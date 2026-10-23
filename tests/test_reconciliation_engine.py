"""Evidence-based bibliographic reconciliation; no database or network required."""
from __future__ import annotations

import unittest

from apps.api.app.reconciliation_engine import (
    assess_work_candidate, alias_records, discovery_terms,
    summarize_book_evidence, title_key,
)
from apps.api.app.inventory_resolution import triage_pending_rows


def pending(title: str, volumes: int = 1) -> dict:
    return {
        "source_key": "fixture:public-title", "entry_title": title,
        "work_declared": None, "edition_declared": None,
        "review_status": "REVIEW_MISSING", "main_volumes": volumes,
        "duplicate_copies": 0, "other_editions_unknown": 0,
        "candidate_ids": [],
    }


def work(id_: int, title: str, *, alias: str | None = None,
         alias_source: str = "WIKIDATA_P4087",
         kind: str = "Manga", volumes: int | None = None) -> dict:
    return {
        "id": id_, "title": title, "title_english": None,
        "title_japanese": None, "source_mal_id": id_,
        "manga_type": kind, "volumes": volumes,
        "exact_aliases": [alias.casefold()] if alias else [],
        "exact_alias_evidence": ([{"alias": alias,
                                  "source_name": alias_source,
                                  "source_id": "Q"+str(id_)}] if alias else []),
    }


class ReconciliationEngineTests(unittest.TestCase):
    def test_alias_with_one_volume_cannot_be_a_safe_radiant_match(self):
        bad = work(999, "Unrelated one-volume work",
                   alias="Radiant", volumes=1)
        result = triage_pending_rows([pending("Radiant", 18)], [bad], [], set())
        row = result["items"][0]
        self.assertEqual(row["review_category"], "SUSPICIOUS_ALIAS_REVIEW")
        evidence = row["candidates"][0]["work_reconciliation"]
        self.assertEqual(evidence["assessment"], "CONFLICT_REVIEW")
        self.assertIn("JAPANESE_WORK_COUNT_VS_FRENCH_HOLDINGS_DIFFER",
                      evidence["warnings"])
        self.assertFalse(evidence["work_identity_confirmed"])
        self.assertFalse(evidence["ownership_confirmed"])
        self.assertEqual(row["candidates"][0]["bibliography"]["bnf_candidate_isbn_count"], 0)

    def test_canonical_title_precedes_and_exposes_foreign_alias(self):
        manga = work(1, "Fairy Tail", volumes=63)
        novel = work(2, "Fairy Tail", kind="Light Novel", volumes=3)
        wrong = work(3, "Unrelated work", alias="Fairy Tail", volumes=1)
        out = triage_pending_rows([pending("Fairy Tail", 60)],
                                  [wrong, novel, manga], [], set())
        row = out["items"][0]
        self.assertEqual(row["review_category"], "AMBIGUOUS_EXACT")
        self.assertEqual(row["candidates"][0]["manga_id"], 1)
        wrong_record = next(x for x in row["candidates"] if x["manga_id"] == 3)
        self.assertIn("ALIAS_CONFLICTS_WITH_OTHER_CANONICAL_TITLE",
                      wrong_record["work_reconciliation"]["warnings"])
        self.assertIn("DERIVATIVE_OR_TEXT_WORK_TYPE_REVIEW",
                      next(x for x in row["candidates"] if x["manga_id"] == 2)
                      ["work_reconciliation"]["warnings"])

    def test_source_attribution_is_preserved_and_not_equated_with_ownership(self):
        item = work(21, "Doubutsu Ningen", alias="Animal Human",
                    alias_source="SCRINIS_FR_PRINT")
        hints = alias_records(item, "Animal Human")
        self.assertEqual(hints[0]["source_name"], "SCRINIS_FR_PRINT")
        evidence = assess_work_candidate(pending("Animal Human"), item)
        self.assertTrue(any(x["source"] == "SCRINIS_FR_PRINT"
                            for x in evidence["evidence"]))
        self.assertFalse(evidence["work_identity_confirmed"])
        self.assertFalse(evidence["edition_identity_confirmed"])
        self.assertFalse(evidence["isbn_assigned_to_ownership"])

    def test_unknown_alias_source_is_flagged_without_throwing_away_candidate(self):
        item = work(20, "Original", alias="French Title",
                    alias_source="UNKNOWN_UNCHECKED_IMPORT")
        row = triage_pending_rows([pending("French Title")], [item], [], set())["items"][0]
        self.assertEqual(row["review_category"], "ALIAS_SOURCE_REVIEW")
        self.assertEqual(row["candidates"][0]["work_reconciliation"]["assessment"],
                         "EVIDENCE_INCOMPLETE_REVIEW")
        self.assertIn("ALIAS_UNVERIFIED_OR_UNTRACED",
                      row["candidates"][0]["work_reconciliation"]["warnings"])

    def test_wikidata_fact_fr_title_is_a_clue_not_an_edition_proof(self):
        item = work(15, "Shingeki no Kyojin")
        item["wikidata_label_fr"] = "L'Attaque des Titans"
        row = triage_pending_rows(
            [pending("L'Attaque des Titans", 30)], [item], [], set()
        )["items"][0]
        self.assertEqual(row["review_category"], "SINGLE_EXACT_SUGGESTION")
        e = row["candidates"][0]["work_reconciliation"]
        self.assertTrue(any(s["kind"] == "EXTERNAL_ID_LINK" for s in e["evidence"]))
        self.assertFalse(e["ownership_confirmed"])

    def test_bnf_staging_and_registered_books_are_independent(self):
        result = summarize_book_evidence(
            10,
            [{"manga_id": 10, "isbn13": "9781234567897",
              "title_fr": "Title vol 1", "edition_kind_suggested": "UNKNOWN",
              "source_url": "https://catalogue.bnf.fr/ark:/12148/cb12345678x",
              "work_isbn_count": 11}],
            [{"manga_id": 10, "isbn13": "9782871294146",
              "work_isbn_count": 2}],
        )
        self.assertEqual(result["bnf_candidate_isbn_count"], 11)
        self.assertEqual(result["registered_french_isbn_count"], 2)
        self.assertTrue(result["candidate_source_truncated"])
        self.assertEqual(result["bnf_candidate_isbns_sample"][0]["status"],
                         "BNF_CANDIDATE_UNVERIFIED")
        self.assertEqual(result["registered_isbns_sample"][0]["status"],
                         "CATALOGUE_BOOK_NOT_OWNERSHIP")
        self.assertFalse(result["ownership_inferred"])

    def test_search_terms_are_hints_only_and_never_strip_edition_identity(self):
        self.assertEqual(title_key("Tôgen-Anki !"), "togen anki")
        self.assertIn("eri", discovery_terms("Adieu Eri"))
        self.assertIn("kuroko", discovery_terms("Kuroko's Basket"))
        self.assertEqual(discovery_terms("the les volumes"), [])

    def test_no_result_stays_unresolved_even_with_year_or_edition_name(self):
        candidate = pending("Dragon Ball - Forever")
        out = triage_pending_rows([candidate], [], [], set())
        self.assertEqual(out["review_categories"], {"SEARCH_REQUIRED": 1})
        self.assertFalse(out["automatic_association"])
        self.assertEqual(out["confirmed_editions_written"], 0)


if __name__ == "__main__":
    unittest.main()
