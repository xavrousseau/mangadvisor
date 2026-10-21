"""Protect reading-library status and recommendation goal invariants without a DB."""
import inspect
import unittest

from apps.api.app.main import (
    LibraryRecommendationRequest,
    normalize_library_recommendation_goal,
    recommend_from_library,
)


class LegacyRecommendationContractTests(unittest.TestCase):
    def test_three_legacy_goals_remain_valid(self):
        for goal in ("SIMILAR_SAFE", "READ_NEXT", "SHORT_FINISHED"):
            with self.subTest(goal=goal):
                self.assertEqual(normalize_library_recommendation_goal(goal), goal)
                payload=LibraryRecommendationRequest(recommendation_goal=goal)
                self.assertEqual(payload.recommendation_goal, goal)

    def test_negative_library_statuses_never_seed_positive_recommendations(self):
        sql_and_logic = inspect.getsource(recommend_from_library)
        self.assertIn("l.library_status NOT IN ('DROPPED', 'NOT_INTERESTED')", sql_and_logic)
        for status in ("READ", "READING", "OWNED", "WANT_TO_READ"):
            with self.subTest(status=status):
                self.assertIn(f"l.library_status = '{status}'", sql_and_logic)

    def test_existing_library_exclusion_not_weakened(self):
        source=inspect.getsource(recommend_from_library)
        self.assertIn("user_manga_library",source)
        self.assertIn("NOT_INTERESTED",source)
        self.assertIn("DROPPED",source)
