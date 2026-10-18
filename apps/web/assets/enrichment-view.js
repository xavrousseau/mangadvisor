/** Bounded BnF title-based workshop; candidate ≠ verified series association. */
const VALID_STATUS=new Set(["TO_VERIFY","REGISTERED_HERE","REGISTERED_OTHER"]);
const VALID_CLUE=new Set(["TITLE_WORDS_PRESENT","SOME_TITLE_WORDS","NO_TITLE_WORDS"]);
const FORMAT_ORDER=["CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER","UNKNOWN"];
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
  '</div><div class="enrich-query"><label for="enrich-alt-title">'+L("enrichAliasLabel")+'</label>'+
   '<div class="actions"><input type="search" id="enrich-alt-title" class="input" maxlength="90" '+
     'placeholder="'+L("enrichAliasPlaceholder")+'" autocomplete="off">'+
   '<button type="button" class="btn btn-primary" data-action="enrich-discover">✦ '+
     L("enrichRun")+'</button></div>'+
   '<p class="tiny muted">'+L("enrichAliasHelp")+'</p></div>'+
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

/** Append another BnF page without losing candidate confirmations or duplicate ISBNs. */
export function mergeEnrichmentPages(previous, incoming){
 if(!previous || !Array.isArray(previous.items) || !incoming ||
    previous.manga_id!==incoming.manga_id ||
    JSON.stringify(previous.searched_titles)!==JSON.stringify(incoming.searched_titles))return incoming;
 const byIsbn=new Map(previous.items.map(item=>[item.isbn13,item]));
 for(const next of (Array.isArray(incoming.items)?incoming.items:[])){
  const old=byIsbn.get(next.isbn13);
  if(!old || (old.registration_status==="TO_VERIFY" &&
     ["REGISTERED_HERE","REGISTERED_OTHER"].includes(next.registration_status))){
   byIsbn.set(next.isbn13,next);
  }
 }
 const items=Array.from(byIsbn.values());
 return {...incoming,items,count:items.length,
  pages_loaded:Math.max(previous.pages_loaded||previous.page||1,incoming.page||1),
  search_errors:[...new Set([...(previous.search_errors||[]),...(incoming.search_errors||[])])],
  truncated:Boolean(previous.truncated||incoming.truncated),
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
 const entry=x=>{
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
 };
 const sections=FORMAT_ORDER.map(kind=>{
  const group=candidates.filter(x=>x.edition_kind_suggested===kind ||
    (kind==="UNKNOWN"&&!FORMAT_ORDER.includes(x.edition_kind_suggested)));
  if(!group.length)return null;
  const newCount=group.filter(x=>x.registration_status==="TO_VERIFY").length;
  return {kind,group,newCount};
 }).filter(Boolean).sort((a,b)=>b.newCount-a.newCount);
 const groups=sections.map(({kind,group})=>
  '<section class="enrich-format-group"><div class="enrich-format-header"><h4>'+
   L("edition"+kind)+'</h4><span>'+e(group.length)+' '+L("enrichReferences")+'</span></div>'+
   '<div class="enrich-candidates">'+group.map(entry).join("")+'</div></section>'
 ).join("");
 const titles=(Array.isArray(data?.searched_titles)?data.searched_titles:[]).map(e).join(" · ");
 const page=Math.max(1,Math.min(3,Number(data?.pages_loaded||data?.page||1)));
 const navigation='<div class="enrich-pagination"><p>'+
  L("enrichQueries")+': '+titles+' · '+
  L("enrichPagesLoaded")+': '+e(page)+' / '+e(data?.max_pages||3)+'</p>'+
  (data?.has_more_pages?
   '<button type="button" class="btn btn-small btn-soft" data-action="enrich-more">'+
   L("enrichLoadMore")+' →</button>':'')+'</div>';
 return stats+hints+(candidates.length?'<div class="enrich-formats">'+groups+'</div>':
 '<div class="home-empty">'+L("enrichEmpty")+'</div>')+navigation;
}
