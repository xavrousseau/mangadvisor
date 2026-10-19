# Nettoyage 4.1 — rapport de traçabilité

## Périmètre

Audit de l'arbre Git **main** du 19 octobre 2026 avant nettoyage : **331 fichiers suivis** environ (nombre définitif tiré de l'arbre au moment du commit), dont **99 fichiers purement historiques** répartis entre :

- _archive/v0_8_13_cleanup : 56 fichiers (copies de .py, patchs V0.8, rapports obsolètes) ;
- legacy/full_stack_2026_03 : 43 fichiers (ancien prototype Docker, vieux modules, carnets Jupyter volumineux).

Ces deux dossiers représentaient ensemble **environ 13,95 Mio** de fichiers historiques non exploités par le runtime actuel. Les supprimer de la branche active n'efface **pas leur historique Git**. Les objets historiques existants ne deviennent pas immédiatement plus petits dans un clone déjà constitué : il s'agit avant tout de simplifier le checkout et les nouveaux téléchargements.

## Suppressions ciblées

| Catégorie | Traitement | Justification |
|---|---|---|
| _archive/** et legacy/** | Retrait de la branche active | Anciennes versions non utilisées au démarrage ni par CI ; reconstructibles depuis Git |
| cmd/archive-v0-8-temp-files.cmd | Retrait | Récréait le dossier _archive/ devenu inutile |
| cmd/audit-project-files.cmd | Retrait | Outil V0.8.13 écrivant un rapport daté et obsolète |
| cmd/run-jikan-catalog.cmd | Retrait | Ancienne ingestion, Python hôte, remplacée par option 25 |
| cmd/extract-jikan-recommendations.cmd | Retrait | Nécessitait Python local ; doublon de l'option 26 |
| cmd/load-jikan-recommendations.cmd | Retrait | Doublon option 26, proposait une remise à zéro non nécessaire |
| cmd/rebuild-canonical-catalog.cmd | Retrait | Redondant : l'option 25 fait déjà le chargement et la reconstruction sécurisée |
| cmd/diagnose-jikan-recommendations.cmd | Retrait | Ancien lanceur Python local ; analyse Python conservée pour les diagnostics avancés |
| cmd/run-jikan-pipeline.cmd | Retrait | Ancien lanceur du sous-menu 12 ; remplacé par l'option 25 |
| pipelines/engine/src/extract/jikan_client.py | Retrait | Client isolé encore câblé sur api.jikan.moe, arrêté, sans appel de production |
| docs/reports/recommendation_profile_tests_v0_7_4.md | Retrait | Copie **identique** de recommendation_profile_tests_latest.md |
| docs/reports/project_file_audit_v0_8_13.txt | Retrait | Rapport figé sur une arborescence 0.8, erronée aujourd'hui |

Les scripts Python de tests de profil, les schémas SQL, les composants Web, Streamlit et API sont conservés. Un seul rapport actualisable recommendation_profile_tests_latest.md est désormais produit.

## Menus unifiés

- **25** devient le seul parcours visible d'ingestion du catalogue (Tenrai).
- Le menu **12** historique devient un alias discret redirigeant vers 25, sans proposer de réinitialiser les données.
- La commande directe mangadvisor.cmd catalogue a été réparée ; mangadvisor.cmd jikan est un alias de compatibilité.
- Les sous-commandes obsolètes jikan-reset et jikan-pages renvoient un message clair et n'exécutent aucun traitement destructeur.
- Aucun numéro des fonctions essentielles (17 sauvegarde, 21 import, 22 installation, 25 catalogue, 26 recommandations) ne change.

## Ce qui reste volontairement

- Le code Web principal et Streamlit coexistent par choix : l'UI historique est encore testée.
- Les scripts run_library_*_tests.py sont utilisés pour la validation métier et ont donc été conservés.
- Les anciens rapports **non identiques** servent de preuves historiques, mais ne constituent pas la documentation courante.
- La documentation V1 est conservée en tant qu'archive de conception, avec avertissement visible.
- Les scripts sources nommés jikan pour compatibilité SQL restent actifs **mais appellent Tenrai** ; un renommage immédiat pourrait casser les intégrations et chemins.

## Garde-fous

1. Tout retrait se fait dans une branche dédiée ; pas de suppression directe sur main.
2. Aucune modification des volumes PostgreSQL, Meilisearch, Ollama, de .env, private-data/, backups/ ou mobile-local/.
3. CI Python, vérification Windows et intégration Docker doivent réussir avant intégration.
4. Une actualisation locale via Git ne devrait toucher que les fichiers suivis. En présence de modifications locales, utiliser les mécanismes de sauvegarde et comparer avant une mise à jour.
5. Les fichiers supprimés restent accessibles dans l'historique via git log et git show sans recréer les anciens répertoires dans la version active.

## Améliorations futures (séparées du présent nettoyage)

La division des très gros fichiers FastAPI/JS et le retrait éventuel de Streamlit demandent une évolution fonctionnelle dédiée. Aucun code applicatif critique n'est supprimé dans cette opération d'hygiène.
