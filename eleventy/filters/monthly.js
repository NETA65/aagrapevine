// /monthly/ — "Carry the message this month": one month model per month for a rolling window
// (the current month in America/Chicago at build time, plus the next 12). Auto-loaded by
// eleventy.config.js. Owned by src/pages/monthly.njk (hub) and src/pages/monthly-month.njk
// (one poster page per month × language).
//
// The rule — the PLAN and what is LIVE NOW:
//   * every month page shows that month's plan: the poster, the issues' themes, the "put it to work"
//     tips, story deadlines, the dates, the weekly open meetings, Book of the Month, and the same month
//     as a message for a group chat or an e-mail (monthMessage);
//   * the current month's page and the hub's "This month" card also show what is live right now
//     (monthNow): which dates are over, the next committee meeting (next month's once this month's is
//     over), the next issue when it is already online, and one-line pointers to the daily quote, What's
//     New, the Bulletin, Instagram, the Grapevine meetings count and the subscription price.
// The Monthly digest (/digest/, community.js) recaps LAST month; everything current lives here — as a
// link when another page is its one home (the Zoom details on /meetings/#committee-meeting, prices on
// /shop/, how to send a story on /contribute/, the quote itself on the home page). No list is on both:
// an issue's highlight stories are the digest's; the toolkit shows the themes and story counts and
// links to /read/.
//
// Everything here is read from data the site already has — nothing is typed in:
//   db.editorial   Grapevine themes per issue (extra.issue_key) until the issue is out, story
//                  deadlines (extra.deadline), La Viña's evergreen suggested topics (extra.evergreen)
//   db.articles    issues[] — the Grapevine issue on the stands (its own theme, once it is out),
//                  La Viña's bimonthly issue; items — the stories (counts, free to read, and the theme
//                  and La Viña's issue when issues[] has moved on to the next one: issueTheme)
//   carry          config/carry.yml — the 10 ways and the "put it to work" tips per GV issue
//   db.events      committee meetings, the monthly recurring events (CityWide Dallas booth …),
//                  workshops and assemblies (content/events, dated Drive flyers, the outside calendars)
//   db.weekly_open the Weekly Open meetings (La Viña's from its extra.starts date)
//   db.shop.botm   Book of the Month offers (starts / ends window)
//   site.meeting   the committee meeting rule (used when a month's meeting is not in events.json:
//                  the current month once its meeting is over, or the 13th month)
//   live extras    db.quote, db.whatsnew, db.announcements, db.instagram, db.meetings, db.shop,
//                  db.audio_project (monthNow)
//
// Globals:   monthlyPages  [{ key: "YYYY-MM", lang }]  → pagination for the per-month pages
//            monthlyKeys   ["YYYY-MM", …]              (13 keys, current month first)
//            monthlyPastPages [{ key, lang, label }]   the 3 months before: redirect stubs to /monthly/
// Filters:   mpMonths(db, carry, site, lang)            → [model, …] for the whole window
//            mpMonth(key, db, carry, site, lang)        → one model
//            mpNow(db, site, lang)                      → the current month's live extras (monthNow)
//            mpIssues(key, db, carry, site, lang)       → the month's issues on the site: story counts and
//                                                         the /read/ links (monthIssueLinks)
//            mpMessage(key, db, carry, site, langs, style) → the month as a WhatsApp / e-mail text
//                                                         (monthMessage; langs ["en"] or ["en", "es"])
//            mpQr(url, label)                           → QR code SVG (qrSvg from community.js)
//            mpGuides(pdfs, lang)                       → the GVR / RLV guides in the Library (repGuides)
// Everything is built once per build and language (the hub and 26 month pages share it).
// Dev/test:  MONTHLY_NOW=2026-12-15 (or an instant: 2026-10-22T06:00:00Z) fixes "now" — the window,
//            the "over" marks, the next committee meeting and the live extras.

// (community.js imports this file too: the cycle is safe, both only call each other's functions.)
import { qrSvg, issueLabel, issueInSentence } from "./community.js";
import { chicagoDayEndMs, gvMeetings, announcementList } from "./committee.js";
import { shopFromMonthly, money } from "./shop.js";
import { groupIssues } from "./read.js";

// Helpers handed over by eleventy.config.js (translateKey …); the fallback keeps the module usable
// from a plain `node` script too (as report.js).
let H = { translateKey: (k) => k };

const TZ = "America/Chicago";
const LOC = { en: "en-US", es: "es-US" };
const WINDOW = 13;
const PAST_MONTHS = 3;
const WD = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };

// 12 poster designs keyed by calendar month; 6 structurally different layouts, each used twice
// with its own seasonal palette and motif (src/assets/css/areas/monthly.css).
export const DESIGNS = [
  { id: "frost", layout: "editorial" },   // Jan — winter frost, snowflakes
  { id: "rose", layout: "ticket" },       // Feb — rose & wine, a ticket with a coupon corner
  { id: "sprout", layout: "split" },      // Mar — spring green, calendar strip
  { id: "rain", layout: "cork" },         // Apr — spring showers, pinned notes
  { id: "bloom", layout: "cover" },       // May — flowers, magazine cover
  { id: "notebook", layout: "notebook" }, // Jun — ruled notebook page (a nod to the member's poster)
  { id: "sun", layout: "editorial" },     // Jul — summer sun
  { id: "shore", layout: "ticket" },      // Aug — late-summer sea & sand
  { id: "chalk", layout: "notebook" },    // Sep — chalkboard, back to school
  { id: "autumn", layout: "cork" },       // Oct — autumn corkboard, falling leaves
  { id: "harvest", layout: "split" },     // Nov — harvest plum & gold
  { id: "holiday", layout: "cover" },     // Dec — winter holidays, pine & stars
];

/* ------------------------------------------------------------------ */
/*  Date helpers (Central time)                                        */
/* ------------------------------------------------------------------ */
const pad = (n) => String(n).padStart(2, "0");
const ymdFmt = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });

/** "YYYY-MM-DD" in Central time; a date-only string is returned as is. */
export function chicagoYmd(v) {
  if (!v) return "";
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)) return v;
  const d = v instanceof Date ? v : new Date(v);
  return isNaN(d) ? "" : ymdFmt.format(d);
}
export function nowDate() {
  const fixed = process.env.MONTHLY_NOW;
  if (fixed && /^\d{4}-\d{2}-\d{2}/.test(fixed)) return new Date(fixed.length === 10 ? fixed + "T12:00:00-05:00" : fixed);
  return new Date();
}
export function addMonths(key, n) {
  const [y, m] = key.split("-").map(Number);
  const i = y * 12 + (m - 1) + n;
  return `${Math.floor(i / 12)}-${pad((i % 12) + 1)}`;
}
const lastDay = (key) => { const [y, m] = key.split("-").map(Number); return new Date(Date.UTC(y, m, 0)).getUTCDate(); };
/** 13 month keys: the current Central-time month first. */
export function windowKeys(now = nowDate(), n = WINDOW) {
  const first = chicagoYmd(now).slice(0, 7);
  return Array.from({ length: n }, (_, i) => addMonths(first, i));
}

const utcNoon = (ymd) => new Date(ymd + "T12:00:00Z");
function monthName(key, lang, style = "long") {
  const [y, m] = key.split("-").map(Number);
  return new Intl.DateTimeFormat(LOC[lang] || "en-US", { month: style, timeZone: "UTC" }).format(new Date(Date.UTC(y, m - 1, 15)));
}
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
/** "May 2027" / "mayo de 2027" */
export function monthLabel(key, lang) {
  const y = key.slice(0, 4);
  return lang === "es" ? `${monthName(key, "es")} de ${y}` : `${monthName(key, "en")} ${y}`;
}
/** "Oct 1" / "1 de octubre" (+ year when it is not `year`) */
export function shortDate(ymd, lang, year) {
  if (!ymd) return "";
  const [y, m, d] = ymd.split("-").map(Number);
  const key = `${y}-${pad(m)}`;
  const withYear = year && String(y) !== String(year);
  if (lang === "es") return `${d} de ${monthName(key, "es")}${withYear ? ` de ${y}` : ""}`;
  return `${monthName(key, "en", "short")} ${d}${withYear ? `, ${y}` : ""}`;
}
/** "Jun 25–27" / "25–27 de junio" (same month), else "Jun 30–Jul 2" / "30 de junio–2 de julio" */
function dayRange(a, b, lang) {
  if (a.slice(0, 7) !== b.slice(0, 7)) return `${shortDate(a, lang)}–${shortDate(b, lang)}`;
  const d1 = Number(a.slice(8)), d2 = Number(b.slice(8));
  return lang === "es" ? `${d1}–${d2} de ${monthName(a.slice(0, 7), "es")}` : `${monthName(a.slice(0, 7), "en", "short")} ${d1}–${d2}`;
}
/** Calendar chip for a Central-time date: { day: "21", mon: "Oct", wd: "Wed" } */
function chip(ymd, lang) {
  const d = utcNoon(ymd);
  const loc = LOC[lang] || "en-US";
  const f = (o) => new Intl.DateTimeFormat(loc, { ...o, timeZone: "UTC" }).format(d).replace(/\.$/, "");
  return { day: String(d.getUTCDate()), mon: cap(f({ month: "short" })), wd: cap(f({ weekday: "short" })), ymd };
}
/** "Wednesday, October 21" / "miércoles 21 de octubre" */
function longDay(ymd, lang) {
  const d = utcNoon(ymd);
  if (lang === "es") {
    const f = (o) => new Intl.DateTimeFormat("es-US", { ...o, timeZone: "UTC" }).format(d);
    return `${f({ weekday: "long" })} ${d.getUTCDate()} de ${f({ month: "long" })}`;
  }
  return new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" }).format(d);
}
/** Central-time clock parts of an instant: { h, mi } */
function chicagoClock(v) {
  const d = new Date(v);
  if (isNaN(d)) return null;
  const p = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit", hourCycle: "h23" }).formatToParts(d);
  return { h: Number(p.find((x) => x.type === "hour").value), mi: Number(p.find((x) => x.type === "minute").value) };
}
/** "5–8 PM" / "5–8 p. m." / "7 PM" (Central time; the zone word is added by the template) */
export function timeRange(start, end, lang) {
  const a = chicagoClock(start);
  if (!a) return "";
  const b = end ? chicagoClock(end) : null;
  const mer = (h) => (lang === "es" ? (h < 12 ? "a. m." : "p. m.") : h < 12 ? "AM" : "PM");
  const hm = (c) => `${c.h % 12 || 12}${c.mi ? ":" + pad(c.mi) : ""}`;
  if (!b || (b.h === a.h && b.mi === a.mi)) return `${hm(a)} ${mer(a.h)}`;
  if ((a.h < 12) === (b.h < 12)) return `${hm(a)}–${hm(b)} ${mer(b.h)}`;
  return `${hm(a)} ${mer(a.h)}–${hm(b)} ${mer(b.h)}`;
}

/* ------------------------------------------------------------------ */
/*  Committee meeting rule (fallback when events.json has no date)     */
/* ------------------------------------------------------------------ */
function nthWeekday(y, m0, weekday, n) {
  if (n === -1) {
    const last = new Date(Date.UTC(y, m0 + 1, 0));
    return last.getUTCDate() - ((last.getUTCDay() - weekday + 7) % 7);
  }
  const first = new Date(Date.UTC(y, m0, 1)).getUTCDay();
  const day = 1 + ((weekday - first + 7) % 7) + (n - 1) * 7;
  return day <= new Date(Date.UTC(y, m0 + 1, 0)).getUTCDate() ? day : null;
}
function chicagoInstant(ymd, hhmm) {
  const [h, mi] = String(hhmm || "19:00").split(":").map(Number);
  const [y, m, d] = ymd.split("-").map(Number);
  const guess = new Date(Date.UTC(y, m - 1, d, h, mi || 0));
  const tz = new Intl.DateTimeFormat("en-US", { timeZone: TZ, timeZoneName: "shortOffset" }).formatToParts(guess).find((p) => p.type === "timeZoneName")?.value || "GMT-6";
  const off = Number((tz.match(/GMT([+-]\d+)/) || [0, -6])[1]);
  return new Date(guess.getTime() - off * 3600e3).toISOString();
}
export function meetingByRule(key, meeting = {}) {
  const wd = WD[String(meeting.weekday || "wednesday").toLowerCase()] ?? 3;
  const n = Number(meeting.week_of_month || 3);
  const [y, m] = key.split("-").map(Number);
  const d = nthWeekday(y, m - 1, wd, n);
  if (!d) return null;
  const ymd = `${key}-${pad(d)}`;
  const skip = new Set((meeting.skip_dates || []).map((s) => (s instanceof Date ? s.toISOString().slice(0, 10) : String(s))));
  if (skip.has(ymd)) return null;
  return { ymd, start: chicagoInstant(ymd, meeting.start || "19:00"), end: chicagoInstant(ymd, meeting.end || "20:00") };
}

/* ------------------------------------------------------------------ */
/*  Text helpers                                                       */
/* ------------------------------------------------------------------ */
const tr = (item, field, lang) => {
  if (!item) return "";
  const i = item.i18n && item.i18n[field];
  if (i && typeof i[lang] === "string" && i[lang].trim()) return i[lang];
  if (i && typeof i.en === "string" && i.en.trim()) return i.en;
  return item[field] || (item.extra && item.extra[field]) || "";
};
const pair = (p, lang) => (p ? p[lang] || p.en || p.es || "" : "");
const clean = (s) => String(s ?? "").replace(/\s+/g, " ").trim();
const isYmd = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
/** ms → ISO instant ("" when unknown): the `overAt` of a date row, a deadline, an offer */
const iso = (ms) => (Number.isFinite(ms) ? new Date(ms).toISOString() : "");
/** A poster hook: the first question of the summary (short), else its first sentence. */
export function hook(summary, max = 110) {
  const s = String(summary || "").replace(/\s+/g, " ").trim();
  if (!s) return "";
  const parts = s.match(/[^.?!]+[.?!]+/g) || [s];
  const q = parts.map((p) => p.trim()).find((p) => p.endsWith("?") && p.length <= max);
  const pick = q || parts[0].trim();
  return pick.length > max ? pick.slice(0, max).replace(/\s+\S*$/, "") + "…" : pick;
}
const slug = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

/* ------------------------------------------------------------------ */
/*  The month model                                                    */
/* ------------------------------------------------------------------ */
const DAY = 864e5;

function eventDays(ev) {
  const ex = ev.extra || {};
  const start = chicagoYmd(ex.start || ev.date);
  let end = ex.end ? chicagoYmd(ex.end) : start;
  // An end at midnight (timed events that finish at 00:00) belongs to the day before; keep ≥ start.
  if (end && end > start && typeof ex.end === "string" && !/^\d{4}-\d{2}-\d{2}$/.test(ex.end)) {
    const c = chicagoClock(ex.end);
    if (c && c.h === 0 && c.mi === 0) end = chicagoYmd(new Date(Date.parse(ex.end) - 1));
  }
  if (!end || end < start) end = start;
  return { start, end };
}

/** When an event is over (ms): a timed event at its end (without one, 6 hours after it starts); an
 *  all-day or date-only event — or one whose end is a date — at midnight Central after its last day.
 *  The district report's rule too (report.js upcomingEvents). */
function eventOverMs(e) {
  const ex = e.extra || {};
  const s = ex.start || e.date;
  if (!s) return NaN;
  if (ex.end && !isYmd(ex.end)) return Date.parse(ex.end);
  if (ex.end || ex.all_day || isYmd(s)) return chicagoDayEndMs(eventDays(e).end);
  return Date.parse(s) + 6 * 3600e3;
}

/** The month a row is shown in: its 1st (a date that began the month before shows its chip on the 1st),
 *  its year (dates of another year say it), the time-zone word, and "now" for the `past` marks. */
const monthCtx = (key, L, now) => ({ first: `${key}-01`, year: key.slice(0, 4), zone: L === "es" ? "(hora del Centro)" : "Central", nowMs: now.getTime() });

/**
 * One row of a month's dates — the page's Dates card, the poster, the hub's chips and the message:
 * the fields the poster always had (chip, day, range, time + zone, city, tentative …) plus
 *   overAt    when it is over, as an ISO instant (eventOverMs) — the browser marks it "Over" then
 *             (src/assets/js/monthly.js); past = overAt ≤ now (an instant, not a day)
 *   href      where its title links: the committee meeting → /meetings/#committee-meeting (the one home
 *             of its Zoom details); anything else → its own page (url) or /events/. A monthly series
 *             keeps its own link: its later dates are folded on /events/, where an anchor could land on
 *             a hidden card. external = another site.
 *   category  the data's category (eventTone keeps the Grapevine / La Viña calendars' colours)
 * extra: { kind: "committee" | "recurring" | "event", … }
 */
function dateRow(e, L, ctx, extra = {}) {
  const d = eventDays(e);
  const ex = e.extra || {};
  const timed = !ex.all_day && ex.start && !isYmd(ex.start);
  const shownDay = d.start < ctx.first ? ctx.first : d.start;
  const overAt = iso(eventOverMs(e));
  const href = extra.kind === "committee" ? "/meetings/#committee-meeting" : e.url || "/events/";
  return {
    id: e.id, title: tr(e, "title", L), url: e.url || "", href, external: /^https?:/.test(href), category: e.category || "",
    ymd: d.start, endYmd: d.end, chip: chip(shownDay, L), dayLabel: shortDate(shownDay, L, ctx.year), day: longDay(d.start, L),
    endDay: d.end !== d.start ? longDay(d.end, L) : "",
    range: d.end !== d.start ? dayRange(d.start, d.end, L) : "",
    time: timed ? `${timeRange(ex.start, ex.end, L)}` : "", zone: timed ? ctx.zone : "",
    city: ex.city || "", online: !!ex.online || /zoom/i.test(ex.location || ""),
    tentative: !!ex.tentative, overAt, past: !!overAt && Date.parse(overAt) <= ctx.nowMs, ...extra,
  };
}

/** A month's committee meeting as a date row: its events.json record, else the site.meeting rule
 *  (events.json drops a meeting once it is over; skip_dates are honoured) — null when there is none. */
function committeeRow(events, key, site, L, ctx) {
  let ev = events.find((e) => e.id && String(e.id).startsWith(`ev:committee:${key}-`));
  if (!ev) {
    const r = meetingByRule(key, site.meeting || {});
    if (r) ev = { id: `ev:committee:${r.ymd}`, kind: "event", url: "/meetings/", title: "", extra: { start: r.start, end: r.end, location: "Zoom", online: true } };
  }
  if (!ev) return null;
  const row = dateRow(ev, L, ctx, { kind: "committee" });
  row.title = "";
  row.platform = (site.meeting && site.meeting.platform) || "Zoom";
  return row;
}

/* The magazines' stories on the site (db.articles items): what the issue counts, the La Viña fallback
   and the theme fallback read. The publication as the digest reads it (community.js monthIssues). */
const storyPub = (a) => (a && a.extra && a.extra.publication) || (a && a.category) || "";
const storiesOf = (db) => ((db.articles && db.articles.items) || [])
  .filter((a) => a && a.kind === "article" && a.status !== "gone" && a.extra && a.extra.issue_key);

/* An issue's theme and where it came from ("issue" | "stories" | "calendar"): see issueTheme. */
function themeOf(db, pub, key, L) {
  const meta = ((db.articles && db.articles.issues) || []).find((i) => i && i.publication === pub && i.key === key) || null;
  const own = meta ? clean(tr(meta, "theme", L)) : "";
  if (own) return { text: own, themes: [own], from: "issue", machine: L === "es" && (meta.machine || []).includes("es") };
  const first = storiesOf(db).find((a) => storyPub(a) === pub && a.extra.issue_key === key);
  const told = first ? clean((first.i18n && first.i18n.issue_theme && first.i18n.issue_theme[L]) || first.extra.issue_theme) : "";
  if (told) return { text: told, themes: [told], from: "stories", machine: L === "es" && (first.machine || []).includes("es") };
  if (pub === "gv") {
    const themed = ((db.editorial && db.editorial.items) || []).filter((i) => i && i.extra && i.extra.publication === "gv" && i.extra.issue_key === key);
    const themes = themed.map((i) => clean(tr(i, "title", L))).filter(Boolean);
    if (themes.length) return { text: themes.join(" / "), themes, from: "calendar", machine: L === "es" && themed.some((i) => (i.machine || []).includes("es")) };
  }
  return { text: "", themes: [], from: "", machine: false };
}

/**
 * A magazine issue's theme — ONE name everywhere (the month pages and posters, the district report, the
 * monthly digest and its e-mail): the theme the issue itself carries once it is out (articles.json
 * issues[]: i18n.theme[lang], else i18n.theme.en, else theme); else the one its stories on the site carry
 * (the first story's i18n.issue_theme[lang], else extra.issue_theme — so a month keeps its theme after
 * issues[] has moved on to the next issue late in the month); else, for Grapevine, the editorial
 * calendar's call for stories (its titles for that issue_key, joined " / "); else "".
 * scripts/notify/send_digest.py issue_theme() is the same rule (tests/test_digest_parity.py).
 */
export function issueTheme(db, pub, key, lang) {
  return themeOf(db || {}, pub, key, lang === "es" ? "es" : "en").text;
}

/* La Viña's bimonthly issue that covers a month: the synced issue (issues[], key = the month or the one
   before), else — once issues[] has moved on to the next issue late in the month — the issue its stories
   on the site belong to (the same two keys): label from the stories (i18n.issue_label, else the rule),
   its official page from extra.issue_url, no cover. */
function lvIssueOf(db, key, L) {
  const meta = ((db.articles && db.articles.issues) || []).find((i) => i && i.publication === "lv" && i.key && (i.key === key || addMonths(i.key, 1) === key)) || null;
  if (meta) return { key: meta.key, theme: issueTheme(db, "lv", meta.key, L), label: tr(meta, "label", L), url: meta.url || "", cover: meta.cover || "" };
  const lvStories = storiesOf(db).filter((a) => storyPub(a) === "lv");
  const k = [key, addMonths(key, -1)].find((x) => lvStories.some((a) => a.extra.issue_key === x));
  if (!k) return null;
  const first = lvStories.find((a) => a.extra.issue_key === k);
  const label = clean(first.i18n && first.i18n.issue_label && first.i18n.issue_label[L]) || issueLabel(first.extra.issue_label || "", L);
  return { key: k, theme: issueTheme(db, "lv", k, L), label, url: first.extra.issue_url || "", cover: "" };
}

/**
 * One month's model (the month's PLAN: every month page, the posters, the district report).
 * @param {string} key   "YYYY-MM"
 * @param {object} db    { editorial, articles, events, weekly_open, shop }
 * @param {object} carry the `carry` global (config/carry.yml)
 * @param {object} site  the `site` global (meeting, links, url)
 * @param {string} lang  "en" | "es"
 * @param {Date}   now
 */
export function monthModel(key, db = {}, carry = {}, site = {}, lang = "en", now = nowDate()) {
  const L = lang === "es" ? "es" : "en";
  const year = key.slice(0, 4);
  const first = `${key}-01`;
  const last = `${key}-${pad(lastDay(key))}`;
  const nextFirst = `${addMonths(key, 1)}-01`;
  const today = chicagoYmd(now);
  const mNum = Number(key.slice(5, 7));
  const design = DESIGNS[mNum - 1];
  const editorial = (db.editorial && db.editorial.items) || [];
  const gvEd = editorial.filter((i) => i && i.extra && i.extra.publication === "gv");
  const issues = (db.articles && db.articles.issues) || [];

  /* Grapevine issue on the stands. Its theme is ONE name everywhere (this page, the month pages, the
     district report, the monthly digest, Read and Home): issueTheme — the theme the issue itself
     carries once it is out (the synced issue, "Loneliness"), kept after the next issue is synced from
     its stories; before that, the editorial calendar's call for stories ("Dealing with Loneliness"). */
  const gvIssue = issues.find((i) => i && i.publication === "gv" && i.key === key) || null;
  const gvStory = storiesOf(db).find((a) => storyPub(a) === "gv" && a.extra.issue_key === key) || null;
  const themed = gvEd.filter((i) => i.extra.issue_key === key);
  const gvTheme = themeOf(db, "gv", key, L);
  const gv = gvTheme.text ? {
    key, theme: gvTheme.text, themes: gvTheme.themes, label: monthLabel(key, L),
    summary: gvTheme.from === "issue" ? tr(gvIssue, "description", L) : tr(themed[0], "summary", L),
    url: (gvIssue && gvIssue.url) || (gvStory && gvStory.extra.issue_url) || "", cover: gvIssue ? gvIssue.cover || "" : "",
    machine: gvTheme.machine,
  } : null;

  /* La Viña's bimonthly issue that covers this month (lvIssueOf) */
  const lv = lvIssueOf(db, key, L);

  /* "Put it to work" tips for this month's Grapevine issue */
  const wayById = carry.wayById || {};
  const tips = ((carry.tips || {})[key] || []).filter((t) => wayById[t.way]).map((t) => ({
    way: t.way, icon: wayById[t.way].icon || "circle", title: pair(wayById[t.way].title, L), text: pair(t.text, L),
  }));

  /* Story deadlines from the 1st of this month through the 1st of next month (still open); overAt =
     midnight Central after the deadline (the browser marks a passed one on the hub) */
  const deadlines = gvEd
    .filter((i) => i.extra.deadline && i.extra.deadline >= first && i.extra.deadline <= nextFirst && i.extra.deadline >= today)
    .sort((a, b) => a.extra.deadline.localeCompare(b.extra.deadline) || String(a.title).localeCompare(String(b.title)))
    .map((i) => ({
      id: i.id, theme: tr(i, "title", L), themeEn: i.title, hook: L === "en" ? hook(i.summary) : "",
      summary: tr(i, "summary", L),
      issueKey: i.extra.issue_key, issueLabel: i.extra.issue_key ? monthLabel(i.extra.issue_key, L) : tr(i, "issue_label", L),
      due: i.extra.deadline, dueLabel: shortDate(i.extra.deadline, L, year), dueLong: shortDate(i.extra.deadline, L, "0"),
      overAt: iso(chicagoDayEndMs(i.extra.deadline)),
      submitUrl: i.extra.submit_url || "", guidelinesUrl: i.extra.guidelines_url || "",
      machine: L === "es" && (i.machine || []).includes("es"),
    }));

  /* La Viña suggested topics — 3, rotating by month */
  const lvTopics = editorial.filter((i) => i && i.extra && i.extra.publication === "lv" && i.extra.evergreen)
    .sort((a, b) => String(a.id).localeCompare(String(b.id)));
  const topics = [];
  if (lvTopics.length) {
    const idx = Number(year) * 12 + mNum;
    const n = Math.min(3, lvTopics.length);
    for (let i = 0; i < n; i++) {
      const it = lvTopics[(idx * 3 + i) % lvTopics.length];
      if (!topics.includes(it)) topics.push(it);
    }
  }
  const lvTopicList = topics.map((i) => ({ id: i.id, es: tr(i, "title", "es"), text: tr(i, "title", L) }));

  /* Book of the Month offers whose window overlaps the month; overAt = midnight Central after its last day */
  const botm = (((db.shop && db.shop.botm) || []).filter((b) => b && b.ends && (!b.starts || b.starts <= last) && b.ends >= first))
    .sort((a, b) => (a.pub === (L === "es" ? "lv" : "gv") ? -1 : 1) - (b.pub === (L === "es" ? "lv" : "gv") ? -1 : 1))
    .map((b) => ({
      // The book's own title (a Grapevine book is in English, a La Viña book in Spanish), never a translation.
      id: b.id, pub: b.pub, title: b.title || tr(b, "title", L), lang: b.lang || (b.pub === "lv" ? "es" : "en"), discount: b.discount_pct || null,
      ends: b.ends, endsLabel: shortDate(b.ends, L, year), starts: b.starts, past: b.ends < today, overAt: iso(chicagoDayEndMs(b.ends)),
    }));

  /* The shared offer when every book has the same discount and end date (the poster says it once) */
  const botmOffer = botm.length > 1 && botm.every((b) => b.discount === botm[0].discount && b.ends === botm[0].ends)
    ? { discount: botm[0].discount, endsLabel: botm[0].endsLabel } : null;

  /* Dates: committee meeting, the monthly recurring events, other events — every event in events.json that
     is not gone: content/events, dated Drive flyers, the outside calendars (the NETA 65 workshop feed, the
     Grapevine / La Viña calendars) … */
  const events = ((db.events && db.events.items) || []).filter((e) => e && e.kind === "event" && e.status !== "gone");
  const inMonth = (e) => { const d = eventDays(e); return d.start && d.start <= last && d.end >= first; };
  const ctx = monthCtx(key, L, now);
  const committee = committeeRow(events, key, site, L, ctx);
  /* The recurring series (config/site.yml recurring_events:) — events.json lists only the next
     `months_ahead` dates, so a later month's date is worked out from the same rule (like the
     committee meeting from site.meeting), with the series' own title and repeat line. */
  const recEvents = events.filter((e) => e.extra && e.extra.recurring && e.extra.series);
  const recIn = recEvents.filter(inMonth);
  for (const spec of Array.isArray(site.recurring_events) ? site.recurring_events : []) {
    if (!spec || !spec.key || spec.enabled === false) continue;
    const series = recEvents.filter((e) => e.extra.series === spec.key);
    const lastListed = series.reduce((mx, e) => (eventDays(e).start > mx ? eventDays(e).start : mx), "");
    if (!series.length || series.some(inMonth) || lastListed >= first) continue;
    const r = meetingByRule(key, { week_of_month: spec.week_of_month, weekday: spec.weekday, start: spec.start, end: spec.end, skip_dates: spec.skip_dates || [] });
    if (!r) continue;
    const tpl = series[series.length - 1];
    recIn.push({ ...tpl, id: `ev:recurring:${spec.key}:${r.ymd}`, date: r.start, extra: { ...tpl.extra, start: r.start, end: r.end } });
  }
  const recurring = recIn
    .sort((a, b) => eventDays(a).start.localeCompare(eventDays(b).start))
    .map((e) => dateRow(e, L, ctx, { kind: "recurring", series: e.extra.series, label: tr(e, "recurrence_label", L) }));
  const other = events.filter((e) => !(e.extra && e.extra.recurring) && !String(e.id).startsWith("ev:committee:") && inMonth(e))
    .sort((a, b) => eventDays(a).start.localeCompare(eventDays(b).start))
    .map((e) => dateRow(e, L, ctx, { kind: "event" }));
  const dates = [committee, ...recurring, ...other].filter(Boolean).sort((a, b) => a.chip.ymd.localeCompare(b.chip.ymd));

  /* Weekly open meetings (La Viña's only from its start date) */
  const weekly = ((db.weekly_open && db.weekly_open.items) || []).filter((w) => {
    if (!w || w.status === "gone") return false;
    const starts = w.extra && w.extra.starts;
    return !starts || starts <= last;
  }).map((w) => {
    const starts = (w.extra && w.extra.starts) || "";
    return {
      id: w.id, pub: w.source === "lavina" ? "lv" : "gv", title: tr(w, "title", L), when: tr(w, "when", L) || tr(w, "day", L),
      startsLabel: starts && starts >= first ? shortDate(starts, L) : "", new: !!(starts && starts >= first && starts <= last),
    };
  }).sort((a, b) => (a.pub === (L === "es" ? "lv" : "gv") ? -1 : 1) - (b.pub === (L === "es" ? "lv" : "gv") ? -1 : 1));

  /* Mini calendar (split layout): leading blanks + days with marks */
  const [yy, mm] = key.split("-").map(Number);
  const offset = new Date(Date.UTC(yy, mm - 1, 1)).getUTCDay();
  const marks = {};
  const mark = (ymd, type) => { if (ymd && ymd.startsWith(key)) { const d = Number(ymd.slice(8)); (marks[d] = marks[d] || []).includes(type) || marks[d].push(type); } };
  for (const d of dates) {
    for (let c = d.chip.ymd; c <= (d.endYmd || d.chip.ymd) && c <= last; c = chicagoYmd(new Date(utcNoon(c).getTime() + 864e5))) mark(c, d.kind);
  }
  for (const d of deadlines) mark(d.due, "deadline");
  const weekdays = Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(LOC[L], { weekday: "narrow", timeZone: "UTC" }).format(new Date(Date.UTC(2026, 1, 1 + i))));
  const calendar = { offset, days: lastDay(key), marks, weekdays };

  /* Density: how much the poster holds (the CSS tightens type for busy months) */
  const load = deadlines.length * 3 + Math.min(tips.length, 3) * 2 + botm.length * 1.5 + dates.length * 1.2 + weekly.length + (L === "es" ? 2 : 0);
  const density = load > 20 ? "dense" : load > 15 ? "snug" : "roomy";

  const path = `/monthly/${key}/`;
  const url = (L === "es" ? "/es" : "") + path;
  return {
    key, lang: L, year, month: mNum, first, last,
    name: cap(monthName(key, L)), monthName: monthName(key, L), label: monthLabel(key, L), title: cap(monthLabel(key, L)),
    design: design.id, layout: design.layout, density,
    isCurrent: key === today.slice(0, 7),
    gv, lv, tips, deadlines, lvTopics: lvTopicList, botm, botmOffer,
    committee, recurring, events: other, dates, weekly, calendar,
    url, absUrl: String(site.url || "").replace(/\/$/, "") + url,
    prev: addMonths(key, -1), next: addMonths(key, 1),
    fileName: `neta65-grapevine-${key}-${L}.png`,
    slug: slug(key),
  };
}

/* ------------------------------------------------------------------ */
/*  This month, live (the hub's "This month" card, the current page)   */
/* ------------------------------------------------------------------ */
/** "2026-10-05" minus n calendar days */
const ymdMinus = (ymd, n) => { const [y, m, d] = ymd.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d - n)).toISOString().slice(0, 10); };
/** A news date as ms (a date-only value at noon UTC, like the rest of the site) */
const msOf = (v) => (isYmd(v) ? Date.parse(v + "T12:00:00Z") : Date.parse(v));

/**
 * What is live in the current Central-time month — the hub's "This month" card and the current month's
 * page show it, never a later month (MONTHLY_NOW moves it, like the window):
 *   key            the current month, "YYYY-MM"
 *   nextCommittee  the next committee meeting that is not over: this month's (its events.json record,
 *                  else the rule), then next month's — { ymd, day, dayLabel, time, zone, platform, overAt,
 *                  thisMonth } or null. (Not src/_data/meeting.js: that one ignores MONTHLY_NOW.)
 *   outNext        an issue already online before its month (the district report's rule: articles.json
 *                  issues[] newer than this month's Grapevine key / than the La Viña issue covering this
 *                  month) → [{ pub, theme, issue (inside a sentence), monthKey, monthLabel, monthUrl (its
 *                  toolkit, "" outside the window) }], the page language's magazine first
 *   quote          true when the home page shows a daily quote (homeDailyQuotes: of the last 2 days, with
 *                  its text and link) — the toolkit points there, never repeats it
 *   instagram      [{ username, url }] the page language's magazine first
 *   news           { n: What's New entries since the 1st (their news date up to now + 1 day), since, sinceLabel }
 *   bulletin       { n: bulletin posts not over yet (announcementList — /bulletin/'s list), top: { title, href }:
 *                  the newest of them by its day (its date, or its `publish` day when later — never simply
 *                  the first on /bulletin/, where pinned posts come first) }
 *   subsFrom       the lowest subscription price (shopFromMonthly) or null
 *   gvm            { inArea, nearby } Grapevine meetings (gvMeetings) or null when there are none in our Area
 *   audio          { gv, lv } the phone story lines ({ phone, tel } or null) — standing information: the
 *                  message of every month gives them
 */
export function monthNow(db = {}, site = {}, lang = "en", now = nowDate()) {
  const L = lang === "es" ? "es" : "en";
  const nowMs = now.getTime();
  const today = chicagoYmd(now);
  const key = today.slice(0, 7);
  const first = `${key}-01`;
  const events = ((db.events && db.events.items) || []).filter((e) => e && e.kind === "event" && e.status !== "gone");

  let nextCommittee = null;
  for (const k of [key, addMonths(key, 1)]) {
    const row = committeeRow(events, k, site, L, monthCtx(k, L, now));
    if (!row || row.past) continue;
    nextCommittee = { ymd: row.ymd, day: row.day, dayLabel: row.dayLabel, time: row.time, zone: row.zone, platform: row.platform, overAt: row.overAt, thisMonth: row.ymd.startsWith(key) };
    break;
  }

  const issues = (db.articles && db.articles.issues) || [];
  const keys = windowKeys(now);
  const lv = lvIssueOf(db, key, L);
  const newer = (pub, after) => issues.filter((i) => i && i.publication === pub && i.key && i.key > after).sort((a, b) => a.key.localeCompare(b.key))[0];
  const outNext = [];
  for (const pub of L === "es" ? ["lv", "gv"] : ["gv", "lv"]) {
    const i = pub === "gv" ? newer("gv", key) : lv ? newer("lv", lv.key) : null;
    const theme = i ? clean(tr(i, "theme", L)) : "";
    if (!theme) continue;
    const own = clean(i.i18n && i.i18n.label && i.i18n.label[L]);
    const label = own || (pub === "gv" ? monthLabel(i.key, L) : clean(i.label) || i.key);
    outNext.push({ pub, theme, issue: issueInSentence(label, L), monthKey: i.key, monthLabel: monthLabel(i.key, L), monthUrl: keys.includes(i.key) ? `/monthly/${i.key}/` : "" });
  }

  const since2 = ymdMinus(today, 2);
  const quote = ((db.quote && db.quote.items) || []).some((q) => q && (q.pub === "gv" || q.pub === "lv") && clean(q.text)
    && /^https?:\/\//.test(String(q.url || "")) && isYmd(String(q.date || "").slice(0, 10)) && String(q.date).slice(0, 10) >= since2);

  const profiles = (db.instagram && db.instagram.profiles) || {};
  const instagram = (L === "es" ? ["lv", "gv"] : ["gv", "lv"]).map((k) => profiles[k]).filter((p) => p && p.username)
    .map((p) => { const u = String(p.username).replace(/^@/, ""); return { username: u, url: p.url || `https://www.instagram.com/${u}/` }; });

  const n = ((db.whatsnew && db.whatsnew.items) || []).filter((i) => i && i.status !== "gone" && i.wn_date
    && chicagoYmd(i.wn_date) >= first && msOf(i.wn_date) <= nowMs + DAY).length;

  const posts = announcementList((db.announcements && db.announcements.items) || [], now);
  // "the newest:" names the newest post by its own day — its date (else when it was first seen), or its
  // `publish` day when that is later (a scheduled post appears that morning) — not the first on /bulletin/,
  // where pinned posts come first. The same day: /bulletin/'s order (pinned first, then newest).
  const postDay = (p) => {
    const d = chicagoYmd(p.date || p.first_seen || "");
    const pub = String((p.extra && p.extra.publish) || "").slice(0, 10);
    return isYmd(pub) && pub > d ? pub : d;
  };
  const top = posts.reduce((best, p) => (!best || postDay(p) > postDay(best) ? p : best), null);

  const from = shopFromMonthly(db.shop);
  const g = gvMeetings(db.meetings, L, site);
  const ap = db.audio_project || {};
  const line = (d) => (d && d.phone && d.tel ? { phone: String(d.phone), tel: String(d.tel) } : null);
  return {
    key, nextCommittee, outNext, quote, instagram,
    news: { n, since: first, sinceLabel: shortDate(first, L) },
    bulletin: { n: posts.length, top: top ? { title: clean(tr(top, "title", L)), href: `/bulletin/#${top._anchor}` } : null },
    subsFrom: Number.isFinite(from) && from > 0 ? from : null,
    gvm: g.inArea ? { inArea: g.inArea, nearby: g.nearby } : null,
    audio: { gv: line(ap.gv), lv: line(ap.lv) },
  };
}

/**
 * A month's magazine issues that have stories on the site (db.articles items): the page language's
 * magazine first → [{ pub, isLv, name, label, theme, url (the official issue page), count, free,
 * readHref }] — [] when neither has any. Grapevine's issue key is the month; La Viña's is the bimonthly
 * issue covering it (m.lv). readHref: "/read/#<pub>-current" when it is the newest issue of that
 * magazine on /read/ (read.js groupIssues — the page's own rule), else the archive. No highlight lists
 * here: an issue's stories are the monthly digest's (the month they came out).
 */
export function monthIssueLinks(db = {}, m = {}) {
  const L = m.lang === "es" ? "es" : "en";
  const stories = storiesOf(db || {}).filter((a) => a.url);
  const out = [];
  for (const pub of L === "es" ? ["lv", "gv"] : ["gv", "lv"]) {
    const x = m[pub] || null;
    const key = pub === "gv" ? m.key : x && x.key;
    if (!key) continue;
    const list = stories.filter((a) => storyPub(a) === pub && a.extra.issue_key === key);
    if (!list.length) continue;
    const first = list[0];
    const label = (x && x.label) || clean(first.i18n && first.i18n.issue_label && first.i18n.issue_label[L]) || issueLabel(first.extra.issue_label || "", L) || monthLabel(key, L);
    const newest = groupIssues(db.articles, pub)[0];
    out.push({
      pub, isLv: pub === "lv", name: pub === "lv" ? "La Viña" : "Grapevine", key, label,
      theme: (x && x.theme) || issueTheme(db, pub, key, L),
      url: (x && x.url) || first.extra.issue_url || "",
      count: list.length, free: list.filter((a) => a.extra.free === true).length,
      readHref: newest && newest.key === key ? `/read/#${pub}-current` : "/read/#archive-title",
    });
  }
  return out;
}

/**
 * The month as a message for a group chat ("whatsapp": *bold* headings with an emoji, "•" bullets) or an
 * e-mail ("email": UPPERCASE headings underlined with dashes, "-" bullets, no emoji and no asterisks), in
 * one language or both (langs = [lang] or [lang, other]: the first leads; headings then read
 * "English / Español" and each line gets the other language's words on an indented line when they
 * differ). Pure — everything comes in: ctx = { mm: {en, es} month models, nw: {en, es} monthNow,
 * iss: {en, es} monthIssueLinks }, t = translateKey. The live parts (dates already over left out, the
 * next committee meeting, the Grapevine meetings count, the subscription price) only on the current
 * month; a later month gives its whole plan. Links go to the site in the first language. Sections with
 * nothing to say are left out. The poster says the same things; this is its text version.
 */
export function monthMessage(ctx, langs, style, site, t) {
  const Ls = (Array.isArray(langs) ? langs : [langs]).map((l) => (l === "es" ? "es" : "en"));
  const main = Ls[0];
  const wa = style === "whatsapp";
  const mm = ctx.mm;
  const m = mm[main];
  const nw = (ctx.nw && ctx.nw[main]) || null;
  const cur = !!(m.isCurrent && nw);
  const iss = (ctx.iss && ctx.iss[main]) || [];
  const uniq = (a) => a.filter((v, i) => v && a.indexOf(v) === i);
  // vars: an object, or a function of the language (month names differ by language)
  const both = (key, vars) => uniq(Ls.map((l) => t(key, l, typeof vars === "function" ? vars(l) : vars))).join(" / ");
  const head = (s, emoji) => (wa ? `${emoji} *${s}*` : `${s.toUpperCase()}\n${"-".repeat(Math.min(s.length, 60))}`);
  const bullet = wa ? "•" : "-";
  const base = String((site && site.url) || "").replace(/\/+$/, "");
  const url = (p) => base + (main === "es" ? "/es" : "") + p;
  const out = [];

  // Masthead: "Grapevine & La Viña · NETA 65 — October 2026" + the tagline
  const title = `${both("monthly.kicker")} — ${uniq(Ls.map((l) => mm[l].title)).join(" / ")}`;
  out.push(wa ? `*${title}*` : title, wa ? `_${both("monthly.tagline")}_` : both("monthly.tagline"), "");

  // 📖 In the magazines: each magazine's theme (the page language's first) and its stories on the site
  const magLines = [];
  for (const p of main === "es" ? ["lv", "gv"] : ["gv", "lv"]) {
    const x = m[p];
    if (!x || !x.theme) continue;
    const v = iss.find((i) => i.pub === p);
    const issue = p === "lv" && main === "es" ? issueInSentence(x.label, main) : x.label;
    let line = t(p === "gv" ? "report.i_gv" : "report.i_lv", main, { issue, theme: x.theme });
    if (v && v.count) line += ` — ${t(v.count === 1 ? "read.n_stories_one" : "read.n_stories", main, { n: v.count })}${v.free ? ` · ${t("community.wn.free_n", main, { n: v.free })}` : ""}`;
    magLines.push(`${bullet} ${line}`);
    for (const l of Ls.slice(1)) { const o = mm[l][p]; if (o && o.theme && o.theme !== x.theme) magLines.push(`  “${o.theme}”`); }
  }
  if (magLines.length) {
    out.push(head(both("monthly.issues_title"), "📖"), ...magLines);
    if (iss.length) out.push(`  ${t("monthly.msg_read", main, { url: url("/read/") })}`);
    out.push("");
  }

  // 💡 Put it to work: up to 3 tips (the other language's words on a second line)
  const tips = (m.tips || []).slice(0, 3);
  if (tips.length) {
    out.push(head(both("monthly.put_to_work"), "💡"));
    tips.forEach((tp, i) => {
      out.push(`${bullet} ${tp.title}: ${tp.text}`);
      for (const l of Ls.slice(1)) { const o = (mm[l].tips || [])[i]; if (o && o.text !== tp.text) out.push(`  ${o.title}: ${o.text}`); }
    });
    out.push("");
  }

  // 📅 Dates: this month only what is not over yet (+ the next committee meeting once this month's is
  // over); a later month every date. "Sat, Oct 10 · 5–8 PM Central · every month — Title — City"
  const rows = (m.dates || []).filter((d) => !cur || !d.past);
  out.push(head(both("monthly.msg_dates", (l) => ({ month: mm[l].monthName })), "📅"));
  for (const d of rows) {
    const when = [d.range || `${d.chip.wd}, ${d.dayLabel}`, d.time ? `${d.time} ${d.zone}` : ""].filter(Boolean).join(" · ");
    if (d.kind === "committee") {
      out.push(`${bullet} ${when} — ${both("monthly.committee")} (${d.platform}) — ${both("monthly.all_welcome")}`);
      continue;
    }
    const bits = [when];
    if (d.kind === "recurring") bits.push(both("report.e_monthly"));
    if (d.tentative) bits.push(both("report.e_tbc"));
    // the place once: most titles already name the city ("Writing Workshop — Mansfield")
    const place = d.city && !d.title.toLowerCase().includes(String(d.city).toLowerCase()) ? ` — ${d.city}` : "";
    out.push(`${bullet} ${bits.join(" · ")} — ${d.title}${place}`);
    for (const l of Ls.slice(1)) { const o = (mm[l].dates || []).find((x) => x.id === d.id); if (o && o.title && o.title !== d.title) out.push(`  ${o.title}`); }
  }
  if (!rows.length) out.push(both(cur && (m.dates || []).length ? "monthly.no_more_dates" : "monthly.no_dates"));
  // … written like the rows above: "Next committee meeting: Wed, Nov 18 · 7–8 PM Central — Zoom" (in the
  // middle of a line, after the colon, Spanish goes on in lower case: "Próxima reunión del comité: mié, 18 …")
  const nc = cur && nw ? nw.nextCommittee : null;
  if (nc && !nc.thisMonth) {
    const wd = chip(nc.ymd, main).wd;
    const when = [`${main === "es" ? wd.toLowerCase() : wd}, ${nc.dayLabel}`, nc.time ? `${nc.time} ${nc.zone}` : ""].filter(Boolean).join(" · ");
    out.push(`${bullet} ${both("monthly.next_meeting")}: ${when} — ${nc.platform}`);
  }
  out.push(`  ${t("monthly.msg_events", main, { url: url("/events/") })}`, `  ${t("monthly.msg_join", main, { url: url("/meetings/#committee-meeting") })}`, "");

  // 🔁 Every week: the weekly open meetings (+ this month: the Grapevine meetings near you)
  const weekly = m.weekly || [];
  const g = cur ? nw.gvm : null;
  if (weekly.length || g) {
    out.push(head(both("monthly.every_week"), "🔁"));
    for (const w of weekly) out.push(`${bullet} ${t("report.o_line", main, { title: w.title, when: w.when })}${w.startsLabel ? ` — ${t("report.o_starts", main, { date: w.startsLabel })}` : ""}`);
    if (weekly.length) out.push(`  ${t("report.o_more", main, { url: url("/meetings/#weekly-open") })}`);
    if (g) {
      const ours = t(g.inArea === 1 ? "committee.gvm.count_one" : "committee.gvm.count", main, { n: g.inArea });
      out.push(`${bullet} ${both("committee.gvm.home_title")}: ${t(g.nearby ? "committee.gvm.home_text" : "committee.gvm.home_text_area", main, { ours, nearby: g.nearby })}`);
      out.push(`  ${url("/meetings/#grapevine-meetings")}`);
    }
    out.push("");
  }

  // ✍️ Share your story: Grapevine's deadlines, La Viña's open topics (no deadline), the phone story
  // lines (La Viña first in Spanish), how to send one
  const ap = (nw && nw.audio) || {};
  const phones = (main === "es" ? [["La Viña", ap.lv], ["Grapevine", ap.gv]] : [["Grapevine", ap.gv], ["La Viña", ap.lv]]).filter(([, d]) => d);
  const deadlines = m.deadlines || [];
  const lvTopics = m.lvTopics || [];
  if (deadlines.length || lvTopics.length || phones.length) {
    out.push(head(both("monthly.msg_stories"), "✍️"));
    for (const d of deadlines) {
      const themes = uniq(Ls.map((l) => ((mm[l].deadlines || []).find((x) => x.id === d.id) || {}).theme));
      out.push(`${bullet} ${t("monthly.msg_deadline", main, { date: d.dueLabel, theme: themes.join(" / "), issue: d.issueLabel })}`);
    }
    if (lvTopics.length) out.push(`${bullet} ${t("monthly.msg_lv_topics", main)} ${lvTopics.map((x) => `“${x.es}”`).join(", ")}`);
    if (phones.length) out.push(`${wa ? "🎙️" : bullet} ${t("monthly.msg_phone", main)} ${phones.map(([name, d]) => `${name} ${d.phone}`).join(" · ")}`);
    out.push(`  ${t("monthly.msg_how", main, { url: url("/contribute/") })}`, "");
  }

  // 📚 Book of the Month (this month: the offers not over yet; the discount said once when the books
  // share it) + this month: the subscription price (the prices' one home is /shop/)
  const offers = (m.botm || []).filter((b) => !cur || !b.past);
  if (offers.length) {
    const o0 = offers[0];
    const shared = offers.every((b) => b.discount === o0.discount && b.ends === o0.ends);
    const endsIn = (l) => ((mm[l].botm || []).find((x) => x.id === o0.id) || o0).endsLabel;
    out.push(head(shared && o0.discount ? both("monthly.msg_botm_off", (l) => ({ pct: o0.discount, date: endsIn(l) })) : both("monthly.botm"), "📚"));
    for (const b of offers) out.push(`${bullet} “${b.title}” (${b.pub === "lv" ? "La Viña" : "Grapevine"})${!shared && b.discount ? ` — ${t("monthly.botm_off", main, { pct: b.discount, date: b.endsLabel })}` : ""}`);
    out.push(`  ${t("monthly.msg_botm_more", main, { url: url("/shop/#botm") })}`);
  }
  if (cur && nw.subsFrom) out.push(`${wa ? "📬 " : ""}${both("shop.subs_from", (l) => ({ amount: money(nw.subsFrom, l) }))}: ${url("/shop/#subscriptions")}`);
  if (offers.length || (cur && nw.subsFrom)) out.push("");

  // 🖼️ The month's toolkit page (its poster is there)
  out.push(`${wa ? "🖼️ " : ""}${t("monthly.msg_footer", main, { month: m.monthName, url: url(`/monthly/${m.key}/`) })}`);
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

/**
 * The representatives' official guides among the Library's documents (db.pdfs): Grapevine's GVR
 * Workbook and La Viña's RLV manual, the newest of each → [{ pub, title, url, lang }], the page
 * language's magazine first ([] when neither is there). The page links to them and never quotes them.
 */
export function repGuides(pdfs, lang = "en") {
  const docs = ((pdfs && pdfs.items) || [])
    .filter((i) => i && i.url && i.status !== "gone")
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
  const gv = docs.find((i) => i.category === "gvr" && /workbook/i.test(`${i.title || ""} ${(i.tags || []).join(" ")}`));
  const lv = docs.find((i) => i.category === "rlv" && /manual/i.test(i.title || ""));
  const out = [];
  if (gv) out.push({ pub: "gv", title: gv.title, url: gv.url, lang: gv.lang || "en" });
  if (lv) out.push({ pub: "lv", title: lv.title, url: lv.url, lang: lv.lang || "es" });
  return lang === "es" ? out.reverse() : out;
}

export default function (eleventyConfig, helpers) {
  if (helpers && helpers.translateKey) H = { ...H, translateKey: helpers.translateKey };
  eleventyConfig.addGlobalData("monthlyKeys", () => windowKeys());
  eleventyConfig.addGlobalData("monthlyPages", () => {
    const keys = windowKeys();
    return ["en", "es"].flatMap((lang) => keys.map((key) => ({ key, lang })));
  });
  // The last PAST_MONTHS months keep a small redirect page (src/pages/monthly-past.njk → /monthly/),
  // so printed posters' QR codes and shared links never land on "page not found".
  eleventyConfig.addGlobalData("monthlyPastPages", () => {
    const cur = windowKeys(nowDate(), 1)[0];
    const keys = Array.from({ length: PAST_MONTHS }, (_, i) => addMonths(cur, -(i + 1)));
    return ["en", "es"].flatMap((lang) => keys.map((key) => ({ key, lang, label: monthLabel(key, lang) })));
  });

  // The window's models, this month's live extras and the messages are built once per language per
  // build (the hub and 26 pages share them).
  let cache = new Map();
  let nowCache = new Map();
  let msgCache = new Map();
  eleventyConfig.on("eleventy.before", () => { cache = new Map(); nowCache = new Map(); msgCache = new Map(); });
  const months = (db, carry, site, lang) => {
    const k = lang;
    if (!cache.has(k)) {
      const now = nowDate();
      const keys = windowKeys(now);
      cache.set(k, keys.map((key, i) => {
        const m = monthModel(key, db || {}, carry || {}, site || {}, lang, now);
        m.index = i;
        m.hasPrev = i > 0;
        m.hasNext = i < keys.length - 1;
        return m;
      }));
    }
    return cache.get(k);
  };
  const model = (key, db, carry, site, lang) => months(db, carry, site, lang).find((m) => m.key === key) || monthModel(key, db || {}, carry || {}, site || {}, lang);
  const live = (db, site, lang) => {
    const L = lang === "es" ? "es" : "en";
    if (!nowCache.has(L)) nowCache.set(L, monthNow(db || {}, site || {}, L, nowDate()));
    return nowCache.get(L);
  };
  eleventyConfig.addFilter("mpMonths", (db, carry, site, lang) => months(db, carry, site, lang));
  eleventyConfig.addFilter("mpMonth", (key, db, carry, site, lang) => model(key, db, carry, site, lang));
  // This month's live extras (the hub's "This month" card, the current month's page): {% set nx = db | mpNow(site, lang) %}
  eleventyConfig.addFilter("mpNow", (db, site, lang) => live(db, site, lang));
  // A month's issues on the site (story counts, the /read/ link): {% set views = m.key | mpIssues(db, carry, site, lang) %}
  eleventyConfig.addFilter("mpIssues", (key, db, carry, site, lang) => monthIssueLinks(db || {}, model(key, db, carry, site, lang)));
  // The month as a message: {{ m.key | mpMessage(db, carry, site, [lang, other], "whatsapp") }} (or "email")
  eleventyConfig.addFilter("mpMessage", (key, db, carry, site, langs, style) => {
    const L = (Array.isArray(langs) ? langs : [langs]).map((l) => (l === "es" ? "es" : "en"));
    const k = `${key}|${L.join("+")}|${style}`;
    if (!msgCache.has(k)) {
      const mm = { en: model(key, db, carry, site, "en"), es: model(key, db, carry, site, "es") };
      const ctx = {
        mm,
        nw: { en: live(db, site, "en"), es: live(db, site, "es") },
        iss: { en: monthIssueLinks(db || {}, mm.en), es: monthIssueLinks(db || {}, mm.es) },
      };
      msgCache.set(k, monthMessage(ctx, L, style, site || {}, (key2, lang, vars) => H.translateKey(key2, lang, vars)));
    }
    return msgCache.get(k);
  });
  eleventyConfig.addFilter("mpQr", (url, label = "") => qrSvg(url, { label, cls: "mp-qr-svg", margin: 2 }));
  eleventyConfig.addFilter("mpGuides", (pdfs, lang) => repGuides(pdfs, lang));
}
