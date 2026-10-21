"""Offline safeguards for duplicate MAL IDs and PostgreSQL metadata upserts."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from pipelines.engine.scripts.load_jikan_to_postgres import (
    collect_rows_from_files, merge_manga_rows, transform_jikan_item,
)
from pipelines.engine.src.load.postgres_loader import upsert_jikan_manga_batch


class MetadataMergeTests(unittest.TestCase):
    def test_sparse_duplicate_does_not_erase_titles_tags_or_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "search" / "search_page_1.json"
            second = root / "top" / "top_manga_page_1.json"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_text(json.dumps({"mangadvisor_source": "tenrai", "data": [{
                "mal_id": 7, "title": "Naruto", "title_english": "Naruto",
                "score": 8.5, "genres": [{"mal_id": 1, "name": "Action"}],
                "authors": [{"mal_id": 2, "name": "Author"}],
            }]}), encoding="utf-8")
            second.write_text(json.dumps({"mangadvisor_source": "tenrai", "data": [{
                "mal_id": 7, "title": "Naruto", "title_english": "",
                "score": None, "genres": [], "authors": [],
            }]}), encoding="utf-8")
            rows, total, invalid, errors = collect_rows_from_files([first, second])
        self.assertEqual((len(rows), total, invalid, errors), (1, 2, 0, 0))
        self.assertEqual(rows[0]["title_english"], "Naruto")
        self.assertEqual(rows[0]["score"], 8.5)
        self.assertEqual(json.loads(rows[0]["genres_json"])[0]["name"], "Action")
        self.assertEqual(len(json.loads(rows[0]["authors_json"])), 1)

    def test_new_populated_values_win_and_zero_is_valid(self):
        old = transform_jikan_item({"mal_id": 7, "title": "Old", "score": 7.0, "chapters": 12})
        new = transform_jikan_item({"mal_id": 7, "title": "New", "score": 0, "chapters": None})
        merged = merge_manga_rows(old, new)
        self.assertEqual(merged["title"], "New")
        self.assertEqual(merged["score"], 0)
        self.assertEqual(merged["chapters"], 12)

    def test_mismatched_mal_ids_rejected(self):
        a = transform_jikan_item({"mal_id": 1})
        b = transform_jikan_item({"mal_id": 2})
        with self.assertRaises(ValueError):
            merge_manga_rows(a, b)

    def test_sql_upsert_preserves_existing_values(self):
        connection = Mock()
        row = transform_jikan_item({"mal_id": 7, "title": "Example"})
        row["source_name"] = "tenrai"
        self.assertEqual(upsert_jikan_manga_batch(connection, [row]), 1)
        sql, rows = connection.cursor.return_value.__enter__.return_value.executemany.call_args.args
        self.assertIn("COALESCE(NULLIF(BTRIM(EXCLUDED.title_english)", sql)
        self.assertIn("COALESCE(EXCLUDED.score, jikan_manga_source.score)", sql)
        self.assertIn("EXCLUDED.genres_json = '[]'::jsonb", sql)
        self.assertNotIn("TRUNCATE", sql.upper())
        self.assertEqual(rows[0]["mal_id"], 7)
        connection.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
