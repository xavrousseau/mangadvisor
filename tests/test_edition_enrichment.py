"""Enrichment is bounded, evidence-based and never adds books automatically."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from apps.api.app.edition_enrichment import (
    build_workshop, select_search_titles, title_clue, title_tokens,
    create_enrichment_router,
)


def candidate(isbn, title, **other):
    return {"isbn13":isbn, "title_fr":title, "status":"CANDIDATE_UNCONFIRMED",
            "manga_match_verified":False, "edition_kind_suggested":"UNKNOWN",
            "publisher_fr":"A real publisher", **other}


class EnrichmentTests(unittest.TestCase):
    def test_tokens_are_normalized_but_never_certify_identity(self):
        self.assertEqual(title_tokens("L'Édition Deluxe de MONSTER, Tome 2"),{"monster","2"})
        self.assertEqual(title_clue("Monster. Tome 1",["Monster"]),
                         (2,"TITLE_WORDS_PRESENT"))
        self.assertEqual(title_clue("Mystery Tome 1",["Monster"]),
                         (0,"NO_TITLE_WORDS"))
        self.assertEqual(title_clue("Monster in Tokyo",["Monster Tokyo"]),
                         (2,"TITLE_WORDS_PRESENT"))

    def test_two_distinct_titles_and_no_unsafe_cql(self):
        titles=select_search_titles({"title":"Naruto","title_english":"NARUTO"})
        self.assertEqual(titles,["Naruto"])
        self.assertEqual(select_search_titles({
            "title":'Naruto" OR bib.title all "Anything',
            "title_english":"Naruto Shippuden"
        }),["Naruto Shippuden"])
        self.assertEqual(select_search_titles({"title":"海贼王","title_english":"One Piece"}),
                         ["海贼王","One Piece"])
        self.assertEqual(select_search_titles({"title":"!!","title_english":""}),[])

    def test_dedupe_and_register_here_other_versus_new(self):
        results=[
            {"items":[candidate("9782871294146","Naruto, tome 1"),
                      candidate("9782344074282","Naruto, tome 2")]},
            {"items":[candidate("9782871294146","Naruto volume one"),
                      candidate("9781234567897","Unexpected book")]},
        ]
        registered={
            "9782871294146":{"manga_id":12,"edition_kind":"CLASSIC","volume_number":1},
            "9781234567897":{"manga_id":27,"edition_kind":"PERFECT","volume_number":1},
        }
        report=build_workshop(12,["Naruto","Naruto French"],results,registered,[])
        self.assertEqual(report["count"],3)
        self.assertEqual(report["to_verify_count"],1)
        self.assertEqual(report["registered_here_count"],1)
        self.assertEqual(report["registered_other_count"],1)
        self.assertEqual(report["items"][0]["isbn13"],"9782344074282")
        by_isbn={row["isbn13"]:row for row in report["items"]}
        self.assertEqual(by_isbn["9782871294146"]["registration_status"],"REGISTERED_HERE")
        self.assertEqual(by_isbn["9781234567897"]["registration_status"],"REGISTERED_OTHER")
        self.assertEqual(by_isbn["9781234567897"]["registered_manga_id"],27)
        self.assertFalse(report["exhaustive"])
        self.assertFalse(report["match_verified"])
        self.assertFalse(report["writes_performed"])
        self.assertEqual(by_isbn["9782344074282"]["manga_match_verified"],False)

    def test_partial_search_failures_and_no_false_exhaustive_results(self):
        report=build_workshop(5,["Monster"],[{"items":[]}],{},["Monster alternative"])
        self.assertEqual(report["search_errors"],["Monster alternative"])
        self.assertEqual(report["items"],[])
        self.assertTrue(report["first_page_per_title_only"])

    def test_cap_candidates_and_registration_lookup_only_reads(self):
        rows=[candidate(f"978{index:010d}",f"Naruto Tome {index}")
              for index in range(44)]
        report=build_workshop(5,["Naruto"],[{"items":rows}],{},[])
        self.assertEqual(report["count"],30)
        self.assertTrue(report["truncated"])

    def test_endpoint_queries_existing_series_and_isbns_read_only(self):
        class Cursor:
            def __init__(self):self.sql=[]
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,sql,params):
                self.sql.append((sql,params))
            def fetchone(self):
                return {"id":12,"title":"Naruto","title_english":"Naruto"}
            def fetchall(self):
                return [{"isbn13":"9782871294146","manga_id":12,
                         "edition_kind":"CLASSIC","volume_number":1}]
        class Connection:
            def __init__(self):self.cur=Cursor()
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def cursor(self):return self.cur
        connections=[]
        def connect():
            c=Connection()
            connections.append(c)
            return c
        router=create_enrichment_router(connect)
        endpoint=next(route.endpoint for route in router.routes
                      if route.path.endswith("/enrichment"))
        with patch("apps.api.app.edition_enrichment.search_bnf_by_title",
                   return_value={"items":[candidate("9782871294146","Naruto 1"),
                                          candidate("9782344074282","Naruto 2")]}
                  ) as search:
            report=endpoint(12)
        search.assert_called_once_with("Naruto")
        self.assertEqual(report["registered_here_count"],1)
        self.assertEqual(report["to_verify_count"],1)
        self.assertEqual(len(connections),2)
        for conn in connections:
            for sql,_ in conn.cur.sql:
                self.assertTrue(sql.strip().upper().startswith("SELECT"),sql)
        self.assertEqual(connections[1].cur.sql[0][1]["isbns"],
                         ["9782344074282","9782871294146"])


    def test_optional_french_title_is_deduped_sanitized_and_not_persisted(self):
        book={"title":"Shingeki no Kyojin","title_english":"Attack on Titan"}
        self.assertEqual(select_search_titles(book, "L’Attaque des Titans"),
                         ["Shingeki no Kyojin","Attack on Titan","L’Attaque des Titans"])
        self.assertEqual(select_search_titles(book,"Attack on Titan"),
                         ["Shingeki no Kyojin","Attack on Titan"])
        with self.assertRaises(ValueError):
            select_search_titles(book,'Monster" OR bib.isbn')

    def test_bnf_page_limits_and_more_are_documentary_not_exhaustive(self):
        records=[candidate("9782871294146","Monster. Tome 1")]
        first=build_workshop(12,["Monster"],
            [{"items":records,"bnf_reported_records":55}],{},[],page=1)
        second=build_workshop(12,["Monster"],
            [{"items":records,"bnf_reported_records":55}],{},[],page=2)
        last=build_workshop(12,["Monster"],
            [{"items":records,"bnf_reported_records":55}],{},[],page=3)
        self.assertTrue(first["has_more_pages"])
        self.assertTrue(second["has_more_pages"])
        self.assertFalse(last["has_more_pages"])
        self.assertTrue(first["first_page_per_title_only"])
        self.assertFalse(second["first_page_per_title_only"])
        self.assertFalse(last["exhaustive"])
        self.assertFalse(last["writes_performed"])
        empty=build_workshop(12,["Monster"],
            [{"items":[],"bnf_reported_records":19}],{},[],page=1)
        self.assertFalse(empty["has_more_pages"])

    def test_second_page_and_alias_hit_sru_at_record_21_without_writes(self):
        class Cursor:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,sql,params):
                assert sql.strip().upper().startswith("SELECT"),sql
                self.params=params
            def fetchone(self):return {
                "id":12,"title":"Shingeki no Kyojin","title_english":"Attack on Titan"}
            def fetchall(self):return []
        class Conn:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def cursor(self):return Cursor()
        router=create_enrichment_router(lambda: Conn())
        endpoint=next(r.endpoint for r in router.routes if r.path.endswith("/enrichment"))
        mock={"items":[candidate("9782871294146","L'Attaque des Titans. Tome 1")],
              "bnf_reported_records":70}
        with patch("apps.api.app.edition_enrichment.search_bnf_by_title",
                   return_value=mock) as search:
            page=endpoint(12,page=2,alternate_title="L’Attaque des Titans")
        self.assertEqual(search.call_count,3)
        for call in search.call_args_list:
            self.assertEqual(call.kwargs,{"start_record":21})
        self.assertEqual(page["searched_titles"][-1],"L’Attaque des Titans")
        self.assertTrue(page["has_more_pages"])
        self.assertEqual(page["count"],1)
        self.assertFalse(page["match_verified"])
        for invalid in (0,4,999):
            with self.assertRaises(HTTPException) as exc:
                endpoint(12,page=invalid)
            self.assertEqual(exc.exception.status_code,422)



if __name__=="__main__":
    unittest.main()
