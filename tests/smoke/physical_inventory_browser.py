"""CI-only Chrome smoke: physically distinct editions visible in main desktop/mobile UI."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE="http://127.0.0.1:8501"
OUT=Path("tests/smoke/screenshots")
OUT.mkdir(parents=True,exist_ok=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for device,width,height in (("desktop",1440,960),("mobile",390,844)):
            page=browser.new_page(viewport={"width":width,"height":height})
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(BASE+"/library",wait_until="domcontentloaded",timeout=90000)
            workspace=page.locator("#physical-inventory-workspace")
            expect(workspace).to_be_visible(timeout=30000)
            expect(page.locator(".physical-inventory-stats")).to_be_visible(timeout=30000)
            matches=page.locator('.physical-work:has-text("Demo CI 16")')
            expect(matches).to_have_count(1,timeout=30000)
            expect(matches.locator(".physical-edition-entry")).to_have_count(2)
            expect(matches).to_contain_text("Version X")
            expect(matches).to_contain_text("Version Y")
            expect(matches).to_contain_text("3")
            expect(matches).to_contain_text("4")
            expect(workspace).to_contain_text("ISBN")
            page.screenshot(path=str(OUT/f"{device}-physical-inventory-3-9.png"),full_page=True)
            matches.locator('[data-go^="/manga/"]').click()
            expect(page).to_have_url(BASE+"/manga/16",timeout=30000)
            expect(page.locator(".physical-inventory-detail .physical-edition-entry")).to_have_count(2,timeout=30000)
            expect(page.locator(".physical-inventory-detail")).to_contain_text("Version X")
            expect(page.locator(".physical-inventory-detail")).to_contain_text("Version Y")
            expect(page.locator("#collection-book-panel")).to_be_visible()
            # This is a distinct read-only panel; no phantom ISBNs or edits.
            assert page.locator(".physical-inventory-detail [data-action='volume-owned']").count()==0
            assert not errors, (device, errors)
            page.screenshot(path=str(OUT/f"{device}-physical-editions-detail-3-9.png"),full_page=True)
            page.close()
        browser.close()
    print("OK: desktop/mobile show both declared physical editions, not ISBN books.")


if __name__=="__main__":
    main()
