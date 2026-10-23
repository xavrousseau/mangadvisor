"""Evidence-first candidate ranking and bibliographic quality gates.

Candidate discovery is intentionally distinct from identity confirmation.
No returned score authorizes creation of an owned ISBN or a title alias.
"""
from __future__ import annotations

import re
from typing import Any

from apps.api.app.reconciliation_engine import (
    IDENTITY_CHECKED_ALIAS_SOURCES, title_key,
)
from apps.api.app.bnf_candidate_quality import classify_candidate

# Full words, not arbitrary SQL substring matches (eri != period, fairy != fairyland).
# PostgreSQL uses \m and \M as start/end of a word.
def search_patterns(terms: list[str]) -> list[str]:
    return [r"\m" + re.escape(word) + r"\M" for word in terms
            if re.fullmatch(r"[a-z0-9]{3,35}", word)][:3]


def _titles(candidate: dict[str, Any]) -> list[str]:
    return [str(x) for x in (
        candidate.get("title"), candidate.get("title_english"),
        candidate.get("title_japanese"), candidate.get("wikidata_label_fr"),
    ) if isinstance(x, str) and x.strip()]


def score_candidate(query: str, candidate: dict[str, Any],
                    physical_count: int | None = None) -> dict[str, Any]:
    """Rank search candidates, preserving evidence level and warning reasons.

    - Exact text alone is not identity: collisions may exist.
    - Strong provenance can rank *suggestions* but no ownership assertion.
    - Counts are warning flags, never identity evidence.
    """
    normalized = title_key(query)
    qtokens = set(normalized.split())
    names = _titles(candidate)
    alias_rows = [a for a in candidate.get("matching_alias_sources") or []
                  if isinstance(a, dict) and a.get("alias")]
    exact_primary = any(title_key(x) == normalized for x in names[:3])
    exact_wikidata = (bool(candidate.get("wikidata_label_fr")) and
                     title_key(candidate["wikidata_label_fr"]) == normalized)
    matching_alias = [a for a in alias_rows
                      if title_key(a.get("alias")) == normalized]
    linked = [a for a in matching_alias
              if a.get("source_name") in IDENTITY_CHECKED_ALIAS_SOURCES]
    if exact_primary:
        score, basis = 100, "EXACT_CATALOG_TITLE"
    elif exact_wikidata:
        score, basis = 90, "EXACT_WIKIDATA_LINKED_TITLE"
    elif linked:
        score, basis = 86, "EXACT_SOURCE_CHECKED_ALIAS"
    elif matching_alias:
        score, basis = 60, "EXACT_UNVERIFIED_ALIAS"
    else:
        names += [str(a["alias"]) for a in alias_rows]
        matches = [set(title_key(x).split()) for x in names if x]
        overlap = max((len(qtokens & ts) for ts in matches), default=0)
        coverage = max((len(qtokens & ts)/max(len(ts), 1)
                        for ts in matches),default=0)
        score = min(44, int(18 * overlap / max(len(qtokens), 1) +
                            22 * coverage))
        basis = "WHOLE_WORD_DISCOVERY"
    warnings = []
    kind = str(candidate.get("manga_type") or "").strip().casefold()
    volumes = candidate.get("volumes")
    if kind in ("one-shot", "one shot", "oneshot") and (
        type(physical_count) is int and physical_count > 1
    ):
        warnings.append("ONE_SHOT_VS_PHYSICAL_BOOKS")
        score -= 35
    if kind in ("light novel", "novel") and (
        type(physical_count) is int and physical_count >= 10
    ):
        warnings.append("NOVEL_VS_LARGE_MANGA_COLLECTION")
        score -= 25
    if (type(physical_count) is int and type(volumes) is int and
        volumes > 0 and physical_count > max(10 + volumes, 3 * volumes)):
        warnings.append("CATALOGUE_VOLUME_DISCREPANCY_NOT_IDENTITY_PROOF")
        score -= 20
    if basis == "EXACT_UNVERIFIED_ALIAS":
        warnings.append("ALIAS_PROVENANCE_INSUFFICIENT")
    return {
        "score": max(0, score), "basis": basis,
        "warnings": warnings,
        "identity_confirmed": False,
        "edition_confirmed": False,
        "ownership_confirmed": False,
    }


def rank_candidates(query: str, candidates: list[dict[str, Any]],
                    physical_count: int | None = None,
                    *, total_limited: bool = False,
                    display_limit: int = 20) -> dict[str, Any]:
    ranked = [{**dict(item),
               "ranking":score_candidate(query,item,physical_count)}
              for item in candidates]
    ranked.sort(key=lambda x: (-x["ranking"]["score"],
                              len(title_key(str(x.get("title") or ""))),
                              int(x.get("id") or 0)))
    top = ranked[0]["ranking"]["score"] if ranked else 0
    runner_up = ranked[1]["ranking"]["score"] if len(ranked)>1 else 0
    margin = top - runner_up
    # This is a quality gate for a top-ranked *suggestion*, never auto-linking.
    usable = (not total_limited and top >= 80 and margin >= 15 and
              not ranked[0]["ranking"]["warnings"])
    return {
        "candidates": ranked[:max(1, min(100, display_limit))],
        "candidate_count": len(ranked),
        "candidate_list_truncated": len(ranked) > max(1, min(100, display_limit)),
        "status": ("STRONG_REVIEW_SUGGESTION" if usable else
                   "AMBIGUOUS_OR_INCOMPLETE" if ranked else
                   "NOT_FOUND_IN_LOCAL_CATALOGUE"),
        "confidence_type": "HEURISTIC_RANK_NOT_CALIBRATED_PROBABILITY",
        "top_score": top,
        "runner_up_score": runner_up,
        "ranking_margin": margin,
        "correspondence_certified": False,
        "owned_editions_modified": 0,
    }


def classify_bnf_candidate_for_work(
    record: dict[str, Any], known_work_titles: list[str],
    authors: list[str] | None = None,
) -> dict[str, Any]:
    """Hard-reject distinct titles / non-French notices before ISBN review.

    Even corroborated records remain a *book candidate*, not a certified
    volume or owned physical book.
    """
    evidence = classify_candidate(record, known_work_titles, authors)
    work = evidence["work_status"]
    lang = evidence["language_status"]
    if work == "REJECT_DIFFERENT_WORK":
        category = "EXCLUDE_DIFFERENT_WORK"
    elif work == "REVIEW_DERIVATIVE":
        category = "REVIEW_SEPARATE_DERIVATIVE"
    elif work == "REVIEW_OTHER_TITLE":
        category = "REVIEW_DIFFERENT_SUBTITLE_OR_WORK"
    elif lang == "NON_FRENCH_DECLARED":
        category = "EXCLUDE_NON_FRENCH"
    elif lang != "FRENCH_DECLARED":
        category = "REVIEW_LANGUAGE_UNVERIFIED"
    elif evidence["author_evidence"] == "REVIEW_DIFFERENT_CREDITS":
        category = "REVIEW_AUTHOR_CONFLICT"
    elif (evidence["volume_suggested"] is not None and
          work == "REVIEW_VOLUME_CANDIDATE"):
        category = "POTENTIAL_FRENCH_VOLUME_REVIEW"
    else:
        category = "REVIEW_EDITION_OR_NUMBERING"
    return {
        **evidence,
        "quality_bucket": category,
        "work_identity_confirmed": False,
        "book_assignment_confirmed": False,
        "owned": False,
    }


def summarize_bnf_quality(records: list[dict[str, Any]],
                          work_titles: list[str],
                          authors: list[str] | None = None) -> dict[str, Any]:
    reviewed = [classify_bnf_candidate_for_work(row,work_titles,authors)
                for row in records]
    buckets: dict[str,int] = {}
    for item in reviewed:
        key = item["quality_bucket"]
        buckets[key] = buckets.get(key,0)+1
    return {
        "reviewed_count": len(reviewed),
        "categories": buckets,
        "sample": [{"isbn13": x["isbn13"],"title_fr":x["title_fr"],
                    "quality_bucket":x["quality_bucket"],
                    "volume_suggested":x["volume_suggested"],
                    "source_url":x["source_url"]}
                   for x in reviewed[:12]],
        "automatic_assignment": False,
    }
