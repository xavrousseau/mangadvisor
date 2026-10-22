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
    run_batch as run_scrinis, french_print_isbns, lookup_work,
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
    return correlate_bnf_scrinis_isbns(
        candidates, supplied, supplier_coverage=coverage)


def correlate_bnf_scrinis_isbns(
    candidates: list[dict[str, Any]], supplied: set[str] | list[str], *,
    supplier_coverage: str,
) -> dict[str, Any]:
    """Compare ISBN sets after independently verifying the source work.

    Positive ISBN overlap is corroboration only. Missing supplier ISBNs never
    prove absence, especially when the source only exposes bounded references.
    """
    supplied = set(supplied)
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
    return {"status": "COMPARED", "supplier_coverage": supplier_coverage,
            "scrinis_french_print_isbns_seen": len(supplied),
            "isbn_correlations": correlations,
            "correlation_counts": dict(Counter(
                row["evidence_status"] for row in correlations))}


def load_work_evidence(
    conn: Any, manga_id: int,
) -> tuple[dict, list[dict], dict | None, list[str]]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT m.id, m.source_mal_id, m.title, m.title_english,
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
               FROM manga m WHERE m.id=%s""", (manga_id,))
        manga = cur.fetchone()
        if manga is None:
            raise ValueError(f"Manga inconnu : {manga_id}")
        cur.execute(
            """SELECT isbn13,title_fr,author_fr,publisher_fr,
                      release_date_text,language_recorded,
                      edition_kind_suggested,source_name,source_url
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
        aliases = []
        cur.execute("SELECT to_regclass('manga_title_alias') AS relation")
        if cur.fetchone()["relation"]:
            cur.execute(
                "SELECT alias FROM manga_title_alias "
                "WHERE manga_id=%s AND language_code='fr' "
                "AND source_name IN "
                "('SCRINIS_FR_PRINT','TENRAI_MAL_TYPED','WIKIDATA_P4087') "
                "ORDER BY alias LIMIT 15", (manga_id,))
            aliases = [r["alias"] for r in cur.fetchall()]
        return manga, candidates, fact, aliases



def scrinis_selection_diagnostics(conn: Any, selected: list[int]) -> dict[int, dict[str, Any]]:
    """Explain supplier zero-selection from its actual SQL eligibility guards."""
    result: dict[int, dict[str, Any]] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('manga_scrinis_fr_attempt') AS relation")
        attempt_available = bool(cur.fetchone()["relation"])
        cur.execute("SELECT to_regclass('manga_title_alias') AS relation")
        aliases_available = bool(cur.fetchone()["relation"])
        for manga_id in selected:
            has_alias = False
            attempt_status = None
            attempt_reason = None
            cooldown_active = False
            if aliases_available:
                cur.execute(
                    """SELECT EXISTS(SELECT 1 FROM manga_title_alias
                       WHERE manga_id=%s AND language_code='fr'
                         AND source_name IN
                         ('SCRINIS_FR_PRINT','TENRAI_MAL_TYPED','WIKIDATA_P4087')
                       ) AS present""", (manga_id,))
                has_alias = bool(cur.fetchone()["present"])
            if attempt_available:
                cur.execute(
                    """SELECT status,reason,checked_at > NOW() -
                          CASE WHEN status IN ('PROVIDER_ERROR','DETAIL_UNAVAILABLE')
                               THEN INTERVAL '1 day' ELSE INTERVAL '45 days' END
                       AS cooldown_active
                       FROM manga_scrinis_fr_attempt WHERE manga_id=%s""",
                    (manga_id,))
                attempt = cur.fetchone()
                if attempt:
                    attempt_status = attempt["status"]
                    attempt_reason = attempt["reason"]
                    cooldown_active = bool(attempt["cooldown_active"])
            result[manga_id] = {
                "already_has_source_french_alias": has_alias,
                "previous_attempt_status": attempt_status,
                "previous_attempt_reason": attempt_reason,
                "attempt_cooldown_active": cooldown_active,
                "source_retry_eligible": not has_alias and not cooldown_active,
            }
    for detail in result.values():
        detail["next_action"] = next_scrinis_action(detail)
    return result


def next_scrinis_action(row: dict[str, Any]) -> str:
    """Safe triage without overriding a retry delay or inventing a match."""
    status = row.get("previous_attempt_status")
    if row.get("already_has_source_french_alias"):
        return "USE_EXISTING_TITLE_EVIDENCE"
    if status == "AMBIGUOUS":
        return "REVIEW_AMBIGUOUS_SOURCE_MATCH"
    if status == "DETAIL_UNAVAILABLE":
        return ("AWAIT_NORMAL_RETRY" if row.get("attempt_cooldown_active")
                else "RETRY_DETAIL_WHEN_ELIGIBLE")
    if row.get("attempt_cooldown_active"):
        return "AWAIT_NORMAL_RETRY"
    return "ELIGIBLE_FOR_NORMAL_PROVIDER_SEARCH"


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


def probe_scrinis_work(
    manga: dict[str, Any], candidates: list[dict[str, Any]], client: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-evaluate one explicitly selected public work WITHOUT SQL writes.

    This manual diagnostic intentionally does not use the persistent 45-day
    attempt cooldown. Normal background enrichment continues to respect it.
    """
    outcome = lookup_work({
        "id": manga["id"], "mal_id": manga["source_mal_id"],
        "title": manga["title"], "title_english": manga.get("title_english"),
        "title_japanese": manga.get("title_japanese"),
        "manga_type": manga.get("manga_type"),
        "mal_authors": manga.get("mal_authors") or [],
    }, client)
    diagnosis = {"status": outcome["status"], "reason": outcome.get("reason")}
    if outcome["status"] != "MATCHED":
        return diagnosis, {"status": "NO_VERIFIED_SCRINIS_WORK", "isbn_correlations": []}
    supplied = set(outcome["french_print_isbns"])
    coverage = ("INCOMPLETE_SUPPLIER_DETAIL" if outcome["book_references_truncated"]
                else "BOUNDED_SUPPLIER_DETAIL")
    diagnosis.update({
        "source_public_id": outcome["scrinis_id"],
        "work_evidence": outcome["work_evidence"],
        "author_evidence": outcome["author_evidence"],
        "french_print_isbns_seen": len(supplied),
        "supplier_coverage": coverage,
    })
    return diagnosis, correlate_bnf_scrinis_isbns(
        candidates, supplied, supplier_coverage=coverage)


def run_pilot(*, limit: int = 10, manga_ids: list[int] | None = None,
              pages: int = 3, scrinis: bool = True,
              bnf: bool = True, probe_scrinis: bool = False) -> dict[str, Any]:
    if probe_scrinis and (manga_ids is None or bnf or scrinis):
        raise ValueError(
            "Probe Scrinis : identifiants explicites et aucun enrichissement fournisseur automatique.")
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
    # Read-only supplier-selection diagnostics are useful even when skipping Scrinis.
    if selected:
        with connect_database() as conn:
            result["scrinis_selection_diagnostics"] = scrinis_selection_diagnostics(conn, selected)
    if bnf and selected:
        result["bnf"] = run_bnf(connect_database, limit=len(selected),
                                refresh=True, target_ids=selected,
                                search=partial(search_bnf_title_pages,max_pages=pages))
    if scrinis and selected:
        # Existing routine saves ONLY independently verified French-title evidence.
        result["scrinis"] = run_scrinis(limit=len(selected), target_ids=selected)
        with connect_database() as conn:
            result["scrinis_selection_diagnostics"] = scrinis_selection_diagnostics(conn, selected)
        result["scrinis"]["selection_note"] = ("0 selected means already-linked French aliases or recent attempts may have been skipped; not an API success check.")
    client = RateLimitedClient() if scrinis or probe_scrinis else None
    reports = []
    probe_blocked = False
    for manga_id in selected:
        with connect_database() as conn:
            manga, raw, fact, aliases = load_work_evidence(conn, manga_id)
        titles = [manga[k] for k in ("title", "title_english", "title_japanese")
                  if manga.get(k)] + aliases
        quality = review(raw, titles)
        probe = None
        if probe_scrinis:
            if probe_blocked:
                probe = {"status": "SKIPPED_PROVIDER_UNAVAILABLE",
                         "reason": "PREVIOUS_PROVIDER_ERROR"}
                correlations = {"status": "NOT_REQUESTED", "isbn_correlations": []}
            else:
                probe, correlations = probe_scrinis_work(manga, quality["candidates"], client)
                if probe["status"] == "PROVIDER_ERROR":
                    probe_blocked = True
        elif scrinis:
            correlations = scrinis_isbn_evidence(fact, quality["candidates"], client)
        else:
            correlations = {"status": "NOT_REQUESTED", "isbn_correlations": []}
        work_report = {
            "manga_id": manga_id, "mal_id": manga["source_mal_id"],
            "title": manga["title"], "trusted_french_aliases": aliases,
            "total_candidates": quality["total_staged"],
            "work_status_counts": quality["work_status_counts"],
            "language_status_counts": quality["language_status_counts"],
            "edition_suggested_counts": quality["edition_suggested_counts"],
            "candidates": quality["candidates"],
            "cross_source": correlations,
        }
        if probe_scrinis:
            work_report["scrinis_probe"] = probe
        reports.append(work_report)
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
    parser.add_argument("--skip-bnf", action="store_true",
                        help="Reutiliser les candidats BnF existants sans requete BnF")
    parser.add_argument("--details", action="store_true",
                        help="Inclure les lignes ISBN dans le rapport JSON")
    parser.add_argument("--report-only", action="store_true",
                        help="Audit des candidats existants, aucune requete fournisseur")
    parser.add_argument("--probe-scrinis", action="store_true",
                        help="Sonder Scrinis en lecture SQL seule pour les mangas explicites, sans cooldown")
    args = parser.parse_args(argv)
    try:
        ids = [int(x.strip()) for x in args.manga_ids.split(",")] if args.manga_ids else None
        if args.probe_scrinis and (args.report_only or not ids):
            raise ValueError("--probe-scrinis demande --manga-ids et exclut --report-only.")
        report = run_pilot(limit=args.limit, manga_ids=ids, pages=args.pages,
                           scrinis=not (args.skip_scrinis or args.report_only or args.probe_scrinis),
                           bnf=not (args.report_only or args.skip_bnf or args.probe_scrinis),
                           probe_scrinis=args.probe_scrinis)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    if not args.details:
        for work in report["works"]:
            work.pop("candidates", None)
            cross = work["cross_source"]
            if "isbn_correlations" in cross:
                cross["isbn_correlations"] = []
        report["detail_level"] = "summary; use --details for ISBN entries"
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    # All-provider failure is an explicit failure, never hidden in summary.
    return 1 if report.get("bnf", {}).get("error", 0) == len(report["selected_ids"]) and report["selected_ids"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
