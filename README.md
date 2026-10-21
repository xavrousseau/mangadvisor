# Mangadvisor

**Catalogue manga international, éditions françaises, mangathèque personnelle et conseiller IA.**

Mangadvisor est une application locale en français, organisée autour d'une seule
base **PostgreSQL** et d'une seule **interface Web**. Le catalogue de référence
repose sur les identifiants de manga **MyAnimeList (MAL)** ; il est alimenté via
Tenrai (format Jikan compatible), puis enrichi avec Scrinis, MangaUpdates,
Wikidata et la Bibliothèque nationale de France (BnF).

Les données personnelles restent dans les volumes PostgreSQL locaux et ne sont
jamais déduites d'un ISBN ou d'un titre trouvé chez un fournisseur externe.

## Démarrage sur Windows

**Prérequis :** Docker Desktop et le dépôt Git local. Démarrer
`mangadvisor.cmd` à la racine du projet ; aucune installation Python ou
PostgreSQL sur Windows n'est nécessaire.

| Commande | Utilité |
|---|---|
| **1 — Première installation** | Prépare la configuration privée, Docker, le catalogue et les services |
| **2 — Démarrer** | Lance l'application Web sans retélécharger le catalogue |
| **3 — Mettre à jour** | Met à jour Git et les images avec sauvegarde préalable |
| **4 — Sauvegarder** | Sauvegarde PostgreSQL et vérifie la restauration |
| **5 — Diagnostic** | Vérifie l'API, Docker et les données locales |
| **6 — Arrêter** | Arrêt sans suppression des volumes |
| **7 — Récupérer GitHub** | Met à jour les sources locales sans réinstaller les données |
| **A — Outils avancés** | Catalogue, enrichissements, imports, scanner, IA et maintenance |

Les données de la mangathèque et les anciennes éditions déclarées doivent
toujours être préservées lors d'une mise à jour. Le programme prévoit une
sauvegarde et un contrôle de restauration, sans suppression automatique.

## Catalogue : initialisation, enrichissement et nouveautés

La base internationale est initialisée **une fois** ; les évolutions
quotidiennes sont traitées **sans rescanner la totalité du catalogue**.

| Étape | Menu | Résultat réel |
|---|---|---|
| Initialisation MAL/Jikan | **A → 19** | Téléchargement paginé complet, cache JSON et construction des tables `jikan_manga_source` et `manga` |
| Compléter les titres français | **A → 20** | Titres FR Scrinis ajoutés à `manga_title_alias` seulement après contrôle d'identité et de publication française |
| Catalogue vivant | **A → 21** | Audit du socle, delta MAL, fiches corrigées, contrôles MangaUpdates/BnF et activation *facultative* du worker Docker quotidien |

**État initial communiqué par le dernier bilan local :** 85 776 identifiants
MAL distincts et 85 776 œuvres dans la table `manga`. Ce total représente
les notices publiques exposées par le fournisseur lors de la collecte,
pas une garantie d'exhaustivité de toutes les œuvres existantes.

Les JSON de catalogue restent directement sous le chemin historique
`data/raw/jikan/manga_page_N.json`, dans le dossier Git du PC.
Les nouveaux et anciens volumes de la mangathèque ne sont **jamais**
marqués comme possédés sur la foi d'un résultat Scrinis/BnF.

### Les enrichissements ne sont pas interchangeables

- **Tenrai / MAL** : identité canonique, descriptions, genres, catégories et auteurs.
- **Scrinis** : candidats d'éditions françaises papier et références ISBN ;
  rapprochement conservateur avec le bon manga.
- **MangaUpdates** : titres alternatifs, informations internationales et
  auteur/type utiles pour lever les ambiguïtés.
- **BnF / SRU** : notices bibliographiques françaises candidates ; les fichiers
  mensuels BnF doivent encore être déposés localement pour le traitement bulk.
- **Wikidata** : titres localisés et métadonnées de seconde source, quand
  l'identifiant MAL est confirmé.

Les deux `Wind Breaker`, les différentes versions de `Dragon Ball` et
les œuvres homonymes ne doivent jamais être fusionnés arbitrairement.

## Arborescence maintenue

| Dossier | Responsabilité |
|---|---|
| `apps/web/` | **Unique interface utilisateur** HTML, CSS, JavaScript et Nginx |
| `apps/api/` | FastAPI, bibliothèque physique, ISBN, recherche et conseiller |
| `pipelines/engine/` | Collecte, synchronisation et contrôles des fournisseurs |
| `sql/schema/` | Schémas PostgreSQL et consolidations additives |
| `infra/compose/`, `infra/docker/` | Conteneurs et modes stable, dev, mobile, automatisation |
| `cmd/`, `mangadvisor.cmd` | Commandes Windows et unique menu utilisateur |
| `tests/`, `.github/workflows/` | Tests de non-régression Python, Web, Windows et Docker |
| `tools/` | Audit structurel du dépôt |
| `docs/` | **Documentation actuelle** et inventaire d'architecture |
| `data/` | Modèles CSV/XLSX publics ; données brutes locales **ignorées par Git** |

L'ancienne UI Streamlit, les sorties de tests V0.x, les assistants de
benchmark sans effet sur le catalogue et les documents d'itérations ont
été retirés du dépôt courant. Leur historique reste accessible dans Git.
Les tests qui protègent les données et les fonctions réellement exécutées
sont conservés, même lorsqu'ils sont volumineux.

## Documentation utile

- [Catalogue initial MAL/Jikan](docs/04_product/catalogue_mal_complet.md)
- [Catalogue vivant et mises à jour automatiques](docs/04_product/catalogue_vivant_cycle.md)
- [Enrichissement français via Scrinis](docs/04_product/enrichissement_fr_direct_scrinis.md)
- [Import d'inventaire physique](docs/04_product/safe_inventory_import_3_8.md)
- [Réconciliation des entrées non identifiées](docs/04_product/manual_pending_inventory_reconciliation_4_3.md)
- [Import bibliographique BnF](docs/04_product/bnf_bulk_import_4_8.md)
- [Sauvegarde et restauration](docs/04_product/library_backup_recovery_3_2.md)
- [Structure technique](docs/03_technical/project_structure.md)
- [Audit fichier par fichier](docs/03_technical/inventaire_complet_git_2026_10_21.md)

## Sécurité et confidentialité

Les chemins `.env`, `private-data/`, `backups/`, `data/raw/`,
`data/logs/` et les volumes Docker restent **hors du dépôt Git**.
Une suppression de fichiers suivis par Git ne doit jamais toucher aux
sauvegardes personnelles ni aux volumes persistants PostgreSQL.

La veille Docker doit être activée explicitement depuis **A → 21** et
ne fonctionne que lorsque Docker Desktop et le PC tournent. Les cas
ambigus restent à contrôler ; aucune suggestion bibliographique ne
prouve qu'un manga ou un tome est possédé.
