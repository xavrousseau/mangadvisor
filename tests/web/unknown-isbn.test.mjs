import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

async function load(path){
 const code=readFileSync(path,"utf8");
 return import("data:text/javascript;charset=utf-8,"+encodeURIComponent(code));
}
const {unknownIsbnWizardMarkup,EDITION_CHOICES}=await load("apps/web/assets/unknown-isbn-view.js");
const {csvPreviewMarkup}=await load("apps/web/assets/bulk-import-view.js");
const escape=value=>String(value??"").replace(/[&<>"']/g,c=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const translate=key=>key;
const book={
 isbn13:"9782344074282",title_fr:"Édition française — Tome 3",
 author_fr:"Auteur",publisher_fr:"Éditeur",source_url:"https://catalogue.bnf.fr/ark:/12148/cb12345",
 verified_isbn:true,edition_kind_suggested:"PERFECT"
};
const state={
 isbn:book.isbn13,record:book,matches:[],selectedId:null,query:"",
 searched:false,loading:false,error:""
};

test("unknown CSV row has contextual verify button, known one does not",()=>{
 const output=csvPreviewMarkup({matched:1,unknown:1,to_update:0,errors:[],items:[
  {isbn13:"9782871294146",match:"EXACT_ISBN",title_fr:"Naruto",edition_kind:"CLASSIC",volume_number:1},
  {isbn13:book.isbn13,match:"UNKNOWN"},
 ]},translate,escape);
 assert.equal((output.match(/data-action="resolve-unknown"/g)||[]).length,1);
 assert.match(output,/data-isbn="9782344074282"/);
 assert.match(output,/data-action="bulk-apply"/);
});

test("BnF verification alone does not choose a manga or default to tome 1",()=>{
 const html=unknownIsbnWizardMarkup(state,translate,escape);
 assert.match(html,/Notice/); // BnF text in the source label is provided by localization key.
 assert.match(html,/Édition française — Tome 3/);
 assert.match(html,/catalogue.bnf.fr/);
 assert.doesNotMatch(html,/data-action="resolve-confirm-edition"/);
 assert.doesNotMatch(html,/value="1"/);
 assert.equal(EDITION_CHOICES.includes("DELUXE"),true);
});

test("confirmation requires explicit manga selection and volume entry",()=>{
 const found={...state,query:"Naruto",searched:true,
   matches:[{id:1,title:"Naruto",title_japanese:"ナルト"},{id:3,title:"Nana"}]};
 const unselected=unknownIsbnWizardMarkup(found,translate,escape);
 assert.match(unselected,/data-action="resolve-select-series"/);
 assert.doesNotMatch(unselected,/data-action="resolve-confirm-edition"/);
 const selected=unknownIsbnWizardMarkup({...found,selectedId:1},translate,escape);
 assert.match(selected,/aria-pressed="true"/);
 assert.match(selected,/value="PERFECT" selected/);
 assert.match(selected,/id="resolve-volume-number"/);
 assert.match(selected,/data-action="resolve-confirm-edition"/);
 assert.match(selected,/placeholder="1" required/);
});

test("untrusted metadata and series names are escaped; external links restricted",()=>{
 const html=unknownIsbnWizardMarkup({...state,record:{
  ...book,title_fr:"<script>alert(1)</script>",publisher_fr:'"><img src=x onerror=alert(1)>',
  source_url:"https://evil.example/steal",
 },matches:[{id:1,title:"<svg onload=alert(1)>"}],searched:true,selectedId:1},
 translate,escape);
 assert.doesNotMatch(html,/<script|<svg onload|<img src/);
 assert.match(html,/&lt;script&gt;/);
 assert.match(html,/&lt;svg onload/);
 assert.doesNotMatch(html,/href="https:\/\/evil/);
});

test("invalid or empty ISBN does not render a wizard",()=>{
 assert.equal(unknownIsbnWizardMarkup({isbn:"abc",record:book},translate,escape),"");
 assert.equal(unknownIsbnWizardMarkup(null,translate,escape),"");
});
