# Mangadvisor 1.2 — Fiches françaises fiables (lot 1)

## Décisions

Une **œuvre originale** (catalogue Jikan/MyAnimeList) et un **livre physique
français** (ISBN et notice BnF) sont deux notions distinctes.
Les informations françaises ne remplacent **pas** sans contrôle les titres,
résumés, dates ou nombres de tomes de l'œuvre japonaise.

## Ce qui change

### Recherche BnF plus rigoureuse

L'API Catalogue général de la Bibliothèque nationale de France est
interrogée en SRU 1.2, format Dublin Core, avec un ISBN-13 contrôlé.
Chaque réponse est maintenant vérifiée sur :

- un ISBN complet, avec bornes de numéro, et non une sous-chaîne de treize
  chiffres tirée d'une succession plus longue d'identifiants ;
- un identifiant de notice ARK BnF strict (pas de faux lien ni de redirection) ;
- un XML sans déclaration DTD/ENTITY, et une limite de taille de 1,5 Mo ;
- la présence d'un vrai titre bibliographique.

Une notice invalide ou sans identifiant sûr n'est **pas** présentée comme
vérifiée. En l'absence de correspondance, aucun livre n'est créé.
Une indisponibilité technique du service reste signalée distinctement.

Sources : https://api.bnf.fr/fr/api-sru-catalogue-general
et https://api.bnf.fr/fr/conditions-generales-dutilisation-du-site-bnf-api-et-jeux-de-donnees.

### Fiches manga enrichies

Le panneau « Éditions françaises et mes tomes » possède désormais :

1. Un espace « Informations françaises vérifiées » qui montre les
   éditeurs et auteurs tirés des **livres enregistrés**. Il ne prétend
   pas détenir un titre français officiel pour l'œuvre entière.
2. Les livres regroupés par type **Classique, Deluxe, Perfect, Collector,
   Intégrale, Autre ou À préciser**. Pour chaque type, affichage du nombre
   de livres renseignés, possédés et lus. Le groupe n'est pas un inventaire
   exhaustif des tomes publiés.
3. Sur chaque carte : numéro de tome, titre exact de la notice française,
   éditeur, auteur, ISBN, source, lien ARK et date de vérification lorsqu'ils
   sont enregistrés. Le type choisi par l'utilisateur reste identifié.
4. L'ajout d'un nouvel ISBN ne présume plus le tome 1 ; le numéro doit
   être saisi avant l'enregistrement.

Les statuts « Possédé » et « Lu » restent indépendants, et les anciens
compteurs globaux restent affichés **séparément**, sans addition.

### Architecture

- `apps/api/app/collection.py` : ISBN exact, lien ARK autorisé, résumé
  bibliographique de livres vérifiés (`french_overview` dans la réponse
  existante de `GET /collection/mangas/{id}/editions`).
- `apps/web/assets/collection-view.js` : présentation sourcée, groupes
  par type, numéro de volume non présumé.
- `apps/web/assets/i18n.js` : libellés en français et en anglais.
- `apps/web/assets/app.css` : adapté aux trois designs et au mobile.

Aucune migration, **aucune écriture automatique** et aucune modification
des données historiques de `user_manga_library`.

## Vérifications

- Unitaires Python : ISBN exact et checksum, refus d'un identifiant
  concaténé, ARK malveillant, XML DTD/ENTITY interdit, aperçu des
  métadonnées qui n'invente pas un titre officiel de série.
- Tests frontend : genres d'édition séparés, HTML non fiable échappé,
  groupe vide honnête, numéro de tome saisi explicitement.
- Tests Docker/PostgreSQL CI : rendu de la fiche réelle avec livre
  synthétique français, liens sources et navigation PC/mobile ; vérification
  des champs historiques et du suivi de tomes existant.

## Limites et suite

Le catalogue BnF n'est **pas** un catalogue exhaustif des éditions
commerciales françaises. La recherche sur un vrai ISBN dépend de la notice
disponible et de l'accès à la BnF sur le PC de l'utilisateur.

Cette évolution clôt la **fiabilisation de la présentation des notices déjà
retrouvées**, pas la constitution automatique d'une bibliographie complète.
Étape suivante : série → éditions réelles → grille de tomes/progression,
avec notion de tomes inconnus distincte de tomes prouvés comme manquants.

Plus tard : scanner ISBN, importer des lots plus grands, intégrer un export
MangaCollec **uniquement** si sa disponibilité et son droit d'usage sont
confirmés.
