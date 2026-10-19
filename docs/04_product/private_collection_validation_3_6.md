# Mangadvisor 3.6 — Évaluer le moteur avec un véritable inventaire privé

## Objet

Cette fonction utilise **ton inventaire de séries** plutôt qu'un simple catalogue synthétique. Elle permet d'évaluer sur TON installation locale les capacités de rapprochement des titres et de détecter d'éventuelles recommandations qui correspondent déjà à une série possédée.

**Attention :** le dépôt GitHub ne contient **ni le vrai inventaire, ni les rapports personnels**. Le CSV personnel est livré séparément à son propriétaire dans un ZIP. Le dossier \`data/private/\` est exclu de Git.

## Installation (une seule fois)

1. Mettre Mangadvisor à jour depuis GitHub : \`git pull origin main\`.
2. Extraire le **pack privé de mangathèque** fourni dans **la racine du dossier Mangadvisor**, en conservant l'arborescence : \`data/private/inventaire.csv\` et \`data/private/inventaire.json\`.
3. Lancer Docker Desktop, puis \`mangadvisor.cmd\` option **3 — Build + démarrage**.
4. Choisir l'option **20 — Auditer ma mangathèque (lecture seule)**.
5. Consulter \`data/private/rapport_audit.json\`. Il est créé **uniquement sur le PC**, sans être envoyé à GitHub.

Le script utilisé est \`tests/local/private_inventory_audit.py\`. Il s'exécute **dans le conteneur API Docker** déjà installé : aucune installation Python supplémentaire n'est nécessaire sur Windows.

On peut également lancer une validation des quantités sans contacter l'API :

\`python tests/local/private_inventory_audit.py --input data/private/inventaire.csv --report data/private/rapport_offline.json --offline\`

## Vérifications réellement effectuées

- **Intégrité du fichier** : titres non vides, colonnes attendues, quantités entières positives ou nulles, somme physique égale principaux + doubles + éditions inconnues ; refus des titres exactement dupliqués.
- **Correspondance au catalogue local** : pour chaque entrée, appelle \`GET /mangas?q=...&limit=70\` ; accepte un rapprochement **seulement si exactement une œuvre** possède un titre strictement égal après normalisation d'accents/ponctuation (titre principal, anglais ou japonais). Les cas sans correspondance ou ambigus sont signalés **pour validation manuelle**. Aucun ISBN ou identifiant MAL n'est inventé.
- **Éditions multiples** : deux mentions portant sur des nombres différents de tomes d'une même série sont **conservées comme deux lignes d'inventaire**. Elles peuvent correspondre au même identifiant canonique pour le test de non-recommandation, mais aucune édition n'est fusionnée ou importée.
- **Trois recherches read-only avec Mon conseiller** (action et sans gore, mystère terminé et français préféré, surprise basée sur la bibliothèque réelle de l'application). Vérifie les doublons de résultats, la diversité telle que rapportée par l'API et les éventuelles œuvres reconnues dans l'inventaire qui réapparaissent.
- **Comparaison avec l'inventaire externe** : un manga réapparu n'est pas immédiatement imputé à un bug du classement ; il peut indiquer que la bibliothèque **de l'application** n'est pas encore synchronisée avec le classeur. Le rapport dit explicitement \`possible_collection_sync_issue\`, et n'écrit rien pour « réparer ».

L'API contactée est **exclusivement l'API HTTP locale** (\`127.0.0.1\`, \`localhost\` ou \`api\` à l'intérieur du conteneur). L'outil refuse volontairement les URL externes.

## Ce que le fichier ne permet PAS encore de mesurer

Cet inventaire donne des **quantités** et certaines mentions d'**éditions en cours / collections partielles**. Il **ne renseigne pas** les notes personnelles, les mangas lus, les vrais favoris, les ISBN, les plages précises de tomes de chaque édition ou les réactions historiques « Ça m'intéresse / Pas pour moi ».

Ainsi, nous ne pouvons pas prétendre calculer :
- un taux de satisfaction des recommandations ;
- une précision de découverte des genres réellement aimés ;
- un taux de correspondance ISBN/tomes ;
- un avant/après réel des réactions dans la base personnelle sans lire les réactions enregistrées.

Un **statut « édition en cours » dans le plan de rangement n'est pas le statut \`READING\`** de Mangadvisor et n'est pas une vérification des publications en France.

**Nous ne devons pas importer automatiquement le fichier dans \`user_manga_library\`** : les volumes de plusieurs éditions/doublons sont distincts, et les mêmes séries peuvent exister sous plusieurs noms ou formats. Il faut valider les rapprochements puis choisir une procédure d'import séparée qui préserve l'historique des lectures.

## Confidentialité et non-destruction

- Aucun fichier personnel ni titre de l'inventaire dans le dépôt GitHub ou les tests CI.
- Aucun accès Internet vers un fournisseur de recommandation externe depuis le script.
- Aucune commande \`POST /recommendations/feedback\`, \`POST /library\`, \`DELETE\`, SQL \`INSERT/UPDATE\` ou migration.
- Aucun changement de ta collection, de tes notes ou de tes livres existants.
- Les tests GitHub exécutent uniquement une **collection synthétique et les fonctions de validation** ; l'exécution des 103 recherches réelles nécessite Docker sur ton PC.

## Interpréter le rapport

Dans \`catalogue_coverage\` :
- \`exact_unique_entries\` : combien de lignes ont trouvé un titre unique strictement identique.
- \`ambiguous_entries\` : plusieurs œuvres du catalogue portent le même titre, rapprochement incertain.
- \`manual_check_entries\` : aucun titre strictement identique ; il faut éventuellement vérifier un alias ou une édition.
- \`distinct_confirmed_catalogue_ids\` : combien d'identifiants canoniques distincts correspondent aux lignes rapprochées. Ce nombre **peut être inférieur** au nombre de lignes si des variantes d'édition existent.

Dans \`recommendation_checks\`, \`listed_owned_titles_suggested\` signale les mangas déjà présents dans l'inventaire externe ; c'est un **point d'attention**, pas un diagnostic de fuite de données ou une preuve de bug tant que la base active n'a pas été réconciliée.

## Suite logique

Analyser le rapport produit localement et résoudre les titres sans correspondance avec validation humaine. Une fois les œuvres et les éditions confirmées, **comparer de vraies recommandations avant/après des réactions existantes**, uniquement en lecture seule, puis améliorer le classement à partir de mesures fiables.
