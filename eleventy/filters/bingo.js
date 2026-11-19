// GVR / RLV Bingo (the GVR / RLV corner's bingo cards: /gvr/bingo/ and /es/gvr/bingo/, the /gvr/ teaser) — the pool
// of squares at build time: content/bingo/bingo.csv read, checked and filled in. Auto-loaded by eleventy.config.js
// like every eleventy/filters/*.js (its default export below registers nothing: the bingo pages' filter bingoSample
// is eleventy/filters/bingo-sample.js's, auto-loaded the same way; tGroup is eleventy.config.js's). Owned by
// src/_data/bingo.js (the `bingo` global); the cards themselves are drawn and laid out by
// src/assets/js/bingo-core.js (window.GVBingo, pure: the browser's builder and the build's server-rendered sample
// card) and src/assets/js/bingo.js (the Alpine builder), on src/pages/gvr-bingo.njk.
// content/bingo/README.md is the owner's guide to every column; aagrapevine-ops/r34/SPEC.md §2 the data contract.
//
//   checkBingoCsv(text, opts)  → { items, problems, rows, rowOf } — every row checked and shaped. THE rules (below):
//                                tests/test_bingo_csv.py is their Python twin (what the committee's Code check runs
//                                on the real file), and the two must give the same lines and items — keep them in
//                                step. Pure: the text and opts only (no file, no clock, no settings), so the twin
//                                can hold every line to it. Placeholders stay as written ({gv_meeting} …).
//   bingoInfo(site, weekly)    → the facts the cards print (SPEC §2 `info`): our committee and Area names, the
//                                contact e-mail, the site's short address, the home and /gvr/ addresses in both
//                                languages, our Grapevine Meeting and the committee meeting (each a long, a mid and
//                                a short line), AA Grapevine's Weekly Open and La Viña's open meeting — each
//                                { en, es }, or null when the settings have none
//   fillItems(items, info, opts) → { items, problems } — the build-time placeholders filled in with `info` in each
//                                language ({event} stays: the builder's "Event name", filled in the browser); a row
//                                whose placeholder has no value in this build is left out, with a problem line
//   loadBingo(opts)            → the `bingo` global: { file, found, rows, items, problems, cats, wheres, info }
//   logBingoProblems(problems) → the build log's "[bingo] N problem(s) — left out:" lines
//   catNamesOf(json)           → the categories src/_i18n/bingo.json names ("bingo.cat.<cat>" with en and es)
//   measure(text)              → a cell's length as the limits count it (a placeholder counts as 20)
//   bingoRefusedIn(text)       → the refused words in a cell: booth.js refusedIn's, then BINGO_REFUSED's
//
// The CSV (SPEC §2): UTF-8 (a BOM is fine; a byte that is not UTF-8 is named), commas, RFC 4180 quotes (booth.js
// parseCsv — the booth display's reader, the one Python's csv module agrees with), the first row the header: column
// names in any order and capitalization, an unknown column ignored, a known one twice → the first one (named); the
// header needs id, type and cat. A blank row and a row whose id starts with "#" (a comment) are skipped. A row with
// any mistake is left out (every mistake of it is listed); a row switched off (on = no) is checked like the others
// but not shown. Every cell is read as one line: Unicode NFC, every run of white space one space, nothing around it
// (white space spelled out, as booth.js reads it: JavaScript's and Python's \s disagree on a few characters).
// Lengths are counted in characters as a person counts them (code points: "ñ" is one).
//   id          needed; a–z, 0–9 and dashes (no dash at either end or twice in a row), 48 at most; unique
//   on          yes / blank (yes) / no (yes, y, true, 1, si, sí · no, n, false, 0)
//   type        needed, one of TYPES (capitals ignored): check (do it, cross it off), name (find someone: "Name &
//               group"), phone (trade numbers: "Name & phone"), write (write an answer: label_*, default "Answer"),
//               sign (someone initials it), info (an information square: our meetings, the contact — only in cat
//               meetings, the builder's "Meetings & contact squares")
//   pub         gv, lv, both — blank = both (and the booth's spellings: grapevine, lavina, la viña, ambos, gv/lv …)
//   cat         needed, one of CATS (capitals ignored) — or a new category that src/_i18n/bingo.json names
//               ("bingo.cat.<cat>" in English and Spanish: opts.catNames; the line says so when it is missing)
//   where       blank = everywhere; else WHERES separated by spaces, ";" or "," (capitals ignored, twice = once)
//   pin         yes / blank / no — yes: pre-ticked "Always on every card" in the builder
//   weight      blank 1; a number from 0.5 to 5 ("1.5" or "1,5")
//   from, until optional real days written YYYY-MM-DD, years 2000–2099; until not before from
//   text_*      the square's words: LIMITS.text (90) at most, a placeholder counting LIMITS.placeholder (20)
//   short_*     the words on big grids (7×7 and up): LIMITS.short (36) at most; NEEDED when that language's text
//               is longer than 36 (measured the same way)
//   label_*     the write-in line's label for name / phone / write / sign rows: LIMITS.label (24) at most; blank =
//               the type's default; never on check / info rows
//   source_url  optional: an https:// link where a fact can be checked (never shown)
//   notes       the committee's own; never shown, never checked
// Languages: a row is offered in a language when it has that language's text_*; then everything its type needs in
// that language is there (short_* when the text is long). short_* / label_* without text_* in the same language is
// a mistake; so is a row with no text at all. Every shown cell (text, short, label) may use only the PLACEHOLDERS
// and says none of the refused words — booth.js refusedIn (PDF, donations, contributions to Grapevine, sales and
// urgency words, unverified claims, "Conference-approved", "today only" without {event}) and bingo's own
// (BINGO_REFUSED: no selfies or photos of people, no last or full names — anonymity: first names only). Two rows
// that are on never have the same text in a language (a card could show the same square twice), nor the same
// big-grid words (short_*, else the text: a big card could show the same words twice): the later one is named and
// left out (the comparison ignores capitals; rows with other mistakes, or off, take no part).
// Problem lines are the booth's: { where: "bingo.csv row 14 (people-gvr-today)", en, es } — "text_en: 95 characters
// (90 at most)" — every line in both languages (the twin checks each English line has its Spanish one).
//
// Items (SPEC §2 data contract), in file order: { id, type, pub, cat, where: [...] ([] = everywhere), pin, weight,
// from, until (YYYY-MM-DD or null), text: { en, es }, short: { en, es }, label: { en, es } } — a language the row
// is not offered in is "" in all three; short is short_* or, when that is blank, the text itself (what a big grid
// shows: never ""); label "" = the type's default. After fillItems, every placeholder but {event} is filled in.
//
// Placeholders (PLACEHOLDERS; anything else in {…} is a mistake): {event} — the builder's "Event name" ("this event" /
// "este evento" when it is empty), filled in the browser; and, filled here from the settings (bingoInfo): {committee},
// {area}, {email} (config/site.yml meeting.chair_email, else site.contact_email), {site} (the site's address without
// https:// — grapevine.neta65.org on the live site), {gv_meeting} / {gv_meeting_short} (our Grapevine Meeting,
// recurring_events key grapevine-meeting), {committee_meeting} / {committee_meeting_short} (config/site.yml
// meeting:), {gv_weekly} / {gv_weekly_short} (AA Grapevine's Weekly Open, data/site/weekly_open.json) and
// {lv_weekly} / {lv_weekly_short} (La Viña's open meeting, the same file, while config/site.yml lavina_weekly_open is
// enabled) — each _short one the words for big grids ("1st Wed · 7 PM", "Wed 11 AM · Zoom"); the long monthly ones
// with the zone and the platform ("3rd Wednesday of the month, 7 – 8 PM Central, Google Meet"). The cards' strip
// also has a mid line for each monthly meeting ("3rd Wed · 7 PM · Google Meet": `info` only, no placeholder). Their
// words are worked out with the site's own readers — monthlyRule (the rules as the sync reads them), central-time.js
// zoneInstant / zoneParts / overnight and Intl (the clock times, in Central time, the way cmTimeRange writes them),
// esMeridiem (the site's "p. m."), the i18n's committee.rule / committee.ord.* (the Spanish day: "cada tercer
// miércoles del mes"), committee.js platformOf / weeklyOpenAll (the platform, the weekly meetings' own "when" and
// next start) — never a time written by hand; the few words only the cards use are in BINGO_WORDS, in both languages.
// AA principles: anonymity (first names only, no photos of people), attraction not promotion (refusedIn), no money
// asks — the checker refuses what the booth refuses, and more.

import fs from "node:fs";
import path from "node:path";
import { parseCsv, refusedIn, splitUrl } from "./booth.js";
import { platformOf, weeklyOpenAll } from "./committee.js";
import { monthlyRule, siteUrl, esMeridiem, translateKey, TZ } from "../../eleventy.config.js";
import { zoneInstant, zoneParts, overnight } from "../central-time.js";

const LANGS = ["en", "es"];
const LOCALES = { en: "en-US", es: "es-US" };

/* ------------------------------------------------------------------ */
/*  The CSV's columns, types, categories, occasions and placeholders    */
/* ------------------------------------------------------------------ */
/** Every column of content/bingo/bingo.csv, in the shipped file's order (the order in a file is free). */
export const COLUMNS = ["id", "on", "type", "pub", "cat", "where", "pin", "weight", "from", "until",
  "text_en", "short_en", "label_en", "text_es", "short_es", "label_es", "source_url", "notes"];
/** The square types (what goes under the words: a tick circle, a write-in line, an initials box, nothing). */
export const TYPES = ["check", "name", "phone", "write", "sign", "info"];
/** The types with a write-in line, whose label_* is theirs to change. */
export const LABEL_TYPES = ["name", "phone", "write", "sign"];
/** The categories, in the builder's order: meet & connect, read & discuss, share your story, podcasts / video / app,
 *  carry the message, meetings / events / contact, history & fun facts, just for fun. */
export const CATS = ["people", "read", "write", "listen", "service", "meetings", "history", "fun"];
/** The one category an info square belongs to (the builder's "Meetings & contact squares", capped per card). */
export const INFO_CAT = "meetings";
/** The occasions a square fits ("Where are you taking it?"): home group, district meeting, area assembly, area
 *  committee meeting, workshop, our booth or table, our committee meeting, an online meeting. */
export const WHERES = ["group", "district", "assembly", "acm", "workshop", "booth", "committee", "online"];
/** The placeholders a shown cell may use: {event} is filled in the browser, the others here (fillItems). */
export const PLACEHOLDERS = ["event", "committee", "area", "email", "site", "gv_meeting", "gv_meeting_short",
  "committee_meeting", "committee_meeting_short", "gv_weekly", "gv_weekly_short", "lv_weekly", "lv_weekly_short"];
/** The lengths: id, text_*, short_* (and when a text needs one), label_*; what a placeholder counts; weight. */
export const LIMITS = Object.freeze({ id: 48, text: 90, short: 36, label: 24, placeholder: 20, weightMin: 0.5, weightMax: 5 });
/** A build-time placeholder → its `info` key (fillItems). */
export const PLACEHOLDER_INFO = {
  committee: "committee", area: "area", email: "email", site: "site", gv_meeting: "gvMeeting",
  gv_meeting_short: "gvMeetingShort", committee_meeting: "committeeMeeting", committee_meeting_short: "committeeMeetingShort",
  gv_weekly: "gvWeekly", gv_weekly_short: "gvWeeklyShort", lv_weekly: "lvWeekly", lv_weekly_short: "lvWeeklyShort",
};
// where each build-time placeholder's value comes from — the problem line of one without a value
const PLACEHOLDER_FROM = {
  committee: { en: "config/site.yml site.committee", es: "config/site.yml site.committee" },
  area: { en: "config/site.yml site.area", es: "config/site.yml site.area" },
  email: { en: "config/site.yml meeting.chair_email or site.contact_email", es: "config/site.yml meeting.chair_email o site.contact_email" },
  site: { en: "config/site.yml site.url", es: "config/site.yml site.url" },
  gv_meeting: { en: "config/site.yml recurring_events: grapevine-meeting", es: "config/site.yml recurring_events: grapevine-meeting" },
  committee_meeting: { en: "config/site.yml meeting:", es: "config/site.yml meeting:" },
  gv_weekly: { en: "data/site/weekly_open.json, the Grapevine Weekly Open", es: "data/site/weekly_open.json, la Grapevine Weekly Open" },
  lv_weekly: { en: "data/site/weekly_open.json and config/site.yml lavina_weekly_open", es: "data/site/weekly_open.json y config/site.yml lavina_weekly_open" },
};
PLACEHOLDER_FROM.gv_meeting_short = PLACEHOLDER_FROM.gv_meeting;
PLACEHOLDER_FROM.committee_meeting_short = PLACEHOLDER_FROM.committee_meeting;
PLACEHOLDER_FROM.gv_weekly_short = PLACEHOLDER_FROM.gv_weekly;
PLACEHOLDER_FROM.lv_weekly_short = PLACEHOLDER_FROM.lv_weekly;

/** The few words only the cards' meeting lines use (bingoInfo) — everything else is the settings', the site's i18n
 *  and Intl's. A monthly meeting has three lines:
 *    long   "3rd Wednesday of the month, 7 – 8 PM Central, Google Meet" / "cada tercer miércoles del mes, 7–8 p. m.
 *           (hora del Centro), por Google Meet" — the Spanish day is the site's own (committee.rule, committee.ord.*:
 *           "Cada tercer miércoles del mes", in lower case after a colon); the zone in the words the site writes it
 *           with ("Central" / "(hora del Centro)": monthly.js monthCtx, the weekly meetings' own "when"); "por" before
 *           a platform, "en" before a place
 *    mid    "3rd Wed · 7 PM · Google Meet" / "3.er mié. · 7 p. m. · Google Meet" — the short line and where (the
 *           cards' Meetings & contact strip when the long one does not fit)
 *    short  "3rd Wed · 7 PM" / "3.er miércoles · 7 p. m." — the big grids' squares ({…_short}): no place, no end,
 *           no zone
 *  and the weekly open meetings on big grids "Wed 11 AM" / "mié. 11 a. m." (then " · Zoom": no "·" between the day
 *  and the time, so the meeting's name, day, time and platform fit in 36 characters in both languages). */
export const BINGO_WORDS = {
  // (the Spanish long line says "primer", "tercer" …: committee.ord.*; these are the English ones and the short and
  // mid lines' Spanish ones)
  ord: {
    en: { 1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", "-1": "last" },
    es: { 1: "1.er", 2: "2.º", 3: "3.er", 4: "4.º", 5: "5.º", "-1": "último" },
  },
  rule: { en: "{ord} {weekday} of the month" },
  zone: { en: "{time} Central", es: "{time} (hora del Centro)" },
  platform: { en: "{where}", es: "por {where}" },
  place: { en: "{where}", es: "en {where}" },
  short: { en: "{ord} {day} · {time}", es: "{ord} {day} · {time}" },
  weekly: { en: "{day} {time}", es: "{day} {time}" },
};

/* ------------------------------------------------------------------ */
/*  Small readers (the Python twin has the same ones)                   */
/* ------------------------------------------------------------------ */
const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const W = "[\\p{L}\\p{N}_]";
// White space, spelled out (booth.js WS_CHARS): JavaScript's \s and trim() and Python's \s and strip() disagree on a
// few characters (U+FEFF, U+001C–U+001F, U+0085), and the two checkers must read every cell alike.
const WS_CHARS = " \\t\\n\\r\\f\\v\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff";
const WS = `[${WS_CHARS}]`;
const TRIM = new RegExp(`^${WS}+|${WS}+$`, "g");
const SPACES = new RegExp(`${WS}+`, "g");
const LIST_SPLIT = new RegExp(`(?:[;,]|${WS})+`);
const MARK = /\{([^{}]*)\}/g;
const ON_YES = ["yes", "y", "true", "1", "si", "sí"];
const ON_NO = ["no", "n", "false", "0"];
const PUBS = {
  gv: "gv", grapevine: "gv", lv: "lv", lavina: "lv", "laviña": "lv", both: "both", all: "both", aa: "both",
  ambos: "both", ambas: "both", gvlv: "both", "gv/lv": "both", "gv-lv": "both", "gv+lv": "both", "gv&lv": "both",
};
const LANG_NAME = { en: { en: "English", es: "inglés" }, es: { en: "Spanish", es: "español" } };
const isMap = (v) => !!v && typeof v === "object" && !Array.isArray(v);
const arr = (v) => (Array.isArray(v) ? v : []);

/** A cell as the checks read it: Unicode NFC, every run of white space one space, nothing around it. */
const oneLine = (v) => String(v ?? "").normalize("NFC").replace(SPACES, " ").replace(TRIM, "");
/** Length in characters as a person counts them (code points, so an emoji or "ñ" is one). */
const len = (s) => [...String(s)].length;
/** A cell's length as the limits count it: its characters, each {…} counting LIMITS.placeholder (its words are
 *  filled in later, and differ between builds). */
export function measure(s) {
  const v = String(s ?? "");
  let marks = 0;
  const rest = v.replace(MARK, () => { marks++; return ""; });
  return len(rest) + marks * LIMITS.placeholder;
}
/** A real calendar day written YYYY-MM-DD, in the years 2000–2099 (booth.js validDay). */
function validDay(v) {
  if (!/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(v)) return false;
  const [y, m, d] = v.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

/* ------------------------------------------------------------------ */
/*  Words a bingo card never says (besides booth.js refusedIn)          */
/* ------------------------------------------------------------------ */
// Anonymity (Traditions Eleven and Twelve): a card asks for a FIRST name, and only with the person's OK — never a
// last or full name, never a photo of a person (a selfie, a group photo, "a picture with your sponsor"). A photo of
// a thing ("a picture of the first cover", "una foto de mi libro") is not caught: the words after "photo of" /
// "foto de" (and any of a, the, your … / un, la, tu, mi …) must name a person — "él" and "mí" only with their
// accents, as "el" and "mi" are words before a thing too.
const PEOPLE_EN = `(?:someone|somebody|anyone|anybody|everyone|everybody|people|persons?|members?|friends?|sponsors?|sponsees?|newcomers?|old-?timers?|speakers?|groups?|gvrs?|rlvs?|reps?|representatives?|delegates?|dcms?|chair(?:person)?s?|trusted${WS}+servants?|committee|yourself|yourselves|you|us|them|him|her|me|each${WS}+other)`;
const DET_EN = `(?:(?:a|an|the|your|my|our|their|his|her|this|that|these|those|another|other|each|every|one|two|three|some|any|new|fellow|whole)${WS}+)*`;
const PEOPLE_ES = `(?:alguien|todos|todas|gente|personas?|miembros?|compañer[oa]s?|amig[oa]s?|padrinos?|madrinas?|ahijad[oa]s?|reci[eé]n${WS}+llegad[oa]s?|nuev[oa]s?|oradore?s?|oradoras?|grupos?|rlvs?|gvrs?|representantes?|delegad[oa]s?|mcds?|coordinador(?:a|es|as)?|servidore?s?|servidoras?|comit[eé]|ti|ustedes|nosotr[oa]s|ell[oa]s?|él|mí)`;
const DET_ES = `(?:(?:un|una|unos|unas|el|la|los|las|tu|tus|su|sus|mi|mis|nuestro|nuestra|nuestros|nuestras|otro|otra|otros|otras|alg[uú]n|alguna|algunos|algunas|cada|este|esta|estos|estas|ese|esa|todo|toda|todos|todas)${WS}+)*`;
const PHOTO_EN = "(?:photo(?:graph)?s?|pictures?|pics?|snapshots?)";
const PHOTO_ES = "(?:fotos?|fotograf[ií]as?|im[aá]gen(?:es)?)";
const PHOTOS_WHY = {
  en: "no photos of people: anonymity (first names only, no faces)",
  es: "sin fotos de personas: anonimato (solo nombres de pila, sin caras)",
};
const NAMES_WHY = {
  en: "first names only, never a last name: anonymity",
  es: "solo nombres de pila, nunca un apellido: anonimato",
};
/** Bingo's own refused words: { re, en, es } — what each catches is in the comment above; checked after refusedIn. */
export const BINGO_REFUSED = [
  { re: new RegExp(`(?<!${W})(?:selfies?|selfis?|autofotos?)(?!${W})`, "iu"), ...PHOTOS_WHY },
  { re: new RegExp(`(?<!${W})(?:${PHOTO_EN}${WS}+(?:of|with)${WS}+${DET_EN}${PEOPLE_EN}|(?:group|team)${WS}+${PHOTO_EN})(?!${W})`, "iu"), ...PHOTOS_WHY },
  { re: new RegExp(`(?<!${W})(?:${PHOTO_ES}${WS}+(?:de|del|con)${WS}+${DET_ES}${PEOPLE_ES}|fotos?${WS}+grupal(?:es)?)(?!${W})`, "iu"), ...PHOTOS_WHY },
  { re: new RegExp(`(?<!${W})(?:(?:last|full|family)${WS}*names?|surnames?)(?!${W})`, "iu"), ...NAMES_WHY },
  { re: new RegExp(`(?<!${W})(?:apellidos?|nombres?${WS}+completos?)(?!${W})`, "iu"), ...NAMES_WHY },
];
/** Every refused word in a shown cell → [{ word (as written), en, es }]: booth.js refusedIn's, then bingo's own. */
export function bingoRefusedIn(text) {
  const s = String(text ?? "");
  const out = refusedIn(s);
  for (const r of BINGO_REFUSED) {
    const m = r.re.exec(s);
    if (m) out.push({ word: m[0], en: r.en, es: r.es });
  }
  return out;
}

/* ------------------------------------------------------------------ */
/*  Checking the CSV — tests/test_bingo_csv.py is its twin              */
/* ------------------------------------------------------------------ */
/** src/_i18n/bingo.json (its data) → the categories it names: every key "bingo.cat.<cat>" (<cat>: a–z, 0–9, dashes)
 *  whose English and Spanish are both filled in, in the file's order. */
export function catNamesOf(json) {
  if (!isMap(json)) return [];
  const out = [];
  for (const [k, v] of Object.entries(json)) {
    const m = /^bingo\.cat\.([a-z0-9]+(?:-[a-z0-9]+)*)$/.exec(k);
    if (m && isMap(v) && oneLine(v.en) && oneLine(v.es) && !out.includes(m[1])) out.push(m[1]);
  }
  return out;
}

const list = (a) => a.join(", ");
const listEs = (a) => (a.length > 1 ? `${a.slice(0, -1).join(", ")} y ${a[a.length - 1]}` : a.join(""));
const listEn = (a) => (a.length > 1 ? `${a.slice(0, -1).join(", ")} and ${a[a.length - 1]}` : a.join(""));

/**
 * content/bingo/bingo.csv (its text) → { items, problems, rows, rowOf }: the squares the cards can use, in file order
 * (the shape is in the header comment), a problem line for each mistake — { where: "bingo.csv row 14
 * (people-gvr-today)", en, es } —, the number of rows after the header, and each item's row ({ id: row number }:
 * fillItems names it).
 *   opts.file      the name the lines give the file ("bingo.csv")
 *   opts.catNames  the categories src/_i18n/bingo.json names (catNamesOf): a cat outside CATS is accepted when it
 *                  is one of them (loadBingo reads the file; without it only CATS)
 */
export function checkBingoCsv(text, opts = {}) {
  const file = opts.file || "bingo.csv";
  const catNames = arr(opts.catNames);
  const items = [];
  const problems = [];
  const rowOf = {};
  const add = (where, en, es) => problems.push({ where, en, es });
  const raw = String(text ?? "");
  if (raw.includes("�")) {
    add(file, "the file is not saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)",
      "el archivo no está guardado como UTF-8: letras como ñ y é pueden salir mal (Excel: Guardar como → CSV UTF-8)");
  }
  const { rows, unclosed } = parseCsv(raw);
  if (unclosed) {
    add(`${file} row ${unclosed}`, "a cell starts with a double quote (\") that is never closed: everything after it was read as that one cell",
      "una celda empieza con comillas dobles (\") que nunca se cierran: todo lo que sigue se leyó como esa celda");
  }
  const header = rows[0] || [];
  if (!header.some((c) => oneLine(c))) {
    add(file, "the file is empty: the first row must be the header (id,on,type,…)",
      "el archivo está vacío: la primera fila debe ser el encabezado (id,on,type,…)");
    return { items, problems, rows: 0, rowOf };
  }
  // the header: names in any order and capitalization; an unknown column is ignored, a known one twice → the first
  const col = Object.create(null);
  const twice = new Set();
  header.forEach((h, i) => {
    const k = oneLine(h).toLowerCase();
    if (!k) return;
    if (!(k in col)) col[k] = i;
    else if (COLUMNS.includes(k) && !twice.has(k)) {
      twice.add(k);
      add(`${file} header`, `column ${k} is in the header twice: the first one is used`,
        `la columna ${k} está dos veces en el encabezado: se usa la primera`);
    }
  });
  const needed = ["id", "type", "cat"];
  for (const need of needed) {
    if (!(need in col)) add(`${file} header`, `the header (first row) has no ${need} column`, `el encabezado (primera fila) no tiene la columna ${need}`);
  }
  if (needed.some((k) => !(k in col))) return { items, problems, rows: rows.length - 1, rowOf };

  const seen = new Map(); // id → the row it was first used in
  const texts = { en: new Map(), es: new Map() }; // a shown text (lower case) → { row, id } of the first row with it
  const shorts = { en: new Map(), es: new Map() }; // big-grid words (lower case) → { row, id, cell } of the first row
  for (let r = 1; r < rows.length; r++) {
    const cells = rows[r];
    const rowNo = r + 1;
    if (!cells.some((c) => oneLine(c))) continue; // a blank row
    const get = (k) => (k in col ? cells[col[k]] ?? "" : "");
    const idRaw = oneLine(get("id"));
    if (idRaw.startsWith("#")) continue; // a comment
    const where = `${file} row ${rowNo}${idRaw ? ` (${[...idRaw].slice(0, LIMITS.id).join("")})` : ""}`;
    const errs = [];
    const err = (en, es) => errs.push([en, es]);
    const flush = () => errs.forEach(([en, es]) => add(where, en, es));

    // more cells than the header has: a comma in a text that is not in quotes moved every cell after it
    if (cells.length > header.length && cells.slice(header.length).some((c) => oneLine(c))) {
      err(`the row has ${cells.length} cells but the header has ${header.length}: a comma inside a text needs the whole cell in double quotes`,
        `la fila tiene ${cells.length} celdas pero el encabezado tiene ${header.length}: una coma dentro de un texto necesita la celda entera entre comillas dobles`);
      flush();
      continue;
    }

    // id, on, type, pub, cat, where, pin, weight, dates, source_url
    let id = "";
    if (!idRaw) err("id is empty", "falta el id");
    else if (!ID.test(idRaw) || len(idRaw) > LIMITS.id) {
      err(`id "${idRaw}": use only a–z, 0–9 and dashes (no spaces or capitals), at most ${LIMITS.id} characters`,
        `id "${idRaw}": usa solo a–z, 0–9 y guiones (sin espacios ni mayúsculas), ${LIMITS.id} caracteres como máximo`);
    } else if (seen.has(idRaw)) {
      err(`id "${idRaw}" is already used in row ${seen.get(idRaw)}`, `el id "${idRaw}" ya se usa en la fila ${seen.get(idRaw)}`);
    } else {
      id = idRaw;
      seen.set(id, rowNo);
    }
    const yesNo = (k) => {
      const v = oneLine(get(k));
      const lc = v.toLowerCase();
      if (!v) return null;
      if (ON_YES.includes(lc)) return true;
      if (ON_NO.includes(lc)) return false;
      err(`${k} "${v}": write yes or no`, `${k} "${v}": escribe yes o no`);
      return null;
    };
    const on = yesNo("on") ?? true;
    const typeRaw = oneLine(get("type"));
    const type = typeRaw.toLowerCase();
    const typeOk = TYPES.includes(type);
    if (!typeRaw) err(`type is empty (${list(TYPES)})`, `falta type (${list(TYPES)})`);
    else if (!typeOk) err(`type "${typeRaw}" is not one of: ${list(TYPES)}`, `type "${typeRaw}" no es uno de: ${list(TYPES)}`);
    const pubRaw = oneLine(get("pub"));
    const pubKey = pubRaw.toLowerCase().replace(SPACES, "");
    const pub = !pubRaw ? "both" : Object.hasOwn(PUBS, pubKey) ? PUBS[pubKey] : null;
    if (!pub) err(`pub "${pubRaw}": write gv, lv or both`, `pub "${pubRaw}": escribe gv, lv o both`);
    const catRaw = oneLine(get("cat"));
    const cat = catRaw.toLowerCase();
    const catOk = CATS.includes(cat) || catNames.includes(cat);
    if (!catRaw) err(`cat is empty (${list(CATS)})`, `falta cat (${list(CATS)})`);
    else if (!catOk) {
      err(`cat "${catRaw}" is not one of: ${list(CATS)} — a new category also needs its name in src/_i18n/bingo.json ("bingo.cat.${cat}", in English and Spanish)`,
        `cat "${catRaw}" no es uno de: ${list(CATS)}; una categoría nueva necesita también su nombre en src/_i18n/bingo.json ("bingo.cat.${cat}", en inglés y en español)`);
    }
    if (typeOk && type === "info" && catOk && cat !== INFO_CAT) {
      err(`type info is only for cat ${INFO_CAT} rows (an information square: our meetings, events and contact)`,
        `type info es solo para filas de cat ${INFO_CAT} (una casilla informativa: nuestras reuniones, eventos y contacto)`);
    }
    const wheres = [];
    for (const w of oneLine(get("where")).toLowerCase().split(LIST_SPLIT).filter(Boolean)) {
      if (!WHERES.includes(w)) err(`where: "${w}" is not one of: ${list(WHERES)}`, `where: "${w}" no es uno de: ${list(WHERES)}`);
      else if (!wheres.includes(w)) wheres.push(w);
    }
    const pin = yesNo("pin") ?? false;
    const wRaw = oneLine(get("weight"));
    let weight = 1;
    if (wRaw) {
      const n = /^[0-9]{1,3}(?:[.,][0-9]{1,3})?$/.test(wRaw) ? Number(wRaw.replace(",", ".")) : NaN;
      if (n >= LIMITS.weightMin && n <= LIMITS.weightMax) weight = n;
      else err(`weight "${wRaw}": a number from 0.5 to 5`, `weight "${wRaw}": un número de 0.5 a 5`);
    }
    const dates = { from: null, until: null };
    for (const k of ["from", "until"]) {
      const v = oneLine(get(k));
      if (!v) continue;
      if (validDay(v)) dates[k] = v;
      else {
        err(`${k} "${v}": a date written YYYY-MM-DD, year 2000–2099 (Excel may have changed it: format the column as Text)`,
          `${k} "${v}": una fecha escrita AAAA-MM-DD, año 2000–2099 (Excel pudo cambiarla: da a la columna el formato Texto)`);
      }
    }
    if (dates.from && dates.until && dates.until < dates.from) {
      err(`until (${dates.until}) is before from (${dates.from})`, `until (${dates.until}) es anterior a from (${dates.from})`);
    }
    const srcRaw = oneLine(get("source_url"));
    if (srcRaw && !splitUrl(srcRaw)) err(`source_url "${srcRaw}": not an https:// link`, `source_url "${srcRaw}": no es un enlace https://`);

    // the two languages: what each one has, what a shown language needs, the lengths, the placeholders and words
    const L = {};
    for (const lang of LANGS) L[lang] = { text: oneLine(get(`text_${lang}`)), short: oneLine(get(`short_${lang}`)), label: oneLine(get(`label_${lang}`)) };
    const langs = [];
    let partial = false; // a language with short / label but no text (named: no "no text at all" line on top)
    for (const lang of LANGS) {
      const v = L[lang];
      if (v.label && typeOk && !LABEL_TYPES.includes(type)) {
        err(`label_${lang} is only for ${listEn(LABEL_TYPES)} rows`, `label_${lang} es solo para filas ${listEs(LABEL_TYPES)}`);
      }
      if (!v.text) {
        const others = ["short", "label"].filter((f) => v[f]).map((f) => `${f}_${lang}`);
        if (others.length) {
          partial = true;
          err(`text_${lang} is empty, but other ${LANG_NAME[lang].en} cells are filled (${list(others)}): fill it in, or empty them`,
            `text_${lang} está vacío, pero hay otras celdas en ${LANG_NAME[lang].es} con texto (${list(others)}): complétalo o vacíalas`);
        }
        continue;
      }
      langs.push(lang);
      const tooLong = (f, max) => {
        const n = measure(v[f]);
        if (!v[f] || n <= max) return;
        const marks = /\{[^{}]*\}/.test(v[f]);
        err(`${f}_${lang}: ${n} characters (${max} at most${marks ? `; each {…} counts as ${LIMITS.placeholder}` : ""})`,
          `${f}_${lang}: ${n} caracteres (${max} como máximo${marks ? `; cada {…} cuenta como ${LIMITS.placeholder}` : ""})`);
      };
      tooLong("text", LIMITS.text);
      tooLong("short", LIMITS.short);
      tooLong("label", LIMITS.label);
      const n = measure(v.text);
      if (n > LIMITS.short && !v.short) {
        err(`short_${lang} is empty, but text_${lang} has ${n} characters (more than ${LIMITS.short}): write the words for big grids (7×7 and up)`,
          `short_${lang} está vacío, pero text_${lang} tiene ${n} caracteres (más de ${LIMITS.short}): escribe las palabras para cuadrículas grandes (7×7 o más)`);
      }
    }
    if (!langs.length && !partial) {
      err("the row has no text in English or Spanish: fill in text_en, text_es or both",
        "la fila no tiene texto en inglés ni en español: completa text_en, text_es o los dos");
    }
    for (const lang of LANGS) {
      for (const f of ["text", "short", "label"]) {
        const v = L[lang][f];
        if (!v || !L[lang].text) continue;
        const name = `${f}_${lang}`;
        const marks = [];
        for (const m of v.matchAll(MARK)) if (!PLACEHOLDERS.includes(m[1]) && !marks.includes(m[1])) marks.push(m[1]);
        for (const mk of marks) {
          err(`${name}: {${mk}} is not a placeholder bingo knows (${PLACEHOLDERS.map((p) => `{${p}}`).join(", ")})`,
            `${name}: {${mk}} no es un marcador que el bingo conozca (${PLACEHOLDERS.map((p) => `{${p}}`).join(", ")})`);
        }
        for (const hit of bingoRefusedIn(v)) {
          err(`${name}: “${hit.word}” is not used on bingo cards — ${hit.en}`, `${name}: “${hit.word}” no se usa en las tarjetas de bingo: ${hit.es}`);
        }
      }
    }
    // two rows that are on with the same text: a card could show the same square twice (the first one keeps it); then
    // the same for the big grids' words — short_*, else the text itself: what a 7×7 and up (or a card with small
    // squares) prints, every square in them —, checked only when the texts differ (one line for one mistake)
    if (!errs.length && on) {
      for (const lang of langs) {
        const first = texts[lang].get(L[lang].text.toLowerCase());
        if (first) {
          err(`text_${lang} is the same as in row ${first.row} (${first.id}): a card could show the same square twice`,
            `text_${lang} es el mismo que en la fila ${first.row} (${first.id}): una tarjeta podría mostrar la misma casilla dos veces`);
        }
      }
      // (a row's big-grid words, and the cell they come from: "short_en", or "text_en" when short_en is blank)
      const big = (lang) => ({ key: (L[lang].short || L[lang].text).toLowerCase(), cell: `${L[lang].short ? "short" : "text"}_${lang}` });
      if (!errs.length) {
        for (const lang of langs) {
          const { key, cell } = big(lang);
          const first = shorts[lang].get(key);
          if (first) {
            const there = first.cell === cell ? "" : `${first.cell} `;
            err(`${cell} is the same as ${there}in row ${first.row} (${first.id}): a big card could show the same words twice`,
              `${cell} es el mismo que ${there}en la fila ${first.row} (${first.id}): una tarjeta grande podría mostrar las mismas palabras dos veces`);
          }
        }
      }
      if (!errs.length) {
        for (const lang of langs) {
          texts[lang].set(L[lang].text.toLowerCase(), { row: rowNo, id });
          shorts[lang].set(big(lang).key, { row: rowNo, id, cell: big(lang).cell });
        }
      }
    }

    if (errs.length) {
      flush();
      continue;
    }
    if (!on) continue;
    const pickL = (f) => ({ en: langs.includes("en") ? f(L.en) : "", es: langs.includes("es") ? f(L.es) : "" });
    items.push({
      id, type, pub, cat, where: wheres, pin, weight, from: dates.from, until: dates.until,
      text: pickL((v) => v.text), short: pickL((v) => v.short || v.text), label: pickL((v) => v.label),
    });
    rowOf[id] = rowNo;
  }
  return { items, problems, rows: rows.length - 1, rowOf };
}

/* ------------------------------------------------------------------ */
/*  The facts the cards print (SPEC §2 `info`)                          */
/* ------------------------------------------------------------------ */
const WD = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };
const fill = (s, vars) => String(s).replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m));
const both = (en, es) => ({ en: en || es || "", es: es || en || "" });
const lowerFirst = (s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s);

/** A weekday (0 = Sunday) in a language: "Wednesday" / "Wed" (en), "miércoles" (es, lower case mid-sentence; its
 *  short form is the whole word too: a monthly meeting's big-grid words have room for it — "1.er miércoles · 7 p. m."). */
function weekdayWord(d, lang, short = false) {
  const opts = { weekday: lang === "en" && short ? "short" : "long", timeZone: "UTC" };
  const s = new Intl.DateTimeFormat(LOCALES[lang], opts).format(new Date(Date.UTC(2023, 0, 1 + d, 12)));
  return lang === "es" ? s.toLowerCase() : s;
}
/** A weekday's short form in both languages: "Wed" (en), "mié." (es: Intl's, with the period Spanish writes after an
 *  abbreviation) — only for the lines that name the platform too, which takes the room: the weekly open meetings'
 *  big-grid words and a monthly meeting's mid line. */
function weekdayAbbr(d, lang) {
  const s = new Intl.DateTimeFormat(LOCALES[lang], { weekday: "short", timeZone: "UTC" }).format(new Date(Date.UTC(2023, 0, 1 + d, 12)));
  return lang === "es" ? s.toLowerCase().replace(/([^.])$/, "$1.") : s;
}

/** "HH:MM" → [h, mi] (monthlyRule wrote it). */
const hm = (v) => String(v).split(":").map(Number);

/** An hour and its AM / PM joined by a space no line breaks at ("7" / "PM" on two lines is no time): a narrow one in
 *  English, as Intl writes a range's ("7 – 8 PM"; its "7 PM" alone has a plain space), esMeridiem's in Spanish. */
const clockJoin = (s, lang) =>
  lang === "es" ? esMeridiem(s) : String(s).replace(/(\d)[ \u00a0\u2009\u202f]+(?=[AP]M\b)/g, "$1\u202f");

/** A meeting's clock times on Central's wall clock, the way the site writes them (Intl, as cmTimeRange — whole hours
 *  without ":00"): "7 – 8 PM" / "7–8 p. m."; an overnight one "10 PM – 1 AM"; `startOnly`: "7 PM" / "7 p. m." —
 *  each hour and its AM / PM kept on one line (clockJoin). */
function clockText(start, end, lang, startOnly = false) {
  const [sh, sm] = hm(start);
  const [eh, em] = end ? hm(end) : [sh, sm];
  const night = !!end && overnight(start, end);
  // (a winter Wednesday: the wall clock is the same on every day of the year)
  const a = zoneInstant(2026, 0, 21, sh, sm, TZ);
  const b = zoneInstant(2026, 0, night ? 22 : 21, eh, em, TZ);
  const o = { hour: "numeric", timeZone: TZ };
  if (sm || (!startOnly && em)) o.minute = "2-digit";
  try {
    const f = new Intl.DateTimeFormat(LOCALES[lang], o);
    let s;
    if (startOnly || !(b > a)) s = f.format(a);
    else if (night || typeof f.formatRange !== "function") s = `${f.format(a)} – ${f.format(b)}`;
    else s = f.formatRange(a, b);
    return clockJoin(s, lang);
  } catch {
    return "";
  }
}

/**
 * A monthly meeting's lines for the cards (BINGO_WORDS says what each one looks like) — r: a monthlyRule-read entry
 * (week_of_month, weekday, start, end: the end as used, one hour after the start when it is missing); where: its
 * platform ("Google Meet") or, `place`, its place; "" for none → { long, mid, short: { en, es } }, or null when the
 * rule cannot be read (no day of the week, no week of the month, no start).
 */
function meetingLines(r, where, place = false) {
  if (!isMap(r)) return null;
  const n = Number(r.week_of_month);
  const wd = WD[String(r.weekday || "").toLowerCase()];
  if (![1, 2, 3, 4, 5, -1].includes(n) || wd === undefined || !/^\d{2}:\d{2}$/.test(String(r.start || ""))) return null;
  const out = { long: {}, mid: {}, short: {} };
  for (const lang of LANGS) {
    const ord = BINGO_WORDS.ord[lang][String(n)];
    const weekday = weekdayWord(wd, lang);
    const day = lang === "es"
      ? lowerFirst(translateKey("committee.rule", lang, { ord: translateKey(`committee.ord.${n === -1 ? "last" : n}`, lang), weekday }))
      : fill(BINGO_WORDS.rule[lang], { ord, weekday });
    const time = clockText(r.start, r.end, lang);
    const at = where ? fill(BINGO_WORDS[place ? "place" : "platform"][lang], { where }) : "";
    out.long[lang] = [day, time && fill(BINGO_WORDS.zone[lang], { time }), at].filter(Boolean).join(", ");
    const start = clockText(r.start, r.end, lang, true);
    out.short[lang] = fill(BINGO_WORDS.short[lang], { ord, day: weekdayWord(wd, lang, true), time: start });
    out.mid[lang] = [fill(BINGO_WORDS.short[lang], { ord, day: weekdayAbbr(wd, lang), time: start }), where].filter(Boolean).join(" · ");
  }
  return out;
}

/**
 * A weekly open meeting's lines for the cards (lv: La Viña's, else AA Grapevine's) → { long: { en, es }, short:
 * { en, es } | null }, or null when the data has no such meeting —
 *   long   "Wednesdays at 11:00 AM Central, Zoom" / "los miércoles a las 11:00 a. m. (hora del Centro), por Zoom":
 *          the data's own "when" (committee.js weeklyOpen) and its platform (BINGO_WORDS.platform)
 *   short  for big grids, "Wed 11 AM · Zoom" / "mié. 11 a. m. · Zoom": the day and the start time of its next meeting
 *          (weeklyOpen's next: the data's next_start, rolled forward a week at a time) on Central's clock — so Noon
 *          Eastern is 11 AM, as the long line says —, the time written as clockText writes {gv_meeting_short}'s,
 *          and the platform; null when the data has no next start
 */
function weeklyLines(items, lv) {
  const long = {};
  let short = {};
  for (const lang of LANGS) {
    const w = weeklyOpenAll(items, lang).find((x) => !!x.isLv === lv);
    if (!w || !w.when) return null;
    const platform = platformOf(w.zoomUrl) || (w.zoomId ? "Zoom" : "");
    const when = clockJoin(lang === "es" ? lowerFirst(w.when) : w.when, lang);
    long[lang] = [when, platform && fill(BINGO_WORDS.platform[lang], { where: platform })].filter(Boolean).join(", ");
    const p = w.next ? zoneParts(Date.parse(w.next.iso), TZ) : null;
    if (!p || !short) {
      short = null;
      continue;
    }
    const day = weekdayAbbr(new Date(Date.UTC(p.y, p.mo, p.d)).getUTCDay(), lang);
    const time = clockText(`${String(p.h).padStart(2, "0")}:${String(p.mi).padStart(2, "0")}`, null, lang, true);
    short[lang] = [fill(BINGO_WORDS.weekly[lang], { day, time }), platform].filter(Boolean).join(" · ");
  }
  return { long, short };
}

/**
 * The facts the cards print, in both languages (SPEC §2 `info`; the {…} placeholders' values) →
 *   { committee: { en, es }, area: { en, es }, email, site (the address without https://: "grapevine.neta65.org"),
 *     home: { en, es } (the absolute home addresses: the cards' QR codes), gvr: { en, es } (the absolute /gvr/ ones),
 *     gvMeeting, gvMeetingMid, gvMeetingShort, committeeMeeting, committeeMeetingMid, committeeMeetingShort (a
 *     monthly meeting's long, mid and short lines: BINGO_WORDS; the mid ones have no placeholder — the cards'
 *     Meetings & contact strip prints them when the long ones do not fit), gvWeekly, gvWeeklyShort, lvWeekly,
 *     lvWeeklyShort: { en, es } | null }
 *   site    the `site` global (src/_data/site.js: config/site.yml, its url from SITE_URL on GitHub)
 *   weekly  data/site/weekly_open.json (its data, or its items)
 * A name the settings write in one language only is that one in both; a meeting the settings do not have (or that is
 * switched off, or whose rule cannot be read) is null — its placeholders then have no value (fillItems).
 */
export function bingoInfo(site = {}, weekly = null) {
  const s = isMap(site) ? site : {};
  const m = isMap(s.meeting) ? s.meeting : {};
  const base = String(s.url || "").replace(/\/+$/, "");
  const abs = (p) => (base ? siteUrl(p, { url: base }) : "");
  const committee = both(oneLine(s.committee), oneLine(s.committee_es));
  if (!committee.en) for (const lang of LANGS) committee[lang] = translateKey("committee.name", lang);
  // our Grapevine Meeting: recurring_events key grapevine-meeting (read as the series is: monthlyRule forgiving)
  const raw = s.recurring_events;
  const entries = Array.isArray(raw) ? raw : isMap(raw) ? [raw] : [];
  const gv = entries.map((e) => (isMap(e) && e.enabled !== false ? monthlyRule(e, true) : null)).find((e) => e && e.key === "grapevine-meeting");
  const gvPlatform = gv ? platformOf(gv.online_url) : null;
  const gvLines = gv ? meetingLines(gv, gvPlatform || oneLine(gv.location).split(",")[0], !gvPlatform) : null;
  // the committee meeting: config/site.yml meeting: — with src/_data/meeting.js's defaults for what it leaves out (the
  // 3rd Wednesday at 7 PM, an hour long); no `meeting:` section at all ({}): none
  const given = Object.fromEntries(Object.entries(m).filter(([, v]) => v !== undefined && v !== null && v !== ""));
  const cmLines = Object.keys(m).length
    ? meetingLines(monthlyRule({ week_of_month: 3, weekday: "wednesday", start: "19:00", ...given }), oneLine(m.platform) || "Zoom")
    : null;
  const items = Array.isArray(weekly) ? weekly : isMap(weekly) ? arr(weekly.items) : [];
  const lvOn = !(isMap(s.lavina_weekly_open) && s.lavina_weekly_open.enabled === false);
  const gvWeekly = weeklyLines(items, false);
  const lvWeekly = lvOn ? weeklyLines(items, true) : null;
  return {
    committee,
    area: both(oneLine(s.area), oneLine(s.area_es)),
    email: oneLine(m.chair_email) || oneLine(s.contact_email),
    site: base.replace(/^https?:\/\//i, "").replace(/^www\./i, ""),
    home: { en: abs("/"), es: abs("/es/") },
    gvr: { en: abs("/gvr/"), es: abs("/es/gvr/") },
    gvMeeting: gvLines ? gvLines.long : null,
    gvMeetingMid: gvLines ? gvLines.mid : null,
    gvMeetingShort: gvLines ? gvLines.short : null,
    committeeMeeting: cmLines ? cmLines.long : null,
    committeeMeetingMid: cmLines ? cmLines.mid : null,
    committeeMeetingShort: cmLines ? cmLines.short : null,
    gvWeekly: gvWeekly ? gvWeekly.long : null,
    gvWeeklyShort: gvWeekly ? gvWeekly.short : null,
    lvWeekly: lvWeekly ? lvWeekly.long : null,
    lvWeeklyShort: lvWeekly ? lvWeekly.short : null,
  };
}

/** A build-time placeholder's value in a language ("" when the settings have none). */
function placeholderValue(info, key, lang) {
  const v = isMap(info) ? info[PLACEHOLDER_INFO[key]] : null;
  return typeof v === "string" ? v : isMap(v) ? String(v[lang] || "") : "";
}

/**
 * The checked items with every build-time placeholder filled in from `info` (bingoInfo), each language with its own
 * words; {event} stays for the browser → { items, problems }. A row whose placeholder has no value in this build (a
 * meeting the settings no longer have, no site address …) is left out, with one line per placeholder:
 * "{gv_meeting} has no value in this build (config/site.yml recurring_events: grapevine-meeting): the square is left out".
 *   opts.file   the name the lines give the file ("bingo.csv")
 *   opts.rowOf  { id: row number } (checkBingoCsv's): the lines' "row N"
 */
export function fillItems(items, info, opts = {}) {
  const file = opts.file || "bingo.csv";
  const rowOf = isMap(opts.rowOf) ? opts.rowOf : {};
  const out = [];
  const problems = [];
  for (const it of arr(items)) {
    const missing = [];
    const done = { text: {}, short: {}, label: {} };
    for (const f of ["text", "short", "label"]) {
      for (const lang of LANGS) {
        done[f][lang] = String((it[f] && it[f][lang]) || "").replace(MARK, (mk, k) => {
          if (k === "event" || !Object.hasOwn(PLACEHOLDER_INFO, k)) return mk;
          const v = placeholderValue(info, k, lang);
          if (!v && !missing.some((x) => x.k === k)) missing.push({ k, cell: `${f}_${lang}` });
          return v || mk;
        });
      }
    }
    if (missing.length) {
      const where = `${file}${rowOf[it.id] ? ` row ${rowOf[it.id]}` : ""} (${it.id})`;
      for (const { k, cell } of missing) {
        problems.push({
          where,
          en: `${cell}: {${k}} has no value in this build (${PLACEHOLDER_FROM[k].en}): the square is left out`,
          es: `${cell}: {${k}} no tiene valor en esta compilación (${PLACEHOLDER_FROM[k].es}): la casilla queda fuera`,
        });
      }
      continue;
    }
    out.push({ ...it, where: [...arr(it.where)], ...done });
  }
  return { items: out, problems };
}

/* ------------------------------------------------------------------ */
/*  Loading the owner's file (the `bingo` global)                       */
/* ------------------------------------------------------------------ */
// The repository: Eleventy and the tests run from its root.
const ROOT = process.cwd();
const readText = (p) => {
  try {
    return fs.readFileSync(path.resolve(ROOT, p), "utf8");
  } catch {
    return null;
  }
};
const readJson = (p) => {
  const s = readText(p);
  if (s === null) return null;
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
};

/**
 * The `bingo` global (src/_data/bingo.js; SPEC §2 data contract):
 *   opts.csv / opts.csvText   the CSV's path (content/bingo/bingo.csv) or its text
 *   opts.site                 the `site` global (src/_data/site.js)
 *   opts.weekly               data/site/weekly_open.json — its path (the default) or its data
 *   opts.i18n / opts.catNames src/_i18n/bingo.json's path (the default) or the categories it names (catNamesOf)
 * → { file (the CSV's path), found, rows, items (checked, on, placeholders filled but {event}), problems (the CSV's,
 *     then fillItems'), cats (CATS, then any other category a shown square uses, in file order), wheres (WHERES),
 *     info (bingoInfo) }. Problems never stop the build.
 */
export function loadBingo(opts = {}) {
  const csvFile = opts.csv || "content/bingo/bingo.csv";
  const file = path.basename(csvFile);
  const csvText = typeof opts.csvText === "string" ? opts.csvText : readText(csvFile);
  const weekly = typeof opts.weekly === "string" || opts.weekly === undefined ? readJson(opts.weekly || "data/site/weekly_open.json") : opts.weekly;
  const catNames = Array.isArray(opts.catNames) ? opts.catNames : catNamesOf(readJson(opts.i18n || "src/_i18n/bingo.json"));
  const info = bingoInfo(opts.site, weekly);
  if (csvText === null) {
    return {
      file: csvFile, found: false, rows: 0, items: [], cats: [...CATS], wheres: [...WHERES], info,
      problems: [{ where: file, en: `${csvFile} was not found: the cards have no squares`, es: `no se encontró ${csvFile}: las tarjetas no tienen casillas` }],
    };
  }
  const checked = checkBingoCsv(csvText, { file, catNames });
  const filled = fillItems(checked.items, info, { file, rowOf: checked.rowOf });
  const cats = [...CATS];
  for (const it of filled.items) if (!cats.includes(it.cat)) cats.push(it.cat);
  return {
    file: csvFile, found: true, rows: checked.rows, items: filled.items, problems: [...checked.problems, ...filled.problems],
    cats, wheres: [...WHERES], info,
  };
}

/** The build log's `[bingo]` lines for problems ([{ where, en, es }]): "[bingo] 2 problem(s) — left out:", then one
 *  "where: what" line each, in English — the first 40. Nothing when there are none. A plain console.warn, never a
 *  build warning (eleventy/build-warnings.js): a STRICT_BUILD never fails on them — the Code check stops on the real
 *  CSV's instead (tests/test_bingo_csv.py Real), so the committee hears of a mistake before a GVR prints a card. */
export function logBingoProblems(problems) {
  const all = arr(problems);
  if (!all.length) return;
  const lines = all.slice(0, 40).map((p) => `${p.where}: ${p.en}`);
  if (all.length > 40) lines.push(`… and ${all.length - 40} more (python tests/test_bingo_csv.py content/bingo/bingo.csv lists them all)`);
  console.warn(`[bingo] ${all.length} problem(s) — left out:\n  ${lines.join("\n  ")}`);
}

// The plugin eleventy.config.js loads from every eleventy/filters/*.js: the bingo has no filter of its own here (the
// pages' bingoSample is eleventy/filters/bingo-sample.js's); the default export must still be there.
export default function () {}
