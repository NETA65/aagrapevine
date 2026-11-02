"""Round 20 — our meetings on Google Meet, the Grapevine Meeting and the committee meeting's guest speakers: the
settings and the data they make (scripts/sync/meeting.py, scripts/sync/build_data.py) and the pages' reading of the
same settings (eleventy.config.js monthlyRule, eleventy/central-time.js ruleDate, eleventy/filters/committee.js,
monthly.js, src/_data/meeting.js), which must agree with the sync's:

  * a monthly series' first date (`starts:`): no date before it — not even in the 90 past days the calendar files
    keep —, a note when it is not one of the rule's days; a series' `url:` may be a page of this site;
  * the committee meeting's guest speakers (`meeting: speakers:`): who speaks at which meeting, the same notes on both
    sides when one is left out (not a meeting day, a skip date, a second one for a date, a full last name), the
    speaker's lines in each meeting's calendar text and in events.json — never in what search engines read, never
    in a calendar alarm, never "confirmed" —, and a reminder for the chair 45 days ahead;
  * the meeting's flyers (`meeting: flyer_match:`) under the names the committee gives them on the Drive, from the
    flyers/ folder only, a month's own named with its month — never a second event;
  * one Google Meet room for two meetings: the committee meeting (or a workshop) in the Grapevine Meeting's room is
    never a moved Grapevine Meeting;
  * the link to join and the "Meeting code" in what search engines read (left out) and on a series' card.

The settings are written here, with fixed clocks; RealSettings (the gate's CONTENT_TESTS) checks config/site.yml
itself: the Grapevine Meeting, the CityWide booth, the 12 speakers of 2027 and the flyer names.

    python -m unittest tests.test_r20_meeting -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from nodejs import run_js  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import drive as D  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402

CHI = ZoneInfo("America/Chicago")
NOW = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)          # Thu Nov 26, 2026 (noon CST): the day of the merge
ROOM = "https://meet.google.com/abc-defg-hij"

GVM_ENTRY = """
  - key: "grapevine-meeting"
    title: "Grapevine Meeting (online)"
    title_es: "Reunión de Grapevine (en línea)"
    summary: "Online AA meeting in English: we read a story from AA Grapevine and share on its topic."
    summary_es: "Reunión de AA en línea, en inglés: leemos una historia de AA Grapevine y compartimos sobre su tema."
    week_of_month: 1
    weekday: "wednesday"
    start: "19:00"
    end: "20:00"
    starts: "2026-12-02"
    online_url: "https://meet.google.com/abc-defg-hij"
    meeting_id: "abc-defg-hij"
    contact: "grapevine@example.org"
    url: "/meetings/#grapevine-meeting"
    flyer_match: "grapevine meeting *[-–—] *flyer"
    months_ahead: 6
    skip_dates: []
"""
SPEAKERS = """
  speakers:
    - date: "2027-01-20"
      name: "Ann B."
      confirmed: true
      position: "Past delegate, Area 99"
      position_es: "Ex delegada del Área 99"
      topic: "How the Conference works"
      topic_es: "Cómo trabaja la Conferencia"
    - date: 2027-02-17
      name: "Carlos D."
      confirmed: false
      position: "Delegate, Area 98"
      topic: "Grapevine as a tool"
"""
YAML = """
site: {timezone: America/Chicago, url: "https://example.org/gv", committee: "NETA 65 Grapevine & La Viña Committee",
       committee_es: "Comité de Grapevine y La Viña de NETA 65"}
meeting:
  week_of_month: 3
  weekday: "wednesday"
  start: "19:00"
  end: "20:00"
  platform: "Google Meet"
  online_url: "https://meet.google.com/abc-defg-hij"
  meeting_id: "abc-defg-hij"
  note: "All AA members are welcome to attend. No registration required."
  note_es: "Todos los miembros de AA pueden asistir. No hace falta registrarse."
  skip_dates: []
  flyer_match: "committee meeting *[-–—] *(flyer|guest speaker)"
  speaker_until: "19:30"
""" + SPEAKERS + "recurring_events:" + GVM_ENTRY

# The names the committee gives its files on the Drive (round 20: the brand kit's upload names) → which settings'
# flyer_match finds each one: "meeting" (the committee meeting's) or "series" (the Grapevine Meeting's), or none
FLYER_NAMES = {
    ("flyers", "Grapevine Meeting - flyer.png"): "series",
    ("flyers", "Committee Meeting - flyer.png"): "meeting",
    **{("flyers", f"{m} 2027 Committee Meeting - guest speaker.png"): "meeting"
       for m in ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December")},
    ("flyers", "Our online meetings - flyer.png"): None,
    ("flyers", "2027 Guest Speaker Series - flyer.png"): None,
    ("slides", "Grapevine and La Viña Monthly Committee Meeting.pptx"): None,
}


class NoTranslator:
    """Stands in for the translation model: tests never download or run it."""
    def translate(self, texts, src, tgt):
        return [(None, False) for _ in texts]


def ctx_with(cfg: str | dict = YAML, now: datetime = NOW, **raw: list[dict]) -> B.Ctx:
    """A build context with these settings, a fixed clock and the raw items of some sources (drive=[…])."""
    ctx = B.Ctx(offline=True)
    ctx.cfg = yaml.safe_load(cfg) if isinstance(cfg, str) else cfg
    ctx.now, ctx.now_ts = now, now.timestamp()
    ctx.today_local = now.astimezone(ctx.tz).date()
    for name, items in raw.items():
        ctx.raw[name] = {"items": items}
    return ctx


def drive_items(names=FLYER_NAMES) -> list[dict]:
    """The files as drive.py lists them (data/raw/drive.json): its own reading of each name — a month alone is
    extra.event_month, a day would be extra.event_date (an event)."""
    out = []
    for n, (folder, name) in enumerate(names, 1):
        mime = ("application/vnd.openxmlformats-officedocument.presentationml.presentation" if name.endswith(".pptx")
                else "image/png")
        e = D.Entry(id=f"file{n:02d}", name=name, mime=mime, modified="2026-11-20")
        out.append(D.build_item(D.Found(e, D.Panel(77, "Panel 77", "p77", "P77"), [folder], ["root", "p77", "f"], seq=n), {}))
    return out


class Untranslated(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())
        p.start()
        self.addCleanup(p.stop)


# =========================================================================== a series' first date
class FirstDate(Untranslated):
    def test_no_date_before_it_not_even_in_the_past_days(self):
        rule = M.MonthlyRule(week_of_month=1, weekday=2, start=(19, 0), end=(20, 0))
        # without a first date, a build on Nov 26 makes up the last 90 days' meetings…
        self.assertEqual([d["ymd"] for d in M.upcoming_rule_dates(rule, 3, CHI, NOW, include_recent_days=90)],
                         ["2026-09-02", "2026-10-07", "2026-11-04"])
        first = M.MonthlyRule(week_of_month=1, weekday=2, start=(19, 0), end=(20, 0), starts="2026-12-02")
        self.assertEqual([d["ymd"] for d in M.upcoming_rule_dates(first, 3, CHI, NOW, include_recent_days=90)],
                         ["2026-12-02", "2027-01-06", "2027-02-03"])
        # the dates before it never count: still `count` real dates
        self.assertEqual(len(M.upcoming_rule_dates(first, 6, CHI, NOW)), 6)

    def test_the_series_from_its_first_date(self):
        ids = [e["id"] for e in B.recurring_events(ctx_with())]
        self.assertEqual(ids, [f"ev:recurring:grapevine-meeting:{d}" for d in (
            "2026-12-02", "2027-01-06", "2027-02-03", "2027-03-03", "2027-04-07", "2027-05-05")])
        # a month later, the first one is a past date the calendar files keep — and still none before it
        later = B.recurring_events(ctx_with(now=datetime(2027, 1, 10, 18, 0, tzinfo=timezone.utc)))
        self.assertEqual([e["id"][-10:] for e in later][:3], ["2026-12-02", "2027-01-06", "2027-02-03"])
        first = B.recurring_events(ctx_with())[0]
        self.assertEqual((first["extra"]["platform"], first["extra"]["online_url"], first["extra"]["meeting_id"],
                          first["extra"]["location"], first["extra"]["host"], first["url"]),
                         ("Google Meet", ROOM, "abc-defg-hij", None, "neta", "/meetings/#grapevine-meeting"))
        self.assertEqual(first["extra"]["recurrence_label"], "Every first Wednesday of the month · 7:00 – 8:00 PM")

    def test_the_notes(self):
        def notes(starts, url='"/meetings/#grapevine-meeting"'):
            text = YAML.replace('starts: "2026-12-02"', f"starts: {starts}").replace(
                'url: "/meetings/#grapevine-meeting"', f"url: {url}")
            specs, problems = B.recurring_specs(ctx_with(text))
            return specs[0], problems
        sp, problems = notes("2026-12-02")              # an unquoted YAML date counts the same
        self.assertEqual((sp["rule"].starts, problems), ("2026-12-02", []))
        sp, problems = notes('"2026-12-01"')            # not a 1st Wednesday: the first date is the next one
        self.assertEqual(sp["rule"].starts, "2026-12-01")
        self.assertEqual(problems, ["recurring_events entry 1 (grapevine-meeting): starts “2026-12-01” is not the 1st "
                                    "Wednesday of its month — the first date is 2026-12-02 (the rule's next day)"])
        sp, problems = notes('"soon"')
        self.assertIsNone(sp["rule"].starts)
        self.assertEqual(problems, ["recurring_events entry 1 (grapevine-meeting): starts “soon” is not a date like "
                                    "\"2026-12-02\" — ignored"])
        # `url:` — a page of this site, or a web address; anything else is left out (and noted)
        for url, want in (('"/meetings/#grapevine-meeting"', "/meetings/#grapevine-meeting"),
                          ('"www.example.org/gvm"', "https://www.example.org/gvm"), ('"meetings"', None),
                          ('"//example.org/x"', None)):
            sp, problems = notes("2026-12-02", url)
            self.assertEqual(sp["url"], want, url)
            self.assertEqual(bool(problems), want is None, (url, problems))

    def test_the_committee_meeting_reads_it_too(self):
        self.assertEqual(M.meeting_rule({"starts": "2027-01-20"}).starts, "2027-01-20")
        self.assertIsNone(M.meeting_rule({}).starts)
        got = M.upcoming_meetings(2, now=NOW, cfg={"meeting": {"starts": "2027-01-20"}})
        self.assertEqual([d["ymd"] for d in got], ["2027-01-20", "2027-02-17"])

    def test_no_listing_note_for_a_month_before_it(self):
        ctx = ctx_with()
        recurring = B.recurring_events(ctx)
        listing = {"id": "ev:gvcal:x", "category": "gv-calendar", "title": "Grapevine Meeting", "url": "https://x.org/a",
                   "extra": {"start": "2026-11-11T01:00:00Z", "end": "2026-11-11T02:00:00Z", "online_url": ROOM}}
        ctx.today_local = date(2026, 11, 2)
        self.assertEqual(B.series_listing_notes(ctx, [listing], recurring), [], "November is before the first date")


class FirstDateOnPages(unittest.TestCase):
    """eleventy.config.js monthlyRule reads `starts` as the sync does (meeting.check_starts / ymd_text); the countdown's
    rule (central-time.js ruleDate — the browser runs the same code), the pages' dates (committee.js meetingDates,
    cmRuleObj) and the monthly toolkit's projection (monthly.js meetingByRule) give no date before it."""

    VALUES = ["2026-12-02", " 2026-12-02 ", "2027-02-30", "soon", "", None, 20261202, "2026-12-02T19:00", True]

    def test_the_pages_read_it_like_the_sync(self):
        got = run_js(self, """
            const yaml = await import("js-yaml");
            const { monthlyRule } = await imp("eleventy.config.js");
            const base = { key: "gvm", title: "Grapevine Meeting", week_of_month: 1, weekday: "wednesday", start: "19:00" };
            out({ values: input.map((v) => monthlyRule({ ...base, starts: v }, true).starts ?? null),
                  unquoted: monthlyRule(yaml.load("starts: 2026-12-02"), true).starts,
                  meeting: monthlyRule({ starts: "2027-01-20" }).starts, none: "starts" in monthlyRule(base, true) });
        """, data=self.VALUES)
        self.assertEqual(got["values"], [M.check_starts(v, 2, 1)[0] for v in self.VALUES])
        self.assertEqual((got["unquoted"], got["meeting"], got["none"]), ("2026-12-02", "2027-01-20", False))

    def test_no_date_before_it(self):
        spec = yaml.safe_load(GVM_ENTRY)[0]
        got = run_js(self, """
            const T = await imp("eleventy/central-time.js");
            const C = await imp("eleventy/filters/committee.js");
            const { meetingByRule } = await imp("eleventy/filters/monthly.js");
            const rule = filters.cmRuleObj(input);
            const day = (mo) => { const d = T.ruleDate(2026, mo, rule, "America/Chicago"); return d && d.ymd; };
            out({ rule, nov: day(10), dec: day(11), noStarts: T.ruleDate(2026, 10, { ...rule, starts: "" }, "America/Chicago").ymd,
                  byRule: ["2026-11", "2026-12"].map((k) => (meetingByRule(k, input) || {}).ymd || null),
                  dates: C.meetingDates(input, 3, 2, new Date("2026-11-26T18:00:00Z")).map((d) => d.ymd) });
        """, data=spec)
        self.assertEqual(got["rule"], {"weekday": 3, "n": 1, "start": "19:00", "end": "20:00", "skip": [], "starts": "2026-12-02"})
        self.assertEqual((got["nov"], got["dec"], got["noStarts"]), (None, "2026-12-02", "2026-11-04"))
        self.assertEqual(got["byRule"], [None, "2026-12-02"])
        self.assertEqual(got["dates"], ["2026-12-02", "2027-01-06"])

    def test_the_monthly_toolkit_passes_it_on(self):
        # monthly.js projects a series' later months from its rule with the settings' skip_dates AND starts
        src = (ROOT / "eleventy" / "filters" / "monthly.js").read_text(encoding="utf-8")
        self.assertIn('skip_dates: sp.skip_dates || [], starts: sp.starts || ""', src)


# =========================================================================== the guest speakers
SPEAKER_CASES = """
week_of_month: 3
weekday: "wednesday"
skip_dates: ["2027-03-17"]
speaker_until: "19:30"
speakers:
  - date: "2027-01-20"
    name: "Ann B."
    confirmed: true
    position: "Past delegate, Area 99"
    position_es: "Ex delegada del Área 99"
    topic: "How the Conference works"
    topic_es: "Cómo trabaja la Conferencia"
  - {date: "2027-01-21", name: "Bad D.", topic: "Wrong day"}
  - {date: "2027-02-17", name: "Jeannie Smith", topic: "A full last name"}
  - {date: "2027-01-20", name: "Dup D.", topic: "A second one"}
  - {date: "soon", name: "Xavier Y.", topic: "No date"}
  - "not a block"
  - {date: "2027-03-17", name: "Greg G.", topic: "A skip date"}
  - {date: 2027-07-21, name: "Luke B.", confirmed: "yes"}
  - {date: "2027-04-21", name: "María José C.", topic_es: "Solo en español", position: "Delegate"}
  - {date: "2027-05-19", topic: "No name"}
"""
SPEAKER_NOTES = [
    "speaker “Bad D.”: 2027-01-21 is not the 3rd Wednesday of its month — left out (that month's meeting is 2027-01-20)",
    "speaker “Jeannie Smith” (2027-02-17): the name must be a first name and a last initial, like \"Rick W.\" — left out",
    "speaker “Dup D.”: 2027-01-20 has a speaker already (“Ann B.”) — left out",
    "speaker “Xavier Y.”: date “soon” is not a date like \"2027-01-20\" — left out",
    "speakers entry 6: not understood (its settings must be indented under “- date:”) — left out",
    "speaker “Greg G.”: 2027-03-17 is one of the skip_dates (no meeting that day) — left out",
    "speaker “Luke B.” (2027-07-21): no topic — shown without one",
    "speakers entry 10 (2027-05-19): the name must be a first name and a last initial, like \"Rick W.\" — left out",
]


class Speakers(Untranslated):
    def test_who_speaks_when_and_why_one_is_left_out(self):
        got, notes = M.meeting_speakers(yaml.safe_load(SPEAKER_CASES))
        self.assertEqual(got, {
            "2027-01-20": {"name": "Ann B.", "position": {"en": "Past delegate, Area 99", "es": "Ex delegada del Área 99"},
                           "topic": {"en": "How the Conference works", "es": "Cómo trabaja la Conferencia"},
                           "confirmed": True},
            "2027-04-21": {"name": "María José C.", "position": {"en": "Delegate", "es": "Delegate"},
                           "topic": {"en": "Solo en español", "es": "Solo en español"}, "confirmed": False},
            "2027-07-21": {"name": "Luke B.", "position": {"en": "", "es": ""}, "topic": {"en": "", "es": ""},
                           "confirmed": False}})              # (only `confirmed: true` is confirmed)
        self.assertEqual(notes, SPEAKER_NOTES)

    def test_the_list_itself(self):
        self.assertEqual(M.meeting_speakers({}), ({}, []))
        self.assertEqual(M.meeting_speakers({"speakers": []}), ({}, []))
        one, notes = M.meeting_speakers({"speakers": {"date": "2027-01-20", "name": "Ann B.", "topic": "T"}})
        self.assertEqual((list(one), notes), (["2027-01-20"], []))           # one, without the leading "- "
        self.assertEqual(M.meeting_speakers({"speakers": "Ann B."}),
                         ({}, ["speakers: not understood — it must be a list, each speaker starting with “- date:”"]))
        for name in ("Rick W.", "Mary Jo K.", "José Luis M.", "O’Neil P.", "Ana-María Ñ."):
            self.assertRegex(name, M.SPEAKER_NAME, name)
        for name in ("Rick Williams", "rick w.", "Rick W", "Rick W. Jr.", "R. W.", "A B C D E.", "Rick W. (Dallas)"):
            self.assertIsNone(M.SPEAKER_NAME.fullmatch(name), name)

    def test_until_when_the_speaker_talks(self):
        for v, want in (("19:30", ((19, 30), [])), (1170, ((19, 30), [])), ("7:30 PM", ((19, 30), [])), (None, (None, [])),
                        ("21:00", (None, ["speaker_until “21:00” is not a time between the meeting's start and end — not shown"])),
                        ("late", (None, ["speaker_until “late” is not a time between the meeting's start and end — not shown"])),
                        ("19:00", (None, ["speaker_until “19:00” is not a time between the meeting's start and end — not shown"]))):
            self.assertEqual(M.speaker_until({"start": "19:00", "end": "20:00", "speaker_until": v}), want, v)

    def test_each_committee_meeting_names_its_speaker(self):
        got = {e["id"][-10:]: e for e in B.committee_meetings(ctx_with())}
        dec, jan, feb = got["2026-12-16"], got["2027-01-20"], got["2027-02-17"]
        base = "Our monthly committee meeting on Google Meet. All AA members are welcome to attend. No registration required."
        self.assertEqual((dec["summary"], dec["extra"].get("speaker")), (base, None))      # Dec 16, 2026: no speaker
        self.assertEqual(jan["extra"]["speaker"], {
            "name": "Ann B.", "position": {"en": "Past delegate, Area 99", "es": "Ex delegada del Área 99"},
            "topic": {"en": "How the Conference works", "es": "Cómo trabaja la Conferencia"}})        # never "confirmed"
        self.assertEqual(jan["i18n"]["summary"], {
            "en": base + " Guest speaker: Ann B. — “How the Conference works”. The guest speaker's part ends by 7:30 PM; "
                         "committee business follows until 8:00 PM.",
            "es": "Nuestra reunión mensual del comité por Google Meet. Todos los miembros de AA pueden asistir. No hace "
                  "falta registrarse. Orador(a) invitado(a): Ann B. — “Cómo trabaja la Conferencia”. La charla de la "
                  "persona invitada termina a más tardar a las 7:30 p. m.; luego, hasta las "
                  "8:00 p. m., siguen los asuntos del comité."})
        self.assertEqual(feb["extra"]["speaker"]["position"], {"en": "Delegate, Area 98", "es": "Delegate, Area 98"})
        # the title, the times and the id as without a speaker; joining: the Meet link and code, no passcode
        for e in (dec, jan):
            self.assertEqual(e["title"], "NETA 65 Grapevine & La Viña Committee Meeting")
            self.assertEqual((e["extra"]["online_url"], e["extra"]["meeting_id"], e["extra"]["passcode"],
                              e["extra"]["location"]), (ROOM, "abc-defg-hij", None, "Google Meet"))
        self.assertEqual((jan["extra"]["start"], jan["extra"]["end"]), ("2027-01-21T01:00:00Z", "2027-01-21T02:00:00Z"))
        self.assertNotIn("confirmed", json.dumps(list(got.values())))

    def test_an_older_zoom_url_still_counts(self):
        cfg = yaml.safe_load(YAML)
        cfg["meeting"].update(platform="Zoom", meeting_id="949 476 7497", passcode="neta65")
        cfg["meeting"]["zoom_url"] = cfg["meeting"].pop("online_url").replace(ROOM, "https://us02web.zoom.us/j/9494767497")
        e = B.committee_meetings(ctx_with(cfg))[0]["extra"]
        self.assertEqual((e["online_url"], e["passcode"]), ("https://us02web.zoom.us/j/9494767497", "neta65"))

    def test_the_notes_reach_status_json(self):
        cfg = yaml.safe_load(YAML)
        cfg["meeting"].update(yaml.safe_load(SPEAKER_CASES))
        ctx = ctx_with(cfg)
        with mock.patch.object(B, "ics_events", lambda c: []):
            B.build_events(ctx)
        self.assertEqual(ctx.raw_problems["meeting"], ("config/site.yml meeting: " + "; ".join(SPEAKER_NOTES))[:2000])

    def test_the_chair_is_reminded_of_a_speaker_not_confirmed(self):
        ctx = ctx_with()
        for today, want in (("2027-01-02", []), ("2027-01-03", ["2027-02-17"]), ("2027-02-17", ["2027-02-17"]),
                            ("2027-02-18", []), ("2026-12-10", [])):
            got = B._speaker_reminders(ctx, ROOT, date.fromisoformat(today))
            self.assertEqual([r["due"] for r in got], want, today)
        self.assertEqual(B._speaker_reminders(ctx, ROOT, date(2027, 1, 3)), [{
            "id": "speaker:2027-02-17", "file": "config/site.yml", "due": "2027-02-17",
            "message": "config/site.yml meeting: the guest speaker for 2027-02-17 (Carlos D.) is not confirmed yet — once "
                       "they say yes, set confirmed: true (or change the speaker)."}])
        self.assertIn(B._speaker_reminders, B.REMINDER_CHECKS)

    def test_the_words_are_the_pages(self):
        words = json.loads((ROOT / "src" / "_i18n" / "committee.json").read_text(encoding="utf-8"))
        self.assertEqual(B._SPEAKER, words["committee.meeting.speaker"])
        self.assertEqual(B._SPEAKER_UNTIL, words["committee.meeting.speaker_until"])


SPEAKERS_JS = r"""
const yaml = await import("js-yaml");
const C = await imp("eleventy/filters/committee.js");
const W = await imp("eleventy/build-warnings.js");
W.clearBuildWarnings();
const cases = yaml.load(input.cases);
const list = C.meetingSpeakers(cases);
const notes = C.meetingSpeakerNotes(cases);
const warned = W.buildWarnings();                           // the chair's notes: never a build warning
const until = input.until.map((v) => C.meetingSpeakerUntil({ start: "19:00", end: "20:00", speaker_until: v }));
out({ list, notes, warned, until, one: C.meetingSpeaker(cases, "2027-01-20", "es"), none: C.meetingSpeaker(cases, "2026-12-16", "en") });
"""

EVENTS_JS = r"""
const yaml = await import("js-yaml");
const C = await imp("eleventy/filters/committee.js");
const cfg = yaml.load(input.yaml);
const site = { ...cfg.site, meeting: cfg.meeting };
const at = new Date("2026-11-26T18:00:00Z");
const pick = (lang) => C.normalizeEvents([], site, lang, { now: at, monthsBack: 0, monthsAhead: 3 }).filter((e) => e.committee);
const en = pick("en"), es = pick("es");
const ics = C.buildIcs(en, { name: "x", lang: "en", url: "https://example.org/gv/events/", now: at, alarms: true });
out({
  en: en.map((e) => ({ ymd: e.startYmd, uid: e.uid, title: e.title, start: e.startIso, end: e.endIso, summary: e.summary,
                       desc: e.calDescription, speaker: e.speaker, gcal: e.gcal })),
  es: es.map((e) => ({ ymd: e.startYmd, summary: e.summary, desc: e.calDescription, speaker: e.speaker })),
  alarms: ics.split(/\r?\n/).filter((l) => l.startsWith("DESCRIPTION:") && !/\\n/.test(l)),
  ld: JSON.stringify(C.eventLd(en, site, "en")),
});
"""


class SpeakersOnPages(unittest.TestCase):
    def test_the_pages_read_them_like_the_sync(self):
        until = ["19:30", 1170, "21:00", "late", None, ""]
        got = run_js(self, SPEAKERS_JS, data={"cases": SPEAKER_CASES, "until": until})
        py, notes = M.meeting_speakers(yaml.safe_load(SPEAKER_CASES))
        self.assertEqual({s["ymd"]: {k: s[k] for k in ("name", "position", "topic", "confirmed")} for s in got["list"]}, py)
        self.assertEqual(got["notes"], notes)
        self.assertEqual(got["warned"], [], "a slip in the settings never fails a build")
        self.assertEqual(got["until"], [f"{t[0]:02d}:{t[1]:02d}" if t else ""
                                        for t, _ in (M.speaker_until({"start": "19:00", "end": "20:00", "speaker_until": v})
                                                     for v in until)])
        self.assertEqual(got["one"], {"ymd": "2027-01-20", "name": "Ann B.", "position": "Ex delegada del Área 99",
                                      "topic": "Cómo trabaja la Conferencia"})      # never `confirmed`
        self.assertIsNone(got["none"])

    def test_each_meeting_with_its_speaker_in_the_calendars(self):
        got = run_js(self, EVENTS_JS, data={"yaml": YAML}, now="2026-11-26T18:00:00Z")
        by = {e["ymd"]: e for e in got["en"]}
        dec, jan = by["2026-12-16"], by["2027-01-20"]
        # Dec 16, 2026: no speaker
        self.assertIsNone(dec["speaker"])
        self.assertNotIn("Guest speaker", dec["desc"] + dec["summary"])
        self.assertEqual(jan["speaker"], {"name": "Ann B.", "position": "Past delegate, Area 99", "topic": "How the Conference works"})
        self.assertTrue(jan["summary"].endswith(
            "committee meeting on Google Meet. All AA members are welcome to attend. No registration required. Guest "
            "speaker: Ann B. — “How the Conference works”. The guest speaker's part ends by 7:30 PM; committee business "
            "follows until 8:00 PM."), jan["summary"])
        self.assertIn("\n\nGuest speaker: Ann B. — Past delegate, Area 99\nTopic: “How the Conference works”\nThe guest "
                      "speaker's part ends by 7:30 PM; committee business follows until 8:00 PM.\n\nJoin on Google Meet: "
                      f"{ROOM}\nMeeting code: abc-defg-hij\n\nDetails: https://example.org/gv/meetings/", jan["desc"])
        # the same title, times and calendar uid with or without a speaker
        self.assertEqual((jan["uid"], jan["title"], jan["start"], jan["end"]),
                         ("ev-committee-2027-01-20", dec["title"], "2027-01-21T01:00:00.000Z", "2027-01-21T02:00:00.000Z"))
        self.assertIn("Ann%20B.", jan["gcal"])
        es = {e["ymd"]: e for e in got["es"]}["2027-01-20"]
        self.assertIn("Orador(a) invitado(a): Ann B. — Ex delegada del Área 99\nTema: “Cómo trabaja la Conferencia”\nLa charla "
                      "de la persona invitada termina a más tardar a las 7:30 p. m.; luego, hasta las "
                      "8:00 p. m., siguen los asuntos del comité.", es["desc"])
        # never in a calendar alarm (the title alone), never in what search engines read (no committee meeting there)
        self.assertTrue(got["alarms"])
        for line in got["alarms"]:
            self.assertNotIn("Ann", line)
        self.assertNotIn("Ann B.", got["ld"])
        self.assertNotIn("committee-meeting", got["ld"])

    def test_the_home_page_and_the_countdown_get_each_dates_speaker(self):
        tmp = Path(self._tmp())
        (tmp / "config").mkdir()
        (tmp / "config" / "site.yml").write_text("meeting:" + YAML.split("meeting:", 1)[1].split("recurring_events:")[0],
                                                 encoding="utf-8")
        got = run_js(self, """
            const meetingData = (await imp("src/_data/meeting.js")).default;
            const here = process.cwd();
            process.chdir(input);
            try { out(meetingData().upcoming.slice(0, 3)); } finally { process.chdir(here); }
        """, data=str(tmp), now="2026-11-26T18:00:00Z")
        self.assertEqual([sorted(d) for d in got], [["end", "start", "ymd"], ["end", "speaker", "start", "ymd"],
                                                    ["end", "speaker", "start", "ymd"]])
        self.assertEqual(got[1]["speaker"], {"name": "Ann B.", "position": {"en": "Past delegate, Area 99", "es": "Ex delegada del Área 99"},
                                             "topic": {"en": "How the Conference works", "es": "Cómo trabaja la Conferencia"}})

    def _tmp(self) -> str:
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="gv-r20-")
        self.addCleanup(shutil.rmtree, d, True)
        return d


# =========================================================================== the flyers on the Drive
class Flyers(Untranslated):
    def test_the_names_the_committee_gives_them(self):
        cfg = yaml.safe_load(YAML)
        meeting = B._flyer_pattern(cfg["meeting"]["flyer_match"])[0]
        series = B._flyer_pattern(cfg["recurring_events"][0]["flyer_match"])[0]
        for (folder, name), want in FLYER_NAMES.items():
            it = next(i for i in drive_items() if i["extra"]["name"] == name)
            found = [k for k, p in (("meeting", meeting), ("series", series)) if B._flyer_matches(p, it)]
            # (the committee meeting's slides carry its name: the flyers/ folder only)
            if folder != "flyers":
                found = [k for k in found if k != "meeting"]
            self.assertEqual(found, [want] if want else [], name)
        # a month alone in the name is that month (drive.py: event_month) — never a day, so never an event
        months = {i["extra"]["name"]: i["extra"].get("event_month") for i in drive_items()}
        self.assertEqual(months["January 2027 Committee Meeting - guest speaker.png"], "2027-01")
        self.assertEqual(months["December 2027 Committee Meeting - guest speaker.png"], "2027-12")
        self.assertEqual([i for i in drive_items() if i["extra"].get("event_date")], [])
        self.assertEqual(B.flyer_events(ctx_with(drive=drive_items())), [])

    def test_only_the_flyers_folder(self):
        ctx = ctx_with(drive=drive_items())
        loose = re.compile("committee meeting", re.I)
        self.assertIn("Grapevine and La Viña Monthly Committee Meeting.pptx",
                      [i["extra"]["name"] for i in drive_items() if i["id"] in {f["id"] for f in B.series_flyers(ctx, loose)}])
        self.assertNotIn("slides", {i["category"] for i in drive_items()
                                    if i["id"] in {f["id"] for f in B.series_flyers(ctx, loose, category="flyers")}})

    def test_each_meeting_its_flyer(self):
        ctx = ctx_with(drive=drive_items())
        with mock.patch.object(B, "ics_events", lambda c: []):
            evs = {e["id"]: e for e in B.build_events(ctx)}
        name = {i["extra"]["view_url"]: i["extra"]["name"] for i in drive_items()}
        flyer = lambda eid: name.get(evs[eid]["extra"]["flyer_url"])   # noqa: E731
        self.assertEqual(flyer("ev:committee:2026-12-16"), "Committee Meeting - flyer.png")
        self.assertEqual(flyer("ev:committee:2027-01-20"), "January 2027 Committee Meeting - guest speaker.png")
        self.assertEqual(flyer("ev:committee:2027-02-17"), "February 2027 Committee Meeting - guest speaker.png")
        self.assertEqual(flyer("ev:recurring:grapevine-meeting:2026-12-02"), "Grapevine Meeting - flyer.png")
        self.assertEqual([e for e in evs.values() if e["category"] == "flyer"], [])           # no second event
        self.assertNotIn("meeting", ctx.raw_problems)
        # the pages compute the meetings themselves (normalizeEvents) and show the flyer the sync found for each date
        got = run_js(self, """
            const yaml = await import("js-yaml");
            const C = await imp("eleventy/filters/committee.js");
            const cfg = yaml.load(input.yaml);
            const evs = C.normalizeEvents(input.items, { ...cfg.site, meeting: cfg.meeting }, "en",
              { now: new Date("2026-11-26T18:00:00Z"), monthsBack: 0, monthsAhead: 3 });
            out(evs.filter((e) => e.committee).map((e) => [e.startYmd, e.flyer && e.flyer.view]));
        """, data={"items": list(evs.values()), "yaml": YAML})
        self.assertEqual({ymd: name.get(view) for ymd, view in got if ymd in ("2026-12-16", "2027-01-20")},
                         {"2026-12-16": "Committee Meeting - flyer.png",
                          "2027-01-20": "January 2027 Committee Meeting - guest speaker.png"})

    def test_a_flyer_named_with_its_day(self):
        """A day in the name makes a flyer an event (drive.py): on a meeting's own day it is that meeting's flyer, not
        a second event; on another day it stays one."""
        names = {("flyers", "Committee Meeting - flyer.png"): "meeting",
                 ("flyers", "2027-01-20 Committee Meeting - guest speaker.png"): "meeting",
                 ("flyers", "2027-01-23 Committee Meeting - guest speaker.png"): "meeting"}
        items = drive_items(names)
        ctx = ctx_with(drive=items)
        with mock.patch.object(B, "ics_events", lambda c: []):
            evs = {e["id"]: e for e in B.build_events(ctx)}
        by_name = {i["extra"]["name"]: i for i in items}
        self.assertEqual(evs["ev:committee:2027-01-20"]["extra"]["flyer_url"],
                         by_name["2027-01-20 Committee Meeting - guest speaker.png"]["extra"]["view_url"])
        self.assertEqual(sorted(e["id"] for e in evs.values() if e["category"] == "flyer"),
                         [f"ev:flyer:{by_name['2027-01-23 Committee Meeting - guest speaker.png']['extra']['file_id']}"])


# =========================================================================== one Google Meet room, two meetings
def listing(day: str, title: str, start: str = "01:00", room: str = ROOM) -> dict:
    """An event of Grapevine's calendar (or a feed) in an online room: the day is its Central day (the evening)."""
    d = date.fromisoformat(day)
    nxt = date.fromordinal(d.toordinal() + 1).isoformat()
    return {"id": f"ev:gvcal:{day}-{re.sub(r'[^a-z]+', '-', title.lower())}", "category": "gv-calendar", "source": "calendar",
            "kind": "event", "title": title, "url": f"https://example.org/events/{day}",
            "extra": {"start": f"{nxt}T{start}:00Z", "end": f"{nxt}T02:00:00Z", "online_url": room}}


class SharedRoom(Untranslated):
    """The committee meeting (3rd Wednesday) and the Grapevine Meeting (1st Wednesday) share one Google Meet room: a
    listing in that room is the Grapevine Meeting only when it names it, on a day that is not the committee
    meeting's — the committee meeting as a calendar lists it, or a workshop in the room, never reads as a moved
    Grapevine Meeting (series_listing_notes, series_moved_dates)."""

    def run_with(self, listings, skip=()):
        text = YAML.replace("    skip_dates: []\n", f"    skip_dates: {json.dumps(list(skip))}\n")
        ctx = ctx_with(text)
        recurring = B.recurring_events(ctx)
        notes = B.series_listing_notes(ctx, listings, recurring)
        moved = B.series_moved_dates(ctx, listings, recurring)
        return notes, moved

    def test_the_committee_meeting_and_a_workshop_in_the_room(self):
        committee = listing("2027-01-20", "NETA 65 Grapevine & La Viña Committee Meeting")
        workshop = listing("2027-01-09", "Online Writing Workshop")
        self.assertEqual(self.run_with([committee, workshop]), ([], 0))
        # …also in a month the series skips: neither becomes that month's Grapevine Meeting
        before = json.dumps([committee, workshop])
        self.assertEqual(self.run_with([committee, workshop], skip=["2027-01-06"]), ([], 0))
        self.assertEqual(json.dumps([committee, workshop]), before, "the listings are left as they are")

    def test_a_grapevine_meeting_on_another_day_is_still_one(self):
        moved = listing("2027-01-13", "Grapevine Meeting")
        notes, n = self.run_with([moved])
        self.assertEqual(notes, ["recurring_events entry 1 (grapevine-meeting): Grapevine's calendar (aagrapevine.org) "
                                 "lists it on 2027-01-13 (https://example.org/events/2027-01-13), but the rule gives "
                                 "2027-01-06 — if that month's date moved, add \"2027-01-06\" to its skip_dates (the "
                                 "calendar's own listing stays on the Events page)"])
        notes, n = self.run_with([moved], skip=["2027-01-06"])
        self.assertEqual((notes, n, moved["title"]), ([], 1, "Grapevine Meeting (online)"))
        # …but not on the committee meeting's own day, whatever its title
        self.assertEqual(self.run_with([listing("2027-01-20", "Grapevine Meeting")]), ([], 0))

    def test_a_room_of_its_own_is_as_before(self):
        # the committee meeting elsewhere (Zoom): any listing in the series' room is the series, as for La Viña's
        cfg = yaml.safe_load(YAML)
        cfg["meeting"].update(online_url="https://us02web.zoom.us/j/9494767497", meeting_id="949 476 7497")
        ctx = ctx_with(cfg)
        recurring = B.recurring_events(ctx)
        notes = B.series_listing_notes(ctx, [listing("2027-01-20", "NETA 65 Grapevine & La Viña Committee Meeting")], recurring)
        self.assertEqual(len(notes), 1)


# =========================================================================== joining, on the pages
class Joining(Untranslated):
    def test_a_series_card_says_meeting_code_and_search_engines_get_no_room(self):
        recurring = B.recurring_events(ctx_with())
        hybrid = {"id": "ev:manual:zz-meet", "source": "committee", "kind": "event", "category": "manual", "url": "",
                  "title": "Grapevine Writing Workshop", "lang": "en", "date": "2027-01-09T19:00:00Z", "status": "ok",
                  "summary": f"Come in person or join on Google Meet: {ROOM} (meeting code abc-defg-hij). "
                             "Código de la reunión: abc-defg-hij. Coffee at 1 PM.",
                  "extra": {"start": "2027-01-09T19:00:00Z", "end": "2027-01-09T21:00:00Z", "slug": "zz-meet",
                            "location": "Grupo Seis, 6 Elm St, Tyler, TX 75701", "city": "Tyler", "state": "TX",
                            "online_url": ROOM, "platform": "Google Meet"}}
        got = run_js(self, """
            const C = await imp("eleventy/filters/committee.js");
            const evs = C.normalizeEvents(input.items, input.site, "en", { now: new Date("2026-11-26T18:00:00Z"), monthsBack: 0, monthsAhead: 0 });
            const gvm = evs.find((e) => e.series === "grapevine-meeting");
            out({ key: gvm.meetingIdKey, desc: gvm.calDescription, link: gvm.link, ld: C.eventLd(evs, input.site, "en") });
        """, data={"items": recurring + [hybrid], "site": {"url": "https://example.org/gv"}}, now="2026-11-26T18:00:00Z")
        self.assertEqual(got["key"], "committee.meeting.code")
        self.assertIn(f"Online on Google Meet: {ROOM}\nMeeting code: abc-defg-hij\nContact: grapevine@example.org", got["desc"])
        self.assertEqual(got["link"], "/meetings/#grapevine-meeting")
        self.assertEqual([e["name"] for e in got["ld"]], ["Grapevine Writing Workshop"])     # the online-only series: none
        self.assertEqual(got["ld"][0]["description"], "Coffee at 1 PM.")
        self.assertNotIn("abc-defg-hij", json.dumps(got["ld"]))


# =========================================================================== config/site.yml as it is (CONTENT_TESTS)
class RealSettings(unittest.TestCase):
    """config/site.yml as the committee keeps it (scripts/ops/gate_tests.py CONTENT_TESTS): our Grapevine Meeting on
    the first Wednesday in the committee meeting's Google Meet room from Dec 2, 2026; the CityWide booth 5:30–7:30 PM
    at Lovers Lane; the 12 guest speakers of 2027 on the 3rd Wednesdays, by first name and last initial; the flyer
    names of the Drive found by the right setting."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        cls.meeting = cls.cfg["meeting"]
        ctx = B.Ctx(offline=True)
        ctx.cfg = cls.cfg
        cls.specs, cls.problems = B.recurring_specs(ctx)

    def test_the_committee_meeting_on_google_meet(self):
        m = self.meeting
        self.assertEqual(m["platform"], "Google Meet")
        self.assertRegex(m["online_url"], r"^https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}$")
        self.assertEqual(m["meeting_id"], m["online_url"].rsplit("/", 1)[1])
        for k in ("zoom_url", "passcode"):
            self.assertNotIn(k, m)
        self.assertNotIn("committee", self.cfg["phone_access"])
        self.assertEqual(B.meeting_notes(m), [])

    def test_the_grapevine_meeting(self):
        sp = next(s for s in self.specs if s["key"] == "grapevine-meeting")
        self.assertEqual((sp["rule"].week_of_month, sp["rule"].weekday, sp["rule"].span(), sp["rule"].starts),
                         (1, 2, ((19, 0), (20, 0)), "2026-12-02"))
        self.assertEqual(date.fromisoformat(sp["rule"].starts).weekday(), 2)
        self.assertEqual((sp["online_url"], sp["meeting_id"], sp["platform"], sp["host"], sp["location"], sp["url"]),
                         (self.meeting["online_url"], self.meeting["meeting_id"], "Google Meet", "neta", None,
                          "/meetings/#grapevine-meeting"))
        self.assertEqual(sp["title"], ("Grapevine Meeting (online)", "Reunión de Grapevine (en línea)"))
        self.assertFalse([p for p in self.problems if "grapevine-meeting" in p], self.problems)
        self.assertNotRegex(json.dumps(self.cfg, ensure_ascii=False, default=str), r"(?i)hosted by")

    def test_the_citywide_booth(self):
        sp = next(s for s in self.specs if s["key"] == "citywide-dallas")
        self.assertEqual(sp["rule"].span(), ((17, 30), (19, 30)))
        entry = next(e for e in self.cfg["recurring_events"] if e.get("key") == "citywide-dallas")
        for k in ("location", "summary", "summary_es"):
            self.assertIn("Lovers Lane", entry[k], k)
            self.assertNotIn("Lover's", entry[k], k)

    def test_the_guest_speakers_of_2027(self):
        speakers, notes = M.meeting_speakers(self.meeting)
        self.assertEqual(notes, [])
        self.assertEqual(len(speakers), 12)
        self.assertEqual(sorted(speakers), [M.nth_weekday(2027, mo, 2, 3).isoformat() for mo in range(1, 13)])
        self.assertNotIn("2026-12-16", speakers)
        for ymd, s in speakers.items():
            with self.subTest(ymd=ymd):
                self.assertRegex(s["name"], M.SPEAKER_NAME)
                self.assertTrue(all(s["position"].values()) and all(s["topic"].values()))
                self.assertNotEqual(s["topic"]["en"], s["topic"]["es"])
                self.assertNotRegex(json.dumps(s, ensure_ascii=False), r"@|\+?\d{3}[ .-]\d{3}[ .-]\d{4}|A\.A\.")
        self.assertEqual(M.speaker_until(self.meeting), ((19, 30), []))

    def test_the_flyer_names(self):
        meeting = B._flyer_pattern(self.meeting["flyer_match"])[0]
        series = B._flyer_pattern(next(e for e in self.cfg["recurring_events"]
                                       if e.get("key") == "grapevine-meeting")["flyer_match"])[0]
        others = [B._flyer_pattern(e.get("flyer_match"))[0] for e in self.cfg["recurring_events"]
                  if e.get("key") != "grapevine-meeting" and e.get("flyer_match")]
        others.append(B._flyer_pattern(self.cfg["lavina_weekly_open"]["flyer_match"])[0])
        for it in drive_items():
            folder, name = it["category"], it["extra"]["name"]
            want = FLYER_NAMES[(folder, name)]
            found = [k for k, p in (("meeting", meeting), ("series", series)) if B._flyer_matches(p, it)]
            found = [k for k in found if folder == "flyers" or k != "meeting"]
            self.assertEqual(found, [want] if want else [], name)
            self.assertFalse(any(B._flyer_matches(p, it) for p in others), name)


if __name__ == "__main__":
    unittest.main()
