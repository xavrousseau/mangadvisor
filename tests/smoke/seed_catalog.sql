-- Base et données exclusivement jetables dans GitHub Actions. NE PAS exécuter sur la base personnelle.
INSERT INTO genre(name) VALUES ('Action'), ('Adventure'), ('Drama') ON CONFLICT DO NOTHING;
INSERT INTO theme(name) VALUES ('Mystery'), ('Psychological') ON CONFLICT DO NOTHING;
INSERT INTO demographic(name) VALUES ('Seinen'), ('Shounen') ON CONFLICT DO NOTHING;

INSERT INTO manga (
    source_mal_id,title,title_english,synopsis,status,volumes,chapters,score,popularity,members,favorites,manga_type
)
SELECT 900000 + n,
       CASE n WHEN 1 THEN 'Naruto' WHEN 2 THEN 'Monster'
              WHEN 3 THEN 'Vinland Saga' WHEN 4 THEN 'Berserk'
              ELSE 'Demo CI ' || LPAD(n::text, 2, '0') END,
       'Test title ' || n,
       'Synopsis fictif pour tests automatises.',
       CASE WHEN n % 3 = 0 THEN 'Publishing' ELSE 'Finished' END,
       12 + n, 100 + n, 7.2 + (n % 10)::numeric/10, n, 10000 + n * 100, n * 10, 'Manga'
FROM generate_series(1,36) AS n;

INSERT INTO jikan_manga_source(mal_id,title,raw_json)
SELECT m.source_mal_id,m.title,'{}'::jsonb FROM manga m ON CONFLICT(mal_id) DO NOTHING;

INSERT INTO manga_genre(manga_id,genre_id)
SELECT m.id,g.id FROM manga m
JOIN genre g ON g.name = CASE WHEN m.id % 2 = 0 THEN 'Action' ELSE 'Adventure' END
ON CONFLICT DO NOTHING;
-- Ajouter deux genres communs à Naruto et à plusieurs titres fictifs.
-- Cela garantit des candidats réels pour les tests du moteur "similaire".
INSERT INTO manga_genre(manga_id,genre_id)
SELECT m.id,g.id FROM manga m JOIN genre g ON g.name = 'Action'
WHERE m.title IN ('Naruto','Demo CI 05','Demo CI 07','Demo CI 09','Demo CI 11')
ON CONFLICT DO NOTHING;
INSERT INTO manga_theme(manga_id,theme_id)
SELECT m.id,t.id FROM manga m CROSS JOIN theme t
WHERE t.name = 'Mystery' AND m.id % 2 = 0
ON CONFLICT DO NOTHING;
INSERT INTO manga_demographic(manga_id,demographic_id)
SELECT m.id,d.id FROM manga m CROSS JOIN demographic d
WHERE d.name = 'Seinen'
ON CONFLICT DO NOTHING;
INSERT INTO user_manga_library(user_id,manga_id,library_status,user_score,is_favorite)
SELECT 1,m.id,'READ',9.0,TRUE FROM manga m WHERE m.title IN ('Naruto','Monster')
ON CONFLICT(user_id,manga_id) DO NOTHING;
-- Une lecture en cours pour vérifier l'accueil personnel (base CI uniquement).
INSERT INTO user_manga_library(user_id,manga_id,library_status,user_score,is_favorite,read_volumes,owned_volumes)
SELECT 1,m.id,'READING',8.0,FALSE,3,12 FROM manga m
WHERE m.title = 'Vinland Saga'
ON CONFLICT(user_id,manga_id) DO NOTHING;
DO $$
BEGIN
  IF (SELECT count(*) FROM manga) < 30 THEN
    RAISE EXCEPTION 'Catalogue insuffisant pour la validation de pagination';
  END IF;
END $$;
