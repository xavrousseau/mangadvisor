# Mangadvisor 1.2 — Bibliographie française exploratoire par titre

## Besoin

Mangadvisor pouvait déjà vérifier un livre français par **ISBN connu**,
mais il fallait d'abord disposer de son code. Cette évolution offre
une recherche BnF par **titre français**, directement depuis la fiche
d'un manga, pour découvrir les notices de livres dont l'ISBN n'a pas
encore été ajouté à notre catalogue.

## Conception

### Un résultat bibliographique n'est pas une édition complète

Les recherches utilisent le service officiel SRU 1.2 du Catalogue général
de la Bibliothèque nationale de France :
https://api.bnf.fr/fr/api-sru-catalogue-general

Les métadonnées Dublin Core sont transmises avec leur ISBN-13,
titre de notice, auteur, éditeur, date telle que renseignée, langue déclarée
(français, multiple, autre ou inconnue) et lien ARK. Une notice au
Catalogue général **ne suffit pas à prouver qu'un livre est en français**.

L'interface affiche clairement :

- des **notices de livres**, pas un titre français officiel de l'œuvre ;
- un maximum de **18 ISBN** valides à partir des **30 premières notices**
  de la recherche, sans prétendre exploiter toutes les pages de résultats ;
- la mention *« Résultats partiels »*, sans présumer l'inventaire de tous
  les tomes parus ni la disponibilité commerciale actuelle ;
- « Déjà associé à cette fiche » si l'ISBN est enregistré pour ce manga ;
- « Vérifier cet ISBN et l'associer » dans le cas contraire.

### Parcours précis

1. Ouvrir une fiche manga, descendre à **Éditions françaises et mes tomes**.
2. Utiliser **Explorer les livres français** : le champ titre est
   prérempli avec le titre catalogue, mais reste modifiable pour chercher
   le titre français réellement édité.
3. Choisir un résultat. Mangadvisor **vérifie de nouveau le même ISBN**
   par son endpoint BnF exact existant, et affiche une fiche de prévisualisation.
4. L'utilisateur confirme la bonne œuvre, le type d'édition et le numéro
   de tome. Rien n'est créé à partir de la seule recherche par titre.
5. Après ajout, la liste de livres recensés est rafraîchie. Un ISBN
   déjà associé apparaît désormais comme enregistré.

Cette première itération **ne charge pas automatiquement** tous les
tomes d'une série à partir d'une requête par titre, et ne remplace pas
les titres ni les descriptions japonais sans source française fiable.

### Sécurité et protection des données

- Une recherche GET, aucun accès écriture pendant l'exploration.
- Requête SRU CQL limitée à `bib.title all "..."`, après normalisation et
  rejet des opérateurs, jokers et guillemets CQL.
- Réponse XML plafonnée à 2 Mo, refus de DTD et ENTITY.
- Inclusion **uniquement** d'ISBN-13 avec checksum valide, notices dotées
  d'une URL ARK BnF vérifiable ; déduplication des ISBN.
- Lien HTML limité à `https://catalogue.bnf.fr/ark:/12148/cb...`,
  aucun HTML brut issu des résultats.
- Confirmation utilisateur explicite et second contrôle ISBN côté serveur
  à la création. Les ISBN déjà associés ailleurs sont refusés.
- Aucune migration, suppression, réécriture des états possédé/lu ou des
  anciens compteurs ; aucun appel automatique à la BnF en tâche de fond.

### Vérifications

- Tests unitaires Python : normalisation du titre, injection CQL, checksum
  ISBN, déduplication, ARK refusés, XML malveillant, limites et échec réseau.
- Tests Node : affichage FR, résultat connu/inconnu, échappement, URL
  BnF sûre, périmètre incomplet.
- Test Playwright sur PC et mobile : réponse BnF **simulée**, voir des
  ISBN déjà reconnus et à valider, lancer la vérification exacte et
  constater que le numéro de tome reste vide. Aucune insertion pour
  un résultat de recherche.
- Tests Docker, PostgreSQL de CI **jetable**, plus les contrôles existants.

L'accès réseau réel au SRU BnF devra être confirmé sur un PC lors
d'une recherche avec un vrai titre français. Les jeux de données de
test ne doivent pas être présentés comme de vraies notices BnF.

## Prochaine amélioration

Enrichir ce catalogue de manière progressive et **provenance par provenance**,
avec classement par édition éditoriale précise (éditeur/collection/tirage)
lorsque ces attributs sont réellement documentés, puis proposer des
indicateurs de complétude sur un inventaire français explicitement vérifié.

Pour l'instant, le seul taux de progression affiché reste celui des
ISBN identifiés. Un numéro absent ne devient pas automatiquement un
« tome publié et manquant ».

### Installation Windows

Après fusion : `git pull origin main`, lancer Docker Desktop et
`mangadvisor.cmd` → **3 — Build + démarrage**.
Ouvrir `http://localhost:8501` et choisir une fiche manga.
