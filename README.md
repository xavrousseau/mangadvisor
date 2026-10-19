# Mangadvisor

**Ta mangathèque, tes découvertes et ton conseiller manga personnel.** Application locale PC + mobile, avec catalogue multi-sources, bibliothèque, éditions françaises ISBN et recommandations explicables. Interface sombre/orange, français/anglais, sans abonnement.

## Pour démarrer sur Windows

1. Installer et démarrer **Docker Desktop**. Placer le dépôt GitHub sur le PC.
2. À la racine, exécuter **mangadvisor.cmd**, puis choisir **3 — Build + démarrage**.
3. Ouvrir **http://localhost:8501**. Les outils historiques Streamlit sont accessibles à **http://localhost:8502**.
4. Naviguer dans **Découvrir**, **Ma bibliothèque** et **Pour moi → Mon conseiller**.

Pour mettre à jour après une nouvelle version : lancer git pull origin main puis le menu 3. **Ne jamais supprimer les volumes Docker de production ni utiliser l'option Nuke** si l'on souhaite conserver la collection.

### Sauvegarder ta mangathèque (recommandé avant les grosses mises à jour)

Dans `mangadvisor.cmd`, **17 — Sauvegarder et vérifier** produit un dump PostgreSQL complet dans `backups/` et **teste une vraie restauration isolée**. **18** revérifie la dernière archive ; **19** permet une restauration volontaire avec confirmation explicite, copie de sécurité de la base courante et conservation de l'ancienne base. Les archives privées ne sont jamais envoyées sur GitHub.

**Copie ensuite les fichiers `.dump` et `.dump.json` sur un deuxième support** : une sauvegarde restée sur le PC ne protège pas d'une panne de son disque. Les secrets `.env` et les modèles Ollama sont hors du dump et nécessitent une sauvegarde séparée.

Voir : [Sauvegarde et récupération 3.2](docs/04_product/library_backup_recovery_3_2.md).

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
- **Conseiller conversationnel** : affinage multi-tours (longueur, ambiance, édition française, exclusions romance/horreur/gore selon les tags) et compréhension IA locale facultative. Le panneau « Comment cette sélection est-elle construite ? » mesure la diversité des tags et les affinités documentées, sans inventer de pourcentage de compatibilité. Les contraintes explicites restent prioritaires même si l'IA locale les interprète mal.
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
