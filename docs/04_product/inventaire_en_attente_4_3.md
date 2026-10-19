# Mangadvisor 4.3 — conserver les entrées de la mangathèque sans correspondance

## Pourquoi cette évolution ?

Un inventaire physique peut contenir des mangas dont le titre français ne figure
pas exactement dans le catalogue, des variantes de noms, des livres documentaires
ou plusieurs œuvres plausibles. **Il ne faut jamais forcer le rapprochement.**

La version 4.3 distingue désormais trois états :

- **Déclaration reconnue** : une œuvre unique du catalogue est identifiée et
  son édition déclarée est enregistrée séparément des ISBN vérifiés.
- **Déclaration déjà présente** : aucune écriture supplémentaire (idempotence).
- **Déclaration en attente** : entrée conservée intégralement dans
  `user_manga_inventory_pending`, sans `manga_id`, sans ISBN, sans lecture
  ni note inventée.

Les quantités, intitulés, références et éditions d'un inventaire personnel
restent exclusivement dans les fichiers privés et la base locale. Les tests du
dépôt utilisent uniquement des données synthétiques fictives.

## Comment utiliser l'option 21

1. Conserver son fichier dans `private-data/mangatheque.csv`.
2. Ouvrir `mangadvisor.cmd`, puis sélectionner **21**.
3. Lire d'abord l'aperçu **sans aucune écriture**.
4. Si l'utilisateur accepte de poursuivre après l'aperçu, le script propose
   distinctement **`CONSERVER N`** pour les N lignes `REVIEW_MISSING`
   et `REVIEW_AMBIGUOUS`.
5. Cette confirmation **ne crée aucun manga**. Elle préserve seulement les
   déclarations non associées à une fiche canonique.
6. Si des entrées `READY` existent également, leur import classique
   demande toujours une confirmation séparée.

La sauvegarde de ces lignes est répétable : une ligne déjà conservée à
l'identique n'est pas enregistrée une seconde fois. Si les titres ou quantités
d'une ligne conservée ont changé, l'opération refuse de les écraser et exige
une réconciliation manuelle.

## Lecture dans l'application

La page **Ma bibliothèque** (site principal sur 8501) affiche les séries
identifiées et une section **En attente de rapprochement** pour les lignes
conservées sans association. Les quantités physiques sont clairement
distinguées des ISBN réels et de la bibliothèque de recommandation.

L'API expose :

- `POST /inventory/preview` : aperçu en lecture seule.
- `POST /inventory/pending/save` : conservation explicitement confirmée avec
  le jeton de l'aperçu courant, sans écriture de `user_manga_library`.
- `GET /inventory/pending` : lecture des déclarations à rapprocher.
- `GET /inventory/declarations` : déclarations **reconnues**, inchangées.

## Limites honnêtes de la version

**Conserver** un titre en attente n'est pas **l'associer** à une œuvre.
Les 41 titres manquants et 8 titres ambigus sont toujours à rapprocher lors
d'une prochaine étape avec recherche de titres alternatifs, candidats
expliqués et validation humaine. Les ISBN et éditions françaises demandent
toujours une confirmation de leurs notices.

Toute migration est additive. Pas de suppression SQL, pas de réinitialisation
des volumes et pas d'import de fichier personnel dans GitHub.

## Vérifications

La CI sur PostgreSQL jetable vérifie un inventaire de démonstration avec
lignes identifiées et inconnues, l'idempotence de la conservation, le refus
d'un jeton expiré, le maintien de la bibliothèque avant/après, et
l'affichage de l'attente sur PC et mobile, sans lien vers un faux manga.
