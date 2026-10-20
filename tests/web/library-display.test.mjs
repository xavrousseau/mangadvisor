import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const source=readFileSync("apps/web/assets/library-display.js","utf8");
const {preferredMangaTitle,declaredCountsByManga,libraryCardMeta}=
  await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));

test("english fallback is consistent without inventing a French official title",()=>{
 assert.equal(preferredMangaTitle({
  title:"Kimetsu no Yaiba",title_english:"Demon Slayer: Kimetsu no Yaiba",
  title_japanese:"鬼滅の刃",
 },"fr"),"Demon Slayer: Kimetsu no Yaiba");
 assert.equal(preferredMangaTitle({title:"Jujutsu Kaisen"},"fr"),"Jujutsu Kaisen");
 assert.equal(preferredMangaTitle({title:"Titre original",title_fr:"Titre français",
  title_fr_verified:false},"fr"),"Titre original");
 assert.equal(preferredMangaTitle({title:"Original",title_fr:"Titre confirmé",
  title_fr_verified:true},"fr"),"Titre confirmé");
 assert.equal(preferredMangaTitle({title:"Original",title_fr:"Titre confirmé",
  title_fr_verified:true},"en"),"Original");
 assert.equal(preferredMangaTitle({title_japanese:"日本語"},"fr"),"日本語");
});

test("BnF authority and exact MAL Wikidata French titles are displayed with source",()=>{
 assert.equal(preferredMangaTitle({
  title:"Shingeki no Kyojin",title_english:"Attack on Titan",
  title_fr:"L'Attaque des Titans",title_fr_verified:true,
  title_fr_source:"BNF_AUTHORITY_WORK"
 },"fr"),"L'Attaque des Titans");
 assert.equal(preferredMangaTitle({
  title:"Shingeki no Kyojin",title_english:"Attack on Titan",
  title_fr:"L'Attaque des Titans",title_fr_verified:false,
  title_fr_source:"WIKIDATA_P4087_FR"
 },"fr"),"L'Attaque des Titans");
 assert.equal(preferredMangaTitle({
  title:"Shingeki no Kyojin",title_english:"Attack on Titan",
  title_fr:"Titre sans provenance",title_fr_verified:false,
  title_fr_source:"SOURCE_INCONNUE"
 },"fr"),"Attack on Titan");
 assert.equal(preferredMangaTitle({
  title:"Shingeki no Kyojin",title_english:"Attack on Titan",
  title_fr:"L'Attaque des Titans",title_fr_verified:true,
  title_fr_source:"BNF_AUTHORITY_WORK"
 },"en"),"Attack on Titan");
});
test("declared physical editions count every copy once per manga",()=>{
 const data={
  scope:"owner_declared_unverified_editions_not_isbn_books",
  items:[
   {manga_id:20,main_volumes:34,duplicate_copies:1,other_editions_unknown:0},
   {manga_id:20,main_volumes:42,duplicate_copies:0,other_editions_unknown:2},
   {manga_id:31,main_volumes:12,duplicate_copies:0,other_editions_unknown:0},
  ],
 };
 const numbers=declaredCountsByManga(data);
 assert.equal(numbers.get(20),79);
 assert.equal(numbers.get(31),12);
 assert.equal(numbers.size,2);
 assert.equal(declaredCountsByManga({scope:"unverified",items:data.items}).size,0);
 assert.equal(declaredCountsByManga({
  scope:data.scope,items:[{manga_id:1,main_volumes:-1}]
 }).size,0);
});

test("unknown rating must not masquerade as unknown owned quantity",()=>{
 const manga={manga_id:20,library_status:"Possédé",user_score:null};
 const known=declaredCountsByManga({
  scope:"owner_declared_unverified_editions_not_isbn_books",
  items:[{manga_id:20,main_volumes:34,duplicate_copies:0,other_editions_unknown:0}]
 });
 assert.equal(libraryCardMeta(manga,known,"fr"),
   "Possédé · 34 exemplaires déclarés");
 assert.equal(libraryCardMeta(manga,null,"fr"),"Possédé");
 assert.equal(libraryCardMeta({...manga,user_score:9.5},known,"fr"),
   "Possédé · ★ 9.5/10 · 34 exemplaires déclarés");
 assert.equal(libraryCardMeta(manga,known,"en"),
   "Possédé · 34 declared copies");
});
