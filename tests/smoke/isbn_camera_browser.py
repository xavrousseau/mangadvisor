"""CI browser contract: MangAxiom V1 does not expose ISBN scanner entry points.

The old scanning engine remains in the repository and is tested separately;
this UX check must never make a physical edition write.
"""
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8501"


def run(page, device):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE + "/library", wait_until="domcontentloaded", timeout=60000)
    expect(page.locator("#library-series-panel")).to_be_visible(timeout=30000)
    assert page.locator('[data-action="open-scanner"]:visible').count() == 0
    assert page.locator('[data-action="library-view"][data-value="manage"]').count() == 0
    page.goto(BASE + "/manga/1", wait_until="domcontentloaded", timeout=60000)
    expect(page.locator(".detail-hero")).to_be_visible(timeout=30000)
    assert page.locator('[data-action="open-scanner"]:visible').count() == 0
    assert not errors, (device, errors)


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for device, viewport in (
                ("desktop", {"width": 1400, "height": 900}),
                ("mobile", {"width": 390, "height": 844}),
            ):
                page = browser.new_page(viewport=viewport)
                try:
                    run(page, device)
                    print("MangAxiom ISBN scanner UX hidden OK:", device)
                finally:
                    page.close()
        finally:
            browser.close()
