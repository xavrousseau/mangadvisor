import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const src=readFileSync("apps/web/assets/isbn-scanner.js","utf8");
const {normalizeScannerIsbn,scanCanSave,scannerMarkup,SCAN_KINDS,scanSessionTotals,scanSessionEntry,scanOutcome}=
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


test("session totals distinguish new, updated, duplicate and unresolved ISBNs",()=>{
 let entries=[];
 entries=scanSessionEntry(entries,{isbn:"9782871294146",title:"Naruto 1",status:"unresolved"});
 entries=scanSessionEntry(entries,{isbn:"9782871294146",title:"Naruto 1",status:"created"});
 entries=scanSessionEntry(entries,{isbn:"9782344074282",title:"Monster",status:"duplicate"});
 entries=scanSessionEntry(entries,{isbn:"9782368526156",title:"New book",status:"updated"});
 assert.equal(entries.length,3);
 assert.deepEqual(scanSessionTotals(entries),{created:1,updated:1,duplicate:1,unresolved:0});
 const different=scanSessionEntry(entries,{isbn:"9791000000000",status:"unresolved"});
 assert.equal(scanSessionTotals(different).unresolved,1);
});

test("a known scan is only an update if a positive status changes",()=>{
 assert.equal(scanOutcome({status:"created"},null),"created");
 assert.equal(scanOutcome({status:"updated",edition:{is_owned:true,is_read:false}},
  {is_owned:false,is_read:false}),"updated");
 assert.equal(scanOutcome({status:"updated",edition:{is_owned:true,is_read:true}},
  {is_owned:true,is_read:true}),"duplicate");
 assert.equal(scanOutcome({status:"updated",edition:{is_owned:true,is_read:true}},
  {is_owned:true,is_read:false}),"updated");
});

test("session report is escaped, lists unresolved ISBNs and offers retry",()=>{
 const badTitle='<svg onload=evil()>';
 const rows=[
  {isbn:"9782871294146",status:"created",title:"Naruto 1"},
  {isbn:"9782344074282",status:"unresolved",title:badTitle}
 ];
 const html=scannerMarkup("fr",escape,{phase:"summary",isbn:"",camera:false,message:""},1,rows);
 assert.match(html,/Bilan de session/);
 assert.match(html,/Tomes ajoutés/);
 assert.match(html,/À vérifier/);
 assert.match(html,/data-action="scan-retry"/);
 assert.match(html,/data-action="scan-resume"/);
 assert.doesNotMatch(html,/<svg onload/);
 assert.match(html,/&lt;svg onload/);
});

test("previously selected series is shown as a suggestion, not an automatic confirmation",()=>{
 const html=scannerMarkup("fr",escape,{...draft,previousSeries:true,ack:false},2);
 assert.match(html,/Série conservée du tome précédent/);
 assert.match(html,/data-action="scan-confirm" disabled/);
 assert.match(html,/id="scan-ack"/);
});
