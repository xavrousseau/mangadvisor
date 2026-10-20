import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync("apps/web/assets/bnf-candidates-view.js", "utf8");
const { bnfCachedCandidatesMarkup } =
  await import("data:text/javascript;charset=utf-8," + encodeURIComponent(src));
const escape = value => String(value ?? "").replace(/[&<>"']/g, ch=>({
  "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;",
}[ch]));
const options = {escape, lang:"fr"};
const record = {
  isbn13:"9782871294146", title_fr:"Naruto Tome 1",
  publisher_fr:"Kana", author_fr:"Masashi Kishimoto",
  source_url:"https://catalogue.bnf.fr/ark:/12148/cb12345678x",
  registration_status:"TO_VERIFY", title_clue_rank:2
};

test("unverified BnF records are visibly separate and require manual ISBN verification",()=>{
  const html=bnfCachedCandidatesMarkup({
    status:"CHECKED",candidate_count:1,items:[record],
  },options);
  assert.match(html,/Notices BnF à examiner/);
  assert.match(html,/pas des ISBN associés à cette série/);
  assert.match(html,/Naruto Tome 1/);
  assert.match(html,/9782871294146/);
  assert.match(html,/data-action="bnf-candidate-verify"/);
  assert.match(html,/Notice BnF/);
  assert.doesNotMatch(html,/data-action="volume-owned"/);
  assert.doesNotMatch(html,/data-action="edition-confirm"/);
});

test("registered records are never offered as fresh suggestions",()=>{
  for(const status of ["REGISTERED_HERE","REGISTERED_OTHER"]){
    const html=bnfCachedCandidatesMarkup({
      status:"CHECKED",candidate_count:1,items:[{...record,registration_status:status}]
    },options);
    assert.doesNotMatch(html,/data-action="bnf-candidate-verify"/);
  }
});

test("hostile catalogue fields are escaped; only exact official BnF URLs are linked",()=>{
  const html=bnfCachedCandidatesMarkup({
    status:"CHECKED",candidate_count:1,items:[{
      ...record,title_fr:'<img src=x onerror="alert(1)">',
      publisher_fr:'<script>alert(1)</script>',
      source_url:"https://catalogue.bnf.fr.attacker.test/ark:/12148/cb12345678x",
    }]
  },options);
  assert.match(html,/&lt;img src/);
  assert.match(html,/&lt;script&gt;/);
  assert.doesNotMatch(html,/<img /);
  assert.doesNotMatch(html,/<script>/);
  assert.doesNotMatch(html,/href=/);
});

test("missing and failed batches never fabricate a French edition",()=>{
  assert.equal(bnfCachedCandidatesMarkup(null,options),"");
  assert.equal(bnfCachedCandidatesMarkup({status:"NOT_SEARCHED"},options),"");
  const html=bnfCachedCandidatesMarkup({
    status:"ERROR",candidate_count:0,items:[]
  },options);
  assert.match(html,/Recherche indisponible/);
  assert.doesNotMatch(html,/data-action="bnf-candidate-verify"/);
});
