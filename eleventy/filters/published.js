// Area filters — Published Writers (/published/ and /es/published/).
// Auto-loaded by eleventy.config.js. Every filter name starts with "pw" so it never
// collides with another page area.
//
// Data: data/site/spotlight.json (docs/DATA_SCHEMA.md → "spotlight.json"): Grapevine and
// La Viña stories with a byline whose extra.pub_date lies in the longest window
// (spotlight.list_days, e.g. [60, 90]), each with extra.geo.scope = neta65 | texas | other |
// unknown. Templates read it as db.spotlight; until src/_data/db.js lists "spotlight" this
// module reads the file itself (same link cleaning as db.js: safeUrl on url/image).
//
// The windows are counted from TODAY in America/Chicago (the build day here; the browser
// recounts from its own today in /assets/js/published.js), so the server-rendered default
// view and the script always agree on the same day.
//
// The page's second list, the Texas writers archive (#archive — pwArchive below), comes from
// data/site/writers_archive.json (db.writers_archive; docs/DATA_SCHEMA.md → "writers_archive.json"):
// every story by a Texas writer in the magazines' online archives, plus every captured Texas story.
//
// Dev switches:
//   PW_TODAY=2026-11-30 npx @11ty/eleventy …   build as if it were that day (empty windows)
//   PW_EMPTY=1 npx @11ty/eleventy …           build as if no story had been found yet
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import * as yaml from "js-yaml";
import { safeUrl, TZ } from "../../eleventy.config.js";
import { scriptJson } from "../script-json.js";
import { issueName, localizeIssueLabel } from "./read.js";

const require = createRequire(import.meta.url);

const EMPTY = !!process.env.PW_EMPTY;
/** Where a writer is from, in display order. "texas" here = Texas OUTSIDE Area 65. */
export const PW_GROUPS = ["neta65", "texas", "other", "unknown"];
/** The scope filter: which groups each choice shows (Area 65 first, then Texas, then the rest). */
export const PW_SCOPES = { neta65: ["neta65"], texas: ["neta65", "texas"], all: ["neta65", "texas", "other", "unknown"] };
const PUBS = ["all", "gv", "lv"];
/** Cards shown per group before "see more" (divisible by 2, 3, 4 and 6 columns). Area 65 is the
 *  highlight: its 12 most recent stories, then "Show all N from our Area"; the other groups show 12
 *  more per click ("Show 12 more"). Without JavaScript every story of the default view shows. */
export const PW_GROUP_LIMIT = 12;
const ANONYMOUS = /^\s*(anonymous|an[oó]nim[oa]|anon\.?)\s*$/i;
const YMD = /^\d{4}-\d{2}-\d{2}$/;

/* ------------------------------------------------------------------ */
/*  small utils                                                        */
/* ------------------------------------------------------------------ */
const str = (v) => (v === null || v === undefined ? "" : String(v)).replace(/\s+/g, " ").trim();

/** Lower case, accents removed, apostrophes dropped, initials kept together, other punctuation → spaces:
 *  "Peñasco, Tejas" → "penasco tejas", "Beginner's" → "beginners", "H. T. B." → "htb" (so the searches
 *  "beginners" and "H.T.B." find them; published.js and published-archive.js do the same). The edge before the
 *  initials is a group, not a lookbehind: the page scripts use the same pattern, and Safari before 16.4 has no
 *  lookbehind. */
const INITIALS = /(^|[^\p{L}\p{N}])(\p{L}\.(?:\s*\p{L}\.)+)/gu;
export function pwNorm(s) {
  return foldWords(str(s).replace(INITIALS, (m, pre, ini) => pre + ini.replace(/[.\s]/g, "")));
}
/** pwNorm without keeping initials together ("H. T. B." → "h t b"). */
function foldWords(s) {
  return s.toLowerCase().normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replace(/['\u2018\u2019\u02bc]/g, "").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

/** The search words of a story (a card's or an archive row's data-s): each field normalized on its own, each word
 *  once — initials both together and one by one ("M.B." → "mb m b"): a search keeps initials together only when
 *  each letter has its period, so "M.B.", "MB", "M.B" and "M B" all find the writer. */
function pwWords(fields) {
  const out = new Set();
  for (const f of fields) {
    if (f === null || f === undefined || f === "") continue;
    for (const w of (pwNorm(f) + " " + foldWords(str(f))).split(" ")) if (w) out.add(w);
  }
  return [...out].join(" ");
}

function todayChicago() {
  const env = process.env.PW_TODAY;
  if (env && YMD.test(env)) return env;
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

/** "2026-09-23" minus 60 days → "2026-07-25" (calendar days, no time-zone drift). */
export function pwMinusDays(ymd, n) {
  const d = new Date(ymd + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

function hostOf(u) {
  try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; }
}

function initialsOf(name) {
  const words = str(name).replace(/[^\p{L}\s.-]/gu, " ").split(/[\s.-]+/).filter(Boolean);
  if (!words.length) return "";
  return (words[0][0] + (words.length > 1 ? words[words.length - 1][0] : "")).toUpperCase();
}

/* ------------------------------------------------------------------ */
/*  settings + data                                                    */
/* ------------------------------------------------------------------ */
let cfgCache = null;
function spotlightConfig() {
  if (cfgCache) return cfgCache;
  let s = {};
  try { s = (yaml.load(fs.readFileSync("config/site.yml", "utf8")) || {}).spotlight || {}; } catch { s = {}; }
  cfgCache = s && typeof s === "object" ? s : {};
  return cfgCache;
}

function readSpotlightFile() {
  try {
    const data = JSON.parse(fs.readFileSync("data/site/spotlight.json", "utf8"));
    if (!data || !Array.isArray(data.items)) return null;
    for (const it of data.items) {
      if (!it || typeof it !== "object") continue;
      it.url = safeUrl(it.url);
      if (it.image !== undefined && it.image !== null) it.image = safeUrl(it.image);
      if (it.extra && typeof it.extra.issue_url === "string") it.extra.issue_url = safeUrl(it.extra.issue_url);
    }
    return data;
  } catch {
    return null;
  }
}

/** The spotlight site file: db.spotlight when db.js provides it, else read here. */
function spotlightOf(db) {
  if (EMPTY) return { updated: null, items: [] };
  const s = db && db.spotlight;
  if (s && Array.isArray(s.items)) return s;
  return readSpotlightFile() || { updated: null, items: [] };
}

function listDaysOf(data) {
  const raw = Array.isArray(data.list_days) ? data.list_days : spotlightConfig().list_days;
  const days = (Array.isArray(raw) ? raw : []).map(Number).filter((n) => Number.isInteger(n) && n > 0 && n <= 3660);
  const uniq = [...new Set(days)];
  if (!uniq.length) return { list: [60, 90], def: 60 };
  // "first = default" (config/site.yml); the choices are shown shortest first.
  return { list: [...uniq].sort((a, b) => a - b), def: uniq[0] };
}

function defaultScopeOf(data) {
  const v = data.default_scope || spotlightConfig().default_scope;
  return PW_SCOPES[v] ? v : "neta65";
}

/* ------------------------------------------------------------------ */
/*  view model                                                         */
/* ------------------------------------------------------------------ */
function viewItem(it, lang, h) {
  const e = it.extra || {};
  const geo = e.geo && typeof e.geo === "object" ? e.geo : {};
  const scope = PW_GROUPS.includes(geo.scope) ? geo.scope : "unknown";
  const pub = (e.publication || it.category) === "lv" || it.source === "lavina" ? "lv" : "gv";
  const date = YMD.test(e.pub_date || "") ? e.pub_date : str(it.date).slice(0, 10);
  const origTitle = str(it.title);
  const title = str(h.pickLang(it, "title", lang)) || origTitle;
  const origLang = it.lang === "en" || it.lang === "es" ? it.lang : "";
  const translated = !!origLang && origLang !== lang && title !== origTitle;
  const machine = translated && Array.isArray(it.machine) && it.machine.includes(lang);

  const rawAuthor = str(e.author);
  const anonymous = !rawAuthor || ANONYMOUS.test(rawAuthor);
  const author = anonymous ? h.translateKey("published.anonymous", lang) : rawAuthor;

  let place = "";
  if (scope !== "unknown") {
    place = str(lang === "es" ? geo.label_es : geo.label_en) || str(geo.label_en) || str(h.pickLang(it, "author_location", lang)) || str(e.author_location);
  }
  const county = (scope === "neta65" || scope === "texas") && str(geo.county) && !/\b(county|condado)\b/i.test(place)
    ? h.translateKey("published.county", lang, { county: str(geo.county) }) : "";

  // La Viña's issue by the site's one name for it ("September–October 2026": read.js issueName)
  const issue = (pub === "lv" && issueName(e.issue_key, "lv", lang)) || str(h.pickLang(it, "issue_label", lang)) || str(e.issue_label);
  const section = str(h.pickLang(it, "section", lang));
  const topic = str(h.pickLang(it, "topic", lang));
  const meta = [];
  for (const v of [section, topic]) if (v && !meta.some((m) => pwNorm(m) === pwNorm(v))) meta.push(v);

  const i18nTitle = (it.i18n && it.i18n.title) || {};
  // Writer, place (both languages, county) and title (both languages); each word once (each field on its own:
  // two writers' initials side by side stay two words).
  const search = pwWords([
    rawAuthor, anonymous ? author : "", geo.city, geo.county, geo.label_en, geo.label_es, e.author_location,
    origTitle, i18nTitle.en, i18nTitle.es,
  ]);

  return {
    id: str(it.id),
    scope, pub, date,
    url: it.url, host: hostOf(it.url),
    image: str(it.image),
    title, titleLang: translated ? lang : origLang, origTitle: translated ? origTitle : "", origLang, machine,
    author, anonymous, initials: anonymous ? "" : initialsOf(rawAuthor),
    place, county,
    issue, meta,
    free: e.free === true ? true : e.free === false ? false : null,
    exclusive: e.online_exclusive === true,
    isNew: it.is_new === true,
    search,
  };
}

function inScope(item, scope) { return PW_SCOPES[scope].includes(item.scope); }
function inPub(item, pub) { return pub === "all" || item.pub === pub; }

/**
 * db | pwView(lang) → everything the page needs, with the DEFAULT filters applied
 * (default scope + first list_days window, all magazines, no search) so the page works
 * without JavaScript and matches what published.js shows on the same day.
 */
function pwView(db, lang, h) {
  const data = spotlightOf(db);
  const { list: listDays, def: defDays } = listDaysOf(data);
  const defScope = defaultScopeOf(data);
  const today = todayChicago();
  const cutoffs = Object.fromEntries(listDays.map((d) => [d, pwMinusDays(today, d)]));

  const seen = new Set();
  const items = [];
  for (const it of data.items || []) {
    if (!it || typeof it !== "object" || it.status === "gone" || it.kind !== "article" || !it.url) continue;
    const v = viewItem(it, lang, h);
    if (!v.date || !v.title || seen.has(v.id)) continue;
    seen.add(v.id);
    items.push(v);
  }
  const rank = Object.fromEntries(PW_GROUPS.map((g, i) => [g, i]));
  items.sort((a, b) => rank[a.scope] - rank[b.scope] || (a.date < b.date ? 1 : a.date > b.date ? -1 : 0) || a.title.localeCompare(b.title, lang));

  // counts[days][scope][pub] — stories inside each window (the window is open-ended at the top:
  // a story counts from its pub_date on, whatever the clock says).
  const counts = {};
  for (const d of listDays) {
    counts[d] = {};
    for (const s of Object.keys(PW_SCOPES)) {
      counts[d][s] = {};
      for (const p of PUBS) counts[d][s][p] = items.filter((i) => i.date >= cutoffs[d] && inScope(i, s) && inPub(i, p)).length;
    }
  }

  const defCut = cutoffs[defDays];
  const longest = listDays[listDays.length - 1];
  const groups = PW_GROUPS.map((key) => {
    const all = items.filter((i) => i.scope === key);
    let n = 0;
    // visible: one of the first PW_GROUP_LIMIT stories of the default view; over: in the default view
    // but past the limit — shown without JavaScript, hidden from the first paint with it (html.js)
    const rows = all.map((i) => {
      const match = i.date >= defCut && inScope(i, defScope);
      const visible = match && n < PW_GROUP_LIMIT;
      const over = match && !visible;
      if (match) n++;
      return { ...i, visible, over };
    });
    const matchCount = n;
    const hiddenByLimit = Math.max(0, matchCount - PW_GROUP_LIMIT);
    // Our Area, all shown but the longest window holds more of it: "Show all N from our Area" widens
    // the period (published.js does the same from the browser's own today).
    let widen = null;
    if (key === "neta65" && defScope === "neta65" && matchCount > 0 && !hiddenByLimit && longest > defDays) {
      const more = all.filter((i) => i.date >= cutoffs[longest]).length;
      if (more > matchCount) widen = { days: longest, n: more };
    }
    return { key, items: rows, total: all.length, matchCount, shownCount: matchCount - hiddenByLimit, hiddenByLimit, widen };
  }).filter((g) => g.total > 0);

  const shownTotal = counts[defDays][defScope].all;
  // "Also in the last N days: X stories by writers elsewhere in Texas / outside Texas"
  const nextScope = defScope === "neta65" ? "texas" : defScope === "texas" ? "all" : "";
  const moreCount = nextScope ? counts[defDays][nextScope].all - shownTotal : 0;

  const cfg = spotlightConfig();
  const counties = (Array.isArray(cfg.neta65_counties) ? cfg.neta65_counties : []).map(str).filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "en"));

  return {
    today, cutoffs, listDays, defDays, defScope, defPub: "all",
    items, groups, counts, shownTotal, nextScope, moreCount,
    counties, countyCount: counties.length,
    updated: data.updated || null,
    limit: PW_GROUP_LIMIT,
    total: items.length,
  };
}

/* ------------------------------------------------------------------ */
/*  Texas writers archive (#archive): every story by a Texas writer in  */
/*  the magazines' online archives, plus every captured Texas story     */
/* ------------------------------------------------------------------ */
// db.writers_archive (scripts/sync/build_data.py; docs/DATA_SCHEMA.md → "writers_archive.json"): items with
// scope neta65 | texas (= Texas outside Area 65), writers[] (name, anonymous, place as printed, geo), issue_key,
// year, theme, summary (the magazine's own subtitle), audio / online_exclusive / column flags and i18n + machine
// like every other site item. The page renders the Area 65 rows (they show without JavaScript and are kept
// offline with the page); the rest of Texas goes into /published/texas-archive.json
// (src/pages/published-archive-json.11ty.js), which /assets/js/published-archive.js fetches only when the
// page's scope asks for it (All of Texas / Everyone). No file → no rows → the page leaves the section out.

/** Rows shown before "Show 40 more" (the page hands it to published-archive.js). */
export const PW_ARC_PAGE = 40;
/** Area 65 hometowns offered as search chips above the archive. */
const ARC_TOP = 8;
/** The only links an archive row may have: the magazines' own pages (published-archive.js checks the same). */
const ARC_URL = /^https:\/\/(?:www\.)?(?:aagrapevine|aalavina)\.org\/\S*$/;
const PUB_NAME = { gv: "Grapevine", lv: "La Viña" };

function archiveOf(db) {
  const a = db && db.writers_archive;
  return a && typeof a === "object" && Array.isArray(a.items) ? a : { updated: null, items: [] };
}

/** An item the archive can list: a story page of either magazine, with a title. */
function arcUsable(it) {
  return !!it && typeof it === "object" && ARC_URL.test(str(it.url)) && !!str(it.title);
}

/** The year each magazine's online archive starts: data.since (build_data), else the oldest story listed. */
function arcSince(data, items) {
  const out = {};
  for (const p of ["gv", "lv"]) {
    const v = Number(data.since && data.since[p]);
    const years = items.filter((it) => (it.pub === "lv" ? "lv" : "gv") === p && Number.isInteger(it.year)).map((it) => it.year);
    out[p] = Number.isInteger(v) && v > 1900 ? v : years.length ? Math.min(...years) : null;
  }
  const known = [out.gv, out.lv].filter(Boolean);
  out.all = known.length ? Math.min(...known) : null;
  return out;
}

/** A writer's place in the page language: the geo label ("Denton, Texas" / "Condado de Smith, Texas"),
 *  else the place as printed. */
function arcPlace(w, lang) {
  const g = w.geo && typeof w.geo === "object" ? w.geo : {};
  return str(lang === "es" ? g.label_es : g.label_en) || str(g.label_en) || str(w.place);
}

/** Every query word must start a word of the row's search words (the rule of published.js and
 *  published-archive.js): "dal" finds Dallas — but a year is a whole word: "1990" is not the decade "1990s". */
function arcMatches(search, toks) {
  const s = " " + search + " ";
  return toks.every((t) => s.includes(/^\d{4}$/.test(t) ? " " + t + " " : " " + t));
}

/** "1990" → 1990s first, "undated" last. */
const decRank = (d) => (d === "undated" ? -1 : Number(d));

function arcRow(it, lang, h) {
  if (!arcUsable(it)) return null;
  const url = str(it.url);
  const pub = it.pub === "lv" ? "lv" : "gv";
  const origTitle = str(it.title);
  const origLang = it.lang === "en" || it.lang === "es" ? it.lang : pub === "lv" ? "es" : "en";
  const title = str(h.pickLang(it, "title", lang)) || origTitle;
  const translated = origLang !== lang && title !== origTitle;
  const machine = translated && Array.isArray(it.machine) && it.machine.includes(lang);

  // The writers as the magazine printed them, as the items of the byline (a meta-row: the dots between them
  // never start a line): ["John W.", "Denton, Texas"] (+ the county, like the cards); a letters column with
  // several Texas writers: ["Irene H-P. (San Antonio)", "Stacy C. (Horseshoe Bay)"].
  const writers = (Array.isArray(it.writers) ? it.writers : []).filter((w) => w && typeof w === "object");
  const anonymous = h.translateKey("published.anonymous", lang);
  const nameOf = (w) => (!str(w.name) || w.anonymous === true || ANONYMOUS.test(str(w.name)) ? anonymous : str(w.name));
  let by = [];
  let county = "";
  if (writers.length === 1) {
    const w = writers[0];
    const g = w.geo && typeof w.geo === "object" ? w.geo : {};
    const place = arcPlace(w, lang);
    by = [nameOf(w), place].filter(Boolean);
    if ((g.scope === "neta65" || g.scope === "texas") && str(g.county) && !/\b(county|condado)\b/i.test(place)) {
      county = h.translateKey("published.county", lang, { county: str(g.county) });
    }
  } else if (writers.length > 1) {
    by = writers.map((w) => {
      const town = str(w.geo && w.geo.city) || arcPlace(w, lang).split(",")[0].trim();
      return town ? `${nameOf(w)} (${town})` : nameOf(w);
    });
  }

  const key = /^\d{4}-(0[1-9]|1[0-2])$/.test(str(it.issue_key)) ? str(it.issue_key) : "";
  const year = Number.isInteger(it.year) ? it.year : key ? Number(key.slice(0, 4)) : null;
  const dec = year ? String(Number.isInteger(it.decade) ? it.decade : Math.floor(year / 10) * 10) : "undated";
  // the site's one name for an issue (read.js issueName): "October 1991", La Viña "September–October 2016"
  const issue = issueName(key, pub, lang) || (str(it.issue_label) ? localizeIssueLabel(str(it.issue_label), lang, pub) : "");

  // theme and the magazine's subtitle: translated when there is a translation, else as printed (with its lang)
  const theme = str(h.pickLang(it, "theme", lang));
  const themeI18n = (it.i18n && it.i18n.theme) || {};
  const themeLang = theme && str(themeI18n[lang]) === theme ? lang : origLang;
  const origBrief = str(it.summary);
  const brief = str(h.pickLang(it, "summary", lang)) || origBrief;
  const briefLang = brief && brief !== origBrief ? lang : origLang;
  // a machine-translated subtitle under a title that has no mark of its own (the title not translated, or
  // translated by hand): the subtitle carries the mark
  const briefMachine = !machine && briefLang === lang && origLang !== lang && Array.isArray(it.machine) && it.machine.includes(lang);

  // Search words, each once: writers (as printed, places, cities, counties, both labels), the title in every
  // language, the theme, the year, the decade ("1990s") and the magazine — not the subtitle.
  const i18nTitle = (it.i18n && it.i18n.title) || {};
  const words = [title, origTitle, i18nTitle.en, i18nTitle.es, it.theme, themeI18n.en, themeI18n.es,
    year, year ? dec + "s" : "", PUB_NAME[pub]];
  for (const w of writers) {
    const g = w.geo && typeof w.geo === "object" ? w.geo : {};
    words.push(w.name, nameOf(w), w.place, g.city, g.county, g.label_en, g.label_es,
      str(g.county) ? h.translateKey("published.county", lang, { county: str(g.county) }) : "");
  }
  const search = pwWords(words);

  return {
    id: str(it.id), key: str(it.key).toLowerCase() || url.toLowerCase(),
    url, host: hostOf(url), pub, scope: it.scope === "neta65" ? "neta65" : "texas",
    title, titleLang: translated ? lang : origLang, origTitle: translated ? origTitle : "", origLang, machine,
    by, multi: writers.length > 1, county,
    issueKey: key, issue, year, dec,
    // "Grapevine Online Exclusives" is a theme in name only: the online-exclusive flag says it
    theme: it.online_exclusive === true && /online exclusive/i.test(theme) ? "" : theme, themeLang, brief, briefLang, briefMachine,
    audio: it.audio === true, exclusive: it.online_exclusive === true, column: it.column === true,
    // the Area 65 hometowns of this story's writers (for the place chips)
    towns: [...new Set(writers.filter((w) => w.geo && w.geo.scope === "neta65" && str(w.geo.city)).map((w) => str(w.geo.city)))],
    search,
  };
}

/** One rest-of-Texas row for the JSON file (src/pages/published-archive-json.11ty.js documents the keys). */
function arcCompact(r, lang) {
  const o = { o: r.o, u: r.url, p: r.pub, t: r.title };
  if (r.titleLang !== lang) o.tl = r.titleLang;
  if (r.origTitle) { o.g = r.origTitle; o.gl = r.origLang; }
  if (r.machine) o.m = 1;
  if (r.by.length) o.b = r.by;
  if (r.multi) o.w = 1;
  if (r.county) o.c = r.county;
  if (r.issue) o.i = r.issue;
  if (r.year) o.y = r.year;
  o.d = r.dec;
  if (r.theme) { o.h = r.theme; if (r.themeLang !== lang) o.hl = r.themeLang; }
  if (r.brief) { o.r = r.brief; if (r.briefLang !== lang) o.rl = r.briefLang; if (r.briefMachine) o.rm = 1; }
  if (r.audio) o.a = 1;
  if (r.exclusive) o.x = 1;
  if (r.column) o.k = 1;
  o.s = r.search;
  return o;
}

function buildArchive(data, lang, h) {
  const T = (k, vars) => h.translateKey(k, lang, vars);
  const seen = new Set();
  const rows = [];
  for (const it of data.items) {
    const r = arcRow(it, lang, h);
    if (!r || seen.has(r.key)) continue;
    seen.add(r.key);
    rows.push(r);
  }
  // Decade groups newest first ("Date not shown" last); in each, the newest issue first, then the title.
  // `o` = the row's place in the whole list: the JSON rows slot in between the page's rows by it.
  const when = (r) => r.issueKey || (r.year ? String(r.year) : "");
  rows.sort((a, b) => decRank(b.dec) - decRank(a.dec) || (when(a) < when(b) ? 1 : when(a) > when(b) ? -1 : 0)
    || a.title.localeCompare(b.title, lang) || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
  rows.forEach((r, i) => { r.o = i; });

  const decKeys = [...new Set(rows.map((r) => r.dec))].sort((a, b) => decRank(b) - decRank(a));
  // counts[scope][pub][decade] for the first paint (the chips, before the JSON is in): "texas" = all of Texas,
  // Area 65 included; pub all | gv | lv; decade all | 2020 … | undated
  const counts = {};
  for (const s of ["neta65", "texas"]) {
    counts[s] = {};
    for (const p of PUBS) {
      const c = { all: 0 };
      for (const d of decKeys) c[d] = 0;
      for (const r of rows) {
        if ((s === "texas" || r.scope === "neta65") && (p === "all" || r.pub === p)) { c.all++; c[r.dec]++; }
      }
      counts[s][p] = c;
    }
  }

  const areaRows = rows.filter((r) => r.scope === "neta65");
  const restRows = rows.filter((r) => r.scope !== "neta65");
  // Without JavaScript every Area 65 row shows; with it the first PW_ARC_PAGE (the rest wait for
  // "Show 40 more": `over` rows are hidden from the first paint, published.css).
  areaRows.forEach((r, i) => { r.over = i >= PW_ARC_PAGE; });
  const decades = decKeys.map((key) => {
    const area = areaRows.filter((r) => r.dec === key);
    return {
      key, label: key === "undated" ? T("published.archive.undated") : T("published.archive.decade", { d: key }),
      rows: area, n: area.length, all: counts.texas.all[key],
      over: area.length > 0 && area.every((r) => r.over),
    };
  });

  // The Area 65 hometowns with the most stories; n = what a search for the name finds among the Area 65
  // rows (the place chips put the name into the page's search box).
  const tally = new Map();
  for (const r of areaRows) for (const t of r.towns) tally.set(t, (tally.get(t) || 0) + 1);
  const top = [...tally.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "en")).slice(0, ARC_TOP)
    .map(([label]) => {
      const toks = pwNorm(label).split(" ").filter(Boolean);
      return { label, n: areaRows.filter((r) => arcMatches(r.search, toks)).length };
    })
    .sort((a, b) => b.n - a.n || a.label.localeCompare(b.label, "en"));

  // version = a fingerprint of the JSON file: the page asks for texas-archive.json?v=<version>, a new address
  // whenever the rows change — so a browser can never slot an older file's rows (their `o`) into a newer page.
  // (Not build.version: that is the code's fingerprint and stays the same when only the stories change.)
  const json = restRows.map((r) => arcCompact(r, lang));
  const version = crypto.createHash("sha1").update(JSON.stringify(json)).digest("hex").slice(0, 10);
  return {
    total: rows.length, area: areaRows.length,
    since: arcSince(data, data.items.filter(arcUsable)),
    counts, decades, areaRows, restRows,
    json, version,
    // an Area 65 row with a machine translation (its title or its subtitle): the list's note shows without JavaScript
    mt: areaRows.some((r) => r.machine || r.briefMachine),
    top, page: PW_ARC_PAGE,
    updated: data.updated || null,
  };
}

/**
 * db | pwArchive(lang) → the Texas writers archive for one language:
 * { total, area (Area 65 rows), since {gv, lv, all}, counts[scope][pub][decade], decades [{key, label, rows
 * (its Area 65 rows), n, all, over}], areaRows, restRows, json (the rest of Texas, compact), version (the
 * JSON's fingerprint), mt (an Area 65 row is machine-translated), top [{label, n}], page, updated }. Built once
 * per language and build.
 */
let arcCache = new Map();
function pwArchive(db, lang, h) {
  const data = archiveOf(db);
  // Each template gets its own copy of the data: the cache goes by what the file holds — its date and a
  // checksum of the stories' ids and titles (emptied before each build)
  let sum = 0;
  for (const it of data.items) {
    const s = it && typeof it === "object" ? `${it.id}|${it.title}` : "";
    for (let i = 0; i < s.length; i++) sum = (sum * 31 + s.charCodeAt(i)) | 0;
  }
  const key = [lang, data.updated, data.items.length, sum].join("|");
  if (!arcCache.has(key)) arcCache.set(key, buildArchive(data, lang, h));
  return arcCache.get(key);
}

/** db → { total, area, since } — the archive's headline numbers without building the rows (the home page). */
export function pwArchiveTotals(db) {
  const data = archiveOf(db);
  const seen = new Set();
  const items = [];
  for (const it of data.items) {
    if (!arcUsable(it)) continue;
    const key = str(it.key).toLowerCase() || str(it.url).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    items.push(it);
  }
  return { total: items.length, area: items.filter((it) => it.scope === "neta65").length, since: arcSince(data, items).all };
}

/** mailto: link with a subject and a pre-filled body (CRLF line breaks, RFC 6068). */
function pwMailto(email, subject, body) {
  const e = str(email);
  if (!e) return "";
  const q = [];
  if (subject) q.push("subject=" + encodeURIComponent(str(subject)));
  if (body) q.push("body=" + encodeURIComponent(String(body).replace(/\r?\n/g, "\r\n")));
  return safeUrl("mailto:" + e + (q.length ? "?" + q.join("&") : ""));
}

/** UI strings published.js needs (raw templates: it fills {n} {days} {pub} {q} {stories} itself). */
const JS_KEYS = [
  "status.neta65.one", "status.neta65.other", "status.texas.one", "status.texas.other",
  "status.all.one", "status.all.other", "status.pub", "status.q",
  "n_stories.one", "n_stories.other", "show_all", "show_all_area", "show_more", "shown_of", "widen_note",
  "empty.neta65", "empty.texas", "empty.all", "empty.filtered",
  "more.texas", "more.all", "btn.texas", "btn.all",
];
function pwStrings(lang, h) {
  const out = {};
  for (const k of JS_KEYS) out[k] = h.translateKey("published." + k, lang);
  return out;
}

/** UI strings published-archive.js needs (raw templates; keys under published. unless they start with common.). */
const ARC_JS_KEYS = [
  "archive.status.neta65.one", "archive.status.neta65.other", "archive.status.texas.one", "archive.status.texas.other",
  "archive.when.since", "archive.when.dec", "archive.when.undated", "status.pub", "status.q",
  "archive.loading", "archive.load_error", "archive.empty_title", "archive.empty_text", "archive.empty_filters",
  "n_stories.one", "n_stories.other", "show_all", "show_more", "shown_of",
  "writer", "archive.writers", "opens_on", "original_title", "archive.audio", "online_exclusive", "archive.column",
  "common.auto_translated",
];
function pwArcStrings(lang, h) {
  const out = {};
  for (const k of ARC_JS_KEYS) out[k] = h.translateKey(k.startsWith("common.") ? k : "published." + k, lang);
  return out;
}

/* ------------------------------------------------------------------ */
/*  Icon sprite: the page repeats a few icons in every card (150+ cards), so they are  */
/*  defined once as <symbol>s and referenced with <use> — same Lucide / local art as   */
/*  the {% icon %} shortcode, a fraction of the bytes.                                 */
/* ------------------------------------------------------------------ */
const symbolCache = new Map();
function iconFile(name) {
  const local = path.join("src/_includes/icons", `${name}.svg`);
  if (fs.existsSync(local)) return local;
  try {
    const f = path.join(path.dirname(require.resolve("lucide-static/package.json")), "icons", `${name}.svg`);
    return fs.existsSync(f) ? f : "";
  } catch { return ""; }
}
function symbolOf(name) {
  if (symbolCache.has(name)) return symbolCache.get(name);
  let out = "";
  const f = /^[a-z0-9-]+$/.test(name) ? iconFile(name) : "";
  if (f) {
    const svg = fs.readFileSync(f, "utf8").replace(/<!--.*?-->/gs, "").trim();
    const m = svg.match(/<svg\b([^>]*)>([\s\S]*)<\/svg>/i);
    if (m) {
      const keep = ["viewBox", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"]
        .map((a) => { const v = m[1].match(new RegExp(`\\s${a}="([^"]*)"`)); return v ? ` ${a}="${v[1]}"` : ""; }).join("");
      out = `<symbol id="pw-i-${name}"${keep}>${m[2].replace(/>\s+</g, "><").trim()}</symbol>`;
    }
  } else {
    console.warn(`[published] missing icon: ${name}`);
  }
  symbolCache.set(name, out);
  return out;
}
/** "quote,lock" | pwSprite → one hidden <svg> holding those symbols (put it once on the page). */
function pwSprite(names) {
  const list = String(names || "").split(",").map((s) => s.trim()).filter(Boolean);
  return `<svg class="pw-sprite" aria-hidden="true" focusable="false" width="0" height="0">${list.map(symbolOf).join("")}</svg>`;
}
/** "lock" | pwIcon("size-3") → <svg class="icon size-3"><use href="#pw-i-lock"/></svg> (decorative) */
function pwIcon(name, cls = "size-4") {
  const n = String(name || "");
  if (!/^[a-z0-9-]+$/.test(n)) return "";
  return `<svg class="icon ${cls}" aria-hidden="true" focusable="false"><use href="#pw-i-${n}"/></svg>`;
}

/** JSON for an inline <script type="application/json"> (the shared serializer, eleventy/script-json.js). */
const pwJson = scriptJson;

export default function (eleventyConfig, helpers) {
  const h = helpers || {};
  eleventyConfig.on("eleventy.before", () => { cfgCache = null; arcCache = new Map(); });
  eleventyConfig.addFilter("pwView", (db, lang) => pwView(db, lang || "en", h));
  eleventyConfig.addFilter("pwStrings", (lang) => pwStrings(lang || "en", h));
  eleventyConfig.addFilter("pwArchive", (db, lang) => pwArchive(db, lang || "en", h));
  eleventyConfig.addFilter("pwArcStrings", (lang) => pwArcStrings(lang || "en", h));
  eleventyConfig.addFilter("pwJson", pwJson);
  eleventyConfig.addFilter("pwSprite", pwSprite);
  eleventyConfig.addFilter("pwIcon", pwIcon);
  eleventyConfig.addFilter("pwMailto", pwMailto);
  // "2 stories" / "1 historia" (published.n_stories.one|other)
  eleventyConfig.addFilter("pwStories", (n, lang) => h.translateKey(Number(n) === 1 ? "published.n_stories.one" : "published.n_stories.other", lang, { n }));
  // 1263 → "1,263" (the same as the page scripts' Intl.NumberFormat)
  eleventyConfig.addFilter("pwNum", (n, lang) => new Intl.NumberFormat(lang === "es" ? "es-US" : "en-US").format(Number(n) || 0));
}
