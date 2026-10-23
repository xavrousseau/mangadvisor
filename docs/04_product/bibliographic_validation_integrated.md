# Recette intégrée du moteur bibliographique (2026-10-22)

## Objet
Pilote conservateur de rapprochement **œuvre MAL → candidats BnF → indices Scrinis → édition / tome / ISBN**. Il n'enregistre **aucune édition certifiée** ni **aucune possession**. Les mentions `REVIEW_*` sont des suggestions documentaires et non des validations.

La base de référence internationale MAL/Tenrai et la collection utilisateur ne sont pas réinitialisées. Les ISBN sont des références de publication; l'ISBN possédé ne peut être déduit d'un titre ni d'une correspondance de sources.

## Architecture et limites

- **MAL/Tenrai** : identité canonique et auteurs de l'œuvre. Un identifiant MAL externe contradictoire est un signal bloquant.
- **BnF** : notices publiques `manga_bnf_candidate`, avec ISBN, titre, auteur, éditeur, langue enregistrée et lien de provenance. Un résultat de recherche par titre reste un candidat.
- **Scrinis** : recherche publique d'œuvre, détail, auteurs, ISBN de livres FR imprimés. Le rapprochement exige un MAL ID concordant ou titre exact **et** auteur concordant, puis un ISBN imprimé en français.
- **Recoupement** : `ISBN_IN_BOTH_SOURCES` est une corroboration bibliographique, **pas** une preuve d'édition ou de possession. Une absence d'ISBN Scrinis ne prouve pas que le tome n'existe pas.
- **Œuvres ambiguës** : candidates concurrentes réexaminées si l'ensemble est petit et complet; sinon `AMBIGUOUS`. Aucun rapprochement forcé.
- **Éditions** : une mention « prestige », « deluxe », « perfect », « collector » ou « intégrale » suggère une catégorie. L'absence de mention donne `UNKNOWN`, jamais automatiquement `CLASSIC`.
- **Numéros de tomes** : extraction de notations explicites ou d'un nombre borné placé après un titre fiable; jamais une preuve de l'édition.
- **Couverture fournisseur** : Scrinis expose un nombre de volumes borné dans l'adaptateur; `INCOMPLETE_SUPPLIER_DETAIL` indique qu'un lot peut être incomplet. Aucun faux négatif ne doit résulter d'une référence tronquée.
- **Réponses volumineuses** : téléchargement HTTP en flux, plafonné à 8 Mo de JSON décompressé pour les détails Scrinis; les autres demandes restent limitées à 600 ko. Une réponse au-delà de la limite est signalée, pas tronquée arbitrairement en JSON valide.
- **Débit** : le client conserve un délai de 4,5 s entre les appels Scrinis, et met les résultats publics valides en cache 24 h. La documentation de Scrinis annonce 15 requêtes/minute anonymes (ce plafond peut évoluer).

## Modes d'exécution

### Parcours conseillé — une seule opération sous Windows

Lancer `mangadvisor.cmd` → **A (Options avancées) → 24 (Recette bibliographique complète)**.
Cette action n'utilise que `.env.sandbox`, `docker-compose.sandbox.yml` et la base
`mangadvisor_realtest`. Elle produit automatiquement **deux rapports JSON** sous
`data/logs/bibliography_validation/` : l'audit BnF sans réseau puis la sonde
Scrinis réelle. Une seule confirmation est demandée avant les appels.
La sandbox doit déjà contenir la base de recette et les 99 candidats importés.

Les commandes ci-dessous sont conservées **pour diagnostic développeur**, pas
comme des étapes à demander une par une à l'utilisateur.

Depuis PowerShell à la racine du dépôt, avec la sandbox PostgreSQL, le mode **rapport uniquement** relit les candidats déjà collectés et ne contacte pas les fournisseurs :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m pipelines.engine.scripts.bibliography_pipeline --manga-ids 49271,11,51119 --report-only --details > rapport_bibliographique.txt
```

Le mode **sonde Scrinis réelle** fait une nouvelle recherche publique ciblée, même si un précédent essai est en cooldown. Il n'appelle **aucun traitement d'écriture BnF ou Scrinis** et ne touche pas aux tables de catalogue ni à la mangathèque :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m pipelines.engine.scripts.bibliography_pipeline --manga-ids 49271,11,51119 --probe-scrinis --details > rapport_sonde_scrinis.txt
```

`--probe-scrinis` exige des `--manga-ids` explicites, exclut `--report-only` et n'exécute pas de nouveau lot BnF. Il ignore le cooldown **seulement pour cette inspection volontaire**, pas pour l'enrichissement automatique normal. Il peut créer un **cache local de métadonnées publiques**, mais n'écrit aucune donnée SQL. Il faut respecter les limitations Scrinis et ne pas l'utiliser en boucle.

Le rapport de la sonde contient, pour chaque œuvre, `scrinis_probe.status`, le motif, les preuves d'identité lorsque confirmées, le nombre d'ISBN FR imprimés détectés et les corrélations ISBN avec la BnF. Les détails de tous les candidats BnF sont ajoutés avec `--details`.

## Interprétation et garde-fous

| Statut | Signification | Action |
| --- | --- | --- |
| `REJECT_DIFFERENT_WORK` | Titre incompatible avec les titres fiables connus | Ne pas rattacher |
| `REVIEW_DERIVATIVE` | Roman / artbook / guide / ouvrage dérivé probable | Revue séparée |
| `REVIEW_VOLUME_CANDIDATE` | Numérotation de tome plausible | Contrôler œuvre, édition, ISBN |
| `REVIEW_EDITION_CANDIDATE` | Indice textuel d'édition | Contrôler édition et tome |
| `REVIEW_UNNUMBERED` | Titre plausible non numéroté | Ne pas déduire de tome |
| `AMBIGUOUS` | Plusieurs œuvres Scrinis possibles | Ne pas associer |
| `DETAIL_UNAVAILABLE` | Détail inaccessible ou incomplet | Revoir, sans écriture |
| `ISBN_IN_BOTH_SOURCES` | Deux fournisseurs mentionnent cet ISBN après vérification de l'œuvre Scrinis | Corroboré seulement |

### Contrôle des contradictions d'édition et de tome (octobre 2026)

Une concordance d'ISBN peut désormais être contredite par la fiche détaillée
Scrinis elle-même. Lorsqu'une référence imprimée française mentionne une
**famille d'édition différente** (p. ex. Deluxe contre Pastel) ou un
**numéro de tome différent** de la notice BnF, la corrélation est marquée
`ISBN_EDITION_CONFLICT_REVIEW` ou `ISBN_VOLUME_CONFLICT_REVIEW`.
Un ISBN présenté par Scrinis dans plusieurs éditions ou tomes divergents
est `ISBN_SUPPLIER_REFERENCE_CONFLICT_REVIEW`.

Le champ `edition_volume_evidence` précise le niveau de cohérence; même
`FAMILY_AND_TOME_CONSISTENT_UNVERIFIED` reste une simple preuve de
référence, **sans valider la possession ni écrire un tome canonique**.
La préparation des rapports V2 signale également les collisions entre
différentes œuvres candidates, familles et tomes sous
`isbn_conflict_count` et `isbn_conflicts_sample` (max. 20 détails).
Ces contrôles utilisent des métadonnées de publication et ne modifient
pas les tables personnelles.

Le libellé `confirmed_editions_written=0` et `user_inventory_written=0` reste le comportement voulu de ce pilote. La création de tables œuvre / édition / tome / ISBN certifiées nécessitera un workflow de validation et des preuves complémentaires, distinct de la présente recette.

## Validation attendue avant fusion

1. `python -m compileall -q apps/api pipelines/engine tests` ;
2. `python -m unittest discover -s tests -p 'test_*.py' -v` ;
3. CI GitHub Actions Python et intégration jetable ;
4. Rejouer **une fois** les deux commandes ci-dessus sur la sandbox locale, puis examiner les 99 candidats et la réponse réelle Scrinis de Chainsaw Man, One Piece et Solo Leveling ;
5. Vérifier que les tables `manga_fr_edition` et `user_manga_*` restent inchangées.

Les tests simulés valident les règles, pas le comportement actuel de l'API externe ni la couverture complète du catalogue. Le pilote ne doit pas être déclaré « production prête » avant la recette réelle.
