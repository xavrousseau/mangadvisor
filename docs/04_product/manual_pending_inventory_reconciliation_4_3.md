# Atelier de rapprochement de la mangathèque physique (édition par édition)

## Objectif

Lors d'un import CSV, certaines séries sont conservées dans
`user_manga_inventory_pending` parce qu'aucune correspondance exacte et
unique n'a été établie avec le catalogue. L'utilisateur a actuellement
**49 lignes en attente**. Elles représentent des déclarations physiques
préservées, **pas** des mangas validés ni des ISBN.

L'atelier permet de confirmer manuellement, depuis **Ma bibliothèque**,
le **manga du catalogue** correspondant à une ligne existante sans
recharger le CSV et sans taper de commandes SQL.

## Utilisation

1. Dans `mangadvisor.cmd`, choisir **3 — Mettre à jour sans perdre mes données** :
   sauvegarde PostgreSQL vérifiée, synchronisation GitHub, reconstruction Docker.
2. Ouvrir [Mangadvisor](http://localhost:8501) → **Ma bibliothèque**.
3. Descendre à **En attente de rapprochement**. Chaque entrée possède un
   bouton **Rapprocher cette ligne**.
4. Vérifier le nom, l'édition déclarée et le nombre de tomes.
5. Rechercher l'œuvre du catalogue : le nom courant est proposé mais
   **aucune correspondance n'est appliquée automatiquement**. Modifier la
   recherche (nom français, anglais ou japonais) si nécessaire.
6. Choisir **Examiner cette œuvre** : le serveur revalide l'œuvre, vérifie les
   conflits avec les éditions déjà enregistrées, puis affiche un récapitulatif.
7. Cocher la confirmation explicite et cliquer sur **Enregistrer l'association**.
8. La ligne disparaît des éléments en attente et apparaît parmi les
   déclarations physiques sous le manga choisi, avec son **édition et ses
   quantités d'origine inchangées**.

### Plusieurs éditions de Dragon Ball

Une ligne pour `Dragon Ball — Pastel, 42 tomes` et une autre pour
`Dragon Ball — Deluxe, 34 tomes` peuvent viser le **même manga canonique**,
mais sont conservées avec deux clés d'édition différentes. Les
éditions distinctes **ne sont jamais fusionnées**.

Si deux lignes veulent s'associer à la *même œuvre et la même édition*,
l'opération est bloquée : les quantités ne sont pas additionnées
silencieusement. Si un manga est marqué `NOT_INTERESTED`, le rapprochement
est également bloqué jusqu'à correction explicite de ce conflit.

## Garanties PostgreSQL

Les deux opérations de lecture sont :

- `GET /inventory/pending/candidates?source_key=...&q=...` : candidats
  de recherche seulement ; le classement textuel n'est pas une preuve.
- `POST /inventory/pending/resolve/preview` avec `source_key` et
  `manga_id` : vérifie les données, retourne un récapitulatif et un jeton
  de cohérence dérivé de la déclaration, de l'édition et du manga choisis.

Une confirmation explicite via `POST /inventory/pending/resolve` ajoute
atomiquement :

- Une déclaration dans `user_manga_inventory_declaration` avec **les
  valeurs de l'utilisateur reprises telles quelles**.
- Une trace de provenance dans `user_manga_inventory_resolution` :
  original, identifiant lié, édition, empreinte SHA, date de confirmation.
- La suppression de la **ligne en attente correspondante uniquement**,
  après que les deux écritures ont réussi. Tout échec annule l'ensemble.

Aucune insertion dans `manga_fr_edition`, `user_manga_volume` ou
`user_manga_library` : **zéro ISBN inventé, zéro numéro de tome déduit,
zéro lecture ou note modifiée**.

Un jeton périmé (notice catalogue, déclaration ou édition modifiées)
entraîne une réponse 409 avec invitation à refaire l'aperçu. Une
déclaration déjà résolue ne peut pas être reconfirmée par erreur.

## Et après ?

Le rapprochement d'une œuvre ne garantit pas encore la disponibilité des
volumes à l'unité. La prochaine étape pourra vérifier un ISBN physique
avec la BnF pour attribuer de véritables numéros de tome à la bonne édition.
Les 49 lignes non rapprochées seront résolues progressivement, à partir
des choix du propriétaire plutôt que d'une association arbitraire.

Tests de non-régression :
`tests/test_inventory_resolution.py`,
`tests/web/inventory-resolution.test.mjs`, test d'intégration HTTP sur
PostgreSQL jetable (deux éditions d'une même œuvre, rejet des anciens
jetons, traçabilité, non-mutation du statut de lecture et des ISBN).
