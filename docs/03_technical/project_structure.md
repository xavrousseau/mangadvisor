# Architecture actuelle de Mangadvisor

**État :** 21 octobre 2026 — audit du dépôt Git, après retrait des
prototypes Streamlit, anciens rapports et anciens assistants de benchmark.

## Un seul point d'entrée et une seule interface

- **`mangadvisor.cmd`** est le menu Windows utilisateur.
- **`cmd/control-center.ps1`** orchestre Docker, PostgreSQL, sauvegardes,
  catalogue, imports et mises à jour.
- **`apps/web/`** est l'unique interface : JavaScript/CSS/HTML derrière Nginx.
- **`apps/api/app/main.py`** est l'API FastAPI. Les modules de domaine
  restent séparés dans `apps/api/app/`.
- L'ancien Streamlit `apps/ui/` a été supprimé de la branche active.
  Son code reste récupérable par l'historique Git, mais certaines anciennes
  fonctions CSV/XLSX historiques ne sont pas toutes représentées à
  l'identique dans le Web : ne pas prétendre à une équivalence parfaite.

## Données et synchronisation

1. **Tenrai (compatibilité Jikan) / MAL** : `sync_full_mal_catalogue.py`
   conserve les JSON du référentiel initial sous `data/raw/jikan/`,
   crée des entrées `jikan_manga_source` et consolide `manga`.
2. **`catalogue_lifecycle.py`** : après audit du chargement initial,
   relève les nouvelles œuvres et certaines corrections de notices,
   seulement sur des fenêtres bornées ; conteneur `catalog-sync`
   opt-in dans Docker Compose.
3. **`enrich_catalogue_scrinis_fr.py`** : rattache un titre FR sourcé à
   un ID MAL après vérification stricte de l'œuvre ; les ISBN référencés
   ne deviennent pas des volumes possédés.
4. **`catalogue_mangaupdates.py`**, `bnf_batch.py`,
   `bnf_bulk_import.py`, `wikidata_enrichment.py` : éléments de preuve,
   enrichissement international et bibliographie française.
5. **`apps/api/app/inventory_import.py`**, `collection.py` et
   `inventory_resolution.py` : mangathèque et inventaire privé,
   séparés des informations bibliographiques publiques.

**Tables distinctes** : `manga` = référentiel canonique ;
`jikan_manga_source` = cache normalisé MAL ;
`manga_title_alias` = titres alternatifs sourcés ;
`user_manga_*` = états privés de la collection.
Les éditions françaises et ISBN sont des entités documentaires à relier
avec provenance, sans déduire la propriété.

## Infrastructure

- `infra/compose/docker-compose.yml` : PostgreSQL, API, Web, moteur de
  collecte et services optionnels Meilisearch, Ollama, `catalog-sync`.
- `infra/compose/docker-compose.local.yml` : profil stable local Windows,
  ports en boucle locale et montage des données brutes du PC.
- `infra/compose/docker-compose.dev.yml` : rechargement à chaud **sans
  ancien service Streamlit**.
- `infra/compose/docker-compose.mobile.yml` : HTTPS mobile opt-in.
- `infra/docker/` : images `api`, `engine`, `web`.
- `sql/schema/001…007` : création et consolidations non destructrices.

Le volume nommé `mangadvisor_pgdata` dans Docker garde le contenu
PostgreSQL ; les JSON `data/raw/jikan` sont des fichiers sources, pas
la base SQL elle-même. Les dossiers privés ignorés par Git et les
volumes Docker ne doivent **jamais** être effacés pour nettoyer le dépôt.

## Contrats de qualité maintenus

- `tests/test_*.py` : contrôles Python unitaires, SQL de sécurité,
  rapprochement strict des éditions, refus des homonymes.
- `tests/web/*.test.mjs` : interface Web et interactions.
- `tests/smoke/` et `tests/integration/` : FastAPI, PostgreSQL, Nginx
  et parcours de collection sous environnement CI.
- `tests/windows/` : menu et PowerShell Windows.
- `.github/workflows/` : tests Python, Windows, Docker et intégration.
- `tools/audit_repository.py` : inventaire de fichiers suivis, syntaxe et
  références de fichiers explicites.

Les rapports de QA générés vont désormais sous
`data/logs/quality_reports/`, **hors de Git**, mais les programmes
de tests restent conservés. Le document
[inventaire complet](inventaire_complet_git_2026_10_21.md) donne la
décision fichier par fichier.

## Dette technique non masquée

- **`apps/api/app/main.py` et `apps/web/assets/app.js`** restent
  volumineux ; le découpage nécessite des tests de parité fonctionnelle.
- **`benchmark_manga_sources.py` et `benchmark_manga_sources_v2.py`**
  ne sont plus proposés dans le menu normal, mais servent toujours
  d'adaptateurs de source aux collecteurs actifs. Les supprimer
  immédiatement casserait l'enrichissement Scrinis/MangaUpdates.
- Meilisearch demeure dans Compose ; son exploitation par un index
  applicatif est à confirmer avant de retirer son service ou son volume.
- L'enrichissement de toutes les œuvres MAL par MangaUpdates/BnF n'est
  pas garanti à la fin de la synchronisation initiale : c'est une file
  progressive, avec des vérifications conservatrices.
- Les documents historiques restent disponibles dans l'historique Git,
  mais **ne polluent plus le checkout**.
