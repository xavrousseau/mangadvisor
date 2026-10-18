# Mangadvisor 1.1 — Ressemblances vérifiables manga par manga

Cette évolution complète les explications introduites par la PR #10, sans les
remplacer. Son but : montrer précisément quelles œuvres du profil partagent
des caractéristiques connues avec chaque manga proposé.

## Démonstration honnête

L'API ajoute `explanation` à chaque candidat des trois moteurs :

- `reference_titles` : mangas **effectivement utilisés comme sources** par
  le moteur lors de la recherche.
- `source_matches` : pour chaque manga source ayant une intersection connue,
  les genres, thèmes et publics communs avec le candidat. Ces intersections
  proviennent directement des tables `manga_genre`, `manga_theme` et
  `manga_demographic` ; elles ne sont jamais reconstruites à partir d'un texte.
- `score.base`, `score.goal_bonus`, `score.final` : valeurs retournées par
  l'API existante. L'équation initial + bonus = final n'apparaît que si ces
  trois valeurs sont présentes.
- `shared`, `community`, `cautions` : données retournées par les critères
  déjà calculés, accessibles sans recalculer ni altérer le moteur.

Les correspondances « source → candidat » décrivent **des attributs observés**,
pas des contributions numériques par manga source. L'interface le dit
explicitement, de même que l'absence de correspondances prouvées.

## Expérience

Dans le panneau existant « Pourquoi ce manga ? » (déjà FR/EN) :
- En haut : les mangas de référence qui possèdent **réellement** des genres,
  thèmes ou publics communs avec la suggestion.
- Optionnel : l'effet **réel** du bonus objectif (score initial, bonus, total).
- Ensuite : les critères et signaux techniques conservés depuis la PR #10.
- Un court panneau repliable sur l'écran « Pour moi » rappelle comment
  améliorer ses recommandations avec notes, favoris, retours et filtres.

## Contraintes techniques

- API : une **seule requête SQL de lecture** pour tous les mangas sources et
  candidats de la réponse (jusqu'à 20 résultats), pour éviter le N+1.
- Aucune migration ni modification de données, aucun changement du classement.
- Fonction de preuves isolée, tests de non-mutation et d'intersections strictes.
- Tests sur une base PostgreSQL fictive des **trois moteurs**, vérifiant
  chaque intersection contre la véritable fiche des mangas source et cible.
- Tests navigateur desktop et mobile : preuve affichée et traduction FR/EN.

## Limite assumée

Cette preuve ne détaille pas encore mathématiquement la contribution de chaque
terme SQL au score, ni la pondération causale de chaque manga source. Inventer
ces contributions serait trompeur. Le prochain lot est une analyse de qualité
et des exclusions sur des données fictives et des scénarios reproductibles.
