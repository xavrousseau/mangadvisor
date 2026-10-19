"""Protect the real library from catalog rebuilds and broken Windows DB config.

These tests run WITHOUT a PostgreSQL server. CI also executes the SQL
against a disposable PostgreSQL database to verify referential stability.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipelines.engine.src.load.postgres_loader import (
    get_postgres_connection,
    local_database_settings,
)
from pipelines.engine.scripts.load_jikan_recommendations_to_postgres import (
    upsert_recommendation_rows,
)

ROOT = Path(__file__).resolve().parents[1]


class RepositorySafetyTests(unittest.TestCase):
    def test_legacy_rebuild_scripts_never_truncate_canonical_library_tables(self):
        for path in (
            "sql/schema/003_build_canonical_from_jikan.sql",
            "sql/schema/005_build_theme_demographic_from_jikan.sql",
        ):
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8").upper()
                # Strip comments to avoid matching explanations of old mistakes.
                active = "\n".join(x.split("--", 1)[0] for x in text.splitlines())
                self.assertNotIn("TRUNCATE", active)
                self.assertNotIn("DROP TABLE", active)
                self.assertIn("ON CONFLICT", active)
                self.assertIn("BEGIN;", active)
                self.assertIn("COMMIT;", active)
        manga_sql=(ROOT/"sql/schema/003_build_canonical_from_jikan.sql").read_text()
        self.assertIn("ON CONFLICT (source_mal_id) DO UPDATE",manga_sql)
        self.assertNotIn("RESTART IDENTITY",manga_sql)

    def test_windows_catalog_menu_uses_safe_central_orchestrator(self):
        script=(ROOT/"mangadvisor.cmd").read_text(encoding="utf-8")
        self.assertIn('-Action Catalogue', script)
        self.assertNotIn('--reset-db', script)
        self.assertNotIn('cmd\\run-jikan-pipeline.cmd', script)

    def test_parser_handles_quotes_unicode_and_only_known_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            filename=Path(temp)/".env"
            filename.write_text(
                '# comment\nPOSTGRES_DB=real_db\nPOSTGRES_USER=manga_reader\n'
                'POSTGRES_PASSWORD="good!p@ss;=value"\nPOSTGRES_PORT=5435\n'
                'OLLAMA_MODEL=qwen2.5:3b\n',
                encoding="utf-8",
            )
            config=local_database_settings(filename)
        self.assertEqual(config,{
            "POSTGRES_DB":"real_db","POSTGRES_USER":"manga_reader",
            "POSTGRES_PASSWORD":"good!p@ss;=value","POSTGRES_PORT":"5435",
        })

    def test_system_environment_overrides_local_env_safely(self):
        env={
            "POSTGRES_DB":"ci_db","POSTGRES_USER":"ci_user",
            "POSTGRES_PASSWORD":"ci_password","POSTGRES_HOST":"postgres",
            "POSTGRES_PORT":"5432",
        }
        with patch.dict(os.environ,env), patch(
            "pipelines.engine.src.load.postgres_loader.local_database_settings",
            return_value={
                "POSTGRES_DB":"personal_db","POSTGRES_USER":"manga",
                "POSTGRES_PASSWORD":"personal_secret","POSTGRES_PORT":"7777",
            },
        ), patch("pipelines.engine.src.load.postgres_loader.psycopg.connect") as connect:
            get_postgres_connection()
        kwargs=connect.call_args.kwargs
        self.assertEqual(kwargs["dbname"],"ci_db")
        self.assertEqual(kwargs["user"],"ci_user")
        self.assertEqual(kwargs["password"],"ci_password")
        self.assertEqual(kwargs["host"],"postgres")
        self.assertEqual(kwargs["port"],"5432")

    def test_recommendation_reset_is_atomic_and_rejects_empty_source(self):
        class FakeCursor:
            def __init__(self, fail=False):
                self.commands=[]
                self.fail=fail
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self, statement):
                self.commands.append(statement.strip())
            def executemany(self, statement, rows):
                self.commands.append("INSERT_BATCH")
                if self.fail:
                    raise RuntimeError("Synthetic SQL failure")

        class FakeConnection:
            def __init__(self, fail=False):
                self.cur=FakeCursor(fail)
                self.commits=0
            def cursor(self):return self.cur
            def commit(self):self.commits+=1

        with self.assertRaisesRegex(ValueError,"Import vide"):
            upsert_recommendation_rows(FakeConnection(),[],reset=True)
        row={"source_manga_id":1,"recommended_mal_id":2,
             "recommended_manga_id":2,"recommended_title":"Synthetic",
             "votes":3,"raw_json":"{}"}
        success=FakeConnection()
        self.assertEqual(upsert_recommendation_rows(success,[row],reset=True),1)
        self.assertEqual(success.cur.commands[0],
                         "DELETE FROM manga_recommendation_edge;")
        self.assertEqual(success.cur.commands[1],"INSERT_BATCH")
        self.assertEqual(success.commits,1)

        failing=FakeConnection(fail=True)
        with self.assertRaisesRegex(RuntimeError,"Synthetic SQL failure"):
            upsert_recommendation_rows(failing,[row],reset=True)
        self.assertEqual(failing.commits,0)
        self.assertEqual(failing.cur.commands[0],
                         "DELETE FROM manga_recommendation_edge;")

    def test_missing_password_has_clear_failure_not_guess(self):
        env={k:v for k,v in os.environ.items() if not k.startswith("POSTGRES_")}
        with patch.dict(os.environ,env,clear=True), patch(
            "pipelines.engine.src.load.postgres_loader.local_database_settings",
            return_value={},
        ):
            with self.assertRaisesRegex(RuntimeError,"POSTGRES_PASSWORD absent"):
                get_postgres_connection()


if __name__ == "__main__":
    unittest.main()
