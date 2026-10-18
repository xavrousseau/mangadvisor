# Mangadvisor

**Ta mangathèque, tes découvertes et ton conseiller manga personnel.** Application locale PC + mobile, avec catalogue multi-sources, bibliothèque, éditions françaises ISBN et recommandations explicables. Interface sombre/orange, français/anglais, sans abonnement.

## Pour démarrer sur Windows

1. Installer et démarrer **Docker Desktop**. Placer le dépôt GitHub sur le PC.
2. À la racine, exécuter **mangadvisor.cmd**, puis choisir **3 — Build + démarrage**.
3. Ouvrir **http://localhost:8501**. Les outils historiques Streamlit sont accessibles à **http://localhost:8502**.
4. Naviguer dans **Découvrir**, **Ma bibliothèque** et **Pour moi → Mon conseiller**.

Pour mettre à jour après une nouvelle version : lancer git pull origin main puis le menu 3. **Ne jamais supprimer les volumes Docker de production ni utiliser l'option Nuke** si l'on souhaite conserver la collection.

### Activer le vrai modèle IA local (optionnel)

Le conseiller fonctionne **sans IA générative** dès le premier démarrage, grâce à son moteur de recherche guidée. Pour augmenter sa compréhension du langage :

1. Ouvrir mangadvisor.cmd puis choisir **15 — Installer et activer le conseiller IA local**.
2. Valider le téléchargement du modèle Ollama **qwen2.5:3b**. Prévoir plusieurs Go libres et assez de mémoire.
3. Ouvrir **Pour moi → Mon conseiller**. Le bandeau indique **IA locale active** si le modèle répond.
4. Utiliser **16 — Arrêter le conseiller IA local** si nécessaire : l'application et les recommandations continuent en mode guidé.

**Les recommandations continuent toujours de venir du catalogue Mangadvisor**, pas d'une liste inventée par l'IA. Aucune clé payante nécessaire. Plus de détails : docs/04_product/local_ai_advisor_3_0.md.

## Fonctionnalités

- **Catalogue manga** : fiches, couvertures, recherche, genres, thèmes, notes, synopsis et traductions identifiées quand une source réelle est configurée.
- **Bibliothèque personnelle** : favoris, statuts, notes, lectures, suivi possédé/lu, import CSV et ajout par ISBN/scanner.
- **Éditions françaises** : notices BnF confirmées, ISBN, éditeurs, formats distincts (classique, Deluxe, Perfect…), recherche assistée des notices manquantes. Pas de disponibilité commerciale supposée.
- **Recommandations** : personnalisation depuis les lectures et préférences, explications fondées sur les tags réels, exclusion des œuvres connues, retours utilisateur et modes de découverte par ambiance.
- **Conseiller conversationnel** : affinage multi-tours (longueur, ambiance, édition française, exclusions romance/horreur/gore selon les tags) et compréhension IA locale facultative.
- **Mobile privé** : option 13 du menu pour configurer le scanner en HTTPS sur le Wi-Fi domestique ; authentification séparée.

## Limites connues

Le modèle local augmente la souplesse de compréhension mais n'est pas encore un agent autonome capable de surveiller ou d'acheter des nouveautés. Les sources de parutions françaises ne sont pas exhaustives. La présence d'un ISBN BnF ne signifie pas que le livre soit en stock, ni que toute la série soit publiée. Les critères d'âge et les avertissements de contenu ne sont pas certifiés par le catalogue.

## Architecture

Sources publiques et notices autorisées → pipelines Python → PostgreSQL + pgvector / Meilisearch → API FastAPI → interface Web. Docker Compose orchestre PostgreSQL, Meilisearch, API et interfaces. Ollama est un **service facultatif**, non accessible de l'extérieur.

Répertoires :
- apps/api : API et moteur de recommandation.
- apps/web : interface PC/mobile.
- apps/ui : interface historique Streamlit.
- pipelines : ingestion et normalisation des sources.
- infra : Docker, réseau, HTTPS local.
- tests : tests unitaires, API PostgreSQL jetable, Chromium PC/mobile.
- docs : architecture, décisions produit et procédures.

Les évolutions sont proposées en pull requests GitHub et ne sont fusionnées qu'après validation des deux workflows. Les tests ne modifient jamais la base personnelle.
