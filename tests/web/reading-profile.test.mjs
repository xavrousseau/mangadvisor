import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const source=readFileSync("apps/web/assets/reading-profile.js","utf8");
const {readingProfileMarkup}=await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(source));
const escape=v=>String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

test("reading profile supports status counts and weighted tags",()=>{
 const html=readingProfileMarkup({
  status_counts:{READ:3,READING:2,WANT_TO_READ:4},negative_item_count:1,
  top_genres:[{name:"Action",total_weight:7.4}],
  strongest_sources:[{title:"Naruto",library_status:"READ",user_score:9}],
  negative_items:[{title:"Fairy Tail",library_status:"DROPPED",negative_reason:"Abandonné"}]
 },"fr",escape);
 assert.match(html,/Genres dominants/);
 assert.match(html,/Naruto/);
 assert.match(html,/Fairy Tail/);
 assert.match(html,/DROPPED/);
});
test("reading profile escapes untrusted manga names",()=>{
 const html=readingProfileMarkup({
  strongest_sources:[{title:'<img src=x onerror="alert(1)">'}],
  top_genres:[{name:"<script>alert(1)</script>",total_weight:1}]
 },"fr",escape);
 assert.doesNotMatch(html,/<script>|<img src/);
 assert.match(html,/&lt;script&gt;/);
});
test("reading profile tolerates missing data",()=>{
 assert.match(readingProfileMarkup({}, "en",escape),/Top genres/);
});
