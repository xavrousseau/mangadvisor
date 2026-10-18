"""Explications vérifiables des recommandations de Mangadvisor.

Une ressemblance observée avec une source ne constitue PAS une attribution exacte
de points au score. Le classement est toujours calculé par le moteur SQL existant.
"""
from __future__ import annotations

from typing import Any


def build_explanation(
    recommendation: dict[str, Any],
    sources: list[dict[str, Any]],
    attributes: dict[int, dict[str, list[str]]],
    *,
    origin: str,
) -> dict[str, Any]:
    """Construit un contrat de preuve factuel, sans modifier le score.

    Les ressemblances source/candidat sont des intersections de valeurs réellement
    présentes dans les tables manga_genre, manga_theme et manga_demographic.
    Elles n'affirment pas que chaque source a contribué un nombre de points précis.
    """
    candidate_id = int(recommendation["id"])
    candidate = attributes.get(candidate_id, {})
    similarities = []
    source_titles = []
    for source in sources[:10]:
        try:
            source_id = int(source["id"])
        except (KeyError, TypeError, ValueError):
            continue
        title = str(source.get("title") or "").strip()
        if not title:
            continue
        source_titles.append(title)
        tags = attributes.get(source_id, {})
        shared: dict[str, list[str]] = {}
        for kind in ("genres", "themes", "demographics"):
            left = set(candidate.get(kind) or [])
            right = set(tags.get(kind) or [])
            shared[kind] = sorted(left & right)[:5]
        if any(shared.values()):
            similarities.append({
                "manga_id": source_id,
                "title": title,
                "genres": shared["genres"],
                "themes": shared["themes"],
                "demographics": shared["demographics"],
                # Uniquement pour les vraies sources bibliothèque qui portent ces clés.
                "user_score": source.get("user_score"),
                "is_favorite": bool(source.get("is_favorite")),
            })

    # Ordre d'entrée conservé : pour la bibliothèque, c'est l'ordre de priorité
    # sélectionné par le moteur, pas un classement recréé côté interface.
    explanation: dict[str, Any] = {
        "origin": origin,
        "reference_titles": source_titles,
        "source_matches": similarities[:5],
        "shared": {
            "genres": list(recommendation.get("common_genres") or [])[:8],
            "themes": list(recommendation.get("common_themes") or [])[:8],
            "demographics": list(recommendation.get("common_demographics") or [])[:8],
        },
        "community": {
            "source_count": int(recommendation.get("community_source_count") or 0),
            "votes": int(recommendation.get("community_votes") or 0),
            "recommended_from": list(
                recommendation.get("community_recommended_from") or []
            )[:5],
        },
        "cautions": list(recommendation.get("sensitive_mismatches") or [])[:8],
        "score": {
            "final": recommendation.get("recommendation_score"),
            "base": recommendation.get("base_recommendation_score"),
            "goal_bonus": recommendation.get("goal_bonus"),
            "community_signal": recommendation.get("community_score"),
            "editorial_signal": recommendation.get("editorial_score"),
            "quality_signal": recommendation.get("quality_score"),
            "dominant_intent_signal": recommendation.get("dominant_intent_score"),
        },
    }
    return explanation


def get_attribute_rows_sql() -> str:
    """Une requête pour les mangas recommandés et leurs sources, sans N+1."""
    return """
        SELECT m.id,
          ARRAY(SELECT g.name FROM manga_genre mg
                JOIN genre g ON g.id=mg.genre_id
                WHERE mg.manga_id=m.id ORDER BY g.name) AS genres,
          ARRAY(SELECT t.name FROM manga_theme mt
                JOIN theme t ON t.id=mt.theme_id
                WHERE mt.manga_id=m.id ORDER BY t.name) AS themes,
          ARRAY(SELECT d.name FROM manga_demographic md
                JOIN demographic d ON d.id=md.demographic_id
                WHERE md.manga_id=m.id ORDER BY d.name) AS demographics
        FROM manga m
        WHERE m.id = ANY(%(ids)s);
    """


def add_explanations(
    recommendations: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    *,
    origin: str,
    connection_factory: Any,
) -> None:
    """Attache les preuves aux cartes en place ; aucune écriture PostgreSQL."""
    if not recommendations:
        return
    ids = set()
    for item in recommendations + sources:
        try:
            manga_id = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if manga_id > 0:
            ids.add(manga_id)

    if not ids:
        return
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(get_attribute_rows_sql(), {"ids": sorted(ids)})
            rows = cur.fetchall()

    attributes = {
        int(row["id"]): {
            key: list(row.get(key) or [])
            for key in ("genres", "themes", "demographics")
        }
        for row in rows
    }
    for item in recommendations:
        item["explanation"] = build_explanation(
            item, sources, attributes, origin=origin
        )
