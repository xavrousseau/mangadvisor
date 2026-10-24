# Mangadvisor — identité bibliographique et rapprochements prudents

## Source de vérité et limites

- **Œuvre** : catalogue canonique `manga` construit à partir d'identifiants MAL/Tenrai. Une identité Scrinis n'est rapprochée qu'après confrontation de l'identifiant MAL explicite ou du titre exact avec les auteurs. Les œuvres concurrentes restent distinctes.
- **Édition** : la catégorie (Deluxe, Perfect, intégrale, « Pastel » déclaré, etc.) est un **indice de publication**, jamais une identité prouvée sans source et sans validation. Une édition inconnue n'est jamais assimilée à l'édition classique.
- **Tome** : un numéro lu explicitement dans une notice ou un champ `volume_label` reste un indice. Une année « 2024 » ou un titre dérivé ne devient pas un numéro de tome.
- **ISBN** : identifiant d'un livre (validation ISBN-10/13 et checksum). Un ISBN commun à deux sources corrobore la référence, pas l'édition exacte ni la possession.
- **Mangathèque** : `user_manga_*` et `manga_fr_edition` ne sont jamais alimentés par un simple rapprochement de titres ou de références.

La préparation documentaire est isolée dans `bib_stage_batch`,
`bib_stage_candidate`, `bib_stage_edition` et `bib_stage_volume`.
Les livres BnF peuvent également être conservés dans `bnf_bulk_notice`,
et les propositions de recherche par titre dans `manga_bnf_candidate`.
Aucune de ces tables ne vaut association canonique à une édition possédée.

## Règles de vérification multi-sources

1. **Identité de l'œuvre** : rejeter les identifiants MAL contradictoires, les œuvres dérivées identifiables et les candidats concurrents non départagés. En cas de titre exact sans identifiant, exiger la concordance des auteurs pour le lien œuvre Scrinis.
2. **Langue et support** : ne rapprocher que les références explicitement `fr` et `print`; les ebooks et livres japonais ne corroborent pas une édition française papier.
3. **ISBN** : filtrer les identifiants invalides, croiser uniquement les ISBN publiés avec des références d'œuvre Scrinis vérifiée; l'absence n'est jamais une preuve qu'un livre n'existe pas. Conserver toutes les langues déclarées par la notice BnF (une notice `fre` + `eng` est à revoir, pas une preuve de livre français exclusivement).
4. **Famille d'édition** : quand les deux notices disent explicitement Deluxe / Pastel / Perfect / intégrale etc., marquer `ISBN_EDITION_CONFLICT_REVIEW` si les familles divergent.
5. **Tome** : si les numéros explicites se contredisent, marquer `ISBN_VOLUME_CONFLICT_REVIEW`. Si le même ISBN est donné pour plusieurs familles ou tomes distincts côté fournisseur, marquer `ISBN_SUPPLIER_REFERENCE_CONFLICT_REVIEW`. Ne jamais interpréter une année de publication (1900–2099), un livre dérivé ou une autre œuvre comme un tome de la série.
6. **Données incomplètes** : conserver `EDITION_AND_TOME_UNVERIFIED` ou une preuve partielle lorsque l'un des champs manque. Même `FAMILY_AND_TOME_CONSISTENT_UNVERIFIED` n'autorise pas l'enregistrement automatique.
7. **Staging** : signaler les ISBN cités pour plusieurs œuvres d'entrée, familles d'édition ou numéros de tomes distincts dans `isbn_staging_conflicts`, sans supprimer ni fusionner les propositions concurrentes.

Le retour API/rapport conserve `registration_ready = false`, et le pipeline
annonce `confirmed_editions_written=0` et `user_inventory_written=0`.

## Sources et provenance

La BnF diffuse les livres en lots mensuels ISO 2709 / UNIMARC, notamment en
UTF-8 : https://api.bnf.fr/fr/produits_bibliographiques_mensuels .
Ces lots contiennent de **nouvelles notices**, pas un catalogue historique
complet. La BnF n'a pas publié de produit en avril ni en mai 2026 et
signale une phase de stabilisation ultérieure. Ne jamais traiter ces mois
manquants comme des mois à zéro nouvelle parution.

Les métadonnées BnF sont en Licence Ouverte; conserver notamment
`801$b` (organisme catalogueur) et `801$c` (date) pour l'attribution
UNIMARC, ainsi que l'identifiant FRBNF et l'empreinte de fichier.
Référence : https://www.bnf.fr/fr/conditions-de-reutilisations-des-donnees-de-la-bnf .

Scrinis donne accès à la recherche, aux séries et à la recherche par ISBN,
avec un débit anonyme déclaré de **15 requêtes/minute** :
https://scrin.is/fr/api . Respecter les plafonds et marquer les listes de
références tronquées; l'absence d'un tome dans une réponse bornée ne prouve
rien. Wikidata peut fournir des titres et des alias liés aux identifiants
vérifiés; un alias à lui seul ne valide pas une édition. MangaUpdates peut
aider la recherche mais ne prouve pas une possession.

## Vérification sans installer ou réinstaller Windows

Le code, les rapports synthétiques et les contrôles de CI peuvent évoluer
sans Docker Desktop utilisateur. Les tests offline ciblent les variantes
Dragon Ball (noms d'éditions distincts), les tomes contradictoires,
les ISBN répétés et les sources numériques ou étrangères.

La validation de données réelles nécessite une base PostgreSQL isolée.
L'ancien Compose sandbox du dépôt a été retiré.
Les étapes non certifiées restent suivies dans
[l'issue #71](https://github.com/xavrousseau/mangadvisor/issues/71).

## Frontière V1 / V2

Ces règles relèvent de la fiabilité **fonctionnelle V1**, pas du design.
La V2 sera exclusivement consacrée à l'expérience utilisateur.
