"""Source comparison tests: fixtures and fake connections only, never external HTTP."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pipelines.engine.scripts import benchmark_manga_sources as mod


WORK = {
    "title": "L'Attaque des Titans",
    "title_english": "Attack on Titan",
    "title_japanese": "進撃の巨人",
    "mal_id": 23390,
    "origin": "pending",
}


class FakeCursor:
    def __init__(self):
        self.sql = ""
        self.calls = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params=None):
        self.sql = sql
        self.calls.append(sql)
        assert sql.strip().upper().startswith("SELECT"), "Write statement prohibited"
    def fetchall(self):
        if "user_manga_inventory_pending" in self.sql:
            return [{"title": "L'Attaque des Titans", "title_english": None,
                     "title_japanese": None, "mal_id": None}]
        if "user_manga_inventory_declaration" in self.sql:
            return [{"title": "Dragon Ball", "title_english": "Dragon Ball",
                     "title_japanese": "ドラゴンボール", "mal_id": 42}]
        return [{"title": "Dragon Ball", "title_english": "Dragon Ball",
                 "title_japanese": "ドラゴンボール", "mal_id": 42},
                {"title": "One Piece", "title_english": "One Piece",
                 "title_japanese": "ワンピース", "mal_id": 13}]


class FakeConnection:
    def __init__(self):
        self.cur = FakeCursor()
    def cursor(self):
        return self.cur


class SearchTests(unittest.TestCase):
    def test_50_limit_and_priority_deduped(self):
        db = FakeConnection()
        samples = mod.select_samples(db, 50)
        self.assertEqual([x["origin"] for x in samples], ["pending", "owned", "catalog"])
        self.assertEqual([x["title"] for x in samples],
                         ["L'Attaque des Titans", "Dragon Ball", "One Piece"])
        self.assertEqual(len(db.cur.calls), 3)

    def test_uses_multilingual_titles_and_never_confirms_physical_edition(self):
        obj = {"title": "Attack on Titan", "aliases": [], "id": 13,
               "mal_id": None, "has_isbn": False, "has_genres": True}
        out = mod.classify(WORK, [obj])
        self.assertEqual(out["status"], "EXACT_TITLE")
        self.assertNotIn("manga_id", out)
        self.assertNotIn("edition", out)
        obj["mal_id"] = WORK["mal_id"]
        self.assertEqual(mod.classify(WORK, [obj])["status"], "SAME_MAL_ID")

    def test_ambiguous_results_not_automatically_resolved(self):
        match = lambda i: {"title": "Dragon Ball", "aliases": [], "id": i,
                           "mal_id": None, "has_isbn": True, "has_genres": True}
        out = mod.classify({"title": "Dragon Ball"}, [match(1), match(2)])
        self.assertEqual(out["status"], "AMBIGUOUS")

    def test_payload_wrappers_and_unrecognized_schema(self):
        self.assertEqual(mod.candidates_from_payload({"results": [{
            "record": {"title": "Berserk", "series_id": 55, "genres": ["Action"]}
        }]})[0]["id"], 55)
        self.assertEqual(mod.candidates_from_payload({"data": {
            "series": [{"title": "One Piece", "id": 8}]
        }})[0]["title"], "One Piece")
        self.assertIsNone(mod.candidates_from_payload({"unrecognized": 5}))

    def test_http_calls_bound_size_and_do_not_post_private_fields(self):
        sess = Mock()
        sess.get.return_value.status_code = 200
        sess.get.return_value.content = json.dumps({"items": [
            {"title": "Attack on Titan", "id": 3}
        ]}).encode()
        response = mod.request_source("scrinis", WORK["title"], sess)
        self.assertEqual(response["status"], "OK")
        self.assertEqual(response["candidates"][0]["id"], 3)
        kwargs = sess.get.call_args.kwargs
        self.assertEqual(kwargs["params"]["q"], WORK["title"])
        self.assertNotIn("status", kwargs["params"])
        self.assertNotIn("user_id", kwargs["params"])
        sess.post.return_value.status_code = 200
        sess.post.return_value.content = b'{"results":[]}'
        response = mod.request_source("mangaupdates", WORK["title"], sess)
        self.assertEqual(response["status"], "OK")
        self.assertEqual(sess.post.call_args.kwargs["json"],
                         {"search": WORK["title"], "perpage": 5})

    def test_quota_error_stops_requests_for_one_provider_only(self):
        sess = Mock()
        sess.get.return_value.status_code = 429
        sess.post.return_value.status_code = 200
        sess.post.return_value.content = b'{"results":[]}'
        samples = [WORK, {**WORK, "title": "Another Manga"}]
        with patch.object(mod.time, "monotonic", side_effect=range(100, 120)):
            result = mod.compare_works(samples, session=sess, sleep=lambda _: None)
        self.assertEqual(sess.get.call_count, 1)
        self.assertEqual(sess.post.call_count, 2)
        self.assertEqual(result["providers"]["scrinis"]["UNAVAILABLE"], 1)
        self.assertEqual(result["providers"]["scrinis"]["SKIPPED_PROVIDER_UNAVAILABLE"], 1)

    def test_reports_only_local_disk_and_no_database_writes(self):
        report = {"entries": [{"title": "Naruto", "origin": "catalog", "sources": {
            "scrinis": {"status": "NO_MATCH"}, "mangaupdates": {"status": "NO_MATCH"}
        }}], "providers": {}}
        with tempfile.TemporaryDirectory() as tmp:
            js, csv = mod.save_report(report, Path(tmp))
            self.assertEqual(json.loads(js.read_text())["entries"][0]["title"], "Naruto")
            self.assertIn("scrinis_etat", csv.read_text(encoding="utf-8-sig"))

    def test_dry_run_sends_no_external_requests(self):
        conn = FakeConnection()
        class Context:
            def __enter__(self):
                return conn
            def __exit__(self, *args):
                return False
        with patch.object(mod, "get_postgres_connection", return_value=Context()), patch.object(
            mod.requests, "Session"
        ) as client:
            self.assertEqual(mod.main(["--dry-run", "--limit", "3"]), 0)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
