import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const js = readFileSync("apps/web/assets/explanations.js", "utf8");
const { renderRecommendationExplanation } =
  await import("data:text/javascript;charset=utf-8," + encodeURIComponent(js));

const escape = value => String(value).replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));

const fr = {
  explainTitle:"Pourquoi ce manga ?", explainSources:"Mangas pris en compte",
  explainSourcesNote:"Sources utilisées", explainExactMatches:"Ressemblances observées",
  explainNoDirect:"Pas de ressemblance directe", explainMeasured:"Non additif",
  explainCommunity:"Communauté", explainNoCommunity:"Sans votes",
  explainCautions:"Réserves", explainNoCautions:"Aucune réserve",
  explainScore:"Comprendre le score", explainBase:"Score initial",
  explainGoal:"Bonus objectif", explainFinal:"Score final",
  explainNotTotal:"Pas une décomposition complète",
  explainSignals:"Autres facteurs", explainEngineOriginal:"Texte d'origine",
  explainVotes:"votes", explainCommunityCount:"mangas sources",
  explainShared:"Points communs", genreMatch:"Genres", themeMatch:"Thèmes",
  audienceMatch:"Public", explainCommunityScore:"Communauté",
  explainEditorialScore:"Éditorial", explainQualityScore:"Qualité",
  explainIntentScore:"Intention",
};
const english = Object.fromEntries(Object.entries(fr).map(([key, value]) => [
  key, key === "explainSources" ? "Manga used to build your profile" :
  key === "explainExactMatches" ? "Verified similarities" : value
]));

const render = (m, lang="fr") => renderRecommendationExplanation(m, {
  text:key=> (lang==="fr"?fr:english)[key] || key,
  translateTag:value=>value==="Drama" && lang==="fr"?"Drame":value,
  escape,
});

test("affiche la preuve au niveau des sources, pas une causalité inventée", () => {
  const html=render({
    recommendation_score: 105,
    explanation:{
      reference_titles:["Monster", "Berserk"],
      source_matches:[{title:"Monster",genres:["Drama"],themes:["Mystery"],demographics:[]}],
      shared:{genres:["Drama"],themes:["Mystery"],demographics:[]},
      score:{base:100,goal_bonus:5,final:105},
    },
  });
  assert.match(html,/Ressemblances observées/);
  assert.match(html,/Monster/);
  assert.match(html,/Berserk/);
  assert.match(html,/Drame/);
  assert.match(html,/Score initial/);
  assert.match(html,/100.0/);
  assert.match(html,/\+5.0/);
  assert.match(html,/105.0/);
  assert.match(html,/Non additif/);
});

test("n'invente pas de contribution quand les sources n'ont pas de point commun", () => {
  const html=render({recommendation_score:50,explanation:{
    reference_titles:["Berserk"],source_matches:[],
    community:{votes:0,source_count:0},
    score:{final:50},
  }});
  assert.match(html,/Pas de ressemblance directe/);
  assert.match(html,/Sans votes/);
  assert.match(html,/Score final/);
});

test("tous les noms de mangas et les attributs sont échappés",()=>{
  const html=render({reason:'<img src=x onerror=alert(1)>',
    explanation:{
      reference_titles:['<script>alert(1)</script>'],
      source_matches:[{title:'<svg onload=attack()>',genres:['<b>Action</b>']}],
      score:{final:1},
    },
  });
  assert.doesNotMatch(html,/<script>|<svg onload|<img src/);
  assert.match(html,/&lt;script&gt;/);
  assert.match(html,/&lt;svg onload/);
  assert.match(html,/&lt;img src/);
});

test("les libellés bilingues sont utilisés sans modifier les valeurs",()=>{
  const item={explanation:{
    reference_titles:["Monster"],source_matches:[{title:"Monster",genres:["Drama"]}],
    score:{final:22},
  }};
  const snapshot=JSON.stringify(item);
  assert.match(render(item,"en"),/Verified similarities/);
  assert.match(render(item,"en"),/Manga used to build your profile/);
  assert.equal(JSON.stringify(item),snapshot);
});
