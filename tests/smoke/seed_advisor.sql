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
