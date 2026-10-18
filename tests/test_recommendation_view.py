"""Contrôles non destructifs de l'interface des recommandations Mangadvisor 1.0."""
import copy
import unittest

from apps.ui.app.recommendations import (
    GOALS,
    GOAL_LABELS,
    compact_evidence,
    format_community_rating,
    format_internal_score,
)


class RecommendationPresentationTests(unittest.TestCase):
    def test_internal_score_is_not_a_percentage(self):
        self.assertEqual(format_internal_score(114.4), "114.4 pts")
        self.assertEqual(format_internal_score(0), "0.0 pts")
        self.assertEqual(format_internal_score(None), "Non calculé")
        self.assertEqual(format_internal_score("inconnu"), "Non calculé")
        self.assertNotIn("%", format_internal_score(98))

    def test_community_rating_has_its_own_scale(self):
        self.assertEqual(format_community_rating(8.74), "★ 8.7/10")
        self.assertEqual(format_community_rating(0), "★ 0.0/10")
        self.assertEqual(format_community_rating(None), "Non noté")
        self.assertEqual(format_community_rating("n/a"), "Non noté")

    def test_summary_only_mentions_real_evidence(self):
        item = {
            "common_themes": ["Psychological", "Mystery"],
            "common_genres": ["Drama", "Suspense"],
            "community_recommended_from": ["Monster"],
            "recommendation_score": 115.0,
            "reason": "Longue explication du moteur.",
        }
        expected = "Thèmes en commun : Psychological, Mystery · Genres en commun : Drama, Suspense"
        self.assertEqual(compact_evidence(item), expected)
        self.assertNotIn("Monster", compact_evidence(item))
        self.assertNotIn("%", compact_evidence(item))

    def test_empty_evidence_does_not_invent_a_match(self):
        text = compact_evidence({"score": 9.9, "recommendation_score": 180})
        self.assertIn("consulte le détail", text)
        self.assertNotIn("100", text)
        self.assertNotIn("%", text)

    def test_community_signal_is_used_when_present(self):
        self.assertIn(
            "Aussi conseillé depuis Berserk",
            compact_evidence({"community_recommended_from": ["Berserk"]}),
        )

    def test_no_mutation_of_recommendations(self):
        item = {
            "common_genres": ["Adventure", "Drama", "Action"],
            "common_themes": ["Mystery"],
            "community_recommended_from": [],
        }
        original = copy.deepcopy(item)
        compact_evidence(item)
        self.assertEqual(item, original)

    def test_goals_match_existing_backend_codes(self):
        self.assertEqual(
            set(GOALS.values()),
            {"SIMILAR_SAFE", "READ_NEXT", "SHORT_FINISHED"},
        )
        self.assertEqual(len(GOAL_LABELS), len(GOALS))
        self.assertEqual(GOAL_LABELS["SHORT_FINISHED"], "Série terminée / plutôt courte")


if __name__ == "__main__":
    unittest.main()
