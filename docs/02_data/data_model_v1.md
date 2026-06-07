# Mangadvisor — Data Model v1

## 1. Objectif

Ce document définit le **modèle de données principal** du projet Mangadvisor.

Le modèle doit permettre :

* l’agrégation de plusieurs sources de données
* la consolidation des œuvres
* l’enrichissement des métadonnées
* la recherche rapide
* la génération de recommandations

La base de données principale du projet est :

```text
PostgreSQL + pgvector
```

---

# 2. Principes du modèle

Le modèle repose sur quelques principes clés.

## 1 manga = 1 entité canonique

Plusieurs sources peuvent référencer un même manga :

* MyAnimeList
* AniList
* MangaNews

Mais dans la base Mangadvisor :

```text
1 manga = 1 enregistrement canonique
```

Les identifiants des sources sont stockés séparément.

---

## Séparation des sources

Les données brutes provenant des APIs sont stockées dans des tables dédiées.

Cela permet :

* de conserver la traçabilité
* de reconstruire le catalogue si nécessaire

---

## Données enrichies

La table `manga` représente la version consolidée utilisée par l’API.

---

# 3. Diagramme simplifié

```text
sources
   │
   │
   ▼
source_manga
   │
   │ reconciliation
   ▼
manga
   │
   ├── manga_genres
   │
   ├── manga_tags
   │
   ├── manga_relations
   │
   └── manga_embeddings
```

---

# 4. Table `sources`

Liste des sources de données utilisées.

```text
sources
```

| colonne    | type      | description        |
| ---------- | --------- | ------------------ |
| id         | serial    | identifiant source |
| name       | text      | nom de la source   |
| base_url   | text      | url source         |
| created_at | timestamp | création           |

---

# 5. Table `source_manga`

Stocke les données brutes provenant des APIs.

```text
source_manga
```

| colonne         | type      | description       |
| --------------- | --------- | ----------------- |
| id              | serial    | identifiant       |
| source_id       | int       | source            |
| source_manga_id | text      | id dans la source |
| title           | text      | titre             |
| synopsis        | text      | synopsis          |
| score           | numeric   | score             |
| popularity      | int       | popularité        |
| raw_json        | jsonb     | réponse brute API |
| created_at      | timestamp | ingestion         |

---

# 6. Table `manga`

Table centrale du projet.

```text
manga
```

| colonne    | type      | description        |
| ---------- | --------- | ------------------ |
| id         | serial    | id manga           |
| title      | text      | titre principal    |
| title_en   | text      | titre anglais      |
| title_jp   | text      | titre japonais     |
| synopsis   | text      | synopsis           |
| start_year | int       | année début        |
| status     | text      | ongoing / finished |
| volumes    | int       | nombre volumes     |
| chapters   | int       | nombre chapitres   |
| score      | numeric   | score moyen        |
| popularity | int       | popularité         |
| created_at | timestamp | création           |
| updated_at | timestamp | mise à jour        |

---

# 7. Table `genres`

Liste des genres.

```text
genres
```

| colonne | type   |
| ------- | ------ |
| id      | serial |
| name    | text   |

---

# 8. Table `manga_genres`

Relation manga → genres.

```text
manga_genres
```

| colonne  | type |
| -------- | ---- |
| manga_id | int  |
| genre_id | int  |

---

# 9. Table `tags`

Tags descriptifs.

Exemples :

```text
samurai
historical
sports
slice_of_life
```

```text
tags
```

| colonne | type   |
| ------- | ------ |
| id      | serial |
| name    | text   |

---

# 10. Table `manga_tags`

Relation manga → tags.

```text
manga_tags
```

| colonne  | type    |
| -------- | ------- |
| manga_id | int     |
| tag_id   | int     |
| weight   | numeric |

---

# 11. Table `manga_relations`

Relations entre mangas.

Exemples :

```text
prequel
sequel
spin_off
adaptation
```

```text
manga_relations
```

| colonne          | type   |
| ---------------- | ------ |
| id               | serial |
| manga_id         | int    |
| related_manga_id | int    |
| relation_type    | text   |

---

# 12. Table `manga_embeddings`

Vecteurs utilisés pour la recommandation.

```text
manga_embeddings
```

| colonne   | type        |
| --------- | ----------- |
| manga_id  | int         |
| embedding | vector(384) |

Dimension 384 correspond au modèle :

```text
all-MiniLM-L6-v2
```

---

# 13. Similarité vectorielle

Recommandations basées sur la distance cosine.

Exemple :

```sql
SELECT
  m2.id,
  m2.title,
  1 - (e1.embedding <=> e2.embedding) AS similarity
FROM manga_embeddings e1
JOIN manga_embeddings e2
  ON e1.manga_id != e2.manga_id
JOIN manga m2
  ON m2.id = e2.manga_id
WHERE e1.manga_id = 42
ORDER BY similarity DESC
LIMIT 10;
```

---

# 14. Index recommandés

```sql
CREATE INDEX idx_manga_title
ON manga(title);

CREATE INDEX idx_source_manga
ON source_manga(source_id, source_manga_id);

CREATE INDEX idx_manga_embedding
ON manga_embeddings
USING ivfflat (embedding vector_cosine_ops);
```

---

# 15. Intégration Meilisearch

Les champs indexés dans Meilisearch seront :

```text
id
title
genres
tags
score
popularity
```

Objectif :

* recherche rapide
* autocomplétion
* filtres

---

# 16. Pipeline de mise à jour

Le pipeline suit ces étapes :

```text
Extract
   ↓
Normalize
   ↓
Reconcile
   ↓
Enrich
   ↓
Embed
   ↓
Load PostgreSQL
   ↓
Index Meilisearch
```

---

# 17. Évolutions futures

Le modèle pourra évoluer avec :

### profils utilisateurs

```text
users
user_ratings
user_history
```

---

### recommandations personnalisées

```text
user_embeddings
```

---

### suivi lecture

```text
user_manga_progress
```

---

# 18. Résumé

Le modèle Mangadvisor repose sur :

* une table canonique `manga`
* des tables relationnelles pour les métadonnées
* des embeddings vectoriels
* un moteur de recherche externe

Ce modèle permet :

* recherche rapide
* enrichissement progressif
* recommandations intelligentes

---

# Fin du document

 