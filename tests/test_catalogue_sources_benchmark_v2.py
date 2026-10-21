"""Offline V2 tests: captured response shapes, ambiguous editions, quota and privacy."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pipelines.engine.scripts import benchmark_manga_sources_v2 as v2


def work(title="Demon Slayer", **kwargs):
    return {"title": title, "title_english": "", "title_japanese": "",
            "mal_id": None, "origin": "pending", **kwargs}


def hit(title, identity, **kwargs):
    return {"title": title, "id": str(identity),
            "aliases": [], "format": "", "mal_id": None,
            "has_isbn_in_search": False,
            "has_genres_in_search": True, **kwargs}


class FakeSession:
    def __init__(self):
        self.get = Mock()
        self.post = Mock()


class BenchmarkV2Tests(unittest.TestCase):
    def test_scrinis_nested_ids_and_schema_diagnostics(self):
        payload = {"data": {"results": [
            {"type": "series", "series": {"id": 3014, "title": "One Piece",
                                         "title_fr": "One Piece",
                                         "genres": [{"name": "Action"}]}},
            {"type": "volume", "series": {"series_id": 205, "title": "Dragon Ball Forever"},
             "id": 9876},
        ]}}
        results, diag = v2.parse_hits(payload)
        self.assertEqual([x["id"] for x in results], ["3014", "205"])
        self.assertEqual(diag["with_id"], 2)
        self.assertEqual(diag["hit_key"], "results")

    def test_mangaupdates_associated_titles(self):
        payload = {"results": [{"record": {
            "series_id": 123, "title": "Sayonara Eri",
            "associated": [{"title": "Adieu Eri"}],
            "type": "Manga"}}]}
        items, _ = v2.parse_hits(payload)
        self.assertEqual(items[0]["id"], "123")
        self.assertIn("Adieu Eri", items[0]["aliases"])
        self.assertEqual(v2.rank(work("Adieu Eri"), items)["status"], "EXACT_TITLE")

    def test_keep_competing_exact_candidates(self):
        results = v2.rank(work("Demon Slayer"), [
            hit("Demon Slayer", 101),
            hit("Demon Slayer", 102),
            hit("Demon Slayer dj - Other", 103),
        ])
        self.assertEqual(results["status"], "AMBIGUOUS")
        self.assertGreaterEqual(results["candidate_count"], 3)
        self.assertEqual(results["ambiguous_count"], 1)

    def test_misleading_spinoff_is_only_a_suggestion(self):
        candidate = v2.rank(work("Dragon Ball - Forever"), [
            hit("DRAGON BALL SUPER", 10)])
        self.assertEqual(candidate["status"], "SUGGESTION_ONLY")
        self.assertIsNone(v2.alternative_query(work("Dragon Ball - Forever")))

    def test_volume_isbns_are_checksummed_and_not_claimed_owned(self):
        detail = v2.parse_details("scrinis", {"data": {
            "id": 10, "title": "Dragon Ball",
            "genres": [{"name": "Aventure"}],
            "themes": [{"name": "Arts martiaux"}],
            "volumes": [
                {"number": 1, "isbn": "9780306406157"},
                {"number": 2, "isbn": "9780306406158"}],
            "description": "DO NOT COPY A COPYRIGHT BLURB"
        }})
        self.assertEqual(detail["book_references"], [{
            "isbn13": "9780306406157", "volume_label": "1", "edition_label": ""}])
        self.assertNotIn("description", detail)
        self.assertTrue(detail["has_summary"])
        self.assertEqual(detail["genres"], ["Aventure"])

    def test_real_public_url_patterns_and_reject_untrusted_ids(self):
        sess = FakeSession()
        sess.get.return_value.status_code = 200
        sess.get.return_value.content = b'{"data":{"id":3014,"title":"One Piece"}}'
        response = v2.request_public("scrinis", "detail", sess, identifier="3014")
        self.assertEqual(response["status"], "OK")
        self.assertEqual(sess.get.call_args.args[0], "https://scrin.is/api/v1/series/3014")
        with self.assertRaises(ValueError):
            v2.request_public("scrinis", "detail", sess, identifier="../private")
        sess.post.return_value.status_code = 200
        sess.post.return_value.content = b'{"results":[]}'
        v2.request_public("mangaupdates", "search", sess, query="One Piece")
        self.assertEqual(sess.post.call_args.kwargs["json"],
                         {"search": "One Piece", "perpage": 8})

    def test_rate_delay_applies_to_details_too_and_cache_reuses_responses(self):
        sess = FakeSession()
        sess.get.return_value.status_code = 200
        sess.get.return_value.content = b'{"results":[{"id":3014,"title":"One Piece"}]}'
        sleep = Mock()
        ticks = iter([1., 2., 3., 4., 5., 6.])
        with tempfile.TemporaryDirectory() as d:
            client = v2.RateLimitedClient(session=sess, cache_dir=Path(d),
                                           sleep=sleep, clock=lambda: next(ticks))
            a = client.call("scrinis", "search", query="One Piece")
            b = client.call("scrinis", "search", query="One Piece")
            self.assertEqual(a, b)
            self.assertEqual(sess.get.call_count, 1)
            sess.get.return_value.content = b'{"id":3014,"title":"One Piece"}'
            client.call("scrinis", "detail", identifier="3014")
            self.assertEqual(sess.get.call_count, 2)
            self.assertGreaterEqual(sleep.call_args.args[0], 0)
            self.assertLessEqual(client.counts["scrinis"], 2)

    def test_quota_one_provider_stops_without_modifying_other(self):
        class FakeClient:
            def __init__(self):
                self.counts = {"scrinis": 1, "mangaupdates": 1}
                self.calls = []
            def call(self, provider, kind, **kwargs):
                self.calls.append((provider, kind))
                if provider == "scrinis":
                    return {"status": "UNAVAILABLE", "http_status": 429}
                return {"status": "OK", "candidates": [], "schema": {}}
        c = FakeClient()
        report = v2.evaluate([work("Naruto")], client=c, detail_budget=0,
                             alternate_budget=0)
        self.assertEqual(report["providers"]["scrinis"]["evaluated"], 0)
        self.assertIsNone(report["providers"]["scrinis"]["rate_percent"])
        self.assertEqual(report["providers"]["mangaupdates"]["evaluated"], 1)
        self.assertEqual(report["entries"][0]["sources"]["scrinis"]["status"], "UNAVAILABLE")

    def test_report_contains_other_candidates_and_details(self):
        record = {"format_version": 2, "entries": [{
            "title": "Bleach", "origin": "pending", "sources": {
                "scrinis": {"status": "AMBIGUOUS", "selected_id": "10",
                            "candidates": [hit("Bleach", 10), hit("Bleach", 12)],
                            "candidate_count": 2, "ambiguous_count": 1,
                            "detail_status": "OK",
                            "details": {"title": "Bleach", "aliases": ["ブリーチ"],
                                        "genres": ["Action"], "themes": ["Shonen"],
                                        "book_references": [], "volume_items_seen": 0}},
                "mangaupdates": {"status": "NO_MATCH", "candidates": []}}}], "providers": {}}
        with tempfile.TemporaryDirectory() as tmp:
            js, cs = v2.save_report(record, Path(tmp))
            self.assertEqual(json.loads(js.read_text())["format_version"], 2)
            self.assertIn("concurrents_ambigus", cs.read_text(encoding="utf-8-sig"))
            self.assertIn("ブリーチ", cs.read_text(encoding="utf-8-sig"))

    def test_only_samples_from_database_no_postgres_mutations(self):
        from tests.test_catalogue_sources_benchmark import FakeConnection
        db = FakeConnection()
        items = v2.v1.select_samples(db, 50)
        self.assertTrue(all(sql.strip().upper().startswith("SELECT") for sql in db.cur.calls))
        self.assertTrue(items)


if __name__ == "__main__":
    unittest.main()
