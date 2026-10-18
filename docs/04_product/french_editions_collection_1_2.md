# Mangadvisor 1.2 — Collection française, éditions et tomes

## Ce que cette version réalise

La fiche manga possède désormais un espace **Éditions françaises et mes tomes**.
Une œuvre (manga canonique d'origine Jikan), une édition française (Classique,
Deluxe, Perfect, Collector, Intégrale ou Autre) et **chaque livre ISBN physique**
sont des objets distincts.

L'utilisateur entre un ISBN-13, vérifie la notice du Catalogue général de
la Bibliothèque nationale de France, puis **confirme** le rattachement à l'œuvre,
le type d'édition et le numéro de tome. Aucun lien œuvre/édition n'est créé
automatiquement sur la seule ressemblance d'un titre.

Chaque livre lié possède deux boutons indépendants : **Possédé** / **Lu**.
Un livre peut donc être lu sans avoir été acheté, ou possédé sans avoir été lu.
Les statistiques « possédés », « lus » et « manquants » portent **uniquement
sur les ISBN enregistrés**. Ce n'est pas le nombre officiel de volumes parus
en France : les éditions peuvent regrouper plusieurs volumes japonais.

## Sources françaises fiables

La BnF met son Catalogue général à disposition via l'API SRU sans authentification
(documentation : https://api.bnf.fr/fr/api-sru-catalogue-general).

- Recherche **exacte par ISBN-13** après contrôle du chiffre de validation.
- Extraction du titre, auteurs, éditeur et date de la notice Dublin Core.
- Vérification de la présence de l'ISBN recherché dans les identifiants de la notice.
- Lien vers la notice, nom de la BnF et date de vérification conservés par livre.
- Les sources Bibliothèque nationale de France sont des **métadonnées bibliographiques**,
  réutilisables selon la licence ouverte sous réserve d'attribution et de date
  de récupération : https://www.bnf.fr/fr/conditions-de-reutilisations-des-donnees-de-la-bnf
- Les résumés protégés des éditeurs et les images de couverture françaises ne
  sont pas copiés ni téléchargés par cette fonctionnalité.

Le **type d'édition** (Deluxe/Perfect/etc.) est suggéré seulement lorsque le
titre de la notice contient explicitement un libellé identifiable. Dans les
autres cas il reste « À préciser », jamais automatiquement « Classique ».
L'utilisateur peut choisir un autre type : ce choix est conservé comme
`USER_CONFIRMED`, sans être présenté comme validé par la BnF.

L'API BnF peut être indisponible ou ne pas contenir le livre recherché.
Dans ce cas le logiciel indique clairement l'absence de résultat ou la panne,
et **n'enregistre aucune édition**. Pas de données inventées.

## Base de données et protection des collections existantes

Deux nouvelles tables sont créées **de manière additive et idempotente** au
démarrage du conteneur API :

- `manga_fr_edition` : `manga_id`, ISBN unique, titre/éditeur/auteur FR,
  type d'édition, numéro, source/lien/date et origine du type choisi.
- `user_manga_volume` : statut `is_owned` et `is_read` par ISBN et
  `user_id`, distinct des statuts globaux de lecture.

Aucune colonne, aucune entrée de `user_manga_library` n'est effacée ou
réécrite. Les historiques `owned_volumes`, `read_volumes`, notes,
favoris, statuts et imports existants sont inchangés. Leur ancien suivi
global est montré **séparément** sur la fiche : on ne l'additionne pas aux
tomes identifiés par ISBN.

L'API est toujours mono-utilisateur, réservée au PC local ; ne pas l'exposer
publiquement.

## Parcours et API

- `GET /collection/isbn/{isbn}` : aperçu vérifié, sans enregistrement.
- `GET /collection/mangas/{manga_id}/editions` : volumes liés, catégories,
  sources et statistiques sur les livres connus uniquement.
- `POST /collection/mangas/{manga_id}/editions` : confirmation explicite,
  nouvelle vérification côté serveur de l'ISBN BnF avant écriture ;
  ISBN déjà associé → 409 sans déplacement silencieux d'une œuvre à l'autre.
- `PUT /collection/volumes/{edition_id}` : état possédé/lu **par tome**,
  aucun changement des compteurs historiques.

La fiche, les actions et l'assistant de vérification ISBN sont disponibles
en **français et en anglais**, et suivent les trois designs personnels.

## Limites de cette première intégration 1.2

- Le catalogue d'éditions se construit par ISBN, **une notice à la fois**.
  La BnF n'identifie pas automatiquement, et de façon exhaustive, toutes les
  éditions et tous les tomes d'une série.
- La date d'édition peut être une année dans la notice : elle est présentée
  telle quelle, sans fausse précision.
- Aucun rapprochement ou écrasement automatique des anciens compteurs globaux ;
  un assistant de rapprochement et l'import en masse viendront plus tard.
- Les données françaises ne remplacent pas automatiquement le titre japonais
  et le synopsis Jikan ; les informations françaises sont placées dans une
  section distincte pour préserver leurs sources.
- Le rangement d'éditions particulières (Deluxe, Perfect, etc.) est un
  **choix explicite** si la notice ne le précise pas.

## Vérification

GitHub Actions utilise une base PostgreSQL **jetable** :
- Tests Python du parseur SRU/ISBN et de la migration non destructive.
- Tests JavaScript des éditions et du contenu affiché (sans HTML non fiable).
- Tests SQL HTTP des volumes possédés/lus et des anciens champs inchangés.
- Playwright sur desktop et mobile, avec vraie édition de test, bascule FR/EN,
  états et rechargement.

Le scénario CI ne dépend **jamais** de l'état réel de l'API BnF pour rester
reproductible : la notice SRU est simulée dans les tests unitaires, puis une
fiche synthétique est insérée dans la **base CI uniquement**.

## Installation Windows

Après fusion :
`git pull origin main`, démarrer Docker Desktop puis ouvrir
`mangadvisor.cmd` → **3 — Build + démarrage**.
La migration additive est créée automatiquement au démarrage de l'API.
Ouvrir `http://localhost:8501` et consulter une fiche manga.
