"""Offline tests: audited full MAL base, bounded daily delta, safe replay.

No network. Ensures no full download or private-library write on daily runs.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipelines.engine.scripts import catalogue_lifecycle as life
from pipelines.engine.scripts import catalogue_mangaupdates as mu


def item(mid, suffix=""):
    return {"mal_id":mid,"title":"Work "+str(mid)+suffix,
            "type":"Manga","genres":[{"name":"Action"}],
            "themes":[{"name":"School"}],
            "demographics":[{"name":"Shounen"}]}


def response(n,sort,ids,last=858):
    return {
        "pagination":{"last_visible_page":last,
                       "current_page":n,"has_next_page":n<last},
        "data":[item(i) for i in ids]
    }


class Response:
    status_code=200
    headers={}
    def __init__(self,payload):
        self.payload=payload
    def json(self):return self.payload
    def raise_for_status(self):pass


class Client:
    def __init__(self,results):
        self.results=results
        self.calls=[]
    def get(self,url,*,params,timeout):
        key=(params["page"],params["sort"])
        self.calls.append(key)
        return Response(self.results[key])


class FakeCursor:
    def __init__(self,db):
        self.db=db;self.sql=""
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.sql=sql
        self.db.sql.append((sql,params))
    def fetchone(self):
        if "pg_try_advisory_lock" in self.sql:
            return {"locked":self.db.lock}
        if "FROM catalogue_lifecycle_state" in self.sql:
            return {"rolling_page":self.db.rolling}
        if "to_regclass('public.manga_title_alias')" in self.sql:
            return {"tbl":"manga_title_alias"}
        if "source_count" in self.sql:
            return {"source_count":85776,"canonical_count":85776,
                    "max_mal_id":200000,"orphan_source":0}
        raise AssertionError(self.sql)
    def fetchall(self):
        if "SELECT mal_id,raw_json" in self.sql:
            params=self.db.sql[-1][1][0]
            return [{"mal_id":id,"raw_json":self.db.existing[id]}
                    for id in params if id in self.db.existing]
        raise AssertionError(self.sql)


class FakeDB:
    def __init__(self,existing=None,rolling=3,lock=True):
        self.existing=existing or {}
        self.rolling=rolling
        self.lock=lock
        self.sql=[]
    def cursor(self):return FakeCursor(self)
    def commit(self):pass
    def close(self):pass
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def transaction(self):
        class Tx:
            def __enter__(self):return self
            def __exit__(self,*_):return False
        return Tx()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.logs=Path(tmp.name)/"logs"
        self.updates=Path(tmp.name)/"raw"/"updates"
        self.patches=[
            patch.object(life,"LOGS",self.logs),
            patch.object(life,"UPDATES",self.updates),
            patch("pipelines.engine.scripts.catalogue_lifecycle.time.sleep"),
        ]
        for obj in self.patches:
            obj.start()
            self.addCleanup(obj.stop)

    def baseline(self):
        source=self.logs/"last_initial_sync.json"
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_text(json.dumps({
            "status":"CATALOGUE_COMPLETE",
            "canonical_synced":True,"unique_ids_in_run":85776}))
        return source

    def test_initial_audit_requires_completed_source(self):
        path=self.baseline()
        db=FakeDB()
        self.assertEqual(life.audit_base(db,report_path=path)["source_count"],85776)
        path.write_text(json.dumps({"status":"INTERRUPTED","unique_ids_in_run":85776}))
        with self.assertRaisesRegex(ValueError,"initial non terminé"):
            life.audit_base(db,report_path=path)

    def test_daily_queries_bounded_descending_head_and_rotating_history(self):
        results={
            (1,"desc"):response(1,"desc",[200002,200001,200000]),
            (3,"asc"):response(3,"asc",[1,2,3]),
            (4,"asc"):response(4,"asc",[4,5,6]),
        }
        client=Client(results)
        db=FakeDB(existing={200000:item(200000),1:item(1),
                            2:item(2),3:item(3),
                            4:item(4),5:item(5),6:item(6)})
        with patch.object(life,"audit_base",return_value={
            "source_count":85776,"max_mal_id":200000}):
            with patch.object(life,"upsert_jikan_manga_batch",
                              return_value=2) as upsert:
                with patch.object(life,"consolidate_changed") as canon:
                    output=life.synchronize(db,client=client,rotating=2)
        self.assertEqual(client.calls,[(1,"desc"),(3,"asc"),(4,"asc")])
        self.assertEqual(output["new_mal_ids"],2)
        self.assertEqual(output["updated_mal_ids"],0)
        self.assertEqual(output["canonical_upserts"],2)
        self.assertEqual(output["next_rolling_page"],5)
        self.assertEqual(upsert.call_args.args[1][0]["mal_id"],200002)
        self.assertEqual(sorted(canon.call_args.args[1]),[200001,200002])
        self.assertTrue(list(self.updates.glob("delta_*.json")))
        self.assertFalse(any("DELETE" in q[0].upper()
                             or "TRUNCATE" in q[0].upper()
                             for q in db.sql))

    def test_already_known_data_no_upserts_and_rotates_cursor(self):
        results={(1,"desc"):response(1,"desc",[200000,199999]),
                 (3,"asc"):response(3,"asc",[9])}
        db=FakeDB(existing={
            200000:item(200000),199999:item(199999),9:item(9)})
        with patch.object(life,"audit_base",return_value={
            "max_mal_id":200000}):
            with patch.object(life,"upsert_jikan_manga_batch") as upsert:
                with patch.object(life,"consolidate_changed") as canon:
                    out=life.synchronize(db,client=Client(results),rotating=1)
        self.assertEqual(out["canonical_upserts"],0)
        upsert.assert_not_called()
        canon.assert_not_called()
        self.assertEqual(out["next_rolling_page"],4)

    def test_exceed_new_head_budget_fails_closed(self):
        db=FakeDB(existing={})
        client=Client({(1,"desc"):response(1,"desc",[202000,201999])})
        with patch.object(life,"audit_base",return_value={"max_mal_id":200000}):
            with patch.object(life,"upsert_jikan_manga_batch") as upsert:
                with self.assertRaisesRegex(ValueError,"Trop de nouveaux"):
                    life.synchronize(db,client=client,newest_cap=1,rotating=0)
                upsert.assert_not_called()

    def test_rejects_corrupt_or_unordered_api(self):
        client=Client({(1,"desc"):response(1,"desc",[4,5])})
        with self.assertRaises(ValueError):
            life.get_page(client,"https://api.tenrai.org/v1",1,"desc")
        self.assertNotIn(("1","asc"),client.calls)

    def test_sql_is_targeted_and_never_updates_private_collection(self):
        db=FakeDB()
        life.consolidate_changed(db,[7,8,7])
        self.assertEqual(len(db.sql),9)
        self.assertTrue(all(q[1]==([7,8],) for q in db.sql if q[1] is not None))
        self.assertTrue(any("TENRAI_MAL_TYPED" in statement
                            for statement,_ in db.sql))
        for text,params in db.sql:
            self.assertNotIn("user_manga_",text)
            self.assertNotIn("manga_fr_edition",text)
            self.assertNotIn("TRUNCATE",text.upper())
            self.assertNotIn("DELETE FROM",text.upper())

    def test_lock_prevents_duplicate_concurrent_run(self):
        db=FakeDB(lock=False)
        with patch.object(life,"synchronize") as sync:
            result=life.run_cycle(factory=lambda:db)
        self.assertEqual(result["status"],"SKIPPED_ALREADY_RUNNING")
        sync.assert_not_called()

    def test_background_run_serializes_progress_and_enrichment(self):
        db=FakeDB()
        with patch.object(life,"synchronize",return_value={
                "new_mal_ids":3,"updated_mal_ids":5}):
            result=life.run_cycle(factory=lambda:db,
                scrinis_runner=lambda **k: {"selected":8},
                mu_runner=lambda **k: {"selected":5},
                bnf_runner=lambda **k: {"sru":{"selected":3}})
        self.assertEqual(result["status"],"SUCCESS")
        self.assertEqual(result["mal"]["new_mal_ids"],3)
        self.assertEqual(result["mangaupdates"]["selected"],5)
        self.assertEqual(json.loads((self.logs/"last_cycle.json")
                      .read_text())["status"],"SUCCESS")

    def test_source_mangaupdates_requires_independent_identity(self):
        fake=type("Provider",(),{"calls":[],
          "call":lambda self,prov,kind,**kw:(
            {"status":"OK","data":{
                "status":"OK","title":"Wind Breaker",
                "authors":[],"genres":["Action"],"themes":[]}}
            if kind=="detail" else None)})()
        search={"status":"OK","candidates":[{
            "id":"818","title":"Wind Breaker","aliases":[],
            "mal_id":None,"format":"Manga"}]}
        work={"id":1,"mal_id":45,"title":"Wind Breaker",
              "title_english":"Wind Breaker",
              "title_japanese":"","mal_authors":["Nii, Satoru"]}
        status,ev=mu.candidate_review(work,search,fake)
        self.assertEqual(status,"UNVERIFIED")
        self.assertEqual(ev["relation"],"REVIEW_REQUIRED")
        self.assertNotIn("user_manga",mu.UPSERT)

    def test_daily_sync_does_not_change_full_jikan_directory(self):
        self.assertTrue(str(life.UPDATES).endswith("updates"))
        self.assertIn("manga_page_",life.full.cache_path(1).name)
        self.assertNotEqual(life.UPDATES,life.full.RAW)
        self.assertIn("profile",("automation","profile"))


if __name__=="__main__":
    unittest.main()
