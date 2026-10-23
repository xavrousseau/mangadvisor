"""Prevent reintroducing historical duplicate entry points or archives.

These tests check only the tracked source checkout; private volumes/backups
are never examined, altered or deleted.
"""
from pathlib import Path
import unittest

from tools.audit_repository import has_compose_service

ROOT = Path(__file__).resolve().parents[1]

RETIRED = (
    "_archive",
    "legacy",
    "apps/ui",
    "infra/docker/ui/Dockerfile",
    "cmd/archive-v0-8-temp-files.cmd",
    "cmd/audit-project-files.cmd",
    "cmd/run-jikan-catalog.cmd",
    "cmd/run-jikan-pipeline.cmd",
    "cmd/extract-jikan-recommendations.cmd",
    "cmd/load-jikan-recommendations.cmd",
    "cmd/rebuild-canonical-catalog.cmd",
    "cmd/diagnose-jikan-recommendations.cmd",
    "cmd/build.cmd",
    "cmd/clean.cmd",
    "cmd/common.cmd",
    "cmd/down.cmd",
    "cmd/install-check.cmd",
    "cmd/logs.cmd",
    "cmd/nuke.cmd",
    "cmd/restart.cmd",
    "cmd/retire-legacy-ui.cmd",
    "cmd/run-library-goal-tests.cmd",
    "cmd/run-library-import-robustness-tests.cmd",
    "cmd/run-library-import-tests.cmd",
    "cmd/run-library-recommendation-tests.cmd",
    "cmd/run-library-status-tests.cmd",
    "cmd/run-recommendation-tests.cmd",
    "cmd/run-v0-8-validation.cmd",
    "cmd/start.cmd",
    "cmd/status.cmd",
    "cmd/stop.cmd",
    "cmd/up.cmd",
    "pipelines/engine/scripts/run_jikan_pipeline.py",
    "pipelines/engine/scripts/run_library_goal_tests.py",
    "pipelines/engine/scripts/run_library_import_robustness_tests.py",
    "pipelines/engine/scripts/run_library_import_tests.py",
    "pipelines/engine/scripts/run_library_recommendation_tests.py",
    "pipelines/engine/scripts/run_library_status_tests.py",
    "pipelines/engine/src/extract/jikan_client.py",
    "docs/reports/recommendation_profile_tests_v0_7_4.md",
    "docs/reports/project_file_audit_v0_8_13.txt",
)


class RepositoryHygieneTests(unittest.TestCase):
    def test_retired_files_are_not_reintroduced(self):
        for path in RETIRED:
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists(), f"Historical duplicate restored: {path}")

    def test_compose_service_detection_catches_retired_ui(self):
        self.assertTrue(has_compose_service("services:\n  ui:\n    image: old\n", "ui"))
        self.assertTrue(has_compose_service("services:\n  ui : {}\n", "ui"))
        self.assertFalse(has_compose_service("services:\n  ui_backup:\n", "ui"))
        self.assertFalse(has_compose_service("services:\n  web:\n", "ui"))

    def test_one_catalogue_menu_path(self):
        menu = (ROOT / "mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertIn('if "%CHOICE%"=="1" set "KEY=install"', menu)
        self.assertIn('if "%CHOICE%"=="2" set "KEY=start"', menu)
        self.assertIn('if "%CHOICE%"=="3" set "KEY=update"', menu)
        self.assertIn('if "%CHOICE%"=="4" set "KEY=backup"', menu)
        self.assertIn('if "%CHOICE%"=="5" set "KEY=diagnostic"', menu)
        self.assertIn('if "%CHOICE%"=="6" set "KEY=stop"', menu)
        self.assertIn('if /I "%~1"=="catalogue" set "ACTION=Catalogue"', menu)
        self.assertIn('if /I "%~1"=="logs" set "ACTION=Logs"', menu)
        self.assertIn('if /I "%~1"=="status" set "ACTION=Status"', menu)
        self.assertNotIn("CMD_SCRIPT", menu)
        self.assertIn("Load-Complete-MAL-Catalogue",
            (ROOT/"cmd/control-center.ps1").read_text(encoding="utf-8"))
        self.assertNotIn(" -Action Nuke", menu)
        self.assertIn('if "%CHOICE%"=="11" set "KEY=wikidata-enrich"', menu)
        self.assertNotIn('if "%CHOICE%"=="11" set "KEY=nuke"', menu)
        self.assertIn(':advanced', menu)
        self.assertIn(':maintenance', menu)
        self.assertNotIn(":jikan_menu", menu)
        self.assertNotIn("--reset-db", menu)
        self.assertNotIn("cmd\\run-jikan-pipeline.cmd", menu)

    def test_windows_menu_never_exits_an_unmatched_if(self):
        menu = (ROOT / "mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertNotRegex(
            menu,
            r'(?im)^if /I "(?:%CHOICE%|%~1)"=="[^"]+"[^\r\n]*& goto (?:menu|:eof)\s*$',
        )

    def test_active_launchers_never_call_retired_pipeline_scripts(self):
        """Historic prose may mention removed scripts; executable launchers may not."""
        old = (
            "run_jikan_pipeline.py",
            "run_library_goal_tests.py",
            "run_library_import_robustness_tests.py",
            "run_library_import_tests.py",
            "run_library_recommendation_tests.py",
            "run_library_status_tests.py",
        )
        candidates = [
            ROOT / "mangadvisor.cmd",
            *(ROOT / "cmd").glob("*.ps1"),
            *(ROOT / ".github/workflows").glob("*.yml"),
            *(ROOT / "tests/integration").glob("*.sh"),
            *(ROOT / "tests/smoke").glob("*.py"),
        ]
        for source in candidates:
            contents = source.read_text(encoding="utf-8")
            for script in old:
                with self.subTest(source=str(source.relative_to(ROOT)), script=script):
                    self.assertNotIn(script, contents)

    def test_private_data_remain_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for item in (".env", "private-data/", "backups/", ".env.mobile", "mobile-local/"):
            self.assertIn(item, gitignore)

    def test_docker_build_context_excludes_private_local_data(self):
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        entries = {line.strip() for line in dockerignore.splitlines()
                   if line.strip() and not line.lstrip().startswith("#")}
        for required in (".git", ".env", ".env.*", "private-data/",
                         "private-evaluations/", "backups/", "mobile-local/",
                         "data/raw/", "data/logs/", "data/staging/"):
            with self.subTest(path=required):
                self.assertIn(required, entries)
        for required in ("apps/api", "apps/web", "pipelines/engine"):
            self.assertNotIn(required, entries)
            self.assertNotIn(required + "/", entries)

    def test_runtime_diagnostics_never_overwrite_versioned_reports(self):
        for name in ("analyze_jikan_recommendation_edges.py",
                     "run_recommendation_profile_tests.py"):
            with self.subTest(name=name):
                text = (ROOT / "pipelines/engine/scripts" / name).read_text(
                    encoding="utf-8"
                )
                self.assertIn(' / "data" / "logs" / "diagnostics"', text)
                self.assertNotIn(' / "docs" / "reports"', text)
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/logs/*", ignore)

    def test_recommendation_profile_has_only_one_output(self):
        report = (ROOT / "pipelines/engine/scripts/run_recommendation_profile_tests.py").read_text(encoding="utf-8")
        self.assertIn('recommendation_profile_tests_latest.md', report)
        self.assertNotIn('LEGACY_REPORT_PATH', report)
        self.assertNotIn('recommendation_profile_tests_v0_7_4.md', report)


if __name__ == "__main__":
    unittest.main()
