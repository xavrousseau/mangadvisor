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

    def test_edition_and_volume_disagreement_override_isbn_overlap(self):
        """Dragon Ball Deluxe and a distinct edition must not be merged."""
        code = "9782344067802"
        candidate = {"isbn13": code, "title_fr": "Dragon Ball Deluxe, tome 1",
                     "work_status": "REVIEW_VOLUME_CANDIDATE",
                     "language_status": "FRENCH_DECLARED",
                     "volume_suggested": 1}
        def compare(label, volume):
            return pipeline.correlate_bnf_scrinis_isbns(
                [candidate], {code}, supplier_coverage="BOUNDED_SUPPLIER_DETAIL",
                supplier_references=[{"isbn13": code, "lang": "fr",
                                      "medium": "print", "edition_label": label,
                                      "volume_label": volume}])["isbn_correlations"][0]

        self.assertEqual(compare("Pastel", "1")["evidence_status"],
                         "ISBN_EDITION_CONFLICT_REVIEW")
        self.assertEqual(compare("Deluxe", "2")["evidence_status"],
                         "ISBN_VOLUME_CONFLICT_REVIEW")
        matched = compare("Deluxe", "Tome 1")
        self.assertEqual(matched["evidence_status"], "ISBN_IN_BOTH_SOURCES")
        self.assertEqual(matched["edition_volume_evidence"],
                         "FAMILY_AND_TOME_CONSISTENT_UNVERIFIED")
        self.assertFalse(matched["edition_identity_verified"])
        self.assertFalse(matched["isbn_ownership_verified"])

    def test_duplicate_supplier_isbn_with_incompatible_editions_is_conflict(self):
        code = "9782344067802"
        result = pipeline.correlate_bnf_scrinis_isbns(
            [{"isbn13": code, "title_fr": "Dragon Ball Deluxe, tome 1",
              "work_status": "REVIEW_VOLUME_CANDIDATE",
              "language_status": "FRENCH_DECLARED"}], {code},
            supplier_coverage="INCOMPLETE_SUPPLIER_DETAIL",
            supplier_references=[
                {"isbn13": code, "lang": "fr", "medium": "print",
                 "edition_label": "Deluxe", "volume_label": "1"},
                {"isbn13": code, "lang": "fr", "medium": "print",
                 "edition_label": "Pastel", "volume_label": "1"}])
        self.assertEqual(result["correlation_counts"],
                         {"ISBN_SUPPLIER_REFERENCE_CONFLICT_REVIEW": 1})
        self.assertEqual(result["confirmed_editions_written"], 0)
        self.assertEqual(result["ownership_mutations"], 0)

    def test_supplier_ebook_and_foreign_references_cannot_conflict_with_print(self):
        code = "9782344067802"
        result = pipeline.correlate_bnf_scrinis_isbns(
            [{"isbn13": code, "title_fr": "Dragon Ball Deluxe, tome 1",
              "work_status": "REVIEW_VOLUME_CANDIDATE",
              "language_status": "FRENCH_DECLARED"}], {code},
            supplier_coverage="BOUNDED_SUPPLIER_DETAIL",
            supplier_references=[
                {"isbn13": code, "lang": "ja", "medium": "print",
                 "edition_label": "Pastel", "volume_label": "9"},
                {"isbn13": code, "lang": "fr", "medium": "ebook",
                 "edition_label": "Pastel", "volume_label": "9"},
                {"isbn13": code, "lang": "fr", "medium": "print",
                 "edition_label": "Deluxe", "volume_label": "1"}])
        self.assertEqual(result["correlation_counts"], {"ISBN_IN_BOTH_SOURCES": 1})

    def test_blank_edition_never_implies_classic_or_tome(self):
        code = "9782344067802"
        result = pipeline.correlate_bnf_scrinis_isbns(
            [{"isbn13": code, "title_fr": "Dragon Ball",
              "work_status": "REVIEW_UNNUMBERED",
              "language_status": "FRENCH_DECLARED"}], {code},
            supplier_coverage="BOUNDED_SUPPLIER_DETAIL",
            supplier_references=[{"isbn13": code, "lang": "fr", "medium": "print",
                                  "edition_label": "", "volume_label": "2024"}])
        row = result["isbn_correlations"][0]
        self.assertEqual(row["edition_volume_evidence"],
                         "EDITION_AND_TOME_UNVERIFIED")
        self.assertFalse(row["edition_identity_verified"])

    def test_multilingual_bnf_cannot_be_presented_as_french_isbn_match(self):
        from apps.api.app.bnf_candidate_quality import classify_candidate
        isbn = "9782344067802"
        candidate = classify_candidate(
            {"isbn13": isbn, "title_fr": "Dragon Ball. 1",
             "language_recorded": "fre; eng"}, ["Dragon Ball"],
        )
        evidence = pipeline.correlate_bnf_scrinis_isbns(
            [candidate], {isbn}, supplier_coverage="BOUNDED_SUPPLIER_DETAIL",
            supplier_references=[{"isbn13": isbn, "lang": "fr", "medium": "print",
                                  "volume_label": "1"}],
        )
        self.assertEqual(evidence["isbn_correlations"][0]["evidence_status"], "LANGUAGE_REVIEW")
        self.assertEqual(evidence["confirmed_editions_written"], 0)
        self.assertEqual(evidence["ownership_mutations"], 0)

    def test_year_tokens_are_not_corroborated_as_tome_numbers(self):
        self.assertIsNone(pipeline._numbered_tome("Dragon Ball : 2024"))
        self.assertIsNone(pipeline._numbered_tome("Berserk. 1999"))
        self.assertEqual(pipeline._numbered_tome("Berserk. 42"), 42)

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

    def test_verified_french_alias_prevents_translated_title_false_negative(self):
        from apps.api.app.bnf_candidate_review import review
        sample = [{"isbn13": "9781234567897", "title_fr": "L'Attaque des Titans. 1",
                   "language_recorded": "fre", "edition_kind_suggested": "UNKNOWN"}]
        without = review(sample, ["Shingeki no Kyojin"])
        with_alias = review(sample, ["Shingeki no Kyojin", "L'Attaque des Titans"])
        self.assertEqual(without["work_status_counts"], {"REJECT_DIFFERENT_WORK": 1})
        self.assertEqual(with_alias["work_status_counts"], {"REVIEW_VOLUME_CANDIDATE": 1})
        self.assertFalse(with_alias["candidates"][0]["registration_ready"])

    def test_scrinis_triage_respects_ambiguity_and_retry(self):
        cases = [
            ({"already_has_source_french_alias": True, "previous_attempt_status": "MATCHED"},
             "USE_EXISTING_TITLE_EVIDENCE"),
            ({"previous_attempt_status": "AMBIGUOUS", "attempt_cooldown_active": True},
             "REVIEW_AMBIGUOUS_SOURCE_MATCH"),
            ({"previous_attempt_status": "DETAIL_UNAVAILABLE", "attempt_cooldown_active": True},
             "AWAIT_NORMAL_RETRY"),
            ({"previous_attempt_status": "DETAIL_UNAVAILABLE", "attempt_cooldown_active": False},
             "RETRY_DETAIL_WHEN_ELIGIBLE"),
            ({"previous_attempt_status": None, "attempt_cooldown_active": False},
             "ELIGIBLE_FOR_NORMAL_PROVIDER_SEARCH"),
        ]
        for state, expected in cases:
            with self.subTest(state=state):
                self.assertEqual(pipeline.next_scrinis_action(state), expected)

    def test_full_scan_requires_single_explicit_manga(self):
        with self.assertRaises(ValueError):
            pipeline.run_pilot(pages=10)
        with self.assertRaises(ValueError):
            pipeline.run_pilot(pages=10, manga_ids=[1, 2])
        with self.assertRaises(ValueError):
            pipeline.run_pilot(limit=11)
        with self.assertRaises(ValueError):
            pipeline.run_pilot(manga_ids=[1, 1])

    def test_cli_summary_hides_isbn_rows_unless_details_requested(self):
        import contextlib
        import io
        import json
        sample = {
            "selected_ids": [2],
            "works": [{"cross_source": {
                "status": "COMPARED",
                "correlation_counts": {"ISBN_IN_BOTH_SOURCES": 1},
                "isbn_correlations": [{"isbn13": "9782344067802",
                                       "evidence_status": "ISBN_IN_BOTH_SOURCES"}],
            }}],
        }
        with patch.object(pipeline, "run_pilot", return_value=sample):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline.main(["--report-only"]), 0)
            summary = json.loads(out.getvalue())
            self.assertEqual(summary["works"][0]["cross_source"]["isbn_correlations"], [])
            self.assertEqual(
                summary["works"][0]["cross_source"]["correlation_counts"],
                {"ISBN_IN_BOTH_SOURCES": 1},
            )
        detailed_sample = {
            "selected_ids": [2],
            "works": [{"cross_source": {
                "status": "COMPARED",
                "isbn_correlations": [{"isbn13": "9782344067802"}],
            }}],
        }
        with patch.object(pipeline, "run_pilot", return_value=detailed_sample):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline.main(["--report-only", "--details"]), 0)
            self.assertEqual(
                json.loads(out.getvalue())["works"][0]["cross_source"]["isbn_correlations"][0]["isbn13"],
                "9782344067802",
            )

    def test_details_shows_bnf_candidates_and_summary_omits_them(self):
        import contextlib
        import io
        import json

        candidate = {
            "isbn13": "9782344067802",
            "title_fr": "Exemple. Tome 1",
            "publisher_fr": "Editeur",
            "work_status": "REVIEW_VOLUME_CANDIDATE",
            "language_status": "FRENCH_DECLARED",
            "edition_suggested": "UNKNOWN",
            "volume_suggested": 1,
            "registration_ready": False,
        }

        def sample_report():
            return {
                "selected_ids": [2],
                "works": [{
                    "manga_id": 2,
                    "candidates": [candidate.copy()],
                    "cross_source": {"status": "NOT_REQUESTED", "isbn_correlations": []},
                }],
            }

        with patch.object(pipeline, "run_pilot", side_effect=lambda **kw: sample_report()):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline.main(["--report-only", "--details"]), 0)
            detailed = json.loads(out.getvalue())
            self.assertEqual(detailed["works"][0]["candidates"], [candidate])
            self.assertFalse(detailed["works"][0]["candidates"][0]["registration_ready"])

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline.main(["--report-only"]), 0)
            summary = json.loads(out.getvalue())
            self.assertNotIn("candidates", summary["works"][0])

    def test_explicit_probe_cross_checks_isbn_without_confirming_edition(self):
        from unittest.mock import Mock
        candidate = {
            "isbn13": "9782344067802", "work_status": "REVIEW_VOLUME_CANDIDATE",
            "language_status": "FRENCH_DECLARED", "registration_ready": False,
        }
        work = {
            "id": 49271, "source_mal_id": 116778, "title": "Chainsaw Man",
            "title_english": "Chainsaw Man", "title_japanese": None,
            "manga_type": "Manga", "mal_authors": ["Fujimoto, Tatsuki"],
        }
        result = {
            "status": "MATCHED", "reason": "SOURCE_CONFIRMED",
            "scrinis_id": "42", "work_evidence": "EXACT_TITLE_AUTHOR",
            "author_evidence": "MATCH", "french_print_isbns": ["9782344067802"],
            "book_references_truncated": True,
        }
        client = Mock()
        with patch.object(pipeline, "lookup_work", return_value=result) as lookup:
            diagnosis, cross = pipeline.probe_scrinis_work(work, [candidate], client)
        lookup.assert_called_once()
        self.assertEqual(diagnosis["source_public_id"], "42")
        self.assertEqual(diagnosis["supplier_coverage"], "INCOMPLETE_SUPPLIER_DETAIL")
        self.assertEqual(cross["correlation_counts"], {"ISBN_IN_BOTH_SOURCES": 1})
        self.assertEqual(cross["status"], "COMPARED")
        self.assertFalse(candidate["registration_ready"])
        self.assertNotIn("confirmed_edition", diagnosis)

    def test_explicit_probe_requires_verified_work(self):
        from unittest.mock import Mock
        with patch.object(pipeline, "lookup_work", return_value={
            "status": "AMBIGUOUS", "reason": "MULTIPLE_PLAUSIBLE_WORKS"}):
            diagnosis, cross = pipeline.probe_scrinis_work({
                "id": 2, "source_mal_id": 13, "title": "One Piece",
                "title_english": None, "title_japanese": None,
            }, [], Mock())
        self.assertEqual(diagnosis["status"], "AMBIGUOUS")
        self.assertEqual(cross["status"], "NO_VERIFIED_SCRINIS_WORK")

    def test_probe_mode_never_invokes_bnf_or_scrinis_writers(self):
        fake_context = MagicMock()
        fake_context.__enter__.return_value = MagicMock()
        with patch.object(pipeline, "connect_database", return_value=fake_context), \
             patch.object(pipeline, "select_ids", return_value=[2, 3]), \
             patch.object(pipeline, "load_work_evidence", side_effect=lambda conn, mid: (
                 {"id": mid, "source_mal_id": mid + 10, "title": "Berserk",
                  "title_english": None, "title_japanese": None},
                 [], None, [])), \
             patch.object(pipeline, "scrinis_selection_diagnostics", return_value={}), \
             patch.object(pipeline, "probe_scrinis_work", side_effect=[
                 ({"status": "PROVIDER_ERROR", "reason": "SEARCH_NETWORK_ERROR"},
                  {"status": "NO_VERIFIED_SCRINIS_WORK", "isbn_correlations": []}),
             ]) as probe, \
             patch.object(pipeline, "run_bnf") as run_bnf, \
             patch.object(pipeline, "run_scrinis") as run_scrinis:
            report = pipeline.run_pilot(manga_ids=[2, 3], bnf=False,
                                        scrinis=False, probe_scrinis=True)
        run_bnf.assert_not_called()
        run_scrinis.assert_not_called()
        probe.assert_called_once()
        self.assertEqual(report["works"][1]["scrinis_probe"]["status"],
                         "SKIPPED_PROVIDER_UNAVAILABLE")
        self.assertEqual(report["confirmed_editions_written"], 0)
        self.assertEqual(report["user_inventory_written"], 0)

    def test_probe_mode_requires_explicit_target_and_no_writers(self):
        with self.assertRaises(ValueError):
            pipeline.run_pilot(bnf=False, scrinis=False, probe_scrinis=True)
        with self.assertRaises(ValueError):
            pipeline.run_pilot(manga_ids=[2], probe_scrinis=True)
        with self.assertRaises(SystemExit):
            pipeline.main(["--probe-scrinis", "--report-only", "--manga-ids", "2"])

    def test_skip_bnf_reuses_saved_candidates(self):
        import contextlib
        import io
        with patch.object(pipeline, "run_pilot", return_value={
            "selected_ids": [2], "works": []}) as run:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    pipeline.main(["--manga-ids", "2", "--skip-bnf"]), 0)
            self.assertFalse(run.call_args.kwargs["bnf"])
            self.assertTrue(run.call_args.kwargs["scrinis"])

    def test_report_only_never_calls_suppliers_or_writes(self):
        fake_conn = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_conn
        with patch.object(pipeline, "connect_database", return_value=fake_context), \
             patch.object(pipeline, "select_ids", return_value=[2]), \
             patch.object(pipeline, "load_work_evidence", return_value=(
                 {"source_mal_id": 2, "title": "Berserk", "title_english": None,
                  "title_japanese": None}, [], None, [])), \
             patch.object(pipeline, "run_bnf") as bnf, \
             patch.object(pipeline, "run_scrinis") as scrinis, \
             patch.object(pipeline, "scrinis_selection_diagnostics", return_value={2: {"next_action": "REVIEW_AMBIGUOUS_SOURCE_MATCH"}}) as diagnostics:
            output = pipeline.run_pilot(manga_ids=[2], bnf=False, scrinis=False)
            bnf.assert_not_called()
            scrinis.assert_not_called()
            diagnostics.assert_called_once()
            self.assertEqual(output["scrinis_selection_diagnostics"][2]["next_action"], "REVIEW_AMBIGUOUS_SOURCE_MATCH")
            self.assertEqual(output["works"][0]["total_candidates"], 0)
            self.assertEqual(output["user_inventory_written"], 0)


if __name__ == "__main__":
    unittest.main()
