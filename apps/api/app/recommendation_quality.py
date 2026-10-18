"""Deterministic, evidence-aware diversification of existing manga recommendations.

This does not recompute the SQL recommendation score. It only selects/reorders
already eligible candidates returned by the engine. Explicit CLOSE mode is
fully backward-compatible with the previous score-based order.
"""
from __future__ import annotations

from typing import Any

BALANCE_MODES = {"CLOSE", "BALANCED", "EXPLORE"}
WEAK_EVIDENCE_WARNING = "limited_attribute_evidence"


def evidence_strength(item: dict[str, Any]) -> str:
    """Distinguish generic demographic/one-genre matches from stronger evidence."""
    themes = int(item.get("common_theme_count") or 0)
    genres = int(item.get("common_genre_count") or 0)
    community = int(item.get("community_source_count") or 0)
    if themes > 0 or genres >= 2 or community > 0:
        return "supported"
    return "limited"


def matched_tags(item: dict[str, Any]) -> frozenset[str]:
    """Use only verified profile-overlap tags (not invented novel genre signals)."""
    result: set[str] = set()
    for attr, kind in (("common_genres", "g"), ("common_themes", "t")):
        values = item.get(attr)
        if not isinstance(values, (list, tuple)):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                result.add(f"{kind}:{value.casefold().strip()}")
    return frozenset(result)


def overlap(first: frozenset[str], second: frozenset[str]) -> float:
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def selection_quality(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Diagnostics describe metadata coverage/diversity, not objective relevance."""
    limited = sum(evidence_strength(item) == "limited" for item in items)
    tag_sets = [matched_tags(item) for item in items]
    pairs = [
        overlap(tag_sets[i], tag_sets[j])
        for i in range(len(items)) for j in range(i + 1, len(items))
        if tag_sets[i] and tag_sets[j]
    ]
    return {
        "count": len(items),
        "limited_evidence_count": limited,
        "repeated_overlap_pairs": sum(value >= 0.75 for value in pairs),
        "comparable_pairs": len(pairs),
    }


def choose_balanced(
    candidates: list[dict[str, Any]], limit: int, mode: str = "CLOSE"
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose a deterministic bounded-diversity top-N from ordered SQL results.

    * CLOSE: same objects in same order, capped to requested limit.
    * BALANCED/EXPLORE: encourage varied, sufficiently evidenced manga while
      retaining top relevance. Never take a candidate >14/28 SQL-score points
      below the best remaining eligible candidate.
    * Existing community, rating, goal bonuses, source ordering are untouched.
    """
    if mode not in BALANCE_MODES:
        raise ValueError("Invalid recommendation balance mode")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    remaining = list(candidates)
    before = selection_quality(remaining[:limit])
    if mode == "CLOSE":
        chosen = remaining[:limit]
    else:
        picked: list[dict[str, Any]] = []
        max_drop, redundancy_weight, weak_penalty = (
            (14.0, 18.0, 12.0) if mode == "BALANCED"
            else (28.0, 32.0, 20.0)
        )
        while remaining and len(picked) < limit:
            best_score = max(float(item.get("recommendation_score") or 0) for item in remaining)
            available = [
                (index, item)
                for index, item in enumerate(remaining)
                if float(item.get("recommendation_score") or 0) >= best_score - max_drop
            ]
            tags_of_picked = [matched_tags(item) for item in picked]

            def priority(candidate: tuple[int, dict[str, Any]]) -> tuple[float, float, int]:
                index, item = candidate
                score = float(item.get("recommendation_score") or 0)
                limited_penalty = weak_penalty if evidence_strength(item) == "limited" else 0.0
                tags = matched_tags(item)
                redundant = max((overlap(tags, tags_prior) for tags_prior in tags_of_picked), default=0.0)
                adjusted = score - limited_penalty - redundancy_weight * redundant
                # Score and previous engine order break ties deterministically.
                return (adjusted, score, -index)

            index, selected = max(available, key=priority)
            picked.append(selected)
            remaining.pop(index)
        chosen = picked

    # A duplicate id can never appear twice in a recommendation set.
    unique: list[dict[str, Any]] = []
    ids: set[int] = set()
    for item in chosen:
        manga_id = item.get("id")
        if isinstance(manga_id, int) and manga_id in ids:
            continue
        if isinstance(manga_id, int):
            ids.add(manga_id)
        unique.append(item)

    return unique, {
        "mode": mode,
        "candidate_pool_count": len(candidates),
        "before": before,
        "after": selection_quality(unique),
        "note": "Diagnostic de couverture des attributs et de répétition, pas une note de pertinence.",
    }
