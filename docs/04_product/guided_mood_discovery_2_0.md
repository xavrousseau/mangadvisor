# Mangadvisor 2.0 — découverte selon ton envie

## Parcours

Dans Pour moi, sélectionner **Selon mon envie**. Le parcours propose six ambiances : sombre, doux, action, mystère, romance et fantasy ; des filtres pour série courte (1–12 tomes), longue (13 tomes ou plus), terminée, note communautaire minimale et personnalisation depuis la bibliothèque.

Le moteur interroge uniquement des genres et thèmes effectivement référencés dans le catalogue, et exige au moins une correspondance avec l'ambiance. La longueur, lorsqu'elle est spécifiée, exclut les séries dont le nombre de tomes n'est pas connu. Les mangas déjà dans la bibliothèque, y compris ceux rejetés, ne sont jamais candidats.

Si activée, la personnalisation utilise uniquement les attributs des mangas appréciés : favoris, notes d'au moins 7, ou statuts lu/en cours sans note. L'interface distingue clairement une sélection personnalisée d'une sélection générale du catalogue lorsque les préférences manquent.

Le classement fait intervenir l'adéquation aux tags, les affinités documentées et la note communautaire ; il ne représente pas une probabilité de compatibilité et ne remplace pas le score de similarité du moteur historique. Les cartes affichent des genres et thèmes réellement trouvés. Chaque suggestion propose les boutons « Ça m'intéresse », « Déjà lu » et « Pas pour moi », ainsi que sa fiche.

## Limites honnêtes

- La disponibilité française et les éditions publiées en France ne sont pas garanties dans ce premier filtre. Examiner les fiches françaises existantes.
- Une ambiance n'est pas une classification de sécurité ou une garantie d'adéquation à un âge.
- La sélection est réalisée sur un maximum de 500 candidats présélectionnés en base par score et popularité, puis classés plus finement. Cela favorise les titres documentés et peut manquer des titres de niche.
- Les ambiances reflètent seulement la richesse des métadonnées du catalogue. Aucun titre ni goût ne sont inventés.
- L'API POST /discovery/mood est entièrement en lecture seule, sans modification de schéma ni des moteurs historiques.
- Les deux modes historiques restent accessibles en onglets.

## Vérifications

Tests unitaires Python et JavaScript, tests PostgreSQL sur base jetable, test navigateur Chromium avec écrans ordinateur/mobile, validation des exclusions et des filtres, conservation des actions sur les cartes.

## Mise à jour locale

Récupérer avec git pull origin main, puis Docker Desktop et mangadvisor.cmd, option **3 — Build + démarrage**. Ouvrir Pour moi. Ne pas nettoyer les volumes Docker.
