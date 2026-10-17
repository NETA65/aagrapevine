"""Round 12 · calendar: the story deadlines calendar (/deadlines.ics, /es/deadlines.ics) and the ONE reminder every
"Add to calendar" file of the site carries.

  * the reminder itself (central-time.js icsAlarm / alarmText — the build's and the browser's one helper): an hour
    before a timed event, 9 AM the day before an all-day one; its words are the title alone, never a link, a meeting
    ID or a passcode (Alarm);
  * the deadlines calendar (eleventy/filters/monthly.js deadlinesIcs, src/pages/deadlines-ics.11ty.js): every open
    deadline of both magazines and nothing else (no passed, dropped or undated theme), the month files' UIDs, valid
    RFC 5545 (CRLF, lines folded at 75 octets, TEXT escaped, one VALARM per entry), a moved deadline keeps its UID with
    a higher SEQUENCE; /contribute/'s "Add to my calendar" data says the same (DeadlinesCalendar);
  * where the reminder is and is not: the month files and the weekly open meetings' files have it, the big
    /events.ics feeds do not (a subscriber would get ninety alarms); the browser's downloads (app.js GV.icsText,
    /contribute/'s button through read.js) have it, with the Zoom passcode only in the description (Files, Browser);
  * the pages: the card under the deadlines on /contribute/ (committee.js cmSubscribe "deadlines"), the links from
    Home and What's New, the reminder line in every "Add to calendar" menu (Pages).

Every test runs on a fixed clock (run_js now=…): what is "open" never depends on the day the tests run.

    python -m unittest tests.test_r12_u3_calendar -v
"""
from __future__ import annotations

import re
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_central_time import DOM, WEEKLY, SITE as WEEKLY_SITE  # noqa: E402
from test_monthly import CARRY, SITE as MONTH_SITE, full_db  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-15T15:00:00Z"            # Thursday, October 15, 2026, 10 AM in Texas
LATER = "2026-10-15T16:00:00Z"
SITE = {"url": "https://example.org/site"}
PASSCODE = "238047"


def unfold(text: str) -> list[str]:
    return text.replace("\r\n ", "").split("\r\n")


def components(text: str, name: str) -> list[dict]:
    """Each BEGIN:<name> … END:<name> block's lines as {property (with its parameters): value}; for a VEVENT also
    "alarms": its VALARM blocks the same way (they never overwrite the event's own DESCRIPTION)."""
    out, cur, alarm = [], None, None
    for line in unfold(text):
        if line == f"BEGIN:{name}":
            cur = {"alarms": []}
        elif line == f"END:{name}" and cur is not None:
            out.append(cur)
            cur = None
        elif cur is not None and line == "BEGIN:VALARM":
            alarm = {}
        elif cur is not None and line == "END:VALARM":
            cur["alarms"].append(alarm)
            alarm = None
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            (alarm if alarm is not None else cur)[k] = v
    return out


def editorial(item_id: str, pub: str, title: str, deadline: str | None, issue: str | None = None, **kw) -> dict:
    extra = {"publication": pub, **({"deadline": deadline} if deadline else {}), **({"issue_key": issue} if issue else {}),
             **kw.pop("extra", {})}
    return {"id": item_id, "source": "grapevine" if pub == "gv" else "lavina", "kind": "theme", "title": title,
            "lang": "en" if pub == "gv" else "es", "status": kw.pop("status", "ok"), "extra": extra, **kw}


ED = [
    editorial("ed:gv:2027-05:fun-in-sobriety", "gv", "Fun in Sobriety", "2026-10-01", "2027-05"),          # passed
    editorial("ed:gv:2027-06:emotional-sobriety", "gv", "Emotional Sobriety", "2026-11-01", "2027-06",
              i18n={"title": {"en": "Emotional Sobriety", "es": "Sobriedad emocional"}}, machine=["es"]),
    editorial("ed:gv:2027-04:today", "gv", "Due Today", "2026-10-15", "2027-04"),                         # open all day
    editorial("ed:gv:2027-07:gone", "gv", "Dropped Theme", "2026-12-01", "2027-07", status="gone"),
    editorial("ed:gv:2027-08:long", "gv", "Sober Seniors; Young & Old, Together — Stories From Every Generation "
              "Of The Fellowship, Near And Far", "2027-01-01", "2027-08"),
    editorial("ed:gv:2027-09:zoom", "gv", "Online Groups (Zoom ID 871 2036 8287, passcode 238047) https://zoom.us/j/87120368287",
              "2027-02-01", "2027-09"),
    editorial("ed:lv:2027-05:recaidas", "lv", "Recaídas", "2026-10-17", "2027-05",
              i18n={"title": {"es": "Recaídas", "en": "Relapses"}}, machine=["en"]),
    editorial("ed:lv:topic:gratitud", "lv", "Gratitud", None, extra={"evergreen": True}),                   # no date
    editorial("ed:lv:undated-issue", "lv", "Sin edición", "2026-12-15"),                                    # no issue_key
]

FEED_JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const P = await imp("src/pages/deadlines-ics.11ty.js");
const db = { editorial: { items: input.items } };
const now = new Date();
const res = { now: now.toISOString(), feeds: {}, pages: {}, paths: {}, cals: {} };
for (const lang of ["en", "es"]) {
  res.feeds[lang] = M.deadlinesIcs(db, input.site, lang, now);
  res.pages[lang] = P.render({ db, site: input.site, lang });
  res.paths[lang] = P.data.permalink({ lang });
  res.cals[lang] = filters.mpDeadlineCals(db, input.site, lang);
  const m = M.monthModel("2026-10", db, {}, input.site, lang, now);
  res["month_" + lang] = M.monthIcs(m, db, input.site, lang, now);
}
res.excluded = P.data.eleventyExcludeFromCollections === true && P.data.layout === null;
res.pagination = P.data.pagination;
if (input.moved) {
  const moved = input.items.map((i) => (i.id === input.moved ? Object.assign({}, i, { extra: Object.assign({}, i.extra, { deadline: "2026-11-08" }) }) : i));
  res.movedFeed = M.deadlinesIcs({ editorial: { items: moved } }, input.site, "en", new Date(Date.parse(input.later)));
}
res.empty = M.deadlinesIcs({}, input.site, "en", now);
out(res);
"""


class Alarm(unittest.TestCase):
    """central-time.js icsAlarm / alarmText: the reminder's lines and words."""

    TITLES = [
        "NETA 65 Grapevine / La Viña Committee Meeting",
        "Weekly Open — Zoom https://zoom.us/j/87120368287 Passcode: 238047",
        "Reunión ID: 871 2036 8287 código de acceso 238047",
        "Workshop (Zoom ID 871-2036-8287)",
        "Meeting (Zoom, passcode 238047)",
        "us02web.zoom.us/j/1234567890 pwd=abc123",
        "Taller; Q&A, abierto",
        "Back\\slash",
        "Line\nbreak",
        "",
        # the value goes with its word — small words between them ("de Zoom", "is", ":") — and an ID after "de Zoom" too
        "Taller (Contraseña de Zoom: 238047)",
        "Zoom passcode is 238047",
        "Reunión en Zoom — ID de Zoom: 871 2036 8287, clave 238047",
        "ID de la reunión: 871 2036 8287; contraseña: 238047",
        "Zoom meeting ID: 87120368287 (Passcode: Ab3xYz)",
        # the same words with no code after them are ordinary words: a theme quoted exactly keeps them
        "Conceptos clave del servicio",
        "La honestidad, clave de la sobriedad",
        "Código de conducta del grupo",
        "Fecha límite: “La clave de mi recuperación” — La Viña",
        "Fecha límite: “El código de la calle” — La Viña",
        "Taller: la contraseña del corazón",
        "The password is love",
        "La clave de 1935",
        "La clave de 12 pasos",
    ]

    _r = None

    def setUp(self):
        if Alarm._r is None:
            Alarm._r = run_js(self, r"""
              const T = await imp("eleventy/central-time.js");
              out({ text: input.map((t) => T.alarmText(t)), timed: input.map((t) => T.icsAlarm(t, false)), day: T.icsAlarm("Deadline", true) });""",
                              data=self.TITLES, needs_modules=False, now=NOW)
        self.r = Alarm._r

    def test_the_lines(self):
        self.assertEqual(self.r["timed"][0], ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:NETA 65 Grapevine / La Viña Committee Meeting",
                                              "TRIGGER:-PT1H", "END:VALARM"])
        # an all-day entry: 15 hours before the start of its day = 9 AM the day before, in the calendar's own zone
        self.assertEqual(self.r["day"], ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Deadline", "TRIGGER:-PT15H", "END:VALARM"])

    def test_never_a_link_a_meeting_id_or_a_passcode(self):
        text = dict(zip(self.TITLES, self.r["text"]))
        self.assertEqual(text["Weekly Open — Zoom https://zoom.us/j/87120368287 Passcode: 238047"], "Weekly Open — Zoom")
        self.assertEqual(text["Reunión ID: 871 2036 8287 código de acceso 238047"], "Reunión")
        self.assertEqual(text["Workshop (Zoom ID 871-2036-8287)"], "Workshop (Zoom)")
        self.assertEqual(text["Meeting (Zoom, passcode 238047)"], "Meeting (Zoom)")
        self.assertEqual(text["us02web.zoom.us/j/1234567890 pwd=abc123"], "NETA 65", "nothing left: the committee's name")
        self.assertEqual(text[""], "NETA 65")
        for t in self.r["text"]:
            self.assertNotRegex(t, r"https?:|zoom\.us|238047|8287|abc123|Ab3xYz|\n")

    def test_the_word_and_its_value_go_together(self):
        text = dict(zip(self.TITLES, self.r["text"]))
        self.assertEqual(text["Taller (Contraseña de Zoom: 238047)"], "Taller")
        self.assertEqual(text["Zoom passcode is 238047"], "Zoom")
        self.assertEqual(text["Reunión en Zoom — ID de Zoom: 871 2036 8287, clave 238047"], "Reunión en Zoom")
        self.assertEqual(text["ID de la reunión: 871 2036 8287; contraseña: 238047"], "NETA 65")
        self.assertEqual(text["Zoom meeting ID: 87120368287 (Passcode: Ab3xYz)"], "Zoom")

    def test_ordinary_words_stay(self):
        """"clave", "código", "contraseña", "password" with no code after them: the title as it is (a La Viña theme is
        quoted exactly — "Conceptos clave del servicio" never becomes "Conceptos servicio")."""
        text = dict(zip(self.TITLES, self.r["text"]))
        for title in ("Conceptos clave del servicio", "La honestidad, clave de la sobriedad", "Código de conducta del grupo",
                      "Fecha límite: “La clave de mi recuperación” — La Viña", "Fecha límite: “El código de la calle” — La Viña",
                      "Taller: la contraseña del corazón", "The password is love", "La clave de 1935", "La clave de 12 pasos"):
            with self.subTest(title=title):
                self.assertEqual(text[title], title)

    def test_text_escaping(self):
        desc = {t: lines[2] for t, lines in zip(self.TITLES, self.r["timed"])}
        self.assertEqual(desc["Taller; Q&A, abierto"], "DESCRIPTION:Taller\\; Q&A\\, abierto")
        self.assertEqual(desc["Back\\slash"], "DESCRIPTION:Back\\\\slash")
        self.assertEqual(desc["Line\nbreak"], "DESCRIPTION:Line break", "one line: no break is left in it")


class DeadlinesCalendar(unittest.TestCase):
    _r = None

    def setUp(self):
        if DeadlinesCalendar._r is None:
            DeadlinesCalendar._r = run_js(self, FEED_JS, data={"items": ED, "site": SITE, "moved": "ed:gv:2027-06:emotional-sobriety",
                                                               "later": LATER}, now=NOW)
        self.r = DeadlinesCalendar._r

    def uids(self, text: str) -> list[str]:
        return [e["UID"] for e in components(text, "VEVENT")]

    def test_the_clock_is_the_tests(self):
        self.assertEqual(self.r["now"], "2026-10-15T15:00:00.000Z")

    def test_where_the_files_are(self):
        self.assertEqual(self.r["paths"], {"en": "/deadlines.ics", "es": "/es/deadlines.ics"})
        self.assertTrue(self.r["excluded"], "not a page: out of the collections (the sitemap, the feeds, the search)")
        self.assertEqual(self.r["pagination"], {"data": "languages", "size": 1, "alias": "lang"})
        strip = lambda s: re.sub(r"DTSTAMP:\d+T\d+Z", "", s)
        for lang in ("en", "es"):
            self.assertEqual(strip(self.r["pages"][lang]), strip(self.r["feeds"][lang]), "the page writes deadlinesIcs on the build's clock")

    def test_every_open_deadline_and_nothing_else(self):
        self.assertEqual(self.uids(self.r["feeds"]["en"]), [
            "deadline-ed-gv-2027-04-today@neta65-gvlv",              # due today: open through its day
            "deadline-ed-lv-2027-05-recaidas@neta65-gvlv",
            "deadline-ed-gv-2027-06-emotional-sobriety@neta65-gvlv",
            "deadline-ed-gv-2027-08-long@neta65-gvlv",
            "deadline-ed-gv-2027-09-zoom@neta65-gvlv",
        ])
        # passed (Oct 1), dropped by the magazine (gone), La Viña's undated topics and a date without its issue: never
        self.assertNotIn("fun-in-sobriety", self.r["feeds"]["en"])
        self.assertNotIn("Dropped Theme", self.r["feeds"]["en"])
        self.assertNotIn("Gratitud", self.r["feeds"]["en"])
        self.assertNotIn("Sin edición", self.r["feeds"]["en"])
        self.assertEqual(self.uids(self.r["feeds"]["es"]), [u.replace("@", "-es@") for u in self.uids(self.r["feeds"]["en"])])
        empty = unfold(self.r["empty"])
        self.assertEqual((empty[0], empty[-2], empty.count("BEGIN:VEVENT")), ("BEGIN:VCALENDAR", "END:VCALENDAR", 0),
                         "no deadline open: a calendar with no entry")

    def test_with_no_deadline_open_the_calendar_still_has_a_component(self):
        """RFC 5545 §3.6: icalbody = calprops component, component = 1*(…) — a VCALENDAR with nothing in it is not
        valid. With no entry, the site's zone (the X-WR-TIMEZONE it names) as a VTIMEZONE."""
        from icalendar import Calendar
        empty = unfold(self.r["empty"])
        self.assertIn("BEGIN:VTIMEZONE", empty)
        self.assertIn("TZID:America/Chicago", empty)
        self.assertLess(empty.index("END:VTIMEZONE"), empty.index("END:VCALENDAR"))
        self.assertTrue(empty[empty.index("BEGIN:VTIMEZONE") - 1].startswith("X-PUBLISHED-TTL:"), "after the calendar's own lines")
        cal = Calendar.from_ical(self.r["empty"])
        self.assertEqual([c.name for c in cal.subcomponents], ["VTIMEZONE"])
        self.assertEqual([e for c in cal.walk() for e in (getattr(c, "errors", None) or [])], [])
        for line in self.r["empty"].split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        # a calendar with entries is as it was: no zone it does not use (its times are UTC and all-day dates)
        self.assertNotIn("BEGIN:VTIMEZONE", self.r["feeds"]["en"])

    def test_valid_rfc5545(self):
        for lang in ("en", "es"):
            text = self.r["feeds"][lang]
            with self.subTest(lang=lang):
                self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n") and text.endswith("END:VCALENDAR\r\n"))
                self.assertNotIn("\n", text.replace("\r\n", ""), "CRLF line ends only")
                self.assertNotIn("\r", text.replace("\r\n", ""))
                for line in text.split("\r\n"):
                    self.assertLessEqual(len(line.encode("utf-8")), 75, line)
                self.assertTrue(any(line.startswith(" ") for line in text.split("\r\n")), "long lines are folded")
                lines = unfold(text)
                self.assertEqual(lines.count("BEGIN:VEVENT"), lines.count("END:VEVENT"))
                self.assertEqual(lines.count("BEGIN:VALARM"), lines.count("BEGIN:VEVENT"), "one reminder per deadline")
                self.assertIn("REFRESH-INTERVAL;VALUE=DURATION:PT12H", lines)
                for ev in components(text, "VEVENT"):
                    self.assertTrue(ev["DTSTAMP"] and int(ev["SEQUENCE"]) > 0)
                    self.assertEqual(ev["TRANSP"], "TRANSPARENT")
                    start = datetime.strptime(ev["DTSTART;VALUE=DATE"], "%Y%m%d")
                    self.assertEqual(datetime.strptime(ev["DTEND;VALUE=DATE"], "%Y%m%d") - start, timedelta(days=1),
                                     "an all-day entry on its day (DTEND: the day after)")
        long = next(e for e in components(self.r["feeds"]["en"], "VEVENT") if e["UID"].startswith("deadline-ed-gv-2027-08"))
        self.assertIn("Sober Seniors\\; Young & Old\\, Together", long["SUMMARY"], "TEXT escaped")

    def test_icalendar_reads_it(self):
        from icalendar import Calendar
        for lang in ("en", "es"):
            cal = Calendar.from_ical(self.r["feeds"][lang])
            self.assertEqual([e for c in cal.walk() for e in (getattr(c, "errors", None) or [])], [], lang)
            events = list(cal.walk("VEVENT"))
            self.assertEqual(len(events), 5)
            for ev in events:
                alarms = [c for c in ev.subcomponents if c.name == "VALARM"]
                self.assertEqual(len(alarms), 1)
                self.assertEqual(str(alarms[0]["ACTION"]), "DISPLAY")
                self.assertEqual(alarms[0]["TRIGGER"].dt.total_seconds(), -15 * 3600, "9 AM the day before")
                if "Online Groups" not in str(ev["SUMMARY"]):
                    self.assertEqual(str(alarms[0]["DESCRIPTION"]), str(ev["SUMMARY"]), "the title")

    def test_the_words(self):
        en = {e["UID"]: e for e in components(self.r["feeds"]["en"], "VEVENT")}
        es = {e["UID"]: e for e in components(self.r["feeds"]["es"], "VEVENT")}
        lv = en["deadline-ed-lv-2027-05-recaidas@neta65-gvlv"]
        self.assertEqual(lv["SUMMARY"], "Story deadline: “Recaídas” — La Viña (in Spanish)", "La Viña's own Spanish words")
        self.assertIn("https://example.org/site/contribute/#deadlines", lv["DESCRIPTION"])
        self.assertEqual(lv["CATEGORIES"], "Story deadlines")
        self.assertEqual(es["deadline-ed-gv-2027-06-emotional-sobriety-es@neta65-gvlv"]["SUMMARY"],
                         "Fecha límite para historias: “Sobriedad emocional / Emotional Sobriety” — Grapevine (en inglés)",
                         "a machine-translated theme keeps Grapevine's own words beside it")
        self.assertIn("https://example.org/site/es/contribute/#deadlines", es["deadline-ed-lv-2027-05-recaidas-es@neta65-gvlv"]["DESCRIPTION"])
        cal = unfold(self.r["feeds"]["en"])
        self.assertIn("X-WR-CALNAME:NETA 65 Grapevine & La Viña — Story deadlines", cal)
        self.assertIn("X-WR-CALNAME:La Viña y Grapevine de NETA 65 — Fechas límite para historias", unfold(self.r["feeds"]["es"]))
        self.assertIn("URL:https://example.org/site/contribute/#deadlines", cal)

    def test_the_reminder_never_carries_a_link_or_a_passcode(self):
        for lang in ("en", "es"):
            for ev in components(self.r["feeds"][lang], "VEVENT"):
                with self.subTest(lang=lang, uid=ev["UID"]):
                    self.assertEqual(len(ev["alarms"]), 1)
                    a = ev["alarms"][0]
                    self.assertEqual((a["ACTION"], a["TRIGGER"]), ("DISPLAY", "-PT15H"))
                    self.assertNotRegex(a["DESCRIPTION"], r"https?:|zoom\.us|238047|8287")
        zoom = next(e for e in components(self.r["feeds"]["en"], "VEVENT") if "zoom" in e["UID"])
        self.assertIn(PASSCODE, zoom["SUMMARY"], "the theme's own title is left as the magazine wrote it")
        self.assertEqual(zoom["alarms"][0]["DESCRIPTION"], "Story deadline: “Online Groups (Zoom)” — Grapevine")

    def test_the_same_uids_as_the_month_files(self):
        for lang in ("en", "es"):
            month = {e["UID"]: e for e in components(self.r["month_" + lang], "VEVENT") if e["UID"].startswith("deadline-")}
            feed = {e["UID"]: e for e in components(self.r["feeds"][lang], "VEVENT")}
            with self.subTest(lang=lang):
                self.assertTrue(month, "October's file has its deadlines")
                self.assertLessEqual(set(month), set(feed))
                for uid, ev in month.items():
                    for k in ("SUMMARY", "DESCRIPTION", "DTSTART;VALUE=DATE", "DTEND;VALUE=DATE"):
                        self.assertEqual(ev[k], feed[uid][k], (uid, k))
                    self.assertEqual(ev["alarms"], feed[uid]["alarms"], "the same reminder")

    def test_a_moved_deadline_moves(self):
        before = {e["UID"]: e for e in components(self.r["feeds"]["en"], "VEVENT")}
        after = {e["UID"]: e for e in components(self.r["movedFeed"], "VEVENT")}
        uid = "deadline-ed-gv-2027-06-emotional-sobriety@neta65-gvlv"
        self.assertEqual((before[uid]["DTSTART;VALUE=DATE"], after[uid]["DTSTART;VALUE=DATE"]), ("20261101", "20261108"))
        self.assertGreater(int(after[uid]["SEQUENCE"]), int(before[uid]["SEQUENCE"]), "a calendar app takes the newer one")

    def test_contributes_add_to_my_calendar_says_the_same(self):
        for lang in ("en", "es"):
            cals, feed = self.r["cals"][lang], {e["UID"]: e for e in components(self.r["feeds"][lang], "VEVENT")}
            with self.subTest(lang=lang):
                self.assertEqual(sorted(cals), sorted(["ed:gv:2027-04:today", "ed:lv:2027-05:recaidas", "ed:gv:2027-06:emotional-sobriety",
                                                       "ed:gv:2027-08:long", "ed:gv:2027-09:zoom"]))
                for item_id, c in cals.items():
                    ics = c["ics"]
                    self.assertIn(ics["uid"], feed)
                    self.assertEqual(ics["title"].replace(";", "\\;").replace(",", "\\,"), feed[ics["uid"]]["SUMMARY"])
                    self.assertEqual((ics["start"], ics["end"], ics["allDay"]), (ics["start"], ics["start"], True), "one day, the last day")
                    self.assertTrue(c["gcal"].startswith("https://calendar.google.com/calendar/render?action=TEMPLATE&"))
                    self.assertTrue(c["outlook"].startswith("https://outlook.live.com/calendar/0/action/compose?"))
                    self.assertIn("allday=true", c["outlook"])
        g = self.r["cals"]["en"]["ed:gv:2027-06:emotional-sobriety"]["gcal"]
        self.assertIn("dates=20261101%2F20261102", g)


class Files(unittest.TestCase):
    """Where the reminder is: the month files and the weekly open meetings' files; not the /events.ics feeds."""

    _r = None

    def setUp(self):
        if Files._r is None:
            Files._r = run_js(self, r"""
              const M = await imp("eleventy/filters/monthly.js");
              const C = await imp("eleventy/filters/committee.js");
              const E = await imp("src/pages/events-ics.11ty.js");
              const W = await imp("src/pages/meetings-weekly-ics.11ty.js");
              const now = new Date();
              const db = input.db, site = input.site;
              const m = M.monthModel("2026-10", db, input.carry, site, "en", now);
              const full = { db: { weekly_open: { items: input.weekly } }, site: input.wsite, languages: ["en", "es"] };
              const weekly = {};
              for (const f of W.data.pagination.before(["en", "es"], full)) weekly[W.data.permalink({ file: f })] = W.render(Object.assign({ file: f }, full));
              out({ month: M.monthIcs(m, db, site, "en", now),
                    events: E.render({ lang: "en", site, db }),
                    eventsEs: E.render({ lang: "es", site, db }),
                    weekly });""",
                              data={"db": full_db(), "site": MONTH_SITE, "carry": CARRY, "weekly": WEEKLY, "wsite": WEEKLY_SITE}, now=NOW)
        self.r = Files._r

    def test_the_month_file_has_one_reminder_per_entry(self):
        evs = components(self.r["month"], "VEVENT")
        self.assertTrue(evs)
        for ev in evs:
            with self.subTest(uid=ev["UID"]):
                self.assertEqual(len(ev["alarms"]), 1)
                timed = "DTSTART" in ev
                self.assertEqual(ev["alarms"][0]["TRIGGER"], "-PT1H" if timed else "-PT15H")
                self.assertEqual(ev["alarms"][0]["ACTION"], "DISPLAY")
                self.assertNotRegex(ev["alarms"][0]["DESCRIPTION"], r"https?:|zoom\.us")
        committee = next(e for e in evs if e["UID"].startswith("ev-committee-"))
        self.assertEqual(committee["alarms"][0]["TRIGGER"], "-PT1H", "the committee meeting: an hour before")
        self.assertTrue(any(e["UID"].startswith("deadline-") and e["alarms"][0]["TRIGGER"] == "-PT15H" for e in evs),
                        "a story deadline: 9 AM the day before")
        for line in self.r["month"].split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_the_events_feeds_have_none(self):
        for k in ("events", "eventsEs"):
            self.assertIn("BEGIN:VEVENT", self.r[k])
            self.assertNotIn("VALARM", self.r[k], "a subscriber would get ninety alarms")

    def test_the_weekly_open_files(self):
        self.assertEqual(len(self.r["weekly"]), 4)
        for path, text in self.r["weekly"].items():
            with self.subTest(path=path):
                (ev,) = components(text, "VEVENT")
                self.assertEqual(len(ev["alarms"]), 1)
                a = ev["alarms"][0]
                self.assertEqual((a["ACTION"], a["TRIGGER"]), ("DISPLAY", "-PT1H"), "an hour before each meeting")
                self.assertEqual(a["DESCRIPTION"], ev["SUMMARY"])
                self.assertNotIn(PASSCODE, a["DESCRIPTION"])
                self.assertIn(PASSCODE, ev["DESCRIPTION"], "the passcode stays in the description, as before")
                for line in text.split("\r\n"):
                    self.assertLessEqual(len(line.encode("utf-8")), 75)
                lines = unfold(text)
                # the alarm is inside the event, after its own lines
                self.assertLess(lines.index("BEGIN:VALARM"), lines.index("END:VEVENT"))
                self.assertGreater(lines.index("BEGIN:VALARM"), lines.index("BEGIN:VEVENT"))


class Browser(unittest.TestCase):
    """app.js GV.icsText (every "Add to calendar → .ics file" download) and /contribute/'s button (read.js)."""

    _r = None

    def setUp(self):
        if Browser._r is None:
            Browser._r = run_js(self, DOM + r"""
              const p = page([], { files: ["time", "src/assets/js/app.js"] });
              const timed = { uid: "ev-x@neta65-gvlv", title: "Workshop", start: "2026-10-24T15:00:00Z", end: "2026-10-24T17:00:00Z",
                              description: "Join on Zoom: https://zoom.us/j/87120368287\nPasscode: 238047", location: "https://zoom.us/j/87120368287" };
              const day = { uid: "deadline-x@neta65-gvlv", title: "Story deadline: “Recaídas” — La Viña", start: "2026-10-17", end: "2026-10-17", allDay: true };
              const bare = page([], { files: ["src/assets/js/app.js"] }).win.GV.icsText(timed);    // without central-time.js
              // /contribute/: the deadline's "Add to my calendar" → its .ics button (read.js binds it on itself)
              const btn = el("button", { "data-dl-ics": JSON.stringify(day) });
              const menu = el("details", { class: "cm-menu ct-dl-cal", open: "" }, [el("summary"), el("div", { class: "cm-menu-panel" }, [btn])]);
              const q = page([menu], { files: ["time", "src/assets/js/app.js", "src/assets/js/read.js"] });
              q.ready();
              btn.click();
              const ordinary = p.win.GV.icsText(Object.assign({}, timed, { title: "Conceptos clave del servicio (contraseña de Zoom: 238047)" }));
              out({ timed: p.win.GV.icsText(timed), day: p.win.GV.icsText(day), bare, ordinary,
                    downloads: q.downloads.map((d) => d.text), menuOpen: menu.hasAttribute("open") });""", now=NOW)
        self.r = Browser._r

    def test_a_timed_event(self):
        (ev,) = components(self.r["timed"], "VEVENT")
        self.assertEqual(ev["alarms"], [{"ACTION": "DISPLAY", "DESCRIPTION": "Workshop", "TRIGGER": "-PT1H"}])
        self.assertIn(PASSCODE, ev["DESCRIPTION"], "the description keeps the Zoom details")
        for line in self.r["timed"].split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        self.assertTrue(self.r["timed"].endswith("END:VALARM\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"))

    def test_the_browsers_copy_strips_the_value_and_keeps_the_words(self):
        (ev,) = components(self.r["ordinary"], "VEVENT")
        self.assertEqual(ev["alarms"][0]["DESCRIPTION"], "Conceptos clave del servicio", "/assets/js/central-time.js: the same rule")

    def test_an_all_day_entry(self):
        (ev,) = components(self.r["day"], "VEVENT")
        self.assertEqual((ev["DTSTART;VALUE=DATE"], ev["DTEND;VALUE=DATE"]), ("20261017", "20261018"))
        self.assertEqual(ev["alarms"][0]["TRIGGER"], "-PT15H", "9 AM the day before")

    def test_without_central_time_no_reminder(self):
        self.assertNotIn("VALARM", self.r["bare"])
        self.assertIn("BEGIN:VEVENT", self.r["bare"])

    def test_contributes_button_downloads_the_deadline(self):
        self.assertEqual(len(self.r["downloads"]), 1)
        (ev,) = components(self.r["downloads"][0], "VEVENT")
        self.assertEqual(ev["UID"], "deadline-x@neta65-gvlv")
        self.assertEqual(ev["alarms"][0]["TRIGGER"], "-PT15H")
        self.assertFalse(self.r["menuOpen"], "the menu closes once the file is made")


class Pages(unittest.TestCase):
    """The card on /contribute/ and the links to it; the reminder line in each "Add to calendar" menu."""

    _r = None

    def setUp(self):
        if Pages._r is None:
            Pages._r = run_js(self, r"""
              const C = await imp("eleventy/filters/committee.js");
              const sc = {};
              C.default(new Proxy({}, { get(_t, name) { return name === "addShortcode" ? (n, fn) => { sc[n] = fn; } : () => ({ add() {} }); } }));
              const site = input.site;
              out({ events: sc.cmSubscribe("en", site), deadlines: sc.cmSubscribe("en", site, "deadlines"), deadlinesEs: sc.cmSubscribe("es", site, "deadlines") });""",
                               data={"site": SITE}, now=NOW)
        self.r = Pages._r

    @staticmethod
    def read(rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_the_deadlines_card(self):
        d = self.r["deadlines"]
        self.assertIn('id="deadlines-calendar"', d)
        self.assertRegex(d, r"<h3 class=\"card-h mt-2\">.*Get the deadlines in your calendar</h3>")
        self.assertIn('href="webcal://example.org/site/deadlines.ics"', d)
        self.assertIn("https://calendar.google.com/calendar/r?cid=webcal%3A%2F%2Fexample.org%2Fsite%2Fdeadlines.ics", d)
        self.assertIn("addfromweb?url=https%3A%2F%2Fexample.org%2Fsite%2Fdeadlines.ics&amp;name=NETA%2065%20Grapevine%20%26%20La%20Vi%C3%B1a", d)
        self.assertIn('data-copy="https://example.org/site/deadlines.ics"', d)
        self.assertIn('href="https://example.org/site/es/deadlines.ics" hreflang="es"', d)
        self.assertIn("“From URL”", d, "Google Calendar's own steps")
        self.assertIn("Google Calendar ignores the reminders inside calendar files", d)
        self.assertIn("turn off “Remove Alerts”", d)
        self.assertIn("md:grid-cols-3", d)
        es = self.r["deadlinesEs"]
        self.assertIn('href="webcal://example.org/site/es/deadlines.ics"', es)
        self.assertIn("Las fechas límite en tu calendario", es)
        self.assertIn("Google Calendar no usa los avisos", es)

    def test_the_events_card_is_as_it_was(self):
        e = self.r["events"]
        self.assertTrue(e.lstrip().startswith('<div class="card cm-subscribe relative overflow-hidden card-pad">'))
        self.assertIn('<h2 class="card-h mt-2">', e)
        self.assertIn('href="webcal://example.org/site/events.ics"', e)
        self.assertNotIn("Remove Alerts", e)
        self.assertNotIn("deadlines", e)
        self.assertNotIn("md:grid-cols-3", e)

    def test_contribute_wires_the_menu_and_the_card(self):
        page = self.read("src/pages/contribute.njk")
        self.assertIn('{%- set dlCal = db | mpDeadlineCals(site, lang) -%}', page)
        self.assertIn('data-dl-ics="{{ c.ics | json }}" data-js-only', page)
        self.assertIn('{% cmSubscribe lang, site, "deadlines" %}', page)
        self.assertEqual(page.count("{{ dlCalMenu(r, c, lang, isLv"), 2, "each row and the next deadline's card")
        self.assertIn('"committee.cal.reminder_day" | t(lang)', page)
        read_js = self.read("src/assets/js/read.js")
        self.assertIn('document.querySelectorAll("[data-dl-ics]")', read_js)
        css = self.read("src/assets/css/areas/read.css")
        self.assertIn(".read-deadline-row.is-past .ct-dl-cal { display: none; }", css)

    def test_home_and_whats_new_link_it(self):
        self.assertIn("'/contribute/#deadlines-calendar' | lurl(L)", self.read("src/pages/index.njk"))
        wn = self.read("src/pages/whats-new.njk")
        self.assertIn('"/deadlines.ics" | lurl(lang) | siteUrl(site)', wn)
        self.assertIn('href="{{ dlIcs | cmWebcal }}"', wn)

    def test_every_add_to_calendar_menu_says_so(self):
        events, meetings = self.read("src/pages/events.njk"), self.read("src/pages/meetings.njk")
        self.assertEqual(events.count('class="cm-menu-note"'), 2)
        self.assertEqual(meetings.count('class="cm-menu-note"'), 2)
        self.assertIn('("committee.cal.reminder_day" if ev.allDay else "committee.cal.reminder_timed")', events)

    def test_not_in_the_sitemap(self):
        sitemap = self.read("src/pages/sitemap.11ty.js")
        self.assertIn("skip feeds, JSON, .ics", sitemap)
        self.assertIn("eleventyExcludeFromCollections: true", self.read("src/pages/deadlines-ics.11ty.js"))


if __name__ == "__main__":
    unittest.main()
