"""Read-only coverage audit does not infer a French publication total."""
import unittest
from apps.api.app.bnf_edition_audit import volume_from_title, analyze


class BnfEditionAuditTests(unittest.TestCase):
    def test_extracts_explicit_volume_numbers(self):
        self.assertEqual(volume_from_title("Berserk. 43 (collector)"), 43)
        self.assertEqual(volume_from_title("Berserk. 24 / Kentaro Miura"), 24)
        self.assertEqual(volume_from_title("Berserk tome 03"), 3)
        self.assertEqual(volume_from_title("Berserk vol. 7"), 7)
        self.assertIsNone(volume_from_title("Berserk intégrale"))

    def test_separates_editions_and_only_reports_internal_gaps(self):
        report = analyze([
            {"isbn13":"9780000000001", "title_fr":"Berserk. 24 / Kentaro", "edition_kind_suggested":"UNKNOWN"},
            {"isbn13":"9780000000002", "title_fr":"Berserk. 26 / Kentaro", "edition_kind_suggested":"UNKNOWN"},
            {"isbn13":"9780000000003", "title_fr":"Berserk. 43 (collector)", "edition_kind_suggested":"COLLECTOR"},
            {"isbn13":"9780000000004", "title_fr":"Berserk Perfect", "edition_kind_suggested":"PERFECT"},
        ])
        self.assertFalse(report["is_exhaustive"])
        self.assertEqual(report["edition_groups"][0]["edition"], "COLLECTOR")
        self.assertEqual(report["edition_groups"][1]["edition"], "UNKNOWN")
        self.assertEqual(report["edition_groups"][1]["unseen_numbers_between_min_max"], [25])
        self.assertEqual(len(report["unparsed"]), 1)


if __name__ == "__main__":
    unittest.main()
