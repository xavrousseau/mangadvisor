"""BnF SRU title search: suggestions only; never auto-confirm or write user data."""
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from apps.api.app.edition_discovery import (
    sanitize_title_query, extract_valid_isbns, parse_title_search_response,
    search_bnf_by_title, edition_discovery_router,
)

SAMPLE="""<?xml version="1.0" encoding="utf-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
 <srw:numberOfRecords>384</srw:numberOfRecords>
 <srw:records>
  <srw:record><srw:recordIdentifier>ark:/12148/cb12345678x</srw:recordIdentifier>
   <srw:recordData><dc:dc><dc:title>Monster. Tome 1</dc:title>
    <dc:creator>Naoki Urasawa</dc:creator><dc:publisher>Kana</dc:publisher>
    <dc:date>2001</dc:date><dc:language>français</dc:language>
    <dc:identifier>ISBN 978-2-87129-414-6</dc:identifier>
   </dc:dc></srw:recordData></srw:record>
  <srw:record><srw:recordIdentifier>ark:/12148/cb23456789a</srw:recordIdentifier>
   <srw:recordData><dc:dc><dc:title>Monster Perfect Edition, tome 1</dc:title>
    <dc:publisher>Kana</dc:publisher>
    <dc:identifier>ISBN 9782344074282</dc:identifier>
   </dc:dc></srw:recordData></srw:record>
 </srw:records>
</srw:searchRetrieveResponse>""".encode("utf-8")


class FakeCursor:
    def __init__(self, exists=True):
        self.exists=exists
        self.writes=[]
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params):
        if not sql.strip().upper().startswith("SELECT "):
            raise AssertionError("Title search must be READ ONLY")
        self.writes.append(sql)
    def fetchone(self):return {"id":1} if self.exists else None


class FakeConn:
    def __init__(self,exists=True):self.cursor_obj=FakeCursor(exists)
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return self.cursor_obj


class TestTitleDiscovery(unittest.TestCase):
    def test_first_page_candidate_and_provenance(self):
        result=parse_title_search_response(SAMPLE)
        self.assertEqual(result["count"],2)
        self.assertEqual(result["bnf_reported_records"],384)
        self.assertFalse(result["exhaustive"])
        self.assertTrue(result["candidate_only"])
        first=result["items"][0]
        self.assertEqual(first["isbn13"],"9782871294146")
        self.assertEqual(first["title_fr"],"Monster. Tome 1")
        self.assertEqual(first["publisher_fr"],"Kana")
        self.assertEqual(first["language_recorded"],"français")
        self.assertEqual(first["source_url"],"https://catalogue.bnf.fr/ark:/12148/cb12345678x")
        self.assertEqual(first["status"],"CANDIDATE_UNCONFIRMED")
        self.assertFalse(first["manga_match_verified"])
        self.assertEqual(result["items"][1]["edition_kind_suggested"],"PERFECT")

    def test_reject_unchecked_and_partial_identifiers(self):
        self.assertEqual(extract_valid_isbns(["ISBN 97828712941460","ISBN 978-2-87129-414-6"]),["9782871294146"])
        malformed=SAMPLE.replace(b"ark:/12148/cb12345678x",b"https://attacker.test/ark:/12148/cb12345678x")
        result=parse_title_search_response(malformed)
        self.assertEqual(result["count"],1)
        self.assertEqual(result["items"][0]["isbn13"],"9782344074282")

    def test_dedupe_and_limit(self):
        dup=SAMPLE.replace(b"9782344074282",b"9782871294146")
        result=parse_title_search_response(dup)
        self.assertEqual(result["count"],1)
        self.assertEqual(parse_title_search_response(SAMPLE,limit=1)["count"],1)

    def test_no_entities_or_xml_bombs(self):
        with self.assertRaises(ValueError):
            parse_title_search_response(b"<!DOCTYPE b [<!ENTITY x 'boom'>]>"+SAMPLE)
        with self.assertRaises(ValueError):
            parse_title_search_response(b" " * 1_500_001)

    def test_restrict_cql_injection_and_short_queries(self):
        for bad in ('x', ' ', '3', 'Monster" or bib.anywhere all "anything',
                    "Monster) and bib.title", "text\\some", "a"*91):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                sanitize_title_query(bad)
        self.assertEqual(sanitize_title_query("  L’Attaque    des Titans  "),"L’Attaque des Titans")

    def test_remote_page_two_requests_exact_bounded_sru_slice(self):
        from urllib.parse import urlsplit, parse_qs
        received=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,size):return SAMPLE
        def fake_get(request,timeout):
            received.append(parse_qs(urlsplit(request.full_url).query))
            self.assertEqual(timeout,9)
            return Response()
        with patch("apps.api.app.edition_discovery.urllib.request.urlopen",
                   side_effect=fake_get):
            found=search_bnf_by_title("Monster",start_record=21)
        self.assertEqual(received[0]["startRecord"],["21"])
        self.assertEqual(received[0]["maximumRecords"],["20"])
        self.assertEqual(found["bnf_start_record"],21)
        self.assertEqual(found["search_scope"],"requested_title_search_page")
        self.assertFalse(found["exhaustive"])
        self.assertFalse(found["items"][0]["manga_match_verified"])
        for start in (0,2,61,999999):
            with self.assertRaises(ValueError):
                search_bnf_by_title("Monster",start_record=start)

    def test_remote_unavailability_is_explicit(self):
        with patch("apps.api.app.edition_discovery.urllib.request.urlopen",side_effect=OSError("offline")):
            with self.assertRaises(HTTPException) as e:
                search_bnf_by_title("Monster")
        self.assertEqual(e.exception.status_code,503)

    def test_route_requires_known_manga_and_performs_no_writes(self):
        conn=FakeConn(True)
        router=edition_discovery_router(lambda:conn)
        handler=next(route.endpoint for route in router.routes if "GET" in route.methods)
        with patch("apps.api.app.edition_discovery.search_bnf_by_title",
                   return_value=parse_title_search_response(SAMPLE)) as searched:
            result=handler(1,"Monster")
        searched.assert_called_once_with("Monster")
        self.assertEqual(result["manga_id"],1)
        self.assertEqual(len(conn.cursor_obj.writes),1)
        self.assertTrue(result["candidate_only"])
        unknown=edition_discovery_router(lambda:FakeConn(False))
        handler2=next(route.endpoint for route in unknown.routes if "GET" in route.methods)
        with self.assertRaises(HTTPException) as error:
            handler2(999,"Monster")
        self.assertEqual(error.exception.status_code,404)


if __name__=="__main__":
    unittest.main()
