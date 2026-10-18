import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const source=readFileSync("apps/web/assets/bibliography-view.js","utf8");
const {bibliographyPanel,bibliographyResults}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
const escape=v=>String(v??"").replace(/[&<>"']/g,x=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[x]));
const t=(_,key)=>key;
const item={isbn13:"9782871294146",title_fr:"Monster. Tome 1",
 author_fr:"Naoki Urasawa",publisher_fr:"Kana",release_date_text:"2001",
 source_url:"https://catalogue.bnf.fr/ark:/12148/cb12345678x",
 source_checked_at:"2026-10-18T00:00:00Z",language_recorded:"français",
 status:"CANDIDATE_UNCONFIRMED",manga_match_verified:false};
test("search widget is editable; not an automatic edition import",()=>{
 const out=bibliographyPanel(escape,t,"fr","Monster");
 assert.match(out,/id="fr-bibliography-form"/);
 assert.match(out,/name="title"/);
 assert.match(out,/biblioSuggestion/);
 assert.doesNotMatch(out,/data-action="edition-confirm"/);
});
test("title search results remain visually unconfirmed",()=>{
 const out=bibliographyResults({candidate_only:true,exhaustive:false,items:[item]},escape,t,"fr");
 assert.match(out,/biblioCandidate/);
 assert.match(out,/biblioResultsDisclaimer/);
 assert.match(out,/data-action="biblio-verify-isbn"/);
 assert.match(out,/9782871294146/);
 assert.match(out,/2001/);
 assert.doesNotMatch(out,/data-action="volume-owned"/);
});
test("no record is honestly empty instead of invented published volumes",()=>{
 const out=bibliographyResults({items:[],exhaustive:false},escape,t,"en");
 assert.match(out,/biblioNoResults/);
 assert.match(out,/biblioResultsDisclaimer/);
});
test("URLs restricted to the BnF catalog; malicious fields escaped",()=>{
 const suspicious={...item,title_fr:"<img src=x onerror=alert(1)>",
  source_url:"javascript:alert(2)",publisher_fr:'<script>alert(3)</script>'};
 const out=bibliographyResults({items:[suspicious]},escape,t,"fr");
 assert.doesNotMatch(out,/<img src|<script>|href="javascript:/);
 assert.match(out,/&lt;img src/);
 assert.match(out,/&lt;script&gt;/);
});
test("unconfirmed or invalid ISBN input cannot be offered for selection",()=>{
 const rejected=bibliographyResults({items:[
  {...item,isbn13:"<script>"},
  {...item,status:"NOT_A_CANDIDATE"}
 ]},escape,t,"fr");
 assert.doesNotMatch(rejected,/data-action="biblio-verify-isbn"/);
 assert.match(rejected,/biblioNoResults/);
});
