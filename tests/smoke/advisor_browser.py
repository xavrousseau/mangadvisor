"""Chromium end-to-end advisor conversation on disposable CI PostgreSQL."""
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

BASE="http://127.0.0.1:8501"
DIR=Path("tests/smoke/screenshots")
DIR.mkdir(parents=True,exist_ok=True)

def chat(page,message):
    page.locator("#advisor-message").fill(message)
    page.locator("#advisor-form button[type=submit]").click()
    expect(page.locator("#advisor-form button[type=submit]")).to_be_enabled(timeout=25000)

def run(page,device):
    page.goto(BASE+"/for-you",wait_until="domcontentloaded",timeout=60000)
    page.locator('[data-action="rec-mode"][data-value="advisor"]').click()
    expect(page.locator(".advisor-studio")).to_be_visible(timeout=20000)
    expect(page.locator(".advisor-suggestion")).to_have_count(4)
    chat(page,"Je cherche un mystère plutôt long, terminé, idéalement en français")
    expect(page.locator(".advisor-message.is-assistant").first).to_be_visible()
    expect(page.locator(".advisor-card").first).to_be_visible(timeout=30000)
    expect(page.locator(".advisor-card").first).to_contain_text("ISBN français enregistré")
    first_titles=page.locator(".advisor-card h3").all_inner_texts()
    assert first_titles,device
    # One-tap diversity controls are a normal conversational follow-up.
    expect(page.locator('[data-action="advisor-balance"]')).to_have_count(3)
    page.locator('[data-action="advisor-balance"][data-value="EXPLORE"]').click()
    expect(page.locator('[data-action="advisor-balance"][data-value="EXPLORE"]')).to_have_attribute(
        "aria-pressed","true",timeout=30000)
    expect(page.locator(".advisor-card").first).to_be_visible(timeout=30000)
    expect(page.locator(".advisor-message.is-assistant").last).to_contain_text("découvertes variées")
    page.screenshot(path=str(DIR/f"{device}-advisor-variety.png"),full_page=True)
    chat(page,"Français obligatoire")
    expect(page.locator(".advisor-card")).to_have_count(1,timeout=25000)
    expect(page.locator(".advisor-card h3").first).to_have_text("Demo CI 08")
    expect(page.locator(".advisor-editions")).to_have_count(1)
    page.locator(".advisor-editions > summary").click()
    expect(page.locator(".advisor-edition-group")).to_have_count(4)
    expect(page.locator(".advisor-editions")).to_contain_text("Deluxe")
    expect(page.locator(".advisor-editions")).to_contain_text("Perfect")
    expect(page.locator(".advisor-editions")).to_contain_text("9781234567804")
    expect(page.locator(".advisor-editions")).to_contain_text("Éditeur Deluxe fictif")
    chat(page,"Édition Deluxe obligatoire")
    expect(page.locator(".advisor-card")).to_have_count(1,timeout=25000)
    expect(page.locator(".advisor-card h3").first).to_have_text("Demo CI 08")
    chat(page,"Une enquête psychologique, sans horreur et sans gore")
    expect(page.locator(".advisor-card").first).to_be_visible(timeout=25000)
    expect(page.locator(".advisor-story-chip")).to_have_count(2,timeout=25000)
    expect(page.locator(".advisor-card").first).to_contain_text("Mot du synopsis")
    expect(page.locator(".advisor-card").first).to_contain_text("Tag du catalogue")
    expect(page.locator(".advisor-message.is-assistant").last).to_contain_text("sans horreur documentée")
    assert page.locator(".advisor-message.is-user").count()>=3
    page.screenshot(path=str(DIR/f"{device}-advisor-conversation.png"),full_page=True)
    page.locator('[data-action="advisor-reset"]').click()
    expect(page.locator(".advisor-suggestion")).to_have_count(4)
    expect(page.locator(".advisor-card")).to_have_count(0)
    # Previous recommendation modes remain accessible.
    page.locator('[data-action="rec-mode"][data-value="mood"]').click()
    expect(page.locator("#mood-length")).to_be_visible()
    page.locator('[data-action="rec-mode"][data-value="advisor"]').click()
    expect(page.locator("#advisor-message")).to_be_visible()

if __name__=="__main__":
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        try:
            for device,viewport in (("desktop",{"width":1400,"height":900}),
                                    ("mobile",{"width":390,"height":844})):
                page=browser.new_page(viewport=viewport)
                try:
                    run(page,device)
                    print("Manga advisor multi-turn browser OK",device)
                finally:
                    page.close()
        finally:
            browser.close()
