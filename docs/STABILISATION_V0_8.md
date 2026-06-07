\# Mangadvisor — Stabilisation V0.8



\## Objectif de la V0.8



La V0.8 transforme Mangadvisor d’un simple moteur de recommandation en une première application orientée bibliothèque utilisateur.



L’utilisateur peut maintenant :



\* gérer une bibliothèque manga ;

\* indiquer les mangas lus, en cours, possédés, à lire, abandonnés ou non intéressants ;

\* noter ses mangas ;

\* marquer des favoris ;

\* importer une bibliothèque depuis CSV ou Excel ;

\* analyser son profil de lecture ;

\* obtenir des recommandations depuis sa bibliothèque ;

\* choisir un objectif de recommandation.



\---



\## Fonctionnalités validées



\### V0.7.4 — Moteur de recommandation stable



Le moteur de recommandation profil est stabilisé.



Il prend en compte :



\* genres communs ;

\* thèmes communs ;

\* cible éditoriale ;

\* score manga ;

\* popularité ;

\* statut ;

\* signal communautaire Jikan ;

\* malus simples.



\### V0.8.1 — Recommandations depuis bibliothèque



Ajout de la recommandation à partir de la bibliothèque utilisateur.



Endpoint principal :



```text

POST /recommendations/library

```



\### V0.8.2 — Pondération bibliothèque



Ajout d’un poids positif par manga de bibliothèque.



Les signaux pris en compte :



\* statut bibliothèque ;

\* note utilisateur ;

\* favori ;

\* manga lu ;

\* manga en cours ;

\* manga à lire ;

\* manga possédé.



\### V0.8.3 — Objectifs de recommandation



Ajout de l’objectif de recommandation.



Objectifs disponibles :



```text

SIMILAR\_SAFE

READ\_NEXT

SHORT\_FINISHED

```



\### V0.8.4 — Tests des statuts bibliothèque



Validation des statuts :



```text

READ

READING

OWNED

WANT\_TO\_READ

DROPPED

NOT\_INTERESTED

```



\### V0.8.5 — Neutralisation des mangas mal notés



Un manga lu avec une très mauvaise note ne contribue plus positivement au profil.



\### V0.8.6 — Profil de lecture



Ajout de l’analyse du profil utilisateur.



Endpoint :



```text

GET /library/profile

```



Retourne :



\* répartition par statut ;

\* sources positives ;

\* mangas les plus influents ;

\* signaux négatifs ;

\* genres dominants ;

\* thèmes dominants ;

\* cibles éditoriales dominantes.



\### V0.8.7 — Import CSV



Ajout de l’import bibliothèque depuis CSV.



Endpoint :



```text

POST /library/import/csv

```



\### V0.8.8 — Import Excel



Ajout de l’import Excel côté Streamlit.



Le fichier Excel est converti en CSV en mémoire puis envoyé à l’API d’import CSV.



\### V0.8.9 — Modèles d’import



Ajout de modèles téléchargeables :



\* modèle CSV ;

\* modèle Excel.



\### V0.8.10 — Tests automatisés import



Validation automatique :



\* CSV simulation ;

\* CSV import réel ;

\* Excel converti en CSV.



\### V0.8.11 — Robustesse import



Validation des cas non parfaits :



\* colonnes françaises ;

\* séparateur point-virgule ;

\* note avec virgule ;

\* statut invalide ;

\* titre vide ;

\* doublon ;

\* mise à jour d’un manga existant ;

\* booléen invalide.



\---



\## Endpoints principaux



\### Catalogue



```text

GET /mangas

GET /mangas/{manga\_id}

```



\### Recommandations



```text

GET  /recommendations/similar

POST /recommendations/profile

POST /recommendations/library

```



\### Bibliothèque



```text

GET    /library

POST   /library/items

PUT    /library/items/{manga\_id}

DELETE /library/items/{manga\_id}

GET    /library/profile

POST   /library/import/csv

```



\---



\## Statuts bibliothèque



| Statut         | Sens           |

| -------------- | -------------- |

| READ           | Manga lu       |

| READING        | Manga en cours |

| OWNED          | Manga possédé  |

| WANT\_TO\_READ   | Envie de lire  |

| DROPPED        | Abandonné      |

| NOT\_INTERESTED | Pas intéressé  |



\---



\## Objectifs de recommandation



| Objectif       | Sens                           |

| -------------- | ------------------------------ |

| SIMILAR\_SAFE   | Proche de mes goûts            |

| READ\_NEXT      | Quoi lire ensuite              |

| SHORT\_FINISHED | Série terminée / plutôt courte |



\---



\## Format d’import bibliothèque



Colonnes reconnues :



```text

title

library\_status

user\_score

is\_favorite

owned\_volumes

read\_volumes

notes

```



Alias français reconnus :



```text

titre

statut

note

favori

volumes\_possedes

volumes\_lus

commentaire

```



\---



\## Commandes utiles



\### Lancer la stack



```cmd

mangadvisor.cmd up

```



\### Build



```cmd

mangadvisor.cmd build

```



\### Restart



```cmd

mangadvisor.cmd restart

```



\### Statut



```cmd

mangadvisor.cmd status

```



\### Logs



```cmd

mangadvisor.cmd logs

```



\---



\## Commandes de test



\### Tests profils de recommandation



```cmd

cmd\\run-recommendation-tests.cmd

```



\### Tests recommandations depuis bibliothèque



```cmd

cmd\\run-library-recommendation-tests.cmd

```



\### Tests objectifs de recommandation



```cmd

cmd\\run-library-goal-tests.cmd

```



\### Tests statuts bibliothèque



```cmd

cmd\\run-library-status-tests.cmd

```



\### Tests import bibliothèque



```cmd

cmd\\run-library-import-tests.cmd

```



\### Tests robustesse import



```cmd

cmd\\run-library-import-robustness-tests.cmd

```



\### Validation globale V0.8



```cmd

cmd\\run-v0-8-validation.cmd

```



\---



\## Rapports générés



Les rapports sont stockés dans :



```text

docs/reports

```



Rapports importants :



\* `recommendation\_profile\_tests\_v0\_7\_4.md`

\* `library\_recommendation\_tests\_v0\_8\_2\_profile\_summary.md`

\* `library\_goal\_tests\_v0\_8\_3.md`

\* `library\_status\_tests\_v0\_8\_5.md`

\* `library\_import\_tests\_v0\_8\_10.md`

\* `library\_import\_robustness\_tests\_v0\_8\_11.md`



\---



\## Décision



La V0.8 peut être considérée comme une base fonctionnelle solide.



Elle valide :



\* le moteur de recommandation ;

\* la bibliothèque utilisateur ;

\* l’import CSV et Excel ;

\* le profil utilisateur ;

\* les recommandations depuis bibliothèque ;

\* les objectifs de recommandation ;

\* les principaux tests de robustesse.



La prochaine grande étape pourra être :



\* nettoyage du projet ;

\* amélioration produit ;

\* préparation de la future couche LLM.



