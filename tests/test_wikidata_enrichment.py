"""Wikidata P4087: safe exact-ID matches, CC0 staging and bounded service access."""
from __future__ import annotations
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from fastapi import HTTPException

from apps.api.app.wikidata_enrichment import (
    WikidataLookupError, WORK_SQL, SOURCE, UPSERT_ATTEMPT_SQL, UPSERT_FACT_SQL,
    MAX_BATCH, cli_main, create_wikidata_router,
    fetch_wikidata, normalize_wikidata, run_batch, sparql_for_ids,
)


def binding(mid, qid, label=None, desc=None, genre=None):
    data={
        "malId":{"type":"literal", "value":str(mid)},
        "item":{"type":"uri", "value":"http://www.wikidata.org/entity/"+qid},
    }
    for name, value in [
        ("labelFr",label),("descriptionFr",desc),("genreFr",genre)
    ]:
        if value is not None:
            data[name]={"type":"literal","value":value,"xml:lang":"fr"}
    return data


def response(*rows):
    return {"head":{"vars":["malId","item","labelFr","descriptionFr","genreFr"]},
            "results":{"bindings":list(rows)}}


class FakeDb:
    def __init__(self, works=None, exists=True):
        self.works=works or []
        self.exists=exists
        self.executed=[]
        self.current=[]
        self.one=None
    def __call__(self):return FakeConn(self)


class FakeCursor:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.db.executed.append((sql,params))
        if "LEFT JOIN manga_wikidata_attempt a" in sql:
            self.db.current=self.db.works
        elif "SELECT id FROM manga WHERE id" in sql:
            self.db.one={"id":12} if self.db.exists else None
        elif "FROM manga_wikidata_attempt a" in sql and "JOIN manga m" in sql:
            self.db.one={
                "status":"MATCHED",
                "checked_at":datetime(2026,10,20,tzinfo=timezone.utc),
                "wikidata_id":"Q12345",
                "label_fr":"L'Attaque des Titans",
                "description_fr":"manga japonais",
                "genres_fr":["mystère"],
                "source_name":SOURCE,
            }
    def fetchall(self):return self.db.current
    def fetchone(self):return self.db.one


class FakeTransaction:
    def __enter__(self):return self
    def __exit__(self,*_):return False


class FakeConn:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return FakeCursor(self.db)
    def commit(self):pass
    def transaction(self):return FakeTransaction()


class WikidataEnrichmentTests(unittest.TestCase):
    def test_sparql_queries_only_manga_id_and_validated_literals(self):
        q=sparql_for_ids([13, 1, 13])
        self.assertIn('VALUES ?malId { "1" "13" }',q)
        self.assertIn("wdt:P4087",q)
        self.assertIn("skos:altLabel",q)
        self.assertIn('LANG(?altTitle) IN ("fr", "en", "ja")',q)
        self.assertIn('LANG(?labelFr)="fr"',q)
        self.assertNotIn("wdt:P4086",q)
        for values in ([],[0],[-2],[1234567890],["1"],[1]*16):
            with self.subTest(values=values),self.assertRaises(ValueError):
                sparql_for_ids(values)

    def test_exact_id_ambiguous_and_malicious_binding_rejected(self):
        parsed=normalize_wikidata([13, 111, 42],response(
            binding(13,"Q12345","L'Attaque des Titans","manga japonais","mystère"),
            binding(13,"Q12345","L'Attaque des Titans",genre="action"),
            binding(111,"Q4444","Autre nom"),
            binding(111,"Q5555","Autre nom"),
            binding(42,"Q0000","malformed"),
            binding(43,"Q8","OUTSIDE REQUEST"),
        ))
        one=parsed[13]
        self.assertEqual(one["status"],"MATCHED")
        self.assertEqual(one["fact"]["label_fr"],"L'Attaque des Titans")
        self.assertEqual(one["fact"]["genres_fr"],["action","mystère"])
        self.assertEqual(one["fact"]["description_fr"],"manga japonais")
        self.assertEqual(parsed[111]["status"],"AMBIGUOUS")
        self.assertIsNone(parsed[111]["fact"])
        self.assertEqual(parsed[42]["status"],"NOT_FOUND")

    def test_multilingual_aliases_are_accepted_only_with_explicit_language(self):
        item=binding(74,"Q12345","L'Attaque des Titans")
        item["altTitle"]={"type":"literal","value":"Attack on Titan","xml:lang":"en"}
        evil=binding(74,"Q12345")
        evil["altTitle"]={"type":"literal","value":"Fake name","xml:lang":"xx"}
        altjp=binding(74,"Q12345")
        altjp["altTitle"]={"type":"literal","value":"進撃の巨人","xml:lang":"ja"}
        record=normalize_wikidata([74],response(item,evil,altjp))[74]
        self.assertEqual(record["status"],"MATCHED")
        self.assertIn({"lang":"en","title":"Attack on Titan"},record["fact"]["alternate_titles"])
        self.assertIn({"lang":"ja","title":"進撃の巨人"},record["fact"]["alternate_titles"])
        self.assertFalse(any(t["title"]=="Fake name" for t in record["fact"]["alternate_titles"]))

    def test_invalid_or_truncated_provider_json_aborts_batch(self):
        for data in ({},{"results":{"bindings":"wrong"}},
                     {"results":{"bindings":[{}]*500}}):
            with self.subTest(data=str(data)[:40]),self.assertRaises(WikidataLookupError):
                normalize_wikidata([13],data)

    def test_http_is_single_bounded_identified_wikimedia_request(self):
        calls=[]
        raw=json.dumps(response(binding(13,"Q12345","French label"))).encode()
        class Response:
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self,limit):
                self.limit=limit
                return raw
        def fake_open(request,timeout):
            calls.append((request,timeout))
            return Response()
        with patch("apps.api.app.wikidata_enrichment.urllib.request.urlopen",
                   side_effect=fake_open):
            parsed=fetch_wikidata([13])
        self.assertEqual(parsed["results"]["bindings"][0]["labelFr"]["value"],
                         "French label")
        self.assertEqual(len(calls),1)
        req,timeout=calls[0]
        self.assertEqual(timeout,25)
        self.assertEqual(urlsplit(req.full_url).hostname,"query.wikidata.org")
        self.assertIn("github.com/xavrousseau/mangadvisor",req.get_header("User-agent").lower())
        sparql=parse_qs(urlsplit(req.full_url).query)["query"][0]
        self.assertIn("wdt:P4087",sparql)

    def test_outage_does_not_retry_and_persists_error_only(self):
        from urllib.error import HTTPError
        def blocked(*_args,**_kwargs):
            raise HTTPError("https://query.wikidata.org/sparql",429,"Too Many Requests",{},None)
        with patch("apps.api.app.wikidata_enrichment.urllib.request.urlopen",
                   side_effect=blocked) as call:
            with self.assertRaises(WikidataLookupError):
                fetch_wikidata([13])
        self.assertEqual(call.call_count,1)
        db=FakeDb([{"id":2,"source_mal_id":13,"title":"Shingeki no Kyojin"}])
        stats=run_batch(db,lookup=lambda _ids: (_ for _ in ()).throw(WikidataLookupError("offline")))
        self.assertEqual(stats["error"],1)
        self.assertEqual(stats["matched"],0)
        self.assertFalse(any("INSERT INTO manga_wikidata_fact" in q
                             for q,_ in db.executed))

    def test_batch_prioritizes_collection_and_only_writes_staging_tables(self):
        works=[
            {"id":2,"source_mal_id":13,"title":"Shingeki no Kyojin"},
            {"id":3,"source_mal_id":42,"title":"Dragon Ball"},
            {"id":4,"source_mal_id":9,"title":"Unmatched"},
        ]
        db=FakeDb(works)
        requested=[]
        def lookup(ids):
            requested.append(ids)
            return response(
                binding(13,"Q12345","L'Attaque des Titans","manga japonais","action"),
                binding(42,"Q11111","Dragon Ball"),
                binding(42,"Q22222","Other Dragon Ball"),  # ambiguous
            )
        result=run_batch(db,limit=3,lookup=lookup)
        self.assertEqual(requested,[[13,42,9]])
        self.assertEqual(result["matched"],1)
        self.assertEqual(result["ambiguous"],1)
        self.assertEqual(result["not_found"],1)
        self.assertEqual(result["labels_fr"],1)
        self.assertEqual(result["genres_fr"],1)
        statements=[q for q,_ in db.executed]
        self.assertEqual(sum("INSERT INTO manga_wikidata_fact" in q for q in statements),1)
        self.assertEqual(sum("INSERT INTO manga_wikidata_attempt" in q for q in statements),3)
        self.assertFalse(any("INSERT INTO manga_fr_edition" in q or
                             "INSERT INTO user_manga_" in q or
                             "UPDATE manga " in q or "DELETE FROM manga" in q
                             for q in statements))
        self.assertIn("user_manga_inventory_declaration",WORK_SQL)
        self.assertIn("user_manga_library",WORK_SQL)
        self.assertIn("ORDER BY priority",WORK_SQL)
        self.assertIn("ON CONFLICT (manga_id)",UPSERT_FACT_SQL)
        self.assertIn("ON CONFLICT (manga_id)",UPSERT_ATTEMPT_SQL)

    def test_second_run_only_uses_own_staged_metadata(self):
        # Source of truth must always remain Tenrai/MAL, never a guessed title.
        sql=WORK_SQL
        self.assertIn("m.source_mal_id",sql)
        self.assertIn("a.checked_at IS NULL",sql)
        self.assertIn("INTERVAL '45 days'",sql)
        self.assertNotIn("title ILIKE",sql)

    def test_router_exposes_facts_as_community_metadata_not_verified_edition(self):
        db=FakeDb()
        router=create_wikidata_router(db)
        endpoint=next(r.endpoint for r in router.routes
                      if r.path.endswith("/wikidata"))
        payload=endpoint(12)
        self.assertEqual(payload["status"],"MATCHED")
        self.assertEqual(payload["label_fr"],"L'Attaque des Titans")
        self.assertEqual(payload["source_url"],"https://www.wikidata.org/wiki/Q12345")
        self.assertEqual(payload["genres_fr"],["mystère"])
        self.assertFalse(payload["french_publisher_title_verified"])
        self.assertFalse(payload["editions_verified"])
        self.assertFalse(payload["description_is_plot_synopsis"])
        self.assertTrue(all(q.strip().startswith("SELECT") for q,_ in db.executed))
        with self.assertRaises(HTTPException):
            endpoint(0)
        unknown=FakeDb(exists=False)
        missing=create_wikidata_router(unknown)
        with self.assertRaises(HTTPException) as e:
            missing.routes[0].endpoint(99)
        self.assertEqual(e.exception.status_code,404)

    def test_cli_reports_total_unavailability_as_failure(self):
        with patch("apps.api.app.wikidata_enrichment.run_batch",return_value={
            "selected":2,"matched":0,"not_found":0,"ambiguous":0,
            "error":2,"labels_fr":0,"genres_fr":0,
        }):
            self.assertEqual(cli_main(["--limit","2"]),1)
        for n in (0,MAX_BATCH+1):
            with self.assertRaises(SystemExit):
                cli_main(["--limit",str(n)])


if __name__=="__main__":
    unittest.main()
