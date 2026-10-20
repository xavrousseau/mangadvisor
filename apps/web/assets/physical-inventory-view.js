/** Physical declared inventory, distinct from the BnF verified ISBN collection.
 * UI is read-only and escapes every owner-provided title/edition/status string.
 */
export function physicalInventoryMarkup(data, lang, translate, escape, {compact=false}={}){
  const e=value=>escape(String(value??""));
  const L=key=>e(translate(lang,key));
  const safeCount=x=>Number.isSafeInteger(Number(x))&&Number(x)>=0?Number(x):0;
  if(data?.scope!=="owner_declared_unverified_editions_not_isbn_books") {
    return '<p class="collection-caveat">'+L("physicalUnavailable")+'</p>';
  }
  const raw=Array.isArray(data.items)?data.items:[];
  const groups=new Map();
  for(const item of raw){
    const id=Number(item?.manga_id);
    if(!Number.isSafeInteger(id)||id<=0)continue;
    if(!groups.has(id))groups.set(id,{title:item.work_title||"",editions:[]});
    groups.get(id).editions.push(item);
  }
  const stats=data.summary||{};
  if(!groups.size && !(Array.isArray(data.pending?.items) && data.pending.items.length)){
    return '<section class="physical-inventory-empty"><p>'+L("physicalEmpty")+'</p>'+
      '<p class="collection-caveat">'+L("physicalImportHelp")+'</p></section>';
  }
  const summary=compact?"":'<div class="physical-inventory-stats" aria-label="'+L("physicalSummary")+'">'+
   [["physicalWorks",stats.works],["physicalEditions",stats.edition_entries],
    ["physicalMain",stats.main_volumes],["physicalDuplicates",stats.identical_duplicates],
    ["physicalOther",stats.other_editions_unidentified]].map(([label,count])=>
     '<div class="physical-stat"><small>'+L(label)+'</small><strong>'+
      safeCount(count)+'</strong></div>').join("")+'</div>';
  const cards=[...groups.entries()].map(([id,group])=>{
    const entries=group.editions.map(item=>{
      const parts=[
        ['physicalMain',item.main_volumes],
        ['physicalDuplicates',item.duplicate_copies],
        ['physicalOther',item.other_editions_unknown],
      ];
      return '<div class="physical-edition-entry">'+
        '<div class="physical-edition-heading"><strong>'+
          e(item.edition_declared||translate(lang,"physicalUnspecified"))+'</strong>'+
        (item.format_hint?'<span class="pill">'+e(item.format_hint)+'</span>':"")+'</div>'+
        (item.entry_title && item.entry_title!==group.title?
           '<div class="physical-source-title">'+e(item.entry_title)+'</div>':"")+
        '<div class="physical-edition-counts">'+parts.map(([k,v])=>
          '<span>'+L(k)+' <strong>'+safeCount(v)+'</strong></span>').join("")+'</div>'+
      '</div>';
    }).join("");
    return '<article class="physical-work" data-manga-id="'+id+'">'+
      (compact?"":'<div class="physical-work-header"><h3>'+e(group.title)+'</h3>'+
        '<button type="button" class="btn btn-small btn-soft" data-go="/manga/'+id+'">'+
          L("physicalOpenWork")+' →</button></div>')+
      '<div class="physical-edition-list">'+entries+'</div></article>';
  }).join("");
  // Pending rows are genuine owner declarations but not canonical manga links.
  // They must never display an invented ISBN, status OWNED, or manga detail link.
  const unresolved=compact?[]:(Array.isArray(data.pending?.items)?data.pending.items:[]);
  const pendingLabel=lang==="fr"?"En attente de rapprochement":"Waiting for a catalogue match";
  const pendingHelp=lang==="fr"?
    "Conservees sans les attribuer a une mauvaise oeuvre ou edition. Aucun ISBN n'a ete deduit.":
    "Preserved without assigning an uncertain manga or edition. No ISBN was inferred.";
  const pendingMarkup=unresolved.length?
    '<section class="physical-inventory-pending"><h2 class="section-title">'+pendingLabel+
    ' ('+safeCount(data.pending.count)+' · '+safeCount(data.pending.declared_physical_volumes)+
    (lang==="fr"?" exemplaires":" copies")+')</h2>'+
    '<p class="collection-caveat">'+pendingHelp+'</p>'+
    '<div class="physical-work-grid">'+unresolved.map(item=>{
      const n=safeCount(item.main_volumes)+safeCount(item.duplicate_copies)+
        safeCount(item.other_editions_unknown);
      const status=item.review_status==="REVIEW_AMBIGUOUS"?
        (lang==="fr"?"Plusieurs correspondances possibles":"Multiple possible matches"):
        (lang==="fr"?"Aucune correspondance exacte":"No exact match");
      return '<article class="physical-work"><div class="physical-work-header"><h3>'+
        e(item.entry_title)+'</h3><span class="pill">'+e(status)+'</span></div>'+
        '<p class="muted tiny">'+n+(lang==="fr"?" exemplaires declares":" declared copies")+
        '</p>'+
        '<p class="muted tiny">'+e(item.edition_declared||
          (lang==="fr"?"Édition non précisée":"Unspecified edition"))+'</p>'+
        '<button type="button" class="btn btn-small btn-soft" data-action="pending-match-start" data-key="'+
          e(item.source_key)+'">'+(lang==="fr"?"Rapprocher cette ligne":"Match this entry")+
        '</button></article>';
    }).join("")+'</div><div id="inventory-match-slot"></div></section>':"";
  return summary+
    '<p class="collection-caveat">'+L("physicalScopeNote")+'</p>'+
    '<div class="physical-work-grid">'+cards+'</div>'+pendingMarkup+
    (data.limited?'<p class="collection-caveat">'+L("physicalTruncated")+'</p>':"");
}
