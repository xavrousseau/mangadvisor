"""One supported UI: no residual Streamlit app even in development."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class SingleWebStackTests(unittest.TestCase):
    def test_stable_compose_has_one_ui_no_source_reload(self):
        base=(ROOT/"infra/compose/docker-compose.yml").read_text("utf-8")
        local=(ROOT/"infra/compose/docker-compose.local.yml").read_text("utf-8")
        dev=(ROOT/"infra/compose/docker-compose.dev.yml").read_text("utf-8")
        self.assertNotIn("\n  ui:\n",base)
        self.assertNotIn("\n  ui:\n",local)
        self.assertIn("\n  web:\n",base)
        self.assertIn("127.0.0.1:"+ "$"+"{UI_PORT}:80",local)
        self.assertNotIn("--reload",local)
        self.assertNotIn("/workspace",local.split("\n  api:",1)[1].split("\n  web:",1)[0])
        self.assertIn("../../data/raw:/workspace/data/raw",local)
        self.assertNotIn("\\n  ui:\\n",dev)
        self.assertNotIn("8502",dev)
        self.assertIn("--reload",dev)

    def test_every_normal_windows_entrypoint_uses_stable_compose(self):
        for rel in ("cmd/common.cmd","cmd/control-center.ps1",
                    "cmd/ai-setup.ps1","cmd/mobile-setup.ps1",
                    "cmd/library-backup.ps1"):
            source=(ROOT/rel).read_text("utf-8")
            with self.subTest(rel=rel):
                self.assertIn("docker-compose.local.yml",source)
        self.assertIn("COMPOSE_FILE_2",(ROOT/"cmd/common.cmd").read_text("utf-8"))

    def test_no_legacy_ui_entrypoint_or_service(self):
        for rel in ("cmd/up.cmd", "cmd/start.cmd", "cmd/restart.cmd"):
            source=(ROOT/rel).read_text("utf-8")
            self.assertNotIn("retire-legacy-ui.cmd", source)
        ps=(ROOT/"cmd/control-center.ps1").read_text("utf-8")
        self.assertNotIn('"legacyArgs"',ps)
        self.assertFalse((ROOT/"infra/docker/ui/Dockerfile").exists())
        self.assertFalse((ROOT/"apps/ui").exists())

    def test_personal_resources_stay_persistent(self):
        base=(ROOT/"infra/compose/docker-compose.yml").read_text("utf-8")
        for name in ("mangadvisor_pgdata:/var/lib/postgresql/data",
                     "mangadvisor_meili:/meili_data",
                     "mangadvisor_ollama_models:/root/.ollama"):
            self.assertIn(name,base)


if __name__=="__main__":
    unittest.main()
