"""Owned-only manga inventories must produce cautious, sourced discovery.

No private CSV or live PostgreSQL connection is required: route tests use
synthetic catalog rows and examine which read-only SQL queries are sent.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.api.app.advisor import (
    AdvisorRequest,
    make_advisor_router,
    recurring_owned_tags,
)


CANDIDATES = [
    {
        "id": 101, "title": "Synthetic Mystery", "genres": ["Mystery"],
        "themes": ["Detective"], "score": 8.1, "popularity": 40,
        "status": "Finished", "volumes": 9, "chapters": 85,
        "french_record_count": 0, "preferred_format_record_count": 0,
    },
    {
        "id": 102, "title": "Synthetic Other", "genres": ["Romance"],
        "themes": [], "score": 9.1, "popularity": 1, "status": "Finished",
        "volumes": 4, "chapters": 20, "french_record_count": 0,
        "preferred_format_record_count": 0,
    },
]


class FakeCursor:
    def __init__(self, owner):
        self.owner = owner
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params):
        self.owner.queries.append((query, params))
        if "WITH positive AS" in query:
            self.rows = self.owner.rated_rows
        elif "WITH marked AS" in query:
            self.rows = []
        elif "WITH owned AS" in query:
            self.rows = self.owner.owned_rows
        elif "FROM manga m WHERE" in query:
            # A real PostgreSQL query applies this filter BEFORE LIMIT.
            self.rows = [
                row for row in CANDIDATES
                if any(
                    tag.casefold() in set(params["genres"])
                    for tag in row["genres"]
                ) or any(
                    tag.casefold() in set(params["themes"])
                    for tag in row["themes"]
                )
            ]
        else:
            raise AssertionError(f"Unexpected query: {query[:120]}")

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, owner):
        self.owner = owner

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return FakeCursor(self.owner)


class FakeDatabase:
    def __init__(self, *, owned_rows=None, rated_rows=None):
        self.owned_rows = owned_rows or []
        self.rated_rows = rated_rows or []
        self.queries = []

    def __call__(self):
        return FakeConnection(self)


def advice(database, message="Surprends-moi selon mes goûts"):
    router = make_advisor_router(database, user_id=42)
    endpoint = next(route.endpoint for route in reversed(router.routes)
                    if route.path == "/advisor/message")
    with patch("apps.api.app.advisor.fetch_recommended_editions", return_value={}):
        return endpoint(AdvisorRequest(message=message, limit=6))


class OwnershipDiscoveryTests(unittest.TestCase):
    def test_ownership_needs_two_distinct_works_per_tag(self):
        tags, evidence = recurring_owned_tags([
            {"kind": "genres", "tag": "Mystery", "source_count": 2, "owned_work_count": 4},
            {"kind": "genres", "tag": "Action", "source_count": 1, "owned_work_count": 4},
            {"kind": "themes", "tag": "Detective", "source_count": 3, "owned_work_count": 4},
            {"kind": "themes", "tag": "", "source_count": 4, "owned_work_count": 4},
        ])
        self.assertEqual(tags, {"genres": {"mystery"}, "themes": {"detective"}})
        self.assertEqual(evidence, {
            "owned_works_considered": 4,
            "recurring_genres": 1,
            "recurring_themes": 1,
        })

    def test_editions_do_not_count_as_separate_sources_in_sql(self):
        db = FakeDatabase(owned_rows=[
            {"kind": "genres", "tag": "mystery", "source_count": 2, "owned_work_count": 3},
            {"kind": "themes", "tag": "detective", "source_count": 2, "owned_work_count": 3},
        ])
        result = advice(db)
        self.assertEqual(result["status"], "results")
        self.assertEqual(result["personalization_basis"], "owned_collection_only")
        self.assertTrue(result["personalized"])
        self.assertEqual([row["id"] for row in result["recommendations"]], [101])
        self.assertIn("Posséder un manga ne signifie pas forcément l'aimer", result["reply"])
        self.assertEqual(result["ownership_evidence"]["owned_works_considered"], 3)
        owner_sql = next(sql for sql, _ in db.queries if "WITH owned AS" in sql)
        self.assertIn("COUNT(DISTINCT o.manga_id)", owner_sql)
        self.assertIn("library_status='OWNED'", owner_sql)
        self.assertIn("user_score IS NULL", owner_sql)
        self.assertIn("source_count>=2", owner_sql)
        catalog_sql, params = next((q, p) for q, p in db.queries if "FROM manga m WHERE" in q)
        self.assertIn("NOT EXISTS (SELECT 1 FROM user_manga_library", catalog_sql)
        self.assertIn("user_manga_volume v", catalog_sql)
        self.assertEqual(params["genres"], ["mystery"])
        self.assertEqual(params["themes"], ["detective"])

    def test_recommendation_returns_international_name_with_original_title(self):
        db = FakeDatabase(owned_rows=[
            {"kind": "genres", "tag": "mystery",
             "source_count": 2, "owned_work_count": 2},
        ])
        with patch.dict(CANDIDATES[0], {"title_english": "International Mystery"}):
            result = advice(db)
        suggestion = result["recommendations"][0]
        self.assertEqual(suggestion["title"], "International Mystery")
        self.assertEqual(suggestion["title_original"], "Synthetic Mystery")
        self.assertEqual(suggestion["id"], 101)

    def test_positive_reading_preferences_take_priority_over_owned_titles(self):
        db = FakeDatabase(
            rated_rows=[{"kind": "genres", "tag": "mystery"}],
            owned_rows=[{"kind": "genres", "tag": "romance", "source_count": 4,
                         "owned_work_count": 5}],
        )
        result = advice(db)
        self.assertEqual(result["status"], "results")
        self.assertEqual(result["personalization_basis"], "reading_preferences")
        self.assertNotIn("Posséder un manga", result["reply"])
        self.assertFalse(any("WITH owned AS" in q for q, _ in db.queries))

    def test_ownership_without_recurring_tags_requests_more_information(self):
        db = FakeDatabase(owned_rows=[])
        result = advice(db)
        self.assertEqual(result["status"], "clarify")
        self.assertEqual(result["personalization_basis"], "none")
        self.assertFalse(any("FROM manga m WHERE" in q for q, _ in db.queries))

    def test_no_ownership_reuse_when_profile_is_explicitly_disabled(self):
        db = FakeDatabase(owned_rows=[
            {"kind": "genres", "tag": "mystery", "source_count": 3, "owned_work_count": 3}
        ])
        result = advice(db, "Surprends-moi sans mes goûts")
        self.assertEqual(result["status"], "clarify")
        self.assertFalse(db.queries)


if __name__ == "__main__":
    unittest.main()
