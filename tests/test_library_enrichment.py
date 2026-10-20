"""Linked-library enrichment: privacy, resumability, quotas and no broad catalog scans."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from apps.api.app.library_enrichment import (
    LINKED_SQL, PENDING_SQL, COVERAGE_SQL, DEFAULT_WORKS, MAX_WORKS,
    run_library_enrichment, linked_library_scope, enrichment_coverage, cli_main,
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
        elif sql==COVERAGE_SQL:
            ids=params["target_ids"]
            eligible=len(ids)
            self.one=self.database.coverage or {
                "in_scope":eligible,"without_mal_id":0,"unsupported_type":0,
                "wikidata_eligible":eligible,"wikidata_cached":0,
                "wikidata_due":eligible,"bnf_eligible":eligible,
                "bnf_cached":0,"bnf_due":eligible,
            }
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
    def __init__(self,ids, pending=0, coverage=None):
        self.linked_ids=ids
        self.pending=pending
        self.coverage=coverage
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

    def test_when_everything_is_cached_no_source_is_called(self):
        db=FakeDb([9, 11, 15], pending=49, coverage={
            "in_scope":3, "without_mal_id":0, "unsupported_type":0,
            "wikidata_eligible":3, "wikidata_cached":3, "wikidata_due":0,
            "bnf_eligible":3, "bnf_cached":3, "bnf_due":0,
        })
        wiki=Mock()
        bnf=Mock()
        report=run_library_enrichment(
            db,wikidata_batch=wiki,bnf_batch=bnf,sleep=lambda _:None,
        )
        self.assertEqual(report["coverage"]["wikidata_cached"],3)
        self.assertEqual(report["sources"]["wikidata"]["selected"],0)
        self.assertEqual(report["sources"]["bnf"]["selected"],0)
        self.assertEqual(report["sources"]["bnf"]["cached"],3)
        self.assertEqual(report["failed_sources"],[])
        wiki.assert_not_called()
        bnf.assert_not_called()

    def test_when_all_wikidata_ids_are_missing_bnf_can_still_run(self):
        db=FakeDb([9, 11],coverage={
            "in_scope":2,"without_mal_id":2,"unsupported_type":0,
            "wikidata_eligible":0,"wikidata_cached":0,"wikidata_due":0,
            "bnf_eligible":2,"bnf_cached":0,"bnf_due":2,
        })
        wiki=Mock()
        bnf=Mock(side_effect=[
            {"selected":2,"checked":2,"error":0},
            {"selected":0,"checked":0,"error":0},
        ])
        report=run_library_enrichment(
            db,wikidata_batch=wiki,bnf_batch=bnf,sleep=lambda _:None
        )
        wiki.assert_not_called()
        self.assertEqual(bnf.call_count,2)
        self.assertEqual(report["sources"]["bnf"]["selected"],2)
        self.assertEqual(report["coverage"]["without_mal_id"],2)

    def test_zero_selected_despite_due_items_is_flagged(self):
        db=FakeDb([9,11])
        wiki=Mock(return_value={"selected":0,"matched":0,"error":0})
        report=run_library_enrichment(
            db,wikidata_batch=wiki,include_bnf=False,sleep=lambda _:None
        )
        self.assertEqual(report["failed_sources"],["wikidata"])
        self.assertEqual(report["sources"]["wikidata"]["due_before"],2)
        self.assertEqual(report["sources"]["wikidata"]["halted"],1)
        self.assertNotIn("bnf",report["sources"])

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

    def test_coverage_is_read_only_and_bound_to_scope(self):
        db=FakeDb([1,2])
        coverage=enrichment_coverage(db,[1,2])
        self.assertEqual(coverage["in_scope"],2)
        self.assertEqual(len(db.queries),1)
        self.assertEqual(db.queries[0][0],COVERAGE_SQL)
        self.assertEqual(db.queries[0][1],{"target_ids":[1,2]})
        self.assertTrue(all(sql.strip().startswith("SELECT") for sql,_ in db.queries))
        with self.assertRaises(ValueError):
            enrichment_coverage(db,[-1])
        with self.assertRaises(ValueError):
            enrichment_coverage(db,list(range(1,252)))

    def test_cli_rejects_out_of_range_before_network(self):
        for value in ["0","251"]:
            with self.assertRaises(SystemExit):
                cli_main(["--max-works",value])


if __name__=="__main__":
    unittest.main()
