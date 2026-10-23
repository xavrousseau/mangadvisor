# Retour d'expérience — ce que les autres discussions nous ont appris

## Acquis fonctionnels à ne pas perdre
- UI Web unique Nginx sur `localhost:8501`, thèmes et présentation moderne validés ; ne pas revenir au Streamlit historique. Le « voir la fiche » doit être testé, pas seulement les cartes.
- Catalogues Jikan/Tenrai, enrichissements Wikidata/BnF/Scrinis, moteur de recommandation et conseiller guidé. Reprendre les algorithmes seulement après audit de la qualité des entrées.
- Gestion d'une mangathèque physique avec CSV/XLSX, quantités, statut de lecture, ISBN/tome/édition, sauvegardes PostgreSQL vérifiées et restauration. Le scanner HTTPS mobile/IA locale sont utiles mais ne doivent pas bloquer le catalogue.
- Profil lecteur et recommandations avec équilibre « proche / équilibré / explorer », exclusions d'horreur/gore, et explications vérifiables.
- Parcours Windows piloté par un seul `mangadvisor.cmd` compréhensible pour un utilisateur non développeur.

## Échecs constatés
- 26 options de menu, 130 tests, 76 docs et 114 branches : une étape historique n'est pas une fonctionnalité à maintenir.
- Migrations et sauvegardes Windows : erreurs natives PowerShell 5.1 / arguments `pg_dump`, problèmes d'environnement PostgreSQL, conteneurs API ≠ engine, API Python `ModuleNotFoundError: pipelines`. Les tests doivent utiliser la **vraie image de production Windows/Docker**.
- Git local divergent, fichiers non suivis, mise à jour bloquée ; sauvegardes, `.env`, `private-data`, `data/raw/jikan` et volumes PostgreSQL doivent rester hors des suppressions Git.
- Un « titre similaire » n'est pas une identité : Adieu Eri/Sayonara Eri doit venir d'un lien vérifié ; alias Radiant/Ikujitsu et Fairy Tail/Bishoujo Hatsu Shibori sont des contre-exemples.
- BnF : candidats de plusieurs éditions et langues ; Berserk Prestige/Collector et dérivés doivent rester distincts ; Tokyo Ghoul et :re ne doivent pas hériter des mêmes ISBN.
- Les copies du `catalogue_work` précédent ne changeaient pas l'application, qui continuait à lire l'ancien index : **les lectures applicatives sont migrées dans la même étape que les tables**.
- Plusieurs passages CI verts sur la logique simulée n'ont pas empêché des erreurs sur la vraie installation Windows. Une seule recette de bout en bout en environnement réel évite mieux ces trous que 100 tests unitaires.

## Chiffres de référence avant reconstruction
- 85 776 fiches catalogue ; 228 010 alias anciens ; 5 420 conflits dans le graphe transitoire.
- Après l'option 26 : 313 864 titres et claims, seulement 153 œuvres avec au moins un titre FR sourcé et non rejeté, 781 livres BnF candidats et 10 revendications ambiguës croisées ; aucun tome français confirmé.
- Mangathèque : les exports et comptes ont varié selon la date et le type de déclaration (53 œuvres liées, ~49 lignes à revoir, 1 672 quantités déclarées dans un fichier initial). **Ne pas mélanger les comptes d'œuvres, éditions, tomes et quantités.**

Ces chiffres sont une photographie de l'ancien système, **pas des objectifs de remplissage**. La V2 doit prouver la qualité de ses liens et des éditions.
