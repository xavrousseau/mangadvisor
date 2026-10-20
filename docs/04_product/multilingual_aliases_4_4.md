# Mangadvisor — rapprochement multilingue FR / EN / JA

## Objectif

Les captures utilisateur montrent la même série sous **L'Attaque des Titans**
(inventaire), **Shingeki no Kyojin** (nom d'origine romanisé) et
**Attack on Titan** (titre anglais). Mangadvisor conserve déjà un MAL manga ID
pour les œuvres mais n'exploitait pas partout leurs synonymes multilingues.

La fonctionnalité distingue deux éléments :
1. **Alias vérifiés en base** : index PostgreSQL de titres FR, EN, JA issus de
   Wikidata **P4087** après revérification de l'identifiant manga MAL dans
   l'élément Wikidata lui-même (et refus si l'ID ne correspond pas).
2. **Recherche externe facultative** : bouton MangaDex dans l'atelier des
   lignes en attente. Une recherche limitée renvoie seulement les résultats
   ayant un lien `links.mal` explicite vers un manga qui existe déjà dans
   le catalogue Mangadvisor. Aucune confirmation automatique.

### Sources étudiées

| Source | Usage retenu | Limites |
|---|---|---|
| Wikidata, [P4087](https://www.wikidata.org/wiki/Property:P4087) | Titres et alias FR/EN/JA, provenance QID, CC0 | Couverture partielle, labels communautaires non officiels |
| [MangaDex](https://api.mangadex.org/docs/03-manga/) | Recherche à la demande des alias multilingues ; rapprochement uniquement si `links.mal` explicite | Attribution obligatoire, uniquement non commercial, pas de stockage de scans/chapitres |
| [MyAnimeList API v2](https://myanimelist.net/apiconfig/references/api/v2) | Prochaine source optionnelle pour `alternative_titles.synonyms` avec Client-ID | Configuration d'application nécessaire |
| [Manga Hook](https://mangahook-api.vercel.app/introduction) | Non intégré | API adossée au scraping, moins adaptée à un catalogue pérenne |
| [publicapis.dev](https://publicapis.dev/category/anime) | Répertoire d'identification de fournisseurs | Répertoire, pas API de données unique |

Les sources externes peuvent comporter des erreurs. Une correspondance
`links.mal` ou `P4087` est un indice fort d'identité de l'œuvre mais
**pas une preuve d'édition française** ni de possession.

## Utilisation

1. `mangadvisor.cmd` → **3** pour sauvegarder PostgreSQL et mettre à jour.
2. **A → 13** : « Récupérer les titres alternatifs FR, EN et JA ». Un petit lot
   (12 œuvres par défaut, 20 max) est traité dans les correspondances Wikidata
   déjà validées, en donnant la priorité à la collection. La sauvegarde
   PostgreSQL est vérifiée avant le lot.
3. Répéter A → 13 pour étendre progressivement l'index. Les séries déjà
   enrichies sont mémorisées pendant 45 jours.
4. Ouvrir **Ma bibliothèque → En attente de rapprochement**, rechercher
   une ligne par son titre français, anglais ou japonais. La recherche
   standard utilise désormais les alias sourcés.
5. Si elle ne trouve pas de résultat, saisir le titre et cliquer
   **Recherche étendue MangaDex (facultative)**. Les résultats doivent porter
   un lien MAL manga vers le catalogue. Un lien source est affiché.
6. Contrôler **l'œuvre** et **l'édition** avant tout rapprochement manuel.
   Un titre alternatif ne crée jamais un volume ou un ISBN.

La recherche globale `GET /mangas?q=...` prend elle aussi en charge les
alias enregistrés. Les labels français Wikidata déjà en cache sont ajoutés
automatiquement lors de l'initialisation additive SQL de l'API, sans
requête réseau ni nouvelle entrée de bibliothèque.

## Exemple de doublon dangereux

La bibliothèque peut afficher `Shingeki no Kyojin` avec **34 tomes principaux
+ 1 autre édition** et l'inventaire en attente `L'Attaque des Titans` avec
**35 exemplaires**. Cela **peut être deux façons de décrire les mêmes livres**.

Le moteur ne doit donc surtout pas additionner automatiquement 34 + 1 + 35.
La confirmation manuelle refuse d'insérer une nouvelle ligne avec la même
œuvre/édition. L'utilisateur doit identifier les différentes éditions avant
toute consolidation. Les livres compagnons, les éditions Deluxe/Perfect et les
manga dérivés demeurent des fiches distinctes si leurs identités diffèrent.

## Sécurité, limites et tests

- Deux nouvelles tables additives : `manga_title_alias` (avec source,
  langue et provenance), `manga_title_alias_attempt` (date/statut).
- L'index ne modifie **aucun** champ `manga.title`/ISBN/volumes/lectures ;
  la recherche est insensible à la casse et accepte toutes les langues
  dont un titre est disponible.
- Wikidata renvoie au plus 20 entités par requête, avec taille et durée
  bornées. Les titres sont refusés si le P4087 ne confirme pas l'ID MAL manga.
- Recherche MangaDex facultative et limitée à 12 œuvres, catégorie
  `safe`, une requête HTTP par clic, sans images ni contenu de lecture,
  sans écriture PostgreSQL. Les erreurs réseau sont visibles.
- Les tests simulent les fournisseurs externes (aucun besoin que leurs serveurs
  soient accessibles pendant GitHub Actions) et contrôlent les rejets.

L'intégration de nouvelles sources doit respecter les conditions d'usage,
éviter les doublons et privilégier les identifiants vérifiés plutôt que les
ressemblances de titres.