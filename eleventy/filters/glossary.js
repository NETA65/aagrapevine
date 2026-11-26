// The service words a member meets on the site — GVR, RLV, NETA 65, Area 65, DCM, GSR, ACM, Assembly, Delegate, Panel —
// explained where they first appear on the key pages (Home, the GVR / RLV corner, GVR / RLV 101, Meetings) and all
// together on the GVR / RLV corner (/gvr/#glossary). Auto-loaded by eleventy.config.js.
//
//   {{ "read.gvr.subtitle" | t(lang) | gloss(lang) | safe }}
//       the string, escaped, with the FIRST appearance of each word of the glossary marked up as
//       <abbr class="gl-term" data-gl title="Grapevine Representative: the member who …">GVR</abbr>;
//       gloss(lang, ["gvr", "rlv"]) marks only those. Every match is found in the string as written, before any
//       markup goes in (a definition that names another word is never marked inside a title). Never use it on
//       words inside a link or a button: app.js turns each mark into a button (GV.glossary), and a button may not
//       sit inside another control (GV.glossary leaves such a mark a plain <abbr>).
//   {% set words = lang | glossary %}
//       every entry in order: { key, term, name, def } (the GVR / RLV corner's list).
//
// The words of each entry are src/_i18n/glossary.json's: glossary.term.<key> (as the page writes it: "GVR",
// "MCD" in Spanish), glossary.name.<key> (what it stands for) and glossary.def.<key> (one plain sentence). The patterns below find the word
// in a sentence, in each language (a plural too: "GVRs", "MCD"…). Without JavaScript the browser's own tooltip shows
// the title on hover; with it, a tap or Enter opens the definition under the word (main.css .gl-pop).
export const GLOSSARY = [
  { key: "gvr", en: "GVRs?", es: "GVRs?" },
  { key: "rlv", en: "RLVs?", es: "RLVs?" },
  { key: "neta", en: "NETA 65", es: "NETA 65" },
  { key: "area65", en: "Area 65", es: "Área 65" },
  { key: "dcm", en: "DCMs?", es: "MCDs?" },
  { key: "gsr", en: "GSRs?", es: "RSGs?" },
  { key: "acm", en: "ACMs?", es: "ACMs?" },
  { key: "assembly", en: "[Aa]ssembl(?:y|ies)", es: "[Aa]sambleas?" },
  { key: "delegate", en: "[Dd]elegates?", es: "[Dd]elegad[oa]s?" },
  { key: "panel", en: "Panel(?: \\d{2})?", es: "Panel(?: \\d{2})?" },
];

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/** The first match of each wanted entry in `text` (as written), never two overlapping: [{ start, end, key }]. */
export function glossMatches(text, lang = "en", keys = null) {
  const L = lang === "es" ? "es" : "en";
  const want = Array.isArray(keys) && keys.length ? new Set(keys) : null;
  const spans = [];
  for (const g of GLOSSARY) {
    if (want && !want.has(g.key)) continue;
    const re = new RegExp(`(?<![\\p{L}\\p{N}])(?:${g[L]})(?![\\p{L}\\p{N}])`, "u");
    const m = re.exec(String(text ?? ""));
    if (!m) continue;
    const s = { start: m.index, end: m.index + m[0].length, key: g.key };
    if (!spans.some((o) => s.start < o.end && o.start < s.end)) spans.push(s);
  }
  return spans.sort((a, b) => a.start - b.start);
}

export default function (eleventyConfig, helpers) {
  const t = (key, lang, vars) => helpers.translateKey(key, lang, vars);
  const entry = (g, lang) => ({
    key: g.key,
    term: t("glossary.term." + g.key, lang),
    name: t("glossary.name." + g.key, lang),
    def: t("glossary.def." + g.key, lang),
  });

  eleventyConfig.addFilter("gloss", (text, lang = "en", keys = null) => {
    const s = String(text ?? "");
    let out = "", at = 0;
    for (const m of glossMatches(s, lang, keys)) {
      const e = entry(GLOSSARY.find((g) => g.key === m.key), lang);
      out += esc(s.slice(at, m.start)) + `<abbr class="gl-term" data-gl title="${esc(e.name + ": " + e.def)}">${esc(s.slice(m.start, m.end))}</abbr>`;
      at = m.end;
    }
    return out + esc(s.slice(at));
  });

  eleventyConfig.addFilter("glossary", (lang = "en") => GLOSSARY.map((g) => entry(g, lang)));
}
