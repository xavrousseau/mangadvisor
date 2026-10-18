import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source=readFileSync("apps/web/assets/unknown-isbn-view.js","utf8");
const {resolverMarkup,titleSearchSuggestion,isVerifiedIsbnRecord,EDITION_OPTIONS}=
  await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
const escape=value=>String(value).replace(/[&<>"']/g,c=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const texts=key=>key;
const record={
 isbn13:"9782344074282",title_fr:"Monster. Tome 1",
 publisher_fr:"Kana",author_fr:"Naoki Urasawa",
 source_url:"https://catalogue.bnf.fr/ark:/12148/cbtest",
 verified_isbn:true,edition_kind_suggested:"UNKNOWN",
};
const base={isbn:record.isbn13,record,query:"Monster",matches:[],
 selected:null,searched:false,kind:"UNKNOWN",volume:1};

test("an ISBN cannot be silently attached to a manga",()=>{
 const html=resolverMarkup(base,texts,escape);
 assert.match(html,/name="manga"/);
 assert.match(html,/Monster\. Tome 1/);
 assert.match(html,/collectionBnfSource/);
 assert.doesNotMatch(html,/data-action="bulk-resolve-confirm"/);
 assert.doesNotMatch(html,/bulk-resolver-confirm/);
});
test("only an explicitly selected manga enables a gated final confirmation",()=>{
 const html=resolverMarkup({...base,selected:{id:2,title:"Monster"},
   matches:[{id:2,title:"Monster"}],searched:true},texts,escape);
 assert.match(html,/data-action="bulk-resolve-select"/);
 assert.match(html,/bulk-resolve-ack/);
 assert.match(html,/data-action="bulk-resolve-confirm" disabled/);
 assert.match(html,/resolveAcknowledgement/);
 assert.match(html,/editionDELUXE/);
 assert.equal(EDITION_OPTIONS.includes("PERFECT"),true);
});
test("the volume number is never guessed or pre-filled when missing",()=>{
 const html=resolverMarkup({...base,volume:null,selected:{id:2,title:"Monster"},
   matches:[{id:2,title:"Monster"}],searched:true},texts,escape);
 assert.match(html,/id="bulk-resolve-volume"[^>]*value=""/);
 assert.match(html,/data-action="bulk-resolve-confirm" disabled/);
});
test("the BnF lookup must match the exact verified ISBN",()=>{
 assert.equal(isVerifiedIsbnRecord(record,record.isbn13),true);
 assert.equal(isVerifiedIsbnRecord({...record,isbn13:"9782871294146"},record.isbn13),false);
 assert.equal(isVerifiedIsbnRecord({...record,verified_isbn:false},record.isbn13),false);
 assert.equal(isVerifiedIsbnRecord(record,"<script>"),false);
 assert.equal(resolverMarkup({...base,isbn:'"><img onerror=alert(1)>'},texts,escape),"");
});
test("search hint is editable and never treated as a verified series match",()=>{
 assert.equal(titleSearchSuggestion("Monster. Tome 1"),"Monster");
 assert.equal(titleSearchSuggestion("Naruto, volume 05"),"Naruto");
 assert.equal(titleSearchSuggestion(""),"");
 const html=resolverMarkup({...base,query:"<script>evil</script>"},texts,escape);
 assert.doesNotMatch(html,/<script>/);
 assert.match(html,/&lt;script&gt;/);
});
test("untrusted French book titles and catalog candidates are escaped",()=>{
 const html=resolverMarkup({...base,record:{...record,title_fr:'<svg onload="evil()">'},
   matches:[{id:2,title:'<img src=x onerror=1>'}],searched:true,
   selected:{id:2,title:'<img src=x onerror=1>'}},texts,escape);
 assert.doesNotMatch(html,/<svg|<img src/);
 assert.match(html,/&lt;img src/);
 assert.match(html,/&lt;svg/);
});
test("no-match search provides honest empty state without confirm",()=>{
 const html=resolverMarkup({...base,matches:[],searched:true},texts,escape);
 assert.match(html,/resolveNoMangas/);
 assert.doesNotMatch(html,/data-action="bulk-resolve-confirm"/);
});
