"""Safety contracts for the independent Windows sandbox checkout."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SandboxIsolationTests(unittest.TestCase):
    def test_separate_compose_project_containers_and_network(self):
        override = (ROOT/"infra/compose/docker-compose.sandbox.yml").read_text("utf-8")
        self.assertIn("name: mangadvisor_sandbox", override)
        self.assertIn("name: mangadvisor_sandbox_network", override)
        for service in ("postgres", "meilisearch", "api", "web", "engine", "ollama", "catalog_sync"):
            self.assertIn("container_name: mangadvisor_sandbox_" + service, override)
        self.assertIn("POSTGRES_DB: mangadvisor_realtest", override)
        self.assertIn("manga_sandbox_raw:/workspace/data/raw", override)
        self.assertIn("manga_sandbox_logs:/workspace/data/logs", override)
        self.assertNotIn("../../data/logs:", override)
        self.assertNotIn("../../data/raw:", override)
        self.assertNotIn("external: true", override)
        self.assertNotIn("mangadvisor_pgdata:", override)
        self.assertNotIn("mangadvisor_meili:", override)

    def test_credentials_are_generated_locally_and_ignored(self):
        script = (ROOT/"cmd/setup-sandbox.ps1").read_text("utf-8")
        guard = (ROOT/"cmd/environment-safety.ps1").read_text("utf-8")
        ignored = (ROOT/".gitignore").read_text("utf-8")
        self.assertIn(".env.sandbox", ignored)
        self.assertIn("New-Key", script)
        self.assertIn("mangadvisor-test", script)
        self.assertIn("Assert-MangadvisorSandboxCompose", script)
        self.assertIn('--profile automation --profile ai config --format json', guard)
        self.assertIn("Assert-MangadvisorSandboxConfig", guard)
        self.assertNotIn('down -v', script)
        self.assertNotIn('docker rm', script)
        self.assertNotIn('docker volume rm', script)
        self.assertNotIn('up -d', script)
        self.assertLess(script.index('Assert-MangadvisorSandboxCompose $composeArgs'),
                        script.index('[IO.File]::Open'))
        self.assertIn('[IO.FileMode]::CreateNew', script)

if __name__=="__main__":
    unittest.main()
