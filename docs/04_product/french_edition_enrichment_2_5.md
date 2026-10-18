# Mangadvisor 2.5 — Recherche française par plusieurs titres et pages

## Objectif
Retrouver davantage de notices bibliographiques françaises dans l’**Atelier d’enrichissement français** sans créer de faux rapprochements, d’ISBN, de numéros de tomes ni de disponibilités commerciales.

## Nouveau parcours
Sur la fiche manga, dans l’atelier :
1. Tu peux ajouter **un autre titre français facultatif** (entre 3 et 90 caractères, si renseigné). Mangadvisor cherche dans le catalogue BnF à partir des titres catalogués (titre principal et anglais différents) et de cet alias saisi, **sans le sauvegarder comme titre officiel**.
2. Le bouton **Rechercher les éditions** ouvre la première page de résultats, avec les statuts existants « à vérifier », « déjà associé ici » et « lié ailleurs ».
3. Si la BnF annonce d’autres notices au-delà de la page consultée, le bouton **Chercher sur la page suivante** apparaît. Il est possible de parcourir jusqu’à **trois pages de 20 notices BnF par titre**, soit trois requêtes maximum par titre et jusqu’à trois titres par recherche.
4. Chaque page chargée est ajoutée à la précédente, avec **déduplication par ISBN**, et les ISBN enregistrés dans la session conservent leur statut. L’atelier affiche les titres interrogés et le nombre de pages consultées.
5. Les ISBN sont désormais **regroupés par format suggéré** (classique, Deluxe, Perfect, Collector, intégrale, autre ou inconnu), avec le nombre de notices visibles par groupe. Ce regroupement n’a aucune valeur de confirmation : les formats comme la correspondance à l’œuvre restent à vérifier.

La limite précédente de **30 ISBN visibles par réponse** est conservée pour éviter les réponses énormes ; en chargeant des pages, l’interface cumule au maximum les ISBN de trois réponses. Si une page dépasse 30 ISBN exploitables, un avertissement indique que des candidats ont été omis.

## Garanties techniques et limites
- L’API **GET /collection/mangas/{manga_id}/enrichment?page=1..3&alternate_title=…** reste **en lecture seule** ; l’alias est local à la requête. Contrôle des paramètres côté serveur, CQL sûr, trois pages au maximum par titre et aucun téléchargement non borné.
- Les recherches BnF peuvent répondre avec des résultats homonymes ou incomplets, ainsi qu’avec des notices ne disposant pas d’ISBN utilisable. Le rapport est toujours **non exhaustif** et **non vérifié**, même sur la troisième page. Le compteur total BnF n’est pas un nombre de tomes ni un nombre d’ISBN français.
- Les statuts sont établis à partir des ISBN **effectivement enregistrés dans la table** existante, et les associations à une autre œuvre bloquent le rattachement.
- Pour enregistrer un livre, l’utilisateur doit ouvrir **Vérifier cet ISBN** : la route existante refait une recherche BnF **exacte** par ISBN, exige le choix de l’édition et du numéro de tome puis l’enregistrement explicite.
- Pas de nouvelle base, pas de migration, pas d’écriture sur la bibliothèque lors de la recherche, pas de recherche en arrière-plan, pas d’appel à une IA payante.
- Les tests couvrent la pagination SRU `startRecord`, les limites et le contrôle de titres, les doublons interpages et le maintien des confirmations, les groupes éditoriaux, la sécurité des liens et du rendu, ainsi que Chromium PC/mobile sur des données BnF simulées.

## Limites non résolues
L’alias français n’est pas automatiquement découvert. La recherche reste bornée à trois titres et trois pages, sans garantie de catalogue français complet. Les ouvrages peuvent être présents à la BnF sans être retrouvés par les titres recherchés, ou correspondre à une autre œuvre malgré un titre ressemblant.

## Mise à jour
Après fusion : `git pull origin main`. Démarrer Docker Desktop, `mangadvisor.cmd` → **3 — Build + démarrage**. Ne pas effacer les volumes. Ouvrir une fiche manga puis son **Atelier d’enrichissement français**.
