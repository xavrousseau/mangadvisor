"""Unit safeguards for Mangadvisor 3.8 private and additive inventory import."""
import unittest
from fastapi import HTTPException
from apps.api.app.inventory_import import (
    parse_inventory, attach_inventory_matches, preview_hash, UNSPECIFIED,
)


CSV="""serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier;ligne_source;oeuvre_commune;edition_declaree;format_catalogue_provisoire
Demo (34 tomes);34;0;0;Inventaire!A29;Dragon Ball;Deluxe;PERFECT_A_VERIFIER
Demo (42 tomes);42;0;0;Inventaire!A30;Dragon Ball;Pastel;PASTEL
Other;8;1;2;Inventaire!A31;;;
"""

CATALOG=[{"id":15,"title":"Dragon Ball","title_english":None,"title_japanese":None},
         {"id":31,"title":"Other","title_english":None,"title_japanese":None}]


class ImportInventoryTests(unittest.TestCase):
    def test_actual_quantity_and_edition_semantics(self):
        rows=parse_inventory(CSV)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["main_volumes"],34)
        self.assertEqual(rows[1]["main_volumes"],42)
        self.assertNotEqual(rows[0]["edition_key"],rows[1]["edition_key"])
        self.assertEqual(rows[0]["search_title"],"Dragon Ball")
        self.assertEqual(rows[2]["edition_key"],UNSPECIFIED)
        self.assertIsNone(rows[2]["edition_declared"])
        self.assertEqual(rows[2]["other_editions_unknown"],2)

    def test_matching_is_unique_and_never_fuses_physical_editions(self):
        report=attach_inventory_matches(parse_inventory(CSV),CATALOG,[],[])
        self.assertEqual(report["ready"],3)
        self.assertEqual(report["review"],0)
        self.assertEqual(report["declared_physical_volumes"],87)
        self.assertEqual([r["manga_id"] for r in report["items"]],[15,15,31])
        self.assertTrue(all(r["status"]=="READY" for r in report["items"]))
        self.assertEqual(len(preview_hash(report,1)),64)

    def test_existing_entries_idempotent_and_changed_counts_blocked(self):
        rows=parse_inventory(CSV)
        existing=[{**rows[0],"manga_id":15}]
        report=attach_inventory_matches(rows,CATALOG,existing,[])
        self.assertEqual(report["items"][0]["status"],"UNCHANGED")
        changed=[{**existing[0],"main_volumes":35}]
        report=attach_inventory_matches(rows,CATALOG,changed,[])
        self.assertEqual(report["items"][0]["status"],"REVIEW_EXISTING")

    def test_ambiguous_and_missing_title_do_not_import(self):
        rows=parse_inventory(CSV)
        catalog=CATALOG+[{"id":33,"title":"Dragon Ball","title_english":None,"title_japanese":None}]
        report=attach_inventory_matches(rows,catalog,[],[])
        self.assertEqual([x["status"] for x in report["items"][:2]],
                         ["REVIEW_AMBIGUOUS","REVIEW_AMBIGUOUS"])
        self.assertEqual(report["items"][0]["manga_id"],None)
        gone=attach_inventory_matches(rows,[],[],[])
        self.assertEqual(gone["ready"],0)
        self.assertEqual(gone["review"],3)

    def test_duplicate_same_edition_or_unlabeled_collisions_block_all(self):
        rows=parse_inventory(CSV)
        rows.append({**rows[0],"entry_title":"another label","line":20})
        result=attach_inventory_matches(rows,CATALOG,[],[])
        self.assertEqual(result["items"][0]["status"],"REVIEW_DUPLICATE_EDITION")
        self.assertEqual(result["items"][3]["status"],"REVIEW_DUPLICATE_EDITION")
        self.assertEqual(result["ready"],2)

    def test_rejected_library_entry_never_overwritten(self):
        result=attach_inventory_matches(parse_inventory(CSV),CATALOG,[],
            [{"manga_id":15,"library_status":"NOT_INTERESTED"}])
        self.assertEqual(result["items"][0]["status"],"REVIEW_LIBRARY_CONFLICT")
        self.assertEqual(result["items"][1]["status"],"REVIEW_LIBRARY_CONFLICT")

    def test_confirmations_include_all_catalog_and_current_state(self):
        rows=parse_inventory(CSV)
        base=attach_inventory_matches(rows,CATALOG,[],[])
        changed=attach_inventory_matches(rows,CATALOG,[],
                                        [{"manga_id":15,"library_status":"READ"}])
        self.assertNotEqual(preview_hash(base,1),preview_hash(changed,1))
        self.assertNotEqual(preview_hash(base,1),preview_hash(base,2))

    def test_malformed_or_ambiguous_inventory_is_rejected(self):
        bad=[
            CSV.replace(";34;0;0;", ";-3;0;0;"),
            CSV.replace("Demo (34 tomes);", ";"),
            CSV.replace("Dragon Ball;Deluxe;", "Dragon Ball;;"),
            CSV.replace("serie;tomes_principaux", "serie;serie;tomes_principaux"),
            CSV.replace(";34;0;0;", ";0;0;0;"),
            CSV+"x;1;1;1;F;Dragon Ball;;\n",
        ]
        for sample in bad:
            with self.subTest(sample=sample[:80]):
                with self.assertRaises((ValueError,HTTPException)):
                    parse_inventory(sample)


if __name__=="__main__":
    unittest.main()
