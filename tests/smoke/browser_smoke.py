"""Vérification de la vraie interface Streamlit avec données fictives et base jetable CI."""
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8501"
OUTPUT = Path("tests/smoke/screenshots")
OUTPUT.mkdir(parents=True, exist_ok=True)


def ready(page):
    page.goto(BASE, wait_until="domcontentloaded", timeout=120000)
    expect(page.get_by_text("Ta prochaine", exact=False).first).to_be_visible(timeout=120000)
    expect(page.get_by_role("tab", name="🔎 Découvrir")).to_be_visible(timeout=90000)


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
            ready(page)
            page.screenshot(path=str(OUTPUT / f"{device}-discover.png"), full_page=True)
            page.get_by_role("tab", name="✨ Pour moi").click()
            expect(page.get_by_text("Des mangas faits pour toi")).to_be_visible(timeout=30000)
            page.screenshot(path=str(OUTPUT / f"{device}-pour-moi.png"), full_page=True)
            page.get_by_role("tab", name="📚 Ma bibliothèque").click()
            expect(page.get_by_text("3. Ma bibliothèque")).to_be_visible(timeout=30000)
            page.screenshot(path=str(OUTPUT / f"{device}-bibliotheque.png"), full_page=True)
            if errors:
                raise AssertionError(f"Erreurs navigateur sur {device}: {errors}")
            page.close()
        browser.close()
    print("OK : interface affichée, 3 vues vérifiées sur PC et mobile.")


if __name__ == "__main__":
    run()
