# Audit — fichiers racine, outils et documentation (21 octobre 2026)

> Revue statique sur la branche de nettoyage PR #89. Aucune donnée personnelle ou volume Docker modifié.

## Fichiers racine et outils

| Chemin | Fonction vérifiée | Décision |
|---|---|---|
| `mangadvisor.cmd` | Menu Windows principal, point d'entrée utilisateur unique | Conserver |
| `README.md` | Installation, mises à jour, sauvegardes et guide utilisateur | Conserver et aligner sur les options actuelles |
| `.env.example` | Modèle de variables locales, sans vrai secret | Conserver ; seul `.env` privé doit contenir des secrets |
| `.gitignore` | Empêche le suivi des bases privées, sauvegardes et exports personnels | Conserver |
| `.dockerignore` | **Ajouté** : empêche l'inclusion de données privées et archives dans le contexte Docker build | Conserver, protéger par test |
| `tools/audit_repository.py` | Inventaire Git et analyse statique (syntaxe, imports Web, contrats de sécurité/Compose) | Conserver ; la couverture de certains liens documentaires reste informative plutôt que bloquante |

## Décisions documentaires

- **Guides actifs** : README, procédures de sauvegarde/restauration, imports physiques, catalogue MAL, catalogue vivant, aide à la résolution des ISBN et des titres. Garder accessibles, éviter les multiples vérités contradictoires.
- **Guides V1** (architecture, pipelines, modèle de données) : déjà annoncés comme archives conceptuelles. Ne pas les traiter comme les instructions de lancement actuelles.
- **Ancien guide `control_center_4_0.md`** : numérotation historique incompatible avec le menu actuel ; avertissement explicite ajouté.
- **Benchmarks** : ancien guide V1 maintenant identifié comme historique ; A→16 et A→17 utilisent tous deux V2 dans le menu courant. Guides alignés.
- **Rapports d'audit datés** : témoignent de l'état du dépôt à une date/commit donnés. Ne pas les réécrire comme si leurs résultats étaient encore actuels ; éviter leur duplication dans le README.

## Changements réalisés

1. Nouveau `.dockerignore` : exclusion du `.git`, des fichiers `.env` réels, `private-data/`, `backups/`, `private-evaluations/`, des données brutes/logs/exports et d'anciens dossiers. Le code `apps/` et `pipelines/` reste disponible aux Dockerfiles. **La protection s'applique au contexte des nouveaux builds** ; elle ne supprime aucun volume et ne remplace pas la sauvegarde PostgreSQL.
2. Nouveau test de contrat dans `tests/test_repository_hygiene.py` : interdiction de supprimer par accident les principales exclusions privées Docker.
3. README et guides des benchmarks mis à jour pour le fonctionnement V2 réel.
4. Le guide historique `control_center_4_0.md` pointe explicitement vers le README et le menu actifs.

## Travaux qui restent pour déclarer l'audit intégral

- Reconcilier les **fichiers effectivement suivis dans le HEAD** avec les inventaires datés : des fichiers ont été ajoutés depuis le rapport 4.4, tandis que six scripts anciens ont été supprimés.
- Vérifier tous les liens documentaires et les exemples de commandes. Les fichiers marqués « historiques » peuvent contenir des chemins anciens par conception.
- Comparer les responsabilités du prototype Streamlit et du Web puis migrer ses tests avant une éventuelle suppression.
- Vérifier la non-régression des derniers commits, y compris le contexte Docker réduit, dans les quatre workflows.
- Confirmer la couverture exhaustive des scénarios des cinq scripts de bibliothèque retirés : ce point reste ouvert.

## Sécurité

Ne pas exécuter de tests manipulant les données sur la base personnelle. Préserver les backups `backups/`, `private-data/`, les fichiers `.env`, les sources `data/raw/` et les volumes Docker. La PR doit rester en brouillon jusqu'à validation de la CI et de la couverture.
