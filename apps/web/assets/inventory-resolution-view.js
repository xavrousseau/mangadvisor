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
  const discovery=state.discovery;
  const external=state.externalEvidence;
  const info=fr
    ?"Sélectionne l'œuvre exacte du catalogue. L'édition et les quantités déclarées restent inchangées. Aucun ISBN ni tome précis n'est inventé."
    :"Choose the exact catalogue work. Your edition and quantities remain unchanged. No ISBN or exact volume is inferred.";
  let items="";
  if(Array.isArray(state.items)&&state.items.length){
    items='<div class="inventory-match-candidates">'+state.items.slice(0,12).map(manga=>{
      const id=Number(manga.id);
      if(!Number.isSafeInteger(id)||id<=0)return "";
      const riskCodes=manga.reconciliation?.warnings||[];
      const rank=manga.ranking;
      const rankLabels={
        EXACT_CATALOG_TITLE:fr?"Titre original exact":"Exact original title",
        EXACT_WIKIDATA_LINKED_TITLE:fr?"Titre Wikidata lié à MAL":"Wikidata title linked to MAL",
        EXACT_SOURCE_CHECKED_ALIAS:fr?"Alias sourcé lié à MAL":"Source-linked MAL alias",
        EXACT_UNVERIFIED_ALIAS:fr?"Alias non corroboré":"Unverified alias",
        WHOLE_WORD_DISCOVERY:fr?"Mots communs seulement":"Shared words only",
      };
      const rankNote=rank?
        '<p class="muted tiny">'+e(rankLabels[rank.basis]||"")+
        ' · '+e(fr?"Candidat à confirmer, pas une identité vérifiée":"Candidate only, not confirmed identity")+'</p>':"";
      const rankWarnings=rank&&Array.isArray(rank.warnings)&&rank.warnings.length?
        '<p class="collection-caveat">'+e(fr?
          "Indices contradictoires : examen indispensable.":"Conflicting clues: review required.")+'</p>':"";
      const riskTexts={
        ALIAS_CONFLICTS_WITH_OTHER_CANONICAL_TITLE: fr?
          "Alias en conflit avec un titre canonique" : "Alias conflicts with a canonical title",
        ALIAS_UNVERIFIED_OR_UNTRACED: fr?
          "Alias non corroboré" : "Uncorroborated alias",
        JAPANESE_WORK_COUNT_VS_FRENCH_HOLDINGS_DIFFER: fr?
          "Quantité de tomes à contrôler" : "Volume count requires checking",
        DERIVATIVE_OR_TEXT_WORK_TYPE_REVIEW: fr?
          "Œuvre dérivée ou roman possible" : "Possible derivative or novel",
        ONE_SHOT_VS_MULTIPLE_PHYSICAL_BOOKS: fr?
          "One-shot et plusieurs livres déclarés" : "One-shot versus several books",
        NO_CURRENT_TITLE_OR_ALIAS_EVIDENCE: fr?
          "Titre non corroboré" : "Uncorroborated title",
      };
      const warnings=Array.isArray(riskCodes)?riskCodes.slice(0,3)
        .map(x=>riskTexts[x]||"").filter(Boolean):[];
      const riskNote=warnings.length?
        '<p class="collection-caveat" role="note">'+
        e(fr?"Association à vérifier : ":"Match to review: ")+
        e(warnings.join(" · "))+'</p>':"";
      return '<article class="inventory-match-candidate">'+
        '<strong>'+e(manga.title)+'</strong>'+
        (manga.title_english&&manga.title_english!==manga.title?
          '<span class="muted tiny"> · '+e(manga.title_english)+'</span>':"")+
        (manga.matched_alias?
          '<p class="muted tiny">'+e(fr?"Autre titre reconnu : ":"Matched alias: ")+e(manga.matched_alias)+'</p>':"")+
        '<p class="muted tiny">MAL '+e(manga.source_mal_id||"—")+
        ' · '+e(manga.manga_type||"—")+
        (manga.volumes!==null&&manga.volumes!==undefined?
          ' · '+e(manga.volumes)+' '+(fr?"tomes":"volumes"):"")+
        (manga.suggestion_kind==="EXACT_TITLE"?
          ' · '+(fr?"Titre exact":"Exact title"):"")+
        (manga.suggestion_kind==="EXACT_MULTILINGUAL_ALIAS"?
          ' · '+(fr?"Alias multilingue exact (à confirmer)":"Exact multilingual alias (confirm)"):"")+
        (manga.suggestion_kind==="MANGADEX_MAL_LINK"?
          ' · '+(fr?"MangaDex : lien MyAnimeList vérifié (à confirmer)":"MangaDex: verified MAL link (confirm)"):"")+
        '</p>'+
        (manga.source_name==="MANGADEX" && /^https:\/\/mangadex\.org\/title\/[a-f0-9-]{36}$/i.test(String(manga.source_url||""))?
          '<a href="'+e(manga.source_url)+'" target="_blank" rel="noopener noreferrer">MangaDex ↗</a>':"")+
        rankNote+rankWarnings+riskNote+
        '<button type="button" class="btn btn-small btn-soft" data-action="pending-match-select" data-id="'+e(id)+'">'+
          (fr?"Examiner cette œuvre":"Review this work")+'</button></article>';
    }).join("")+'</div>';
  }else if(state.searched){
    items='<p class="collection-caveat">'+e(fr?
      "Aucun résultat. Essaie le titre international ou un autre mot-clé.":"No results. Try an international name or another keyword.")+'</p>';
  }
  const discoveryInfo=discovery?
    '<div class="collection-caveat" role="status"><strong>'+
    e(fr?"Recherche approfondie : ":"Extended search: ")+
    e(discovery.catalogue_candidates_seen||0)+' '+
    e(fr?"candidats analysés":"candidates reviewed")+'</strong>'+
    '<p>'+e(discovery.catalog_truncated?
      (fr?"Résultats partiels : ne pas conclure à une correspondance unique.":
          "Partial results: do not infer a unique match."):
      (fr?"Résultats triés par indices, sans attribution automatique.":
          "Ranked clues only, without automatic matching."))+'</p></div>':"";
  const cross=external;
  const aniRows=Array.isArray(cross?.anilist?.items)?cross.anilist.items.slice(0,5):[];
  const wikiRows=Array.isArray(cross?.wikidata?.items)?cross.wikidata.items.slice(0,4):[];
  const crossStatus=cross?.international_id_evidence?.status||"";
  const sourcesInfo=cross?
    '<section class="inventory-match-review" aria-label="'+e(fr?"Sources internationales":"International sources")+'">'+
    '<h4>'+e(fr?"Vérification des identifiants internationaux":"International identity checks")+'</h4>'+
    '<p class="muted tiny">'+e(fr?
      "Ces liens permettent de vérifier une œuvre. Ils ne certifient aucune édition ni aucun livre possédé.":
      "These links can help check a work. They do not certify editions or ownership.")+'</p>'+
    (crossStatus==="CONTRADICTION_REVIEW"?
      '<p class="collection-caveat">'+e(fr?
        "Des identifiants se contredisent : aucune conclusion automatique.":
        "Conflicting identifiers: no automatic conclusion.")+'</p>':"")+
    (aniRows.length?
      '<p><strong>AniList</strong> · '+e(aniRows.length)+
      e(fr?" pistes documentées":" documented leads")+'</p>'+
      '<ul>'+aniRows.map(item=>{
        const n=Number(item.anilist_id);
        const safe=Number.isSafeInteger(n)&&n>0;
        const name=item.titles?.find(x=>x.language==="english")?.title||
                   item.titles?.find(x=>x.language==="romaji")?.title||"";
        return '<li>'+e(name)+
          ' · MAL '+e(item.source_mal_id||"—")+
          (safe?' <a target="_blank" rel="noopener noreferrer" href="https://anilist.co/manga/'+n+'">AniList ↗</a>':"")+
          '</li>';
      }).join("")+'</ul>':
      '<p class="muted tiny">'+e(fr?
        "AniList : aucune identité exploitable ou source indisponible.":
        "AniList: no usable identity or provider unavailable.")+'</p>')+
    (wikiRows.length?
      '<p><strong>Wikidata</strong> · '+e(wikiRows.length)+
      e(fr?" correspondances possibles":" possible cross-links")+'</p>':"")+
    '<p class="muted tiny">Kitsu : '+e(cross?.kitsu?.status||"—")+'</p>'+
    '</section>':"";
  const quantities=Number(original.main_volumes||0)+" "+
    (fr?"tomes principaux":"main volumes")+" · "+Number(original.duplicate_copies||0)+" "+
    (fr?"doublons":"duplicates")+" · "+Number(original.other_editions_unknown||0)+" "+
    (fr?"autres éditions à identifier":"other editions to identify");
  const existing=Array.isArray(selection?.existing_declarations)?selection.existing_declarations:[];
  const modes=Array.isArray(selection?.allowed_actions)?selection.allowed_actions:["CREATE_DECLARATION"];
  const choice=existing.length?(state.reviewMode||""):"CREATE_DECLARATION";
  const previous=existing.length
    ?'<div class="collection-caveat"><strong>'+e(fr?
      "Déclarations déjà enregistrées :":"Already in your collection:")+'</strong>'+
      '<p>'+existing.map(row=>e(
        (row.edition_declared||(fr?"Édition non précisée":"Unspecified edition"))+
        " — "+row.main_volumes+" "+(fr?"tomes":"volumes")+
        " · "+row.duplicate_copies+" "+(fr?"doublons":"duplicates")+
        " · "+row.other_editions_unknown+" "+(fr?"autres éditions":"other editions")
      )).join(" / ")+'</p><p>'+e(fr?
      "Compare ces livres avant de confirmer : les mêmes volumes ne doivent pas être comptés deux fois.":
      "Compare these books before confirming: the same volumes must never be counted twice.")+'</p></div>'
    :"";
  const modeSelector=existing.length
    ?'<label for="pending-match-mode">'+e(fr?"Décision sur cette ligne :":"Choose an action:")+'</label>'+
     '<select id="pending-match-mode" class="select">'+
     '<option value="">'+e(fr?"Sélectionne une action":"Select an action")+'</option>'+
     (modes.includes("CREATE_DECLARATION")?
       '<option value="CREATE_DECLARATION"'+(choice==="CREATE_DECLARATION"?' selected':"")+'>'+
       e(fr?"Ajouter une édition différente":"Add a separate edition")+'</option>':"")+
     '<option value="MARK_DUPLICATE"'+(choice==="MARK_DUPLICATE"?' selected':"")+'>'+
     e(fr?"Archiver cette ligne déjà comptée (ne rien ajouter)":"Archive already counted record (add nothing)")+
     '</option></select>'+
     '<label class="inventory-match-ack"><input type="checkbox" id="pending-match-existing-ack"/> '+
     e(fr?"J'ai comparé les exemplaires déjà enregistrés":"I compared the existing copies")+'</label>'
    :"";
  const review=selection?'<section class="inventory-match-review">'+
    '<h4>'+e(fr?"Vérification avant association":"Review before matching")+'</h4>'+
    '<p><strong>'+e(original.entry_title)+'</strong> → <strong>'+e(selected?.title)+'</strong></p>'+
    '<p>'+e(fr?"Édition déclarée : ":"Declared edition: ")+
      e(original.edition_declared||(fr?"non précisée":"unspecified"))+'</p>'+
    '<p class="muted tiny">'+e(quantities)+'</p>'+
    previous+modeSelector+
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
      'value="'+e(state.query||"")+'" placeholder="'+e(fr?"Titre du manga":"Manga title")+'"'+
      (state.loading?' disabled':"")+'/>'+
      '<button class="btn btn-soft" type="submit"'+(state.loading?' disabled':"")+'>'+
      e(fr?"Rechercher":"Search")+'</button></div></form>'+
      '<button class="btn btn-small btn-soft" type="button" data-action="pending-match-deep"'+(state.loading?' disabled':"")+'>'+
      e(fr?"Trouver de meilleurs candidats":"Find better candidates")+'</button> '+
      '<button class="btn btn-small btn-soft" type="button" data-action="pending-match-cross"'+(state.loading?' disabled':"")+'>'+
      e(fr?"Vérifier AniList, Kitsu et Wikidata":"Check AniList, Kitsu and Wikidata")+'</button> '+
      '<button class="btn btn-small btn-soft" type="button" data-action="pending-match-external"'+(state.loading?' disabled':"")+'>'+
      e(fr?"Recherche étendue MangaDex (facultative)":"Extended MangaDex search (optional)")+'</button>'+
      '<p class="muted tiny">'+e(fr?
        "Source publique MangaDex : uniquement pour un usage personnel non commercial ; aucune correspondance automatique.":
        "Public MangaDex source: personal non-commercial use only; no automatic matches.")+'</p>'+
      (state.loading?'<p class="info">'+e(fr?"Recherche en cours…":"Searching…")+'</p>':"")+
      (state.message?'<p class="message" role="alert">'+e(state.message)+'</p>':"")+
      discoveryInfo+sourcesInfo+items+review+'</section>';
}
