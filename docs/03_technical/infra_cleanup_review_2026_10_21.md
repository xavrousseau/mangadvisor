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
