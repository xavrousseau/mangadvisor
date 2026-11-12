"""CI smoke: physical inventory API preserves distinct declared editions.

The MangAxiom V1 library deliberately does not show edition/ISBN admin
screens, but their underlying records must remain available and untouched.
"""
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8501"


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for device, width, height in (
                ("desktop", 1440, 960),
                ("mobile", 390, 844),
            ):
                page = browser.new_page(viewport={"width": width, "height": height})
                try:
                    page.goto(BASE + "/library", wait_until="domcontentloaded", timeout=90000)
                    expect(page.locator("#library-series-panel")).to_be_visible()
                    assert page.locator('[data-action="library-view"][data-value="editions"]').count() == 0
                    assert page.locator("#physical-inventory-workspace:visible").count() == 0

                    inventory = page.request.get(BASE + "/api/inventory/declarations")
                    pending = page.request.get(BASE + "/api/inventory/pending")
                    assert inventory.ok, inventory.text()
                    assert pending.ok, pending.text()
                    text = inventory.text()
                    assert "Version X" in text and "Version Y" in text, text[:1500]
                    assert "Demo CI 16" in text, text[:1500]
                    assert "Inconnu de CI" in pending.text(), pending.text()[:1500]
                    print("Physical edition preservation OK:", device)
                finally:
                    page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
