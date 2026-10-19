"""Read-only declared physical inventory must not be confused with ISBNs."""
import unittest

from apps.api.app.inventory_import import summarize_declarations


class PhysicalInventorySummaryTests(unittest.TestCase):
    def test_distinct_editions_counted_as_one_work_but_separate_physical_entries(self):
        rows=[
            {"manga_id":7,"edition_declared":"Pastel",
             "main_volumes":42,"duplicate_copies":0,"other_editions_unknown":0},
            {"manga_id":7,"edition_declared":"Deluxe",
             "main_volumes":34,"duplicate_copies":1,"other_editions_unknown":0},
            {"manga_id":19,"edition_declared":None,
             "main_volumes":2,"duplicate_copies":0,"other_editions_unknown":3},
        ]
        summary=summarize_declarations(rows)
        self.assertEqual(summary,{
            "works":2,"edition_entries":3,
            "main_volumes":78,"identical_duplicates":1,
            "other_editions_unidentified":3,
            "physical_total_declared":82,
        })

    def test_no_data_returns_zeros(self):
        self.assertEqual(summarize_declarations([]),{
            "works":0,"edition_entries":0,"main_volumes":0,
            "identical_duplicates":0,"other_editions_unidentified":0,
            "physical_total_declared":0,
        })

    def test_sourced_counts_are_not_ISBNs_or_read_volumes(self):
        result=summarize_declarations([{
            "manga_id":3,"main_volumes":9,"duplicate_copies":2,
            "other_editions_unknown":4,
        }])
        self.assertNotIn("read_volumes",result)
        self.assertNotIn("isbn_count",result)
        self.assertEqual(result["main_volumes"],9)
        self.assertEqual(result["physical_total_declared"],15)


if __name__=="__main__":
    unittest.main()
