# Mangadvisor 3.0 — Conseiller à compréhension IA locale (facultatif)

## Pourquoi

Mangadvisor propose déjà des recommandations provenant des vraies données PostgreSQL (catalogue, genres, thèmes, historique et ISBN français). Son conseiller initial interprète des expressions guidées. Cette version **ajoute un véritable modèle de langage local** pour comprendre plus librement les demandes, sans sacrifier la traçabilité.

**Distinction importante :** il s'agit d'un assistant de recommandation enrichi par un LLM, **pas encore d'un agent autonome généraliste** capable d'organiser des achats, de surveiller seul des nouveautés ou de modifier la bibliothèque.

## Fonctionnement

1. L'utilisateur écrit sa demande dans **Pour moi → Mon conseiller**.
2. Si Ollama a été explicitement activé, le modèle **qwen2.5:3b** installé localement retourne **uniquement un JSON de critères** (ambiance, longueur, langue, édition, exclusions et indices narratifs). Il ne reçoit aucune ligne de bibliothèque, aucune notice ISBN ni contenu SQL.
3. Le serveur **valide strictement** les critères avec AdvisorContext (clés et valeurs autorisées). Il conserve les critères antérieurs sauf modification explicite et permet de demander d'autres résultats.
4. Le **même moteur SQL** qu'avant retrouve les mangas réellement connus, exclut les mangas personnels et ceux marqués indésirables, et conserve des justifications issues des tags et notices réelles.
5. La réponse est formulée par le moteur vérifiable ; l'IA ne génère **aucun manga, tome français, ISBN, stock, prix ou score de compatibilité fictif**.

Le modèle n'est ni une condition de démarrage ni un service payant. Si Ollama est désactivé, indisponible ou retourne un JSON invalide, /advisor/ai-message réutilise **le conseiller guidé**. L'interface affiche clairement « IA locale active », « Mode guidé » ou « IA locale indisponible ». Aucun résultat n'est inventé en mode repli.

## Installation Windows — à faire une seule fois

Sur le PC, avec Docker Desktop démarré :

1. Mettre à jour le dépôt : git pull origin main
2. Exécuter mangadvisor.cmd, **option 3** pour reconstruire et démarrer l'application.
3. Exécuter mangadvisor.cmd, **option 15 — Installer et activer le conseiller IA local**. Confirmer le téléchargement du modèle. Il peut demander plusieurs gigaoctets de disque et une RAM suffisante. Le registre public Ollama n'est utilisé **que pour télécharger le modèle**.
4. Ouvrir http://localhost:8501 → **Pour moi → Mon conseiller**. Le bandeau indique le mode réel.

Pour arrêter le modèle sans toucher aux mangas, utiliser **option 16**. Le modèle téléchargé reste dans un volume Docker distinct. Le mode guidé demeure disponible. Ne pas modifier les volumes PostgreSQL ou Meilisearch.

La première réponse sur un PC sans GPU peut être lente. En cas de panne ou de délai excessif, l'application bascule vers le conseiller guidé. L'IA locale est accessible uniquement depuis le réseau Docker Mangadvisor : le port 11434 du modèle n'est **pas publié sur Internet ni sur le réseau local**.

## Sécurité des données

- Opt-in explicite : OLLAMA_ENABLED=true. Le script option 15 ne remplace pas les autres variables du fichier .env.
- L'endpoint du modèle est fixé par la configuration du serveur et jamais par le navigateur.
- Les messages envoyés au modèle contiennent uniquement le message courant et les critères antérieurs, pas le contenu de la collection ou les secrets Docker.
- Le retour du modèle est strictement limité à des clés de AdvisorContext ; ni SQL, ni ID manga, ni URL ne peuvent servir d'ordre.
- Pas de journalisation des messages, pas d'historique conservé côté serveur et pas de modification du suivi de volumes.
- Les exclusions horreur/gore/romance ne couvrent que les tags enregistrés : l'absence de tag n'est **pas** une garantie de sécurité.
- Une notice française enregistrée ne prouve ni stock commercial ni exhaustivité de l'édition.

## Limites et validation

Le modèle local peut mal comprendre une nuance ou un changement d'avis : les critères reconnus sont affichés et peuvent être corrigés. L'absence de modèle ne bloque pas les recommandations.

Tests automatisés : validation des filtres et rejet de sorties malveillantes, dialogue multi-tours, modèle désactivé, modèle simulé, mode visible, API PostgreSQL jetable en mode guidé, navigateur PC/mobile, sécurité des ISBN existante.

**Non testé dans GitHub Actions** : l'inférence réelle de qwen2.5:3b sur un PC Windows donné (RAM/CPU/GPU), le premier téléchargement du modèle et son comportement selon la disponibilité réseau. À confirmer localement après installation.

## Étape suivante

Un véritable **agent IA autonome** nécessitera des outils autorisés, une gestion des permissions, un historique fiable, une validation humaine avant toute action, des sources françaises plus complètes et des tests supplémentaires. Cette version fournit la première brique IA réelle sans mettre la bibliothèque en danger.
