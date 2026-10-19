# Mangadvisor — Audit technique du dépôt (19 octobre 2026)

## Périmètre et méthode

Inventaire de **300 fichiers suivis** sur `main` via l'arbre GitHub, couvrant les fichiers actifs, les tests, les documents, les sauvegardes historiques et le répertoire `legacy/`. Les fichiers volumineux archivés (dont notebooks binaires/JSON historiques) ont été **inventoriés** ; ils n'ont pas été réexécutés ni relus cellule par cellule. Les contrôles approfondis ont porté sur les points d'entrée et risques actifs :

- `mangadvisor.cmd`, `cmd/*.cmd`, `cmd/ai-setup.ps1`, `cmd/mobile-setup.ps1`.
- Docker Compose (base/dev/mobile), Dockerfiles, Nginx, Caddy, `.env.example`.
- SQL des schémas canoniques, Jikan, bibliothèque et édition.
- API FastAPI et modules conseiller/IA/recommandations, collection française, import CSV, scanner et recherche BnF.
- Interface Web PC/mobile, internationalisation, conseiller et ateliers BnF.
- Tests Python/JS et workflow d'intégration PostgreSQL/Chromium.

**Méthode de validation :** comparaison des chemins d'exécution, des contraintes SQL, des variables Docker, des fonctions appelées et des tests existants. Tests nouveaux de protection contre une destruction de données + exécution réelle de reconstruction SQL sur base jetable GitHub Actions. L'accès au PC et à sa base PostgreSQL personnelle n'est pas disponible ici. Il serait abusif d'affirmer que toutes les configurations Windows, tous les imports réels, tous les ISBN BnF et toutes les cellules de notebooks historiques ont été exécutés.

## Constats critiques confirmés et corrections proposées dans cet audit

### A1 — Reconstruction SQL détruisant la collection (CRITIQUE)
- **Avant :** `sql/schema/003_build_canonical_from_jikan.sql` faisait `TRUNCATE manga_genre, genre, manga RESTART IDENTITY CASCADE`, ce qui supprime par cascade des entrées de bibliothèque, associations ISBN, lectures et autres tables reliées. `005_build_theme_demographic_from_jikan.sql` supprimait aussi toutes les tables de tags correspondantes.
- **Après :** remplacement par des `INSERT ... ON CONFLICT` transactionnels et des relations additives. Les `manga.id` existants restent inchangés. Les champs absents d'une source partielle ne remplacent pas les métadonnées existantes par `NULL`.
- **Limite assumée :** les anciens tags ne sont pas supprimés automatiquement, faute de connaître leur provenance (source Jikan ou enrichissement manuel). Une synchronisation destructive nécessiterait un marquage de provenance et une migration vérifiée.

### A2 — Pipeline Windows Jikan utilisant un faux mot de passe (ÉLEVÉ)
- **Avant :** `cmd/run-jikan-pipeline.cmd` imposait `manga/manga` et la base `mangadvisor`, malgré la présence d'un fichier `.env` et d'identifiants configurables.
- **Après :** aucun identifiant en dur, récupération des vrais paramètres via les variables d'environnement (priorité Docker/CI) ou `.env` local pour les appels Python. En outre, la commande Windows exécute le pipeline dans le conteneur **engine** où ses dépendances Python sont installées.
- Les anciens scripts `.cmd` faisant appel à `psql` utilisent désormais l'utilisateur et la base fournis par le conteneur PostgreSQL, avec arrêt en cas d'erreur SQL.

### A3 — Perte possible des données sources en cas d'échec Jikan (ÉLEVÉ)
- **Avant :** la réinitialisation optionnelle dans le pipeline courant intervenait **avant** l'extraction réseau ; le script historique `run-jikan-catalog.cmd` vidait toujours la table source avant de tenter le chargement.
- **Après :** `--reset-db` attend une extraction réussie ; le script historique se contente d'upserts sources sans vider la table.

### A4 — Jikan rechargé sans catalogue actualisé (MOYEN/ÉLEVÉ)
- **Avant :** l'option Jikan principale ne chargeait que `jikan_manga_source`, sans mettre à jour automatiquement la table `manga` et les relations genres/thèmes nécessaires aux recommandations.
- **Après :** synchronisation additive du catalogue et des tags après chargement source, utilisant les scripts SQL sécurisés ci-dessus.

### A5 — Chargement des recommandations communautaires remplaçant le graphe trop tôt (ÉLEVÉ)
- **Avant :** l'option `--reset` de `load_jikan_recommendations_to_postgres.py` vidait `manga_recommendation_edge` puis commençait à parcourir les fichiers, sans transaction unique avec le rechargement. Un fichier endommagé ou une sortie vide pouvait effacer les anciennes relations.
- **Après :** les fichiers sont lus en premier. Si des fichiers sont corrompus ou si aucune relation valide n'existe, le remplacement est refusé. Pour les données valides, `DELETE` et toutes les insertions/upserts sont effectués dans **la même transaction**, et commit uniquement après l'insertion complète ; un échec SQL n'est pas validé.

## Cohérence des composants existants

| Zone | Constat |
| --- | --- |
| API/recommandations | Moteurs fondés sur les lignes SQL et tags enregistrés ; le conseiller IA ne choisit pas d'ISBN ou de mangas arbitraires. |
| Bibliothèque | Suivis globaux historiques et ISBN français détaillés distincts ; imports conservateurs et confirmations explicites. |
| Éditions françaises | Recherche BnF candidate non exhaustive ; l'association finale exige une recherche exacte ISBN et un choix manuel. |
| Docker et accès | Ports web/API/DB locaux sur 127.0.0.1 en mode dev, partage mobile HTTPS optionnel avec authentification. Pas d'exposition publique prévue. |
| IA | Modèle Ollama facultatif, réseau Docker privé, repli vers le conseiller guidé si indisponible. La qualité du vrai modèle et la RAM doivent être validées sur le PC. |
| Tests | Tests Python et Node ; PostgreSQL jetable et Chromium desktop/mobile. Les workflows vérifient déjà la plupart des parcours web, pas toutes les installations réelles. |
| Documentation | README récent cohérent avec 3.x ; des documents d'architecture de V0/V1 décrivent encore des composants prévus (AniList, MangaNews, embeddings et Meilisearch actifs) qui ne correspondent pas tous à l'implémentation actuelle. À marquer explicitement comme historique, non état actuel. |
| Archives | `_archive/` et `legacy/` occupent une partie importante des 300 fichiers. Ils ne sont pas exécutés par le démarrage courant ; les laisser séparés de la documentation et des commandes de production. |

## Risques non résolus et travail restant

1. **Sauvegardes :** les volumes PostgreSQL sont persistants, mais la persistance n'est pas une sauvegarde externe. Mettre en place un export/restauration et tester la restauration sur une base jetable avant toute migration ou nettoyage important.
2. **Qualité des données :** certaines recommandations dépendent de tags Jikan incomplets ; l'absence de tag horreur/gore n'est pas une certification d'innocuité. Les pages BnF ne sont pas un inventaire exhaustif ni un stock vendeur.
3. **Bibliographie et imports réels :** valider les correspondances sur les vrais ISBN et un vrai export MangaCollec.
4. **IA locale :** vérifier le téléchargement et les performances du modèle sur le PC Windows et avec le matériel réel ; GitHub Actions n'exécute pas l'inférence lourde.
5. **Documentation ancienne :** annoter/refondre les schémas d'architecture V1 qui parlent encore de Streamlit comme interface principale, de pipelines AniList/MangaNews ou d'embeddings pas effectivement branchés. Le README courant doit faire autorité.
6. **Versions et dépendances :** `pyproject.toml` conserve une version de paquet V0.1 ; les dépendances Python ne sont pas épinglées, ce qui peut créer des différences d'installation dans le temps. Prévoir une stratégie de gel/actualisation contrôlée.
7. **Sécurité :** l'accès LAN HTTPS reste à activation explicite ; éviter toute ouverture directe des ports API/PostgreSQL vers Internet et remplacer les secrets d'exemple par de vraies valeurs locales.

## Tests de non-régression ajoutés

- `tests/test_repository_safety.py` : interdiction de `TRUNCATE` / `DROP TABLE` dans les reconstructions canoniques, configuration réelle des identifiants, priorité de l'environnement et refus d'un mot de passe absent. Vérification supplémentaire : refus de remplacer un graphe Jikan par des données vides et absence de commit après une erreur d'insertion.
- `tests/smoke/rebuild_safety_smoke.py` : sur **mangadvisor_ci / manga_ci exclusivement**, mise à jour répétée du catalogue Jikan, conservation stricte de la correspondance identifiants manga, bibliothèque, ISBN et statuts de lecture, ajout/idempotence des liens tags. CI interdite sur une base personnelle.

## Conclusion

**Mangadvisor est une application en développement avancé et fonctionnel, non un produit achevé et certifié intégralement.** Le risque le plus sérieux détecté résidait dans l'entretien du catalogue, qui pouvait écraser la bibliothèque. Ces corrections privilégient la conservation des données et rendent le pipeline Windows cohérent avec Docker. Les fonctionnalités existantes restent conservées. L'acceptation définitive exige des tests CI réussis et une validation de fonctionnement sur le poste utilisateur.
