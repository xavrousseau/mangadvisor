import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync("apps/web/assets/home.js", "utf8");
const { readingNow, personalPicks, recommendationSources } =
  await import("data:text/javascript;charset=utf-8," + encodeURIComponent(src));

test("readingNow affiche seulement les séries réellement en cours", () => {
  const entries = [
    { manga_id: 4, library_status: "READ", title: "Lu" },
    { manga_id: 7, library_status: "READING", title: "En cours 1" },
    { manga_id: 7, library_status: "READING", title: "Doublon" },
    { manga_id: 8, library_status: "READING", title: "En cours 2" },
    { manga_id: 9, library_status: "WANT_TO_READ", title: "À lire" },
  ];
  const result = readingNow(entries);
  assert.deepEqual(result.map(item => item.manga_id), [7, 8]);
  assert.equal(entries.length, 5);
});

test("readingNow ne présente pas de faux manga en cours", () => {
  assert.deepEqual(readingNow([]), []);
  assert.deepEqual(readingNow([{ library_status: "READ", manga_id: 3 }]), []);
  assert.deepEqual(readingNow(null), []);
});

test("personalPicks respecte le classement du moteur et exclut les titres connus", () => {
  const items = [
    { id: 7, recommendation_score: 108 },
    { id: 2, recommendation_score: 105 },
    { id: 7, recommendation_score: 100 },
    { id: 5, recommendation_score: 98 },
    { id: 4, recommendation_score: 92 },
  ];
  assert.deepEqual(personalPicks(items, [2], 2).map(m => m.id), [7, 5]);
  assert.equal(items.length, 5);
});

test("personalPicks ne fabrique pas de recommandations", () => {
  assert.deepEqual(personalPicks([], []), []);
  assert.deepEqual(personalPicks([{ id: null }, { id: 0 }], []), []);
  assert.deepEqual(personalPicks(null, null), []);
});

test("recommendationSources n'utilise que les sources effectivement retournées par l'API", () => {
  const result = { positive_sources: [{ title: "Monster" }, { title: "Berserk" }, { title: "Nana" }] };
  assert.deepEqual(recommendationSources(result), ["Monster", "Berserk"]);
  assert.deepEqual(recommendationSources({}), []);
  assert.deepEqual(recommendationSources({ positive_sources: [{ id: 1 }] }), []);
});
