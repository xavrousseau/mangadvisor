# Mangadvisor — enrichissement bibliographique gratuit (BnF, première étape)

## Objectif

Compléter progressivement le catalogue Tenrai/MyAnimeList par des **notices
bibliographiques françaises sourcées**. Les recherches BnF portent sur les titres
déjà présents dans `manga`. Elles **ne prouvent pas** qu'un ISBN correspond à
une série donnée : chaque résultat est une proposition en attente de vérification.

La BnF propose son catalogue général en SRU 1.2, sans authentification et sous
licence ouverte de l'État :
https://api.bnf.fr/fr/api-sru-catalogue-general

## Utilisation sur Windows

1. Sauvegarder et mettre à jour Mangadvisor via `mangadvisor.cmd` → **3**.
2. Ouvrir `mangadvisor.cmd` → **A** (options avancées) → **10**.
3. Choisir de **1 à 25 mangas** (10 par défaut). Valider la sauvegarde de
   sécurité effectuée automatiquement.
4. Le programme recherche les mangas **physiquement possédés d'abord**, puis les
   séries suivies, puis le reste du catalogue par popularité. Il essaie les
   titres originaux et internationaux exploitables.
5. Consulter le bilan dans le terminal ; ouvrir ensuite les fiches mangas.
   Une rubrique « Notices BnF à examiner » est affichée lorsqu'une recherche a
   été effectuée. Le bouton « Vérifier cet ISBN » reprend le processus existant
   de vérification du livre par son ISBN puis demande confirmation du format et
   du tome.

Les recherches ne portent que sur la première page des 20 premières notices
par titre, et ne constituent **jamais un catalogue exhaustif des éditions**.
Les résultats non rapprochés avec un titre existant restent consultables comme
pistes, mais ne deviennent pas des faits sur la série. Les ISBN déjà rattachés à
une autre série sont signalés, pas récupérés ni réattribués.

Relancer A → 10 traite **les prochaines séries**. Les œuvres contrôlées ne
sont pas réinterrogées pendant 45 jours ; les erreurs sont réessayables après
24 heures. Une option volontaire permet de rafraîchir les œuvres déjà vérifiées,
mais n'est pas nécessaire en usage normal. Chaque requête réseau est espacée
d'au moins 1,25 seconde. En cas d'indisponibilité de la BnF, les erreurs sont
affichées et les précédentes données ne sont pas supprimées.

## Sécurité et structure PostgreSQL

Tables additives créées automatiquement par l'API ou le traitement :

- `manga_bnf_candidate` : `(manga_id,isbn13)`, titre du livre, auteur,
  éditeur, date, langue, notice BnF et indice textuel de rapprochement.
  Le statut de rapprochement est **toujours non confirmé**.
- `manga_bnf_attempt` : une date et un état par manga (`CHECKED`, `EMPTY`,
  `PARTIAL`, `ERROR` ou `SKIPPED`) pour les reprises et bilans.

L'écriture est limitée à ces deux tables. Aucune modification de `manga`,
`jikan_manga_source`, `manga_fr_edition`, `user_manga_library`,
`user_manga_inventory_declaration`, `user_manga_volume` ou des volumes
Docker n'est réalisée. Un résultat de recherche, même assorti d'un ISBN
correct, ne vaut pas validation de la **correspondance série/édition/tome**.
La confirmation reste manuelle via l'API existante `/collection/isbn/{isbn}`.

API en lecture seule :
`GET /collection/mangas/{manga_id}/bnf-candidates`, également proxifiée sous
`http://localhost:8501/api`. Les ISBN associés à une autre série sont étiquetés
`REGISTERED_OTHER`.

Le traitement est idempotent sur `(manga_id,isbn13)` : une reprise ne crée pas
de doublons. Les copies PostgreSQL vérifiées par `mangadvisor.cmd` comprennent
ces nouvelles tables.

## Ce que cette étape ne prétend pas faire

- Elle **n'ajoute pas automatiquement des tomes** : seuls les utilisateurs
  confirment chaque édition après vérification de l'ISBN.
- Elle ne déclare pas que le titre français d'une **œuvre** est déterminé
  simplement parce qu'un livre candidat porte ce titre.
- Elle n'est pas un moissonnage massif de toutes les notices BnF.
- Elle n'enrichit pas automatiquement les synopsis ni les tags thématiques ;
  la prochaine étape étudiera un fournisseur spécialisé et ses droits d'usage.
- Elle ne promet pas de couvertures ni de stock chez les libraires.

Prochaines sources à évaluer : MangaUpdates (genres/thèmes/synopsis et conditions
d'utilisation) puis données ouvertes ou fichiers bulk pour les enrichissements
bibliographiques à plus grande échelle. Aucun autre fournisseur n'est utilisé
par ce premier traitement.

## Tests

`tests/test_bnf_batch.py` valide l'absence d'écriture sur les tables de
bibliothèque, le filtrage de provenance, la reprise après panne, la priorité
d'acquisition et le contrôle des paramètres.

`tests/web/bnf-candidates.test.mjs` vérifie les libellés non confirmés,
les actions de vérification manuelle et l'échappement HTML.

Les contrôles CI du dépôt exécutent aussi les validations Python, Node, Windows
et Docker existantes. Une recherche BnF réelle reste tributaire de la
disponibilité du service distant.
