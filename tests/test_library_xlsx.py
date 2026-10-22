"""Offline XLSX import conversion and validation, never touches PostgreSQL."""
import base64
import io
import unittest

from fastapi import HTTPException
from openpyxl import Workbook
from apps.api.app.library_xlsx import xlsx_to_library_csv, MAX_XLSX_BYTES
from apps.api.app.main import LibraryXlsxConversionRequest, convert_reading_library_xlsx


class ReadingXlsxTests(unittest.TestCase):
    def workbook_base64(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["title", "library_status", "user_score", "is_favorite"])
        ws.append(["Naruto", "READ", 8.5, True])
        ws.append(["Bleach", "WANT_TO_READ", None, False])
        buf = io.BytesIO()
        wb.save(buf)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def test_xlsx_first_sheet_converts_to_library_csv(self):
        encoded = self.workbook_base64()
        result = convert_reading_library_xlsx(
            LibraryXlsxConversionRequest(content_base64=encoded)
        )
        self.assertIn("title,library_status,user_score,is_favorite", result["csv_content"])
        self.assertIn("Naruto,READ,8.5,True", result["csv_content"])
        self.assertIn("Bleach,WANT_TO_READ,,False", result["csv_content"])

    def test_conversion_rejects_corrupt_or_oversized_input(self):
        with self.assertRaises(HTTPException):
            xlsx_to_library_csv("not-base64")
        big = base64.b64encode(b"PK\x03\x04"+b"x"*MAX_XLSX_BYTES).decode("ascii")
        with self.assertRaises(HTTPException):
            xlsx_to_library_csv(big)

    def test_conversion_does_not_evaluate_spreadsheet_formula(self):
        wb=Workbook()
        ws=wb.active
        ws.append(["title", "library_status"])
        ws.append(["=1+1", "READ"])
        data=io.BytesIO()
        wb.save(data)
        result=xlsx_to_library_csv(base64.b64encode(data.getvalue()).decode("ascii"))
        self.assertNotIn("2,READ", result)
