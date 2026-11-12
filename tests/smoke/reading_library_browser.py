"""Test API des anciens imports de lecture, retirés de l'UX MangAxiom V1.

Sur la base CI jetable uniquement : vérifie que les traitements historiques
restent add-only, que la prévisualisation ne modifie rien et que la conversion
Excel fonctionne, même si aucun bouton d'import n'apparaît plus dans l'UI.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8501"


def guard_ci_database():
    config = (Path(__file__).resolve().parents[2] / ".env").read_text(encoding="utf-8")
    variables = dict(
        line.split("=", 1) for line in config.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    if variables.get("POSTGRES_DB") != "mangadvisor_ci" or variables.get("POSTGRES_USER") != "manga_ci":
        raise RuntimeError("Refus : test d'import seulement sur PostgreSQL CI jetable.")


def run():
    guard_ci_database()
    with sync_playwright() as playwright:
        api = playwright.request.new_context(base_url=BASE)
        try:
            template_csv = api.get("/api/library/import/template?format=csv")
            assert template_csv.ok and "Naruto" in template_csv.json()["content"]
            template_xlsx = api.get("/api/library/import/template?format=xlsx")
            assert template_xlsx.ok and template_xlsx.json()["content_base64"]

            before_result = api.get("/api/library?q=Naruto&limit=20")
            assert before_result.ok
            before = before_result.json()

            csv = "title,library_status,user_score,is_favorite\nNaruto,READ,1,true\n"
            payload = {"csv_content": csv, "delimiter": ",",
                       "default_status": "WANT_TO_READ", "dry_run": True}
            preview = api.post("/api/library/import/csv", data=payload)
            assert preview.ok, preview.text()
            assert "Naruto" in preview.text()
            assert api.get("/api/library?q=Naruto&limit=20").json() == before, \
                "CSV preview modified existing library data"

            payload["dry_run"] = False
            apply_result = api.post("/api/library/import/csv", data=payload)
            assert apply_result.ok, apply_result.text()
            assert api.get("/api/library?q=Naruto&limit=20").json() == before, \
                "Add-only CSV import unexpectedly changed existing reading data"

            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["title", "library_status", "user_score", "is_favorite"])
            sheet.append(["Naruto", "READ", 5, False])
            output = io.BytesIO()
            workbook.save(output)
            converted = api.post("/api/library/import/xlsx/convert", data={
                "content_base64": base64.b64encode(output.getvalue()).decode("ascii"),
            })
            assert converted.ok, converted.text()
            content = converted.json().get("csv_content", "")
            assert "Naruto,READ,5,False" in content, content
            preview_xlsx = api.post("/api/library/import/csv", data={
                "csv_content": content, "delimiter": ",",
                "default_status": "WANT_TO_READ", "dry_run": True,
            })
            assert preview_xlsx.ok, preview_xlsx.text()
            assert api.get("/api/library?q=Naruto&limit=20").json() == before, \
                "Excel import preview modified the library"

            print("OK: historical CSV/Excel APIs remain safe; hidden from UX MangAxiom.")
        finally:
            api.dispose()


if __name__ == "__main__":
    run()
