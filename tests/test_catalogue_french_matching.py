"""Offline French-market catalogue matching and inventory privacy tests."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from pipelines.engine.scripts import catalogue_french_matching as fr
from pipelines.engine.scripts import benchmark_manga_sources_v2 as v2


def sample(title="Dragon Ball", origin="pending", **kwargs):
    return {"title": title, "title_english": "", "title_japanese": "",
            "mal_id": None, "origin": origin, **kwargs}


def hit(title, identity, evidence="EXACT_TITLE", kind="manga"):
    return {"title": title, "id": str(identity), "evidence": evidence,
            "score": 1.0, "aliases": [], "format": kind, "mal_id": None}


class Cursor:
    def __init__(self):
        self.sql = ""
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        assert statement.lstrip().upper().startswith("SELECT"), "SQL write forbidden"
        self.sql = statement
        self.calls.append((statement, params))

    def fetchall(self):
        if "user_manga_inventory_pending" in self.sql:
            return [
                {"title": "Dragon Ball", "edition_declared": "Pastel",
                 "format_hint": "Manga"},
                {"title": "Dragon Ball", "edition_declared": "Deluxe",
                 "format_hint": "Manga"},
                {"title": "Tokyo Ghoul", "edition_declared": None,
                 "format_hint": "Manga"},
            ]
        if "user_manga_inventory_declaration" in self.sql:
            return [
                {"title": "Black Clover", "edition_declared": "Standard",
                 "format_hint": None}
            ]
        return []


class DB:
    def __init__(self):
        self.cur = Cursor()
    def cursor(self):
        return self.cur


def series_details(*, editions=None, refs=None):
    return {"status": "OK", "title": "Dragon Ball",
            "authors": ["Akira Toriyama"],
            "editions": editions if editions is not None else [
                {"edition": "Deluxe", "medium": "print", "lang": "fr", "volume_count": 14}],
            "book_references": refs if refs is not None else [
                {"isbn13": "9780306406157", "edition_label": "Deluxe",
                 "medium": "print", "lang": "fr", "volume_label": "1"}]}


class FrenchMatchingTests(unittest.TestCase):
    def test_inventory_market_target_and_multiple_editions(self):
        db = DB()
        enriched = fr.enrich_sample_targets(db, [
            sample(), sample("Black Clover", origin="owned"),
            sample("One Piece", origin="catalog")
        ])
        self.assertEqual(enriched[0]["market_target"], "FR_PRINT")
        self.assertEqual(enriched[0]["market_target_basis"],
                         "USER_COLLECTION_DEFAULT_UNVERIFIED")
        self.assertEqual(enriched[0]["edition_targets"], ["Pastel", "Deluxe"])
        self.assertEqual(enriched[0]["format_hints"], ["Manga"])
        self.assertEqual(enriched[1]["edition_targets"], ["Standard"])
        self.assertEqual(enriched[2]["market_target"], "INTERNATIONAL")
        self.assertEqual(enriched[2]["edition_targets"], [])
        self.assertTrue(all(x[0].strip().upper().startswith("SELECT") for x in db.cur.calls))
        self.assertTrue(all(x[1] and isinstance(x[1][0], list) for x in db.cur.calls))
        self.assertFalse(any("source_reference" in x[0] or "main_volumes" in x[0]
                             for x in db.cur.calls))

    def test_declaration_does_not_pretend_isbn_ownership(self):
        entry = sample(edition_targets=["Deluxe"], format_hints=["Manga"],
                       market_target="FR_PRINT")
        review = fr.edition_review(entry, series_details())
        self.assertEqual(review["status"], "FR_PRINT_EDITION_CANDIDATE_REVIEW")
        self.assertEqual(review["score"], 90)
        self.assertEqual(review["french_print_isbns"], ["9780306406157"])
        self.assertFalse(review["isbn_ownership_verified"])

    def test_pastel_and_deluxe_not_merged(self):
        entry = sample(edition_targets=["Pastel", "Deluxe"],
                       market_target="FR_PRINT")
        review = fr.edition_review(entry, series_details())
        self.assertEqual(review["status"], "FR_PRINT_PARTIAL_EDITION_MATCH_REVIEW")
        self.assertEqual(review["matched_declared_families"], ["deluxe"])
        self.assertEqual(review["unconfirmed_declared_families"], ["pastel"])
        self.assertLess(review["score"], 90)

    def test_wrong_edition_family_never_passes_as_matching(self):
        entry = sample(edition_targets=["Pastel"], market_target="FR_PRINT")
        review = fr.edition_review(entry, series_details())
        self.assertEqual(review["status"], "FR_PRINT_EDITION_CONFLICT_REVIEW")
        self.assertIn("DECLARED_EDITION_NOT_FOUND_AMONG_CANDIDATES", review["signals"])
        self.assertLessEqual(review["score"], 25)

    def test_japanese_or_ebook_does_not_prove_french_paper(self):
        entry = sample(edition_targets=["Deluxe"], market_target="FR_PRINT")
        detail = series_details(
            editions=[{"edition": "Deluxe", "medium": "ebook", "lang": "fr"},
                      {"edition": "Deluxe", "medium": "print", "lang": "ja"}],
            refs=[{"isbn13": "9780306406157", "lang": "ja", "medium": "print",
                   "edition_label": "Deluxe"}])
        review = fr.edition_review(entry, detail)
        self.assertEqual(review["score"], 0)
        self.assertEqual(review["status"], "NO_FR_PRINT_EVIDENCE")
        self.assertEqual(review["french_print_isbns"], [])

    def test_general_catalogue_has_no_french_requirement(self):
        entry = sample("One Piece", origin="catalog",
                       market_target="INTERNATIONAL")
        review = fr.edition_review(entry, series_details())
        self.assertIsNone(review["score"])
        self.assertEqual(review["status"], "NOT_APPLICABLE_INTERNATIONAL")

    def test_absent_declaration_does_not_infer_standard(self):
        entry = sample(market_target="FR_PRINT", edition_targets=[])
        review = fr.edition_review(entry, series_details())
        self.assertEqual(review["status"], "FR_PRINT_WORK_FOUND_EDITION_UNKNOWN")
        self.assertLess(review["score"], 90)
        self.assertIn("EXACT_EDITION_NOT_DECLARED", review["signals"])

    def test_english_title_alone_does_not_validate_french_edition(self):
        entry = sample("Tokyo Ghoul", market_target="FR_PRINT")
        report = fr.review_entry(entry, {"status": "EXACT_TITLE",
                                        "candidates": [hit("Tokyo Ghoul", 101)]})
        self.assertEqual(report["work"]["score"], 60)
        self.assertEqual(report["edition"]["score"], 0)
        self.assertFalse(report["automatic_link"])

    def test_work_kind_can_reject_manhwa_versus_declared_manga(self):
        entry = sample("Wind Breaker", market_target="FR_PRINT",
                       format_hints=["Manga"])
        review = fr.identity_review(entry, hit("Wind Breaker", 101, kind="Manhwa"),
                                    ambiguous=True)
        self.assertEqual(review["status"], "REVIEW_AMBIGUOUS")
        self.assertEqual(review["type_evidence"], "CONFLICT")
        self.assertLess(review["score"], 60)

    def test_ambiguous_two_candidate_evidence_preserved_without_link(self):
        entry = sample("Black Clover", market_target="FR_PRINT",
                       edition_targets=["Standard"])
        providers = {
            "status": "AMBIGUOUS",
            "candidates": [hit("Black Clover", 100), hit("Black Clover", 200)],
            "competing_details": [
                {"id": "100", "details": series_details()},
                {"id": "200", "details": series_details(editions=[
                    {"edition": "standard", "medium": "print", "lang": "fr"}],
                    refs=[])}
            ],
        }
        review = fr.review_entry(entry, providers)
        self.assertEqual(review["work"]["status"], "REVIEW_AMBIGUOUS")
        self.assertEqual(review["edition"]["status"], "NOT_EVALUATED_NO_DETAIL")
        self.assertEqual(len(review["competing_evidence"]), 2)
        self.assertNotEqual(review["competing_evidence"][0]["edition"]["status"],
                            review["competing_evidence"][1]["edition"]["status"])
        self.assertFalse(review["automatic_link"])

    def test_declared_editions_use_limited_detail_budget_first(self):
        """Dragon Ball at position 38 must not miss out on its only detail slot."""
        class Client:
            counts = {"scrinis": 0, "mangaupdates": 0}
            def __init__(self):
                self.calls = []
            def call(self, provider, kind, **kwargs):
                self.calls.append((kind, kwargs))
                if kind == "detail":
                    return {"status": "OK", "data": series_details()}
                return {"status": "OK", "schema": {}, "candidates": [{
                    "id": "38", "title": kwargs["query"], "aliases": [],
                    "format": "manga", "mal_id": None,
                    "has_isbn_in_search": False, "has_genres_in_search": False
                }]}
        rows = [sample("Tokyo Ghoul"), sample("Yakuza Zen"), sample(
            "Dragon Ball", origin="owned", market_target="FR_PRINT",
            edition_targets=["Pastel", "Deluxe"])]
        rows[0]["market_target"] = "FR_PRINT"
        rows[1]["market_target"] = "FR_PRINT"
        client = Client()
        report = v2.evaluate(rows, client=client, providers=("scrinis",),
                             detail_budget=1, alternate_budget=0)
        # Still ordered as selected; the *first* detail call went to Dragon Ball.
        self.assertEqual([x["title"] for x in report["entries"]],
                         ["Tokyo Ghoul", "Yakuza Zen", "Dragon Ball"])
        self.assertEqual([call["query"] for kind, call in client.calls
                          if kind == "search"][:1], ["Dragon Ball"])
        self.assertEqual(len([a for a in client.calls if a[0] == "detail"]), 1)
        dragon = report["entries"][2]["sources"]["scrinis"]
        self.assertEqual(dragon["detail_status"], "OK")
        self.assertEqual(dragon["detail_priority_reason"],
                         "DECLARED_PHYSICAL_EDITION_FIRST")
        self.assertEqual(dragon["matching_review"]["edition"]["status"],
                         "FR_PRINT_PARTIAL_EDITION_MATCH_REVIEW")
        self.assertEqual(report["declared_edition_entries"], 1)

    def test_scrinis_volume_and_isbn_caps_are_explicit(self):
        # Even valid references are intentionally bounded in the report.
        detail = v2.parse_details("scrinis", {"public_n": 100, "titles": {
            "primary": "Long Series"}, "volumes": [
                {"n": i, "isbn_13": "9780306406157", "medium": "print",
                 "lang": "fr", "edition": "standard"}
                for i in range(101)]})
        self.assertEqual(detail["volume_items_seen"], 101)
        self.assertEqual(detail["volume_records_scanned"], 101)
        self.assertEqual(detail["book_references_valid_in_scan"], 101)
        self.assertEqual(len(detail["book_references"]), 101)
        self.assertFalse(detail["book_references_truncated"])
        self.assertFalse(detail["volume_scan_truncated"])

    def test_network_requests_remain_title_only(self):
        class Client:
            counts = {"scrinis": 0}
            def __init__(self):
                self.calls = []
            def call(self, provider, kind, **kw):
                self.calls.append((provider, kind, kw))
                return {"status": "OK", "schema": {}, "candidates": []}
        entry = sample(market_target="FR_PRINT",
                       edition_targets=["Deluxe: user-only"],
                       format_hints=["Manga, from private inventory"])
        c = Client()
        output = v2.evaluate([entry], client=c, providers=("scrinis",),
                             alternate_budget=0, detail_budget=0)
        self.assertEqual(c.calls, [("scrinis", "search", {"query": "Dragon Ball"})])
        self.assertNotIn("Deluxe: user-only", str(c.calls))
        self.assertEqual(output["entries"][0]["sources"]["scrinis"]
                         ["matching_review"]["market_target"], "FR_PRINT")

    def test_new_csv_columns_and_private_local_evidence(self):
        class Client:
            counts = {"scrinis": 0, "mangaupdates": 0}
            def call(self, provider, kind, **kw):
                return {"status": "OK", "schema": {}, "candidates": []}
        entry = sample(market_target="FR_PRINT", edition_targets=["Pastel"],
                       market_target_basis="USER_COLLECTION_DEFAULT_UNVERIFIED")
        report = v2.evaluate([entry], client=Client(), providers=("scrinis","mangaupdates"),
                             alternate_budget=0, detail_budget=0)
        report["entries"][0]["sources"]["scrinis"]["competing_details"] = [{
            "id": "100", "status": "OK",
            "details": {"book_references_truncated": True}}]
        with tempfile.TemporaryDirectory() as directory:
            js, csv_path = v2.save_report(report, Path(directory))
            with csv_path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["cible_langue"], "fr")
            self.assertEqual(rows[0]["cible_support"], "print")
            self.assertEqual(rows[0]["editions_declarees"], "Pastel")
            self.assertEqual(rows[0]["isbn_references_incompletes"], "OUI")
            self.assertEqual(rows[1]["isbn_references_incompletes"], "NON_EVALUE")
            self.assertEqual(rows[0]["score_edition_fr_indicatif"], "0")
            self.assertIn("matching_review", js.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
