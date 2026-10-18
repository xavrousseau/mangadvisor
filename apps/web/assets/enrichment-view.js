/** Bounded BnF title-based workshop; candidate ≠ verified series association. */
const VALID_STATUS=new Set(["TO_VERIFY","REGISTERED_HERE","REGISTERED_OTHER"]);
const VALID_CLUE=new Set(["TITLE_WORDS_PRESENT","SOME_TITLE_WORDS","NO_TITLE_WORDS"]);
const bnfLink=url=>{
 try{
  const parsed=new URL(String(url||""));
  return parsed.protocol==="https:"&&parsed.hostname==="catalogue.bnf.fr"&&
    /^\/ark:\/12148\/cb[0-9A-Za-z]+\/?$/.test(parsed.pathname)?parsed.href:null;
 }catch{return null;}
};

export function enrichmentPanel(escape,t,lang){
 const e=s=>escape(String(s??"")),L=k=>e(t(lang,k));
 return '<section class="enrichment-panel" id="fr-enrichment">'+
  '<div class="enrichment-head"><div><div class="eyebrow">✧ MANGADVISOR · BnF</div>'+
  '<h3>'+L("enrichHeading")+'</h3><p>'+L("enrichIntro")+'</p></div>'+
  '<button type="button" class="btn btn-primary" data-action="enrich-discover">✦ '+
    L("enrichRun")+'</button></div>'+
  '<div id="fr-enrichment-results" aria-live="polite"></div></section>';
}

/** Reflect confirmed ISBN associations after a saved book, without rerunning BnF. */
export function reconcileEnrichment(data,editions){
 if(!data||!Array.isArray(data.items))return data;
 const known=new Set((Array.isArray(editions)?editions:[]).map(x=>String(x.isbn13||"")));
 const items=data.items.map(item=>
   known.has(item.isbn13)&&item.registration_status==="TO_VERIFY"
    ?{...item,registration_status:"REGISTERED_HERE",
      registered_manga_id:data.manga_id}:item);
 return {...data,items,
  to_verify_count:items.filter(x=>x.registration_status==="TO_VERIFY").length,
  registered_here_count:items.filter(x=>x.registration_status==="REGISTERED_HERE").length,
  registered_other_count:items.filter(x=>x.registration_status==="REGISTERED_OTHER").length,
 };
}

export function enrichmentResults(data,escape,t,lang){
 const e=s=>escape(String(s??"")),L=k=>e(t(lang,k));
 const candidates=(Array.isArray(data?.items)?data.items:[])
  .filter(x=>VALID_STATUS.has(x?.registration_status)&&/^[0-9]{13}$/.test(String(x?.isbn13||"")));
 const numbers=[
  [data?.to_verify_count??0,"enrichNewCandidates"],
  [data?.registered_here_count??0,"enrichAlreadyHere"],
  [data?.registered_other_count??0,"enrichAlreadyOther"],
 ];
 const stats='<div class="enrich-stats">'+numbers.map(([num,key])=>
   '<span><strong>'+e(num)+'</strong>'+L(key)+'</span>').join("")+'</div>';
 const hints='<p class="enrich-warning">'+L("enrichNotice")+'</p>'+
  ((data?.search_errors?.length)?'<p class="enrich-warning">'+L("enrichPartial")+': '+
    data.search_errors.map(e).join(", ")+'</p>':"")+
  (data?.truncated?'<p class="enrich-warning">'+L("enrichTruncated")+'</p>':"");
 const entries=candidates.map(x=>{
  const link=bnfLink(x.source_url);
  const status=x.registration_status;
  const clue=VALID_CLUE.has(x.title_clue)?x.title_clue:"NO_TITLE_WORDS";
  const metadata=[x.author_fr,x.publisher_fr,x.release_date_text]
   .filter(v=>typeof v==="string"&&v).map(e).join(" · ");
  return '<article class="enrich-candidate" data-registration="'+status+'">'+
   '<div class="enrich-item-main"><div class="enrich-labels">'+
   '<span class="enrich-status '+(status==="TO_VERIFY"?"fresh":"registered")+'">'+
      L(status==="TO_VERIFY"?"enrichNewCandidates":
        status==="REGISTERED_HERE"?"enrichAlreadyHere":"enrichAlreadyOther")+'</span>'+
   '<span class="enrich-clue">'+L("enrichClue"+clue)+'</span></div>'+
   '<h4>'+e(x.title_fr||x.isbn13)+'</h4>'+
   (metadata?'<p>'+metadata+'</p>':"")+
   '<p class="edition-source">ISBN '+e(x.isbn13)+
    (link?' · <a href="'+e(link)+'" target="_blank" rel="noopener noreferrer">'+
     L("collectionBnfSource")+' ↗</a>':"")+'</p>'+
   '<p class="tiny muted">'+L("biblioLanguage")+': '+e(x.language_recorded||t(lang,"biblioLanguageUnknown"))+
    ' · '+L("collectionEditionType")+': '+L("edition"+
     (["UNKNOWN","CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER"].includes(x.edition_kind_suggested)
      ?x.edition_kind_suggested:"UNKNOWN"))+'</p>'+
   (status==="REGISTERED_OTHER"?'<p class="enrich-warning">'+L("enrichConflictHelp")+'</p>':"")+
   '</div>'+
   (status==="TO_VERIFY"?
    '<button type="button" class="btn btn-small btn-soft" data-action="enrich-verify-isbn" data-isbn="'+
     e(x.isbn13)+'">'+L("enrichVerify")+' →</button>':
    '<span class="enrich-done" aria-label="'+L("enrichNoAction")+'">✓</span>')+
   '</article>';
 }).join("");
 return stats+hints+(entries?'<div class="enrich-candidates">'+entries+'</div>':
 '<div class="home-empty">'+L("enrichEmpty")+'</div>');
}
