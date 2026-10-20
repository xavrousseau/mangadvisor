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
test("French/English/Japanese alias and prior quantities are visible before reviewing",()=>{
 const result=inventoryResolverMarkup({
  ...base,items:[{...manga,title:"Shingeki no Kyojin",
   title_fr:"L'Attaque des Titans",matched_alias:"L'Attaque des Titans",
   alias_source:"BNF_AUTHORITY_WORK",suggestion_kind:"EXACT_ALIAS",
   already_in_inventory:true,known_editions:[{
    edition:null,main_volumes:34,duplicate_copies:0,
    other_editions_unknown:1
   }]}],
  review:{source:{...pending,main_volumes:35,edition_declared:null},
    manga:{...manga,title:"Shingeki no Kyojin"},
    existing_declarations:[{edition_declared:null,main_volumes:34,
      duplicate_copies:0,other_editions_unknown:1}],
    same_edition_exists:true,
    allowed_actions:["MARK_DUPLICATE"]
  },
  reviewMode:""
 },{escape,lang:"fr"});
 assert.match(result,/L&#39;Attaque des Titans/);
 assert.match(result,/BNF_AUTHORITY_WORK/);
 assert.match(result,/Déjà présent dans ta collection/);
 assert.match(result,/34 tomes principaux/);
 assert.match(result,/35 tomes principaux/);
 assert.match(result,/ne double pas les quantités/);
 assert.match(result,/value="MARK_DUPLICATE"/);
 assert.doesNotMatch(result,/value="CREATE_DECLARATION"/);
 assert.match(result,/data-action="pending-match-confirm" disabled/);
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
