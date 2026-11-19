"""Dates the browser works out between the daily builds, in Central time (the site's time zone): the scripts run in
Node.js on a pretend page, with a clock the test sets.

  * What's New (src/assets/js/community.js): the "Today" / "Yesterday" badges on the day headings. Yesterday is the
    calendar day before today, not 24 hours ago — the days the clocks change are 23 or 25 hours long, and "24 hours
    ago" named the wrong day (the first hour of the Monday after the spring change) or today itself (the last hour
    of the autumn change's Sunday). A clock that gives no YYYY-MM-DD shows no badge and stops nothing else (DayBadges).
  * The Monthly toolkit (src/assets/js/monthly.js): the new-month notice ([data-mp-newmonth="YYYY-MM"], on the hub
    and on the current month's page) shows once the visitor's month is its month or later — and a copy two or more
    months old (a page saved for offline use, or no rebuild for a while) names and links the VISITOR's month, not
    the one after the build's, also when the month turns while the page is open (NewMonthNotice).

    python -m unittest tests.test_client_dates -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

# The page stand-in: el(tag, attrs, children, text) builds elements ("[attr]" and tag-name selectors);
# page(children, file, { lang, at, intl }) loads the script on a finished page at that instant → { clock, minute()
# (the script's every-minute check), docListeners }. `intl` replaces Intl (a browser whose clock gives odd dates).
DOM = r"""
import vm from "node:vm";
class El {
  constructor(tag, attrs, children, text) {
    this.tagName = String(tag).toUpperCase();
    this.attrs = Object.assign({}, attrs || {});
    this.children = children || [];
    this.hidden = "hidden" in this.attrs;
    this.textContent = text || "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains: () => false };
  }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = String(v); }
  hasAttribute(n) { return n in this.attrs; }
  removeAttribute(n) { delete this.attrs[n]; }
  addEventListener() {}
  *walk() { for (const c of this.children) { yield c; yield* c.walk(); } }
  querySelectorAll(sel) {
    const s = String(sel).trim(), attr = /^\[([\w-]+)\]$/.exec(s), tag = /^[a-z]+$/i.test(s) ? s.toUpperCase() : null;
    return [...this.walk()].filter((e) => (attr ? e.hasAttribute(attr[1]) : tag ? e.tagName === tag : false));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
const el = (tag, attrs, children, text) => new El(tag, attrs, children, text);
const page = (children, file, { lang = "en", at, intl } = {}) => {
  const clock = { now: Date.parse(at) };
  class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(clock.now); } static now() { return clock.now; } }
  const body = el("body", {}, children || []);
  const root = el("html", { lang }, [body]);
  root.lang = lang;
  const intervals = [], docListeners = {};
  const document = { readyState: "complete", documentElement: root, body, activeElement: body, hidden: false,
                     addEventListener: (t, fn) => { (docListeners[t] ||= []).push(fn); },
                     querySelectorAll: (s) => root.querySelectorAll(s), querySelector: (s) => root.querySelector(s) };
  const ctx = { console, Date: FakeDate, document, GV: {}, SITE: { lang, base: "/aagrapevine/", tz: "America/Chicago" },
                location: { pathname: "/aagrapevine/", search: "", hash: "" }, addEventListener() {},
                setTimeout: () => 0, clearTimeout() {}, setInterval: (fn, ms) => { intervals.push({ fn, ms }); return intervals.length; } };
  if (intl) ctx.Intl = intl;
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(file, "utf8"), ctx, { filename: file });
  return { clock, docListeners, minute: () => intervals.find((i) => i.ms === 60000).fn() };
};
"""


def js(case: unittest.TestCase, script: str, data=None):
    return run_js(case, DOM + script, data=data, needs_modules=False, timeout=60)


class DayBadges(unittest.TestCase):
    # [the instant, the day it is in Central time, why]
    MOMENTS = [
        ["2026-09-30T17:00:00Z", "2026-09-30", "a plain day"],
        ["2026-10-01T03:00:00Z", "2026-09-30", "late evening: already tomorrow in UTC"],
        ["2027-03-15T05:30:00Z", "2027-03-15", "00:30 on the Monday after the spring change (Sunday had 23 hours)"],
        ["2026-11-02T05:30:00Z", "2026-11-01", "23:30 on the autumn change's Sunday (25 hours long)"],
        ["2027-01-01T06:30:00Z", "2027-01-01", "New Year's Day, 00:30"],
        ["2028-03-01T12:00:00Z", "2028-03-01", "after a leap day"],
        ["2027-03-01T12:00:00Z", "2027-03-01", "after February's 28th"],
    ]

    def test_today_and_the_calendar_day_before(self):
        cases = []
        for at, today, _why in self.MOMENTS:
            d = date.fromisoformat(today)
            cases.append({"at": at, "days": [(d - timedelta(days=n)).isoformat() for n in (0, 1, 2)]})
        r = js(self, r"""
          out(input.map((c) => {
            const badges = c.days.map((d) => el("span", { "data-rel-day": d }));
            page([el("div", { "data-today": "Today", "data-yesterday": "Yesterday" }, badges)], "src/assets/js/community.js", { at: c.at });
            return badges.map((b) => b.textContent);
          }));""", data=cases)
        for (at, _today, why), got in zip(self.MOMENTS, r):
            with self.subTest(at=at, why=why):
                self.assertEqual(got, ["Today", "Yesterday", ""])

    def test_a_clock_without_a_calendar_date_stops_nothing(self):
        # a browser whose date comes back as "9/30/2026": no badge — and the page's other helpers (the Copy buttons,
        # the QR code's PNG) are still set up after it, instead of the badges' RangeError stopping them
        r = js(self, r"""
          const badges = ["2026-09-30", "2026-09-29"].map((d) => el("span", { "data-rel-day": d }));
          const intl = { DateTimeFormat: function () { return { format: () => "9/30/2026" }; } };
          const p = page([el("div", { "data-today": "Today", "data-yesterday": "Yesterday" }, badges)], "src/assets/js/community.js",
                         { at: "2026-09-30T17:00:00Z", intl });
          out({ badges: badges.map((b) => b.textContent), clicks: (p.docListeners.click || []).length });""")
        self.assertEqual(r, {"badges": ["", ""], "clicks": 2})


class NewMonthNotice(unittest.TestCase):
    # The notice as src/pages/monthly.njk and monthly-month.njk render it for a build made in September 2026 (the notice
    # for October): the words with {month} unfilled in data-mp-newmonth-text, today's words in [data-mp-newmonth-label].
    SCRIPT = r"""
      const WORDS = { en: ["It's {month} now — open this month's toolkit", "October"], es: ["Ya es {month}: abre el kit de este mes", "octubre"] };
      const notice = (lang, label) => {
        const [text, built] = WORDS[lang], words = text.replace("{month}", built);
        const inner = label ? [el("span", { "data-mp-newmonth-label": "" }, [], words), el("span", { "aria-hidden": "true" }, [], "→")] : [];
        const a = el("a", { href: "/aagrapevine/" + (lang === "es" ? "es/" : "") + "monthly/2026-10/" }, [el("span", {}, inner, label ? "" : words + " →")]);
        return el("p", Object.assign({ "data-mp-newmonth": "2026-10", role: "status", hidden: "" }, label ? { "data-mp-newmonth-text": text } : {}), [a]);
      };
      out(input.map(({ lang, times, label = true }) => {
        const n = notice(lang, label);
        const p = page([n], "src/assets/js/monthly.js", { lang, at: times[0] });
        return times.map((t, i) => {
          if (i) { p.clock.now = Date.parse(t); p.minute(); }                   // the page left open: the minute's check
          const a = n.querySelector("a"), lab = n.querySelector("[data-mp-newmonth-label]");
          return [n.hidden, a.getAttribute("href"), (lab || a.querySelector("span")).textContent];
        });
      }));"""
    TIMES = ["2026-09-30T17:00:00Z", "2026-10-15T17:00:00Z", "2026-11-01T07:30:00Z", "2026-11-20T17:00:00Z",
             "2026-12-02T17:00:00Z", "2027-01-10T17:00:00Z", "2026-10-20T17:00:00Z"]

    def results(self):
        return js(self, self.SCRIPT, data=[{"lang": "en", "times": self.TIMES}, {"lang": "es", "times": self.TIMES},
                                           {"lang": "en", "times": ["2026-11-20T17:00:00Z"], "label": False}])

    def test_the_visitors_month_named_and_linked(self):
        en, es, _ = self.results()
        hub, hub_es = "/aagrapevine/monthly/", "/aagrapevine/es/monthly/"
        self.assertEqual(en, [
            [True, hub + "2026-10/", "It's October now — open this month's toolkit"],    # still September: not yet
            [False, hub + "2026-10/", "It's October now — open this month's toolkit"],   # the month the build expected
            [False, hub + "2026-11/", "It's November now — open this month's toolkit"],  # 01:30 on Nov 1, Central time
            [False, hub + "2026-11/", "It's November now — open this month's toolkit"],
            [False, hub + "2026-12/", "It's December now — open this month's toolkit"],  # it turned while open
            [False, hub + "2027-01/", "It's January now — open this month's toolkit"],
            [False, hub + "2026-10/", "It's October now — open this month's toolkit"],   # a clock put back: back too
        ])
        self.assertEqual([row[1:] for row in es[1:4]], [
            [hub_es + "2026-10/", "Ya es octubre: abre el kit de este mes"],
            [hub_es + "2026-11/", "Ya es noviembre: abre el kit de este mes"],
            [hub_es + "2026-11/", "Ya es noviembre: abre el kit de este mes"],
        ])
        self.assertEqual(es[5][1:], [hub_es + "2027-01/", "Ya es enero: abre el kit de este mes"])

    def test_a_clock_without_a_calendar_date(self):
        # a browser whose date comes back as "9/30/2026": the month is taken from the UTC date instead — never a made-up
        # month in the link ("/monthly/9/30/20/"), nor the notice shown before its month
        r = js(self, r"""
          const real = Intl;
          const intl = { DateTimeFormat: function (loc, o) { return o && o.day ? { format: () => "9/30/2026" } : new real.DateTimeFormat(loc, o); } };
          out(["2026-09-30T17:00:00Z", "2026-11-20T17:00:00Z"].map((at) => {
            const lab = el("span", { "data-mp-newmonth-label": "" }, [], "It's October now — open this month's toolkit");
            const a = el("a", { href: "/aagrapevine/monthly/2026-10/" }, [el("span", {}, [lab])]);
            const n = el("p", { "data-mp-newmonth": "2026-10", "data-mp-newmonth-text": "It's {month} now — open this month's toolkit", hidden: "" }, [a]);
            page([n], "src/assets/js/monthly.js", { at, intl });
            return [n.hidden, a.getAttribute("href"), lab.textContent];
          }));""")
        self.assertEqual(r, [[True, "/aagrapevine/monthly/2026-10/", "It's October now — open this month's toolkit"],
                             [False, "/aagrapevine/monthly/2026-11/", "It's November now — open this month's toolkit"]])

    def test_a_notice_without_its_words_still_links_the_month(self):
        # markup without the label and the unfilled words (a page from before they were added): the link follows the
        # visitor's month, the words stay the page's own — nothing breaks
        _, _, bare = self.results()
        self.assertEqual(bare, [[False, "/aagrapevine/monthly/2026-11/", "It's October now — open this month's toolkit →"]])


if __name__ == "__main__":
    unittest.main()
