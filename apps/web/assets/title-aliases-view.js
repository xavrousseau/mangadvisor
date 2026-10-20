/** Exact MAL-id linked alternate titles, not French edition identity. */
export function titleAliasesMarkup(data,{escape,lang="fr"}={}){
  if(!data || !Array.isArray(data.items) || !data.items.length)return "";
  const e=v=>escape(String(v??""));
  const fr=lang!=="en";
  const grouped=new Map();
  for(const row of data.items.slice(0,60)){
    const name=String(row.alias||"").trim(),language=row.language_code;
    if(!name||!["fr","en","ja","ja-ro","und"].includes(language))continue;
    const url=String(row.source_ref||"");
    const link=/^https:\/\/mangadex\.org\/title\/[0-9a-f-]{36}$/.test(url)
      ||/^https:\/\/www\.wikidata\.org\/wiki\/Q[1-9][0-9]{0,11}$/.test(url)
      ?'<a href="'+e(url)+'" target="_blank" rel="noopener noreferrer">'+
         e(row.source_name==="MANGADEX_MAL_LINK"?"MangaDex":"Wikidata")+' ↗</a>'
      :'';
    if(!grouped.has(language))grouped.set(language,[]);
    grouped.get(language).push('<li>'+e(name)+
      '<span class="muted tiny"> · '+e(row.source_name||"source")+'</span> '+link+'</li>');
  }
  if(!grouped.size)return "";
  const names={
    fr:fr?"Français":"French",en:fr?"Anglais":"English",
    ja:fr?"Japonais":"Japanese","ja-ro":fr?"Japonais romanisé":"Romanized Japanese",
    und:fr?"Autres noms":"Other names"
  };
  return '<section class="manga-alias-panel" aria-label="'+e(fr?"Noms alternatifs":"Alternative titles")+'">'+
    '<h2 class="section-title">'+e(fr?"Noms de cette œuvre (FR · EN · JP)":"Names of this work (FR · EN · JP)")+'</h2>'+
    '<p class="collection-caveat">'+e(fr?
      "Noms fournis par MAL, Wikidata et MangaDex avec identifiants d'œuvre reliés. Ce ne sont pas des titres d'éditions françaises vérifiées.":
      "Names linked by the work's MAL identity. They are not verified French book editions.")+'</p>'+
    [...grouped.entries()].map(([code,items])=>'<details class="manga-alias-group"'+(code==="fr"?' open':'')+'>'+
      '<summary>'+e(names[code])+' ('+items.length+')</summary><ul>'+items.join("")+'</ul></details>').join("")+
    '</section>';
}
