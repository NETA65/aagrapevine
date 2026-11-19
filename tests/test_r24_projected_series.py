"""Round 24 — a later month's date of a monthly series keeps how to join it.

The month pages (eleventy/filters/monthly.js monthModel) list a series' dates past the ones data/site/events.json has
(its `months_ahead`) by working them out from its rule, each written from one of the series' records — and the
month's calendar file (/monthly/<month>/, monthIcs) writes it as /events.ics writes a date. events.json lists the
dates to come first, soonest first, then the past ones the calendar files keep (90 days), newest first
(scripts/sync/build_data.py order_events): the series' LAST record is its OLDEST past date, extra.past true. A date
that is over gives no link, no meeting ID or code (committee.js normalizeEvents, round 24), so a later month written
from that record lost them: La Viña's monthly workshop in /monthly/2027-07/ … /monthly/2027-10/ (English and
Spanish) had no "Meeting ID: 815 9593 1777", and the Grapevine Meeting's later months would lose their Google Meet
link once its first date (Dec 2, 2026) is over.

Here, with the sync's own records in its own order (a build on Jan 10, 2027: two or three past dates of each series kept):
  * a later month's date has the link, the meeting ID or code — its calendar text is the series' upcoming dates'
    own, in both languages;
  * it is never marked past, and takes no flyer named with another month ("July 2027 Grapevine Meeting - flyer"
    is July's; August has the series' own flyer);
  * with only past dates left in events.json (a sync that has not run for weeks), a later date still to come keeps
    them too.

The settings are round 20's (tests/test_r20_meeting.py: a made-up Google Meet room) and a made-up Zoom workshop.

    python -m unittest tests.test_r24_projected_series -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py, test_r20_meeting.py, test_monthly.py

from nodejs import run_js  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from test_monthly import vevents  # noqa: E402
from test_r20_meeting import ROOM, YAML, NoTranslator, ctx_with, drive_items  # noqa: E402  (round 20's)

NOW = "2027-01-10T18:00:00Z"              # Sun Jan 10, 2027 (noon CST): Dec 2 and Jan 6 are over
ZOOM = "https://us02web.zoom.us/j/12345678901"
ZOOM_ID = "123 4567 8901"                 # made up
WORKSHOP = f"""
  - key: "zoom-workshop"
    title: "Monthly Virtual Workshop (in Spanish)"
    title_es: "Taller Mensual y Virtual"
    summary: "In Spanish, open to all: books, event news and service updates."
    summary_es: "En español y abierto a todos: libros, noticias de eventos y novedades de servicio."
    host: "lv"
    week_of_month: 4
    weekday: "thursday"
    start: "14:00"
    end: "15:00"
    online_url: "{ZOOM}"
    meeting_id: "{ZOOM_ID}"
    contact: "workshop@example.org"
    months_ahead: 6
    skip_dates: []
"""
SETTINGS = YAML + WORKSHOP
FLYERS = {("flyers", "Grapevine Meeting - flyer.png"): "series",
          ("flyers", "July 2027 Grapevine Meeting - flyer.png"): "series"}

# Each projected month's date of the series (monthModel's recurring rows: the record it is written from) and its
# entry in the month's calendar file; /events.ics's entries of the same series (the dates events.json lists).
JS = r"""
const yaml = await import("js-yaml");
const C = await imp("eleventy/filters/committee.js");
const M = await imp("eleventy/filters/monthly.js");
const cfg = yaml.load(input.yaml);
const site = { ...cfg.site, meeting: cfg.meeting, recurring_events: cfg.recurring_events };
const now = new Date(input.now);
const db = { events: { items: input.items } };
const res = { months: {}, feed: {} };
for (const lang of ["en", "es"]) {
  res.feed[lang] = C.buildIcs(C.normalizeEvents(input.items, site, lang, { monthsBack: 3, monthsAhead: 12, now }), { lang, now, name: "x" });
  for (const key of input.months) {
    const m = M.monthModel(key, db, {}, site, lang, now);
    res.months[`${key}:${lang}`] = {
      rows: m.recurring.map((d) => ({ id: d.id, series: d.series, past: d.past, online: d.online,
        srcPast: d.src.extra.past, flyer: d.src.extra.flyer_url || null })),
      ics: M.monthIcs(m, db, site, lang, now),
    };
  }
}
out(res);
"""


def build(drive=FLYERS) -> list[dict]:
    """events.json's events as the daily sync writes them on Jan 10, 2027 (build_events → order_events)."""
    with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()):
        ctx = ctx_with(SETTINGS, now=datetime.fromisoformat(NOW.replace("Z", "+00:00")), drive=drive_items(drive))
        with mock.patch.object(B, "ics_events", lambda c: []):
            return json.loads(json.dumps(B.build_events(ctx)))


def entries(ics: str) -> dict[str, dict]:
    return {e["UID"]: e for e in vevents(ics)}


def uid(series: str, ymd: str, lang: str) -> str:
    return f"ev-recurring-{series}-{ymd}{'-es' if lang == 'es' else ''}@neta65-gvlv"


class LaterMonthsKeepTheirJoiningDetails(unittest.TestCase):
    # the months after the last date events.json lists (Jul 7 / Jun 24, 2027), worked out from the rule
    PROJECTED = {"grapevine-meeting": ("2027-08-04", "2027-09-01"),
                 "zoom-workshop": ("2027-07-22", "2027-08-26", "2027-09-23", "2027-10-28")}
    # a date events.json lists, still to come: its calendar text is what a later month's must be (no month flyer)
    LISTED = {"grapevine-meeting": "2027-02-03", "zoom-workshop": "2027-01-28"}

    @classmethod
    def setUpClass(cls):
        cls.items = build()

    def run_pages(self, items, months) -> dict:
        return run_js(self, JS, data={"yaml": SETTINGS, "items": items, "now": NOW, "months": list(months)}, now=NOW)

    def test_the_sync_lists_the_oldest_past_date_last(self):
        """The order the pages read: the series' last record is a past date (what the month pages used to copy)."""
        for series in self.PROJECTED:
            dates = [e for e in self.items if e.get("extra", {}).get("series") == series]
            with self.subTest(series=series):
                self.assertTrue(dates[-1]["extra"]["past"])
                self.assertEqual(dates[-1]["id"], min(e["id"] for e in dates))
                self.assertFalse(dates[0]["extra"]["past"])

    def test_a_later_months_date_has_the_link_and_the_meeting_id(self):
        months = sorted({ymd[:7] for days in self.PROJECTED.values() for ymd in days})
        got = self.run_pages(self.items, months)
        for series, days in self.PROJECTED.items():
            link, code = {"grapevine-meeting": (ROOM, "abc-defg-hij"), "zoom-workshop": (ZOOM, ZOOM_ID)}[series]
            for lang in ("en", "es"):
                listed = entries(got["feed"][lang])[uid(series, self.LISTED[series], lang)]
                self.assertIn(link, listed["DESCRIPTION"])
                for ymd in days:
                    with self.subTest(series=series, date=ymd, lang=lang):
                        month = got["months"][f"{ymd[:7]}:{lang}"]
                        rows = [r for r in month["rows"] if r["series"] == series]
                        self.assertEqual([r["id"] for r in rows], [f"ev:recurring:{series}:{ymd}"])
                        self.assertEqual((rows[0]["past"], rows[0]["srcPast"], rows[0]["online"]), (False, False, True))
                        ev = entries(month["ics"])[uid(series, ymd, lang)]
                        self.assertIn(link, ev["DESCRIPTION"])
                        self.assertIn(code, ev["DESCRIPTION"])
                        self.assertEqual(ev["LOCATION"], link)
                        # the same words as the series' dates /events.ics lists (a series without a page of its
                        # own links its date's card on /events/: "#ev-recurring-zoom-workshop-2027-07-22")
                        self.assertEqual(ev["DESCRIPTION"], listed["DESCRIPTION"].replace(self.LISTED[series], ymd))

    def test_no_flyer_of_another_month(self):
        view = {i["extra"]["name"]: i["extra"]["view_url"] for i in drive_items(FLYERS)}
        july = next(e for e in self.items if e["id"] == "ev:recurring:grapevine-meeting:2027-07-07")
        self.assertEqual(july["extra"]["flyer_url"], view["July 2027 Grapevine Meeting - flyer.png"])
        got = self.run_pages(self.items, ["2027-08"])
        aug = next(r for r in got["months"]["2027-08:en"]["rows"] if r["series"] == "grapevine-meeting")
        self.assertEqual(aug["flyer"], view["Grapevine Meeting - flyer.png"])
        ev = entries(got["months"]["2027-08:en"]["ics"])[uid("grapevine-meeting", "2027-08-04", "en")]
        self.assertNotIn(view["July 2027 Grapevine Meeting - flyer.png"], ev["DESCRIPTION"] + ev.get("ATTACH", ""))
        # a series whose only flyer is named with a month: none for a later month
        only_july = build({("flyers", "July 2027 Grapevine Meeting - flyer.png"): "series"})
        got = self.run_pages(only_july, ["2027-08"])
        aug = next(r for r in got["months"]["2027-08:en"]["rows"] if r["series"] == "grapevine-meeting")
        self.assertIsNone(aug["flyer"])

    def test_only_past_dates_left(self):
        """A sync that has not run since: events.json has only the series' past dates; a later month still to come
        is written with its link and code all the same."""
        stale = [e for e in self.items if e.get("extra", {}).get("past") is True]
        self.assertTrue(any(e["extra"].get("series") == "grapevine-meeting" for e in stale))
        got = self.run_pages(stale, ["2027-03"])
        for lang in ("en", "es"):
            ev = entries(got["months"][f"2027-03:{lang}"]["ics"])[uid("grapevine-meeting", "2027-03-03", lang)]
            with self.subTest(lang=lang):
                self.assertIn(ROOM, ev["DESCRIPTION"])
                self.assertIn("abc-defg-hij", ev["DESCRIPTION"])
                self.assertEqual(ev["LOCATION"], ROOM)


if __name__ == "__main__":
    unittest.main()
