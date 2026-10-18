"""Guided manga discovery grounded in catalog tags and known library preferences.

Read-only; no made-up French availability, mood inference, or LLM classification.
"""
from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

discovery_router = APIRouter(prefix="/discovery", tags=["discovery"])

MOODS: dict[str, dict[str, tuple[str, ...]]] = {
    "DARK": {
        "genres": ("Horror", "Suspense"),
        "themes": ("Psychological", "Gore", "Survival"),
    },
    "COMFORT": {
        "genres": ("Slice of Life", "Comedy"),
        "themes": ("Iyashikei", "CGDCT", "Pets", "Childcare"),
    },
    "ACTION": {
        "genres": ("Action", "Adventure"),
        "themes": ("Martial Arts", "Super Power", "Samurai", "Military"),
    },
    "MYSTERY": {
        "genres": ("Mystery", "Suspense"),
        "themes": ("Detective", "Psychological", "Time Travel"),
    },
    "ROMANCE": {
        "genres": ("Romance",),
        "themes": ("Love Polygon",),
    },
    "FANTASY": {
        "genres": ("Fantasy", "Supernatural"),
        "themes": ("Mythology", "Isekai", "Magic"),
    },
}

Mood = Literal["DARK", "COMFORT", "ACTION", "MYSTERY", "ROMANCE", "FANTASY"]
Length = Literal["ANY", "SHORT", "LONG"]


class MoodDiscoveryRequest(BaseModel):
    mood: Mood
    length: Length = "ANY"
    only_finished: bool = False
    use_library: bool = True
    min_score: float = Field(default=6.5, ge=0, le=10)
    limit: int = Field(default=8, ge=1, le=12)


def match_mood(
    item: dict[str, Any], mood: str
) -> dict[str, list[str]]:
    """Only cite catalogued genres/themes, never guess from synopsis/title."""
    chosen = MOODS[mood]
    return {
        kind: [
            name for name in (item.get(kind) or [])
            if isinstance(name, str)
            and name.casefold() in {tag.casefold() for tag in chosen[kind]}
        ]
        for kind in ("genres", "themes")
    }


def preference_overlap(
    item: dict[str, Any], preferences: dict[str, set[str]]
) -> dict[str, list[str]]:
    return {
        kind: [
            name for name in (item.get(kind) or [])
            if isinstance(name, str) and name.casefold() in preferences.get(kind, set())
        ]
        for kind in ("genres", "themes")
    }


def discovery_rank(
    item: dict[str, Any],
    matched_mood: dict[str, list[str]],
    matched_preferences: dict[str, list[str]],
) -> tuple[float, float, int, int]:
    """Deterministic order, not a likelihood, rating or existing engine score."""
    mood_weight = 18 * len(matched_mood["genres"]) + 20 * len(matched_mood["themes"])
    affinity_weight = min(
        24,
        5 * len(matched_preferences["genres"])
        + 7 * len(matched_preferences["themes"]),
    )
    community_rating = float(item.get("score") or 0)
    # Tie breaks: score, catalogue popularity, canonical id.
    return (
        mood_weight + affinity_weight + community_rating * 2,
        community_rating,
        -int(item.get("popularity") or 9999999),
        -int(item["id"]),
    )


def choose_discoveries(
    candidates: list[dict[str, Any]],
    mood: str,
    preferences: dict[str, set[str]],
    limit: int,
) -> list[dict[str, Any]]:
    """Enforce exact mood match and never elevate unsupported candidates."""
    chosen = []
    for item in candidates:
        mood_matches = match_mood(item, mood)
        if not any(mood_matches.values()):
            continue
        affinity_matches = preference_overlap(item, preferences)
        entry = {
            **item,
            "mood_matches": mood_matches,
            "affinity_matches": affinity_matches,
            "ranking_score": None,  # No misleading probability or score.
        }
        chosen.append((discovery_rank(item, mood_matches, affinity_matches), entry))
    chosen.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in chosen[:limit]]


def make_discovery_router(
    connection_factory: Callable[..., Any], user_id: int = 1
) -> APIRouter:
    @discovery_router.post("/mood")
    def discover_by_mood(payload: MoodDiscoveryRequest) -> dict[str, Any]:
        selected = MOODS[payload.mood]
        params: dict[str, Any] = {
            "user_id": user_id,
            "min_score": payload.min_score,
            "mood_genres": [s.lower() for s in selected["genres"]],
            "mood_themes": [s.lower() for s in selected["themes"]],
        }
        restrictions = [
            "COALESCE(m.manga_type, 'Manga') IN ('Manga', 'Manhwa', 'Manhua', 'One-shot')",
            "COALESCE(m.score, 0) >= %(min_score)s",
            """NOT EXISTS (
                SELECT 1 FROM user_manga_library l
                WHERE l.user_id = %(user_id)s AND l.manga_id = m.id
            )""",
            """(
                EXISTS (
                    SELECT 1 FROM manga_genre mg
                    JOIN genre g ON g.id = mg.genre_id
                    WHERE mg.manga_id = m.id
                      AND LOWER(g.name) = ANY(%(mood_genres)s)
                )
                OR EXISTS (
                    SELECT 1 FROM manga_theme mt
                    JOIN theme t ON t.id = mt.theme_id
                    WHERE mt.manga_id = m.id
                      AND LOWER(t.name) = ANY(%(mood_themes)s)
                )
            )""",
        ]
        if payload.only_finished:
            restrictions.append("LOWER(COALESCE(m.status, '')) = 'finished'")
        if payload.length == "SHORT":
            restrictions.append("m.volumes BETWEEN 1 AND 12")
        if payload.length == "LONG":
            restrictions.append("m.volumes >= 13")

        sql = """
            SELECT
                m.id, m.title, m.status, m.volumes, m.chapters,
                m.score::float AS score, m.popularity, m.manga_type,
                COALESCE(ARRAY(
                    SELECT g.name
                    FROM manga_genre mg JOIN genre g ON g.id = mg.genre_id
                    WHERE mg.manga_id = m.id ORDER BY g.name
                ), ARRAY[]::text[]) AS genres,
                COALESCE(ARRAY(
                    SELECT t.name
                    FROM manga_theme mt JOIN theme t ON t.id = mt.theme_id
                    WHERE mt.manga_id = m.id ORDER BY t.name
                ), ARRAY[]::text[]) AS themes
            FROM manga m
            WHERE """ + " AND ".join(restrictions) + """
            ORDER BY m.score DESC NULLS LAST, m.popularity ASC NULLS LAST, m.id ASC
            LIMIT 500
        """
        preference_sql = """
            WITH positive AS (
                SELECT manga_id
                FROM user_manga_library l
                WHERE user_id = %(user_id)s
                  AND library_status NOT IN ('DROPPED','NOT_INTERESTED')
                  AND (
                    is_favorite = TRUE OR user_score >= 7
                    OR (library_status IN ('READ','READING')
                        AND user_score IS NULL)
                  )
            )
            SELECT 'genres' AS kind, LOWER(g.name) AS tag
            FROM positive p JOIN manga_genre mg ON mg.manga_id = p.manga_id
            JOIN genre g ON g.id = mg.genre_id
            UNION
            SELECT 'themes' AS kind, LOWER(t.name) AS tag
            FROM positive p JOIN manga_theme mt ON mt.manga_id = p.manga_id
            JOIN theme t ON t.id = mt.theme_id
        """
        preferences: dict[str, set[str]] = {"genres": set(), "themes": set()}
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                candidates = cur.fetchall()
                if payload.use_library:
                    cur.execute(preference_sql, {"user_id": user_id})
                    for row in cur.fetchall():
                        preferences[row["kind"]].add(row["tag"])

        results = choose_discoveries(candidates, payload.mood, preferences, payload.limit)
        personalized = payload.use_library and bool(
            preferences["genres"] or preferences["themes"]
        )
        return {
            "mood": payload.mood,
            "length": payload.length,
            "only_finished": payload.only_finished,
            "source": "catalog_and_library" if personalized else "catalog_only",
            "personalized": personalized,
            "candidate_count": len(candidates),
            "count": len(results),
            "recommendations": results,
            "note": "Genres/thèmes vérifiés du catalogue ; disponibilité française non vérifiée.",
        }

    return discovery_router
