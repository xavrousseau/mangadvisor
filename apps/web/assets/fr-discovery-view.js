/** Provenance-first browsing of BnF French BOOK records by title.
 * A result is a bibliographic lead, not a confirmed manga mapping or a
 * complete publication listing. User must still confirm the ISBN's series.
 */
export function frDiscoverySearchForm(value, text, escape) {
 const e=v=>escape(String(v??"")), L=k=>e(text(k));
 return '<section class="fr-discovery"><h3>'+L("frSearchTitle")+'</h3>'+
 '<p class="fr-discovery-intro">'+L("frSearchIntro")+'</p>'+
 '<form id="fr-discovery-form" class="fr-discovery-form">'+
 '<label for="fr-discovery-query">'+L("frSearchLabel")+'</label>'+
 '<div class="actions"><input id="fr-discovery-query" name="title" class="input" type="search" maxlength="90" required minlength="3" value="'+e(value)+'" autocomplete="off">'+
 '<button class="btn btn-soft" type="submit">'+L("frSearchAction")+' →</button></div></form>'+
 '<div id="fr-discovery-results" aria-live="polite"></div></section>';
}

function safeBnfLink(raw) {
 try {
  const uri=new URL(raw);
  return uri.protocol==="https:" && uri.hostname==="catalogue.bnf.fr" &&
    /^\/ark:\/12148\/cb[0-9A-Za-z]+$/.test(uri.pathname) && !uri.search && !uri.hash
   ?uri.href:null;
 } catch {return null;}
}

export function frDiscoveryResults(data, knownISBNs, text, escape) {
 const e=v=>escape(String(v??"")),L=k=>e(text(k));
 const known = knownISBNs instanceof Set ? knownISBNs : new Set();
 const items = Array.isArray(data?.items) ? data.items.slice(0,18) : [];
 const cards = items.map(item=>{
  if(item?.verified_isbn!==true || !/^[0-9]{13}$/.test(String(item.isbn13??"")))return "";
  const url=safeBnfLink(item.source_url);
  const already=known.has(item.isbn13);
  const language=["french","mixed","other","unknown"].includes(item.language_status)
    ? item.language_status:"unknown";
  const languageText=L("frSearchLanguage_"+language);
  return '<article class="fr-discovery-card"><div><span class="fr-discovery-label">'+
   L("frSearchRecord")+'</span><h4>'+e(item.title_fr)+'</h4>'+
   '<p>'+[item.author_fr,item.publisher_fr,item.release_date_text].filter(Boolean).map(e).join(" · ")+'</p>'+
   '<p class="fr-discovery-language">'+L("frSearchLanguage")+': '+languageText+'</p>'+
   '<p class="edition-source">ISBN '+e(item.isbn13)+
   (url?' · <a href="'+e(url)+'" rel="noopener noreferrer" target="_blank">'+L("collectionBnfSource")+' ↗</a>':'')+
   ' · '+L("collectionSourceDate")+' '+e(String(item.source_checked_at||"").slice(0,10))+'</p></div>'+
   (already?'<span class="fr-discovery-present">'+L("frSearchAlready")+'</span>':
     '<button type="button" class="btn btn-small btn-soft" data-action="fr-discovery-select" data-isbn="'+e(item.isbn13)+'">'+L("frSearchVerify")+' →</button>')+
   '</article>';
 }).filter(Boolean).join("");
 return '<div class="fr-discovery-found"><h4>'+L("frSearchResults")+' · '+e(items.length)+'</h4>'+
 '<p class="collection-caveat">'+L("frSearchWarning")+'</p>'+
 (cards||'<div class="home-empty">'+L("frSearchNone")+'</div>')+'</div>';
}
