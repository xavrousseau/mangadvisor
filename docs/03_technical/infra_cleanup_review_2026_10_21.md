# Audit de nettoyage — infrastructure (21 octobre 2026)

> Revue statique de la branche `cleanup/pipelines-2026-10-21`. Aucune suppression de volume, aucun déploiement sur le PC personnel. La CI a validé les contrôles automatisés du lot précédent, mais cette revue n'atteste pas l'état réel des volumes Windows.

## Inventaire et décisions proposées

| Fichier | Fonction observée | Décision |
|---|---|---|
| `infra/compose/docker-compose.yml` | Services PostgreSQL, Meilisearch, API, Web, moteur ponctuel ; catalog-sync et Ollama sous profils | Conserver et clarifier les services réellement utilisés |
| `infra/compose/docker-compose.local.yml` | Ports liés à 127.0.0.1 et montages ciblés des données d'extraction pour l'usage stable | Conserver |
| `infra/compose/docker-compose.dev.yml` | Code monté avec rechargement Uvicorn ; Streamlit uniquement sous profil `legacy` | Conserver tant que les tests/migrations en dépendent |
| `infra/docker/api/Dockerfile` | Image FastAPI et dépendances API | Conserver |
| `infra/docker/engine/Dockerfile` | Python pour collecte, traitement et synchronisation du catalogue | Conserver |
| `infra/docker/web/Dockerfile` | Image Nginx et fichiers Web | Conserver |
| `infra/docker/ui/Dockerfile` | Ancien prototype Streamlit, utilisé uniquement dans l'overlay développement | À réévaluer avec `apps/ui/`, pas à supprimer isolément |

## Constats de dette technique

1. **Meilisearch :** déclaré dans Compose, démarré avec les services courants et requis au démarrage de l'API. Son indexation et ses consommateurs applicatifs doivent être prouvés avant d'en faire une dépendance obligatoire. Ne jamais supprimer le volume `mangadvisor_meili` pendant l'audit.
2. **Service `engine` :** son `command: ["python", "--version"]` est volontairement neutre. Ce n'est pas un démon qui assure l'alimentation ; le centre de pilotage exécute les scripts dans des conteneurs ponctuels. Ne pas le présenter comme un service d'indexation autonome.
3. **`catalog-sync` :** profil `automation`, exécute `catalogue_lifecycle.py --daemon` avec montage local du dépôt. Sa configuration a des implications de reproductibilité et de gestion des arrêts/sauvegardes ; préserver le comportement validé avant tout remaniement.
4. **Ancien Streamlit :** `ui` n'existe pas dans Compose stable. Sa suppression éventuelle doit être traitée avec `apps/ui/`, les tests, les dépendances Python et l'overlay `dev` dans le même lot.
5. **Dépendances :** `pipelines/engine/requirements.txt` contient des versions non verrouillées et inclut `pandas` et `fastapi`. Inventorier les imports réels avant retrait, puis verrouiller un ensemble compatible et vérifier la CI.
6. **Commentaires :** les mentions d'une indexation Meilisearch ou d'embeddings déjà fonctionnels ne sont pas une preuve d'exécution. Les descriptions doivent distinguer prévu et actif.

## Règles de nettoyage

- Aucune commande `docker compose down -v`, suppression de volume, reset SQL, ni effacement de `data/raw`, `data/logs`, `backups` ou `private-data`.
- Ne pas retirer un Dockerfile, service ou dépendance sans rechercher ses appels dans le menu, les workflows et les tests.
- Conserver l'accès local aux ports et le démarrage de l'interface Web 8501 ; ne pas réintroduire l'ancien Streamlit dans la configuration stable.
- Exécuter ensuite des tests de non-régression sur une base jetable avant toute fusion dans `main`.

## Décision à ce stade

Aucune suppression d'infrastructure n'est justifiée par la seule revue statique. La prochaine passe doit d'abord démontrer les usages réels de Meilisearch, des dépendances et de l'ancienne UI avant de proposer des retraits.

## Résultat de la deuxième passe

- Recherche des références `MEILI_HOST` : aucune utilisation métier trouvée dans `apps/api/` ou `pipelines/` ; la variable n'apparaît que dans la configuration Compose et la documentation. **Le moteur de recherche réellement exposé au public ne doit pas être annoncé comme Meilisearch.** Le service et son volume sont conservés pour ne pas changer l'infrastructure sans stratégie de migration.
- `apps/ui/` contient encore un prototype Streamlit de plus de 35 ko et des fonctions testées directement par `tests/test_discovery.py` et `tests/test_recommendation_view.py`. Suppression **reportée**, car elle ferait perdre des tests et demande une comparaison fonctionnelle avec le Web actuel.
- Aucun import `pandas` dans les scripts `pipelines/` identifiés : la dépendance `pandas` a été retirée de `pipelines/engine/requirements.txt`. Le prototype `apps/ui/app/app.py` utilise encore `pandas` de façon conditionnelle pour son import Excel ; ce composant doit être analysé à part.
- `fastapi` est conservé dans l'image moteur : le synchroniseur charge des modules de `apps/api/` qui peuvent importer ce paquet ; retirer ce paquet sans tests serait prématuré.
- Les commentaires de `infra/compose/docker-compose.yml` ont été corrigés pour distinguer les services déclarés des fonctionnalités réellement branchées.

### Suite

Valider les workflows GitHub Actions du dernier commit. Ensuite comparer les fonctions Streamlit encore exclusives (notamment import Excel, centre de recommandations) avec leurs équivalents Web avant toute suppression du dossier `apps/ui/` ou du Dockerfile associé.

## Pré-audit `apps/ui/` versus `apps/web/`

Le prototype Streamlit contient encore `discovery.py` (normalisation et pagination du catalogue) et `recommendations.py` (présentation des recommandations). Les tests `test_discovery.py` et `test_recommendation_view.py` importent ces fonctions. L'interface Web actuelle fournit déjà des parcours de découverte, fiche et recommandations via `apps/web/assets/app.js`, `advisor-view.js` et les modules de collection ; **cela ne démontre pas à lui seul une équivalence fonctionnelle**.

Le module principal Streamlit comporte des chemins d'import Excel utilisant `pandas` et `openpyxl`, tandis que l'interface Web possède `bulk-import-view.js` pour ses prévisualisations. Avant retrait, il faut comparer les formats Excel, les capacités d'import et les fonctions de lecture/recommandation sur données factices.

Décision : conserver temporairement `apps/ui/`, `infra/docker/ui/Dockerfile` et le profil `legacy`, puis migrer uniquement les tests réutilisables vers des composants indépendants de Streamlit. Ne pas annoncer le retrait comme terminé.

## Décision finale sur Meilisearch — audit transversal après retrait de Streamlit

**Verdict : configuration présente, consommation métier non démontrée.** Les recherches dans le code de l'API et des pipelines n'ont trouvé aucun usage actif d'un client ou des index Meilisearch. À l'inverse, le service est explicitement requis par les Compose stables et de développement, le centre de pilotage Windows (de nombreuses commandes `up postgres meilisearch`), les contrôles d'installation CI et certains contrats de persistance. Le retirer aujourd'hui n'est pas une simple suppression de dossier.

**Arbitrage pour PR #89 : conserver temporairement le service et surtout le volume nommé `mangadvisor_meili`.** Ne pas annoncer une recherche Meilisearch fonctionnelle. Une désactivation propre devra être traitée à part : enlever les dépendances Docker, adapter les commandes PowerShell, les vérifications CI, les variables `.env` et les guides, avec migration explicite si des index conservés doivent être récupérés. Aucune action `docker compose down -v` ni `docker volume rm` ne devra être utilisée.

**Situation Streamlit :** son code, son image et son profil Docker ont été retirés de la branche de nettoyage après migration des fonctions vers le Web ; les chemins historiques éventuels dans les rapports datés ne constituent pas des appels exécutables. Les suites de tests Python/Windows/Docker stables ont réussi sur ce lot, la validation d'intégration complète du dernier commit reste à confirmer.
