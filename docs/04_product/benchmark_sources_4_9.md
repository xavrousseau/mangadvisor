# Benchmark historique V1 des fournisseurs mangas sur 50 œuvres

> **Référence historique.** Le menu actif A → 16 redirige désormais vers la V2 (A → 17). Le module Python V1 reste dans le dépôt parce que la V2 importe certaines de ses fonctions.

## Objectif

Comparer Scrinis et MangaUpdates **sans toucher aux 10 000+ mangas actuels**.
Deux sources bibliographiques distinctes (BnF et Sudoc) restent disponibles
pour confirmer ultérieurement les identifiants français : comparer directement
des ISBN sur des lignes d'inventaire qui n'en portent aucun serait trompeur.

## Sources effectivement interrogées

- **Scrinis** : https://scrin.is/fr/api (endpoint \`GET /api/v1/search\`).
  Le service est en bêta, limite publiquement les accès sans clé à **15/min**,
  autorise la réutilisation par API dans ses conditions (27/09/2026).
  https://scrin.is/fr/conditions
- **MangaUpdates** : https://api.mangaupdates.com/v1
  (endpoint public \`POST /series/search\`). Son API indique qu'il faut
  attribuer la source, espacer les appels et mettre en cache.
  Le code utilise une pause prudente de 2 secondes, sans login ni token.
- **BnF** : les notices candidates déjà chargées par **A → 15** pourront
  alimenter une évaluation ultérieure ISBN/tome/éditeur, mais ne sont pas
  sollicitées par ce benchmark de séries.
- **Sudoc** : le service officiel **isbn2ppn** sert à vérifier des ISBN
  connus, pas à résoudre automatiquement des séries par leur nom.
  https://abes.fr/api-et-web-services/
- **Open Library** : pour de gros volumes, privilégier les fichiers dumps.
  https://openlibrary.org/developers/api

Ce premier benchmark utilise uniquement la recherche : la présence
d'un ISBN, d'un genre ou d'une fiche étendue ne peut être mesurée que si
ces champs figurent dans le **résultat de recherche lui-même**. L'absence
d'un tel champ ne signifie pas qu'il n'existe pas dans la fiche détaillée.

## Utilisation

1. Récupérer la dernière version du dépôt par **mangadvisor.cmd → 3**,
   qui sauvegarde d'abord les données.
2. Démarrer Docker Desktop. Ouvrir **mangadvisor.cmd → A → 16 ou A → 17**. Ces deux entrées exécutent désormais le comparatif V2. Cette page décrit surtout le premier benchmark historique V1 ; pour les étapes actuelles, suivre [le guide V2](benchmark_sources_v2.md).
3. Choisir **50 mangas** (ou un plus petit nombre pour la première exécution).
4. Lire l'échantillon proposé **avant tout appel Internet** :
   - jusqu'à **25 titres en attente de rapprochement** dans la mangathèque,
   - jusqu'à **15 œuvres physiques déjà rapprochées**,
   - compléter avec des mangas populaires jusqu'à 50 titres uniques.
5. Confirmer explicitement pour transmettre **uniquement les titres** des
   œuvres à Scrinis et MangaUpdates. Aucun statut de lecture, note, identifiant
   utilisateur, quantité ni liste complète de ta collection n'est transmis.
6. Les recherches s'effectuent avec 4,5 secondes entre deux requêtes Scrinis
   et 2 secondes entre deux requêtes MangaUpdates, sans contournement de quota.
   Les erreurs 401/403/429 arrêtent les requêtes du fournisseur en cause.
7. Lire les comptes-rendus **CSV et JSON**, conservés exclusivement en local :
   \`data/logs/catalog_sources/\` (ignoré par Git).

Le diagnostic peut durer plusieurs minutes à 50 titres, en raison des
restrictions normales imposées par les fournisseurs.

## Lecture des résultats

- \`SAME_MAL_ID\` : identifiant manga MAL identique, indice d'identité fort.
- \`EXACT_TITLE\` : titre exact en français, anglais ou japonais **mais pas
  une preuve d'identité canonique**.
- \`AMBIGUOUS\` : plusieurs résultats aussi plausibles.
- \`SUGGESTION_ONLY\` : candidats non confirmés.
- \`NO_MATCH\` : aucune fiche utilisable dans la réponse.
- \`UNKNOWN_SCHEMA\` : la réponse API n'est pas au format prévu, **pas**
  une absence réelle de manga.
- \`UNAVAILABLE\`, \`HTTP_ERROR\`, \`NETWORK_ERROR\` : fournisseur indisponible ;
  les chiffres de couverture doivent exclure ces erreurs du dénominateur.

Ce benchmark ne fait **aucune** insertion, modification ou suppression en
PostgreSQL. Il ne relie **aucun ISBN, édition Deluxe/Pastel, ni livre physique**.

## Critère de décision

Confronter la couverture observée, l'identité MAL réellement vérifiée,
la qualité des titres FR, les informations de genre et la fiabilité du
service aux **droits de réutilisation**. Scrinis est hébergé par un
particulier et peut être indisponible ; MangaUpdates n'est pas une garantie
d'édition française. Ne pas automatiser un moissonnage massif avant
confirmation des conditions et validation des taux d'erreur sur les 50 titres.

En second chantier, ajouter des tests d'ISBN connus contre **BnF/Sudoc**,
puis des recherches ponctuelles de fiches complètes Scrinis/MangaUpdates,
toujours sans écriture sur la collection.
