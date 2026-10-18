"""Tests de la découverte et des filtres, sans écrire en base de données."""
import unittest
from unittest.mock import patch

from apps.ui.app.discovery import (
    PAGE_SIZE,
    GENRES,
    normalize_search,
    paginated_catalog,
)
from apps.api.app.main import list_mangas


class FakeCursor:
    def __init__(self, results):
        self.results = results
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.results


class FakeConnection:
    def __init__(self, results):
        self.fake_cursor = FakeCursor(results)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.fake_cursor


class DiscoveryTests(unittest.TestCase):
    def test_query_normalization(self):
        self.assertEqual(normalize_search("  Vinland   Saga  "), "Vinland Saga")
        self.assertEqual(normalize_search(" \n "), "")
        self.assertEqual(len(normalize_search("A" * 200)), 120)

    def test_gallery_pagination_boundary(self):
        items = [{"id": i} for i in range(PAGE_SIZE + 1)]
        visible, has_next = paginated_catalog(items)
        self.assertEqual(len(visible), PAGE_SIZE)
        self.assertTrue(has_next)
        self.assertFalse(paginated_catalog(items[:PAGE_SIZE])[1])
        self.assertEqual(paginated_catalog([]), ([], False))

    def test_all_genre_values_are_real_filter_values(self):
        self.assertIsNone(GENRES["Tous les genres"])
        self.assertEqual(GENRES["Aventure"], "Adventure")

    def test_api_combines_filters_with_parenthesized_search(self):
        conn = FakeConnection([{"id": 123, "title": "Naruto"}])
        with patch("apps.api.app.main.get_connection", return_value=conn):
            response = list_mangas(
                q="Naruto", limit=13, offset=12,
                genre="Action", only_finished=True,
            )
        self.assertEqual(response["count"], 1)
        self.assertEqual(conn.fake_cursor.params["q"], "%Naruto%")
        self.assertEqual(conn.fake_cursor.params["genre"], "Action")
        self.assertEqual(conn.fake_cursor.params["offset"], 12)
        self.assertIn("WHERE (m.title ILIKE", conn.fake_cursor.sql)
        self.assertIn("EXISTS (", conn.fake_cursor.sql)
        self.assertIn("LOWER(COALESCE(m.status, '')) = 'finished'", conn.fake_cursor.sql)
        self.assertIn("AND EXISTS", conn.fake_cursor.sql)
        self.assertIn("AND LOWER", conn.fake_cursor.sql)

    def test_api_unfiltered_catalog_uses_no_where_clause(self):
        conn = FakeConnection([])
        with patch("apps.api.app.main.get_connection", return_value=conn):
            response = list_mangas(
                q=None, limit=13, offset=0,
                genre=None, only_finished=False,
            )
        self.assertEqual(response["items"], [])
        self.assertNotIn("WHERE (m.title", conn.fake_cursor.sql)
        self.assertNotIn("AND EXISTS", conn.fake_cursor.sql)
        self.assertEqual(conn.fake_cursor.params, {"limit": 13, "offset": 0})


if __name__ == "__main__":
    unittest.main()
