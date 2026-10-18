# Mangadvisor 1.0 — Découverte visuelle (lot 3)

## Objectif

Passer d'une recherche par liste déroulante à un véritable parcours visuel du catalogue, fidèle au thème sombre et orange validé. Le moteur de recommandation, la bibliothèque et les scores existants restent intacts.

## Parcours utilisateur

1. Ouvrir **Découvrir** : grille de 12 mangas, avec couvertures Jikan de la base existante et visuel de repli.
2. Rechercher par titre, choisir un genre ou limiter aux séries terminées.
3. Parcourir les pages ; chaque action de filtre réinitialise la pagination et ferme l'ancienne sélection.
4. Sélectionner **Voir la fiche** : couverture, titres alternatifs, genres, thèmes, cible, statut, statistiques et synopsis.
5. Lancer **Trouver des mangas similaires**, en réutilisant exactement la route \`GET /recommendations/similar\`.
6. Garder la fiche ouverte pendant les interactions ; la fermer sans modifier aucune donnée.

L'onglet **Fiche manga** conserve sa recherche directe et utilise désormais la même présentation détaillée que **Découvrir**.

## Changements techniques

- \`GET /mangas\` accepte deux filtres SQL paramétrés : \`genre\` (genre exact) et \`only_finished\`.
- Le filtrage est réalisé **avant** \`LIMIT\`/\`OFFSET\`, pour éviter les résultats incohérents.
- La recherche sur les titres est entre parenthèses avant combinaison avec les filtres \`AND\`.
- Chargement de 13 mangas pour une page de 12 : le treizième sert de détecteur de page suivante, sans inventer de total.
- Appels aux couvertures en lot, en réutilisant le service et le cache du lot 2.
- Nouveau module isolé \`apps/ui/app/discovery.py\` pour faciliter la maintenance du grand fichier historique.
- Réutilisation des composants de fiche et de recommandation pour ne pas recopier les règles métier.
- Tests unitaires pour la normalisation de recherche, les bornes de pagination et le SQL filtré.

## Garanties et limites

- **Aucun changement de schéma**, suppression ou modification de données.
- Les couvertures sont liées au JSON Jikan déjà présent, et peuvent manquer.
- La galerie affiche les scores communautaires, jamais un faux pourcentage de compatibilité.
- Il n'y a aucune donnée fictive dans les résultats affichés.
- Le catalogue reste uniquement local via l'API du projet ; l'interface ne fait pas de recherche en ligne.
- La recherche directe de l'onglet Fiche manga garde la limite historique de 100 candidats.
- Le rendu sur PC/mobile et l'exécution avec une base PostgreSQL réelle restent à contrôler avant fusion.
- Les pull requests sont empilées : lot 1 (thème) → lot 2 (jaquettes) → lot 3 (découverte).
