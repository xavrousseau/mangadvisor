# Mangadvisor 3.6 — Tester sa vraie mangathèque sans publier ni modifier ses données

## Pourquoi ce mode existe

Les premiers tests utilisaient des séries synthétiques. Une collection réelle peut poser des problèmes absents d'un catalogue de démonstration : titres édités en français, oeuvres sous plusieurs éditions, plusieurs volumes identiques, titres ambigus et complétude non vérifiée.

**Le benchmark privé n'est PAS un import.** Il effectue une simulation de rapprochement au moyen de \`POST /library/import/csv\` avec \`dry_run=true\`, puis interroge le conseiller **uniquement en lecture** pour trois demandes (action, mystère, surprise). Toutes les requêtes sont adressées à \`127.0.0.1:8000\`, jamais à un service tiers. Le résultat est enregistré sur ton disque.

## Utilisation Windows

1. Réaliser la sauvegarde de ta collection avec \`mangadvisor.cmd\`, option **17**.
2. Créer \`private-data\` à la racine du projet, puis y déposer ton CSV privé **en le nommant \`mangatheque.csv\`**.
3. Démarrer Mangadvisor normalement avec Docker Desktop et l'option **3**.
4. Lancer \`mangadvisor.cmd\`, option **20 — Tester ma mangathèque en lecture seule**.
5. Un fichier \`private-data/benchmark_mangatheque_YYYYMMDD_HHMMSS_XXXXXX.json\` est créé. Il contient les titres non reconnus, les correspondances floues, les collisions d'oeuvres et les propositions effectivement retournées par l'application, avec leurs diagnostics.
6. Après des **réactions réelles** (« Ça m'intéresse », « Pas pour moi »…) dans l'interface, relancer l'option 20 : le rapport calcule pour chaque scénario le nombre de suggestions inchangées et nouvellement apparues depuis le rapport précédent.

Tu peux aussi ouvrir une console PowerShell dans le dépôt et lancer :
\`powershell -NoProfile -ExecutionPolicy Bypass -File cmd/benchmark-mangatheque.ps1 -CsvFile "C:\mon\chemin\inventaire.csv"\`

Aucune note, aucun statut lu ou favori ne sont inventés. Le fichier CSV doit avoir l'en-tête exact (séparateur \`;\`) :
\`serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier;statut_releve;ligne_source\`

**Ne pas renommer ni supprimer \`private-data/\`** entre les deux prises de mesure si tu veux conserver le benchmark précédent. \`private-data/\` est ignoré par Git : cette collection privée **n'est jamais poussée sur GitHub**. Les données d'exemple CI qui testent ce script sont entièrement synthétiques.

## Ce qui est validé — et ce qui ne l'est pas

- La quantité de séries, tomes principaux, doublons et autres éditions est recalculée dans le fichier local.
- Chaque série est testée contre le catalogue de ton instance par **la logique de rapprochement actuelle**, sans aucune écriture. Les correspondances indirectes (rang 3+) sont marquées **floues**, pas certifiées. Si plusieurs lignes correspondent au même identifiant manga, le benchmark distingue les **éditions explicitement déclarées d'une même œuvre** des collisions ambiguës (voir 3.7 ci-dessous).
- Seules les correspondances directes et non conflictuelles peuvent être utilisées pour repérer une suggestion correspondant à un manga de l'inventaire.
- Le benchmark vérifie le résultat réel actuel du conseiller pour trois demandes. Une œuvre de la liste qui apparaît dans les suggestions est un signe que **la liste privée et la bibliothèque en base ne sont peut-être pas encore synchronisées**, pas automatiquement une erreur du moteur.
- Les indicateurs **avant/après** montrent des changements de suggestions, **pas une amélioration prouvée de la qualité**. Pour juger l'amélioration, il faut des retours véritablement donnés par l'utilisateur, une collection reliée au bon identifiant et une période d'observation suffisante.
- Ce CSV indique la possession physique et quelques mentions éditoriales ; il **ne contient pas** d'ISBN fiables, de volumes effectivement lus, de notes, de favoris, ni d'avis négatifs. Les estimations du plan de rangement ne sont pas des preuves de complétude éditoriale. Les tomes physiques en double sont comptés séparément des tomes principaux ; les autres éditions doivent être identifiées avant rattachement aux ISBN.

## Pourquoi ne pas importer automatiquement le CSV ?

La fonctionnalité historique d'import CSV de la bibliothèque peut **remplacer par des valeurs vides** certaines métadonnées (notes, favoris, lectures, commentaires) lorsqu'un manga existe déjà. En outre, les titres français ou les éditions d'une même œuvre peuvent conduire à une association incertaine. Le mode 3.6 **n'appelle donc jamais l'import en mode écriture**. Une vraie intégration de ce fichier nécessite un mécanisme d'import additif, conservateur et confirmé pour chaque correspondance sensible.

## Garanties techniques

- Script \`cmd/benchmark-mangatheque.ps1\` : lecture locale, contrôle de chiffres positifs, refus des doublons de lignes, \`dry_run=true\` imposé ; aucune option d'activation des écritures.
- \`private-data/\` dans \`.gitignore\`; ni collection privée ni identifiants/API privés dans le dépôt.
- CI PostgreSQL jetable : fixture **synthétique**, double exécution du benchmark, comparaisons déterministes, snapshot et compteurs de bibliothèque inchangés, avant de réexécuter la sauvegarde/restauration et la vérification HTTPS.


## Extension 3.7 — deux éditions physiques d'une seule œuvre

Le CSV conserve ses six premières colonnes et accepte trois colonnes facultatives :

- **oeuvre_commune** : titre canonique à rechercher, uniquement lorsque le propriétaire confirme explicitement que les variantes représentent la même œuvre.
- **edition_declaree** : libellé de l'édition possédée, distinct pour chaque version.
- **format_catalogue_provisoire** : indice informatif, jamais utilisé pour inventer un ISBN.

Les CSV plus anciens continuent à fonctionner. Les deux premières colonnes facultatives doivent être renseignées ensemble, ou rester vides ensemble.

Deux lignes ne forment un **groupe d'éditions distinctes** que si elles ont le même titre canonique déclaré, des éditions déclarées différentes, une correspondance de catalogue directe (rang 1 ou 2), et le même identifiant manga canonique. Sinon, il s'agit toujours d'une collision potentiellement ambiguë. Les groupes validés se trouvent dans le nouveau champ **groupes_editions_distinctes** du rapport, avec les quantités séparées.

### Exemple privé documenté

Les deux versions Dragon Ball sont conservées séparément dans l'inventaire : **Pastel (42 tomes)** et **Deluxe (34 tomes)**, mais pointent vers la même œuvre pour le benchmark. L'éditeur Glénat appelle sa version 34 tomes *Perfect Edition* : l'association aux ISBN de la collection physique reste néanmoins à confirmer. Références :
- https://www.glenat.com/actualite/arret-de-commercialisation-des-editions-sens-francais-de-dragon-ball/
- https://www.glenat.com/glenat-manga/series-dragon-ball-perfect-edition/

**Aucune écriture dans la bibliothèque, aucune attribution automatique d'ISBN et aucune fusion de tomes physiques.** Le benchmark ne fait que distinguer les vrais groupes d'éditions déclarés des correspondances ambiguës.
