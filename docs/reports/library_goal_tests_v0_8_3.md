# Mangadvisor — Tests objectifs recommandations bibliothèque V0.8.3

Date d’exécution : `2026-06-07 13:53:21`

API testée : `http://localhost:8000`

## Bibliothèque de test

| Demandé | Trouvé | Statut | Note | Favori |
|---|---|---|---:|---|
| Naruto | Naruto | READ | 8.0 | Non |
| Death Note | Death Note | READ | 9.0 | Oui |
| Fullmetal Alchemist | Fullmetal Alchemist | READ | 9.0 | Oui |
| Nana | Nana | READ | 8.5 | Non |

## Comparaison synthétique

| Objectif | Recommandations obtenues |
|---|---|
| Proche de mes goûts | Psyren, Yakusoku no Neverland, Bakuman., Mahoutsukai no Yome, Beck |
| Quoi lire ensuite | Psyren, Yakusoku no Neverland, Bakuman., Beck, Banana Fish |
| Série terminée / plutôt courte | Psyren, Aku no Hana, Watashitachi no Shiawase na Jikan, Bakuman., Yakusoku no Neverland |

## Détail par objectif

## Proche de mes goûts — `SIMILAR_SAFE`

**Description :** Recommandations proches des goûts dominants de la bibliothèque.

**Objectif retourné par l’API :** `SIMILAR_SAFE`

### Sources utilisées

| Titre | Statut bibliothèque | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Fullmetal Alchemist | READ | 9.0 | Oui | 11.0 |
| Death Note | READ | 9.0 | Oui | 11.0 |
| Nana | READ | 8.5 | Non | 6.5 |

### Profil détecté

**Règle de sélection :** Sources haute confiance : favoris et/ou notes utilisateur >= 8.5.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Award Winning | 2 | 17.5 |
| Drama | 2 | 17.5 |
| Action | 2 | 17.0 |
| Adventure | 2 | 17.0 |
| Fantasy | 2 | 17.0 |
| Supernatural | 1 | 11.0 |
| Suspense | 1 | 11.0 |
| Romance | 1 | 6.5 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Military | 1 | 11.0 |
| Psychological | 1 | 11.0 |
| Adult Cast | 1 | 6.5 |
| Love Polygon | 1 | 6.5 |
| Music | 1 | 6.5 |
| Martial Arts | 1 | 6.0 |

#### Top cibles éditoriales

| Cible | Sources | Poids |
|---|---:|---:|
| Shounen | 3 | 28.0 |
| Shoujo | 1 | 6.5 |

### Recommandations

| Rang | Titre | Score final | Score base | Bonus objectif | Volumes | Chapitres | Statut | Genres communs | Thèmes communs | Cible commune |
|---:|---|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | Psyren | 105.0 | 95.0 | 10.0 | 16 | 145 | Finished | Action, Adventure, Romance, Supernatural | Psychological | Shounen |
| 2 | Yakusoku no Neverland | 92.1 | 78.1 | 14.0 | 20 | 181 | Finished | Award Winning, Suspense | Psychological | Shounen |
| 3 | Bakuman. | 88.4 | 78.4 | 10.0 | 20 | 176 | Finished | Drama, Romance |  | Shounen |
| 4 | Mahoutsukai no Yome | 85.4 | 75.4 | 10.0 |  |  | Publishing | Drama, Fantasy, Romance |  | Shounen |
| 5 | Beck | 83.4 | 77.4 | 6.0 | 34 | 103 | Finished | Award Winning, Drama, Romance | Music | Shounen |

## Quoi lire ensuite — `READ_NEXT`

**Description :** Recommandations pratiques à lire maintenant, avec bonus qualité/statut/popularité.

**Objectif retourné par l’API :** `READ_NEXT`

### Sources utilisées

| Titre | Statut bibliothèque | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Fullmetal Alchemist | READ | 9.0 | Oui | 11.0 |
| Death Note | READ | 9.0 | Oui | 11.0 |
| Nana | READ | 8.5 | Non | 6.5 |

### Profil détecté

**Règle de sélection :** Sources haute confiance : favoris et/ou notes utilisateur >= 8.5.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Award Winning | 2 | 17.5 |
| Drama | 2 | 17.5 |
| Action | 2 | 17.0 |
| Adventure | 2 | 17.0 |
| Fantasy | 2 | 17.0 |
| Supernatural | 1 | 11.0 |
| Suspense | 1 | 11.0 |
| Romance | 1 | 6.5 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Military | 1 | 11.0 |
| Psychological | 1 | 11.0 |
| Adult Cast | 1 | 6.5 |
| Love Polygon | 1 | 6.5 |
| Music | 1 | 6.5 |
| Martial Arts | 1 | 6.0 |

#### Top cibles éditoriales

| Cible | Sources | Poids |
|---|---:|---:|
| Shounen | 3 | 28.0 |
| Shoujo | 1 | 6.5 |

### Recommandations

| Rang | Titre | Score final | Score base | Bonus objectif | Volumes | Chapitres | Statut | Genres communs | Thèmes communs | Cible commune |
|---:|---|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | Psyren | 110.0 | 95.0 | 15.0 | 16 | 145 | Finished | Action, Adventure, Romance, Supernatural | Psychological | Shounen |
| 2 | Yakusoku no Neverland | 104.1 | 78.1 | 26.0 | 20 | 181 | Finished | Award Winning, Suspense | Psychological | Shounen |
| 3 | Bakuman. | 101.4 | 78.4 | 23.0 | 20 | 176 | Finished | Drama, Romance |  | Shounen |
| 4 | Beck | 97.4 | 77.4 | 20.0 | 34 | 103 | Finished | Award Winning, Drama, Romance | Music | Shounen |
| 5 | Banana Fish | 97.3 | 77.3 | 20.0 | 19 | 110 | Finished | Action, Adventure, Drama, Suspense | Psychological | Shoujo |

## Série terminée / plutôt courte — `SHORT_FINISHED`

**Description :** Recommandations terminées, avec préférence pour les séries courtes ou moyennes.

**Objectif retourné par l’API :** `SHORT_FINISHED`

### Sources utilisées

| Titre | Statut bibliothèque | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Fullmetal Alchemist | READ | 9.0 | Oui | 11.0 |
| Death Note | READ | 9.0 | Oui | 11.0 |
| Nana | READ | 8.5 | Non | 6.5 |

### Profil détecté

**Règle de sélection :** Sources haute confiance : favoris et/ou notes utilisateur >= 8.5.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Award Winning | 2 | 17.5 |
| Drama | 2 | 17.5 |
| Action | 2 | 17.0 |
| Adventure | 2 | 17.0 |
| Fantasy | 2 | 17.0 |
| Supernatural | 1 | 11.0 |
| Suspense | 1 | 11.0 |
| Romance | 1 | 6.5 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Military | 1 | 11.0 |
| Psychological | 1 | 11.0 |
| Adult Cast | 1 | 6.5 |
| Love Polygon | 1 | 6.5 |
| Music | 1 | 6.5 |
| Martial Arts | 1 | 6.0 |

#### Top cibles éditoriales

| Cible | Sources | Poids |
|---|---:|---:|
| Shounen | 3 | 28.0 |
| Shoujo | 1 | 6.5 |

### Recommandations

| Rang | Titre | Score final | Score base | Bonus objectif | Volumes | Chapitres | Statut | Genres communs | Thèmes communs | Cible commune |
|---:|---|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | Psyren | 140.0 | 95.0 | 45.0 | 16 | 145 | Finished | Action, Adventure, Romance, Supernatural | Psychological | Shounen |
| 2 | Aku no Hana | 137.4 | 75.4 | 62.0 | 11 | 58 | Finished | Drama, Romance | Psychological | Shounen |
| 3 | Watashitachi no Shiawase na Jikan | 133.0 | 65.0 | 68.0 | 1 | 8 | Finished | Drama, Romance | Music, Psychological |  |
| 4 | Bakuman. | 128.4 | 78.4 | 50.0 | 20 | 176 | Finished | Drama, Romance |  | Shounen |
| 5 | Yakusoku no Neverland | 128.1 | 78.1 | 50.0 | 20 | 181 | Finished | Award Winning, Suspense | Psychological | Shounen |

## Notes

Ce rapport compare les objectifs `SIMILAR_SAFE`, `READ_NEXT` et `SHORT_FINISHED` sur une bibliothèque volontairement mixte.
Il permet de vérifier si l’objectif modifie réellement le classement final sans modifier le moteur V0.7.4.
