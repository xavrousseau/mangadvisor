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
            expect(page.locator("#home-personal .profile-context")).to_be_visible(timeout=30000)
            expect(page.locator("#home-explore-title")).to_be_visible()
            page.screenshot(path=str(OUTPUT / f"{device}-accueil.png"), full_page=True)

            # Appearance: three genuinely different themes, accent and density.
            expect(page.locator("html")).to_have_attribute("data-theme", "night")
            expect(page.locator("html")).to_have_attribute("data-accent", "amber")
            page.locator(".appearance-trigger").click()
            expect(page).to_have_url(BASE+"/appearance", timeout=30000)
            expect(page.get_by_role("heading", name="Personnalise Mangadvisor")).to_be_visible()
            expect(page.locator(".theme-choice")).to_have_count(3)
            expect(page.locator(".accent-choice")).to_have_count(6)
            page.locator('[data-action="appearance-preset"][data-value="paper"]').click()
            page.locator('[data-action="appearance-accent"][data-value="ocean"]').click()
            page.locator('[data-action="appearance-density"][data-value="compact"]').click()
            expect(page.locator("html")).to_have_attribute("data-theme", "paper")
            expect(page.locator("html")).to_have_attribute("data-accent", "ocean")
            expect(page.locator("html")).to_have_attribute("data-density", "compact")
            assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(246, 241, 232)"
            assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == "light"
            page.screenshot(path=str(OUTPUT / f"{device}-apparence-papier.png"), full_page=True)
            page.reload()
            expect(page.locator('[data-action="appearance-preset"][data-value="paper"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator('[data-action="appearance-accent"][data-value="ocean"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator('[data-action="appearance-density"][data-value="compact"]')).to_have_attribute("aria-pressed", "true")
            page.locator("#app-language").select_option("en")
            expect(page.get_by_role("heading", name="Make Mangadvisor yours")).to_be_visible()
            expect(page.locator("html")).to_have_attribute("data-theme", "paper")
            page.locator('[data-action="appearance-preset"][data-value="noir"]').click()
            expect(page.locator("html")).to_have_attribute("data-theme", "noir")
            assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(9, 10, 13)"
            page.screenshot(path=str(OUTPUT / f"{device}-apparence-noir.png"), full_page=True)
            page.locator("#app-language").select_option("fr")
            page.locator('[data-action="appearance-reset"]').click()
            expect(page.locator("html")).to_have_attribute("data-theme", "night")
            expect(page.locator("html")).to_have_attribute("data-accent", "amber")
            expect(page.locator("html")).to_have_attribute("data-density", "comfortable")
            page.locator('[data-go="/"]').last.click()
            expect(page.locator(".hero h1")).to_be_visible(timeout=30000)

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
            expect(page.locator("#rec-balance")).to_have_value("BALANCED")
            if device=="desktop":
                page.locator("#rec-balance").select_option("EXPLORE")
                page.locator("#rec-submit").click()
                expect(page.locator("#rec-results .rec-quality")).to_be_visible(timeout=60000)
                expect(page.locator("#rec-results .rec-quality")).to_contain_text("Diagnostic de la sélection")
                page.locator("#rec-balance").select_option("BALANCED")
                page.locator("#rec-submit").click()
                expect(page.locator("#rec-results .rec-card").first).to_be_visible(timeout=60000)
                expect(page.locator("#rec-results .profile-context")).to_be_visible(timeout=30000)
                page.locator("#rec-results .profile-context > summary").click()
                expect(page.get_by_text("Mangas utilisés pour construire ton profil")).to_be_visible()
                page.locator("#rec-results .rec-card .reco-explanation > summary").first.click()
                expect(page.locator("#rec-results .rec-card .why-explainer").first).to_be_visible()
                expect(page.locator("#rec-results .rec-card .why-factor").first).to_be_visible()
                expect(page.locator("#rec-results .rec-card").first.get_by_text(
                    "Ressemblances vérifiées avec tes mangas"
                )).to_be_visible()
                expect(page.locator("#rec-results .rec-card .why-explainer").first).to_contain_text(
                    "Ces attributs sont partagés"
                )
                page.screenshot(path=str(OUTPUT / "desktop-preuves-verifiees.png"), full_page=True)
                page.locator("#app-language").select_option("en")
                expect(page.locator("#rec-results .profile-context")).to_be_visible(timeout=30000)
                page.locator("#rec-results .rec-card .reco-explanation > summary").first.click()
                expect(page.get_by_text("What this manga shares with your taste").first).to_be_visible()
                expect(page.get_by_text("Verified similarities with your manga").first).to_be_visible()
                page.locator("#app-language").select_option("fr")
                expect(page.locator("#rec-results .rec-card").first).to_be_visible(timeout=30000)
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

            # V1.2 : fiche française sur un livre distinct du manga canonique.
            page.goto(BASE+"/manga/1",wait_until="domcontentloaded",timeout=60000)
            expect(page.locator("#french-collection")).to_be_visible(timeout=40000)
            expect(page.locator(".edition-item")).to_have_count(1,timeout=30000)
            expect(page.locator(".edition-item")).to_contain_text("Naruto")
            expect(page.locator(".edition-item")).to_contain_text("9782871294146")
            expect(page.locator(".edition-item .edition-actions button")).to_have_count(2)
            # La page conserve l'ancienne fiche et ses données.
            expect(page.locator("#library-editor")).to_be_visible()
            page.screenshot(path=str(OUTPUT / f"{device}-collection-fr.png"),full_page=True)
            if device=="desktop":
                edition_item=page.locator(".edition-item").first
                edition_item.locator('[data-action="volume-owned"]').click()
                expect(page.locator(".collection-stats")).to_contain_text("1")
                expect(page.locator('[data-action="volume-owned"]').first).to_have_attribute("aria-pressed","true")
                page.reload()
                expect(page.locator('[data-action="volume-owned"]').first).to_have_attribute("aria-pressed","true",timeout=30000)
                page.locator("#app-language").select_option("en")
                expect(page.get_by_role("heading",name="French editions and my volumes")).to_be_visible(timeout=30000)
                page.locator("#app-language").select_option("fr")

            assert not errors, f"Erreurs navigateur {device}: {errors}"
            page.close()
        browser.close()
    print("OK : parcours web, fiches, sélection FR/EN et bibliothèque (desktop/mobile).")


if __name__ == "__main__":
    run()
