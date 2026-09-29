// Filters for the "community" pages: What's New, Monthly Digest, Share Kit (QR), Status, RSS feeds
// and sitemap. (The district report on /monthly/#report has its own file: report.js.)
//
// Everything here is pure data shaping (no network), so the pages keep
// working with empty data and the build never fails because a source was
// down. Plain-text messages (WhatsApp / e-mail / district report) are built
// here rather than in Nunjucks because exact line breaks matter in them.
import QRCode from "qrcode";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { safeUrl } from "../../eleventy.config.js";
// The monthly digest groups the committee's photos into the albums of /photos/ (the same anchors).
import { ownLangs, chicagoDayEndMs, isPhotoItem, photoAlbumKey, photoAlbumSlugs } from "./committee.js";
// The monthly digest names its months like /monthly/ (monthLabel), finds the committee meeting of the
// month it covers by the same rule (meetingByRule) and gives an issue the toolkit's theme (issueTheme).
// (monthly.js imports from this file too: the cycle is safe, both only call each other's functions.)
import { nowDate, addMonths, monthLabel, meetingByRule, issueTheme } from "./monthly.js";
// An issue is "current" when /read/ shows it as the newest of its magazine (the page's own rule).
import { groupIssues } from "./read.js";

const TZ = "America/Chicago";
const LOCALES = { en: "en-US", es: "es-US" };
const DAY = 864e5;

/* ------------------------------------------------------------------ */
/*  Content groups (one per What's New filter chip / digest section)   */
/* ------------------------------------------------------------------ */
// `page` = where "see all" links go; `emoji` = WhatsApp bullet.
export const GROUPS = {
  announcement: { icon: "megaphone", tone: "vine", page: "/bulletin/", emoji: "📣" },
  article: { icon: "newspaper", tone: "gv", page: "/read/", emoji: "📰" },
  episode: { icon: "headphones", tone: "grape", page: "/listen/", emoji: "🎧" },
  video: { icon: "circle-play", tone: "grape", page: "/watch/", emoji: "🎬" },
  post: { icon: "instagram", tone: "grape", page: "/instagram/", emoji: "📸" },
  pdf: { icon: "file-text", tone: "gv", page: "/library/", emoji: "📄" },
  drive: { icon: "folder-open", tone: "vine", page: "/portfolio/", emoji: "📁" },
  event: { icon: "calendar-days", tone: "vine", page: "/events/", emoji: "📅" },
  topic: { icon: "pen-line", tone: "lv", page: "/contribute/", emoji: "✍️" },
  other: { icon: "sparkles", tone: "muted", page: "/whats-new/", emoji: "•" },
};
// Filter-chip order on What's New.
export const CHIP_ORDER = ["article", "pdf", "episode", "video", "post", "drive", "announcement", "event", "topic", "other"];

const DRIVE_ICONS = { photo: "image", slides: "presentation", document: "file", video_file: "film", form: "clipboard-list" };

/* ------------------------------------------------------------------ */
/*  Small helpers                                                      */
/* ------------------------------------------------------------------ */
function toDate(v) {
  if (!v) return null;
  if (v instanceof Date) return isNaN(v) ? null : v;
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)) return new Date(v + "T12:00:00Z");
  const d = new Date(v);
  return isNaN(d) ? null : d;
}
const ms = (v) => { const d = toDate(v); return d ? d.getTime() : 0; };
const isDateOnly = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);

/** YYYY-MM-DD of a moment in Central time (used for day grouping). */
export function ymdChicago(v) {
  if (isDateOnly(v)) return v;
  const d = toDate(v);
  if (!d) return "";
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

function fmt(v, lang, opts) {
  const d = toDate(v);
  if (!d) return "";
  let s = new Intl.DateTimeFormat(LOCALES[lang] || "en-US", { timeZone: TZ, ...opts }).format(d);
  if (lang === "es") s = esMeridiem(s.charAt(0).toUpperCase() + s.slice(1));
  return s;
}
/** Intl's Spanish "7:00 p.m." → "7:00 p. m.", the style the rest of the site uses
 *  (build_data's Weekly Open time, committee.js). */
export const esMeridiem = (s) => String(s).replace(/\b([ap])\.\s?m\./g, "$1. m.").replace(/(\d) (?=[ap]\. m\.)/g, "$1 ");
const fmtShortDay = (v, lang) => fmt(v, lang, { weekday: "short", month: "short", day: "numeric" });
const fmtShortDayYear = (v, lang) => fmt(v, lang, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
// Inside a sentence ("fecha límite: jue, 1 de oct"): Spanish keeps the weekday lower-case.
const fmtShortDayMid = (v, lang) => { const s = fmtShortDay(v, lang); return lang === "es" ? s.charAt(0).toLowerCase() + s.slice(1) : s; };
const fmtDay = (v, lang) => fmt(v, lang, { month: "short", day: "numeric", year: "numeric" });
const fmtTime = (v, lang) => fmt(v, lang, { hour: "numeric", minute: "2-digit", timeZoneName: "short" });

/** "Oct 17" – "Oct 23, 2026" style range. */
function fmtRange(a, b, lang) {
  const sameYear = toDate(a)?.getUTCFullYear() === toDate(b)?.getUTCFullYear();
  const first = fmt(a, lang, sameYear ? { month: "short", day: "numeric" } : { month: "short", day: "numeric", year: "numeric" });
  return `${first} – ${fmtDay(b, lang)}`;
}

/**
 * Localize a magazine issue label: "October 2026" ⇄ "Octubre 2026",
 * "Septiembre-Octubre 2026" ⇄ "September / October 2026" (same style as the
 * pipeline's rule-built labels). Labels that don't look like
 * "<month>[-/<month>] <year>" are returned unchanged.
 */
const MONTHS = {
  en: ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"],
  es: ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
};
export function issueLabel(label, lang) {
  const s = clean(label);
  const m = s.match(/^([A-Za-zÁÉÍÓÚáéíóúñÑ]+)(?:\s*[-–\/]\s*([A-Za-zÁÉÍÓÚáéíóúñÑ]+))?\s+(?:de\s+)?(\d{4})$/);
  if (!m) return s;
  const idx = (w) => {
    const x = w.toLowerCase().replace("setiembre", "septiembre");
    const i = MONTHS.en.indexOf(x);
    return i !== -1 ? i : MONTHS.es.indexOf(x);
  };
  const a = idx(m[1]);
  const b = m[2] ? idx(m[2]) : null;
  if (a === -1 || b === -1) return s;
  const name = (i) => { const n = (MONTHS[lang] || MONTHS.en)[i]; return n.charAt(0).toUpperCase() + n.slice(1); };
  return `${name(a)}${b !== null ? " / " + name(b) : ""} ${m[3]}`;
}

/**
 * Issue label of an article / editorial theme in the page language. The data
 * pipeline writes `i18n.issue_label` by rule ("October 2026" ⇄ "Octubre 2026",
 * "September / October 2026" ⇄ "Septiembre / Octubre 2026") — that wins; the
 * local rule above is the fallback for older data.
 */
export function issueLabelOf(item, lang) {
  const i = item?.i18n?.issue_label;
  if (i && i[lang]) return clean(i[lang]);
  return issueLabel(item?.extra?.issue_label || "", lang);
}

/**
 * The same label inside a sentence: Spanish months are lower-case there and
 * take "de" before the year ("la edición de octubre de 2026").
 */
export function issueInSentence(label, lang) {
  const s = clean(label);
  if (lang !== "es") return s;
  const m = s.match(/^(.*?)\s+(?:de\s+)?(\d{4})$/);
  if (!m) return s;
  const months = m[1].split(/\s*\/\s*/).map((w) => (MONTHS.es.includes(w.toLowerCase()) ? w.toLowerCase() : w));
  return `${months.join("/")} de ${m[2]}`;
}

function absUrl(url, site) {
  if (!url) return "";
  if (/^(https?:|mailto:|tel:)/.test(url)) return url;
  const b = String(site?.url || "").replace(/\/$/, "");
  return b + (url.startsWith("/") ? url : "/" + url);
}
const langPath = (url, lang) => (lang && lang !== "en" && url.startsWith("/") ? `/${lang}${url}` : url);
const clean = (s) => String(s ?? "").replace(/\s+/g, " ").trim();

/**
 * The moment an item became "new" for timeline purposes.
 * Items from whatsnew.json carry `wn_date`, computed by build_data.py with the
 * full rules (launch-day back catalog is not news, undated PDFs are not news,
 * future-dated magazine issues count from the day they appeared …) — that
 * always wins. The fallback below is only for items from other files:
 * magazine articles carry their ISSUE date (e.g. Oct 1) but appear on the web
 * weeks earlier, and events carry their event date — so a date in the future
 * falls back to when our robot first saw the item.
 */
export function whenOf(item, now = Date.now()) {
  if (!item) return null;
  if (item.wn_date) return item.wn_date;
  if (item.kind === "event") return item.first_seen || item.date || null;
  const d = ms(item.date);
  if (d && d <= now + DAY) return item.date;
  if (item.first_seen && ms(item.first_seen) <= now + DAY) return item.first_seen;
  return item.date || item.first_seen || null;
}

/** Which What's New group (filter chip) an item belongs to. */
export function groupOf(item) {
  const k = item?.kind;
  if (k === "announcement" || k === "event" || k === "article" || k === "episode" || k === "post" || k === "topic") return k;
  if (k === "video") return item.source === "drive" ? "drive" : "video";
  if (k === "pdf") return item.source === "drive" ? "drive" : "pdf";
  if (item?.source === "drive" || ["document", "slides", "photo", "video_file", "form"].includes(k)) return "drive";
  return "other";
}

/** Color family for an item's icon bubble: gv | lv | grape | vine | muted. */
function toneOf(item, group) {
  const host = item?.extra?.host || "";
  if (item?.source === "lavina" || item?.category === "lv" || host.includes("lavina") || item?.extra?.publication === "lv") {
    if (group === "article" || group === "pdf" || group === "topic") return "lv";
  }
  return (GROUPS[group] || GROUPS.other).tone;
}

/**
 * Teaser without the title repeated: Instagram titles are the caption's first
 * sentence and the summary is the whole caption, so the same words would show
 * twice. Returns the rest of the summary ("" when nothing is left).
 */
export function teaser(summary, title) {
  const s = clean(summary);
  const truncated = /(\.\.\.|…)$/.test(clean(title));
  const t = clean(title).replace(/\s*(\.\.\.|…)$/, "");
  if (!s || !t) return s;
  if (s.toLowerCase() === t.toLowerCase()) return "";
  if (t.length < 12 || !s.toLowerCase().startsWith(t.toLowerCase())) return s;
  const rest = s.slice(t.length).replace(/^[\s,;:]+/, "");
  if (!rest) return "";
  return truncated ? "…" + rest : rest;
}

/**
 * Image for a SMALL list thumbnail (What's New: 48–128 px wide boxes).
 *  - YouTube's 480×360 "hqdefault" (4:3 with black bars) → the 320×180 "mqdefault" (16:9).
 *  - A cached image "/assets/cache/<dir>/<name>.webp" → "<name>.sm.webp" next to it when the
 *    daily sync wrote one (a ~160 px wide copy); otherwise the 480 px original, unchanged.
 */
const smallThumbSeen = new Map();
export function listThumb(src) {
  const u = String(src || "");
  if (!u) return "";
  const yt = u.match(/^(https:\/\/i\d?\.ytimg\.com\/vi(?:_webp)?\/[\w-]+\/)(?:hq|sd|maxres)default(\.jpg|\.webp)$/);
  if (yt) return `${yt[1]}mqdefault${yt[2]}`;
  const m = u.match(/^\/assets\/cache\/([\w-]+\/[\w-]+)\.webp$/);
  if (!m) return u;
  if (!smallThumbSeen.has(m[1])) smallThumbSeen.set(m[1], fs.existsSync(path.join("src", "assets", "cache", `${m[1]}.sm.webp`)));
  return smallThumbSeen.get(m[1]) ? `/assets/cache/${m[1]}.sm.webp` : u;
}

/** Link target for an item (internal paths get the language prefix). */
export function hrefOf(item, lang) {
  const u = item?.url || "";
  if (!u) return "";
  return u.startsWith("/") ? langPath(u, lang) : u;
}

const isMediaItem = (item) => item?.kind === "episode" || item?.kind === "video";

function pickLang(item, field, lang) {
  if (!item) return "";
  const i = item.i18n && item.i18n[field];
  if (i && (i[lang] || i[lang] === "")) return i[lang] || i[item.lang] || item[field] || "";
  if (i && i.en) return i.en;
  return item[field] ?? "";
}

/** Shallow copy of an item plus the display helpers templates need. */
function prep(item, now = Date.now()) {
  const group = groupOf(item);
  const ex = item.extra || {};
  const isGroup = !!ex.is_group;
  return {
    ...item,
    _when: whenOf(item, now),
    _group: group,
    _tone: toneOf(item, group),
    _icon: isGroup ? "images" : group === "drive" ? DRIVE_ICONS[item.kind] || "folder-open" : (GROUPS[group] || GROUPS.other).icon,
    _ext: /^https?:/.test(item.url || ""),
    // YouTube dates that are only approximate (old uploads) show month + year, never a time.
    _approx: !!ex.date_approx,
    _hasTime: !!item.date && !isDateOnly(item.date) && !ex.date_approx && item.kind !== "event" && ms(item.date) <= now + DAY,
    // A PDF's `lang` is the language of its TITLE; the document itself may differ.
    _docLang: item.kind === "pdf" && ex.doc_lang ? ex.doc_lang : item.lang,
    // Languages the committee wrote it in by hand too (content/events title_es …): no "Original in …" pill there.
    _own: ownLangs(item),
    _isGroup: isGroup,
  };
}

function eventStart(ev) {
  return ev?.extra?.start || ev?.date || null;
}

/** The calendar day an event ends on (Central time): its `end` day, else its start day. */
function eventLastDay(ev) {
  const x = ev?.extra || {};
  const s = eventStart(ev);
  const last = x.end ? ymdChicago(isDateOnly(x.end) ? x.end : new Date(ms(x.end) - 1)) : ymdChicago(s);
  const first = ymdChicago(s);
  return last && last > first ? last : first;
}

/** An event over several days (an Area assembly, Fri–Sun) — not a timed one that only runs past midnight. */
function isMultiDay(ev) {
  const x = ev?.extra || {};
  const s = eventStart(ev);
  if (!s || eventLastDay(ev) === ymdChicago(s)) return false;
  return !!(x.all_day || isDateOnly(s)) || ms(x.end) - ms(s) > 18 * 3600e3;
}

/** Does an event's date need its year? When it ends in another year than `now`, or more than about
 *  six months ahead ("Fri, Sep 17 – Sun, Sep 19, 2027" next to this September's dates on What's New). */
const YEAR_AFTER_DAYS = 183;
function needsYear(lastYmd, now) {
  if (!lastYmd) return false;
  return lastYmd.slice(0, 4) !== ymdChicago(new Date(now)).slice(0, 4) || ms(lastYmd) - now > YEAR_AFTER_DAYS * DAY;
}

/** "Sat, Oct 17", "Wed, Oct 21 · 7:00 PM CDT" — or, over several days, "Fri, Mar 19 – Sun, Mar 21".
 *  With the year when it is another year or far ahead: "Fri, Sep 17 – Sun, Sep 19, 2027" /
 *  "Vie, 17 de sept – dom, 19 de sept de 2027". opts.time === false: the days only, never the time
 *  (the monthly digest lists the events that took place that way: cmEventDays). */
export function eventWhen(ev, lang, now = Date.now(), opts = {}) {
  const s = eventStart(ev);
  if (!s) return "";
  const allDay = opts.time === false || ev?.extra?.all_day || isDateOnly(s);
  const multi = isMultiDay(ev);
  const firstYmd = ymdChicago(s);
  const lastYmd = multi ? eventLastDay(ev) : firstYmd;
  const withYear = needsYear(lastYmd, now);
  // the first day carries the year only when the range crosses into another year (Dec 31 – Jan 2)
  const day1 = withYear && (!multi || firstYmd.slice(0, 4) !== lastYmd.slice(0, 4)) ? fmtShortDayYear(s, lang) : fmtShortDay(s, lang);
  const first = allDay ? day1 : `${day1} · ${fmtTime(s, lang)}`;
  if (!multi) return first;
  const last = withYear ? fmtShortDayYear(lastYmd, lang) : fmtShortDay(lastYmd, lang);
  return `${first} – ${lang === "es" ? last.charAt(0).toLowerCase() + last.slice(1) : last}`;
}

/** The event's place in the page language (content/events `location_es` → i18n.location), else as written. */
export function eventWhere(ev, lang) {
  const x = ev?.extra || {};
  return clean((ev?.i18n?.location && ev.i18n.location[lang]) || x.location || x.city || "");
}

/** The day(s) on an event's small date box: "17", or "19–21" over several days. */
function eventDayBox(ev, lang) {
  const s = eventStart(ev);
  if (!s) return "";
  const day = fmt(isDateOnly(s) ? s : ymdChicago(s), lang, { day: "numeric" });
  return isMultiDay(ev) ? `${day}–${fmt(eventLastDay(ev), lang, { day: "numeric" })}` : day;
}

/** The month line of that date box: "Sep", or "Apr–May" when the event ends in another month
 *  (the tiles on /events/, home and announcements do the same — homeEventInfo). */
function eventMonthBox(ev, lang) {
  const s = eventStart(ev);
  if (!s) return "";
  const mon = (v) => new Intl.DateTimeFormat(LOCALES[lang] || "en-US", { timeZone: TZ, month: "short" }).format(toDate(v)).replace(/\./g, "");
  const first = mon(ymdChicago(s));
  if (!isMultiDay(ev)) return first;
  const last = mon(eventLastDay(ev));
  return last !== first ? `${first}–${last}` : first;
}

/* ------------------------------------------------------------------ */
/*  QR code → inline SVG (synchronous; qrcode.create is the public API) */
/* ------------------------------------------------------------------ */
export function qrSvg(text, { label = "", cls = "", margin = 2, ecl = "M" } = {}) {
  if (!text) return "";
  let qr;
  try {
    qr = QRCode.create(String(text), { errorCorrectionLevel: ecl });
  } catch (e) {
    console.warn(`[community] QR failed for ${text}: ${e.message}`);
    return "";
  }
  const size = qr.modules.size;
  const full = size + margin * 2;
  // One path of horizontal runs keeps the SVG small (~3–6 KB) and crisp.
  let d = "";
  for (let r = 0; r < size; r++) {
    let c = 0;
    while (c < size) {
      if (qr.modules.get(r, c)) {
        let run = 1;
        while (c + run < size && qr.modules.get(r, c + run)) run++;
        d += `M${c + margin} ${r + margin}h${run}v1h-${run}z`;
        c += run;
      } else c++;
    }
  }
  const a11y = label ? `role="img" aria-label="${escapeXml(label)}"` : `aria-hidden="true"`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${full} ${full}" width="${full * 8}" height="${full * 8}" shape-rendering="crispEdges" class="${cls}" ${a11y}><rect width="${full}" height="${full}" fill="#ffffff"/><path fill="#000000" d="${d}"/></svg>`;
}

/** Same QR as a reusable <symbol> (referenced with <use href="#id">) — keeps
 *  pages that show one code many times (poster previews) small. */
export function qrSymbol(text, id, margin = 2) {
  const svg = qrSvg(text, { margin });
  const m = svg.match(/viewBox="([^"]+)"[^>]*>(.*)<\/svg>$/s);
  return m ? `<symbol id="${id}" viewBox="${m[1]}">${m[2]}</symbol>` : "";
}

export function escapeXml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&apos;")
    // strip characters that are illegal in XML 1.0
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g, "");
}

/* ------------------------------------------------------------------ */
/*  What's New                                                         */
/* ------------------------------------------------------------------ */
/** Items ready for the timeline / feed: prepared, "gone" removed, newest first. */
export function prepareWhatsNew(items, now = Date.now()) {
  return (items || [])
    .filter((i) => i && i.status !== "gone")
    .map((i) => prep(i, now))
    .sort((a, b) => ms(b._when) - ms(a._when));
}

/**
 * A podcast episode and its YouTube upload come out on the same day with the same title
 * ("Gated Communities [Season 11, Episode 12]") or the same season/episode numbers. On the
 * What's New page they are ONE entry: the episode, carrying the video as `_twin` (both badges,
 * "Listen · Watch" links, the video's thumbnail). The day, chip and hero counts are computed
 * from this merged list, so they match what is shown. (The RSS feed keeps both items.)
 */
export function mergeMediaTwins(prepared) {
  const list = prepared || [];
  const norm = (s) => clean(s).toLowerCase();
  const se = (i) => (i.extra && i.extra.season != null && i.extra.episode != null ? `${i.extra.season}|${i.extra.episode}` : "");
  const eps = list.filter((i) => i.kind === "episode");
  if (!eps.length) return list;
  const twinOf = new Map(); // video → episode
  const taken = new Set();
  for (const v of list) {
    if (v.kind !== "video" || v.source === "drive") continue;
    const day = ymdChicago(v._when);
    const t = norm(v.title), k = se(v);
    const ep = eps.find((e) => !taken.has(e) && ymdChicago(e._when) === day && ((t && norm(e.title) === t) || (k && se(e) === k)));
    if (ep) { twinOf.set(v, ep); taken.add(ep); }
  }
  if (!twinOf.size) return list;
  const merged = new Map([...twinOf].map(([v, e]) => [e, { ...e, _twin: v }]));
  return list.filter((i) => !twinOf.has(i)).map((i) => merged.get(i) || i);
}

/** Group prepared items by Central-time day, with per-kind counts and ranks. */
export function whatsNewDays(prepared, lang) {
  const days = new Map();
  for (const it of prepared || []) {
    const ymd = ymdChicago(it._when) || "undated";
    if (!days.has(ymd)) days.set(ymd, []);
    days.get(ymd).push(it);
  }
  return [...days.entries()].map(([ymd, items]) => {
    const entries = bundleIssues(items);
    // counts/ranks are per ENTRY (a bundle is one entry) — the page script
    // uses them for filtering and "show N more"; itemTotal is for display.
    const counts = {};
    const ranked = entries.map((it, i) => {
      const r = counts[it._group] || 0;
      counts[it._group] = r + 1;
      return { ...it, _rankAll: i, _rankKind: r };
    });
    const itemCounts = {};
    for (const it of items) itemCounts[it._group] = (itemCounts[it._group] || 0) + 1;
    return {
      ymd,
      label: ymd === "undated" ? "" : fmt(ymd, lang, { weekday: "long", month: "long", day: "numeric", year: "numeric" }),
      items: ranked,
      counts,
      itemCounts,
      total: entries.length,
      itemTotal: items.length,
    };
  });
}

/**
 * When a magazine issue lands, dozens of articles appear on the same day.
 * Fold 4+ articles of the same publication + issue into ONE timeline entry
 * ("27 new stories in the October 2026 issue") placed where the first was.
 */
const BUNDLE_MIN = 4;
function bundleIssues(items) {
  const keyOf = (it) => (it.kind === "article" && it.extra?.issue_key ? `${it.extra.publication || it.source}|${it.extra.issue_key}` : null);
  const groups = new Map();
  for (const it of items) { const k = keyOf(it); if (k) { if (!groups.has(k)) groups.set(k, []); groups.get(k).push(it); } }
  const out = [];
  const done = new Set();
  for (const it of items) {
    const k = keyOf(it);
    const g = k && groups.get(k);
    if (!g || g.length < BUNDLE_MIN) { out.push(it); continue; }
    if (done.has(k)) continue;
    done.add(k);
    out.push({
      ...g[0],
      id: `bundle:${k}`,
      _bundle: true,
      _items: g,
    });
  }
  return out;
}

function chipList(prepared) {
  const counts = {};
  for (const it of prepared || []) counts[it._group] = (counts[it._group] || 0) + 1;
  return CHIP_ORDER.filter((k) => counts[k]).map((k) => ({ key: k, count: counts[k], icon: GROUPS[k].icon }));
}

function countRecent(prepared, days, now = Date.now()) {
  return (prepared || []).filter((i) => { const t = ms(i._when); return t && now - t <= days * DAY && t <= now + DAY; }).length;
}

/* ------------------------------------------------------------------ */
/*  Published writers (spotlight) — Area 65 first, then the rest of Texas */
/* ------------------------------------------------------------------ */
// data/site/spotlight.json (docs/DATA_SCHEMA.md → "spotlight.json"): Grapevine / La Viña
// stories with a byline, each with extra.geo.scope (neta65 | texas | other | unknown) and
// extra.pub_date (the day the story counts as published). Templates get it as db.spotlight;
// while src/_data/db.js does not list "spotlight" yet, it is read here with the same link
// cleaning as db.js (safeUrl on every link).
const YMD = /^\d{4}-\d{2}-\d{2}$/;
const ANONYMOUS = /^\s*(anonymous|an[oó]nim[oa]|anon\.?)\s*$/i;
let spotlightFile; // undefined = not read yet in this build (reset on "eleventy.before")

function readSpotlightFile() {
  try {
    const data = JSON.parse(fs.readFileSync(path.join("data", "site", "spotlight.json"), "utf8"));
    if (!data || !Array.isArray(data.items)) return null;
    for (const it of data.items) {
      if (!it || typeof it !== "object") continue;
      it.url = safeUrl(it.url);
      if (typeof it.image === "string") it.image = safeUrl(it.image);
      if (it.extra && typeof it.extra.issue_url === "string") it.extra.issue_url = safeUrl(it.extra.issue_url);
    }
    return data;
  } catch {
    return null;
  }
}

export function spotlightOf(db) {
  const s = db?.spotlight;
  if (s && Array.isArray(s.items)) return s;
  if (spotlightFile === undefined) spotlightFile = readSpotlightFile();
  return spotlightFile || { items: [] };
}

/** "2026-09-23" minus 60 days → "2026-07-25" (calendar days, no time-zone drift). */
function minusDays(ymd, n) {
  const d = new Date(ymd + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

/** The home page's window (spotlight.home_days, 60 by default) — /published/ opens with it. */
export function spotlightHomeDays(spot) {
  const n = Number(spot?.home_days);
  return Number.isInteger(n) && n > 0 ? n : 60;
}

/**
 * Stories by writers from Area 65 (`neta65`) and from the rest of Texas (`texas`) published
 * in the last `days` days: extra.pub_date ≥ today (Central time) − days, the same rule as the
 * home page and /published/. Each list newest first (then by title).
 * opts.exclusiveStart: leave out the day `days` days back, so the window is exactly `days`
 * calendar days (today and the days − 1 before it). `since` is the first day included.
 * opts.since / opts.until ("YYYY-MM-DD", both included): an exact range of days instead — the
 * monthly digest passes the previous calendar month, so two editions never list the same story.
 */
export function writersPick(spot, days, now = Date.now(), opts = {}) {
  const today = ymdChicago(new Date(now));
  const since = YMD.test(opts.since || "") ? opts.since : minusDays(today, opts.exclusiveStart ? days - 1 : days);
  const until = YMD.test(opts.until || "") ? opts.until : "";
  const out = { days, since, until, today, allDays: spotlightHomeDays(spot), neta65: [], texas: [], total: 0 };
  const seen = new Set();
  for (const it of spot?.items || []) {
    if (!it || typeof it !== "object" || it.status === "gone" || it.kind !== "article" || !it.url) continue;
    const scope = it.extra?.geo?.scope;
    if (scope !== "neta65" && scope !== "texas") continue;
    const pd = it.extra?.pub_date;
    if (!YMD.test(pd || "") || pd < since || (until && pd > until)) continue;
    const key = it.id || it.url;
    if (seen.has(key)) continue;
    seen.add(key);
    out[scope].push(it);
  }
  const order = (a, b) => (a.extra.pub_date < b.extra.pub_date ? 1 : a.extra.pub_date > b.extra.pub_date ? -1 : 0) || clean(a.title).localeCompare(clean(b.title));
  out.neta65.sort(order);
  out.texas.sort(order);
  out.total = out.neta65.length + out.texas.length;
  return out;
}

/** "Victor R." — or "Anonymous" / "Anónimo" when the magazine printed no name. */
export function writerName(item, lang, t) {
  const a = clean(item?.extra?.author);
  return !a || ANONYMOUS.test(a) ? t("community.writers.anonymous", lang) : a;
}

/** "Grand Prairie, Texas" in the page language (written by rules in build_data, never machine-translated). */
export function writerPlace(item, lang) {
  const g = item?.extra?.geo || {};
  return clean(lang === "es" ? g.label_es : g.label_en) || clean(g.label_en) || clean(pickLang(item, "author_location", lang)) || clean(item?.extra?.author_location);
}

const pubName = (item) => (item?.extra?.publication === "lv" || item?.source === "lavina" || item?.category === "lv" ? "La Viña" : "Grapevine");

/* ------------------------------------------------------------------ */
/*  Monthly digest (/digest/ — its e-mail twin is scripts/notify/send_digest.py) */
/* ------------------------------------------------------------------ */
// One EDITION per calendar month P (America/Chicago), named after it — "September 2026 digest" /
// "Resumen de septiembre de 2026". It is on /digest/ from the first build on the 1st of the next month
// K through the end of K, and the e-mail goes out once, early in K. It recaps what happened or was
// published on the site in P, read from the FULL data files (never whatsnew.json, which keeps only its
// newest 150 entries), a day being its Central calendar day:
//   * the bulletin's posts (announcements.json) by the later of their date and their `publish` day, not
//     expired;
//   * the events that took place in P (events.json, the month an event starts in) and P's committee
//     meeting — its record, else the site.meeting rule (events.json drops a meeting once it is over) —
//     with their days only; events are never "news" on their own (no count, no e-mail);
//   * the committee's uploads (drive.json) by the later of their date and the day the site first had
//     them (first_seen): a file named after an earlier meeting ("2026-08-11 Report", uploaded in
//     September) is September's, and a photo taken on the 30th but uploaded on the 2nd is the next
//     month's — each upload is in exactly one edition, the one of the month it was added. A dated flyer
//     is an event, not an upload; photos are ONE entry per album for the month ("Photos: Booth — 5 new
//     photos", linking to /photos/#album);
//   * the magazine stories that came out online in P (articles.json extra.pub_date; a story without one
//     counts in the month its issue came out online — never by first_seen, so the site's launch never
//     puts the back catalog into one edition), grouped by issue with a few highlights (free to read
//     first, then members' stories, in the magazine's order);
//   * stories by writers from Area 65 and the rest of Texas published in P (spotlight.json);
//   * podcast episodes (a YouTube upload of the same episode folded into it, mergeMediaTwins), videos,
//     the magazines' Instagram posts (instagram.json: per account, how many and the 3 newest — the
//     site's /instagram/ page is their one home) and documents, by date.
// Plus ONE pointer: "Coming up in K" → /monthly/K/, the toolkit, the home of everything current (the
// committee meeting and its Zoom details, events not over yet, the weekly open meetings, deadlines, Book
// of the Month, the daily quote …). An issue's highlight stories are only here, in the month they came
// out; the toolkit shows the themes and counts. Nothing is in both.
// Two files keep only their newest entries, so a page read late in K can show fewer of P's items than the
// e-mail did: events.json (the newest 12 past one-off events) and instagram.json (the newest
// sources.instagram.keep_per_account posts of each account).
// send_digest.py applies the same rules: keep the two in step (tests/test_digest_parity.py compares what
// each one picks; docs/OPERATIONS.md → monthly-digest.yml).

const pad2 = (n) => String(n).padStart(2, "0");
/** "2026-09" → "2026-09-30" */
const monthLastDay = (key) => { const [y, m] = key.split("-").map(Number); return `${key}-${pad2(new Date(Date.UTC(y, m, 0)).getUTCDate())}`; };
/** "September" / "septiembre" (the month alone; Spanish months are lower-case inside a sentence) */
export function monthWord(key, lang) {
  const [y, m] = String(key).split("-").map(Number);
  if (!y || !m) return "";
  return new Intl.DateTimeFormat(LOCALES[lang] || "en-US", { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(y, m - 1, 15)));
}

/**
 * The edition shown at `now`: the Central-time month BEFORE now's (October 1–31 → the September digest),
 * or the one covering an explicit "YYYY-MM" (`month`): the month it covers (key, first, last) and the
 * month it comes out in (out, outFirst: its toolkit pointer, the page's "since" pointer).
 */
export function digestEdition(now = nowDate(), month = "") {
  const key = /^\d{4}-(0[1-9]|1[0-2])$/.test(month || "") ? month : addMonths(ymdChicago(new Date(now)).slice(0, 7), -1);
  const out = addMonths(key, 1);
  return { key, first: `${key}-01`, last: monthLastDay(key), out, outFirst: `${out}-01` };
}

// What the edition counts as news (What's New groups; the drive group holds the albums too, "post" is
// Instagram).
const MONTH_NEWS = ["announcement", "article", "episode", "video", "post", "pdf", "drive"];
// The intro's list, in this order: "89 magazine stories, 8 podcast episodes, 2 videos, 38 Instagram posts …
// 1 photo album and 1 bulletin post".
export const COUNT_ORDER = ["article", "episode", "video", "post", "pdf", "drive", "album", "announcement"];
// The full source lists read by their own date (the magazine stories by extra.pub_date, below).
const MONTH_SOURCES = ["announcements", "episodes", "videos", "instagram", "pdfs", "drive"];
// How many of an Instagram account's posts of the month the edition shows (the rest: /instagram/).
const IG_NEWEST = 3;

/** The later of two news dates by their Central calendar day: `b` only when its day is after `a`'s (or
 *  there is no `a`), so on the same day `a` keeps its own time. */
function laterOf(a, b) {
  const da = a ? ymdChicago(a) : "";
  const dbb = b ? ymdChicago(b) : "";
  return dbb && (!da || dbb > da) ? b : a || null;
}

/** A bulletin post's news date: the later of its date (else when it was first seen) and its `publish`
 *  day (a post scheduled with `publish:` counts from the day it appeared on the site). */
function postWhen(it) {
  const pub = String(it.extra?.publish || "").slice(0, 10);
  return laterOf(it.date || it.first_seen || null, YMD.test(pub) ? pub : null);
}

/** A committee upload's news date (drive.json): the later of its date (the date its name starts with,
 *  else when the photo was taken or the file created — drive.py) and when the site first had it, so each
 *  upload is in the edition of the month it was added. */
const uploadWhen = (it) => laterOf(it.date || null, it.first_seen || null);

/**
 * The day a magazine story counts in, for a list of stories: its extra.pub_date (the day it came out
 * online — build_data), else — a story whose pub_date could not be worked out — the earliest pub_date of
 * its issue's stories (the day the issue came out online). Never first_seen: the stories the site found
 * at its launch (the back catalog) would all land in one edition. "" when neither is known.
 */
function storyDayOf(stories) {
  const issueOf = (a) => `${a.extra.publication || a.category}|${a.extra.issue_key}`;
  const first = new Map();
  for (const a of stories) {
    const pd = a.extra.pub_date;
    if (YMD.test(pd || "") && (!first.has(issueOf(a)) || pd < first.get(issueOf(a)))) first.set(issueOf(a), pd);
  }
  return (a) => (YMD.test(a.extra.pub_date || "") ? a.extra.pub_date : first.get(issueOf(a)) || "");
}
/** The magazine stories the digest reads: articles.json stories on the site, with a link and an issue. */
const digestStories = (db) => (db?.articles?.items || [])
  .filter((a) => a && a.kind === "article" && a.status !== "gone" && a.url && a.extra?.issue_key);

/**
 * P's news by group ({ key: [items] }), newest first — the bulletin's pinned posts first, a podcast's
 * YouTube twin folded into it, the committee's photos one entry per album:
 *   { id: "album:<key>", kind: "album", _album: true, _count: photos, _when: the newest photo's date,
 *     url: "/photos/#<album>", title: the album's folder (or ""), i18n: { album } }
 * `_when` is the date an item counts on (a scheduled post's `publish` day, an upload's first_seen …); the
 * item keeps its own `date` (a committee file's row shows the date in its name).
 */
export function monthNews(db, ed, now = Date.now()) {
  const today = ymdChicago(new Date(now));
  const inMonth = (v) => { const d = ymdChicago(v); return !!d && d >= ed.first && d <= ed.last; };
  const found = new Map();
  for (const name of MONTH_SOURCES) {
    for (const raw of db?.[name]?.items || []) {
      if (!raw || !raw.id || raw.status === "gone" || found.has(raw.id)) continue;
      const it = prep(raw, now);
      if (!MONTH_NEWS.includes(it._group)) continue;
      if (name === "drive" && (raw.kind === "announcement" || raw.extra?.event_date)) continue;   // a bulletin doc / a dated flyer (an event)
      const when = raw.kind === "announcement" ? postWhen(raw) : name === "drive" ? uploadWhen(raw) : raw.date;
      if (!(isDateOnly(when) || (typeof when === "string" && ms(when)))) continue;              // undated: never news
      if (ms(when) > now + DAY || !inMonth(when)) continue;
      // a bulletin post is over after its `expires` day (Central time) — the rule of /bulletin/, the
      // home page, build_data and the e-mail (send_digest.py; tests/test_digest_parity.py compares them)
      if (it.kind === "announcement" && it.extra?.expires && String(it.extra.expires).slice(0, 10) < today) continue;
      found.set(raw.id, { ...it, _when: when });
    }
  }
  // the magazine stories that came out online in P (storyDayOf: extra.pub_date, else their issue's)
  const stories = digestStories(db);
  const dayOf = storyDayOf(stories);
  for (const a of stories) {
    if (!a.id || found.has(a.id)) continue;
    const pd = dayOf(a);
    if (!pd || pd < ed.first || pd > ed.last) continue;
    found.set(a.id, { ...prep(a, now), _when: pd });
  }
  // the committee's photos: ONE entry per album for the month, dated by its newest photo and linking to
  // the album on /photos/ (committee.js photoAlbumKey / photoAlbumSlugs: the same ids as that page)
  const albums = new Map();
  for (const it of found.values()) {
    if (it.source !== "drive" || !isPhotoItem(it)) continue;
    const k = photoAlbumKey(it);
    if (!albums.has(k)) albums.set(k, []);
    albums.get(k).push(it);
  }
  if (albums.size) {
    const slugs = photoAlbumSlugs(db?.drive?.items || []);
    for (const [k, members] of albums) {
      for (const p of members) found.delete(p.id);
      const newest = members.reduce((a, b) => (ms(b._when) > ms(a._when) ? b : a));
      const slug = slugs.get(k);
      found.set(`album:${k}`, {
        id: `album:${k}`, kind: "album", source: "drive", category: "photos", _group: "drive", _album: true,
        _count: members.length, _when: newest._when, _tone: "vine", _icon: "images", _ext: false,
        url: slug ? `/photos/#${slug}` : "/photos/", title: k.startsWith("f:") ? k.slice(2) : "",
        i18n: { album: members[0].i18n?.album || null }, machine: members[0].machine || [], extra: {},
      });
    }
  }
  const list = mergeMediaTwins([...found.values()].sort((a, b) => ms(b._when) - ms(a._when) || String(a.id).localeCompare(String(b.id))));
  const out = {};
  for (const k of MONTH_NEWS) out[k] = list.filter((i) => i._group === k);
  // pinned bulletin posts first
  out.announcement.sort((a, b) => (b.extra?.pinned === true) - (a.extra?.pinned === true));
  return out;
}

const EVERY_ISSUE_RE = /in every issue|en cada (?:edici[oó]n|n[uú]mero)/i;
const isDepartment = (a) => a?.extra?.department === true || EVERY_ISSUE_RE.test(String(a?.extra?.section || ""));

/**
 * The magazine issues whose stories came out online in P (extra.pub_date — so the September digest
 * features the October Grapevine, online since September 23; storyDayOf), Grapevine first, the newest
 * issue key first (issuesByLang.es puts La Viña first). Each: the stories of P (`count`, `free`), all the
 * issue's stories on the site (`total`), `current` (the newest issue of that magazine on /read/ — read.js
 * groupIssues, the page's own rule), label, theme (monthly.js issueTheme — the toolkit's name for it),
 * the official issue page and cover, the /read/ link, and `n` highlights: the stories of P minus `skip`
 * (the writers' stories, listed in their own section), free to read first, then members' stories (not
 * "In Every Issue"), then the magazine's order.
 */
export function monthIssues(db, ed, n = 3, skip = new Set()) {
  const pubOf = (a) => a.extra.publication || a.category;
  const stories = digestStories(db);
  const dayOf = storyDayOf(stories);
  const groups = new Map();
  for (const a of stories) {
    const pub = pubOf(a);
    const pd = dayOf(a);
    if ((pub !== "gv" && pub !== "lv") || !pd || pd < ed.first || pd > ed.last) continue;
    const k = `${pub}|${a.extra.issue_key}`;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(a);
  }
  const out = [...groups.entries()].map(([k, list]) => {
    const [pub, key] = k.split("|");
    const meta = (db?.articles?.issues || []).find((i) => i && i.publication === pub && i.key === key) || null;
    const first = list[0];
    const label = (l) => clean(meta?.i18n?.label?.[l] || first.i18n?.issue_label?.[l]) || issueLabel(first.extra.issue_label || meta?.label || key, l);
    const newest = groupIssues(db?.articles, pub)[0];
    const current = !!newest && newest.key === key;
    const ranked = list.filter((a) => !skip.has(a.id) && !skip.has(a.url)).map((a, i) => ({ a, i }))
      .sort((x, y) => (x.a.extra.free === true ? 0 : 1) - (y.a.extra.free === true ? 0 : 1) || isDepartment(x.a) - isDepartment(y.a) || x.i - y.i)
      .map((x) => x.a);
    return {
      pub, key, isLv: pub === "lv", name: pub === "lv" ? "La Viña" : "Grapevine",
      label: { en: label("en"), es: label("es") },
      theme: { en: issueTheme(db, pub, key, "en"), es: issueTheme(db, pub, key, "es") },
      url: meta?.url || first.extra.issue_url || "",
      cover: meta?.cover || "",
      count: list.length,
      total: stories.filter((a) => pubOf(a) === pub && a.extra.issue_key === key).length,
      free: list.filter((a) => a.extra.free === true).length,
      current,
      readHref: current ? `/read/#${pub}-current` : "/read/",
      highlights: ranked.slice(0, n),
    };
  });
  return out.sort((a, b) => (a.pub === b.pub ? 0 : a.pub === "gv" ? -1 : 1) || (a.key < b.key ? 1 : a.key > b.key ? -1 : 0));
}

/**
 * P's Instagram posts (monthNews' "post" group, newest first) per account of the magazines — Grapevine,
 * La Viña, then any other in the order of their key: { key, name, username, url (the account on
 * Instagram), count, newest: the IG_NEWEST newest posts }. The page shows each account's count and its
 * newest posts, the texts only the counts; all of them are on the site's /instagram/ page (one link).
 * `profiles` = instagram.json profiles (the handle and the account's address).
 */
export function monthInstagram(posts, profiles = {}) {
  const by = new Map();
  for (const p of posts || []) {
    const key = String(p.extra?.account || p.category || p.extra?.username || "");
    if (!by.has(key)) by.set(key, []);
    by.get(key).push(p);
  }
  const rank = (k) => (k === "gv" ? 0 : k === "lv" ? 1 : 2);
  return [...by.entries()]
    .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
    .map(([key, list]) => {
      const prof = (profiles && profiles[key]) || {};
      const username = String(prof.username || list[0].extra?.username || "").replace(/^@/, "");
      return {
        key, name: key === "lv" ? "La Viña" : key === "gv" ? "Grapevine" : clean(prof.name) || username,
        username, url: prof.url || (username ? `https://www.instagram.com/${username}/` : ""),
        count: list.length, newest: list.slice(0, IG_NEWEST),
      };
    });
}

/**
 * The events that took place in P — every category but the committee's, in the month an event starts
 * in, once it has started — plus P's committee meeting: its events.json record, else the site.meeting
 * rule (monthly.js meetingByRule: skip_dates honoured) when the settings have a meeting, once it has
 * started: { id: "ev:committee:<day>", category: "committee", url: "/meetings/", _committee: true }.
 * Soonest first. (A meeting cancelled without a skip date still reads as held — the rule cannot know.)
 */
export function monthEventsHeld(db, ed, site = {}, now = Date.now()) {
  const inMonth = (v) => { const d = ymdChicago(v); return !!d && d >= ed.first && d <= ed.last; };
  const all = (db?.events?.items || []).filter((e) => e && e.status !== "gone");
  const evs = all.filter((e) => e.category !== "committee" && eventStart(e) && inMonth(eventStart(e)) && ms(eventStart(e)) <= now)
    .map((e) => prep(e, now));
  const rule = site?.meeting && typeof site.meeting === "object" && Object.keys(site.meeting).length ? site.meeting : null;
  const rec = all.find((e) => String(e.id || "").startsWith(`ev:committee:${ed.key}-`));
  const cm = rec && eventStart(rec) ? { ymd: ymdChicago(eventStart(rec)), start: eventStart(rec), end: rec.extra?.end || null }
    : rule ? meetingByRule(ed.key, rule) : null;
  if (cm && cm.start && ms(cm.start) <= now) {
    const base = rec || { kind: "event", source: "committee", title: "", lang: "en", i18n: {}, machine: [] };
    evs.push({
      ...prep({ ...base, id: `ev:committee:${cm.ymd}`, category: "committee", url: "/meetings/", date: cm.start,
        extra: { start: cm.start, end: cm.end, all_day: false, location: (rule && rule.platform) || "Zoom" } }, now),
      _committee: true,
    });
  }
  return evs.sort((a, b) => ms(eventStart(a)) - ms(eventStart(b)) || String(a.id).localeCompare(String(b.id)));
}

/**
 * Everything the monthly edition shows (the /digest/ page, its WhatsApp / e-mail texts).
 * opts: site, now, month ("YYYY-MM": the month covered), highlights, perSection.
 */
export function buildMonthlyDigest(db, opts = {}) {
  const now = opts.now instanceof Date ? opts.now.getTime() : Number(opts.now) || nowDate().getTime();
  const site = opts.site || {};
  const cfg = site.digest || {};
  const intOr = (v, d) => (Number.isInteger(Number(v)) && Number(v) > 0 ? Number(v) : d);
  const highlights = intOr(opts.highlights ?? cfg.highlights, 3);
  const perSection = intOr(opts.perSection ?? cfg.per_section, 5);
  const ed = digestEdition(now, opts.month);

  const news = monthNews(db, ed, now);
  const counts = {
    article: news.article.length, episode: news.episode.length, video: news.video.length, post: news.post.length,
    pdf: news.pdf.length, drive: news.drive.filter((i) => !i._album).length, album: news.drive.filter((i) => i._album).length,
    announcement: news.announcement.length,
  };
  const instagram = monthInstagram(news.post, db?.instagram?.profiles);
  const total = COUNT_ORDER.reduce((n, k) => n + counts[k], 0);
  const writers = writersPick(spotlightOf(db), 0, now, { since: ed.first, until: ed.last });
  // the writers' stories have their own section: never again among an issue's highlights
  const skip = new Set([...writers.neta65, ...writers.texas].flatMap((w) => [w.id, w.url]).filter(Boolean));
  const issues = monthIssues(db, ed, highlights, skip);
  // What's New entries since the edition came out (the page's "since" pointer, never in the texts)
  const since = (db?.whatsnew?.items || []).filter((i) => i && i.status !== "gone" && i.wn_date && ymdChicago(i.wn_date) >= ed.outFirst && ms(i.wn_date) <= now + DAY).length;

  return {
    edition: { ...ed, label: { en: monthLabel(ed.key, "en"), es: monthLabel(ed.key, "es") } },
    // once K is over (midnight Central after its last day), a copy of this page read then says it is
    // last month's edition (digest.njk, src/assets/js/community.js digestPage `stale`)
    staleAfter: new Date(chicagoDayEndMs(monthLastDay(ed.out))).toISOString(),
    today: ymdChicago(new Date(now)),
    highlights,
    perSection,
    news,
    counts,
    total,
    issues,
    // the page language's magazine first: La Viña on /es/ (stable: the newest issue key first within each)
    issuesByLang: { en: issues, es: [...issues.filter((i) => i.isLv), ...issues.filter((i) => !i.isLv)] },
    // P's Instagram posts per account (monthInstagram), the page language's magazine first
    instagram,
    instagramByLang: { en: instagram, es: [...instagram.filter((a) => a.key === "lv"), ...instagram.filter((a) => a.key !== "lv")] },
    writers,
    events: monthEventsHeld(db, ed, site, now),
    since,
    // the ONE pointer to what is current: the toolkit of the month the edition comes out in
    toolkit: {
      path: `/monthly/${ed.out}/`,
      label: { en: monthLabel(ed.out, "en"), es: monthLabel(ed.out, "es") },
      month: { en: monthWord(ed.out, "en"), es: monthWord(ed.out, "es") },
    },
  };
}

/** "89 magazine stories, 8 podcast episodes, 38 Instagram posts, 1 photo album and 1 bulletin post" (zero counts
 *  left out), in `lang`. */
export function digestCountList(md, lang, t) {
  const parts = COUNT_ORDER
    .filter((k) => md.counts[k] > 0)
    .map((k) => t(`community.digest.n_${k}${md.counts[k] === 1 ? "_one" : ""}`, lang, { n: md.counts[k] }));
  if (parts.length < 2) return parts[0] || "";
  return `${parts.slice(0, -1).join(", ")} ${t("community.digest.and", lang)} ${parts[parts.length - 1]}`;
}

/** The edition's one-sentence intro ("In September: 89 magazine stories, … and 1 bulletin post."). */
export function digestIntro(md, lang, t) {
  const vars = { prev: monthWord(md.edition.key, lang) };
  const list = digestCountList(md, lang, t);
  return list ? t("community.digest.intro", lang, { ...vars, list }) : t("community.digest.intro_quiet", lang, vars);
}

/** An Instagram post's one line in the digest: its title in `lang` (the caption's first line — the sync
 *  writes it), else — a post without a caption ("AA Grapevine — Instagram": media.js IG_GENERIC_TITLE) —
 *  "An Instagram post from Grapevine" (`name`: the account). */
const IG_GENERIC_TITLE = /^\s*(?:aa\s+grapevine|la\s+vi[ñn]a)\s*[—–-]\s*instagram\s*$/i;
export function postLine(it, lang, t, name) {
  const s = clean(pickLang(it, "title", lang));
  return s && !IG_GENERIC_TITLE.test(s) && !IG_GENERIC_TITLE.test(String(it?.title || "")) ? s : t("community.wn.ig_post", lang, { name });
}

/** An album row's title: "Photos: Booth" / "Fotos: Booth" (the album's name in `lang` when there is one),
 *  else "New photos" (a panel's own photos). */
export function albumTitle(it, lang, t) {
  const name = clean(it?.i18n?.album?.[lang] || it?.title);
  return name ? t("community.digest.album", lang, { name }) : t("community.digest.album_plain", lang);
}

/**
 * Plain-text monthly edition for WhatsApp ("whatsapp") or e-mail ("email").
 * `langs` = ["en"], ["es"] or ["en","es"] (bilingual: both languages in one message).
 * `media` = the shared podcast/video title helpers of eleventy/filters/media.js
 * ({ title, cleanTitle, videoKind } — see mediaHelpers below), so episodes and
 * videos read as on Home, Listen and Watch (no "[Season 11, Episode 12]" tail).
 * The order of the page: the intro · the bulletin · the events of the month · the committee's uploads ·
 * the magazines · the writers · podcasts, videos, Instagram (each account's count and one link),
 * documents · (a quiet month) · the one pointer to this month's toolkit · the footer.
 */
export function monthlyDigestText(md, langs, style, site, t, media = {}) {
  const L = Array.isArray(langs) ? langs : [langs];
  const wa = style === "whatsapp";
  const main = L[0];
  const uniq = (arr) => arr.filter((v, i, a) => v && a.indexOf(v) === i);
  // vars: an object, or a function of the language (month names differ by language)
  const both = (key, vars) => uniq(L.map((l) => t(key, l, typeof vars === "function" ? vars(l) : vars))).join(" / ");
  const head = (s, emoji) => (wa ? `${emoji} *${s}*` : `${s.toUpperCase()}\n${"-".repeat(Math.min(s.length, 60))}`);
  const bullet = wa ? "•" : "-";
  const per = wa ? 3 : md.perSection;
  const url = (p) => absUrl(langPath(p, main), site);
  const ed = md.edition;
  const prevW = (l) => ({ prev: monthWord(ed.key, l) });
  // the events' days are written as seen from the month covered (a date of another year says it)
  const asOf = Date.parse(`${ed.last}T12:00:00Z`);
  const titleOf = (item, l) => {
    const raw = clean(pickLang(item, "title", l));
    if (!isMediaItem(item) || !media.title) return raw;
    // A Weekly Open recording's display title drops the show name on the web pages, which show
    // the show next to it; a text message has no such label, so only the numbering tail goes.
    if (media.cleanTitle && media.videoKind && media.videoKind(item) === "weekly") return clean(media.cleanTitle(raw)) || raw;
    return clean(media.title(item, l)) || raw;
  };
  const titleLines = (item) => { const ts = uniq(L.map((l) => titleOf(item, l))); return ts.length ? ts : [clean(item.title)]; };
  const more = (n, page) => `${wa ? "➕" : "+"} ${both("community.digest.text_more", { n })} ${url(page)}`;
  const out = [];

  const title = `NETA 65 Grapevine / La Viña — ${both("community.digest.edition", (l) => ({ month: ed.label[l] }))}`;
  out.push(wa ? `*${title}*` : title);
  const sub = both("community.digest.edition_sub", prevW);
  out.push(wa ? `_${sub}_` : sub);
  out.push("");
  for (const l of L) out.push(digestIntro(md, l, t));
  out.push("");

  // The bulletin
  const ann = md.news.announcement;
  if (ann.length) {
    out.push(head(`${both("community.group.announcement")} (${ann.length})`, "📣"));
    for (const a of ann.slice(0, per)) {
      const [first, ...others] = titleLines(a);
      out.push(`${bullet} ${first}`);
      for (const r of others) out.push(`  ${r}`);
      out.push(`  ${absUrl(hrefOf(a, main), site)}`);
    }
    if (ann.length > per) out.push(more(ann.length - per, "/bulletin/"));
    out.push("");
  }

  // The events that took place (days only; the committee meeting under its own name)
  if (md.events.length) {
    out.push(head(both("community.digest.events_title", prevW), "📅"));
    for (const ev of md.events) {
      const [first, ...rest] = ev._committee ? [both("community.digest.committee_meeting")] : titleLines(ev);
      const where = eventWhere(ev, main);
      out.push(`${bullet} ${eventWhen(ev, main, asOf, { time: false })} — ${first}${where ? ` (${where})` : ""}`);
      for (const r of rest) out.push(`  ${r}`);
      if (ev.url) out.push(`  ${ev._committee ? url("/meetings/") : absUrl(hrefOf(ev, main), site)}`);
    }
    out.push("");
  }

  // The committee's uploads: files, and the photos one line per album
  const drive = md.news.drive;
  if (drive.length) {
    out.push(head(`${both("community.group.drive")} (${drive.length})`, "📁"));
    for (const item of drive.slice(0, per)) {
      if (item._album) {
        const names = uniq(L.map((l) => albumTitle(item, l, t)));
        out.push(`${bullet} ${names[0]} — ${t(item._count === 1 ? "community.digest.n_photos_one" : "community.digest.n_photos", main, { n: item._count })}`);
        for (const r of names.slice(1)) out.push(`  ${r}`);
      } else {
        // a file with its own date (the one in its name: two "Area Chair Meeting Report" files of different
        // meetings can be added the same month)
        const [first, ...others] = titleLines(item);
        out.push(`${bullet} ${first}${item.date ? ` (${fmtDay(item.date, main)})` : ""}`);
        for (const r of others) out.push(`  ${r}`);
      }
      out.push(`  ${absUrl(hrefOf(item, main), site)}`);
    }
    if (drive.length > per) out.push(more(drive.length - per, GROUPS.drive.page));
    out.push("");
  }

  // New in the magazines: each issue whose stories came out in P (La Viña first in Spanish)
  const issues = md.issuesByLang[main] || md.issues;
  if (issues.length) {
    out.push(head(both("community.digest.issues_title"), "📖"));
    for (const iss of issues) {
      const theme = uniq(L.map((l) => iss.theme[l])).map((x) => `“${x}”`).join(" / ");
      const n = both(iss.count === 1 ? "community.digest.n_stories_one" : "community.digest.n_stories", { n: iss.count });
      out.push(`${bullet} ${iss.name} — ${iss.label[main]}${theme ? `: ${theme}` : ""} (${n})`);
      for (const a of iss.highlights.slice(0, per)) {
        const [first, ...others] = titleLines(a);
        out.push(`  “${first}”${a.extra?.free === true ? ` — ${both("community.digest.free")}` : ""}`);
        for (const r of others) out.push(`  “${r}”`);
        out.push(`  ${a.url}`);
      }
      out.push(`  ${both("community.digest.issue_more", { n: iss.total })}: ${url(iss.readHref)}`);
    }
    out.push("");
  }

  // Writers from Area 65 (first) and the rest of Texas, published in P
  const W = md.writers;
  if (W && W.total) {
    out.push(head(`${both("community.writers.digest_title")} (${W.total})`, "⭐"));
    const pubUrl = url("/published/");
    for (const key of ["neta65", "texas"]) {
      const list = W[key] || [];
      if (!list.length) continue;
      out.push(`${both(`community.writers.group_${key}`)}:`);
      for (const item of list.slice(0, per)) {
        const [first, ...others] = titleLines(item);
        const place = writerPlace(item, main);
        out.push(`${bullet} "${first}" — ${writerName(item, main, t)}${place ? `, ${place}` : ""} (${pubName(item)}, ${issueInSentence(issueLabelOf(item, main), main)})`);
        for (const r of others) out.push(`  "${r}"`);
        out.push(`  ${absUrl(item.url, site)}`);
      }
      if (list.length > per) out.push(`${wa ? "➕" : "+"} ${both("community.digest.text_more", { n: list.length - per })} ${pubUrl}`);
    }
    out.push("");
  }

  // Listen & watch, Instagram, the new documents
  for (const [key, emoji] of [["episode", "🎧"], ["video", "🎬"], ["post", "📸"], ["pdf", "📄"]]) {
    const items = md.news[key];
    if (!items.length) continue;
    out.push(head(`${both(`community.group.${key}`)} (${items.length})`, emoji));
    if (key === "post") {
      // Instagram: how many posts each account shared (the page language's magazine first) and ONE link,
      // the site's Instagram page — never the posts one by one in a message
      for (const acc of md.instagramByLang[main] || md.instagram) {
        out.push(`${bullet} ${acc.name}${acc.username ? ` @${acc.username}` : ""}: ${both(acc.count === 1 ? "community.digest.ig_n_one" : "community.digest.ig_n", { n: acc.count })}`);
      }
      out.push(`  ${url("/instagram/")}`, "");
      continue;
    }
    for (const item of items.slice(0, per)) {
      const [first, ...others] = titleLines(item);
      out.push(`${bullet} ${first}`);
      for (const r of others) out.push(`  ${r}`);
      out.push(`  ${absUrl(hrefOf(item, main), site)}`);
    }
    if (items.length > per) out.push(more(items.length - per, GROUPS[key].page));
    out.push("");
  }
  if (!md.total && !(W && W.total)) {
    out.push(both("community.digest.text_quiet", prevW));
    out.push("");
  }

  // The one pointer to what is current: this month's toolkit
  out.push(head(both("community.digest.coming_month", (l) => ({ month: md.toolkit.month[l] })), "🗓️"));
  const kit = uniq(L.map((l) => t("community.digest.toolkit_text", l)));
  if (kit.length === 1) out.push(`${kit[0]} ${url(md.toolkit.path)}`);
  else out.push(...kit, url(md.toolkit.path));
  out.push("");

  out.push(`${wa ? "🌐 " : ""}${both("community.digest.text_footer")}`);
  for (const l of L) out.push(absUrl(langPath("/whats-new/", l), site));
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

function uniqByTitle(items, lang) {
  const seen = new Set();
  return (items || []).filter((it) => {
    const k = clean(pickLang(it, "title", lang)).toLowerCase();
    if (!k || seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

/* ------------------------------------------------------------------ */
/*  Status dashboard                                                   */
/* ------------------------------------------------------------------ */
// Sources whose count is legitimately 0 until the committee adds something
// get a friendly "how to fill this" hint instead of a bare 0.
const EMPTY_HINTS = { drive: "drive_empty", announcements: "ann_empty", manual_events: "events_empty", events_external: "ext_empty" };

const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));

export function statusView(status, now = Date.now()) {
  const sources = (status?.sources || []).map((s) => {
    const updated = s.updated || null;
    const age = updated ? now - ms(updated) : null;
    // ok: true = last run fine · false = last run failed (older data kept) · null/absent = never ran
    let state = "never";
    if (s.ok === false) state = "failed";
    else if (updated) state = "ok";
    const count = Number(s.count) || 0;
    const panel = Array.isArray(s.stats?.panels) && s.stats.panels.length ? String(s.stats.panels[0]) : "";
    return {
      ...s,
      state,
      count,
      stale: state === "ok" && age !== null && age > 3 * DAY,
      ageDays: age === null ? null : Math.floor(age / DAY),
      attempted: s.attempted || updated,
      hint: state === "ok" && count === 0 && EMPTY_HINTS[s.source] ? EMPTY_HINTS[s.source] : "",
      panel,
    };
  });
  const c = status?.crawl || {};
  const tr = status?.translations || {};
  // Optional outside calendars (config/site.yml sources.ics_feeds) — build_data's status.json `feeds`.
  // Kept apart from the content sources: a feed blocked by a site's bot protection is an extra that
  // does not work, not a source that "failed" (it is not in the counts above).
  const FEED_STATES = new Set(["ok", "blocked", "error", "never"]);
  const feeds = (Array.isArray(status?.feeds) ? status.feeds : []).filter((f) => f && f.url).map((f) => {
    let host = "";
    try { host = new URL(f.url).hostname.replace(/^www\./, ""); } catch { /* not a URL */ }
    const state = FEED_STATES.has(f.state) ? f.state : "never";
    return {
      ...f,
      state,
      host,
      events: Math.max(0, Number(f.events_count) || 0),
      dups: Math.max(0, Number(f.duplicates) || 0),
      http: f.http_status ? String(f.http_status) : "",
    };
  });
  const totalItems = sources.reduce((a, s) => a + s.count, 0);
  const found7d = sources.reduce((a, s) => a + (Number(s.new_7d) || 0), 0);
  return {
    generated: status?.generated || null,
    sources,
    feeds,
    okCount: sources.filter((s) => s.state === "ok").length,
    failedCount: sources.filter((s) => s.state === "failed").length,
    totalItems,
    found7d,
    // Everything tracked was first found in the last 7 days (the site's first week): the page
    // says so, so the big number is not read as "1,240 new things this week". From the second
    // week on this is false by itself — no date to update by hand.
    allFound7d: totalItems > 0 && found7d >= totalItems,
    // The Status page's library panel: document facts only (curated entries, build_data.py).
    crawl: {
      pdfs: num(c.pdfs) || 0,
      thumbs: num(c.pdfs_with_thumbs) || 0,
      updated: c.updated || null,
      hasData: (num(c.pdfs) || 0) > 0,
    },
    translations: {
      cached: num(tr.cached) || 0,
      pending: num(tr.pending) || 0,
      rejected: num(tr.rejected_by_guard) || 0,
      glossary: num(tr.glossary_entries) || 0,
    },
  };
}

/**
 * 0–100 → "1.6%" / "42%" / "99.9%" (es: "1,6 %"). Whole numbers from 10 up, but a value
 * short of 100 never rounds up to "100%" (it keeps one decimal, at most 99.9: 99.88 and
 * 99.97 both read "99.9%"), and a tiny non-zero value never shows as "0%".
 */
export function cmPct(n, lang) {
  let v = Number(n) || 0;
  if (v > 0 && v < 0.1) v = 0.1;
  let digits = v >= 10 ? 0 : 1;
  if (v < 100 && v >= 99.5) { digits = 1; v = Math.min(99.9, Math.round(v * 10) / 10); }
  return new Intl.NumberFormat(LOCALES[lang] || "en-US", { style: "percent", maximumFractionDigits: digits }).format(v / 100);
}

/* ------------------------------------------------------------------ */
/*  Icon sprite (What's New repeats the same few icons ~300 times)      */
/* ------------------------------------------------------------------ */
// Same icon sources as the shared {% icon %} shortcode: src/_includes/icons
// first, then Lucide. Each icon becomes ONE <symbol> per page; entries then
// reference it with a tiny <svg><use href="#cmi-name"/></svg>.
const require = createRequire(import.meta.url);
let LUCIDE_DIR = null;
try { LUCIDE_DIR = path.join(path.dirname(require.resolve("lucide-static/package.json")), "icons"); } catch { /* not installed */ }
const symbolCache = new Map();
const SYMBOL_ATTRS = ["viewBox", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"];

export function iconSymbol(name) {
  if (symbolCache.has(name)) return symbolCache.get(name);
  const local = path.join("src/_includes/icons", `${name}.svg`);
  const file = fs.existsSync(local) ? local : LUCIDE_DIR ? path.join(LUCIDE_DIR, `${name}.svg`) : "";
  let out = "";
  if (file && fs.existsSync(file)) {
    const svg = fs.readFileSync(file, "utf8").replace(/<!--.*?-->/gs, "");
    const open = (svg.match(/<svg\b[^>]*>/) || [""])[0];
    const attrs = SYMBOL_ATTRS.map((a) => { const m = open.match(new RegExp(`\\s${a}="([^"]*)"`)); return m ? ` ${a}="${m[1]}"` : ""; }).join("");
    const inner = svg.slice(svg.indexOf(open) + open.length, svg.lastIndexOf("</svg>")).replace(/>\s+</g, "><").replace(/\s+/g, " ").trim();
    out = `<symbol id="cmi-${name}"${attrs.includes("viewBox") ? "" : ' viewBox="0 0 24 24"'}${attrs}>${inner}</symbol>`;
  } else {
    console.warn(`[community] missing icon for sprite: ${name}`);
  }
  symbolCache.set(name, out);
  return out;
}

/** Hidden sprite with every icon in `names` (duplicates ignored). */
export function iconSprite(names) {
  const list = [...new Set((names || []).filter(Boolean))];
  return `<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" class="absolute" aria-hidden="true" focusable="false"><defs>${list.map(iconSymbol).join("")}</defs></svg>`;
}

/** Reference to a sprite icon — same classes/a11y as the {% icon %} shortcode. */
export function iconUse(name, cls = "size-5") {
  return `<svg class="icon ${cls}" aria-hidden="true" focusable="false"><use href="#cmi-${name}"/></svg>`;
}

// Every icon the What's New timeline can reference.
export const WN_ICONS = [
  ...new Set([
    ...Object.values(GROUPS).map((g) => g.icon), ...Object.values(DRIVE_ICONS),
    "images", "book-open", "headphones", "youtube", "instagram", "users", "file-text", "grapes", "languages", "lock",
  ]),
];

/* ------------------------------------------------------------------ */
/*  Eleventy registration                                              */
/* ------------------------------------------------------------------ */
export default function (eleventyConfig, helpers) {
  const t = (key, lang, vars) => helpers.translateKey(key, lang, vars);
  // spotlight.json is read at most once per build (only while db.js does not provide it)
  eleventyConfig.on("eleventy.before", () => { spotlightFile = undefined; smallThumbSeen.clear(); });

  // Filters are prefixed "cm" (community) so they can never clash with another
  // area's filters; qrSvg keeps its plain name. QR code as inline SVG:
  //   {{ url | qrSvg("Label", "classes") | safe }}
  eleventyConfig.addFilter("qrSvg", (text, label = "", cls = "") => qrSvg(text, { label, cls }));
  eleventyConfig.addFilter("cmQrSymbol", (text, id) => qrSymbol(text, id));
  // Same SVG as a data: URI (download link). Encoded so it is safe in href="".
  eleventyConfig.addFilter("cmSvgDataUri", (svg) => "data:image/svg+xml;charset=utf-8," + encodeURIComponent(String(svg || "")));

  eleventyConfig.addFilter("cmWnPrepare", (items) => mergeMediaTwins(prepareWhatsNew(items)));
  eleventyConfig.addFilter("cmWnDays", (prepared, lang) => whatsNewDays(prepared, lang));
  eleventyConfig.addFilter("cmWnChips", (prepared) => chipList(prepared));
  eleventyConfig.addFilter("cmWnCountRecent", (prepared, days = 7) => countRecent(prepared, days));
  eleventyConfig.addFilter("cmHref", (item, lang) => hrefOf(item, lang));
  eleventyConfig.addFilter("cmTeaser", (summary, title) => teaser(summary, title));
  eleventyConfig.addFilter("cmListThumb", (src) => listThumb(src));
  eleventyConfig.addFilter("cmEventWhen", (ev, lang) => eventWhen(ev, lang));
  eleventyConfig.addFilter("cmEventWhere", (ev, lang) => eventWhere(ev, lang));
  eleventyConfig.addFilter("cmEventDayBox", (ev, lang) => eventDayBox(ev, lang));
  eleventyConfig.addFilter("cmEventMonthBox", (ev, lang) => eventMonthBox(ev, lang));
  eleventyConfig.addFilter("cmDateRange", (a, b, lang) => fmtRange(a, b, lang));
  eleventyConfig.addFilter("cmIssueLabel", (label, lang) => issueLabel(label, lang));

  // Monthly digest (/digest/): {% set md = db | cmMonthlyDigest(site) %} — LAST month's edition. MONTHLY_NOW
  // (the /monthly/ test clock) also moves it: MONTHLY_NOW=2026-10-01T15:05:00Z builds the September one.
  eleventyConfig.addFilter("cmMonthlyDigest", (db, site) => buildMonthlyDigest(db, { site }));
  eleventyConfig.addFilter("cmDigestIntro", (md, lang) => digestIntro(md, lang, t));
  eleventyConfig.addFilter("cmMonthWord", (key, lang) => monthWord(key, lang));
  // An event that took place, as the digest lists it: its day(s) only, seen from the month covered
  // ("Sat, Sep 12"; "Fri, Jun 25 – Sun, Jun 27"): {{ ev | cmEventDays(lang, md.edition) }}
  eleventyConfig.addFilter("cmEventDays", (ev, lang, ed) => eventWhen(ev, lang, Date.parse(`${ed && ed.last}T12:00:00Z`) || Date.now(), { time: false }));
  // An album row of the committee's uploads: "Photos: Booth" / "New photos"
  eleventyConfig.addFilter("cmAlbumTitle", (it, lang) => albumTitle(it, lang, t));
  // An Instagram post's one line (its caption's first line): {{ p | cmPostLine(lang, acc.name) }}
  eleventyConfig.addFilter("cmPostLine", (it, lang, name) => postLine(it, lang, t, name));
  // The media filters (media.js) register after this file (alphabetical load order),
  // so they are looked up when the digest renders, not now. Missing → raw titles.
  const filterFn = (name) => { const f = eleventyConfig.getFilter ? eleventyConfig.getFilter(name) : null; return typeof f === "function" ? f : null; };
  const mediaHelpers = () => ({ title: filterFn("mediaTitle"), cleanTitle: filterFn("mediaCleanTitle"), videoKind: filterFn("mediaVideoKind") });
  eleventyConfig.addFilter("cmDigestText", (md, langs, style, site) => monthlyDigestText(md, langs, style, site, t, mediaHelpers()));

  // Published writers (Area 65 first, then the rest of Texas): the digest's list is md.writers;
  // these print one writer's byline the same way everywhere.
  eleventyConfig.addFilter("cmWriterName", (item, lang) => writerName(item, lang, t));
  eleventyConfig.addFilter("cmWriterPlace", (item, lang) => writerPlace(item, lang));


  eleventyConfig.addFilter("cmStatus", (status) => statusView(status));
  // Drop items whose title (in `lang`) repeats an earlier one — scraped section
  // pages sometimes share a generic title ("Read"), which looks broken in lists.
  eleventyConfig.addFilter("cmUniqTitle", (items, lang) => uniqByTitle(items, lang));
  // Articles grouped by magazine issue (publication + issue key — GV September
  // and LV September/October share the key "2026-09"), in first-seen order.
  eleventyConfig.addFilter("cmByIssue", (items) => {
    const m = new Map();
    for (const it of items || []) {
      const k = it?.extra?.issue_key ? `${it.extra.publication || it.source}|${it.extra.issue_key}` : "other";
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(it);
    }
    return [...m.entries()].map(([key, list]) => ({ key, items: list }));
  });

  // mailto: with subject AND body (the shared `mailto` filter only takes a subject)
  eleventyConfig.addFilter("cmMailto", (email, subject = "", body = "") => {
    const q = [subject && "subject=" + encodeURIComponent(subject), body && "body=" + encodeURIComponent(body)].filter(Boolean).join("&");
    return `mailto:${email || ""}${q ? "?" + q : ""}`;
  });
  // "https://x.github.io/Repo/es/" → "x.github.io/Repo/es"
  eleventyConfig.addFilter("cmShortUrl", (u) => String(u || "").replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/$/, ""));
  // `cmWebcal` (https:// → webcal://) used by the community pages is registered in
  // committee.js; both files are auto-loaded, so it is available here too.
  eleventyConfig.addFilter("cmNum", (n, lang) => new Intl.NumberFormat(LOCALES[lang] || "en-US").format(Number(n) || 0));
  // 0–100 → "1.6%" / "1,6 %" (≥ 10 without decimals; a tiny non-zero value never shows as 0,
  // and anything short of 100 never rounds up to "100%": 99.9 → "99.9%", 99.97 → "99.9%")
  eleventyConfig.addFilter("cmPct", (n, lang) => cmPct(n, lang));

  // UI string with a fallback when the key does not exist (safe with I18N_STRICT=1):
  //   {{ ("community.status.src." + s.source) | cmTOr(lang, s.label) }}
  eleventyConfig.addFilter("cmTOr", (key, lang, fallback = "", vars) => {
    try {
      const v = helpers.translateKey(key, lang, vars);
      return v === key ? fallback : v;
    } catch {
      return fallback;
    }
  });

  // Issue label of an item in the page language ("Octubre 2026"), and the same
  // label for use inside a sentence ("octubre de 2026").
  eleventyConfig.addFilter("cmItemIssue", (item, lang) => issueLabelOf(item, lang));
  eleventyConfig.addFilter("cmIssueInSentence", (label, lang) => issueInSentence(label, lang));

  // Icon sprite: {{ names | cmIconSprite | safe }} once, then {{ "rss" | cmUse("size-4") | safe }}
  eleventyConfig.addFilter("cmIconSprite", (names) => iconSprite(names || WN_ICONS));
  eleventyConfig.addFilter("cmUse", (name, cls) => iconUse(name, cls));
  eleventyConfig.addGlobalData("cmWnIcons", WN_ICONS);
}
