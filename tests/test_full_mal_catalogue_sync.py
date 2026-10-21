"""Offline regression checks for the complete MAL catalogue sync."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipelines.engine.scripts import sync_full_mal_catalogue as sync


def manga(mal_id):
    return {
        "mal_id": mal_id,
        "title": "Manga " + str(mal_id),
        "title_english": None,
        "title_japanese": "日本語",
        "type": "Manga",
        "genres": [{"mal_id": 1, "name": "Action"}],
        "authors": [{"mal_id": 7, "name": "Creator"}],
        "themes": [], "demographics": [], "serializations": [],
        "published": {"from": None, "to": None},
    }


def page(page_num, *, last=2, ids=None, total=4):
    ids = ids or ([1, 2] if page_num == 1 else [3, 4])
    return {"pagination": {
        "current_page": page_num,
        "last_visible_page": last,
        "has_next_page": page_num < last,
        "items": {"total": total, "count": len(ids), "per_page": 100},
    }, "data": [manga(i) for i in ids]}


class Response:
    status_code = 200
    headers = {}
    def __init__(self, value, status=200, headers=None):
        self.value = value
        self.status_code = status
        self.headers = headers or {}
    def json(self): return self.value
    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


class Session:
    def __init__(self, pages=None):
        self.pages = pages or {1: page(1), 2: page(2)}
        self.calls = []
    def get(self, url, *, params, timeout):
        self.calls.append((url, dict(params)))
        return Response(self.pages[params["page"]])


class DB:
    def __init__(self, *, missing=0, source=4, canonical=4):
        self.closed = False
        self.missing, self.source, self.canonical = missing, source, canonical
        self.statement = ""
    def close(self): self.closed = True
    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql):
        assert sql.lstrip().upper().startswith("SELECT")
        self.statement = sql
    def fetchone(self):
        if "LEFT JOIN" in self.statement:
            return {"n": self.missing}
        return {"source_count": self.source, "canonical_count": self.canonical,
                "genre_links": 2, "theme_links": 0}


class FullCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.raw = Path(self.dir.name) / "raw"
        self.logs = Path(self.dir.name) / "logs"
        self.p1 = patch.object(sync, "RAW", self.raw)
        self.p2 = patch.object(sync, "LOGS", self.logs)
        self.p3 = patch("pipelines.engine.scripts.sync_full_mal_catalogue.time.sleep")
        self.p4 = patch.dict("os.environ", {"MANGA_API_BASE_URL": "https://api.tenrai.org/v1"})
        self.p5 = patch.object(sync, "PREVIOUS_RAW", self.raw / "complete_tenrai")
        for p in (self.p1, self.p2, self.p3, self.p4, self.p5):
            p.start()
            self.addCleanup(p.stop)

    def test_source_unfiltered_includes_every_manga_medium(self):
        self.assertEqual(sync.query(1), {
            "page": 1, "limit": 100, "order_by": "mal_id", "sort": "asc"})
        self.assertNotIn("sfw", sync.query(1))
        self.assertNotIn("type", sync.query(1))
        self.assertNotIn("q", sync.query(1))
        self.assertNotIn("genres", sync.query(1))

    def test_historical_jikan_paths_and_legacy_loader_discovery(self):
        from pipelines.engine.scripts.load_jikan_to_postgres import iter_jikan_json_files
        sync.persist(1, sync.DEFAULT_BASE, page(1))
        sync.persist(2, sync.DEFAULT_BASE, page(2))
        self.assertEqual(sync.cache_path(1), self.raw / "manga_page_1.json")
        self.assertEqual(sync.cache_path(2), self.raw / "manga_page_2.json")
        self.assertEqual([p.name for p in iter_jikan_json_files(self.raw, ["legacy"])],
                         ["manga_page_1.json", "manga_page_2.json"])

    def test_offline_migration_preserves_older_jikan_pages(self):
        # PR #81 put the pages in complete_tenrai/manga_page_00001.json.
        sync.PREVIOUS_RAW.mkdir(parents=True)
        p1 = page(1)
        previous = {**p1, "mangadvisor_source": "tenrai",
                    "mangadvisor_api_base": sync.DEFAULT_BASE,
                    "mangadvisor_query": sync.query(1)}
        sync.previous_cache_path(1).write_text(json.dumps(previous), encoding="utf-8")
        sync.cache_path(1).parent.mkdir(parents=True, exist_ok=True)
        old_jikan = {"data": [manga(999)], "mangadvisor_source": "jikan"}
        sync.cache_path(1).write_text(json.dumps(old_jikan), encoding="utf-8")
        sync.previous_cache_path(2).write_text(json.dumps({
            **page(2), "mangadvisor_source": "tenrai",
            "mangadvisor_api_base": sync.DEFAULT_BASE,
            "mangadvisor_query": sync.query(2)}, ensure_ascii=False), encoding="utf-8")
        with patch.object(sync, "get_postgres_connection",
                          side_effect=AssertionError("SQL should never open")), \
             patch.object(sync.requests, "Session",
                          side_effect=AssertionError("HTTP forbidden")):
            info = sync.repair_layout()
        self.assertEqual(info["moved"], 2)
        self.assertEqual(info["archived_old_root_files"], 1)
        self.assertEqual(info["valid_root_pages"], 2)
        self.assertEqual(info["remaining_legacy_pages"], 0)
        saved = (self.raw / "legacy_archive_before_complete_sync" / "manga_page_1.json")
        self.assertEqual(json.loads(saved.read_text()), old_jikan)
        self.assertEqual(sync.load_cache(1, sync.DEFAULT_BASE)["data"][0]["mal_id"], 1)
        self.assertEqual(sync.load_cache(2, sync.DEFAULT_BASE)["data"][0]["mal_id"], 3)
        self.assertEqual(sync.repair_layout()["moved"], 0)

    def test_invalid_old_cache_not_imported_and_existing_new_cache_not_overwritten(self):
        sync.PREVIOUS_RAW.mkdir(parents=True)
        sync.previous_cache_path(1).write_text("invalid", encoding="utf-8")
        sync.persist(2, sync.DEFAULT_BASE, page(2))
        previous = {**page(2), "mangadvisor_source": "tenrai",
                    "mangadvisor_api_base": sync.DEFAULT_BASE,
                    "mangadvisor_query": sync.query(2)}
        sync.previous_cache_path(2).write_text(json.dumps(previous), encoding="utf-8")
        info = sync.repair_layout()
        self.assertEqual(info["invalid_previous_pages"], 1)
        self.assertEqual(info["already_in_place"], 1)
        self.assertEqual(info["moved"], 0)
        self.assertEqual(info["valid_root_pages"], 1)
        self.assertTrue(sync.previous_cache_path(2).exists())
        self.assertIsNone(sync.load_cache(1, sync.DEFAULT_BASE))

    def test_cli_layout_repair_and_status_never_touch_network_or_sql(self):
        sync.PREVIOUS_RAW.mkdir(parents=True)
        sync.previous_cache_path(1).write_text(json.dumps({
            **page(1), "mangadvisor_source": "tenrai",
            "mangadvisor_api_base": sync.DEFAULT_BASE,
            "mangadvisor_query": sync.query(1)}))
        with patch.object(sync, "get_postgres_connection",
                          side_effect=AssertionError("SQL forbidden")), \
             patch.object(sync.requests, "Session",
                          side_effect=AssertionError("Network forbidden")):
            self.assertEqual(sync.main(["--repair-layout"]), 0)
            self.assertEqual(sync.main(["--status"]), 0)
        self.assertTrue(sync.cache_path(1).exists())

    def test_plan_is_read_only_and_uses_real_last_page(self):
        client = Session()
        result = sync.run(plan=True, session=client,
                          connection_factory=lambda: self.fail("DB should not open"))
        self.assertEqual(result["source_pages_reported"], 2)
        self.assertEqual(result["source_total_reported"], 4)
        self.assertEqual(result["status"], "PLAN")
        self.assertFalse(self.raw.exists())
        self.assertFalse(self.logs.exists())
        self.assertEqual(len(client.calls), 1)

    def test_complete_run_loads_source_in_batches_but_not_canonical(self):
        client = Session()
        db = DB()
        saved = []
        def upsert(conn, rows):
            self.assertIs(conn, db)
            self.assertTrue(all(r["source_name"] == "tenrai" for r in rows))
            self.assertTrue(all(isinstance(r["mal_id"], int) for r in rows))
            saved.extend(rows)
            return len(rows)
        with patch.object(sync, "upsert_jikan_manga_batch", side_effect=upsert):
            report = sync.run(session=client, batch_pages=1,
                              connection_factory=lambda: db)
        self.assertTrue(report["complete"])
        self.assertFalse(report["canonical_synced"])
        self.assertEqual(report["status"], "SOURCE_COMPLETE_PENDING_CANONICAL_SQL")
        self.assertEqual(report["unique_ids_in_run"], 4)
        self.assertEqual(report["db_upserts"], 4)
        self.assertEqual(len(saved), 4)
        self.assertTrue(db.closed)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(json.loads((self.logs / "last_sync.json").read_text())["complete"], True)
        self.assertEqual(sync.load_cache(2, sync.DEFAULT_BASE)["data"][0]["mal_id"], 3)

    def test_resume_uses_cached_later_pages(self):
        base = sync.DEFAULT_BASE
        sync.persist(2, base, page(2))
        client = Session()
        db = DB()
        with patch.object(sync, "upsert_jikan_manga_batch", side_effect=lambda db, rows: len(rows)):
            result = sync.run(session=client, connection_factory=lambda: db)
        self.assertEqual(result["pages_cached"], 1)
        self.assertEqual(result["pages_fetched"], 1)
        self.assertEqual([args[1]["page"] for args in client.calls], [1])

    def test_stale_or_malformed_cache_is_never_mixed_with_current_source(self):
        sync.persist(2, "https://different.example/v1", page(2))
        self.assertIsNone(sync.load_cache(2, sync.DEFAULT_BASE))
        sync.cache_path(2).write_text("{not valid json", encoding="utf-8")
        self.assertIsNone(sync.load_cache(2, sync.DEFAULT_BASE))
        bad = page(2, ids=[1, 4])
        sync.persist(2, sync.DEFAULT_BASE, bad)
        client = Session()
        db = DB()
        with patch.object(sync, "upsert_jikan_manga_batch", side_effect=lambda db, rows: len(rows)):
            with self.assertRaisesRegex(sync.CatalogueError, "dupliqué entre pages"):
                sync.run(session=client, connection_factory=lambda: db)
        self.assertEqual(json.loads((self.logs / "last_sync.json").read_text())["status"],
                         "INTERRUPTED")

    def test_provider_total_discrepancy_never_claims_complete(self):
        client = Session({1: page(1, total=12), 2: page(2, total=12)})
        with patch.object(sync, "upsert_jikan_manga_batch", side_effect=lambda db, rows: len(rows)):
            with self.assertRaisesRegex(sync.CatalogueError, "annonce 12"):
                sync.run(session=client, connection_factory=DB)
        self.assertEqual(json.loads((self.logs / "last_sync.json").read_text())["status"],
                         "INCOMPLETE_TOTAL_MISMATCH")

    def test_capped_run_never_finalizes_source(self):
        with patch.object(sync, "upsert_jikan_manga_batch", side_effect=lambda db, rows: len(rows)):
            with self.assertRaisesRegex(sync.CatalogueError, "plafond 1"):
                sync.run(session=Session(), max_pages=1, connection_factory=DB)
        self.assertEqual(json.loads((self.logs / "last_sync.json").read_text())["status"],
                         "INCOMPLETE_PAGE_CAP")

    def test_invalid_ambiguous_or_missing_pagination_fails_closed(self):
        for val in ({"data": [manga(1)]}, page(1, ids=[2, 1]), page(1, ids=[1, 1]),
                    {"data": [], "pagination": {"last_visible_page": 1,
                                                "has_next_page": False}}):
            with self.subTest(value=val):
                with self.assertRaises(sync.CatalogueError):
                    sync.pagination(val, 1)

    def test_final_audit_only_after_sql_coverage(self):
        sync.LOGS.mkdir(parents=True)
        sync.write_status({"complete": True,
                           "status": "SOURCE_COMPLETE_PENDING_CANONICAL_SQL",
                           "unique_ids_in_run": 4})
        with patch.object(sync, "get_postgres_connection", return_value=DB()):
            result = sync.finalize()
        self.assertEqual(result["status"], "CATALOGUE_COMPLETE")
        self.assertTrue(result["canonical_synced"])
        self.assertEqual(result["db_counts"]["canonical_count"], 4)
        sync.write_status({"complete": True,
                           "status": "SOURCE_COMPLETE_PENDING_CANONICAL_SQL",
                           "unique_ids_in_run": 4})
        with patch.object(sync, "get_postgres_connection", return_value=DB(missing=1)):
            with self.assertRaises(sync.CatalogueError):
                sync.finalize()
        self.assertFalse(json.loads((self.logs/"last_sync.json").read_text()).get("canonical_synced", False))

    def test_public_jikan_endpoint_is_explicitly_rejected(self):
        with patch.dict("os.environ", {"MANGA_API_BASE_URL": "https://api.jikan.moe/v4"}):
            with self.assertRaisesRegex(sync.CatalogueError, "fermé"):
                sync.base_url()


if __name__ == "__main__":
    unittest.main()
