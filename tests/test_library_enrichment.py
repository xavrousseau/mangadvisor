"""Linked-library enrichment: privacy, resumability, quotas and no broad catalog scans."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from apps.api.app.library_enrichment import (
    LINKED_SQL, PENDING_SQL, DEFAULT_WORKS, MAX_WORKS,
    run_library_enrichment, linked_library_scope, cli_main,
)
from apps.api.app import bnf_batch, wikidata_enrichment


class FakeCursor:
    def __init__(self, database):
        self.database=database
        self.rows=[]
        self.one=None

    def __enter__(self):return self
    def __exit__(self,*_):return False

    def execute(self,sql,params=None):
        self.database.queries.append((sql,params))
        if sql==LINKED_SQL:
            self.rows=[{"id":i} for i in self.database.linked_ids[:params["limit"]]]
        elif sql==PENDING_SQL:
            self.one={"count":self.database.pending}
        else:
            raise AssertionError("Unexpected DB query from orchestrator")

    def fetchall(self):return self.rows
    def fetchone(self):return self.one


class FakeConnection:
    def __init__(self,database):self.database=database
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return FakeCursor(self.database)


class FakeDb:
    def __init__(self,ids, pending=0):
        self.linked_ids=ids
        self.pending=pending
        self.queries=[]
    def __call__(self):return FakeConnection(self)


class LibraryEnrichmentTests(unittest.TestCase):
    def test_scope_is_only_this_users_existing_linked_mangas(self):
        db=FakeDb([9,5,15],pending=49)
        result=linked_library_scope(db,user_id=1,max_works=2)
        self.assertEqual(result,{"ids":[9,5],"truncated":True,"pending":49})
        self.assertEqual(db.queries[0][1],{"user_id":1,"limit":3})
        self.assertIn("user_manga_inventory_declaration",LINKED_SQL)
        self.assertIn("user_manga_library",LINKED_SQL)
        self.assertIn("d.user_id=%(user_id)s",LINKED_SQL)
        self.assertIn("l.user_id=%(user_id)s",LINKED_SQL)
        self.assertIn("user_manga_inventory_pending",PENDING_SQL)
        self.assertNotIn("manga_bnf_candidate",LINKED_SQL)
        self.assertTrue(all(q.lstrip().startswith("SELECT") for q,_ in db.queries))

    def test_no_collection_does_not_treat_pending_titles_as_matches(self):
        db=FakeDb([],pending=49)
        wikidata=Mock()
        bnf=Mock()
        summary=run_library_enrichment(db,wikidata_batch=wikidata,bnf_batch=bnf)
        self.assertEqual(summary["linked_works"],0)
        self.assertEqual(summary["pending_inventory"],49)
        self.assertEqual(summary["sources"],{})
        wikidata.assert_not_called()
        bnf.assert_not_called()

    def test_one_call_processes_multiple_bounded_provider_batches(self):
        db=FakeDb(list(range(1,54)),pending=49)
        wikidata_calls=[]
        bnf_calls=[]
        def wikidata(_factory, **kw):
            wikidata_calls.append(kw)
            selected=[15,15,15,8,0][len(wikidata_calls)-1]
            return {"selected":selected,"matched":selected-1 if selected else 0,
                    "not_found":int(bool(selected)), "error":0}
        def bnf(_factory,**kw):
            bnf_calls.append(kw)
            selected=[10,10,10,10,10,3,0][len(bnf_calls)-1]
            return {"selected":selected,"candidates":selected*2,
                    "checked":selected, "error":0}
        delays=[]
        result=run_library_enrichment(
            db,max_works=80,wikidata_batch=wikidata,bnf_batch=bnf,
            sleep=delays.append,
        )
        self.assertEqual(result["linked_works"],53)
        self.assertEqual(result["pending_inventory"],49)
        self.assertFalse(result["scope_limited"])
        self.assertEqual(result["sources"]["wikidata"]["selected"],53)
        self.assertEqual(result["sources"]["wikidata"]["matched"],49)
        self.assertEqual(result["sources"]["bnf"]["selected"],53)
        self.assertEqual(result["sources"]["bnf"]["candidates"],106)
        self.assertEqual(len(wikidata_calls),5)
        self.assertEqual(len(bnf_calls),7)
        for kw in wikidata_calls:
            self.assertEqual(kw["target_ids"],list(range(1,54)))
            self.assertEqual(kw["limit"],15)
            self.assertFalse(kw["refresh"])
        for kw in bnf_calls:
            self.assertEqual(kw["limit"],10)
            self.assertEqual(kw["target_ids"],list(range(1,54)))
        self.assertEqual(len(delays),(5-1)+(7-1))
        self.assertEqual(result["failed_sources"],[])

    def test_total_remote_failure_is_not_retried_repeatedly(self):
        db=FakeDb([11,12,13],pending=0)
        wiki=Mock(return_value={"selected":3,"error":3})
        bnf=Mock(return_value={"selected":0,"error":0})
        result=run_library_enrichment(
            db,wikidata_batch=wiki,bnf_batch=bnf,sleep=lambda *_:None
        )
        self.assertEqual(wiki.call_count,1)
        self.assertEqual(result["failed_sources"],["wikidata"])
        self.assertEqual(result["sources"]["wikidata"]["halted"],1)
        self.assertEqual(bnf.call_count,1)

    def test_bounds_and_no_accidental_unscoped_fallback(self):
        db=FakeDb([1,2])
        for value in [0,-1,MAX_WORKS+1,False,"80"]:
            with self.subTest(value=value),self.assertRaises(ValueError):
                linked_library_scope(db,max_works=value)
        for value in [0,-2,True]:
            with self.subTest(user=value),self.assertRaises(ValueError):
                linked_library_scope(db,user_id=value)
        self.assertEqual(db.queries,[])

    def test_source_batches_include_target_id_filter_and_reject_bad_ids(self):
        for module in (wikidata_enrichment,bnf_batch):
            old=module.WORK_SQL
            self.assertIn("ORDER BY priority ASC",old)
            with self.subTest(module=module.__name__):
                class Stub:
                    def __call__(self):
                        raise AssertionError("No DB access for invalid scope")
                with self.assertRaises(ValueError):
                    module.run_batch(Stub(),target_ids=[-1])
                with self.assertRaises(ValueError):
                    module.run_batch(Stub(),target_ids=[1]*251)
        import inspect
        for module in (wikidata_enrichment,bnf_batch):
            source=inspect.getsource(module.run_batch)
            self.assertIn("m.id=ANY(%(target_ids)s)",source)
            self.assertIn('params["target_ids"] = target_ids',source)

    def test_cli_rejects_out_of_range_before_network(self):
        for value in ["0","251"]:
            with self.assertRaises(SystemExit):
                cli_main(["--max-works",value])


if __name__=="__main__":
    unittest.main()
