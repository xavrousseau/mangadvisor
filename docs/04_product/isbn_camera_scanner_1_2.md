# Mangadvisor 1.2 — Scan rapide ISBN-13 (caméra / webcam)

## Depuis Ma bibliothèque ou une fiche manga

Ouvrir **Scanner mes tomes** / **Scanner un tome**.

- **Caméra** (webcam du PC ou caméra du mobile en contexte sécurisé) : viser le code-barres EAN-13 commençant par 978/979. Le scanner s'arrête dès qu'un ISBN-13 valide est lu. Le bouton d'enregistrement n'est jamais déclenché par la caméra.
- **Saisie manuelle** : taper/copier l'ISBN-13 si l'appareil ou le navigateur n'a pas de lecteur EAN-13.
- **ISBN déjà enregistré** : affiche la série, le type d'édition et le tome existants, ainsi que les statuts actuels. Une confirmation actualise seulement les statuts positifs, **sans nouveau tome en base**.
- **ISBN inconnu** : consulte la notice BnF exacte puis impose la série (recherche/sélection, sauf présélection visible depuis sa fiche), l'édition, le numéro de tome et une case de confirmation explicite.
- **Possédé / Lu** : cases indépendantes. Le mode rapide coche Possédé par défaut, sans jamais supprimer un statut déjà positif. L'utilisateur confirme avant d'enregistrer.
- **Scanner le suivant** : enchaîne les tomes dans la même session. Fermeture, navigation ou changement de langue arrête la caméra.

## Respect du référentiel et de la collection

L'API utilise GET /collection/scan/status/{isbn} sans écriture. Si inconnu, elle réutilise la recherche BnF /collection/isbn/{isbn}. L'enregistrement passe par POST /collection/scan/confirm : contrôle serveur ISBN-13, notice BnF pour une nouvelle entrée, confirmation obligatoire, conflit en cas d'association différente et mise à jour additive des seuls statuts acquis.

Les tables historiques user_manga_library et leurs compteurs ne sont ni écrites ni recalculées. Aucune modification de schéma. Il n'y a ni reconnaissance magique de la série, ni déduction de tome/édition à partir du titre BnF. Un ISBN sans notice BnF reste bloqué.

## Caméra et téléphone : prérequis techniques

Le lecteur emploie le navigateur BarcodeDetector si celui-ci prend en charge **EAN-13**. Il ne télécharge aucune bibliothèque de scan externe. Tous les navigateurs ne supportent pas encore cette API : la saisie manuelle reste possible.

getUserMedia() et BarcodeDetector nécessitent un **contexte sécurisé** :
- **Sur le PC local** : http://localhost:8501 est considéré comme une origine de confiance par les navigateurs modernes. Autoriser l'accès à la webcam.
- **Sur le téléphone** : http://192.168.x.x:8501 n'est **pas** considéré comme sécurisé. Il faudra servir Mangadvisor via un accès HTTPS valide (et rendre le service accessible au téléphone), sans exposer directement l'API/PostgreSQL sur Internet. Cette évolution n'installe pas de HTTPS à elle seule.
- En cas de refus caméra, d'absence d'EAN-13 ou de HTTPS manquant, un message explique la limite. Rien n'est enregistré automatiquement.

Documentations :
- https://developer.mozilla.org/en-US/docs/Web/API/BarcodeDetector
- https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia

## Vérifications automatisées

- tests/web/isbn-scanner.test.mjs : checksum ISBN-13, champs obligatoires, confirmation explicite, rendu HTML échappé et absence d'association automatique.
- tests/test_collection_scan.py : absence de mutation au scan, prérequis BnF, confirmation atomique, refus des doublons/déplacements et préservation des statuts existants.

## Mise à jour Windows après intégration dans main

Dans le dépôt Mangadvisor : récupérer les changements Git, démarrer Docker Desktop puis mangadvisor.cmd → option **3 — Build + démarrage**. Visiter http://localhost:8501 → **Ma bibliothèque** → **Scanner mes tomes**. Les données PostgreSQL sont conservées : ne pas exécuter de nettoyage des volumes Docker.
