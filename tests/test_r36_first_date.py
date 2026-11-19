"""Round 36 — a monthly series' first date is the settings', on every page, even before the sync has run: the owner moved
the Grapevine Meeting's first date from Dec 2, 2026 to Jan 6, 2027 (config/site.yml recurring_events `starts:`), and
data/site/events.json kept the Dec 2 date the last sync wrote until the next one — /events/, the calendar files, its
share page, the monthly toolkit and the search showed a meeting that will never take place (the Code check builds the
pushed commit before the sync runs; a sync that fails would have published it).

  * eleventy.config.js beforeFirstDate: a date of a series ("ev:recurring:<key>:<YYYY-MM-DD>") before the first date
    its settings give (read as every page reads them: monthlyRule — a quoted date, an unquoted YAML one, a key made
    from the title) is taken out; its first date and every later one, a series without `starts`, a series the
    settings do not have (any more), the committee meeting's dates and every other event are kept; a key that
    several entries use counts the earliest of their first dates (none when one has none), never the last one's;
  * src/_data/db.js applies it to events.json once, for every page, with a plain log line (never a build warning: a
    strict build — the Code check — still passes before the sync has run).

    python -m unittest tests.test_r36_first_date -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from nodejs import run_js  # noqa: E402


def rec(series: str, ymd: str, category: str = "recurring", **extra) -> dict:
    """An events.json record of a series' date (build_data.recurring_events' id and extra.series)."""
    return {"id": f"ev:{category}:{series}:{ymd}" if category == "recurring" else f"ev:{category}:{ymd}",
            "category": category, "kind": "event", "source": "committee", "title": series, "date": f"{ymd}T01:00:00Z",
            "extra": {"start": f"{ymd}T01:00:00Z", "series": series, **extra} if category == "recurring"
            else {"start": f"{ymd}T01:00:00Z"}}


class BeforeFirstDate(unittest.TestCase):
    def test_what_is_left_out(self):
        settings = yaml.safe_load("""
recurring_events:
  - key: "grapevine-meeting"
    title: "Grapevine Meeting"
    week_of_month: 1
    weekday: "wednesday"
    start: "19:00"
    starts: "2027-01-06"
  - title: "Booth at the Fair"          # no key: its key is made from the title (booth-at-the-fair)
    week_of_month: 2
    weekday: "saturday"
    start: "17:30"
    starts: 2027-02-13                   # unquoted (Python's date, handed over as its text; the JS Date: below)
  - key: "citywide-dallas"               # no first date: every date stays
    title: "GV/LV booth at CityWide Dallas"
    week_of_month: 2
    weekday: "saturday"
    start: "17:30"
  - key: "typo"
    title: "A first date that is no date"
    week_of_month: 1
    weekday: "monday"
    start: "10:00"
    starts: "soon"                       # counts for nothing (monthlyRule, as the sync's check_starts)
""")
        items = [
            rec("grapevine-meeting", "2026-12-02"),                  # the old first date: out
            rec("grapevine-meeting", "2027-01-06"),                  # the first date: kept
            rec("grapevine-meeting", "2027-02-03"),
            rec("booth-at-the-fair", "2027-01-09"),                  # out
            rec("booth-at-the-fair", "2027-02-13"),
            rec("citywide-dallas", "2026-12-12"),
            rec("typo", "2026-12-07"),
            rec("gone-series", "2026-12-05"),                        # a series no longer in the settings
            rec("x", "2026-12-16", category="committee"),            # the committee meeting's
            {"id": "ev:manual:2026-12-01-workshop", "category": "manual", "kind": "event", "extra": {}},
            # without extra.series: the series is the id's key
            {"id": "ev:recurring:grapevine-meeting:2026-11-04", "category": "recurring", "kind": "event", "extra": {}},
            None,
        ]
        got = run_js(self, r"""
          const C = await imp("eleventy.config.js");
          const r = C.beforeFirstDate(input.items, input.settings.recurring_events);
          const none = C.beforeFirstDate(input.items, undefined);
          out({ kept: r.kept.map((it) => it && it.id), dropped: r.dropped, none: none.dropped.length,
                bad: C.beforeFirstDate(null, null) });
        """, data={"items": items, "settings": json.loads(json.dumps(settings, default=str))})
        self.assertEqual(got["dropped"], ["ev:recurring:grapevine-meeting:2026-12-02", "ev:recurring:booth-at-the-fair:2027-01-09",
                                          "ev:recurring:grapevine-meeting:2026-11-04"])
        self.assertEqual(got["kept"], [
            "ev:recurring:grapevine-meeting:2027-01-06", "ev:recurring:grapevine-meeting:2027-02-03",
            "ev:recurring:booth-at-the-fair:2027-02-13", "ev:recurring:citywide-dallas:2026-12-12",
            "ev:recurring:typo:2026-12-07", "ev:recurring:gone-series:2026-12-05", "ev:committee:2026-12-16",
            "ev:manual:2026-12-01-workshop", None])
        self.assertEqual(got["none"], 0, "no settings: nothing is left out")
        self.assertEqual(got["bad"], {"kept": [], "dropped": []})

    def test_a_key_used_twice_never_hides_a_real_date(self):
        """A copied block whose key was not changed (the sync keeps the first entry it can read, skips the other and
        the Status page names it): the earliest first date of the two counts, none when one has none — never the
        last entry's alone, which would leave out the dates the sync wrote for the first."""
        def entry(key: str, starts=None, weekday: str = "wednesday") -> dict:
            e = {"key": key, "title": key, "week_of_month": 1, "weekday": weekday, "start": "19:00"}
            if starts is not None:
                e["starts"] = starts
            return e

        items = [rec("gvm", "2026-12-02"), rec("gvm", "2027-01-06"), rec("gvm", "2027-02-03"), rec("gvm", "2027-06-02")]
        cases = {
            # the first entry's Jan 6, a copy's June 2: only what is before Jan 6 goes
            "later_copy": [entry("gvm", "2027-01-06"), entry("gvm", "2027-06-02")],
            # the same the other way round
            "earlier_copy": [entry("gvm", "2027-06-02"), entry("gvm", "2027-01-06")],
            # the first entry has no first date (the sync writes every date): nothing goes, whatever the copy says
            "first_without": [entry("gvm"), entry("gvm", "2027-06-02")],
            "copy_without": [entry("gvm", "2027-06-02"), entry("gvm")],
            # a first entry the sync cannot read (no such weekday: skipped) — the copy it keeps has no first date
            "unreadable_first": [entry("gvm", "2027-06-02", weekday="wensday"), entry("gvm")],
        }
        got = run_js(self, r"""
          const C = await imp("eleventy.config.js");
          const r = {};
          for (const [name, rec] of Object.entries(input.cases)) r[name] = C.beforeFirstDate(input.items, rec).dropped;
          out(r);
        """, data={"items": items, "cases": cases})
        self.assertEqual(got["later_copy"], ["ev:recurring:gvm:2026-12-02"])
        self.assertEqual(got["earlier_copy"], ["ev:recurring:gvm:2026-12-02"])
        self.assertEqual(got["first_without"], [])
        self.assertEqual(got["copy_without"], [])
        self.assertEqual(got["unreadable_first"], [])

    def test_an_unquoted_date_reaches_the_build_as_a_date(self):
        """config/site.yml read by js-yaml (src/_data/site.js): an unquoted `starts: 2027-01-06` is a Date there."""
        got = run_js(self, r"""
          const yaml = await import("js-yaml");
          const C = await imp("eleventy.config.js");
          const cfg = yaml.load("recurring_events:\n  - key: gvm\n    title: GVM\n    week_of_month: 1\n    weekday: wednesday\n"
            + "    start: '19:00'\n    starts: 2027-01-06\n");
          out(C.beforeFirstDate([{ id: "ev:recurring:gvm:2026-12-02", category: "recurring", extra: { series: "gvm" } },
                                 { id: "ev:recurring:gvm:2027-01-06", category: "recurring", extra: { series: "gvm" } }],
                                cfg.recurring_events));
        """)
        self.assertEqual(got["dropped"], ["ev:recurring:gvm:2026-12-02"])
        self.assertEqual([it["id"] for it in got["kept"]], ["ev:recurring:gvm:2027-01-06"])


class TheBuildsData(unittest.TestCase):
    """src/_data/db.js on events.json of the test's own (SITE_DATA) and config/site.yml as it is: a date before the
    first date of a series the settings give one is gone from db.events, with a log line and no build warning."""

    def test_db_leaves_it_out(self):
        cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8")) or {}
        entries = cfg.get("recurring_events") or []
        entries = entries if isinstance(entries, list) else [entries]
        first = next(((str(e["key"]), str(e["starts"])[:10]) for e in entries
                      if isinstance(e, dict) and re.fullmatch(r"[a-z0-9-]{1,32}", str(e.get("key") or ""))
                      and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("starts") or "")[:10])), None)
        if not first:
            self.skipTest("no series in config/site.yml has a first date (starts:)")
        key, starts = first
        tmp = Path(tempfile.mkdtemp(prefix="gv-r36-first-date-"))
        try:
            (tmp / "events.json").write_text(json.dumps({"updated": None, "items": [
                rec(key, "2000-01-05"), rec(key, starts), rec("zz-other-series", "2000-01-05")]}), encoding="utf-8")
            got = run_js(self, r"""
              const W = await imp("eleventy/build-warnings.js");
              const D = await imp("src/_data/db.js");
              const log = console.log, warn = console.warn, logged = [];
              console.log = (s) => logged.push(String(s)); console.warn = () => {};
              try {
                W.clearBuildWarnings();
                const db = D.default();
                out({ ids: db.events.items.map((it) => it.id), logged: logged.filter((s) => s.startsWith("[events]")),
                      warnings: W.buildWarnings() });
              } finally { console.log = log; console.warn = warn; }
            """, env={"SITE_DATA": str(tmp)})
        finally:
            shutil.rmtree(tmp, True)
        self.assertEqual(got["ids"], [f"ev:recurring:{key}:{starts}", "ev:recurring:zz-other-series:2000-01-05"])
        self.assertEqual(got["logged"], [
            "[events] left out 1 date(s) before their series' first date (config/site.yml starts) — the next sync removes "
            f"them from data/site/events.json: ev:recurring:{key}:2000-01-05"])
        self.assertEqual(got["warnings"], [])


if __name__ == "__main__":
    unittest.main()
