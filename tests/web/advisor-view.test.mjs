import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const editionSource=readFileSync("apps/web/assets/advisor-editions.js","utf8");
const editionUrl="data:text/javascript;charset=utf-8,"+encodeURIComponent(editionSource);
const file=readFileSync("apps/web/assets/advisor-view.js","utf8")
 .replace('from "./advisor-editions.js"', 'from "'+editionUrl+'"');
const {advisorChatMarkup,advisorResultsMarkup,ADVISOR_PROMPTS,ADVISOR_BALANCE_PROMPTS}=
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


test("the UI discloses whether the local AI is really available",()=>{
 const local=advisorChatMarkup({history:[],aiMode:"local_ai",lang:"fr"},L,e);
 assert.match(local,/advisorAIActive/);
 assert.match(local,/advisor-ai-dot active/);
 const guided=advisorChatMarkup({history:[],aiMode:"guided",lang:"fr"},L,e);
 assert.match(guided,/advisorAIGuided/);
 assert.doesNotMatch(guided,/advisor-ai-dot active/);
 const fallback=advisorChatMarkup({history:[],aiMode:"guided_fallback",lang:"fr"},L,e);
 assert.match(fallback,/advisorAIFallback/);
 assert.doesNotMatch(fallback,/advisor-ai-dot active/);
});


test("three discovery modes are real conversational actions, translated and selected",()=>{
 assert.equal(Object.keys(ADVISOR_BALANCE_PROMPTS.fr).length,3);
 assert.match(ADVISOR_BALANCE_PROMPTS.fr.EXPLORE,/Surprends-moi/);
 const item={id:1,title:"Detective Story",genres:["Mystery"],themes:["Detective"],
  mood_matches:{genres:["Mystery"],themes:["Detective"]},
  variety_evidence:["Detective"],narrative_matches:[]};
 const html=advisorResultsMarkup({count:1,context:{recommendation_balance:"EXPLORE"},
  recommendations:[item]},{L,e,tr:e,poster:()=>"",rating:()=>"",published:()=>""});
 assert.equal((html.match(/data-action="advisor-balance"/g)||[]).length,3);
 assert.match(html,/data-value="EXPLORE" aria-pressed="true"/);
 assert.match(html,/data-value="CLOSE" aria-pressed="false"/);
 assert.match(html,/advisorVarietyEvidence/);
 assert.match(html,/Detective/);
 assert.doesNotMatch(html,/selection_probability/);
});

test("variety evidence escapes catalog strings and refuses unknown HTML",()=>{
 const item={id:2,title:"A",mood_matches:{genres:["Mystery"]},
  variety_evidence:['<img src=x onerror=alert(1)>'],
  narrative_matches:[]};
 const html=advisorResultsMarkup({count:1,context:{recommendation_balance:"BALANCED"},
  recommendations:[item]},{L,e,tr:e,poster:()=>"",rating:()=>"",published:()=>""});
 assert.doesNotMatch(html,/<img src=x/);
 assert.match(html,/&lt;img src=x/);
 assert.match(html,/data-value="BALANCED" aria-pressed="true"/);
});


test("a first-click personalized surprise shows honest library evidence, not empty mood tags",()=>{
 assert.match(ADVISOR_PROMPTS.fr[2],/Surprends-moi/);
 assert.match(ADVISOR_PROMPTS.en[2],/Surprise me/);
 const manga={id:12,title:"A genuine library suggestion",
  genres:["Action"],themes:[],
  mood_matches:{genres:[],themes:[]},
  affinity_matches:{genres:["Action"],themes:[]},
  variety_evidence:[],french_recorded:false};
 const result={count:1,personalized:true,discovery_source:"library_tags",
               context:{recommendation_balance:"EXPLORE"},recommendations:[manga]};
 const html=advisorResultsMarkup(result,{
   L,e,tr:e,poster:()=>"<span>poster</span>",
   rating:()=>"",published:()=>"",
 });
 assert.match(html,/moodAffinity/);
 assert.match(html,/Action/);
 assert.doesNotMatch(html,/advisorProof/);
 assert.match(html,/data-go="\/manga\/12"/);
});


test("advisor evidence audit discloses real metrics without inventing a success rate",()=>{
 const manga={id:51,title:"Real title",genres:["Mystery"],themes:["Psychological"],
  mood_matches:{genres:["Mystery"],themes:[]},
  affinity_matches:{genres:["Mystery"],themes:[]},
  narrative_matches:[],variety_evidence:[]};
 const reply={count:1,personalized:true,context:{recommendation_balance:"BALANCED"},
  recommendations:[manga],quality_diagnostic:{
    scope:"displayed_catalogue_results_only",mode:"BALANCED",
    examined_count:42,returned_count:1,unique_manga_count:1,
    tag_evidence_count:1,unique_recorded_tags:2,
    affinity_evidence_count:1,mean_pairwise_tag_overlap:null,
    candidate_pool_capped:false
  }};
 const markup=advisorResultsMarkup(reply,{
  L,e,tr:e,poster:()=>"",rating:()=>"",published:()=>"",
 });
 assert.match(markup,/<details class="advisor-quality">/);
 assert.match(markup,/advisorQualityShown/);
 assert.match(markup,/advisorQualityExamined/);
 assert.match(markup,/42/);
 assert.match(markup,/advisorQualityCaution/);
 assert.doesNotMatch(markup,/NaN|undefined|Infinity|compatibilityPercentage/);
 reply.quality_diagnostic.mean_pairwise_tag_overlap=0.375;
 reply.quality_diagnostic.candidate_pool_capped=true;
 const limited=advisorResultsMarkup(reply,{
  L,e,tr:e,poster:()=>"",rating:()=>"",published:()=>"",
 });
 assert.match(limited,/38%/);
 assert.match(limited,/advisorQualityWindow/);
});
