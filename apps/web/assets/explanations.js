/**
 * Mangadvisor: factual, bilingual recommendations explanation.
 * Inputs come from FastAPI; everything is escaped before HTML output.
 */
export function renderRecommendationExplanation(item, { text, translateTag, escape }) {
  const e = value => escape(String(value ?? ""));
  const L = key => e(text(key));
  const tagged = values => (Array.isArray(values) ? values : [])
    .filter(value => typeof value === "string" && value)
    .map(value => '<span class="explain-tag">' + e(translateTag(value)) + '</span>')
    .join("");

  const evidence = item?.explanation || {};
  const matches = Array.isArray(evidence.source_matches) ? evidence.source_matches : [];
  const titles = Array.isArray(evidence.reference_titles) ? evidence.reference_titles : [];
  const shared = evidence.shared || {};
  const cautions = Array.isArray(evidence.cautions) ? evidence.cautions : [];
  const community = evidence.community || {};
  const values = evidence.score || {};
  const format = value => {
    const n = Number(value);
    return value !== null && value !== undefined && Number.isFinite(n)
      ? n.toFixed(1)
      : "—";
  };
  const matched = matches.slice(0, 5).map(source => {
    const tags = [
      ...(source.genres || []), ...(source.themes || []), ...(source.demographics || [])
    ];
    return '<div class="explain-source"><strong>' + e(source.title) + '</strong>' +
      '<div class="explain-tags">' + tagged(tags) + '</div></div>';
  }).join("");

  const sharedMarkup = [
    ["genreMatch", shared.genres],
    ["themeMatch", shared.themes],
    ["audienceMatch", shared.demographics],
  ].filter(([, values]) => Array.isArray(values) && values.length)
   .map(([key, values]) => '<div class="explain-attribute"><span>' + L(key) + '</span>' +
     '<div class="explain-tags">' + tagged(values) + '</div></div>').join("");

  const communityMarkup = Number(community.votes || 0) > 0
    ? '<p>' + e(community.votes) + ' ' + L("explainVotes") +
       (Number(community.source_count || 0) > 0
       ? ' · ' + e(community.source_count) + ' ' + L("explainCommunityCount")
       : "") + '</p>' +
       (Array.isArray(community.recommended_from) && community.recommended_from.length
       ? '<div class="explain-tags">' + community.recommended_from
         .slice(0, 5).map(title => '<span class="explain-tag">' + e(title) + '</span>').join("") +
         '</div>'
       : "")
    : '<p class="muted">' + L("explainNoCommunity") + '</p>';

  const hasGoal = values.base !== null && values.base !== undefined
    && values.goal_bonus !== null && values.goal_bonus !== undefined;
  const scoreDetails = hasGoal
    ? '<div class="explain-score-steps">' +
      '<span>' + L("explainBase") + '<strong>' + format(values.base) + '</strong></span>' +
      '<span>＋</span><span>' + L("explainGoal") +
      '<strong>' + (Number(values.goal_bonus) >= 0 ? "+" : "") +
        format(values.goal_bonus) + '</strong></span>' +
      '<span>＝</span><span class="total">' + L("explainFinal") +
      '<strong>' + format(values.final) + '</strong></span></div>'
    : '<div class="explain-score-steps"><span class="total">' + L("explainFinal") +
      '<strong>' + format(values.final ?? item.recommendation_score) + '</strong></span></div>';

  const signals = [
    ["explainCommunityScore", values.community_signal],
    ["explainEditorialScore", values.editorial_signal],
    ["explainQualityScore", values.quality_signal],
    ["explainIntentScore", values.dominant_intent_signal],
  ].filter(([, value]) => value !== null && value !== undefined)
   .map(([key, value]) => '<span class="explain-signal">' + L(key) +
     ' <strong>' + format(value) + '</strong></span>').join("");

  return '<div class="explain-layout">' +
    (titles.length
      ? '<section><h4>' + L("explainSources") + '</h4>' +
        '<div class="explain-tags">' + titles.slice(0, 8).map(title =>
        '<span class="explain-tag source">' + e(title) + '</span>').join("") + '</div>' +
        '<p class="explain-caption">' + L("explainSourcesNote") + '</p></section>'
      : "") +
    '<section><h4>' + L("explainExactMatches") + '</h4>' +
      (matched || '<p class="muted">' + L("explainNoDirect") + '</p>') +
      '<p class="explain-caption">' + L("explainMeasured") + '</p></section>' +
    (sharedMarkup ? '<section><h4>' + L("explainShared") + '</h4>' +
       sharedMarkup + '</section>' : "") +
    '<section><h4>' + L("explainCommunity") + '</h4>' + communityMarkup + '</section>' +
    '<section><h4>' + L("explainCautions") + '</h4>' +
      (cautions.length ? '<div class="explain-tags caution">' + tagged(cautions) + '</div>' :
       '<p class="muted">' + L("explainNoCautions") + '</p>') + '</section>' +
    '<section><h4>' + L("explainScore") + '</h4>' + scoreDetails +
      (signals ? '<h5>' + L("explainSignals") + '</h5><div class="explain-signals">' +
        signals + '</div>' : "") +
      '<p class="explain-caption">' + L("explainNotTotal") + '</p></section>' +
    (item?.reason ? '<details class="explain-raw"><summary>' +
      L("explainEngineOriginal") + '</summary><p>' + e(item.reason) +
      '</p></details>' : "") +
    '</div>';
}
