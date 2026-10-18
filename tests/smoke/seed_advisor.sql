-- Disposable GitHub Actions only: artificial French ISBN record on an unowned test manga.
-- Do not run this file on a personal Mangadvisor database.
INSERT INTO manga_fr_edition
  (manga_id,isbn13,title_fr,author_fr,publisher_fr,edition_kind,
   edition_kind_origin,volume_number,source_name,source_url,source_checked_at)
SELECT id,'9781234567897','Demo CI 08 — Tome 1','Auteur fictif','Éditeur fictif',
  'UNKNOWN','USER_CONFIRMED',1,'TEST SYNTHÉTIQUE CI',
  'https://catalogue.bnf.fr/ark:/12148/cb12345678x',NOW()
FROM manga WHERE title='Demo CI 08'
ON CONFLICT (isbn13) DO NOTHING;


-- Tag and synopsis clues are artificially added ONLY on the disposable CI catalog.
INSERT INTO manga_theme(manga_id,theme_id)
SELECT m.id,t.id FROM manga m JOIN theme t ON t.name='Psychological'
WHERE m.title='Demo CI 08'
ON CONFLICT DO NOTHING;
UPDATE manga SET synopsis='An investigation with psychological puzzles and no supernatural claims.'
WHERE title='Demo CI 08';
INSERT INTO genre(name) VALUES ('Horror') ON CONFLICT DO NOTHING;
INSERT INTO manga_genre(manga_id,genre_id)
SELECT m.id,g.id FROM manga m JOIN genre g ON g.name='Horror'
WHERE m.title='Demo CI 28'
ON CONFLICT DO NOTHING;
