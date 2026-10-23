import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source=readFileSync("apps/web/assets/inventory-resolution-view.js","utf8");
const {inventoryResolverMarkup}=await import(
  "data:text/javascript;charset=utf-8,"+encodeURIComponent(source)
);
const escape=value=>String(value??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const pending={
 source_key:"Inventaire!A29",entry_title:"Dragon Ball (34 tomes)",
 edition_declared:"Deluxe",main_volumes:34,duplicate_copies:0,
 other_editions_unknown:0
};
const manga={
 id:15,title:"Dragon Ball",title_english:"Dragon Ball",
 manga_type:"Manga",volumes:42,source_mal_id:42
};
const base={
 sourceKey:"Inventaire!A29",pending,query:"Dragon Ball",items:[
  {...manga,suggestion_kind:"EXACT_TITLE"}
 ],searched:true,loading:false,message:"",
};

test("manual series and edition confirmation does not imply ISBNs or individual volumes",()=>{
 const html=inventoryResolverMarkup({
  ...base,review:{
   source:pending,manga,edition_key:"deluxe",
   confirmation_token:"a".repeat(64),
  }
 },{escape,lang:"fr"});
 assert.match(html,/data-action="pending-match-select"/);
 assert.match(html,/data-id="15"/);
 assert.match(html,/Dragon Ball/);
 assert.match(html,/Deluxe/);
 assert.match(html,/34 tomes principaux/);
 assert.match(html,/Je confirme ce rapprochement/);
 assert.match(html,/data-action="pending-match-confirm" disabled/);
 assert.match(html,/Cela n&#39;ajoute ni ISBN/);
 assert.doesNotMatch(html,/data-action="edition-confirm"/);
 assert.doesNotMatch(html,/data-action="volume-owned"/);
});
test("pending manga titles and source labels are HTML escaped",()=>{
 const markup=inventoryResolverMarkup({
  ...base,pending:{...pending,entry_title:'<img src=x onerror="alert(1)">'},
  items:[{...manga,title:'<script>alert(1)</script>'}],
  review:null
 },{escape});
 assert.match(markup,/&lt;img/);
 assert.match(markup,/&lt;script&gt;/);
 assert.doesNotMatch(markup,/<img /);
 assert.doesNotMatch(markup,/<script>/);
});
test("initial asynchronous search cannot race with owner typing",()=>{
 const html=inventoryResolverMarkup({...base,loading:true,items:[]},{
  escape,lang:"fr"
 });
 assert.match(html,/id="pending-match-query"[^>]*disabled/);
 assert.match(html,/type="submit" disabled/);
 const ready=inventoryResolverMarkup({...base,loading:false},{
  escape,lang:"fr"
 });
 assert.doesNotMatch(ready,/id="pending-match-query"[^>]*disabled/);
});
test("empty draft adds no fake selected manga",()=>{
 assert.equal(inventoryResolverMarkup(null,{escape}),"");
 const html=inventoryResolverMarkup({
  ...base,items:[],searched:true,review:null,
 },{escape,lang:"fr"});
 assert.match(html,/Aucun résultat/);
 assert.doesNotMatch(html,/pending-match-confirm/);
});

test("already counted manga requires an explicit archival decision and review",()=>{
 const html=inventoryResolverMarkup({
  ...base,reviewMode:"",review:{
   source:pending,manga,edition_key:"deluxe",
   confirmation_token:"a".repeat(64),
   same_edition_exists:true,
   allowed_actions:["MARK_DUPLICATE"],
   existing_declarations:[{
     edition_key:"deluxe",edition_declared:"Deluxe",entry_title:"Dragon Ball",
     main_volumes:34,duplicate_copies:0,other_editions_unknown:0
   }]
  }
 },{escape,lang:"fr"});
 assert.match(html,/id="pending-match-mode"/);
 assert.match(html,/value="MARK_DUPLICATE"/);
 assert.doesNotMatch(html,/value="CREATE_DECLARATION"/);
 assert.match(html,/id="pending-match-existing-ack"/);
 assert.match(html,/Déclarations déjà enregistrées/);
 assert.match(html,/34 tomes/);
 assert.match(html,/data-action="pending-match-confirm" disabled/);
});
test("two separate physical editions remain available for deliberate association",()=>{
 const html=inventoryResolverMarkup({
  ...base,reviewMode:"",review:{
   source:pending,manga,edition_key:"deluxe",
   allowed_actions:["CREATE_DECLARATION","MARK_DUPLICATE"],
   existing_declarations:[{
     edition_key:"pastel",edition_declared:"Pastel",entry_title:"Dragon Ball",
     main_volumes:42,duplicate_copies:0,other_editions_unknown:0
   }]
  }
 },{escape,lang:"fr"});
 assert.match(html,/Pastel/);
 assert.match(html,/value="CREATE_DECLARATION"/);
 assert.match(html,/value="MARK_DUPLICATE"/);
});

test("suspect alias and edition mismatch warnings are visible before selecting a work",()=>{
 const html=inventoryResolverMarkup({
  ...base,items:[{...manga,id:99,title:"Unrelated manga",
    matched_alias:"Dragon Ball",suggestion_kind:"EXACT_MULTILINGUAL_ALIAS",
    reconciliation:{assessment:"CONFLICT_REVIEW",warnings:[
      "ALIAS_UNVERIFIED_OR_UNTRACED",
      "JAPANESE_WORK_COUNT_VS_FRENCH_HOLDINGS_DIFFER"
    ]}}],
  searched:true
 },{escape,lang:"fr"});
 assert.match(html,/Association à vérifier/);
 assert.match(html,/Alias non corroboré/);
 assert.match(html,/Quantité de tomes à contrôler/);
 assert.match(html,/data-action="pending-match-select"/);
 assert.doesNotMatch(html,/data-action="edition-confirm"/);
});
