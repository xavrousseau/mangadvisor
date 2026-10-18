"""No user data is modified by scan previews; confirmed writes are additive."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from apps.api.app.collection_scan import (
    ScanConfirmation, normalize_isbn, scan_router,
)

ISBN = "9782871294146"
RECORD = {
    "isbn13": ISBN, "title_fr": "Naruto. Tome 1",
    "publisher_fr": "Kana", "author_fr": "Masashi Kishimoto",
    "release_date_text": "2002", "source_name": "BNF",
    "source_url": "https://catalogue.bnf.fr/ark:/12148/cb12345678x",
    "source_checked_at": "2026-10-18T12:00:00+00:00",
    "verified_isbn": True, "edition_kind_suggested": "UNKNOWN",
}


class FakeDB:
    def __init__(self):
        self.edition = None
        self.commits = 0
        self.statements = []
        self.is_owned = False
        self.is_read = False
        self.manga_exists = True

    def __call__(self):
        return FakeConn(self)


class FakeConn:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.db.commits += 1


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.sql = " ".join(sql.split())
        self.db.statements.append(self.sql)
        if self.sql.startswith("INSERT INTO manga_fr_edition"):
            self.db.edition = {
                "edition_id": 7, "manga_id": params["manga_id"], "manga_title": "Naruto",
                "isbn13": params["isbn13"], "title_fr": params["title_fr"],
                "publisher_fr": params["publisher_fr"],
                "edition_kind": params["edition_kind"],
                "volume_number": params["volume_number"],
                "source_url": params["source_url"],
            }
        if self.sql.startswith("INSERT INTO user_manga_volume"):
            self.db.is_owned = self.db.is_owned or params["owned"]
            self.db.is_read = self.db.is_read or params["read"]

    def fetchone(self):
        if self.sql.startswith("SELECT ed.id AS edition_id"):
            if self.db.edition is None:
                return None
            return {**self.db.edition, "is_owned": self.db.is_owned, "is_read": self.db.is_read}
        if self.sql.startswith("SELECT id FROM manga"):
            return {"id": 1} if self.db.manga_exists else None
        raise AssertionError("Unexpected SQL fetchone: " + self.sql[:100])


def route(db, path, method):
    return next(r.endpoint for r in scan_router(db).routes if
                r.path == "/collection/scan/" + path and method in r.methods)


def new_payload(**overrides):
    data = dict(isbn13=ISBN, confirmed=True, manga_id=1,
                edition_kind="CLASSIC", volume_number=1,
                is_owned=True, is_read=False)
    data.update(overrides)
    return ScanConfirmation(**data)


class ScanTests(unittest.TestCase):
    def test_only_valid_book_isbns_and_explicit_confirmation(self):
        self.assertEqual(normalize_isbn("978-2-87129-414-6"), ISBN)
        for value in ("4006381333931", "9782871294140", "not-a-book"):
            with self.subTest(value=value), self.assertRaises(HTTPException) as caught:
                normalize_isbn(value)
            self.assertEqual(caught.exception.status_code, 422)
        with self.assertRaises(Exception):
            new_payload(confirmed=False)

    def test_preview_is_read_only(self):
        db = FakeDB()
        result = route(db, "status/{raw_isbn}", "GET")(ISBN)
        self.assertFalse(result["registered"])
        self.assertEqual(db.commits, 0)
        self.assertFalse(any(sql.startswith("INSERT") for sql in db.statements))

    def test_unverified_isbn_never_creates_books(self):
        db = FakeDB()
        confirm = route(db, "confirm", "POST")
        with patch("apps.api.app.collection_scan.lookup_bnf", return_value=None):
            with self.assertRaises(HTTPException) as caught:
                confirm(new_payload())
        self.assertEqual(caught.exception.status_code, 404)
        self.assertIsNone(db.edition)
        self.assertEqual(db.commits, 0)

    def test_series_edition_and_tome_required_for_unknown_books(self):
        db = FakeDB()
        with self.assertRaises(HTTPException) as caught:
            route(db, "confirm", "POST")(ScanConfirmation(
                isbn13=ISBN, confirmed=True, is_owned=True,
            ))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(db.commits, 0)

    def test_new_scan_creates_edition_and_marks_owned_in_one_transaction(self):
        db = FakeDB()
        with patch("apps.api.app.collection_scan.lookup_bnf", return_value=dict(RECORD)) as bnf:
            result = route(db, "confirm", "POST")(new_payload(edition_kind="PERFECT"))
        bnf.assert_called_once_with(ISBN)
        self.assertEqual(result["status"], "created")
        self.assertEqual(db.edition["edition_kind"], "PERFECT")
        self.assertTrue(result["edition"]["is_owned"])
        self.assertFalse(result["edition"]["is_read"])
        self.assertEqual(db.commits, 1)
        self.assertFalse(any("user_manga_library" in sql for sql in db.statements))

    def test_known_scan_never_calls_bnf_or_creates_duplicate_and_preserves_read(self):
        db = FakeDB()
        db.edition = {
            "edition_id": 7, "manga_id": 1, "manga_title": "Naruto",
            "isbn13": ISBN, "title_fr": "Naruto Tome 1",
            "publisher_fr": "Kana", "edition_kind": "CLASSIC",
            "volume_number": 1, "source_url": RECORD["source_url"],
        }
        db.is_read = True
        with patch("apps.api.app.collection_scan.lookup_bnf", side_effect=AssertionError("No BnF")):
            result = route(db, "confirm", "POST")(ScanConfirmation(
                isbn13=ISBN, confirmed=True, is_owned=True, is_read=False,
            ))
        self.assertEqual(result["status"], "updated")
        self.assertTrue(result["edition"]["is_owned"])
        self.assertTrue(result["edition"]["is_read"])
        self.assertFalse(any(sql.startswith("INSERT INTO manga_fr_edition") for sql in db.statements))

    def test_existing_isbn_cannot_move_to_wrong_series(self):
        db = FakeDB()
        db.edition = {
            "edition_id": 7, "manga_id": 1, "manga_title": "Naruto",
            "isbn13": ISBN, "title_fr": "Naruto Tome 1",
            "publisher_fr": "Kana", "edition_kind": "CLASSIC",
            "volume_number": 1, "source_url": RECORD["source_url"],
        }
        with self.assertRaises(HTTPException) as caught:
            route(db, "confirm", "POST")(new_payload(manga_id=2))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(db.commits, 0)

    def test_requires_a_positive_status(self):
        with self.assertRaises(HTTPException) as caught:
            route(FakeDB(), "confirm", "POST")(new_payload(is_owned=False, is_read=False))
        self.assertEqual(caught.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
