/** Manga titles, ownership declarations and ratings must never be mixed.
 * French localized labels are shown only when explicitly marked verified.
 * Otherwise use an available English title, then the source's original title.
 */
export function preferredMangaTitle(manga,lang="fr"){
  const read=x=>typeof x==="string"?x.trim():"";
  const verified=lang==="fr" && manga?.title_fr_verified===true
    ? read(manga.title_fr):"";
  return verified || read(manga?.title_english) || read(manga?.title) ||
    read(manga?.title_japanese) || (lang==="fr"?"Titre inconnu":"Unknown title");
}

export function declaredCountsByManga(data){
  const result=new Map();
  if(data?.scope!=="owner_declared_unverified_editions_not_isbn_books")return result;
  for(const row of Array.isArray(data.items)?data.items:[]){
    const id=Number(row.manga_id);
    if(!Number.isSafeInteger(id)||id<=0)continue;
    let total=0;
    for(const key of ["main_volumes","duplicate_copies","other_editions_unknown"]){
      const n=Number(row[key]);
      if(!Number.isSafeInteger(n)||n<0)return new Map();
      total+=n;
    }
    result.set(id,(result.get(id)||0)+total);
  }
  return result;
}

export function libraryCardMeta(manga, declared,lang="fr"){
  // "OWNED · —" used to show an absent USER RATING as a misleading
  // possession count. Never display a bare em dash or claim ISBN ownership.
  const status=manga?.library_status||"";
  const parts=[status];
  const score=manga?.user_score;
  if(score!==null&&score!==undefined&&score!==""){
    const n=Number(score);
    if(Number.isFinite(n))parts.push("★ "+n.toFixed(1)+"/10");
  }
  const declaredCount=declared instanceof Map?declared.get(Number(manga?.manga_id)):null;
  if(Number.isSafeInteger(declaredCount)&&declaredCount>=0){
    parts.push(lang==="fr"
      ?declaredCount+" exemplaires déclarés"
      :declaredCount+" declared copies");
  }
  return parts.filter(Boolean).join(" · ");
}
