# Mangadvisor — rapprochement bibliographique prudent (v2)

## Périmètre de cette livraison

Branche de travail `cleanup/pipelines-2026-10-21`, sans fusion dans `main`.

L'amélioration concerne le **choix d'une oeuvre Scrinis** lorsque plusieurs fiches
portent des titres comparables. La preuve bibliographique BnF reste une
**zone de candidats**, distincte de la mangathèque et des éditions vérifiées.

## Règle de décision — trois candidats maximum

Le classement Scrinis existant compare identifiant MAL, titre exact et
similarité textuelle. Auparavant, un classement `AMBIGUOUS` bloquait
immédiatement, sans consulter les détails des fiches concurrentes.

Désormais, lorsque **la totalité des concurrents** tient dans une borne de
trois fiches :
1. Écarter un candidat dont l'identifiant MAL déclaré contredit notre MAL.
2. Télécharger le détail de chaque candidat encore admissible sous la
   limitation de débit du fournisseur.
3. Vérifier la cohérence du type d'oeuvre (manga/manhwa/roman/artbook).
4. Comparer les auteurs connus et les auteurs fournisseur, après normalisation
   du nom.
5. Exiger au moins un ISBN déclaré français imprimé par Scrinis.
6. Accepter le rapprochement de **l'oeuvre** uniquement si un seul candidat
   satisfait tous ces critères et qu'aucune vérification concurrente est
   indisponible ou incomplète.

Deux auteurs concordants, plus de trois candidats plausibles, réponse
inaccessible, conflit d'identifiant, auteurs non vérifiables ou absence
d'ISBN FR papier : **aucune association automatique par cette voie**.

L'ISBN n'est **jamais ajouté comme volume possédé** ni associé à une édition
canonique du seul fait du rapprochement de l'oeuvre.

## Séries longues

L'enveloppe des réponses de détail Scrinis est désormais limitée à 2,5 Mo
(contre 600 Ko auparavant). La limite des réponses de recherche demeure
600 Ko. Cette modification n'implique PAS que le cas One Piece soit résolu :
un nouveau résultat API réel est requis, et toute réponse dépassant 2,5 Mo
demeure rejetée. Aucune pagination fictive n'est ajoutée.

L'adaptateur Scrinis sait examiner au plus 250 entrées volume par réponse,
avec indicateurs de troncature. **Ne pas considérer cette limite comme une
couverture bibliographique exhaustive.**

## Tests et recette

- `tests/test_scrinis_competing_works.py` : choix unique sur auteur,
  égalité des auteurs, information concurrente indisponible, plus de trois
  concurrents, conflit MAL explicite.
- `tests/test_scrinis_response_limits.py` : réponse longue acceptable en
  détail, plafond toujours en vigueur, recherche toujours limitée.
- Mise à jour des régressions BnF et capacité Scrinis.
- CI GitHub Actions « Vérifications Python » : réussite, **441 tests**
  lors du commit `5b0a3ee52a4a029e1da0be7c1027dc0c9bdeeae1`.
- CI « Centre de pilotage Windows » et « installation stable mono-interface » :
  réussites sur ce commit.
- CI navigateur intégrée : échec indépendant sur un sélecteur Playwright
  qui rencontre deux éléments `data-action=rec-mode` (aucune preuve de
  panne de rapprochement bibliographique à partir de cet échec).

## À valider avec le jeu de données sandbox

Exécuter sur le sandbox les tests et un **nouveau** lot Scrinis éligible.
Les états `AMBIGUOUS` existants ne sont pas reclassifiés sans nouvelle
collecte. Les contrôles de temporisation restent actifs ; aucune relance
massive forcée n'est introduite.

Vérifier en priorité : Chainsaw Man, Solo Leveling et One Piece, puis un
échantillon plus varié incluant des éditions multiples. Réaliser un audit
manuel des rapprochements réellement produits avant de passer à 100 mangas.

## Limites assumées

La résolution des ambiguïtés est conservatrice et fondée sur les auteurs
et ISBN FR papier ; elle ne constitue pas encore le graphe transversal
complet `oeuvre -> langue -> édition -> tome -> ISBN`. Les recherches BnF
exactes par ISBN et la validation fine des éditions sont les évolutions
suivantes. Les données de la collection utilisateur restent isolées.
