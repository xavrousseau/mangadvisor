"""Regression tests from the real Berserk candidate audit, all read-only."""
from __future__ import annotations

import unittest

from apps.api.app.bnf_candidate_quality import classify_candidate
from apps.api.app.bnf_candidate_review import review


def row(title, isbn="9782344067802", language=None, edition="UNKNOWN"):
    return {"isbn13": isbn, "title_fr": title, "publisher_fr": "Glénat",
            "language_recorded": language, "edition_kind_suggested": edition}


class CandidateQualityTests(unittest.TestCase):
    def test_prestige_is_distinct_from_unlabelled_and_collector(self):
        cases = [
            ("Berserk. 1 (Éd. prestige) Kentaro Miura", "PRESTIGE", 1),
            ("Berserk. 3 (Édition Prestige)", "PRESTIGE", 3),
            ("Berserk : 5 (Éd. prestige)", "PRESTIGE", None),
            ("Berserk. tome 6 (Edition prestige)", "PRESTIGE", 6),
            ("Berserk. 42 (Éd. collector)", "COLLECTOR", 42),
            ("Berserk. 42 / Kentaro Miura", "UNKNOWN", 42),
        ]
        for title, edition, volume in cases:
            with self.subTest(title=title):
                found = classify_candidate(row(title), ["Berserk"])
                self.assertEqual(found["edition_suggested"], edition)
                self.assertEqual(found["volume_suggested"], volume)
                self.assertFalse(found["registration_ready"])

    def test_other_work_is_rejected_from_main_series_matches(self):
        for title in ("Berserk of gluttony. 10", "Berserk of Gluttony. 12"):
            found = classify_candidate(row(title), ["Berserk"])
            self.assertEqual(found["work_status"], "REJECT_DIFFERENT_WORK")
            self.assertFalse(found["needs_manual_review"])

    def test_artbook_is_a_derivative_not_classic_tome(self):
        found = classify_candidate(row("Berserk : illustrations file"), ["Berserk"])
        self.assertEqual(found["work_status"], "REVIEW_DERIVATIVE")
        self.assertIsNone(found["volume_suggested"])
        self.assertFalse(found["registration_ready"])

    def test_language_is_declared_not_inferred_from_publisher(self):
        for text, expected in [
            (None, "UNKNOWN"),
            ("fre", "FRENCH_DECLARED"),
            ("français", "FRENCH_DECLARED"),
            ("eng", "NON_FRENCH_DECLARED"),
            ("fre ; eng", "MULTILINGUAL_REVIEW"),
            ("und", "UNRECOGNIZED"),
        ]:
            with self.subTest(language=text):
                found = classify_candidate(row("Berserk. 41", language=text), ["Berserk"])
                self.assertEqual(found["language_status"], expected)

    def test_review_does_not_mutate_or_validate_records(self):
        entries = [row("Berserk of gluttony. 10"), row("Berserk. 1 (Éd. prestige)")]
        before = [dict(e) for e in entries]
        result = review(entries, ["Berserk"])
        self.assertEqual(entries, before)
        self.assertEqual(result["total_staged"], 2)
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["work_matched"])
        self.assertFalse(result["edition_matched"])


if __name__ == "__main__":
    unittest.main()
