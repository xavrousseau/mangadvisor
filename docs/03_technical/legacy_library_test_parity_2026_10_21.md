# Réconciliation des anciens tests bibliothèque et du prototype Streamlit

> Audit du 21 octobre 2026 sur PR #89. Les cinq anciens scripts `pipelines/engine/scripts/run_library_*_tests.py` ont été relus depuis `main`, où ils restent accessibles dans l'historique. Ils exigeaient `--reset-library` et effaçaient l'état de la bibliothèque via HTTP : **ne jamais les réactiver sur une base personnelle**.

## Scénarios historiques : couverture actuelle

| Ancien lanceur | Scénarios identifiés | Traitement sécurisé |
|---|---|---|
| `run_library_import_robustness_tests.py` | Colonnes françaises séparées par `;`, notes décimales avec virgule, statut invalide, titre vide, doublon, import sur manga existant, favori booléen invalide | **8 tests hors ligne ajoutés** dans `tests/test_legacy_library_csv_contracts.py`. Connexion SQL simulée, aucune API/DB personnelle. |
| `run_library_import_tests.py` | Dry-run, import normal, XLSX transformé en CSV par Streamlit, œuvre non trouvée | Dry-run/œuvre inconnue vérifiés hors ligne. **XLSX et flux Web : écart à traiter**. |
| `run_library_status_tests.py` | `NOT_INTERESTED`, `DROPPED`, `WANT_TO_READ`, `OWNED`, note très faible ; exclusion des recommandations | Tests modernes de non-recommandation et de qualité déjà présents, **parité de tous ces profils réels à vérifier au niveau intégration**. |
| `run_library_goal_tests.py` | `SIMILAR_SAFE`, `READ_NEXT`, `SHORT_FINISHED` | Codes contrôlés par `test_recommendation_view.py` et suites de recommandations ; **résultats E2E des trois objectifs encore à recouper**. |
| `run_library_recommendation_tests.py` | Cinq profils (shōnen, thriller, seinen, contemplatif, mixte) | Tests actuels de sélection/qualité et parcours CI ; **pas de preuve de parité chiffrée profil par profil**. |

### Attention : évolution volontaire du contrat

L'ancien test « mise à jour d'un manga déjà présent » attendait l'écrasement des champs d'une ligne de bibliothèque. Le code actuel `/library/import/csv` est délibérément `ADD-ONLY` : `ON CONFLICT (user_id, manga_id) DO NOTHING`. **L'import n'a plus vocation à écraser notes, favoris ni progression existante.** Le nouveau test défend ce comportement, pas l'ancienne attente.

### Différence entre les trois imports

- `/library/import/csv` importe des **statuts de lecture** et des associations d'œuvres, sans déduire l'ISBN.
- `/inventory/*` traite les **déclarations de volumes physiques** et conserve les éditions distinctes.
- `/collection/import/*` importe **des livres ISBN identifiés** et leurs états de possession/lecture.
  
Ne pas fusionner ces parcours sous prétexte qu'ils s'appellent tous « import ».

## Ancien Streamlit vs interface Web

**Fonction de l'ancien prototype :** `apps/ui/app/app.py` accepte les fichiers `.csv` **et `.xlsx`** et convertit la première feuille Excel en CSV en mémoire avec `pandas.read_excel(..., engine="openpyxl")`. Il envoie ensuite les données vers l'ancien endpoint de bibliothèque `/library/import/csv`.

**Interface Web actuelle :** le sélecteur `#bulk-csv-file` dans `apps/web/assets/app.js` accepte uniquement `.csv` et le contenu est envoyé vers `/collection/import/preview` puis `/collection/import/apply`. Ce flux est un **import de livres ISBN**, pas un équivalent de l'import Excel de statuts de lecture.

**Décision :** ne pas supprimer `apps/ui/` en prétendant que toutes ses fonctions ont été migrées. Priorité à concevoir un import Web explicite de bibliothèque de lecture (CSV/XLSX), avec aperçu, résolution non ambiguë, protection contre l'écrasement et tests, ou à documenter clairement l'abandon approuvé de cette ancienne interface.

## Suite recommandée

1. Exécuter la CI du dernier commit et corriger tout nouveau test défaillant.
2. Ajouter des tests hors ligne sur les cinq exclusions de statuts et les trois objectifs.
3. Choisir ensuite une voie explicite pour l'import Excel de la bibliothèque avant toute suppression du prototype Streamlit.
4. Ne pas fusionner tant que ces réserves restent ouvertes ou ne sont pas volontairement acceptées.

## Migration Web en cours dans la PR #89

Le Web propose maintenant dans **Ma bibliothèque** un atelier distinct des livres ISBN pour importer les statuts de lecture par CSV ou XLSX. Le CSV utilise l'endpoint existant `/library/import/csv` ; le XLSX est converti par `/library/import/xlsx/convert` via `openpyxl` avant utilisation du même contrat. La conversion est bornée (512 Ko XLSX, 1 500 lignes, 32 colonnes) et ne modifie aucune table.

Le parcours comprend une simulation (`dry_run=true`), l'affichage des correspondances et erreurs, puis une confirmation explicite pour une importation **additive** (`ON CONFLICT DO NOTHING`). L'interface distingue ce parcours de l'import de livres ISBN vérifiés (`/collection/import/*`).

Des tests Python et Web couvrent les principaux contrats de conversion, d'aperçu et de non-écrasement. Des tests additionnels vérifient la présence des trois objectifs de recommandation et les exclusions des deux statuts négatifs. Il reste à valider les interactions réelles en navigateur et les quatre workflows du dernier HEAD, avant d'affirmer une parité parfaite avec Streamlit. L'ancien prototype n'est donc pas supprimé.

## Passage de parité Streamlit → Web — octobre 2026

- Modèles CSV et XLSX de bibliothèque générés sans Streamlit par le nouvel endpoint `GET /library/import/template?format=csv|xlsx`. Les modèles contiennent uniquement des exemples publics (Naruto, Bleach, One Piece, Fairy Tail).
- Profil de lecture rendu dans `Ma bibliothèque` via `/library/profile`, sans mutation : statuts, compteurs, tags pondérés, sources influentes et signaux négatifs. La présentation Web est dans `apps/web/assets/reading-profile.js`.
- Nouveaux tests `tests/test_library_templates.py` et `tests/web/reading-profile.test.mjs` ; le smoke Playwright charge aussi le profil et vérifie les modèles via API.
- **Décision prudente :** ne pas retirer encore `apps/ui/` : la parité des fonctionnalités de lecture et de recommandations, les tests `tests/test_discovery.py` et `tests/test_recommendation_view.py` qui en importent des utilitaires, ainsi que la dernière CI restent à clôturer. Les anciennes dépendances et l'overlay dev sont donc conservés tant que le retrait complet ne peut pas être validé en un lot.

## Clôture de la migration Streamlit (lot suivant)

Le prototype Streamlit (`apps/ui/`), son `requirements.txt`, le Dockerfile `infra/docker/ui/Dockerfile` et la définition `ui` du Compose développement ont été **retirés de la branche PR #89** après migration des écrans utiles : découverte et fiches via Web, recommandations et conseiller via Web, import lecture CSV/XLSX, modèles et profil de lecture. La version utilisateur stable n'emploie que le site Web.

Les tests de présentation propres à Streamlit ont été retirés ; les tests API catalogue, JavaScript Web, recommandations et parcours navigateur restent. La CI ne construit plus l'image `ui`. La mise à jour Windows conserve une opération de nettoyage du conteneur nommé `mangadvisor_ui` via `docker rm -f`, **sans option `-v` et sans suppression des volumes de données**.

La première passe CI a détecté une dépendance de collecte `requests` installée auparavant indirectement par les dépendances UI et des assertions liées au profil `legacy`. Les dépendances de collecte ont été ajoutées explicitement à la CI et les assertions ont été mises à jour. **La réussite des quatre workflows du dernier HEAD est nécessaire avant de valider définitivement ce retrait**.
