// Protect the product's "Voir la fiche" route and the Nginx SPA reload.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const controller = readFileSync(new URL('../../apps/web/assets/app.js', import.meta.url), 'utf8');
const proxy = readFileSync(new URL('../../apps/web/nginx.conf', import.meta.url), 'utf8');

test('manga cards and covers navigate to the manga detail route', () => {
  assert.match(controller, /data-go=[^\n]*?\/manga\//);
  assert.match(controller, /function routeInfo\(\)/);
  assert.ok(controller.includes('path.match(/^\\/manga\\/('));
});

test('a direct page refresh keeps the Web SPA route', () => {
  assert.match(proxy, /location \/ \{/);
  assert.match(proxy, /try_files \$uri \$uri\/ \/index\.html;/);
});

test('the API proxy stays separate from the Web SPA routes', () => {
  assert.match(proxy, /location \/api\/ \{/);
  assert.match(proxy, /rewrite \^\/api\/\(\.\*\)\$ \/\$1 break;/);
});
