"""Prevent reintroducing historical duplicate entry points or archives.

These tests check only the tracked source checkout; private volumes/backups
are never examined, altered or deleted.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

RETIRED = (
    "_archive",
    "legacy",
    "cmd/archive-v0-8-temp-files.cmd",
    "cmd/audit-project-files.cmd",
    "cmd/run-jikan-catalog.cmd",
    "cmd/run-jikan-pipeline.cmd",
    "cmd/extract-jikan-recommendations.cmd",
    "cmd/load-jikan-recommendations.cmd",
    "cmd/rebuild-canonical-catalog.cmd",
    "cmd/diagnose-jikan-recommendations.cmd",
    "pipelines/engine/src/extract/jikan_client.py",
    "docs/reports/recommendation_profile_tests_v0_7_4.md",
    "docs/reports/project_file_audit_v0_8_13.txt",
)


class RepositoryHygieneTests(unittest.TestCase):
    def test_retired_files_are_not_reintroduced(self):
        for path in RETIRED:
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists(), f"Historical duplicate restored: {path}")

    def test_one_catalogue_menu_path(self):
        menu = (ROOT / "mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertIn('"25"', menu)
        self.assertIn(" -Action Catalogue", menu)
        self.assertNotIn(":jikan_menu", menu)
        self.assertNotIn("--reset-db", menu)
        self.assertNotIn("cmd\\run-jikan-pipeline.cmd", menu)

    def test_windows_menu_never_exits_an_unmatched_if(self):
        menu = (ROOT / "mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertNotRegex(
            menu,
            r'(?im)^if /I "(?:%CHOICE%|%~1)"=="[^"]+"[^\\n]*& goto (?:menu|:eof)\\s*
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for item in (".env", "private-data/", "backups/", ".env.mobile", "mobile-local/"):
            self.assertIn(item, gitignore)

    def test_recommendation_profile_has_only_one_output(self):
        report = (ROOT / "pipelines/engine/scripts/run_recommendation_profile_tests.py").read_text(encoding="utf-8")
        self.assertIn('recommendation_profile_tests_latest.md', report)
        self.assertNotIn('LEGACY_REPORT_PATH', report)
        self.assertNotIn('recommendation_profile_tests_v0_7_4.md', report)


if __name__ == "__main__":
    unittest.main()
,
        )

    def test_private_data_remain_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for item in (".env", "private-data/", "backups/", ".env.mobile", "mobile-local/"):
            self.assertIn(item, gitignore)

    def test_recommendation_profile_has_only_one_output(self):
        report = (ROOT / "pipelines/engine/scripts/run_recommendation_profile_tests.py").read_text(encoding="utf-8")
        self.assertIn('recommendation_profile_tests_latest.md', report)
        self.assertNotIn('LEGACY_REPORT_PATH', report)
        self.assertNotIn('recommendation_profile_tests_v0_7_4.md', report)


if __name__ == "__main__":
    unittest.main()
