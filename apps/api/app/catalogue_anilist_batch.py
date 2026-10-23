"""Resume-safe, bounded AniList cross-ID ingestion for the PUBLIC catalogue.

No fuzzy title joins, no edits to manga/Jikan/user_* tables, no automatic
editions. Runs inside the production API container (no pipelines package).
Default is report-only; explicit --run makes the API calls.

AniList currently documents a degraded limit of 30 requests/minute.
We send at most eight MAL IDs per query and pause >= 2.2 seconds.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any, Callable

from fastapi import HTTPException

from apps.api.app.bnf_batch import connect_database
from apps.api.app.catalogue_source_graph import stage_external_facts
from apps.api.app.international_crosswalk import search_anilist_by_mal_ids

SOURCE="ANILIST"
BATCH_SIZE=8
DEFAULT_LIMIT=64
MAX_LIMIT=200
DELAY=2.3
ADVISORY_KEY_1=85470
ADVISORY_KEY_2=10

SCHEMA="""
CREATE TABLE IF NOT EXISTS catalogue_provider_attempt (
  work_id BIGINT NOT NULL REFERENCES catalogue_work(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  status TEXT NOT NULL
    CHECK(status IN ('MATCHED','NOT_RETURNED','PROVIDER_ERROR')),
  attempt_count INTEGER NOT NULL DEFAULT 1 CHECK (attempt_count>=1),
  external_id TEXT,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  next_retry_at TIMESTAMPTZ,
  PRIMARY KEY(work_id, provider)
);
CREATE INDEX IF NOT EXISTS catalogue_provider_attempt_retry_idx
 ON catalogue_provider_attempt(provider,status,next_retry_at);
"""

NEXT_BATCH_SQL="""
SELECT w.id AS work_id,m.source_mal_id AS mal_id
FROM catalogue_work w
JOIN manga m ON m.id=w.legacy_manga_id
LEFT JOIN catalogue_provider_attempt p
  ON p.work_id=w.id AND p.provider='ANILIST'
WHERE w.origin_source='MAL'
  AND (p.work_id IS NULL
       OR (p.status='PROVIDER_ERROR' AND p.next_retry_at<=now()))
ORDER BY m.popularity NULLS LAST, w.id
LIMIT %s
"""
SAVE_ATTEMPT_SQL="""
INSERT INTO catalogue_provider_attempt
  (work_id,provider,status,attempt_count,external_id,checked_at,next_retry_at)
VALUES (%(work_id)s,'ANILIST',%(status)s,1,%(external_id)s,now(),
 CASE WHEN %(status)s='PROVIDER_ERROR' THEN now()+interval '1 hour'
 ELSE NULL END)
ON CONFLICT(work_id,provider) DO UPDATE SET
  status=EXCLUDED.status,
  attempt_count=catalogue_provider_attempt.attempt_count+1,
  external_id=EXCLUDED.external_id,
  checked_at=now(),
  next_retry_at=EXCLUDED.next_retry_at
"""


def ensure_schema(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)


def select_batch(conn: Any, limit: int=BATCH_SIZE) -> list[dict[str,int]]:
    with conn.cursor() as cur:
        cur.execute(NEXT_BATCH_SQL,(max(1,min(BATCH_SIZE,limit)),))
        return [{"work_id":int(x["work_id"]), "mal_id":int(x["mal_id"])}
                for x in cur.fetchall()]


def summarize(conn: Any) -> dict[str,int]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              (SELECT count(*) FROM catalogue_work WHERE origin_source='MAL')
                 AS eligible_works,
              count(*) FILTER (WHERE p.status='MATCHED') AS matched,
              count(*) FILTER (WHERE p.status='NOT_RETURNED') AS not_returned,
              count(*) FILTER (WHERE p.status='PROVIDER_ERROR') AS provider_errors
            FROM catalogue_provider_attempt p WHERE p.provider='ANILIST'
        """)
        row=dict(cur.fetchone())
        return {key:int(value or 0) for key,value in row.items()}


def run_batch(conn: Any, rows: list[dict[str,int]],
              lookup: Callable[[list[int]],dict[str,Any]]=search_anilist_by_mal_ids
              ) -> dict[str,Any]:
    """One network request, exact MAL-ID joins, one atomic database commit."""
    if not rows or len(rows)>BATCH_SIZE:
        raise ValueError("Each AniList request must contain 1-8 work IDs.")
    mal_to_work={r["mal_id"]:r["work_id"] for r in rows}
    result=lookup(list(mal_to_work))
    if not isinstance(result,dict) or not isinstance(result.get("items"),list) or (
        result.get("status") in ("PROVIDER_UNAVAILABLE","NO_VALID_MAL_IDS")
    ):
        raise ValueError("AniList incomplete response: no negative assumptions.")
    by_mal={}
    for item in result["items"]:
        if not isinstance(item,dict):
            raise ValueError("Unexpected AniList entry.")
        mid=item.get("source_mal_id")
        if type(mid) is not int or mid not in mal_to_work:
            # Never trust an unrelated provider ID or title.
            continue
        if mid in by_mal:
            raise ValueError("Duplicate MAL identifier from AniList; no link written.")
        by_mal[mid]=item
    linked=0
    with conn.cursor() as cur:
        for row in rows:
            mid=row["mal_id"]
            item=by_mal.get(mid)
            if item is not None:
                aid=item.get("anilist_id")
                url=item.get("source_url")
                if type(aid) is not int or aid<=0 or url!=(
                    "https://anilist.co/manga/"+str(aid)
                ):
                    raise ValueError("Invalid source proof; abort current batch.")
                outcome=stage_external_facts(
                    conn,mid,provider=SOURCE,source_id=str(aid),
                    url=url,titles=item.get("titles"),relations=item.get("relations"))
                if outcome["status"]!="STAGED_SOURCE_CLAIMS":
                    raise ValueError("Exact MAL identity did not resolve locally.")
                linked+=1
            cur.execute(SAVE_ATTEMPT_SQL,{
                "work_id":row["work_id"],
                "status":"MATCHED" if item else "NOT_RETURNED",
                "external_id":str(item["anilist_id"]) if item else None,
            })
    return {"requested":len(rows),"matched":linked,
            "not_returned":len(rows)-linked,"network_requests":1}


def record_provider_outage(conn: Any, rows: list[dict[str,int]]) -> None:
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(SAVE_ATTEMPT_SQL,{
                "work_id":row["work_id"],"status":"PROVIDER_ERROR",
                "external_id":None,
            })


def main(argv: list[str]|None=None,
         *, sleep:Callable[[float],None]=time.sleep) -> int:
    parser=argparse.ArgumentParser(
        description="Resume-safe AniList public work-ID coverage in bounded batches")
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report-only",action="store_true")
    mode.add_argument("--run",action="store_true")
    parser.add_argument("--limit",type=int,default=DEFAULT_LIMIT)
    args=parser.parse_args(argv)
    if not 1<=args.limit<=MAX_LIMIT:
        parser.error("Use --limit between 1 and 200.")
    with connect_database() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.catalogue_work') IS NOT NULL AS ready")
            if not cur.fetchone()["ready"]:
                parser.error("Run A -> 26 to build the public graph first.")
        if args.report_only:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT to_regclass('public.catalogue_provider_attempt') IS NOT NULL AS ready"
                )
                exists=bool(cur.fetchone()["ready"])
            metrics=(summarize(conn) if exists else
                     {"eligible_works":0,"matched":0,"not_returned":0,"provider_errors":0})
            print(json.dumps({"mode":"READ_ONLY","source":SOURCE,
                              "attempt_table_ready":exists,"metrics":metrics}))
            return 0
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s,%s) AS locked",
                        (ADVISORY_KEY_1,ADVISORY_KEY_2))
            locked=bool(cur.fetchone()["locked"])
        if not locked:
            print(json.dumps({"error":"ALREADY_RUNNING","source":SOURCE}))
            return 3
        try:
            ensure_schema(conn)
            conn.commit()
            total=0
            found=0
            calls=0
            failed=False
            while total<args.limit:
                rows=select_batch(conn,args.limit-total)
                if not rows:
                    break
                try:
                    result=run_batch(conn,rows)
                    conn.commit()
                except (HTTPException,ValueError,TimeoutError,OSError):
                    conn.rollback()
                    record_provider_outage(conn,rows)
                    conn.commit()
                    failed=True
                    break  # Do not hammer a provider during a service outage.
                total+=result["requested"]
                found+=result["matched"]
                calls+=1
                if total<args.limit:
                    sleep(DELAY)
            stats=summarize(conn)
            print(json.dumps({
                "source":SOURCE, "mode":"PARTIAL_PROVIDER_OUTAGE" if failed else "APPLIED",
                "scanned_this_run":total,"matched_this_run":found,
                "requests_this_run":calls,
                "coverage":stats,
                "work_id_joins":"EXACT_MAL_ID_ONLY",
                "french_titles_not_invented":True,
                "user_library_modified":False,"isbn_editions_modified":False,
            },ensure_ascii=False,indent=2))
            return 2 if failed else 0
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s,%s)",
                            (ADVISORY_KEY_1,ADVISORY_KEY_2))
            conn.commit()


if __name__=="__main__":
    raise SystemExit(main())
