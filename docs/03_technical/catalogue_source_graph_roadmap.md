# Mangadvisor — Refonte du référentiel bibliographique (sources publiques)

## Ce qui est avéré dans l'export du 23 octobre 2026

La base contient **85 776 œuvres** dans `manga`, **85 776 documents Jikan bruts** et
**228 010 alias**. Parmi ces alias, **113 354** sont de simples
`title_synonyms` sans langue garantie et **114 539** sont des titres typés
FR/EN/JA par l'export MAL. Seulement **160 œuvres** disposent d'un alias
français explicite, et les tables d'éditions françaises sont **vides**.

Un recalcul effectué sur la base transmise (liaison exacte alias → titres
canoniques de *différentes* œuvres) donne **5 416 lignes d'alias à vérifier**,
dont **4 056 synonymes non typés** et **1 355 titres typés**. Les 8 151
relations « alias → œuvre tierce » signalées dans l'audit sont un *autre*
dénominateur : plusieurs œuvres peuvent porter un même titre. Il ne faut
pas présenter 8 151 comme 8 151 lignes à effacer.

Exemples démontrés dans les sources brutes : `Radiant` dans les synonymes
d'`Ikujitsu`, et `Fairy Tail` dans les synonymes de
`Bishoujo Hatsu Shibori`. **Ce n'est pas une identité d'œuvre fiable.**

## Architecture adoptée

1. **Source Jikan** `jikan_manga_source.raw_json` : archive intouchable
   des 85 776 fiches, incrémentée par les pipelines existants.
2. **Référentiel `catalogue_work`** : identifiant interne indépendant
   des fournisseurs. Les 85 776 œuvres actuelles conservent leur
   `legacy_manga_id`. Une œuvre française sans MAL dispose du même
   statut dans ce nouveau référentiel, avec un `origin_source` et un
   `origin_id` vérifiables, sans inventer de numéro MAL.
3. **Titres `catalogue_title_claim`** : langue, source, identifiant source,
   texte et nature (titre canonique / typé / synonyme non vérifié /
   titre externe). Un `title_synonyms` de Jikan est `DISCOVERY_ONLY`,
   ou `COLLISION_REVIEW` s'il correspond à la fiche principale d'une
   autre œuvre. Aucun alias Jikan non typé n'est une confirmation d'identité.
4. **Identifiants `catalogue_work_identifier`** : paires source-ID
   issues de MAL, AniList, Kitsu, MangaDex et Wikidata. Des ID externes
   déclarés par deux œuvres différentes deviennent `COLLISION_REVIEW`.
   Les déclarations externes sont `SOURCE_CLAIM`, pas des liens
   automatiquement vérifiés.
5. **Relations `catalogue_work_relation`** : suite, adaptation,
   histoire annexe… conservées avec les identifiants originaux, et
   **sans fusionner** les œuvres. Une adaptation anime n'est pas un manga.
6. **Bibliographie française** : BnF/éditeurs/Scrinis restent les sources
   d'édition, volume et ISBN. Elles ne certifient ni la correspondance
   entre œuvres ni la possession d'un tome. Un livre d'une œuvre dérivée
   ne doit pas être affecté à la série parente.

Le nouveau référentiel conserve l'ancien `manga` pour compatibilité :
**il ne supprime ni ne réécrit les tables existantes, ne modifie pas les
associations possédées et ne supprime aucun synonyme brut**.

## Téléchargement et rapprochement multi-API : règles d'import

| Fournisseur | Télécharger | Lien de confiance | Français/édition |
| --- | --- | --- | --- |
| Jikan/Tenrai | Catalogue brut + incréments | ID MAL = source, `title_synonyms` seulement découverte | FR si `type=French` explicite, sinon langue inconnue |
| AniList | Groupes jusqu'à 8 ID MAL | `idMal` renvoyé égale au MAL demandé, auteur/relations à contrôler | EN/JA, jamais inventer FR |
| Kitsu | Mappings `myanimelist/manga`, `anilist/manga` | même ID MAL, aucun mix anime/manga | identifiants croisés, pas un ISBN |
| MangaDex | Titre + `links.mal` exact | ne pas rapprocher sur le titre seul | `altTitles.fr` sourcés, pas éditions françaises |
| Wikidata | P4087/QID + libellés | identifiant MAL explicite et unique | libellé `fr` sourcé, pas édition |
| BnF/éditeur/Scrinis | Notices bibliographiques | ISBN-13, œuvre, éditeur, collection, tome | base des éditions françaises, **séparée du catalogue d'œuvres** |

Les connecteurs AniList, Kitsu, MangaDex et Wikidata existants sont
réutilisés par le module `rebuild_catalogue_source_graph.py`. Chaque
réponse d'API est **explicitement déclenchée**, limitée à huit ID MAL,
liée par identifiant exact et stockée sans fusion ni attribution ISBN.
Un fournisseur indisponible n'est pas assimilé à un résultat vide.
Aucun téléchargement multiréférentiel exhaustif des 85k n'est revendiqué :
il faudra ensuite un collecteur paginé, avec reprise, cache,
contrôle des quotas et mesure de couverture réelle.

## Utilisation Windows (sans effacer la base)

Après une **mise à jour de l'application** puis son démarrage :
`mangadvisor.cmd` → **A — Outils avancés** → **26 — Reconstruire
le référentiel public des œuvres**.

Cette étape reconstruit l'identité de toutes les fiches Jikan et
reclasse les alias **à partir des tables déjà téléchargées**, sans
faire d'appel Internet et sans attribuer un tome possédé. Elle peut
être relancée : `INSERT ... ON CONFLICT` protège l'idempotence.

Pour une investigation ciblée en lecture seule :
`docker exec mangadvisor_api python -m pipelines.engine.scripts.rebuild_catalogue_source_graph --report-only`.

Pour enrichir **explicitement** des ID connus, après reconstruction :
`docker exec mangadvisor_api python -m pipelines.engine.scripts.rebuild_catalogue_source_graph --apply --mal-ids 145863,598 --providers anilist,kitsu,mangadex,wikidata`.

La requête réseau ne se produit que lorsque `--providers` est demandé.
Cette commande reste un **pilote borné**, pas le téléchargement massif
qui reste à industrialiser.

## Enrichissement FR conservateur et droits des sources

La reconstruction A → 26 recharge maintenant également les libellés français
de `manga_wikidata_fact.label_fr` (lien P4087/MAL contrôlé) et les
titres `manga_scrinis_fr_fact.title_fr` pour les œuvres dont l'identité
MAL et les indices bibliographiques sont cohérents. Elle **ne crée aucun
ISBN ni édition possédée**, et marque les libellés qui recoupent le
titre principal d'une autre œuvre comme `COLLISION_REVIEW`.

Le bilan affiche les nombres `works_with_sourced_french_titles`,
`wikidata_french_titles` et `scrinis_french_titles`.
Ces nombres mesurent la couverture des titres sourcés, pas les éditions
françaises commercialisées.

**Restriction majeure :** les conditions officielles AniList interdisent
la collecte en masse de ses données et limitent leur utilisation dans
les applications de suivi/listes de mangas concurrentes.
**Ne pas lancer d'enrichissement massif AniList** sans autorisation écrite
du fournisseur. La limitation technique à 30 requêtes/minute ne suffit
pas à rendre cette collecte autorisée.

Source : https://docs.anilist.co/guide/terms-of-use

## Validation obligatoire avant toute correction finale de base

- tests Python : typage des sources, absence de jointure textuelle,
  synonymes discovery-only, identités non-MAL, liens de sources,
  relations distinctes, collisions;
- PostgreSQL CI : reconstruction effective et répétable, collision
  canonique, création d'une œuvre non-MAL, identifiant AniList lié
  exactement à MAL; compte des œuvres Jikan et collection inchangés;
- sur la vraie base : rapport nombre d'œuvres, claims, conflits, liens
  internationaux, titres `fr`; suivi à chaque lot d'enrichissement;
- seulement ensuite : établir un **jeu de référence** et mesurer
  précision, rappel, couverture, édition/ISBN séparément.

Le taux de 95 % de rapprochements bibliographiques **n'est pas
démontré par cette refonte structurante**. Une reconstruction technique
réussie n'est pas une certification de toutes les associations.

## Étapes supplémentaires nécessaires à la V1

1. Indexer les titres et identifiants issus du **nouveau graphe
   qualifié**, plus les œuvres hors MAL, dans la recherche publique.
2. Automatiser les collectes AniList/Kitsu/MangaDex/Wikidata en lots
   reprenables, avec quotas, checkpoint et gestion des absences
   réelles de données.
3. Construire le référentiel français **œuvre → édition → volume/ISBN**
   à partir de preuves BnF/éditeurs/Scrinis, sans mélanger les dérivés.
4. Mettre les anciens mauvais liens en quarantaine réversible
   après validation sur un clone PostgreSQL restauré, avant toute
   modification des 85 776 fiches d'origine.
