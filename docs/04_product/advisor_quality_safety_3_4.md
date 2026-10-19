# Mangadvisor 3.4 — Évaluer les recommandations et fiabiliser les demandes complexes

## Objectif

Le conseiller produit des mangas issus du catalogue réel, mais avant cette version il était difficile de juger **la qualité documentaire de l'ensemble d'une sélection**. L'IA locale pouvait aussi interpréter imparfaitement une demande à plusieurs contraintes, notamment en contredisant une exclusion explicite.

Cette évolution ne prétend **pas** mesurer la probabilité que l'utilisateur aime un manga ; elle ajoute des mesures factuelles, inspectables à chaque recherche et calculées localement avec les données réellement interrogées.

## Un bilan par sélection

Dans **Pour moi → Mon conseiller**, ouvrir le panneau discret **« Comment cette sélection est-elle construite ? »** sous les trois modes de découverte :

- **Mangas affichés** : nombre de fiches retournées.
- **Candidats examinés** : nombre de lignes de catalogue SQL parcourues, limité à 500. Si 500 ont été lues, l'interface signale qu'il peut exister d'autres candidats non examinés.
- **Genres et thèmes distincts** : nombre de tags effectivement enregistrés parmi les suggestions affichées.
- **Affinités avec tes lectures** : nombre de propositions comportant au moins un genre ou thème commun aux lectures positives réellement enregistrées ; zéro si la personnalisation est désactivée ou indisponible.
- **Ressemblance moyenne des tags entre suggestions** : moyenne de Jaccard sur les couples possédant tous deux des tags documentés, affichée uniquement lorsqu'au moins un couple est comparable. Plus cette valeur est élevée, plus les suggestions partagent de tags ; cela n'évalue **ni** l'intrigue réelle ni leur qualité littéraire.

L'API `POST /advisor/message` et `POST /advisor/ai-message` incluent le même champ `quality_diagnostic` : `scope`, `examined_count`, `returned_count`, `unique_manga_count`, `tag_evidence_count`, `unique_recorded_tags`, `affinity_evidence_count`, `french_isbn_record_count`, `narrative_clue_evidence_count`, `mean_pairwise_tag_overlap`, `pair_count_compared` et `candidate_pool_capped`.

Ces mesures ne contiennent **aucun export de la bibliothèque personnelle**, aucune nouvelle requête externe et aucune donnée reconstruite ou devinée. Elles sont calculées en lecture seule après la sélection SQL. Une valeur d'affinité ne constitue pas une note de satisfaction.

## Conseiller IA — contraintes explicites toujours prioritaires

Lorsque Ollama est activé, il continue à **interpréter les préférences** et non à générer des mangas. Une étape déterministe supplémentaire `reconcile_ai_intent` compare sa proposition avec les critères expressément reconnus dans le message.

Les contraintes reconnues côté serveur ont toujours priorité si le modèle les contredit :

- « sans horreur », « sans gore », « sans romance » et leur éventuelle autorisation explicite ;
- « français obligatoire », « idéalement en français », « peu importe la langue » ;
- format français imposé ou simplement préféré ;
- courte/longue série, terminée/en cours ;
- personnalisation et mode de découverte ;
- score minimal explicite.

En complément, un modèle qui omet un ancien filtre strict ne peut pas le desserrer **silencieusement**. Pour lever un filtre obligatoire, il faut qu'une nouvelle demande soit reconnue sans ambiguïté par la partie guidée. L'ordre « recommençons » réinitialise les anciennes contraintes, même si l'IA oublie de le faire.

L'IA locale ne reçoit toujours **ni SQL, ni collection de volumes, ni notes personnelles, ni ISBN**. Les suggestions sont choisies exclusivement parmi les lignes de PostgreSQL et leurs éditions réellement connues.

### Limites

Une formulation très originale peut être correctement comprise par Ollama, mais rester ambiguë pour les protections déterministes : dans ce cas, **la sécurité des contraintes obligatoires prévaut** et il pourra être nécessaire de reformuler l'assouplissement. Les tags Jikan et les notices françaises peuvent être incomplets. Les contraintes `sans horreur` ou `sans gore` excluent les œuvres **étiquetées ainsi**, sans garantir l'absence de contenu sensible non étiqueté.

## Vérifications et qualité

- Tests unitaires : Jaccard moyen calculé, résultats vides ou isolés, affinités sourcées, absence de probabilité fictive et pertinence des statistiques ; demandes mixtes où le modèle retourne volontairement l'opposé des filtres, préservation multi-tours et réinitialisation explicite.
- Test API sur PostgreSQL CI jetable : preuve que les compteurs correspondent au nombre de fiches retournées, que leurs sources sont des tags existants et que les exclusions sont respectées.
- Tests JavaScript et Chromium PC/mobile : panneau repliable accessible et données lisibles. Tous les tests du catalogue, ISBN, sauvegarde/restore et HTTPS restent exécutés avant fusion.
- Validation **sur ta vraie collection** : à réaliser sur le PC après mise à jour. Les tests GitHub utilisent des titres synthétiques ; ils ne mesurent pas encore la satisfaction ni l'affinité réelle de ta bibliothèque de mangas.

## Essai local

1. `git pull origin main`, puis Docker Desktop et `mangadvisor.cmd` option **3**.
2. Au préalable, faire une sauvegarde de la bibliothèque (option **17**).
3. Ouvrir **http://localhost:8501 → Pour moi → Mon conseiller**.
4. Demander « Surprends-moi selon mes goûts », puis tester les modes **Proche / Équilibré / Surprends-moi** ; ouvrir **Comment cette sélection est-elle construite ?** et comparer tags, affinités et répétitions.
5. Si Ollama est activé (option **15**), demander « Un mystère terminé et court, obligatoirement en français, sans horreur ni gore » puis « Montre-m'en d'autres » et vérifier que les critères restent actifs.

Prochain chantier après validation : analyser les recommandations réellement appréciées/rejetées et ajuster leurs poids avec des retours explicites, sans prétendre inventer des préférences ou évaluer la qualité d'une oeuvre à partir d'un score mystérieux.
