"""End-to-end browser checks for the scanner flow; BnF and writes mocked in CI.

No real collection data is modified by this browser test.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8501"
ISBN = "9782871294146"
DIR = Path("tests/smoke/screenshots")
DIR.mkdir(parents=True, exist_ok=True)


def run(page, size):
    sent = []

    def status_unknown(route):
        route.fulfill(json={"isbn13": ISBN, "registered": False, "edition": None})

    def bnf_record(route):
        route.fulfill(json={
            "isbn13": ISBN, "title_fr": "Naruto, tome 1",
            "publisher_fr": "Kana", "author_fr": "Masashi Kishimoto",
            "source_url": "https://catalogue.bnf.fr/ark:/12148/cb12345678x",
            "verified_isbn": True, "edition_kind_suggested": "UNKNOWN",
        })

    def confirm_new(route):
        sent.append(route.request.post_data_json)
        route.fulfill(json={
            "status": "created",
            "edition": {"edition_id": 50, "manga_id": 1,
                        "title_fr": "Naruto, tome 1", "isbn13": ISBN},
            "preserved": True,
        })

    page.route("**/api/collection/scan/status/" + ISBN, status_unknown)
    page.route("**/api/collection/isbn/" + ISBN, bnf_record)
    page.route("**/api/collection/scan/confirm", confirm_new)

    page.goto(BASE + "/library", wait_until="domcontentloaded", timeout=60000)
    expect(page.locator('[data-action="open-scanner"]:visible').first).to_be_visible(timeout=30000)
    page.locator('[data-action="open-scanner"]:visible').first.click()
    expect(page.locator("#scan-dialog")).to_be_visible()
    expect(page.locator('[data-action="scan-confirm"]')).to_have_count(0)

    page.locator("#scan-isbn-input").fill(ISBN)
    page.locator('#scan-isbn-form button[type="submit"]').click()
    expect(page.locator(".scan-book")).to_contain_text("Naruto, tome 1")
    expect(page.locator('[data-action="scan-confirm"]')).to_be_disabled()

    page.locator("#scan-series-input").fill("Naruto")
    page.locator('#scan-series-form button[type="submit"]').click()
    expect(page.locator('.scan-match[data-id="1"]')).to_be_visible(timeout=30000)
    page.locator('.scan-match[data-id="1"]').click()
    page.locator("#scan-kind").select_option("CLASSIC")
    page.locator("#scan-volume").fill("1")
    page.locator("#scan-ack").check()
    expect(page.locator('[data-action="scan-confirm"]')).to_be_enabled()
    page.screenshot(path=str(DIR / (size + "-isbn-scanner-preview.png")))
    page.locator('[data-action="scan-confirm"]').click()
    expect(page.locator(".scan-success")).to_be_visible(timeout=15000)
    assert len(sent) == 1, sent
    assert sent[0] == {
        "isbn13": ISBN, "confirmed": True,
        "is_owned": True, "is_read": False,
        "manga_id": 1, "edition_kind": "CLASSIC", "volume_number": 1,
    }, sent

    page.locator('[data-action="scan-summary"]').last.click()
    expect(page.locator(".scan-report")).to_be_visible()
    expect(page.locator(".scan-report")).to_contain_text("Tomes ajoutés")
    expect(page.locator(".scan-report")).to_contain_text("Naruto, tome 1")
    page.locator('[data-action="scan-resume"]').click()
    expect(page.locator("#scan-isbn-input")).to_have_value("")
    page.locator('.scan-heading [data-action="scan-close"]').click()
    expect(page.locator("#scan-dialog")).to_have_count(0)

    page.unroute("**/api/collection/scan/status/" + ISBN)
    page.unroute("**/api/collection/scan/confirm")

    def status_known(route):
        route.fulfill(json={
            "isbn13": ISBN, "registered": True,
            "edition": {
                "edition_id": 50, "manga_id": 1, "manga_title": "Naruto",
                "title_fr": "Naruto, tome 1", "publisher_fr": "Kana",
                "isbn13": ISBN, "edition_kind": "CLASSIC", "volume_number": 1,
                "is_owned": True, "is_read": False,
            },
        })

    def confirm_known(route):
        sent.append(route.request.post_data_json)
        route.fulfill(json={
            "status": "updated",
            "edition": {"edition_id": 50, "title_fr": "Naruto, tome 1", "isbn13": ISBN,
                        "is_owned": True, "is_read": True},
            "preserved": True,
        })

    page.route("**/api/collection/scan/status/" + ISBN, status_known)
    page.route("**/api/collection/scan/confirm", confirm_known)
    page.locator('[data-action="open-scanner"]:visible').first.click()
    page.locator("#scan-isbn-input").fill(ISBN)
    page.locator('#scan-isbn-form button[type="submit"]').click()
    expect(page.locator(".scan-duplicate")).to_be_visible()
    expect(page.locator("#scan-ack")).to_have_count(0)
    page.locator("#scan-read").check()
    page.locator('[data-action="scan-confirm"]').click()
    expect(page.locator(".scan-success")).to_be_visible()
    assert len(sent) == 2, sent
    assert sent[1] == {"isbn13": ISBN, "confirmed": True,
                       "is_owned": True, "is_read": True}, sent
    page.locator('.scan-success [data-action="scan-summary"]').click()
    expect(page.locator(".scan-report")).to_be_visible()
    expect(page.locator(".scan-report")).to_contain_text("Statuts complétés")
    page.locator('.scan-report [data-action="scan-close"]').click()
    page.unroute("**/api/collection/isbn/" + ISBN)
    page.unroute("**/api/collection/scan/status/" + ISBN)
    page.unroute("**/api/collection/scan/confirm")


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for size, viewport in (
                ("desktop", {"width": 1400, "height": 900}),
                ("mobile", {"width": 390, "height": 844}),
            ):
                page = browser.new_page(viewport=viewport)
                try:
                    run(page, size)
                    print("ISBN scanner browser flow OK:", size)
                finally:
                    page.close()
        finally:
            browser.close()
