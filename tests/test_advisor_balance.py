"""Mangadvisor 3.1: diverse picks are grounded, deterministic and never relax filters."""
import json
import unittest

from apps.api.app.advisor import (
    AdvisorContext, interpret, score_candidates, select_balanced_candidates,
)
from apps.api.app.advisor_ai import parse_intent_response


EMPTY_PREFERENCES = {"genres": set(), "themes": set()}


def candidate(id, score, themes, *, genres=None):
    return {
        "id": id, "title": "Demo " + str(id),
        "genres": list(genres or ["Mystery"]),
        "themes": themes, "score": score, "popularity": id,
        "french_record_count": 0,
        "preferred_format_record_count": 0,
        "synopsis": "",
    }


class BalanceTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            candidate(1, 9.2, ["Psychological"]),
            candidate(2, 9.1, ["Psychological"]),
            candidate(3, 8.7, ["Detective"]),
            candidate(4, 8.3, ["Time Travel"]),
        ]

    def recs(self, mode, rows=None, **extra):
        context = AdvisorContext(mood="MYSTERY", recommendation_balance=mode, **extra)
        return score_candidates(rows or self.candidates, context, EMPTY_PREFERENCES, 2)

    def test_close_preserves_relevance_order(self):
        picks=self.recs("CLOSE")
        self.assertEqual([p["id"] for p in picks], [1,2])
        self.assertEqual(picks[0]["variety_evidence"],[])
        self.assertEqual(picks[1]["variety_evidence"],[])

    def test_balanced_and_explore_reduce_redundancy_without_randomness(self):
        for mode in ("BALANCED","EXPLORE"):
            with self.subTest(mode=mode):
                one=self.recs(mode)
                two=self.recs(mode)
                self.assertEqual([p["id"] for p in one],[1,3])
                self.assertEqual([p["id"] for p in two],[1,3])
                self.assertEqual(one[1]["variety_evidence"],["Detective"])
                self.assertEqual(one[1]["mood_matches"]["themes"],["Detective"])
                self.assertIsNone(one[1]["ranking_score"])
                self.assertNotIn("synopsis",one[1])

    def test_hard_exclusions_and_required_french_format_never_relax(self):
        rows=[
            candidate(1,9.9,["Psychological"],genres=["Mystery","Horror"]),
            candidate(2,9.6,["Gore"],genres=["Mystery"]),
            candidate(3,8.9,["Detective"],genres=["Mystery"]),
            candidate(4,8.8,["Psychological"],genres=["Mystery"]),
        ]
        recs=self.recs("EXPLORE",rows,avoid_horror=True,avoid_gore=True)
        self.assertTrue(recs)
        self.assertTrue({r["id"] for r in recs}.issubset({3,4}))
        self.assertTrue(all(r["mood_matches"]["genres"] for r in recs))
        self.assertEqual(select_balanced_candidates([], "EXPLORE", 6),[])

    def test_quality_floor_keeps_extremely_weak_matches_behind_strong(self):
        rows=[
            candidate(1,9.0,["Psychological","Detective"]),
            candidate(2,8.8,["Psychological","Detective"]),
            candidate(3,0.1,[],genres=["Mystery"]),
        ]
        # This is a pure selector test (SQL is responsible for min_score filtering).
        result=score_candidates(rows, AdvisorContext(
            mood="MYSTERY",min_score=0, recommendation_balance="EXPLORE"
        ),EMPTY_PREFERENCES,2)
        self.assertEqual(result[0]["id"],1)
        self.assertEqual(result[1]["id"],2)

    def test_natural_language_modes_are_conversational_and_keep_requirements(self):
        start=AdvisorContext(mood="MYSTERY",french="REQUIRE",
            preferred_edition_kind="DELUXE",require_edition_kind=True,
            avoid_horror=True)
        for phrase,mode in [
            ("Surprends-moi avec une sélection inattendue","EXPLORE"),
            ("Je veux une sélection variée","BALANCED"),
            ("Je veux une sélection très proche de mes goûts","CLOSE"),
            ("Surprise me with unexpected manga","EXPLORE"),
        ]:
            with self.subTest(phrase=phrase):
                ctx,changes,more,_=interpret(phrase,start)
                self.assertEqual(ctx.recommendation_balance,mode)
                self.assertEqual(ctx.french,"REQUIRE")
                self.assertTrue(ctx.require_edition_kind)
                self.assertTrue(ctx.avoid_horror)
                self.assertFalse(more)
                self.assertIn("recommendation_balance",changes)

    def test_local_ai_can_request_balance_but_not_filter_bypass(self):
        previous=AdvisorContext(mood="MYSTERY",french="REQUIRE",
                                avoid_gore=True)
        state,changes,more=parse_intent_response(json.dumps({
            "updates":{"recommendation_balance":"EXPLORE"},
            "more":False, "reset":False,
        }),previous)
        self.assertEqual(state.recommendation_balance,"EXPLORE")
        self.assertEqual(state.french,"REQUIRE")
        self.assertTrue(state.avoid_gore)
        self.assertEqual(changes,["recommendation_balance"])
        self.assertFalse(more)

    def test_invalid_balance_rejected_by_model_validation(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            AdvisorContext(recommendation_balance="ANYTHING")
        from apps.api.app.advisor_ai import LocalAiUnavailable
        with self.assertRaises(LocalAiUnavailable):
            parse_intent_response(
                '{"updates":{"recommendation_balance":"SELL_MANGA"}}',
                AdvisorContext(mood="MYSTERY"),
            )


if __name__=="__main__":
    unittest.main()
