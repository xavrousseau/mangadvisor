"""Quality mode regressions: non-destructive and deterministic.

The SQL engine score is authoritative; this module selects among eligible
candidates but never invents a new compatibility percentage.
"""
import copy
import unittest
from pydantic import ValidationError

from apps.api.app.main import (
    ProfileRecommendationRequest, LibraryRecommendationRequest,
)
from apps.api.app.recommendation_quality import (
    choose_balanced, evidence_strength, selection_quality, matched_tags,
)


def manga(mid, score, tags=None, *, themes=None, community=0):
    genres = tags or []
    themes = themes or []
    return {
        "id": mid,
        "title": "Synthetic " + str(mid),
        "recommendation_score": score,
        "common_genre_count": len(genres),
        "common_theme_count": len(themes),
        "common_genres": genres,
        "common_themes": themes,
        "community_source_count": community,
    }


class RecommendationQualityTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            manga(1, 120, ["Action", "Adventure"], themes=["Mystery"]),
            manga(2, 118, ["Action", "Adventure"], themes=["Mystery"]),
            manga(3, 116, ["Action", "Adventure"], themes=["Mystery"]),
            manga(4, 111, ["Romance", "Drama"], themes=["School"]),
            manga(5, 70, ["Sports", "Drama"], themes=["Team Sports"]),
        ]

    def test_close_preserves_engine_order_and_exact_scores(self):
        original = copy.deepcopy(self.items)
        chosen, diagnosis = choose_balanced(self.items, 4, "CLOSE")
        self.assertEqual([m["id"] for m in chosen], [1, 2, 3, 4])
        self.assertEqual([m["recommendation_score"] for m in chosen],
                         [120, 118, 116, 111])
        self.assertEqual(diagnosis["mode"], "CLOSE")
        self.assertEqual(self.items, original)

    def test_balanced_favors_diversity_within_bounded_score_concession(self):
        chosen, diagnosis = choose_balanced(self.items, 3, "BALANCED")
        self.assertEqual(chosen[0]["id"], 1)
        self.assertEqual(chosen[1]["id"], 4)
        self.assertIn(chosen[2]["id"], (2, 3))
        self.assertLess(diagnosis["after"]["repeated_overlap_pairs"],
                        diagnosis["before"]["repeated_overlap_pairs"])
        self.assertEqual(self.items[0]["recommendation_score"], 120)

    def test_explore_never_takes_far_away_candidate(self):
        chosen, _ = choose_balanced(self.items, 3, "EXPLORE")
        self.assertEqual(chosen[0]["id"], 1)
        self.assertNotIn(5, [m["id"] for m in chosen])
        self.assertIn(4, [m["id"] for m in chosen])

    def test_single_generic_match_is_weaker_than_a_real_theme(self):
        generic = manga(8, 98, ["Action"])
        supported = manga(9, 90, ["Adventure"], themes=["Mystery"])
        self.assertEqual(evidence_strength(generic), "limited")
        self.assertEqual(evidence_strength(supported), "supported")
        chosen, _ = choose_balanced([generic, supported], 1, "BALANCED")
        self.assertEqual(chosen[0]["id"], 9)

    def test_no_fabricated_tags_or_notes(self):
        unknown = {"id": 11, "recommendation_score": 88,
                   "common_genres": None, "common_themes": None}
        old = copy.deepcopy(unknown)
        chosen, diagnostic = choose_balanced([unknown], 1, "BALANCED")
        self.assertEqual(chosen[0], old)
        self.assertEqual(unknown, old)
        self.assertEqual(diagnostic["after"]["limited_evidence_count"], 1)
        self.assertEqual(matched_tags(unknown), frozenset())

    def test_deterministic_ties_and_single_candidate(self):
        items = [manga(1, 70, ["Drama"], themes=["Mystery"]),
                 manga(2, 70, ["Drama"], themes=["Mystery"])]
        for mode in ("CLOSE", "BALANCED", "EXPLORE"):
            output, _ = choose_balanced(items, 2, mode)
            self.assertEqual([m["id"] for m in output], [1, 2])
        self.assertEqual(selection_quality([])["count"], 0)

    def test_api_modes_are_validated_and_backwards_compatible(self):
        profile = ProfileRecommendationRequest(liked_titles=["Naruto"])
        library = LibraryRecommendationRequest()
        self.assertEqual(profile.recommendation_balance, "CLOSE")
        self.assertEqual(library.recommendation_balance, "CLOSE")
        for model, kw in (
            (ProfileRecommendationRequest, {"liked_titles": ["Naruto"]}),
            (LibraryRecommendationRequest, {}),
        ):
            with self.assertRaises(ValidationError):
                model(**kw, recommendation_balance="MAGIC")

    def test_invalid_mode_and_limit_rejected(self):
        with self.assertRaises(ValueError):
            choose_balanced(self.items, 3, "ANY")
        with self.assertRaises(ValueError):
            choose_balanced(self.items, 0, "CLOSE")


if __name__ == "__main__":
    unittest.main()
