# Sources et limites — choix vérifiables

| Source | Usage retenu | Identifiant | Limite |
| --- | --- | --- | --- |
| MyAnimeList via Jikan/Tenrai | Catalogue brut initial, genres, thèmes, auteurs, relations quand sourcées | `MAL:manga:<id>` | Jikan est une passerelle non officielle ; vérifier l'accès, les limites d'appels et les droits de réutilisation. Les synonymes non typés ne prouvent rien. |
| Wikidata | QID, `P4087`, labels FR/EN/JA et liens sourcés | `Wikidata:Q...` et P4087 | Données communautaires ; vérifier contradictions et types de média. |
| BnF Catalogue général | Notices de livres, ISBN, éditeurs, collections, responsables | ARK/ISBN + notice | SRU accessible sans clé sous licence ouverte, attribution requise ; distinguer notice/édition et œuvre. |
| Éditeurs français | Valider collection, format, tome et édition | code éditeur / ISBN | Respecter le droit d'accès/republication et enregistrer la provenance. |
| MangaDex / Kitsu | Pistes additionnelles d'identifiants et noms multilingues | IDs du fournisseur | Envisager seulement après vérification des conditions applicables ; leurs titres ne prouvent pas une édition papier. |
| AniList | Pas de collecte de masse ni de duplication pour un tracker sans autorisation | `idMal`, ID AniList | Conditions officielles restrictives : https://docs.anilist.co/guide/terms-of-use. |
| Mangahook / OmegaAPI | Hors socle V1 | variable | Agrégateurs/scrapers, qualité/accès/conditions non vérifiés pour un référentiel bibliographique durable. |

Références :
- https://api.bnf.fr/fr/api-sru-catalogue-general
- https://www.wikidata.org/wiki/Property:P4087
- https://docs.anilist.co/guide/terms-of-use

**Aucune absence de correspondance ne signifie que l'œuvre n'existe pas.** Les erreurs de fournisseur/quotas ne deviennent jamais des négatifs définitifs.
