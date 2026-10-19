"""CI tests use fictional titles; the private collection is NEVER in Git."""
from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC=Path(__file__).resolve().parents[1]/"cmd/evaluate-private-library.py"
spec=importlib.util.spec_from_file_location("private_collection_eval",SRC)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class LocalCollectionTests(unittest.TestCase):
    def test_accents_punctuation_and_unverified_format(self):
        self.assertEqual(mod.norm("L'Étoile — ★"),"l etoile")
        self.assertEqual(mod.search_title("Example A (42 tomes)"),("Example A",True))
        status,id_,name=mod.match_catalog_entry("Example A (42 tomes)",[
            {"id":4,"title":"Example A","title_english":None}])
        self.assertEqual(status,"FORMAT_TO_VERIFY")
        self.assertIsNone(id_)
        self.assertEqual(name,"Example A")

    def test_unique_exact_match_is_safe_and_multiple_matches_unresolved(self):
        source=[{"id":1,"title":"L'Étoile","title_english":"The Star"},
                {"id":2,"title":"Another Story","title_english":None}]
        status,id_,name=mod.match_catalog_entry("The Star",source)
        self.assertEqual((status,id_),("EXACT_TITLE",1))
        ambiguous=mod.match_catalog_entry("The Star",source+[
            {"id":9,"title":"The Star","title_english":None}])
        self.assertEqual(ambiguous[0],"AMBIGUOUS")
        self.assertIsNone(ambiguous[1])
        self.assertEqual(mod.match_catalog_entry("Nope",[])[0],"NOT_FOUND")
        self.assertEqual(mod.match_catalog_entry("Example Name",source)[0],"TO_VERIFY")

    def test_reads_private_csv_without_invented_ownership_status(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"reference.csv"
            file.write_text(
                "titre;tomes_principaux_declares;doublons_identiques_hors_profil;"
                "autres_editions_non_identifiees\n"
                "Example One;3;1;0\nExample Two;4;0;2\n",
                encoding="utf-8-sig",
            )
            items=mod.load_inventory(file)
        self.assertEqual(len(items),2)
        self.assertEqual(items[0]["tomes_principaux_declares"],3)
        self.assertEqual(items[1]["autres_editions_non_identifiees"],2)
        self.assertNotIn("user_score",items[0])

    def test_read_only_api_only_and_recommendation_overlap(self):
        inventory=[
            {"titre":"Example One","tomes_principaux_declares":3,
             "doublons_identiques_hors_profil":1,
             "autres_editions_non_identifiees":0},
            {"titre":"Example Two (12 tomes)","tomes_principaux_declares":12,
             "doublons_identiques_hors_profil":0,
             "autres_editions_non_identifiees":0},
        ]
        calls=[]
        def synthetic(base,endpoint,payload=None):
            calls.append((endpoint,payload))
            if endpoint=="/health":
                return {"status":"ok"}
            if endpoint.startswith("/library?"):
                return {"items":[{"manga_id":1}]}
            if endpoint.startswith("/mangas?"):
                if "Example+One" in endpoint:
                    return {"items":[{"id":1,"title":"Example One"}]}
                return {"items":[{"id":2,"title":"Example Two"}]}
            if endpoint=="/advisor/message":
                return {"status":"results","recommendations":[{"id":1,"title":"Example One"},
                                                            {"id":2,"title":"Example Two"}]}
            raise AssertionError("Unexpected endpoint "+endpoint)
        with patch.object(mod,"request_json",side_effect=synthetic):
            report,rows=mod.analyze("http://127.0.0.1:8000",inventory)
        self.assertEqual(report["series_identifiees_catalogue"],1)
        self.assertEqual(report["series_identifiees_absentes_de_la_bibliotheque_app"],0)
        self.assertEqual(len(report["titre_possede_recommande_malgre_identifiant_confirme"]),3)
        self.assertEqual(rows[1]["correspondance"],"FORMAT_TO_VERIFY")
        self.assertEqual(rows[1]["present_dans_bibliotheque_app"],"INDETERMINE")
        self.assertTrue(all(payload is None or endpoint=="/advisor/message"
                            for endpoint,payload in calls))
        self.assertTrue(all(endpoint.startswith(("/health","/mangas?","/library?","/advisor/message"))
                            for endpoint,_ in calls))


if __name__=="__main__":
    unittest.main()
