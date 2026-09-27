// Loads config/expenses.yml — the service expense tracker's defaults (/expenses/, src/pages/expenses.njk)
// — and exposes it as `expenses` in every template:
//   expenses.config   the defaults as the tracker reads them (the page embeds it as <script id="xp-config">;
//                     expenses-core.js mergeDefaults adds it to each visitor's own settings):
//                       categories [{id, type, template, icon, color, label: {en, es}, builtin, order,
//                                    default_funder?, default_claim?, giveaway_default?}]
//                       funders [{id, kind, name: {en, es}, builtin, order}] · methods [{id, name, builtin, order}]
//                       rates [{id, name, rate, note, builtin}] · default_rate · defaults {funder, method, round_trip}
//                       panels [{id, from, to}] · renewal_days · backup_reminder_days · tones · types · templates
//                       · icons (the icon picker: drawn at build time in #xp-icons)
//   expenses.icons    the Lucide names the page draws once at build time (category icons + the picker)
//   expenses.ui       {en: {...}, es: {...}}: every "expenses.*" string of src/_i18n/expenses.json with the
//                     "expenses." prefix taken off — the page hands its language's set to the app
//                     (<script id="xp-ui">); the build's own `t` filter reads the same file.
// Checks: unique ids, a known type / template / tone / funder kind, both labels, icons that exist,
// rates as decimals, dates as YYYY-MM-DD. A problem is logged, and with I18N_STRICT=1 (CI) it fails
// the build instead.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import * as yaml from "js-yaml";

const FILE = "config/expenses.yml";
const STRINGS = "src/_i18n/expenses.json";
const TYPES = ["expense", "mileage", "received", "giveaway", "stock"];
const TEMPLATES = ["general", "books", "subscription", "lodging", "meal", "printing", "travel", "mileage", "received", "giveaway", "stock"];
const FUNDER_KINDS = ["self", "area", "district", "group", "committee", "person", "other"];
const TONES = ["gv", "lv", "grape", "vine", "rose", "teal", "gold", "slate"];
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const RATE = /^(\d{1,2}(\.\d{1,3})?)?$/;

// A Lucide icon (lucide-static) or one of the site's own (src/_includes/icons) — as the {% icon %} shortcode.
let lucideDir = null;
function iconExists(name) {
  if (fs.existsSync(path.join("src/_includes/icons", `${name}.svg`))) return true;
  if (!lucideDir) {
    try { lucideDir = path.join(path.dirname(createRequire(import.meta.url).resolve("lucide-static/package.json")), "icons"); }
    catch (e) { return true; } // no npm packages (a unit test without node_modules): nothing to check against
  }
  return fs.existsSync(path.join(lucideDir, `${name}.svg`));
}

function uiStrings() {
  const out = { en: {}, es: {} };
  if (!fs.existsSync(STRINGS)) return out;
  const data = JSON.parse(fs.readFileSync(STRINGS, "utf8"));
  for (const [k, v] of Object.entries(data)) {
    if (!k.startsWith("expenses.") || !v || typeof v !== "object") continue;
    const short = k.slice("expenses.".length);
    out.en[short] = v.en ?? v.es ?? "";
    out.es[short] = v.es ?? v.en ?? "";
  }
  return out;
}

export default function () {
  const ui = uiStrings();
  if (!fs.existsSync(FILE)) return { config: null, icons: [], ui, tones: TONES };
  const cfg = yaml.load(fs.readFileSync(FILE, "utf8")) || {};
  const problems = [];

  // A {en, es} pair: both languages present, or filled from the other one (and reported).
  const pair = (v, where) => {
    if (!v || typeof v !== "object") { problems.push(`${where}: missing`); const s = v ? String(v) : ""; return { en: s, es: s }; }
    for (const [a, b] of [["en", "es"], ["es", "en"]]) {
      if (typeof v[a] !== "string" || !v[a].trim()) { problems.push(`${where}: missing "${a}"`); v[a] = v[b] || ""; }
    }
    return { en: v.en, es: v.es };
  };
  const list = (v, where) => {
    if (!Array.isArray(v) || !v.length) { problems.push(`${where}: an empty list`); return []; }
    const seen = new Set();
    return v.filter((x, i) => {
      if (!x || x.id === undefined || x.id === null || String(x.id).trim() === "") { problems.push(`${where} #${i + 1}: no id`); return false; }
      x.id = String(x.id);
      if (!/^[a-z0-9_]+$/.test(x.id)) problems.push(`${where} ${x.id}: ids are lower-case letters, digits and _`);
      if (seen.has(x.id)) { problems.push(`${where}: duplicate id "${x.id}"`); return false; }
      seen.add(x.id);
      return true;
    });
  };

  const tones = Array.isArray(cfg.tones) ? cfg.tones.map(String) : TONES;
  for (const t of tones) if (!TONES.includes(t)) problems.push(`tones: "${t}" is not drawn by areas/expenses.css`);
  const icons = [...new Set((Array.isArray(cfg.icons) ? cfg.icons : []).map(String))];
  for (const n of icons) if (!iconExists(n)) problems.push(`icons: no icon "${n}"`);

  const funders = list(cfg.funders, "funders").map((f, i) => {
    if (!FUNDER_KINDS.includes(f.kind)) problems.push(`funders ${f.id}: unknown kind "${f.kind}"`);
    return { id: f.id, kind: f.kind, name: pair(f.name, `funders ${f.id} name`), builtin: true, hidden: false, order: i };
  });
  if (!funders.some((f) => f.id === "me" && f.kind === "self")) problems.push(`funders: "me" (kind self) is required`);
  const funderIds = new Set(funders.map((f) => f.id));

  const categories = list(cfg.categories, "categories").map((c, i) => {
    const where = `categories ${c.id}`;
    if (!TYPES.includes(c.type)) problems.push(`${where}: unknown type "${c.type}"`);
    if (!TEMPLATES.includes(c.template)) problems.push(`${where}: unknown template "${c.template}"`);
    if (!tones.includes(c.color)) problems.push(`${where}: unknown color "${c.color}"`);
    if (!c.icon || !icons.includes(c.icon)) problems.push(`${where}: icon "${c.icon}" is not in the icons list`);
    if (c.default_funder !== undefined && !funderIds.has(c.default_funder)) problems.push(`${where}: unknown default_funder "${c.default_funder}"`);
    if (c.default_claim !== undefined && !["none", "to_request"].includes(c.default_claim)) problems.push(`${where}: default_claim is none or to_request`);
    const out = { id: c.id, type: c.type, template: c.template, icon: c.icon, color: c.color, label: pair(c.label, `${where} label`), builtin: true, hidden: false, order: i };
    if (c.default_funder !== undefined) out.default_funder = c.default_funder;
    if (c.default_claim !== undefined) out.default_claim = c.default_claim;
    if (c.giveaway_default) out.giveaway_default = true;
    return out;
  });
  for (const t of TYPES) if (!categories.some((c) => c.type === t)) problems.push(`categories: no category of type "${t}"`);

  const methods = list(cfg.methods, "methods").map((m, i) => ({ id: m.id, name: pair(m.name, `methods ${m.id} name`), builtin: true, hidden: false, order: i }));
  const methodIds = new Set(methods.map((m) => m.id));

  const rates = list(cfg.rates, "rates").map((r) => {
    const rate = r.rate === undefined || r.rate === null ? "" : String(r.rate);
    if (!RATE.test(rate)) problems.push(`rates ${r.id}: rate "${rate}" is not a decimal with up to 3 places`);
    const out = { id: r.id, name: pair(r.name, `rates ${r.id} name`), rate, builtin: true };
    if (r.note) out.note = pair(r.note, `rates ${r.id} note`);
    return out;
  });
  const rateIds = new Set(rates.map((r) => r.id));
  const default_rate = String(cfg.default_rate || (rates[0] && rates[0].id) || "");
  if (!rateIds.has(default_rate)) problems.push(`default_rate: unknown rate "${default_rate}"`);

  const d = cfg.defaults || {};
  const defaults = { funder: String(d.funder || "me"), method: String(d.method || "cash"), round_trip: !!d.round_trip };
  if (!funderIds.has(defaults.funder)) problems.push(`defaults.funder: unknown funder "${defaults.funder}"`);
  if (!methodIds.has(defaults.method)) problems.push(`defaults.method: unknown method "${defaults.method}"`);

  const panels = (Array.isArray(cfg.panels) ? cfg.panels : []).map((p, i) => {
    const out = { id: String(p && p.id), from: String(p && p.from), to: String(p && p.to) };
    if (!ISO.test(out.from) || !ISO.test(out.to) || out.from > out.to) problems.push(`panels #${i + 1}: from / to are YYYY-MM-DD, from ≤ to`);
    return out;
  });

  const days = (v, dflt, where) => {
    if (v === undefined) return dflt;
    const n = Number(v);
    if (!Number.isInteger(n) || n < 1 || n > 365) { problems.push(`${where}: a whole number of days (1–365)`); return dflt; }
    return n;
  };

  // Every "expenses.*" string needs both languages (the build's `t` filter falls back silently otherwise).
  if (!fs.existsSync(STRINGS)) problems.push(`${STRINGS}: missing`);

  if (problems.length) {
    const msg = `[expenses] ${FILE}: ${problems.join("; ")}`;
    if (process.env.I18N_STRICT) throw new Error(msg);
    console.warn(msg);
  }

  // category icons first, then the rest of the picker set (each once)
  const allIcons = [...new Set([...categories.map((c) => c.icon), ...icons])];
  return {
    config: {
      categories, funders, methods, rates, default_rate, defaults, panels,
      renewal_days: days(cfg.renewal_days, 60, "renewal_days"),
      backup_reminder_days: days(cfg.backup_reminder_days, 30, "backup_reminder_days"),
      tones, types: TYPES, templates: TEMPLATES, icons: allIcons,
    },
    icons: allIcons,
    tones,
    ui,
  };
}
