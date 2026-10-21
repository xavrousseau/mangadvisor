# Inventaire transversal du dépôt Mangadvisor — 21 octobre 2026

> **Périmètre exact :** branche `cleanup/pipelines-2026-10-21`, commit `14164cec7c68bc6b11bf179228fdf6378e8edf50`. Liste extraite de l'arbre Git récursif GitHub (`truncated=false`). **284 fichiers suivis**. Cet inventaire fournit une décision de traitement *par catégorie* pour chaque chemin : il ne constitue pas une revue manuelle du contenu de chacune des 284 sources.

## Dénombrement

| Ensemble | Nombre de fichiers |
|---|---:|
| `.github` | 4 |
| `(racine)` | 7 |
| `apps` | 53 |
| `cmd` | 8 |
| `data` | 2 |
| `docs` | 72 |
| `infra` | 9 |
| `pipelines` | 22 |
| `sql` | 10 |
| `tests` | 96 |
| `tools` | 1 |
| **TOTAL** | **284** |

## Résultats de contrôle transversal

- **Références anciennes dans les points d'entrée actifs :** les lanceurs, quatre workflows et smoke principal vérifiés ne référencent plus les six scripts retirés ; un test automatique a été ajouté dans `tests/test_repository_hygiene.py` pour les chemins exécutables pertinents. **Les mentions historiques dans les rapports ne sont pas des dépendances exécutables**.
- **Cohérence Docker :** un nouveau `.dockerignore` exclut fichiers privés, sauvegardes, caches et données téléchargées du contexte de construction ; contrôle dans la suite de tests. Les images API/Web/engine conservent leurs sources.
- **Données personnelles :** aucune suppression de volumes et aucune opération de reconstruction contre une base personnelle. Reconstruction contrôlée exclusivement en CI sur base jetable.
- **Contrats SQL :** restauration et liens de bibliothèque à protéger ; mise à jour canonique additive et refus des titres de source vides.
- **Documentation :** plusieurs guides décrivent encore des fonctionnalités historiques. Les documentations V1 doivent rester explicitement des archives de conception ; le README et la structure courante font référence.
- **Ancienne interface :** `apps/ui/` est maintenu tant que l'équivalence Web et les imports Excel ne sont pas démontrés ; elle ne fait pas partie de la configuration stable.
- **Couverture non démontrée :** équivalence exhaustive des cinq anciens scripts de tests supprimés ; distinction fournisseur entre absence de donnée et suppression explicite ; revue fonctionnelle individuelle de chaque fichier. Ces réserves empêchent une certification de nettoyage « 100 % ».

## Registre complet des fichiers

La colonne « traitement » représente une **classification de nettoyage**, pas un diagnostic fonctionnel individuel. Pas de suppression décidée automatiquement par nom ou extension.

| Chemin suivi | Traitement provisoire |
|---|---|
| `.dockerignore` | Racine — conserver / contrôler |
| `.env.example` | Racine — conserver / contrôler |
| `.gitattributes` | Racine — conserver / contrôler |
| `.github/workflows/control-center-windows.yml` | CI — conserver |
| `.github/workflows/integration-v1.yml` | CI — conserver |
| `.github/workflows/single-web-stack.yml` | CI — conserver |
| `.github/workflows/verify-python.yml` | CI — conserver |
| `.gitignore` | Racine — conserver / contrôler |
| `README.md` | Racine — conserver / contrôler |
| `apps/api/app/advisor.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/advisor_ai.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/advisor_editions.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/advisor_feedback.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/advisor_quality.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/bnf_batch.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/collection.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/collection_bulk.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/collection_scan.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/edition_discovery.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/edition_enrichment.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/inventory_import.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/inventory_resolution.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/library_enrichment.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/library_seed_selection.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/localization.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/main.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/mangadex_discovery.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/mood_discovery.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/multilingual_aliases.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/narrative_evidence.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/recommendation_explanations.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/recommendation_quality.py` | API active — conserver, refactorisation ciblée |
| `apps/api/app/wikidata_enrichment.py` | API active — conserver, refactorisation ciblée |
| `apps/api/requirements.txt` | API active — conserver, refactorisation ciblée |
| `apps/ui/app/app.py` | Streamlit ancien — migration à établir |
| `apps/ui/app/discovery.py` | Streamlit ancien — migration à établir |
| `apps/ui/app/recommendations.py` | Streamlit ancien — migration à établir |
| `apps/ui/app/theme.css` | Streamlit ancien — migration à établir |
| `apps/ui/requirements.txt` | Streamlit ancien — migration à établir |
| `apps/web/assets/advisor-editions.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/advisor-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/app.css` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/app.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/appearance.css` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/appearance.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/bibliography-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/bnf-candidates-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/bulk-import-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/collection-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/enrichment-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/explain.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/home.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/i18n.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/inventory-resolution-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/isbn-scanner.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/library-display.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/mood-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/physical-inventory-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/unknown-isbn-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/assets/wikidata-view.js` | Web actif — conserver, refactorisation ciblée |
| `apps/web/index.html` | Web actif — conserver, refactorisation ciblée |
| `apps/web/nginx.conf` | Web actif — conserver, refactorisation ciblée |
| `cmd/ai-setup.ps1` | Lanceur Windows — conserver |
| `cmd/benchmark-mangatheque.ps1` | Lanceur Windows — conserver |
| `cmd/control-center.ps1` | Lanceur Windows — conserver |
| `cmd/github-sync.ps1` | Lanceur Windows — conserver |
| `cmd/import-private-inventory.ps1` | Lanceur Windows — conserver |
| `cmd/library-backup.ps1` | Lanceur Windows — conserver |
| `cmd/local-api.ps1` | Lanceur Windows — conserver |
| `cmd/mobile-setup.ps1` | Lanceur Windows — conserver |
| `data/modele_bibliotheque_mangadvisor.csv` | Modèle public — vérifier absence de données réelles |
| `data/modele_bibliotheque_mangadvisor.xlsx` | Modèle public — vérifier absence de données réelles |
| `docs/02_data/data_model_v1.md` | Documentation — revue éditoriale |
| `docs/02_data/data_pipeline_v1.md` | Documentation — revue éditoriale |
| `docs/03_technical/apps_api_web_review_2026_10_21.md` | Documentation — revue éditoriale |
| `docs/03_technical/audit_transversal_4_4.md` | Documentation — revue éditoriale |
| `docs/03_technical/cleanup_4_1.md` | Documentation — revue éditoriale |
| `docs/03_technical/infra_cleanup_review_2026_10_21.md` | Documentation — revue éditoriale |
| `docs/03_technical/infrastructure_single_web_4_5.md` | Documentation — revue éditoriale |
| `docs/03_technical/mangadvisor_architecture_v1.md` | Documentation — revue éditoriale |
| `docs/03_technical/project_structure.md` | Documentation — revue éditoriale |
| `docs/03_technical/root_docs_tools_review_2026_10_21.md` | Documentation — revue éditoriale |
| `docs/03_technical/sql_tests_review_2026_10_21.md` | Documentation — revue éditoriale |
| `docs/04_product/advisor_discovery_balance_3_1.md` | Documentation — revue éditoriale |
| `docs/04_product/advisor_feedback_learning_3_5.md` | Documentation — revue éditoriale |
| `docs/04_product/advisor_french_editions_2_3.md` | Documentation — revue éditoriale |
| `docs/04_product/advisor_library_surprise_3_3.md` | Documentation — revue éditoriale |
| `docs/04_product/advisor_narrative_safety_2_2.md` | Documentation — revue éditoriale |
| `docs/04_product/advisor_quality_safety_3_4.md` | Documentation — revue éditoriale |
| `docs/04_product/appearance_customization.md` | Documentation — revue éditoriale |
| `docs/04_product/benchmark_sources_4_9.md` | Documentation — revue éditoriale |
| `docs/04_product/benchmark_sources_v2.md` | Documentation — revue éditoriale |
| `docs/04_product/bibliographic_staging_v1.md` | Documentation — revue éditoriale |
| `docs/04_product/bnf_bulk_import_4_8.md` | Documentation — revue éditoriale |
| `docs/04_product/bulk_collection_import_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/catalogue_mal_complet.md` | Documentation — revue éditoriale |
| `docs/04_product/catalogue_vivant_cycle.md` | Documentation — revue éditoriale |
| `docs/04_product/control_center_4_0.md` | Documentation — revue éditoriale |
| `docs/04_product/conversational_advisor_2_1.md` | Documentation — revue éditoriale |
| `docs/04_product/design_system_v1.md` | Documentation — revue éditoriale |
| `docs/04_product/discovery_v1.md` | Documentation — revue éditoriale |
| `docs/04_product/edition_progress_known_isbns_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/enrichissement_bnf_progressif_4_0.md` | Documentation — revue éditoriale |
| `docs/04_product/enrichissement_fr_direct_scrinis.md` | Documentation — revue éditoriale |
| `docs/04_product/explainable_recommendations_1_1.md` | Documentation — revue éditoriale |
| `docs/04_product/french_bibliography_discovery_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/french_edition_enrichment_2_5.md` | Documentation — revue éditoriale |
| `docs/04_product/french_edition_enrichment_workshop_2_4.md` | Documentation — revue éditoriale |
| `docs/04_product/french_editions_collection_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/french_records_reliability_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/guided_mood_discovery_2_0.md` | Documentation — revue éditoriale |
| `docs/04_product/inventaire_en_attente_4_3.md` | Documentation — revue éditoriale |
| `docs/04_product/isbn_camera_scanner_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/library_backup_recovery_3_2.md` | Documentation — revue éditoriale |
| `docs/04_product/library_enrichment_one_click_4_2.md` | Documentation — revue éditoriale |
| `docs/04_product/library_recommendations_4_7.md` | Documentation — revue éditoriale |
| `docs/04_product/local_ai_advisor_3_0.md` | Documentation — revue éditoriale |
| `docs/04_product/manga_covers_v1.md` | Documentation — revue éditoriale |
| `docs/04_product/manual_pending_inventory_reconciliation_4_3.md` | Documentation — revue éditoriale |
| `docs/04_product/mobile_https_scan_session_2_0.md` | Documentation — revue éditoriale |
| `docs/04_product/multilingual_aliases_4_4.md` | Documentation — revue éditoriale |
| `docs/04_product/physical_inventory_dashboard_3_9.md` | Documentation — revue éditoriale |
| `docs/04_product/private_library_benchmark_3_6.md` | Documentation — revue éditoriale |
| `docs/04_product/recommendation_feedback_1_1.md` | Documentation — revue éditoriale |
| `docs/04_product/recommendation_quality_1_1.md` | Documentation — revue éditoriale |
| `docs/04_product/recommendations_v1.md` | Documentation — revue éditoriale |
| `docs/04_product/resolve_unknown_isbns_1_2.md` | Documentation — revue éditoriale |
| `docs/04_product/roadmap_mangadvisor_1_1_to_2_0.md` | Documentation — revue éditoriale |
| `docs/04_product/safe_inventory_import_3_8.md` | Documentation — revue éditoriale |
| `docs/04_product/verified_source_links_1_1.md` | Documentation — revue éditoriale |
| `docs/04_product/web_experience_bilingual.md` | Documentation — revue éditoriale |
| `docs/04_product/wikidata_metadata_enrichment_4_1.md` | Documentation — revue éditoriale |
| `docs/STABILISATION_V0_8.md` | Documentation — revue éditoriale |
| `docs/recommandation_tests_v0_6.md` | Documentation — revue éditoriale |
| `docs/reports/Mangadvisor V0.7 Data Foundation.docx` | Documentation — revue éditoriale |
| `docs/reports/jikan_recommendation_edges_diagnostic.md` | Documentation — revue éditoriale |
| `docs/reports/library_goal_tests_v0_8_3.md` | Documentation — revue éditoriale |
| `docs/reports/library_import_robustness_tests_v0_8_11.md` | Documentation — revue éditoriale |
| `docs/reports/library_import_tests_v0_8_10.md` | Documentation — revue éditoriale |
| `docs/reports/library_recommendation_tests_v0_8_2_profile_summary.md` | Documentation — revue éditoriale |
| `docs/reports/library_status_tests_v0_8_5.md` | Documentation — revue éditoriale |
| `docs/reports/recommendation_profile_tests_latest.md` | Documentation — revue éditoriale |
| `docs/reports/repository_audit_2026_10_19.md` | Documentation — revue éditoriale |
| `docs/reports/repository_audit_2026_10_20.md` | Documentation — revue éditoriale |
| `infra/compose/docker-compose.dev.yml` | Infrastructure — conserver, revue dépendances |
| `infra/compose/docker-compose.local.yml` | Infrastructure — conserver, revue dépendances |
| `infra/compose/docker-compose.mobile.yml` | Infrastructure — conserver, revue dépendances |
| `infra/compose/docker-compose.yml` | Infrastructure — conserver, revue dépendances |
| `infra/docker/api/Dockerfile` | Infrastructure — conserver, revue dépendances |
| `infra/docker/engine/Dockerfile` | Infrastructure — conserver, revue dépendances |
| `infra/docker/ui/Dockerfile` | Infrastructure — conserver, revue dépendances |
| `infra/docker/web/Dockerfile` | Infrastructure — conserver, revue dépendances |
| `infra/mobile/Caddyfile` | Infrastructure — conserver, revue dépendances |
| `mangadvisor.cmd` | Lanceur Windows — conserver |
| `pipelines/__init__.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/requirements.txt` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/analyze_jikan_recommendation_edges.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/benchmark_manga_sources.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/benchmark_manga_sources_v2.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/bnf_bulk_import.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/catalogue_french_matching.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/catalogue_lifecycle.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/catalogue_mangaupdates.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/check_network.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/enrich_catalogue_scrinis_fr.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/extract_jikan.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/extract_jikan_recommendations.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/load_jikan_to_postgres.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/prepare_bibliographic_staging.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/run_recommendation_profile_tests.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/scripts/sync_full_mal_catalogue.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/src/__init__.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/src/extract/__init__.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/src/load/__init__.py` | Pipeline — conserver après nettoyage |
| `pipelines/engine/src/load/postgres_loader.py` | Pipeline — conserver après nettoyage |
| `pyproject.toml` | Racine — conserver / contrôler |
| `sql/queries/check_jikan_data_quality.sql` | Schéma/diagnostic — conserver |
| `sql/queries/check_jikan_source_data.sql` | Schéma/diagnostic — conserver |
| `sql/queries/inspect_jikan_attributes.sql` | Schéma/diagnostic — conserver |
| `sql/schema/001_jikan_source_tables.sql` | Schéma/diagnostic — conserver |
| `sql/schema/002_canonical_manga_tables.sql` | Schéma/diagnostic — conserver |
| `sql/schema/003_build_canonical_from_jikan.sql` | Schéma/diagnostic — conserver |
| `sql/schema/004_add_theme_demographic_tables.sql` | Schéma/diagnostic — conserver |
| `sql/schema/005_build_theme_demographic_from_jikan.sql` | Schéma/diagnostic — conserver |
| `sql/schema/006_add_jikan_recommendation_tables.sql` | Schéma/diagnostic — conserver |
| `sql/schema/007_add_user_library_tables.sql` | Schéma/diagnostic — conserver |
| `tests/integration/guided-ingestion-smoke.sh` | Tests — conserver, contrôle CI |
| `tests/smoke/advisor_browser.py` | Tests — conserver, contrôle CI |
| `tests/smoke/advisor_ownership_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/advisor_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/browser_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/collection_bulk_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/collection_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/explanations_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/feedback_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/inventory_import_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/isbn_camera_browser.py` | Tests — conserver, contrôle CI |
| `tests/smoke/mood_discovery_browser.py` | Tests — conserver, contrôle CI |
| `tests/smoke/mood_discovery_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/ownership_exclusion_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/physical_inventory_browser.py` | Tests — conserver, contrôle CI |
| `tests/smoke/quality_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/rebuild_safety_smoke.py` | Tests — conserver, contrôle CI |
| `tests/smoke/resolve_unknown_db.py` | Tests — conserver, contrôle CI |
| `tests/smoke/seed_advisor.sql` | Tests — conserver, contrôle CI |
| `tests/smoke/seed_catalog.sql` | Tests — conserver, contrôle CI |
| `tests/smoke/seed_fr_editions.sql` | Tests — conserver, contrôle CI |
| `tests/test_advisor_ai.py` | Tests — conserver, contrôle CI |
| `tests/test_advisor_balance.py` | Tests — conserver, contrôle CI |
| `tests/test_advisor_editions.py` | Tests — conserver, contrôle CI |
| `tests/test_advisor_feedback_learning.py` | Tests — conserver, contrôle CI |
| `tests/test_advisor_library_surprise.py` | Tests — conserver, contrôle CI |
| `tests/test_advisor_ownership_fallback.py` | Tests — conserver, contrôle CI |
| `tests/test_advisor_quality.py` | Tests — conserver, contrôle CI |
| `tests/test_bibliographic_staging.py` | Tests — conserver, contrôle CI |
| `tests/test_bnf_batch.py` | Tests — conserver, contrôle CI |
| `tests/test_bnf_bulk_import.py` | Tests — conserver, contrôle CI |
| `tests/test_catalogue_api_metadata.py` | Tests — conserver, contrôle CI |
| `tests/test_catalogue_french_matching.py` | Tests — conserver, contrôle CI |
| `tests/test_catalogue_lifecycle.py` | Tests — conserver, contrôle CI |
| `tests/test_catalogue_scrinis_fr_direct.py` | Tests — conserver, contrôle CI |
| `tests/test_catalogue_sources_benchmark.py` | Tests — conserver, contrôle CI |
| `tests/test_catalogue_sources_benchmark_v2.py` | Tests — conserver, contrôle CI |
| `tests/test_check_network.py` | Tests — conserver, contrôle CI |
| `tests/test_collection_bulk.py` | Tests — conserver, contrôle CI |
| `tests/test_collection_fr.py` | Tests — conserver, contrôle CI |
| `tests/test_collection_routes.py` | Tests — conserver, contrôle CI |
| `tests/test_collection_scan.py` | Tests — conserver, contrôle CI |
| `tests/test_conversational_advisor.py` | Tests — conserver, contrôle CI |
| `tests/test_cover_api.py` | Tests — conserver, contrôle CI |
| `tests/test_discovery.py` | Tests — conserver, contrôle CI |
| `tests/test_edition_discovery.py` | Tests — conserver, contrôle CI |
| `tests/test_edition_enrichment.py` | Tests — conserver, contrôle CI |
| `tests/test_extended_tenrai_catalogue.py` | Tests — conserver, contrôle CI |
| `tests/test_feedback.py` | Tests — conserver, contrôle CI |
| `tests/test_full_mal_catalogue_sync.py` | Tests — conserver, contrôle CI |
| `tests/test_inventory_import.py` | Tests — conserver, contrôle CI |
| `tests/test_inventory_resolution.py` | Tests — conserver, contrôle CI |
| `tests/test_jikan_metadata_merge.py` | Tests — conserver, contrôle CI |
| `tests/test_library_enrichment.py` | Tests — conserver, contrôle CI |
| `tests/test_library_import_match_safety.py` | Tests — conserver, contrôle CI |
| `tests/test_library_seed_selection.py` | Tests — conserver, contrôle CI |
| `tests/test_localization.py` | Tests — conserver, contrôle CI |
| `tests/test_mangadex_discovery.py` | Tests — conserver, contrôle CI |
| `tests/test_mood_discovery.py` | Tests — conserver, contrôle CI |
| `tests/test_multilingual_aliases.py` | Tests — conserver, contrôle CI |
| `tests/test_physical_inventory_summary.py` | Tests — conserver, contrôle CI |
| `tests/test_pipeline_failure_modes.py` | Tests — conserver, contrôle CI |
| `tests/test_recommendation_explanations.py` | Tests — conserver, contrôle CI |
| `tests/test_recommendation_ingestion_health.py` | Tests — conserver, contrôle CI |
| `tests/test_recommendation_quality.py` | Tests — conserver, contrôle CI |
| `tests/test_recommendation_view.py` | Tests — conserver, contrôle CI |
| `tests/test_repository_hygiene.py` | Tests — conserver, contrôle CI |
| `tests/test_repository_safety.py` | Tests — conserver, contrôle CI |
| `tests/test_single_web_deployment.py` | Tests — conserver, contrôle CI |
| `tests/test_stabilisation_safety.py` | Tests — conserver, contrôle CI |
| `tests/test_tenrai_migration.py` | Tests — conserver, contrôle CI |
| `tests/test_web_proxy_lifecycle.py` | Tests — conserver, contrôle CI |
| `tests/test_wikidata_enrichment.py` | Tests — conserver, contrôle CI |
| `tests/test_windows_powershell51_encoding.py` | Tests — conserver, contrôle CI |
| `tests/web/advisor-editions.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/advisor-view.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/appearance.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/bibliography.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/bnf-candidates.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/bulk-import.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/collection.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/enrichment.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/explain.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/home.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/inventory-resolution.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/isbn-scanner.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/library-display.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/manga-detail-route.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/mood-view.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/physical-inventory.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/unknown-isbn.test.mjs` | Tests — conserver, contrôle CI |
| `tests/web/wikidata-view.test.mjs` | Tests — conserver, contrôle CI |
| `tests/windows/test-github-sync.ps1` | Tests — conserver, contrôle CI |
| `tests/windows/test-menu-import-backup.ps1` | Tests — conserver, contrôle CI |
| `tests/windows/test-menu-return.ps1` | Tests — conserver, contrôle CI |
| `tests/windows/test-safe-git-update.ps1` | Tests — conserver, contrôle CI |
| `tools/audit_repository.py` | Outil d'audit — conserver |

## Décision pour la PR #89

Conserver la PR en brouillon et **ne pas fusionner** avant réussite des quatre workflows sur son dernier commit, contrôle ciblé des réserves ci-dessus et validation explicite du périmètre final. Les historiques Git conservent toutes les anciennes versions.
