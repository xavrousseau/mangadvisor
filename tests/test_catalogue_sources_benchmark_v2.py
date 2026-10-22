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

    def test_scrinis_hub_id_and_localized_names(self):
        payload = {"items": [{"hub_id": 3014,
                               "ids": {"mal": 13},
                               "title": "L'Attaque des Titans",
                               "title_localized": {"en": "Attack on Titan"},
                               "format": "manga"}]}
        items, diagnostics = v2.parse_hits(payload)
        self.assertEqual(items[0]["id"], "3014")
        self.assertIn("Attack on Titan", items[0]["aliases"])
        self.assertEqual(diagnostics["identity_field_types"]["hub_id"], "int")
        self.assertEqual(diagnostics["identity_field_types"]["ids"], "dict")
        self.assertNotIn("hub_id", v2.parse_hits({"items": []})[1].get("identity_field_types", {}))

    def test_homonymous_wind_breaker_is_not_confirmed(self):
        sample = work("Wind Breaker")
        result = v2.rank(sample, [
            hit("Wind Breaker", 101, format="Manhwa"),
            hit("Wind Breaker (NII Satoru)", 102, format="Manga"),
        ])
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIn("SAME_TITLE_DIFFERENT_QUALIFIED_WORK",
                      result["disambiguation_reasons"])
        self.assertEqual(result["ambiguous_count"], 1)
        self.assertEqual(len(result["candidates"]), 2)

    def test_doujinshi_does_not_beat_real_manga_on_fuzzy_name(self):
        result = v2.rank(work("Demon Slayer"), [
            hit("Demon Slayer dj - Fanbook", 51, format="Doujinshi"),
            hit("Kimetsu no Yaiba", 52, format="Manga"),
        ])
        self.assertEqual(result["status"], "SUGGESTION_ONLY")
        self.assertEqual(result["candidates"][0]["title"], "Kimetsu no Yaiba")

    def test_inspect_two_competing_candidates_without_selecting_either(self):
        class Client:
            counts = {"scrinis": 2, "mangaupdates": 0}
            def __init__(self):
                self.calls = []
            def call(self, provider, kind, **kwargs):
                self.calls.append((kind, kwargs))
                if kind == "detail":
                    return {"status": "OK", "data": {
                        "title": "Wind Breaker",
                        "authors": ["Nii Satoru"] if kwargs["identifier"] == "102"
                                   else ["Other Artist"],
                        "publishers": ["Different Publisher"], "book_references": []}}
                return {"status": "OK", "schema": {}, "candidates": [
                    hit("Wind Breaker", 101, format="Manhwa"),
                    hit("Wind Breaker (NII Satoru)", 102, format="Manga"),
                ]}
        client = Client()
        report = v2.evaluate([work("Wind Breaker")], client=client,
                             providers=("scrinis",), detail_budget=2, alternate_budget=0)
        src = report["entries"][0]["sources"]["scrinis"]
        self.assertEqual(src["status"], "AMBIGUOUS")
        self.assertEqual(src["detail_status"], "COMPARED_AMBIGUOUS")
        self.assertEqual([x[1].get("identifier") for x in client.calls],
                         [None, "101", "102"])
        self.assertEqual(len(src["competing_details"]), 2)
        self.assertNotIn("details", src)
        self.assertEqual(report["providers"]["scrinis"]["ambiguous_candidate_details_ok"], 2)

    def test_ambiguous_inspection_never_exceeds_remaining_budget(self):
        class Client:
            counts = {"scrinis": 0, "mangaupdates": 0}
            def __init__(self):
                self.calls = []
            def call(self, provider, kind, **kwargs):
                self.calls.append(kind)
                if kind == "detail":
                    raise AssertionError("Cannot inspect only half a competing pair")
                return {"status": "OK", "schema": {}, "candidates": [
                    hit("Wind Breaker", 101), hit("Wind Breaker", 102)]}
        c = Client()
        report = v2.evaluate([work("Wind Breaker")], client=c,
                             providers=("scrinis",), detail_budget=1, alternate_budget=0)
        self.assertEqual(c.calls, ["search"])
        src = report["entries"][0]["sources"]["scrinis"]
        self.assertEqual(src["detail_status"], "SKIPPED_AMBIGUOUS")
        self.assertEqual(src["review_not_run_reason"], "INSUFFICIENT_DETAIL_BUDGET")

    def test_foreign_language_edition_does_not_block_original_work(self):
        result = v2.rank(work("Tokyo Ghoul"), [
            hit("Tokyo Ghoul", 101, format="manga"),
            hit("Tokyo Ghoul (en allemand)", 102, format="manga"),
            hit("Tokyo Ghoul (en portugais)", 103, format="manga"),
            hit("Tokyo Ghoul:re", 104, format="manga")
        ])
        self.assertEqual(result["status"], "EXACT_TITLE")
        self.assertEqual(result["ambiguous_count"], 0)
        self.assertEqual(result["selected_id"], "101")
        self.assertEqual(len(result["candidates"]), 4)

    def test_distinct_same_title_scrinis_hub_records_still_ambiguous(self):
        result = v2.rank(work("Black Clover"), [
            hit("Black Clover", 33269, format="manga"),
            hit("Black Clover", 163154, format="manga")
        ])
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertEqual(result["ambiguous_count"], 1)
        self.assertEqual([x["id"] for x in result["review_candidates"]],
                         ["33269", "163154"])

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
        self.assertEqual([v["isbn13"] for v in detail["book_references"]],
                         ["9780306406157"])
        self.assertEqual(detail["book_references"][0]["volume_label"], "1")
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

    def test_streamed_scrinis_metadata_accepts_large_but_bounded_detail(self):
        import requests
        sess = FakeSession()
        response = requests.Response()
        response.status_code = 200
        # 2.6 MB exceeds the old 2.5 MB cap, yet is safely below the new cap.
        response._content = json.dumps({
            "public_n": 3014, "titles": {"primary": "One Piece"},
            "summary": "x" * 2_600_000,
        }).encode()
        response._content_consumed = True
        sess.get.return_value = response
        result = v2.request_public("scrinis", "detail", sess, identifier="3014")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["data"]["id"], "3014")
        self.assertNotIn("summary", result["data"])
        self.assertEqual(sess.get.call_args.kwargs["stream"], True)
        self.assertTrue(response.raw.closed if response.raw is not None else True)

    def test_streamed_response_stops_at_a_configured_byte_budget(self):
        import requests
        sess = FakeSession()
        response = requests.Response()
        response.status_code = 200
        response._content = b"x" * 1000
        response._content_consumed = True
        sess.get.return_value = response
        with patch.object(v2, "MAX_DETAIL_RESPONSE", 300):
            result = v2.request_public("scrinis", "detail", sess, identifier="3014")
        self.assertEqual(result["status"], "RESPONSE_TOO_LARGE")

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

    def test_official_scrinis_public_n_over_opaque_uuid(self):
        # Fields reproduced from the official GET /api/v1/series/9884 and
        # search result shape; identifiers are illustrative but typed.
        search = {"items": [{
            "hub_id": "7d362751-a6c9-4620-a873-864f33120482",
            "public_n": 9884, "ids": {}, "title": "Bestia",
            "title_localized": "Bestia", "type": "comic", "genres": ["Aventure"],
        }]}
        results, schema = v2.parse_hits(search, source="scrinis")
        self.assertEqual(results[0]["id"], "9884")
        self.assertEqual(schema["identity_field_types"]["hub_id"], "str")
        self.assertEqual(schema["with_id"], 1)
        details = v2.parse_details("scrinis", {
            "hub_id": "7d362751-a6c9-4620-a873-864f33120482",
            "public_n": 9884, "type": "comic",
            "titles": {"primary": "Bestia", "all": [
                {"lang": "fr", "title": "Bestia", "role": "primary"},
                {"lang": "ja", "title": "ベスティア", "role": "alternative"}]},
            "publication": {"publisher": "Les Humanoïdes Associés", "volume_count": 2},
            "taxonomy": {
                "genres": [{"slug": "adventure", "label": "Aventure", "kind": "genre"}],
                "tags": [{"slug": "monsters", "label": "Monstres et créatures"}],
                "demographics": [{"label": "Seinen"}]},
            "credits": [{"role": "artist", "name": "Corc"},
                        {"role": "author", "name": "Corc"}],
            "editions": [{"edition": "standard", "medium": "print",
                          "lang": "fr", "volume_count": 2},
                         {"edition": "standard", "medium": "ebook",
                          "lang": "fr", "volume_count": 2}],
            "volumes": [
                {"n": 1.0, "edition": "standard", "medium": "ebook",
                 "lang": "fr", "isbn_13": "9782731624649"},
                {"n": 1.0, "edition": "standard", "medium": "print",
                 "lang": "fr", "isbn_13": "9782731652772"},
                {"n": 2.0, "edition": "standard", "medium": "print",
                 "lang": "fr", "isbn_13": "9782731672756"},
                {"n": 2.0, "edition": "standard", "medium": "ebook",
                 "lang": "fr", "isbn_13": "9782731653991"}],
            "summary": {"kind": "publisher", "text": "copyright text must never be exported"},
        })
        self.assertEqual(details["id"], "9884")
        self.assertEqual(details["title"], "Bestia")
        self.assertIn("ベスティア", details["aliases"])
        self.assertEqual(details["genres"], ["Aventure"])
        self.assertEqual(details["themes"], ["Monstres et créatures"])
        self.assertEqual(details["authors"], ["Corc"])
        self.assertEqual(details["publishers"], ["Les Humanoïdes Associés"])
        self.assertEqual(details["volume_items_seen"], 4)
        self.assertEqual(details["editions"][0]["medium"], "print")
        self.assertEqual(details["book_references"][0]["isbn13"], "9782731652772")
        self.assertEqual(details["book_references"][1]["isbn13"], "9782731672756")
        self.assertEqual([x["medium"] for x in details["book_references"]],
                         ["print", "print", "ebook", "ebook"])
        self.assertEqual(details["book_references"][0]["volume_label"], "1")
        self.assertNotIn("summary", details)
        self.assertNotIn("covers", details)

    def test_scrinis_public_n_is_not_taken_from_other_provider(self):
        payload = {"results": [{"title": "Bestia", "public_n": 9884,
                                "hub_id": "uuid-opaque"}]}
        scrinis, _ = v2.parse_hits(payload, source="scrinis")
        other, _ = v2.parse_hits(payload, source="mangaupdates")
        self.assertEqual(scrinis[0]["id"], "9884")
        self.assertIsNone(other[0]["id"])

    def test_detail_request_uses_verified_scrinis_public_n(self):
        sess = FakeSession()
        sess.get.return_value.status_code = 200
        sess.get.return_value.content = b'{"public_n":9884,"titles":{"primary":"Bestia"},"volumes":[]}'
        result = v2.request_public("scrinis", "detail", sess, identifier="9884")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["data"]["id"], "9884")
        self.assertEqual(sess.get.call_args.args[0],
                         "https://scrin.is/api/v1/series/9884")

    def test_scrinis_cache_v1_parsed_null_id_is_invalidated(self):
        import hashlib
        sess = FakeSession()
        sess.get.return_value.status_code = 200
        sess.get.return_value.content = b'{"items":[{"hub_id":3014,"title":"One Piece"}]}'
        old_key = hashlib.sha256(json.dumps(["scrinis", "search", "One Piece", None],
                                            ensure_ascii=False).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            stale = Path(d) / (old_key + ".json")
            stale.write_text('{"status":"OK","candidates":[{"id":null}]}')
            client = v2.RateLimitedClient(session=sess, cache_dir=Path(d))
            refreshed = client.call("scrinis", "search", query="One Piece")
            self.assertEqual(refreshed["candidates"][0]["id"], "3014")
            self.assertEqual(sess.get.call_count, 1)

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
            self.assertIn("fiches_concurrentes_a_verifier", cs.read_text(encoding="utf-8-sig"))
            self.assertIn("ブリーチ", cs.read_text(encoding="utf-8-sig"))

    def test_only_samples_from_database_no_postgres_mutations(self):
        class Cursor:
            calls = []
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, sql, params=None):
                self.calls.append(sql)
                assert sql.lstrip().upper().startswith("SELECT")
            def fetchall(self):
                return [{"title": "Naruto", "title_english": "", "title_japanese": "",
                         "mal_id": 13}]
        class Connection:
            def __init__(self): self.cur = Cursor()
            def cursor(self): return self.cur
        db = Connection()
        items = v2.v1.select_samples(db, 50)
        self.assertTrue(all(sql.lstrip().upper().startswith("SELECT") for sql in db.cur.calls))
        self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
