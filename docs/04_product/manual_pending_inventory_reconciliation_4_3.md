# Rapprochement manuel de la mangathèque physique

## Objectif

Un import CSV peut conserver des lignes dans `user_manga_inventory_pending`
quand aucune correspondance sûre avec une œuvre du catalogue n'a été
établie. Les lignes en attente sont des **déclarations personnelles
conservées**, pas des ISBN vérifiés ni des tomes déjà attribués.

Dans **Ma bibliothèque → Mes éditions**, une entrée en attente peut être
rapprochée manuellement d'une œuvre. Les titres français, anglais et
japonais servent à **proposer des candidats**, jamais à confirmer
silencieusement une correspondance.

## Parcours utilisateur

1. Ouvrir **Ma bibliothèque → Mes éditions** et choisir une ligne en attente.
2. Cliquer **Rapprocher cette ligne**, chercher l'œuvre et sélectionner
   **Examiner cette œuvre**.
3. Vérifier ensemble : œuvre canonique, édition déclarée, nombre de tomes,
   autres éditions et doublons.
4. **Si aucune édition n'est déjà déclarée** : confirmer l'association.
5. **Si cette œuvre existe déjà** : comparer les exemplaires réels ;
   sélectionner explicitement l'une des actions permises :
   - **Ajouter une édition distincte** : uniquement si la clé d'édition
     est différente des éditions déjà présentes. Les quantités originales
     sont conservées.
   - **Archiver la ligne déjà comptée** : pour éviter de compter deux fois
     les mêmes livres. La ligne est retirée des attentes et conservée dans
     le journal d'audit, **sans ajouter de déclaration ou de tome**.
6. Confirmer explicitement la comparaison des déclarations existantes,
   puis le rapprochement choisi.

**Exemple :** les éditions Pastel et Deluxe de *Dragon Ball* peuvent
partager la même œuvre MAL sans partager leurs ISBN ou leurs volumes.
Une seconde ligne décrivant déjà la Deluxe ne doit pas ajouter ses 34 tomes
une deuxième fois.

La confirmation reste refusée si l'œuvre est marquée `NOT_INTERESTED`
dans la bibliothèque de lecture tant que cette contradiction n'est pas
corrigée explicitement.

## Garanties techniques

- `GET /inventory/pending/candidates` retourne des **suggestions seulement**.
- `POST /inventory/pending/resolve/preview` présente les éditions
  existantes, les quantités, les actions autorisées et un jeton SHA256
  incluant le contexte. Aucune écriture.
- `POST /inventory/pending/resolve` exige le jeton actuel,
  `acknowledge_work_and_edition=true` et, si des déclarations existent,
  `acknowledge_existing_inventory=true`. L'action est explicite :
  `CREATE_DECLARATION` ou `MARK_DUPLICATE`.
- Sous transaction, une nouvelle édition distincte crée une ligne dans
  `user_manga_inventory_declaration`. L'archivage **n'en crée pas**.
  Les deux actions enregistrent leur mode et le contenu original dans
  `user_manga_inventory_resolution` avant de retirer une seule ligne
  de `user_manga_inventory_pending`. En cas d'erreur, la transaction
  n'est pas validée.
- Une colonne `resolution_mode` est ajoutée de manière additive aux
  installations existantes ; les anciens rapprochements sont identifiés
  par défaut comme créations de déclaration.

Aucune action ne déduit d'ISBN, de numéro de tome exact, de lecture ou
de note. Les tables `manga_fr_edition`, `user_manga_volume` et
`user_manga_library` ne sont pas modifiées par ce rapprochement.

## Validation

Les comportements de création d'une édition distincte et d'archivage
sans double comptage sont couverts par les tests
`tests/test_inventory_resolution.py`,
`tests/web/inventory-resolution.test.mjs` et par la recette
PostgreSQL/HTTP jetable de la CI. La validation des livres réels
appartient au propriétaire : **l'application ne peut pas deviner quels
exemplaires sont physiquement identiques**.
