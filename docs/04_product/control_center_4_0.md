# Mangadvisor 4.0 — Centre de pilotage Windows

**Objectif : tout faire depuis le seul fichier mangadvisor.cmd**, sans installer Python localement ni taper des commandes SQL, Docker ou PowerShell. Docker Desktop est requis. Git pour Windows est facultatif (utile pour les mises à jour d'un clone Git).

## Installation complète — option 22

1. Télécharger le projet via GitHub (ZIP ou clone Git), puis démarrer Docker Desktop en mode Linux.
2. Double-cliquer sur **mangadvisor.cmd**, sélectionner **22 — Installation complète**.
3. La configuration privée **.env** est générée uniquement si absente, à partir de **.env.example**, avec deux clés aléatoires distinctes pour PostgreSQL et Meilisearch. Les répertoires privés **backups/** et **private-data/** sont créés.
4. Démarrer PostgreSQL et Meilisearch, attendre la disponibilité de la base et appliquer les scripts SQL **001 → 002 → 004 → 006 → 007** (tables sources, catalogue, tags, recommandations, bibliothèque). Ces créations sont additives.
5. Construire les images Docker et démarrer l'API **et l'interface unique Web (8501)**, qui initialisent de manière additive les tables des éditions françaises et de l'inventaire. Arrêter sans supprimer l'ancienne UI Streamlit 8502 si elle existait.
6. **Extraction manga via Tenrai (scripts historiques Jikan)** : choisir les pages SEARCH et TOP (40 et 10 par défaut, 25 notices maximum par page). Les scripts extraient les JSON dans **data/raw/jikan/search/** et **data/raw/jikan/top/**.
7. **Chargement SQL Jikan** : exécuter le chargeur des sources search et top, puis les reconstructions SQL **003 → 004 → 005** pour remplir **jikan_manga_source**, **manga**, **genre**, **manga_genre**, **theme**, **manga_theme**, **demographic** et **manga_demographic**. Ces mises à jour ne vident pas le catalogue.
8. **Recommandations communautaires** : extraire les relations Jikan entre œuvres puis les charger dans **manga_recommendation_edge** ; 50 mangas à enrichir par défaut. Les données déjà téléchargées peuvent être réutilisées.
9. **Diagnostic** : vérifier la santé API, PostgreSQL, les compteurs SQL, une recherche, l'ouverture du site Web **et ses appels API réels via Nginx** (santé + bibliothèque).
10. **Sauvegarde vérifiée** : créer un dump PostgreSQL et valider une restauration de test dans une base isolée.
11. **Import facultatif de collection** : placer un fichier CSV compatible dans **private-data/mangatheque.csv**. Un aperçu est exécuté sans écriture. L'import réel exige ensuite deux confirmations et exclut les titres ambigus ou non reconnus.
12. Nouveau diagnostic, puis **sauvegarde finale automatique vérifiée**, y compris si une bibliothèque vient d'être importée. Copier ensuite les archives sur un autre support.

Une réinstallation est **non destructive par défaut** : elle ne supprime ni volume Docker, ni configuration .env existante, ni données de la mangathèque. Pour repartir d'une base vierge malgré des données existantes, sauvegarder d'abord avec 17 puis utiliser **11 — Nuke** séparément et volontairement. **11 est irréversible sans sauvegarde**.

### Menu de pilotage

| Option | Action | Données modifiées |
|---|---|---|
| **22** | Assistant d'installation complet : environnement, SQL, données, app, import, diagnostic | Oui, sauf lecture seule/confirmation |
| **23** | Configurer les secrets et les répertoires privés | .env seulement si absent |
| **24** | Initialiser/réparer les tables SQL | Création additive |
| **25** | Extraire et charger le catalogue Tenrai | Upserts catalogue, sans reset |
| **26** | Extraire et charger les recommandations communautaires | Upserts relations, sans reset |
| **27** | Diagnostiquer bases et application | Lecture seule |
| **28** | Sauvegarde vérifiée, mise à jour Git, rebuild Docker, diagnostic | Préserve les volumes |
| **29** | Vérification DNS et accès HTTPS depuis le conteneur Docker vers Tenrai et un site témoin | Lecture seule |
| **17 à 19** | Sauvegarder, revérifier, restaurer après confirmation | Restauration seulement sur demande |
| **20 et 21** | Simuler la collection, importer après aperçu et confirmation | Option 21 uniquement |
| **13 à 16** | Scanner mobile HTTPS et IA Ollama locale optionnelle | Aucun effacement de bibliothèque |
| **1 à 10** | État, build, démarrage, arrêt, logs, nettoyage standard | Option 10 conserve les volumes |
| **11** | Nuke explicite | **DESTRUCTIF : supprime les volumes Docker** |

## Mise à jour en un clic — option 28

Sur un clone Git, l'option 28 refuse les changements non enregistrés sur les fichiers suivis, effectue une **sauvegarde avec restauration de test**, lance un git pull en avance rapide uniquement, réapplique les schémas additifs, reconstruit les services et termine par un diagnostic. Les collections et volumes sont préservés. Docker et l'application doivent être démarrés avant cette option pour permettre la sauvegarde. Avec une installation ZIP, la mise à jour Git automatique n'est pas disponible ; l'outil l'indique.

## Tests, limites et données françaises

L'import CSV conserve les déclarations physiques par édition mais ne prétend pas connaître les ISBN, les volumes lus, les notes ou la complétude. Les ISBN français sont recherchés et vérifiés séparément via la BnF ; **il n'existe pas encore de chargement complet automatique de toutes les éditions françaises**. Les anciennes propositions de pipelines AniList, MangaNews, embeddings et indexation exhaustive Meilisearch ne sont pas toutes implémentées dans ce parcours et ne sont pas annoncées comme exécutées.

Le diagnostic contrôle l'infrastructure réelle, mais pas la qualité artistique des recommandations ni l'identification certaine de tous les titres. Vérifier les fiches, les couvertures, la correspondance des mangas de ta collection, les éditions et les exclusions des recommandations dans l'interface. Une CI GitHub réussie ne remplace pas un test du PC.

En cas d'échec Jikan (réseau ou quotas), relancer l'option 25 sans suppression. En cas d'échec SQL, corriger puis relancer 24. Pour un inventaire non reconnu, enrichir le catalogue avant d'importer plutôt que d'inventer une correspondance. L'option 6 donne accès aux logs et 27 permet de reprendre les contrôles.

## Erreur : Network is unreachable / impossible de joindre Jikan

Si l'extraction affiche **Errno 101 : Network is unreachable**, c'est le conteneur Docker **engine** qui n'a pas pu joindre Internet. Ce n'est ni une erreur PostgreSQL ni une limite de quota Jikan. Le chargement est interrompu sans suppression des volumes.

Le centre de pilotage vérifie désormais le réseau **avant les options 25 et 26**, et propose aussi **29 — Diagnostic réseau Docker/Jikan** à la demande. Ce contrôle est en lecture seule et teste DNS + connexion TCP/TLS vers api.jikan.moe, ainsi qu'un site témoin : il ne change aucune configuration réseau.

Pour dépanner : ouvrir https://api.jikan.moe/v4/manga?page=1&limit=1 dans le navigateur de Windows. Si Windows arrive à joindre Jikan mais pas Docker, essayer **Docker Desktop > Troubleshoot > Restart Docker Desktop**. Si nécessaire, examiner **Docker Desktop > Settings > Resources > Proxies** et les règles VPN/pare-feu. Si ni Windows ni Docker ne peuvent joindre le site, corriger d'abord l'accès du PC. Relancer **29**, puis **25** lorsque l'accès HTTPS de Jikan est confirmé. **Ne pas utiliser 11/Nuke** pour une erreur réseau.

## Source du catalogue manga depuis le 1er octobre 2026

**Attention :** le fournisseur public Jikan `api.jikan.moe` a officiellement été arrêté le 1er octobre 2026 ([annonce des mainteneurs](https://github.com/jikan-me/jikan-rest/issues/613)). Mangadvisor utilise désormais **[Tenrai v1](https://api.tenrai.org/documentation)**, qui documente un format compatible avec Jikan pour les recherches et les recommandations mangas.

L'URL `https://api.tenrai.org/v1` est utilisée automatiquement, **même si ton ancien fichier .env ne comporte pas encore la nouvelle variable**. Si besoin, elle peut être définie dans `.env` via `MANGA_API_BASE_URL=https://api.tenrai.org/v1`. Aucune clé payante n'est nécessaire, les limitations publiques restent applicables (120 appels/minute, 4 appels/seconde). Le fournisseur est encore en bêta : une coupure est possible.

Les scripts historiques dont le nom contient « Jikan » et les dossiers `data/raw/jikan/` sont conservés pour compatibilité avec les bases et tests déjà existants, **mais les nouveaux JSON enregistrent le fournisseur réel** ; les écritures SQL conservent également `source_name=tenrai`. Le chargement est additif et les associations aux mangas existants restent basées sur les identifiants MyAnimeList (`mal_id`).

L'option **29** vérifie dorénavant la connexion HTTPS au fournisseur configuré **et une vraie réponse manga JSON**. Après mise à jour, relancer 29 puis 25 pour charger le catalogue, 26 pour les recommandations. Aucune réinstallation ni suppression de volume n'est requise.


## Dédoublonnage de Mangadvisor 4.1

L'ancien sous-menu Jikan (option 12) a été fusionné fonctionnellement avec l'option 25, sans changer les numéros des autres options. Taper 12 ou utiliser l'alias historique `jikan` renvoie à l'ingestion centrale Tenrai ; la commande `jikan-reset`, dangereuse pour les données, est désormais refusée. Les anciens lanceurs autonomes Windows nécessitant Python sur le PC ont été retirés. Les commandes du centre de pilotage restent la référence ; voir le [rapport de nettoyage](../03_technical/cleanup_4_1.md).

## Interface unique et réparation HTTP 502 (4.2)

Le site utilisateur est exclusivement **http://localhost:8501**. L'ancien Streamlit **8502** reste présent en code uniquement pour les tests ; `docker compose --profile legacy up ui` est réservé au développement et non requis par le menu Windows. Les options de démarrage standard et le centre de pilotage arrêtent proprement toute ancienne instance 8502 sans effacer ses données.

Si l'API est recréée après Nginx, son adresse IP peut changer sur le réseau Docker. Le proxy Web utilise désormais `resolver 127.0.0.11` pour rafraîchir automatiquement cette adresse tout en retirant le préfixe `/api` et en préservant les paramètres d'URL. L'option **27** distingue maintenant trois cas : API directe indisponible, site HTML indisponible, ou proxy / bibliothèque indisponible (dont `HTTP 502`). Aucune purge Docker n'est nécessaire.

## Stabilisation 4.4 (API, sauvegarde et bibliothèque)

Le site Web attend dorénavant le **healthcheck réel** de FastAPI (connexion PostgreSQL), et le diagnostic 27 conserve son contrôle du proxy Nginx. L'option 17 de sauvegarde vérifie aussi, dans la base temporaire restaurée, les tables `user_manga_inventory_declaration` et `user_manga_inventory_pending` si elles figurent dans l'archive. Un ancien outil indépendant utilisant `--reset-db` est explicitement bloqué. La page « Ma bibliothèque » sépare statut, éventuelle note et nombre d'exemplaires physiques **déclarés** ; aucun ISBN n'est inféré.

Le nom affiché suit la priorité **titre français explicitement vérifié (si disponible) → titre anglais fourni par la source → titre principal → titre japonais**. À ce jour, il n'existe pas de registre général de titres français officiellement vérifiés ; les couvertures peuvent être celles des éditions japonaises. Voir le [rapport d'audit et la suite](../03_technical/audit_transversal_4_4.md).
