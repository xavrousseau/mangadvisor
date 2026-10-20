# Mangadvisor — enrichissement Wikidata par identifiant MAL (P4087)

## Pourquoi Wikidata ?

Après Tenrai (catalogue de base) et BnF (notices des *livres* français,
ISBN et éditions **à vérifier**), Mangadvisor peut aussi consulter **Wikidata**.
Les données structurées Wikidata sont publiées sous **CC0** :
https://www.wikidata.org/wiki/Wikidata:Licensing

La propriété [MyAnimeList manga ID — P4087](https://www.wikidata.org/wiki/Property:P4087)
désigne une **entrée manga MyAnimeList** (différente de P4086, réservée
aux animes). La base PostgreSQL conserve déjà l'identifiant dans
\`manga.source_mal_id\`. Un rapprochement par identifiant source évite
les correspondances incertaines reposant uniquement sur des titres.

**Limite** : une étiquette en français dans Wikidata n'est **pas la preuve**
qu'il s'agit du titre vendu en France, ni d'une édition Glénat, Kana,
Delcourt, etc. Une description Wikidata est généralement une phrase
d'identification, **pas un synopsis littéraire**.

## Utilisation sans ligne de commande

1. Depuis le dossier Mangadvisor en clone Git, \`mangadvisor.cmd\` → **3**.
   Cette option sauvegarde PostgreSQL, récupère GitHub, reconstruit Docker
   et vérifie les services.
2. Ensuite \`mangadvisor.cmd\` → **A — Options avancées** → **11 — Wikidata**.
3. Choisir de 1 à 15 œuvres (8 par défaut), puis répondre **Non**
   à l'actualisation des œuvres déjà traitées.
4. Une sauvegarde PostgreSQL **avec restauration de contrôle** précède
   les nouvelles écritures de métadonnées.
5. Ouvrir les fiches mangas pour voir « Informations complémentaires ·
   Wikidata » et leur lien direct vers la source. Les libellés français
   Wikidata peuvent également être affichés dans le conseiller, avec
   un avertissement de provenance, lorsque le rapprochement P4087 est unique.

Le traitement explore **d'abord la collection physique**, puis la
bibliothèque, puis le catalogue par popularité. On peut relancer des lots :
les succès/absences/ambiguïtés déjà vérifiés sont conservés pendant 45 jours,
les erreurs peuvent être retentées après un jour, ou relancés sur décision
explicite avec « Actualiser ».

## Source, quotas et comportement des pannes

- Service public : https://query.wikidata.org/sparql
- \`SELECT ?item ... WHERE { VALUES ?malId ... ?item wdt:P4087 ?malId }\`
- **Une requête** par lot de 15 identifiants au maximum ; pas de parallélisme.
- Requête limitée à 500 lignes, réponse limitée à 1 Mo, timeout 25 secondes.
- Identification \`User-Agent\` avec URL du dépôt Mangadvisor.
- Sur refus 429, 503 ou panne de réseau, **aucun retry immédiat** : un
  état ERROR est enregistré et le script signale l'échec.
- [Manuel WDQS et limites](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual).
  Les limites sont susceptibles de changer et le service public peut être
  temporairement inaccessible. Un appel réel n'est pas garanti par la CI.

## PostgreSQL : uniquement deux tables additives

- \`manga_wikidata_fact\` : un enregistrement par œuvre (manga_id + MAL
  source ID), identifiant Wikidata, label FR, description FR courte,
  genres FR et source nominative. **Aucune modification des tags canoniques.**
- \`manga_wikidata_attempt\` : état d'une recherche
  (\`MATCHED\`, \`NOT_FOUND\`, \`AMBIGUOUS\`, \`ERROR\`) et date.

Deux éléments Wikidata différents avec le même identifiant P4087
entraînent \`AMBIGUOUS\` : **aucune information n'est retenue**. Les
métadonnées de précédentes recherches ne sont affichées que si le dernier
état est \`MATCHED\` et que l'identifiant source concorde toujours.

La collecte ne modifie jamais \`manga\`, \`genre\`, \`manga_genre\`,
\`manga_theme\`, \`manga_fr_edition\`, \`user_manga_library\`,
\`user_manga_volume\`, \`user_manga_inventory_declaration\`, ni les
données Docker.

L'API \`GET /enrichment/mangas/{id}/wikidata\` est en lecture seule. Les
drapeaux \`description_is_plot_synopsis\`, \`french_publisher_title_verified\`
et \`editions_verified\` restent tous **false** : l'IA ne doit pas présenter
une fiche Wikidata comme une édition française ou un synopsis confirmé.

## Effet sur le conseiller

La sélection, les exclusions de mangas possédés, les preuves d'affinité,
les filtres de genres et les contraintes d'éditions françaises restent
calculés à partir des tables déjà vérifiées. Seul le **nom affiché**
pour une recommandation en français peut utiliser \`label_fr\` si le
rattachement P4087 est unique ; la provenance Wikidata est indiquée
explicitement, et le titre d'origine est conservé en dessous.

Cela améliore la lisibilité sans attribuer de faux goûts ou de faux ISBN.

## Étapes suivantes possibles

La couverture Wikidata par identifiant P4087 est partielle. Un synopsis
détaillé et des catégories narratives fiables nécessitent une source
spécialisée ayant des conditions de réutilisation compatibles. La BnF
continue d'être la source dédiée aux ISBN et aux tomes français.

Tests : \`tests/test_wikidata_enrichment.py\`,
\`tests/web/wikidata-view.test.mjs\`, intégration GitHub sur PostgreSQL
jetable et navigateur. Aucun test synthétique n'utilise la collection privée.
