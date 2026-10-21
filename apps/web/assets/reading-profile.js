/** Read-only reading profile: source is the existing /library/profile API. */
export function readingProfileMarkup(profile, lang="fr", escapeHtml=(v)=>String(v)){
 const fr=lang!=="en", e=escapeHtml;
 const counts=profile?.status_counts||{};
 const stats=[
  [fr?"Lus":"Read",counts.READ||0],
  [fr?"En cours":"Reading",counts.READING||0],
  [fr?"À lire":"To read",counts.WANT_TO_READ||0],
  [fr?"Signaux négatifs":"Negative signals",profile?.negative_item_count||0]
 ];
 const tags=(name,values)=>'<p><strong>'+e(name)+'</strong> '+(
   (values||[]).slice(0,10).map(v=>e(v.name||"")+' ('+e(v.total_weight??0)+')').join(", ") || "—"
 )+'</p>';
 const sources=(profile?.strongest_sources||[]).slice(0,5).map(m=>
   '<li>'+e(m.title||"")+' — '+e(m.library_status||"")+
   ' · '+e(m.user_score??"—")+' / 10</li>').join("");
 const negative=(profile?.negative_items||[]).slice(0,15).map(m=>
   '<li>'+e(m.title||"")+' — '+e(m.library_status||"")+
   ' · '+e(m.negative_reason||"")+'</li>').join("");
 return '<section class="reading-profile">'+
 '<div class="stat-grid">'+stats.map(([label,value])=>
   '<div class="stat-card"><strong>'+e(value)+'</strong><span>'+e(label)+'</span></div>').join("")+'</div>'+
 tags(fr?"Genres dominants :":"Top genres:",profile?.top_genres)+
 tags(fr?"Thèmes dominants :":"Top themes:",profile?.top_themes)+
 tags(fr?"Démographies dominantes :":"Top demographics:",profile?.top_demographics)+
 (sources?'<h3>'+(fr?"Mangas les plus influents":"Most influential manga")+'</h3><ul>'+sources+'</ul>':"")+
 (negative?'<details><summary>'+(fr?"Signaux négatifs / exclusions":"Negative signals / exclusions")+'</summary><ul>'+negative+'</ul></details>':"")+
 '</section>';
}
