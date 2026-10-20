# Mangadvisor — enrichir ma mangathèque en une seule opération

## Pourquoi une option supplémentaire ?

L'ancien parcours obligeait à lancer séparément des lots Wikidata (8 mangas)
et BnF (10 mangas), alors que l'utilisateur peut avoir des dizaines de séries
dans sa collection. L'option avancée **12 — Enrichir ma mangathèque
automatiquement (Wikidata et BnF)** traite maintenant **les œuvres déjà
reliées à la bibliothèque personnelle**, avec une seule sauvegarde préalable.

Pour la première collecte personnelle observée, la base contenait **53 mangas
suivis**, **54 déclarations physiques** et **49 lignes d'inventaire encore à
rapprocher**. Ces chiffres correspondent à un point de départ utilisateur,
pas à des totaux garantis pour les autres installations.

## Mode d'emploi Windows

1. Lancer `mangadvisor.cmd`, puis **3 — Mettre à jour sans perdre mes données**.
2. Choisir **A — Options avancées**, puis **12 — Enrichir ma mangathèque
   automatiquement**.
3. Confirmer le maximum de séries ciblées (80 par défaut, 250 maximum).
   Ce nombre n'est pas un nombre de pages internet : il fixe les **œuvres
   personnelles liées**, et évite de parcourir les 10 000 mangas du catalogue.
4. Choisir de lancer les recherches BnF en plus de Wikidata (Oui par défaut).
   BnF est plus lent et fournit des **ISBN candidats à vérifier**, jamais des
   tomes ajoutés automatiquement.
5. Le centre de contrôle effectue **une sauvegarde PostgreSQL complète avec
   restauration de contrôle**, puis lance les sources l'une après l'autre.
6. Lire le bilan de chaque source. Après « Appuyez sur une touche », le menu
   réapparaît. Revenir à la page Mangadvisor pour consulter les genres et les
   notices bibliographiques.

Les options **10** (BnF uniquement) et **11** (Wikidata uniquement) sont
conservées pour explorer également les œuvres du catalogue **hors collection**.

## Garanties et fonctionnement

- Les ID ciblés proviennent exclusivement des tables
  `user_manga_inventory_declaration` et `user_manga_library` pour
  `user_id=1`, dédoublonnés par `manga.id`. Les œuvres physiques vérifiées
  passent en premier.
- Les entrées `user_manga_inventory_pending` ne contiennent aucun
  `manga_id` vérifié. Elles sont **comptées et signalées**, sans correspondance
  inventée et sans écriture corrective.
- Wikidata traite des lots de 15 MAL ID maximum ; BnF traite des lots de
  10 mangas, avec sa temporisation entre les requêtes. Une courte attente
  sépare deux lots consécutifs.
- Le traitement est **reprenable** : les tables
  `manga_wikidata_attempt` et `manga_bnf_attempt` évitent de revérifier
  immédiatement une série déjà analysée.
- Un pré-bilan SQL **en lecture seule** distingue pour chaque fournisseur :
  œuvres éligibles, déjà recherchées récemment (cache) et restant à traiter.
  Wikidata compte aussi les mangas sans ID MyAnimeList ou dont le type
  n'est pas couvert. La mention « 53 œuvres liées » ne signifie donc
  **pas** « 53 œuvres enrichies ». Une exécution avec `selected=0` peut
  être normale si toutes les séries éligibles sont en cache ; toute anomalie
  entre le pré-bilan et le traitement est explicitement signalée.
- La sélection BnF est affichée en clair **avant la sauvegarde** :
  « Wikidata=OUI ; BnF=OUI/NON ». Si l'utilisateur choisit Non,
  aucun appel BnF n'a lieu et le bilan le mentionne explicitement.
- Un échec général d'une source arrête ses appels suivants ; son bilan
  signale un **échec partiel**. Les résultats sauvegardés restent présents.
- Les seules écritures des collecteurs sont dans
  `manga_wikidata_fact`, `manga_wikidata_attempt`,
  `manga_bnf_candidate`, `manga_bnf_attempt`.
  **Aucun ISBN, tome, édition, état de lecture, note ou préférence personnelle
  n'est créé ou remplacé.**

## Intérêt pour le conseiller

Le conseiller affiche les genres Wikidata comme **données communautaires
complémentaires** reliées à une œuvre par son MAL ID. Ils ne sont **jamais une
preuve** que l'utilisateur apprécie le genre ou qu'un manga répond à une
ambiance demandée.

En revanche, si l'utilisateur demande explicitement « sans horreur »,
« sans gore » ou « sans romance », les libellés Wikidata correspondants peuvent
**écarter préventivement** une œuvre qui possédait pourtant un tag canonique
incomplet. Les filtres SQL et la vérification Python concordent : des
genres Wikidata absents ne produisent aucune exclusion nouvelle.

Les éditions françaises exigées restent contrôlées exclusivement grâce aux
ISBN validés dans `manga_fr_edition`, jamais grâce aux libellés Wikidata.

## Suite

Les **49 lignes en attente** ne deviendront pas des séries connues grâce à un
import de synopsis. Pour cela, une prochaine étape dédiée devra proposer
un atelier de rapprochement manuel, avec différentes éditions de la même œuvre
conservées séparément. Elle devra demander confirmation pour les cas
ambigus, sans relier automatiquement les lignes de CSV à une mauvaise série.
