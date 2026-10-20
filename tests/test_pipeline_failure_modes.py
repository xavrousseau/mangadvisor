"""Fail closed when the ingestion stage has no usable external records.

These tests are intentionally offline and cannot touch personal PostgreSQL data.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pipelines.engine.scripts import load_jikan_to_postgres as catalogue
from pipelines.engine.scripts import load_jikan_recommendations_to_postgres as recommendations


class IngestionExitCodeTests(unittest.TestCase):
    def test_catalogue_without_files_is_an_error(self):
        with patch.object(catalogue, "parse_args") as args, patch.object(
            catalogue, "iter_jikan_json_files", return_value=[]
        ):
            args.return_value.sources = ["search", "top"]
            args.return_value.no_dedupe = False
            self.assertEqual(catalogue.main(), 1)

    def test_catalogue_with_only_invalid_rows_is_an_error(self):
        with patch.object(catalogue, "parse_args") as args, patch.object(
            catalogue, "iter_jikan_json_files", return_value=[Path("broken.json")]
        ), patch.object(catalogue, "collect_rows_from_files", return_value=([], 0, 0, 1)):
            args.return_value.sources = ["search"]
            args.return_value.no_dedupe = False
            self.assertEqual(catalogue.main(), 1)

    def test_catalogue_rejects_partial_corruption_before_db_writes(self):
        good = {"mal_id": 31, "title": "Verified title"}
        with patch.object(catalogue, "parse_args") as args, patch.object(
            catalogue, "iter_jikan_json_files", return_value=[Path("good.json"), Path("broken.json")]
        ), patch.object(catalogue, "collect_rows_from_files", return_value=([good], 1, 0, 1)), patch.object(
            catalogue, "get_postgres_connection"
        ) as open_database:
            args.return_value.sources = ["search"]
            args.return_value.no_dedupe = False
            self.assertEqual(catalogue.main(), 1)
            open_database.assert_not_called()

    def test_recommendations_without_files_is_an_error(self):
        with patch.object(recommendations, "parse_args") as args, patch.object(
            recommendations, "iter_recommendation_files", return_value=[]
        ):
            args.return_value.reset = False
            self.assertEqual(recommendations.main(), 1)

    def test_recommendations_without_usable_edges_is_an_error(self):
        database = Mock()
        with patch.object(recommendations, "parse_args") as args, patch.object(
            recommendations, "iter_recommendation_files",
            return_value=[Path("manga_1_recommendations.json")]
        ), patch.object(recommendations, "get_postgres_connection", return_value=database), patch.object(
            recommendations, "get_manga_mapping", return_value=({1: 123}, {1: "Synthetic"})
        ), patch.object(recommendations, "load_json_file", return_value={"data": []}), patch.object(
            recommendations, "upsert_recommendation_rows"
        ) as upsert:
            args.return_value.reset = False
            self.assertEqual(recommendations.main(), 1)
            upsert.assert_not_called()
            database.close.assert_called_once()

    def test_recommendations_reject_partial_corruption_before_db_writes(self):
        database = Mock()
        rows = {"mal_id": 1, "title": "Synthetic"}
        files = [Path("manga_1_recommendations.json"), Path("manga_2_recommendations.json")]
        def read_file(path):
            if "manga_2_" in path.name:
                raise ValueError("Invalid JSON")
            return {"data": [rows]}
        with patch.object(recommendations, "parse_args") as args, patch.object(
            recommendations, "iter_recommendation_files", return_value=files
        ), patch.object(recommendations, "get_postgres_connection", return_value=database), patch.object(
            recommendations, "get_manga_mapping", return_value=({1: 100, 2: 200}, {1: "A", 2: "B"})
        ), patch.object(recommendations, "load_json_file", side_effect=read_file), patch.object(
            recommendations, "parse_recommendation_item", return_value={
                "source_manga_id": 100, "recommended_mal_id": 2,
                "recommended_manga_id": 200, "recommended_title": "Synthetic",
                "votes": 2, "raw_json": "{}"
            }
        ), patch.object(recommendations, "upsert_recommendation_rows") as upsert:
            args.return_value.reset = False
            self.assertEqual(recommendations.main(), 1)
            upsert.assert_not_called()
            database.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
