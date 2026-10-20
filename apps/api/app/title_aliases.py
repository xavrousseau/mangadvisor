"""Multilingual manga aliases from canonical MAL IDs, Wikidata P4087 and MangaDex.

Title-based discovery is NOT identity proof. MangaDex results require exact
attributes.links.mal == canonical source_mal_id before accepting any alias.
No ISBN, French retail edition, reading progress or user collection is changed.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from apps.api.app.bnf_batch import connect_database

SOURCE_MANGADEX = "MANGADEX_MAL_LINK"
MAX_MANGADEX_BATCH = 30
MAX_ALIASES = 35
MANGADEX_URL = "https://api.mangadex.org/manga"
USER_AGENT = "Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; noncommercial metadata)"
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
QID = re.compile(r"^Q[1-9][0-9]{0,11}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_title_alias (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    search_key TEXT NOT NULL,
    language_code TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    source_mal_id INTEGER NOT NULL,
    validated_identity BOOLEAN NOT NULL DEFAULT TRUE,
    is_french_publisher_title BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(manga_id,search_key,language_code,source_name),
    CHECK(char_length(alias) BETWEEN 1 AND 220),
    CHECK(char_length(search_key) BETWEEN 1 AND 220),
    CHECK(language_code IN ('fr','en','ja','ja-ro','und')),
    CHECK(validated_identity=TRUE),
    CHECK(is_french_publisher_title=FALSE)
);
CREATE INDEX IF NOT EXISTS manga_title_alias_key_idx
    ON manga_title_alias(search_key);
CREATE INDEX IF NOT EXISTS manga_title_alias_manga_lang_idx
    ON manga_title_alias(manga_id,language_code);
CREATE TABLE IF NOT EXISTS manga_mangadex_attempt (
    manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
    source_mal_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('MATCHED','NOT_FOUND','AMBIGUOUS','ERROR')),
    source_id TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS manga_mangadex_pending_attempt (
    user_id INTEGER NOT NULL,
    source_key TEXT NOT NULL,
    search_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('MATCHED','AMBIGUOUS','NOT_FOUND','OUTSIDE_CATALOG','ERROR')
    ),
    candidates INTEGER NOT NULL DEFAULT 0,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(user_id,source_key)
);
"""


def normalize_title(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())[:220]


def make_alias(title: Any, language: str, source: str,
               reference: str, mal_id: int) -> dict[str,Any] | None:
    if not isinstance(title,str):
        return None
    title=" ".join(title.split())
    if not title or len(title)>220 or language not in ("fr","en","ja","ja-ro","und"):
        return None
    if any(ord(c)<32 for c in title):
        return None
    key=normalize_title(title)
    if not key:
        return None
    return {"alias":title,"search_key":key,"language_code":language,
            "source_name":source,"source_ref":reference,"source_mal_id":mal_id}


UPSERT = """
INSERT INTO manga_title_alias
 (manga_id,alias,search_key,language_code,source_name,source_ref,source_mal_id)
VALUES
 (%(manga_id)s,%(alias)s,%(search_key)s,%(language_code)s,
  %(source_name)s,%(source_ref)s,%(source_mal_id)s)
ON CONFLICT (manga_id,search_key,language_code,source_name) DO UPDATE SET
 alias=EXCLUDED.alias,source_ref=EXCLUDED.source_ref,
 source_mal_id=EXCLUDED.source_mal_id,updated_at=NOW()
"""

LOCAL_SQL = """
SELECT m.id,m.source_mal_id,m.title,m.title_english,m.title_japanese,
       j.raw_json,wf.label_fr,wf.wikidata_id
FROM manga m
LEFT JOIN jikan_manga_source j ON j.mal_id=m.source_mal_id
LEFT JOIN manga_wikidata_attempt wa
  ON wa.manga_id=m.id AND wa.status='MATCHED'
LEFT JOIN manga_wikidata_fact wf
  ON wf.manga_id=wa.manga_id AND wf.source_mal_id=m.source_mal_id
WHERE m.id > %(after_id)s
ORDER BY m.id
LIMIT %(limit)s
"""


def local_aliases(manga: dict[str,Any]) -> list[dict[str,Any]]:
    mid=int(manga["source_mal_id"])
    variants=[]
    for field,lang,source in (
        ("title","ja-ro","MAL_ORIGINAL"),("title_english","en","MAL_ENGLISH"),
        ("title_japanese","ja","MAL_JAPANESE"),
    ):
        if item:=make_alias(manga.get(field),lang,source,f"MAL:{mid}",mid):
            variants.append(item)
    raw=manga.get("raw_json")
    if isinstance(raw,str):
        try:raw=json.loads(raw)
        except ValueError:raw=None
    if isinstance(raw,dict) and raw.get("mal_id")==mid:
        synonyms=raw.get("title_synonyms")
        if isinstance(synonyms,list):
            for title in synonyms[:MAX_ALIASES]:
                if item:=make_alias(title,"und","MAL_SYNONYM",f"MAL:{mid}",mid):
                    variants.append(item)
        titles=raw.get("titles")
        if isinstance(titles,list):
            for line in titles[:MAX_ALIASES]:
                if not isinstance(line,dict):continue
                lang={"French":"fr","English":"en","Japanese":"ja",
                      "Default":"ja-ro","Synonym":"und"}.get(line.get("type"))
                if lang and (item:=make_alias(line.get("title"),lang,"MAL_ALTERNATIVE",
                                             f"MAL:{mid}",mid)):
                    variants.append(item)
    qid=manga.get("wikidata_id")
    if isinstance(qid,str) and QID.fullmatch(qid) and manga.get("label_fr"):
        if item:=make_alias(manga["label_fr"],"fr","WIKIDATA_P4087",
                           "https://www.wikidata.org/wiki/"+qid,mid):
            variants.append(item)
    unique={}
    for item in variants:
        unique[(item["search_key"],item["language_code"],item["source_name"])]=item
    return list(unique.values())[:80]


def ensure_alias_schema(factory: Callable[...,Any]) -> None:
    with factory() as conn:
        with conn.cursor() as cur:cur.execute(SCHEMA)
        conn.commit()


def import_local_aliases(factory: Callable[...,Any], *, limit:int=20000) -> dict[str,int]:
    if type(limit) is not int or not 1<=limit<=100000:
        raise ValueError("Invalid catalog scope")
    ensure_alias_schema(factory)
    after_id=0
    report={"works":0,"aliases":0,"french":0}
    while report["works"]<limit:
        with factory() as conn:
            with conn.cursor() as cur:
                cur.execute(LOCAL_SQL,{"after_id":after_id,
                                       "limit":min(1000,limit-report["works"])})
                batch=list(cur.fetchall())
        if not batch:break
        with factory() as conn:
            with conn.cursor() as cur:
                for row in batch:
                    for alias in local_aliases(row):
                        cur.execute(UPSERT,{"manga_id":row["id"],**alias})
                        report["aliases"]+=1
                        report["french"]+=int(alias["language_code"]=="fr")
            conn.commit()
        after_id=int(batch[-1]["id"])
        report["works"]+=len(batch)
        print(f"Index multilingue : {report['works']} mangas, {report['aliases']} alias.",flush=True)
    return report


class MangaDexUnavailable(Exception):
    pass


def fetch_mangadex(title:str)->dict[str,Any]:
    if not isinstance(title,str) or not 2<=len(title.strip())<=180:
        raise ValueError("Invalid discovery title")
    url=MANGADEX_URL+"?"+urllib.parse.urlencode({
        "title":title.strip(),"limit":20,"contentRating[]":"safe",
    })
    req=urllib.request.Request(url,headers={"Accept":"application/json",
                                             "User-Agent":USER_AGENT})
    try:
        with urllib.request.urlopen(req,timeout=22) as response:
            raw=response.read(750001)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError) as exc:
        raise MangaDexUnavailable("MangaDex indisponible.") from exc
    if len(raw)>750000:raise MangaDexUnavailable("Reponse MangaDex trop volumineuse.")
    try:payload=json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise MangaDexUnavailable("Reponse MangaDex invalide.") from exc
    if not isinstance(payload,dict) or payload.get("result")!="ok" or not isinstance(payload.get("data"),list):
        raise MangaDexUnavailable("Structure de reponse MangaDex non reconnue.")
    return payload


def matched_mangadex(mal_id:int,pages:list[dict[str,Any]])->dict[str,Any]:
    matches={}
    for page in pages:
        if not isinstance(page,dict):continue
        for entry in page.get("data",[])[:20]:
            if not isinstance(entry,dict) or entry.get("type")!="manga":continue
            uuid=entry.get("id")
            attrs=entry.get("attributes")
            if not isinstance(uuid,str) or not UUID.fullmatch(uuid):continue
            if not isinstance(attrs,dict):continue
            links=attrs.get("links") or {}
            if not isinstance(links,dict) or str(links.get("mal") or "")!=str(mal_id):
                continue
            matches[uuid]=attrs
    if len(matches)!=1:
        return {"status":"AMBIGUOUS" if matches else "NOT_FOUND",
                "source_id":None,"aliases":[]}
    uuid,attrs=next(iter(matches.items()))
    found=[]
    def append(title:Any,code:Any)->None:
        language={"jp":"ja","ja":"ja","ja-ro":"ja-ro",
                  "fr":"fr","en":"en"}.get(code)
        if language and (item:=make_alias(title,language,SOURCE_MANGADEX,
                        "https://mangadex.org/title/"+uuid,mal_id)):
            found.append(item)
    title=attrs.get("title")
    if isinstance(title,dict):
        for lang,val in title.items():append(val,lang)
    alts=attrs.get("altTitles")
    if isinstance(alts,list):
        for entry in alts[:MAX_ALIASES]:
            if isinstance(entry,dict):
                for lang,val in entry.items():append(val,lang)
    unique={}
    for item in found:unique[(item["search_key"],item["language_code"])]=item
    return {"status":"MATCHED","source_id":uuid,
            "aliases":list(unique.values())[:MAX_ALIASES]}


PENDING_MANGADEX = """
SELECT m.id,m.source_mal_id,m.title,m.title_english
FROM manga m
LEFT JOIN manga_mangadex_attempt a ON a.manga_id=m.id
WHERE m.source_mal_id>0 AND m.id=ANY(%(target_ids)s)
 AND (a.checked_at IS NULL OR a.source_mal_id<>m.source_mal_id
      OR a.checked_at<NOW()-CASE WHEN a.status='ERROR'
           THEN INTERVAL '1 day' ELSE INTERVAL '45 days' END)
ORDER BY m.popularity ASC NULLS LAST,m.id
LIMIT %(limit)s
"""
UPSERT_ATTEMPT = """
INSERT INTO manga_mangadex_attempt(manga_id,source_mal_id,status,source_id,checked_at)
VALUES (%(manga_id)s,%(source_mal_id)s,%(status)s,%(source_id)s,NOW())
ON CONFLICT (manga_id) DO UPDATE SET
 source_mal_id=EXCLUDED.source_mal_id,status=EXCLUDED.status,
 source_id=EXCLUDED.source_id,checked_at=NOW()
"""


def import_mangadex_aliases(
    factory: Callable[...,Any], *, target_ids:list[int],limit:int=15,
    search:Callable[[str],dict[str,Any]]=fetch_mangadex,
    sleep:Callable[[float],Any]=time.sleep
)->dict[str,int]:
    if type(limit) is not int or not 1<=limit<=MAX_MANGADEX_BATCH:
        raise ValueError("MangaDex limit 1..30")
    if len(target_ids)>250 or any(type(x) is not int or x<=0 for x in target_ids):
        raise ValueError("Invalid linked manga IDs")
    ensure_alias_schema(factory)
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(PENDING_MANGADEX,{"target_ids":target_ids,"limit":limit})
            works=list(cur.fetchall())
    report={"selected":len(works),"matched":0,"not_found":0,
            "ambiguous":0,"error":0,"aliases":0,"french":0}
    requests=0
    for work in works:
        titles=list(dict.fromkeys(
            str(t).strip() for t in (work.get("title_english"),work.get("title"))
            if t and len(str(t).strip())>=2
        ))[:2]
        pages=[]
        failed=False
        for title in titles:
            if requests:sleep(1.6)
            requests+=1
            try:pages.append(search(title))
            except (MangaDexUnavailable,ValueError,TimeoutError,OSError):
                failed=True
                break
        result=({"status":"ERROR","source_id":None,"aliases":[]} if failed
                else matched_mangadex(int(work["source_mal_id"]),pages))
        with factory() as conn:
            with conn.cursor() as cur:
                if result["status"]=="MATCHED":
                    for alias in result["aliases"]:
                        cur.execute(UPSERT,{"manga_id":work["id"],**alias})
                        report["aliases"]+=1
                        report["french"]+=int(alias["language_code"]=="fr")
                cur.execute(UPSERT_ATTEMPT,{
                    "manga_id":work["id"],"source_mal_id":work["source_mal_id"],
                    "status":result["status"],"source_id":result["source_id"],
                })
            conn.commit()
        report[result["status"].lower()]+=1
        print(f"MangaDex : MAL {work['source_mal_id']} -> {result['status']}",flush=True)
        if result["status"]=="ERROR":
            print("MangaDex indisponible : arret, reprise plus tard.",flush=True)
            break
    return report


PENDING_OWNER_SQL = """
SELECT p.source_key,p.entry_title,p.work_declared
FROM user_manga_inventory_pending p
LEFT JOIN manga_mangadex_pending_attempt a
  ON a.user_id=p.user_id AND a.source_key=p.source_key
WHERE p.user_id=%(user_id)s
  AND (a.checked_at IS NULL
    OR a.search_hash<>md5(COALESCE(NULLIF(BTRIM(p.work_declared),''),
                                    p.entry_title))
    OR a.checked_at<NOW()-CASE WHEN a.status='ERROR' THEN INTERVAL '1 day'
                                ELSE INTERVAL '45 days' END)
ORDER BY p.source_key
LIMIT %(limit)s
"""

UPSERT_PENDING = """
INSERT INTO manga_mangadex_pending_attempt
    (user_id,source_key,search_hash,status,candidates,checked_at)
VALUES (%(user_id)s,%(source_key)s,%(search_hash)s,%(status)s,%(candidates)s,NOW())
ON CONFLICT (user_id,source_key) DO UPDATE SET
 search_hash=EXCLUDED.search_hash,status=EXCLUDED.status,
 candidates=EXCLUDED.candidates,checked_at=NOW()
"""


def pending_mangadex_aliases(
    factory:Callable[...,Any], *,limit:int=15,user_id:int=1,
    search:Callable[[str],dict[str,Any]]=fetch_mangadex,
    sleep:Callable[[float],Any]=time.sleep,
)->dict[str,int]:
    """Look up UNRESOLVED owner's titles, never resolve them automatically."""
    if type(limit) is not int or not 1<=limit<=MAX_MANGADEX_BATCH:
        raise ValueError("Invalid pending MangaDex limit")
    if type(user_id) is not int or user_id<=0:raise ValueError("Invalid user")
    ensure_alias_schema(factory)
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(PENDING_OWNER_SQL,{"user_id":user_id,"limit":limit})
            works=list(cur.fetchall())
    result={"selected":len(works),"matched":0,"ambiguous":0,
            "not_found":0,"outside_catalog":0,"error":0,
            "aliases":0,"french":0}
    for index,work in enumerate(works):
        title=(work.get("work_declared") or work.get("entry_title") or "").strip()[:180]
        digest=hashlib.md5(title.encode("utf-8")).hexdigest()
        findings={}
        status="NOT_FOUND"
        try:
            if len(title)>=2:
                if index:sleep(1.6)
                response=search(title)
                for raw in response.get("data",[])[:20]:
                    if not isinstance(raw,dict):continue
                    attrs=raw.get("attributes") or {}
                    if not isinstance(attrs,dict):continue
                    links=attrs.get("links") or {}
                    if not isinstance(links,dict):continue
                    value=str(links.get("mal") or "")
                    if not re.fullmatch(r"[1-9][0-9]{0,8}",value):continue
                    mal=int(value)
                    matched=matched_mangadex(mal,[{"data":[raw]}])
                    if matched["status"]!="MATCHED":continue
                    # A substring hit is NOT proof that this owner source title
                    # denotes the result; require an exact title / altTitle.
                    if normalize_title(title) not in {
                        alias["search_key"] for alias in matched["aliases"]
                    }:
                        continue
                    findings[mal]=matched
            if findings:
                ids=list(findings)
                with factory() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT id,source_mal_id FROM manga
                            WHERE source_mal_id=ANY(%(ids)s)
                        """,{"ids":ids})
                        canonical={int(row["source_mal_id"]):int(row["id"])
                                   for row in cur.fetchall()}
                if not canonical:
                    status="OUTSIDE_CATALOG"
                else:
                    status="MATCHED" if len(canonical)==1 else "AMBIGUOUS"
                    with factory() as conn:
                        with conn.cursor() as cur:
                            for mal,manga_id in canonical.items():
                                for alias in findings[mal]["aliases"]:
                                    cur.execute(UPSERT,{"manga_id":manga_id,**alias})
                                    result["aliases"]+=1
                                    result["french"]+=int(alias["language_code"]=="fr")
                        conn.commit()
        except (MangaDexUnavailable,ValueError,TimeoutError,OSError):
            status="ERROR"
        with factory() as conn:
            with conn.cursor() as cur:
                cur.execute(UPSERT_PENDING,{
                    "user_id":user_id,"source_key":work["source_key"],
                    "search_hash":digest,"status":status,"candidates":len(findings),
                })
            conn.commit()
        result[status.lower()]+=1
        print(f"MangaDex inventaire {index+1}/{len(works)} : "
              f"{status} ({len(findings)} liens MAL vérifiés)",flush=True)
        if status=="ERROR":break
    return result


def create_title_alias_router(factory:Callable[...,Any])->APIRouter:
    router=APIRouter(prefix="/mangas",tags=["Noms multilingues sourcés"])

    @router.get("/{manga_id}/title-aliases")
    def title_aliases(manga_id:int)->dict[str,Any]:
        if manga_id<=0:
            raise HTTPException(status_code=422,detail="Identifiant manga invalide.")
        with factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id,source_mal_id FROM manga WHERE id=%(id)s",
                            {"id":manga_id})
                manga=cur.fetchone()
                if manga is None:
                    raise HTTPException(status_code=404,detail="Manga introuvable.")
                cur.execute("""
                    SELECT alias,language_code,source_name,source_ref
                    FROM manga_title_alias
                    WHERE manga_id=%(manga_id)s AND source_mal_id=%(mal_id)s
                    ORDER BY CASE language_code WHEN 'fr' THEN 0
                         WHEN 'en' THEN 1 WHEN 'ja-ro' THEN 2
                         WHEN 'ja' THEN 3 ELSE 4 END,
                         CASE source_name WHEN 'MANGADEX_MAL_LINK' THEN 0
                         WHEN 'WIKIDATA_P4087' THEN 1 ELSE 2 END,
                         alias LIMIT 60
                """,{"manga_id":manga_id,"mal_id":manga["source_mal_id"]})
                rows=list(cur.fetchall())
        return {
            "manga_id":manga_id,"count":len(rows),"items":rows,
            "verified_identity":True,
            "french_publisher_titles_verified":False,
            "automatic_edition_match":False,
            "notice":"Noms de communauté reliés à la même œuvre par MAL ID. "
                     "Les titres français ne prouvent pas une édition commercialisée.",
        }

    return router


def cli_main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="Alias multilingues identifiants exacts.")
    parser.add_argument("--local-only",action="store_true")
    parser.add_argument("--mangadex-limit",type=int,default=15)
    parser.add_argument("--catalog-limit",type=int,default=20000)
    args=parser.parse_args(argv)
    if not 1<=args.mangadex_limit<=MAX_MANGADEX_BATCH:
        parser.error("--mangadex-limit doit etre entre 1 et 30")
    if not 1<=args.catalog_limit<=100000:
        parser.error("--catalog-limit doit etre entre 1 et 100000")
    print("Indexation des noms alternatifs MAL et Wikidata déjà en base.",flush=True)
    local=import_local_aliases(connect_database,limit=args.catalog_limit)
    print("Index local : "+", ".join(f"{k}={v}" for k,v in local.items()),flush=True)
    if args.local_only:
        print("MangaDex desactive : source MAL et Wikidata uniquement.",flush=True)
        return 0
    from apps.api.app.library_enrichment import linked_library_scope
    scope=linked_library_scope(connect_database,max_works=250)
    ids=scope["ids"]
    if not ids:
        print("Aucune oeuvre personnelle liee : pas d'appels MangaDex.",flush=True)
        return 0
    aggregate={"selected":0,"matched":0,"not_found":0,
               "ambiguous":0,"error":0,"aliases":0,"french":0}
    while aggregate["selected"]<args.mangadex_limit:
        remaining=min(10,args.mangadex_limit-aggregate["selected"])
        step=import_mangadex_aliases(connect_database,target_ids=ids,limit=remaining)
        for key,val in step.items():aggregate[key]+=val
        if step["selected"]==0 or step["error"]:break
    print("MangaDex : "+", ".join(f"{k}={v}" for k,v in aggregate.items()),flush=True)
    print("Correspondances par MAL ID uniquement. ISBN et editions inchanges.",flush=True)
    return 1 if aggregate["error"] else 0


if __name__=="__main__":
    raise SystemExit(cli_main())
