# Mangadvisor — reconstruction propre

**Statut : chantier de reconstruction, pas encore une application exécutable.**

## Ce que nous construisons
Mangadvisor est une application locale Windows/Docker permettant de découvrir des mangas, consulter des fiches **en français lorsque la source est attestée**, retrouver les éditions françaises et leurs volumes/ISBN, gérer une collection physique, obtenir des recommandations expliquées et utiliser un conseiller de lecture.

**La V1 livrera le fonctionnement complet. La V2 sera consacrée uniquement à l'UX.**

## Notre stratégie
1. Construire un catalogue général propre, sans utiliser la mangathèque personnelle comme référentiel.
2. Importer les sources en conservant les documents bruts, leurs IDs et leurs dates.
3. Identifier les œuvres via des identifiants externes *scopés au fournisseur* et des preuves bibliographiques, jamais par un titre seul.
4. Séparer œuvre, édition, tome/publication, exemplaire possédé.
5. Construire ensuite l'application Web, l'import privé et les recommandations.

**Source « sûre » ne veut pas dire source unique** : MAL/Jikan porte des fiches internationales ; Wikidata sert aux liens explicites (P4087) et aux libellés multilingues ; BnF et éditeurs sont le point de départ bibliographique des livres français. Aucune source seule n'identifie toutes les œuvres et tous les tirages.

## Dossiers de départ
- `db/schema.sql` : modèle relationnel V1 à faire valider par PostgreSQL isolé.
- `docs/architecture.md` : composants, règles de rapprochement, protection des données.
- `docs/roadmap.md` : huit étapes, chacune avec un résultat observable.
- `docs/retour-experience.md` : erreurs à ne pas répéter d'après les précédents échanges.
- `docs/sources-et-licences.md` : API et conditions de réutilisation.
- `fixtures/cas_reference.json` : cas difficiles qui doivent guider nos contrôles.

## Règles de projet
- Une branche de travail pour la reconstruction ; pas de branche ni PR par petite tâche.
- Menu `mangadvisor.cmd` avec 6–7 opérations maximum, **ajouté seulement quand les opérations fonctionnent**.
- Un seul `compose.yaml`, un schéma SQL, une API, une UI Web, un pipeline de données.
- Tests limités aux flux critiques : base/identité, éditions/ISBN, import personnel, application de bout en bout.
- Aucun `down -v`, suppression de volume, reset ou modification des données personnelles pendant la reconstruction.
- Les autres outils sont des fonctions internes du pipeline et non de nouveaux boutons.

## Sauvegarde de l'ancien projet
Le `main` de l'ancien projet est préservé sur `archive/mangadvisor-pre-reconstruction-20261023`. **Cette archive Git ne contient pas** les volumes Docker, `.env`, `backups/`, `private-data/` ni les fichiers Jikan locaux. Ils doivent rester conservés séparément et ne pas être écrasés.

Consulter `docs/roadmap.md` avant de commencer le moindre téléchargement.
