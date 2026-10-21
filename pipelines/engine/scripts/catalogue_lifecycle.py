"""Mangadvisor catalogue lifecycle: one-time audited MAL base, daily DELTAS.

Never reruns 858 MAL pages in the daily cycle. Instead:
  * newest MAL IDs descending until existing overlap (bounded; fail closed);
  * rotating sample of older ascending pages to notice corrected/backfilled works;
  * upsert ONLY changed MAL IDs into source and canonical SQL;
  * bounded Scrinis / MangaUpdates and BnF candidate enrichment;
  * daily opt-in Docker worker when Docker is running.

No ISBN or inventory ownership is ever confirmed automatically. A complete
MAL catalogue must already exist (A -> 19); otherwise fail with guidance.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from pipelines.engine.scripts import sync_full_mal_catalogue as full
from pipelines.engine.scripts import enrich_catalogue_scrinis_fr as scrinis
from pipelines.engine.scripts import catalogue_mangaupdates as mu
from pipelines.engine.scripts import bnf_bulk_import as bnf_files
from pipelines.engine.src.load.postgres_loader import (
    get_postgres_connection, upsert_jikan_manga_batch,
)
from pipelines.engine.scripts.load_jikan_to_postgres import transform_jikan_item

LOGS = full.ROOT / "data" / "logs" / "catalogue_lifecycle"
UPDATES = full.RAW / "updates"
ADVISORY_KEY = 72962026
RECENT_PAGE_CAP = 8
ROTATING_PAGES = 8
DAILY_INTERVAL = 86400
STATE_DDL = """
CREATE TABLE IF NOT EXISTS catalogue_lifecycle_state (
 id SMALLINT PRIMARY KEY CHECK(id=1),
 rolling_page INTEGER NOT NULL DEFAULT 1 CHECK(rolling_page>=1),
 last_success_at TIMESTAMPTZ
);
INSERT INTO catalogue_lifecycle_state(id) VALUES(1)
ON CONFLICT(id) DO NOTHING;
"""
# Uses only the MAL IDs collected during this delta, not a scan/rewrite of
# the entire jikan_manga_source/manga population.
CANONICAL = """
INSERT INTO manga (
 source_name,source_mal_id,title,title_english,title_japanese,
 synopsis,status,chapters,volumes,score,popularity,rank,members,favorites,
 published_from,published_to,manga_type
)
SELECT j.source_name,j.mal_id,j.title,j.title_english,j.title_japanese,
 j.synopsis,j.status,j.chapters,j.volumes,j.score,j.popularity,j.rank,j.members,
 j.favorites,j.published_from,j.published_to,j.manga_type
FROM jikan_manga_source j
WHERE j.mal_id=ANY(%s) AND j.title IS NOT NULL
ON CONFLICT(source_mal_id) DO UPDATE SET
 title=EXCLUDED.title,title_english=COALESCE(EXCLUDED.title_english,manga.title_english),
 title_japanese=COALESCE(EXCLUDED.title_japanese,manga.title_japanese),
 synopsis=COALESCE(EXCLUDED.synopsis,manga.synopsis),
 status=COALESCE(EXCLUDED.status,manga.status),
 chapters=COALESCE(EXCLUDED.chapters,manga.chapters),
 volumes=COALESCE(EXCLUDED.volumes,manga.volumes),
 score=COALESCE(EXCLUDED.score,manga.score),
 popularity=COALESCE(EXCLUDED.popularity,manga.popularity),
 rank=COALESCE(EXCLUDED.rank,manga.rank),
 members=COALESCE(EXCLUDED.members,manga.members),
 favorites=COALESCE(EXCLUDED.favorites,manga.favorites),
 published_from=COALESCE(EXCLUDED.published_from,manga.published_from),
 published_to=COALESCE(EXCLUDED.published_to,manga.published_to),
 manga_type=COALESCE(EXCLUDED.manga_type,manga.manga_type),
 updated_at=NOW()
"""
TAGS = [
    ("genre","manga_genre","genres_json"),
    ("theme","manga_theme","themes_json"),
    ("demographic","manga_demographic","demographics_json"),
]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_page(session: Any, base: str, page: int, sort: str) -> dict:
    if type(page) is not int or page<1 or sort not in ("asc","desc"):
        raise ValueError("Invalid MAL delta pagination")
    params={"page":page,"limit":100,"order_by":"mal_id","sort":sort}
    for retry in range(4):
        try:
            response=session.get(base+"/manga",params=params,timeout=35)
            if response.status_code in (429,500,502,503,504):
                if retry == 3:
                    response.raise_for_status()
                retry_after=response.headers.get("Retry-After","0")
                try:
                    wait=min(120,max(0,float(retry_after)))
                except (ValueError,TypeError):
                    wait=0
                time.sleep(max(wait,3*(2**retry)))
                continue
            response.raise_for_status()
            payload=response.json()
            items=payload.get("data") if isinstance(payload,dict) else None
            pg=payload.get("pagination") if isinstance(payload,dict) else None
            if not isinstance(items,list) or not items or len(items)>100 or not isinstance(pg,dict):
                raise ValueError("Tenrai: incomplete delta response")
            last=pg.get("last_visible_page")
            if type(last) is not int or last<page:
                raise ValueError("Tenrai: invalid page boundaries")
            if type(pg.get("has_next_page")) is not bool or pg["has_next_page"]!=(page<last):
                raise ValueError("Tenrai: inconsistent has_next_page")
            if pg.get("current_page") not in (None,page):
                raise ValueError("Tenrai: different page returned")
            ids=[x.get("mal_id") for x in items if isinstance(x,dict)]
            if (len(ids)!=len(items) or
                any(type(i) is not int or i<=0 for i in ids) or
                len(ids)!=len(set(ids)) or
                ids!=sorted(ids,reverse=(sort=="desc"))):
                raise ValueError("Tenrai: duplicate, missing or unsorted MAL ID")
            return payload
        except (requests.RequestException,ValueError):
            if retry==3:
                raise
            time.sleep(3*(2**retry))
    raise ValueError("Tenrai: exhausted retries")


def changed_items(db: Any, pages: list[dict]) -> tuple[list[dict],int,int]:
    """Compare actual MAL JSON, retain distinct IDs; no writes in this phase."""
    found: dict[int,dict] = {}
    for p in pages:
        for item in p["data"]:
            mal=item["mal_id"]
            # If a work occurred in both scans, preserve newest-page result.
            found.setdefault(mal,item)
    if not found:
        return [],0,0
    with db.cursor() as cur:
        cur.execute("SELECT mal_id,raw_json FROM jikan_manga_source WHERE mal_id=ANY(%s)",
                    (list(found),))
        db_rows=cur.fetchall()
    previous={int(r["mal_id"]):r["raw_json"] for r in db_rows}
    delta=[]
    added=0
    changed=0
    for mal,item in found.items():
        old=previous.get(mal)
        if isinstance(old,str):
            old=json.loads(old)
        if old != item:
            if old is None:
                added+=1
            else:
                changed+=1
            delta.append(item)
    return delta,added,changed


def consolidate_changed(db: Any, ids: list[int]) -> None:
    """Targeted upsert, additive relations, transaction; preserve book ownership."""
    ids=sorted(set(ids))
    if not ids:
        return
    with db.transaction():
        with db.cursor() as cur:
            cur.execute(CANONICAL,(ids,))
            for name, link, column in TAGS:
                cur.execute(f"""
                  INSERT INTO {name}(name)
                  SELECT DISTINCT tag.item->>'name'
                  FROM jikan_manga_source j
                  CROSS JOIN LATERAL jsonb_array_elements(
                    CASE WHEN jsonb_typeof(j.{column})='array'
                         THEN j.{column} ELSE '[]'::jsonb END) tag(item)
                  WHERE j.mal_id=ANY(%s)
                    AND length(BTRIM(tag.item->>'name'))>0
                  ON CONFLICT(name) DO NOTHING
                """,(ids,))
                cur.execute(f"""
                  INSERT INTO {link}(manga_id,{name}_id)
                  SELECT DISTINCT m.id,t.id
                  FROM jikan_manga_source j
                  JOIN manga m ON m.source_mal_id=j.mal_id
                  CROSS JOIN LATERAL jsonb_array_elements(
                    CASE WHEN jsonb_typeof(j.{column})='array'
                         THEN j.{column} ELSE '[]'::jsonb END) tag(item)
                  JOIN {name} t ON t.name=tag.item->>'name'
                  WHERE j.mal_id=ANY(%s)
                  ON CONFLICT DO NOTHING
                """,(ids,))


def audit_base(db: Any, *, report_path: Path | None = None) -> dict:
    """Require completed initial pass. An incomplete DB is NOT a valid base."""
    report_path=report_path or full.LOGS/"last_sync.json"
    if not report_path.is_file():
        raise ValueError("Initialisation A -> 19 absente : bilan Jikan introuvable")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status")!="CATALOGUE_COMPLETE" or not report.get("canonical_synced"):
        raise ValueError("Catalogue MAL initial non terminé : lancer A -> 19 avant la veille")
    with db.cursor() as cur:
        cur.execute("""
          SELECT (SELECT COUNT(*) FROM jikan_manga_source) AS source_count,
                 (SELECT COUNT(*) FROM manga) AS canonical_count,
                 (SELECT MAX(mal_id) FROM jikan_manga_source) AS max_mal_id,
                 (SELECT COUNT(*) FROM jikan_manga_source j LEFT JOIN manga m
                    ON m.source_mal_id=j.mal_id WHERE m.id IS NULL) AS orphan_source
        """)
        result=cur.fetchone()
    if (not result or result["source_count"]<report.get("unique_ids_in_run",0)
            or result["orphan_source"] or not result["max_mal_id"]):
        raise ValueError("La base MAL n'est plus cohérente ; veille suspendue")
    return dict(result)


def persist_delta(items: list[dict], *, at: str) -> None:
    if not items:
        return
    # Keep updates separate: never overwrite historic manga_page_N.json files.
    UPDATES.mkdir(parents=True,exist_ok=True)
    safe=at.replace(":","-").replace("+","_")
    path=UPDATES/("delta_"+safe+".json")
    temp=path.with_suffix(".json.tmp")
    temp.write_text(json.dumps({"source":"tenrai","items":items},
                               ensure_ascii=False),encoding="utf-8")
    temp.replace(path)


def synchronize(db: Any, *, client: Any = None, newest_cap: int = RECENT_PAGE_CAP,
                rotating: int = ROTATING_PAGES) -> dict:
    if not 1<=newest_cap<=25 or not 0<=rotating<=30:
        raise ValueError("Budgets de veille MAL invalides")
    baseline=audit_base(db)
    with db.cursor() as cur:
        cur.execute(STATE_DDL)
    db.commit()
    with db.cursor() as cur:
        cur.execute("SELECT rolling_page FROM catalogue_lifecycle_state WHERE id=1")
        cursor=int(cur.fetchone()["rolling_page"])
    client=client or requests.Session()
    base=full.base_url()
    pages=[]
    scanned=0
    # Descending pages: only the new head. A bounded cap must NOT claim
    # success if the old baseline boundary was not reached.
    reached_old=False
    last_page=0
    for page in range(1,newest_cap+1):
        if scanned:
            time.sleep(1.1)
        payload=get_page(client,base,page,"desc")
        pages.append(payload)
        scanned+=1
        last_page=payload["pagination"]["last_visible_page"]
        if min(x["mal_id"] for x in payload["data"])<=baseline["max_mal_id"]:
            reached_old=True
            break
        if page>=last_page:
            reached_old=True
            break
    if not reached_old:
        raise ValueError("Trop de nouveaux mangas MAL pour le budget : aucun import partiel")
    # Older slice rotates between runs, allowing detection of corrections and
    # backfilled lower MAL IDs without rescanning the entire catalogue daily.
    next_cursor=cursor
    for _ in range(rotating):
        page=next_cursor if next_cursor<=last_page else 1
        time.sleep(1.1)
        pages.append(get_page(client,base,page,"asc"))
        scanned+=1
        next_cursor=page+1 if page<last_page else 1
    delta,added,updated=changed_items(db,pages)
    rows=[]
    for item in delta:
        row=transform_jikan_item(item)
        if not row or not row.get("title"):
            raise ValueError("Notice MAL modifiée invalide : import refusé")
        row["source_name"]="tenrai"
        rows.append(row)
    persist_delta(delta,at=utcnow()) # checkpoint external source before SQL
    if rows:
        upsert_jikan_manga_batch(db,rows)
        consolidate_changed(db,[r["mal_id"] for r in rows])
    with db.transaction():
        with db.cursor() as cur:
            cur.execute("""
             UPDATE catalogue_lifecycle_state
             SET rolling_page=%s,last_success_at=NOW()
             WHERE id=1
            """,(next_cursor,))
    return {
        "recent_pages":scanned-rotating,"rotating_pages":rotating,
        "max_existing_mal_id_before":baseline["max_mal_id"],
        "new_mal_ids":added,"updated_mal_ids":updated,
        "canonical_upserts":len(rows),
        "next_rolling_page":next_cursor,
        "ids_changed":[r["mal_id"] for r in rows],
        "scope":"NEWEST_AND_ROTATING_PAGES_NOT_WHOLE_CATALOGUE",
    }


def bnf_import_and_review(*, max_files: int = 3, limit: int = 3) -> dict:
    """Import only user-provided official monthly files; plus live SRU queue."""
    from apps.api.app import bnf_batch
    files=[]
    if bnf_files.IMPORTS.is_dir():
        files=sorted(p for p in bnf_files.IMPORTS.iterdir()
                     if p.is_file() and not p.is_symlink()
                     and p.name.lower().endswith(bnf_files.SUPPORTED))[:max_files]
    imported=[]
    if files:
        with get_postgres_connection() as conn:
            for p in files:
                imported.append(bnf_files.ingest_one(p,preview=False,database=conn))
    review=bnf_batch.run_batch(bnf_batch.connect_database,limit=limit)
    return {"monthly_files":imported,"sru":review,
            "note":"BNF_MATCHES_ARE_CANDIDATES_NOT_VERIFIED_OWNERSHIP"}


def run_cycle(*, mal_client: Any = None,
              factory: Callable[...,Any] = get_postgres_connection,
              enrich: bool = True, bnf_runner=bnf_import_and_review,
              mu_runner=mu.run_batch, scrinis_runner=scrinis.run_batch) -> dict:
    LOGS.mkdir(parents=True,exist_ok=True)
    result={"started_at":utcnow(),"status":"RUNNING"}
    with factory() as db:
        with db.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s) AS locked",(ADVISORY_KEY,))
            got=bool(cur.fetchone()["locked"])
        db.commit()
        if not got:
            result["status"]="SKIPPED_ALREADY_RUNNING"
            return result
        try:
            result["mal"]=synchronize(db,client=mal_client)
            if enrich:
                # Source outages do not erase existing data; failures are
                # explicit rather than silently labeled as complete.
                result["scrinis"]=scrinis_runner(factory=factory,limit=8)
                result["mangaupdates"]=mu_runner(factory=factory,limit=5)
                result["bnf"]=bnf_runner(limit=3)
            result["status"]="SUCCESS"
        except Exception as exc:
            # A PostgreSQL statement may have aborted the current
            # transaction. Roll back before releasing the session lock.
            db.rollback()
            result["status"]="FAILED"
            result["error_type"]=type(exc).__name__
            result["error"]=str(exc)[:320]
        finally:
            result["finished_at"]=utcnow()
            temp=LOGS/"last_cycle.tmp"
            temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
            temp.replace(LOGS/"last_cycle.json")
            with db.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)",(ADVISORY_KEY,))
            db.commit()
    return result


def main(argv: list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(description="Mangadvisor catalogue vivant")
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit",action="store_true")
    mode.add_argument("--once",action="store_true")
    mode.add_argument("--daemon",action="store_true")
    mode.add_argument("--status",action="store_true")
    parser.add_argument("--skip-enrichment",action="store_true")
    args=parser.parse_args(argv)
    if args.status:
        path=LOGS/"last_cycle.json"
        print(path.read_text(encoding="utf-8") if path.is_file()
              else "Aucun cycle de veille exécuté.")
        return 0
    if args.audit:
        with get_postgres_connection() as db:
            print(json.dumps(audit_base(db),ensure_ascii=False))
        return 0
    if args.once:
        result=run_cycle(enrich=not args.skip_enrichment)
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        return 0 if result["status"] in ("SUCCESS","SKIPPED_ALREADY_RUNNING") else 2
    while True:
        result=run_cycle(enrich=not args.skip_enrichment)
        print(json.dumps(result,ensure_ascii=False),flush=True)
        # Docker restart policy keeps the opt-in worker alive when Docker starts.
        # No attempt to wake the Windows PC or to work while Docker is stopped.
        time.sleep(DAILY_INTERVAL if result["status"]=="SUCCESS" else 21600)


if __name__=="__main__":
    sys.exit(main())
