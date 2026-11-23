// Library (all PDFs & documents) + site-wide Search — Eleventy filters.
//
// Auto-loaded by eleventy.config.js. Everything here runs at BUILD time:
//   * libDocs(db, lang)        → normalized, newest-first list of every library
//                                 document (crawled PDFs + committee Drive docs)
//   * libFacets(docs, lang)    → facet values + counts (source, language, type, year)
//   * libCollections(docs,lang)→ quick "collections" (GVR kit, RLV kit, catalogs …)
//   * libStats(docs)           → hero counters
//   * libIndexJson(db, lang)   → compact JSON for /library-index.json (client search)
//   * searchIndexJson(db, nav, lang, site, presentations) → compact JSON for /search-index.json
//                                 (story entries carry the writer + hometown, `a`; the
//                                 Published Writers page lists the Texas writers' names/cities;
//                                 since round 37 every event's own page, the series' pages, the
//                                 month toolkits, the presentations, the current issues, the
//                                 flyers, the shop's offers and the long pages' sections too —
//                                 searchIndex below)
//   * searchSpotlightTile(view, db) → the "Published Writers" browse tile on /search/: the
//                                 count of the view it links to (normally the /published/
//                                 default: Area 65 writers, first list_days window), + ?query
//   * libNum(n, lang)          → 3,100 (same locales as the rest of the site: en-US / es-US)
//   * jsonScript               → JSON safe to embed inside <script type="application/json">
//
// How crawled PDFs are described (scripts/sync/crawl.py + crawl_rules.py):
//   category = "gvr" / "rlv" when the PDF is on the official GVR / RLV resource page
//              (the rep "kits"), else the document type (postcard, order-form, news …);
//   tags     = for kit PDFs, the document type as well (["postcard"]);
//   lang     = language of the TITLE;  extra.doc_lang = language of the DOCUMENT;
//              (a document keeps both: `l` = document language, `tl` = title language,
//              so an untranslated title gets the right lang="" for screen readers);
//   date     = upload month ("2026-02-01", day unknown) or the exact day; may be null;
//   extra.orphan = no page links to the file any more (kept, but de-emphasized here);
//   extra.versions = the language editions of ONE document (scripts/sync/pdf_curate.py merges an
//              English and a Spanish/French edition into one entry): each page shows the edition in
//              its own language (else the entry's), with links to every edition (`vs`), and the
//              language facet counts every edition's language (`ls`). extra.kits = every rep kit
//              (gvr / rlv) the document is in, when that is more than its own category says.
//
// Dev/test switch: LIB_EMPTY=1 npx @11ty/eleventy …  builds the library and the
// search index as if no content had been synced yet (to check empty states).
import { openSync, readSync, closeSync, readFileSync } from "node:fs";
import path from "node:path";
import { scriptJson } from "../script-json.js";
import { TZ } from "../../eleventy.config.js"; // the site's time zone (config/site.yml site.timezone)
import { eventTone } from "./event-tone.js"; // the colour rule: a booth's search words (booth, literature table)
import { issueName, groupIssues, issueView, localizeIssueLabel } from "./read.js"; // La Viña's issue as every page names it ("May–June 2027"); /read/'s current issues
import { meetingTitleParts } from "./media.js"; // a weekly open meeting episode's own title (its meeting and date)
import { windowKeys, monthModel, monthLabel, nowDate } from "./monthly.js"; // the month toolkits (/monthly/<YYYY-MM>/)
import { shopBotm, shopSpecialty, shopOffers, shopPriceChanges } from "./shop.js"; // /shop/'s offers, as the page shows them
import { pwArchiveItems } from "./published.js"; // the Texas writers archive (/published/#archive), as the page lists it
import orientationData from "../../src/_data/orientation.js"; // GVR / RLV 101 lessons (config/orientation.yml)
import historyData from "../../src/_data/history.js"; // the history's milestones (config/history.yml): /about/'s section shows with them
import siteLanguages from "../../src/_data/languages.js"; // the site's languages (the event pages' plan pairs them)
import { SEARCH_SECTIONS } from "../search-sections.js"; // the long pages' sections the search finds on their own (round 37)

const EMPTY = () => !!process.env.LIB_EMPTY;
// Only real web links (or site-relative paths) ever reach an href/src.
const SAFE_URL = /^(https?:\/\/|\/(?!\/))/i;
const DAY = 864e5;
const LOCALES = { en: "en-US", es: "es-US" }; // same as eleventy.config.js / app.js
const OFFICIAL_HOST = /(^|\.)(aagrapevine|aalavina)\.org$/i;
// A two-letter language code ("und" and junk → "").
const okLang = (v) => (typeof v === "string" && /^[a-z]{2}$/.test(v) ? v : "");
// First pages taller than this (height ÷ width) are shown whole instead of top-cropped:
// Letter (1.29) and A4 (1.41) covers crop well at the top (masthead + headline); booklets,
// posters and legal-size pages (1.55+) often center their title, so a top crop is a flat band.
const TALL_PAGE = 1.45;

/* ------------------------------------------------------------------ */
/*  Vocabulary                                                          */
/* ------------------------------------------------------------------ */

// Document types in display order + icon. Unknown types (e.g. a new Drive
// folder name) are listed alphabetically before "other" with a generic icon
// and a prettified label. "rep" is the type of kit PDFs the crawler could not
// sub-classify ("Rep resources"); the kits themselves are collections.
export const CATEGORIES = [
  ["news", "newspaper"], ["catalog", "book-open"], ["postcard", "mail"], ["flyer", "megaphone"],
  ["order-form", "clipboard-list"], ["guidelines", "list-checks"], ["workbook", "notebook-pen"],
  ["service", "hand-heart"], ["literature", "book-marked"], ["rep", "badge-check"],
  ["reports", "file-chart-column"], ["notes", "notepad-text"], ["slides", "presentation"],
  ["workshops", "graduation-cap"], ["forms", "file-pen-line"], ["other", "file-text"],
];
const CAT_ICON = Object.fromEntries(CATEGORIES);
const CAT_ORDER = { ...Object.fromEntries(CATEGORIES.map(([k], i) => [k, i])), other: 999 }; // "other" always last
// Drive folder names → library type keys (the Drive sync already maps
// English/Spanish folder names; this only merges near-duplicates).
const CAT_ALIASES = { flyers: "flyer", volantes: "flyer", postcards: "postcard", catalogs: "catalog", minutes: "notes", form: "forms", report: "reports", workshop: "workshops" };
const KITS = new Set(["gvr", "rlv"]);
// Tags that name a document type (kit PDFs carry their type as a tag).
const TYPE_TAGS = new Set(CATEGORIES.map(([k]) => k).filter((k) => k !== "rep" && k !== "other"));

export const SOURCES = [
  { key: "gv", icon: "grapes", tone: "gv" },
  { key: "lv", icon: "grapes", tone: "lv" },
  { key: "neta", icon: "users", tone: "vine" },
];
export const LANGS = ["en", "es", "fr"];

// Quick collections. `code` is a single letter stored per document in the JSON.
export const COLLECTIONS = [
  { key: "gvr-kit", code: "g", icon: "badge-check", tone: "gv" },
  { key: "rlv-kit", code: "r", icon: "badge-check", tone: "lv" },
  { key: "catalogs", code: "c", icon: "book-open", tone: "grape" },
  { key: "flyers", code: "f", icon: "megaphone", tone: "vine" },
  { key: "news", code: "n", icon: "newspaper", tone: "gv" },
  { key: "reports", code: "m", icon: "folder-open", tone: "vine" },
];

// Drive items that are NOT library documents.
const DRIVE_SKIP_KINDS = new Set(["photo", "video_file", "event", "announcement"]);
const DRIVE_SKIP_CATS = new Set(["photos", "fotos", "announcements", "anuncios"]);

/* ------------------------------------------------------------------ */
/*  Text helpers                                                        */
/* ------------------------------------------------------------------ */

// Decode %XX escapes that can leak into titles from file names ("La-Vin%CC%83a").
function safeDecode(s) {
  if (!s || s.indexOf("%") === -1) return s;
  try { return decodeURIComponent(s); } catch { /* fall through: decode valid runs only */ }
  return s.replace(/(?:%[0-9A-Fa-f]{2})+/g, (run) => { try { return decodeURIComponent(run); } catch { return run; } });
}

function squish(s) { return String(s || "").replace(/\s+/g, " ").trim(); }

function hostOf(url) { try { return new URL(url).hostname.toLowerCase(); } catch { return ""; } }

function fileNameOf(url) {
  try { return new URL(url).pathname.split("/").filter(Boolean).pop() || ""; } catch { return String(url || "").split(/[?#]/)[0].split("/").pop() || ""; }
}

// "Libro_de_trabajo-de-La-Vin%CC%83a (1).pdf" → "Libro de trabajo de La Viña"
function prettyFile(name) {
  let b = safeDecode(name || "").normalize("NFC");
  b = b.replace(/\.[A-Za-z0-9]{2,5}$/, "").replace(/\.[A-Za-z0-9]{2,5}$/, ""); // "x.pdf.pdf" happens
  b = b.replace(/\s*\(\d+\)\s*$/, "").replace(/[_+]+/g, " ");
  b = b.replace(/(?<!\d)-+|-+(?!\d)/g, " "); // keep hyphens only between digits (2026-27)
  return squish(b).replace(/^[\s.-]+|[\s.-]+$/g, "");
}

// Cheap guard: a title that is ONLY a generic link text ("Read more", "Descargar aquí").
// The crawler already avoids these; this only protects against old/odd records.
const GENERIC_RE = /^(?:(?:click|haga?\s+clic|pulse)\s+(?:here|aqu[ií])|read\s*more|lee(?:r)?\s*m[aá]s|learn\s*more|more\s*info|m[aá]s\s*info(?:rmaci[oó]n)?|download(?:\s+(?:here|pdf|now))?|descarga(?:r)?(?:\s+(?:aqu[ií]|pdf))?|here|aqu[ií]|pdf|view|ver|open|abrir|link|enlace|file|archivo)$/i;
function isGeneric(t) {
  const s = squish(t).replace(/[.:!…»>→]+$/g, "").trim();
  return !s || s.length < 3 || GENERIC_RE.test(s);
}

// Loose comparable form (accent/case/separator-insensitive).
function fold(s) { return String(s || "").normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, ""); }

function dehyphen(s) {
  return squish(String(s || "").replace(/[_+]+/g, " ").replace(/(?<!\d)-+|-+(?!\d)/g, " "));
}

function cleanTitle(raw, fileTitle) {
  let t = squish(safeDecode(String(raw || "")).normalize("NFC")).replace(/\.pdf$/i, "").trim();
  // A title that is really a file name ("Manual-RLV-2025", "GV_Catalog_2026") reads better de-hyphenated.
  // (only when it LOOKS like one: "Oración y Meditación" keeps its accents over "Oracion_y_meditacion.pdf")
  if (t && fileTitle && fold(t) === fold(fileTitle) && (!/\s/.test(t) || /_/.test(t))) t = fileTitle;
  else if (t && !/\s/.test(t) && /[_-]/.test(t)) t = dehyphen(t);
  // Title-cased ordinals from machine translation: "30Th" → "30th".
  return t.replace(/(\d)(St|Nd|Rd|Th)\b/g, (m, d, s) => d + s.toLowerCase());
}

// Cheap guard on top of the translation pipeline's own guard: a degenerate
// machine translation ("information-information-information…") is worse than the original.
function looksBroken(tr, orig) {
  if (!tr) return true;
  if (tr.length > orig.length * 3 + 20) return true;
  return /(^|[^\p{L}])(\p{L}{3,})(?:[\s\-_,.]+\2){2,}(?!\p{L})/iu.test(tr);
}

// Language markers in DRIVE file names ("Informe_ESPANOL.pdf"). Crawled PDFs carry extra.doc_lang.
function langHint(name) {
  const w = " " + String(name || "").normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^a-z]+/g, " ") + " ";
  if (/ (frances|francais|french) /.test(w)) return "fr";
  if (/ (ingles|english) /.test(w)) return "en";
  if (/ (espanol|spanish) /.test(w)) return "es";
  return null;
}

// Calendar day in the Area's time zone (the rest of the site formats dates in Central time):
// an episode published 2026-09-21T04:15Z is "September 20" everywhere.
const DAY_FMT = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
function ymd(helpers, v) {
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)) return v; // already a plain date
  const d = helpers.toDate(v);
  if (!d) return "";
  try { return DAY_FMT.format(d); } catch { return d.toISOString().slice(0, 10); }
}

export function fmtNum(n, lang) {
  const v = Number(n);
  if (!Number.isFinite(v)) return String(n ?? "");
  try { return new Intl.NumberFormat(LOCALES[lang] || "en-US").format(v); } catch { return String(v); }
}

// translateKey for keys that may not exist (new Drive folder names, new nav
// pages, unexpected language codes) — "" instead of the raw key, and never
// throws (translateKey throws for missing keys when I18N_STRICT is set).
function tryKey(helpers, key, lang, vars) {
  try { const s = helpers.translateKey(key, lang, vars); return s === key ? "" : s; } catch { return ""; }
}

function catLabel(helpers, key, lang) {
  const s = tryKey(helpers, "library.cat." + key, lang);
  if (s) return s;
  // Unknown folder / type name → "Budget reports"
  const p = String(key || "").replace(/[-_]+/g, " ").trim();
  return p ? p.charAt(0).toUpperCase() + p.slice(1) : key;
}

/* ------------------------------------------------------------------ */
/*  Cached thumbnails (src/assets/cache/…)                              */
/* ------------------------------------------------------------------ */

// Pixel size from a WebP / PNG / JPEG header → {w, h}, or null (unknown format).
function imageSize(b) {
  const u24 = (i) => b[i] | (b[i + 1] << 8) | (b[i + 2] << 16);
  if (b.length >= 30 && b.toString("latin1", 0, 4) === "RIFF" && b.toString("latin1", 8, 12) === "WEBP") {
    const chunk = b.toString("latin1", 12, 16);
    if (chunk === "VP8 " && b[23] === 0x9d && b[24] === 0x01 && b[25] === 0x2a) return { w: b.readUInt16LE(26) & 0x3fff, h: b.readUInt16LE(28) & 0x3fff };
    if (chunk === "VP8L" && b[20] === 0x2f) { const v = b.readUInt32LE(21); return { w: (v & 0x3fff) + 1, h: ((v >>> 14) & 0x3fff) + 1 }; }
    if (chunk === "VP8X") return { w: u24(24) + 1, h: u24(27) + 1 };
    return null;
  }
  if (b.length >= 24 && b.readUInt32BE(0) === 0x89504e47 && b.toString("latin1", 12, 16) === "IHDR") return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  if (b.length >= 4 && b[0] === 0xff && b[1] === 0xd8) {
    for (let i = 2; i + 9 < b.length;) {
      if (b[i] !== 0xff) { i++; continue; }
      const m = b[i + 1];
      if (m === 0xff) { i++; continue; }
      if (m === 0xd9 || m === 0xda) break; // end of image / start of scan: no frame header before it
      if (m === 0x01 || (m >= 0xd0 && m <= 0xd8)) { i += 2; continue; } // markers without a length
      if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) return { w: b.readUInt16BE(i + 7), h: b.readUInt16BE(i + 5) };
      i += 2 + b.readUInt16BE(i + 2);
    }
  }
  return null;
}

// Site-relative thumbnail ("/assets/cache/pdf/x.webp") → false when the file is missing
// (no <img> that would 404), else its {w, h} (null if the format is unknown).
// Web links → undefined (not checked). Reset with the document cache on every build.
const thumbSeen = new Map();
function localThumb(p) {
  const s = String(p || "");
  if (!/^\/assets\/[\w\-./]+$/.test(s) || s.includes("..")) return undefined;
  if (!thumbSeen.has(s)) {
    let r = false;
    try {
      const fd = openSync(path.join("src", s), "r");
      try {
        const b = Buffer.alloc(65536);
        const n = readSync(fd, b, 0, b.length, 0);
        r = n > 0 ? imageSize(b.subarray(0, n)) : false;
      } finally { closeSync(fd); }
    } catch { r = false; }
    thumbSeen.set(s, r);
  }
  return thumbSeen.get(s);
}

/* ------------------------------------------------------------------ */
/*  Library documents                                                   */
/* ------------------------------------------------------------------ */

/** Kit ("gvr" | "rlv" | "") and document type of a PDF / Drive item. */
export function docKitType(item) {
  let c = String(item?.category || "other").toLowerCase().trim() || "other";
  c = CAT_ALIASES[c] || c;
  if (!KITS.has(c)) return { kit: "", type: c };
  const tag = (Array.isArray(item.tags) ? item.tags : []).map((x) => CAT_ALIASES[String(x).toLowerCase()] || String(x).toLowerCase()).find((x) => TYPE_TAGS.has(x));
  return { kit: c, type: tag || "rep" };
}

function collectionsFor(doc) {
  let co = "";
  const kits = new Set([doc.kit, ...(doc.ks || [])]);
  if (kits.has("gvr")) co += "g";
  if (kits.has("rlv")) co += "r";
  if (doc.c === "catalog") co += "c";
  if (doc.c === "flyer" || doc.c === "postcard") co += "f";
  if (doc.c === "news") co += "n";
  if (doc.s === "neta" && ["reports", "notes", "minutes", "informes", "actas"].includes(doc.c)) co += "m";
  return co;
}

function normalizeDoc(item, lang, helpers) {
  const ex = item.extra || {};
  const isDrive = item.source === "drive" || item.source === "committee";
  const openUrl = isDrive ? (ex.view_url || item.url) : (ex.file_url || item.url);
  if (!openUrl || !SAFE_URL.test(openUrl)) return null;
  const fileTitle = prettyFile(isDrive ? (item.title || "") : (ex.filename || fileNameOf(openUrl)));
  const refs = Array.isArray(ex.referrers) ? ex.referrers.filter((r) => r && SAFE_URL.test(r.url || "")) : [];

  // --- titles -------------------------------------------------------------
  let orig = cleanTitle(item.title || "", fileTitle);
  let t;
  let fromFile = false; // the title is the file name (its language is the document's, not item.lang)
  let machine = !!(item.machine && item.machine.includes(lang));
  if (isGeneric(orig)) {
    orig = fileTitle || orig; // same text in both languages — a translated file name means nothing
    t = orig;
    fromFile = !!fileTitle;
    machine = false;
  } else {
    t = cleanTitle(helpers.pickLang(item, "title", lang), fileTitle) || orig;
    if (isGeneric(t) || looksBroken(t, orig)) { t = orig; machine = false; }
  }
  if (!t) { t = orig = fileTitle || hostOf(openUrl) || tryKey(helpers, "library.untitled", lang) || "…"; fromFile = true; } // never an empty heading
  if (fold(t) === fold(orig)) machine = false; // "translation" identical to original → not worth a note

  // --- source: where the file was published --------------------------------
  // aa.org PDFs linked from aalavina.org count as La Viña (the page that shares them).
  const host = String(ex.host || hostOf(openUrl)).toLowerCase();
  let pubHost = host;
  if (!isDrive && !OFFICIAL_HOST.test(host)) pubHost = refs.map((r) => hostOf(r.url)).find((h) => OFFICIAL_HOST.test(h)) || host;
  const s = isDrive ? "neta" : /lavina/i.test(pubHost) ? "lv" : "gv";
  const { kit, type: c } = docKitType(item);

  // --- document language (extra.doc_lang; item.lang is the TITLE language) --
  const l = okLang(ex.doc_lang) || (isDrive ? langHint(item.title) : null) || okLang(item.lang) || (s === "lv" ? "es" : "en");
  // Language of the original title ("La Viña Subscription Form (Spanish)" is English
  // text about a Spanish document). Unknown ("und") → the document's language.
  const tl = (!fromFile && okLang(item.lang)) || l;

  // --- dates ----------------------------------------------------------------
  const date = helpers.toDate(item.date);
  const d = date ? ymd(helpers, item.date) : isDrive ? ymd(helpers, item.first_seen) : "";
  // Crawled PDFs often only know their upload month (…/files/2026-02/… → "2026-02-01"): show "February 2026".
  const dp = !isDrive && d && ex.upload_month && d === `${ex.upload_month}-01` ? "m" : "";
  const fs = (helpers.toDate(item.first_seen) || new Date(0)).getTime();

  const kind = item.kind || "pdf";
  const mime = String(ex.mime || "");
  const ft = kind === "slides" || /presentation/.test(mime) ? "slides"
    : kind === "form" || /form/.test(mime) ? "form"
    : /pdf/.test(mime) || kind === "pdf" || /\.pdf($|\?)/i.test(openUrl) ? "pdf"
    : /word|document/.test(mime) ? "doc" : /image/.test(mime) ? "image" : "file";
  let thumb = (isDrive ? (ex.thumb_url || item.image) : (ex.thumb || item.image)) || "";
  if (!SAFE_URL.test(thumb)) thumb = "";
  const shape = thumb ? localThumb(thumb) : undefined;
  if (shape === false) thumb = ""; // cached file missing: show the paper tile, not a broken request
  const ref = refs[0] || null;
  const ev = /^\d{4}-\d{2}-\d{2}$/.test(String(ex.event_date || "")) ? ex.event_date : "";

  const doc = {
    id: item.id,
    k: kind,
    ft,
    s,
    c,
    kit,
    l,
    tl,
    t,
    o: fold(orig) !== fold(t) ? orig : "", // set only when `t` is a translation (else t IS the original, in `tl`)
    m: machine,
    d,
    dp,
    y: d ? Number(d.slice(0, 4)) : null,
    ev,
    u: openUrl,
    dl: isDrive && SAFE_URL.test(ex.download_url || "") ? ex.download_url : "",
    pv: isDrive && SAFE_URL.test(ex.preview_url || "") ? ex.preview_url : "",
    th: thumb,
    // Tall first page → shown whole on a blurred copy of itself (see TALL_PAGE, library.css .lib-th-fit).
    tf: !!(shape && shape.w > 0 && shape.h / shape.w > TALL_PAGE),
    sz: Number(ex.size_bytes) || 0,
    pg: Number(ex.pages) || 0,
    r: ref ? { url: ref.url, title: squish(safeDecode(ref.title || "")) || hostOf(ref.url).replace(/^www\./, "") } : null,
    hx: !isDrive && host && !OFFICIAL_HOST.test(host) ? host.replace(/^www\./, "") : "", // opens on another site (aa.org)
    or: !isDrive && ex.orphan === true, // no page links to it any more
    n: !!item.is_new,
    fname: fileTitle,
    ks: Array.isArray(ex.kits) ? ex.kits.filter((k) => KITS.has(k)) : [],
    panel: ex.panel_label || "",
    // Undated crawled PDFs sort last ("first found today" says nothing about their age).
    ts: date ? date.getTime() : isDrive ? fs : 0,
    fs,
  };
  doc.co = collectionsFor(doc);
  return doc;
}

/* ---- language editions (extra.versions, see scripts/sync/pdf_curate.py) ---- */
const VERSION_FIELDS = ["host", "file_url", "filename", "size_bytes", "pages", "thumb", "upload_month", "referrers", "event_date", "orphan"];
/** The editions of a merged document (2+ with a language and a web link), else null. */
function versionsOf(item) {
  const vs = Array.isArray(item?.extra?.versions) ? item.extra.versions.filter((v) => v && okLang(v.lang) && SAFE_URL.test(v.url || "")) : [];
  return vs.length > 1 ? vs : null;
}
/** The entry as seen through one of its editions (the fields normalizeDoc reads). */
function editionItem(item, v) {
  const ex = { ...(item.extra || {}), doc_lang: v.lang, file_url: v.file_url || v.url };
  for (const k of VERSION_FIELDS) if (k !== "file_url") ex[k] = v[k] ?? null;
  delete ex.versions;
  return {
    ...item,
    url: v.url,
    title: v.title || item.title,
    lang: okLang(v.title_lang) || v.lang,
    i18n: { ...(item.i18n || {}), title: v.i18n_title || {} },
    machine: Array.isArray(v.machine) ? v.machine : [],
    date: v.date ?? item.date,
    first_seen: v.first_seen || item.first_seen,
    category: v.category || item.category,
    tags: Array.isArray(v.tags) ? v.tags : item.tags,
    extra: ex,
  };
}
// Language names in their own language, for the edition links ("English · Español").
const ENDONYMS = { en: "English", es: "Español", fr: "Français" };

const cache = new Map(); // key: lang + items identity → docs (rebuilt every build)
let cacheGen = null;

export function libraryDocs(db, lang, helpers) {
  if (EMPTY() || !db) return [];
  const pdfs = (db.pdfs && db.pdfs.items) || [];
  const drive = (db.drive && db.drive.items) || [];
  if (cacheGen !== pdfs) { cache.clear(); thumbSeen.clear(); cacheGen = pdfs; }
  const ck = lang + ":" + drive.length + ":" + pdfs.length;
  if (cache.has(ck)) return cache.get(ck);

  const out = [];
  const seen = new Set();
  const add = (it) => {
    let d = null;
    try {
      const vs = it.source !== "drive" && it.source !== "committee" ? versionsOf(it) : null;
      if (vs) {
        // One card per document: the edition in the page language (else the entry's own), with
        // links to every edition — this page's language first.
        const cur = vs.find((v) => v.lang === lang) || vs.find((v) => v.id === it.id) || vs[0];
        d = normalizeDoc(editionItem(it, cur), lang, helpers);
        if (d) {
          d.id = it.id; // the same anchor (#doc-…) in both languages
          const ordered = [cur, ...vs.filter((v) => v !== cur)];
          d.ls = [...new Set(ordered.map((v) => v.lang))];
          // One bilingual file filed under each site's language: no edition links (it is the same file).
          d.vs = it.extra.same_file ? [] : ordered.map((v) => ({ l: v.lang, u: v.url, name: ENDONYMS[v.lang] || v.lang.toUpperCase() }));
          // Other editions' titles are search words too ("Descarga de audios" finds "Audio Downloads").
          d.alt = [...new Set(ordered.slice(1).map((v) => cleanTitle(v.title || "", "")).filter((t) => t && fold(t) !== fold(d.t) && fold(t) !== fold(d.o)))].join(" · ");
        }
      } else d = normalizeDoc(it, lang, helpers);
    } catch (e) { console.warn(`[library] skipped ${it && it.id}: ${e.message}`); }
    if (d && d.id && !seen.has(d.id)) { seen.add(d.id); out.push(d); }
  };
  for (const it of pdfs) {
    if (!it || it.status === "gone") continue;
    add(it);
  }
  for (const it of drive) {
    if (!it || it.status === "gone") continue;
    const cat = String(it.category || "").toLowerCase();
    if (DRIVE_SKIP_KINDS.has(it.kind) || DRIVE_SKIP_CATS.has(cat)) continue;
    if (it.extra && (it.extra.is_image || it.extra.is_video || it.extra.form_closed === true)) continue;
    add(it);
  }
  // Newest first; files no page links to any more go last.
  out.sort((a, b) => (a.or - b.or) || b.ts - a.ts || b.fs - a.fs || a.t.localeCompare(b.t, lang));
  cache.set(ck, out);
  return out;
}

export function libraryFacets(docs, lang, helpers) {
  const count = (key) => { const m = new Map(); for (const d of docs) { const v = d[key]; if (v === null || v === "" || v === undefined) continue; m.set(v, (m.get(v) || 0) + 1); } return m; };
  const src = count("s"), cat = count("c"), yr = count("y");
  // A document with editions in several languages counts once in each of them.
  const lng = new Map();
  for (const d of docs) for (const l of d.ls && d.ls.length ? d.ls : [d.l]) if (l) lng.set(l, (lng.get(l) || 0) + 1);
  const langLabel = (k) => tryKey(helpers, "library.lang." + k, lang) || k.toUpperCase();
  return {
    src: SOURCES.filter((x) => src.get(x.key)).map((x) => ({ key: x.key, label: helpers.translateKey("library.src." + x.key, lang), count: src.get(x.key), tone: x.tone })),
    lang: [...LANGS.filter((k) => lng.get(k)), ...[...lng.keys()].filter((k) => !LANGS.includes(k)).sort()]
      .map((k) => ({ key: k, label: langLabel(k), count: lng.get(k) })),
    cat: [...cat.keys()].sort((a, b) => (CAT_ORDER[a] ?? 500) - (CAT_ORDER[b] ?? 500) || a.localeCompare(b))
      .map((k) => ({ key: k, label: catLabel(helpers, k, lang), count: cat.get(k), icon: CAT_ICON[k] || "file-text" })),
    year: [...yr.keys()].sort((a, b) => b - a).map((k) => ({ key: String(k), label: String(k), count: yr.get(k) })),
  };
}

export function libraryCollections(docs, lang, helpers) {
  return COLLECTIONS.map((c) => {
    const count = docs.filter((d) => d.co.includes(c.code)).length;
    return {
      ...c,
      label: helpers.translateKey(`library.col.${c.key}`, lang),
      // An empty collection says what will show up there (instead of just "0").
      desc: (!count && tryKey(helpers, `library.col.${c.key}_empty`, lang)) || helpers.translateKey(`library.col.${c.key}_desc`, lang),
      count,
    };
  });
}

// The hero's "new this month" (library.stat_new): documents dated this calendar month in Central time — from
// the 1st through today (a crawled PDF known only by its upload month counts in that month), never one whose
// page no longer links it (`or`).
export function libraryStats(docs, now = Date.now()) {
  const today = DAY_FMT.format(new Date(now));
  const month = today.slice(0, 7);
  const bySrc = { gv: 0, lv: 0, neta: 0 };
  let recent = 0, pdf = 0;
  for (const d of docs) {
    bySrc[d.s] = (bySrc[d.s] || 0) + 1;
    if (d.ft === "pdf") pdf++;
    if (d.d && !d.or && d.d.slice(0, 7) === month && d.d <= today) recent++;
  }
  return { total: docs.length, pdf, recent, bySrc, sources: Object.values(bySrc).filter(Boolean).length };
}

/* Compact client index: short keys, empty fields omitted, referrers de-duplicated. */
export function libraryIndex(db, lang, helpers) {
  const docs = libraryDocs(db, lang, helpers);
  const refs = [];
  const refIdx = new Map();
  const cats = {};
  const items = docs.map((d) => {
    const o = { id: d.id, t: d.t, s: d.s, c: d.c, l: d.l, u: d.u };
    if (d.tl !== d.l) o.tl = d.tl; // title language, when not the document's (library.js: d.tl || d.l)
    if (d.o) o.o = d.o;
    if (d.m) o.m = 1;
    if (d.d) o.d = d.d;
    if (d.dp) o.dp = d.dp;
    if (d.ev) o.ev = d.ev;
    if (d.th) o.th = d.th;
    if (d.th && d.tf) o.tf = 1;
    if (d.dl) o.dl = d.dl;
    if (d.pv) o.pv = d.pv;
    if (d.sz) o.sz = d.sz;
    if (d.pg) o.pg = d.pg;
    if (d.hx) o.hx = d.hx;
    if (d.or) o.or = 1;
    if (d.n) o.n = 1;
    if (d.k !== "pdf") o.k = d.k;
    if (d.ft !== "pdf") o.ft = d.ft;
    if (d.co) o.co = d.co;
    if (d.ls && d.ls.length > 1) o.ls = d.ls; // languages of all its editions (language facet)
    if (d.vs && d.vs.length > 1) o.vs = d.vs.map((v) => [v.l, v.u]); // edition links, this page's language first
    // Extra search words: the file name, when it adds words the titles don't have; other editions' titles.
    const xw = [d.fname && !fold(d.t + d.o).includes(fold(d.fname)) ? d.fname : "", d.alt || ""].filter(Boolean).join(" · ");
    if (xw) o.x = xw;
    if (d.r) {
      const key = d.r.url;
      if (!refIdx.has(key)) { refIdx.set(key, refs.length); refs.push([d.r.url, d.r.title]); }
      o.r = refIdx.get(key);
    }
    if (!(d.c in cats)) cats[d.c] = catLabel(helpers, d.c, lang);
    return o;
  });
  return {
    v: 2,
    lang,
    updated: [db?.pdfs?.updated, db?.drive?.updated].filter(Boolean).sort().pop() || null,
    count: items.length,
    cats,
    refs,
    items,
  };
}

/* ------------------------------------------------------------------ */
/*  Site-wide search index                                              */
/* ------------------------------------------------------------------ */

function snippet(s, n = 170) {
  s = squish(String(s || "").replace(/<[^>]*>/g, " ").replace(/https?:\/\/\S+/g, ""));
  if (s.length <= n) return s;
  return s.slice(0, n).replace(/\s+\S*$/, "").replace(/[,;:.\-–—\s]+$/, "") + "…";
}

// Anchors on the committee pages (#album-…, bulletin post / event cards) are made by
// eleventy/filters/committee.js. Reuse its helpers so search results land on the
// exact card; if that file ever changes or goes away, fall back to the same rules.
let committee = {};
try { committee = await import("./committee.js"); } catch { /* optional */ }
// Since round 37 an event's result opens its own page, a monthly series' its series' page: the pages the build writes
// (eleventy/event-pages.js eventPagePlan — the one answer the event pages' templates paginate over, so a result never
// links a page that was not written) and the cancelled events' notice pages (eleventy/cancelled-pages.js). Without
// them (a file gone), the cards on /events/ as before.
let eventPages = {};
try { eventPages = await import("../event-pages.js"); } catch { /* optional */ }
let cancelledNotices = {};
try { cancelledNotices = await import("../cancelled-pages.js"); } catch { /* optional */ }
// The cancelled events' notice pages (cancelledPages: every language at once — it reads all the events in each, about
// half a second), worked out once for both languages' indexes: the same lists (db.events: one object for every
// template) at the same moment of the same site give the same answer — keyed like eventPagePlan's memo, by site.built
// and site.url, as each template's `site` is a copy of its own. Forgotten at each build's start (eleventy.before).
let cancelledMemo = null;
const EMPTY_LIST = Object.freeze([]);
// The address of every page this build writes (Eleventy's "eleventy.contentMap": every page of every template — a
// pagination's pages too, in a collection or not), known before any page is rendered; null outside a build (a test, a
// script). The search links a monthly series' page only when it is among them (searchIndex, hubOf).
let builtUrls = null;
function cancelledOnce(cancelled, items, site) {
  const key = `${site?.built ?? ""}|${site?.url ?? ""}`;
  const m = cancelledMemo;
  if (!m || m.cancelled !== cancelled || m.items !== items || m.key !== key) {
    cancelledMemo = { cancelled, items, key, pages: cancelledNotices.cancelledPages(cancelled, items, site || {}, siteLanguages) };
  }
  return cancelledMemo.pages;
}
function slug(s, max = 60) {
  if (typeof committee.slugify === "function") { try { return committee.slugify(s, max); } catch { /* fall back */ } }
  return String(s || "").normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "").slice(0, max).replace(/-+$/, "") || "item";
}
// An event's title as /events/ shows it: without the spaces a calendar left inside its brackets (committee.js
// tidyBrackets: "… ( A.A. Un camino a la vida )" → "… (A.A. Un camino a la vida)"), its original's too
function tidyTitle(s) {
  if (typeof committee.tidyBrackets === "function") { try { return committee.tidyBrackets(s); } catch { /* fall back */ } }
  return String(s ?? "").replace(/([(¿¡])\s+/g, "$1").replace(/\s+\)/g, ")");
}

// How many past events /events/ lists (keep in sync with `past | limit(40)` in src/pages/events.njk).
const PAST_EVENTS_SHOWN = 40;

// Icons for site pages that have none in nav.js (footer links).
const PAGE_ICONS = { home: "house", about: "info", digest: "mail", share: "qr-code", search: "search", status: "activity" };

// Published-writers spotlight (data/site/spotlight.json, see docs/DATA_SCHEMA.md): db.spotlight when
// the data loader provides it, else the file itself (read once per build). Only names, places and
// counts are used from it — no links. null when there is none yet.
let spotFile;
function spotlightOf(db) {
  if (db && db.spotlight && Array.isArray(db.spotlight.items)) return db.spotlight;
  if (spotFile === undefined) {
    try { spotFile = JSON.parse(readFileSync(path.join("data", "site", "spotlight.json"), "utf8")); } catch { spotFile = null; }
    if (!spotFile || !Array.isArray(spotFile.items)) spotFile = null;
  }
  return spotFile;
}
const TEXAS_SCOPES = new Set(["neta65", "texas"]);
// The /published/ scope choices, narrowest first ("texas" includes Area 65; "all" = everyone).
const SPOT_SCOPES = ["neta65", "texas", "all"];
/**
 * The "Published Writers" browse tile on /search/ — the number it shows must be what the visitor
 * sees after clicking. `view` = db | pwView(lang) (eleventy/filters/published.js: the SAME counts
 * the /published/ page renders, windows counted from today in America/Chicago); without it, the
 * counts stored in spotlight.json. Normally the page's default view (default_scope + first
 * list_days window, no query string). When that view is empty, the first non-empty one — Area 65
 * first (longer window), then Texas, then everyone — and `query` opens /published/ on exactly
 * that view (?scope=&days=, which published.js reads; defaults are left out, as it does).
 * → { n, scope: "neta65" | "texas" | "all", days, query }; n = 0 when there is nothing to show.
 */
export function spotlightTile(view, db) {
  const fromView = !!(view && view.counts && Array.isArray(view.listDays) && view.listDays.length);
  const sp = fromView || EMPTY() ? null : spotlightOf(db);
  const num = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);
  let list, defDays, defScope, count;
  if (fromView) {
    list = view.listDays.map(Number).filter((d) => Number.isInteger(d) && d > 0);
    defDays = list.includes(Number(view.defDays)) ? Number(view.defDays) : list[0];
    defScope = view.defScope;
    // pwView: counts[days][scope][pub] ("all" = both magazines).
    count = (d, s) => { const c = view.counts[d] && view.counts[d][s]; return num(c && typeof c === "object" ? c.all : c); };
  } else {
    const raw = sp && Array.isArray(sp.list_days) ? sp.list_days.map(Number).filter((d) => Number.isInteger(d) && d > 0) : [];
    list = raw.length ? [...new Set(raw)] : [60, 90];
    defDays = list[0]; // "first = default"
    defScope = sp && sp.default_scope;
    count = (d, s) => { const c = sp && sp.counts && sp.counts[String(d)]; return num(c && c[s]); };
  }
  if (!SPOT_SCOPES.includes(defScope)) defScope = "neta65";
  const tile = { n: 0, scope: defScope, days: defDays, query: "" };
  if (EMPTY() || !list.length) return tile;
  const windows = [defDays, ...list.filter((d) => d > defDays).sort((a, b) => a - b)];
  for (const scope of SPOT_SCOPES.slice(SPOT_SCOPES.indexOf(defScope))) {
    for (const days of windows) {
      const n = count(days, scope);
      if (n <= 0) continue;
      const q = [];
      if (scope !== defScope) q.push("scope=" + scope);
      if (days !== defDays) q.push("days=" + days);
      return { n, scope, days, query: q.length ? "?" + q.join("&") : "" };
    }
  }
  return tile;
}

// Language-neutral internal path → path in the page language ("/events/#x" → "/es/events/#x").
const lurl = (u, lang) => (!u || /^(https?:|mailto:|tel:|#)/.test(u) ? u : (lang && lang !== "en" ? `/${lang}` : "") + (u.startsWith("/") ? u : "/" + u));
// Data items link to our own pages with language-neutral paths ("/bulletin/#slug").
const isInternal = (u) => typeof u === "string" && /^\/(?!\/)/.test(u);

/**
 * The site search's entries in one language (/search-index.json; the fields: src/pages/search-index.11ty.js) —
 * everything the site shows, each linking where it is: the site's pages, and since round 37 also the sections of its
 * long pages (eleventy/search-sections.js), the presentations (`extra.presentations`: the `presentations` global,
 * src/_data/presentations.js — left out when it is not given), the month toolkits, the current issues, the Drive's
 * flyers, the shop's offers, the next committee meeting, every event's own page (a monthly series' page for a series —
 * once the build writes it: `extra.pages`, the addresses of the build's pages, when given) and a cancelled event's
 * notice; then the synced content (stories, documents, episodes, videos, posts, albums …).
 * The [search] check (eleventy/seo-check.js searchProblems) checks the built result: every page the sitemap lists has
 * an entry, every link's page and #anchor exists, each language's file stays under its size budget.
 */
export function searchIndex(db, nav, lang, helpers, site, extra = {}) {
  const T = (k, vars) => helpers.translateKey(k, lang, vars);
  const P = (it, f) => squish(helpers.pickLang(it, f, lang));
  const both = (k) => [tryKey(helpers, k, "en"), tryKey(helpers, k, "es")].filter(Boolean).join(" ");
  // "October 2026 · Loneliness" — distinct phrases only (accent/case-insensitive).
  const uniq = (list, sep = " · ") => list.filter((v, i, a) => v && a.findIndex((w) => fold(w) === fold(v)) === i).join(sep);
  const out = [];
  const seenId = new Set();
  // `u`: absolute link, or a language-neutral internal path (prefixed here, once).
  // `a`: a story's byline — writer · hometown ("Victor R. · Grand Prairie, Texas"), searched and shown.
  // Languages (for lang="" in search.js): `l` = the item's language (badge); `ol` = language
  // of the original title `o` (default `l`); `tl` = language of the shown title `t` when
  // known. With `o` given, a `t` equal to it IS the untranslated original (language `ol`).
  const push = (e) => {
    if (!e.u || !SAFE_URL.test(e.u) || !e.id || seenId.has(e.id) || !squish(e.t)) return; // nothing to link to / no title
    seenId.add(e.id);
    if (e.im && !SAFE_URL.test(e.im)) e.im = "";
    const o = { id: e.id, k: e.k, t: squish(e.t), u: isInternal(e.u) ? lurl(e.u, lang) : e.u };
    // a second link: an episode's page at its podcast host; a presentation's "Start the presentation" (one of our own
    // pages: its path in the page language, as `u`)
    if (e.u2 && SAFE_URL.test(e.u2)) o.u2 = isInternal(e.u2) ? lurl(e.u2, lang) : e.u2;
    const ol = okLang(e.ol) || okLang(e.l);
    let tl = okLang(e.tl);
    if (e.o && fold(e.o) !== fold(e.t)) {
      o.o = squish(e.o);
      if (ol && ol !== okLang(e.l)) o.ol = ol;
    } else if (e.o && !tl) tl = ol;
    if (tl && tl !== lang) o.tl = tl; // an untranslated title in another language
    if (e.s) o.s = e.s;
    if (e.x && e.x.trim()) o.x = squish(e.x);
    if (e.d) o.d = e.d;
    if (e.d && e.dp) o.dp = e.dp;
    if (e.l && e.l !== "und") o.l = e.l;
    if (e.src) o.src = e.src;
    if (e.im) o.im = e.im;
    if (e.yt) o.yt = e.yt;
    if (e.m) o.m = 1;
    if (e.n) o.n = 1;
    if (e.pw) o.pw = 1;
    if (e.z) o.z = 1;
    if (e.tb) o.tb = 1;
    if (e.lw) o.lw = 1;
    if (e.pr) o.pr = 1;
    if (e.ic) o.ic = e.ic;
    if (e.a && squish(e.a)) o.a = squish(e.a);
    out.push(o);
  };
  const mach = (it) => !!(it.machine && it.machine.includes(lang)) && fold(helpers.pickLang(it, "title", lang)) !== fold(it.title);
  const ok = (it) => it && it.status !== "gone";
  const safely = (label, fn) => { try { fn(); } catch (e) { console.warn(`[search-index] ${label}: ${e.message}`); } };

  /* ---- site pages (always present, even with no synced content) ---- */
  const pages = [{ key: "nav.home", url: "/", page: "home", icon: "house" }];
  const walk = (list) => { for (const it of list || []) { if (it.children) walk(it.children); else if (it.url) pages.push(it); } };
  walk(nav && nav.primary);
  walk(nav && nav.footer);
  const seenPage = new Set();
  // The Published Writers page is also found by the hometowns of the Texas writers it spotlights (Area 65
  // included): searching "Tyler" or "Grayson" offers the page…
  let spotWords = "";
  // …and by those of the writers in its Texas writers archive (db.writers_archive, ≈1,300 stories, all years),
  // with the archive's own keywords — words on the page's entry (each story has an entry of its own too since round
  // 37's fixer, with its byline as the Library's stories have theirs: "archive stories" below). Places only, the towns geo knows
  // (it found their counties): city, county and label, in geo's spelling ("Fort Worth", not a printed "Forth
  // Worth"). No names and no bylines as printed: first names, initials and bylines such as "Panel 31 delegate"
  // or "Central Office newsletter" would make the page a hit for everyday AA searches ("Bill W.", "delegate").
  let arcWords = "";
  if (!EMPTY()) {
    // the words split the way MiniSearch splits (spaces and punctuation), each once (the page's own keywords
    // included), nothing shorter than 2 letters
    const seen = new Set(both("search.kw.published").split(/[\s\p{Z}\p{P}]+/u).map(fold));
    const wordsOf = (values) => {
      const words = [];
      for (const v of values) {
        for (const word of squish(v).split(/[\s\p{Z}\p{P}]+/u)) {
          const f = fold(word);
          if (f.length < 2 || seen.has(f)) continue;
          seen.add(f);
          words.push(word);
        }
      }
      return words;
    };
    // a town geo knows: it found its counties (not "Texas", "Kingwood Group", "Grupo Paz y Sobriedad")
    const towns = (geos) => geos.filter((g) => g && Array.isArray(g.counties) && g.counties.length)
      .flatMap((g) => [g.city, g.county, g.label_en, g.label_es]);
    safely("spotlight", () => {
      const geos = (spotlightOf(db)?.items || []).map((it) => it?.extra?.geo).filter((g) => g && TEXAS_SCOPES.has(g.scope));
      spotWords = wordsOf(towns(geos)).join(" ");
    });
    safely("writers archive", () => {
      const geos = (db?.writers_archive?.items || []).flatMap((it) => (Array.isArray(it?.writers) ? it.writers : []).map((w) => w && w.geo));
      const words = wordsOf(towns(geos));
      arcWords = words.length ? [...words, ...wordsOf([both("search.kw.published_archive")])].join(" ") : "";
    });
  }
  for (const p of pages) {
    const pk = p.page || p.url.replace(/^\/|\/$/g, "") || "home";
    if (seenPage.has(p.url)) continue;
    seenPage.add(p.url);
    const desc = tryKey(helpers, p.descKey || `search.page_desc.${pk}`, lang) || tryKey(helpers, `search.page_desc.${pk}`, lang);
    push({
      id: "page:" + pk,
      k: "page",
      t: tryKey(helpers, p.key, lang) || p.url,
      tl: lang, // our own UI string, always in the page language
      o: tryKey(helpers, p.key, lang === "es" ? "en" : "es"),
      ol: lang === "es" ? "en" : "es",
      s: desc,
      // (the Share your story page is also found by "faq" / "preguntas frecuentes": its FAQ — words of its own, as the
      // open calls for stories share search.kw.contribute and are no FAQ)
      x: [both(`search.kw.${pk}`), pk === "contribute" ? both("search.kw.contribute_faq") : "",
        pk === "published" ? spotWords : "", pk === "published" ? arcWords : ""].filter(Boolean).join(" "),
      u: p.url,
      src: "site",
      ic: p.icon || PAGE_ICONS[pk] || "file-text",
    });
  }
  /* ---- The GV/LV report for the district meeting: its one home is /monthly/#report, so a search
     for "district" / "distrito" or "report" / "informe" lands on the section, not the page top ---- */
  if (seenPage.has("/monthly/") && !seenPage.has("/monthly/#report")) {
    seenPage.add("/monthly/#report");
    push({
      id: "report:monthly", k: "page", t: T("community.report.title"), tl: lang, s: T("community.report.sub"),
      x: both("search.kw.report"), u: "/monthly/#report", src: "site", ic: "clipboard-list",
    });
  }
  /* ---- GVR / RLV 101: each lesson has a page of its own (/orientation/<id>/), found by its title in
     both languages, its key points and "orientation" / "orientación" (config/orientation.yml) ---- */
  if (seenPage.has("/orientation/")) {
    safely("orientation", () => {
      const other = lang === "es" ? "en" : "es";
      const txt = (p, l = lang) => squish(String((p && (p[l] || p.en)) || "").replace(/\{\w+\}/g, ""));
      for (const l of orientationData().lessons || []) {
        push({
          id: "orientation:" + l.id, k: "page", t: `${T("nav.orientation")} · ${txt(l.title)}`, tl: lang, s: txt(l.summary),
          x: [txt(l.title, other), both("search.kw.orientation"), ...(l.points || []).flatMap((p) => [txt(p.title), txt(p.title, other)])].join(" "),
          u: `/orientation/${l.id}/`, src: "site", ic: l.icon || "graduation-cap",
        });
      }
    });
  }
  /* ---- The bingo cards (/gvr/bingo/, src/pages/gvr-bingo.njk): a page of the GVR / RLV corner the menu does not
     list, found by its name in both languages and "bingo" / "game" / "print" (search.kw.bingo) ---- */
  if (seenPage.has("/gvr/") && !seenPage.has("/gvr/bingo/")) {
    seenPage.add("/gvr/bingo/");
    push({
      id: "page:gvr-bingo", k: "page", t: T("bingo.title"), tl: lang, o: tryKey(helpers, "bingo.title", lang === "es" ? "en" : "es"),
      ol: lang === "es" ? "en" : "es", s: T("bingo.meta_desc"), x: both("search.kw.bingo"), u: "/gvr/bingo/", src: "site", ic: "grid-3x3",
    });
  }
  const other = lang === "es" ? "en" : "es";
  /* ---- Since round 37: the sections of the long pages (eleventy/search-sections.js) — "booth display", "FAQ", "New to
     AA?", "ASL" land on the section itself (/about/#booth-title …), each found by its heading in both languages and its
     search.sec.<id>.x words; only a page the menus list (its entry is above). Kind "section": results show it (the
     "Jump to" box keeps to the pages), the Pages filter counts it ---- */
  safely("sections", () => {
    let history = null;
    try { history = historyData(); } catch { history = null; } // (a file the build itself refuses: its page says so)
    const ctx = { orientation: orientationData(), history };
    for (const sec of SEARCH_SECTIONS) {
      if (!seenPage.has(sec.page)) continue;
      if (typeof sec.shown === "function" && !sec.shown(ctx)) continue; // (the page leaves it out: nothing to find)
      const tv = typeof sec.titleVars === "function" ? sec.titleVars(ctx) : undefined;
      const sv = typeof sec.subVars === "function" ? sec.subVars(ctx) : undefined;
      push({
        id: "section:" + sec.id, k: "section", t: T(sec.title, tv), tl: lang, o: tryKey(helpers, sec.title, other, tv), ol: other,
        s: sec.sub ? snippet(T(sec.sub, sv), 200) : "",
        x: [sec.x ? both(sec.x) : "", sec.page === "/shop/" ? both("search.kw.shop_section") : "",
          sec.sub ? snippet(tryKey(helpers, sec.sub, other, sv), 200) : ""].filter(Boolean).join(" "),
        u: `${sec.page}#${sec.anchor}`, src: "site", ic: sec.icon || "file-text",
      });
    }
  });
  /* ---- The presentations (/orientation/#presentations: config/presentations/<id>.yml — the `presentations` global,
     handed over by the templates): each deck's card, found by its title and summary in both languages, its audience and
     "presentation" / "slides" / "diapositivas" (search.kw.presentation); `u` its card (/orientation/#pres-<id>), `u2`
     "Start the presentation" (/orientation/?present=<id>: the player opens it, search.js altLink) ---- */
  safely("presentations", () => {
    const decks = (extra && extra.presentations && Array.isArray(extra.presentations.decks)) ? extra.presentations.decks : [];
    if (!decks.length || !seenPage.has("/orientation/")) return;
    const txt = (p, l = lang) => squish((p && typeof p === "object" ? p[l] || p.en || p.es : p) || "");
    for (const d of decks) {
      if (!d || typeof d.id !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(d.id)) continue;
      const card = d.card || {};
      push({
        id: "presentation:" + d.id, k: "presentation", t: txt(card.title) || txt(d.title), tl: lang, o: txt(card.title, other), ol: other,
        s: snippet(txt(card.summary), 200),
        x: [txt(card.audience), txt(card.audience, other), snippet(txt(card.summary, other), 200), txt(d.short), both("search.kw.presentation")]
          .filter(Boolean).join(" "),
        u: `/orientation/#pres-${d.id}`, u2: `/orientation/?present=${d.id}`, src: "neta",
      });
    }
  });
  if (EMPTY() || !db) return out;

  /* ---- articles (Grapevine & La Viña) ----
     Byline `a` = writer · hometown (the place only when geo.py recognised it, in the page
     language). Writers from Texas are also found by their county and "Texas" / "Area 65". */
  const bothVars = (k, vars) => [tryKey(helpers, k, "en", vars), tryKey(helpers, k, "es", vars)].filter(Boolean).join(" ");
  safely("articles", () => {
    for (const it of db.articles?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      const g = ex.geo || {};
      const lv = ex.publication === "lv" || it.source === "lavina" || it.category === "lv";
      const place = squish(it.i18n?.author_location?.[lang] || g[`label_${lang}`] || "");
      const placeOther = squish(it.i18n?.author_location?.[lang === "es" ? "en" : "es"] || g[`label_${lang === "es" ? "en" : "es"}`] || "");
      const texan = TEXAS_SCOPES.has(g.scope);
      push({
        id: it.id, k: "article", t: P(it, "title"), o: it.title,
        s: snippet(P(it, "summary")),
        a: [squish(ex.author), place].filter(Boolean).join(" · "),
        x: uniq([P(it, "issue_label"), P(it, "topic"), P(it, "section"), ...["issue_label", "topic", "section"].flatMap((f) => [it.i18n?.[f]?.en, it.i18n?.[f]?.es]), ex.issue_label, ex.topic, lv ? "La Viña" : "Grapevine",
          fold(placeOther) !== fold(place) ? placeOther : "",
          texan && g.county ? bothVars("search.county", { county: g.county }) : "",
          g.scope === "neta65" ? both("search.kw.writer_neta65") : g.scope === "texas" ? both("search.kw.writer_texas") : ""].map(squish)),
        u: it.url, d: ymd(helpers, it.date), l: it.lang, src: lv ? "lv" : "gv",
        im: it.image || "", m: mach(it), n: it.is_new, pw: ex.free === false,
      });
    }
  });

  /* ---- Since round 37: each magazine's CURRENT issue (/read/'s first issue of each: read.js groupIssues, issueView —
     the card at /read/#gv-current, #lv-current) — found by its theme in both languages, its month and "current issue" /
     "número actual" (search.kw.issue) ---- */
  safely("issues", () => {
    for (const pub of ["gv", "lv"]) {
      const issue = groupIssues(db.articles, pub)[0];
      if (!issue) continue;
      const v = issueView(issue, lang, helpers);
      const w = issueView(issue, other, helpers);
      const mag = pub === "lv" ? "La Viña" : "AA Grapevine";
      push({
        id: "issue:" + pub, k: "issue", t: v.topic || v.label || mag, tl: v.topic ? v.topicLang : lang,
        o: w.topic && fold(w.topic) !== fold(v.topic) ? w.topic : "", ol: w.topicLang,
        s: uniq([T("read.current_issue"), mag, v.label]),
        x: uniq([w.label, snippet(v.description, 200), both("search.kw.issue"), pub === "lv" ? "La Viña" : "Grapevine"], " "),
        // (no `d`: the month is in the line — La Viña's issue spans two, "Noviembre / Diciembre 2026")
        u: `/read/#${pub}-current`, l: pub === "lv" ? "es" : "en",
        src: pub, im: v.cover || "", m: !!v.topicMachine,
      });
    }
  });

  /* ---- editorial themes (calls for stories) — only the ones still open, like /contribute/ ---- */
  safely("editorial", () => {
    const today = new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date()); // YYYY-MM-DD in Central time
    for (const it of db.editorial?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      const deadline = ex.deadline ? ymd(helpers, ex.deadline) : "";
      if (deadline && deadline < today) continue; // closed
      if (!deadline && ex.evergreen !== true && ex.issue_key && String(ex.issue_key) < today.slice(0, 7)) continue; // past issue
      const lv = ex.publication === "lv" || it.category === "lv";
      // La Viña's issue by the site's one name for it ("May–June 2027", as /contribute/ shows the same deadline)
      const issue = (lv && issueName(ex.issue_key, "lv", lang)) || P(it, "issue_label") || ex.issue_label;
      push({
        id: it.id, k: "topic", t: P(it, "title"), o: it.title,
        s: [issue, deadline ? T("search.deadline", { date: helpers.fmtDate(deadline, lang, "medium") }) : T("search.topic_open")].filter(Boolean).join(" · "),
        x: both("search.kw.contribute"),
        // No `d`: the deadline is in the snippet (a date in the meta line would read as a publish date).
        u: "/contribute/", l: it.lang, src: lv ? "lv" : "gv", m: mach(it),
      });
    }
  });

  /* ---- PDFs + committee documents (same titles and types as the Library) ---- */
  safely("library", () => {
    for (const d of libraryDocs(db, lang, helpers)) {
      const kitWords = d.kit ? both(`library.col.${d.kit}-kit`) : "";
      push({
        // d.o is empty when d.t is the original title (language d.tl); d.l is the document's language.
        id: d.id, k: d.k === "pdf" ? "pdf" : d.k, t: d.t, o: d.o, ol: d.tl, tl: d.o ? lang : d.tl,
        s: uniq([d.ev ? T("library.event_on", { date: helpers.fmtDate(d.ev, lang, "medium") }) : "", catLabel(helpers, d.c, lang), d.r && d.r.title]),
        x: [d.fname && !fold(d.t + d.o).includes(fold(d.fname)) ? d.fname : "", d.alt || "", kitWords].filter(Boolean).join(" "),
        u: d.u, d: d.d, dp: d.dp, l: d.l, src: d.s, im: d.th && (d.s === "neta" || d.th.startsWith("/")) ? d.th : "", m: d.m, n: d.n && !d.or, z: d.or,
      });
    }
  });

  /* ---- podcast episodes ----
     A result opens the episode in the site's own player (/listen/?ep=<id>: loaded, its row shown — media.js
     openLinked); `u2`, the podcast host's page for it, is the second choice ("Episode page ↗", search.js). An id
     the address can't carry keeps the host's page as the one link. */
  safely("episodes", () => {
    for (const it of db.episodes?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      const host = it.url || ex.player_url || ex.link || "";
      const own = /^[\w:.-]{1,80}$/.test(String(it.id || ""));
      // a weekly open meeting's episode called only by its show's name (La Viña's): "La Viña Open Meeting, November 5,
      // 2026" — its meeting and date (media.js meetingTitleParts), the feed's title stays the original
      const mt = meetingTitleParts(it);
      push({
        id: it.id, k: "episode", t: mt ? `${T(mt.label)}, ${helpers.fmtDate(mt.date, lang, "medium")}` : P(it, "title"), o: it.title,
        s: snippet(P(it, "summary"), 200),
        x: ex.show_name || "",
        u: own ? `/listen/?ep=${it.id}` : host, u2: own ? host : "",
        d: ymd(helpers, it.date), l: it.lang, src: "podcast", m: mach(it), n: it.is_new,
      });
    }
  });

  /* ---- YouTube videos ---- */
  safely("videos", () => {
    for (const it of db.videos?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      push({
        id: it.id, k: "video", t: P(it, "title"), o: it.title,
        s: snippet(P(it, "summary")),
        x: (ex.playlists || []).join(" · "),
        u: it.url, d: ymd(helpers, it.date), dp: ex.date_approx ? "m" : "", l: it.lang, src: it.category === "lv" ? "lv" : "youtube",
        yt: ex.video_id || "", im: ex.video_id ? "" : it.image || "", m: mach(it), n: it.is_new,
      });
    }
  });

  /* ---- Instagram posts (caption is the useful text) — since round 37 without its sentences that say how to join a
     meeting ("Meeting ID Zoom: 815 9593 1777", a passcode, a Zoom or Meet link: committee.js withoutJoinDetails): the
     index is a file anyone can read; the post itself, one tap away, still has them ---- */
  // (on the caption as written, line by line — then made one line, as P does)
  const noJoin = (s) => squish(typeof committee.withoutJoinDetails === "function" ? committee.withoutJoinDetails(s) : s);
  safely("instagram", () => {
    for (const it of db.instagram?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      const cap = noJoin(helpers.pickLang(it, "summary", lang));
      const first = cap.split(/(?<=[.!?¡¿])\s|\n/)[0] || "";
      const acct = ex.account === "lv" || it.category === "lv" ? "lv" : "gv";
      // The title is a caption line: in the page language if the caption was translated.
      const shownOrig = first ? fold(cap) === fold(noJoin(it.summary)) : fold(P(it, "title")) === fold(it.title);
      push({
        id: it.id, k: "post",
        t: first ? snippet(first, 90) : noJoin(P(it, "title")),
        tl: shownOrig ? it.lang : lang,
        o: "",
        s: snippet(cap, 170),
        x: "@" + (ex.username || "") + " instagram",
        u: it.url, d: ymd(helpers, it.date), l: it.lang, src: acct, im: ex.thumb || "", m: mach(it), n: it.is_new,
      });
    }
  });

  /* ---- Committee: Drive photo albums (one entry per album, like /photos/) ---- */
  safely("albums", () => {
    let albums = null;
    if (typeof committee.photoAlbums === "function") {
      try { albums = committee.photoAlbums(db.drive?.items || [], lang); } catch { albums = null; }
    }
    if (albums) {
      for (const a of albums) {
        // A magazine's covers of one year ("Grapevine covers 2019" / "Portadas de Grapevine 2019"; committee.js
        // photoAlbums): one entry, found by any of its issues in either language ("March 2019", "Marzo 2019", La
        // Viña's "Mayo–Junio 2019"), linking to that album with the page's filter set (/photos/?mag=gv&year=2019
        // #covers-gv-2019) — never one entry per cover
        if (a.covers) {
          const c = a.covers;
          const issues = a.items.flatMap((p) => (p.cover && typeof committee.coverIssueLabel === "function"
            ? ["en", "es"].map((l) => committee.coverIssueLabel(p.cover, l)) : [p.label]));
          push({
            id: "covers:" + c.id, k: "album", t: a.title,
            s: T(a.count === 1 ? "committee.photos.covers_count_one" : "committee.photos.covers_count", { n: fmtNum(a.count, lang) }),
            x: uniq([...issues, c.name, c.year ? String(c.year) : "", both("committee.photos.covers_title"), "cover covers portada portadas", both("nav.photos")], " "),
            u: `/photos/?mag=${c.pub}${c.year ? "&year=" + c.year : ""}#${c.id}`, d: ymd(helpers, a.newest), src: c.pub,
            im: (a.cover && a.cover[0] && a.cover[0].thumb) || "", n: a.hasNew,
            // lw: ranked a little lower (search.js boostDocument × 0.7) — its keywords name all twelve months, so a
            // search for "december" found 94 cover years before the month's events, issue and toolkit
            lw: 1,
          });
          continue;
        }
        push({
          id: "album:" + a.slug, k: "album", t: a.title,
          s: [(a.count === 1 ? T("search.photos_one") : T("search.photos_n", { n: fmtNum(a.count, lang) })), a.panelLabel].filter(Boolean).join(" · "),
          x: both("nav.photos"),
          u: "/photos/#" + a.slug, d: ymd(helpers, a.newest), src: "neta",
          im: (a.cover && a.cover[0] && a.cover[0].thumb) || "", n: a.hasNew,
        });
      }
      return;
    }
    const fallback = new Map();
    for (const it of db.drive?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      if (!(it.kind === "photo" || it.kind === "video_file" || ex.is_image || ex.is_video)) continue;
      const name = ex.album || ex.panel_label || "photos";
      if (!fallback.has(name)) fallback.set(name, { name, n: 0, cover: "", date: "", panel: ex.panel_label || "" });
      const a = fallback.get(name);
      a.n++;
      if (!a.cover) a.cover = ex.thumb_url || it.image || "";
      const dd = ymd(helpers, it.date);
      if (dd > a.date) a.date = dd;
    }
    for (const a of fallback.values()) {
      const sl = "album-" + slug(a.name, 50);
      push({
        id: "album:" + sl, k: "album", t: a.name === "photos" ? T("search.album_loose") : a.name,
        s: [(a.n === 1 ? T("search.photos_one") : T("search.photos_n", { n: fmtNum(a.n, lang) })), a.panel].filter(Boolean).join(" · "),
        x: both("nav.photos"),
        u: "/photos/#" + sl, d: a.date, src: "neta", im: a.cover,
      });
    }
  });

  /* ---- Committee: the bulletin's posts (expired ones are hidden on the page, so skip them) ---- */
  safely("announcements", () => {
    const today = new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date()); // YYYY-MM-DD in Central time
    const list = typeof committee.announcementList === "function"
      ? committee.announcementList(db.announcements?.items || [])
      : (db.announcements?.items || []).filter((it) => ok(it) && !(it.extra?.expires && String(it.extra.expires).slice(0, 10) < today));
    for (const it of list) {
      if (!ok(it)) continue;
      // The data gives "/bulletin/#<slug>" (the card's id; db.js turns an older "/announcements/#…" into
      // it); older records: the bulletin page's own anchor.
      const u = isInternal(it.url) && it.url.includes("#") ? it.url
        : "/bulletin/#" + (it._anchor || "ann-" + slug(String(it.id).replace(/^ann:/, ""), 70));
      push({
        id: it.id, k: "announcement", t: P(it, "title"), o: it.title,
        s: snippet(P(it, "summary") || P(it, "body_md")),
        u, d: ymd(helpers, it.date), l: it.lang, src: "neta", m: mach(it), n: it.is_new,
      });
    }
  });

  /* ---- Events (monthly committee meetings are covered by the Meeting page) ----
     Since round 37 every event /events/ lists has a page of its own (eleventy/event-pages.js eventPagePlan — the pages
     the build writes, read at the build's own moment, site.built): a result opens it (committee.js eventPageHref with
     the plan; its path in the page language, as every `u`), a monthly recurring event (config/site.yml
     `recurring_events:`) its SERIES' page (/events/series/<key>/: its next dates, how to join) when the plan has one.
     A series is ONE entry: its next date; its past dates are left out (/events/ does not list them). An event the plan
     has no page for (an anchor unfit for an address) keeps its card on /events/ while it is upcoming or among the
     PAST_EVENTS_SHOWN past events the "Past events" list shows (that list opens by itself when a link points into it),
     else its own page elsewhere (e.g. the La Viña calendar), else no entry. An upcoming CANCELLED event (content/events
     `cancelled: true` — db.events.cancelled) has one entry too, "Cancelled: <title>, <day>" (its notice page,
     eleventy/cancelled-pages.js, while it is to come), ranked low (z): a search for "garland" says it is off.
     Its words (`x`, searched, never shown): its summary without how to join (a meeting ID or code, an online link:
     committee.js withoutJoinValues, withoutJoinDetails — the index is a public file), its day of the week, city and
     organizer (never the committee itself: every event of ours is the committee's), "flyer volante" when it has one,
     and its kind in both languages ("Writing workshop Taller de escritura": event-pages.js eventKind). */
  // The events in this language as /events/ lists them, at the build's moment, with the plan of their pages — worked
  // out once (the events, their flyers and the next meeting read them); null without committee.js, or when it cannot
  // read the events (then the events have their plain /events/#… entries, as before round 37, and every flyer the
  // Portfolio's flyers).
  let evCtx;
  const eventsNow = () => {
    if (evCtx !== undefined) return evCtx;
    evCtx = null;
    if (typeof committee.normalizeEvents !== "function") return evCtx;
    const built = Date.parse(String(site?.built || ""));
    const now = Number.isFinite(built) ? new Date(built) : new Date();
    let evs;
    try { evs = committee.normalizeEvents(db.events?.items || [], site || {}, lang, { now }); } catch { return evCtx; }
    let plan = null;
    if (typeof eventPages.eventPagePlan === "function") {
      // (the same call as the event pages' templates — db.events.items, site, the site's languages, the cancelled list —
      // so it is the one plan of the build, worked out once: eventPagePlan's memo)
      try { plan = eventPages.eventPagePlan(db.events?.items || [], site || {}, siteLanguages, { cancelled: db.events?.cancelled }); } catch { plan = null; }
    }
    evCtx = { now, evs, plan };
    return evCtx;
  };
  // a path in the page language → the same path language-neutral (push adds the page language's /es once)
  const neutral = (p) => (lang !== "en" && typeof p === "string" && p.startsWith(`/${lang}/`) ? p.slice(lang.length + 1) : p);
  const eventsRoot = "/events/";
  // A series' page (/[es/]events/series/<key>/, src/pages/event-share-series.njk) is linked only when the build writes
  // it: `extra.pages`, the addresses of the build's pages (the filters hand over the build's own: builtUrls, from
  // "eleventy.contentMap"), has it; given none (outside a build: a test, a script), the plan's word is taken. Without its
  // page, a series' date opens its own page — never a page that is not there. (The [search] check, eleventy/seo-check.js,
  // still flags a series' page the sitemap lists and no entry links.)
  const written = extra?.pages && typeof extra.pages[Symbol.iterator] === "function"
    ? new Set([...extra.pages].map((p) => (typeof p === "string" ? p : p && p.url)).filter((u) => typeof u === "string")) : null;
  /** A series' page for this key in the page language, when the plan has one and the build writes it — else "". */
  const hubOf = (key, ctx) => {
    if (!key || !ctx || !ctx.plan || typeof committee.seriesPagePath !== "function") return "";
    const hub = committee.seriesPagePath(key, lang);
    return ctx.plan.byPath && ctx.plan.byPath[hub] && (!written || written.has(hub)) ? hub : "";
  };
  /** Where an event's result goes (a language-neutral path), or "" — its series' page for a monthly series' date (when
   *  the plan has one and the build writes it), else its own page (eventPageHref with the plan), else "" (the caller
   *  falls back to the card). */
  const pageOf = (ev, ctx) => {
    if (!ctx || !ctx.plan) return "";
    const hub = hubOf(ev.recurring ? String(ev.series || ev.item?.extra?.series || "") : "", ctx);
    if (hub) return neutral(hub);
    const href = typeof committee.eventPageHref === "function"
      ? neutral(committee.eventPageHref(ev, lang, { plan: ctx.plan, now: ctx.now }))
      : "";
    // (the card, "/events/#…", or /events/ itself: no page of its own)
    return href && href !== eventsRoot && !href.startsWith(eventsRoot + "#") ? href : "";
  };
  const LOC_OF = { en: "en-US", es: "es-US" };
  /** An event's day(s) of the week in both languages ("Saturday sábado"; over several days: its first and last). */
  const weekdays = (ev) => {
    const days = [];
    const add = (ms, ymdText, allDay) => {
      const d = allDay ? new Date(`${ymdText}T12:00:00Z`) : new Date(ms);
      if (Number.isNaN(d.getTime())) return;
      for (const l of ["en", "es"]) {
        try { days.push(new Intl.DateTimeFormat(LOC_OF[l], { weekday: "long", timeZone: allDay ? "UTC" : TZ }).format(d)); } catch { /* none */ }
      }
    };
    add(ev.startMs, ev.startYmd, !!ev.allDay);
    if (ev.multiDay) add(ev.allDay ? NaN : ev.endMs - 1, ev.endYmd, !!ev.allDay);
    return uniq(days, " ");
  };
  /** (round 37's fixer) An event over several days, its first and last day in full in both languages ("March 19, 2027
   *  March 21, 2027 19 de marzo de 2027 21 de marzo de 2027"): the line it shows gives them in short ("Fri, Mar 19 – Sun,
   *  Mar 21, 2027"), and "march", "marzo", "june 25", "asamblea de junio" must still find it. Searched, never shown. */
  const fullDays = (ev) => {
    if (!ev || !ev.multiDay) return "";
    const days = [];
    const at = ev.allDay ? [`${ev.startYmd}T12:00:00Z`, `${ev.endYmd}T12:00:00Z`] : [ev.startMs, ev.endMs - 1];
    for (const l of ["en", "es"]) {
      for (const v of at) {
        const d = new Date(v);
        if (Number.isNaN(d.getTime())) continue;
        try { days.push(new Intl.DateTimeFormat(LOC_OF[l], { month: "long", day: "numeric", year: "numeric", timeZone: ev.allDay ? "UTC" : TZ }).format(d)); } catch { /* none */ }
      }
    }
    return uniq(days, " ");
  };
  /** An event's city ("Fort Worth"): the data's, else its place's (committee.js eventPlace), else "". */
  const cityOf = (ev) => {
    const x = ev.item?.extra || {};
    if (x.city) return squish(x.city);
    if (!ev.location || typeof committee.eventPlace !== "function") return "";
    try { return squish(committee.eventPlace(String(ev.location), x)?.address?.addressLocality || ""); } catch { return ""; }
  };
  /** Who holds it, in both languages ("District 87 La Viña Committee", the Area's name …) — never the committee itself
   *  (committee.js eventOrganizer: the Event's organizer). */
  const organizerOf = (ev) => {
    if (typeof committee.eventOrganizer !== "function") return "";
    const names = [];
    for (const l of ["en", "es"]) {
      try {
        const org = committee.eventOrganizer(ev, site || {}, l);
        if (org && org.name && !(typeof committee.isCommitteeOrganizer === "function" && committee.isCommitteeOrganizer(org, site || {}))) names.push(org.name);
      } catch { /* none */ }
    }
    return uniq(names, " ");
  };
  /** Its kind in both languages ("Writing workshop Taller de escritura"): its page's kind (the plan's), else eventKind. */
  const kindWords = (ev, ctx) => {
    const page = ctx?.plan?.byAnchor?.[ev.anchor]?.[lang];
    let k = page && page.kind;
    if (!k && typeof eventPages.eventKind === "function") { try { k = eventPages.eventKind(ev, site || {}); } catch { k = null; } }
    return k && k.label ? both(k.label) : "";
  };
  /** A summary as the index may keep it: without a sentence that says how to join or gives the event's own way in. */
  const safeSummary = (ev, text) => {
    let s = String(text ?? "");
    if (typeof committee.withoutJoinValues === "function") s = committee.withoutJoinValues(s, [ev.meetingId, ev.online, ev.item?.extra?.meeting_id, ev.item?.extra?.online_url]);
    if (typeof committee.withoutJoinDetails === "function") s = committee.withoutJoinDetails(s);
    return s;
  };
  safely("events", () => {
    const ctx = eventsNow();
    const now = ctx ? ctx.now.getTime() : Date.now();
    let evs = ctx ? ctx.evs : null;
    const anchored = !!evs; // anchors known = the same ones /events/ renders
    if (!evs) {
      evs = (db.events?.items || []).filter((it) => ok(it) && it.kind === "event").map((it) => {
        const t0 = helpers.toDate(it.extra?.end || it.extra?.start || it.date);
        return {
          item: it, committee: it.category === "committee", recurring: it.category === "recurring", anchor: "ev-" + slug(String(it.id).replace(/^ev:/, "")),
          past: it.extra?.past === true || (!!t0 && t0.getTime() < now - DAY), link: it.url || "", linkExternal: /^https?:/.test(it.url || ""),
        };
      });
    }
    // Same selection as events.njk: `all | where("past", true) | whereNot("committee", true) |
    // whereNot("recurring", true) | reverse | limit(40)` (normalizeEvents sorts soonest first, so the
    // newest past events are the last ones).
    const pastRows = new Set(anchored ? evs.filter((e) => e.past === true && e.committee !== true && e.recurring !== true).slice(-PAST_EVENTS_SHOWN).map((e) => e.id) : []);
    const series = new Set(); // recurring events already indexed (by their next date)
    for (const ev of evs) {
      const it = ev.item;
      if (!it || !ok(it) || ev.committee || it.category === "committee") continue;
      // (a cancelled one has its own entry below, at its notice page)
      if (ev.cancelled === true || it.extra?.cancelled === true) continue;
      const recurring = it.category === "recurring";
      if (recurring) {
        const k = String(it.extra?.series || it.id);
        if (ev.past || series.has(k)) continue;
        series.add(k);
      }
      const ex = it.extra || {};
      // The card's anchor on /events/. (Without committee.js the anchor is a guess, so the
      // data's own "/events/#<slug>" link wins then.)
      const card = !anchored && isInternal(it.url) && it.url.includes("#") ? it.url : "/events/#" + ev.anchor;
      let u = anchored ? pageOf(ev, ctx) : "";
      if (!u && (!ev.past || pastRows.has(ev.id))) u = card;
      else if (!u && /^https?:\/\//.test(it.url || "")) u = it.url;
      if (!u) continue;
      const start = ex.start || it.date;
      // A recurring event (and a content/events file with title_es / summary_es) is written by the
      // committee in both languages: no "EN" badge on the Spanish page (search.js shows one when `l`
      // differs), and "every month" / "cada mes" finds a recurring one too. Its repeat line is the one
      // the calendars carry (committee.js recurrenceText, with its time zone).
      const own = typeof committee.ownLangs === "function"
        ? committee.ownLangs(it).includes(lang)
        : (recurring || it.category === "manual") && !(it.machine || []).includes(lang) && fold(P(it, "title")) !== fold(it.title);
      // The card's own date line: a RANGE for an event over several days ("Fri, Mar 19 – Sun, Mar 21, 2027"),
      // and the place in the page language (content/events `location_es` → i18n.location) — or, for an event
      // with no place that is held online (La Viña's monthly workshop on Zoom), "Online on Zoom" as on its card.
      // A monthly series has its repeat line in the date's place ("Every fourth Thursday of the month · 2:00 –
      // 3:00 PM Central time · Online on Zoom"): the result's meta line already shows its next date (`d`), and
      // with that date in the line too, the two lines a phone shows of it (library.css .ss-snippet) cut its time
      // zone mid-word ("hora de…"). Without the date the zone shows in full on a 360–390px phone (at 320px the
      // English line stops at "PM Central…"), but the place can still be cut there ("· Online on…" / "· En línea
      // por…"): the whole line fits in two lines from about 412px. (Its date is still searched: see `x` below.)
      const when = ev.multiDay && ev.rangeLabel ? ev.rangeLabel : helpers.fmtDate(start, lang, "medium");
      const online = ev.isOnline || !!ex.online_url;
      const platform = ev.platform || ex.platform || "";
      const where = ev.location || P(it, "location") || ex.location || [ex.city, ex.state].filter(Boolean).join(", ")
        || (online ? (platform ? T("committee.events.online_on", { platform }) : T("committee.events.online")) : "");
      const tentative = ev.tentative === true || ex.tentative === true;
      // whose event it is: the GV / LV calendars are theirs, and so is an event La Viña or Grapevine holds
      // (extra.host: La Viña's monthly workshop); a NETA 65 feed (neta65.org) and the committee's own are ours
      const host = ex.host === "lv" || ex.host === "gv" ? ex.host : "";
      // a monthly booth (the CityWide Dallas booth) is also found by "booth" / "literature table" / "mesa de
      // literatura" — not every monthly event: La Viña's workshop on Zoom is no booth
      const booth = recurring && eventTone(it) === "booth";
      // our own online meeting (a monthly series of ours with a link and no place: the Grapevine Meeting on Google
      // Meet) is found by "online meeting", "Google Meet", "first Wednesday" … — never by the words of the Grapevine
      // meetings list (the AA groups that read Grapevine: committee.gvm.search_kw), which it is not part of
      const ownOnline = recurring && !host && online && !(ev.location || ex.location);
      push({
        id: it.id, k: "event", t: tidyTitle(P(it, "title") || ev.title), o: tidyTitle(it.title), ol: it.lang,
        s: [recurring ? (ev.recurrence || P(it, "recurrence_label")) : when, where].filter(Boolean).join(" · "),
        // A series' next date left the line shown above (for a phone's sake), but it must still find the series —
        // "october", "oct 22", "22 octubre" find a one-off event by the date in its line. The meta line's `d` is
        // only shown, never searched (search.js), so the date goes with the keywords: searched, never shown.
        x: uniq([snippet(safeSummary(ev, P(it, "summary")), 120), recurring ? when : "", recurring ? both("search.kw.recurring") : "",
          booth ? both("search.kw.booth") : "", ownOnline ? both("search.kw.own_online") : "",
          tentative ? both("committee.events.tentative") : "",
          anchored ? weekdays(ev) : "", anchored ? cityOf(ev) : "", anchored ? organizerOf(ev) : "",
          ev.flyer ? both("search.kw.flyer") : "", anchored ? kindWords(ev, ctx) : "", anchored ? fullDays(ev) : "",
          // (round 37's fixer) "events", "eventos", "upcoming events", "próximos eventos" find every event — the
          // magazines' calendars' and ours alike —, "upcoming" only the ones still to come
          both("search.kw.event"), ev.past ? "" : both("search.kw.upcoming")].map(squish), " "),
        u, d: ymd(helpers, start), l: own ? lang : it.lang,
        src: host || (it.category === "lv-calendar" ? "lv" : it.category === "gv-calendar" ? "gv" : "neta"), m: mach(it), z: ev.past,
        // tb = "Details to be confirmed" (content/events `tentative: true`): search.js shows the badge
        ...(tentative && !ev.past ? { tb: 1 } : {}),
      });
    }
    // …and every series' page the plan has (and the build writes) gets an entry, even one whose only date to come is a
    // date the host moved (ev.seriesOf: its own entry opens that date's page): the series' title, its rule, its next date
    const linked = new Set(out.filter((e) => e.k === "event").map((e) => e.u));
    for (const hub of ctx && ctx.plan ? ctx.plan.hubs || [] : []) {
      if (hub.lang !== lang || linked.has(hub.path) || hubOf(hub.key, ctx) !== hub.path) continue;
      const s = hub.series || {}, next = hub.next || {};
      push({
        id: "series:" + hub.key, k: "event", t: tidyTitle(s.title || next.title || hub.key), tl: lang,
        s: [s.recurrence, next.location || (next.isOnline ? (next.platform ? T("committee.events.online_on", { platform: next.platform }) : T("committee.events.online")) : "")]
          .filter(Boolean).join(" · "),
        x: uniq([snippet(safeSummary(next, s.summary || next.summary), 120), next.dateLabel, both("search.kw.recurring"), weekdays(next),
          kindWords(next, ctx), both("search.kw.event"), both("search.kw.upcoming")].map(squish), " "),
        u: neutral(hub.path), d: next.startYmd || "", src: next.host === "lv" || next.host === "gv" ? next.host : "neta",
      });
    }
  });

  /* ---- Since round 37: an upcoming CANCELLED event (content/events `cancelled: true`) — one entry, at its notice page
     (eleventy/cancelled-pages.js cancelledPages: only while it is to come, at the address its page had): "Cancelled:
     <title>, <day>" (committee.js cancelledPageMeta — the page's own title and description), ranked low (z), found by
     its title in both languages, its city, day of the week and "cancelled" / "cancelado" ---- */
  safely("cancelled events", () => {
    if (typeof cancelledNotices.cancelledPages !== "function") return;
    const ctx = eventsNow();
    for (const c of cancelledOnce(db.events?.cancelled || EMPTY_LIST, db.events?.items || EMPTY_LIST, site)) {
      if (c.lang !== lang || !c.meta) continue;
      const ev = c.ev || {};
      const it = ev.item || {};
      const ex = it.extra || {};
      const own = typeof committee.ownLangs === "function" ? committee.ownLangs(it).includes(lang) : false;
      push({
        id: "cancelled:" + it.id, k: "event", t: c.meta.title, tl: lang, s: c.meta.description,
        x: uniq([tidyTitle(it.title), tidyTitle(P(it, "title")), both("evcancel.ics_prefix"), weekdays(ev), cityOf(ev), organizerOf(ev),
          kindWords(ev, ctx), fullDays(ev), both("search.kw.event")].map(squish), " "),
        u: neutral(c.path), d: ymd(helpers, ex.start || it.date), l: own ? lang : it.lang,
        src: ex.host === "lv" || ex.host === "gv" ? ex.host : "neta", z: 1,
      });
    }
  });

  /* ---- Since round 37: the NEXT COMMITTEE MEETING (/meetings/#next-meeting-h, the countdown's card) — its day, time
     and platform (never its guest speaker's name, its link or code), found by "next meeting" / "próxima reunión"
     (search.kw.next_meeting). The date the page itself shows: the meeting rule's next one (as cmNextMeeting), at the
     build's moment; the platform the card's "Join on Google Meet" names (config/site.yml meeting: — committee.js
     meetingJoin; a committee meeting's shaped event has none: its join details live on /meetings/ alone) ---- */
  safely("next meeting", () => {
    if (typeof committee.normalizeEvents !== "function" || !seenPage.has("/meetings/")) return;
    const ctx = eventsNow();
    const next = committee.normalizeEvents([], site || {}, lang, { monthsBack: 0, monthsAhead: 14, now: ctx ? ctx.now : new Date() })
      .find((e) => e.committee && !e.past);
    if (!next) return;
    const platform = (typeof committee.meetingJoin === "function" ? committee.meetingJoin(site?.meeting, lang).platform : "") || next.platform || "";
    const where = platform ? T("committee.events.online_on", { platform }) : T("committee.events.online");
    // (mid-sentence in Spanish, the day of the week takes no capital: "Próxima reunión del comité: miércoles, 16 de
    // diciembre de 2026" — English keeps its "Wednesday")
    let date = next.dateLabel || helpers.fmtDate(next.startIso, lang, "long");
    if (lang === "es" && date) date = date.charAt(0).toLowerCase() + date.slice(1);
    push({
      id: "meeting:next-committee", k: "meeting", t: T("search.next_meeting", { date }), tl: lang,
      s: [next.timeLabel, where].filter(Boolean).join(" · "),
      // (and the committee's name, config/site.yml committee: "NETA 65 Grapevine & La Viña Committee")
      x: [both("search.kw.next_meeting"), both("committee.meetings.committee_title"), squish(site?.committee || "")].filter(Boolean).join(" "),
      u: "/meetings/#next-meeting-h", d: next.startYmd || "", src: "neta", ic: "calendar-clock",
    });
  });

  /* ---- Since round 37: the Drive's FLYERS (the Portfolio's flyers tab — pictures, never a Library document: those have
     their entries above) — each found by its title in both languages and "flyer" / "volante" (search.kw.flyer), opening
     the page of the event it is the flyer of (normalizeEvents' ev.flyer: its own page, a monthly series' page, or
     /meetings/#committee-meeting for a committee meeting's) — the soonest one to come, else the latest that is over —,
     else the weekly open meeting or store offer it is the flyer of, else the Portfolio's flyers
     (/portfolio/#docs-flyers). A flyer only cancelled events use is not in db.drive any
     more (src/_data/db.js: eleventy/cancelled-events.js hideCancelledFlyers).
     A flyer is a picture of what its event's own entry already says, so it never comes before it: its date is its
     EVENT's (`d`, the recency boost of search.js — never the day it was put on the Drive), it ranks low once its event
     is over (`z`, as the event itself), and search.js ranks every flyer lower (×0.5) unless the words searched are
     "flyer" / "volante" (kit.siteIndex: FLYER_TERM) — "writing workshop" lists the next workshop before any flyer, and
     "committee meeting" the next meeting before the guest speakers' flyers. A flyer whose only event is a date of a
     monthly series that the host moved and that is over (ev.seriesOf) opens its series' page, not that date's ---- */
  safely("flyers", () => {
    const ctx = eventsNow();
    const FLYER_CATS = new Set(["flyers", "flyer", "volantes"]);
    const fileId = (url) => (String(url || "").match(/\/d\/([\w-]{10,})/) || String(url || "").match(/[?&]id=([\w-]{10,})/) || [])[1] || "";
    const meetingPath = committee.COMMITTEE_MEETING_PATH || "/meetings/#committee-meeting";
    const target = new Map(); // Drive file id → { u, ev, rank }
    for (const ev of ctx ? ctx.evs : []) {
      const fid = fileId(ev.flyer && ev.flyer.view);
      if (!fid || ev.cancelled === true) continue;
      const u = ev.committee ? meetingPath
        : (ev.past && ev.seriesOf ? neutral(hubOf(String(ev.seriesOf), ctx)) : "") || pageOf(ev, ctx) || (!ev.past && ev.anchor ? "/events/#" + ev.anchor : "");
      if (!u) continue;
      // (the soonest event still to come first, else the latest one over)
      const rank = ev.past ? [1, -(ev.startMs || 0)] : [0, ev.startMs || 0];
      const had = target.get(fid);
      if (!had || rank[0] < had.rank[0] || (rank[0] === had.rank[0] && rank[1] < had.rank[1])) target.set(fid, { u, ev, rank });
    }
    // …else a weekly open meeting's flyer, its card on /meetings/#weekly-open (config/site.yml grapevine_weekly_open /
    // lavina_weekly_open flyer_match: committee.js weeklyFlyer's rule), or a store offer's banner, its offer on /shop/
    const elsewhere = (fid, u) => { if (fid && !target.has(fid)) target.set(fid, { u, ev: null, rank: [2, 0] }); };
    // (every flyer its pattern finds, since round 37's fixer — not only the newest, which the card shows: an earlier
    // one still on the Drive, "Nueva reunión abierta de La Viña …", is about the same meeting)
    for (const cfg of [site?.grapevine_weekly_open, site?.lavina_weekly_open]) {
      if (!cfg || !cfg.flyer_match || typeof committee.driveMatch !== "function") continue;
      for (const f of committee.driveMatch(db.drive?.items || [], cfg.flyer_match, "flyers", 50)) {
        elsewhere((f.extra && f.extra.file_id) || fileId(f.url), "/meetings/#weekly-open");
      }
    }
    for (const o of shopOffers(site || {}, lang, db.drive?.items || [], (k, l, v) => helpers.translateKey(k, l, v))) {
      for (const st of o.stores || []) if (st.banner) elsewhere(fileId(st.banner.view) || fileId(st.banner.src), `/shop/#offers-${o.key}`);
    }
    for (const it of db.drive?.items || []) {
      if (!ok(it) || it.kind !== "photo" || !FLYER_CATS.has(String(it.category || "").toLowerCase())) continue;
      const ex = it.extra || {};
      const tg = target.get(ex.file_id || fileId(it.url));
      const ev = tg ? tg.ev : null;
      const when = ev ? (ev.recurring ? String(ev.recurrence || "").split(" · ")[0] : ev.multiDay && ev.rangeLabel ? ev.rangeLabel
        : helpers.fmtDate(ev.item?.extra?.start || ev.item?.date, lang, "medium")) : "";
      push({
        id: "flyer:" + it.id, k: "flyer", t: P(it, "title"), o: it.title,
        s: ev ? uniq([tidyTitle(ev.title), when]) : squish(ex.panel_label || ""),
        x: uniq([both("search.kw.flyer"), it.i18n?.title?.en, it.i18n?.title?.es, ev ? tidyTitle(ev.item?.title) : ""].map(squish), " "),
        // (its event's day — a flyer of none: the day it was put on the Drive)
        u: tg ? tg.u : "/portfolio/#docs-flyers", d: ymd(helpers, ev ? ev.item?.extra?.start || ev.item?.date : it.date), l: it.lang, src: "neta",
        im: ex.thumb_url || it.image || "", m: mach(it), n: it.is_new, z: !!(ev && ev.past),
      });
    }
  });

  /* ---- Since round 37: the MONTH TOOLKITS (/monthly/<YYYY-MM>/: this month and the 12 after it — the window the pages
     are written for, monthly.js windowKeys) — each by its page's own title and description ("Monthly toolkit: December
     2026"), found by its month in both languages, the issues' themes, the Books of the Month and "toolkit" / "kit del
     mes" / "poster" (search.kw.month_kit) ---- */
  safely("months", () => {
    if (!seenPage.has("/monthly/")) return;
    const now = nowDate();
    for (const key of windowKeys(now)) {
      const m = monthModel(key, db, {}, site || {}, lang, now);
      const named = !!(m.gv && /\b(issue|edici[oó]n)\b/i.test(m.gv.theme));
      push({
        id: "month:" + key, k: "month", t: T("monthly.month_title", { month: m.title }), tl: lang,
        s: m.gv ? T(named ? "monthly.month_desc_named" : "monthly.month_desc", { month: m.title, theme: m.gv.theme }) : T("monthly.month_desc_plain", { month: m.title }),
        x: uniq([monthLabel(key, "en"), monthLabel(key, "es"), m.gv && m.gv.theme, m.gv && m.gv.orig, m.lv && m.lv.theme, m.lv && m.lv.label,
          ...(m.botm || []).map((b) => b.title), both("search.kw.month_kit")].map(squish), " "),
        u: `/monthly/${key}/`, d: `${key}-01`, dp: "m", src: "neta",
      });
    }
  });

  /* ---- Since round 37: the SHOP's offers, each to its place on /shop/ (as the page shows them: shop.js) — the Books
     of the Month (#botm-<gv|lv>-title), the specialty items (#special-<type>: cards, planner, calendar …), an offer the
     stores announced (#offers-<key>: free shipping …) and a price change AA Grapevine announced (#pc-<key>-before /
     -after, the notice the page shows now) — kind "section", found by their titles and the shop's words ---- */
  safely("shop", () => {
    if (!seenPage.has("/shop/")) return;
    const shop = db.shop || {};
    const tt = (k, l, v) => helpers.translateKey(k, l, v);
    for (const b of shopBotm(shop, lang, "", tt)) {
      push({
        id: "botm:" + b.pub, k: "section", t: b.title, tl: b.itemLang, o: b.subtitle || "", ol: lang,
        s: uniq([T("shop.botm_title"), b.mag, b.startsLabel && b.endsLabel ? `${b.startsLabel} – ${b.endsLabel}` : ""]),
        x: uniq([snippet(b.blurb, 160), both("shop.botm_title"), both("search.kw.botm"), both("search.kw.shop_section")].map(squish), " "),
        u: `/shop/#botm-${b.pub}-title`, src: b.pub, im: b.image || "", ic: "book-open",
      });
    }
    for (const sp of shopSpecialty(shop, lang, tt)) {
      push({
        id: "shop:" + sp.anchor, k: "section", t: sp.title, tl: sp.titleLang, s: snippet(sp.text, 170),
        x: uniq([sp.typeName, tryKey(helpers, "shop.special_type_" + sp.type, other), both("shop.special_title"), sp.mag,
          both("search.kw.shop_section")].map(squish), " "),
        u: `/shop/#${sp.anchor}`, src: sp.pub, im: sp.image || "", ic: "gift",
      });
    }
    for (const o of shopOffers(site || {}, lang, db.drive?.items || [], tt)) {
      push({
        id: "offer:" + o.key, k: "section", t: o.title, tl: o.titleLang, s: o.dates,
        x: uniq([...(o.stores || []).map((s) => snippet(s.text, 160)), both("shop.offer_eyebrow"), both("search.kw.shop_section")].map(squish), " "),
        u: `/shop/#offers-${o.key}`, src: "site", ic: o.icon || "truck",
      });
    }
    for (const pc of shopPriceChanges(shop, lang, tt)) {
      const part = pc.before ? "before" : "after";
      push({
        id: "price:" + pc.key, k: "section", t: T("shop.pc_title_" + part, { date: pc.date }), tl: lang,
        s: snippet(T("shop.pc_lead_" + part, { date: pc.date }), 170), x: [both("search.kw.price_change"), both("search.kw.shop_section")].join(" "),
        u: `/shop/#pc-${pc.key}-${part}`, src: "gv", ic: part === "before" ? "calendar-clock" : "badge-dollar-sign",
      });
    }
  });

  /* ---- (round 37's fixer) The TEXAS WRITERS ARCHIVE (/published/#archive: db.writers_archive, every year's stories by
     Texas writers — published.js pwArchiveItems, the stories the page lists): each story → its page on the magazine's
     site, as the page's rows link it, found by its title (both languages), its writers and their hometowns (`a`), its
     issue and its theme. Ranked below the newer articles (lw, as a year of covers). A story the Library has already
     (db.articles, above: its summary, its picture) keeps that entry. A lean entry each (~1,250 of them, ~270 bytes:
     about a quarter of each index — eleventy/seo-check.js SEARCH_LIMIT): no summary, no date. ---- */
  safely("archive stories", () => {
    if (!seenPage.has("/published/")) return;
    const known = new Set(out.filter((e) => e.k === "article").map((e) => String(e.u).toLowerCase().replace(/\/+$/, "")));
    for (const it of pwArchiveItems(db)) {
      const url = String(it.url || "");
      if (!/^https:\/\//i.test(url) || known.has(url.toLowerCase().replace(/\/+$/, ""))) continue;
      const lv = it.pub === "lv";
      const writers = (Array.isArray(it.writers) ? it.writers : []).map((w) => [w && !w.anonymous ? squish(w.name) : "",
        squish((w && w.geo && w.geo[`label_${lang}`]) || (w && w.place) || "")].filter(Boolean).join(" · ")).filter(Boolean);
      // (its issue as the page's row names it: "December 2026", "Julio / Agosto 2015" — published.js's rule)
      const issue = issueName(it.issue_key, lv ? "lv" : "gv", lang) || (it.issue_label ? localizeIssueLabel(String(it.issue_label), lang, lv ? "lv" : "gv") : "");
      push({
        id: it.id, k: "article", t: P(it, "title"), o: it.title, ol: it.lang,
        s: uniq([issue, lv ? "La Viña" : "AA Grapevine"]),
        a: uniq(writers, "; "),
        x: squish(it.theme || ""),
        // (no `d`: the issue is in its line, and an old story needs no recency boost — a lean entry)
        u: url, l: it.lang, src: lv ? "lv" : "gv", m: mach(it), lw: 1,
      });
    }
  });

  /* ---- Weekly open meetings (Grapevine + La Viña) → their section on our Meeting page (Zoom ID, passcode,
     day and time in both languages; the official page is linked from there). Since round 37 the result says "Online on
     Zoom", never the Zoom ID: the index is a file anyone can read, and the card on /meetings/#weekly-open is the one
     place that gives how to join ---- */
  safely("weekly_open", () => {
    for (const it of db.weekly_open?.items || []) {
      if (!ok(it)) continue;
      const ex = it.extra || {};
      const when = P(it, "when") || [P(it, "day"), P(it, "time")].filter(Boolean).join(" · ");
      // One entry per meeting (Grapevine's on Wednesdays, La Viña's in Spanish on Thursdays)
      const lv = it.source === "lavina";
      push({
        id: "weekly-open:" + it.id, k: "meeting", t: P(it, "title"), o: it.title,
        s: [when, ex.zoom_id || ex.zoom_url ? T("committee.events.online_on", { platform: "Zoom" }) : ""].filter(Boolean).join(" · "),
        x: ["zoom", both(lv ? "search.kw.weekly_open_lv" : "search.kw.weekly_open"), it.i18n?.when?.[lang === "es" ? "en" : "es"]].filter(Boolean).join(" "),
        u: "/meetings/#weekly-open", l: it.lang, src: lv ? "lv" : "gv",
        // (round 37's fixer) where it says when and how to join: ranked above its own dated recordings, which share
        // its title's words and are newer (search.js boostDocument: `pr`)
        pr: 1,
      });
    }
  });

  /* ---- Grapevine meetings (db.meetings) → their group's card on /meetings/ (#gvg-…). ONE entry per group
     and place: a group that meets several times a week (e.g. every morning) is one result, not six.
     Found by its name, city, county, region and "Grapevine meeting" / "reunión de Grapevine". ---- */
  safely("meetings", () => {
    if (typeof committee.gvMeetings !== "function") return;
    const gv = committee.gvMeetings(db.meetings, lang, site || {});
    const cards = [gv.areaGroup, ...gv.nearbyGroups].filter(Boolean).flatMap((g) => g.days.flatMap((d) => d.items.map((c) => ({ c, dayName: d.name, group: g }))));
    const byPlace = new Map();
    for (const e of cards) {
      const k = fold(e.c.name) + "|" + fold(e.c.address || e.c.placeLine);
      if (!byPlace.has(k)) byPlace.set(k, []);
      byPlace.get(k).push(e);
    }
    for (const list of byPlace.values()) {
      const { c, group } = list[0];
      const when = list.length <= 2 ? list.map((e) => `${e.dayName} ${e.c.time}`).join(" · ") : "";
      push({
        id: "meeting:" + c.id, k: "meeting", t: c.name, tl: lang,
        s: when ? [when, c.placeLine].filter(Boolean).join(" · ") : T("committee.gvm.search_many", { place: c.placeLine, n: list.length }),
        x: uniq([both("committee.gvm.search_kw"), both("committee.gvm.title"), group.inArea ? "NETA 65 Area 65" : group.label,
          c.search, ...c.badges.map((b) => b.label), c.spanish ? both("committee.weekly.lang_es") : ""].map(squish), " "),
        u: "/meetings/#" + (c.groupAnchor || c.anchor), ic: "map-pin",
      });
    }
  });
  return out;
}

/* ------------------------------------------------------------------ */
export default function (eleventyConfig, helpers) {
  eleventyConfig.addFilter("libDocs", (db, lang) => libraryDocs(db, lang, helpers));
  eleventyConfig.addFilter("libFacets", (docs, lang) => libraryFacets(docs || [], lang, helpers));
  eleventyConfig.addFilter("libCollections", (docs, lang) => libraryCollections(docs || [], lang, helpers));
  eleventyConfig.addFilter("libStats", (docs) => libraryStats(docs || []));
  eleventyConfig.addFilter("libCatLabel", (key, lang) => catLabel(helpers, key, lang));
  eleventyConfig.addFilter("libCatIcon", (key) => CAT_ICON[key] || "file-text");
  eleventyConfig.addFilter("libCatIconMap", (cats) => Object.fromEntries((cats || []).map((c) => [c.key, c.icon])));
  eleventyConfig.addFilter("libColsConfig", (cols) => (cols || []).map((c) => ({ key: c.key, code: c.code, label: c.label, icon: c.icon, tone: c.tone })));
  eleventyConfig.addFilter("libNum", (n, lang) => fmtNum(n, lang));
  // JSON for <script type="application/json"> blocks: "<" escaped so data can never close the tag.
  eleventyConfig.addFilter("jsonScript", scriptJson); // the shared serializer (eleventy/script-json.js)
  eleventyConfig.addFilter("libIndexJson", (db, lang) => JSON.stringify(libraryIndex(db, lang, helpers)));
  // one index per language per build (search.njk + search-index.json share it — both hand over the same
  // `presentations` global: the first call builds it), with the addresses of the build's pages (builtUrls)
  const searchCache = new Map();
  const getSearch = (db, nav, lang, site, presentations) => {
    if (!searchCache.has(lang)) searchCache.set(lang, searchIndex(db, nav, lang, helpers, site, { presentations, pages: builtUrls }));
    return searchCache.get(lang);
  };
  eleventyConfig.on("eleventy.before", () => { searchCache.clear(); spotFile = undefined; cancelledMemo = null; builtUrls = null; });
  // (every page's address, once Eleventy knows them all — before the search page and index are rendered)
  eleventyConfig.on("eleventy.contentMap", ({ urlToInputPath } = {}) => {
    builtUrls = urlToInputPath && typeof urlToInputPath === "object" ? new Set(Object.keys(urlToInputPath)) : null;
  });
  eleventyConfig.addFilter("searchIndexJson", (db, nav, lang, site, presentations) => {
    const items = getSearch(db, nav, lang, site, presentations);
    return JSON.stringify({ v: 2, lang, built: new Date().toISOString(), count: items.length, items });
  });
  eleventyConfig.addFilter("searchSpotlightTile", (view, db) => spotlightTile(view, db));
  eleventyConfig.addFilter("searchKindCounts", (db, nav, lang, site, presentations) => {
    const counts = {};
    for (const e of getSearch(db, nav, lang, site, presentations)) counts[e.k] = (counts[e.k] || 0) + 1;
    return counts;
  });
}
