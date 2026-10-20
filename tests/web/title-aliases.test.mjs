import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const load=async path=>{
 const source=readFileSync(path,"utf8");
 return import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
};
const {titleAliasesMarkup}=await load("apps/web/assets/title-aliases-view.js");
const {preferredMangaTitle}=await load("apps/web/assets/library-display.js");
const {inventoryResolverMarkup}=await load("apps/web/assets/inventory-resolution-view.js");
const escape=v=>String(v??"").replace(/[&<>"']/g,x=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[x]));

test("sourced FR/EN/JP names share same canonical manga but are not book editions",()=>{
 const html=titleAliasesMarkup({
  manga_id:7,items:[
   {alias:"L’Attaque des Titans",language_code:"fr",
    source_name:"MANGADEX_MAL_LINK",
    source_ref:"https://mangadex.org/title/12345678-1111-2222-3333-444444444444"},
   {alias:"Attack on Titan",language_code:"en",source_name:"MAL_ENGLISH",source_ref:"MAL:13"},
   {alias:"Shingeki no Kyojin",language_code:"ja-ro",source_name:"MAL_ORIGINAL",source_ref:"MAL:13"},
   {alias:"進撃の巨人",language_code:"ja",source_name:"MAL_JAPANESE",source_ref:"MAL:13"}
  ]
 },{escape,lang:"fr"});
 assert.match(html,/L’Attaque des Titans/);
 assert.match(html,/Attack on Titan/);
 assert.match(html,/Shingeki no Kyojin/);
 assert.match(html,/進撃の巨人/);
 assert.match(html,/MangaDex ↗/);
 assert.match(html,/éditions françaises vérifiées/);
 assert.doesNotMatch(html,/data-action="edition-confirm"/);
});

test("French community label is a display name, not a verified publisher edition",()=>{
 const manga={title:"Shingeki no Kyojin",title_english:"Attack on Titan",
   title_fr_community:"L'Attaque des Titans",
   title_fr_source:"MANGADEX_MAL_LINK"};
 assert.equal(preferredMangaTitle(manga,"fr"),"L'Attaque des Titans");
 assert.equal(preferredMangaTitle(manga,"en"),"Attack on Titan");
 assert.equal(preferredMangaTitle({...manga,title_fr_source:null},"fr"),"Attack on Titan");
 assert.equal(preferredMangaTitle({...manga,title_fr_verified:true,
   title_fr:"L'Attaque des Titans officiel"},"fr"),"L'Attaque des Titans officiel");
});

test("existing physical collection is visibly warned on matching French alias",()=>{
 const html=inventoryResolverMarkup({
  sourceKey:"row-22",pending:{entry_title:"L'Attaque des Titans",main_volumes:35,
   edition_declared:null},query:"L'Attaque des Titans",
  searched:true,loading:false,items:[{
   id:7,title:"Shingeki no Kyojin",title_english:"Attack on Titan",
   title_fr_community:"L'Attaque des Titans",source_mal_id:13,
   suggestion_kind:"EXACT_ALIAS",already_declared_editions:1
  }]
 },{escape,lang:"fr"});
 assert.match(html,/L&#39;Attaque des Titans/);
 assert.match(html,/œuvre possède déjà une déclaration physique/);
 assert.match(html,/Nom exact retrouvé/);
 assert.match(html,/data-action="pending-match-select"/);
 assert.doesNotMatch(html,/data-action="pending-match-confirm"/);
});

test("reject untrusted external URLs and encode all alias text",()=>{
 const html=titleAliasesMarkup({items:[{
  alias:'<img src=x onerror="alert(1)">',language_code:"fr",
  source_name:"MANGADEX_MAL_LINK",
  source_ref:"https://mangadex.org.attacker.test/title/"+ "a".repeat(36)
 }]},{escape,lang:"fr"});
 assert.match(html,/&lt;img/);
 assert.doesNotMatch(html,/<img /);
 assert.doesNotMatch(html,/href=/);
});
