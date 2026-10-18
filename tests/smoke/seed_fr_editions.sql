-- Données synthétiques sur CI jetable uniquement. Jamais exécuter sur les volumes personnels.
-- La structure est déjà créée au démarrage de l'API.
INSERT INTO manga_fr_edition
  (manga_id,isbn13,title_fr,author_fr,publisher_fr,
   edition_kind,edition_kind_origin,volume_number,release_date_text,
   source_name,source_url,source_checked_at)
SELECT id,'9782871294146','Naruto — Tome 1','Masashi Kishimoto','Kana',
  'CLASSIC','USER_CONFIRMED',1,'2002',
  'BnF — DONNÉE SYNTHÉTIQUE CI',
  'https://catalogue.bnf.fr/ark:/12148/cb12345678x',now()
FROM manga WHERE title='Naruto'
ON CONFLICT (isbn13) DO NOTHING;
