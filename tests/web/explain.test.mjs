import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync("apps/web/assets/explain.js", "utf8");
const { explainRecommendation, explainProfile, explainVerifiedSources } =
  await import("data:text/javascript;charset=utf-8," + encodeURIComponent(source));

test("the explanation uses only tags returned by the recommendation engine", () => {
  const original = {
    common_genres: ["Drama", "Mystery"],
    common_themes: ["Psychological", "Mystery"],
    common_demographics: ["Seinen"],
    community_recommended_from: ["Monster"],
    recommendation_score: 110.5,
    reason: "Original technical reason.",
  };
  const before = structuredClone(original);
  const result = explainRecommendation(original);
  assert.deepEqual(result.factors.map(x => x.label),
    ["themeMatch", "genreMatch", "audienceMatch", "communitySignal"]);
  assert.deepEqual(result.factors[0].values, ["Psychological", "Mystery"]);
  assert.equal(result.originalReason, "Original technical reason.");
  assert.deepEqual(result.components, []);
  assert.deepEqual(original, before);
});

test("missing, null and malformed evidence cannot fabricate an explanation", () => {
  assert.deepEqual(explainRecommendation(null).factors, []);
  assert.deepEqual(explainRecommendation({}).components, []);
  const result = explainRecommendation({
    common_themes: null,
    common_genres: "Action",
    common_demographics: [null, "", "Seinen", "Seinen"],
    community_recommended_from: [],
    editorial_score: "unavailable",
    dominant_intent_score: null,
    quality_score: NaN,
    goal_bonus: "",
    sensitive_mismatches: null,
  });
  assert.deepEqual(result.factors, [{ field: "common_demographics", label: "audienceMatch", values: ["Seinen"] }]);
  assert.equal(result.components.length, 0);
  assert.deepEqual(result.mismatches, []);
});

test("components reflect actual engine values, including negative and zero bonuses", () => {
  const result = explainRecommendation({
    editorial_score: 80.15,
    dominant_intent_score: -25,
    community_score: 0,
    quality_score: "16.5",
    goal_bonus: -8.0,
    recommendation_score: 120,
    sensitive_mismatches: ["Gore", "Romance", "Gore"],
  });
  assert.deepEqual(result.components.map(x => [x.field, x.value]), [
    ["editorial_score", 80.15], ["dominant_intent_score", -25],
    ["community_score", 0], ["quality_score", 16.5], ["goal_bonus", -8],
  ]);
  assert.deepEqual(result.mismatches, ["Gore", "Romance"]);
  assert.ok(!result.components.some(x => x.field === "recommendation_score"));
});

test("a library profile lists global sources without inventing per-candidate links", () => {
  const input = {
    positive_sources: [
      { title: "Monster", is_favorite: true, user_score: 9, library_status: "READ" },
      { title: "Vinland Saga", is_favorite: false, user_score: 8.5, library_status: "READING" },
    ],
    profile_summary: {
      top_genres: [{ name: "Drama" }, { name: "Adventure" }],
      top_themes: [{ name: "Psychological" }],
    },
  };
  const p = explainProfile(input);
  assert.deepEqual(p.sources.map(x => x.title), ["Monster", "Vinland Saga"]);
  assert.equal(p.sources[0].favorite, true);
  assert.equal(p.sources[0].score, 9);
  assert.deepEqual(p.genres, ["Drama", "Adventure"]);
  assert.deepEqual(p.themes, ["Psychological"]);
});

test("manual recommendations use only source titles present in the API response", () => {
  const p = explainProfile({ sources: [{ id: 2, title: "Nana" }] });
  assert.deepEqual(p.sources.map(x => x.title), ["Nana"]);
  assert.deepEqual(explainProfile({}), { sources: [], genres: [], themes: [] });
  assert.deepEqual(explainProfile(null), { sources: [], genres: [], themes: [] });
});


test("candidate-specific source matches use only API-provided verified overlaps", () => {
  const original = {
    explanation: {
      reference_titles: ["Monster", "Berserk"],
      source_matches: [
        { title: "Monster", genres: ["Drama"], themes: ["Psychological"], demographics: [] },
        { title: "Berserk", genres: [], themes: [], demographics: [] },
      ],
      score: { base: 75, goal_bonus: -5, final: 70 },
    },
  };
  const snapshot = structuredClone(original);
  const result=explainVerifiedSources(original);
  assert.deepEqual(result.references, ["Monster", "Berserk"]);
  assert.deepEqual(result.matches.map(x => x.title), ["Monster"]);
  assert.deepEqual(result.matches[0].genres, ["Drama"]);
  assert.deepEqual(result.score, { base: 75, bonus: -5, final: 70 });
  assert.deepEqual(original, snapshot);
});

test("candidate-specific evidence cannot fabricate matches or missing scores",()=>{
  assert.deepEqual(explainVerifiedSources(null), { references: [], matches: [], score: null });
  assert.deepEqual(explainVerifiedSources({explanation:{
    reference_titles:["Nana"],
    source_matches:[{title:"Nana",themes:[],genres:[],demographics:[]}],
    score:{base:null, goal_bonus:"", final:25},
  }}),{
    references:["Nana"], matches:[],score:{base:null,bonus:null,final:25},
  });
});

test("up to eight diversified library sources remain visible without fabrication", () => {
  const sources = Array.from({ length: 11 }, (_, i) => ({
    title: `Source ${i + 1}`, is_favorite: false,
    user_score: null, library_status: "OWNED",
  }));
  const result = explainProfile({ positive_sources: sources });
  assert.equal(result.sources.length, 8);
  assert.equal(result.sources[7].title, "Source 8");
  assert.ok(result.sources.every(x => x.favorite === false && x.score === null));
});

test("ownership-only recommendations show an explicit visible warning", () => {
  const app = readFileSync("apps/web/assets/app.js", "utf8");
  const translations = readFileSync("apps/web/assets/i18n.js", "utf8");
  assert.ok(app.includes('result.profile_summary?.preference_evidence'));
  assert.ok(app.includes('role="status"'));
  for (const label of ["recOwnedOnlyWarning", "recInterestOnlyWarning"]) {
    assert.ok(app.includes(label));
    assert.equal(translations.split(label + ":").length, 3);
  }
});
