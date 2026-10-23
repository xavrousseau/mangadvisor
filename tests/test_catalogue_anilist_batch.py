"""Data-integrity tests for resumable cross-source catalogue enrichment."""
from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from apps.api.app import catalogue_anilist_batch as batch


class FakeCursor:
    def __init__(self, queries, rows=None):
        self.queries=queries
        self.rows=rows or []
    def __enter__(self): return self
    def __exit__(self,*args):return False
    def execute(self, query, params=None):
        self.queries.append((query,params))
    def fetchall(self): return self.rows
    def fetchone(self):return {"locked":True}


class FakeDB:
    def __init__(self):
        self.queries=[]
        self.commits=0
        self.rollbacks=0
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def cursor(self):return FakeCursor(self.queries)
    def commit(self):self.commits+=1
    def rollback(self):self.rollbacks+=1


class BatchTests(unittest.TestCase):
    def test_match_can_only_join_an_identical_mal_id(self):
        db=FakeDB()
        source={"status":"CROSS_ID_CANDIDATES","items":[
            {"source_mal_id":145863,"anilist_id":34567,
             "source_url":"https://anilist.co/manga/34567",
             "titles":[{"language":"english","title":"Goodbye, Eri"}],
             "relations":[]},
            {"source_mal_id":999999,"anilist_id":55,
             "source_url":"https://anilist.co/manga/55",
             "titles":[],"relations":[]},
        ]}
        works=[{"work_id":10,"mal_id":145863},{"work_id":11,"mal_id":20}]
        with patch.object(batch,"stage_external_facts",
                          return_value={"status":"STAGED_SOURCE_CLAIMS"}) as stage:
            result=batch.run_batch(db,works,lookup=lambda _:source)
        self.assertEqual(result["matched"],1)
        stage.assert_called_once()
        self.assertEqual(stage.call_args.args[1],145863)
        attempts=[p for q,p in db.queries if "INSERT INTO catalogue_provider_attempt" in q]
        self.assertEqual([a["status"] for a in attempts],
                         ["MATCHED","NOT_RETURNED"])
        self.assertEqual([a["external_id"] for a in attempts],["34567",None])
        self.assertFalse(any("user_manga" in q for q,p in db.queries))

    def test_api_error_does_not_create_false_negative(self):
        db=FakeDB()
        rows=[{"work_id":10,"mal_id":145863}]
        with self.assertRaises(ValueError):
            batch.run_batch(db,rows,lookup=lambda _:
                            {"status":"PROVIDER_UNAVAILABLE","items":[]})
        self.assertEqual(db.queries,[])
        batch.record_provider_outage(db,rows)
        self.assertEqual(db.queries[0][1]["status"],"PROVIDER_ERROR")
        self.assertIn("interval '1 hour'",batch.SAVE_ATTEMPT_SQL)
        self.assertIn("next_retry_at<=now()",batch.NEXT_BATCH_SQL)

    def test_duplicate_mal_claim_must_fail_closed(self):
        db=FakeDB()
        repeated=[{"source_mal_id":145863,"anilist_id":123,
                   "source_url":"https://anilist.co/manga/123"},
                  {"source_mal_id":145863,"anilist_id":124,
                   "source_url":"https://anilist.co/manga/124"}]
        with self.assertRaises(ValueError):
            batch.run_batch(db,[{"work_id":10,"mal_id":145863}],
                            lookup=lambda _:{"status":"CROSS_ID_CANDIDATES",
                                             "items":repeated})
        self.assertEqual(db.queries,[])

    def test_ratelimit_never_exceeds_degraded_provider_quota(self):
        self.assertGreaterEqual(batch.DELAY,2.2)
        self.assertEqual(batch.BATCH_SIZE,8)
        self.assertLessEqual(batch.MAX_LIMIT,200)
        self.assertIn("idMal_in",__import__(
            "apps.api.app.international_crosswalk",fromlist=["ANILIST_MAL_QUERY"]
        ).ANILIST_MAL_QUERY)

    def test_resume_commits_each_batch_and_report_only_never_calls_provider(self):
        db=FakeDB()
        with (patch.object(batch,"connect_database",return_value=db),
              patch.object(batch,"ensure_schema") as ensure,
              patch.object(batch,"select_batch",side_effect=[
                  [{"work_id":10,"mal_id":145863}],
                  [],
              ]) as select,
              patch.object(batch,"run_batch",return_value={
                  "requested":1,"matched":1,"network_requests":1,
              }) as network,
              patch.object(batch,"summarize",return_value={
                  "eligible_works":85776,"matched":1,"not_returned":0,
                  "provider_errors":0,
              }),
              contextlib.redirect_stdout(io.StringIO()) as output):
            result=batch.main(["--run","--limit","2"],sleep=lambda _:None)
        self.assertEqual(result,0)
        self.assertEqual(db.commits,3)  # schema, one atomic batch, unlock
        self.assertIn('"matched_this_run": 1',output.getvalue())
        self.assertEqual(select.call_count,2)
        network.assert_called_once()
        ensure.assert_called_once()

    def test_menu_uses_existing_production_api_image_and_is_57_safe(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        command=(root/"cmd/enrich-catalogue-anilist.ps1").read_text(encoding="utf-8")
        menu=(root/"mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertIn("catalogue_anilist_batch --run --limit 64",command)
        self.assertIn('if "%CHOICE%"=="27" set "KEY=catalogue-anilist"',menu)
        self.assertIn("27 - Enrichir la base publique",menu)
        self.assertNotIn("pipelines.engine",command)
        self.assertFalse(any(ord(c)>127 for c in command))

if __name__=="__main__":
    unittest.main()
