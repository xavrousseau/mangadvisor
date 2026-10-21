# Inventaire transversal du dépôt Mangadvisor — 21 octobre 2026

> **Périmètre exact :** branche `cleanup/pipelines-2026-10-21`, commit `dbf5a8a0517bea066825c2993123b0635149c0bd`. Liste extraite de l'arbre Git récursif GitHub (`truncated=false`). **284 fichiers suivis**. Cet inventaire fournit une décision de traitement *par catégorie* pour chaque chemin : il ne constitue pas une revue manuelle du contenu de chacune des 284 sources.

## Dénombrement

| Ensemble | Nombre de fichiers |
|---|---:|
| `.github` | 4 |
| `(racine)` | 7 |
| `apps` | 51 |
| `cmd` | 8 |
| `data` | 2 |
| `docs` | 69 |
| `infra` | 8 |
| `pipelines` | 22 |
| `sql` | 10 |
| `tests` | 102 |
| `tools` | 1 |
| **TOTAL** | **284** |

## Résultats de contrôle transversal

- **Références anciennes dans les points d'entrée actifs :** les lanceurs, quatre workflows et smoke principal vérifiés ne référencent plus les six scripts retirés ; un test automatique a été ajouté dans `tests/test_repository_hygiene.py` pour les chemins exécutables pertinents. **Les mentions historiques dans les rapports ne sont pas des dépendances exécutables**.
- **Cohérence Docker :** un nouveau `.dockerignore` exclut fichiers privés, sauvegardes, caches et données téléchargées du contexte de construction ; contrôle dans la suite de tests. Les images API/Web/engine conservent leurs sources.
- **Données personnelles :** aucune suppression de volumes et aucune opération de reconstruction contre une base personnelle. Reconstruction contrôlée exclusivement en CI sur base jetable.
- **Contrats SQL :** restauration et liens de bibliothèque à protéger ; mise à jour canonique additive et refus des titres de source vides.
- **Documentation :** plusieurs guides décrivent encore des fonctionnalités historiques. Les documentations V1 doivent rester explicitement des archives de conception ; le README et la structure courante font référence.
- **Interface Web unique :** Streamlit supprimé après migration des fonctions utiles et des tests ; parcours de lecture CSV/XLSX et import ISBN distincts.
- **Réserves :** Meilisearch déclaré mais sans client actif identifié (volume conservé), suppression intentionnelle de métadonnées fournisseur non gérée, contrôle local sur Windows distinct de la CI.

## Registre complet des fichiers

> Liste des fichiers suivis à ce commit. Le rôle est classé par famille ; cela ne vaut pas une revue fonctionnelle individuelle ligne par ligne.

| Chemin suivi | Rôle |
|---|---|
| `.dockerignore` | Configuration / racine |
| `.env.example` | Configuration / racine |
| `.gitattributes` | Configuration / racine |
| `.github/workflows/control-center-windows.yml` | CI automatisée |
| `.github/workflows/integration-v1.yml` | CI automatisée |
| `.github/workflows/single-web-stack.yml` | CI automatisée |
| `.github/workflows/verify-python.yml` | CI automatisée |
| `.gitignore` | Configuration / racine |
| `README.md` | Configuration / racine |
| `apps/api/app/advisor.py` | API active |
| `apps/api/app/advisor_ai.py` | API active |
| `apps/api/app/advisor_editions.py` | API active |
| `apps/api/app/advisor_feedback.py` | API active |
| `apps/api/app/advisor_quality.py` | API active |
| `apps/api/app/bnf_batch.py` | API active |
| `apps/api/app/collection.py` | API active |
| `apps/api/app/collection_bulk.py` | API active |
| `apps/api/app/collection_scan.py` | API active |
| `apps/api/app/edition_discovery.py` | API active |
| `apps/api/app/edition_enrichment.py` | API active |
| `apps/api/app/inventory_import.py` | API active |
| `apps/api/app/inventory_resolution.py` | API active |
| `apps/api/app/library_enrichment.py` | API active |
| `apps/api/app/library_seed_selection.py` | API active |
| `apps/api/app/library_templates.py` | API active |
| `apps/api/app/library_xlsx.py` | API active |
| `apps/api/app/localization.py` | API active |
| `apps/api/app/main.py` | API active |
| `apps/api/app/mangadex_discovery.py` | API active |
| `apps/api/app/mood_discovery.py` | API active |
| `apps/api/app/multilingual_aliases.py` | API active |
| `apps/api/app/narrative_evidence.py` | API active |
| `apps/api/app/recommendation_explanations.py` | API active |
| `apps/api/app/recommendation_quality.py` | API active |
| `apps/api/app/wikidata_enrichment.py` | API active |
| `apps/api/requirements.txt` | API active |
| `apps/web/assets/advisor-editions.js` | Web actif unique |
| `apps/web/assets/advisor-view.js` | Web actif unique |
| `apps/web/assets/app.css` | Web actif unique |
| `apps/web/assets/app.js` | Web actif unique |
| `apps/web/assets/appearance.css` | Web actif unique |
| `apps/web/assets/appearance.js` | Web actif unique |
| `apps/web/assets/bibliography-view.js` | Web actif unique |
| `apps/web/assets/bnf-candidates-view.js` | Web actif unique |
| `apps/web/assets/bulk-import-view.js` | Web actif unique |
| `apps/web/assets/collection-view.js` | Web actif unique |
| `apps/web/assets/enrichment-view.js` | Web actif unique |
| `apps/web/assets/explain.js` | Web actif unique |
| `apps/web/assets/home.js` | Web actif unique |
| `apps/web/assets/i18n.js` | Web actif unique |
| `apps/web/assets/inventory-resolution-view.js` | Web actif unique |
| `apps/web/assets/isbn-scanner.js` | Web actif unique |
| `apps/web/assets/library-display.js` | Web actif unique |
| `apps/web/assets/mood-view.js` | Web actif unique |
| `apps/web/assets/physical-inventory-view.js` | Web actif unique |
| `apps/web/assets/reading-profile.js` | Web actif unique |
| `apps/web/assets/unknown-isbn-view.js` | Web actif unique |
| `apps/web/assets/wikidata-view.js` | Web actif unique |
| `apps/web/index.html` | Web actif unique |
| `apps/web/nginx.conf` | Web actif unique |
| `cmd/ai-setup.ps1` | Menu Windows / script |
| `cmd/benchmark-mangatheque.ps1` | Menu Windows / script |
| `cmd/control-center.ps1` | Menu Windows / script |
| `cmd/github-sync.ps1` | Menu Windows / script |
| `cmd/import-private-inventory.ps1` | Menu Windows / script |
| `cmd/library-backup.ps1` | Menu Windows / script |
| `cmd/local-api.ps1` | Menu Windows / script |
| `cmd/mobile-setup.ps1` | Menu Windows / script |
| `data/modele_bibliotheque_mangadvisor.csv` | Fichier de référence public |
| `data/modele_bibliotheque_mangadvisor.xlsx` | Fichier de référence public |
| `docs/02_data/data_model_v1.md` | Documentation / guide |
| `docs/02_data/data_pipeline_v1.md` | Documentation / guide |
| `docs/03_technical/audit_transversal_4_4.md` | Documentation / guide |
| `docs/03_technical/cleanup_4_1.md` | Documentation / guide |
| `docs/03_technical/infrastructure_single_web_4_5.md` | Documentation / guide |
| `docs/03_technical/inventaire_transversal_2026_10_21.md` | Documentation / guide |
| `docs/03_technical/mangadvisor_architecture_v1.md` | Documentation / guide |
| `docs/03_technical/project_structure.md` | Documentation / guide |
| `docs/04_product/advisor_discovery_balance_3_1.md` | Documentation / guide |
| `docs/04_product/advisor_feedback_learning_3_5.md` | Documentation / guide |
| `docs/04_product/advisor_french_editions_2_3.md` | Documentation / guide |
| `docs/04_product/advisor_library_surprise_3_3.md` | Documentation / guide |
| `docs/04_product/advisor_narrative_safety_2_2.md` | Documentation / guide |
| `docs/04_product/advisor_quality_safety_3_4.md` | Documentation / guide |
| `docs/04_product/appearance_customization.md` | Documentation / guide |
| `docs/04_product/benchmark_sources_4_9.md` | Documentation / guide |
| `docs/04_product/benchmark_sources_v2.md` | Documentation / guide |
| `docs/04_product/bibliographic_staging_v1.md` | Documentation / guide |
| `docs/04_product/bnf_bulk_import_4_8.md` | Documentation / guide |
| `docs/04_product/bulk_collection_import_1_2.md` | Documentation / guide |
| `docs/04_product/catalogue_mal_complet.md` | Documentation / guide |
| `docs/04_product/catalogue_vivant_cycle.md` | Documentation / guide |
| `docs/04_product/control_center_4_0.md` | Documentation / guide |
| `docs/04_product/conversational_advisor_2_1.md` | Documentation / guide |
| `docs/04_product/design_system_v1.md` | Documentation / guide |
| `docs/04_product/discovery_v1.md` | Documentation / guide |
| `docs/04_product/edition_progress_known_isbns_1_2.md` | Documentation / guide |
| `docs/04_product/enrichissement_bnf_progressif_4_0.md` | Documentation / guide |
| `docs/04_product/enrichissement_fr_direct_scrinis.md` | Documentation / guide |
| `docs/04_product/explainable_recommendations_1_1.md` | Documentation / guide |
| `docs/04_product/french_bibliography_discovery_1_2.md` | Documentation / guide |
| `docs/04_product/french_edition_enrichment_2_5.md` | Documentation / guide |
| `docs/04_product/french_edition_enrichment_workshop_2_4.md` | Documentation / guide |
| `docs/04_product/french_editions_collection_1_2.md` | Documentation / guide |
| `docs/04_product/french_records_reliability_1_2.md` | Documentation / guide |
| `docs/04_product/guided_mood_discovery_2_0.md` | Documentation / guide |
| `docs/04_product/inventaire_en_attente_4_3.md` | Documentation / guide |
| `docs/04_product/isbn_camera_scanner_1_2.md` | Documentation / guide |
| `docs/04_product/library_backup_recovery_3_2.md` | Documentation / guide |
| `docs/04_product/library_enrichment_one_click_4_2.md` | Documentation / guide |
| `docs/04_product/library_recommendations_4_7.md` | Documentation / guide |
| `docs/04_product/local_ai_advisor_3_0.md` | Documentation / guide |
| `docs/04_product/manga_covers_v1.md` | Documentation / guide |
| `docs/04_product/manual_pending_inventory_reconciliation_4_3.md` | Documentation / guide |
| `docs/04_product/mobile_https_scan_session_2_0.md` | Documentation / guide |
| `docs/04_product/multilingual_aliases_4_4.md` | Documentation / guide |
| `docs/04_product/physical_inventory_dashboard_3_9.md` | Documentation / guide |
| `docs/04_product/private_library_benchmark_3_6.md` | Documentation / guide |
| `docs/04_product/recommendation_feedback_1_1.md` | Documentation / guide |
| `docs/04_product/recommendation_quality_1_1.md` | Documentation / guide |
| `docs/04_product/recommendations_v1.md` | Documentation / guide |
| `docs/04_product/resolve_unknown_isbns_1_2.md` | Documentation / guide |
| `docs/04_product/roadmap_mangadvisor_1_1_to_2_0.md` | Documentation / guide |
| `docs/04_product/safe_inventory_import_3_8.md` | Documentation / guide |
| `docs/04_product/verified_source_links_1_1.md` | Documentation / guide |
| `docs/04_product/web_experience_bilingual.md` | Documentation / guide |
| `docs/04_product/wikidata_metadata_enrichment_4_1.md` | Documentation / guide |
| `docs/STABILISATION_V0_8.md` | Documentation / guide |
| `docs/recommandation_tests_v0_6.md` | Documentation / guide |
| `docs/reports/Mangadvisor V0.7 Data Foundation.docx` | Documentation / guide |
| `docs/reports/jikan_recommendation_edges_diagnostic.md` | Documentation / guide |
| `docs/reports/library_goal_tests_v0_8_3.md` | Documentation / guide |
| `docs/reports/library_import_robustness_tests_v0_8_11.md` | Documentation / guide |
| `docs/reports/library_import_tests_v0_8_10.md` | Documentation / guide |
| `docs/reports/library_recommendation_tests_v0_8_2_profile_summary.md` | Documentation / guide |
| `docs/reports/library_status_tests_v0_8_5.md` | Documentation / guide |
| `docs/reports/recommendation_profile_tests_latest.md` | Documentation / guide |
| `docs/reports/repository_audit_2026_10_19.md` | Documentation / guide |
| `docs/reports/repository_audit_2026_10_20.md` | Documentation / guide |
| `infra/compose/docker-compose.dev.yml` | Infrastructure active |
| `infra/compose/docker-compose.local.yml` | Infrastructure active |
| `infra/compose/docker-compose.mobile.yml` | Infrastructure active |
| `infra/compose/docker-compose.yml` | Infrastructure active |
| `infra/docker/api/Dockerfile` | Infrastructure active |
| `infra/docker/engine/Dockerfile` | Infrastructure active |
| `infra/docker/web/Dockerfile` | Infrastructure active |
| `infra/mobile/Caddyfile` | Infrastructure active |
| `mangadvisor.cmd` | Menu Windows / script |
| `pipelines/__init__.py` | Pipeline actif |
| `pipelines/engine/requirements.txt` | Pipeline actif |
| `pipelines/engine/scripts/analyze_jikan_recommendation_edges.py` | Pipeline actif |
| `pipelines/engine/scripts/benchmark_manga_sources.py` | Pipeline actif |
| `pipelines/engine/scripts/benchmark_manga_sources_v2.py` | Pipeline actif |
| `pipelines/engine/scripts/bnf_bulk_import.py` | Pipeline actif |
| `pipelines/engine/scripts/catalogue_french_matching.py` | Pipeline actif |
| `pipelines/engine/scripts/catalogue_lifecycle.py` | Pipeline actif |
| `pipelines/engine/scripts/catalogue_mangaupdates.py` | Pipeline actif |
| `pipelines/engine/scripts/check_network.py` | Pipeline actif |
| `pipelines/engine/scripts/enrich_catalogue_scrinis_fr.py` | Pipeline actif |
| `pipelines/engine/scripts/extract_jikan.py` | Pipeline actif |
| `pipelines/engine/scripts/extract_jikan_recommendations.py` | Pipeline actif |
| `pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py` | Pipeline actif |
| `pipelines/engine/scripts/load_jikan_to_postgres.py` | Pipeline actif |
| `pipelines/engine/scripts/prepare_bibliographic_staging.py` | Pipeline actif |
| `pipelines/engine/scripts/run_recommendation_profile_tests.py` | Pipeline actif |
| `pipelines/engine/scripts/sync_full_mal_catalogue.py` | Pipeline actif |
| `pipelines/engine/src/__init__.py` | Pipeline actif |
| `pipelines/engine/src/extract/__init__.py` | Pipeline actif |
| `pipelines/engine/src/load/__init__.py` | Pipeline actif |
| `pipelines/engine/src/load/postgres_loader.py` | Pipeline actif |
| `pyproject.toml` | Configuration / racine |
| `sql/queries/check_jikan_data_quality.sql` | Schéma / diagnostic |
| `sql/queries/check_jikan_source_data.sql` | Schéma / diagnostic |
| `sql/queries/inspect_jikan_attributes.sql` | Schéma / diagnostic |
| `sql/schema/001_jikan_source_tables.sql` | Schéma / diagnostic |
| `sql/schema/002_canonical_manga_tables.sql` | Schéma / diagnostic |
| `sql/schema/003_build_canonical_from_jikan.sql` | Schéma / diagnostic |
| `sql/schema/004_add_theme_demographic_tables.sql` | Schéma / diagnostic |
| `sql/schema/005_build_theme_demographic_from_jikan.sql` | Schéma / diagnostic |
| `sql/schema/006_add_jikan_recommendation_tables.sql` | Schéma / diagnostic |
| `sql/schema/007_add_user_library_tables.sql` | Schéma / diagnostic |
| `tests/integration/guided-ingestion-smoke.sh` | Tests automatisés |
| `tests/smoke/advisor_browser.py` | Tests automatisés |
| `tests/smoke/advisor_ownership_smoke.py` | Tests automatisés |
| `tests/smoke/advisor_smoke.py` | Tests automatisés |
| `tests/smoke/browser_smoke.py` | Tests automatisés |
| `tests/smoke/collection_bulk_smoke.py` | Tests automatisés |
| `tests/smoke/collection_smoke.py` | Tests automatisés |
| `tests/smoke/explanations_smoke.py` | Tests automatisés |
| `tests/smoke/feedback_smoke.py` | Tests automatisés |
| `tests/smoke/inventory_import_smoke.py` | Tests automatisés |
| `tests/smoke/isbn_camera_browser.py` | Tests automatisés |
| `tests/smoke/mood_discovery_browser.py` | Tests automatisés |
| `tests/smoke/mood_discovery_smoke.py` | Tests automatisés |
| `tests/smoke/ownership_exclusion_smoke.py` | Tests automatisés |
| `tests/smoke/physical_inventory_browser.py` | Tests automatisés |
| `tests/smoke/quality_smoke.py` | Tests automatisés |
| `tests/smoke/reading_library_browser.py` | Tests automatisés |
| `tests/smoke/rebuild_safety_smoke.py` | Tests automatisés |
| `tests/smoke/resolve_unknown_db.py` | Tests automatisés |
| `tests/smoke/seed_advisor.sql` | Tests automatisés |
| `tests/smoke/seed_catalog.sql` | Tests automatisés |
| `tests/smoke/seed_fr_editions.sql` | Tests automatisés |
| `tests/test_advisor_ai.py` | Tests automatisés |
| `tests/test_advisor_balance.py` | Tests automatisés |
| `tests/test_advisor_editions.py` | Tests automatisés |
| `tests/test_advisor_feedback_learning.py` | Tests automatisés |
| `tests/test_advisor_library_surprise.py` | Tests automatisés |
| `tests/test_advisor_ownership_fallback.py` | Tests automatisés |
| `tests/test_advisor_quality.py` | Tests automatisés |
| `tests/test_bibliographic_staging.py` | Tests automatisés |
| `tests/test_bnf_batch.py` | Tests automatisés |
| `tests/test_bnf_bulk_import.py` | Tests automatisés |
| `tests/test_catalogue_api_metadata.py` | Tests automatisés |
| `tests/test_catalogue_french_matching.py` | Tests automatisés |
| `tests/test_catalogue_lifecycle.py` | Tests automatisés |
| `tests/test_catalogue_scrinis_fr_direct.py` | Tests automatisés |
| `tests/test_catalogue_sources_benchmark.py` | Tests automatisés |
| `tests/test_catalogue_sources_benchmark_v2.py` | Tests automatisés |
| `tests/test_check_network.py` | Tests automatisés |
| `tests/test_collection_bulk.py` | Tests automatisés |
| `tests/test_collection_fr.py` | Tests automatisés |
| `tests/test_collection_routes.py` | Tests automatisés |
| `tests/test_collection_scan.py` | Tests automatisés |
| `tests/test_conversational_advisor.py` | Tests automatisés |
| `tests/test_cover_api.py` | Tests automatisés |
| `tests/test_discovery.py` | Tests automatisés |
| `tests/test_edition_discovery.py` | Tests automatisés |
| `tests/test_edition_enrichment.py` | Tests automatisés |
| `tests/test_extended_tenrai_catalogue.py` | Tests automatisés |
| `tests/test_feedback.py` | Tests automatisés |
| `tests/test_full_mal_catalogue_sync.py` | Tests automatisés |
| `tests/test_inventory_import.py` | Tests automatisés |
| `tests/test_inventory_resolution.py` | Tests automatisés |
| `tests/test_jikan_metadata_merge.py` | Tests automatisés |
| `tests/test_legacy_library_csv_contracts.py` | Tests automatisés |
| `tests/test_legacy_recommendation_contracts.py` | Tests automatisés |
| `tests/test_library_enrichment.py` | Tests automatisés |
| `tests/test_library_import_match_safety.py` | Tests automatisés |
| `tests/test_library_seed_selection.py` | Tests automatisés |
| `tests/test_library_templates.py` | Tests automatisés |
| `tests/test_library_xlsx.py` | Tests automatisés |
| `tests/test_localization.py` | Tests automatisés |
| `tests/test_mangadex_discovery.py` | Tests automatisés |
| `tests/test_mood_discovery.py` | Tests automatisés |
| `tests/test_multilingual_aliases.py` | Tests automatisés |
| `tests/test_physical_inventory_summary.py` | Tests automatisés |
| `tests/test_pipeline_failure_modes.py` | Tests automatisés |
| `tests/test_recommendation_explanations.py` | Tests automatisés |
| `tests/test_recommendation_ingestion_health.py` | Tests automatisés |
| `tests/test_recommendation_quality.py` | Tests automatisés |
| `tests/test_repository_hygiene.py` | Tests automatisés |
| `tests/test_repository_safety.py` | Tests automatisés |
| `tests/test_single_web_deployment.py` | Tests automatisés |
| `tests/test_stabilisation_safety.py` | Tests automatisés |
| `tests/test_tenrai_migration.py` | Tests automatisés |
| `tests/test_web_proxy_lifecycle.py` | Tests automatisés |
| `tests/test_wikidata_enrichment.py` | Tests automatisés |
| `tests/test_windows_powershell51_encoding.py` | Tests automatisés |
| `tests/web/advisor-editions.test.mjs` | Tests automatisés |
| `tests/web/advisor-view.test.mjs` | Tests automatisés |
| `tests/web/appearance.test.mjs` | Tests automatisés |
| `tests/web/bibliography.test.mjs` | Tests automatisés |
| `tests/web/bnf-candidates.test.mjs` | Tests automatisés |
| `tests/web/bulk-import.test.mjs` | Tests automatisés |
| `tests/web/collection.test.mjs` | Tests automatisés |
| `tests/web/enrichment.test.mjs` | Tests automatisés |
| `tests/web/explain.test.mjs` | Tests automatisés |
| `tests/web/home.test.mjs` | Tests automatisés |
| `tests/web/inventory-resolution.test.mjs` | Tests automatisés |
| `tests/web/isbn-scanner.test.mjs` | Tests automatisés |
| `tests/web/library-display.test.mjs` | Tests automatisés |
| `tests/web/manga-detail-route.test.mjs` | Tests automatisés |
| `tests/web/mood-view.test.mjs` | Tests automatisés |
| `tests/web/physical-inventory.test.mjs` | Tests automatisés |
| `tests/web/reading-library-import.test.mjs` | Tests automatisés |
| `tests/web/reading-profile.test.mjs` | Tests automatisés |
| `tests/web/unknown-isbn.test.mjs` | Tests automatisés |
| `tests/web/wikidata-view.test.mjs` | Tests automatisés |
| `tests/windows/test-github-sync.ps1` | Tests automatisés |
| `tests/windows/test-menu-import-backup.ps1` | Tests automatisés |
| `tests/windows/test-menu-return.ps1` | Tests automatisés |
| `tests/windows/test-safe-git-update.ps1` | Tests automatisés |
| `tools/audit_repository.py` | Outil d'audit |

## Décisions finales de nettoyage

- Interface Web unique : code Streamlit, Dockerfile et service Docker retirés de la branche.
- Meilisearch sans client actif confirmé : service et volume conservés ; ne pas annoncer l'indexation Meilisearch comme active.
- Lecture CSV/XLSX et livres physiques ISBN : imports distincts, aperçu préalable et préservation des données existantes.
- Quatre workflows GitHub réussis au commit `031ed76da49b5f07286c634be045e04ea390210d`; revalider le HEAD après les derniers changements.
- Fusion PR #89 en `main` soumise à validation explicite.
