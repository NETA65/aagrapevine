"""Round 24 — the committee meeting's dates: the sync writes a record for every date the pages list.

The pages work out the committee meeting's dates themselves (eleventy/filters/committee.js normalizeEvents →
meetingDates: this month in Central time and the MEETING_MONTHS_AHEAD after it — /events/, /events.ics, the event
share pages, the month pages' calendar files) and take each date's flyer from its events.json record, which the sync
writes (scripts/sync/build_data.py committee_meetings → meeting.window_meetings). The sync used to write the next 12
dates: before a month's meeting the pages list 13 (Nov 18, 2026 … Nov 17, 2027 on Nov 11, 2026), so the 13th showed
without the flyer the Drive had for it ("November 2027 Committee Meeting - guest speaker"). Here:

  * one number on both sides (MEETING_MONTHS_AHEAD), and no month page beyond it;
  * the same dates on both sides, on any day — before, during and after a month's meeting, on the last evening of a
    year (already January in UTC), with a skipped date, a "5th Wednesday" rule, a first date (`starts:`) — and none
    of the sync's records outside the pages' window (normalizeEvents would list it as one more date);
  * the last date the pages list has its month's flyer — on /events/ (both languages), in /events.ics and in the
    month's calendar file (/monthly/2027-11/) — and every date before it its own.

The settings and the Drive's file names are round 20's (tests/test_r20_meeting.py), with fixed clocks.

    python -m unittest tests.test_r24_meeting_window -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py, test_r20_meeting.py

from nodejs import run_js  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402
from test_r20_meeting import YAML, NoTranslator, Untranslated, ctx_with, drive_items  # noqa: E402  (round 20's)

TODAY = "2026-11-11T18:00:00Z"            # Wed Nov 11, 2026 (noon CST): a week before November's meeting
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")

# The pages' committee meetings still to come, as /events/ lists them (normalizeEvents' own window: no monthsAhead),
# from the settings alone and from the sync's records — and, with the records, each date's flyer (/events/ in both
# languages), the flyer /events.ics attaches to it, and the one the month's calendar file attaches (monthIcs).
PAGES_JS = r"""
const yaml = await import("js-yaml");
const C = await imp("eleventy/filters/committee.js");
const M = await imp("eleventy/filters/monthly.js");
const cfg = yaml.load(input.yaml);
const site = { ...cfg.site, meeting: cfg.meeting, recurring_events: cfg.recurring_events };
const res = { ahead: C.MEETING_MONTHS_AHEAD, monthPages: M.windowKeys(new Date(input.now)).length, runs: [] };
const upcoming = (evs) => evs.filter((e) => e.committee && !e.past);
for (const now of input.clocks) {
  const at = new Date(now);
  res.runs.push({
    now,
    rule: upcoming(C.normalizeEvents([], site, "en", { now: at })).map((e) => e.startYmd),
    synced: upcoming(C.normalizeEvents(input.synced[now] || [], site, "en", { now: at })).map((e) => e.startYmd),
  });
}
if (input.items) {
  const at = new Date(input.now);
  res.flyers = {};
  for (const lang of ["en", "es"]) {
    res.flyers[lang] = upcoming(C.normalizeEvents(input.items, site, lang, { now: at })).map((e) => [e.startYmd, e.flyer ? e.flyer.view : null]);
  }
  // /events.ics as src/pages/events-ics.11ty.js writes it
  res.ics = C.buildIcs(C.normalizeEvents(input.items, site, "en", { monthsBack: 3, monthsAhead: C.MEETING_MONTHS_AHEAD, now: at }), { lang: "en", now: at, name: "x" });
  // the month's calendar file beside /monthly/2027-11/ (and /es/monthly/2027-11/)
  const db = { events: { items: input.items } };
  res.month = {};
  for (const lang of ["en", "es"]) res.month[lang] = M.monthIcs(M.monthModel("2027-11", db, {}, site, lang, at), db, site, lang, at);
}
out(res);
"""


def unfold(ics: str) -> list[str]:
    out: list[str] = []
    for line in ics.split("\r\n"):
        if line.startswith(" ") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def attached(ics: str) -> dict[str, str | None]:
    """Each event's UID → the flyer it attaches (ATTACH), None without one."""
    evs: dict[str, str | None] = {}
    uid = None
    for line in unfold(ics):
        if line == "BEGIN:VEVENT":
            uid = ""
        elif line == "END:VEVENT":
            uid = None
        elif uid is not None and line.startswith("UID:"):
            uid = line[4:]
            evs[uid] = None
        elif uid and line.startswith("ATTACH:"):
            evs[uid] = line[7:]
    return evs


def settings(**meeting) -> dict:
    cfg = yaml.safe_load(YAML)
    cfg["meeting"].update(meeting)
    return cfg


class OneWindow(Untranslated):
    """The sync's committee meetings are the pages' ones, on any day: the same months (one number on both sides)."""

    # (the meeting is 7–8 PM Central: 01:00–02:00 UTC the next day in November)
    CLOCKS = {
        TODAY: 13,                          # before November's meeting: Nov 18, 2026 … Nov 17, 2027
        "2026-11-19T01:30:00Z": 13,         # during it (7:30 PM CST): still listed
        "2026-11-19T03:30:00Z": 12,         # after it (9:30 PM CST): Dec 16, 2026 … Nov 17, 2027
        "2027-01-01T03:00:00Z": 12,         # Dec 31, 9 PM CST — January in UTC, still December here: Jan … Dec 2027
        "2027-03-01T18:00:00Z": 13,
    }

    def compare(self, cfg: dict, clocks) -> dict:
        synced, ids = {}, {}
        for now in clocks:
            at = datetime.fromisoformat(now.replace("Z", "+00:00"))
            ms = B.committee_meetings(ctx_with(cfg, now=at))
            synced[now] = ms
            ids[now] = [m["id"].removeprefix("ev:committee:") for m in ms]
        got = run_js(self, PAGES_JS, data={"yaml": yaml.safe_dump(cfg, allow_unicode=True), "clocks": list(clocks),
                                           "synced": synced, "now": TODAY}, now=TODAY)
        for run in got["runs"]:
            with self.subTest(now=run["now"]):
                self.assertEqual(ids[run["now"]], run["rule"])        # the same dates…
                self.assertEqual(run["synced"], run["rule"])          # …and no record the pages would add to them
        return {"js": got, "ids": ids}

    def test_one_number(self):
        got = run_js(self, PAGES_JS, data={"yaml": YAML, "clocks": [], "synced": {}, "now": TODAY}, now=TODAY)
        self.assertEqual(got["ahead"], M.MEETING_MONTHS_AHEAD)
        self.assertEqual(M.MEETING_MONTHS_AHEAD, 12)
        # the month pages (this month and the 12 after it) never go past the months the sync writes
        self.assertLessEqual(got["monthPages"], M.MEETING_MONTHS_AHEAD + 1)
        # the sync's default is that number (build_data.committee_meetings, meeting.window_meetings)
        self.assertEqual(B.committee_meetings.__defaults__, (M.MEETING_MONTHS_AHEAD,))
        self.assertEqual(M.window_meetings.__defaults__[-1], M.MEETING_MONTHS_AHEAD)

    def test_the_same_dates_on_any_day(self):
        r = self.compare(settings(), self.CLOCKS)
        for now, n in self.CLOCKS.items():
            self.assertEqual(len(r["ids"][now]), n, now)
        self.assertEqual((r["ids"][TODAY][0], r["ids"][TODAY][-1]), ("2026-11-18", "2027-11-17"))
        self.assertEqual(r["ids"]["2027-01-01T03:00:00Z"][-1], "2027-12-15")

    def test_skipped_dates_a_fifth_week_and_a_first_date(self):
        self.compare(settings(skip_dates=["2027-03-17", "2027-11-17"]), [TODAY, "2027-03-01T18:00:00Z"])
        self.compare(settings(week_of_month=5), [TODAY])                   # only the months with a 5th Wednesday
        self.compare(settings(week_of_month=-1, weekday="friday"), [TODAY])
        self.compare(settings(starts="2027-02-17"), [TODAY])

    def test_a_count_of_dates_would_miss_the_last_one(self):
        """What went wrong: the next 12 dates end a month early whenever this month's meeting is still to come."""
        rule = [d["ymd"] for d in M.upcoming_meetings(12, now=datetime(2026, 11, 11, 18, tzinfo=timezone.utc),
                                                      cfg=settings())]
        window = [d["ymd"] for d in M.window_meetings(now=datetime(2026, 11, 11, 18, tzinfo=timezone.utc),
                                                      cfg=settings())]
        self.assertEqual(rule[-1], "2027-10-20")
        self.assertEqual(window, rule + ["2027-11-17"])


class TheLastDateHasItsFlyer(Untranslated):
    """On Nov 11, 2026 the pages list the committee meeting up to Nov 17, 2027: that date has its month's flyer from
    the Drive, on /events/ (both languages), in /events.ics and in the month's calendar file, as every date before it
    has its own (Nov 18 and Dec 16, 2026: the undated "Committee Meeting - flyer"; each month of 2027 its own)."""

    @classmethod
    def setUpClass(cls):
        cls.drive = drive_items()
        cls.view = {i["extra"]["name"]: i["extra"]["view_url"] for i in cls.drive}
        with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()):
            ctx = ctx_with(now=datetime(2026, 11, 11, 18, tzinfo=timezone.utc), drive=cls.drive)
            with mock.patch.object(B, "ics_events", lambda c: []):
                cls.items = B.build_events(ctx)
        cls.problems = dict(ctx.raw_problems)

    def want(self, ymd: str) -> str:
        if ymd < "2027-01-01":
            return self.view["Committee Meeting - flyer.png"]
        return self.view[f"{MONTHS[int(ymd[5:7]) - 1]} {ymd[:4]} Committee Meeting - guest speaker.png"]

    def test_the_sync_writes_it(self):
        cm = {e["id"]: e for e in self.items if e.get("category") == "committee"}
        self.assertEqual(len(cm), 13)
        last = cm["ev:committee:2027-11-17"]["extra"]
        self.assertEqual(last["flyer_url"], self.view["November 2027 Committee Meeting - guest speaker.png"])
        self.assertTrue(last["flyer_thumb"])
        # never a second event of the flyer, nor a note for the chair
        self.assertEqual([e["id"] for e in self.items if e.get("category") == "flyer"], [])
        self.assertNotIn("meeting", self.problems)

    def test_the_pages_show_it(self):
        got = run_js(self, PAGES_JS, data={"yaml": YAML, "clocks": [], "synced": {}, "now": TODAY,
                                           "items": json.loads(json.dumps(self.items))}, now=TODAY)
        for lang in ("en", "es"):
            rows = got["flyers"][lang]
            with self.subTest(lang=lang):
                self.assertEqual((len(rows), rows[0][0], rows[-1][0]), (13, "2026-11-18", "2027-11-17"))
                self.assertEqual({ymd: view for ymd, view in rows}, {ymd: self.want(ymd) for ymd, _ in rows})
        nov = self.view["November 2027 Committee Meeting - guest speaker.png"]
        # /events.ics: the same flyer on the same date
        ics = attached(got["ics"])
        self.assertEqual(ics["ev-committee-2027-11-17@neta65-gvlv"], nov)
        self.assertEqual(ics["ev-committee-2026-12-16@neta65-gvlv"], self.view["Committee Meeting - flyer.png"])
        # /monthly/2027-11/'s calendar file (and the Spanish one's)
        self.assertEqual(attached(got["month"]["en"])["ev-committee-2027-11-17@neta65-gvlv"], nov)
        self.assertEqual(attached(got["month"]["es"])["ev-committee-2027-11-17-es@neta65-gvlv"], nov)


if __name__ == "__main__":
    unittest.main()
