import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const source=readFileSync("apps/web/assets/physical-inventory-view.js","utf8");
const {physicalInventoryMarkup}=
  await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
const escape=value=>String(value??"").replace(/[&<>"']/g,ch=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[ch]));
const t=(_lang,key)=>key;
const declared={
 scope:"owner_declared_unverified_editions_not_isbn_books",
 summary:{works:1,edition_entries:2,main_volumes:76,identical_duplicates:0,
          other_editions_unidentified:0,physical_total_declared:76},
 items:[
  {manga_id:20,work_title:"Dragon Ball",entry_title:"Dragon Ball (42 tomes)",
   edition_declared:"Pastel",main_volumes:42,duplicate_copies:0,
   other_editions_unknown:0,format_hint:null},
  {manga_id:20,work_title:"Dragon Ball",entry_title:"Dragon Ball (34 tomes)",
   edition_declared:"Deluxe",main_volumes:34,duplicate_copies:0,
   other_editions_unknown:0,format_hint:"PERFECT_A_VERIFIER"},
 ]
};

test("two physical editions are separate while canonical work and counts are not doubled",()=>{
 const html=physicalInventoryMarkup(declared,"fr",t,escape);
 assert.equal((html.match(/class="physical-work" /g)||[]).length,1);
 assert.equal((html.match(/class="physical-edition-entry"/g)||[]).length,2);
 assert.match(html,/Pastel/);
 assert.match(html,/Deluxe/);
 assert.match(html,/physicalMain <strong>42<\/strong>/);
 assert.match(html,/physicalMain <strong>34<\/strong>/);
 assert.match(html,/physicalWorks<\/small><strong>1<\/strong>/);
 assert.match(html,/physicalEditions<\/small><strong>2<\/strong>/);
 assert.match(html,/data-go="\/manga\/20"/);
 assert.match(html,/PERFECT_A_VERIFIER/);
 assert.doesNotMatch(html,/ISBN vérifié|ISBN-13/);
});

test("manga details show the physical owner inventory without merging it with book-level ISBNs",()=>{
 const html=physicalInventoryMarkup(declared,"fr",t,escape,{compact:true});
 assert.equal((html.match(/class="physical-edition-entry"/g)||[]).length,2);
 assert.doesNotMatch(html,/physical-inventory-stats/);
 assert.match(html,/physicalScopeNote/);
});

test("source titles and declared labels are escaped rather than executed",()=>{
 const payload=structuredClone(declared);
 payload.items[0].edition_declared='<img src=x onerror="alert(1)">';
 payload.items[0].entry_title='<svg onload="alert(1)">';
 payload.items[1].format_hint='<script>throw 5</script>';
 const html=physicalInventoryMarkup(payload,"fr",t,escape);
 assert.match(html,/&lt;img src=x/);
 assert.match(html,/&lt;svg onload/);
 assert.match(html,/&lt;script&gt;/);
 assert.doesNotMatch(html,/<img src=|<svg onload|<script>/);
});

test("empty and invalid evidence remains empty or clearly unavailable",()=>{
 const empty=physicalInventoryMarkup({
  scope:declared.scope,items:[],summary:{}},
  "fr",t,escape);
 assert.match(empty,/physicalEmpty/);
 const unsupported=physicalInventoryMarkup({scope:"hallucinated",items:declared.items},
   "fr",t,escape);
 assert.match(unsupported,/physicalUnavailable/);
 assert.doesNotMatch(unsupported,/Pastel/);
});
