"""Regression: production API image cannot import pipelines/engine modules.

The Windows A->26 action must run a CLI that exists in the *built* API image,
not merely a file exposed by CI's development-mode bind mount.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from apps.api.app import catalogue_source_graph_cli as cli

ROOT=Path(__file__).resolve().parents[1]


class DummyConnection:
    def __init__(self):
        self.commits=0
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def commit(self):self.commits+=1


class ProductionCatalogueGraphTests(unittest.TestCase):
    def test_windows_menu_targets_installed_api_cli(self):
        runner=(ROOT/"cmd/rebuild-catalogue-source-graph.ps1").read_text(
            encoding="utf-8")
        dockerfile=(ROOT/"infra/docker/api/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("python -m apps.api.app.catalogue_source_graph_cli --apply",runner)
        self.assertNotIn("python -m pipelines.engine.scripts",runner)
        self.assertIn("COPY apps/api /workspace/apps/api",dockerfile)
        # A local bind mount must not be required to make the CLI importable.
        self.assertNotIn("COPY pipelines",dockerfile)
        self.assertNotIn("pipelines.",Path(cli.__file__).read_text(encoding="utf-8"))

    def test_apply_calls_real_graph_rebuild_then_commits(self):
        db=DummyConnection()
        counts={"legacy_works":85776,"source_graph_initialized":1,
                "works":85776}
        output=io.StringIO()
        with (patch.object(cli,"connect_database",return_value=db),
              patch.object(cli,"ensure_schema") as schema,
              patch.object(cli,"rebuild_legacy_sources") as rebuild,
              patch.object(cli,"public_report",return_value=counts) as report,
              contextlib.redirect_stdout(output)):
            self.assertEqual(cli.main(["--apply"]),0)
        schema.assert_called_once_with(db)
        rebuild.assert_called_once_with(db)
        self.assertEqual(db.commits,1)
        self.assertEqual(report.call_count,2)
        self.assertIn('"mode": "APPLIED"',output.getvalue())
        self.assertIn('"external_api_requests": 0',output.getvalue())

    def test_report_only_never_executes_mutating_sql(self):
        db=DummyConnection()
        output=io.StringIO()
        with (patch.object(cli,"connect_database",return_value=db),
              patch.object(cli,"ensure_schema") as schema,
              patch.object(cli,"rebuild_legacy_sources") as rebuild,
              patch.object(cli,"public_report",
                           return_value={"legacy_works":85776,"source_graph_initialized":0}),
              contextlib.redirect_stdout(output)):
            self.assertEqual(cli.main(["--report-only"]),0)
        schema.assert_not_called()
        rebuild.assert_not_called()
        self.assertEqual(db.commits,0)
        self.assertIn('"mode": "READ_ONLY"',output.getvalue())

    def test_apply_and_report_only_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            cli.main(["--apply","--report-only"])


if __name__=="__main__":
    unittest.main()
