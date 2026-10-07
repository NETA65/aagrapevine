// The booth display (the About page's "Booth display": a show that plays by itself at the committee's Grapevine /
// La Viña table at assemblies and events) — everything the show is made of at build time. Auto-loaded by
// eleventy.config.js. Owned by src/_data/booth.js (the `booth` global: the owner's files read and checked) and
// src/pages/booth-json.11ty.js (/about/booth.json, the one file the player fetches); the player itself is
// src/assets/js/booth-core.js + booth.js, its page section src/_includes/macros/booth.njk.
//
// What goes into the show (SPEC §1–§2.5, aagrapevine-ops/r5/SPEC.md):
//   · content/booth/booth.csv — the committee's own rows: quizzes, true or false, facts, quotes, history, fill in the
//     blank, scrambled words, polls, talking points, messages, QR codes and links to official videos, podcast
//     episodes and pictures (content/booth/README.md is the owner's guide to every column)
//   · data/site/booth.json — the photos, videos, sound files and notes of the Drive panel folder's booth\ (the
//     daily sync: scripts/sync/drive.py + build_data.py), with .cache/booth-media/manifest.json — the copies the
//     deploy saved next to the site (scripts/build/booth-media.mjs), so they play offline; without the manifest a
//     picture is shown from Google's copy (online only) and a video or sound file is left out
//   · the site's own data, read again with every build — the "live" items: the next events and assembly, both daily
//     quotes, the official channels' short videos, the newest podcast episodes, the next story themes, the prices,
//     both Books of the Month, the meetings anyone can join, the newest bulletin posts
//   · config/site.yml `booth:` — the player's starting settings (event name, language, sound)
//
//   parseCsv(text)            → { rows, unclosed } — RFC 4180, as Python's csv module reads a file (a BOM, "" inside
//                               quotes, line breaks inside quotes, CRLF / LF / CR); `unclosed` = the row where a quoted
//                               cell starts and never ends (the rest of the file was read into it)
//   checkCsv(text, opts)      → { items, problems, rows } — every row checked and shaped (SPEC §1.2 and §4). THE
//                               rules: tests/test_booth_csv.py is their Python twin (what the committee's Code check
//                               runs on the real file), and the two must give the same lines — keep them in step
//   youtubeOf(url)            → { id, short, start } | null — watch?v=, youtu.be/, shorts/, embed/ (and ?t=1m30s)
//   driveItems(drive, manifest, base) → { items, problems, collections } — the Drive booth folder's files
//   boothDefaults(cfg)        → { defaults, problems } — config/site.yml booth.defaults as the player's settings keys
//   loadBooth(opts)           → the `booth` global (the files read; problems never stop the build)
//   liveItems(ctx)            → the live items of the day (SPEC §2.5)
//   eventsPick(ctx)           → the next events a booth could be at ("pick the event" in the player's settings)
//   boothShow(booth, ctx)     → the whole /about/booth.json object (SPEC §2.4)
// Filter: boothJson(booth, data) → that file's text (data = the template's data: db, site, meeting).
//
// Problems never stop the build: a row or a file the show cannot use is left out and listed in `problems` — the
// player's Settings → Items shows them, in both languages ({ where, en, es }) — and the build log names them. The
// Code check fails instead (tests/test_booth_csv.py: the real CSV must have none), so the committee hears of a
// mistake before a booth does.
// Every fact of a live item comes from the site's own data and functions — the same words and numbers the other
// pages show: committee.js (the events of /events/, the committee meeting's rule, the weekly open meetings, the
// bulletin), read.js (the editorial calendar: themes and deadlines), shop.js (prices, announced price changes, the
// Books of the Month), community.js (QR codes), event-tone.js (an assembly), and the site's strings (src/_i18n)
// where the pages already say the same thing; the few words only the booth uses are in BOOTH_WORDS below, in
// both languages.
// AA principles (SPEC §4): only Grapevine / La Viña and our committee; quotes word for word with their credit lines
// (the live Daily Quote is the item the Home page shows, with its attribution and a link to the official page);
// prices as information, with "as of" and never an urgent word; no magazine or book covers, no Grapevine artwork
// (the podcast's logo neither); links only to AA, Grapevine, La Viña, NETA 65 and this site, and a QR code to a
// page, never a document file. The words the booth never shows (refusedIn: "PDF", donations, sales and urgency
// words, unverified claims …) are checked wherever words come from: the CSV's cells, the Drive folder's captions and
// notes, and every live item (the official channel's titles, the bulletin's posts, the events' names …).
// Dates and day boundaries are Central time (America/Chicago); the build's "now" is monthly.js nowDate()
// (MONTHLY_NOW=2026-12-15 moves it for a preview build, as for /monthly/).

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { monthlyRule } from "../../eleventy.config.js";
import { qrSvg } from "./community.js";
import { normalizeEvents, chicagoDayEndMs, announcementList, weeklyOpenAll, meetingTitle, recurrenceText } from "./committee.js";
import { editorialFor, issueName, aboutVideos } from "./read.js";
import { nowDate, chicagoYmd } from "./monthly.js";
import { shopBotm, shopPlanPrice, shopNextChange, money, dayLabel } from "./shop.js";
import { eventTone } from "./event-tone.js";

const LOCALES = { en: "en-US", es: "es-US" };
const LANGS = ["en", "es"];

// Helpers handed over by eleventy.config.js (translateKey, pickLang, fmtDate …); the fallbacks keep the module
// usable from a plain `node` script too (the data file reads the CSV before any page is rendered).
let H = {
  translateKey: (k) => k,
  pickLang: (item, field, lang) => {
    if (!item) return "";
    const i = item.i18n && item.i18n[field];
    if (i && i[lang]) return i[lang];
    return item[field] ?? (item.extra && item.extra[field]) ?? "";
  },
};
const t = (key, lang, vars) => H.translateKey(key, lang, vars);

/* ------------------------------------------------------------------ */
/*  The CSV's columns, types and channels (SPEC §1.2, §3.1, §3.2)       */
/* ------------------------------------------------------------------ */
/** Every column of content/booth/booth.csv, in the starter file's order (the order in a file is free). */
export const COLUMNS = [
  "id", "on", "type", "pub", "tags", "weight", "from", "until", "seconds", "reveal",
  "title_en", "text_en", "choices_en", "correct", "answer_en", "explain_en", "credit_en",
  "title_es", "text_es", "choices_es", "answer_es", "explain_es", "credit_es",
  "media_url", "start", "end", "qr_url", "source_url", "notes",
];
/** The row types — each one is also the slide's render type (§3.1). */
export const TYPES = ["quiz", "truefalse", "fact", "quote", "history", "fill", "scramble", "poll", "prompt", "message",
  "qr", "video", "audio", "image"];
/** A CSV type → the settings channel that switches it on and off (§3.2). */
export const CSV_CHANNEL = {
  quiz: "quiz", truefalse: "quiz", fill: "puzzles", scramble: "puzzles", fact: "facts", history: "facts",
  quote: "quotes", poll: "polls", prompt: "prompts", message: "messages", qr: "qr", video: "web-video",
  audio: "web-audio", image: "web-image",
};
/** A Drive file's kind → its channel. */
export const DRIVE_CHANNEL = { photo: "photos", poster: "posters", video: "videos", audio: "sounds", message: "notes" };
/** The channels in the order the player's settings list them (welcome and about are the player's own: no items). */
export const CHANNELS = ["quiz", "puzzles", "facts", "quotes", "polls", "prompts", "messages", "qr", "web-video",
  "web-audio", "web-image", "photos", "posters", "videos", "sounds", "notes", "live-events", "live-quote",
  "live-video", "live-podcast", "live-themes", "live-prices", "live-book", "live-meetings", "live-bulletin"];

// What each type needs in every language the row is shown in ("a|b": one of the two), the columns only some
// types take, and the text lengths a slide has room for.
const NEEDS = {
  quiz: ["text", "choices"], truefalse: ["text"], fact: ["text"], quote: ["text", "credit"], history: ["title", "text"],
  fill: ["text", "answer"], scramble: ["text", "answer"], poll: ["text", "choices"], prompt: ["text"],
  message: ["text"], qr: ["title|text"], video: ["title|text"], audio: ["title|text"], image: ["title|text"],
};
const MEDIA_TYPES = ["video", "audio", "image"];
const CHOICE_TYPES = ["quiz", "poll"];
const ANSWER_TYPES = ["fill", "scramble"];
const REVEAL_TYPES = ["quiz", "truefalse", "fill", "scramble"];
const SOURCE_TYPES = ["quiz", "truefalse", "fact", "history", "fill"];
const SHORT_TEXT = ["quiz", "truefalse", "fill"];
// a row's text columns in each language, in the order the checks name them
const LANG_FIELDS = ["title", "text", "choices", "answer", "explain", "credit"];
const MAX = { title: 80, text: 300, short_text: 180, explain: 240, credit: 200, choice: 70, answer: 60 };
const LANG_NAME = { en: { en: "English", es: "inglés" }, es: { en: "Spanish", es: "español" } };

/** Links a row may show or play (media_url, qr_url): AA's non-affiliation — research.md D3 "Links". The site's own
 *  address (site.url) is added to them. (m.youtube.com and www.youtube-nocookie.com are YouTube's own addresses too.)
 *  The podcast's host, Captivate, has three: episodes.captivate.fm (the feed's links to new episodes), its file
 *  server podcasts.captivate.fm (where those links lead, and where the feed points the older episodes — every
 *  episode of 2021 to mid-2025 — directly) and player.captivate.fm (an episode's page). Never *.captivate.fm: any
 *  podcast's own site is <show>.captivate.fm. */
export const ALLOWED_HOSTS = [
  "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
  "aagrapevine.org", "www.aagrapevine.org", "aalavina.org", "www.aalavina.org", "aa.org", "www.aa.org",
  "neta65.org", "www.neta65.org", "neta65.github.io", "episodes.captivate.fm", "podcasts.captivate.fm",
  "player.captivate.fm",
];
const YT_HOSTS = ["youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"];
const HOSTS_EN = "YouTube, aagrapevine.org, aalavina.org, aa.org, neta65.org, the podcast's captivate.fm, this website";
const HOSTS_ES = "YouTube, aagrapevine.org, aalavina.org, aa.org, neta65.org, captivate.fm del podcast, este sitio";

const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const W = "[\\p{L}\\p{N}_]";
// White space, spelled out: JavaScript's \s and trim() and Python's \s and strip() disagree on a few characters
// (U+FEFF, U+001C–U+001F, U+0085), and the two checkers must read every cell alike.
const WS_CHARS = " \\t\\n\\r\\f\\v\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff";
const WS = `[${WS_CHARS}]`;
// An address the booth accepts: https, a host, no white space, no user name in it ("https://aa.org@other.site/" is
// not aa.org)
const URL_RE = new RegExp(`^https://([^/?#@:${WS_CHARS}]+)(:[0-9]+)?([/?#][^${WS_CHARS}]*)?$`, "i");

/* ------------------------------------------------------------------ */
/*  Reading the CSV (RFC 4180, the way Python's csv module reads it)    */
/* ------------------------------------------------------------------ */
/**
 * The records of a CSV text → { rows: [[cell, …], …], unclosed: <row number> | null }. Read exactly as Python's csv
 * module (excel dialect, strict off) reads a file opened with newline="" — tests/test_booth_csv.py parse_csv is the
 * same reader, and the tests hold both to the csv module:
 *   · a BOM at the start is dropped (Excel's "CSV UTF-8" writes one);
 *   · a record ends at CRLF, LF or CR outside quotes; an empty line is a record with no cells ([]), so the row
 *     numbers stay those a spreadsheet shows (the header is row 1);
 *   · a cell that starts with a double quote runs to the next lone double quote: commas and line breaks inside it
 *     are text, "" is one double quote, and text after the closing quote is kept ("ab"c → abc);
 *   · a double quote inside an unquoted cell is text;
 *   · a quoted cell that never ends takes the rest of the file (`unclosed` = its row; checkCsv reports it).
 * Line breaks inside cells stay as written (CRLF included): the checks make them "\n".
 */
export function parseCsv(text) {
  let s = String(text ?? "");
  if (s.charCodeAt(0) === 0xfeff) s = s.slice(1);
  const rows = [];
  let rec = null; // the record being read (null: none started)
  let cell = "";
  let state = "start"; // start (of a cell) | plain | quoted | closed (a quote just closed a quoted cell)
  let unclosed = null;
  const endRecord = () => {
    if (rec === null && state === "start" && cell === "") rows.push([]);
    else {
      (rec ??= []).push(cell);
      rows.push(rec);
    }
    rec = null;
    cell = "";
    state = "start";
  };
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (state === "quoted") {
      if (c === '"') {
        if (s[i + 1] === '"') { cell += '"'; i++; } else state = "closed";
      } else cell += c;
      continue;
    }
    if (c === "\r" || c === "\n") {
      endRecord();
      if (c === "\r" && s[i + 1] === "\n") i++;
      continue;
    }
    if (c === ",") {
      (rec ??= []).push(cell);
      cell = "";
      state = "start";
      continue;
    }
    if (c === '"' && state === "start") {
      rec ??= [];
      state = "quoted";
      unclosed = rows.length + 1;
      continue;
    }
    rec ??= [];
    cell += c;
    state = "plain";
  }
  if (state === "quoted") {
    (rec ??= []).push(cell);
    rows.push(rec);
    return { rows, unclosed };
  }
  if (rec !== null || cell !== "" || state === "closed") endRecord();
  return { rows, unclosed: null };
}

/* ------------------------------------------------------------------ */
/*  Small readers the checks share (the Python twin has the same ones)  */
/* ------------------------------------------------------------------ */
const TRIM = new RegExp(`^${WS}+|${WS}+$`, "g");
const TRIM_END = new RegExp(`${WS}+$`);
const SPACES = new RegExp(`${WS}+`, "g");
const TAG_SPLIT = new RegExp(`(?:[;,]|${WS})+`);
const TYPE_PUNCT = new RegExp(`(?:${WS}|[_/-])+`, "g");
const TAG = /^[\p{L}\p{N}][\p{L}\p{N}_-]*$/u;
const PLACEHOLDERS = ["event", "committee", "site"];
const ON_YES = ["yes", "y", "true", "1", "si", "sí"];
const ON_NO = ["no", "n", "false", "0"];
const TF_TRUE = ["true", "t", "yes", "y", "v", "verdadero", "cierto", "sí", "si"];
const TF_FALSE = ["false", "f", "no", "n", "falso"];
const PUBS = {
  gv: "gv", grapevine: "gv", lv: "lv", lavina: "lv", "laviña": "lv", both: "both", all: "both", aa: "both",
  ambos: "both", ambas: "both", gvlv: "both", "gv/lv": "both", "gv-lv": "both", "gv+lv": "both", "gv&lv": "both",
};

/** A cell as the checks read it: Unicode NFC, line breaks "\n" (no spaces at the end of a line, at most one empty
 *  line in a row), nothing around it. */
function cellText(v) {
  return String(v ?? "").normalize("NFC").replace(/\r\n?/g, "\n").split("\n").map((l) => l.replace(TRIM_END, ""))
    .join("\n").replace(/\n{3,}/g, "\n\n").replace(TRIM, "");
}
/** A one-line cell (a title, a choice, a credit line, a link …): every run of white space one space. */
const oneLine = (v) => cellText(v).replace(SPACES, " ");
/** Length in characters as a person counts them (code points, so an emoji or "ñ" is one). */
const len = (s) => [...String(s)].length;
const pad2 = (n) => String(n).padStart(2, "0");
/** 90 → "1:30" (the messages show times the way the column takes them). */
const clock = (sec) => `${Math.floor(sec / 60)}:${pad2(sec % 60)}`;

/** A real calendar day written YYYY-MM-DD, in the years 2000–2099 (so a mistyped year — 0027, 2207 — is named; and
 *  Date.UTC would read the years 0–99 as 1900–1999). tests/test_booth_csv.py valid_day says the same. */
function validDay(v) {
  if (!/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(v)) return false;
  const [y, m, d] = v.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

/** "90" → 90, "1:30" → 90, "1:02:03" → 3723; anything else null. */
export function secondsOf(v) {
  const s = String(v ?? "").replace(TRIM, "");
  let m = /^([0-9]{1,5})$/.exec(s);
  if (m) return Number(m[1]);
  m = /^([0-9]{1,3}):([0-5][0-9])$/.exec(s);
  if (m) return Number(m[1]) * 60 + Number(m[2]);
  m = /^([0-9]{1,2}):([0-5][0-9]):([0-5][0-9])$/.exec(s);
  return m ? Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) : null;
}

/** An https:// address → { host (lower case), path, query } or null (another scheme, white space, a user name). */
export function splitUrl(v) {
  const m = URL_RE.exec(String(v ?? ""));
  if (!m) return null;
  const rest = m[3] || "";
  const q = rest.indexOf("?"), h = rest.indexOf("#");
  const pathEnd = Math.min(q < 0 ? rest.length : q, h < 0 ? rest.length : h);
  const query = q < 0 || (h >= 0 && h < q) ? "" : rest.slice(q + 1, h > q ? h : rest.length);
  return { host: m[1].toLowerCase(), path: rest.slice(0, pathEnd) || "/", query };
}
const params = (query) => {
  const out = Object.create(null);
  for (const part of String(query || "").split("&")) {
    if (!part) continue;
    const i = part.indexOf("=");
    const k = i < 0 ? part : part.slice(0, i);
    let v = i < 0 ? "" : part.slice(i + 1);
    try { v = decodeURIComponent(v.replace(/\+/g, " ")); } catch { /* keep it as written */ }
    if (!(k in out)) out[k] = v;
  }
  return out;
};
/** YouTube's ?t= / ?start=: "90", "90s", "1m30s", "1h2m3s" → seconds, else null. */
function ytTime(v) {
  const s = String(v ?? "");
  let m = /^([0-9]{1,6})s?$/.exec(s);
  if (m) return Number(m[1]);
  m = /^(?:([0-9]{1,2})h)?(?:([0-9]{1,3})m)?(?:([0-9]{1,5})s)?$/.exec(s);
  return m && (m[1] || m[2] || m[3]) ? Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0) : null;
}

/**
 * A YouTube link → { id, short, start } or null: youtube.com/watch?v=<id> (m. and www. too), youtu.be/<id>,
 * youtube.com/shorts/<id> (short: true — the player shows it in a phone-shaped frame), youtube.com/embed/<id> and
 * youtube-nocookie.com/embed/<id>; `start` from ?t= / ?start= (seconds or 1m30s), else null.
 */
export function youtubeOf(url) {
  const u = splitUrl(url);
  if (!u) return null;
  const seg = u.path.split("/").filter(Boolean);
  const q = params(u.query);
  let id = "", short = false;
  if (u.host === "youtu.be") id = seg.length === 1 ? seg[0] : "";
  else if (YT_HOSTS.includes(u.host)) {
    const head = (seg[0] || "").toLowerCase();
    if (head === "watch" && seg.length === 1) id = q.v || "";
    else if ((head === "shorts" || head === "embed") && seg.length === 2) {
      id = seg[1];
      short = head === "shorts";
    }
  }
  if (!/^[A-Za-z0-9_-]{11}$/.test(id)) return null;
  const tv = q.t !== undefined ? q.t : q.start;
  return { id, short, start: tv === undefined ? null : ytTime(tv) };
}
const ytWatch = (id, short) => (short ? `https://www.youtube.com/shorts/${id}` : `https://www.youtube.com/watch?v=${id}`);
const ytPoster = (id) => `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;

/** The media block every media item has (null where the kind does not use a key). */
const mediaBlock = (o) => ({
  kind: o.kind, src: o.src, id: o.id ?? null, short: !!o.short, local: !!o.local, poster: o.poster ?? null,
  start: o.start ?? 0, end: o.end ?? null, muted: !!o.muted, fit: o.fit || "contain",
  w: o.w ?? null, h: o.h ?? null, bytes: o.bytes ?? null,
});

/* ------------------------------------------------------------------ */
/*  Words the booth never shows (SPEC §1.2, §4: attraction, not promotion) */
/* ------------------------------------------------------------------ */
// Each rule: what it catches, and why — in both languages, for the problem line. Checked in every shown cell of the
// CSV (titles, texts, choices, answers, explanations, credit lines; never the notes or the links — but the part of a
// qr_url the player prints under the code may not say "PDF" either: PDF_WORD), in the Drive booth folder's captions
// and notes (driveItems) and in every live item's words (screenLive).
const SALES_EN = "no sales or urgency words: attraction, not promotion";
const SALES_ES = "sin palabras de venta ni de urgencia: atracción, no promoción";
/** "PDF" / "PDFs" as a word: a visitor never reads it (say "document"). */
const PDF_WORD = new RegExp(`(?<!${W})pdfs?(?!${W})`, "iu");
const REFUSED = [
  { re: PDF_WORD,
    en: "say “document” instead", es: "di “documento”" },
  { re: new RegExp(`${W}*donat${W}*`, "iu"),
    en: "Grapevine and La Viña take no donations (say “Carry the Message gift”)",
    es: "Grapevine y La Viña no reciben donativos (di “regalo de Lleva el Mensaje”)" },
  { re: new RegExp(`(?<!${W})contributions?${WS}+to${WS}+(?:the${WS}+)?(?:aa${WS}+)?(?:grapevine|la${WS}+vi[ñn]a)(?!${W})`, "iu"),
    en: "AA Grapevine, Inc. does not accept contributions", es: "AA Grapevine, Inc. no acepta contribuciones" },
  { re: new RegExp(`(?<!${W})contribu(?:ir|ciones|ción|cion)${WS}+(?:a|para)${WS}+(?:la${WS}+)?(?:aa${WS}+)?(?:grapevine|la${WS}+vi[ñn]a)(?!${W})`, "iu"),
    en: "AA Grapevine, Inc. does not accept contributions", es: "AA Grapevine, Inc. no acepta contribuciones" },
  // (the official channel's own Shorts say "Download Now! Then Subscribe!" / "¡Descárgala ahora! ¡Luego suscríbete!":
  // "download the La Viña app today", "¿dónde puedes descargar hoy…?" and "how to subscribe" stay informative)
  { re: new RegExp(`(?<!${W})(?:buy${WS}+now|hurry|limited(?:${WS}|-)+time|act${WS}+now|last${WS}+chance|don[’']?t${WS}+miss|subscribe${WS}+(?:now|today)|download${WS}+(?:it${WS}+|them${WS}+)?(?:now|today))(?!${W})`, "iu"),
    en: SALES_EN, es: SALES_ES },
  { re: new RegExp(`(?<!${W})sale!`, "iu"), en: SALES_EN, es: SALES_ES },
  { re: new RegExp(`(?<!${W})before${WS}+(?:the${WS}+)?prices?${WS}+(?:go(?:es)?${WS}+up|rises?|increases?|changes?)(?!${W})`, "iu"),
    en: SALES_EN, es: SALES_ES },
  { re: new RegExp(`(?<!${W})(?:compra${WS}+(?:ya|ahora)|ap[uú]rate|apres[uú]rate|date${WS}+prisa|tiempo${WS}+limitado|[uú]ltima${WS}+oportunidad|suscr[ií]bete${WS}+(?:ya|hoy|ahora)|desc[aá]rg(?:a|ue)(?:l[aoe]s?)?${WS}+(?:ya|ahora|hoy))(?!${W})`, "iu"),
    en: SALES_EN, es: SALES_ES },
  { re: new RegExp(`(?<!${W})antes${WS}+de${WS}+que${WS}+(?:suba|suban|cambie|cambien)${WS}+(?:el${WS}+|los${WS}+)?precios?(?!${W})`, "iu"),
    en: SALES_EN, es: SALES_ES },
  // a shouted call to subscribe, like "sale!": "Subscribe!", "¡Suscríbete!"
  { re: new RegExp(`(?<!${W})(?:subscribe|suscr[ií]b(?:ete|ase))!`, "iu"), en: SALES_EN, es: SALES_ES },
  // the claims research.md leaves out — no source was found for them (A4, E6, Open question 23; SPEC §4: "never the
  // unverified items")
  { re: new RegExp(`(?<!${W})(?:reach(?:es|ing)?${WS}+millions|lleg(?:a|an)${WS}+a${WS}+millones|183${WS}+challenge|reto${WS}+183)(?!${W})`, "iu"),
    en: "an unverified claim (no source found): leave it out",
    es: "una afirmación sin verificar (no se encontró la fuente): omítela" },
  // "Conference-approved" said of Grapevine or La Viña (the cell names one of them): the Conference RECOGNIZES
  // Grapevine as the international journal of AA (1986), and the recognition extends to La Viña
  { re: new RegExp(`(?<!${W})(?:conference(?:${WS}|-)+approved|aprobad[oa]s?${WS}+por${WS}+la${WS}+conferencia)(?!${W})`, "iu"),
    when: (s) => new RegExp(`grapevine|la${WS}+vi[ñn]a`, "iu").test(s),
    en: "say “recognized by the Conference as the international journal of AA”",
    es: "di “reconocida por la Conferencia como la revista internacional de AA”" },
  // "today only" in a text without {event}: the same rows play on many days
  { re: new RegExp(`(?<!${W})(?:today${WS}+only|s[oó]lo${WS}+hoy|[uú]nicamente${WS}+hoy)(?!${W})`, "iu"),
    when: (s) => !s.includes("{event}"),
    en: "“today only” needs {event} (the booth shows the same rows on many days)",
    es: "“solo hoy” necesita {event} (la pantalla muestra las mismas filas muchos días)" },
];

/** The refused words in a text → [{ word (as written), en, es }] — one per rule that catches something. */
export function refusedIn(text) {
  const s = String(text ?? "");
  const out = [];
  for (const r of REFUSED) {
    const m = r.re.exec(s);
    if (m && (!r.when || r.when(s))) out.push({ word: m[0], en: r.en, es: r.es });
  }
  return out;
}

/* ------------------------------------------------------------------ */
/*  Checking the CSV (SPEC §1.2 and §4) — tests/test_booth_csv.py is its twin */
/* ------------------------------------------------------------------ */
/** The site's address with one "/" at the end ("https://neta65.github.io/aagrapevine/"), or "". */
const siteBase = (site) => {
  const u = String((site && site.url) || "").replace(/\/+$/, "");
  return u ? u + "/" : "";
};
/** qr_url → the code's address on English slides and on Spanish ones: { en, es } (SPEC update 1). {site} at the
 *  start of the link is the site's address: "{site}contribute/" → en: its English page, es: the same page under
 *  the Spanish home (".../es/contribute/"); {site_es} is the Spanish home in both ("{site_es}meetings/" → the
 *  Spanish page on every slide). Any other link has no Spanish address of its own (es null: the same code on
 *  every slide). null when there is no site address to put in, or a brace is left anywhere. */
function resolveSite(v, base) {
  const s = String(v);
  for (const [tok, both] of [["{site_es}", true], ["{site}", false]]) {
    if (!s.startsWith(tok)) continue;
    if (!base) return null;
    const rest = s.slice(tok.length).replace(/^\/+/, "");
    if (/[{}]/.test(rest)) return null;
    // (a path that already starts in the Spanish home stays where it is)
    const es = base + (/^es(?:[/?#]|$)/.test(rest) ? "" : "es/") + rest;
    return { en: both ? es : base + rest, es };
  }
  return /[{}]/.test(s) ? null : { en: s, es: null };
}

/**
 * content/booth/booth.csv (its text) → { items, problems, rows }: the rows the show uses, in file order, as ITEMs
 * of /about/booth.json (SPEC §2.4), and a problem line for each mistake — { where: "booth.csv row 14 (quiz-12)",
 * en, es }. A row with any mistake is left out (all its mistakes are listed); a blank row and a row whose id starts
 * with "#" (a comment) are skipped; a row switched off (on = no) is checked like the others but not shown.
 *   opts.site  { url }: the site's address — {site} / {site_es} in qr_url, and its host is an allowed site
 *   opts.file  the name the lines give the file ("booth.csv")
 * Text columns keep {event}, {committee} and {site} for the player (GVB.fill puts the event's name, the committee's
 * name and the site's address in their place). qr_url is worked out here (resolveSite): item.qr is the address for
 * English slides, item.qr_es the one for Spanish slides when a {site} link has a Spanish page (else null).
 */
export function checkCsv(text, opts = {}) {
  const file = opts.file || "booth.csv";
  const base = siteBase(opts.site);
  const own = base ? (splitUrl(base) || {}).host : "";
  const hostOk = (h) => ALLOWED_HOSTS.includes(h) || (!!own && h === own);
  const items = [];
  const problems = [];
  const add = (where, en, es) => problems.push({ where, en, es });
  const raw = String(text ?? "");
  if (raw.includes("\ufffd")) {
    add(file, "the file is not saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)",
      "el archivo no está guardado como UTF-8: letras como ñ y é pueden salir mal (Excel: Guardar como → CSV UTF-8)");
  }
  const { rows, unclosed } = parseCsv(raw);
  if (unclosed) {
    add(`${file} row ${unclosed}`, "a cell starts with a double quote (\") that is never closed: everything after it was read as that one cell",
      "una celda empieza con comillas dobles (\") que nunca se cierran: todo lo que sigue se leyó como esa celda");
  }
  const header = rows[0] || [];
  if (!header.some((c) => cellText(c))) {
    add(file, "the file is empty: the first row must be the header (id,on,type,…)",
      "el archivo está vacío: la primera fila debe ser el encabezado (id,on,type,…)");
    return { items, problems, rows: 0 };
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
  for (const need of ["id", "type"]) {
    if (!(need in col)) add(`${file} header`, `the header (first row) has no ${need} column`, `el encabezado (primera fila) no tiene la columna ${need}`);
  }
  if (!("id" in col) || !("type" in col)) return { items, problems, rows: rows.length - 1 };

  const seen = new Map(); // id → the row it was first used in
  for (let r = 1; r < rows.length; r++) {
    const cells = rows[r];
    const rowNo = r + 1;
    if (!cells.some((c) => cellText(c))) continue; // a blank row
    const get = (k) => (k in col ? cells[col[k]] ?? "" : "");
    const idRaw = oneLine(get("id"));
    if (idRaw.startsWith("#")) continue; // a comment
    const where = `${file} row ${rowNo}${idRaw ? ` (${[...idRaw].slice(0, 48).join("")})` : ""}`;
    const errs = [];
    const err = (en, es) => errs.push([en, es]);
    const flush = () => errs.forEach(([en, es]) => add(where, en, es));

    // more cells than the header has: a comma in a text that is not in quotes moved every cell after it
    if (cells.length > header.length && cells.slice(header.length).some((c) => cellText(c))) {
      err(`the row has ${cells.length} cells but the header has ${header.length}: a comma inside a text needs the whole cell in double quotes`,
        `la fila tiene ${cells.length} celdas pero el encabezado tiene ${header.length}: una coma dentro de un texto necesita la celda entera entre comillas dobles`);
      flush();
      continue;
    }

    // id, on, type, pub, tags, weight, dates, seconds, reveal
    let id = "";
    if (!idRaw) err("id is empty", "falta el id");
    else if (!ID.test(idRaw) || len(idRaw) > 48) {
      err(`id "${idRaw}": use only a–z, 0–9 and dashes (no spaces or capitals), at most 48 characters`,
        `id "${idRaw}": usa solo a–z, 0–9 y guiones (sin espacios ni mayúsculas), 48 caracteres como máximo`);
    } else if (seen.has(idRaw)) {
      err(`id "${idRaw}" is already used in row ${seen.get(idRaw)}`, `el id "${idRaw}" ya se usa en la fila ${seen.get(idRaw)}`);
    } else {
      id = idRaw;
      seen.set(id, rowNo);
    }
    const onRaw = oneLine(get("on"));
    const onLc = onRaw.toLowerCase();
    const on = !onRaw ? true : ON_YES.includes(onLc) ? true : ON_NO.includes(onLc) ? false : null;
    if (on === null) err(`on "${onRaw}": write yes or no`, `on "${onRaw}": escribe yes o no`);
    const typeRaw = oneLine(get("type"));
    const type = typeRaw.toLowerCase().replace(TYPE_PUNCT, "");
    const typeOk = TYPES.includes(type);
    if (!typeRaw) err(`type is empty (${TYPES.join(", ")})`, `falta type (${TYPES.join(", ")})`);
    else if (!typeOk) err(`type "${typeRaw}" is not one of: ${TYPES.join(", ")}`, `type "${typeRaw}" no es uno de: ${TYPES.join(", ")}`);
    const pubRaw = oneLine(get("pub"));
    const pubKey = pubRaw.toLowerCase().replace(SPACES, "");
    const pub = !pubRaw ? "both" : Object.hasOwn(PUBS, pubKey) ? PUBS[pubKey] : null;
    if (!pub) err(`pub "${pubRaw}": write gv, lv or both`, `pub "${pubRaw}": escribe gv, lv o both`);
    const tags = [];
    for (const tg of oneLine(get("tags")).toLowerCase().split(TAG_SPLIT).filter(Boolean)) {
      if (!TAG.test(tg) || len(tg) > 32) {
        err(`tags: "${tg}" is not a tag (one word: letters, digits, dashes; at most 32 characters)`,
          `tags: "${tg}" no es una etiqueta (una palabra: letras, números, guiones; 32 caracteres como máximo)`);
      } else if (!tags.includes(tg)) tags.push(tg);
    }
    const wRaw = oneLine(get("weight"));
    let weight = 1;
    if (wRaw) {
      const n = /^[0-9]{1,3}(?:[.,][0-9]{1,3})?$/.test(wRaw) ? Number(wRaw.replace(",", ".")) : NaN;
      if (n >= 0.5 && n <= 5) weight = n;
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
    const whole = (k, lo, hi) => {
      const v = oneLine(get(k));
      if (!v) return null;
      if (/^[0-9]{1,4}$/.test(v) && Number(v) >= lo && Number(v) <= hi) return Number(v);
      err(`${k} "${v}": a whole number from ${lo} to ${hi}`, `${k} "${v}": un número entero de ${lo} a ${hi}`);
      return null;
    };
    const seconds = whole("seconds", 4, 180);
    const reveal = whole("reveal", 4, 60);
    if (typeOk && oneLine(get("reveal")) && !REVEAL_TYPES.includes(type)) {
      err("reveal is only for quiz, truefalse, fill and scramble rows", "reveal es solo para filas quiz, truefalse, fill y scramble");
    }
    if (!typeOk) {
      flush();
      continue;
    }

    // the two languages: what each one has, the columns this type never takes, what a shown language needs
    const takes = (f) => (f === "choices" ? CHOICE_TYPES.includes(type) : f === "answer" ? ANSWER_TYPES.includes(type) : true);
    const L = {};
    for (const lang of LANGS) {
      L[lang] = {
        title: oneLine(get(`title_${lang}`)), text: cellText(get(`text_${lang}`)), choices: oneLine(get(`choices_${lang}`)),
        answer: oneLine(get(`answer_${lang}`)), explain: cellText(get(`explain_${lang}`)), credit: oneLine(get(`credit_${lang}`)),
        list: null,
      };
    }
    for (const lang of LANGS) {
      if (L[lang].choices && !takes("choices")) err(`choices_${lang} is only for quiz and poll rows`, `choices_${lang} es solo para filas quiz y poll`);
      if (L[lang].answer && !takes("answer")) err(`answer_${lang} is only for fill and scramble rows`, `answer_${lang} es solo para filas fill y scramble`);
    }
    const langs = [];
    for (const lang of LANGS) {
      const v = L[lang];
      const used = LANG_FIELDS.filter((f) => takes(f) && v[f]);
      if (!used.length) continue;
      langs.push(lang);
      const others = used.map((f) => `${f}_${lang}`).join(", ");
      for (const need of NEEDS[type]) {
        const opts = need.split("|");
        if (opts.some((f) => v[f])) continue;
        if (opts.length === 1) {
          err(`${need}_${lang} is empty, but other ${LANG_NAME[lang].en} cells are filled (${others}): fill it in, or empty them`,
            `${need}_${lang} está vacío, pero hay otras celdas en ${LANG_NAME[lang].es} con texto (${others}): complétalo o vacíalas`);
        } else {
          err(`${opts.map((f) => `${f}_${lang}`).join(" and ")} are both empty, but other ${LANG_NAME[lang].en} cells are filled (${others}): fill one in, or empty them`,
            `${opts.map((f) => `${f}_${lang}`).join(" y ")} están vacíos, pero hay otras celdas en ${LANG_NAME[lang].es} con texto (${others}): completa uno o vacía las otras`);
        }
      }
      const tooLong = (f, max) => {
        const n = len(v[f]);
        if (v[f] && n > max) err(`${f}_${lang} is ${n} characters long: at most ${max}`, `${f}_${lang} tiene ${n} caracteres: ${max} como máximo`);
      };
      tooLong("title", MAX.title);
      tooLong("text", SHORT_TEXT.includes(type) ? MAX.short_text : MAX.text);
      if (type === "fill") tooLong("answer", MAX.answer);
      tooLong("explain", MAX.explain);
      tooLong("credit", MAX.credit);
      if (takes("choices") && v.choices) {
        const list = v.choices.split("|").map((c) => c.replace(TRIM, ""));
        if (list.length < 2 || list.length > 6) {
          err(`choices_${lang}: give 2 to 6 choices separated by |`, `choices_${lang}: da de 2 a 6 opciones separadas por |`);
        } else {
          list.forEach((c, k) => {
            if (!c) err(`choices_${lang}: choice ${k + 1} is empty`, `choices_${lang}: la opción ${k + 1} está vacía`);
            else if (len(c) > MAX.choice) {
              err(`choices_${lang}: choice ${k + 1} is ${len(c)} characters long: at most ${MAX.choice}`,
                `choices_${lang}: la opción ${k + 1} tiene ${len(c)} caracteres: ${MAX.choice} como máximo`);
            }
          });
          const lower = list.map((c) => c.toLowerCase());
          const dup = lower.findIndex((c, k) => c && lower.indexOf(c) !== k);
          if (dup >= 0) err(`choices_${lang}: two choices are the same ("${list[dup]}")`, `choices_${lang}: hay dos opciones iguales ("${list[dup]}")`);
          v.list = list;
        }
      }
      if (type === "fill" && v.text) {
        const blanks = (v.text.match(/_{3,}/g) || []).length;
        if (!blanks) err(`text_${lang}: put ___ (three underscores) where the answer goes`, `text_${lang}: pon ___ (tres guiones bajos) donde va la respuesta`);
        else if (blanks > 1) err(`text_${lang}: has more than one ___ blank`, `text_${lang}: tiene más de un espacio ___`);
      }
      if (type === "scramble" && v.answer) {
        const letters = [...v.answer].filter((ch) => /\p{L}/u.test(ch)).length;
        if (!/^[\p{L} ]+$/u.test(v.answer) || letters < 3 || letters > 16) {
          err(`answer_${lang} "${v.answer}": letters and spaces only, 3 to 16 letters`, `answer_${lang} "${v.answer}": solo letras y espacios, de 3 a 16 letras`);
        }
      }
    }
    if (takes("choices") && L.en.list && L.es.list && L.en.list.length !== L.es.list.length) {
      err(`choices_en has ${L.en.list.length} choices and choices_es has ${L.es.list.length}: both languages need the same number, in the same order`,
        `choices_en tiene ${L.en.list.length} opciones y choices_es tiene ${L.es.list.length}: los dos idiomas necesitan el mismo número, en el mismo orden`);
    }
    if (!langs.length && !MEDIA_TYPES.includes(type)) {
      err("the row has no text in English or Spanish: fill in text_en, text_es or both",
        "la fila no tiene texto en inglés ni en español: completa text_en, text_es o los dos");
    }

    // correct: the right choice of a quiz (1–6 or A–F → its place, 0-based), the answer of a true-or-false
    const corRaw = oneLine(get("correct"));
    const corLc = corRaw.toLowerCase();
    let correct = null;
    if (type === "quiz") {
      const count = (langs.map((l) => L[l].list).find(Boolean) || []).length;
      const idx = /^[1-6]$/.test(corRaw) ? Number(corRaw) - 1 : /^[a-f]$/.test(corLc) ? corLc.charCodeAt(0) - 97 : -1;
      if (!corRaw) err("correct is empty: the number (1–6) or letter (A–F) of the right choice", "falta correct: el número (1–6) o la letra (A–F) de la opción correcta");
      else if (idx < 0) err(`correct "${corRaw}": the number (1–6) or letter (A–F) of the right choice`, `correct "${corRaw}": el número (1–6) o la letra (A–F) de la opción correcta`);
      else if (count && idx >= count) err(`correct "${corRaw}": there are only ${count} choices`, `correct "${corRaw}": solo hay ${count} opciones`);
      else correct = idx;
    } else if (type === "truefalse") {
      if (!corRaw) err("correct is empty: write true or false", "falta correct: escribe true o false");
      else if (TF_TRUE.includes(corLc)) correct = true;
      else if (TF_FALSE.includes(corLc)) correct = false;
      else err(`correct "${corRaw}": write true or false`, `correct "${corRaw}": escribe true o false`);
    } else if (corRaw) err("correct is only for quiz and truefalse rows", "correct es solo para filas quiz y truefalse");

    // the media: a YouTube video or a web file on an allowed site
    const mediaRaw = oneLine(get("media_url"));
    let media = null, yt = null;
    if (MEDIA_TYPES.includes(type)) {
      const u = mediaRaw ? splitUrl(mediaRaw) : null;
      if (!mediaRaw) err("media_url is empty", "falta media_url");
      else if (!u) err(`media_url "${mediaRaw}": not an https:// link`, `media_url "${mediaRaw}": no es un enlace https://`);
      else if (!hostOk(u.host)) err(`media_url: ${u.host} is not one of the allowed sites (${HOSTS_EN})`, `media_url: ${u.host} no es uno de los sitios permitidos (${HOSTS_ES})`);
      else if (type === "video") {
        yt = youtubeOf(mediaRaw);
        if (yt) media = { kind: "youtube", src: ytWatch(yt.id, yt.short), id: yt.id, short: yt.short, poster: ytPoster(yt.id) };
        else if (/\.(?:mp4|webm)$/i.test(u.path)) media = { kind: "video", src: mediaRaw };
        else err(`media_url "${mediaRaw}": a YouTube video or an https .mp4 / .webm file`, `media_url "${mediaRaw}": un video de YouTube o un archivo https .mp4 / .webm`);
      } else if (type === "audio") {
        if (/\.(?:mp3|m4a|ogg)$/i.test(u.path)) media = { kind: "audio", src: mediaRaw };
        else err(`media_url "${mediaRaw}": an https .mp3 / .m4a / .ogg file`, `media_url "${mediaRaw}": un archivo https .mp3 / .m4a / .ogg`);
      } else if (/\.(?:jpe?g|png|webp)$/i.test(u.path)) media = { kind: "image", src: mediaRaw };
      else err(`media_url "${mediaRaw}": an https .jpg / .png / .webp picture`, `media_url "${mediaRaw}": una imagen https .jpg / .png / .webp`);
    } else if (mediaRaw) err("media_url is only for video, audio and image rows", "media_url es solo para filas video, audio e image");
    const times = { start: null, end: null };
    for (const k of ["start", "end"]) {
      const v = oneLine(get(k));
      if (!v) continue;
      if (type !== "video" && type !== "audio") {
        err(`${k} is only for video and audio rows`, `${k} es solo para filas video y audio`);
        continue;
      }
      const s = secondsOf(v);
      if (s === null) err(`${k} "${v}": seconds (90) or m:ss (1:30)`, `${k} "${v}": segundos (90) o m:ss (1:30)`);
      else times[k] = s;
    }
    const start = times.start ?? (yt && yt.start) ?? null;
    if (start !== null && times.end !== null && times.end <= start) {
      err(`end (${clock(times.end)}) is not after start (${clock(start)})`, `end (${clock(times.end)}) no es posterior a start (${clock(start)})`);
    }

    // qr_url: a link shown as a QR code ({site} / {site_es} for a page of this site: the English page on English
    // slides, the Spanish one on Spanish slides — qr / qr_es) — a page, never a document file: the player prints its
    // address (host and path) under the code, and a visitor never reads "PDF"; source_url: where to check it
    const qrRaw = oneLine(get("qr_url"));
    let qr = null, qrEs = null;
    if (!qrRaw) {
      if (type === "qr") err("qr_url is empty", "falta qr_url");
    } else {
      const resolved = resolveSite(qrRaw, base);
      const u = resolved ? splitUrl(resolved.en) : null;
      if (!u) err(`qr_url "${qrRaw}": an https:// link, or {site}… for a page of this website`, `qr_url "${qrRaw}": un enlace https:// o {site}… para una página de este sitio`);
      else if (!hostOk(u.host)) err(`qr_url: ${u.host} is not one of the allowed sites (${HOSTS_EN})`, `qr_url: ${u.host} no es uno de los sitios permitidos (${HOSTS_ES})`);
      else if (PDF_WORD.test(u.path)) {
        err("qr_url: a link to a document file (its address shows under the code): link to the page that offers the document",
          "qr_url: un enlace a un archivo de documento (su dirección se ve debajo del código): enlaza la página que ofrece el documento");
      } else {
        qr = resolved.en;
        qrEs = resolved.es;
      }
    }
    const srcRaw = oneLine(get("source_url"));
    if (!srcRaw) {
      if (SOURCE_TYPES.includes(type)) err("source_url is empty: where can this be checked? (an https:// link)", "falta source_url: ¿dónde se puede comprobar? (un enlace https://)");
    } else if (!splitUrl(srcRaw)) err(`source_url "${srcRaw}": not an https:// link`, `source_url "${srcRaw}": no es un enlace https://`);

    // every shown cell: placeholders the player knows, and no refused words
    for (const lang of LANGS) {
      for (const f of LANG_FIELDS) {
        const v = L[lang][f];
        if (!v || !takes(f)) continue;
        const name = `${f}_${lang}`;
        const marks = [];
        for (const m of v.matchAll(/\{([^{}]*)\}/g)) if (!PLACEHOLDERS.includes(m[1]) && !marks.includes(m[1])) marks.push(m[1]);
        for (const mk of marks) {
          err(`${name}: {${mk}} is not a placeholder the booth knows ({event}, {committee}, {site})`,
            `${name}: {${mk}} no es un marcador que la pantalla conozca ({event}, {committee}, {site})`);
        }
        for (const hit of refusedIn(v)) err(`${name}: “${hit.word}” is not used on the booth — ${hit.en}`, `${name}: “${hit.word}” no se usa en la pantalla: ${hit.es}`);
      }
    }

    if (errs.length) {
      flush();
      continue;
    }
    if (!on) continue;
    const block = (lang) => (langs.includes(lang) ? {
      title: L[lang].title || null,
      text: L[lang].text || null,
      choices: takes("choices") ? L[lang].list || [] : [],
      answer: takes("answer") ? L[lang].answer || null : null,
      explain: L[lang].explain || null,
      credit: L[lang].credit || null,
      rows: [],
    } : null);
    const mb = media ? mediaBlock({ ...media, start: start ?? 0, end: times.end }) : null;
    items.push({
      id, source: "csv", type, channel: CSV_CHANNEL[type], pub, langs,
      en: block("en"), es: block("es"),
      correct, seconds, reveal, weight, from: dates.from, until: dates.until, tags,
      collection: "csv", first: false, order: null,
      media: mb, online: !!mb, qr, qr_es: qrEs, url: qr || (mb && mb.kind === "youtube" ? mb.src : null),
      until_ts: null,
    });
  }
  return { items, problems, rows: rows.length - 1 };
}

/* ------------------------------------------------------------------ */
/*  The Drive booth folder (data/site/booth.json + the copies saved)    */
/* ------------------------------------------------------------------ */
const isMap = (v) => !!v && typeof v === "object" && !Array.isArray(v);
const arr = (v) => (Array.isArray(v) ? v : []);
const str = (v) => (typeof v === "string" ? v : v === null || v === undefined ? "" : String(v));
const LH3 = /^https:\/\/lh3\.googleusercontent\.com\/\S+$/;
const MEDIA_FILE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/;
const numOr = (v, lo, hi, dflt = null) => (typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi ? v : dflt);
// What the sync and the download step write about a file (English) → the Spanish line (SPEC §1.1, §2.2, §2.3);
// anything else is shown as written. (The sync's problems carry their own Spanish words, problem_es; the download
// step's skipped files a `code`, worded below.)
const DRIVE_ES = {
  "not a type the booth can show": "no es un tipo de archivo que la pantalla pueda mostrar",
  "too big": "demasiado grande",
  "over the folder limit": "pasa el límite de la carpeta",
};
const driveEs = (en) => {
  const k = str(en).trim().toLowerCase();
  return Object.hasOwn(DRIVE_ES, k) ? DRIVE_ES[k] : str(en);
};
// Why the download step (scripts/build/booth-media.mjs: the manifest's skipped[].code) saved no copy of a file, in
// Spanish (its English words, with the sizes, are the manifest's `reason`). "expired" (past its last day) needs no
// note: the file never shows again.
const SKIPPED_ES = {
  too_big: "es demasiado grande para guardarlo para usar sin conexión (config/site.yml booth.max_file_mb)",
  over_limit: "no se guardó para usar sin conexión: los archivos guardados de la carpeta booth pasarían el límite (config/site.yml booth.max_total_mb)",
  no_file: "data/site/booth.json no tiene el id del archivo de Drive",
  out_of_time: "no se descargó: se acabó el tiempo para descargas de esta actualización (la próxima lo vuelve a intentar)",
  html: "Google Drive respondió con una página web en lugar del archivo (demasiadas descargas hoy, o Drive no pudo revisarlo); la próxima actualización lo vuelve a intentar",
  incomplete: "la descarga quedó incompleta o no tenía el tamaño del archivo; la próxima actualización lo vuelve a intentar",
  failed: "la descarga falló; la próxima actualización lo vuelve a intentar",
};

/** The base path of the site's own files ("/aagrapevine/" on GitHub Pages, "/" on a computer or a custom domain) —
 *  as src/pages/manifest.11ty.js and sw.11ty.js work it out (the HTML base plugin only rewrites HTML). */
export function basePath() {
  const prefix = String(process.env.PATH_PREFIX || "/").replace(/^\/+|\/+$/g, "");
  return prefix ? `/${prefix}/` : "/";
}

/**
 * The Drive booth folder's files (data/site/booth.json, SPEC §2.2) as ITEMs, with the copies the deploy saved
 * (.cache/booth-media/manifest.json, §2.3 — published at <base>about/booth/media/):
 *   · a file the manifest lists plays from that copy (local, offline too: media.src "<base>about/booth/media/<file>",
 *     its size, type and a picture's width and height);
 *   · else a photo or poster is shown from Google's copy (lh3, online only);
 *   · else a video or sound file is left out — "not downloaded in this build" (with the reason the download step
 *     gave, "too big" …) — a stream from Drive is not something a booth can count on;
 *   · a note (message) needs no file.
 * Its words: the title (none when the name says "(no caption)" or is a camera's), a note's text; a file without a
 * language is shown in every language mode (langs [], the same words in both). The words the booth never shows
 * (refusedIn — the CSV's rule): a file whose caption, or a note whose heading or text, says one is left out and named
 * (rename the file or change the note; "(no caption)" shows a picture without its title). → { items, problems,
 * collections (the folder's collections that kept an item, with how many) }.
 */
export function driveItems(drive, manifest, base = "/") {
  const items = [];
  const problems = [];
  const d = isMap(drive) ? drive : {};
  const files = isMap(manifest) && isMap(manifest.items) ? manifest.items : {};
  // the download step's skipped files: { reason (English), code } by file id
  const why = new Map(arr(isMap(manifest) ? manifest.skipped : []).filter(isMap).map((s) => [str(s.file_id), { en: str(s.reason), code: str(s.code) }]));
  const listed = arr(d.collections).filter((x) => isMap(x) && /^[a-z0-9][a-z0-9-]*$/.test(str(x.id)));
  const label = new Map(listed.map((x) => [x.id, str(x.label) || x.id]));
  for (const it of arr(d.items)) {
    if (!isMap(it)) continue;
    const fileId = str(it.file_id) || str(it.id).replace(/^drive:/, "");
    const coll = /^[a-z0-9][a-z0-9-]*$/.test(str(it.collection)) ? it.collection : "main";
    const name = oneLine(it.name) || oneLine(it.title) || fileId;
    const where = `Drive: booth/${coll !== "main" ? `${label.get(coll) || coll}/` : ""}${name}`;
    const kind = str(it.kind);
    if (!/^[A-Za-z0-9_-]{6,}$/.test(fileId) || !Object.hasOwn(DRIVE_CHANNEL, kind)) {
      problems.push({ where, en: "not a type the booth can show", es: driveEs("not a type the booth can show") });
      continue;
    }
    const saved = isMap(files[fileId]) && MEDIA_FILE.test(str(files[fileId].file)) ? files[fileId] : null;
    const fit = it.fit === "cover" || it.fit === "contain" ? it.fit : kind === "photo" ? "cover" : "contain";
    const size = (o) => ({ w: numOr(o.w, 1, 1e5), h: numOr(o.h, 1, 1e5), bytes: numOr(o.bytes, 0, 1e12) });
    const local = saved ? { src: `${base}about/booth/media/${saved.file}`, local: true, ...size(saved) } : null;
    let media = null;
    if (kind === "photo" || kind === "poster") {
      if (local) media = mediaBlock({ kind: "image", ...local, fit });
      else if (LH3.test(str(it.image_url))) media = mediaBlock({ kind: "image", src: it.image_url, fit });
      else {
        problems.push({ where, en: "no picture to show: the sync gave no address for it", es: "no hay imagen que mostrar: la sincronización no dio su dirección" });
        continue;
      }
    } else if (kind === "video" || kind === "audio") {
      if (!local) {
        const reason = why.get(fileId);
        // (past its last day since the sync: it would not show anyway — no note)
        if (reason && reason.code === "expired") continue;
        const es = reason ? (Object.hasOwn(SKIPPED_ES, reason.code) ? SKIPPED_ES[reason.code] : driveEs(reason.en)) : "";
        problems.push({
          where,
          en: `not downloaded in this build, so it is left out (videos and sound files play only from the copy saved with the site)${reason && reason.en ? `: ${reason.en}` : ""}`,
          es: `no se descargó en esta actualización, así que queda fuera (los videos y los archivos de sonido solo se reproducen desde la copia guardada con el sitio)${es ? `: ${es}` : ""}`,
        });
        continue;
      }
      const start = numOr(it.start, 0, 86400, 0);
      const end = numOr(it.end, 0, 86400);
      media = mediaBlock({ kind, ...local, start, end: end !== null && end > start ? end : null, muted: it.muted === true, fit });
    }
    const langs = LANGS.filter((l) => arr(it.langs).includes(l));
    const title = it.caption === false ? "" : oneLine(it.title);
    const text = kind === "message" ? cellText(it.text) : "";
    if (kind === "message" && !text) {
      problems.push({ where, en: "the note has no text", es: "la nota no tiene texto" });
      continue;
    }
    // the words the booth never shows (SPEC §1.2, §4 — the same rule as the CSV's cells and the bulletin's posts):
    // the whole file is left out, as a CSV row with a mistake is (a file named "…donate…" may well say it in the
    // picture too, which no check can read). Only the words shown: `title` is "" with "(no caption)".
    const hit = [title, text].flatMap((s) => refusedIn(s))[0];
    if (hit) {
      problems.push({ where, en: fill(BOOTH_WORDS.left_out.en, { word: hit.word }), es: fill(BOOTH_WORDS.left_out.es, { word: hit.word }) });
      continue;
    }
    const block = () => (title || text ? { title: title || null, text: text || null, choices: [], answer: null, explain: null, credit: null, rows: [] } : null);
    const shown = (l) => (langs.length ? langs.includes(l) : true);
    items.push({
      id: `drive:${fileId}`, source: "drive", type: kind, channel: DRIVE_CHANNEL[kind],
      pub: ["gv", "lv", "both"].includes(it.pub) ? it.pub : "both", langs,
      en: shown("en") ? block() : null, es: shown("es") ? block() : null,
      correct: null, seconds: Number.isInteger(it.seconds) ? numOr(it.seconds, 3, 120) : null, reveal: null,
      weight: numOr(it.weight, 0.5, 5, 1), from: DAY.test(str(it.from)) ? it.from : null, until: DAY.test(str(it.until)) ? it.until : null,
      tags: [], collection: coll, first: it.first === true, order: Number.isInteger(it.order) ? it.order : null,
      media, online: !!media && !media.local, qr: null, qr_es: null, url: null, until_ts: null,
    });
  }
  // the files the sync could not use (an unknown type, a note with no text, dates the wrong way round …): its own
  // words in both languages (problem / problem_es)
  for (const p of arr(d.problems)) {
    if (!isMap(p) || !str(p.problem)) continue;
    problems.push({ where: `Drive: ${oneLine(p.file) || "booth"}`, en: oneLine(p.problem), es: oneLine(p.problem_es) || driveEs(oneLine(p.problem)) });
  }
  // the collections that kept an item, in the folder's order (one the list does not name: its id as its label)
  const count = new Map();
  for (const it of items) count.set(it.collection, (count.get(it.collection) || 0) + 1);
  const collections = listed.filter((x) => count.has(x.id)).map((x) => ({ id: x.id, label: label.get(x.id), count: count.get(x.id) }));
  for (const [id, n] of count) if (!label.has(id)) collections.push({ id, label: id === "main" ? "Booth folder" : id, count: n });
  return { items, problems, collections };
}

/* ------------------------------------------------------------------ */
/*  config/site.yml `booth:` (SPEC §1.3)                                */
/* ------------------------------------------------------------------ */
const LANG_MODES = ["en", "es", "both", "alternate"];
const YES = ["true", "yes", "y", "on", "1", "si", "sí"];
const NO = ["false", "no", "n", "off", "0"];

/**
 * config/site.yml `booth:` → { defaults, max_file_mb, max_total_mb, problems }. `defaults` are the player's
 * starting settings on every device, in its settings' own keys (§3.6): { event: { en, es }, lang, sound } — the
 * event's name (es blank: the player uses the English one), the language mode (en | es | both | alternate) and
 * whether the sound starts on. A value it cannot read keeps the player's default and is listed as a problem.
 */
export function boothDefaults(cfg) {
  const problems = [];
  const c = isMap(cfg) ? cfg : {};
  const d = isMap(c.defaults) ? c.defaults : {};
  const where = (k) => `config/site.yml booth.${k}`;
  const name = (k) => {
    const v = d[k];
    if (v === null || v === undefined || v === "") return "";
    if (typeof v === "object" || typeof v === "boolean") {
      problems.push({ where: where(`defaults.${k}`), en: "the event's name must be a text in quotes", es: "el nombre del evento debe ser un texto entre comillas" });
      return "";
    }
    const s = oneLine(v);
    if (len(s) <= 80) return s;
    problems.push({ where: where(`defaults.${k}`), en: `the event's name is ${len(s)} characters long: at most 80`, es: `el nombre del evento tiene ${len(s)} caracteres: 80 como máximo` });
    return [...s].slice(0, 80).join("").replace(TRIM, "");
  };
  const ev = { en: name("event_name"), es: name("event_name_es") };
  let lang = "both";
  if (d.language !== undefined && d.language !== null && d.language !== "") {
    const v = oneLine(d.language).toLowerCase();
    if (LANG_MODES.includes(v)) lang = v;
    else problems.push({ where: where("defaults.language"), en: `"${oneLine(d.language)}" is not en, es, both or alternate: both is used`, es: `"${oneLine(d.language)}" no es en, es, both ni alternate: se usa both` });
  }
  let sound = false;
  if (d.sound !== undefined && d.sound !== null && d.sound !== "") {
    const v = oneLine(d.sound).toLowerCase();
    if (YES.includes(v)) sound = true;
    else if (!NO.includes(v)) problems.push({ where: where("defaults.sound"), en: `"${oneLine(d.sound)}" is not true or false: false is used`, es: `"${oneLine(d.sound)}" no es true ni false: se usa false` });
  }
  const mb = (k, dflt) => {
    const v = c[k];
    if (v === undefined || v === null || v === "") return dflt;
    if (typeof v === "number" && Number.isFinite(v) && v > 0) return v;
    problems.push({ where: where(k), en: `"${oneLine(v)}" is not a number of megabytes: ${dflt} is used`, es: `"${oneLine(v)}" no es un número de megabytes: se usa ${dflt}` });
    return dflt;
  };
  return { defaults: { event: ev, lang, sound }, max_file_mb: mb("max_file_mb", 95), max_total_mb: mb("max_total_mb", 400), problems };
}

/* ------------------------------------------------------------------ */
/*  Loading the owner's files (the `booth` global)                      */
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
  if (s === null) return { found: false, data: null, error: "" };
  try {
    return { found: true, data: JSON.parse(s), error: "" };
  } catch (e) {
    return { found: true, data: null, error: String((e && e.message) || e).split("\n")[0] };
  }
};

/**
 * The `booth` global (src/_data/booth.js): the CSV checked and shaped, the Drive folder's files with their saved
 * copies, the starting settings — everything of the show that does not change with the day's data (boothShow adds
 * the live items when the page is built).
 *   opts.csv / opts.csvText          the CSV's path (content/booth/booth.csv) or its text
 *   opts.drive / opts.driveData      data/site/booth.json's path or its data (missing: no Drive items)
 *   opts.manifest / opts.manifestData  .cache/booth-media/manifest.json's path or its data (missing: no saved copies)
 *   opts.config                      config/site.yml's `booth:` section
 *   opts.site                        the `site` global (its url: {site} in qr_url, the site's own host)
 *   opts.base                        the base path of the site's files (default: PATH_PREFIX, as the pages)
 * → { csv: { file, found, rows, items, problems }, drive: { file, found, updated, items, collections, problems },
 *     manifest: { file, found, built, files }, config: { defaults, max_file_mb, max_total_mb }, base, items (the
 *     CSV's and the Drive's, in that order), problems (all of them) }.
 */
export function loadBooth(opts = {}) {
  const base = opts.base || basePath();
  const csvFile = opts.csv || "content/booth/booth.csv";
  const csvText = typeof opts.csvText === "string" ? opts.csvText : readText(csvFile);
  const csv = csvText === null
    ? { items: [], rows: 0, problems: [{ where: path.basename(csvFile), en: `${csvFile} was not found: the show has no rows from it`, es: `no se encontró ${csvFile}: la pantalla no tiene filas de ese archivo` }] }
    : checkCsv(csvText, { site: opts.site, file: path.basename(csvFile) });
  const driveFile = opts.drive || "data/site/booth.json";
  const dj = opts.driveData !== undefined ? { found: !!opts.driveData, data: opts.driveData, error: "" } : readJson(driveFile);
  const manifestFile = opts.manifest || ".cache/booth-media/manifest.json";
  const mj = opts.manifestData !== undefined ? { found: !!opts.manifestData, data: opts.manifestData, error: "" } : readJson(manifestFile);
  const drive = driveItems(dj.data, mj.found && isMap(mj.data) ? mj.data : null, base);
  if (dj.error) drive.problems.unshift({ where: driveFile, en: `could not be read (${dj.error}): the show has no files from the Drive booth folder`, es: `no se pudo leer (${dj.error}): la pantalla no tiene archivos de la carpeta booth del Drive` });
  const cfg = boothDefaults(opts.config);
  const manifest = isMap(mj.data) ? mj.data : {};
  return {
    csv: { file: csvFile, found: csvText !== null, rows: csv.rows, items: csv.items, problems: csv.problems },
    drive: {
      file: driveFile, found: dj.found, updated: isMap(dj.data) ? dj.data.updated || null : null,
      items: drive.items, collections: drive.collections, problems: drive.problems,
    },
    manifest: { file: manifestFile, found: mj.found && isMap(mj.data), built: manifest.built || null, files: isMap(manifest.items) ? Object.keys(manifest.items).length : 0 },
    config: { defaults: cfg.defaults, max_file_mb: cfg.max_file_mb, max_total_mb: cfg.max_total_mb },
    base,
    items: [...csv.items, ...drive.items],
    problems: [...csv.problems, ...drive.problems, ...cfg.problems],
  };
}

/* ------------------------------------------------------------------ */
/*  The live items (SPEC §2.5): made from the site's data with each build */
/* ------------------------------------------------------------------ */
/** The few words only the booth's live items use, in both languages (everything else they say is the site's own
 *  strings, src/_i18n — the words the pages use for the same thing). The Daily Quote's heading is the feature's own
 *  name, in the quote's language. */
export const BOOTH_WORDS = {
  next_assembly: { en: "Next assembly", es: "Próxima asamblea" },
  quote: { gv: "Grapevine Daily Quote · {date}", lv: "Cita Diaria de La Viña · {date}" },
  on_youtube: { en: "AA Grapevine & La Viña on YouTube", es: "AA Grapevine & La Viña en YouTube" },
  prices_as_of: { en: "Prices as of {date}, from the official stores", es: "Precios al {date}, según las tiendas oficiales" },
  meetings: { en: "Meetings you can join", es: "Reuniones a las que puedes unirte" },
  starts: { en: "Starts {date}", es: "Comienza el {date}" },
  left_out: { en: "left out of the booth: it says “{word}”", es: "queda fuera de la pantalla: dice “{word}”" },
  off_host: { en: "left out of the booth: its sound file is on {host}, not on the podcast's host (captivate.fm)",
    es: "queda fuera de la pantalla: su archivo de sonido está en {host}, no en el sitio del podcast (captivate.fm)" },
  live_failed: { en: "the {part} could not be made, so they are left out ({error})", es: "no se pudo preparar {part}, así que queda fuera ({error})" },
};
const PARTS = {
  events: { en: "events", es: "los eventos" }, quotes: { en: "daily quotes", es: "las citas diarias" },
  videos: { en: "videos", es: "los videos" }, podcast: { en: "podcast episodes", es: "los episodios del podcast" },
  themes: { en: "story themes", es: "los temas para historias" }, prices: { en: "prices", es: "los precios" },
  books: { en: "Books of the Month", es: "los libros del mes" }, meetings: { en: "meetings", es: "las reuniones" },
  bulletin: { en: "bulletin posts", es: "los avisos del boletín" },
};
// Where a live item's problem line says it comes from ("YouTube: <its title>"), as the other lines name a CSV row or
// a Drive file
const LIVE_WHERE = {
  events: "Events", quotes: "Daily Quote", videos: "YouTube", podcast: "Podcast", themes: "Story themes",
  prices: "Prices", books: "Book of the Month", meetings: "Meetings", bulletin: "Bulletin",
};
const MAG = { gv: "Grapevine", lv: "La Viña" };
const fill = (s, vars) => String(s).replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m));
const ymdPlus = (ymd, n) => {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
};
const idSlug = (s) => str(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80);
const instantIso = (v) => {
  const ms = Date.parse(str(v));
  return Number.isFinite(ms) ? new Date(ms).toISOString() : null;
};
/** A text cut to n characters at a word, with "…". */
const clip = (s, n) => {
  const x = oneLine(s);
  if (len(x) <= n) return x;
  return [...x].slice(0, n - 1).join("").replace(new RegExp(`${WS}+\\S*$`, "u"), "").replace(/[\s,;:.–—-]+$/u, "") + "…";
};
/** Markdown-light → plain text (a bulletin post's teaser). */
const plain = (s) => String(s ?? "").replace(/!\[[^\]]*\]\([^)]*\)/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
  .replace(/\*\*|__|`/g, "").replace(/^#+\s*/gm, "").replace(/^>\s?/gm, "");
/** Markdown → one line of plain text, the way the sync flattens a post's body into its teaser (scripts/sync/
 *  announcements.py markdown_to_text): code and tables dropped, a link → its words, heading / quote / list marks and
 *  **bold**, *italic*, `code` marks removed. */
const flatText = (md) => oneLine(String(md ?? "")
  .replace(/```[\s\S]*?```/g, " ").replace(/^\s*\|.*$/gm, " ").replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
  .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/<(https?:\/\/[^>]+)>/g, "$1")
  .replace(/^\s*(?:#{1,6}|>|[-*+]|\d+[.)])\s+/gm, "").replace(/^\s*(?:[-*_]\s*){3,}$/gm, " ")
  .replace(/(\*\*|__|\*|_|~~|`)(?=\S)(.+?)(?<=\S)\1/g, "$2").replace(/<[^>]+>/g, " "));
// a line that is not prose: a heading, a list item, a quote, a table row
const HEADING_LINE = /^#{1,6}(?:\s|$)/;
const BLOCK_LINE = /^(?:#{1,6}(?:\s|$)|[-*+]\s|\d+[.)]\s|>|\|)/;
/**
 * A post's first paragraph (its body, Markdown) as one plain line → { lead, before }: the heading(s) at the top are
 * skipped (`before`: their words — the sync's teaser starts with them), and the paragraph stops at the first heading,
 * list, quote or table line. lead "" when the post starts with a list, a quote or a table (the teaser it has is used).
 * The bulletin's teaser on a slide: the sync's runs every block into one line ("…learn from it. Why it matters A
 * meeting in print…"), a heading and a list included.
 */
function firstParagraph(md) {
  const before = [];
  for (const block of cellText(md).split(/\n{2,}/)) {
    const lines = block.split("\n").map((l) => l.replace(TRIM, ""));
    let i = 0;
    while (i < lines.length && HEADING_LINE.test(lines[i])) before.push(lines[i++]);
    if (i === lines.length) continue;
    if (BLOCK_LINE.test(lines[i])) break;
    let j = i;
    while (j < lines.length && !BLOCK_LINE.test(lines[j])) j++;
    const lead = flatText(lines.slice(i, j).join("\n"));
    if (lead) return { lead, before: flatText(before.join("\n")) };
  }
  return { lead: "", before: "" };
}

/* ------------------------------------------------------------------ */
/*  The words the booth never shows, on a live item (SPEC §4)           */
/* ------------------------------------------------------------------ */
// SPEC §4's rules are for "the CSV and every live item": a live item's words come from the site's data (the
// official channel's titles, the bulletin's posts, the events' names …) and are checked with refusedIn, as a CSV
// row's cells are. A list (events, meetings, story themes, prices) loses only the rows that say one; anything else
// is left out whole. Each is named in `problems` (Settings → Items, the build log): "YouTube: <its title>: left out
// of the booth: it says “Download Now”".
const LIST_TYPES = ["events", "meetings", "themes", "prices"];
// the words a block shows (its rows apart)
const blockWords = (b) => (b ? [b.title, b.text, b.explain, b.credit, ...arr(b.choices)].filter(Boolean) : []);
const rowWords = (r) => [r.title, r.when, r.place, r.note].filter(Boolean);
const firstRefused = (list) => list.flatMap((s) => refusedIn(s))[0] || null;
const leftOut = (where, hit) => ({ where, en: fill(BOOTH_WORDS.left_out.en, { word: hit.word }), es: fill(BOOTH_WORDS.left_out.es, { word: hit.word }) });

/**
 * A live item (liveItem's shape) checked for the words the booth never shows → the item to show (a list without the
 * rows that say one; a language with no row left is not shown) or null (left out). Each word found is a problem line
 * pushed to `problems`, its `where` "<label>: <the item's heading or the row's title>".
 */
function screenLive(it, label, problems) {
  const heading = (it.en && it.en.title) || (it.es && it.es.title) || it.id;
  const hit = firstRefused(LANGS.flatMap((l) => blockWords(it[l])));
  const list = LIST_TYPES.includes(it.type);
  const rowHit = list ? null : firstRefused(LANGS.flatMap((l) => arr(it[l] && it[l].rows).flatMap(rowWords)));
  if (hit || rowHit) {
    problems.push(leftOut(`${label}: ${heading}`, hit || rowHit));
    return null;
  }
  if (!list) return it;
  const out = { ...it };
  let changed = false;
  for (const l of LANGS) {
    if (!out[l] || !out[l].rows.length) continue;
    const rows = out[l].rows.filter((r) => {
      const h = firstRefused(rowWords(r));
      if (h) problems.push(leftOut(`${label}: ${r.title || heading}`, h));
      return !h;
    });
    if (rows.length === out[l].rows.length) continue;
    changed = true;
    out[l] = rows.length ? { ...out[l], rows } : null;
  }
  if (!changed) return it;
  out.langs = it.langs.filter((l) => out[l]);
  return out.langs.length ? out : null;
}

/** The day's context: the template's data (db, site; `now` and `base` for tests) and the clock; a context passed in
 *  again is used as it is, so what several parts read (the events, in each language) is worked out once. */
const CONTEXT = Symbol("booth context");
function context(ctx = {}) {
  if (ctx[CONTEXT]) return ctx;
  const site = ctx.site || {};
  const url = String(site.url || "").replace(/\/+$/, "");
  const now = ctx.now instanceof Date ? ctx.now : nowDate();
  const own = url ? (splitUrl(url + "/") || {}).host : "";
  const memo = new Map();
  // a link a QR code or an item may hold: on an allowed site (SPEC §1.2), else null
  const linkOk = (u) => {
    const s = splitUrl(u);
    return s && (ALLOWED_HOSTS.includes(s.host) || (!!own && s.host === own)) ? String(u) : null;
  };
  return {
    [CONTEXT]: true,
    db: ctx.db || {}, site, now, nowMs: now.getTime(), today: chicagoYmd(now),
    url, prefix: ctx.base || basePath(),
    // a page of the site → its full address ("/events/" → "https://…/aagrapevine/events/"; lang "es": the same
    // page under the Spanish home, ".../es/events/" — a live item's qr_es, the code its Spanish slides show)
    abs: (p, lang) => url + (lang === "es" ? "/es" : "") + (String(p).startsWith("/") ? p : "/" + p),
    linkOk,
    // a link from the data a QR code may show (qr, url): an allowed one that is a page — never a document file
    // (an event's flyer on neta65.org, an offer's leaflet): the player prints the address under the code, and a
    // visitor never reads "PDF" (the CSV's qr_url has the same rule); else null
    qrOk: (u) => {
      const s = linkOk(u);
      return s && !PDF_WORD.test(splitUrl(s).path) ? s : null;
    },
    once: (key, fn) => {
      if (!memo.has(key)) memo.set(key, fn());
      return memo.get(key);
    },
  };
}

// The blocks of a live item (every key of SPEC §2.4, null when not used). A row's `starts_ts` (when it begins, epoch
// ms) is there for the countdown, and for every dated row.
const rowBlock = (r) => ({
  title: r.title || null, when: r.when || null, place: r.place || null, note: r.note || null,
  ends_ts: Number.isFinite(r.ends_ts) ? r.ends_ts : null, pub: r.pub || "both", thumb: r.thumb || null,
  starts_ts: Number.isFinite(r.starts_ts) ? r.starts_ts : null,
});
const textBlock = (b) => (b ? {
  title: b.title || null, text: b.text || null, choices: arr(b.choices), answer: b.answer || null,
  explain: b.explain || null, credit: b.credit || null, rows: arr(b.rows).map(rowBlock),
} : null);
// qr_es: the code on its Spanish slides when that is another address (a page of this site under /es/), else null
function liveItem(o) {
  return {
    id: o.id, source: "live", type: o.type, channel: o.channel, pub: o.pub || "both", langs: o.langs,
    en: textBlock(o.en), es: textBlock(o.es),
    correct: null, seconds: null, reveal: null, weight: 1, from: null, until: null, tags: o.tags || [],
    collection: "live", first: false, order: null,
    media: o.media || null, online: !!o.online, qr: o.qr || null,
    qr_es: o.qr && o.qr_es && o.qr_es !== o.qr ? o.qr_es : null, url: o.url || null,
    until_ts: Number.isFinite(o.until_ts) ? o.until_ts : null,
  };
}

/** The events of /events/ (committee.js normalizeEvents, in a language) that are not over, without the committee
 *  meetings (the meetings item has those), soonest first. */
const upcomingOf = (c, lang) => c.once(`events:${lang}`, () =>
  normalizeEvents((c.db.events && c.db.events.items) || [], c.site, lang, { monthsBack: 0, monthsAhead: 0, now: c.now })
    .filter((e) => !e.past && !e.committee));
const byId = (list) => new Map(list.map((e) => [e.id, e]));
// "Saturday, October 10, 2026 · 5:00 – 8:00 PM CDT"; an event over several days: its range ("Fri, Mar 19 – Sun,
// Mar 21, 2027"), as /events/ writes them
const whenOf = (e) => (e.multiDay ? e.rangeLabel || e.dateLabel : [e.dateLabel, e.timeLabel].filter(Boolean).join(" · "));
// "Details to be confirmed" (tentative), "Online on Zoom" (online or hybrid: the place stays beside it)
const noteOf = (e, lang) => [
  e.tentative ? t("committee.events.tentative", lang) : "",
  e.isOnline ? (e.platform ? t("committee.events.online_on", lang, { platform: e.platform }) : t("committee.events.online", lang)) : "",
].filter(Boolean).join(" · ");
const eventRow = (c, e, lang) => {
  const th = str(e.flyer && e.flyer.thumb);
  return {
    title: e.title, when: whenOf(e), place: e.location || "", note: noteOf(e, lang),
    ends_ts: e.endMs, starts_ts: e.startMs, pub: e.host === "lv" || e.host === "gv" ? e.host : "both",
    // the flyer's small picture (online, like every Drive picture): Google's copy, or one the site keeps
    thumb: /^https:\/\//.test(th) ? th : /^\/[^/]/.test(th) ? c.prefix + th.slice(1) : null,
  };
};

/** live-events: the next four events (a monthly series once: its next date) as one list, each row until it is over;
 *  and a countdown to the next NETA 65 assembly (event-tone.js: an assembly of ours), until it begins. */
function liveEvents(c) {
  const en = upcomingOf(c, "en");
  if (!en.length) return [];
  const es = byId(upcomingOf(c, "es"));
  const pick = [];
  const series = new Set();
  for (const e of en) {
    const key = e.series || e.seriesOf;
    if (key) {
      if (series.has(key)) continue;
      series.add(key);
    }
    pick.push(e);
    if (pick.length === 4) break;
  }
  const rows = (lang) => pick.map((e) => eventRow(c, lang === "es" ? es.get(e.id) || e : e, lang));
  const page = c.linkOk(c.abs("/events/"));
  const pageEs = c.linkOk(c.abs("/events/", "es"));
  const out = [liveItem({
    id: "live:events:next", type: "events", channel: "live-events", langs: ["en", "es"],
    en: { title: t("committee.events.upcoming", "en"), rows: rows("en") },
    es: { title: t("committee.events.upcoming", "es"), rows: rows("es") },
    qr: page, qr_es: pageEs, url: page, until_ts: Math.max(...pick.map((e) => e.endMs)),
  })];
  const asm = en.find((e) => e.group === "neta" && eventTone(e) === "assembly" && e.startMs > c.nowMs);
  if (asm) {
    const ae = es.get(asm.id) || asm;
    // (its card on /events/ — on /es/events/ for the Spanish slides — or its own page; a flyer's document: /events/)
    const link = c.qrOk(asm.detailsUrl) || page;
    out.push(liveItem({
      id: `live:countdown:${idSlug(asm.id)}`, type: "countdown", channel: "live-events", langs: ["en", "es"],
      en: { title: BOOTH_WORDS.next_assembly.en, text: asm.title, rows: [eventRow(c, asm, "en")] },
      es: { title: BOOTH_WORDS.next_assembly.es, text: ae.title, rows: [eventRow(c, ae, "es")] },
      qr: link, qr_es: c.qrOk(ae.detailsUrl) || pageEs, url: link, until_ts: asm.startMs,
    }));
  }
  return out;
}

/** live-quote: Grapevine's Daily Quote and La Viña's Cita Diaria, as the Home page shows them (home.js
 *  homeDailyQuotes: a quote of the last two days, exactly as published, in its own language, with its attribution
 *  and a link to the official page) — each until the Home page would drop it. */
function liveQuotes(c) {
  const out = [];
  const cutoff = ymdPlus(c.today, -2);
  for (const q of arr(c.db.quote && c.db.quote.items)) {
    if (!isMap(q) || (q.pub !== "gv" && q.pub !== "lv") || out.some((x) => x.pub === q.pub)) continue;
    const text = cellText(q.text);
    const day = str(q.date).slice(0, 10);
    const link = c.linkOk(str(q.url));
    if (!text || !link || !DAY.test(day) || day < cutoff) continue;
    const lang = q.lang === "es" || q.lang === "en" ? q.lang : q.pub === "lv" ? "es" : "en";
    const label = new Intl.DateTimeFormat(LOCALES[lang], lang === "es" ? { day: "numeric", month: "long", timeZone: "UTC" }
      : { month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${day}T12:00:00Z`));
    const from = oneLine(q.source);
    const credit = [oneLine(q.attribution), from ? `${t("home.quote_from", lang)} ${from}` : ""].filter(Boolean).join(" · ");
    out.push(liveItem({
      id: `live:quote:${q.pub}`, type: "quote", channel: "live-quote", pub: q.pub, langs: [lang],
      [lang]: { title: fill(BOOTH_WORDS.quote[q.pub], { date: label }), text, credit },
      qr: c.qrOk(link), url: c.qrOk(link), until_ts: chicagoDayEndMs(ymdPlus(day, 2)),
    }));
  }
  return out;
}

/** A YouTube video of the official channel as an item (its own language, its channel's colour). */
const videoItem = (id, o) => liveItem({
  id: `live:video:${id}`, type: "video", channel: "live-video", pub: o.pub, langs: [o.lang],
  [o.lang]: { title: o.title, credit: BOOTH_WORDS.on_youtube[o.lang] },
  media: mediaBlock({ kind: "youtube", src: ytWatch(id, o.short), id, short: o.short, poster: ytPoster(id) }),
  online: true, url: ytWatch(id, o.short),
});

/** live-video: the official Grapevine / La Viña YouTube channel (db.videos) — the committee's own choice first
 *  (config/site.yml about_videos, as /about/#videos shows them), then the newest 30 Shorts and videos of 8 minutes or
 *  less; never a recording of a weekly open meeting or a live stream (an AA meeting is not a booth video). A video a
 *  CSV row already plays is left to that row. A title that says a word the booth never shows ("Download Now! Then
 *  Subscribe!") leaves its video out and named (screenLive) — not given another heading: YouTube's player prints the
 *  title in its own top bar, and the video is that call — and the next one takes its place among the 30.
 *  → { items, problems }. */
function liveVideos(c, used) {
  const problems = [];
  const keep = (item) => screenLive(item, LIVE_WHERE.videos, problems);
  const items = arr(c.db.videos && c.db.videos.items).filter((it) => isMap(it) && it.status !== "gone");
  const idOf = (it) => str(it.extra && it.extra.video_id) || str(it.id).replace(/^yt:/, "");
  const recording = (it) => {
    const x = it.extra || {};
    const tags = arr(it.tags).map(String);
    return x.is_live_recording === true || tags.includes("live") || tags.includes("weekly-open")
      || arr(x.playlists).some((p) => /weekly open/i.test(String(p))) || /weekly open/i.test(str(it.title));
  };
  const brief = (it) => {
    const x = it.extra || {};
    const sec = Number(x.duration_sec);
    return x.is_short === true || (sec > 0 && sec <= 480);
  };
  const seen = new Set(used);
  const out = [];
  for (const v of aboutVideos(c.site.about_videos, items, "en")) {
    const it = items.find((i) => idOf(i) === v.id);
    if (seen.has(v.id) || (it && recording(it))) continue;
    seen.add(v.id);
    const item = keep(videoItem(v.id, { pub: v.pub, lang: v.lang, title: v.title, short: !!(it && it.extra && it.extra.is_short === true) }));
    if (item) out.push(item);
  }
  const newest = items.filter((it) => /^[A-Za-z0-9_-]{11}$/.test(idOf(it)) && !recording(it) && brief(it))
    .sort((a, b) => str(b.date).localeCompare(str(a.date)));
  let n = 0;
  for (const it of newest) {
    if (n >= 30) break;
    const id = idOf(it);
    if (seen.has(id)) continue;
    seen.add(id);
    const lang = it.lang === "es" ? "es" : "en";
    const title = oneLine((it.i18n && it.i18n.title && it.i18n.title[lang]) || it.title);
    // (checked before it counts: one left out does not shorten the list)
    const item = keep(videoItem(id, { pub: it.category === "lv" ? "lv" : "gv", lang, title, short: !!(it.extra && it.extra.is_short === true) }));
    if (!item) continue;
    n++;
    out.push(item);
  }
  return { items: out, problems };
}

/** live-podcast: the six newest episodes of AA Grapevine's podcast (db.episodes, show "gv" — never the weekly open
 *  meeting's recordings), streamed from the official podcast host (captivate.fm: an episode whose sound file is on
 *  another site is left out, and named while it is newer than the ones shown — a new address of the host needs
 *  adding to ALLOWED_HOSTS). No picture: the show's artwork is the AA GRAPEVINE logo, which is Grapevine's artwork
 *  (SPEC §4, research.md D3: no logos on a slide), so the slide shows the headphones icon and the offline copy keeps
 *  no picture. An episode a CSV row already plays is left to that row. → { items, problems }. */
function livePodcast(c, used) {
  const out = [];
  const problems = [];
  const eps = arr(c.db.episodes && c.db.episodes.items)
    .filter((it) => isMap(it) && it.status !== "gone" && (str(it.extra && it.extra.show) || str(it.category)) === "gv")
    .sort((a, b) => str(b.date).localeCompare(str(a.date)));
  for (const it of eps) {
    if (out.length >= 6) break;
    const x = it.extra || {};
    const src = str(x.audio_url);
    if (!c.linkOk(src)) {
      const u = splitUrl(src);
      if (u) problems.push({ where: `${LIVE_WHERE.podcast}: ${oneLine(it.title) || src}`, en: fill(BOOTH_WORDS.off_host.en, { host: u.host }), es: fill(BOOTH_WORDS.off_host.es, { host: u.host }) });
      continue;
    }
    if (used.includes(src)) continue;
    const key = str(it.id).split(":").pop().replace(/[^A-Za-z0-9_-]/g, "") || idSlug(src);
    // (checked before it counts: one left out does not shorten the list)
    const item = screenLive(liveItem({
      id: `live:podcast:${key}`, type: "audio", channel: "live-podcast", pub: "gv", langs: ["en"],
      en: { title: oneLine(it.title), text: oneLine(x.show_name) || null },
      media: mediaBlock({ kind: "audio", src, poster: null }),
      online: true, url: c.qrOk(str(it.url)) || c.qrOk(str(x.player_url)), tags: ["podcast"],
    }), LIVE_WHERE.podcast, problems);
    if (item) out.push(item);
  }
  return { items: out, problems };
}

/** live-themes: the next three story themes of each magazine with a deadline still ahead (read.js editorialFor —
 *  the calendar /contribute/ shows): the theme in the magazine's own language, the other language beside it; the
 *  issue; the due date — each row until its day is over. */
function liveThemes(c) {
  const rows = { en: [], es: [] };
  const ed = (c.db.editorial && c.db.editorial.items) || [];
  for (const pub of ["gv", "lv"]) {
    const es = new Map(editorialFor(ed, pub, H, "es").upcoming.map((v) => [v.item && v.item.id, v]));
    for (const v of editorialFor(ed, pub, H, "en").upcoming.filter((x) => x.deadline && x.deadline >= c.today).slice(0, 3)) {
      for (const [lang, x] of [["en", v], ["es", es.get(v.item && v.item.id) || v]]) {
        rows[lang].push({
          title: x.original ? `${x.original} (${x.theme})` : x.theme,
          when: t("home.deadline", lang, { date: dayLabel(v.deadline, lang) }),
          note: [MAG[pub], issueName(v.issueKey, pub, lang) || x.issueLabel].filter(Boolean).join(" · "),
          ends_ts: chicagoDayEndMs(v.deadline), pub, day: v.deadline,
        });
      }
    }
  }
  if (!rows.en.length) return [];
  const order = (a, b) => a.day.localeCompare(b.day) || (a.pub === b.pub ? 0 : a.pub === "gv" ? -1 : 1);
  rows.en.sort(order);
  rows.es.sort(order);
  return [liveItem({
    id: "live:themes:next", type: "themes", channel: "live-themes", langs: ["en", "es"],
    en: { title: t("read.contrib.deadlines_title", "en"), rows: rows.en },
    es: { title: t("read.contrib.deadlines_title", "es"), rows: rows.es },
    qr: c.linkOk(c.abs("/contribute/")), qr_es: c.linkOk(c.abs("/contribute/", "es")), url: c.linkOk(c.abs("/contribute/#deadlines")),
    until_ts: Math.max(...rows.en.map((r) => r.ends_ts)), tags: ["writing"],
  })];
}

/** The U.S. 1-year print / digital plan of a magazine (shop.json subscriptions). */
const yearPlan = (shop, pub, type) => {
  const reg = arr(shop.subscriptions).find((s) => isMap(s) && s.pub === pub && s.region === "us");
  return arr(reg && reg.plans).find((p) => isMap(p) && p.type === type && Number(p.term_months) === 12 && Number(p.price) > 0) || null;
};

/** live-prices: the 1-year print and digital subscriptions of both magazines, as information — "Prices as of …, from
 *  the official stores" (the day the stores were read) and, while an announced change is ahead, the new price beside
 *  the plan ("From Jan 1, 2027: $39.00", the Shop's own words), until that day; never an urgent word. */
function livePrices(c) {
  const shop = isMap(c.db.shop) ? c.db.shop : {};
  const next = shopNextChange(shop, c.now);
  const pending = next && Date.parse(next.at.announced) <= c.nowMs ? next : null;
  const rows = { en: [], es: [] };
  for (const pub of ["gv", "lv"]) {
    for (const type of ["print", "digital"]) {
      const p = yearPlan(shop, pub, type);
      if (!p) continue;
      const now = shopPlanPrice(p, shop, "now", c.now);
      const then = pending && p.change && p.change.key === pending.key ? shopPlanPrice(p, shop, "after", c.now) : null;
      for (const lang of LANGS) {
        const price = money(now, lang);
        const later = then !== null ? money(then, lang) : "";
        rows[lang].push({
          title: `${MAG[pub]} · ${t(`shop.type_${type}`, lang)} · ${t("shop.term_year", lang)}`,
          when: price,
          note: later && later !== price ? t("shop.pc_from", lang, { date: dayLabel(pending.effective, lang, true), price: later }) : "",
          pub,
        });
      }
    }
  }
  if (!rows.en.length) return [];
  const read = chicagoYmd(shop.updated) || c.today;
  const page = c.linkOk(c.abs("/shop/#subscriptions"));
  return [liveItem({
    id: "live:prices:subscriptions", type: "prices", channel: "live-prices", langs: ["en", "es"],
    en: { title: t("shop.nav_subs", "en"), text: fill(BOOTH_WORDS.prices_as_of.en, { date: dayLabel(read, "en") }), rows: rows.en },
    es: { title: t("shop.nav_subs", "es"), text: fill(BOOTH_WORDS.prices_as_of.es, { date: dayLabel(read, "es") }), rows: rows.es },
    qr: page, qr_es: c.linkOk(c.abs("/shop/#subscriptions", "es")), url: page,
    until_ts: pending ? Date.parse(pending.at.effective) : null, tags: ["prices", "subscribe"],
  })];
}

/** live-book: Grapevine's Book of the Month and La Viña's Libro del mes (shop.js shopBotm: an offer not over, its
 *  prices only while they are the store's current ones) — the title it is sold under, a short blurb (200
 *  characters), the offer in words; NO cover (a book cover is Grapevine artwork); the QR goes to the official store
 *  page. A book in the other language says so on the slide's first line, as /shop/ does: "En inglés · Traducción
 *  del título: Pase lo que pase…" (its language, its title's translation — an automatic one says so). Until the
 *  offer ends. */
function liveBooks(c) {
  const shop = isMap(c.db.shop) ? c.db.shop : {};
  const tr = (k, l, v) => H.translateKey(k, l, v);
  const views = { en: shopBotm(shop, "en", c.today, tr, c.now), es: shopBotm(shop, "es", c.today, tr, c.now) };
  const out = [];
  for (const pub of ["gv", "lv"]) {
    const ve = views.en.find((v) => v.pub === pub);
    const vs = views.es.find((v) => v.pub === pub);
    if (!ve || !vs) continue;
    const block = (v, lang) => {
      const blurb = refusedIn(v.blurb).length ? "" : clip(v.blurb, 200);
      // (in `text`, not the credit line: a slide in both languages shows each language's text, the lead one's credit)
      const other = LANGS.includes(v.itemLang) && v.itemLang !== lang;
      const gloss = other && v.subtitle ? `${t(v.subtitleMachine ? "common.auto_translated" : "shop.title_tr", lang)}: ${v.subtitle}` : "";
      const head = other ? [t(`committee.weekly.lang_${v.itemLang}`, lang), gloss].filter(Boolean).join(" · ") : "";
      return {
        title: v.title,
        text: [head, blurb].filter(Boolean).join("\n"),
        credit: [MAG[pub], t("monthly.botm", lang), v.monthLabel].filter(Boolean).join(" · "),
        explain: v.hasPrices && v.endsLabel ? t("orientation.live_botm_price", lang, { sale: v.sale, price: v.price, date: v.endsLabel })
          : v.pct && v.endsLabel ? t("monthly.botm_off", lang, { pct: v.pct, date: v.endsLabel })
            : v.endsLabel ? t("monthly.botm_until", lang, { date: v.endsLabel }) : "",
      };
    };
    const link = c.qrOk(ve.url) || c.qrOk(ve.pageUrl);
    out.push(liveItem({
      id: `live:book:${pub}`, type: "book", channel: "live-book", pub, langs: ["en", "es"],
      en: block(ve, "en"), es: block(vs, "es"), qr: link, url: link,
      until_ts: DAY.test(str(ve.ends)) ? chicagoDayEndMs(ve.ends) : null, tags: ["books"],
    }));
  }
  return out;
}

/** live-meetings: the meetings anyone can join — the committee's monthly meeting (config/site.yml `meeting:`, its rule
 *  as /meetings/ writes it), the weekly open meetings of Grapevine and La Viña (db.weekly_open, committee.js
 *  weeklyOpenAll) and La Viña's monthly workshop on Zoom (its next date: config/site.yml recurring_events, host lv).
 *  A meeting in the other language says so, as /meetings/ does — "Grapevine Weekly Open AA Meeting (en inglés)" —
 *  unless its title already does (config/site.yml writes La Viña's English titles "… (in Spanish)"); the committee's
 *  own meeting has no language of its own. */
function liveMeetings(c) {
  const rows = { en: [], es: [] };
  const marked = (title, own, lang) => {
    if (!LANGS.includes(own) || own === lang) return title;
    const mark = t(own === "en" ? "access.in_english" : "access.in_spanish", lang);
    return title.toLowerCase().includes(mark.replace(/[()]/g, "").toLowerCase()) ? title : `${title} ${mark}`;
  };
  const m = isMap(c.site.meeting) ? c.site.meeting : {};
  if (Object.keys(m).length) {
    const rule = monthlyRule(m);
    for (const lang of LANGS) {
      rows[lang].push({
        title: meetingTitle(c.site, lang),
        when: recurrenceText(rule, lang),
        note: [t("committee.events.online_on", lang, { platform: oneLine(m.platform) || "Zoom" }),
          m.meeting_id ? `${t("committee.meeting.id", lang)} ${oneLine(m.meeting_id)}` : ""].filter(Boolean).join(" · "),
        pub: "both",
      });
    }
  }
  const wo = arr(c.db.weekly_open && c.db.weekly_open.items);
  for (const lang of LANGS) {
    for (const w of weeklyOpenAll(wo, lang, c.now).sort((a, b) => Number(a.isLv) - Number(b.isLv))) {
      rows[lang].push({
        title: marked(w.title, w.lang, lang), when: w.when,
        note: w.starts ? fill(BOOTH_WORDS.starts[lang], { date: w.starts.date }) : w.zoomId ? `Zoom ${w.zoomId}` : "",
        pub: w.isLv ? "lv" : "gv", starts_ts: w.starts ? Date.parse(w.starts.iso) : null,
      });
    }
  }
  const ws = upcomingOf(c, "en").find((e) => e.recurring && e.host === "lv");
  if (ws) {
    const wsEs = byId(upcomingOf(c, "es")).get(ws.id) || ws;
    for (const [lang, e] of [["en", ws], ["es", wsEs]]) {
      rows[lang].push({
        // (La Viña's workshop is in Spanish)
        title: marked(e.title, "es", lang), when: [e.dateLabel, e.timeLabel].filter(Boolean).join(" · "), note: noteOf(e, lang),
        ends_ts: e.endMs, starts_ts: e.startMs, pub: "lv",
      });
    }
  }
  if (!rows.en.length) return [];
  const page = c.linkOk(c.abs("/meetings/"));
  return [liveItem({
    id: "live:meetings:next", type: "meetings", channel: "live-meetings", langs: ["en", "es"],
    en: { title: BOOTH_WORDS.meetings.en, rows: rows.en }, es: { title: BOOTH_WORDS.meetings.es, rows: rows.es },
    qr: page, qr_es: c.linkOk(c.abs("/meetings/", "es")), url: page, tags: ["online"],
  })];
}

// A post's body in a language (Markdown): its translation, or the body itself in the post's own language — never the
// English body on a Spanish slide (the post's Spanish teaser is used then).
const bodyOf = (p, lang) => {
  const i = isMap(p.i18n) && isMap(p.i18n.body_md) ? p.i18n.body_md : null;
  if (i && typeof i[lang] === "string" && i[lang].trim()) return i[lang];
  return lang === (p.lang === "es" ? "es" : "en") ? str(p.extra && p.extra.body_md) : "";
};

/** live-bulletin: the bulletin's two newest posts (committee.js announcementList: pinned first, none past its
 *  `expires` day) as messages — the title and its teaser in each language, the QR to the post on /bulletin/ — each
 *  until its `expires` day is over. The teaser: the post's first paragraph when its summary is the one the sync makes
 *  from the body (every block run into one line — headings and lists included: "…learn from it. Why it matters A
 *  meeting in print…"), else its summary (one written by hand); 280 characters at most. A post that says a word the
 *  booth never shows is left out and named (screenLive), and the next post takes its place. */
function liveBulletin(c) {
  const items = [];
  const problems = [];
  for (const p of announcementList(arr(c.db.announcements && c.db.announcements.items), c.now)) {
    if (items.length >= 2) break;
    // the sync's summary starts with the body's first words (its headings, then the first paragraph) — cut at 400
    // characters with "…" when the paragraph is longer
    const first = firstParagraph(bodyOf(p, p.lang === "es" ? "es" : "en"));
    const sum = oneLine(p.summary);
    const start = oneLine(`${first.before} ${first.lead}`);
    const fromBody = !!first.lead && (sum.startsWith(start) || (sum.length > 1 && sum.endsWith("…") && start.startsWith(sum.slice(0, -1))));
    const words = (lang) => ({
      title: oneLine(H.pickLang(p, "title", lang) || p.title),
      text: clip((fromBody && firstParagraph(bodyOf(p, lang)).lead) || plain(H.pickLang(p, "summary", lang) || p.summary || ""), 280),
    });
    const en = words("en"), es = words("es");
    if (!en.title && !es.title) continue;
    const link = c.linkOk(c.abs(`/bulletin/#${p._anchor}`));
    const exp = str(p.extra && p.extra.expires).slice(0, 10);
    // (checked before it counts: one left out does not shorten the list)
    const item = screenLive(liveItem({
      id: `live:bulletin:${p._anchor}`, type: "message", channel: "live-bulletin", langs: ["en", "es"],
      en, es, qr: link, qr_es: c.linkOk(c.abs(`/bulletin/#${p._anchor}`, "es")), url: link,
      until_ts: DAY.test(exp) ? chicagoDayEndMs(exp) : null,
    }), LIVE_WHERE.bulletin, problems);
    if (item) items.push(item);
  }
  return { items, problems };
}

/**
 * The live items of the day (SPEC §2.5) → { items, problems }, in this order: events and the assembly countdown,
 * the daily quotes, videos, podcast episodes, story themes, prices, the Books of the Month, meetings, bulletin
 * posts. `used`: { youtube: [ids], audio: [srcs] } the CSV already plays (left to its rows). Every item's words are
 * checked for the words the booth never shows (screenLive: a list loses the rows that say one, anything else is left
 * out — named in `problems`; the parts with a quota — videos, podcast, bulletin — check before they count). A part
 * that fails on odd data is left out with a problem line — the show and the build go on.
 */
export function liveItems(ctx, used = {}) {
  const c = context(ctx);
  const items = [];
  const problems = [];
  // each part → its items, or { items, problems } (a part that names what it left out)
  const parts = [
    ["events", () => liveEvents(c)], ["quotes", () => liveQuotes(c)], ["videos", () => liveVideos(c, arr(used.youtube))],
    ["podcast", () => livePodcast(c, arr(used.audio))], ["themes", () => liveThemes(c)], ["prices", () => livePrices(c)],
    ["books", () => liveBooks(c)], ["meetings", () => liveMeetings(c)], ["bulletin", () => liveBulletin(c)],
  ];
  for (const [part, make] of parts) {
    try {
      const made = make();
      const list = Array.isArray(made) ? made : arr(made && made.items);
      if (!Array.isArray(made)) problems.push(...arr(made && made.problems));
      for (const it of list) {
        const kept = screenLive(it, LIVE_WHERE[part], problems);
        if (kept) items.push(kept);
      }
    } catch (e) {
      const error = String((e && e.message) || e).split("\n")[0];
      console.warn(`[booth] the live ${part} could not be made: ${error}`);
      problems.push({ where: "Live items", en: fill(BOOTH_WORDS.live_failed.en, { part: PARTS[part].en, error }), es: fill(BOOTH_WORDS.live_failed.es, { part: PARTS[part].es, error }) });
    }
  }
  return { items, problems };
}

/** "Pick the event" (the player's Settings → Event): the next twelve events a booth could be at — every date of
 *  /events/ that is not over, not a committee meeting and not only online — with their names and dates in both
 *  languages and the place (left blank while the venue is to be announced). */
export function eventsPick(ctx) {
  const c = context(ctx);
  const es = byId(upcomingOf(c, "es"));
  return upcomingOf(c, "en").filter((e) => e.location || !e.isOnline).slice(0, 12).map((e) => {
    const x = es.get(e.id) || e;
    return {
      id: e.id, title_en: e.title, title_es: x.title, date_label_en: e.rangeLabel || e.dateLabel,
      date_label_es: x.rangeLabel || x.dateLabel, place: e.locationTba ? "" : e.location || "",
    };
  });
}

/* ------------------------------------------------------------------ */
/*  The show: /about/booth.json (SPEC §2.4)                             */
/* ------------------------------------------------------------------ */
// A stable text of a value (keys sorted), for the version: the same show gives the same version in every build.
function canon(v) {
  if (Array.isArray(v)) return `[${v.map(canon).join(",")}]`;
  if (isMap(v)) return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canon(v[k])}`).join(",")}}`;
  return JSON.stringify(v === undefined ? null : v);
}

/**
 * The whole /about/booth.json (SPEC §2.4) from the `booth` global (loadBooth) and the template's data (ctx: db,
 * site, meeting; `now` and `base` for tests):
 *   { app: "gv-booth", schema: 1, version (12 hex: the items and the defaults — a new version is what makes a
 *     running player swap the show), built, as_of (Central day), site: { url, url_es, base, host, committee_en,
 *     committee_es }, defaults, collections, channels (those with items, how many), events_pick, items (the CSV's,
 *     the Drive folder's, the live ones), qr ({ address: SVG } — every item's QR target, English (item.qr) and
 *     Spanish (item.qr_es), and both site homes, community.js qrSvg), problems ([{ where, en, es }]) }
 * An ITEM's qr is the code its English slides show; qr_es, when it is another address (a page of this site under
 * /es/: a CSV qr_url written {site}…, a live list's page), the code its Spanish slides show (the player's
 * GVB.qrOf). A CSV row playing a YouTube video that the channel's list knows as a Short is shown as one.
 */
export function boothShow(booth, ctx = {}) {
  const c = context(ctx);
  const b = isMap(booth) ? booth : loadBooth({ site: c.site, base: c.prefix });
  const shorts = new Set(arr(c.db.videos && c.db.videos.items)
    .filter((v) => isMap(v) && v.extra && v.extra.is_short === true).map((v) => str(v.extra.video_id)));
  const csvItems = arr(b.csv && b.csv.items).map((it) => (it.media && it.media.kind === "youtube" && !it.media.short && shorts.has(it.media.id)
    ? { ...it, media: { ...it.media, short: true } } : it));
  const live = liveItems(c, {
    youtube: csvItems.filter((it) => it.media && it.media.kind === "youtube").map((it) => it.media.id),
    audio: csvItems.filter((it) => it.media && it.media.kind === "audio").map((it) => it.media.src),
  });
  const items = [...csvItems, ...arr(b.drive && b.drive.items), ...live.items];
  const defaults = (b.config && b.config.defaults) || boothDefaults({}).defaults;
  const url = c.url ? c.url + "/" : "";
  const site = {
    url, url_es: url ? url + "es/" : "", base: c.prefix, host: c.url.replace(/^https?:\/\//, ""),
    committee_en: str(c.site.committee), committee_es: str(c.site.committee_es) || str(c.site.committee),
  };
  // every code a slide may show: its English one (qr), its Spanish one (qr_es) and the site's two homes
  const targets = [];
  for (const u of [...items.flatMap((it) => [it.qr, it.qr_es]), site.url, site.url_es]) if (u && !targets.includes(u)) targets.push(u);
  const count = {};
  for (const it of items) count[it.channel] = (count[it.channel] || 0) + 1;
  return {
    app: "gv-booth",
    schema: 1,
    version: crypto.createHash("sha1").update(canon(items)).update(canon(defaults)).digest("hex").slice(0, 12),
    built: instantIso(c.site.built) || new Date().toISOString(),
    as_of: c.today,
    site,
    defaults,
    collections: arr(b.drive && b.drive.collections),
    channels: CHANNELS.filter((ch) => count[ch]).map((id) => ({ id, count: count[id] })),
    events_pick: eventsPick(c),
    items,
    qr: Object.fromEntries(targets.map((u) => [u, qrSvg(u, { margin: 2 })])),
    problems: [...arr(b.problems), ...live.problems],
  };
}

export default function (eleventyConfig, helpers) {
  if (helpers) H = { ...H, ...helpers };
  // {{ booth | boothJson(data) }} — src/pages/booth-json.11ty.js: this.boothJson(data.booth, data)
  eleventyConfig.addFilter("boothJson", (booth, data) => JSON.stringify(boothShow(booth, data || {})) + "\n");
}
