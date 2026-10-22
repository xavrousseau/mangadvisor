"""Bounded, read-only French bibliography regression tests."""
import unittest
from unittest.mock import patch

from apps.api.app.edition_discovery import search_bnf_title_pages
from pipelines.engine.scripts.benchmark_manga_sources_v2 import _scrinis_details


def fake_isbn(serial):
    prefix = "9780000" + str(serial).zfill(5)
    digits = [int(x) for x in prefix]
    check = (10 - sum(n * (1 if i % 2 == 0 else 3)
                      for i, n in enumerate(digits)) % 10) % 10
    return prefix + str(check)


class PaginationTests(unittest.TestCase):
    def test_bnf_multiple_pages_deduplicated_and_bounded(self):
        requests = []

        def get_page(query, *, start_record=1):
            requests.append((query, start_record))
            return {"bnf_reported_records": 48,
                    "items": [{"isbn13": fake_isbn(start_record)},
                              {"isbn13": fake_isbn(1)}]}

        report = search_bnf_title_pages("Berserk", fetch_page=get_page)
        self.assertEqual([start for _, start in requests], [1, 21, 41])
        self.assertEqual(report["bnf_pages_checked"], 3)
        self.assertEqual(report["count"], 3)
        self.assertFalse(report["page_limit_reached"])
        self.assertFalse(report["exhaustive"])

    def test_bnf_reports_partial_when_more_pages_exist(self):
        def get_page(query, *, start_record=1):
            return {"bnf_reported_records": 101,
                    "items": [{"isbn13": fake_isbn(start_record)}]}
        report = search_bnf_title_pages("Berserk", fetch_page=get_page)
        self.assertEqual(report["bnf_pages_checked"], 3)
        self.assertTrue(report["page_limit_reached"])

    def test_ten_pages_with_pause_and_blank_isbn_page(self):
        requested, pauses = [], []
        def get_page(query, *, start_record=1):
            requested.append(start_record)
            # Empty ISBN page is not end of SRU records.
            return {"bnf_reported_records": 145,
                    "items": [] if start_record == 41 else
                    [{"isbn13": fake_isbn(start_record)}]}
        result = search_bnf_title_pages(
            "Berserk", max_pages=10, fetch_page=get_page,
            sleep=pauses.append,
        )
        self.assertEqual(requested, [1, 21, 41, 61, 81, 101, 121, 141])
        self.assertEqual(len(pauses), 7)
        self.assertFalse(result["page_limit_reached"])
        self.assertEqual(result["count"], 7)

    def test_page_count_must_be_bounded(self):
        for count in (0, 11, -1, True, 3.5):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    search_bnf_title_pages("Berserk", max_pages=count)

    def test_scrinis_keeps_more_than_twenty_unique_isbns(self):
        records = [
            {"n": n, "isbn_13": fake_isbn(n),
             "lang": "fr", "medium": "print", "edition": "standard"}
            for n in range(1, 36)
        ]
        result = _scrinis_details({
            "public_n": 123,
            "titles": {"primary": "Berserk"},
            "volumes": records,
        })
        self.assertEqual(len(result["book_references"]), 35)
        self.assertEqual(result["book_references_valid_in_scan"], 35)
        self.assertFalse(result["book_references_truncated"])

    def test_scrinis_reports_hard_limit(self):
        records = [
            {"n": n, "isbn_13": fake_isbn(n),
             "lang": "fr", "medium": "print"} for n in range(1, 270)
        ]
        result = _scrinis_details({
            "public_n": 123, "titles": {"primary": "Berserk"}, "volumes": records,
        })
        self.assertEqual(result["volume_records_scanned"], 250)
        self.assertTrue(result["volume_scan_truncated"])
        self.assertTrue(result["book_references_truncated"])


if __name__ == "__main__":
    unittest.main()
