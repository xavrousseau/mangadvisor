/** Mangadvisor ISBN quick-add.
 * Native EAN-13 camera recognition when supported; no implicit book writes.
 * Keep this module independent from the legacy series library and CSV import.
 */
export const SCAN_KINDS = Object.freeze(["UNKNOWN","CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER"]);

const I18N = {
 fr: {
  title:"Scanner mes tomes", intro:"Un code-barres, une notice vérifiée, une confirmation. Aucun ajout automatique.",
  manual:"ISBN-13 du livre", verify:"Vérifier l’ISBN", camera:"Ouvrir la caméra",
  cameraStop:"Arrêter la caméra", close:"Fermer", focus:"Place le code-barres du tome dans le cadre.",
  idle:"Prêt pour un ISBN de manga.", checking:"Vérification du tome…",
  secure:"La caméra nécessite HTTPS ou localhost. Depuis un téléphone connecté au PC par adresse IP HTTP, saisis l’ISBN ou utilise un accès HTTPS sécurisé.",
  unsupported:"La lecture automatique EAN-13 n’est pas prise en charge par ce navigateur. La saisie ISBN reste disponible.",
  denied:"Impossible d’ouvrir la caméra. Vérifie son autorisation et qu’aucun autre logiciel ne l’utilise.",
  invalid:"Saisis un ISBN-13 valide (978 ou 979), avec son chiffre de contrôle.",
  unknown:"Notice BnF vérifiée · ISBN non enregistré", known:"ISBN déjà référencé dans Mangadvisor",
  already:"Ce livre est déjà marqué comme possédé : il ne sera pas ajouté en double.",
  series:"Série", edition:"Édition", volume:"Numéro de tome", find:"Rechercher une série",
  search:"Rechercher", select:"Choisir", noResults:"Aucune série trouvée. Modifie ta recherche.",
  choose:"Choisis explicitement la série concernée. Un titre BnF ressemblant n’est pas une preuve.",
  source:"Notice BnF", owned:"Possédé", read:"Lu", states:"Statuts à enregistrer",
  warning:"Confirme la série, l’édition et le numéro du tome. Aucun rapprochement automatique.",
  ack:"Je confirme que cet ISBN correspond à la série et à l’édition sélectionnées.",
  save:"Confirmer l’ajout", mark:"Confirmer les statuts", cancel:"Annuler",
  success:"Tome enregistré avec succès !", next:"Scanner le suivant",
  done:"Terminer", preserved:"Les statuts déjà acquis et l’ancien suivi global sont conservés.",
  noBnf:"Notice ISBN introuvable ou BnF indisponible : aucun tome n’a été ajouté.",
  isbn:"ISBN", more:"tome(s) traité(s) pendant cette session",
  kindUNKNOWN:"À préciser",kindCLASSIC:"Classique",kindDELUXE:"Deluxe",
  kindPERFECT:"Perfect",kindCOLLECTOR:"Collector",kindINTEGRAL:"Intégrale",kindOTHER:"Autre",
  empty:"Choisis Possédé, Lu ou les deux.", cameraReady:"Caméra active — lecture EAN-13",
 },
 en: {
  title:"Scan my volumes",intro:"One barcode, a verified record, your confirmation. Nothing is added automatically.",
  manual:"Book ISBN-13",verify:"Check ISBN",camera:"Open camera",
  cameraStop:"Stop camera",close:"Close",focus:"Position the book barcode within the frame.",
  idle:"Ready for a manga ISBN.",checking:"Checking the book…",
  secure:"The camera requires HTTPS or localhost. On a phone accessing your PC via HTTP IP, enter the ISBN or use secure HTTPS access.",
  unsupported:"Automatic EAN-13 reading is unavailable in this browser. Manual ISBN entry is still supported.",
  denied:"Cannot open the camera. Check camera permissions and whether another app is using it.",
  invalid:"Enter a valid 978/979 ISBN-13 with a correct check digit.",
  unknown:"Verified BnF record · ISBN not yet registered", known:"ISBN already registered in Mangadvisor",
  already:"Already marked as owned: this copy will not be counted twice.",
  series:"Series", edition:"Edition", volume:"Volume number", find:"Search for a series",
  search:"Search",select:"Select",noResults:"No series found. Adjust your search.",
  choose:"Explicitly select the correct series. A similar BnF title does not prove a match.",
  source:"BnF record",owned:"Owned",read:"Read",states:"Statuses to record",
  warning:"Confirm the series, edition and volume number. No automatic matching.",
  ack:"I confirm that this ISBN matches the chosen series and edition.",
  save:"Confirm addition",mark:"Confirm statuses",cancel:"Cancel",
  success:"Volume saved successfully!",next:"Scan another",
  done:"Finish",preserved:"Previous positive statuses and legacy series counts are preserved.",
  noBnf:"ISBN record not found or BnF unavailable: nothing has been added.",
  isbn:"ISBN",more:"volume(s) processed this session",
  kindUNKNOWN:"Unspecified",kindCLASSIC:"Standard",kindDELUXE:"Deluxe",
  kindPERFECT:"Perfect",kindCOLLECTOR:"Collector",kindINTEGRAL:"Omnibus",kindOTHER:"Other",
  empty:"Choose Owned, Read or both.",cameraReady:"Camera active — reading EAN-13",
 }
};
const msg=(lang,key)=>I18N[lang==="en"?"en":"fr"][key]||key;
const safeArk=url=>typeof url==="string"&&/^https:\/\/catalogue\.bnf\.fr\/ark:\/12148\/[a-zA-Z0-9]+$/.test(url)?url:null;

export function normalizeScannerIsbn(raw){
 const isbn=String(raw??"").replace(/[\s-]/g,"");
 if(!/^(978|979)\d{10}$/.test(isbn))return null;
 const sum=isbn.slice(0,12).split("").reduce((total,n,i)=>total+Number(n)*(i%2===0?1:3),0);
 return (10-sum%10)%10===Number(isbn[12])?isbn:null;
}

export function scanCanSave(draft){
 if(!draft || !draft.isbn || (!draft.owned&&!draft.read))return false;
 if(draft.phase==="known")return true;
 if(draft.phase!=="unknown" || !draft.record?.verified_isbn || draft.record.isbn13!==draft.isbn)return false;
 return Boolean(draft.selected?.id && SCAN_KINDS.includes(draft.kind) &&
  Number.isInteger(Number(draft.volume)) && Number(draft.volume)>=1 && Number(draft.volume)<=9999 &&
  String(draft.volume).trim()!=="" && draft.ack);
}

export function scannerMarkup(lang,escape,draft,count=0){
 const e=value=>escape(String(value??"")),L=key=>e(msg(lang,key));
 const hasBook=draft.phase==="known"||draft.phase==="unknown";
 const book=draft.phase==="known"?draft.registered?.edition:draft.record;
 const known=draft.phase==="known",unknown=draft.phase==="unknown";
 const label='<div class="scan-status '+(known?'is-known':'')+'">'+
  L(known?"known":unknown?"unknown":draft.phase==="loading"?"checking":"idle")+'</div>';
 const camera='<div class="scan-camera'+(draft.camera?" is-active":"")+'">'+
  '<video id="scan-video" autoplay playsinline muted aria-label="'+L("camera")+'"></video>'+
  '<div class="scan-target" aria-hidden="true"></div><p>'+L(draft.camera?"focus":"cameraReady")+'</p></div>';
 const cameraButtons='<div class="scan-tools"><button class="btn btn-soft" type="button" data-action="scan-start"'+
  (draft.camera?' disabled':'')+'>▣ '+L("camera")+'</button>'+
  (draft.camera?'<button class="btn btn-small" type="button" data-action="scan-stop">'+L("cameraStop")+'</button>':'')+'</div>';
 let detail="";
 if(hasBook && book){
  const title=known?book.title_fr:book.title_fr;
  const publisher=known?book.publisher_fr:book.publisher_fr;
  const source=safeArk(book.source_url);
  detail='<article class="scan-book">'+label+'<p class="scan-book-isbn">'+L("isbn")+' '+e(draft.isbn)+'</p>'+
   '<h3>'+e(title)+'</h3><p>'+e(publisher||"")+'</p>'+
   (source?'<a href="'+e(source)+'" target="_blank" rel="noopener noreferrer">'+L("source")+' ↗</a>':"")+'</article>';
  if(known){
   detail+='<div class="scan-known"><p><strong>'+L("series")+' :</strong> '+e(book.manga_title)+
    ' · '+L("edition")+' '+L("kind"+book.edition_kind)+' · '+L("volume")+' '+e(book.volume_number)+'</p>'+
    (book.is_owned?'<p class="scan-duplicate">✓ '+L("already")+'</p>':"")+'</div>';
  }else{
   detail+='<div class="scan-associate"><p class="scan-hint">'+L("choose")+'</p>'+
    (draft.selected?'<p class="scan-selected"><strong>'+L("series")+' :</strong> '+e(draft.selected.title)+
      ' <button type="button" class="btn-link" data-action="scan-unselect">'+L("search")+'</button></p>':
      '<form id="scan-series-form" class="scan-inline-form">'+
      '<label for="scan-series-input">'+L("find")+'</label>'+
      '<div class="actions"><input id="scan-series-input" class="input" name="q" maxlength="120" required value="'+e(draft.query||"")+'">'+
      '<button type="submit" class="btn btn-soft">'+L("search")+'</button></div></form>'+
      (draft.searched?'<div class="scan-matches">'+(draft.matches.length?draft.matches.map(m=>
        '<button class="scan-match" type="button" data-action="scan-select" data-id="'+e(m.id)+'">'+
        '<strong>'+e(m.title)+'</strong><span>'+L("select")+' →</span></button>').join(""):
        '<p class="muted">'+L("noResults")+'</p>')+'</div>':""))+
    '<div class="scan-fields"><div class="field"><label for="scan-kind">'+L("edition")+'</label>'+
    '<select class="select" id="scan-kind">'+SCAN_KINDS.map(k=>
      '<option value="'+k+'"'+(k===draft.kind?' selected':'')+'>'+L("kind"+k)+'</option>').join("")+'</select></div>'+
    '<div class="field"><label for="scan-volume">'+L("volume")+'</label>'+
    '<input class="input" id="scan-volume" type="number" min="1" max="9999" step="1" inputmode="numeric" value="'+e(draft.volume)+'" placeholder="1"></div></div>'+
    '<p class="scan-hint">'+L("warning")+'</p>'+
    '<label class="check scan-ack"><input type="checkbox" id="scan-ack"'+(draft.ack?' checked':'')+'>'+L("ack")+'</label>'+
    '</div>';
  }
  detail+='<div class="scan-confirm"><strong>'+L("states")+'</strong><div class="scan-toggles">'+
   '<label class="check"><input type="checkbox" id="scan-owned"'+(draft.owned?' checked':'')+'>'+L("owned")+'</label>'+
   '<label class="check"><input type="checkbox" id="scan-read"'+(draft.read?' checked':'')+'>'+L("read")+'</label></div>'+
   '<button class="btn btn-primary" type="button" data-action="scan-confirm"'+(scanCanSave(draft)?'':' disabled')+'>'+
   L(known?"mark":"save")+'</button><p class="scan-hint">'+L("preserved")+'</p></div>';
 }
 if(draft.phase==="saved"){
  detail='<div class="scan-success" role="status"><div class="scan-success-icon">✓</div>'+
   '<h3>'+L("success")+'</h3><p>'+e(draft.savedTitle||draft.isbn)+'</p>'+
   '<p class="scan-hint">'+L("preserved")+'</p><div class="actions">'+
   '<button class="btn btn-primary" data-action="scan-next">'+L("next")+'</button>'+
   '<button class="btn btn-soft" data-action="scan-close">'+L("done")+'</button></div></div>';
 }
 return '<div class="scan-overlay" id="scan-overlay"><section id="scan-dialog" class="scan-dialog" role="dialog" aria-modal="true" aria-labelledby="scan-title">'+
  '<header class="scan-heading"><div><div class="eyebrow">MANGADVISOR · ISBN</div><h2 id="scan-title">'+L("title")+'</h2>'+
  '<p>'+L("intro")+'</p></div><button type="button" class="scan-x" data-action="scan-close" aria-label="'+L("close")+'">×</button></header>'+
  (draft.phase==="saved"?detail:
   '<div class="scan-body"><form class="scan-inline-form" id="scan-isbn-form">'+
   '<label for="scan-isbn-input">'+L("manual")+'</label><div class="actions">'+
   '<input class="input" id="scan-isbn-input" name="isbn" maxlength="18" autocomplete="off" inputmode="numeric" placeholder="978..." value="'+e(draft.isbn||"")+'">'+
   '<button type="submit" class="btn btn-primary">'+L("verify")+'</button></div></form>'+
   cameraButtons+camera+
   (draft.phase==="loading"?'<div class="info">'+L("checking")+'</div>':"")+
   (draft.message?'<p class="scan-error" role="alert">'+e(draft.message)+'</p>':"")+
   detail+'</div>')+
  '<footer class="scan-footer">'+e(count)+' '+L("more")+'</footer></section></div>';
}

export function createIsbnScanner({root,request,lang,escape,onSaved}){
 let draft=null,stream=null,frame=0,epoch=0,detector=null,lastDetect=0,busy=false,handled=0,returnFocus=null;
 const isOpen=()=>Boolean(draft&&root.querySelector("#scan-overlay"));
 const t=key=>msg(lang(),key);
 function stopCamera(){
  if(frame)cancelAnimationFrame(frame);frame=0;
  if(stream){for(const track of stream.getTracks())track.stop();stream=null;}
  const video=root.querySelector("#scan-video");
  if(video)video.srcObject=null;
  if(draft)draft.camera=false;
  detector=null;busy=false;
 }
 function paint(){
  if(!draft)return;
  const existing=root.querySelector("#scan-overlay");
  if(existing)existing.outerHTML=scannerMarkup(lang(),escape,draft,handled);
  else root.insertAdjacentHTML("beforeend",scannerMarkup(lang(),escape,draft,handled));
 }
 function close(){
  epoch++;stopCamera();draft=null;root.querySelector("#scan-overlay")?.remove();
  if(returnFocus?.isConnected)returnFocus.focus();returnFocus=null;
 }
 function open(selectedManga=null){
  close();returnFocus=document.activeElement;handled=0;
  draft={phase:"idle",isbn:"",record:null,registered:null,matches:[],selected:selectedManga?.id?
   {id:selectedManga.id,title:selectedManga.title}:null,query:"",searched:false,
   kind:"UNKNOWN",volume:"",owned:true,read:false,ack:false,camera:false,message:""};
  paint();root.querySelector("#scan-isbn-input")?.focus();
 }
 function message(text){
  if(!draft)return;draft.message=text;const node=root.querySelector(".scan-error");
  if(node)node.textContent=text;else paint();
 }
 function reset(next=false){
  if(!draft)return;
  const selected=next?null:draft.selected;
  stopCamera();epoch++;
  draft={phase:"idle",isbn:"",record:null,registered:null,matches:[],selected,
   query:"",searched:false,kind:"UNKNOWN",volume:"",owned:true,read:false,ack:false,
   camera:false,message:""};
  paint();root.querySelector("#scan-isbn-input")?.focus();
 }
 async function lookup(raw){
  const isbn=normalizeScannerIsbn(raw);
  if(!isbn){message(t("invalid"));return;}
  stopCamera();
  const current=++epoch;
  draft={...draft,phase:"loading",isbn,record:null,registered:null,message:"",
   matches:[],searched:false,ack:false,volume:""};
  paint();
  try{
   const result=await request("/collection/scan/status/"+isbn);
   if(current!==epoch||!isOpen())return;
   if(result.registered && result.edition){
    draft={...draft,phase:"known",registered:result,
     owned:result.edition.is_owned||true,read:result.edition.is_read||false};
   }else{
    const record=await request("/collection/isbn/"+isbn);
    if(current!==epoch||!isOpen())return;
    if(record?.verified_isbn!==true || record.isbn13!==isbn)throw Error(t("noBnf"));
    draft={...draft,phase:"unknown",record,owned:true,read:false,
      kind:SCAN_KINDS.includes(record.edition_kind_suggested)?record.edition_kind_suggested:"UNKNOWN"};
   }
   paint();
  }catch(err){
   if(current!==epoch||!isOpen())return;
   draft={...draft,phase:"idle",message:err.message||t("noBnf")};
   paint();
  }
 }
 async function startCamera(){
  if(!draft||stream)return;
  if(!window.isSecureContext){message(t("secure"));return;}
  if(!("BarcodeDetector" in window)||!navigator.mediaDevices?.getUserMedia){
   message(t("unsupported"));return;
  }
  const current=++epoch;
  try{
   const formats=await window.BarcodeDetector.getSupportedFormats();
   if(!formats.includes("ean_13"))throw Error(t("unsupported"));
   detector=new window.BarcodeDetector({formats:["ean_13"]});
   const cameraStream=await navigator.mediaDevices.getUserMedia({
    audio:false,video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}}
   });
   if(current!==epoch||!isOpen()){cameraStream.getTracks().forEach(track=>track.stop());return;}
   stream=cameraStream;draft.camera=true;draft.message="";paint();
   const video=root.querySelector("#scan-video");
   video.srcObject=stream;
   await video.play();
   if(current!==epoch||!isOpen()){stopCamera();return;}
   const tick=async now=>{
    if(!draft?.camera||current!==epoch||!stream)return;
    if(!busy && now-lastDetect>280 && video.readyState>=2){
     busy=true;lastDetect=now;
     try{
      const found=await detector.detect(video);
      if(current!==epoch||!draft?.camera)return;
      const value=(found||[]).map(item=>normalizeScannerIsbn(item.rawValue)).find(Boolean);
      if(value){await lookup(value);return;}
     }catch{/* Individual frames can fail under low light; keep scanning. */}
     finally{busy=false;}
    }
    if(current===epoch&&draft?.camera)frame=requestAnimationFrame(tick);
   };
   frame=requestAnimationFrame(tick);
  }catch(err){
   if(current!==epoch)return;
   stopCamera();draft.message=err.message===t("unsupported")?t("unsupported"):t("denied");paint();
  }
 }
 async function searchSeries(form){
  if(draft?.phase!=="unknown")return;
  const q=String(new FormData(form).get("q")||"").trim().slice(0,120);
  if(!q)return;
  const current=epoch;
  draft.query=q;draft.selected=null;draft.searched=false;paint();
  try{
   const result=await request("/mangas?"+new URLSearchParams({q,limit:"12"}));
   if(current!==epoch||draft?.phase!=="unknown"||draft.query!==q)return;
   draft.matches=(result.items||[]).slice(0,12);draft.searched=true;paint();
  }catch(err){if(current===epoch)message(err.message||t("noResults"));}
 }
 function capture(){
  if(!draft)return;
  const target=root.querySelector("#scan-dialog");if(!target)return;
  draft.owned=Boolean(target.querySelector("#scan-owned")?.checked);
  draft.read=Boolean(target.querySelector("#scan-read")?.checked);
  if(draft.phase==="unknown"){
   draft.kind=target.querySelector("#scan-kind")?.value||"UNKNOWN";
   draft.volume=target.querySelector("#scan-volume")?.value??"";
   draft.ack=Boolean(target.querySelector("#scan-ack")?.checked);
  }
  const save=target.querySelector('[data-action="scan-confirm"]');
  if(save)save.disabled=!scanCanSave(draft);
 }
 async function confirm(button){
  capture();
  if(!scanCanSave(draft)){message(t("empty"));return;}
  button.disabled=true;
  const current=epoch;
  const payload={isbn13:draft.isbn,confirmed:true,is_owned:draft.owned,is_read:draft.read};
  if(draft.phase==="unknown"){
   Object.assign(payload,{manga_id:Number(draft.selected.id),
    edition_kind:draft.kind,volume_number:Number(draft.volume)});
  }
  try{
   const result=await request("/collection/scan/confirm",{method:"POST",data:payload});
   if(current!==epoch||!isOpen())return;
   const title=result.edition?.title_fr||draft.isbn;
   handled++;
   stopCamera();draft={...draft,phase:"saved",savedTitle:title,message:""};paint();
   await onSaved(result);
  }catch(err){if(current===epoch&&isOpen()){button.disabled=false;message(err.message||t("noBnf"));}}
 }
 async function click(action,button){
  if(action==="scan-close"){close();return;}
  if(!draft)return;
  if(action==="scan-start"){await startCamera();return;}
  if(action==="scan-stop"){stopCamera();paint();return;}
  if(action==="scan-next"){reset(true);return;}
  if(action==="scan-unselect"){capture();draft.selected=null;draft.matches=[];draft.searched=false;paint();return;}
  if(action==="scan-select"&&draft.phase==="unknown"){
   capture();const manga=draft.matches.find(m=>Number(m.id)===Number(button.dataset.id));
   if(manga){draft.selected={id:manga.id,title:manga.title};draft.ack=false;paint();}
   return;
  }
  if(action==="scan-confirm")await confirm(button);
 }
 function submit(form){
  if(form.id==="scan-isbn-form")return lookup(new FormData(form).get("isbn"));
  if(form.id==="scan-series-form")return searchSeries(form);
 }
 return {open,close,click,submit,capture,isOpen};
}
