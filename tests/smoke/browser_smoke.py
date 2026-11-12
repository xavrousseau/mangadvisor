"""Recette navigateur UX MangAxiom sur catalogue PostgreSQL jetable de la CI.

Les anciens ateliers CSV/ISBN ne font plus partie de l'interface V1.
Leurs tests métier/API restent dans les suites distinctes de tests Python.
"""
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8501"
OUTPUT = Path("tests/smoke/screenshots")
OUTPUT.mkdir(parents=True, exist_ok=True)


def assert_no_horizontal_overflow(page, device):
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > window.innerWidth + 2"
    )
    assert not overflow, f"Débordement horizontal : {device}"


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for device, width, height in [
                ("desktop", 1440, 960),
                ("tablet", 820, 1180),
                ("mobile", 390, 844),
                ("small-mobile", 320, 700),
            ]:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                )
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                try:
                    page.goto(BASE, wait_until="domcontentloaded", timeout=120000)
                    expect(page.locator(".hero h1")).to_be_visible(timeout=90000)
                    expect(page.locator("#home-cards .manga-card").first).to_be_visible(
                        timeout=60000
                    )
                    expect(page.locator(".home-axiom-card")).to_be_visible()
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(
                        path=str(OUTPUT / f"{device}-accueil.png"), full_page=True
                    )

                    # Axiom est un chatbot sur l'accueil et non un menu ou un
                    # mode obligatoire de la page de recommandations.
                    assert page.locator(".nav-link").count() == 5
                    assert page.locator(".nav-link").filter(
                        has_text="Axiom"
                    ).count() == 0
                    page.locator('[data-action="axiom-open"]').click()
                    expect(page.locator("#axiom-overlay")).to_be_visible()
                    expect(page.locator("#advisor-form")).to_be_visible()
                    page.locator('[data-action="axiom-close"]').click()
                    expect(page.locator("#axiom-overlay")).to_be_hidden()

                    page.locator('[data-go="/discover"]').first.click()
                    expect(page).to_have_url(BASE + "/discover", timeout=30000)
                    expect(page.locator("#catalog-results .manga-card").first).to_be_visible(
                        timeout=40000
                    )
                    assert page.locator("#catalog-results .pagination").count() == 0
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(
                        path=str(OUTPUT / f"{device}-explorer.png"), full_page=True
                    )

                    # Ajout depuis Explorer, sans écraser les notes et comptes
                    # existants. La CI n'utilise que ses données jetables.
                    first_card = page.locator("#catalog-results .manga-card").first
                    first_card.locator('[data-action="quick-add-toggle"]').click()
                    menu = first_card.locator(".quick-add-menu")
                    expect(menu).to_be_visible()
                    menu.locator('[data-status="WANT_TO_READ"]').click()
                    expect(menu).to_be_hidden(timeout=30000)

                    # Recherche et fiche utilisent la vraie API de test.
                    page.locator("#catalog-query").fill("Monster")
                    expect(page.locator("#catalog-results .manga-card").first).to_be_visible(
                        timeout=30000
                    )
                    page.locator("#catalog-results .manga-card .card-open").first.click()
                    expect(page.locator(".detail-hero h1")).to_be_visible(timeout=30000)
                    expect(page.locator("#library-editor")).to_be_visible()
                    expect(page.locator("#edit-owned-volumes")).to_be_visible()
                    expect(page.locator("#edit-read-volumes")).to_be_visible()
                    assert page.locator('[data-action="open-scanner"]:visible').count() == 0
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(
                        path=str(OUTPUT / f"{device}-fiche.png"), full_page=True
                    )

                    # Pour moi garde ses recommandations et les preuves métier.
                    page.locator('[data-go="/for-you"]').first.click()
                    expect(page).to_have_url(BASE + "/for-you", timeout=30000)
                    expect(page.locator('[data-action="generate-mood"]')).to_be_visible(
                        timeout=30000
                    )
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(
                        path=str(OUTPUT / f"{device}-pour-moi.png"), full_page=True
                    )

                    # Mangathèque = séries + envies, pas d'import CSV visible.
                    page.locator('[data-go="/library"]').first.click()
                    expect(page).to_have_url(BASE + "/library", timeout=30000)
                    expect(page.locator("#library-series-panel .manga-card").first).to_be_visible(
                        timeout=30000
                    )
                    assert page.locator('.library-view-tab[data-value="manage"]').count() == 0
                    assert page.locator(".pagination:visible").count() == 0
                    assert page.locator('input[type="file"]:visible').count() == 0
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(
                        path=str(OUTPUT / f"{device}-mangatheque.png"), full_page=True
                    )

                    # Profil alimenté par l'API réelle de lecture.
                    page.locator('[data-go="/profile"]').first.click()
                    expect(page).to_have_url(BASE + "/profile", timeout=30000)
                    expect(page.locator("#profile-summary .reading-profile")).to_be_visible(timeout=30000)
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(path=str(OUTPUT / f"{device}-profil.png"), full_page=True)

                    # Les formulaires sont des maquettes UI, pas un faux login.
                    page.locator('[data-go="/login"]').first.click()
                    expect(page.locator("#auth-ui-form")).to_be_visible()
                    page.locator('[data-go="/register"]').first.click()
                    expect(page.locator("#auth-pseudo")).to_be_visible()
                    expect(page.locator(".auth-note")).to_contain_text("raccordés au backend")
                    assert_no_horizontal_overflow(page, device)
                    page.screenshot(path=str(OUTPUT / f"{device}-inscription.png"), full_page=True)

                    assert not errors, f"Erreurs JavaScript {device}: {errors}"
                    print(f"MangAxiom UX browser smoke OK : {device}")
                finally:
                    page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    run()
