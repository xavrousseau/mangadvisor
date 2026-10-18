"""Evidence contract tests: attribute intersections never fabricate source matches."""
import copy
import unittest

from apps.api.app.recommendation_explanations import (
    add_explanations, build_explanation,
)


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.params = None
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.cursor_value = Cursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_value


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {"id": 1, "title": "Monster", "user_score": 9.5, "is_favorite": True},
            {"id": 2, "title": "Berserk", "user_score": 9, "is_favorite": False},
        ]
        self.tags = {
            1: {"genres": ["Drama", "Mystery"], "themes": ["Psychological"], "demographics": ["Seinen"]},
            2: {"genres": ["Action"], "themes": ["Military"], "demographics": ["Seinen"]},
            10: {"genres": ["Drama", "Mystery"], "themes": ["Psychological"], "demographics": ["Shounen"]},
        }

    def test_only_verified_attributes_are_attributed_to_source(self):
        item = {
            "id": 10, "common_genres": ["Drama", "Mystery"],
            "common_themes": ["Psychological"],
            "recommendation_score": 98.5, "community_votes": 3,
        }
        before = copy.deepcopy(item)
        explanation = build_explanation(item, self.sources, self.tags, origin="library")
        self.assertEqual(explanation["origin"], "library")
        self.assertEqual(explanation["reference_titles"], ["Monster", "Berserk"])
        self.assertEqual(len(explanation["source_matches"]), 1)
        self.assertEqual(explanation["source_matches"][0]["title"], "Monster")
        self.assertEqual(explanation["source_matches"][0]["genres"], ["Drama", "Mystery"])
        self.assertEqual(explanation["source_matches"][0]["themes"], ["Psychological"])
        self.assertEqual(explanation["source_matches"][0]["demographics"], [])
        self.assertNotIn("Berserk", [s["title"] for s in explanation["source_matches"]])
        self.assertEqual(item, before)

    def test_no_fake_match_when_source_metadata_absent(self):
        item = {"id": 10, "recommendation_score": 53}
        explanation = build_explanation(item, self.sources, {10: self.tags[10]}, origin="manual")
        self.assertEqual(explanation["source_matches"], [])
        self.assertEqual(explanation["reference_titles"], ["Monster", "Berserk"])

    def test_actual_bonus_is_not_recalculated(self):
        item = {
            "id": 10, "recommendation_score": 108,
            "base_recommendation_score": 100, "goal_bonus": 8,
            "community_score": 12.4,
        }
        explanation = build_explanation(item, [], self.tags, origin="library")
        self.assertEqual(explanation["score"]["base"], 100)
        self.assertEqual(explanation["score"]["goal_bonus"], 8)
        self.assertEqual(explanation["score"]["final"], 108)
        self.assertEqual(explanation["score"]["community_signal"], 12.4)

    def test_single_read_only_query_and_preserved_order(self):
        rows = [
            {"id": 1, **self.tags[1]}, {"id": 2, **self.tags[2]},
            {"id": 10, **self.tags[10]}, {"id": 11, "genres": [], "themes": [], "demographics": []},
        ]
        conn = Connection(rows)
        recommendations = [
            {"id": 11, "recommendation_score": 120},
            {"id": 10, "recommendation_score": 110},
        ]
        add_explanations(
            recommendations, self.sources, origin="library",
            connection_factory=lambda: conn,
        )
        self.assertEqual([x["id"] for x in recommendations], [11, 10])
        self.assertEqual(conn.cursor_value.params["ids"], [1, 2, 10, 11])
        self.assertIn("WHERE m.id = ANY", conn.cursor_value.sql)
        self.assertNotIn("UPDATE ", conn.cursor_value.sql)
        self.assertNotIn("DELETE ", conn.cursor_value.sql)
        self.assertEqual(len(recommendations[1]["explanation"]["source_matches"]), 1)

    def test_empty_recommendations_never_touch_database(self):
        def fail():
            raise AssertionError("connection should not be opened")
        add_explanations([], self.sources, origin="library", connection_factory=fail)


if __name__ == "__main__":
    unittest.main()
