# Mangadvisor — plan produit validé (18 octobre 2026)

Évolutions dans cet ordre, en conservant le thème sombre/orange, le sélecteur FR/EN et la bibliothèque.

## 1.1 — Usage quotidien et recommandations

1. **Accueil personnalisé (ce premier lot)** : reprendre les mangas marqués READING ; proposer des recommandations réellement produites par POST /recommendations/library ; distinguer sans ambiguïté « Explorer librement » des recommandations personnelles. En l'absence de données, guider l'utilisateur sans inventer de correspondances.
2. **Cartes et retours utilisateur** : « Ça m'intéresse », « Déjà lu », « Pas pour moi ». Préserver notes et volumes existants. Ne promettre l'apprentissage qu'une fois les retours réellement exploités par le moteur.
3. **Explicabilité et filtres** : motifs vérifiables (genres, thèmes, sources), score moteur exprimé en points, tests des exclusions et cas vides.

## 1.2 — France et collection

4. **Fiches enrichies en français** : titre officiel français, éditeur, auteur, tomes et éditions distinctes (classique, Deluxe, Perfect), sources françaises et conditions de réutilisation vérifiées. Traduction des synopsis avec origine et limites explicites.
5. **Bibliothèque avancée** : tomes possédés, lus et manquants, progression, éditions ; étudier les possibilités réelles d'import et de synchronisation MangaCollec, sans duplication ni suppression implicite.

## 2.0 — Conseiller et suivi

6. **Découverte selon l'envie** : ambiance et format, combinés aux goûts de l'utilisateur et au catalogue.
7. **Conseiller conversationnel** : suggestions contextualisées et explicables, ancrées dans les vraies données du catalogue et de la bibliothèque.
8. **Sorties françaises** : dates et tomes à venir, suivis et notifications lorsque des sources fiables sont disponibles.

## Garde-fous

- Une évolution = branche distincte, tests automatiques et revue avant fusion.
- Jeux de données de test synthétiques, aucun test destructif sur les collections personnelles.
- FR/EN sans fausses traductions : afficher la langue d'origine lorsque nécessaire.
- Vérifications avec vrais navigateurs desktop/mobile et API PostgreSQL sur base jetable.
- L'application reste locale sans authentification ; ne pas l'exposer publiquement.
- Ne déclarer une fonctionnalité complète qu'après validation de ses critères.
