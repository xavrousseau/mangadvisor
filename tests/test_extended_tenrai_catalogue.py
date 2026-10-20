"""Offline tests for paginated Tenrai catalog expansion.

No network access, real database, personal library or downloads are needed.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipelines.engine.scripts import extract_jikan as extractor
from pipelines.engine.scripts import load_jikan_to_postgres as loader


def arguments(**kwargs):
    defaults = dict(
        mode="search", start_page=1, end_page=6, limit=25, query=None,
        manga_type="manga", status=None, order_by="popularity", sort="asc",
        min_score=None, max_score=None, genres=None, genres_exclude=None,
        sfw="true", unapproved=None, top_filter=None, force=False,
        no_legacy_search_copy=True, until_end=True, sleep_seconds=0,
        timeout=5, max_retries=1, retry_delay_seconds=0,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def page(ids, next_page):
    return {
        "data": [{"mal_id": i, "title": f"Manga {i}"} for i in ids],
        "pagination": {"has_next_page": next_page},
    }


class ProgressiveCatalogTests(unittest.TestCase):
    def test_scoped_files_do_not_overwrite_general_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(extractor, "RAW_JIKAN_DIR", Path(directory)):
                general = extractor.output_path_for_mode("search", 1)
                manga = extractor.output_path_for_mode("search", 1, "manga")
                oneshot = extractor.output_path_for_mode("search", 1, "oneshot")
        self.assertEqual(len({general, manga, oneshot}), 3)
        self.assertTrue(str(manga).endswith("search/type_manga/search_page_1.json"))

    def test_stops_at_last_page_and_reuses_scoped_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            args = arguments()
            with patch.object(extractor, "RAW_JIKAN_DIR", raw), patch.object(
                extractor, "parse_args", return_value=args
            ), patch.object(
                extractor, "fetch_jikan_with_retry",
                side_effect=[page([100], True), page([101], False)]
            ) as fetch, patch.object(extractor.time, "sleep"):
                self.assertEqual(extractor.main(), 0)
                self.assertEqual(fetch.call_count, 2)
                self.assertEqual(extractor.main(), 0)
                self.assertEqual(fetch.call_count, 2)
            self.assertEqual(len(list(raw.rglob("search_page_*.json"))), 2)
            rows, count, invalid, failures = loader.collect_rows_from_files(
                loader.iter_jikan_json_files(raw, ["search"])
            )
            self.assertEqual((len(rows), count, invalid, failures), (2, 2, 0, 0))

    def test_query_metadata_prevents_wrong_cache_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            args = arguments(until_end=False, sort="asc")
            with patch.object(extractor, "RAW_JIKAN_DIR", raw), patch.object(
                extractor, "fetch_jikan_with_retry",
                side_effect=[page([10], True), page([20], False)]
            ) as fetch:
                extractor.extract_page(args, 1)
                extractor.extract_page(args, 1)
                self.assertEqual(fetch.call_count, 1)
                args.sort = "desc"
                path, count = extractor.extract_page(args, 1)
                self.assertEqual((fetch.call_count, count), (2, 1))
                obj = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(obj["data"][0]["mal_id"], 20)
                self.assertEqual(obj["mangadvisor_query"]["sort"], "desc")

    def test_untagged_legacy_cache_refreshes_when_paging_until_end(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            old = raw / "search" / "search_page_1.json"
            old.parent.mkdir(parents=True)
            old.write_text(json.dumps({
                "mangadvisor_source": "tenrai", "data": [{"mal_id": 1}]
            }), encoding="utf-8")
            with patch.object(extractor, "RAW_JIKAN_DIR", raw), patch.object(
                extractor, "fetch_jikan_with_retry", return_value=page([2], False)
            ) as fetch:
                path, _ = extractor.extract_page(arguments(manga_type=None), 1)
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual(json.loads(path.read_text())["data"][0]["mal_id"], 2)

    def test_tenrai_throttle_respects_retry_after(self):
        from unittest.mock import Mock
        too_fast = Mock(status_code=429, headers={"Retry-After": "7"})
        ok = Mock(status_code=200)
        ok.json.return_value = page([99], False)
        with patch.object(extractor.requests, "get", side_effect=[too_fast, ok]), patch.object(
            extractor.time, "sleep"
        ) as sleep:
            result = extractor.fetch_jikan_with_retry(
                "/manga", {"page": 1}, max_retries=2, retry_delay_seconds=1
            )
        self.assertEqual(result["data"][0]["mal_id"], 99)
        sleep.assert_called_once_with(7)

    def test_page_cap_is_hard_bounded(self):
        with self.assertRaisesRegex(ValueError, "2000"):
            extractor.validate_args(arguments(end_page=2001))


if __name__ == "__main__":
    unittest.main()
