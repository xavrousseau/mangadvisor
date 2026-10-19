"""Read-only evidence diagnostics for the conversational manga advisor.

Metrics are descriptive properties of *returned catalogue rows*. They are
not recommendations success probabilities, ratings of people or inferred
properties of an unobserved collection. No writes or personal-library export.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any


def _tags(row: dict[str, Any]) -> set[str]:
    return {
        kind + ":" + tag.strip().casefold()
        for kind in ("genres", "themes")
        for tag in (row.get(kind) or [])
        if isinstance(tag, str) and tag.strip()
    }


def quality_diagnostic(
    recommendations: list[dict[str, Any]], *,
    examined: int,
    pool_limited: bool,
    personalized: bool,
    mode: str,
) -> dict[str, Any]:
    """Summarize coverage and repetition with explicit data scope.

    Exact duplicate IDs are counted independently, even if their titles differ.
    Pair overlap is a Jaccard similarity over recorded genre/theme tags.
    If the sample has fewer than two items (or no tag evidence), overlap is null
    rather than an invented score of zero.
    """
    tags = [_tags(row) for row in recommendations]
    valid_pairs = [
        len(a & b) / len(a | b)
        for a, b in combinations(tags, 2) if a and b
    ]
    overlap = round(sum(valid_pairs) / len(valid_pairs), 3) if valid_pairs else None
    return {
        "scope": "displayed_catalogue_results_only",
        "mode": mode,
        "examined_count": examined,
        "candidate_pool_capped": pool_limited,
        "returned_count": len(recommendations),
        "unique_manga_count": len({row.get("id") for row in recommendations}),
        "tag_evidence_count": sum(bool(entry) for entry in tags),
        "unique_recorded_tags": len(set().union(*tags)) if tags else 0,
        "mean_pairwise_tag_overlap": overlap,
        "pair_count_compared": len(valid_pairs),
        "affinity_evidence_count": sum(
            bool(row.get("affinity_matches", {}).get("genres")
                 or row.get("affinity_matches", {}).get("themes"))
            for row in recommendations
        ) if personalized else 0,
        "french_isbn_record_count": sum(
            bool(row.get("french_recorded")) for row in recommendations
        ),
        "narrative_clue_evidence_count": sum(
            bool(row.get("narrative_matches")) for row in recommendations
        ),
        "quality_is_not_a_probability": True,
    }
