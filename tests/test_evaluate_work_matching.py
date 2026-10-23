"""Guard against overstating 95% when only a handful of fixtures pass."""
from __future__ import annotations
import unittest
from tools.evaluate_work_matching import evaluate


class IndependentThresholdTests(unittest.TestCase):
    def test_tiny_perfect_fixture_does_not_claim_95_percent(self):
        gold=[{"case_id":"a","expected_manga_id":11,
               "evidence_url":"https://myanimelist.net/manga/11"},
              {"case_id":"b","expected_manga_id":None,
               "evidence_url":"https://catalogue.bnf.fr/"}]
        predicted=[{"case_id":"a","suggested_manga_id":11,
                    "decision":"STRONG_REVIEW_SUGGESTION"},
                   {"case_id":"b","suggested_manga_id":None,"decision":"ABSTAIN"}]
        outcome=evaluate(gold,predicted)
        self.assertEqual(outcome["precision"],1.0)
        self.assertEqual(outcome["recall"],1.0)
        self.assertFalse(outcome["target_95_met"])
        self.assertFalse(outcome["sufficient_gold_and_predictions"])

    def test_forty_eight_cases_still_fail_below_precise_recall_threshold(self):
        gold=[{"case_id":str(i),"expected_manga_id":i+1,
               "evidence_url":"https://myanimelist.net/manga/"+str(i+1)}
              for i in range(48)]
        predicted=[{"case_id":str(i),
                    "suggested_manga_id":i+1 if i<46 else None,
                    "decision":"STRONG_REVIEW_SUGGESTION" if i<46 else "ABSTAIN"}
                   for i in range(48)]
        outcome=evaluate(gold,predicted)
        self.assertEqual(outcome["correct_suggestions"],46)
        self.assertTrue(outcome["target_95_met"])
        predicted[45]["suggested_manga_id"]=999
        predicted[44]["suggested_manga_id"]=998
        predicted[46]["suggested_manga_id"]=47
        predicted[46]["decision"]="STRONG_REVIEW_SUGGESTION"
        bad=evaluate(gold,predicted)
        self.assertFalse(bad["target_95_met"])
        self.assertEqual(bad["false_positives"],2)

    def test_omitted_labels_and_no_match_suggestions_cannot_fake_precision(self):
        gold=[{"case_id":str(i),"expected_manga_id":i+1 if i<25 else None,
               "evidence_url":"https://example.org/verified/"+str(i)}
              for i in range(48)]
        predicted=[{"case_id":str(i),
                    "suggested_manga_id":i+1 if i<25 else None,
                    "decision":"STRONG_REVIEW_SUGGESTION" if i<25 else "ABSTAIN"}
                   for i in range(48)]
        self.assertTrue(evaluate(gold,predicted)["target_95_met"])
        for i in (46,47):
            predicted[i]={"case_id":str(i),"suggested_manga_id":400+i,
                          "decision":"STRONG_REVIEW_SUGGESTION"}
        out=evaluate(gold,predicted)
        self.assertEqual(out["false_links_to_unindexed_works"],2)
        self.assertFalse(out["target_95_met"])
        self.assertFalse(evaluate(gold,predicted[:-1])["target_95_met"])

    def test_duplicate_case_ids_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([{"case_id":"x","expected_manga_id":1},
                      {"case_id":"x","expected_manga_id":2}],[])


if __name__ == "__main__":
    unittest.main()

