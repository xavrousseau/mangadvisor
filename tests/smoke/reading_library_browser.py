"""Real browser E2E for the distinct reading-library CSV/XLSX import.

Runs ONLY against the disposable mangadvisor_ci database used in GitHub Actions.
"""
from __future__ import annotations

import io
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from openpyxl import Workbook

BASE = "http://127.0.0.1:8501"


def guard_ci_database():
    config = (Path(__file__).resolve().parents[2] / ".env").read_text(encoding="utf-8")
    variables = dict(
        line.split("=", 1) for line in config.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    if variables.get("POSTGRES_DB") != "mangadvisor_ci" or variables.get("POSTGRES_USER") != "manga_ci":
        raise RuntimeError("Refus : navigateur d'import seulement sur PostgreSQL CI jetable.")


def run():
    guard_ci_database()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(BASE + "/library", wait_until="domcontentloaded")
        # Imports live in the Manage tab of the maintained single Web UI.
        page.locator('[data-action="library-view"][data-value="manage"]').last.click()
        expect(page.locator("#library-manage-panel")).to_be_visible(timeout=30000)
        expect(page.locator("#reading-import-workspace")).to_be_visible(timeout=30000)
        page.locator("#reading-import-workspace summary").click()
        expect(page.locator("#reading-file")).to_be_visible()
        assert page.locator("#bulk-csv-file").count() == 1, "ISBN import must remain separate"
        expect(page.locator('[data-action="reading-template-csv"]')).to_be_visible()
        expect(page.locator('[data-action="reading-template-xlsx"]')).to_be_visible()
        template_csv = page.request.get(BASE + "/api/library/import/template?format=csv")
        assert template_csv.ok and "Naruto" in template_csv.json()["content"]
        template_excel = page.request.get(BASE + "/api/library/import/template?format=xlsx")
        assert template_excel.ok and template_excel.json()["content_base64"]
        page.locator("#reading-profile-workspace summary").click()
        page.locator('[data-action="reading-profile-load"]').click()
        expect(page.locator("#reading-profile-results")).to_contain_text("Genres dominants", timeout=30000)


        before = page.request.get(BASE + "/api/library?q=Naruto&limit=20").json()
        csv = b"title,library_status,user_score,is_favorite\nNaruto,READ,1,true\n"
        page.locator("#reading-file").set_input_files({
            "name": "lecture.csv", "mimeType": "text/csv", "buffer": csv
        })
        expect(page.locator("#reading-csv")).to_have_value(csv.decode("utf-8"))
        page.locator('[data-action="reading-preview"]').click()
        expect(page.locator("#reading-import-result")).to_contain_text("Naruto", timeout=30000)
        expect(page.locator('[data-action="reading-apply"]')).to_be_visible()
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator('[data-action="reading-apply"]').click()
        expect(page.locator("#reading-import-result")).to_contain_text("correspondances traitées", timeout=30000)
        after = page.request.get(BASE + "/api/library?q=Naruto&limit=20").json()
        assert before == after, "Add-only reading CSV import unexpectedly changed existing library data"

        book = Workbook()
        sheet = book.active
        sheet.append(["title", "library_status", "user_score", "is_favorite"])
        sheet.append(["Naruto", "READ", 5, False])
        output = io.BytesIO()
        book.save(output)
        page.locator("#reading-file").set_input_files({
            "name": "lecture.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "buffer": output.getvalue(),
        })
        expect(page.locator("#reading-csv")).to_have_value("title,library_status,user_score,is_favorite\nNaruto,READ,5,False\n", timeout=30000)
        page.locator('[data-action="reading-preview"]').click()
        expect(page.locator("#reading-import-result")).to_contain_text("Naruto", timeout=30000)
        after_xlsx_preview = page.request.get(BASE + "/api/library?q=Naruto&limit=20").json()
        assert before == after_xlsx_preview, "XLSX preview mutated the library"
        assert not failures, failures
        browser.close()
        print("OK: CSV preview/apply remains add-only; XLSX conversion/preview; ISBN section separate.")


if __name__ == "__main__":
    run()
