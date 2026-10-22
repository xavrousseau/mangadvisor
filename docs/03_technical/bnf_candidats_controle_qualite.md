# Contrôle de qualité des candidats BnF — 22 octobre 2026

## Cas témoin : Berserk (MAL 2)

Recherche paginée à trois pages : 38 ISBN candidats, **PARTIAL**, zéro échec HTTP.
Les 38 candidats ne représentent ni 38 tomes confirmés ni 38 publications en français.

Inventaire visuel communiqué lors de la recette :
- 3 notices explicitement Collector pour les numéros 41, 42 et 43 ;
- édition Prestige explicitement désignée pour les numéros 1, 2, 3, 5 et 6 ;
- plusieurs notices numérotées sans libellé d'édition : leur statut reste UNKNOWN, pas CLASSIC ;
- « Berserk of Gluttony » : **autre œuvre**, à exclure des rapprochements automatiques de Berserk ;
- « Berserk : illustrations file » : ouvrage connexe, sans assimilation à un tome principal ;
- « Berserk / Kentaro Miura » : livre sans tome ni édition déterminables à ce stade.

## Modèle de confiance

**Œuvre -> langue -> édition -> tome -> ISBN**, cinq dimensions indépendantes.
- Une recherche par mot du titre produit des candidats, pas un match d'œuvre.
- La langue du titre, l'éditeur français ou un traducteur mentionné ne remplacent pas
  la langue déclarée et une validation des métadonnées source.
- Un ISBN unique n'identifie pas à lui seul la série recherchée.
- Une édition Prestige n'est ni automatiquement une Classic ni une Perfect.
- Une variante Collector doit garder sa propre identité d'édition et son ISBN.
- Les numéros de tomes supposés manquants ne doivent pas être déduits d'un intervalle BnF.
- Aucun candidat ne doit être enregistré comme possédé sans confirmation utilisateur.

## Nouveau diagnostic en lecture seule

Module : `apps/api/app/bnf_candidate_review.py` ; règles :
`apps/api/app/bnf_candidate_quality.py`.

Commande dans le sandbox moteur après mise à jour et construction :

```powershell
docker compose --env-file .env.sandbox -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.sandbox.yml run --rm -T -e POSTGRES_DB=mangadvisor_realtest engine python -m apps.api.app.bnf_candidate_review --mal-id 2
```

Analyse les 38 candidats **sans UPDATE, DELETE ni INSERT**. Les champs
`work_status`, `language_status` et `edition_suggested` sont des aides
à la revue, pas des correspondances vérifiées ; `registration_ready` reste faux.

## Étapes suivantes

1. Réviser la classification et les langues constatées sur les 38 notices.
2. Élargir progressivement la pagination BnF avec garde-fous et throttling,
   sans prétendre à l'exhaustivité.
3. Croiser chaque candidat plausible avec Scrinis et les références éditeur :
   ISBN, titre, auteur, éditeur, langue et édition.
4. Créer des associations vérifiées distinctes par œuvre/édition/tome/ISBN ;
   ne jamais modifier la mangathèque sur une simple recherche de titre.
5. Étendre les tests à plusieurs éditions d'une même série et aux homonymes.
