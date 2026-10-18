# Mangadvisor 1.2 — Import en lot et rapprochement sans perte

## Ce qui est livré

Depuis **Ma bibliothèque**, un assistant « Importer mes tomes par ISBN »
accepte un CSV UTF-8 (fichier local ou texte collé) contenant jusqu'à
**250 lignes / 80 Ko**. Séparateurs français `;` et `,`, tabulation.
Colonnes :
- `isbn13` ou `isbn` obligatoire
- `possede` / `owned` facultatif (par défaut oui)
- `lu` / `read` facultatif (par défaut non)

Exemple :
```csv
isbn13;possede;lu
9782871294146;oui;non
```
L'exemple est un format de démonstration et **ne prouve pas** que l'ISBN
figure dans ta collection ou que sa notice BnF est disponible.

## Sécurité de l'import

1. La fonction `POST /collection/import/preview` vérifie syntaxe,
   checksum des ISBN-13, doublons et identifiants existants **sans rien écrire**.
2. Le tableau d'aperçu distingue **ISBN reconnu** / **ISBN non référencé**,
   ainsi que les lignes invalides. Pour les connus, le titre et le numéro
   affichés proviennent de `manga_fr_edition` (déjà liés à une vraie
   notice BnF), jamais d'une supposition sur le titre du fichier.
3. L'utilisateur confirme l'import avec `POST /collection/import/apply`,
   un jeton calculé à partir du même contenu et de l'état connu.
   Une prévisualisation obsolète est refusée.
4. L'import met exclusivement des drapeaux à **vrai** (fusion logique OR).
   `non` / `false` ne supprime jamais une propriété existante.
   Refaire l'import ne duplique ni ne supprime rien.
5. Les ISBN inconnus restent dans l'aperçu sans être ajoutés. On peut
   les rechercher séparément dans la fiche manga via BnF, confirmer le
   rattachement à l'œuvre et à l'édition, puis relancer le CSV.

**Aucune modification des notes, favoris, statuts et volumes historiques
de `user_manga_library`.** L'import travaille seulement sur la table
`user_manga_volume`. Pas d'accès à des services externes en lot.

## Ancien suivi ↔ nouveaux tomes

Un bouton « Comparer avec mon ancien suivi » appelle
`GET /collection/reconciliation` en lecture seule. Il affiche côte à
côte, par œuvre, les anciens nombres globaux (`owned_volumes` et
`read_volumes`) et les tomes précis enregistrés par ISBN.

**Aucun transfert ni addition automatique** des compteurs : le nombre
de livres dans une édition Deluxe n'équivaut pas nécessairement au nombre
de tomes japonais. Le tableau sert à identifier les séries pour lesquelles
il reste à renseigner les ISBN. Le suivi d'origine reste inchangé.

## MangaCollec : état de l'étude au 18 octobre 2026

- Le site https://www.mangacollec.com présente la consultation et la
  gestion en ligne des collections, par séries et tomes.
- L'accès aux fonctions privées suppose une connexion personnelle.
- Aucune documentation officielle publique suffisamment fiable n'a été
  établie pour garantir un export CSV de collection ou une API de
  synchronisation autorisée, documentée et stable.
- Conséquence : **pas de connexion automatisée, pas de scraping de
  compte ni de demande d'identifiants**. L'import CSV fonctionne avec
  tout export ou inventaire personnel **que l'utilisateur possède
  légitimement**, si ses colonnes contiennent des ISBN.
- Une intégration directe ne devra être ajoutée que si une API officielle
  ou un export réellement disponible est vérifié avec ses conditions
  d'utilisation. La synchronisation ne sera pas présentée comme disponible
  avant ce contrôle.

## Limites

Le CSV ne crée pas automatiquement de nouvelles notices BnF : on garantit
avant tout que les ISBN inconnus ne soient jamais liés à une mauvaise
série ou édition. Pour une bibliothèque contenant de nombreux ISBN jamais
enregistrés, la prochaine évolution utile sera un **assistant de vérification
des ISBN inconnus un par un**, avec confirmation explicite et réutilisation
du fichier importé, puis éventuellement un parcours de capture de codes-barres.

L'application est toujours réservée à l'utilisateur local (pas d'authentification
multi-utilisateur) ; ne pas l'exposer sur Internet.

## Tests

- Unitaires Python : délimiteurs, colonnes, contrôle ISBN, doublons,
  refus des lignes corrompues, jeton de confirmation, absence d'effacement.
- Node : rendu du tableau, refus des liens/HTML malveillants,
  distinction reconnu/inconnu et comparaison historique.
- GitHub Actions Docker/PostgreSQL jetable : aperçu, approbation invalide
  refusée, import idempotent, conservation des champs historiques et
  lecture seule des statistiques.
- Playwright ordinateur/mobile : ouverture de l'import, aperçu de deux
  ISBN dont un inconnu et comparaison en lecture seule.

Après fusion : `git pull origin main`, Docker Desktop,
`mangadvisor.cmd` → **3 — Build + démarrage**, puis « Ma bibliothèque ».
