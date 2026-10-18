"""Tests indépendants de PostgreSQL pour l'API de couvertures Mangadvisor."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from apps.api.app.main import get_manga_covers


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.parameters = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parameters):
        self.sql = sql
        self.parameters = parameters

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_instance


class CoverEndpointTests(unittest.TestCase):
    def test_batch_preserves_id_mapping_and_filters_external_urls(self):
        conn = FakeConnection([
            {"manga_id": 1, "image_url": "https://cdn.myanimelist.net/images/manga/1/a.jpg"},
            {"manga_id": 2, "image_url": "https://example.org/tracker.jpg"},
            {"manga_id": 3, "image_url": None},
        ])
        with patch("apps.api.app.main.get_connection", return_value=conn):
            response = get_manga_covers(ids="1,2,3,1")
        self.assertEqual(response["count"], 3)
        self.assertEqual(conn.cursor_instance.parameters["manga_ids"], [1, 2, 3])
        self.assertIn("j.raw_json", conn.cursor_instance.sql)
        self.assertTrue(response["covers"][0]["image_url"].startswith("https://cdn.myanimelist.net/"))
        self.assertIsNone(response["covers"][1]["image_url"])
        self.assertIsNone(response["covers"][2]["image_url"])

    def test_reject_invalid_identifiers(self):
        for bad in ("", "0", "-1", "abc", "1,xyz", ",".join(["1"] * 51)):
            with self.subTest(ids=bad):
                with self.assertRaises(HTTPException) as ctx:
                    get_manga_covers(ids=bad)
                self.assertEqual(ctx.exception.status_code, 400)

    def test_no_images_remains_valid(self):
        with patch("apps.api.app.main.get_connection", return_value=FakeConnection([])):
            response = get_manga_covers(ids="88")
        self.assertEqual(response, {"count": 0, "covers": []})


if __name__ == "__main__":
    unittest.main()
