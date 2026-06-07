# Mangadvisor — Data Pipeline v1

## 1. Objectif

Ce document décrit le **pipeline de données Mangadvisor**.

Le pipeline est responsable de :

* récupérer les données depuis plusieurs sources
* normaliser les formats
* consolider les œuvres
* enrichir les métadonnées
* générer des embeddings
* charger la base PostgreSQL
* indexer les données dans Meilisearch

Le pipeline constitue le **cœur data du projet**.

---

# 2. Architecture générale du pipeline

Le pipeline suit une architecture en plusieurs étapes.

```
Sources externes
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
Chargement PostgreSQL
      ↓
Indexation Meilisearch
```

Chaque étape est implémentée sous forme de modules Python.

---

# 3. Sources de données

Le pipeline récupère les données depuis plusieurs sources.

## Jikan API

Source principale pour les mangas.

Données récupérées :

* titre
* synopsis
* genres
* score
* popularité
* statut
* volumes
* chapitres

Documentation :

```
https://jikan.moe
```

---

## AniList API

API GraphQL.

Utilisée pour enrichir :

* relations entre œuvres
* tags
* popularité
* métadonnées supplémentaires

Documentation :

```
https://anilist.co
```

---

## MangaNews

Source éditoriale française.

Utilisée pour :

* enrichir les métadonnées
* compléter certaines informations

---

# 4. Structure du pipeline

Le pipeline est situé dans :

```
pipelines/engine
```

Structure recommandée :

```
pipelines/engine
│
├── scripts
│
├── src
│   ├── common
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

# 5. Étape 1 — Extraction

Objectif :

Récupérer les données depuis les APIs et sources externes.

Modules concernés :

```
src/extract
```

Scripts possibles :

```
extract_jikan.py
extract_anilist.py
extract_manganews.py
```

Sortie :

```
data/raw/
```

Exemple :

```
data/raw/jikan/manga.json
data/raw/anilist/manga.json
```

---

# 6. Étape 2 — Normalisation

Objectif :

Transformer les données dans un format commun.

Modules :

```
src/normalize
```

Transformations :

* uniformisation des champs
* nettoyage du texte
* gestion des titres multiples
* conversion des dates

Sortie :

```
data/staging/
```

---

# 7. Étape 3 — Rapprochement des œuvres

Objectif :

Identifier les mangas identiques provenant de différentes sources.

Problème :

Un même manga peut exister dans plusieurs APIs.

Exemple :

```
Vagabond
```

peut exister dans :

* MyAnimeList
* AniList
* MangaNews

Solution :

Algorithme de rapprochement basé sur :

* similarité de titre
* auteur
* année

Sortie :

```
table manga canonique
```

---

# 8. Étape 4 — Enrichissement

Objectif :

Ajouter des métadonnées utiles.

Modules :

```
src/enrich
```

Ajouts possibles :

* tags
* genres
* relations
* statistiques

Sortie :

```
data/curated/
```

---

# 9. Étape 5 — Embeddings

Objectif :

Générer un vecteur représentant chaque manga.

Utilisé pour :

* recommandations
* similarité sémantique

Modèle utilisé :

```
sentence-transformers/all-MiniLM-L6-v2
```

Dimension :

```
384
```

Modules :

```
src/embed
```

Sortie :

```
manga_embeddings
```

---

# 10. Étape 6 — Chargement PostgreSQL

Objectif :

Insérer les données dans la base.

Modules :

```
src/load
```

Tables principales :

```
manga
genres
tags
manga_genres
manga_tags
manga_relations
manga_embeddings
```

---

# 11. Étape 7 — Indexation Meilisearch

Objectif :

Indexer les mangas pour la recherche.

Modules :

```
src/index
```

Index principal :

```
manga
```

Champs indexés :

```
title
genres
tags
score
popularity
```

---

# 12. Scripts d’exécution

Les scripts orchestrant le pipeline sont situés dans :

```
pipelines/engine/scripts
```

Exemples :

```
run_extract.py
run_normalize.py
run_reconcile.py
run_enrich.py
run_embed.py
run_load.py
run_index.py
```

---

# 13. Pipeline complet

Exécution complète :

```
run_pipeline.py
```

Logique :

```
extract
→ normalize
→ reconcile
→ enrich
→ embed
→ load
→ index
```

---

# 14. Fréquence d’exécution

Deux modes sont possibles.

## mode batch

Exécution complète :

```
1 fois par jour
```

---

## mode développement

Exécution partielle :

```
module par module
```

---

# 15. Gestion des erreurs

Le pipeline doit :

* logguer les erreurs
* continuer si possible
* permettre un redémarrage partiel

Les logs sont stockés dans :

```
data/logs
```

---

# 16. Observabilité

Chaque étape du pipeline doit produire :

* logs
* métriques simples

Exemples :

```
nombre mangas extraits
nombre mangas consolidés
nombre embeddings générés
```

---

# 17. Évolutions futures

Le pipeline pourra intégrer :

## LLM

Utilisation possible :

* génération de résumés
* enrichissement des tags
* explications de recommandations

Technologie envisagée :

```
Ollama
```

---

## Traduction

Pour les synopsis :

```
Argos Translate
ou
LibreTranslate
```

---

# 18. Résumé

Le pipeline Mangadvisor permet de transformer plusieurs sources de données en un catalogue enrichi utilisable pour la recommandation.

Étapes principales :

```
Extract
Normalize
Reconcile
Enrich
Embed
Load
Index
```

Cette architecture permet :

* d’ajouter facilement de nouvelles sources
* d’améliorer progressivement le moteur de recommandation
* de maintenir une base de données propre et cohérente.

---

# Fin du document

 