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
        self.assertNotIn("external: true", override)
        self.assertNotIn("mangadvisor_pgdata:", override)
        self.assertNotIn("mangadvisor_meili:", override)

    def test_credentials_are_generated_locally_and_ignored(self):
        script = (ROOT/"cmd/setup-sandbox.ps1").read_text("utf-8")
        ignored = (ROOT/".gitignore").read_text("utf-8")
        self.assertIn(".env.sandbox", ignored)
        self.assertIn("New-Key", script)
        self.assertIn("mangadvisor-test", script)
        self.assertIn("config", script)
        self.assertIn('"--profile", "automation", "--profile", "ai"', script)
        self.assertIn('$config.services.PSObject.Properties[$name]', script)
        self.assertIn('$null -eq $service', script)
        self.assertNotIn('down -v', script)
        self.assertNotIn('docker rm', script)
        self.assertNotIn('docker volume rm', script)
        self.assertNotIn('up -d', script)
        self.assertIn("mangadvisor_sandbox_mangadvisor_pgdata", script)
        self.assertIn("mangadvisor_sandbox_mangadvisor_meili", script)

if __name__=="__main__":
    unittest.main()
