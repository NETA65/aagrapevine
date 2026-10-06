/* Central time: the site's ONE time-zone helper, for the build AND the browser.
     the build (Node.js)   import { zoneInstant, … } from "eleventy/central-time.js" — eleventy.config.js sets its
                           zone from config/site.yml site.timezone (America/Chicago) when it loads
     the browser           /assets/js/central-time.js → window.GVTime, made from this file by
                           src/pages/central-time.11ty.js (the same code, without the `export` line) and loaded
                           right before app.js; its zone is window.SITE.tz (base.njk: site.timezone)
   The Area meets, and every date on the site is shown, in Central time; the weekly open meetings are hosted in
   Eastern time — any IANA zone name works.
   Written for old browsers too (var and function; no arrow functions, ?? or ?.). A zone's offset is worked out
   from the wall clock Intl gives for an instant (formatToParts: year … second), never from a written "GMT-5":
   an iPhone on iOS 15.3 or older has no timeZoneName "shortOffset" (the committee meeting showed an hour late
   there in daylight-saving months), and a browser without formatToParts gets the same parts from format().
   No fixed −6 hours anywhere: a browser without time zones gets null / NaN, and its caller keeps the build's own
   text.
     zone() / setZone(tz)        the site's zone; an unknown name leaves it as it was → the zone
     isZone(tz)                  a zone name this JavaScript knows
     zoneParts(ms, tz)           the wall clock of an instant in a zone: { y, mo (0–11), d, h (0–23), mi, s } or null
     offsetMinutes(ms, tz)       the zone's offset from UTC at that instant (Central: −300 in summer, −360 in winter)
     zoneInstant(y, mo, d, h, mi, tz)  a wall-clock date and time in a zone → the instant (ms); month and day may
                                 run over (Date.UTC rolls them). The offset is looked up on both sides of the day
                                 and each answer is checked against it, so a time after the clocks change on that
                                 very day is right (a single look used the offset from before the change: 3:30 AM
                                 on the spring Sunday came out as 4:30 AM). A time the clocks pass twice (1:30 AM
                                 on the autumn Sunday) is the first one; one they skip (2:30 AM in spring) is read
                                 with the offset from before the change: 3:30 AM daylight time
     wallInstant("2026-10-21", "19:00", tz)  the same from text → ms, NaN when either cannot be read
     clock("19:00")              [19, 0]; null unless "H:MM" / "HH:MM" (24 h)
     ymdOf(ms, tz)               "YYYY-MM-DD" of an instant in the zone ("" without one)
     nthWeekday(y, mo, wd, n)    the day of the month of its nth weekday (wd 0 = Sunday; n 1–5, or −1 = the last),
                                 null when the month has no such day (a 5th Wednesday)
     overnight(start, end)       an end earlier on the clock than the start that is the next morning: the event
                                 then lasts at most OVERNIGHT_MAX_HOURS ("22:00"–"01:00" → true; "19:00"–"08:00",
                                 13 hours, is a slip of the pen → false; "19:00"–"20:00" → false). "HH:MM" or [h, mi];
                                 the rule of scripts/sync/meeting.py overnight()
     ruleDate(y, mo, rule, tz)   a monthly meeting's date in a month: rule { weekday 0–6, n, start "HH:MM", end,
                                 skip ["YYYY-MM-DD"] } (the countdown's shape: src/_data/meeting.js `rule`,
                                 committee.js cmRuleObj) → { ymd, start, end } (ms) or null (no such day, a
                                 skipped date). An overnight end is on the next day ("22:00"–"01:00" ends at 1 AM
                                 the next morning); no end, or one not after the start: one hour (the site's rule)
     timeRange(a, b, locale, tz, opts)  "7:00 – 8:00 PM CDT" (Intl formatRange); a time that ends after midnight
                                 "7:00 PM – 1:00 AM CST" — never the numeric dates Intl writes into a range over two
                                 days ("12/31/2026, 7:00 PM – 1/1/2027, 12:00 AM"); the zone is said once, or at
                                 both ends on the night the clocks change. opts: more Intl options for each end
                                 ({ weekday: "short" }). Spanish "p.m." is left to the caller's esMeridiem
     icsSequence(ms)             an iCalendar SEQUENCE for a file made at that moment: whole minutes since
                                 2026-01-01 UTC. Every .ics the site writes (the /events.ics feeds, the weekly open
                                 meetings' files, the browser's "Add to calendar" downloads) keeps an event's UID
                                 and gives it this number, so a newer file always counts as the newer version and a
                                 calendar app takes a changed time or place (a number made from the event's own
                                 details could come out lower after a change, and the change would be ignored). */

var DEFAULT_ZONE = "America/Chicago";
var OVERNIGHT_MAX_HOURS = 12;            // scripts/sync/meeting.py OVERNIGHT_MAX_HOURS
var ZONE = DEFAULT_ZONE;
var SEQ_EPOCH = Date.UTC(2026, 0, 1);
var FMT = {};

function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
function pad(n) { return (n < 10 ? "0" : "") + n; }

// One formatter per zone (null for a name Intl does not know). hour12: false is understood by every browser
// (hourCycle is newer); the hour it gives for midnight can be "24", and a browser that ignores it says "PM".
function formatter(tz) {
  var key = String(tz || "");
  if (!key) return null;
  if (!has(FMT, key)) {
    var f = null;
    try {
      f = new Intl.DateTimeFormat("en-US", { timeZone: key, hour12: false, year: "numeric", month: "numeric",
        day: "numeric", hour: "numeric", minute: "numeric", second: "numeric" });
    } catch (e) {
      f = null;
    }
    FMT[key] = f;
  }
  return FMT[key];
}

function isZone(tz) { return !!formatter(tz); }
function zone() { return ZONE; }
function setZone(tz) {
  if (tz && isZone(tz)) ZONE = String(tz);
  return ZONE;
}

function zoneParts(ms, tz) {
  var f = formatter(tz || ZONE), t = Number(ms), p = {};
  if (!f || !isFinite(t)) return null;
  try {
    if (typeof f.formatToParts === "function") {
      var parts = f.formatToParts(new Date(t));
      for (var i = 0; i < parts.length; i++) p[parts[i].type] = parts[i].value;
    } else {
      // "10/21/2026, 19:00:00"
      var m = /(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)/.exec(f.format(new Date(t)));
      if (m) p = { month: m[1], day: m[2], year: m[3], hour: m[4], minute: m[5], second: m[6] };
    }
  } catch (e) {
    return null;
  }
  var h = Number(p.hour);
  if (p.dayPeriod) h = (h % 12) + (/^p/i.test(p.dayPeriod) ? 12 : 0);
  var o = { y: Number(p.year), mo: Number(p.month) - 1, d: Number(p.day), h: h % 24, mi: Number(p.minute), s: Number(p.second) || 0 };
  return isNaN(o.y) || isNaN(o.mo) || isNaN(o.d) || isNaN(o.h) || isNaN(o.mi) ? null : o;
}

// The zone's offset at an instant, in ms (wall clock − UTC)
function offsetMs(ms, tz) {
  var p = zoneParts(ms, tz);
  return p ? Date.UTC(p.y, p.mo, p.d, p.h, p.mi, p.s) - Math.floor(ms / 1000) * 1000 : NaN;
}
function offsetMinutes(ms, tz) {
  var o = offsetMs(Number(ms), tz);
  return isNaN(o) ? NaN : Math.round(o / 60000);
}

function zoneInstant(y, mo, d, h, mi, tz) {
  var guess = Date.UTC(y, mo, d, h || 0, mi || 0);
  if (isNaN(guess)) return NaN;
  // the zone's offset a day before and a day after: the same, except around a change of the clocks
  var before = offsetMs(guess - 864e5, tz), after = offsetMs(guess + 864e5, tz);
  if (isNaN(before) || isNaN(after)) return NaN;
  var early = guess - before, late = guess - after;
  if (before === after) return early;
  // the reading whose offset is right at its own instant: both on the night the clocks go back (the first
  // wins), neither for a time they skip (read with the offset from before the change)
  var okEarly = offsetMs(early, tz) === before, okLate = offsetMs(late, tz) === after;
  return okEarly && okLate ? Math.min(early, late) : okLate ? late : early;
}

function clock(s) {
  var m = /^\s*(\d{1,2}):(\d{2})(?!\d)/.exec(s === null || s === undefined ? "" : String(s));
  if (!m) return null;
  var h = Number(m[1]), mi = Number(m[2]);
  return h < 24 && mi < 60 ? [h, mi] : null;
}

function wallInstant(ymd, hm, tz) {
  var d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(ymd || "")), c = clock(hm);
  return d && c ? zoneInstant(Number(d[1]), Number(d[2]) - 1, Number(d[3]), c[0], c[1], tz) : NaN;
}

function ymdOf(ms, tz) {
  var p = zoneParts(ms, tz);
  return p ? p.y + "-" + pad(p.mo + 1) + "-" + pad(p.d) : "";
}

function nthWeekday(y, mo, weekday, n) {
  var dim = new Date(Date.UTC(y, mo + 1, 0)).getUTCDate();
  if (n === -1) return dim - ((new Date(Date.UTC(y, mo, dim)).getUTCDay() - weekday + 7) % 7);
  var day = 1 + ((weekday - new Date(Date.UTC(y, mo, 1)).getUTCDay() + 7) % 7) + (n - 1) * 7;
  return day >= 1 && day <= dim ? day : null;
}

function overnight(start, end, maxHours) {
  var s = typeof start === "object" && start ? start : clock(start), e = typeof end === "object" && end ? end : clock(end);
  if (!s || !e) return false;
  var a = s[0] * 60 + s[1], b = e[0] * 60 + e[1];
  return b < a && 24 * 60 - a + b <= (maxHours === undefined ? OVERNIGHT_MAX_HOURS : maxHours) * 60;
}

// (the site's defaults: the 3rd Wednesday, 19:00)
function ruleDate(y, mo, rule, tz) {
  rule = rule || {};
  var base = new Date(Date.UTC(y, mo, 1));
  y = base.getUTCFullYear();
  mo = base.getUTCMonth();
  var wd = rule.weekday === undefined || rule.weekday === null || rule.weekday === "" ? 3 : Number(rule.weekday);
  var n = rule.n === undefined || rule.n === null || rule.n === "" ? 3 : Number(rule.n);
  if (!(wd >= 0 && wd <= 6) || !(n === -1 || (n >= 1 && n <= 5))) return null;
  var day = nthWeekday(y, mo, Math.floor(wd), Math.floor(n));
  if (!day) return null;
  var ymd = y + "-" + pad(mo + 1) + "-" + pad(day), skip = rule.skip || [];
  for (var i = 0; i < skip.length; i++) if (String(skip[i]).slice(0, 10) === ymd) return null;
  var s = clock(rule.start) || [19, 0], e = clock(rule.end);
  var start = zoneInstant(y, mo, day, s[0], s[1], tz);
  if (isNaN(start)) return null;
  // an overnight end is the next morning's wall clock (zoneInstant rolls the day over: DST-safe)
  var end = e ? zoneInstant(y, mo, day + (overnight(s, e) ? 1 : 0), e[0], e[1], tz) : NaN;
  return { ymd: ymd, start: start, end: end > start ? end : start + 3600e3 };
}

function timeRange(a, b, locale, tz, opts) {
  var A = Number(a instanceof Date ? a.getTime() : a), B = Number(b instanceof Date ? b.getTime() : b);
  var o = { hour: "numeric", minute: "2-digit", timeZone: tz || ZONE };
  for (var k in opts || {}) if (has(opts, k) && k !== "timeZoneName") o[k] = opts[k];
  try {
    o.timeZoneName = "short";
    var f = new Intl.DateTimeFormat(locale, o);
    if (!isFinite(A)) return "";
    if (!(B > A)) return f.format(A);
    if (ymdOf(A, o.timeZone) === ymdOf(B, o.timeZone) && typeof f.formatRange === "function") return f.formatRange(A, B);
    return (zoneName(f, A) === zoneName(f, B) ? withoutZone(f, A) : f.format(A)) + " – " + f.format(B);
  } catch (e) {
    return "";
  }
}
function zoneName(f, ms) {
  try {
    var parts = f.formatToParts(new Date(ms));
    for (var i = 0; i < parts.length; i++) if (parts[i].type === "timeZoneName") return parts[i].value;
  } catch (e) { /* no formatToParts: the zone at both ends */ }
  return "";
}
// The same text without its zone ("Thu, 7:00 PM CST" → "Thu, 7:00 PM"), so both ends read alike
function withoutZone(f, ms) {
  try {
    var parts = f.formatToParts(new Date(ms)), out = "";
    for (var i = 0; i < parts.length; i++) {
      var next = parts[i + 1];
      if (parts[i].type === "timeZoneName" || (parts[i].type === "literal" && next && next.type === "timeZoneName")) continue;
      out += parts[i].value;
    }
    return out.replace(/^\s+|\s+$/g, "");
  } catch (e) {
    return f.format(ms);
  }
}

function icsSequence(ms) {
  var t = Number(ms instanceof Date ? ms.getTime() : ms);
  return isFinite(t) && t > SEQ_EPOCH ? Math.floor((t - SEQ_EPOCH) / 60000) : 0;
}

export { DEFAULT_ZONE, zone, setZone, isZone, zoneParts, offsetMinutes, zoneInstant, wallInstant, clock, ymdOf, nthWeekday, overnight, ruleDate, timeRange, icsSequence };
