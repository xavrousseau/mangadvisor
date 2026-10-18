"""Tests réels de la nouvelle interface Mangadvisor avec base CI jetable."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8501"
OUTPUT = Path("tests/smoke/screenshots")
OUTPUT.mkdir(parents=True, exist_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for device, width, height in [
            ("desktop", 1440, 960),
            ("mobile", 390, 844),
        ]:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(BASE, wait_until="domcontentloaded", timeout=120000)
            expect(page.locator(".hero h1")).to_be_visible(timeout=90000)
            expect(page.locator(".manga-card").first).to_be_visible(timeout=30000)
            # L'accueil personnel montre la lecture en cours et une vraie sélection
            # du moteur sans perdre les raccourcis de découverte.
            expect(page.locator("#home-continue .home-reading-card")).to_have_count(1, timeout=40000)
            expect(page.locator("#home-continue")).to_contain_text("Vinland Saga")
            expect(page.locator("#home-personal .rec-card").first).to_be_visible(timeout=90000)
            expect(page.locator("#home-explore-title")).to_be_visible()
            page.screenshot(path=str(OUTPUT / f"{device}-accueil.png"), full_page=True)

            page.locator('[data-go="/discover"]').first.click()
            expect(page).to_have_url(BASE+"/discover", timeout=30000)
            expect(page.locator(".manga-card")).to_have_count(12, timeout=40000)
            page.screenshot(path=str(OUTPUT / f"{device}-discover.png"), full_page=True)

            if device=="desktop":
                page.locator("#catalog-query").fill("Monster")
                expect(page.locator(".manga-card")).to_have_count(1, timeout=30000)
                page.locator(".manga-card .card-open").first.click()
                expect(page).to_have_url(BASE+"/manga/2")
            else:
                page.locator(".manga-card .card-open").first.click()

            expect(page.locator(".detail-hero h1")).to_be_visible(timeout=30000)
            expect(page.locator(".synopsis")).to_be_visible(timeout=30000)
            page.screenshot(path=str(OUTPUT / f"{device}-fiche.png"), full_page=True)

            page.locator("#app-language").select_option("en")
            expect(page.get_by_role("heading", name="The story")).to_be_visible(timeout=30000)
            page.locator("#app-language").select_option("fr")
            expect(page.get_by_role("heading", name="L'histoire")).to_be_visible(timeout=30000)
            expect(page.locator("#library-editor")).to_be_visible()
            expect(page.locator("#edit-status")).to_have_value("READ")
            page.screenshot(path=str(OUTPUT / f"{device}-fiche-fr.png"), full_page=True)

            page.locator('[data-go="/for-you"]').first.click()
            expect(page).to_have_url(BASE+"/for-you")
            expect(page.locator("#rec-submit")).to_be_visible(timeout=30000)
            if device=="desktop":
                page.locator("#rec-submit").click()
                expect(page.locator("#rec-results .rec-card").first).to_be_visible(timeout=60000)
                page.locator("#rec-results .rec-card .btn-soft").first.click()
                expect(page.locator(".detail-hero h1")).to_be_visible(timeout=30000)
                page.go_back()
                expect(page.locator("#rec-results .rec-card").first).to_be_visible(timeout=30000)
                disliked = page.locator("#rec-results .rec-card").first.locator(
                    '[data-action="feedback"][data-feedback="NOT_FOR_ME"]'
                )
                disliked_id = disliked.get_attribute("data-manga-id")
                disliked.click()
                expect(page.locator(
                    '#rec-results [data-action="feedback"][data-manga-id="' + disliked_id + '"]'
                )).to_have_count(0, timeout=30000)
                # Le prochain appel au moteur doit réellement exclure ce manga.
                page.locator("#rec-submit").click()
                expect(page.locator("#rec-results .rec-card").first).to_be_visible(timeout=60000)
                expect(page.locator(
                    '#rec-results [data-action="feedback"][data-manga-id="' + disliked_id + '"]'
                )).to_have_count(0, timeout=30000)
            page.screenshot(path=str(OUTPUT / f"{device}-pour-moi.png"), full_page=True)

            page.locator('[data-go="/library"]').first.click()
            expect(page).to_have_url(BASE+"/library")
            expect(page.locator(".manga-card").first).to_be_visible(timeout=30000)
            page.screenshot(path=str(OUTPUT / f"{device}-bibliotheque.png"), full_page=True)

            assert not errors, f"Erreurs navigateur {device}: {errors}"
            page.close()
        browser.close()
    print("OK : parcours web, fiches, sélection FR/EN et bibliothèque (desktop/mobile).")


if __name__ == "__main__":
    run()
