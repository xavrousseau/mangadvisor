# Audit de nettoyage — sql/ et tests/ (21 octobre 2026)

> Revue statique et corrections sur la branche de travail PR #89. Les tests SQL de reconstruction s'exécutent sur la base CI jetable `mangadvisor_ci`, jamais sur la mangathèque personnelle.

## Inventaire SQL — décisions

| Fichier | Utilité réelle | Décision |
|---|---|---|
| `sql/schema/001_jikan_source_tables.sql` | Source Jikan/Tenrai structurée, JSON source et index | Conserver |
| `sql/schema/002_canonical_manga_tables.sql` | Identifiants `manga.id`, genres et liens | Conserver |
| `sql/schema/003_build_canonical_from_jikan.sql` | Actualisation additive de l'œuvre et des genres | **Corrigé** : titres vides écartés, noms existants préservés |
| `sql/schema/004_add_theme_demographic_tables.sql` | Tables et liens des thèmes/démographies | Conserver |
| `sql/schema/005_build_theme_demographic_from_jikan.sql` | Actualisation additive des thèmes/démographies | Conserver |
| `sql/schema/006_add_jikan_recommendation_tables.sql` | Relations de recommandations de la communauté | Conserver |
| `sql/schema/007_add_user_library_tables.sql` | Bibliothèque privée, relations et horodatage | Conserver |
| `sql/queries/check_jikan_data_quality.sql` | Diagnostic qualité des données source | Conserver comme outil de contrôle |
| `sql/queries/check_jikan_source_data.sql` | Inspection de l'import Jikan | Conserver, comparer les deux diagnostics à la revue documentaire |
| `sql/queries/inspect_jikan_attributes.sql` | Inspection des attributs JSON | Conserver |

### Résultats importants

1. La reconstruction canonique ne fait plus de `TRUNCATE`, ne reconstruit plus `manga.id` et utilise `ON CONFLICT`, ce qui protège normalement les clés des œuvres, les associations personnelles et les éditions.
2. **Risque confirmé et corrigé** : une source avec `title = ''` était auparavant insérée ou écrasait le titre canonique. Le script 003 écarte maintenant les titres blancs et protège les titres anglais/japonais lorsqu'ils arrivent vides.
3. Les liens genre, thème et démographie sont **additifs** : les tags disparus de la source ne sont pas supprimés automatiquement. Ce choix protège la provenance mais peut laisser des tags périmés ; correction future après traçabilité des origines, pas par suppression générale.
4. Les contraintes SQL possèdent parfois `ON DELETE CASCADE`, ce qui est normal pour certaines clés étrangères mais rend toute suppression de `manga` potentiellement très risquée. Les procédures de synchronisation ne doivent jamais supprimer les œuvres en masse.

## Inventaire des tests — familles et responsabilités

| Famille | Scénarios couverts | Décision |
|---|---|---|
| `tests/test_*.py` | Validation Python : catalogue, recommandations, sécurité d'import, bibliothèque, traduction, sources | Conserver |
| `tests/web/*.test.mjs` | Composants UI et règles d'affichage JS, y compris la navigation vers les fiches | Conserver |
| `tests/smoke/*.py` et `tests/smoke/*.sql` | Parcours E2E Docker et base synthétique | Conserver sous contrôle CI |
| `tests/integration/*` | Chargement initial, services et comportement de bout en bout | Conserver |
| `tests/windows/*` | Orchestration PowerShell Windows | Conserver |
| `.github/workflows/*` | Exécution automatisée et preuve de régression | Conserver |

### Corrections de ce lot

- `tests/smoke/rebuild_safety_smoke.py` : suppression du bloc conditionnel dupliqué ; deux passes SQL additives conservent le contrôle d'idempotence.
- Le scénario SQL CI vérifie maintenant également que les titres canoniques résistent à un enregistrement source avec titres vides, en plus des identifiants `manga.id`, de la bibliothèque, des ISBN et du suivi de lecture.
- Les cinq anciens scripts de tests bibliothèque `--reset-library` ont été retirés dans les lots précédents, mais leur couverture exhaustive n'est **pas** encore certifiée équivalente aux tests modernes. C'est une réserve de fusion.

## À contrôler avant fusion

- Statut des quatre workflows sur le dernier HEAD PR #89.
- Vérifier les scénarios de restauration sur base strictement jetable.
- Comparer les requêtes de diagnostic Jikan et supprimer les doublons seulement si leurs sorties et consommateurs sont équivalents.
- Éviter de confondre les données déclarées de mangathèque et les éditions ISBN vérifiées, y compris dans les tests de bout en bout.
- Contrôler les contrats historiques de suppression des œuvres lors de la prochaine passe `apps/api/`, et non par changement de contrainte SQL non migré.

**Bilan :** les sept scripts de schéma recensés ont une utilité ; aucune suppression de `sql/schema/` justifiée à ce stade.
