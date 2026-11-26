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
// link when another page is its one home (the joining details on /meetings/#committee-meeting, prices on
// /shop/, how to send a story on /contribute/, the quote itself on the home page). No list is on both:
// an issue's highlight stories are the digest's; the toolkit shows the themes and story counts and
// links to /read/.
//
// Everything here is read from data the site already has — nothing is typed in:
//   db.editorial   the magazines' themes per issue (extra.issue_key: Grapevine's editorial calendar, La Viña's
//                  yearly themes document) until the issue is out, story deadlines (extra.deadline — both
//                  magazines), both magazines' evergreen suggested topics (extra.evergreen: La Viña's temas
//                  sugeridos; Grapevine's departments and what it is always in need of)
//   db.articles    issues[] — the Grapevine issue on the stands (its own theme, once it is out),
//                  La Viña's bimonthly issue; items — the stories (counts, free to read, and the theme
//                  and La Viña's issue when issues[] has moved on to the next one: issueTheme)
//   carry          config/carry.yml — the 10 ways and the "put it to work" tips per GV issue
//   db.events      committee meetings, the monthly recurring events (CityWide Dallas booth …),
//                  workshops and assemblies (content/events, dated Drive flyers, the outside calendars)
//   db.weekly_open the Weekly Open meetings (La Viña's from its extra.starts date)
//   db.shop.botm   Book of the Month offers (starts / ends window)
//   db.shop.price_changes  a price change AA Grapevine announced (config/site.yml price_changes): the months
//                  from its announcement through its notice pass it on in their message (model `price`) and on
//                  their poster (posterExtras), and the current month's "Keep up all month" has its line
//                  (monthly-month.njk)
//   site.store_offers  an offer the stores announced (config/site.yml store_offers: free shipping …): the months
//                  its days meet name it in their message (model `offers`) and on their poster (posterExtras), and
//                  the current month's "Keep up all month" has its line
//   site.meeting   the committee meeting rule (used when a month's meeting is not in events.json:
//                  the current month once its meeting is over, or the 13th month)
//   live extras    db.quote, db.whatsnew, db.announcements, db.instagram, db.meetings, db.shop,
//                  db.audio_project (monthNow)
//
// Globals:   monthlyPages  [{ key: "YYYY-MM", lang }]  → pagination for the per-month pages (and their
//                                                         calendar files, src/pages/monthly-ics.11ty.js)
//            monthlyKeys   ["YYYY-MM", …]              (13 keys, current month first)
//            monthlyPastPages [{ key, lang, label }]   the 12 months before: redirect stubs to /monthly/
// Filters:   mpMonths(db, carry, site, lang)            → [model, …] for the whole window
//            mpMonth(key, db, carry, site, lang)        → one model
//            mpNow(db, site, lang)                      → the current month's live extras (monthNow)
//            mpIssues(key, db, carry, site, lang)       → the month's issues on the site: story counts and
//                                                         the /read/ links (monthIssueLinks)
//            mpMessage(key, db, carry, site, langs, style) → the month as a WhatsApp / e-mail text
//                                                         (monthMessage; langs ["en"] or ["en", "es"])
//            mpPosterExtras(m)                          → the poster's rows after its dates: the stores' offers and
//                                                         the price change of the month (posterExtras)
//            mpPosterPlaces(m, site)                    → where the poster's blocks that may move are built, from the
//                                                         estimate of each block's height in the page's language: the
//                                                         split's story or Book of the Month in its side column when
//                                                         the dates need the room (posterPlaces, posterBlocks)
//            mpQr(url, label)                           → QR code SVG (qrSvg from community.js)
//            mpGuides(pdfs, lang)                       → the GVR / RLV guides in the Library (repGuides)
//            mpIcs(key, db, carry, site, lang)          → the month's dates as an iCalendar file (monthIcs)
// Everything is built once per build and language (the hub and 26 month pages share it).
// Dev/test:  MONTHLY_NOW=2026-12-15 (or an instant: 2026-10-22T06:00:00Z) fixes "now" — the window,
//            the "over" marks, the next committee meeting and the live extras.

// (community.js imports this file too: the cycle is safe, both only call each other's functions.)
import crypto from "node:crypto";
import { qrSvg, issueLabel, issueInSentence, issueLabelOf } from "./community.js";
import { chicagoDayEndMs, eventEndMs, eventSpan, gvMeetings, announcementList, normalizeEvents, buildIcs, calendarLinks, meetingJoin,
  meetingSpeaker, COMMITTEE_MEETING_PATH, tidyBrackets } from "./committee.js";
import { monthlyRule, TZ } from "../../eleventy.config.js";
import { overnight, wallInstant } from "../central-time.js";
import { shopFromMonthly, money, shopPriceChangeIn, dayLabel, shopOfferIn, offerDates } from "./shop.js";
import { groupIssues, issueName, squash } from "./read.js";
// (since round 37) where a date's title links: the event's own page, a series' page (eleventy/filters/event-links.js)
import { eventLink, eventLinkPlan } from "./event-links.js";

// Helpers handed over by eleventy.config.js (translateKey …); the fallback keeps the module usable
// from a plain `node` script too (as report.js).
let H = { translateKey: (k) => k };

// (TZ: config/site.yml site.timezone — America/Chicago — from eleventy.config.js)
const LOC = { en: "en-US", es: "es-US" };
// The month pages: this month and the 12 after it. Each one's committee meeting takes its flyer (its calendar file's
// ATTACH: monthIcs → normalizeEvents) from its events.json record, which the sync writes for this month and at least
// the committee.js MEETING_MONTHS_AHEAD (12) after it (through config/site.yml events_until's month: meetingMonthsAhead)
// — so no month page lies beyond them (tests/test_meeting_window.py).
const WINDOW = 13;
// A printed poster stays on a corkboard for months: its QR code (the month's page) keeps working for a year.
const PAST_MONTHS = 12;
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
/** The build's clock: ONE moment per build — taken at the build's first call and given to every caller after it:
 *  the month window (monthlyKeys, monthlyPages, monthlyPastPages), the month models and the live extras, the
 *  digest, the district report, the booth, the shop, the presentations. Read afresh at each call, a build that ran
 *  across midnight at the end of a month built October's pages from an October window but their models from a
 *  November one: the 2026-10 page lost its pager and the window linked to a /monthly/2027-11/ that was never
 *  built. Each build ends with endBuildClock (eleventy.after), so the next one — `npm start` rebuilds — takes its
 *  own. MONTHLY_NOW=2026-12-15 (or an instant) fixes it for a preview build or a test. A copy each time: a caller
 *  can never move it for the others. */
let buildNow = null;
export function nowDate() {
  const fixed = process.env.MONTHLY_NOW;
  if (fixed && /^\d{4}-\d{2}-\d{2}/.test(fixed)) return new Date(fixed.length === 10 ? fixed + "T12:00:00-05:00" : fixed);
  if (buildNow === null) buildNow = Date.now();
  return new Date(buildNow);
}
export function endBuildClock() {
  buildNow = null;
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
// A Central wall-clock date and time → the instant (UTC ISO): the site's one helper, eleventy/central-time.js
// (right on the days the clocks change; a time it cannot read is 19:00, the meeting's default)
const ymdPlus = (ymd, n) => new Date(Date.parse(`${ymd}T12:00:00Z`) + n * 864e5).toISOString().slice(0, 10);
function chicagoInstant(ymd, hhmm) {
  const ms = wallInstant(ymd, hhmm || "19:00", TZ);
  return new Date(Number.isFinite(ms) ? ms : wallInstant(ymd, "19:00", TZ)).toISOString();
}
/** A month's date of a monthly rule in the shape of config/site.yml `meeting:` (the committee meeting, or a
 *  recurring event's rule) → { ymd, start, end } (UTC ISO), null on a skip date, before its first date (`starts`:
 *  the Grapevine Meeting's 2027-01-06) or when the month has no such day. Read the way scripts/sync/meeting.py
 *  reads it (eleventy.config.js monthlyRule): "5pm", "7:00 PM", "sábado", "third" … never stop the build or move
 *  the time by 12 hours, an end that is missing or not after the start makes it one hour long (MonthlyRule.span)
 *  — as on /events/ and /meetings/ — and an overnight end ("22:00"–"01:00", central-time.js overnight) is the
 *  next morning. */
export function meetingByRule(key, meeting = {}) {
  const rule = monthlyRule(meeting && typeof meeting === "object" ? meeting : {});
  const wd = WD[String(rule.weekday || "wednesday").toLowerCase()] ?? 3;
  const n = Number(rule.week_of_month || 3);
  const [y, m] = key.split("-").map(Number);
  const d = nthWeekday(y, m - 1, wd, n);
  if (!d) return null;
  const ymd = `${key}-${pad(d)}`;
  const skip = new Set(rule.skip_dates || []);
  if (skip.has(ymd) || (rule.starts && ymd < rule.starts)) return null;
  const endDay = overnight(rule.start || "19:00", rule.end || "20:00") ? ymdPlus(ymd, 1) : ymd;
  return { ymd, start: chicagoInstant(ymd, rule.start || "19:00"), end: chicagoInstant(endDay, rule.end || "20:00") };
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
/** Words that begin a sentence in the data, inside a sentence: in Spanish the first word goes lower case ("— Los
 *  jueves a las 11:00 a. m." → "— los jueves …") unless it is a name ("La Viña …": the next word is capitalized
 *  too) or an acronym ("AA …"). English keeps its capitals (its weekdays are names). */
export function midSentence(s, lang) {
  const v = String(s ?? "");
  if (lang !== "es" || !/^\p{Lu}\p{Ll}*(?![\p{L}\d])/u.test(v) || /^\S+\s+\p{Lu}/u.test(v)) return v;
  return v.charAt(0).toLowerCase() + v.slice(1);
}

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

/** The month a row is shown in: its 1st (a date that began the month before shows its chip on the 1st),
 *  its year (dates of another year say it), the time-zone word, and "now" for the `past` marks. */
const monthCtx = (key, L, now) => ({ first: `${key}-01`, year: key.slice(0, 4), zone: L === "es" ? "(hora del Centro)" : "Central", nowMs: now.getTime() });

/**
 * One row of a month's dates — the page's Dates card, the poster, the hub's chips and the message:
 * the fields the poster always had (chip, day, range, time + zone, city, tentative …) plus
 *   overAt    when it is over, as an ISO instant (committee.js eventEndMs: a timed event at its end — one
 *             hour after it starts without one —, an all-day one at midnight Central after its last day;
 *             the instant /events/ and the home page write too) — the browser marks it "Over" then
 *             (src/assets/js/monthly.js); past = overAt ≤ now (an instant, not a day)
 *   href      where its title links (an English path: the page's lurl puts it in its language): the committee
 *             meeting → /meetings/#committee-meeting (the one home of its joining details); since round 37 any
 *             other event → its own page on this site, "/events/<anchor>/", and a date of a monthly series →
 *             its series' page, "/events/series/<key>/" (eleventy/filters/event-links.js eventLink, with the
 *             build's plan of the pages: ctx.links — a later month's date worked out from the series' rule has
 *             no page of its own, its series' page has); an event the build writes no page for → its own link
 *             (url), else /events/. external = another site.
 *   category  the data's category (eventTone keeps the Grapevine / La Viña calendars' colours)
 *   host      "lv" / "gv" for La Viña's or Grapevine's own event (extra.host — La Viña's monthly workshop):
 *             eventTone gives it that magazine's colour; "" for ours
 *   title     its title in the row's language, without the spaces a calendar left inside its brackets
 *             ("( A.A. Un camino a la vida )" → "(A.A. Un camino a la vida)": no ")" on a line of its own —
 *             committee.js tidyBrackets, so /events/ and the calendar files read the same)
 *   place     the city to show after the title, with its state when that is not Texas ("Riverside, CA"; "TX"
 *             and "Texas" are both Texas): "" when the title already names the city ("Writing Workshop — Mansfield", "booth at CityWide
 *             Dallas") — the page's row, the poster and the message say a place once
 *   online    it can be joined online (an online link, or "Zoom" / "Google Meet" as its place): the row, the
 *             poster and the message say "Online" there, after the place when it has one ("Riverside, CA ·
 *             Online": an event out of state is on a North Texas poster because it can be joined online)
 * extra: { kind: "committee" | "recurring" | "event", … }
 * (src, not enumerable: the event record the row is made from — the month's calendar file writes it as
 * /events.ics does, monthIcs)
 */
// Texas as a calendar writes it ("TX", "Texas", "tx."): a Texas city needs no state on a North Texas poster
const TEXAS = /^\s*(?:tx\.?|texas)\s*$/i;
function dateRow(e, L, ctx, extra = {}) {
  const d = eventDays(e);
  const ex = e.extra || {};
  const timed = !ex.all_day && ex.start && !isYmd(ex.start);
  const shownDay = d.start < ctx.first ? ctx.first : d.start;
  const overAt = iso(eventEndMs(e));
  const href = extra.kind === "committee" ? COMMITTEE_MEETING_PATH : eventLink(e, "en", ctx.links, { page: true }) || e.url || "/events/";
  const title = tidyBrackets(clean(tr(e, "title", L)));
  const city = clean(ex.city);
  const state = clean(ex.state);
  return Object.defineProperty({
    id: e.id, title, url: e.url || "", href, external: /^https?:/.test(href), category: e.category || "",
    ymd: d.start, endYmd: d.end, chip: chip(shownDay, L), dayLabel: shortDate(shownDay, L, ctx.year), day: longDay(d.start, L),
    endDay: d.end !== d.start ? longDay(d.end, L) : "",
    range: d.end !== d.start ? dayRange(d.start, d.end, L) : "",
    time: timed ? `${timeRange(ex.start, ex.end, L)}` : "", zone: timed ? ctx.zone : "",
    city, place: city && !title.toLowerCase().includes(city.toLowerCase()) ? city + (state && !TEXAS.test(state) ? `, ${state}` : "") : "",
    online: !!ex.online || !!ex.online_url || /\b(?:zoom|google meet|microsoft teams|webex)\b/i.test(ex.location || ""),
    host: ex.host === "lv" || ex.host === "gv" ? ex.host : "",
    tentative: !!ex.tentative, overAt, past: !!overAt && Date.parse(overAt) <= ctx.nowMs, ...extra,
  }, "src", { value: e });
}

/** A month's committee meeting as a date row: its events.json record, else the site.meeting rule
 *  (events.json drops a meeting once it is over; skip_dates are honoured) — null when there is none. Its guest
 *  speaker (config/site.yml meeting.speakers, committee.js meetingSpeaker: { name, position, topic } in the row's
 *  language), null on a date without one (Dec 16, 2026): the page's row, the poster and the message name them.
 *  `platform`: where it is held ("Google Meet"); "" once it is over — it was held online, maybe on another platform
 *  (the move to Google Meet changed it for the dates before): the pages say "Online" then. */
function committeeRow(events, key, site, L, ctx) {
  let ev = events.find((e) => e.id && String(e.id).startsWith(`ev:committee:${key}-`));
  if (!ev) {
    const r = meetingByRule(key, site.meeting || {});
    // (where it is held: the settings' platform — committee.js meetingJoin, "Zoom" only when it is left out)
    if (r) ev = { id: `ev:committee:${r.ymd}`, kind: "event", url: COMMITTEE_MEETING_PATH, title: "", extra: { start: r.start, end: r.end, location: meetingJoin(site.meeting).platform, online: true } };
  }
  if (!ev) return null;
  const row = dateRow(ev, L, ctx, { kind: "committee" });
  row.title = "";
  row.platform = row.past ? "" : meetingJoin(site.meeting).platform;
  row.speaker = meetingSpeaker(site.meeting, row.ymd, L);
  return row;
}

/* The magazines' stories on the site (db.articles items): what the issue counts, the La Viña fallback
   and the theme fallback read. The publication as the digest reads it (community.js monthIssues). */
const storyPub = (a) => (a && a.extra && a.extra.publication) || (a && a.category) || "";
const storiesOf = (db) => ((db.articles && db.articles.items) || [])
  .filter((a) => a && a.kind === "article" && a.status !== "gone" && a.extra && a.extra.issue_key);

/* An issue's theme and where it came from ("issue" | "stories" | "calendar"): see issueTheme. machine: the theme
   in this language is a machine translation (a Grapevine theme in Spanish, a La Viña theme in English) — the item's
   `machine` languages, and only when the words shown are this language's own (not the original as a fallback) and
   differ from the original (a title left in English, "Classic Grapevine", is no translation: /read/'s rule, read.js tr). */
function themeOf(db, pub, key, L) {
  const meta = ((db.articles && db.articles.issues) || []).find((i) => i && i.publication === pub && i.key === key) || null;
  const own = meta ? clean(tr(meta, "theme", L)) : "";
  if (own) return { text: own, themes: [own], from: "issue", machine: !!clean(meta.i18n && meta.i18n.theme && meta.i18n.theme[L]) && own !== clean(meta.theme) && (meta.machine || []).includes(L) };
  const first = storiesOf(db).find((a) => storyPub(a) === pub && a.extra.issue_key === key);
  const toldL = first ? clean(first.i18n && first.i18n.issue_theme && first.i18n.issue_theme[L]) : "";
  const told = toldL || (first ? clean(first.extra.issue_theme) : "");
  if (told) return { text: told, themes: [told], from: "stories", machine: !!toldL && toldL !== clean(first.extra.issue_theme) && (first.machine || []).includes(L) };
  // the magazine's own call for stories: Grapevine's editorial calendar, La Viña's yearly themes (a La Viña theme
  // is Spanish: on the English pages its translation, marked machine when it is one — as a Grapevine one in Spanish)
  const themed = ((db.editorial && db.editorial.items) || []).filter((i) => i && i.extra && i.extra.publication === pub && i.extra.issue_key === key);
  const themes = themed.map((i) => clean(tr(i, "title", L))).filter(Boolean);
  if (themes.length) return { text: themes.join(" / "), themes, from: "calendar", machine: themed.some((i) => i.lang !== L && (i.machine || []).includes(L) && clean(tr(i, "title", L)) !== clean(i.title)) };
  return { text: "", themes: [], from: "", machine: false };
}

/**
 * A magazine issue's theme — ONE name everywhere (the month pages and posters, the district report, the
 * monthly digest and its e-mail): the theme the issue itself carries once it is out (articles.json
 * issues[]: i18n.theme[lang], else i18n.theme.en, else theme); else the one its stories on the site carry
 * (the first story's i18n.issue_theme[lang], else extra.issue_theme — so a month keeps its theme after
 * issues[] has moved on to the next issue late in the month); else the magazine's own call for stories in
 * db.editorial — Grapevine's editorial calendar, La Viña's yearly themes (its titles for that issue_key, joined
 * " / "); else "".
 * scripts/notify/send_digest.py issue_theme() is the same rule (tests/test_digest_parity.py).
 */
export function issueTheme(db, pub, key, lang) {
  return themeOf(db || {}, pub, key, lang === "es" ? "es" : "en").text;
}

/* La Viña's bimonthly issue that covers a month: the synced issue (issues[], key = the month or the one
   before), else — once issues[] has moved on to the next issue late in the month — the issue its stories
   on the site belong to (the same two keys): its official page from extra.issue_url, no cover; else — an issue
   not out yet — the one La Viña's yearly themes name for those two keys (db.editorial: its call for stories is
   the theme, as Grapevine's calendar is for a Grapevine issue not out yet), no page and no cover. The label is
   the site's one name for a La Viña issue, from its key (read.js issueName: "September–October 2026" /
   "Septiembre–Octubre 2026", as /contribute/, Home and the presentations write it); the data's own label only
   without a key. themeLang: the language the theme is in ("es" on an English page while a theme has no English
   words yet); machine: the theme is a machine translation (themeOf) — the pages mark it as one. */
function lvIssueOf(db, key, L) {
  const meta = ((db.articles && db.articles.issues) || []).find((i) => i && i.publication === "lv" && i.key && (i.key === key || addMonths(i.key, 1) === key)) || null;
  const lvTheme = (k) => {
    const th = themeOf(db, "lv", k, L);
    const theme = th.text;
    const themeLang = L === "en" && theme && theme === issueTheme(db, "lv", k, "es") ? "es" : L;
    const machine = !!theme && themeLang === L && th.machine;
    // orig: the theme in La Viña's own Spanish words, beside a machine translation (the pages, the poster)
    return { theme, themeLang, machine, orig: machine ? issueTheme(db, "lv", k, "es") : "" };
  };
  if (meta) return { key: meta.key, ...lvTheme(meta.key), label: issueName(meta.key, "lv", L) || tr(meta, "label", L), url: meta.url || "", cover: meta.cover || "" };
  const lvStories = storiesOf(db).filter((a) => storyPub(a) === "lv");
  const k = [key, addMonths(key, -1)].find((x) => lvStories.some((a) => a.extra.issue_key === x));
  if (k) {
    const first = lvStories.find((a) => a.extra.issue_key === k);
    return { key: k, ...lvTheme(k), label: issueName(k, "lv", L), url: first.extra.issue_url || "", cover: "" };
  }
  const cal = ((db.editorial && db.editorial.items) || []).find((i) => i && i.status !== "gone" && i.extra && i.extra.publication === "lv"
    && /^\d{4}-\d{2}$/.test(i.extra.issue_key || "") && (i.extra.issue_key === key || addMonths(i.extra.issue_key, 1) === key));
  if (!cal) return null;
  return { key: cal.extra.issue_key, ...lvTheme(cal.extra.issue_key), label: issueName(cal.extra.issue_key, "lv", L), url: "", cover: "" };
}

/** The price change AA Grapevine announced to mention in a month (first–last, YYYY-MM-DD): { kind, effective } or
 *  null — shop.js shopPriceChangeIn: "before" in the months from its announcement to the one before its day,
 *  "after" from its month through its notice_until. */
function priceMention(shop, first, last) {
  const hit = shopPriceChangeIn(shop || {}, first, last);
  return hit ? { kind: hit.kind, effective: hit.c.effective } : null;
}

/**
 * The story deadlines of both magazines due from `from` through `to` ("YYYY-MM-DD", both included) and not passed
 * on `today` (Central time), soonest first → { gv, lv } — a month's (monthModel: its 1st through the 1st of the
 * next month) or every one still open (/deadlines.ics: deadlinesIcs). One shape for the month pages, the month's
 * message, its calendar file and the deadlines calendar, so they never disagree:
 *   gv  Grapevine's dated themes (its editorial calendar: extra.deadline) — overAt = midnight Central after the
 *       deadline (the browser marks a passed one on the hub)
 *   lv  La Viña's (its yearly themes document: dated topics with an issue_key). The theme is La Viña's own words,
 *       in Spanish (lang "es" on every page); on the English pages its English words beside it when they differ
 *       (gloss; glossMachine when they are a machine translation). The issue inside a sentence: "May–June 2027" /
 *       "mayo–junio de 2027" — the same deadline reads the same on /contribute/, Home, the report and the slides,
 *       and La Viña's issue on these pages too (read.js issueName).
 * `year`: the year a date leaves out ("Oct 1"; another year's "Jan 1, 2027"); none: always with it.
 */
export function storyDeadlines(editorial, lang = "en", { from = "", to = "9999-12-31", today = "", year = "" } = {}) {
  const L = lang === "es" ? "es" : "en";
  const items = Array.isArray(editorial) ? editorial : [];
  const due = (i) => i.extra.deadline >= from && i.extra.deadline <= to && i.extra.deadline >= today;
  const order = (a, b) => a.extra.deadline.localeCompare(b.extra.deadline) || String(a.title).localeCompare(String(b.title));
  const gv = items
    .filter((i) => i && i.extra && i.extra.publication === "gv" && i.extra.deadline && due(i))
    .sort(order)
    .map((i) => ({
      id: i.id, theme: tr(i, "title", L), themeEn: i.title, hook: L === "en" ? hook(i.summary) : "",
      summary: tr(i, "summary", L),
      issueKey: i.extra.issue_key, issueLabel: i.extra.issue_key ? monthLabel(i.extra.issue_key, L) : tr(i, "issue_label", L),
      due: i.extra.deadline, dueLabel: shortDate(i.extra.deadline, L, year), dueLong: shortDate(i.extra.deadline, L, "0"),
      overAt: iso(chicagoDayEndMs(i.extra.deadline)),
      submitUrl: i.extra.submit_url || "", guidelinesUrl: i.extra.guidelines_url || "",
      machine: L === "es" && (i.machine || []).includes("es") && clean(tr(i, "title", L)) !== clean(i.title),
    }));
  const lv = items
    .filter((i) => i && i.status !== "gone" && i.extra && i.extra.publication === "lv" && i.extra.issue_key && i.extra.deadline && due(i))
    .sort(order)
    .map((i) => {
      const es = clean(tr(i, "title", "es")) || clean(i.title);
      const en = L === "en" ? clean(tr(i, "title", "en")) : "";
      return {
        id: i.id, pub: "lv", theme: es, themeLang: "es", gloss: en && en !== es ? en : "",
        glossMachine: !!en && en !== es && (i.machine || []).includes("en"),
        issueKey: i.extra.issue_key, issueLabel: issueName(i.extra.issue_key, "lv", L, true) || issueInSentence(issueLabelOf(i, L), L),
        due: i.extra.deadline, dueLabel: shortDate(i.extra.deadline, L, year), dueLong: shortDate(i.extra.deadline, L, "0"),
        overAt: iso(chicagoDayEndMs(i.extra.deadline)),
      };
    });
  return { gv, lv };
}

/**
 * A magazine's suggested topics for the month `key` ("YYYY-MM"; no deadline: La Viña's temas sugeridos, Grapevine's
 * departments and what it always needs) — 3, rotating by month, the same rule for both → [{ id, es | en (the
 * magazine's own words: La Viña's Spanish, Grapevine's English), text (the topic in `lang`), textLang, machine (text is
 * a machine translation of the magazine's words) }] — monthModel's lvTopics / gvTopics (the toolkit, the posters, the
 * message) and the district report's (report.js).
 * `dated`: that magazine's deadlines listed with them (storyDeadlines rows or editorial items — by id): a topic with
 * the words of one of them is skipped and the next one in the rotation taken, still 3 — Grapevine's department
 * "Emotional Sobriety" read "Any time, … Emotional Sobriety" under its June 2027 theme "Emotional Sobriety — stories due
 * Nov 1" (the review of October 2026). Compared in both languages, case, accents and punctuation aside (read.js squash),
 * so the English and Spanish pages pick the same three (the message pairs them by id). /contribute/ keeps both on
 * purpose: the tile "In every issue", the theme "Next deadline".
 */
export function monthTopics(editorial, pub, key, lang = "en", dated = []) {
  const L = lang === "es" ? "es" : "en";
  const items = (Array.isArray(editorial) ? editorial : []).filter(Boolean);
  const byId = new Map(items.map((i) => [i.id, i]));
  const wordsOf = (i) => (i ? [i.title, i.extra && i.extra.theme, tr(i, "title", "en"), tr(i, "title", "es")] : []);
  const listed = new Set((dated || []).filter(Boolean)
    .flatMap((d) => [...wordsOf(byId.get(d.id)), d.theme, d.themeEn, d.gloss]).map(squash).filter(Boolean));
  const all = items.filter((i) => i.status !== "gone" && i.extra && i.extra.publication === pub && i.extra.evergreen)
    .sort((a, b) => String(a.id).localeCompare(String(b.id)));
  const open = all.filter((i) => !wordsOf(i).some((w) => listed.has(squash(w))));
  const out = [];
  const idx = Number(String(key).slice(0, 4)) * 12 + Number(String(key).slice(5, 7));
  for (let i = 0; out.length < Math.min(3, open.length) && i < all.length; i++) {
    const it = all[(idx * 3 + i) % all.length];
    if (open.includes(it) && !out.includes(it)) out.push(it);
  }
  const own = pub === "lv" ? "es" : "en";
  return out.map((i) => {
    const text = tr(i, "title", L), mine = tr(i, "title", own);
    return { id: i.id, [own]: mine, text, textLang: text === mine ? own : L,
      machine: L !== own && text !== mine && (i.machine || []).includes(L) };
  });
}

// What an events.json date of a series says about that date alone, never about a later month's (seriesTemplate):
// that it is over (build_data.order_events: extra.past), and that an outside calendar or feed listed that day too
// (merge_calendar_duplicates, fill_from_feed)
const DATE_ONLY = ["past", "also_on_calendar", "calendar_match", "also_in_feed", "feed_match"];

/**
 * The record a later month's date of a monthly series is written from (monthModel): the series' LATEST date in
 * events.json — not its last record, which is its oldest past date (build_data.order_events lists the dates to come
 * first, soonest first, then the past ones kept, newest first), and a past date gives none of the joining details
 * (committee.js normalizeEvents: no link, no meeting ID or code once a date is over). What only that date has is left
 * out (DATE_ONLY), and so is its flyer: a later month's date has the series' own flyer, the one for every date
 * (build_data.pick_flyer: a name with no day or month in it) — the flyer two of its dates share; a flyer named with
 * a day or a month is one date's alone ("July 2027 Grapevine Meeting - flyer" is not August's). So a series with
 * only ONE date in events.json gives its later months no flyer (every series has six or more dates there today).
 */
function seriesTemplate(series) {
  const newest = [...series].sort((a, b) => eventDays(b).start.localeCompare(eventDays(a).start));
  const extra = { ...(newest[0].extra || {}) };
  for (const k of DATE_ONLY) delete extra[k];
  const flyerOf = (e) => (e.extra && e.extra.flyer_url) || "";
  const own = newest.find((e) => flyerOf(e) && series.filter((o) => flyerOf(o) === flyerOf(e)).length > 1);
  extra.flyer_url = own ? own.extra.flyer_url : null;
  extra.flyer_thumb = own ? own.extra.flyer_thumb || null : null;
  return { ...newest[0], extra };
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
    // a machine translation (a Spanish page): marked as one, with the theme in Grapevine's own English words (orig)
    machine: gvTheme.machine, orig: gvTheme.machine ? themeOf(db, "gv", key, "en").text : "",
  } : null;

  /* La Viña's bimonthly issue that covers this month (lvIssueOf) */
  const lv = lvIssueOf(db, key, L);

  /* "Put it to work" tips for this month's Grapevine issue */
  const wayById = carry.wayById || {};
  const tips = ((carry.tips || {})[key] || []).filter((t) => wayById[t.way]).map((t) => ({
    way: t.way, icon: wayById[t.way].icon || "circle", title: pair(wayById[t.way].title, L), text: pair(t.text, L),
  }));

  /* Story deadlines from the 1st of this month through the 1st of next month (still open) — both magazines'
     (storyDeadlines: the same rows /deadlines.ics is written from) */
  const { gv: deadlines, lv: lvDeadlines } = storyDeadlines(editorial, L, { from: first, to: nextFirst, today, year });

  /* Each magazine's suggested topics of the month (monthTopics: 3, rotating) — never one with the words of a deadline
     listed above it in the same card (the month's: the toolkit's card, the poster's block, the message's lines) */
  const lvTopicList = monthTopics(editorial, "lv", key, L, lvDeadlines);
  const gvTopicList = monthTopics(editorial, "gv", key, L, deadlines);

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
  // (the build's plan of the events' pages: where each date's title links — dateRow)
  ctx.links = eventLinkPlan(db, site);
  const committee = committeeRow(events, key, site, L, ctx);
  /* The recurring series (config/site.yml recurring_events:) — events.json lists only the next
     `months_ahead` dates, so a later month's date is worked out from the same rule (like the
     committee meeting from site.meeting), with the series' own title and repeat line — and its link, meeting ID
     or code: written from the series' latest date, a date still to come (seriesTemplate). */
  const recEvents = events.filter((e) => e.extra && e.extra.recurring && e.extra.series);
  const recIn = recEvents.filter(inMonth);
  const projected = new Set();
  for (const spec of Array.isArray(site.recurring_events) ? site.recurring_events : []) {
    // the entry as build_data.recurring_specs reads it (eleventy.config.js monthlyRule): its key slugified
    // ("CityWide Dallas" → "citywide-dallas", else from the title) — the `series` its dates carry in
    // events.json — and one skip date without brackets counted too; a key used twice counts once (the sync
    // keeps the first entry)
    const sp = spec && typeof spec === "object" && spec.enabled !== false ? monthlyRule(spec, true) : null;
    if (!sp || !sp.key || projected.has(sp.key)) continue;
    projected.add(sp.key);
    const series = recEvents.filter((e) => e.extra.series === sp.key);
    const lastListed = series.reduce((mx, e) => (eventDays(e).start > mx ? eventDays(e).start : mx), "");
    if (!series.length || series.some(inMonth) || lastListed >= first) continue;
    const tpl = seriesTemplate(series);
    // the rule as build_data understood it (extra.rule: week_of_month 1–5 / -1, English weekday, "HH:MM"
    // start and the end as used — "Saturdays", "2nd", "5 PM" or no end all read as the sync read them);
    // only skip_dates and the first date (`starts`: no month before it) come from the settings
    const rule = (tpl.extra && tpl.extra.rule) || sp;
    const r = meetingByRule(key, { week_of_month: rule.week_of_month, weekday: rule.weekday, start: rule.start, end: rule.end, skip_dates: sp.skip_dates || [], starts: sp.starts || "" });
    if (!r) continue;
    // (a date after every one events.json lists: still to come, as build_data marks such a date — extra.past false)
    recIn.push({ ...tpl, id: `ev:recurring:${sp.key}:${r.ymd}`, date: r.start, extra: { ...tpl.extra, start: r.start, end: r.end, past: false } });
  }
  const recurring = recIn
    .sort((a, b) => eventDays(a).start.localeCompare(eventDays(b).start))
    .map((e) => dateRow(e, L, ctx, { kind: "recurring", series: e.extra.series, label: tr(e, "recurrence_label", L) }));
  const other = events.filter((e) => !(e.extra && e.extra.recurring) && !String(e.id).startsWith("ev:committee:") && inMonth(e))
    .sort((a, b) => eventDays(a).start.localeCompare(eventDays(b).start))
    .map((e) => dateRow(e, L, ctx, { kind: "event" }));
  /* One list, by the day its chip shows, and on one day by the time it starts (round 33c: November 18, 2026 listed
     the committee meeting, 7–8 PM, above La Viña's workshop, 2–3 PM — the day alone decided): an all-day date first
     (committee.js eventSpan: midnight Central of its day), then the timed ones from the earliest — the order of
     /events/ and its calendar's "Next up" (normalizeEvents: startMs). A date that began the month before (its chip on
     the 1st) started before anything on the 1st: first that day. Dates that start at the same moment keep the order
     above (the committee meeting, the monthly series, the other events: a stable sort) — never the title, which would
     order them differently in English and Spanish. Every list made from this one follows it: the page's Dates card
     (and its "Earlier in …" fold), the poster, the hub's chips and the month's message (the calendar file, monthIcs,
     sorts its entries by their start itself, the story deadlines among them). */
  const startsAt = (d) => { const s = d.src ? eventSpan(d.src) : null; return s ? s.startMs : Infinity; };
  const dates = [committee, ...recurring, ...other].filter(Boolean)
    .sort((a, b) => a.chip.ymd.localeCompare(b.chip.ymd) || (startsAt(a) - startsAt(b)) || 0);

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
  for (const d of [...deadlines, ...lvDeadlines]) mark(d.due, "deadline");
  const weekdays = Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(LOC[L], { weekday: "narrow", timeZone: "UTC" }).format(new Date(Date.UTC(2026, 1, 1 + i))));
  const calendar = { offset, days: lastDay(key), marks, weekdays };

  /* Density: how much the poster holds (the CSS tightens type for busy months; every date of the month is on the
     poster — round 26b —, and the page's fit, assets/js/monthly.js, sizes the type and places the blocks so they
     all fit). La Viña's deadlines are on the Spanish poster only (one compact line each), with its topics;
     Grapevine's topics on the English poster
     (posterGvTopics: macros/monthly.njk story()) where its deadlines leave room — fewer than two (each comes with
     its prompt) — and the poster stays "roomy" with them: three more lines on a fuller poster would make all of
     its type smaller (the poster's fit, assets/js/monthly.js: December 2026's 21.75px → 18.25px), and a "snug" one
     loses La Viña's invitation (monthly.lv_nudge) and a "Put it to work" tip — never for Grapevine's topics. The
     stores' offers and the price change of the month are rows of the poster's Dates block too (posterExtras): each
     counts as a date */
  const price = priceMention(db.shop, first, last);
  const offers = shopOfferIn(site, first, last, L, today);
  const isCurrent = key === today.slice(0, 7);
  const extras = offers.filter((o) => !(isCurrent && o.past)).length + (price ? 1 : 0);
  const base = deadlines.length * 3 + Math.min(tips.length, 3) * 2 + botm.length * 1.5 + (dates.length + extras) * 1.2 + weekly.length
    + (L === "es" ? 2 + lvDeadlines.length * 2 : 0);
  const posterGvTopics = L !== "es" && gvTopicList.length > 0 && deadlines.length < 2 && base + 2 <= 15;
  const load = base + (posterGvTopics ? 2 : 0);
  const density = load > 20 ? "dense" : load > 15 ? "snug" : "roomy";

  const path = `/monthly/${key}/`;
  const url = (L === "es" ? "/es" : "") + path;
  return {
    key, lang: L, year, month: mNum, first, last,
    name: cap(monthName(key, L)), monthName: monthName(key, L), label: monthLabel(key, L), title: cap(monthLabel(key, L)),
    design: design.id, layout: design.layout, density,
    isCurrent,
    gv, lv, tips, deadlines, lvDeadlines, lvTopics: lvTopicList, gvTopics: gvTopicList, posterGvTopics, botm, botmOffer,
    committee, recurring, events: other, dates, weekly, calendar,
    // a price change AA Grapevine announced whose notice meets this month (shop.js shopPriceChangeIn): { kind
    // "before" | "after", effective } — the month's message passes it on (monthMessage), and its poster (posterExtras)
    price,
    // the offers the stores announced whose days meet this month (config/site.yml store_offers, shop.js shopOfferIn):
    // [{ key, title, titleLang, starts, ends, showStarts, icon, past }] — the month's message names them (monthMessage),
    // and its poster (posterExtras)
    offers,
    url, absUrl: String(site.url || "").replace(/\/$/, "") + url,
    prev: addMonths(key, -1), next: addMonths(key, 1),
    fileName: `neta65-grapevine-${key}-${L}.png`,
    // "Add this month's dates to my calendar": the month's calendar file beside its page (monthIcs, icsPath)
    icsUrl: icsPath(key, L),
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
 *                  else the rule), then next month's — { ymd, day, dayLabel, time, zone, platform, speaker,
 *                  overAt, thisMonth } or null. (Not src/_data/meeting.js: that one ignores MONTHLY_NOW.)
 *   outNext        an issue already online before its month (the district report's rule: articles.json
 *                  issues[] newer than this month's Grapevine key / than the La Viña issue covering this
 *                  month) → [{ pub, theme, machine (a machine translation), issue (inside a sentence), monthKey,
 *                  monthLabel, monthUrl (its toolkit, "" outside the window) }], the page language's magazine first
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
    nextCommittee = { ymd: row.ymd, day: row.day, dayLabel: row.dayLabel, time: row.time, zone: row.zone, platform: row.platform, speaker: row.speaker,
      overAt: row.overAt, thisMonth: row.ymd.startsWith(key) };
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
    // La Viña's issue by the site's one name for it (issueName), like its issue and deadlines on these pages
    const issue = (pub === "lv" && issueName(i.key, "lv", L, true)) || issueInSentence(label, L);
    // machine: the theme is a machine translation (the page marks it, as the month's own themes — themeOf's rule)
    const machine = !!clean(i.i18n && i.i18n.theme && i.i18n.theme[L]) && theme !== clean(i.theme) && (i.machine || []).includes(L);
    outNext.push({ pub, theme, machine, issue, monthKey: i.key, monthLabel: monthLabel(i.key, L), monthUrl: keys.includes(i.key) ? `/monthly/${i.key}/` : "" });
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
    const label = (x && x.label) || (pub === "lv" && issueName(key, "lv", L))
      || clean(first.i18n && first.i18n.issue_label && first.i18n.issue_label[L]) || issueLabel(first.extra.issue_label || "", L) || monthLabel(key, L);
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
 * The poster's rows after the month's dates, in its Dates block (round 26b, the owner: "add all the happenings and
 * events of that month to those posters") — in the words of the month's message (monthMessage), so the two never
 * disagree: each offer the stores announced whose days meet the month (its title, its days: "November 1 – December
 * 31, 2026", "Through December 31, 2026"), then AA Grapevine's price change ("Grapevine and La Viña prices change on
 * January 1, 2027"). The current month leaves out an offer already over, as its message does. Described, never sold:
 * no price, no link (the poster is a picture). → [{ kind: "offer" | "price", key, icon, title, titleLang, meta }]
 * (icon: the offer's own — the truck, the gift — as on the page's "Keep up all month"; the price change's
 * calendar-clock, as there). t: (key, lang, vars) → the site's words.
 */
export function posterExtras(m, t) {
  const L = m && m.lang === "es" ? "es" : "en";
  const rows = [];
  for (const o of (m && m.offers) || []) {
    if (m.isCurrent && o.past) continue;
    const d = offerDates(o.showStarts === false ? "" : o.starts, o.ends, L, t);
    rows.push({ kind: "offer", key: o.key, icon: o.icon || "truck", title: o.title, titleLang: o.titleLang || L,
      meta: d.charAt(0).toUpperCase() + d.slice(1) });
  }
  if (m && m.price) {
    const key = m.price.kind === "before" ? "shop.pc_line_before" : "shop.pc_line_after";
    rows.push({ kind: "price", key: "price", icon: "calendar-clock", title: t(key, L, { date: dayLabel(m.price.effective, L) }),
      titleLang: L, meta: "" });
  }
  return rows;
}

/* ------------------------------------------------------------------ */
/*  The poster as built: where its blocks go (posterPlaces)            */
/* ------------------------------------------------------------------ */
/* Round 33c. The poster as the build makes it is what a reader sees before the page's fit has run (assets/js/monthly.js:
   about a second after the fonts arrive) and what a page opened without JavaScript keeps: its blocks where the template
   puts them (macros/monthly.njk poster(): data-mp-move, the build's place first) at the stylesheet's type (the month's
   density; a Spanish poster smaller until its fit — areas/monthly.css). A busy month's column may lose its last lines
   there, but every date must be whole (tests/browser/test_monthly_posters_browser.py UnfittedClipped). The density alone could not
   see to that: it counts the dates, not their words, and November 2026 — ten rows in its Dates block once La Viña's
   monthly workshop moved to the 18th, the longest of them Spanish ("Ofertas de regalo para las fiestas en las tiendas de
   La Viña y Grapevine", two lines where the English one takes one) — was already "dense", the densest there is, when
   its last two rows ran past the foot of the split's content column, under the story and the issue.
   So the build now estimates how tall each block of the poster is, from the words it will print in the page's
   language — every date's title and line under it, the story's deadlines and topics, the issue's theme and tips … —
   set in the poster's own typefaces at the poster's starting type and the column's width (each letter as wide as Chrome
   draws it: POSTER_FACES), and it puts the blocks that may sit in either column (their data-mp-move) where the dates
   end inside their column and nothing else is cut, when the template's own places would not hold them (posterPlaces:
   November 2026's Spanish story goes up into the side column, under the calendar, so the dates and the Book of the
   Month all fit; its English Book of the Month, cut at the foot until now, goes there too). Any month: the estimate
   reads the month's own words, so a month whose dates are longer or more in one language is placed for that language.
   The page's fit then starts from that arrangement (the build's own first) and searches on as before. Today that is
   the split layout (March and November): its two columns run the poster's whole height; every other layout's dates
   head their column (the ticket's stub, the cork's right-hand column) or have a band of their own across the poster
   (the editorial's band, the cover's strip, the notebook's lower row), so no block before them could make room.
   Never a date shortened or left out: the dates' rows are what is measured, not what gives way. */

/* The poster's two typefaces as Chrome draws them (measured in round 33c at 40px, in thousandths of an em): every
   letter's advance — Inter (the sans: --font-sans) at weight 400, Fraunces (the display face: --font-display) at 700,
   a–z then A–Z — and how much wider another weight draws a letter (bolder is wider) and a space (narrower in Inter);
   an accented letter as its base letter. Set this way, 95% of the 1,003 lines of the 26 posters of round 33c came within
   2% of their real width, 99% within 3% (the worst 5%); every block of the split's columns within 2px of its real height
   but one, where a line that fits by a pixel was counted on two (18px taller: the safe side). */
const POSTER_FACES = {
  sans: {
    low: [562, 612, 571, 612, 583, 333, 613, 591, 242, 242, 549, 242, 876, 591, 600, 612, 612, 391, 528, 327, 591, 562, 818, 546, 562, 552],
    up: [704, 654, 730, 722, 601, 590, 746, 743, 269, 571, 672, 565, 903, 753, 765, 639, 765, 644, 642, 646, 744, 704, 1009, 682, 679, 629],
    digit: 595, space: { 400: 281, 500: 267, 600: 252, 700: 237, 800: 219 },
    wLow: { 400: 1, 500: 1.016, 600: 1.032, 700: 1.049, 800: 1.068 }, wUp: { 400: 1, 500: 1.01, 600: 1.019, 700: 1.029, 800: 1.04 },
    marks: { "-": 460, "–": 500, "—": 1000, "(": 365, ")": 365, "/": 360, "?": 511, "¿": 511, "&": 644, "@": 966 }, narrow: 288,
  },
  display: {
    low: [566, 614, 524, 624, 533, 406, 585, 644, 323, 323, 624, 331, 959, 644, 594, 628, 615, 494, 496, 402, 635, 554, 840, 561, 572, 500],
    up: [745, 732, 704, 806, 667, 622, 764, 862, 424, 536, 814, 638, 938, 759, 792, 720, 794, 778, 621, 711, 746, 721, 1070, 731, 690, 642],
    digit: 610, space: { 600: 209, 700: 203, 800: 200 },
    wLow: { 600: 0.965, 700: 1, 800: 1.017 }, wUp: { 600: 0.974, 700: 1, 800: 1.013 },
    marks: { "-": 382, "–": 540, "—": 846, "(": 374, ")": 373, "/": 476, "?": 566, "¿": 542, "&": 985, "@": 924 }, narrow: 290,
  },
};

/* The poster's kinds of text (areas/monthly.css): face, weight, size in em of the poster's type (a nested size
   multiplied out: a compact deadline's theme is 1.1em of the list's 0.88em), line height, uppercase, letter spacing in em.
   Fraunces under 30px is drawn a little wider (its optical size): `small` adds 2% there. */
const POSTER_TEXT = {
  h: { face: "sans", wt: 800, size: 0.9, lh: 1.15, up: true, ls: 0.1 },          // .mp-h — a block's heading
  sub: { face: "sans", wt: 800, size: 0.8, lh: 1.3, up: true, ls: 0.08 },        // .mp-sub
  note: { face: "sans", wt: 400, size: 0.95, lh: 1.3 },                          // .mp-note
  send: { face: "sans", wt: 600, size: 0.84, lh: 1.3 },                          // .mp-send
  nudge: { face: "sans", wt: 500, size: 0.84, lh: 1.3 },                         // .mp-send--lv
  topic: { face: "display", wt: 600, size: 1.12, lh: 1.15 },                     // .mp-topics li
  dlTheme: { face: "display", wt: 700, size: 1.5, lh: 1.05 },                    // .mp-dl-theme
  dlLine: { face: "sans", wt: 400, size: 0.86, lh: 1.3 },                        // .mp-dl-hook, .mp-dl-due
  cTheme: { face: "sans", wt: 700, size: 0.968, lh: 1.2 },                       // .mp-dl--compact .mp-dl-theme
  cOrig: { face: "sans", wt: 400, size: 0.7568, lh: 1.2 },                       // .mp-dl--compact .mp-orig
  cDue: { face: "sans", wt: 400, size: 0.7568, lh: 1.3 },                        // .mp-dl--compact .mp-dl-due
  mtnote: { face: "sans", wt: 400, size: 0.72, lh: 1.25 },                       // .mp-mtnote
  lvTheme: { face: "display", wt: 700, size: 1.35, lh: 1.05, line: 1.45 },       // .mp-lvline strong (in a line of 1.3em)
  theme: { face: "display", wt: 700, size: 1.85, lh: 1.02 },                     // .mp-theme
  origTheme: { face: "sans", wt: 400, size: 0.9, lh: 1.2 },                      // .mp-orig--theme
  tipT: { face: "sans", wt: 700, size: 0.95, lh: 1.2 },                          // .mp-tips strong
  tipX: { face: "sans", wt: 400, size: 0.86, lh: 1.3 },                          // .mp-tip-t
  dateT: { face: "sans", wt: 700, size: 0.92, lh: 1.15 },                        // .mp-date-t
  dateM: { face: "sans", wt: 400, size: 0.84, lh: 1.22 },                        // .mp-date-m
  book: { face: "display", wt: 700, size: 0.9632, lh: 1.12 },                    // .mp-books strong
  off: { face: "sans", wt: 800, size: 0.86, lh: 1.25 },                          // .mp-books .mp-off
  offAll: { face: "sans", wt: 800, size: 0.92, lh: 1.3 },                        // .mp-botm > p.mp-off
  wkT: { face: "sans", wt: 700, size: 0.8772, lh: 1.25 },                        // .mp-wk strong
  wkWhen: { face: "sans", wt: 400, size: 0.7912, lh: 1.25 },                     // .mp-wk-when
  kicker: { face: "sans", wt: 800, size: 0.86, lh: 1.3, up: true, ls: 0.16 },    // .mp-kicker
  tag: { face: "sans", wt: 700, size: 1.05, lh: 1.3 },                           // .mp-tag
  committee: { face: "sans", wt: 700, size: 0.8, lh: 1.3, ls: 0.04 },            // .mp-committee
  url: { face: "sans", wt: 800, size: 0.9, lh: 1.3 },                            // .mp-l-split .mp-url
  scan: { face: "sans", wt: 400, size: 0.84, lh: 1.3 },                          // .mp-scan
};

/** A text's width in em of its own size, in a kind of text (POSTER_TEXT). */
export function posterEm(s, x) {
  const F = POSTER_FACES[x.face];
  let w = 0, n = 0;
  for (const ch of x.up ? String(s).toUpperCase() : String(s)) {
    const c = ch.normalize("NFD").charCodeAt(0);
    if (c >= 97 && c <= 122) w += F.low[c - 97] * F.wLow[x.wt];
    else if (c >= 65 && c <= 90) w += F.up[c - 65] * F.wUp[x.wt];
    else if (c >= 48 && c <= 57) w += F.digit * F.wLow[x.wt];
    else if (ch === " ") w += F.space[x.wt];
    else w += F.marks[ch] || F.narrow;
    n++;
  }
  return w / 1000 + (x.ls || 0) * n;
}

/** How many lines a text takes in a box `width` px wide, the poster's type `T` px: the words set one after another,
 *  a line broken at a space or after a hyphen or a dash (where Chrome breaks "lending-library" too); a word longer than
 *  the line (an e-mail address: overflow-wrap) on as many lines as it needs. 0 for no text. */
export function posterLines(s, width, x, T) {
  const text = clean(s);
  if (!text) return 0;
  const px = x.size * T * (x.face === "display" && x.size * T < 30 ? 1.02 : 1);
  const space = (POSTER_FACES[x.face].space[x.wt] / 1000 + (x.ls || 0)) * px;
  let lines = 1, cur = 0;
  for (const word of text.split(" ")) {
    word.split(/(?<=[-–—])(?=.)/).forEach((part, i) => {
      const w = posterEm(part, x) * px, join = cur > 0 && i === 0 ? space : 0;
      if (cur > 0 && cur + join + w > width + 0.5) { lines++; cur = w; } else cur += join + w;
      while (cur > width + 0.5) { lines++; cur -= width; }
    });
  }
  return lines;
}

/** A text's height in px (its lines × its line height), or 0 for no text. */
const posterText = (s, width, x, T) => posterLines(s, width, x, T) * x.size * T * (x.line ? x.line / x.size : x.lh);

/** The height of things stacked in a block, in px: [{ mt, h, mb }], the margins between two of them collapsed (the
 *  larger one counts — a list's first row's margin and the heading's margin under it are one), the first one's top
 *  and the last one's bottom margin inside the block (a flex item: they never reach outside it). */
function posterStack(items) {
  let h = 0, mb = null;
  for (const it of items) {
    if (!it) continue;
    h += (mb === null ? it.mt || 0 : Math.max(mb, it.mt || 0)) + it.h;
    mb = it.mb || 0;
  }
  return h + (mb || 0);
}

/**
 * Each block of a month's poster, estimated: { head, calendar, story, issue, dates, botm, weekly, foot } — each a
 * function of the column's width in px (inside the block's own padding, which the column adds: posterPlaces) → its
 * height in px at the poster's type `T` px, from the words the template prints (macros/monthly.njk, the poster in the
 * page's language; the dates' rows after them: posterExtras) and the stylesheet's sizes and spaces (areas/monthly.css).
 * The masthead and the footer are the split's (its side column: the only one they are estimated in).
 * t: (key, lang, vars) → the site's words; site: the `site` global (links, committee, url).
 */
export function posterBlocks(m, site, t, T) {
  const L = m && m.lang === "es" ? "es" : "en";
  const tt = (k, v) => t(k, L, v);
  const links = (site && site.links) || {};
  const X = POSTER_TEXT;
  const text = (s, w, x) => posterText(s, w, x, T);
  // a block's heading: its icon (1.05em of the heading's 0.9em) and 10px beside it, 8px under it
  const heading = (s, w) => ({ h: Math.max(0.945 * T, text(s, w - 0.945 * T - 10, X.h)), mb: 8 });
  const sub = (s, w) => ({ mt: 10, h: text(s, w, X.sub), mb: 6 });
  // topics: a dot before each (1.1em of the topic's 1.12em)
  const topics = (list, w) => list.map((s) => ({ mt: 4, h: text(s, w - 1.232 * T, X.topic) }));
  // a compact list of deadlines (the Spanish poster's): 7px above and under each row (2px above the first), a 2px
  // rule between two; the theme, Grapevine's own words under a machine-translated one, the issue and the day
  const compact = (rows, w) => rows.map((r, i) => ({ h: (i ? 9 : 2) + 7 + text(r.theme, w, X.cTheme)
    + (r.orig ? 1 + text(r.orig, w, X.cOrig) : 0) + 6 + text(r.due, w, X.cDue) }));
  const dueLine = (d, sep) => `${tt("monthly.for_issue", { issue: d.issueLabel })}${sep}${tt("monthly.due", { date: d.dueLabel })}`;
  const machineNote = (w) => ({ mt: 10, h: text(tt("read.mt_note_en"), w, X.mtnote) });

  const story = (w) => {
    const items = [heading(tt(L === "es" ? "monthly.share_story_lv" : "monthly.share_story"), w)];
    if (L === "es") {
      items.push(...compact((m.lvDeadlines || []).map((d) => ({ theme: d.theme, due: dueLine(d, " · ") })), w));
      if ((m.lvTopics || []).length) items.push(sub(tt("monthly.lv_topics"), w), ...topics(m.lvTopics.map((x) => x.es), w));
      items.push({ mt: 10, h: text(tt("monthly.lv_send", { email: links.lv_email_editorial }), w, X.send) });
      if ((m.deadlines || []).length) {
        items.push(sub(tt("monthly.gv_english"), w), ...compact(m.deadlines.map((d) => ({ theme: d.theme,
          orig: d.machine && d.themeEn && d.themeEn !== d.theme ? d.themeEn : "", due: dueLine(d, " · ") })), w));
        if (m.deadlines.some((d) => d.machine)) items.push(machineNote(w));
      }
    } else {
      // a deadline: its theme, its prompt, its issue and day — 12px above and under it (2px above the first), a rule
      if ((m.deadlines || []).length) {
        items.push(...m.deadlines.map((d, i) => ({ h: (i ? 14 : 2) + text(d.theme, w, X.dlTheme)
          + (d.hook ? 4 + text(d.hook, w, X.dlLine) : 0) + 6 + text(dueLine(d, " — "), w, X.dlLine) + 12 })));
      } else items.push({ h: text(tt("monthly.no_deadlines"), w, X.note) });
      if (m.posterGvTopics) items.push(sub(tt("monthly.gv_topics"), w), ...topics((m.gvTopics || []).map((x) => x.text), w));
      items.push({ mt: 10, h: text(tt("monthly.submit_line", { email: links.gv_email_editorial }), w, X.send) });
      if (m.density === "roomy") items.push({ mt: 10, h: text(tt("monthly.lv_nudge", { email: links.lv_email_editorial }), w, X.nudge) });
    }
    return posterStack(items);
  };

  // the issue (as macros/monthly.njk issue() with the split's three tips at most: all of them in a roomy month, two in a
  // snug one, one in a dense one)
  const issue = (w) => {
    const items = [];
    if (L === "es" && m.lv) items.push({ h: 2 + text(`${tt("monthly.in_lv")} · ${m.lv.label}`, w, X.sub) + text(m.lv.theme, w, X.lvTheme), mb: 14 });
    items.push(heading(tt("monthly.in_gv", { month: m.monthName }), w));
    items.push({ h: text(m.gv ? m.gv.theme : tt("monthly.no_issue"), w, X.theme) });
    if (m.gv && m.gv.machine && m.gv.orig) {
      items.push({ mt: 6, h: text(m.gv.orig, w, X.origTheme) });
      if (L === "es" && !(m.deadlines || []).some((d) => d.machine)) items.push(machineNote(w));
    }
    const tips = m.tips || [];
    if (tips.length) {
      const n = m.density === "roomy" ? 3 : m.density === "dense" ? 1 : 2;
      items.push(sub(tt("monthly.put_to_work"), w));
      // a tip: its icon (1.65em) and 12px beside its title and its line
      for (const tp of tips.slice(0, n)) {
        const tw = w - 1.65 * T - 12;
        items.push({ mt: 12, h: Math.max(1.65 * T, text(tp.title, tw, X.tipT) + 2 + text(tp.text, tw, X.tipX)) });
      }
    }
    return posterStack(items);
  };

  // the dates: each row 5px above and under its chip (its month, day and weekday: 13px and 2.81em) or its title and the
  // line under it, whichever is taller; an offer's or the price change's icon in a smaller chip (1.9em)
  const dates = (w) => {
    const extras = posterExtras(m, t);
    const items = [heading(tt("monthly.dates"), w)];
    if (!(m.dates || []).length && !extras.length) items.push({ h: text(tt("monthly.no_dates"), w, X.note) });
    for (const d of m.dates || []) {
      const parts = [];
      if (d.range) parts.push(d.range);
      if (d.time) parts.push(`${d.time} ${d.zone}`);
      if (d.kind === "committee") {
        parts.push(d.platform || tt("monthly.online"));
        if (d.speaker) parts.push(tt("monthly.speaker", { name: d.speaker.name }));
        parts.push(tt("monthly.all_welcome"));
      } else {
        if (d.place) parts.push(d.place);
        if (d.online) parts.push(tt("monthly.online"));
      }
      if (d.tentative) parts.push(tt("committee.events.tentative"));
      const bw = w - 3.1 * T - 12;
      const body = 2 + text(d.kind === "committee" ? tt("monthly.committee") : d.title, bw, X.dateT)
        + (parts.length ? 2 + text(parts.join(" · "), bw, X.dateM) : 0);
      items.push({ h: 10 + Math.max(13 + 2.81 * T, body) });
    }
    for (const x of extras) {
      const bw = w - 1.9 * T - 10;
      items.push({ h: 10 + Math.max(1.9 * T + 1, 2 + text(x.title, bw, X.dateT) + (x.meta ? 2 + text(x.meta, bw, X.dateM) : 0)) });
    }
    return posterStack(items);
  };

  const botm = (w) => {
    if (!(m.botm || []).length) return 0;
    const offText = (b) => (b.discount ? tt("monthly.botm_off", { pct: b.discount, date: b.endsLabel }) : tt("monthly.botm_until", { date: b.endsLabel }));
    const items = [heading(tt("monthly.botm"), w)];
    for (const b of m.botm) items.push({ mt: 6, h: text(b.title, w, X.book) + (m.botmOffer ? 0 : 2 + text(offText(b), w, X.off)) });
    if (m.botmOffer) items.push({ mt: 8, h: text(offText({ discount: m.botmOffer.discount, endsLabel: m.botmOffer.endsLabel }), w, X.offAll) });
    return posterStack(items);
  };

  const weekly = (w) => {
    if (!(m.weekly || []).length) return 0;
    const items = [heading(tt("monthly.weekly"), w)];
    for (const x of m.weekly) {
      // (the NEW badge after the title: about as wide as the word in the title's letters)
      const when = `${x.when}${x.startsLabel ? ` · ${tt("monthly.weekly_from", { date: x.startsLabel })}` : ""}`;
      items.push({ mt: 6, h: text(x.new ? `${x.title} ${tt("monthly.new").toUpperCase()}` : x.title, w, X.wkT) + text(when, w, X.wkWhen) });
    }
    return posterStack(items);
  };

  // the split's masthead: the kicker, the month's name (its size: the stylesheet's min(120px, 320px / (0.6 × letters)),
  // 0.9 of it a line), the year on a line of its own (0.62 of the name; 18px under a name with a descender, else 8px)
  // and the tagline
  const head = (w) => {
    const name = String(m.name || ""), M = Math.min(120, 320 / (0.6 * Math.max(1, name.length)));
    return text(tt("monthly.kicker"), w, X.kicker) + 6 + 0.9 * M + (/[gjpqy]/.test(name) ? 18 : 8) + 0.558 * M
      + 10 + text(tt("monthly.tagline"), w, X.tag);
  };

  // the split's calendar: its weekday row (28px) and a 40px row a week, 5px apart
  const calendar = () => {
    const c = m.calendar || { offset: 0, days: 30 };
    return 28 + 45 * Math.ceil((c.offset + c.days) / 7);
  };

  // the split's footer: the logo and the QR code (176px) on a line, 16px, then the committee, the address (its two
  // halves never broken: a line each when they do not fit on one) and "scan for this month's toolkit", 2px apart
  const foot = (w) => {
    const short = String((site && site.url) || "").replace(/^https?:\/\//, "");
    const addr = short + (L === "es" ? "/es/" : short.includes("/") ? "/" : "");
    const cut = addr.indexOf("/");
    const halves = cut > 0 ? [addr.slice(0, cut + 1), addr.slice(cut + 1)] : [addr];
    const urlLines = halves.length > 1 && posterEm(addr, X.url) * X.url.size * T > w ? 2 : 1;
    const committee = (L !== "en" && site && site[`committee_${L}`]) || (site && site.committee) || "";
    return 176 + 16 + text(committee, w, X.committee) + 2 + urlLines * X.url.size * T * X.url.lh + 2 + text(tt("monthly.scan"), w, X.scan);
  };

  return { head, calendar, story, issue, dates, botm, weekly, foot };
}

/** The poster's type before its fit (areas/monthly.css, which this mirrors — a test reads both): the month's density's,
 *  and a Spanish poster's own: 21px, 18px with nine rows or more in its Dates block (its dates, the stores' offers, the
 *  price change). */
export const POSTER_START_PX = { roomy: 25, snug: 23, dense: 21.5, es: 21, esBusy: 18, esBusyRows: 9 };
export function posterStartPx(m, t) {
  if (m && m.lang === "es") return ((m.dates || []).length + posterExtras(m, t).length >= POSTER_START_PX.esBusyRows ? POSTER_START_PX.esBusy : POSTER_START_PX.es);
  return POSTER_START_PX[m && m.density] || POSTER_START_PX.snug;
}

/* The layouts whose blocks the build places from the estimate, as the template builds them (macros/monthly.njk
   poster()) and the stylesheet sizes them (areas/monthly.css, the column rule at its own value): each column's room
   inside its padding (w × h px), the space between its blocks, the padding a block has in it (the split's issue is a
   card: 20px 24px) and the blocks that never leave it; `moves`: the blocks that may sit in either column, the
   template's place first (their data-mp-move, without the dates: they stay where the template puts them — they are
   what is measured, never what gives way). Only the split today: its two columns run the poster's whole height, so
   what each holds is known before the fit; the other layouts' columns end where a band, a strip or a row under them
   begins, and their dates head their column or stand in that band (see above). */
const POSTER_COLUMNS = {
  split: {
    cols: {
      // .mp-l-split .mp-side: 404px wide, padding 42px 32px 32px 38px — the masthead, the calendar, the footer
      side: { w: 334, h: 1276, gap: 22, blocks: ["head", "calendar", "foot"] },
      // .mp-l-split .mp-content: the rest of the 1080px, padding 42px 44px 32px 42px — the issue, the dates
      content: { w: 590, h: 1276, gap: 20, blocks: ["issue", "dates"], pad: { issue: [20, 24] } },
    },
    moves: { story: ["content", "side"], botm: ["content", "side"], weekly: ["side", "content"] },
  },
};
// the blocks' place in the reading order (macros/monthly.njk data-mp-order): a column lists its blocks so
const POSTER_ORDER = { head: 0, calendar: 5, story: 10, issue: 20, dates: 30, botm: 40, weekly: 50, foot: 90 };

/**
 * Where the build puts the poster's blocks that may move (macros/monthly.njk poster(): data-mp-move, the build's place
 * first) → { at: { <block>: <column> }, move: { <block>: its data-mp-move — the build's column first }, T (the starting
 * type, px), cols: { <column>: { need, room, datesEnd } } — the estimate it was chosen on, px }.
 * Every arrangement of those blocks (each in one of its columns) is estimated (posterBlocks) and the first of these wins,
 * in this order: the dates end inside their column; the footer is whole (the QR code and the address: the column that
 * ends with it holds everything); the fewest px are cut at the columns' feet; the fewest blocks are away from the
 * template's place — so the template's own arrangement whenever it holds everything (every month of round 33c but
 * November 2026: its Spanish dates under the story, its English Book of the Month under the dates). A layout the build
 * does not place (POSTER_COLUMNS) keeps the template's arrangement: `at` is empty.
 */
export function posterPlaces(m, site, t) {
  const spec = POSTER_COLUMNS[m && m.layout];
  const T = posterStartPx(m, t);
  const out = { at: {}, move: {}, T, cols: {} };
  if (!spec) return out;
  const est = posterBlocks(m, site, t, T);
  const memo = new Map();
  // a block's height in a column (its padding there included; 0 when it is not on this poster: no Book of the Month …)
  const height = (col, b) => {
    const k = `${col}|${b}`;
    if (!memo.has(k)) {
      const c = spec.cols[col], [py, px] = (c.pad && c.pad[b]) || [0, 0];
      const h = est[b](c.w - 2 * px);
      memo.set(k, h ? h + 2 * py : 0);
    }
    return memo.get(k);
  };
  // a column's blocks in the reading order, stacked: what they need in all, and where the dates end (none: null)
  const measure = (col, at) => {
    const c = spec.cols[col];
    const blocks = [...c.blocks, ...Object.keys(at).filter((b) => at[b] === col)].sort((a, b) => POSTER_ORDER[a] - POSTER_ORDER[b]);
    let y = 0, datesEnd = null;
    for (const b of blocks) {
      const h = height(col, b);
      if (!h) continue;
      y += (y ? c.gap : 0) + h;
      if (b === "dates") datesEnd = y;
    }
    return { need: Math.round(y), room: c.h, datesEnd: datesEnd === null ? null : Math.round(datesEnd), foot: blocks.includes("foot") };
  };
  // every arrangement, the template's first (each block's first column before its others, in the reading order)
  const movers = Object.keys(spec.moves).sort((a, b) => POSTER_ORDER[a] - POSTER_ORDER[b]);
  let all = [{}];
  for (const b of movers) all = all.flatMap((a) => spec.moves[b].map((col) => ({ ...a, [b]: col })));
  // (a score before another: the first of its numbers that differs is smaller — a tie keeps the earlier arrangement)
  const ahead = (a, b) => { const i = a.findIndex((v, k) => v !== b[k]); return i >= 0 && a[i] < b[i]; };
  let best = null;
  for (const at of all) {
    const cols = Object.fromEntries(Object.keys(spec.cols).map((col) => [col, measure(col, at)]));
    const list = Object.values(cols);
    const score = [
      list.some((c) => c.datesEnd !== null && c.datesEnd > c.room) ? 1 : 0,   // a date cut
      list.some((c) => c.foot && c.need > c.room) ? 1 : 0,                    // the footer cut
      list.reduce((s, c) => s + Math.max(0, c.need - c.room), 0),             // px cut in all
      movers.filter((b) => at[b] !== spec.moves[b][0]).length,                // blocks away from the template's place
    ];
    if (!best || ahead(score, best.score)) best = { at, cols, score };
  }
  out.at = best.at;
  out.move = Object.fromEntries(movers.map((b) => [b, [best.at[b], ...spec.moves[b].filter((c) => c !== best.at[b])].join(" ")]));
  for (const [col, c] of Object.entries(best.cols)) out.cols[col] = { need: c.need, room: c.room, datesEnd: c.datesEnd };
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
 * A theme that is a machine translation (a Grapevine theme in Spanish, a La Viña one in English) comes with the
 * magazine's own words — on the next line, or "translation / original" in a deadline — and the message ends with
 * the site's note that some titles were translated automatically (as the monthly digest's e-mail does).
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
  let mt = false;     // a machine-translated title was written: the note above the footer
  // a committee meeting's guest speaker on a line of its own under it: "Guest speaker: Rick W. — “…”" (its topic in
  // the other language's words on the next line when they differ)
  const speakerLines = (sp, others) => {
    if (!sp) return [];
    const lines = [`  ${sp.topic ? t("monthly.msg_speaker", main, { name: sp.name, topic: sp.topic }) : t("committee.meeting.speaker", main, { name: sp.name })}`];
    for (const o of others) if (o && o.topic && o.topic !== sp.topic) lines.push(`  “${o.topic}”`);
    return lines;
  };

  // Masthead: "Grapevine & La Viña · NETA 65 — October 2026" + the tagline
  const title = `${both("monthly.kicker")} — ${uniq(Ls.map((l) => mm[l].title)).join(" / ")}`;
  out.push(wa ? `*${title}*` : title, wa ? `_${both("monthly.tagline")}_` : both("monthly.tagline"), "");

  // 📖 In the magazines: each magazine's theme (the page language's first) and its stories on the site
  const magLines = [];
  for (const p of main === "es" ? ["lv", "gv"] : ["gv", "lv"]) {
    const x = m[p];
    if (!x || !x.theme) continue;
    const v = iss.find((i) => i.pub === p);
    const issue = (p === "lv" && issueName(x.key, "lv", main, true)) || x.label;
    let line = t(p === "gv" ? "report.i_gv" : "report.i_lv", main, { issue, theme: x.theme });
    if (v && v.count) line += ` — ${t(v.count === 1 ? "read.n_stories_one" : "read.n_stories", main, { n: v.count })}${v.free ? ` · ${t("community.wn.free_n", main, { n: v.free })}` : ""}`;
    magLines.push(`${bullet} ${line}`);
    const others = Ls.slice(1).map((l) => mm[l][p]).filter((o) => o && o.theme && o.theme !== x.theme);
    for (const o of others) magLines.push(`  “${o.theme}”`);
    // one language: a machine translation's original words (the magazine's own) under it
    if (!others.length && x.machine && x.orig && x.orig !== x.theme) magLines.push(`  “${x.orig}”`);
    if (x.machine || others.some((o) => o.machine)) mt = true;
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
      out.push(`${bullet} ${when} — ${both("monthly.committee")} (${d.platform || both("monthly.online")}) — ${both("monthly.all_welcome")}`);
      out.push(...speakerLines(d.speaker, Ls.slice(1).map((l) => ((mm[l].dates || []).find((x) => x.id === d.id) || {}).speaker)));
      continue;
    }
    const bits = [when];
    if (d.kind === "recurring") bits.push(both("report.e_monthly"));
    if (d.tentative) bits.push(both("report.e_tbc"));
    // the place once: most titles already name the city ("Writing Workshop — Mansfield"; dateRow.place);
    // an event that can be joined online says "Online" too, after its place when it has one ("Riverside, CA ·
    // Online"; La Viña's monthly workshop on Zoom: "Online"), as the poster and the page's row do
    const where = [d.place, d.online ? both("monthly.online") : ""].filter(Boolean).join(" · ");
    out.push(`${bullet} ${bits.join(" · ")} — ${d.title}${where ? ` — ${where}` : ""}`);
    for (const l of Ls.slice(1)) { const o = (mm[l].dates || []).find((x) => x.id === d.id); if (o && o.title && o.title !== d.title) out.push(`  ${o.title}`); }
  }
  if (!rows.length) out.push(both(cur && (m.dates || []).length ? "monthly.no_more_dates" : "monthly.no_dates"));
  // … written like the rows above: "Next committee meeting: Wed, Nov 18 · 7–8 PM Central — Google Meet" (in the
  // middle of a line, after the colon, Spanish goes on in lower case: "Próxima reunión del comité: mié, 18 …")
  const nc = cur && nw ? nw.nextCommittee : null;
  if (nc && !nc.thisMonth) {
    const wd = chip(nc.ymd, main).wd;
    const when = [`${main === "es" ? wd.toLowerCase() : wd}, ${nc.dayLabel}`, nc.time ? `${nc.time} ${nc.zone}` : ""].filter(Boolean).join(" · ");
    out.push(`${bullet} ${both("monthly.next_meeting")}: ${when} — ${nc.platform}`);
    out.push(...speakerLines(nc.speaker, Ls.slice(1).map((l) => ctx.nw && ctx.nw[l] && ctx.nw[l].nextCommittee && ctx.nw[l].nextCommittee.speaker)));
  }
  out.push(`  ${t("monthly.msg_events", main, { url: url("/events/") })}`, `  ${t("monthly.msg_join", main, { url: url(COMMITTEE_MEETING_PATH) })}`, "");

  // 🔁 Every week: the weekly open meetings (+ this month: the Grapevine meetings near you)
  const weekly = m.weekly || [];
  const g = cur ? nw.gvm : null;
  if (weekly.length || g) {
    out.push(head(both("monthly.every_week"), "🔁"));
    // "— los jueves a las 11:00 a. m.": the data's "Los jueves …" goes on in lower case after the dash (midSentence)
    for (const w of weekly) out.push(`${bullet} ${t("report.o_line", main, { title: w.title, when: midSentence(w.when, main) })}${w.startsLabel ? ` — ${t("report.o_starts", main, { date: w.startsLabel })}` : ""}`);
    if (weekly.length) out.push(`  ${t("report.o_more", main, { url: url("/meetings/#weekly-open") })}`);
    if (g) {
      const ours = t(g.inArea === 1 ? "committee.gvm.count_one" : "committee.gvm.count", main, { n: g.inArea });
      out.push(`${bullet} ${both("committee.gvm.home_title")}: ${t(g.nearby ? "committee.gvm.home_text" : "committee.gvm.home_text_area", main, { ours, nearby: g.nearby })}`);
      out.push(`  ${url("/meetings/#grapevine-meetings")}`);
    }
    out.push("");
  }

  // ✍️ Share your story: Grapevine's deadlines and open topics (no deadline: its departments and what it always
  // needs, in each language of the message, like its themes); La Viña's deadlines (its theme in its own Spanish
  // words, like its topics) and open topics — La Viña first in Spanish —; the phone story lines (La Viña first in
  // Spanish), how to send one
  const ap = (nw && nw.audio) || {};
  const phones = (main === "es" ? [["La Viña", ap.lv], ["Grapevine", ap.gv]] : [["Grapevine", ap.gv], ["La Viña", ap.lv]]).filter(([, d]) => d);
  const deadlines = m.deadlines || [];
  const lvDeadlines = m.lvDeadlines || [];
  const lvTopics = m.lvTopics || [];
  const gvTopics = m.gvTopics || [];
  if (deadlines.length || lvDeadlines.length || lvTopics.length || gvTopics.length || phones.length) {
    out.push(head(both("monthly.msg_stories"), "✍️"));
    // a theme in each language ("Diversión en sobriedad / Fun in Sobriety"); a machine translation with Grapevine's
    // own words after it in one language too
    const gvLines = deadlines.map((d) => {
      const rows = Ls.map((l) => (mm[l].deadlines || []).find((x) => x.id === d.id) || {});
      if (rows.some((x) => x.machine)) mt = true;
      const themes = uniq([...rows.map((x) => x.theme), d.machine ? d.themeEn : ""]);
      return `${bullet} ${t("monthly.msg_deadline", main, { date: d.dueLabel, theme: themes.join(" / "), issue: d.issueLabel })}`;
    });
    if (gvTopics.length) {
      const words = gvTopics.map((x) => {
        const rows = Ls.map((l) => (mm[l].gvTopics || []).find((y) => y.id === x.id) || {});
        if (rows.some((y) => y.machine)) mt = true;
        return `“${uniq(rows.map((y) => y.text || x.en)).join(" / ")}”`;
      });
      gvLines.push(`${bullet} ${t("monthly.msg_gv_topics", main)} ${words.join(", ")}`);
    }
    const lvLines = lvDeadlines.map((d) => `${bullet} ${t("monthly.msg_deadline_lv", main, { date: d.dueLabel, theme: d.theme, issue: d.issueLabel })}`);
    if (lvTopics.length) lvLines.push(`${bullet} ${t("monthly.msg_lv_topics", main)} ${lvTopics.map((x) => `“${x.es}”`).join(", ")}`);
    out.push(...(main === "es" ? [...lvLines, ...gvLines] : [...gvLines, ...lvLines]));
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
  // 📢 a price change AA Grapevine announced, in the months its notice meets (monthModel `price`): "Grapevine and La
  // Viña prices change on January 1, 2027" before it, "New … prices as of …" in its month — a heads-up for the
  // groups' budget for Grapevine and La Viña books and subscriptions; what changes is on /shop/ (#price-changes)
  if (m.price) {
    const key = m.price.kind === "before" ? "shop.pc_line_before" : "shop.pc_line_after";
    out.push(`${wa ? "📢 " : ""}${both(key, (l) => ({ date: dayLabel(m.price.effective, l) }))}: ${url("/shop/#price-changes")}`);
  }
  if (offers.length || (cur && nw.subsFrom) || m.price) out.push("");
  // 📦 an offer the stores announced, in the months its days meet (monthModel `offers`; this month only the ones not
  // over yet), under its own heading — apart from the Book of the Month above, so the two never read as one deal
  // (Grapevine's free shipping can't be combined with any other offer): "Free shipping at the Grapevine and La Viña
  // stores", then "November 1 – December 31, 2026: …/shop/#offers-free-shipping-2026" ("Through December 31, 2026"
  // for an offer whose stores give no first day: show_starts false) — its title from the settings, in each language;
  // what each store says is in its own section of /shop/ (#offers-<key>: every offer has that address). 🎁 for an
  // offer with `icon: gift` (a parcel by a gift offer would read as shipping), else 📦
  const storeOffers = (m.offers || []).filter((o) => !cur || !o.past);
  for (const o of storeOffers) {
    const title = (l) => ((mm[l].offers || []).find((x) => x.key === o.key) || o).title;
    const days = uniq(Ls.map((l) => offerDates(o.showStarts === false ? "" : o.starts, o.ends, l, t)))
      .map((d) => d.charAt(0).toUpperCase() + d.slice(1));
    out.push(head(uniq(Ls.map(title)).join(" / "), o.icon === "gift" ? "🎁" : "📦"),
      `${days.join(" / ")}: ${url(`/shop/#offers-${o.key}`)}`, "");
  }

  // the site's note on machine translation (the monthly digest's words), then 🖼️ the month's toolkit page (its
  // poster is there)
  if (mt) out.push(both("monthly.msg_machine"), "");
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

/** Where a month's calendar file is (src/pages/monthly-ics.11ty.js writes it there, m.icsUrl links it): beside the
 *  month's page, named for the month and language — the name a computer saves it under —
 *  "/monthly/2026-10/neta65-grapevine-2026-10-en.ics", "/es/monthly/2026-10/neta65-grapevine-2026-10-es.ics". */
export function icsPath(key, lang) {
  const L = lang === "es" ? "es" : "en";
  return `${L === "es" ? "/es" : ""}/monthly/${key}/neta65-grapevine-${key}-${L}.ics`;
}

/** Where a month's share picture is — the picture the link previews of WhatsApp, Facebook … show for the month's
 *  page (its og:image): a 1200 × 630 PNG of the top of its poster, beside the page — "/monthly/2026-10/share.png",
 *  "/es/monthly/2026-10/share.png" (a site path: base.njk adds the site's address and folder). */
export function sharePicturePath(key, lang) {
  return `${lang === "es" ? "/es" : ""}/monthly/${key}/share.png`;
}

/** A month page's HTML with a version in its share picture's address (og:image, twitter:image: "…/share.png?v=…") —
 *  the first 8 hex characters of a hash of what the picture is drawn from: the page's poster (its HTML: the month's
 *  words, dates, deadlines, themes, design) and the site's code version (the ?v= of its main.css: the styles, fonts and
 *  templates that draw it). The link previews that keep a picture by its address (Facebook, Messenger, LinkedIn,
 *  Slack…) fetch it again once the poster changes; an unchanged poster keeps its address. A page without a poster or
 *  without a share picture is returned as it is. (The mpShareVersion transform, below; scripts/ops/poster_share.py
 *  finds the pages by the address's path, whatever the ?v=.) The page's structured data (base.njk: the WebPage's
 *  primaryImageOfPage, "url":"…/share.png") gets the same address, so it never names another picture than og:image. */
export function shareVersioned(html) {
  const s = String(html == null ? "" : html);
  if (!s.includes('/share.png"')) return s;
  const poster = /<article\b[^>]*\bdata-mp-poster\b[\s\S]*?<\/article>/.exec(s);
  if (!poster) return s;
  const code = (/\/assets\/css\/main\.css\?v=([\w-]+)/.exec(s) || [])[1] || "";
  const v = crypto.createHash("sha256").update(code + "\n" + poster[0]).digest("hex").slice(0, 8);
  return s.replace(/(<meta (?:property="og:image"|name="twitter:image") content="[^"?]*\/monthly\/\d{4}-\d{2}\/share\.png)"/g, `$1?v=${v}"`)
    .replace(/("url":"[^"?]*\/monthly\/\d{4}-\d{2}\/share\.png)"/g, `$1?v=${v}"`);
}

/** Whether this build's month pages point at their share pictures: only when the build is asked to (POSTER_SHARE=1).
 *  The pictures are not made by the build: Website update (.github/workflows/update.yml) takes them with the
 *  runner's Chrome right after it (scripts/ops/poster_share.py), and builds the site again without POSTER_SHARE when
 *  they could not be made — so no page ever points at a picture that is not there. Every other build (a local one,
 *  the Code check) keeps the committee's card on the month pages. */
export function posterShareOn(env = process.env) {
  return /^(?:1|true)$/i.test(String((env && env.POSTER_SHARE) || "").trim());
}

/** The site's calendar events (committee.js normalizeEvents, as /events.ics has them) by id, for monthIcs: the
 *  window's months, and the month before — with (since round 37) the cancelled events (db.events.cancelled), as
 *  /events.ics has them too. */
export function monthIcsEvents(db = {}, site = {}, lang = "en", now = nowDate()) {
  const items = [...((db.events && db.events.items) || []), ...((db.events && db.events.cancelled) || [])];
  return new Map(normalizeEvents(items, site, lang === "es" ? "es" : "en", { monthsBack: 1, monthsAhead: WINDOW, now }).map((e) => [e.id, e]));
}

// A calendar entry with another link (since round 37: a series' date worked out from its rule, which has no page of
// its own, links to its series' page): its URL and the "Details: …" line of its description (shapeEvent writes the
// link into both).
function withDetailsUrl(ev, url) {
  if (!url || url === ev.detailsUrl) return ev;
  const from = String(ev.detailsUrl || "");
  return { ...ev, detailsUrl: url, calDescription: from ? String(ev.calDescription || "").split(from).join(url) : ev.calDescription };
}

/**
 * "Add this month's dates to my calendar": a month's dates as an iCalendar file — one static file per month and
 * language beside the month's page (src/pages/monthly-ics.11ty.js, at icsPath), linked from the page's Dates card
 * (m.icsUrl), so it needs no script and opens straight in a phone's calendar.
 *   events     the month's date rows (m.dates: the committee meeting, the monthly series, the other events — this
 *              month only the ones not over yet, as in its message), written exactly as /events.ics writes them
 *              (committee.js normalizeEvents + buildIcs: the same UID, description, joining details, guest
 *              speaker and link — a calendar that has both keeps one copy; a later month's date of a series,
 *              worked out from its rule, is written from the same record, its link its series' page: it has no
 *              page of its own — withDetailsUrl)
 *   deadlines  the story deadlines the page lists (Grapevine's, La Viña's), each an all-day entry on its day:
 *              "Story deadline: “Fun in Sobriety” — Grapevine", its issue and how to send a story (/contribute/)
 *   cancelled  (since round 37) the month's cancelled events (db.events.cancelled, which no date row lists — this
 *              month only the ones not over yet): "Cancelled: …", STATUS:CANCELLED, no reminder (buildIcs), so the
 *              entry a member added with an earlier copy of the file is corrected when they add it again
 * The calendar's name is the month's ("NETA 65 Grapevine & La Viña — October 2026"). RFC 5545 as buildIcs
 * writes it: CRLF line ends, lines folded at 75 octets, TEXT escaped, UTC times, DATE values for all-day entries.
 * (SEQUENCE and DTSTAMP are buildIcs's, as in /events.ics.) Each entry has the site's one reminder (buildIcs
 * alarms: an hour before; 9 AM the day before a deadline or an all-day event) — but a cancelled event's.
 */
export function monthIcs(m, db = {}, site = {}, lang = "en", now = nowDate(), normalized = null) {
  const L = lang === "es" ? "es" : "en";
  const t = (k, v) => H.translateKey(k, L, v);
  const abs = (p) => String(site.url || "").replace(/\/+$/, "") + (L === "es" ? "/es" : "") + p;
  const opt = { monthsBack: 1, monthsAhead: WINDOW, now };
  // (normalized: the site's calendar events of this language, when the caller already has them — monthIcsEvents)
  const all = normalized || monthIcsEvents(db, site, L, now);
  const events = [];
  for (const d of m.dates || []) {
    if (m.isCurrent && d.past) continue;
    // a date the site's calendar lists; else (a later month's date of a series, worked out from its rule) its record
    let ev = all.get(d.id) || (d.kind !== "committee" && d.src ? normalizeEvents([d.src], site, L, opt).find((e) => e.id === d.id) : null);
    // (since round 37 an entry links to its event's own page — shapeEvent's detailsUrl; a date worked out from the
    // rule has none — events.json does not list it, so no page is written for it —: its series' page, else /events/;
    // a series whose own page is one of ours, the Grapevine Meeting's section of /meetings/, keeps that)
    if (ev && !all.has(d.id) && String(ev.detailsUrl || "").endsWith(`/events/${ev.anchor}/`)) {
      const page = eventLink(d.src, L, eventLinkPlan(db, site), { page: true }) || (L === "es" ? "/es/events/" : "/events/");
      ev = withDetailsUrl(ev, String(site.url || "").replace(/\/+$/, "") + page);
    }
    if (ev) events.push(ev);
  }
  // (since round 37) the month's cancelled events (db.events.cancelled — never among its dates): their entry as
  // /events.ics writes it, marked cancelled and with no reminder (buildIcs), so a member who adds the month again gets
  // the entry they had corrected — this month, only those not over yet
  for (const ev of all.values()) {
    if (ev.cancelled && ev.monthKey === m.key && !(m.isCurrent && ev.past) && !events.includes(ev)) events.push(ev);
  }
  const dls = [...(m.deadlines || []).map((d) => deadlineEntry(d, "gv", L, site)), ...(m.lvDeadlines || []).map((d) => deadlineEntry(d, "lv", L, site))];
  const list = [...events, ...dls].sort((a, b) => (a.allDay ? Date.parse(a.startYmd + "T12:00:00Z") : a.startMs)
    - (b.allDay ? Date.parse(b.startYmd + "T12:00:00Z") : b.startMs) || String(a.title).localeCompare(String(b.title)));
  return buildIcs(list, {
    lang: L, now, alarms: true,
    name: t("monthly.ics_name", { month: m.label }),
    description: t("monthly.ics_desc", { month: m.label, url: abs(`/monthly/${m.key}/`) }),
    url: abs(`/monthly/${m.key}/`),
    categoryLabel: (ev) => t(ev.group === "deadline" ? "monthly.ics_cat_deadline" : `committee.events.group.${ev.group}`),
  });
}

/**
 * A story deadline (a storyDeadlines row) as a calendar entry — the month files' (monthIcs) and the deadlines
 * calendar's (deadlinesIcs; /contribute/'s "Add to my calendar": deadlineCals): an all-day entry on its day,
 * "Story deadline: “Fun in Sobriety” — Grapevine", its issue and how to send a story (/contribute/#deadlines). The
 * same UID everywhere — `deadline-<the theme's id>` (buildIcs adds "-es" in Spanish and "@neta65-gvlv") — so a
 * calendar that has a month's file and the deadlines calendar, or a deadline added twice, keeps one copy, and a
 * moved deadline moves. (A machine-translated theme with Grapevine's own words after it, as in the month's message.)
 */
export function deadlineEntry(d, pub, lang = "en", site = {}) {
  const L = lang === "es" ? "es" : "en";
  const t = (k, v) => H.translateKey(k, L, v);
  const contribute = String(site.url || "").replace(/\/+$/, "") + (L === "es" ? "/es" : "") + "/contribute/#deadlines";
  return {
    id: d.id, pub, uid: `deadline-${slug(d.id)}`, group: "deadline", allDay: true, startYmd: d.due, endYmd: d.due,
    title: t("monthly.ics_deadline", { theme: d.machine && d.themeEn && d.themeEn !== d.theme ? `${d.theme} / ${d.themeEn}` : d.theme,
      pub: t(pub === "lv" ? "monthly.lv_spanish" : "monthly.gv_english") }),
    calDescription: `${t("monthly.for_issue", { issue: d.issueLabel })}.\n\n${t("monthly.msg_how", { url: contribute })}`,
    calLocation: "", detailsUrl: contribute, tentative: false,
  };
}

/** Every story deadline still open — both magazines', soonest first — as calendar entries (deadlineEntry), from the
 *  site's editorial calendar (db.editorial). A theme the magazine dropped (status "gone") is left out, so it leaves
 *  the subscribers' calendars too; La Viña's suggested topics have no date and are never in it. `now`: the build's
 *  clock (nowDate) — a deadline is open through its day, in Central time. */
export function openDeadlines(db = {}, site = {}, lang = "en", now = nowDate()) {
  const L = lang === "es" ? "es" : "en";
  const editorial = ((db.editorial && db.editorial.items) || []).filter((i) => i && i.status !== "gone");
  const { gv, lv } = storyDeadlines(editorial, L, { today: chicagoYmd(now) });
  return [...gv.map((d) => deadlineEntry(d, "gv", L, site)), ...lv.map((d) => deadlineEntry(d, "lv", L, site))]
    .sort((a, b) => a.startYmd.localeCompare(b.startYmd) || String(a.title).localeCompare(String(b.title)));
}

/** Where the deadlines calendar is: "/deadlines.ics", "/es/deadlines.ics" (src/pages/deadlines-ics.11ty.js writes it;
 *  committee.js cmSubscribe "deadlines" links it). */
export function deadlinesIcsPath(lang) {
  return lang === "es" ? "/es/deadlines.ics" : "/deadlines.ics";
}

/**
 * "Story deadlines in my calendar": the text of /deadlines.ics and /es/deadlines.ics (src/pages/deadlines-ics.11ty.js)
 * — every open story deadline of both magazines (openDeadlines), a calendar a member subscribes to once (the card on
 * /contribute/#deadlines-calendar, committee.js cmSubscribe "deadlines"). It updates itself when a magazine adds,
 * moves or drops a theme: the same UIDs, a higher SEQUENCE (buildIcs). Each deadline has the site's one reminder,
 * 9 AM the day before (buildIcs alarms; Google Calendar ignores it — the card says so). RFC 5545 as buildIcs writes
 * it; its name, description and category in the file's language. No deadline open: a calendar with no entry — only
 * the site's zone (a VTIMEZONE: RFC 5545 wants one component at least; buildIcs).
 */
export function deadlinesIcs(db = {}, site = {}, lang = "en", now = nowDate()) {
  const L = lang === "es" ? "es" : "en";
  const t = (k, v) => H.translateKey(k, L, v);
  const page = String(site.url || "").replace(/\/+$/, "") + (L === "es" ? "/es" : "") + "/contribute/#deadlines";
  return buildIcs(openDeadlines(db, site, L, now), {
    lang: L, now, alarms: true,
    name: t("read.dlcal.name"),
    description: t("read.dlcal.desc", { url: page }),
    url: page,
    categoryLabel: () => t("monthly.ics_cat_deadline"),
  });
}

/** /contribute/'s "Add to my calendar" beside each deadline (contribute.njk dlCalMenu): { <the theme's id>: { gcal,
 *  outlook, ics } } — Google Calendar's and Outlook.com's "add" links (committee.js calendarLinks) and the .ics
 *  download's data (app.js GV.ics: the UID and words of /deadlines.ics, and its reminder). A theme without an open
 *  deadline has none, and its row no button. */
export function deadlineCals(db = {}, site = {}, lang = "en", now = nowDate()) {
  const L = lang === "es" ? "es" : "en";
  const out = {};
  for (const e of openDeadlines(db, site, L, now)) {
    out[e.id] = {
      ...calendarLinks(e),
      ics: { uid: `${e.uid}${L !== "en" ? "-" + L : ""}@neta65-gvlv`, title: e.title, start: e.startYmd, end: e.endYmd, allDay: true,
        description: e.calDescription, url: e.detailsUrl, filename: `story-deadline-${e.startYmd}` },
    };
  }
  return out;
}

export default function (eleventyConfig, helpers) {
  if (helpers && helpers.translateKey) H = { ...H, translateKey: helpers.translateKey };
  // the build's one "now" (nowDate): taken by its first call, let go when the build is done — the next build
  // (`npm start` rebuilds) takes its own
  eleventyConfig.on("eleventy.after", endBuildClock);
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
  // A sentence's first word inside another sentence (midSentence): /about/'s "Próxima reunión: miércoles, 18 de
  // noviembre…" — {{ meeting.next.start | fmtDate(lang, "long") | midSentence(lang) }} (app.js GV.meetingLines
  // writes it the same way when it rolls the line on)
  eleventyConfig.addFilter("midSentence", (s, lang) => midSentence(s, lang));
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
  // The poster's rows after its dates (macros/monthly.njk dates()): {% for x in m | mpPosterExtras %}
  eleventyConfig.addFilter("mpPosterExtras", (m) => posterExtras(m, (key2, lang, vars) => H.translateKey(key2, lang, vars)));
  // Where the poster's blocks that may move are built (macros/monthly.njk poster(), the split's story, Book of the
  // Month and weekly meetings): {% set pp = m | mpPosterPlaces(site) %} → pp.at.story "content" | "side", pp.move.story
  // its data-mp-move (posterPlaces)
  eleventyConfig.addFilter("mpPosterPlaces", (m, site) => posterPlaces(m || {}, site || {}, (key2, lang, vars) => H.translateKey(key2, lang, vars)));
  eleventyConfig.addFilter("mpQr", (url, label = "") => qrSvg(url, { label, cls: "mp-qr-svg", margin: 2 }));
  // A month page's share picture (its ogImage, monthly-month.njk): {{ mpage.key | mpShareImage(mpage.lang) }} — the
  // site path of its share.png in a build asked for it (POSTER_SHARE=1), else "" (the page keeps the committee's card)
  eleventyConfig.addFilter("mpShareImage", (key, lang) => (posterShareOn() && /^\d{4}-\d{2}$/.test(String(key || ""))
    ? sharePicturePath(String(key), lang) : ""));
  // …and, once the page is made (its poster is in it), a version in that address: shareVersioned
  eleventyConfig.addTransform("mpShareVersion", function (content) {
    const out = (this.page && this.page.outputPath) || this.outputPath;
    return typeof out === "string" && out.endsWith(".html") && typeof content === "string" ? shareVersioned(content) : content;
  });
  eleventyConfig.addFilter("mpGuides", (pdfs, lang) => repGuides(pdfs, lang));
  // A month's calendar file (src/pages/monthly-ics.11ty.js): this.mpIcs(key, db, carry, site, lang) — the site's
  // calendar events worked out once per language and build (the 26 files share them)
  let icsEvents = new Map();
  eleventyConfig.on("eleventy.before", () => { icsEvents = new Map(); });
  eleventyConfig.addFilter("mpIcs", (key, db, carry, site, lang) => {
    const L = lang === "es" ? "es" : "en";
    const now = nowDate();
    if (!icsEvents.has(L)) icsEvents.set(L, monthIcsEvents(db || {}, site || {}, L, now));
    return monthIcs(model(key, db, carry, site, L), db || {}, site || {}, L, now, icsEvents.get(L));
  });
  // /contribute/'s "Add to my calendar" beside each story deadline: {% set dlCal = db | mpDeadlineCals(site, lang) %}
  // → { <theme id>: { gcal, outlook, ics } } (deadlineCals: the entries of /deadlines.ics)
  eleventyConfig.addFilter("mpDeadlineCals", (db, site, lang) => deadlineCals(db || {}, site || {}, lang, nowDate()));
}
