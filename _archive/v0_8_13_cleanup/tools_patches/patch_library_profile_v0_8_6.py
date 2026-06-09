from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"


LIBRARY_PROFILE_ENDPOINT = r'''
@app.get("/library/profile")
def get_library_profile() -> dict[str, Any]:
    """
    Retourne une synthèse du profil de lecture construit depuis la bibliothèque.

    V0.8.6 :
    - répartition par statut ;
    - sources positives avec poids ;
    - mangas négatifs / exclus ;
    - genres, thèmes et cibles éditoriales dominants.
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

    positive_sources_sql = """
        WITH weighted_sources AS (
            SELECT
                m.id,
                m.title,
                m.title_english,
                m.status AS manga_status,
                m.manga_type,
                m.score::float AS manga_score,
                m.popularity,

                l.library_status,
                l.user_score::float AS user_score,
                l.is_favorite,
                l.owned_volumes,
                l.read_volumes,
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
                        WHEN l.user_score >= 6 THEN 0.0
                        WHEN l.user_score >= 5 THEN -2.0
                        WHEN l.user_score IS NULL THEN 0.0
                        ELSE -10.0
                      END
                )::float AS positive_weight

            FROM user_manga_library l
            JOIN manga m
                ON m.id = l.manga_id

            WHERE l.user_id = %(user_id)s
              AND l.library_status NOT IN ('DROPPED', 'NOT_INTERESTED')
        )

        SELECT *
        FROM weighted_sources
        WHERE positive_weight > 0
        ORDER BY
            positive_weight DESC,
            is_favorite DESC,
            user_score DESC NULLS LAST,
            updated_at DESC,
            popularity ASC NULLS LAST;
    """

    negative_items_sql = """
        SELECT
            m.id,
            m.title,
            m.title_english,
            m.status AS manga_status,
            m.manga_type,
            m.score::float AS manga_score,
            m.popularity,

            l.library_status,
            l.user_score::float AS user_score,
            l.is_favorite,
            l.updated_at,

            CASE
                WHEN l.library_status = 'NOT_INTERESTED' THEN 'Pas intéressé'
                WHEN l.library_status = 'DROPPED' THEN 'Abandonné'
                WHEN l.user_score IS NOT NULL AND l.user_score < 5 THEN 'Très mauvaise note'
                WHEN l.user_score IS NOT NULL AND l.user_score < 6 THEN 'Note faible'
                ELSE 'Signal faible ou neutre'
            END AS negative_reason

        FROM user_manga_library l
        JOIN manga m
            ON m.id = l.manga_id

        WHERE l.user_id = %(user_id)s
          AND (
                l.library_status IN ('DROPPED', 'NOT_INTERESTED')
                OR (
                    l.user_score IS NOT NULL
                    AND l.user_score < 6
                )
          )

        ORDER BY
            l.library_status ASC,
            l.user_score ASC NULLS LAST,
            l.updated_at DESC;
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
                        WHEN l.user_score >= 6 THEN 0.0
                        WHEN l.user_score >= 5 THEN -2.0
                        WHEN l.user_score IS NULL THEN 0.0
                        ELSE -10.0
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
            cur.execute(status_counts_sql, {"user_id": DEFAULT_USER_ID})
            status_rows = cur.fetchall()

            cur.execute(positive_sources_sql, {"user_id": DEFAULT_USER_ID})
            positive_sources = cur.fetchall()

            cur.execute(negative_items_sql, {"user_id": DEFAULT_USER_ID})
            negative_items = cur.fetchall()

            cur.execute(profile_tags_sql, {"user_id": DEFAULT_USER_ID})
            tag_rows = cur.fetchall()

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

        grouped_tags[attribute_type].append(
            {
                "name": row["name"],
                "source_count": row["source_count"],
                "total_weight": round(float(row["total_weight"] or 0), 1),
            }
        )

    strongest_sources = positive_sources[:5]

    return {
        "user_id": DEFAULT_USER_ID,
        "status_counts": status_counts,
        "positive_source_count": len(positive_sources),
        "negative_item_count": len(negative_items),
        "strongest_sources": strongest_sources,
        "positive_sources": positive_sources,
        "negative_items": negative_items,
        "top_genres": grouped_tags["genre"][:10],
        "top_themes": grouped_tags["theme"][:10],
        "top_demographics": grouped_tags["demographic"][:10],
    }
'''


def main() -> int:
    text = MAIN_PATH.read_text(encoding="utf-8")

    if '@app.get("/library/profile")' in text:
        print("[INFO] Endpoint /library/profile déjà présent.")
    else:
        marker = '\n\n@app.post("/recommendations/library")'

        if marker not in text:
            raise SystemExit(
                "[ERREUR] Impossible de trouver @app.post(\"/recommendations/library\") dans main.py."
            )

        text = text.replace(
            marker,
            "\n" + LIBRARY_PROFILE_ENDPOINT + marker,
            1,
        )

        MAIN_PATH.write_text(text, encoding="utf-8")
        print("[OK] Endpoint /library/profile ajouté.")

    print()
    print("Patch V0.8.6 terminé.")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print()
    print("Puis teste dans Swagger :")
    print("  GET /library/profile")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())