"""MangaUpdates evidence queue for canonical MAL works, never an unsafe merge.

Search and detail reuse the verified source adapters / rate limiter. A candidate
is linked only if MAL identifier agrees or a title AND independent author
agree. Everything else is stored for review rather than shown as a verified
French edition. This is a bounded, replayable part of the catalogue lifecycle.
"""
from __future__ import annotations

import json
from typing import Any, Callable
from pipelines.engine.scripts import benchmark_manga_sources_v2 as source
from pipelines.engine.scripts.enrich_catalogue_scrinis_fr import compare_authors
from pipelines.engine.src.load.postgres_loader import get_postgres_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_mangaupdates_attempt (
  manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK(status IN (
    'MATCHED','AMBIGUOUS','UNVERIFIED','NO_MATCH','ERROR','AUTHOR_CONFLICT','MAL_CONFLICT')),
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS manga_mangaupdates_evidence (
  manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
  mu_id TEXT NOT NULL CHECK(mu_id ~ '^[1-9][0-9]*$'),
  title TEXT NOT NULL,
  relation TEXT NOT NULL CHECK (relation IN ('MATCHED','REVIEW_REQUIRED')),
  proof TEXT NOT NULL,
  genres TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  themes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  authors TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  source_url TEXT NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY(manga_id,mu_id)
);
"""
SELECT = """
SELECT m.id,m.source_mal_id AS mal_id,m.title,m.title_english,m.title_japanese,
 COALESCE((SELECT array_agg(BTRIM(a.item->>'name'))
   FROM jikan_manga_source s
   CROSS JOIN LATERAL jsonb_array_elements(
    CASE WHEN jsonb_typeof(s.authors_json)='array'
     THEN s.authors_json ELSE '[]'::jsonb END) a(item)
   WHERE s.mal_id=m.source_mal_id
     AND jsonb_typeof(a.item)='object'
     AND length(BTRIM(a.item->>'name'))>1),ARRAY[]::TEXT[]) AS mal_authors
FROM manga m
LEFT JOIN manga_mangaupdates_attempt a ON a.manga_id=m.id
WHERE m.source_mal_id>0 AND
 (a.manga_id IS NULL OR a.checked_at < NOW() -
  CASE WHEN a.status='ERROR' THEN INTERVAL '1 day' ELSE INTERVAL '60 days' END)
ORDER BY CASE WHEN EXISTS (
 SELECT 1 FROM user_manga_inventory_declaration d WHERE d.manga_id=m.id
) THEN 0 ELSE 1 END, m.popularity ASC NULLS LAST, m.id
LIMIT %(limit)s
"""
UPSERT = """
INSERT INTO manga_mangaupdates_evidence(
 manga_id,mu_id,title,relation,proof,genres,themes,authors,source_url)
VALUES (%(manga_id)s,%(mu_id)s,%(title)s,%(relation)s,%(proof)s,
 %(genres)s,%(themes)s,%(authors)s,%(source_url)s)
ON CONFLICT(manga_id,mu_id) DO UPDATE SET
 title=EXCLUDED.title, relation=EXCLUDED.relation, proof=EXCLUDED.proof,
 genres=EXCLUDED.genres,themes=EXCLUDED.themes,authors=EXCLUDED.authors,
 checked_at=NOW()
"""
ATTEMPT = """
INSERT INTO manga_mangaupdates_attempt(manga_id,status)
VALUES(%s,%s)
ON CONFLICT(manga_id) DO UPDATE SET status=EXCLUDED.status,checked_at=NOW()
"""


def candidate_review(work: dict, search: dict, client: Any) -> tuple[str, dict | None]:
    if search.get("status") != "OK":
        return "ERROR", None
    sample = dict(work)
    sample["mal_id"] = work.get("mal_id")
    ranked = source.rank(sample, search.get("candidates") or [])
    if ranked["status"] == "NO_MATCH" or ranked["status"] == "SUGGESTION_ONLY":
        return "NO_MATCH", None
    # Even when one strong candidate exists, a conflicting exact match
    # in the returned list is NOT automatically resolved.
    if ranked["status"] == "AMBIGUOUS":
        return "AMBIGUOUS", None
    hit = (ranked.get("candidates") or [None])[0]
    if not hit or not hit.get("id"):
        return "UNVERIFIED", None
    mal = hit.get("mal_id")
    if mal is not None and str(mal).isdigit() and int(mal) != int(work["mal_id"]):
        return "MAL_CONFLICT", None
    detail = client.call("mangaupdates", "detail", identifier=str(hit["id"]))
    if detail.get("status") != "OK" or not isinstance(detail.get("data"), dict):
        return "ERROR", None
    info = detail["data"]
    if info.get("status") != "OK":
        return "ERROR", None
    # The MU parser may not expose authors; absence is not a match.
    author_result = compare_authors(work.get("mal_authors") or [], info.get("authors") or [])
    same_id = str(mal) == str(work["mal_id"]) if mal is not None else False
    relation = "MATCHED" if same_id or (
        hit["evidence"] == "EXACT_TITLE" and author_result == "MATCH") else "REVIEW_REQUIRED"
    if author_result == "CONFLICT" and not same_id:
        relation = "REVIEW_REQUIRED"
    status = "MATCHED" if relation == "MATCHED" else (
        "AUTHOR_CONFLICT" if author_result == "CONFLICT" else "UNVERIFIED")
    record = {
        "manga_id": work["id"], "mu_id": str(hit["id"]),
        "title": str(info.get("title") or hit["title"])[:200],
        "relation": relation,
        "proof": "MAL_ID" if same_id else "TITLE_AND_AUTHOR" if relation == "MATCHED"
                 else "CANDIDATE_ONLY",
        "genres": [str(x)[:100] for x in (info.get("genres") or [])[:30]],
        "themes": [str(x)[:100] for x in (info.get("themes") or [])[:30]],
        "authors": [str(x)[:150] for x in (info.get("authors") or [])[:20]],
        "source_url": "https://www.mangaupdates.com/series/" + str(hit["id"]),
    }
    return status, record


def run_batch(factory: Callable[..., Any] = get_postgres_connection, *,
              limit: int = 5, client: Any = None, target_ids: list[int] | None = None) -> dict:
    if type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("MangaUpdates : limit doit être 1..25")
    if target_ids is not None and (len(target_ids) > 100 or any(
            type(x) is not int or x <= 0 for x in target_ids)):
        raise ValueError("MangaUpdates : IDs de fiches invalides")
    client = client or source.RateLimitedClient()
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    sql = SELECT
    params: dict[str, Any] = {"limit":limit}
    if target_ids:
        sql = sql.replace("ORDER BY CASE WHEN EXISTS", 
                          "AND m.id=ANY(%(ids)s)\nORDER BY CASE WHEN EXISTS")
        params["ids"] = target_ids
    with factory() as db:
        with db.cursor() as cur:
            cur.execute(sql,params)
            works = list(cur.fetchall())
    stats = {"selected":len(works),"verified":0,"review":0,"unmatched":0,"errors":0}
    for work in works:
        title = str(work.get("title_english") or work.get("title") or "").strip()
        if not title:
            status,record="NO_MATCH",None
        else:
            search = client.call("mangaupdates","search",query=title[:200])
            status,record=candidate_review(work,search,client)
        with factory() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    if record:
                        cur.execute(UPSERT,record)
                    cur.execute(ATTEMPT,(work["id"],status))
        if status=="MATCHED":
            stats["verified"]+=1
        elif status=="ERROR":
            stats["errors"]+=1
            break # stop on upstream failure / rate limit
        elif status=="NO_MATCH":
            stats["unmatched"]+=1
        else:
            stats["review"]+=1
    return stats
