import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const editionSource=readFileSync("apps/web/assets/advisor-editions.js","utf8");
const editionUrl="data:text/javascript;charset=utf-8,"+encodeURIComponent(editionSource);
const file=readFileSync("apps/web/assets/advisor-view.js","utf8")
 .replace('from "./advisor-editions.js"', 'from "'+editionUrl+'"');
const {advisorChatMarkup,advisorResultsMarkup,ADVISOR_PROMPTS}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(file));
const e=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const L=e;

test("conversation offers French starter prompts and accessible composer",()=>{
 assert.equal(ADVISOR_PROMPTS.fr.length,4);
 const html=advisorChatMarkup({history:[],busy:false,lang:"fr"},L,e);
 assert.match(html,/data-action="advisor-prompt"/);
 assert.match(html,/id="advisor-form"/);
 assert.match(html,/maxlength="500"/);
 assert.match(html,/role="log"/);
 assert.match(html,/data-action="advisor-reset"/);
});

test("history does not render arbitrary HTML and busy state blocks input",()=>{
 const html=advisorChatMarkup({history:[{role:"user",text:'<img src=x onerror="alert(1)">'},
  {role:"assistant",text:"Aucun résultat"}],busy:true,lang:"fr"},L,e);
 assert.doesNotMatch(html,/<img src=x/);
 assert.match(html,/&lt;img src=x/);
 assert.match(html,/textarea[^>]+disabled/);
 assert.match(html,/button class="btn btn-primary" type="submit" disabled/);
});

test("results show only server-provided evidence and verified ISBN distinction",()=>{
 const m={id:8,title:"Manga 8",status:"Finished",score:8.2,volumes:9,
  mood_matches:{genres:["Mystery"],themes:[]},affinity_matches:{genres:[],themes:[]},
  french_recorded:true};
 const options={L,e,tr:e,poster:()=>'<span class="poster"></span>',
  rating:()=>"★ 8.2/10",published:()=>"Finished"};
 const html=advisorResultsMarkup({personalized:false,count:1,recommendations:[m]},options);
 assert.match(html,/Mystery/);
 assert.match(html,/advisor-french is-verified/);
 assert.match(html,/French ISBN registered|advisorFrenchRegistered/);
 assert.match(html,/data-go="\/manga\/8"/);
 assert.match(html,/data-feedback="INTERESTED"/);
 const second=advisorResultsMarkup({personalized:false,count:1,
  recommendations:[{...m,french_recorded:false}]},options);
 assert.match(second,/advisor-french "/);
 assert.doesNotMatch(second,/advisor-french is-verified/);
});

test("malicious titles, tags and feedback IDs are not injected",()=>{
 const html=advisorResultsMarkup({count:1,recommendations:[{
  id:'7" onclick="alert(1)',
  title:"<script>alert(1)</script>",
  mood_matches:{genres:['<svg onload="attack()">']},
  affinity_matches:{genres:[],themes:[]},
 } ]},{L,e,tr:e,poster:()=>"poster",rating:()=>"",published:()=>""});
 assert.doesNotMatch(html,/<script>|<svg onload|onclick="alert/);
 assert.match(html,/&lt;script&gt;/);
 assert.match(html,/&lt;svg/);
});


test("narrative evidence names its source and unverified clues stay explicit",()=>{
 const manga={id:44,title:"Enquête étrange",status:"Finished",volumes:9,
  mood_matches:{genres:["Mystery"],themes:[]},
  affinity_matches:{genres:[],themes:[]},french_recorded:false,
  narrative_matches:[
   {concept:"INVESTIGATION",source:"synopsis_word",matched:"investigation"},
   {concept:"PSYCHOLOGICAL",source:"catalog_tag",matched:"Psychological"}
  ],
  narrative_unverified:["SURVIVAL"]};
 const html=advisorResultsMarkup({count:1,recommendations:[manga]},{
  L,e,tr:e,poster:()=>'<span class="poster"></span>',rating:()=>"★",
  published:()=>"Finished"});
 assert.match(html,/advisor-story-chip/);
 assert.match(html,/advisorStoryINVESTIGATION/);
 assert.match(html,/advisorStoryTag: Psychological/);
 assert.match(html,/advisorStorySynopsis: investigation/);
 assert.match(html,/advisorNarrativeMissing: advisorStorySURVIVAL/);
});

test("synopsis-derived tokens remain HTML escaped",()=>{
 const manga={id:15,title:"Safe title",mood_matches:{genres:["Mystery"]},
  narrative_matches:[{concept:"INVESTIGATION",source:"synopsis_word",matched:'<img src=x onerror=alert(1)>'}],
  narrative_unverified:[],affinity_matches:{},french_recorded:false};
 const html=advisorResultsMarkup({count:1,recommendations:[manga]},{
  L,e,tr:e,poster:()=>"Poster",rating:()=>"",published:()=>""});
 assert.doesNotMatch(html,/<img src=x/);
 assert.match(html,/&lt;img src=x/);
});
