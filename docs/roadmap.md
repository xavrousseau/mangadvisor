# Plan d'exécution — une étape = un livrable vérifiable

## Étape 0 — Préserver et simplifier
**Livrable** : branche de reconstruction avec moins de 15 fichiers au départ, archive Git du dernier `main` ; inventaire de 344 fichiers et liste courte du code utile. Aucun changement au poste local ni aux volumes.
**Validé quand** : dépôt propre consultable, archivé, structure et rôles sans doublon.

## Étape 1 — Démarrage minimal
**Livrable** : `compose.yaml`, PostgreSQL, FastAPI, UI Web statique et `mangadvisor.cmd` épuré.
**Validé quand** : sur Windows, « Installer et démarrer » donne une page et `/health` fonctionnels ; « Arrêter » laisse le volume intact. Une seule recette réelle + tests ciblés.

## Étape 2 — Catalogue international brut
**Livrable** : importer dans une **base isolée** une copie des archives publiques déjà exportées (Jikan/MAL 85 776 fiches), sans retélécharger ces données tant que leur intégrité est vérifiée. Connexion fournisseur autorisée pour les nouveautés ensuite. Les JSON bruts ont leur hash et ID source.
**Validé quand** : nombre d'enregistrements, conflits d'ID et erreurs de parsing chiffrés ; relancer l'import ne double aucune ligne ; la base personnelle reste inchangée.

## Étape 3 — Œuvres et titres qualifiés
**Livrable** : remplir `work`, `external_identifier`, `title_claim`, `relation_claim` avec règles de preuve; créer les nouvelles œuvres sans MAL à partir de sources légitimes (ex. manga français).
**Validé quand** : cas Radiant/Fairy Tail/Adieu Eri résolus selon preuves, erreurs mises en attente, aucune fusion induite par `title_synonyms`. Tableau de couverture FR/EN/JA avec sources.

## Étape 4 — Référentiel français : éditions / volumes / ISBN
**Livrable** : traitement bibliographique BnF (SRU/exports sous licence ouverte) et sources éditeurs autorisées ; fiches d'édition confirmées et publications, candidats incertains séparés.
**Validé quand** : Dragon Ball Pastel/Deluxe, Berserk éditions et Tokyo Ghoul/:re ne sont pas confondus ; statistiques éditions, tomes, ISBN et refus justifiés.

## Étape 5 — Vraie consultation du catalogue
**Livrable** : API et UI utilisent seulement les œuvres/titres qualifiés; accueil, découvrir, recherche FR/EN/JA, filtres et fiches de manga, éditions françaises ; recherche Postgres d'abord.
**Validé quand** : mêmes résultats utiles entre la base et l'écran, liens « voir la fiche » fonctionnels, suppression des faux positifs connus. Aucun index obsolète.

## Étape 6 — Bibliothèque personnelle
**Livrable** : import CSV/XLSX avec simulation, résolution explicite des ambiguïtés, suivis/notes/statuts, éditions distinctes, sauvegarde/restauration. Réutiliser la collection existante comme **jeu de recette**, pas comme référentiel.
**Validé quand** : quantités déclarées intactes, 53 œuvres suivies/49 lignes difficiles examinées sur données copiées sans affecter l'original, aucun ISBN ni tome inventé.

## Étape 7 — Recommandations et conseiller
**Livrable** : recommandations expliquées selon affinités, genres, thèmes, démographie, progression et exclusions des titres possédés ; conseiller guidé par envies, sources transparentes ; IA locale optionnelle et scanner si l'infrastructure validée le permet.
**Validé quand** : parcours Naruto/Bleach/HxH, scénarios « sans gore » et exclusions, test sur collection fictive + copie autorisée ; explications cohérentes et fiches accessibles.

## Étape 8 — Livraison V1
**Livrable** : commandes utilisateur simples, documentation compacte, sauvegarde vérifiée, recette complète Windows, CI minimale; bascule réversible après tests et comparaison catalogue V1/V2.
**Validé quand** : lancement depuis zéro, import source, consultation, bibliothèque et recommandations fonctionnent de bout en bout sans script manuel supplémentaire. **V2 ensuite : UX seulement.**

## Discipline de développement
Un seul chantier ouvert à la fois ; **aucune PR par test ou micro-correction**. Une suite d'essais contrôlée en cours de chantier, un seul point de fusion lorsque le lot est vert. Maximum quatre familles de tests permanentes. Les scripts d'exploration temporaires restent hors du Git.
