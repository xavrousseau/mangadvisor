# Mangadvisor

**Ta mangathèque, tes découvertes et ton conseiller manga personnel.** Application locale PC + mobile, avec catalogue Tenrai, enrichissement BnF des éditions françaises, bibliothèque et recommandations explicables. Interface sombre/orange, français/anglais, sans abonnement.

[Structure actuelle du dépôt](docs/03_technical/project_structure.md) · [Compte rendu du nettoyage 4.1](docs/03_technical/cleanup_4_1.md)

## Source du catalogue manga depuis le 1er octobre 2026

**Attention :** le fournisseur public Jikan `api.jikan.moe` a officiellement été arrêté le 1er octobre 2026 ([annonce des mainteneurs](https://github.com/jikan-me/jikan-rest/issues/613)). Mangadvisor utilise désormais **[Tenrai v1](https://api.tenrai.org/documentation)**, qui documente un format compatible avec Jikan pour les recherches et les recommandations mangas.

L'URL `https://api.tenrai.org/v1` est utilisée automatiquement, **même si ton ancien fichier .env ne comporte pas encore la nouvelle variable**. Si besoin, elle peut être définie dans `.env` via `MANGA_API_BASE_URL=https://api.tenrai.org/v1`. Aucune clé payante n'est nécessaire, les limitations publiques restent applicables (120 appels/minute, 4 appels/seconde). Le fournisseur est encore en bêta : une coupure est possible.

Les scripts historiques dont le nom contient « Jikan » et les dossiers `data/raw/jikan/` sont conservés pour compatibilité avec les bases et tests déjà existants, **mais les nouveaux JSON enregistrent le fournisseur réel** ; les écritures SQL conservent également `source_name=tenrai`. Le chargement est additif et les associations aux mangas existants restent basées sur les identifiants MyAnimeList (`mal_id`).

L'option **29** vérifie dorénavant la connexion HTTPS au fournisseur configuré **et une vraie réponse manga JSON**. Après mise à jour, relancer 29 puis 25 pour charger le catalogue, 26 pour les recommandations. Aucune réinstallation ni suppression de volume n'est requise.

## Tout piloter depuis mangadvisor.cmd (centre de pilotage 4.x)

Pour une première installation sur Windows : **télécharge le dépôt GitHub (ZIP ou Git), démarre Docker Desktop, double-clique sur mangadvisor.cmd et choisis l'option 22 — Installer de A à Z**. Aucun Python, psql ou terminal technique à installer sur Windows : les opérations data fonctionnent dans Docker.

L'assistant prépare le fichier .env avec des secrets aléatoires, crée les tables PostgreSQL, démarre l'application, **extrait les JSON Jikan SEARCH + TOP, les charge dans PostgreSQL, construit le catalogue et récupère les recommandations communautaires**, vérifie API/SQL/UI, effectue une sauvegarde testée et propose l'aperçu puis l'import confirmé de ta bibliothèque personnelle (CSV à placer dans private-data/mangatheque.csv). Les éditions françaises ISBN sont à compléter séparément après vérification BnF.

Les options **23 à 29** permettent ensuite de refaire chaque opération sans réinstallation : configuration, tables, catalogue, recommandations, diagnostic, **mise à jour Git + sauvegarde + Docker** et diagnostic réseau Docker/Tenrai (29). Les étapes 25 et 26 vérifient maintenant l'accès externe avant de lancer leurs extractions. Les options historiques de maintenance, sauvegarde et import sont conservées ; l'ancien sous-menu 12 a été remplacé par un alias de compatibilité vers l'option 25. **L'option 22 n'efface jamais tes volumes**, et l'option destructive 11 doit rester exceptionnelle et volontaire.

Voir [le guide complet du centre de pilotage 4.0](docs/04_product/control_center_4_0.md).

## Démarrage habituel sur Windows (base déjà initialisée)

1. Installer et démarrer **Docker Desktop**. Placer le dépôt GitHub sur le PC.
2. À la racine, exécuter **mangadvisor.cmd**, puis choisir **3 — Build + démarrage**.
3. Ouvrir **http://localhost:8501**. Les outils historiques Streamlit sont accessibles à **http://localhost:8502**.
4. Naviguer dans **Découvrir**, **Ma bibliothèque** et **Pour moi → Mon conseiller**.

Pour mettre à jour après une nouvelle version : lancer git pull origin main puis le menu 3. **Ne jamais supprimer les volumes Docker de production ni utiliser l'option Nuke** si l'on souhaite conserver la collection.

### Voir les éditions physiques dans l'application (Mangadvisor 3.9)

Dans **Ma bibliothèque**, le volet **Mon inventaire physique par édition** affiche les éditions déclarées d'une même œuvre et leurs quantités séparées. Chaque fiche manga affiche également les éditions physiques déclarées, distinctes des livres par **ISBN réellement vérifiés**. Cela ne crée ni ISBN, ni tomes lus, ni séries supposées complètes. Le volet est vide jusqu'à l'import confirmé du CSV personnel.

Voir : [Tableau des éditions physiques 3.9](docs/04_product/physical_inventory_dashboard_3_9.md).

### Importer ton inventaire avec confirmation (option 21 — Mangadvisor 3.8)

Après avoir effectué une **sauvegarde validée (option 17)**, place le CSV privé dans `private-data/mangatheque.csv`. Démarre l'application et choisis l'**option 21**. Le script rapproche seulement les œuvres aux titres correspondants de façon exacte et unique, puis affiche un **aperçu sans écriture** : lignes prêtes, éditions distinctes, lignes ambiguës et données préexistantes. Une confirmation textuelle explicite est obligatoire avant l'import, notamment pour accepter un import partiel.

Les quantités par **édition déclarée** sont conservées séparément des ISBN vérifiés. Une œuvre absente de la bibliothèque est ajoutée comme « Possédée » pour éviter qu'elle soit recommandée ; **aucune note, favori, statut existant ou tome lu n'est écrasé**. Un titre manquant ou homonyme reste à vérifier. Les fichiers et rapports restent exclusivement dans `private-data/`, ignoré par Git.

Voir [Import sécurisé 3.8](docs/04_product/safe_inventory_import_3_8.md).

### Tester ta vraie mangathèque sans importer les données (option 20)

Copier ton CSV de collection dans le dossier local `private-data/mangatheque.csv`, puis lancer Mangadvisor et choisir **option 20** dans `mangadvisor.cmd`. Le test rapproche les titres avec le catalogue réel via `dry_run=true`, signale les homonymes/éditions et mesure des recommandations en lecture seule. Après tes réactions aux suggestions, relancer l'option 20 permet de comparer les recommandations avant/après. **Ne jamais publier la collection sur GitHub** : `private-data/` est exclu de Git.

Voir : [Benchmark privé de la mangathèque 3.6](docs/04_product/private_library_benchmark_3_6.md).

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
- **Conseiller conversationnel** : affinage multi-tours (longueur, ambiance, édition française, exclusions romance/horreur/gore selon les tags) et compréhension IA locale facultative. Le panneau « Comment cette sélection est-elle construite ? » mesure la diversité des tags et les affinités documentées, sans inventer de pourcentage de compatibilité. Les contraintes explicites restent prioritaires même si l'IA locale les interprète mal. Les statuts **WANT_TO_READ** sont des indices d'intérêt faibles et des refus de plusieurs mangas ayant des tags communs peuvent moduler légèrement l'ordre, jamais bannir un genre.
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
