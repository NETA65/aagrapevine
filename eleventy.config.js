// Eleventy configuration — NETA 65 Grapevine / La Viña site.
// Shared filters live here; page-area specific filters can be added as
// separate files in ./eleventy/filters/*.js (auto-loaded, see bottom).
import { EleventyHtmlBasePlugin } from "@11ty/eleventy";
import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import * as yaml from "js-yaml";
import markdownIt from "markdown-it";
import { setZone, zoneInstant } from "./eleventy/central-time.js";
import { iconSvg, iconSprite } from "./eleventy/icons.js";

const require = createRequire(import.meta.url);
const md = markdownIt({ html: false, linkify: true, breaks: true });
// Markdown written by the committee (bulletin posts, event descriptions) — the `md` filter. Raw HTML is
// shown as text (html: false), so a post can never put a script on the page. Options, for text that
// sits under a heading of its own: {{ body | md({ h: 3, lang: lang, name: title }) | safe }}
//   h     the level the text's own top headings get: a bulletin post's title is an h2, so the text's
//         headings start at h3 and each one is at most one level below the one before it ("# / ##",
//         "## / ###" and even "## / #### / #" → h3 / h4 / h3; h6 at most) — the page's outline stays
//         in order, with no level skipped, whatever levels the text jumps between;
//   lang  "es": links to the site's own pages ("/events/") lead to the Spanish page ("/es/events/"),
//         and the tables' label is in that language;
//   name  what the text belongs to (a post's title): each table is then named "Table 1 · <name>",
//         so a page with several posts never has two regions of the same name;
//   ids   a prefix (the post's own anchor): each heading gets an id, "<ids>--<its words>" ("ann-x--why-it-
//         matters"; the same words again: "…-2"), so a section can be linked to — the bulletin's "In this
//         post" list (the `mdToc` filter, which takes the same options and gives the same ids) and a link
//         shared to one section. "--" never occurs in a slug, so these ids never meet a post's own;
//   idsFrom  the text in its own language (a translated post's original): the ids take ITS headings' words,
//         heading by heading, when both have as many headings — so a section has the same id on the
//         English and the Spanish page, and a shared link, or the language switch (which keeps the #),
//         finds it in either. (Otherwise each page's own words.)
// A table comes in a box of its own that scrolls sideways on a phone (a named, focusable region, so a
// keyboard can scroll it too); pictures load lazily.
const mdSlug = (s) => String(s || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
  .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50).replace(/-+$/, "") || "section";
// A heading's words as plain text ("Why it **matters**" → "Why it matters"; a link keeps its words):
// tokens[i] is its heading_open, tokens[i + 1] the inline content.
const mdHeadingWords = (tokens, i) => (tokens[i + 1]?.type === "inline" ? tokens[i + 1].children || [] : [])
  .map((c) => (c.type === "text" || c.type === "code_inline" ? c.content : c.type === "softbreak" || c.type === "hardbreak" ? " " : ""))
  .join("").replace(/\s+/g, " ").trim();
// Every heading of the text at once (env is new for each render, so this runs once per text): its level
// on the page — with option h, its depth among the headings above it that are bigger (a stack of the
// text's own levels), never more than one step deeper — its words, and with option ids its id (from the
// words of idsFrom's headings when it has as many). Sets the tokens' tags and ids; returns
// [{ id, text, level }] in order.
function mdHeadingPlan(tokens, env) {
  const h = Math.min(6, Math.max(1, Number(env?.h) || 1));
  const open = [], used = new Map(), list = [];
  const heads = tokens.map((t, i) => (t.type === "heading_open" ? i : -1)).filter((i) => i >= 0);
  let named = null;
  if (env?.ids && env.idsFrom) {
    const other = md.parse(String(env.idsFrom), {});
    const words = other.map((t, i) => (t.type === "heading_open" ? mdHeadingWords(other, i) : null)).filter((w) => w !== null);
    if (words.length === heads.length) named = words;
  }
  heads.forEach((i, k) => {
    const t = tokens[i];
    const lv = Number(t.tag.slice(1));
    let tag = t.tag;
    if (h > 1) {
      while (open.length && open[open.length - 1] >= lv) open.pop();
      tag = "h" + Math.min(6, h + open.length);
      open.push(lv);
    }
    t.tag = tag;
    const close = tokens.findIndex((c, j) => j > i && c.type === "heading_close");
    if (close > 0) tokens[close].tag = tag;
    const text = mdHeadingWords(tokens, i);
    let id = "";
    if (env?.ids) {
      const base = `${env.ids}--${mdSlug(named ? named[k] : text)}`;
      const n = (used.get(base) || 0) + 1;
      used.set(base, n);
      id = n > 1 ? `${base}-${n}` : base;
      t.attrSet("id", id);
    }
    list.push({ id, text, level: Number(tag.slice(1)) });
  });
  return list;
}
const mdHeading = (tokens, idx, options, env, self) => {
  if (env && !env.hDone) { env.hDone = true; mdHeadingPlan(tokens, env); }
  return self.renderToken(tokens, idx, options);
};
// The sections of a text, for an "In this post" list: { h, ids, idsFrom } as given to `md` (the same ids). Its
// top-level headings — or, when there is only one of them, the headings right under it ("# Details"
// over "## Parking", "## Food" …). Fewer than two sections: [] (a list of one says nothing).
const mdToc = (s, opts) => {
  if (!s) return [];
  const env = { ...(opts || {}) };
  const list = mdHeadingPlan(md.parse(String(s), env), env).filter((x) => x.id && x.text);
  if (!list.length) return [];
  const top = Math.min(...list.map((x) => x.level));
  let out = list.filter((x) => x.level === top);
  if (out.length === 1) out = list.filter((x) => x.level === top + 1);
  return out.length >= 2 ? out.map(({ id, text }) => ({ id, text })) : [];
};
md.renderer.rules.heading_open = mdHeading;
md.renderer.rules.heading_close = mdHeading;
md.renderer.rules.table_open = (tokens, idx, options, env, self) => {
  const lang = env?.lang || "en";
  const label = env?.name ? translateKey("common.md_table_of", lang, { n: (env.tables = (env.tables || 0) + 1), name: env.name }) : translateKey("common.md_table", lang);
  return `<div class="md-table" role="region" tabindex="0" aria-label="${md.utils.escapeHtml(label)}">` + self.renderToken(tokens, idx, options);
};
md.renderer.rules.table_close = (tokens, idx, options, env, self) => self.renderToken(tokens, idx, options) + "</div>";
const mdImage = md.renderer.rules.image;
md.renderer.rules.image = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet("loading", "lazy");
  tokens[idx].attrSet("decoding", "async");
  return mdImage(tokens, idx, options, env, self);
};
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const href = tokens[idx].attrGet("href") || "";
  const pathOnly = href.split(/[?#]/)[0];
  // a page of this site ("/events/", "/" …), not a file ("/bulletin/files/flyer.pdf", "/feed.xml")
  if (env?.lang === "es" && /^\/(?![/\\])/.test(href) && !/^\/(en|es)(\/|$)/.test(pathOnly) && !/\.[a-z0-9]{2,5}$/i.test(pathOnly)) {
    tokens[idx].attrSet("href", "/es" + href);
  }
  return self.renderToken(tokens, idx, options);
};
// The site's time zone — config/site.yml site.timezone (America/Chicago; a name that is not a time zone, or no
// settings file, keeps that). Every date the build writes is in it: fmtDate, the © year, toDate's times without
// a zone, and the shared helper eleventy/central-time.js (set here, so src/_data/meeting.js, the area filters
// and the browser's copy — window.SITE.tz — all use the one zone). Area filters import it: { TZ }.
function siteTimezone() {
  try {
    return ((yaml.load(fs.readFileSync("config/site.yml", "utf8")) || {}).site || {}).timezone;
  } catch {
    return "";
  }
}
export const TZ = setZone(siteTimezone());
const LOCALES = { en: "en-US", es: "es-US" };

/* ------------------------------------------------------------------ */
/*  i18n helpers                                                       */
/* ------------------------------------------------------------------ */
let I18N = null;
function loadI18n() {
  const dir = "src/_i18n";
  const out = {};
  for (const f of fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort()) {
    const data = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
    for (const [k, v] of Object.entries(data)) out[k] = v;
  }
  return out;
}

function interpolate(str, vars) {
  if (!vars || typeof str !== "string") return str;
  return str.replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m));
}

export function translateKey(key, lang = "en", vars) {
  if (!I18N) I18N = loadI18n();
  const entry = I18N[key];
  if (!entry) {
    if (process.env.I18N_STRICT) throw new Error(`Missing i18n key: ${key}`);
    return key;
  }
  const s = entry[lang] ?? entry.en ?? key;
  return interpolate(s, vars);
}

// An item's text in a language: its translation (i18n[lang]), else the field written for that language
// (title_es), else the item's own words — its language's entry (i18n[item.lang]) or the field as published
// (extra.<field>, else <field>) — and English only when the item has no words of its own (a Spanish story
// without a translation into another language keeps its Spanish title rather than an English one).
export function pickLang(item, field, lang) {
  if (!item) return "";
  const i = item.i18n && item.i18n[field];
  if (i && (i[lang] || i[lang] === "")) return i[lang] || i[item.lang] || item[field] || "";
  if (item[field + "_" + lang]) return item[field + "_" + lang];
  if (i && item.lang && i[item.lang]) return i[item.lang];
  const own = item.extra && item.extra[field] !== undefined ? item.extra[field] : item[field];
  if (own !== undefined && own !== null && own !== "") return own;
  if (i && i.en) return i.en;
  return own ?? "";
}

/* ------------------------------------------------------------------ */
/*  Dates                                                              */
/* ------------------------------------------------------------------ */
/** A value from the data or a template → a Date (null when it is not one):
      "2026-10-21"           that day, at noon UTC — the same calendar day in Central time (and anywhere in the
                             Americas), so a date-only value never prints as the day before;
      "2026-10" / "2026"     that month / year, the same way (its 1st / January 1, at noon UTC) — not midnight
                             UTC, which is still the month before in Central time ("2026-10" printed "September");
      "2026-10-21T19:00", "2026-10-21 19:00:00"  a date and time without a zone: Central wall-clock time (TZ),
                             whatever zone the computer that builds the site is in;
      an instant with its zone ("…Z", "…-05:00"), a Date, ms → that instant. An invalid one → null.
    (Every filter that reads a date goes through here: fmtDate, isoDate, rfc822, isRecent, year, sortByDate and
    the area filters' helpers.toDate.) */
function toDate(v) {
  if (!v || typeof v === "boolean") return null;
  if (v instanceof Date) return isNaN(v) ? null : v;
  if (typeof v === "string") {
    const s = v.trim();
    let m = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(s);
    if (m) {
      const y = Number(m[1]), mo = Number(m[2] || 1), d = Number(m[3] || 1);
      const day = new Date(Date.UTC(y, mo - 1, d, 12));
      return day.getUTCMonth() === mo - 1 && day.getUTCDate() === d ? day : null;
    }
    m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3})\d*)?)?$/.exec(s);
    if (m) {
      const [y, mo, d, h, mi] = m.slice(1, 6).map(Number);
      if (mo < 1 || mo > 12 || d < 1 || d > 31 || h > 23 || mi > 59) return null;
      const ms = zoneInstant(y, mo - 1, d, h, mi, TZ) + Number(m[6] || 0) * 1000 + Number((m[7] || "").padEnd(3, "0"));
      return Number.isFinite(ms) ? new Date(ms) : null;
    }
  }
  const d = new Date(v);
  return isNaN(d) ? null : d;
}

function fmtDate(v, lang = "en", style = "long") {
  const d = toDate(v);
  if (!d) return "";
  const loc = LOCALES[lang] || "en-US";
  const opts = {
    short: { month: "short", day: "numeric", year: "numeric", timeZone: TZ },
    long: { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: TZ },
    medium: { month: "long", day: "numeric", year: "numeric", timeZone: TZ },
    month: { month: "long", year: "numeric", timeZone: TZ },
    monthShort: { month: "short", timeZone: TZ },
    day: { day: "numeric", timeZone: TZ },
    weekday: { weekday: "short", timeZone: TZ },
    time: { hour: "numeric", minute: "2-digit", timeZone: TZ, timeZoneName: "short" },
    datetime: { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZone: TZ, timeZoneName: "short" },
  }[style];
  if (style === "iso") return d.toISOString();
  if (style === "ymd") return d.toISOString().slice(0, 10);
  if (style === "relative") return relative(d, lang);
  let s = new Intl.DateTimeFormat(loc, opts || {}).format(d);
  // Spanish writes month names in lowercase ("octubre de 2026"). Only the "long" style, which
  // opens with the weekday and is used as a stand-alone line, gets a capital ("Miércoles, 21 …").
  if (lang === "es" && style === "long") s = s.charAt(0).toUpperCase() + s.slice(1);
  if (lang === "es") s = esMeridiem(s);
  return s;
}

/** Intl's Spanish "7:00 p.m." → "7:00 p. m.", the one spelling the whole site uses (RAE style).
    Both spaces are no-break spaces (U+00A0), so a narrow card never wraps "1:03 a." / "m.".
    The browser twin is GV.esMeridiem in src/assets/js/app.js. */
export function esMeridiem(s) {
  return String(s)
    .replace(/\b([ap])\.\s?m\./g, "$1.\u00a0m.")
    .replace(/(\d) (?=[ap]\.\u00a0m\.)/g, "$1\u00a0");
}

/* ------------------------------------------------------------------ */
/*  Links from data                                                    */
/* ------------------------------------------------------------------ */
// Every link that comes from synced data or hand-edited content (content/events/*.md,
// content/bulletin/*.md → data/site/*.json) passes through safeUrl()
// before a template writes it into href/src:
//   * http(s)://…, mailto:…, tel:…, "#fragment" and site-relative "/path" are kept;
//   * "//host/…", "www.district5.org" or "zoom.us/j/123" (scheme forgotten) become "https://…";
//   * anything else ("javascript:…", "data:…", relative "foo/bar", a bare file name) becomes ""
//     so the template hides the link instead of printing a broken or unsafe one.
// src/_data/db.js applies it to all URL fields of data/site/*.json; the `extUrl` filter is the
// same function for templates.
const FILE_EXT_TLD = /\.(?:jpe?g|png|gif|webp|avif|svg|pdf|docx?|xlsx?|pptx?|txt|md|html?|php|aspx?|mp3|m4a|mp4|mov|zip)$/i;
const BARE_HOST = /^(?:[\p{L}\p{N}](?:[\p{L}\p{N}-]*[\p{L}\p{N}])?\.)+\p{L}{2,24}(?::\d{1,5})?(?=[/?#]|$)/u;
export function safeUrl(value) {
  if (value === null || value === undefined || typeof value === "object") return "";
  // Browsers ignore tabs/newlines inside URLs ("java\tscript:" still runs), so drop all controls first.
  const s = String(value).trim().replace(/[\u0000-\u001f\u007f]/g, "");
  if (!s) return "";
  if (/^https?:\/\/[^\s/\\?#]/i.test(s)) return s;
  if (/^(?:mailto|tel):[^\s]/i.test(s)) return s;
  if (s.startsWith("#")) return s;
  if (/^\/(?![/\\])/.test(s)) return s; // "/path" (not "//host" or "/\host", which leave the site)
  if (/^\/\/[^\s/\\?#]/.test(s)) return "https:" + s;
  const host = s.match(BARE_HOST);
  if (host && (/^www\./i.test(s) || !FILE_EXT_TLD.test(host[0].replace(/:\d+$/, "")))) return "https://" + s;
  return "";
}

/* ------------------------------------------------------------------ */
/*  Our own addresses in a language, absolute addresses, share pictures */
/* ------------------------------------------------------------------ */
// Every address the build writes ("/es/feed.xml", "/events/" …: the `eleventy.contentMap` event, before any
// page is rendered); null outside a build (a filter called from a test or a script).
let builtUrls = null;
// The addresses that lead elsewhere and are left as they are (langPath, siteUrl). Any other "scheme:" — a
// "javascript:" that got this far — stays an address on our site, as these helpers always made it: harmless.
const OTHER_PLACE = /^(?:https?|mailto|tel|webcal):/i;

/** A link to one of the site's pages or files in a language (the `lurl` filter; community.js hrefOf):
    "/events/" → "/es/events/" on a Spanish page. A file — a document or picture ("/bulletin/files/flyer.pdf"),
    anything in /assets/ — exists once for both languages: it gets the prefix only when the build writes that
    file for the language too (/es/feed.xml, /es/events.ics, /es/manifest.webmanifest, /es/search-index.json …),
    never otherwise (outside a build: never). Other sites ("https://…", "//host/…"), mailto:, tel:, webcal: and
    "#…" are left as they are. */
export function langPath(url, lang) {
  if (!url || typeof url !== "string" || OTHER_PLACE.test(url) || /^(?:#|\/\/)/.test(url)) return url;
  const u = url.startsWith("/") ? url : "/" + url;
  if (!lang || lang === "en") return u;
  const p = u.split(/[?#]/)[0];
  const file = p.startsWith("/assets/") || /\.[a-z0-9]{1,12}$/i.test(p.slice(p.lastIndexOf("/") + 1));
  if (file && !(builtUrls && builtUrls.has(`/${lang}${p}`))) return u;
  return `/${lang}${u}`;
}

/** An absolute address on the public site (feeds, QR codes, share links and pictures): "/es/library/" →
    "https://…/aagrapevine/es/library/". An address that is already absolute (https:, mailto:, tel:, webcal:) is
    left as it is ("//host/…" gets https:). Nothing → the site's own address. */
export function siteUrl(url, site) {
  const u = url === null || url === undefined ? "" : String(url).trim();
  if (OTHER_PLACE.test(u)) return u;
  if (u.startsWith("//")) return "https:" + u;
  const b = String(site?.url || "").replace(/\/$/, "");
  return b + (u.startsWith("/") ? u : "/" + u);
}

// The Spanish twin of a config/site.yml `links:` entry whose name is not "<name>_es": La Viña's own page of
// the same thing (its "Lleva el Mensaje" page for Grapevine's Carry the Message).
const LINK_TWINS = { es: { carry_the_message: "lleva_el_mensaje" } };

/** One of the links in config/site.yml `links:` in the page's language (the `langLink` filter; area filters
    get it as a helper): on a Spanish page its Spanish twin when the settings have one — "<name>_es"
    (aa_twelve_and_twelve_es, support_phone_intl_es …) or the name in LINK_TWINS (carry_the_message →
    lleva_el_mensaje) —, else the link itself ("" when there is none).
      {{ site.links | langLink("carry_the_message", lang) }} */
export function langLink(links, key, lang) {
  const L = links && typeof links === "object" ? links : {};
  if (lang && lang !== "en") {
    const twin = L[(LINK_TWINS[lang] || {})[key]] || L[`${key}_${lang}`];
    if (twin) return twin;
  }
  return L[key] ?? "";
}

// A picture the link previews of WhatsApp, Facebook, iMessage … show: PNG, JPEG, GIF or WebP (never an SVG or a
// document) — by its file name, or Google's picture of a Drive file (lh3.googleusercontent.com, the event flyers)
// and YouTube's video pictures, which have none.
const SHARE_PICTURE = /\.(?:png|jpe?g|gif|webp)$/i;
const SHARE_PICTURE_HOST = /^(?:lh\d\.googleusercontent\.com|i\d?\.ytimg\.com)$/i;

/** A page's share picture (its `ogImage`: an address, or { src, width, height, alt }) → { url (absolute),
    width, height, alt } — width and height only when both are known (0 otherwise), alt "" when not given —,
    or null when there is none or it is not a picture the previews show (the page then keeps the committee's
    card). */
export function shareImage(img, site) {
  const o = img && typeof img === "object" ? img : { src: img };
  const src = safeUrl(o.src);
  if (!src || src.startsWith("#") || /^(?:mailto|tel):/i.test(src)) return null;
  const abs = siteUrl(src, site);
  let parsed;
  try { parsed = new URL(abs); } catch { return null; }
  if (!SHARE_PICTURE.test(parsed.pathname) && !SHARE_PICTURE_HOST.test(parsed.hostname)) return null;
  const w = Math.round(Number(o.width)) || 0, h = Math.round(Number(o.height)) || 0;
  return { url: abs, width: w > 0 && h > 0 ? w : 0, height: w > 0 && h > 0 ? h : 0, alt: String(o.alt ?? "").replace(/\s+/g, " ").trim() };
}

/* ------------------------------------------------------------------ */
/*  Monthly rules from config/site.yml (`meeting:`, `recurring_events:`) */
/* ------------------------------------------------------------------ */
// Read the way scripts/sync/meeting.py reads them (parse_hhmm; meeting_rule for the committee meeting,
// weekday_index / week_of_month_value for a recurring event, MonthlyRule.span for the end,
// check_skip_dates for skip_dates), so the pages and data/site/events.json always agree, and a value
// the daily sync accepts ("7:00 PM", "5pm", "sábado", "2nd", one skip date without brackets …) never
// stops the build. Unreadable values are left out: the pages' own defaults (3rd Wednesday, 19:00) apply.
// Every page reads the rules through here: src/_data/meeting.js (the home page, /meetings/' dates, the
// countdown), committee.js (/events/, /meetings/' lines, the calendar files) and monthly.js
// meetingByRule (the toolkit's rule-built dates and, through it, the monthly digest).
const WEEKDAY_NAME = {
  monday: "monday", tuesday: "tuesday", wednesday: "wednesday", thursday: "thursday", friday: "friday",
  saturday: "saturday", sunday: "sunday", lunes: "monday", martes: "tuesday", miercoles: "wednesday",
  "miércoles": "wednesday", jueves: "thursday", viernes: "friday", sabado: "saturday", "sábado": "saturday",
  domingo: "sunday",
};
const ORDINAL = {
  first: 1, second: 2, third: 3, fourth: 4, fifth: 5, last: -1, primer: 1, primero: 1, primera: 1,
  segundo: 2, segunda: 2, tercer: 3, tercero: 3, tercera: 3, cuarto: 4, cuarta: 4, quinto: 5, quinta: 5,
  ultimo: -1, "último": -1, ultima: -1, "última": -1,
};
const WEEKS = [1, 2, 3, 4, 5, -1];

/** "19:00", "7:00 PM", "7 p.m.", "7pm", "19h00", "19.30", 19 (the hour), 1140 (minutes: an unquoted 19:00)
    → "HH:MM"; else fallback (= parse_hhmm). */
export function hhmm(v, fallback = "") {
  if (v === null || v === undefined || v === "" || typeof v === "boolean") return fallback;
  let h, mi;
  if (typeof v === "number" && Number.isInteger(v)) {
    if (v >= 0 && v <= 23) [h, mi] = [v, 0];
    else if (v >= 24 * 60) [h, mi] = [Math.floor(v / 3600), Math.floor((v % 3600) / 60)];
    else [h, mi] = [Math.floor(v / 60), v % 60];
  } else {
    const m = /^\s*(\d{1,2})(?:[:.h](\d{2})(?::\d{2})?)?\s*(?:([ap])\.?\s*m\.?)?\s*$/i.exec(typeof v === "number" ? v.toFixed(2) : String(v));
    if (!m) return fallback;
    [h, mi] = [Number(m[1]), Number(m[2] || 0)];
    if (m[3]) {
      if (h < 1 || h > 12) return fallback;
      h = (h % 12) + (m[3].toLowerCase() === "p" ? 12 : 0);
    }
  }
  return h >= 0 && h <= 23 && mi >= 0 && mi <= 59 ? `${String(h).padStart(2, "0")}:${String(mi).padStart(2, "0")}` : fallback;
}

/** A monthly rule with canonical values: weekday "saturday", week_of_month 1–5 / -1, start / end "HH:MM" (the
    end as used: one hour after the start when missing, unreadable or not after it — 23:59 at most), skip_dates
    a list of "YYYY-MM-DD". forgiving = a recurring event (plurals "Saturdays", words "second" / "2nd" /
    "último", its key slugified as build_data.recurring_specs does); otherwise the committee meeting
    (meeting_rule: a day name, a whole number). Anything else in the entry (title, platform, zoom_url …) is
    kept as it is; a value already canonical stays the same, so reading a rule twice changes nothing. */
export function monthlyRule(o, forgiving = false) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return o;
  const out = { ...o };
  let wd = String(o.weekday ?? "").trim().toLowerCase();
  if (forgiving) {
    wd = wd.replace(/\.+$/, "");
    if (!Object.hasOwn(WEEKDAY_NAME, wd) && wd.endsWith("s")) wd = wd.slice(0, -1);
  }
  if (Object.hasOwn(WEEKDAY_NAME, wd)) out.weekday = WEEKDAY_NAME[wd]; else delete out.weekday;
  let n = null;
  const w = o.week_of_month;
  // the committee meeting: int() of it (2.9 → 2, " 3 " → 3); a recurring event: a whole number or its words
  if (typeof w === "number") n = forgiving && !Number.isInteger(w) ? null : Math.trunc(w);
  else if (typeof w === "string") {
    const s = w.trim().toLowerCase();
    const m = forgiving ? /^(-?\d)\s*(?:st|nd|rd|th|\.?\s*[ºoª°]|\.?\s*er|\.?\s*ra)?$/.exec(s) : /^[+-]?\d+$/.exec(s);
    n = forgiving && Object.hasOwn(ORDINAL, s) ? ORDINAL[s] : m ? Number(forgiving ? m[1] : m[0]) : null;
  }
  if (WEEKS.includes(n)) out.week_of_month = n; else delete out.week_of_month;
  for (const k of ["start", "end"]) {
    const t = hhmm(o[k]);
    if (t) out[k] = t; else delete out[k];
  }
  // The end as the sync uses it (MonthlyRule.span): missing, unreadable or not after the start → one hour
  // after the start, 23:59 at most (the committee meeting's start defaults to 19:00, as in meeting_rule).
  // A meeting without any time keeps none (the pages' 19:00–20:00 apply): `meeting: {}` stays empty.
  const st = out.start || (!forgiving && ("start" in o || "end" in o) ? "19:00" : "");
  if (st) {
    const [sh, sm] = st.split(":").map(Number);
    const [eh, em] = String(out.end || "00:00").split(":").map(Number);
    if (!out.end || eh * 60 + em <= sh * 60 + sm) out.end = sh < 23 ? `${String(sh + 1).padStart(2, "0")}:${String(sm).padStart(2, "0")}` : "23:59";
  }
  // One date written without the brackets counts too (check_skip_dates); a date object → "YYYY-MM-DD".
  if ("skip_dates" in o) {
    const sk = o.skip_dates;
    out.skip_dates = (Array.isArray(sk) ? sk : sk === null || sk === undefined || sk === "" ? [] : [sk])
      .map((d) => (d instanceof Date ? d.toISOString().slice(0, 10) : String(d ?? "").trim()));
  }
  if (forgiving) {
    // the key as build_data.recurring_specs makes it (common.slugify: ASCII, dashes, lower case, 32
    // characters, "item" when nothing is left; from the title when there is no key) — the `series` its
    // dates carry in data/site/events.json
    const slug = (v) => String(v || "").normalize("NFKD").replace(/[^\x00-\x7f]/g, "").replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "").toLowerCase().slice(0, 32).replace(/^-+|-+$/g, "");
    const title = String(o.title ?? "").trim() || String(o.title_es ?? "").trim();
    const key = String(o.key ?? "").trim() ? slug(o.key) || "item" : title ? slug(title) || "item" : "";
    if (key) out.key = key; else delete out.key;
  }
  return out;
}

function relative(d, lang) {
  const rtf = new Intl.RelativeTimeFormat(LOCALES[lang] || "en-US", { numeric: "auto" });
  const diff = (d.getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  const units = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];
  for (const [u, s] of units) if (abs >= s || u === "minute") return rtf.format(Math.round(diff / s), u);
  return "";
}

function dateVal(item) {
  if (!item) return 0;
  const v = item.extra && item.extra.start ? item.extra.start : item.date || item.first_seen;
  const d = toDate(v);
  return d ? d.getTime() : 0;
}

/* ------------------------------------------------------------------ */
export default function (eleventyConfig) {
  const pathPrefix = process.env.PATH_PREFIX || "/";

  eleventyConfig.addPlugin(EleventyHtmlBasePlugin);

  // Dev helper: ONLY=library,search npx @11ty/eleventy  → builds just those src/pages/* files
  if (process.env.ONLY) {
    const keep = process.env.ONLY.split(",").map((s) => s.trim()).filter(Boolean);
    for (const f of fs.readdirSync("src/pages")) {
      if (!keep.some((k) => f.startsWith(k))) eleventyConfig.ignores.add(`src/pages/${f}`);
    }
  }
  // autoescape MUST stay true: titles/captions come from third-party sources (XSS safety). Use | safe only for trusted HTML.
  eleventyConfig.setNunjucksEnvironmentOptions({ autoescape: true, trimBlocks: true, lstripBlocks: true, throwOnUndefined: false });

  // Rebuild i18n when those files change in --serve mode
  eleventyConfig.addWatchTarget("src/_i18n/");
  eleventyConfig.addWatchTarget("data/site/");
  eleventyConfig.addWatchTarget("config/");
  // (the booth display's CSV: src/_data/booth.js reads it, so an edit shows in the preview's /about/booth.json)
  eleventyConfig.addWatchTarget("content/booth/");
  eleventyConfig.on("eleventy.before", () => { I18N = loadI18n(); });

  /* ---------- passthrough ---------- */
  eleventyConfig.addPassthroughCopy({ "src/assets/img": "assets/img" });
  eleventyConfig.addPassthroughCopy({ "src/assets/js": "assets/js" });
  eleventyConfig.addPassthroughCopy({ "src/assets/cache": "assets/cache" });
  eleventyConfig.addPassthroughCopy({ "src/favicon.ico": "favicon.ico" });
  if (fs.existsSync("src/CNAME")) eleventyConfig.addPassthroughCopy({ "src/CNAME": "CNAME" });
  eleventyConfig.addPassthroughCopy({ "src/.nojekyll": ".nojekyll" });
  // Pictures and documents saved next to the bulletin's posts (content/bulletin/flyer.jpg) are published
  // at /bulletin/files/, where scripts/sync/announcements.py points the posts' links (any capitalization
  // of the extension: "Flyer.JPG" too). The folder's old name (content/announcements/) still works for a
  // post saved there by habit — announcements.py reads it and asks for the post to be moved.
  const anyCase = (ext) => [...ext].map((c) => `[${c}${c.toUpperCase()}]`).join("");
  const attachExt = ["jpg", "jpeg", "png", "gif", "webp", "pdf"].map(anyCase).join(",");
  eleventyConfig.addPassthroughCopy({
    [`content/bulletin/*.{${attachExt}}`]: "bulletin/files",
    [`content/announcements/*.{${attachExt}}`]: "bulletin/files",
  });
  // The booth display's photos and videos (the committee's Drive booth folder), saved for offline by
  // scripts/build/booth-media.mjs into .cache/booth-media/files/ just before the build (update.yml) — never in git —
  // are published at /about/booth/media/, where the show's data (src/_data/booth.js) points the slides that have a
  // saved copy (.cache/booth-media/manifest.json). No folder (the Code check, a fresh checkout): nothing to copy, and
  // the booth shows those pictures from Google's copy while online.
  if (fs.existsSync(".cache/booth-media/files")) eleventyConfig.addPassthroughCopy({ ".cache/booth-media/files": "about/booth/media" });
  // `npm start` never watches .cache/ (also the translation models, ~175 MB): a download writes its files in steps,
  // and every step would start a rebuild — after downloading, start the preview again to publish the new files.
  // (.gitignore lists .cache/ too, and Eleventy reads it; this says it outright. watchIgnores is a Set in Eleventy 3;
  // the check keeps the tests' stand-in configuration in tests/nodejs.py working.)
  if (eleventyConfig.watchIgnores instanceof Set) eleventyConfig.watchIgnores.add(".cache/**");
  // Self-hosted open-source vendor libs (no CDN dependency)
  const nm = (p) => "node_modules/" + p;
  eleventyConfig.addPassthroughCopy({
    [nm("alpinejs/dist/cdn.min.js")]: "assets/vendor/alpine.min.js",
    [nm("minisearch/dist/umd/index.js")]: "assets/vendor/minisearch.js",
    [nm("glightbox/dist/js/glightbox.min.js")]: "assets/vendor/glightbox.min.js",
    [nm("glightbox/dist/css/glightbox.min.css")]: "assets/vendor/glightbox.min.css",
    [nm("lite-youtube-embed/src/lite-yt-embed.js")]: "assets/vendor/lite-yt-embed.js",
    [nm("lite-youtube-embed/src/lite-yt-embed.css")]: "assets/vendor/lite-yt-embed.css",
    [nm("html-to-image/dist/html-to-image.js")]: "assets/vendor/html-to-image.js", // /monthly/ poster → PNG
  });
  for (const f of ["inter-latin-wght-normal", "inter-latin-ext-wght-normal", "inter-latin-wght-italic"]) {
    eleventyConfig.addPassthroughCopy({ [nm(`@fontsource-variable/inter/files/${f}.woff2`)]: `assets/fonts/${f}.woff2` });
  }
  // Fraunces "opsz" files (wght + opsz axes — all the CSS uses); the "full" files add the
  // SOFT/WONK axes the site never sets and are ~45–70 KB bigger each.
  for (const f of ["fraunces-latin-opsz-normal", "fraunces-latin-ext-opsz-normal", "fraunces-latin-opsz-italic"]) {
    eleventyConfig.addPassthroughCopy({ [nm(`@fontsource-variable/fraunces/files/${f}.woff2`)]: `assets/fonts/${f}.woff2` });
  }

  /* ---------- i18n filters ---------- */
  eleventyConfig.addFilter("t", (key, lang, vars) => translateKey(key, lang, vars));
  eleventyConfig.addFilter("tx", (item, field, lang) => pickLang(item, field, lang));
  eleventyConfig.addFilter("machineFor", (item, lang) => !!(item && item.machine && item.machine.includes(lang)));
  // {{ "/events/" | lurl(lang) }}: our page (or file) in the page's language — langPath above. It learns which files
  // the build writes per language here, before any page is rendered.
  eleventyConfig.on("eleventy.contentMap", ({ urlToInputPath }) => { builtUrls = new Set(Object.keys(urlToInputPath || {})); });
  eleventyConfig.addFilter("lurl", langPath);
  // {{ site.links | langLink("carry_the_message", lang) }}: a config link in the page's language (its Spanish twin on /es/)
  eleventyConfig.addFilter("langLink", langLink);
  eleventyConfig.addFilter("altLangUrl", (url, lang) => {
    const u = url || "/";
    if (lang === "es") return u.replace(/^\/es(\/|$)/, "/") || "/";
    return "/es" + (u.startsWith("/") ? u : "/" + u);
  });
  eleventyConfig.addFilter("otherLang", (lang) => (lang === "es" ? "en" : "es"));
  eleventyConfig.addFilter("pick", (obj, lang, field = "") => {
    // pick(obj, lang, "title") → obj.title_es || obj.title  (for config/site.yml style fields)
    if (!obj) return "";
    if (lang !== "en" && obj[`${field}_${lang}`]) return obj[`${field}_${lang}`];
    return obj[field] ?? "";
  });

  /* ---------- dates ---------- */
  eleventyConfig.addFilter("fmtDate", fmtDate);
  // {{ label | meridiem(lang) }}: a time label built elsewhere gets the site's Spanish "p. m." spelling.
  eleventyConfig.addFilter("meridiem", (s, lang) => (lang === "es" ? esMeridiem(s ?? "") : s));
  eleventyConfig.addFilter("toDate", toDate);
  eleventyConfig.addFilter("isoDate", (v) => { const d = toDate(v); return d ? d.toISOString() : ""; });
  eleventyConfig.addFilter("rfc822", (v) => { const d = toDate(v); return d ? d.toUTCString() : ""; });
  eleventyConfig.addFilter("isRecent", (v, days = 14) => { const d = toDate(v); return !!d && Date.now() - d.getTime() < days * 864e5 && d.getTime() <= Date.now() + 864e5; });
  eleventyConfig.addFilter("sortByDate", (items, dir = "desc") => [...(items || [])].sort((a, b) => (dir === "asc" ? dateVal(a) - dateVal(b) : dateVal(b) - dateVal(a))));
  eleventyConfig.addFilter("upcoming", (items) => (items || []).filter((i) => dateVal(i) >= Date.now() - 6 * 3600e3).sort((a, b) => dateVal(a) - dateVal(b)));
  eleventyConfig.addFilter("past", (items) => (items || []).filter((i) => dateVal(i) < Date.now() - 6 * 3600e3).sort((a, b) => dateVal(b) - dateVal(a)));
  eleventyConfig.addFilter("withinDays", (items, days = 7) => (items || []).filter((i) => { const t = dateVal(i); return t && Date.now() - t <= days * 864e5 && t <= Date.now() + 864e5; }));
  eleventyConfig.addFilter("duration", (sec) => {
    sec = Math.round(Number(sec) || 0);
    if (!sec) return "";
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
  });
  // The footer's "© {{ site.built | year }}": the year in Central time, like every other date here (a build
  // after 6 PM Central on Dec 31 is already next year in UTC, and the © stayed a year ahead until the next build).
  const YEAR_FMT = new Intl.DateTimeFormat("en-US", { timeZone: TZ, year: "numeric" });
  eleventyConfig.addFilter("year", (v) => { const d = toDate(v); return d ? Number(YEAR_FMT.format(d)) : ""; });

  /* ---------- collections helpers ---------- */
  eleventyConfig.addFilter("where", (items, key, val) => (items || []).filter((i) => {
    const v = key.split(".").reduce((o, k) => (o == null ? o : o[k]), i);
    return Array.isArray(val) ? val.includes(v) : v === val;
  }));
  eleventyConfig.addFilter("whereNot", (items, key, val) => (items || []).filter((i) => {
    const v = key.split(".").reduce((o, k) => (o == null ? o : o[k]), i);
    return Array.isArray(val) ? !val.includes(v) : v !== val;
  }));
  eleventyConfig.addFilter("whereIncludes", (items, key, val) => (items || []).filter((i) => {
    const v = key.split(".").reduce((o, k) => (o == null ? o : o[k]), i);
    return Array.isArray(v) ? v.includes(val) : typeof v === "string" && v.includes(val);
  }));
  eleventyConfig.addFilter("limit", (arr, n) => (arr || []).slice(0, n));
  eleventyConfig.addFilter("offset", (arr, n) => (arr || []).slice(n));
  eleventyConfig.addFilter("groupBy", (items, key) => {
    const m = new Map();
    for (const i of items || []) {
      const v = key.split(".").reduce((o, k) => (o == null ? o : o[k]), i) ?? "other";
      if (!m.has(v)) m.set(v, []);
      m.get(v).push(i);
    }
    return [...m.entries()].map(([k, v]) => ({ key: k, items: v }));
  });
  eleventyConfig.addFilter("countBy", (items, key) => {
    const o = {};
    for (const i of items || []) { const v = key.split(".").reduce((x, k) => (x == null ? x : x[k]), i) ?? "other"; o[v] = (o[v] || 0) + 1; }
    return o;
  });
  eleventyConfig.addFilter("pluck", (items, key) => (items || []).map((i) => key.split(".").reduce((o, k) => (o == null ? o : o[k]), i)));
  eleventyConfig.addFilter("uniq", (arr) => [...new Set((arr || []).filter((x) => x !== undefined && x !== null && x !== ""))]);
  eleventyConfig.addFilter("keys", (o) => Object.keys(o || {}));
  eleventyConfig.addFilter("values", (o) => Object.values(o || {}));
  eleventyConfig.addFilter("length", (a) => (a ? (a.length ?? Object.keys(a).length) : 0));
  eleventyConfig.addFilter("shuffleSeed", (arr, seed = 1) => {
    // deterministic shuffle (build-time) so pages don't churn randomly
    const a = [...(arr || [])]; let s = seed;
    for (let i = a.length - 1; i > 0; i--) { s = (s * 9301 + 49297) % 233280; const j = Math.floor((s / 233280) * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  });

  /* ---------- text ---------- */
  eleventyConfig.addFilter("md", (s, opts) => (s ? md.render(String(s), { ...(opts || {}) }) : ""));
  // a text's sections for an "In this post" list: [{ id, text }] — the ids `md` gives with the same { h, ids, idsFrom }
  eleventyConfig.addFilter("mdToc", mdToc);
  eleventyConfig.addFilter("mdInline", (s) => (s ? md.renderInline(String(s)) : ""));
  eleventyConfig.addFilter("stripHtml", (s) => String(s || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim());
  eleventyConfig.addFilter("excerpt", (s, n = 160) => {
    s = String(s || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    return s.length > n ? s.slice(0, n).replace(/\s+\S*$/, "") + "…" : s;
  });
  eleventyConfig.addFilter("json", (v) => JSON.stringify(v));
  eleventyConfig.addFilter("fileSize", (b) => {
    b = Number(b) || 0; if (!b) return "";
    const u = ["B", "KB", "MB", "GB"]; let i = 0; while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
    return `${b.toFixed(i ? 1 : 0)} ${u[i]}`;
  });
  eleventyConfig.addFilter("absUrl", (url, base) => {
    try { return new URL(url, (base || "").replace(/\/?$/, "/")).toString(); } catch { return url; }
  });
  // Absolute URL on the public site (feeds, QR codes, share pictures): {{ "/es/library/" | siteUrl(site) }} — siteUrl above
  eleventyConfig.addFilter("siteUrl", siteUrl);
  // A page's share picture (base.njk og:image / twitter:image): {{ ogImage | shareImage(site) }} — shareImage above
  eleventyConfig.addFilter("shareImage", shareImage);
  // Data-driven href/src: {{ item.extra.website | extUrl }} → "" when the value is not a safe link.
  eleventyConfig.addFilter("extUrl", safeUrl);
  eleventyConfig.addFilter("hostname", (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } });
  eleventyConfig.addFilter("driveImg", (fileId, w = 800) => (fileId ? `https://lh3.googleusercontent.com/d/${fileId}=w${w}` : ""));
  eleventyConfig.addFilter("ytThumb", (id, q = "hqdefault") => (id ? `https://i.ytimg.com/vi/${id}/${q}.jpg` : ""));
  eleventyConfig.addFilter("mailto", (email, subject) => `mailto:${email}${subject ? "?subject=" + encodeURIComponent(subject) : ""}`);
  eleventyConfig.addFilter("urlencode", (s) => encodeURIComponent(String(s || "")));

  /* ---------- icons: {% icon "name", "extra classes", "label" %} ----------
     One small <svg> pointing at the page's icon sprite (<use href="#i-name">); the iconSprite transform then
     puts the drawings of the icons each page uses in one hidden <svg> at the start of its <body>. The how and
     why: eleventy/icons.js. label: the icon is a picture with that name (escaped); without one, decoration.
     An unknown name: a warning and nothing. */
  eleventyConfig.addShortcode("icon", (name, cls = "size-5", label = "") => {
    const svg = iconSvg(name, cls, label);
    if (!svg) console.warn(`[icon] missing icon: ${name}`);
    return svg;
  });
  eleventyConfig.addTransform("iconSprite", function (content) {
    const out = (this.page && this.page.outputPath) || this.outputPath;
    return typeof out === "string" && out.endsWith(".html") ? iconSprite(content) : content;
  });

  /* ---------- Tailwind CSS (compiled after each build) ----------
     Every .css file at the top of src/assets/css is a stylesheet of its own, at /assets/css/<same name>:
     main.css (every page — base.njk) and the page-area stylesheets only some pages link (pageStyles:
     booth.css, expenses.css … — see "Page-area styles" at the end of main.css). Compiled side by side, one
     Tailwind process each; a failed one fails the build. The log shows Tailwind's own words only when it
     says more than its name and "Done", then one line with each stylesheet's size. Not for a build that
     writes no files (Eleventy's toJSON(), as tests use it): nothing to style, and no stray ./_site. */
  eleventyConfig.on("eleventy.after", async ({ directories, dir, outputMode }) => {
    if (outputMode && outputMode !== "fs") return;
    // `directories.output` honors the CLI --output flag (`dir` is deprecated in Eleventy 3)
    const outDir = path.join((directories && directories.output) || dir.output, "assets/css");
    fs.mkdirSync(outDir, { recursive: true });
    const cli = path.join(path.dirname(require.resolve("@tailwindcss/cli/package.json")), "dist", "index.mjs");
    const sheets = fs.readdirSync("src/assets/css").filter((f) => f.endsWith(".css")).sort();
    const routine = /^\s*(?:≈ tailwindcss v[\d.]+|Done in [\d.]+\s*m?s)?\s*$/;
    await Promise.all(sheets.map((f) => new Promise((resolve, reject) => {
      execFile(process.execPath, [cli, "-i", `src/assets/css/${f}`, "-o", path.join(outDir, f), "--minify"], (err, stdout, stderr) => {
        const said = String(stderr || "").replace(/\x1b\[[0-9;]*m/g, "").split(/\r?\n/).filter((l) => !routine.test(l));
        if (err || said.length) process.stderr.write(`[css] ${f}:\n${stderr}`);
        if (err) reject(new Error(`[css] ${f}: Tailwind failed (${err.code ?? err.message})`));
        else resolve();
      });
    })));
    console.log(`[css] ${sheets.map((f) => `${f} ${Math.round(fs.statSync(path.join(outDir, f)).size / 1024)} KB`).join(" · ")}`);
  });

  /* ---------- area-specific filters (auto-loaded) ---------- */
  const extraDir = path.resolve("eleventy/filters");
  if (fs.existsSync(extraDir)) {
    for (const f of fs.readdirSync(extraDir).filter((f) => f.endsWith(".js")).sort()) {
      eleventyConfig.addPlugin(async (cfg) => {
        const mod = await import("./eleventy/filters/" + f);
        await mod.default(cfg, { translateKey, pickLang, fmtDate, toDate, esMeridiem, langLink, langPath });
      });
    }
  }

  return {
    pathPrefix,
    dir: { input: "src", includes: "_includes", data: "_data", output: "_site" },
    templateFormats: ["njk", "md", "html", "11ty.js"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
}
