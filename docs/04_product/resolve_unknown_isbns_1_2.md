# Mangadvisor 1.2 — Assistant de résolution des ISBN inconnus

## Problème traité

L'import CSV était déjà sûr : il ne rapprochait automatiquement que les ISBN
**déjà associés** à une œuvre et une édition françaises dans Mangadvisor.
C'était frustrant pour un nouveau manga : chaque ISBN inconnu exigeait de
quitter l'import, chercher une fiche, revenir, rouvrir le fichier.

L'assistant permet de traiter les ISBN inconnus **depuis le même aperçu CSV**,
sans nouvelle saisie du fichier.

## Parcours en trois étapes

1. **Vérifier ce tome** : depuis une ligne « ISBN non référencé », rechercher
   l'ISBN-13 **exact** dans le Catalogue général de la BnF. La notice, le
   titre français, l'auteur, l'éditeur et le lien source sont affichés.
   Si la notice manque ou si la BnF est momentanément indisponible,
   ne rien associer ; proposer un nouvel essai.
2. **Choisir la série** : proposer une *recherche modifiable* préremplie
   à partir du titre de la notice, mais jamais une correspondance
   automatique. Le lecteur recherche puis sélectionne explicitement
   une œuvre du catalogue Mangadvisor.
3. **Confirmer l'édition et le tome** : choisir Classique, Deluxe,
   Perfect, Collector, Intégrale ou Autre ; indiquer le numéro de tome.
   Une case dédiée demande de confirmer le bon rattachement œuvre/livre.
   Le bouton d'enregistrement est inactif tant qu'elle n'est pas cochée.

Le backend recontrôle la notice BnF lors de l'enregistrement par
`POST /collection/mangas/{manga_id}/editions`. Les ISBN déjà enregistrés
ne peuvent pas être rattachés silencieusement à une autre série (409).

## Retour automatique au CSV

Après association validée :
- Le CSV initial **reste présent et inchangé**.
- Mangadvisor relance automatiquement `POST /collection/import/preview`.
- L'ISBN passe de « Inconnu » à « Reconnu » si la base contient bien
  l'association fraîchement enregistrée.
- Les autres ISBN inconnus gardent leur bouton de vérification.
- L'utilisateur contrôle le nouvel aperçu puis confirme l'import global
  pour renseigner les statuts **Possédé** et **Lu** du fichier.

L'ajout de la seule édition ne marque **aucun livre possédé ou lu**.
La confirmation finale de l'import est une action séparée qui préserve
les états positifs existants.

Changer de langue FR/EN n'efface pas le CSV ni l'assistant en cours.
Si le CSV est modifié pendant l'aperçu, l'ancien jeton et l'ancien
assistant sont invalidés pour imposer une nouvelle vérification.

## Sécurité et limites

- Aucune déduction de série ni d'édition à partir d'un simple titre.
- Aucune requête groupée BnF ; l'utilisateur choisit chaque ISBN et
  le valide individuellement.
- Aucune migration ou écriture dans la bibliothèque historique :
  seuls `manga_fr_edition` et, après import confirmé,
  `user_manga_volume` sont modifiés.
- Les notices BnF restent bibliographiques, datées et attribuées.
- Si la BnF n'expose pas une notice, l'ISBN reste inconnu ; Mangadvisor
  n'invente pas d'éditeur ni de tome.
- Les éditions Perfect/Deluxe nécessitent le contrôle de l'utilisateur :
  une édition papier peut rassembler plusieurs volumes originaux.
- Aucune synchronisation MangaCollec : disponibilité API/export
  public toujours non confirmée.

## Tests

- Unitaires Node : correspondance stricte ISBN, rendu de la notice,
  aucune association sans série choisie ni consentement,
  sélection du type d'édition, titres HTML échappés.
- Parcours navigateur PC et mobile avec **notice BnF simulée**
  pour éviter de dépendre du service externe en CI : recherche
  Monster, choix explicite de la série, Perfect tome 1, confirmation,
  conservation du CSV, nouvel aperçu.
- Intégration PostgreSQL CI **réelle** : l'ISBN inconnu reste ignoré
  au départ, une réponse BnF est simulée **uniquement pour le
  rattachement via le backend**, puis le même CSV est rechargé ;
  l'import « possédé/lu » s'applique aux tables réelles de la base
  jetable et conserve l'ancienne bibliothèque à l'identique.

La recherche BnF en direct et les libellés des notices françaises
devront également être constatés sur le PC avec de vrais ISBN.

## Installation

Après fusion dans main : `git pull origin main`, Docker Desktop,
`mangadvisor.cmd` → **3 — Build + démarrage**.
Ouvrir http://localhost:8501 → **Ma bibliothèque** →
« Importer mes tomes par ISBN », puis afficher l'aperçu.
