# Audit de nettoyage — apps/api et apps/web (21 octobre 2026)

> Audit statique du code de la branche `cleanup/pipelines-2026-10-21`. Aucune modification de la base personnelle, aucun démontage de fonctionnalité utilisateur. Les tests GitHub sur ce lot sont à confirmer sur le dernier commit.

## Synthèse

- `apps/api/app/main.py` : environ **3 860 lignes / 127 Ko**, application FastAPI et logique catalogue, bibliothèque, import CSV historique, recommandations, couvertures et initialisation. **Conserver, découper progressivement par domaine à contrat constant**, uniquement avec tests ciblés.
- `apps/web/assets/app.js` : environ **1 489 lignes / 86 Ko**, routage client, état global, orchestration réseau, navigation, bibliothèque, conseiller et formulaire d'import. **Conserver, extraire des fonctions par écran à comportement identique**, uniquement avec tests JS.
- Les modules spécialisés déjà présents évitent les véritables doublons de code : plusieurs opérations voisines correspondent à **des données différentes** (œuvre manga, déclaration de tomes, livre ISBN identifié, lecture).
- `apps/web/index.html` et `apps/web/nginx.conf` : fichiers de démarrage actifs ; **conserver**. Nginx réinterroge le DNS interne Docker, nécessaire après recréation du conteneur API.

## Inventaire du périmètre API

| Module / groupe | Rôle vérifié dans le code | Décision |
|---|---|---|
| `main.py` | FastAPI, routes catalogue, bibliothèque, recommandations et imports historiques | **À refactoriser**, ne pas supprimer |
| `advisor.py`, `advisor_ai.py`, `advisor_editions.py`, `advisor_feedback.py`, `advisor_quality.py` | Conseiller guidé/IA locale optionnelle, éditions candidates, retours et notation | **Conserver**, usages distincts |
| `mood_discovery.py`, `narrative_evidence.py`, `recommendation_explanations.py`, `recommendation_quality.py`, `library_seed_selection.py` | Critères de découverte, explications, qualité et sélection des mangas sources | **Conserver**, jeux de tests dédiés |
| `inventory_import.py`, `inventory_resolution.py` | Déclarations physiques, import avec aperçu et rapprochement manuel des ambiguïtés | **Conserver**, éviter toute association forcée |
| `collection.py`, `collection_bulk.py`, `collection_scan.py` | Livres ISBN vérifiés, lot CSV, caméra/scan, suivi par volume | **Conserver** ; ne pas confondre avec le CSV bibliothèque |
| `edition_discovery.py`, `edition_enrichment.py`, `library_enrichment.py`, `mangadex_discovery.py` | Recherche et enrichissement contrôlés ; preuves et candidats | **Conserver**, vérifier les dépendances API |
| `bnf_batch.py`, `wikidata_enrichment.py`, `multilingual_aliases.py`, `localization.py` | Candidats BnF, labels Wikidata, alias sourcés, traduction | **Conserver** |
| `requirements.txt` | FastAPI, Uvicorn, psycopg pour l'image API | **Conserver** ; versions à figer plus tard |

Cette liste décrit les groupes métier, sans prétendre que chaque branche d'exécution est totalement couverte.

## Inventaire du périmètre Web

| Module / groupe | Rôle | Décision |
|---|---|---|
| `assets/app.js` | Contrôleur central, navigation, requêtes, état et événements | **Refactoriser progressivement**, pas de réécriture complète |
| `assets/i18n.js`, `appearance.js`, `appearance.css`, `app.css` | Internationalisation FR/EN et thème | **Conserver** |
| `home.js`, `mood-view.js`, `advisor-view.js`, `advisor-editions.js`, `explain.js` | Accueil et recommandations avec explications | **Conserver** |
| `collection-view.js`, `physical-inventory-view.js`, `inventory-resolution-view.js`, `library-display.js` | Affichage bibliothèque, éditions et déclarations physiques | **Conserver**, responsabilités distinctes |
| `bulk-import-view.js`, `unknown-isbn-view.js`, `isbn-scanner.js` | CSV, résolution ISBN, scanner mobile | **Conserver** |
| `bibliography-view.js`, `bnf-candidates-view.js`, `wikidata-view.js`, `enrichment-view.js` | Sources bibliographiques et vérification | **Conserver** |
| `index.html`, `nginx.conf` | Entrée de l'interface et proxy API | **Conserver** |

## Principaux risques à traiter avant nettoyage profond

1. **Imports distincts** : `POST /library/import/csv` dans `main.py`, les déclarations `/inventory/*` et les livres `/collection/import/*` répondent à des modèles différents. Ne jamais les fusionner ni les remplacer sans conversion explicite, prévisualisation et tests de migration.
2. **Volumes physiques** : maintenir la distinction entre le nombre de volumes déclarés et les ISBN effectivement vérifiés. Ne jamais inventer une édition ou un numéro de tome.
3. **États d'interface** : `app.js` orchestre de multiples écrans et interactions. Toute extraction doit conserver les événements, les routes, les paramètres, les appels API et le chargement dynamique des couvertures.
4. **Liens Voir la fiche** : l'interface produit des liens `/manga/{id}` et Nginx utilise la navigation SPA. Vérifier les clics navigateur et le retour direct après rechargement de la page, pas seulement l'existence du texte.
5. **Données externes** : titres FR, ISBN, auteurs et labels ne doivent pas être automatiquement confirmés à partir d'une simple ressemblance.
6. **Taille des fichiers** : les deux contrôleurs centraux constituent une dette de maintenance mais leur découpage augmente momentanément le nombre de fichiers ; privilégier une meilleure séparation des responsabilités plutôt qu'un nombre minimal de fichiers.

## Plan de simplification proposé

**Passe A — sécurité des contrats (avant extraction)**

- Conserver les tests Python existants (matching CSV non ambigu, import physique multiéditions, exclusion des œuvres possédées, recommandations).
- Conserver les tests JS Web sur les cartes, les fiches, les bibliographies, les ISBN et le conseiller.
- Faire passer les tests Docker navigateur et contrôler le lien `Voir la fiche`.

**Passe B — extractions à faible risque**

- Déplacer, par petits groupes, les fonctions de formatage/rendu du contrôleur Web vers des modules testables purs.
- Extraire les fonctions d'import CSV historique et de validation hors de `main.py`, en conservant les routes et les modèles HTTP.
- Faire suivre chaque extraction des suites Python, JS et intégration Docker.

**Passe C — rationalisation**

- Comparer les contrats des trois imports, sans fusionner leur stockage.
- Éliminer les vrais doublons confirmés par référence d'appel et résultats de test, pas sur la base d'un nom.
- Mettre à jour la documentation des fichiers actifs et retirer la documentation purement historique non référencée dans une passe distincte.

## Décision

**GO pour une refactorisation contrôlée ; NO-GO pour la suppression directe de modules `apps/api/` ou `apps/web/`.** À ce stade aucun de ces modules n'est démontré mort. Les derniers commits restent sur une PR brouillon, non fusionnée dans `main`.
