import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const src=readFileSync("apps/web/assets/enrichment-view.js","utf8");
const {enrichmentPanel,enrichmentResults,reconcileEnrichment,mergeEnrichmentPages}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(src));
const e=v=>String(v??"").replace(/[&<>"']/g,x=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[x]));
const t=(_,key)=>key;
const isbn=(code,status,title="Naruto. Tome 1")=>({
 isbn13:code,title_fr:title,status:"CANDIDATE_UNCONFIRMED",
 registration_status:status,title_clue:"TITLE_WORDS_PRESENT",
 author_fr:"Masashi Kishimoto",publisher_fr:"Kana",
 edition_kind_suggested:"CLASSIC",
 source_url:"https://catalogue.bnf.fr/ark:/12148/cb12345678x",
});
const report={
 manga_id:1,searched_titles:["Naruto"],
 candidate_only:true,first_page_per_title_only:true,
 to_verify_count:1,registered_here_count:1,registered_other_count:1,
 items:[
  isbn("9782344074282","TO_VERIFY"),
  isbn("9782871294146","REGISTERED_HERE"),
  isbn("9781234567897","REGISTERED_OTHER"),
 ]
};

test("workshop requires user action; no auto saving or bulk association",()=>{
 const html=enrichmentPanel(e,t,"fr");
 assert.match(html,/id="fr-enrichment"/);
 assert.match(html,/data-action="enrich-discover"/);
 assert.doesNotMatch(html,/data-action="edition-confirm"|data-action="volume-owned"/);
});

test("registered ISBNs cannot be reverified through the UI",()=>{
 const html=enrichmentResults(report,e,t,"fr");
 assert.equal((html.match(/data-action="enrich-verify-isbn"/g)||[]).length,1);
 assert.equal((html.match(/class="enrich-candidate"/g)||[]).length,3);
 assert.match(html,/enrichAlreadyHere/);
 assert.match(html,/enrichAlreadyOther/);
 assert.match(html,/enrichConflictHelp/);
 assert.match(html,/enrichNotice/);
 assert.match(html,/9782344074282/);
});

test("confirming one ISBN changes local workflow status and preserves remaining",()=>{
 const updated=reconcileEnrichment(report,[{isbn13:"9782344074282"}]);
 assert.equal(updated.to_verify_count,0);
 assert.equal(updated.registered_here_count,2);
 assert.equal(updated.registered_other_count,1);
 assert.equal(updated.items[0].registration_status,"REGISTERED_HERE");
 assert.equal(report.items[0].registration_status,"TO_VERIFY");
 assert.equal((enrichmentResults(updated,e,t,"fr").match(/data-action="enrich-verify-isbn"/g)||[]).length,0);
});

test("no HTML injection or untrusted external links in candidate metadata",()=>{
 const malicious={
  ...report,items:[
   {...report.items[0],
     title_fr:'<img src=x onerror="alert(1)">',
     publisher_fr:"<script>alert(1)</script>",
     source_url:"javascript:alert(1)",
     title_clue:"<svg onload=alert(1)>",
   }
  ]
 };
 const html=enrichmentResults(malicious,e,t,"fr");
 assert.doesNotMatch(html,/<img src|<script>|<svg onload|href="javascript:/);
 assert.match(html,/&lt;img/);
 assert.match(html,/&lt;script/);
 assert.match(html,/enrichClueNO_TITLE_WORDS/);
 assert.match(html,/data-action="enrich-verify-isbn"/);
});

test("failed or absent search returns bounded empty message",()=>{
 const html=enrichmentResults({items:[],search_errors:["English title"],to_verify_count:0,
   registered_other_count:0,registered_here_count:0},e,t,"en");
 assert.match(html,/enrichEmpty/);
 assert.match(html,/enrichPartial/);
 assert.doesNotMatch(html,/enrich-verify-isbn/);
});


test("French title query is editable without creating a stored official alias",()=>{
 const html=enrichmentPanel(e,t,"fr");
 assert.match(html,/id="enrich-alt-title"/);
 assert.match(html,/maxlength="90"/);
 assert.match(html,/enrichAliasHelp/);
 assert.doesNotMatch(html,/data-action="edition-confirm"/);
});

test("formats are visually grouped but still unconfirmed and safe",()=>{
 const grouped={...report,items:[
  {...report.items[0],edition_kind_suggested:"DELUXE"},
  {...report.items[1],edition_kind_suggested:"CLASSIC"},
  {...report.items[2],edition_kind_suggested:"PERFECT"}],
  searched_titles:["Naruto","Naruto FR"],page:1,max_pages:3,has_more_pages:true};
 const html=enrichmentResults(grouped,e,t,"fr");
 assert.equal((html.match(/class="enrich-format-group"/g)||[]).length,3);
 assert.match(html,/editionDELUXE/);
 assert.match(html,/editionCLASSIC/);
 assert.match(html,/editionPERFECT/);
 assert.match(html,/Naruto FR/);
 assert.match(html,/data-action="enrich-more"/);
 assert.match(html,/enrichPagesLoaded/);
});

test("incremental pages dedupe ISBNs and preserve verified candidates",()=>{
 const p1={...report,page:1,max_pages:3,has_more_pages:true,
  items:[isbn("9782344074282","TO_VERIFY"),isbn("9782871294146","REGISTERED_HERE")]};
 const confirmed=reconcileEnrichment(p1,[{isbn13:"9782344074282"}]);
 const p2={...report,page:2,has_more_pages:false,
  items:[isbn("9782344074282","TO_VERIFY"),isbn("9781234567804","TO_VERIFY")],
  to_verify_count:2,registered_here_count:0,registered_other_count:0};
 const merged=mergeEnrichmentPages(confirmed,p2);
 assert.equal(merged.items.length,3);
 assert.equal(merged.registered_here_count,2);
 assert.equal(merged.to_verify_count,1);
 assert.equal(merged.pages_loaded,2);
 assert.equal(merged.has_more_pages,false);
 assert.equal((enrichmentResults(merged,e,t,"fr").match(/data-action="enrich-verify-isbn"/g)||[]).length,1);
 assert.doesNotMatch(enrichmentResults(merged,e,t,"fr"),/data-action="enrich-more"/);
 assert.equal(confirmed.items.length,2);
});

test("new query or different manga never merges old BnF results",()=>{
 const next={...report,manga_id:2,searched_titles:["Naruto FR"],page:1,items:[]};
 const result=mergeEnrichmentPages(report,next);
 assert.equal(result,next);
 const changed={...report,searched_titles:["Alternative title"],page:1,items:[]};
 assert.equal(mergeEnrichmentPages(report,changed),changed);
});

test("all aliases and BnF titles remain escaped in page summaries",()=>{
 const suspicious={...report,searched_titles:["Naruto",'<img src=x onerror=alert(1)>'],
  page:1,has_more_pages:true};
 const html=enrichmentResults(suspicious,e,t,"fr");
 assert.doesNotMatch(html,/<img src/);
 assert.match(html,/&lt;img/);
});
