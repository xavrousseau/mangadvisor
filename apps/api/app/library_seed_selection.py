"""Select representative manga sources without mistaking ownership for a rating.

The only trusted taste evidence is the user's explicit ratings/favorites and
read/reading statuses. Other owned works can broaden catalogue coverage, but
are never upgraded to favorites. All titles/tags come from local SQL.
"""
from __future__ import annotations

from typing import Any

MAX_LIBRARY_SEEDS = 8


def evidence_tier(source: dict[str, Any]) -> int:
    score = source.get("user_score")
    if source.get("is_favorite") is True or (score is not None and float(score) >= 8.5):
        return 3
    # An explicit lukewarm/negative rating overrides a "read" status:
    # reading a book is not proof that the reader enjoyed it.
    if score is not None:
        return 2 if float(score) >= 7 else 0
    if source.get("library_status") in ("READ", "READING"):
        return 2
    if source.get("library_status") == "WANT_TO_READ":
        return 1
    return 0


def evidence_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    tiers = [evidence_tier(source) for source in sources]
    if any(tier >= 2 for tier in tiers):
        level = "RECORDED_TASTE"
        warning = None
    elif any(tier == 1 for tier in tiers):
        level = "OWNERSHIP_AND_INTEREST_ONLY"
        warning = (
            "Les possessions et envies ne prouvent pas une preference de lecture. "
            "Ajoute quelques notes ou favoris pour personnaliser davantage."
        )
    else:
        level = "OWNERSHIP_ONLY"
        warning = (
            "Ces propositions sont explorees a partir des mangas possedes, "
            "pas de gouts confirmes. Note ou ajoute des favoris pour affiner."
        )
    return {"level": level, "warning": warning}


def choose_representative_sources(
    sources: list[dict[str, Any]],
    tags_by_manga: dict[int, set[str]],
) -> tuple[list[dict[str, Any]], str]:
    """Diversify weakly rated collections using *recorded* distinct tags.

    Sources arrive in the existing, weighted SQL order. For three or more
    strongly positive works, keep the previous behavior of using the top five.
    Otherwise protect strong signals and greedily cover distinct genre/theme
    attributes. Equal evidence, tag gains and weights keep original SQL order.
    """
    strong = [source for source in sources if evidence_tier(source) == 3]
    if len(strong) >= 3:
        return strong[:5], "EXPLICIT_FAVORITES_OR_HIGH_RATINGS"

    if len(sources) <= 5:
        return sources[:5], "SMALL_LIBRARY"

    available = list(enumerate(sources))
    picked: list[dict[str, Any]] = []
    seen_tags: set[str] = set()

    def add(index: int, item: dict[str, Any]) -> None:
        picked.append(item)
        seen_tags.update(tags_by_manga.get(int(item["id"]), set()))
        available[:] = [(i, candidate) for i, candidate in available if i != index]

    # A small number of true favorites/high ratings must always be retained.
    for index, item in tuple(available):
        if evidence_tier(item) == 3:
            add(index, item)

    while available and len(picked) < MAX_LIBRARY_SEEDS:
        def priority(pair: tuple[int, dict[str, Any]]) -> tuple[int, int, float, int]:
            index, item = pair
            fresh = tags_by_manga.get(int(item["id"]), set()) - seen_tags
            # Themes tell more about the story than a generic Action genre.
            novelty = sum(2 if tag.startswith("t:") else 1 for tag in fresh)
            return (
                evidence_tier(item),
                novelty,
                float(item.get("positive_weight") or 0),
                -index,
            )

        index, item = max(available, key=priority)
        add(index, item)

    strategy = "RECORDED_ATTRIBUTE_DIVERSITY" if any(tags_by_manga.values()) else "WEIGHTED_FALLBACK_NO_TAGS"
    return picked, strategy
