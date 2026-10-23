"""Conservative evaluation of manga candidate retrieval and book-level evidence.

This is a synthetic/public-name regression corpus, NOT the user's 48-owner-row
ground truth. A green CI does not prove 95% real-world matching accuracy.
"""
from __future__ import annotations
import unittest

from apps.api.app.matching_quality import (
    score_candidate, rank_candidates, search_patterns,
    classify_bnf_candidate_for_work, summarize_bnf_quality,
)


def work(ident, title, kind="Manga", volumes=None, **extras):
    return {"id":ident,"title":title,"title_english":None,
            "title_japanese":None,"manga_type":kind,"volumes":volumes,
            "source_mal_id":ident,**extras}


def alias(title, source):
    return [{"alias":title,"source_name":source,"source_id":"id-test"}]


class MatchQualityTests(unittest.TestCase):
    def test_search_uses_postgres_word_boundaries_and_never_bare_substring(self):
        self.assertEqual(search_patterns(["eri","adieu"]),[r"\meri\M",r"\madieu\M"])
        self.assertEqual(search_patterns(["eri.*","x"]),[])
        self.assertEqual(search_patterns(["eri","dragon"]),[r"\meri\M",r"\mdragon\M"])

    def test_adieu_eri_discovery_ranks_genuine_title_above_noisy_popular_series(self):
        options=[
            work(878,"Blue Period"),work(927,"Bakemonogatari"),
            work(1145,"Sayonara Eri",volumes=1),
            work(8097,"Isekaigaeri no Yuusha ga Gendai Saikyou!"),
            work(359,"Zaregoto Series",kind="Light Novel"),
            work(2422,"Aiki"),work(53,"Fushigi Yuugi"),
        ]
        out=rank_candidates("Adieu Eri",options,1)
        self.assertEqual(out["candidates"][0]["id"],1145)
        self.assertEqual(out["status"],"AMBIGUOUS_OR_INCOMPLETE")
        self.assertLess(out["top_score"],80)
        self.assertFalse(out["correspondence_certified"])
        self.assertEqual(out["candidates"][0]["ranking"]["basis"],"WHOLE_WORD_DISCOVERY")

    def test_radiant_and_fairy_tail_false_aliases_are_deprioritized(self):
        wrong=work(118051,"Ikujitsu",volumes=1,
                   matching_alias_sources=alias("Radiant","TENRAI_MAL"))
        r=score_candidate("Radiant",wrong,19)
        self.assertIn("CATALOGUE_VOLUME_DISCREPANCY_NOT_IDENTITY_PROOF",r["warnings"])
        self.assertEqual(r["basis"],"EXACT_UNVERIFIED_ALIAS")
        fairy=rank_candidates("Fairy Tail",[
            work(63341,"Bishoujo Hatsu Shibori",volumes=1,
                 matching_alias_sources=alias("Fairy Tail","TENRAI_MAL")),
            work(78003,"Fairy Tail",kind="Light Novel",volumes=3),
            work(598,"Fairy Tail",volumes=63)
        ],63)
        self.assertEqual(fairy["candidates"][0]["id"],598)
        self.assertEqual(fairy["status"],"STRONG_REVIEW_SUGGESTION")
        self.assertFalse(fairy["correspondence_certified"])

    def test_canonical_collision_without_evidence_must_abstain(self):
        results=rank_candidates("Wind Breaker",[
            work(103237,"Wind Breaker",kind="Manhwa"),
            work(133081,"Wind Breaker",kind="Manga"),
        ],23)
        self.assertEqual(results["top_score"],results["runner_up_score"])
        self.assertEqual(results["status"],"AMBIGUOUS_OR_INCOMPLETE")

    def test_solo_leveling_manhwa_not_confused_with_novel(self):
        results=rank_candidates("Solo Leveling",[
            work(119184,"Solo Leveling",kind="Novel",volumes=13),
            work(121496,"Solo Leveling",kind="Manhwa",volumes=15),
        ],21)
        self.assertEqual(results["candidates"][0]["id"],121496)
        self.assertEqual(results["status"],"STRONG_REVIEW_SUGGESTION")
        self.assertFalse(results["correspondence_certified"])

    def test_checked_alias_is_stronger_than_unknown_alias_but_not_an_identity(self):
        results=rank_candidates("Demon Slayer",[
            work(1,"Wrong manga",matching_alias_sources=alias("Demon Slayer","TENRAI_MAL")),
            work(96792,"Kimetsu no Yaiba",volumes=23,
                 matching_alias_sources=alias("Demon Slayer","TENRAI_MAL_TYPED")),
        ],23)
        self.assertEqual(results["candidates"][0]["id"],96792)
        self.assertFalse(results["candidates"][0]["ranking"]["identity_confirmed"])

    def test_bnf_author_match_is_not_work_proof(self):
        cases=[
            ("Black / Tite Kubo","EXCLUDE_DIFFERENT_WORK"),
            ("Friend / Tite Kubo","EXCLUDE_DIFFERENT_WORK"),
            ("Bleach. 1 / Tite Kubo","POTENTIAL_FRENCH_VOLUME_REVIEW"),
            ("Bleach : roman 1 / Tite Kubo","REVIEW_SEPARATE_DERIVATIVE"),
        ]
        for title, bucket in cases:
            with self.subTest(title=title):
                record={"manga_id":12,"isbn13":"9782344074282","title_fr":title,
                    "language_recorded":"fre","edition_kind_suggested":"UNKNOWN",
                    "author_fr":"Tite Kubo",
                    "source_url":"https://catalogue.bnf.fr/ark:/12148/cb48845861d"}
                actual=classify_bnf_candidate_for_work(record,["Bleach"],["Tite Kubo"])
                self.assertEqual(actual["quality_bucket"],bucket)
                self.assertFalse(actual["book_assignment_confirmed"])
                self.assertFalse(actual["owned"])

    def test_naruto_subtitle_is_not_a_series_volume(self):
        record={"isbn13":"9782505017653",
                "title_fr":"Naruto vs Hitachi !! / Masashi Kishimoto",
                "language_recorded":"fre",
                "author_fr":"Masashi Kishimoto",
                "source_url":"https://catalogue.bnf.fr/ark:/12148/cb43555472z"}
        actual=classify_bnf_candidate_for_work(record,["Naruto"],["Masashi Kishimoto"])
        self.assertEqual(actual["quality_bucket"],"REVIEW_DIFFERENT_SUBTITLE_OR_WORK")
        self.assertIsNone(actual["volume_suggested"])

    def test_roman_number_is_not_assigned_to_manhwa_volume(self):
        record={"isbn13":"9782382880807",
                "title_fr":"Solo leveling. I / Chugong",
                "language_recorded":"fre","author_fr":"Chugong",
                "source_url":"https://catalogue.bnf.fr/ark:/12148/cb474999777"}
        result=classify_bnf_candidate_for_work(record,["Solo Leveling"],["Dubu"])
        self.assertIn(result["quality_bucket"],(
            "REVIEW_DIFFERENT_SUBTITLE_OR_WORK","REVIEW_AUTHOR_CONFLICT"))
        self.assertIsNone(result["volume_suggested"])

    def test_bnf_audit_does_not_count_other_series_as_verified_isbns(self):
        records=[{
            "isbn13":"9782344001844","title_fr":"Tokyo Ghoul. 7",
            "language_recorded":"fre","source_url":"https://catalogue.bnf.fr/"
        },{
            "isbn13":"9782344012895","title_fr":"Black / Tite Kubo",
            "language_recorded":"fre","source_url":"https://catalogue.bnf.fr/"
        }]
        report=summarize_bnf_quality(records,["Bleach"])
        self.assertEqual(report["categories"]["EXCLUDE_DIFFERENT_WORK"],2)
        self.assertFalse(report["automatic_assignment"])


if __name__ == "__main__":
    unittest.main()
