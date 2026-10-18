/** BnF title-search results are unconfirmed book CANDIDATES. */
export function bibliographyPanel(escape, t, lang, mangaTitle) {
 const e=x=>escape(String(x??""));
 const L=k=>e(t(lang,k));
 return '<section class="bibliography-panel" id="fr-bibliography">'+
 '<div class="section-header"><h3 class="section-title">'+L("biblioHeading")+'</h3></div>'+
 '<p class="page-desc">'+L("biblioIntro")+'</p>'+
 '<form id="fr-bibliography-form"><label for="fr-bibliography-query">'+L("biblioQueryLabel")+'</label>'+
 '<div class="actions"><input id="fr-bibliography-query" class="input" name="title" type="search" minlength="3" maxlength="90" required placeholder="'+
  L("biblioQueryPlaceholder")+'" autocomplete="off">'+
 '<button type="submit" class="btn btn-soft">'+L("biblioSearch")+'</button></div></form>'+
 '<p class="collection-caveat">'+L("biblioSuggestion")+': '+e(mangaTitle)+'</p>'+
 '<div id="fr-bibliography-results" aria-live="polite"></div></section>';
}

export function bibliographyResults(data, escape, t, lang) {
 const e=x=>escape(String(x??""));
 const L=k=>e(t(lang,k));
 const list=Array.isArray(data?.items)?data.items:[];
 const items=list.filter(item=>item?.status==="CANDIDATE_UNCONFIRMED"&&/^[0-9]{13}$/.test(String(item.isbn13||"")));
 const source=url=>{
  try {const parsed=new URL(url);
   return parsed.protocol==="https:"&&parsed.hostname==="catalogue.bnf.fr"?parsed.href:null;
  }catch{return null;}
 };
 const entries=items.map(item=>{
  const link=source(item.source_url);
  const attribution=link?'<a href="'+e(link)+'" target="_blank" rel="noopener noreferrer">'+L("collectionBnfSource")+' ↗</a>':L("collectionBnfSource");
  return '<article class="biblio-candidate"><div class="biblio-candidate-body">'+
   '<span class="biblio-candidate-badge">'+L("biblioCandidate")+'</span>'+
   '<h4>'+e(item.title_fr)+'</h4>'+
   '<p>'+[item.author_fr,item.publisher_fr,item.release_date_text].filter(Boolean).map(e).join(" · ")+'</p>'+
   '<p class="edition-source">ISBN '+e(item.isbn13)+' · '+attribution+
    (item.source_checked_at?' · '+L("collectionSourceDate")+' '+e(String(item.source_checked_at).slice(0,10)):'')+'</p>'+
   '<p class="muted tiny">'+L("biblioLanguage")+': '+e(item.language_recorded||t(lang,"biblioLanguageUnknown"))+'</p>'+
   '</div><button type="button" class="btn btn-small btn-soft" data-action="biblio-verify-isbn" data-isbn="'+e(item.isbn13)+'">'+L("biblioVerify")+' →</button></article>';
 }).join("");
 const notice='<div class="biblio-notice">'+
  '<strong>'+L("biblioResultsCount")+' : '+e(items.length)+'</strong>'+
  '<p>'+L("biblioResultsDisclaimer")+'</p></div>';
 return notice+(items.length?'<div class="biblio-candidates">'+entries+'</div>':
   '<div class="home-empty">'+L("biblioNoResults")+'</div>');
}
