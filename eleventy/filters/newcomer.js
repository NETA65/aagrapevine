// Area filters: newcomer — the "New to AA? / ¿Eres nuevo en AA?" card (src/_includes/macros/ui.njk newcomerCard /
// newcomerLine: its home is /meetings/#new-to-aa, a shorter copy is on the 404 page, and Home has one line to it).
//   ncOffices(site, lang)  the local AA offices the card lists
// The card points ONLY to AA (no outside enterprise, attraction rather than promotion): aa.org's own pages and AA's
// Meeting Guide app page (config/site.yml links: aa_find, aa_is_aa_for_you, aa_meeting_guide and their _es twins —
// the macro picks them with langLink), the Area's site (site.area_website) and the AA offices below. No phone numbers.

/** "https://www.aadallas.org/x" → "aadallas.org" ("" when it is not an address). */
const hostOf = (u) => {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
};

/**
 * The local AA offices of the card: the offices of config/site.yml `meetings.feeds` that are in our Area
 * (`in_area: true`) and whose own site is known (`site`, an https address — never the feed address, which can hold
 * an access key), each once, in the settings' order; on a Spanish page the Spanish-speaking offices (`lang: es`:
 * Alcohólicos Anónimos Dallas) come first.
 * → [{ name, url, host, lang }] — lang: the language of the office's site ("en" | "es"; the card marks an office whose
 *   site is not in the page's language).
 */
export function newcomerOffices(site, lang = "en") {
  const L = lang === "es" ? "es" : "en";
  const feeds = Array.isArray(site?.meetings?.feeds) ? site.meetings.feeds : [];
  const list = [];
  const seen = new Set();
  for (const f of feeds) {
    if (!f || typeof f !== "object" || f.in_area !== true) continue;
    const url = String(f.site || "").trim();
    const host = /^https:\/\//i.test(url) ? hostOf(url) : "";
    if (!host || seen.has(host)) continue;
    seen.add(host);
    list.push({ name: String(f.name || "").trim() || host, url, host, lang: f.lang === "es" ? "es" : "en" });
  }
  return L === "es" ? [...list.filter((o) => o.lang === "es"), ...list.filter((o) => o.lang !== "es")] : list;
}

export default function (eleventyConfig) {
  // {% for of in site | ncOffices(L) %} — the card's "AA offices in our Area"
  eleventyConfig.addFilter("ncOffices", (site, lang) => newcomerOffices(site, lang));
}
