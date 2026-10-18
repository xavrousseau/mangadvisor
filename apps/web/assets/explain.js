/**
 * Evidence displayed by Mangadvisor. No additional scores or associations are inferred.
 * These helpers consume fields actually present in the recommendation API responses.
 */
const VALID_FACTORS = [
  ["common_themes", "themeMatch"],
  ["common_genres", "genreMatch"],
  ["common_demographics", "audienceMatch"],
  ["community_recommended_from", "communitySignal"],
];
const COMPONENTS = [
  ["editorial_score", "explainEditorial"],
  ["dominant_intent_score", "explainIntent"],
  ["community_score", "explainCommunity"],
  ["quality_score", "explainQuality"],
  ["goal_bonus", "explainGoalBonus"],
];

/** Plain structured evidence without UI strings or speculative matching claims. */
export function explainRecommendation(item) {
  if (!item || typeof item !== "object") {
    return { factors: [], components: [], mismatches: [], originalReason: null };
  }
  const factors = VALID_FACTORS.flatMap(([field, label]) => {
    const values = Array.isArray(item[field])
      ? [...new Set(item[field].filter(value => typeof value === "string" && value.trim()).map(s => s.trim()))].slice(0, 6)
      : [];
    return values.length ? [{ field, label, values }] : [];
  });
  const components = COMPONENTS.flatMap(([field, label]) => {
    const raw = item[field];
    if (raw === null || raw === undefined || raw === "") return [];
    const numeric = Number(raw);
    return Number.isFinite(numeric) ? [{ field, label, value: numeric }] : [];
  });
  const mismatches = Array.isArray(item.sensitive_mismatches)
    ? [...new Set(item.sensitive_mismatches.filter(value => typeof value === "string" && value.trim()))].slice(0, 8)
    : [];
  return {
    factors, components, mismatches,
    originalReason: typeof item.reason === "string" && item.reason.trim() ? item.reason : null,
  };
}

/**
 * Sources belong to the overall recommendation search, not to a particular
 * candidate. Show them separately to avoid claiming a fake per-title connection.
 */
export function explainProfile(response) {
  if (!response || typeof response !== "object") return { sources: [], genres: [], themes: [] };
  const sourceItems = Array.isArray(response.positive_sources)
    ? response.positive_sources
    : Array.isArray(response.sources) ? response.sources : [];
  const sources = sourceItems
    .filter(x => x && typeof x.title === "string" && x.title.trim())
    .slice(0, 6)
    .map(x => ({
      title: x.title,
      favorite: x.is_favorite === true,
      score: x.user_score === null || x.user_score === undefined
        ? null
        : (Number.isFinite(Number(x.user_score)) ? Number(x.user_score) : null),
      status: typeof x.library_status === "string" ? x.library_status : null,
    }));
  const summary = response.profile_summary || {};
  const tags = key => Array.isArray(summary[key])
    ? summary[key].filter(x => x && typeof x.name === "string" && x.name.trim()).slice(0, 5).map(x => x.name)
    : [];
  return { sources, genres: tags("top_genres"), themes: tags("top_themes") };
}
