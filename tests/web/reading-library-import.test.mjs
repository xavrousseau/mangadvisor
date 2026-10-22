import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const ui=readFileSync('apps/web/assets/app.js','utf8');
const api=readFileSync('apps/api/app/main.py','utf8');

test('reading-library CSV/XLSX is separate from ISBN book import',()=>{
 assert.match(ui,/id="reading-file"/);
 assert.match(ui,/accept="\.csv,\.xlsx/);
 assert.match(ui,/data-action="reading-preview"/);
 assert.match(ui,/data-action="reading-apply"/);
 assert.match(ui,/request\("\/library\/import\/csv"/);
 assert.match(ui,/request\("\/library\/import\/xlsx\/convert"/);
 assert.match(ui,/request\("\/collection\/import\/preview"/);
});

test('preview must be simulated before any reading-library import',()=>{
 assert.match(ui,/async function previewReadingCsv\(/);
 assert.match(ui,/default_status:status,dry_run:true/);
 assert.match(ui,/if\(!preview\|\|document\.querySelector\("#reading-csv"\)/);
 assert.match(ui,/default_status:preview\.status,dry_run:false/);
 assert.match(ui,/state\.readingPreview=null/);
});

test('API reading import cannot overwrite existing entries',()=>{
 assert.match(api,/ON CONFLICT \(user_id, manga_id\) DO NOTHING/);
 assert.match(api,/def convert_reading_library_xlsx/);
 assert.match(api,/return \{"csv_content": xlsx_to_library_csv/);
});
