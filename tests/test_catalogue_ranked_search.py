"""Guard discover-page manga search from Meili false positives.

This fixture reproduces the user's 'Adieu Eri' search screenshot:
Sayonara Eri must beat titles merely containing the word 'Adieu',
and substring 'eri' must not match inside Period.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.api.app.catalogue_ranked_search import ranked_catalogue_ids
from apps.api.app import main


def manga(idx: int, title: str, *, alias: str | None = None,
          source: str = "TENRAI_MAL_TYPED") -> dict:
    return {
        "id": idx, "source_mal_id": idx,
        "title": title, "title_english": None,
        "title_japanese": None, "manga_type": "Manga", "volumes": 1,
        "wikidata_label_fr": None,
        "matching_alias_sources": (
            [{"alias": alias, "source_name": source,"source_id": "Q%d" % idx}]
            if alias else []
        ),
    }


class Cursor:
    def __init__(self, rows):
        self.rows=rows
        self.statements=[]
    def execute(self, sql, params):
        self.statements.append((sql, params))
    def fetchall(self):
        return self.rows
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


class DB:
    def __init__(self, ids, catalog):
        self.cur=Cursor(ids)
        self.catalog=catalog
        self.calls=0
        self.statements=[]
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def cursor(self):
        self.calls+=1
        if self.calls == 1:
            return self.cur
        return self
    def execute(self,sql,params):
        self.statements.append((sql,params))
    def fetchall(self):
        ids=self.statements[-1][1].get("search_ids",[])
        return [dict(self.catalog[id]) for id in ids
                if id in self.catalog]


class CatalogRankedSearchTests(unittest.TestCase):
    def test_adieu_eri_prefers_sayonara_and_does_not_use_substrings(self):
        cur=Cursor([
            manga(101, "I Bid You Adieu"),
            manga(1145, "Sayonara Eri"),
            manga(878, "Blue Period"),
            manga(155, "Saraba Tomo yo"),
            manga(927, "Bakemonogatari"),
        ])
        matched=ranked_catalogue_ids(cur,"Adieu Eri")
        self.assertEqual(matched,[1145])
        sql, params=cur.statements[0]
        self.assertIn("~* ANY",sql)
        self.assertNotIn("ILIKE ANY",sql)
        self.assertIn(r"\meri\M",params["patterns"])
        self.assertIn(r"\madieu\M",params["patterns"])

    def test_exact_documented_french_alias_outweighs_partial_words(self):
        cur=Cursor([manga(10,"French-language work",alias="Adieu Eri",
                          source="WIKIDATA_P4087"),
                    manga(1145,"Sayonara Eri")])
        result=ranked_catalogue_ids(cur,"Adieu Eri")
        self.assertEqual(result[0],10)
        self.assertIn(1145,result)

    def test_single_word_search_keeps_existing_meili_path(self):
        cursor=Cursor([manga(1145,"Sayonara Eri")])
        self.assertIsNone(ranked_catalogue_ids(cursor,"Narutoo"))
        self.assertEqual(cursor.statements,[])

    def test_wholeword_search_ignores_meili_fuzzy_wrong_cards(self):
        actual={1145:manga(1145,"Sayonara Eri")}
        db=DB([manga(1145,"Sayonara Eri"),
               manga(23,"I Bid You Adieu")],actual)
        with (patch.object(main,"get_connection",return_value=db),
              patch.object(main,"meili_search_ids",return_value=[23,99]) as fuzzy):
            out=main.list_mangas(
                q="Adieu Eri",limit=13,offset=0,genre=None,only_finished=False)
        self.assertEqual([item["title"] for item in out["items"]],["Sayonara Eri"])
        fuzzy.assert_not_called()
        self.assertEqual(db.statements[-1][1]["search_ids"],[1145])
        self.assertEqual(out["count"],1)

    def test_missing_multiword_name_does_not_show_unrelated_fuzzy_hits(self):
        db=DB([],{})
        with (patch.object(main,"get_connection",return_value=db),
              patch.object(main,"meili_search_ids",return_value=[5,6]) as fuzzy):
            out=main.list_mangas(
                q="Completely Unknown Manga Title",
                limit=13,offset=0,genre=None,only_finished=False)
        self.assertEqual(out["items"],[])
        self.assertEqual(db.statements[-1][1]["search_ids"],[])
        fuzzy.assert_not_called()


if __name__=="__main__":
    unittest.main()
