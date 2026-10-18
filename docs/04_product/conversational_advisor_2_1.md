# Mangadvisor — conseiller manga conversationnel 2.1

## Utilisation

Ouvrir Pour moi > **Mon conseiller** dans l'application (ordinateur ou smartphone). Décrire une envie en langage courant, par exemple :

> Je veux un manga sombre avec une intrigue prenante, pas trop long, terminé, idéalement en français.

L'application extrait et **affiche les critères qu'elle a effectivement reconnus** : atmosphère, longueur, statut de publication, présence d'un ISBN français enregistré (obligatoire ou souhaitée), usage de la bibliothèque et exclusion explicite de la romance. On peut ensuite préciser :

> Finalement plutôt long.
> Uniquement en français.
> Sans romance.
> Montre-m'en d'autres.

Les critères non modifiés sont conservés durant la conversation, sur le navigateur courant uniquement. Le bouton **Nouvelle conversation** repart de zéro. La conversation n'est **pas** stockée en base.

## Fonctionnement réel et limites

Il ne s'agit **pas encore d'un modèle génératif généraliste**. Cette première version utilise une compréhension guidée de phrases françaises/anglaises, un jeu documenté d'intentions et des recherches SQL paramétrées, sans appel externe à une API payante. Si le conseiller ne reconnaît aucune nouvelle contrainte, il demande une reformulation. Une mention « mature » ne crée pas un filtre d'âge inexistant ; l'application en signale explicitement la limite.

Les résultats sont issus uniquement du catalogue canonique : correspondances exactes avec des genres/thèmes présents en base, affinités avec les notes/favoris réellement enregistrés, note communautaire et édition française enregistrée. Un utilisateur doit disposer d'au moins une ambiance identifiable pour lancer une recherche : autrement, le conseiller demande une précision.

Le filtre français respecte la nuance entre « idéalement » (bonus au classement, sans exclusion) et « obligatoire » (ne conserver que les séries ayant au moins une notice manga_fr_edition déjà enregistrée). Cette table contient des ISBN provenant des notices BnF et d'associations explicitement confirmées ; elle ne prouve **ni qu'une série entière soit publiée en France ni qu'un tome soit actuellement disponible à la vente**.

Les mangas présents dans l'ancienne bibliothèque ou déjà possédés/lus via le suivi français sont exclus. Les séries sans nombre de tomes connu sont exclues lorsque la longueur est imposée. Un « manga terminé » est défini par la valeur Finished du catalogue, pas par une édition française entièrement parue.

Le moteur utilise un maximum de 500 candidats préfiltrés en SQL, puis un classement déterministe documenté. Il ne produit pas de pourcentage magique de compatibilité et ne classifie pas l'âge des lecteurs.

## Confidentialité et préservation des données

- POST /advisor/message est **en lecture seule** ; paramètres et longueur du texte validés.
- Aucun historique de chat sauvegardé, aucune nouvelle table, aucun import de collection, aucune migration destructive.
- Les actions explicites « Ça m'intéresse », « Déjà lu » et « Pas pour moi » utilisent le mécanisme de retour déjà existant, et ce sont les seules interactions qui peuvent écrire un statut.
- Le texte de l'utilisateur et les noms issus du catalogue sont échappés avant affichage HTML ; les requêtes SQL utilisent des paramètres.
- L'authentification HTTPS facultative du scanner mobile reste inchangée et s'applique également au conseiller si l'utilisateur accède par Wi-Fi.

## Validation automatique

- Tests Python : compréhension des négations, persistance des critères, changements de statut, distinctions français souhaité/obligatoire, classement sourcé et aucune correspondance inventée.
- Tests JavaScript : sécurité du rendu, clavier et formulaire de conversation, cartes et réactions.
- Test PostgreSQL jetable : demande initiale, reformulation, correspondance vérifiable aux tags, cas sans résultat, absence de fiction, ISO 422 hors limites, exclusions et notice ISBN fictive explicitement séparée de la collection.
- Chromium ordinateur et viewport mobile : conversation complète, précision sur le français, fiches, nouvelle conversation, retour au parcours précédent.
- Les tests GitHub n'accèdent jamais aux volumes PostgreSQL personnels.

## Mise à jour

Sur le PC : git pull origin main, Docker Desktop, mangadvisor.cmd, **3 — Build + démarrage**. Ouvrir http://localhost:8501, puis Pour moi > Mon conseiller. Aucun effacement de base.
