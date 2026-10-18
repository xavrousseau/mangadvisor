/** Manga FR: source-attributed BOOK records, never invented series metadata.
 * Escaping/URL restrictions apply to everything read from the catalog.
 */
export const EDITION_KINDS = ["UNKNOWN","CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER"];
const allowedLink = url => {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.hostname === "catalogue.bnf.fr" ? url : null;
  } catch { return null; }
};
export function groupedEditions(editions) {
  const groups = new Map();
  for (const edition of Array.isArray(editions) ? editions : []) {
    const kind = EDITION_KINDS.includes(edition.edition_kind) ? edition.edition_kind : "UNKNOWN";
    if (!groups.has(kind)) groups.set(kind, []);
    groups.get(kind).push(edition);
  }
  return EDITION_KINDS.filter(kind => groups.has(kind)).map(kind => ({
    kind,
    books: groups.get(kind).slice().sort((a,b)=>
      Number(a.volume_number) - Number(b.volume_number) || Number(a.id) - Number(b.id)),
  }));
}
export function collectionPanel(data, library, lang, tr, escape) {
 const e=value=>escape(String(value??""));
 const L=key=>e(tr(lang,key));
 const editionLabel=type=>L("edition"+(EDITION_KINDS.includes(type)?type:"UNKNOWN"));
 const editions=Array.isArray(data?.editions)?data.editions:[];
 const overview=data?.french_overview||{};
 const legacy=(library?.owned_volumes!=null||library?.read_volumes!=null)
   ?'<p class="collection-legacy">'+L("collectionLegacy")+
     ' · '+L("collectionOwned")+': '+e(library?.owned_volumes??"—")+
     ' · '+L("collectionRead")+': '+e(library?.read_volumes??"—")+'</p>':'';
 const notices=editions.length?
   '<section class="fr-notices"><div class="fr-notices-heading">✦ <strong>'+L("frVerifiedInformation")+
   '</strong><span>'+e(overview.reference_count??editions.length)+' '+L("frBookRecords")+'</span></div>'+
   '<p class="fr-notices-caveat">'+L("frEvidenceScope")+'</p>'+
   (Array.isArray(overview.publishers_fr)&&overview.publishers_fr.length
    ?'<div class="fr-notice-line"><strong>'+L("frPublishers")+'</strong><span>'+
     overview.publishers_fr.map(e).join(" · ")+'</span></div>':"")+
   (Array.isArray(overview.authors_fr)&&overview.authors_fr.length
    ?'<div class="fr-notice-line"><strong>'+L("frAuthors")+'</strong><span>'+
     overview.authors_fr.map(e).join(" · ")+'</span></div>':"")+
   '</section>':"";
 const serverProgress=Array.isArray(data?.edition_progress)?data.edition_progress:[];
 const cards=groupedEditions(editions).map(group=>{
  const owned=group.books.filter(book=>Boolean(book.is_owned)).length;
  const read=group.books.filter(book=>Boolean(book.is_read)).length;
  const apiProgress=serverProgress.find(row=>row.edition_kind===group.kind &&
    Number(row.known_books)===group.books.length);
  const total=group.books.length;
  const limitPercent=x=>Math.min(100,Math.max(0,Number.isFinite(Number(x))?Number(x):0));
  const ownedPct=limitPercent(apiProgress?.owned_pct_of_known??(100*owned/total));
  const readPct=limitPercent(apiProgress?.read_pct_of_known??(100*read/total));
  const progress='<div class="edition-progress" aria-label="'+L("progressKnownOnly")+'">'+
    [[owned,ownedPct,"collectionOwned","owned"],[read,readPct,"collectionRead","read"]]
      .map(([num,pct,label,type])=>'<div class="edition-progress-line"><div class="edition-progress-label"><span>'+
        L(label)+'</span><strong>'+e(num)+' / '+e(total)+' '+L("progressReferencedBooks")+'</strong></div>'+
        '<div class="edition-progress-track" role="progressbar" aria-label="'+L(label)+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+e(pct)+'">'+
        '<span class="edition-progress-fill '+type+'" style="width:'+e(pct)+'%"></span></div></div>').join("")+
    '<p class="edition-progress-disclaimer">'+L("progressNoPublishedTotal")+'</p></div>';
  const entries=group.books.map(item=>{
   const url=allowedLink(item.source_url);
   const sourceName=item.source_name?e(item.source_name):L("collectionBnfSource");
   const source=url?'<a href="'+e(url)+'" target="_blank" rel="noopener noreferrer">'+sourceName+' ↗</a>':sourceName;
   const sourceDate=item.source_checked_at?'<span>'+L("collectionSourceDate")+' '+e(String(item.source_checked_at).slice(0,10))+'</span>':"";
   return '<article class="edition-item"><div class="edition-main"><div class="edition-topline">'+
     '<span class="edition-type">'+editionLabel(group.kind)+'</span>'+
     '<span>'+L("collectionTome")+' '+e(item.volume_number)+'</span></div>'+
     '<h3>'+e(item.title_fr)+'</h3>'+
     '<p>'+[item.author_fr,item.publisher_fr,item.release_date_text].filter(Boolean).map(e).join(" · ")+'</p>'+
     '<p class="edition-source"><span>'+L("collectionIsbn")+' '+e(item.isbn13)+'</span> · '+source+
     (sourceDate?' · '+sourceDate:'')+'</p>'+
     (item.edition_kind_origin==="USER_CONFIRMED"?'<span class="edition-user">'+L("collectionKindUser")+'</span>':'')+
     '</div><div class="edition-actions" role="group" aria-label="'+e(item.title_fr)+'">'+
     '<button type="button" class="btn btn-small '+(item.is_owned?'btn-primary':'')+'" data-action="volume-owned" data-edition-id="'+e(item.id)+'"'+
     ' data-owned="'+Boolean(item.is_owned)+'" data-read="'+Boolean(item.is_read)+'" aria-pressed="'+Boolean(item.is_owned)+'">'+L("collectionOwned")+'</button>'+
     '<button type="button" class="btn btn-small '+(item.is_read?'btn-primary':'')+'" data-action="volume-read" data-edition-id="'+e(item.id)+'"'+
     ' data-owned="'+Boolean(item.is_owned)+'" data-read="'+Boolean(item.is_read)+'" aria-pressed="'+Boolean(item.is_read)+'">'+L("collectionRead")+'</button>'+
     '</div></article>';
  }).join("");
  return '<section class="edition-group" data-edition-kind="'+e(group.kind)+'">'+
    '<div class="edition-group-head"><h3>'+editionLabel(group.kind)+'</h3>'+
    '<span>'+e(group.books.length)+' '+L("frBooksListed")+
    ' · '+e(owned)+' '+L("collectionOwned")+' · '+e(read)+' '+L("collectionRead")+'</span></div>'+
    progress+
    '<div class="edition-list">'+entries+'</div></section>';
 }).join("");
 const stats=editions.length?'<div class="collection-stats">'+[
    [data.owned_books,"collectionOwned"],[data.read_books,"collectionRead"],
    [data.missing_known_books,"collectionMissing"],
  ].map(([n,label])=>'<span><strong>'+e(n)+'</strong>'+L(label)+'</span>').join("")+'</div>':"";
 const lookup='<form class="edition-lookup" id="edition-isbn-form">'+
   '<label for="edition-isbn">'+L("collectionSearchIsbn")+'</label>'+
   '<div class="actions"><input class="input" id="edition-isbn" name="isbn" maxlength="18" required placeholder="ISBN-13" inputmode="numeric" autocomplete="off">'+
   '<button type="submit" class="btn btn-soft">'+L("collectionSearch")+'</button></div>'+
   '<p class="tiny muted">'+L("collectionIsbnHelp")+'</p></form><div id="edition-preview"></div>';
 return '<section class="collection-panel" id="french-collection">'+
   '<div class="section-header"><div><h2 class="section-title">'+L("collectionTitle")+'</h2>'+
   '<p class="section-caption">'+L("collectionSubtitle")+'</p></div></div>'+
   notices+stats+legacy+
   (editions.length?cards:'<div class="home-empty">'+L("collectionEmpty")+'</div>')+
   '<p class="collection-caveat">'+L("collectionKnownOnly")+'</p>'+lookup+'</section>';
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
   '<input id="edition-number" class="input" type="number" min="1" max="9999" value="" required placeholder="'+L("collectionTome")+'"></div></div>'+
   '<p class="collection-caveat">'+L("frNoAssumedNumber")+'</p>'+
   '<button class="btn btn-primary" type="button" data-action="edition-confirm">'+L("collectionConfirm")+'</button>'+
   '</div>';
}
