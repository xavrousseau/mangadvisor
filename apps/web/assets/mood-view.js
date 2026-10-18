/** Guided Mangadvisor discovery. All tag matches are returned by the server. */
export const MOOD_OPTIONS = Object.freeze([
 ["DARK","moodDark","◈"],["COMFORT","moodComfort","☁"],
 ["ACTION","moodAction","⚡"],["MYSTERY","moodMystery","⌕"],
 ["ROMANCE","moodRomance","♡"],["FANTASY","moodFantasy","✧"],
]);
export const MOOD_LENGTHS = Object.freeze([
 ["ANY","moodAnyLength"],["SHORT","moodShortLength"],["LONG","moodLongLength"],
]);

export function moodFormMarkup(draft,L,e){
 return '<div class="mood-studio">'+
  '<div class="mood-studio-title"><div class="eyebrow">MANGADVISOR · 2.0</div><h2>'+L("moodChoose")+'</h2>'+
  '<p>'+L("moodPickHelp")+'</p></div>'+
  '<div class="mood-picker" role="group" aria-label="'+L("moodChoose")+'">'+
  MOOD_OPTIONS.map(([value,key,icon])=>
   '<button type="button" class="mood-choice'+(draft.mood===value?' selected':'')+
   '" aria-pressed="'+(draft.mood===value)+'" data-action="mood-select" data-mood="'+value+'">'+
   '<span class="mood-choice-icon" aria-hidden="true">'+icon+'</span><strong>'+L(key)+'</strong></button>').join("")+
  '</div>'+
  '<div class="mood-controls">'+
    '<div class="field"><label for="mood-length">'+L("moodLength")+'</label><select id="mood-length" class="select">'+
    MOOD_LENGTHS.map(([value,key])=>
      '<option value="'+value+'"'+(draft.length===value?' selected':'')+'>'+L(key)+'</option>').join("")+'</select></div>'+
    '<div class="field"><label for="mood-min-score">'+L("minRating")+'</label>'+
      '<input id="mood-min-score" class="input" type="number" step="0.1" min="0" max="10" value="'+e(draft.minScore)+'"></div>'+
    '<label class="check"><input type="checkbox" id="mood-finished"'+(draft.onlyFinished?' checked':'')+'>'+L("finishedOnly")+'</label>'+
    '<label class="check"><input type="checkbox" id="mood-personal"'+(draft.useLibrary?' checked':'')+'>'+L("moodUseLibrary")+'</label>'+
  '</div><p class="mood-disclaimer">'+L("moodEvidenceHelp")+'</p>'+
  '<button class="btn btn-primary mood-submit" type="button" id="rec-submit" data-action="generate-mood">✧ '+L("moodFind")+' →</button>'+
  '</div>';
}

export function verifiedMoodTags(item){
 const mood=item.mood_matches||{}, affinity=item.affinity_matches||{};
 const filtered=field=>(Array.isArray(field)?field:[]).filter(tag=>typeof tag==="string");
 return {mood:[...filtered(mood.genres),...filtered(mood.themes)],
  affinity:[...filtered(affinity.genres),...filtered(affinity.themes)]};
}

export function moodResultsMarkup(items, {L,e,tr,poster,rating,published}){
 if(!items.length)return '<div class="info">'+L("moodNoResults")+'</div>';
 return '<div class="mood-grid">'+items.map((m,i)=>{
  const {mood,affinity}=verifiedMoodTags(m);
  const badges=tags=>tags.slice(0,4).map(tag=>'<span class="pill">'+tr(tag)+'</span>').join("");
  return '<article class="rec-card mood-card">'+poster(m)+
   '<div class="rec-body"><span class="rec-rank">'+L("moodPick")+' #'+(i+1)+'</span>'+
   '<h3>'+e(m.title||"Manga")+'</h3>'+
   '<p class="mood-card-meta">'+rating(m)+' · '+published(m.status)+
     (m.volumes?' · '+e(m.volumes)+' '+L("moodVolumes"):'')+'</p>'+
   '<div class="mood-evidence"><strong>'+L("moodMatched")+'</strong><div class="tag-row">'+badges(mood)+'</div></div>'+
   (affinity.length?'<div class="mood-evidence"><strong>'+L("moodAffinity")+'</strong><div class="tag-row">'+badges(affinity)+'</div></div>':
     '<p class="mood-card-hint">'+L("moodNotPersonalEvidence")+'</p>')+
   '<div class="actions"><button class="btn btn-small btn-soft" data-go="/manga/'+e(m.id)+'">'+L("details")+' →</button></div>'+
   '<div class="feedback-actions" role="group" aria-label="'+L("feedbackInfo")+'">'+
    '<button type="button" class="feedback-btn" data-action="feedback" data-feedback="INTERESTED" data-manga-id="'+e(m.id)+'">♡ '+L("feedbackInterested")+'</button>'+
    '<button type="button" class="feedback-btn" data-action="feedback" data-feedback="ALREADY_READ" data-manga-id="'+e(m.id)+'">✓ '+L("feedbackRead")+'</button>'+
    '<button type="button" class="feedback-btn dislike" data-action="feedback" data-feedback="NOT_FOR_ME" data-manga-id="'+e(m.id)+'">× '+L("feedbackDislike")+'</button>'+
   '</div></div></article>';
 }).join("")+'</div>';
}
