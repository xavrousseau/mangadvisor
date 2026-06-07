from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"


NEW_RECOMMEND_FROM_LIBRARY = r'''
LIBRARY_RECOMMENDATION_GOALS = {
    "SIMILAR_SAFE",
    "READ_NEXT",
    "SHORT_FINISHED",
}


def normalize_library_recommendation_goal(value: str | None) -> str:
    goal = (value or "SIMILAR_SAFE").strip().upper()

    if goal not in LIBRARY_RECOMMENDATION_GOALS:
        return "SIMILAR_SAFE"

    return goal


def fetch_manga_metadata_for_recommendations(
    manga_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not manga_ids:
        return {}

    sql = """
        SELECT
            id,
            status,
            volumes,
            chapters,
            popularity,
            score::float AS score
        FROM manga
        WHERE id = ANY(%(manga_ids)s);
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"manga_ids": manga_ids})
            rows = cur.fetchall()

    return {row["id"]: row for row in rows}


def compute_library_goal_bonus(
    recommendation: dict[str, Any],
    recommendation_goal: str,
) -> float:
    goal = normalize_library_recommendation_goal(recommendation_goal)

    status = recommendation.get("status")
    volumes = recommendation.get("volumes")
    chapters = recommendation.get("chapters")
    manga_score = recommendation.get("score")
    popularity = recommendation.get("popularity")
    community_source_count = recommendation.get("community_source_count") or 0
    sensitive_mismatch_count = recommendation.get("sensitive_mismatch_count") or 0

    bonus = 0.0

    if goal == "SIMILAR_SAFE":
        if community_source_count >= 2:
            bonus += 8
        elif community_source_count == 1:
            bonus += 4

        if recommendation.get("common_demographic_count", 0) > 0:
            bonus += 6

        if sensitive_mismatch_count > 0:
            bonus -= sensitive_mismatch_count * 8

        if status in ("On Hiatus", "Discontinued"):
            bonus -= 12

    elif goal == "READ_NEXT":
        if status == "Finished":
            bonus += 10
        elif status == "Publishing":
            bonus += 6
        elif status == "On Hiatus":
            bonus -= 12
        elif status == "Discontinued":
            bonus -= 20

        if manga_score is not None:
            if float(manga_score) >= 8.5:
                bonus += 8
            elif float(manga_score) >= 8.0:
                bonus += 5
            elif float(manga_score) < 7.2:
                bonus -= 8

        if popularity is not None:
            if int(popularity) <= 100:
                bonus += 5
            elif int(popularity) <= 500:
                bonus += 2

        if community_source_count >= 2:
            bonus += 6
        elif community_source_count == 1:
            bonus += 3

        if sensitive_mismatch_count > 0:
            bonus -= sensitive_mismatch_count * 5

    elif goal == "SHORT_FINISHED":
        if status != "Finished":
            bonus -= 100
        else:
            bonus += 20

        if volumes is None:
            bonus -= 8
        else:
            volumes_int = int(volumes)

            if volumes_int <= 12:
                bonus += 35
            elif volumes_int <= 25:
                bonus += 25
            elif volumes_int <= 40:
                bonus += 10
            else:
                bonus -= 35

        if chapters is not None:
            chapters_int = int(chapters)

            if chapters_int <= 100:
                bonus += 8
            elif chapters_int > 250:
                bonus -= 12

        if manga_score is not None and float(manga_score) >= 8.0:
            bonus += 5

        if status in ("On Hiatus", "Discontinued"):
            bonus -= 50

        if sensitive_mismatch_count > 0:
            bonus -= sensitive_mismatch_count * 6

    return round(bonus, 1)


@app.post("/recommendations/library")
def recommend_from_library(
    payload: LibraryRecommendationRequest,
) -> dict[str, Any]:
    """
    Recommande des mangas à partir de la bibliothèque utilisateur.

    V0.8.3 :
    - conserve la pondération bibliothèque V0.8.2 ;
    - ajoute un objectif de recommandation :
        SIMILAR_SAFE, READ_NEXT, SHORT_FINISHED ;
    - ajuste le classement final selon l'objectif ;
    - conserve le résumé de profil bibliothèque.
    """
    recommendation_goal = normalize_library_recommendation_goal(
        getattr(payload, "recommendation_goal", "SIMILAR_SAFE")
    )

    positive_sources_sql = """
        WITH weighted_sources AS (
            SELECT
                m.id,
                m.title,
                m.popularity,
                l.library_status,
                l.user_score::float AS user_score,
                l.is_favorite,
                l.updated_at,

                (
                    CASE
                        WHEN l.library_status = 'READING' THEN 3.5
                        WHEN l.library_status = 'READ' THEN 3.0
                        WHEN l.library_status = 'WANT_TO_READ' THEN 1.5
                        WHEN l.library_status = 'OWNED' THEN 1.0
                        ELSE 0.0
                    END

                    + CASE
                        WHEN l.is_favorite = TRUE THEN 4.0
                        ELSE 0.0
                      END

                    + CASE
                        WHEN l.user_score >= 9 THEN 4.0
                        WHEN l.user_score >= 8.5 THEN 3.5
                        WHEN l.user_score >= 8 THEN 3.0
                        WHEN l.user_score >= 7 THEN 2.0
                        WHEN l.user_score >= 6 THEN 0.5
                        WHEN l.user_score IS NULL THEN 0.0
                        ELSE -2.0
                      END
                )::float AS positive_weight

            FROM user_manga_library l
            JOIN manga m
                ON m.id = l.manga_id

            WHERE l.user_id = %(user_id)s
              AND l.library_status NOT IN ('DROPPED', 'NOT_INTERESTED')
        )

        SELECT
            id,
            title,
            library_status,
            user_score,
            is_favorite,
            positive_weight,
            popularity
        FROM weighted_sources
        WHERE positive_weight > 0

        ORDER BY
            positive_weight DESC,
            is_favorite DESC,
            user_score DESC NULLS LAST,
            updated_at DESC,
            popularity ASC NULLS LAST

        LIMIT 10;
    """

    all_library_ids_sql = """
        SELECT manga_id
        FROM user_manga_library
        WHERE user_id = %(user_id)s;
    """

    status_counts_sql = """
        SELECT
            library_status,
            COUNT(*)::int AS count
        FROM user_manga_library
        WHERE user_id = %(user_id)s
        GROUP BY library_status
        ORDER BY library_status;
    """

    profile_tags_sql = """
        WITH weighted_sources AS (
            SELECT
                l.manga_id,

                (
                    CASE
                        WHEN l.library_status = 'READING' THEN 3.5
                        WHEN l.library_status = 'READ' THEN 3.0
                        WHEN l.library_status = 'WANT_TO_READ' THEN 1.5
                        WHEN l.library_status = 'OWNED' THEN 1.0
                        ELSE 0.0
                    END

                    + CASE
                        WHEN l.is_favorite = TRUE THEN 4.0
                        ELSE 0.0
                      END

                    + CASE
                        WHEN l.user_score >= 9 THEN 4.0
                        WHEN l.user_score >= 8.5 THEN 3.5
                        WHEN l.user_score >= 8 THEN 3.0
                        WHEN l.user_score >= 7 THEN 2.0
                        WHEN l.user_score >= 6 THEN 0.5
                        WHEN l.user_score IS NULL THEN 0.0
                        ELSE -2.0
                      END
                )::float AS positive_weight

            FROM user_manga_library l

            WHERE l.user_id = %(user_id)s
              AND l.library_status NOT IN ('DROPPED', 'NOT_INTERESTED')
        ),

        filtered_sources AS (
            SELECT
                manga_id,
                positive_weight
            FROM weighted_sources
            WHERE positive_weight > 0
        ),

        profile_attributes AS (
            SELECT
                'genre' AS attribute_type,
                g.name,
                fs.manga_id,
                fs.positive_weight
            FROM filtered_sources fs
            JOIN manga_genre mg
                ON mg.manga_id = fs.manga_id
            JOIN genre g
                ON g.id = mg.genre_id

            UNION ALL

            SELECT
                'theme' AS attribute_type,
                t.name,
                fs.manga_id,
                fs.positive_weight
            FROM filtered_sources fs
            JOIN manga_theme mt
                ON mt.manga_id = fs.manga_id
            JOIN theme t
                ON t.id = mt.theme_id

            UNION ALL

            SELECT
                'demographic' AS attribute_type,
                d.name,
                fs.manga_id,
                fs.positive_weight
            FROM filtered_sources fs
            JOIN manga_demographic md
                ON md.manga_id = fs.manga_id
            JOIN demographic d
                ON d.id = md.demographic_id
        )

        SELECT
            attribute_type,
            name,
            COUNT(DISTINCT manga_id)::int AS source_count,
            SUM(positive_weight)::float AS total_weight
        FROM profile_attributes
        GROUP BY
            attribute_type,
            name
        ORDER BY
            attribute_type ASC,
            total_weight DESC,
            source_count DESC,
            name ASC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(positive_sources_sql, {"user_id": DEFAULT_USER_ID})
            positive_sources_available = cur.fetchall()

            cur.execute(all_library_ids_sql, {"user_id": DEFAULT_USER_ID})
            library_rows = cur.fetchall()

            cur.execute(status_counts_sql, {"user_id": DEFAULT_USER_ID})
            status_rows = cur.fetchall()

            cur.execute(profile_tags_sql, {"user_id": DEFAULT_USER_ID})
            tag_rows = cur.fetchall()

    if not positive_sources_available:
        raise HTTPException(
            status_code=400,
            detail=(
                "La bibliothèque ne contient pas encore assez de signaux positifs. "
                "Ajoute au moins un manga lu, en cours, possédé, favori ou bien noté."
            ),
        )

    high_confidence_sources = [
        source
        for source in positive_sources_available
        if source.get("is_favorite") is True
        or (
            source.get("user_score") is not None
            and float(source.get("user_score")) >= 8.5
        )
    ]

    if len(high_confidence_sources) >= 3:
        positive_sources_used = high_confidence_sources[:5]
        source_selection_rule = (
            "Sources haute confiance : favoris et/ou notes utilisateur >= 8.5."
        )
    else:
        positive_sources_used = positive_sources_available[:5]
        source_selection_rule = (
            "Sources positives principales : favoris, notes, statuts lus/en cours/envie."
        )

    library_manga_ids = {
        row["manga_id"] if isinstance(row, dict) else row[0]
        for row in library_rows
    }

    liked_titles = [row["title"] for row in positive_sources_used]

    profile_limit = max(payload.limit * 4, 20)

    profile_result = recommend_from_profile(
        ProfileRecommendationRequest(
            liked_titles=liked_titles,
            limit=min(profile_limit, 20),
            min_score=payload.min_score,
            only_finished=(
                payload.only_finished
                or recommendation_goal == "SHORT_FINISHED"
            ),
            exclude_sensitive_mismatches=payload.exclude_sensitive_mismatches,
        )
    )

    raw_recommendations = []

    for recommendation in profile_result.get("recommendations", []):
        manga_id = recommendation.get("id")

        if manga_id in library_manga_ids:
            continue

        raw_recommendations.append(recommendation)

    metadata_by_id = fetch_manga_metadata_for_recommendations(
        [
            recommendation["id"]
            for recommendation in raw_recommendations
            if recommendation.get("id")
        ]
    )

    recommendations = []

    for recommendation in raw_recommendations:
        manga_id = recommendation.get("id")
        metadata = metadata_by_id.get(manga_id, {})

        recommendation["volumes"] = metadata.get("volumes")
        recommendation["chapters"] = metadata.get("chapters")
        recommendation["recommendation_goal"] = recommendation_goal

        goal_bonus = compute_library_goal_bonus(
            recommendation=recommendation,
            recommendation_goal=recommendation_goal,
        )

        recommendation["goal_bonus"] = goal_bonus
        recommendation["base_recommendation_score"] = recommendation.get(
            "recommendation_score"
        )
        recommendation["recommendation_score"] = round(
            float(recommendation.get("recommendation_score") or 0) + goal_bonus,
            1,
        )

        recommendation["reason"] = (
            recommendation.get("reason", "")
            + f" Objectif bibliothèque : {recommendation_goal} ({goal_bonus:+.1f})."
        )

        recommendations.append(recommendation)

    recommendations.sort(
        key=lambda item: (
            float(item.get("recommendation_score") or 0),
            int(item.get("community_source_count") or 0),
            int(item.get("community_votes") or 0),
            -int(item.get("popularity") or 999999),
        ),
        reverse=True,
    )

    recommendations = recommendations[: payload.limit]

    status_counts = {
        row["library_status"]: row["count"]
        for row in status_rows
    }

    grouped_tags: dict[str, list[dict[str, Any]]] = {
        "genre": [],
        "theme": [],
        "demographic": [],
    }

    for row in tag_rows:
        attribute_type = row["attribute_type"]

        if attribute_type not in grouped_tags:
            continue

        if len(grouped_tags[attribute_type]) >= 10:
            continue

        grouped_tags[attribute_type].append(
            {
                "name": row["name"],
                "source_count": row["source_count"],
                "total_weight": round(float(row["total_weight"] or 0), 1),
            }
        )

    profile_summary = {
        "status_counts": status_counts,
        "source_selection_rule": source_selection_rule,
        "positive_source_count_available": len(positive_sources_available),
        "positive_source_count_used": len(positive_sources_used),
        "top_genres": grouped_tags["genre"],
        "top_themes": grouped_tags["theme"],
        "top_demographics": grouped_tags["demographic"],
    }

    return {
        "user_id": DEFAULT_USER_ID,
        "source": "library",
        "recommendation_goal": recommendation_goal,
        "profile_summary": profile_summary,
        "positive_sources_available": positive_sources_available,
        "positive_sources": positive_sources_used,
        "excluded_library_manga_count": len(library_manga_ids),
        "count": len(recommendations),
        "recommendations": recommendations,
    }
'''


def add_goal_field(text: str) -> str:
    if "recommendation_goal" in text:
        print("[INFO] Champ recommendation_goal déjà présent.")
        return text

    old = '''    exclude_sensitive_mismatches: bool = Field(
        default=False,
        description="Si true, exclut les mangas avec éléments éloignants.",
    )
'''

    new = '''    exclude_sensitive_mismatches: bool = Field(
        default=False,
        description="Si true, exclut les mangas avec éléments éloignants.",
    )
    recommendation_goal: str = Field(
        default="SIMILAR_SAFE",
        description=(
            "Objectif de recommandation depuis bibliothèque : "
            "SIMILAR_SAFE, READ_NEXT ou SHORT_FINISHED."
        ),
    )
'''

    if old not in text:
        raise SystemExit("[ERREUR] Bloc LibraryRecommendationRequest introuvable.")

    print("[OK] Champ recommendation_goal ajouté.")
    return text.replace(old, new, 1)


def replace_library_endpoint(text: str) -> str:
    start_marker = '@app.post("/recommendations/library")'
    end_marker = '\n\n@app.get("/recommendations/similar")'

    start = text.find(start_marker)

    if start == -1:
        raise SystemExit("[ERREUR] Endpoint /recommendations/library introuvable.")

    end = text.find(end_marker, start)

    if end == -1:
        raise SystemExit("[ERREUR] Fin de fonction introuvable avant /recommendations/similar.")

    print("[OK] Endpoint /recommendations/library remplacé.")
    return text[:start] + NEW_RECOMMEND_FROM_LIBRARY + text[end:]


def main() -> int:
    text = MAIN_PATH.read_text(encoding="utf-8")

    text = add_goal_field(text)
    text = replace_library_endpoint(text)

    MAIN_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {MAIN_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())