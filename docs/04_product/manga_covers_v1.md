# Mangadvisor 1.0 — Couvertures et cartes réelles

## Contenu du lot

- Lecture **sans migration** de \`jikan_manga_source.raw_json\` pour trouver la couverture MyAnimeList d'un manga canonique.
- Nouvelle route \`GET /covers/mangas?ids=1,2,3\` : maximum 50 identifiants par appel ; requête SQL en lecture seule.
- Filtrage des URL d'images vers le domaine \`cdn.myanimelist.net\` en HTTPS.
- Récupération côté Streamlit par lot et cache de 30 minutes.
- Cartes de bibliothèque avec jaquette, statut, note et gestion conservée dans les détails.
- Bibliothèque paginée à 24 œuvres ; les filtres rechargent la première page.
- Recommandations illustrées, sans modifier le classement, les scores ni les raisons fournis par le moteur.
- Visuel de remplacement sans fausse couverture pour les images manquantes.
- Vérification de syntaxe et tests unitaires de l'API de couvertures via GitHub Actions.

## Restrictions

- Les couvertures sont issues du JSON Jikan déjà présent : si la source ne contient pas le champ \`images\`, une vignette de remplacement est affichée.
- Les liens pointent vers un serveur tiers et peuvent expirer ou être indisponibles.
- Les images ne sont pas stockées ni copiées dans Mangadvisor.
- Cette modification ne change pas le catalogue, la bibliothèque ou le moteur de recommandation.
- La présentation responsive doit encore être vérifiée en exécutant Streamlit sur PC et mobile.
- Ne pas lancer de scripts de tests qui effacent la bibliothèque personnelle.
