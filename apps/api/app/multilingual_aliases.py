"""Multilingual alias evidence for Mangadvisor (Wikidata CC0).

Only trusted, unique Wikidata manga P4087 -> canonical MAL-ID links may add
French/English/Japanese titles. A label is a search alias, *not* an edition,
ISBN, or verified French commercial title. No updates to manga or inventory.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Callable

from apps.api.app.bnf_batch import connect_database

QID = re.compile(r"^Q[1-9][0-9]{0,11}$")
MAX_BATCH = 20
DEFAULT_BATCH = 12
MAX_BYTES = 400_000
SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_title_alias (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_id TEXT NOT NULL,
    language_code TEXT NOT NULL CHECK (language_code IN ('fr','en','ja','ja-ro')),
    alias TEXT NOT NULL CHECK (length(alias) BETWEEN 2 AND 200),
    alias_key TEXT NOT NULL CHECK (length(alias_key) BETWEEN 2 AND 200),
    source_url TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (manga_id,source_name,language_code,alias_key)
);
CREATE INDEX IF NOT EXISTS idx_manga_title_alias_key ON manga_title_alias(alias_key);
CREATE TABLE IF NOT EXISTS manga_title_alias_attempt (
    manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
    wikidata_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('CHECKED','EMPTY','ERROR')),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

WORK_SQL = """
SELECT m.id,m.source_mal_id,f.wikidata_id
FROM manga m
JOIN manga_wikidata_attempt a ON a.manga_id=m.id AND a.status='MATCHED'
JOIN manga_wikidata_fact f ON f.manga_id=m.id
 AND f.source_mal_id=m.source_mal_id
LEFT JOIN manga_title_alias_attempt attempt ON attempt.manga_id=m.id
WHERE m.source_mal_id > 0
AND (%(refresh)s OR attempt.manga_id IS NULL
     OR attempt.wikidata_id<>f.wikidata_id
     OR attempt.checked_at < NOW() -
       CASE WHEN attempt.status='ERROR' THEN INTERVAL '1 day'
            ELSE INTERVAL '45 days' END)
AND f.wikidata_id ~ '^Q[1-9][0-9]*$'
ORDER BY CASE WHEN EXISTS(
  SELECT 1 FROM user_manga_inventory_declaration d WHERE d.manga_id=m.id
) THEN 0 WHEN EXISTS(
  SELECT 1 FROM user_manga_library l WHERE l.manga_id=m.id
) THEN 1 ELSE 2 END,m.popularity ASC NULLS LAST,m.id ASC
LIMIT %(limit)s
"""

def title_key(raw: str) -> str:
    """Unicode- and punctuation-tolerant, accent-insensitive alias search."""
    value = unicodedata.normalize("NFKD", raw.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())[:200]


def fetch_entities(qids: list[str]) -> dict[str, Any]:
    if not 1 <= len(qids) <= MAX_BATCH or any(not QID.fullmatch(x) for x in qids):
        raise ValueError("Identifiants Wikidata invalides.")
    url="https://www.wikidata.org/w/api.php?"+urllib.parse.urlencode({
        "action":"wbgetentities","ids":"|".join(qids),
        "props":"labels|aliases|claims","languages":"fr|en|ja",
        "format":"json",
    })
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; CC0 alias discovery)",
        "Accept":"application/json",
    })
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read(MAX_BYTES+1)
    except (OSError,TimeoutError,urllib.error.URLError) as exc:
        raise ValueError("Wikidata indisponible ; relancer plus tard.") from exc
    if len(raw)>MAX_BYTES:
        raise ValueError("Réponse Wikidata trop volumineuse.")
    try:
        return json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise ValueError("Wikidata a renvoyé un JSON invalide.") from exc


def _claim_has_mal(entity: dict[str, Any], mal_id: int) -> bool:
    """Independently re-verify P4087 inside the downloaded entity."""
    claims=entity.get("claims")
    if not isinstance(claims,dict):
        return False
    for claim in claims.get("P4087",[]):
        if not isinstance(claim,dict) or claim.get("rank")=="deprecated":
            continue
        main=claim.get("mainsnak") or {}
        value=(main.get("datavalue") or {}).get("value")
        if str(value)==str(mal_id) and isinstance(value,str):
            return True
    return False


def parse_entities(works: list[dict[str, Any]], payload: dict[str, Any]) -> dict[int,list[dict[str,str]]]:
    if not isinstance(payload,dict) or not isinstance(payload.get("entities"),dict):
        raise ValueError("Wikidata : réponse incomplète.")
    source=payload["entities"]
    outcome={}
    for work in works:
        qid=work["wikidata_id"]
        entity=source.get(qid,{})
        if not isinstance(entity,dict) or entity.get("id")!=qid:
            raise ValueError("Une entité Wikidata est manquante ou incohérente.")
        if not _claim_has_mal(entity,int(work["source_mal_id"])):
            # Fail the entire batch, rather than inadvertently claiming aliases
            # of an unverified manga from a stale/incorrect source link.
            raise ValueError("L'entité Wikidata ne confirme pas l'ID manga MAL P4087.")
        titles={}
        for field in ("labels","aliases"):
            values=entity.get(field) or {}
            if not isinstance(values,dict):
                continue
            for lang in ("fr","en","ja"):
                content=values.get(lang,[])
                for item in (content if isinstance(content,list) else [content]):
                    if not isinstance(item,dict):
                        continue
                    name=item.get("value")
                    if not isinstance(name,str) or not 2<=len(name.strip())<=200:
                        continue
                    label=name.strip()
                    key=title_key(label)
                    if 2<=len(key)<=200:
                        titles[(lang,key)]={
                            "language_code":lang,"alias":label,
                            "alias_key":key,"source_name":"WIKIDATA_P4087",
                            "source_id":qid,
                            "source_url":"https://www.wikidata.org/wiki/"+qid,
                        }
        outcome[work["id"]]=list(titles.values())[:80]
    return outcome


UPSERT = """
INSERT INTO manga_title_alias
(manga_id,source_name,source_id,language_code,alias,alias_key,source_url)
VALUES (%(manga_id)s,%(source_name)s,%(source_id)s,%(language_code)s,
        %(alias)s,%(alias_key)s,%(source_url)s)
ON CONFLICT (manga_id,source_name,language_code,alias_key)
DO UPDATE SET alias=EXCLUDED.alias,source_id=EXCLUDED.source_id,
              source_url=EXCLUDED.source_url
"""

def run_batch(factory: Callable[..., Any], *, limit: int=DEFAULT_BATCH,
              refresh: bool=False,
              lookup: Callable[[list[str]],dict[str,Any]]=fetch_entities) -> dict[str,int]:
    if not 1<=limit<=MAX_BATCH:
        raise ValueError("Un lot doit contenir entre 1 et 20 mangas.")
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(WORK_SQL,{"limit":limit,"refresh":refresh})
            works=list(cur.fetchall())
    stats={"selected":len(works),"checked":0,"empty":0,"error":0,"aliases":0}
    if not works:
        return stats
    try:
        data=parse_entities(works,lookup([work["wikidata_id"] for work in works]))
    except (OSError,TimeoutError,ValueError,KeyError) as exc:
        print("Wikidata : erreur de vérification des identifiants, aucun alias enregistré :",str(exc))
        stats["error"]=len(works)
        # Do not poison the cache on a transient provider error.
        return stats
    with factory() as conn:
        for work in works:
            aliases=data[work["id"]]
            state="CHECKED" if aliases else "EMPTY"
            with conn.transaction():
                with conn.cursor() as cur:
                    # A refresh may replace aliases for the same proven source QID,
                    # never another source's records.
                    cur.execute("""DELETE FROM manga_title_alias
                                   WHERE manga_id=%(id)s AND source_name='WIKIDATA_P4087'""",
                                {"id":work["id"]})
                    for item in aliases:
                        cur.execute(UPSERT,{"manga_id":work["id"],**item})
                    cur.execute("""
                        INSERT INTO manga_title_alias_attempt(manga_id,wikidata_id,status)
                        VALUES (%(id)s,%(qid)s,%(status)s)
                        ON CONFLICT (manga_id) DO UPDATE SET
                          wikidata_id=EXCLUDED.wikidata_id,status=EXCLUDED.status,
                          checked_at=NOW()
                    """,{"id":work["id"],"qid":work["wikidata_id"],"status":state})
            stats["aliases"]+=len(aliases)
            stats[state.lower()]+=1
    return stats


def cli_main(argv: list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(description="Alias FR/EN/JA Wikidata (ID MAL vérifié).")
    parser.add_argument("--limit",type=int,default=DEFAULT_BATCH)
    parser.add_argument("--refresh",action="store_true")
    args=parser.parse_args(argv)
    print("Alias français/anglais/japonais depuis les entités Wikidata vérifiées.")
    print("Aucune édition, ISBN, déclaration ou lecture ne sera modifiée.")
    report=run_batch(connect_database,limit=args.limit,refresh=args.refresh)
    print("Bilan : "+", ".join(f"{k}={v}" for k,v in report.items()))
    return 1 if report["error"] else 0


if __name__=="__main__":
    raise SystemExit(cli_main())
