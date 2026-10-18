/** Conversational advisor UI: safe, bounded and catalogue-grounded. */
import {advisorFrenchEditionsMarkup} from "./advisor-editions.js";
export const ADVISOR_PROMPTS={
 fr:[
  "Je veux une enquête psychologique sans horreur ni gore, pas trop longue, idéalement en français.",
  "J'ai envie d'une série douce et réconfortante.",
  "Une aventure fantastique assez longue.",
  "Je cherche un manga de mystère terminé avec une édition française obligatoire."
 ],
 en:[
  "I want a mystery, preferably in a Deluxe French edition, not too long.",
  "Something cozy and comforting.",
  "A long fantasy adventure.",
  "A finished mystery with a required French edition."
 ]
};

export function advisorChatMarkup({history=[],busy=false,lang="fr",aiMode="guided"},L,e){
 const modeKey=aiMode==="local_ai"?"advisorAIActive":
   aiMode==="guided_fallback"?"advisorAIFallback":"advisorAIGuided";
 const aiBanner='<div class="advisor-ai-state" aria-live="polite"><span class="advisor-ai-dot '+
  (aiMode==="local_ai"?"active":"")+'" aria-hidden="true">✧</span>'+L(modeKey)+'</div>';
 const intro=history.length?"":'<div class="advisor-welcome">'+
  '<div class="advisor-orb" aria-hidden="true">✧</div><h2>'+L("advisorGreeting")+'</h2>'+
  '<p>'+L("advisorIntro")+'</p></div>';
 const samples=history.length?"":'<div class="advisor-suggestions">'+(ADVISOR_PROMPTS[lang]||ADVISOR_PROMPTS.fr).map((s,i)=>
  '<button class="advisor-suggestion" data-action="advisor-prompt" data-index="'+i+'" type="button">'+e(s)+' <span>↗</span></button>').join("")+'</div>';
 const messages=history.map(m=>
  '<div class="advisor-message '+(m.role==="user"?"is-user":"is-assistant")+'">'+
  '<div class="advisor-message-persona">'+(m.role==="user"?L("advisorYou"):"Mangadvisor")+'</div>'+
  '<p>'+e(m.text)+'</p></div>').join("");
 return '<section class="advisor-studio" aria-label="'+L("advisorTitle")+'">'+
  '<div class="advisor-studio-head"><div><div class="eyebrow">MANGADVISOR · ADVISOR</div>'+
  '<h2>'+L("advisorTitle")+'</h2><p>'+L("advisorSubhead")+'</p></div>'+
  '<button type="button" class="btn btn-small btn-soft" data-action="advisor-reset"'+(busy?' disabled':'')+'>'+
  '↺ '+L("advisorReset")+'</button></div>'+
  aiBanner+
  '<div class="advisor-transcript" id="advisor-transcript" role="log" aria-live="polite" aria-relevant="additions text">'+
  intro+samples+messages+(busy?'<div class="advisor-loading">'+L("loading")+'…</div>':"")+'</div>'+
  '<form id="advisor-form" class="advisor-composer">'+
   '<label for="advisor-message">'+L("advisorYourRequest")+'</label>'+
   '<div class="advisor-input-row"><textarea id="advisor-message" name="message" rows="2" maxlength="500" '+
   'placeholder="'+L("advisorPlaceholder")+'"'+(busy?' disabled':'')+' required></textarea>'+
   '<button class="btn btn-primary" type="submit"'+(busy?' disabled':'')+'>'+L("advisorSend")+' ↗</button></div>'+
   '<p class="advisor-note">'+L("advisorLimits")+'</p></form></section>';
}

export function advisorResultsMarkup(response,{L,e,tr,poster,rating,published}){
 if(!response||!Array.isArray(response.recommendations)||!response.recommendations.length)return "";
 const chips=item=>{
  const rows=Array.isArray(item)?item:[];
  return rows.slice(0,5).map(x=>'<span class="pill">'+tr(x)+'</span>').join("");
 };
 return '<section class="advisor-recommendations"><div class="advisor-results-heading">'+
  '<div><div class="eyebrow">'+L(response.personalized?"advisorWithTaste":"advisorCatalog")+'</div>'+
  '<h2>'+L("advisorPicks")+'</h2></div>'+
  '<span class="mood-count">'+e(response.count)+' '+L("moodResultsCount")+'</span></div>'+
  '<div class="mood-grid">'+response.recommendations.map((m,i)=>{
   const mood=[...(m.mood_matches?.genres||[]),...(m.mood_matches?.themes||[])];
   const common=[...(m.affinity_matches?.genres||[]),...(m.affinity_matches?.themes||[])];
   const narrative=Array.isArray(m.narrative_matches)?m.narrative_matches:[];
   const unmatched=Array.isArray(m.narrative_unverified)?m.narrative_unverified:[];
   const safeConcept=id=>["INVESTIGATION","PSYCHOLOGICAL","SURVIVAL"].includes(id)?id:null;
   const storyBadges=narrative.filter(x=>safeConcept(x.concept)).map(x=>
    '<span class="advisor-story-chip"><strong>'+L("advisorStory"+x.concept)+'</strong>'+
    '<small>'+L(x.source==="catalog_tag"?"advisorStoryTag":"advisorStorySynopsis")+': '+
    e(x.matched||"")+'</small></span>').join("");
   const missingBadges=unmatched.filter(safeConcept).map(id=>L("advisorStory"+id)).join(", ");
   return '<article class="rec-card advisor-card">'+poster(m)+
    '<div class="rec-body"><span class="rec-rank">'+L("advisorPick")+' #'+(i+1)+'</span>'+
    '<h3>'+e(m.title||"Manga")+'</h3>'+
    '<p class="mood-card-meta">'+rating(m)+' · '+published(m.status)+
     (m.volumes?' · '+e(m.volumes)+' '+L("moodVolumes"):'')+'</p>'+
    '<div class="mood-evidence"><strong>'+L("advisorProof")+'</strong>'+
    '<div class="tag-row">'+chips(mood)+'</div></div>'+
    (common.length?'<div class="mood-evidence"><strong>'+L("moodAffinity")+'</strong>'+
     '<div class="tag-row">'+chips(common)+'</div></div>':"")+
    (storyBadges?'<div class="mood-evidence"><strong>'+L("advisorNarrativeEvidence")+'</strong>'+
     '<div class="advisor-story-grid">'+storyBadges+'</div></div>':"")+
    (missingBadges?'<p class="advisor-unverified">'+L("advisorNarrativeMissing")+': '+missingBadges+'</p>':"")+
    '<div class="advisor-french '+(m.french_recorded?"is-verified":"")+'">'+
       L(m.french_recorded?"advisorFrenchRegistered":"advisorFrenchUnknown")+'</div>'+
    advisorFrenchEditionsMarkup(m.french_editions,{L,e})+
    '<div class="actions"><button class="btn btn-small btn-soft" data-go="/manga/'+e(m.id)+'">'+L("details")+' →</button></div>'+
    '<div class="feedback-actions" role="group" aria-label="'+L("feedbackInfo")+'">'+
     '<button class="feedback-btn" data-action="feedback" data-feedback="INTERESTED" data-manga-id="'+e(m.id)+'">♡ '+L("feedbackInterested")+'</button>'+
     '<button class="feedback-btn" data-action="feedback" data-feedback="ALREADY_READ" data-manga-id="'+e(m.id)+'">✓ '+L("feedbackRead")+'</button>'+
     '<button class="feedback-btn dislike" data-action="feedback" data-feedback="NOT_FOR_ME" data-manga-id="'+e(m.id)+'">× '+L("feedbackDislike")+'</button>'+
    '</div></div></article>';
  }).join("")+'</div><p class="advisor-footnote">'+L("advisorFrenchCaution")+'</p></section>';
}
