# Catalogue vivant Mangadvisor — initialisation et mise à jour continue

## Vision : une seule base de référence qui évolue

Le catalogue international (MyAnimeList/MAL, via Tenrai compatible Jikan)
est **la base initiale d'identité** ; Scrinis, MangaUpdates et BnF ajoutent
des métadonnées et des preuves bibliographiques, **sans créer une deuxième
liste de mangas indépendante**. La mangathèque personnelle reste protégée.

\`data/raw/jikan/manga_page_N.json\` sur Windows (projet :
\`F:\1.Boulot\03_Github\mangadvisor\data\raw\jikan\`) conserve les 858
pages Jikan/Tenrai complètes ; **on ne les réécrit jamais** lors de la
veille quotidienne. PostgreSQL \`jikan_manga_source\` et \`manga\` restent
les deux niveaux SQL principaux, avec identifiant \`mal_id\` partagé.

### Phase I — socle initial, une seule fois

Le menu **A → 19** télécharge toutes les pages publiques Jikan/MAL,
respecte le nombre de pages donné par Tenrai, conserve les JSON
dans le dossier historique, importe le référentiel, puis contrôle
le nombre d'ID MAL distincts et leur présence dans \`manga\`.
Le dernier rapport local indique **85 776 notices**. Le cycle
automatique REFUSE de fonctionner si ce socle n'est pas marqué
\`CATALOGUE_COMPLETE\` ou si des notices sources restent sans œuvre
canonique. **A → 21 → 1** effectue cet audit en lecture seule.

L'exhaustivité est relative **aux notices publiques exposées par Tenrai
à la date du téléchargement**, pas à tous les mangas de l'univers ni
aux notices supprimées/non approuvées. Un contenu Jikan ou MAL inexact
n'est pas corrigé automatiquement par son simple import.

### Phase II — compléments à la même base

Un traitement initial puis des lots progressifs utilisent des contrôles
documentaires séparés :

| Source | Rôle | Écriture autorisée |
|---|---|---|
| Scrinis | Identifier une publication française papier d'une œuvre par titre exact + auteur (ou MAL ID), fiche détaillée et ISBN FR | Alias français dans \`manga_title_alias\`, provenance ; aucun ISBN possédé |
| MangaUpdates | Références internationales, identifiants, auteurs, genres et thèmes | \`manga_mangaupdates_evidence\` : rapprochements confirmés ou à revoir, pas de fusion de fiches homonymes |
| BnF SRU | ISBN français et titres publiés en France | \`manga_bnf_candidate\` : références ISBN **à vérifier** |
| BnF données mensuelles | Notices officielles UNIMARC/ISO2709 | \`bnf_bulk_notice\` : table source bibliographique isolée ; fichiers fournis dans \`data/raw/bnf/imports\` |

**Les 85 776 œuvres n'ont PAS encore toutes été réconciliées avec
MangaUpdates et la BnF.** Ce rattrapage est progressif selon les
quotas et le temps de fonctionnement de Docker. Les données françaises
ne sont jamais inventées lorsqu'un auteur ou une édition manque.

### Phase III — actualisation incrémentale et suivi des nouveautés

Le moteur \`catalogue_lifecycle.py\` ne relance pas A → 19 quotidiennement.

Chaque cycle interroge au plus **8 premières pages** MAL triées par
\`mal_id DESC\` jusqu'à rejoindre la dernière zone d'ID connue.
Il vérifie en complément **8 pages anciennes tournantes** en tri
\`mal_id ASC\` pour découvrir des ajouts approuvés tardivement et les
corrections d'anciennes fiches. Le curseur est enregistré dans
\`catalogue_lifecycle_state\`, pour ne pas examiner les mêmes
vieilles pages chaque jour.

Les nouvelles informations ne sont chargées en SQL que si le JSON
d'une notice a réellement changé ou si son \`mal_id\` est absent de
\`jikan_manga_source\`. Les mises à jour canoniques des titres,
synopsis, volumes, genres, thèmes et démographies sont
**limitées à ces identifiants**. Aucune reconstruction SQL globale
des 85 776 œuvres n'est lancée dans le cycle quotidien.

Les JSON correspondant aux changements vont dans
\`data/raw/jikan/updates/delta_*.json\`, **jamais** parmi les
\`manga_page_N.json\` historiques.

Les enrichissements reprennent ensuite avec un nombre borné de
fiches : **40 Scrinis, 15 MangaUpdates et 10 BnF SRU par cycle**.
Lorsque le cycle découvre ou corrige une notice MAL, ses nouveaux
identifiants canoniques passent **en priorité** dans des lots spécifiques
(maximum 12 Scrinis, 5 MangaUpdates et 5 BnF) avant de reprendre la file
globale de rattrapage. Le rapprochement n'est toujours jamais forcé.
L'objectif est de progresser sur le stock international et français,
sans saturer les API publiques. Des erreurs de limite de débit arrêtent
les traitements concernés sans créer de correspondances fictives.
Les fichiers mensuels BnF **déjà présents localement** sont détectés
automatiquement par leur SHA-256 lors d'un cycle (jusqu'à 3 fichiers) ;
un même fichier ne sera pas réimporté.

**Point de vigilance :** le téléchargement *automatique* des archives
mensuelles BnF **n'est pas encore implémenté** ; il faut déposer les
fichiers fournis par la BnF dans le répertoire prévu. Le contrôle SRU,
lui, interroge le catalogue BnF en ligne. De plus, les nouvelles sorties
en librairie peuvent précéder leur indexation sur MAL, Scrinis ou BnF.
Le cycle n'est donc **pas** une garantie d'apparition immédiate de tous
les prochains tomes.

Le parcours quotidien des pages tournantes n'exclut pas qu'une
ancienne notice soit manquée temporairement, notamment lors de
réordonnancements de pagination par l'API. Un **audit complet
exceptionnel** via A → 19 reste possible, mais n'est pas nécessaire à
chaque nouveauté.

### Fonctionnement automatique dans Docker

Dans \`mangadvisor.cmd\` :

- **Option 3** : mise à jour du dépôt et reconstruction des images.
- **A → 21 → 1** : audit sans réseau du socle Jikan initial.
- **A → 21 → 2** : exécution manuelle d'un cycle incrémental.
- **A → 21 → 3** : activation **explicite** du conteneur
  \`mangadvisor_catalog_sync\` (profil Compose \`automation\`, avec
  sauvegarde PostgreSQL avant activation). Premier cycle immédiatement,
  puis un cycle toutes les ~24 heures si le dernier a réussi, ou
  une nouvelle tentative après 6 heures en cas d'erreur.
- **A → 21 → 4** : arrêt/désactivation sans suppression des volumes
  PostgreSQL ni des fichiers bruts.
- **A → 21 → 5** : dernier état du worker.

Le travail ne s'exécute **que lorsque le PC et Docker Desktop tournent**.
Le redémarrage Docker relance le conteneur activé
(\`restart: unless-stopped\`). Il ne peut pas réveiller un PC éteint
ni assurer une disponibilité 24/7 sans machine toujours allumée.

### Suivi, contrôles et sécurité

\`data/logs/catalogue_lifecycle/last_cycle.json\` conserve chaque
dernier bilan : pages récentes et anciennes parcourues, MAL ID nouveaux,
ID dont le contenu a été modifié, nombre d'œuvres effectivement mises
à jour, données candidates Scrinis/MangaUpdates/BnF et erreurs source.

Un **verrou PostgreSQL** empêche deux cycles simultanés. Toute exécution
ayant échoué est explicitement signalée \`FAILED\` : nous ne confondons
pas un succès partiel (par exemple MAL OK mais BnF indisponible) avec
une mise à jour complète de toutes les sources.

Le synchroniseur n'effectue ni \`DELETE\`, ni \`TRUNCATE\`, ni
réinitialisation des \`manga.id\`, ni aucun changement dans les tables
\`user_manga_*\` / \`user_manga_volume\`. Un ISBN tiers est toujours
une **référence bibliographique candidate, jamais une preuve de
possession**. La sauvegarde PostgreSQL existante est conservée et
faite avant l'activation de la veille ; les sauvegardes quotidiennes
automatiques ne font **pas** encore partie de ce worker.

Le succès de cette phase n'est donc pas « 85 776 mangas ont tous des
éditions françaises » mais : **socle initial complet et contrôlé**,
**nouvelles œuvres ajoutées sans tout recharger**, **corrections
ciblées**, **enrichissements avec provenance**, et **statistiques
d'avancement vérifiables**.
