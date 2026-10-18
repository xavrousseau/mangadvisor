"""Conversation parsing must never invent facts or weaken restrictions silently."""
import unittest

from pydantic import ValidationError

from apps.api.app.advisor import (
    AdvisorContext, AdvisorRequest, interpret, match_mood, score_candidates,
)


class ConversationalAdvisorTests(unittest.TestCase):
    def test_complex_request_and_soft_french_preference(self):
        text=("Je cherche un manga mature avec une intrigue prenante, "
              "pas trop long, terminé, idéalement disponible en français.")
        result, changes, more, warnings = interpret(text, AdvisorContext())
        self.assertEqual(result.mood, "MYSTERY")
        self.assertEqual(result.length, "SHORT")
        self.assertIs(result.only_finished, True)
        self.assertEqual(result.french, "PREFER")
        self.assertFalse(more)
        self.assertIn("maturity_not_verified", warnings)
        self.assertIn("french", changes)

    def test_followup_preserves_previous_filters_and_can_change_one(self):
        previous, _, _, _ = interpret(
            "Je cherche un mystère terminé en français", AdvisorContext()
        )
        next_context, changes, _, _ = interpret("Finalement plutôt long", previous)
        self.assertEqual(changes, ["length"])
        self.assertEqual(next_context.mood, "MYSTERY")
        self.assertEqual(next_context.french, "REQUIRE")
        self.assertIs(next_context.only_finished, True)
        self.assertEqual(next_context.length, "LONG")

    def test_avoid_romance_is_not_positive_mood(self):
        ctx, changes, _, _ = interpret(
            "Je veux du mystère mais sans romance", AdvisorContext()
        )
        self.assertEqual(ctx.mood, "MYSTERY")
        self.assertTrue(ctx.avoid_romance)
        self.assertIn("avoid_romance",changes)

    def test_unfinished_and_relaxation_have_priority(self):
        ctx, changes, _, _ = interpret(
            "Je cherche une série pas forcément terminée", AdvisorContext(
                mood="DARK", only_finished=True)
        )
        self.assertIsNone(ctx.only_finished)
        self.assertEqual(ctx.mood,"DARK")
        another,_,_,_=interpret("Je veux une série en cours de publication",ctx)
        self.assertIs(another.only_finished,False)

    def test_more_and_reset(self):
        ctx,changes,more,_=interpret("Montre-m'en d'autres",AdvisorContext(mood="ACTION"))
        self.assertTrue(more)
        self.assertFalse(changes)
        self.assertEqual(ctx.mood,"ACTION")
        reset,_,_,_=interpret("Recommençons, plutôt du fantastique",ctx)
        self.assertEqual(reset.mood,"FANTASY")
        self.assertEqual(reset.french,"ANY")

    def test_verification_required_not_commercial_availability(self):
        ctx,_,_,_=interpret("En français obligatoire",AdvisorContext(mood="MYSTERY"))
        self.assertEqual(ctx.french,"REQUIRE")
        ctx,_,_,_=interpret("idéalement en français",ctx)
        self.assertEqual(ctx.french,"PREFER")

    def test_bounded_api_and_unrecognized(self):
        with self.assertRaises(ValidationError):
            AdvisorRequest(message="x")
        with self.assertRaises(ValidationError):
            AdvisorRequest(message="a"*501)
        ctx,changes,_,_=interpret("Surprends-moi avec un chef-d'œuvre",AdvisorContext())
        self.assertIsNone(ctx.mood)
        self.assertEqual(changes,[])

    def test_rank_requires_each_requested_mood_and_source_tags(self):
        candidates=[
            dict(id=1,title="A",genres=["Action"],themes=[],score=9,popularity=1,
                 french_record_count=0),
            dict(id=2,title="B",genres=["Action"],themes=["Mystery"],score=8,popularity=20,
                 french_record_count=1),
            dict(id=3,title="C",genres=["Adventure"],themes=["Mystery"],score=7.8,popularity=200,
                 french_record_count=0),
        ]
        ctx=AdvisorContext(mood="ACTION",secondary_mood="MYSTERY",french="PREFER")
        selected=score_candidates(candidates,ctx,{"genres":set(),"themes":set()},6)
        self.assertEqual([m["id"] for m in selected],[2,3])
        self.assertTrue(selected[0]["french_recorded"])
        self.assertEqual(selected[0]["mood_matches"]["themes"],["Mystery"])
        self.assertIsNone(selected[0]["ranking_score"])
        self.assertEqual(match_mood(candidates[0],"MYSTERY"),
                         {"genres":[],"themes":[]})


if __name__ == "__main__":
    unittest.main()
