"""Safety gates for the last legacy pipeline and the current Docker boot."""
import unittest
from pathlib import Path
from unittest.mock import patch

from pipelines.engine.scripts import run_jikan_pipeline

ROOT=Path(__file__).resolve().parents[1]


class StabilisationSafetyTests(unittest.TestCase):
    def test_legacy_reset_is_refused_before_any_file_or_database_operation(self):
        with patch("sys.argv",["run_jikan_pipeline.py","--reset-db"]):
            with patch.object(run_jikan_pipeline,"run_python_script") as launch:
                with self.assertRaisesRegex(ValueError,"desactive"):
                    run_jikan_pipeline.main()
                launch.assert_not_called()

    def test_backup_restore_does_not_revive_legacy_streamlit(self):
        source=(ROOT/"cmd/library-backup.ps1").read_text("utf-8")
        self.assertIn("user_manga_inventory_pending",source)
        self.assertIn("user_manga_inventory_declaration",source)
        self.assertIn("stop api web engine",source)
        self.assertIn("up -d api web",source)
        self.assertNotIn("up -d api web ui",source)

    def test_docker_web_only_starts_after_api_becomes_healthy(self):
        compose=(ROOT/"infra/compose/docker-compose.yml").read_text("utf-8")
        api=compose.split("\n  api:\n",1)[1].split("\n  ollama:\n",1)[0]
        web=compose.split("\n  web:\n",1)[1].split("\n  engine:\n",1)[0]
        self.assertIn("healthcheck:",api)
        self.assertIn("127.0.0.1:8000/health",api)
        self.assertIn("condition: service_healthy",web)


if __name__=="__main__":
    unittest.main()
