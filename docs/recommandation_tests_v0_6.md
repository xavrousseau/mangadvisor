# Mangadvisor — Grille de validation des recommandations V0.6

## Objectif du document

Ce document sert à tester la qualité du moteur de recommandation Mangadvisor.

L’objectif n’est pas seulement de vérifier que l’API fonctionne techniquement, mais de vérifier si les recommandations sont crédibles pour un lecteur manga.

La V0.6 utilise actuellement :

* les genres ;
* les thèmes ;
* la cible éditoriale ;
* le score manga ;
* la popularité ;
* le statut ;
* quelques malus simples sur les écarts sensibles.

Cette grille permet de tester plusieurs profils types et de noter si les recommandations sont cohérentes.

---

## Règle de validation

Pour chaque profil, on teste dans l’interface Streamlit :

```text
http://localhost:8501
```

Dans l’onglet :

```text
🧠 Recommandation depuis mon profil
```

On sélectionne les mangas du profil, puis on lance la recommandation.

---

## Barème simple

Pour chaque recommandation affichée :

| Cas                                  | Score manuel |
| ------------------------------------ | -----------: |
| Manga très attendu                   |           +2 |
| Manga acceptable / cohérent          |           +1 |
| Manga discutable mais compréhensible |            0 |
| Manga à éviter / hors sujet          |           -2 |

### Lecture du résultat

| Score total sur 5 recommandations | Interprétation                   |
| --------------------------------: | -------------------------------- |
|                            8 à 10 | Très bon                         |
|                             5 à 7 | Correct                          |
|                             2 à 4 | À améliorer                      |
|                        0 ou moins | Mauvais profil de recommandation |

---

# Profil 1 — Shōnen aventure / combat

## Entrée utilisateur

```text
Naruto
Bleach
Hunter x Hunter
```

## Intention lecteur

Le lecteur aime les shōnen d’action, les combats, la progression des personnages, l’aventure, les pouvoirs, les arcs longs et les univers vastes.

## Recommandations très attendues

```text
Dragon Ball
One Piece
Fullmetal Alchemist
D.Gray-man
Kekkaishi
Yu Yu Hakusho
Black Clover
My Hero Academia
Jujutsu Kaisen
Demon Slayer
```

## Recommandations acceptables

```text
Tsubasa: RESERVoir CHRoNiCLE
Rave
Magi
Fairy Tail
Shaman King
```

## Recommandations à éviter

```text
Nana
Paradise Kiss
Monster
20th Century Boys
Battle Royale
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 2 — Thriller psychologique / mystère

## Entrée utilisateur

```text
Death Note
Monster
20th Century Boys
```

## Intention lecteur

Le lecteur aime les intrigues, la manipulation, la tension psychologique, les mystères, les enquêtes et les personnages ambigus.

## Recommandations très attendues

```text
Liar Game
Pluto
Billy Bat
Homunculus
The Promised Neverland
Tomodachi Game
Battle Royale
```

## Recommandations acceptables

```text
Berserk
Dragon Head
Blame!
X
Parasyte
```

## Recommandations à éviter

```text
Naruto
One Piece
Dragon Ball
Nana
Love Hina
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 3 — Seinen sombre / violent / mature

## Entrée utilisateur

```text
Berserk
Blame!
Battle Royale
```

## Intention lecteur

Le lecteur aime les univers sombres, violents, adultes, avec de la survie, de la tension, du drame, de la violence et une ambiance mature.

## Recommandations très attendues

```text
Gantz
Vagabond
Vinland Saga
Kingdom
Claymore
Dragon Head
Monster
20th Century Boys
```

## Recommandations acceptables

```text
Death Note
Parasyte
Dorohedoro
Tokyo Ghoul
Attack on Titan
```

## Recommandations à éviter

```text
Love Hina
Ouran Koukou Host Club
Nana
Lovely Complex
Hikaru no Go
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 4 — Romance / drame / personnages

## Entrée utilisateur

```text
Nana
Paradise Kiss
Lovely★Complex
```

## Intention lecteur

Le lecteur aime les relations humaines, la romance, le drame, les personnages forts, les émotions, les histoires de vie et les dynamiques sentimentales.

## Recommandations très attendues

```text
Fruits Basket
Kimi ni Todoke
Ao Haru Ride
Orange
Honey and Clover
Kare Kano
Kodomo no Omocha
Full Moon wo Sagashite
```

## Recommandations acceptables

```text
Ouran Koukou Host Club
Love Hina
Maison Ikkoku
Skip Beat!
```

## Recommandations à éviter

```text
Berserk
Battle Royale
Blame!
Dragon Ball
Hajime no Ippo
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 5 — Sport / dépassement de soi

## Entrée utilisateur

```text
Hajime no Ippo
Slam Dunk
Eyeshield 21
```

## Intention lecteur

Le lecteur aime le sport, la progression, l’effort, la compétition, les rivalités, les équipes et le dépassement de soi.

## Recommandations très attendues

```text
Haikyuu!!
Kuroko no Basket
Blue Lock
Captain Tsubasa
Major
Ashita no Joe
```

## Recommandations acceptables

```text
Hikaru no Go
Chihayafuru
Initial D
Yowamushi Pedal
```

## Recommandations à éviter

```text
Berserk
Nana
Paradise Kiss
Monster
Death Note
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 6 — Aventure longue / monde vaste

## Entrée utilisateur

```text
One Piece
Hunter x Hunter
Fullmetal Alchemist
```

## Intention lecteur

Le lecteur aime les mondes vastes, les aventures longues, les groupes de personnages, les voyages, les pouvoirs, la construction d’univers et les arcs narratifs importants.

## Recommandations très attendues

```text
Dragon Ball
Naruto
Bleach
D.Gray-man
Magi
Fairy Tail
Rave
Tsubasa: RESERVoir CHRoNiCLE
```

## Recommandations acceptables

```text
Shaman King
Black Clover
Seven Deadly Sins
Kekkaishi
```

## Recommandations à éviter

```text
Nana
Paradise Kiss
Monster
Battle Royale
Love Hina
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 7 — Mystère / surnaturel

## Entrée utilisateur

```text
Death Note
Bleach
xxxHOLiC
```

## Intention lecteur

Le lecteur aime le surnaturel, les mystères, les esprits, les phénomènes étranges, les pouvoirs et les ambiances plus mystérieuses.

## Recommandations très attendues

```text
D.Gray-man
Yu Yu Hakusho
Noragami
Blue Exorcist
Jujutsu Kaisen
Mushishi
Natsume Yuujinchou
```

## Recommandations acceptables

```text
Hikaru no Go
X
Full Moon wo Sagashite
Tsubasa: RESERVoir CHRoNiCLE
```

## Recommandations à éviter

```text
Nana
Paradise Kiss
Hajime no Ippo
Slam Dunk
Love Hina
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Profil 8 — Tranche de vie / contemplatif

## Entrée utilisateur

```text
Yokohama Kaidashi Kikou
Mushishi
Natsume Yuujinchou
```

## Intention lecteur

Le lecteur aime les histoires calmes, contemplatives, poétiques, avec une ambiance douce, de la tranche de vie, du voyage intérieur et peu d’action.

## Recommandations très attendues

```text
Aria
Aqua
Barakamon
Yotsuba&!
Girls' Last Tour
Kino no Tabi
```

## Recommandations acceptables

```text
Honey and Clover
March Comes in Like a Lion
Nana
Solanin
```

## Recommandations à éviter

```text
Berserk
Battle Royale
Dragon Ball
Bleach
Gantz
```

## Résultat observé

À compléter après test.

```text
1.
2.
3.
4.
5.
```

## Score manuel

```text
Score :
Commentaire :
```

---

# Synthèse des tests

| Profil                           | Score manuel | Statut | Commentaire |
| -------------------------------- | -----------: | ------ | ----------- |
| Shōnen aventure / combat         |              |        |             |
| Thriller psychologique / mystère |              |        |             |
| Seinen sombre / violent / mature |              |        |             |
| Romance / drame / personnages    |              |        |             |
| Sport / dépassement de soi       |              |        |             |
| Aventure longue / monde vaste    |              |        |             |
| Mystère / surnaturel             |              |        |             |
| Tranche de vie / contemplatif    |              |        |             |

---

# Décisions à prendre après test

Après avoir rempli cette grille, on pourra décider :

1. Si le scoring actuel est suffisant.
2. Quels profils sont mal recommandés.
3. Quels tags sont trop puissants.
4. Quels tags ne sont pas assez puissants.
5. Si certains genres doivent être considérés comme trop génériques.
6. Si certains filtres doivent devenir des préférences utilisateur.
7. Si on doit enrichir les données avec des tags manuels ou des embeddings.

---

# Règle importante

On ne modifie pas le moteur après un seul mauvais résultat isolé.

On modifie le moteur seulement si un problème revient sur plusieurs profils.

Exemples :

```text
Si Romance remonte trop souvent dans des profils shōnen, on ajoute un malus Romance.
Si Psychological écrase tous les autres critères, on réduit son poids.
Si Award Winning donne trop d’importance à certains mangas, on baisse son impact.
Si les mangas peu populaires remontent trop souvent, on augmente le bonus popularité ou le malus score faible.
```
