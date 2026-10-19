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
        self.assertIn('profiles: ["legacy"]', compose)
        app = (ROOT / "apps/web/assets/app.js").read_text(encoding="utf-8")
        self.assertNotIn("http://localhost:8502", app)
        self.assertNotIn("127.0.0.1:8502", app)

    def test_menu_stops_legacy_without_removing_volumes(self):
        for relative in ("cmd/start.cmd", "cmd/up.cmd", "cmd/restart.cmd"):
            with self.subTest(script=relative):
                code = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("--profile legacy stop ui", code)
                self.assertNotIn("down -v", code)
                self.assertNotIn("volume rm", code)
        control = (ROOT / "cmd/control-center.ps1").read_text(encoding="utf-8")
        self.assertIn('Compose @("--profile","legacy","stop","ui")', control)
        self.assertIn('"/api/health"', control)
        self.assertIn('"/api/library?limit=1"', control)
        self.assertNotIn("down -v", control)


if __name__ == "__main__":
    unittest.main()
