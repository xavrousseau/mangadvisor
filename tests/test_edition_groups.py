"""Edition grouping: only manual confirmation, no ISBN/ownership inference."""
from __future__ import annotations

import unittest
from fastapi import HTTPException
from pydantic import ValidationError

from apps.api.app.edition_groups import (
    GROUP_SCHEMA, EditionGroupCreate, GroupBookLink,
    create_edition_group_router, ensure_edition_group_schema,
)


def group(**extra):
    return EditionGroupCreate(
        edition_key="pastel", label="Première édition française (Pastel)",
        edition_kind="OTHER", confirmation="CONFIRMER_EDITION", **extra)


def link(**extra):
    return GroupBookLink(
        book_id=42, isbn13="9782871294146",
        confirmation="CONFIRMER_RATTACHEMENT", **extra)


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.sql = ""
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        self.sql = " ".join(sql.split())
        self.db.calls.append((self.sql, params))
        if self.sql.startswith("CREATE"):
            assert "manga_fr_edition_group" in sql
        elif self.sql.startswith("INSERT"):
            assert "manga_fr_edition_group" in sql
        else:
            assert self.sql.startswith("SELECT")
    def fetchone(self):
        sql = self.sql
        db = self.db
        if "SELECT id FROM manga WHERE" in sql:
            return {"id": db.manga_id} if db.manga_exists else None
        if "INSERT INTO manga_fr_edition_group " in sql:
            return None if db.group_exists else {"id": 9}
        if "FROM manga_fr_edition_group WHERE" in sql:
            return None if not db.group_exists else {
                "id": 9, "manga_id": db.group_manga_id,
                "edition_kind": db.group_kind}
        if "FROM manga_fr_edition WHERE id=" in sql:
            return None if not db.book_exists else {
                "id": 42, "manga_id": db.book_manga_id,
                "edition_kind": db.book_kind, "isbn13": db.book_isbn,
                "source_name": db.source_name, "source_url": db.source_url}
        if "INSERT INTO manga_fr_edition_group_book" in sql:
            return None if db.book_already_grouped else {"book_id": 42}
        if "AS count" in sql:
            return {"count": 1}
        raise AssertionError(sql)
    def fetchall(self):
        if "FROM manga_fr_edition_group WHERE" in self.sql:
            return [{"id": 9, "manga_id": 1, "edition_key": "pastel",
                     "label": "Pastel", "edition_kind": "OTHER"}]
        if "FROM manga_fr_edition_group_book link" in self.sql:
            return [{"group_id": 9, "book_id": 42, "isbn13": "9782871294146",
                     "volume_number": 1}]
        raise AssertionError(self.sql)


class FakeDb:
    def __init__(self, *, manga_exists=True, group_exists=True, book_exists=True,
                 book_already_grouped=False, group_manga_id=1, group_kind="OTHER",
                 book_manga_id=1, book_kind="OTHER", book_isbn="9782871294146",
                 source_name="BnF", source_url="https://catalogue.bnf.fr/example"):
        self.manga_exists = manga_exists
        self.group_exists = group_exists
        self.book_exists = book_exists
        self.book_already_grouped = book_already_grouped
        self.group_manga_id = group_manga_id
        self.group_kind = group_kind
        self.book_manga_id = book_manga_id
        self.book_kind = book_kind
        self.book_isbn = book_isbn
        self.source_name = source_name
        self.source_url = source_url
        self.manga_id = 1
        self.calls = []
        self.commits = 0
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self): return FakeCursor(self)
    def commit(self): self.commits += 1


def handler(db, method, path):
    router = create_edition_group_router(lambda: db)
    route = next(r for r in router.routes if r.path == path and method in r.methods)
    return route.endpoint


GROUP_PATH = "/collection/mangas/{manga_id}/edition-groups"
BOOK_PATH = "/collection/mangas/{manga_id}/edition-groups/{group_id}/books"


class EditionGroupTests(unittest.TestCase):
    def test_schema_is_additive_and_fks_lock_same_work_kind_and_isbn(self):
        db = FakeDb()
        ensure_edition_group_schema(lambda: db)
        self.assertEqual(db.commits, 1)
        self.assertIn("FOREIGN KEY (book_id,manga_id,edition_kind,isbn13)", GROUP_SCHEMA)
        self.assertIn("FOREIGN KEY (group_id,manga_id,edition_kind)", GROUP_SCHEMA)
        self.assertIn("ON DELETE RESTRICT", GROUP_SCHEMA)
        self.assertIn("UNIQUE(manga_id,edition_key)", GROUP_SCHEMA)
        for forbidden in ("DROP TABLE", "TRUNCATE", "DELETE FROM",
                          "UPDATE user_manga", "INSERT INTO user_manga"):
            self.assertNotIn(forbidden, GROUP_SCHEMA)

    def test_confirmation_tokens_and_slug_are_required(self):
        with self.assertRaises(ValidationError):
            EditionGroupCreate(edition_key="pastel", label="Pastel", edition_kind="OTHER")
        with self.assertRaises(ValidationError):
            EditionGroupCreate(edition_key="Pastel", label="Pastel",
                               edition_kind="OTHER", confirmation="CONFIRMER_EDITION")
        with self.assertRaises(ValidationError):
            GroupBookLink(book_id=42, isbn13="9782871294146")
        with self.assertRaises(ValidationError):
            GroupBookLink(book_id=42, isbn13="9782871294146",
                          confirmation="yes")

    def test_create_group_never_writes_a_book_or_inventory(self):
        db = FakeDb(group_exists=False)
        result = handler(db, "POST", GROUP_PATH)(1, group())
        self.assertEqual(result["edition_key"], "pastel")
        self.assertEqual(result["books_linked"], 0)
        self.assertEqual(result["ownership_mutations"], 0)
        self.assertEqual(db.commits, 1)
        self.assertEqual(len([q for q, _ in db.calls if q.startswith("INSERT")]), 1)
        self.assertTrue(any("ON CONFLICT (manga_id,edition_key) DO NOTHING"
                            in q for q, _ in db.calls))

    def test_existing_edition_cannot_be_merged_or_overwritten(self):
        db = FakeDb(group_exists=True)
        with self.assertRaises(HTTPException) as err:
            handler(db, "POST", GROUP_PATH)(1, group())
        self.assertEqual(err.exception.status_code, 409)
        self.assertEqual(db.commits, 0)

    def test_unknown_work_has_no_side_effect(self):
        db = FakeDb(manga_exists=False, group_exists=False)
        with self.assertRaises(HTTPException) as err:
            handler(db, "POST", GROUP_PATH)(3, group())
        self.assertEqual(err.exception.status_code, 404)
        self.assertFalse(any(q.startswith("INSERT") for q, _ in db.calls))

    def test_correct_manual_book_link_preserves_ownership(self):
        db = FakeDb()
        output = handler(db, "POST", BOOK_PATH)(1, 9, link())
        self.assertEqual(output["isbn13"], "9782871294146")
        self.assertEqual(output["ownership_mutations"], 0)
        self.assertEqual(db.commits, 1)
        self.assertEqual([q for q, _ in db.calls if q.startswith("INSERT")],
                         [next(q for q, _ in db.calls
                               if q.startswith("INSERT INTO manga_fr_edition_group_book"))])

    def test_cross_work_category_isbn_or_missing_source_are_rejected(self):
        for overrides in (
            {"group_manga_id": 2},
            {"book_manga_id": 2},
            {"group_kind": "DELUXE"},
            {"book_isbn": "9780306406157"},
            {"source_name": None},
            {"source_url": ""},
        ):
            with self.subTest(overrides=overrides):
                db = FakeDb(**overrides)
                with self.assertRaises(HTTPException) as err:
                    handler(db, "POST", BOOK_PATH)(1, 9, link())
                self.assertEqual(err.exception.status_code, 409)
                self.assertFalse(any(q.startswith("INSERT") for q, _ in db.calls))
                self.assertEqual(db.commits, 0)

    def test_book_cannot_switch_between_pastel_deluxe_silently(self):
        db = FakeDb(book_already_grouped=True)
        with self.assertRaises(HTTPException) as err:
            handler(db, "POST", BOOK_PATH)(1, 9, link())
        self.assertEqual(err.exception.status_code, 409)
        self.assertEqual(db.commits, 0)

    def test_wrong_isbn_checksum_is_rejected_before_query(self):
        db = FakeDb()
        with self.assertRaises(HTTPException) as err:
            handler(db, "POST", BOOK_PATH)(1, 9, link(isbn13="9782871294141"))
        self.assertEqual(err.exception.status_code, 422)
        self.assertEqual(db.calls, [])

    def test_read_only_tree_counts_only_explicit_registered_books(self):
        db = FakeDb()
        result = handler(db, "GET", GROUP_PATH)(1)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["ungrouped_registered_books"], 1)
        self.assertEqual(result["groups"][0]["books"][0]["book_id"], 42)
        self.assertFalse(result["published_totals_known"])
        self.assertFalse(result["ownership_verified"])
        self.assertFalse(any(q.startswith("INSERT") for q, _ in db.calls))


if __name__ == "__main__":
    unittest.main()
