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
            # An unmatched synthetic title saved in the preceding inventory smoke
            # remains visible but has no made-up manga detail link.
            pending=page.locator(".physical-inventory-pending")
            expect(pending).to_be_visible(timeout=30000)
            expect(pending).to_contain_text("Inconnu de CI")
            expect(pending).to_contain_text("2 exemplaires")
            assert pending.locator('[data-go^="/manga/"]').count()==0
            # The pending work now has a manual, opt-in resolution wizard.
            pending.locator('[data-action="pending-match-start"]').first.click()
            expect(page.locator("#inventory-match-panel")).to_be_visible(timeout=30000)
            expect(page.locator("#inventory-match-panel")).to_contain_text("Inconnu de CI")
            page.locator("#pending-match-query").fill("Demo CI 16")
            page.locator('#pending-match-search-form button[type="submit"]').click()
            options=page.locator(".inventory-match-candidate")
            expect(options.first).to_be_visible(timeout=30000)
            options.locator('[data-action="pending-match-select"][data-id="16"]').first.click()
            expect(page.locator(".inventory-match-review")).to_be_visible(timeout=30000)
            expect(page.locator(".inventory-match-review")).to_contain_text("Inconnu de CI")
            expect(page.locator(".inventory-match-review")).to_contain_text("Demo CI 16")
            expect(page.locator('[data-action="pending-match-confirm"]')).to_be_disabled()
            mode=page.locator("#pending-match-mode")
            if mode.count():
                mode.select_option("MARK_DUPLICATE")
            page.locator("#pending-match-ack").check()
            expect(page.locator('[data-action="pending-match-confirm"]')).to_be_enabled()
            # Do not confirm in this browser smoke: original pending claims
            # and the subsequent CI fixtures must remain unchanged.
            page.locator('[data-action="pending-match-close"]').click()
            expect(page.locator("#inventory-match-panel")).to_have_count(0)
            expect(pending).to_contain_text("Inconnu de CI")
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
