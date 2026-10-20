import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source=readFileSync("apps/web/assets/wikidata-view.js","utf8");
const {wikidataFactsMarkup}=await import(
  "data:text/javascript;charset=utf-8,"+encodeURIComponent(source)
);
const escape=value=>String(value??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const context={escape,lang:"fr"};
const example={
  status:"MATCHED",match_basis:"exact_mal_manga_id_P4087",
  wikidata_id:"Q12345",source_url:"https://www.wikidata.org/wiki/Q12345",
  label_fr:"L'Attaque des Titans",description_fr:"manga japonais",
  genres_fr:["action","mystère"],french_publisher_title_verified:false,
  description_is_plot_synopsis:false,editions_verified:false,
};

test("exact MAL linked French label has visible evidence and caveats",()=>{
  const html=wikidataFactsMarkup(example,context);
  assert.match(html,/L&#39;Attaque des Titans/);
  assert.match(html,/Wikidata/);
  assert.match(html,/P4087/);
  assert.match(html,/pas un synopsis complet/);
  assert.match(html,/action · mystère/);
  assert.match(html,/href="https:\/\/www.wikidata.org\/wiki\/Q12345"/);
  assert.doesNotMatch(html,/data-action="edition-confirm"/);
  assert.doesNotMatch(html,/class="edition-item/);
});

test("missing and ambiguous source are not fabricated into publication evidence",()=>{
  assert.equal(wikidataFactsMarkup(null,context),"");
  assert.equal(wikidataFactsMarkup({status:"NOT_SEARCHED"},context),"");
  const ambiguous=wikidataFactsMarkup({status:"AMBIGUOUS",label_fr:"Fake"},context);
  assert.match(ambiguous,/Plusieurs correspondances/);
  assert.doesNotMatch(ambiguous,/Fake/);
  const err=wikidataFactsMarkup({status:"ERROR"},context);
  assert.match(err,/Service indisponible/);
});

test("escaped hostile fields and restricted Wikidata URLs",()=>{
  const html=wikidataFactsMarkup({
    ...example,label_fr:'<img src=x onerror="alert(1)">',
    description_fr:'<script>alert(1)</script>',
    genres_fr:['<svg onload="alert(1)">'],
    source_url:"https://www.wikidata.org.attacker.test/wiki/Q12345",
  },context);
  assert.doesNotMatch(html,/href=/);
  assert.doesNotMatch(html,/<img /);
  assert.doesNotMatch(html,/<script>/);
  assert.doesNotMatch(html,/<svg /);
});

test("English interface labels source as community, not commercial French title",()=>{
  const html=wikidataFactsMarkup(example,{...context,lang:"en"});
  assert.match(html,/Not a full synopsis or proof of a French publication/);
  assert.match(html,/French label/);
});
