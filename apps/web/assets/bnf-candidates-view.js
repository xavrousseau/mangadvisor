/** Cached BnF title-search results are NEVER verified manga/edition associations. */
const isOfficialRecord = url =>
  /^https:\/\/catalogue\.bnf\.fr\/ark:\/12148\/cb[0-9A-Za-z]+$/.test(String(url || ""));

export function bnfCachedCandidatesMarkup(cache, {escape, lang = "fr"}) {
  if (!cache || cache.status === "NOT_SEARCHED") return "";
  const fr = lang !== "en";
  const e = value => escape(String(value ?? ""));
  const items = Array.isArray(cache.items) ? cache.items.slice(0, 8) : [];
  const count = Number.isInteger(cache.candidate_count) ? cache.candidate_count : 0;
  const heading = fr ? "Notices BnF à examiner" : "BnF records to review";
  const notice = fr
    ? "Résultats de recherche, pas des ISBN associés à cette série. Vérifie l'édition et le tome avant tout ajout."
    : "Search suggestions, not ISBNs associated with this series. Verify each edition and volume before saving.";
  const status = cache.status === "ERROR"
    ? (fr ? "Recherche indisponible : réessayer via le menu." : "Search unavailable: retry from the menu.")
    : cache.status === "PARTIAL"
      ? (fr ? "Résultats incomplets : certaines recherches ont échoué." : "Partial results: some searches failed.")
      : cache.status === "EMPTY"
        ? (fr ? "Aucune notice candidate dans les premières pages consultées." : "No candidates in the first searched pages.")
        : cache.status === "SKIPPED"
          ? (fr ? "Aucun titre exploitable pour la recherche." : "No searchable title available.")
          : "";
  const cards = items.map(row => {
    const isbn = /^[0-9]{13}$/.test(String(row.isbn13 || "")) ? row.isbn13 : null;
    if (!isbn) return "";
    const verified = row.registration_status === "REGISTERED_HERE";
    const elsewhere = row.registration_status === "REGISTERED_OTHER";
    const action = verified || elsewhere ? "" :
      '<button type="button" class="btn btn-small btn-soft" data-action="bnf-candidate-verify" data-isbn="' +
        e(isbn) + '">' + (fr ? "Vérifier cet ISBN" : "Verify this ISBN") + '</button>';
    const info = verified ? (fr ? "Déjà enregistré ici" : "Already registered here") :
      elsewhere ? (fr ? "Enregistré sur une autre série" : "Registered for another series") :
      row.title_clue_rank === 0 ? (fr ? "Lien avec la série non établi" : "Work identity not established") :
      (fr ? "Indice de titre uniquement" : "Title overlap only");
    const source = isOfficialRecord(row.source_url)
      ? '<a href="' + e(row.source_url) + '" target="_blank" rel="noopener noreferrer">' +
          (fr ? "Notice BnF" : "BnF source record") + ' ↗</a>'
      : '';
    return '<article class="edition-item bnf-candidate-item"><div class="edition-main">' +
      '<h3>' + e(row.title_fr) + '</h3>' +
      '<p>' + [row.author_fr, row.publisher_fr, row.release_date_text].filter(Boolean).map(e).join(" · ") + '</p>' +
      '<p class="edition-source">ISBN ' + e(isbn) + ' · ' + e(info) + (source ? ' · ' + source : '') + '</p>' +
      '</div><div class="edition-actions">' + action + '</div></article>';
  }).join("");
  return '<section class="collection-panel bnf-candidate-panel" id="bnf-candidate-panel">' +
    '<div class="section-header"><h2 class="section-title">' + e(heading) + '</h2>' +
    '<span class="tiny muted">' + e(count) + ' ' + (fr ? "notices candidates" : "candidate records") + '</span></div>' +
    '<p class="collection-caveat">' + e(notice) + '</p>' +
    (status ? '<p class="message">' + e(status) + '</p>' : '') +
    (cards ? '<div class="edition-list">' + cards + '</div>' : '') +
    (count > items.length ? '<p class="tiny muted">' +
      e(fr ? "Seules les premières notices sont affichées." : "Only the first records are shown.") + '</p>' : '') +
    '</section>';
}
