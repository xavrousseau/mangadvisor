# Mangadvisor — guide d'utilisation du centre de pilotage

**Version de référence :** le menu exécuté par `mangadvisor.cmd` dans `main`.
Ce document décrit le fonctionnement actuel, sans reprendre les anciens menus
Jikan, Streamlit ou les numéros des anciennes versions. Les commandes du menu
restent la source de vérité si un intitulé évolue.

## Prérequis et lancement

Windows 10/11, Docker Desktop démarré, et Git pour Windows si l'on souhaite
actualiser automatiquement le code. Aucun Python ni PostgreSQL à installer
sur Windows : les traitements tournent dans des conteneurs Docker.

Depuis un clone Git du dépôt, double-cliquer sur **`mangadvisor.cmd`**.
Le site est disponible par défaut à **http://localhost:8501** ; les ports
effectifs sont configurés dans le fichier privé `.env`. Le conteneur
`web` utilise Nginx comme proxy vers FastAPI, et PostgreSQL conserve les
données de référence. Une seule interface Web est maintenue : l'ancien
prototype Streamlit n'est plus livré.

## Menu principal

| Choix | Action |
| --- | --- |
| **1** | Installation guidée, préparation SQL, catalogue complet et contrôles |
| **2** | Démarrer les services et ouvrir le site, sans réimportation du catalogue |
| **3** | Sauvegarder, synchroniser le code Git, reconstruire et diagnostiquer |
| **4** | Sauvegarder PostgreSQL et tester la restauration dans une base distincte |
| **5** | Diagnostiquer PostgreSQL, FastAPI, le proxy Web et la bibliothèque |
| **6** | Arrêter les services sans supprimer les volumes |
| **7** | Mettre à jour uniquement le code Git, sans reconstruire ni toucher aux données |
| **A** | Accéder aux options avancées |
| **0** | Quitter le menu |

Le choix **3** effectue une sauvegarde vérifiée **avant** le changement de
code ; en cas d'échec de la sauvegarde, la mise à jour est interrompue.
Le choix **7** ne sauvegarde pas la base : il ne convient pas à une mise
à jour de structure SQL qui doit être précédée d'une sauvegarde.

## Options avancées

| Choix | Action |
| --- | --- |
| 1–2 | Catalogue partiel et recommandations communautaires |
| 3–4 | Import CSV de la mangathèque physique et aperçu non destructif |
| 5–6 | Démarrer/arrêter la session de scanner mobile HTTPS |
| 7–8 | Démarrer/arrêter le conseiller IA local facultatif |
| 9 | Journaux Docker |
| 10–11 | Candidats BnF et métadonnées Wikidata |
| 12–13 | Enrichir la mangathèque et récupérer les alias FR/EN/JA |
| 14–15 | Extension Tenrai et import de fichiers BnF |
| 16–17 | Comparatif de sources V2, deux raccourcis vers le même outil |
| 18 | Préparer les fiches bibliographiques sans toucher aux possessions |
| 19 | Charger le catalogue MAL/Jikan complet via Tenrai avec reprise |
| 20 | Enrichir les titres FR avec Scrinis |
| 21 | Catalogue vivant : nouveautés et synchronisation incrémentale |
| 22 | Réindexer les titres et alias publics dans Meilisearch |
| 23–24 | Pilote et recette bibliographique BnF/Scrinis en sandbox |

**A → S** ouvre les opérations de secours : état Docker, fichier
`.env`, tables SQL, vérification/restauration de sauvegarde et test réseau.
La restauration effective demande une confirmation explicite. Il n'existe
pas d'option de purge des volumes.

## Catalogue et sources

Les scripts historiques dont le nom contient `jikan` interrogent le
fournisseur **Tenrai** selon `MANGA_API_BASE_URL` (par défaut
`https://api.tenrai.org/v1`). Les JSON bruts sont placés sous
`data/raw/jikan/` ; cet emplacement est conservé pour compatibilité.
Une panne réseau ou un quota fournisseur ne justifie jamais la suppression
de PostgreSQL ni une réinitialisation de la collection.

Pour le premier chargement complet, préférer **1** (assistant) ou **A → 19**.
Pour les nouveautés, utiliser **A → 21** au lieu de retélécharger
systématiquement l'ensemble du catalogue. Les correspondances entre
œuvres, éditions, tomes et ISBN sont distinctes ; un titre ressemblant
à un autre ne suffit pas à attribuer un tome possédé.

Les procédures spécialisées sont conservées ici :
[import sûr de la mangathèque](safe_inventory_import_3_8.md),
[correspondances en attente](manual_pending_inventory_reconciliation_4_3.md),
[alias multilingues](multilingual_aliases_4_4.md),
[import BnF](bnf_bulk_import_4_8.md).

## Sauvegardes et récupération

Avant tout changement important, conserver une sauvegarde PostgreSQL
vérifiée et en copier le fichier et son manifeste SHA256 sur un autre
support. En cas de disparition du conteneur PostgreSQL, l'application
ne doit jamais initialiser une nouvelle base vide à la place du volume
historique : elle exige des preuves, puis le consentement interactif
`RECUPERER` avant tout rattachement. Si ces preuves manquent, s'arrêter
et diagnostiquer Docker Desktop plutôt que supprimer un volume.

Un `.env` existant, les volumes Docker, `backups/`, `private-data/`
et les données brutes ne sont jamais des fichiers de nettoyage Git.
Les imports incertains restent en attente d'une résolution explicite.

Pour les détails de restauration :
[procédure de sauvegarde et récupération](library_backup_recovery_3_2.md).

## Vérifications et limites

Le diagnostic du menu **5** teste les services, la base, une réponse
API, le site, le proxy `/api/` et la bibliothèque. Une CI verte
atteste les scénarios synthétiques exécutés sur GitHub (dont Windows,
Docker et navigateur), **pas** le contenu et le fonctionnement de ta
base personnelle sous Windows.

Avant de déclarer la V1 terminée, effectuer la recette réelle de
l'installation, du chargement, de l'import, des rapprochements, des
recommandations et du conseiller/scanner facultatifs. Les correspondances
bibliographiques encore ouvertes sont suivies dans
[l'issue #71](https://github.com/xavrousseau/mangadvisor/issues/71).
La V2 sera consacrée à l'UX ; elle ne sert pas à reporter les corrections
fonctionnelles nécessaires à la V1.
