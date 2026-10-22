# Exécuter tous les tests sans toucher à la base sandbox

L'image normale `engine` est volontairement minimale : elle ne contient
pas `openpyxl`, les scripts Windows, l'ensemble du dépôt, ni les fichiers
SQL de vérification. Elle ne convient qu'aux tests ciblés du moteur.

Depuis PowerShell **à la racine du clone** :

```powershell
git pull origin cleanup/pipelines-2026-10-21
docker build -f infra/docker/tests/Dockerfile -t mangadvisor-regression-tests .
docker run --rm --network none mangadvisor-regression-tests
```

La commande `docker run` lance l'intégralité des tests unittest dans un
conteneur jetable **sans réseau et sans volume monté**. Elle ne peut donc
ni modifier la collection ni contacter la base sandbox. Aucune commande
`docker compose down -v` n'est nécessaire.

Pour tester seulement la nouvelle logique Scrinis, remplacer la dernière
commande par :

```powershell
docker run --rm --network none mangadvisor-regression-tests python -m unittest discover -s tests -p "test_scrinis*.py" -v
```

Le filtre `test_scrinis*.py` doit être utilisé avec cette image **après
reconstruction**. Sous l'image `engine` précédente, zéro test pouvait
simplement refléter un état antérieur à l'ajout de ces fichiers.

Les tests utilisant des mocks ne remplacent pas une recette d'enrichissement
sur le sandbox. Les informations bibliographiques réelles seront validées
séparément après vérification des délais fournisseur.

La CI GitHub utilise aussi une exécution Python native du dépôt, distincte
de l'image de production. Les tests navigateur sont une chaîne différente.
