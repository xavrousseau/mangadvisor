import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src=readFileSync("apps/web/assets/fr-discovery-view.js","utf8");
const {frDiscoverySearchForm,frDiscoveryResults}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(src));
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;",
}[c]));
const dictionary={frSearchTitle:"Explorer les livres français",frSearchLabel:"Titre français",
  frSearchResults:"Notices trouvées",frSearchRecord:"Notice BnF",
  frSearchAlready:"Déjà associé",frSearchVerify:"Vérifier cet ISBN",frSearchNone:"Aucune notice"};
const tr=k=>dictionary[k]||k;
const data={query:"Naruto",items:[
 {isbn13:"9782871294146",title_fr:"Naruto Tome 1",
   publisher_fr:"Kana",source_url:"https://catalogue.bnf.fr/ark:/12148/cb1111x",
   source_checked_at:"2026-10-18T10:00:00Z",verified_isbn:true,
   language_status:"french"},
 {isbn13:"9782344074282",title_fr:"Naruto Tome 2",
   publisher_fr:"Kana",source_url:"https://catalogue.bnf.fr/ark:/12148/cb2222x",
   verified_isbn:true},
]};

test("search form starts from an editable series title",()=>{
 const html=frDiscoverySearchForm('Naruto',tr,esc);
 assert.match(html,/id="fr-discovery-query"/);
 assert.match(html,/name="title"/);
 assert.match(html,/value="Naruto"/);
 assert.match(html,/id="fr-discovery-results"/);
});

test("search results distinguish registered books from unlinked ISBNs",()=>{
 const html=frDiscoveryResults(data,new Set(["9782871294146"]),tr,esc);
 assert.match(html,/Déjà associé/);
 assert.match(html,/frSearchLanguage_french/);
 assert.match(html,/frSearchLanguage_unknown/);
 assert.match(html,/data-action="fr-discovery-select" data-isbn="9782344074282"/);
 assert.doesNotMatch(html,/data-action="fr-discovery-select" data-isbn="9782871294146"/);
 assert.match(html,/Vérifier cet ISBN/);
});

test("untrusted BnF title, query and links cannot inject code",()=>{
 const unsafe=structuredClone(data);
 unsafe.items[1].title_fr='<img src=x onerror="bad()">';
 unsafe.items[1].source_url="javascript:alert(1)";
 const html=frDiscoveryResults(unsafe,new Set(),tr,esc);
 assert.match(html,/&lt;img/);
 assert.doesNotMatch(html,/<img src|href="javascript:/);
 const form=frDiscoverySearchForm('"><script>x()</script>',tr,esc);
 assert.doesNotMatch(form,/<script>/);
 assert.match(form,/&lt;script&gt;/);
});

test("incomplete results never suggest full publication coverage",()=>{
 const empty=frDiscoveryResults({items:[],is_exhaustive:false},new Set(),tr,esc);
 assert.match(empty,/frSearchWarning/);
 assert.match(empty,/Aucune notice/);
 assert.doesNotMatch(empty,/data-action="fr-discovery-select"/);
});

test("unverified ISBN or forged non-BnF links are omitted",()=>{
 const input={items:[
  {verified_isbn:false,isbn13:"9782344074282",title_fr:"Fake"},
  {verified_isbn:true,isbn13:"abc",title_fr:"Fake2"},
  {verified_isbn:true,isbn13:"9782871294146",title_fr:"Valid",
   source_url:"https://evil.test/ark:/12148/cb1234x"},
 ]};
 const html=frDiscoveryResults(input,new Set(),tr,esc);
 assert.doesNotMatch(html,/Fake/);
 assert.match(html,/Valid/);
 assert.doesNotMatch(html,/evil.test/);
});
