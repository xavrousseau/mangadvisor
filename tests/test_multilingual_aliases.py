"""Multilingual titles are evidence-backed, never physical-edition matches."""
import unittest
from unittest.mock import patch
from apps.api.app.multilingual_aliases import (
  title_key,parse_entities,fetch_entities,run_batch,SCHEMA,WORK_SQL
)


def entity(qid,mal,*,wrong=False):
    return {
      "id":qid,
      "labels":{
        "fr":{"language":"fr","value":"L'Attaque des Titans"},
        "en":{"language":"en","value":"Attack on Titan"},
        "ja":{"language":"ja","value":"進撃の巨人"},
      },
      "aliases":{
        "fr":[{"language":"fr","value":"Les Titans"}],
        "en":[{"language":"en","value":"Shingeki no Kyojin"}],
      },
      "claims":{"P4087":[{"mainsnak":{"datavalue":{
         "value":str(mal if not wrong else 99999)
      }}}]},
    }


class Cursor:
    def __init__(self,db):self.db=db;self.sql=None
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.sql=sql
        self.db.calls.append((sql,params))
    def fetchall(self):return self.db.works
class Conn:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return Cursor(self.db)
    def commit(self):pass
    def transaction(self):return self
class Db:
    def __init__(self):
        self.calls=[]
        self.works=[{"id":5,"source_mal_id":13,"wikidata_id":"Q123"}]
    def __call__(self):return Conn(self)


class AliasTests(unittest.TestCase):
    def test_unicode_accent_and_punctuation(self):
        self.assertEqual(title_key(" L’Attaque  des  Titans ! "), "l attaque des titans")
        self.assertEqual(title_key("Éri"),"eri")
        self.assertEqual(title_key("進撃の巨人"),"進撃の巨人")

    def test_only_exact_wikidata_mal_identity_is_accepted(self):
        works=[{"id":5,"source_mal_id":13,"wikidata_id":"Q123"}]
        aliases=parse_entities(works,{"entities":{"Q123":entity("Q123",13)}})[5]
        names={a["alias"] for a in aliases}
        self.assertIn("L'Attaque des Titans",names)
        self.assertIn("Attack on Titan",names)
        self.assertIn("進撃の巨人",names)
        self.assertIn("Shingeki no Kyojin",names)
        self.assertEqual({a["source_name"] for a in aliases},{"WIKIDATA_P4087"})
        self.assertEqual({a["source_url"] for a in aliases},{"https://www.wikidata.org/wiki/Q123"})
        with self.assertRaises(ValueError):
            parse_entities(works,{"entities":{"Q123":entity("Q123",13,wrong=True)}})
        with self.assertRaises(ValueError):
            parse_entities(works,{"entities":{}})
        with self.assertRaises(ValueError):
            parse_entities(works,{"entities":{"Q123":entity("Q456",13)}})

    def test_batch_only_writes_title_alias_evidence(self):
        db=Db()
        stats=run_batch(db,limit=1,lookup=lambda ids:{
           "entities":{"Q123":entity("Q123",13)}
        })
        self.assertEqual(stats["checked"],1)
        self.assertGreater(stats["aliases"],2)
        self.assertIn("manga_wikidata_attempt",WORK_SQL)
        insertions=[sql for sql,_ in db.calls if "INSERT INTO" in sql]
        self.assertTrue(all("manga_title_alias" in x for x in insertions))
        self.assertFalse(any("INSERT INTO manga_fr_edition" in s
            or "INSERT INTO user_manga_" in s for s,_ in db.calls))
        self.assertIn("PRIMARY KEY (manga_id,source_name,language_code,alias_key)",SCHEMA)

    def test_provider_bad_id_causes_no_alias_writes(self):
        db=Db()
        stats=run_batch(db,limit=1,lookup=lambda ids:{
           "entities":{"Q123":entity("Q123",13,wrong=True)}
        })
        self.assertEqual(stats["error"],1)
        self.assertEqual(stats["aliases"],0)
        self.assertFalse(any("INSERT INTO manga_title_alias" in sql for sql,_ in db.calls))

    def test_bounded_provider_and_locale_request(self):
        from apps.api.app import multilingual_aliases as mod
        for value in ([],["Q1"]*21,["Q1; DROP TABLE manga"]):
            with self.assertRaises(ValueError):
                fetch_entities(value)
        class Response:
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self,n):
                self.n=n
                return b'{"entities":{}}'
        with patch.object(mod.urllib.request,"urlopen",return_value=Response()) as fetch:
            fetch_entities(["Q123"])
        req=fetch.call_args[0][0]
        self.assertIn("wikidata.org/w/api.php",req.full_url)
        self.assertIn("languages=fr%7Cen%7Cja",req.full_url)
        self.assertIn("claims",req.full_url)
        self.assertEqual(fetch.call_args.kwargs["timeout"],25)
        self.assertIn("Mangadvisor",req.get_header("User-agent"))
    def test_batch_limits_and_no_network_on_zero_works(self):
        db=Db()
        for limit in (0,21):
            with self.assertRaises(ValueError):
                run_batch(db,limit=limit)
        db.works=[]
        provider=unittest.mock.Mock()
        report=run_batch(db,lookup=provider)
        self.assertEqual(report["selected"],0)
        provider.assert_not_called()

if __name__=="__main__":
    unittest.main()
