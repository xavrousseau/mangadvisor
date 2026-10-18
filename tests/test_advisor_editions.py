"""Registered French ISBN evidence must be grouped without inferred completion."""
import unittest

from apps.api.app.advisor_editions import (
    MAX_BOOKS_PER_FORMAT, group_registered_editions, fetch_recommended_editions,
)
from apps.api.app.advisor import AdvisorContext, interpret, score_candidates


class EditionsEvidenceTests(unittest.TestCase):
    def test_empty_and_unknown_formats_are_honest(self):
        self.assertEqual(group_registered_editions([])["registered_isbn_count"],0)
        unknown=group_registered_editions([{
            "isbn13":"9781234567897","edition_kind":"UNKNOWN",
            "volume_number":4,"title_fr":"An item",
            "publisher_fr":None,"source_name":"CI","source_url":"test",
        }])
        self.assertEqual(unknown["registered_formats"][0]["edition_kind"],"UNKNOWN")
        self.assertEqual(unknown["registered_formats"][0]["format_basis"],"format_not_established")
        self.assertIsNone(unknown["complete_french_series"])
        self.assertIs(unknown["published_total_known"],False)
        self.assertIs(unknown["availability_checked"],False)

    def test_separate_format_series_and_publishers_without_guessing_missing(self):
        rows=[
            {"isbn13":"9781234567897","edition_kind":"DELUXE","volume_number":1,
             "title_fr":"A deluxe 1","publisher_fr":"Éditeur A"},
            {"isbn13":"9781234567804","edition_kind":"DELUXE","volume_number":3,
             "title_fr":"A deluxe 3","publisher_fr":"Éditeur A"},
            {"isbn13":"9781234567811","edition_kind":"PERFECT","volume_number":1,
             "title_fr":"A perfect 1","publisher_fr":"Éditeur B"},
            {"isbn13":"9781234567828","edition_kind":"CLASSIC","volume_number":7,
             "title_fr":"A classic 7","publisher_fr":"Éditeur C"},
            {"isbn13":"9781234567828","edition_kind":"CLASSIC","volume_number":7,
             "title_fr":"duplicate","publisher_fr":"Éditeur C"},
        ]
        report=group_registered_editions(rows)
        self.assertEqual(report["registered_isbn_count"],4)
        groups={x["edition_kind"]:x for x in report["registered_formats"]}
        self.assertEqual(groups["DELUXE"]["known_volume_numbers"],[1,3])
        self.assertEqual(groups["DELUXE"]["registered_isbn_count"],2)
        self.assertEqual(groups["PERFECT"]["publishers_fr"],["Éditeur B"])
        self.assertEqual(groups["CLASSIC"]["known_volume_numbers"],[7])
        self.assertEqual(report["complete_french_series"],None)
        self.assertEqual(report["published_total_known"],False)

    def test_capped_book_previews_keep_total_counts(self):
        rows=[{"isbn13":f"97812345{i:05d}","edition_kind":"CLASSIC",
                "volume_number":i+1,"publisher_fr":"Publisher"}
              for i in range(12)]
        report=group_registered_editions(rows)
        group=report["registered_formats"][0]
        self.assertEqual(group["registered_isbn_count"],12)
        self.assertEqual(len(group["books_shown"]),MAX_BOOKS_PER_FORMAT)
        self.assertEqual(group["books_remaining"],12-MAX_BOOKS_PER_FORMAT)
        self.assertEqual(len(group["known_volume_numbers"]),12)

    def test_parameterized_query_only_for_selected_ids(self):
        class Cursor:
            def __init__(self):
                self.sql=None
                self.params=None
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,params):
                self.sql=sql;self.params=params
            def fetchall(self):return []
        class Connection:
            def __init__(self):self.cur=Cursor()
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def cursor(self):return self.cur
        connection=Connection()
        result=fetch_recommended_editions(lambda:connection,[4,4,-1,1,0])
        self.assertEqual(sorted(result),[1,4])
        self.assertEqual(connection.cur.params,{"manga_ids":[1,4]})
        self.assertIn("ANY(%(manga_ids)s)",connection.cur.sql)
        self.assertEqual(fetch_recommended_editions(lambda:connection,[]),{})

    def test_format_preference_vs_required_and_context_followups(self):
        initial,changes,_,_=interpret("Un mystère en édition Deluxe",AdvisorContext())
        self.assertEqual(initial.preferred_edition_kind,"DELUXE")
        self.assertFalse(initial.require_edition_kind)
        self.assertIn("preferred_edition_kind",changes)
        strict,_,_,_=interpret("Finalement Deluxe obligatoire",initial)
        self.assertTrue(strict.require_edition_kind)
        self.assertEqual(strict.mood,"MYSTERY")
        reset,_,_,_=interpret("Peu importe le format",strict)
        self.assertIsNone(reset.preferred_edition_kind)
        self.assertFalse(reset.require_edition_kind)
        other,_,_,_=interpret("En édition Perfect uniquement",initial)
        self.assertEqual(other.preferred_edition_kind,"PERFECT")
        self.assertTrue(other.require_edition_kind)

    def test_soft_preference_boosts_edition_without_inventing_source(self):
        ctx=AdvisorContext(mood="MYSTERY",preferred_edition_kind="DELUXE")
        rows=[
            {"id":1,"title":"A","genres":["Mystery"],"themes":[],
             "score":8.5,"popularity":1,"preferred_format_record_count":0},
            {"id":2,"title":"B","genres":["Mystery"],"themes":[],
             "score":8.2,"popularity":2,"preferred_format_record_count":2},
        ]
        picked=score_candidates(rows,ctx,{"genres":set(),"themes":set()},2)
        self.assertEqual([x["id"] for x in picked],[2,1])
        self.assertTrue(picked[0]["preferred_format_recorded"])
        self.assertFalse(picked[1]["preferred_format_recorded"])


if __name__=="__main__":
    unittest.main()
