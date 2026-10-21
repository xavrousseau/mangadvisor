# Comparatif des sources manga — V2

La V2 corrige les angles morts mis en évidence par le **premier échantillon
réel de 50 œuvres (20 octobre 2026)**. Le JSON V1 fournissait 30 titres exacts
Scrinis, 14 ambigus et 2 sans candidat ; 30 titres exacts MangaUpdates,
17 suggestions et trois erreurs HTTP/réseau.

Ces chiffres concernent les **résultats de recherche**, pas une validation
d'œuvre, une couverture exhaustive, ni des preuves de livres/ISBN possédés.

## Installation et démarrage

Depuis Windows, utiliser \`mangadvisor.cmd → 3\` pour mettre à jour le dépôt,
puis **A → 17**. Le menu **A → 16** conserve la V1 pour comparaison.

L'outil propose :
1. Un maximum de **50 œuvres** (priorité aux entrées en attente puis à la
   collection reconnue, enfin au catalogue) ;
2. Un maximum de **12 fiches détaillées par fournisseur**, paramétrable de 0 à
   20. Les fiches sont choisies uniquement quand un candidat a un identifiant
   numérique exploitable et une correspondance par titre/MAL, même ambiguë ;
3. Un aperçu des titres sans requête externe ;
4. Un accord explicite avant d'envoyer ces titres à Scrinis et MangaUpdates.

Chaque fournisseur peut effectuer au plus **6 recherches alternatives**
supplémentaires, réservées aux titres multilingues connus et à deux équivalences
de recherche explicites (City Hunter/Nicky Larson et Adieu Eri/Sayonara Eri).
Cette deuxième recherche **ne constitue jamais une correspondance validée**.

Les recherches et lectures de fiches sont espacées globalement par fournisseur,
sans dépasser la limite Scrinis **15 requêtes/minute sans clé** (pause 4,5 s).
MangaUpdates est interrogé à intervalle prudent de 2 s, avec une attribution
claire à la source dans les rapports. Les réponses structurées réussies sont
mises en cache 24 heures **sur le PC uniquement**, hors Git.

## Dossier de sortie

\`data/logs/catalog_sources/\`

- \`comparatif_sources_v2_YYYYMMDD_....json\` : tous les candidats (jusqu'à 8
  par recherche), leurs identifiants explicites, scores, format, signaux de
  correspondance, ambiguïtés, diagnostic de forme de la réponse, fiches
  détaillées consultées.
- \`comparatif_sources_v2_YYYYMMDD_....csv\` : **une ligne par œuvre et
  fournisseur**, résultats, candidats supplémentaires, genres, thèmes,
  titres alternatifs, ISBN **candidats** contrôlés, et erreurs.
- \`cache_v2/\` : résultats de recherche/fiches déjà consultés,
  automatiquement réutilisés pendant 24 heures.

**Attention aux colonnes bibliographiques :**

- \`genres\` et \`themes\` ne sont renseignés **que si une fiche détaillée a
  été chargée**. L'absence dans un tableau n'implique pas absence chez
  Scrinis/MangaUpdates.
- \`isbn_valides_candidats\` conserve uniquement des ISBN-10/13 à clé correcte
  trouvés sur une fiche ou les 20 premiers tomes retournés ; un ISBN n'est
  **jamais** automatiquement lié à une œuvre/édition/possession.
- \`concurrents_ambigus\` et \`autres_candidats\` permettent enfin de savoir
  pourquoi Bleach, Naruto, Demon Slayer, etc. sont ambigus.
- \`search_schema\` et \`alternate_schema\` donnent les **noms de clés** reçus,
  non le contenu entier de la réponse. Cela aide à diagnostiquer les
  identifiants Scrinis manquants dans la V1.
- Un ISBN/une série n'est pas un tome confirmé : le système ne crée pas
  de volume dans la mangathèque et ne fusionne jamais Dragon Ball Pastel,
  Deluxe, guides ou spin-offs.

Le code utilise exclusivement des requêtes SELECT à PostgreSQL ; aucune
insertion, suppression ou modification des tables catalogue ou utilisateur.

## Retour d'expérience du 21 octobre 2026 et correctif

Le second test réel de 50 œuvres a donné :
- **Scrinis** : 35 titres exacts, 9 ambigus, 4 suggestions, 2 absences ;
  55 appels HTTP, **aucun identifiant ni détail récupéré**.
- **MangaUpdates** : 32 titres exacts, 18 suggestions, 20 fiches détaillées
  récupérées après 74 appels ; **aucun ISBN/volume** exposé sur ces fiches.
- **45/50** œuvres avaient au moins un titre exact sur l'un des deux services,
  mais le type du titre peut contredire le manga réellement recherché.

Deux dangers confirmés dans le rapport :
1. **Wind Breaker** : le résultat intitulé exactement "Wind Breaker" est le
   **manhwa sur le cyclisme** tandis que "Wind Breaker (NII Satoru)" est un
   autre candidat **manga japonais**. Un titre identique ne suffit pas.
2. **Demon Slayer/Fullmetal Alchemist** : un doujinshi pouvait apparaître au
   premier rang malgré un véritable manga japonais également présent parmi
   les candidats.

La révision de la V2 corrige ces deux erreurs :
- Les candidats manga dont le titre comporte un qualificatif d'auteur
  \`(…)\` rendent le rapprochement **AMBIGUOUS** quand la recherche exacte
  désigne potentiellement une œuvre distincte ; la fiche de ce candidat n'est
  alors pas lue comme s'il avait été validé.
- Un doujinshi, artbook ou roman passe derrière une œuvre de type manga
  ordinaire **pour les simples suggestions non exactes**.
- Le parseur essaie aussi le champ \`hub_id\` des résultats Scrinis si celui-ci
  est un entier positif, et conserve le type des champs \`hub_id\`/\`ids\`
  pour diagnostic. La correspondance avec le vrai endpoint de fiche reste à
  vérifier sur une exécution réelle ; ne jamais prendre \`public_n\` pour
  un identifiant d'œuvre.

## Limites honnêtes

- **Aucun appel API réel V2 n'a été exécuté dans GitHub Actions**. Les tests
  utilisent des réponses synthétiques. Le format courant des résultats Scrinis
  devra être validé grâce aux diagnostics du vrai rapport V2.
- Le fournisseur Scrinis étant encore en bêta, les réponses peuvent être
  incomplètes. Sa documentation officielle décrit \`/api/v1/search\` et
  \`/api/v1/series/{id}\`, mais pas ici la structure détaillée de chaque
  résultat. On ne devine jamais un ID numérique.
- La documentation officielle MangaUpdates décrit \`POST /series/search\`
  et \`GET /series/{id}\`. Les catégories de séries dérivées ou artbooks
  restent visibles et ne sont pas fusionnées par simple similarité.
- Les ISBN ne sont recherchés qu'au travers des fiches détaillées consultées.
  L'intégration avec BnF et Sudoc sera une étape distincte sur ISBN confirmés.
- En présence d'un quota dépassé, la source est suspendue ; ses requêtes
  suivantes sont marquées indisponibles, **pas absentes du catalogue**.

## Sources / conditions

- [API Scrinis](https://scrin.is/fr/api)
- [Conditions Scrinis](https://scrin.is/fr/conditions)
- [Documentation MangaUpdates](https://api.mangaupdates.com/v1)

Scrinis autorise la réutilisation via son API mais interdit l'aspiration
hors interface et le contournement des quotas. MangaUpdates demande
attribution, espacement des appels et cache. L'outil respecte ces points.

Le comparatif donne les preuves nécessaires pour **choisir une source à
enrichir ultérieurement**, mais ne constitue pas une autorisation de
répliquer massivement toute la base du fournisseur.
