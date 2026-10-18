# Mangadvisor 1.2 — Découverte bibliographique des éditions françaises

## Pourquoi cette évolution ?

Un ISBN isolé se recherche déjà dans Mangadvisor via le Catalogue général de
la BnF. Pour trouver de nouveaux tomes, il fallait cependant connaître
l'ISBN à l'avance. Cette étape ajoute une **recherche par titre**, sans
transformer ses résultats en inventaire exhaustif de publications.

## Le parcours

Depuis une fiche manga, l'utilisateur découvre la section
« Découvrir les livres français » :

1. Saisir un **titre français de recherche**. Le titre de la fiche originale
   est montré comme suggestion, mais la requête est modifiable et pas
   lancée automatiquement.
2. Mangadvisor utilise l'API officielle BnF Catalogue général **SRU v1.2** :
   `bib.title all "<saisie>"`, `recordSchema=dublincore`,
   `startRecord=1`, `maximumRecords=20`.
3. Les notices candidates affichent leurs titres bibliographiques, éditeurs,
   auteurs, dates disponibles, ISBN-13 validés, langue mentionnée (ou absence
   de renseignement), URL vers notice ARK et date de récupération.
4. Cliquer « Vérifier cet ISBN » lance **une nouvelle recherche exacte**
   auprès du service ISBN existant. Le numéro d'édition et le numéro de
   tome sont alors proposés comme **champs à confirmer manuellement**.
5. Seulement une fois vérifiés, l'utilisateur peut enregistrer le livre
   via la route existante `POST /collection/mangas/{id}/editions`, qui
   reconsulte elle-même la BnF et refuse les doublons.

## Ce que les résultats ne prouvent PAS

- Ils n'établissent **pas** un lien entre une notice et l'œuvre japonaise.
- Une recherche dans le Catalogue général, même riche, n'est **pas**
  une bibliographie complète de l'ensemble des tomes commercialisés.
- Ils ne prouvent pas qu'une édition est classique, Deluxe, Perfect,
  complète ou disponible en librairie : le titre peut éventuellement
  fournir un indice, mais la confirmation reste manuelle.
- Un ISBN valide dans un résultat ne prouve pas une édition déjà
  enregistrée. Les candidats ont le statut explicite
  `CANDIDATE_UNCONFIRMED`, `manga_match_verified=false`.
- La langue de publication n'est pas devinée : elle reste non précisée
  quand la notice ne la mentionne pas, même dans un catalogue français.

## Protection et traçabilité

- Aucune migration SQL ou écriture sur les tables historiques.
- La recherche par titre est uniquement **GET/lecture seule**.
- URL source BnF sûre : seulement les ARK reconnus ; aucune URL arbitraire.
- Les ISBN doivent avoir 13 chiffres et un checksum valide.
- Les expressions de recherche CQL sont limitées à des caractères autorisés,
  sans guillemets doubles, parenthèses ou opérateurs injectés.
- Les résultats XML sont limités à 1,5 Mo, et les DTD/ENTITY refusées.
- Les métadonnées BnF sont placées sous Licence Ouverte : **conserver le
  nom de la source et la date de récupération**.
  https://www.bnf.fr/fr/conditions-de-reutilisations-des-donnees-de-la-bnf

## Sources et références de développement

- Documentation API SRU BnF :
  https://api.bnf.fr/fr/api-sru-catalogue-general
- Le service SRU supporte `bib.title`, `bib.isbn`, `recordSchema`,
  `startRecord` et `maximumRecords`.
- Aucune intégration éditeur supplémentaire n'est supposée exister ou
  autorisée à ce stade.

## Tests

- Tests Python : recherche CQL sûre, ARK BnF, checksum ISBN, exclusion de
  notices malformées, pagination partielle et absence d'écriture.
- Tests JavaScript : marquage « candidat », aucun lien dangereux,
  HTML non fiable neutralisé, liste vide explicite.
- Playwright desktop/mobile : réponse BnF **simulée en CI**, recherche
  par titre, candidat, deuxième vérification exacte de l'ISBN,
  numéro de tome vide et absence de modification du livre possédé.

## Suite prévue

Un véritable **référentiel éditorial complet** nécessiterait une source
fiable donnant explicitement l'identité exacte d'une édition, ses tomes
et leur statut de publication, avec des possibilités de réutilisation
compatibles. La BnF par titre est une étape de découverte, non une preuve
de complétude. Une fois une source vérifiée, le suivi pourra distinguer
un tome publié et manquant d'un ISBN simplement absent de la base locale.
