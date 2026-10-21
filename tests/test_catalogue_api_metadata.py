"""Read-only catalogue enrichment from the already downloaded MAL source."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from apps.api.app import main as api


class Cursor:
    def __init__(self, db):
        self.db = db
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        self.db.statements.append(str(sql))
        self.db.params.append(params)
    def fetchall(self):
        return [self.db.manga_row]
    def fetchone(self):
        return self.db.manga_row


class DB:
    def __init__(self, manga_row=None):
        self.manga_row = manga_row or {
            "id": 42, "source_mal_id": 13,
            "title": "Original Japanese name", "title_fr": "Le manga français",
            "title_fr_verified": True, "title_fr_source": "TENRAI_MAL_TYPED",
            "title_fr_publication_verified": False,
            "authors": ["Auteur 1", "Auteur 2"]}
        self.statements = []
        self.params = []
        self.committed = False
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self): return Cursor(self)
    def commit(self): self.committed = True


class CatalogueAPIMetadataTests(unittest.TestCase):
    def test_catalogue_list_shows_french_work_title_without_rewriting_mal(self):
        db = DB()
        with patch.object(api, "get_connection", return_value=db):
            result = api.list_mangas(q="Le manga français", limit=20,
                                     offset=0, genre=None, only_finished=False)
        self.assertEqual(result["items"][0]["title"], "Original Japanese name")
        self.assertEqual(result["items"][0]["title_fr"], "Le manga français")
        self.assertTrue(result["items"][0]["title_fr_verified"])
        self.assertEqual(result["items"][0]["authors"], ["Auteur 1", "Auteur 2"])
        sql = db.statements[0]
        self.assertIn("manga_title_alias a", sql)
        self.assertIn("a.language_code='fr'", sql)
        self.assertIn("src.authors_json", sql)
        self.assertIn("WIKIDATA_P4087", sql)
        self.assertIn("TENRAI_MAL_TYPED", sql)
        self.assertIn("EXISTS (SELECT 1 FROM manga_title_alias ta", sql)
        self.assertTrue(sql.strip().upper().startswith("SELECT"))
        self.assertNotIn("INSERT INTO", sql.upper())

    def test_detail_has_french_work_title_author_provenance_and_no_isbn_ownership(self):
        db = DB()
        with patch.object(api, "get_connection", return_value=db):
            manga = api.get_manga(42)
        self.assertFalse(manga["title_fr_publication_verified"])
        self.assertEqual(manga["source_mal_id"], 13)
        self.assertEqual(db.params[0], {"manga_id": 42})
        self.assertIn("AS title_fr_source", db.statements[0])
        self.assertIn("AS authors", db.statements[0])
        self.assertNotIn("user_manga_volume", db.statements[0])

    def test_coverage_reports_actual_counts_not_estimated_enrichment(self):
        counts = {"canonical_works": 85776, "mal_source_works": 85776,
                  "explicit_french_mal_labels": 9,
                  "works_with_french_label": 27,
                  "source_works_with_authors": 74000,
                  "works_with_synopsis": 65000}
        db = DB(counts)
        with patch.object(api, "get_connection", return_value=db):
            result = api.catalogue_coverage()
        self.assertEqual(result["canonical_works"], 85776)
        self.assertEqual(result["works_with_french_label"], 27)
        self.assertFalse(result["french_label_is_licensed_edition"])
        self.assertIn("mal_id", result["catalogue_identity"])
        self.assertTrue(db.statements[0].strip().upper().startswith("SELECT"))

    def test_startup_materializes_only_explicit_typed_names_by_mal_id(self):
        db = DB()
        patches = [
            patch.object(api, name) for name in (
                "ensure_collection_schema", "ensure_inventory_schema",
                "ensure_bnf_schema", "ensure_wikidata_schema"
            )
        ]
        for obj in patches:
            obj.start()
            self.addCleanup(obj.stop)
        with patch.object(api, "get_connection", return_value=db):
            api.prepare_fr_collection()
        inserts = [sql for sql in db.statements if "INSERT INTO manga_title_alias" in sql]
        typed = [sql for sql in inserts if "'TENRAI_MAL_TYPED'" in sql]
        self.assertEqual(len(typed), 1)
        statement = typed[0]
        self.assertIn("src.mal_id=m.source_mal_id", statement)
        self.assertIn("('french','english','japanese')", statement)
        self.assertIn("WHEN 'french' THEN 'fr'", statement)
        self.assertIn("ON CONFLICT", statement)
        for sql in db.statements:
            self.assertNotIn("INSERT INTO user_manga_", sql)
            self.assertNotIn("UPDATE manga SET", sql.upper())
        self.assertTrue(db.committed)

    def test_frontend_actually_uses_french_work_label_and_authors(self):
        root = Path(__file__).resolve().parents[1]
        ui = (root/"apps/web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn('preferredMangaTitle(m,state.lang)', ui)
        self.assertIn('preferredMangaTitle(manga,state.lang)', ui)
        self.assertIn("manga.authors.join", ui)
        self.assertIn("pas édition physique", ui)


if __name__ == "__main__":
    unittest.main()
