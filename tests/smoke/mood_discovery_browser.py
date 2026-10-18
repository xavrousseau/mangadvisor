"""Guided mood discovery real-browser check on disposable CI catalog."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8501"
DIR = Path("tests/smoke/screenshots")
DIR.mkdir(parents=True, exist_ok=True)

def check(page, layout):
    page.goto(BASE + "/for-you", wait_until="domcontentloaded", timeout=60000)
    expect(page.locator('[data-action="generate-mood"]')).to_be_visible(timeout=25000)
    expect(page.locator(".mood-choice")).to_have_count(6)
    page.locator('[data-action="mood-select"][data-mood="MYSTERY"]').click()
    expect(page.locator('[data-mood="MYSTERY"]')).to_have_attribute("aria-pressed", "true")
    page.locator("#mood-length").select_option("LONG")
    page.locator("#mood-finished").check()
    page.locator('[data-action="generate-mood"]').click()
    expect(page.locator(".mood-card").first).to_be_visible(timeout=25000)
    expect(page.locator(".mood-evidence").first).to_be_visible()
    expect(page.locator('[data-action="feedback"][data-feedback="INTERESTED"]').first).to_be_visible()
    assert page.locator(".mood-card").count() >= 1
    assert page.locator(".mood-result-summary").inner_text().strip()
    page.screenshot(path=str(DIR / f"{layout}-mood-discovery.png"), full_page=True)
    # Existing historical recommendation modes stay reachable.
    page.locator('[data-action="rec-mode"][data-value="library"]').click()
    expect(page.locator("#rec-goal")).to_be_visible()
    page.locator('[data-action="rec-mode"][data-value="manual"]').click()
    expect(page.locator("#manual-search")).to_be_visible()
    page.locator('[data-action="rec-mode"][data-value="mood"]').click()
    expect(page.locator('[data-action="generate-mood"]')).to_be_visible()

if __name__ == "__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            for layout,viewport in (
                ("desktop",{"width":1400,"height":900}),
                ("mobile",{"width":390,"height":844}),
            ):
                page=browser.new_page(viewport=viewport)
                try:
                    check(page,layout)
                    print("Guided mood discovery real browser OK:",layout)
                finally:
                    page.close()
        finally:
            browser.close()
