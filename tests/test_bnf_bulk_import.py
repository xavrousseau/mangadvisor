"""Offline contract tests for importing UTF-8 UNIMARC BnF batches.

Synthetic ISO2709 fixtures only: no network, PostgreSQL or personal collection.
"""
from __future__ import annotations

import gzip
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pipelines.engine.scripts import bnf_bulk_import as importer


def data_field(*subfields):
    return b"  " + b"".join(b"\x1f" + code.encode("ascii") + text.encode("utf-8")
                             for code, text in subfields) + b"\x1e"


def make_record(*, notice="FRBNF99900001", title="Dragon Ball, tome 1",
                subject="Mangas", isbn="9780306406157",
                series="Dragon Ball", volume="1"):
    fields = [
        ("001", notice.encode() + b"\x1e"),
        ("010", data_field(("a", isbn))),
        ("200", data_field(("a", title), ("f", "Akira Toriyama"))),
        ("214", data_field(("c", "Glénat"), ("d", "2024"))),
        ("225", data_field(("a", series), ("v", volume))),
        ("606", data_field(("a", subject))),
        ("801", data_field(("b", "FR-BnF"), ("c", "20261020"))),
    ]
    directory, body = b"", b""
    for tag, payload in fields:
        directory += tag.encode() + f"{len(payload):04d}{len(body):05d}".encode()
        body += payload
    base = 24 + len(directory) + 1
    size = base + len(body) + 1
    leader = (f"{size:05d}" + "n" * 7 + f"{base:05d}" + "n" * 7).encode()
    assert len(leader) == 24
    return leader + directory + b"\x1e" + body + b"\x1d"


class FakeCursor:
    def __init__(self, db):
        self.db = db
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, statement, params=None):
        self.db.statements.append(statement)
    def executemany(self, statement, rows):
        self.db.statements.append(statement)
        self.db.rows.extend(rows)
    def fetchone(self):
        return self.db.existing


class FakeDb:
    def __init__(self, existing=None):
        self.existing = existing
        self.statements = []
        self.rows = []
        self.commits = 0
        self.rollbacks = 0
    def cursor(self):
        return FakeCursor(self)
    def transaction(self):
        from contextlib import nullcontext
        return nullcontext()
    def commit(self):
        self.commits += 1
    def rollback(self):
        self.rollbacks += 1


class BnfBulkTests(unittest.TestCase):
    def test_iso2709_decodes_bnf_fields_and_preserves_two_editions(self):
        payload = (make_record(notice="FRBNF001", volume="1") +
                   make_record(notice="FRBNF002", title="Dragon Ball, édition Deluxe",
                               volume="2", isbn="978-0-306-40615-7"))
        rows = list(importer.iter_iso2709(io.BytesIO(payload)))
        self.assertEqual(len(rows), 2)
        result = [importer.parse_candidate(item, "x" * 64, importer.datetime.now(importer.timezone.utc))
                  for item in rows]
        self.assertEqual([i["notice_id"] for i in result], ["FRBNF001", "FRBNF002"])
        self.assertEqual(result[0]["cataloguing_agency"], "FR-BnF")
        self.assertEqual(result[0]["volume_label"], "1")
        self.assertEqual(result[1]["volume_label"], "2")
        self.assertEqual(result[1]["isbn13"], result[0]["isbn13"])

    def test_non_manga_and_bad_isbn_do_not_create_confirmed_manga(self):
        original = make_record(subject="Histoire générale", series="Arts", isbn="9780000000000")
        self.assertIsNone(importer.parse_candidate(
            original, "x" * 64, importer.datetime.now(importer.timezone.utc)))
        manga = make_record(isbn="9780000000000")
        item = importer.parse_candidate(manga, "x" * 64, importer.datetime.now(importer.timezone.utc))
        self.assertEqual(item["isbn13"], [])
        self.assertIn("sujet:Mangas", item["match_evidence"])

    def test_isbn10_conversion_and_checksum(self):
        self.assertEqual(importer.isbn13("0-306-40615-2"), "9780306406157")
        self.assertIsNone(importer.isbn13("0-306-40615-0"))
        self.assertEqual(importer.isbn13("978-0-306-40615-7"), "9780306406157")
        self.assertIsNone(importer.isbn13("978-0-306-40615-8"))

    def test_read_plain_gzip_zip(self):
        record = make_record()
        with tempfile.TemporaryDirectory() as dir:
            root = Path(dir)
            (root / "sample.not").write_bytes(record)
            with gzip.open(root / "sample.not.gz", "wb") as out:
                out.write(record)
            with zipfile.ZipFile(root / "sample.zip", "w") as z:
                z.writestr("UNIMARC_UTF8/books.not", record)
            for name in ("sample.not", "sample.not.gz", "sample.zip"):
                self.assertEqual(list(importer.iter_file_records(root / name)), [record])

    def test_corrupt_stream_rejected(self):
        record = make_record()
        with self.assertRaisesRegex(ValueError, "incomplète"):
            list(importer.iter_iso2709(io.BytesIO(record[:-3])))

    def test_preview_does_not_open_database_or_write_anything(self):
        with tempfile.TemporaryDirectory() as dir:
            root = Path(dir)
            (root / "bnf.not").write_bytes(make_record())
            with patch.object(importer, "get_postgres_connection") as connect:
                self.assertEqual(importer.main(["--preview", "--input-dir", str(root)]), 0)
                connect.assert_not_called()

    def test_staging_idempotence_and_no_private_mutations(self):
        with tempfile.TemporaryDirectory() as dir:
            file = Path(dir) / "bnf.not"
            file.write_bytes(make_record())
            db = FakeDb()
            result = importer.ingest_one(file, database=db)
            self.assertEqual(result["status"], "IMPORTED")
            self.assertEqual((result["scanned"], result["candidates"]), (1, 1))
            self.assertEqual(db.rows[0]["notice_id"], "FRBNF99900001")
            self.assertTrue(all("user_manga_" not in s and
                                "INSERT INTO manga_fr_edition" not in s
                                for s in db.statements))
            skip = FakeDb(existing=("COMPLETED",))
            self.assertEqual(importer.ingest_one(file, database=skip)["status"], "ALREADY_IMPORTED")
            self.assertFalse(skip.rows)

    def test_bad_record_leaves_no_import_marker_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as dir:
            file = Path(dir) / "bad.not"
            file.write_bytes(make_record() + b"broken")
            db = FakeDb()
            with self.assertRaises(ValueError):
                importer.ingest_one(file, database=db)
            self.assertFalse(any("INSERT INTO bnf_bulk_batch" in s for s in db.statements))
            self.assertEqual(db.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
