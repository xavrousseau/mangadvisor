# Étape 27 — Construire les identifiants internationaux de la base entière

Après avoir exécuté **A → 26** (référentiel de 85 776 œuvres), lancer
**A → 27 — Enrichir la base publique depuis AniList**.

Le premier lot traite **64 identifiants MAL manga au maximum**. Après chaque
requête, une ligne `catalogue_provider_attempt` est enregistrée par œuvre :
`MATCHED`, `NOT_RETURNED` ou `PROVIDER_ERROR`.

- La relation `MAL → AniList` est enregistrée **uniquement lorsque la réponse
  contient le même ID MAL**. Le titre français ou romaji ne sert jamais de clé
  de jointure.
- AniList renvoie souvent des titres anglais, romaji et japonais. Cela
  **n'ajoute pas de traduction française fictive**. Les titres français
  viendront de Wikidata `P4087` (libellé français), MangaDex `altTitles.fr`,
  Scrinis, BnF et éditeurs après validation des identifiants et des œuvres.
- `NOT_RETURNED` signifie seulement que ce lot n'a pas été renvoyé par
  **cette requête AniList filtrée** : pas de preuve que le manga n'existe
  pas sur le site. Les erreurs HTTP / 429 restent `PROVIDER_ERROR` avec
  reprise au plus tôt une heure plus tard.
- Une coupure après un lot n'efface pas les lots précédents : ils sont
  enregistrés atomiquement. Relancer A → 27 passe aux identifiants MAL
  qui n'ont pas encore de résultat. La bibliothèque personnelle et les
  éditions/ISBN possédés ne sont jamais interrogés ni modifiés.
- Un verrou PostgreSQL empêche deux instances d'enrichir le même référentiel
  en parallèle.
- En raison de la limitation dégradée **30 requêtes par minute** documentée
  par AniList, les appels sont séparés d'au moins **2,3 secondes**.
  L'enrichissement de 85 776 œuvres nécessite donc de nombreux lots et
  ne peut pas être accompli instantanément.
- A → 27 est une première phase *mesurable*, pas une promesse de 95 %
  de correspondances, ni un résultat pour tous les catalogues externes.

Pour une mesure en lecture seule :

```sh
docker exec mangadvisor_api python -m apps.api.app.catalogue_anilist_batch --report-only
```

Pour un lot explicite plus important (200 maximum par exécution) :

```sh
docker exec mangadvisor_api python -m apps.api.app.catalogue_anilist_batch --run --limit 200
```

L'option A → 27 traite 64 identifiants par exécution, sans paramètres à saisir.

Sources officielles :
- https://docs.anilist.co/guide/rate-limiting
- https://docs.anilist.co/reference/query

Le moteur de rapprochement des éditions françaises et les identifiants
Kitsu/MangaDex/Wikidata restent des chantiers séparés à construire sur
ce même référentiel, sans reprendre une collecte intégrale Jikan.
