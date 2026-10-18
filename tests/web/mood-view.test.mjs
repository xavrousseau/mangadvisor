import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const source=readFileSync("apps/web/assets/mood-view.js","utf8");
const {MOOD_OPTIONS,moodFormMarkup,verifiedMoodTags,moodResultsMarkup}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
const e=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const L=s=>e(s),tr=e;
const opts={L,e,tr,poster:()=>'<div class="poster"></div>',rating:()=>"★ 8.2/10",
 published:()=>"Terminée"};

test("six supported moods are explicit and accessible with one selected",()=>{
 assert.equal(MOOD_OPTIONS.length,6);
 const html=moodFormMarkup({mood:"DARK",length:"SHORT",useLibrary:true,
  minScore:7.5,onlyFinished:true},L,e);
 assert.match(html,/aria-pressed="true" data-action="mood-select" data-mood="DARK"/);
 assert.equal((html.match(/aria-pressed="true"/g)||[]).length,1);
 assert.match(html,/id="mood-length"/);
 assert.match(html,/value="SHORT" selected/);
 assert.match(html,/id="mood-personal" checked/);
 assert.match(html,/id="mood-finished" checked/);
 assert.match(html,/data-action="generate-mood"/);
});

test("show only verified catalog matches and actual preference overlap",()=>{
 const m={id:7,title:"Monster",score:8.2,status:"Finished",volumes:18,
  mood_matches:{genres:["Mystery"],themes:["Psychological"]},
  affinity_matches:{genres:["Mystery"],themes:[]}};
 assert.deepEqual(verifiedMoodTags(m),{mood:["Mystery","Psychological"],affinity:["Mystery"]});
 const html=moodResultsMarkup([m],opts);
 assert.match(html,/Correspond à ton ambiance|Mystery/);
 assert.match(html,/Psychological/);
 assert.match(html,/href=|data-go="\/manga\/7"/);
 assert.match(html,/data-feedback="INTERESTED"/);
 assert.match(html,/18 /);
});

test("unsafe catalog titles and tags remain escaped; absent matches not invented",()=>{
 const title='<img onerror=alert(1)>';
 const m={id:8,title,status:"Publishing",
   mood_matches:{genres:["<svg onload=alert(1)>"]},affinity_matches:{}};
 const html=moodResultsMarkup([m],opts);
 assert.doesNotMatch(html,/<img onerror|<svg onload/);
 assert.match(html,/&lt;img/);
 assert.match(html,/&lt;svg/);
 assert.deepEqual(verifiedMoodTags({mood_matches:{},affinity_matches:{}}),
                  {mood:[],affinity:[]});
});
