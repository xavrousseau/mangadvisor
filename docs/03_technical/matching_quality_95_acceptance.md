# Matching quality: auditable accuracy gates (2026-10-23)

## Root cause

Before this change, a query for `Adieu Eri` used
`ILIKE '%adieu%'` OR `ILIKE '%eri%'`, ranked by popularity and
returned up to 50 hits before filtering. Titles containing `eri` inside
an unrelated word entered the same candidate pool as `Sayonara Eri`.
The presence of a BnF ISBN in `manga_bnf_candidate` was counted as a
possible book despite the possibility of another title by the same author.

## Remediation

- PostgreSQL whole-word boundaries `\\m...\\M` replace arbitrary substring
  discovery; limit 100 raw candidate rows and return the best 20 with a
  transparent heuristic rank; candidate truncation prevents a strong
  suggestion from appearing certain.
- Evidence weight, canonical-title collisions, source-scoped aliases,
  work type and obvious volume incompatibilities are used to **rank
  discovery suggestions**, never automatically confirm them.
- Work-specific BnF classification separates `EXCLUDE_DIFFERENT_WORK`,
  `REVIEW_DIFFERENT_SUBTITLE_OR_WORK`, `REVIEW_SEPARATE_DERIVATIVE`,
  `REVIEW_LANGUAGE_UNVERIFIED` and `POTENTIAL_FRENCH_VOLUME_REVIEW`.
  Invalid source/work relationships do not count as corroborated ISBN
  evidence. Raw BnF candidate staging is preserved for traceability.
- The BnF review is visible in `GET /inventory/pending/triage` and
  optional `GET /inventory/pending/discover?source_key=...&include_bnf=true`.
  No write to manga, editions, user library or ISBNs.

## Optional cross-source identity discovery

For work titles without a local exact match, the read-only discovery endpoint
can explicitly query the publicly available sources, independently:

- `/inventory/pending/discover?source_key=...&include_mangadex=true`:
  publicly declared MangaDex `links.mal` records, checked against our
  existing local MAL IDs. These are *suggestions*; conflicting metadata or
  wrong third-party IDs remain possible.
- `/inventory/pending/discover?source_key=...&include_wikidata=true`:
  exact French/English Wikidata labels or alt-labels with a manga
  `P4087` identity claim, returning the cited Q ID and existing MAL
  catalogue ID when available. Several Q IDs are a review case.
- `include_bnf=true`: book-level edition candidates, not MAL identities.

All external lookups are explicit, bounded and non-mutating; third parties
can receive the queried title. These options cannot supply a missing
physical ISBN, identify a possessed edition from its tome count, or prove
that a work is absent from a particular catalogue.

## Scope of evidence, not a fabricated 95%

Tests cover adversarial examples from previous diagnostic outputs:
Radiant/Ikujitsu; Fairy Tail/novel/incorrect alias;
Wind Breaker manga versus manhwa; Solo Leveling manhwa versus novel;
Sayonara Eri versus misleading substring search hits;
Bleach versus Black/Friend; Naruto versus Naruto vs Hitachi.
The PostgreSQL integration suite asserts real word-boundary behaviour
and HTTP route safety on a **disposable** database.

These deterministic tests must pass 100% in CI, **but passing them is not
proof of 95% precision on the user's 48 actual unresolved works**.
Those 48 rows have no exhaustive independent ground-truth mapping:
34 previously had zero exact candidate; some French supplements have no
MAL counterpart. The owner has not verified all editions/ISBNs.

**Acceptance protocol for the 95% goal:** collect a verified external work ID
(or an explicit no-MAL/unresolved label) for every reviewable row independently;
hold out at least 20% as evaluation-only; record precision among accepted
matches, recall over identifiable works, the false-positive count, and the
abstention rate *separately*. Accuracy for work identity must not be presented
as edition/ISBN correctness. The bar is **precision ≥95%, recall ≥95% AND
resolution coverage of all annotated cases ≥95%**, with zero unauthorized
inventory writes; publish numerator, denominator, abstentions and all errors.
Correctly declining an unsafe identity is useful, but is not counted as a
*resolved and identified work*. French originals without MAL identity require
a separate, source-backed canonical-work implementation before they can
count toward full coverage. If the gold labels are incomplete or the
threshold is not reached, the feature remains experimental.

## International cross-ID connectors: AniList and Kitsu

The optional `include_anilist=true` request uses the official AniList GraphQL
POST endpoint, only `type: MANGA`, retrieving `idMal`, multilingual titles,
synonyms and format. It returns source-scoped candidates even when no MAL ID
exists; without an explicit MAL link the catalogue **is not** silently joined.
The request is one bounded page (12); no automated per-library refresh.
AniList documents a degraded rate limit of **30 requests/minute** in its
current API documentation. HTTP 429 and GraphQL errors return a provider
error, not `NO_MATCH`.

The optional `include_kitsu=true` asks Kitsu JSON:API for up to three MAL
**manga** IDs, then validates each match using
`/manga/{id}/mappings`. Only `myanimelist/manga` and `anilist/manga`
mappings count. Kitsu Cloudflare restrictions can produce an unavailable
provider response. An anime mapping cannot substitute for manga metadata.

Both can be requested with
`GET /inventory/pending/discover?source_key=...&include_anilist=true&include_kitsu=true`.
A joint `CROSS_ID_AGREEMENT_REVIEW` is an inspectable reference alignment,
**not independently verified work identity**, because providers may
reuse the same underlying community mapping. A disagreement becomes
`CONTRADICTION_REVIEW`, requiring investigation; no ownership/ISBN write.
These providers receive the title/MAL ID as a network request only when
explicitly enabled. No bulk external fetch is triggered by the dashboard.

Primary technical references:
https://docs.anilist.co/guide/graphql/
https://docs.anilist.co/reference/object/media
https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting
https://kitsu.docs.apiary.io/#reference/mappings

## Unverified vs contradicted aliases

An alias from an upstream source that has not independently corroborated the
work is `EVIDENCE_INCOMPLETE_REVIEW` / `ALIAS_SOURCE_REVIEW`, NOT a proven
conflict. An unrelated one-volume work presented for a 19-volume declaration,
or an alias that conflicts with another canonical work title, is a
`CONFLICT_REVIEW` / `SUSPICIOUS_ALIAS_REVIEW` case. This distinction
prevents innocent cases such as Nekomajin or Animal Human from being labeled
as incompatible without evidence.

## Remaining hard limits

A correct answer about a French title absent from Jikan cannot be proven
by PostgreSQL word matching alone: federated source cross-ID lookup and a
non-MAL canonical-work identity are still needed for full coverage.
Book-level evidence needs French edition and contributor corroboration
before any ISBN-to-work certification. Do **not** call a hypothetical match
95% reliable because it has a heuristic score of 95: the scores are not
calibrated probabilities.
