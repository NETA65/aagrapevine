"""Dates in the browser (src/assets/js/app.js GV.fmtDate, GV.relative), run in Node.js on a pretend page
(tests/fakedom.py):

  * one formatter per (kind, locale, options) — a list of hundreds of dates (the Tracker's Requests, a search's
    results) no longer builds an Intl formatter per date; an option left undefined (timeZone: undefined, the
    device's own zone) is a formatter of its own, so the build-time and local times stay apart
  * GV.relative ("3 days ago") — and, in a browser without Intl.RelativeTimeFormat (iOS 13 and older), the plain
    date: never an error, so the page's script goes on — the [data-local-time] dates, the copy and share buttons
    after them; "" for something that is not a date

    python -m unittest tests.test_app_formats -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

# app.js on a page with a local time, a relative time and a copy button; noRtf: a browser without
# Intl.RelativeTimeFormat. Every Intl formatter made is counted (made()).
APP_JS = PAGE_JS + r"""
function app(lang, noRtf) {
  const copied = [];
  const p = page({ html: '<time data-local-time datetime="2026-10-03T23:30:00Z">x</time><time data-relative datetime="2026-10-03T15:00:00Z">y</time>' +
                         '<button type="button" id="copy" data-copy="the meeting ID">Copy</button>',
                   globals: { SITE: { lang, base: "/aagrapevine/" }, navigator: { clipboard: { writeText: (t) => { copied.push(t); return Promise.resolve(); } } } } });
  vm.runInContext(`(() => {
    const n = { DateTimeFormat: 0, RelativeTimeFormat: 0 };
    for (const k of Object.keys(n)) {
      const C = Intl[k];
      if (C) Intl[k] = new Proxy(C, { construct(t, a) { n[k] += 1; return new t(...a); } });
    }
    globalThis.made = () => Object.assign({}, n);
    ${noRtf ? "delete Intl.RelativeTimeFormat;" : ""}
  })();`, p.win);
  vm.runInContext(fs.readFileSync("src/assets/js/app.js", "utf8"), p.win, { filename: "app.js" });
  return { p, G: p.win.GV, copied, made: () => p.win.made() };
}
const R = {};
{
  const { p, G, made } = app("en");
  const now = p.win.__clock.now;   // (the page's clock)
  const opts = { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" };
  const outs = new Set();
  for (let i = 0; i < 300; i++) outs.add(G.fmtDate("2026-10-03T23:30:00Z", opts));
  R.cached = { outs: [...outs], made: made().DateTimeFormat };
  R.local = G.fmtDate("2026-10-03T23:30:00Z", Object.assign({}, opts, { timeZone: undefined }));   // the device's (TZ=UTC here)
  R.central = G.fmtDate("2026-10-03T23:30:00Z", opts);
  R.madeAfterLocal = made().DateTimeFormat;
  R.month = G.fmtDate("2026-10-03T12:00:00Z", { month: "long" });
  const rel = [];
  for (let i = 0; i < 50; i++) rel.push(G.relative(now + 2 * 86400e3 + 60e3));
  R.relative = { inTwoDays: rel[0], same: new Set(rel).size, made: made().RelativeTimeFormat, ago: G.relative(now - 3 * 3600e3),
                 bad: G.relative("not a date") };
}
{
  const { p, G } = app("es");
  R.es = { date: G.fmtDate("2026-10-03T23:30:00Z", { hour: "numeric", minute: "2-digit" }), rel: G.relative(p.win.__clock.now - 86400e3) };
}
{
  const { p, G, copied } = app("en", true);
  R.noRtf = { relative: G.relative("2026-10-03T15:00:00Z"), bad: G.relative("nope"), relEl: null };
  await p.ready();
  R.noRtf.relEl = p.$("time[data-relative]").textContent;
  R.noRtf.local = p.$("time[data-local-time]").textContent;
  R.noRtf.title = p.$("time[data-local-time]").getAttribute("title");
  p.click(p.$("#copy"));
  await p.tick(100);
  R.noRtf.copied = copied.slice();
  R.noRtf.errors = p.errors.map(String);
}
out(R);
"""


class Formats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Formats.r is None:
            Formats.r = run_js(self, APP_JS, needs_modules=False, env={"TZ": "UTC"})
        self.r = Formats.r

    def test_one_formatter_per_kind_and_options(self):
        # P5-4: 300 dates in the same style → one Intl.DateTimeFormat, not 300
        self.assertEqual(self.r["cached"]["made"], 1)
        self.assertEqual(self.r["cached"]["outs"], ["Oct 3, 2026, 6:30 PM"])          # Central time (CDT)
        self.assertEqual(self.r["central"], "Oct 3, 2026, 6:30 PM")
        self.assertEqual(self.r["local"], "Oct 3, 2026, 11:30 PM")                     # timeZone: undefined — its own
        self.assertEqual(self.r["madeAfterLocal"], 2)
        self.assertEqual(self.r["month"], "October")
        self.assertEqual(self.r["es"]["date"], "6:30 p. m.")                  # (esMeridiem, as before)

    def test_relative(self):
        rel = self.r["relative"]
        self.assertEqual(rel["inTwoDays"], "in 2 days")
        self.assertEqual((rel["same"], rel["made"]), (1, 1))
        self.assertEqual(rel["ago"], "3 hours ago")
        self.assertEqual(rel["bad"], "")
        self.assertEqual(self.r["es"]["rel"], "ayer")

    def test_without_relative_time_format_the_page_keeps_working(self):
        # P5-7: iOS 13 has no Intl.RelativeTimeFormat — the plain date instead, and the copy button still copies
        n = self.r["noRtf"]
        self.assertEqual(n["relative"], "Oct 3, 2026")
        self.assertEqual(n["bad"], "")
        self.assertEqual(n["relEl"], "Oct 3, 2026")
        self.assertEqual(n["local"], "Oct 3, 2026, 11:30 PM")
        self.assertEqual(n["title"], "Oct 3, 2026")
        self.assertEqual(n["copied"], ["the meeting ID"])
        self.assertEqual(n["errors"], [])


if __name__ == "__main__":
    unittest.main()
