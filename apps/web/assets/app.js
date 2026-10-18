import { t, tag, publication, libraryStatus, GENRES } from "./i18n.js";
import { readingNow, personalPicks, recommendationSources } from "./home.js";
import { renderRecommendationExplanation } from "./explanations.js";

const STATUS = ["READ","READING","OWNED","WANT_TO_READ","DROPPED","NOT_INTERESTED"];
const SCREENS = ["home","discover","recommendations","library"];
const state = {
  lang: ["fr","en"].includes(localStorage.getItem("ma-language")) ? localStorage.getItem("ma-language") : "fr",
  catalogPage:1, catalogQuery:"",catalogGenre:"",catalogFinished:false,
  libraryPage:1,libraryQuery:"",libraryStatus:"",
  recMode:"library",recGoal:"SIMILAR_SAFE",recMinScore:6.8,recFinished:false,recExclude:false,
  selected:[],manualQuery:"",manualMatches:[],recResult:null,
  similar:{},detailCache:{},currentDetail:null,libraryDetail:null,
};
let renderToken = 0, searchTimer = null;
const root=document.querySelector("#app");
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[char]));
const e=escapeHtml;
const L=key=>e(t(state.lang,key));
const tr=value=>e(tag(state.lang,value));
const idNumber=id=>/^[1-9]\d{0,9}$/.test(String(id))?Number(id):null;
const score=value=>value===null||value===undefined||value===""?"—":Number(value).toFixed(1);
const apiRoot="/api";
function qs(path,params={}) {
  const query=new URLSearchParams();
  for(const [k,v] of Object.entries(params)) if(v!==""&&v!==null&&v!==undefined&&v!==false) query.set(k,String(v));
  const value=query.toString();
  return apiRoot+path+(value?"?"+value:"");
}
async function request(path,{method="GET",data,signal}={}){
  const options={method,headers:{"Accept":"application/json"},signal};
  if(data!==undefined){options.headers["Content-Type"]="application/json";options.body=JSON.stringify(data);}
  const response=await fetch(apiRoot+path,options);
  if(!response.ok){
    let message="";
    try{const body=await response.json();message=typeof body.detail==="string"?body.detail:"";}catch{}
    throw Error(message||"HTTP "+response.status);
  }
  return response.json();
}
async function covers(items){
  const ids=[...new Set(items.map(m=>Number(m.manga_id||m.id)).filter(Number.isInteger))];
  if(!ids.length)return {};
  try {
    const r=await request("/covers/mangas?"+new URLSearchParams({ids:ids.slice(0,50).join(",")}));
    return Object.fromEntries((r.covers||[]).filter(x=>x.image_url).map(x=>[x.manga_id,x.image_url]));
  } catch {return {};}
}
function coverUrl(url){
  try {const x=new URL(url);return x.protocol==="https:"&&x.hostname==="cdn.myanimelist.net"?url:null;}catch{return null;}
}
function poster(manga, urls, isButton=true){
  const url=coverUrl(urls?.[manga.manga_id||manga.id]);
  const title=String(manga.title||"Manga");
  const visual=url
    ? '<img class="poster" loading="lazy" src="'+e(url)+'" alt="'+e(title)+'" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><div class="poster-fallback" hidden><span class="poster-letter">M.</span><small>'+e(title)+'</small></div>'
    : '<div class="poster-fallback"><span class="poster-letter">M.</span><small>'+e(title)+'</small></div>';
  return isButton
    ? '<button type="button" class="poster-btn" data-go="/manga/'+e(manga.manga_id||manga.id)+'" aria-label="'+L("details")+': '+e(title)+'">'+visual+'</button>'
    : '<div class="detail-cover">'+visual+'</div>';
}
function stars(m){return m.score===null||m.score===undefined?L("unrecognized"):"★ "+score(m.score)+"/10";}
function badges(list,limit=4){return (list||[]).slice(0,limit).map(x=>'<span class="pill">'+tr(x)+'</span>').join("");}
function card(m,urls){
 const status=publication(state.lang,m.status);
 return '<article class="manga-card">'+poster(m,urls)+'<div class="manga-card-body"><h3 class="manga-card-title">'+e(m.title||"Manga")+'</h3>'+
 '<p class="manga-card-meta">'+stars(m)+' · '+e(status)+'</p><button class="card-open" data-go="/manga/'+e(m.manga_id||m.id)+'">'+L("details")+' &rarr;</button></div></article>';
}
function loadingCards(n=8){return '<div class="manga-grid" aria-busy="true">'+Array.from({length:n},()=>'<div class="skeleton"></div>').join("")+'</div>';}
function errorBox(error,action="refresh"){
  return '<div class="empty" role="alert"><span class="empty-symbol">⚠</span><h2>'+L("error")+'</h2><p>'+L("requestError")+'</p><p class="tiny">'+e(error?.message||"")+'</p><button class="btn btn-primary" data-action="'+e(action)+'">'+L("retry")+'</button></div>';
}
function emptyBox(symbol,title,description,button="",target=""){
  return '<div class="empty"><span class="empty-symbol">'+symbol+'</span><h2>'+title+'</h2><p>'+description+'</p>'+
  (button?'<button class="btn btn-primary" data-go="'+target+'">'+button+' →</button>':"")+'</div>';
}
function paginate(page,hasNext,prefix){
 return '<div class="pagination"><button class="btn" data-action="'+prefix+'-prev" '+(page===1?'disabled':'')+'>← '+L("previous")+'</button>'+
 '<span>'+L("page")+' '+page+'</span><button class="btn" data-action="'+prefix+'-next" '+(hasNext?'':'disabled')+'>'+L("next")+' →</button></div>';
}
function routeInfo(){
 const path=decodeURI(location.pathname);
 if(path==="/")return {view:"home"};
 if(path==="/discover")return {view:"discover"};
 if(path==="/for-you")return {view:"recommendations"};
 if(path==="/library")return {view:"library"};
 const match=path.match(/^\/manga\/([1-9]\d*)$/);
 if(match&&idNumber(match[1]))return {view:"detail",id:Number(match[1])};
 return {view:"not-found"};
}
function shell(){
  const active=routeInfo().view;
  document.documentElement.lang=state.lang;
  document.title="Mangadvisor — "+t(state.lang,active==="detail"?"mangaDetails":active==="recommendations"?"forYou":active==="not-found"?"discover":active);
  const navItems=[
    ["home","/","◈","home"],["discover","/discover","⌕","discover"],
    ["recommendations","/for-you","✧","forYou"],["library","/library","▤","library"]
  ];
  return '<div class="layout"><aside class="sidebar" aria-label="Navigation principale"><a href="/" class="brand" data-go="/">'+
  '<div class="logo-mark">M</div><div class="logo-word">mangadvisor<span>.</span><small>YOUR MANGA UNIVERSE</small></div></a>'+
  '<div class="sidebar-caption">Mangadvisor 1.0</div><nav class="nav">'+navItems.map(([view,url,icon,key])=>
    '<button class="nav-link '+(active===view?'active':'')+'" data-go="'+url+'"'+(active===view?' aria-current="page"':'')+
    '><span class="nav-ico" aria-hidden="true">'+icon+'</span><span>'+L(key)+'</span></button>').join("")+
  '</nav><div class="sidebar-bottom"><p>'+L("footer")+'</p><a class="legacy-link" href="http://localhost:8502" target="_blank" rel="noopener">↗ '+L("openLegacy")+'</a></div></aside>'+
  '<div class="main"><header class="topbar"><div class="crumb">'+L(active==="detail"?"mangaDetails":active==="recommendations"?"forYou":active==="not-found"?"discover":active)+'</div>'+
  '<div class="topbar-right"><label class="field-label" for="app-language">'+L("language")+'</label><select id="app-language" class="locale-select" aria-label="'+L("language")+'"><option value="fr"'+(state.lang==="fr"?" selected":"")+'>🇫🇷 FR</option><option value="en"'+(state.lang==="en"?" selected":"")+'>🇬🇧 EN</option></select><div class="avatar" aria-hidden="true">M</div></div></header>'+
  '<main id="content" class="main-content" tabindex="-1"><div class="skeleton"></div></main></div></div>'+
  '<div class="notice hidden" id="toast" role="status"></div>';
}
function toast(text){
 const area=document.querySelector("#toast");if(!area)return;
 area.textContent=text;area.classList.remove("hidden");
 setTimeout(()=>area.classList.add("hidden"),3500);
}
async function go(path,replace=false){
 if(path.startsWith("/")){
   if(replace)history.replaceState({}, "",path);else history.pushState({}, "",path);
 }
 window.scrollTo({top:0,behavior:"instant"});
 await render();
}
async function render(){
 const token=++renderToken;
 root.innerHTML=shell();
 await view(token);
}
function mount(html,token){
 if(renderToken!==token)return false;
 const target=document.querySelector("#content");
 if(!target)return false;
 target.innerHTML=html;return true;
}
async function view(token){
 const view=routeInfo();
 try {
   if(view.view==="home")return await renderHome(token);
   if(view.view==="discover")return await renderDiscover(token);
   if(view.view==="detail")return await renderDetail(token,view.id);
   if(view.view==="library")return await renderLibrary(token);
   if(view.view==="recommendations")return await renderRecommendations(token);
   mount(emptyBox("⌕",L("noResults"),L("noResultsHelp"),L("startExplore"),"/discover"),token);
 }catch(err){mount(errorBox(err),token);}
}
async function renderHome(token){
 const markup='<section class="hero"><div class="hero-decor" aria-hidden="true"></div><div class="hero-content"><div class="eyebrow">✦ '+L("eyebrow")+'</div>'+
 '<h1>'+ (state.lang==="fr"?'Chaque grande histoire commence par une <em>découverte.</em>':'Every great story begins with <em>discovery.</em>')+'</h1>'+
 '<p>'+L("heroText")+'</p><div class="hero-actions"><button class="btn btn-primary" data-go="/discover">⌕ '+L("startExplore")+' →</button>'+
 '<button class="btn btn-ghost" data-go="/for-you">✧ '+L("getRecs")+'</button></div></div></section>'+
 '<div class="section-header"><div><h2 class="section-title">'+L("whatNext")+'</h2></div></div>'+
 '<div class="quick-actions">'+[
  ["⌕","discover","browseHelp","/discover"],["✧","forYou","recommendationsHelp","/for-you"],["▤","library","libraryHelp","/library"]
 ].map(([icon,title,subtitle,target])=>'<button class="quick-card" data-go="'+target+'"><span class="quick-symbol" aria-hidden="true">'+icon+'</span><span class="quick-arrow">↗</span><h3>'+L(title)+'</h3><p>'+L(subtitle)+'</p></button>').join("")+'</div>'+
 '<section aria-labelledby="home-continue-title"><div class="section-header"><div><h2 class="section-title" id="home-continue-title">'+L("homeContinue")+'</h2>'+
 '<p class="section-caption">'+L("homeContinueDesc")+'</p></div><button class="btn-link" data-go="/library">'+L("homeContinueAction")+' →</button></div>'+
 '<div id="home-continue">'+loadingCards(4)+'</div></section>'+
 '<section aria-labelledby="home-personal-title"><div class="section-header"><div><div class="eyebrow">✦ MANGADVISOR MATCH</div>'+
 '<h2 class="section-title" id="home-personal-title">'+L("homePersonalTitle")+'</h2><p class="section-caption">'+L("homePersonalDesc")+'</p></div>'+
 '<button class="btn-link" data-go="/for-you">'+L("homePersonalAction")+' →</button></div>'+
 '<div id="home-personal"><div class="info">'+L("homePersonalLoading")+'</div>'+loadingCards(2)+'</div></section>'+
 '<section aria-labelledby="home-explore-title"><div class="section-header"><div><h2 class="section-title" id="home-explore-title">'+L("homeExploreTitle")+'</h2>'+
 '<p class="section-caption">'+L("homeExploreDesc")+'</p></div><button class="btn-link" data-go="/discover">'+L("homeExploreAction")+' →</button></div>'+
 '<div id="home-cards">'+loadingCards(5)+'</div></section>'+
 '<div class="section-header"><h2 class="section-title">'+L("quickStart")+'</h2></div>'+
 '<div class="steps">'+[1,2,3].map(i=>'<div class="step"><span class="step-count">'+i+'</span><div><h3>'+L("step"+i)+'</h3><p>'+L("step"+i+"Desc")+'</p></div></div>').join("")+'</div>';
 if(!mount(markup,token))return;

 // Chargement indépendant des trois espaces : un moteur lent n'empêche pas
 // l'utilisateur de parcourir les autres sections.
 const stillHere=()=>token===renderToken&&routeInfo().view==="home";
 const readingTask=(async()=>{
  const target=document.querySelector("#home-continue");
  try{
   const result=await request("/library?status=READING&limit=4");
   const items=readingNow(result.items||[]);
   const urls=await covers(items);
   if(!stillHere()||!target)return;
   target.innerHTML=items.length?'<div class="home-reading-grid">'+items.map(item=>{
     const total=item.volumes??item.owned_volumes;
     const progress=item.read_volumes!=null&&total!=null
       ?'<div class="home-progress">'+e(item.read_volumes)+' / '+e(total)+' '+L("homeProgress")+'</div>':'';
     return '<article class="home-reading-card">'+poster(item,urls)+
       '<div class="home-reading-body"><span class="pill accent">'+e(libraryStatus(state.lang,item.library_status))+'</span>'+
       '<h3>'+e(item.title||"Manga")+'</h3>'+progress+
       '<button class="card-open" data-go="/manga/'+e(item.manga_id)+'">'+L("details")+' →</button></div></article>';
   }).join("")+'</div>':
    '<div class="home-empty"><span aria-hidden="true">▤</span><p>'+L("homeContinueMissing")+'</p>'+
    '<button class="btn btn-small btn-soft" data-go="/discover">'+L("startExplore")+' →</button></div>';
  }catch(error){if(stillHere()&&target)target.innerHTML=errorBox(error);}
 })();
 const browseTask=(async()=>{
  const target=document.querySelector("#home-cards");
  try{
   const result=await request("/mangas?limit=5");
   const items=result.items||[];
   const urls=await covers(items);
   if(!stillHere()||!target)return;
   target.innerHTML=items.length?'<div class="manga-grid">'+items.map(item=>card(item,urls)).join("")+'</div>':
     emptyBox("📚",L("noResults"),L("noResultsHelp"));
  }catch(error){if(stillHere()&&target)target.innerHTML=errorBox(error);}
 })();
 const personalizedTask=(async()=>{
  const target=document.querySelector("#home-personal");
  try{
   // Ne pas présenter une sélection générique comme une recommandation.
   const library=await request("/library?limit=1");
   if(!stillHere()||!target)return;
   if(!(library.items||[]).length){
     target.innerHTML=emptyBox("✧",L("homePersonalTitle"),L("homePersonalMissing"),
       L("startExplore"),"/discover");
     return;
   }
   const result=await request("/recommendations/library",{
     method:"POST",data:{
       limit:6,min_score:6.8,only_finished:false,
       exclude_sensitive_mismatches:false,recommendation_goal:"SIMILAR_SAFE"
     }
   });
   const picks=personalPicks(result.recommendations||[],[],4);
   if(!stillHere()||!target)return;
   if(!picks.length){
     target.innerHTML=emptyBox("✧",L("homePersonalTitle"),L("homePersonalNoMatch"),
       L("homePersonalAction"),"/for-you");
     return;
   }
   const sources=recommendationSources(result);
   const intro=sources.length?
     '<p class="home-source">'+L("homePersonalBecause")+' <strong>'+sources.map(e).join(" · ")+'</strong></p>':'';
   const cards=await recommendationMarkup(picks,token);
   if(stillHere()&&target)target.innerHTML=intro+cards;
  }catch(error){
   if(stillHere()&&target)target.innerHTML=
     '<div class="home-empty"><p>'+L("homePersonalMissing")+'</p>'+
     '<button class="btn btn-small btn-soft" data-go="/for-you">'+L("homePersonalAction")+' →</button></div>';
  }
 })();
 await Promise.allSettled([readingTask,browseTask,personalizedTask]);
}
async function renderDiscover(token){
 const opts=GENRES.map(([value,label])=>'<option value="'+e(value)+'"'+(state.catalogGenre===value?' selected':'')+'>'+
 (label==="allGenres"?L("allGenres"):tr(value))+'</option>').join("");
 const layout='<div class="headline-row"><div><div class="eyebrow">MANGADVISOR · DISCOVERY</div><h1 class="page-title">'+L("startExplore")+'</h1>'+
 '<p class="page-desc">'+L("browseHelp")+'</p></div></div>'+
 '<div class="filters"><div class="field grow"><label for="catalog-query">'+L("search")+'</label>'+
 '<input type="search" class="input" id="catalog-query" autocomplete="off" value="'+e(state.catalogQuery)+'" placeholder="'+L("searchPlaceholder")+'"></div>'+
 '<div class="field medium"><label for="catalog-genre">'+L("filterGenre")+'</label><select class="select" id="catalog-genre">'+opts+'</select></div>'+
 '<label class="check"><input type="checkbox" id="catalog-finished"'+(state.catalogFinished?" checked":"")+'>'+L("finishedOnly")+'</label></div>'+
 '<div id="catalog-results">'+loadingCards(10)+'</div>';
 if(!mount(layout,token))return;
 await updateCatalog(token);
}
async function updateCatalog(token){
 const out=document.querySelector("#catalog-results");if(!out||token!==renderToken)return;
 out.innerHTML=loadingCards(10);
 try{
  const res=await request("/mangas?"+new URLSearchParams({
   limit:"13",offset:String((state.catalogPage-1)*12),
   ...(state.catalogQuery?{q:state.catalogQuery}:{}),
   ...(state.catalogGenre?{genre:state.catalogGenre}:{}),
   ...(state.catalogFinished?{only_finished:"true"}:{})
  }));
  const items=(res.items||[]).slice(0,12),hasNext=(res.items||[]).length>12;
  const urls=await covers(items);
  if(renderToken!==token)return;
  out.innerHTML='<div class="list-head"><span>'+L("page")+' '+state.catalogPage+' · '+items.length+' '+L("showing")+'</span></div>'+
   (items.length?'<div class="manga-grid">'+items.map(m=>card(m,urls)).join("")+'</div>':
    emptyBox("⌕",L("noResults"),L("noResultsHelp")))+
   paginate(state.catalogPage,hasNext,"catalog");
 }catch(err){if(renderToken===token)out.innerHTML=errorBox(err);}
}
async function renderLibrary(token){
 const statusOpts=[["","allStatuses"],...STATUS.map(v=>[v,v])];
 const html='<div class="headline-row"><div><div class="eyebrow">YOUR COLLECTION</div><h1 class="page-title">'+L("library")+'</h1>'+
 '<p class="page-desc">'+L("libraryHelp")+'</p></div>'+
 '<button class="btn btn-soft" data-go="/discover">＋ '+L("startExplore")+'</button></div>'+
 '<div class="filters"><div class="field grow"><label for="lib-query">'+L("librarySearch")+'</label>'+
 '<input id="lib-query" class="input" type="search" autocomplete="off" value="'+e(state.libraryQuery)+'" placeholder="'+L("searchPlaceholder")+'"></div>'+
 '<div class="field medium"><label for="lib-status">'+L("status")+'</label><select id="lib-status" class="select">'+
 statusOpts.map(([value,key])=>'<option value="'+e(value)+'"'+(state.libraryStatus===value?' selected':'')+'>'+
 (value?e(libraryStatus(state.lang,value)):L(key))+'</option>').join("")+'</select></div></div>'+
 '<div id="library-results">'+loadingCards(10)+'</div><div class="section-header"><span class="muted tiny">'+L("importLegacy")+'</span>'+
 '<a href="http://localhost:8502" class="btn-link" target="_blank" rel="noopener">'+L("openLegacy")+' ↗</a></div>';
 if(!mount(html,token))return;
 await updateLibrary(token);
}
async function updateLibrary(token){
 const out=document.querySelector("#library-results");if(!out||renderToken!==token)return;
 out.innerHTML=loadingCards(8);
 try{
  const params=new URLSearchParams({limit:"25",offset:String((state.libraryPage-1)*24)});
  if(state.libraryQuery)params.set("q",state.libraryQuery);
  if(state.libraryStatus)params.set("status",state.libraryStatus);
  const res=await request("/library?"+params);
  const items=(res.items||[]).slice(0,24),hasNext=(res.items||[]).length>24;
  const urls=await covers(items);
  if(renderToken!==token)return;
  const html=items.length?'<div class="list-head"><span>'+L("page")+' '+state.libraryPage+' · '+items.length+' '+L("showing")+'</span></div>'+
   '<div class="manga-grid">'+items.map(m=>'<article class="manga-card">'+poster(m,urls)+'<div class="manga-card-body"><h3 class="manga-card-title">'+e(m.title)+'</h3>'+
   '<p class="manga-card-meta">'+e(libraryStatus(state.lang,m.library_status))+' · '+(m.is_favorite?'♥ ':'')+
   (m.user_score!=null?'★ '+score(m.user_score)+'/10':'—')+'</p><button class="card-open" data-go="/manga/'+m.manga_id+'">'+L("details")+' →</button></div></article>').join("")+'</div>':
   emptyBox("▤",L("libraryEmpty"),L("libraryEmptyHelp"),L("startExplore"),"/discover");
  out.innerHTML=html+paginate(state.libraryPage,hasNext,"library");
 }catch(err){if(token===renderToken)out.innerHTML=errorBox(err);}
}
async function readLibraryItem(manga){
 try{
  const res=await request("/library?"+new URLSearchParams({q:manga.title,limit:"100"}));
  return (res.items||[]).find(x=>Number(x.manga_id)===Number(manga.id))||null;
 }catch{return null;}
}
async function renderDetail(token,id){
 const html='<div><button class="btn-link" data-action="back">← '+L("back")+'</button></div>'+
 '<div id="detail-content" style="padding-top:20px"><div class="skeleton" style="min-height:380px"></div></div>';
 if(!mount(html,token))return;
 try{
  const manga=state.detailCache[id]||await request("/mangas/"+id);
  state.detailCache[id]=manga;state.currentDetail=manga;
  const [urls,libraryItem,translation]=await Promise.all([
    covers([manga]),readLibraryItem(manga),
    state.lang==="fr"&&manga.synopsis?request("/localization/synopsis",{
      method:"POST",data:{manga_id:id,lang:"fr"}
    }).catch(()=>null):Promise.resolve(null)
  ]);
  if(token!==renderToken)return;
  state.libraryDetail=libraryItem;
  const synopsis=translation?.text||manga.synopsis||"";
  const reallyTranslated=state.lang==="fr"&&Boolean(translation?.translated);
  const elements='<section class="detail-hero">'+
   poster(manga,urls,false)+'<div class="detail-info"><div class="eyebrow">MANGADVISOR · '+L("mangaDetails")+'</div>'+
   '<h1>'+e(manga.title)+'</h1>'+
   '<p class="detail-sub">'+(manga.title_japanese?e(manga.title_japanese)+' · ':'')+
    (manga.title_english&&manga.title_english!==manga.title?e(manga.title_english):'')+'</p>'+
   '<div class="tag-row">'+badges(manga.genres,5)+badges(manga.demographics,2)+'</div>'+
   '<p class="muted tiny">'+L("status")+' : '+e(publication(state.lang,manga.status))+' · '+
   (manga.manga_type?tr(manga.manga_type):'Manga')+'</p>'+
   '<div class="actions"><button class="btn btn-primary" data-action="scroll-save">＋ '+L(libraryItem?"inLibrary":"addLibrary")+'</button>'+
    '<button class="btn btn-soft" data-action="similar">✧ '+L("similar")+'</button></div></div></section>'+
   '<div class="detail-stats">'+[
    ["communityRating",stars(manga)],["volumes",manga.volumes??"—"],["chapters",manga.chapters??"—"],["popularity",manga.popularity??"—"]
   ].map(([label,value])=>'<div class="stat"><small>'+L(label)+'</small><strong>'+e(value)+'</strong></div>').join("")+'</div>'+
   '<div class="section-header"><h2 class="section-title">'+L("story")+'</h2></div>'+
   '<article class="synopsis">'+e(synopsis||t(state.lang,"noSynopsis"))+'</article>'+
   (state.lang==="fr"&&manga.synopsis?'<div class="locale-note">'+
      (reallyTranslated?'✦ '+L("translatedNote"): 'ⓘ '+L("originalEnglish")+' · '+L("translationUnavailable"))+'</div>':'')+
   '<div class="section-header"><h2 class="section-title">'+L("genres")+' & '+L("themes")+'</h2></div>'+
   '<div class="tag-row">'+badges([...(manga.genres||[]),...(manga.themes||[])],30)+'</div>'+
   '<div class="section-header" id="save-section"><h2 class="section-title">'+L("library")+'</h2></div>'+
   '<form class="library-editor" id="library-editor">'+
    '<div class="form-grid"><div class="field"><label for="edit-status">'+L("readingStatus")+'</label><select class="select" id="edit-status" name="status">'+
    STATUS.map(value=>'<option value="'+value+'"'+(libraryItem?.library_status===value?' selected':'')+'>'+e(libraryStatus(state.lang,value))+'</option>').join("")+'</select></div>'+
    '<div class="field"><label for="edit-rating">'+L("myRating")+'</label>'+
    '<input type="number" class="input" min="0" max="10" step="0.5" id="edit-rating" name="rating" value="'+e(libraryItem?.user_score??"")+'"></div></div>'+
    '<div class="field"><label for="edit-notes">'+L("notes")+'</label><textarea class="textarea" id="edit-notes" name="notes" placeholder="'+L("notePlaceholder")+'">'+e(libraryItem?.notes??"")+'</textarea></div>'+
    '<div class="form-action-row"><label class="check"><input type="checkbox" name="favorite"'+(libraryItem?.is_favorite?' checked':'')+'>'+L("favorite")+'</label>'+
    '<div class="actions">'+(libraryItem?'<button type="button" data-action="remove-library" class="btn btn-small">'+L("removeLibrary")+'</button>':'')+
    '<button class="btn btn-primary" type="submit">'+L(libraryItem?"updateLibrary":"addLibrary")+'</button></div></div></form>'+
   '<div class="section-header" id="similar-heading"><h2 class="section-title">'+L("similarTitle")+'</h2></div>'+
   '<p class="page-desc">'+L("similarHelp")+'</p><div id="similar-results">'+
    (state.similar[id]?await recommendationMarkup(state.similar[id].recommendations||[],token):'<button class="btn btn-soft" data-action="similar">✧ '+L("similar")+'</button>')+'</div>';
  if(renderToken===token)document.querySelector("#detail-content").innerHTML=elements;
 }catch(err){if(token===renderToken)document.querySelector("#detail-content").innerHTML=errorBox(err);}
}
function recEvidence(m){
 const sources=[
  ["themeMatch",m.common_themes],["genreMatch",m.common_genres],
  ["audienceMatch",m.common_demographics],["communitySignal",m.community_recommended_from]
 ].filter(([,x])=>Array.isArray(x)&&x.length);
 return sources.slice(0,2).map(([key,vals])=>L(key)+": "+vals.slice(0,2).map(x=>tr(x)).join(", ")).join(" · ") || L("whyNone");
}
async function recommendationMarkup(items,token){
 if(!items.length)return emptyBox("✧",L("noRecommendations"),L("noResultsHelp"),L("startExplore"),"/discover");
 const urls=await covers(items);
 if(token!==renderToken)return "";
 return '<div class="info" style="margin:12px 0">'+L("scoreNote")+' '+L("internalNote")+'</div>'+
 '<div class="rec-grid">'+items.map((m,i)=>
  '<article class="rec-card">'+poster(m,urls)+'<div class="rec-body"><span class="rec-rank">✦ #'+(i+1)+'</span>'+
  '<h3>'+e(m.title||"Manga")+'</h3><div class="rec-score"><strong>'+L("scoreLabel")+': '+
  (m.recommendation_score!=null?score(m.recommendation_score)+' '+L("scoreUnit"):'—')+'</strong>'+
  '<span class="muted">'+stars(m)+'</span></div>'+
  '<p>'+recEvidence(m)+'</p>'+
  '<div class="actions"><button class="btn btn-small btn-soft" data-go="/manga/'+e(m.id)+'">'+L("details")+' →</button></div>'+
  '<div class="feedback-actions" role="group" aria-label="'+L("feedbackInfo")+'">'+
  '<button type="button" class="feedback-btn" data-action="feedback" data-feedback="INTERESTED" data-manga-id="'+e(m.id)+'">♡ '+L("feedbackInterested")+'</button>'+
  '<button type="button" class="feedback-btn" data-action="feedback" data-feedback="ALREADY_READ" data-manga-id="'+e(m.id)+'">✓ '+L("feedbackRead")+'</button>'+
  '<button type="button" class="feedback-btn dislike" data-action="feedback" data-feedback="NOT_FOR_ME" data-manga-id="'+e(m.id)+'">× '+L("feedbackDislike")+'</button>'+
  '</div></div>'+
  '<details class="reco-explanation" style="grid-column:1/-1"><summary>✦ '+L("explainTitle")+'</summary>'+
  renderRecommendationExplanation(m, {
    text:key=>t(state.lang,key),
    translateTag:value=>tag(state.lang,value),
    escape:escapeHtml,
  })+
  '</details></article>').join("")+'</div>';
}
async function renderRecommendations(token){
 const libraryMode=state.recMode==="library";
 const goalLabels={"SIMILAR_SAFE":"goalSimilar","READ_NEXT":"goalNext","SHORT_FINISHED":"goalShort"};
 const html='<div class="headline-row"><div><div class="eyebrow">✦ YOUR PERSONAL MANGA MATCH</div>'+
 '<h1 class="page-title">'+L("personalizedTitle")+'</h1><p class="page-desc">'+L("personalizedIntro")+'</p></div></div>'+
 '<details class="improve-panel"><summary>✧ '+L("explainImprove")+'</summary>'+
 '<ul><li>'+L("explainImproveRead")+'</li><li>'+L("explainImproveReact")+'</li><li>'+L("explainImproveGoal")+'</li></ul>'+
 '<button class="btn btn-small btn-soft" data-go="/library">'+L("homeContinueAction")+' →</button></details>'+
 '<div class="toggle-tabs" role="group" aria-label="'+L("forYou")+'">'+
 '<button class="'+(libraryMode?'selected':'')+'" data-action="rec-mode" data-value="library">'+L("libraryMode")+'</button>'+
 '<button class="'+(!libraryMode?'selected':'')+'" data-action="rec-mode" data-value="manual">'+L("manualMode")+'</button></div>'+
 '<div class="option-panel"><h2>'+L(libraryMode?"libraryMode":"manualMode")+'</h2>'+
 '<p>'+L(libraryMode?"libraryModeText":"manualModeText")+'</p>'+
 (libraryMode?'<div class="field medium"><label for="rec-goal">'+L("goal")+'</label>'+
  '<select id="rec-goal" class="select">'+Object.entries(goalLabels).map(([value,key])=>
   '<option value="'+value+'"'+(state.recGoal===value?' selected':'')+'>'+L(key)+'</option>').join("")+'</select></div>':
  '<div class="field grow"><label for="manual-search">'+L("findTitle")+'</label>'+
   '<div class="actions"><input class="input" style="flex:1;min-width:200px" id="manual-search" type="search" placeholder="'+L("searchPlaceholder")+'" value="'+e(state.manualQuery)+'">'+
   '<button class="btn btn-soft" data-action="manual-search">⌕ '+L("search")+'</button></div>'+
   '<div id="manual-suggestions"></div></div>'+
   '<div class="field" style="margin-top:15px"><label>'+L("selectedMangas")+'</label><div class="selected-chips">'+
   (state.selected.length?state.selected.map((x,i)=>'<span class="chip">'+e(x)+'<button type="button" data-action="remove-selected" data-index="'+i+'" aria-label="'+L("cancel")+' '+e(x)+'">×</button></span>').join(""):'<span class="tiny muted">'+L("emptySelected")+'</span>')+
   '</div></div>')+
 '<div class="filters" style="margin:20px 0 12px"><div class="field medium"><label for="rec-min-score">'+L("minRating")+'</label>'+
 '<input type="number" min="0" max="10" step="0.1" class="input" id="rec-min-score" value="'+e(state.recMinScore)+'"></div>'+
 '<label class="check"><input type="checkbox" id="rec-finished"'+(state.recFinished?' checked':'')+'>'+L("finishedOnly")+'</label>'+
 '<label class="check"><input type="checkbox" id="rec-exclude"'+(state.recExclude?' checked':'')+'>'+L("excludeThemes")+'</label></div>'+
 '<button class="btn btn-primary" id="rec-submit" data-action="generate">✧ '+L("recommend")+' →</button></div>'+
 '<div id="rec-results">'+(state.recResult?'':'<div class="info">'+L(libraryMode?"startLibrary":"manualModeText")+'</div>')+'</div>';
 if(!mount(html,token))return;
 if(state.recMode==="manual"&&state.manualMatches.length)updateManualSuggestions();
 if(state.recResult)await showRecResults(token);
}
function updateManualSuggestions(){
 const target=document.querySelector("#manual-suggestions");if(!target)return;
 target.innerHTML=state.manualMatches.length?'<div class="selected-chips">'+state.manualMatches
  .filter(m=>!state.selected.includes(m.title)).slice(0,15)
  .map(m=>'<button class="chip" data-action="add-selected" data-title="'+e(m.title)+'">＋ '+e(m.title)+'</button>').join("")+'</div>':'';
}
async function showRecResults(token){
 const target=document.querySelector("#rec-results");if(!target||!state.recResult)return;
 const result=state.recResult;
 const sources=(result.positive_sources||result.sources||[]).map(s=>s.title).filter(Boolean);
 target.innerHTML='<div class="section-header"><h2 class="section-title">'+L("results")+'</h2></div>'+
  (sources.length?'<div class="list-head">'+L("sources")+': '+sources.slice(0,5).map(e).join(" · ")+'</div>':'')+
  '<div id="rec-cards">'+loadingCards(3)+'</div>';
 const text=await recommendationMarkup(result.recommendations||[],token);
 if(token===renderToken&&document.querySelector("#rec-cards"))document.querySelector("#rec-cards").innerHTML=text;
}
async function generateRecommendations(){
 const btn=document.querySelector("#rec-submit");
 if(btn){btn.disabled=true;btn.textContent=t(state.lang,"loading");}
 try{
  const opts={limit:8,min_score:Number(state.recMinScore)||0,only_finished:state.recFinished,exclude_sensitive_mismatches:state.recExclude};
  if(state.recMode==="manual"&&!state.selected.length){toast(t(state.lang,"emptySelected"));return;}
  const result=state.recMode==="library"
    ?await request("/recommendations/library",{method:"POST",data:{...opts,recommendation_goal:state.recGoal}})
    :await request("/recommendations/profile",{method:"POST",data:{...opts,liked_titles:state.selected}});
  state.recResult=result;
  await showRecResults(renderToken);
 }catch(err){const box=document.querySelector("#rec-results");if(box)box.innerHTML=errorBox(err);}
 finally{if(btn){btn.disabled=false;btn.innerHTML='✧ '+t(state.lang,"recommend")+' →';}}
}
async function sendRecommendationFeedback(button){
 const mangaId=idNumber(button.dataset.mangaId);
 const action=button.dataset.feedback;
 if(!mangaId||!["INTERESTED","ALREADY_READ","NOT_FOR_ME"].includes(action))return;
 const card=button.closest(".rec-card");
 const buttons=card?[...card.querySelectorAll('[data-action="feedback"]')]:[button];
 buttons.forEach(x=>x.disabled=true);
 try{
  await request("/recommendations/feedback",{
    method:"POST",data:{manga_id:mangaId,action}
  });
  const names={
    INTERESTED:"feedbackInterestedSaved",
    ALREADY_READ:"feedbackReadSaved",
    NOT_FOR_ME:"feedbackDislikeSaved"
  };
  toast(t(state.lang,names[action]));
  // Le calcul reste côté API : la sélection courante perd le manga déjà évalué.
  if(state.recResult?.recommendations)
   state.recResult.recommendations=state.recResult.recommendations.filter(
     item=>Number(item.id)!==mangaId
   );
  for(const result of Object.values(state.similar))
   if(Array.isArray(result?.recommendations))
     result.recommendations=result.recommendations.filter(item=>Number(item.id)!==mangaId);
  if(routeInfo().view==="home"){
    // Recalcul de l'accueil sur données réelles après un nouvel avis.
    await render();
  }else{
    card?.remove();
    if(routeInfo().view==="recommendations"){
      const results=document.querySelector("#rec-results");
      if(results&&!results.querySelector(".rec-card")){
        const group=results.querySelector("#rec-cards");
        if(group)group.innerHTML='<div class="info">'+L("feedbackRefresh")+'</div>';
      }
    }
  }
 }catch(error){
  buttons.forEach(x=>x.disabled=false);
  toast(error?.message||t(state.lang,"error"));
 }
}


async function saveLibrary(form){
 const manga=state.currentDetail;if(!manga)return;
 const fd=new FormData(form);
 const value=String(fd.get("rating")??"").trim();
 const rating=value===""?null:Number(value);
 if(rating!==null&&(!Number.isFinite(rating)||rating<0||rating>10)){toast(t(state.lang,"error"));return;}
 const old=state.libraryDetail;
 const payload={
  manga_id:Number(manga.id),library_status:fd.get("status")||"READ",
  user_score:rating,is_favorite:fd.has("favorite"),
  owned_volumes:old?.owned_volumes??null,read_volumes:old?.read_volumes??null,
  notes:String(fd.get("notes")||""),
  started_at:old?.started_at??null,finished_at:old?.finished_at??null,
 };
 try{
  const r=await request("/library/items",{method:"POST",data:payload});
  state.libraryDetail=r.item||payload;state.recResult=null;toast(t(state.lang,"saved"));
  await renderDetail(++renderToken,Number(manga.id));
 }catch(err){toast(err.message);}
}
async function removeLibrary(){
 const manga=state.currentDetail;if(!manga||!confirm(t(state.lang,"confirmRemove")))return;
 try{
  await request("/library/items/"+manga.id,{method:"DELETE"});
  state.libraryDetail=null;state.recResult=null;toast(t(state.lang,"removed"));await render();
 }catch(err){toast(err.message);}
}
async function similarRecommendations(){
 const manga=state.currentDetail;if(!manga)return;
 const node=document.querySelector("#similar-results");if(node)node.innerHTML=loadingCards(2);
 try{
  const result=await request("/recommendations/similar?"+new URLSearchParams({title:manga.title,limit:"6"}));
  state.similar[manga.id]=result;
  if(location.pathname==="/manga/"+manga.id&&node)node.innerHTML=await recommendationMarkup(result.recommendations||[],renderToken);
  document.querySelector("#similar-heading")?.scrollIntoView({block:"start",behavior:"smooth"});
 }catch(err){if(node)node.innerHTML=errorBox(err);}
}
// Event delegation: all actions have a real handler. User content is always escaped.
root.addEventListener("click",async event=>{
 const button=event.target.closest("[data-go],[data-action]");if(!button)return;
 if(button.hasAttribute("data-go")){
  event.preventDefault();await go(button.dataset.go);return;
 }
 const action=button.dataset.action;
 if(action==="refresh")return render();
 if(action==="feedback")return sendRecommendationFeedback(button);
 if(action==="back"){if(history.length>1)history.back();else await go("/discover");return;}
 if(action==="catalog-prev"||action==="catalog-next"){
  state.catalogPage=Math.max(1,state.catalogPage+(action.endsWith("next")?1:-1));
  await updateCatalog(renderToken);window.scrollTo({top:0,behavior:"smooth"});return;
 }
 if(action==="library-prev"||action==="library-next"){
  state.libraryPage=Math.max(1,state.libraryPage+(action.endsWith("next")?1:-1));
  await updateLibrary(renderToken);window.scrollTo({top:0,behavior:"smooth"});return;
 }
 if(action==="scroll-save"){document.querySelector("#save-section")?.scrollIntoView({behavior:"smooth"});return;}
 if(action==="similar")return similarRecommendations();
 if(action==="remove-library")return removeLibrary();
 if(action==="rec-mode"){
  state.recMode=button.dataset.value;state.recResult=null;await render();return;
 }
 if(action==="remove-selected"){
  state.selected.splice(Number(button.dataset.index),1);state.recResult=null;await render();return;
 }
 if(action==="add-selected"){
  if(state.selected.length>=10){toast(t(state.lang,"selectTitles"));return;}
  if(!state.selected.includes(button.dataset.title))state.selected.push(button.dataset.title);
  state.recResult=null;await render();return;
 }
 if(action==="manual-search")return manualSearch();
 if(action==="generate")return generateRecommendations();
});
async function manualSearch(){
 const q=document.querySelector("#manual-search")?.value.trim()||"";
 state.manualQuery=q;if(!q)return;
 const target=document.querySelector("#manual-suggestions");if(target)target.innerHTML='<p class="muted tiny">'+L("loading")+'</p>';
 try{
  const r=await request("/mangas?"+new URLSearchParams({q,limit:"30"}));
  state.manualMatches=r.items||[];updateManualSuggestions();
 }catch(err){if(target)target.innerHTML='<p class="message">'+e(err.message)+'</p>';}
}
root.addEventListener("submit",event=>{
 if(event.target.id==="library-editor"){event.preventDefault();saveLibrary(event.target);}
});
root.addEventListener("change",async event=>{
 const input=event.target;
 if(input.id==="app-language"){
  state.lang=input.value==="en"?"en":"fr";localStorage.setItem("ma-language",state.lang);await render();return;
 }
 if(input.id==="catalog-genre"){state.catalogGenre=input.value;state.catalogPage=1;await updateCatalog(renderToken);}
 if(input.id==="catalog-finished"){state.catalogFinished=input.checked;state.catalogPage=1;await updateCatalog(renderToken);}
 if(input.id==="lib-status"){state.libraryStatus=input.value;state.libraryPage=1;await updateLibrary(renderToken);}
 if(input.id==="rec-goal"){state.recGoal=input.value;state.recResult=null;}
 if(input.id==="rec-min-score"){state.recMinScore=input.value;state.recResult=null;}
 if(input.id==="rec-finished"){state.recFinished=input.checked;state.recResult=null;}
 if(input.id==="rec-exclude"){state.recExclude=input.checked;state.recResult=null;}
});
root.addEventListener("input",event=>{
 const id=event.target.id;
 if(id==="catalog-query"||id==="lib-query"){
  const val=event.target.value.trim().slice(0,120);
  clearTimeout(searchTimer);
  searchTimer=setTimeout(()=>{
   if(id==="catalog-query"){state.catalogQuery=val;state.catalogPage=1;updateCatalog(renderToken);}
   else{state.libraryQuery=val;state.libraryPage=1;updateLibrary(renderToken);}
  },350);
 }
});
root.addEventListener("keydown",event=>{
 if(event.key==="Enter"&&event.target.id==="manual-search"){event.preventDefault();manualSearch();}
});
window.addEventListener("popstate",()=>render());
render();
