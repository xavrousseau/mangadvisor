"""Multilingual work title aliases are source-linked, bounded and never editions."""
from __future__ import annotations
import unittest
from unittest.mock import patch, Mock

from apps.api.app.title_aliases import (
    title_key, aliases_from_source, REVIEWED_WORK_ALIASES,
    CANONICAL_SQL, UPSERT_SQL, SCHEMA, refresh_library_wikidata,
    sync_aliases,
)


class FakeCursor:
    def __init__(self,db,named=False):
        self.db=db
        self.named=named
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.db.queries.append((sql,params))
        if sql.startswith("INSERT INTO manga_title_alias"):
            self.db.writes.append(params)
    def fetchmany(self,size):
        if not self.named:raise AssertionError("bulk cursor expected")
        result=self.db.rows[self.db.offset:self.db.offset+size]
        self.db.offset+=len(result)
        return result


class FakeConn:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self,name=None):return FakeCursor(self.db,named=name is not None)
    def commit(self):pass


class FakeDb:
    def __init__(self,rows):
        self.rows=rows
        self.offset=0
        self.queries=[]
        self.writes=[]
    def __call__(self):return FakeConn(self)


class AliasTests(unittest.TestCase):
    def test_french_punctuation_accents_normalize_but_keep_series_numbers_and_japanese(self):
        self.assertEqual(title_key("L’Attaque des Titans"),"l attaque des titans")
        self.assertEqual(title_key("L'attaque des titans"),"l attaque des titans")
        self.assertEqual(title_key("HÉLL’S PARADISE"),"hell s paradise")
        self.assertEqual(title_key("Kaiju n°8"),"kaiju no 8")
        self.assertEqual(title_key("Kaiju nº 8"),"kaiju no 8")
        self.assertEqual(title_key("進撃の巨人"),"進撃の巨人")
        self.assertNotEqual(title_key("Tokyo Ghoul"),title_key("Tokyo Ghoul:re"))
        self.assertNotEqual(title_key("Fairy Tail"),title_key("Fairy Tail 100 Years Quest"))
        self.assertNotEqual(title_key("Dragon Ball"),title_key("Dragon Ball Super"))
        self.assertEqual(title_key("💥"),"")

    def test_raw_mal_synonyms_and_three_wikidata_languages_are_provenanced(self):
        row={
          "id":7,"source_mal_id":74,
          "title":"Shingeki no Kyojin",
          "title_english":"Attack on Titan",
          "title_japanese":"進撃の巨人",
          "raw_json":{"title_synonyms":["AoT","Shingeki no Kyojin"],
             "titles":[
                 {"type":"Default","title":"Shingeki no Kyojin"},
                 {"type":"English","title":"Attack on Titan"},
                 {"type":"Japanese","title":"進撃の巨人"},
             ]},
          "wikidata_id":"Q987654",
          "wikidata_label_fr":"L'Attaque des Titans",
          "wikidata_alternate_titles":[
            {"lang":"fr","title":"L’Attaque des Titans"},
            {"lang":"en","title":"Attack on Titan"},
            {"lang":"ja","title":"進撃の巨人"},
          ]
        }
        aliases=aliases_from_source(row)
        by_source={(a["source_name"],a["alias_key"]):a for a in aliases}
        assert by_source
        bnf=by_source[("BNF_AUTHORITY_WORK","l attaque des titans")]
        self.assertEqual(bnf["source_url"],
                         "https://catalogue.bnf.fr/ark:/12148/cb177166897")
        self.assertEqual(bnf["language"],"fr")
        self.assertIn(("MAL_ENGLISH","attack on titan"),by_source)
        self.assertIn(("MAL_JAPANESE","進撃の巨人"),by_source)
        self.assertIn(("MAL_SYNONYM","aot"),by_source)
        self.assertIn(("WIKIDATA_P4087_FR","l attaque des titans"),by_source)
        self.assertIn(("WIKIDATA_P4087_JA","進撃の巨人"),by_source)
        self.assertTrue(all(a["source_url"] for a in aliases))
        # Same text from two sources is retained as two provenance records.
        self.assertNotEqual(bnf["source_name"],
                            by_source[("WIKIDATA_P4087_FR","l attaque des titans")]["source_name"])

    def test_authority_seed_never_applies_to_anime_or_unrelated_work(self):
        row={"id":9,"source_mal_id":9999,"title":"Attack on Titan animation"}
        aliases=aliases_from_source(row)
        self.assertFalse(any(a["source_name"]=="BNF_AUTHORITY_WORK" for a in aliases))
        self.assertFalse(any(a["language"]=="fr" for a in aliases))
        self.assertEqual(REVIEWED_WORK_ALIASES[0][0],74)

    def test_bulk_index_does_not_write_user_library(self):
        db=FakeDb([
            {"id":1,"source_mal_id":74,"title":"Shingeki no Kyojin",
             "title_english":"Attack on Titan","title_japanese":"進撃の巨人",
             "raw_json":{"title_synonyms":["AoT"]},
             "wikidata_id":None,"wikidata_label_fr":None,
             "wikidata_alternate_titles":[]},
            {"id":2,"source_mal_id":42,"title":"Dragon Ball",
             "title_english":None,"title_japanese":None,
             "raw_json":None,"wikidata_id":None,
             "wikidata_label_fr":None,"wikidata_alternate_titles":[]},
        ])
        result=sync_aliases(db,max_works=3)
        self.assertEqual(result["works"],2)
        self.assertTrue(any(w["source_name"]=="BNF_AUTHORITY_WORK" for w in db.writes))
        self.assertTrue(any(w["alias_key"]=="aot" for w in db.writes))
        self.assertTrue(all("INSERT INTO manga_title_alias" in sql
                            for sql,params in db.queries
                            if sql.strip().startswith("INSERT")))
        self.assertIn("ON CONFLICT (manga_id,alias_key,source_name)",UPSERT_SQL)
        self.assertIn("REFERENCES manga(id)",SCHEMA)
        self.assertFalse(any("DELETE FROM" in sql or "TRUNCATE" in sql
                             for sql,_ in db.queries))

    def test_opt_in_refresh_is_chunked_by_exact_linked_mal_ids(self):
        db=FakeDb([])
        ids=list(range(1,54))
        calls=[]
        def mock_batch(_factory,**kw):
            calls.append(kw)
            return {"selected":len(kw["target_ids"]),"matched":len(kw["target_ids"]),
                    "error":0}
        with patch("apps.api.app.library_enrichment.linked_library_scope",
                   return_value={"ids":ids,"pending":49,"truncated":False}),\
             patch("apps.api.app.wikidata_enrichment.run_batch",side_effect=mock_batch):
            paused=[]
            out=refresh_library_wikidata(db,max_works=80,sleep=paused.append)
        self.assertEqual([len(c["target_ids"]) for c in calls],[15,15,15,8])
        self.assertEqual(len(paused),3)
        self.assertEqual(out["matched"],53)
        self.assertTrue(all(c["refresh"] for c in calls))
        self.assertTrue(all(c["limit"]==len(c["target_ids"]) for c in calls))


if __name__ == "__main__":
    unittest.main()
