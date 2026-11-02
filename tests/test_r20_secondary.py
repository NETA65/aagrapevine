"""Round 20 — the secondary pages and outputs with our meetings on Google Meet, the Grapevine Meeting and the committee
meeting's guest speakers (settings written here, fixed clocks):

  * Phone     — /accessibility/#phone: our meetings on Google Meet have no number to call (axPhone `online`: the
                committee meeting and the Grapevine Meeting, each linking to its section on /meetings/), the weekly
                open meetings' Zoom room keeps its call button; a meeting on Zoom is never listed as one without;
  * Booth     — "Meetings you can join": the committee meeting with its meeting code and the next date's guest speaker,
                our Grapevine Meeting (its next date), La Viña's workshop — five rows, the player shows them all —;
                the Grapevine Meeting never takes a row of "Coming up";
  * Monthly   — the committee row's guest speaker on the page's row, the poster and the month's message (the topic in
                each language); none on a date without one (Dec 16, 2026);
  * Report    — the district report: the next meeting's guest speaker and until when, "the link and the meeting code",
                the Grapevine Meeting with its first date; the Area report: the Google Meet link and code without a
                passcode, the speaker under "Next committee meeting", past meetings "online" (never a platform);
  * Digest    — the e-mail's pointer names the coming committee meeting's guest speaker (text and HTML); a held date of
                a series of ours never links to its meeting room;
  * Search    — the Grapevine Meeting is found by its own words ("online meeting", "Google Meet"), not by the words
                of the Grapevine meetings list;
  * Orientation — {platform} in the sessions is the settings' platform.

    python -m unittest tests.test_r20_secondary -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py and the other tests' fixtures

import test_booth_build as BB  # noqa: E402
import test_send_digest as SD  # noqa: E402
from nodejs import run_js  # noqa: E402

from scripts.notify import send_digest as D  # noqa: E402

ROOM = "https://meet.google.com/abc-defg-hij"
CODE = "abc-defg-hij"
SPEAKERS = [
    {"date": "2027-01-20", "name": "Ann B.", "confirmed": True, "position": "Past delegate, Area 99", "position_es": "Ex delegada del Área 99",
     "topic": "How the Conference works", "topic_es": "Cómo trabaja la Conferencia"},
    {"date": "2027-02-17", "name": "Carlos D.", "confirmed": False, "position": "Delegate, Area 98", "position_es": "Delegado del Área 98",
     "topic": "Carrying the message", "topic_es": "Llevar el mensaje"},
]
MEETING = {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet",
           "online_url": ROOM, "meeting_id": CODE, "chair_email": "chair@example.org", "speaker_until": "19:30",
           "note": "All AA members are welcome to attend.", "note_es": "Todos los miembros de AA pueden asistir.",
           "skip_dates": [], "speakers": SPEAKERS}
GVM = {"key": "grapevine-meeting", "title": "Grapevine Meeting", "title_es": "Reunión de Grapevine (en inglés)",
       "week_of_month": 1, "weekday": "wednesday", "start": "19:00", "end": "20:00", "starts": "2026-12-02",
       "online_url": ROOM, "meeting_id": CODE, "url": "/meetings/#grapevine-meeting", "months_ahead": 6, "skip_dates": []}
LV_WS = {"key": "lv-monthly-workshop", "title": "La Viña Monthly Virtual Workshop (in Spanish)", "title_es": "Taller Mensual y Virtual de La Viña",
         "host": "lv", "week_of_month": 4, "weekday": "thursday", "start": "14:00", "end": "15:00",
         "online_url": "https://us06web.zoom.us/j/81595931777", "meeting_id": "815 9593 1777"}
CITYWIDE = {"key": "citywide-dallas", "title": "GV/LV booth at CityWide Dallas", "week_of_month": 2, "weekday": "saturday",
            "start": "17:30", "end": "19:30", "location": "Lovers Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220"}
SITE = {"url": "https://neta65.github.io/aagrapevine", "committee": "NETA 65 Grapevine & La Viña Committee",
        "committee_es": "Comité de Grapevine y La Viña de NETA 65", "contact_email": "chair@example.org",
        "meeting": MEETING, "recurring_events": [CITYWIDE, LV_WS, GVM],
        "phone_access": {"numbers": [{"number": "+1 346 248 7799", "city": "Houston"}], "weekly_open": {"phone_passcode": ""}}}


def gvm_event(ymd: str, start: str, end: str) -> dict:
    """A date of the Grapevine Meeting as the sync writes it in events.json (category recurring, ours, online only)."""
    return BB.event(f"ev:recurring:grapevine-meeting:{ymd}", "Grapevine Meeting", "Reunión de Grapevine (en inglés)",
                    start, end, "recurring", online_url=ROOM, platform="Google Meet", recurring=True, series="grapevine-meeting",
                    host="neta", meeting_id=CODE)


class Phone(unittest.TestCase):
    SCRIPT = r"""
const A = await imp("eleventy/filters/access.js");
const t = (k) => ({ "nav.meeting": "Committee meeting" })[k] || k;
const zoom = { ...input.site, meeting: { ...input.site.meeting, platform: "Zoom", online_url: "https://us02web.zoom.us/j/9494767497",
  meeting_id: "949 476 7497", passcode: "" }, recurring_events: [input.lv] };
out({
  meet: A.axPhone(input.site, input.weekly, "en", t), meetEs: A.axPhone(input.site, input.weekly, "es", t).online,
  zoom: A.axPhone(zoom, input.weekly, "en", t),
  platforms: [A.platformOf(input.room), A.platformOf("https://us06web.zoom.us/j/1"), A.platformOf("not a link"), A.platformOf("")],
});
"""

    def test_our_meetings_on_google_meet_have_no_number_to_call(self):
        weekly = [{"zoomDigits": "87120368287", "zoomId": "871 2036 8287", "passcode": "238047", "title": "Weekly Open"}]
        r = run_js(self, self.SCRIPT, data={"site": SITE, "weekly": weekly, "lv": LV_WS, "room": ROOM}, needs_modules=False)
        # the weekly open meetings' Zoom room: its call button, as before
        self.assertEqual([(m["key"], m["call"]) for m in r["meet"]["meetings"]],
                         [("weekly-87120368287", "tel:+13462487799,,87120368287%23,,,,*238047%23")])
        self.assertTrue(r["meet"]["ok"])
        # our own meetings on Google Meet: listed as having no number to call — never La Viña's workshop (theirs, on
        # Zoom) or the CityWide booth (a place)
        self.assertEqual(r["meet"]["online"], [{"platform": "Google Meet", "items": [
            {"key": "committee", "title": "Committee meeting", "details": "/meetings/#committee-meeting"},
            {"key": "grapevine-meeting", "title": "Grapevine Meeting", "details": "/meetings/#grapevine-meeting"}]}])
        self.assertEqual(r["meetEs"][0]["items"][1]["title"], "Reunión de Grapevine (en inglés)")
        # back on Zoom with a meeting ID: the committee meeting has its call button again, and nothing is "online only"
        self.assertEqual([m["key"] for m in r["zoom"]["meetings"]], ["committee", "weekly-87120368287"])
        self.assertEqual(r["zoom"]["online"], [])
        self.assertEqual(r["platforms"], ["Google Meet", "Zoom", "", ""])

    def test_the_page_and_its_words(self):
        page = (ROOT / "src" / "pages" / "accessibility.njk").read_text(encoding="utf-8")
        self.assertIn("{% for g in phone.online %}", page)
        self.assertIn("'access.ph_meet_subject'", page)
        s = json.loads((ROOT / "src" / "_i18n" / "access.json").read_text(encoding="utf-8"))
        for key in ("access.ph_meet_t", "access.ph_meet"):
            for lang in ("en", "es"):
                self.assertIn("{platform}", s[key][lang], (key, lang))
        # honest: no promise the code does not check (captions, "no account needed"), and the weekly meetings' Zoom
        # dial-in words stay
        for key in ("access.ph_meet_t", "access.ph_meet", "access.ph_meet_help", "access.ph_title", "access.ph_sub"):
            for lang in ("en", "es"):
                self.assertNotRegex(s[key][lang], r"(?i)caption|subt[ií]tulo|account|cuenta", (key, lang))
        self.assertIn("Zoom", s["access.ph_any_number"]["en"])
        self.assertNotIn("our Zoom meetings", s["access.ph_title"]["en"] + s["access.meta_desc"]["en"])
        pwa = json.loads((ROOT / "src" / "_i18n" / "pwa.json").read_text(encoding="utf-8"))
        self.assertNotIn("our Zoom", pwa["pwa.offline.phone_lead"]["en"])


BOOTH_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const res = {};
for (const [name, now] of input.runs) {
  const items = B.liveItems({ db: input.db, site: input.site, now: new Date(now), base: "/aagrapevine/" }).items;
  const pick = (id) => items.find((i) => i.id === id) || null;
  res[name] = { meetings: pick("live:meetings:next"), events: pick("live:events:next") };
}
out(res);
"""


class Booth(unittest.TestCase):
    def setUp(self):
        BB.node_ready(self)

    def run_booth(self, runs):
        events = [
            BB.event("ev:recurring:lv-monthly-workshop:2027-01-28", "La Viña Monthly Virtual Workshop (in Spanish)",
                     "Taller Mensual y Virtual de La Viña", "2027-01-28T20:00:00Z", "2027-01-28T21:00:00Z", "recurring",
                     online_url="https://us06web.zoom.us/j/81595931777", platform="Zoom", recurring=True,
                     series="lv-monthly-workshop", host="lv", meeting_id="815 9593 1777"),
            gvm_event("2026-12-02", "2026-12-03T01:00:00Z", "2026-12-03T02:00:00Z"),
            gvm_event("2027-01-06", "2027-01-07T01:00:00Z", "2027-01-07T02:00:00Z"),
            gvm_event("2027-02-03", "2027-02-04T01:00:00Z", "2027-02-04T02:00:00Z"),
            BB.event("ev:manual:2027-01-23-writing", "Grapevine Writing Workshop — Plano", "Taller de Escritura de Grapevine — Plano",
                     "2027-01-23T19:00:00Z", "2027-01-23T22:00:00Z", location="Group Two, 2 Elm St, Plano, TX"),
        ]
        site = {**SITE, "built": runs[0][1]}
        db = {"events": {"items": events}, "weekly_open": {"items": BB.WEEKLY_OPEN}}
        return run_js(self, BOOTH_JS, data={"db": db, "site": site, "runs": runs})

    def test_meetings_you_can_join(self):
        r = self.run_booth([("jan", "2027-01-10T17:00:00Z"), ("dec", "2026-12-10T17:00:00Z")])
        m = r["jan"]["meetings"]
        rows = m["en"]["rows"]
        self.assertEqual([x["title"] for x in rows], ["NETA 65 Grapevine & La Viña Committee Meeting", "Grapevine Weekly Open AA Meeting",
                                                      "La Viña Open Meeting (in Spanish)", "Grapevine Meeting",
                                                      "La Viña Monthly Virtual Workshop (in Spanish)"])
        # the committee meeting: where, its meeting code (never "Meeting ID" for a code) and the next date's speaker
        self.assertEqual(rows[0]["note"], f"Online on Google Meet · Meeting code {CODE} · Guest speaker on Jan 20: Ann B.")
        self.assertEqual(m["es"]["rows"][0]["note"],
                         f"En línea por Google Meet · Código de la reunión {CODE} · Orador(a) invitado(a) el 20 de enero: Ann B.")
        # the Grapevine Meeting: its next date (February's: January's is over), ours (both magazines' colours)
        gvm = rows[3]
        self.assertIn("February 3, 2027", gvm["when"])
        self.assertEqual((gvm["note"], gvm["pub"]), (f"Online on Google Meet · Meeting code {CODE}", "both"))
        self.assertGreater(gvm["ends_ts"], gvm["starts_ts"])
        self.assertEqual(m["es"]["rows"][3]["title"], "Reunión de Grapevine (en inglés)")      # (said once)
        self.assertEqual(m["es"]["rows"][1]["title"], "Grapevine Weekly Open AA Meeting (en inglés)")
        # never a row of "Coming up": the next four events are the others
        titles = [x["title"] for x in r["jan"]["events"]["en"]["rows"]]
        self.assertNotIn("Grapevine Meeting", titles)
        self.assertIn("Grapevine Writing Workshop — Plano", titles)
        # December 16, 2026 has no guest speaker: no speaker in the note; the Grapevine Meeting's next date is Jan 6
        dec = r["dec"]["meetings"]["en"]["rows"]
        self.assertEqual(dec[0]["note"], f"Online on Google Meet · Meeting code {CODE}")
        self.assertIn("January 6, 2027", dec[3]["when"])

    def test_the_player_shows_five_meetings(self):
        js = (ROOT / "src" / "assets" / "js" / "booth.js").read_text(encoding="utf-8")
        self.assertRegex(js, r'RENDER\.meetings = function \(R\) \{ return listSlide\(R, "booth\.screen\.meetings", "users", "map-pin", 5\); \};')
        # (the themes slide shows five rows too: the slide's fit shrinks its type when the rows need it)
        self.assertRegex(js, r'"pen-line", "tag", 5\)')

    def test_the_csv_rows(self):
        import csv
        rows = {r["id"]: r for r in csv.DictReader((ROOT / "content" / "booth" / "booth.csv").read_text(encoding="utf-8-sig").splitlines())}
        committee = rows["message-fun-event-committee"]
        self.assertNotIn("Zoom", committee["text_en"] + committee["text_es"])
        self.assertIn("online", committee["text_en"])
        self.assertEqual(rows["message-committee-guest-speakers"]["from"], "2026-12-17", "December 16 has no speaker")
        self.assertIn("done by 7:30 p.m.", rows["message-committee-guest-speakers"]["text_en"])
        gvm = rows["fact-online-grapevine-meeting"]
        self.assertIn("Google Meet", gvm["text_en"] + gvm["text_es"])
        self.assertNotRegex(gvm["text_en"], r"(?i)grapevine meetings")


MONTHLY_JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const { db, site } = input;
const res = {};
for (const [key, now] of input.runs) {
  const d = new Date(now);
  const mm = { en: M.monthModel(key, db, {}, site, "en", d), es: M.monthModel(key, db, {}, site, "es", d) };
  const nw = { en: M.monthNow(db, site, "en", d), es: M.monthNow(db, site, "es", d) };
  const iss = { en: [], es: [] };
  res[key] = {
    committee: { en: mm.en.committee, es: mm.es.committee }, dates: mm.en.dates.map((x) => [x.kind, x.ymd, x.title]),
    next: nw.en.nextCommittee,
    msg: M.monthMessage({ mm, nw, iss }, ["en"], "whatsapp", site, t), bi: M.monthMessage({ mm, nw, iss }, ["en", "es"], "whatsapp", site, t),
  };
}
out(res);
"""


class Monthly(unittest.TestCase):
    def test_the_guest_speaker_on_the_rows_and_in_the_message(self):
        db = {"events": {"items": [gvm_event("2026-12-02", "2026-12-03T01:00:00Z", "2026-12-03T02:00:00Z"),
                                   gvm_event("2027-01-06", "2027-01-07T01:00:00Z", "2027-01-07T02:00:00Z")]}}
        r = run_js(self, MONTHLY_JS, data={"db": db, "site": SITE, "runs": [["2027-01", "2027-01-02T18:00:00Z"],
                                                                             ["2026-12", "2026-12-17T18:00:00Z"],
                                                                             ["2026-11", "2026-11-26T18:00:00Z"]]})
        jan = r["2027-01"]
        self.assertEqual(jan["committee"]["en"]["speaker"], {"ymd": "2027-01-20", "name": "Ann B.", "position": "Past delegate, Area 99",
                                                             "topic": "How the Conference works"})
        self.assertEqual(jan["committee"]["es"]["speaker"]["topic"], "Cómo trabaja la Conferencia")
        self.assertEqual(jan["committee"]["en"]["platform"], "Google Meet")
        self.assertIn(["recurring", "2027-01-06", "Grapevine Meeting"], jan["dates"])
        lines = jan["msg"].split("\n")
        i = next(n for n, x in enumerate(lines) if "Committee meeting (Google Meet)" in x)
        self.assertEqual(lines[i + 1], "  Guest speaker: Ann B. — “How the Conference works”")
        bi = jan["bi"].split("\n")
        i = next(n for n, x in enumerate(bi) if "Committee meeting / Reunión del comité (Google Meet)" in x)
        self.assertEqual(bi[i + 1:i + 3], ["  Guest speaker: Ann B. — “How the Conference works”", "  “Cómo trabaja la Conferencia”"])
        self.assertNotIn("Zoom", jan["msg"])
        # December 16, 2026: on Google Meet, no speaker; once it is over, the next meeting (January's) with its speaker
        dec = r["2026-12"]
        self.assertIsNone(dec["committee"]["en"]["speaker"])
        self.assertEqual((dec["next"]["ymd"], dec["next"]["speaker"]["name"]), ("2027-01-20", "Ann B."))
        self.assertIn("• Next committee meeting: Wed, Jan 20 · 7–8 PM Central — Google Meet\n  Guest speaker: Ann B. — “How the Conference works”",
                      dec["msg"])
        # November 2026: the Grapevine Meeting is not there yet (its first date is December 2)
        self.assertNotIn("Grapevine Meeting", [x[2] for x in r["2026-11"]["dates"]])

    def test_a_poster_never_leaves_out_the_committee_meeting(self):
        # one more date a month (the Grapevine Meeting): a busy month's poster shows one date fewer, and the one it
        # leaves out is never the committee meeting's
        r = run_js(self, """
            const M = await imp("eleventy/filters/monthly.js");
            const d = (kind, ymd) => ({ kind, ymd });
            const dates = [d("recurring", "2027-02-03"), d("recurring", "2027-02-13"), d("event", "2027-02-14"),
                           d("committee", "2027-02-17"), d("event", "2027-02-20")];
            const ymds = (list) => list.map((x) => x.ymd);
            out({ three: ymds(M.posterDates(dates, 3)), four: ymds(M.posterDates(dates, 4)), five: ymds(M.posterDates(dates, 5)),
                  none: ymds(M.posterDates(dates.filter((x) => x.kind !== "committee"), 3)) });
        """)
        self.assertEqual(r["three"], ["2027-02-03", "2027-02-13", "2027-02-17"])
        self.assertEqual(r["four"], ["2027-02-03", "2027-02-13", "2027-02-14", "2027-02-17"])
        self.assertEqual(r["five"], ["2027-02-03", "2027-02-13", "2027-02-14", "2027-02-17", "2027-02-20"])
        self.assertEqual(r["none"], ["2027-02-03", "2027-02-13", "2027-02-14"])
        poster = (ROOT / "src" / "_includes" / "macros" / "monthly.njk").read_text(encoding="utf-8")
        self.assertIn("{%- set shown = m.dates | mpPosterDates(lim) -%}", poster)

    def test_the_templates(self):
        page = (ROOT / "src" / "pages" / "monthly-month.njk").read_text(encoding="utf-8")
        poster = (ROOT / "src" / "_includes" / "macros" / "monthly.njk").read_text(encoding="utf-8")
        self.assertIn("d.speaker", page)
        self.assertIn("nc.speaker", page)
        self.assertIn('{% if d.speaker %} · {{ "monthly.speaker" | t(lang, { name: d.speaker.name }) }}{% endif %}', poster)
        self.assertNotIn("Zoom link", page)


REPORT_JS = r"""
const R = await imp("eleventy/filters/report.js");
const carry = (await imp("src/_data/carry.js")).default();
const now = new Date(input.now);
const committee = (m) => Object.fromEntries(["en", "es"].map((l) => [l, m.langs[l].sections.find((x) => x.id === "committee").text]));
const area = R.areaModel(input.db, input.site, now);
out({
  jan: committee(R.reportModel(input.db, input.meeting, carry, input.site, now)),
  dec: committee(R.reportModel(input.db, input.decMeeting, carry, input.site, new Date(input.decNow))),
  area: { mt: area.mt.filter((m) => ["2026-11-18", "2026-12-16", "2027-01-20"].includes(m.y)), en: area.langs.en.s, es: area.langs.es.s },
});
"""


class Report(unittest.TestCase):
    def test_the_district_and_area_reports(self):
        db = {"events": {"items": []}, "editorial": {"items": []}, "articles": {"items": [], "issues": []}, "shop": {},
              "meetings": {"items": []}, "weekly_open": {"items": []}, "pdfs": {"items": []}, "spotlight": {"items": []},
              "audio_project": {}}
        meeting = {"next": {"ymd": "2027-01-20", "start": "2027-01-21T01:00:00Z", "end": "2027-01-21T02:00:00Z"},
                   "rule": {"weekday": 3, "n": 3, "start": "19:00", "end": "20:00"}}
        dec = {"next": {"ymd": "2026-12-16", "start": "2026-12-17T01:00:00Z", "end": "2026-12-17T02:00:00Z"},
               "rule": {"weekday": 3, "n": 3, "start": "19:00", "end": "20:00"}}
        r = run_js(self, REPORT_JS, data={"db": db, "site": SITE, "meeting": meeting, "decMeeting": dec,
                                          "now": "2027-01-05T18:00:00Z", "decNow": "2026-11-27T18:00:00Z"})
        nb = lambda s: s.replace(" ", " ").replace(" ", " ").replace(" ", " ")   # noqa: E731
        en, es = nb(r["jan"]["en"]), nb(r["jan"]["es"])
        self.assertIn("Guest speaker: Ann B., Past delegate, Area 99 — “How the Conference works”.", en)
        self.assertIn("The talk and questions are done by 7:30 PM; then committee business until 8:00 PM.", en)
        self.assertIn("Orador(a) invitado(a): Ann B., Ex delegada del Área 99 — “Cómo trabaja la Conferencia”.", es)
        self.assertIn("terminan a más tardar a las 7:30 p. m.; luego, los asuntos del comité hasta las 8:00 p. m.", es)
        self.assertIn("How to join on Google Meet, the link and the meeting code: https://neta65.github.io/aagrapevine/meetings/", en)
        self.assertNotIn("meeting ID and passcode", en)
        self.assertIn("Grapevine Meeting: every first Wednesday of the month · 7:00 – 8:00 PM Central time, on Google Meet. "
                      "Every AA member is welcome: https://neta65.github.io/aagrapevine/meetings/#grapevine-meeting", en)
        self.assertNotIn("The first one", en, "January: the Grapevine Meeting has begun")
        self.assertIn("Reunión de Grapevine (en inglés): cada primer miércoles del mes", es)
        self.assertNotIn("Zoom", en + es)
        # late November: December 16 has no speaker; the Grapevine Meeting's first date is ahead
        d = nb(r["dec"]["en"])
        self.assertNotIn("Guest speaker", d)
        self.assertIn("The first one is on Wednesday, December 2.", d)
        self.assertIn("La primera es el miércoles 2 de diciembre.", nb(r["dec"]["es"]))
        # the Area report: the link and the code (no passcode on Google Meet), the speaker under the next meeting's line,
        # past meetings "online" — Nov 18, 2026 was still on Zoom
        a = r["area"]
        self.assertIn(f"Google Meet: meet.google.com/{CODE} · Meeting code: {CODE}", a["en"]["meet_more"])
        self.assertIn(f"Google Meet: meet.google.com/{CODE} · Código de la reunión: {CODE}", a["es"]["meet_more"])
        self.assertIn("How to join on Google Meet, the link and the meeting code", a["en"]["meet_more"])
        self.assertEqual(a["en"]["met"], "Committee meetings (online): {dates} — about [N] members each time")
        self.assertEqual(a["en"]["meets"], "Committee meetings on Google Meet: {dates}")
        jan = next(m for m in a["mt"] if m["y"] == "2027-01-20")
        self.assertEqual(nb(jan["t"]["en"][1]).split("\n"), [
            "Next NETA 65 Grapevine / La Viña committee meeting: Wednesday, January 20, 7–8 PM Central time, on Google Meet.",
            "Guest speaker: Ann B., Past delegate, Area 99 — “How the Conference works”.",
            "The talk and questions are done by 7:30 PM; then committee business until 8:00 PM."])
        self.assertEqual(len(next(m for m in a["mt"] if m["y"] == "2026-12-16")["t"]["en"][1].split("\n")), 1)


class Digest(SD.DigestCase):
    """The e-mail (send_digest.py): the coming committee meeting's guest speaker in the pointer; a held date of the
    Grapevine Meeting links to its section on /meetings/, never to the meeting room."""

    def test_the_speaker_and_the_links(self):
        self.full_month()
        events = json.loads((self.site_dir / "events.json").read_text(encoding="utf-8"))["items"]
        for e in events:
            if e["id"] == "ev:committee:2026-10-21":
                e["extra"]["speaker"] = {"name": "Ann B.", "position": {"en": "Past delegate", "es": "Ex delegada"},
                                         "topic": {"en": "How the Conference works", "es": "Cómo trabaja la Conferencia"}}
        held = SD.event("ev:recurring:grapevine-meeting:2026-09-02", "2026-09-03T00:00:00Z", "2026-09-03T01:00:00Z",
                        "Grapevine Meeting", "recurring", series="grapevine-meeting", online_url=ROOM, host="neta")
        held["url"] = ""
        self.write("events", {"items": events + [held]})
        data = D.collect(SD.OCT1)
        self.assertEqual(data["speaker"], {"ymd": "2026-10-21", "name": "Ann B.",
                                           "topic": {"en": "How the Conference works", "es": "Cómo trabaja la Conferencia"}})
        row = D.event_row(next(e for e in data["events"] if e["id"] == held["id"]), "en", D.Links(SD.SITE))
        self.assertEqual((row["where"], row["url"]), ("Online", f"{SD.SITE}/events/"))
        html, text = self.preview()
        self.assertIn("Committee meeting on October 21, 2026 — guest speaker: Ann B. — “How the Conference works”", text)
        self.assertIn("Reunión del comité del 21 de octubre de 2026 — orador(a) invitado(a): Ann B. — “Cómo trabaja la Conferencia”", text)
        self.assertIn("guest speaker: Ann B.", html)
        self.assertNotIn("meet.google.com", text + html)
        # once that meeting has begun, the pointer no longer names it
        later = D.collect(datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc), "2026-09")
        self.assertIsNone(later["speaker"])


class Search(unittest.TestCase):
    def test_the_grapevine_meeting_has_words_of_its_own(self):
        code = (ROOT / "eleventy" / "filters" / "library.js").read_text(encoding="utf-8")
        self.assertIn('ownOnline ? both("search.kw.own_online") : ""', code)
        s = json.loads((ROOT / "src" / "_i18n" / "library.json").read_text(encoding="utf-8"))
        own = s["search.kw.own_online"]
        for lang, words in (("en", ("online meeting", "google meet", "first wednesday")), ("es", ("reunión en línea", "google meet", "primer miércoles"))):
            for w in words:
                self.assertIn(w, own[lang], (lang, w))
        # never the words of the Grapevine meetings list (the AA groups that read Grapevine)
        for w in ("grapevine meetings", "gr ", "in person", "near me"):
            self.assertNotIn(w, own["en"])
        for lang, w in (("en", "google meet"), ("es", "google meet"), ("en", "guest speaker"), ("es", "orador invitado")):
            self.assertIn(w, s["search.kw.meetings"][lang])


class Orientation(unittest.TestCase):
    def test_the_platform_placeholder(self):
        r = run_js(self, """
            const o = input.o;
            out({ en: filters.o101Text(o.text, "en", filters.o101Vars({}, "en", "Every third Wednesday", "7:00 PM", "Google Meet")),
                  es: filters.o101Text(o.text, "es", filters.o101Vars({}, "es", "Cada tercer miércoles", "7:00 p. m.", "Google Meet")),
                  none: filters.o101Vars({}, "en", "", "").platform });
        """, data={"o": {"text": {"en": "We meet on {platform} {rule_lc}.", "es": "Nos reunimos por {platform} {rule_lc}."}}})
        self.assertEqual((r["en"], r["es"], r["none"]), ("We meet on Google Meet every third Wednesday.",
                                                         "Nos reunimos por Google Meet cada tercer miércoles.", "Zoom"))
        yml = (ROOT / "config" / "orientation.yml").read_text(encoding="utf-8")
        self.assertNotRegex(yml, r"(?:on|por) Zoom")


if __name__ == "__main__":
    unittest.main()
