# Catalogue MAL/Jikan complet — fondation de Mangadvisor

## Décision d'architecture

**Nous revenons au point de départ prévu : d'abord charger le catalogue
MyAnimeList au format Jikan, puis enrichir les fiches existantes.**

Le service public \`api.jikan.moe/v4\` a été **arrêté le 1er octobre 2026**.
Tenrai (\`https://api.tenrai.org/v1\`) est un relais public compatible
Jikan sur de nombreux endpoints et accède au catalogue MAL. Cela ne
signifie **pas** que Tenrai est exploité ou développé par Jikan :
la **source technique** est Tenrai ; le **référentiel d'identité** est
l'identifiant de manga **MyAnimeList (\`mal_id\`)**.

Liens :
- [annonce officielle fermeture Jikan](https://github.com/jikan-me/jikan-rest/issues/613)
- [API Tenrai, pagination et documentation](https://api.tenrai.org/documentation)
- [évolutions de Tenrai](https://api.tenrai.org/changelog)

## Parcours concret

\`mangadvisor.cmd → A → 19\` :

1. Vérifie Docker, PostgreSQL et la connectivité de Tenrai.
2. Interroge la **première page** en lecture seule afin d'afficher le
   \`pagination.items.total\` et \`last_visible_page\` **déclarés par la
   source**. Ne les confondez pas avec les 10 033 mangas présents dans la
   base locale avant chargement.
3. Demande une confirmation explicite du parcours complet.
4. Demande si les caches existants doivent être rafraîchis (non par défaut).
5. Effectue une sauvegarde PostgreSQL cohérente.
6. Récupère \`GET /manga?page=N&limit=100&order_by=mal_id&sort=asc\`,
   **sans filtre \`type\`, \`sfw\`, \`q\`, \`status\`, \`genres\` ou \`score\`**.
   Autrement dit : tous les *types* de publications MAL présents dans la
   recherche publique, y compris one-shots, manhwa, manhua, light novels
   et doujinshi lorsqu'ils apparaissent dans la liste du fournisseur.
7. Suit \`pagination.last_visible_page\` et \`has_next_page\`, sans
   prédéterminer 600 ou 2 000 pages. Garde-fou maximal 20 000 pages :
   si la source le dépasse, l'exécution **échoue sans se déclarer complète**.
8. Enregistre chaque page à l'emplacement
   \`data/raw/jikan/complete_tenrai/manga_page_00001.json\`. Les pages
   ont leur provenance et requête enregistrées et sont **réutilisables**
   après une interruption ; page 1 est rafraîchie à chaque exécution.
   La mise à jour complète des pages anciennes s'effectue en choisissant
   \`Retélécharger toutes les pages\`.
9. Insère ou met à jour les \`mal_id\` par lots de 20 pages dans
   \`jikan_manga_source\` (aucune écriture à ce stade dans la mangathèque).
10. **Seulement si toutes les pages ont été obtenues sans erreur et que
    le total annoncé correspond aux IDs distincts**, exécute les scripts
    canoniques non destructeurs \`003\`, \`004\`, \`005\`.
11. Vérifie qu'aucune entrée de \`jikan_manga_source\` ne reste sans
    correspondance dans \`manga\`, puis enregistre un bilan SQL final.

Les notes, quantités de volumes, ISBN possédés, statuts de lecture,
déclarations de collection et identifiants internes \`manga.id\` ne sont
**jamais réinitialisés**, ni supprimés. La consolidation est additive
sur \`manga.source_mal_id\`.

Les métadonnées originales disponibles dans le flux sont conservées dans
\`jikan_manga_source\`, et reprises dans le canonique selon les scripts
existants : titres (principal, EN, JA), synopsis, type, publication,
volumes, chapitres, popularité, score, genres, thèmes, démographie.
Les auteurs sont disponibles dans \`authors_json\` de la source, mais
aucune nouvelle relation \`manga_author\` n'est créée par cette phase.

## Interruption et reprise

En cas de timeout, quota, blocage réseau ou arrêt volontaire :
- les pages déjà vérifiées restent dans \`data/raw/jikan/complete_tenrai/\` ;
- les notices insérées en \`jikan_manga_source\` sont conservées ;
- le catalogue \`manga\` conserve son état stable précédent si la source
  complète n'a pas été validée ;
- le rapport \`data/logs/catalogue_complete/last_sync.json\` indique
  \`INTERRUPTED\` ou \`INCOMPLETE_*\`, et **\`complete=false\`** ;
- relancer A → 19 avec cache, qui réapplique les upserts idempotents.

**Attention :** le fournisseur évolue pendant l'extraction. En cas de
pages décalées ou de doublons MAL entre pages, l'outil s'arrête plutôt
que déclarer le catalogue complet. Choisir alors de rafraîchir toutes
les pages, ce qui reconstruit un instantané plus cohérent.

## Quels chiffres affichons-nous ?

\`last_sync.json\` contient notamment :
- \`source_total_reported\` : total de fiches annoncé par Tenrai ;
- \`source_pages_reported\` : dernière page signalée ;
- \`unique_ids_in_run\` : nombre de \`mal_id\` uniques effectivement lus ;
- \`pages_cached\` et \`pages_fetched\` : preuve de reprise et requêtes ;
- \`db_upserts\` : nombre de lignes source insérées/mises à jour ;
- \`db_counts.source_count\` et \`db_counts.canonical_count\` après SQL ;
- \`complete\` et \`canonical_synced\` pour distinguer les phases.

Un nombre élevé de fiches n'est **pas** une preuve d'exhaustivité :
le critère est la dernière page atteinte, le total cohérent et la
consolidation canonique vérifiée.

## Limites transparentes

- Il s'agit du **catalogue public renvoyé par \`/manga\` de Tenrai à
  l'instant de la collecte**, pas de toutes les notices privées, refusées,
  supprimées ou en attente d'approbation de MyAnimeList. Tenrai offre aussi
  certains endpoints \`/manga/unapproved\`, \`/manga/denied\` et
  \`/manga/deleted\` ; ils ne sont **pas inclus** ici, car ils doivent
  être distingués des œuvres officiellement publiées dans les recherches
  et ne devraient pas être mélangés automatiquement au catalogue public.
- Les pages en cache, sauf la première, sont réutilisées. Pour une
  **nouvelle photographie exhaustive**, choisir le rafraîchissement
  intégral des pages. Un cache peut autrement être ancien.
- Tenrai peut changer de pagination, être indisponible ou imposer une
  limitation de débit. Une pause de 1,1 seconde et des retries avec
  \`Retry-After\` évitent de saturer le fournisseur. Aucun nombre garanti
  de mangas ou de durée garantie ne peut être donné avant le premier appel.
- Le site doit filtrer les contenus réservés aux adultes selon ses
  paramètres d'affichage : la collecte complète **n'applique aucun filtre
  SFW** afin de pouvoir connaître tout le catalogue public.
- Cette phase ne fournit **pas** les titres français manquants ni les
  ISBN français. Après constitution fiable du socle, nous utiliserons
  Scrinis, BnF et MangaUpdates pour enrichir les fiches par MAL ID,
  titre/auteur et édition.

**Objectif immédiat :** disposer d'un catalogue MAL public le plus
complet possible dans PostgreSQL et savoir **combien de fiches sont
réellement opérationnelles** avant toute nouvelle phase multilingue.
