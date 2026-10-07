"""Times the site's build works out from the settings, and the one it prints from its own clock:

  * the committee meeting, as config/site.yml `meeting:` gives it — src/_data/meeting.js (the home page, the
    dates on /meetings/, the countdown's rule) and eleventy/filters/committee.js (/events/, the calendar files,
    the "Every third Wednesday of the month · 7:00 – 8:00 PM" line) read it the way the daily sync does
    (scripts/sync/meeting.py meeting_rule, through eleventy.config.js monthlyRule): "7:00 PM", "7pm", 19 or an
    unquoted 19:00 never stop the build or turn into 7 AM, an end that is not after the start makes it one
    hour long, "sábado" and "third" are read as the sync reads them — so every page shows the dates and times
    of data/site/events.json;
  * the footer's © year: the year in Central time (a build on the evening of Dec 31 is not next year yet).

The settings are written here (each in a folder of its own), not read from config/site.yml. The checks run
the JavaScript with Node.js (tests/nodejs.py) and are skipped without Node.js or the site's npm packages.

    python -m unittest tests.test_build_times -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402

CHI = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)      # the October meeting's day, 10 AM CDT
LINE = "Every third Wednesday of the month · 7:00 – 8:00 PM"

# name: (the settings as the committee might write them, /meetings/' line for them)
CONFIGS = {
    "as written": ('meeting: {week_of_month: 3, weekday: "wednesday", start: "19:00", end: "20:00"}', LINE),
    "12-hour clock": ('meeting: {start: "7:00 PM", end: "8:00 PM"}', LINE),
    "7pm": ("meeting: {start: 7pm, end: 8pm}", LINE),
    "hours only": ("meeting: {start: 19, end: 20}", LINE),
    "unquoted": ("meeting: {start: 19:00, end: 20:00}", LINE),       # PyYAML reads 1140 / 1200 (minutes)
    "19h00": ('meeting: {start: "19h00", end: "8.00 p.m."}', LINE),
    "end before the start": ('meeting: {start: "19:00", end: "08:00"}', LINE),
    "no end": ('meeting: {start: "18:30"}', "Every third Wednesday of the month · 6:30 – 7:30 PM"),
    "late start": ('meeting: {start: "23:30"}', "Every third Wednesday of the month · 11:30 – 11:59 PM"),
    # an end earlier on the clock, at most 12 hours later: the next morning (meeting.py overnight) — every page
    # agrees with the sync's dates, never a one-hour meeting
    "overnight": ('meeting: {start: "22:00", end: "01:00"}', "Every third Wednesday of the month · 10:00 PM – 1:00 AM"),
    "overnight, 12-hour clock": ('meeting: {start: "11:00 PM", end: "12:30 AM"}',
                                 "Every third Wednesday of the month · 11:00 PM – 12:30 AM"),
    "words": ("meeting: {week_of_month: third, weekday: sábado, start: late}", "Every third Saturday of the month · 7:00 – 8:00 PM"),
    "one skip date": ("meeting: {week_of_month: -1, weekday: Friday, skip_dates: 2026-10-30}",
                      "Every last Friday of the month · 7:00 – 8:00 PM"),
    "empty": ("meeting: {}", LINE),
    "nothing": ("meeting:", LINE),
}

JS = r"""
const RealDate = Date;
const fixed = RealDate.parse(input.now);
// "now" for src/_data/meeting.js and committee.js meetingDates (both read the clock)
class FixedDate extends RealDate {
  constructor(...a) { if (a.length) super(...a); else super(fixed); }
  static now() { return fixed; }
}
const meetingData = (await imp("src/_data/meeting.js")).default;
const siteData = (await imp("src/_data/site.js")).default;
const C = await imp("eleventy/filters/committee.js");
const root = process.cwd();
const res = {};
for (const [name, dir] of input.dirs) {
  globalThis.Date = FixedDate;
  try {
    process.chdir(dir);                                 // the data files read config/site.yml from here …
    const mt = meetingData(), site = siteData();
    process.chdir(root);                                // … the filters their words from src/_i18n
    res[name] = {
      rule: mt.rule, upcoming: mt.upcoming,
      ruleObj: filters.cmRuleObj(site.meeting),
      line: `${filters.cmRule(site.meeting, "en")} · ${filters.cmTimeRange(site.meeting, "en")}`.replace(/[\u2009\u202f\u00a0]/g, " "),
      dates: C.meetingDates(site.meeting, 0, 11),
    };
  } catch (e) {
    res[name] = "throws " + e.message;
  } finally {
    globalThis.Date = RealDate;
    process.chdir(root);
  }
}
out(res);
"""


def iso(s: str) -> str:
    return s.replace(".000Z", "Z")


class CommitteeMeetingTimes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-meeting-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        dirs = []
        for i, (name, (text, _)) in enumerate(CONFIGS.items()):
            d = self.tmp / f"c{i}"
            (d / "config").mkdir(parents=True)
            (d / "config" / "site.yml").write_text(text + "\n", encoding="utf-8")
            dirs.append([name, str(d)])
        self.got = run_js(self, JS, data={"now": NOW.isoformat(), "dirs": dirs})

    def test_the_same_meetings_as_the_sync(self):
        for name, (text, _) in CONFIGS.items():
            with self.subTest(settings=name):
                g = self.got[name]
                self.assertIsInstance(g, dict, g)                      # never a stopped build
                rule = M.meeting_rule((yaml.safe_load(text) or {}).get("meeting"))
                # the home page and /meetings/: the next 12 meetings, as events.json lists them
                want = M.upcoming_rule_dates(rule, 12, CHI, NOW)
                self.assertEqual([{k: iso(v) for k, v in d.items()} for d in g["upcoming"]], want)
                # /events/ and the calendar files: every meeting from October to next September
                since = datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc)
                months = [d for d in M.upcoming_rule_dates(rule, 13, CHI, since) if d["ymd"] < "2027-10"]
                self.assertEqual([{k: iso(v) for k, v in d.items()} for d in g["dates"]], months)
                # the countdown's rule — the home page's (meeting.js) and /events/' (cmRuleObj) are one rule
                (sh, sm), (eh, em) = rule.span()
                js_rule = dict(g["rule"], start=g["rule"].get("start") or "19:00")
                self.assertEqual({k: js_rule[k] for k in ("weekday", "n", "start", "end")},
                                 {"weekday": (rule.weekday + 1) % 7, "n": rule.week_of_month,
                                  "start": f"{sh:02d}:{sm:02d}", "end": f"{eh:02d}:{em:02d}"})
                self.assertEqual({k: g["ruleObj"][k] for k in ("weekday", "n", "start", "end", "skip")},
                                 {k: js_rule[k] for k in ("weekday", "n", "start", "end", "skip")})
                self.assertLessEqual(set(rule.skip), set(g["rule"]["skip"]))

    def test_the_line_on_meetings(self):
        for name, (_, line) in CONFIGS.items():
            with self.subTest(settings=name):
                self.assertEqual(self.got[name]["line"], line)

    def test_an_end_before_the_start_on_the_meeting_day(self):
        # 10 AM on the meeting day: an end written as "08:00" does not make the October meeting over already
        g = self.got["end before the start"]
        self.assertEqual((g["upcoming"][0]["ymd"], g["rule"]["end"]), ("2026-10-21", "20:00"))


class FooterYear(unittest.TestCase):
    def test_the_year_in_central_time(self):
        got = run_js(self, "out(input.map((v) => filters.year(v)))",
                     data=["2027-01-01T02:30:00Z", "2027-01-01T06:30:00Z", "2026-12-31", "2027-01-01", "", None])
        # 8:30 PM on Dec 31 in Texas is 2026 still; 12:30 AM on Jan 1 is 2027
        self.assertEqual(got, [2026, 2027, 2026, 2027, "", ""])


if __name__ == "__main__":
    unittest.main()
