"""Offline regressions migrated from historical --reset-library runners.

Use fake SQL connection only; never issue HTTP calls or touch personal storage.
Legacy 'update existing rows' expectation is intentionally replaced with ADD-ONLY
preservation, as required by the current import contract.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.api.app.main import LibraryImportCsvRequest, import_library_csv


class Cursor:
    def __init__(self):
        self.commands = []
        self.records = {
            "Naruto": {"id": 1, "title": "Naruto", "manga_type": "Manga",
                       "score": 8.0, "popularity": 10, "match_rank": 0},
            "Monster": {"id": 2, "title": "Monster", "manga_type": "Manga",
                        "score": 9.0, "popularity": 20, "match_rank": 0},
        }
        self.last_title = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, values):
        self.commands.append((sql, values))
        if "SELECT" in sql and "FROM manga" in sql:
            self.last_title = values["title"]

    def fetchall(self):
        result = self.records.get(self.last_title)
        return [result] if result else []


class Connection:
    def __init__(self):
        self.cursor_object = Cursor()
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_object

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    @property
    def writes(self):
        return [(sql, params) for sql, params in self.cursor_object.commands
                if "INSERT INTO user_manga_library" in sql]


class LegacyCsvContractTests(unittest.TestCase):
    def exercise_import(self, csv_content, *, delimiter=",", dry_run=False):
        conn = Connection()
        payload = LibraryImportCsvRequest(
            csv_content=csv_content, delimiter=delimiter,
            dry_run=dry_run,
        )
        with patch("apps.api.app.main.get_connection", return_value=conn):
            report = import_library_csv(payload)
        return report, conn

    def test_french_headers_semicolon_and_comma_decimal(self):
        report, conn = self.exercise_import(
            "titre;statut;note;favori;commentaire\n"
            "Naruto;READ;8,5;oui;Commentaire, avec virgule\n", delimiter=";"
        )
        self.assertEqual((report["matched_count"], report["error_count"]), (1, 0))
        self.assertEqual(len(conn.writes), 1)
        values = conn.writes[0][1]
        self.assertEqual(values["user_score"], 8.5)
        self.assertTrue(values["is_favorite"])
        self.assertEqual(values["notes"], "Commentaire, avec virgule")

    def test_invalid_status_only_rejects_affected_row(self):
        report, conn = self.exercise_import(
            "title,library_status\nNaruto,READ\nMonster,JAI_LU\n"
        )
        self.assertEqual((report["matched_count"], report["error_count"]), (1, 1))
        self.assertEqual(len(conn.writes), 1)

    def test_missing_title_and_unknown_manga_do_not_create_entries(self):
        report, conn = self.exercise_import(
            "title,library_status\n,READ\nUnknown Series,READ\nNaruto,READ\n"
        )
        self.assertEqual(
            (report["matched_count"], report["error_count"], report["not_found_count"]),
            (1, 1, 1),
        )
        self.assertEqual(len(conn.writes), 1)

    def test_invalid_favorite_does_not_write_row(self):
        report, conn = self.exercise_import(
            "title,is_favorite\nMonster,maybe\nNaruto,yes\n"
        )
        self.assertEqual((report["matched_count"], report["error_count"]), (1, 1))
        self.assertEqual(len(conn.writes), 1)

    def test_duplicate_rows_remain_add_only_at_sql_level(self):
        report, conn = self.exercise_import(
            "title,library_status\nNaruto,READ\nNaruto,WANT_TO_READ\n"
        )
        self.assertEqual(report["matched_count"], 2)
        self.assertEqual(len(conn.writes), 2)
        self.assertTrue(all("ON CONFLICT (user_id, manga_id) DO NOTHING" in sql
                            for sql, _ in conn.writes))

    def test_existing_library_row_is_not_overwritten(self):
        report, conn = self.exercise_import(
            "title,library_status,user_score,is_favorite\n"
            "Naruto,READ,3.0,no\n"
        )
        self.assertEqual(report["matched_count"], 1)
        self.assertIn("DO NOTHING", conn.writes[0][0])
        self.assertNotIn("DO UPDATE", conn.writes[0][0])

    def test_dry_run_rolls_back_and_never_sends_an_insert(self):
        report, conn = self.exercise_import(
            "title,library_status\nNaruto,READ\n", dry_run=True
        )
        self.assertEqual(report["status"], "dry_run")
        self.assertEqual(len(conn.writes), 0)
        self.assertEqual((conn.rollbacks, conn.commits), (1, 0))

    def test_not_found_never_uses_fuzzy_title_matching(self):
        report, conn = self.exercise_import(
            "title,library_status\nNarut,READ\n"
        )
        self.assertEqual(report["not_found_count"], 1)
        self.assertEqual(len(conn.writes), 0)


if __name__ == "__main__":
    unittest.main()
