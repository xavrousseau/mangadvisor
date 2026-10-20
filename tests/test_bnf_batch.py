"""BnF batch enrichment: evidence-only, bounded, safely resumable."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException

from apps.api.app.bnf_batch import (
    MAX_BATCH, REQUEST_DELAY, WORK_SQL, UPSERT_CANDIDATE,
    cli_main, create_bnf_catalog_router, normalize_candidates, run_batch,
)


def record(isbn="9782871294146", title="Naruto. Tome 1", **overrides):
    return {
        "isbn13": isbn, "title_fr": title, "status": "CANDIDATE_UNCONFIRMED",
        "manga_match_verified": False,
        "source_url": "https://catalogue.bnf.fr/ark:/12148/cb12345678x",
        "publisher_fr": "Kana", "author_fr": "Masashi Kishimoto",
        "edition_kind_suggested": "UNKNOWN", **overrides,
    }


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        self.db.executed.append((sql, params))
        if "LEFT JOIN manga_bnf_attempt" in sql:
            self.db.rows = self.db.works
        elif "SELECT id FROM manga WHERE" in sql:
            self.db.one = {"id": 7} if self.db.exists else None
        elif "FROM manga_bnf_attempt WHERE" in sql:
            self.db.one = {
                "status": "CHECKED",
                "checked_at": datetime(2026, 10, 20, tzinfo=timezone.utc),
                "candidate_count": 1,
            }
        elif "FROM manga_bnf_candidate c" in sql:
            self.db.rows = [{
                **record(),
                "title_clue": "TITLE_WORDS_PRESENT", "title_clue_rank": 2,
                "searched_title": "Naruto", "registration_status": "TO_VERIFY",
            }]

    def fetchall(self):
        return self.db.rows

    def fetchone(self):
        return self.db.one


class FakeTransaction:
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


class FakeConnection:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def cursor(self):
        return FakeCursor(self.db)
    def commit(self):
        pass
    def transaction(self):
        return FakeTransaction()


class FakeDb:
    def __init__(self, works=None, exists=True):
        self.works = works or []
        self.exists = exists
        self.rows = []
        self.one = None
        self.executed = []
    def __call__(self):
        return FakeConnection(self)


class BnfBatchTests(unittest.TestCase):
    def test_candidate_provenance_is_strict_and_no_title_proof(self):
        found = normalize_candidates(["Naruto"], [
            ("Naruto", {"items": [
                record(),
                record(isbn="9782871294146", title="Naruto. Tome 2"),
                record(isbn="9782344074282", title="Other manga",
                       source_url="https://example.org/ark:/12148/cb12345678x"),
                record(isbn="9782344074282", title="Other manga",
                       manga_match_verified=True),
                record(isbn="9781234567890", title="Bad ISBN"),
                record(isbn="9782344074282", title="Other manga"),
            ]}),
        ])
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["isbn13"], "9782871294146")
        self.assertEqual(found[0]["title_clue_rank"], 2)
        self.assertEqual(found[1]["isbn13"], "9782344074282")
        self.assertEqual(found[1]["title_clue_rank"], 0)
        self.assertEqual(found[1]["source_url"],
                         "https://catalogue.bnf.fr/ark:/12148/cb12345678x")
        self.assertNotIn("manga_match_verified", found[0])
        self.assertNotIn("volume_number", found[0])
        self.assertEqual(found[1]["edition_kind_suggested"], "UNKNOWN")

    def test_priority_is_user_collection_then_broader_catalog(self):
        self.assertIn("user_manga_inventory_declaration", WORK_SQL)
        self.assertIn("user_manga_library", WORK_SQL)
        self.assertIn("ORDER BY priority ASC, m.popularity ASC", WORK_SQL)
        self.assertIn("INTERVAL '45 days'", WORK_SQL)
        self.assertIn("INTERVAL '1 day'", WORK_SQL)
        self.assertIn("ON CONFLICT (manga_id, isbn13) DO UPDATE", UPSERT_CANDIDATE)
        self.assertNotIn("manga_fr_edition", UPSERT_CANDIDATE)

    def test_batch_persists_only_staging_and_checkpoint_per_manga(self):
        db = FakeDb([
            {"id": 2, "title": "Naruto", "title_english": "Naruto"},
            {"id": 3, "title": "Shingeki no Kyojin", "title_english": "Attack on Titan"},
        ])
        requested = []
        delays = []

        def search(title):
            requested.append(title)
            if title == "Shingeki no Kyojin":
                raise HTTPException(status_code=503, detail="BnF unavailable")
            return {"items": [record(
                isbn="9782871294146" if title == "Naruto" else "9782344074282",
                title="Naruto Tome 1" if title == "Naruto" else "Attack on Titan Tome 1",
            )]}

        stats = run_batch(db, limit=2, search=search, sleep=delays.append)
        self.assertEqual(stats["selected"], 2)
        self.assertEqual(stats["checked"], 1)
        self.assertEqual(stats["partial"], 1)
        self.assertEqual(stats["candidates"], 2)
        self.assertEqual(requested, ["Naruto", "Shingeki no Kyojin", "Attack on Titan"])
        self.assertEqual(delays, [REQUEST_DELAY, REQUEST_DELAY])
        writes = [sql for sql, _ in db.executed if sql.strip().startswith("INSERT")]
        self.assertEqual(sum("INSERT INTO manga_bnf_candidate" in s for s in writes), 2)
        self.assertEqual(sum("INSERT INTO manga_bnf_attempt" in s for s in writes), 2)
        self.assertTrue(all("INSERT INTO manga_bnf_" in s for s in writes))
        self.assertFalse(any("DELETE FROM" in s or "TRUNCATE" in s for s in writes))
        query = next(p for sql, p in db.executed if sql == WORK_SQL)
        self.assertEqual(query, {"limit": 2, "refresh": False})

    def test_network_outage_is_not_presented_as_successful_enrichment(self):
        db = FakeDb([{"id": 5, "title": "Monster", "title_english": None}])
        def unavailable(_):
            raise HTTPException(status_code=503, detail="offline")
        stats = run_batch(db, search=unavailable, sleep=lambda *_: None)
        self.assertEqual(stats["error"], 1)
        self.assertEqual(stats["candidates"], 0)
        self.assertFalse(any("INSERT INTO manga_bnf_candidate" in sql
                             for sql, _ in db.executed))

    def test_empty_or_unsafe_title_skips_http_and_tracks_it(self):
        db = FakeDb([{"id": 6, "title": 'Untrusted" CQL', "title_english": None}])
        searches = []
        stats = run_batch(db, search=lambda x: searches.append(x), sleep=lambda *_: None)
        self.assertEqual(searches, [])
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(stats["candidates"], 0)

    def test_limit_rejected_before_database_or_network(self):
        db = FakeDb()
        for value in (0, MAX_BATCH + 1, -1):
            with self.assertRaises(ValueError):
                run_batch(db, limit=value)
        self.assertEqual(db.executed, [])
        with self.assertRaises(SystemExit):
            cli_main(["--limit", "999"])

    def test_readonly_endpoint_marks_every_candidate_unverified(self):
        db = FakeDb(exists=True)
        router = create_bnf_catalog_router(db)
        endpoint = next(route.endpoint for route in router.routes
                        if route.path.endswith("/bnf-candidates"))
        found = endpoint(7)
        self.assertTrue(found["candidate_only"])
        self.assertFalse(found["manga_match_verified"])
        self.assertEqual(found["items"][0]["registration_status"], "TO_VERIFY")
        self.assertEqual(found["candidate_count"], 1)
        self.assertEqual(found["source"], "BNF_SRU")
        self.assertTrue(all(sql.strip().startswith("SELECT") for sql, _ in db.executed))
        invalid = FakeDb(exists=False)
        other = create_bnf_catalog_router(invalid)
        other_endpoint = next(route.endpoint for route in other.routes)
        with self.assertRaises(HTTPException) as err:
            other_endpoint(999)
        self.assertEqual(err.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
