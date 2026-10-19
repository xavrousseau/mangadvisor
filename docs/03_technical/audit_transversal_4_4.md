# Mangadvisor 4.4 — audit transversal, suivi des 229 fichiers

> Base : branche `audit/stabilisation-transverse-4-4`, commit `6efe6bd8631c`, arbre GitHub non tronqué.
> Audit technique effectué le 19 octobre 2026. Aucun accès direct au Docker ni aux fichiers privés du PC.

## Méthode et portée exacte

- Inventaire de **229 fichiers Git suivis** (répartis en .env.example 1, .github 3, .gitignore 1, apps 43, cmd 25, data 2, docs 52, infra 8, mangadvisor.cmd 1, pipelines 19, pyproject.toml 1, README.md 1, sql 10, tests 61, tools 1).
- Les **227 fichiers texte** ont fait l'objet d'une inspection automatisée initiale du code GitHub : chemins Jikan abandonnés, commandes SQL destructrices, références 8502, marqueurs TODO/FIXME et usages dangereux courants. Les **2 fichiers binaires** (modèle Excel et document Word) ont été inventoriés, **pas interprétés comme du code exécutable**.
- Revue logique approfondie du flux critique Windows → Compose → FastAPI → PostgreSQL → catalogue → bibliothèque → Web et du cycle sauvegarde/restauration. Lecture du code source réel, pas seulement du README.
- La CI `tools/audit_repository.py --strict` ajoute : scan de **chaque fichier suivi**, décodage UTF-8, syntaxe Python, références import JS, scripts PowerShell Windows, chemins `COPY` Dockerfiles, noms des services, contrats d'API/Compose, refus des anciens scripts destructeurs. Les tests JS sont désormais découverts automatiquement.
- Les tests d'intégration GitHub utilisent des données synthétiques jetables. Ils **ne remplacent pas** un test de l'application et de la collection réelle sur le PC Windows.

Une revue automatique d'un fichier ne signifie **pas** certification exhaustive de chacune de ses branches fonctionnelles. Cette distinction reste essentielle.

## Corrections de stabilisation apportées

| Priorité | Code concerné | Problème confirmé | Correctif |
|---|---|---|---|
| P0 | `pipelines/engine/scripts/run_jikan_pipeline.py` | Ancien outil contenant `TRUNCATE jikan_manga_source` derrière `--reset-db` | Logique destructrice retirée, argument désormais explicitement refusé |
| P1 | `cmd/library-backup.ps1` | Restauration d'essai affichait seulement le suivi/ISBN, pas les déclarations physiques ni les lignes en attente | Contrôle et compteurs supplémentaires sur archives anciennes ou nouvelles, sans modifier les tables |
| P1 | `cmd/library-backup.ps1` | Après restauration, l'ancien site Streamlit pouvait être redémarré sur 8502 | Seuls API et Web 8501 sont relancés ; l'arrêt cible Streamlit sous profil `legacy` |
| P1 | `infra/compose/docker-compose.yml` | Web démarré dès la création de l'API, avant sa disponibilité réelle ; période propice aux 502 | Healthcheck réel FastAPI/PostgreSQL et dépendance `service_healthy` |
| P1 | `apps/web/assets/app.js`, `library-display.js` | Statut `Possédé · —` : le tiret signalait en réalité une note utilisateur vide | Note uniquement si renseignée ; quantités physiques distinctes par manga, issues des déclarations enregistrées |
| P1 | `apps/web/assets/app.js`, `library-display.js` | Titres japonais ou romanisés parfois prioritaires alors qu'un titre international est disponible | Affichage cohérent du titre anglais disponible, puis titre original en repli ; conservation des alias en fiche |
| P2 | `mangadvisor.cmd`, `apps/api/app/main.py`, `apps/web/assets/app.js` | Versions contradictoires 3.8 / 0.8.7 / 1.0 | Libellés non ambigus et version API 4.4.0 |
| P2 | `.github/workflows/verify-python.yml` | Modules/tests JavaScript spécifiés à la main, risque d'oubli après ajout de fichiers | Découverte et vérification de l'ensemble des modules JS et tests Web |
| P2 | `cmd/control-center.ps1`, README | Messages parlant encore de l'API publique Jikan arrêtée | Mentions adaptées à Tenrai (noms SQL historiques conservés) |

## Limites et améliorations encore ouvertes (ne pas prétendre qu'elles sont finies)

1. **Titre français vérifié** : une API internationale ne suffit pas à établir automatiquement le titre français officiel. Le repli anglais est une amélioration d'affichage, pas une traduction. Il faudra introduire une table d'alias français sourcés/validés, les rendre recherchables, et préserver l'identifiant MAL canonique.
2. **Couvertures françaises** : le site affiche normalement la couverture MyAnimeList, souvent japonaise. Associer une couverture française à la bonne édition nécessite un ISBN et une source fiable ; pas de remplacement automatique par recherche d'images non vérifiées.
3. **Réconciliation des entrées en attente** : les titres sauvegardés dans `user_manga_inventory_pending` ne sont pas encore liés. Une interface devra afficher les candidats (titre français, origine, type, auteur, éditions) et demander une validation explicite. Pas de rapprochement forcé.
4. **Deux modèles de possession** : `user_manga_library.owned_volumes` et `user_manga_inventory_declaration` sont deux déclarations de granularité différente. Le présent correctif les affiche séparément, sans modifier leurs valeurs ni les additionner avec des livres ISBN.
5. **Dépendances non figées** : les requirements Python (`fastapi`, `psycopg`, `streamlit`, `requests`…) n'ont pas de versions verrouillées. Gel reproductible et actualisation de sécurité à préparer dans une PR indépendante.
6. **Configuration Docker locale** : la superposition habituelle `docker-compose.dev.yml` monte le code local et lance Uvicorn `--reload`. Cela facilite le développement mais ne constitue pas une configuration de production isolée ; séparation dev/local stable à traiter dans un chantier planifié.
7. **Modules volumineux** : `apps/api/app/main.py` (environ 116 ko) et `apps/web/assets/app.js` (environ 79 ko) présentent un risque de maintenance. Découpage fonctionnel graduel, avec contrats API et tests de non-régression.
8. **Qualité des données et recommandations** : tags MAL/Tenrai incomplets, anciens noms `jikan_*` conservés pour compatibilité, indexation Meilisearch et embeddings non systématiquement alimentés ; ne pas présenter un moteur comme source exhaustive de disponibilité française ou de maturité.
9. **Documentation historique** : les plans V1 et rapports antérieurs restent consultables comme archives de conception, sans être des preuves d'implémentation active. La documentation de référence reste `docs/03_technical/project_structure.md` et le centre de pilotage.

## Revue fichier par fichier — classification de maintenance

Le tableau ci-dessous est **un inventaire technique**, non une affirmation que chaque fonction interne a été exécutée. `Revue statique et CI / conserver` veut dire que le fichier n'a pas été modifié sur la seule base de son nom. Aucun fichier personnel `.env`, `private-data/` ou `backups/` n'est suivi ici.

| Fichier suivi | Zone | Décision à ce stade |
|---|---|---|
| `.env.example` | Configuration | Revue statique et CI / conserver |
| `.github/workflows/control-center-windows.yml` | Test/CI | Revue statique et CI / conserver |
| `.github/workflows/integration-v1.yml` | Test/CI | Correction/revue approfondie |
| `.github/workflows/verify-python.yml` | Test/CI | Correction/revue approfondie |
| `.gitignore` | Configuration | Revue statique et CI / conserver |
| `apps/api/app/advisor_ai.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/advisor_editions.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/advisor_feedback.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/advisor_quality.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/advisor.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/collection_bulk.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/collection_scan.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/collection.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/edition_discovery.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/edition_enrichment.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/inventory_import.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/localization.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/main.py` | API/Donnees | Correction/revue approfondie |
| `apps/api/app/mood_discovery.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/narrative_evidence.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/recommendation_explanations.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/app/recommendation_quality.py` | API/Donnees | Revue statique et CI / conserver |
| `apps/api/requirements.txt` | API/Donnees | Revue statique et CI / conserver |
| `apps/ui/app/app.py` | UI ancienne facultative | Revue statique et CI / conserver |
| `apps/ui/app/discovery.py` | UI ancienne facultative | Revue statique et CI / conserver |
| `apps/ui/app/recommendations.py` | UI ancienne facultative | Revue statique et CI / conserver |
| `apps/ui/app/theme.css` | UI ancienne facultative | Revue statique et CI / conserver |
| `apps/ui/requirements.txt` | UI ancienne facultative | Revue statique et CI / conserver |
| `apps/web/assets/advisor-editions.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/advisor-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/app.css` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/app.js` | Web 8501 | Correction/revue approfondie |
| `apps/web/assets/appearance.css` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/appearance.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/bibliography-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/bulk-import-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/collection-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/enrichment-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/explain.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/home.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/i18n.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/isbn-scanner.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/library-display.js` | Web 8501 | Correction/revue approfondie |
| `apps/web/assets/mood-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/physical-inventory-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/assets/unknown-isbn-view.js` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/index.html` | Web 8501 | Revue statique et CI / conserver |
| `apps/web/nginx.conf` | Web 8501 | Revue statique et CI / conserver |
| `cmd/ai-setup.ps1` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/benchmark-mangatheque.ps1` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/build.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/clean.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/common.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/control-center.ps1` | CLI Windows/sauvegarde | Correction/revue approfondie |
| `cmd/down.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/import-private-inventory.ps1` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/install-check.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/library-backup.ps1` | CLI Windows/sauvegarde | Correction/revue approfondie |
| `cmd/logs.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/mobile-setup.ps1` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/nuke.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/restart.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-library-goal-tests.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-library-import-robustness-tests.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-library-import-tests.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-library-recommendation-tests.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-library-status-tests.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-recommendation-tests.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/run-v0-8-validation.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/start.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/status.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/stop.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `cmd/up.cmd` | CLI Windows/sauvegarde | Revue statique et CI / conserver |
| `data/modele_bibliotheque_mangadvisor.csv` | Modele public | Revue statique et CI / conserver |
| `data/modele_bibliotheque_mangadvisor.xlsx` | Modele public | Revue statique et CI / conserver |
| `docs/02_data/data_model_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/02_data/data_pipeline_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/03_technical/cleanup_4_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/03_technical/mangadvisor_architecture_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/03_technical/project_structure.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/advisor_discovery_balance_3_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/advisor_feedback_learning_3_5.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/advisor_french_editions_2_3.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/advisor_library_surprise_3_3.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/advisor_narrative_safety_2_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/advisor_quality_safety_3_4.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/appearance_customization.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/bulk_collection_import_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/control_center_4_0.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/conversational_advisor_2_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/design_system_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/04_product/discovery_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/04_product/edition_progress_known_isbns_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/explainable_recommendations_1_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/french_bibliography_discovery_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/french_edition_enrichment_2_5.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/french_edition_enrichment_workshop_2_4.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/french_editions_collection_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/french_records_reliability_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/guided_mood_discovery_2_0.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/inventaire_en_attente_4_3.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/isbn_camera_scanner_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/library_backup_recovery_3_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/local_ai_advisor_3_0.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/manga_covers_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/04_product/mobile_https_scan_session_2_0.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/physical_inventory_dashboard_3_9.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/private_library_benchmark_3_6.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/recommendation_feedback_1_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/recommendation_quality_1_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/recommendations_v1.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/04_product/resolve_unknown_isbns_1_2.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/roadmap_mangadvisor_1_1_to_2_0.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/safe_inventory_import_3_8.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/verified_source_links_1_1.md` | Documentation | Revue statique et CI / conserver |
| `docs/04_product/web_experience_bilingual.md` | Documentation | Revue statique et CI / conserver |
| `docs/recommandation_tests_v0_6.md` | Documentation | Revue statique et CI / conserver |
| `docs/reports/jikan_recommendation_edges_diagnostic.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/library_goal_tests_v0_8_3.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/library_import_robustness_tests_v0_8_11.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/library_import_tests_v0_8_10.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/library_recommendation_tests_v0_8_2_profile_summary.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/library_status_tests_v0_8_5.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/Mangadvisor V0.7 Data Foundation.docx` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/recommendation_profile_tests_latest.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/reports/repository_audit_2026_10_19.md` | Rapport/document historique | Revue statique et CI / conserver |
| `docs/STABILISATION_V0_8.md` | Documentation | Revue statique et CI / conserver |
| `infra/compose/docker-compose.dev.yml` | Docker/reseau | Revue statique et CI / conserver |
| `infra/compose/docker-compose.mobile.yml` | Docker/reseau | Revue statique et CI / conserver |
| `infra/compose/docker-compose.yml` | Docker/reseau | Correction/revue approfondie |
| `infra/docker/api/Dockerfile` | Docker/reseau | Revue statique et CI / conserver |
| `infra/docker/engine/Dockerfile` | Docker/reseau | Revue statique et CI / conserver |
| `infra/docker/ui/Dockerfile` | Docker/reseau | Revue statique et CI / conserver |
| `infra/docker/web/Dockerfile` | Docker/reseau | Revue statique et CI / conserver |
| `infra/mobile/Caddyfile` | Docker/reseau | Revue statique et CI / conserver |
| `mangadvisor.cmd` | CLI Windows/sauvegarde | Correction/revue approfondie |
| `pipelines/__init__.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/requirements.txt` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/analyze_jikan_recommendation_edges.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/check_network.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/extract_jikan_recommendations.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/extract_jikan.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/load_jikan_to_postgres.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/run_jikan_pipeline.py` | Acquisition/ETL | Correction/revue approfondie |
| `pipelines/engine/scripts/run_library_goal_tests.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/run_library_import_robustness_tests.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/run_library_import_tests.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/run_library_recommendation_tests.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/run_library_status_tests.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/scripts/run_recommendation_profile_tests.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/src/__init__.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/src/extract/__init__.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/src/load/__init__.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pipelines/engine/src/load/postgres_loader.py` | Acquisition/ETL | Revue statique et CI / conserver |
| `pyproject.toml` | Configuration | Revue statique et CI / conserver |
| `README.md` | Configuration | Correction/revue approfondie |
| `sql/queries/check_jikan_data_quality.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/queries/check_jikan_source_data.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/queries/inspect_jikan_attributes.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/001_jikan_source_tables.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/002_canonical_manga_tables.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/003_build_canonical_from_jikan.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/004_add_theme_demographic_tables.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/005_build_theme_demographic_from_jikan.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/006_add_jikan_recommendation_tables.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `sql/schema/007_add_user_library_tables.sql` | Schema/catalogue | Revue statique et CI / conserver |
| `tests/smoke/advisor_browser.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/advisor_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/browser_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/collection_bulk_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/collection_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/explanations_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/feedback_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/inventory_import_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/isbn_camera_browser.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/mood_discovery_browser.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/mood_discovery_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/physical_inventory_browser.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/quality_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/rebuild_safety_smoke.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/resolve_unknown_db.py` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/seed_advisor.sql` | Test/CI | Revue statique et CI / conserver |
| `tests/smoke/seed_catalog.sql` | Test/CI | Correction/revue approfondie |
| `tests/smoke/seed_fr_editions.sql` | Test/CI | Revue statique et CI / conserver |
| `tests/test_advisor_ai.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_advisor_balance.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_advisor_editions.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_advisor_feedback_learning.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_advisor_library_surprise.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_advisor_quality.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_check_network.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_collection_bulk.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_collection_fr.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_collection_routes.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_collection_scan.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_conversational_advisor.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_cover_api.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_discovery.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_edition_discovery.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_edition_enrichment.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_feedback.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_inventory_import.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_localization.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_mood_discovery.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_physical_inventory_summary.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_recommendation_explanations.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_recommendation_quality.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_recommendation_view.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_repository_hygiene.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_repository_safety.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_tenrai_migration.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_web_proxy_lifecycle.py` | Test/CI | Revue statique et CI / conserver |
| `tests/test_windows_powershell51_encoding.py` | Test/CI | Revue statique et CI / conserver |
| `tests/web/advisor-editions.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/advisor-view.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/appearance.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/bibliography.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/bulk-import.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/collection.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/enrichment.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/explain.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/home.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/isbn-scanner.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/library-display.test.mjs` | Test/CI | Correction/revue approfondie |
| `tests/web/mood-view.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/physical-inventory.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tests/web/unknown-isbn.test.mjs` | Test/CI | Revue statique et CI / conserver |
| `tools/audit_repository.py` | Audit/qualite | Correction/revue approfondie |

## Validation avant fusion

- Test syntaxe Python, PowerShell 5.1, modules JS, tests unitaires et contrats de chemins.
- `docker compose config` et intégration Docker CI : démarrage API saine, proxy Nginx, site PC/mobile, catalogue, recommandations, inventaire, sauvegarde et restauration.
- Aucune commande Nuke, `down -v`, purge de `private-data` ou suppression de volumes dans le correctif.
- **Un résultat CI vert ne certifie pas l'accès à la base privée Windows**. Valider une sauvegarde et l'affichage réel après mise à jour sur le PC avant toute refonte ultérieure.
