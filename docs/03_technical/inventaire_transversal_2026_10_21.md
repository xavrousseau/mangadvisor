# Inventaire des fichiers versionnés — Mangadvisor

Dernière photographie de la branche de nettoyage : commit `191ac97306ecac86a41a94be686d4b486bcbaa4c` (21 octobre 2026). Arbre GitHub récursif non tronqué : **282 fichiers suivis**. L'inventaire liste les chemins et leur famille, mais ne certifie pas que chaque ligne de chaque fichier a été testée individuellement.

## Répartition

| Ensemble | Fichiers |
|---|---:|
| `.github` | 4 |
| `(racine)` | 7 |
| `apps` | 52 |
| `cmd` | 8 |
| `data` | 2 |
| `docs` | 65 |
| `infra` | 8 |
| `pipelines` | 22 |
| `sql` | 10 |
| `tests` | 103 |
| `tools` | 1 |
| **Total** | **282** |

## État fonctionnel et décisions

- **Une seule UI** : Streamlit et son Dockerfile, le service et le profil Docker historiques ont été retirés. Le Web héberge l'import CSV/XLSX lecture, les modèles, le profil, le catalogue, le conseiller et les recommandations.
- **Recherche intelligente** : Meilisearch est conservé et réellement intégré à la recherche simple par titre. Les titres EN/JA et alias vérifiés sont indexés sans données personnelles ; PostgreSQL fournit les fiches et reste la source de vérité. Si l'index est absent, la recherche SQL reste disponible. Les filtres combinés et la pagination profonde restent SQL.
- **Indexation** : un script API reconstruit un index temporaire et le permute. Menu `mangadvisor.cmd` → `A` → `22`. La synchronisation incrémentale fine des alias reste une évolution.
- **Sécurité** : ne jamais supprimer `.env`, `private-data/`, `backups/` ni les volumes Docker PostgreSQL/Meilisearch. L'import de lecture est additif et distinct des éditions/ISBN physiques.
- **Rapports de diagnostics** : `analyze_jikan_recommendation_edges.py` et `run_recommendation_profile_tests.py` restent utiles comme outils facultatifs, mais écrivent désormais leurs rapports dans `data/logs/diagnostics/` (ignoré par Git), sans remplacer les anciens résultats figés de `docs/reports/`. Les comptes rendus datés de juin sont des photographies historiques et ne prouvent pas le comportement du moteur actuel.
- **Historique** : les rapports d'audit datés et contradictoires ont été retirés de la version actuelle ; l'historique des commits Git les conserve. Les guides fonctionnels anciens ne doivent pas être interprétés comme la configuration courante.
- **CI** : quatre workflows ont réussi sur le commit `9e5a1d946b7c05a5f48c6e549c45450e83384509`, avant la suppression de quatre rapports obsolètes. Nouvelle validation du dernier HEAD obligatoire avant fusion.
- **Restant** : essais manuels sur Windows et vraie bibliothèque seulement après sauvegarde vérifiée ; enrichissement Meilisearch pour recherche avec filtres ; distinction entre champ fournisseur manquant et suppression volontaire.

## Liste exhaustive des chemins Git

| Chemin | Famille |
|---|---|
| `.dockerignore` | Configuration |
| `.env.example` | Configuration |
| `.gitattributes` | Configuration |
| `.github/workflows/control-center-windows.yml` | GitHub Actions |
| `.github/workflows/integration-v1.yml` | GitHub Actions |
| `.github/workflows/single-web-stack.yml` | GitHub Actions |
| `.github/workflows/verify-python.yml` | GitHub Actions |
| `.gitignore` | Configuration |
| `README.md` | Configuration |
| `apps/api/app/advisor.py` | API |
| `apps/api/app/advisor_ai.py` | API |
| `apps/api/app/advisor_editions.py` | API |
| `apps/api/app/advisor_feedback.py` | API |
| `apps/api/app/advisor_quality.py` | API |
| `apps/api/app/bnf_batch.py` | API |
| `apps/api/app/collection.py` | API |
| `apps/api/app/collection_bulk.py` | API |
| `apps/api/app/collection_scan.py` | API |
| `apps/api/app/edition_discovery.py` | API |
| `apps/api/app/edition_enrichment.py` | API |
| `apps/api/app/inventory_import.py` | API |
| `apps/api/app/inventory_resolution.py` | API |
| `apps/api/app/library_enrichment.py` | API |
| `apps/api/app/library_seed_selection.py` | API |
| `apps/api/app/library_templates.py` | API |
| `apps/api/app/library_xlsx.py` | API |
| `apps/api/app/localization.py` | API |
| `apps/api/app/main.py` | API |
| `apps/api/app/mangadex_discovery.py` | API |
| `apps/api/app/mood_discovery.py` | API |
| `apps/api/app/multilingual_aliases.py` | API |
| `apps/api/app/narrative_evidence.py` | API |
| `apps/api/app/recommendation_explanations.py` | API |
| `apps/api/app/recommendation_quality.py` | API |
| `apps/api/app/search_index.py` | API |
| `apps/api/app/wikidata_enrichment.py` | API |
| `apps/api/requirements.txt` | API |
| `apps/web/assets/advisor-editions.js` | Web |
| `apps/web/assets/advisor-view.js` | Web |
| `apps/web/assets/app.css` | Web |
| `apps/web/assets/app.js` | Web |
| `apps/web/assets/appearance.css` | Web |
| `apps/web/assets/appearance.js` | Web |
| `apps/web/assets/bibliography-view.js` | Web |
| `apps/web/assets/bnf-candidates-view.js` | Web |
| `apps/web/assets/bulk-import-view.js` | Web |
| `apps/web/assets/collection-view.js` | Web |
| `apps/web/assets/enrichment-view.js` | Web |
| `apps/web/assets/explain.js` | Web |
| `apps/web/assets/home.js` | Web |
| `apps/web/assets/i18n.js` | Web |
| `apps/web/assets/inventory-resolution-view.js` | Web |
| `apps/web/assets/isbn-scanner.js` | Web |
| `apps/web/assets/library-display.js` | Web |
| `apps/web/assets/mood-view.js` | Web |
| `apps/web/assets/physical-inventory-view.js` | Web |
| `apps/web/assets/reading-profile.js` | Web |
| `apps/web/assets/unknown-isbn-view.js` | Web |
| `apps/web/assets/wikidata-view.js` | Web |
| `apps/web/index.html` | Web |
| `apps/web/nginx.conf` | Web |
| `cmd/ai-setup.ps1` | Lanceur Windows |
| `cmd/benchmark-mangatheque.ps1` | Lanceur Windows |
| `cmd/control-center.ps1` | Lanceur Windows |
| `cmd/github-sync.ps1` | Lanceur Windows |
| `cmd/import-private-inventory.ps1` | Lanceur Windows |
| `cmd/library-backup.ps1` | Lanceur Windows |
| `cmd/local-api.ps1` | Lanceur Windows |
| `cmd/mobile-setup.ps1` | Lanceur Windows |
| `data/modele_bibliotheque_mangadvisor.csv` | Fichier source versionné |
| `data/modele_bibliotheque_mangadvisor.xlsx` | Fichier source versionné |
| `docs/02_data/data_model_v1.md` | Documentation |
| `docs/02_data/data_pipeline_v1.md` | Documentation |
| `docs/03_technical/infrastructure_single_web_4_5.md` | Documentation |
| `docs/03_technical/inventaire_transversal_2026_10_21.md` | Documentation |
| `docs/03_technical/mangadvisor_architecture_v1.md` | Documentation |
| `docs/03_technical/project_structure.md` | Documentation |
| `docs/04_product/advisor_discovery_balance_3_1.md` | Documentation |
| `docs/04_product/advisor_feedback_learning_3_5.md` | Documentation |
| `docs/04_product/advisor_french_editions_2_3.md` | Documentation |
| `docs/04_product/advisor_library_surprise_3_3.md` | Documentation |
| `docs/04_product/advisor_narrative_safety_2_2.md` | Documentation |
| `docs/04_product/advisor_quality_safety_3_4.md` | Documentation |
| `docs/04_product/appearance_customization.md` | Documentation |
| `docs/04_product/benchmark_sources_4_9.md` | Documentation |
| `docs/04_product/benchmark_sources_v2.md` | Documentation |
| `docs/04_product/bibliographic_staging_v1.md` | Documentation |
| `docs/04_product/bnf_bulk_import_4_8.md` | Documentation |
| `docs/04_product/bulk_collection_import_1_2.md` | Documentation |
| `docs/04_product/catalogue_mal_complet.md` | Documentation |
| `docs/04_product/catalogue_vivant_cycle.md` | Documentation |
| `docs/04_product/control_center_4_0.md` | Documentation |
| `docs/04_product/conversational_advisor_2_1.md` | Documentation |
| `docs/04_product/design_system_v1.md` | Documentation |
| `docs/04_product/discovery_v1.md` | Documentation |
| `docs/04_product/edition_progress_known_isbns_1_2.md` | Documentation |
| `docs/04_product/enrichissement_bnf_progressif_4_0.md` | Documentation |
| `docs/04_product/enrichissement_fr_direct_scrinis.md` | Documentation |
| `docs/04_product/explainable_recommendations_1_1.md` | Documentation |
| `docs/04_product/french_bibliography_discovery_1_2.md` | Documentation |
| `docs/04_product/french_edition_enrichment_2_5.md` | Documentation |
| `docs/04_product/french_edition_enrichment_workshop_2_4.md` | Documentation |
| `docs/04_product/french_editions_collection_1_2.md` | Documentation |
| `docs/04_product/french_records_reliability_1_2.md` | Documentation |
| `docs/04_product/guided_mood_discovery_2_0.md` | Documentation |
| `docs/04_product/inventaire_en_attente_4_3.md` | Documentation |
| `docs/04_product/isbn_camera_scanner_1_2.md` | Documentation |
| `docs/04_product/library_backup_recovery_3_2.md` | Documentation |
| `docs/04_product/library_enrichment_one_click_4_2.md` | Documentation |
| `docs/04_product/library_recommendations_4_7.md` | Documentation |
| `docs/04_product/local_ai_advisor_3_0.md` | Documentation |
| `docs/04_product/manga_covers_v1.md` | Documentation |
| `docs/04_product/manual_pending_inventory_reconciliation_4_3.md` | Documentation |
| `docs/04_product/mobile_https_scan_session_2_0.md` | Documentation |
| `docs/04_product/multilingual_aliases_4_4.md` | Documentation |
| `docs/04_product/physical_inventory_dashboard_3_9.md` | Documentation |
| `docs/04_product/private_library_benchmark_3_6.md` | Documentation |
| `docs/04_product/recommendation_feedback_1_1.md` | Documentation |
| `docs/04_product/recommendation_quality_1_1.md` | Documentation |
| `docs/04_product/recommendations_v1.md` | Documentation |
| `docs/04_product/resolve_unknown_isbns_1_2.md` | Documentation |
| `docs/04_product/roadmap_mangadvisor_1_1_to_2_0.md` | Documentation |
| `docs/04_product/safe_inventory_import_3_8.md` | Documentation |
| `docs/04_product/verified_source_links_1_1.md` | Documentation |
| `docs/04_product/web_experience_bilingual.md` | Documentation |
| `docs/04_product/wikidata_metadata_enrichment_4_1.md` | Documentation |
| `docs/STABILISATION_V0_8.md` | Documentation |
| `docs/recommandation_tests_v0_6.md` | Documentation |
| `docs/reports/Mangadvisor V0.7 Data Foundation.docx` | Documentation |
| `docs/reports/jikan_recommendation_edges_diagnostic.md` | Documentation |
| `docs/reports/library_goal_tests_v0_8_3.md` | Documentation |
| `docs/reports/library_import_robustness_tests_v0_8_11.md` | Documentation |
| `docs/reports/library_import_tests_v0_8_10.md` | Documentation |
| `docs/reports/library_recommendation_tests_v0_8_2_profile_summary.md` | Documentation |
| `docs/reports/library_status_tests_v0_8_5.md` | Documentation |
| `docs/reports/recommendation_profile_tests_latest.md` | Documentation |
| `infra/compose/docker-compose.dev.yml` | Docker |
| `infra/compose/docker-compose.local.yml` | Docker |
| `infra/compose/docker-compose.mobile.yml` | Docker |
| `infra/compose/docker-compose.yml` | Docker |
| `infra/docker/api/Dockerfile` | Docker |
| `infra/docker/engine/Dockerfile` | Docker |
| `infra/docker/web/Dockerfile` | Docker |
| `infra/mobile/Caddyfile` | Docker |
| `mangadvisor.cmd` | Lanceur Windows |
| `pipelines/__init__.py` | Collecte / données |
| `pipelines/engine/requirements.txt` | Collecte / données |
| `pipelines/engine/scripts/analyze_jikan_recommendation_edges.py` | Collecte / données |
| `pipelines/engine/scripts/benchmark_manga_sources.py` | Collecte / données |
| `pipelines/engine/scripts/benchmark_manga_sources_v2.py` | Collecte / données |
| `pipelines/engine/scripts/bnf_bulk_import.py` | Collecte / données |
| `pipelines/engine/scripts/catalogue_french_matching.py` | Collecte / données |
| `pipelines/engine/scripts/catalogue_lifecycle.py` | Collecte / données |
| `pipelines/engine/scripts/catalogue_mangaupdates.py` | Collecte / données |
| `pipelines/engine/scripts/check_network.py` | Collecte / données |
| `pipelines/engine/scripts/enrich_catalogue_scrinis_fr.py` | Collecte / données |
| `pipelines/engine/scripts/extract_jikan.py` | Collecte / données |
| `pipelines/engine/scripts/extract_jikan_recommendations.py` | Collecte / données |
| `pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py` | Collecte / données |
| `pipelines/engine/scripts/load_jikan_to_postgres.py` | Collecte / données |
| `pipelines/engine/scripts/prepare_bibliographic_staging.py` | Collecte / données |
| `pipelines/engine/scripts/run_recommendation_profile_tests.py` | Collecte / données |
| `pipelines/engine/scripts/sync_full_mal_catalogue.py` | Collecte / données |
| `pipelines/engine/src/__init__.py` | Collecte / données |
| `pipelines/engine/src/extract/__init__.py` | Collecte / données |
| `pipelines/engine/src/load/__init__.py` | Collecte / données |
| `pipelines/engine/src/load/postgres_loader.py` | Collecte / données |
| `pyproject.toml` | Configuration |
| `sql/queries/check_jikan_data_quality.sql` | Modèle SQL |
| `sql/queries/check_jikan_source_data.sql` | Modèle SQL |
| `sql/queries/inspect_jikan_attributes.sql` | Modèle SQL |
| `sql/schema/001_jikan_source_tables.sql` | Modèle SQL |
| `sql/schema/002_canonical_manga_tables.sql` | Modèle SQL |
| `sql/schema/003_build_canonical_from_jikan.sql` | Modèle SQL |
| `sql/schema/004_add_theme_demographic_tables.sql` | Modèle SQL |
| `sql/schema/005_build_theme_demographic_from_jikan.sql` | Modèle SQL |
| `sql/schema/006_add_jikan_recommendation_tables.sql` | Modèle SQL |
| `sql/schema/007_add_user_library_tables.sql` | Modèle SQL |
| `tests/integration/guided-ingestion-smoke.sh` | Test automatisé |
| `tests/smoke/advisor_browser.py` | Test automatisé |
| `tests/smoke/advisor_ownership_smoke.py` | Test automatisé |
| `tests/smoke/advisor_smoke.py` | Test automatisé |
| `tests/smoke/browser_smoke.py` | Test automatisé |
| `tests/smoke/collection_bulk_smoke.py` | Test automatisé |
| `tests/smoke/collection_smoke.py` | Test automatisé |
| `tests/smoke/explanations_smoke.py` | Test automatisé |
| `tests/smoke/feedback_smoke.py` | Test automatisé |
| `tests/smoke/inventory_import_smoke.py` | Test automatisé |
| `tests/smoke/isbn_camera_browser.py` | Test automatisé |
| `tests/smoke/mood_discovery_browser.py` | Test automatisé |
| `tests/smoke/mood_discovery_smoke.py` | Test automatisé |
| `tests/smoke/ownership_exclusion_smoke.py` | Test automatisé |
| `tests/smoke/physical_inventory_browser.py` | Test automatisé |
| `tests/smoke/quality_smoke.py` | Test automatisé |
| `tests/smoke/reading_library_browser.py` | Test automatisé |
| `tests/smoke/rebuild_safety_smoke.py` | Test automatisé |
| `tests/smoke/resolve_unknown_db.py` | Test automatisé |
| `tests/smoke/seed_advisor.sql` | Test automatisé |
| `tests/smoke/seed_catalog.sql` | Test automatisé |
| `tests/smoke/seed_fr_editions.sql` | Test automatisé |
| `tests/test_advisor_ai.py` | Test automatisé |
| `tests/test_advisor_balance.py` | Test automatisé |
| `tests/test_advisor_editions.py` | Test automatisé |
| `tests/test_advisor_feedback_learning.py` | Test automatisé |
| `tests/test_advisor_library_surprise.py` | Test automatisé |
| `tests/test_advisor_ownership_fallback.py` | Test automatisé |
| `tests/test_advisor_quality.py` | Test automatisé |
| `tests/test_bibliographic_staging.py` | Test automatisé |
| `tests/test_bnf_batch.py` | Test automatisé |
| `tests/test_bnf_bulk_import.py` | Test automatisé |
| `tests/test_catalogue_api_metadata.py` | Test automatisé |
| `tests/test_catalogue_french_matching.py` | Test automatisé |
| `tests/test_catalogue_lifecycle.py` | Test automatisé |
| `tests/test_catalogue_scrinis_fr_direct.py` | Test automatisé |
| `tests/test_catalogue_sources_benchmark.py` | Test automatisé |
| `tests/test_catalogue_sources_benchmark_v2.py` | Test automatisé |
| `tests/test_check_network.py` | Test automatisé |
| `tests/test_collection_bulk.py` | Test automatisé |
| `tests/test_collection_fr.py` | Test automatisé |
| `tests/test_collection_routes.py` | Test automatisé |
| `tests/test_collection_scan.py` | Test automatisé |
| `tests/test_conversational_advisor.py` | Test automatisé |
| `tests/test_cover_api.py` | Test automatisé |
| `tests/test_discovery.py` | Test automatisé |
| `tests/test_edition_discovery.py` | Test automatisé |
| `tests/test_edition_enrichment.py` | Test automatisé |
| `tests/test_extended_tenrai_catalogue.py` | Test automatisé |
| `tests/test_feedback.py` | Test automatisé |
| `tests/test_full_mal_catalogue_sync.py` | Test automatisé |
| `tests/test_inventory_import.py` | Test automatisé |
| `tests/test_inventory_resolution.py` | Test automatisé |
| `tests/test_jikan_metadata_merge.py` | Test automatisé |
| `tests/test_legacy_library_csv_contracts.py` | Test automatisé |
| `tests/test_legacy_recommendation_contracts.py` | Test automatisé |
| `tests/test_library_enrichment.py` | Test automatisé |
| `tests/test_library_import_match_safety.py` | Test automatisé |
| `tests/test_library_seed_selection.py` | Test automatisé |
| `tests/test_library_templates.py` | Test automatisé |
| `tests/test_library_xlsx.py` | Test automatisé |
| `tests/test_localization.py` | Test automatisé |
| `tests/test_mangadex_discovery.py` | Test automatisé |
| `tests/test_meilisearch_catalogue.py` | Test automatisé |
| `tests/test_mood_discovery.py` | Test automatisé |
| `tests/test_multilingual_aliases.py` | Test automatisé |
| `tests/test_physical_inventory_summary.py` | Test automatisé |
| `tests/test_pipeline_failure_modes.py` | Test automatisé |
| `tests/test_recommendation_explanations.py` | Test automatisé |
| `tests/test_recommendation_ingestion_health.py` | Test automatisé |
| `tests/test_recommendation_quality.py` | Test automatisé |
| `tests/test_repository_hygiene.py` | Test automatisé |
| `tests/test_repository_safety.py` | Test automatisé |
| `tests/test_single_web_deployment.py` | Test automatisé |
| `tests/test_stabilisation_safety.py` | Test automatisé |
| `tests/test_tenrai_migration.py` | Test automatisé |
| `tests/test_web_proxy_lifecycle.py` | Test automatisé |
| `tests/test_wikidata_enrichment.py` | Test automatisé |
| `tests/test_windows_powershell51_encoding.py` | Test automatisé |
| `tests/web/advisor-editions.test.mjs` | Test automatisé |
| `tests/web/advisor-view.test.mjs` | Test automatisé |
| `tests/web/appearance.test.mjs` | Test automatisé |
| `tests/web/bibliography.test.mjs` | Test automatisé |
| `tests/web/bnf-candidates.test.mjs` | Test automatisé |
| `tests/web/bulk-import.test.mjs` | Test automatisé |
| `tests/web/collection.test.mjs` | Test automatisé |
| `tests/web/enrichment.test.mjs` | Test automatisé |
| `tests/web/explain.test.mjs` | Test automatisé |
| `tests/web/home.test.mjs` | Test automatisé |
| `tests/web/inventory-resolution.test.mjs` | Test automatisé |
| `tests/web/isbn-scanner.test.mjs` | Test automatisé |
| `tests/web/library-display.test.mjs` | Test automatisé |
| `tests/web/manga-detail-route.test.mjs` | Test automatisé |
| `tests/web/mood-view.test.mjs` | Test automatisé |
| `tests/web/physical-inventory.test.mjs` | Test automatisé |
| `tests/web/reading-library-import.test.mjs` | Test automatisé |
| `tests/web/reading-profile.test.mjs` | Test automatisé |
| `tests/web/unknown-isbn.test.mjs` | Test automatisé |
| `tests/web/wikidata-view.test.mjs` | Test automatisé |
| `tests/windows/test-github-sync.ps1` | Test automatisé |
| `tests/windows/test-menu-import-backup.ps1` | Test automatisé |
| `tests/windows/test-menu-return.ps1` | Test automatisé |
| `tests/windows/test-safe-git-update.ps1` | Test automatisé |
| `tools/audit_repository.py` | Contrôle du dépôt |

**Fusion :** la PR #89 reste en brouillon. Ne pas fusionner sans accord explicite et sans quatre contrôles CI réussis sur son dernier commit.
