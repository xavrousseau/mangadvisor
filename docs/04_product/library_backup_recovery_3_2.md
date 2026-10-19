# Mangadvisor 3.2 — Sauvegarder et récupérer sa mangathèque

## Ce que protège cette sauvegarde

Le menu **17 — Sauvegarder et vérifier** crée un export PostgreSQL **complet** de la base utilisée par Mangadvisor : catalogue canonique, goûts, mangas suivis, éditions françaises, ISBN, tomes possédés/lus, réactions aux recommandations, données sources Jikan et autres tables présentes. Les états ne sont ni remplacés ni modifiés par la sauvegarde.

Ce n'est **pas** une simple copie d'un CSV, ni une copie du volume Docker, ni un dump texte. PostgreSQL utilise `pg_dump -Fc` avec compression et instantané transactionnel cohérent.

L'outil se base sur les paramètres **POSTGRES_DB / POSTGRES_USER présents dans le conteneur Docker** : aucun identifiant n'est codé en dur, et la sauvegarde ne requiert pas l'installation de PostgreSQL ou de Python sur Windows.

## Depuis mangadvisor.cmd

Avec **Docker Desktop démarré** et la stack Mangadvisor initialisée :

- **Option 17 — Sauvegarder et vérifier** : création de `backups/mangadvisor_YYYYMMDD_HHMMSS_XXXXXXXX.dump` et de son manifeste `.dump.json` contenant la date, la taille, la base d'origine et son empreinte SHA-256 ; copie binaire grâce à `docker cp` (pas de corruption par redirection Windows PowerShell) ; restauration **réelle** du dump dans une base isolée temporaire et contrôle des tables / compteurs catalogue, bibliothèque, ISBN et tomes ; destruction de la **seule** base de test.
- **Option 18 — Vérifier la dernière sauvegarde** : vérifie l'empreinte SHA-256 et recommence une restauration isolée complète. On peut aussi préciser une archive avec `powershell -File cmd/library-backup.ps1 -Action Verify -File "C:\...\backups\mangadvisor_...dump"`.
- **Option 19 — Restaurer** : action **volontaire**, jamais déclenchée au démarrage. Demande de saisir exactement `RESTAURER <nom_de_base>`, sauvegarde **et vérifie d'abord la base active**, restaure la sauvegarde sélectionnée dans une nouvelle base, arrête temporairement les services applicatifs puis **renomme l'ancienne base** au lieu de la supprimer. En cas d'échec avant le basculement final, le script tente de rétablir l'ancien nom. Le script redémarre l'API et les interfaces. L'ancienne base existe encore sous un nom `ma_before_XXXXXXXX` : ne pas l'effacer sans avoir contrôlé le résultat.

Les opérations 18 et 19 choisissent la sauvegarde la plus récente dans `backups/` si aucun fichier n'est précisé. Une archive venant d'une autre base, sortie de ce dossier, sans manifeste ou modifiée est refusée. **La restauration de production est refusée en mode non interactif** ; le seul contournement est réservé à la base synthétique `mangadvisor_ci` sous GitHub Actions.

## Précautions indispensables

1. Après la première sauvegarde, **copier les deux fichiers** (`.dump` et `.dump.json`) sur un support différent du disque du PC (disque USB fiable, espace privé chiffré…). **Un fichier placé sur le même disque ne protège pas d'une panne de ce disque.**
2. Protéger ces archives comme des documents personnels : elles contiennent ta bibliothèque et peuvent contenir des notes. Le dossier `backups/` est ignoré par Git : **ne jamais le pousser sur GitHub ni le partager**.
3. Refaire une sauvegarde avant toute grosse mise à jour, réinitialisation du catalogue ou import massif, puis régulièrement (par exemple une fois par semaine et après les ajouts importants). Il n'existe **aucune programmation de sauvegarde automatique** dans cette version.
4. La restauration demande de l'espace disque pour accueillir simultanément la base courante, la base restaurée et la copie de sécurité. Vérifier l'espace Docker avant d'utiliser l'option 19.
5. **Ne pas utiliser le menu Nuke** en supposant que le dump se trouve dans Docker : les archives sont sur le disque Windows dans `backups/`, mais la reprise dépend de PostgreSQL disponible et de l'installation des schémas/extension présents dans l'image.
6. Les fichiers `.env`, `.env.mobile`, mots de passe de connexion, configuration Caddy et modèles Ollama ne sont **pas inclus** dans le dump PostgreSQL. Les conserver séparément en lieu sûr. Le volume Meilisearch (index reconstituable) et le volume Ollama (modèle téléchargeable) ne sont pas exportés ici.
7. L'option 19 remplace le **catalogue entier** ainsi que les données utilisateur par l'état de l'archive choisie. Ce n'est pas un fusionneur d'ajouts récents : conserver les sauvegardes récentes et vérifier la date avant confirmation.

## Ce que valident les tests GitHub

Le workflow intégré réutilise **ce même script PowerShell**, sur une base PostgreSQL artificielle jetable seulement :

1. Export réel avec `pg_dump` + manifeste SHA-256.
2. Import réel avec `pg_restore --single-transaction --exit-on-error` dans une base temporaire et interrogation des tables importantes.
3. Refus explicite d'une copie du dump volontairement altérée, même si elle possède un manifeste.
4. Basculement de restauration contrôlé en environnement **CI uniquement**, conservation de l'ancienne base et relecture des suivis utilisateur et ISBN après redémarrage.

Le test n'ouvre **jamais** ta base personnelle. Les performances de sauvegarde et de restauration dépendent cependant de la taille de ton catalogue, de l'espace disque et des ressources du PC ; elles doivent être vérifiées une fois localement.

## Règle de sécurité

**Pas de suppression de collection pour tester une restauration.** Les tests ont leur propre base PostgreSQL et la restauration réelle conserve l'ancienne base au lieu de la détruire. La restauration n'est jamais lancée automatiquement.

## Suite du projet

Une fois le premier fichier de sauvegarde créé et testé sur ton PC : reprendre l'optimisation des recommandations (qualité, personnalisation, diversité) et la compréhension du conseiller IA local (multi-tour, vrais motifs du catalogue, refus des hypothèses non sourcées).
