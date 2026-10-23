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
as edition/ISBN correctness. The bar is precision ≥95% AND recall ≥95% on
this gold set with zero unauthorized inventory writes; publish numerator,
denominator and all errors. If the gold labels are incomplete or the
threshold is not reached, the feature remains experimental.

## Remaining hard limits

A correct answer about a French title absent from Jikan cannot be proven
by PostgreSQL word matching alone: federated source cross-ID lookup and a
non-MAL canonical-work identity are still needed for full coverage.
Book-level evidence needs French edition and contributor corroboration
before any ISBN-to-work certification. Do **not** call a hypothetical match
95% reliable because it has a heuristic score of 95: the scores are not
calibrated probabilities.
