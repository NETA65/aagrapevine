"""Round 30, Unit C — /events/' "Next 5 weeks" calendar: the sidebar's card under the calendar feed (events.njk #ev-cal),
the weeks to come as a month-style grid that stays in view while the list scrolls.

  * the weeks (Weeks: eleventy/filters/committee.js calendarWeeks, the filter cmCalWeeks, on fixed clocks and the
    test's own events, meeting and weekly open meetings — never the day's data or settings):
      - 8 rows of 7 days from the Sunday of the clock's week in CENTRAL time (Saturday 11:30 PM Central is still that
        week, although it is Sunday in UTC), 5 shown and 3 spare (hidden), each ending when its Saturday ends in
        Central time (endIso: the browser drops the row then); today, the days before it (past), the month's short
        name on the grid's first day and on each 1st; the caption of the months shown ("November – December 2026");
      - every upcoming event on its Central day — the committee meeting at 7 PM Central on its Wednesday, never on
        Thursday as in UTC —, an event over several days on each of them (all-day: "All day" each day; a timed one:
        its start on its first day only), one that only runs past midnight on its first day only, one already over
        nowhere; an outside calendar's date without a time with no time; days before the grid left out;
      - the two weekly open meetings every week from their next date or their first one (`starts`), stepped in the
        host's zone: Noon Eastern stays 11:00 AM Central across the clock changes of 2027-03-14 and 2027-11-07 (their
        end, an hour after the start, moves with the zone); their entries lead to #ev-weekly-gv / #ev-weekly-lv;
      - within a day the list's events by start, then the weekly meetings; 3 dots, then "+n"; the day's words for a
        screen reader; the first entry's card is where the day's link goes; the day shown first (today when something
        is on today, else the next day with something on);
      - the colours (eventTone) and the colour key in its order — grey says "NETA 65" only when every grey entry is
        ours —; Spanish weekday, month and time words; nothing on in these weeks → null (no card);
  * the page (Page: a build of /events/ and /es/events/ only, on a fixed clock, with the test's events and weekly
    meetings): the feed card (#subscribe) first, then the calendar in a sticky wrapper (sticky-aside) inside a plain
    aside — the aside itself not sticky, no aside inside it —; data-lastmod="skip" (eleventy/lastmod.js leaves the
    card out of the page's fingerprint); 7 column headers; a tbody with data-cm-max="5" and 8 rows, rows 6–8 hidden;
    every link of the card goes to an id on the page, no id twice, one aria-current="date" (on the build's day);
    none of the strings other tests read the list by (<li id=, cm-month, ev-weekly, cm-menu-note); the test's events
    on their days, a past day without a link; the Spanish page in Spanish;
  * in the browser (Browser: src/assets/js/committee.js on the built card, in the page stand-in of
    tests/test_central_time.py, with the clock moved on): a week later the first row is gone and rows 2–6 show, today
    and the past days moved, the past days' links gone; three weeks later the caption names the months shown; an
    entry that is over is faded and loses its link, the day's link then leads to its next entry; the day shown moves
    on to "Today" / "Next up"; a click on a day shows that day's list instead of jumping (and stays the visitor's
    pick), a past day does nothing; an entry whose card is the address's #id already says "cm:reveal" (the list
    reveals it — Unit B), any other does not;
  * the styles (Styles: committee.css): a fixed-layout table, weekday names on one line (2 letters in a narrow card),
    the dots' colours kept in forced colours.

    python -m unittest tests.test_r30_calendar -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import collections
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
import test_central_time as TCT  # noqa: E402  (the page stand-in, TCT.DOM — a module, so its tests don't run twice)
from test_r21_weekly import weekly_item  # noqa: E402  (the weekly open meetings as weekly_open.json has them)

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-11-13T18:00:00Z"            # Friday, November 13, 2026, noon in Texas: the grid starts on Sunday, Nov 8
SITE = {"url": "https://example.org",    # the test's own committee meeting: every 3rd Wednesday, 7 – 8 PM Central
        "meeting": {"weekday": "wednesday", "week_of_month": 3, "start": "19:00", "end": "20:00", "platform": "Google Meet"}}
WEEKLY = [weekly_item(False), weekly_item(True)]
SPACES = re.compile(r"[   ]")
# the site's words (src/_i18n): the colour key's labels are read from there, as the page does
T = {k: v for f in sorted((ROOT / "src" / "_i18n").glob("*.json")) for k, v in json.loads(f.read_text(encoding="utf-8")).items()}


def plain(s: str) -> str:
    return SPACES.sub(" ", s)


def event(eid: str, title: str, start: str, end: str | None = None, *, category: str = "manual", source: str = "committee",
          url: str = "", **extra) -> dict:
    """An events.json item (scripts/sync/build_data.py) — `start` / `end`: an ISO instant or a date (all day)."""
    x = {"start": start, "end": end, "all_day": len(start) == 10, **extra}
    return {"id": eid, "source": source, "kind": "event", "url": url, "title": title, "summary": "", "lang": "en",
            "date": start, "first_seen": None, "image": None, "tags": [], "category": category, "status": "ok", "extra": x,
            "i18n": {"title": {"en": title, "es": title + " (ES)"}}, "machine": [], "is_new": False}


def gv_meeting(ymd: str, start: str, end: str) -> dict:
    """A date of our Grapevine Meeting (config/site.yml recurring_events → build_data): grey, NETA 65's."""
    it = event(f"ev:recurring:grapevine-meeting:{ymd}", "Grapevine Meeting", start, end, category="recurring",
               series="grapevine-meeting", recurring=True, online_url="https://meet.google.com/abc-defg-hij")
    it["i18n"]["title"]["es"] = "Reunión de Grapevine (en inglés)"
    return it


# --------------------------------------------------------------------------- the weeks (calendarWeeks)
WEEKS_JS = r"""
const res = {};
for (const c of input.cases) {
  const evs = filters.cmEvents(c.items, input.site, c.lang || "en").filter((e) => !e.past);
  const wos = filters.cmWeeklyAll(c.weekly || [], c.lang || "en");
  res[c.name] = filters.cmCalWeeks(evs, wos, c.lang || "en", c.opt || { weeks: 5, spare: 3 });
}
out(res);
"""


def weeks(case: unittest.TestCase, now: str, **cases) -> dict:
    """{name: calendarWeeks(…)} on the clock `now`; each case: { items, weekly, lang, opt }."""
    return run_js(case, WEEKS_JS, data={"site": SITE, "cases": [{"name": k, **v} for k, v in cases.items()]}, now=now)


def days(cal: dict) -> dict[str, dict]:
    return {d["ymd"]: d for w in cal["weeks"] for d in w["days"]}


def entries(cal: dict, ymd: str) -> list[tuple]:
    """A day's entries as (title, time, tone, weekly, anchor)."""
    return [(e["title"], plain(e["time"]), e["tone"], e["weekly"], e["anchor"]) for e in days(cal)[ymd]["events"]]


class Weeks(unittest.TestCase):
    def test_eight_weeks_from_the_sunday_of_this_week_in_central_time(self):
        items = [event("ev:manual:zz-one", "ZZ One", "2026-11-20T18:00:00Z")]
        friday = weeks(self, NOW, en={"items": items})["en"]
        # Saturday, 11:30 PM in Texas — Sunday in UTC — is still the week of Sunday, November 8
        late = weeks(self, "2026-11-15T05:30:00Z", en={"items": items})["en"]
        sunday = weeks(self, "2026-11-15T12:00:00Z", en={"items": items})["en"]
        for cal, first, today in ((friday, "2026-11-08", "2026-11-13"), (late, "2026-11-08", "2026-11-14"), (sunday, "2026-11-15", "2026-11-15")):
            with self.subTest(today=today):
                ymds = [d["ymd"] for w in cal["weeks"] for d in w["days"]]
                self.assertEqual(len(cal["weeks"]), 8)
                self.assertEqual(ymds[0], first)
                self.assertEqual(len(ymds), 56)
                self.assertEqual(len(set(ymds)), 56)
                self.assertEqual(sorted(ymds), ymds)
                self.assertEqual(cal["n"], 5)
                self.assertEqual([w["hidden"] for w in cal["weeks"]], [False] * 5 + [True] * 3)
                self.assertEqual(cal["todayYmd"], today)
                self.assertEqual([d["ymd"] for d in days(cal).values() if d["today"]], [today])
                self.assertEqual([d["ymd"] for d in days(cal).values() if d["past"]], [y for y in ymds if y < today])
                self.assertEqual(cal["captionFrom"], first)
        # each row ends when its Saturday ends in Central time (midnight CST = 06:00 UTC)
        self.assertEqual([w["endIso"] for w in friday["weeks"]][:3],
                         ["2026-11-15T06:00:00.000Z", "2026-11-22T06:00:00.000Z", "2026-11-29T06:00:00.000Z"])
        self.assertEqual([[d["day"] for d in w["days"]] for w in friday["weeks"]][0], [8, 9, 10, 11, 12, 13, 14])
        # the month's short name: the grid's first day and each 1st
        self.assertEqual({y: d["mon"] for y, d in days(friday).items() if d["mon"]},
                         {"2026-11-08": "Nov", "2026-12-01": "Dec", "2027-01-01": "Jan"})
        self.assertEqual(plain(friday["caption"]), "November – December 2026")
        self.assertEqual([wd["short"] for wd in friday["weekdays"]], ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
        self.assertEqual([wd["long"] for wd in friday["weekdays"]][3], "Wednesday")
        self.assertEqual([wd["tiny"] for wd in friday["weekdays"]], ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"])
        # five weeks from Dec 6 reach into January
        dec = weeks(self, "2026-12-07T18:00:00Z", en={"items": [event("ev:manual:zz-two", "ZZ Two", "2026-12-20T18:00:00Z")]})["en"]
        self.assertEqual(plain(dec["caption"]), "December 2026 – January 2027")

    def test_each_event_on_its_central_days(self):
        items = [
            # an evening in Texas is already the next day in UTC
            event("ev:manual:zz-evening", "ZZ Evening", "2026-11-19T01:00:00Z", "2026-11-19T02:00:00Z"),
            # three days, all day
            event("ev:manual:zz-assembly", "ZZ Assembly", "2026-12-04", "2026-12-06"),
            # Friday 6 PM to Sunday noon: three days, its start on the first
            event("ev:manual:zz-retreat", "ZZ Retreat", "2026-11-28T00:00:00Z", "2026-11-29T18:00:00Z"),
            # 7 PM to 1 AM: one evening
            event("ev:manual:zz-late", "ZZ Late Night", "2026-11-22T01:00:00Z", "2026-11-22T07:00:00Z"),
            # all day Thursday to Saturday: began before today — its days before today are past ones, still marked
            event("ev:manual:zz-began", "ZZ Began", "2026-11-12", "2026-11-14"),
            # an outside calendar's date without a time: no time ("Time not listed" on its card)
            event("ev:lvcal:zz", "ZZ Taller", "2026-11-21", category="lv-calendar", source="calendar", url="https://example.org/taller"),
            # over already; and one after the 8 weeks
            event("ev:manual:zz-over", "ZZ Over", "2026-11-13T15:00:00Z", "2026-11-13T16:00:00Z"),
            event("ev:manual:zz-later", "ZZ Later", "2027-01-05T18:00:00Z"),
        ]
        cal = weeks(self, NOW, en={"items": items})["en"]
        d = days(cal)
        on = collections.defaultdict(list)
        for ymd, day in d.items():
            for e in day["events"]:
                on[e["title"]].append(ymd)
        # the test's committee meeting, 3rd Wednesday at 7 PM Central (01:00 UTC on Thursday)
        meeting = [t for t in on if "Committee" in t]
        self.assertEqual(len(meeting), 1)
        self.assertEqual(on[meeting[0]], ["2026-11-18", "2026-12-16"])
        self.assertEqual(on["ZZ Evening"], ["2026-11-18"])
        self.assertEqual(on["ZZ Assembly"], ["2026-12-04", "2026-12-05", "2026-12-06"])
        self.assertEqual(on["ZZ Retreat"], ["2026-11-27", "2026-11-28", "2026-11-29"])
        self.assertEqual(on["ZZ Late Night"], ["2026-11-21"])
        self.assertEqual(on["ZZ Began"], ["2026-11-12", "2026-11-13", "2026-11-14"])
        self.assertEqual(on["ZZ Taller"], ["2026-11-21"])
        self.assertNotIn("ZZ Over", on)
        self.assertNotIn("ZZ Later", on)
        times = {(t, y): plain(e["time"]) for y, day in d.items() for e in day["events"] for t in [e["title"]]}
        self.assertEqual(times[(meeting[0], "2026-11-18")], "7:00 PM")
        self.assertEqual([times[("ZZ Assembly", y)] for y in on["ZZ Assembly"]], ["All day"] * 3)
        self.assertEqual([times[("ZZ Retreat", y)] for y in on["ZZ Retreat"]], ["6:00 PM", "", ""])
        self.assertEqual(times[("ZZ Late Night", "2026-11-21")], "7:00 PM")
        self.assertEqual(times[("ZZ Taller", "2026-11-21")], "")
        # each entry leads to its card; its end is the card's
        self.assertEqual(entries(cal, "2026-12-05")[0][4], "ev-manual-zz-assembly")
        self.assertEqual(d["2026-12-05"]["events"][0]["endIso"], "2026-12-07T06:00:00.000Z")
        self.assertEqual(d["2026-11-18"]["events"][0]["endIso"], "2026-11-19T02:00:00.000Z")

    def test_the_weekly_meetings_every_week_from_their_first_date(self):
        # La Viña's meeting starts on Thursday, November 19 (its `starts`): no Thursday before it
        lv = weekly_item(True)
        lv["extra"].update({"starts": "2026-11-19", "next_start": "2026-11-19T17:00:00Z"})
        cal = weeks(self, NOW, en={"items": [], "weekly": [weekly_item(False), lv]})["en"]
        d = days(cal)
        gv = [y for y, day in d.items() if any(e["anchor"] == "ev-weekly-gv" for e in day["events"])]
        lvd = [y for y, day in d.items() if any(e["anchor"] == "ev-weekly-lv" for e in day["events"])]
        # (Wednesday, November 11 is over: the next one is the 18th)
        self.assertEqual(gv, ["2026-11-18", "2026-11-25", "2026-12-02", "2026-12-09", "2026-12-16", "2026-12-23", "2026-12-30"])
        self.assertEqual(lvd, ["2026-11-19", "2026-11-26", "2026-12-03", "2026-12-10", "2026-12-17", "2026-12-24", "2026-12-31"])
        e = d["2026-11-18"]["events"][-1]
        self.assertEqual((e["title"], plain(e["time"]), e["tone"], e["weekly"]), ("Grapevine Weekly Open AA Meeting", "11:00 AM", "gv", True))
        self.assertEqual(d["2026-11-19"]["events"][-1]["tone"], "lv")
        self.assertTrue(cal["weekly"])
        # the 11 AM Central meeting is over at noon Central: an hour after it starts
        self.assertEqual(e["endIso"], "2026-11-18T18:00:00.000Z")
        # under way (11:30 AM): listed; at 12:10 PM — its card still says "Live now" — its hour is over: not listed
        during = weeks(self, "2026-11-18T17:30:00Z", en={"items": [], "weekly": [weekly_item(False)]})["en"]
        after = weeks(self, "2026-11-18T18:10:00Z", en={"items": [], "weekly": [weekly_item(False)]})["en"]
        self.assertTrue([x for x in days(during)["2026-11-18"]["events"] if x["weekly"]])
        self.assertEqual([x for x in days(after)["2026-11-18"]["events"] if x["weekly"]], [])
        self.assertTrue([x for x in days(after)["2026-11-25"]["events"] if x["weekly"]])

    def test_noon_eastern_stays_11_am_central_across_the_clock_changes(self):
        for now, when in (("2027-03-01T18:00:00Z", {"2027-03-10": "18:00", "2027-03-17": "17:00"}),     # 2027-03-14
                          ("2027-10-25T18:00:00Z", {"2027-11-03": "17:00", "2027-11-10": "18:00"})):    # 2027-11-07
            with self.subTest(now=now):
                cal = weeks(self, now, en={"items": [], "weekly": [weekly_item(False)]})["en"]
                gv = [(y, e) for y, day in days(cal).items() for e in day["events"] if e["weekly"]]
                self.assertEqual(len(gv), 8, "a Wednesday each week")
                self.assertEqual({plain(e["time"]) for _, e in gv}, {"11:00 AM"}, "Noon Eastern = 11 AM Central, every week")
                self.assertLessEqual(set(when), {y for y, _ in gv})
                for y, e in gv:
                    self.assertEqual(date.fromisoformat(y).weekday(), 2, "a Wednesday")
                    if y in when:
                        # its end (an hour after its start, in UTC) moves with Eastern time's clock change
                        self.assertEqual(e["endIso"], f"{y}T{when[y]}:00.000Z")

    def test_a_day_in_order_with_its_words_dots_and_link(self):
        items = [event("ev:manual:zz-morning", "ZZ Morning", "2026-11-18T15:00:00Z", "2026-11-18T16:00:00Z"),
                 event("ev:manual:zz-night", "ZZ Night", "2026-11-19T02:00:00Z", "2026-11-19T03:00:00Z"),
                 event("ev:manual:zz-allday", "ZZ All Day", "2026-11-18"),
                 event("ev:manual:zz-booth", "ZZ Book Booth", "2026-11-14T23:30:00Z", "2026-11-15T01:30:00Z")]
        cal = weeks(self, NOW, en={"items": items, "weekly": WEEKLY})["en"]
        day = days(cal)["2026-11-18"]
        titles = [e[0] for e in entries(cal, "2026-11-18")]
        # the list's events by their start (all day first), the weekly meeting last although it is at 11 AM
        self.assertEqual(titles[:2], ["ZZ All Day", "ZZ Morning"])
        self.assertIn("Committee", titles[2])
        self.assertEqual(titles[3:], ["ZZ Night", "Grapevine Weekly Open AA Meeting"])
        self.assertEqual(len(day["dots"]), 3)
        self.assertEqual(day["more"], 2)
        self.assertEqual(day["first"], "ev-manual-zz-allday")
        self.assertEqual(day["label"], "Wednesday, November 18")
        self.assertEqual(plain(day["sr"]), "Wednesday, November 18: ZZ All Day, All day; ZZ Morning, 9:00 AM; " + titles[2]
                         + ", 7:00 PM; ZZ Night, 8:00 PM; Grapevine Weekly Open AA Meeting, 11:00 AM, every week")
        # a day with nothing on
        self.assertEqual((days(cal)["2026-11-16"]["events"], days(cal)["2026-11-16"]["sr"], days(cal)["2026-11-16"]["first"]), ([], "", ""))
        # the day shown first: nothing today (Friday 13th) → the next day with something on, Saturday's booth
        self.assertEqual((cal["panel"], cal["panelToday"]), ("2026-11-14", False))
        today = weeks(self, "2026-11-14T18:00:00Z", en={"items": items, "weekly": WEEKLY})["en"]
        self.assertEqual((today["panel"], today["panelToday"]), ("2026-11-14", True))

    def test_the_colours_and_the_key(self):
        items = [gv_meeting("2026-12-02", "2026-12-03T01:00:00Z", "2026-12-03T02:00:00Z"),
                 event("ev:manual:zz-booth", "ZZ Literature Booth", "2026-11-14T23:30:00Z", "2026-11-15T01:30:00Z"),
                 event("ev:manual:zz-assembly", "ZZ Area Assembly", "2026-12-04", "2026-12-06")]
        # grey from somebody else's calendar (an outside feed: not ours)
        other = items + [event("ev:feed:zz", "ZZ Spring Retreat", "2026-11-25", category="feed", source="calendar", url="https://example.org/r")]
        got = weeks(self, NOW, ours={"items": items, "weekly": WEEKLY}, other={"items": other, "weekly": WEEKLY},
                    none={"items": items})
        cal = got["ours"]
        tone = {e[0]: (e[2], e[3]) for y in days(cal) for e in entries(cal, y)}
        self.assertEqual(tone["Grapevine Meeting"], ("other", False))
        self.assertEqual(tone["ZZ Literature Booth"], ("booth", False))
        self.assertEqual(tone["ZZ Area Assembly"], ("assembly", False))
        self.assertEqual(tone["Grapevine Weekly Open AA Meeting"], ("gv", True))
        self.assertEqual(tone["La Viña Open Meeting (in Spanish)"], ("lv", True))
        self.assertEqual([k["tone"] for k in cal["kinds"]], ["committee", "gv", "lv", "booth", "assembly", "other"])
        self.assertEqual(cal["kinds"][-1]["label"], T["committee.events.kind.neta"]["en"], "every grey entry is ours (the Grapevine Meeting)")
        self.assertEqual(got["other"]["kinds"][-1], {"tone": "other", "label": T["committee.events.kind.other"]["en"]})
        self.assertEqual(cal["kinds"][0]["label"], T["committee.events.kind.committee"]["en"])
        self.assertFalse(got["none"]["weekly"])
        self.assertEqual([k["tone"] for k in got["none"]["kinds"]], ["committee", "booth", "assembly", "other"])

    def test_in_spanish(self):
        items = [gv_meeting("2026-12-02", "2026-12-03T01:00:00Z", "2026-12-03T02:00:00Z")]
        cal = weeks(self, NOW, es={"items": items, "weekly": WEEKLY, "lang": "es"})["es"]
        self.assertEqual([wd["short"] for wd in cal["weekdays"]], ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"])
        self.assertEqual([wd["tiny"] for wd in cal["weekdays"]], ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sá"])
        self.assertEqual([wd["long"] for wd in cal["weekdays"]], ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        self.assertEqual(plain(cal["caption"]), "Noviembre–diciembre de 2026")
        d = days(cal)
        self.assertEqual(d["2026-12-01"]["mon"], "Dic")
        self.assertEqual(d["2026-12-02"]["label"], "Miércoles, 2 de diciembre")
        self.assertEqual(entries(cal, "2026-12-02")[0][:2], ("Reunión de Grapevine (en inglés)", "7:00 p. m."))
        self.assertTrue(plain(d["2026-12-02"]["sr"]).endswith("11:00 a. m., cada semana"), d["2026-12-02"]["sr"])
        self.assertEqual(cal["kinds"][0]["label"], T["committee.events.kind.committee"]["es"])

    def test_nothing_on_gives_no_card(self):
        far = [event("ev:manual:zz-far", "ZZ Far", "2027-06-01T18:00:00Z")]
        r = run_js(self, r"""
          const far = filters.cmEvents(input.far, {}, "en", {}).filter((e) => !e.committee);
          out({ none: filters.cmCalWeeks([], [], "en", { weeks: 5, spare: 3 }), far: filters.cmCalWeeks(far, [], "en"),
                bare: filters.cmCalWeeks(far, [{ title: "No date" }], "en") });""", data={"far": far}, now=NOW)
        self.assertEqual(r, {"none": None, "far": None, "bare": None})


# --------------------------------------------------------------------------- the page
def page_items() -> list[dict]:
    """The test's events for the page (on top of the committee meetings of config/site.yml, which the checks below
    never name): a booth on Saturday 14th, an all-day retreat that began on Thursday 12th, an outside calendar's date
    without a time, our Grapevine Meeting, an assembly over three days and a morning workshop."""
    return [
        event("ev:manual:2026-11-14-zz-booth", "ZZ Literature Booth", "2026-11-14T23:30:00Z", "2026-11-15T01:30:00Z"),
        event("ev:manual:2026-11-12-zz-retreat", "ZZ Retreat", "2026-11-12", "2026-11-14"),
        event("ev:lvcal:zztaller", "ZZ Taller", "2026-11-21", category="lv-calendar", source="calendar", url="https://example.org/taller"),
        gv_meeting("2026-12-02", "2026-12-03T01:00:00Z", "2026-12-03T02:00:00Z"),
        event("ev:manual:2026-12-04-zz-assembly", "ZZ Area Assembly", "2026-12-04", "2026-12-06"),
        event("ev:manual:2026-12-09-zz-workshop", "ZZ Morning Workshop", "2026-12-09T15:00:00Z", "2026-12-09T16:00:00Z"),
    ]


PAGE_JS = r"""
process.env.ONLY = "events.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const L = await imp("eleventy/lastmod.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r30-calendar-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { ...(data.db || {}).events, items: input.items },
                         weekly_open: { updated: "2026-11-13T12:00:00Z", items: input.weekly } }),
      });
    },
  });
  const pages = (await elev.toJSON()).filter((p) => /\/events\/$/.test(p.url));
  out(Object.fromEntries(pages.map((p) => [p.url.includes("/es/") ? "es" : "en",
    { html: p.content, fingerprinted: L.dropSkipped(p.content).includes('id="ev-cal"') }])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
BUILT: dict[str, dict] = {}


def built(case: unittest.TestCase) -> dict:
    """/events/ and /es/events/ built on NOW with the test's events and weekly meetings → {lang: {html, fingerprinted}}."""
    if "pages" not in BUILT:
        BUILT["pages"] = run_js(case, PAGE_JS, data={"items": page_items(), "weekly": WEEKLY}, timeout=600, now=NOW)
    return BUILT["pages"]


def calendar_html(page: str) -> str:
    start = page.index('<section id="ev-cal"')
    return page[start:page.index("</section>", start) + len("</section>")]


def cell(cal: str, ymd: str) -> str:
    return re.search(rf'<td [^>]*data-cm-day="{ymd}"[^>]*>[\s\S]*?</td>', cal).group(0)


class Page(unittest.TestCase):
    def test_the_sidebar_feed_first_then_the_sticky_calendar(self):
        for lang, got in built(self).items():
            html = got["html"]
            with self.subTest(lang=lang):
                aside = html[html.index('<aside class="min-w-0" aria-label='):]
                aside = aside[:aside.index("</aside>")]
                self.assertNotIn("sticky-aside\" aria-label", html, "the aside itself is not sticky")
                self.assertLess(aside.index('<div id="subscribe">'), aside.index('<div class="sticky-aside mt-6">'))
                self.assertLess(aside.index('<div class="sticky-aside mt-6">'), aside.index('<section id="ev-cal"'))
                self.assertNotIn("<aside", aside[1:], "no aside inside the aside")
                self.assertRegex(aside, r'<section id="ev-cal" class="cm-cal-card card card-pad" data-cm-cal data-lastmod="skip" '
                                        r'aria-labelledby="ev-cal-title">')
                self.assertFalse(got["fingerprinted"], "the card moves with the day: never part of the page's fingerprint")

    def test_the_grid(self):
        for lang, got in built(self).items():
            cal = calendar_html(got["html"])
            with self.subTest(lang=lang):
                self.assertEqual(len(re.findall(r'<th scope="col">', cal)), 7)
                self.assertEqual(cal.count('<tbody data-cm-max="5">'), 1)
                rows = re.findall(r'<tr data-cm-expire="([^"]+)"( class="hidden")?>', cal)
                self.assertEqual(len(rows), 8)
                self.assertEqual([bool(h) for _, h in rows], [False] * 5 + [True] * 3)
                self.assertEqual(rows[0][0], "2026-11-15T06:00:00.000Z")
                self.assertEqual(len(re.findall(r'<td class="cm-cal-d[^"]*" data-cm-day="\d{4}-\d{2}-\d{2}"', cal)), 56)
                # the strings other tests read the list by never appear in the card
                for s in ("<li id=", 'class="cm-month"', 'id="ev-weekly"', "cm-menu-note", "<aside", "data-group="):
                    self.assertNotIn(s, cal)

    def test_every_link_goes_to_the_page_and_no_id_twice(self):
        for lang, got in built(self).items():
            html, cal = got["html"], calendar_html(got["html"])
            with self.subTest(lang=lang):
                ids = collections.Counter(re.findall(r'\sid="([^"]+)"', html))
                self.assertEqual([k for k, n in ids.items() if n > 1], [])
                targets = set(re.findall(r'href="#([^"]+)"', cal))
                self.assertGreater(len(targets), 6)
                self.assertEqual(sorted(t for t in targets if t not in ids), [])
                self.assertIn("ev-weekly-gv", targets)
                self.assertIn("ev-weekly-lv", targets)
                self.assertIn("ev-recurring-grapevine-meeting-2026-12-02", targets)
                # one "today", the build's
                self.assertEqual(html.count('aria-current="date"'), 1)
                self.assertRegex(cell(cal, "2026-11-13"), r'^<td class="cm-cal-d is-today is-selected" data-cm-day="2026-11-13" aria-current="date">')

    def test_the_events_on_their_days(self):
        got = built(self)
        en, es = calendar_html(got["en"]["html"]), calendar_html(got["es"]["html"])
        # Saturday 14th: the retreat (all day, first) and the booth
        sat = cell(en, "2026-11-14")
        self.assertIn('href="#ev-manual-2026-11-12-zz-retreat" data-cm-cal-day="2026-11-14"', sat)
        self.assertIn("Saturday, November 14: ZZ Retreat, All day; ZZ Literature Booth, 5:30", plain(sat))
        self.assertNotIn("is-selected", sat)
        # today, the retreat's second day: today's list shows first
        self.assertIn("is-selected", cell(en, "2026-11-13"))
        self.assertRegex(en, r'<div class="cm-cal-panel" data-cm-cal-panel="2026-11-13">\s*<h3 class="cm-cal-ph"><span class="cm-cal-tag" '
                             r'data-cm-cal-tag>Today</span> Friday, November 13</h3>')
        self.assertEqual(len(re.findall(r'data-cm-cal-panel="[^"]+">', en)), 1, "one list shows")
        # Thursday 12th, before today: the retreat's dot, no link
        thu = cell(en, "2026-11-12")
        self.assertIn("is-past", thu)
        self.assertIn('<a class="cm-cal-link" data-cm-cal-day="2026-11-12">', thu)
        self.assertNotIn("href=", thu)
        # the assembly on each of its three days, in its colour
        for ymd in ("2026-12-04", "2026-12-05", "2026-12-06"):
            self.assertIn('href="#ev-manual-2026-12-04-zz-assembly"', cell(en, ymd))
            self.assertIn("cm-cal-dot ev-tone-assembly", cell(en, ymd))
        # Wednesday, Dec 2: our Grapevine Meeting (grey), then the Weekly Open (a ring)
        wed = cell(en, "2026-12-02")
        self.assertIn('href="#ev-recurring-grapevine-meeting-2026-12-02"', wed)
        self.assertIn('<span class="cm-cal-dot ev-tone-other"></span><span class="cm-cal-dot ev-tone-gv is-weekly"></span>', wed)
        self.assertIn('<a class="cm-cal-ev" href="#ev-weekly-gv">Grapevine Weekly Open AA Meeting</a> <span class="cm-cal-wk">· Every week</span>', en)
        # the colour key and the help
        self.assertIn(T["committee.events.kind.neta"]["en"] + "</li>", en)
        self.assertIn('<li><span class="cm-cal-dot is-weekly"></span>Every week</li>', en)
        self.assertIn("Times are Central time.", en)
        # Spanish
        self.assertIn("Próximas 5 semanas</h2>", es)
        self.assertIn('<span class="cm-cal-wd" aria-hidden="true">Mié</span><span class="cm-cal-wd2" aria-hidden="true">Mi</span>'
                      '<span class="sr-only">Miércoles</span>', es)
        self.assertIn(">Noviembre–diciembre de 2026</p>", plain(es))
        self.assertIn("Sábado, 14 de noviembre: ZZ Retreat (ES), Todo el día; ZZ Literature Booth (ES), 5:30 p. m.", plain(es))
        self.assertIn('data-cm-cal-tag>Hoy</span> Viernes, 13 de noviembre</h3>', es)
        self.assertIn("Los horarios están en hora del Centro.", es)


# --------------------------------------------------------------------------- in the browser
# A small HTML reader for the page stand-in (TCT.DOM's el()): the built card becomes elements the script can query.
PARSE = r"""
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);
const decode = (s) => s.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'");
function parse(src) {
  const top = el("div", {}, []), stack = [top];
  const re = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*(\/?)>|([^<]+)/g;
  let m;
  while ((m = re.exec(src))) {
    const parent = stack[stack.length - 1];
    if (m[5] !== undefined) { if (m[5].trim()) parent.appendChild(el("#text", {}, [], decode(m[5]))); continue; }
    if (!m[2]) continue;
    if (m[1]) {
      for (let i = stack.length - 1; i > 0; i--) if (stack[i].tagName === m[2].toUpperCase()) { stack.length = i; break; }
      continue;
    }
    const attrs = {};
    for (const a of m[3].matchAll(/([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) attrs[a[1]] = decode(a[2] ?? a[3] ?? a[4] ?? "");
    const node = parent.appendChild(el(m[2].toLowerCase(), attrs, []));
    if (!VOID.has(m[2].toLowerCase()) && !m[4]) stack.push(node);
  }
  return top.children;
}
// What the card shows: the rows (shown / spare / gone), today, the past days, each day's link, the list shown and its
// heading's tag, the picked day, the entries that are over, the caption.
function snap(doc) {
  const cal = doc.querySelector("[data-cm-cal]"), cap = cal.querySelector("[data-cm-cal-cap]");
  const ymd = (e) => e.getAttribute("data-cm-day");
  const tds = cal.querySelectorAll("[data-cm-day]");
  return {
    rows: cal.querySelectorAll("tr[data-cm-expire]").map((tr) => (tr.hidden ? "gone" : tr.classList.contains("hidden") ? "spare" : "shown")),
    today: tds.filter((td) => td.classList.contains("is-today")).map(ymd),
    current: tds.filter((td) => td.getAttribute("aria-current") === "date").map(ymd),
    past: tds.filter((td) => td.classList.contains("is-past")).map(ymd),
    selected: tds.filter((td) => td.classList.contains("is-selected")).map(ymd),
    links: Object.fromEntries(cal.querySelectorAll("a[data-cm-cal-day]").map((a) => [a.getAttribute("data-cm-cal-day"), a.getAttribute("href")])),
    panel: cal.querySelectorAll("[data-cm-cal-panel]").filter((d) => !d.hidden).map((d) => [d.getAttribute("data-cm-cal-panel"), d.querySelector("[data-cm-cal-tag]").textContent]),
    over: cal.querySelectorAll("[data-cm-cal-end]").filter((li) => li.classList.contains("is-over")).map((li) => [li.querySelector("a").textContent, li.querySelector("a").getAttribute("href")]),
    caption: cap.textContent, from: cap.getAttribute("data-cm-cal-cap"),
  };
}
function open(at) {
  const p = page(parse(input.html), { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], at });
  p.ready();
  p.cal = p.doc.querySelector("[data-cm-cal]");
  // a click on a link of the card: its delegated listener (→ whether the browser's own jump was stopped)
  p.click = (sel) => {
    const a = p.cal.querySelector(sel);
    let stopped = false;
    for (const fn of p.cal.listeners.click || []) fn({ target: a, preventDefault() { stopped = true; } });
    return stopped;
  };
  p.at = (iso) => { p.clock.now = Date.parse(iso); p.minute(); };
  return p;
}
"""


def browser(case: unittest.TestCase, script: str) -> dict:
    html = calendar_html(built(case)["en"]["html"])
    return run_js(case, TCT.DOM + PARSE + script, data={"html": html}, timeout=180)


class Browser(unittest.TestCase):
    def test_as_the_build_left_it(self):
        r = browser(self, f'const p = open("{NOW}"); out(snap(p.doc));')
        self.assertEqual(r["rows"], ["shown"] * 5 + ["spare"] * 3)
        self.assertEqual((r["today"], r["current"]), (["2026-11-13"], ["2026-11-13"]))
        self.assertEqual(r["past"], ["2026-11-08", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"])
        self.assertEqual(r["panel"], [["2026-11-13", "Today"]])
        self.assertEqual(r["selected"], ["2026-11-13"])
        self.assertIsNone(r["links"]["2026-11-12"])
        self.assertEqual(r["links"]["2026-11-13"], "#ev-manual-2026-11-12-zz-retreat")
        self.assertEqual(r["links"]["2026-11-14"], "#ev-manual-2026-11-12-zz-retreat")
        self.assertEqual((plain(r["caption"]), r["from"]), ("November – December 2026", "2026-11-08"))
        self.assertEqual(r["over"], [])

    def test_a_week_later_and_three_weeks_later(self):
        r = browser(self, f"""
          const p = open("{NOW}");
          p.at("2026-11-20T18:00:00Z");          // Friday, November 20
          const week = snap(p.doc);
          p.at("2026-12-05T18:00:00Z");          // Saturday, December 5: the assembly's second day
          out({{ week, three: snap(p.doc) }});""")
        w = r["week"]
        self.assertEqual(w["rows"], ["gone"] + ["shown"] * 5 + ["spare"] * 2, "the first week went; rows 2–6 show")
        self.assertEqual((w["today"], w["current"]), (["2026-11-20"], ["2026-11-20"]))
        self.assertEqual(w["past"][-1], "2026-11-19")
        self.assertNotIn("2026-11-20", w["past"])
        for ymd in ("2026-11-14", "2026-11-18", "2026-11-19"):
            self.assertIsNone(w["links"][ymd], f"{ymd} is over: no link")
        self.assertIsNotNone(w["links"]["2026-11-21"])
        self.assertEqual(w["panel"], [["2026-11-21", "Next up"]], "the list shown moves on to the next day with something on")
        self.assertEqual(w["selected"], ["2026-11-21"])
        self.assertEqual(w["from"], "2026-11-15")
        t = r["three"]
        self.assertEqual(t["rows"], ["gone"] * 3 + ["shown"] * 5)
        self.assertEqual(t["panel"], [["2026-12-05", "Today"]])
        self.assertEqual((plain(t["caption"]), t["from"]), ("November 2026 – January 2027", "2026-11-29"))

    def test_what_is_over_is_faded_and_the_days_link_moves_on(self):
        r = browser(self, f"""
          const p = open("{NOW}");
          p.at("2026-11-14T18:00:00Z");          // Saturday noon: today has the retreat and the booth
          const sat = snap(p.doc);
          p.at("2026-11-15T01:45:00Z");          // 7:45 PM: the booth is over, the retreat (all day) is not
          const evening = snap(p.doc);
          p.at("2026-11-15T07:00:00Z");          // Sunday, 1 AM
          const sunday = snap(p.doc);
          p.at("2026-12-09T16:30:00Z");          // Wednesday, December 9, 10:30 AM: the morning workshop is over
          out({{ sat, evening, sunday, dec9: snap(p.doc) }});""")
        self.assertEqual(r["sat"]["panel"], [["2026-11-14", "Today"]])
        self.assertEqual(r["evening"]["over"], [["ZZ Literature Booth", None]])
        self.assertEqual(r["evening"]["panel"], [["2026-11-14", "Today"]], "the retreat is still on today")
        self.assertEqual(r["evening"]["links"]["2026-11-14"], "#ev-manual-2026-11-12-zz-retreat")
        self.assertEqual(r["sunday"]["today"], ["2026-11-15"])
        self.assertIn("2026-11-14", r["sunday"]["past"])
        self.assertIsNone(r["sunday"]["links"]["2026-11-14"])
        self.assertEqual(r["sunday"]["panel"][0][1], "Next up")
        self.assertGreater(r["sunday"]["panel"][0][0], "2026-11-15")
        # Dec 9: the workshop (first) is over → the day's link goes to the Weekly Open, still to come
        self.assertIn(["ZZ Morning Workshop", None], r["dec9"]["over"])
        self.assertEqual(r["dec9"]["links"]["2026-12-09"], "#ev-weekly-gv")
        self.assertEqual(r["dec9"]["panel"], [["2026-12-09", "Today"]])

    def test_a_click_on_a_day_shows_its_list(self):
        r = browser(self, f"""
          const p = open("{NOW}");
          const stopped = p.click('a[data-cm-cal-day="2026-12-02"]');
          const picked = snap(p.doc);
          p.at("2026-11-13T19:00:00Z");          // a minute later: still the visitor's pick
          const later = snap(p.doc);
          const past = p.click('a[data-cm-cal-day="2026-11-12"]');
          out({{ stopped, picked, later, past, pastSnap: snap(p.doc) }});""")
        self.assertTrue(r["stopped"], "no jump: the day's list shows instead")
        self.assertEqual(r["picked"]["panel"], [["2026-12-02", ""]])
        self.assertEqual(r["picked"]["selected"], ["2026-12-02"])
        self.assertEqual(r["later"]["panel"], [["2026-12-02", ""]])
        self.assertFalse(r["past"], "a past day is no link: nothing happens")
        self.assertEqual(r["pastSnap"]["panel"], [["2026-12-02", ""]])

    def test_a_click_on_the_day_already_shown_keeps_next_up(self):
        r = browser(self, '''
          const p = open("2026-11-16T18:00:00Z");     // Monday: nothing on today, Wednesday is next
          const before = snap(p.doc).panel;
          const day = before[0][0];
          p.click('a[data-cm-cal-day="' + day + '"]');
          const same = snap(p.doc).panel;
          p.click('a[data-cm-cal-day="2026-12-02"]');
          out({ before, same, other: snap(p.doc).panel });''')
        self.assertEqual(r["before"], [["2026-11-18", "Next up"]])
        self.assertEqual(r["same"], [["2026-11-18", "Next up"]])
        self.assertEqual(r["other"], [["2026-12-02", ""]])

    def test_an_entry_already_in_the_address_asks_the_list_to_reveal_it(self):
        r = browser(self, f"""
          const p = open("{NOW}");
          const said = [];
          p.win.addEventListener("cm:reveal", (e) => said.push(e.detail));
          p.click('a[data-cm-cal-day="2026-12-02"]');
          const sel = 'a[href="#ev-recurring-grapevine-meeting-2026-12-02"]';
          // (the panel's entry, not the day's link: both go there)
          const entry = p.cal.querySelectorAll(sel).filter((a) => a.closest("[data-cm-cal-panel]"))[0];
          const click = () => {{ let stopped = false; for (const fn of p.cal.listeners.click) fn({{ target: entry, preventDefault() {{ stopped = true; }} }}); return stopped; }};
          p.win.location.hash = "";
          const first = click();
          p.win.location.hash = "#ev-recurring-grapevine-meeting-2026-12-02";
          const again = click();
          out({{ said, first, again }});""")
        self.assertEqual(r["said"], [{"id": "ev-recurring-grapevine-meeting-2026-12-02"}], "only when there is no hashchange")
        self.assertFalse(r["first"], "the link itself still goes to the card")
        self.assertFalse(r["again"])


# --------------------------------------------------------------------------- the styles and the wiring
class Styles(unittest.TestCase):
    def test_the_card_never_pushes_the_page_sideways_and_keeps_its_colours(self):
        css = (ROOT / "src" / "assets" / "css" / "areas" / "committee.css").read_text(encoding="utf-8")
        self.assertIn(".cm-cal { width: 100%; margin-top: 0.625rem; table-layout: fixed;", css)
        self.assertRegex(css, r"\.cm-cal th \{[^}]*white-space: nowrap;")
        self.assertIn(".cm-cal-card { container-type: inline-size; }", css)
        self.assertIn("@container (width < 12.5rem) { .cm-cal-wd { display: none; } .cm-cal-wd2 { display: inline; } }", css)
        forced = css[css.index("@media (forced-colors: active) {\n  .cm-cal-dot"):]
        self.assertIn(".cm-cal-dot { forced-color-adjust: none; }", forced[:400])
        self.assertIn("outline: 2px solid Highlight", forced[:400])
        js = (ROOT / "src" / "assets" / "js" / "committee.js").read_text(encoding="utf-8")
        self.assertIn("  expire();\n  calendar();\n", js)
        self.assertIn("setInterval(function () { expire(); calToday();", js)


if __name__ == "__main__":
    unittest.main()
