"""Provenance-first work title index, not a machine translation service.

A canonical MyAnimeList manga can be looked up by its existing JP / EN
titles, Jikan raw synonyms, and Wikidata P4087 labels & aliases. Each
label remains source-attributed; no foreign work is ever inferred from title
similarity. The only manually reviewed work title in the seed is the BnF
authority for MyAnimeList manga 74, with a direct work-authority citation.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from collections import Counter
from typing import Any, Callable, Iterable

from apps.api.app.bnf_batch import connect_database

SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_title_alias (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    alias TEXT NOT NULL CHECK (length(alias) BETWEEN 1 AND 200),
    alias_key TEXT NOT NULL CHECK (length(alias_key) BETWEEN 1 AND 200),
    language TEXT NOT NULL CHECK (language IN ('fr','en','ja','romaji','und')),
    source_name TEXT NOT NULL,
    source_url TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (manga_id,alias_key,source_name)
);
CREATE INDEX IF NOT EXISTS idx_manga_title_alias_key
  ON manga_title_alias(alias_key);
CREATE INDEX IF NOT EXISTS idx_manga_title_alias_manga
  ON manga_title_alias(manga_id);
"""

# A single authoritative BnF *work* authority verified against MAL 74 and
# the author's original manga, NOT an edition's ISBN. Do not generalize this
# seed to loosely related franchise works or anime adaptations.
REVIEWED_WORK_ALIASES = (
    (74, "L'Attaque des Titans", "fr", "BNF_AUTHORITY_WORK",
     "https://catalogue.bnf.fr/ark:/12148/cb177166897"),
)

CANONICAL_SQL = """
SELECT m.id,m.source_mal_id,m.title,m.title_english,m.title_japanese,
       j.raw_json,
       CASE WHEN w.wikidata_id IS NOT NULL
             AND wa.status='MATCHED'
             AND w.source_mal_id=m.source_mal_id
            THEN w.label_fr END AS wikidata_label_fr,
       CASE WHEN w.wikidata_id IS NOT NULL
             AND wa.status='MATCHED'
             AND w.source_mal_id=m.source_mal_id
            THEN w.alternate_titles END AS wikidata_alternate_titles,
       CASE WHEN w.wikidata_id IS NOT NULL
             AND wa.status='MATCHED'
             AND w.source_mal_id=m.source_mal_id
            THEN w.wikidata_id END AS wikidata_id
FROM manga m
LEFT JOIN jikan_manga_source j ON j.mal_id=m.source_mal_id
LEFT JOIN manga_wikidata_attempt wa ON wa.manga_id=m.id
LEFT JOIN manga_wikidata_fact w ON w.manga_id=wa.manga_id
ORDER BY m.id
"""

UPSERT_SQL = """
INSERT INTO manga_title_alias
(manga_id,alias,alias_key,language,source_name,source_url)
VALUES (%(manga_id)s,%(alias)s,%(alias_key)s,%(language)s,%(source_name)s,%(source_url)s)
ON CONFLICT (manga_id,alias_key,source_name) DO UPDATE SET
 alias=EXCLUDED.alias, language=EXCLUDED.language,
 source_url=EXCLUDED.source_url, updated_at=NOW()
"""

def title_key(title: str | None) -> str:
    """Unicode-safe lookup for French accents and punctuation, no translation.

    Hiragana, Katakana and kanji remain intact. Never discard franchise
    subtitles, part numbers or edition suffixes: they're identity clues.
    """
    if not isinstance(title,str):
        return ""
    t = unicodedata.normalize("NFKC",title).casefold()
    t = t.replace("n°","no ").replace("nº","no ")
    t = "".join(c for c in unicodedata.normalize("NFKD", t)
                if not unicodedata.combining(c))
    t = "".join(c if c.isalnum() else " " for c in t)
    return " ".join(t.split())[:200]


def _language(type_name: str | None) -> str:
    label=(type_name or "").casefold()
    if "english" in label: return "en"
    if "japanese" in label: return "ja"
    if "french" in label: return "fr"
    if "romaji" in label or "default" in label: return "romaji"
    return "und"


def aliases_from_source(row: dict[str,Any]) -> list[dict[str,str | None]]:
    """Only names already associated with this exact manga's MAL ID."""
    found:dict[tuple[str,str],dict[str,str|None]]={}
    def include(value:Any, language:str, source:str, url:str|None=None):
        if not isinstance(value,str):return
        text=value.strip()
        key=title_key(text)
        if not key or len(text)>200 or key.isdigit():return
        found[(key,source)]={"alias":text,"alias_key":key,
                             "language":language,"source_name":source,
                             "source_url":url}
    mal=row.get("source_mal_id")
    malurl=f"https://myanimelist.net/manga/{mal}" if type(mal) is int and mal>0 else None
    include(row.get("title"),"romaji","MAL_ORIGINAL",malurl)
    include(row.get("title_english"),"en","MAL_ENGLISH",malurl)
    include(row.get("title_japanese"),"ja","MAL_JAPANESE",malurl)
    raw=row.get("raw_json")
    if isinstance(raw,dict):
        for item in (raw.get("titles") or [])[:50]:
            if isinstance(item,dict):
                include(item.get("title"),_language(item.get("type")),"MAL_ALT",malurl)
        for name in (raw.get("title_synonyms") or [])[:50]:
            include(name,"und","MAL_SYNONYM",malurl)
    wiki=row.get("wikidata_id")
    if isinstance(wiki,str) and re.fullmatch(r"Q[1-9]\d{0,11}",wiki):
        source_url=f"https://www.wikidata.org/wiki/{wiki}"
        include(row.get("wikidata_label_fr"),"fr","WIKIDATA_P4087_FR",
                source_url)
        raw_titles=row.get("wikidata_alternate_titles")
        if isinstance(raw_titles,list):
            for item in raw_titles[:40]:
                if isinstance(item,dict) and item.get("lang") in ("fr","en","ja"):
                    include(item.get("title"),item["lang"],
                            "WIKIDATA_P4087_"+item["lang"].upper(),source_url)
    for verified_mal,title,lang,source,url in REVIEWED_WORK_ALIASES:
        if mal==verified_mal:
            include(title,lang,source,url)
    return list(found.values())


def ensure_alias_schema(factory:Callable[...,Any]) -> None:
    with factory() as conn:
        with conn.cursor() as cur: cur.execute(SCHEMA)
        conn.commit()


def sync_aliases(factory:Callable[...,Any], *, max_works:int=50000) -> dict[str,int]:
    if type(max_works) is not int or not 1<=max_works<=50000:
        raise ValueError("Nombre de mangas incorrect (1..50000).")
    ensure_alias_schema(factory)
    totals=Counter()
    with factory() as conn:
        # Named cursor streams a full catalogue without materializing JSON
        # bodies of tens of thousands of works in memory.
        with conn.cursor(name="manga_alias_index_cursor") as cur:
            cur.execute(CANONICAL_SQL)
            while totals["works"] < max_works:
                batch=cur.fetchmany(min(200,max_works-totals["works"]))
                if not batch:break
                with factory() as writer:
                    with writer.cursor() as out:
                        for work in batch:
                            aliases=aliases_from_source(work)
                            for alias in aliases:
                                out.execute(UPSERT_SQL,{
                                    "manga_id":work["id"],**alias
                                })
                            totals["aliases_processed"]+=len(aliases)
                            totals["works"]+=1
                    writer.commit()
                print(f"Index des titres : {totals['works']} œuvres parcourues ; "
                      f"{totals['aliases_processed']} alias traités.",flush=True)
    return dict(totals)


def refresh_library_wikidata(factory:Callable[...,Any],
                             *, max_works:int=80,
                             sleep:Callable[[float],Any]|None=None)->dict[str,int]:
    """Opt-in only: requery cached linked MAL IDs for current multilingual labels."""
    import time
    from apps.api.app.library_enrichment import linked_library_scope
    from apps.api.app.wikidata_enrichment import run_batch as wiki_batch
    if type(max_works) is not int or not 1 <= max_works <= 250:
        raise ValueError("Maximum d'oeuvres liees invalide (1..250).")
    scope=linked_library_scope(factory,max_works=max_works)
    ids=scope["ids"]
    paused=sleep if sleep is not None else time.sleep
    totals=Counter()
    for offset in range(0,len(ids),15):
        if offset: paused(2.5)
        part=ids[offset:offset+15]
        result=wiki_batch(factory,limit=len(part),refresh=True,target_ids=part)
        for k,v in result.items():
            if isinstance(v,int):totals[k]+=v
        print(f"Alias Wikidata : lot {1+offset//15}, "
              f"{result['matched']} correspondances, "
              f"{result['error']} erreurs.",flush=True)
        if result["selected"] and result["error"]==result["selected"]:
            print("Source indisponible : arrêt immédiat des recherches Wikidata.",
                  flush=True)
            totals["aborted"]=1
            break
    return dict(totals)


def cli_main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="Index des titres et alias FR/EN/JA existants.")
    parser.add_argument("--max-works",type=int,default=50000)
    parser.add_argument("--refresh-library-wikidata",action="store_true",
                        help="Reconsulter Wikidata pour les oeuvres liees uniquement.")
    parser.add_argument("--library-max-works",type=int,default=80)
    args=parser.parse_args(argv)
    if not 1<=args.max_works<=50000:parser.error("1..50000 attendus")
    if not 1<=args.library_max_works<=250:parser.error("1..250 attendus")
    if args.refresh_library_wikidata:
        refresh=refresh_library_wikidata(
            connect_database,max_works=args.library_max_works)
        if refresh.get("aborted"):
            print("Alias locaux deja recuperes inchanges. Nouvelle tentative "
                  "Wikidata possible plus tard.",flush=True)
    result=sync_aliases(connect_database,max_works=args.max_works)
    print("Bilan index multilingue : "+", ".join(
        f"{key}={val}" for key,val in result.items()),flush=True)
    print("Aucune édition ni ligne de ta mangathèque n'a été modifiée.",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(cli_main())
