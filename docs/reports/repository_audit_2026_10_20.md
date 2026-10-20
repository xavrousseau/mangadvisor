# Mangadvisor — audit transversal du dépôt (20 octobre 2026)

## Référence et périmètre
- Référence étudiée : `main`, commit `b4e60afd43f9945e6db61489aa782f75efc9e202`.
- Inventaire : 246 fichiers Git suivis, environ 1,68 Mo. Inspection approfondie des points d'entrée Windows, Docker, schéma SQL, ETL Tenrai/Jikan, API, import physique, conseiller, front Web, CI et documents d'architecture.
- Le dépôt a été lu via GitHub. Les tests ont été réalisés dans GitHub Actions sur jeux synthétiques et environnements jetables ; ni le PC Windows personnel, ni les volumes PostgreSQL privés, ni la vraie mangathèque n'ont été modifiés.
- PR corrective isolée : https://github.com/xavrousseau/mangadvisor/pull/58. **Brouillon, non fusionné dans `main`.**

## Constats critiques / élevés — ordre de traitement

| ID | Gravité | Fichiers / éléments | Fait technique vérifié | Action / état |
|---|---|---|---|---|
| A01 | P0, bloquant | `mangadvisor.cmd` (choix 1–29 et commandes directes) | Le `& goto menu` / `& goto :eof` placé après un `if` monoligne est exécuté hors du contrôle conditionnel ; les choix suivants ne sont pas atteints correctement. | 51 branches corrigées dans PR #58 ; tests Windows exécutant réellement le batch ajoutés. |
| A02 | P1, élevé | `load_jikan_to_postgres.py` | Absence de fichier JSON et zéro notice valide renvoyaient `0` (succès) ; un catalogue ancien en base peut masquer le chargement raté. | Codes d'erreur corrigés + tests dans PR #58. |
| A03 | P1, élevé | `load_jikan_recommendations_to_postgres.py` | Aucun fichier ou aucune relation valide pouvait produire un succès avec `--reset` inactif, malgré une phase d'alimentation improductive. | Codes d'erreur corrigés + tests dans PR #58. |
| A04 | P1, élevé | `extract_jikan.py` | Un fichier SEARCH/TOP déjà sur disque était réutilisé sans vérifier son origine Tenrai/Jikan : risque de données anciennes présentées comme nouvelles. | Contrôle source/cache et retéléchargement si provenance invalide ajoutés dans PR #58. |
| A05 | P1, élevé | `inventory_import.py`, `main.py`, `advisor.py`, `mood_discovery.py` | Possession déclarée et statut de bibliothèque sont des tables distinctes. Supprimer la ligne `user_manga_library` laisse la déclaration physique et certains moteurs de recommandation n'excluent plus l'œuvre malgré sa possession. | Non corrigé. Définir un invariant, couvrir les trois chemins de recommandation et ajouter un test PostgreSQL avant recette. |
| A07 | P1, élevé | `main.py : find_manga_for_import` | L'ancien import CSV choisissait arbitrairement le premier manga trouvé via `ILIKE '%titre%'` et `LIMIT 1`, même si plusieurs œuvres correspondaient. Risque d'association silencieuse à la mauvaise série. | Recherche exacte (titre/alias) **et unique** seulement, ambiguïtés non importées + tests ajoutés dans PR #58. |
| A06 | P1, élevé | `control-center.ps1` | Le diagnostic post-ingestion vérifie le nombre total de lignes mais pas systématiquement que l'exécution courante en a réellement chargé de nouvelles ; un état antérieur peut masquer une étape interrompue/partiellement invalide. | Atténué par A02/A03 ; ajouter ensuite bilan par exécution, compteur/horodatage et décision échec partiel. |

## Cohérence, duplications et dette technique

| ID | Importance | Analyse | Recommandation |
|---|---|---|---|
| C01 | Moyenne | `extract_jikan.py` écrivait par défaut deux copies d'une même page SEARCH (`search/search_page_N.json` et `manga_page_N.json`) ; seule la variante SEARCH/TOP est utilisée par le parcours normal. | Option `--no-legacy-search-copy` ajoutée au lanceur dans PR #58 ; conserver la lecture historique explicite en compatibilité. |
| C02 | Moyenne | Même logique de requêtes HTTP, backoff 429 et retry réimplémentée dans `extract_jikan.py` et `extract_jikan_recommendations.py`. | Un client fournisseur partagé avec tests de quota/erreur. |
| C03 | Moyenne | Meilisearch est démarré et déclaré comme dépendance requise par Docker, mais aucun consommateur actif `MEILI_HOST` n'a été identifié hors Compose. | Déclarer ce service comme non branché ; évaluer retrait ou profil facultatif *après* tests, sans effacer son volume. |
| C04 | Moyenne | `EMBEDDING_MODEL`, `ENABLE_OLLAMA` et autres clés historiques existent dans `.env.example` / Docker tandis que l'IA utilisateur est contrôlée via `OLLAMA_ENABLED`. | Supprimer les paramètres morts après inventaire d'utilisation ; éviter de confondre recherche sémantique planifiée et fonctionnelle. |
| C05 | Moyenne | `apps/ui` (ancien prototype Streamlit) subsiste derrière un overlay de développement et ses dépendances/tests alors que `apps/web` est le seul site normal. | Comparer fonctionnalités migrées puis archiver hors chemin de production et documenter la décision. |
| C06 | Moyenne | `apps/api/app/main.py` contient environ 3 710 lignes, `apps/web/assets/app.js` environ 1 347 lignes. La logique domaine, SQL, présentation et navigation restent très centralisées. | Découper par domaine à comportement constant avec couverture non-régression avant refonte. |
| C07 | Moyenne | Trois imports différents coexistent : catalogue bibliothèque `POST /library/import/csv`, inventaire physique `/inventory/*`, livres par ISBN `/collection/import/*`. | Les trois formats ne sont pas des doublons stricts ; clarifier leur usage et unifier l'entrée utilisateur/explication, pas fusionner les données sans modèle. |
| C08 | Moyenne | Import inventaire physique limité à 250 lignes / 110 Ko ; le lot ISBN a sa propre limite. | Vérifier la taille réelle de l'export ; prévoir découpage contrôlé et rapport global si nécessaire. |
| C09 | Moyenne | L'API annonçait `version='4.4.0'` alors que le produit est en version 4.7 ; `pyproject.toml` contient encore un ancien numéro V0.x. | API mise en cohérence dans PR #58 ; définir une source unique pour les versions et corriger le packaging ensuite. |
| C10 | Moyenne | Dépendances Python non épinglées ; bases d'images Docker et composants peuvent évoluer entre installations. | Geler versions/contraintes reproductibles, mettre à jour en CI de façon contrôlée. |
| C11 | Qualité fonctionnelle | Mise à jour SQL additive des genres et thèmes ; les tags retirés côté fournisseur demeurent, faute de provenance. | Ajouter provenance par association et stratégie de désactivation non destructive ; vérifier l'effet sur recommandations. |
| C12 | Qualité documentaire | Scripts Jikan historiques encore nommés Jikan malgré migration Tenrai, docs V1 distinctes d'éléments réellement actifs (Meilisearch/embeddings). | Marquer l'historique, consolider documentation d'architecture actuelle et renommage progressif avec compatibilité. |
| C13 | Tests / fiabilité | Un essai d'intégration Docker a échoué sur `ConnectionResetError` en interrogeant Nginx immédiatement après le démarrage ; le contrôle ne réessayait pas avant la recréation API, contrairement au contrôle après. | Ajouter des tentatives bornées avant test (PR #58), garder l'échec si le proxy demeure indisponible. |

## Points positifs vérifiés
- PostgreSQL/collection est conservateur : mises à jour canoniques SQL par `ON CONFLICT` sans `TRUNCATE`; sauvegarde `pg_dump` et restauration de vérification isolée.
- L'inventaire de plusieurs éditions physiques se fait sans inventer ISBN, notes ou tomes lus, avec entrées non rapprochées conservées séparément.
- Docker stable utilise une seule interface Web utilisateur sur `UI_PORT`, Nginx proxy vers FastAPI, Streamlit historique isolé au profil dev.
- Les recommandations de la 4.7 différencient explicitement simple possession et préférences attestées ; des tests associés existent.
- Le nouveau test batch ajouté en PR #58 couvre un cas que le contrôle précédent n'exécutait pas (il ne vérifiait que la présence des chaînes de menu).
- Les fichiers identiques par hash relevés dans le dépôt sont seulement des `__init__.py` vides ; les véritables doublons recherchés sont avant tout **fonctionnels**, pas des copies de fichiers.

## Couverture de validation et critères de sortie
1. Tous les contrôles GitHub Actions de PR #58 **verts au dernier commit** : Python+JS, Windows 5.1 avec batch exécuté, Docker et intégration SQL synthétique. Ce critère pourra être coché après vérification du dernier SHA.
2. Résoudre A05 avec tests de toutes les recommandations après suppression volontaire d'un statut alors qu'une déclaration physique existe.
3. Définir la politique pour les entrées privées en attente, les éditions multiples et les séries ambigües ; préserver l'idempotence et l'absence d'ISBN inventé.
4. Exécuter l'option 22 puis 27 sur PC personnel avec un réel réseau Tenrai ; contrôler un rechargement incrémental et un arrêt propre si fournisseur indisponible.
5. Valider aperçu CSV, import réel seulement après sauvegarde, vérification des éditions (ex. Dragon Ball Pastel/Deluxe), reprise après redémarrage et restauration **isolée**.
6. Vérifier physiquement sur PC navigateur desktop/mobile : fiche manga, liens `Voir la fiche`, couverture, recherche, bibliothèque, conseiller et exclusions des titres déjà possédés.
7. Avant refonte structurelle : gel des dépendances, clarification services inutilisés et documentation actuelle. Ne jamais considérer que CI synthétique certifie le résultat avec la mangathèque privée.

## Décision de validation
**GO conditionnel sur les corrections ciblées / NO-GO pour la recette finale.**
L'architecture est substantielle et le code a des protections sérieuses, mais les défauts A01–A07 et l'absence de test du poste personnel interdisent de déclarer le produit entièrement propre et validé. Aucun effacement de données n'est nécessaire pour réaliser ces corrections.

Fin du rapport.