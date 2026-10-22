# Mangadvisor

**Découvrir, recommander et organiser ses mangas — avec des références sourcées.**

Mangadvisor est une application **locale** pour gérer une mangathèque physique et une
bibliothèque de lecture, rechercher des mangas et recevoir des recommandations
personnalisées. L'interface est un **site Web** servi localement ; Docker
orchestré par `mangadvisor.cmd` héberge les services. Aucune installation
de Python ou de PostgreSQL n'est nécessaire sur Windows.

> **Données :** le catalogue des œuvres, les notices bibliographiques
> candidates et les livres que tu déclares posséder sont **trois choses
> différentes**. Un ISBN croisé entre BnF et Scrinis ne prouve ni une édition
> exacte ni la possession d'un tome. Les rapprochements ambigus restent
> soumis à validation.

## Démarrer sous Windows

Prérequis : **Windows 10/11**, Docker Desktop démarré, accès Internet lors
de la première collecte. Git pour Windows est requis pour les mises à jour
automatiques d'un dépôt cloné.

Double-cliquer sur **`mangadvisor.cmd`** à la racine du dépôt.

| Menu | Fonction |
| --- | --- |
| **1** | Première installation guidée, création des tables et catalogue |
| **2** | Démarrer l'application et ouvrir le site |
| **3** | Sauvegarder, récupérer la version stable `main`, reconstruire, vérifier |
| **4** | Sauvegarder PostgreSQL avec restauration de vérification |
| **5** | Diagnostiquer la base, les services et l'application |
| **6** | Arrêter sans supprimer les volumes Docker |
| **7** | Synchroniser uniquement le code depuis `main` |
| **A** | Opérations avancées ; entretien, catalogue, enrichissement, scanner |
| **0** | Quitter le menu |

Adresse par défaut : **http://localhost:8501**. Les ports réels sont définis
dans le fichier privé `.env`. La commande **2** réutilise la base et les
images existantes, sans retélécharger le catalogue.

Pour la **première mangathèque physique**, placer un CSV conforme dans
`private-data/mangatheque.csv` et suivre la simulation d'import. Les
quantités et éditions sont conservées telles que déclarées ; aucune
association incertaine n'est imposée.

- [Importer la mangathèque physique](docs/04_product/safe_inventory_import_3_8.md)
- [Rapprocher une ligne en attente](docs/04_product/manual_pending_inventory_reconciliation_4_3.md)
- [Sauvegarder et restaurer](docs/04_product/library_backup_recovery_3_2.md)

## Fonctions disponibles

| Fonction | Description |
| --- | --- |
| **Découverte** | Fiches, couvertures, recherche multilingue, genres, filtres |
| **Ma bibliothèque** | Statuts de lecture, favoris, notes, import CSV/XLSX |
| **Mangathèque physique** | Quantités par édition déclarée, doublons, lignes en attente |
| **Recommandations** | Par ambiance, par profil, par collection et par œuvre |
| **Conseiller** | Échanges guidés, résultats sourcés par le catalogue |
| **Scan ISBN** | Recherche et enrichissement à partir du code-barres, selon les permissions navigateur |
| **Sources françaises** | Wikidata, BnF et Scrinis, avec provenance et ambiguïtés |
| **Options facultatives** | Conseiller IA local Ollama, scanner mobile HTTPS, veille automatique |

Le conseiller et les recommandations ne doivent pas inventer des éditions,
des ISBN, des notes, des livres possédés ni des lectures. Le modèle IA local,
lorsqu'il est activé, reste subordonné aux résultats contrôlés de l'application.

### Catalogue, sources et édition française

- **Tenrai / identifiants MAL** : collecte et reprise du catalogue international
  dans PostgreSQL. [Guide du catalogue](docs/04_product/catalogue_mal_complet.md).
- **Meilisearch** : recherche tolérante aux fautes sur des métadonnées
  **publiques** et retour à PostgreSQL si nécessaire. Les possessions,
  notes et préférences personnelles ne sont pas indexées.
- **Wikidata** : libellés et alias complémentaires, avec identifiant MAL
  vérifié quand disponible.
- **BnF** : notices de livres et ISBN **candidats**, import UNIMARC/ISO 2709
  contrôlé et traçable. [Guide BnF](docs/04_product/bnf_bulk_import_4_8.md).
- **Scrinis** : enrichissement de titres et références françaises imprimées
  après vérification de l'identité de l'œuvre. [Guide Scrinis](docs/04_product/enrichissement_fr_direct_scrinis.md).

Pour investiguer des sources, le menu **A → 17** dispose d'un comparatif
documenté, et **A → 23** d'un pilote bibliographique.
Le menu **A → 24** lance une **recette isolée** BnF/Scrinis sur la
sandbox `mangadvisor_realtest`, si celle-ci a été initialisée.
Cette recette ne modifie pas la collection personnelle.
[Recette BnF/Scrinis](docs/04_product/bibliographic_validation_integrated.md).

**Limite actuelle :** le modèle complet *œuvre → édition → tome → ISBN*
avec association automatique sûre et exhaustive n'est pas encore validé.
Les rapprochements non prouvés restent des propositions. Le suivi est
dans [l'issue bibliographique #71](https://github.com/xavrousseau/mangadvisor/issues/71).
Les éditions classiques, Deluxe, Pastel, collectors et intégrales ne
doivent jamais être mélangées par défaut.

## Sécurité des données et mises à jour

- PostgreSQL est la source de vérité. Docker conserve ses **volumes persistants**.
  Ne jamais effacer ces volumes pour corriger un problème de code.
- `.env`, `private-data/`, `backups/` et les fichiers bruts privés
  sont exclus de Git. **Ne jamais envoyer de sauvegardes ou secrets sur GitHub.**
- L'option **3** vérifie une sauvegarde PostgreSQL avant la mise à jour ;
  l'option **7** met seulement le code à jour. La synchronisation refuse
  les historiques divergents et les branches autres que `main`.
- La restauration d'une sauvegarde n'est **jamais automatique** :
  elle exige une confirmation explicite sous **A → S → 5**.
- Conserver une copie du dossier `backups/` sur un autre support physique.

Il est préférable d'utiliser le **clone Git** du dépôt plutôt qu'un ZIP
pour bénéficier des mises à jour sécurisées.

## Architecture et maintenance

```text
mangadvisor.cmd                 Menu utilisateur Windows
cmd/control-center.ps1          Orchestration et maintenance
apps/web/                      Site Web (HTML / CSS / JavaScript)
apps/api/                      API FastAPI et logique applicative
pipelines/engine/              Acquisition et enrichissement
sql/schema/                    Modèle SQL et migrations additives
infra/compose/                 Docker Compose (stable et sandbox)
infra/docker/                  Images des services
tests/                         Python, JavaScript et tests navigateur
.github/workflows/             Contrôles CI GitHub Actions
docs/                          Documentation ciblée par usage
```

L'ancien prototype Streamlit a été retiré de la configuration maintenue.
Les scripts historiquement nommés « Jikan » conservent leurs noms quand
cela évite de casser les pipelines ; le fournisseur utilisé est Tenrai.

Tests du code (dans un environnement ayant installé les dépendances) :

```text
python -m compileall -q apps/api pipelines/engine tests tools
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/web/*.test.mjs
```

La CI vérifie aussi l'interface sous Playwright, Docker, PostgreSQL,
les parcours API et Windows. **CI verte ≠ recette réelle de ta base privée** :
la dernière doit être vérifiée séparément lorsque le comportement dépend
de données locales ou des réponses actuelles des fournisseurs.

- [Architecture technique](docs/03_technical/project_structure.md)
- [Contrôles bibliographiques](docs/04_product/bibliographic_validation_integrated.md)
- [État de GitHub et tâches ouvertes](https://github.com/xavrousseau/mangadvisor/issues/71)

## Méthode de contribution

`main` est la branche stable. Une évolution cohérente est développée
sur une branche courte, testée, documentée et intégrée dans **une PR**,
de préférence par *squash* pour conserver un historique lisible.
Les données personnelles et rapports de test générés ne sont pas
versionnés. Ne jamais fusionner une ancienne branche divergente sans
auditer les fonctionnalités uniques qu'elle contient.
