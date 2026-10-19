# Mangadvisor 4.5 — une application visible, un Docker stable

## Décision de référence
Le site utilisateur est **WEB / Nginx sur http://127.0.0.1:8501**. L'API FastAPI et PostgreSQL restent uniques. Le Compose principal n'a plus de service `ui`. Le mode stable local n'active **aucun rechargement à chaud** et n'expose les ports qu'à `127.0.0.1` : PostgreSQL, Meilisearch, API et WEB ne sont pas accessibles directement depuis le réseau domestique.

**`mangadvisor.cmd` est le seul parcours à utiliser sur le PC.** Il combine :
- `infra/compose/docker-compose.yml` : services de référence et volumes persistants ;
- `infra/compose/docker-compose.local.yml` : ports locaux et cache brut Tenrai ;
- `infra/compose/docker-compose.mobile.yml` : HTTPS privé opt-in, superposé aux deux précédents uniquement après configuration mobile.

`infra/compose/docker-compose.dev.yml` est limité aux développeurs et à la CI : montage du code en lecture/écriture, Uvicorn `--reload`, et définition explicite de l'ancien service Streamlit sous profil `legacy`. Il n'est plus chargé par les options du menu ni par les tâches d'IA ou de sauvegarde.

## Migration automatique de l'ancien port 8502
Au démarrage (menu **3**, **4**, **9** ou via les options de l'assistant), le script arrête puis retire **uniquement le conteneur `mangadvisor_ui`** depuis l'ancienne configuration Compose : `stop ui`, puis `rm -f ui`. Cela n'invoque **pas** `--volumes`, `down -v`, `Nuke`, `docker volume rm`, ni aucune commande de purge SQL. Les données de PostgreSQL et Meilisearch restent dans leurs volumes nommés ; les CSV, archives et secrets restent sur le disque Windows.

Le code de l'ancienne interface reste dans Git **temporairement** pour achever la migration de ses fonctionnalités spécifiques. Un développeur peut encore le lancer intentionnellement avec l'overlay dev et le profil `legacy`, mais il ne fait plus partie de la distribution normale.

## Matrice des fonctions de l'ancien Streamlit

| Fonction Streamlit historique | WEB 8501 aujourd'hui | Conclusion |
|---|---|---|
| Recherche par titre/genre, séries terminées et pagination | Oui, rubrique Découvrir | Couvert |
| Fiche manga et recommandations similaires | Oui, fiche et suggestions | Couvert |
| Choisir ses mangas préférés et obtenir des recommandations | Oui, rubrique Pour moi, mode manuel | Couvert |
| Suggestions depuis sa bibliothèque | Oui, mode bibliothèque | Couvert |
| Statut, note, favori, notes et suppression de série | Oui, fiche manga | Couvert pour les champs modifiables présents |
| Liste des mangas possédés, éditions physiques, ISBN et scanner | Oui, ma bibliothèque / scanner | Couvert et plus complet |
| Import d'ISBN par lot | Oui, aperçu, résolution, confirmation explicite | Couvert |
| Import **générique** des lectures via CSV, avec modèle téléchargeable | API existante ; absence de parcours dédié WEB | **À migrer** |
| Import direct **Excel XLSX** de lectures | Streamlit seulement | **À migrer** |
| Profil de lecture détaillé via /library/profile | API existante ; WEB présente un contexte partiel des recommandations | **À compléter** |
| Édition directe des anciens compteurs de volumes lus/possédés (non ISBN) | API existante ; fiche WEB ne propose pas tous ces champs | **À compléter sans écraser l'inventaire physique** |

**Pourquoi ne pas supprimer immédiatement le code `apps/ui/` ?** Parce que ces dernières fonctions ne sont pas encore reproduites complètement dans le site WEB. Effacer ce code aujourd'hui sans les migrer ferait disparaître des capacités existantes. La présente étape est une **désactivation complète de Streamlit pour les utilisateurs** et une séparation des environnements, pas une fausse promesse de parité fonctionnelle à 100 %. Une PR ultérieure portera les outils manquants dans WEB ; ensuite les fichiers Streamlit, leur image Docker et leurs tests pourront être supprimés proprement de la branche active.

## Contrôles CI ajoutés
- Exécution de `docker compose config` dans le mode stable, absence du service `ui` et du `--reload`.
- Démarrage réel de PostgreSQL, API et WEB via le **Compose stable**, vérification du proxy et de la bibliothèque à travers le port 8501.
- Deux exécutions successives d'un moteur `engine` temporaire pour confirmer que `data/raw/` conserve les fichiers JSON entre extraction et chargement sans monter l'intégralité du dépôt.
- Maintien des tests historiques de Streamlit **uniquement dans la CI de développement** tant que les fonctions spécifiques restent à migrer.

## Déploiement Windows
1. Sauvegarder et vérifier via menu 17.
2. Mettre Git à jour avec l'option 28 ; celle-ci protège les modifications suivies par un `stash` explicite.
3. Ouvrir la seule URL `http://127.0.0.1:8501` après reconstruction. Le port `8502` ne doit plus afficher de site et le conteneur `mangadvisor_ui` ne doit plus être en cours d'exécution.
4. Contrôler « Ma bibliothèque » : œuvres et éditions connues, puis entrées en attente. **Ne pas réimporter la mangathèque déjà conservée**.

Le premier `git pull` reste nécessaire pour installer ce comportement sur le PC. Les volumes ne sont pas renommés, les identifiants PostgreSQL ne changent pas et aucune migration destructrice n'est effectuée.
