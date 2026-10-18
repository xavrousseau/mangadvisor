/** Guided, explicit association of an unknown ISBN to a canonical manga.
 * An edition is NEVER inferred from a BnF title; selecting a manga is mandatory.
 * This module produces markup only. No persistence or network calls.
 */
export const EDITION_OPTIONS = Object.freeze([
  "UNKNOWN", "CLASSIC", "DELUXE", "PERFECT", "COLLECTOR", "INTEGRAL", "OTHER",
]);

export function titleSearchSuggestion(title) {
  return String(title || "")
    .replace(/(?:[\s.,:;—-]+)(?:tome|volume|vol\.?)\s*\d+.*$/i, "")
    .trim().slice(0, 120);
}

export function isVerifiedIsbnRecord(record, isbn) {
  return Boolean(record && record.verified_isbn === true &&
    typeof record.isbn13 === "string" && record.isbn13 === isbn &&
    /^[0-9]{13}$/.test(isbn));
}

export function resolverMarkup(state, text, escape) {
  const e=value=>escape(String(value??""));
  const L=key=>e(text(key));
  const isbn=String(state?.isbn||"");
  if(!/^[0-9]{13}$/.test(isbn))return "";
  const record=state.record;
  if(!isVerifiedIsbnRecord(record,isbn)){
    return '<section class="bulk-resolver" id="bulk-resolver" aria-live="polite">'+
      '<div class="bulk-resolver-head"><h3>'+L("resolveTitle")+'</h3>'+
      '<button class="btn btn-small" type="button" data-action="bulk-resolve-close">'+L("resolveCancel")+' ×</button></div>'+
      '<p>'+L("resolveChecking")+' <strong>'+e(isbn)+'</strong></p></section>';
  }
  const safeLink=(()=>{try{
    const uri=new URL(record.source_url);
    return uri.protocol==="https:"&&uri.hostname==="catalogue.bnf.fr"?uri.href:null;
  }catch{return null;}})();
  const source=safeLink?'<a target="_blank" rel="noopener noreferrer" href="'+e(safeLink)+'">'+L("collectionBnfSource")+' ↗</a>':
    L("collectionBnfSource");
  const selected=state.selected;
  const searched=Boolean(state.searched);
  const matches=Array.isArray(state.matches)?state.matches:[];
  const results=searched?'<div class="bulk-resolver-results"><h4>'+L("resolveSearchResults")+'</h4>'+
   (matches.length?matches.map(manga=>{
     if(!Number.isSafeInteger(Number(manga.id))||Number(manga.id)<1)return "";
     return '<button type="button" class="bulk-manga-option" data-action="bulk-resolve-select" data-id="'+
       e(manga.id)+'" aria-pressed="'+Boolean(selected&&Number(selected.id)===Number(manga.id))+'">'+
       '<strong>'+e(manga.title)+'</strong>'+
       '<span>'+L("resolveSelectManga")+' →</span></button>';
   }).join(""):'<p class="muted">'+L("resolveNoMangas")+'</p>')+'</div>':"";
  const kind=EDITION_OPTIONS.includes(state.kind)?state.kind:
    EDITION_OPTIONS.includes(record.edition_kind_suggested)?record.edition_kind_suggested:"UNKNOWN";
  const volume=Number.isInteger(Number(state.volume))&&Number(state.volume)>=1&&Number(state.volume)<=9999
    ?Number(state.volume):1;
  const confirm=selected?'<div class="bulk-resolver-confirm"><h4>'+L("resolveStepThree")+'</h4>'+
    '<p class="resolve-confirmation">'+L("resolveSelectedManga")+': <strong>'+e(selected.title)+'</strong></p>'+
    '<div class="form-grid"><div class="field"><label for="bulk-resolve-kind">'+L("collectionEditionType")+
    '</label><select id="bulk-resolve-kind" class="select">'+EDITION_OPTIONS.map(option=>
      '<option value="'+option+'"'+(option===kind?' selected':'')+'>'+L("edition"+option)+'</option>').join("")+
    '</select></div><div class="field"><label for="bulk-resolve-volume">'+L("collectionTome")+
    '</label><input id="bulk-resolve-volume" class="input" min="1" max="9999" type="number" value="'+e(volume)+'"></div></div>'+
    '<label class="bulk-confirm-check"><input id="bulk-resolve-ack" type="checkbox"> <span>'+
      L("resolveAcknowledgement")+'</span></label>'+
    '<button type="button" class="btn btn-primary" data-action="bulk-resolve-confirm" disabled>'+
      L("resolveSaveEdition")+'</button></div>':"";
  return '<section class="bulk-resolver" id="bulk-resolver" aria-live="polite">'+
    '<div class="bulk-resolver-head"><div><span class="eyebrow">1 / 3 · ISBN</span><h3>'+L("resolveTitle")+'</h3></div>'+
    '<button class="btn btn-small" type="button" data-action="bulk-resolve-close">'+L("resolveCancel")+' ×</button></div>'+
    '<div class="bulk-resolver-notice"><span class="edition-verified">✓ '+L("collectionVerified")+'</span>'+
    '<h4>'+e(record.title_fr)+'</h4>'+
    '<p>'+[record.author_fr,record.publisher_fr,record.release_date_text].filter(Boolean).map(e).join(" · ")+'</p>'+
    '<p>ISBN '+e(isbn)+' · '+source+'</p></div>'+
    '<div class="bulk-resolver-search"><h4>'+L("resolveStepTwo")+'</h4>'+
    '<p>'+L("resolveLinkWarning")+'</p>'+
    '<form id="bulk-resolve-search-form"><label for="bulk-resolve-query">'+L("resolveFindManga")+'</label>'+
    '<div class="actions"><input id="bulk-resolve-query" name="manga" class="input" maxlength="120" autocomplete="off" required value="'+
      e(state.query??titleSearchSuggestion(record.title_fr))+'">'+
    '<button type="submit" class="btn btn-soft">'+L("resolveSearchManga")+'</button></div></form>'+
    results+'</div>'+confirm+
    '<p class="collection-caveat">'+L("resolvePreserveCsv")+'</p></section>';
}
