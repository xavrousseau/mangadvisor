"""Downloadable starter files for the separate reading-library import.

No database access, no sample ownership data persisted anywhere.
"""
from __future__ import annotations
import base64
import csv
import io
from openpyxl import Workbook

HEADERS = ("title","library_status","user_score","is_favorite",
           "owned_volumes","read_volumes","notes")
ROWS = (
    ("Naruto","READ",8.5,"true",72,72,"Très bon shonen"),
    ("Bleach","READ",8,"false",74,74,""),
    ("One Piece","WANT_TO_READ","","false","","",""),
    ("Fairy Tail","NOT_INTERESTED","","false","","",""),
)

def reading_template_csv() -> str:
    stream=io.StringIO()
    writer=csv.writer(stream,lineterminator="\n")
    writer.writerow(HEADERS)
    writer.writerows(ROWS)
    return stream.getvalue()

def reading_template_xlsx_base64() -> str:
    wb=Workbook()
    ws=wb.active
    ws.title="bibliotheque"
    ws.append(HEADERS)
    for row in ROWS:
        ws.append(row)
    result=io.BytesIO()
    wb.save(result)
    return base64.b64encode(result.getvalue()).decode("ascii")
