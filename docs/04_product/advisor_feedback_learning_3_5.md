# Mangadvisor 3.5 — Apprendre des retours de lecture, sans surinterpréter

## Objectif

Les actions **Ça m'intéresse**, **Déjà lu** et **Pas pour moi** étaient déjà enregistrées dans \`user_manga_library\`. Les œuvres rejetées étaient déjà exclues des recommandations, mais **Mon conseiller** exploitait mal les envies \`WANT_TO_READ\` et n'utilisait pas les refus *répétés* comme indices légers pour départager des mangas par ailleurs conformes.

Cette évolution améliore **le moteur conversationnel** (\`/advisor/message\` et \`/advisor/ai-message\`). Les autres moteurs de recommandations conservent leurs comportements antérieurs et notamment leur exclusion systématique des mangas déjà rejetés.

## Signaux autorisés

| Statut personnel existant | Interprétation | Effet |
| --- | --- | --- |
| Favori / bien noté / lu ou en cours sans note | Préférence fondée sur la bibliothèque | Bonus d'affinité déjà présent, inchangé |
| \`WANT_TO_READ\` (« Ça m'intéresse » ou intention manuelle) | Curiosité, **pas une lecture réellement aimée** | Petit bonus : +3 points par tag commun, plafonné à +6 |
| \`NOT_INTERESTED\` pour **un seul manga** | Rejet **de ce titre uniquement** | Titre exclu de SQL ; **aucune** sanction globale de son genre |
| Au moins **deux mangas distincts** refusés partageant un même genre/thème | Indice prudent d'une éventuelle réticence | -6 points par tag partagé, plafonné à -12, **seulement** sans signal positif fort ni envie de lecture positive sur ce tag |
| \`DROPPED\`, \`OWNED\` sans autre preuve | Interprétation ambiguë | Aucune déduction négative nouvelle |

Les genres et thèmes proviennent **exclusivement** des associations du catalogue actuel ; rien n'est deviné depuis des synopsis ou depuis le modèle IA. Les liens de même tag sur des mangas distincts sont comptés par \`COUNT(DISTINCT manga_id)\`.

La pénalité n'est **jamais un filtre d'exclusion de genre**. Une recommandation conforme peut toujours être affichée si elle correspond à une demande explicite. Le moteur continue à préserver en amont les filtres obligatoires (édition française/ISBN, format, statut, longueur, horreur/gore/romance lorsqu'ils sont étiquetés) et exclut les **titres** déjà enregistrés dans la bibliothèque.

Les anciennes notes, favoris, statuts possédé/lu, ISBN et commentaires ne sont jamais modifiés. **Aucune table supplémentaire**, aucun entraînement d'IA, aucune API payante ou synchronisation externe.

## Dans l'interface

Sous les cartes du conseiller, des preuves supplémentaires peuvent apparaître :
- **« Tags présents dans des mangas que tu veux lire »** : raison positive légère (source \`WANT_TO_READ\`).
- **« Tags partagés avec plusieurs titres refusés »** : indication de la pénalité faible et réversible, si au moins deux rejets distincts sont documentés.

Le panneau existant **« Comment cette sélection est-elle construite ? »** indique désormais le nombre de genres/thèmes documentés associés à des envies de lecture et à plusieurs refus. Ces nombres sont **des comptes de tags**, pas le nombre de mangas appréciés, ni un taux de satisfaction ni une « probabilité de correspondance ».

Le mode **« Surprends-moi selon mes goûts »** peut désormais démarrer avec des tags documentés d'œuvres marquées \`WANT_TO_READ\`, même si aucun favori/lu n'est encore renseigné. Il distingue cet intérêt d'une préférence confirmée ; les titres suivis ne sont jamais proposés une nouvelle fois.

Si la personnalisation est désactivée, les signaux de retours ne sont pas consultés ni utilisés pour classer.

## Contrôle et réversibilité

L'utilisateur peut modifier une intention \`WANT_TO_READ\` ou \`NOT_INTERESTED\` depuis la mangathèque : le classement est recalculé depuis le **statut actuel**, pas depuis une mémoire secrète ou une ancienne étiquette historique. La modification des retours conserve les protections déjà en place sur les statuts de lecture et de possession.

Les poids sont **des heuristiques fixes**, pas une mesure scientifique de tes goûts. Les tags communautaires peuvent être incomplets, et refuser plusieurs œuvres avec un genre commun ne veut pas dire refuser ce genre en lui-même.

## Tests

- Tests unitaires : un refus isolé ne retire pas des genres entiers ; deux refus distincts appliquent une pénalité légère ; un intérêt ou une préférence déjà appréciée empêche la pénalité sur le même tag ; dédoublonnage, sûreté et déterminisme.
- Tests PostgreSQL jetable : réaction \`INTERESTED\` enregistrée, preuve d'un effet dans le conseiller, refus réitérés dans la bibliothèque, ré-exécution des recommandations et absence des ISBN/titres refusés ; les anciens compteurs de tomes restent inchangés.
- Tests JS : étiquettes de preuve, provenance des compteurs et échappement HTML des noms de tags.
- Tous les tests existants Python/JS/PostgreSQL/navigateur PC/mobile/HTTPS/sauvegarde restent requis pour intégrer la version.

## Mise à jour

Avant la mise à jour, réaliser une sauvegarde avec \`mangadvisor.cmd\` option **17**. Puis \`git pull origin main\`, redémarrer via l'option **3**, ouvrir **http://localhost:8501 → Pour moi → Mon conseiller** et essayer le bouton **Surprends-moi**. Après quelques réactions « Ça m'intéresse » et « Pas pour moi », lancer une nouvelle recherche et consulter le bilan de la sélection.

La prochaine étape devra confronter ces pondérations aux retours réels de la collection personnelle et les ajuster, sans apprendre automatiquement des catégories intimes ni créer un profil opaque.
