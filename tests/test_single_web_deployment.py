"""One supported end-user WEB stack; Streamlit is DEV/CI reference only."""
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
        self.assertIn('profiles: ["legacy"]',dev)
        self.assertIn("8502",dev)
        self.assertIn("--reload",dev)

    def test_every_normal_windows_entrypoint_uses_stable_compose(self):
        for rel in ("cmd/common.cmd","cmd/control-center.ps1",
                    "cmd/ai-setup.ps1","cmd/mobile-setup.ps1",
                    "cmd/library-backup.ps1"):
            source=(ROOT/rel).read_text("utf-8")
            with self.subTest(rel=rel):
                self.assertIn("docker-compose.local.yml",source)
        self.assertIn("COMPOSE_FILE_2",(ROOT/"cmd/common.cmd").read_text("utf-8"))

    def test_only_legacy_migration_can_remove_legacy_container(self):
        script=(ROOT/"cmd/retire-legacy-ui.cmd").read_text("utf-8")
        self.assertIn("--profile legacy stop ui",script)
        self.assertIn("--profile legacy rm -f ui",script)
        self.assertNotIn("--volumes",script)
        self.assertNotIn("down -v",script)
        self.assertNotIn("volume rm",script)
        for rel in ("cmd/up.cmd","cmd/start.cmd","cmd/restart.cmd"):
            self.assertIn("retire-legacy-ui.cmd",(ROOT/rel).read_text("utf-8"))
        ps=(ROOT/"cmd/control-center.ps1").read_text("utf-8")
        self.assertIn('legacyArgs+@("rm","-f","ui")',ps)
        backup=(ROOT/"cmd/library-backup.ps1").read_text("utf-8")
        self.assertIn("stop api web engine",backup)
        self.assertNotIn("stop api web ui engine",backup)

    def test_personal_resources_stay_persistent(self):
        base=(ROOT/"infra/compose/docker-compose.yml").read_text("utf-8")
        for name in ("mangadvisor_pgdata:/var/lib/postgresql/data",
                     "mangadvisor_meili:/meili_data",
                     "mangadvisor_ollama_models:/root/.ollama"):
            self.assertIn(name,base)


if __name__=="__main__":
    unittest.main()
