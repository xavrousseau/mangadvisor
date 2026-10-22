# Pilote bibliographique FR — BnF + Scrinis

Date : 22 octobre 2026. Branche : `cleanup/pipelines-2026-10-21`.

## Objectif et sécurité

Traiter **1 à 10 mangas par lot**, comparer les ISBN BnF candidats avec les ISBN
français papier de Scrinis pour des œuvres dont le rapprochement préalable
Scrinis est suffisamment étayé. Le rapport ne certifie jamais une édition.

Le pipeline écrit uniquement :
- `manga_bnf_candidate` et `manga_bnf_attempt` (BnF brut, candidat) ;
- les tables existantes `manga_scrinis_fr_fact`, `manga_scrinis_fr_attempt`
  et `manga_title_alias` pour les titres français Scrinis vérifiés.

**Jamais** `manga_fr_edition`, `user_manga_volume`,
`user_manga_inventory_declaration` ou les possessions personnelles.
Les références douteuses restent disponibles pour examen. La recherche
BnF 3 pages par titre est le défaut. Au-delà, un unique manga doit
être désigné explicitement.

## Lancement depuis un conteneur Docker sandbox

Préparer le moteur :

```powershell
git pull origin cleanup/pipelines-2026-10-21
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml build engine
```

Tests :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m unittest discover -s tests -p test_bibliography_pipeline.py -v
```

Rapport seul pour Berserk déjà enrichi, **sans appel réseau ni écriture** :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m pipelines.engine.scripts.bibliography_pipeline --manga-ids 2 --report-only
```

Pilote 5 mangas :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m pipelines.engine.scripts.bibliography_pipeline --limit 5 --pages 3
```

Berserk ciblé avec pagination étendue :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m pipelines.engine.scripts.bibliography_pipeline --manga-ids 2 --pages 10
```

## Menu normal (hors sandbox)

Dans `mangadvisor.cmd` : A → 23, option de lot bornée, sauvegarde
et confirmation obligatoires. **Ne pas utiliser ce menu dans le clone
sandbox** : la configuration et les volumes de son déploiement normal
ne sont pas ceux du sandbox.

## Interprétation

`ISBN_IN_BOTH_SOURCES` : ISBN français papier observé chez Scrinis
pour une œuvre préalablement rapprochée, et candidat BnF. Cela corrobore
l'ISBN mais ne garantit pas l'édition ni le tome sans revue.

`BNF_ONLY_NOT_PROOF_OF_ABSENCE` : pas observé dans le détail Scrinis
collecté ; Scrinis peut avoir une couverture incomplète.

`DIFFERENT_WORK` : exclure du manga visé, conserver la notice brute.

`DERIVATIVE_REVIEW` : ouvrage connexe distinct de la série de tomes.

`NO_VERIFIED_SCRINIS_WORK` : aucune preuve d'identité Scrinis exploitable ;
aucun appariement inter-sources effectué.

Le rapport reste une **évidence de source**, pas une table d'éditions
définitives. Phase suivante : persistance versionnée des associations
œuvre/édition/tome/ISBN après validation et revue des ambiguïtés.
