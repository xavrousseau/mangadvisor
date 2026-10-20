# Mangadvisor

**Ta mangathèque, tes éditions françaises et tes prochaines découvertes mangas.**

Mangadvisor est une application locale, avec une interface Web accessible depuis le PC. Elle réunit un catalogue alimenté par **Tenrai**, une bibliothèque personnelle, des éditions françaises vérifiées par ISBN/BnF et un conseiller en mangas. Les données sont conservées dans PostgreSQL (Docker). Un conseiller IA local Ollama et l'accès HTTPS sur téléphone sont **facultatifs**.

## Démarrer sur Windows : un seul fichier

**Prérequis** : [Docker Desktop](https://www.docker.com/products/docker-desktop/) démarré et dossier de Mangadvisor téléchargé depuis ce GitHub. Git pour Windows est nécessaire uniquement pour la mise à jour automatique (commande 3). Pas besoin d'installer Python ni PostgreSQL sur le PC.

**Double-clique sur `mangadvisor.cmd`** (à la racine du dépôt) puis choisis :

| Choix | Action | À quoi ça sert |
| --- | --- | --- |
| **1** | **Première installation** | Crée la configuration privée, initialise PostgreSQL, construit les images, récupère le catalogue Tenrai et les relations de recommandation, lance le site, vérifie l'installation et propose l'import de la collection. |
| **2** | **Démarrer Mangadvisor** | Lance les conteneurs existants en arrière-plan, vérifie l'API et ouvre le site. **Ne retélécharge pas le catalogue** et **n'efface rien**. |
| **3** | **Mettre à jour** | Vérifie la sauvegarde de la base, récupère `main` via Git, applique les évolutions non destructrices, reconstruit les images et lance le diagnostic. |
| **4** | **Sauvegarder la mangathèque** | Enregistre une archive PostgreSQL privée et teste sa restauration dans une base isolée. |
| **5** | **Vérifier le fonctionnement** | Contrôle PostgreSQL, API directe, Nginx, bibliothèque et principaux volumes de données. |
| **6** | **Arrêter Mangadvisor** | Arrête Docker Compose sans supprimer les données. |
| **7** | **Récupérer GitHub** | Télécharge le code officiel depuis GitHub, archive automatiquement les fichiers locaux non suivis qui bloquent l'arrivée de nouveaux fichiers, et ne touche pas à Docker. |
| **A** | **Options avancées** | Catalogue, recommandations, imports, scanner mobile, IA locale, journaux, configuration et restauration. |
| **0** | **Quitter le menu** | Ne stoppe pas une application déjà démarrée. |

Le site est ensuite disponible par défaut sur **http://localhost:8501**. Le port exact vient du fichier privé `.env`, créé à la première installation. Chaque action s'exécute **dans la même fenêtre de commandes** et affiche clairement son succès ou son échec. Il n'est pas nécessaire de lancer des commandes Docker manuelles pour utiliser l'application.

### Première installation complète

1. Télécharge le dépôt (clone Git ou ZIP) et démarre Docker Desktop.
2. Double-clique sur **`mangadvisor.cmd`**, puis appuie sur **1**.
3. Suis l'assistant pour construire les images, créer les tables, récupérer les notices Tenrai et les relations manga. Une connexion Internet est nécessaire.
4. Pour importer ta collection personnelle, dépose le CSV dans **`private-data/mangatheque.csv`**. Le format attendu est décrit dans [Import de l'inventaire physique](docs/04_product/safe_inventory_import_3_8.md) ; il contient notamment les colonnes `serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier`.
5. L'assistant affiche un **aperçu** avant toute écriture ; il ne confirme jamais automatiquement les associations incertaines. Les éditions distinctes d'une même œuvre restent distinctes. Une sauvegarde est vérifiée avant l'import confirmé et une autre à la fin de l'installation.

**Import ultérieur depuis A → 3 :** le menu présente d'abord un aperçu sans écriture. Si tu demandes l'import, il réalise automatiquement une sauvegarde PostgreSQL vérifiée **avant** toute modification. Une sauvegarde impossible bloque l'import.

Les dossiers `private-data/`, `backups/` et le fichier `.env` sont exclus de Git. **Ne les publie pas sur GitHub**. Les fichiers Excel doivent être exportés ou convertis au format CSV attendu avant l'import physique, sans attribuer automatiquement d'ISBN, de notes ou de tomes lus.

### Les jours suivants

Démarre Docker Desktop, lance `mangadvisor.cmd` puis **2**. La page doit s'ouvrir dans le navigateur. Lorsque tu souhaites arrêter les services, utilise **6**. En cas de problème, choisis **5** pour obtenir les contrôles et les messages d'erreur, puis ouvre les journaux dans **A**.

### Mettre à jour sans perdre les données

Pour simplement récupérer le dernier code, choisis **7** (« Récupérer GitHub »). Pour mettre à jour **et** reconstruire Docker, choisis **3**. Les deux commandes utilisent le synchroniseur sécurisé `cmd/github-sync.ps1`, qui :
- télécharge `main` de `origin` et refuse les historiques divergents ou une autre branche ;
- déplace **uniquement** les fichiers locaux non suivis qui entreraient en collision avec des nouveaux fichiers officiels, dans `mangadvisor-archives-git/` **à côté du dossier Mangadvisor** (jamais de suppression) ;
- exige confirmation avant de placer les modifications **déjà suivies** dans une sauvegarde Git locale (stash), qui n'est jamais réappliquée automatiquement ;
- ne lance jamais `git reset --hard`, `git clean`, `docker compose down -v`, et ne déplace jamais `.env`, `private-data/`, `backups/` ou `data/raw/`.

L'option **3** réalise **d'abord** une sauvegarde PostgreSQL avec restauration de vérification, puis appelle le synchroniseur, applique les migrations SQL additives, reconstruit les images Docker et lance le diagnostic. L'option **7** ne fait que synchroniser le code : lance ensuite l'option 3 pour le mettre en service.

**Premier déblocage si l'ancien menu ne propose pas encore 7 :** exécuter une seule fois, depuis PowerShell dans le dossier Mangadvisor, les commandes suivantes pour récupérer le synchroniseur depuis la branche officielle sans écraser les fichiers personnels :
```powershell
git fetch origin main
git show FETCH_HEAD:cmd/github-sync.ps1 | Set-Content -Encoding Ascii .\cmd\github-sync.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\cmd\github-sync.ps1
```
L'outil archivera aussi cette copie temporaire du synchroniseur, puisque la nouvelle version officielle suit le même nom de fichier. Après cette première mise à jour, le menu **7** sera disponible.

Un dossier téléchargé en **ZIP** ne contient pas d'historique `.git` : pour éviter une fusion destructrice, l'option 7 l'indique et ne tente pas de le convertir silencieusement. Pour les mises à jour automatiques futures, utiliser un clone Git initial. Conserve impérativement `private-data/`, `backups/` et `.env`.

### Sauvegarde et restauration

L'option principale **4** réalise un `pg_dump` avec manifeste SHA256, suivi d'une **restauration de vérification dans une base temporaire**. La restauration réelle n'est pas automatique : elle se trouve sous **A → S → 5** et demande une confirmation explicite ; une nouvelle sauvegarde de sécurité est créée avant le basculement. [Procédure détaillée](docs/04_product/library_backup_recovery_3_2.md).

**Copie tes archives de `backups/` sur un deuxième support.** Un disque dur défaillant pourrait détruire à la fois la base et les sauvegardes conservées uniquement sur le même PC.

## Ce qui est dans Mangadvisor

- **Catalogue et fiches** : recherche, filtres, couvertures, synopsis et genres/thèmes issus de données réelles.
- **Bibliothèque de lecture** : statuts, notes, favoris, progression et historique personnel.
- **Mangathèque physique** : quantités déclarées par édition distincte, sans confondre les exemplaires, les ISBN vérifiés ni les volumes lus.
- **Éditions françaises** : rapprochements volontaires avec la BnF, recherche par titre/ISBN et scanner lorsque le navigateur/HTTPS le permet.
- **Recommandations** : découverte par ambiance, par bibliothèque, par proximité d'œuvre et conseiller conversationnel ; exclusion des séries déjà enregistrées ou physiquement possédées quand la correspondance à l'œuvre est confirmée.
- **IA locale facultative** : Ollama peut aider à interpréter les demandes mais ne décide pas seul quels mangas existent.

**Important :** une entrée physique sans correspondance canonique (titre ambigu ou absent du catalogue) reste **en attente**. Elle ne peut pas exclure automatiquement un manga du catalogue sans risquer de faire une fausse association.

## Architecture et contrôle qualité

| Composant | Emplacement |
| --- | --- |
| Menu Windows et orchestration | `mangadvisor.cmd`, `cmd/control-center.ps1` |
| Front Web | `apps/web/` |
| API FastAPI, bibliothèque, conseiller | `apps/api/` |
| Extracteurs Tenrai et chargements SQL | `pipelines/engine/` et `sql/schema/` |
| Docker stable (sans Streamlit) | `infra/compose/docker-compose.yml` + `docker-compose.local.yml` |
| Tests unitaires et intégration | `tests/`, `.github/workflows/` |

L'ancien prototype Streamlit est encore présent uniquement pour les tests et la transition technique ; **il ne fait pas partie de l'interface normale**. Les scripts de données historiquement nommés Jikan restent utilisables mais l'API source normale est Tenrai. Aucun historique de nommage ne justifie une suppression des volumes.

[Audit et anomalies connues](docs/reports/repository_audit_2026_10_20.md) · [Architecture](docs/03_technical/project_structure.md) · [Import physique](docs/04_product/safe_inventory_import_3_8.md) · [Sauvegardes](docs/04_product/library_backup_recovery_3_2.md)
