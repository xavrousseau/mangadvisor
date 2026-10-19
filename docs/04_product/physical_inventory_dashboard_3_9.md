# Mangadvisor 3.9 — Ma collection physique par édition

## Objectif

L'import sécurisé 3.8 conservait déjà les éditions déclarées dans PostgreSQL. La version 3.9 les rend directement visibles dans **Ma bibliothèque** et sur **les fiches de chaque manga**, sans mélanger les quantités physiques aux livres validés par ISBN.

## Ma bibliothèque

Un volet **Mon inventaire physique par édition**, ouvert par défaut, regroupe les entrées par œuvre canonique. Chaque édition déclarée possède sa propre ligne indiquant son nom, ses tomes déclarés, les exemplaires identiques en double et les volumes d'autres éditions encore non identifiées.

Les compteurs distinguent le **nombre d'œuvres** de celui des **entrées d'édition**. Les quantités physiques ne constituent ni un nombre de tomes narratifs distincts, ni une preuve de complétude éditoriale.

Une carte donne accès à la fiche de l'œuvre. Dans celle-ci, les éditions déclarées sont affichées avant le panneau des **ISBN français vérifiés**, sans les additionner ni en déduire des statuts de lecture.

### Exemple de deux éditions

Une même œuvre, Dragon Ball, peut posséder deux éditions déclarées : Pastel (42 volumes) et Deluxe (34 volumes). Ce sont **deux versions physiques pour une œuvre**, pas 76 tomes narratifs différents. La forme éditoriale précise et les ISBN de chaque tome doivent être confirmés séparément.

## API et protection des données

Le GET existant **/inventory/declarations** renvoie ses champs historiques, plus un objet de compteurs summary et un indicateur limited. Il accepte également le filtre **?manga_id=123** pour afficher une seule œuvre.

Les compteurs sont : works, edition_entries, main_volumes, identical_duplicates, other_editions_unidentified et physical_total_declared.

Tout est en lecture seule : aucune migration, aucun changement d'ISBN, aucune note ni état de lecture modifié. Les données privées ne sont pas envoyées sur GitHub.

## Utilisation après mise à jour

1. Sauvegarde avec mangadvisor.cmd option **17**.
2. Mets à jour via git pull origin main et redémarre Docker Desktop puis option **3**.
3. Lorsque tu voudras valider l'import réel : CSV privé dans private-data/mangatheque.csv puis menu **21** ; prévisualisation obligatoire et confirmation des seules correspondances sûres.
4. Va dans **Ma bibliothèque** pour voir l'inventaire physique. Sur chaque fiche manga, les versions déclarées apparaîtront avant les ISBN.

Le tableau reste **vide tant qu'aucun inventaire n'a été importé** sur le PC. Les tests GitHub utilisent des données synthétiques.

## Vérification

Tests Python : sommes et distinction des œuvres/éditions. Tests JS : regroupement des deux éditions, provenance des compteurs et échappement HTML. PostgreSQL CI et navigateur Chromium ordinateur/mobile : une importation fictive est suivie d'un affichage en bibliothèque et sur une fiche manga. Les anciennes suites ISBN, sauvegarde et HTTPS restent requises.

## Étape suivante

À terme, rapprocher chaque édition déclarée des ISBN réellement enregistrés et permettre de suivre les tomes individuels **après confirmation**, sans supposer qu'une série est complète ni que tous ses livres sont en vente.
