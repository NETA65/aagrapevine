"""Monthly date rules that run past midnight (scripts/sync/meeting.py MonthlyRule.span / upcoming_rule_dates):
an end earlier than the start is the next morning when the event then lasts at most OVERNIGHT_MAX_HOURS
("22:00"–"01:00"), never a one-hour event; a missing end, or one further back ("19:00"–"08:00"), still makes
a one-hour event, as the web pages show it.
Run:  python -m unittest tests.test_meeting_rule -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402

CHI = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


class Overnight(unittest.TestCase):
    def test_overnight(self):
        self.assertTrue(M.overnight((22, 0), (1, 0)))
        self.assertTrue(M.overnight((19, 0), (7, 0)), "twelve hours: still the next morning")
        self.assertFalse(M.overnight((19, 0), (8, 0)), "thirteen hours: a slip of the pen")
        self.assertFalse(M.overnight((19, 0), (20, 0)), "the same day")
        self.assertFalse(M.overnight((19, 0), (19, 0)))
        self.assertTrue(M.overnight((23, 0), (0, 30), max_hours=3))
        self.assertFalse(M.overnight((11, 0), (0, 0), max_hours=3))

    def test_span(self):
        night = M.MonthlyRule(week_of_month=-1, weekday=5, start=(22, 0), end=(1, 0))
        self.assertEqual(night.span(), ((22, 0), (1, 0)))
        self.assertTrue(night.ends_next_day())
        slip = M.MonthlyRule(week_of_month=-1, weekday=5, start=(19, 0), end=(8, 0))
        self.assertEqual(slip.span(), ((19, 0), (20, 0)))
        self.assertFalse(slip.ends_next_day())
        same = M.MonthlyRule(week_of_month=-1, weekday=5, start=(23, 30), end=(23, 30))
        self.assertEqual(same.span(), ((23, 30), (23, 59)), "no end: one hour, at most to 23:59")


class Dates(unittest.TestCase):
    def test_the_end_is_the_next_morning(self):
        """The last Saturday of the month, 10 PM to 1 AM Central: Oct 31 → Nov 1 crosses the end of daylight
        saving time too (1:00 AM CDT = 06:00 UTC), Nov 28 → Nov 29 is in CST (07:00 UTC)."""
        rule = M.MonthlyRule(week_of_month=-1, weekday=5, start=(22, 0), end=(1, 0))
        got = M.upcoming_rule_dates(rule, 2, CHI, NOW)
        self.assertEqual(got, [
            {"ymd": "2026-10-31", "start": "2026-11-01T03:00:00Z", "end": "2026-11-01T06:00:00Z"},
            {"ymd": "2026-11-28", "start": "2026-11-29T04:00:00Z", "end": "2026-11-29T07:00:00Z"}])

    def test_a_running_overnight_event_is_still_listed(self):
        rule = M.MonthlyRule(week_of_month=-1, weekday=5, start=(22, 0), end=(1, 0))
        at_half_past_midnight = datetime(2026, 11, 29, 6, 30, tzinfo=timezone.utc)      # 12:30 AM CST, Nov 29
        self.assertEqual(M.upcoming_rule_dates(rule, 1, CHI, at_half_past_midnight)[0]["ymd"], "2026-11-28")

    def test_one_hour_rules_are_unchanged(self):
        rule = M.MonthlyRule(week_of_month=3, weekday=2, start=(19, 0), end=(20, 0))
        self.assertEqual(M.upcoming_rule_dates(rule, 1, CHI, NOW),
                         [{"ymd": "2026-10-21", "start": "2026-10-22T00:00:00Z", "end": "2026-10-22T01:00:00Z"}])

    def test_the_committee_meeting(self):
        late = M.meeting_rule({"start": "23:00", "end": "00:30"})
        self.assertEqual(late.span(), ((23, 0), (0, 30)))
        self.assertEqual(M.upcoming_meetings(1, now=NOW, cfg={"meeting": {"start": "23:00", "end": "00:30"}})[0],
                         {"ymd": "2026-10-21", "start": "2026-10-22T04:00:00Z", "end": "2026-10-22T05:30:00Z"})
        no_end = M.meeting_rule({"start": "23:30"})
        self.assertEqual(no_end.span(), ((23, 30), (23, 59)), "as /meetings/ and the home page show it")


class RecurringEventNotes(unittest.TestCase):
    """build_data.recurring_specs: an overnight end is no longer "not after the start — shown as one hour"."""

    def problems(self, start: str, end: str) -> list[str]:
        ctx = B.Ctx(offline=True)
        ctx.cfg = yaml.safe_load(f"""
recurring_events:
  - key: "night-owls"
    title: "Night Owls workshop"
    week_of_month: -1
    weekday: "saturday"
    start: "{start}"
    end: "{end}"
""")
        ctx.now = NOW
        ctx.now_ts = NOW.timestamp()
        ctx.today_local = NOW.astimezone(ctx.tz).date()
        return B.recurring_specs(ctx)[1]

    def test_notes(self):
        self.assertEqual(self.problems("22:00", "01:00"), [])
        self.assertEqual(len(self.problems("19:00", "08:00")), 1)
        self.assertIn("not after the start — shown as one hour long", self.problems("19:00", "08:00")[0])


if __name__ == "__main__":
    unittest.main()
