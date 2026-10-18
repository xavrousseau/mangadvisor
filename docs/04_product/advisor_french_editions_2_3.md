# Mangadvisor 2.3 — éditions françaises sourcées dans le conseiller

## Nouveau parcours

Dans **Pour moi → Mon conseiller**, chaque manga recommandé pour lequel des ISBN français ont été enregistrés affiche un volet **Éditions françaises référencées**.

Ce volet regroupe les **livres physiques connus** par format éditorial : CLASSIC, DELUXE, PERFECT, COLLECTOR, INTEGRAL, OTHER ou UNKNOWN. Chaque groupe indique :
- le **nombre d'ISBN effectivement enregistrés** dans ce format ;
- les éditeurs présents sur ces notices (ou « non renseigné ») ;
- les **numéros de tomes des ISBN référencés**, pas un total de tomes publiés ;
- jusqu'à quatre ISBN détaillés par format (titre français du livre, éditeur, numéro de tome, éventuelle date, lien source si BnF valide), ainsi que le nombre de notices restantes.

Le format **UNKNOWN reste explicitement inconnu**. Un tome 1 Deluxe n'est jamais confondu avec un tome 1 Perfect ni avec un tome 1 classique. Le titre japonais et le nombre de volumes de la série originale ne sont jamais utilisés pour inventer des parutions françaises.

Les données viennent **uniquement de la table existante** manga_fr_edition, elle-même constituée de notices ISBN associées à une œuvre de manière confirmée. Le volet n'effectue **aucune recherche externe** ni écriture. Seuls des liens source sécurisés du catalogue BnF sont cliquables.

## Dialogue par format

L'utilisateur peut préciser son intention dans la conversation :

- « Je préfère une édition Deluxe » : augmente le rang des mangas **ayant au moins un ISBN français Deluxe enregistré**, sans exclure les autres.
- « Édition Deluxe obligatoire » : filtre **strictement** les mangas sans ISBN français Deluxe enregistré.
- « En édition Perfect uniquement » : remplace la préférence précédente par Perfect obligatoire.
- « Peu importe le format » : retire le critère de format tout en conservant les autres éléments de la conversation.

Le changement de format est pris en compte même si la conversation a commencé par « mystère terminé ». L'intention est affichée parmi les critères reconnus. Aucun format non référencé n'est affirmé ni supposé.

Les critères précédents « français souhaité » vs « ISBN français obligatoire » restent indépendants des contraintes de format. « Disponible en France » continue de signifier, dans cette version, **ISBN français enregistré**, et non vente confirmée ; l'interface le précise.

## Limites et garde-fous

**Une notice enregistrée n'est pas une preuve que la totalité de la série soit sortie en France ni de disponibilité en librairie.** Les champs published_total_known=false, availability_checked=false et complete_french_series=null sont explicites dans les résultats API. Un trou entre des tomes connus ne prouve pas qu'un livre n'a pas été publié.

Pour chaque format, quatre notices au plus sont affichées sur la carte afin de préserver la lisibilité mobile ; le nombre réel de références connues est toujours indiqué. Pour consulter les autres notices, ouvrir la fiche du manga, où la collection française et la liste existante sont disponibles.

Les éditions non enregistrées ne sont pas découvertes par ce nouveau parcours ; elles doivent être ajoutées via le dispositif de notice et de confirmation déjà présent. Aucun titre, ISBN, éditeur, stock ou tome n'est généré artificiellement.

## Architecture et validation

- Nouveau module backend apps/api/app/advisor_editions.py : requête SQL paramétrée pour les mangas déjà sélectionnés, groupement par format et nombre de notices enregistré.
- L'API POST /advisor/message conserve les attributs de recommandation précédents et ajoute french_editions par manga proposé. La préférence de format est appliquée au classement ; l'exigence de format ajoute un prédicat SQL EXISTS.
- Nouveau composant frontend apps/web/assets/advisor-editions.js, rendu HTML échappé et whitelist stricte pour les URL BnF (HTTPS uniquement).
- Tests unitaires Python et JS : groupement, doublons, limitation d'affichage, données de preuve, liens sûrs et interprétation de suivi.
- Tests SQL sur base PostgreSQL jetable : notices fictives pour un même manga sous quatre formats, préférence/exigence de format, aucun résultat si format absent.
- Tests navigateur Chromium desktop/mobile : affichage des livres et de leurs sources, passage à « Deluxe obligatoire », conversation et autres parcours préservés.

Aucune nouvelle migration SQL, aucune remise à zéro des volumes Docker et aucune mutation des mangas personnels. Les fixtures sont **synthétiques et strictement réservées à GitHub Actions**.

## Sur le PC

Après fusion : git pull origin main. Lancer Docker Desktop, puis mangadvisor.cmd → **3 — Build + démarrage**. Ouvrir **Pour moi → Mon conseiller** et rechercher une série ayant des éditions françaises déjà enregistrées.
