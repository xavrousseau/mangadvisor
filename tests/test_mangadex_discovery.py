"""MangaDex is an optional *read only* search, never a provenance shortcut."""
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from apps.api.app.mangadex_discovery import (
    extract_mal_candidates,search_verified_mangadex,search_mangadex
)

UUID="11111111-2222-4333-8444-555555555555"
def result(mid="13",uuid=UUID):
    return {"type":"manga","id":uuid,"attributes":{
        "title":{"en":"Attack on Titan"},
        "altTitles":[{"fr":"L'Attaque des Titans"},{"ja":"進撃の巨人"}],
        "links":{"mal":mid},
        "contentRating":"safe",
    }}

class Cursor:
    def __init__(self):self.args=None
    def execute(self,sql,params):
        self.sql=sql;self.args=params
    def fetchall(self):
        return [{"id":47,"source_mal_id":13,"title":"Shingeki no Kyojin",
                 "title_english":"Attack on Titan","title_japanese":"進撃の巨人",
                 "volumes":34,"manga_type":"Manga"}]

class MangadexTests(unittest.TestCase):
    def test_only_exact_mal_link_is_candidate(self):
        rows=extract_mal_candidates({"data":[
           result(),
           result(mid=""),
           result(mid="13'; DROP TABLE manga --"),
           result(mid="999",uuid="broken"),
        ]})
        self.assertEqual(list(rows),[13])
        self.assertIn("L'Attaque des Titans",[x["alias"] for x in rows[13]["titles"]])
        self.assertEqual(rows[13]["source_name"],"MANGADEX")

    def test_ambiguous_duplicate_mal_id_is_not_trusted(self):
        other="22222222-2222-4333-8444-555555555555"
        rows=extract_mal_candidates({"data":[result(),result(uuid=other)]})
        self.assertEqual(rows,{})

    def test_candidate_must_also_exist_in_canonical_catalog(self):
        cur=Cursor()
        items=search_verified_mangadex(
           cur,"L'Attaque des Titans",
           lookup=lambda _:{"data":[result()]},
        )
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["id"],47)
        self.assertEqual(items[0]["matched_alias"],"L'Attaque des Titans")
        self.assertEqual(items[0]["source_name"],"MANGADEX")
        self.assertEqual(items[0]["verification_basis"],"mangadex_links_mal_exact")
        self.assertEqual(cur.args,{"ids":[13]})
        self.assertIn("source_mal_id=ANY",cur.sql)
        self.assertNotIn("INSERT",cur.sql)

    def test_missing_or_bad_mal_id_never_generates_sql(self):
        cur=Cursor()
        found=search_verified_mangadex(
          cur,"L'Attaque",lookup=lambda _:{"data":[result(mid="unknown")]}
        )
        self.assertEqual(found,[])
        self.assertIsNone(cur.args)

    def test_network_single_request_with_safe_content_rating(self):
        from apps.api.app import mangadex_discovery as mod
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self,n):return b'{"result":"ok","data":[]}'
        with patch.object(mod.urllib.request,"urlopen",return_value=Resp()) as fn:
            data=search_mangadex("L'Attaque des Titans")
        self.assertEqual(data["data"],[])
        req=fn.call_args.args[0]
        self.assertIn("api.mangadex.org/manga",req.full_url)
        self.assertIn("contentRating%5B%5D=safe",req.full_url)
        self.assertEqual(fn.call_count,1)
        with self.assertRaises(ValueError):
            search_mangadex(" ")
        with patch.object(mod.urllib.request,"urlopen",side_effect=TimeoutError()):
            with self.assertRaises(HTTPException) as err:
                search_mangadex("Naruto")
        self.assertEqual(err.exception.status_code,503)

if __name__=="__main__":
    unittest.main()
