"""Pilot orchestration and ISBN evidence safeguards; no external network."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock, patch

from pipelines.engine.scripts import bibliography_pipeline as pipeline


class PipelineTests(unittest.TestCase):
    def test_bnf_scrinis_common_isbn_remains_unconfirmed(self):
        client = Mock()
        client.call.return_value = {"status": "OK", "data": {
            "status": "OK", "id": "42", "book_references": [
                {"isbn13": "9782344067802", "lang": "fr", "medium": "print"}],
            "book_references_truncated": False}}
        rows = [
            {"isbn13": "9782344067802",
             "work_status": "REVIEW_VOLUME_CANDIDATE",
             "language_status": "FRENCH_DECLARED"},
            {"isbn13": "9782487369078",
             "work_status": "REJECT_DIFFERENT_WORK",
             "language_status": "FRENCH_DECLARED"},
        ]
        output = pipeline.scrinis_isbn_evidence(
            {"scrinis_public_n": 42}, rows, client)
        self.assertEqual(output["status"], "COMPARED")
        self.assertEqual(output["correlation_counts"], {
            "ISBN_IN_BOTH_SOURCES": 1, "DIFFERENT_WORK": 1})
        self.assertNotIn("registration_ready", output)

    def test_unverified_scrinis_work_never_cross_matches(self):
        client = Mock()
        output = pipeline.scrinis_isbn_evidence(None, [], client)
        self.assertEqual(output["status"], "NO_VERIFIED_SCRINIS_WORK")
        client.call.assert_not_called()

    def test_supplier_id_conflict(self):
        client = Mock()
        client.call.return_value = {"status": "OK", "data": {
            "status": "OK", "id": "99",
            "book_references": [{"isbn13": "9782344067802"}]}}
        output = pipeline.scrinis_isbn_evidence(
            {"scrinis_public_n": 42}, [], client)
        self.assertEqual(output["status"], "SCRINIS_ID_MISMATCH")

    def test_full_scan_requires_single_explicit_manga(self):
        with self.assertRaises(ValueError):
            pipeline.run_pilot(pages=10)
        with self.assertRaises(ValueError):
            pipeline.run_pilot(pages=10, manga_ids=[1, 2])
        with self.assertRaises(ValueError):
            pipeline.run_pilot(limit=11)
        with self.assertRaises(ValueError):
            pipeline.run_pilot(manga_ids=[1, 1])

    def test_report_only_never_calls_suppliers_or_writes(self):
        fake_conn = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_conn
        with patch.object(pipeline, "connect_database", return_value=fake_context), \
             patch.object(pipeline, "select_ids", return_value=[2]), \
             patch.object(pipeline, "load_work_evidence", return_value=(
                 {"source_mal_id": 2, "title": "Berserk", "title_english": None,
                  "title_japanese": None}, [], None)), \
             patch.object(pipeline, "run_bnf") as bnf, \
             patch.object(pipeline, "run_scrinis") as scrinis:
            output = pipeline.run_pilot(manga_ids=[2], bnf=False, scrinis=False)
            bnf.assert_not_called()
            scrinis.assert_not_called()
            self.assertEqual(output["works"][0]["total_candidates"], 0)
            self.assertEqual(output["user_inventory_written"], 0)


if __name__ == "__main__":
    unittest.main()
