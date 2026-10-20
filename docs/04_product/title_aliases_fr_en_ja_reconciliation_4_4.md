# Mangadvisor — Titres manga multilingues (FR / EN / JP) et rapprochement sans doublons

## Constat réel

La fiche MyAnimeList manga **74** correspond à *Shingeki no Kyojin*,
aussi connu sous le nom *Attack on Titan* et commercialisé en France
sous *L'Attaque des Titans*.

Mangadvisor conservait déjà ces titres dans plusieurs bases, mais la
recherche de rapprochement n'utilisait que les colonnes principales
(title/title_english/title_japanese). Des variantes étaient encore dans
\`jikan_manga_source.raw_json\`, inutilisées. Wikidata avait été exploité
uniquement pour un libellé FR et les genres : pas pour les alias
multilingues. Les notices BnF de volumes ne doivent pas être assimilées
au titre de l'œuvre sans preuve supplémentaire.

Une difficulté supplémentaire est apparue sur la collection personnelle :
\`Shingeki no Kyojin\` est déjà déclaré avec **34 tomes principaux + 1 autre
édition non identifiée**, alors que \`L'Attaque des Titans\` figure également
parmi les entrées en attente avec **35 exemplaires**. **Il n'est pas
possible de savoir automatiquement s'il s'agit exactement des mêmes livres.**

## Sources vérifiées et restrictions

| Source | Usage adopté | Condition / limitation |
|---|---|---|
| MyAnimeList/Jikan déjà chargé dans PostgreSQL | Titres japonais, anglophones, romaji, \`titles[]\` et \`title_synonyms[]\` déjà présents dans \`raw_json\` | L'identifiant MAL connu rattache chaque alias à une seule œuvre. Une même chaîne peut appartenir à plusieurs œuvres ; les suggestions restent manuelles. |
| Wikidata P4087 | \`rdfs:label\` et \`skos:altLabel\` en **fr**, **en**, **ja** via l'ID **MAL manga**, et libellé FR déjà enregistré. | CC0. Seule une correspondance Wikidata unique est acceptée. Les libellés français communautaires ne sont **pas** des preuves de commercialisation en français. Source : https://www.wikidata.org/wiki/Property:P4087 |
| BnF, notices d'autorité d'œuvre | Une première correspondance documentaire contrôlée pour MAL **74** : \`L'Attaque des Titans\`, \`Attack on Titan\`, \`Shingeki no Kyojin\`. | https://catalogue.bnf.fr/ark:/12148/cb177166897 — série de mangas d'Hajime Isayama. Une notice d'un **livre** trouvé par recherche de titre ne crée **jamais** un alias de série automatique. |
| BnF, notices bibliographiques / ISBN | Outil BnF déjà existant : livres/éditions en candidats, validation utilisateur. | Accessible en SRU sans authentification et sous licence ouverte : https://api.bnf.fr/fr/api-sru-catalogue-general |
| Open Library et Google Books | Étude complémentaire à réserver à **l'identification d'ISBN** après confirmation d'une édition. | Ne pas les utiliser pour fusionner des œuvres par ressemblance. Open Library recommande les **dumps** pour le bulk, ses API ne doivent pas servir de backend massif (https://openlibrary.org/developers/api). Google Books requiert une identification API (https://developers.google.com/books/docs/v1/using). |
| MangaUpdates et Kitsu | Sources additionnelles possibles après contrôle détaillé des droits, de la couverture et de la correspondance avec l'ID MAL. | Les noms ressemblants ne suffisent pas à une association sûre. Ne pas ingérer en masse sans autorisation. |
| AniList | **Non intégré**. | L'API interdit des usages concurrents de services de suivi manga et la collecte massive : https://docs.anilist.co/guide/terms-of-use |

## Utilisation dans \`mangadvisor.cmd\`

Après **3 — Mettre à jour sans perdre mes données**, choisir :

**A — Options avancées → 13 — Indexer les noms FR EN JP et les titres alternatifs**.

1. Choisir d'**actualiser Wikidata pour la collection** (Oui recommandé
   au premier lancement, car les anciens lots Wikidata ne collectaient pas
   \`skos:altLabel\`). Le menu permet jusqu'à 250 œuvres liées, 80 par défaut.
   Les requêtes sont faites par lots de 15 ID MAL maximum, avec pauses
   entre lots, et arrêt si Wikidata refuse une requête complète.
2. Mangadvisor crée d'abord une **sauvegarde PostgreSQL avec restauration
   de test validée**.
3. Il réutilise **toutes les fiches déjà présentes en base** pour indexer
   les titres/alias, sans nouvel appel MyAnimeList. L'indexation est
   additive/idempotente : la clé est \`(manga_id,alias_key,source_name)\`.
4. Ouvrir le site : la recherche de mangas et l'atelier de rapprochement
   comprennent désormais les titres FR / EN / JP et les synonymes présents.
   Les noms français sourcés sont préférés dans l'interface française,
   avec mention BnF ou Wikidata lorsqu'il y a un tel libellé.

La normalisation convertit les accents latins et ponctuations typographiques
(\`L’Attaque\` = \`L'attaque\`), mais conserve les mots et sous-titres
(\`Dragon Ball\` ≠ \`Dragon Ball Super\`; \`Tokyo Ghoul\` ≠ \`Tokyo Ghoul:re\`)
ainsi que les sons japonais distincts (\`ガ\` ≠ \`カ\`).

**Important :** ceci ne garantit pas automatiquement un nom français pour
chaque manga. Il n'existe pas d'API libre et universelle qui valide
parfaitement les noms FR, éditeurs, langues et toutes les éditions du monde.
L'index indique systématiquement la provenance connue de chaque titre.

## Rapprocher sans doubler sa collection

Dans **Ma bibliothèque → En attente de rapprochement** :

- Rechercher en français (\`L'Attaque des Titans\`), anglais
  (\`Attack on Titan\`) ou japonais (\`Shingeki no Kyojin\` /
  \`進撃の巨人\`). Les résultats montrent le titre principal et, si
  disponible, l'alias utilisé et sa provenance.
- Une œuvre déjà possédée affiche maintenant les **quantités et éditions
  physiques enregistrées**. Les suggestions n'effectuent aucune écriture.
- Cliquer **Examiner cette œuvre** pour comparer l'entrée originale
  avec toutes les déclarations enregistrées pour l'œuvre choisie.
- Si les exemplaires sont des livres **réellement distincts**, choisir
  *Nouvelle édition distincte* si autorisé, cocher la confirmation puis
  enregistrer.
- Si la ligne française compte en réalité les **mêmes exemplaires** qu'une
  déclaration déjà enregistrée, choisir *Ligne déjà comptée : archiver sans
  ajouter de tomes*, cocher la confirmation et enregistrer.
- Si l'édition n'est pas identifiable, **ne rien confirmer**. Les données
  continuent d'être conservées dans les entrées en attente.

Le rapprochement double compté consigne la ligne originale,
\`resolution_mode='MARK_DUPLICATE'\`, l'ID œuvre choisi, le titre et les
quantités dans \`user_manga_inventory_resolution\`. Il **n'ajoute aucun
volume** dans \`user_manga_inventory_declaration\`. Tout se fait dans une
unique transaction et exige deux consentements cohérents côté serveur.

Les modes \`CREATE_DECLARATION\` et \`MARK_DUPLICATE\` ne déterminent **ni
ISBN ni numéros de tome précis**, ne fusionnent pas des éditions déjà
identifiées et ne modifient pas l'historique de lecture.

## SQL et tests

- Table additive \`manga_title_alias\`, indexée sur \`alias_key\`,
  étrangère à \`user_manga_library\` et \`manga_fr_edition\`.
- Migration additive de \`manga_wikidata_fact.alternate_titles\` et
  \`user_manga_inventory_resolution.resolution_mode\`.
- Tests unitaires de langue, accents, kana, source fiable, P4087,
  SQL non destructif, cas des 34+1/35 exemplaires et de l'édition
  déjà existante ; tests navigateur et tests PostgreSQL réel dans CI.
