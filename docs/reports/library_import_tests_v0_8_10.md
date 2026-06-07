# Mangadvisor — Tests import bibliothèque V0.8.10

Date d’exécution : `2026-06-07 13:53:23`

API testée : `http://localhost:8000`

## Synthèse

| Test | Dry run | Matched | Non trouvés | Erreurs | Taille bibliothèque après test | Résultat |
|---|---|---:|---:|---:|---:|---|
| CSV simulation | Oui | 4 | 1 | 0 | 0 | OK |
| CSV import réel | Non | 4 | 1 | 0 | 4 | OK |
| Excel converti en CSV - import réel | Non | 4 | 1 | 0 | 4 | OK |

## Détail

## CSV simulation

**Résultat :** `OK`

### Lignes trouvées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | READ | 8.5 | Oui |
| 3 | Bleach | Bleach | READ | 8.0 | Non |
| 4 | One Piece | One Piece | WANT_TO_READ |  | Non |
| 5 | Fairy Tail | Fairy Tail | NOT_INTERESTED |  | Non |

### Titres non trouvés

| Ligne | Titre | Statut demandé |
|---:|---|---|
| 6 | Titre Qui Nexiste Pas 999 | READ |

### Erreurs

| Ligne | Erreur |
|---:|---|
|  | Aucune |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Bibliothèque vide |  |  |  |

### Profil après test

**Statuts :** `{}`

**Sources positives :** `0`

**Signaux négatifs :** `0`

## CSV import réel

**Résultat :** `OK`

### Lignes trouvées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | READ | 8.5 | Oui |
| 3 | Bleach | Bleach | READ | 8.0 | Non |
| 4 | One Piece | One Piece | WANT_TO_READ |  | Non |
| 5 | Fairy Tail | Fairy Tail | NOT_INTERESTED |  | Non |

### Titres non trouvés

| Ligne | Titre | Statut demandé |
|---:|---|---|
| 6 | Titre Qui Nexiste Pas 999 | READ |

### Erreurs

| Ligne | Erreur |
|---:|---|
|  | Aucune |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Bleach | READ | 8.0 | Non |
| Fairy Tail | NOT_INTERESTED |  | Non |
| Naruto | READ | 8.5 | Oui |
| One Piece | WANT_TO_READ |  | Non |

### Profil après test

**Statuts :** `{'NOT_INTERESTED': 1, 'READ': 2, 'WANT_TO_READ': 1}`

**Sources positives :** `3`

**Signaux négatifs :** `1`

## Excel converti en CSV - import réel

**Résultat :** `OK`

### Lignes trouvées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | READ | 8.5 | Oui |
| 3 | Bleach | Bleach | READ | 8.0 | Non |
| 4 | One Piece | One Piece | WANT_TO_READ |  | Non |
| 5 | Fairy Tail | Fairy Tail | NOT_INTERESTED |  | Non |

### Titres non trouvés

| Ligne | Titre | Statut demandé |
|---:|---|---|
| 6 | Titre Qui Nexiste Pas 999 | READ |

### Erreurs

| Ligne | Erreur |
|---:|---|
|  | Aucune |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Bleach | READ | 8.0 | Non |
| Fairy Tail | NOT_INTERESTED |  | Non |
| Naruto | READ | 8.5 | Oui |
| One Piece | WANT_TO_READ |  | Non |

### Profil après test

**Statuts :** `{'NOT_INTERESTED': 1, 'READ': 2, 'WANT_TO_READ': 1}`

**Sources positives :** `3`

**Signaux négatifs :** `1`

## Note

Ce test valide l'endpoint `/library/import/csv` et vérifie que l'import alimente correctement la bibliothèque et le profil de lecture.
Le test Excel crée un fichier `.xlsx` en mémoire si `openpyxl` est installé localement, puis le reconvertit en CSV pour réutiliser la même logique métier.
