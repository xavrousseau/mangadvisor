# Structure actuelle de Mangadvisor (4.1)

> Ce document décrit les fichiers exécutés **aujourd'hui**, et non le plan d'architecture V1.

## Point d'entrée Windows

Double-cliquer sur **mangadvisor.cmd** : c'est l'unique menu utilisateur.
- **22** : assistant complet de première installation (config, SQL, Docker, catalogue, recommandations, sauvegardes, inventaire, contrôles).
- **25** : extraction puis synchronisation du catalogue manga depuis **Tenrai v1**.
- **26** : extraction et chargement des recommandations communautaires.
- **27** : diagnostic complet.
- **29** : diagnostic de l'accès réseau et de la réponse API manga.
- **17–21** : sauvegarde, vérification/restauration, benchmark et import contrôlé de bibliothèque.
- **11** : seule option destructive de volumes ; confirmation explicite requise.

L'ancien sous-menu **12** n'est plus proposé. Le numéro 12 reste un alias temporaire vers 25 pour les anciennes habitudes. Les raccourcis jikan-reset et jikan-pages sont refusés, au profit du parcours sécurisé 25.

## Arborescence utile

| Dossier / fichier | Utilité effective |
|---|---|
| mangadvisor.cmd | Menu principal pour tous les utilisateurs Windows |
| cmd/control-center.ps1 | Enchaînement installation, alimentation, mises à jour et diagnostics |
| cmd/*.cmd (maintenance active) | Petits lanceurs Docker ; certains outils PowerShell concernent la bibliothèque, l'IA et le mobile |
| infra/compose/ | Services PostgreSQL, Meilisearch, FastAPI, Web, ancienne UI Streamlit, extraction et IA facultative |
| infra/docker/ | Images Docker des services actifs |
| apps/web/ | **Interface principale** HTML/CSS/JS sur port UI_PORT (8501 par défaut) |
| apps/api/ | API FastAPI, catalogue, recommandations, ISBN et bibliothèque |
| apps/ui/ | Prototype Streamlit historique : profil Docker optionnel `legacy`, réservé aux tests ; non démarré sur le PC par défaut |
| pipelines/engine/scripts/ | Extraction du catalogue, chargement SQL, enrichissement communautaire, vérifications |
| pipelines/engine/src/load/ | Écriture PostgreSQL depuis les JSON |
| sql/schema/001…007 | Tables et mises à jour additives (les scripts 003/005 construisent le catalogue) |
| tests/ | Tests unitaires Python, JS Web, fumée Docker/PC/mobile |
| .github/workflows/ | Validation Windows/PowerShell, Python/JS, intégration Docker |
| docs/04_product/control_center_4_0.md | Instructions pratiques pour utiliser le logiciel |
| docs/03_technical/ | Architecture courante et historique de conception |
| data/modele_bibliotheque_mangadvisor.* | **Modèles publics vides** d'import CSV/Excel |

## Flux de données effectivement exécuté

1. Le centre de pilotage vérifie Docker Desktop, initialise les tables SQL et les conteneurs.
2. Les scripts historiques appelés extract_jikan.py et extract_jikan_recommendations.py interrogent **Tenrai v1** (base configurable via MANGA_API_BASE_URL).
3. Le système sauvegarde les réponses JSON sous data/raw/jikan/ (nom historique conservé pour compatibilité).
4. Le chargeur écrit jikan_manga_source et le catalogue manga canonique **sans modifier les identifiants des œuvres existantes**. Les tags genre/thème/démographie sont synchronisés de manière additive.
5. Le graphe de recommandations communautaires est chargé dans manga_recommendation_edge sans effacement préalable.
6. Les éditions françaises sont proposées à partir de données BnF après vérification ; **aucune importation exhaustive automatique d'ISBN n'est assurée**.
7. L'inventaire privé est importé uniquement après aperçu et validation explicite. Les correspondances incertaines restent à résoudre.

### Ce qui existe mais ne doit pas être annoncé comme entièrement opérationnel

Les services pgvector et Meilisearch sont prévus dans l'infrastructure ; cela **ne signifie pas** que les embeddings ou l'indexation Meilisearch complète sont systématiquement calculés et alimentés. AniList, MangaNews et le pipeline multi-sources complet décrit dans les documents V1 restent des pistes de développement, pas des étapes garanties.

Une seule interface utilisateur est démarrée par défaut : **Web sur 8501**. Le prototype Streamlit reste dans le code sous profil Docker optionnel `legacy` uniquement pour les tests historiques. Il n'est pas supprimé tant que ses anciennes fonctions et tests n'ont pas été migrés. Le proxy Web valide l'API par le DNS interne Docker (127.0.0.11) après changement d'IP du conteneur.

## Ce que le nettoyage 4.1 a retiré

Les arborescences _archive/ et legacy/ n'étaient jamais lancées par Docker, les menus ou les tests modernes. Elles ont été retirées de la **version courante du dépôt**, tout en restant consultables dans **l'historique Git**. Les scripts Windows historiques isolés nécessitant un Python hôte ont également été retirés lorsqu'ils reproduisaient les commandes du menu central. Voir [le relevé précis du nettoyage](cleanup_4_1.md).

## Fichiers privés : ne jamais les supprimer automatiquement

Les dossiers ignorés .env, private-data/, backups/, mobile-local/, .env.mobile et les données dans les **volumes Docker PostgreSQL/Meilisearch** sont **hors du nettoyage Git**. Pour les préserver, faire une sauvegarde vérifiée via le menu 17, puis en conserver une copie hors du PC.

Une commande git pull supprime de l'arborescence suivie les fichiers retirés du dépôt, mais **ne supprime pas ces fichiers privés ignorés ou les volumes Docker**.

## Documents de conception V1

Les fichiers data_pipeline_v1.md, data_model_v1.md et mangadvisor_architecture_v1.md portent désormais un avertissement : leurs diagrammes et promesses décrivent le plan initial, pas nécessairement les fonctionnalités branchées.
