import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync("apps/web/assets/app.js", "utf8");
const css = readFileSync("apps/web/assets/next-experience.css", "utf8");
const index = readFileSync("apps/web/index.html", "utf8");

test("MangAxiom is the visible web identity", () => {
  assert.match(index, /<title>MangAxiom/);
  assert.match(app, /MangAxiom —/);
});

test("Axiom is a single chatbot launched from home and uses the existing API", () => {
  assert.match(app, /home-axiom-card/);
  assert.match(app, /id="axiom-overlay"/);
  assert.match(app, /id="advisor-main".*advisorChatMarkup/s);
  assert.match(app, /request\("\/advisor\/ai-message"/);
  const nav = app.slice(app.indexOf("const navItems=["), app.indexOf("return '<div class=\"layout\""));
  assert.doesNotMatch(nav, /\["advisor"/);
  assert.doesNotMatch(nav, /Axiom \(IA\)/);
});

test("Explorer and the library load more items without numbered pagination", () => {
  assert.match(app, /function maybeLoadNextCatalogPage/);
  assert.match(app, /function maybeLoadNextLibraryPage/);
  assert.doesNotMatch(app, /paginate\(state\.catalogPage/);
  assert.doesNotMatch(app, /paginate\(state\.libraryPage/);
  assert.match(css, /infinite-scroll-status/);
});

test("Library V1 exposes additions from Explorer, not CSV or ISBN entry points", () => {
  const start = app.indexOf("async function renderLibrary(token)");
  const end = app.indexOf("async function updatePhysicalInventory", start);
  const renderLibrary = app.slice(start, end);
  assert.match(renderLibrary, /Ajouter depuis Explorer/);
  assert.doesNotMatch(renderLibrary, /data-action="open-scanner".*collection-stage-art/s);
  assert.doesNotMatch(renderLibrary, /data-value="manage".*library-series-panel/s);
});

test("Manga cards can add a status without discarding existing reading data", () => {
  assert.match(app, /quick-add-save/);
  assert.match(app, /readLibraryItem\(manga\)/);
  assert.match(app, /owned_volumes:old\?\.owned_volumes/);
  assert.match(app, /read_volumes:old\?\.read_volumes/);
  assert.match(app, /name="owned_volumes"/);
  assert.match(app, /name="read_volumes"/);
});
