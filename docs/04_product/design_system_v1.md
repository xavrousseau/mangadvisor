# Mangadvisor 1.0 — Identité visuelle validée

Date de validation : 18 octobre 2026.

## Direction artistique figée

- **Fond principal** : `#0e1119` ; **navigation latérale** : `#141922`.
- **Cartes** : `#1a202c` ; **survol / surfaces actives** : `#222938`.
- **Texte principal** : `#f3f1eb` ; **secondaire** : `#a5adba`.
- **Séparations** : `#333b49` ; **accent principal** : `#ffb36b`.
- Interface sombre, chaleureuse, épurée, typographie lisible et grands visuels mangas.
- Navigation intuitive sur ordinateur et téléphone, priorité à la bibliothèque et aux recommandations expliquées.

## Intégration initiale

Le premier lot applique cette identité aux écrans existants via `apps/ui/app/theme.css` et réorganise uniquement l'accueil, l'identité de marque et la navigation. La logique métier, la base PostgreSQL et les endpoints de l'API sont laissés intacts.

### Limitations assumées de cette étape

- Ce lot n'inclut **pas** encore les couvertures officielles : l'API existante n'expose pas d'URL de couverture. Une intégration future devra choisir une source autorisée, réutiliser les identifiants canoniques et prévoir une image de substitution.
- Les cartes de bibliothèque et de recommandations restent basées sur les composants Streamlit actuels, stylisés par CSS. La refonte compacte et illustrée est un chantier suivant.
- Le thème sombre est volontairement fixé : aucun interrupteur clair/sombre dans cette version.
- Pas d'authentification : application encore conçue pour un utilisateur local. Ne pas la déployer publiquement telle quelle.

## Garde-fous

1. Ne jamais toucher aux données utilisateur pour un changement purement graphique.
2. Ne jamais afficher comme réels des taux de correspondance ou des compteurs de démonstration.
3. Conserver les fonctionnalités existantes : imports CSV/Excel, bibliothèque, profil, recommandations et détails manga.
4. Valider les modifications sur une branche avant fusion dans `main`.
5. Les futurs jeux de tests destructifs doivent utiliser une base séparée pour protéger les bibliothèques personnelles.
