// The presentations (/orientation/, "Presentations": three workshops and the committee meeting) — their deck files
// and the facts that keep them current. Auto-loaded by eleventy.config.js. Owned by src/_data/presentations.js (the
// `presentations` global) and src/pages/presentations-json.11ty.js (/orientation/presentations/<id>.json, what the
// player opens); the player itself is src/assets/js/presentations*.js, the page src/pages/orientation.njk.
//
// The decks: config/presentations/<id>.yml, one per deck (the owner's how-to: config/presentations/README.md), or
// the folder in PRESENTATIONS_DIR (tests/fixtures/presentations: the sample decks for tests and previews).
//   loadDecks(dir, opts)        → { decks, problems } — every deck file read, checked and shaped for the global
//   checkDeck(d, stem)          → one deck's problems, as tests/test_presentations.py words them (THE rules: the
//                                 Python checker is what the people writing a deck run; this is its twin, so the
//                                 build stops on exactly the same things — keep the two in step)
//   publishedPhones()           → the phone numbers the site itself publishes (a deck may show them)
//   liveFacts(ctx)              → every {live:…} value: a string, or { value, steps?, until?, fallback? } (SPEC
//                                 UPDATE 3) — each step's `value` from its instant `from` (sorted), so a copy opened
//                                 weeks later (offline, saved) still says what is true then; from `until` the
//                                 `fallback` ("" without one), which is also what an empty value says (FALLBACKS:
//                                 a phrase that reads in the sentence, never a label left dangling). The month's
//                                 facts (month, year, the issues) switch together at midnight Central on the 1st;
//                                 the next meeting when that meeting ends; the meeting's day, its month and the
//                                 meeting after it at midnight Central after the meeting's day
//   liveData(kind, options, ctx) → the `data` block of a `live` slide: every row known within about a year (at most
//                                 MAX_ROWS) and the slide's `limit` — the player leaves out the rows already past,
//                                 then applies the limit
//   deckJson(deck, ctx)         → the whole /orientation/presentations/<id>.json object
// Filter: presDeckJson(deck, data) → that file's text (data = the template's data: db, site, carry, meeting).
//
// Every fact comes from the site's own data and functions — the same words and numbers the other pages show,
// never typed in and never worked out a second way here: committee.js (the events of /events/, the committee
// meeting's rule and time, the bulletin, the Drive's panel), read.js (the editorial calendar: deadlines and
// themes), monthly.js (this month's and the next issues, the toolkit's ideas, the build's clock), shop.js (prices,
// announced price changes, Grapevine's and La Viña's Books of the Month), src/_data/meeting.js (the next meeting
// dates), access.js (joining the committee meeting by phone: /accessibility/#phone), db.audio_project (the
// magazines' story lines: /contribute/#record), committee.js weeklyOpen (the weekly open meetings of /meetings/),
// read.js issueLabel (an issue's name), community.js (QR codes), event-tone.js (an event's kind). Missing data
// gives the key's fallback or empty rows: the player then points to the page.
// The content of the decks stays English (the owner's decision), so every label here is English.
// Dates and day boundaries are Central time (America/Chicago); instants are UTC ISO ("2027-01-01T06:00:00.000Z").
// The build's "now" is monthly.js nowDate(): MONTHLY_NOW=2026-12-15 moves it for a preview build, as for /monthly/.

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import * as yaml from "js-yaml";
import { monthlyRule, TZ } from "../../eleventy.config.js";
import { normalizeEvents, meetingDates, recurrenceText, chicagoDayEndMs, announcementList, driveInfo, weeklyOpenAll } from "./committee.js";
import { editorialFor, issueLabel } from "./read.js";
import { monthModel, monthLabel, nowDate, chicagoYmd, issueTheme, addMonths } from "./monthly.js";
import { shopPlanPrice, shopNextChange, shopPriceChangeIn, shopBotm, money, dayLabel } from "./shop.js";
import { qrSvg, issueLabelOf } from "./community.js";
import { eventTone } from "./event-tone.js";
import { axPhone } from "./access.js";

// The repository (the deck folder, the icons, data/site/shop.json): Eleventy and the tests run from its root.
const ROOT = process.cwd();

// Helpers handed over by eleventy.config.js (translateKey, pickLang, fmtDate …); the fallbacks keep the module
// usable from a plain `node` script too (the data file imports it before any page is rendered).
let H = {
  translateKey: (k) => k,
  pickLang: (item, field, lang) => {
    const i = item && item.i18n && item.i18n[field];
    return (i && i[lang]) || (item && item[field]) || "";
  },
  fmtDate: (v, lang, style) => {
    const d = v instanceof Date ? v : new Date(v);
    if (isNaN(d)) return "";
    const o = style === "long" ? { weekday: "long", month: "long", day: "numeric", year: "numeric" } : { month: "long", day: "numeric", year: "numeric" };
    return new Intl.DateTimeFormat("en-US", { ...o, timeZone: TZ }).format(d);
  },
};
const t = (key, vars) => H.translateKey(key, "en", vars);

/* ------------------------------------------------------------------ */
/*  The rules (tests/test_presentations.py — the same names and lists) */
/* ------------------------------------------------------------------ */
const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const KEY = /^[a-z][a-z0-9_]*$/;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const TONES = ["gv", "lv", "vine", "grape"];
const ACCENTS = ["gv", "lv", "vine", "grape", "navy"];
const LANGS = ["en", "es"];
export const LIVE_KEYS = [
  "site", "site_url", "email", "panel", "as_of", "month", "year",
  "meeting_next", "meeting_day", "meeting_after", "meeting_month", "meeting_rule", "meeting_time", "meeting_zoom_id",
  "meeting_passcode", "meeting_phone", "meeting_phone_passcode",
  "lv_workshop_next", "lv_workshop_time", "lv_workshop_zoom_id",
  "price_gv_print", "price_gv_digital", "price_lv_print", "price_lv_digital", "price_change_note", "price_change_date",
  "gv_issue", "lv_issue", "gv_next_issue", "lv_next_issue", "gv_theme", "lv_theme", "next_deadline_gv", "next_deadline_lv",
  "botm", "botm_lv", "gv_audio_phone", "lv_audio_phone",
  "assembly_next", "gv_open_meeting", "lv_open_meeting", "open_meeting_zoom",
];
export const LIVE_KINDS = {
  deadlines: ["pub", "limit", "limit_each"], events: ["limit", "filter", "series"], prices: ["pub"], meeting: ["limit"],
  "lv-workshop": ["limit"], issues: [], monthly: ["limit"], botm: [], bulletin: ["limit"], qr: ["url", "caption"],
};
export const EVENT_FILTER_NAMES = ["all", "workshops", "neta", "calendar", "assemblies"];
const COMMON = ["id", "layout", "title", "eyebrow", "notes", "minutes", "optional", "starts_off", "facilitator", "handout",
  "accent", "source", "takeaway", "version_notes", "version_minutes", "version_fields", "show_from", "show_until", "when",
  "lang", "print", "allow_words"];
// The layouts with a `style`, and the styles each takes: columns as panels, cards or plain; a text slide as a
// read-aloud announcement card ("script") or a centred pause ("break").
const STYLES = { columns: ["panels", "cards", "plain"], text: ["script", "break"] };
// How a handout page prints (landscape unless it says portrait)
const PRINTS = ["portrait", "landscape"];
// {ui:<key>}: a control of the player, named in the page's language (Customize → Your details …)
export const UI_KEYS = ["customize", "version", "slides", "edit", "add", "your_details", "prepare", "save_share", "notes",
  "overview", "presenter_view", "print", "full_screen", "black_screen"];
// What a version may NOT give its own value (version_fields): the build makes the slide's data from them, once for
// every version
const VERSION_FIXED = ["kind", "options", "qr"];
// layout → [required fields, optional fields]
export const LAYOUTS = {
  title: [[], ["subtitle", "lines"]],
  section: [["number"], ["subtitle"]],
  bullets: [["items"], ["numbered", "checklist"]],
  // checklist: tick boxes in place of the columns' bullets (a printed checklist in two languages …)
  columns: [["columns"], ["style", "checklist"]],
  table: [["rows"], ["header", "widths", "first_col_bold"]],
  agenda: [["items"], []],
  quote: [["quote", "credit"], []],
  activity: [["steps", "duration"], ["materials", "numbered"]],
  qa: [[], ["prompts", "note"]],
  resources: [["links"], []],
  credits: [["sources"], ["disclaimer", "note"]],
  closing: [[], ["message", "lines", "qr"]],
  text: [["body"], ["style"]],
  flow: [["steps"], []],
  live: [["kind"], ["intro", "options"]],
};
// Python's \b is Unicode-aware (a word character is any letter or digit): the same edges here, so "enseñar" and
// "lección" are words and an accented letter next to a banned word never makes a false match.
const W = "[\\p{L}\\p{N}_]";
const word = (body, flags = "giu") => new RegExp(`(?<!${W})(?:${body})(?!${W})`, flags);
// Visitor-facing wording rules (slides AND notes — anyone can open the notes). AA shares experience rather than
// teaching; GVR / RLV service is a "position"; the site never talks about how its data is gathered.
const BANNED = word(`pdfs?|crawl${W}*|scrap(?:e|es|ed|ing|er|ers)|robots?|bots?|automatically|autom[aá]ticamente|lessons?|`
  + `lecci[oó]n(?:es)?|trainers?|training|quiz${W}*|courses?|curso|curriculum|class(?:es)?|clases?|teach${W}*|taught|`
  + `enseñ${W}*|capacitaci[oó]n|jobs?`);
// Attraction rather than promotion: describe, never sell.
const PUSHY = new RegExp(`(before (?:the )?prices? (?:go up|goes up|rise|rises|increase|increases|change|changes)|`
  + `subscribe (?:now|today)|(?<!${W})hurry(?!${W})|last chance|don'?t miss out|limited[- ]time|act now)`, "iu");
const PHONE = /(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}(?!\d)/g;
const PHONE_OK = /^(?:\+?1[ .-]?)?\(?(?:800|888|877|866|855|844|833|212)\)?/;   // toll-free; AA's New York offices
const EMAIL_RE = "[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\\.[A-Za-z0-9-]+)*\\.[A-Za-z]{2,}";
const EMAIL = new RegExp(EMAIL_RE, "g");
const EMAIL_FULL = new RegExp(`^${EMAIL_RE}$`);
const EMAIL_OK = /@(?:aagrapevine\.org|aalavina\.org|aa\.org|neta65\.org)$/i;
const TOKEN = /\{(fill|live|slide):([^}]*)\}/g;
const BRACE = /\{[a-z_]+(?::[^}]*)?\}/g;
// Every token a text may hold: the three above, a span in another language {lang:es}…{/lang}, a control's name
// {ui:customize}, and — at the start of a line of the notes — the versions it is for {only:short} / {not:short}
const TOKEN_KNOWN = /^\{(?:fill|live|slide|lang|ui|only|not):[^}]*\}$/;
const CLOSE_TAG = /\{\/[a-z_]*\}/g;
const LANG_TAG = /\{lang:([^}]*)\}|\{\/lang\}/g;
const UI_TAG = /\{ui:([^}]*)\}/g;
const VERSION_TAG = /\{(only|not):([^}]*)\}/g;
const LINK = /\[([^\]]+)\]\(([^)\s]+)\)/g;
const HTML = /<[A-Za-z/!]/;
const TIME_LINE = /^\s*TIME:/m;
const PPT_TALK = new RegExp(`(?<!${W})(?:right-click|hide slide|this file|powerpoint)(?!${W})|(?<=${W})\\.pptx(?!${W})`, "iu");

// A deck file is read the way the Python checker reads it (PyYAML, YAML 1.1): `yes` / `no` / `on` / `off` (any of
// their capitalizations) are true / false, an unquoted date is a date (which no text field accepts) and `<<:` merges
// a mapping — so a deck the checker passes never stops the build, nor the other way round.
const PY_BOOL = { true: true, True: true, TRUE: true, yes: true, Yes: true, YES: true, on: true, On: true, ON: true,
  false: false, False: false, FALSE: false, no: false, No: false, NO: false, off: false, Off: false, OFF: false };
const DECK_SCHEMA = yaml.CORE_SCHEMA.withTags(
  { ...yaml.boolYaml11Tag, resolve: (s) => (Object.prototype.hasOwnProperty.call(PY_BOOL, s) ? PY_BOOL[s] : yaml.NOT_RESOLVED) },
  yaml.timestampTag, yaml.mergeTag);

const urlOk = (u) => /^https:\/\/\S+$/.test(u) || /^\/(?!\/)\S*$/.test(u) || EMAIL_FULL.test(u) || /^mailto:\S+$/.test(u);
const isStr = (v) => typeof v === "string";
const isMap = (v) => !!v && typeof v === "object" && !Array.isArray(v) && !(v instanceof Date);
const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const has = (o, k) => isMap(o) && Object.prototype.hasOwnProperty.call(o, k);
const sorted = (a) => `[${[...a].sort().map((x) => `'${x}'`).join(", ")}]`;

// A value the way Python prints it in the checker's messages ('x', None, True, [1, 2]).
function repr(v) {
  if (v === null || v === undefined) return "None";
  if (v === true) return "True";
  if (v === false) return "False";
  if (isStr(v)) return v.includes("'") && !v.includes('"') ? `"${v}"` : `'${v}'`;
  if (Array.isArray(v)) return `[${v.map(repr).join(", ")}]`;
  if (v instanceof Date) return isNaN(v) ? "None" : `datetime.date(${v.toISOString().slice(0, 10).split("-").map(Number).join(", ")})`;
  if (isMap(v)) return `{${Object.entries(v).map(([k, x]) => `${repr(k)}: ${repr(x)}`).join(", ")}}`;
  return String(v);
}
const str = (v) => (v === null || v === undefined ? "None" : String(v));

function pairOk(v, where, out) {
  if (!isMap(v) || !["en", "es"].every((k) => isStr(v[k]) && v[k].trim())) out.push(`${where}: needs an English AND a Spanish text {en: …, es: …}`);
}

/** [path, text] for every string under a node ("items[0].text", "version_notes.short" …). */
function* strings(node, p = "") {
  if (isStr(node)) yield [p, node];
  else if (Array.isArray(node)) for (let i = 0; i < node.length; i++) yield* strings(node[i], `${p}[${i}]`);
  else if (isMap(node)) for (const [k, v] of Object.entries(node)) yield* strings(v, p ? `${p}.${k}` : String(k));
}

/** A slide's minutes: "about N minutes" as a number (0.25 … 30; 1¼ → 1.25, 30 seconds → 0.5). */
const minutesOk = (v) => isNum(v) && v > 0 && v <= 30;

/** A U.S. number's ten digits, however it is written: "+1 346 248 7799" and "(346) 248-7799" → "3462487799". */
const phoneDigits = (s) => {
  const d = String(s).replace(/\D+/g, "");
  return d.length === 11 && d.startsWith("1") ? d.slice(1) : d;
};

/**
 * The phone numbers the site itself publishes, as ten digits — every number in config/site.yml (Zoom's dial-in
 * numbers, AA Grapevine's customer service …; read the way the checker reads it) and the magazines' story lines
 * (data/site/audio_project.json gv / lv `phone`). Nobody's personal number: a deck may show them (better:
 * {live:meeting_phone}, {live:gv_audio_phone}, {live:lv_audio_phone}, which follow the site when a number changes).
 * Read once (per build process), as tests/test_presentations.py published_phones reads them.
 */
let PUBLISHED = null;
export function publishedPhones() {
  if (PUBLISHED) return PUBLISHED;
  const found = new Set();
  let cfg = null;
  try {
    cfg = yaml.load(fs.readFileSync(path.join(ROOT, "config", "site.yml"), "utf8"), { schema: DECK_SCHEMA });
  } catch {
    cfg = null;
  }
  for (const [, text] of strings(cfg)) for (const mt of text.matchAll(PHONE)) found.add(phoneDigits(mt[0]));
  let audio = null;
  try {
    audio = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "site", "audio_project.json"), "utf8"));
  } catch {
    audio = null;
  }
  for (const pub of ["gv", "lv"]) {
    const line = isMap(audio) ? audio[pub] : null;
    const phone = isMap(line) ? line.phone : null;
    if (isStr(phone) && phoneDigits(phone).length === 10) found.add(phoneDigits(phone));
  }
  PUBLISHED = found;
  return found;
}

/** A slide's minutes in a version: its `version_minutes` for that version, else its `minutes` (0 without either). */
function slideMinutes(s, version) {
  const vm = isMap(s.version_minutes) && isStr(version) && has(s.version_minutes, version) ? s.version_minutes[version] : undefined;
  for (const v of [vm, s.minutes]) if (isNum(v)) return v;
  return 0;
}

function checkItems(items, where, out, depth = 0) {
  if (!Array.isArray(items) || !items.length) {
    out.push(`${where}: needs a list with at least one item`);
    return;
  }
  items.forEach((it, i) => {
    if (isStr(it)) {
      if (!it.trim()) out.push(`${where}[${i}]: empty item`);
    } else if (isMap(it) && depth === 0) {
      if (Object.keys(it).some((k) => k !== "text" && k !== "items") || !isStr(it.text) || !it.text.trim()) {
        out.push(`${where}[${i}]: an item is a string or {text: …, items: […]}`);
      }
      if (has(it, "items")) checkItems(it.items, `${where}[${i}].items`, out, depth + 1);
    } else {
      out.push(`${where}[${i}]: an item is a string` + (depth ? " (one level of sub-items only)" : ""));
    }
  });
}

/** The fields a version may give its own value on a slide of `layout` (version_fields): its title, eyebrow, source
 *  and takeaway, and the layout's own fields — not the ones the build makes the slide's data from. */
export function changeableFields(layout) {
  const [req, opt] = has(LAYOUTS, layout) ? LAYOUTS[layout] : [[], []];
  return ["title", "eyebrow", "source", "takeaway", ...req, ...opt].filter((k) => !VERSION_FIXED.includes(k));
}

/** {lang:es}…{/lang} spans of one text (`pre` names it): "en" or "es", opened and closed on the same line, one at
 *  a time — the player marks each span with its language (a notes line, a paragraph or a few words). */
function langProblems(text, pre, out) {
  for (const line of text.split("\n")) {
    let open = null;
    for (const mt of line.matchAll(LANG_TAG)) {
      if (mt[0] === "{/lang}") {
        if (open === null) out.push(`${pre}: {/lang} without its {lang:…}`);
        open = null;
        continue;
      }
      if (!LANGS.includes(mt[1])) out.push(`${pre}: {lang:${mt[1]}} — the language is "en" or "es"`);
      if (open !== null) out.push(`${pre}: a {lang:…} inside another one (close the first with {/lang})`);
      open = mt[1];
    }
    if (open !== null) out.push(`${pre}: {lang:${open}} without its {/lang} on the same line`);
  }
}

/**
 * The rules of a slide's own fields — its title, its texts, its layout's fields — as lines that start with `w`
 * ("slide 12 (agenda)"). Run on the slide, and on the slide as each version shows it (version_fields).
 */
function fieldProblems(s, layout, w, idset) {
  const out = [];
  if (!isStr(s.title) || !s.title.trim()) out.push(`${w}: title required`);
  for (const k of ["eyebrow", "source", "takeaway", "subtitle", "quote", "credit", "note", "message", "body", "intro"]) {
    if (has(s, k) && (!isStr(s[k]) || !s[k].trim())) out.push(`${w}: ${k} must be a non-empty string`);
  }
  if (has(STYLES, layout) && has(s, "style") && !STYLES[layout].includes(s.style)) out.push(`${w}: style ${STYLES[layout].join(" | ")}`);
  if (layout === "title" && has(s, "lines") && (!Array.isArray(s.lines) || !s.lines.every(isStr))) out.push(`${w}: lines — a list of strings`);
  if (layout === "section" && !(Number.isInteger(s.number) || isStr(s.number))) out.push(`${w}: number`);
  if (layout === "bullets") checkItems(s.items, `${w}.items`, out);
  if (layout === "columns") {
    const cols = s.columns;
    if (!Array.isArray(cols) || cols.length < 2 || cols.length > 4) out.push(`${w}: columns — 2 to 4`);
    else {
      cols.forEach((c, j) => {
        if (!isMap(c) || Object.keys(c).some((k) => !["heading", "gloss", "text", "items", "accent", "link"].includes(k))) {
          out.push(`${w}.columns[${j}]: {heading, gloss, text | items, accent}`);
          return;
        }
        if (has(c, "text") === has(c, "items")) out.push(`${w}.columns[${j}]: text OR items`);
        if (has(c, "items")) checkItems(c.items, `${w}.columns[${j}].items`, out);
        if (has(c, "accent") && !ACCENTS.includes(c.accent)) out.push(`${w}.columns[${j}]: accent one of ${sorted(ACCENTS)}`);
      });
    }
  }
  if (layout === "table") {
    const rows = s.rows, header = s.header;
    if (!Array.isArray(rows) || !rows.length || !rows.every((r) => Array.isArray(r) && r.length)) out.push(`${w}: rows — a list of rows (lists)`);
    else {
      const n = Array.isArray(header) ? header.length : rows[0].length;
      if (header !== undefined && header !== null && (!Array.isArray(header) || !header.every(isStr))) out.push(`${w}: header — a list of strings`);
      rows.forEach((r, j) => {
        if (r.length !== n || !r.every((x) => isStr(x) || isNum(x))) out.push(`${w}.rows[${j}]: ${n} cells (text)`);
      });
      if (has(s, "widths") && (!Array.isArray(s.widths) || s.widths.length !== n || !s.widths.every((x) => isNum(x) && x > 0))) {
        out.push(`${w}: widths — ${n} positive numbers`);
      }
    }
  }
  if (layout === "agenda") {
    const items = s.items;
    if (!Array.isArray(items) || !items.length) out.push(`${w}: items`);
    else {
      items.forEach((it, j) => {
        if (!isMap(it) || Object.keys(it).some((k) => !["time", "title", "detail", "from"].includes(k)) || !isStr(it.title) || !isStr(it.time)) {
          out.push(`${w}.items[${j}]: {time: "0:08", title, detail, from}`);
        } else if (has(it, "from") && !idset.has(it.from)) out.push(`${w}.items[${j}]: from — no slide ${repr(it.from)}`);
      });
    }
  }
  if (layout === "activity") {
    checkItems(s.steps, `${w}.steps`, out);
    const dur = s.duration;
    if (!isNum(dur) || dur <= 0) out.push(`${w}: duration (the time card's minutes)`);
    const mat = s.materials;
    if (mat !== undefined && mat !== null && !(isStr(mat) || (Array.isArray(mat) && mat.every(isStr)))) out.push(`${w}: materials — text or a list`);
  }
  if (layout === "qa" && has(s, "prompts")) checkItems(s.prompts, `${w}.prompts`, out);
  if (layout === "resources") {
    const links = s.links;
    if (!Array.isArray(links) || !links.length) out.push(`${w}: links`);
    else {
      links.forEach((k, j) => {
        if (!isMap(k) || Object.keys(k).some((x) => !["label", "url", "note"].includes(x)) || !isStr(k.label)) out.push(`${w}.links[${j}]: {label, url, note}`);
        else if (!isStr(k.url) || !urlOk(k.url)) out.push(`${w}.links[${j}]: url ${repr(k.url)} — https://…, a site path /… or an e-mail`);
      });
    }
  }
  if (layout === "credits") {
    const src = s.sources;
    if (!Array.isArray(src) || !src.length || !src.every((x) => isStr(x) && x.trim())) out.push(`${w}: sources — a list of strings`);
  }
  if (layout === "closing") {
    if (has(s, "lines") && (!Array.isArray(s.lines) || !s.lines.every(isStr))) out.push(`${w}: lines — a list of strings`);
    if (has(s, "qr") && (!isStr(s.qr) || !urlOk(s.qr) || EMAIL_FULL.test(s.qr))) out.push(`${w}: qr — a site path or an https:// address`);
  }
  if (layout === "flow") {
    const steps = s.steps;
    if (!Array.isArray(steps) || steps.length < 2 || steps.length > 6) out.push(`${w}: steps — 2 to 6`);
    else {
      steps.forEach((st, j) => {
        if (!isMap(st) || Object.keys(st).some((k) => k !== "title" && k !== "text") || !isStr(st.title)) out.push(`${w}.steps[${j}]: {title, text}`);
      });
    }
  }
  if (layout === "live") {
    const kind = s.kind;
    if (!has(LIVE_KINDS, kind)) out.push(`${w}: kind one of ${sorted(Object.keys(LIVE_KINDS))}`);
    else {
      const opts = has(s, "options") ? s.options : {};
      if (!isMap(opts)) out.push(`${w}: options — a mapping`);
      else {
        for (const k of Object.keys(opts)) {
          if (!LIVE_KINDS[kind].includes(k)) out.push(`${w}: option ${repr(k)} is not used by ${repr(kind)} (${sorted(LIVE_KINDS[kind])})`);
        }
        if (has(opts, "limit") && (!Number.isInteger(opts.limit) || opts.limit < 1 || opts.limit > 24)) out.push(`${w}: options.limit 1–24`);
        // deadlines of both magazines: this many of EACH (3 + 3), within `limit`
        if (has(opts, "limit_each") && (!Number.isInteger(opts.limit_each) || opts.limit_each < 1 || opts.limit_each > 12)) {
          out.push(`${w}: options.limit_each 1–12 (rows of each magazine)`);
        }
        if (has(opts, "pub") && !["gv", "lv", "both"].includes(opts.pub)) out.push(`${w}: options.pub gv | lv | both`);
        if (has(opts, "filter") && !EVENT_FILTER_NAMES.includes(opts.filter)) out.push(`${w}: options.filter ${EVENT_FILTER_NAMES.join(" | ")}`);
        if (has(opts, "series") && opts.series !== "all") out.push(`${w}: options.series "all" (every date of a monthly series; default: once)`);
        if (kind === "qr" && (!isStr(opts.url) || !urlOk(opts.url))) out.push(`${w}: options.url (a site path or https://) for the QR code`);
      }
    }
  }
  return out;
}

/**
 * Every problem in one parsed deck file (`stem` = its file name without .yml), as readable lines — empty = fine.
 * tests/test_presentations.py check_deck, line for line (its YAML reading is loadDecks' job here).
 */
export function checkDeck(d, stem) {
  const out = [];
  if (!isMap(d)) return [`${stem}.yml: the file must be a mapping`];
  const allowedTop = ["id", "order", "lang", "title", "short", "eyebrow", "footer", "minutes", "icon", "tone",
    "drive_title", "card", "presets", "fillins", "slides"];
  for (const k of Object.keys(d)) if (!allowedTop.includes(k)) out.push(`unknown top-level field ${repr(k)}`);
  if (d.id !== stem) out.push(`id ${repr(d.id)} must be the file name ${repr(stem)}`);
  if (!Number.isInteger(d.order) || d.order < 1 || d.order > 9) out.push("order: a whole number 1–9");
  if (d.lang !== "en") out.push('lang: "en" (the content stays English — the owner\'s decision)');
  for (const k of ["title", "short", "eyebrow", "footer", "icon"]) {
    if (!isStr(d[k]) || !d[k].trim()) out.push(`${k}: a non-empty string`);
  }
  if (!Number.isInteger(d.minutes) || d.minutes < 5 || d.minutes > 240) out.push("minutes: a whole number 5–240");
  if (!TONES.includes(d.tone)) out.push(`tone: one of ${sorted(TONES)}`);
  if (has(d, "drive_title") && (!isStr(d.drive_title) || !d.drive_title.trim())) out.push("drive_title: a string");
  if (isStr(d.icon) && fs.existsSync(path.join(ROOT, "node_modules", "lucide-static"))) {
    if (!(fs.existsSync(path.join(ROOT, "node_modules", "lucide-static", "icons", `${d.icon}.svg`))
      || fs.existsSync(path.join(ROOT, "src", "_includes", "icons", `${d.icon}.svg`)))) out.push(`icon ${repr(d.icon)}: no such lucide icon`);
  }
  const card = isMap(d.card) ? d.card : {};
  for (const k of ["title", "summary", "audience"]) pairOk(card[k], `card.${k}`, out);

  const slides = d.slides;
  if (!Array.isArray(slides) || slides.length < 5) return [...out, "slides: a list of at least 5 slides"];
  const ids = [];
  slides.forEach((s, i) => {
    const sid = isMap(s) ? s.id : null;
    if (!isStr(sid) || !ID.test(sid)) out.push(`slide ${i + 1}: id ${repr(sid)} must be lowercase letters, digits and dashes`);
    else if (ids.includes(sid)) out.push(`slide ${i + 1}: duplicate id ${repr(sid)}`);
    ids.push(isStr(sid) ? sid : `#${i + 1}`);
  });
  const idset = new Set(ids);
  const byId = new Map(slides.filter(isMap).map((s) => [s.id, s]));

  // presenter blanks
  const fillKeys = new Map();   // key → notes_only
  const fills = Array.isArray(d.fillins) ? d.fillins : [];
  if (has(d, "fillins") && !Array.isArray(d.fillins)) out.push("fillins: a list");
  fills.forEach((f, j) => {
    const w = `fillins[${j}]`;
    if (!isMap(f)) { out.push(`${w}: a mapping`); return; }
    for (const k of Object.keys(f)) {
      if (!["key", "label", "hint", "default", "shared", "notes_only"].includes(k)) out.push(`${w}: unknown field ${repr(k)}`);
    }
    const key = f.key;
    if (!isStr(key) || !KEY.test(key)) out.push(`${w}: key ${repr(key)} must be lowercase letters, digits and _`);
    else if (fillKeys.has(key)) out.push(`${w}: duplicate key ${repr(key)}`);
    else fillKeys.set(key, !!f.notes_only);
    pairOk(f.label, `${w}.label`, out);
    if (!isStr(f.hint) || !f.hint.trim()) out.push(`${w}: hint (what an empty blank shows) is required`);
    if (has(f, "default") && !isStr(f.default)) out.push(`${w}.default: a string`);
    for (const k of ["shared", "notes_only"]) if (has(f, k) && typeof f[k] !== "boolean") out.push(`${w}.${k}: true or false`);
  });

  // versions
  let presets = d.presets;
  const presetIds = [];
  if (!Array.isArray(presets) || !presets.length) {
    out.push("presets: at least one (the first is the full version)");
    presets = [];
  }
  presets.forEach((p, j) => {
    const w = `presets[${j}]`;
    if (!isMap(p)) { out.push(`${w}: a mapping`); return; }
    for (const k of Object.keys(p)) {
      if (!["id", "label", "minutes", "hide", "only", "note"].includes(k)) out.push(`${w}: unknown field ${repr(k)}`);
    }
    const pid = p.id;
    if (!isStr(pid) || !ID.test(pid) || presetIds.includes(pid)) out.push(`${w}: id ${repr(pid)} must be unique, lowercase letters, digits and dashes`);
    presetIds.push(pid);
    pairOk(p.label, `${w}.label`, out);
    if (has(p, "note")) pairOk(p.note, `${w}.note`, out);
    if (!Number.isInteger(p.minutes) || p.minutes < 1 || p.minutes > 240) out.push(`${w}: minutes, a whole number`);
    if (has(p, "hide") && has(p, "only")) out.push(`${w}: hide OR only, not both`);
    if (j === 0 && (has(p, "hide") || has(p, "only"))) out.push(`${w}: the first version is the full one (no hide / only)`);
    for (const k of ["hide", "only"]) {
      if (!has(p, k)) continue;
      if (!Array.isArray(p[k]) || !p[k].length) { out.push(`${w}.${k}: a list of slide ids`); continue; }
      for (const x of p[k]) {
        if (!idset.has(x)) out.push(`${w}.${k}: no slide ${repr(x)}`);
        else if (byId.get(x) && byId.get(x).facilitator) out.push(`${w}.${k}: ${repr(x)} is a facilitator slide (never in the show)`);
      }
    }
  });

  // slides
  let hasDisclaimer = false;
  slides.forEach((s, i) => {
    if (!isMap(s)) { out.push(`slide ${i + 1}: a mapping`); return; }
    const sid = s.id;
    const w = `slide ${i + 1} (${str(sid)})`;
    const layout = s.layout;
    if (!has(LAYOUTS, layout)) { out.push(`${w}: layout ${repr(layout)} is not one of ${sorted(Object.keys(LAYOUTS))}`); return; }
    const [req, opt] = LAYOUTS[layout];
    for (const k of Object.keys(s)) if (!COMMON.includes(k) && !req.includes(k) && !opt.includes(k)) out.push(`${w}: unknown field ${repr(k)} for layout ${repr(layout)}`);
    for (const k of req) if (!has(s, k)) out.push(`${w}: ${repr(layout)} needs ${repr(k)}`);
    const fac = s.facilitator === true;
    for (const k of ["optional", "starts_off", "facilitator", "handout", "numbered", "checklist", "first_col_bold", "disclaimer"]) {
      if (has(s, k) && typeof s[k] !== "boolean") out.push(`${w}: ${k} must be true or false`);
    }
    // (`handout`: printed for the participants — a facilitator page, or a slide that is shown AND printed)
    if (fac && (s.optional || s.starts_off)) out.push(`${w}: a facilitator slide is never in the show (no optional / starts_off)`);
    const notes = s.notes;
    if (!isStr(notes) || !notes.trim()) out.push(`${w}: notes required`);
    else {
      if (!fac && notes.trim().split(/\s+/).length < 25) out.push(`${w}: notes look thin (< 25 words): say what to SAY, DO and ASK`);
      if (TIME_LINE.test(notes)) out.push(`${w}: no TIME: line in the notes — give \`minutes:\` (the player writes the TIME line)`);
      if (PPT_TALK.test(notes) && !fac) {
        out.push(`${w}: notes still talk about PowerPoint (hidden slides, this file …) — say what to do in the web player (Customize → …)`);
      }
    }
    const m = s.minutes;
    if (fac) {
      if (!(m === null || m === undefined || m === 0 || m === false)) out.push(`${w}: a facilitator slide has no minutes`);
    } else if (!minutesOk(m)) out.push(`${w}: minutes (0.25–30) required`);
    // any slide: on a section slide the colour of its part (the slides after it take it), else this slide's own
    if (has(s, "accent") && !ACCENTS.includes(s.accent)) out.push(`${w}: accent one of ${sorted(ACCENTS)}`);
    // a slide written in Spanish (a handout, an announcement to read): the player marks it lang="es"
    if (has(s, "lang") && !LANGS.includes(s.lang)) out.push(`${w}: lang is "en" or "es" (the language the slide is written in)`);
    // a handout page prints landscape, unless it says portrait
    if (has(s, "print")) {
      if (!PRINTS.includes(s.print)) out.push(`${w}: print is "portrait" or "landscape"`);
      else if (s.handout !== true) out.push(`${w}: print is for a handout page (handout: true)`);
    }
    if (has(s, "version_notes")) {
      const vn = s.version_notes;
      if (!isMap(vn) || !Object.keys(vn).length) out.push(`${w}: version_notes {<version id>: text}`);
      else {
        for (const [k, v] of Object.entries(vn)) {
          if (!presetIds.includes(k)) out.push(`${w}: version_notes for an unknown version ${repr(k)}`);
          if (!isStr(v) || !v.trim()) out.push(`${w}: version_notes.${k} must be text`);
        }
      }
    }
    // this slide's minutes in a version (its schedule, TIME lines and the sums below use them)
    if (has(s, "version_minutes")) {
      const vm = s.version_minutes;
      if (!isMap(vm) || !Object.keys(vm).length) out.push(`${w}: version_minutes {<version id>: minutes}`);
      else {
        for (const [k, v] of Object.entries(vm)) {
          if (!presetIds.includes(k)) out.push(`${w}: version_minutes for an unknown version ${repr(k)}`);
          if (!minutesOk(v)) out.push(`${w}: version_minutes.${k} must be minutes (0.25–30)`);
        }
      }
    }
    for (const k of ["show_from", "show_until"]) {
      if (has(s, k) && (!isStr(s[k]) || !DAY.test(s[k]))) out.push(`${w}: ${k} must be a quoted "YYYY-MM-DD"`);
    }
    if (isStr(s.show_from) && isStr(s.show_until) && s.show_from > s.show_until) out.push(`${w}: show_from is after show_until`);
    if (has(s, "when") && s.when !== "price_notice") out.push(`${w}: when: "price_notice" is the only condition`);

    // the slide's own fields (its title, its texts, its layout's fields)
    const own = fieldProblems(s, layout, w, idset);
    out.push(...own);
    // a version's own value for some of them (an agenda's title, an activity's duration …): only a field of the
    // layout, and the slide as that version shows it keeps every rule (only what is new there is named)
    if (has(s, "version_fields")) {
      const vf = s.version_fields;
      if (!isMap(vf) || !Object.keys(vf).length) out.push(`${w}: version_fields {<version id>: {<field>: value}}`);
      else {
        const changeable = changeableFields(layout);
        const seen = new Set(own);
        for (const [k, v] of Object.entries(vf)) {
          if (!presetIds.includes(k)) out.push(`${w}: version_fields for an unknown version ${repr(k)}`);
          if (!isMap(v) || !Object.keys(v).length) {
            out.push(`${w}: version_fields.${k} {<field>: value}`);
            continue;
          }
          for (const f of Object.keys(v)) {
            if (!changeable.includes(f)) out.push(`${w}: version_fields.${k}: ${repr(f)} is not a field a version can change on a ${repr(layout)} slide`);
          }
          const pre = `${w} version_fields.${k}`;
          const shown = { ...s, ...Object.fromEntries(Object.entries(v).filter(([f]) => changeable.includes(f))) };
          for (const line of fieldProblems(shown, layout, pre, idset)) if (!seen.has(w + line.slice(pre.length))) out.push(line);
        }
      }
    }

    // every text of the slide: tokens, links, wording, privacy
    let allow = s.allow_words || [];
    if (!Array.isArray(allow) || !allow.every(isStr)) {
      out.push(`${w}: allow_words — a list of words`);
      allow = [];
    }
    const allowL = [...new Set(allow.map((x) => x.toLowerCase()))];
    const usedAllow = new Set();
    const scanned = Object.fromEntries(Object.entries(s).filter(([k]) => !["id", "layout", "accent", "when", "lang", "print", "show_from", "show_until", "allow_words"].includes(k)));
    for (const [where, text] of strings(scanned)) {
      if (/not an official aa grapevine/i.test(text)) hasDisclaimer = true;
      // (a version's own quote or sources are as verbatim as the slide's: "version_fields.short.quote" → "quote")
      const field = where.startsWith("version_fields.") ? where.split(".").slice(2).join(".") : where;
      const exempt = (layout === "quote" && field === "quote") || (layout === "credits" && field.startsWith("sources"));
      for (const mt of text.matchAll(TOKEN)) {
        const [, kind, key] = mt;
        if (kind === "fill") {
          if (!fillKeys.has(key)) out.push(`${w} ${where}: {fill:${key}} is not in fillins`);
          else if (fillKeys.get(key) && !where.startsWith("notes") && !where.startsWith("version_notes")) out.push(`${w} ${where}: {fill:${key}} is notes_only (never on a slide)`);
        } else if (kind === "live" && !LIVE_KEYS.includes(key)) out.push(`${w} ${where}: unknown {live:${key}}`);
        else if (kind === "slide" && !idset.has(key)) out.push(`${w} ${where}: {slide:${key}} — no such slide`);
      }
      for (const mt of text.matchAll(BRACE)) if (!TOKEN_KNOWN.test(mt[0])) out.push(`${w} ${where}: unknown placeholder ${mt[0]}`);
      for (const mt of text.matchAll(CLOSE_TAG)) if (mt[0] !== "{/lang}") out.push(`${w} ${where}: unknown placeholder ${mt[0]}`);
      langProblems(text, `${w} ${where}`, out);
      for (const mt of text.matchAll(UI_TAG)) {
        if (!UI_KEYS.includes(mt[1])) out.push(`${w} ${where}: unknown {ui:${mt[1]}} — a control of the player: ${UI_KEYS.join(", ")}`);
      }
      // {only:short,visit} / {not:short}: a line of the notes for some versions only (a TRANSITION to a slide another
      // version leaves out …) — at the start of the line, naming versions of the deck
      for (const mt of text.matchAll(VERSION_TAG)) {
        const [tag, kind, list] = mt;
        if (where !== "notes" || text.slice(text.lastIndexOf("\n", mt.index - 1) + 1, mt.index).trim()) {
          out.push(`${w} ${where}: {${kind}:…} goes at the start of a line of the notes`);
          continue;
        }
        const ids = list.split(",").map((x) => x.trim());
        if (!ids.some(Boolean)) out.push(`${w} ${where}: ${tag} names no version`);
        for (const x of ids) if (x && !presetIds.includes(x)) out.push(`${w} ${where}: ${tag} — no version ${repr(x)}`);
      }
      for (const mt of text.matchAll(LINK)) if (!urlOk(mt[2])) out.push(`${w} ${where}: link ${repr(mt[2])} — https://…, a site path or an e-mail`);
      if (HTML.test(text)) out.push(`${w} ${where}: no HTML in the text (use **bold**, _italic_, [label](url))`);
      if (!exempt) {
        for (const mt of text.matchAll(BANNED)) {
          const found = mt[0].toLowerCase();
          if (allowL.includes(found)) { usedAllow.add(found); continue; }
          out.push(`${w} ${where}: the word ${repr(mt[0])} breaks the site's wording rules `
            + `(…${text.slice(Math.max(0, mt.index - 40), mt.index + mt[0].length + 40)}…)`);
        }
        const pushy = PUSHY.exec(text);
        if (pushy) out.push(`${w} ${where}: sounds like selling (${repr(pushy[0])}) — describe, never sell`);
      }
      for (const mt of text.matchAll(PHONE)) {
        if (!PHONE_OK.test(mt[0]) && !publishedPhones().has(phoneDigits(mt[0]))) {
          out.push(`${w} ${where}: a personal-looking phone number ${repr(mt[0])} (a Zoom meeting ID? write {live:meeting_zoom_id} / {live:lv_workshop_zoom_id}; `
            + "the site's own numbers: {live:meeting_phone}, {live:gv_audio_phone}, {live:lv_audio_phone})");
        }
      }
      for (const mt of text.matchAll(EMAIL)) {
        if (!EMAIL_OK.test(mt[0])) out.push(`${w} ${where}: e-mail ${repr(mt[0])} — only service addresses (aagrapevine.org, aalavina.org, aa.org, neta65.org)`);
      }
    }
    for (const x of allowL) if (!usedAllow.has(x)) out.push(`${w}: allow_words ${repr(x)} is not used on this slide (remove it)`);
    if (layout === "quote" && isStr(s.credit) && !s.credit.trim()) out.push(`${w}: a quote needs its credit line`);
  });

  if (!hasDisclaimer) out.push('no slide says "Not an official AA Grapevine, Inc. presentation" (keep it, as in the deck)');

  // lengths: the full version ≈ the deck's minutes, each version ≈ its own — a slide counts with its
  // version_minutes for that version, else its minutes; a version's `only` shows its slides even when they
  // start off. (Sums are rounded half up, as the Python checker does.)
  const total = (shown, version) => shown.reduce((n, x) => n + slideMinutes(x, version), 0);
  const full = presets.length && isMap(presets[0]) ? presets[0].id : null;
  const base = slides.filter((x) => isMap(x) && !x.facilitator && !x.starts_off);
  if (Number.isInteger(d.minutes) && base.length) {
    const tm = total(base, full);
    if (!(0.75 * d.minutes <= tm && tm <= 1.25 * d.minutes)) out.push(`the slides' minutes add up to ${Math.floor(tm + 0.5)}, the deck says ${d.minutes}`);
  }
  for (const p of presets) {
    if (!isMap(p) || !Number.isInteger(p.minutes)) continue;
    let shown;
    if (has(p, "only") && Array.isArray(p.only)) shown = p.only.filter((x) => isStr(x) && byId.has(x)).map((x) => byId.get(x));
    else {
      const hide = new Set(Array.isArray(p.hide) ? p.hide.filter(isStr) : []);
      shown = base.filter((x) => !hide.has(x.id));
    }
    const tm = total(shown, p.id);
    if (shown.length && !(0.7 * p.minutes <= tm && tm <= 1.3 * p.minutes)) out.push(`version ${repr(p.id)}: its slides add up to ${Math.floor(tm + 0.5)} minutes, it says ${p.minutes}`);
  }
  return out;
}

/* ------------------------------------------------------------------ */
/*  Days and instants (Central time)                                   */
/* ------------------------------------------------------------------ */
const iso = (ms) => (Number.isFinite(ms) ? new Date(ms).toISOString() : null);
const ymdPlus = (ymd, n) => {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
};
/** Midnight Central at the start of a "YYYY-MM-DD" day (committee.js chicagoDayEndMs: the midnight after the day before). */
export const dayStartIso = (ymd) => (DAY.test(String(ymd)) ? iso(chicagoDayEndMs(ymdPlus(ymd, -1))) : null);
/** The last moment of a "YYYY-MM-DD" day in Central time (…T04:59:59.999Z in summer): it reads as that day, and it
 *  is past only once the day is over — a slide's show_until, a story deadline's `due`. */
export const dayEndIso = (ymd) => (DAY.test(String(ymd)) ? iso(chicagoDayEndMs(ymd) - 1) : null);
const instantIso = (v) => {
  const ms = Date.parse(String(v || ""));
  return Number.isFinite(ms) ? new Date(ms).toISOString() : null;
};

/* ------------------------------------------------------------------ */
/*  Reading the decks                                                  */
/* ------------------------------------------------------------------ */
// A short, stable hash: the same YAML content gives the same value in every build (keys sorted, so the order the
// fields are written in does not count).
function canon(v) {
  if (Array.isArray(v)) return `[${v.map(canon).join(",")}]`;
  if (v instanceof Date) return JSON.stringify(isNaN(v) ? null : v.toISOString());
  if (isMap(v)) return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canon(v[k])}`).join(",")}}`;
  return JSON.stringify(v === undefined ? null : v);
}
const hash = (s) => crypto.createHash("sha256").update(s).digest("hex").slice(0, 10);
/** A slide's `h`: its YAML fields as written — a committee edit of the slide changes it, the day's facts never do
 *  (the player tells "Changed since you edited it" by it). */
export const slideHash = (s) => hash(canon(s));

const pairOf = (v) => (isMap(v) ? { en: String(v.en ?? "").trim(), es: String(v.es ?? "").trim() } : { en: "", es: "" });
const textList = (a) => (Array.isArray(a) ? a.filter(isStr) : []);

// The {live:…} keys each "Stays current" kind covers (the card's chips: kinds). The other keys (the site's address,
// the e-mail, the panel, today's date) are facts too, but nothing a presenter would call "current news".
// (The story lines' numbers — gv_audio_phone, lv_audio_phone — and the weekly open meetings' day, time and Zoom room
// are standing information, as on /monthly/ and /meetings/: no chip.)
const KIND_OF_KEY = (key) => (key.startsWith("meeting_") ? "meeting" : key.startsWith("lv_workshop_") ? "lv-workshop"
  : key.startsWith("price_") ? "prices" : /_(?:issue|theme)$/.test(key) ? "issues" : key.startsWith("next_deadline_") ? "deadlines"
    : key.startsWith("botm") ? "botm" : key === "assembly_next" ? "events" : "");
// The order the card lists them in. A QR code is not something that changes: never a chip.
const KIND_ORDER = ["meeting", "lv-workshop", "events", "deadlines", "issues", "monthly", "prices", "botm", "bulletin"];

/** Is a price-change notice on today (config/site.yml price_changes: from `announced` through `notice_until`)?
 *  shop.js shopPriceChangeIn — the day the toolkit, the report and the digest use. */
export const priceNoticeOn = (shop, now) => !!shopPriceChangeIn(shop || {}, chicagoYmd(now));

/**
 * One deck, shaped: the global's card fields and, for its JSON file, every slide with what the player needs
 * besides its YAML fields — h, its number in the default version, its part, accent and default eyebrow.
 *   default version = the first preset (the full one), today: no facilitator slide, no slide that starts off,
 *   none outside its show_from / show_until days (Central), no `when: "price_notice"` slide while no notice is on.
 * Slides the player could not show (not a mapping, no usable id, an unknown layout) are left out — the checker has
 * named them already.
 */
function shapeDeck(d, id, now, notice) {
  const seen = new Set();
  const raw = d.slides.filter((s) => {
    const ok = isMap(s) && isStr(s.id) && ID.test(s.id) && !seen.has(s.id) && has(LAYOUTS, s.layout);
    if (ok) seen.add(s.id);
    return ok;
  });
  const presets = (Array.isArray(d.presets) ? d.presets : []).filter((p) => isMap(p) && isStr(p.id) && ID.test(p.id)).map((p) => ({
    id: p.id,
    label: pairOf(p.label),
    minutes: Number.isInteger(p.minutes) ? p.minutes : null,
    hide: textList(p.hide),
    only: Array.isArray(p.only) ? textList(p.only) : null,
    note: isMap(p.note) ? pairOf(p.note) : null,
  }));
  const fillins = (Array.isArray(d.fillins) ? d.fillins : []).filter((f) => isMap(f) && isStr(f.key) && KEY.test(f.key)).map((f) => ({
    key: f.key,
    label: pairOf(f.label),
    hint: isStr(f.hint) ? f.hint : "",
    default: isStr(f.default) ? f.default : "",
    shared: f.shared === true,
    notes_only: f.notes_only === true,
  }));

  const today = chicagoYmd(now);
  const first = presets[0] || { hide: [], only: null };
  const inFirst = (s) => (first.only ? first.only.includes(s.id) : !first.hide.includes(s.id));
  const shownToday = (s) => !s.facilitator && !s.starts_off && inFirst(s)
    && !(isStr(s.show_from) && DAY.test(s.show_from) && today < s.show_from)
    && !(isStr(s.show_until) && DAY.test(s.show_until) && today > s.show_until)
    && !(s.when === "price_notice" && !notice);

  // Parts and accents run in deck order, as the PowerPoint generator (decks/kit.py) set them: a section slide
  // starts a part ("Part 3 · Inside an issue …" — the eyebrow of the slides after it) and sets the accent its
  // slides inherit ("gv" when it names none, and before the first section); another slide's own accent colours
  // that slide alone (the slides after it keep their part's). Each slide's `accent` is the one it shows.
  // A facilitator section ("For the chair") is a part for its pages, never one of the presentation's parts.
  const versions = new Set(presets.map((p) => p.id));
  const parts = [];
  const tokens = new Set();
  const kinds = new Set();
  // A slide without an eyebrow of its own shows its part's ("Part 3 · …"), or the deck's before the first part —
  // but a Q&A or credits slide shows none, as the decks drew them (a section slide never shows one either)
  const browOf = (s, part) => (isStr(s.eyebrow) && s.eyebrow.trim() ? s.eyebrow
    : ["qa", "credits"].includes(s.layout) ? "" : part ? `Part ${part.n} · ${part.title}` : String(d.eyebrow || ""));
  let part = null, accent = "gv", n = 0;
  const slides = raw.map((s) => {
    if (s.layout === "section") {
      part = { n: s.number, title: isStr(s.title) ? s.title.trim() : "", id: s.id };
      if (!s.facilitator) parts.push(part);
      accent = ACCENTS.includes(s.accent) ? s.accent : "gv";
    }
    if (s.layout === "live" && has(LIVE_KINDS, s.kind)) kinds.add(s.kind);
    for (const [, text] of strings(s)) for (const mt of text.matchAll(TOKEN)) if (mt[1] === "live") tokens.add(mt[2]);
    const shown = shownToday(s);
    if (shown) n += 1;
    const out = {
      id: s.id,
      layout: s.layout,
      h: slideHash(s),
      n_default: shown ? n : null,
      part: part ? { n: part.n, title: part.title } : null,
      accent: ACCENTS.includes(s.accent) ? s.accent : accent,
      eyebrow: browOf(s, part),
      title: isStr(s.title) ? s.title : "",
    };
    // the layout's fields (and a slide's source / takeaway) exactly as written: tokens stay, the player fills them
    for (const [k, v] of Object.entries(s)) {
      if (!["id", "layout", "title", "eyebrow", "accent", "notes", "minutes", "version_minutes", "optional", "starts_off",
        "facilitator", "handout", "print", "version_notes", "version_fields", "show_from", "show_until", "when", "lang",
        "allow_words"].includes(k)) out[k] = v;
    }
    return Object.assign(out, {
      notes: isStr(s.notes) ? s.notes : "",
      minutes: isNum(s.minutes) ? s.minutes : null,
      // this slide's minutes in a version, where they differ from `minutes` (its schedule and TIME lines there)
      version_minutes: isMap(s.version_minutes)
        ? Object.fromEntries(Object.entries(s.version_minutes).filter(([k, v]) => versions.has(k) && minutesOk(v))) : {},
      optional: s.optional === true,
      starts_off: s.starts_off === true,
      facilitator: s.facilitator === true,
      // printed for the participants: a facilitator page (Prepare → Print), or a slide that is shown AND printed —
      // on a landscape page, unless it says portrait (null: not a handout)
      handout: s.handout === true,
      print: s.handout === true ? (s.print === "portrait" ? "portrait" : "landscape") : null,
      version_notes: isMap(s.version_notes) ? Object.fromEntries(Object.entries(s.version_notes).filter(([, v]) => isStr(v))) : {},
      // a version's own value for some of the slide's fields (the agenda's title in the 60-minute version …): the
      // versions of the deck, the fields a version may change (tokens stay)
      version_fields: isMap(s.version_fields) ? Object.fromEntries(Object.entries(s.version_fields)
        .filter(([k, v]) => versions.has(k) && isMap(v))
        .map(([k, v]) => [k, Object.fromEntries(Object.entries(v).filter(([f]) => changeableFields(s.layout).includes(f)))])
        .filter(([, v]) => Object.keys(v).length)) : {},
      show_from: dayStartIso(s.show_from),
      show_until: dayEndIso(s.show_until),
      when: s.when === "price_notice" ? "price_notice" : null,
      // the language the slide is written in: "es" for a Spanish handout or announcement (the player marks it)
      lang: LANGS.includes(s.lang) ? s.lang : "en",
    });
  });
  for (const [, text] of strings(d.footer)) for (const mt of text.matchAll(TOKEN)) if (mt[1] === "live") tokens.add(mt[2]);
  for (const k of tokens) if (KIND_OF_KEY(k)) kinds.add(KIND_OF_KEY(k));

  const card = isMap(d.card) ? d.card : {};
  return {
    id,
    order: Number.isInteger(d.order) ? d.order : 99,
    title: String(d.title || ""),
    short: String(d.short || d.title || ""),
    card: { title: pairOf(card.title), summary: pairOf(card.summary), audience: pairOf(card.audience) },
    minutes: Number.isInteger(d.minutes) ? d.minutes : null,
    icon: String(d.icon || ""),
    tone: TONES.includes(d.tone) ? d.tone : "gv",
    drive_title: isStr(d.drive_title) ? d.drive_title.trim() : "",
    count: n,
    parts: parts.map((p) => ({ n: p.n, title: p.title, id: p.id })),
    kinds: KIND_ORDER.filter((k) => kinds.has(k)),
    presets,
    fillins,
    url: `/orientation/presentations/${id}.json`,
    // for the deck's JSON file (src/pages/presentations-json.11ty.js)
    lang: "en",
    eyebrow: String(d.eyebrow || ""),
    footer: String(d.footer || ""),
    version: hash(slides.map((s) => s.h).join("\n")),
    slides,
  };
}

/**
 * Every deck file of a folder (*.yml) → { decks (by `order`), problems ["<file>: <problem>", …] }.
 * opts: now (the build's clock: monthly.js nowDate), shop (data/site/shop.json — whether a price notice is on).
 * A deck the player could not use at all is left out (not YAML, not a mapping, a file name that is not an id, no
 * slides, no version); every other problem is reported and the deck kept (src/_data/presentations.js decides
 * whether a problem stops the build).
 */
export function loadDecks(dir, opts = {}) {
  const folder = path.resolve(ROOT, String(dir || "config/presentations"));
  let files = [];
  try {
    files = fs.readdirSync(folder).filter((f) => f.endsWith(".yml")).sort();
  } catch {
    return { decks: [], problems: [] };
  }
  const now = opts.now instanceof Date ? opts.now : nowDate();
  let shop = opts.shop;
  if (shop === undefined) {
    try { shop = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "site", "shop.json"), "utf8")); } catch { shop = {}; }
  }
  const notice = priceNoticeOn(shop, now);
  const decks = [];
  const problems = [];
  for (const f of files) {
    const stem = f.slice(0, -4);
    let d;
    try {
      d = yaml.load(fs.readFileSync(path.join(folder, f), "utf8"), { schema: DECK_SCHEMA });
    } catch (e) {
      problems.push(`${f}: not valid YAML: ${String(e && e.message ? e.message : e).split("\n")[0]}`);
      continue;
    }
    if (!isMap(d)) {
      problems.push(`${f}: the file must be a mapping`);
      continue;
    }
    for (const p of checkDeck(d, stem)) problems.push(`${f}: ${p}`);
    if (!ID.test(stem) || !Array.isArray(d.slides) || !d.slides.length || !(Array.isArray(d.presets) && d.presets.some((p) => isMap(p) && isStr(p.id) && ID.test(p.id)))) {
      problems.push(`${f}: left out — the player cannot use it (an id, its slides and a first version are needed)`);
      continue;
    }
    decks.push(shapeDeck(d, stem, now, notice));
  }
  decks.sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
  return { decks, problems };
}

/* ------------------------------------------------------------------ */
/*  The facts (the {live:…} keys and the live slides' data)            */
/* ------------------------------------------------------------------ */
/** The build's context: the template's data (db, site, carry, meeting) and the clock. A context passed in again is
 *  used as it is, so what one deck reads more than once (the events, the deadlines, the month) is worked out once. */
const CONTEXT = Symbol("presentations context");
function context(c = {}) {
  if (c[CONTEXT]) return c;
  const site = c.site || {};
  const base = String(site.url || "").replace(/\/+$/, "");
  const now = c.now instanceof Date ? c.now : nowDate();
  const memo = new Map();
  return {
    [CONTEXT]: true,
    db: c.db || {}, site, carry: c.carry || {}, meeting: c.meeting || null, now,
    nowMs: now.getTime(), today: chicagoYmd(now), base,
    // an address on the site → absolute, with the base path ("/events/" → "https://…/aagrapevine/events/")
    abs: (p) => (/^https?:\/\//.test(String(p)) ? String(p) : base + (String(p).startsWith("/") ? p : "/" + p)),
    host: base.replace(/^https?:\/\//, ""),
    once: (key, fn) => {
      if (!memo.has(key)) memo.set(key, fn());
      return memo.get(key);
    },
  };
}
const lcFirst = (s) => (s ? s.charAt(0).toLocaleLowerCase("en") + s.slice(1) : s);
const clean = (s) => String(s ?? "").replace(/\s+/g, " ").trim();
const limitOf = (o, dflt) => (Number.isInteger(o && o.limit) && o.limit >= 1 && o.limit <= 24 ? o.limit : dflt);
const eachOf = (o) => (Number.isInteger(o && o.limit_each) && o.limit_each >= 1 && o.limit_each <= 12 ? o.limit_each : null);
const pubsOf = (o) => (o && (o.pub === "gv" || o.pub === "lv") ? [o.pub] : ["gv", "lv"]);
// A Zoom meeting ID or passcode kept on one line wherever it is shown ("949 476 7497" never breaks after "949"),
// and a time range too: "7:00 – 8:00 PM" with the clock's spaces made no-break (narrow) ones and a word joiner
// (U+2060) after the dash — a line may still break after an en dash before a no-break space (UAX #14: the dash
// "breaks after", LB12a), "7:00 –" / "8:00 PM" — and a time's AM / PM never on the next line ("3:00 PM Eastern").
const nb = (s) => String(s ?? "").replace(/ /g, "\u00a0");
const oneLine = (s) => String(s ?? "")
  .replace(/(\d)[ \u00a0\u2009\u202f]*\u2013[ \u00a0\u2009\u202f]*(?=\d)/g, "$1\u202f\u2013\u2060\u202f")
  .replace(/(\d)[ \u00a0\u2009]+(?=[AP]M\b)/g, "$1\u202f")
  .replace(/\u2009/g, "\u202f");

// How far ahead a deck's facts reach, so a copy opened later (saved for offline, a slow venue connection) stays
// right: a live slide's rows within about a year, at most MAX_ROWS of them; a fact's value now and its next STEPS
// values (the next four meetings, workshops, deadlines, assemblies).
const HORIZON_MS = 366 * 864e5;
const MAX_ROWS = 24;
const STEPS = 3;

/**
 * What a fact says when it has nothing to say — no data yet, its offer over, or a copy opened after the last value
 * the build knew: a phrase that reads in the slide's sentence ("Next meeting: see the Meetings page"), never a label
 * left with nothing after it. config/presentations/README.md lists the same. A key that is not here is always known
 * (the site's address, the meeting's rule and Zoom room …) or empty by design (price_change_note and
 * price_change_date outside a price notice; meeting_phone_passcode until the chair sets one).
 */
export const FALLBACKS = {
  meeting_next: "see the Meetings page",
  meeting_day: "see the Meetings page",
  meeting_after: "see the Meetings page",
  meeting_month: "Monthly",
  meeting_phone: "see the Accessibility page",
  lv_workshop_next: "see La Viña's events calendar at aalavina.org",
  price_gv_print: "see the Shop page",
  price_gv_digital: "see the Shop page",
  price_lv_print: "see the Shop page",
  price_lv_digital: "see the Shop page",
  gv_issue: "see aagrapevine.org",
  gv_next_issue: "see aagrapevine.org",
  gv_theme: "see aagrapevine.org",
  lv_issue: "see aalavina.org",
  lv_next_issue: "see aalavina.org",
  lv_theme: "see aalavina.org",
  next_deadline_gv: "see aagrapevine.org for Grapevine's themes",
  next_deadline_lv: "see aalavina.org for La Viña's themes",
  botm: "see aagrapevine.org's Book of the Month",
  botm_lv: "see aalavina.org's Libro del mes",
  gv_audio_phone: "see the Share your story page",
  lv_audio_phone: "see the Share your story page",
  assembly_next: "see the Events page",
  gv_open_meeting: "see the Meetings page",
  lv_open_meeting: "see the Meetings page",
  open_meeting_zoom: "see the Meetings page",
};

/**
 * A fact as the deck's JSON gives it: { value, steps: [{ from, value }]?, until?, fallback? } — or just its text when
 * it never changes and is never empty. A step that says what the one before it says is left out; `fallback` comes
 * only when it can be needed (an empty value, an `until`).
 */
function fact(value, steps = [], until = null, fallback = "") {
  const v = String(value ?? "");
  const st = [];
  let last = v;
  for (const s of steps) {
    const x = String((s && s.value) ?? "");
    if (!s || !s.from || x === last) continue;
    st.push({ from: s.from, value: x });
    last = x;
  }
  const out = { value: v };
  if (st.length) out.steps = st;
  if (until) out.until = until;
  if (fallback && (until || !v || st.some((s) => !s.value))) out.fallback = fallback;
  return Object.keys(out).length === 1 ? v : out;
}

/**
 * A run of values, each current until its `end` (an ISO instant) and followed by the next: [{ value, end }] → a fact
 * that switches at each end, the last end its `until` (then the fallback). The current one and the next STEPS.
 */
function run(list, fallback) {
  const xs = [];
  for (const x of list) {
    if (xs.length > STEPS) break;
    xs.push(x);
    if (!x.end) break;   // no known end: what comes after it cannot follow it
  }
  if (!xs.some((x) => x.value)) return fact("", [], null, fallback);
  return fact(xs[0].value, xs.slice(1).map((x, i) => ({ from: xs[i].end, value: x.value })), xs[xs.length - 1].end || null, fallback);
}

/** A monthly rule's line as the site writes it — "Every third Wednesday of the month · 7:00 – 8:00 PM Central time"
 *  (committee.js recurrenceText: the committee meeting's own words and clock on /meetings/, with the zone) — split
 *  at its last " · " into the rule and the time. */
function ruleAndTime(line) {
  const s = String(line || "");
  const i = s.lastIndexOf(" · ");
  return i < 0 ? { rule: "", time: "" } : { rule: s.slice(0, i), time: s.slice(i + 3) };
}

/** The committee meeting: its dates from today on, within about a year (src/_data/meeting.js, and committee.js
 *  meetingDates — the same rule — for a meeting earlier today, which the site's list drops once it has ended), its
 *  rule, time and Zoom details (config/site.yml `meeting:`). A meeting day stays in the list until midnight Central
 *  after it (`over`): during AND after tonight's meeting, the meeting's day is still tonight's (meeting_day), while
 *  the next meeting (meeting_next) is next month's from the moment tonight's ends (`end`). Without the settings,
 *  nothing: the pages' own fallback rule (the third Wednesday) is not a fact to put on a slide. */
const meetingInfo = (c) => c.once("meeting", () => {
  const m = c.site.meeting && typeof c.site.meeting === "object" ? c.site.meeting : {};
  if (!Object.keys(m).length) return { rows: [], rule: "", time: "", zoom_id: "", passcode: "", url: "" };
  const list = [...(c.meeting && Array.isArray(c.meeting.upcoming) ? c.meeting.upcoming : []), ...meetingDates(m, 1, 13)];
  const seen = new Set();
  const rows = list
    .filter((x) => x && DAY.test(String(x.ymd)) && !seen.has(x.ymd) && seen.add(x.ymd))
    .map((x) => ({ ymd: x.ymd, start: instantIso(x.start), end: instantIso(x.end), label: H.fmtDate(x.start, "en", "long"), over: iso(chicagoDayEndMs(x.ymd)) }))
    .filter((x) => x.start && Date.parse(x.over) > c.nowMs && Date.parse(x.start) <= c.nowMs + HORIZON_MS)
    .sort((a, b) => a.start.localeCompare(b.start))
    .slice(0, MAX_ROWS);
  const rt = ruleAndTime(recurrenceText(monthlyRule(m), "en"));
  return { rows, rule: rt.rule, time: oneLine(rt.time), zoom_id: nb(clean(m.meeting_id)), passcode: clean(m.passcode), url: String(m.zoom_url || "") };
});

/** The events of /events/ (committee.js normalizeEvents, in English) that are not over, without committee meetings
 *  — every date of a monthly series (the CityWide booth's Saturdays …), soonest first. */
const upcomingEvents = (c) => c.once("events", () =>
  normalizeEvents((c.db.events && c.db.events.items) || [], c.site, "en", { monthsBack: 0, monthsAhead: 0, now: c.now })
    .filter((e) => !e.past && !e.committee));
const WORKSHOP = /(?<![\p{L}\p{N}_])(?:workshops?|talleres|taller)(?![\p{L}\p{N}_])/iu;
const EVENT_FILTERS = {
  all: () => true,
  workshops: (e) => [e.title, e.item && e.item.title, e.item && e.item.i18n && e.item.i18n.title && e.item.i18n.title.en]
    .some((s) => WORKSHOP.test(String(s || ""))),
  neta: (e) => e.group === "neta",
  calendar: (e) => e.group === "calendar",
  // NETA 65's own assemblies (event-tone.js: an assembly, as /events/ colours it), never another calendar's
  assemblies: (e) => e.group === "neta" && eventTone(e) === "assembly",
};

/** La Viña's monthly workshop on Zoom: the dates of La Viña's own monthly series (config/site.yml recurring_events,
 *  host "lv") and of La Viña's listing of a month its rule skips — soonest first, not over yet. */
const lvWorkshop = (c) => c.once("lv-workshop", () => {
  const evs = upcomingEvents(c);
  const first = evs.find((e) => e.recurring && e.host === "lv" && e.series);
  if (!first) return { dates: [], first: null, time: "" };
  const dates = evs.filter((e) => (e.recurring && e.series === first.series) || e.seriesOf === first.series);
  // "2:00 – 3:00 PM Central time (3:00 PM Eastern)": the time of the series' own line on /events/ (its rule:
  // e.recurrence) and its start in La Viña's own time zone, as the decks say it
  let time = ruleAndTime(first.recurrence).time;
  const eastern = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "numeric", minute: "2-digit" }).format(new Date(first.startMs));
  if (time && eastern) time = `${time} (${eastern} Eastern)`;
  return { dates, first, time: oneLine(time) };
});

/** An issue's name on the slides, one style for both magazines (read.js issueLabel, as /contribute/ writes them):
 *  "October 2026"; La Viña's two months "September–October 2026". "" without a key. */
const issueName = (pub, key) => (/^\d{4}-\d{2}$/.test(String(key || "")) ? issueLabel({ key, pub, label: pub === "lv" ? "a-b" : "" }, "en") : "");

/**
 * The English words data/translations/overrides.yml gives a text by hand ({ "original text": { en, es } } — scripts/
 * sync/translate.py Overrides, matched as it matches them: spaces collapsed, then without accents in any case), or
 * "". Overrides always win, and build_data never lists one in an item's `machine`. Read once per build process.
 */
let HAND = null;
const handKey = (s) => String(s ?? "").normalize("NFC").replace(/\s+/g, " ").trim();
const looseKey = (s) => handKey(s).normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
function handEnglish(text) {
  if (!HAND) {
    HAND = { exact: new Map(), loose: new Map() };
    let data = null;
    try {
      data = yaml.load(fs.readFileSync(path.join(ROOT, "data", "translations", "overrides.yml"), "utf8"), { schema: DECK_SCHEMA });
    } catch {
      data = null;
    }
    for (const [k, v] of Object.entries(isMap(data) ? data : {})) {
      if (!isMap(v)) continue;
      const vals = {};
      for (const [l, x] of Object.entries(v)) if (x !== null && x !== undefined && LANGS.includes(String(l).toLowerCase())) vals[String(l).toLowerCase()] = String(x);
      if (!Object.keys(vals).length) continue;
      HAND.exact.set(handKey(k), vals);
      HAND.loose.set(looseKey(k), vals);
    }
  }
  const hit = HAND.exact.get(handKey(text)) || HAND.loose.get(looseKey(text));
  return (hit && hit.en) || "";
}
/** Is `en`, the English beside a theme written in another language (`orig`), a machine translation? The item it
 *  comes from lists "en" in its `machine`, and no hand-written English of the theme (overrides.yml) says the same. */
const machineGloss = (it, orig, en) => !!en && !!it && Array.isArray(it.machine) && it.machine.includes("en") && handEnglish(orig) !== en;

/** The story deadlines still open (read.js editorialFor: the calendar /contribute/ shows), one row per theme, the
 *  soonest first: the theme in the magazine's own language with the English words beside it when they differ
 *  (La Viña's themes are Spanish) — `gloss_machine` when those words are a machine translation (the player marks
 *  them). `due` is the last moment of the deadline day (Central); `issue_key` ("2027-05") ties the themes of one
 *  issue together (a list is never cut between them). */
const deadlineRows = (c, pubs) => c.once(`deadlines:${pubs.join("+")}`, () => {
  const rows = [];
  for (const pub of pubs) {
    for (const v of editorialFor((c.db.editorial && c.db.editorial.items) || [], pub, H, "en").upcoming) {
      if (!v.deadline || v.deadline < c.today) continue;
      const own = v.original && v.original !== v.theme;
      rows.push({
        pub,
        due: dayEndIso(v.deadline),
        due_label: dayLabel(v.deadline, "en"),
        issue: issueName(pub, v.issueKey) || v.issueLabel || "",
        issue_key: v.issueKey || "",
        theme: own ? v.original : v.theme,
        theme_lang: own ? v.origLang || (pub === "lv" ? "es" : "en") : v.themeLang || "en",
        gloss: own ? v.theme : "",
        // (themeView's `machine`: the item lists "en" in its `machine` and the English is its translation)
        gloss_machine: !!own && !!v.machine && machineGloss(v.item, v.original, v.theme),
        _ymd: v.deadline,
      });
    }
  }
  return rows.sort((a, b) => a._ymd.localeCompare(b._ymd) || (a.pub === b.pub ? 0 : a.pub === "gv" ? -1 : 1));
});
const strip = ({ _ymd, ...r }) => r;
// A theme in a sentence (the facts): its English words beside it when they are ours; a machine translation is left
// out of the facts' text, which cannot mark it (the live rows carry it with gloss_machine, and the player marks it).
const themeText = (r) => (r.gloss && !r.gloss_machine ? `${r.theme} (${r.gloss})` : r.theme);
// two rows of one issue (its themes): the same magazine and issue (or, without a key, the same label and day)
const sameIssue = (a, b) => a.pub === b.pub && (a.issue_key ? a.issue_key === b.issue_key : a.issue === b.issue && a._ymd === b._ymd);

/** One magazine's deadlines as a fact: "November 1, 2026 — June 2027: Emotional Sobriety" (two themes of an issue:
 *  "… / …"; two issues due the same day: "…; July 2027: …"), each until that day is over, then the next. */
function deadlineRun(rows, fallback) {
  const days = [];
  for (const r of rows) {
    let d = days.find((x) => x.ymd === r._ymd);
    if (!d) days.push((d = { ymd: r._ymd, label: r.due_label, issues: [] }));
    let g = d.issues.find((x) => x.issue === r.issue);
    if (!g) d.issues.push((g = { issue: r.issue, themes: [] }));
    g.themes.push(themeText(r));
  }
  const text = (d) => `${d.label} — ${d.issues.map((g) => `${g.issue ? `${g.issue}: ` : ""}${g.themes.join(" / ")}`).join("; ")}`;
  return run(days.map((d) => ({ value: text(d), end: iso(chicagoDayEndMs(d.ymd)) })), fallback);
}

/** A month's model (monthly.js monthModel: the Grapevine issue of the month, La Viña's issue that covers it, the
 *  toolkit's "put it to work" ideas) — "YYYY-MM"; thisMonth: the build's month. */
const monthOf = (c, key) => c.once(`month:${key}`, () => monthModel(key, c.db, c.carry, c.site, "en", c.now));
const thisMonth = (c) => monthOf(c, c.today.slice(0, 7));

/** An item's title in one language — its translation, or its own title when it is written in that language
 *  (never the other language in its place). */
const titleIn = (it, lang) => clean((it.i18n && it.i18n.title && it.i18n.title[lang]) || (it.lang === lang ? it.title : ""));

/** Is the English of La Viña's theme of issue `key` (`en` beside the Spanish `es`) a machine translation? The items
 *  monthly.js issueTheme takes it from, in its order — the issue itself (articles.json issues[]), else the first of
 *  its stories on the site, else La Viña's call for stories (db.editorial) — as machineGloss tells it. */
function issueGlossMachine(c, key, es, en) {
  if (!en || en === es) return false;
  const a = c.db.articles || {};
  const tri = (it, f, l) => clean((it.i18n && it.i18n[f] && it.i18n[f][l]) || it[f] || (it.extra && it.extra[f]) || "");
  const meta = (a.issues || []).find((i) => i && i.publication === "lv" && i.key === key);
  if (meta && tri(meta, "theme", "en")) return machineGloss(meta, es, en);
  const story = (a.items || []).find((s) => s && s.kind === "article" && s.status !== "gone" && s.extra && s.extra.issue_key === key
    && (s.extra.publication || s.category) === "lv");
  if (story && clean((story.i18n && story.i18n.issue_theme && story.i18n.issue_theme.en) || story.extra.issue_theme)) return machineGloss(story, es, en);
  return ((c.db.editorial && c.db.editorial.items) || []).some((i) => i && i.extra && i.extra.publication === "lv"
    && i.extra.issue_key === key && machineGloss(i, titleIn(i, "es") || clean(i.title), titleIn(i, "en")));
}

/** An issue for the slides: Grapevine's theme in English; La Viña's in Spanish, its English words as a gloss
 *  (gloss_machine: a machine translation); its name in the slides' one style (issueName). */
function issueOf(c, m, pub) {
  const x = m && m[pub];
  if (!x || !x.theme) return null;
  const label = issueName(pub, x.key) || x.label;
  if (pub === "gv") return { label, theme: x.theme, theme_lang: "en", gloss: "", gloss_machine: false };
  const es = clean(issueTheme(c.db, "lv", x.key, "es")) || x.theme;
  const en = clean(issueTheme(c.db, "lv", x.key, "en"));
  const gloss = en && en !== es ? en : "";
  return { label, theme: es, theme_lang: "es", gloss, gloss_machine: issueGlossMachine(c, x.key, es, gloss) };
}
const issueText = (x) => (x ? `${x.label} · ${themeText(x)}` : "");

/** La Viña's issue `key` before anything of it is out: the editorial calendar's call for stories for that issue
 *  (La Viña's dated themes), as monthly.js issueTheme reads the calendar for a Grapevine issue that is not out yet
 *  — its theme in Spanish with the English beside it, its name in the slides' style ("November–December 2026";
 *  else as the data pipeline writes it: community.js issueLabelOf). null without one. */
function lvCalendarIssue(c, key) {
  const themed = ((c.db.editorial && c.db.editorial.items) || [])
    .filter((i) => i && i.extra && i.extra.publication === "lv" && i.extra.issue_key === key && titleIn(i, "es"));
  if (!themed.length) return null;
  const theme = themed.map((i) => titleIn(i, "es")).join(" / ");
  const en = themed.map((i) => titleIn(i, "en")).filter(Boolean).join(" / ");
  const gloss = en && en !== theme ? en : "";
  return { label: issueName("lv", key) || issueLabelOf(themed[0], "en"), theme, theme_lang: "es", gloss,
    gloss_machine: !!gloss && themed.some((i) => machineGloss(i, titleIn(i, "es"), titleIn(i, "en"))) };
}

/** La Viña's issue `key` ("2026-11": November / December): its own data once it is out (monthModel's), else its
 *  call for stories. */
const lvIssueAt = (c, key) => {
  const m = monthOf(c, key);
  return (m.lv && m.lv.key === key && issueOf(c, m, "lv")) || lvCalendarIssue(c, key);
};

/**
 * A magazine's issues from the one of this month on: [{ key, x, end }] — Grapevine's of this month and the three
 * after it; La Viña's bimonthly issue that covers this month and the three after it. `x` as issueOf gives it, or
 * null: nothing is known of it yet (no theme in the site's data); `end` the instant the next one takes its place
 * (midnight Central on the 1st of the next one's first month). Grapevine's come from monthly.js's own rule (the
 * issue, its stories, else the calendar's call for stories); La Viña's the same way (lvIssueAt), the issue that
 * covers this month being monthModel's — or, before anything of it is out, the one La Viña's calendar gives this
 * month: an issue starts in an odd month (the data pipeline's rule: "2026-09" is September–October).
 */
const issueSeries = (c, pub) => c.once(`issues:${pub}`, () => {
  const k0 = c.today.slice(0, 7);
  const months = pub === "gv" ? 1 : 2;
  let k = k0;
  if (pub === "lv") {
    const cur = thisMonth(c).lv;
    k = cur && /^\d{4}-\d{2}$/.test(String(cur.key)) ? cur.key : Number(k0.slice(5)) % 2 ? k0 : addMonths(k0, -1);
  }
  return [0, 1, 2, 3].map((i) => {
    const key = addMonths(k, i * months);
    return { key, x: pub === "gv" ? issueOf(c, monthOf(c, key), "gv") : lvIssueAt(c, key), end: dayStartIso(`${addMonths(key, months)}-01`) };
  });
});

/** The U.S. 1-year print / digital plan of a magazine (shop.json subscriptions). */
const yearPlan = (shop, pub, type) => {
  const reg = (shop.subscriptions || []).find((s) => s && s.pub === pub && s.region === "us");
  return ((reg && reg.plans) || []).find((p) => p && p.type === type && Number(p.term_months) === 12 && Number(p.price) > 0) || null;
};

/** A plan's price in effect today (shop.js shopPlanPrice — an announced price stands in once its day has come);
 *  while an announced change is ahead (and announced): { value, from: its first moment, then: the new price }. */
function planPrice(c, pub, type) {
  const shop = c.db.shop || {};
  const p = yearPlan(shop, pub, type);
  if (!p) return { value: "", from: null, then: null };
  const value = money(shopPlanPrice(p, shop, "now", c.now), "en");
  const next = shopNextChange(shop, c.now);
  if (next && p.change && p.change.key === next.key && Date.parse(next.at.announced) <= c.nowMs) {
    const then = money(shopPlanPrice(p, shop, "after", c.now), "en");
    if (then && then !== value) return { value, from: instantIso(next.at.effective), then };
  }
  return { value, from: null, then: null };
}

/** The price change whose notice is on today (shop.js shopPriceChangeIn) → { kind "before" | "after", c } or null. */
const noticeOf = (c) => shopPriceChangeIn(c.db.shop || {}, c.today);

/** The notice's words: "Prices change on January 1, 2027: Grapevine, 1 year: print $39.00, digital $34.00; …" before
 *  its day, "New prices since January 1, 2027." from it (the Shop's and the district report's own strings). */
function noticeText(ch, kind) {
  const date = dayLabel(ch.effective, "en");
  if (kind === "after") return `${t("shop.pc_title_after", { date })}.`;
  const parts = [];
  for (const pub of ["gv", "lv"]) {
    const rows = (ch.yearly || []).filter((r) => r && r.pub === pub && Number(r.new) > 0);
    if (rows.length) parts.push(t("report.pc_pub", { pub: pub === "lv" ? "La Viña" : "Grapevine", list: rows.map((r) => `${t(`report.t_${r.type}`)} ${money(r.new, "en")}`).join(", ") }));
  }
  if (Number(ch.books_more) > 0) parts.push(t("report.pc_books", { amount: money(ch.books_more, "en") }));
  return `${t("shop.pc_title_before", { date })}${parts.length ? `: ${parts.join("; ")}` : ""}.`;
}

/** The Books of the Month on offer today (shop.js shopBotm: Grapevine's first), as the slides name them. */
const botmList = (c) => c.once("botm", () =>
  shopBotm(c.db.shop || {}, "en", c.today, (k, l, v) => H.translateKey(k, l, v), c.now).map((b) => ({
    pub: b.pub,
    title: b.title,
    mag: b.mag,
    lang: b.itemLang,
    note: b.pct && b.endsLabel ? t("monthly.botm_off", { pct: b.pct, date: b.endsLabel }) : b.endsLabel ? t("monthly.botm_until", { date: b.endsLabel }) : "",
    url: c.abs("/shop/#botm"),
    until: b.ends ? iso(chicagoDayEndMs(b.ends)) : null,
  })));

/** A date as the decks write it in a sentence (AP style): "Nov. 5, 2026", "March 4, 2027". */
const AP_MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];
const apDate = (ymd) => {
  const [y, m, d] = String(ymd).split("-").map(Number);
  return `${AP_MONTHS[m - 1]} ${d}, ${y}`;
};

/** The weekly open meetings of /meetings/#weekly-open (committee.js weeklyOpenAll, in English: data/site/
 *  weekly_open.json — La Viña's from config/site.yml lavina_weekly_open), each with its data item. */
const weeklyOpens = (c) => c.once("weekly", () => {
  const items = ((c.db.weekly_open && c.db.weekly_open.items) || []).filter(isMap);
  return weeklyOpenAll(items, "en", c.now).map((w) => ({ w, it: items.find((it) => (it.id || "") === w.id) || {} }));
});

/** The next NETA 65 assembly as one line: "NETA 65 Spring Assembly 2027 · Fri, Mar 19 – Sun, Mar 21, 2027" (its
 *  days as /events/ writes a range), "(details to be confirmed)" while the event file says it is tentative. */
const assemblyText = (e) => `${e.title} · ${e.rangeLabel || e.dateLabel}${e.tentative ? ` (${lcFirst(t("committee.events.tentative"))})` : ""}`;

/**
 * Every {live:…} value of the day → { key: "text" | { value, steps?, until?, fallback? } } (all of LIVE_KEYS, whether
 * a deck uses them or not: a presenter's own slide may name any of them). A value that changes gives what it will
 * say next (steps, the facts the build already has), so a copy opened weeks later is still right; past what the
 * build knew it says its fallback (FALLBACKS), never a date that is over.
 */
export function liveFacts(ctx) {
  const c = context(ctx);
  const out = {};
  out.site = c.host;
  out.site_url = c.base ? c.base + "/" : "";
  out.email = String(c.site.contact_email || "");
  const di = driveInfo((c.db && c.db.status) || {}, c.site);
  out.panel = (di.panel && di.panel.label) || "";
  out.as_of = H.fmtDate(c.now, "en", "medium");
  // The month's facts switch together at midnight Central on the 1st — the month, the year, this month's issues and
  // the next ones (below) — so a slide that shows this issue beside the next one never skips a month, even on a
  // copy opened after the month changed. The month and the year for the next twelve months; `as_of` stays the day
  // the facts were read.
  const k0 = c.today.slice(0, 7);
  const months = Array.from({ length: 11 }, (_, i) => addMonths(k0, i + 1));
  out.month = fact(monthLabel(k0, "en"), months.map((k) => ({ from: dayStartIso(`${k}-01`), value: monthLabel(k, "en") })));
  out.year = fact(k0.slice(0, 4), months.map((k) => ({ from: dayStartIso(`${k}-01`), value: k.slice(0, 4) })));

  // The committee meeting. meeting_next is the next meeting until it ENDS ("the next meeting" in a workshop: after
  // 8 PM on a meeting night it is next month's). The committee deck reads right during AND after tonight's meeting
  // with the meeting's day: meeting_day is tonight's until midnight Central after it (the title slide), meeting_after
  // the one after it (the "Next meeting" slide shown at the end of tonight's meeting), meeting_month the month of
  // meeting_day ("October 2026 meeting"). Those three move on together, at midnight.
  const mt = meetingInfo(c);
  const unended = mt.rows.filter((r) => !(Date.parse(r.end) <= c.nowMs));
  out.meeting_next = run(unended.map((r) => ({ value: r.label, end: r.end || r.over })), FALLBACKS.meeting_next);
  out.meeting_day = run(mt.rows.map((r) => ({ value: r.label, end: r.over })), FALLBACKS.meeting_day);
  out.meeting_after = run(mt.rows.slice(1).map((r, i) => ({ value: r.label, end: mt.rows[i].over })), FALLBACKS.meeting_after);
  out.meeting_month = run(mt.rows.map((r) => ({ value: monthLabel(r.ymd.slice(0, 7), "en"), end: r.over })), FALLBACKS.meeting_month);
  out.meeting_rule = lcFirst(mt.rule);
  out.meeting_time = mt.time;
  out.meeting_zoom_id = mt.zoom_id;
  out.meeting_passcode = mt.passcode;
  // joining it by phone, as /accessibility/#phone gives it (access.js axPhone: config/site.yml phone_access + the
  // meeting's ID): Zoom's first dial-in number and its city — "+1 346 248 7799 (Houston)" — and what a caller types
  // as the passcode (the chair's numbers-only phone passcode, or a numbers-only meeting passcode; else "")
  const phone = axPhone(c.site, [], "en", (k) => k);
  const byPhone = phone.meetings.find((x) => x.key === "committee");
  const dial = phone.numbers[0];
  out.meeting_phone = fact(byPhone && dial ? (dial.city ? `${dial.display} (${dial.city})` : dial.display) : "", [], null, FALLBACKS.meeting_phone);
  out.meeting_phone_passcode = byPhone ? byPhone.pass : "";

  // La Viña's monthly workshop: each date until that workshop ends
  const lv = lvWorkshop(c);
  out.lv_workshop_next = run(lv.dates.map((e) => ({ value: e.dateLabel, end: iso(e.endMs) })), FALLBACKS.lv_workshop_next);
  out.lv_workshop_time = lv.time;
  out.lv_workshop_zoom_id = lv.first ? nb(lv.first.meetingId) : "";

  // the 1-year prices: today's, and the announced one from its day
  for (const pub of ["gv", "lv"]) {
    for (const type of ["print", "digital"]) {
      const p = planPrice(c, pub, type);
      out[`price_${pub}_${type}`] = fact(p.value, p.from ? [{ from: p.from, value: p.then }] : [], null, FALLBACKS[`price_${pub}_${type}`]);
    }
  }
  // the notice while it is on — before its day, then "New prices since …" until it ends; empty otherwise
  const hit = noticeOf(c);
  const noticeEnd = hit ? instantIso(hit.c.at.notice_end) : null;
  if (hit && hit.kind === "before") {
    out.price_change_note = fact(noticeText(hit.c, "before"), [{ from: instantIso(hit.c.at.effective), value: noticeText(hit.c, "after") }], noticeEnd);
  } else if (hit) out.price_change_note = fact(noticeText(hit.c, "after"), [], noticeEnd);
  else out.price_change_note = "";
  out.price_change_date = hit ? fact(dayLabel(hit.c.effective, "en"), [], noticeEnd) : "";

  // this month's issue, the next one and this month's theme alone ("Loneliness"): Grapevine's for the next three
  // months, La Viña's for this issue and the next one, each switching on the 1st of its first month
  for (const pub of ["gv", "lv"]) {
    const xs = issueSeries(c, pub);
    const n = pub === "gv" ? 3 : 2;
    out[`${pub}_issue`] = run(xs.slice(0, n).map((s) => ({ value: issueText(s.x), end: s.end })), FALLBACKS[`${pub}_issue`]);
    out[`${pub}_next_issue`] = run(xs.slice(1, n + 1).map((s, i) => ({ value: issueText(s.x), end: xs[i].end })), FALLBACKS[`${pub}_next_issue`]);
    out[`${pub}_theme`] = run(xs.slice(0, n).map((s) => ({ value: s.x ? themeText(s.x) : "", end: s.end })), FALLBACKS[`${pub}_theme`]);
  }
  // each magazine's next story deadlines, each until its day is over
  const rows = deadlineRows(c, ["gv", "lv"]);
  out.next_deadline_gv = deadlineRun(rows.filter((r) => r.pub === "gv"), FALLBACKS.next_deadline_gv);
  out.next_deadline_lv = deadlineRun(rows.filter((r) => r.pub === "lv"), FALLBACKS.next_deadline_lv);
  // Grapevine's Book of the Month (botm) and La Viña's Libro del mes (botm_lv), each until its offer ends
  const books = botmList(c);
  for (const [key, pub] of [["botm", "gv"], ["botm_lv", "lv"]]) {
    const b = books.find((x) => x.pub === pub);
    out[key] = fact(b ? b.title : "", [], b ? b.until : null, FALLBACKS[key]);
  }
  // the magazines' story lines — record your story by phone (/contribute/#record), as their official pages give them
  const ap = c.db.audio_project || {};
  out.gv_audio_phone = fact(clean(ap.gv && ap.gv.phone), [], null, FALLBACKS.gv_audio_phone);
  out.lv_audio_phone = fact(clean(ap.lv && ap.lv.phone), [], null, FALLBACKS.lv_audio_phone);

  // the next NETA 65 assembly, until it is over, then the one after it (the assemblies of /events/)
  const assemblies = upcomingEvents(c).filter((e) => EVENT_FILTERS.assemblies(e) && e.startMs <= c.nowMs + HORIZON_MS);
  out.assembly_next = run(assemblies.map((e) => ({ value: assemblyText(e), end: iso(e.endMs) })), FALLBACKS.assembly_next);

  // the weekly open meetings (/meetings/#weekly-open): "Wednesdays, 11:00 AM Central (noon Eastern)" — La Viña's
  // with its first meeting, "starting Nov. 5, 2026", which says "since Nov. 5, 2026" from that day — and their Zoom
  // room, "Zoom 871 2036 8287, passcode 238047" (both meetings' when they share it, as they do today)
  const wos = weeklyOpens(c);
  const when = (w) => [w.day, w.timeCentral].filter(Boolean).join(", ") + (w.hostTime ? ` (${lcFirst(w.hostTime)})` : "");
  const gvo = wos.find((x) => !x.w.isLv), lvo = wos.find((x) => x.w.isLv);
  out.gv_open_meeting = fact(gvo ? when(gvo.w) : "", [], null, FALLBACKS.gv_open_meeting);
  const starts = lvo ? [lvo.it.extra && lvo.it.extra.starts, c.site.lavina_weekly_open && c.site.lavina_weekly_open.starts].find((x) => DAY.test(String(x || ""))) : "";
  if (lvo && starts && Date.parse(dayStartIso(starts)) > c.nowMs) {
    out.lv_open_meeting = fact(`${when(lvo.w)}, starting ${apDate(starts)}`, [{ from: dayStartIso(starts), value: `${when(lvo.w)}, since ${apDate(starts)}` }], null, FALLBACKS.lv_open_meeting);
  } else out.lv_open_meeting = fact(lvo ? when(lvo.w) + (starts ? `, since ${apDate(starts)}` : "") : "", [], null, FALLBACKS.lv_open_meeting);
  const room = (w) => (w.zoomId ? `Zoom\u00a0${nb(w.zoomId)}${w.passcode ? `, passcode\u00a0${nb(w.passcode)}` : ""}` : "");
  const rooms = [gvo, lvo].filter((x) => x && room(x.w));
  const shared = rooms.length === 2 && room(rooms[0].w) === room(rooms[1].w);
  out.open_meeting_zoom = fact(rooms.length === 1 || shared ? room(rooms[0].w)
    : rooms.map((x) => `${x.w.isLv ? "La Viña" : "Grapevine"}: ${room(x.w)}`).join(" · "), [], null, FALLBACKS.open_meeting_zoom);
  return Object.fromEntries(LIVE_KEYS.map((k) => [k, out[k] ?? ""]));
}

/** A QR code for a site path or an https:// address: { url (absolute), label, svg } (community.js qrSvg). */
function qrData(c, target, caption) {
  const u = isStr(target) && urlOk(target) && !EMAIL_FULL.test(target) && !/^mailto:/.test(target) ? c.abs(target) : "";
  const label = clean(caption) || u.replace(/^https?:\/\//, "");
  return { url: u, label, svg: u ? qrSvg(u, { label }) : "" };
}

/**
 * The `data` of a live slide of `kind` with its `options` — the shapes the player reads (SPEC §2 and UPDATE 3).
 * Dated rows (deadlines, events, meetings, La Viña's workshops): every one known within about a year, at most
 * MAX_ROWS, soonest first, with the slide's `limit` (and the deadlines' `limit_each`) — the player leaves out the
 * rows already past on the viewer's clock, THEN applies the limits, so a copy opened later still fills the slide.
 * The toolkit's ideas and the bulletin's posts never pass: cut at `limit` here (the limit comes along all the
 * same). Rows already past at the build are left out. Labels are English, addresses absolute (with the base path).
 */
export function liveData(kind, options, ctx) {
  const c = context(ctx);
  const o = isMap(options) ? options : {};
  const ahead = (ms) => ms <= c.nowMs + HORIZON_MS;
  switch (kind) {
    case "deadlines": {
      // whole issues: the list is never cut between two themes of one issue
      const rows = [];
      for (const r of deadlineRows(c, pubsOf(o))) {
        if (!ahead(Date.parse(r.due))) continue;
        if (rows.length >= MAX_ROWS && !sameIssue(rows[rows.length - 1], r)) break;
        rows.push(r);
      }
      return { rows: rows.map(strip), limit: limitOf(o, 6), limit_each: eachOf(o), url: c.abs("/contribute/#deadlines") };
    }
    case "events": {
      // every date of a monthly series (the booth's Saturdays …), not only its next one, so a copy opened later still
      // knows the series' next date; `series` is the series' own id (config/site.yml recurring_events: the same on
      // every date and in every build — La Viña's own listing of a month its rule skips carries it too), "" for a
      // one-off event: the player keeps one row per series, its next date still ahead
      const f = EVENT_FILTERS[o.filter] || EVENT_FILTERS.all;
      const rows = [];
      for (const e of upcomingEvents(c)) {
        if (!f(e) || !ahead(e.startMs)) continue;
        rows.push({
          // (its time range on one line, as the meeting's: "5:00 – 8:00 PM" never cut at the dash)
          start: iso(e.startMs), end: iso(e.endMs), all_day: !!e.allDay, date_label: e.dateLabel, time_label: oneLine(e.timeLabel),
          title: e.title, place: e.location || "", online: !!e.isOnline, platform: e.platform || "", kind: eventTone(e),
          url: e.detailsUrl || c.abs("/events/"), series: e.series || e.seriesOf || "",
          // details not final yet (an assembly's venue …): the slide says so, as the Events page does
          tentative: !!e.tentative,
        });
        if (rows.length >= MAX_ROWS) break;
      }
      return { rows, limit: limitOf(o, 5), url: c.abs("/events/") };
    }
    case "prices": {
      const rows = [];
      for (const pub of pubsOf(o)) {
        for (const plan of ["print", "digital"]) {
          const p = planPrice(c, pub, plan);
          if (p.value) rows.push({ pub, plan, price: p.value, then: p.then || null });
        }
      }
      const hit = noticeOf(c);
      const ch = hit ? hit.c : null;
      return {
        rows,
        change: ch ? {
          at: instantIso(ch.at.effective), label: dayLabel(ch.effective, "en"), notice_from: instantIso(ch.at.announced),
          notice_until: instantIso(ch.at.notice_end), books_more: Number(ch.books_more) > 0 ? money(ch.books_more, "en") : "",
        } : null,
        url: c.abs(ch ? "/shop/#price-changes" : "/shop/#subscriptions"),
      };
    }
    case "meeting": {
      // each date with its end (the player leaves a meeting out once it has ended)
      const mt = meetingInfo(c);
      return {
        rows: mt.rows.map((r) => ({ start: r.start, end: r.end, label: r.label })),
        limit: limitOf(o, 3),
        rule: mt.rule, time: mt.time, zoom_id: mt.zoom_id, passcode: mt.passcode, url: mt.url,
        page: c.abs("/meetings/#committee-meeting"),
      };
    }
    case "lv-workshop": {
      const lv = lvWorkshop(c);
      return {
        rows: lv.dates.filter((e) => ahead(e.startMs)).slice(0, MAX_ROWS).map((e) => ({ start: iso(e.startMs), end: iso(e.endMs), label: e.dateLabel })),
        limit: limitOf(o, 3),
        time: lv.time,
        zoom_id: lv.first ? nb(lv.first.meetingId) : "",
        url: lv.first ? lv.first.online || "" : "",
        contact: lv.first ? lv.first.contact : "",
        page: lv.first && lv.first.detailsUrl ? lv.first.detailsUrl : c.abs("/events/"),
      };
    }
    case "issues":
      // this month's issues, as {live:gv_issue} / {live:lv_issue} give them
      return { month: monthLabel(c.today.slice(0, 7), "en"), gv: issueSeries(c, "gv")[0].x, lv: issueSeries(c, "lv")[0].x, url: c.abs("/read/") };
    case "monthly": {
      const mm = thisMonth(c);
      return {
        month: monthLabel(mm.key, "en"),
        url: c.abs(`/monthly/${mm.key}/`),
        tips: (mm.tips || []).slice(0, limitOf(o, 3)).map((x) => ({ title: x.title, text: x.text })),
        limit: limitOf(o, 3),
      };
    }
    case "botm": {
      const [first, also] = botmList(c);
      const one = (b) => ({ title: b.title, mag: b.mag, lang: b.lang, note: b.note, url: b.url, until: b.until });
      return first ? { ...one(first), also: also ? one(also) : null } : { title: "", mag: "", lang: "", note: "", url: c.abs("/shop/#botm"), until: null, also: null };
    }
    case "bulletin": {
      // the newest posts first, by their own day (a scheduled post by its `publish` day) — not /bulletin/'s order,
      // where pinned posts come first
      const day = (p) => {
        const d = chicagoYmd(p.date || p.first_seen || "");
        const pub = String((p.extra && p.extra.publish) || "").slice(0, 10);
        return DAY.test(pub) && pub > d ? pub : d;
      };
      const posts = announcementList((c.db.announcements && c.db.announcements.items) || [], c.now)
        .map((p, i) => ({ p, i, d: day(p) }))
        .sort((a, b) => b.d.localeCompare(a.d) || a.i - b.i)
        .slice(0, limitOf(o, 3));
      return {
        rows: posts.map(({ p, d }) => ({ title: clean(H.pickLang(p, "title", "en")) || clean(p.title), date_label: d ? dayLabel(d, "en") : "", url: c.abs(`/bulletin/#${p._anchor}`) })),
        limit: limitOf(o, 3),
        url: c.abs("/bulletin/"),
      };
    }
    case "qr":
      return qrData(c, o.url, o.caption);
    default:
      return null;
  }
}

/** The PowerPoint copy in the committee's Drive slides folder: the newest Drive file whose title is the deck's
 *  drive_title → { view, date } or null. */
function driveCopy(c, title) {
  if (!title) return null;
  const hit = ((c.db.drive && c.db.drive.items) || [])
    .filter((it) => it && it.source === "drive" && it.status !== "gone" && clean(it.title) === clean(title))
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))[0];
  if (!hit) return null;
  const view = (hit.extra && hit.extra.view_url) || hit.url || "";
  return view ? { view, date: DAY.test(String(hit.date || "").slice(0, 10)) ? String(hit.date).slice(0, 10) : "" } : null;
}

/** /orientation/presentations/<id>.json for one deck of the global (`presentations.decks`). */
export function deckJson(deck, ctx) {
  const c = context(ctx);
  const slides = (deck.slides || []).map((s) => {
    let data = null;
    if (s.layout === "live") data = liveData(s.kind, s.options, c);
    // a closing slide's QR code (`qr: "/"`): the player shows the code, it never makes one
    else if (s.layout === "closing" && isStr(s.qr)) data = qrData(c, s.qr, "");
    return { ...s, data };
  });
  return {
    app: "gv-presentation",
    schema: 1,
    id: deck.id,
    lang: deck.lang || "en",
    title: deck.title,
    short: deck.short,
    eyebrow: deck.eyebrow,
    footer: deck.footer,
    minutes: deck.minutes,
    built: instantIso(c.site.built) || new Date().toISOString(),
    as_of: H.fmtDate(c.now, "en", "medium"),
    version: deck.version,
    site: { url: c.base ? c.base + "/" : "", host: c.host },
    drive: driveCopy(c, deck.drive_title),
    presets: deck.presets,
    fillins: deck.fillins,
    live: liveFacts(c),
    slides,
  };
}

export default function (eleventyConfig, helpers) {
  if (helpers) H = { ...H, ...helpers };
  // {{ deck | presDeckJson(data) }} — src/pages/presentations-json.11ty.js: this.presDeckJson(data.deck, data)
  eleventyConfig.addFilter("presDeckJson", (deck, data) => JSON.stringify(deckJson(deck, data || {})) + "\n");
}
