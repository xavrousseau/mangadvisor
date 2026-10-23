# Mangadvisor — regroupement canonique des éditions (V1)

## Choix architectural

Le catalogue `manga` représente **l'œuvre**, identifiée par son ID MAL.
La table déjà utilisée `manga_fr_edition` représente **un livre ISBN**
avec numéro de tome, et NON une édition regroupant plusieurs livres.
Les clés étrangères de `user_manga_volume` vers ces livres sont conservées.

Une migration additive crée deux tables, sans déplacer les ISBN existants :

- `manga_fr_edition_group` : une **édition déclarée explicitement** pour une
  œuvre, avec une clé stable `edition_key`, un libellé, une catégorie et
  éventuellement un éditeur. Deux éditions de même catégorie peuvent avoir
  deux clés distinctes. Aucune édition n'est déduite d'un titre fournisseur.
- `manga_fr_edition_group_book` : association **explicitement confirmée**
  entre l'édition et un livre déjà enregistré via BnF. Un même livre ne peut
  appartenir qu'à une seule édition, et des clés étrangères composites
  interdisent la confusion d'œuvre, de catégorie ou d'ISBN.

Ainsi : `manga` (œuvre) → `manga_fr_edition_group` (édition) →
`manga_fr_edition` (livre/tome avec ISBN) → `user_manga_volume` (possession,
lecture). La dernière liaison est **indépendante** et n'est jamais modifiée
par le regroupement.

Les livres historiques restent **non regroupés** après migration. Aucun
backfill à partir d'un libellé « classique » ou d'une correspondance de
titres ; l'API renvoie leur nombre pour une validation ultérieure.

## Dragon Ball : deux éditions bien séparées

| Œuvre | Clé d'édition | Libellé déclaré | Catégorie technique |
|---|---|---|---|
| Dragon Ball | `pastel` | Première édition française (« Pastel » dans l'inventaire) | `OTHER` |
| Dragon Ball | `deluxe` | Deluxe | `DELUXE` |

Ces libellés sont des **choix éditoriaux déclarés**, non des preuves que la
BnF emploie historiquement le nom « Pastel ». Aucun ISBN précis ne peut
être attribué sans vérification de la notice et confirmation du bon tome.

## API : validation humaine explicite (local uniquement)

- `GET /collection/mangas/{id}/edition-groups` : arborescence des éditions
  déjà confirmées et ISBN associés; nombre de livres existants non regroupés.
- `POST /collection/mangas/{id}/edition-groups` : enregistre un **libellé
  d'édition** après saisie de `confirmation: "CONFIRMER_EDITION"`.
  Le couple `(manga_id,edition_key)` est unique, aucune fusion automatique.
- `POST /collection/mangas/{id}/edition-groups/{group_id}/books` :
  exige `book_id`, l'ISBN-13 exact et
  `confirmation: "CONFIRMER_RATTACHEMENT"`. Le livre **doit déjà exister**
  dans `manga_fr_edition`, dont la création impose une recherche ISBN
  exacte BnF et un choix manuel de l'œuvre, de la catégorie et du tome.
  L'API vérifie œuvre, catégorie, ISBN et provenance ; conflit → HTTP 409.
  PostgreSQL garantit les mêmes invariants par clés étrangères composites.

L'API retourne `ownership_mutations: 0`. Elle **ne crée pas** de tomes
possédés ni de statistiques « publiés » ; seuls les ISBN explicitement
enregistrés et liés sont énumérés. Aucun parcours UX supplémentaire n'est
ajouté dans cette étape fonctionnelle V1.

## Sécurité et recette

- Migration idempotente ajoutant des tables et un index d'identité ; aucune
  mise à jour, suppression ou remplacement de `manga_fr_edition` et des
  tables `user_manga_*`. La migration exige au préalable la présence du
  schéma de collection déjà existant.
- Tests : validité des confirmations, collisions de clé, mauvaise œuvre,
  incompatibilité de catégorie ou d'ISBN, absence de provenance, double
  liaison, lecture sans écriture et protections SQL.
- Un scénario PostgreSQL / API HTTP en CI jetable vérifie les liens
  effectivement créés et l'absence de changement des statuts privés.
- Une recette réelle de l'installation Windows et des notices fournisseur
  est **reportée** ; ces tests ne peuvent attester la qualité des 99
  candidats BnF, des sources Scrinis ou de l'inventaire réel.

Voir aussi [rapprochement bibliographique](../03_technical/rapprochement_bibliographique_v2.md)
et [issue #71](https://github.com/xavrousseau/mangadvisor/issues/71).
