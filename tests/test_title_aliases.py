"""Alias ingestion is indexed by exact MAL manga ID, never inferred edition."""
import unittest
from datetime import datetime,timezone
from unittest.mock import patch

from fastapi import HTTPException
from apps.api.app.title_aliases import (
    normalize_title,make_alias,local_aliases,matched_mangadex,
    import_local_aliases,import_mangadex_aliases,pending_mangadex_aliases,
    create_title_alias_router,SOURCE_MANGADEX,SCHEMA,LOCAL_SQL,
    PENDING_MANGADEX,PENDING_OWNER_SQL,UPSERT,
)

UUID="12345678-1111-2222-3333-444444444444"
UUID_TWO="12345678-1111-2222-3333-555555555555"


def dex(uuid=UUID,mal=13,title="L'Attaque des Titans"):
    return {"id":uuid,"type":"manga","attributes":{
        "title":{"en":"Attack on Titan"},
        "altTitles":[{"fr":title},{"ja-ro":"Shingeki no Kyojin"},
                     {"ja":"進撃の巨人"}],
        "links":{"mal":str(mal)},
    }}


class Cursor:
    def __init__(self,db):self.db=db;self.sql=""
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.db.queries.append((sql,params));self.sql=sql
        if sql==LOCAL_SQL:
            n=params["after_id"]
            self.db.rows=[x for x in self.db.catalog if x["id"]>n][:params["limit"]]
        elif sql==PENDING_MANGADEX:
            self.db.rows=self.db.works[:params["limit"]]
            self.db.works=self.db.works[params["limit"]:]
        elif sql==PENDING_OWNER_SQL:
            self.db.rows=self.db.pending[:params["limit"]]
            self.db.pending=self.db.pending[params["limit"]:]
        elif "WHERE source_mal_id=ANY" in sql:
            self.db.rows=[{"id":x["id"],"source_mal_id":x["source_mal_id"]}
                          for x in self.db.catalog
                          if x["source_mal_id"] in params["ids"]]
        elif "SELECT id,source_mal_id FROM manga WHERE id" in sql:
            self.db.one={"id":7,"source_mal_id":13} if self.db.exists else None
        elif "FROM manga_title_alias" in sql and "ORDER BY CASE language_code" in sql:
            self.db.rows=[
                {"alias":"L'Attaque des Titans","language_code":"fr",
                 "source_name":SOURCE_MANGADEX,
                 "source_ref":"https://mangadex.org/title/"+UUID}
            ]
    def fetchall(self):return self.db.rows
    def fetchone(self):return self.db.one


class Connection:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return Cursor(self.db)
    def commit(self):pass


class Database:
    def __init__(self,catalog=None,works=None,pending=None,exists=True):
        self.queries=[];self.rows=[];self.one=None
        self.catalog=catalog or [];self.works=works or []
        self.pending=pending or [];self.exists=exists
    def __call__(self):return Connection(self)


class MultilingualTitleTests(unittest.TestCase):
    def test_normalize_typographic_accents_without_stripping_franchise(self):
        self.assertEqual(normalize_title("L’Attaque des Titans"),
                         normalize_title("L'attaque des titans"))
        self.assertEqual(normalize_title("Kaiju n°8"),"kaiju n 8")
        self.assertNotEqual(normalize_title("Dragon Ball Deluxe"),
                            normalize_title("Dragon Ball"))
        self.assertNotEqual(normalize_title("Attack on Titan"),
                            normalize_title("Attack on Titan: Before the Fall"))
        self.assertEqual(normalize_title("進撃の巨人"),"進撃の巨人")
        self.assertIsNone(make_alias("<x>","xy","MAL","source",13))
        self.assertIsNone(make_alias("x"*300,"fr","MAL","source",13))

    def test_raw_mal_aliases_only_imported_if_mal_id_matches(self):
        source={
            "id":7,"source_mal_id":13,"title":"Shingeki no Kyojin",
            "title_english":"Attack on Titan","title_japanese":"進撃の巨人",
            "raw_json":{"mal_id":13,
                "title_synonyms":["Shingeki no Kyojin","Attack on Titan"],
                "titles":[{"type":"French","title":"L'Attaque des Titans"},
                          {"type":"English","title":"Attack on Titan"}]},
            "label_fr":"L'Attaque des Titans","wikidata_id":"Q4321"
        }
        aliases=local_aliases(source)
        self.assertTrue(any(a["language_code"]=="fr" and a["source_name"]=="WIKIDATA_P4087"
                            for a in aliases))
        self.assertTrue(any(a["source_name"]=="MAL_ALTERNATIVE" and
                            a["language_code"]=="fr" for a in aliases))
        self.assertTrue(any(a["alias"]=="進撃の巨人" for a in aliases))
        other=local_aliases({**source,"raw_json":{"mal_id":999,
                         "titles":[{"type":"French","title":"Intruder"}]}})
        self.assertFalse(any(a["alias"]=="Intruder" for a in other))
        db=Database(catalog=[source])
        report=import_local_aliases(db,limit=2)
        self.assertEqual(report["works"],1)
        self.assertGreater(report["aliases"],3)
        self.assertTrue(all("INSERT INTO manga_title_alias" in q
                            for q,_ in db.queries if "INSERT INTO" in q))

    def test_dex_requires_exact_mal_id_not_just_similar_title(self):
        payload={"result":"ok","data":[
            dex(mal=13),
            dex(uuid=UUID_TWO,mal=999,title="L'Attaque des Titans"),
        ]}
        exact=matched_mangadex(13,[payload])
        self.assertEqual(exact["status"],"MATCHED")
        self.assertEqual(exact["source_id"],UUID)
        self.assertTrue(any(a["language_code"]=="fr" and
                           a["alias"]=="L'Attaque des Titans" for a in exact["aliases"]))
        self.assertTrue(all(a["source_name"]==SOURCE_MANGADEX for a in exact["aliases"]))
        self.assertEqual(matched_mangadex(25,[payload])["status"],"NOT_FOUND")
        amb={"result":"ok","data":[dex(),dex(uuid=UUID_TWO,mal=13)]}
        self.assertEqual(matched_mangadex(13,[amb])["status"],"AMBIGUOUS")
        self.assertEqual(matched_mangadex(13,[{"data":[{
            **dex(),"attributes":{**dex()["attributes"],"links":{}}
        }]}])["status"],"NOT_FOUND")

    def test_dex_batch_does_not_modify_canonical_or_user_tables(self):
        db=Database(works=[
            {"id":7,"source_mal_id":13,"title":"Shingeki no Kyojin",
             "title_english":"Attack on Titan"}
        ])
        requests=[]
        result=import_mangadex_aliases(
            db,target_ids=[7],limit=3,
            search=lambda title:requests.append(title) or
                  {"result":"ok","data":[dex()]},
            sleep=lambda _:None
        )
        self.assertEqual(result["matched"],1)
        self.assertEqual(result["french"],1)
        self.assertEqual(requests,["Attack on Titan","Shingeki no Kyojin"])
        inserts=[q for q,_ in db.queries if "INSERT INTO" in q]
        self.assertTrue(any("INSERT INTO manga_mangadex_attempt" in q for q in inserts))
        self.assertTrue(all("INSERT INTO manga_" in q for q in inserts))
        self.assertFalse(any("user_manga" in q or "manga_fr_edition" in q for q in inserts))
        self.assertIn("source_mal_id",PENDING_MANGADEX)
        self.assertIn("NOT NULL",SCHEMA)

    def test_pending_french_titles_can_supply_verified_alias_without_auto_link(self):
        db=Database(
            catalog=[{"id":7,"source_mal_id":13}],
            pending=[{"source_key":"A2","entry_title":"L'Attaque des Titans",
                      "work_declared":None}],
        )
        result=pending_mangadex_aliases(
            db,limit=5,search=lambda _:{"data":[dex()],"result":"ok"},
            sleep=lambda _:None
        )
        self.assertEqual(result["matched"],1)
        self.assertGreaterEqual(result["french"],1)
        self.assertFalse(any("INSERT INTO user_manga_inventory_declaration" in q
                             or "DELETE FROM user_manga_inventory_pending" in q
                             for q,_ in db.queries))
        self.assertTrue(any("INSERT INTO manga_mangadex_pending_attempt" in q
                            for q,_ in db.queries))
        query=next((q for q,_ in db.queries if "source_mal_id=ANY" in q),None)
        self.assertIsNotNone(query)

    def test_pending_search_must_match_a_full_external_title(self):
        db=Database(catalog=[{"id":7,"source_mal_id":13}],
                    pending=[{"source_key":"A3","entry_title":"Titans",
                              "work_declared":None}])
        result=pending_mangadex_aliases(
            db,limit=1,
            search=lambda _:{"data":[dex()],"result":"ok"},
            sleep=lambda _:None
        )
        self.assertEqual(result["matched"],0)
        self.assertEqual(result["not_found"],1)
        self.assertFalse(any("INSERT INTO manga_title_alias" in q
                            for q,_ in db.queries))

    def test_unknown_external_mal_stays_unlinked(self):
        db=Database(pending=[{"source_key":"B1","entry_title":"Other Work",
                              "work_declared":None}])
        result=pending_mangadex_aliases(db,limit=1,
             search=lambda _:{"data":[dex(mal=888,title="Other Work")],"result":"ok"},
             sleep=lambda _:None)
        self.assertEqual(result["outside_catalog"],1)
        self.assertFalse(any("INSERT INTO manga_title_alias" in q
                             for q,_ in db.queries))

    def test_aliases_endpoint_read_only_and_marks_french_unverified(self):
        db=Database()
        router=create_title_alias_router(db)
        endpoint=next(r.endpoint for r in router.routes
                      if r.path.endswith("/title-aliases"))
        output=endpoint(7)
        self.assertEqual(output["items"][0]["language_code"],"fr")
        self.assertFalse(output["french_publisher_titles_verified"])
        self.assertFalse(output["automatic_edition_match"])
        with self.assertRaises(HTTPException):
            endpoint(-1)


if __name__=="__main__":
    unittest.main()
