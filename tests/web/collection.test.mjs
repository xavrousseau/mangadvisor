import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const src=readFileSync("apps/web/assets/collection-view.js","utf8");
const { collectionPanel, editionPreview, EDITION_KINDS, groupedEditions }=
  await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(src));
const escape = value => String(value??"").replace(/[&<>"']/g, ch=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[ch]));
const texts={collectionTitle:"Éditions françaises et mes tomes",collectionOwned:"Possédé",
  collectionRead:"Lu",collectionMissing:"Manquant",collectionTome:"Tome",
  collectionIsbn:"ISBN",collectionBnfSource:"Notice BnF",
  collectionSearchIsbn:"Recherche ISBN",collectionConfirm:"Confirmer",
  collectionLegacy:"Compteurs historiques"};
const t=(_,key)=>texts[key]||key;
const example={manga_id:1,count:2,owned_books:1,read_books:2,missing_known_books:1,
 editions:[
  {id:1,title_fr:"Naruto Tome 1",edition_kind:"CLASSIC",edition_kind_origin:"USER_CONFIRMED",
    volume_number:1,isbn13:"9782871294146",source_url:"https://catalogue.bnf.fr/ark:/12148/cb123",
    source_checked_at:"2026-10-18T14:00:00Z",is_owned:true,is_read:true,
    publisher_fr:"Kana",author_fr:"Masashi Kishimoto"},
  {id:2,title_fr:"Naruto Deluxe Tome 1",edition_kind:"DELUXE",edition_kind_origin:"BNF_TITLE",
    volume_number:1,isbn13:"9782344074282",is_owned:false,is_read:true,source_url:"https://catalogue.bnf.fr/ark:/12148/cb456"}
 ]};

test("classic and deluxe editions are distinct; owned/read values stay independent",()=>{
 const output=collectionPanel(example,{owned_volumes:20,read_volumes:7},"fr",t,escape);
 assert.match(output,/Naruto Deluxe Tome 1/);
 assert.match(output,/Naruto Tome 1/);
 assert.match(output,/9782871294146/);
 assert.match(output,/aria-pressed="false"/);
 assert.match(output,/aria-pressed="true"/);
 assert.match(output,/Compteurs historiques/);
 assert.match(output,/collection-stats/);
 assert.equal(EDITION_KINDS.includes("PERFECT"),true);
});

test("untrusted source content is escaped and links restricted",()=>{
 const data=structuredClone(example);
 data.editions[0].title_fr='<img src=x onerror=alert(1)>';
 data.editions[0].source_url="javascript:alert(1)";
 const output=collectionPanel(data,null,"fr",t,escape);
 assert.match(output,/&lt;img src/);
 assert.doesNotMatch(output,/<img src/);
 assert.doesNotMatch(output,/href="javascript:/);
});

test("confirmed ISBN preview does not auto-add a volume",()=>{
 const preview=editionPreview({
  title_fr:"Bleach Deluxe 1",isbn13:"9782344074282",edition_kind_suggested:"DELUXE",
  source_url:"https://catalogue.bnf.fr/ark:/12148/cb123",
 },"fr",t,escape);
 assert.match(preview,/value="DELUXE" selected/);
 assert.match(preview,/collectionConfirmTitle/);
 assert.match(preview,/data-action="edition-confirm"/);
 assert.doesNotMatch(preview,/data-action="volume-owned"/);
});


test("classic, perfect and deluxe are distinct visual groups",()=>{
 const data=structuredClone(example);
 data.french_overview={
   source_scope:"verified_registered_books_only",
   reference_count:2, publishers_fr:["Kana"],authors_fr:["Masashi Kishimoto"],
 };
 const html=collectionPanel(data,null,"fr",t,escape);
 assert.match(html,/class="fr-notices"/);
 assert.match(html,/Kana/);
 assert.match(html,/data-edition-kind="CLASSIC"/);
 assert.match(html,/data-edition-kind="DELUXE"/);
 assert.match(html,/2026-10-18/);
 const grouped=groupedEditions(data.editions);
 assert.deepEqual(grouped.map(x=>x.kind),["CLASSIC","DELUXE"]);
 assert.equal(grouped[0].books.length,1);
});
test("manual ISBN preview requires an explicit volume number",()=>{
 const preview=editionPreview({
   title_fr:"Monster, tome 3",isbn13:"9782871294146",edition_kind_suggested:"UNKNOWN",
 }, "fr",t,escape);
 assert.match(preview,/id="edition-number"[^>]*value=""[^>]*required/);
 assert.doesNotMatch(preview,/id="edition-number"[^>]*value="1"/);
});
test("no French records means no invented publishers or official series title",()=>{
 const html=collectionPanel({editions:[],french_overview:{publishers_fr:["Fake"]}},null,"fr",t,escape);
 assert.doesNotMatch(html,/Fake/);
 assert.doesNotMatch(html,/class="fr-notices"/);
});


test("progress is explicitly scoped to recorded ISBNs and updates for each edition",()=>{
 const data=structuredClone(example);
 data.edition_progress=[
   {edition_kind:"CLASSIC",known_books:1,owned_books:1,read_books:1,
     owned_pct_of_known:100,read_pct_of_known:100,published_total_known:false},
   {edition_kind:"DELUXE",known_books:1,owned_books:0,read_books:1,
     owned_pct_of_known:0,read_pct_of_known:100,published_total_known:false},
 ];
 const markup=collectionPanel(data,null,"fr",t,escape);
 assert.match(markup,/class="edition-progress"/);
 assert.match(markup,/progressNoPublishedTotal/);
 assert.match(markup,/aria-label="collectionOwned" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100"/);
 assert.match(markup,/aria-label="collectionOwned" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"/);
 assert.match(markup,/style="width:100%"/);
 assert.match(markup,/style="width:0%"/);
});
test("invalid server progress percentages are bounded and cannot inject CSS",()=>{
 const data=structuredClone(example);
 data.edition_progress=[{
  edition_kind:"CLASSIC",known_books:1,
  owned_pct_of_known:"9000; background:url(javascript:evil())",
  read_pct_of_known:-500,
 }];
 const markup=collectionPanel(data,null,"fr",t,escape);
 assert.doesNotMatch(markup,/javascript:evil/);
 assert.match(markup,/style="width:0%"/);
});
