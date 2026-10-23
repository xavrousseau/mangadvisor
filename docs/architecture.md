# Architecture Mangadvisor — V1

## Architecture minimale
- **PostgreSQL 16** : unique source de vérité pour le catalogue, éditions, bibliothèque, preuves, imports. Recherche d'abord via FTS/`pg_trgm` ; pas de Meilisearch tant qu'un benchmark ne prouve pas la nécessité.
- **FastAPI** : routes métier simples (`/catalogue`, `/works/{id}`, `/editions`, `/library`, `/recommendations`, `/health`).
- **Web statique HTML/CSS/JS derrière Nginx** : conserver l'orientation et le thème déjà validés, ne pas revenir à Streamlit.
- **Un module de pipeline Python** : `fetch → raw → normalize → reconcile → publish`, idempotent et reprenable, avec un état de traitement et des métriques.
- **Docker Compose unique** : `postgres`, `api`, `web`. IA locale Ollama facultative dans un profil Compose lorsque le conseiller guidé fonctionne.
- **Un lanceur Windows** : installer/démarrer, charger/actualiser le catalogue, importer sa bibliothèque, sauvegarder/restaurer, diagnostiquer, mettre à jour, arrêter.

## Identité et fiabilité
`work.id` est notre clé interne. `external_identifier(provider, media_type, external_id)` lie un ID fournisseur et une œuvre, seulement avec une preuve. Les ID MAL, Wikidata QID ou autres NE SONT PAS des IDs universels. Un titre, même exact, ne justifie jamais la fusion de deux œuvres.

Les alias Jikan `title_synonyms` non typés servent à **découvrir des candidats**, pas à **prouver** une identité. Un chapitre d'un recueil n'est pas automatiquement une œuvre équivalente.

`work` → `edition` → `publication` (tome, ISBN) → `owned_item`. Les éditions Dragon Ball Pastel/Deluxe sont distinctes, y compris si l'œuvre source est identique. Tokyo Ghoul et Tokyo Ghoul:re sont deux œuvres liées, non fusionnées. `Radiant` doit pouvoir exister sans ID MAL.

## Règles de fusion
- Fusion automatique : même identifiant externe explicite, même type de média, attribution non contradictoire, et provenance enregistrée ; dans les cas risqués, exiger une seconde preuve.
- Si collision de deux œuvres sur le même ID externe : quarantaine, **pas** de fusion.
- Titres FR : uniquement valeurs fournies explicitement en français par une source attribuable ; ne pas inventer une édition papier à partir d'un titre traduit.
- ISBN : concerne une publication d'une édition. Un ISBN revendiqué par deux œuvres ou éditions reste candidat ambigu et bloque la validation.
- Toute correction est rejouable, documentée, et précède une sauvegarde ; les snapshots bruts restent immuables.

## Données et confidentialité
Le catalogue est **public**. Les données `library` et `owned_item` sont **privées**. Ne jamais mélanger leurs exports. Les données personnelles existantes sont conservées sur les volumes originaux ; aucun test ne doit les toucher.

## Définition de « 95 % »
95 % = objectif de **précision des associations confirmées** sur un jeu de vérité de référence. Afficher séparément taux de couverture, rappel, taux de conflits et nombre d'éditions françaises réellement prouvées. La précision sur 50 cas triés par nous n'est pas un 95 % global représentatif ; compléter par un échantillon aléatoire stratifié avant de conclure.
