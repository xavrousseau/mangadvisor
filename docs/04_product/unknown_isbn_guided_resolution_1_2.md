# Mangadvisor 1.2 — Assistant d'identification des ISBN inconnus

## Objectif

Permettre de compléter progressivement un gros inventaire français **depuis
l'aperçu d'import CSV**, sans recopier les lignes ou quitter la bibliothèque.

L'import CSV précédent ne peut appliquer les statuts que pour les ISBN déjà
présents dans `manga_fr_edition`. Un ISBN inconnu était seulement signalé :
cette évolution lui ajoute une action **« Vérifier cet ISBN »**.

## Parcours utilisateur

1. **Ma bibliothèque → Importer mes tomes par ISBN** : choisir ou coller un
   CSV contenant des ISBN, vérifier le fichier.
2. Sur une ligne « ISBN non référencé », cliquer **Vérifier cet ISBN**.
3. Mangadvisor recherche une notice **exacte** via l'API de la BnF déjà
   intégrée (`GET /collection/isbn/{isbn}`). Le titre du livre, l'éditeur,
   l'auteur, sa date et le lien vers la notice sont affichés **avec leur
   provenance** ; les sources non vérifiées sont rejetées.
4. **C'est à l'utilisateur de rechercher et choisir la série Mangadvisor**.
   Une notice de livre n'établit pas à elle seule le manga canonique :
   aucun rapprochement automatique par similarité de titre.
5. L'utilisateur confirme la **catégorie d'édition** (Classique, Deluxe,
   Perfect, Collector, Intégrale, Autre, À préciser) et saisit
   **explicitement le numéro de tome** (aucun numéro 1 attribué par défaut).
6. Un dernier clic de confirmation appelle le **POST existant**
   `/collection/mangas/{id}/editions`. Ce dernier **recontrôle l'ISBN auprès
   de la BnF côté serveur**, refuse les doublons et n'efface aucune donnée.
7. Mangadvisor réanalyse **le même CSV conservé en mémoire**. L'ISBN
   nouvellement associé passe d'« Inconnu » à « Reconnu ».
   L'utilisateur peut résoudre d'autres ISBN, puis cliquer séparément sur
   **Confirmer l'import non destructif** pour appliquer les états
   « Possédé » et « Lu ».

**Important :** confirmer l'association à la série ne marque pas
automatiquement le livre comme acheté ou lu. La modification des statuts
n'a lieu que lors de l'import final, conformément au parcours précédent.

## Cas d'erreur et préservation

- Notice BnF absente ou indisponible : erreur claire, **aucun enregistrement**.
- Manga introuvable dans le catalogue Mangadvisor : changer de recherche ;
  aucune série ne sera inventée.
- Mauvais livre ou doute sur la correspondance : bouton **Fermer**.
- ISBN déjà référencé entre-temps : l'API renvoie 409 ; relancer l'aperçu
  permet de vérifier son association actuelle.
- Changement du contenu CSV : l'ancien aperçu, ses jetons de confirmation et
  l'assistant actif sont invalidés.
- Le navigateur ne conserve le CSV que durant la session en mémoire de
  l'onglet ; il n'est pas envoyé vers un service tiers. Seule la recherche
  de l'ISBN demandé interroge la BnF.
- **Aucune modification du schéma**, aucune modification de la bibliothèque
  historique (`user_manga_library`) et aucun changement des valeurs
  possédées/lues existantes sans confirmation spécifique.

## Sources et limites

Le Catalogue général de la BnF fournit des métadonnées bibliographiques,
pas une cartographie garantie des séries et éditions de mangas.
Source : https://api.bnf.fr/fr/api-sru-catalogue-general

Le service BnF peut ne pas contenir certains tomes ou leur ISBN. L'ajout
manuel de livres non présents dans la BnF n'est **pas** réalisé dans ce lot,
afin de préserver la traçabilité du catalogue.

Ce parcours ne constitue **pas** une synchronisation MangaCollec :
aucune API officielle de collection n'a été vérifiée. Le CSV doit être
fourni par l'utilisateur et contenir des ISBN.

## Validation technique

- Module de rendu `unknown-isbn-view.js` sans HTML non fiable ; l'URL source
  n'est cliquable que si elle cible `https://catalogue.bnf.fr`.
- Tests Node : bouton uniquement pour ISBN inconnu, BnF seule insuffisante,
  sélection manuelle obligatoire, volume numérique non présumé,
  échappement des titres/éditeurs et refus des URL tierces.
- Tests Playwright PC et mobile : notice BnF **simulée** pour reproductibilité,
  recherche **réelle** de manga dans le catalogue CI, choix explicite de série,
  numéro manuel, fermeture sans écriture et conservation de l'aperçu.
- La création effective via l'API a déjà des tests unitaires de confirmation
  de source, doublon ISBN et manga inconnu dans `tests/test_collection_routes.py`.
- Les tests complets de l'import CSV et de préservation des compteurs historiques
  continuent d'être exécutés sur une base PostgreSQL CI jetable.

## Installation

Après fusion sur `main`, actualiser le GitHub local puis démarrer
`mangadvisor.cmd` → **3 — Build + démarrage**. L'interface web reste
sur `http://localhost:8501`.

L'assistant sera visible **dans le tableau d'aperçu de l'import CSV de
« Ma bibliothèque »**, uniquement sur les lignes d'ISBN inconnus.
