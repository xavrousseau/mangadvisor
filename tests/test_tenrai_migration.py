"""Contract tests for Tenrai's Jikan-compatible manga ingestion (offline fixtures)."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pipelines.engine.scripts import extract_jikan
from pipelines.engine.scripts import extract_jikan_recommendations as reco
from pipelines.engine.scripts.load_jikan_to_postgres import collect_rows_from_files
from pipelines.engine.src.load.postgres_loader import upsert_jikan_manga_batch


SAMPLE_MANGA = {
    "mal_id": 2,
    "title": "Berserk",
    "title_english": "Berserk",
    "genres": [{"mal_id": 1, "name": "Action"}],
    "themes": [],
    "demographics": [],
}


class FakeConnection:
    def __init__(self):
        self.last_query = None
        self.last_rows = None
        self.committed = False

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def executemany(self, statement, rows):
        self.last_query = statement
        self.last_rows = rows

    def commit(self):
        self.committed = True


class TenraiMigrationTests(unittest.TestCase):
    def test_defaults_target_tenrai(self):
        self.assertEqual(extract_jikan.JIKAN_BASE_URL, os.getenv("MANGA_API_BASE_URL", "https://api.tenrai.org/v1").rstrip("/"))
        self.assertEqual(reco.JIKAN_BASE_URL, extract_jikan.JIKAN_BASE_URL)

    @patch("pipelines.engine.scripts.extract_jikan.requests.get")
    def test_catalog_requires_list_envelope(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"data": [SAMPLE_MANGA]}
        result = extract_jikan.fetch_jikan_with_retry("/manga", {"page": 1, "limit": 1}, max_retries=1)
        self.assertEqual(result["data"][0]["mal_id"], 2)
        get.return_value.json.return_value = {"error": "schema changed"}
        with self.assertRaisesRegex(ValueError, "incompatible"):
            extract_jikan.fetch_jikan_with_retry("/manga", {"page": 1, "limit": 1}, max_retries=1)

    def test_provider_origin_is_loaded_into_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "search_page_1.json"
            path.write_text(json.dumps({"data": [SAMPLE_MANGA], "mangadvisor_source": "tenrai"}), encoding="utf-8")
            rows, count, invalid, file_errors = collect_rows_from_files([path])
        self.assertEqual((count, invalid, file_errors), (1, 0, 0))
        self.assertEqual(rows[0]["source_name"], "tenrai")
        db = FakeConnection()
        self.assertEqual(upsert_jikan_manga_batch(db, rows), 1)
        self.assertIn("source_name = EXCLUDED.source_name", db.last_query)
        self.assertTrue(db.committed)

    def test_old_jikan_cache_is_not_used_as_current_tenrai(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            cache = raw / "search" / "search_page_1.json"
            cache.parent.mkdir(parents=True)
            cache.write_text(json.dumps({
                "data": [SAMPLE_MANGA], "mangadvisor_source": "jikan"
            }), encoding="utf-8")
            args = argparse.Namespace(
                mode="search", force=False, no_legacy_search_copy=True,
                timeout=5, max_retries=1, retry_delay_seconds=0
            )
            with patch.object(extract_jikan, "RAW_JIKAN_DIR", raw), patch.object(
                extract_jikan, "JIKAN_BASE_URL", "https://api.tenrai.org/v1"
            ), patch.object(extract_jikan, "build_search_params", return_value={"page": 1}), patch.object(
                extract_jikan, "fetch_jikan_with_retry",
                return_value={"data": [SAMPLE_MANGA]}
            ) as fetch:
                path, count = extract_jikan.extract_page(args, 1)
                self.assertEqual(count, 1)
                fetch.assert_called_once()
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["mangadvisor_source"], "tenrai")
                extract_jikan.extract_page(args, 1)
                fetch.assert_called_once()  # Fresh Tenrai cache is reused safely.

    def test_legacy_json_remains_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manga_page_1.json"
            path.write_text(json.dumps({"data": [SAMPLE_MANGA]}), encoding="utf-8")
            rows, *_ = collect_rows_from_files([path])
        self.assertEqual(rows[0]["source_name"], "jikan")


if __name__ == "__main__":
    unittest.main()
