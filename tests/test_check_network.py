"""Offline unit tests for the Jikan outbound-network preflight."""
from __future__ import annotations

import errno
import io
import socket
import unittest
from unittest.mock import patch

from pipelines.engine.scripts.check_network import check_https, main


class NetworkCheckTests(unittest.TestCase):
    @patch("pipelines.engine.scripts.check_network.socket.getaddrinfo")
    def test_dns_failure_explained(self, getaddrinfo):
        getaddrinfo.side_effect = socket.gaierror("lookup failure")
        ok, message = check_https("api.jikan.moe")
        self.assertFalse(ok)
        self.assertIn("DNS", message)

    @patch("pipelines.engine.scripts.check_network.socket.getaddrinfo")
    @patch("pipelines.engine.scripts.check_network.socket.create_connection")
    def test_network_unreachable_explained(self, create_connection, getaddrinfo):
        getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", 443))]
        create_connection.side_effect = OSError(errno.ENETUNREACH, "Network is unreachable")
        ok, message = check_https("api.jikan.moe")
        self.assertFalse(ok)
        self.assertIn("Reseau injoignable", message)

    @patch("pipelines.engine.scripts.check_network.check_https")
    def test_main_fails_safely_and_explains_next_steps(self, check):
        check.side_effect = [(False, "Internet inaccessible"), (False, "Jikan inaccessible")]
        with patch("sys.stdout", new_callable=io.StringIO) as capture:
            code = main()
        self.assertEqual(code, 2)
        self.assertIn("Restart Docker Desktop", capture.getvalue())
        self.assertIn("Ne pas lancer Nuke", capture.getvalue())

    @patch("pipelines.engine.scripts.check_network.check_https")
    def test_jikan_online_is_sufficient(self, check):
        check.side_effect = [(False, "Test site bloqué"), (True, "Jikan HTTPS OK")]
        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
