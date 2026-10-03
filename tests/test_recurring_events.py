"""Offline tests for monthly recurring events: the date rule shared by the committee meeting and
config/site.yml `recurring_events:` (scripts/sync/meeting.py), the events build_data makes of them
(scripts/sync/build_data.py) and the monthly e-mail's handling (scripts/notify/send_digest.py).

La Viña's monthly workshop on Zoom (`lv-monthly-workshop`) adds an event the committee does not hold:
`host: lv` (shown with the Grapevine / La Viña calendars, in La Viña's colour), online only (`online_url`
and `meeting_id`, no `location`), and its flyer found on the Drive by `flyer_match` — under the flyer's
first name and the name it was given later. Its dates (the 4th Thursday; the last Thursday tried too)
across the daylight-saving changes and in months with five Thursdays; the same date listed by La Viña's
own calendar (aalavina.org: an all-day "Taller Mensual" whose place is the Zoom link) or an .ics feed is
shown once; a listing on another day of the month tells the chair which skip date to add (not when La Viña
lists that month's own date too); La Viña's listing of a skipped month (Thanksgiving) is that month's date,
with the series' words; an unknown `host:` in a content/events file is listed, the event still shows. The
pages' side (committee.js, home.js — the home row keeps no place for La Viña's series —, monthly.js,
community.js, library.js, event-tone.js) runs with Node.js; in the calendars a date that has passed links to
/events/ itself (its card is gone), and the repeat line names its time zone.

The settings are written here, not read from config/site.yml, so the chair can change the real
booth (or add others) without turning these tests red. No network, no translation model.

    python -m unittest tests.test_recurring_events -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unicodedata
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py, test_events_feeds.py (its calendar helper)

from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import events_external as E  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402
from scripts.sync.common import event_host  # noqa: E402
from scripts.sync.meeting import MonthlyRule, upcoming_rule_dates  # noqa: E402

CHI = ZoneInfo("America/Chicago")
TODAY = datetime(2026, 9, 24, 15, 0, tzinfo=timezone.utc)          # Thu Sep 24, 2026, 10 AM CDT
BOOTH = MonthlyRule(week_of_month=2, weekday=5, start=(17, 0), end=(20, 0))   # 2nd Saturday 5–8 PM

CITYWIDE_YAML = """
site: {timezone: America/Chicago}
recurring_events:
  - key: "citywide-dallas"
    title: "GV/LV booth at CityWide Dallas"
    title_es: "Mesa de GV/LV en CityWide Dallas"
    summary: "Our literature table at CityWide Dallas."
    summary_es: "Nuestra mesa de literatura en CityWide Dallas."
    week_of_month: 2
    weekday: "saturday"
    start: 17:00
    end: "20:00"
    location: "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220"
    url: "https://citywidedallasaa.org"
    months_ahead: 6
    skip_dates: []
"""


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def ctx_with(cfg_yaml: str | dict, now: datetime = TODAY) -> B.Ctx:
    """A build context with the given settings and a fixed clock (no raw data)."""
    ctx = B.Ctx(offline=True)
    ctx.cfg = yaml.safe_load(cfg_yaml) if isinstance(cfg_yaml, str) else cfg_yaml
    ctx.now = now
    ctx.now_ts = now.timestamp()
    ctx.today_local = now.astimezone(ctx.tz).date()
    return ctx


class NoTranslator:
    """Stands in for the translation model: tests never download or run it."""
    def translate(self, texts, src, tgt):
        return [(None, False) for _ in texts]


# --------------------------------------------------------------------------- the date rule
class MonthlyRuleDates(unittest.TestCase):
    def test_second_saturday_for_13_months_across_both_dst_changes(self):
        got = upcoming_rule_dates(BOOTH, 13, CHI, TODAY)
        self.assertEqual([d["ymd"] for d in got], [
            "2026-10-10", "2026-11-14", "2026-12-12", "2027-01-09", "2027-02-13", "2027-03-13", "2027-04-10",
            "2027-05-08", "2027-06-12", "2027-07-10", "2027-08-14", "2027-09-11", "2027-10-09"])
        starts = {d["ymd"]: d["start"] for d in got}
        ends = {d["ymd"]: d["end"] for d in got}
        # 17:00 Central = 22:00 UTC with daylight time (CDT, until Nov 1, 2026 / from Mar 14, 2027) …
        self.assertEqual(starts["2026-10-10"], "2026-10-10T22:00:00Z")
        self.assertEqual(ends["2026-10-10"], "2026-10-11T01:00:00Z")
        # … and 23:00 UTC with standard time (CST): after the Nov 1 switch, and on Mar 13 (DST starts Mar 14)
        self.assertEqual(starts["2026-11-14"], "2026-11-14T23:00:00Z")
        self.assertEqual(ends["2026-11-14"], "2026-11-15T02:00:00Z")
        self.assertEqual(starts["2027-03-13"], "2027-03-13T23:00:00Z")
        self.assertEqual(starts["2027-04-10"], "2027-04-10T22:00:00Z")
        self.assertEqual(starts["2027-10-09"], "2027-10-09T22:00:00Z")
        for d in got:            # always 5–8 PM on the local clock, whatever the season
            s, e = utc(d["start"]).astimezone(CHI), utc(d["end"]).astimezone(CHI)
            self.assertEqual((s.date().isoformat(), s.hour, s.minute, e.hour), (d["ymd"], 17, 0, 20))

    def test_on_the_day_the_clocks_change(self):
        first_sunday = MonthlyRule(week_of_month=1, weekday=6, start=(17, 0), end=(20, 0))
        nov = upcoming_rule_dates(first_sunday, 1, CHI, datetime(2026, 10, 20, tzinfo=timezone.utc))
        self.assertEqual(nov[0], {"ymd": "2026-11-01", "start": "2026-11-01T23:00:00Z", "end": "2026-11-02T02:00:00Z"})
        second_sunday = MonthlyRule(week_of_month=2, weekday=6, start=(17, 0), end=(20, 0))
        mar = upcoming_rule_dates(second_sunday, 1, CHI, datetime(2027, 3, 1, tzinfo=timezone.utc))
        self.assertEqual(mar[0], {"ymd": "2027-03-14", "start": "2027-03-14T22:00:00Z", "end": "2027-03-15T01:00:00Z"})

    def test_skip_dates_leave_a_month_out_and_the_count_stays(self):
        rule = MonthlyRule(week_of_month=2, weekday=5, start=(17, 0), end=(20, 0),
                           skip=frozenset({"2026-12-12", "2027-01-09"}))
        got = [d["ymd"] for d in upcoming_rule_dates(rule, 4, CHI, TODAY)]
        self.assertEqual(got, ["2026-10-10", "2026-11-14", "2027-02-13", "2027-03-13"])

    def test_last_weekday_of_the_month(self):
        last_saturday = MonthlyRule(week_of_month=-1, weekday=5, start=(17, 0), end=(20, 0))
        got = [d["ymd"] for d in upcoming_rule_dates(last_saturday, 5, CHI, TODAY)]
        self.assertEqual(got, ["2026-09-26", "2026-10-31", "2026-11-28", "2026-12-26", "2027-01-30"])

    def test_fifth_weekday_only_in_months_that_have_one(self):
        fifth_saturday = MonthlyRule(week_of_month=5, weekday=5, start=(10, 0), end=(12, 0))
        got = [d["ymd"] for d in upcoming_rule_dates(fifth_saturday, 3, CHI, TODAY)]
        self.assertEqual(got, ["2026-10-31", "2027-01-30", "2027-05-29"])

    def test_year_boundary_and_an_event_still_running(self):
        self.assertEqual(upcoming_rule_dates(BOOTH, 1, CHI, datetime(2026, 12, 20, tzinfo=timezone.utc))[0]["ymd"],
                         "2027-01-09")
        # Last Wednesday of September 2026, 7–8 PM CDT = Oct 1, 00:00–01:00 UTC. At 00:30 UTC it is already
        # October in UTC, but the meeting is still going on: it is still the "next" one.
        last_wed = MonthlyRule(week_of_month=-1, weekday=2, start=(19, 0), end=(20, 0))
        got = upcoming_rule_dates(last_wed, 2, CHI, datetime(2026, 10, 1, 0, 30, tzinfo=timezone.utc))
        self.assertEqual([d["ymd"] for d in got], ["2026-09-30", "2026-10-28"])
        # … and once it has ended it is gone
        done = upcoming_rule_dates(BOOTH, 1, CHI, datetime(2026, 10, 11, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(done[0]["ymd"], "2026-11-14")

    def test_recent_dates_on_request(self):
        got = [d["ymd"] for d in upcoming_rule_dates(BOOTH, 5, CHI, TODAY, include_recent_days=90)]
        self.assertEqual(got, ["2026-07-11", "2026-08-08", "2026-09-12", "2026-10-10", "2026-11-14"])

    def test_missing_or_earlier_end_means_one_hour(self):
        rule = MonthlyRule(week_of_month=2, weekday=5, start=(17, 0), end=(9, 0))
        d = upcoming_rule_dates(rule, 1, CHI, TODAY)[0]
        self.assertEqual(utc(d["end"]) - utc(d["start"]), utc("2026-10-10T23:00:00Z") - utc("2026-10-10T22:00:00Z"))

    def test_setting_values_written_every_way(self):
        for v, want in [(2, 2), ("2", 2), ("2nd", 2), ("second", 2), ("Segundo", 2), ("2.º", 2), ("last", -1),
                        ("último", -1), (-1, -1), (0, None), (6, None), ("often", None), (None, None), (True, None)]:
            self.assertEqual(M.week_of_month_value(v), want, v)
        for v, want in [("saturday", 5), ("Saturday", 5), ("SATURDAYS", 5), ("sábado", 5), ("Sábados", 5),
                        ("sabado", 5), ("miércoles", 2), ("funday", None), ("", None), (None, None)]:
            self.assertEqual(M.weekday_index(v), want, v)
        self.assertEqual(M.ymd_text(date(2027, 1, 9)), "2027-01-09")
        self.assertEqual(M.ymd_text("2027-01-09"), "2027-01-09")
        self.assertIsNone(M.ymd_text("2027-02-30"))
        self.assertIsNone(M.ymd_text("next month"))

    def test_committee_meeting_rule_unchanged(self):
        cfg = {"site": {"timezone": "America/Chicago"},
               "meeting": {"weekday": "wednesday", "week_of_month": 3, "start": "19:00", "end": "20:00"}}
        rule = M.meeting_rule(cfg["meeting"])
        self.assertEqual(rule, MonthlyRule(3, 2, (19, 0), (20, 0), frozenset()))
        got = upcoming_rule_dates(rule, 3, CHI, TODAY)
        self.assertEqual(got[0], {"ymd": "2026-10-21", "start": "2026-10-22T00:00:00Z", "end": "2026-10-22T01:00:00Z"})
        self.assertEqual(got[1]["start"], "2026-11-19T01:00:00Z")          # CST from November
        # anything unreadable keeps the old defaults: 3rd Wednesday, 19:00–20:00
        self.assertEqual(M.meeting_rule({"weekday": "someday", "week_of_month": "x", "start": "late"}),
                         MonthlyRule(3, 2, (19, 0), (20, 0), frozenset()))
        with mock.patch.object(M, "load_config", lambda: cfg):
            self.assertEqual(len(M.upcoming_meetings(12)), 12)


# --------------------------------------------------------------------------- build_data
class RecurringEventsBuild(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())
        p.start()
        self.addCleanup(p.stop)

    def test_ids_times_and_texts(self):
        ctx = ctx_with(CITYWIDE_YAML)
        evs = B.recurring_events(ctx)
        self.assertEqual(ctx.raw_problems, {})
        by_id = {e["id"]: e for e in evs}
        upcoming = [e for e in evs if B.ts(e["extra"]["end"]) >= TODAY.timestamp()]
        self.assertEqual([e["id"] for e in upcoming], [f"ev:recurring:citywide-dallas:{d}" for d in (
            "2026-10-10", "2026-11-14", "2026-12-12", "2027-01-09", "2027-02-13", "2027-03-13")])
        oct_, nov = by_id["ev:recurring:citywide-dallas:2026-10-10"], by_id["ev:recurring:citywide-dallas:2026-11-14"]
        self.assertEqual((oct_["extra"]["start"], oct_["extra"]["end"]), ("2026-10-10T22:00:00Z", "2026-10-11T01:00:00Z"))
        self.assertEqual((nov["extra"]["start"], nov["extra"]["end"]), ("2026-11-14T23:00:00Z", "2026-11-15T02:00:00Z"))
        self.assertEqual(oct_["date"], oct_["extra"]["start"])
        # dates of the last 90 days are kept too (for calendar subscribers; build_events marks them past)
        self.assertIn("ev:recurring:citywide-dallas:2026-09-12", by_id)
        self.assertIn("ev:recurring:citywide-dallas:2026-07-11", by_id)
        self.assertNotIn("ev:recurring:citywide-dallas:2026-06-13", by_id)
        self.assertEqual((oct_["source"], oct_["kind"], oct_["category"]), ("committee", "event", "recurring"))
        self.assertEqual(oct_["url"], "https://citywidedallasaa.org")
        ex = oct_["extra"]
        self.assertEqual((ex["all_day"], ex["city"], ex["state"], ex["online_url"], ex["recurring"], ex["series"]),
                         (False, "Dallas", "TX", None, True, "citywide-dallas"))
        self.assertIsNone(ex["flyer_url"])
        self.assertIsNone(ex["flyer_thumb"])
        self.assertEqual(ex["location"], "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220")
        self.assertEqual(oct_["i18n"]["title"], {"en": "GV/LV booth at CityWide Dallas", "es": "Mesa de GV/LV en CityWide Dallas"})
        self.assertEqual(oct_["i18n"]["summary"]["es"], "Nuestra mesa de literatura en CityWide Dallas.")
        self.assertEqual(oct_["i18n"]["recurrence_label"], {
            "en": "Every second Saturday of the month · 5:00\u2009–\u20098:00 PM",
            "es": "Cada segundo sábado del mes · 5:00–8:00\u00a0p.\u00a0m."})
        # the rule itself, in the shape of `meeting:` — the web pages write the line from it with the
        # committee meeting's own helpers (eleventy/filters/committee.js recurrenceText)
        self.assertEqual(ex["rule"], {"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "20:00"})
        self.assertEqual(oct_["machine"], [])
        self.assertIs(oct_["is_new"], False)

    def test_recurrence_labels(self):
        # worded like the committee meeting's line ("Every third Wednesday of the month · 7:00 – 8:00 PM"),
        # time ranges as the browser writes them (thin spaces around the dash; none in "5:00–8:00 p. m.")
        rule = MonthlyRule(week_of_month=-1, weekday=6, start=(11, 30), end=(13, 0))
        self.assertEqual(B.recurrence_label(rule), {
            "en": "Every last Sunday of the month · 11:30 AM\u2009–\u20091:00 PM",
            "es": "Cada último domingo del mes · 11:30\u00a0a.\u00a0m.\u2009–\u20091:00\u00a0p.\u00a0m."})
        self.assertEqual(B.recurrence_label(MonthlyRule(1, 0, (9, 0), (11, 0)))["es"],
                         "Cada primer lunes del mes · 9:00–11:00\u00a0a.\u00a0m.")
        self.assertEqual(B.recurrence_label(MonthlyRule(3, 2, (19, 0), (20, 0)))["en"],
                         "Every third Wednesday of the month · 7:00\u2009–\u20098:00 PM")
        # a 23:30 start with no end: the one-hour rule stops at 23:59 (the same day) — so does extra.rule
        late = MonthlyRule(2, 5, (23, 30), (23, 30))
        self.assertEqual(B.rule_fields(late), {"week_of_month": 2, "weekday": "saturday", "start": "23:30", "end": "23:59"})
        self.assertEqual(B.rule_fields(rule)["week_of_month"], -1)

    def test_words_match_the_committee_meeting_line(self):
        """The rule words are the site's own (src/_i18n/committee.json), so the booth's line and the
        committee meeting's line on /meetings/ can never be worded differently."""
        strings = json.loads((ROOT / "src" / "_i18n" / "committee.json").read_text(encoding="utf-8"))
        for lang in ("en", "es"):
            self.assertEqual(B._RULE[lang], strings["committee.rule"][lang], lang)
            for n, word in B._ORD_WORDS[lang].items():
                key = "committee.ord." + ("last" if n == -1 else str(n))
                self.assertEqual(word, strings[key][lang], (lang, key))

    def test_a_skip_date_that_is_not_the_events_day_is_reported(self):
        """A likely slip (the Sunday, the 1st Saturday, the wrong month) would skip nothing: it is ignored
        as before, but the chair is told (status.json problems.recurring_events → Actions summary)."""
        ctx = ctx_with(CITYWIDE_YAML.replace("    skip_dates: []",
                                             '    skip_dates: ["2026-11-14", 2027-01-09, "2027-02-30", "garbage", '
                                             '"2026-10-11", "2026-12-05"]'))
        evs = B.recurring_events(ctx)
        days = [e["extra"]["start"][:10] for e in evs if B.ts(e["extra"]["end"]) >= TODAY.timestamp()]
        self.assertEqual(days, ["2026-10-10", "2026-12-12", "2027-02-13", "2027-03-13", "2027-04-10", "2027-05-08"])
        report = ctx.raw_problems["recurring_events"]
        self.assertIn("skip date “2026-10-11” is not the 2nd Saturday of its month — ignored "
                      "(that month's is 2026-10-10)", report)
        self.assertIn("skip date “2026-12-05” is not the 2nd Saturday of its month — ignored "
                      "(that month's is 2026-12-12)", report)
        for words in ("“2027-02-30” is not a date", "“garbage” is not a date"):
            self.assertIn(words, report)
        for fine in ("2026-11-14", "2027-01-09"):             # real 2nd Saturdays (quoted or not): no note
            self.assertNotIn(f"“{fine}”", report)
        # a "5th Saturday" rule and a month that has none; the last Friday of the month
        _, problems = B.recurring_specs(ctx_with("""
recurring_events:
  - {title: "Fifth", week_of_month: 5, weekday: saturday, start: "10:00", skip_dates: ["2026-11-28", "2026-10-31"]}
  - {title: "Last", week_of_month: -1, weekday: friday, start: "10:00", skip_dates: ["2026-10-30", "2026-10-23"]}
"""))
        text = " / ".join(problems)
        self.assertIn("“2026-11-28” is not the 5th Saturday of its month — ignored (that month has no 5th Saturday)", text)
        self.assertIn("“2026-10-23” is not the last Friday of its month — ignored (that month's is 2026-10-30)", text)
        self.assertNotIn("“2026-10-31”", text)
        self.assertNotIn("“2026-10-30”", text)

    def test_never_new_never_in_whats_new_never_a_past_event(self):
        ctx = ctx_with(CITYWIDE_YAML)
        with mock.patch.object(B, "ics_events", lambda c: []):
            evs = B.build_events(ctx)
        rec = [e for e in evs if e["category"] == "recurring"]
        self.assertEqual(len(rec), 9)                       # 6 ahead + 3 in the last 90 days
        for e in rec:
            e["first_seen"] = "2026-09-24T10:00:00Z"        # even if the robot "found" it today
            self.assertFalse(ctx.is_new(e, B.raw_source(e)), e["id"])
        wn = B.plan_whatsnew(ctx, {"events": evs})
        self.assertFalse([it["id"] for _, it in wn if it.get("category") == "recurring"])
        past = [e["extra"]["start"][:10] for e in rec if e["extra"]["past"]]
        self.assertEqual(past, ["2026-09-12", "2026-08-08", "2026-07-11"])
        self.assertEqual(sum(1 for e in rec if not e["extra"]["past"]), 6)

    def test_past_dates_do_not_push_out_real_past_events(self):
        ctx = ctx_with(CITYWIDE_YAML)
        old = [{"id": f"ev:manual:old-{i}", "source": "committee", "kind": "event", "title": f"Old {i}", "lang": "en",
                "date": f"2026-0{1 + i % 8}-0{1 + i % 9}", "category": "manual", "status": "ok", "extra": {}}
               for i in range(15)]
        with mock.patch.object(B, "ics_events", lambda c: []), \
                mock.patch.object(B.Ctx, "items", lambda self, name: old if name == "manual_events" else []):
            evs = B.build_events(ctx)
        past_manual = [e for e in evs if e["category"] == "manual" and e["extra"]["past"]]
        self.assertEqual(len(past_manual), B.PAST_EVENTS_KEEP)
        self.assertEqual(sum(1 for e in evs if e["category"] == "recurring" and e["extra"]["past"]), 3)

    def test_bad_entries_are_skipped_and_reported(self):
        ctx = ctx_with("""
recurring_events:
  - key: "citywide-dallas"
    title: "Booth"
    week_of_month: 2
    weekday: "saturday"
    start: "17:00"
    end: "20:00"
  - "just a line of text"
  - title: "No such day"
    week_of_month: 2
    weekday: "funday"
    start: "17:00"
  - title: "Week seven"
    week_of_month: 7
    weekday: "saturday"
    start: "17:00"
  - key: "citywide-dallas"
    title: "Same key again"
    week_of_month: 1
    weekday: "friday"
    start: "18:00"
  - title: "No start"
    week_of_month: 1
    weekday: "friday"
  - week_of_month: 1
    weekday: "friday"
    start: "18:00"
  - key: "Second Friday Workshop!"
    title: "Workshop"
    week_of_month: "2nd"
    weekday: "Viernes"
    start: "6:30 PM"
    end: "6 PM"
    url: "not a link"
    months_ahead: 99
    skip_dates: ["2026-10-09", "someday"]
""")
        with mock.patch.object(B, "ics_events", lambda c: []):
            evs = B.build_events(ctx)             # never raises
        series = {e["extra"]["series"] for e in evs if e["category"] == "recurring"}
        self.assertEqual(series, {"citywide-dallas", "second-friday-workshop"})
        report = ctx.raw_problems["recurring_events"]
        for words in ("entry 2", "entry 3", "funday", "entry 4", "week_of_month “7”", "used twice", "entry 6",
                      "start time", "entry 7", "needs a title", "not after the start", "not a web address",
                      "months_ahead", "someday"):
            self.assertIn(words, report)
        self.assertNotIn("entry 1 ", report)
        ws = [e for e in evs if e["extra"].get("series") == "second-friday-workshop" and not e["extra"]["past"]]
        self.assertEqual(len(ws), B.RECURRING_AHEAD)                 # months_ahead 99 → the default
        self.assertNotIn("2026-10-09", [e["extra"]["start"][:10] for e in ws])      # skipped
        first = ws[0]
        self.assertEqual(first["extra"]["start"], "2026-11-14T00:30:00Z")          # Fri Nov 13, 6:30 PM CST
        self.assertEqual(B.ts(first["extra"]["end"]) - B.ts(first["extra"]["start"]), 3600)   # one hour
        self.assertEqual(first["url"], "/events/")                   # bad link left out → our own page

    def test_not_a_list_is_reported_not_fatal(self):
        for cfg in ("recurring_events: oops", "recurring_events: 5"):
            ctx = ctx_with(cfg)
            self.assertEqual(B.recurring_events(ctx), [])
            self.assertIn("recurring_events", ctx.raw_problems)
        ctx = ctx_with("recurring_events:")
        self.assertEqual(B.recurring_events(ctx), [])
        self.assertEqual(ctx.raw_problems, {})
        ctx = ctx_with("meeting: {}")
        self.assertEqual(B.recurring_events(ctx), [])

    def test_a_crash_is_contained(self):
        ctx = ctx_with(CITYWIDE_YAML)
        with mock.patch.object(B, "recurring_events", side_effect=RuntimeError("boom")), \
                mock.patch.object(B, "ics_events", lambda c: []):
            evs = B.build_events(ctx)
        self.assertIn("recurring_events", ctx.raw_problems)
        self.assertFalse([e for e in evs if e["category"] == "recurring"])

    def test_only_english_given_spanish_is_machine_translated(self):
        class Stub:
            def translate(self, texts, src, tgt):
                return [(f"[{tgt}] {t}", True) for t in texts]

        ctx = ctx_with(CITYWIDE_YAML.replace('    title_es: "Mesa de GV/LV en CityWide Dallas"\n', "")
                       .replace('    summary_es: "Nuestra mesa de literatura en CityWide Dallas."\n', ""))
        with mock.patch.object(B.T, "get_translator", lambda **kw: Stub()):
            ev = B.recurring_events(ctx)[0]
        self.assertEqual(ev["i18n"]["title"]["es"], "[es] GV/LV booth at CityWide Dallas")
        self.assertEqual(ev["i18n"]["summary"]["es"], "[es] Our literature table at CityWide Dallas.")
        self.assertEqual(ev["machine"], ["es"])
        self.assertEqual(ev["i18n"]["recurrence_label"]["es"], "Cada segundo sábado del mes · 5:00–8:00\u00a0p.\u00a0m.")
        # translation not possible right now: the English shows in both, nothing marked "auto-translated"
        ev = B.recurring_events(ctx_with(CITYWIDE_YAML.replace('    title_es: "Mesa de GV/LV en CityWide Dallas"\n', "")))[0]
        self.assertEqual(ev["i18n"]["title"]["es"], "GV/LV booth at CityWide Dallas")
        self.assertEqual(ev["machine"], [])


# --------------------------------------------------------------------------- monthly e-mail
class DigestEmail(unittest.TestCase):
    def test_the_booth_that_took_place_is_in_its_months_digest(self):
        """The monthly digest recaps the month before: the booth's September date is in the September
        digest (sent October 1) — with its day only, no "every month" —, never on its own "news"."""
        from scripts.notify import send_digest as D
        now = datetime(2026, 10, 1, 15, 5, tzinfo=timezone.utc)     # the September digest goes out
        ctx = ctx_with(CITYWIDE_YAML, now)
        with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()), \
                mock.patch.object(B, "ics_events", lambda c: []):
            events = B.build_events(ctx)                # keeps the booth dates of the last 90 days (past: true)
        with mock.patch.object(D, "load_items", lambda name: events if name == "events" else []), \
                mock.patch.object(D, "load_file", lambda name: {}), mock.patch.object(D, "load_config", lambda: {}):
            data = D.collect(now)                       # September only: Sep 12 (Oct 10 is the October digest's)
        booth = [e for e in data["events"] if e["category"] == "recurring"]
        self.assertEqual([e["id"] for e in booth], ["ev:recurring:citywide-dallas:2026-09-12"])
        self.assertEqual(D.total_count(data), 0)            # nothing new → no e-mail that month
        row = D.event_row(booth[0], "es", D.Links("https://example.org"))
        self.assertEqual(row["when"], "sáb, 12 de sept")     # the day only (as the website writes it): no time, no "cada mes"
        self.assertEqual(row["url"], "https://citywidedallasaa.org")


# --------------------------------------------------------------------------- La Viña's monthly workshop
NOW_OCT = datetime(2026, 10, 1, 21, 0, tzinfo=timezone.utc)        # Thu Oct 1, 2026, 4 PM CDT
EAST = ZoneInfo("America/New_York")
ZOOM = "https://us06web.zoom.us/j/81595931777"
FLYER_ID = "16Tm35F7P7ynir3lH03wZBWmVE0MllVuR"
# The flyer's name on the committee's Drive when it was uploaded, and the name it was given afterwards
OLD_NAME = ("Taller informativo mensual de La Viña se lleva a cabo el último jueves de cada mes a las 200 p. m. CT "
            "a través de Zoom 81595931777.png")
NEW_NAME = "Taller Mensual y Virtual de La Viña - último jueves de cada mes, 3 p. m. (hora del Este), por Zoom.png"
LV_ENTRY = """  - key: "lv-monthly-workshop"
    title: "La Viña Monthly Virtual Workshop (in Spanish)"
    title_es: "Taller Mensual y Virtual de La Viña"
    summary: "La Viña's monthly Zoom workshop, in Spanish and open to everyone."
    summary_es: "El taller mensual de La Viña por Zoom, en español y abierto a todos."
    host: "lv"
    week_of_month: 4
    weekday: "thursday"
    start: "14:00"
    end: "15:00"
    online_url: "https://us06web.zoom.us/j/81595931777"
    meeting_id: "815 9593 1777"
    contact: "lveditorial@aagrapevine.org"
    flyer_match: "taller (informativo )?mensual( y virtual)? de la vi[nñ]a"
    months_ahead: 6
    skip_dates: ["2026-11-26", "2026-12-24"]
"""
LV_YAML = CITYWIDE_YAML + LV_ENTRY          # the booth stays as it is, next to La Viña's workshop
LV_ID = "ev:recurring:lv-monthly-workshop:"


def flyer(name: str, fid: str = FLYER_ID, day: str = "2026-10-01", kind: str = "photo", **extra) -> dict:
    """A committee Drive file as drive.py lists it (data/raw/drive.json): its title is the name without the
    extension and without a date at its start (drive.py keeps that in extra.event_date / event_month)."""
    title = extra.pop("title", name.rsplit(".", 1)[0])
    view = f"https://drive.google.com/file/d/{fid}/view"
    return {"id": f"drive:{fid}", "source": "drive", "kind": kind, "url": view, "title": title, "lang": "es",
            "date": day, "first_seen": f"{day}T15:25:08Z", "category": "flyers", "status": "ok",
            "extra": {"file_id": fid, "mime": "image/png", "name": name, "view_url": view,
                      "thumb_url": f"https://lh3.googleusercontent.com/d/{fid}=w600", "is_image": True, "is_pdf": False,
                      **extra}}


def dated_flyer(day: str, fid: str) -> dict:
    """'2026-10-22 Taller Mensual y Virtual de La Viña 2-3pm.png' as drive.py reads it: an event of that day."""
    return flyer(f"{day} Taller Mensual y Virtual de La Viña 2-3pm.png", fid, title="Taller Mensual y Virtual de La Viña 2-3pm",
                 event_date=day, event_title="Taller Mensual y Virtual de La Viña", event_time="14:00",
                 event_end_time="15:00", event_location=None, event_tz=None)


def la_vina_listing(day: str, slug: str = "taller-mensual") -> dict:
    """La Viña's own calendar page for one date of the workshop, as events_external.py turns it into an event (the
    real aalavina.org/get-involved/events/2026-09-24/taller-mensual): an all-day "Taller Mensual" whose place is
    the Zoom link — no time, no description."""
    url = f"https://www.aalavina.org/get-involved/events/{day}/{slug}"
    return E.build_item(url, E.decide({"title": "Taller Mensual", "start": day, "all_day": True, "location_raw": ZOOM,
                                       "lang": "es"}))


def lv_ctx(now: datetime = NOW_OCT, cfg: str = LV_YAML, **raw: list[dict]) -> B.Ctx:
    """ctx_with + the raw items of some sources (drive=[…], events_external=[…], manual_events=[…])."""
    ctx = ctx_with(cfg, now)
    for name, items in raw.items():
        ctx.raw[name] = {"items": items}
    return ctx


def lv_dates(evs: list[dict]) -> list[dict]:
    return [e for e in evs if e["id"].startswith(LV_ID)]


class LaVinaWorkshopDates(unittest.TestCase):
    """2 PM Central — 3 PM Eastern, La Viña's own time (both zones change their clocks the same night) — on the
    4th Thursday, as La Viña's calendar has listed it (also in months with five Thursdays); the last Thursday,
    the rule first given, is checked too."""
    FOURTH = MonthlyRule(week_of_month=4, weekday=3, start=(14, 0), end=(15, 0))
    LAST = MonthlyRule(week_of_month=-1, weekday=3, start=(14, 0), end=(15, 0))

    def check_clock(self, got: list[dict]) -> None:
        for d in got:
            s, e = utc(d["start"]), utc(d["end"])
            self.assertEqual((s.astimezone(CHI).weekday(), s.astimezone(CHI).hour, e.astimezone(CHI).hour,
                              s.astimezone(EAST).hour, s.astimezone(CHI).date().isoformat()), (3, 14, 15, 15, d["ymd"]), d)

    def test_the_fourth_thursday(self):
        got = upcoming_rule_dates(self.FOURTH, 8, CHI, NOW_OCT)
        # October, December and April have five Thursdays (the last ones: Oct 29, Dec 31, Apr 29): still the 4th
        self.assertEqual([d["ymd"] for d in got], ["2026-10-22", "2026-11-26", "2026-12-24", "2027-01-28",
                                                   "2027-02-25", "2027-03-25", "2027-04-22", "2027-05-27"])
        starts = {d["ymd"]: d["start"] for d in got}
        self.assertEqual(starts["2026-10-22"], "2026-10-22T19:00:00Z")      # CDT
        self.assertEqual(starts["2026-11-26"], "2026-11-26T20:00:00Z")      # CST from Nov 1
        self.assertEqual(starts["2027-02-25"], "2027-02-25T20:00:00Z")
        self.assertEqual(starts["2027-03-25"], "2027-03-25T19:00:00Z")      # CDT again from Mar 14
        self.check_clock(got)

    def test_the_last_thursday(self):
        got = upcoming_rule_dates(self.LAST, 8, CHI, NOW_OCT)
        self.assertEqual([d["ymd"] for d in got], ["2026-10-29", "2026-11-26", "2026-12-31", "2027-01-28",
                                                   "2027-02-25", "2027-03-25", "2027-04-29", "2027-05-27"])
        starts = {d["ymd"]: d["start"] for d in got}
        self.assertEqual(starts["2026-10-29"], "2026-10-29T19:00:00Z")      # still CDT: the clocks change Sun Nov 1
        self.assertEqual(starts["2026-12-31"], "2026-12-31T20:00:00Z")      # New Year's Eve, CST
        self.assertEqual(starts["2027-04-29"], "2027-04-29T19:00:00Z")
        self.check_clock(got)

    def test_the_series_leaves_out_thanksgiving_and_christmas_eve(self):
        evs = lv_dates(B.recurring_events(lv_ctx()))
        upcoming = [e["id"][len(LV_ID):] for e in evs if B.ts(e["extra"]["end"]) >= NOW_OCT.timestamp()]
        self.assertEqual(upcoming, ["2026-10-22", "2027-01-28", "2027-02-25", "2027-03-25", "2027-04-22", "2027-05-27"])
        # the last 90 days stay for calendar subscribers (build_events marks them past)
        self.assertEqual(sorted(e["id"][len(LV_ID):] for e in evs if B.ts(e["extra"]["end"]) < NOW_OCT.timestamp()),
                         ["2026-07-23", "2026-08-27", "2026-09-24"])


class LaVinaWorkshopSettings(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())
        p.start()
        self.addCleanup(p.stop)

    def test_the_entry(self):
        ctx = lv_ctx(drive=[flyer(NEW_NAME)])
        evs = B.recurring_events(ctx)
        self.assertEqual(ctx.raw_problems, {})
        ev = next(e for e in evs if e["id"] == LV_ID + "2026-10-22")
        ex = ev["extra"]
        self.assertEqual((ev["category"], ev["source"], ev["url"], ev["lang"]), ("recurring", "committee", "/events/", "en"))
        # online only: no place, the Zoom link and meeting ID, its platform — and who holds it
        self.assertEqual((ex["location"], ex["city"], ex["state"]), (None, None, None))
        self.assertEqual((ex["online_url"], ex["online"], ex["platform"], ex["meeting_id"], ex["host"]),
                         (ZOOM, True, "Zoom", "815 9593 1777", "lv"))
        self.assertEqual(ex["contact"], "lveditorial@aagrapevine.org")       # its own line on the card
        self.assertEqual((ex["flyer_url"], ex["flyer_thumb"]), (f"https://drive.google.com/file/d/{FLYER_ID}/view",
                                                                f"https://lh3.googleusercontent.com/d/{FLYER_ID}=w600"))
        self.assertEqual(ex["rule"], {"week_of_month": 4, "weekday": "thursday", "start": "14:00", "end": "15:00"})
        self.assertEqual(ev["i18n"]["title"], {"en": "La Viña Monthly Virtual Workshop (in Spanish)",
                                               "es": "Taller Mensual y Virtual de La Viña"})
        self.assertEqual(ev["i18n"]["recurrence_label"], {
            "en": "Every fourth Thursday of the month · 2:00 – 3:00 PM",
            "es": "Cada cuarto jueves del mes · 2:00–3:00 p. m."})
        self.assertEqual(ev["machine"], [])
        # the booth is ours and in person, as before
        booth = next(e for e in evs if e["id"] == "ev:recurring:citywide-dallas:2026-10-10")["extra"]
        self.assertEqual((booth["host"], booth["online"], booth["platform"], booth["meeting_id"], booth["flyer_url"],
                          booth["contact"]), ("neta", False, None, None, None, None))
        self.assertEqual(booth["location"], "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220")

    def test_host_values(self):
        for v, want in [(None, "neta"), ("", "neta"), ("neta", "neta"), ("NETA 65", "neta"), ("neta65", "neta"),
                        ("Comité", "neta"), ("lv", "lv"), ("LV", "lv"), ("La Viña", "lv"), ("la vina", "lv"),
                        ("gv", "gv"), ("Grapevine", "gv"), ("AA Grapevine", "gv"), ("aagrapevine", None), ("us", None),
                        ("La  Viña", "lv"), (5, None)]:
            self.assertEqual(event_host(v), want, v)

    def test_mistakes_are_noted_and_the_event_still_shows(self):
        bad = LV_ENTRY.replace('host: "lv"', 'host: "aagrapevine"') \
                      .replace('meeting_id: "815 9593 1777"', 'meeting_id: "ask the chair!"') \
                      .replace('contact: "lveditorial@aagrapevine.org"', 'contact: "<b>write to us</b>"') \
                      .replace('flyer_match: "taller (informativo )?mensual( y virtual)? de la vi[nñ]a"',
                               'flyer_match: "taller (mensual"')
        ctx = lv_ctx(cfg=CITYWIDE_YAML + bad, drive=[flyer(NEW_NAME)])
        evs = lv_dates(B.recurring_events(ctx))
        report = ctx.raw_problems["recurring_events"]
        self.assertIn("recurring_events entry 2 (lv-monthly-workshop): host “aagrapevine” must be", report)
        self.assertIn("meeting_id “ask the chair!” is not a meeting ID", report)
        self.assertIn("flyer_match “taller (mensual” is not a pattern the site can read", report)
        self.assertIn("contact “<b>write to us</b>” is not an e-mail address", report)
        self.assertNotIn("skipped", report)
        ex = evs[0]["extra"]          # shown all the same: ours by default, no ID, no contact, no flyer
        self.assertEqual((ex["host"], ex["meeting_id"], ex["contact"], ex["flyer_url"], ex["online_url"]),
                         ("neta", None, None, None, ZOOM))
        # an address written as a link is the address
        linked = LV_ENTRY.replace('"lveditorial@aagrapevine.org"', '"mailto:lveditorial@aagrapevine.org"')
        ctx = lv_ctx(cfg=CITYWIDE_YAML + linked, drive=[flyer(NEW_NAME)])
        self.assertEqual(lv_dates(B.recurring_events(ctx))[0]["extra"]["contact"], "lveditorial@aagrapevine.org")
        self.assertEqual(ctx.raw_problems, {})
        # a meeting ID that is not the link's meeting is shown (the chair checks which one is right); a pattern
        # that matches an empty name would take any file: refused
        odd = LV_ENTRY.replace('"815 9593 1777"', '"815 9593 1778"').replace(
            '"taller (informativo )?mensual( y virtual)? de la vi[nñ]a"', '".*"')
        ctx = lv_ctx(cfg=CITYWIDE_YAML + odd, drive=[flyer(NEW_NAME)])
        ex = lv_dates(B.recurring_events(ctx))[0]["extra"]
        self.assertEqual((ex["meeting_id"], ex["flyer_url"]), ("815 9593 1778", None))
        report = ctx.raw_problems["recurring_events"]
        self.assertIn("meeting_id “815 9593 1778” is not the meeting online_url opens (Zoom meeting 81595931777)", report)
        self.assertIn("flyer_match “.*” would match every file on the Drive — no flyer", report)
        # several patterns: any one of them
        listed = LV_ENTRY.replace('"taller (informativo )?mensual( y virtual)? de la vi[nñ]a"',
                                  '["reunión abierta", "taller mensual y virtual"]')
        ex = lv_dates(B.recurring_events(lv_ctx(cfg=CITYWIDE_YAML + listed, drive=[flyer(NEW_NAME)])))[0]["extra"]
        self.assertTrue(ex["flyer_url"])


class LaVinaWorkshopFlyer(unittest.TestCase):
    """`flyer_match` finds the flyer by a pattern, never by its exact name: the first name, the new one, accents
    written the Mac way (NFD), capitals, a name without the ñ."""

    def setUp(self):
        p = mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())
        p.start()
        self.addCleanup(p.stop)

    def flyer_of(self, evs: list[dict], day: str) -> str | None:
        return next(e for e in evs if e["id"] == LV_ID + day)["extra"]["flyer_url"]

    def test_found_under_both_names(self):
        view = f"https://drive.google.com/file/d/{FLYER_ID}/view"
        for name in (OLD_NAME, NEW_NAME, unicodedata.normalize("NFD", NEW_NAME), NEW_NAME.upper(),
                     "Taller Mensual y Virtual de La Vina.jpg", "taller informativo mensual de la viña.pdf"):
            ctx = lv_ctx(drive=[flyer(name)])
            evs = B.recurring_events(ctx)
            for day in ("2026-10-22", "2027-01-28", "2026-09-24"):
                self.assertEqual(self.flyer_of(evs, day), view, (name, day))
            self.assertEqual(ctx.raw_problems, {})

    def test_both_names_are_the_series_flyer(self):
        """drive.py reads no date from either name (no event_date / event_month): the flyer of EVERY date, never
        one date's or one month's — "último jueves de cada mes, 3 p. m." names no day."""
        from scripts.sync import drive as D
        for name in (OLD_NAME, NEW_NAME):
            self.assertEqual(D.name_date(D.strip_ext(name))[0], None, name)

    def test_no_match_no_flyer_and_no_problem(self):
        ctx = lv_ctx(drive=[flyer("2027-03-14 Spring Assembly GV booth.pdf", "X1"), flyer("Taller de Escritura.png", "X2")])
        evs = B.recurring_events(ctx)
        self.assertIsNone(self.flyer_of(evs, "2026-10-22"))
        self.assertEqual(ctx.raw_problems, {})

    def test_the_newest_wins_and_a_bulletin_post_is_no_flyer(self):
        older, newer = flyer(OLD_NAME, "OLD", day="2026-09-01"), flyer(NEW_NAME, "NEW", day="2026-10-01")
        post = flyer("Taller mensual de La Viña: notas.docx", "POST", day="2026-10-02", kind="announcement")
        evs = B.recurring_events(lv_ctx(drive=[older, post, newer]))
        self.assertEqual(self.flyer_of(evs, "2026-10-22"), "https://drive.google.com/file/d/NEW/view")

    def test_a_flyer_for_one_date_or_one_month(self):
        """A dated flyer is its day's own: on a date of the series it is that date's flyer and no second event
        (one date, one card); on another day — a date La Viña moved — it stays an event of its own, with the
        series' host, Zoom link and meeting ID. A name with only a month is that month's."""
        drive = [flyer(NEW_NAME), dated_flyer("2026-10-22", "D1022"), dated_flyer("2026-11-19", "D1119"),
                 flyer("Enero 2027 Taller Mensual y Virtual de La Viña.png", "M2701", title="Enero 2027 Taller Mensual y Virtual de La Viña",
                       event_month="2027-01")]
        ctx = lv_ctx(drive=drive)
        with mock.patch.object(B, "ics_events", lambda c: []):
            evs = B.build_events(ctx)
        self.assertEqual(self.flyer_of(evs, "2026-10-22"), "https://drive.google.com/file/d/D1022/view")
        self.assertEqual(self.flyer_of(evs, "2027-01-28"), "https://drive.google.com/file/d/M2701/view")
        self.assertEqual(self.flyer_of(evs, "2027-02-25"), f"https://drive.google.com/file/d/{FLYER_ID}/view")
        flyers = {e["id"]: e for e in evs if e["category"] == "flyer"}
        self.assertEqual(sorted(flyers), ["ev:flyer:D1119"])           # Oct 22's flyer is no second event
        moved = flyers["ev:flyer:D1119"]["extra"]
        self.assertEqual((moved["host"], moved["online_url"], moved["online"], moved["platform"], moved["meeting_id"],
                          moved["contact"]), ("lv", ZOOM, True, "Zoom", "815 9593 1777", "lveditorial@aagrapevine.org"))
        self.assertEqual((moved["start"], moved["end"]), ("2026-11-19T20:00:00Z", "2026-11-19T21:00:00Z"))


class LaVinaWorkshopListings(unittest.TestCase):
    """La Viña's own calendar (events_external) and the .ics feeds may list a date of the workshop too: the
    site shows it ONCE — ours, with its time, words, Zoom ID and flyer."""

    def setUp(self):
        p = mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())
        p.start()
        self.addCleanup(p.stop)

    def build(self, **raw) -> tuple[B.Ctx, list[dict]]:
        ctx = lv_ctx(drive=[flyer(NEW_NAME)], **raw)
        with mock.patch.object(B, "ics_events", lambda c: []):
            evs = B.build_events(ctx)
        return ctx, evs

    def test_la_vinas_own_listing_of_a_date_shows_once(self):
        listing = la_vina_listing("2026-10-22")
        self.assertEqual((listing["category"], listing["extra"]["all_day"], listing["extra"]["location"],
                          listing["extra"]["online_url"]), ("lv-calendar", True, "Zoom", ZOOM))
        ctx, evs = self.build(events_external=[listing])
        self.assertEqual([e for e in evs if e["category"] == "lv-calendar"], [])
        ours = next(e for e in evs if e["id"] == LV_ID + "2026-10-22")
        self.assertEqual((ours["extra"]["also_on_calendar"], ours["extra"]["calendar_match"]), ("lv-calendar", "online"))
        self.assertEqual((ours["extra"]["start"], ours["url"]), ("2026-10-22T19:00:00Z", "/events/"))    # ours wins
        self.assertEqual(ctx.raw_problems, {})

    def test_a_listing_on_another_day_is_kept_and_the_chair_told(self):
        ctx, evs = self.build(events_external=[la_vina_listing("2026-10-29")])
        kept = [e for e in evs if e["category"] == "lv-calendar"]
        self.assertEqual([e["extra"]["start"] for e in kept], ["2026-10-29"])
        self.assertIn(LV_ID + "2026-10-22", {e["id"] for e in evs})
        report = ctx.raw_problems["recurring_events"]
        self.assertIn("recurring_events entry 2 (lv-monthly-workshop): La Viña's calendar (aalavina.org) lists it on "
                      "2026-10-29 (https://www.aalavina.org/get-involved/events/2026-10-29/taller-mensual), but the "
                      "rule gives 2026-10-22 — if that month's date moved, add \"2026-10-22\" to its skip_dates", report)
        # the chair's to settle: La Viña's listing stays as La Viña wrote it until then
        self.assertEqual((kept[0]["title"], kept[0]["extra"].get("series_of")), ("Taller Mensual", None))

    def test_a_second_session_in_the_room_is_no_moved_date(self):
        """La Viña lists the rule's day AND another session in the workshop's room that month (a special workshop
        on the 5th Thursday): the rule's date is confirmed by La Viña itself — the other listing stays, and the
        chair is not asked to skip it."""
        ctx, evs = self.build(events_external=[la_vina_listing("2026-10-22"),
                                               la_vina_listing("2026-10-29", "taller-especial")])
        self.assertEqual([e["url"] for e in evs if e["category"] == "lv-calendar"],
                         ["https://www.aalavina.org/get-involved/events/2026-10-29/taller-especial"])
        self.assertEqual(next(e for e in evs if e["id"] == LV_ID + "2026-10-22")["extra"]["calendar_match"], "online")
        self.assertEqual(ctx.raw_problems, {})

    def test_a_skipped_month_is_la_vinas_listing_with_the_series_words(self):
        """November's 4th Thursday is Thanksgiving (skip_dates): La Viña's own listing of that month — Thursday,
        Nov 19, in the workshop's Zoom room — IS November's date of the workshop. It stays La Viña's listing (its
        day, no time, its page) with the series' title and summary in both languages, host, meeting ID and flyer;
        no note for the chair."""
        ctx, evs = self.build(events_external=[la_vina_listing("2026-11-19")])
        nov = [e for e in evs if e["category"] == "lv-calendar"]
        self.assertEqual([e["extra"]["start"] for e in nov], ["2026-11-19"])
        self.assertEqual(ctx.raw_problems, {})
        ev, ex = nov[0], nov[0]["extra"]
        self.assertEqual((ev["url"], ex["all_day"]), ("https://www.aalavina.org/get-involved/events/2026-11-19/taller-mensual", True))
        self.assertEqual((ex["series_of"], ex["host"], ex["online_url"], ex["online"], ex["platform"], ex["meeting_id"],
                          ex["contact"]), ("lv-monthly-workshop", "lv", ZOOM, True, "Zoom", "815 9593 1777",
                                           "lveditorial@aagrapevine.org"))
        self.assertEqual(ex["flyer_url"], f"https://drive.google.com/file/d/{FLYER_ID}/view")
        self.assertEqual(ev["i18n"]["title"], {"en": "La Viña Monthly Virtual Workshop (in Spanish)",
                                               "es": "Taller Mensual y Virtual de La Viña"})
        self.assertEqual(ev["i18n"]["summary"]["es"], "El taller mensual de La Viña por Zoom, en español y abierto a todos.")
        self.assertEqual((ev["title"], ev["lang"], ev["machine"]), ("La Viña Monthly Virtual Workshop (in Spanish)", "en", []))
        B.I18n(NoTranslator()).apply(ev)          # the translation step keeps the series' words ("Taller Mensual"
        self.assertEqual(ev["i18n"]["title"]["en"], "La Viña Monthly Virtual Workshop (in Spanish)")   # is never shown)
        self.assertNotIn("_fixed_i18n", ev)
        # a convention over several days in that room in November is something else: untouched
        convention = E.build_item("https://www.aalavina.org/get-involved/events/2026-11-05/convencion",
                                  E.decide({"title": "Convención Hispana Virtual", "start": "2026-11-05", "end": "2026-11-07",
                                            "all_day": True, "location_raw": ZOOM, "lang": "es"}))
        _ctx, evs = self.build(events_external=[convention])
        conv = next(e for e in evs if e["category"] == "lv-calendar")
        self.assertEqual((conv["title"], conv["extra"].get("series_of"), conv["extra"].get("host")),
                         ("Convención Hispana Virtual", None, None))

    def test_other_events_of_la_vinas_calendar_are_untouched(self):
        convention = E.build_item("https://www.aalavina.org/get-involved/events/2026-10-22/convencion-virtual",
                                  E.decide({"title": "Convención Hispana Virtual", "start": "2026-10-22", "end": "2026-10-24",
                                            "all_day": True, "location_raw": "https://us02web.zoom.us/j/1234567890",
                                            "lang": "es"}))
        _ctx, evs = self.build(events_external=[convention])
        self.assertEqual([e["id"] for e in evs if e["category"] == "lv-calendar"], [convention["id"]])

    def test_an_ics_feed_listing_shows_once(self):
        """A feed (Google Calendar, neta65.org …) listing the workshop at its Eastern time (3 PM New York = our 2 PM
        Central), with the Zoom link."""
        import test_events_feeds as F
        ctx = lv_ctx(cfg=LV_YAML + 'sources: {ics_feeds: [{url: "https://example.org/cal.ics", label: "Example"}]}\n',
                     drive=[flyer(NEW_NAME)])
        feed_text = F.ics(
            "BEGIN:VEVENT\r\nDTSTART;TZID=America/New_York:20261022T150000\r\nDTEND;TZID=America/New_York:20261022T160000\r\n"
            "UID:taller-2026-10@example.org\r\nSUMMARY:Taller Mensual de La Viña\r\nURL:https://example.org/taller\r\n"
            f"LOCATION:{ZOOM}\r\nEND:VEVENT\r\n",
            # the same room the same day, 4 hours later: another meeting
            "BEGIN:VEVENT\r\nDTSTART;TZID=America/Chicago:20261022T180000\r\nDTEND;TZID=America/Chicago:20261022T190000\r\n"
            "UID:other-2026-10@example.org\r\nSUMMARY:Reunión de servicio\r\nURL:https://example.org/otra\r\n"
            f"LOCATION:{ZOOM}\r\nEND:VEVENT\r\n")
        items = B._parse_ics(ctx, {"_ics": feed_text, "_spec": B.feed_specs(ctx)[0]})
        ctx.feeds = [{"key": "example", "label": "Example"}]
        with mock.patch.object(B, "ics_events", lambda c: items):
            evs = B.build_events(ctx)
        self.assertEqual([e["title"] for e in evs if e["source"] == "calendar"], ["Reunión de servicio"])
        ours = next(e for e in evs if e["id"] == LV_ID + "2026-10-22")
        self.assertEqual((ours["extra"]["feed_match"], ours["extra"]["also_in_feed"]), ("online", "example"))
        self.assertEqual(ctx.feeds[0]["duplicates"], 1)

    def test_a_date_moved_by_hand_matches_la_vinas_listing(self):
        """The chair's way for a moved date: a content/events file (host: lv, the Zoom link) — and La Viña's own
        listing of that day shows once too (the file wins)."""
        folder = Path(tempfile.mkdtemp(prefix="lv-moved-"))
        self.addCleanup(shutil.rmtree, folder, True)
        (folder / "2026-11-19-lv-monthly-workshop.md").write_text(
            '---\ntitle: "La Viña Monthly Virtual Workshop (in Spanish)"\ntitle_es: "Taller Mensual y Virtual de La Viña"\n'
            "start: 2026-11-19T14:00:00-06:00\nend: 2026-11-19T15:00:00-06:00\n"
            f'online_url: "{ZOOM}"\nmeeting_id: "815 9593 1777"\nhost: "La Viña"\nlang: en\n---\nThe week before Thanksgiving.\n',
            encoding="utf-8")
        manual = A.parse_event(folder / "2026-11-19-lv-monthly-workshop.md", CHI)
        self.assertEqual((manual["extra"]["host"], manual["extra"]["meeting_id"]), ("lv", "815 9593 1777"))
        _ctx, evs = self.build(manual_events=[manual], events_external=[la_vina_listing("2026-11-19")])
        self.assertEqual([e for e in evs if e["category"] == "lv-calendar"], [])
        mine = next(e for e in evs if e["category"] == "manual")
        self.assertEqual((mine["extra"]["also_on_calendar"], mine["extra"]["calendar_match"]), ("lv-calendar", "online"))
        # a host the site does not know — the group that hosts a workshop, written where `host:` goes — is a slip:
        # the event still shows, as ours, and the line is listed (status.json content_events → /status/)
        (folder / "2026-10-26-lv-writing-workshop-tyler.md").write_text(
            "---\ntitle: La Viña Writing Workshop — Tyler\nstart: 2026-10-26T19:00:00-05:00\nhost: Grupo Libro Grande\n"
            "---\nHosted by Grupo Libro Grande.\n", encoding="utf-8")
        items, errors, failed = A.collect(folder, lambda p: A.parse_event(p, CHI), "events")
        tyler = next(i for i in items if i["id"] == "ev:manual:2026-10-26-lv-writing-workshop-tyler")
        self.assertNotIn("host", tyler["extra"])
        self.assertNotIn("host_problem", tyler["extra"])            # (reported by collect, not kept in the data)
        self.assertEqual(failed, set())
        self.assertEqual(errors, [f"{folder.name}/2026-10-26-lv-writing-workshop-tyler.md: "
                                  "host: “Grupo Libro Grande” must be neta (our committee), lv (La Viña) or gv (Grapevine) "
                                  "— shown as ours (NETA 65); the group that hosts it goes in the description"])

    def test_online_rooms(self):
        r = B.online_room
        for url in (ZOOM, "https://us06web.zoom.us/j/81595931777?pwd=abc123#success", "https://zoom.us/j/81595931777",
                    "http://us02web.zoom.us/w/81595931777?tk=x", "https://zoom.us/wc/join/81595931777",
                    "https://us06web.zoom.us/j/81595931777/"):
            self.assertEqual(r(url), "zoom:81595931777", url)
        self.assertEqual(r("https://zoom.us/my/Grapevine.Weekly"), "zoom:my/grapevine.weekly")
        self.assertEqual(r("https://meet.google.com/abc-defg-hij?authuser=0"), "meet:abc-defg-hij")
        self.assertEqual(r("https://teams.microsoft.com/l/meetup-join/19%3ameeting_X/0?context=y"),
                         "teams.microsoft.com/l/meetup-join/19:meeting_x/0")
        for v in (None, "", "Zoom", "https://zoom.us", "https://www.aalavina.org/", "zoom.us/j/81595931777"):
            self.assertIsNone(r(v), v)
        self.assertEqual(B.event_rooms({"extra": {"meeting_id": "815 9593 1777"}}), {"zoom:81595931777"})
        self.assertEqual(B.event_rooms({"extra": {"online_url": "https://meet.google.com/abc-defg-hij",
                                                  "meeting_id": "815 9593 1777"}}), {"meet:abc-defg-hij"})


class LaVinaWorkshopEmail(unittest.TestCase):
    def test_a_date_that_took_place_in_the_monthly_email(self):
        from scripts.notify import send_digest as D
        with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()), \
                mock.patch.object(B, "ics_events", lambda c: []):
            events = B.build_events(lv_ctx(drive=[flyer(NEW_NAME)]))
        sep = next(e for e in events if e["id"] == LV_ID + "2026-09-24")
        for lang, where, when in (("en", "Online", "Thu, Sep 24"), ("es", "En línea", "jue, 24 de sept")):
            row = D.event_row(sep, lang, D.Links("https://example.org"))
            # its day (no time), "Online", and its flyer — its card on /events/ is gone once it is over
            self.assertEqual((row["when"], row["where"], row["url"]),
                             (when, where, f"https://drive.google.com/file/d/{FLYER_ID}/view"), lang)
        booth = next(e for e in events if e["id"] == "ev:recurring:citywide-dallas:2026-09-12")
        self.assertEqual(D.event_row(booth, "en", D.Links("https://example.org"))["url"], "https://citywidedallasaa.org")


# The pages: /events/ (normalizeEvents), the calendar files (buildIcs), the home page (homeEventInfo), the monthly
# toolkit (monthModel, monthMessage), the digest (buildMonthlyDigest, eventWhere), the colours (eventTone) and the
# search (searchIndexJson) — with the events build_data makes.
PAGES_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const { eventTone } = await imp("eleventy/filters/event-tone.js");
const M = await imp("eleventy/filters/monthly.js");
const CO = await imp("eleventy/filters/community.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const now = new Date(input.now);
const items = input.items;
const db = { events: { items }, articles: { items: [], issues: [] } };
const pick = (e) => e && ({ group: e.group, host: e.host, tone: eventTone(e), location: e.location, isOnline: e.isOnline,
  platform: e.platform, online: e.online, meetingId: e.meetingId, contact: e.contact, flyer: e.flyer && e.flyer.view, link: e.link,
  calLocation: e.calLocation, calDescription: e.calDescription, title: e.title, recurrenceDay: e.recurrenceDay,
  recurrence: e.recurrence, past: e.past, detailsUrl: e.detailsUrl, icsUrl: e.icsData.url, icsDescription: e.icsData.description,
  gcal: e.gcal, outlook: e.outlook });
const res = {};
// the home row (homeEvents reads the clock: the build's "now" here) — with our one-off workshops of October
const realNow = Date.now;
Date.now = () => now.getTime();
res.homeRow = filters.homeEvents([...items, ...input.oneOff], null, 4).map((e) => e.id);
res.homeRowFew = filters.homeEvents([...items, input.oneOff[0]], null, 4).map((e) => e.id);
Date.now = realNow;
for (const lang of ["en", "es"]) {
  const evs = C.normalizeEvents(items, input.site, lang, { now });
  const lv = evs.find((e) => e.id === input.lv);
  const mm = M.monthModel("2026-10", db, {}, input.site, lang, now);
  const mmEs = M.monthModel("2026-10", db, {}, input.site, lang === "en" ? "es" : "en", now);
  const both = { [lang]: mm, [lang === "en" ? "es" : "en"]: mmEs };
  const nw = { en: M.monthNow(db, input.site, "en", now), es: M.monthNow(db, input.site, "es", now) };
  const iss = { en: [], es: [] };
  const md = CO.buildMonthlyDigest(db, { site: input.site, now, month: "2026-09" });
  const held = md.events.find((e) => e.id === input.sep);
  const idx = JSON.parse(filters.searchIndexJson({ events: { items: input.live } }, [], lang, input.site)).items;
  // the dates that took place in September (both kept 90 days in the calendar files): La Viña's, which has no page
  // of its own (its card on /events/ is gone once it is over), and the booth's, which has one
  const lvHeld = evs.find((e) => e.id === input.sep), boothHeld = evs.find((e) => e.id === input.boothSep);
  // a date whose rule cannot be read (an older events.json): the data's recurrence_label
  const noRule = C.normalizeEvents(items.filter((i) => i.id === input.lv).map((i) => ({ ...i, extra: { ...i.extra, rule: null } })),
                                   input.site, lang, { now }).find((e) => e.id === input.lv);
  const icsOpts = { lang, now, name: "x", categoryLabel: (ev) => t(`committee.events.group.${ev.group}`, lang) };
  res[lang] = {
    lv: pick(lv), booth: pick(evs.find((e) => e.id === input.booth)),
    held: pick(lvHeld), boothHeld: pick(boothHeld), noRule: noRule.recurrence,
    ics: C.buildIcs([lv], icsOpts),
    icsHeld: C.buildIcs([lvHeld, boothHeld, lv], icsOpts),
    home: filters.homeEventInfo(items.find((i) => i.id === input.lv), lang),
    homeBooth: filters.homeEventInfo(items.find((i) => i.id === input.booth), lang),
    row: mm.dates.find((d) => d.id === input.lv), rowTone: eventTone(mm.dates.find((d) => d.id === input.lv)),
    novIds: M.monthModel("2026-11", db, {}, input.site, lang, now).dates.map((d) => d.id),
    msg: M.monthMessage({ mm: both, nw, iss }, [lang], "whatsapp", input.site, t),
    digest: held && { url: held.url, where: CO.eventWhere(held, lang, t) },
    search: idx.filter((e) => String(e.id).startsWith(input.lvPrefix)),
    boothSearch: idx.filter((e) => String(e.id).startsWith("ev:recurring:citywide-dallas:")),
  };
  // /events/ as the page lists it: November's date from La Viña's own listing, and the series' "Then …" line
  const listed = filters.cmCollapseRecurring(C.normalizeEvents(items, input.site, lang, { now }));
  const moved = listed.find((e) => e.seriesOf);
  res[lang].then = (listed.find((e) => e.id === input.lv) || {}).moreDates;
  res[lang].moved = moved && { ...pick(moved), seriesOf: moved.seriesOf, ownWords: moved.ownWords,
    timeLabel: moved.timeLabel, later: !!moved.later, summary: moved.summary };
}
out(res);
"""


class LaVinaWorkshopOnPages(unittest.TestCase):
    """Every page that lists a recurring event, for an online-only event La Viña holds: no place and no map pin,
    "Online on Zoom" with a "Join online" button, its meeting ID, La Viña's colour and group — the booth unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.res = None

    def result(self) -> dict:
        if LaVinaWorkshopOnPages.res is None:
            with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()), \
                    mock.patch.object(B, "ics_events", lambda c: []):
                # La Viña's own calendar lists November's date (Nov 19: the 4th Thursday is Thanksgiving, skipped)
                items = B.build_events(lv_ctx(drive=[flyer(NEW_NAME)], events_external=[la_vina_listing("2026-11-19")]))
                # the search lists only what is still to come by the real clock: dates worked out from today
                live = B.build_events(lv_ctx(now=datetime.now(timezone.utc).replace(microsecond=0), drive=[flyer(NEW_NAME)]))
            for e in items + live:
                e.pop("_fixed_i18n", None)
            site = {"url": "https://example.org/site", "meeting": {"week_of_month": 3, "weekday": "wednesday",
                                                                    "start": "19:00", "end": "20:00", "platform": "Zoom"},
                    "recurring_events": yaml.safe_load(LV_YAML)["recurring_events"], "links": {}}
            if str(Path(__file__).resolve().parent) not in sys.path:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
            from nodejs import run_js
            # three of our own one-off workshops in October (Oct 3, 7 and 17: the last one comes before the workshop)
            one_off = [{"id": f"ev:manual:{day}-workshop", "source": "committee", "kind": "event", "category": "manual",
                        "status": "ok", "title": f"Workshop {day}", "lang": "en", "date": f"{day}T19:00:00Z",
                        "extra": {"start": f"{day}T19:00:00Z", "end": f"{day}T21:00:00Z", "all_day": False}}
                       for day in ("2026-10-03", "2026-10-07", "2026-10-17")]
            LaVinaWorkshopOnPages.res = run_js(self, PAGES_JS, data={
                "items": items, "live": live, "site": site, "now": "2026-10-01T21:00:00Z", "lv": LV_ID + "2026-10-22",
                "sep": LV_ID + "2026-09-24", "booth": "ev:recurring:citywide-dallas:2026-10-10",
                "boothSep": "ev:recurring:citywide-dallas:2026-09-12", "lvPrefix": LV_ID, "oneOff": one_off})
        return LaVinaWorkshopOnPages.res

    def test_events_page_card(self):
        for lang, online in (("en", "Online on Zoom"), ("es", "En línea por Zoom")):
            lv = self.result()[lang]["lv"]
            self.assertEqual((lv["group"], lv["host"], lv["tone"]), ("calendar", "lv", "lv"), lang)
            self.assertEqual((lv["location"], lv["isOnline"], lv["platform"], lv["online"], lv["meetingId"]),
                             ("", True, "Zoom", ZOOM, "815 9593 1777"), lang)
            self.assertEqual((lv["flyer"], lv["link"]), (f"https://drive.google.com/file/d/{FLYER_ID}/view", ""), lang)
            self.assertEqual(lv["calLocation"], ZOOM)
            self.assertIn(f"{online}: {ZOOM}", lv["calDescription"])
            self.assertIn({"en": "Meeting ID: 815 9593 1777", "es": "ID de reunión: 815 9593 1777"}[lang], lv["calDescription"])
            # the e-mail to write to: its own line on the card (ev.contact) and in the calendar entry
            self.assertEqual(lv["contact"], "lveditorial@aagrapevine.org")
            self.assertIn({"en": "Contact: ", "es": "Contacto: "}[lang] + "lveditorial@aagrapevine.org", lv["calDescription"])
            self.assertEqual(lv["recurrenceDay"], {"en": "Every fourth Thursday of the month",
                                                   "es": "Cada cuarto jueves del mes"}[lang])
            booth = self.result()[lang]["booth"]
            self.assertEqual((booth["group"], booth["host"], booth["tone"], booth["isOnline"], booth["meetingId"],
                              booth["contact"]), ("neta", "", "booth", False, "", ""), lang)

    def test_a_moved_date_from_la_vinas_calendar(self):
        """November's date comes from La Viña's own listing (the rule skips Thanksgiving): its own card in the
        GV & LV group, with the series' title and summary (the committee's words: no language pill), Zoom ID and
        flyer — "Time not listed", as La Viña gives none — and named in the series' "Then …" line, so October's
        card never reads as if November had no workshop."""
        for lang, then, title, when in (
                ("en", ["Nov 19", "Jan 28", "Feb 25"], "La Viña Monthly Virtual Workshop (in Spanish)",
                 "Time not listed — see event details"),
                ("es", ["19 nov", "28 ene", "25 feb"], "Taller Mensual y Virtual de La Viña",
                 "Hora no indicada — ver detalles del evento")):
            r = self.result()[lang]
            self.assertEqual(r["then"], then, lang)
            moved = r["moved"]
            self.assertEqual((moved["title"], moved["timeLabel"], moved["seriesOf"], moved["later"]),
                             (title, when, "lv-monthly-workshop", False), lang)
            self.assertEqual((moved["group"], moved["tone"], moved["isOnline"], moved["meetingId"], moved["contact"],
                              moved["flyer"]), ("calendar", "lv", True, "815 9593 1777", "lveditorial@aagrapevine.org",
                                                f"https://drive.google.com/file/d/{FLYER_ID}/view"), lang)
            self.assertEqual(moved["link"], "https://www.aalavina.org/get-involved/events/2026-11-19/taller-mensual")
            self.assertEqual(moved["ownWords"], lang == "es")        # (English is its own language: no pill either)

    def test_calendar_file(self):
        for lang, category in (("en", "Grapevine / La Viña calendar"), ("es", "Calendario de Grapevine / La Viña")):
            ics = self.result()[lang]["ics"].replace("\r\n ", "")
            self.assertIn("DTSTART:20261022T190000Z\r\nDTEND:20261022T200000Z", ics)
            self.assertIn(f"LOCATION:{ZOOM}", ics)
            self.assertIn(f"ATTACH:https://drive.google.com/file/d/{FLYER_ID}/view", ics)
            self.assertIn(f"CATEGORIES:{category}", ics)
            self.assertIn("URL:https://example.org/site" + ("/es" if lang == "es" else "") + "/events/#ev-recurring-lv-monthly-workshop-2026-10-22", ics)

    def test_a_date_that_took_place_links_to_the_page(self):
        """/events/ lists only the dates of a series still to come (its "Past events" leave the series out), so the
        calendar entry of a date that has passed — the calendar files keep it 90 days — links to /events/ itself,
        never to the #… of a card that is gone: its URL, the "Details:" line, the Google / Outlook links and the
        card's ".ics file". A date still to come keeps its card's #anchor; the booth, which has a page of its own,
        links there, past or not."""
        from icalendar import Calendar
        for lang in ("en", "es"):
            page = "https://example.org/site" + ("/es" if lang == "es" else "") + "/events/"
            r = self.result()[lang]
            held, nxt, booth = r["held"], r["lv"], r["boothHeld"]
            self.assertEqual((held["past"], held["detailsUrl"], held["icsUrl"]), (True, page, page), lang)
            self.assertEqual(held["calDescription"].splitlines()[-1], {"en": "Details: ", "es": "Detalles: "}[lang] + page)
            self.assertNotIn("#ev-", held["calDescription"])
            self.assertEqual(held["icsDescription"], held["calDescription"])
            self.assertEqual(parse_qs(urlparse(held["gcal"]).query)["details"], [held["calDescription"]])
            self.assertEqual(parse_qs(urlparse(held["outlook"]).query)["body"], [held["calDescription"]])
            self.assertEqual((nxt["past"], nxt["detailsUrl"]), (False, page + "#ev-recurring-lv-monthly-workshop-2026-10-22"))
            self.assertEqual((booth["past"], booth["detailsUrl"], booth["icsUrl"]),
                             (True, "https://citywidedallasaa.org", "https://citywidedallasaa.org"), lang)
            # the calendar file, read back
            uid = "-es@neta65-gvlv" if lang == "es" else "@neta65-gvlv"
            urls = {str(e["UID"]).replace(uid, ""): str(e["URL"]) for e in Calendar.from_ical(r["icsHeld"]).walk("VEVENT")}
            self.assertEqual(urls, {"ev-recurring-lv-monthly-workshop-2026-09-24": page,
                                    "ev-recurring-citywide-dallas-2026-09-12": "https://citywidedallasaa.org",
                                    "ev-recurring-lv-monthly-workshop-2026-10-22": page + "#ev-recurring-lv-monthly-workshop-2026-10-22"})

    def test_the_repeat_line_names_its_time_zone(self):
        """The calendars' description repeats the rule with its time, next to the date's own start and end — which a
        calendar shows in its reader's zone (DTSTART is an instant): the line names Central time, in the words of the
        district report and the QR poster (report.c_time), so a reader in New York never finds "2:00 PM" beside a
        workshop their calendar puts at 3:00 PM. Written from the rule or — an older events.json — from the data's
        recurrence_label: the same line. The card shows its day part only (the card's time says "CDT"); the
        search's line is the repeat line · where — the next date is in the result's meta line (`d`); repeated in the
        line, it cut the time zone mid-word on a phone. (The place can still be cut on a 360–390px phone: the whole
        line fits in two lines from about 412px.) That date is still searched, with the keywords (`x`, never
        shown): "october" or "oct 22" finds the series as it finds a one-off event by the date in its line."""
        from icalendar import Calendar
        lines = {"en": "Every fourth Thursday of the month · 2:00 – 3:00 PM Central time",
                 "es": "Cada cuarto jueves del mes · 2:00–3:00 p. m., hora del Centro"}
        zone = json.loads((ROOT / "src" / "_i18n" / "report.json").read_text(encoding="utf-8"))["report.c_time"]

        def written(ymd: str, lang: str) -> str:
            """A date as the pages write it ("October 22, 2026" / "22 de octubre de 2026"). The search's dates are
            worked out from today (see result()), so the words expected come from the hit's own `d`."""
            y, m, d = map(int, ymd.split("-"))
            return {"en": f"{B.MONTHS_EN[m - 1]} {d}, {y}", "es": f"{d} de {B.MONTHS_ES[m - 1].lower()} de {y}"}[lang]

        def spaces(s: str) -> str:            # the clock's thin and no-break spaces, as plain ones
            return re.sub("[\u2009\u202f\u00a0]", " ", s)

        for lang, line in lines.items():
            r = self.result()[lang]
            self.assertTrue(line.endswith(zone[lang].replace("{time}", "")), lang)
            self.assertEqual((spaces(r["lv"]["recurrence"]), spaces(r["noRule"])), (line, line), lang)
            self.assertIn(line, spaces(r["lv"]["calDescription"]).splitlines(), lang)
            desc = str(next(iter(Calendar.from_ical(r["ics"]).walk("VEVENT")))["DESCRIPTION"])
            self.assertIn(line, spaces(desc).splitlines(), lang)
            self.assertEqual(r["lv"]["recurrenceDay"], line.split(" · ")[0])
            hit = r["search"][0]
            self.assertEqual(spaces(hit["s"]), line + " · " + {"en": "Online on Zoom", "es": "En línea por Zoom"}[lang])
            self.assertRegex(hit["d"], r"^\d{4}-\d{2}-\d{2}$")
            # the next date, out of the line shown (above): in the meta line (`d`) and searched with the keywords
            self.assertIn(written(hit["d"], lang), hit["x"], lang)
            booth = r["boothSearch"][0]
            self.assertTrue(spaces(booth["s"]).startswith({"en": "Every second Saturday of the month · 5:00 – 8:00 PM Central time · ",
                                                           "es": "Cada segundo sábado del mes · 5:00–8:00 p. m., hora del Centro · "}[lang]))
            self.assertIn("9200 Inwood Road", booth["s"])
            self.assertIn(written(booth["d"], lang), booth["x"], lang)

    def test_home_page(self):
        for lang, online in (("en", "Online on Zoom"), ("es", "En línea por Zoom")):
            home = self.result()[lang]["home"]
            self.assertEqual((home["location"], home["online"], home["tba"]), ("", online, False), lang)
            self.assertEqual(self.result()[lang]["homeBooth"]["online"], "")        # a place: no "online" line

    def test_home_row(self):
        """Our own series (the booth) keeps a place in the home row of 4; La Viña's series keeps none — its next
        date takes its turn by date, so our Oct 17 workshop, which comes sooner, is never pushed off."""
        r = self.result()
        self.assertEqual(r["homeRow"], ["ev:manual:2026-10-03-workshop", "ev:manual:2026-10-07-workshop",
                                        "ev:recurring:citywide-dallas:2026-10-10", "ev:manual:2026-10-17-workshop"])
        # with room to spare it shows (its next date only), before a second committee meeting fills the row
        self.assertEqual([i for i in r["homeRowFew"] if i.startswith(LV_ID)], [LV_ID + "2026-10-22"])
        self.assertEqual(r["homeRowFew"][:2], ["ev:manual:2026-10-03-workshop", "ev:recurring:citywide-dallas:2026-10-10"])

    def test_monthly_toolkit(self):
        for lang, word in (("en", "Online"), ("es", "En línea")):
            r = self.result()[lang]
            row = r["row"]
            self.assertEqual((row["kind"], row["host"], row["online"], row["place"], r["rowTone"]),
                             ("recurring", "lv", True, "", "lv"), lang)
            line = next(x for x in r["msg"].splitlines() if "Viña" in x and ("Workshop" in x or "Taller" in x))
            self.assertTrue(line.endswith(f" — {word}"), line)
            # November's 4th Thursday is Thanksgiving: in skip_dates, so no date on November's page
            self.assertFalse([i for i in r["novIds"] if i.startswith(LV_ID)], lang)

    def test_digest_and_search(self):
        for lang, word, online in (("en", "Online", "Online on Zoom"), ("es", "En línea", "En línea por Zoom")):
            r = self.result()[lang]
            self.assertEqual(r["digest"], {"url": f"https://drive.google.com/file/d/{FLYER_ID}/view", "where": word}, lang)
            self.assertEqual(len(r["search"]), 1, lang)                  # the series once: its next date
            hit = r["search"][0]
            self.assertEqual(hit["src"], "lv")
            self.assertIn(online, hit["s"])
            # "booth" / "literature table" find the booth, as before — not La Viña's workshop (no booth)
            self.assertIn("every month monthly", hit["x"])
            self.assertNotIn("booth", hit["x"])
            booth = r["boothSearch"]
            self.assertEqual([b["src"] for b in booth], ["neta"], lang)
            for words in ("every month monthly", "cada mes mensual", "booth literature table", "mesa de literatura"):
                self.assertIn(words, booth[0]["x"], lang)


# --------------------------------------------------------------------------- the web pages' reading
class PagesReadTheSettingsLikeTheSync(unittest.TestCase):
    """src/_data/meeting.js, committee.js and monthly.js read `meeting:` / `recurring_events:` through
    eleventy.config.js monthlyRule — the same reading as meeting.meeting_rule and build_data.recurring_specs,
    so a value the daily sync accepts ("7:00 PM", "5pm", "sábado", "2nd", a key with spaces, no end, one skip
    date without brackets) never stops the build or moves a date on the pages."""

    TIMES = ["19:00", "7:00 PM", "7 p.m.", "7pm", "19h00", "19.30", 19.5, 19, 1140, 68400, "5 PM", "8:00", "23:30",
             "evening", "", None, "24:00", "12 pm", "0 am", -5, True]
    DAYS = ["saturday", "Saturdays", "Sábados", "sabado", "jueves", " Friday ", "Wednesdays", "Sat.", "funday",
            "constructor", None, 5]
    WEEKS = [2, "2", "2nd", "second", "segundo", "2.º", "last", "último", -1, "third", " 3 ", "+3", 7, 0, 2.5, "x", None]
    KEYS = ["citywide-dallas", "CityWide Dallas", "CityWide-Dallas", "Second Friday Workshop!", "!!!", "   ",
            "Ñandú café", "a" * 31 + "-b", 0]

    def test_same_rule_as_the_sync(self):
        if str(Path(__file__).resolve().parent) not in sys.path:     # run as tests.test_recurring_events
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        from nodejs import run_js
        base = {"key": "citywide-dallas", "title": "Booth", "week_of_month": 2, "weekday": "saturday",
                "start": "17:00", "end": "20:00"}
        rec = ([dict(base, start=t) for t in self.TIMES] + [dict(base, end=t) for t in self.TIMES]
               + [dict(base, weekday=d) for d in self.DAYS] + [dict(base, week_of_month=w) for w in self.WEEKS]
               + [dict(base, key=k) for k in self.KEYS] + [{k: v for k, v in base.items() if k != "end"}]
               + [dict(base, skip_dates=s) for s in ("2026-10-10", ["2026-11-14", "2026-11-15", "junk"], None, "")])
        meet = ([{}] + [{"start": t} for t in self.TIMES] + [{"start": "19:00", "end": t} for t in self.TIMES]
                + [{"start": "20:30", "end": "20:00"}, {"weekday": "sábado", "week_of_month": "third"}]
                + [{"weekday": d} for d in self.DAYS] + [{"week_of_month": w} for w in self.WEEKS]
                + [{"skip_dates": s} for s in ("2026-12-16", ["2026-12-16", "2026-12-17", "junk"], None)])
        got = run_js(self, 'const { monthlyRule } = await imp("eleventy.config.js");'
                           'out({ rec: input.rec.map((e) => monthlyRule(e, true)), meet: input.meet.map((e) => monthlyRule(e)),'
                           '      again: input.rec.map((e) => monthlyRule(monthlyRule(e, true), true)) });',
                     data={"rec": rec, "meet": meet})
        checked = 0
        for e, j, j2 in zip(rec, got["rec"], got["again"]):
            specs, _ = B.recurring_specs(ctx_with({"recurring_events": [e]}))
            if not specs:
                continue                 # skipped by the sync: no dates in events.json, so /monthly/ has none to project
            sp = specs[0]
            # the rule in events.json's shape (extra.rule: the end as used) and the key its dates carry (extra.series)
            self.assertEqual({k: j.get(k) for k in ("week_of_month", "weekday", "start", "end", "key")},
                             dict(B.rule_fields(sp["rule"]), key=sp["key"]), e)
            self.assertLessEqual(set(sp["rule"].skip), set(j.get("skip_dates") or []), e)
            self.assertEqual(j2, j, e)                                  # read twice: the same
            checked += 1
        self.assertGreater(checked, 40)
        days = [d.lower() for d in M.DAY_NAMES_EN]
        for e, j in zip(meet, got["meet"]):
            r = M.meeting_rule(e)
            (sh, sm), (eh, em) = r.span()
            # what the pages fall back on when a value is left out: the 3rd Wednesday, 19:00–20:00
            self.assertEqual((j.get("weekday", "wednesday"), j.get("week_of_month", 3), j.get("start", "19:00"), j.get("end", "20:00")),
                             (days[r.weekday], r.week_of_month, f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}"), e)
            self.assertLessEqual(set(r.skip), set(j.get("skip_dates") or []), e)
        self.assertEqual(got["meet"][0], {})                            # no settings: none made up (the digest's "no rule")


if __name__ == "__main__":
    unittest.main()
