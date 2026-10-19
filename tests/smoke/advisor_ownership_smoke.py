"""CI-only live PostgreSQL check for weak ownership-based manga discovery.

This fixture creates a SECOND local user in the throwaway GitHub CI database.
It never changes the main test user's favorites, notes or library.
"""
from __future__ import annotations

import os

if os.getenv("POSTGRES_DB") != "mangadvisor_ci":
    raise SystemExit("REFUS : test uniquement sur la base jetable mangadvisor_ci.")

from apps.api.app.advisor import AdvisorRequest, make_advisor_router  # noqa: E402
from apps.api.app.main import get_connection  # noqa: E402

CI_USER_ID = 942


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO app_user(id,username,display_name) "
                "VALUES (%s,'ci_owned_only_advisor','Synthetic owner') "
                "ON CONFLICT (id) DO NOTHING;",
                (CI_USER_ID,),
            )
            cursor.execute(
                """
                INSERT INTO user_manga_library
                    (user_id,manga_id,library_status,user_score,is_favorite)
                SELECT %s,id,'OWNED',NULL,FALSE
                FROM manga WHERE title IN ('Naruto','Demo CI 05')
                ON CONFLICT (user_id,manga_id) DO NOTHING;
                """,
                (CI_USER_ID,),
            )
            cursor.execute(
                """
                INSERT INTO user_manga_library
                    (user_id,manga_id,library_status)
                SELECT %s,id,'NOT_INTERESTED'
                FROM manga WHERE title='Demo CI 07'
                ON CONFLICT (user_id,manga_id) DO NOTHING;
                """,
                (CI_USER_ID,),
            )
            cursor.execute(
                "SELECT title,library_status FROM manga "
                "JOIN user_manga_library l ON l.manga_id=manga.id "
                "WHERE l.user_id=%s;",
                (CI_USER_ID,),
            )
            seeded = {row["title"]: row["library_status"] for row in cursor.fetchall()}
    assert seeded == {
        "Naruto": "OWNED", "Demo CI 05": "OWNED",
        "Demo CI 07": "NOT_INTERESTED",
    }, seeded

    try:
        advisor = make_advisor_router(get_connection, user_id=CI_USER_ID)
        endpoint = next(
            route.endpoint for route in reversed(advisor.routes)
            if route.path == "/advisor/message"
        )
        data = endpoint(AdvisorRequest(message="Surprends-moi selon mes goûts"))
        assert data["status"] == "results" and data["count"] > 0, data
        assert data["personalization_basis"] == "owned_collection_only", data
        assert data["ownership_evidence"]["owned_works_considered"] == 2, data
        assert data["personalized"] is True, data
        excluded = {"Naruto", "Demo CI 05", "Demo CI 07"}
        returned_titles = {row["title"] for row in data["recommendations"]}
        assert returned_titles.isdisjoint(excluded), (excluded, returned_titles)
        assert all(
            row["affinity_matches"]["genres"] or row["affinity_matches"]["themes"]
            for row in data["recommendations"]
        ), data
        assert "Posséder un manga" in data["reply"], data
        print(
            "OK: PostgreSQL reelle, 2 œuvres possedees non notees, "
            f"{data['count']} suggestions distinctes, exclusions respectees."
        )
    finally:
        # Removing the synthetic user cascades only to their disposable rows.
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM app_user WHERE id=%s;", (CI_USER_ID,))


if __name__ == "__main__":
    main()
