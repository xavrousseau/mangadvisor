"""Offline regressions for the guided recommendation extraction and personal audit."""
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipelines.engine.scripts import extract_jikan_recommendations as recommendations

ROOT = Path(__file__).resolve().parents[1]


class RecommendationIngestionHealthTests(unittest.TestCase):
    def run_extractor(self, effects: list[object]) -> tuple[int, str]:
        mangas = [
            {"id": idx + 1, "source_mal_id": 100 + idx, "title": f"Test {idx}"}
            for idx in range(len(effects))
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(recommendations, "RAW_RECOMMENDATIONS_DIR", Path(directory)),
                patch.object(recommendations, "get_mangas_to_enrich", return_value=mangas),
                patch.object(recommendations, "extract_recommendations_for_manga", side_effect=effects),
                patch("sys.argv", ["extract_jikan_recommendations.py", "--limit-items", "2", "--sleep-seconds", "0"]),
                redirect_stdout(out),
            ):
                code = recommendations.main()
        return code, out.getvalue()

    def test_complete_provider_outage_returns_error(self):
        code, message = self.run_extractor([ConnectionError("fournisseur inaccessible")] * 2)
        self.assertEqual(code, 1)
        self.assertIn("ECHEC", message)
        self.assertIn("option 29", message)

    def test_partial_success_is_visible_and_retriable(self):
        code, message = self.run_extractor([(True, 3), ConnectionError("quota fournisseur")])
        self.assertEqual(code, 0)
        self.assertIn("ATTENTION", message)
        self.assertIn("option 26", message)

    def test_cached_data_counts_as_usable_without_network(self):
        code, message = self.run_extractor([(False, 2), (False, 0)])
        self.assertEqual(code, 0)
        self.assertNotIn("ECHEC", message)
        self.assertNotIn("ATTENTION", message)

    def test_guided_wizard_backs_up_before_quality_audit(self):
        script = (ROOT / "cmd/control-center.ps1").read_text(encoding="utf-8")
        wizard = script.split("function Wizard {", 1)[1].split("\ntry {\n  switch ($Action)", 1)[0]
        # Earlier setup phases have their own diagnostic and backup. Compare
        # only the post-import tail, which must protect the newly owned items.
        post_import = wizard[wizard.index("  Inventory\n"):]
        phases = ["  Inventory\n", "  Backup\n", "  Diagnostic\n", "    Benchmark-Inventory\n"]
        offsets = [post_import.index(phase) for phase in phases]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn('Join-Path $root "private-data\\mangatheque.csv"', script)
        self.assertIn('cmd\\benchmark-mangatheque.ps1', script)
        self.assertIn("Benchmark facultatif non abouti", wizard)
        self.assertIn("Relance l'option 20", wizard)


if __name__ == "__main__":
    unittest.main()
