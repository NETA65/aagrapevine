"""Round 36 — the weekly open meetings in the calendar feeds (/events.ics, /es/events.ics; November 2026):

  * both feeds hold AA Grapevine's Weekly Open (Wednesdays) and La Viña's Reunión Abierta (Thursdays) — the two
    "every week" cards of /events/#ev-weekly — as ONE entry each that repeats every week (RRULE:FREQ=WEEKLY;BYDAY=WE /
    TH) at Noon Eastern in its own zone (DTSTART;TZID=America/New_York …, an hour long), with that zone's VTIMEZONE
    before every VEVENT. Read back with icalendar and stepped week by week by hand, through the days the clocks change
    (2027-03-14, 2027-11-07), every meeting is at 11:00 AM Central — with the feed's own VTIMEZONE as with the zone
    database;
  * its first date never moves from build to build (a subscribed calendar reads the feed every 12 hours): the
    meeting's first day (extra.starts: La Viña's, 2026-11-05), else its first meeting day on or after the day the site
    first saw it (first_seen, read in the HOST's zone), else its next date — the same entry, word for word, from
    builds weeks apart but for DTSTAMP and SEQUENCE; its VTIMEZONE has the zone's rules of the build's year, not of
    that first date's (a series that began in Mexico City in June 2022 does not keep the daylight time dropped since);
  * its UID is the one of the meeting's own file in that language (/meetings/weekly-open-gv.ics … — weeklyCalendar),
    every UID of a feed is there once, and no entry has a reminder (VALARM: a subscriber would get over a hundred);
  * its words are the feed's language (Spanish in /es/events.ics), with the Zoom link, meeting ID, passcode and a
    "Details:" line that is its URL: /meetings/#weekly-open (a section /meetings/ has, as a committee meeting's
    #committee-meeting); CATEGORIES the label of the chip its /events/ card shows under (GV & LV calendars);
  * no weekly entry for a meeting without a date, one that is gone, no data or a COMMITTEE_EMPTY build — and a
    calendar with no component at all still gets the site's VTIMEZONE (valid), one with only the weekly meetings not;
  * the words that promise it: the feed's own description and the subscribe card (committee.ics.desc,
    committee.sub.text) name the weekly open meetings in both languages.

No network; the feeds are rendered by src/pages/events-ics.11ty.js itself, on a fixed clock, with weekly open meetings
of the test's own (shaped like data/site/weekly_open.json).

    python -m unittest tests.test_ics_weekly_open -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHI, NY = ZoneInfo("America/Chicago"), ZoneInfo("America/New_York")
SITE_URL = "https://example.org/site"
SITE = {"url": SITE_URL, "links": {},
        "meeting": {"weekday": "wednesday", "week_of_month": 3, "start": "19:00", "end": "20:00", "skip_dates": []}}
ZOOM_URL = "https://us02web.zoom.us/j/83456789012?pwd=MadeUpToken.1"
ZOOM_ID, PASSCODE = "834 5678 9012", "975310"
NOV19 = "2026-11-19T18:00:00Z"       # Thu Nov 19, 2026, noon Central: La Viña's meeting of the day is under way
JAN10 = "2027-01-10T15:00:00Z"       # Sun Jan 10, 2027: seven weeks later


def i18n() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


T = i18n()


def weekly_item(lv: bool, **extra) -> dict:
    """A weekly_open.json item as scripts/sync/weekly_open.py writes it (GV: first seen 2026-09-23; La Viña: its
    first day, `starts`)."""
    x = {"zoom_id": ZOOM_ID, "passcode": PASSCODE, "zoom_url": ZOOM_URL, "start_local": "12:00",
         "timezone": "America/New_York", "time_central": "11 AM Central"}
    if lv:
        x.update({"day": "Jueves", "time": "12 p. m. (hora del Este)", "weekday": "thursday",
                  "next_start": "2026-11-19T17:00:00Z", "starts": "2026-11-05", "url": "https://www.aalavina.org/podcast"})
        title = {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"}
        summary = {"en": "A virtual open AA meeting in Spanish.", "es": "Una reunión abierta virtual de AA en español."}
    else:
        x.update({"day": "Wednesdays", "time": "Noon Eastern", "weekday": "wednesday",
                  "url": "https://www.aagrapevine.org/grapevine-weekly-open", "next_start": "2026-11-25T17:00:00Z"})
        title = {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"}
        summary = {"en": "Each week AA Grapevine holds an open virtual AA meeting.",
                   "es": "Cada semana AA Grapevine celebra una reunión abierta."}
    x.update(extra)
    return {"id": "weekly_open_lv" if lv else "weekly_open", "source": "lavina" if lv else "grapevine",
            "kind": "meeting", "url": x["url"], "title": title["es" if lv else "en"],
            "summary": summary["es" if lv else "en"], "lang": "es" if lv else "en", "status": "ok",
            "first_seen": "2026-09-24T15:46:38Z" if lv else "2026-09-23T16:30:28Z", "extra": x,
            "i18n": {"title": title, "summary": summary}}


WEEKLY = [weekly_item(False), weekly_item(True)]

# src/pages/events-ics.11ty.js and src/pages/meetings-weekly-ics.11ty.js as the build runs them (this.t, the build's
# clock: run_js now), for each case of input.cases: { weekly (null: no weekly_open data at all), empty
# (COMMITTEE_EMPTY) } → { en, es } feeds; and the weekly files of input.weekly → { path: text }.
FEEDS_JS = r"""
const conf = await imp("eleventy.config.js");
const feed = await imp("src/pages/events-ics.11ty.js");
const W = await imp("src/pages/meetings-weekly-ics.11ty.js");
const render = (lang, weekly) => feed.render.call({ t: (k, l, v) => conf.translateKey(k, l, v) },
  { lang, site: input.site, db: Object.assign({ events: { items: [] } }, weekly ? { weekly_open: { items: weekly } } : {}) });
const res = { cases: {}, files: {} };
for (const [name, c] of Object.entries(input.cases)) {
  if (c.empty) process.env.COMMITTEE_EMPTY = "1";
  try { res.cases[name] = { en: render("en", c.weekly), es: render("es", c.weekly) }; }
  finally { delete process.env.COMMITTEE_EMPTY; }
}
const full = { db: { weekly_open: { items: input.weekly } }, site: input.site, languages: ["en", "es"] };
for (const f of W.data.pagination.before(["en", "es"], full)) res.files[W.data.permalink({ file: f })] = W.render(Object.assign({ file: f }, full));
out(res);
"""
CASES = {"weekly": {"weekly": WEEKLY}, "none": {"weekly": None}, "empty": {"weekly": WEEKLY, "empty": True},
         "dateless": {"weekly": [{**weekly_item(False), "extra": {k: v for k, v in weekly_item(False)["extra"].items()
                                                                   if k != "next_start"}},
                                 {**weekly_item(True), "status": "gone"}]}}
RUNS: dict[str, dict] = {}


def feeds(case: unittest.TestCase, now: str = NOV19) -> dict:
    if now not in RUNS:
        RUNS[now] = run_js(case, FEEDS_JS, data={"site": SITE, "cases": CASES, "weekly": WEEKLY}, now=now)
    return RUNS[now]


def unfold(text: str) -> list[str]:
    return text.replace("\r\n ", "").split("\r\n")


def blocks(text: str, name: str = "VEVENT") -> list[list[str]]:
    """Each component's own lines (unfolded), BEGIN/END left out."""
    out, cur, depth = [], None, 0
    for line in unfold(text):
        if line == f"BEGIN:{name}" and cur is None:
            cur, depth = [], 0
        elif cur is not None and line == f"END:{name}" and depth == 0:
            out.append(cur)
            cur = None
        elif cur is not None:
            depth += line.startswith("BEGIN:") - line.startswith("END:")
            cur.append(line)
    return out


def field(lines: list[str], key: str) -> list[str]:
    return [ln.split(":", 1)[1] for ln in lines if ln.split(":", 1)[0].split(";")[0] == key]


def weekly_events(text: str) -> dict[str, list[str]]:
    """The weekly entries of a feed: UID → its lines."""
    return {field(b, "UID")[0]: b for b in blocks(text) if field(b, "UID")[0].startswith("weekly-open")}


def ics_text(s: str) -> str:
    return s.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


class BothFeedsHaveBothMeetings(unittest.TestCase):
    def test_one_repeating_entry_each_on_its_day_in_its_own_zone(self):
        r = feeds(self)["cases"]["weekly"]
        want = {"en": {"weekly-open@neta65-gvlv": ("WE", "20260923T120000", "20260923T130000"),
                       "weekly-open-lv@neta65-gvlv": ("TH", "20261105T120000", "20261105T130000")},
                "es": {"weekly-open-es@neta65-gvlv": ("WE", "20260923T120000", "20260923T130000"),
                       "weekly-open-lv-es@neta65-gvlv": ("TH", "20261105T120000", "20261105T130000")}}
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                text = r[lang]
                evs = weekly_events(text)
                self.assertEqual(sorted(evs), sorted(want[lang]))
                for uid, (day, start, end) in want[lang].items():
                    ev = evs[uid]
                    self.assertEqual(field(ev, "RRULE"), [f"FREQ=WEEKLY;BYDAY={day}"])
                    self.assertIn(f"DTSTART;TZID=America/New_York:{start}", ev)
                    self.assertIn(f"DTEND;TZID=America/New_York:{end}", ev)
                    self.assertEqual((field(ev, "STATUS"), field(ev, "TRANSP")), (["CONFIRMED"], ["OPAQUE"]))
                    self.assertEqual(field(ev, "SEQUENCE"), field(blocks(text)[-1], "SEQUENCE"), "the feed's SEQUENCE")
                    self.assertEqual(len(field(ev, "DTSTAMP")), 1)
                # the page language's meeting first, as on /events/ (La Viña's on /es/), before the dated events
                uids = [field(b, "UID")[0] for b in blocks(text)]
                self.assertEqual(uids[:2], list(want[lang]) if lang == "en" else list(want[lang])[::-1])
                self.assertTrue(all(u.startswith("ev-") for u in uids[2:]) and len(uids) > 2, "the dated events follow")
                # the zone's VTIMEZONE, once, before every VEVENT; the site's own zone stays the calendar's default
                lines = unfold(text)
                self.assertEqual(lines.count("TZID:America/New_York"), 1)
                self.assertLess(lines.index("END:VTIMEZONE"), lines.index("BEGIN:VEVENT"))
                self.assertIn("X-WR-TIMEZONE:America/Chicago", lines)
                self.assertNotIn("TZID:America/Chicago", lines, "a calendar with components needs no fallback zone")
                for line in text.split("\r\n"):
                    self.assertLessEqual(len(line.encode("utf-8")), 75)
                self.assertTrue(text.endswith("END:VCALENDAR\r\n"))

    def test_every_meeting_is_at_11_central_across_the_clock_changes(self):
        from icalendar import Calendar
        for lang in ("en", "es"):
            cal = Calendar.from_ical(feeds(self)["cases"]["weekly"][lang])
            self.assertEqual([e for c in cal.walk() for e in (getattr(c, "errors", None) or [])], [])
            (vtz,) = cal.walk("VTIMEZONE")
            own = vtz.to_tz(lookup_tzid=False)          # the feed's own rules, not the zone database's
            for ev in cal.walk("VEVENT"):
                uid = str(ev["UID"])
                if not uid.startswith("weekly-open"):
                    continue
                start, end = ev["DTSTART"].dt, ev["DTEND"].dt
                self.assertEqual(str(ev["DTSTART"].params["TZID"]), "America/New_York")
                self.assertEqual(end - start, timedelta(hours=1))
                self.assertEqual(not ev.subcomponents, True, "no VALARM")
                wall = start.replace(tzinfo=None)
                weekday = wall.weekday()
                seen = set()
                # by hand: the same wall-clock time every 7 days, from the first meeting through 2027
                for k in range(0, 80):
                    local = wall + timedelta(weeks=k)
                    if local.year > 2027:
                        break
                    for tz in (own, NY):
                        at = local.replace(tzinfo=tz).astimezone(CHI)
                        with self.subTest(lang=lang, uid=uid, day=local.date().isoformat()):
                            self.assertEqual((at.hour, at.minute, at.weekday()), (11, 0, weekday))
                    seen.add(local.date().isoformat())
                # the weeks on both sides of the two changes are there
                near = {"WE": ["2027-03-10", "2027-03-17", "2027-11-03", "2027-11-10"],
                        "TH": ["2027-03-11", "2027-03-18", "2027-11-04", "2027-11-11"]}[ev["RRULE"]["BYDAY"][0]]
                self.assertTrue(set(near) <= seen, uid)
                # and the zone database agrees with the feed's own rules on those days
                for d in near:
                    noon = datetime.fromisoformat(d + "T12:00:00")
                    self.assertEqual(noon.replace(tzinfo=own).utcoffset(), noon.replace(tzinfo=NY).utcoffset(), d)


class TheFirstDateNeverMoves(unittest.TestCase):
    def test_two_builds_weeks_apart_write_the_same_entries(self):
        a, b = feeds(self, NOV19)["cases"]["weekly"], feeds(self, JAN10)["cases"]["weekly"]
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ea, eb = weekly_events(a[lang]), weekly_events(b[lang])
                self.assertEqual(len(ea), 2, "both weekly meetings are there to compare")
                self.assertEqual(sorted(ea), sorted(eb))
                # (their zone too: New York's rules are the same in 2026 and 2027)
                self.assertEqual(blocks(a[lang], "VTIMEZONE"), blocks(b[lang], "VTIMEZONE"))
                for uid in ea:
                    keep = lambda ev: [ln for ln in ev if not ln.startswith(("DTSTAMP:", "SEQUENCE:"))]  # noqa: E731
                    self.assertEqual(keep(ea[uid]), keep(eb[uid]), uid)
                    self.assertGreater(int(field(eb[uid], "SEQUENCE")[0]), int(field(ea[uid], "SEQUENCE")[0]))

    def test_the_one_off_files_still_start_at_the_next_meeting(self):
        files = feeds(self)["files"]
        # Nov 19, noon Central: La Viña's meeting of the day is under way (the cards say "Live now" for 75 minutes)
        self.assertIn("DTSTART;TZID=America/New_York:20261119T120000", unfold(files["/meetings/weekly-open-lv.ics"]))
        self.assertIn("DTSTART;TZID=America/New_York:20261125T120000", unfold(files["/meetings/weekly-open-gv.ics"]))

    def test_where_the_first_date_comes_from(self):
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const now = new Date();
          const one = (it) => C.weeklyFeed([it], input.site, "en", now).map((w) => w.dtstart + " " + w.rrule.slice(-2));
          out({
            starts: one(input.lv),
            seen: one(input.gv),
            // seen on Thursday, 00:30 in New York — still Wednesday evening in Central time: the host's day counts
            hostDay: one(Object.assign({}, input.gv, { first_seen: "2026-09-24T04:30:00Z" })),
            // seen on Wednesday, 10 PM in New York — already Thursday in UTC: the host's day counts, not UTC's
            utcNextDay: one(Object.assign({}, input.gv, { first_seen: "2026-09-24T02:00:00Z" })),
            noSeen: one(Object.assign({}, input.gv, { first_seen: null })),
            laterSeen: one(Object.assign({}, input.gv, { first_seen: "2027-05-01T00:00:00Z" })),
          });""", data={"site": SITE, "gv": weekly_item(False), "lv": weekly_item(True)}, now=NOV19)
        self.assertEqual(r["starts"], ["20261105T120000 TH"])
        self.assertEqual(r["seen"], ["20260923T120000 WE"])
        self.assertEqual(r["hostDay"], ["20260930T120000 WE"])
        self.assertEqual(r["utcNextDay"], ["20260923T120000 WE"], "first_seen read in New York, not in UTC")
        self.assertEqual(r["noSeen"], ["20261125T120000 WE"], "no first_seen: the next date")
        self.assertEqual(r["laterSeen"], ["20261125T120000 WE"], "never after the next date")

    def test_the_zone_rules_are_the_builds_not_the_first_years(self):
        """The first date stays put, but the VTIMEZONE follows the zone data of the build: Mexico City dropped
        daylight time in October 2022, so a series that began in June 2022 must not keep 2022's summer offset."""
        from icalendar import Calendar
        mx = ZoneInfo("America/Mexico_City")
        if datetime(2026, 7, 1, 12, tzinfo=mx).utcoffset() != timedelta(hours=-6):
            self.skipTest("this Python's zone data predates Mexico's 2022 change")
        item = weekly_item(False, timezone="America/Mexico_City", starts="2022-06-01",
                           next_start="2026-11-25T18:00:00Z")
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const now = new Date();
          const off = new Intl.DateTimeFormat("en-US", { timeZone: "America/Mexico_City", timeZoneName: "shortOffset" })
            .format(new Date("2026-07-01T18:00:00Z"));
          out({ knows: off.endsWith("GMT-6"),
                ics: C.buildIcs([], { lang: "en", now, weekly: C.weeklyFeed([input.item], input.site, "en", now) }) });
          """, data={"site": SITE, "item": item}, now=NOV19)
        if not r["knows"]:
            self.skipTest("this Node's zone data predates Mexico's 2022 change")
        self.assertIn("DTSTART;TZID=America/Mexico_City:20220601T120000", unfold(r["ics"]), "the first date stays put")
        (vtz,) = Calendar.from_ical(r["ics"]).walk("VTIMEZONE")
        own = vtz.to_tz(lookup_tzid=False)
        for d in ("2026-07-01", "2027-01-06", "2027-07-07", "2028-04-05"):
            noon = datetime.fromisoformat(d + "T12:00:00")
            self.assertEqual(noon.replace(tzinfo=own).utcoffset(), noon.replace(tzinfo=mx).utcoffset(), d)


class SameUidAsItsOwnFile(unittest.TestCase):
    def test_the_uids_are_the_weekly_files_and_unique(self):
        r = feeds(self)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                pre = "/es" if lang == "es" else ""
                own = {field(blocks(r["files"][f"{pre}/meetings/weekly-open-{k}.ics"])[0], "UID")[0] for k in ("gv", "lv")}
                self.assertEqual(set(weekly_events(r["cases"]["weekly"][lang])), own)
                uids = [field(b, "UID")[0] for b in blocks(r["cases"]["weekly"][lang])]
                self.assertEqual(len(uids), len(set(uids)), "every UID once")
                self.assertTrue(all(u.startswith(("ev-", "weekly-open")) for u in uids))
                # the same words, place and link as the meeting's own file
                for k in ("gv", "lv"):
                    (mine,) = blocks(r["files"][f"{pre}/meetings/weekly-open-{k}.ics"])
                    ev = weekly_events(r["cases"]["weekly"][lang])[field(mine, "UID")[0]]
                    for key in ("SUMMARY", "DESCRIPTION", "LOCATION", "URL", "RRULE"):
                        self.assertEqual(field(ev, key), field(mine, key)[:1], (k, key))

    def test_a_uid_is_never_written_twice(self):
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const now = new Date();
          const w = C.weeklyFeed(input.weekly, input.site, "en", now);
          const clash = { uid: "weekly-open", title: "A dated event", startMs: Date.parse("2026-12-01T18:00:00Z"),
                          endMs: Date.parse("2026-12-01T19:00:00Z"), allDay: false, group: "neta" };
          out({ twice: C.buildIcs([], { lang: "en", now, weekly: [...w, ...w] }), clash: C.buildIcs([clash], { lang: "en", now, weekly: w }) });
          """, data={"site": SITE, "weekly": WEEKLY}, now=NOV19)
        self.assertEqual([field(b, "UID")[0] for b in blocks(r["twice"])], ["weekly-open@neta65-gvlv", "weekly-open-lv@neta65-gvlv"])
        self.assertEqual([field(b, "UID")[0] for b in blocks(r["clash"])], ["weekly-open-lv@neta65-gvlv", "weekly-open@neta65-gvlv"])
        self.assertEqual([field(b, "SUMMARY")[0] for b in blocks(r["clash"])][1], "A dated event")


class NoReminder(unittest.TestCase):
    def test_no_valarm_in_either_feed(self):
        for lang in ("en", "es"):
            text = feeds(self)["cases"]["weekly"][lang]
            self.assertIn("BEGIN:VEVENT", text)
            self.assertNotIn("VALARM", text, "a subscriber would get over a hundred alarms")
        # (the meeting's own file keeps its one reminder)
        self.assertIn("BEGIN:VALARM", feeds(self)["files"]["/meetings/weekly-open-gv.ics"])


class WordsAndLinks(unittest.TestCase):
    def test_each_feed_speaks_its_language(self):
        r = feeds(self)["cases"]["weekly"]
        for lang in ("en", "es"):
            pre = "/es" if lang == "es" else ""
            page = f"{SITE_URL}{pre}/meetings/#weekly-open"
            details = {"en": "Details: ", "es": "Detalles: "}[lang]
            for uid, ev in weekly_events(r[lang]).items():
                with self.subTest(lang=lang, uid=uid):
                    desc = ics_text(field(ev, "DESCRIPTION")[0]).split("\n")
                    self.assertEqual(field(ev, "URL"), [page])
                    self.assertEqual([ln for ln in desc if ln.startswith(details)], [details + page], "Details: its URL")
                    self.assertEqual(ics_text(field(ev, "LOCATION")[0]), ZOOM_URL)
                    self.assertEqual(ics_text(field(ev, "CATEGORIES")[0]), T["committee.events.group.calendar"][lang])
                    join = T["committee.meeting.cal_join"][lang].replace("{platform}", "Zoom")
                    self.assertIn(f"{join}: {ZOOM_URL}", desc)
                    self.assertIn(f"{T['committee.meeting.id'][lang]}: {ZOOM_ID}", desc)
                    self.assertIn(f"{T['committee.meeting.passcode'][lang]}: {PASSCODE}", desc)
                    if "-lv" in uid:
                        self.assertEqual(ics_text(field(ev, "SUMMARY")[0]),
                                         {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"}[lang])
                        self.assertEqual(desc[0], weekly_item(True)["i18n"]["summary"][lang])
                    else:
                        self.assertEqual(ics_text(field(ev, "SUMMARY")[0]), "Grapevine Weekly Open AA Meeting")
                        self.assertEqual(desc[0], T["committee.weekly.gv_text"][lang])
        self.assertIn("Calendario de Grapevine / La Viña", r["es"])
        self.assertIn("Código de acceso", ics_text("".join(unfold(r["es"]))))

    def test_the_link_leads_to_a_section_meetings_has(self):
        page = (ROOT / "src" / "pages" / "meetings.njk").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'\bid="weekly-open"', page)), 1)
        # …and /events/ keeps its "every week" cards, under the GV & LV calendars chip (the feed's CATEGORIES)
        events = (ROOT / "src" / "pages" / "events.njk").read_text(encoding="utf-8")
        self.assertIn('<section id="ev-weekly" class="mb-10" x-show="filter === \'all\' || filter === \'calendar\'"', events)
        self.assertIn('<h3 id="ev-weekly-{{ key }}"', events)

    def test_the_feed_and_the_subscribe_card_say_so(self):
        self.assertIn("weekly open meetings of AA Grapevine and La Viña", T["committee.ics.desc"]["en"])
        self.assertIn("las reuniones abiertas semanales de AA Grapevine y La Viña", T["committee.ics.desc"]["es"])
        self.assertIn("weekly open meeting", T["committee.sub.text"]["en"])
        self.assertIn("reuniones abiertas semanales", T["committee.sub.text"]["es"])
        r = feeds(self)["cases"]["weekly"]
        for lang in ("en", "es"):
            desc = ics_text("".join(field(unfold(r[lang]), "X-WR-CALDESC")))
            self.assertEqual(desc, T["committee.ics.desc"][lang])


class NoWeeklyEntry(unittest.TestCase):
    def test_no_data_no_date_gone_or_committee_empty(self):
        r = feeds(self)["cases"]
        for case in ("none", "empty", "dateless"):
            for lang in ("en", "es"):
                with self.subTest(case=case, lang=lang):
                    text = r[case][lang]
                    self.assertEqual(weekly_events(text), {})
                    self.assertNotIn("America/New_York", text)
                    self.assertIn("BEGIN:VEVENT", text, "the committee meetings are still there")
                    self.assertNotIn("TZID:America/Chicago", text)

    def test_an_empty_calendar_stays_valid(self):
        from icalendar import Calendar
        r = run_js(self, r"""
          const C = await imp("eleventy/filters/committee.js");
          const now = new Date();
          out({ nothing: C.buildIcs([], { lang: "en", now, weekly: [] }),
                bare: C.buildIcs([], { lang: "en", now }),
                weeklyOnly: C.buildIcs([], { lang: "es", now, weekly: C.weeklyFeed(input.weekly, input.site, "es", now) }),
                gone: C.weeklyFeed(input.weekly.map((it) => Object.assign({}, it, { status: "gone" })), input.site, "en", now),
                wrongKind: C.weeklyFeed(input.weekly.map((it) => Object.assign({}, it, { kind: "event" })), input.site, "en", now) });
          """, data={"site": SITE, "weekly": WEEKLY}, now=NOV19)
        for k in ("nothing", "bare"):
            self.assertEqual(blocks(r[k]), [])
            self.assertEqual([field(b, "TZID") for b in blocks(r[k], "VTIMEZONE")], [["America/Chicago"]], k)
            Calendar.from_ical(r[k])
        self.assertEqual([field(b, "TZID") for b in blocks(r["weeklyOnly"], "VTIMEZONE")], [["America/New_York"]],
                         "a calendar with the weekly meetings only: their zone, no fallback")
        self.assertEqual(len(blocks(r["weeklyOnly"])), 2)
        self.assertEqual((r["gone"], r["wrongKind"]), ([], []))


if __name__ == "__main__":
    unittest.main()
