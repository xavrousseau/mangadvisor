Super, voici une version **README.md** claire et opérationnelle pour ton repo **Mangadvisor**.
C’est un résumé du **ARCHITECTURE.md**, pensé pour les contributeurs (ou toi dans 3 mois).

---

# 📚 Mangadvisor

Mangadvisor est une application de **recommandation de mangas** basée sur des **embeddings multilingues** et une **explication transparente**.

> *“Proche de Vagabond via `samouraï`, `historique`, `contemplatif` + similarité 0,86”*

---

## 🚀 Objectifs

* Recommandations utiles, pas de listes génériques.
* Explications courtes et factuelles (tags + score + phrase).
* MVP reproductible, simple, FR-friendly.

---

## 🏗️ Stack v0.1 (Foundation Baseline)

* **Backend** : FastAPI + Pydantic v2
* **DB** : PostgreSQL 15 + extension `pgvector`
* **Embeddings** : modèle multilingue (cloud ou local via Ollama)
* **UI** : NiceGUI (recherche + pills moods + résultats)
* **Infra** : Docker Compose (Windows/Linux friendly)

---

## 🔑 Fonctionnalités MVP

* **Ingestion Jikan (MyAnimeList)** : ≥200 œuvres en base.
* **Embeddings pgvector** : similarité cosine.
* **API** :

  * `/search?q=...` → recherche titre
  * `/similar/{id}` → voisins les plus proches
  * `/explain` → tags + score + micro-phrase
* **UI** :

  * Recherche simple
  * Filtres “moods” (feel-good, contemplatif, sombre, sport…)
  * Explications visibles (tags, score, phrase ≤160 caractères)

---

## 🌍 Traduction & multilingue

* Titres : priorité FR > EN > JP romaji > JP kanji.
* Synopsis : EN original + version FR auto (Argos/LibreTranslate).
* Tags : pivot EN → affichage FR via dictionnaire fixe (`slice of life → tranche de vie`).
* UI : FR par défaut, EN optionnel.

---

## 💬 Explication (format standard)

* **Tags communs** (≤3)
* **Score** (cosine, arrondi à 2 décimales, code couleur)
* **Phrase** (≤160 caractères, factuelle)

**Exemple** :

* Chips : `[samouraï] [historique] [contemplatif]`
* Score : `0,86` (vert)
* Phrase : *“Proche de Vagabond par son ambiance samouraï et son ton contemplatif.”*

---

## ✅ Definition of Done (v0.1)

* Ingestion Jikan : ≥200 œuvres, 0 doublon, golden set présent (Vagabond, Berserk…).
* Embeddings : 100% des synopsis vectorisés, k-NN cohérent, requêtes <300 ms.
* API : endpoints fonctionnels, Swagger FR, P95 <500 ms.
* UI : recherche → résultats explicables, navigation clavier, FR/EN switch.

---

## 🚧 Non-objectifs v0.1

* Authentification (JWT/social)
* ANN (HNSW, IVFFlat)
* Scraping MangaNews
* Personnalisation par profil
* LLM génératif libre (uniquement pipeline explicatif)

---

## 📊 Suivi qualité

* **Logs ingestion** : œuvres lues, insérées, ignorées.
* **Logs embeddings** : % générés, hash payload.
* **Métriques API** : latence, taux erreurs.
* **Tests golden set** : cohérence recos sur 12 mangas de référence.

---

## ▶️ Démarrage rapide (bientôt)

```bash
# Lancer la stack
docker compose up -d

# Vérifier API
http://localhost:8000/docs

# Vérifier UI
http://localhost:8080
```

---

## 📌 Roadmap

* **v0.1** : Jikan + embeddings + API + UI minimaliste ✅
* **v0.2** : ajout AniList, Meilisearch (recherche typo-tolérante), import bibliothèques, JWT.
* **v0.3** : scraping MangaNews, explications enrichies, profils utilisateurs.

---

👉 **Mangadvisor** : un moteur de recommandation de mangas simple, multilingue et explicable.

---
 