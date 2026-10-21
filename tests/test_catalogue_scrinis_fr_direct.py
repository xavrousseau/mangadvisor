"""Offline real-catalogue Scrinis enrichment tests; no external requests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from pipelines.engine.scripts import enrich_catalogue_scrinis_fr as mod
from apps.api.app import main as api


def row(*, mal_id=25, title="Tokyo Ghoul",
        authors=("Ishida, Sui",), manga_type="Manga"):
    return {
        "id": 52, "mal_id": mal_id, "title": title, "title_english": title,
        "title_japanese": "東京喰種", "mal_authors": list(authors),
        "manga_type": manga_type,
    }


def scrinis_detail(*, title="Tokyo Ghoul", author="Sui Ishida", lang="fr",
                   medium="print", isbn="9780306406157", work_type="Manga",
                   identity="148390"):
    return {"status": "OK", "id": identity, "title": title,
            "authors": [author] if author else [], "work_type": work_type,
            "editions": [{"lang": lang, "medium": medium,
                          "edition": "standard"}],
            "book_references": [{"lang": lang, "medium": medium,
                                "isbn13": isbn, "edition_label": "standard",
                                "volume_label": "1"}]}


def candidates(*, name="Tokyo Ghoul", identity="148390",
               mal_id=None, fmt="Manga", extra=None):
    return {"status": "OK", "schema": {}, "candidates": [
        {"id": identity, "title": name, "aliases": [],
         "format": fmt, "mal_id": mal_id},
        *(extra or [])]}


class Provider:
    def __init__(self, *, search=None, detail=None):
        self.search = search if search is not None else candidates()
        self.detail = detail if detail is not None else {
            "status": "OK", "data": scrinis_detail()}
        self.calls = []
    def call(self, provider, kind, *, query=None, identifier=None):
        self.calls.append((provider, kind, query or identifier))
        return self.search if kind == "search" else self.detail


class Cursor:
    def __init__(self, db):
        self.db = db
        self.query = ""
        self.params = None
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        self.query = sql
        self.params = params
        self.db.statements.append(sql)
    def fetchone(self):
        if "SELECT manga_id FROM manga_scrinis_fr_fact" in self.query:
            return self.db.occupied
        if "RETURNING manga_id" in self.query:
            if "manga_scrinis_fr_fact" in self.query:
                return {"manga_id": self.params["manga_id"]}
            return {"manga_id": self.params["manga_id"]} if self.db.alias_new else None
        raise AssertionError("Unexpected SQL fetchone: " + self.query)
    def fetchall(self):
        return self.db.rows


class DB:
    def __init__(self, *, occupied=None, alias_new=True, rows=None):
        self.occupied, self.alias_new = occupied, alias_new
        self.rows = rows or []
        self.statements = []
        self.commits = 0
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self): return Cursor(self)
    def commit(self): self.commits += 1
    def transaction(self):
        db = self
        class Txn:
            def __enter__(self): return self
            def __exit__(self, *_): db.commits += 1
        return Txn()


class ScrinisDirectEnrichmentTests(unittest.TestCase):
    def test_author_tokens_match_even_when_surname_is_first(self):
        self.assertEqual(mod.compare_authors(["Ishida, Sui"], ["Sui Ishida"]), "MATCH")
        self.assertEqual(mod.compare_authors(["Gotōge, Koyoharu"], ["Koyoharu Gotōge"]), "MATCH")
        self.assertEqual(mod.compare_authors(["Ishida, Sui"], ["Tite Kubo"]), "CONFLICT")
        self.assertEqual(mod.compare_authors([], ["Sui Ishida"]), "UNVERIFIED")

    def test_exact_work_and_author_plus_french_print_isbn_adds_real_alias(self):
        provider = Provider(detail={"status": "OK", "data": scrinis_detail(title="Tokyo Ghoul - FR")})
        outcome = mod.lookup_work(row(), provider)
        self.assertEqual(outcome["status"], "MATCHED")
        self.assertEqual(outcome["work_evidence"], "EXACT_TITLE_AUTHOR")
        self.assertEqual(outcome["title"], "Tokyo Ghoul - FR")
        self.assertEqual(outcome["isbn_count"], 1)
        self.assertEqual(provider.calls, [
            ("scrinis", "search", "Tokyo Ghoul"),
            ("scrinis", "detail", "148390")])
        db = DB()
        status = mod.save_one(db, 52, outcome)
        self.assertEqual(status, "NEW_FR_ALIAS")
        self.assertIn(mod.UPSERT_FACT, db.statements)
        self.assertIn(mod.INSERT_ALIAS, db.statements)
        self.assertTrue(all("INSERT INTO user_manga_" not in q for q in db.statements))
        self.assertTrue(all("UPDATE manga SET" not in q for q in db.statements))
        self.assertNotIn("manga_fr_edition", " ".join(db.statements))

    def test_already_known_title_is_not_counted_as_new(self):
        result = mod.lookup_work(row(), Provider())
        status = mod.save_one(DB(alias_new=False), 52, result)
        self.assertEqual(status, "ALREADY_PRESENT")

    def test_known_conflicting_mal_identifier_is_rejected(self):
        provider = Provider(search=candidates(mal_id=999))
        outcome = mod.lookup_work(row(), provider)
        self.assertEqual(outcome["status"], "MAL_ID_CONFLICT")
        self.assertFalse(any(kind == "detail" for _, kind, _ in provider.calls))

    def test_matching_mal_id_can_compensate_for_missing_authors(self):
        provider = Provider(search=candidates(mal_id=25), detail={
            "status": "OK", "data": scrinis_detail(author="")})
        outcome = mod.lookup_work(row(authors=()), provider)
        self.assertEqual(outcome["status"], "MATCHED")
        self.assertEqual(outcome["work_evidence"], "SAME_MAL_ID")

    def test_search_homonyms_are_not_automatically_associated(self):
        extra = [{"id": "27705", "title": "Tokyo Ghoul", "aliases": [],
                  "format": "Manga", "mal_id": None}]
        provider = Provider(search=candidates(extra=extra))
        outcome = mod.lookup_work(row(), provider)
        self.assertEqual(outcome["status"], "AMBIGUOUS")
        self.assertEqual(len(provider.calls), 1)

    def test_author_disagreement_and_missing_author_require_review(self):
        mismatch = Provider(detail={"status": "OK", "data": scrinis_detail(author="Kubo Tite")})
        self.assertEqual(mod.lookup_work(row(), mismatch)["status"], "AUTHOR_CONFLICT")
        unknown = Provider(detail={"status": "OK", "data": scrinis_detail(author="")})
        self.assertEqual(mod.lookup_work(row(), unknown)["status"], "NEEDS_AUTHOR_REVIEW")

    def test_no_french_print_isbn_no_alias_and_no_fake_edition(self):
        for lang, medium in [("ja", "print"), ("fr", "ebook")]:
            with self.subTest(lang=lang, medium=medium):
                provider = Provider(detail={"status": "OK", "data": scrinis_detail(
                    lang=lang, medium=medium)})
                result = mod.lookup_work(row(), provider)
                self.assertEqual(result["status"], "NO_FR_PRINT_ISBN")
                db = DB()
                self.assertEqual(mod.save_one(db, 52, result), "NO_FR_PRINT_ISBN")
                self.assertNotIn(mod.INSERT_ALIAS, db.statements)
                self.assertNotIn(mod.UPSERT_FACT, db.statements)

    def test_mal_work_and_scrinis_derived_formats_cannot_mix(self):
        result = mod.lookup_work(row(manga_type="Manga"), Provider(
            detail={"status": "OK", "data": scrinis_detail(work_type="Novel")}))
        self.assertEqual(result["status"], "WORK_TYPE_CONFLICT")

    def test_one_provider_identity_cannot_be_reused_for_two_mal_works(self):
        result = mod.lookup_work(row(), Provider())
        db = DB(occupied={"manga_id": 987})
        self.assertEqual(mod.save_one(db, 52, result), "AMBIGUOUS")
        self.assertNotIn(mod.INSERT_ALIAS, db.statements)
        self.assertNotIn(mod.UPSERT_FACT, db.statements)
        self.assertIn(mod.UPSERT_ATTEMPT, db.statements)

    def test_provider_unavailable_stops_safely(self):
        client = Provider(search={"status": "UNAVAILABLE", "http_status": 429})
        db = DB(rows=[row(), row(mal_id=30)])
        report = mod.run_batch(lambda: db, limit=2, client=client)
        self.assertEqual(report["provider_errors"], 1)
        self.assertEqual(report["matched_sources"], 0)
        self.assertEqual(report["new_french_aliases"], 0)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(report["selected"], 2)

    def test_sql_targets_unenriched_canonical_mal_and_prioritizes_library(self):
        sql = mod.SELECT_WORK
        self.assertIn("FROM manga m", sql)
        self.assertIn("jikan_manga_source", sql)
        self.assertIn("user_manga_inventory_declaration", sql)
        self.assertIn("m.source_mal_id", sql)
        self.assertIn("SCRINIS_FR_PRINT", sql)
        self.assertIn("INTERVAL '45 days'", sql)
        for protected in ("INSERT INTO user_manga_", "DELETE FROM manga",
                          "UPDATE manga SET", "TRUNCATE"):
            self.assertNotIn(protected, " ".join(
                (mod.SCHEMA, mod.UPSERT_FACT, mod.INSERT_ALIAS, mod.UPSERT_ATTEMPT)))
        self.assertNotIn("'One-shot'", mod.SELECT_WORK)

    def test_api_and_ui_use_scrinis_source_in_live_catalogue(self):
        db = DB()
        # Actual SQL source priority must be recognized by API in same branch.
        s = api.PUBLIC_METADATA_SELECT
        self.assertIn("SCRINIS_FR_PRINT", s)
        self.assertIn("a.source_name WHEN 'SCRINIS_FR_PRINT' THEN 0", s)
        self.assertIn("SCRINIS_FR_PRINT", api.catalogue_coverage.__code__.co_consts.__repr__())
        from pathlib import Path
        code = (Path(__file__).resolve().parents[1] / "apps/web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn('manga.title_fr_source==="SCRINIS_FR_PRINT"', code)


if __name__ == "__main__":
    unittest.main()
