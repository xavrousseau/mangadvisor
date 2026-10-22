"""Search index tests: no personal data, no actual network or PostgreSQL writes."""
import unittest
from unittest.mock import patch

from apps.api.app import search_index
from apps.api.app.main import list_mangas


class DummyCursor:
    def __init__(self):
        self.sql = ""
        self.params = None
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params):
        self.sql, self.params = sql, params
    def fetchall(self):
        return [{"id": 7, "title": "Naruto"}]


class DummyConnection:
    def __init__(self):
        self.cur = DummyCursor()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def cursor(self):
        return self.cur


class SearchIndexTests(unittest.TestCase):
    def test_typos_are_served_by_ranked_meilisearch_ids_with_sql_records(self):
        db = DummyConnection()
        with patch("apps.api.app.main.get_connection", return_value=db), patch(
            "apps.api.app.main.meili_search_ids", return_value=[7, 11]
        ) as search:
            output = list_mangas(q="Narutoo", limit=13, offset=0, genre=None, only_finished=False)
        search.assert_called_once_with("Narutoo", limit=500)
        self.assertEqual(output["items"][0]["title"], "Naruto")
        self.assertIn("m.id = ANY(%(search_ids)s::int[])", db.cur.sql)
        self.assertIn("array_position(%(search_ids)s::int[],m.id)", db.cur.sql)
        self.assertEqual(db.cur.params["search_ids"], [7, 11])
        self.assertNotIn("q", db.cur.params)

    def test_missing_index_uses_original_postgresql_query(self):
        db = DummyConnection()
        with patch("apps.api.app.main.get_connection", return_value=db), patch(
            "apps.api.app.main.meili_search_ids", return_value=None
        ):
            list_mangas(q="Naruto", limit=13, offset=0, genre=None, only_finished=False)
        self.assertIn("m.title ILIKE", db.cur.sql)
        self.assertEqual(db.cur.params["q"], "%Naruto%")

    def test_empty_index_also_falls_back_to_sql_for_new_titles(self):
        db = DummyConnection()
        with patch("apps.api.app.main.get_connection", return_value=db), patch(
            "apps.api.app.main.meili_search_ids", return_value=[]
        ):
            list_mangas(q="New Manga", limit=13, offset=0, genre=None, only_finished=False)
        self.assertEqual(db.cur.params["q"], "%New Manga%")

    def test_genre_filters_and_deep_pagination_still_use_sql(self):
        for options in ({"genre": "Adventure", "only_finished": False, "offset": 0},
                        {"genre": None, "only_finished": True, "offset": 0},
                        {"genre": None, "only_finished": False, "offset": 500}):
            with self.subTest(**options):
                db=DummyConnection()
                with patch("apps.api.app.main.get_connection", return_value=db), patch(
                    "apps.api.app.main.meili_search_ids"
                ) as search:
                    list_mangas(q="Naruto", limit=13, **options)
                search.assert_not_called()
                self.assertEqual(db.cur.params["q"], "%Naruto%")

    def test_index_contains_only_public_metadata(self):
        index_source = open(search_index.__file__, encoding="utf-8").read()
        for secret in ("user_manga_library", "user_manga_inventory", "user_score",
                       "is_favorite", "POSTGRES_PASSWORD", "owned_volumes"):
            with self.subTest(name=secret):
                self.assertNotIn(secret, index_source.split("SELECT m.id")[1].split('""")')[0])

    def test_search_unavailable_does_not_crash(self):
        with patch.object(search_index, "_request", side_effect=OSError("connection refused")):
            self.assertIsNone(search_index.search_ids("Naruto"))
