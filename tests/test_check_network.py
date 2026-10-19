"""Offline unit tests for the configured manga API connectivity check."""
from __future__ import annotations

import errno
import io
import socket
import unittest
from unittest.mock import Mock, patch

from pipelines.engine.scripts.check_network import api_base, check_https, check_provider, main


class NetworkCheckTests(unittest.TestCase):
    @patch("pipelines.engine.scripts.check_network.socket.getaddrinfo")
    def test_dns_failure_explained(self, getaddrinfo):
        getaddrinfo.side_effect = socket.gaierror("lookup failure")
        ok, message = check_https("api.tenrai.org")
        self.assertFalse(ok)
        self.assertIn("DNS", message)

    @patch("pipelines.engine.scripts.check_network.socket.getaddrinfo")
    @patch("pipelines.engine.scripts.check_network.socket.create_connection")
    def test_network_unreachable_explained(self, create_connection, getaddrinfo):
        getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", 443))]
        create_connection.side_effect = OSError(errno.ENETUNREACH, "Network is unreachable")
        ok, message = check_https("api.tenrai.org")
        self.assertFalse(ok)
        self.assertIn("Reseau injoignable", message)

    @patch.dict("os.environ", {}, clear=True)
    def test_tenrai_is_default(self):
        self.assertEqual(api_base(), "https://api.tenrai.org/v1")

    @patch.dict("os.environ", {"MANGA_API_BASE_URL": "https://api.jikan.moe/v4"})
    def test_discontinued_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "arrete"):
            api_base()

    @patch("pipelines.engine.scripts.check_network.requests.get")
    def test_provider_requires_real_manga(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"data": [{"mal_id": 2, "title": "Berserk"}]}
        self.assertTrue(check_provider("https://api.tenrai.org/v1")[0])
        get.return_value.json.return_value = {"data": [{"oops": "broken"}]}
        self.assertFalse(check_provider("https://api.tenrai.org/v1")[0])

    @patch("pipelines.engine.scripts.check_network.check_https")
    def test_main_fails_safely_and_explains_next_steps(self, check):
        check.side_effect = [(False, "Internet inaccessible"), (False, "Tenrai inaccessible")]
        with patch("sys.stdout", new_callable=io.StringIO) as capture:
            code = main()
        self.assertEqual(code, 2)
        self.assertIn("Restart Docker Desktop", capture.getvalue())
        self.assertIn("Ne pas lancer Nuke", capture.getvalue())

    @patch("pipelines.engine.scripts.check_network.check_provider")
    @patch("pipelines.engine.scripts.check_network.check_https")
    def test_api_manga_response_required(self, check, provider):
        check.side_effect = [(False, "example blocked"), (True, "Tenrai HTTPS OK")]
        provider.return_value = (False, "Bad JSON")
        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(main(), 2)

    @patch("pipelines.engine.scripts.check_network.check_provider")
    @patch("pipelines.engine.scripts.check_network.check_https")
    def test_provider_online_is_sufficient(self, check, provider):
        check.side_effect = [(False, "Test site bloque"), (True, "Tenrai HTTPS OK")]
        provider.return_value = (True, "API OK")
        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
