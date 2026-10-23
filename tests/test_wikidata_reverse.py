"""Validate opt-in Wikidata P4087 reverse title discovery without network calls."""
from __future__ import annotations
import unittest
from unittest.mock import patch,MagicMock

from apps.api.app.wikidata_reverse import sparql_exact_title,parse_reverse_result,search_wikidata_mal_titles
from fastapi import HTTPException


class ReverseLinkTests(unittest.TestCase):
    def test_exact_title_query_uses_fr_en_and_no_interpolation(self):
        q=sparql_exact_title('Adieu Eri')
        self.assertIn('"Adieu Eri"@fr',q)
        self.assertIn('"Adieu Eri"@en',q)
        self.assertIn("P4087",q)
        injected=sparql_exact_title('abc" } UNION { ?x ?y ?z')
        self.assertIn('abc\\"',injected)
        with self.assertRaises(ValueError):
            sparql_exact_title('a')

    def test_external_mal_ids_must_be_valid_and_are_not_links_to_owner(self):
        data={"results":{"bindings":[
            {"item":{"value":"https://www.wikidata.org/entity/Q1234"},
             "malId":{"value":"145863"}},
            {"item":{"value":"https://www.wikidata.org/entity/Q1234"},
             "malId":{"value":"145863"}},
            {"item":{"value":"https://www.wikidata.org/entity/Q2"},
             "malId":{"value":"invalid"}},
        ]}}
        parsed=parse_reverse_result(data)
        self.assertEqual(parsed["status"],"EXACT_LABEL_CROSS_ID_CANDIDATES")
        self.assertEqual(len(parsed["items"]),1)
        self.assertEqual(parsed["items"][0]["source_mal_id"],145863)
        self.assertFalse(parsed["items"][0]["work_identity_confirmed"])

    def test_missing_and_overlarge_responses_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_reverse_result({})
        src={"results":{"bindings":[
            {"item":{"value":"https://www.wikidata.org/entity/Q1"},
             "malId":{"value":"1"}} for _ in range(26)
        ]}}
        response=parse_reverse_result(src)
        self.assertEqual(response["status"],"TRUNCATED_REVIEW")
        self.assertTrue(response["truncated"])
        self.assertEqual(response["items"],[])

    def test_provider_failure_returns_503_not_an_invented_no_match(self):
        import urllib.error
        with patch("apps.api.app.wikidata_reverse.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("network")):
            with self.assertRaises(HTTPException) as cm:
                search_wikidata_mal_titles("Adieu Eri")
        self.assertEqual(cm.exception.status_code,503)


if __name__ == "__main__":
    unittest.main()
