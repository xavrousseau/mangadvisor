import { t, tag, publication, libraryStatus, GENRES } from "./i18n.js";
import { collectionPanel, editionPreview } from "./collection-view.js";
import { physicalInventoryMarkup } from "./physical-inventory-view.js";
import { createIsbnScanner } from "./isbn-scanner.js";
import { moodFormMarkup, moodResultsMarkup, MOOD_OPTIONS } from "./mood-view.js";
import {advisorChatMarkup,advisorResultsMarkup,ADVISOR_PROMPTS,ADVISOR_BALANCE_PROMPTS} from "./advisor-view.js";
import { bibliographyPanel, bibliographyResults } from "./bibliography-view.js";
import { enrichmentPanel, enrichmentResults, reconcileEnrichment, mergeEnrichmentPages } from "./enrichment-view.js";
import { csvPreviewMarkup, reconciliationMarkup } from "./bulk-import-view.js";
import { resolverMarkup, isVerifiedIsbnRecord, EDITION_OPTIONS } from "./unknown-isbn-view.js";
import { readingNow, personalPicks, recommendationSources } from "./home.js";
import { explainRecommendation, explainProfile, explainVerifiedSources } from "./explain.js";
import {
  PRESETS, ACCENTS, DEFAULT_APPEARANCE,
  loadAppearance, saveAppearance, applyAppearance,
} from "./appearance.js";

const STATUS = ["READ","READING","OWNED","WANT_TO_READ","DROPPED","NOT_INTERESTED"];
const SCREENS = ["home","discover","recommendations","library","appearance"];
const state = {
  lang: ["fr","en"].includes(localStorage.getItem("ma-language")) ? localStorage.getItem("ma-language") : "fr",
  appearance: loadAppearance(window.localStorage),
  catalogPage:1, catalogQuery:"",catalogGenre:"",catalogFinished:false,
  libraryPage:1,libraryQuery:"",libraryStatus:"",
  recMode:"mood",mood:"MYSTERY",moodLength:"ANY",moodFinished:false,moodUseLibrary:true,moodMinScore:6.5,recGoal:"SIMILAR_SAFE",recBalance:"BALANCED",recMinScore:6.8,recFinished:false,recExclude:false,
  selected:[],manualQuery:"",manualMatches:[],recResult:null,
  advisorHistory:[],advisorContext:{},advisorSeen:[],advisorResponse:null,advisorBusy:false,
  advisorAiMode:"guided",
  similar:{},detailCache:{},currentDetail:null,libraryDetail:null,
  frenchCollection:null,editionPreview:null,biblioCandidates:null,biblioSearchNonce:0,
  enrichmentReport:null,enrichmentNonce:0,enrichmentAlias:"",enrichmentBusy:false,
  bulkPreview:null,bulkCsv:"",bulkResolver:null,
};
let renderToken = 0, searchTimer = null;
const root=document.querySelector("#app");
applyAppearance(document.documentElement, state.appearance);
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
const isbnScanner=createIsbnScanner({root,request,lang:()=>state.lang,escape:escapeHtml,
 onSaved:async ()=>{if(routeInfo().view==="detail")await refreshFrenchCollection();}
});
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
 if(path==="/appearance")return {view:"appearance"};
 const match=path.match(/^\/manga\/([1-9]\d*)$/);
 if(match&&idNumber(match[1]))return {view:"detail",id:Number(match[1])};
 return {view:"not-found"};
}
function shell(){
  const active=routeInfo().view;
  document.documentElement.lang=state.lang;
  document.title="Mangadvisor — "+t(state.lang,active==="detail"?"mangaDetails":active==="recommendations"?"forYou":active==="appearance"?"appearance":active==="not-found"?"discover":active);
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
  '<div class="main"><header class="topbar"><div class="crumb">'+L(active==="detail"?"mangaDetails":active==="recommendations"?"forYou":active==="appearance"?"appearance":active==="not-found"?"discover":active)+'</div>'+
  '<div class="topbar-right"><label class="field-label" for="app-language">'+L("language")+'</label><select id="app-language" class="locale-select" aria-label="'+L("language")+'"><option value="fr"'+(state.lang==="fr"?" selected":"")+'>🇫🇷 FR</option><option value="en"'+(state.lang==="en"?" selected":"")+'>🇬🇧 EN</option></select>'+
  '<button type="button" class="appearance-trigger '+(active==="appearance"?'active':'')+'" data-go="/appearance" aria-label="'+L("appearance")+'" title="'+L("appearance")+'"><span aria-hidden="true">⚙</span><span class="appearance-label">'+L("appearance")+'</span></button>'+
  '<div class="avatar" aria-hidden="true">M</div></div></header>'+
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
 isbnScanner.close();
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
   if(view.view==="appearance")return renderAppearance(token);
   mount(emptyBox("⌕",L("noResults"),L("noResultsHelp"),L("startExplore"),"/discover"),token);
 }catch(err){mount(errorBox(err),token);}
}
function renderAppearance(token){
 const presetCards=PRESETS.map(preset=>
   '<button type="button" class="theme-choice" data-action="appearance-preset" data-value="'+e(preset.id)+'"'+
   ' aria-pressed="'+(state.appearance.preset===preset.id)+'">'+
   '<span class="theme-thumbnail '+e(preset.id)+'" aria-hidden="true">'+
   '<span class="sample-sidebar"></span><span class="sample-bar"></span>'+
   '<span class="sample-hero"><span class="sample-cover"></span><span class="sample-lines"><span></span><span></span></span></span></span>'+
   '<span class="theme-choice-name">'+L(preset.nameKey)+'</span>'+
   '<span class="theme-choice-desc">'+L(preset.descKey)+'</span></button>'
 ).join("");
 const colorCards=ACCENTS.map(accent=>
   '<button type="button" class="accent-choice" data-action="appearance-accent" data-value="'+e(accent.id)+'"'+
   ' aria-pressed="'+(state.appearance.accent===accent.id)+'">'+
   '<span class="accent-swatch" style="background-color:'+e(accent.hex)+'" aria-hidden="true"></span>'+
   '<span>'+L(accent.nameKey)+'</span></button>'
 ).join("");
 const spacingCards=[
  ["comfortable","densityComfortable"],["compact","densityCompact"]
 ].map(([mode,key])=>
   '<button type="button" class="btn" data-action="appearance-density" data-value="'+e(mode)+'"'+
   ' aria-pressed="'+(state.appearance.density===mode)+'">'+L(key)+'</button>'
 ).join("");
 return mount(
  '<div class="eyebrow">✦ MANGADVISOR · DESIGN STUDIO</div>'+
  '<h1 class="page-title">'+L("appearanceTitle")+'</h1>'+
  '<p class="page-desc appearance-intro">'+L("appearanceDescription")+'</p>'+
  '<section class="appearance-section"><h2>'+L("appearancePresets")+'</h2><p>'+L("appearancePresetsHelp")+'</p>'+
  '<div class="appearance-grid" role="group" aria-label="'+L("appearancePresets")+'">'+presetCards+'</div></section>'+
  '<section class="appearance-section"><h2>'+L("appearanceColors")+'</h2><p>'+L("appearanceColorsHelp")+'</p>'+
  '<div class="accent-grid" role="group" aria-label="'+L("appearanceColors")+'">'+colorCards+'</div></section>'+
  '<section class="appearance-section"><h2>'+L("appearanceDensity")+'</h2><p>'+L("appearanceDensityHelp")+'</p>'+
  '<div class="density-controls" role="group" aria-label="'+L("appearanceDensity")+'">'+spacingCards+'</div></section>'+
  '<p class="appearance-note">'+L("appearanceStorage")+'</p>'+
  '<div class="appearance-footer"><button type="button" class="btn" data-action="appearance-reset">↺ '+L("appearanceReset")+'</button>'+
  '<button type="button" class="btn btn-primary" data-go="/">'+L("appearanceReturn")+' →</button></div>',
  token
 );
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
       exclude_sensitive_mismatches:false,recommendation_goal:"SIMILAR_SAFE",
       recommendation_balance:"BALANCED"
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
   const context=recommendationProfileContext(result);
   const cards=await recommendationMarkup(picks,token);
   if(stillHere()&&target)target.innerHTML=intro+context+cards;
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
 '<div class="actions"><button class="btn btn-primary" data-action="open-scanner">▣ '+e(state.lang==="fr"?"Scanner mes tomes":"Scan my volumes")+'</button>'+
 '<button class="btn btn-soft" data-go="/discover">＋ '+L("startExplore")+'</button></div></div>'+
 '<div class="filters"><div class="field grow"><label for="lib-query">'+L("librarySearch")+'</label>'+
 '<input id="lib-query" class="input" type="search" autocomplete="off" value="'+e(state.libraryQuery)+'" placeholder="'+L("searchPlaceholder")+'"></div>'+
 '<div class="field medium"><label for="lib-status">'+L("status")+'</label><select id="lib-status" class="select">'+
 statusOpts.map(([value,key])=>'<option value="'+e(value)+'"'+(state.libraryStatus===value?' selected':'')+'>'+
 (value?e(libraryStatus(state.lang,value)):L(key))+'</option>').join("")+'</select></div></div>'+
 '<div id="library-results">'+loadingCards(10)+'</div>'+
 '<section class="physical-inventory-section"><details id="physical-inventory-workspace" open>'+
 '<summary>▤ '+L("physicalTitle")+'</summary>'+
 '<p class="page-desc">'+L("physicalIntro")+'</p>'+
 '<div id="physical-inventory-results"><div class="info">'+L("loading")+'</div></div>'+
 '</details></section>'+
 '<section class="bulk-workspace"><details id="bulk-import-workspace"'+(state.bulkResolver?' open':'')+'><summary>⌑ '+L("bulkTitle")+'</summary>'+
 '<p class="page-desc">'+L("bulkIntro")+'</p>'+
 '<div class="bulk-steps"><div class="field"><label for="bulk-csv-file">'+L("bulkFile")+'</label>'+
 '<input id="bulk-csv-file" class="input" type="file" accept=".csv,text/csv,text/plain"></div>'+
 '<div class="field"><label for="bulk-csv-text">'+L("bulkPaste")+'</label>'+
 '<textarea class="textarea" id="bulk-csv-text" rows="5" maxlength="80000" spellcheck="false" placeholder="isbn13;possede;lu">'+e(state.bulkCsv)+'</textarea></div>'+
 '<p class="muted tiny">'+L("bulkFormat")+'</p>'+
 '<button type="button" class="btn btn-primary" data-action="bulk-preview">'+L("bulkPreviewAction")+' →</button></div>'+
 '<div id="bulk-import-result">'+(state.bulkPreview?csvPreviewMarkup(state.bulkPreview,key=>t(state.lang,key),escapeHtml):'')+'</div>'+
 '<p class="collection-caveat">'+L("bulkSafety")+'</p>'+
 '<div class="bulk-actions"><button type="button" class="btn btn-soft" data-action="bulk-compare">'+L("bulkCompareAction")+'</button></div>'+
 '<div id="bulk-compare-result"></div></details></section>'+
 '<div class="section-header"><span class="muted tiny">'+L("importLegacy")+'</span>'+
 '<a href="http://localhost:8502" class="btn-link" target="_blank" rel="noopener">'+L("openLegacy")+' ↗</a></div>';
 if(!mount(html,token))return;
 if(state.bulkResolver)drawBulkResolver();
 void updatePhysicalInventory(token);
 await updateLibrary(token);
}
async function updatePhysicalInventory(token){
 const host=document.querySelector("#physical-inventory-results");
 if(!host)return;
 try{
  const physical=await request("/inventory/declarations");
  if(token===renderToken && routeInfo().view==="library")
    host.innerHTML=physicalInventoryMarkup(physical,state.lang,t,escapeHtml);
 }catch(err){
  if(token===renderToken && routeInfo().view==="library")
    host.innerHTML='<p class="collection-caveat">'+L("physicalUnavailable")+'</p>';
 }
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
  const [urls,libraryItem,translation,frCollection,physicalInventory]=await Promise.all([
    covers([manga]),readLibraryItem(manga),
    state.lang==="fr"&&manga.synopsis?request("/localization/synopsis",{
      method:"POST",data:{manga_id:id,lang:"fr"}
    }).catch(()=>null):Promise.resolve(null),
    request("/collection/mangas/"+id+"/editions").catch(()=>null),
    request("/inventory/declarations?manga_id="+id).catch(()=>null)
  ]);
  if(token!==renderToken)return;
  state.libraryDetail=libraryItem;state.frenchCollection=frCollection;state.editionPreview=null;
  state.biblioCandidates=null;state.biblioSearchNonce++;
  state.enrichmentReport=null;state.enrichmentAlias="";state.enrichmentNonce++;
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
    '<button class="btn btn-soft" data-action="similar">✧ '+L("similar")+'</button>'+
 '<button class="btn btn-soft" data-action="open-scanner">▣ '+e(state.lang==="fr"?"Scanner un tome":"Scan a volume")+'</button></div></div></section>'+
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
   (physicalInventory?.items?.length?
     '<section class="physical-inventory-detail"><h2 class="section-title">'+L("physicalTitle")+'</h2>'+
     physicalInventoryMarkup(physicalInventory,state.lang,t,escapeHtml,{compact:true})+
     '</section>':"")+
   '<div id="collection-book-panel">'+(frCollection?collectionPanel(frCollection,libraryItem,state.lang,t,escapeHtml)+
       bibliographyPanel(escapeHtml,t,state.lang,manga.title)+
       enrichmentPanel(escapeHtml,t,state.lang):
     '<div class="home-empty">'+L("collectionLookupError")+'</div>')+'</div>'+
   '<div class="section-header" id="similar-heading"><h2 class="section-title">'+L("similarTitle")+'</h2></div>'+
   '<p class="page-desc">'+L("similarHelp")+'</p><div id="similar-results">'+
    (state.similar[id]?await recommendationMarkup(state.similar[id].recommendations||[],token):'<button class="btn btn-soft" data-action="similar">✧ '+L("similar")+'</button>')+'</div>';
  if(renderToken===token)document.querySelector("#detail-content").innerHTML=elements;
 }catch(err){if(token===renderToken)document.querySelector("#detail-content").innerHTML=errorBox(err);}
}
function recEvidence(m){
 const data=explainRecommendation(m);
 if(!data.factors.length)return L("whyNone");
 return data.factors.slice(0,2).map(x=>
  L(x.label)+": "+x.values.slice(0,2).map(tr).join(", ")
 ).join(" · ");
}
function verifiedSourceExplanation(m) {
 const info=explainVerifiedSources(m);
 if(!info.references.length && !info.matches.length)return "";
 const matches=info.matches.length?info.matches.map(source=>
  '<div class="verified-source"><strong>'+e(source.title)+'</strong>'+
  '<div class="why-factor-tags">'+
  [...source.genres,...source.themes,...source.demographics].map(v=>'<span class="pill">'+tr(v)+'</span>').join("")+
  '</div></div>'
 ).join(""):'<p class="muted tiny">'+L("explainVerifiedNone")+'</p>';
 const sc=info.score;
 const equation=sc&&sc.base!==null&&sc.bonus!==null&&sc.final!==null?
  '<div class="why-section"><h4>'+L("explainScoreEquation")+'</h4>'+
  '<div class="verified-equation"><div><small>'+L("explainInitialScore")+'</small><strong>'+e(sc.base.toFixed(1))+'</strong></div>'+
  '<span>＋</span><div><small>'+L("explainGoalBonus")+'</small><strong>'+e((sc.bonus>=0?"+":"")+sc.bonus.toFixed(1))+'</strong></div>'+
  '<span>＝</span><div class="verified-total"><small>'+L("explainFinalScore")+'</small><strong>'+e(sc.final.toFixed(1))+'</strong></div></div>'+
  '<p class="why-note">'+L("explainComponentsNote")+'</p></div>' : "";
 return '<div class="why-section"><h4>'+L("explainVerified")+'</h4>'+matches+
  '<p class="why-note">'+L("explainVerifiedNote")+'</p></div>'+equation;
}
function recommendationExplanation(m){
 const info=explainRecommendation(m);
 const factors=info.factors.length?info.factors.map(x=>
  '<div class="why-factor"><span class="why-factor-label">'+L(x.label)+'</span>'+
  '<span class="why-factor-tags">'+x.values.map(v=>'<span class="pill">'+tr(v)+'</span>').join("")+'</span></div>'
 ).join(""):'<p class="muted tiny">'+L("explainNothing")+'</p>';
 const components=info.components.length?
  '<div class="why-section"><h4>'+L("explainComponents")+'</h4>'+
  '<div class="why-scores">'+info.components.map(x=>
   '<div class="why-score"><span>'+L(x.label)+'</span><strong>'+e(
     (x.value>0?"+":"")+x.value.toFixed(1)
    )+' '+L("scoreUnit")+'</strong></div>').join("")+'</div>'+
  '<p class="why-note">'+L("explainComponentsNote")+'</p></div>':'';
 const warnings=info.mismatches.length?
  '<div class="why-caution"><strong>⚠ '+L("explainWarnings")+'</strong>'+
  '<div class="why-factor-tags">'+info.mismatches.map(v=>'<span class="pill">'+tr(v)+'</span>').join("")+'</div></div>':'';
 const original=info.originalReason?
   '<details class="why-original"><summary>'+L("explainOriginal")+'</summary>'+
   (state.lang==="en"?'<p class="why-note">'+L("explainOriginalFrench")+'</p>':'')+
   '<p>'+e(info.originalReason)+'</p></details>':'';
 return '<div class="why-explainer">'+verifiedSourceExplanation(m)+
  '<div class="why-section"><h4>'+L("explainEvidence")+'</h4>'+
   factors+'</div>'+components+warnings+original+'</div>';
}
function recommendationProfileContext(response){
 const profile=explainProfile(response);
 if(!profile.sources.length&&!profile.genres.length&&!profile.themes.length)return "";
 const sources=profile.sources.length?
  '<div class="profile-source-grid">'+profile.sources.map(item=>
   '<div class="profile-source"><strong>'+e(item.title)+'</strong><div class="profile-source-meta">'+
   (item.favorite?'<span class="pill accent">♥ '+L("explainProfileFavorite")+'</span>':'')+
   (item.status?'<span class="pill">'+e(libraryStatus(state.lang,item.status))+'</span>':'')+
   (item.score!==null?'<span class="pill">★ '+e(item.score.toFixed(1))+'/10</span>':'')+
   '</div></div>').join("")+'</div>':'<p class="muted tiny">'+L("explainNoSource")+'</p>';
 const group=(key,items)=>items.length?
  '<div class="profile-group"><strong>'+L(key)+'</strong>'+
  '<div class="why-factor-tags">'+items.map(x=>'<span class="pill">'+tr(x)+'</span>').join("")+'</div></div>':'';
 return '<details class="profile-context"><summary>✦ '+L("explainProfileTitle")+'</summary>'+
  '<div class="profile-content"><h4>'+L("explainProfileSources")+'</h4>'+sources+
  '<p class="why-note">'+L("explainProfileCaution")+'</p>'+
  group("explainProfileGenres",profile.genres)+group("explainProfileThemes",profile.themes)+
  '</div></details>';
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
  '<details class="reco-explanation" style="grid-column:1/-1"><summary>✦ '+L("why")+'</summary>'+
   recommendationExplanation(m)+'</details></article>').join("")+'</div>';
}
async function renderAdvisorRecommendations(token){
 // Ollama is optional; API always has a safe deterministic fallback.
 try {
  const status=await request("/advisor/ai-status");
  state.advisorAiMode=status.available?"local_ai":"guided";
 } catch {state.advisorAiMode="guided";}
 if(token!==renderToken)return;
 const html='<div class="headline-row"><div><div class="eyebrow">✧ MANGADVISOR · YOUR MANGA ADVISOR</div>'+
  '<h1 class="page-title">'+L("advisorTitle")+'</h1><p class="page-desc">'+L("advisorPageIntro")+'</p></div></div>'+
  '<div class="toggle-tabs rec-mode-tabs" role="group" aria-label="'+L("forYou")+'">'+
  '<button class="selected" data-action="rec-mode" data-value="advisor">'+L("advisorMode")+'</button>'+
  '<button data-action="rec-mode" data-value="mood">'+L("moodMode")+'</button>'+
  '<button data-action="rec-mode" data-value="library">'+L("libraryMode")+'</button>'+
  '<button data-action="rec-mode" data-value="manual">'+L("manualMode")+'</button></div>'+
  '<div id="advisor-main">'+advisorChatMarkup({
   history:state.advisorHistory,busy:state.advisorBusy,lang:state.lang,
   aiMode:state.advisorAiMode},L,e)+'</div>'+
  '<div id="advisor-results"></div>';
 if(!mount(html,token))return;
 await paintAdvisorResults(token);
}
async function paintAdvisorResults(token){
 const target=document.querySelector("#advisor-results"),response=state.advisorResponse;
 if(!target||!response?.recommendations?.length)return;
 const urls=await covers(response.recommendations);
 if(token!==renderToken||state.recMode!=="advisor")return;
 target.innerHTML=advisorResultsMarkup(response,{L,e,tr,
  poster:m=>poster(m,urls),rating:m=>stars(m),
  published:status=>e(publication(state.lang,status))});
}
async function sendAdvisorMessage(raw){
 const value=String(raw||"").trim();
 if(state.advisorBusy||value.length<2||value.length>500)return;
 state.advisorBusy=true;state.advisorHistory.push({role:"user",text:value});
 state.advisorHistory=state.advisorHistory.slice(-18);
 const currentToken=renderToken;
 if(state.recMode==="advisor"){
  const main=document.querySelector("#advisor-main");
  if(main)main.innerHTML=advisorChatMarkup({history:state.advisorHistory,busy:true,lang:state.lang,aiMode:state.advisorAiMode},L,e);
 }
 try{
  const response=await request("/advisor/ai-message",{method:"POST",data:{
   message:value,context:state.advisorContext,seen_ids:state.advisorSeen,lang:state.lang,limit:6
  }});
  state.advisorContext=response.context||{};
  state.advisorAiMode=response.ai_mode||"guided";
  state.advisorResponse=response;
  if(response.recommendations?.length)
   state.advisorSeen=[...new Set([...state.advisorSeen,...response.recommendations.map(x=>x.id)])].slice(-100);
  state.advisorHistory.push({role:"assistant",text:response.reply||""});
  if(response.limitations?.includes("maturity_not_verified"))
   state.advisorHistory.push({role:"assistant",text:t(state.lang,"advisorMaturityCaution")});
 }catch(err){
  state.advisorHistory.push({role:"assistant",text:err?.message||t(state.lang,"requestError")});
 }finally{
  state.advisorHistory=state.advisorHistory.slice(-18);
  state.advisorBusy=false;
  if(state.recMode==="advisor"&&currentToken===renderToken){
   const main=document.querySelector("#advisor-main");
   if(main)main.innerHTML=advisorChatMarkup({history:state.advisorHistory,busy:false,lang:state.lang,aiMode:state.advisorAiMode},L,e);
   const target=document.querySelector("#advisor-results");
   if(target)target.innerHTML="";
   await paintAdvisorResults(currentToken);
   document.querySelector("#advisor-message")?.focus();
   document.querySelector("#advisor-main")?.scrollIntoView({behavior:"smooth",block:"nearest"});
  }
 }
}
async function renderMoodRecommendations(token){
 const html='<div class="headline-row"><div><div class="eyebrow">✧ MANGADVISOR · GUIDED DISCOVERY</div>'+
  '<h1 class="page-title">'+L("moodPageTitle")+'</h1><p class="page-desc">'+L("moodPageIntro")+'</p></div></div>'+
  '<div class="toggle-tabs rec-mode-tabs" role="group" aria-label="'+L("forYou")+'">'+
  '<button class="selected" data-action="rec-mode" data-value="mood">'+L("moodMode")+'</button>'+
  '<button data-action="rec-mode" data-value="advisor">'+L("advisorMode")+'</button>'+
  '<button data-action="rec-mode" data-value="library">'+L("libraryMode")+'</button>'+
  '<button data-action="rec-mode" data-value="manual">'+L("manualMode")+'</button></div>'+
  moodFormMarkup({mood:state.mood,length:state.moodLength,onlyFinished:state.moodFinished,
   useLibrary:state.moodUseLibrary,minScore:state.moodMinScore},L,e)+
  '<div id="rec-results">'+(state.recResult?'':'<div class="info">'+L("moodFirstHint")+'</div>')+'</div>';
 if(!mount(html,token))return;
 if(state.recResult)await showMoodResults(token);
}
async function showMoodResults(token){
 const target=document.querySelector("#rec-results");
 if(!target||!state.recResult)return;
 const result=state.recResult;
 const personalized=result.personalized===true;
 const banner='<div class="mood-result-summary"><div><span class="eyebrow">'+
  L(personalized?"moodPersonalized":"moodCatalogOnly")+'</span><h2>'+L("moodYourResults")+'</h2>'+
  '<p>'+L(personalized?"moodPersonalizedHelp":"moodCatalogHelp")+'</p></div>'+
  '<span class="mood-count">'+e(result.count)+' '+L("moodResultsCount")+'</span></div>';
 target.innerHTML=banner+'<div id="rec-cards">'+loadingCards(3)+'</div>'+
  '<p class="mood-disclaimer">'+L("moodFrenchCaution")+'</p>';
 const urls=await covers(result.recommendations||[]);
 if(token!==renderToken || state.recMode!=="mood")return;
 const cards=moodResultsMarkup(result.recommendations||[],{
  L,e,tr,poster:m=>poster(m,urls),rating:m=>stars(m),
  published:status=>e(publication(state.lang,status))
 });
 const group=document.querySelector("#rec-cards");
 if(group)group.innerHTML=cards;
}
async function generateMoodDiscoveries(){
 const button=document.querySelector("#rec-submit");
 if(button){button.disabled=true;button.textContent=t(state.lang,"loading");}
 const payload={
  mood:state.mood,length:state.moodLength,only_finished:state.moodFinished,
  use_library:state.moodUseLibrary,min_score:Number(state.moodMinScore),
  limit:8
 };
 try{
  const result=await request("/discovery/mood",{method:"POST",data:payload});
  if(state.recMode!=="mood")return;
  state.recResult=result;
  await showMoodResults(renderToken);
 }catch(err){
  const node=document.querySelector("#rec-results");
  if(node)node.innerHTML=errorBox(err);
 }finally{
  if(button?.isConnected){button.disabled=false;button.innerHTML='✧ '+t(state.lang,"moodFind")+' →';}
 }
}
async function renderRecommendations(token){
 if(state.recMode==="advisor")return renderAdvisorRecommendations(token);
 if(state.recMode==="mood")return renderMoodRecommendations(token);
 const libraryMode=state.recMode==="library";
 const goalLabels={"SIMILAR_SAFE":"goalSimilar","READ_NEXT":"goalNext","SHORT_FINISHED":"goalShort"};
 const html='<div class="headline-row"><div><div class="eyebrow">✦ YOUR PERSONAL MANGA MATCH</div>'+
 '<h1 class="page-title">'+L("personalizedTitle")+'</h1><p class="page-desc">'+L("personalizedIntro")+'</p></div></div>'+
 '<details class="improve-panel"><summary>✧ '+L("explainImprove")+'</summary>'+
 '<p>'+L("explainImproveText")+'</p>'+
 '<button class="btn btn-small btn-soft" data-go="/library">'+L("explainImproveAction")+' →</button></details>'+
 '<div class="toggle-tabs" role="group" aria-label="'+L("forYou")+'">'+
 '<button class="'+(libraryMode?'selected':'')+'" data-action="rec-mode" data-value="library">'+L("libraryMode")+'</button>'+
 '<button class="'+(!libraryMode?'selected':'')+'" data-action="rec-mode" data-value="manual">'+L("manualMode")+'</button>'+
 '<button data-action="rec-mode" data-value="mood">'+L("moodMode")+'</button>'+
 '<button data-action="rec-mode" data-value="advisor">'+L("advisorMode")+'</button></div>'+
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
 '<div class="filters" style="margin:20px 0 12px"><div class="field medium"><label for="rec-balance">'+L("recBalance")+'</label>'+
 '<select id="rec-balance" class="select">'+
 [["CLOSE","recBalanceClose"],["BALANCED","recBalanceBalanced"],["EXPLORE","recBalanceExplore"]].map(([mode,key])=>
   '<option value="'+mode+'"'+(state.recBalance===mode?' selected':'')+'>'+L(key)+'</option>').join("")+'</select></div>'+
 '<p class="rec-balance-help">'+L("recBalanceHelp")+'</p>'+
 '<div class="field medium"><label for="rec-min-score">'+L("minRating")+'</label>'+
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
  recommendationProfileContext(result)+
  '<div id="rec-cards">'+loadingCards(3)+'</div>';
 const diagnosis=result.quality_diagnostic;
 if(diagnosis&&state.recBalance!=="CLOSE"){
   const count=diagnosis.after||{};
   const stats='<div class="rec-quality"><strong>'+L("recQualityStats")+'</strong>'+
     '<span>'+L("recQualityNote")+'</span>'+
     '<span>'+e(count.limited_evidence_count??0)+' '+L("recQualityLimited")+'</span>'+
     '<span>'+e(count.repeated_overlap_pairs??0)+' '+L("recQualityRepeat")+'</span></div>';
   target.insertAdjacentHTML("beforeend",stats);
 }
 const text=await recommendationMarkup(result.recommendations||[],token);
 if(token===renderToken&&document.querySelector("#rec-cards"))document.querySelector("#rec-cards").innerHTML=text;
}
async function generateRecommendations(){
 const btn=document.querySelector("#rec-submit");
 if(btn){btn.disabled=true;btn.textContent=t(state.lang,"loading");}
 try{
  const opts={limit:8,min_score:Number(state.recMinScore)||0,only_finished:state.recFinished,exclude_sensitive_mismatches:state.recExclude,recommendation_balance:state.recBalance};
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
  if(state.advisorResponse?.recommendations)
   state.advisorResponse.recommendations=state.advisorResponse.recommendations.filter(item=>Number(item.id)!==mangaId);
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


async function refreshFrenchCollection(){
 const manga=state.currentDetail;
 if(!manga)return;
 const target=document.querySelector("#collection-book-panel");
 if(!target)return;
 try{
  const result=await request("/collection/mangas/"+manga.id+"/editions");
  if(routeInfo().view!=="detail"||Number(routeInfo().id)!==Number(manga.id))return;
  state.frenchCollection=result;
  state.enrichmentReport=reconcileEnrichment(state.enrichmentReport,result.editions);
  target.innerHTML=collectionPanel(result,state.libraryDetail,state.lang,t,escapeHtml)+
   bibliographyPanel(escapeHtml,t,state.lang,manga.title)+
   enrichmentPanel(escapeHtml,t,state.lang);
  if(state.biblioCandidates)showBibliographyResults();
  const aliasInput=document.querySelector("#enrich-alt-title");
  if(aliasInput)aliasInput.value=state.enrichmentAlias;
  if(state.enrichmentReport)showEnrichmentResults();
 }catch(error){toast(error?.message||t(state.lang,"error"));}
}
function showEnrichmentResults(){
 const target=document.querySelector("#fr-enrichment-results");
 if(target&&state.enrichmentReport){
  target.innerHTML=enrichmentResults(state.enrichmentReport,escapeHtml,t,state.lang);
 }
}
async function discoverFrenchEnrichment(button,loadMore=false){
 const manga=state.currentDetail;
 if(!manga||routeInfo().view!=="detail"||state.enrichmentBusy)return;
 const previous=state.enrichmentReport;
 const page=loadMore?Number(previous?.pages_loaded||previous?.page||1)+1:1;
 if(page>3||(loadMore&&!previous?.has_more_pages))return;
 const nonce=++state.enrichmentNonce;
 const target=document.querySelector("#fr-enrichment-results");
 if(!target)return;
 if(!loadMore){
  state.enrichmentAlias=String(document.querySelector("#enrich-alt-title")?.value||"").trim();
  state.enrichmentReport=null;
  target.innerHTML='<div class="info">'+L("enrichLoading")+'</div>';
 }else{
  target.insertAdjacentHTML("beforeend",'<p class="info" id="enrich-more-loading">'+L("enrichLoading")+'</p>');
 }
 state.enrichmentBusy=true;
 button.disabled=true;
 try{
  const query=new URLSearchParams();
  if(page>1)query.set("page",String(page));
  if(state.enrichmentAlias)query.set("alternate_title",state.enrichmentAlias);
  const suffix=query.toString()?"?"+query.toString():"";
  const data=await request("/collection/mangas/"+manga.id+"/enrichment"+suffix);
  if(nonce!==state.enrichmentNonce||routeInfo().view!=="detail"||
    Number(routeInfo().id)!==Number(manga.id))return;
  const combined=loadMore?mergeEnrichmentPages(previous,data):data;
  state.enrichmentReport=reconcileEnrichment(combined,state.frenchCollection?.editions);
  showEnrichmentResults();
 }catch(error){
  if(nonce===state.enrichmentNonce){
   if(loadMore){
    target.insertAdjacentHTML("beforeend",'<div class="message">'+
      e(error.message||t(state.lang,"enrichError"))+'</div>');
   }else{
    target.innerHTML='<div class="message">'+
      e(error.message||t(state.lang,"enrichError"))+'</div>';
   }
  }
 }finally{
  state.enrichmentBusy=false;
  document.querySelector("#enrich-more-loading")?.remove();
  if(button.isConnected)button.disabled=false;
 }
}
function showBibliographyResults(){
 const target=document.querySelector("#fr-bibliography-results");
 if(!target)return;
 if(state.biblioCandidates){
   target.innerHTML=bibliographyResults(state.biblioCandidates,escapeHtml,t,state.lang);
 }
}
async function searchFrenchBibliography(form){
 const manga=state.currentDetail;
 if(!manga||routeInfo().view!=="detail")return;
 const query=String(new FormData(form).get("title")||"").trim();
 if(!query)return;
 const nonce=++state.biblioSearchNonce;
 state.biblioCandidates=null;
 const target=document.querySelector("#fr-bibliography-results");
 if(!target)return;
 target.innerHTML='<div class="info">'+L("loading")+'</div>';
 try{
  const data=await request("/collection/mangas/"+manga.id+"/discover?"+
    new URLSearchParams({title:query}));
  if(nonce!==state.biblioSearchNonce||routeInfo().view!=="detail"||
    Number(routeInfo().id)!==Number(manga.id))return;
  state.biblioCandidates=data;
  showBibliographyResults();
 }catch(error){
  if(nonce!==state.biblioSearchNonce)return;
  target.innerHTML='<div class="message">'+e(error.message||t(state.lang,"biblioSearchError"))+'</div>';
 }
}
async function verifyBibliographyCandidate(button){
 const isbn=String(button.dataset.isbn||"");
 if(!/^[0-9]{13}$/.test(isbn))return;
 const item=button.dataset.action==="enrich-verify-isbn"
  ?state.enrichmentReport?.items?.find(entry=>
    entry.isbn13===isbn&&entry.registration_status==="TO_VERIFY")
  :state.biblioCandidates?.items?.find(entry=>
    entry.isbn13===isbn&&entry.status==="CANDIDATE_UNCONFIRMED");
 if(!item||routeInfo().view!=="detail")return;
 const form=document.querySelector("#edition-isbn-form");
 const input=document.querySelector("#edition-isbn");
 if(!form||!input)return;
 input.value=isbn;
 await searchFrenchIsbn(form); // Existing endpoint RECHECKS the ISBN, no write.
 const panel=document.querySelector("#edition-preview");
 if(panel?.querySelector(".edition-preview")){
   panel.insertAdjacentHTML("afterbegin",'<p class="collection-caveat">'+
      L("biblioVerifyInstruction")+'</p>');
 }
 panel?.scrollIntoView({behavior:"smooth",block:"nearest"});
}
async function searchFrenchIsbn(form){
 const manga=state.currentDetail;if(!manga)return;
 const input=String(new FormData(form).get("isbn")||"").trim();
 const preview=document.querySelector("#edition-preview");if(!preview)return;
 state.editionPreview=null;
 preview.innerHTML='<div class="info">'+L("loading")+'</div>';
 try{
  const record=await request("/collection/isbn/"+encodeURIComponent(input));
  if(Number(state.currentDetail?.id)!==Number(manga.id))return;
  state.editionPreview=record;
  preview.innerHTML=editionPreview(record,state.lang,t,escapeHtml);
 }catch(error){preview.innerHTML='<div class="message">'+e(error.message||t(state.lang,"collectionLookupError"))+'</div>';}
}
async function confirmFrenchEdition(button){
 const manga=state.currentDetail, preview=state.editionPreview;
 if(!manga||!preview)return;
 const edition_kind=document.querySelector("#edition-type")?.value;
 const volume_number=Number(document.querySelector("#edition-number")?.value);
 if(!Number.isInteger(volume_number)||volume_number<1||volume_number>9999)return;
 button.disabled=true;
 try{
  await request("/collection/mangas/"+manga.id+"/editions",{
    method:"POST",data:{isbn13:preview.isbn13,edition_kind,volume_number}
  });
  state.editionPreview=null;
  await refreshFrenchCollection();
  toast(t(state.lang,"collectionSaved"));
 }catch(error){button.disabled=false;toast(error.message||t(state.lang,"error"));}
}
async function updateFrenchVolume(button){
 const id=idNumber(button.dataset.editionId);
 if(!id)return;
 const previousOwned=button.dataset.owned==="true";
 const previousRead=button.dataset.read==="true";
 const action=button.dataset.action;
 button.disabled=true;
 try{
  await request("/collection/volumes/"+id,{
    method:"PUT",data:{
      is_owned:action==="volume-owned"?!previousOwned:previousOwned,
      is_read:action==="volume-read"?!previousRead:previousRead,
    }
  });
  await refreshFrenchCollection();
  toast(t(state.lang,"collectionVolumeSaved"));
 }catch(error){button.disabled=false;toast(error.message||t(state.lang,"error"));}
}
function currentBulkResolver(isbn){
 return routeInfo().view==="library" && state.bulkResolver?.isbn===isbn &&
  Boolean(state.bulkPreview?.items?.some(row=>row.isbn13===isbn && row.match==="UNKNOWN"));
}
function drawBulkResolver(){
 const target=document.querySelector("#bulk-resolver-slot");
 if(!target)return;
 target.innerHTML=state.bulkResolver
  ?resolverMarkup(state.bulkResolver,key=>t(state.lang,key),escapeHtml):"";
}
async function startBulkResolution(button){
 const isbn=String(button.dataset.isbn||"");
 if(!/^[0-9]{13}$/.test(isbn)||
    !state.bulkPreview?.items?.some(row=>row.isbn13===isbn&&row.match==="UNKNOWN"))return;
 state.bulkResolver={isbn,record:null,query:"",matches:[],searched:false,selected:null,
   kind:"UNKNOWN",volume:null};
 drawBulkResolver();
 document.querySelector("#bulk-resolver-slot")?.scrollIntoView({behavior:"smooth",block:"nearest"});
 try{
  const record=await request("/collection/isbn/"+isbn);
  if(!currentBulkResolver(isbn))return;
  if(!isVerifiedIsbnRecord(record,isbn))throw Error(t(state.lang,"resolveNoRecord"));
  state.bulkResolver.record=record;
  state.bulkResolver.query="";
  state.bulkResolver.kind=EDITION_OPTIONS.includes(record.edition_kind_suggested)
   ?record.edition_kind_suggested:"UNKNOWN";
  drawBulkResolver();
 }catch(error){
  if(!currentBulkResolver(isbn))return;
  const slot=document.querySelector("#bulk-resolver-slot");
  if(slot)slot.innerHTML='<section class="bulk-resolver" id="bulk-resolver" role="alert">'+
   '<div class="bulk-resolver-head"><h3>'+L("resolveTitle")+'</h3>'+
   '<button type="button" class="btn btn-small" data-action="bulk-resolve-close">'+L("resolveCancel")+'</button></div>'+
   '<p>'+L("resolveNoRecord")+'</p><p class="muted">'+e(error.message||"")+'</p>'+
   '<button type="button" class="btn btn-soft" data-action="bulk-resolve" data-isbn="'+e(isbn)+'">'+
    L("resolveSearchAgain")+'</button></section>';
 }
}
async function searchBulkManga(form){
 const resolver=state.bulkResolver;
 if(!resolver||!currentBulkResolver(resolver.isbn)||!isVerifiedIsbnRecord(resolver.record,resolver.isbn))return;
 const search=String(new FormData(form).get("manga")||"").trim().slice(0,120);
 if(!search)return;
 resolver.query=search;resolver.selected=null;resolver.matches=[];resolver.searched=false;
 const slot=document.querySelector("#bulk-resolver-slot");
 if(slot)slot.insertAdjacentHTML("beforeend",'<p class="info">'+L("resolveSearching")+'</p>');
 try{
  const result=await request("/mangas?"+new URLSearchParams({q:search,limit:"12"}));
  if(!currentBulkResolver(resolver.isbn)||resolver!==state.bulkResolver||resolver.query!==search)return;
  resolver.matches=(result.items||[]).slice(0,12);
  resolver.searched=true;
  drawBulkResolver();
 }catch(error){
  if(resolver!==state.bulkResolver)return;
  if(slot)slot.innerHTML+='<p class="message">'+e(error.message||"")+'</p>';
 }
}
function selectBulkManga(button){
 const resolver=state.bulkResolver;if(!resolver||!currentBulkResolver(resolver.isbn))return;
 const id=idNumber(button.dataset.id);
 const manga=resolver.matches.find(row=>Number(row.id)===id);
 if(!manga)return;
 resolver.selected={id,title:manga.title};
 drawBulkResolver();
 document.querySelector(".bulk-resolver-confirm")?.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function syncBulkConfirmation(){
 const btn=document.querySelector('[data-action="bulk-resolve-confirm"]');
 if(!btn)return;
 const raw=String(document.querySelector("#bulk-resolve-volume")?.value??"").trim();
 const number=Number(raw);
 btn.disabled=!(document.querySelector("#bulk-resolve-ack")?.checked && raw &&
   Number.isInteger(number) && number>=1 && number<=9999);
}
async function confirmBulkAssociation(button){
 const draft=state.bulkResolver;if(!draft||!currentBulkResolver(draft.isbn)||
    !isVerifiedIsbnRecord(draft.record,draft.isbn)||!draft.selected)return;
 const checkbox=document.querySelector("#bulk-resolve-ack");
 const edition_kind=document.querySelector("#bulk-resolve-kind")?.value;
 const volume_number=Number(document.querySelector("#bulk-resolve-volume")?.value);
 const mangaId=idNumber(draft.selected.id);
 if(!checkbox?.checked || !String(document.querySelector("#bulk-resolve-volume")?.value??"").trim() ||
    !EDITION_OPTIONS.includes(edition_kind)||
    !mangaId||!Number.isInteger(volume_number)||volume_number<1||volume_number>9999){
  toast(t(state.lang,"resolveInputNeeded"));return;
 }
 button.disabled=true;
 try{
  await request("/collection/mangas/"+mangaId+"/editions",{
   method:"POST",data:{isbn13:draft.isbn,edition_kind,volume_number},
  });
  if(!currentBulkResolver(draft.isbn))return;
  // The original CSV is deliberately retained; the server recomputes its
  // confirmed ISBNs and a NEW approval token before any owned/read write.
  await previewBulkCsv();
  const target=document.querySelector("#bulk-import-result");
  if(target?.querySelector(".bulk-preview")){
   target.insertAdjacentHTML("afterbegin",'<div class="info">✓ '+L("resolveSuccess")+'</div>');
   target.querySelector(".bulk-preview")?.scrollIntoView({behavior:"smooth",block:"nearest"});
  }
  toast(t(state.lang,"resolveSuccess"));
 }catch(error){
  button.disabled=false;
  toast(error.message||t(state.lang,"error"));
 }
}

async function previewBulkCsv(){
 const input=document.querySelector("#bulk-csv-text");
 if(!input)return;
 const content=input.value.trim();
 if(!content){toast(t(state.lang,"bulkFormat"));return;}
 const target=document.querySelector("#bulk-import-result");if(!target)return;
 state.bulkCsv=content;state.bulkPreview=null;state.bulkResolver=null;
 target.innerHTML='<div class="info">'+L("loading")+'</div>';
 try{
  const result=await request("/collection/import/preview",{method:"POST",data:{csv_content:content}});
  if(routeInfo().view!=="library")return;
  state.bulkPreview=result;
  target.innerHTML=csvPreviewMarkup(result,key=>t(state.lang,key),escapeHtml);
 }catch(error){state.bulkPreview=null;target.innerHTML=errorBox(error);}
}
async function applyBulkCsv(button){
 const preview=state.bulkPreview;
 if(!preview||!state.bulkCsv)return;
 button.disabled=true;
 try{
  const result=await request("/collection/import/apply",{method:"POST",data:{
    csv_content:state.bulkCsv,confirmation_token:preview.confirmation_token,
  }});
  state.bulkPreview=null;
  const target=document.querySelector("#bulk-import-result");
  if(target)target.innerHTML='<div class="info">✓ '+L("bulkSaved")+' · '+
    e(result.processed)+' '+L("bulkToUpdate")+'. '+e(result.unknown)+' '+L("bulkUnknown")+
    '<p>'+L("bulkImportHint")+'</p></div>';
  state.recResult=null;
  toast(t(state.lang,"bulkSaved"));
 }catch(error){
  button.disabled=false;
  if(error?.message?.includes("409")){
    state.bulkPreview=null;
  }
  toast(error.message||t(state.lang,"bulkChanged"));
 }
}
async function reconcileBulkCounts(button){
 const target=document.querySelector("#bulk-compare-result");if(!target)return;
 button.disabled=true;target.innerHTML='<div class="info">'+L("loading")+'</div>';
 try{
  const result=await request("/collection/reconciliation");
  if(routeInfo().view!=="library")return;
  target.innerHTML=reconciliationMarkup(result,key=>t(state.lang,key),escapeHtml);
 }catch(error){target.innerHTML=errorBox(error);}
 finally{button.disabled=false;}
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
 if(action==="open-scanner")return isbnScanner.open(routeInfo().view==="detail"?state.currentDetail:null);
 if(action.startsWith("scan-"))return isbnScanner.click(action,button);
 if(["appearance-preset","appearance-accent","appearance-density","appearance-reset"].includes(action)){
  const part={"appearance-preset":"preset","appearance-accent":"accent","appearance-density":"density"}[action];
  const wanted=action==="appearance-reset" ? DEFAULT_APPEARANCE : {...state.appearance,[part]:button.dataset.value};
  state.appearance=saveAppearance(window.localStorage,wanted);
  applyAppearance(document.documentElement,state.appearance);
  if(routeInfo().view==="appearance")renderAppearance(renderToken);
  if(action==="appearance-reset")toast(t(state.lang,"appearanceResetSuccess"));
  return;
 }
 if(action==="feedback")return sendRecommendationFeedback(button);
 if(action==="bulk-preview")return previewBulkCsv();
 if(action==="bulk-resolve")return startBulkResolution(button);
 if(action==="bulk-resolve-close"){state.bulkResolver=null;drawBulkResolver();return;}
 if(action==="bulk-resolve-select")return selectBulkManga(button);
 if(action==="bulk-resolve-confirm")return confirmBulkAssociation(button);
 if(action==="bulk-apply")return applyBulkCsv(button);
 if(action==="bulk-compare")return reconcileBulkCounts(button);
 if(action==="edition-confirm")return confirmFrenchEdition(button);
 if(action==="biblio-verify-isbn"||action==="enrich-verify-isbn")
  return verifyBibliographyCandidate(button);
 if(action==="enrich-discover")return discoverFrenchEnrichment(button);
 if(action==="enrich-more")return discoverFrenchEnrichment(button,true);
 if(action==="volume-owned"||action==="volume-read")return updateFrenchVolume(button);
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
 if(action==="advisor-reset"){
  if(state.advisorBusy)return;
  state.advisorHistory=[];state.advisorContext={};state.advisorSeen=[];state.advisorResponse=null;
  await render();return;
 }
 if(action==="advisor-prompt"){
  const prompt=ADVISOR_PROMPTS[state.lang]?.[Number(button.dataset.index)];
  if(prompt)await sendAdvisorMessage(prompt);
  return;
 }
 if(action==="advisor-balance"){
  if(state.advisorBusy)return;
  const prompt=ADVISOR_BALANCE_PROMPTS[state.lang]?.[button.dataset.value];
  if(prompt)await sendAdvisorMessage(prompt);
  return;
 }
 if(action==="mood-select"){
  if(MOOD_OPTIONS.some(([name])=>name===button.dataset.mood)){
   state.mood=button.dataset.mood;state.recResult=null;await render();
  }
  return;
 }
 if(action==="generate-mood")return generateMoodDiscoveries();
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
 if(event.target.id==="advisor-form"){
  event.preventDefault();sendAdvisorMessage(new FormData(event.target).get("message"));return;
 }
 if(event.target.id==="scan-isbn-form"||event.target.id==="scan-series-form"){
  event.preventDefault();isbnScanner.submit(event.target);return;
 }
 if(event.target.id==="library-editor"){event.preventDefault();saveLibrary(event.target);}
 if(event.target.id==="edition-isbn-form"){event.preventDefault();searchFrenchIsbn(event.target);}
 if(event.target.id==="fr-bibliography-form"){event.preventDefault();searchFrenchBibliography(event.target);}
 if(event.target.id==="bulk-resolve-search-form"){event.preventDefault();searchBulkManga(event.target);}
});
root.addEventListener("change",async event=>{
 const input=event.target;
 if(input.id.startsWith("scan-")){isbnScanner.capture();return;}
 if(input.id==="app-language"){
  state.lang=input.value==="en"?"en":"fr";localStorage.setItem("ma-language",state.lang);await render();return;
 }
 if(input.id==="catalog-genre"){state.catalogGenre=input.value;state.catalogPage=1;await updateCatalog(renderToken);}
 if(input.id==="catalog-finished"){state.catalogFinished=input.checked;state.catalogPage=1;await updateCatalog(renderToken);}
 if(input.id==="lib-status"){state.libraryStatus=input.value;state.libraryPage=1;await updateLibrary(renderToken);}
 if(input.id==="bulk-resolve-ack")syncBulkConfirmation();
 if(input.id==="bulk-csv-file"&&input.files?.[0]){
  const file=input.files[0];
  if(file.size>80000){toast(t(state.lang,"bulkFormat"));input.value="";return;}
  state.bulkCsv=await file.text();
  state.bulkPreview=null;state.bulkResolver=null;
  const area=document.querySelector("#bulk-csv-text");if(area)area.value=state.bulkCsv;
  const out=document.querySelector("#bulk-import-result");if(out)out.innerHTML='<div class="info">'+L("bulkFileReady")+'</div>';
 }
 if(input.id==="mood-length" && ["ANY","SHORT","LONG"].includes(input.value)){
   state.moodLength=input.value;state.recResult=null;
 }
 if(input.id==="mood-finished"){state.moodFinished=input.checked;state.recResult=null;}
 if(input.id==="mood-personal"){state.moodUseLibrary=input.checked;state.recResult=null;}
 if(input.id==="mood-min-score"){state.moodMinScore=input.value;state.recResult=null;}
 if(input.id==="rec-goal"){state.recGoal=input.value;state.recResult=null;}
 if(input.id==="rec-balance"){state.recBalance=input.value;state.recResult=null;}
 if(input.id==="rec-min-score"){state.recMinScore=input.value;state.recResult=null;}
 if(input.id==="rec-finished"){state.recFinished=input.checked;state.recResult=null;}
 if(input.id==="rec-exclude"){state.recExclude=input.checked;state.recResult=null;}
});
root.addEventListener("input",event=>{
 const id=event.target.id;
 if(id.startsWith("scan-")){isbnScanner.capture();return;}
 if(id==="bulk-resolve-volume")syncBulkConfirmation();
 if(id==="bulk-csv-text" && state.bulkPreview && event.target.value.trim()!==state.bulkCsv){
  state.bulkPreview=null;state.bulkResolver=null;
  const output=document.querySelector("#bulk-import-result");
  if(output)output.innerHTML='<div class="info">'+L("bulkPreviewAction")+'</div>';
 }
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
 if(event.key==="Escape"&&isbnScanner.isOpen()){event.preventDefault();isbnScanner.close();return;}
 if(event.key==="Enter"&&event.target.id==="manual-search"){event.preventDefault();manualSearch();}
});
window.addEventListener("popstate",()=>render());
render();
