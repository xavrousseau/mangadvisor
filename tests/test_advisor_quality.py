"""Mangadvisor 3.4: factual results quality and mandatory LLM intent guard."""
import json
import unittest

from apps.api.app.advisor import AdvisorContext
from apps.api.app.advisor_ai import parse_intent_response, reconcile_ai_intent
from apps.api.app.advisor_quality import quality_diagnostic


class AdvisorQualityTests(unittest.TestCase):
    def test_metrics_are_descriptive_deterministic_and_tag_sourced(self):
        rows=[
            {"id":1,"genres":["Mystery"],"themes":["Psychological"],
             "affinity_matches":{"genres":["Mystery"],"themes":[]},
             "french_recorded":True, "narrative_matches":[{"source":"catalog_tag"}]},
            {"id":2,"genres":["Mystery"],"themes":["Detective"],
             "affinity_matches":{"genres":[],"themes":[]},
             "french_recorded":False,"narrative_matches":[]},
            {"id":3,"genres":["Action"],"themes":["Survival"],
             "affinity_matches":{"genres":[],"themes":["Survival"]},
             "french_recorded":True,"narrative_matches":[]},
        ]
        q=quality_diagnostic(rows,examined=500,pool_limited=True,
                             personalized=True,mode="EXPLORE")
        self.assertEqual(q["scope"],"displayed_catalogue_results_only")
        self.assertEqual(q["examined_count"],500)
        self.assertTrue(q["candidate_pool_capped"])
        self.assertEqual(q["returned_count"],3)
        self.assertEqual(q["unique_manga_count"],3)
        self.assertEqual(q["unique_recorded_tags"],5)
        self.assertEqual(q["tag_evidence_count"],3)
        self.assertEqual(q["affinity_evidence_count"],2)
        self.assertEqual(q["french_isbn_record_count"],2)
        self.assertEqual(q["narrative_clue_evidence_count"],1)
        # Only the two mystery results share a catalog tag.
        self.assertEqual(q["mean_pairwise_tag_overlap"],0.111)
        self.assertEqual(q["pair_count_compared"],3)
        self.assertTrue(q["quality_is_not_a_probability"])

    def test_empty_and_one_result_have_no_fake_similarity(self):
        q=quality_diagnostic([],examined=0,pool_limited=False,
                             personalized=False,mode="BALANCED")
        self.assertEqual(q["returned_count"],0)
        self.assertIsNone(q["mean_pairwise_tag_overlap"])
        self.assertEqual(q["pair_count_compared"],0)
        q=quality_diagnostic([{"id":3,"genres":["Mystery"]}],
                             examined=1,pool_limited=False,
                             personalized=True,mode="CLOSE")
        self.assertEqual(q["tag_evidence_count"],1)
        self.assertIsNone(q["mean_pairwise_tag_overlap"])
        self.assertEqual(q["affinity_evidence_count"],0)

    def test_intent_guard_preserves_explicit_compound_user_request(self):
        prior=AdvisorContext(mood="MYSTERY", french="PREFER")
        # The local model incorrectly drops exclusions and compulsory French.
        hallucinated,changes,more=parse_intent_response(json.dumps({
            "updates":{"french":"ANY","avoid_horror":False,
                       "avoid_gore":False,"length":"ANY"},
            "more":False,"reset":False
        }),prior)
        result,recognized,_,warnings=reconcile_ai_intent(
            "Un mystère court, français obligatoire, sans horreur et sans gore",
            prior,hallucinated,changes,more,
        )
        self.assertEqual(result.mood,"MYSTERY")
        self.assertEqual(result.french,"REQUIRE")
        self.assertEqual(result.length,"SHORT")
        self.assertTrue(result.avoid_horror)
        self.assertTrue(result.avoid_gore)
        self.assertIn("french",recognized)
        self.assertEqual(warnings,[])

    def test_model_cannot_silently_remove_existing_mandatory_filters(self):
        prior=AdvisorContext(mood="MYSTERY",french="REQUIRE",
                             preferred_edition_kind="DELUXE",
                             require_edition_kind=True,avoid_horror=True)
        model=prior.model_copy(update={
            "french":"ANY", "require_edition_kind":False,"avoid_horror":False})
        safe,changes,_,_=reconcile_ai_intent("Montre-moi d'autres",prior,model,
                                             ["french","require_edition_kind",
                                              "avoid_horror"],True)
        self.assertEqual(safe.french,"REQUIRE")
        self.assertTrue(safe.avoid_horror)
        self.assertTrue(safe.require_edition_kind)
        self.assertEqual(safe.preferred_edition_kind,"DELUXE")

    def test_explicit_user_relaxation_or_reset_is_honored(self):
        prior=AdvisorContext(mood="MYSTERY", french="REQUIRE",
                             preferred_edition_kind="DELUXE",
                             require_edition_kind=True,avoid_horror=True)
        relaxed=prior.model_copy(update={
            "french":"ANY","avoid_horror":False,"require_edition_kind":False,
            "preferred_edition_kind":None})
        safe,changes,_,_=reconcile_ai_intent(
            "Peu importe la langue, avec horreur, tout format",
            prior,relaxed,["french","avoid_horror","preferred_edition_kind"],False)
        self.assertEqual(safe.french,"ANY")
        self.assertFalse(safe.avoid_horror)
        self.assertFalse(safe.require_edition_kind)
        self.assertIsNone(safe.preferred_edition_kind)
        restarted,changes,_,_=reconcile_ai_intent(
            "Recommençons avec de l'action",prior,
            prior.model_copy(update={"mood":"ACTION"}),["mood"],False)
        self.assertEqual(restarted.mood,"ACTION")
        self.assertEqual(restarted.french,"ANY")
        self.assertFalse(restarted.require_edition_kind)
        self.assertFalse(restarted.avoid_horror)

    def test_server_owned_library_mode_survives_model_reply(self):
        prior=AdvisorContext(profile_discovery=True,
                             recommendation_balance="EXPLORE")
        model=prior.model_copy(update={"recommendation_balance":"CLOSE"})
        result,changes,_,_=reconcile_ai_intent(
            "Surprends-moi avec une sélection inattendue",prior,model,
            ["recommendation_balance"],False)
        self.assertTrue(result.profile_discovery)
        self.assertEqual(result.recommendation_balance,"EXPLORE")


if __name__ == "__main__":
    unittest.main()
