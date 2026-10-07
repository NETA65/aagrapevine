"""Central time — the site's one time-zone helper (eleventy/central-time.js) for the build and the browser, and
what is built on it:

  * the helper itself: a Central wall-clock date and time ↔ the instant, right on the Sundays the clocks change
    (2026-03-08, 2026-11-01, 2027-03-14, 2027-11-07: a time after the change was an hour off when the offset was
    looked up only once), other zones too (the weekly open meetings are hosted in Eastern time), the monthly
    meeting rule (ruleDate), time ranges that end after midnight (never "12/31/2026, 7:00 PM – 1/1/2027, 12:00 AM")
    and the calendars' SEQUENCE (SharedHelper);
  * the browser's copy, /assets/js/central-time.js (src/pages/central-time.11ty.js): the same code as window.GVTime;
    app.js GV.nextMeeting on an old iPhone (iOS 15.3 and older: no timeZoneName "shortOffset") gives the summer
    meeting at 7 PM, not at 8 PM — no fixed −6 hours anywhere (BrowserCopy);
  * the zone is config/site.yml site.timezone (SiteZone);
  * one "now" per build for every monthly helper: a build that runs across midnight on October 31 never links to a
    month page it does not build (BuildClock);
  * toDate: "2026-10" is October, an ISO time without a zone is Central time on any computer (ToDate);
  * the home page's and /events/' event times that end after midnight (CrossMidnight);
  * every .ics the site writes keeps an event's UID and gives it a SEQUENCE that is higher in a newer file
    (CalendarFiles), the weekly open meetings' "Add to calendar" (every week, in their own zone, with the Zoom
    link and passcode) and the end times on /meetings/ (WeeklyOpen);
  * /gvr/ and /about/'s "Next committee meeting" rolls on in the browser once the meeting is over, also in a copy
    saved for offline use (MeetingLines);
  * /events/' counts and chips follow the events that end while the page is open, the countdown rolls on (and is
    never "Live now" after the meeting's end) and the photo lightbox's labels are escaped (CommitteePage).

The JavaScript runs in Node.js (tests/nodejs.py); the browser scripts in a vm with a small stand-in for the page and
a clock the test sets. Expected instants come from Python's zoneinfo.

    python -m unittest tests.test_central_time -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHI = ZoneInfo("America/Chicago")
NYC = ZoneInfo("America/New_York")
UTC = timezone.utc
DST_SUNDAYS = [date(2026, 3, 8), date(2026, 11, 1), date(2027, 3, 14), date(2027, 11, 7)]
SPACES = re.compile(r"[   ]")


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def plain(s: str) -> str:
    return SPACES.sub(" ", s)


# --------------------------------------------------------------------------- the page stand-in
# el(tag, attrs, children, text) builds elements; selectors: tag, #id, .class, [attr], [attr="v"], [attr~="v"] and
# comma lists (no descendants). page(children, { at, files, lang, tz, intl, alpine }) loads the scripts in a vm on a
# page that is still loading (DOMContentLoaded comes from p.ready()), at that instant → { win, doc, clock, intervals
# (fn, ms), minute() (every 60-second interval once), fireWin(type, ev), comps (Alpine.data components), downloads }.
# files: "time" = the browser copy of the helper (/assets/js/central-time.js), else a repository path.
DOM = r"""
import vm from "node:vm";
const { browserScript } = await imp("src/pages/central-time.11ty.js");
const TIME_JS = browserScript();
function matcher(sel) {
  const m = /^([a-z][a-z0-9]*)?((?:\[[\w-]+(?:~?="[^"]*")?\]|\.[\w:-]+|#[\w-]+)*)$/i.exec(String(sel).trim());
  if (!m) return () => false;
  const parts = [...m[2].matchAll(/\[([\w-]+)(?:(~?)="([^"]*)")?\]|\.([\w:-]+)|#([\w-]+)/g)];
  return (e) => (!m[1] || e.tagName === m[1].toUpperCase()) && parts.every((p) => p[1]
    ? (p[3] === undefined ? e.hasAttribute(p[1]) : p[2] ? String(e.getAttribute(p[1]) || "").split(/\s+/).includes(p[3]) : e.getAttribute(p[1]) === p[3])
    : p[4] ? e.classList.contains(p[4]) : e.attrs.id === p[5]);
}
class El {
  constructor(tag, attrs, children, text) {
    this.tagName = String(tag).toUpperCase();
    this.attrs = Object.assign({}, attrs || {});
    this.children = children || [];
    this.parent = null;
    for (const c of this.children) c.parent = this;
    this.hidden = "hidden" in this.attrs;
    this.text = text || "";
    this.listeners = {};
    this.style = { setProperty() {} };
    const self = this, cls = () => String(self.attrs.class || "").split(/\s+/).filter(Boolean);
    this.classList = {
      add(c) { if (!cls().includes(c)) self.attrs.class = [...cls(), c].join(" "); },
      remove(c) { self.attrs.class = cls().filter((x) => x !== c).join(" "); },
      toggle(c, on) { if (on === undefined ? !cls().includes(c) : on) this.add(c); else this.remove(c); },
      contains: (c) => cls().includes(c),
    };
  }
  get textContent() { return this.text + this.children.map((c) => c.textContent).join(""); }
  set textContent(v) { this.text = String(v); this.children = []; }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = String(v); }
  hasAttribute(n) { return n in this.attrs; }
  removeAttribute(n) { delete this.attrs[n]; }
  toggleAttribute(n, on) { if (on) this.attrs[n] = ""; else delete this.attrs[n]; }
  contains(o) { for (let n = o; n; n = n.parent) if (n === this) return true; return false; }
  closest(sel) { const ok = matcher(sel); for (let n = this; n; n = n.parent) if (n.tagName && ok(n)) return n; return null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this); }
  *walk() { for (const c of this.children) { yield c; yield* c.walk(); } }
  querySelectorAll(sel) {
    const ms = String(sel).split(",").map(matcher);
    const found = [...this.walk()].filter((e) => ms.some((m) => m(e)));
    found.forEach = Array.prototype.forEach;
    return found;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(t, fn, o) { (this.listeners[t] ||= []).push(fn); }
  click() { (this.listeners.click || []).forEach((f) => f({ preventDefault() {} })); if (this.onclick) this.onclick(); }
}
const el = (tag, attrs, children, text) => new El(tag, attrs, children, text);
const page = (children, { at, files = ["time", "src/assets/js/app.js"], lang = "en", tz = "America/Chicago", intl, alpine = false } = {}) => {
  const clock = { now: Date.parse(at || "2026-10-06T15:00:00Z") };
  class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(clock.now); } static now() { return clock.now; } }
  const body = el("body", {}, [...(children || [])]);
  const root = el("html", { lang }, [body]);
  const docListeners = {}, winListeners = {}, intervals = [], downloads = [], comps = {}, stores = {};
  const doc = {
    readyState: "loading", documentElement: root, body, activeElement: body, visibilityState: "visible",
    addEventListener: (t, fn) => { (docListeners[t] ||= []).push(fn); },
    querySelectorAll: (s) => root.querySelectorAll(s), querySelector: (s) => root.querySelector(s),
    getElementById: (id) => root.querySelector("#" + id),
    createElement: (t) => el(t),
  };
  class CustomEvent { constructor(type, init) { this.type = type; this.detail = init && init.detail; } }
  class Blob { constructor(parts, o) { this.text = parts.join(""); this.type = o && o.type; } }
  const ctx = {
    console, JSON, Math, Object, Array, String, Number, RegExp, Intl: intl || Intl, Promise, isNaN, isFinite, parseFloat, Error, RangeError,
    TypeError, Map, Set, WeakMap, Symbol, encodeURIComponent, decodeURIComponent, unescape, TextEncoder, Date: FakeDate,
    document: doc, navigator: {}, localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setTimeout: (fn) => { fn(); return 1; }, clearTimeout() {}, clearInterval() {},
    setInterval: (fn, ms) => { intervals.push({ fn, ms }); return intervals.length; },
    requestAnimationFrame: (fn) => fn(), NodeFilter: {}, CustomEvent, Blob, URLSearchParams,
    URL: { createObjectURL: (b) => { downloads.push(b); return "blob:" + downloads.length; }, revokeObjectURL() {} },
    location: { hash: "", search: "", pathname: "/" }, history: { replaceState() {} },
    matchMedia: () => ({ matches: false }), getComputedStyle: () => ({}),
    SITE: { lang, base: "/aagrapevine/", tz },
    addEventListener: (t, fn) => { (winListeners[t] ||= []).push(fn); },
    dispatchEvent: (ev) => { for (const fn of winListeners[ev.type] || []) fn(ev); return true; },
  };
  ctx.window = ctx;
  if (alpine) ctx.Alpine = { data: (n, f) => { comps[n] = f; }, store: (n, v) => (v ? (stores[n] = v) : stores[n] || {}) };
  vm.createContext(ctx);
  for (const f of files) vm.runInContext(f === "time" ? TIME_JS : fs.readFileSync(f, "utf8"), ctx, { filename: f });
  const fire = (t, ev) => { for (const fn of docListeners[t] || []) fn(Object.assign({ type: t }, ev || {})); };
  const fireWin = (t, ev) => { for (const fn of winListeners[t] || []) fn(Object.assign({ type: t }, ev || {})); };
  return {
    win: ctx, doc, clock, intervals, downloads, comps, fireWin,
    ready: () => { doc.readyState = "interactive"; fire("DOMContentLoaded"); if (alpine) fire("alpine:init"); },
    minute: () => intervals.filter((i) => i.ms === 60000).forEach((i) => i.fn()),
  };
};
// An old iPhone's Intl (iOS 15.3 and older): timeZoneName "shortOffset" is refused, as Safari does
const RealDTF = Intl.DateTimeFormat;
function OldDTF(locale, opts) {
  if (opts && /offset/i.test(String(opts.timeZoneName || ""))) throw new RangeError("timeZoneName must be short or long");
  return new RealDTF(locale, opts);
}
OldDTF.prototype = RealDTF.prototype;
OldDTF.supportedLocalesOf = RealDTF.supportedLocalesOf;
const OLD_INTL = Object.assign(Object.create(Intl), { DateTimeFormat: OldDTF });
"""


def js(case: unittest.TestCase, script: str, data=None, env=None):
    return run_js(case, DOM + script, data=data, needs_modules=True, env=env, timeout=120)


# --------------------------------------------------------------------------- the helper itself
class SharedHelper(unittest.TestCase):
    TIMES = ["00:30", "01:30", "03:00", "03:30", "05:00", "06:59", "07:00", "12:00", "19:00", "23:30"]

    _got = None

    def setUp(self):
        if SharedHelper._got is None:
            SharedHelper._got = self.compute()
        self.got, self.cases, self.instants, self.ny = SharedHelper._got

    def compute(self):
        cases = [[d.isoformat(), t] for d in DST_SUNDAYS for t in self.TIMES
                 if not (d.month == 3 and t.startswith("02"))]      # 2:00–2:59 on the spring Sunday does not exist
        instants = []
        for d in DST_SUNDAYS:                                         # every half hour of the night and morning
            start = datetime(d.year, d.month, d.day, 0, 0, tzinfo=CHI).astimezone(UTC)
            instants += [iso(start + timedelta(minutes=30 * i)) for i in range(28)]
        ny = [[d.isoformat(), t] for d in (date(2026, 3, 8), date(2026, 11, 1)) for t in ("03:30", "06:00", "12:00")]
        got = run_js(self, r"""
          const T = await imp("eleventy/central-time.js");
          const isoOf = (ms) => (Number.isFinite(ms) ? new Date(ms).toISOString() : "NaN");
          out({
            walls: input.cases.map(([d, t]) => isoOf(T.wallInstant(d, t, "America/Chicago"))),
            parts: input.instants.map((s) => T.zoneParts(Date.parse(s), "America/Chicago")),
            offsets: input.instants.map((s) => T.offsetMinutes(Date.parse(s), "America/Chicago")),
            ny: input.ny.map(([d, t]) => isoOf(T.wallInstant(d, t, "America/New_York"))),
            zone: T.zone(), known: [T.isZone("America/Chicago"), T.isZone("Central"), T.isZone(""), T.isZone("constructor")],
            junk: [isoOf(T.wallInstant("2026-10-21", "7 PM")), isoOf(T.wallInstant("21/10/2026", "19:00")), isoOf(T.wallInstant("2026-10-21", "24:00")),
                   T.zoneParts(Date.parse("2026-10-21T00:00:00Z"), "Mars/Olympus"), isoOf(T.zoneInstant(2026, 9, 21, 19, 0, "Nowhere/Land")), T.ymdOf(NaN)],
            setBad: [T.setZone("Central"), T.setZone(""), T.zone()],
          });""", data={"cases": cases, "instants": instants, "ny": ny}, needs_modules=False)
        return got, cases, instants, ny

    def test_times_after_the_clocks_change_are_right(self):
        for (d, t), got in zip(self.cases, self.got["walls"]):
            with self.subTest(day=d, time=t):
                y, m, dd = map(int, d.split("-"))
                h, mi = map(int, t.split(":"))
                self.assertEqual(got, iso(datetime(y, m, dd, h, mi, tzinfo=CHI)))     # fold=0: 1:30 AM in the autumn = CDT

    def test_the_wall_clock_of_every_half_hour_of_those_nights(self):
        for s, p, off in zip(self.instants, self.got["parts"], self.got["offsets"]):
            with self.subTest(instant=s):
                local = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=UTC).astimezone(CHI)
                self.assertEqual(p, {"y": local.year, "mo": local.month - 1, "d": local.day, "h": local.hour, "mi": local.minute, "s": 0})
                self.assertEqual(off, int(local.utcoffset().total_seconds() // 60))

    def test_other_zones(self):
        for (d, t), got in zip(self.ny, self.got["ny"]):
            y, m, dd = map(int, d.split("-"))
            h, mi = map(int, t.split(":"))
            self.assertEqual(got, iso(datetime(y, m, dd, h, mi, tzinfo=NYC)), (d, t))

    def test_times_the_clocks_skip_or_pass_twice(self):
        # 2:30 AM on the spring Sunday never shows on a clock: read with the offset from before the change (3:30 AM
        # daylight time — zoneinfo's fold=0), never an hour earlier; 1:30 AM on the autumn Sunday comes twice: the
        # first. The same east of UTC (Berlin) and with a half-hour change (Lord Howe Island), where a first look at
        # the offset lands on the other side of the change.
        cases = [["America/Chicago", "2026-03-08", "02:30"], ["America/Chicago", "2027-03-14", "02:00"],
                 ["America/Chicago", "2026-11-01", "01:30"], ["America/Chicago", "2027-11-07", "01:59"],
                 ["America/New_York", "2026-03-08", "02:30"], ["America/New_York", "2026-11-01", "01:30"],
                 ["Europe/Berlin", "2026-03-29", "02:30"], ["Europe/Berlin", "2026-10-25", "02:30"],
                 ["Australia/Lord_Howe", "2026-04-05", "01:45"], ["Australia/Lord_Howe", "2026-10-04", "02:15"]]
        got = run_js(self, r"""
          const T = await imp("eleventy/central-time.js");
          out(input.map(([tz, d, t]) => { const ms = T.wallInstant(d, t, tz); return Number.isFinite(ms) ? new Date(ms).toISOString() : "NaN"; }));""",
                     data=cases, needs_modules=False)
        for (tz, d, t), g in zip(cases, got):
            with self.subTest(zone=tz, day=d, time=t):
                y, m, dd = map(int, d.split("-"))
                h, mi = map(int, t.split(":"))
                self.assertEqual(g, iso(datetime(y, m, dd, h, mi, tzinfo=ZoneInfo(tz))))

    def test_unknown_zones_and_text_give_nothing_never_a_guess(self):
        self.assertEqual(self.got["zone"], "America/Chicago")
        self.assertEqual(self.got["known"], [True, False, False, False])
        self.assertEqual(self.got["junk"], ["NaN", "NaN", "NaN", None, "NaN", ""])
        self.assertEqual(self.got["setBad"], ["America/Chicago"] * 3, "a name that is not a zone is ignored")

    def test_the_monthly_rule(self):
        r = run_js(self, r"""
          const T = await imp("eleventy/central-time.js");
          const show = (d) => (d ? { ymd: d.ymd, start: new Date(d.start).toISOString(), end: new Date(d.end).toISOString() } : null);
          const R = { weekday: 3, n: 3, start: "19:00", end: "20:00", skip: [] };
          out({
            oct: show(T.ruleDate(2026, 9, R)),
            noEnd: show(T.ruleDate(2026, 9, { weekday: 3, n: 3, start: "18:30" })),
            endFirst: show(T.ruleDate(2026, 9, { weekday: 3, n: 3, start: "19:00", end: "08:00" })),
            defaults: show(T.ruleDate(2026, 9, {})),
            fifthNone: show(T.ruleDate(2026, 9, { weekday: 3, n: 5 })), fifthSep: show(T.ruleDate(2026, 8, { weekday: 3, n: 5 })),
            last: show(T.ruleDate(2026, 9, { weekday: 5, n: -1, start: "19:00" })),
            skipped: show(T.ruleDate(2026, 9, Object.assign({}, R, { skip: ["2026-10-21"] }))),
            rolled: show(T.ruleDate(2026, 12, R)), back: show(T.ruleDate(2027, -1, R)),
            dst: show(T.ruleDate(2027, 2, { weekday: 0, n: 2, start: "03:30", end: "05:00" })),
            fall: show(T.ruleDate(2027, 10, { weekday: 0, n: 1, start: "02:30" })),
            bad: [show(T.ruleDate(2026, 9, { weekday: 9, n: 3 })), show(T.ruleDate(2026, 9, { weekday: 3, n: 7 })), show(T.ruleDate(2026, 9, { weekday: "wednesday" }))],
            nth: [T.nthWeekday(2026, 9, 3, 3), T.nthWeekday(2026, 9, 3, 5), T.nthWeekday(2026, 1, 0, -1), T.nthWeekday(2028, 1, 2, 5)],
          });""", needs_modules=False)

        def span(d, h, mi, end_h, end_mi, tz=CHI):
            a = datetime(d.year, d.month, d.day, h, mi, tzinfo=tz)
            b = datetime(d.year, d.month, d.day, end_h, end_mi, tzinfo=tz)
            return {"ymd": d.isoformat(), "start": iso(a), "end": iso(b)}

        self.assertEqual(r["oct"], span(date(2026, 10, 21), 19, 0, 20, 0))
        self.assertEqual(r["noEnd"], span(date(2026, 10, 21), 18, 30, 19, 30), "no end: one hour")
        self.assertEqual(r["endFirst"], span(date(2026, 10, 21), 19, 0, 20, 0), "an end before the start: one hour")
        self.assertEqual(r["defaults"], span(date(2026, 10, 21), 19, 0, 20, 0), "the 3rd Wednesday, 7 PM")
        self.assertIsNone(r["fifthNone"])
        self.assertEqual(r["fifthSep"]["ymd"], "2026-09-30")
        self.assertEqual(r["last"]["ymd"], "2026-10-30")
        self.assertIsNone(r["skipped"])
        self.assertEqual(r["rolled"]["ymd"], "2027-01-20")
        self.assertEqual(r["back"]["ymd"], "2026-12-16")
        self.assertEqual(r["dst"], span(date(2027, 3, 14), 3, 30, 5, 0), "the spring Sunday: after the change")
        a = datetime(2027, 11, 7, 2, 30, tzinfo=CHI)                  # the autumn Sunday, after the change (CST)
        self.assertEqual(r["fall"], {"ymd": "2027-11-07", "start": iso(a), "end": iso(a + timedelta(hours=1))})
        self.assertEqual(r["bad"], [None, None, None])
        self.assertEqual(r["nth"], [21, None, 22, 29])

    def test_time_ranges(self):
        r = run_js(self, r"""
          const T = await imp("eleventy/central-time.js");
          const R = (a, b, loc, o, tz) => T.timeRange(Date.parse(a), Date.parse(b), loc, tz || "America/Chicago", o);
          out({
            day: R("2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", "en-US"),
            dayEs: R("2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", "es-US"),
            night: R("2027-01-01T01:00:00Z", "2027-01-01T06:00:00Z", "en-US"),
            nightEs: R("2027-01-01T01:00:00Z", "2027-01-01T06:00:00Z", "es-US"),
            nightWd: R("2027-01-01T01:00:00Z", "2027-01-01T06:00:00Z", "en-US", { weekday: "short" }),
            change: R("2026-11-01T00:00:00Z", "2026-11-01T07:30:00Z", "en-US"),
            zoneIgnored: R("2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", "en-US", { timeZoneName: "long" }),
            noEnd: R("2026-10-22T00:00:00Z", "2026-10-22T00:00:00Z", "en-US"),
            east: R("2026-10-07T16:00:00Z", "2026-10-07T17:00:00Z", "en-US", null, "America/New_York"),
            dates: [T.timeRange(new Date("2026-10-22T00:00:00Z"), new Date("2026-10-22T01:00:00Z"), "en-US")],
            junk: T.timeRange(NaN, 0, "en-US"),
          });""", needs_modules=False)
        r = {k: plain(v) if isinstance(v, str) else [plain(x) for x in v] for k, v in r.items()}
        self.assertEqual(r["day"], "7:00 – 8:00 PM CDT")
        self.assertEqual(r["dayEs"], "7:00–8:00 p.m. CDT")
        self.assertEqual(r["night"], "7:00 PM – 12:00 AM CST", "never 12/31/2026, 7:00 PM – 1/1/2027, 12:00 AM")
        self.assertEqual(r["nightEs"], "7:00 p.m. – 12:00 a.m. CST")
        self.assertEqual(r["nightWd"], "Thu, 7:00 PM – Fri, 12:00 AM CST")
        self.assertEqual(r["change"], "7:00 PM CDT – 1:30 AM CST", "the night the clocks change: the zone at both ends")
        self.assertEqual(r["zoneIgnored"], "7:00 – 8:00 PM CDT")
        self.assertEqual(r["noEnd"], "7:00 PM CDT")
        self.assertEqual(r["east"], "12:00 – 1:00 PM EDT")
        self.assertEqual(r["dates"], ["7:00 – 8:00 PM CDT"])
        self.assertEqual(r["junk"], "")

    def test_the_calendars_sequence_grows_with_time(self):
        r = run_js(self, r"""
          const T = await imp("eleventy/central-time.js");
          const at = ["2025-12-31T23:59:00Z", "2026-01-01T00:00:00Z", "2026-01-01T00:01:59Z", "2026-10-06T15:00:00Z", "2026-10-06T15:01:00Z"];
          out({ seq: at.map((s) => T.icsSequence(Date.parse(s))), date: T.icsSequence(new Date("2026-01-01T01:00:00Z")), junk: T.icsSequence("x") });""",
                   needs_modules=False)
        minutes = int((datetime(2026, 10, 6, 15, tzinfo=UTC) - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds() // 60)
        self.assertEqual(r["seq"], [0, 0, 1, minutes, minutes + 1])
        self.assertEqual((r["date"], r["junk"]), (60, 0))
        self.assertLess(r["seq"][-1], 2 ** 31 - 1)


# --------------------------------------------------------------------------- the browser's copy
class BrowserCopy(unittest.TestCase):
    def test_the_same_functions_as_the_module(self):
        r = js(self, r"""
          const T = await imp("eleventy/central-time.js");
          const p = page([], { files: ["time"], tz: "America/New_York" });
          const q = page([], { files: ["time"], tz: "Central" });
          out({ names: Object.keys(p.win.GVTime).sort(), module: Object.keys(T).sort(), zone: p.win.GVTime.zone(), fallback: q.win.GVTime.zone(),
                exports: /^\s*export\b/m.test(TIME_JS), size: TIME_JS.length,
                same: p.win.GVTime.wallInstant("2026-03-08", "03:30", "America/Chicago") === T.wallInstant("2026-03-08", "03:30", "America/Chicago") });""")
        self.assertEqual(r["names"], r["module"])
        self.assertEqual(r["zone"], "America/New_York", "the site's zone: window.SITE.tz")
        self.assertEqual(r["fallback"], "America/Chicago")
        self.assertFalse(r["exports"], "a plain script: no export line")
        self.assertLess(r["size"], 8000, "small: whole-line comments are left out")
        self.assertTrue(r["same"])

    def test_the_build_stops_on_a_module_it_cannot_copy(self):
        tmp = Path(tempfile.mkdtemp(prefix="gv-time-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        src = (ROOT / "eleventy" / "central-time.js").read_text(encoding="utf-8")
        (tmp / "inline.js").write_text(src.replace("function zone()", "export function zone()"), encoding="utf-8")
        (tmp / "renamed.js").write_text(src.replace("export { DEFAULT_ZONE,", "export { DEFAULT_ZONE as D,"), encoding="utf-8")
        (tmp / "none.js").write_text(re.sub(r"^export .*$", "", src, flags=re.M), encoding="utf-8")
        r = run_js(self, r"""
          const { browserScript } = await imp("src/pages/central-time.11ty.js");
          out(input.map((f) => { try { browserScript(f); return "made"; } catch (e) { return "stopped"; } }));""",
                   data=[str(tmp / n) for n in ("inline.js", "renamed.js", "none.js")], needs_modules=False)
        self.assertEqual(r, ["stopped"] * 3)

    def test_only_whole_line_comments_are_left_out(self):
        # a block comment with code after its end on the same line keeps that line — and every line after it
        tmp = Path(tempfile.mkdtemp(prefix="gv-time-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "m.js").write_text("/* about\n   the file */\nvar a = 1;\n/* b */ var b = 2;\n  // c\nvar c = 3; /* d */\n"
                                  "function setZone() {}\nfunction sum() { return a + b + c; }\n\nexport { sum };\n", encoding="utf-8")
        r = run_js(self, r"""
          import vm from "node:vm";
          const { browserScript } = await imp("src/pages/central-time.11ty.js");
          const script = browserScript(input);
          const ctx = { window: {} };
          vm.runInNewContext(script, ctx);
          out({ sum: ctx.window.GVTime.sum(), comments: [/about|\/\/ c/.test(script), script.includes("/* b */")] });""",
                   data=str(tmp / "m.js"), needs_modules=False)
        self.assertEqual(r["sum"], 6)
        self.assertEqual(r["comments"], [False, True])

    def test_old_iphones_get_the_summer_meeting_at_7_pm(self):
        # GV.nextMeeting (app.js): the countdown, the calendar links and the home page's card. iOS 15.3 and older
        # refuse timeZoneName "shortOffset": the old code then used a fixed −6 hours, an hour late in summer.
        moments = ["2026-10-06T15:00:00Z", "2027-05-25T12:00:00Z", "2027-11-25T12:00:00Z", "2026-10-22T00:30:00Z", "2026-10-22T01:00:00Z"]
        r = js(self, r"""
          const rule = { weekday: 3, n: 3, start: "19:00", end: "20:00", skip: ["2027-06-16"] };
          const res = {};
          for (const [name, intl] of [["new", Intl], ["old", OLD_INTL]]) {
            res[name] = input.map((at) => {
              const p = page([], { at, intl });
              const n = p.win.GV.nextMeeting(rule);
              return n ? [n.ymd, n.start.toISOString(), n.end.toISOString()] : null;
            });
          }
          const bare = page([], { files: ["src/assets/js/app.js"] });       // central-time.js did not load
          res.without = bare.win.GV.nextMeeting(rule);
          let refused = false;
          try { new OLD_INTL.DateTimeFormat("en-US", { timeZone: "America/Chicago", timeZoneName: "shortOffset" }); } catch (e) { refused = true; }
          res.refused = refused;
          out(res);""", data=moments)

        def mtg(d):
            a = datetime(d.year, d.month, d.day, 19, tzinfo=CHI)
            return [d.isoformat(), iso(a), iso(a + timedelta(hours=1))]

        want = [mtg(date(2026, 10, 21)), mtg(date(2027, 7, 21)), mtg(date(2027, 12, 15)), mtg(date(2026, 10, 21)), mtg(date(2026, 11, 18))]
        self.assertTrue(r["refused"])
        self.assertEqual(r["new"], want)
        self.assertEqual(r["old"], want, "the same on an old iPhone: 7 PM CDT is 00:00 UTC, never 01:00")
        self.assertIsNone(r["without"], "no helper: no guess (the page keeps the build's date)")

    def test_an_overnight_meeting_ends_the_next_morning(self):
        # a rule from 10 PM to 1 AM (the last Saturday): the end is 1 AM the NEXT morning — also on the night the
        # clocks go back (Oct 31 → Nov 1: 1:00 AM CDT) —, as scripts/sync/meeting.py overnight() has it; the
        # countdown keeps the meeting until then. 7 PM to 8 AM is a slip of the pen (13 hours): one hour.
        moments = ["2026-11-01T05:30:00Z", "2026-11-01T06:30:00Z"]          # 12:30 AM CDT (running) · after the end
        r = js(self, r"""
          const rule = { weekday: 6, n: -1, start: "22:00", end: "01:00", skip: [] };
          const T = await imp("eleventy/central-time.js");
          const show = (d) => (d ? [d.ymd, new Date(d.start).toISOString(), new Date(d.end).toISOString()] : null);
          out({
            build: [show(T.ruleDate(2026, 9, rule)), show(T.ruleDate(2026, 10, rule)),
                    show(T.ruleDate(2026, 9, { weekday: 3, n: 3, start: "19:00", end: "08:00" }))],
            overnight: [T.overnight("22:00", "01:00"), T.overnight([19, 0], [7, 0]), T.overnight("19:00", "08:00"),
                        T.overnight("19:00", "20:00"), T.overnight("23:00", "00:30"), T.overnight("19:00", "")],
            browser: input.map((at) => { const p = page([], { at }); const n = p.win.GV.nextMeeting(rule);
                                         return n ? [n.ymd, n.start.toISOString(), n.end.toISOString()] : null; }),
          });""", data=moments)
        oct31, nov28 = datetime(2026, 10, 31, 22, tzinfo=CHI), datetime(2026, 11, 28, 22, tzinfo=CHI)
        want_oct = ["2026-10-31", iso(oct31), iso(datetime(2026, 11, 1, 1, tzinfo=CHI))]
        self.assertEqual(want_oct[2], "2026-11-01T06:00:00.000Z", "1:00 AM CDT, before the clocks go back")
        self.assertEqual(r["build"][0], want_oct)
        self.assertEqual(r["build"][1], ["2026-11-28", iso(nov28), iso(datetime(2026, 11, 29, 1, tzinfo=CHI))])
        oct21 = datetime(2026, 10, 21, 19, tzinfo=CHI)
        self.assertEqual(r["build"][2], ["2026-10-21", iso(oct21), iso(oct21 + timedelta(hours=1))], "a slip: one hour")
        self.assertEqual(r["overnight"], [True, True, False, False, True, False])
        self.assertEqual(r["browser"], [want_oct, r["build"][1]], "running at 12:30 AM; the next one once it ended")

    def test_a_browser_without_formatToParts(self):
        r = js(self, r"""
          function NoParts(l, o) { const f = new RealDTF(l, o); return { format: (d) => f.format(d), resolvedOptions: () => f.resolvedOptions() }; }
          NoParts.supportedLocalesOf = RealDTF.supportedLocalesOf;
          const p = page([], { files: ["time"], intl: Object.assign(Object.create(Intl), { DateTimeFormat: NoParts }) });
          const T = p.win.GVTime;
          out({ spring: new Date(T.wallInstant("2026-03-08", "03:30")).toISOString(), fall: new Date(T.wallInstant("2026-11-01", "19:00")).toISOString(),
                range: T.timeRange(Date.parse("2027-01-01T01:00:00Z"), Date.parse("2027-01-01T06:00:00Z"), "en-US") });""")
        self.assertEqual(r["spring"], iso(datetime(2026, 3, 8, 3, 30, tzinfo=CHI)))
        self.assertEqual(r["fall"], iso(datetime(2026, 11, 1, 19, tzinfo=CHI)))
        self.assertEqual(plain(r["range"]), "7:00 PM CST – 12:00 AM CST")


# --------------------------------------------------------------------------- the site's zone
class SiteZone(unittest.TestCase):
    SCRIPT = r"""
      const { pathToFileURL: toUrl } = await import("node:url");
      process.chdir(input.dir);
      const C = await import(toUrl(input.root + "/eleventy.config.js").href);
      const T = await import(toUrl(input.root + "/eleventy/central-time.js").href);
      const M = (await import(toUrl(input.root + "/src/_data/meeting.js").href)).default;
      const F = await import(toUrl(input.root + "/eleventy/filters/committee.js").href);
      const S = (await import(toUrl(input.root + "/src/_data/site.js").href)).default;
      out({ tz: C.TZ, zone: T.zone(), filters: F.TZ, site: S().timezone, next: M().next,
            range: F.clockRange(Date.parse("2026-10-22T00:00:00Z"), Date.parse("2026-10-22T01:00:00Z")) });"""

    def run_in(self, yml: str | None):
        if not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            self.skipTest("the site's npm packages are not installed (npm ci)")
        tmp = Path(tempfile.mkdtemp(prefix="gv-zone-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        if yml is not None:
            (tmp / "config").mkdir()
            (tmp / "config" / "site.yml").write_text(yml, encoding="utf-8")
        return run_js(self, self.SCRIPT, data={"dir": str(tmp), "root": str(ROOT).replace("\\", "/")}, needs_modules=False)

    def test_the_build_uses_site_timezone(self):
        r = self.run_in('site: {timezone: "America/New_York"}\nmeeting: {week_of_month: 3, weekday: wednesday, start: "19:00"}\n')
        self.assertEqual((r["tz"], r["zone"], r["filters"], r["site"]), ("America/New_York",) * 4)
        self.assertEqual(plain(r["range"]), "8:00 – 9:00 PM EDT", "the area filters print in it too")
        self.assertTrue(r["next"]["start"].endswith(("T23:00:00.000Z", "T00:00:00.000Z")))     # 7 PM Eastern
        self.assertEqual(datetime.fromisoformat(r["next"]["start"].replace("Z", "+00:00")).astimezone(NYC).hour, 19)

    def test_central_without_a_usable_setting(self):
        for yml in ('site: {timezone: "Central"}\nmeeting: {}\n', "site: {}\nmeeting: {}\n"):
            with self.subTest(yml=yml):
                r = self.run_in(yml)
                self.assertEqual((r["tz"], r["zone"]), ("America/Chicago", "America/Chicago"))
                # the pages' site.timezone — window.SITE.tz, the zone of the browser's scripts — is the same zone
                self.assertEqual(r["site"], "America/Chicago")


# --------------------------------------------------------------------------- one "now" per build
class BuildClock(unittest.TestCase):
    def test_a_build_across_midnight_on_october_31(self):
        # The build starts a tenth of a second before midnight (Central) on October 31 — the evening refresh can
        # run then — and the month window (global data) is read first; by the time the pages' models are made it
        # is November 1.
        r = run_js(self, r"""
          const RealDate = Date;
          const clock = { now: RealDate.parse("2026-11-01T04:59:59.900Z") };
          class FakeDate extends RealDate {
            constructor(...a) { if (a.length) super(...a); else super(clock.now); }
            static now() { return clock.now; }
          }
          globalThis.Date = FakeDate;
          const M = await imp("eleventy/filters/monthly.js");
          const { translateKey } = await imp("eleventy.config.js");
          const gd = {}, fl = {}, on = {};
          const cfg = { addGlobalData: (k, f) => { gd[k] = f; }, addFilter: (k, f) => { fl[k] = f; }, addShortcode() {}, addTransform() {},
                        on: (e, f) => { (on[e] ||= []).push(f); } };
          M.default(cfg, { translateKey });
          const build = () => {
            (on["eleventy.before"] || []).forEach((f) => f());
            const keys = gd.monthlyKeys(), pages = gd.monthlyPages(), past = gd.monthlyPastPages();
            clock.now += 2000;                                    // 00:00:01.9 on November 1
            const models = fl.mpMonths({}, {}, {}, "en");
            const page = (k) => fl.mpMonth(k, {}, {}, {}, "en");
            const res = { keys, pageKeys: [...new Set(pages.map((p) => p.key))], past: [...new Set(past.map((p) => p.key))],
                          models: models.map((m) => m.key), first: { key: page(keys[0]).key, prev: page(keys[0]).hasPrev, next: page(keys[0]).hasNext },
                          last: { key: page(keys[12]).key, next: page(keys[12]).hasNext }, now: M.nowDate().toISOString() };
            (on["eleventy.after"] || []).forEach((f) => f());
            return res;
          };
          const one = build(), two = build();
          globalThis.Date = RealDate;
          out({ one, two });""")
        one, two = r["one"], r["two"]
        keys = [f"{2026 + (9 + i) // 12}-{(9 + i) % 12 + 1:02d}" for i in range(13)]      # 2026-10 … 2027-10
        self.assertEqual(one["keys"], keys)
        self.assertEqual(one["pageKeys"], keys, "the pages built")
        self.assertEqual(one["models"], keys, "the models they show: the same window")
        self.assertNotIn("2027-11", one["models"], "never a link to a month page that is not built")
        self.assertEqual(one["first"], {"key": "2026-10", "prev": False, "next": True}, "October keeps its pager")
        self.assertEqual(one["last"], {"key": "2027-10", "next": False})
        # the past months that keep a small redirect page (monthly.js PAST_MONTHS = 12): 2026-09 back to 2025-10
        self.assertEqual(one["past"], [f"{2026 - (i > 8)}-{(8 - i) % 12 + 1:02d}" for i in range(12)])
        self.assertEqual(one["now"], "2026-11-01T04:59:59.900Z", "the build's one moment")
        # the next build takes its own moment: November now
        self.assertEqual(two["keys"][0], "2026-11")
        self.assertEqual(two["models"], two["keys"])


# --------------------------------------------------------------------------- toDate
class ToDate(unittest.TestCase):
    VALUES = ["2026-10", "2026", "2026-10-21", "2026-10-21T19:00", "2026-10-21 19:00:00", "2026-03-08T03:30",
              "2026-11-01T02:30:00.5", "2026-10-22T00:00:00Z", "2026-10-21T19:00:00-05:00", "2026-13", "2026-02-30",
              "2026-10-21T25:00", "soon", "", None, 0, True]

    def got(self, tz: str):
        return run_js(self, r"""
          out({ iso: input.map((v) => filters.isoDate(v)), month: filters.fmtDate("2026-10", "en", "month"),
                monthEs: filters.fmtDate("2026-10", "es", "month"), year: filters.year("2027"),
                invalidDate: filters.isoDate(new Date("x")) });""",
                      data=self.VALUES, env={"TZ": tz})

    def test_partial_dates_and_times_without_a_zone(self):
        want = [
            "2026-10-01T12:00:00.000Z", "2026-01-01T12:00:00.000Z", "2026-10-21T12:00:00.000Z",
            iso(datetime(2026, 10, 21, 19, tzinfo=CHI)), iso(datetime(2026, 10, 21, 19, tzinfo=CHI)),
            iso(datetime(2026, 3, 8, 3, 30, tzinfo=CHI)), "2026-11-01T08:30:00.500Z",
            "2026-10-22T00:00:00.000Z", "2026-10-22T00:00:00.000Z", "", "", "", "", "", "", "", "",
        ]
        results = [self.got(tz) for tz in ("UTC", "Asia/Tokyo", "America/Los_Angeles")]
        for r in results:
            self.assertEqual(r["iso"], want)
            self.assertEqual(r["month"], "October 2026", '"2026-10" is October, not September')
            self.assertEqual(r["monthEs"], "octubre de 2026")
            self.assertEqual(r["year"], 2027)
            self.assertEqual(r["invalidDate"], "", "an invalid Date is no date")
        self.assertEqual(results[0], results[1], "the computer's own zone changes nothing")


# --------------------------------------------------------------------------- events that end after midnight
class CrossMidnight(unittest.TestCase):
    def test_home_and_events_cards(self):
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const ev = (id, start, end) => ({ id, source: "committee", kind: "event", category: "manual", title: id, lang: "en", date: start,
                                            extra: { start, end, all_day: false, location: "Dallas" } });
          const items = [ev("nye", "2027-01-01T01:00:00Z", "2027-01-01T06:00:00Z"), ev("late", "2026-11-01T00:00:00Z", "2026-11-01T07:30:00Z"),
                         ev("day", "2026-10-22T00:00:00Z", "2026-10-22T02:00:00Z"), ev("long", "2026-10-23T23:00:00Z", "2026-10-25T17:00:00Z")];
          const res = {};
          for (const L of ["en", "es"]) {
            const evs = C.normalizeEvents(items, {}, L, { now: new Date("2026-10-06T15:00:00Z") });
            res[L] = {
              home: items.map((e) => filters.homeEventInfo(e, L).when),
              events: items.map((e) => { const x = evs.find((v) => v.id === e.id); return x.timeLabel || x.rangeLabel; }),
              meeting: filters.homeTimeRange("2027-01-01T01:00:00Z", "2027-01-01T06:00:00Z", L),
              span: filters.cmTimeSpan("2026-10-22T00:00:00.000Z", "2026-10-22T01:00:00.000Z", L),
            };
          }
          out(res);""")
        en = {k: [plain(x) for x in v] if isinstance(v, list) else plain(v) for k, v in r["en"].items()}
        es = {k: [plain(x) for x in v] if isinstance(v, list) else plain(v) for k, v in r["es"].items()}
        want_en = ["7:00 PM – 12:00 AM CST", "7:00 PM CDT – 1:30 AM CST", "7:00 – 9:00 PM CDT"]
        self.assertEqual(en["home"][:3], want_en)
        self.assertEqual(en["events"][:3], want_en, "/events/ reads the same")
        self.assertEqual(en["home"][3], "Fri, Oct 23, 6:00 PM CDT – Sun, Oct 25, 12:00 PM CDT", "a weekend (over 18 hours): its dates")
        self.assertEqual(es["home"][:3], ["7:00 p. m. – 12:00 a. m. CST", "7:00 p. m. CDT – 1:30 a. m. CST", "7:00–9:00 p. m. CDT"])
        self.assertEqual(es["events"][:3], es["home"][:3])
        for v in en["home"] + es["home"] + en["events"] + es["events"]:
            self.assertNotRegex(v, r"\d+/\d+/\d{4}", "never a numeric date in a time range")
        self.assertEqual((en["meeting"], es["meeting"]), ("7:00 PM – 12:00 AM CST", "7:00 p. m. – 12:00 a. m. CST"))
        self.assertEqual((en["span"], es["span"]), ("7:00 – 8:00 PM CDT", "7:00–8:00 p. m. CDT"))


# --------------------------------------------------------------------------- calendar files
WEEKLY = [
    {"id": "weekly_open", "source": "grapevine", "kind": "meeting", "title": "Grapevine Weekly Open AA Meeting", "lang": "en",
     "status": "ok", "url": "https://www.aagrapevine.org/grapevine-weekly-open",
     "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "day": "Wednesdays", "time": "Noon Eastern", "weekday": "wednesday",
               "zoom_url": "https://zoom.us/j/87120368287", "start_local": "12:00", "timezone": "America/New_York",
               "time_central": "11 AM Central", "next_start": "2026-10-07T16:00:00Z"}},
    {"id": "weekly_open_lv", "source": "lavina", "kind": "meeting", "title": "Reunión Abierta de La Viña", "lang": "es", "status": "ok",
     "summary": "Una reunión abierta virtual de AA en español, cada semana.",
     "i18n": {"title": {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"},
              "summary": {"en": "A weekly virtual open AA meeting in Spanish.", "es": "Una reunión abierta virtual de AA en español, cada semana."}},
     "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "day": "Jueves", "weekday": "thursday", "start_local": "12:00",
               "timezone": "America/New_York", "next_start": "2026-11-05T17:00:00Z", "zoom_url": "https://zoom.us/j/87120368287",
               "starts": "2026-11-05"}},
]
SITE = {"url": "https://neta65.github.io/aagrapevine"}


def unfold(text: str) -> list[str]:
    return text.replace("\r\n ", "").split("\r\n")


class CalendarFiles(unittest.TestCase):
    def test_every_writer_keeps_the_uid_and_raises_the_sequence(self):
        r = js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const item = (start) => ({ id: "ev:manual:workshop", source: "committee", kind: "event", category: "manual", title: "Workshop",
                                      lang: "en", date: start, extra: { start, all_day: false, location: "Dallas" } });
          const feed = (start, now) => C.buildIcs(C.normalizeEvents([item(start)], {}, "en", { now: new Date(now) }).filter((e) => e.id === "ev:manual:workshop"), { lang: "en", now: new Date(now) });
          const a = feed("2026-10-24T15:00:00Z", "2026-10-06T15:00:00Z"), b = feed("2026-10-24T16:00:00Z", "2026-10-07T03:00:00Z");
          // the browser: app.js GV.icsText / GV.ics and committee.js's "Add to calendar → .ics file" (CM.downloadIcs)
          const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"] });
          const ev = { uid: "ev-x@neta65-gvlv", title: "Workshop", start: "2026-10-24T15:00:00Z", end: "2026-10-24T17:00:00Z", tentative: true };
          const t1 = p.win.GV.icsText(ev);
          p.clock.now += 3 * 60000;
          p.win.CM.downloadIcs(Object.assign({}, ev, { start: "2026-10-24T16:00:00Z", tentative: false }));
          const bare = page([], { files: ["src/assets/js/app.js"] }).win.GV.icsText(ev);     // without central-time.js
          out({ a, b, t1, t2: p.downloads.map((d) => d.text), bare });""")
        field = lambda text, k: [l.split(":", 1)[1] for l in unfold(text) if l.startswith(k + ":")]
        # the calendar feed (/events.ics): the same UID, a higher SEQUENCE after the time changed
        self.assertEqual(field(r["a"], "UID"), field(r["b"], "UID"))
        sa, sb = int(field(r["a"], "SEQUENCE")[0]), int(field(r["b"], "SEQUENCE")[0])
        self.assertGreater(sb, sa)
        self.assertEqual(sa, int((datetime(2026, 10, 6, 15, tzinfo=UTC) - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds() // 60))
        # the browser's downloads: SEQUENCE from the click, STATUS, the UID as given
        self.assertEqual(len(r["t2"]), 1)
        s1, s2 = int(field(r["t1"], "SEQUENCE")[0]), int(field(r["t2"][0], "SEQUENCE")[0])
        self.assertEqual(s2 - s1, 3)
        self.assertEqual(field(r["t1"], "UID"), field(r["t2"][0], "UID"))
        self.assertEqual((field(r["t1"], "STATUS"), field(r["t2"][0], "STATUS")), (["TENTATIVE"], ["CONFIRMED"]))
        self.assertEqual(field(r["bare"], "SEQUENCE"), field(r["t1"], "SEQUENCE"), "the same number without the helper")
        for text in (r["a"], r["t1"], r["t2"][0]):
            self.assertTrue(all(len(l.encode()) <= 75 for l in text.split("\r\n")))


class WeeklyOpen(unittest.TestCase):
    _r = None

    def setUp(self):
        if WeeklyOpen._r is None:
            WeeklyOpen._r = self.compute()
        self.r = WeeklyOpen._r

    def compute(self):
        return run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const T = await imp("src/pages/meetings-weekly-ics.11ty.js");
          const now = new Date("2026-10-06T15:00:00Z");
          const full = { db: { weekly_open: { items: input.items } }, site: input.site, languages: ["en", "es"] };
          const files = T.data.pagination.before(["en", "es"], full);
          const res = { files: files.map((f) => T.data.permalink({ file: f })), cards: {}, texts: {} };
          for (const L of ["en", "es"]) {
            res.cards[L] = C.weeklyOpenAll(input.items, L, now).map((w) => ({ key: w.isLv ? "lv" : "gv", range: w.next.range, starts: w.starts && w.starts.range,
                                                                              cal: filters.cmWeeklyCal(w, input.site, L) }));
          }
          for (const f of files) res.texts[T.data.permalink({ file: f })] = T.render(Object.assign({ file: f }, full));
          res.vtz = { phoenix: C.vtimezone("America/Phoenix", now.getTime()), madrid: C.vtimezone("Europe/Madrid", now.getTime()) };
          res.none = C.weeklyCalendar(Object.assign({}, C.weeklyOpen(input.items[0], "en", now), { next: null }), input.site, "en");
          out(res);""", data={"items": WEEKLY, "site": SITE})

    def test_one_file_per_meeting_and_language(self):
        self.assertEqual(sorted(self.r["files"]), ["/es/meetings/weekly-open-gv.ics", "/es/meetings/weekly-open-lv.ics",
                                                   "/meetings/weekly-open-gv.ics", "/meetings/weekly-open-lv.ics"])
        for card in self.r["cards"]["en"] + self.r["cards"]["es"]:
            self.assertIn(card["cal"]["ics"], self.r["files"])
        self.assertIsNone(self.r["none"], "a meeting without a date: no calendar")

    def test_every_week_in_its_own_zone_with_the_zoom_details(self):
        gv = unfold(self.r["texts"]["/meetings/weekly-open-gv.ics"])
        self.assertIn("DTSTART;TZID=America/New_York:20261007T120000", gv)
        self.assertIn("DTEND;TZID=America/New_York:20261007T130000", gv)
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=WE", gv)
        self.assertIn("UID:weekly-open@neta65-gvlv", gv)
        self.assertIn("LOCATION:https://zoom.us/j/87120368287", gv)
        desc = next(l for l in gv if l.startswith("DESCRIPTION:"))
        for part in ("Join on Zoom: https://zoom.us/j/87120368287", "Meeting ID: 871 2036 8287", "Passcode: 238047",
                     "Details: https://neta65.github.io/aagrapevine/meetings/#weekly-open"):
            self.assertIn(part, desc.replace("\\n", "\n").replace("\\,", ","))
        # its zone's rules: the 2nd Sunday of March and the 1st of November, 2 AM
        tz = gv[gv.index("BEGIN:VTIMEZONE"):gv.index("END:VTIMEZONE") + 1]
        self.assertIn("TZID:America/New_York", tz)
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", tz)
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", tz)
        self.assertEqual([l for l in tz if l.startswith("DTSTART")], ["DTSTART:19700308T020000", "DTSTART:19701101T020000"])
        self.assertEqual([l for l in tz if l.startswith("TZOFFSETTO")], ["TZOFFSETTO:-0400", "TZOFFSETTO:-0500"])
        # La Viña's from its first meeting, Thursdays; the Spanish file in Spanish, its own UID
        lv = unfold(self.r["texts"]["/es/meetings/weekly-open-lv.ics"])
        self.assertIn("DTSTART;TZID=America/New_York:20261105T120000", lv)
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=TH", lv)
        self.assertIn("UID:weekly-open-lv-es@neta65-gvlv", lv)
        self.assertIn("SUMMARY:Reunión Abierta de La Viña", lv)
        desc = next(l for l in lv if l.startswith("DESCRIPTION:"))
        self.assertIn("Código de acceso: 238047", desc)
        self.assertIn("/aagrapevine/es/meetings/#weekly-open", desc)
        for text in self.r["texts"].values():
            self.assertTrue(text.endswith("\r\n"))
            self.assertTrue(all(len(l.encode()) <= 75 for l in text.split("\r\n")))
            self.assertRegex(text, r"\r\nSEQUENCE:\d+\r\n")

    def test_googles_link_repeats_it(self):
        g = next(c for c in self.r["cards"]["en"] if c["key"] == "gv")["cal"]["gcal"]
        self.assertTrue(g.startswith("https://calendar.google.com/calendar/render?action=TEMPLATE&"))
        for part in ("dates=20261007T120000%2F20261007T130000", "ctz=America%2FNew_York", "recur=RRULE%3AFREQ%3DWEEKLY%3BBYDAY%3DWE",
                     "Passcode%3A%20238047"):
            self.assertIn(part, g)

    def test_the_cards_show_the_end_time(self):
        cards = {(L, c["key"]): c for L in ("en", "es") for c in self.r["cards"][L]}
        self.assertEqual(plain(cards[("en", "gv")]["range"]), "11:00 AM – 12:00 PM CDT")
        self.assertEqual(plain(cards[("es", "gv")]["range"]), "11:00 a. m. – 12:00 p. m. CDT")
        self.assertEqual(plain(cards[("en", "lv")]["starts"]), "11:00 AM – 12:00 PM CST", "La Viña's first meeting, after the clocks change")

    def test_zones_without_or_with_other_rules(self):
        self.assertEqual(self.r["vtz"]["phoenix"], ["BEGIN:VTIMEZONE", "TZID:America/Phoenix", "BEGIN:STANDARD", "DTSTART:19700101T000000",
                                                    "TZOFFSETFROM:-0700", "TZOFFSETTO:-0700", "END:STANDARD", "END:VTIMEZONE"])
        m = self.r["vtz"]["madrid"]
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", m)          # the last Sunday
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", m)
        self.assertIn("DTSTART:19700329T020000", m)
        self.assertIn("DTSTART:19701025T030000", m)

    def test_the_browser_rolls_the_next_date_on_with_its_end(self):
        r = js(self, r"""
          const box = (len) => el("p", Object.assign({ "data-cm-weekly": "2026-10-07T16:00:00.000Z", "data-cm-weekly-tz": "America/New_York", "data-cm-weekly-at": "12:00" },
                                                     len ? { "data-cm-weekly-len": "60" } : {}),
                                  [el("span", { "data-cm-weekly-label": "", "data-next": "Next meeting:", "data-live": "Live now" }, [], "Next meeting:"),
                                   el("span", { "data-cm-weekly-date": "" }, [], "built")]);
          const res = {};
          for (const [name, at, intl] of [["oct", "2026-10-14T20:00:00Z"], ["nov", "2026-11-02T12:00:00Z"], ["oldIphone", "2026-11-02T12:00:00Z", OLD_INTL]]) {
            const a = box(true), b = box(false);
            page([a, b], { at, intl, files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"] });
            res[name] = [a.querySelector("[data-cm-weekly-date]").textContent, b.querySelector("[data-cm-weekly-date]").textContent];
          }
          out(res);""")
        self.assertEqual([plain(s) for s in r["oct"]], ["Wednesday, October 21 · 11:00 AM – 12:00 PM CDT", "Wednesday, October 21 · 11:00 AM CDT"])
        self.assertEqual([plain(s) for s in r["nov"]], ["Wednesday, November 4 · 11:00 AM – 12:00 PM CST", "Wednesday, November 4 · 11:00 AM CST"])
        self.assertEqual(r["oldIphone"], r["nov"])


# --------------------------------------------------------------------------- /gvr/ and /about/
class MeetingLines(unittest.TestCase):
    SCRIPT = r"""
      const RULE = JSON.stringify({ weekday: 3, n: 3, start: "19:00", end: "20:00", skip: [] });
      const AT = "2026-10-22T00:00:00.000Z";
      const lines = (L) => [
        el("span", { "data-gv-meeting": RULE, "data-at": AT, "data-tpl": L === "es" ? "Próxima reunión: {date} a las {time}" : "Next meeting: {date} at {time}", "data-date": "long" }, [], "built"),
        el("span", { "data-gv-meeting": RULE, "data-at": AT, "data-tpl": L === "es" ? "Próxima: {date}" : "Next: {date}", "data-date": "medium" }, [], "built"),
        el("time", { datetime: AT, "data-gv-meeting": RULE, "data-at": AT, "data-tpl": "{date}", "data-date": "long" }, [], "built"),
        el("span", { "data-gv-meeting": RULE, "data-at": AT, "data-tpl": "{time} · Zoom" }, [], "built"),
      ];
      const text = (els) => els.map((e) => e.textContent);
      const res = {};
      for (const [name, at, L, files, intlName] of input) {
        const els = lines(L);
        const p = page(els, { at, lang: L, intl: intlName === "OLD" ? OLD_INTL : undefined, files: files || undefined });
        p.ready();
        res[name] = { text: text(els), datetime: els[2].getAttribute("datetime"), at: els[0].getAttribute("data-at") };
        if (name === "open") {                       // left open over the meeting: the minute check moves it on
          p.clock.now = Date.parse("2026-10-22T01:00:30Z");
          p.minute();
          res.later = { text: text(els), datetime: els[2].getAttribute("datetime") };
        }
      }
      out(res);"""

    def test_the_line_rolls_on_after_the_meeting(self):
        cases = [
            ["during", "2026-10-22T00:30:00Z", "en"],                   # 7:30 PM: the meeting is on — stays
            ["after", "2026-10-22T01:00:00Z", "en"],                    # 8 PM: over
            ["es", "2026-10-30T12:00:00Z", "es"],
            ["oldIphone", "2026-10-30T12:00:00Z", "en", None, "OLD"],
            ["open", "2026-10-22T00:30:00Z", "en"],
            ["noHelper", "2026-10-30T12:00:00Z", "en", ["src/assets/js/app.js"]],
        ]
        r = js(self, self.SCRIPT, data=cases)
        nov = iso(datetime(2026, 11, 18, 19, tzinfo=CHI))
        self.assertEqual(r["during"]["text"], ["built"] * 4)
        want = ["Next meeting: Wednesday, November 18, 2026 at 7:00 PM CST", "Next: November 18, 2026",
                "Wednesday, November 18, 2026", "7:00 PM CST · Zoom"]
        self.assertEqual([plain(s) for s in r["after"]["text"]], want)
        self.assertEqual((r["after"]["datetime"], r["after"]["at"]), (nov, nov))
        self.assertEqual([plain(s) for s in r["es"]["text"]], ["Próxima reunión: Miércoles, 18 de noviembre de 2026 a las 7:00 p. m. CST",
                                                               "Próxima: 18 de noviembre de 2026", "Miércoles, 18 de noviembre de 2026",
                                                               "7:00 p. m. CST · Zoom"])
        self.assertEqual([plain(s) for s in r["oldIphone"]["text"]], want)
        self.assertEqual(r["open"]["text"], ["built"] * 4)
        self.assertEqual([plain(s) for s in r["later"]["text"]], want)
        self.assertEqual(r["later"]["datetime"], nov)
        self.assertEqual(r["noHelper"]["text"], ["built"] * 4, "without the helper the build's text stays")

    def test_the_pages_carry_the_rule_and_a_saved_copy_keeps_the_helper(self):
        for page in ("gvr.njk", "about.njk"):
            src = (ROOT / "src" / "pages" / page).read_text(encoding="utf-8")
            self.assertIn('data-gv-meeting="{{', src, page)
            self.assertIn('data-at="{{ meeting.next.start }}"', src, page)
        base = (ROOT / "src" / "_includes" / "layouts" / "base.njk").read_text(encoding="utf-8")
        self.assertLess(base.index("/assets/js/central-time.js"), base.index("/assets/js/app.js"), "loaded before app.js")
        sw = run_js(self, r"""
          const S = await imp("src/pages/sw.11ty.js");
          const text = S.render({ build: { version: "t1" }, collections: { all: [] } });
          const cfg = JSON.parse(text.slice(text.indexOf("{"), text.indexOf(";\n\n")));
          out({ shell: cfg.shell, required: cfg.required });""", needs_modules=False)
        self.assertIn("/assets/js/central-time.js?v=t1", sw["shell"])
        self.assertNotIn("/assets/js/central-time.js?v=t1", sw["required"])


# --------------------------------------------------------------------------- /events/ and /photos/
class CommitteePage(unittest.TestCase):
    def test_counts_and_chips_follow_the_events_that_end(self):
        r = js(self, r"""
          const chip = (f, n) => el("button", { "data-cm-filter": f }, f === "all" ? [] : [el("span", { class: "cm-chip-count" }, [], String(n))]);
          const li = (g, end, extra) => el("li", Object.assign({ "data-group": g, "data-committee": "0", "data-cm-expire": end }, extra || {}));
          const chips = [chip("all"), chip("committee", 1), chip("neta", 2), chip("calendar", 1)];
          const items = [li("committee", "2026-10-22T01:00:00Z", { "data-committee": "1" }), li("neta", "2026-10-06T18:00:00Z"),
                         li("neta", "2026-10-30T18:00:00Z"), li("calendar", "2026-10-06T19:00:00Z")];
          const root = el("section", { "data-count-label": "Showing {n} events", "data-count-label-one": "Showing 1 event" },
                          [el("div", {}, chips), el("ol", {}, items)]);
          const p = page([root], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true, at: "2026-10-06T15:00:00Z" });
          p.ready();
          const c = p.comps.cmEvents();
          c.$root = root; c.$nextTick = (fn) => fn(); c.$refs = {};
          // what Alpine re-reads: every property show() looks at
          const seen = new Set();
          const watched = new Proxy(c, { get(t, k, rcv) { seen.add(k); return Reflect.get(t, k, rcv); } });
          c.init();
          c.set("calendar");
          const snap = () => ({ counts: chips.slice(1).map((b) => [b.querySelector(".cm-chip-count").textContent, b.hidden]),
                                text: c.countText(), filter: c.filter, tick: c.tick });
          const before = snap();
          p.clock.now = Date.parse("2026-10-06T19:30:00Z");       // the calendar event and one NETA event are over
          p.minute();
          const after = snap();
          seen.clear(); watched.show(items[2]);
          out({ before, after, readsTick: seen.has("tick") });""")
        self.assertEqual(r["before"]["counts"], [["1", False], ["2", False], ["1", False]])
        self.assertEqual(r["before"]["filter"], "calendar")
        self.assertEqual(r["after"]["counts"], [["1", False], ["1", False], ["0", True]], "recounted; an empty chip hides")
        self.assertEqual(r["after"]["filter"], "all", "its filter falls back to All")
        self.assertEqual(r["after"]["text"], "Showing 1 event")
        self.assertEqual(r["after"]["tick"], r["before"]["tick"] + 1)
        self.assertTrue(r["readsTick"], "show() reads tick, so Alpine works the lists out again")

    def test_the_countdown_rolls_on_and_is_never_live_after_the_end(self):
        # /meetings/ and /events/' countdown (cmMeeting): after the October meeting, November's; without the helper
        # (its script did not load) the build's date stays — "Live now" only until its end
        r = js(self, r"""
          const cfg = { rule: { weekday: 3, n: 3, start: "19:00", end: "20:00", skip: [] }, start: "2026-10-22T00:00:00.000Z", end: "2026-10-22T01:00:00.000Z",
                        title: "Meeting", i18n: { join: "Join", soon: "Soon", live: "Live" } };
          const res = {};
          for (const [name, files] of [["helper", undefined], ["none", ["src/assets/js/app.js", "src/assets/js/committee.js"]]]) {
            const p = page([], { files: files || ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true, at: "2026-10-22T00:30:00Z" });
            p.ready();
            const c = p.comps.cmMeeting(cfg);
            c.compute(); c.tick();
            const during = [c.phase, c.timeLabel];
            p.clock.now = Date.parse("2026-10-22T01:05:00Z");
            c.tick();
            res[name] = { during, after: [c.phase, c.dateLabel, c.timeLabel] };
          }
          out(res);""")
        self.assertEqual(r["helper"]["during"][0], "live")
        self.assertEqual([plain(x) for x in r["helper"]["after"]], ["upcoming", "Wednesday, November 18, 2026", "7:00 – 8:00 PM CST"])
        self.assertEqual(r["none"]["during"][0], "live")
        self.assertEqual(r["none"]["after"][0], "upcoming", "not live for ever")

    def test_the_lightbox_labels_are_text(self):
        r = js(self, r"""
          let opts = null;
          const lab = el("div", { id: "cm-lb-i18n", "data-label": 'Fotos "de" <b>la</b> & más', "data-close": "Cerrar'", "data-prev": "<", "data-next": ">" });
          const a = el("a", { class: "glightbox-cm", href: "https://example.org/x.jpg" });
          const p = page([lab, a], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"] });
          p.win.GLightbox = (o) => { opts = o; return {}; };
          p.ready();
          out(opts ? opts.lightboxHTML : null);""")
        self.assertIn('aria-label="Fotos &quot;de&quot; &lt;b&gt;la&lt;/b&gt; &amp; más"', r)
        self.assertIn('aria-label="Cerrar&#39;"', r)
        self.assertIn('aria-label="&lt;"', r)
        self.assertNotIn("<b>", r)


if __name__ == "__main__":
    unittest.main()
