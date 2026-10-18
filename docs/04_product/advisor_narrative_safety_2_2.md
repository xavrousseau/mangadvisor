# Mangadvisor 2.2 — indices narratifs et exclusions explicites

## Fonctionnement

Dans **Pour moi > Mon conseiller**, une demande comme :

> Je cherche une enquête psychologique, sans horreur ni gore, et une série courte.

est interprétée en contraintes contrôlables : ambiance **Mystère**, préférence pour les indices **Enquête** et **Psychologique**, exclusion des tags **Horror** et **Gore**, série courte entre 1 et 12 tomes.

Les exclusions sont des **filtres stricts sur les genres et thèmes catalogués**, même quand une exclusion apparaît dans un suivi (« Finalement sans horreur »). Les négations évitent d'interpréter « sans horreur » comme une envie positive d'horreur. Elles restent actives dans la conversation jusqu'à la réinitialisation ou un retrait explicite (« finalement avec horreur »). La saisie naturelle en français et certains équivalents anglais sont pris en charge, mais toutes les tournures libres ne sont pas comprises.

## Pourquoi cette suggestion ?

Les motifs **Enquête**, **Psychologique** et **Survie** sont des préférences narratives *souples*. Ils influencent le classement sans écarter un bon candidat dont les informations sont incomplètes. Chaque carte distingue :

- **Tag du catalogue** : le concept est appuyé par un tag précis réellement présent (Detective, Psychological, Survival).
- **Mot du synopsis** : un mot correspondant est réellement contenu dans le synopsis enregistré, sans interprétation inventée de l'intrigue.
- **Non vérifié dans cette fiche** : aucune de ces deux preuves n'a été trouvée pour ce motif. Cela ne signifie pas que le manga ne le contient pas.

La lecture d'un mot dans un synopsis n'est ni une analyse littéraire ni une certitude sur l'ambiance, la difficulté, l'âge conseillé ou le contenu d'une scène. Aucune correspondance n'est inventée ; les mots et tags présentés sont échappés pour l'affichage. Le classement existant reste déterministe et transparent ; aucune API générative payante n'a été ajoutée.

## Limites importantes

Les exclusions portent **uniquement sur les tags renseignés**. Elles ne sont **pas** une garantie que l'œuvre soit exempte d'horreur, de gore ou d'un autre contenu sensible si sa fiche est incomplète. Par conséquent, ces filtres ne doivent pas être utilisés comme contrôle parental ou certification de contenu.

Le catalogue et la documentation d'éditions françaises restent inchangés ; la présence d'un ISBN enregistré ne prouve pas que la série soit complètement disponible en France ou actuellement en stock. Les mangas déjà présents dans les collections sont toujours exclus. Les règles d'ajout de livres restent celles de la confirmation explicite du scanner.

## Vérification

Tests unitaires : ambiguïtés/négations, cumul et retrait des exclusions, correspondances littérales des synopsis, priorité des tags, signalement des preuves manquantes et classification sans connaissance inventée.

Tests intégrés sur une base PostgreSQL jetable : scénario en plusieurs échanges avec exclusions Horror/Gore, preuves narratives venant du tag **Psychological** et du mot **investigation** dans un synopsis de test, et classement d'un ISBN français factice réservé à la CI. Tests Chromium écran PC et mobile : lecture des preuves et message de critères effectivement compris.

Aucune nouvelle table, aucune migration, aucune altération de la mangathèque personnelle. Récupération après fusion : **git pull origin main**, puis **mangadvisor.cmd > 3 — Build + démarrage**.
