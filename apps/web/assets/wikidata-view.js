/** Exact MAL-ID-linked Wikidata facts, never a French publisher/edition claim. */
export function wikidataFactsMarkup(data, {escape, lang="fr"}) {
  if (!data || data.status === "NOT_SEARCHED") return "";
  const e = value => escape(String(value ?? ""));
  const fr = lang === "fr";
  const heading = fr ? "Informations complémentaires · Wikidata" : "More information · Wikidata";
  const intro = fr
    ? "Libellés communautaires liés à l'identifiant manga MyAnimeList (P4087). Ce ne sont ni un synopsis complet ni une preuve d'édition française."
    : "Community labels linked by MyAnimeList manga ID (P4087). Not a full synopsis or proof of a French publication.";
  if (data.status !== "MATCHED") {
    const status = {
      AMBIGUOUS: fr ? "Plusieurs correspondances Wikidata : aucune information retenue." : "Multiple Wikidata matches; no facts accepted.",
      NOT_FOUND: fr ? "Aucune correspondance Wikidata par identifiant." : "No Wikidata match for this identifier.",
      ERROR: fr ? "Service indisponible : recherche à relancer depuis le menu." : "Service unavailable; retry from the menu.",
    }[data.status];
    if (!status) return "";
    return '<section class="fr-notices wikidata-evidence"><div class="fr-notices-heading"><strong>' +
      e(heading) + '</strong></div><p class="fr-notices-caveat">' + e(status) + '</p></section>';
  }
  const url = /^https:\/\/www\.wikidata\.org\/wiki\/Q[1-9][0-9]{0,11}$/.test(String(data.source_url || ""))
    ? data.source_url : null;
  if (!url) return "";
  const label = typeof data.label_fr === "string" ? data.label_fr.trim() : "";
  const description = typeof data.description_fr === "string" ? data.description_fr.trim() : "";
  const genres = Array.isArray(data.genres_fr)
    ? data.genres_fr.filter(x => typeof x === "string").slice(0, 12) : [];
  const line=(title,value) => value
    ? '<div class="fr-notice-line"><strong>'+e(title)+'</strong><span>'+e(value)+'</span></div>'
    : "";
  return '<section class="fr-notices wikidata-evidence">' +
    '<div class="fr-notices-heading"><strong>✦ '+e(heading)+'</strong>' +
    '<a href="'+e(url)+'" target="_blank" rel="noopener noreferrer">Wikidata ↗</a></div>' +
    '<p class="fr-notices-caveat">'+e(intro)+'</p>' +
    line(fr?"Libellé français":"French label",label) +
    line(fr?"Description courte":"Short description",description) +
    (genres.length ? '<div class="fr-notice-line"><strong>' +
      e(fr?"Genres documentés":"Recorded genres")+'</strong><span>'+
      genres.map(e).join(' · ')+'</span></div>' : "") +
    '</section>';
}
