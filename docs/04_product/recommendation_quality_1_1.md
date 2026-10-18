# Mangadvisor 1.1 — Pertinence et variété des recommandations

## Objectif

Améliorer deux limites du classement actuel : des candidats avec seulement un
genre général en commun peuvent remonter haut ; plusieurs titres très proches
peuvent monopoliser les premières places.

Le score SQL original, les explications factuelles et la bibliothèque
personnelle ne sont jamais modifiés par cette sélection.

## Trois modes

- **Proche de mes goûts — CLOSE** : classement moteur historique inchangé.
  Valeur par défaut des API pour garantir la compatibilité.
- **Équilibré — BALANCED** : revalorise les candidats disposant de preuves
  d'affinité solides et les attributs variés. N'autorise un candidat qu'à
  14 points maximum derrière le meilleur score restant.
- **Explorer davantage — EXPLORE** : recherche davantage de variété sur
  une fenêtre de 28 points ; ne suggère jamais de manga sans critère
  d'éligibilité renvoyé par le moteur existant.

L'interface web utilise Équilibré par défaut. Le mode Proche reste disponible
à tout moment.

## Critères observables

Un titre dont la seule preuve est un genre commun ou un public commun
est signalé comme « preuve limitée » tant qu'il n'a aucun thème, ni
au moins deux genres communs, ni recommandation communautaire.

Pour éviter des propositions identiques, la diversification utilise
uniquement les genres et thèmes communs réellement renvoyés par le moteur.
Le score original est toujours affiché en points et reste inchangé.

Les statistiques de diagnostic portent uniquement sur les répétitions et
la couverture des preuves ; elles ne constituent **pas** des mesures de
satisfaction ou des probabilités de compatibilité.

## Exclusion des mangas déjà connus

Les candidats des trois parcours — bibliothèque, sélection manuelle et
mangas similaires — excluent tous les identifiants déjà présents dans
la bibliothèque, quel que soit leur statut (lu, possédé, à lire, rejeté…).
Les titres de référence servent toujours de sources du moteur.

Aucune modification de schéma, aucun reset, aucune écriture PostgreSQL.

## Tests de non-régression

- Tests unitaires de stabilité, invariance des scores, diversité,
  preuve limitée, fenêtre de 14/28 points et cas sans données.
- Validation API des valeurs autorisées et rétrocompatibilité.
- Test SQL de la vraie base fictive de CI : candidats éligibles, scores
  inchangés, refus et mangas possédés exclus, diagnostic cohérent.
- Navigation Playwright sur PC et mobile avec les choix Équilibré/Explorer.
- Aucune exécution destructive sur une collection personnelle.

## Limites

Le moteur ne retient que 20 candidats au maximum : la diversification dépend
de la richesse du catalogue et des recommandations Jikan. Les seuils 14/28
sont des réglages de produit testés sur données synthétiques, pas une preuve
de gain de pertinence mesuré auprès de vrais lecteurs.

La prochaine étape de la feuille de route est Mangadvisor 1.2, avec des fiches
françaises enrichies et une gestion plus fine des éditions et des tomes.
