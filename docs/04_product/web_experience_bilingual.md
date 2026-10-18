# Mangadvisor — nouvelle interface web moderne (lot UX bilingue)

## Pourquoi une nouvelle interface ?

La première version Streamlit a permis de valider les appels au moteur mais ne tenait
pas la promesse de l'interface sombre/orange. Les fiches étaient trop loin du clic,
l'accueil expliquait mal les possibilités et les données Jikan apparaissaient en anglais.

La nouvelle interface conserve **toutes les données et l'API FastAPI**. Aucune
migration SQL ni écriture automatique de bibliothèque.

## Démarrer sur Windows

1. Conserver le fichier .env et les volumes Docker existants.
2. Mettre à jour le dépôt : git pull origin main (une fois ce lot fusionné).
3. Depuis le répertoire Mangadvisor, lancer mangadvisor.cmd puis 3
   (Build + démarrage).
4. Ouvrir http://localhost:8501 pour l'interface moderne.
5. L'ancienne interface Streamlit, comprenant notamment l'import CSV/Excel,
   reste accessible à l'adresse http://localhost:8502.

## Pages et fonctionnalités

- **Accueil** : trois actions claires, parcours en trois étapes et 5 mangas du catalogue.
- **Découvrir** : recherche par titre, genre, publication, pagination de 12 et couvertures.
- **Fiche manga** : URL directe /manga/{id}, compatible historique précédent/suivant,
  couverture, synopsis, métadonnées, genres/thèmes, note MyAnimeList, ajout et mise à jour
  de la bibliothèque, recommandations similaires et lien de retour.
- **Pour moi** : recommandations de la bibliothèque ou des titres choisis,
  3 objectifs pour la bibliothèque, critères de publication et note communautaire,
  scores moteur présentés en points et explication conservée.
- **Bibliothèque** : recherche, statut, pagination de 24, favori et note personnelle.
- **Langues** : commutateur visible FR / EN. Les labels, actions, statuts et principaux
  genres/thèmes/démographies disposent de traductions, sans altérer les données sources.
- Responsive : navigation latérale sur PC et barre basse sur mobile.

## Traduction des synopsis

Les synopsis du catalogue sont généralement d'origine anglaise.

- En EN : affichage du texte original.
- En FR, si un prestataire de traduction est configuré : récupération de la traduction
  via POST /localization/synopsis, cache en mémoire de 512 textes, aucune écriture SQL.
- En FR sans prestataire, ou si l'appel échoue : **texte anglais explicitement signalé**,
  jamais présenté comme une traduction réussie.

Pour activer la traduction, fournir dans le .env personnel :
  LIBRETRANSLATE_URL=http://votre-service-libretranslate:5000/translate
  LIBRETRANSLATE_API_KEY=                       # facultatif selon le prestataire

Le service doit être accessible depuis le conteneur API. Aucun service de traduction
n'est lancé automatiquement et aucune clé n'est exigée pour utiliser l'application.
Seuls les synopsis publics du catalogue sont envoyés au prestataire configuré :
jamais les notes personnelles, favoris ou informations de bibliothèque.

## Limites assumées

- Les imports CSV/Excel et outils avancés restent pour l'instant dans Streamlit
  (bouton depuis la Bibliothèque moderne).
- L'application reste **mono-utilisateur sans authentification** : la réserver au PC
  ou réseau personnel de confiance, ne pas exposer telle quelle sur Internet.
- Les étiquettes des thèmes rares non référencés dans le dictionnaire peuvent
  apparaître en anglais ; le texte d'origine n'est jamais traduit à tort.
- Les traductions automatiques du synopsis peuvent comporter des imprécisions.
- Le frontend utilise du JavaScript natif, sans dépendance React ni accès direct à PostgreSQL.
- Les volumes Docker/PostgreSQL du projet existant ne sont pas supprimés ou réinitialisés.

## Validation

Les tests Python vérifient le fallback de traduction ; GitHub Actions démarre une
base **exclusivement fictive**, l'API, Streamlit historique et la nouvelle interface web.
Le navigateur Playwright teste les liens, les fiches, le basculement FR/EN,
les recommandations et l'affichage desktop/mobile. Les captures sont stockées en
artefacts du workflow.

Reste à faire après revue utilisateur : renforcer la couverture FR des champs libres,
compléter les outils d'import directement dans la nouvelle interface, puis ajouter
le conseiller IA sans dégrader la navigation.
