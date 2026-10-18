import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const source=readFileSync("apps/web/assets/bulk-import-view.js","utf8");
const { csvPreviewMarkup, reconciliationMarkup }=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
const escape=value=>String(value).replace(/[&<>"']/g,c=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;",
}[c]));
const labels=key=>key;
test("known ISBN can be confirmed, unknown ISBN is visibly skipped",()=>{
 const p={matched:1,unknown:1,to_update:1,errors:[],items:[
  {match:"EXACT_ISBN",isbn13:"9782871294146",edition_id:1,manga_id:1,
   title_fr:"Naruto Tome 1",edition_kind:"CLASSIC",volume_number:1,is_owned:true,is_read:false},
  {match:"UNKNOWN",isbn13:"9782344074282",is_owned:true,is_read:false},
 ]};
 const h=csvPreviewMarkup(p,labels,escape);
 assert.match(h,/Naruto Tome 1/);
 assert.match(h,/9782344074282/);
 assert.match(h,/bulkUnknown/);
 assert.match(h,/data-action="bulk-apply"/);
});
test("no match means no import confirmation button",()=>{
 const h=csvPreviewMarkup({matched:0,unknown:1,to_update:0,errors:[],
  items:[{match:"UNKNOWN",isbn13:"9782344074282"}]},labels,escape);
 assert.doesNotMatch(h,/data-action="bulk-apply"/);
});
test("malicious CSV and metadata cannot create executable html",()=>{
 const h=csvPreviewMarkup({matched:1,unknown:0,to_update:1,
 errors:[{line:3,message:'<img src=x onerror="alert(1)">'}],
 items:[{match:"EXACT_ISBN",title_fr:"<script>x</script>",isbn13:"9782871294146",
  edition_kind:"CLASSIC",volume_number:1}]},labels,escape);
 assert.doesNotMatch(h,/<script>|<img src/);
 assert.match(h,/&lt;script&gt;/);
 assert.match(h,/&lt;img src/);
});
test("legacy counts are contrasted, not added to precise ISBN tracking",()=>{
 const h=reconciliationMarkup({
  legacy_totals:{owned:20,read:15},isbn_totals:{known:3,owned:2,read:1},
  items:[{manga_id:1,title:"Naruto",legacy_owned:20,legacy_read:15,
    known_books:3,owned_books:2,read_books:1}]
 },labels,escape);
 assert.match(h,/bulkLegacy/);
 assert.match(h,/bulkVerified/);
 assert.match(h,/20 \/ 15/);
 assert.match(h,/2 \/ 1/);
 assert.match(h,/data-go="\/manga\/1"/);
});
