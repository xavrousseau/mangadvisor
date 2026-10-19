# Mangadvisor 4.7 — Sources représentatives de la mangathèque

## Problème observé

Une bibliothèque importée peut contenir de nombreuses œuvres simplement marquées
**OWNED**, sans note ni favori. Le moteur sélectionnait alors les cinq premières
sources classées par poids/date, qui ne représentent pas forcément une collection
riche et variée. Une possession **n'est pas une preuve d'appréciation**.

## Nouvelle sélection sur `POST /recommendations/library`

- Si **trois favoris ou bonnes notes (au moins 8,5/10)** sont présents, conserver
  le choix historique des cinq sources les mieux classées parmi ces favoris.
- Sinon, lire jusqu'à **100 sources positives**, en respectant les poids déjà
  calculés, puis les **genres et thèmes réellement enregistrés en SQL**.
  La sélection retient au maximum **huit œuvres distinctes** et privilégie les
  favoris, les notes et les lectures avant les simples possessions.
- À niveau de preuve équivalent, privilégier des attributs nouveaux ;
  les thèmes attestés sont un peu plus distinctifs que les genres.
  Si aucun genre/thème n'est enregistré, revenir à un classement stable
  par poids puis ordre historique, sans inventer d'attributs.
- Les sources choisies servent uniquement de départ à **l'algorithme SQL
  existant**. Les exclusions des mangas déjà présents dans
  `user_manga_library`, le seuil de score, les bonus communautaires et
  les modes CLOSE / BALANCED / EXPLORE sont conservés.

## Traçabilité et limites

`profile_summary` inclut désormais :

- `source_sampling_strategy` : haute confiance, petite bibliothèque,
  diversité des attributs ou repli sans tags.
- `preference_evidence` : `RECORDED_TASTE`,
  `OWNERSHIP_AND_INTEREST_ONLY` ou `OWNERSHIP_ONLY`.
- `evidence_warning` : message de prudence si aucune préférence forte
  n'est documentée.
- `recorded_seed_attribute_count` : nombre de tags distincts réellement
  attestés parmi les sources sélectionnées.
- `positive_source_pool_capped` : avertit quand la limite de 100 entrées
  positives examinées est atteinte.

Les déclarations d'inventaire restent séparées des vrais ISBN et des volumes
lus. Deux éditions physiques (par exemple **Dragon Ball Pastel** et
**Dragon Ball Deluxe**) continuent de partager une œuvre canonique, mais ne
sont jamais fusionnées en une seule possession.

## Mesure avec une bibliothèque personnelle

Après la mise à jour 28, utiliser l'option **20** depuis `mangadvisor.cmd`
pour générer un benchmark **en lecture seule** de son CSV privé dans
`private-data/`. Il révèle la couverture du catalogue, les ambiguïtés
et la répétition des recommandations, **sans envoyer la collection sur GitHub**.

Les tests automatisés simulent jusqu'à 103 entrées avec des tags synthétiques,
mais **ne prouvent pas encore la pertinence** sur les mangas du propriétaire.
Pour affiner la personnalisation, quelques notes ou favoris explicites sont
beaucoup plus fiables que le simple inventaire.
