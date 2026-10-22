"""Scrinis multi-candidate matching safety checks, no HTTP or database."""
import unittest
from unittest.mock import Mock, patch

from pipelines.engine.scripts import enrich_catalogue_scrinis_fr as en


def candidate(number):
    return {"id": str(number), "title": "Chainsaw Man", "aliases": [],
            "format": "Manga", "mal_id": None, "evidence": "EXACT_TITLE"}


def detail(number, authors, isbn="9782344067802"):
    return {"status": "OK", "data": {
        "status": "OK", "id": str(number),
        "title": "Chainsaw Man", "work_type": "Manga",
        "authors": authors,
        "book_references": [{"isbn13": isbn, "lang": "fr", "medium": "print"}],
    }}


class ScrinisCompetitionTests(unittest.TestCase):
    def setUp(self):
        self.work = {"id": 49271, "mal_id": 116778, "title": "Chainsaw Man",
                     "title_english": "Chainsaw Man", "title_japanese": None,
                     "manga_type": "Manga", "mal_authors": ["Tatsuki Fujimoto"]}
        self.choices = [candidate(10), candidate(11)]
        self.ranked = {"status": "AMBIGUOUS", "ambiguous_count": 1,
                       "review_candidates": [{"id": "10"}, {"id": "11"}],
                       "candidates": self.choices}

    def test_unique_author_match_allows_candidate_with_print_isbn(self):
        cli = Mock()
        cli.call.side_effect = [
            {"status": "OK", "candidates": self.choices},
            detail(10, ["Tatsuki Fujimoto"]),
            detail(11, ["Other Person"]),
        ]
        with patch.object(en.scr, "rank", return_value=self.ranked):
            result = en.lookup_work(self.work, cli)
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(result["scrinis_id"], "10")
        self.assertEqual(cli.call.call_count, 3)

    def test_two_matching_authors_remain_ambiguous(self):
        cli = Mock()
        cli.call.side_effect = [
            {"status": "OK", "candidates": self.choices},
            detail(10, ["Tatsuki Fujimoto"]),
            detail(11, ["Tatsuki Fujimoto"]),
        ]
        with patch.object(en.scr, "rank", return_value=self.ranked):
            result = en.lookup_work(self.work, cli)
        self.assertEqual(result["status"], "AMBIGUOUS")

    def test_unavailable_competing_detail_is_not_a_false_match(self):
        cli = Mock()
        cli.call.side_effect = [
            {"status": "OK", "candidates": self.choices},
            detail(10, ["Tatsuki Fujimoto"]),
            {"status": "RESPONSE_TOO_LARGE"},
        ]
        with patch.object(en.scr, "rank", return_value=self.ranked):
            result = en.lookup_work(self.work, cli)
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertEqual(result["reason"], "COMPETING_DETAIL_UNAVAILABLE")

    def test_more_than_three_rivals_stays_ambiguous_without_details(self):
        cli = Mock()
        cli.call.return_value = {"status": "OK", "candidates": self.choices}
        many = {**self.ranked, "ambiguous_count": 3}
        with patch.object(en.scr, "rank", return_value=many):
            result = en.lookup_work(self.work, cli)
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertEqual(cli.call.call_count, 1)

    def test_explicit_mal_conflict_never_becomes_match(self):
        cli = Mock()
        rivals = [dict(candidate(10), mal_id=998), candidate(11)]
        cli.call.side_effect = [
            {"status": "OK", "candidates": rivals},
            detail(11, ["Tatsuki Fujimoto"]),
        ]
        ranked = {**self.ranked, "candidates": rivals}
        with patch.object(en.scr, "rank", return_value=ranked):
            result = en.lookup_work(self.work, cli)
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(result["scrinis_id"], "11")


if __name__ == "__main__":
    unittest.main()
