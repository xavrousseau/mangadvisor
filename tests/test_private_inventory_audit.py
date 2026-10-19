"""Synthetic-only tests: private inventory never appears in version control."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.local.private_inventory_audit import (
    normalized, work_title, classify, read_inventory, assert_local_api, run,
)


class PrivateInventoryAuditTests(unittest.TestCase):
    def test_parenthetical_edition_counts_keep_two_physical_rows(self):
        self.assertEqual(work_title("Dragon Ball (34 tomes)"),"Dragon Ball")
        self.assertEqual(work_title("Dragon Ball (42 tomes)"),"Dragon Ball")
        self.assertEqual(work_title("Kuroko's Basket Extra Game"),
                         "Kuroko's Basket Extra Game")
        self.assertEqual(normalized("L’Attaque des Titans"),
                         normalized("L'Attaque des Titans"))
        self.assertNotEqual(normalized("Tokyo Ghoul"),
                            normalized("Tokyo Ghoul:RE"))

    def test_label_matching_is_conservative_and_discloses_ambiguity(self):
        possible=[{"id":11,"title":"Dragon Ball","title_english":"Dragon Ball"}]
        matched=classify("Dragon Ball (34 tomes)",possible)
        self.assertEqual(matched["status"],"label_exact_unique")
        self.assertFalse("isbn13" in matched)
        self.assertIn("non vérifiés",matched["notes"])
        self.assertEqual(classify("Unrelated Series",possible)["status"],
                         "manual_check")
        dubious=classify("Dragon Ball",[
            {"id":11,"title":"Dragon Ball"},
            {"id":12,"title":"Dragon Ball"},
        ])
        self.assertEqual(dubious["status"],"ambiguous")
        self.assertIsNone(dubious["catalogue_id"])

    def test_inventory_detects_mismatch_without_adding_reading_status(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"sample.csv"
            with source.open("w",encoding="utf-8-sig",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=[
                    "collection","tomes_principaux","doublons_identiques",
                    "autres_editions_a_identifier","total_physique_estime",
                    "etat_releve",
                ])
                writer.writeheader()
                writer.writerow({
                    "collection":"Dragon Ball (42 tomes)",
                    "tomes_principaux":42,
                    "doublons_identiques":0,
                    "autres_editions_a_identifier":0,
                    "total_physique_estime":42,
                    "etat_releve":"Pas de mention en cours",
                })
            inventory=read_inventory(source)
            self.assertEqual(len(inventory),1)
            self.assertEqual(inventory[0]["tomes_principaux"],42)
            offline=run(inventory,"",offline=True)
            self.assertFalse(offline["metadata"]["reading_status_available"])
            self.assertFalse(offline["metadata"]["isbn_identifiers_available"])
            self.assertIsNone(offline["catalogue_coverage"])
            text=source.read_text(encoding="utf-8-sig").replace(",42,",",43,",1)
            source.write_text(text,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"total physique non cohérent"):
                read_inventory(source)

    def test_public_internet_and_credentials_are_refused(self):
        for address in (
            "https://localhost:8000", "http://example.org:8000",
            "http://127.0.0.1:8000?token=secret",
            "http://user:pass@localhost:8000",
            "http://192.168.1.33:8000",
        ):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    assert_local_api(address)
        self.assertEqual(assert_local_api("http://api:8000"),
                         "http://api:8000")

    def test_real_api_path_is_read_only_and_owned_overlap_is_reported(self):
        inventory=[{"collection":"Test Title","tomes_principaux":5,
                    "doublons_identiques":1,
                    "autres_editions_a_identifier":0,
                    "total_physique_estime":6}]
        calls=[]
        def fake_fetch(url,payload=None):
            calls.append((url,payload))
            if "/mangas?" in url:
                return {"items":[{"id":80,"title":"Test Title"}]}
            return {"status":"results","recommendations":[
                {"id":80,"title":"Test Title"},
                {"id":81,"title":"Unknown Book"}],
                "quality_diagnostic":{"unique_recorded_tags":2}}
        with patch("tests.local.private_inventory_audit.fetch",side_effect=fake_fetch):
            output=run(inventory,"http://127.0.0.1:8000")
        self.assertEqual(output["catalogue_coverage"]["exact_unique_entries"],1)
        self.assertEqual(len(output["recommendation_checks"]),3)
        self.assertTrue(all(c["listed_owned_titles_suggested"]
                            for c in output["recommendation_checks"]))
        self.assertTrue(all(c["duplicate_ids_in_response"]==0
                            for c in output["recommendation_checks"]))
        self.assertEqual(sum("/advisor/message" in u for u,_ in calls),3)
        self.assertFalse(any("/feedback" in u for u,_ in calls))
        self.assertFalse(any("/library" in u for u,_ in calls))


if __name__ == "__main__":
    unittest.main()
