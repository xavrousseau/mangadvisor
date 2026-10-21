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

    def test_normal_windows_entrypoints_use_only_stable_compose(self):
        for rel in ("cmd/control-center.ps1","cmd/ai-setup.ps1",
                    "cmd/mobile-setup.ps1","cmd/library-backup.ps1"):
            source=(ROOT/rel).read_text("utf-8")
            with self.subTest(rel=rel):
                self.assertIn("docker-compose.local.yml",source)
        for obsolete in ("cmd/common.cmd","cmd/up.cmd","cmd/start.cmd",
                         "cmd/restart.cmd","cmd/retire-legacy-ui.cmd"):
            self.assertFalse((ROOT/obsolete).exists(),obsolete)

    def test_only_main_controller_migrates_legacy_ui_safely(self):
        ps=(ROOT/"cmd/control-center.ps1").read_text("utf-8")
        self.assertIn('legacyArgs+@("stop","ui")',ps)
        self.assertIn('legacyArgs+@("rm","-f","ui")',ps)
        self.assertNotIn("down --volumes",ps)
        self.assertNotIn("down -v",ps)
        backup=(ROOT/"cmd/library-backup.ps1").read_text("utf-8")
        self.assertIn("stop api web engine",backup)
        self.assertIn("--profile automation stop catalog-sync",backup)
        self.assertNotIn("stop api web ui engine",backup)

    def test_personal_resources_stay_persistent(self):
        base=(ROOT/"infra/compose/docker-compose.yml").read_text("utf-8")
        for name in ("mangadvisor_pgdata:/var/lib/postgresql/data",
                     "mangadvisor_meili:/meili_data",
                     "mangadvisor_ollama_models:/root/.ollama"):
            self.assertIn(name,base)


if __name__=="__main__":
    unittest.main()
