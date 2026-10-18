# Mangadvisor Mobile 2.0 — HTTPS privé et bilan des scans

## Configuration Windows + Docker Desktop

**Aucun hébergement public.** Le PC exécute Mangadvisor, le téléphone utilise le même Wi-Fi privé. Un proxy Caddy facultatif sert une page HTTPS sur la carte réseau IPv4 privée explicitement choisie, au port 8443, protégée par l'utilisateur manga et un mot de passe fort. Les autres services restent liés à localhost.

1. Récupérer la version Git, démarrer Docker Desktop et Mangadvisor normalement (menu 3 si nécessaire).
2. Ouvrir mangadvisor.cmd puis sélectionner **13 — Activer le scanner mobile HTTPS**.
3. Si plusieurs interfaces réseau sont disponibles, choisir la carte Ethernet/Wi-Fi du foyer.
4. Le script génère un mot de passe aléatoire. Lire le lien, l'identifiant et le mot de passe dans **mobile-local/access.txt**, stocké uniquement sur le PC et ignoré par Git.
5. Transférer **uniquement** mobile-local/mangadvisor-root-ca.crt vers **son propre** téléphone Android (USB ou Quick Share).
6. Android : Paramètres > Sécurité et confidentialité > Autres paramètres de sécurité > Installer un certificat > Certificat CA (intitulés variables). Lire l'avertissement de sécurité Android. N'installer que le CA créé sur son propre PC.
7. Dans Chrome Android, ouvrir l'adresse HTTPS avec IP/port indiqués, entrer manga + mot de passe, aller à **Ma bibliothèque > Scanner mes tomes** puis autoriser la caméra.

**Certificat non reconnu ?** Il ne suffit pas d'ignorer une alerte HTTPS : pour obtenir l'accès à la caméra, le certificat doit être réellement approuvé. Vérifier la CA du PC, l'IP exacte et le support EAN-13 du navigateur.

**Lien inaccessible ?** Vérifier que le PC ne dort pas, que Docker tourne, que les appareils partagent le Wi-Fi et que le réseau Windows a le profil Privé. Si besoin seulement, ouvrir PowerShell en administrateur et saisir :

    New-NetFirewallRule -DisplayName "Mangadvisor Mobile HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8443 -Profile Private -RemoteAddress LocalSubnet

Pour supprimer la règle :

    Remove-NetFirewallRule -DisplayName "Mangadvisor Mobile HTTPS"

Éviter les Wi-Fi publics/invités ; ne jamais rediriger le port 8443 depuis la box, exposer Docker sur Internet, ni partager les secrets et clés privées du proxy. Lorsque le PC change d'IP, relancer l'option 13 puis rouvrir la nouvelle URL.

Pour couper l'accès, **14 — Arrêter le scanner mobile HTTPS** ou mangadvisor.cmd mobile-stop. L'arrêt ne supprime jamais les données. Retirer le certificat CA du téléphone s'il n'est plus utilisé.

## Parcours et bilan

- Après confirmation, **Scanner le suivant** conserve la dernière série comme suggestion explicite. Le tome, le type d'édition et la confirmation de rattachement restent indispensables pour un ISBN inconnu.
- Si la caméra était utilisée, le bouton du tome suivant tente de la redémarrer après la confirmation. Aucune écriture n'est déclenchée par un scan seul.
- Le **Bilan de session** classe chaque ISBN traité comme : nouvel ajout, statuts complétés, déjà présent sans changement ou non résolu. Les ISBN à revoir proposent une nouvelle tentative.
- Le bilan reste **temporaire dans le navigateur**, sans nouvelle table ni synchronisation. Les tomes confirmés restent persistants en PostgreSQL.
- Scanner deux fois le même ISBN ne crée pas deux copies. Possédé/Lu sont indépendants et les statuts positifs précédents sont conservés. Les compteurs historiques ne sont pas touchés.

## Vérifications

- Tests JS : classement de session, rapprochement exact ISBN, confirmation avant écriture, protections HTML.
- Tests Playwright : ordinateur et affichage mobile, édition nouvelle, édition déjà connue, bilan.
- GitHub Actions : proxy Caddy HTTPS réellement démarré sur boucle locale de CI, test de certificat avec CA locale, authentification requise et refus de mauvais mot de passe.

Sources :
- https://caddyserver.com/docs/automatic-https
- https://developer.mozilla.org/en-US/docs/Web/API/BarcodeDetector/getSupportedFormats_static
