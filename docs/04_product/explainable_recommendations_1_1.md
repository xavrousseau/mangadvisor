# Mangadvisor 1.1 — Comprendre les recommandations

## Principe produit

Remplacer l'explication technique difficile à lire par une présentation structurée
fondée **uniquement** sur les données renvoyées par le moteur existant.

### Sur chaque carte (« Pourquoi ce manga ? »)

- Thèmes communs, genres communs et cible éditoriale proche, seulement lorsque
  ces tableaux contiennent de véritables éléments.
- Signal communautaire uniquement si `community_recommended_from` est présent.
  C'est une relation explicite de recommandations entre mangas ; jamais inventée.
- Composantes numériques disponibles : `editorial_score`,
  `dominant_intent_score`, `community_score`, `quality_score` et
  `goal_bonus`. Afficher les valeurs réelles en points, positives ou négatives.
- Les composants sont **partiels**. Leur somme ne reconstruit pas nécessairement
  `recommendation_score` (pénalités, bonus divers, ajustements).
- Les critères `sensitive_mismatches` sont affichés clairement comme réserves.
- L'explication `reason` historique reste disponible dans un volet technique.
  Elle est généralement produite en français par le moteur ; en mode EN, le
  texte conserve sa langue originale avec une mention explicite.
- Pas de jauge ou pourcentage de « compatibilité » inventé.

### Sur le profil personnel

Le panneau « Comment Mangadvisor a défini tes goûts » est disponible sous
l'accueil personnalisé et l'écran « Pour moi » :

- Sources réellement utilisées : `positive_sources` (depuis la bibliothèque)
  ou `sources` (depuis les titres choisis), dans leur ordre renvoyé par l'API.
- Statut, note et favori affichés seulement s'ils ont été retournés.
- Genres/thèmes dominants depuis `profile_summary`, lorsque présents.
- Mention explicite : ces sources forment le **profil global**, elles n'ont pas
  forcément contribué chacune à une recommandation précise.
- Aucun contenu fictif ou correspondance « Parce que tu as aimé X » sans preuve.

### Langues et ergonomie

Toutes les nouvelles sections, titres, mentions et réserves sont FR/EN.
La traduction des genres/thèmes réutilise le dictionnaire existant.
Le volet est repliable, sur ordinateur et mobile, sans imposer de longs textes
au milieu des cartes.

## Technique

- Nouveau module pur `apps/web/assets/explain.js` : mise en forme des données
  existantes, non-mutante et sans dépendance SQL.
- Réutilisation pour accueil, recommandations de bibliothèque/manuelles et
  recommandations similaires depuis une fiche.
- Aucun changement du moteur, de l'API ni du schéma PostgreSQL.
- Tests Node couvrant : valeurs absentes ou invalides, scores négatifs/nuls,
  absence d'invention de scores, sources vérifiables et immutabilité.
- Test Playwright : ouverture des preuves, affichage des sources et changement
  de langue dans un parcours réaliste sur base Docker jetable.

## Limites

Le moteur ne donne pas encore une décomposition additive complète du score et
ne quantifie pas individuellement l'effet de **chaque lecture source** sur
**chaque manga proposé**. L'interface ne prétend pas le contraire.

L'optimisation du classement et la vérification de la pertinence avec la
bibliothèque réelle constitueront le lot de contrôle suivant, sans utiliser de
tests destructifs.
