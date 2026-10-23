"""Catalogue export remains data-safe: no owner data or binary stdout pipe."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicCatalogueExportTests(unittest.TestCase):
    def test_menu_has_one_click_safe_public_export(self):
        source=(ROOT/"mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertIn("25 - Exporter toute la base manga",source)
        self.assertIn('if "%CHOICE%"=="25" set "KEY=catalogue-export"',source)
        self.assertIn('if /I "%~1"=="catalogue-export" set "PS_SCRIPT=export-catalogue-public.ps1"',source)

    def test_only_whitelisted_bibliographic_tables_can_be_dumped(self):
        script=(ROOT/"cmd/export-catalogue-public.ps1").read_text(encoding="utf-8")
        whitelist=script.split("$publicTables = @(",1)[1].split("\n)",1)[0]
        names=re.findall(r'"([a-z_]+)"',whitelist)
        self.assertGreaterEqual(len(names),10)
        self.assertIn("manga",names)
        self.assertIn("manga_title_alias",names)
        self.assertIn("manga_bnf_candidate",names)
        self.assertIn("manga_fr_edition",names)
        self.assertIn("manga_wikidata_fact",names)
        for table in names:
            self.assertFalse(table.startswith(("user_","private_","pg_")))
        self.assertIn('Write-PublicDump "jikan_raw" @("jikan_manga_source")',script)

    def test_dump_uses_binary_docker_cp_and_checks_integrity(self):
        script=(ROOT/"cmd/export-catalogue-public.ps1").read_text(encoding="utf-8")
        self.assertIn('"pg_dump"',script)
        self.assertIn('"--no-owner","--no-privileges"',script)
        self.assertIn("pg_restore -l",script)
        self.assertIn("& docker cp",script)
        self.assertIn("Get-FileHash",script)
        self.assertIn("backups\\catalogue-public",script)
        self.assertNotIn("docker volume rm",script)
        self.assertNotIn("docker compose down",script)
        self.assertNotIn(' -c "DELETE ',script)
        self.assertNotIn(' -c "DROP ',script)
        self.assertIn('includes_personal_library=$false',script)
        self.assertIn('includes_passwords=$false',script)

    def test_every_single_dump_target_comes_from_allowlist(self):
        script=(ROOT/"cmd/export-catalogue-public.ps1").read_text(encoding="utf-8")
        self.assertIn('foreach ($table in $tables)',script)
        self.assertIn('"public." + $table',script)
        self.assertIn('$selected = @($publicTables | Where-Object',script)
        self.assertIn('if ($found -notcontains "manga"',script)


if __name__ == "__main__":
    unittest.main()
