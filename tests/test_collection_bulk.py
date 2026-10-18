"""Bulk French book import stays ISBN-only, idempotent and non-destructive."""
import unittest

from fastapi import HTTPException
from apps.api.app.collection_bulk import (
    normalize_csv, attach_matches, make_preview, parse_bool, confirmation_token, MAX_ROWS,
)

KNOWN = [
    {"id": 7, "isbn13": "9782871294146", "manga_id": 1,
     "title_fr": "Naruto. Tome 1", "edition_kind": "CLASSIC",
     "volume_number": 1, "is_owned": False, "is_read": True}
]


class SafeBulkTests(unittest.TestCase):
    def test_semicolon_with_french_yes_no(self):
        result=normalize_csv("isbn13;possede;lu\n9782871294146;oui;non\n")
        self.assertEqual(result["total_rows"],1)
        self.assertEqual(result["items"][0]["is_owned"],True)
        self.assertEqual(result["items"][0]["is_read"],False)
        self.assertFalse(result["errors"])

    def test_comma_and_tab_and_isbn_only(self):
        for separator in (",", "\t"):
            with self.subTest(separator=separator):
                data=normalize_csv("ISBN13"+separator+"owned"+separator+"read\n9782871294146"+separator+"true"+separator+"1\n")
                self.assertTrue(data["items"][0]["is_owned"])
                self.assertTrue(data["items"][0]["is_read"])
        result=normalize_csv("isbn\n9782871294146\n")
        self.assertTrue(result["items"][0]["is_owned"])
        self.assertFalse(result["items"][0]["is_read"])

    def test_duplicate_rows_merge_positive_states_and_do_not_delete_anything(self):
        result=normalize_csv(
            "\ufeffisbn;possede;lu\n9782871294146;oui;non\n9782871294146;non;oui\n"
        )
        self.assertEqual(result["duplicate_rows"],1)
        self.assertEqual(len(result["items"]),1)
        self.assertTrue(result["items"][0]["is_owned"])
        self.assertTrue(result["items"][0]["is_read"])

    def test_unknown_isbn_never_guessed_from_title(self):
        parsed=normalize_csv("isbn;possede\n9782871294146;oui\n9782344074282;oui\n")
        output=make_preview(parsed,KNOWN)
        self.assertEqual(output["matched"],1)
        self.assertEqual(output["unknown"],1)
        unknown=next(row for row in output["items"] if row["match"]=="UNKNOWN")
        self.assertIsNone(unknown["edition_id"])
        self.assertIsNone(unknown["manga_id"])
        self.assertEqual(unknown["title_fr"],None)
        self.assertEqual(output["to_update"],1)
        self.assertEqual(len(output["confirmation_token"]),64)

    def test_invalid_rows_are_reported_not_invented(self):
        result=normalize_csv("isbn;possede;lu\n9782871294141;oui;non\n9782871294146;maybe;oui\n9782871294146;oui;oui\n")
        self.assertEqual(len(result["errors"]),2)
        self.assertEqual(len(result["items"]),1)

    def test_rejected_headers_malformed_and_overlarge(self):
        with self.assertRaises(HTTPException):
            normalize_csv("serie;tome\nNaruto;1\n")
        with self.assertRaises(HTTPException):
            normalize_csv("isbn;possede\n"+"9782871294146;oui\n"* (MAX_ROWS+1))
        with self.assertRaises(HTTPException):
            normalize_csv("isbn;possede\n9782871294146;oui;extra\n")
        # Last case is a row-level validation issue, not an abort.
    
    def test_false_never_triggers_a_destructive_import(self):
        parsed=normalize_csv("isbn;possede;lu\n9782871294146;non;non\n")
        review=make_preview(parsed,KNOWN)
        self.assertEqual(review["to_update"],0)
        self.assertEqual(review["matched"],1)
        self.assertTrue(KNOWN[0]["is_read"])

    def test_change_in_existing_collection_invalidates_approval(self):
        parsed=normalize_csv("isbn;possede;lu\n9782871294146;oui;non\n")
        before=make_preview(parsed,KNOWN)
        new=[{**KNOWN[0],"is_owned":True}]
        after=make_preview(parsed,new)
        self.assertNotEqual(before["confirmation_token"],after["confirmation_token"])

    def test_preview_token_is_deterministic_without_personal_fields(self):
        parsed=normalize_csv("isbn13\n9782871294146\n")
        first=make_preview(parsed,KNOWN)
        second=make_preview(parsed,KNOWN)
        self.assertEqual(first["confirmation_token"],second["confirmation_token"])
        self.assertNotIn("user_score",str(first["items"]))


if __name__=="__main__":
    unittest.main()
