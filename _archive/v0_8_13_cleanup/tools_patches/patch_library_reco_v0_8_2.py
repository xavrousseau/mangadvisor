from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_library_recommendation_tests.py"


NEW_RECOMMEND_FROM_LIBRARY = r'''
@app.post("/recommendations/library")
def recommend_from_library(
    payload: LibraryRecommendationRequest,
) -> dict[str, Any]:
    """
    Recommande des mangas à partir de la bibliothèque utilisateur.

    V0.8.2 :
    - calcule un poids positif par manga de bibliothèque ;
    - privilégie les favoris et les notes élevées ;
    - évite de mélanger tous les signaux faibles ;
    - exclut les mangas déjà présents dans la bibliothèque ;
    - retourne un résumé du profil bibliothèque.
    """
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
            cur.execute(
                positive_sources_sql,
                {"user_id": DEFAULT_USER_ID},
            )
            positive_sources_available = cur.fetchall()

            cur.execute(
                all_library_ids_sql,
                {"user_id": DEFAULT_USER_ID},
            )
            library_rows = cur.fetchall()

            cur.execute(
                status_counts_sql,
                {"user_id": DEFAULT_USER_ID},
            )
            status_rows = cur.fetchall()

            cur.execute(
                profile_tags_sql,
                {"user_id": DEFAULT_USER_ID},
            )
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

    profile_result = recommend_from_profile(
        ProfileRecommendationRequest(
            liked_titles=liked_titles,
            limit=20,
            min_score=payload.min_score,
            only_finished=payload.only_finished,
            exclude_sensitive_mismatches=payload.exclude_sensitive_mismatches,
        )
    )

    recommendations = []

    for recommendation in profile_result.get("recommendations", []):
        manga_id = recommendation.get("id")

        if manga_id in library_manga_ids:
            continue

        recommendations.append(recommendation)

        if len(recommendations) >= payload.limit:
            break

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
        "profile_summary": profile_summary,
        "positive_sources_available": positive_sources_available,
        "positive_sources": positive_sources_used,
        "excluded_library_manga_count": len(library_manga_ids),
        "count": len(recommendations),
        "recommendations": recommendations,
    }
'''


def replace_function(text: str) -> str:
    start_marker = '@app.post("/recommendations/library")'
    end_marker = '\n\n@app.get("/recommendations/similar")'

    start = text.find(start_marker)

    if start == -1:
        raise SystemExit("[ERREUR] Endpoint /recommendations/library introuvable.")

    end = text.find(end_marker, start)

    if end == -1:
        raise SystemExit("[ERREUR] Fin de fonction introuvable avant /recommendations/similar.")

    return text[:start] + NEW_RECOMMEND_FROM_LIBRARY + text[end:]


def patch_main_py() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    text = replace_function(text)
    MAIN_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Endpoint /recommendations/library remplacé : {MAIN_PATH}")


def patch_test_script() -> None:
    text = TEST_PATH.read_text(encoding="utf-8")

    text = text.replace(
        'REPORT_PATH = REPORT_DIR / "library_recommendation_tests_v0_8_1.md"',
        'REPORT_PATH = REPORT_DIR / "library_recommendation_tests_v0_8_2.md"',
    )

    text = text.replace(
        "# Mangadvisor — Tests recommandations depuis bibliothèque V0.8.1",
        "# Mangadvisor — Tests recommandations depuis bibliothèque V0.8.2",
    )

    text = text.replace(
        "Rapport genere dans docs\\reports\\library_recommendation_tests_v0_8_1.md",
        "Rapport genere dans docs\\reports\\library_recommendation_tests_v0_8_2.md",
    )

    TEST_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Script de test mis à jour : {TEST_PATH}")


def main() -> int:
    patch_main_py()
    patch_test_script()

    print()
    print("Patch V0.8.2 terminé.")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print("  cmd\\run-library-recommendation-tests.cmd")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())