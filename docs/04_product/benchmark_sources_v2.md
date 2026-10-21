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
   20. Une correspondance non ambiguë lit sa fiche ; une ambiguïté peut
   comparer les deux ou trois candidats plausibles, **sans les valider**, si
   le budget restant suffit à lire toutes leurs fiches ;
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
  trouvés sur une fiche ou jusqu'à 100 tomes parcourus (20 ISBN conservés,
  priorité au support papier français) ; un ISBN n'est
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
- **Identifiants Scrinis vérifiés :** le `hub_id` est un UUID, pas un entier.
  Le champ `public_n` est le numéro de fiche public utilisable dans
  `/api/v1/series/{id}`. Le nouveau lecteur utilise uniquement ce numéro
  validé et conserve l'UUID comme identifiant opaque non adressable.

## Troisième test réel du 21 octobre : cause exacte du blocage Scrinis

Le rapport du 21 octobre au matin a confirmé que :
- Scrinis restait à **0/50 identifiants** malgré ses 35 titres exacts ;
- MangaUpdates avait correctement détecté l'homonymie **Wind Breaker**
  et classé les œuvres sous \`AMBIGUOUS\` plutôt que de lire la mauvaise fiche ;
- l'ancien parseur cherchait un entier dans \`hub_id\`, alors que la réponse
  réelle indique \`hub_id\` comme chaîne et \`public_n\` comme entier.

La fiche publique officielle
[Bestia nº 9884](https://scrin.is/fr/series/9884-bestia) permet de suivre
son lien direct [API](https://scrin.is/api/v1/series/9884). Le JSON réel
indique :

- \`hub_id\` UUID et \`public_n: 9884\` ;
- \`titles.primary\` et \`titles.all\` avec les différentes langues ;
- \`taxonomy.genres\`, \`taxonomy.tags\`, \`credits\`, \`publication.publisher\` ;
- \`editions\` distinctes par \`medium\` (\`print\` ou \`ebook\`) et \`lang\` ;
- \`volumes[].n\`, \`volumes[].isbn_13\`, \`edition\`, \`medium\`, \`lang\`.

Le nouveau code reconnaît ces champs, distingue papier français et
numérique et ajoute trois colonnes CSV : \`editions\`,
\`isbn_papier_fr_candidats\`, \`auteurs\`.

Les ISBN restent des **indices bibliographiques non confirmés**, sans
liaison automatique aux volumes de la mangathèque. Le vieux cache Scrinis
est invalidé automatiquement ; le cache MangaUpdates reste exploitable.

Le prochain essai peut être réduit à **5 titres et 5 fiches par API**
dans **A → 17**. Cette vérification permet de mesurer le nombre de fiches
Scrinis effectivement accessibles et les ISBN papier français disponibles.

## Quatrième résultat réel et traitement des ambiguïtés (21 octobre 2026)

Sur les cinq premiers titres de mangathèque en attente :

- **5/5 Scrinis** : identifiants \`public_n\` récupérés ; la lecture des
  identifiants est désormais validée par une exécution locale.
- **1/5 Scrinis** : fiche détaillée lue ; 4 autres avaient le statut
  \`AMBIGUOUS\` et leurs détails étaient auparavant ignorés.
- **Yakuza Zen**, Scrinis \`public_n=15661\` : 3 ISBN de tomes français
  papier renseignés, 3 volumes français papier et 4 japonais papier,
  auteur Gen Momoji et éditeur VEGA.
- **MangaUpdates** : 3 titres exacts, 1 ambigu et 1 suggestion ; seulement
  0 appels Internet grâce au cache local précédent.

Le taux affiché de 20 % de titres Scrinis exacts **non ambigus** ne
représente pas un taux de présence : les cinq titres ont un candidat exact,
mais quatre sont classés ambigus, soit à cause d'homonymes, soit à cause
d'une alerte trop large sur les qualificatifs de langue.

La version suivante évite la fausse alerte pour \`Tokyo Ghoul
(en allemand)\` : une édition linguistique alternative reste candidate
mais ne provoque plus une collision d'œuvres sans autre indice.

Pour les véritables ambiguïtés (les deux \`Wind Breaker\`, les deux
\`Black Clover\`, et le manga + light novel \`Yu-Gi-Oh!\`), le moteur peut
lire **au plus trois fiches concurrentes par œuvre**, à condition que le
quota de fiches détaillées restant permette de consulter **toute la paire**
et non un seul candidat au hasard.

Le JSON garde alors dans \`competing_details\` les métadonnées de chaque
candidat avec son ID, titre, auteur, éditeur, type et ISBN papier français
éventuels ; le CSV expose les mêmes indices sous
\`fiches_concurrentes_a_verifier\`. La rubrique
\`raison_controle_non_execute\` indique le manque de quota/identifiant.

**Jamais** de correspondance automatiquement confirmée ni de liaison
à un manga, à une édition physique ou à la bibliothèque utilisateur.
L'identité demeure \`AMBIGUOUS\` tant qu'il n'existe pas de preuve fiable.

Si l'on veut examiner ces cinq titres avec toutes les ambiguïtés, définir
**10 fiches détaillées par fournisseur** dans A → 17, en gardant
5 œuvres. La limite reste de 20 fiches/fournisseur.

## Cible française en priorité pour la mangathèque (nouvelle version)

**Hypothèse de travail explicite :** les déclarations de la mangathèque
personnelle sont des **livres en français et sur papier** (\`FR_PRINT\`).
Il s'agit d'une *cible de recherche bibliographique*, **pas d'une preuve**
que chaque exemplaire est français, imprimé ou identifié par ISBN.

L'échantillon est réparti en deux scopes :
- \`pending\` (déclarations encore non rapprochées) et \`owned\` (œuvres
  déclarées possédées) : \`market_target=FR_PRINT\`, langue \`fr\`,
  support \`print\`, origine de l'hypothèse
  \`USER_COLLECTION_DEFAULT_UNVERIFIED\`.
- \`catalog\` : \`market_target=INTERNATIONAL\`, **aucune langue ni édition
  française imposée**. Les champs d'œuvre japonaise restent pertinents
  pour les recommandations.

Pour les œuvres de la collection, le benchmark lit en **SELECT seulement** :
- \`edition_declared\` (sans écraser deux versions comme **Dragon Ball Pastel
  et Deluxe**) ;
- \`format_hint\` (manga, manhwa, guide/artbook/roman s'il est précisé).

Ces informations ne sont **jamais transmises aux API** : le client envoie
uniquement un titre de recherche ou un identifiant public pour la fiche.
Il ne récupère ni notes privées, ni quantités, ni références internes.

### Deux évaluations séparées

Le JSON V2 ajoute \`matching_review\` par œuvre/fournisseur :

1. \`work.score\` et \`work.status\` : preuves d'identité de l'œuvre
   (correspondance exacte de titre, MAL lorsqu'il existe, **cohérence du
   type** avec un format déclaré). Les auteurs des fournisseurs sont lus,
   mais **non comparés** faute d'auteur de référence dans l'échantillon.
2. \`edition.score\` et \`edition.status\` : preuves de **publication française
   papier** (\`editions[].lang=fr\` + \`medium=print\` ou références des
   volumes, ISBN bibliographiques français présents, famille d'édition
   lorsque déclarée). Pour un manga du catalogue général, le score
   d'édition française est **non applicable** (null), et non zéro.
3. \`competing_evidence\` : mêmes deux évaluations **pour chaque candidat
   ambigu consulté séparément**, sans sélectionner un "vainqueur".

Les deux scores sont des **indices heuristiques**, **PAS des probabilités** ;
aucun score à 100 % ni ISBN de fournisseur ne confirme automatiquement
une possession ou une édition exacte.

Les familles \`Pastel\`, \`Deluxe\`, \`Perfect\`, \`Kanzenban\`,
\`Intégrale\`, \`Collector\`, \`Prestige\`, \`Double\` et \`Standard\` sont
différenciées. Une famille inconnue n'est **pas réinterprétée** comme
\`Standard\`. Si Pastel et Deluxe sont déclarées pour une même œuvre,
une fiche ne couvrant que Deluxe est marquée
\`FR_PRINT_PARTIAL_EDITION_MATCH_REVIEW\`, jamais comme si les deux éditions
avaient été trouvées.

Les champs supplémentaires du CSV sont \`cible_marche\`,
\`cible_langue\`, \`cible_support\`, \`editions_declarees\`,
\`formats_declares\`, \`score_oeuvre_indicatif\`,
\`score_edition_fr_indicatif\`, \`etat_oeuvre\`, \`etat_edition_fr\`,
\`signaux_edition\` et \`isbn_fr_papier_candidats\`.

**Limite assumée :** il s'agit encore d'un **diagnostic local**, sans
liaison automatique ni import massif, ni contrôle de tous les volumes
au-delà des références fournies. Une future étape distincte pourra
proposer des rapprochements *staging / validation* à partir des ISBN
et des éditeurs français, en préservant l'historique des éditions.

## Limites honnêtes

- **GitHub Actions n'interroge pas les API en direct.** Les tests se basent
  sur des fixtures correspondant au JSON de fiche officielle observé.
  Le fonctionnement du nouveau lecteur sur ton PC reste à confirmer.
- Scrinis est encore en bêta : les données peuvent être incomplètes.
  Aucune recherche de fiche n'est tentée sans `public_n` positif validé,
  et une correspondance ambiguë ne reçoit pas d'enrichissement arbitraire.
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
