"""Menu is a navigation surface, not a list of experiment milestones."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class UserMenuTests(unittest.TestCase):
    def setUp(self):
        self.source=(ROOT/"mangadvisor.cmd").read_text(encoding="utf-8")

    def test_user_space_has_four_understandable_destinations(self):
        header=self.source.split("\n:advanced\n",1)[1].split("\n:catalogue_menu\n",1)[0]
        for name in (
            "Catalogue general et recherche",
            "Ma bibliotheque et mes imports",
            "Fonctions facultatives",
            "Entretien, diagnostic et restauration",
        ):
            self.assertIn(name,header)
        self.assertNotIn("Actualiser les recommandations communautaires",header)
        self.assertNotIn("26 - Reconstruire",header)
        self.assertNotRegex(header,r"echo\s+2[0-6] - ")

    def test_only_clear_public_workflows_show_in_submenus(self):
        catalogue=self.source.split("\n:catalogue_menu\n",1)[1].split("\n:library_menu\n",1)[0]
        personal=self.source.split("\n:library_menu\n",1)[1].split("\n:optional_menu\n",1)[0]
        for label in ("Actualiser les mangas","moteur de recherche",
                      "Exporter la base bibliographique","Lire le bilan"):
            self.assertIn(label,catalogue)
        self.assertIn("Importer mon inventaire CSV",personal)
        self.assertIn("Simuler mon import sans rien modifier",personal)
        self.assertNotIn("BnF",personal)
        self.assertNotIn("Enrichir les fiches via la BnF",catalogue)

    def test_legacy_utilities_remain_available_as_direct_commands(self):
        for command in (
            "catalogue-source-graph","catalogue-export",
            "wikidata-enrich","bnf-enrich","catalogue-french-scrinis",
            "multilingual-aliases",
        ):
            self.assertIn('if /I "%~1"=="'+command+'"',self.source)
        self.assertIn('if /I "%~1"=="catalogue-graph-report"',self.source)
        report=(ROOT/"cmd/report-catalogue-source-graph.ps1").read_text(encoding="utf-8")
        self.assertIn("catalogue_source_graph_cli --report-only",report)
        self.assertNotIn("--apply",report)
        self.assertNotIn("docker compose down",report)


if __name__=="__main__":
    unittest.main()
