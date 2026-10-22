"""Windows entry point for one-shot sandbox bibliography recipe (static contract)."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BibliographyAcceptanceLauncherTests(unittest.TestCase):
    def test_advanced_menu_exposes_one_click_sandbox_recipe(self):
        cmd = (ROOT / "mangadvisor.cmd").read_text(encoding="utf-8-sig")
        self.assertIn("24 - Recette bibliographique complete", cmd)
        self.assertIn('if "%CHOICE%"=="24" set "KEY=bibliography-acceptance"', cmd)
        self.assertIn('if /I "%~1"=="bibliography-acceptance" set "ACTION=BibliographyAcceptance"', cmd)

    def test_recipe_stays_on_sandbox_without_inventory_mutation(self):
        script = (ROOT / "cmd" / "control-center.ps1").read_text(encoding="utf-8-sig")
        start = script.index("function Run-Bibliography-Acceptance")
        end = script.index("function Enrich-BnF", start)
        recipe = script[start:end]
        self.assertIn(".env.sandbox", recipe)
        self.assertIn("docker-compose.sandbox.yml", recipe)
        self.assertIn("POSTGRES_DB=mangadvisor_realtest", recipe)
        self.assertIn("--manga-ids", recipe)
        self.assertIn("49271,11,51119", recipe)
        self.assertIn("--report-only", recipe)
        self.assertIn("--probe-scrinis", recipe)
        self.assertIn("data\\logs\\bibliography_validation", recipe)
        self.assertNotIn("Backup", recipe)
        self.assertNotIn("TRUNCATE", recipe)
        self.assertNotIn("DELETE FROM", recipe)
        self.assertNotIn("UPDATE manga", recipe)


if __name__ == "__main__":
    unittest.main()
