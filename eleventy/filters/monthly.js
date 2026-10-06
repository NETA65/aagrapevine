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
//   db.editorial   the magazines' themes per issue (extra.issue_key: Grapevine's editorial calendar, La Viña's
//                  yearly themes document) until the issue is out, story deadlines (extra.deadline — both
//                  magazines), La Viña's evergreen suggested topics (extra.evergreen)
//   db.articles    issues[] — the Grapevine issue on the stands (its own theme, once it is out),
//                  La Viña's bimonthly issue; items — the stories (counts, free to read, and the theme
//                  and La Viña's issue when issues[] has moved on to the next one: issueTheme)
//   carry          config/carry.yml — the 10 ways and the "put it to work" tips per GV issue
//   db.events      committee meetings, the monthly recurring events (CityWide Dallas booth …),
//                  workshops and assemblies (content/events, dated Drive flyers, the outside calendars)
//   db.weekly_open the Weekly Open meetings (La Viña's from its extra.starts date)
//   db.shop.botm   Book of the Month offers (starts / ends window)
//   db.shop.price_changes  a price change AA Grapevine announced (config/site.yml price_changes): the months
//                  from its announcement through its notice pass it on in their message (model `price`), and
//                  the current month's "Keep up all month" has its line (monthly-month.njk)
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
//            mpQr(url, label)                           → QR code SVG (qrSvg from community.js)
//            mpGuides(pdfs, lang)                       → the GVR / RLV guides in the Library (repGuides)
//            mpIcs(key, db, carry, site, lang)          → the month's dates as an iCalendar file (monthIcs)
// Everything is built once per build and language (the hub and 26 month pages share it).
// Dev/test:  MONTHLY_NOW=2026-12-15 (or an instant: 2026-10-22T06:00:00Z) fixes "now" — the window,
//            the "over" marks, the next committee meeting and the live extras.

// (community.js imports this file too: the cycle is safe, both only call each other's functions.)
import { qrSvg, issueLabel, issueInSentence, issueLabelOf } from "./community.js";
import { chicagoDayEndMs, eventEndMs, gvMeetings, announcementList, normalizeEvents, buildIcs } from "./committee.js";
import { monthlyRule, TZ } from "../../eleventy.config.js";
import { overnight, wallInstant } from "../central-time.js";
import { shopFromMonthly, money, shopPriceChangeIn, dayLabel } from "./shop.js";
import { groupIssues, issueName } from "./read.js";

// Helpers handed over by eleventy.config.js (translateKey …); the fallback keeps the module usable
// from a plain `node` script too (as report.js).
let H = { translateKey: (k) => k };

// (TZ: config/site.yml site.timezone — America/Chicago — from eleventy.config.js)
const LOC = { en: "en-US", es: "es-US" };
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
 *  recurring event's rule) → { ymd, start, end } (UTC ISO), null on a skip date or when the month has no such
 *  day. Read the way scripts/sync/meeting.py reads it (eleventy.config.js monthlyRule): "5pm", "7:00 PM",
 *  "sábado", "third" … never stop the build or move the time by 12 hours, an end that is missing or not
 *  after the start makes it one hour long (MonthlyRule.span) — as on /events/ and /meetings/ — and an overnight
 *  end ("22:00"–"01:00", central-time.js overnight) is the next morning. */
export function meetingByRule(key, meeting = {}) {
  const rule = monthlyRule(meeting && typeof meeting === "object" ? meeting : {});
  const wd = WD[String(rule.weekday || "wednesday").toLowerCase()] ?? 3;
  const n = Number(rule.week_of_month || 3);
  const [y, m] = key.split("-").map(Number);
  const d = nthWeekday(y, m - 1, wd, n);
  if (!d) return null;
  const ymd = `${key}-${pad(d)}`;
  const skip = new Set(rule.skip_dates || []);
  if (skip.has(ymd)) return null;
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
 *   href      where its title links: the committee meeting → /meetings/#committee-meeting (the one home
 *             of its Zoom details); anything else → its own page (url) or /events/. A monthly series
 *             keeps its own link: its later dates are folded on /events/, where an anchor could land on
 *             a hidden card. external = another site.
 *   category  the data's category (eventTone keeps the Grapevine / La Viña calendars' colours)
 *   host      "lv" / "gv" for La Viña's or Grapevine's own event (extra.host — La Viña's monthly workshop):
 *             eventTone gives it that magazine's colour; "" for ours
 *   place     the city to show after the title: "" when the title already names it ("Writing Workshop —
 *             Mansfield", "booth at CityWide Dallas") — the page's row, the poster and the message say a
 *             place once
 *   online    it can be joined online (an online link, or "Zoom" as its place): without a city the row,
 *             the poster and the message say "Online" there
 * extra: { kind: "committee" | "recurring" | "event", … }
 * (src, not enumerable: the event record the row is made from — the month's calendar file writes it as
 * /events.ics does, monthIcs)
 */
function dateRow(e, L, ctx, extra = {}) {
  const d = eventDays(e);
  const ex = e.extra || {};
  const timed = !ex.all_day && ex.start && !isYmd(ex.start);
  const shownDay = d.start < ctx.first ? ctx.first : d.start;
  const overAt = iso(eventEndMs(e));
  const href = extra.kind === "committee" ? "/meetings/#committee-meeting" : e.url || "/events/";
  const title = tr(e, "title", L);
  const city = clean(ex.city);
  return Object.defineProperty({
    id: e.id, title, url: e.url || "", href, external: /^https?:/.test(href), category: e.category || "",
    ymd: d.start, endYmd: d.end, chip: chip(shownDay, L), dayLabel: shortDate(shownDay, L, ctx.year), day: longDay(d.start, L),
    endDay: d.end !== d.start ? longDay(d.end, L) : "",
    range: d.end !== d.start ? dayRange(d.start, d.end, L) : "",
    time: timed ? `${timeRange(ex.start, ex.end, L)}` : "", zone: timed ? ctx.zone : "",
    city, place: city && !title.toLowerCase().includes(city.toLowerCase()) ? city : "",
    online: !!ex.online || !!ex.online_url || /zoom/i.test(ex.location || ""),
    host: ex.host === "lv" || ex.host === "gv" ? ex.host : "",
    tentative: !!ex.tentative, overAt, past: !!overAt && Date.parse(overAt) <= ctx.nowMs, ...extra,
  }, "src", { value: e });
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
      machine: L === "es" && (i.machine || []).includes("es") && clean(tr(i, "title", L)) !== clean(i.title),
    }));

  /* La Viña's story deadlines in the same days (its yearly themes document: dated topics with an issue_key). The
     theme is La Viña's own words, in Spanish (lang "es" on every page); on the English pages its English words
     beside it when they differ (gloss; glossMachine when they are a machine translation). The issue inside a
     sentence: "May–June 2027" / "mayo–junio de 2027" — the same deadline reads the same on /contribute/, Home, the
     report and the slides, and La Viña's issue on these pages too (read.js issueName). */
  const lvDeadlines = editorial
    .filter((i) => i && i.status !== "gone" && i.extra && i.extra.publication === "lv" && i.extra.issue_key && i.extra.deadline
      && i.extra.deadline >= first && i.extra.deadline <= nextFirst && i.extra.deadline >= today)
    .sort((a, b) => a.extra.deadline.localeCompare(b.extra.deadline) || String(a.title).localeCompare(String(b.title)))
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
  // text: the topic in the page language (machine: a machine translation of La Viña's Spanish words)
  const lvTopicList = topics.map((i) => {
    const text = tr(i, "title", L), es = tr(i, "title", "es");
    return { id: i.id, es, text, machine: L !== "es" && text !== es && (i.machine || []).includes(L) };
  });

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
    const tpl = series[series.length - 1];
    // the rule as build_data understood it (extra.rule: week_of_month 1–5 / -1, English weekday, "HH:MM"
    // start and the end as used — "Saturdays", "2nd", "5 PM" or no end all read as the sync read them);
    // only skip_dates come from the settings
    const rule = (tpl.extra && tpl.extra.rule) || sp;
    const r = meetingByRule(key, { week_of_month: rule.week_of_month, weekday: rule.weekday, start: rule.start, end: rule.end, skip_dates: sp.skip_dates || [] });
    if (!r) continue;
    recIn.push({ ...tpl, id: `ev:recurring:${sp.key}:${r.ymd}`, date: r.start, extra: { ...tpl.extra, start: r.start, end: r.end } });
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
  for (const d of [...deadlines, ...lvDeadlines]) mark(d.due, "deadline");
  const weekdays = Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(LOC[L], { weekday: "narrow", timeZone: "UTC" }).format(new Date(Date.UTC(2026, 1, 1 + i))));
  const calendar = { offset, days: lastDay(key), marks, weekdays };

  /* Density: how much the poster holds (the CSS tightens type for busy months). La Viña's deadlines are on the
     Spanish poster only (one compact line each) */
  const load = deadlines.length * 3 + Math.min(tips.length, 3) * 2 + botm.length * 1.5 + dates.length * 1.2 + weekly.length
    + (L === "es" ? 2 + lvDeadlines.length * 2 : 0);
  const density = load > 20 ? "dense" : load > 15 ? "snug" : "roomy";

  const path = `/monthly/${key}/`;
  const url = (L === "es" ? "/es" : "") + path;
  return {
    key, lang: L, year, month: mNum, first, last,
    name: cap(monthName(key, L)), monthName: monthName(key, L), label: monthLabel(key, L), title: cap(monthLabel(key, L)),
    design: design.id, layout: design.layout, density,
    isCurrent: key === today.slice(0, 7),
    gv, lv, tips, deadlines, lvDeadlines, lvTopics: lvTopicList, botm, botmOffer,
    committee, recurring, events: other, dates, weekly, calendar,
    // a price change AA Grapevine announced whose notice meets this month (shop.js shopPriceChangeIn): { kind
    // "before" | "after", effective } — the month's message passes it on (monthMessage)
    price: priceMention(db.shop, first, last),
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
 *                  else the rule), then next month's — { ymd, day, dayLabel, time, zone, platform, overAt,
 *                  thisMonth } or null. (Not src/_data/meeting.js: that one ignores MONTHLY_NOW.)
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
      out.push(`${bullet} ${when} — ${both("monthly.committee")} (${d.platform}) — ${both("monthly.all_welcome")}`);
      continue;
    }
    const bits = [when];
    if (d.kind === "recurring") bits.push(both("report.e_monthly"));
    if (d.tentative) bits.push(both("report.e_tbc"));
    // the place once: most titles already name the city ("Writing Workshop — Mansfield"; dateRow.place);
    // an online event without a city says "Online" (La Viña's monthly workshop on Zoom), as the poster does
    const where = d.place || (!d.city && d.online ? both("monthly.online") : "");
    out.push(`${bullet} ${bits.join(" · ")} — ${d.title}${where ? ` — ${where}` : ""}`);
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

  // ✍️ Share your story: Grapevine's deadlines; La Viña's deadlines (its theme in its own Spanish words, like its
  // topics) and open topics (no deadline) — La Viña first in Spanish —; the phone story lines (La Viña first in
  // Spanish), how to send one
  const ap = (nw && nw.audio) || {};
  const phones = (main === "es" ? [["La Viña", ap.lv], ["Grapevine", ap.gv]] : [["Grapevine", ap.gv], ["La Viña", ap.lv]]).filter(([, d]) => d);
  const deadlines = m.deadlines || [];
  const lvDeadlines = m.lvDeadlines || [];
  const lvTopics = m.lvTopics || [];
  if (deadlines.length || lvDeadlines.length || lvTopics.length || phones.length) {
    out.push(head(both("monthly.msg_stories"), "✍️"));
    // a theme in each language ("Diversión en sobriedad / Fun in Sobriety"); a machine translation with Grapevine's
    // own words after it in one language too
    const gvLines = deadlines.map((d) => {
      const rows = Ls.map((l) => (mm[l].deadlines || []).find((x) => x.id === d.id) || {});
      if (rows.some((x) => x.machine)) mt = true;
      const themes = uniq([...rows.map((x) => x.theme), d.machine ? d.themeEn : ""]);
      return `${bullet} ${t("monthly.msg_deadline", main, { date: d.dueLabel, theme: themes.join(" / "), issue: d.issueLabel })}`;
    });
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
  // Viña prices change on January 1, 2027" before it, "New … prices since …" in its month — a heads-up for the
  // groups' budget for Grapevine and La Viña books and subscriptions; what changes is on /shop/ (#price-changes)
  if (m.price) {
    const key = m.price.kind === "before" ? "shop.pc_line_before" : "shop.pc_line_after";
    out.push(`${wa ? "📢 " : ""}${both(key, (l) => ({ date: dayLabel(m.price.effective, l) }))}: ${url("/shop/#price-changes")}`);
  }
  if (offers.length || (cur && nw.subsFrom) || m.price) out.push("");

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

/** Whether this build's month pages point at their share pictures: only when the build is asked to (POSTER_SHARE=1).
 *  The pictures are not made by the build: Website update (.github/workflows/update.yml) takes them with the
 *  runner's Chrome right after it (scripts/ops/poster_share.py), and builds the site again without POSTER_SHARE when
 *  they could not be made — so no page ever points at a picture that is not there. Every other build (a local one,
 *  the Code check) keeps the committee's card on the month pages. */
export function posterShareOn(env = process.env) {
  return /^(?:1|true)$/i.test(String((env && env.POSTER_SHARE) || "").trim());
}

/** The site's calendar events (committee.js normalizeEvents, as /events.ics has them) by id, for monthIcs: the
 *  window's months, and the month before. */
export function monthIcsEvents(db = {}, site = {}, lang = "en", now = nowDate()) {
  const items = (db.events && db.events.items) || [];
  return new Map(normalizeEvents(items, site, lang === "es" ? "es" : "en", { monthsBack: 1, monthsAhead: WINDOW, now }).map((e) => [e.id, e]));
}

/**
 * "Add this month's dates to my calendar": a month's dates as an iCalendar file — one static file per month and
 * language beside the month's page (src/pages/monthly-ics.11ty.js, at icsPath), linked from the page's Dates card
 * (m.icsUrl), so it needs no script and opens straight in a phone's calendar.
 *   events     the month's date rows (m.dates: the committee meeting, the monthly series, the other events — this
 *              month only the ones not over yet, as in its message), written exactly as /events.ics writes them
 *              (committee.js normalizeEvents + buildIcs: the same UID, description, Zoom details and link — a
 *              calendar that has both keeps one copy; a later month's date of a series, worked out from its rule,
 *              is written from the same record)
 *   deadlines  the story deadlines the page lists (Grapevine's, La Viña's), each an all-day entry on its day:
 *              "Story deadline: “Fun in Sobriety” — Grapevine", its issue and how to send a story (/contribute/)
 * The calendar's name is the month's ("NETA 65 Grapevine & La Viña — October 2026"). RFC 5545 as buildIcs
 * writes it: CRLF line ends, lines folded at 75 octets, TEXT escaped, UTC times, DATE values for all-day entries.
 * (SEQUENCE and DTSTAMP are buildIcs's, as in /events.ics.)
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
    const ev = all.get(d.id) || (d.kind !== "committee" && d.src ? normalizeEvents([d.src], site, L, opt).find((e) => e.id === d.id) : null);
    if (ev) events.push(ev);
  }
  const contribute = abs("/contribute/#deadlines");
  // (a machine-translated theme with Grapevine's own words after it, as in the month's message)
  const deadline = (d, pub) => ({
    uid: `deadline-${slug(d.id)}`, group: "deadline", allDay: true, startYmd: d.due, endYmd: d.due,
    title: t("monthly.ics_deadline", { theme: d.machine && d.themeEn && d.themeEn !== d.theme ? `${d.theme} / ${d.themeEn}` : d.theme,
      pub: t(pub === "lv" ? "monthly.lv_spanish" : "monthly.gv_english") }),
    calDescription: `${t("monthly.for_issue", { issue: d.issueLabel })}.\n\n${t("monthly.msg_how", { url: contribute })}`,
    calLocation: "", detailsUrl: contribute, tentative: false,
  });
  const dls = [...(m.deadlines || []).map((d) => deadline(d, "gv")), ...(m.lvDeadlines || []).map((d) => deadline(d, "lv"))];
  const list = [...events, ...dls].sort((a, b) => (a.allDay ? Date.parse(a.startYmd + "T12:00:00Z") : a.startMs)
    - (b.allDay ? Date.parse(b.startYmd + "T12:00:00Z") : b.startMs) || String(a.title).localeCompare(String(b.title)));
  return buildIcs(list, {
    lang: L, now,
    name: t("monthly.ics_name", { month: m.label }),
    description: t("monthly.ics_desc", { month: m.label, url: abs(`/monthly/${m.key}/`) }),
    url: abs(`/monthly/${m.key}/`),
    categoryLabel: (ev) => t(ev.group === "deadline" ? "monthly.ics_cat_deadline" : `committee.events.group.${ev.group}`),
  });
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
  // A month page's share picture (its ogImage, monthly-month.njk): {{ mpage.key | mpShareImage(mpage.lang) }} — the
  // site path of its share.png in a build asked for it (POSTER_SHARE=1), else "" (the page keeps the committee's card)
  eleventyConfig.addFilter("mpShareImage", (key, lang) => (posterShareOn() && /^\d{4}-\d{2}$/.test(String(key || ""))
    ? sharePicturePath(String(key), lang) : ""));
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
}
