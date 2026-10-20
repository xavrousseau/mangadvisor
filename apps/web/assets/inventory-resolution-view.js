/** Owner-reviewed mapping from a pending physical claim to a manga WORK.
 * Search results are never auto-resolved, editions never inferred.
 */
export function inventoryResolverMarkup(state,{escape,lang="fr"}={}){
  if(!state)return "";
  const e=value=>escape(String(value??""));
  const fr=lang!=="en";
  const title=fr?"Rapprocher une ligne de ma mangathèque":"Match a physical collection entry";
  const selection=state.review;
  const selected=selection?.manga;
  const original=selection?.source||state.pending||{};
  const info=fr
    ?"Sélectionne l'œuvre exacte du catalogue. L'édition et les quantités déclarées restent inchangées. Aucun ISBN ni tome précis n'est inventé."
    :"Choose the exact catalogue work. Your edition and quantities remain unchanged. No ISBN or exact volume is inferred.";
  let items="";
  if(Array.isArray(state.items)&&state.items.length){
    items='<div class="inventory-match-candidates">'+state.items.slice(0,12).map(manga=>{
      const id=Number(manga.id);
      if(!Number.isSafeInteger(id)||id<=0)return "";
      return '<article class="inventory-match-candidate">'+
        '<strong>'+e(manga.title)+'</strong>'+
        (manga.title_english&&manga.title_english!==manga.title?
          '<span class="muted tiny"> · '+e(manga.title_english)+'</span>':"")+
        '<p class="muted tiny">MAL '+e(manga.source_mal_id||"—")+
        ' · '+e(manga.manga_type||"—")+
        (manga.volumes!==null&&manga.volumes!==undefined?
          ' · '+e(manga.volumes)+' '+(fr?"tomes":"volumes"):"")+
        (manga.suggestion_kind==="EXACT_TITLE"?
          ' · '+(fr?"Titre exact":"Exact title"):"")+'</p>'+
        '<button type="button" class="btn btn-small btn-soft" data-action="pending-match-select" data-id="'+e(id)+'">'+
          (fr?"Examiner cette œuvre":"Review this work")+'</button></article>';
    }).join("")+'</div>';
  }else if(state.searched){
    items='<p class="collection-caveat">'+e(fr?
      "Aucun résultat. Essaie le titre international ou un autre mot-clé.":"No results. Try an international name or another keyword.")+'</p>';
  }
  const quantities=Number(original.main_volumes||0)+" "+
    (fr?"tomes principaux":"main volumes")+" · "+Number(original.duplicate_copies||0)+" "+
    (fr?"doublons":"duplicates")+" · "+Number(original.other_editions_unknown||0)+" "+
    (fr?"autres éditions à identifier":"other editions to identify");
  const review=selection?'<section class="inventory-match-review">'+
    '<h4>'+e(fr?"Vérification avant association":"Review before matching")+'</h4>'+
    '<p><strong>'+e(original.entry_title)+'</strong> → <strong>'+e(selected?.title)+'</strong></p>'+
    '<p>'+e(fr?"Édition déclarée : ":"Declared edition: ")+
      e(original.edition_declared||(fr?"non précisée":"unspecified"))+'</p>'+
    '<p class="muted tiny">'+e(quantities)+'</p>'+
    '<p class="collection-caveat">'+e(fr?
      "Je confirme l'œuvre choisie et cette édition. Cela n'ajoute ni ISBN, ni statut Lu, ni détails de tomes.":
      "I confirm this work and edition. No ISBN, read status or individual volumes will be added.")+'</p>'+
    '<label class="inventory-match-ack"><input type="checkbox" id="pending-match-ack"/> '+
      e(fr?"Je confirme ce rapprochement":"I confirm this match")+'</label>'+
    '<button type="button" class="btn btn-primary" data-action="pending-match-confirm" disabled>'+
      e(fr?"Enregistrer l'association":"Save the match")+'</button></section>':"";
  return '<section class="bulk-resolver inventory-match-panel" id="inventory-match-panel">'+
    '<div class="bulk-resolver-head"><h3>'+e(title)+'</h3>'+
    '<button type="button" class="btn btn-small btn-soft" data-action="pending-match-close">'+
    e(fr?"Fermer":"Close")+'</button></div>'+
    '<p><strong>'+e(original.entry_title)+'</strong> · '+
      e(original.edition_declared||(fr?"édition non précisée":"unspecified edition"))+'</p>'+
    '<p class="collection-caveat">'+e(info)+'</p>'+
    '<form id="pending-match-search-form"><label for="pending-match-query">'+
      e(fr?"Chercher une œuvre dans le catalogue":"Search the catalogue")+'</label>'+
      '<div class="search-bar"><input id="pending-match-query" name="query" maxlength="100" '+
      'value="'+e(state.query||"")+'" placeholder="'+e(fr?"Titre du manga":"Manga title")+'"/>'+
      '<button class="btn btn-soft" type="submit">'+e(fr?"Rechercher":"Search")+'</button></div></form>'+
      (state.loading?'<p class="info">'+e(fr?"Recherche en cours…":"Searching…")+'</p>':"")+
      (state.message?'<p class="message" role="alert">'+e(state.message)+'</p>':"")+
      items+review+'</section>';
}
