# Mangadvisor — Project Structure

## 1. Objectif

Ce document décrit l’organisation du dépôt **Mangadvisor**.

L’objectif est de :

* rendre la structure du projet compréhensible
* faciliter la maintenance
* permettre une prise en main rapide
* documenter les responsabilités de chaque dossier

Le projet est organisé selon plusieurs couches :

```text
Applications
Pipeline data
Infrastructure
Données
Documentation
```

---

# 2. Vue globale de l’arborescence

Structure simplifiée du projet :

```text
mangadvisor
│
├── apps
│   ├── api
│   └── ui
│
├── pipelines
│   └── engine
│
├── infra
│   ├── compose
│   └── docker
│
├── data
│   ├── raw
│   ├── staging
│   ├── curated
│   ├── features
│   └── exports
│
├── sql
│
├── docs
│
├── cmd
│
├── tests
│
├── .env
├── .env.example
├── pyproject.toml
├── README.md
└── mangadvisor.cmd
```

---

# 3. Dossier `apps`

Contient les applications exposées aux utilisateurs.

```text
apps/
```

---

## 3.1 API

```text
apps/api
```

Contient l’API backend du projet.

Technologie :

```text
FastAPI
```

Responsabilités :

* exposer les endpoints
* récupérer les données dans PostgreSQL
* interroger Meilisearch
* fournir les recommandations

Structure interne :

```text
apps/api
│
├── app
│   ├── main.py
│   ├── routes
│   ├── services
│   └── models
│
└── requirements.txt
```

---

## 3.2 Interface utilisateur

```text
apps/ui
```

Interface utilisateur du projet.

Technologie :

```text
Streamlit
```

Responsabilités :

* recherche manga
* affichage fiches œuvres
* affichage recommandations

Structure interne :

```text
apps/ui
│
├── app
│   └── app.py
│
└── requirements.txt
```

---

# 4. Dossier `pipelines`

Contient la logique data du projet.

```text
pipelines/
```

---

## Engine

```text
pipelines/engine
```

Moteur du pipeline de données.

Responsabilités :

* extraction des sources
* normalisation des données
* rapprochement des œuvres
* enrichissement
* génération des embeddings
* chargement base
* indexation Meilisearch

Structure interne :

```text
pipelines/engine
│
├── scripts
│
├── src
│   ├── extract
│   ├── normalize
│   ├── reconcile
│   ├── enrich
│   ├── embed
│   ├── load
│   └── index
│
└── requirements.txt
```

---

# 5. Dossier `infra`

Contient toute l’infrastructure technique.

```text
infra/
```

---

## Docker Compose

```text
infra/compose
```

Contient :

```text
docker-compose.yml
docker-compose.dev.yml
```

Responsabilités :

* définir les services
* orchestrer la stack
* configurer les volumes
* configurer les réseaux

Services :

```text
postgres
meilisearch
api
ui
engine
```

---

## Dockerfiles

```text
infra/docker
```

Contient les images Docker des services.

```text
infra/docker
│
├── api
│   └── Dockerfile
│
├── ui
│   └── Dockerfile
│
└── engine
    └── Dockerfile
```

---

# 6. Dossier `data`

Contient les données du projet.

```text
data/
```

Organisation inspirée des architectures data modernes.

---

## Raw

```text
data/raw
```

Données brutes provenant des sources.

Exemples :

```text
jikan
anilist
manganews
```

---

## Staging

```text
data/staging
```

Données transformées mais pas encore consolidées.

---

## Curated

```text
data/curated
```

Catalogue manga propre et consolidé.

---

## Features

```text
data/features
```

Données enrichies utilisées par les modèles.

Exemples :

```text
embeddings
similarities
```

---

## Exports

```text
data/exports
```

Exports destinés :

* à l’API
* à Meilisearch

---

# 7. Dossier `sql`

Contient les scripts SQL.

```text
sql/
```

Organisation recommandée :

```text
sql/
├── schema
├── seeds
└── queries
```

---

# 8. Dossier `docs`

Documentation du projet.

```text
docs/
```

Structure :

```text
docs
│
├── 01_product
├── 02_data
├── 03_technical
├── 04_operating_guides
└── 05_decisions
```

Documents clés :

```text
mangadvisor_architecture_v1.md
project_structure.md
```

---

# 9. Dossier `cmd`

Scripts Windows pour gérer la stack.

```text
cmd/
```

Scripts disponibles :

```text
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

```text
mangadvisor.cmd
```

---

# 10. Dossier `tests`

Tests du projet.

```text
tests/
```

Structure recommandée :

```text
tests
├── unit
├── integration
└── data_quality
```

---

# 11. Fichiers racine importants

## `.env`

Configuration locale.

---

## `.env.example`

Modèle de configuration.

---

## `pyproject.toml`

Configuration Python :

* outils
* dépendances
* linting

---

## `README.md`

Présentation du projet.

---

## `mangadvisor.cmd`

Interface CLI Windows permettant de gérer la stack.

---

# 12. Architecture logique

Architecture globale :

```text
Sources
  ↓
Pipeline Engine
  ↓
PostgreSQL + pgvector
  ↓
Meilisearch
  ↓
API
  ↓
UI
```

---

# 13. Philosophie du projet

Le projet Mangadvisor est construit selon les principes suivants :

* architecture simple
* séparation claire des responsabilités
* documentation complète
* reproductibilité
* compréhension accessible

Le projet est volontairement structuré pour être **compréhensible par un profil data analyst** souhaitant développer un projet data complet.

---

# Fin du document

 