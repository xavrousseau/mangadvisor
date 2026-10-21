# Mangadvisor — Staging bibliographique, phase 1

## Objectif

Passer des **comparatifs API** à des **références structurées réexaminables**
sans toucher au catalogue \`manga\`, \`manga_fr_edition\`, \`manga_genre\`,
\`user_manga_*\` ni aux états de lecture/recommandation.

**Périmètre exact :** importer les **preuves déjà obtenues** dans le plus
récent rapport V2 (50 entrées au maximum) vers un staging PostgreSQL séparé.
Cela **n'effectue aucun appel externe supplémentaire** et ne complète donc
pas les fiches limitées par le quota ou par la troncature du benchmark.

## Démarrage sur Windows

1. \`mangadvisor.cmd → 3\` : récupérer la dernière version.
2. \`mangadvisor.cmd → A → 17\` : facultatif si un rapport V2 récent existe.
3. \`mangadvisor.cmd → A → 18\` : préparation bibliographique.
4. L'outil choisit automatiquement le **dernier**
   \`data/logs/catalog_sources/comparatif_sources_v2_....json\`, contrôle
   son format et fournit un aperçu JSON et CSV **sans écrire en SQL**.
5. Confirmer explicitement pour stocker ce lot dans les tables
   \`bib_stage_*\`. Refuser laisse seulement les fichiers d'aperçu locaux.

Option technique réservée aux usages CLI : \`--report\` accepte uniquement
le **nom de fichier** d'un rapport V2 local (aucun chemin ou URL arbitraire).
\`--preview\`, \`--import\` et \`--status\` sont mutuellement exclusifs.

Fichiers locaux exclus de Git :
\`data/logs/bibliographic_staging/preparation_<SHA>.json\` (chiffres de
contrôle) et \`candidats_<SHA>.csv\` (une ligne par candidat source).

## Tables isolées

| Table | Objet |
|---|---|
| \`bib_stage_batch\` | Identifiant SHA-256 du rapport d'entrée ; rejeu idempotent du même fichier |
| \`bib_stage_candidate\` | Candidats d'œuvres distincts par fournisseur, identifiant source, titre, type, auteur, genres, score indicatif et statut de revue |
| \`bib_stage_edition\` | Éditions documentées par candidat : langue, support, libellé et nombre de tomes déclaré par source |
| \`bib_stage_volume\` | ISBN-13 valides issus **exclusivement de la fiche de ce candidat**, tome, langue, support, édition et date de publication |

Les clefs \`(SHA, position d'entrée, source, ID fournisseur)\` empêchent
les collisions entre œuvres homonymes telles que **Wind Breaker**.
Deux éditions **Dragon Ball Pastel et Deluxe** restent distinctes par
\`edition_label\` lorsqu'elles sont publiées comme telles dans une fiche.
Une *déclaration privée d'édition* ne génère aucun tome ou ISBN fictif ;
elle est seulement un indice à faire contrôler.

Les données publiées gardent les informations de provenance, mais **pas**
les notes/quantités personnelles, jaquettes, résumés ni la réponse API brute.

## Décisions possibles

**V1 ne prend aucune décision de fusion.** Tous les candidats sont stockés
avec \`decision=REVIEW_REQUIRED\`, y compris si le titre est exact,
si les scores sont élevés, ou si plusieurs sources montrent des indices
qui semblent converger. Il faut éviter :
- de relier le mauvais Wind Breaker (Satoru Nii/Pika ou Yong-seok Jo/WEBTOON) ;
- de confondre Yu-Gi-Oh! manga et roman, ou Black Clover et son one-shot ;
- de considérer une édition numérique/japonaise comme une édition française
  papier ;
- de marquer un tome comme **possédé** à partir d'un ISBN de fournisseur.

Le stockage d'une référence n'est donc **pas la validation de son identité**.

## Liens bibliographiques avec BnF

Après l'enregistrement, l'outil recherche **en lecture seule** si les ISBN
français papier déjà présents dans le rapport apparaissent dans
\`bnf_bulk_notice.isbn13\` (données de l'importateur BnF A → 15).

- Sans données BnF préalablement importées : \`BNF_BULK_STAGING_NOT_LOADED\`.
- Avec BnF : un nombre de notices présentant au moins un ISBN commun.
- Il ne s'agit **pas** d'une validation d'œuvre ni d'édition. Deux sources
  bibliographiques peuvent partager un ISBN malgré des variantes de titres
  ou des notices dupliquées, et une mauvaise association peut rester possible.

La BnF est **une source documentaire supplémentaire**, jamais une
autorisation d'attribution automatique de livres à la mangathèque.

## Conséquences et limites

- **Écriture SQL** : uniquement dans \`bib_stage_batch\`,
  \`bib_stage_candidate\`, \`bib_stage_edition\`, \`bib_stage_volume\`.
  La création de ces tables se fait automatiquement lors du premier import
  confirmé. Aucune modification de tables canoniques ou personnelles.
- Chaque rapport est atomique : échec de l'import = aucune écriture partielle
  du lot. Même rapport rejoué = \`ALREADY_PREPARED\`.
- Les **50 œuvres du benchmark ne représentent pas les 10 033 mangas du
  catalogue**. Il faudra élargir l'outil de collecte en lots vérifiés avant
  d'alimenter le staging à cette échelle.
- Les listes \`book_references\` du V2 restent tronquées à 20 ISBN :
  \`reference_list_truncated\` est propagé. Ce staging ne peut pas recréer
  les ISBN omis dans le rapport initial.
- Les scores sont indicatifs, sans auteur de référence sûr dans l'import.
- Les rapports restent sur le PC ; ne pas les publier sur GitHub.
- La prochaine phase sera une interface de **revue de correspondances**,
  suivi d'un mécanisme d'application *explicite, contrôlé, réversible* aux
  tables canoniques (pas inclus ici).

## Sources de métadonnées

- Scrinis API : recherche et détails des œuvres, éditions et ISBN lorsque
  disponibles dans le rapport V2.
- MangaUpdates API : œuvres et genres/thèmes selon les détails déjà récupérés.
- BnF (import UNIMARC déjà disponible) : contrôle documentaire par ISBN.

La présente opération **n'interroge directement aucune de ces API**.
