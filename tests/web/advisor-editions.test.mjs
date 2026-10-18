import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const src=readFileSync("apps/web/assets/advisor-editions.js","utf8");
const {advisorFrenchEditionsMarkup,safeBnF}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(src));
const e=v=>String(v??"").replace(/[&<>"']/g,c=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const L=e;

const example={
 scope:"registered_isbns_only",registered_isbn_count:3,
 published_total_known:false,availability_checked:false,complete_french_series:null,
 registered_formats:[
  {edition_kind:"DELUXE",registered_isbn_count:2,known_volume_numbers:[1,3],
   publishers_fr:["Kana"],books_remaining:0,books_shown:[
   {title_fr:"Édition Deluxe 1",publisher_fr:"Kana",volume_number:1,isbn13:"9781234567804",
    source_url:"https://catalogue.bnf.fr/ark:/12148/cb12345678x",
    release_date_text:"2024"},
   {title_fr:"Édition Deluxe 3",publisher_fr:"Kana",volume_number:3,isbn13:"9781234567811",
    source_url:"https://phishing.example/ark:/12148/cb1"},
  ]},
  {edition_kind:"PERFECT",registered_isbn_count:1,known_volume_numbers:[1],
   publishers_fr:["Pika"],books_remaining:0,books_shown:[
   {title_fr:"Perfect 1",publisher_fr:"Pika",volume_number:1,isbn13:"9781234567828"}
  ]},
 ]
};

test("renders distinct edition groups, publishers, known volumes and ISBNs",()=>{
 const html=advisorFrenchEditionsMarkup(example,{L,e});
 assert.match(html,/editionDELUXE/);
 assert.match(html,/editionPERFECT/);
 assert.match(html,/Kana/);
 assert.match(html,/Pika/);
 assert.match(html,/9781234567804/);
 assert.match(html,/9781234567811/);
 assert.match(html,/9781234567828/);
 assert.match(html,/1, 3/);
 assert.match(html,/advisorEditionCaution/);
 assert.match(html,/rel="noopener noreferrer"/);
 assert.equal((html.match(/advisor-edition-group-head/g)||[]).length,2);
});

test("never renders remote non-BnF source links or HTML injection",()=>{
 const html=advisorFrenchEditionsMarkup(example,{L,e});
 assert.doesNotMatch(html,/href="https:\/\/phishing/);
 assert.equal(safeBnF("https://catalogue.bnf.fr/ark:/12148/cb12345678x"),
 "https://catalogue.bnf.fr/ark:/12148/cb12345678x");
 assert.equal(safeBnF("http://catalogue.bnf.fr/ark:/12148/cb12345678x"),null);
 assert.equal(safeBnF("https://catalogue.bnf.fr.evil.test/ark:/12148/cb12345678x"),null);
 assert.equal(safeBnF("javascript:alert(1)"),null);
 assert.equal(safeBnF("https://catalogue.bnf.fr/other"),null);
 const injected=structuredClone(example);
 injected.registered_formats[0].books_shown[0].title_fr='<svg onload=alert(1)>';
 injected.registered_formats[0].books_shown[0].publisher_fr='<img src=x>';
 const escaped=advisorFrenchEditionsMarkup(injected,{L,e});
 assert.doesNotMatch(escaped,/<svg onload|<img src=x/);
 assert.match(escaped,/&lt;svg/);
});

test("never represents unsupported registered edition completion as proven",()=>{
 assert.equal(advisorFrenchEditionsMarkup({scope:"catalog",registered_isbn_count:9},{L,e}),"");
 assert.equal(advisorFrenchEditionsMarkup({scope:"registered_isbns_only",registered_isbn_count:0},{L,e}),"");
 const withExtra=structuredClone(example);
 withExtra.registered_formats[0].books_remaining=11;
 const html=advisorFrenchEditionsMarkup(withExtra,{L,e});
 assert.match(html,/\+11/);
 assert.match(html,/advisorEditionMore/);
 assert.doesNotMatch(html,/13 tomes publiés|complete french series/i);
});
