"""Ensure Streamlit's downloadable reading-library templates remain available via API."""
import base64
import csv
import io
import unittest
from openpyxl import load_workbook
from apps.api.app.main import get_reading_library_template

class TemplateTests(unittest.TestCase):
    def test_csv_example_has_expected_columns_and_statuses(self):
        data=get_reading_library_template("csv")
        rows=list(csv.DictReader(io.StringIO(data["content"])))
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]["title"],"Naruto")
        self.assertEqual(rows[0]["library_status"],"READ")
        self.assertEqual(rows[-1]["library_status"],"NOT_INTERESTED")

    def test_xlsx_example_preserves_headers_and_rows(self):
        data=get_reading_library_template("xlsx")
        wb=load_workbook(io.BytesIO(base64.b64decode(data["content_base64"])),read_only=True)
        try:
            records=list(wb.active.values)
            self.assertEqual(len(records),5)
            self.assertEqual(records[0][:2],("title","library_status"))
            self.assertEqual(records[1][0],"Naruto")
        finally:
            wb.close()
