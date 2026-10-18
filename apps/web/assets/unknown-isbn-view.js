/** Explicit, human-confirmed resolution for unknown ISBNs.
 * A BnF record verifies the BOOK only; it cannot identify the matching manga.
 * Every external value is escaped, and only BnF catalogue links are emitted.
 */
export const EDITION_CHOICES = [
  "UNKNOWN", "CLASSIC", "DELUXE", "PERFECT", "COLLECTOR", "INTEGRAL", "OTHER",
];
const validBookLink = value => {
  try {
    const u = new URL(value);
    return u.protocol === "https:" && u.hostname === "catalogue.bnf.fr" ? u.href : null;
  } catch { return null; }
};
const safeId = value => /^[1-9]\d{0,9}$/.test(String(value ?? "")) ? Number(value) : null;

export function unknownIsbnWizardMarkup(data, tr, escape) {
  const e = value => escape(String(value ?? ""));
  const L = key => e(tr(key));
  if (!data?.isbn || !/^\d{13}$/.test(data.isbn)) return "";
  const record = data.record;
  const sourceUrl = record ? validBookLink(record.source_url) : null;
  const recordSection = record ? (
    '<section class="resolve-bnf" aria-label="' + L("resolveRecord") + '">' +
    '<div class="edition-verified">✓ ' + L("resolveRecord") + '</div>' +
    '<h4>' + e(record.title_fr) + '</h4>' +
    '<p>' + [record.author_fr, record.publisher_fr, record.release_date_text]
      .filter(Boolean).map(e).join(" · ") + '</p>' +
    '<p>' + L("collectionIsbn") + ': <strong>' + e(record.isbn13) + '</strong>' +
    (sourceUrl ? ' · <a href="' + e(sourceUrl) +
      '" rel="noopener noreferrer" target="_blank">' + L("collectionBnfSource") + ' ↗</a>' : '') +
    '</p><p class="resolve-notice">' + L("resolveBookNotSeries") + '</p></section>'
  ) : '';

  const mangaResults = (data.matches || []).slice(0, 15).map(manga => {
    const id = safeId(manga.id);
    if (!id) return "";
    const selected = id === data.selectedId;
    return '<button type="button" class="resolve-manga-choice" data-action="resolve-select-series" ' +
      'data-manga-id="' + id + '" aria-pressed="' + selected + '">' +
      '<span>' + e(manga.title) + '</span><small>№ ' + id +
      (manga.title_japanese ? ' · ' + e(manga.title_japanese) : '') + '</small>' +
      (selected ? '<span class="resolve-check" aria-hidden="true">✓</span>' : '') +
      '</button>';
  }).join("");

  const list = data.searched
    ? '<div class="resolve-results" role="group" aria-label="' + L("resolveChooseSeries") + '">' +
      (mangaResults || '<p class="muted tiny">' + L("resolveNoSeries") + '</p>') + '</div>'
    : '';
  const selected = (data.matches || []).find(x => Number(x.id) === data.selectedId);
  const editionOpts = EDITION_CHOICES.map(kind => '<option value="' + kind + '"' +
    (kind === (data.kind || record?.edition_kind_suggested || "UNKNOWN") ? ' selected' : '') +
    '>' + L("edition" + kind) + '</option>').join("");
  const confirmation = selected ?
    '<div class="resolve-confirm"><h4>' + L("resolveConfirmTitle") + '</h4>' +
    '<p>' + L("resolveChosenSeries") + ': <strong>' + e(selected.title) + '</strong></p>' +
    '<div class="form-grid">' +
    '<div class="field"><label for="resolve-edition-kind">' + L("collectionEditionType") +
    '</label><select class="select" id="resolve-edition-kind">' + editionOpts + '</select></div>' +
    '<div class="field"><label for="resolve-volume-number">' + L("collectionTome") +
    '</label><input class="input" id="resolve-volume-number" type="number" min="1" max="9999" value="' +
    e(data.volumeNumber ?? "") + '" placeholder="1" required></div></div>' +
    '<p class="resolve-warning">' + L("resolveConfirmWarning") + '</p>' +
    '<button type="button" class="btn btn-primary" data-action="resolve-confirm-edition">' +
    L("resolveConfirm") + '</button></div>' : '';

  return '<div class="resolve-wizard" id="bulk-resolver-panel">' +
    '<div class="resolve-header"><div><span class="eyebrow">' + L("resolveStep") +
    '</span><h3>' + L("resolveTitle") + '</h3>' +
    '<p>' + L("resolveIntro") + ' <strong>' + e(data.isbn) + '</strong></p></div>' +
    '<button type="button" class="btn btn-small btn-soft" data-action="resolve-cancel">' +
    L("resolveCancel") + ' ✕</button></div>' +
    (data.loading ? '<p class="info">' + L("loading") + '</p>' : '') +
    (data.error ? '<div class="message" role="alert">' + e(data.error) + '</div>' : '') +
    recordSection +
    (record ? '<div class="resolve-search">' +
      '<label for="resolve-manga-query">' + L("resolveFindSeries") + '</label>' +
      '<div class="actions"><input id="resolve-manga-query" class="input" autocomplete="off" ' +
      'type="search" maxlength="120" value="' + e(data.query || "") +
      '" placeholder="' + L("searchPlaceholder") + '">' +
      '<button type="button" class="btn btn-soft" data-action="resolve-search-series">' +
      L("resolveSearch") + '</button></div>' +
      '<p class="muted tiny">' + L("resolveSearchHelp") + '</p>' + list + confirmation +
      '</div>' : '') +
    '</div>';
}
