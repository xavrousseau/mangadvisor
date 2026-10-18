"""Assisted French-edition enrichment workshop: READ-ONLY candidate triage.

Search a bounded set of titles in BnF, explicitly keep candidates unverified,
and check locally whether an ISBN is already bound to this or another work.
Exact ISBN re-verification and user confirmation use the existing collection API.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from apps.api.app.edition_discovery import (
    search_bnf_by_title, sanitize_title_query,
)

MAX_SEARCH_TITLES = 2
MAX_WORKSHOP_RESULTS = 30
STOPWORDS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "the",
    "a", "an", "of", "and", "edition", "editions", "version", "tome",
    "tomes", "volume", "volumes", "livre", "book", "manga",
    "deluxe", "perfect", "collector", "integrale", "integral",
}


def title_tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", str(text or "").casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return {
        token for token in re.findall(r"[a-z0-9]+", normalized)
        if token not in STOPWORDS and (len(token) >= 3 or token.isdigit())
    }


def title_clue(candidate: str, known_titles: list[str]) -> tuple[int, str]:
    """Title word presence is a sorting hint, NEVER a series match check."""
    tokens = title_tokens(candidate)
    best = 0
    for title in known_titles:
        known = title_tokens(title)
        if known:
            best = max(best, len(tokens.intersection(known)) * 100 // len(known))
    if best == 100:
        return (2, "TITLE_WORDS_PRESENT")
    if best:
        return (1, "SOME_TITLE_WORDS")
    return (0, "NO_TITLE_WORDS")


def select_search_titles(manga: dict[str, Any]) -> list[str]:
    """At most two distinct catalog titles; invalid unsafe CQL excluded."""
    options: list[str] = []
    for key in ("title", "title_english"):
        value = manga.get(key)
        if not isinstance(value, str):
            continue
        try:
            valid = sanitize_title_query(value)
        except ValueError:
            continue
        if valid.casefold() not in {x.casefold() for x in options}:
            options.append(valid)
        if len(options) == MAX_SEARCH_TITLES:
            break
    return options


def build_workshop(
    manga_id: int,
    searched_titles: list[str],
    results: list[dict[str, Any]],
    registrations: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    """Dedupe ISBNs, attach true registration state, no fictional volumes."""
    titles = list(searched_titles)
    deduped: dict[str, dict[str, Any]] = {}
    for result in results:
        for candidate in result.get("items", []):
            if candidate.get("status") != "CANDIDATE_UNCONFIRMED":
                continue
            isbn = str(candidate.get("isbn13") or "")
            if not re.fullmatch(r"[0-9]{13}", isbn) or isbn in deduped:
                continue
            strength, clue = title_clue(candidate.get("title_fr") or "", titles)
            bound = registrations.get(isbn)
            state = (
                "REGISTERED_HERE" if bound and int(bound["manga_id"]) == manga_id
                else "REGISTERED_OTHER" if bound else "TO_VERIFY"
            )
            deduped[isbn] = {
                **candidate,
                "registration_status": state,
                "registered_manga_id": int(bound["manga_id"]) if bound else None,
                "registered_edition_kind": bound.get("edition_kind") if bound else None,
                "registered_volume_number": bound.get("volume_number") if bound else None,
                "title_clue": clue,
                "title_clue_rank": strength,
                "searched_titles": titles,
            }
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            item["registration_status"] != "TO_VERIFY",
            -item["title_clue_rank"],
            str(item.get("title_fr") or "").casefold(),
            item["isbn13"],
        ),
    )
    selected = ordered[:MAX_WORKSHOP_RESULTS]
    return {
        "manga_id": manga_id,
        "searched_titles": titles,
        "items": selected,
        "count": len(selected),
        "to_verify_count": sum(i["registration_status"] == "TO_VERIFY" for i in selected),
        "registered_here_count": sum(i["registration_status"] == "REGISTERED_HERE" for i in selected),
        "registered_other_count": sum(i["registration_status"] == "REGISTERED_OTHER" for i in selected),
        "truncated": len(ordered) > MAX_WORKSHOP_RESULTS,
        "search_errors": errors,
        "first_page_per_title_only": True,
        "exhaustive": False,
        "candidate_only": True,
        "match_verified": False,
        "writes_performed": False,
        "notice": "Suggestions non exhaustives. Les mots du titre sont des indices, jamais une preuve d'appartenance à la série. Vérifier chaque ISBN et confirmer le format et le tome.",
    }


def create_enrichment_router(connection_factory: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/collection", tags=["Atelier d'enrichissement français"])

    @router.get("/mangas/{manga_id}/enrichment")
    def enrich_manga(manga_id: int) -> dict[str, Any]:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, title_english FROM manga WHERE id=%(manga_id)s;",
                    {"manga_id": manga_id},
                )
                manga = cur.fetchone()
        if not manga:
            raise HTTPException(status_code=404, detail="Série introuvable.")

        titles = select_search_titles(manga)
        if not titles:
            raise HTTPException(
                status_code=422,
                detail="Aucun titre admissible pour la recherche BnF. Utilise la recherche manuelle.",
            )

        results = []
        errors = []
        for title in titles:
            try:
                results.append(search_bnf_by_title(title))
            except HTTPException as exc:
                if exc.status_code == 503:
                    errors.append(title)
                else:
                    raise
        if not results:
            raise HTTPException(
                status_code=503,
                detail="Recherche BnF indisponible pour les titres de cette série. Aucun enregistrement effectué.",
            )

        candidates = {
            item["isbn13"] for result in results for item in result.get("items", [])
            if item.get("status") == "CANDIDATE_UNCONFIRMED"
            and re.fullmatch(r"[0-9]{13}", str(item.get("isbn13") or ""))
        }
        registrations: dict[str, dict[str, Any]] = {}
        if candidates:
            with connection_factory() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT isbn13,manga_id,edition_kind,volume_number
                           FROM manga_fr_edition WHERE isbn13=ANY(%(isbns)s);""",
                        {"isbns": sorted(candidates)},
                    )
                    registrations = {r["isbn13"]: r for r in cur.fetchall()}
        return build_workshop(manga_id, titles, results, registrations, errors)

    return router
