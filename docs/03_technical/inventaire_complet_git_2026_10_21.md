# Inventaire de référence — **chaque fichier Git du 21 octobre 2026**

## Périmètre et méthode

- **Référence inventoriée** : `main` à `adb9a09a8c49e93a37ad04db4118a05b1dec701e` (303 fichiers suivis).
- **Arborescence initiale** : 39 dossiers, 2 319 096 octets suivis.
- **Après première passe de nettoyage** : 254 fichiers suivis, 1839658 octets ; 49 fichiers retirés du checkout ; l'historique Git permet de les retrouver.
- **Un fichier = une ligne** ci-dessous, avec son usage, la décision et la raison.
- **Niveau de preuve** : inventaire de l'arbre GitHub exhaustif, contrôle statique de dépendances et examen ciblé des points d'entrée Windows, Docker, PostgreSQL, pipelines et API. **Le jugement individuel des 303 fichiers n'est pas une relecture manuelle ligne par ligne de chaque module**. Les suites CI effectuent ensuite les vérifications automatiques de syntaxe et de comportement. Le PostgreSQL privé du PC n'est pas accessible depuis cet audit.
- Aucune suppression de `.env`, sauvegardes, JSON Jikan, PostgreSQL ou volumes personnels : **ils ne sont pas suivis par Git**.

## Résultats structurants

1. **Suppression des expérimentations** : prototype Streamlit, assistants de benchmarks A16–18, staging de démonstration, scripts de validation V0.x et rapports figés. La vraie Web, les flux MAL/Scrinis/MangaUpdates/BnF et les tests de régression restent.
2. **Aucun doublon binaire de code identifié par les empreintes Git**. Les seuls contenus strictement identiques dans l'arbre initial sont : `pipelines/__init__.py` / `pipelines/engine/src/__init__.py` / `pipelines/engine/src/extract/__init__.py` / `pipelines/engine/src/load/__init__.py`. Ce sont des `__init__.py` vides, intentionnels.
3. **Dupliqués fonctionnels / dette** : comparateurs V1/V2 servant maintenant de dépendance à l'enrichissement actif, grosse API centrale, gros contrôleur Web, ancien orchestrateur MAL. **Leur extraction demandera une PR de refactorisation avec tests, et non une suppression immédiate.**
4. **Point de vigilance métier** : aucune référence ISBN externe ne doit déclarer un tome comme possédé ; les homonymes et variantes physiques restent distincts.
5. **Fonctions Streamlit non entièrement migrées** : l'ancien écran possédait des fonctions d'import direct XLSX et un profil de lecture détaillé qui ne sont pas prouvés équivalents dans la Web. Elles restent retrouvables via Git ; une éventuelle restauration doit être faite **dans la Web actuelle**, pas en réintroduisant deux interfaces.

## Revue fichier par fichier du dépôt initial

### .env.example

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `.env.example` | Modèle de configuration Docker, sans secrets privés | **CONSERVER** | Fichier d'exploitation/configuration utile. |

### .gitattributes

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `.gitattributes` | Politique d'attributs Git et de normalisation des fichiers | **CONSERVER** | Fichier d'exploitation/configuration utile. |

### .github

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `.github/workflows/control-center-windows.yml` | Contrôle CI : control center windows | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `.github/workflows/integration-v1.yml` | Contrôle CI : integration v1 | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `.github/workflows/single-web-stack.yml` | Contrôle CI : single web stack | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `.github/workflows/verify-python.yml` | Contrôle CI : verify python | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |

### .gitignore

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `.gitignore` | Exclusion des secrets, caches, exports et sauvegardes privées | **CONSERVER** | Fichier d'exploitation/configuration utile. |

### README.md

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `README.md` | Guide principal utilisateur et architecture opérationnelle | **À SURVEILLER** | Réécrit : ancienne chronologie expérimentale supprimée. |

### apps

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `apps/api/app/advisor.py` | Conseiller de mangas et classement | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/advisor_ai.py` | Conseiller conversationnel avec IA locale | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/advisor_editions.py` | Gestion des éditions pour le conseiller | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/advisor_feedback.py` | Retour utilisateur et apprentissage des suggestions | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/advisor_quality.py` | Règles qualité et sécurité des recommandations | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/bnf_batch.py` | Recherche bibliographique BnF SRU, candidats à vérifier | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/collection.py` | Bibliothèque physique et ISBN | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/collection_bulk.py` | Import en masse de la collection | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/collection_scan.py` | Saisie et scanner ISBN | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/edition_discovery.py` | Repérage d'éditions disponibles | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/edition_enrichment.py` | Compléments aux éditions | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/inventory_import.py` | Import et rapprochement prudent de l'inventaire privé | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/inventory_resolution.py` | Résolution manuelle des ambiguïtés de l'inventaire | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/library_enrichment.py` | Enrichissement de la bibliothèque déjà déclarée | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/library_seed_selection.py` | Sélection du profil lecteur comme entrée du conseiller | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/localization.py` | Préférences linguistiques et libellés | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/main.py` | API FastAPI principale et routes publiques | **À SURVEILLER** | Très gros fichier (~127 Ko), endpoints et SQL mélangés ; découpage progressif à programmer. |
| `apps/api/app/mangadex_discovery.py` | Recherche de références MangaDex | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/mood_discovery.py` | Recherche guidée selon l'humeur | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/multilingual_aliases.py` | Titres alternatifs FR/EN/JA avec provenance | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/narrative_evidence.py` | Traçabilité des explications du conseiller | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/recommendation_explanations.py` | Explications de recommandations | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/recommendation_quality.py` | Qualité / cohérence des recommandations | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/app/wikidata_enrichment.py` | Titres localisés et attributs Wikidata | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/api/requirements.txt` | Dépendances Python du composant | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/ui/app/app.py` | Prototype Streamlit : Point d'entrée / contrôleur de l'interface | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `apps/ui/app/discovery.py` | Prototype Streamlit : Écran de découverte de mangas | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `apps/ui/app/recommendations.py` | Prototype Streamlit : Interface de recommandations | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `apps/ui/app/theme.css` | Prototype Streamlit : theme | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `apps/ui/requirements.txt` | Prototype Streamlit : requirements | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `apps/web/assets/advisor-editions.js` | Affichage des éditions dans le conseiller | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/advisor-view.js` | Interface du conseiller | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/app.css` | Point d'entrée / contrôleur de l'interface | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/app.js` | Point d'entrée / contrôleur de l'interface | **À SURVEILLER** | Très gros contrôleur JS (~86 Ko) ; séparation domaine/vue à programmer avec tests. |
| `apps/web/assets/appearance.css` | Personnalisation visuelle | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/appearance.js` | Personnalisation visuelle | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/bibliography-view.js` | Affichage bibliographique des fiches | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/bnf-candidates-view.js` | Liste des références BnF à revoir | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/bulk-import-view.js` | Vue d'import en lot | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/collection-view.js` | Vue de la collection personnelle | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/enrichment-view.js` | Suivi d'enrichissement de fiches | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/explain.js` | Présentation des motifs de recommandation | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/home.js` | Écran d'accueil | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/i18n.js` | Dictionnaire de traduction Web | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/inventory-resolution-view.js` | Interface de résolution d'inventaire | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/isbn-scanner.js` | Scanner et contrôles ISBN | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/library-display.js` | Présentation des mangas de la bibliothèque | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/mood-view.js` | Découverte par humeur | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/physical-inventory-view.js` | Tableau de l'inventaire physique | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/unknown-isbn-view.js` | Résolution des ISBN inconnus | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/assets/wikidata-view.js` | Consultation des données Wikidata | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/index.html` | Page HTML d'entrée Web | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `apps/web/nginx.conf` | Proxy et serveur Nginx Web | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |

### cmd

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `cmd/ai-setup.ps1` | Activation de l'IA locale facultative | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/benchmark-mangatheque.ps1` | Comparaison de la bibliothèque en lecture seule | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/build.cmd` | Commande d'exploitation Windows : build | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/clean.cmd` | Commande d'exploitation Windows : clean | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/common.cmd` | Commande d'exploitation Windows : common | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/control-center.ps1` | Centre de pilotage Windows | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/down.cmd` | Commande d'exploitation Windows : down | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/github-sync.ps1` | Mise à jour Git sécurisée | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/import-private-inventory.ps1` | Chargement privé de l'inventaire utilisateur | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/install-check.cmd` | Commande d'exploitation Windows : install check | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/library-backup.ps1` | Sauvegarde et restauration de vérification SQL | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/local-api.ps1` | Commande d'exploitation Windows : local api | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/logs.cmd` | Commande d'exploitation Windows : logs | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/mobile-setup.ps1` | Installation et arrêt du scanner mobile HTTPS | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/nuke.cmd` | Commande d'exploitation Windows : nuke | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/restart.cmd` | Commande d'exploitation Windows : restart | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/retire-legacy-ui.cmd` | Commande d'exploitation Windows : retire legacy ui | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-library-goal-tests.cmd` | Commande d'exploitation Windows : run library goal tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-library-import-robustness-tests.cmd` | Commande d'exploitation Windows : run library import robustness tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-library-import-tests.cmd` | Commande d'exploitation Windows : run library import tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-library-recommendation-tests.cmd` | Commande d'exploitation Windows : run library recommendation tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-library-status-tests.cmd` | Commande d'exploitation Windows : run library status tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-recommendation-tests.cmd` | Commande d'exploitation Windows : run recommendation tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/run-v0-8-validation.cmd` | Commande d'exploitation Windows : run  validation | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `cmd/start.cmd` | Commande d'exploitation Windows : start | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/status.cmd` | Commande d'exploitation Windows : status | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/stop.cmd` | Commande d'exploitation Windows : stop | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `cmd/up.cmd` | Commande d'exploitation Windows : up | **CONSERVER** | Fichier d'exploitation/configuration utile. |

### data

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `data/modele_bibliotheque_mangadvisor.csv` | Modèle public vierge d'import de bibliothèque | **CONSERVER** | Fichier d'exploitation/configuration utile. |
| `data/modele_bibliotheque_mangadvisor.xlsx` | Modèle public vierge d'import de bibliothèque | **À SURVEILLER** | Modèle vierge utile, ne jamais ajouter l'inventaire privé réel. |

### docs

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `docs/02_data/data_model_v1.md` | Documentation : data model v1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/02_data/data_pipeline_v1.md` | Documentation : data pipeline v1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/03_technical/audit_transversal_4_4.md` | Documentation : audit transversal 4 4 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/03_technical/cleanup_4_1.md` | Documentation : cleanup 4 1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/03_technical/infrastructure_single_web_4_5.md` | Documentation : infrastructure single web 4 5 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/03_technical/mangadvisor_architecture_v1.md` | Documentation : mangadvisor architecture v1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/03_technical/project_structure.md` | Documentation : project structure | **À SURVEILLER** | Réécrit pour refléter la Web seule, la base MAL et la veille incrémentale. |
| `docs/04_product/advisor_discovery_balance_3_1.md` | Documentation : advisor discovery balance 3 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/advisor_feedback_learning_3_5.md` | Documentation : advisor feedback learning 3 5 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/advisor_french_editions_2_3.md` | Documentation : advisor french editions 2 3 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/advisor_library_surprise_3_3.md` | Documentation : advisor library surprise 3 3 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/advisor_narrative_safety_2_2.md` | Documentation : advisor narrative safety 2 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/advisor_quality_safety_3_4.md` | Documentation : advisor quality safety 3 4 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/appearance_customization.md` | Documentation : appearance customization | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/benchmark_sources_4_9.md` | Documentation : benchmark sources 4 9 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/04_product/benchmark_sources_v2.md` | Documentation : benchmark sources v2 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/04_product/bibliographic_staging_v1.md` | Documentation : bibliographic staging v1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/04_product/bnf_bulk_import_4_8.md` | Documentation : bnf bulk import 4 8 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/bulk_collection_import_1_2.md` | Documentation : bulk collection import 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/catalogue_mal_complet.md` | Documentation : catalogue mal complet | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/catalogue_vivant_cycle.md` | Documentation : catalogue vivant cycle | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/control_center_4_0.md` | Documentation : control center 4 0 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/conversational_advisor_2_1.md` | Documentation : conversational advisor 2 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/design_system_v1.md` | Documentation : design system v1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/04_product/discovery_v1.md` | Documentation : discovery v1 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/04_product/edition_progress_known_isbns_1_2.md` | Documentation : edition progress known isbns 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/enrichissement_bnf_progressif_4_0.md` | Documentation : enrichissement bnf progressif 4 0 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/enrichissement_fr_direct_scrinis.md` | Documentation : enrichissement fr direct scrinis | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/explainable_recommendations_1_1.md` | Documentation : explainable recommendations 1 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/french_bibliography_discovery_1_2.md` | Documentation : french bibliography discovery 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/french_edition_enrichment_2_5.md` | Documentation : french edition enrichment 2 5 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/french_edition_enrichment_workshop_2_4.md` | Documentation : french edition enrichment workshop 2 4 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/french_editions_collection_1_2.md` | Documentation : french editions collection 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/french_records_reliability_1_2.md` | Documentation : french records reliability 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/guided_mood_discovery_2_0.md` | Documentation : guided mood discovery 2 0 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/inventaire_en_attente_4_3.md` | Documentation : inventaire en attente 4 3 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/isbn_camera_scanner_1_2.md` | Documentation : isbn camera scanner 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/library_backup_recovery_3_2.md` | Documentation : library backup recovery 3 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/library_enrichment_one_click_4_2.md` | Documentation : library enrichment one click 4 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/library_recommendations_4_7.md` | Documentation : library recommendations 4 7 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/local_ai_advisor_3_0.md` | Documentation : local ai advisor 3 0 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/manga_covers_v1.md` | Documentation : manga covers v1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/manual_pending_inventory_reconciliation_4_3.md` | Documentation : manual pending inventory reconciliation 4 3 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/mobile_https_scan_session_2_0.md` | Documentation : mobile https scan session 2 0 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/multilingual_aliases_4_4.md` | Documentation : multilingual aliases 4 4 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/physical_inventory_dashboard_3_9.md` | Documentation : physical inventory dashboard 3 9 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/private_library_benchmark_3_6.md` | Documentation : private library benchmark 3 6 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/recommendation_feedback_1_1.md` | Documentation : recommendation feedback 1 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/recommendation_quality_1_1.md` | Documentation : recommendation quality 1 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/recommendations_v1.md` | Documentation : recommendations v1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/resolve_unknown_isbns_1_2.md` | Documentation : resolve unknown isbns 1 2 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/roadmap_mangadvisor_1_1_to_2_0.md` | Documentation : roadmap mangadvisor 1 1 to 2 0 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/04_product/safe_inventory_import_3_8.md` | Documentation : safe inventory import 3 8 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/verified_source_links_1_1.md` | Documentation : verified source links 1 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/web_experience_bilingual.md` | Documentation : web experience bilingual | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/04_product/wikidata_metadata_enrichment_4_1.md` | Documentation : wikidata metadata enrichment 4 1 | **CONSERVER** | Documentation de fonctionnalité conservée (révision éditoriale possible). |
| `docs/STABILISATION_V0_8.md` | Documentation : STABILISATION V0 8 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/recommandation_tests_v0_6.md` | Documentation : recommandation tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/Mangadvisor V0.7 Data Foundation.docx` | Rapport instantané daté de QA/développement : Mangadvisor V0.7 Data Foundation.docx | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/jikan_recommendation_edges_diagnostic.md` | Rapport instantané daté de QA/développement : jikan recommendation edges diagnostic | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/library_goal_tests_v0_8_3.md` | Rapport instantané daté de QA/développement : library goal tests  3 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/library_import_robustness_tests_v0_8_11.md` | Rapport instantané daté de QA/développement : library import robustness tests  11 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/library_import_tests_v0_8_10.md` | Rapport instantané daté de QA/développement : library import tests  10 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/library_recommendation_tests_v0_8_2_profile_summary.md` | Rapport instantané daté de QA/développement : library recommendation tests  2 profile summary | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/library_status_tests_v0_8_5.md` | Rapport instantané daté de QA/développement : library status tests  5 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/recommendation_profile_tests_latest.md` | Rapport instantané daté de QA/développement : recommendation profile tests latest | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/repository_audit_2026_10_19.md` | Rapport instantané daté de QA/développement : repository audit 2026 10 19 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `docs/reports/repository_audit_2026_10_20.md` | Rapport instantané daté de QA/développement : repository audit 2026 10 20 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |

### infra

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `infra/compose/docker-compose.dev.yml` | Configuration Compose : docker compose.dev | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `infra/compose/docker-compose.local.yml` | Configuration Compose : docker compose.local | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `infra/compose/docker-compose.mobile.yml` | Configuration Compose : docker compose.mobile | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `infra/compose/docker-compose.yml` | Configuration Compose : docker compose | **À SURVEILLER** | Meilisearch est présent sans index applicatif entièrement confirmé ; ne pas supprimer son volume sans audit d'usage. |
| `infra/docker/api/Dockerfile` | Image Docker de api | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `infra/docker/engine/Dockerfile` | Image Docker de engine | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `infra/docker/ui/Dockerfile` | Image Docker de ui | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `infra/docker/web/Dockerfile` | Image Docker de web | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `infra/mobile/Caddyfile` | Configuration HTTPS Caddy pour scanner mobile | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |

### mangadvisor.cmd

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `mangadvisor.cmd` | Menu Windows unique de l'application | **CONSERVER** | Fichier d'exploitation/configuration utile. |

### pipelines

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `pipelines/__init__.py` | Fichier d'initialisation du paquet Python (vide par conception) | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/requirements.txt` | Dépendances Python du composant | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/analyze_jikan_recommendation_edges.py` | Rapport ponctuel d'analyse de recommandations Jikan | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/benchmark_manga_sources.py` | Ancien adaptateur de recherche (utilisé par V2) | **À SURVEILLER** | Nom expérimental, mais importé par V2 ; extraction d'un véritable adaptateur à programmer. |
| `pipelines/engine/scripts/benchmark_manga_sources_v2.py` | Analyse/sélection des candidats Scrinis/MangaUpdates (désormais bibliothèque de production) | **À SURVEILLER** | Ancien benchmark réutilisé comme client de production Scrinis/MangaUpdates ; ne PAS supprimer avant extraction des adaptateurs. |
| `pipelines/engine/scripts/bnf_bulk_import.py` | Chargement de lots de notices BnF | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/catalogue_french_matching.py` | Normalisation et revue des titres/éditions françaises | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/catalogue_lifecycle.py` | Cycle autonome de nouveautés et corrections MAL | **À SURVEILLER** | La veille ne garantit pas l'indexation immédiate de toutes les sorties ; pagination bornée, revue et surveillance nécessaires. |
| `pipelines/engine/scripts/catalogue_mangaupdates.py` | Vérification incrémentale MangaUpdates | **À SURVEILLER** | Conserve des preuves/candidats, pas une validation automatique des éditions FR. |
| `pipelines/engine/scripts/check_network.py` | Diagnostic des fournisseurs HTTPS | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/enrich_catalogue_scrinis_fr.py` | Rapprochement Scrinis sécurisé + titres français directs | **À SURVEILLER** | Écriture d'alias directe validée par tests ; une correspondance homonyme reste exclue. |
| `pipelines/engine/scripts/extract_jikan.py` | Extraction des anciennes pages MAL/Tenrai | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/extract_jikan_recommendations.py` | Extraction des suggestions communautaires | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py` | Chargement des relations de recommandations | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/load_jikan_to_postgres.py` | Transformation des données MAL vers PostgreSQL | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/scripts/prepare_bibliographic_staging.py` | Ancien stockage transitoire des rapports V2 | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/run_jikan_pipeline.py` | Orchestrateur historique du pipeline MAL | **À SURVEILLER** | Chevauchement historique avec synchronisation MAL complète ; toujours à vérifier dans l'installation guidée. |
| `pipelines/engine/scripts/run_library_goal_tests.py` | Script de pipeline historique : library goal tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/run_library_import_robustness_tests.py` | Script de pipeline historique : library import robustness tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/run_library_import_tests.py` | Script de pipeline historique : library import tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/run_library_recommendation_tests.py` | Script de pipeline historique : library recommendation tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/run_library_status_tests.py` | Script de pipeline historique : library status tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/run_recommendation_profile_tests.py` | Script de pipeline historique : recommendation profile tests | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `pipelines/engine/scripts/sync_full_mal_catalogue.py` | Parcours intégral paginé et reprise du cache MAL | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/src/__init__.py` | Initialisation Python / chargement pipeline | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/src/extract/__init__.py` | Initialisation Python / chargement pipeline | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/src/load/__init__.py` | Initialisation Python / chargement pipeline | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |
| `pipelines/engine/src/load/postgres_loader.py` | Connexion/UPSERT PostgreSQL sécurisés | **CONSERVER** | Code actif ou dépendance encore nécessaire à l'application. |

### pyproject.toml

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `pyproject.toml` | Métadonnées du projet, pytest et ruff | **À SURVEILLER** | Version 0.1.0 ancienne : source de versionnement unique à harmoniser. |

### sql

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `sql/queries/check_jikan_data_quality.sql` | Requête de contrôle SQL : check jikan data quality | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/queries/check_jikan_source_data.sql` | Requête de contrôle SQL : check jikan source data | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/queries/inspect_jikan_attributes.sql` | Requête de contrôle SQL : inspect jikan attributes | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/001_jikan_source_tables.sql` | Schéma/migration additive SQL : 001 jikan source tables | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/002_canonical_manga_tables.sql` | Schéma/migration additive SQL : 002 canonical manga tables | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/003_build_canonical_from_jikan.sql` | Schéma/migration additive SQL : 003 build canonical from jikan | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/004_add_theme_demographic_tables.sql` | Schéma/migration additive SQL : 004 add theme demographic tables | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/005_build_theme_demographic_from_jikan.sql` | Schéma/migration additive SQL : 005 build theme demographic from jikan | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/006_add_jikan_recommendation_tables.sql` | Schéma/migration additive SQL : 006 add jikan recommendation tables | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |
| `sql/schema/007_add_user_library_tables.sql` | Schéma/migration additive SQL : 007 add user library tables | **CONSERVER** | Schéma/diagnostic de la base ; retrait risqué sans migration. |

### tests

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `tests/integration/guided-ingestion-smoke.sh` | Test d'ingestion CI : guided ingestion smoke.sh | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/advisor_browser.py` | Test d'intégration/fumée : advisor browser | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/advisor_ownership_smoke.py` | Test d'intégration/fumée : advisor ownership smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/advisor_smoke.py` | Test d'intégration/fumée : advisor smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/browser_smoke.py` | Test d'intégration/fumée : browser smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/collection_bulk_smoke.py` | Test d'intégration/fumée : collection bulk smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/collection_smoke.py` | Test d'intégration/fumée : collection smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/explanations_smoke.py` | Test d'intégration/fumée : explanations smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/feedback_smoke.py` | Test d'intégration/fumée : feedback smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/inventory_import_smoke.py` | Test d'intégration/fumée : inventory import smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/isbn_camera_browser.py` | Test d'intégration/fumée : isbn camera browser | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/mood_discovery_browser.py` | Test d'intégration/fumée : mood discovery browser | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/mood_discovery_smoke.py` | Test d'intégration/fumée : mood discovery smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/ownership_exclusion_smoke.py` | Test d'intégration/fumée : ownership exclusion smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/physical_inventory_browser.py` | Test d'intégration/fumée : physical inventory browser | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/quality_smoke.py` | Test d'intégration/fumée : quality smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/rebuild_safety_smoke.py` | Test d'intégration/fumée : rebuild safety smoke | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/resolve_unknown_db.py` | Test d'intégration/fumée : resolve unknown db | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/seed_advisor.sql` | Test d'intégration/fumée : seed advisor | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/seed_catalog.sql` | Test d'intégration/fumée : seed catalog | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/smoke/seed_fr_editions.sql` | Test d'intégration/fumée : seed fr editions | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_ai.py` | Non-régression Python : advisor ai | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_balance.py` | Non-régression Python : advisor balance | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_editions.py` | Non-régression Python : advisor editions | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_feedback_learning.py` | Non-régression Python : advisor feedback learning | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_library_surprise.py` | Non-régression Python : advisor library surprise | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_ownership_fallback.py` | Non-régression Python : advisor ownership fallback | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_advisor_quality.py` | Non-régression Python : advisor quality | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_bibliographic_staging.py` | Non-régression Python : bibliographic staging | **RETIRÉ** | Supprimé du checkout ; conservé dans l'historique Git. |
| `tests/test_bnf_batch.py` | Non-régression Python : bnf batch | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_bnf_bulk_import.py` | Non-régression Python : bnf bulk import | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_catalogue_api_metadata.py` | Non-régression Python : catalogue api metadata | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_catalogue_french_matching.py` | Non-régression Python : catalogue french matching | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_catalogue_lifecycle.py` | Non-régression Python : catalogue lifecycle | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_catalogue_scrinis_fr_direct.py` | Non-régression Python : catalogue scrinis fr direct | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_catalogue_sources_benchmark.py` | Non-régression Python : catalogue sources benchmark | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_catalogue_sources_benchmark_v2.py` | Non-régression Python : catalogue sources benchmark v2 | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_check_network.py` | Non-régression Python : check network | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_collection_bulk.py` | Non-régression Python : collection bulk | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_collection_fr.py` | Non-régression Python : collection fr | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_collection_routes.py` | Non-régression Python : collection routes | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_collection_scan.py` | Non-régression Python : collection scan | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_conversational_advisor.py` | Non-régression Python : conversational advisor | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_cover_api.py` | Non-régression Python : cover api | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_discovery.py` | Non-régression Python : discovery | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_edition_discovery.py` | Non-régression Python : edition discovery | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_edition_enrichment.py` | Non-régression Python : edition enrichment | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_extended_tenrai_catalogue.py` | Non-régression Python : extended tenrai catalogue | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_feedback.py` | Non-régression Python : feedback | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_full_mal_catalogue_sync.py` | Non-régression Python : full mal catalogue sync | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_inventory_import.py` | Non-régression Python : inventory import | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_inventory_resolution.py` | Non-régression Python : inventory resolution | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_library_enrichment.py` | Non-régression Python : library enrichment | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_library_import_match_safety.py` | Non-régression Python : library import match safety | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_library_seed_selection.py` | Non-régression Python : library seed selection | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_localization.py` | Non-régression Python : localization | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_mangadex_discovery.py` | Non-régression Python : mangadex discovery | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_mood_discovery.py` | Non-régression Python : mood discovery | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_multilingual_aliases.py` | Non-régression Python : multilingual aliases | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_physical_inventory_summary.py` | Non-régression Python : physical inventory summary | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_pipeline_failure_modes.py` | Non-régression Python : pipeline failure modes | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_recommendation_explanations.py` | Non-régression Python : recommendation explanations | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_recommendation_ingestion_health.py` | Non-régression Python : recommendation ingestion health | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_recommendation_quality.py` | Non-régression Python : recommendation quality | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_recommendation_view.py` | Non-régression Python : recommendation view | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_repository_hygiene.py` | Non-régression Python : repository hygiene | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_repository_safety.py` | Non-régression Python : repository safety | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_single_web_deployment.py` | Non-régression Python : single web deployment | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_stabilisation_safety.py` | Non-régression Python : stabilisation safety | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_tenrai_migration.py` | Non-régression Python : tenrai migration | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_web_proxy_lifecycle.py` | Non-régression Python : web proxy lifecycle | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_wikidata_enrichment.py` | Non-régression Python : wikidata enrichment | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/test_windows_powershell51_encoding.py` | Non-régression Python : windows powershell51 encoding | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/advisor-editions.test.mjs` | Non-régression composant Web : advisor editions.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/advisor-view.test.mjs` | Non-régression composant Web : advisor view.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/appearance.test.mjs` | Non-régression composant Web : appearance.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/bibliography.test.mjs` | Non-régression composant Web : bibliography.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/bnf-candidates.test.mjs` | Non-régression composant Web : bnf candidates.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/bulk-import.test.mjs` | Non-régression composant Web : bulk import.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/collection.test.mjs` | Non-régression composant Web : collection.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/enrichment.test.mjs` | Non-régression composant Web : enrichment.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/explain.test.mjs` | Non-régression composant Web : explain.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/home.test.mjs` | Non-régression composant Web : home.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/inventory-resolution.test.mjs` | Non-régression composant Web : inventory resolution.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/isbn-scanner.test.mjs` | Non-régression composant Web : isbn scanner.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/library-display.test.mjs` | Non-régression composant Web : library display.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/mood-view.test.mjs` | Non-régression composant Web : mood view.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/physical-inventory.test.mjs` | Non-régression composant Web : physical inventory.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/unknown-isbn.test.mjs` | Non-régression composant Web : unknown isbn.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/web/wikidata-view.test.mjs` | Non-régression composant Web : wikidata view.test | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/windows/test-github-sync.ps1` | Non-régression Windows : test github sync | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/windows/test-menu-import-backup.ps1` | Non-régression Windows : test menu import backup | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/windows/test-menu-return.ps1` | Non-régression Windows : test menu return | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |
| `tests/windows/test-safe-git-update.ps1` | Non-régression Windows : test safe git update | **CONSERVER** | Utilisé pour sécuriser les évolutions et prévenir les régressions. |

### tools

| Fichier du dépôt initial | Fonction | Décision | Vérification / motif |
|---|---|---|---|
| `tools/audit_repository.py` | Audit automatique des fichiers suivis et garde-fous de dépôt | **À SURVEILLER** | Analyse structurale, syntaxe et liens ; ne remplace pas une preuve de fonctionnement sur le PostgreSQL privé. |
## Validation prévue avant fusion

- `python tools/audit_repository.py --strict` : tous les fichiers suivis, syntaxe Python et contrats de chemins/services.
- Tests Python `unittest`, modules Web `node --test`, menu Windows/PowerShell, construction Docker et tests d'intégration GitHub Actions.
- Aucun nettoyage destructeur de PostgreSQL/Meilisearch, aucun `docker compose down -v`.
- Si la CI échoue, corriger les références obsolètes sur la branche de nettoyage, sans fusion automatique.

## Dette technique conservée volontairement

La première passe retire les fichiers **manifestement historiques**. Elle ne
réécrit pas à l'aveugle le gros fichier `apps/api/app/main.py`, les endpoints
d'inventaire ou les règles du conseiller : ces blocs ont des tests et des
dépendances implicites, et leur simplification exige une étude de parité de
fonctionnement. Le nom ancien `Jikan` reste également sur les chemins
`data/raw/jikan` et certains scripts pour compatibilité avec ton PC.
