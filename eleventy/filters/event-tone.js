// Shared: the colour of an event, the same wherever events are listed (/events/, the home page's
// "Upcoming events", the monthly toolkit's dates, …). Auto-loaded by eleventy.config.js.
//
//   {{ ev | eventTone }}            → "committee" | "booth" | "assembly" | "lv" | "gv" | "other"
//   {{ events | eventToneSet }}     → the kinds present, in legend order (for a colour key)
//   {{ ev | isAssembly }}           → true for an Area ASSEMBLY itself (not an ACM, a town hall or a GSR/DCM
//                                     orientation, which share its colour): the "next assembly" pickers (/events/'
//                                     "Save the date", the booth's "Next assembly" slide, the web presentations'
//                                     `assemblies`) and the card's badge "Area assembly"
//
// Markup: put class="ev-tone-<kind>" on the card (or on the tile / badge / dot itself); the colours
// are the ev-* rules in src/assets/css/areas/committee.css (tokens only, light / dark / high contrast).
// Colour is never the only signal: the card's badge (or its title) says the kind in words.
//
// ONE colour per event, whatever the page's language (round 33c): the rules read the data record the shown event
// was made from — a /events/ event's `item`, a monthly date row's `src` (monthly.js dateRow) — its original title
// first, then its English and Spanish ones, and the title the page shows only after them. So the English and the
// Spanish page see the same words in the same order: the delegate's "Conference Connect Town Hall" (Spanish title
// "Reunión Informativa de la Delegada — Conference Connect") is an Area event on /monthly/2026-11/ and
// /es/monthly/2026-11/ alike — the Spanish row used to read only its Spanish title and called it "other" — and a
// title that names La Viña and Grapevine in a different order in each language gets the colour its original names
// first (rule 6) on both pages.
//
// Rules, first match wins (titles are compared without case or accents, in every language the item has):
//   1. committee  the committee's own meeting: category / kind "committee", an id "ev:committee:…", or a
//                 title that says "committee meeting" / "reunión del comité" — never "Area Committee Meeting" /
//                 "Reunión del Comité de Área": that is the Area's own (rule 4)
//   2. lv / gv    La Viña's or Grapevine's OWN event that we share — who holds it (extra.host "lv" / "gv":
//                 config/site.yml recurring_events `host:`, e.g. La Viña's monthly workshop on Zoom): its
//                 magazine's colour whatever its title says
//   3. booth      a literature booth or table: "booth", "table" (not "round table"), "kiosk", "stall",
//                 "mesa" (not "mesa redonda / de trabajo / directiva"), "puesto"
//   4. assembly   the Area's own events (since round 30): an assembly — "assembly" / "asamblea" (a pre-assembly
//                 too) —, the Area Committee Meeting — "ACM", "Area Committee Meeting", "Reunión del Comité de
//                 Área" —, the Area's town hall ("town hall": the delegate's "Conference Connect Town Hall" is
//                 titled so in English, and every language's title is read) and (round 35) the Area's orientation
//                 for GSRs and DCMs: a title that says "orientation" / "orientación" AND names them — "GSR", "DCM",
//                 "RSG", "MCD" (each also with an s), "General Service Representative(s)", "District Committee
//                 Member(s)", "Representante(s) de Servicios Generales", "Miembro(s) del Comité de Distrito"
//                 ("GSR/DCM Orientation 2027 — East", "Orientation for GSRs and DCMs", "Orientación para RSG y
//                 MCD") — and names no GVR / RLV, Grapevine or La Viña ("GVR", "RLV", "Grapevine", "La Viña",
//                 "GV", "LV"): an orientation that does is the committee's own (/orientation/, "GVR and RLV
//                 Orientation Workshop"); a plain "orientation" or "New-rep orientation" names no GSR or DCM (a
//                 title that names the city of Grapevine reads as Grapevine's, as in rule 6: name the group or
//                 the region instead). The
//                 colour key and the card's badge call this kind "Area event" (committee.events.kind.assembly); an
//                 assembly itself keeps the badge "Area assembly" (isAssembly → committee.events.badge_assembly)
//   5. other      a monthly MEETING of ours (config/site.yml recurring_events without `host: lv / gv` — the
//                 Grapevine Meeting): "meeting" / "reunión" in the title. Ours, so never the colour of an event
//                 AA Grapevine or La Viña hold (rule 6 would give "Grapevine Meeting" Grapevine's): its badge
//                 says NETA 65
//   6. lv / gv    the title names La Viña ("La Viña", "La Vina", "LV") or Grapevine ("Grapevine", "GV");
//                 a title that names both gets the one it names first
//   7. an event from La Viña's or Grapevine's own calendar (category lv-calendar / gv-calendar)
//   8. other      anything else (neutral)
//
// It reads a raw data item (db.events.items), a /events/ event (cmEvents: .committee, .host, .item) and a
// monthly toolkit date row (kind: committee | recurring | event; .host; .src, the events.json record — not
// enumerable, read all the same).

/** The kinds, in the order a colour key lists them. */
export const EVENT_TONES = ["committee", "gv", "lv", "booth", "assembly", "other"];

const RE = {
  // (never the Area's: "Area Committee Meeting", "Reunión del Comité de Área" — the ACM is rule 4's)
  committee: /(?<!\barea )\bcommittee meetings?\b|\breunion(?:es)? del comite\b(?! (?:de|del) area\b)/,
  booth: /\b(?:booths?|kiosks?|stalls?|puestos?)\b|\b(?<!round )tables?\b|\bmesas?\b(?! (?:redonda|de trabajo|directiva))/,
  // an Area assembly itself (isAssembly)
  assembly: /\b(?:assembly|assemblies|asambleas?)\b/,
  // the Area's other events, in the assembly's colour: its committee meeting (ACM) and its town hall
  area: /\bacms?\b|\barea committee meetings?\b|\breunion(?:es)? del comite (?:de|del) area\b|\btown ?halls?\b/,
  // … and its orientation for GSRs and DCMs (RSG / MCD): a title with both (areaOrientation) and none of `ours` —
  // an orientation that names GVRs / RLVs, Grapevine or La Viña is the committee's own (/orientation/)
  orientation: /\borienta(?:tion|cion)(?:s|es)?\b/,
  gsrDcm: /\b(?:gsrs?|dcms?|rsgs?|mcds?)\b|\bgeneral service representatives?\b|\bdistrict committee members?\b|\brepresentantes? de servicios generales\b|\bmiembros? del comite de distrito\b/,
  ours: /\b(?:gvrs?|rlvs?|grapevine|la vina|gv|lv)\b/,
  meeting: /\bmeetings?\b|\breunion(?:es)?\b/,
  lv: /\bla vina\b|\blv\b/,
  gv: /\bgrapevine\b|\bgv\b/,
};

/** "La Viña — Taller" → "la vina — taller" (lower case, accents removed). */
function norm(s) {
  return String(s == null ? "" : s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** The data record a shown event was made from — a /events/ event's `item` (committee.js normalizeEvents), a
 *  monthly date row's `src` (monthly.js dateRow) —, or null for a data item itself. The same record on the English
 *  and the Spanish page: what makes the colour one colour in both. */
function recordOf(x) {
  const r = x.item || x.src;
  return r && typeof r === "object" ? r : null;
}

/** Every title the item has, in an order that never depends on the page's language: the record's original title,
 *  its English and Spanish ones (recordOf), then the item's own — a data item's original and translations, or the
 *  title a /events/ event or a date row shows in the page's language, read LAST (before round 33c it came first, and
 *  a date row had no other: the Spanish row of the delegate's town hall never saw the words "Town Hall"). Each title
 *  once. */
function titlesOf(x) {
  const out = [];
  const add = (v) => { if (typeof v === "string" && v.trim()) { const n = norm(v); if (!out.includes(n)) out.push(n); } };
  const addAll = (o) => {
    if (!o) return;
    add(o.title);
    const t = o.i18n && o.i18n.title;
    if (t && typeof t === "object") { add(t.en); add(t.es); }
  };
  addAll(recordOf(x));
  addAll(x);
  return out;
}

/** The Area's orientation for GSRs and DCMs (rule 4, round 35) in one title (norm's form): "gsr/dcm orientation 2027
 *  — east", "orientacion para rsg y mcd" — the word orientation, a GSR / DCM (RSG / MCD) word, and no word of ours
 *  (GVR / RLV, Grapevine, La Viña: the committee's own orientation, /orientation/). */
function areaOrientation(t) {
  return RE.orientation.test(t) && RE.gsrDcm.test(t) && !RE.ours.test(t);
}

/** The first position of a pattern in a title (Infinity when it is not there). */
function firstAt(re, s) {
  const m = re.exec(s);
  return m ? m.index : Infinity;
}

/** Who holds it when it is La Viña or Grapevine ("lv" / "gv"): a /events/ event's or a date row's `host`, else
 *  the data's extra.host (also of the record a /events/ event or a date row was made from: recordOf); "" otherwise. */
function hostOf(x) {
  const rec = recordOf(x);
  for (const h of [x.host, x.extra && x.extra.host, rec && rec.extra && rec.extra.host]) {
    const v = String(h || "").toLowerCase();
    if (v === "lv" || v === "gv") return v;
  }
  return "";
}

export function eventTone(ev) {
  if (!ev || typeof ev !== "object") return "other";
  // (its category: its own, else its record's — recordOf, the same on every language's page)
  const rec = recordOf(ev);
  const category = String(ev.category || (rec && rec.category) || "");
  const id = String(ev.id || "");
  if (ev.committee === true || category === "committee" || ev.kind === "committee" || id.startsWith("ev:committee:")) return "committee";
  const titles = titlesOf(ev);
  if (titles.some((t) => RE.committee.test(t))) return "committee";
  const host = hostOf(ev);
  if (host) return host;
  if (titles.some((t) => RE.booth.test(t))) return "booth";
  if (titles.some((t) => RE.assembly.test(t) || RE.area.test(t) || areaOrientation(t))) return "assembly";
  // a monthly series of ours (a data item, a /events/ event or a monthly date row) that is a meeting
  const series = category === "recurring" || ev.kind === "recurring" || ev.recurring === true;
  if (series && titles.some((t) => RE.meeting.test(t))) return "other";
  for (const t of titles) {
    const lv = firstAt(RE.lv, t), gv = firstAt(RE.gv, t);
    if (lv !== Infinity || gv !== Infinity) return lv < gv ? "lv" : "gv";
  }
  if (category === "lv-calendar") return "lv";
  if (category === "gv-calendar") return "gv";
  return "other";
}

/** An Area ASSEMBLY itself: an event of the "assembly" kind whose title says assembly / asamblea (rule 4's own
 *  words) — not an ACM or the Area's town hall, which share its colour since round 30, nor (round 35) its GSR/DCM
 *  orientations. What the "next assembly" pickers mean (/events/' "Save the date" card, the booth's "Next assembly"
 *  slide, the web presentations' `assemblies` filter and {live:assembly_next}), and when a card's badge says "Area
 *  assembly" rather than "Area event" — the events eventTone called "assembly" before the Area's other events
 *  joined that kind. */
export function isAssembly(ev) {
  return eventTone(ev) === "assembly" && titlesOf(ev).some((t) => RE.assembly.test(t));
}

/** The kinds a list of events uses, in EVENT_TONES order (a colour key shows only these). */
export function eventToneSet(events) {
  const seen = new Set((Array.isArray(events) ? events : []).map(eventTone));
  return EVENT_TONES.filter((k) => seen.has(k));
}

export default function (eleventyConfig) {
  eleventyConfig.addFilter("eventTone", eventTone);
  eleventyConfig.addFilter("eventToneSet", eventToneSet);
  eleventyConfig.addFilter("isAssembly", isAssembly);
}
