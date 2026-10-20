"""An imported title must match exactly one manga, never an arbitrary partial title."""
import unittest
from apps.api.app.main import find_manga_for_import


class FakeCursor:
    def __init__(self, candidates):
        self.candidates = candidates
        self.sql = ""
        self.parameters = {}

    def execute(self, sql, parameters):
        self.sql = sql
        self.parameters = parameters

    def fetchall(self):
        return self.candidates


class SafeCsvTitleMatchingTests(unittest.TestCase):
    def test_one_exact_title_is_accepted(self):
        cursor = FakeCursor([{"id": 1, "title": "Naruto", "match_rank": 0}])
        match = find_manga_for_import(cursor, "Naruto")
        self.assertEqual(match["id"], 1)
        self.assertEqual(cursor.parameters, {"title": "Naruto"})
        self.assertNotIn("ILIKE", cursor.sql)
        self.assertNotIn("like_title", cursor.sql)

    def test_duplicate_exact_alias_is_ambiguous(self):
        cursor = FakeCursor([
            {"id": 2, "title": "Manga X", "match_rank": 0},
            {"id": 3, "title": "Manga Y", "match_rank": 1},
        ])
        self.assertIsNone(find_manga_for_import(cursor, "Manga X"))
        self.assertIn("LIMIT 2", cursor.sql)

    def test_no_exact_match_is_not_guessed(self):
        cursor = FakeCursor([])
        self.assertIsNone(find_manga_for_import(cursor, "Dragon Ball"))


if __name__ == "__main__":
    unittest.main()
