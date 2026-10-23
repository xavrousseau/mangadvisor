"""Conservative evidence assessment for manga-work reconciliation.

A title or alias is a discovery clue, never a work identity proof.
Canonical MAL titles, source-scoped aliases, ISBN candidates, confirmed books
and physical ownership are deliberately separate evidence types.
No writes, network access, or provider-specific data inference.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# These source names have an upstream MAL/author cross-check in their importer.
# They still are NOT proof that a physical French edition is owned.
IDENTITY_CHECKED_ALIAS_SOURCES = frozenset({
    "SCRINIS_FR_PRINT", "TENRAI_MAL_TYPED", "WIKIDATA_P4087",
})
DERIVATIVE_TYPES = frozenset({
    "one-shot", "oneshot", "one shot", "light novel", "novel", "doujinshi",
})
DISCOVERY_STOPWORDS = frozenset({
    "the", "des", "les", "and", "pour", "avec", "from", "sous", "manga",
    "tome", "livre", "edition", "éditions", "volumes", "version", "original",
})


def title_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def discovery_terms(value: str) -> list[str]:
    """Bounded search clues, never an equivalence or translation dictionary."""
    tokens = [s for s in title_key(value).split()
              if 3 <= len(s) <= 35 and s not in DISCOVERY_STOPWORDS]
    distinct = list(dict.fromkeys(tokens))
    # Include shorter last tokens for e.g. "Adieu Eri" (MAL: Sayonara Eri).
    return sorted(distinct, key=lambda s: (-len(s), s))[:3]


def alias_records(manga: dict[str, Any], sought_title: str) -> list[dict[str, str]]:
    """Keep source provenance for exact matches, not just opaque alias text."""
    sought = title_key(sought_title)
    records = manga.get("exact_alias_evidence") or []
    if not isinstance(records, list):
        return []
    unique = set()
    result = []
    for alias in records:
        if not isinstance(alias, dict) or title_key(alias.get("alias")) != sought:
            continue
        source = str(alias.get("source_name") or "")[:80]
        source_id = str(alias.get("source_id") or "")[:100]
        key = (source, source_id)
        if key in unique:
            continue
        unique.add(key)
        result.append({
            "source_name": source, "source_id": source_id,
            "evidence_type": ("MAL_OR_AUTHOR_CHECKED_SOURCE" if source in
                              IDENTITY_CHECKED_ALIAS_SOURCES else
                              "UNVERIFIED_SOURCE_ALIAS"),
        })
    return sorted(result, key=lambda x: (x["source_name"], x["source_id"]))[:12]


def assess_work_candidate(
    pending: dict[str, Any], manga: dict[str, Any],
    *, canonically_matched_elsewhere: bool = False,
) -> dict[str, Any]:
    """Return human-readable positive clues and veto/review warnings.

    Contradictions are evidence to review; they do not authorize writes, nor
    definitively prove that a translation/edition is a different work.
    """
    text = str(pending.get("work_declared") or pending.get("entry_title") or "")
    candidate_titles = [
        manga.get("title"), manga.get("title_english"),
        manga.get("title_japanese"),
    ]
    direct = bool(title_key(text)) and any(
        title_key(x) == title_key(text) for x in candidate_titles if x
    )
    aliases = alias_records(manga, text)
    wiki = manga.get("wikidata_label_fr")
    wiki_direct = bool(wiki) and title_key(wiki) == title_key(text)
    alias_match = bool(aliases) or wiki_direct or title_key(text) in {
        title_key(x) for x in (manga.get("exact_aliases") or []) if x
    }
    signals: list[dict[str, str]] = []
    warnings: list[str] = []
    if direct:
        signals.append({"kind": "TITLE", "source": "JIKAN_MAL",
                        "detail": "CANONICAL_TITLE_EQUAL"})
    if wiki_direct:
        signals.append({"kind": "EXTERNAL_ID_LINK", "source": "WIKIDATA_P4087",
                        "detail": "FRENCH_LABEL_FOR_SAME_MAL_ID"})
    if aliases:
        for alias in aliases:
            signals.append({"kind": "ALIAS", "source": alias["source_name"],
                            "detail": alias["evidence_type"]})
        if not direct and not any(a["source_name"] in IDENTITY_CHECKED_ALIAS_SOURCES
                                  for a in aliases):
            warnings.append("ALIAS_UNVERIFIED_OR_UNTRACED")
    elif alias_match and not direct and not wiki_direct:
        warnings.append("ALIAS_UNVERIFIED_OR_UNTRACED")
    if not direct and alias_match and canonically_matched_elsewhere:
        warnings.append("ALIAS_CONFLICTS_WITH_OTHER_CANONICAL_TITLE")
    kind = str(manga.get("manga_type") or "").strip().casefold()
    owned = pending.get("main_volumes")
    known = manga.get("volumes")
    if type(owned) is int and owned > 1 and kind in {"one-shot", "oneshot", "one shot"}:
        warnings.append("ONE_SHOT_VS_MULTIPLE_PHYSICAL_BOOKS")
    if type(owned) is int and type(known) is int and known > 0 and (
        owned > max(known * 3, known + 10)
    ):
        warnings.append("JAPANESE_WORK_COUNT_VS_FRENCH_HOLDINGS_DIFFER")
    # A novel may legitimately be owned; identify different media without
    # assuming the format of a personal inventory entry.
    if kind in DERIVATIVE_TYPES:
        warnings.append("DERIVATIVE_OR_TEXT_WORK_TYPE_REVIEW")
    if not direct and not alias_match:
        signals.append({"kind": "DISCOVERY", "source": "HISTORICAL_IMPORT",
                        "detail": "SAVED_CANDIDATE_NOT_IDENTITY_EVIDENCE"})
        warnings.append("NO_CURRENT_TITLE_OR_ALIAS_EVIDENCE")
    if manga.get("source_mal_id"):
        signals.append({"kind": "SOURCE_ID", "source": "JIKAN_MAL",
                        "detail": "CATALOGUE_IDENTIFIER_NOT_INVENTORY_LINK"})
    risk = ("CONFLICT_REVIEW" if warnings else
            "IDENTITY_EVIDENCE_REVIEW" if direct or alias_match else
            "DISCOVERY_ONLY")
    return {
        "assessment": risk,
        "evidence": signals[:20],
        "warnings": list(dict.fromkeys(warnings)),
        "alias_provenance": aliases,
        "work_identity_confirmed": False,
        "edition_identity_confirmed": False,
        "ownership_confirmed": False,
        "isbn_assigned_to_ownership": False,
        "next_action": ("REVIEW_CONTRADICTIONS" if warnings else
                        "VERIFY_WORK_AND_EDITION" if direct or alias_match else
                        "DISCOVER_EXTERNAL_WORK_IDS"),
    }


def summarize_book_evidence(
    manga_id: int, bnf_rows: list[dict[str, Any]],
    confirmed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """BnF staging and confirmed book tables are different evidence levels."""
    bnf = [x for x in bnf_rows if int(x["manga_id"]) == manga_id]
    registered = [x for x in confirmed_rows if int(x["manga_id"]) == manga_id]
    return {
        "bnf_candidate_isbn_count": len(bnf),
        "bnf_candidate_isbns_sample": [
            {"isbn13": x["isbn13"], "title_fr": x.get("title_fr"),
             "edition_kind_suggested": x.get("edition_kind_suggested"),
             "source_url": x.get("source_url"), "status": "BNF_CANDIDATE_UNVERIFIED"}
            for x in bnf[:3]
        ],
        "registered_french_isbn_count": len(registered),
        "registered_isbns_sample": [
            {"isbn13": x["isbn13"], "status": "CATALOGUE_BOOK_NOT_OWNERSHIP"}
            for x in registered[:3]
        ],
        "candidate_source_truncated": False,
        "ownership_inferred": False,
        "note": "Une notice BnF ou un ISBN enregistres ne prouvent ni l'oeuvre, ni le tome possede.",
    }
