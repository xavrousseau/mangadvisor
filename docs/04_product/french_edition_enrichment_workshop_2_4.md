# Mangadvisor 2.4 — Atelier d’enrichissement des éditions françaises

## Fonctionnement

Dans la fiche d’une série, ouvrir **Atelier d’enrichissement français** et cliquer sur **Rechercher les éditions**. Mangadvisor effectue jusqu’à deux recherches BnF à partir des titres déjà présents dans le catalogue (titre principal et titre anglais, s’ils sont différents). La recherche est déclenchée par l’utilisateur, jamais automatiquement en arrière-plan.

L’atelier classe les notices ISBN candidates en trois catégories :
- **À vérifier** : ISBN candidat issu de la recherche BnF par titre, mais non encore rattaché localement.
- **Déjà associé ici** : ISBN déjà enregistré sous cette œuvre. Aucune nouvelle association.
- **Déjà lié ailleurs** : ISBN enregistré pour une autre œuvre. Aucune nouvelle association possible ici.

Les candidats non enregistrés sont triés par présence des mots du titre de l’œuvre dans le titre du livre BnF, sans appeler cela une certitude ou une probabilité de correspondance. Un titre commun ne prouve jamais le lien avec la série.

Pour ajouter un livre : cliquer sur **Vérifier cet ISBN**. Le parcours existant vérifie de nouveau la notice BnF **exactement par ISBN**, et demande ensuite une confirmation explicite de l’œuvre, du format (Classique, Deluxe, Perfect…) et du numéro de tome. Seul le bouton de confirmation réalise l’enregistrement. L’atelier conserve les autres candidats en attente et reclasse localement l’ISBN confirmé parmi les ISBN déjà associés.

## Limites importantes

Cette recherche **n’est pas exhaustive** : deux recherches de titres maximum, premières pages BnF uniquement, au plus 30 ISBN affichés, et réponses de recherche susceptibles d’être partiellement indisponibles. L’atelier n’est ni une source de vérité sur les séries françaises complètes, ni une vérification de disponibilité en librairie.

Les données peuvent contenir des notices homonymes ou concernant une autre série. Une vérification humaine est donc impérative. Aucune édition, numéro de tome ou ISBN ne sont inventés. Les notices BnF candidates ne sont pas automatiquement « vérifiées », même quand les mots du titre correspondent.

Pour une série connue sous un autre nom en français, la recherche BnF **manuelle par titre** reste disponible sous la même fiche, ainsi que la recherche exacte par ISBN.

## Architecture et sécurité

Endpoint GET /collection/mangas/{manga_id}/enrichment, en lecture seule : interrogation BnF existante, déduplication des ISBN, statut d’association obtenu par une requête SQL paramétrée contre la table manga_fr_edition. Contrôle des conflits d’ISBN enregistrés globalement. Pas de nouveau stockage ni de migration.

L’interface réutilise les routes d’ISBN et de confirmation existantes. Aucun tome possédé/lu n’est modifié automatiquement et les anciens compteurs restent inchangés. Les liens cliquables sont limités au catalogue BnF HTTPS, les champs de notices sont échappés. Si BnF échoue, aucune écriture n’est effectuée.

Les tests automatisés couvrent les cas de conflit, de doublon, d’absence de résultat, de sécurité d’affichage, les indications non exhaustives et le parcours Chromium desktop/mobile avec réponses BnF simulées. Tests toujours exécutés sur les données jetables de CI.

## Installation

Sur le PC : git pull origin main, Docker Desktop, puis mangadvisor.cmd option **3 — Build + démarrage**. Ouvrir une fiche manga et lancer l’atelier. **Ne pas supprimer les volumes Docker.**
