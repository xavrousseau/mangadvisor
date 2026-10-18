"""Discovery of French BnF ISBN book records, without invented volume links."""
import unittest
from unittest.mock import patch
from fastapi import HTTPException

from apps.api.app.edition_discovery import (
    clean_title_query, extract_valid_isbns, parse_title_results,
    lookup_title_records, create_edition_discovery_router,
)

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/"
xmlns:dc="http://purl.org/dc/elements/1.1/">
<srw:numberOfRecords>100</srw:numberOfRecords>
<srw:records>
<srw:record><srw:recordIdentifier>ark:/12148/cb11111111x</srw:recordIdentifier>
<srw:recordData><dc:dc>
<dc:title>Naruto. Tome 1</dc:title><dc:creator>Masashi Kishimoto</dc:creator>
<dc:publisher>Kana</dc:publisher><dc:date>2002</dc:date>
<dc:language>fre</dc:language>
<dc:identifier>ISBN 978-2-87129-414-6</dc:identifier>
</dc:dc></srw:recordData></srw:record>
<srw:record><srw:recordIdentifier>ark:/12148/cb22222222x</srw:recordIdentifier>
<srw:recordData><dc:dc>
<dc:title>Naruto Tome 2</dc:title><dc:publisher>Kana</dc:publisher>
<dc:identifier>ISBN 9782871294146</dc:identifier>
<dc:identifier>EAN 9782344074282</dc:identifier>
</dc:dc></srw:recordData></srw:record>
<srw:record><srw:recordIdentifier>https://evil.example/ark:/12148/cb3333333x</srw:recordIdentifier>
<srw:recordData><dc:dc>
<dc:title>Naruto Tome 3</dc:title>
<dc:identifier>ISBN 9782344074282</dc:identifier>
</dc:dc></srw:recordData></srw:record>
</srw:records></srw:searchRetrieveResponse>"""


class TitleSearchTests(unittest.TestCase):
    def test_query_is_bounded_and_cannot_escape_the_cql_title(self):
        self.assertEqual(clean_title_query("  Naruto   Deluxe "), "Naruto Deluxe")
        for bad in ('', 'x', 'a'*91, 'naruto" or bib.anywhere all "secret',
                    "title* and bib.author", "manga\n\"attack"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    clean_title_query(bad)

    def test_extract_only_real_checksum_valid_isbn13_tokens(self):
        self.assertEqual(extract_valid_isbns(["ISBN 978-2-87129-414-6"]),
                         ["9782871294146"])
        self.assertEqual(extract_valid_isbns(["97828712941460", "9782871294141"]),[])
        self.assertEqual(extract_valid_isbns(["ISBN 9782871294146 9782871294146"]),
                         ["9782871294146"])

    def test_multiple_bnf_records_are_never_auto_linked_to_manga(self):
        items=parse_title_results(XML, "2026-10-18T09:00:00+00:00")
        self.assertEqual([x["isbn13"] for x in items],
                         ["9782871294146", "9782344074282"])
        self.assertEqual(items[0]["title_fr"],"Naruto. Tome 1")
        self.assertEqual(items[1]["title_fr"],"Naruto Tome 2")
        self.assertEqual(items[0]["source_url"],
                         "https://catalogue.bnf.fr/ark:/12148/cb11111111x")
        self.assertTrue(items[0]["verified_isbn"])
        self.assertEqual(items[0]["publisher_fr"],"Kana")
        self.assertEqual(items[0]["language_status"],"french")
        self.assertEqual(items[1]["language_status"],"unknown")
        self.assertNotIn("manga_id",items[0])
        self.assertNotIn("volume_number",items[0])
        self.assertNotIn("is_published_full_collection",items[0])

    def test_results_are_limited_and_skip_bad_or_missing_sources(self):
        self.assertEqual(len(parse_title_results(XML, "date", limit=1)),1)
        self.assertEqual(len(parse_title_results(XML, "date", limit=18)),2)
        self.assertEqual(parse_title_results(XML.replace(
            b"ark:/12148/cb11111111x",b"invalid_ark").replace(
            b"ark:/12148/cb22222222x",b"invalid_ark"),"date"),[])

    def test_xml_size_and_doctype_rejected(self):
        with self.assertRaises(ValueError):
            parse_title_results(b'<!DOCTYPE foo><data/>',"date")
        with self.assertRaises(ValueError):
            parse_title_results(b"x"*2_000_001,"date")

    def test_language_status_does_not_invent_french_when_missing(self):
        from apps.api.app.edition_discovery import bibliographic_language
        self.assertEqual(bibliographic_language([]),"unknown")
        self.assertEqual(bibliographic_language(["French"]),"french")
        self.assertEqual(bibliographic_language(["eng"]),"other")
        self.assertEqual(bibliographic_language(["fra", "eng"]),"mixed")

    def test_remote_failure_is_explicit_and_no_write_occurs(self):
        with patch("apps.api.app.edition_discovery.urllib.request.urlopen",
                   side_effect=OSError("offline")):
            with self.assertRaises(HTTPException) as err:
                lookup_title_records("Naruto")
        self.assertEqual(err.exception.status_code,503)

    def test_route_is_read_only(self):
        router=create_edition_discovery_router()
        route=next(x for x in router.routes if
                   x.path=="/collection/discover-books")
        self.assertEqual(route.methods,{"GET"})

if __name__=="__main__":
    unittest.main()
