# Structure actuelle de Mangadvisor (4.x)

> Ce document décrit les fichiers exécutés **aujourd'hui**, et non le plan d'architecture V1. Voir aussi [l'audit transversal 4.4](audit_transversal_4_4.md) pour l'inventaire fichier par fichier et les limites des tests.

## Point d'entree Windows

Double-cliquer sur **mangadvisor.cmd** : c'est l'unique menu utilisateur.

- **1** : installation guidee, incluant le catalogue MAL/Jikan **complet**.
- **2** : demarrer et ouvrir l'application Web.
- **3** : mettre a jour le code, sauvegarder et controler les services.
- **4** : sauvegarder et verifier la restauration PostgreSQL.
- **5** : diagnostic.
- **6** : arreter l'application **et le synchroniseur** s'il est actif.
- **7** : mise a jour du code GitHub uniquement.
- **A -> 19** : revalidation / rechargement manuel du catalogue MAL complet.
- **A -> 20** : enrichment FR par Scrinis.
- **A -> 21** : verifier, activer, arreter ou inspecter le cycle incremental.
- **A -> S** : maintenance, configuration et restauration.

Les anciens lanceurs Docker de `cmd/` et les cinq scripts historiques
utilisant `--reset-library` ont ete retires de la branche de nettoyage.
Leur couverture fonctionnelle exhaustive reste a verifier avant fusion. Aucun effacement de volume
PostgreSQL n'est expose au menu principal.

## Arborescence utile

| Dossier / fichier | Utilité effective |
|---|---|
| mangadvisor.cmd | Menu principal pour tous les utilisateurs Windows |
| cmd/control-center.ps1 | Enchaînement installation, alimentation, mises à jour et diagnostics |
| cmd/*.ps1 (8 scripts) | Orchestrateur Windows, sauvegarde, Git, import personnel, benchmark prive, API locale, IA et acces mobile. Plus aucun lanceur .cmd historique dans ce dossier |
| infra/compose/ | `docker-compose.yml` définit les services communs, `docker-compose.local.yml` fournit la configuration stable par défaut, `docker-compose.dev.yml` la configuration de développement sans ancienne interface Streamlit |
| infra/docker/ | Images Docker des services actifs |
| apps/web/ | **Interface principale** HTML/CSS/JS sur port UI_PORT (8501 par défaut) |
| apps/api/ | API FastAPI, catalogue, recommandations, ISBN et bibliothèque |
| apps/ui/ | **Retiré** : import CSV/XLSX de bibliothèque, modèles, profil de lecture et recommandations transférés vers l'API et le Web ; les utilitaires Python du prototype ne sont plus chargés |
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
5. Le graphe de recommandations communautaires est chargé dans manga_recommendation_edge sans effacement préalable : l'ancienne option `--reset` est refusee.
6. En cas de doublons MAL entre fichiers SEARCH/TOP, le chargeur conserve les champs non vides ; l'UPSERT evite egalement de remplacer des metadonnees existantes par NULL ou des listes JSON vides.
7. Les éditions françaises sont proposées à partir de données BnF après vérification ; **aucune importation exhaustive automatique d'ISBN n'est assurée**.
8. L'inventaire privé est importé uniquement après aperçu et validation explicite. Les correspondances incertaines restent à résoudre.

### Ce qui existe mais ne doit pas être annoncé comme entièrement opérationnel

Les services pgvector et Meilisearch sont prévus dans l'infrastructure ; cela **ne signifie pas** que les embeddings ou l'indexation Meilisearch complète sont systématiquement calculés et alimentés. AniList, MangaNews et le pipeline multi-sources complet décrit dans les documents V1 restent des pistes de développement, pas des étapes garanties.

Une seule interface utilisateur existe dans la configuration stable : **Web sur 8501**. Le Compose principal n'a aucun service `ui` et le centre de pilotage retire au premier demarrage un eventuel ancien conteneur Streamlit. L'ancien prototype Streamlit et son profil de développement ont été retirés ; l'import CSV/XLSX, les modèles et le profil de lecture sont disponibles dans le Web. Le test de parité navigateur est maintenu dans la CI. Le proxy Web valide l'API par le DNS interne Docker (127.0.0.11) après changement d'IP du conteneur.

## Ce que le nettoyage 4.1 a retiré

Les arborescences _archive/ et legacy/ n'étaient jamais lancées par Docker, les menus ou les tests modernes. Elles ont été retirées de la **version courante du dépôt**, tout en restant consultables dans **l'historique Git**. Les scripts Windows historiques isolés nécessitant un Python hôte ont également été retirés lorsqu'ils reproduisaient les commandes du menu central. Voir [le relevé précis du nettoyage](cleanup_4_1.md).

## Fichiers privés : ne jamais les supprimer automatiquement

Les dossiers ignorés .env, private-data/, backups/, mobile-local/, .env.mobile et les données dans les **volumes Docker PostgreSQL/Meilisearch** sont **hors du nettoyage Git**. Pour les préserver, faire une sauvegarde verifiee via le menu principal 4, puis en conserver une copie hors du PC.

Une commande git pull supprime de l'arborescence suivie les fichiers retirés du dépôt, mais **ne supprime pas ces fichiers privés ignorés ou les volumes Docker**.

## Documents de conception V1

Les fichiers data_pipeline_v1.md, data_model_v1.md et mangadvisor_architecture_v1.md portent désormais un avertissement : leurs diagrammes et promesses décrivent le plan initial, pas nécessairement les fonctionnalités branchées.

## Nettoyage `pipelines/` (PR #89, non fusionnee)

- Ancien orchestrateur `run_jikan_pipeline.py` retire. Les deux scripts SQL de consolidation sont appeles depuis le centre de pilotage, puis verifies sur une base CI jetable.
- Cinq anciens lanceurs de tests destructeurs `run_library_*_tests.py` retires ; des tests modernes non destructifs subsistent dans `tests/`. Leur equivalence complete reste a confirmer.
- Le menu avance A -> 16 redirige vers le comparatif V2, deja accessible en A -> 17 ; le module `benchmark_manga_sources.py` reste une dependance Python de la V2 et des enrichissements. Il n'est **pas** supprimable isolement.
- Les tests GitHub Actions verts concernent une base jetable, pas les volumes du PC.
- Politique de mise a jour source a approfondir : champ absent et suppression explicite fournisseur ne sont pas encore distingues.
