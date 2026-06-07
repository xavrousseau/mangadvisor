# Mangadvisor — Tests robustesse import bibliothèque V0.8.11

Date d’exécution : `2026-06-07 13:53:24`

API testée : `http://localhost:8000`

## Synthèse

| Test | Matched | Non trouvés | Erreurs | Taille bibliothèque | Résultat |
|---|---:|---:|---:|---:|---|
| Colonnes françaises + point-virgule + note avec virgule | 2 | 0 | 0 | 2 | OK |
| Statut invalide | 1 | 0 | 1 | 1 | OK |
| Titre vide | 1 | 0 | 1 | 1 | OK |
| Doublon dans le fichier | 2 | 0 | 0 | 1 | OK |
| Mise à jour d'un manga déjà présent | 1 | 0 | 0 | 1 | OK |
| Booléen invalide | 0 | 0 | 1 | 0 | OK |

## Détail

## Colonnes françaises + point-virgule + note avec virgule

**Description :** Vérifie que titre/statut/note/favori et le séparateur ; sont bien reconnus.

**Résultat :** `OK`

### Import

- Matched : `2`
- Non trouvés : `0`
- Erreurs : `0`

### Lignes importées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | READ | 8.5 | Oui |
| 3 | Bleach | Bleach | READ | 8.0 | Non |

### Titres non trouvés

| Ligne | Titre |
|---:|---|
|  | Aucun |

### Erreurs

| Ligne | Erreur |
|---:|---|
|  | Aucune |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Bleach | READ | 8.0 | Non |
| Naruto | READ | 8.5 | Oui |

### Profil après test

**Statuts :** `{'READ': 2}`

**Sources positives :** `2`

**Signaux négatifs :** `0`

## Statut invalide

**Description :** Vérifie qu'une ligne avec un statut inconnu part en erreur sans casser tout l'import.

**Résultat :** `OK`

### Import

- Matched : `1`
- Non trouvés : `0`
- Erreurs : `1`

### Lignes importées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | READ | 8.5 | Oui |

### Titres non trouvés

| Ligne | Titre |
|---:|---|
|  | Aucun |

### Erreurs

| Ligne | Erreur |
|---:|---|
| 3 | 400: Statut bibliothèque invalide. Valeurs autorisées : DROPPED, NOT_INTERESTED, OWNED, READ, READING, WANT_TO_READ |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Naruto | READ | 8.5 | Oui |

### Profil après test

**Statuts :** `{'READ': 1}`

**Sources positives :** `1`

**Signaux négatifs :** `0`

## Titre vide

**Description :** Vérifie qu'une ligne sans titre part en erreur.

**Résultat :** `OK`

### Import

- Matched : `1`
- Non trouvés : `0`
- Erreurs : `1`

### Lignes importées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 3 | Death Note | Death Note | READ | 9.0 | Oui |

### Titres non trouvés

| Ligne | Titre |
|---:|---|
|  | Aucun |

### Erreurs

| Ligne | Erreur |
|---:|---|
| 2 | Titre manquant. |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Death Note | READ | 9.0 | Oui |

### Profil après test

**Statuts :** `{'READ': 1}`

**Sources positives :** `1`

**Signaux négatifs :** `0`

## Doublon dans le fichier

**Description :** Vérifie qu'un doublon met à jour le même manga plutôt que de créer deux entrées.

**Résultat :** `OK`

### Import

- Matched : `2`
- Non trouvés : `0`
- Erreurs : `0`

### Lignes importées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | WANT_TO_READ |  | Non |
| 3 | Naruto | Naruto | READ | 8.5 | Oui |

### Titres non trouvés

| Ligne | Titre |
|---:|---|
|  | Aucun |

### Erreurs

| Ligne | Erreur |
|---:|---|
|  | Aucune |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Naruto | READ | 8.5 | Oui |

### Profil après test

**Statuts :** `{'READ': 1}`

**Sources positives :** `1`

**Signaux négatifs :** `0`

## Mise à jour d'un manga déjà présent

**Description :** Vérifie qu'un import met à jour un manga déjà en bibliothèque.

**Résultat :** `OK`

### Import

- Matched : `1`
- Non trouvés : `0`
- Erreurs : `0`

### Lignes importées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
| 2 | Naruto | Naruto | READ | 9.0 | Oui |

### Titres non trouvés

| Ligne | Titre |
|---:|---|
|  | Aucun |

### Erreurs

| Ligne | Erreur |
|---:|---|
|  | Aucune |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Naruto | READ | 9.0 | Oui |

### Profil après test

**Statuts :** `{'READ': 1}`

**Sources positives :** `1`

**Signaux négatifs :** `0`

## Booléen invalide

**Description :** Vérifie qu'une valeur favorite invalide part en erreur.

**Résultat :** `OK`

### Import

- Matched : `0`
- Non trouvés : `0`
- Erreurs : `1`

### Lignes importées

| Ligne | Demandé | Trouvé | Statut | Note | Favori |
|---:|---|---|---|---:|---|
|  | Aucun |  |  |  |  |

### Titres non trouvés

| Ligne | Titre |
|---:|---|
|  | Aucun |

### Erreurs

| Ligne | Erreur |
|---:|---|
| 2 | Valeur booléenne invalide : peut-être |

### Bibliothèque après test

| Titre | Statut | Note | Favori |
|---|---|---:|---|
| Bibliothèque vide |  |  |  |

### Profil après test

**Statuts :** `{}`

**Sources positives :** `0`

**Signaux négatifs :** `0`

## Note

Ce test vérifie la robustesse de l'import bibliothèque : colonnes françaises, séparateur point-virgule, notes avec virgule, statuts invalides, titres vides, doublons, mises à jour et booléens invalides.
