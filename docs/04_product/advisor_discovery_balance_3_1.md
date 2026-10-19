# Mangadvisor 3.1 — Des recommandations pertinentes et moins répétitives

## Objectif

Un conseiller peut proposer plusieurs séries quasi identiques parce qu'elles partagent les mêmes genres/thèmes, même si d'autres œuvres intéressantes correspondent à la demande. Mangadvisor 3.1 ajoute trois **modes de sélection** dans **Pour moi → Mon conseiller** : proche de mes goûts, équilibré et surprends-moi. Cette évolution est indépendante de la disponibilité du modèle Ollama et fonctionne donc en mode guidé ou avec IA locale.

## Les trois modes

- **Proche de mes goûts (CLOSE)** : conserve le classement initial par correspondance aux genres, thèmes, préférences vérifiées, indices narratifs, notes communautaires et notices françaises demandées.
- **Équilibré (BALANCED, par défaut)** : conserve les titres les mieux classés mais pénalise modérément les séries portant trop de tags identiques à celles déjà sélectionnées.
- **Surprends-moi (EXPLORE)** : pénalise davantage les répétitions de tags, tout en imposant un niveau minimal de pertinence par rapport aux meilleurs candidats.

L'algorithme est **déterministe**, sans tirage au sort et sans score de « probabilité d'aimer ». Chaque résultat est un manga provenant du catalogue PostgreSQL réel. La nouvelle information « Autres genres et thèmes présents » est issue uniquement des tags existants qui ne figuraient pas dans les suggestions déjà affichées ; elle ne signifie ni différence garantie de scénario ni classification éditoriale.

La diversification intervient **après** les filtres SQL de type de manga, score minimal, statut terminé, longueur, ISBN français demandé et type d'édition requis, l'exclusion des mangas déjà présents dans la bibliothèque, ainsi que les vérifications de tags et exclusions explicites horreur/gore/romance. Les boutons de mode ne changent **jamais** ces contraintes et n'écrivent rien dans la bibliothèque. Le moteur continue à exiger un genre/une ambiance réellement identifié.

## Parcours utilisateur

1. Ouvrir Pour moi → Mon conseiller. Décrire une ambiance et des préférences.
2. Parmi les résultats, choisir **Proche de mes goûts**, **Équilibré** ou **Surprends-moi**. Les boutons envoient une reformulation au conseiller existant et affichent le mode sélectionné.
3. Les critères précédents demeurent actifs. Pour avoir d'autres œuvres plutôt qu'une nouvelle sélection issue des mêmes candidats, demander séparément **« Montre-m'en d'autres »** ; les suggestions déjà affichées sont alors exclues dans la limite de l'historique transmis.
4. Les formats français et les ISBN affichés restent limités aux **livres réellement enregistrés**, sans prétendre couvrir les éditions françaises publiées.

## IA locale et limitations

Ollama **n'est pas requis**. Si l'IA locale est active, elle ne choisit pas les mangas : elle peut retourner l'un des trois modes comme **critère strictement validé** en plus des filtres habituels ; les recommandations restent extraites et classées par le même moteur audité. En cas de modèle indisponible, le repli guidé offre les mêmes trois modes.

La diversité ne peut pas être garantie si toutes les séries admissibles ont les mêmes tags, si le catalogue est pauvre, ou si les contraintes obligatoires ne laissent qu'une ou deux séries. L'application ne sait toujours pas garantir le stock en magasin ni une classification d'âge à partir des tags seuls.

## Validation

- Tests Python : classement proche, différence reproductible en mode équilibré et exploration, qualité minimale, provenance des tags, conservation des exclusions et contexte multitétapes, validation des critères retournés par l'IA locale.
- Tests JS : boutons FR/EN, mode réellement activé, échappement HTML des tags.
- Tests API PostgreSQL jetable et Chromium ordinateur/mobile : changement de mode, maintien des ISBN français requis et des filtres.
- Aucun changement de tables, aucune migration ou suppression des volumes Docker.

## Mettre à jour

`git pull origin main`, démarrer Docker Desktop, lancer `mangadvisor.cmd` option **3 — Build + démarrage**, puis ouvrir **http://localhost:8501 → Pour moi → Mon conseiller**. Le mode fonctionne avec et sans Ollama. Ne jamais sélectionner **Nuke** si la collection doit être conservée.
