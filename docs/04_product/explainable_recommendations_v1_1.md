# Mangadvisor 1.1 — Des recommandations vraiment explicables

## Objectif

Une suggestion doit pouvoir répondre, en français comme en anglais, à quatre questions :
1. Quels mangas ont été pris en compte pour construire mon profil ?
2. Quels genres, thèmes et publics partage-t-elle réellement avec ces mangas ?
3. Quels sont les signaux de la communauté et les réserves connues ?
4. Quel est le score moteur et, le cas échéant, le bonus lié à l'objectif de lecture ?

Le moteur de calcul et l'ordre de recommandation restent inchangés.

## Réponse API `explanation`

Chaque candidat des endpoints `/recommendations/library`, `/recommendations/profile`
et `/recommendations/similar` inclut désormais :

- `origin` : bibliothèque / sélection manuelle / manga similaire.
- `reference_titles` : titres effectivement choisis comme sources de recommandation.
- `source_matches` : correspondances vérifiées **source par source** en comparant
  les tables de genres, thèmes et démographies de la source et du candidat.
- `shared` : attributs agrégés déjà calculés par le moteur.
- `community` : votes, nombre de mangas sources et titres communautaires remontés par le moteur.
- `cautions` : divergences remontées par les règles existantes.
- `score` : score final, éventuel score de base et bonus objectif, et signaux
  communautaires/éditoriaux/qualité/intention lorsqu'ils existent.

**Distinction fondamentale :** une ressemblance vérifiée entre Monster et un
manga conseillé ne signifie pas que Monster lui a attribué un nombre précis de
points. L'application présente les ressemblances comme des éléments de contexte,
pas comme une décomposition mathématique inventée. Les signaux individuels
ne reconstituent pas à eux seuls le score total.

## Architecture

- `apps/api/app/recommendation_explanations.py` : génération des preuves factuelles.
- Requête PostgreSQL **unique** pour les attributs de toutes les sources
  et recommandations d'une réponse : pas de N requêtes par carte.
- Aucun recalcul de score, aucun changement des fonctions de classement.
- Aucune requête `INSERT`, `UPDATE` ou `DELETE` : lecture seule.
- `apps/web/assets/explanations.js` : panneau structuré accessible et bilingue,
  texte brut du moteur (français) conservé dans un sous-panneau facultatif.
- Conseils d'amélioration sous `Pour moi` : noter ses lectures,
  réagir aux recommandations, ajuster objectifs et filtres.

## Comportement en cas de donnée absente

L'absence d'intersection source-candidat est indiquée explicitement. La simple
présence d'un titre parmi les sources utilisées ne se transforme pas en affirmation
de similarité. Si le moteur ne retourne aucun vote ou réserve, ce manque est
signifié sans inventer de causalité. Aucun pourcentage de compatibilité.

## Validation

- Tests unitaires Python du contrat : preuves strictement intersections,
  respect des scores, ordre stable et SQL de lecture seule.
- Tests Node : bilinguisme, échappement des titres HTML malveillants,
  affichage d'un score réellement disponible et absence de faux match.
- Tests PostgreSQL jetables : comparer chaque correspondance affichée aux vraies
  métadonnées des mangas sources et candidats sur **les trois endpoints**.
- Tests navigateur desktop et mobile : ouvrir les explications, passer en anglais,
  revenir en français et ouvrir la fiche depuis la recommandation.

## Limites

Ce lot améliore la transparence **sans réentraîner ni remplacer le moteur**.
Il n'explique pas encore mathématiquement chaque terme de la formule SQL ni
les poids individuels par manga-source, car ces valeurs ne sont pas calculées
isolément par le moteur existant. Il serait trompeur de les inventer.

Prochaine suite de 1.1 après validation : diagnostic de qualité des recommandations,
meilleure prise en compte des réactions et contrôle des exclusions / préférences.
