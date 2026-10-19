# Mangadvisor 3.8 — Importer une mangathèque physique sans perdre sa collection

## Le principe

Cette version permet d'intégrer **progressivement et avec confirmation** les séries d'un fichier privé comme celui du benchmark 3.7. Le nouvel import n'est **pas** un import d'ISBN : un simple nombre de tomes ne permet pas d'identifier les ISBN, les numéros de tomes exacts, leur édition publiée, ni les lectures.

L'inventaire physique est donc stocké dans une **nouvelle table additive** `user_manga_inventory_declaration`, indépendante des éditions françaises vérifiées (`manga_fr_edition` et `user_manga_volume`). Cette séparation est essentielle pour ne jamais transformer des approximations ou intitulés déclarés en fiches bibliographiques prétendument certifiées.

**Aucune collection réelle ni fichier CSV du propriétaire n'est envoyé sur GitHub, Ollama ou un service extérieur.**

## Préparer le fichier

Placer le CSV privé au chemin `private-data/mangatheque.csv`, comme pour le benchmark 3.7. Il doit contenir les colonnes :

`serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier;statut_releve;ligne_source;oeuvre_commune;edition_declaree;format_catalogue_provisoire`

Les quatre premières sont obligatoires ; `oeuvre_commune` et `edition_declaree` sont facultatives mais doivent être remplies **ensemble** pour les variantes physiques d'une même œuvre. Le format provisoire est conservé comme une note non vérifiée, jamais comme une édition BnF certifiée.

Exemple de données **fictives**, et non une copie de la collection privée :

```csv
serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier;ligne_source;oeuvre_commune;edition_declaree;format_catalogue_provisoire
Manga Démo édition A;3;0;0;Inventaire!A4;Manga Démo;Édition A;INCONNU
Manga Démo édition B;4;1;0;Inventaire!A5;Manga Démo;Édition B;INCONNU
```

## Windows — menu 21

1. **D'abord créer une sauvegarde** avec `mangadvisor.cmd` option **17** et en conserver une copie sur un second support.
2. Mettre à jour `main`, lancer Docker Desktop puis l'option **3 — Build + démarrage**.
3. Placer le CSV dans `private-data/mangatheque.csv`.
4. Lancer **option 21 — Importer ma mangathèque après vérification**.
5. **Aucun enregistrement n'est ajouté pendant l'aperçu.** Le script affiche les lignes sûres, inchangées et nécessitant une vérification, ainsi que leurs éditions et quantités déclarées. Un rapport détaillé est enregistré sous `private-data/inventaire_apercu_*.json`.
6. Saisir exactement la phrase affichée par le script pour confirmer. Si des lignes restent ambiguës, la phrase contient **PARTIEL**, afin de reconnaître explicitement que ces lignes ne seront pas ajoutées. Un fichier modifié ou une base modifiée depuis l'aperçu invalide le jeton et nécessite une nouvelle vérification.
7. Relancer l'option **20** pour comparer les propositions du conseiller avant et après import.

Pour générer seulement l'aperçu et quitter sans écriture :

`powershell -NoProfile -ExecutionPolicy Bypass -File cmd/import-private-inventory.ps1 -PreviewOnly`

## Ce que fait le rapprochement

Le moteur retrouve uniquement les correspondances **exactes et uniques** sur les titres de catalogue ou leurs titres anglais/japonais enregistrés. Un rapprochement « à peu près », plusieurs mangas homonymes, ou une série absente passent au statut **REVIEW** plutôt que d'être importés au hasard.

Le regroupement d'éditions exige des noms d'édition distincts. Deux lignes sans édition portant sur la même œuvre sont classées ambiguës ; deux éditions explicitement identifiées peuvent partager un `manga_id` avec des quantités distinctes.

Une déclaration existante :
- identique : **UNCHANGED**, aucun doublon ou modification ;
- différente (quantité, édition, titre, source) : **REVIEW_EXISTING**, aucune mise à jour automatique ;
- opposée à un statut personnel `NOT_INTERESTED` : **REVIEW_LIBRARY_CONFLICT**, aucune mise à jour sans arbitrage.

Les lignes `REVIEW` ne sont jamais ajoutées par la procédure automatique. Après le premier import, on peut corriger le CSV et relancer l'aperçu pour les titres restants.

## Préservation des données

- Une œuvre canonique liée à une déclaration sûre est ajoutée dans `user_manga_library` comme **OWNED** uniquement si elle n'y figurait pas déjà, afin que les recommandations ne proposent plus une série possédée.
- Pour une œuvre déjà suivie, **aucun** statut lu/à lire/possédé/rejeté, score personnel, favori, nombre de tomes lus, nombre de tomes possédés ou commentaire existant n'est changé.
- Le nombre de tomes physiques déclaré **ne remplace pas** le compteur historique `owned_volumes` ; additionner les deux éditions d'une œuvre donnerait un résultat trompeur.
- Les éditions déclarées, même appelées « Deluxe » ou « Pastel », **ne créent aucun ISBN ni lien BnF**. La vérification des éditions françaises reste un processus séparé, avec confirmation humaine.
- Les `doublons_identiques` représentent des copies physiques supplémentaires d'ouvrages déjà comptés, et les `autres_editions_a_identifier` restent une quantité **non répartie** sur des ISBN.
- Les anciennes routes `/library/import/csv` sont désormais **add-only** pour les œuvres déjà suivies : elles ne peuvent plus écraser les notes et compteurs. Elles ne savent néanmoins pas distinguer les éditions : privilégier le menu 21.
- L'import est atomique : soit les seules lignes prêtes sont enregistrées, soit l'opération échoue sans modifications intermédiaires.

## Vérifications GitHub

- Unitaires : validation CSV, Dragon Ball **uniquement simulé par de faux titres**, doubles éditions, entrées ambiguës, refus de statut contradictoire, stabilité des empreintes.
- PostgreSQL jetable : aperçu sans écriture, refus d'import partiel sans confirmation, rejet d'ancien jeton, création des éditions séparées, conservation de la bibliothèque existante et des scores, import répété sans doublons, refus de remplacement silencieux d'une quantité, exclusion d'œuvre nouvellement possédée des recommandations.
- Contrôle de non-régression sur l'ancien import CSV, et suites précédentes : agent, ISBN, navigateur PC/mobile, sauvegarde/restauration et HTTPS.

## Limitations assumées

- Les titres non reconnus, homonymes ou en version française non référencée dans le catalogue ne seront **pas importés sans arbitrage**. Il reste à fournir un outil de résolution manuelle sûre et d'ISBN par édition.
- La v3.8 se pilote par le **menu Windows 21** et ses rapports privés. Une interface graphique de rapprochement/validation peut être ajoutée après vérification sur les vrais retours.
- Il n'existe pas encore de suivi d'exemplaire individuel (chaque tome précis) à partir d'un simple nombre de volumes.
- Les tests GitHub utilisent une collection entièrement synthétique et ne démontrent pas la qualité des correspondances avec toutes les 103 entrées réelles.
