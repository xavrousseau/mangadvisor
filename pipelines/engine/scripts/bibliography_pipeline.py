"""Small, resumable French bibliography pilot: BnF -> Scrinis -> evidence report.

ONLY BnF staging and existing vetted Scrinis title aliases may be written.
Never creates confirmed editions or user possessions. Cross-source ISBN
corroboration is reported, NOT automatically approved or inserted.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from functools import partial
from typing import Any

from apps.api.app.bnf_batch import (
    connect_database, run_batch as run_bnf, WORK_SQL,
)
from apps.api.app.bnf_candidate_review import review
from apps.api.app.edition_discovery import search_bnf_title_pages
from pipelines.engine.scripts.enrich_catalogue_scrinis_fr import (
    run_batch as run_scrinis, french_print_isbns,
)
from pipelines.engine.scripts.benchmark_manga_sources_v2 import RateLimitedClient

MAX_PILOT = 10


def scrinis_isbn_evidence(
    scrinis_fact: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    client: Any,
) -> dict[str, Any]:
    """Use only supplier-MAL corroborated facts, never merely similar titles."""
    if not scrinis_fact:
        return {"status": "NO_VERIFIED_SCRINIS_WORK", "isbn_correlations": []}
    source_id = str(scrinis_fact["scrinis_public_n"])
    result = client.call("scrinis", "detail", identifier=source_id)
    if result.get("status") != "OK":
        return {"status": "SCRINIS_DETAIL_UNAVAILABLE",
                "supplier_status": result.get("status"), "isbn_correlations": []}
    detail = result.get("data") or {}
    if detail.get("status") != "OK" or str(detail.get("id")) != source_id:
        return {"status": "SCRINIS_ID_MISMATCH", "isbn_correlations": []}
    if detail.get("book_references_truncated"):
        coverage = "INCOMPLETE_SUPPLIER_DETAIL"
    else:
        coverage = "BOUNDED_SUPPLIER_DETAIL"
    # Preserve source language and print-medium requirements exactly.
    supplied = set(french_print_isbns(detail))
    correlations = []
    for candidate in candidates:
        if candidate["work_status"] == "REJECT_DIFFERENT_WORK":
            state = "DIFFERENT_WORK"
        elif candidate["language_status"] != "FRENCH_DECLARED":
            state = "LANGUAGE_REVIEW"
        elif candidate["work_status"] == "REVIEW_DERIVATIVE":
            state = "DERIVATIVE_REVIEW"
        elif candidate["isbn13"] in supplied:
            state = "ISBN_IN_BOTH_SOURCES"
        else:
            state = "BNF_ONLY_NOT_PROOF_OF_ABSENCE"
        correlations.append({"isbn13": candidate["isbn13"],
                             "evidence_status": state})
    return {"status": "COMPARED", "supplier_coverage": coverage,
            "scrinis_french_print_isbns_seen": len(supplied),
            "isbn_correlations": correlations,
            "correlation_counts": dict(Counter(
                row["evidence_status"] for row in correlations))}


def load_work_evidence(conn: Any, manga_id: int) -> tuple[dict, list[dict], dict | None]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, source_mal_id, title, title_english, title_japanese "
            "FROM manga WHERE id=%s", (manga_id,))
        manga = cur.fetchone()
        if manga is None:
            raise ValueError(f"Manga inconnu : {manga_id}")
        cur.execute(
            """SELECT isbn13,title_fr,publisher_fr,language_recorded,
                      edition_kind_suggested,source_url
               FROM manga_bnf_candidate WHERE manga_id=%s ORDER BY isbn13""",
            (manga_id,))
        candidates = list(cur.fetchall())
        # Legacy installations may not yet have the Scrinis evidence table.
        cur.execute("SELECT to_regclass('manga_scrinis_fr_fact') AS relation")
        exists = cur.fetchone()["relation"]
        fact = None
        if exists:
            cur.execute(
                """SELECT scrinis_public_n, work_evidence, author_evidence
                   FROM manga_scrinis_fr_fact WHERE manga_id=%s""", (manga_id,))
            fact = cur.fetchone()
        return manga, candidates, fact


def select_ids(conn: Any, *, limit: int, manga_ids: list[int] | None) -> list[int]:
    if manga_ids is not None:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM manga WHERE id=ANY(%s)", (manga_ids,))
            present = {row["id"] for row in cur.fetchall()}
        if present != set(manga_ids):
            raise ValueError("Certains identifiants de manga sont absents du catalogue.")
        return manga_ids
    # First pilot: prioritise explicitly inventoried works, then library,
    # then popular works, exactly as the existing BnF work selector does.
    with conn.cursor() as cur:
        cur.execute(WORK_SQL.replace("LIMIT %(limit)s", "LIMIT %(limit)s"),
                    {"limit": limit, "refresh": True})
        return [int(row["id"]) for row in cur.fetchall()]


def run_pilot(*, limit: int = 10, manga_ids: list[int] | None = None,
              pages: int = 3, scrinis: bool = True,
              bnf: bool = True) -> dict[str, Any]:
    if not 1 <= limit <= MAX_PILOT or not 1 <= pages <= 10:
        raise ValueError("Lot maximum 10 mangas ; pagination BnF 1 à 10.")
    if manga_ids is not None and (
        not manga_ids or len(manga_ids) > MAX_PILOT
        or len(set(manga_ids)) != len(manga_ids)
        or any(type(x) is not int or x < 1 for x in manga_ids)
    ):
        raise ValueError("Liste de mangas invalide (1 à 10 identifiants uniques).")
    if pages > 3 and (manga_ids is None or len(manga_ids) != 1):
        raise ValueError("Au-delà de 3 pages, cibler un seul manga explicitement.")
    with connect_database() as conn:
        selected = select_ids(conn, limit=limit, manga_ids=manga_ids)
    result: dict[str, Any] = {"selected_ids": selected,
                              "confirmed_editions_written": 0,
                              "user_inventory_written": 0}
    if bnf and selected:
        result["bnf"] = run_bnf(connect_database, limit=len(selected),
                                refresh=True, target_ids=selected,
                                search=partial(search_bnf_title_pages,max_pages=pages))
    if scrinis and selected:
        # Existing routine saves ONLY independently verified French-title evidence.
        result["scrinis"] = run_scrinis(limit=len(selected), target_ids=selected)
    client = RateLimitedClient() if scrinis else None
    reports = []
    for manga_id in selected:
        with connect_database() as conn:
            manga, raw, fact = load_work_evidence(conn, manga_id)
        titles = [manga[k] for k in ("title", "title_english", "title_japanese")
                  if manga.get(k)]
        quality = review(raw, titles)
        correlations = (
            scrinis_isbn_evidence(fact, quality["candidates"], client)
            if scrinis else {"status": "NOT_REQUESTED", "isbn_correlations": []}
        )
        reports.append({"manga_id": manga_id, "mal_id": manga["source_mal_id"],
                        "title": manga["title"], "total_candidates": quality["total_staged"],
                        "work_status_counts": quality["work_status_counts"],
                        "language_status_counts": quality["language_status_counts"],
                        "edition_suggested_counts": quality["edition_suggested_counts"],
                        "cross_source": correlations})
    result["works"] = reports
    result["notice"] = (
        "ISBN candidats, non certifies. Un ISBN commun a BnF et Scrinis est "
        "corrobore, pas attribue automatiquement a une edition ou une possession.")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pilote bibliographie FR BnF + Scrinis")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--manga-ids", default="",
                        help="Identifiants internes separes par des virgules")
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--skip-scrinis", action="store_true")
    parser.add_argument("--report-only", action="store_true",
                        help="Audit des candidats existants, aucune requete fournisseur")
    args = parser.parse_args(argv)
    try:
        ids = [int(x.strip()) for x in args.manga_ids.split(",")] if args.manga_ids else None
        report = run_pilot(limit=args.limit, manga_ids=ids, pages=args.pages,
                           scrinis=not (args.skip_scrinis or args.report_only),
                           bnf=not args.report_only)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    # All-provider failure is an explicit failure, never hidden in summary.
    return 1 if report.get("bnf", {}).get("error", 0) == len(report["selected_ids"]) and report["selected_ids"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
