# Mangadvisor 3.3 — « Surprends-moi » à partir de ma bibliothèque

## Problème résolu

Le conseiller savait traiter six ambiances, mais demandait obligatoirement une ambiance même lorsque l'utilisateur lui disait simplement **« Surprends-moi selon mes goûts »**. Pourtant sa bibliothèque contient déjà des séries préférées, bien notées ou en cours de lecture : ces données sont suffisamment utiles pour proposer un premier point de départ **sans inventer un genre, un thème ou un titre**.

## Nouveau comportement

1. Dans **Pour moi → Mon conseiller**, le troisième exemple propose **« Surprends-moi selon mes goûts »**. Le conseiller guidé et le modèle IA local facultatif comprennent cette demande.
2. Sans ambiance explicite, le moteur interroge les **genres et thèmes réellement associés aux mangas appréciés** dans la bibliothèque : favoris, notes à partir de 7/10, ou lectures en cours/terminées sans note. Seuls les éléments du catalogue PostgreSQL comptent.
3. Les suggestions doivent posséder au moins un de ces genres ou thèmes documentés, respectent le score minimum, le type de manga et l'exclusion des mangas déjà présents dans la bibliothèque et des ISBN déjà suivis. Le mode **EXPLORE** diversifie les suggestions sans introduire de titres hors critères.
4. L'interface affiche **« Inspiré de tes lectures »**, les genres/thèmes d'affinité trouvés, et les informations bibliographiques effectivement enregistrées. Elle n'affiche plus un faux bloc « Correspond à ta demande » vide quand aucune ambiance n'a été choisie.
5. La conversation conserve le mode découverte depuis la bibliothèque : **« Français obligatoire »**, **« Série terminée »** ou **« Sans horreur »** s'appliquent à la sélection suivante sans effacer les contraintes existantes. En demandant explicitement une ambiance ensuite, le conseiller reprend les règles de recherche par ambiance.
6. Si aucune lecture appréciée ne permet de déduire des genres/thèmes, le conseiller **explique la limite** et demande de saisir des lectures ou de sélectionner une ambiance. Il ne propose pas des mangas arbitraires.

## Contrat de sécurité

- La détection de la demande personnelle est faite **par le serveur**, non par une nouvelle commande libre du modèle IA. Ollama ne peut pas modifier directement le drapeau de contexte `profile_discovery` : celui-ci est contrôlé côté backend.
- Les données détaillées de la bibliothèque ne sont **pas** envoyées à Ollama. Le modèle n'invente ni recommandation, ni ISBN, ni catégorie officielle, ni disponibilité commerciale.
- Les filtres explicites, notamment les formats français exigés, les critères de longueur, le statut de publication et les exclusions de tags horreur/gore/romance, sont appliqués de la même manière qu'en mode guidé.
- Pas d'écriture en base, pas de migration, pas de réinitialisation de la bibliothèque et aucune dépendance payante. Le mode fonctionne même si Ollama est arrêté.
- L'affinité par genres/thèmes est une **indication**, pas une certitude que le manga plaira ; les tags manquants peuvent limiter la précision.

## Vérifications

Unitaires Python : reconnaissance française/anglaise, passage du mode bibliothèque vers une ambiance, conservation de filtres stricts, contrôle de la frontière IA, classement à partir de tags sourcés.

PostgreSQL jetable : premier message **Surprends-moi**, comparaison avec la vraie bibliothèque artificielle, exclusion des œuvres déjà présentes, séquence conversationnelle **Français obligatoire** et cas **sans personnalisation**.

Chromium desktop/mobile et tests JavaScript : proposition en un clic et affichage des affinités sans bloc ambigu.

## Démarrage

Mettre à jour par `git pull origin main`, démarrer Docker Desktop et sélectionner **option 3** dans `mangadvisor.cmd`. Ouvrir **http://localhost:8501 → Pour moi → Mon conseiller** et essayer **« Surprends-moi selon mes goûts »**. Pour les prochaines étapes, davantage de données personnelles confirmées améliore la qualité des propositions ; aucun import ni modification n'est nécessaire pour activer le mode.
