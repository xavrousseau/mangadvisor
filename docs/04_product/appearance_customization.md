# Mangadvisor — Apparence personnalisable (octobre 2026)

## Vérification de l'intégration du nouveau design

Le design web moderne, ajouté puis intégré par la PR #7, est le frontend
principal : Nginx sert apps/web/index.html et les modules apps/web/assets
depuis le conteneur web. docker-compose.dev.yml publie web sur
http://localhost:8501 ; Streamlit reste accessible sur http://localhost:8502
pour les imports et outils avancés.

La feuille de style historique apps/web/assets/app.css reste en place : cette
évolution ne remplace ni le thème approuvé ni les composants métier.

## Nouvelle page Apparence

Accès permanent : bouton **⚙ Apparence** dans l'en-tête sur toutes les pages
(également visible sur mobile). URL directe : /appearance.

### Designs

- **Nuit Manga** (par défaut) : bleu nuit + orange ; reste la direction
  visuelle validée.
- **Noir Cinéma** : fond noir, surfaces graphite, typographie angulaire et
  bordures plus carrées.
- **Papier Japonais** : interface claire crème, fond ivoire, titres éditoriaux
  avec police sérif et cartes plus sobres.

### Accents

**Ambre, Corail, Océan, Menthe, Violet et Or**. La même palette peut être
associée à chacun des trois designs. Pour Papier Japonais, les tons
des textes interactifs sont plus sombres afin de rester lisibles.

### Densité

**Confortable** (défaut) ou **Compact** (plus de mangas visibles sur desktop,
espacements et cartes resserrés sans casser la grille mobile).

### Préservation et fonctionnement

- Les préférences sont enregistrées sous la clé ma-appearance-v1 du
  localStorage **du navigateur**, séparément de la langue.
- Les changements sont immédiats, sans requête API, ni écriture SQL.
- La sélection survit à la navigation et au rechargement de la page.
- Un bouton « Réinitialiser le design » restaure **Nuit Manga + Ambre +
  Confortable**.
- Une préférence absente, inconnue, invalide ou un stockage navigateur refusé
  reviennent proprement à une combinaison connue, sans injection de CSS.
- **Aucune note, collection, manga ou donnée personnelle n'est modifiée.**

## Architecture

- apps/web/assets/appearance.js : registre de thèmes/accents, validation et
  lecture/écriture locale.
- apps/web/assets/appearance.css : tokens CSS des trois designs, couleurs
  de remplissage et de texte contrastées, tailles et styles de grilles,
  aperçus des choix.
- apps/web/assets/app.js : page Apparence, navigation et événements,
  initialisation avant le premier rendu.
- apps/web/assets/i18n.js : interface et options entièrement FR/EN.

## Validation

- Tests Node : défaut conforme au thème validé, 3 designs / 6 couleurs,
  persistance, entrée invalide ou corrompue, stockage bloqué et bascule claire.
- Playwright sur **1440 × 960** et **390 × 844** : choix de Papier Japonais +
  Océan + Compact, calcul de la vraie couleur du fond, rechargement,
  changement FR/EN, Noir Cinéma, retour au thème validé.
- Tests d'intégration Docker/Chromium sur PostgreSQL fictif.
- La prévisualisation automatisée porte sur **le frontend web** ; le rendu
  local avec la vraie bibliothèque doit encore être observé par l'utilisateur.

## Utilisation Windows

Depuis le dossier Mangadvisor après fusion dans main :
  git pull origin main

Puis lancer Docker Desktop, mangadvisor.cmd et choisir
« 3 — Build + démarrage ». Ouvrir http://localhost:8501,
puis cliquer sur **⚙ Apparence** en haut à droite.

Le frontend reste réservé à un usage local ; pas d'authentification
multi-utilisateur ni de déploiement public prévu pour cette étape.
