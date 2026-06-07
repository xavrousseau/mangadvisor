# Mangadvisor — Tests statuts bibliothèque V0.8.5

Date d’exécution : `2026-06-07 13:53:21`

API testée : `http://localhost:8000`

## Synthèse

| Scénario | Interdits | Recommandations | Résultat |
|---|---|---|---|
| Shōnen avec titre non intéressé | Fairy Tail | One Piece, Dragon Ball, Yuu☆Yuu☆Hakusho, Fullmetal Alchemist, Jigokuraku | OK |
| Shōnen avec titre abandonné | Fairy Tail | One Piece, Dragon Ball, Yuu☆Yuu☆Hakusho, Fullmetal Alchemist, Jigokuraku | OK |
| Envie de lire déjà présente | One Piece | Dragon Ball, Fairy Tail, Black Clover, Yuu☆Yuu☆Hakusho, Soul Eater | OK |
| Possédé mais pas encore lu | Dragon Ball | One Piece, Fairy Tail, Yuu☆Yuu☆Hakusho, Fullmetal Alchemist, Jigokuraku | OK |
| Manga lu mais très mal noté | Fairy Tail | One Piece, Dragon Ball, Yuu☆Yuu☆Hakusho, Fullmetal Alchemist, Jigokuraku | OK |

## Détail des scénarios

## Shōnen avec titre non intéressé

**Description :** L'utilisateur aime Naruto/Bleach/Hunter x Hunter mais indique ne pas être intéressé par Fairy Tail.

**Résultat du test :** `OK`

### Bibliothèque chargée

| Demandé | Trouvé | Statut | Note | Favori |
|---|---|---|---:|---|
| Naruto | Naruto | READ | 8.5 | Oui |
| Bleach | Bleach | READ | 8.0 | Non |
| Hunter x Hunter | Hunter x Hunter | READING | 9.0 | Oui |
| Fairy Tail | Fairy Tail | NOT_INTERESTED |  | Non |

### Sources positives utilisées

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |

### Sources positives disponibles

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |

### Profil détecté

**Règle de sélection :** Sources positives principales : favoris, notes, statuts lus/en cours/envie.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Action | 3 | 28.0 |
| Adventure | 3 | 28.0 |
| Fantasy | 2 | 22.0 |
| Award Winning | 1 | 6.0 |
| Supernatural | 1 | 6.0 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Martial Arts | 1 | 10.5 |

### Recommandations obtenues

| Rang | Titre | Score final | Score base | Bonus objectif | Statut | Volumes | Chapitres |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | One Piece | 114.4 | 100.4 | 14.0 | Publishing |  |  |
| 2 | Dragon Ball | 113.6 | 99.6 | 14.0 | Finished | 42 | 520 |
| 3 | Yuu☆Yuu☆Hakusho | 101.2 | 87.2 | 14.0 | Finished | 19 | 176 |
| 4 | Fullmetal Alchemist | 98.3 | 84.3 | 14.0 | Finished | 27 | 116 |
| 5 | Jigokuraku | 98.1 | 84.1 | 14.0 | Finished | 13 | 128 |
## Shōnen avec titre abandonné

**Description :** L'utilisateur aime les grands shōnen mais a abandonné Fairy Tail.

**Résultat du test :** `OK`

### Bibliothèque chargée

| Demandé | Trouvé | Statut | Note | Favori |
|---|---|---|---:|---|
| Naruto | Naruto | READ | 8.5 | Oui |
| Bleach | Bleach | READ | 8.0 | Non |
| Hunter x Hunter | Hunter x Hunter | READING | 9.0 | Oui |
| Fairy Tail | Fairy Tail | DROPPED | 4.0 | Non |

### Sources positives utilisées

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |

### Sources positives disponibles

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |

### Profil détecté

**Règle de sélection :** Sources positives principales : favoris, notes, statuts lus/en cours/envie.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Action | 3 | 28.0 |
| Adventure | 3 | 28.0 |
| Fantasy | 2 | 22.0 |
| Award Winning | 1 | 6.0 |
| Supernatural | 1 | 6.0 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Martial Arts | 1 | 10.5 |

### Recommandations obtenues

| Rang | Titre | Score final | Score base | Bonus objectif | Statut | Volumes | Chapitres |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | One Piece | 114.4 | 100.4 | 14.0 | Publishing |  |  |
| 2 | Dragon Ball | 113.6 | 99.6 | 14.0 | Finished | 42 | 520 |
| 3 | Yuu☆Yuu☆Hakusho | 101.2 | 87.2 | 14.0 | Finished | 19 | 176 |
| 4 | Fullmetal Alchemist | 98.3 | 84.3 | 14.0 | Finished | 27 | 116 |
| 5 | Jigokuraku | 98.1 | 84.1 | 14.0 | Finished | 13 | 128 |
## Envie de lire déjà présente

**Description :** L'utilisateur veut lire One Piece : il ne doit donc pas être recommandé à nouveau.

**Résultat du test :** `OK`

### Bibliothèque chargée

| Demandé | Trouvé | Statut | Note | Favori |
|---|---|---|---:|---|
| Naruto | Naruto | READ | 8.5 | Oui |
| Bleach | Bleach | READ | 8.0 | Non |
| Hunter x Hunter | Hunter x Hunter | READING | 9.0 | Oui |
| One Piece | One Piece | WANT_TO_READ |  | Non |

### Sources positives utilisées

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |
| One Piece | WANT_TO_READ |  | Non | 1.5 |

### Sources positives disponibles

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |
| One Piece | WANT_TO_READ |  | Non | 1.5 |

### Profil détecté

**Règle de sélection :** Sources positives principales : favoris, notes, statuts lus/en cours/envie.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Action | 4 | 29.5 |
| Adventure | 4 | 29.5 |
| Fantasy | 3 | 23.5 |
| Award Winning | 1 | 6.0 |
| Supernatural | 1 | 6.0 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Martial Arts | 1 | 10.5 |

### Recommandations obtenues

| Rang | Titre | Score final | Score base | Bonus objectif | Statut | Volumes | Chapitres |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Dragon Ball | 117.7 | 103.7 | 14.0 | Finished | 42 | 520 |
| 2 | Fairy Tail | 114.0 | 100.0 | 14.0 | Finished | 63 | 549 |
| 3 | Black Clover | 102.1 | 88.1 | 14.0 | Finished | 38 | 392 |
| 4 | Yuu☆Yuu☆Hakusho | 101.2 | 87.2 | 14.0 | Finished | 19 | 176 |
| 5 | Soul Eater | 99.5 | 85.5 | 14.0 | Finished | 25 | 117 |
## Possédé mais pas encore lu

**Description :** L'utilisateur possède Dragon Ball mais ne l'a pas encore lu : il ne doit pas être recommandé à nouveau.

**Résultat du test :** `OK`

### Bibliothèque chargée

| Demandé | Trouvé | Statut | Note | Favori |
|---|---|---|---:|---|
| Naruto | Naruto | READ | 8.5 | Oui |
| Bleach | Bleach | READ | 8.0 | Non |
| Hunter x Hunter | Hunter x Hunter | READING | 9.0 | Oui |
| Dragon Ball | Dragon Ball | OWNED |  | Non |

### Sources positives utilisées

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |
| Dragon Ball | OWNED |  | Non | 1.0 |

### Sources positives disponibles

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |
| Dragon Ball | OWNED |  | Non | 1.0 |

### Profil détecté

**Règle de sélection :** Sources positives principales : favoris, notes, statuts lus/en cours/envie.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Action | 4 | 29.0 |
| Adventure | 4 | 29.0 |
| Fantasy | 3 | 23.0 |
| Award Winning | 1 | 6.0 |
| Supernatural | 1 | 6.0 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Martial Arts | 2 | 11.5 |

### Recommandations obtenues

| Rang | Titre | Score final | Score base | Bonus objectif | Statut | Volumes | Chapitres |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | One Piece | 115.7 | 101.7 | 14.0 | Publishing |  |  |
| 2 | Fairy Tail | 105.9 | 91.9 | 14.0 | Finished | 63 | 549 |
| 3 | Yuu☆Yuu☆Hakusho | 101.2 | 87.2 | 14.0 | Finished | 19 | 176 |
| 4 | Fullmetal Alchemist | 99.5 | 85.5 | 14.0 | Finished | 27 | 116 |
| 5 | Jigokuraku | 99.4 | 85.4 | 14.0 | Finished | 13 | 128 |
## Manga lu mais très mal noté

**Description :** L'utilisateur a lu Fairy Tail mais l'a très mal noté. On vérifie son poids dans le profil.

**Résultat du test :** `OK`

### Bibliothèque chargée

| Demandé | Trouvé | Statut | Note | Favori |
|---|---|---|---:|---|
| Naruto | Naruto | READ | 8.5 | Oui |
| Bleach | Bleach | READ | 8.0 | Non |
| Hunter x Hunter | Hunter x Hunter | READING | 9.0 | Oui |
| Fairy Tail | Fairy Tail | READ | 3.0 | Non |

### Sources positives utilisées

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |

### Sources positives disponibles

| Titre | Statut | Note | Favori | Poids positif |
|---|---|---:|---|---:|
| Hunter x Hunter | READING | 9.0 | Oui | 11.5 |
| Naruto | READ | 8.5 | Oui | 10.5 |
| Bleach | READ | 8.0 | Non | 6.0 |

### Profil détecté

**Règle de sélection :** Sources positives principales : favoris, notes, statuts lus/en cours/envie.

#### Top genres

| Genre | Sources | Poids |
|---|---:|---:|
| Action | 3 | 28.0 |
| Adventure | 3 | 28.0 |
| Fantasy | 2 | 22.0 |
| Award Winning | 1 | 6.0 |
| Supernatural | 1 | 6.0 |

#### Top thèmes

| Thème | Sources | Poids |
|---|---:|---:|
| Martial Arts | 1 | 10.5 |

### Recommandations obtenues

| Rang | Titre | Score final | Score base | Bonus objectif | Statut | Volumes | Chapitres |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | One Piece | 114.4 | 100.4 | 14.0 | Publishing |  |  |
| 2 | Dragon Ball | 113.6 | 99.6 | 14.0 | Finished | 42 | 520 |
| 3 | Yuu☆Yuu☆Hakusho | 101.2 | 87.2 | 14.0 | Finished | 19 | 176 |
| 4 | Fullmetal Alchemist | 98.3 | 84.3 | 14.0 | Finished | 27 | 116 |
| 5 | Jigokuraku | 98.1 | 84.1 | 14.0 | Finished | 13 | 128 |

## Notes

Ce rapport vérifie que les statuts `DROPPED`, `NOT_INTERESTED`, `WANT_TO_READ` et `OWNED` empêchent bien les mangas concernés de ressortir dans les recommandations. Il vérifie aussi qu'un manga lu avec une très mauvaise note ne contribue plus positivement au profil. Il vérifie aussi qu'un manga lu avec une très mauvaise note ne contribue plus positivement au profil.
Il vérifie aussi les sources positives réellement utilisées par `/recommendations/library`.
