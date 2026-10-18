import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const src=readFileSync("apps/web/assets/isbn-scanner.js","utf8");
const {normalizeScannerIsbn,scanCanSave,scannerMarkup,SCAN_KINDS}=
 await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(src));
const escape=value=>String(value??"").replace(/[&<>"']/g,c=>({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const record={isbn13:"9782871294146",verified_isbn:true,title_fr:"Naruto, tome 1",
 publisher_fr:"Kana",edition_kind_suggested:"UNKNOWN",
 source_url:"https://catalogue.bnf.fr/ark:/12148/cb12345678x"};
const draft={phase:"unknown",isbn:record.isbn13,record,registered:null,
 selected:{id:1,title:"Naruto"},kind:"CLASSIC",volume:"1",owned:true,read:false,
 ack:false,query:"",matches:[],searched:false,camera:false,message:""};

test("validates real ISBN-13 check digits, rejects regular EAN barcodes",()=>{
 assert.equal(normalizeScannerIsbn("978-2-87129-414-6"),"9782871294146");
 assert.equal(normalizeScannerIsbn("9782871294140"),null);
 assert.equal(normalizeScannerIsbn("4006381333931"),null);
 assert.equal(normalizeScannerIsbn("9782871294146<script>"),null);
 assert.equal(normalizeScannerIsbn("9792871294146"),null);
});

test("new books require verified exact ISBN + series + edition + tome + acknowledgement",()=>{
 assert.equal(scanCanSave(draft),false);
 assert.equal(scanCanSave({...draft,ack:true}),true);
 assert.equal(scanCanSave({...draft,record:{...record,verified_isbn:false},ack:true}),false);
 assert.equal(scanCanSave({...draft,record:{...record,isbn13:"9782344074282"},ack:true}),false);
 assert.equal(scanCanSave({...draft,selected:null,ack:true}),false);
 assert.equal(scanCanSave({...draft,volume:"",ack:true}),false);
 assert.equal(scanCanSave({...draft,volume:"0",ack:true}),false);
 assert.equal(scanCanSave({...draft,kind:"FAKE",ack:true}),false);
 assert.equal(scanCanSave({...draft,owned:false,read:false,ack:true}),false);
 assert.equal(SCAN_KINDS.includes("PERFECT"),true);
});

test("known ISBNs do not create an edition or require a second series choice",()=>{
 const existing={edition:{edition_id:4,manga_title:"Naruto",title_fr:"Naruto, tome 1",
  isbn13:record.isbn13,edition_kind:"CLASSIC",volume_number:1,is_owned:true,is_read:false}};
 const known={...draft,phase:"known",registered:existing,record:null,ack:false};
 assert.equal(scanCanSave(known),true);
 const html=scannerMarkup("fr",escape,known,1);
 assert.match(html,/ISBN déjà référencé/);
 assert.match(html,/déjà marqué comme possédé/);
 assert.doesNotMatch(html,/id="scan-ack"/);
 assert.match(html,/data-action="scan-confirm"/);
});

test("rendering is safe and a scanned notice never auto-confirms",()=>{
 const malicious={...draft,record:{...record,title_fr:'<img src=x onerror="alert(1)">'},
 selected:{id:2,title:"<svg onload=alert(1)>"},volume:"",ack:false};
 const html=scannerMarkup("fr",escape,malicious);
 assert.doesNotMatch(html,/<img src=x|<svg onload/);
 assert.match(html,/&lt;img/);
 assert.match(html,/&lt;svg/);
 assert.match(html,/data-action="scan-confirm" disabled/);
 assert.match(html,/id="scan-volume"[^>]*value=""/);
 assert.match(html,/id="scan-owned"/);
});

test("source links are restricted to safe BnF ARKs",()=>{
 const evil={...draft,record:{...record,source_url:"javascript:alert(1)"}};
 assert.doesNotMatch(scannerMarkup("en",escape,evil),/href="javascript/);
 assert.match(scannerMarkup("en",escape,draft),/href="https:\/\/catalogue.bnf.fr\/ark:/);
});

test("successful scan offers next book and remembers session count",()=>{
 const html=scannerMarkup("en",escape,{...draft,phase:"saved",savedTitle:"Naruto 1"},3);
 assert.match(html,/data-action="scan-next"/);
 assert.match(html,/data-action="scan-close"/);
 assert.match(html,/3 volume\(s\) processed/);
 assert.doesNotMatch(html,/data-action="scan-confirm"/);
});
