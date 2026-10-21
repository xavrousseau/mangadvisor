"""Non-destructive regression checks for one Web UI and robust Docker API routing."""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WebProxyLifecycleTests(unittest.TestCase):
    def test_nginx_refreshes_docker_dns_and_preserves_api_route(self):
        nginx = (ROOT / "apps/web/nginx.conf").read_text(encoding="utf-8")
        self.assertIn("resolver 127.0.0.11", nginx)
        self.assertIn("valid=5s", nginx)
        self.assertIn("set $api_backend", nginx)
        self.assertIn("rewrite ^/api/(.*)$ /$1 break;", nginx)
        self.assertIn("proxy_pass http://$api_backend;", nginx)
        self.assertNotIn("proxy_pass http://api:8000/;", nginx)

    def test_historical_streamlit_is_opt_in_only(self):
        compose = (ROOT / "infra/compose/docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("\\n  ui:\\n", compose)
        stable = (ROOT / "infra/compose/docker-compose.local.yml").read_text("utf-8")
        self.assertNotIn("\\n  ui:\\n", stable)
        legacy = (ROOT / "infra/compose/docker-compose.dev.yml").read_text("utf-8")
        self.assertIn('profiles: ["legacy"]', legacy)
        app = (ROOT / "apps/web/assets/app.js").read_text(encoding="utf-8")
        self.assertNotIn("http://localhost:8502", app)
        self.assertNotIn("127.0.0.1:8502", app)

    def test_main_controller_stops_legacy_and_automatic_worker_safely(self):
        control = (ROOT / "cmd/control-center.ps1").read_text(encoding="utf-8")
        self.assertIn('legacyArgs+@("stop","ui")', control)
        self.assertIn('legacyArgs+@("rm","-f","ui")', control)
        self.assertIn('Compose @("--profile","automation","stop","catalog-sync")', control)
        self.assertIn("function Show-Docker-Logs", control)
        self.assertIn("function Show-Service-Status", control)
        self.assertIn("Load-Complete-MAL-Catalogue -InitialSetup", control)
        self.assertNotIn("down -v", control)
        self.assertNotIn("down --volumes", control)
        backup=(ROOT/"cmd/library-backup.ps1").read_text(encoding="utf-8")
        self.assertIn("--profile automation stop catalog-sync",backup)
        self.assertIn("/api/health",control)
        self.assertIn("/api/library?limit=1",control)


if __name__ == "__main__":
    unittest.main()
