"""Prevent Windows PowerShell 5.1 parser failures from UTF-8 without BOM.

On Windows PowerShell 5.1 a BOM-less script is decoded using the Windows
ANSI code page (usually CP1252), so UTF-8 punctuation inside strings may
be interpreted as closing quotation marks.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS_SCRIPTS = ROOT / "cmd"


class WindowsPowerShell51Compatibility(unittest.TestCase):
    def test_all_powershell_entrypoints_use_ascii_or_utf8_bom(self):
        scripts = sorted(PS_SCRIPTS.glob("*.ps1"))
        self.assertGreaterEqual(len(scripts), 5)
        for path in scripts:
            with self.subTest(script=path.name):
                payload = path.read_bytes()
                has_utf8_bom = payload.startswith(b"\xef\xbb\xbf")
                self.assertTrue(
                    has_utf8_bom or payload.isascii(),
                    f"{path}: UTF-8 sans BOM et caracteres non ASCII : "
                    "Windows PowerShell 5.1 peut refuser de parser ce script.",
                )

    def test_inventory_preview_stays_read_only(self):
        script = (PS_SCRIPTS / "import-private-inventory.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("if ($PreviewOnly)", script)
        self.assertIn('Mode APERCU : aucune modification de la base.', script)
        self.assertIn('Read-Host "Saisis exactement', script)
        self.assertIn('$api/inventory/preview', script)
        self.assertIn('$api/inventory/apply', script)


if __name__ == "__main__":
    unittest.main()
