# Mangadvisor — Réconciliation bibliographique fondée sur les preuves (V1)

## Portée de l'audit — phases A à D

Ce document décrit ce qui est effectivement codé et ce qui reste à prouver sur
la collection physique. Il ne suppose pas que 2 titres égaux désignent la même
œuvre ou le même livre.

### A. Inventaire des chemins de données existants

| Niveau | Stockage / rôle actuel | Limites et risques |
| --- | --- | --- |
| Identité d'œuvre | `manga.id`, `manga.source_mal_id` alimentés par Jikan | Une œuvre non indexée par MAL ne possède pas automatiquement de fiche `manga` exploitable par l'inventaire |
| Titres/alias | `manga.title*`, `manga_title_alias` avec `source_name`, `source_id` et langue | Des sources ont pu attribuer un alias à une mauvaise œuvre; un alias exact ne constitue pas une clé d'identité |
| Liens documentés | `manga_wikidata_fact` (P4087), `manga_scrinis_fr_fact` et découverte MangaDex via `links.mal` | Chaque source a sa propre logique de validation; éviter de compter deux reprises d'une source comme deux attestations indépendantes |
| ISBN proposés | `manga_bnf_candidate`, `bib_stage_*` | Les candidats de recherche BnF et Scrinis ne sont ni certifiés pour l'œuvre canonique ni possédés |
| Livre enregistré | `manga_fr_edition`, `manga_fr_edition_group*` | Une référence enregistrée ne prouve pas un exemplaire possédé |
| Collection | `user_manga_inventory_pending`, `user_manga_inventory_declaration`, `user_manga_volume`, `user_manga_library` | Une quantité de livres ne précise pas les ISBN, tomes ou éditions réellement présents |

Les procédures existantes ne sont pas supprimées. Le registre
`user_manga_inventory_resolution` préserve la confirmation humaine et
les originaux. Les 48 déclarations non résolues observées dans un export
local utilisateur ont révélé 34 recherches sans candidat exact,
8 noms ambigus et 6 candidats exacts uniques dont certains faux positifs.
**L'export privé n'est jamais ajouté au dépôt ou à la CI.**

### B. Modèle de preuve et de relation

`apps/api/app/reconciliation_engine.py` produit pour chaque candidat :

- `evidence[]` : nature, source, signification (titre canonique, alias, lien
  d'identifiant P4087, ancien rapprochement);
- `alias_provenance[]` : `source_name` et `source_id` persistés; la source
  peut être connue sans que l'association elle-même soit irréfutable;
- `warnings[]` : alias contradictoire, source non traçable, type dérivé,
  one-shot, volume du catalogue très inférieur à la quantité déclarée;
- `assessment` : `IDENTITY_EVIDENCE_REVIEW`, `CONFLICT_REVIEW` ou
  `DISCOVERY_ONLY`. **Aucun état ne signifie association automatique.**
- `bibliography` : nombre et échantillons d'ISBN BnF **candidats** séparés
  des livres ISBN **déjà enregistrés**. Les deux niveaux restent distincts
  des livres physiquement possédés.

La valeur de `manga.volumes` concerne l'œuvre référencée par le catalogue
international; elle **n'est jamais utilisée comme équivalent direct des tomes
français possédés**. Un grand désaccord n'est qu'une alerte.

Le bon modèle conceptuel est :

`Œuvre canonique ←(preuve de source)→ noms/identifiants externes`

`Œuvre canonique ←(preuve d'édition)→ série d'édition ←→ livre/ISBN`

`Livre/ISBN ←(confirmation propriétaire)→ exemplaire possédé`

Une suite, un guide, un roman ou un dérivé peuvent être **reliés par type**
mais pas fusionnés au seul motif de partager un titre. Une œuvre sans identifiant
MAL doit rester une entité source indépendante tant qu'elle n'a pas sa propre
identité canonique. **Ce dernier raccordement au catalogue principal n'est pas
encore implémenté : aucune identité MAL factice n'est créée.**

### C. Recherche approfondie et croisement

- `GET /inventory/pending/triage` : rapprochement exact des titres canonisés
  Jikan, alias sourcés, libellés français Wikidata liés à MAL, anciennes
  propositions d'import; bilan par candidat, risque, ISBN candidats/
  enregistrés. Lecture seule.
- `GET /inventory/pending/discover?source_key=...` : recherche bornée des
  mots discriminants du titre, **uniquement** pour suggérer une liste locale.
  Une coïncidence de mot est `DISCOVERY_TOKEN_ONLY`, jamais une preuve.
- `GET /inventory/pending/discover?source_key=...&include_bnf=true` :
  déclenche explicitement une recherche BnF de notices papier; résultats
  `BOOK_NOTICES_UNVERIFIED`. Ne transforme pas des ISBN en possessions.
- `GET /inventory/pending/external-candidates?source_key=...&q=...` :
  découverte existante MangaDex + identifiant `links.mal` vérifié, toujours
  soumise au contrôle de l'œuvre et de l'édition.

Toutes ces routes sont limitées au propriétaire local courant, sans migration
SQL, sans écriture de données, sans déclenchement des pipelines Jikan, ni appel
Internet tacite. Le catalogue public, les volumes et les secrets restent
inchangés.

### D. Mesure et validation

Le jeu utilisateur initial (`/inventory/pending/triage` avant réconciliation)
était : 48 = 34 `SEARCH_REQUIRED` + 8 `AMBIGUOUS_EXACT` +
6 `SINGLE_EXACT_SUGGESTION`. Ce sont des catégories algorithmiques,
**pas 48 identités de référence vérifiées**.

Les tests non privés doivent prouver a minima :

1. l'alias parasite « Radiant » d'une œuvre d'un seul volume est marqué
   incohérent pour une grande collection, et n'est pas accepté;
2. un alias « Fairy Tail » parasite n'éclipse jamais le titre canonique
   identique, et une light novel n'est pas confondue avec un manga;
3. un titre connu seulement via Wikidata/P4087 peut être trouvé mais
   n'implique ni édition ni ISBN possédé;
4. une recherche approfondie « Adieu Eri » peut exposer « Sayonara Eri »
   *en tant que proposition lexicale* sans déclarer une identité;
5. les ISBN BnF candidats ne deviennent jamais des ISBN enregistrés/
   possédés;
6. les API sur PostgreSQL CI sont en lecture seule et laissent les tables
   `user_manga_*` inchangées.

**Seuil de validation produit non atteint par les seuls tests techniques :**
contrôler un échantillon des 48 vrais cas, leurs identifiants et leurs sources
réelles, comparer les faux positifs, puis valider séparément les éditions et
ISBN. L'outil ne peut pas mesurer automatiquement la précision sans
annotations humaines fiables. Le test Docker CI ne démontre pas la justesse
des 48 correspondances réelles.

## Contraintes de déploiement

Le dépôt `main` et la base utilisateur ne doivent pas être modifiés avant
validation de la PR. Aucune commande de remise à zéro Docker, aucune
réimportation de Jikan et aucune mise à jour des volumes n'est requise pour
ce diagnostic. Le code est testé via `tests/test_reconciliation_engine.py`,
`tests/test_inventory_resolution.py` et la recette intégrée Docker/
PostgreSQL GitHub Actions.
