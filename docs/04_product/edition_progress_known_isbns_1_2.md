# Mangadvisor 1.2 — Progression par type d'édition sur livres identifiés

## Pourquoi cette étape ?

La fiche manga répertorie les livres français associés à la série,
regroupés par **Classique, Deluxe, Perfect, Collector, Intégrale, Autre**.
Cette information permet un suivi, mais **ne garantit pas que le catalogue
contient la liste complète des volumes parus**. On ne peut donc pas déclarer
une édition « complète » sur la base des seuls ISBN enregistrés.

## Ce qui change

Pour chaque type d'édition présent dans une fiche, l'API ajoute
`edition_progress` avec :
- `known_books` : livres ISBN précisément enregistrés ;
- `owned_books`, `read_books` : livres déclarés possédés et lus ;
- `unowned_known_books`, `unread_known_books` ;
- `owned_pct_of_known`, `read_pct_of_known` : pourcentages **exclusivement**
  parmi les livres enregistrés, arrondis à 0,1 % ;
- `scope = registered_isbns_only` et `published_total_known = false`.

Sur la fiche, deux jauges présentent « Possédé X/Y livres référencés » et
« Lu X/Y livres référencés » pour chaque type d'édition, avec une mention
indiquant que **le total des livres publiés n'est pas établi**.

Les jauges suivent immédiatement les boutons existants « Possédé » et « Lu »
au retour de l'API. Elles sont lisibles sur mobile, avec un contraste
adapté aux trois thèmes d'apparence.

## Garde-fous

- Les dénominateurs comptent des **livres ISBN**, pas des volumes japonais.
- Un même numéro de tome peut exister sur plusieurs livres ou variantes ;
  l'affichage ne confond pas numéros et livres physiques.
- Un tome sans ISBN enregistré **n'est pas considéré comme manquant**.
- Les ratios ne sont jamais présentés comme une complétude de collection
  ou du catalogue éditorial.
- Aucun `ALTER`, aucune migration, aucune nouvelle écriture en base ;
  `user_manga_library` reste intacte.
- Les groupes correspondent à un **type** d'édition. Ils ne prétendent
  pas délimiter exhaustivement des collections éditoriales homogènes
  lorsqu'un même type regroupe plusieurs tirages ou éditeurs.

## Tests

Tests Python de calcul et de bornes, Node de valeur affichée et de
protection CSS, et Playwright PC/mobile : deux jauges présentes,
dénominateur indiqué, première jauge mise à jour après l'acquisition
d'un livre sur une base PostgreSQL **fictive**.

## Prochaine amélioration

Construire un véritable référentiel fiable des séries/éditions et de leurs
volumes commercialisés en France, puis distinguer clairement :

1. **Non possédé parmi les ISBN connus** (dès maintenant) ;
2. **Tome publié et manquant** (uniquement avec un inventaire vérifié) ;
3. **Volume futur confirmé** (uniquement avec une date et une source fiables).

La BnF seule ne garantit pas cette exhaustivité. Il faudra recouper avec
des sources d'éditeurs ou un catalogue français exploitable légalement,
sans inventer de numéros ou de dates.
