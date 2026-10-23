# Décision d'architecture — Mangadvisor, catalogue V2 (23 octobre 2026)

## Problème constaté, à ne pas contourner

Le catalogue actuellement utilisé par l'application est principalement construit
à partir de Jikan/MyAnimeList (85 776 fiches, 228 010 alias). Un identifiant
MyAnimeList correspond à une fiche de cette source, **pas forcément à
l'identité stable d'une œuvre bibliographique** et encore moins à une
édition française. Certains `title_synonyms` sont des noms de chapitres ou
de récits contenus dans un recueil (ex. collisions Radiant et Fairy Tail).

La première reconstruction de `catalogue_work` est une **table de
staging transitoire** : l'application continue à interroger la table
`manga`, `manga_title_alias` et l'ancien index Meilisearch. Il ne faut
pas appeler ce dispositif une base propre ou migrée.

### Décision

**Reconstruire une nouvelle base bibliographique isolée, V2, depuis les
données brutes vérifiables, puis basculer l'application après recette.**
Ne plus enrichir à l'aveugle la table `manga` en place.

Il n'existe pas d'identifiant fournisseur couvrant simultanément toutes
les œuvres japonaises, les créations françaises et toutes les éditions
physiques. Mangadvisor attribue donc un identifiant **interne**
`work_id` non dérivé des titres ni d'un fournisseur.

## Modèle cible

- `work (work_id PK, type, canonical_title, status)` : une œuvre, série
  ou one-shot. Une suite ou un spin-off est une autre œuvre, reliée
  explicitement à sa parente, et non fusionnée.
- `external_identifier (provider, media_type, external_id, work_id,
  evidence_url, status)` : identité fournisseur scoped. Pour un
  identifiant `CONFIRMED`, une paire
  `(provider, media_type, external_id)` ne peut référencer qu'une
  seule œuvre. Des claims contradictoires vont en quarantaine.
- `work_title (work_id, language, title, kind, source_id, evidence_status)` :
  le titre FR est un fait de source, pas une traduction fabriquée.
  `title_synonyms` Jikan non typés vont dans `DISCOVERY_ONLY`, jamais
  dans les clés de jointure ni l'index des alias confirmés.
- `work_relation (source_work_id, target_work_id, relation_type, source)` :
  `SEQUEL`, `SPIN_OFF`, `ADAPTATION`, etc., sans équivalence par défaut.
- `edition (edition_id PK, work_id FK, publisher, collection, market,
  format, publication_period, source)` : par exemple les éditions
  françaises *Dragon Ball* pastel et Deluxe ne partagent PAS `edition_id`.
- `publication (publication_id PK, edition_id FK, volume_number,
  isbn13 UNIQUE NULLABLE, printed_title, publication_date, source)` :
  ISBN = identifiant de publication spécifique, pas celui de la série.
  Deux ouvrages qui revendiquent un même ISBN sont mis en revue,
  jamais attachés automatiquement aux deux séries.
- `source_snapshot` et `review_queue` : provenance/version/horodatage
  de chaque collecte et arbitrages manuels audités.
- `user_*` reste **hors de la V2 expérimentale**. La migration des
  associations personnelles attend un tableau de correspondance
  `legacy_manga_id → work_id` confirmé, jamais un match approximatif.

## Sources et responsabilité

| Domaine | Point de départ | Règle |
|---|---|---|
| Catalogue manga international | Jikan/MAL, snapshot existant | Import brute + identifiant MAL source, pas vérité universelle. Vérifier les conditions d'exploitation des données. |
| Correspondances externes | Wikidata P4087, références croisées explicites | Identifiant exact + type manga, preuve et contradictions ; jamais titre seul. |
| Titres français | Wikidata étiqueté FR, BnF, éditeurs et sources réutilisables autorisées | Vérifier l'œuvre avant d'ajouter un titre. |
| Éditions, tomes et ISBN français | BnF + métadonnées éditeur/autres sources sous conditions vérifiées | Validation de l'édition, de la collection et du tome ; ISBN de la publication. |
| AniList | Pas de collecte de masse dans Mangadvisor | Conditions officielles restrictives pour collecte en masse et trackers concurrents : demander une autorisation explicite si usage voulu. |
| Autres API (Kitsu, MangaDex...) | Évaluer conditions, qualité et identifiants disponibles | Une API de plus n'est pas automatiquement une preuve supplémentaire indépendante. |

## Plan d'exécution — par lots vérifiables, pas par nouveaux boutons

1. **Préparer une base de travail V2 isolée** dans Docker, sous un
   nom et un stockage distincts de la production. Importer uniquement
   les archives publiques du catalogue et tester la restauration.
   Ne jamais lancer `down -v` ni écraser les volumes actuels.
2. **Reconstruire le noyau** à partir des enregistrements sources
   immuables : œuvres locales, identifiants MAL scoped, titres typés,
   auteurs, relations *documentées*, et files de conflits.
   Chaque ligne produite conserve son `source_record_id`.
3. **Importer et vérifier les sources complémentaires autorisées** par
   ID exact ; mettre les doubles identifiants ou synonymes recoupant
   plusieurs œuvres en `REVIEW`. Comparer couverture et erreur avant
   et après chaque source, indépendamment du nombre de lignes ajoutées.
4. **Recréer la bibliographie française séparément** :
   œuvre → édition → tome/publication → ISBN. Vérifier la bonne édition
   pour les séries rééditées et les œuvres dérivées.
5. **Remplacer les lectures applicatives** de
   `manga_title_alias` par des vues/requêtes V2 ne contenant que des
   preuves qualifiées. Réindexer Meilisearch depuis la V2, pas depuis
   l'ancien catalogue douteux.
6. **Bascule réversible** : comparaison catalogue V1/V2,
   validation manuelle des cas difficiles, migration de la mangathèque
   après sauvegarde et contrôle de tous les identifiants, puis
   désactivation du code legacy. Pas de suppression d'archives brutes.

## Critères d'acceptation (à mesurer, pas à déclarer)

- Nombre d'œuvres V2 et répartition `MAL` / `non-MAL`.
- Couverture effective par titres FR **uniques et sourcés**,
  relations qualifiées et éditions françaises/ISBN vérifiés.
- Précision des liaisons identitaires sur un échantillon de référence
  indépendant, incluant séries/one-shots/anthologies/spin-offs ;
  objectif de 95% **sur les associations confirmées**, avec rappel et
  taux de cas résolus publiés séparément.
- Des tests adversariaux obligatoires : *Radiant* ≠ *Ikujitsu* ;
  *Fairy Tail* ≠ *Bishoujo Hatsu Shibori* ; *Tokyo Ghoul* ≠
  *Tokyo Ghoul:re* ; *Dragon Ball* pastel ≠ Deluxe ;
  *Adieu Eri* = œuvre *Sayonara Eri* seulement avec référence vérifiée.
- Aucun faux ajout à l'inventaire ni aux ISBN possédés ;
  aucun ouvrage d'une série dérivée relié d'office à sa parente.
- Comparaison des écrans de recherche V1/V2 ; aucun basculement
  tant que la V2 n'a pas fait mieux sur les cas validés.

## Nettoyage de mangadvisor.cmd

Le lanceur ne doit plus être un historique de prototypes. Le menu de
gestion présente seulement **Catalogue**, **Ma bibliothèque**,
**Fonctions facultatives** et **Entretien**. Les commandes de laboratoire
restent accessibles directement, par exemple
`mangadvisor.cmd catalogue-source-graph`, sans apparaître dans
les parcours courants.

**Statut de ce document : décision et plan de reconstruction. La base V2
n'est PAS créée par la simple simplification du menu.**
