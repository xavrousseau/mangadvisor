# Mangadvisor 1.1 — Réagir aux recommandations

## Objectif

Sous chaque suggestion, proposer trois actions évidentes, sans quitter la page :

| Action (FR / EN) | Statut existant utilisé | Effet réel sur la recommandation |
|---|---|---|
| Ça m'intéresse / I'm interested | WANT_TO_READ | Ajoute un signal positif léger à la bibliothèque, utilisé pour le profil de lecture |
| Déjà lu / Already read | READ | Marque une lecture effectuée ; peut contribuer positivement au profil |
| Pas pour moi / Not for me | NOT_INTERESTED | Exclut explicitement ce titre des futures propositions |

Chaque action est enregistrée par **POST /recommendations/feedback**, réservé à
l'utilisateur local existant (user_id=1), selon les mêmes limites que l'application
historique sans authentification.

## Garantie de préservation des données

Le retour n'utilise **pas** l'ancienne API de mise à jour complète des éléments.
Il modifie uniquement le champ `library_status` d'un enregistrement existant :
aucun effacement de note, favori, notes personnelles, tomes lus/possédés ou dates.

- Un manga nouvellement noté est ajouté à la bibliothèque.
- Une nouvelle opinion peut modifier un statut purement intentionnel :
  WANT_TO_READ ↔ NOT_INTERESTED.
- « Déjà lu » est une déclaration explicite : peut mettre à jour un statut existant
  sans toucher à la note ou aux volumes.
- « Ça m'intéresse » ou « Pas pour moi » n'écrasent **jamais** un manga déjà
  READ, READING, OWNED ou DROPPED : HTTP 409 avec un message pour éditer
  sa fiche. Cela évite de perdre un état de collection plus précis.

## Intégration au moteur

La bibliothèque était déjà utilisée comme signal :

- Poids positif conditionné à READ / READING / WANT_TO_READ / OWNED et aux notes.
- Les éléments NOT_INTERESTED et DROPPED sont exclus des sources positives.
- Les mangas présents dans la bibliothèque sont exclus des recommandations
  provenant de la bibliothèque.
- **Nouveau :** les recommandations depuis des titres favoris ainsi que les
  recommandations similaires ne proposent plus de candidats déjà marqués
  NOT_INTERESTED ou DROPPED. L'exclusion SQL se fait AVANT LIMIT.

La première version n'apprend **pas encore des catégories entières refusées**.
« Pas pour moi » rejette un manga en particulier, pas tous les mangas ayant ses
genres. Cette interprétation plus fine nécessitera des signaux suffisamment riches
et un modèle de préférences explicite.

## Comportement de l'interface

- Actions présentes sur les cartes depuis l'accueil, « Pour moi » et les
  recommandations similaires des fiches manga.
- Confirmation courte en FR/EN après réponse réussie du serveur.
- La carte est retirée immédiatement de la sélection courante ;
  une nouvelle recherche exploite les préférences enregistrées.
- Accueil personnalisé recalculé après l'action.
- Erreur serveur (dont 409) : la carte reste affichée et son message est visible,
  pour ne pas donner une fausse impression d'enregistrement.

## Tests et sécurité

- Tests unitaires : mapping des statuts, garde-fou, absence d'effacement
  de notes/tomes/favoris, manga inconnu et action invalide.
- Parcours navigateur : réaction « Pas pour moi », disparition immédiate,
  nouvelle recherche et exclusion confirmée.
- Tests d'intégration : bases PostgreSQL synthétiques, persistance de
  « Ça m'intéresse » et « Déjà lu », conservation des informations existantes,
  contrôle que les 3 endpoints de recommandation excluent les titres rejetés.
- Aucun schéma ajouté, aucun reset, aucune migration de la vraie bibliothèque.
- Le serveur est toujours mono-utilisateur : ne pas déployer publiquement sans
  authentification.

## Suite de Mangadvisor 1.1

Après validation de ce lot : mieux présenter l'explication des propositions
et contrôler la pertinence et les exclusions selon les types de préférences.
