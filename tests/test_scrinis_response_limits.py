"""Network-free HTTP response size regression for long-running Scrinis works."""
import json
import unittest

from pipelines.engine.scripts import benchmark_manga_sources_v2 as source


class Response:
    status_code = 200
    def __init__(self, payload):
        self.content = json.dumps(payload).encode("utf-8")


class Session:
    def __init__(self, response):
        self.response = response
    def get(self, *args, **kwargs):
        return self.response


class ResponseLimitsTests(unittest.TestCase):
    def test_scrinis_detail_can_exceed_generic_search_cap(self):
        body = {"public_n": 11, "titles": {"primary": "One Piece"},
                "padding": "x" * (source.MAX_RESPONSE + 5)}
        result = source.request_public(
            "scrinis", "detail", Session(Response(body)), identifier="11")
        self.assertEqual(result["status"], "OK")

    def test_scrinis_detail_is_still_bounded(self):
        body = {"public_n": 11, "titles": {"primary": "One Piece"},
                "padding": "x" * source.MAX_DETAIL_RESPONSE}
        result = source.request_public(
            "scrinis", "detail", Session(Response(body)), identifier="11")
        self.assertEqual(result["status"], "RESPONSE_TOO_LARGE")

    def test_search_still_uses_small_cap(self):
        body = {"results": [], "padding": "x" * source.MAX_RESPONSE}
        result = source.request_public(
            "scrinis", "search", Session(Response(body)), query="One Piece")
        self.assertEqual(result["status"], "RESPONSE_TOO_LARGE")


if __name__ == "__main__":
    unittest.main()
