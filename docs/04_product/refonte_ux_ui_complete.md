# Mangadvisor — refonte complète UX/UI (cahier de livraison)

Statut : chantier engagé sur la PR #89, non fusionné dans `main`.
Document de travail fonctionnel et recette ; **ne pas confondre plan et fonctionnalités livrées**.

## Design
- ADN : nuit profonde, orange ambré, ivoire, mise en avant des couvertures sous réserve de droits/sources licites.
- Desktop : sidebar stable, contenu éditorial lisible ; mobile : navigation tactile basse, actions au pouce, scanner prioritaire.
- Aucune information bibliographique inventée. Rendre les données manquantes compréhensibles sans afficher de faux totaux.
- Chaque page : état chargement, erreur, état vide honnête, clavier, écran étroit, navigation arrière.
- Le catalogue et la mangathèque privée restent séparés des outils techniques.

## Parcours à livrer
| Écran | Expérience cible | Dépendances / réserve |
| --- | --- | --- |
| Accueil | Vedette éditoriale sourcée, lecture en cours, suggestions réellement personnalisées et accès rapide collection | Ne pas présenter un catalogue générique comme recommandations personnelles |
| Découvrir | Recherche FR/EN/JP, suggestions rapides, rayons thématiques, galerie éditoriale, filtres progressifs | Alias multilingues + index Meilisearch à vérifier |
| Pour moi | Entrée conversationnelle, ambiance, surprise, explication et retours utilisateur | Les limites de preuve doivent rester affichées |
| Mes séries | Galerie/liste, recherche, statuts, suivi de lecture, accès direct à la fiche | Données bibliothèque locale |
| Mes éditions | Distinction édition/tome/ISBN et quantité possédée, scanner | Ne pas inférer les éditions à partir du titre seul |
| Mes envies | Séries à lire, indépendantes des livres possédés | Statut `WANT_TO_READ` existant |
| Gérer et importer | Outils CSV/Excel, inventaire, rapprochements, simulation avant modification | Aucune écriture sans confirmation |
| Sorties | Fil daté sourcé des éditions FR et suivi des séries, pas de faux calendrier | BnF/Scrinis et source de dates/ISBN validées ; **non livré** |
| Scanner | Scan successif, identification ISBN/édition, confirmation, anti-doublon | Couverture bibliographique FR à compléter |
| Mobile / PWA | Barre tactile, adaptation 320–430px, installation optionnelle, performance/accessibilité | PWA et mode hors ligne **non livrés** |

## Modifications déjà codées sur la branche de test
- Navigation shell persistante entre les changements de page.
- `ux-refresh.css` : style responsive, hero d'accueil illustré par vraies couvertures du catalogue, galerie Découvrir, états vides compacts.
- `Pour moi` : réglages secondaires repliés.
- Bibliothèque : quatre vues `Mes séries / Mes éditions / Mes envies / Gérer et importer`, galerie/liste, navigation au clavier, smartphone.
- `Mes envies` : réutilisation en lecture de `/library?status=WANT_TO_READ`.
- Les onglets ne modifient pas les données ; les imports conservent les parcours existants.
- Analyse syntaxique JavaScript effectuée ; aucun audit navigateur réel ou campagne responsive complète à ce stade.

## Livraison en cours — version « Mangadvisor Next » (22/10/2026)
- Nouvelle feuille de style `apps/web/assets/next-experience.css` activée après les styles existants.
- Bibliothèque : entrée éditoriale, parcours de démarrage depuis une collection vide, accès direct au scanner et à l'import, onglets série/éditions/envies/gestion, galerie/liste.
- Collection vide : bouton **aperçu** qui affiche des mangas du catalogue public sans écrire dans la mangathèque. Bandeau explicite « pas ta collection » et fermeture réversible.
- Découvrir : bannière dédiée, accès au conseiller, genres interactifs reliés au filtre réel, galerie plus visuelle.
- Pour moi : nouvel écran d'accueil de recommandation et accès au conseiller / suggestions issues de la bibliothèque.
- Fiche manga : couverture mise en avant, titres, actions et synopsis plus lisibles (styling ; modèles bibliographiques inchangés).
- Sorties : destination accessible dans navigation, présentant honnêtement l'absence de planning français vérifié. **Aucune date livrée**.
- Mobile : cinq destinations en navigation inférieure, contrôles tactiles et grilles adaptées.
- Aucune migration SQL, aucun inventaire fictif attribué à l'utilisateur ; les cartes d'aperçu sont celles du catalogue public.
- Syntaxe JS évaluée sur les fichiers modifiés ; l'ensemble nécessite toujours une vraie recette navigateur et mobile.

## Phases restantes avant validation finale
1. Vérifier et corriger l'UX de ces vues dans le navigateur, notamment navigation clavier, écrans vides, accès au scanner, recherches et import.
2. Page fiche manga : hiérarchie couverture/synopsis/édition/tomes, CTA ajout à la collection et retours visuels.
3. Découvrir : filtres progressifs, recherche plus rapide, rayons éditoriaux sans inventer des catégories calculées.
4. Pour moi : fusionner intelligemment conversation/ambiance/profil sans perdre les différentes méthodes existantes ; explicabilité.
5. Page Sorties sur une source fiable, avec avertissement explicite si les données sont incomplètes ; pas de dates supposées.
6. Tests de largeur 320 / 375 / 390 / 768 / 1440 / 1920 ; accessibilité clavier, labels, contrastes, animations réduites.
7. Vérifier latence / requêtes et éviter les reconstructions inutiles. Envisager PWA une fois les parcours stabilisés.
8. Recette de bout en bout sur environnement Docker de test sans altérer `main` ou la vraie bibliothèque.

## Reprise technique BnF / GitHub
- `mangadvisor_realtest` : 85 776 œuvres contrôlées ; sauvegardes et volumes Docker à protéger.
- Audit Berserk : 2 tests automatisés réussis.
- Scrinis : plafond d'affichage 20 ISBN dans l'adaptateur, à corriger avant tout calcul de volumes.
- BnF : 83 ISBN candidats sur cinq œuvres ; recherches paginées à rendre réellement plus complètes ; toujours des candidats non confirmés.
- Conserver l'issue #71 sur la bibliographie française.
- La PR #89 est active. Vérifier #87, #68, #38 avant toute fermeture ; **ne rien fusionner dans main sans validation**.
