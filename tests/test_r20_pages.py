"""Round 20 — the pages of our meetings on Google Meet: /meetings/, the home page, /events/ and /share/ (English and
Spanish), with the committee meeting's guest speakers and our new Grapevine Meeting:

  * how the evening runs (eleventy/filters/committee.js meetingEvening — cmEvening): the opening, about 2 minutes
    later the guest speaker's talk, about 20 minutes later the questions, from `speaker_until` the events, offers,
    magazine topics and sharing (never "committee business": it is not a business meeting), the close at the end,
    then the parking lot — the times from the settings; without a speaker a topic to share on (its second step,
    "Guest speaker": most months a speaker, done by speaker_until; without one the chair's topic), then the same
    second half;
  * the speakers to come (meetingSpeakerDates — cmSpeakers): each with that meeting's calendar text, word for word
    the one /events/ and /events.ics give it, and the text of a meeting without one; a meeting that is over drops off;
  * one of our monthly series from the settings (seriesNext — cmSeriesNext): the Grapevine Meeting's own section
    works while data/site/events.json does not list it yet, with the dates, calendar text and calendar UID the sync's
    record gets (build_data.recurring_events) — events.json's own record when it has the date (its flyer); the
    platform its link names (platformOf, the sync's events_external.platform_of);
  * the countdowns in the browser (src/assets/js/committee.js cmMeeting, home.js homeMeeting): once a meeting is
    over they roll on to the next date WITH that date's guest speaker — or none — and calendar text; a series' card
    gives the feed's UID; "Starting soon" only the last 5 minutes (the room opens a few minutes before we start);
  * the built pages, at a fixed clock, on settings of the test's own (two speakers, a Grapevine Meeting in the
    committee meeting's room): Nov 26, 2026 (the next committee meeting, Dec 16, has no speaker; the Grapevine
    Meeting's first date is Dec 2) and Dec 17, 2026 (the next, Jan 20, has one);
  * the Grapevine Meeting is ours (event-tone.js): its card says NETA 65, never Grapevine's name for its badge.

    python -m unittest tests.test_r20_pages -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from nodejs import run_js  # noqa: E402
from test_central_time import DOM, plain  # noqa: E402  (the browser stand-in: page(), el())
from test_r20_meeting import NOW, ROOM, YAML, Untranslated, ctx_with  # noqa: E402  (the settings of round 20's tests)
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import events_external as X  # noqa: E402

NOV26 = "2026-11-26T18:00:00Z"       # the merge day: the next committee meeting (Dec 16) has no guest speaker
DEC17 = "2026-12-17T18:00:00Z"       # the next one (Jan 20) has: Ann B.

# the settings as the pages read them (src/_data/site.js: the committee meeting's platform and link filled in)
SITE_JS = r"""
const yaml = await import("js-yaml");
const C = await imp("eleventy/filters/committee.js");
const cfg = yaml.load(input.yaml);
const site = { ...cfg.site, meeting: { ...cfg.meeting, online_url: cfg.meeting.online_url || "" }, recurring_events: cfg.recurring_events };
"""


# =========================================================================== how the evening runs
class Evening(unittest.TestCase):
    def test_the_times_come_from_the_settings(self):
        got = run_js(self, SITE_JS + r"""
            const ev = (m, lang) => C.meetingEvening(m, lang);
            out({ en: ev(site.meeting, "en"), es: ev(site.meeting, "es"),
                  late: ev({ ...site.meeting, start: "18:30", end: "20:00", speaker_until: "19:15" }, "en"),
                  short: ev({ ...site.meeting, speaker_until: "19:20" }, "en"),
                  none: ev({ ...site.meeting, speaker_until: "" }, "en"), filter: filters.cmEvening(site.meeting, "en") });
        """, data={"yaml": YAML})
        rows = lambda e: [(r["key"], plain(r["at"]), r["about"]) for r in e["speaker"]]     # noqa: E731
        self.assertEqual(rows(got["en"]), [("opening", "7:00 PM", False), ("talk", "7:02 PM", True),
                                           ("questions", "7:22 PM", True), ("sharing", "7:30 PM", False),
                                           ("close", "8:00 PM", False)])
        self.assertEqual((plain(got["en"]["until"]), plain(got["en"]["end"]), got["en"]["talkMin"]), ("7:30 PM", "8:00 PM", 20))
        self.assertEqual([plain(r["at"]) for r in got["es"]["speaker"]], ["7:00 p. m.", "7:02 p. m.", "7:22 p. m.", "7:30 p. m.", "8:00 p. m."])
        # another start and speaker_until: the times follow
        self.assertEqual(rows(got["late"]), [("opening", "6:30 PM", False), ("talk", "6:32 PM", True),
                                             ("questions", "6:52 PM", True), ("sharing", "7:15 PM", False),
                                             ("close", "8:00 PM", False)])
        # questions that would start at or after speaker_until are left out
        self.assertEqual([r[0] for r in rows(got["short"])], ["opening", "talk", "sharing", "close"])
        # no speaker_until: no speaker's evening; the hour of a night without a speaker stays
        self.assertEqual(got["none"]["speaker"], [])
        self.assertEqual([(r["key"], plain(r["at"])) for r in got["en"]["plain"]], [("topic_hour", "7:00 – 8:00 PM")])
        self.assertEqual(got["filter"], got["en"])


# =========================================================================== the speakers to come
class SpeakerDates(unittest.TestCase):
    def test_each_with_its_meetings_calendar_text(self):
        got = run_js(self, SITE_JS + r"""
            const at = new Date(input.now);
            const evs = C.normalizeEvents([], site, "es", { now: at, monthsBack: 0, monthsAhead: 4 }).filter((e) => e.committee);
            out({ es: C.meetingSpeakerDates(site, "es", at), en: C.meetingSpeakerDates(site, "en", at),
                  later: C.meetingSpeakerDates(site, "en", new Date("2027-01-21T02:30:00Z")).list.map((s) => s.ymd),
                  feed: Object.fromEntries(evs.map((e) => [e.startYmd, e.calDescription])),
                  filter: filters.cmSpeakers(site, "en") });
        """, data={"yaml": YAML, "now": NOV26}, now=NOV26)
        es = got["es"]["list"]
        self.assertEqual([s["ymd"] for s in es], ["2027-01-20", "2027-02-17"])
        self.assertEqual({k: es[0][k] for k in ("name", "position", "topic", "start", "end")},
                         {"name": "Ann B.", "position": "Ex delegada del Área 99", "topic": "Cómo trabaja la Conferencia",
                          "start": "2027-01-21T01:00:00.000Z", "end": "2027-01-21T02:00:00.000Z"})
        self.assertNotIn("confirmed", es[0])
        # that date's calendar text is the feed's own; a meeting without a speaker has the plain one
        self.assertEqual(es[0]["description"], got["feed"]["2027-01-20"])
        self.assertEqual(got["es"]["plain"], got["feed"]["2026-12-16"])
        self.assertNotIn("Ann", got["es"]["plain"])
        self.assertEqual(got["en"]["list"][1]["topic"], "Grapevine as a tool")
        # Jan 20's meeting is over: it drops off
        self.assertEqual(got["later"], ["2027-02-17"])
        self.assertEqual(got["filter"]["list"][0]["ymd"], "2027-01-20")


# =========================================================================== a series of ours, from the settings
SERIES_JS = SITE_JS + r"""
const at = new Date(input.now);
const synced = input.items;
const fromSync = (lang) => C.normalizeEvents(synced, site, lang, { now: at, monthsBack: 0, monthsAhead: 0 }).filter((e) => e.recurring);
const pick = (e) => ({ id: e.id, uid: e.uid, title: e.title, summary: e.summary, start: e.startIso, end: e.endIso, desc: e.calDescription,
                       loc: e.calLocation, gcal: e.gcal, outlook: e.outlook, ics: e.icsData, details: e.detailsUrl, platform: e.platform,
                       code: e.meetingId, codeKey: e.meetingIdKey, contact: e.contact, flyer: e.flyer });
const S = (lang, items) => C.seriesNext(site, "grapevine-meeting", lang, items, { now: at });
const en = S("en", []), es = S("es", []), withData = S("en", input.withFlyer);
out({
  en: { ...en, next: pick(en.next), dates: en.dates.map(pick) }, es: { ...es, next: pick(es.next), dates: es.dates.map(pick) },
  syncEn: fromSync("en").map(pick), syncEs: fromSync("es").map(pick),
  flyer: withData.next.flyer, none: S("en", []) && C.seriesNext(site, "no-such-series", "en", [], { now: at }),
  later: S("en", []) && C.seriesNext(site, "grapevine-meeting", "en", [], { now: new Date("2026-12-03T03:00:00Z") }).next.startIso,
  filter: filters.cmSeriesNext(site, "grapevine-meeting", "en", []).key,
  platforms: input.urls.map((u) => C.platformOf(u)),
});
"""


class SeriesFromTheSettings(Untranslated):
    def run_series(self):
        items = B.recurring_events(ctx_with())
        flyer = json.loads(json.dumps(items))
        flyer[0]["extra"]["flyer_url"] = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view"
        urls = ["https://meet.google.com/abc-defg-hij", "https://us06web.zoom.us/j/81595931777", "https://teams.live.com/meet/1",
                "https://example.org/room", "", "not a link"]
        got = run_js(self, SERIES_JS, data={"yaml": YAML, "now": NOV26, "items": items, "withFlyer": flyer, "urls": urls}, now=NOV26)
        return got, urls

    def test_the_dates_and_calendar_text_are_the_syncs(self):
        got, _ = self.run_series()
        for lang in ("en", "es"):
            mine, sync = got[lang], got["sync" + lang.capitalize()]
            with self.subTest(lang=lang):
                # the next 4 dates, from the first date on (Dec 2, 2026), exactly as the sync's records make them
                self.assertEqual([d["id"][-10:] for d in mine["dates"]], ["2026-12-02", "2027-01-06", "2027-02-03", "2027-03-03"])
                self.assertEqual(mine["dates"], sync[:4])
                self.assertEqual(mine["next"]["uid"], "ev-recurring-grapevine-meeting-2026-12-02")
                self.assertEqual(mine["uidPrefix"], "ev-recurring-grapevine-meeting-")
                self.assertEqual(mine["next"]["ics"]["uid"], "ev-recurring-grapevine-meeting-2026-12-02" + ("-es" if lang == "es" else "")
                                 + "@neta65-gvlv")
        en = got["en"]
        self.assertEqual((en["title"], en["starts"], en["rule"]), ("Grapevine Meeting", "2026-12-02",
                         {"weekday": 3, "n": 1, "start": "19:00", "end": "20:00", "skip": [], "starts": "2026-12-02"}))
        self.assertEqual((en["recurrenceDay"], plain(en["time"]), plain(en["end"])), ("Every first Wednesday of the month", "7:00 – 8:00 PM", "8:00 PM"))
        self.assertEqual((en["join"]["platform"], en["join"]["url"], en["join"]["idLabel"], en["join"]["copyId"], en["join"]["dialIn"]),
                         ("Google Meet", ROOM, "Meeting code", "abc-defg-hij", False))
        self.assertEqual((en["contact"], en["next"]["details"]), ("grapevine@example.org", "https://example.org/gv/meetings/#grapevine-meeting"))
        self.assertEqual(got["es"]["title"], "Reunión de Grapevine (en inglés)")
        # the Spanish title names its language: the pages add no "En inglés" of their own
        self.assertEqual((en["saysLang"], got["es"]["saysLang"]), (False, True))
        self.assertIn("Meeting code: abc-defg-hij", en["next"]["desc"])
        self.assertIn("Every first Wednesday of the month · 7:00 – 8:00 PM Central time", plain(en["next"]["desc"]))

    def test_events_json_record_wins_and_the_rest(self):
        got, urls = self.run_series()
        self.assertEqual(got["flyer"]["view"], "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view")
        self.assertIsNone(got["en"]["next"]["flyer"])             # from the settings alone: no flyer to show
        self.assertIsNone(got["none"])
        self.assertEqual(got["later"], "2027-01-07T01:00:00.000Z")  # Dec 2 is over: Jan 6
        self.assertEqual(got["filter"], "grapevine-meeting")
        # the platform a link names: the sync's own table, word for word
        self.assertEqual(got["platforms"], [X.platform_of(u) if u else None for u in urls[:4]] + [None, None])

    def test_the_platform_table_is_the_syncs(self):
        src = (ROOT / "eleventy" / "filters" / "committee.js").read_text(encoding="utf-8")
        table = src[src.index("const PLATFORM_HOSTS = {"):]
        table = table[table.index("{"):table.index("};") + 1]
        self.assertEqual(json.loads(re.sub(r'([{,]\s*)"?([\w.-]+)"?\s*:', r'\1"\2":', table)), X.PLATFORM_HOSTS)


# =========================================================================== the countdowns in the browser
class Countdowns(unittest.TestCase):
    SPEAKERS = [
        {"ymd": "2027-01-20", "name": "Ann B.", "position": "Past delegate, Area 99", "topic": "How the Conference works",
         "description": "JAN TEXT"},
        {"ymd": "2027-02-17", "name": "Carlos D.", "position": "Delegate, Area 98", "topic": "Grapevine as a tool",
         "description": "FEB TEXT"},
    ]

    def test_the_committee_countdown_rolls_on_with_each_dates_speaker(self):
        r = run_js(self, DOM + r"""
          const cfg = { rule: { weekday: 3, n: 3, start: "19:00", end: "20:00", skip: [] }, start: "2026-12-17T01:00:00.000Z",
                        end: "2026-12-17T02:00:00.000Z", title: "Meeting", description: "DEC TEXT", plain: "PLAIN TEXT",
                        speakers: input.speakers, i18n: { join: "Join", soon: "Soon", live: "Live", speaker: "Guest speaker: {name}" } };
          const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true, at: "2026-12-16T20:00:00Z", lang: "es" });
          p.ready();
          const c = p.comps.cmMeeting(cfg);
          c.compute(); c.tick();
          const snap = () => ({ ymd: c._ymd, speaker: c.speaker, line: c.speakerLine, desc: c._desc, phase: c.phase,
                                gcalDesc: decodeURIComponent((/details=([^&]*)/.exec(c.gcal) || [])[1] || "") });
          const dec = snap();
          p.clock.now = Date.parse("2027-01-21T00:54:00Z");      // 6:54 PM, Jan 20 (the build's Dec 16 is over)
          c.tick();
          const at654 = c.phase;
          p.clock.now = Date.parse("2027-01-21T00:56:00Z"); c.tick();
          const at656 = c.phase;
          const jan = snap();
          p.clock.now = Date.parse("2027-01-21T02:01:00Z"); c.tick();
          const feb = snap();
          c.downloadIcs();
          out({ dec, jan, feb, at654, at656, file: p.downloads.length ? p.downloads[p.downloads.length - 1].text : "" });""",
          data={"speakers": self.SPEAKERS})
        self.assertEqual((r["dec"]["ymd"], r["dec"]["speaker"], r["dec"]["line"], r["dec"]["desc"]), ("2026-12-16", None, "", "PLAIN TEXT"))
        self.assertEqual(r["jan"]["ymd"], "2027-01-20")
        self.assertEqual(r["jan"]["speaker"], {"name": "Ann B.", "position": "Past delegate, Area 99", "topic": "How the Conference works"})
        self.assertEqual((r["jan"]["line"], r["jan"]["desc"], r["jan"]["gcalDesc"]), ("Guest speaker: Ann B.", "JAN TEXT", "JAN TEXT"))
        self.assertEqual((r["feb"]["speaker"]["name"], r["feb"]["desc"]), ("Carlos D.", "FEB TEXT"))
        # "Starting soon" only in the last 5 minutes
        self.assertEqual((r["at654"], r["at656"]), ("upcoming", "soon"))
        # the calendar file: the committee meeting's UID for that date (Spanish page), that date's text
        self.assertIn("UID:ev-committee-2027-02-17-es@neta65-gvlv", r["file"])
        self.assertIn("DESCRIPTION:FEB TEXT", r["file"])

    def test_a_series_countdown_gives_the_feeds_uid_and_says_first_meeting(self):
        r = run_js(self, DOM + r"""
          const cfg = { rule: { weekday: 3, n: 1, start: "19:00", end: "20:00", skip: [], starts: "2026-12-02" }, start: "2026-12-03T01:00:00.000Z",
                        end: "2026-12-03T02:00:00.000Z", title: "Grapevine Meeting", description: "GVM TEXT",
                        uid: "ev-recurring-grapevine-meeting-", file: "grapevine-meeting-", first: "2026-12-02", i18n: { join: "Join" } };
          const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true, at: "2026-11-26T18:00:00Z" });
          p.ready();
          const c = p.comps.cmMeeting(cfg);
          c.compute(); c.tick();
          const first = [c._ymd, c.isFirst, c.speaker, c._desc];
          p.clock.now = Date.parse("2026-12-03T02:01:00Z"); c.tick();
          c.downloadIcs();
          out({ first, next: [c._ymd, c.isFirst], file: p.downloads[0].text });""")
        self.assertEqual(r["first"], ["2026-12-02", True, None, "GVM TEXT"])
        self.assertEqual(r["next"], ["2027-01-06", False])
        self.assertIn("UID:ev-recurring-grapevine-meeting-2027-01-06@neta65-gvlv", r["file"])
        self.assertIn("DESCRIPTION:GVM TEXT", r["file"])

    def test_the_home_card_rolls_on_with_each_dates_speaker(self):
        r = run_js(self, DOM + r"""
          const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/home.js"], alpine: true, at: "2026-12-16T20:00:00Z" });
          p.ready();
          const c = p.comps.homeMeeting();
          const ds = { rule: JSON.stringify({ weekday: 3, n: 3, start: "19:00", end: "20:00", skip: [] }), start: "2026-12-17T01:00:00.000Z",
                       end: "2026-12-17T02:00:00.000Z", speakers: JSON.stringify(input.speakers), speakerTpl: "Guest speaker: {name}",
                       calTitle: "Committee meeting", calDesc: "Monthly committee meeting on Google Meet.", calLoc: "https://meet.google.com/abc-defg-hij",
                       calUrl: "https://example.org/gv/meetings/#committee-meeting" };
          c.$el = { dataset: ds }; c.$root = c.$el;
          c.$refs = { date: el("span", {}, [], "built date"), time: el("span", {}, [], "built time") };
          c.init();
          const dec = [c.speaker, c.speakerLine];
          p.clock.now = Date.parse("2026-12-17T02:30:00Z"); c.tick();
          const jan = [c.speaker, c.speakerLine, c.dateLabel];
          c.addToCalendar();
          out({ dec, jan, file: p.downloads[0].text });""", data={"speakers": [{k: s[k] for k in ("ymd", "name", "topic")} for s in self.SPEAKERS]})
        self.assertEqual(r["dec"], [None, ""])
        self.assertEqual(r["jan"][:2], [{"name": "Ann B.", "topic": "How the Conference works"}, "Guest speaker: Ann B."])
        self.assertEqual(plain(r["jan"][2]), "Wednesday, January 20")
        flat = re.sub(r"\r\n ", "", r["file"])
        self.assertIn("DESCRIPTION:Monthly committee meeting on Google Meet. Guest speaker: Ann B. — “How the Conference works”. "
                      "https://meet.google.com/abc-defg-hij", flat)
        self.assertIn("URL:https://example.org/gv/meetings/#committee-meeting\r\n", flat)   # the section: data-cal-url
        self.assertIn("UID:ev-committee-2027-01-20@neta65-gvlv", flat)

    def test_the_home_card_with_a_speaker_without_a_topic(self):
        # one period after the name ("Guest speaker: Pat E."), never two
        r = run_js(self, DOM + r"""
          const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/home.js"], alpine: true, at: "2027-01-10T20:00:00Z" });
          p.ready();
          const c = p.comps.homeMeeting();
          const ds = { rule: JSON.stringify({ weekday: 3, n: 3, start: "19:00", end: "20:00", skip: [] }), start: "2027-01-21T01:00:00.000Z",
                       end: "2027-01-21T02:00:00.000Z", speakers: JSON.stringify([{ ymd: "2027-01-20", name: "Pat E.", topic: "" }]),
                       speakerTpl: "Guest speaker: {name}", calTitle: "Committee meeting", calDesc: "Monthly committee meeting on Google Meet.",
                       calLoc: "https://meet.google.com/abc-defg-hij", calUrl: "https://example.org/gv/meetings/" };
          c.$el = { dataset: ds }; c.$root = c.$el;
          c.$refs = { date: el("span", {}, [], "built date"), time: el("span", {}, [], "built time") };
          c.init();
          c.addToCalendar();
          out({ line: c.speakerLine, file: p.downloads[0].text });""")
        self.assertEqual(r["line"], "Guest speaker: Pat E.")
        self.assertIn("DESCRIPTION:Monthly committee meeting on Google Meet. Guest speaker: Pat E. https://meet.google.com/abc-defg-hij",
                      re.sub(r"\r\n ", "", r["file"]))


# =========================================================================== the built pages
# /meetings/, the home page, /events/ and /share/ as the build renders them (Eleventy with the site's own config, ONLY
# those pages), at a fixed clock, on these tests' settings: the committee meeting (Google Meet, two guest speakers) and
# the Grapevine Meeting in its room — `site`, the `meeting` global (src/_data/meeting.js on the same settings) and
# events.json's Grapevine Meeting dates (the sync's: build_data.recurring_events)
PAGES_JS = r"""
process.env.ONLY = "meetings.njk,index.njk,events.njk,share.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const yaml = await import("js-yaml");
const { Eleventy } = await import("@11ty/eleventy");
const meetingData = (await imp("src/_data/meeting.js")).default;
const cfg = yaml.load(input.yaml);
// the `meeting` global on these settings
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r20-pages-"));
fs.mkdirSync(path.join(tmp, "config"));
fs.writeFileSync(path.join(tmp, "config", "site.yml"), input.yaml);
const here = process.cwd();
process.chdir(tmp);
let meeting;
try { meeting = meetingData(); } finally { process.chdir(here); fs.rmSync(tmp, { recursive: true, force: true }); }
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r20-site-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(c) {
      // (Eleventy merges computed data into the data it has: every key of config/site.yml's own meeting that these
      // settings leave out is set to nothing — a passcode the committee adds there is not this test's)
      const none = (o) => Object.fromEntries(Object.keys(o || {}).map((k) => [k, null]));
      c.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { updated: null, items: input.items } }),
        site: (data) => ({ ...data.site, meeting: { ...none(data.site.meeting), ...cfg.meeting }, recurring_events: cfg.recurring_events }),
        meeting: (data) => ({ ...meeting, next: meeting.next && { ...none(data.meeting && data.meeting.next), ...meeting.next } }),
      });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url && p.url.endsWith("/")).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def part(page: str, start: str, end: str | None = None) -> str:
    i = page.index(start)
    return page[i:page.index(end, i + 1)] if end else page[i:]


def text(fragment: str) -> str:
    """The words of an HTML fragment (no tags, single spaces; quotation marks against their words)."""
    t = re.sub(r"<script.*?</script>|<svg.*?</svg>", " ", fragment, flags=re.S)
    t = plain(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))).strip()
    return t.replace("“ ", "“").replace(" ”", "”")


def opening_tag(page: str, needle: str) -> str:
    """The whole start tag that holds `needle`."""
    i = page.index(needle)
    return page[page.rindex("<", 0, i):page.index(">", i) + 1]


def x_data(page: str, needle: str) -> dict:
    """The JSON a component gets: x-data="cmMeeting({...})" of the tag that holds `needle`."""
    tag = opening_tag(page, needle)
    m = re.search(r'x-data="cmMeeting\((.*?)\)"', tag, re.S)
    return json.loads(html.unescape(m.group(1)))


class BuiltPages(Untranslated):
    built: dict = {}

    def pages(self, at: str) -> dict:
        if at not in BuiltPages.built:
            items = B.recurring_events(ctx_with())
            BuiltPages.built[at] = run_js(self, PAGES_JS, data={"yaml": YAML, "items": items}, timeout=900, now=at)
        return BuiltPages.built[at]

    # ------------------------------------------------------------------ /meetings/
    def test_meetings_before_the_first_speaker(self):
        p = self.pages(NOV26)
        for url in ("/meetings/", "/es/meetings/"):
            with self.subTest(url=url):
                page = p[url]
                board = part(page, 'class="cm-board"', 'id="grapevine-meeting"')
                cfg = x_data(page, 'class="cm-board"')
                # the countdown: Dec 16, no speaker — its speaker panel is there for the browser, hidden (x-cloak)
                self.assertEqual(cfg["start"], "2026-12-17T01:00:00.000Z")
                self.assertEqual([s["ymd"] for s in cfg["speakers"]], ["2027-01-20", "2027-02-17"])
                self.assertNotIn("Ann", cfg["plain"])
                self.assertIn("x-cloak", opening_tag(board, 'class="cm-count-speaker"'))
                # what happens: the topic-sharing hour shown, the speaker's evening ready for the browser (x-cloak)
                self.assertIn('x-show="speaker" x-cloak', board)
                self.assertNotIn('x-show="!speaker" x-cloak', board)
                # no number to call; the meeting code, copied as written; no passcode
                self.assertNotIn("#phone", board)
                self.assertIn('data-copy="abc-defg-hij"', board)
                self.assertNotRegex(board, r"(?i)passcode|código de acceso")
        en = text(part(p["/meetings/"], 'class="cm-board"', 'id="grapevine-meeting"'))
        # Dec 16: no guest speaker — a topic to share on until 7:30, then the same second half, in six steps; the
        # second, "Guest speaker", says most months have one (done by the settings' speaker_until) and this one doesn't
        self.assertIn("7:00 – 8:00 PM Central time: no guest speaker at this meeting; we share on a topic until 7:30 PM.", en)
        self.assertIn("1 Welcome & opening We open with a moment of silence and the Serenity Prayer. People who are here for the "
                      "first time or new to service are especially welcome. 2 Guest speaker Most months a guest speaker shares on "
                      "a topic and answers our questions, done by 7:30 PM. When there's no guest speaker, as at this meeting, the "
                      "chair introduces a topic and members share their experience on it. 3 Coming up & workshop requests", en)
        self.assertNotIn("A topic to share on", en)
        for s in ("4 Special offers & magazine topics", "5 GVR and RLV sharing", "experience, not reports",
                  "6 Close at 8:00 PM, then the parking lot We close with the Responsibility Statement. Then the parking lot: "
                  "stay on for whatever is on your mind."):
            self.assertIn(s, en)
        # the evening with a guest speaker, for the browser: not a business meeting
        for s in ("How the evening runs", "Each meeting opens with a guest speaker: the talk and questions, done by 7:30 PM. Then "
                  "events, offers, magazine topics and sharing until 8:00 PM.", "7:00 PM Opening A moment of silence and the "
                  "Serenity Prayer, then we welcome our guest speaker and introduce the topic.", "about 7:02 PM Our guest speaker",
                  "About 20 minutes.", "about 7:22 PM Questions for the speaker", "who is done by 7:30 PM.",
                  "7:30 PM Events, offers, topics and sharing Coming events and workshop requests, special offers from the stores, "
                  "the magazines' topics and deadlines, then GVRs and RLVs share what's working.",
                  "8:00 PM Close, then the parking lot We close at 8:00 PM with the Responsibility Statement. Then the parking lot: "
                  "stay on for whatever is on your mind.",
                  "No phone number to call in: this meeting is online only.",
                  "On a computer, open the link in your browser; on a phone or tablet, use the Google Meet app.",
                  "Open the Google Meet link a few minutes before we start"):
            self.assertIn(s, en)
        self.assertNotIn("15 minutes", en)
        self.assertNotRegex(en, r"(?i)committee business|business hour|reports from|the minutes|old business|new business")
        es = text(part(p["/es/meetings/"], 'class="cm-board"', 'id="grapevine-meeting"'))
        for s in ("7:00–8:00 p. m., hora del Centro: en esta reunión no hay orador(a) invitado(a); hasta las 7:30 p. m. "
                  "compartimos sobre un tema.",
                  "2 Orador(a) invitado(a) La mayoría de los meses, un(a) orador(a) invitado(a) habla sobre un tema y responde "
                  "nuestras preguntas, y a más tardar a las 7:30 p. m. termina su parte. Cuando no hay orador(a) invitado(a), "
                  "como en esta reunión, quien coordina presenta un tema y los miembros comparten su experiencia sobre él. "
                  "3 Eventos próximos", "5 Lo que comparten los RLV y GVR",
                  "6 Cierre a las 8:00 p. m. y la reunión después de la reunión",
                  "Cómo transcurre la reunión", "hacia las 7:02 p. m. Nuestro(a) orador(a) invitado(a)",
                  "7:30 p. m. Eventos, ofertas, temas y tiempo para compartir", "después, hasta las 8:00 p. m., eventos, ofertas, temas de las "
                  "revistas y lo que comparten los RLV y GVR.", "A las 8:00 p. m. cerramos con la Declaración de Responsabilidad.",
                  "Sin número de teléfono para llamar"):
            self.assertIn(s, es)
        self.assertNotIn("p. m..", es)
        self.assertNotRegex(es, r"(?i)asuntos del comité|informes de distritos")

    def test_the_guest_speakers_list(self):
        p = self.pages(NOV26)
        for url, name, pos, topic, date in (
                ("/meetings/", "Ann B.", "Past delegate, Area 99", "“How the Conference works”", "Wednesday, January 20, 2027"),
                ("/es/meetings/", "Ann B.", "Ex delegada del Área 99", "“Cómo trabaja la Conferencia”", "Miércoles, 20 de enero de 2027")):
            with self.subTest(url=url):
                box = part(p[url], 'id="guest-speakers"', "</ol>")
                rows = re.findall(r'<li class="cm-speaker[^"]*" data-cm-expire="([^"]+)">(.*?)</li>', box, re.S)
                self.assertEqual([r[0] for r in rows], ["2027-01-21T02:00:00.000Z", "2027-02-18T02:00:00.000Z"])
                first = text(rows[0][1])
                for s in (name, pos, topic, date):
                    self.assertIn(s, first)
                self.assertIn("2027", text(part(box, "<h3", "</h3>")))
        # the upcoming dates name each date's speaker
        dates = text(part(p["/meetings/"], 'class="cm-dates-card', "</ol>"))
        self.assertIn("Wednesday, January 20, 2027 7:00 – 8:00 PM CST Guest speaker: Ann B.", dates)
        self.assertIn("Wednesday, December 16, 2026 7:00 – 8:00 PM CST Next", dates)

    def test_meetings_with_a_speaker_next(self):
        p = self.pages(DEC17)
        page = p["/meetings/"]
        board = part(page, 'class="cm-board"', 'id="grapevine-meeting"')
        panel = opening_tag(board, 'class="cm-count-speaker"')
        self.assertNotIn("x-cloak", panel)
        self.assertIn("Guest speaker: Ann B.", text(part(board, 'class="cm-count-speaker"', "</div>")))
        self.assertIn('x-show="!speaker" x-cloak', board)          # the topic-sharing hour now waits for the browser
        self.assertNotIn('x-show="speaker" x-cloak', board)
        evening = text(part(board, 'class="cm-agenda', 'class="flex flex-1 flex-col" x-show="!speaker"'))
        self.assertIn("about 7:02 PM Our guest speaker Ann B. · Past delegate, Area 99 “How the Conference works” About 20 minutes.", evening)
        self.assertIn("Orador(a) invitado(a): Ann B.", text(part(p["/es/meetings/"], 'class="cm-count-speaker"', "</div>")))

    def test_the_grapevine_meeting_section(self):
        for at, first, date in ((NOV26, True, "Wednesday, December 2, 2026"), (DEC17, False, "Wednesday, January 6, 2027")):
            page = self.pages(at)["/meetings/"]
            sec = part(page, '<section class="container-page section pt-0" aria-labelledby="grapevine-meeting-h"', "</section>")
            with self.subTest(at=at):
                self.assertIn('id="grapevine-meeting"', sec)
                cfg = x_data(sec, 'class="cm-series-board"')
                self.assertEqual((cfg["uid"], cfg["file"], cfg["first"]), ("ev-recurring-grapevine-meeting-", "grapevine-meeting-", "2026-12-02"))
                self.assertEqual(cfg["rule"], {"weekday": 3, "n": 1, "start": "19:00", "end": "20:00", "skip": [], "starts": "2026-12-02"})
                self.assertIn("Meeting code: abc-defg-hij", cfg["description"])
                words = text(sec)
                self.assertIn(date, words)
                for s in ("Grapevine Meeting", "Our monthly online meeting · In English", "The AA Grapevine Statement of Purpose",
                          "in place of the AA Preamble", "A story from AA Grapevine", "and starts the sharing.",
                          "Sharing on its topic", "3 to 5 minutes each.",
                          "No basket (the meeting has no expenses): instead, how we support AA Grapevine and Carry the "
                          "Message; announcements; and we close at 8:00 PM with the Responsibility Statement.",
                          "Meeting code abc-defg-hij", "Join on Google Meet",
                          "The same Google Meet room as our committee meeting."):
                    self.assertIn(s, words)
                # "First meeting" on its first date, "Next meeting" after
                cloaked = lambda label: "x-cloak" in opening_tag(sec, f">{label}<")          # noqa: E731
                self.assertEqual((cloaked("First meeting"), cloaked("Next meeting")), (not first, first))
                self.assertIn(f'data-copy="{ROOM}"', sec)
                self.assertNotIn("Grapevine meetings", words)
                self.assertNotIn("home group", words)          # no "your Seventh Tradition goes to your home group"
        es = text(part(self.pages(NOV26)["/es/meetings/"], 'aria-labelledby="grapevine-meeting-h"', "</section>"))
        for s in ("Nuestra reunión mensual en línea Reunión de Grapevine (en inglés)", "La Declaración de Propósito de AA Grapevine",
                  "No pasamos canasta (la reunión no tiene gastos): en su lugar, cómo apoyamos a AA Grapevine y Lleva el "
                  "Mensaje; los anuncios; y a las 8:00 p. m. cerramos con la Declaración de Responsabilidad.",
                  "Código de la reunión abc-defg-hij", "Primera reunión"):
            self.assertIn(s, es)
        # the Seventh Tradition is not sent to the home group any more: the close says how we support AA Grapevine
        self.assertNotIn("grupo base", es)
        self.assertNotIn("En inglés", es, "the title says it: the eyebrow does not again")

    # ------------------------------------------------------------------ the home page
    def test_the_home_card(self):
        for at, shown in ((NOV26, False), (DEC17, True)):
            for url, line in (("/", "Guest speaker: Ann B."), ("/es/", "Orador(a) invitado(a): Ann B.")):
                page = self.pages(at)[url]
                card = part(page, '<div class="home-meet home-meet--hero"', 'class="home-meet-count"')
                with self.subTest(at=at, url=url):
                    tag = opening_tag(card, 'x-data="homeMeeting"')
                    m = re.search(r"""data-speakers=(?:'([^']*)'|"([^"]*)")""", tag)
                    speakers = json.loads(html.unescape(m.group(1) or m.group(2)))
                    self.assertEqual([s["ymd"] for s in speakers], ["2027-01-20", "2027-02-17"])
                    self.assertEqual(sorted(speakers[0]), ["name", "topic", "ymd"])
                    self.assertIn('data-cal-loc="https://meet.google.com/abc-defg-hij"', tag)
                    self.assertNotIn("meet.google.com", re.search(r'data-cal-desc="([^"]*)"', tag).group(1))
                    self.assertEqual(line in card, shown)
                    self.assertEqual("x-cloak" in opening_tag(card, 'x-show="speaker"'), not shown)

    def test_the_grapevine_meeting_is_ours_on_the_home_page_and_events(self):
        p = self.pages(NOV26)
        home = part(p["/"], 'aria-labelledby="events-title"', "</section>")
        card = part(home, "<article", "</article>")
        self.assertIn("Grapevine Meeting", text(card))
        self.assertIn("ev-tone-other", card)
        self.assertEqual(text(part(card, '<span class="badge ev-badge"', "</span>")), "NETA 65")
        self.assertIn("#i-video", part(card, '<span class="badge ev-badge"', "</span>"))
        for url in ("/events/", "/es/events/"):
            ev = p[url]
            i = ev.index('id="ev-recurring-grapevine-meeting-2026-12-02"')
            gvm = ev[i:ev.index("</li>", ev.index("</article>", i))]
            with self.subTest(url=url):
                self.assertIn("ev-tone-other", gvm)
                self.assertEqual(text(part(gvm, '<span class="badge ev-badge"', "</span>")), "NETA 65")
                self.assertIn("abc-defg-hij", text(gvm))
                self.assertNotIn("ev-tone-gv", gvm)

    # ------------------------------------------------------------------ /events/
    def test_events_committee_cards_and_the_pinned_card(self):
        for at in (NOV26, DEC17):
            for url, line in (("/events/", "Guest speaker: Ann B. — “How the Conference works”"),
                              ("/es/events/", "Orador(a) invitado(a): Ann B. — “Cómo trabaja la Conferencia”")):
                page = self.pages(at)[url]
                with self.subTest(at=at, url=url):
                    i = page.index('id="ev-committee-2027-01-20"')
                    card = page[i:page.index("</article>", i)]
                    self.assertIn(line, text(card))
                    dec = page.index('id="ev-committee-2026-12-16"') if at == NOV26 else -1
                    if dec >= 0:
                        self.assertNotIn("Ann", text(page[dec:page.index("</article>", dec)]))
                    pinned = part(page, '<article class="cm-pinned', 'class="cm-pinned-actions"')
                    cfg = x_data(page, '<article class="cm-pinned')
                    self.assertEqual(len(cfg["speakers"]), 2)
                    self.assertEqual("x-cloak" in opening_tag(pinned, 'x-show="speaker"'), at == NOV26)
                    self.assertIn('href="https://meet.google.com/abc-defg-hij"', part(page, 'class="cm-pinned-actions"', "</a>"))
                    # never a speaker in what search engines read
                    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
                        self.assertNotIn("Ann B", ld)
                    self.assertNotIn("confirmed", page)

    # ------------------------------------------------------------------ /share/
    def test_the_poster(self):
        p = self.pages(NOV26)
        for url in ("/share/", "/es/share/"):
            page = p[url]
            sheets = re.findall(r'<div class="cm-sheet cm-poster" lang="(\w+)" x-show="posterLang === \'(\w+)\'"[^>]*>(.*?)<div class="cm-p-foot">',
                                page, re.S)
            with self.subTest(url=url):
                self.assertEqual([s[1] for s in sheets], ["en", "es", "bi"])
                v = {s[1]: text(s[2]) for s in sheets}
                self.assertIn("Grapevine Meeting · In English", v["en"])
                self.assertIn("Every first Wednesday of the month · 7:00 – 8:00 PM", v["en"])
                self.assertIn("Reunión de Grapevine (en inglés)", v["es"])
                self.assertNotIn("En inglés", v["es"], "the title says it: never twice")
                self.assertIn("Cada primer miércoles del mes · 7:00–8:00 p. m.", v["es"])
                self.assertNotIn("Grapevine Meeting", v["bi"])        # no room on the bilingual poster
                for k in v:
                    self.assertIn("abc-defg-hij", v[k])
                    self.assertNotRegex(v[k], r"(?i)passcode|meeting id\b|ID de reunión")
                    self.assertIn("Google Meet", v[k])
                self.assertIn("MEETING CODE", v["en"].upper())


if __name__ == "__main__":
    unittest.main()
