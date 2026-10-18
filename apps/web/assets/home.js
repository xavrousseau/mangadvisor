/**
 * Mangadvisor 1.1 — sélection déterministe pour l'accueil personnel.
 * Aucun classement inventé : les recommandations conservent l'ordre de l'API.
 * Aucune donnée de l'utilisateur n'est conservée dans le navigateur.
 */
export function readingNow(items, limit = 4) {
  const selected = [];
  const seen = new Set();
  for (const item of Array.isArray(items) ? items : []) {
    const id = Number(item?.manga_id);
    if (item?.library_status !== "READING" || !Number.isInteger(id) || id < 1 || seen.has(id)) continue;
    seen.add(id);
    selected.push(item);
    if (selected.length >= limit) break;
  }
  return selected;
}

export function personalPicks(items, alreadyOwnedIds, limit = 4) {
  const selected = [];
  const known = new Set(Array.isArray(alreadyOwnedIds) ? alreadyOwnedIds.map(Number) : []);
  const seen = new Set();
  for (const item of Array.isArray(items) ? items : []) {
    const id = Number(item?.id);
    if (!Number.isInteger(id) || id < 1 || known.has(id) || seen.has(id)) continue;
    seen.add(id);
    selected.push(item);
    if (selected.length >= limit) break;
  }
  return selected;
}

export function recommendationSources(response, limit = 2) {
  return (Array.isArray(response?.positive_sources) ? response.positive_sources : [])
    .map(entry => entry?.title)
    .filter(title => typeof title === "string" && title.trim().length > 0)
    .slice(0, limit);
}
