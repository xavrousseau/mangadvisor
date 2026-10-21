"""Conservative, incremental Scrinis -> live Mangadvisor FR title enrichment.

Uses existing canonical MAL IDs and source authors; never guesses a title
match from identical names alone. Writes ONLY additive source evidence and
manga_title_alias (used by the actual catalogue UI), never inventory, ISBN
ownership, manga.title, or user associations.

The provider exposes French print editions/ISBNs, but the bibliography
remains SOURCE EVIDENCE: no French edition is automatically owned/linked.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from typing import Any, Callable

from pipelines.engine.scripts import benchmark_manga_sources_v2 as scr
from pipelines.engine.scripts import catalogue_french_matching as fr
from pipelines.engine.src.load.postgres_loader import get_postgres_connection

MAX_BATCH = 100
DEFAULT_BATCH = 20

# Only additive source-owned rows. Keep the existing alias table contract.
SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_title_alias (
 manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
 source_name TEXT NOT NULL,
 source_id TEXT NOT NULL,
 language_code TEXT NOT NULL CHECK (language_code IN ('fr','en','ja','ja-ro','und')),
 alias TEXT NOT NULL CHECK (length(alias) BETWEEN 2 AND 200),
 alias_key TEXT NOT NULL CHECK (length(alias_key) BETWEEN 2 AND 200),
 source_url TEXT NOT NULL,
 first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 PRIMARY KEY (manga_id,source_name,language_code,alias_key)
);
CREATE INDEX IF NOT EXISTS idx_manga_title_alias_key ON manga_title_alias(alias_key);
CREATE TABLE IF NOT EXISTS manga_scrinis_fr_attempt (
 manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
 status TEXT NOT NULL CHECK(status IN (
  'MATCHED','AMBIGUOUS','NO_MATCH','NEEDS_AUTHOR_REVIEW',
  'WORK_TYPE_CONFLICT','AUTHOR_CONFLICT','MAL_ID_CONFLICT','NO_FR_PRINT_ISBN',
  'DETAIL_UNAVAILABLE','PROVIDER_ERROR','MISSING_SOURCE')),
 reason TEXT NOT NULL,
 checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS manga_scrinis_fr_fact (
 manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
 scrinis_public_n BIGINT NOT NULL UNIQUE CHECK(scrinis_public_n>0),
 title_fr TEXT NOT NULL,
 source_url TEXT NOT NULL,
 mal_id INTEGER NOT NULL,
 work_evidence TEXT NOT NULL CHECK(work_evidence IN ('SAME_MAL_ID','EXACT_TITLE_AUTHOR')),
 author_evidence TEXT NOT NULL,
 french_print_isbn_count INTEGER NOT NULL CHECK(french_print_isbn_count>0),
 checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

SELECT_WORK = """
SELECT m.id, m.source_mal_id AS mal_id, m.title, m.title_english,
       m.title_japanese, m.manga_type,
       COALESCE((
         SELECT array_agg(DISTINCT BTRIM(a.item->>'name'))
         FROM jikan_manga_source src
         CROSS JOIN LATERAL jsonb_array_elements(
           CASE WHEN jsonb_typeof(src.authors_json)='array'
                THEN src.authors_json ELSE '[]'::jsonb END
         ) AS a(item)
         WHERE src.mal_id=m.source_mal_id
           AND jsonb_typeof(a.item)='object'
           AND LENGTH(BTRIM(a.item->>'name')) BETWEEN 2 AND 150
       ), ARRAY[]::TEXT[]) AS mal_authors
FROM manga m
LEFT JOIN manga_scrinis_fr_attempt previous ON previous.manga_id=m.id
WHERE m.source_mal_id IS NOT NULL AND m.source_mal_id>0
AND COALESCE(m.manga_type,'Manga') IN ('Manga','Manhwa','Manhua')
AND NOT EXISTS (
 SELECT 1 FROM manga_title_alias a WHERE a.manga_id=m.id
   AND a.language_code='fr'
   AND a.source_name IN ('SCRINIS_FR_PRINT','TENRAI_MAL_TYPED','WIKIDATA_P4087')
)
AND (previous.manga_id IS NULL
     OR previous.checked_at < NOW() -
        CASE WHEN previous.status IN ('PROVIDER_ERROR','DETAIL_UNAVAILABLE')
             THEN INTERVAL '1 day' ELSE INTERVAL '45 days' END)
ORDER BY
  CASE WHEN EXISTS (SELECT 1 FROM user_manga_inventory_declaration d
                    WHERE d.manga_id=m.id) THEN 0
       WHEN EXISTS (SELECT 1 FROM user_manga_library l
                    WHERE l.manga_id=m.id) THEN 1 ELSE 2 END,
  m.popularity ASC NULLS LAST,m.id ASC
LIMIT %(limit)s
"""

UPSERT_ATTEMPT = """
INSERT INTO manga_scrinis_fr_attempt(manga_id,status,reason)
VALUES (%s,%s,%s)
ON CONFLICT(manga_id) DO UPDATE SET
 status=EXCLUDED.status, reason=EXCLUDED.reason, checked_at=NOW()
"""

UPSERT_FACT = """
INSERT INTO manga_scrinis_fr_fact(
 manga_id,scrinis_public_n,title_fr,source_url,mal_id,work_evidence,
 author_evidence,french_print_isbn_count
) VALUES (%(manga_id)s,%(scrinis_id)s,%(title)s,%(url)s,%(mal_id)s,
 %(work_evidence)s,%(author_evidence)s,%(isbn_count)s)
ON CONFLICT(manga_id) DO UPDATE SET
 title_fr=EXCLUDED.title_fr,source_url=EXCLUDED.source_url,
 mal_id=EXCLUDED.mal_id,work_evidence=EXCLUDED.work_evidence,
 author_evidence=EXCLUDED.author_evidence,
 french_print_isbn_count=EXCLUDED.french_print_isbn_count,
 checked_at=NOW()
WHERE manga_scrinis_fr_fact.scrinis_public_n=EXCLUDED.scrinis_public_n
RETURNING manga_id
"""

INSERT_ALIAS = """
INSERT INTO manga_title_alias
(manga_id,source_name,source_id,language_code,alias,alias_key,source_url)
VALUES (%(manga_id)s,'SCRINIS_FR_PRINT',%(scrinis_id)s,'fr',
        %(title)s,%(alias_key)s,%(url)s)
ON CONFLICT (manga_id,source_name,language_code,alias_key) DO NOTHING
RETURNING manga_id
"""


def name_key(value: Any) -> str:
    """Compare transliterated author names independent of surname order."""
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    ascii_name = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(sorted(re.findall(r"[a-z0-9]+", ascii_name)))


def compare_authors(mal: list[str], provider: list[str]) -> str:
    left = {name_key(x) for x in mal if len(name_key(x)) >= 4}
    right = {name_key(x) for x in provider if len(name_key(x)) >= 4}
    if not left or not right:
        return "UNVERIFIED"
    return "MATCH" if left & right else "CONFLICT"


def japanese_work_type_matches(item: dict, detail: dict) -> bool:
    source = fr.work_kind(item.get("manga_type"))
    target = fr.work_kind(detail.get("work_type"))
    # Absent type is unknown, not inferred from the work title.
    if source and target and source != target:
        return False
    return True


def french_print_isbns(detail: dict) -> list[str]:
    return list(dict.fromkeys(
        str(book["isbn13"]) for book in detail.get("book_references") or []
        if isinstance(book, dict) and book.get("isbn13")
        and str(book.get("lang", "")).lower() == "fr"
        and str(book.get("medium", "")).lower() == "print"))


def lookup_work(item: dict, client: Any) -> dict:
    """Find a unique work, verify author or MAL, then French print ISBN."""
    sample = {"title": item.get("title"), "title_english": item.get("title_english"),
              "title_japanese": item.get("title_japanese"), "mal_id": item["mal_id"]}
    search_terms = [
        str(item.get("title_english") or "").strip(),
        str(item.get("title") or "").strip(),
    ]
    tried = []
    decision = None
    for term in search_terms:
        if not term or term in tried or len(term) > 200:
            continue
        tried.append(term)
        result = client.call("scrinis", "search", query=term)
        if result.get("status") != "OK":
            return {"status": "PROVIDER_ERROR", "reason": result.get("status") or "UNKNOWN"}
        decision = scr.rank(sample, result.get("candidates") or [])
        if decision["status"] in ("AMBIGUOUS", "SAME_MAL_ID", "EXACT_TITLE"):
            break
    if decision is None:
        return {"status": "NO_MATCH", "reason": "NO_SEARCH_TERMS"}
    if decision["status"] == "AMBIGUOUS":
        return {"status": "AMBIGUOUS", "reason": "MULTIPLE_PLAUSIBLE_WORKS"}
    if decision["status"] not in ("SAME_MAL_ID", "EXACT_TITLE"):
        return {"status": "NO_MATCH", "reason": "NO_EXACT_WORK_EVIDENCE"}
    selected = decision.get("candidates") or []
    if not selected:
        return {"status": "NO_MATCH", "reason": "NO_CANDIDATES"}
    first = selected[0]
    if not first.get("id"):
        return {"status": "MISSING_SOURCE", "reason": "NO_SCRINIS_PUBLIC_ID"}
    # An explicit supplier MAL ID disagreeing with ours is definitive negative
    # evidence, even when an identical author and title are present.
    external_mal = first.get("mal_id")
    if external_mal is not None and str(external_mal).isdigit() and (
            int(external_mal) != int(item["mal_id"])):
        return {"status": "MAL_ID_CONFLICT", "reason": "SUPPLIER_MAL_ID_DIFFERENT"}
    detail_result = client.call("scrinis", "detail", identifier=first["id"])
    if detail_result.get("status") != "OK":
        return {"status": "DETAIL_UNAVAILABLE",
                "reason": detail_result.get("status") or "UNKNOWN"}
    detail = detail_result.get("data") or {}
    if detail.get("status") != "OK" or str(detail.get("id")) != str(first["id"]):
        return {"status": "DETAIL_UNAVAILABLE", "reason": "DETAIL_ID_MISMATCH"}
    # Search-level formats sometimes identify derivatives more precisely
    # than the series detail; reject either source of type conflict.
    if not japanese_work_type_matches(item, {**detail,
            "work_type": detail.get("work_type") or first.get("format")}):
        return {"status": "WORK_TYPE_CONFLICT", "reason": "MANGA_VS_DERIVATIVE"}
    author_check = compare_authors(item.get("mal_authors") or [], detail.get("authors") or [])
    if author_check == "CONFLICT":
        return {"status": "AUTHOR_CONFLICT", "reason": "MAL_AND_SCRINIS_DIFFERENT_AUTHORS"}
    same_mal = first["evidence"] == "SAME_MAL_ID"
    if not same_mal and author_check != "MATCH":
        return {"status": "NEEDS_AUTHOR_REVIEW", "reason": "EXACT_TITLE_WITHOUT_AUTHOR_CORROBORATION"}
    isbns = french_print_isbns(detail)
    if not isbns:
        return {"status": "NO_FR_PRINT_ISBN", "reason": "NO_VERIFIED_FRENCH_PRINT_ISBN_IN_FETCHED_DETAIL"}
    title = str(detail.get("title") or "").strip()
    if len(title) < 2 or len(title) > 200:
        return {"status": "MISSING_SOURCE", "reason": "NO_USABLE_SCRINIS_SERIES_TITLE"}
    alias_key = fr.normalized(title)[:200]
    if len(alias_key) < 2:
        return {"status": "MISSING_SOURCE", "reason": "INVALID_FRENCH_TITLE_KEY"}
    return {
        "status": "MATCHED", "reason": "SOURCE_CONFIRMED", "title": title,
        "scrinis_id": str(first["id"]), "mal_id": int(item["mal_id"]),
        "work_evidence": "SAME_MAL_ID" if same_mal else "EXACT_TITLE_AUTHOR",
        "author_evidence": author_check, "isbn_count": len(isbns),
        "url": "https://scrin.is/api/v1/series/" + str(first["id"]),
        "manga_id": int(item["id"]),
        "alias_key": alias_key,
    }


def save_one(conn: Any, manga_id: int, result: dict) -> str:
    """Commit ONLY provable source metadata and own attempt; no ownership."""
    with conn.transaction():
        with conn.cursor() as cur:
            status = result["status"]
            if status != "MATCHED":
                cur.execute(UPSERT_ATTEMPT, (manga_id, status, result["reason"]))
                return status
            # Prevent two MAL works from silently claiming one Scrinis ID.
            cur.execute("SELECT manga_id FROM manga_scrinis_fr_fact WHERE scrinis_public_n=%s",
                        (int(result["scrinis_id"]),))
            occupied = cur.fetchone()
            if occupied and int(occupied["manga_id"]) != manga_id:
                cur.execute(UPSERT_ATTEMPT, (
                    manga_id, "AMBIGUOUS", "SCRINIS_ID_LINKED_TO_ANOTHER_MAL_WORK"))
                return "AMBIGUOUS"
            cur.execute(UPSERT_FACT, result)
            stored = cur.fetchone()
            if not stored:
                cur.execute(UPSERT_ATTEMPT, (manga_id, "AMBIGUOUS", "SCRINIS_FACT_DIFFERENT_ID"))
                return "AMBIGUOUS"
            if len(result["alias_key"]) < 2:
                cur.execute(UPSERT_ATTEMPT, (manga_id, "MISSING_SOURCE", "INVALID_TITLE_KEY"))
                return "MISSING_SOURCE"
            cur.execute(INSERT_ALIAS, result)
            new = cur.fetchone() is not None
            cur.execute(UPSERT_ATTEMPT, (manga_id, "MATCHED", result["work_evidence"]))
            return "NEW_FR_ALIAS" if new else "ALREADY_PRESENT"


def run_batch(factory: Callable[..., Any] = get_postgres_connection, *,
              limit: int = DEFAULT_BATCH, client: Any = None) -> dict[str, Any]:
    if type(limit) is not int or not 1 <= limit <= MAX_BATCH:
        raise ValueError("Choisir un lot de 1 à 100 œuvres.")
    client = client or scr.RateLimitedClient()
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    with factory() as conn, conn.cursor() as cur:
        cur.execute(SELECT_WORK, {"limit": limit})
        targets = list(cur.fetchall())
    report: dict[str, Any] = {"selected": len(targets),
        "source": "SCRINIS_FR_PRINT", "new_french_aliases": 0,
        "matched_sources": 0, "review_needed": 0, "provider_errors": 0,
        "no_match": 0, "status_counts": {}}
    for row in targets:
        outcome = lookup_work(row, client)
        with factory() as conn:
            status = save_one(conn, int(row["id"]), outcome)
        counts = report["status_counts"]
        counts[status] = counts.get(status, 0) + 1
        if status == "NEW_FR_ALIAS":
            report["new_french_aliases"] += 1
        if status in ("NEW_FR_ALIAS", "ALREADY_PRESENT"):
            report["matched_sources"] += 1
        elif status in ("PROVIDER_ERROR", "DETAIL_UNAVAILABLE"):
            report["provider_errors"] += 1
        elif status == "NO_MATCH":
            report["no_match"] += 1
        else:
            report["review_needed"] += 1
        print(f"[{report['matched_sources']+report['review_needed']+report['provider_errors']+report['no_match']}/{len(targets)}] "
              f"MAL {row['mal_id']}: {status}", flush=True)
        if status == "PROVIDER_ERROR":
            # Respect the public API if rate-limited/unavailable.
            print("Scrinis non disponible : arrêt du lot sans relancer massivement.", flush=True)
            break
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrichir réellement le catalogue FR via Scrinis, sans deviner les œuvres")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH)
    args = parser.parse_args(argv)
    print("Cible PostgreSQL : manga + jikan_manga_source ; ajout d'alias vérifiés uniquement.")
    print("Titres seuls envoyés au fournisseur ; jamais de données de mangathèque.")
    result = run_batch(limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["provider_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
