/** CSV ISBN import previews: all untrusted metadata are escaped. */
const present = x => x === null || x === undefined ? "—" : String(x);
export function csvPreviewMarkup(data, text, escape) {
 const e=x=>escape(present(x)), L=k=>e(text(k));
 const items=(Array.isArray(data?.items)?data.items:[]);
 const errors=(Array.isArray(data?.errors)?data.errors:[]);
 const rows=items.slice(0,250).map(row=>{
  const matched=row.match==="EXACT_ISBN";
  const description=matched
    ? e(row.title_fr)+" · "+e(row.edition_kind)+" · "+L("collectionTome")+" "+e(row.volume_number)
    : L("bulkUnknown");
  const labels=[row.is_owned?L("collectionOwned"):"",row.is_read?L("collectionRead"):""].filter(Boolean).join(" · ")||L("bulkNoChange");
  return '<tr><td><span class="bulk-status '+(matched?'matched':'pending')+'">'+
   (matched?'✓ '+L("bulkKnown"):'! '+L("bulkUnknown"))+'</span></td>'+
   '<td class="bulk-isbn">'+e(row.isbn13)+'</td><td>'+description+'</td><td>'+labels+
    (matched?'':'<button type="button" class="btn-link bulk-resolve-trigger" data-action="bulk-resolve" data-isbn="'+e(row.isbn13)+'">'+L("resolveStart")+' →</button>')+
    '</td></tr>';
 }).join("");
 const warnings=errors.length
   ?'<details class="bulk-errors"><summary>'+L("bulkInvalid")+' ('+e(errors.length)+')</summary><ul>'+
       errors.map(err=>'<li>'+L("bulkLine")+' '+e(err.line)+': '+e(err.message)+'</li>').join("")+
     '</ul></details>':'';
 const header='<div class="bulk-stats">'+[
  [data.matched,"bulkKnown"],[data.unknown,"bulkUnknown"],
  [data.to_update,"bulkToUpdate"],[errors.length,"bulkInvalid"],
 ].map(([count,key])=>'<span><strong>'+e(count)+'</strong>'+L(key)+'</span>').join("")+'</div>';
 const table=items.length
  ?'<div class="bulk-table-wrap"><table class="bulk-table"><thead><tr><th>'+L("bulkStatus")+
   '</th><th>ISBN</th><th>'+L("bulkTitle")+'</th><th>'+L("bulkAction")+
   '</th></tr></thead><tbody>'+rows+'</tbody></table></div>':"";
 const button=data.matched
  ?'<button type="button" data-action="bulk-apply" class="btn btn-primary">'+L("bulkConfirm")+
   ' ('+e(data.to_update)+' '+L("bulkToUpdate")+')</button>':'';
 return '<div class="bulk-preview"><h3>'+L("bulkPreviewTitle")+'</h3><p>'+L("bulkPreviewHelp")+'</p>'+
  header+table+warnings+'<div id="bulk-resolver-slot"></div>'+button+'</div>';
}
export function reconciliationMarkup(data, text, escape) {
 const e=x=>escape(present(x)), L=k=>e(text(k));
 const items=(Array.isArray(data?.items)?data.items:[]);
 const legacy=data.legacy_totals||{}, isbn=data.isbn_totals||{};
 const summary='<div class="bulk-compare"><div><h4>'+L("bulkLegacy")+'</h4>'+
  '<p>'+L("collectionOwned")+': '+e(legacy.owned)+' · '+L("collectionRead")+': '+e(legacy.read)+'</p></div>'+
  '<div><h4>'+L("bulkVerified")+'</h4>'+
  '<p>'+L("collectionOwned")+': '+e(isbn.owned)+' · '+L("collectionRead")+': '+e(isbn.read)+
  ' · ISBN: '+e(isbn.known)+'</p></div></div>';
 const rows=items.slice(0,25).map(item=>
  '<tr><td>'+e(item.title)+'</td><td>'+e(item.legacy_owned)+' / '+e(item.legacy_read)+
  '</td><td>'+e(item.owned_books)+' / '+e(item.read_books)+
  '</td><td>'+e(item.known_books)+'</td><td><button type="button" class="btn-link" data-go="/manga/'+
    e(item.manga_id)+'">'+L("details")+' →</button></td></tr>').join("");
 const table=items.length?'<div class="bulk-table-wrap"><table class="bulk-table"><thead><tr><th>'+
 L("bulkTitle")+'</th><th>'+L("bulkLegacy")+'</th><th>'+L("bulkVerified")+
 '</th><th>ISBN</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>':
 '<p class="muted">'+L("libraryEmpty")+'</p>';
 return '<div class="bulk-reconcile"><h3>'+L("bulkCompareTitle")+'</h3>'+summary+
   '<p class="collection-caveat">'+L("bulkCompareWarning")+'</p>'+table+
   (items.length>25?'<p class="muted">'+L("bulkFirst25")+'</p>':'')+'</div>';
}
