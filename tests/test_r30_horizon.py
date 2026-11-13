"""Round 30 — every date through December 2028: config/site.yml `events_until` ("2028-12-31", the last day of Panel 77).

The owner (Nov 13, 2026): "go ahead and all the dates till december 31 of 2028". One top-level setting says how far
ahead the committee meeting and each monthly event (`recurring_events:`) are listed — on /events/, in the calendar
files and on the event share pages: every date through its MONTH, never fewer than this month and the 12 after it (the
floor, MEETING_MONTHS_AHEAD: the lists keep rolling once that day is near or past), never more than 60 months
(WINDOW_MONTHS_MAX). The sync works it out (scripts/sync/meeting.py window_months → build_data.committee_meetings and
recurring_events) and so do the pages (eleventy/filters/committee.js meetingMonthsAhead → normalizeEvents' window,
src/pages/events-ics.11ty.js); tests/test_r24_meeting_window.py runs the two on the same clocks and settings. Here:

  * on Nov 13, 2026 with "2028-12-31": the committee meeting's 26 dates (Nov 18, 2026 … Dec 20, 2028) on both sides
    — the sync's records, /events/' cards (both languages, no extra card from a record), /events.ics —; the CityWide
    booth's 26 (Nov 14, 2026 … Dec 9, 2028), the Grapevine Meeting's 25 (from its first date, Dec 2, 2026, … Dec 6,
    2028), La Viña's workshop's 20 (Jan 28, 2027 … Oct 26, 2028: its six skip dates — Thanksgiving and Christmas
    week of 2026, 2027 and 2028 — left out) — the same dates on the pages and in both calendar files;
  * the floor: on Mar 1, 2028 (December 2028 only 9 months away) still this month and the 12 after it; without the
    setting exactly as before round 30 (the committee meeting 12 months ahead, each series its `months_ahead`
    dates); `months_ahead` a minimum (a series that asks for more dates than the window gets them);
  * the slips: a setting that is not a date is ignored (as if left out) and named in the run summary
    (status.json problems.recurring_events: "config/site.yml events_until …"); a typo two centuries away lists 60
    months and says so; never a stopped update;
  * the reminder (status.json reminders, "events-until"): from 90 days before the day (Oct 2, 2028), and once it has
    passed, the run summary asks for the next panel's last day ("2030-12-31");
  * RealSettings (scripts/ops/gate_tests.py CONTENT_TESTS): config/site.yml as the committee keeps it — "2028-12-31",
    every Thanksgiving (the 4th Thursday of November) through that year in La Viña's skip_dates, and the counts above
    from the real settings.

The settings are written here (round 20's committee meeting and Grapevine Meeting, tests/test_r20_meeting.py, with
the CityWide booth and La Viña's workshop as config/site.yml has them), with fixed clocks; no network, no translation
model.

    python -m unittest tests.test_r30_horizon -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py, test_r20_meeting.py, test_r24_meeting_window.py

from nodejs import run_js  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402
from test_r20_meeting import YAML, NoTranslator, Untranslated, ctx_with  # noqa: E402  (round 20's)
from test_r24_meeting_window import unfold  # noqa: E402

NOW = datetime(2026, 11, 13, 18, 0, tzinfo=timezone.utc)          # Fri Nov 13, 2026, noon CST: the owner's day
NOW_ISO = "2026-11-13T18:00:00Z"
SERIES = ("committee", "citywide-dallas", "grapevine-meeting", "lv-monthly-workshop")
LV_SKIPS = ["2026-11-26", "2026-12-24", "2027-11-25", "2027-12-23", "2028-11-23", "2028-12-28"]

# The CityWide booth and La Viña's workshop as config/site.yml has them (their rules and skip dates)
MORE_SERIES = f"""
- key: "citywide-dallas"
  title: "GV/LV booth at CityWide Dallas"
  title_es: "Mesa de GV/LV en CityWide Dallas"
  summary: "Stop by our Grapevine and La Viña literature table at CityWide Dallas."
  summary_es: "Visita nuestra mesa de literatura de Grapevine y La Viña en CityWide Dallas."
  week_of_month: 2
  weekday: "saturday"
  start: "17:30"
  end: "19:30"
  location: "Lovers Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220"
  months_ahead: 6
  skip_dates: []
- key: "lv-monthly-workshop"
  title: "La Viña Monthly Virtual Workshop (in Spanish)"
  title_es: "Taller Mensual y Virtual de La Viña"
  summary: "In Spanish, open to all."
  summary_es: "En español y abierto a todos."
  host: "lv"
  week_of_month: 4
  weekday: "thursday"
  start: "14:00"
  end: "15:00"
  online_url: "https://zoom.us/j/12345678901"
  months_ahead: 6
  skip_dates: {json.dumps(LV_SKIPS)}
"""


def settings(until=None, **series_ahead) -> dict:
    """Round 20's settings with the two other series, `events_until` (None: left out) and `months_ahead` per key."""
    cfg = yaml.safe_load(YAML)
    cfg["recurring_events"] = yaml.safe_load(MORE_SERIES) + cfg["recurring_events"]
    if until is not None:
        cfg["events_until"] = until
    for e in cfg["recurring_events"]:
        if e["key"] in series_ahead:
            e["months_ahead"] = series_ahead[e["key"]]
    return cfg


def build(cfg: dict, now: datetime = NOW) -> tuple[list[dict], dict]:
    """events.json's events (build_data.build_events: no outside calendar) and the problems for the run summary."""
    ctx = ctx_with(cfg, now=now)
    with mock.patch.object(B, "ics_events", lambda c: []):
        items = B.build_events(ctx)
    return items, dict(ctx.raw_problems)


def upcoming(items: list[dict]) -> dict[str, list[str]]:
    """The dates still to come of each series (the committee meeting under "committee"), soonest first."""
    out: dict[str, list[str]] = {}
    for e in items:
        ex = e.get("extra") or {}
        if ex.get("past") or e.get("category") not in ("committee", "recurring"):
            continue
        key = "committee" if e["category"] == "committee" else ex["series"]
        out.setdefault(key, []).append(e["id"].rsplit(":", 1)[1])
    return {k: sorted(v) for k, v in out.items()}


# The pages' dates of each series still to come (normalizeEvents, both languages: from the sync's records and — the
# committee meeting — from the settings alone), the window's number of months, and both calendar files as
# src/pages/events-ics.11ty.js renders them.
PAGES_JS = r"""
const yaml = await import("js-yaml");
const C = await imp("eleventy/filters/committee.js");
const conf = await imp("eleventy.config.js");
const feed = await imp("src/pages/events-ics.11ty.js");
const cfg = yaml.load(input.yaml);
// (src/_data/site.js passes the top-level events_until on as it is, "" without it)
const site = { ...cfg.site, meeting: cfg.meeting, recurring_events: cfg.recurring_events,
               events_until: cfg.events_until ?? "" };
const at = new Date(input.now);
const dates = (evs) => {
  const o = {};
  for (const e of evs) if (!e.past && (e.committee || e.recurring)) (o[e.committee ? "committee" : e.series] ||= []).push(e.startYmd);
  return o;
};
const res = { months: C.meetingMonthsAhead(site, at), rule: dates(C.normalizeEvents([], site, "en", { now: at })) };
for (const lang of ["en", "es"]) {
  res[lang] = dates(C.normalizeEvents(input.items, site, lang, { now: at }));
  res["ics_" + lang] = feed.render.call({ t: (k, l, v) => conf.translateKey(k, l, v) },
                                        { lang, site, db: { events: { items: input.items } } });
}
out(res);
"""


def ics_dates(ics: str) -> dict[str, list[str]]:
    """A calendar file's dates of each series (from the entries' UIDs: ev-committee-<date>, ev-recurring-<key>-<date>)."""
    out: dict[str, list[str]] = {}
    for line in unfold(ics):
        m = re.fullmatch(r"UID:ev-(?:(committee)|recurring-([a-z0-9-]+?))-(\d{4}-\d{2}-\d{2})(?:-es)?@neta65-gvlv", line)
        if m:
            out.setdefault(m[1] or m[2], []).append(m[3])
    return {k: sorted(v) for k, v in out.items()}


def nths(year_from: int, year_to: int, weekday: int, n: int, months=range(1, 13)) -> list[str]:
    return [M.nth_weekday(y, mo, weekday, n).isoformat() for y in range(year_from, year_to + 1) for mo in months]


# =========================================================================== through Panel 77
class ThroughPanel77(unittest.TestCase):
    """On Nov 13, 2026 with `events_until: "2028-12-31"`: every date of every series through December 2028."""

    WANT = {                               # (how many, the first, the last)
        "committee": (26, "2026-11-18", "2028-12-20"),
        "citywide-dallas": (26, "2026-11-14", "2028-12-09"),
        "grapevine-meeting": (25, "2026-12-02", "2028-12-06"),
        "lv-monthly-workshop": (20, "2027-01-28", "2028-10-26"),
    }

    @classmethod
    def setUpClass(cls):
        with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()):
            cls.cfg = settings("2028-12-31")
            cls.items, cls.problems = build(cls.cfg)
        cls.sync = upcoming(cls.items)

    def test_the_sync_lists_every_date(self):
        self.assertEqual(M.window_months(self.cfg, NOW), 25)
        for key, (n, first, last) in self.WANT.items():
            with self.subTest(series=key):
                got = self.sync[key]
                self.assertEqual((len(got), got[0], got[-1]), (n, first, last))
        # each rule's every day of those months — but La Viña's six skip dates and nothing before a first date
        self.assertEqual(self.sync["committee"], nths(2026, 2028, 2, 3)[10:])
        self.assertEqual(self.sync["citywide-dallas"], nths(2026, 2028, 5, 2)[10:])
        self.assertEqual(self.sync["grapevine-meeting"], nths(2026, 2028, 2, 1)[11:])
        self.assertEqual(self.sync["lv-monthly-workshop"], [d for d in nths(2026, 2028, 3, 4)[10:] if d not in LV_SKIPS])
        # all twelve months of 2028 (the 1st Wednesday of each, the 3rd …)
        for key in ("committee", "citywide-dallas", "grapevine-meeting"):
            self.assertEqual(len([d for d in self.sync[key] if d.startswith("2028-")]), 12, key)
        self.assertEqual(self.problems, {})                       # nothing for the run summary

    def test_the_pages_and_both_calendar_files_list_the_same_dates(self):
        got = run_js(self, PAGES_JS, data={"yaml": yaml.safe_dump(self.cfg, allow_unicode=True), "now": NOW_ISO,
                                           "items": json.loads(json.dumps(self.items))}, now=NOW_ISO)
        self.assertEqual(got["months"], 25)
        # the committee meeting from the settings alone: the sync's dates — so no record of the sync makes a card of
        # its own (normalizeEvents' step 2) and none of the pages' dates goes without its record
        self.assertEqual(got["rule"], {"committee": self.sync["committee"]})
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertEqual(got[lang], self.sync)                                # /events/' cards
                ics = ics_dates(got["ics_" + lang])                                   # /events.ics, /es/events.ics
                self.assertEqual({k: [d for d in v if d >= "2026-11-13"] for k, v in ics.items()}, self.sync)
                # (the files keep the last 90 days, too: the committee meeting's three before it)
                self.assertEqual([d for d in ics["committee"] if d < "2026-11-13"],
                                 ["2026-08-19", "2026-09-16", "2026-10-21"])


# =========================================================================== the floor, and without the setting
class TheFloor(Untranslated):
    """Never fewer than this month and the 12 after it; without `events_until`, exactly as before round 30."""

    def test_near_the_day_the_lists_keep_a_year_ahead(self):
        later = datetime(2028, 3, 1, 18, tzinfo=timezone.utc)      # December 2028 is only 9 months away
        cfg = settings("2028-12-31")
        self.assertEqual(M.window_months(cfg, later), 12)
        got = upcoming(build(cfg, later)[0])
        self.assertEqual((len(got["committee"]), got["committee"][0], got["committee"][-1]),
                         (13, "2028-03-15", "2029-03-21"))
        self.assertEqual((len(got["citywide-dallas"]), got["citywide-dallas"][-1]), (13, "2029-03-10"))
        # and a day that has passed: the same year ahead
        self.assertEqual(upcoming(build(settings("2025-12-31"), later)[0]), got)

    def test_without_the_setting_as_before(self):
        got = upcoming(build(settings())[0])
        self.assertEqual((len(got["committee"]), got["committee"][-1]), (13, "2027-11-17"))
        for key in ("citywide-dallas", "grapevine-meeting", "lv-monthly-workshop"):
            self.assertEqual(len(got[key]), B.RECURRING_AHEAD, key)
        self.assertEqual(got["lv-monthly-workshop"][-1], "2027-06-24")
        # (an empty one is left out, too)
        self.assertEqual(upcoming(build(settings(""))[0]), got)

    def test_months_ahead_is_a_minimum(self):
        # June 2027 is 7 months away: the floor's 12 — 13 booths (Nov 2026 … Nov 2027) — unless a series asks for more
        got = upcoming(build(settings("2027-06-30", **{"citywide-dallas": 24}))[0])
        self.assertEqual((len(got["citywide-dallas"]), got["citywide-dallas"][-1]), (24, "2028-10-14"))
        self.assertEqual((len(got["grapevine-meeting"]), got["grapevine-meeting"][-1]), (12, "2027-11-03"))
        self.assertEqual(len(got["committee"]), 13)


# =========================================================================== slips
class Slips(Untranslated):
    """A hand edit that goes wrong never stops the update: it is ignored, or capped, and the run summary says so."""

    def test_a_setting_that_is_not_a_date_is_ignored_and_named(self):
        with self.assertLogs("build_data", "WARNING") as logs:
            items, problems = build(settings("end of Panel 77"))
        self.assertTrue(any("config/site.yml events_until “end of Panel 77”" in m for m in logs.output), logs.output)
        self.assertEqual(upcoming(items), upcoming(build(settings())[0]))     # as if it were left out
        self.assertEqual(problems["recurring_events"], "config/site.yml events_until “end of Panel 77” is not a date "
                                                       "like \"2028-12-31\" — ignored (as if it were left out)")
        self.assertNotIn("meeting", problems)

    def test_a_typo_two_centuries_away_lists_sixty_months(self):
        with self.assertLogs("build_data", "WARNING"):
            items, problems = build(settings("2208-12-31"))
        got = upcoming(items)
        self.assertEqual((len(got["committee"]), got["committee"][-1]), (61, "2031-11-19"))   # Nov 2026 … Nov 2031
        self.assertEqual((len(got["citywide-dallas"]), got["citywide-dallas"][-1]), (61, "2031-11-08"))
        self.assertEqual(problems["recurring_events"], "config/site.yml events_until “2208-12-31” is more than 60 "
                                                       "months away — the dates are listed through 2031-11 only (is "
                                                       "the year right?)")

    def test_its_note_comes_first_with_the_series_notes(self):
        cfg = settings("someday")
        cfg["recurring_events"][0]["skip_dates"] = ["2026-12-13"]          # a Sunday: no booth day
        with self.assertLogs("build_data", "WARNING"):
            problems = build(cfg)[1]["recurring_events"]
        self.assertTrue(problems.startswith("config/site.yml events_until “someday” is not a date"), problems)
        self.assertIn(" / recurring_events entry 1 (citywide-dallas): skip date “2026-12-13”", problems)
        self.assertEqual(problems.count("config/site.yml"), 1)

    def test_the_reminder_for_the_next_panel(self):
        def due(today: str, until="2028-12-31") -> list[dict]:
            ctx = ctx_with(settings(until))
            return B._events_until_reminders(ctx, ROOT, date.fromisoformat(today))

        self.assertIn(B._events_until_reminders, B.REMINDER_CHECKS)
        self.assertEqual(due("2028-10-01"), [])                            # 91 days before
        want = [{"id": "events-until", "file": "config/site.yml", "due": "2028-12-31",
                 "message": "config/site.yml events_until is 2028-12-31 — the Events page and the calendar files list "
                            "our monthly dates through that month, then only 12 months ahead: set the next panel's "
                            "last day (events_until: \"2030-12-31\")."}]
        self.assertEqual(due("2028-10-02"), want)                          # 90 days before
        self.assertEqual(due("2029-02-01"), want)                          # and once it has passed
        self.assertEqual(due("2028-12-01", until=None), [])                # no setting: nothing to remind
        self.assertEqual(due("2028-12-01", until="someday"), [])           # (a problem of its own)
        self.assertTrue(due("2027-02-01", until="2027-03-15")[0]["message"].endswith('(events_until: "2029-03-31").'))


# =========================================================================== config/site.yml as it is
class RealSettings(Untranslated):
    """config/site.yml as the committee keeps it (scripts/ops/gate_tests.py CONTENT_TESTS): every date through the
    end of Panel 77, and La Viña's Thanksgiving skipped every year through it."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))

    def test_through_the_end_of_panel_77(self):
        self.assertEqual(self.cfg["events_until"], "2028-12-31")         # quoted, as its note shows it
        self.assertEqual((M.window_months(self.cfg, NOW), M.window_notes(self.cfg, NOW)), (25, []))
        ctx = ctx_with(self.cfg, now=NOW)
        with mock.patch.object(B, "ics_events", lambda c: []):
            got = upcoming(B.build_events(ctx))
        self.assertEqual({k: (len(v), v[0], v[-1]) for k, v in got.items()}, ThroughPanel77.WANT)
        self.assertNotIn("recurring_events", ctx.raw_problems)

    def test_every_thanksgiving_is_skipped_through_it(self):
        lv = next(e for e in self.cfg["recurring_events"] if e.get("key") == "lv-monthly-workshop")
        rule = (M.weekday_index(lv["weekday"]), M.week_of_month_value(lv["week_of_month"]))
        self.assertEqual(rule, (3, 4))                                     # the 4th Thursday: Thanksgiving's
        skips = [M.ymd_text(d) for d in lv["skip_dates"]]
        self.assertEqual(M.check_skip_dates(lv["skip_dates"], *rule)[1], [])
        last_year = int(M.events_until(self.cfg)[0][:4])
        for y in range(2026, last_year + 1):
            with self.subTest(year=y):
                self.assertIn(M.nth_weekday(y, 11, 3, 4).isoformat(), skips)
        self.assertIn("2028-12-28", skips)                                 # Christmas week, as in 2024 (to confirm)


if __name__ == "__main__":
    unittest.main()
