// The /events/ list, worked out at build time from the events the page shows (src/pages/events.njk) — and the events'
// data checks on /status/. Since the list's redesign (November 2026) the page leads with what is new: the one-off
// events, month by month; a monthly series is ONE card ("Every second Saturday of the month · Next: Sat, Dec 12 ·
// See all dates →") instead of a card for each of its dates (86 of the page's 112 cards were such dates); each date
// keeps its own entry in the "Next 5 weeks" calendar, the .ics feeds, its series' page and its own page.
//
//   {{ upcoming | evList(db, site, lang) }}  → { oneOff, series, nextUp, nextShown, facets } (eventList below)
//   {{ ev | evFacets(site) | safe }}         → the card's filter attributes: ` data-kind="workshop" data-lang="es"
//                                              data-mode="inperson" data-city="fort-worth"` (+ data-district)
//   {{ db | evDataChecks(site, lang) }}      → the events /status/ asks the committee to look at (dataChecks below)
//
// The filters of the page (src/assets/js/committee.js cmEvents) read the attributes; without JavaScript every card
// shows. A card's facets:
//   kind      what it is, from its kind (eleventy/event-pages.js eventKind): "workshop" (writing, recording,
//             information workshops, GVR/RLV orientations, La Viña's monthly workshop), "area" (assemblies, ACMs, the
//             Area's town hall, its GSR/DCM orientations), "booth", "online" (an online meeting: the Grapevine
//             Meeting, the weekly open meetings), "committee" (our committee meeting), "calendar" (an event from
//             Grapevine's or La Viña's own calendar), "other" (anything else: an intergroup meeting …)
//   lang      the language it is held in: "en" | "es" | "both" — a content/events file's `language:` (extra.language),
//             a series' config/site.yml `language:` (recurring_events, meeting), else its words ("bilingual",
//             "(in Spanish)", "(in English)" in a title or summary, either language), else held in Spanish when
//             committee.js heldInSpanish says so (La Viña's own events, La Viña's calendar, a file tagged la-vina),
//             else English (what the Area's and the committee's events are held in unless they say otherwise)
//   mode      "inperson", "online", or both ("inperson online": a place AND an online link)
//   city      its city (the data's extra.city, else its place's: committee.js eventPlace), as a slug — "" online
//   district  a content/events file's `district:` (extra.district: "87"), else none
//
// (Not in eleventy/event-pages.js: that file holds no Eleventy registration — test_unused_code reads every filter of
// eleventy/filters/ — and this one needs the page's own list and language.)
import fs from "node:fs";
import path from "node:path";
import LANGUAGES from "../../src/_data/languages.js";
import { nthWeekday } from "../central-time.js";
import { eventKind, eventPagePlan } from "../event-pages.js";
import { cancelledPages } from "../cancelled-pages.js";
import { oldAnchors } from "../event-redirects.js";
import { eventPlace, heldInSpanish, seriesNext, seriesPagePath, slugify, eventPagePath, EVENT_PAGE_ANCHOR, COMMITTEE_MEETING_PATH, TZ } from "./committee.js";
import { eventTone } from "./event-tone.js";

const EMPTY = !!process.env.COMMITTEE_EMPTY;

/** The kind chips of /events/, in their order (evlist.kind.<facet>: their words). */
export const KIND_FACETS = Object.freeze(["workshop", "area", "booth", "online", "committee", "calendar", "other"]);
/** The language and mode choices (evlist.lang.<v>, evlist.mode.<v>). */
export const LANG_FACETS = Object.freeze(["en", "es", "both"]);
export const MODE_FACETS = Object.freeze(["inperson", "online"]);
/** How many dates a series' card lists (the rest: its series' page). */
export const SERIES_DATES_SHOWN = 3;
/** How many events the "Next up" strip shows. */
export const NEXT_UP = 3;
const NEXT_UP_SPARE = 2;

const FAMILY_FACET = { workshop: "workshop", area: "area", booth: "booth", committee: "committee", calendar: "calendar" };
/** An event's kind chip (see the top of this file). */
export function kindFacet(ev, site) {
  const k = eventKind(ev, site);
  return k.kind === "online-meeting" ? "online" : FAMILY_FACET[k.family] || "other";
}

// A language as written in a settings file or a content/events `language:` line → "en" | "es" | "both" | "".
// (scripts/sync/announcements.py event_language reads a file's line with the same words.)
const LANG_WORD = {
  en: "en", english: "en", ingles: "en", es: "es", spanish: "es", espanol: "es",
  both: "both", bilingual: "both", bilingue: "both", "en-es": "both", "es-en": "both",
};
const fold = (s) => String(s ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
export function langWord(v) {
  return LANG_WORD[fold(v).trim().replace(/\s+/g, " ")] || "";
}
// what its words say (titles and summaries, without case or accents)
const SAYS_BOTH = /\bbilingu|\b(?:in english and spanish|in spanish and english|en ingles y (?:en )?espanol|en espanol y (?:en )?ingles|in both languages|en (?:ambos|los dos) idiomas)\b/;
const SAYS_ES = /\((?:in|en) (?:spanish|espanol)\)|\bin spanish\b|\b(?:en|in) espanol\b/;
const SAYS_EN = /\((?:in|en) (?:english|ingles)\)|\bin english\b|\ben ingles\b/;

function recordOf(ev) {
  return ev && ev.item && typeof ev.item === "object" ? ev.item : ev || {};
}
function seriesEntry(site, key) {
  const raw = site?.recurring_events;
  const list = Array.isArray(raw) ? raw : raw && typeof raw === "object" ? [raw] : [];
  return key ? list.find((e) => e && typeof e === "object" && String(e.key ?? "") === key) || null : null;
}
function seriesKeyOf(ev) {
  return String((ev && (ev.recurring ? ev.series : ev.seriesOf)) || "");
}
function wordsOf(ev) {
  const rec = recordOf(ev);
  const i = rec.i18n || {};
  return [ev.title, ev.summary, rec.title, rec.summary, i.title?.en, i.title?.es, i.summary?.en, i.summary?.es]
    .filter((s) => typeof s === "string" && s).map(fold).join(" \n ");
}

/** The language an event is held in (see the top of this file) → "en" | "es" | "both". */
export function heldIn(ev, site) {
  const rec = recordOf(ev);
  const x = rec.extra || {};
  const own = langWord(x.language)
    || langWord(seriesEntry(site, seriesKeyOf(ev))?.language)
    || (ev.committee ? langWord(site?.meeting?.language) : "");
  if (own) return own;
  const words = wordsOf(ev);
  const en = SAYS_EN.test(words), es = SAYS_ES.test(words);
  if (SAYS_BOTH.test(words) || en && es) return "both";
  if (en) return "en";
  // its words before its host: La Viña's "Taller (in English)" is held in English
  return es || heldInSpanish(ev) ? "es" : "en";
}

/** Its city, in words ("Fort Worth"), "" for an online event or a place without one. */
export function cityOf(ev) {
  if (!ev || ev.committee || !ev.location || ev.locationTba && !recordOf(ev).extra?.city) return "";
  const x = recordOf(ev).extra || {};
  if (x.city) return String(x.city).replace(/\s+/g, " ").trim();
  const p = eventPlace(String(ev.location), x);
  return String((p && p.address && p.address.addressLocality) || "").trim();
}

/** A content/events file's district ("87"), else "". */
export function districtOf(ev) {
  const d = String(recordOf(ev).extra?.district ?? "").trim();
  return /^\d{1,3}$/.test(d) ? d : "";
}

/** In person, online, or both → ["inperson"] | ["online"] | ["inperson", "online"]. */
export function modesOf(ev) {
  if (ev.committee) return ["online"];
  const place = !!ev.location;
  const online = !!ev.isOnline;
  if (place && online) return ["inperson", "online"];
  return online ? ["online"] : ["inperson"];
}

/** Every facet of a card → { kind, lang, modes, city, citySlug, district }. */
export function facetsOf(ev, site) {
  const city = cityOf(ev);
  return { kind: kindFacet(ev, site), lang: heldIn(ev, site), modes: modesOf(ev), city, citySlug: city ? slugify(city, 40) : "", district: districtOf(ev) };
}

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);
/** The card's filter attributes, ready for the markup (each value is a word of [a-z0-9-] or a district number). */
export function facetAttrs(f) {
  return ` data-kind="${esc(f.kind)}" data-lang="${esc(f.lang)}" data-mode="${esc(f.modes.join(" "))}"`
    + (f.citySlug ? ` data-city="${esc(f.citySlug)}"` : "") + (f.district ? ` data-district="${esc(f.district)}"` : "");
}

/* ------------------------------------------------------------------ */
/*  The list                                                           */
/* ------------------------------------------------------------------ */
const WD = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };
/** A monthly rule's day in the month of `ymd` ("YYYY-MM-DD" | null): { weekday: 0–6 or its name, n (week_of_month) }. */
function ruleDay(rule, ymd) {
  const wd = typeof rule?.weekday === "number" ? rule.weekday : WD[String(rule?.weekday ?? "").toLowerCase()];
  const n = Number(rule?.n ?? rule?.week_of_month);
  if (wd === undefined || !Number.isInteger(n)) return null;
  const y = Number(ymd.slice(0, 4)), mo = Number(ymd.slice(5, 7)) - 1;
  const d = nthWeekday(y, mo, wd, n);
  return d ? `${ymd.slice(0, 7)}-${String(d).padStart(2, "0")}` : null;
}
// "Dec 12" / "12 dic" for a "YYYY-MM-DD" day, in the page's language (Central days are calendar days)
function shortDay(ymd, lang) {
  const d = new Date(`${ymd}T12:00:00Z`);
  if (!Number.isFinite(d.getTime())) return ymd;
  const s = new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", { month: "short", day: "numeric", timeZone: "UTC" }).format(d);
  return s.replace(/\.(?=\s|$)/g, "");
}

/**
 * What changed about a series' dates, soonest first (its card on /events/, its own page: eleventy/event-page-model.js)
 * → [{ type: "moved", ymd, from, to, anchor } (a date the host moved — ev.seriesOf —: the rule's day of that month and
 * the day it is held), { type: "cancelled", ymd, day, href } (a date that will not take place: its notice page),
 * { type: "skipped", ymd, day } (a month the rule skips — skip_dates — from `from` through `until`, when no moved date
 * stands for it)]. opt: { dates (its dates still to come: events), rule ({ weekday, n } | { weekday, week_of_month }),
 * skip (skip_dates), lang, from / until ("YYYY-MM-DD": the days the skipped months are said for; "" no limit),
 * cancelled (its cancelled dates' notice pages: eleventy/cancelled-pages.js entries) }.
 */
export function seriesNotes(opt = {}) {
  const o = opt || {};
  const lang = o.lang || "en";
  const notes = [];
  const movedFrom = new Set();
  for (const d of o.dates || []) {
    if (!d || !d.seriesOf) continue;
    const from = o.rule ? ruleDay(o.rule, d.startYmd) : null;
    if (from && from !== d.startYmd) {
      movedFrom.add(from);
      notes.push({ type: "moved", ymd: d.startYmd, from: shortDay(from, lang), to: d.shortLabel, anchor: d.anchor });
    }
  }
  for (const p of o.cancelled || []) {
    if (p && p.ev) notes.push({ type: "cancelled", ymd: p.ev.startYmd, day: p.ev.shortLabel, href: p.path });
  }
  for (const s of o.skip || []) {
    const ymd = String(s).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd) || (o.from && ymd < o.from) || movedFrom.has(ymd) || (o.until && ymd > o.until)) continue;
    notes.push({ type: "skipped", ymd, day: shortDay(ymd, lang) });
  }
  return notes.sort((a, b) => a.ymd.localeCompare(b.ymd));
}

const memo = new WeakMap();          // upcoming → [{ key, model }]

/**
 * The /events/ list in a language → {
 *   oneOff   the events of their own still to come, in date order — every event that is not a date of a monthly
 *            series (ev.recurring, or a date the host moved: ev.seriesOf) nor a committee meeting —, each with
 *            `facets`; and, among them, each cancelled one whose day is not over (db.events.cancelled: its notice
 *            page, eleventy/cancelled-pages.js): { …the event, cancelled: true, noticePath }
 *   series   one entry per monthly series with a date to come — the committee meeting ("committee-meeting"),
 *            then each config/site.yml recurring_events series in the order of its next date: { key, title, next
 *            (its next date), dates (every date still to come, its moved dates among them, in date order — each with
 *            its page, `href`), shown (SERIES_DATES_SHOWN), more (how many after them), href (its series' page —
 *            /events/series/<key>/ —, the committee meeting's /meetings/#committee-meeting), every (how often:
 *            "Every second Saturday of the month"), time, notes, facets, tone, expireIso (its last date's) }
 *            notes: what changed about its dates, soonest first — { type: "moved", from, to } (a date the host moved:
 *            the rule's day of that month, the day it is held), { type: "cancelled", day, href } (a date that will
 *            not take place: its notice page), { type: "skipped", day } (a month the rule skips — skip_dates — up
 *            to its last date shown, when no moved date stands for it)
 *   nextUp   the next NEXT_UP events of the page — the one-off events and each series' next date, never a cancelled
 *            one —: the events themselves (their anchor: where their card is), and NEXT_UP_SPARE more that wait
 *            hidden (nextShown: how many show) until one is over (committee.js expire: data-cm-max)
 *   facets   the filter bar's choices: { kinds: [{ key, n }] (KIND_FACETS with a card, n = its cards), langs, modes
 *            (those with a card), cities: [{ slug, name, n }] by name, districts: [{ d, n }] by number }
 * }  upcoming: the page's events still to come (cmEvents | cmCollapseRecurring | where("past", false)); weekly: the
 *    weekly open meetings the page shows (cmWeeklyAll), counted in the filters' choices.
 */
export function eventList(upcoming, db, site, lang = "en", weekly = []) {
  const list = Array.isArray(upcoming) ? upcoming : [];
  const wos = Array.isArray(weekly) ? weekly : [];
  const key = `${lang}|${site?.built ?? ""}|${wos.map((w) => w && w.lang).join(",")}`;
  const hit = (memo.get(list) || []).find((m) => m.key === key && m.db === db);
  if (hit) return hit.model;
  const model = buildList(list, db || {}, site || {}, lang, wos);
  memo.set(list, [...(memo.get(list) || []), { key, db, model }]);
  return model;
}

function buildList(upcoming, db, site, lang, weekly) {
  const built = Date.parse(String(site.built || ""));
  const now = Number.isFinite(built) ? new Date(built) : new Date();
  const todayYmd = now.toISOString().slice(0, 10);
  // (a date's own page and a series' page worked out by the rules of eleventy/event-pages.js eventPagePlan — a date of a
  // series has a page when its anchor is fit for an address; a series has one when its settings entry is enabled and
  // named, its key fit for an address and a date of it still to come (it is in this list) —, never read from the plan:
  // the plan is memoized for the build, and a pagination's `before` may have made it from settings a test changes later)
  const pageOf = (ev) => (EVENT_PAGE_ANCHOR.test(ev.anchor || "") ? eventPagePath(ev, lang) : "");
  const hasHub = (k) => {
    const e = seriesEntry(site, k);
    return !!e && e.enabled !== false && EVENT_PAGE_ANCHOR.test(k) && !!(e.title || e.title_es);
  };
  const withFacets = (ev) => Object.assign(ev, { facets: facetsOf(ev, site) });
  const live = upcoming.filter((ev) => ev && !ev.past);

  // the cancelled events whose day is not over: a one-off's struck-through card, a series date's note
  const notices = EMPTY ? [] : cancelledPages(db.events?.cancelled || [], db.events?.items || [], site, LANGUAGES)
    .filter((p) => p.lang === lang);
  const cancelledOneOff = notices.filter((p) => !seriesKeyOf(p.ev))
    .map((p) => withFacets({ ...p.ev, cancelled: true, noticePath: p.path }));

  // 1) the one-off events (and the cancelled ones), in date order (the page groups them by month: groupBy("monthKey"))
  const oneOff = [...live.filter((ev) => !ev.committee && !ev.recurring && !ev.seriesOf).map(withFacets), ...cancelledOneOff]
    .sort((a, b) => a.startMs - b.startMs || String(a.title).localeCompare(String(b.title)));

  // 2) the series: the committee meeting, then the monthly series of the settings
  const groups = new Map();
  for (const ev of live) {
    const k = ev.committee ? "committee-meeting" : seriesKeyOf(ev);
    if (!k) continue;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(ev);
  }
  const series = [];
  for (const [k, dates] of groups) {
    dates.sort((a, b) => a.startMs - b.startMs || String(a.anchor).localeCompare(String(b.anchor)));
    const next = dates[0];
    const committee = k === "committee-meeting";
    const sn = committee ? null : seriesNext(site, k, lang, db.events?.items || [], { now, n: 1 });
    const rule = committee ? { weekday: site.meeting?.weekday ?? "wednesday", n: site.meeting?.week_of_month ?? 3 } : sn?.rule;
    const skip = committee ? (site.meeting?.skip_dates || []).map(String) : (sn?.rule?.skip || []);
    const shownLast = dates[Math.min(SERIES_DATES_SHOWN, dates.length) - 1];
    const notes = seriesNotes({ dates, rule, skip, lang, from: todayYmd, until: shownLast ? shownLast.startYmd : "",
      cancelled: notices.filter((p) => seriesKeyOf(p.ev) === k) });
    const href = committee ? (lang === "en" ? "" : `/${lang}`) + COMMITTEE_MEETING_PATH
      : hasHub(k) ? seriesPagePath(k, lang) : "";
    series.push({
      key: k, committee, title: committee ? next.title : (sn?.title || next.title), next,
      dates: dates.map((d) => Object.assign(d, { href: pageOf(d) })), shown: SERIES_DATES_SHOWN,
      more: Math.max(0, dates.length - SERIES_DATES_SHOWN), href,
      every: committee ? next.recurrenceDay : (sn?.recurrenceDay || next.recurrenceDay || ""), time: next.timeLabel,
      notes, facets: (next.facets = facetsOf(next, site)), tone: eventTone(next), expireIso: dates[dates.length - 1].expireIso,
    });
  }
  series.sort((a, b) => (b.committee - a.committee) || a.next.startMs - b.next.startMs);

  // 3) "Next up": the one-off events and each series' next date (NEXT_UP_SPARE more, hidden, for when one is over)
  const nextUp = [...oneOff.filter((ev) => !ev.cancelled), ...series.map((s) => s.next)]
    .sort((a, b) => a.startMs - b.startMs || String(a.anchor).localeCompare(String(b.anchor))).slice(0, NEXT_UP + NEXT_UP_SPARE);

  // 4) the filter bar's choices: what the cards hold (the weekly open meetings' too: online meetings, in their language)
  const weeklyFacets = weekly.map((w) => ({ kind: "online", lang: w && w.lang === "es" ? "es" : "en", modes: ["online"], city: "", citySlug: "", district: "" }));
  const cards = [...oneOff.filter((ev) => !ev.cancelled).map((ev) => ev.facets), ...series.map((s) => s.facets), ...weeklyFacets];
  const count = (fn) => cards.filter(fn).length;
  const cities = new Map();
  for (const f of cards) if (f.citySlug) cities.set(f.citySlug, { slug: f.citySlug, name: (cities.get(f.citySlug)?.name || f.city), n: (cities.get(f.citySlug)?.n || 0) + 1 });
  const districts = new Map();
  for (const f of cards) if (f.district) districts.set(f.district, (districts.get(f.district) || 0) + 1);
  const facets = {
    kinds: KIND_FACETS.map((k) => ({ key: k, n: count((f) => f.kind === k) })).filter((k) => k.n),
    langs: LANG_FACETS.filter((l) => count((f) => f.lang === l)),
    modes: MODE_FACETS.filter((m) => count((f) => f.modes.includes(m))),
    cities: [...cities.values()].sort((a, b) => a.name.localeCompare(b.name, lang)),
    districts: [...districts].map(([d, n]) => ({ d, n })).sort((a, b) => Number(a.d) - Number(b.d)),
  };
  return { oneOff, series, nextUp, nextShown: NEXT_UP, facets };
}

/* ------------------------------------------------------------------ */
/*  /status/: the events to look at                                   */
/* ------------------------------------------------------------------ */
export const TENTATIVE_DAYS = 60;
export const TBA_DAYS = 45;
export const STALE_FILE_DAYS = 90;
const DAY_MS = 864e5;
const FILE_DATE = /^(\d{4}-\d{2}-\d{2})/;
// a header line of a content/events file: its key and its value (quoted, or up to a comment)
const LINE = /^([a-z_]+)[ \t]*:[ \t]*(?:"([^"]*)"|'([^']*)'|([^#]*?))[ \t]*(?:#.*)?$/;
const FRONT = /^﻿?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;

/** A content/events file's header lines → { key: value } (the plain one-line values: enough for its dates). */
function headerOf(file) {
  try {
    const head = FRONT.exec(fs.readFileSync(file, "utf8"));
    const out = {};
    for (const line of head ? head[1].split(/\r?\n/) : []) {
      const m = LINE.exec(line);
      if (m && !(m[1] in out)) out[m[1]] = String(m[2] ?? m[3] ?? m[4] ?? "").trim();
    }
    return out;
  } catch {
    return null;
  }
}

/**
 * The events the committee should look at, for /status/ (src/pages/status.njk "Events to check") → { checks: [{ key,
 * days, items: [{ title, ymd, file, href }] }], n } — each check with what it found, in this order:
 *   tentative  an event still marked `tentative: true` TENTATIVE_DAYS (60) days or less before its day — confirm it, or
 *              take the line out;
 *   tba        "Venue to be announced" (extra.location_tba) TBA_DAYS (45) days or less before its day;
 *   nolink     a content/events file of an event still to come with no `url:` (its page has no outside link: the
 *              Area's or the organizers' page, a registration form) — never made up: the committee adds it when there
 *              is one;
 *   summary    an event made from a dated Drive flyer (category flyer) with no summary: its card and page say only
 *              its title — a content/events file with `flyer:` can say what it is;
 *   stale      a content/events file whose event ended more than STALE_FILE_DAYS (90) days ago — the calendar files
 *              no longer list it: the file can be deleted (cleanup).
 * Each item: its title in the page's language (the one the rest of the site shows: events.json i18n.title — a file's
 * title_es / title_en, or the translated one —, else its own; titleLang: the language it is in), its day ("YYYY-MM-DD"), its file ("content/events/
 * <name>.md", "" for a flyer) and its page on the site (in English, "" when it has none: the page gives it its
 * language). dir: the content/events folder (CONTENT_EVENTS: a test's own, as src/_data/db.js).
 */
export function dataChecks(db, site, lang = "en", dir = process.env.CONTENT_EVENTS || path.join("content", "events")) {
  const built = Date.parse(String(site?.built || ""));
  const now = Number.isFinite(built) ? built : Date.now();
  const items = EMPTY ? [] : (db?.events?.items || []).filter((it) => it && it.kind === "event" && it.status !== "gone");
  const plan = eventPagePlan(db?.events?.items, site || {}, LANGUAGES, { cancelled: db?.events?.cancelled });
  const startOf = (it) => Date.parse(String(it.extra?.start || it.date || "").length === 10 ? `${it.extra?.start || it.date}T12:00:00Z` : String(it.extra?.start || it.date || ""));
  // its day in Central time (an evening event is already "tomorrow" in UTC)
  const ymdOf = (it) => {
    const s = String(it.extra?.start || it.date || "");
    const t = s.length > 10 ? Date.parse(s) : NaN;
    return Number.isFinite(t) ? new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date(t)) : s.slice(0, 10);
  };
  const titleOf = (it) => String(it.i18n?.title?.[lang] || it.i18n?.title?.en || it.title || "");
  const pathOf = (it) => {
    const page = Object.values(plan.byAnchor || {}).find((p) => p.en?.ev?.id === it.id)?.en;
    return page ? page.path : "";
  };
  // (titleLang: the language its title is in when that is not the page's — an English title on /es/status/)
  const titleLangOf = (it) => (it.i18n?.title?.[lang] ? lang : it.i18n?.title?.en ? "en" : String(it.lang || "en"));
  const row = (it) => ({ title: titleOf(it), titleLang: titleLangOf(it), ymd: ymdOf(it), file: String(it.extra?.file || ""), href: pathOf(it) });
  const upcoming = items.filter((it) => !it.extra?.past && it.category !== "committee" && it.category !== "recurring" && Number.isFinite(startOf(it)) && startOf(it) + DAY_MS > now);
  const within = (it, days) => startOf(it) - now <= days * DAY_MS;
  const byDay = (a, b) => a.ymd.localeCompare(b.ymd) || a.title.localeCompare(b.title);
  const checks = [
    { key: "tentative", days: TENTATIVE_DAYS, items: upcoming.filter((it) => it.extra?.tentative === true && within(it, TENTATIVE_DAYS)).map(row) },
    { key: "tba", days: TBA_DAYS, items: upcoming.filter((it) => it.extra?.location_tba === true && within(it, TBA_DAYS)).map(row) },
    { key: "nolink", days: 0, items: upcoming.filter((it) => it.category === "manual" && !/^https?:\/\//i.test(String(it.url || ""))).map(row) },
    { key: "summary", days: 0, items: upcoming.filter((it) => it.category === "flyer" && !String(it.summary || "").trim()).map(row) },
  ];
  // the files of the folder whose event is long over (read from the folder itself: events.json keeps only the last few)
  const stale = [];
  let names = [];
  try { names = EMPTY ? [] : fs.readdirSync(dir).filter((n) => /\.md$/i.test(n) && !/^(?:_|readme)/i.test(n)).sort(); } catch { /* no folder */ }
  for (const name of names) {
    const head = headerOf(path.join(dir, name)) || {};
    const last = [head.end, head.start, head.date, FILE_DATE.exec(name)?.[1]].map((v) => String(v || "").slice(0, 10)).find((v) => /^\d{4}-\d{2}-\d{2}$/.test(v));
    if (!last || Date.parse(`${last}T23:59:59-06:00`) + STALE_FILE_DAYS * DAY_MS > now) continue;
    const own = lang === "en" ? head.title_en : head[`title_${lang}`];
    stale.push({ title: own || head.title || name.replace(/\.md$/i, ""), ymd: last, file: `content/events/${name}`, href: "" });
  }
  checks.push({ key: "stale", days: STALE_FILE_DAYS, items: stale });
  for (const c of checks) c.items.sort(byDay);
  return { checks: checks.filter((c) => c.items.length), n: checks.reduce((s, c) => s + c.items.length, 0) };
}

export default function (eleventyConfig) {
  eleventyConfig.addFilter("evList", (upcoming, db, site, lang, weekly) => eventList(upcoming, db, site, lang, weekly));
  eleventyConfig.addFilter("evFacets", (ev, site) => facetAttrs(ev && ev.facets ? ev.facets : facetsOf(ev || {}, site)));
  // (a series' card: its next date's facets — evList gives every series' next date its own)
  eleventyConfig.addFilter("evDataChecks", (db, site, lang) => dataChecks(db, site, lang || "en"));
  // a card's old anchors ("ev-flyer-…", a readable one its day replaced: eleventy/event-redirects.js oldAnchors), so a
  // link made before the event got its readable address still lands on its card
  eleventyConfig.addFilter("evOldAnchors", (it) => oldAnchors(it));
}
