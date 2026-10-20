# Import bibliographique BnF — première étape contrôlée

## Pourquoi ce module ?

Mangadvisor conserve déjà un catalogue international de mangas dans PostgreSQL.
Cette fonctionnalité ne ré-extrait pas Tenrai et ne touche **jamais** à la
mangathèque ou aux éditions françaises confirmées. Elle importe uniquement
des **candidats bibliographiques français** depuis les fichiers publics BnF.

## Source et formats

- Catalogue officiel : https://api.bnf.fr/index.php/fr/produits_bibliographiques_mensuels
- Télécharger **Bibliographie nationale française — Livres**, sélectionner
  **Unimarc_UTF8** (ou équivalent dans le répertoire de téléchargement).
- Format bibliographique UNIMARC, conteneur **ISO 2709 UTF-8**. Les fichiers
  .not, .mrc, .marc, .iso, .gz et ZIP contenant ces fichiers sont acceptés.
- La licence ouverte de l'État autorise la réutilisation des métadonnées sous
  réserve de conserver l'indication **BnF** et la date de récupération :
  https://www.bnf.fr/fr/conditions-de-reutilisations-des-donnees-de-la-bnf
- Les produits BnF 2026 sont incomplets : pas de fichiers mensuels pour
  avril/mai 2026, reprise progressive dès juin. Ne pas déduire que les
  fichiers manquants correspondent à une absence de publications.
- Les produits rétrospectifs se trouvent sur :
  https://api.bnf.fr/index.php/fr/notices-bibliographiques-de-la-bibliographie-nationale-francaise
  Leur volume peut être très élevé ; commencer par **un lot mensuel**.

## Mode d'emploi Windows

1. Mettre à jour Mangadvisor par l'option **3** de \`mangadvisor.cmd\`.
2. Télécharger un fichier officiel (Livres, UNIMARC, UTF-8, ISO 2709).
3. Le placer dans \`data/raw/bnf/imports/\` (créer les dossiers si besoin).
4. Lancer \`mangadvisor.cmd → A → 15\`.
5. L'outil affiche automatiquement un **aperçu sur les 1 000 premières
   notices de chaque fichier** : sélection manga, ISBN valides et exemples.
6. Confirmer explicitement pour réaliser une sauvegarde PostgreSQL avec
   vérification de restauration **avant** l'écriture en staging.
7. Lire le bilan : notices analysées, mangas candidats, candidats avec ISBN,
   empreinte SHA-256 du lot, éventuels fichiers déjà importés.

Aucune installation Python sur Windows, aucune commande SQL manuelle.
Les fichiers restent en local dans \`data/raw/\` (ignoré par Git).
Une exécution répétée du même fichier est ignorée par empreinte SHA-256.
Un fichier corrompu interrompt son import en annulant ses écritures.

## Champs lus et provenance

L'importeur lit :
- **001** : identifiant notice BnF ;
- **010 $a** : ISBN-10/13 avec contrôle de la clé et conversion ISBN-10 ;
- **200 $a / $f** : titre et auteur ;
- **210/214 $c / $d** : éditeur, date ;
- **225 $a / $v** : collection, volume dans la collection ;
- **606/608** : sujets/formes/genres pour **identifier des candidats** ;
- **801 $b / $c** : origine de catalogage et date de notice.

Il conserve le lien vers la page source BnF, la date réelle de traitement,
l'identifiant de notice et l'empreinte du fichier. Les informations BnF sont
des métadonnées : cet importeur ne télécharge aucune couverture ni chapitre.

**Sélection conservatrice** : seules les notices portant un terme explicite
« manga » ou « bande dessinée japonaise » dans leurs sujets ou leur collection
sont retenues. Cette sélection est susceptible de manquer des mangas pourtant
présents dans la BnF : elle vise une première base de candidats à réviser,
pas une prétendue exhaustivité. La présence d'un ISBN ne certifie jamais à
elle seule le tome ou l'édition d'une œuvre.

## Tables PostgreSQL

L'importeur crée **uniquement**, sans modifier les tables existantes :

- \`bnf_bulk_batch\` : lots importés avec SHA-256, nombre de notices, nombre
  de candidats et horodatage.
- \`bnf_bulk_notice\` : candidats filtrés avec \`notice_id\`, titre,
  auteur, éditeur, collection, tome indicatif, ISBN validés, critères de
  sélection et source.

**Aucune insertion** dans \`manga\`, \`manga_fr_edition\`,
\`user_manga_library\`, \`user_manga_inventory_declaration\` ou
\`user_manga_volume\`. Par exemple, Dragon Ball Pastel et Deluxe restent deux
éditions possibles et distinctes à confirmer plus tard par des indices
explicites ; elles ne sont pas devinées depuis les notices.

## Limites et étape suivante

- Cette livraison est **un pipeline d'import en zone d'attente**, pas une
  intégration déjà opérationnelle dans les fiches Web.
- Le rapprochement ultérieur avec les 10 033+ mangas existants devra
  privilégier l'ISBN, l'éditeur, la série, le numéro de tome et des titres
  multilingues, sans identité forcée quand les signaux divergent.
- Prise en charge **UNIMARC UTF-8 seulement** : ne pas utiliser Intermarc
  ou UNIMARC ISO 5426. Formats MARC XML, CSV et autres archives non prévus.
- Chaque fichier est importé en transaction PostgreSQL atomique. En cas
  d'échec, sa transaction revient en arrière ; une relance recommence ce
  fichier, tandis que les fichiers déjà terminés ne sont pas réimportés.
- L'aperçu porte sur les **1 000 premières notices**, pas tout le lot.
- Une recette réelle sur PC et sur un fichier BnF récent doit encore être
  effectuée ; les tests CI utilisent des notices ISO 2709 synthétiques.
