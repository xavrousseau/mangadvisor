"""Tests réels de la nouvelle interface Mangadvisor avec base CI jetable."""
from pathlib import Path
import json
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
            expect(page.locator('[data-action="generate-mood"]')).to_be_visible(timeout=30000)
            page.locator('[data-action="rec-mode"][data-value="library"]:visible').click()
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
            # Batch import: preview must match only ISBNs already verified in the catalog.
            page.locator("#bulk-import-workspace summary").click()
            expect(page.locator("#bulk-csv-text")).to_be_visible()
            page.locator("#bulk-csv-text").fill(
                "isbn13;possede;lu\n9782871294146;oui;non\n9782344074282;oui;non\n"
            )
            page.locator('[data-action="bulk-preview"]').click()
            expect(page.locator(".bulk-preview")).to_be_visible(timeout=30000)
            expect(page.locator(".bulk-preview h3")).to_have_text("Aperçu de l'import")
            expect(page.locator(".bulk-preview")).to_contain_text("ISBN reconnu")
            expect(page.locator(".bulk-preview")).to_contain_text("ISBN non référencé")
            expect(page.locator(".bulk-preview [data-action='bulk-apply']")).to_be_visible()
            page.screenshot(path=str(OUTPUT / f"{device}-import-csv-apercu.png"), full_page=True)
            # The BnF request is mocked ONLY in this browser test. The real
            # PostgreSQL edition insert is checked separately inside the CI API
            # container, with a patched external BnF lookup.
            resolved={"saved":False,"preview_calls_after_save":0}
            bnf_notice={
                "isbn13":"9782344074282","title_fr":"Monster. Tome 1",
                "author_fr":"Naoki Urasawa","publisher_fr":"Éditeur de démonstration CI",
                "release_date_text":"2002","source_name":"BnF — notice CI simulée",
                "source_url":"https://catalogue.bnf.fr/ark:/12148/cbexample",
                "verified_isbn":True,"edition_kind_suggested":"UNKNOWN",
            }
            def bnf_mock(route):
                route.fulfill(status=200,content_type="application/json",
                              body=json.dumps(bnf_notice))
            def edition_mock(route):
                assert route.request.method=="POST"
                data=route.request.post_data_json
                assert data=={
                    "isbn13":"9782344074282",
                    "edition_kind":"PERFECT",
                    "volume_number":1,
                },data
                resolved["saved"]=True
                route.fulfill(status=201,content_type="application/json",
                              body=json.dumps({"id":100,"manga_id":2,**data}))
            def preview_mock(route):
                reply=route.fetch()
                data=reply.json()
                if resolved["saved"]:
                    resolved["preview_calls_after_save"]+=1
                    row=next(x for x in data["items"] if x["isbn13"]=="9782344074282")
                    row.update({
                        "match":"EXACT_ISBN","edition_id":100,"manga_id":2,
                        "title_fr":"Monster. Tome 1",
                        "edition_kind":"PERFECT","volume_number":1,
                    })
                    data["matched"]+=1;data["unknown"]-=1;data["to_update"]+=1
                route.fulfill(response=reply,body=json.dumps(data))
            page.route("**/api/collection/isbn/9782344074282",bnf_mock)
            page.route("**/api/collection/mangas/2/editions",edition_mock)
            page.route("**/api/collection/import/preview",preview_mock)
            page.locator('[data-action="bulk-resolve"][data-isbn="9782344074282"]').click()
            expect(page.locator("#bulk-resolver .bulk-resolver-notice")).to_be_visible(timeout=30000)
            expect(page.locator("#bulk-resolver")).to_contain_text("Monster. Tome 1")
            page.locator("#bulk-resolve-query").fill("Monster")
            page.locator("#bulk-resolve-search-form button[type=submit]").click()
            expect(page.locator('[data-action="bulk-resolve-select"][data-id="2"]')).to_be_visible(timeout=30000)
            page.locator('[data-action="bulk-resolve-select"][data-id="2"]').click()
            expect(page.locator('[data-action="bulk-resolve-confirm"]')).to_be_disabled()
            page.locator("#bulk-resolve-kind").select_option("PERFECT")
            page.locator("#bulk-resolve-volume").fill("1")
            page.locator("#bulk-resolve-ack").check()
            expect(page.locator('[data-action="bulk-resolve-confirm"]')).to_be_enabled()
            page.screenshot(path=str(OUTPUT / f"{device}-assistant-isbn.png"), full_page=True)
            page.locator('[data-action="bulk-resolve-confirm"]').click()
            expect(page.locator("#bulk-import-result")).to_contain_text(
                "Livre lié à la série",timeout=30000)
            expect(page.locator(".bulk-preview")).to_contain_text(
                "Monster. Tome 1",timeout=30000)
            assert resolved["saved"] and resolved["preview_calls_after_save"]==1,resolved
            page.unroute("**/api/collection/isbn/9782344074282")
            page.unroute("**/api/collection/mangas/2/editions")
            page.unroute("**/api/collection/import/preview")
            page.locator('[data-action="bulk-compare"]').click()
            expect(page.locator(".bulk-reconcile")).to_be_visible(timeout=30000)
            expect(page.locator(".bulk-reconcile")).to_contain_text("Compteurs historiques")

            # V1.2 : fiche française sur un livre distinct du manga canonique.
            page.goto(BASE+"/manga/1",wait_until="domcontentloaded",timeout=60000)
            expect(page.locator("#french-collection")).to_be_visible(timeout=40000)
            expect(page.locator(".fr-notices")).to_be_visible(timeout=30000)
            expect(page.locator(".fr-notices")).to_contain_text("Informations françaises vérifiées")
            expect(page.locator(".fr-notices")).to_contain_text("Kana")
            expect(page.locator(".edition-group")).to_have_count(1)
            expect(page.locator(".edition-group")).to_have_attribute("data-edition-kind","CLASSIC")
            expect(page.locator(".edition-progress")).to_have_count(1)
            expect(page.locator(".edition-progress")).to_contain_text("livres référencés")
            expect(page.locator(".edition-progress")).to_contain_text("Le total des livres publiés")
            expect(page.locator(".edition-progress-track")).to_have_count(2)
            expect(page.locator(".edition-item")).to_have_count(1,timeout=30000)
            expect(page.locator(".edition-item")).to_contain_text("Naruto")
            expect(page.locator(".edition-item")).to_contain_text("9782871294146")
            expect(page.locator(".edition-item .edition-actions button")).to_have_count(2)
            # La page conserve l'ancienne fiche et ses données.
            expect(page.locator("#library-editor")).to_be_visible()
            # BnF title-search response mocked in Chromium only (CI offline).
            candidate_record={
                "isbn13":"9782344074282","title_fr":"Naruto Perfect, tome 1",
                "author_fr":"Masashi Kishimoto","publisher_fr":"Éditeur fictif CI",
                "release_date_text":"2025","language_recorded":"français",
                "source_name":"Bibliothèque nationale de France — Catalogue général",
                "source_url":"https://catalogue.bnf.fr/ark:/12148/cb12345678x",
                "source_checked_at":"2026-10-18T14:00:00Z",
                "status":"CANDIDATE_UNCONFIRMED","manga_match_verified":False,
                "edition_kind_suggested":"PERFECT",
            }
            def title_mock(route):
                assert "Naruto" in route.request.url,route.request.url
                route.fulfill(status=200,content_type="application/json",
                  body=json.dumps({
                    "manga_id":1,"searched_title":"Naruto",
                    "items":[candidate_record],"count":1,
                    "candidate_only":True,"exhaustive":False,
                    "search_scope":"first_page_title_search_only",
                  }))
            def isbn_exact_mock(route):
                record={**candidate_record,"verified_isbn":True}
                route.fulfill(status=200,content_type="application/json",body=json.dumps(record))
            page.route("**/api/collection/mangas/1/discover?*",title_mock)
            page.route("**/api/collection/isbn/9782344074282",isbn_exact_mock)
            expect(page.locator("#fr-bibliography")).to_be_visible()
            page.locator("#fr-bibliography-query").fill("Naruto")
            page.locator('#fr-bibliography-form button[type="submit"]').click()
            expect(page.locator(".biblio-candidate")).to_have_count(1,timeout=30000)
            expect(page.locator(".biblio-candidate")).to_contain_text("association non vérifiée")
            expect(page.locator(".biblio-notice")).to_contain_text("non exhaustifs")
            page.locator('[data-action="biblio-verify-isbn"]').click()
            expect(page.locator("#edition-preview .edition-preview")).to_be_visible(timeout=30000)
            expect(page.locator("#edition-number")).to_have_value("")
            expect(page.locator(".edition-item")).to_have_count(1)
            # The preview is not a write; the user must still choose the volume.
            page.screenshot(path=str(OUTPUT / f"{device}-recherche-bnf-titre.png"),full_page=True)
            # Assisted enrichment is read-only and never auto-confirms a series association.
            enriched=[{
                **candidate_record,"registration_status":"TO_VERIFY",
                "title_clue":"TITLE_WORDS_PRESENT","title_clue_rank":2,
                "registered_manga_id":None
            },{
                **candidate_record,"isbn13":"9782871294146",
                "title_fr":"Naruto. Tome 1","registration_status":"REGISTERED_HERE",
                "registered_manga_id":1,"registered_edition_kind":"CLASSIC",
                "registered_volume_number":1,"title_clue":"TITLE_WORDS_PRESENT",
                "edition_kind_suggested":"CLASSIC"
            },{
                **candidate_record,"isbn13":"9781234567897",
                "title_fr":"Naruto inconnu","registration_status":"REGISTERED_OTHER",
                "registered_manga_id":2,"title_clue":"SOME_TITLE_WORDS",
                "edition_kind_suggested":"UNKNOWN"
            }]
            def enrichment_mock(route):
                url=route.request.url
                assert "alternate_title=Naruto+FR" in url,url
                second="page=2" in url
                if second:
                    sample=[
                        {**enriched[0],"edition_kind_suggested":"PERFECT"},
                        {**candidate_record,"isbn13":"9781234567804",
                         "title_fr":"Naruto Deluxe. Tome 2",
                         "registration_status":"TO_VERIFY",
                         "edition_kind_suggested":"DELUXE",
                         "title_clue":"TITLE_WORDS_PRESENT"}
                    ]
                else:
                    sample=enriched
                route.fulfill(status=200,content_type="application/json",
                    body=json.dumps({
                       "manga_id":1,"searched_titles":["Naruto","Naruto FR"],
                       "items":sample,"count":len(sample),
                       "page":2 if second else 1,"max_pages":3,
                       "has_more_pages":not second,
                       "to_verify_count":2 if second else 1,
                       "registered_here_count":0 if second else 1,
                       "registered_other_count":0 if second else 1,
                       "candidate_only":True,"exhaustive":False,
                       "first_page_per_title_only":not second,"writes_performed":False,
                       "search_errors":[],
                    }))
            page.route("**/api/collection/mangas/1/enrichment*",enrichment_mock)
            expect(page.locator("#fr-enrichment")).to_be_visible()
            page.locator("#enrich-alt-title").fill("Naruto FR")
            page.locator('[data-action="enrich-discover"]').click()
            expect(page.locator(".enrich-candidate")).to_have_count(3,timeout=30000)
            expect(page.locator('[data-action="enrich-verify-isbn"]')).to_have_count(1)
            expect(page.locator(".enrich-stats")).to_contain_text("Déjà lié ailleurs")
            expect(page.locator('[data-action="enrich-more"]')).to_be_visible()
            page.locator('[data-action="enrich-more"]').click()
            expect(page.locator(".enrich-candidate")).to_have_count(4,timeout=30000)
            expect(page.locator(".enrich-format-group")).to_have_count(4)
            expect(page.locator(".enrich-pagination")).to_contain_text("2 / 3")
            expect(page.locator('[data-action="enrich-more"]')).to_have_count(0)
            expect(page.locator('[data-action="enrich-verify-isbn"]')).to_have_count(2)
            page.locator('[data-action="enrich-verify-isbn"][data-isbn="9782344074282"]').click()
            expect(page.locator("#edition-preview .edition-preview")).to_be_visible(timeout=30000)
            expect(page.locator("#edition-number")).to_have_value("")
            expect(page.locator(".edition-item")).to_have_count(1)
            page.screenshot(path=str(OUTPUT / f"{device}-atelier-enrichissement-fr.png"),full_page=True)
            page.unroute("**/api/collection/mangas/1/enrichment*")
            page.unroute("**/api/collection/mangas/1/discover?*")
            page.unroute("**/api/collection/isbn/9782344074282")
            page.screenshot(path=str(OUTPUT / f"{device}-collection-fr.png"),full_page=True)
            if device=="desktop":
                edition_item=page.locator(".edition-item").first
                edition_item.locator('[data-action="volume-owned"]').click()
                expect(page.locator(".collection-stats")).to_contain_text("1")
                expect(page.locator('[data-action="volume-owned"]').first).to_have_attribute("aria-pressed","true")
                expect(page.locator(".edition-progress-track").first).to_have_attribute("aria-valuenow","100")
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
