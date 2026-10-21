# Enrichissement français direct du catalogue MAL depuis Scrinis

## Étape opérationnelle — après le chargement complet MAL/Jikan

Le catalogue **source** est \`jikan_manga_source\` (~85 776 notices
annoncées dans le dernier rapport local). Le catalogue **actif** est
\`manga\`, rattaché à l'œuvre via \`source_mal_id = mal_id\`.

\`mangadvisor.cmd → A → 20\` est le premier traitement d'enrichissement
direct : il sélectionne les **œuvres canoniques sans titre français
sourcé**, cherche leur nom public auprès de **Scrinis**, vérifie les
informations indépendantes, puis enregistre les **titres français
suffisamment étayés** dans \`manga_title_alias\` avec provenance
\`SCRINIS_FR_PRINT\`. Ces alias sont immédiatement lus par
\`GET /mangas\`, \`GET /mangas/{id}\` et **affichés sur le site**.

Cela ne déclenche ni nouvel import MAL, ni benchmark V2, ni staging.

## Lancement

1. Depuis le clone Windows, ouvrir \`mangadvisor.cmd\`, puis **3** pour
   récupérer les dernières modifications.
2. Sélectionner **A → 20**.
3. Choisir un lot entre **1 et 100 œuvres** (20 par défaut) et confirmer.
4. La sauvegarde PostgreSQL est exécutée puis les recherches Scrinis,
   espacées d'au moins 4,5 secondes entre les appels réseau.
5. Le bilan distingue les nouvelles étiquettes réellement créées,
   les correspondances documentées, les refus de rapprochement,
   les absences de candidat et les erreurs API.
6. Consulter le catalogue et, pour les compteurs cumulés,
   \`GET /catalogue/coverage\` de l'API locale.

**Chaque relance sélectionne un nouveau lot**, grâce à
\`manga_scrinis_fr_attempt\` (cache de 45 jours pour les réponses
documentaires, 1 jour après erreur fournisseur). Le catalogue international
reste inchangé ; l'enrichissement se poursuit par petits lots.

## Critères d'acceptation automatiques

Une œuvre ne reçoit un titre \`SCRINIS_FR_PRINT\` que si les critères
suivants sont **tous** remplis :

- Le candidat Scrinis est **non ambigu** et possède un ID public numérique
  exploitable ; les suggestions approximatives sont écartées.
- Il existe un lien **MAL ID identique**, *ou bien* une correspondance
  exacte parmi les titres de la notice MAL **ET** au moins un auteur
  identique après normalisation indépendante (accents/ordre prénom-nom).
- Si Scrinis fournit un MAL ID différent, l'œuvre est rejetée, même si
  titre et auteur coïncident.
- Le type d'œuvre n'est pas incompatible (ex. manga / roman).
  Les One-shots ne sont pas rapprochés automatiquement dans cette phase.
- La fiche détaillée Scrinis confirme **au moins un ISBN-13 français
  papier** dans les références effectivement consultées, et possède un
  titre utilisable.
- Un même ID Scrinis ne peut pas être associé automatiquement à deux
  identifiants de manga MAL différents : contrainte SQL
  \`manga_scrinis_fr_fact.scrinis_public_n UNIQUE\`.

Le résultat positif est inscrit comme **preuve documentaire de
publication française**, pas comme possession. Les cas tels que les deux
*Wind Breaker*, *Black Clover* et son one-shot ou *Yu-Gi-Oh!* et son
roman restent en vérification manuelle dès qu'une ambiguïté subsiste.

### Ce qui est enregistré dans PostgreSQL

- \`manga_title_alias\` : nom de série FR, langue \`fr\`,
  source \`SCRINIS_FR_PRINT\`, ID public Scrinis et URL source.
- \`manga_scrinis_fr_fact\` : ID MAL et ID Scrinis, preuve d'identité,
  preuve auteur, nombre de références ISBN papier FR consultées.
- \`manga_scrinis_fr_attempt\` : traitement effectué, statut
  \`MATCHED\`, \`AMBIGUOUS\`, \`AUTHOR_CONFLICT\`, \`PROVIDER_ERROR\`, etc.

Les données du fournisseur peuvent être **incomplètes** : les réponses
Scrinis détaillées sont encore limitées à une partie des volumes et ISBN
par fiche, comme dans notre moteur V2. L'absence d'ISBN dans la fraction
retournée ne prouve pas qu'il n'existe pas d'édition française.

Les titres d'œuvre SCRINIS_FR_PRINT apparaissent en premier pour
l'affichage français dans Mangadvisor, puis les titres MAL explicitement
typés FR et les titres Wikidata P4087 déjà validés. Les titres source
EN/JA et \`manga.title\` ne sont **pas écrasés**.

## Frontière de sécurité

**Ce traitement n'écrit pas** dans \`manga\`, \`manga_fr_edition\`,
\`user_manga_*\`, \`user_manga_volume\`, les ISBN physiques associés
à l'utilisateur, ni dans les états de lecture. La présence d'un ISBN
dans Scrinis ne permet **jamais** d'affirmer qu'un tome est possédé.

Les informations envoyées à Scrinis se limitent aux titres publics de
l'œuvre. **Aucune donnée de collection personnelle ne quitte le PC**.

Les fiches ambiguës ne sont pas automatiquement fusionnées ; les
statuts refusés sont conservés pour une future interface de revue.

## Mesurer les résultats réels

Le compteur \`new_french_aliases\` du lot indique les ajouts à la table
réellement affichée par le site. \`matched_sources\` peut être plus élevé
lorsqu'un titre était déjà présent.

L'endpoint \`/catalogue/coverage\` expose notamment
\`works_with_french_label\`, \`scrinis_french_titles_added\`,
\`scrinis_french_print_work_matches\` et
\`scrinis_work_labels_with_evidence\`. Ces chiffres sont **mesurés
dans PostgreSQL**, pas estimés à partir des candidats d'API.

## Étapes suivantes

Cette phase s'appuie sur **Scrinis en priorité** car sa fiche permet de
confirmer le marché français papier par ISBN et de vérifier l'auteur.
MangaUpdates, BnF et les autres sources compléteront les œuvres
restantes. Les correspondances complexes pourront être validées dans
une interface de revue, sans sacrifier les identifiants MAL canoniques
ni les éditions possédées.
