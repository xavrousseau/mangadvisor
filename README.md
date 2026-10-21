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
- **Métadonnées complémentaires Wikidata (CC0)** : option **A → 11** pour récupérer par identifiant MyAnimeList manga exact (`P4087`) des libellés français, descriptions courtes et genres sourcés. Les correspondances ambiguës sont refusées ; aucune édition française n’est inventée.
- **Enrichissement personnel en une opération** : option **A → 12** pour enrichir les séries déjà liées à ta mangathèque depuis Wikidata puis, au choix, la BnF. Les entrées physiques non rapprochées sont signalées séparément et les ISBN proposés restent à confirmer. Le conseiller peut afficher les genres Wikidata avec leur provenance et les utiliser uniquement comme précaution pour les exclusions explicites (« sans horreur », « sans gore », « sans romance »).
- **Recommandations** : découverte par ambiance, par bibliothèque, par proximité d'œuvre et conseiller conversationnel ; exclusion des séries déjà enregistrées ou physiquement possédées quand la correspondance à l'œuvre est confirmée.
- **IA locale facultative** : Ollama peut aider à interpréter les demandes mais ne décide pas seul quels mangas existent.

**Important :** une entrée physique sans correspondance canonique (titre ambigu ou absent du catalogue) reste **en attente**. Elle ne peut pas exclure automatiquement un manga du catalogue sans risquer de faire une fausse association.

**Résoudre les lignes en attente :** dans **Ma bibliothèque → En attente de rapprochement**, clique sur **Rapprocher cette ligne**, recherche l'œuvre exacte, vérifie l'édition et les quantités, puis confirme explicitement. Deux éditions d'une même série (ex. Pastel et Deluxe) restent indépendantes. Aucune lecture ni aucun ISBN n'est inventé. [Guide du rapprochement manuel](docs/04_product/manual_pending_inventory_reconciliation_4_3.md).

**Nouveauté — alias multilingues :** les recherches de mangas et le rapprochement peuvent utiliser les titres alternatifs Wikidata (P4087) et les synonymes déjà présents dans les données Tenrai/MyAnimeList, sans télécharger de nouveau catalogue. **A → 13** enrichit des alias supplémentaires FR/EN/JA par lots depuis Wikidata avec vérification de l'ID MAL. Dans l'atelier, un bouton facultatif lance une **recherche MangaDex** (usage personnel non commercial) et ne présente que les résultats qui indiquent explicitement le MAL manga ID du catalogue. Aucune association ni édition n'est automatique. [Guide multilingue](docs/04_product/multilingual_aliases_4_4.md).

## Élargir le catalogue mondial (nouveau, expérimental)

Depuis **mangadvisor.cmd → A → 14**, lancer une **extraction progressive Tenrai** :
- sélectionner un plafond de pages Manga (600 par défaut, 2000 maximum, 25 notices/page) ; ce plafond **n'est pas** un nombre garanti de mangas ;
- choisir éventuellement d'inclure les **one-shots** (plafond séparé de 200 pages) ;
- réutiliser les pages Tenrai déjà téléchargées ou demander expressément de les rafraîchir ;
- le parcours s'arrête sur `pagination.has_next_page=false` ou sur une page vide, sinon au plafond choisi ;
- les pages sont sauvegardées avec leurs paramètres source, séparément par catégorie, et une interruption ne supprime ni pages déjà téléchargées ni données PostgreSQL ;
- une **sauvegarde vérifiée** précède la synchronisation additive vers les tables du catalogue ; le bilan indique le total avant/après et sa variation.

**Important :** ce menu ne récupère **pas encore** un catalogue exhaustif des éditions françaises. Les titres français et ISBN continuent à relever des enrichissements Wikidata/BnF existants. La prochaine étape sera un import **spécifique au format UNIMARC/ISO 2709 des fichiers BnF**, avec contrôle des critères manga et association ISBN→œuvre sans attribution automatique à ta collection. Il n'existe aucune garantie que toutes les pages Tenrai soient disponibles ou que toute œuvre soit un manga français. Pour les fichiers BnF, conserver provenance, date de récupération et licence ouverte.

## Importer les fichiers BnF de livres français (nouveau)

Le menu **`mangadvisor.cmd → A → 15`** propose un import **documentaire** de fichiers BnF en **UNIMARC UTF-8 / ISO 2709**. Déposer les fichiers officiels de livres (.not, .mrc, .marc, .iso, .gz ou .zip) dans `data/raw/bnf/imports/`, puis lancer l'option 15. Un aperçu (1 000 premières notices par fichier) s'affiche **sans écrire en base**. L'import réel ne s'exécute qu'après confirmation et sauvegarde PostgreSQL vérifiée.

La base `bnf_bulk_notice` reçoit **uniquement les notices candidates** selon leur indexation sujet/collection (manga), avec des ISBN validés et une provenance explicite. Les fichiers déjà traités ne sont pas réimportés. **Aucune édition/tome/ISBN n'est automatiquement associé à un manga**, et la mangathèque personnelle ne change pas. Voir le [guide de l'import BnF en masse](docs/04_product/bnf_bulk_import_4_8.md). Les produits BnF sont en [Licence Ouverte](https://www.bnf.fr/fr/conditions-de-reutilisations-des-donnees-de-la-bnf).

## Comparer des sources manga complémentaires (nouveau)

Le menu **`mangadvisor.cmd → A → 16`** prépare un comparatif de **50 mangas**
déjà présents ou en attente de rapprochement, puis interroge les recherches
publiques de **Scrinis** et **MangaUpdates** seulement après confirmation.
Il ne retélécharge pas Tenrai et **ne modifie jamais PostgreSQL**.
Les titres de mangathèque en attente ont priorité ; une confirmation explicite
précède leur envoi en tant que recherches publiques aux fournisseurs.

Les deux rapports restent sur le PC, dans `data/logs/catalog_sources/`.
Les résultats distinguent les titres exacts des simples suggestions,
des ambiguïtés, et des erreurs de fournisseur. Le benchmark ne constitue
pas une preuve d'édition française et n'effectue aucun rapprochement
automatique. Voir le [guide détaillé](docs/04_product/benchmark_sources_4_9.md).

### Préparation bibliographique sécurisée — A → 18

Après la collecte V2, **A → 18** prépare un staging SQL des œuvres candidates,
des éditions et des ISBN bibliographiques. Un aperçu sans écriture précède
une confirmation explicite ; les enregistrements restent `REVIEW_REQUIRED`.
Les données BnF déjà importées sont recoupées en lecture seule par ISBN.
Aucune mutation des fiches mangas canoniques ni de la collection personnelle.

Voir [le guide de staging bibliographique](docs/04_product/bibliographic_staging_v1.md).

### Diagnostic approfondi des sources : V2

Après le premier comparatif, le menu **`mangadvisor.cmd → A → 17`**
conserve les candidats concurrents, recherche éventuellement un titre
alternatif connu et charge un nombre contrôlé de fiches détaillées. Le
rapport local V2 conserve genres, thèmes, provenance des candidats et ISBN
bibliographiques vérifiés **sans jamais les associer automatiquement à une
édition ou une possession**. Les appels externes sont soumis à consentement,
quotas et cache local (24 h).

Lire le [guide comparatif V2](docs/04_product/benchmark_sources_v2.md).
L'ancienne option A → 16 reste disponible pour comparaison.

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
