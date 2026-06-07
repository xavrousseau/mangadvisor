# Mangadvisor — Architecture v1

## 1. Présentation du projet

**Mangadvisor** est un moteur de recommandation de mangas basé sur l’analyse de catalogues publics et enrichi par des techniques de recherche sémantique.

L’objectif est de proposer des recommandations pertinentes et expliquées à partir des lectures et préférences des utilisateurs.

Le projet repose sur :

* l’agrégation de plusieurs sources de données
* une normalisation des catalogues
* un moteur de recherche performant
* un moteur de similarité basé sur embeddings
* une API et une interface utilisateur simple

Le projet est conçu comme un **MVP reproductible et compréhensible**, avec une architecture claire.

---

# 2. Objectifs du MVP

Le MVP Mangadvisor doit permettre :

* la recherche d’un manga
* la consultation de fiches œuvres
* la recommandation de mangas similaires
* l’affichage d’explications simples

Les recommandations doivent être :

* utiles
* contextualisées
* explicables

Format d’explication :

```
Tags communs (≤3)
Score de similarité
Phrase explicative ≤160 caractères
```

Exemple :

```
Tags : samouraï, historique, contemplatif
Score : 0.86
Phrase : Proche de Vagabond par son ambiance samouraï et son ton contemplatif.
```

---

# 3. Sources de données

Mangadvisor agrège plusieurs sources publiques :

### Jikan API

Wrapper non officiel de MyAnimeList.

Utilisé pour :

* catalogue manga
* genres
* scores
* synopsis

Documentation :
[https://jikan.moe](https://jikan.moe)

---

### AniList API

GraphQL API.

Utilisée pour :

* métadonnées supplémentaires
* relations entre œuvres
* popularité
* tags

Documentation :
[https://anilist.co](https://anilist.co)

---

### MangaNews

Source éditoriale française.

Utilisée pour :

* enrichissement du catalogue
* métadonnées complémentaires

---

# 4. Pipeline de données

Le pipeline Mangadvisor est conçu en plusieurs étapes.

```
Sources
   ↓
Extraction
   ↓
Normalisation
   ↓
Rapprochement des œuvres
   ↓
Enrichissement
   ↓
Embeddings
   ↓
Chargement base
   ↓
Indexation recherche
```

---

## Extraction

Les données sont récupérées via :

* API Jikan
* API AniList
* scraping MangaNews

Scripts Python exécutés dans :

```
pipelines/engine/scripts
```

---

## Normalisation

Les données sont transformées dans un format commun :

* titres
* auteurs
* genres
* synopsis
* relations

Les transformations sont réalisées dans le pipeline.

---

## Rapprochement des œuvres

Les œuvres provenant de différentes sources sont rapprochées.

Objectif :

```
1 manga = 1 entité canonique
```

---

## Enrichissement

Les données sont enrichies avec :

* tags
* relations
* informations éditoriales

---

## Embeddings

Un vecteur est généré pour chaque œuvre.

Modèle prévu :

```
sentence-transformers/all-MiniLM-L6-v2
```

Utilisation :

* similarité sémantique
* recommandations

---

## Chargement base

Les données finales sont chargées dans PostgreSQL.

La base contient :

* catalogue canonique
* tags
* relations
* embeddings

---

## Indexation recherche

Les œuvres sont indexées dans Meilisearch.

Objectif :

* recherche rapide
* filtres
* autocomplétion

---

# 5. Architecture technique

Architecture générale :

```
Sources
   ↓
Pipeline Engine
   ↓
PostgreSQL + pgvector
   ↓
Meilisearch
   ↓
API (FastAPI)
   ↓
UI (Streamlit)
```

---

# 6. Stack technique

## Infrastructure

* Docker
* Docker Compose

---

## Base de données

PostgreSQL + extension pgvector.

Stocke :

* catalogue
* relations
* embeddings

---

## Recherche

Meilisearch.

Utilisé pour :

* recherche rapide
* filtrage
* autocomplétion

---

## API

FastAPI.

Expose :

```
/search
/manga/{id}
/recommendations
```

---

## Interface utilisateur

Streamlit.

Permet :

* recherche manga
* affichage fiches
* recommandations

---

## Pipeline data

Scripts Python exécutés dans :

```
pipelines/engine
```

Responsable de :

* extraction
* transformation
* enrichissement
* indexation

---

# 7. Infrastructure Docker

La stack locale contient les services suivants.

```
postgres
meilisearch
api
ui
engine
```

---

## PostgreSQL

Conteneur :

```
mangadvisor_postgres
```

Stockage :

```
volume mangadvisor_pgdata
```

---

## Meilisearch

Conteneur :

```
mangadvisor_meilisearch
```

Stockage :

```
volume mangadvisor_meili
```

---

## API

Conteneur :

```
mangadvisor_api
```

Expose :

```
http://localhost:8000
```

---

## UI

Conteneur :

```
mangadvisor_ui
```

Expose :

```
http://localhost:8501
```

---

## Engine

Conteneur :

```
mangadvisor_engine
```

Responsable du pipeline data.

---

# 8. Réseau Docker

Réseau dédié :

```
mangadvisor_network
```

Tous les services communiquent via ce réseau.

---

# 9. Variables d’environnement

Fichier :

```
.env
```

Variables principales :

```
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD

MEILI_MASTER_KEY

API_PORT
UI_PORT

EMBEDDING_MODEL
ENABLE_TRANSLATION
ENABLE_OLLAMA
```

---

# 10. Commandes Windows

Scripts présents dans :

```
cmd/
```

Scripts disponibles :

```
install-check.cmd
build.cmd
up.cmd
start.cmd
status.cmd
logs.cmd
stop.cmd
down.cmd
restart.cmd
clean.cmd
nuke.cmd
```

Script principal :

```
mangadvisor.cmd
```

---

## Utilisation

Menu interactif :

```
mangadvisor.cmd
```

Commandes directes :

```
mangadvisor.cmd build
mangadvisor.cmd start
mangadvisor.cmd logs
mangadvisor.cmd down
```

---

# 11. Vérification de la stack

Une installation correcte permet d’accéder à :

## API

```
http://localhost:8000
```

---

## Documentation API

```
http://localhost:8000/docs
```

---

## Interface utilisateur

```
http://localhost:8501
```

---

## Meilisearch

```
http://localhost:7700
```

---

# 12. Prochaines étapes

Les prochaines étapes du projet sont :

### Étape 11

Implémentation du pipeline data.

* extraction Jikan
* extraction AniList
* scraping MangaNews

---

### Étape 12

Création du schéma PostgreSQL.

---

### Étape 13

Indexation Meilisearch.

---

### Étape 14

Implémentation du moteur de recommandations.

---

### Étape 15

Connexion API → UI.

---

# 13. Philosophie du projet

Mangadvisor suit plusieurs principes :

* architecture simple
* composants découplés
* documentation claire
* reproductibilité
* MVP compréhensible

Le projet est volontairement structuré pour rester accessible à un profil data analyst souhaitant développer un projet data complet.

---

# Fin du document

 