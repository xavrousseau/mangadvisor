"""Guided discovery is deterministic, catalog-grounded and read-only."""
import unittest

from pydantic import ValidationError

from apps.api.app.mood_discovery import (
    MOODS, MoodDiscoveryRequest, choose_discoveries, match_mood,
    preference_overlap, discovery_rank,
)


class GuidedDiscoveryTests(unittest.TestCase):
    def test_supported_moods_and_constraints(self):
        self.assertIn("COMFORT", MOODS)
        self.assertEqual(MoodDiscoveryRequest(mood="ACTION").length, "ANY")
        for field, value in (
            ("mood", "UNSUPPORTED"), ("length", "INVALID"),
            ("limit", 200), ("min_score", -1),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    MoodDiscoveryRequest(**{"mood": "ACTION", field: value})

    def test_exact_catalog_tag_match_not_synopsis(self):
        candidate = {
            "id": 1, "genres": ["Action"], "themes": ["Mystery"],
            "synopsis": "Horror Psychological Romance dark magic",
        }
        self.assertEqual(match_mood(candidate, "DARK"),
                         {"genres": [], "themes": []})
        self.assertEqual(match_mood(candidate, "MYSTERY"),
                         {"genres": [], "themes": ["Mystery"]})

    def test_no_unsupported_item_and_no_guessed_affinity(self):
        candidates = [
            {"id": 10, "title": "Stranger", "genres": ["Comedy"], "themes": [],
             "score": 9.9, "popularity": 1},
            {"id": 11, "title": "Detective", "genres": ["Mystery"],
             "themes": ["Psychological"], "score": 7.4, "popularity": 8},
        ]
        preferences = {"genres": {"mystery"}, "themes": set()}
        result = choose_discoveries(candidates, "MYSTERY", preferences, 8)
        self.assertEqual([r["id"] for r in result], [11])
        self.assertEqual(result[0]["mood_matches"]["genres"], ["Mystery"])
        self.assertEqual(result[0]["affinity_matches"]["genres"], ["Mystery"])
        self.assertIsNone(result[0]["ranking_score"])
        empty = choose_discoveries(candidates, "ROMANCE", preferences, 8)
        self.assertEqual(empty, [])

    def test_affinity_prioritizes_real_attributes_and_is_stable(self):
        candidates = [
            {"id": 1, "genres": ["Action"], "themes": [], "score": 9.0, "popularity": 1},
            {"id": 2, "genres": ["Action"], "themes": ["Mystery"], "score": 8.9, "popularity": 2},
        ]
        self.assertEqual(
            [row["id"] for row in choose_discoveries(candidates, "ACTION",
                {"genres": set(), "themes": {"mystery"}}, 2)], [2, 1])
        self.assertEqual(
            [row["id"] for row in choose_discoveries(candidates, "ACTION",
                {"genres": set(), "themes": set()}, 2)], [1, 2])
        self.assertEqual(
            [row["id"] for row in choose_discoveries(candidates, "ACTION",
                {"genres": set(), "themes": set()}, 2)], [1, 2])


if __name__ == "__main__":
    unittest.main()
