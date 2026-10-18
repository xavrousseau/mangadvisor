/** Display *registered* French books, never infer a complete published series. */
const VALID_KINDS=new Set(["CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER","UNKNOWN"]);
const safeBnF=url=>{
 try{
  const parsed=new URL(String(url||""));
  return parsed.protocol==="https:"&&parsed.hostname==="catalogue.bnf.fr"&&
    /^\/ark:\/12148\/cb[0-9A-Za-z]+\/?$/.test(parsed.pathname)?parsed.href:null;
 }catch{return null;}
};
export {safeBnF};

export function advisorFrenchEditionsMarkup(summary,{L,e}){
 if(!summary||summary.scope!=="registered_isbns_only"||!summary.registered_isbn_count)return "";
 const groups=Array.isArray(summary.registered_formats)?summary.registered_formats:[];
 const lines=groups.filter(group=>VALID_KINDS.has(group.edition_kind)).map(group=>{
  const books=Array.isArray(group.books_shown)?group.books_shown:[];
  const names=Array.isArray(group.publishers_fr)?group.publishers_fr.filter(Boolean):[];
  const publishers=names.length?names.map(e).join(" · "):L("advisorEditionPublisherUnknown");
  const known=Array.isArray(group.known_volume_numbers)?group.known_volume_numbers:[];
  const rendered=books.map(book=>{
   const url=safeBnF(book.source_url);
   const meta=[
    book.volume_number?L("advisorEditionTome")+" "+e(book.volume_number):null,
    book.publisher_fr?e(book.publisher_fr):null,
    book.release_date_text?e(book.release_date_text):null,
   ].filter(Boolean).join(" · ");
   return '<li class="advisor-edition-book">'+
    '<strong>'+e(book.title_fr||book.isbn13||"")+'</strong>'+
    '<span>'+meta+'</span>'+
    '<div class="advisor-edition-isbn"><span>ISBN-13: '+e(book.isbn13||"")+'</span>'+
    (url?'<a href="'+e(url)+'" target="_blank" rel="noopener noreferrer">'+
     L("advisorEditionSource")+' ↗</a>':"")+'</div></li>';
  }).join("");
  return '<section class="advisor-edition-group">'+
    '<div class="advisor-edition-group-head"><strong>'+L("edition"+group.edition_kind)+'</strong>'+
      '<span>'+e(group.registered_isbn_count)+' '+L("advisorEditionRefs")+'</span></div>'+
    '<p>'+L("advisorEditionPublisher")+': '+publishers+'</p>'+
    '<p>'+L("advisorEditionKnownTomes")+': '+(known.length?known.map(e).join(", "):"—")+'</p>'+
    '<ul>'+rendered+'</ul>'+
    ((group.books_remaining||0)>0?'<p class="advisor-edition-more">+'+e(group.books_remaining)+
     ' '+L("advisorEditionMore")+'</p>':"")+
   '</section>';
 }).join("");
 if(!lines)return "";
 return '<details class="advisor-editions"><summary><span class="advisor-editions-icon" aria-hidden="true">▤</span>'+
  L("advisorEditionExpand")+' · '+e(summary.registered_isbn_count)+' '+
  L("advisorEditionRefs")+'</summary>'+
  '<div class="advisor-edition-groups">'+lines+'</div>'+
  '<p class="advisor-editions-caution">'+L("advisorEditionCaution")+'</p></details>';
}
