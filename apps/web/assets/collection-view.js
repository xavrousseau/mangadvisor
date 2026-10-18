/** View helpers for French book editions, independent from the manga work.
 * All titles, sources, publishers, and URIs are escaped or checked.
 */
export const EDITION_KINDS = ["UNKNOWN","CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER"];
const allowedLink = url => {
  try { const parsed=new URL(url); return parsed.protocol==="https:" && parsed.hostname==="catalogue.bnf.fr" ? url : null; }
  catch { return null; }
};
export function collectionPanel(data, library, lang, tr, escape) {
 const e=value=>escape(String(value??""));
 const L=key=>e(tr(lang,key));
 const editionLabel=type=>L("edition"+(type||"UNKNOWN"));
 const editions=data?.editions||[];
 const legacy=(library?.owned_volumes!=null||library?.read_volumes!=null)
  ?'<p class="collection-legacy">'+L("collectionLegacy")+
   ' · '+L("collectionOwned")+': '+e(library?.owned_volumes??"—")+
   ' · '+L("collectionRead")+': '+e(library?.read_volumes??"—")+'</p>':'';
 const entries=editions.length?'<div class="edition-list">'+editions.map(item=>{
  const url=allowedLink(item.source_url);
  const source=url?'<a href="'+e(url)+'" target="_blank" rel="noopener noreferrer">'+L("collectionBnfSource")+' ↗</a>':L("collectionBnfSource");
  return '<article class="edition-item"><div class="edition-main"><div class="edition-topline">'+
    '<span class="edition-type">'+editionLabel(item.edition_kind)+'</span>'+
    '<span>'+L("collectionTome")+' '+e(item.volume_number)+'</span></div>'+
    '<h3>'+e(item.title_fr)+'</h3>'+
    '<p>'+[item.author_fr,item.publisher_fr,item.release_date_text].filter(Boolean).map(e).join(" · ")+'</p>'+
    '<p class="edition-source">'+L("collectionIsbn")+' '+e(item.isbn13)+' · '+source+
    ' · '+L("collectionSourceDate")+' '+e(String(item.source_checked_at||"").slice(0,10))+'</p>'+
    (item.edition_kind_origin==="USER_CONFIRMED"?'<span class="edition-user">'+L("collectionKindUser")+'</span>':'')+
    '</div><div class="edition-actions" role="group" aria-label="'+e(item.title_fr)+'">'+
    '<button type="button" class="btn btn-small '+(item.is_owned?'btn-primary':'')+'" data-action="volume-owned" data-edition-id="'+e(item.id)+'"'+
    ' data-owned="'+Boolean(item.is_owned)+'" data-read="'+Boolean(item.is_read)+'" aria-pressed="'+Boolean(item.is_owned)+'">'+L("collectionOwned")+'</button>'+
    '<button type="button" class="btn btn-small '+(item.is_read?'btn-primary':'')+'" data-action="volume-read" data-edition-id="'+e(item.id)+'"'+
    ' data-owned="'+Boolean(item.is_owned)+'" data-read="'+Boolean(item.is_read)+'" aria-pressed="'+Boolean(item.is_read)+'">'+L("collectionRead")+'</button>'+
    '</div></article>';
 }).join("")+'</div>':'<div class="home-empty">'+L("collectionEmpty")+'</div>';
 const count=editions.length?
  '<div class="collection-stats">'+
  [[data.owned_books,"collectionOwned"],[data.read_books,"collectionRead"],[data.missing_known_books,"collectionMissing"]]
   .map(([n,label])=>'<span><strong>'+e(n)+'</strong>'+L(label)+'</span>').join("")+
  '</div>':'';
 const form='<form class="edition-lookup" id="edition-isbn-form">'+
 '<label for="edition-isbn">'+L("collectionSearchIsbn")+'</label>'+
 '<div class="actions"><input class="input" id="edition-isbn" name="isbn" maxlength="18" required placeholder="ISBN-13" inputmode="numeric" autocomplete="off">'+
 '<button type="submit" class="btn btn-soft">'+L("collectionSearch")+'</button></div>'+
 '<p class="tiny muted">'+L("collectionIsbnHelp")+'</p></form><div id="edition-preview"></div>';
 return '<section class="collection-panel" id="french-collection">'+
 '<div class="section-header"><div><h2 class="section-title">'+L("collectionTitle")+'</h2>'+
 '<p class="section-caption">'+L("collectionSubtitle")+'</p></div></div>'+
 count+legacy+entries+
 '<p class="collection-caveat">'+L("collectionKnownOnly")+'</p>'+form+'</section>';
}
export function editionPreview(record, lang, tr, escape) {
 const e=value=>escape(String(value??"")), L=key=>e(tr(lang,key));
 const suggested=EDITION_KINDS.includes(record?.edition_kind_suggested)?record.edition_kind_suggested:"UNKNOWN";
 const source=allowedLink(record?.source_url);
 return '<div class="edition-preview"><div class="edition-verified">✓ '+L("collectionVerified")+'</div>'+
 '<h3>'+e(record.title_fr)+'</h3><p>'+[record.author_fr,record.publisher_fr,record.release_date_text].filter(Boolean).map(e).join(" · ")+'</p>'+
 '<p class="edition-source">'+L("collectionIsbn")+' '+e(record.isbn13)+' · '+
 (source?'<a href="'+e(source)+'" target="_blank" rel="noopener noreferrer">'+L("collectionBnfSource")+' ↗</a>':L("collectionBnfSource"))+'</p>'+
 '<p class="collection-caveat">'+L("collectionConfirmTitle")+'</p>'+
 '<div class="form-grid"><div class="field"><label for="edition-type">'+L("collectionEditionType")+'</label><select class="select" id="edition-type">'+
 EDITION_KINDS.map(kind=>'<option value="'+kind+'"'+(kind===suggested?' selected':'')+'>'+L("edition"+kind)+'</option>').join("")+
 '</select></div><div class="field"><label for="edition-number">'+L("collectionTome")+'</label>'+
 '<input id="edition-number" class="input" type="number" min="1" max="9999" value="1" required></div></div>'+
 '<button class="btn btn-primary" type="button" data-action="edition-confirm">'+L("collectionConfirm")+'</button>'+
 '</div>';
}
