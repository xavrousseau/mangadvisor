"""Conservative, explainable learning from EXISTING library status reactions.

No new storage, model training, external AI calls, or assumptions about
unrecorded tastes. One refused manga is never evidence to ban its genres.
"""
from __future__ import annotations

from typing import Any

# This aggregates only EXISTING local statuses; not every WANT_TO_READ entry
# necessarily came from the quick feedback button (a manual intention counts).
FEEDBACK_SQL = """
    WITH marked AS (
        SELECT manga_id, library_status
        FROM user_manga_library
        WHERE user_id=%(user_id)s
          AND library_status IN ('WANT_TO_READ','NOT_INTERESTED')
          AND (library_status <> 'WANT_TO_READ'
               OR user_score IS NULL OR user_score >= 7)
    ), tagged AS (
        SELECT m.library_status AS status, 'genres' AS kind,
               LOWER(g.name) AS tag, m.manga_id
        FROM marked m
        JOIN manga_genre mg ON mg.manga_id=m.manga_id
        JOIN genre g ON g.id=mg.genre_id
        UNION ALL
        SELECT m.library_status AS status, 'themes' AS kind,
               LOWER(t.name) AS tag, m.manga_id
        FROM marked m
        JOIN manga_theme mt ON mt.manga_id=m.manga_id
        JOIN theme t ON t.id=mt.theme_id
    )
    SELECT status,kind,tag,COUNT(DISTINCT manga_id)::int AS sources
    FROM tagged
    GROUP BY status,kind,tag
    ORDER BY status,kind,tag
"""


def empty_feedback() -> dict[str, dict[str, dict[str, int]]]:
    return {
        "interested": {"genres": {}, "themes": {}},
        "rejected": {"genres": {}, "themes": {}},
    }


def build_feedback_profile(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    """Read-only conversion of aggregated, already recorded source counts."""
    result = empty_feedback()
    status_map = {"WANT_TO_READ": "interested", "NOT_INTERESTED": "rejected"}
    for row in rows:
        group = status_map.get(row.get("status"))
        kind, tag = row.get("kind"), row.get("tag")
        if group is None or kind not in ("genres", "themes"):
            continue
        if not isinstance(tag, str) or not tag.strip():
            continue
        count = row.get("sources", 0)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            continue
        key = tag.strip().casefold()
        result[group][kind][key] = max(result[group][kind].get(key, 0), count)
    return result


def feedback_evidence(
    item: dict[str, Any],
    profile: dict[str, dict[str, dict[str, int]]],
    strong: dict[str, set[str]],
) -> dict[str, Any]:
    """Soft signals; a single dislike never generalizes to a whole category.

    An INTERESTED status is not an already-read or an actually-loved manga.
    Two or more *different* rejected titles with a shared tag, with NO strong
    positive or interested evidence on that tag, can lower its rank a little.
    It remains eligible when explicitly requested by the user.
    """
    interested: list[str] = []
    recurring: list[str] = []
    for kind in ("genres", "themes"):
        for name in item.get(kind) or []:
            if not isinstance(name, str):
                continue
            tag = name.casefold()
            if profile["interested"][kind].get(tag, 0) > 0:
                interested.append(name)
            if (profile["rejected"][kind].get(tag, 0) >= 2
                    and tag not in strong.get(kind, set())
                    and not profile["interested"][kind].get(tag, 0)):
                recurring.append(name)
    # Keep scoring deliberately small vs explicit mood + ISBN/edition bonuses.
    positive_bonus = min(6, 3 * len(set(interested)))
    cautious_penalty = min(12, 6 * len(set(recurring)))
    return {
        "interested_tags": list(dict.fromkeys(interested))[:3],
        "repeated_rejection_tags": list(dict.fromkeys(recurring))[:3],
        "interest_bonus": positive_bonus,
        "rejection_penalty": cautious_penalty,
    }


def feedback_summary(profile: dict[str, dict[str, dict[str, int]]]) -> dict[str, Any]:
    """Counts refer to tagged status evidence, not unique reacted-to series."""
    return {
        "scope": "existing_library_statuses",
        "interested_tag_count": sum(
            len(profile["interested"][kind]) for kind in ("genres", "themes")
        ),
        "repeated_rejection_tag_count": sum(
            sum(count >= 2 for count in profile["rejected"][kind].values())
            for kind in ("genres", "themes")
        ),
        "single_rejection_never_bans_genres": True,
    }
