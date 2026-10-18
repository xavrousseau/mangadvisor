/**
 * Local-only, versioned UI appearance preferences.
 * No API or personal manga data is involved. Preferences are per browser.
 */
export const APPEARANCE_KEY = "ma-appearance-v1";
export const PRESETS = Object.freeze([
  { id: "night", nameKey: "themeNight", descKey: "themeNightDesc" },
  { id: "noir", nameKey: "themeNoir", descKey: "themeNoirDesc" },
  { id: "paper", nameKey: "themePaper", descKey: "themePaperDesc" },
]);
export const ACCENTS = Object.freeze([
  { id: "amber", nameKey: "accentAmber", hex: "#ffae67" },
  { id: "coral", nameKey: "accentCoral", hex: "#ff8591" },
  { id: "ocean", nameKey: "accentOcean", hex: "#74b8f6" },
  { id: "mint", nameKey: "accentMint", hex: "#5ad9b2" },
  { id: "violet", nameKey: "accentViolet", hex: "#bb9cf6" },
  { id: "gold", nameKey: "accentGold", hex: "#f6cc65" },
]);
export const DENSITIES = Object.freeze(["comfortable", "compact"]);
export const DEFAULT_APPEARANCE = Object.freeze({
  preset: "night", accent: "amber", density: "comfortable",
});
const has = (collection, id) => collection.some(item => item.id === id);

export function normalizeAppearance(input) {
  const obj = input && typeof input === "object" && !Array.isArray(input) ? input : {};
  return {
    preset: has(PRESETS, obj.preset) ? obj.preset : DEFAULT_APPEARANCE.preset,
    accent: has(ACCENTS, obj.accent) ? obj.accent : DEFAULT_APPEARANCE.accent,
    density: DENSITIES.includes(obj.density) ? obj.density : DEFAULT_APPEARANCE.density,
  };
}
export function loadAppearance(storage) {
  try {
    const raw = storage?.getItem(APPEARANCE_KEY);
    return raw ? normalizeAppearance(JSON.parse(raw)) : { ...DEFAULT_APPEARANCE };
  } catch {
    return { ...DEFAULT_APPEARANCE };
  }
}
export function saveAppearance(storage, appearance) {
  const safe = normalizeAppearance(appearance);
  try { storage?.setItem(APPEARANCE_KEY, JSON.stringify(safe)); }
  catch { /* Private-mode quota and storage restrictions: still change the current screen. */ }
  return safe;
}
export function applyAppearance(documentElement, appearance) {
  const safe = normalizeAppearance(appearance);
  documentElement.dataset.theme = safe.preset;
  documentElement.dataset.accent = safe.accent;
  documentElement.dataset.density = safe.density;
  documentElement.style.colorScheme = safe.preset === "paper" ? "light" : "dark";
  return safe;
}
