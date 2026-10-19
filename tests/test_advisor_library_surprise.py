"""Mangadvisor 3.3: no invented preferences in library-first discovery."""
import json
import unittest

from apps.api.app.advisor import AdvisorContext, interpret, score_candidates
from apps.api.app.advisor_ai import LocalAiUnavailable, parse_intent_response


class LibraryFirstSurpriseTests(unittest.TestCase):
    def test_explicit_surprise_uses_library_without_hallucinating_mood(self):
        ctx, changes, more, _ = interpret(
            "Surprends-moi selon mes goûts", AdvisorContext()
        )
        self.assertIsNone(ctx.mood)
        self.assertTrue(ctx.profile_discovery)
        self.assertTrue(ctx.use_library)
        self.assertEqual(ctx.recommendation_balance, "EXPLORE")
        self.assertIn("profile_discovery", changes)
        self.assertFalse(more)

    def test_followup_preserves_strict_constraints_and_source(self):
        ctx, _, _, _ = interpret("Surprends-moi", AdvisorContext())
        second, changes, _, _ = interpret(
            "En édition Deluxe obligatoire, série terminée, sans horreur",ctx
        )
        self.assertTrue(second.profile_discovery)
        self.assertTrue(second.require_edition_kind)
        self.assertEqual(second.preferred_edition_kind,"DELUXE")
        self.assertIs(second.only_finished,True)
        self.assertTrue(second.avoid_horror)
        self.assertIn("preferred_edition_kind",changes)

    def test_named_mood_returns_to_mood_first_search(self):
        ctx, _, _, _ = interpret("Surprise me",AdvisorContext())
        next_,changes,_,_=interpret("Finalement une aventure fantastique",ctx)
        self.assertFalse(next_.profile_discovery)
        self.assertEqual(next_.mood,"ACTION")
        self.assertEqual(next_.secondary_mood,"FANTASY")
        self.assertIn("mood",changes)

    def test_explicit_library_off_never_uses_profile(self):
        ctx,changes,_,_=interpret("Surprends-moi mais sans mes goûts",AdvisorContext())
        self.assertFalse(ctx.use_library)
        self.assertTrue(ctx.profile_discovery)
        self.assertIn("use_library",changes)

    def test_library_only_candidates_require_actual_recorded_affinity(self):
        rows=[
            dict(id=1,title="Shared tags",genres=["Mystery"],themes=["Detective"],
                 score=9.0,popularity=1,synopsis="Not relevant"),
            dict(id=2,title="No shared tags",genres=["Romance"],themes=["Pets"],
                 score=9.9,popularity=2,synopsis="Unrelated"),
            dict(id=3,title="Other compatible",genres=["Mystery"],themes=["Time Travel"],
                 score=8.0,popularity=3,synopsis="Unrelated"),
        ]
        prefs={"genres":{"mystery"},"themes":{"detective"}}
        context=AdvisorContext(profile_discovery=True,recommendation_balance="EXPLORE")
        recs=score_candidates(
            [row for row in rows
             if (set(map(str.casefold,row["genres"])) & prefs["genres"]
                 or set(map(str.casefold,row["themes"])) & prefs["themes"])],
            context,prefs,5
        )
        self.assertTrue(recs)
        self.assertEqual({x["id"] for x in recs},{1,3})
        self.assertTrue(all(x["affinity_matches"]["genres"] or
                            x["affinity_matches"]["themes"] for x in recs))
        self.assertTrue(all(x["mood_matches"]=={"genres":[],"themes":[]} for x in recs))
        self.assertTrue(all("synopsis" not in x for x in recs))

    def test_llm_cannot_outright_toggle_server_owned_profile_discovery(self):
        with self.assertRaises(LocalAiUnavailable):
            parse_intent_response(json.dumps({"updates":{"profile_discovery":True}}),
                                  AdvisorContext())
        updated,changes,_=parse_intent_response(json.dumps(
            {"updates":{"french":"REQUIRE","recommendation_balance":"EXPLORE"}}
        ),AdvisorContext(profile_discovery=True))
        self.assertTrue(updated.profile_discovery)
        self.assertEqual(updated.french,"REQUIRE")
        self.assertIn("french",changes)


if __name__=="__main__":
    unittest.main()
