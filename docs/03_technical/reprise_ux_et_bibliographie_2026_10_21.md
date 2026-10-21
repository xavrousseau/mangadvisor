# Mangadvisor — relais UX et reprise technique (21/10/2026)

## Règle de travail
La branche `cleanup/pipelines-2026-10-21` / PR #89 reste le point d'intégration de test. Ne pas fusionner dans `main` avant validation. Ne jamais effacer les volumes Docker ou modifier l'installation principale.

## UX : travail en cours
Les captures utilisateur (Accueil, Découvrir, Pour moi, Ma bibliothèque) révèlent :
- Sur desktop, trop d'espace vide et des sections avec hiérarchie faible.
- Découverte : cartes et contrôles rigides, manque de confort de recherche.
- Conseiller : beaucoup trop de contrôles exposés avant l'action principale.
- Bibliothèque : informations techniques d'import/ISBN trop visibles en première lecture.
- Mobile : la navigation basse existe déjà, mais l'ensemble nécessite une recette sur un vrai viewport mobile.
- Navigation : `apps/web/assets/app.js` appelle `root.innerHTML=shell()` à chaque navigation, ce qui détruit les éléments de structure et peut provoquer un clignotement / perte de focus. Refactoriser avec des tests de navigation avant tout remplacement.

Premier correctif **déjà intégré à #89** : `apps/web/assets/ux-refresh.css` chargé après `appearance.css` dans `apps/web/index.html`. Ce correctif est CSS seulement, réversible, sans modification SQL.

Prochaine phase UX : hiérarchiser les pages, différer les paramètres secondaires derrière des `details`, éviter le remplacement intégral de la structure lors de la navigation, tester manuellement desktop 1440/1920 et mobile 390/375/320, vérifier accessibilité, boutons et états vides. Aucun test navigateur réel n'a encore été effectué.

## État catalogue (sandbox uniquement)
- Windows PowerShell : `F:\1.Boulot\03_Github\mangadvisor-test`.
- Docker Compose project `mangadvisor_sandbox`; base SQL `mangadvisor_realtest`, 85 776 mangas internationaux.
- 227 893 alias Tenrai/MAL avant enrichissement français (47 alias FR initiaux).
- Scrinis : 10 œuvres examinées ; 5 correspondances sûres (`EXACT_TITLE_AUTHOR` et `MATCH`), 4 ambiguës, 1 détail indisponible.
- ATTENTION : `french_print_isbn_count = 20` est plafonné par `book_references[:20]`, ce n'est pas le nombre total de tomes/ISBN.
- BnF : 83 ISBN **candidats non confirmés** sur cinq œuvres (Berserk 16, Chainsaw Man 17, One Piece 11, Shingeki no Kyojin 20, Solo Leveling 19).
- Berserk : 15 candidats édition `UNKNOWN` avec numéros de tome 24 à 41, trous candidats 25/29/38 ; tome 43 édition `COLLECTOR`. Les trous d'un échantillon ne prouvent pas une absence de publication.
- `apps/api/app/bnf_edition_audit.py` : exécuté sur vraie base et renvoie les groupes d'éditions attendus ; tests unitaires non validés en conteneur.

## Incident à reprendre après UX
Le CLI Docker Windows a cessé de fonctionner : `docker --version` et appel direct `C:\Program Files\Docker\Docker\resources\bin\docker.exe --version` renvoient code 1, sans stdout/stderr.
- `docker.exe` existe, version 29.8.2.
- Processus Docker Desktop et `com.docker.backend` visibles.
- `com.docker.service` arrêté en mode manuel (pas nécessairement une anomalie sous WSL2).
- **NE PAS** réinitialiser Docker Desktop, purger les données, utiliser `down -v` ou supprimer des volumes.
- Après réparation CLI : vérifier santé et volumes SQL, confirmer le compte 85 776, puis valider les tests `tests/test_bnf_edition_audit.py` dans un environnement où le dossier `tests` est réellement monté.
- Ensuite seulement : amélioration de la pagination BnF, récupération complète des références Scrinis, éditions/ISBN avec preuve et rapprochement manuel lorsque ambigu.

## GitHub
- PR #89 active, draft, pas fusionnée.
- PR #87, #68 et #38 ouvertes : vérifier chaque différence par rapport à #89 avant éventuelle fermeture.
- Issue #71 ouverte : chantier BnF/éditions FR à conserver jusqu'à livraison.

## Protection des données
Le catalogue réel et le cache de 858 pages sources résident dans des volumes persistants du sandbox ; la mangathèque principale n'est pas dans cet environnement. Aucun nettoyage destructif, aucune fusion bibliographique automatique, aucune opération sur la base principale.
