import unittest
from unittest.mock import patch
from fastapi import HTTPException
from apps.api.app.collection import (
    BNF_SOURCE, SCHEMA, EditionCreate, VolumeState, edition_kind_from_title,
    isbn13_normalize, parse_bnf_sru, edition_kind_user_choice_is_explicit,
    lookup_bnf,
)

# A synthetic BnF response in the published SRU Dublin Core structure.
XML = b"""<?xml version='1.0' encoding='utf-8'?>
<srw:searchRetrieveResponse xmlns:srw='http://www.loc.gov/zing/srw/'
xmlns:dc='http://purl.org/dc/elements/1.1/'>
<srw:records><srw:record>
<srw:recordIdentifier>ark:/12148/cb12345678x</srw:recordIdentifier>
<srw:recordData><dc:dc>
<dc:title>Naruto. Tome 1</dc:title>
<dc:creator>Masashi Kishimoto</dc:creator>
<dc:publisher>Kana</dc:publisher>
<dc:date>2002</dc:date>
<dc:identifier>ISBN 978-2-87129-414-6</dc:identifier>
</dc:dc></srw:recordData></srw:record></srw:records>
</srw:searchRetrieveResponse>"""


class FrenchEditionTests(unittest.TestCase):
    def test_isbn_checksum(self):
        self.assertEqual(isbn13_normalize("978-2-87129-414-6"),"9782871294146")
        for value in ("9782871294141", "978-ABC-1", "123", " "):
            with self.subTest(value=value),self.assertRaises(ValueError):
                isbn13_normalize(value)

    def test_bnf_dublin_core_matching_and_attribution(self):
        result=parse_bnf_sru(XML,"9782871294146")
        self.assertEqual(result["title_fr"],"Naruto. Tome 1")
        self.assertEqual(result["publisher_fr"],"Kana")
        self.assertEqual(result["author_fr"],"Masashi Kishimoto")
        self.assertEqual(result["release_date_text"],"2002")
        self.assertEqual(result["source_name"],BNF_SOURCE)
        self.assertEqual(result["source_url"],"https://catalogue.bnf.fr/ark:/12148/cb12345678x")
        self.assertTrue(result["verified_isbn"])

    def test_wrong_isbn_can_never_create_a_verified_record(self):
        self.assertIsNone(parse_bnf_sru(XML,"9782344074282"))
        self.assertIsNone(parse_bnf_sru(XML.replace(b"Naruto. Tome 1",b""),"9782871294146"))

    def test_edition_kind_is_not_guessed_as_classic(self):
        self.assertEqual(edition_kind_from_title("Naruto, tome 1"),"UNKNOWN")
        self.assertEqual(edition_kind_from_title("Bleach Deluxe - Tome 01"),"DELUXE")
        self.assertEqual(edition_kind_from_title("Manga Perfect Edition 1"),"PERFECT")
        self.assertEqual(edition_kind_from_title("L'intégrale, volume 3"),"INTEGRAL")
        record={"edition_kind_suggested":"UNKNOWN"}
        self.assertEqual(edition_kind_user_choice_is_explicit(record,"CLASSIC")["edition_kind_origin"],"USER_CONFIRMED")
        self.assertEqual(edition_kind_user_choice_is_explicit({"edition_kind_suggested":"DELUXE"},"DELUXE")["edition_kind_origin"],"BNF_TITLE")

    def test_schema_is_only_additive_and_legacy_counters_untouched(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS manga_fr_edition",SCHEMA)
        self.assertIn("CREATE TABLE IF NOT EXISTS user_manga_volume",SCHEMA)
        self.assertNotIn("ALTER TABLE user_manga_library",SCHEMA)
        for forbidden in ("DROP TABLE","TRUNCATE","DELETE FROM","UPDATE user_manga_library"):
            self.assertNotIn(forbidden,SCHEMA)

    def test_payload_validation(self):
        self.assertEqual(EditionCreate(isbn13="9782871294146",edition_kind="DELUXE",volume_number=3).volume_number,3)
        with self.assertRaises(Exception):
            EditionCreate(isbn13="9782871294146",edition_kind="SPECIAL",volume_number=1)
        with self.assertRaises(Exception):
            EditionCreate(isbn13="9782871294146",edition_kind="PERFECT",volume_number=0)
        self.assertTrue(VolumeState(is_owned=False,is_read=True).is_read)

    def test_remote_service_failure_is_explicit(self):
        with patch("apps.api.app.collection.urllib.request.urlopen",side_effect=OSError("offline")):
            with self.assertRaises(HTTPException) as failure:
                lookup_bnf("9782871294146")
        self.assertEqual(failure.exception.status_code,503)


if __name__=="__main__":
    unittest.main()
