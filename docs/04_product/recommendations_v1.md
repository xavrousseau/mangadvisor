# Mangadvisor 1.0 — Recommandations personnalisées (lot 4)

## Périmètre

Moderniser la présentation, sans réécrire la logique métier. Les endpoints et scores du moteur V0.8 restent inchangés.

### Écran « Pour moi »

Deux parcours sont réunis dans le même onglet :

1. **Ma bibliothèque** : le moteur utilise les lectures, notes et favoris existants. Objectif au choix : proche de mes goûts, quoi lire ensuite, série terminée / plutôt courte.
2. **Quelques mangas préférés** : recherche dynamique des titres (non limitée aux 500 premiers), sélection de 1 à 10 mangas et recommandation selon ces œuvres.

Les deux modes reprennent les paramètres déjà disponibles : note communautaire minimale, séries terminées et exclusion des thèmes éloignés du profil.

### Résultats

- Grille de deux cartes par ligne, couvertures provenant du lot 2.
- Titre, note MyAnimeList **sur 10** et **score interne en points** : ce dernier n'est **ni un pourcentage ni une probabilité**. Aucune conversion arbitraire.
- Résumé factuel construit uniquement à partir des données du moteur (genres, thèmes, cible, signaux communautaires). En l'absence de critères détaillés, aucun critère n'est inventé.
- Volet « Pourquoi ce manga ? » avec l'explication complète, les facteurs techniques, les votes et les éléments pouvant éloigner la recommandation.
- Bouton de fiche détaillée qui ouvre la vraie fiche sans faire disparaître les résultats.

### Continuité des recherches

Les résultats sont conservés en session Streamlit lorsque l'utilisateur ouvre une fiche ou interagit avec l'interface. Ils sont invalidés si les titres, filtres, objectif ou nombre de résultats changent. Une modification locale de la bibliothèque (ajout, suppression, import réel) invalide ses recommandations précédentes.

Les recommandations similaires depuis « Découvrir » utilisent les mêmes cartes, sans changement de leur API ni de leur ordre.

## Limites et contraintes

- L'application demeure locale et mono-utilisateur ; ne pas déployer publiquement sans authentification.
- Les titres proposés en recherche manuelle proviennent du catalogue Mangadvisor actuellement chargé.
- Les images du CDN peuvent être manquantes ; le visuel de substitution reste disponible.
- Les valeurs de score internes sont celles de l'API et ne doivent pas être présentées comme des taux de compatibilité.
- Aucun SQL du moteur, changement de schéma ou suppression de données.
- Tests unitaires sur la présentation des scores et preuves, et syntaxe Python dans GitHub Actions.
- Pas de validation visuelle avec Docker et PostgreSQL dans cet environnement : à effectuer avant fusion.

## Ordre de livraison

PR #1 : thème → PR #2 : couvertures → PR #3 : découverte → PR #4 : recommandations. Les branches restent empilées, aucun merge automatique vers \`main\`.
