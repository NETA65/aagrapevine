"""Offline tests for events that come from several places, and the new event fields:

  * the optional .ics feeds (config/site.yml `sources.ics_feeds:`) — The Events Calendar's export on
    neta65.org: parsing, ONE polite request per run, the health each feed reports (neta65.org sits behind
    Cloudflare's "Just a moment…" check: HTTP 403), the last good copy, a calendar sent without a charset
    (UTF-8), and the de-duplication against content/events (the six real Grapevine / La Viña workshop
    pages), the committee meeting and the recurring booth — with the cases that must NOT merge (a workshop
    or booth on an assembly's first day, a workshop in a one-day virtual assembly's Zoom room, the same event
    page on another date) and the notes the chair gets;
    a Google Calendar-style repeating event with its deleted, moved and cancelled dates (EXDATE,
    RECURRENCE-ID) and its end (UNTIL);
  * content/events `tentative: true` and `location_es` / `location_en`, "Venue to be announced";
  * events over several days (the Area assemblies, Fri–Sun);
  * dated Drive flyers: a time past midnight, "noon", a time zone in the name, phone / screenshot names,
    "(until 5pm)" in the name, the same flyer uploaded twice;
  * the committee meeting's own `skip_dates` check, and its dates counted from the build's own clock;
  * our own calendar files (/events.ics, /es/events.ics), read back with icalendar: every link leads to a card
    /events/ has — a monthly series' date that has passed, to the page itself — and a repeat line names its
    time zone;
  * the flyers on /events/: the six workshops link their copies on the committee's Drive (neta65.org's cannot be
    shown by other sites), whose picture comes from the Drive; a file's own flyer never gets a feed's picture;
    and the page itself, rendered by Eleventy: every card with a flyer has the side tile — its picture, or the
    tile's own flyer icon and "Flyer" / "Volante";
  * online and hybrid events: a content/events file's online link gives its platform ("Online on Zoom"), a hybrid
    event is both a Place and a VirtualLocation for search engines (attendance "Mixed"), and the members' help
    explains both kinds of flyers (a dated name makes an event; a file's own flyer has no date, `flyer:`);
  * the Actions run summary: a blocked optional feed is a notice, never a "stopped updating" source.

No network: every request is faked (tests/fixtures/neta65-workshops.ics mirrors the plugin's format:
VTIMEZONE, DTSTART;TZID=America/Chicago, UID "<post id>-<start>-<end>@neta65.org", URL, LOCATION with
", United States", CATEGORIES:Grapevine-LaViña,Workshop, ATTACH;FMTTYPE=image/… for the flyer).

    python -m unittest tests.test_events_feeds -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import meeting as M  # noqa: E402

CHI = ZoneInfo("America/Chicago")
TODAY = datetime(2026, 9, 24, 15, 0, tzinfo=timezone.utc)          # Thu Sep 24, 2026, 10 AM CDT
FEED_URL = "https://neta65.org/events/category/workshop/list/?ical=1"
FIXTURE = (ROOT / "tests" / "fixtures" / "neta65-workshops.ics").read_text(encoding="utf-8").replace("\n", "\r\n")
CFG = {
    "site": {"timezone": "America/Chicago"},
    "meeting": {"weekday": "wednesday", "week_of_month": 3, "start": "19:00", "end": "20:00", "skip_dates": []},
    "sources": {
        "crawler": {"user_agent": "NETA65-GrapevineCommitteeBot/2.0 (+https://github.com/NETA65/aagrapevine)"},
        "ics_feeds": [{"url": FEED_URL, "label": "NETA 65 workshops", "label_es": "Talleres de NETA 65",
                       "category": "neta65"}],
    },
}

# The six workshops as the chair wrote them in content/events (headers as in the real files).
WORKSHOPS = {
    "2026-09-26-lv-writing-workshop-fort-worth.md": (
        'title: "La Viña Writing Workshop (in Spanish) — Fort Worth"\n'
        'title_es: "Taller de Escritura de La Viña — Fort Worth"\n'
        "start: 2026-09-26T19:00:00-05:00\nend: 2026-09-26T21:00:00-05:00\n"
        'location: "Grupo Nueva Esperanza, 3401 E Belknap, Fort Worth, TX 76111"\n'
        'url: "https://neta65.org/event/lv-writing-workshop/"\n'
        'flyer: "https://neta65.org/wp-content/uploads/2026/09/New-Writing-Workshop-La-Nueva-Esperanza.jpg"\n'
        "confirmed: true\nlang: en\nsummary_es: \"Taller en español para aprender a escribir tu historia para La Viña.\"\n"),
    "2026-10-03-gv-writing-workshop-arlington.md": (
        'title: "Grapevine Writing Workshop — Arlington"\n'
        'title_es: "Taller de Escritura de Grapevine (en inglés) — Arlington"\n'
        "start: 2026-10-03T14:00:00-05:00\nend: 2026-10-03T17:00:00-05:00\n"
        'location: "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012"\n'
        'url: "https://neta65.org/event/grapevine-writing-workshop-6/"\nconfirmed: true\nlang: en\n'),
    "2026-10-07-lv-writing-workshop-mansfield.md": (
        'title: "La Viña Writing Workshop (in Spanish) — Mansfield"\n'
        'title_es: "Taller de Escritura de La Viña — Mansfield"\n'
        "start: 2026-10-07T20:00:00-05:00\nend: 2026-10-07T22:00:00-05:00\n"
        'location: "Grupo 7 Defectos y 7 Virtudes, 287 Frontage Road, Mansfield, TX 76063"\n'
        'url: "https://neta65.org/event/la-vina-writing-workshop-3/"\nlang: en\n'),
    "2026-10-17-lv-recording-workshop-duncanville.md": (
        'title: "La Viña Recording Workshop (in Spanish) — Duncanville"\n'
        'title_es: "Taller de Grabación de La Viña — Duncanville"\n'
        "start: 2026-10-17T19:00:00-05:00\nend: 2026-10-17T21:00:00-05:00\n"
        'location: "Grupo Progresso Latino, 101 East Camp Wisdom Rd., Duncanville, TX 75116"\n'
        'url: "https://neta65.org/event/lv-recording-workshop/"\nlang: en\n'),
    "2026-10-26-lv-writing-workshop-tyler.md": (
        'title: "La Viña Writing Workshop (in Spanish) — Tyler"\n'
        'title_es: "Taller de Escritura de La Viña — Tyler"\n'
        "start: 2026-10-26T19:00:00-05:00\nend: 2026-10-26T21:00:00-05:00\n"
        'location: "Grupo Libro Grande, 623 West Bow, Tyler, TX 75702"\n'
        'url: "https://neta65.org/event/la-vina-writing-workshop-4/"\nlang: en\n'),
    "2026-11-07-lv-information-workshop-longview.md": (
        'title: "La Viña Information Workshop (in Spanish) — Longview"\n'
        'title_es: "Taller de Información de La Viña — Longview"\n'
        "start: 2026-11-07T19:00:00-06:00\nend: 2026-11-07T21:00:00-06:00\n"
        'location: "Grupo Solo por Hoy, 2035 South High, Longview, TX 75602"\n'
        'url: "https://neta65.org/event/la-vina-information-workshop/"\nlang: en\n'),
    # no event page of its own: found in the feed by its day + title
    "2027-09-18-gvlv-booth-fall-assembly.md": (
        'title: "GV/LV booth — Fall Assembly"\ntitle_es: "Mesa de GV/LV — Asamblea de Otoño"\n'
        "start: 2027-09-18T09:00:00-05:00\nend: 2027-09-18T16:00:00-05:00\nlocation: Tyler, TX\nlang: en\n"),
    # the Spring assembly (Fri–Sun), no event page and no end in the file: the feed fills them in
    "2027-03-19-neta65-spring-assembly.md": (
        'title: "NETA 65 Spring Assembly 2027"\ntitle_es: "Asamblea de Primavera 2027 de NETA 65"\n'
        "start: 2027-03-19\n"
        'location: "DoubleTree by Hilton Hotel Dallas Near the Galleria, 4099 Valley View Ln, Dallas, TX 75244"\n'
        "lang: en\n"),
}
# …and as they were before the committee confirmed them (no `confirmed: true`): what the chair is told then.
UNCONFIRMED = {k: v.replace("confirmed: true\n", "") for k, v in WORKSHOPS.items()}
# The three 2027 Area assemblies as the chair wrote them (two not final yet: venue to be announced).
ASSEMBLIES = {
    "2027-03-19-neta65-spring-assembly.md": (
        'title: "NETA 65 Spring Assembly 2027"\ntitle_es: "Asamblea de Primavera 2027 de NETA 65"\n'
        "start: 2027-03-19\nend: 2027-03-21\n"
        'location: "DoubleTree by Hilton Hotel Dallas Near the Galleria, 4099 Valley View Ln, Dallas, TX 75244"\n'
        "lang: en\n"),
    "2027-06-25-neta65-summer-assembly.md": (
        'title: "NETA 65 Summer Assembly 2027"\ntitle_es: "Asamblea de Verano 2027 de NETA 65"\n'
        'start: 2027-06-25\nend: 2027-06-27\nlocation: "Venue to be announced"\nlocation_es: "Lugar por anunciarse"\n'
        "tentative: true\nlang: en\n"),
    "2027-09-17-neta65-fall-assembly.md": (
        'title: "NETA 65 Fall Assembly 2027"\ntitle_es: "Asamblea de Otoño 2027 de NETA 65"\n'
        'start: 2027-09-17\nend: 2027-09-19\nlocation: "Venue to be announced"\nlocation_es: "Lugar por anunciarse"\n'
        "tentative: true\nlang: en\n"),
}
VTIMEZONE = FIXTURE[FIXTURE.index("BEGIN:VTIMEZONE"):FIXTURE.index("END:VTIMEZONE") + len("END:VTIMEZONE")]


def ics(*vevents: str) -> str:
    """A small calendar in The Events Calendar's shape (VTIMEZONE + TZID=America/Chicago)."""
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//NETA65 - ECPv6.15.1//NONSGML v1.0//EN\r\n" + VTIMEZONE + "\r\n"
            + "".join(vevents) + "END:VCALENDAR\r\n")


def vevent(uid: str, summary: str, start: str, end: str, url: str, location: str = "", flyer: str = "") -> str:
    """start / end: '20270319T190000' (Central time) or '20270319' (all-day; end = the day AFTER, as in .ics)."""
    kind = "VALUE=DATE" if len(start) == 8 else "TZID=America/Chicago"
    lines = ["BEGIN:VEVENT", f"DTSTART;{kind}:{start}", f"DTEND;{kind}:{end}", f"UID:{uid}@neta65.org",
             f"SUMMARY:{summary}", f"URL:{url}"]
    if location:
        lines.append("LOCATION:" + location.replace(",", "\\,"))
    if flyer:
        lines.append(f"ATTACH;FMTTYPE=image/jpeg:{flyer}")
    return "\r\n".join(lines + ["END:VEVENT"]) + "\r\n"


REAL_URLS = ["https://neta65.org/event/lv-writing-workshop/", "https://neta65.org/event/grapevine-writing-workshop-6/",
             "https://neta65.org/event/la-vina-writing-workshop-3/", "https://neta65.org/event/lv-recording-workshop/",
             "https://neta65.org/event/la-vina-writing-workshop-4/", "https://neta65.org/event/la-vina-information-workshop/"]


def ctx_with(cfg: dict | None = None, now: datetime = TODAY, offline: bool = False) -> B.Ctx:
    ctx = B.Ctx(offline=True)
    ctx.offline = offline
    ctx.cfg = json.loads(json.dumps(cfg or CFG))
    ctx.now = now
    ctx.now_ts = now.timestamp()
    ctx.today_local = now.astimezone(ctx.tz).date()
    return ctx


class NoTranslator:
    def translate(self, texts, src, tgt):
        return [(None, False) for _ in texts]


class FakeResp:
    def __init__(self, status: int, text: str, headers: dict | None = None):
        self.status_code, self.text = status, text
        self.content = text.encode("utf-8")
        self.headers = headers or {}


CLOUDFLARE_403 = FakeResp(403, '<!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title>'
                               '<script src="https://challenges.cloudflare.com/x.js"></script></head></html>',
                          {"Server": "cloudflare", "Cf-Mitigated": "challenge", "Content-Type": "text/html"})


class TempState(unittest.TestCase):
    """data/state (the feeds' last good copy) in a temporary folder; no translation model."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-feed-test-"))
        p = mock.patch.object(B, "STATE_DIR", self.tmp)
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def state(self) -> dict:
        return json.loads((self.tmp / B.ICS_STATE_FILE).read_text(encoding="utf-8"))

    def manual_events(self, files: dict[str, str] | None = None) -> list[dict]:
        """content/events files (name → header lines) → their events, as announcements.py reads them."""
        folder = Path(tempfile.mkdtemp(dir=self.tmp, prefix="events-"))
        for name, header in (WORKSHOPS if files is None else files).items():
            (folder / name).write_text(f"---\n{header}---\nA hand-written description.\n", encoding="utf-8")
        return [A.parse_event(p, CHI) for p in A.content_files(folder)]


# --------------------------------------------------------------------------- reading a feed
class FeedParsing(TempState):
    def test_the_events_calendar_export(self):
        ctx = ctx_with()
        evs = B._parse_ics(ctx, {"_ics": FIXTURE, "_spec": B.feed_specs(ctx)[0]})
        by_url = {e["url"]: e for e in evs}
        self.assertEqual(len(evs), 11)                              # 12 VEVENTs, the CANCELLED one left out
        self.assertNotIn("https://neta65.org/event/cancelled-workshop/", by_url)
        fw = by_url["https://neta65.org/event/lv-writing-workshop/"]
        self.assertEqual((fw["extra"]["start"], fw["extra"]["end"]), ("2026-09-27T00:00:00Z", "2026-09-27T02:00:00Z"))
        self.assertEqual(fw["extra"]["location"], "Grupo Nueva Esperanza, 3401 E Belknap, Fort Worth, TX, 76111")
        self.assertEqual(fw["extra"]["city"], "Fort Worth")
        self.assertEqual(fw["extra"]["flyer_url"],
                         "https://neta65.org/wp-content/uploads/2026/09/New-Writing-Workshop-La-Nueva-Esperanza.jpg")
        self.assertEqual(fw["extra"]["flyer_thumb"], fw["extra"]["flyer_url"])
        self.assertEqual(fw["tags"], ["grapevine-lavina", "workshop"])
        self.assertEqual((fw["source"], fw["category"], fw["extra"]["feed"]), ("calendar", "neta65", "neta-65-workshops"))
        self.assertTrue(fw["extra"]["uid"].endswith("@neta65.org"))
        self.assertNotIn("tentative", fw["extra"])
        # daylight saving: 19:00 on Nov 7 is CST (UTC-6)
        lv = by_url["https://neta65.org/event/la-vina-information-workshop/"]
        self.assertEqual(lv["extra"]["start"], "2026-11-08T01:00:00Z")
        # HTML entities in titles (the plugin writes "&#8211;")
        self.assertEqual(by_url["https://neta65.org/event/grapevine-writing-workshop-7/"]["title"],
                         "Grapevine Writing Workshop – Denton")
        # STATUS:TENTATIVE → extra.tentative
        self.assertIs(by_url["https://neta65.org/event/taller-grabacion-garland/"]["extra"]["tentative"], True)
        # an all-day event over three days: the EXCLUSIVE DTEND (Mar 22) → the last day, Mar 21
        spring = by_url["https://neta65.org/event/spring-assembly-2027/"]
        self.assertEqual((spring["extra"]["start"], spring["extra"]["end"], spring["extra"]["all_day"]),
                         ("2027-03-19", "2027-03-21", True))
        # an escaped line break inside DESCRIPTION (\n), as the plugin writes it
        self.assertTrue(fw["summary"].endswith("strength and hope. All AA members are welcome."), fw["summary"])

    def test_the_fixture_is_valid_icalendar(self):
        """Every line of the fixture is a real content line (nothing silently dropped by the parser)."""
        from icalendar import Calendar
        cal = Calendar.from_ical(FIXTURE)
        errors = [e for comp in cal.walk() for e in (getattr(comp, "errors", None) or [])]
        self.assertEqual(errors, [])
        self.assertEqual(len(list(cal.walk("VEVENT"))), 12)

    def test_a_series_leaves_out_its_deleted_moved_and_cancelled_dates(self):
        """A Google Calendar (or Outlook) feed sends a repeating event ONCE (RRULE) with its exceptions: dates
        deleted from the series (EXDATE — a local time, UTC, a list, a day), a date moved or cancelled on its
        own (a VEVENT with the series' UID and RECURRENCE-ID), and its end (UNTIL, which Google writes in UTC
        even after an all-day or a floating start). Every date is listed once, where it really is."""
        series = "\r\n".join([
            # Wednesdays 7 PM Central until Nov 18 (UTC): Oct 21 deleted, Oct 14 moved to 6 PM, Oct 28 cancelled
            "BEGIN:VEVENT", "DTSTART;TZID=America/Chicago:20261007T190000", "DTEND;TZID=America/Chicago:20261007T200000",
            "RRULE:FREQ=WEEKLY;BYDAY=WE;UNTIL=20261119T005959Z", "EXDATE;TZID=America/Chicago:20261021T190000",
            "UID:study@google.com", "SUMMARY:GV Study Group", "END:VEVENT",
            "BEGIN:VEVENT", "DTSTART;TZID=America/Chicago:20261014T180000", "DTEND;TZID=America/Chicago:20261014T190000",
            "RECURRENCE-ID;TZID=America/Chicago:20261014T190000", "UID:study@google.com", "SUMMARY:GV Study Group",
            "END:VEVENT",
            "BEGIN:VEVENT", "DTSTART;TZID=America/Chicago:20261028T190000", "DTEND;TZID=America/Chicago:20261028T200000",
            "RECURRENCE-ID;TZID=America/Chicago:20261028T190000", "UID:study@google.com", "SUMMARY:GV Study Group",
            "STATUS:CANCELLED", "END:VEVENT",
            # all-day on the 2nd Saturday until Dec 31 (written in UTC): Nov 14 deleted
            "BEGIN:VEVENT", "DTSTART;VALUE=DATE:20261010", "DTEND;VALUE=DATE:20261011",
            "RRULE:FREQ=MONTHLY;BYDAY=2SA;UNTIL=20270101T055959Z", "EXDATE;VALUE=DATE:20261114",
            "UID:service@google.com", "SUMMARY:Service Day", "END:VEVENT",
            # EXDATE as a list and in UTC
            "BEGIN:VEVENT", "DTSTART;TZID=America/Chicago:20261001T190000", "DTEND;TZID=America/Chicago:20261001T200000",
            "RRULE:FREQ=WEEKLY;COUNT=5", "EXDATE;TZID=America/Chicago:20261008T190000,20261022T190000",
            "EXDATE:20261030T000000Z", "UID:thursday@example.org", "SUMMARY:Thursday Workshop", "END:VEVENT",
            # a floating time (no zone: the site's), UNTIL in UTC, a floating EXDATE
            "BEGIN:VEVENT", "DTSTART:20261003T100000", "DTEND:20261003T120000",
            "RRULE:FREQ=WEEKLY;UNTIL=20261017T160000Z", "EXDATE:20261010T100000",
            "UID:floating@example.org", "SUMMARY:Floating Saturday", "END:VEVENT",
            # an all-day date moved to the next day
            "BEGIN:VEVENT", "DTSTART;VALUE=DATE:20261003", "DTEND;VALUE=DATE:20261004", "RRULE:FREQ=WEEKLY;COUNT=3",
            "UID:booth@example.org", "SUMMARY:Booth", "END:VEVENT",
            "BEGIN:VEVENT", "DTSTART;VALUE=DATE:20261011", "DTEND;VALUE=DATE:20261012",
            "RECURRENCE-ID;VALUE=DATE:20261010", "UID:booth@example.org", "SUMMARY:Booth", "END:VEVENT"]) + "\r\n"
        ctx = ctx_with()
        evs = B._parse_ics(ctx, {"_ics": ics(series), "_spec": B.feed_specs(ctx)[0]})
        starts: dict[str, list[str]] = {}
        for e in evs:
            starts.setdefault(e["title"], []).append(e["extra"]["start"])
        self.assertEqual(sorted(starts["GV Study Group"]), [
            "2026-10-08T00:00:00Z",                  # Oct 7
            "2026-10-14T23:00:00Z",                  # Oct 14 at its new time, 6 PM (not at 7 PM too)
            "2026-11-05T01:00:00Z", "2026-11-12T01:00:00Z"])     # CST; Nov 18 is after UNTIL
        self.assertEqual(sorted(starts["Service Day"]), ["2026-10-10", "2026-12-12"])
        self.assertEqual(sorted(starts["Thursday Workshop"]), ["2026-10-02T00:00:00Z", "2026-10-16T00:00:00Z"])
        self.assertEqual(sorted(starts["Floating Saturday"]), ["2026-10-03T15:00:00Z", "2026-10-17T15:00:00Z"])
        self.assertEqual(sorted(starts["Booth"]), ["2026-10-03", "2026-10-11", "2026-10-17"])
        self.assertEqual(len({e["id"] for e in evs}), len(evs))

    def test_settings(self):
        ctx = ctx_with({"sources": {"ics_feeds": [
            {"url": "webcal://neta65.org/?post_type=tribe_events&tribe_events_cat=workshop&ical=1&eventDisplay=list",
             "label": "Workshops"},
            {"url": "not a link", "label": "Broken"},
            {"url": "https://example.org/cal.ics", "category": "somewhere"},
            "https://calendar.example.org/basic.ics"]}})
        specs = B.feed_specs(ctx)
        self.assertEqual([s["url"] for s in specs], [
            "https://neta65.org/?post_type=tribe_events&tribe_events_cat=workshop&ical=1&eventDisplay=list",
            "https://example.org/cal.ics", "https://calendar.example.org/basic.ics"])
        self.assertEqual([s["category"] for s in specs], ["ics", "ics", "ics"])
        self.assertEqual({s["group"] for s in specs}, {"neta"})
        self.assertEqual(len({s["key"] for s in specs}), 3)
        report = ctx.raw_problems["ics_feeds"]
        self.assertIn("“not a link” is not a calendar address", report)
        self.assertIn("category “somewhere”", report)
        self.assertEqual(B.feed_specs(ctx_with({"sources": {"ics_feeds": []}})), [])


# --------------------------------------------------------------------------- one polite request, health
class FeedHealth(TempState):
    def run_feed(self, ctx, resp):
        calls = []

        def fake_get(url, **kw):
            calls.append((url, kw))
            if isinstance(resp, Exception):
                raise resp
            return resp
        with mock.patch("requests.get", fake_get):
            evs = B.ics_events(ctx)
        return evs, calls

    def test_cloudflare_block_is_reported_plainly_and_asked_once_a_day(self):
        ctx = ctx_with()
        evs, calls = self.run_feed(ctx, CLOUDFLARE_403)
        self.assertEqual(evs, [])
        self.assertEqual(len(calls), 1)                                           # ONE request, no retries
        self.assertEqual(calls[0][0], FEED_URL)
        self.assertEqual(calls[0][1]["headers"]["User-Agent"], CFG["sources"]["crawler"]["user_agent"])  # our own name
        self.assertEqual(ctx.feed_requests, 1)
        h = ctx.feeds[0]
        self.assertEqual((h["state"], h["http_status"], h["events_count"], h["last_success"], h["checked_this_run"]),
                         ("blocked", 403, 0, None, True))
        self.assertEqual(h["error"], "neta65.org answered with a bot check (HTTP 403) — nothing is wrong on our side; "
                                     "there is no good copy of it yet")
        self.assertNotRegex(h["error"], r"(?i)robot")
        st = self.state()[FEED_URL]
        self.assertEqual((st["state"], st["http_status"], st["attempted"]), ("blocked", 403, "2026-09-24T15:00:00Z"))
        self.assertNotIn("ics", st)
        # a rerun the same day (a settings change, "Run workflow"): the site is NOT asked again
        for hours in (1, 12, 19):
            ctx2 = ctx_with(now=TODAY + timedelta(hours=hours))
            _, calls2 = self.run_feed(ctx2, AssertionError("must not be called"))
            self.assertEqual(calls2, [])
            self.assertEqual((ctx2.feeds[0]["state"], ctx2.feeds[0]["checked_this_run"]), ("blocked", False))
        # the next daily run asks again (once)
        ctx3 = ctx_with(now=TODAY + timedelta(days=1))
        _, calls3 = self.run_feed(ctx3, CLOUDFLARE_403)
        self.assertEqual(len(calls3), 1)

    def test_other_answers(self):
        fine = "nothing is wrong on our side; there is no good copy of it yet"
        cases = [(FakeResp(429, "slow down"), "blocked", 429, f"neta65.org asked for fewer requests (HTTP 429) — {fine}"),
                 (FakeResp(403, "Forbidden"), "blocked", 403,
                  f"neta65.org refused the request (HTTP 403), as its bot protection does — {fine}"),
                 (FakeResp(401, "Unauthorized"), "blocked", 401,
                  f"neta65.org refused the request (HTTP 401), as its bot protection does — {fine}"),
                 (FakeResp(404, "not found"), "error", 404, "HTTP 404"),
                 (FakeResp(200, "<html>a web page</html>"), "error", 200, "the answer is not a calendar file (.ics)"),
                 (requests.ConnectionError("no route"), "error", None, "no answer (ConnectionError)"),
                 (TimeoutError("slow"), "error", None, "no answer (TimeoutError)")]
        for resp, state, http, said in cases:
            (self.tmp / B.ICS_STATE_FILE).unlink(missing_ok=True)
            ctx = ctx_with()
            self.run_feed(ctx, resp)
            self.assertEqual((ctx.feeds[0]["state"], ctx.feeds[0]["http_status"], ctx.feeds[0]["error"]),
                             (state, http, said), resp)

    def test_a_good_copy_is_kept_and_used_while_blocked(self):
        ctx = ctx_with()
        evs, _ = self.run_feed(ctx, FakeResp(200, FIXTURE, {"Content-Type": "text/calendar"}))
        self.assertEqual(len(evs), 11)
        h = ctx.feeds[0]
        self.assertEqual((h["state"], h["http_status"], h["last_success"], h["from_copy"]),
                         ("ok", 200, "2026-09-24T15:00:00Z", False))
        self.assertEqual(self.state()[FEED_URL]["ics"], FIXTURE)
        # a working feed is not asked again the same day either ("at most once a day", as /status/ promises) …
        for hours in (1, 2, 12, 19):
            ctx1 = ctx_with(now=TODAY + timedelta(hours=hours))
            evs1, calls = self.run_feed(ctx1, AssertionError("must not be called"))
            self.assertEqual(calls, [])
            self.assertEqual((len(evs1), ctx1.feeds[0]["from_copy"]), (11, True))
        # … the next day the site blocks the robot: the copy is used, the date it worked is kept
        ctx2 = ctx_with(now=TODAY + timedelta(days=1))
        evs2, _ = self.run_feed(ctx2, CLOUDFLARE_403)
        self.assertEqual(len(evs2), 11)
        h2 = ctx2.feeds[0]
        self.assertEqual((h2["state"], h2["from_copy"], h2["last_success"], h2["events_count"]),
                         ("blocked", True, "2026-09-24T15:00:00Z", 11))
        self.assertEqual(h2["error"], "neta65.org answered with a bot check (HTTP 403) — nothing is wrong on our "
                                      "side; the last good copy is kept")
        # a new answer that cannot be read never replaces the good copy
        ctx3 = ctx_with(now=TODAY + timedelta(days=2))
        self.run_feed(ctx3, FakeResp(200, "BEGIN:VCALENDAR\r\nthis is not iCalendar"))
        self.assertEqual(self.state()[FEED_URL]["ics"], FIXTURE)

    def test_a_calendar_without_a_charset_is_read_as_utf8(self):
        """`requests` reads "text/calendar" without a charset as ISO-8859-1 ("La ViÃ±a"); RFC 5545 says UTF-8."""
        body = FIXTURE.encode("utf-8")
        for headers in ({"Content-Type": "text/calendar"}, {}, {"content-type": "text/calendar; charset=UTF-8"}):
            resp = FakeResp(200, "", headers)
            resp.content = body
            has_charset = "charset" in str(headers).lower()
            resp.text = body.decode("utf-8") if has_charset else body.decode("iso-8859-1")   # what requests gives
            (self.tmp / B.ICS_STATE_FILE).unlink(missing_ok=True)
            ctx = ctx_with()
            evs, _ = self.run_feed(ctx, resp)
            titles = {e["title"] for e in evs}
            self.assertIn("La Viña Writing Workshop", titles, headers)
            self.assertFalse(any("Ã" in t for t in titles), headers)

    def test_offline_build_never_asks(self):
        ctx = ctx_with(offline=True)
        _, calls = self.run_feed(ctx, AssertionError("must not be called"))
        self.assertEqual(calls, [])
        self.assertEqual(ctx.feeds[0]["state"], "never")
        self.assertFalse((self.tmp / B.ICS_STATE_FILE).exists())

    def test_status_json_keeps_feeds_apart_from_sources(self):
        ctx = ctx_with()
        self.run_feed(ctx, CLOUDFLARE_403)
        status = B.build_status(ctx, None, B.I18n(None), {}, False, 0.0)
        self.assertEqual([s["source"] for s in status["sources"]], [s[0] for s in B.SOURCES])
        self.assertNotIn("ics_feeds", status["problems"])          # a blocked feed is not a settings problem
        f = status["feeds"][0]
        self.assertEqual({k: f[k] for k in ("key", "label", "label_es", "state", "http_status", "events_count",
                                            "last_success", "group")},
                         {"key": "neta-65-workshops", "label": "NETA 65 workshops", "label_es": "Talleres de NETA 65",
                          "state": "blocked", "http_status": 403, "events_count": 0, "last_success": None,
                          "group": "neta"})


# --------------------------------------------------------------------------- the same event twice
class FeedDuplicates(TempState):
    def build(self, files=None, feed_text=FIXTURE, cfg=None):
        ctx = ctx_with(cfg)
        manual = self.manual_events(files)
        feed_items = B._parse_ics(ctx, {"_ics": feed_text, "_spec": B.feed_specs(ctx)[0]})
        ctx.feeds = [{"key": "neta-65-workshops", "label": "NETA 65 workshops"}]
        with mock.patch.object(B, "ics_events", lambda c: feed_items), \
                mock.patch.object(B.Ctx, "items", lambda self, name: manual if name == "manual_events" else []):
            evs = B.build_events(ctx)
        return ctx, evs

    def test_the_six_workshops_appear_once_and_keep_their_own_spanish(self):
        ctx, evs = self.build()
        for url in REAL_URLS:
            key = B.event_url_key(url)
            same = [e for e in evs if B.event_url_key(e.get("url")) == key]
            self.assertEqual(len(same), 1, url)
            self.assertEqual(same[0]["category"], "manual", url)            # the hand-written one wins
            self.assertEqual(same[0]["extra"]["also_in_feed"], "neta-65-workshops")
            self.assertEqual(same[0]["extra"]["feed_match"], "url")
            self.assertIn("es", same[0]["extra"]["own_i18n"]["title"])
        fw = next(e for e in evs if e["id"] == "ev:manual:2026-09-26-lv-writing-workshop-fort-worth")
        self.assertEqual(fw["extra"]["own_i18n"]["title"]["es"], "Taller de Escritura de La Viña — Fort Worth")
        self.assertEqual(fw["extra"]["location"], "Grupo Nueva Esperanza, 3401 E Belknap, Fort Worth, TX 76111")
        # the feed only fills what the file leaves out: Arlington's file has no flyer
        arl = next(e for e in evs if e["id"] == "ev:manual:2026-10-03-gv-writing-workshop-arlington")
        self.assertEqual(arl["extra"]["flyer_url"], "https://neta65.org/wp-content/uploads/2026/06/GV-LV-writing-workshop-10-3.png")
        self.assertEqual(arl["title"], "Grapevine Writing Workshop — Arlington")
        # found by day + similar title (no shared event page): the booth; the assembly gets its page and end
        booth = [e for e in evs if B.local_day(ctx, e["extra"]["start"]) == "2027-09-18"]
        self.assertEqual([(e["category"], e["extra"].get("feed_match")) for e in booth], [("manual", "title")])
        self.assertEqual(booth[0]["url"], "https://neta65.org/event/gvlv-booth-fall-assembly/")
        spring = next(e for e in evs if e["id"] == "ev:manual:2027-03-19-neta65-spring-assembly")
        self.assertEqual((spring["extra"]["start"], spring["extra"]["end"], spring["url"]),
                         ("2027-03-19", "2027-03-21", "https://neta65.org/event/spring-assembly-2027/"))
        # events only in the feed are shown, with the NETA 65 events
        feed_only = sorted(e["url"] for e in evs if e["category"] == "neta65")
        self.assertEqual(feed_only, ["https://neta65.org/event/grapevine-writing-workshop-7/",
                                     "https://neta65.org/event/la-vina-writing-workshop-dallas/",
                                     "https://neta65.org/event/taller-grabacion-garland/"])
        self.assertEqual(ctx.feeds[0]["duplicates"], 8)
        self.assertEqual(ctx.feeds[0]["notes"], [])          # the feed and the files agree
        # nothing else was lost or doubled
        self.assertEqual(len([e for e in evs if e["category"] in ("manual", "neta65")]), len(WORKSHOPS) + 3)

    def test_a_files_own_flyer_never_gets_the_feeds_picture(self):
        """A flyer and its picture go together. A file that links its own flyer — a copy on the committee's Drive,
        whose picture /events/ takes from the Drive (committee.js normalizeEvents) — keeps it with no picture from
        the feed: the feed's is the neta65.org copy, which other sites cannot show, and it would win over the
        Drive's. A file with no flyer takes the feed's flyer and its picture, as before."""
        drive = "https://drive.google.com/file/d/1iib2vqUCFpZ-T2oj_EDJU96mSt3P8k0j/view"
        name = "2026-09-26-lv-writing-workshop-fort-worth.md"
        files = {**WORKSHOPS, name: re.sub(r'flyer: "[^"]+"', f'flyer: "{drive}"', WORKSHOPS[name])}
        ctx, evs = self.build(files)
        by_id = {e["id"]: e for e in evs}
        fw = by_id["ev:manual:2026-09-26-lv-writing-workshop-fort-worth"]
        self.assertEqual(fw["extra"]["feed_match"], "url")                  # the feed's copy of it was matched…
        self.assertEqual((fw["extra"]["flyer_url"], fw["extra"]["flyer_thumb"]), (drive, None))     # …and gave nothing
        arl = by_id["ev:manual:2026-10-03-gv-writing-workshop-arlington"]   # no flyer in the file: the feed's pair
        png = "https://neta65.org/wp-content/uploads/2026/06/GV-LV-writing-workshop-10-3.png"
        self.assertEqual((arl["extra"]["flyer_url"], arl["extra"]["flyer_thumb"]), (png, png))

    def test_url_normalization(self):
        k = B.event_url_key
        self.assertEqual(k("https://neta65.org/event/lv-writing-workshop/"), "neta65.org/event/lv-writing-workshop")
        for v in ("http://www.neta65.org/event/lv-writing-workshop", "HTTPS://NETA65.ORG/event/lv-writing-workshop//",
                  "https://neta65.org/event/lv-writing-workshop/?ical=1#details"):
            self.assertEqual(k(v), "neta65.org/event/lv-writing-workshop", v)
        for v in ("https://neta65.org", "https://neta65.org/", "/events/#2027-03-19-x", "", None, "mailto:a@b.org"):
            self.assertIsNone(k(v), v)          # not an event's own page: never used to match

    def test_similar_titles(self):
        fort_worth, tyler = B.title_tokens("Fort Worth"), B.title_tokens("Tyler")
        # the city both events are in (and the year) say nothing: they are ignored
        self.assertTrue(B.similar_titles("LV Writing Workshop", "La Viña Writing Workshop (in Spanish) — Fort Worth",
                                         fort_worth))
        self.assertTrue(B.similar_titles("Taller de Escritura de La Viña", "Taller de Escritura de La Viña — Tyler", tyler))
        self.assertTrue(B.similar_titles("GV/LV booth — Fall Assembly", "Grapevine / La Viña Booth at the Fall Assembly"))
        self.assertTrue(B.similar_titles("NETA 65 Spring Assembly 2027", "Spring Assembly", {"2027"}, exact=True))
        self.assertFalse(B.similar_titles("LV Writing Workshop", "LV Recording Workshop"))
        self.assertFalse(B.similar_titles("Workshop", "Spring Assembly"))
        # an event AT an assembly is not the assembly (the kind of event counts; one-way "subset" is not enough)
        self.assertFalse(B.similar_titles("Grapevine Workshop at the Spring Assembly", "NETA 65 Spring Assembly 2027",
                                          {"2027"}))
        self.assertFalse(B.similar_titles("La Viña Booth at the Fall Assembly", "NETA 65 Fall Assembly 2027", {"2027"}))
        self.assertFalse(B.similar_titles("GV/LV Booth at the Spring Assembly", "NETA 65 Spring Assembly 2027", {"2027"}))
        # without the city on both sides (a place to be announced), every telling word must match
        self.assertFalse(B.similar_titles("LV Writing Workshop", "La Viña Writing Workshop Grupo Hispano", exact=True))
        self.assertTrue(B.similar_titles("LV Writing Workshop", "La Viña Writing Workshop (in Spanish)", exact=True))

    def test_a_workshop_or_booth_at_an_assembly_is_its_own_event(self):
        """On an assembly's first day, at the same hotel (known venue) or in the city of an assembly whose
        venue is still to be announced: never merged into the assembly, which keeps its own link and flyer."""
        feed = ics(
            vevent("20001", "Grapevine Workshop at the Spring Assembly", "20270319T190000", "20270319T210000",
                   "https://neta65.org/event/gv-workshop-spring-assembly/",
                   "DoubleTree by Hilton Hotel Dallas Near the Galleria, 4099 Valley View Ln, Dallas, TX, 75244, United States",
                   "https://neta65.org/wp-content/uploads/2027/03/gv-workshop.jpg"),
            vevent("20002", "La Viña Booth at the Fall Assembly", "20270917T090000", "20270917T160000",
                   "https://neta65.org/event/lv-booth-fall-assembly/", "Tyler Convention Center, Tyler, TX, United States",
                   "https://neta65.org/wp-content/uploads/2027/09/lv-booth.jpg"),
            # all-day on the assembly's first day only (a one-day event against a three-day one)
            vevent("20003", "Spring Assembly", "20270319", "20270320", "https://neta65.org/event/spring-hospitality/",
                   "Dallas, TX, United States"))
        ctx, evs = self.build(ASSEMBLIES, feed)
        by_id = {e["id"]: e for e in evs}
        spring, fall = by_id["ev:manual:2027-03-19-neta65-spring-assembly"], by_id["ev:manual:2027-09-17-neta65-fall-assembly"]
        for a in (spring, fall):
            self.assertNotIn("feed_match", a["extra"])
            self.assertTrue(a["url"].startswith("/events/#"), a["url"])          # its own card, not the workshop's page
            self.assertIsNone(a["extra"]["flyer_url"])
        self.assertEqual(sorted(e["url"] for e in evs if e["category"] == "neta65"), [
            "https://neta65.org/event/gv-workshop-spring-assembly/", "https://neta65.org/event/lv-booth-fall-assembly/",
            "https://neta65.org/event/spring-hospitality/"])
        self.assertEqual(ctx.feeds[0]["duplicates"], 0)

    def test_a_workshop_in_a_virtual_assemblys_zoom_room_is_its_own_event(self):
        """The online-room route: a one-day virtual assembly that a calendar lists by its day only, in the Zoom
        room our workshop at that assembly uses too, is NOT our workshop — both stay, and the file keeps its own
        card (no event page copied from the assembly). Only a date of a monthly series or the host's own event
        (tests/test_recurring_events.py) takes a day-only listing of its room; a listing that gives the
        workshop's own time in that room is still the workshop."""
        from scripts.sync import events_external as E
        zoom = "https://us02web.zoom.us/j/1234567890"
        files = {"2026-10-17-gv-workshop-virtual-pre-assembly.md": (
            'title: "Grapevine Workshop at the Virtual Pre-Assembly"\n'
            "start: 2026-10-17T10:00:00-05:00\nend: 2026-10-17T11:00:00-05:00\n"
            f'online_url: "{zoom}"\nlang: en\n')}
        feed = ics(vevent("50001", "District 12 Virtual Pre-Assembly", "20261017", "20261018",
                          "https://neta65.org/event/d12-pre-assembly/", zoom))
        ctx, evs = self.build(files, feed)
        self.assertEqual([e["url"] for e in evs if e["category"] == "neta65"], ["https://neta65.org/event/d12-pre-assembly/"])
        mine = next(e for e in evs if e["category"] == "manual")
        self.assertNotIn("feed_match", mine["extra"])
        self.assertEqual(mine["url"], "/events/#2026-10-17-gv-workshop-virtual-pre-assembly")
        self.assertEqual(ctx.feeds[0]["duplicates"], 0)
        # La Viña's own calendar listing a one-day virtual convention in that room: kept too
        convention = E.build_item("https://www.aalavina.org/get-involved/events/2026-10-17/convencion-virtual",
                                  E.decide({"title": "Convención Virtual de La Viña", "start": "2026-10-17",
                                            "all_day": True, "location_raw": zoom, "lang": "es"}))
        manual = self.manual_events(files)
        self.assertEqual(B.merge_calendar_duplicates(ctx_with(), manual, [convention]), [convention])
        self.assertNotIn("calendar_match", manual[0]["extra"])
        # the same room at the workshop's own time (a calendar that lists the workshop itself): one event
        timed = ics(vevent("50002", "Grapevine session", "20261017T100000", "20261017T110000",
                           "https://neta65.org/event/d12-pre-assembly-grapevine/", zoom))
        ctx, evs = self.build(files, timed)
        self.assertEqual([e["category"] for e in evs if e["category"] in ("manual", "neta65")], ["manual"])
        self.assertEqual(next(e for e in evs if e["category"] == "manual")["extra"]["feed_match"], "online")

    def test_the_same_page_on_another_date(self):
        """A shared event page counts only on the same day. A past file never swallows a new date; an upcoming
        file whose page shows another date is reported to the chair (the calendar's date is shown too)."""
        feed = ics(
            # the Fort Worth file (Sep 26, 2026) — its page used again for a new workshop in January
            vevent("30001", "LV Writing Workshop", "20270115T190000", "20270115T210000",
                   "https://neta65.org/event/lv-writing-workshop/", "Grupo Hispano, 4800 Ross Ave, Dallas, TX, 75204"),
            # the Arlington file says Oct 3; neta65.org now says Oct 10
            vevent("30002", "Grapevine Writing Workshop", "20261010T140000", "20261010T170000",
                   "https://neta65.org/event/grapevine-writing-workshop-6/",
                   "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX, 76012"))
        with self.assertLogs(B.log, "WARNING") as logs:
            ctx, evs = self.build(UNCONFIRMED, feed)
        self.assertEqual(len(logs.records), 2)
        feed_only = sorted(B.local_day(ctx, e["extra"]["start"]) for e in evs if e["category"] == "neta65")
        self.assertEqual(feed_only, ["2026-10-10", "2027-01-15"])               # neither date is lost
        self.assertEqual(ctx.feeds[0]["duplicates"], 0)
        notes = ctx.feeds[0]["notes"]
        self.assertEqual(len(notes), 2)
        arl = next(n for n in notes if "arlington" in n)
        self.assertIn("content/events/2026-10-03-gv-writing-workshop-arlington.md", arl)
        self.assertIn("on 2026-10-10, but the file says 2026-10-03", arl)
        self.assertIn("“NETA 65 workshops” calendar", arl)
        # the Fort Worth workshop is still upcoming on Sep 24 — the chair is asked too; once it is over, not
        fw_ctx = ctx_with(now=datetime(2026, 10, 1, 12, tzinfo=CHI).astimezone(timezone.utc))
        fw_ctx.feeds = [{"key": "neta-65-workshops"}]
        manual = self.manual_events({k: v for k, v in UNCONFIRMED.items() if "fort-worth" in k})
        items = B._parse_ics(fw_ctx, {"_ics": feed, "_spec": B.feed_specs(fw_ctx)[0]})
        kept = B.merge_feed_duplicates(fw_ctx, manual, items)
        self.assertEqual(len(kept), 2)
        self.assertEqual(fw_ctx.feeds[0]["notes"], [])

    def test_another_start_time_is_reported(self):
        feed = ics(vevent("30003", "Grapevine Writing Workshop", "20261003T150000", "20261003T180000",
                          "https://neta65.org/event/grapevine-writing-workshop-6/"))
        with self.assertLogs(B.log, "WARNING"):
            ctx, evs = self.build({k: v for k, v in UNCONFIRMED.items() if "arlington" in k}, feed)
        arl = next(e for e in evs if e["id"] == "ev:manual:2026-10-03-gv-writing-workshop-arlington")
        self.assertEqual((arl["extra"]["feed_match"], arl["extra"]["start"]), ("url", "2026-10-03T19:00:00Z"))   # file wins
        self.assertEqual(ctx.feeds[0]["notes"], [
            "content/events/2026-10-03-gv-writing-workshop-arlington.md: the “NETA 65 workshops” calendar says it "
            "starts at 3:00 PM, the file says 2:00 PM (Central time). If the time changed, correct start: and end: "
            "in the file."])

    def test_a_venue_now_known_fills_the_tba_place_and_the_chair_is_told(self):
        feed = ics(vevent("30004", "NETA 65 Summer Assembly 2027", "20270625", "20270628",
                          "https://neta65.org/event/summer-assembly-2027/", "Harvey Hotel, 2 Main St, Tyler, TX, 75701"))
        with self.assertLogs(B.log, "WARNING"):          # a made-up venue (the real file still says TBA)
            ctx, evs = self.build(ASSEMBLIES, feed)
        summer = next(e for e in evs if e["id"] == "ev:manual:2027-06-25-neta65-summer-assembly")
        self.assertEqual(summer["extra"]["feed_match"], "title")
        self.assertEqual((summer["extra"]["location"], summer["extra"]["city"]), ("Harvey Hotel, 2 Main St, Tyler, TX, 75701", "Tyler"))
        self.assertNotIn("location_tba", summer["extra"])
        self.assertNotIn("location", summer["extra"]["own_i18n"])        # the stale "Lugar por anunciarse" is gone
        self.assertIs(summer["extra"]["tentative"], True)                # still the chair's call
        self.assertEqual(summer["url"], "https://neta65.org/event/summer-assembly-2027/")
        B.I18n(NoTranslator()).apply(summer)
        self.assertNotIn("location", summer["i18n"])                     # the address, as written, in both languages
        self.assertEqual(ctx.feeds[0]["notes"], [
            "content/events/2027-06-25-neta65-summer-assembly.md: the file says the venue is not known yet; the "
            "“NETA 65 workshops” calendar gives “Harvey Hotel, 2 Main St, Tyler, TX, 75701”, which the site shows "
            "now. Put it in location: (and delete location_es:)."])
        self.assertEqual(len([e for e in evs if e["category"] in ("manual", "neta65")]), 3)

    def test_the_booth_and_the_meeting_in_a_feed_show_once(self):
        """config recurring_events (the CityWide Dallas booth) and the committee meeting are on the calendar
        too: a feed that lists them (the whole neta65.org calendar, a GV/LV calendar) never doubles them."""
        cfg = json.loads(json.dumps(CFG))
        cfg["recurring_events"] = [{
            "key": "citywide-dallas", "title": "GV/LV booth at CityWide Dallas", "title_es": "Mesa de GV/LV en CityWide Dallas",
            "week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "20:00",
            "location": "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220",
            "url": "https://citywidedallasaa.org"}]
        meeting = B.committee_meetings(ctx_with(cfg))[0]
        m_start = datetime.fromisoformat(meeting["extra"]["start"].replace("Z", "+00:00")).astimezone(CHI)
        m_end = datetime.fromisoformat(meeting["extra"]["end"].replace("Z", "+00:00")).astimezone(CHI)
        feed = ics(
            vevent("40001", "Grapevine/La Viña Booth at CityWide Dallas", "20261010T170000", "20261010T200000",
                   "https://neta65.org/event/gvlv-booth-citywide/",
                   "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX, 75220",
                   "https://neta65.org/wp-content/uploads/2026/10/booth.jpg"),
            vevent("40002", "GV/LV Committee Meeting", f"{m_start:%Y%m%dT%H%M%S}", f"{m_end:%Y%m%dT%H%M%S}",
                   "https://neta65.org/event/gvlv-committee-meeting/", "Online"))
        ctx, evs = self.build({}, feed, cfg)
        self.assertEqual([e["id"] for e in evs if e["category"] == "neta65"], [])
        self.assertEqual(ctx.feeds[0]["duplicates"], 2)
        booth = next(e for e in evs if e["id"] == "ev:recurring:citywide-dallas:2026-10-10")
        self.assertEqual((booth["url"], booth["extra"]["flyer_url"]), ("https://citywidedallasaa.org", None))  # untouched
        self.assertEqual(booth["extra"]["feed_match"], "title")
        m = next(e for e in evs if e["id"] == meeting["id"])
        self.assertEqual((m["url"], m["extra"]["feed_match"]), ("/meetings/", "title"))
        self.assertEqual(ctx.feeds[0]["notes"], [])

    def test_the_same_page_for_every_date_of_a_series(self):
        """A feed may list every date of a series under one page: only the date written by hand is dropped."""
        ctx = ctx_with()
        manual = self.manual_events({k: v for k, v in WORKSHOPS.items() if "tyler" in k})
        one = next(e for e in B._parse_ics(ctx, {"_ics": FIXTURE, "_spec": B.feed_specs(ctx)[0]})
                   if e["url"].endswith("la-vina-writing-workshop-4/"))
        later = json.loads(json.dumps(one))
        later["id"], later["extra"]["start"], later["extra"]["end"] = "ev:ics:later", "2026-11-23T01:00:00Z", None
        kept = B.merge_feed_duplicates(ctx, manual, [one, later])
        self.assertEqual([e["id"] for e in kept], ["ev:ics:later"])

    def test_same_title_same_day_other_city_is_another_event(self):
        ctx = ctx_with()
        manual = self.manual_events({k: v for k, v in WORKSHOPS.items() if "tyler" in k})
        feed = B._parse_ics(ctx, {"_ics": FIXTURE, "_spec": B.feed_specs(ctx)[0]})
        dallas = [e for e in feed if e["url"].endswith("-dallas/")]
        self.assertEqual(B.merge_feed_duplicates(ctx, manual, dallas), dallas)


# --------------------------------------------------------------------------- confirmed: true
class ConfirmedFiles(TempState):
    """content/events `confirmed: true`: the committee checked the date, time and place; the NETA 65 calendar
    never changes them, never shows the same event page as a second event, and the chair gets no note
    (only an info line in the log). Real case: the committee confirmed Fort Worth (Sat Sep 26) and
    Arlington (Sat Oct 3) while the calendar listed their pages on Jan 15, 2027 and Oct 10 at 3 PM."""

    def build(self, files, feed_text, now=TODAY):
        ctx = ctx_with(now=now)
        manual = self.manual_events(files)
        feed_items = B._parse_ics(ctx, {"_ics": feed_text, "_spec": B.feed_specs(ctx)[0]})
        ctx.feeds = [{"key": "neta-65-workshops", "label": "NETA 65 workshops"}]
        with mock.patch.object(B, "ics_events", lambda c: feed_items), \
                mock.patch.object(B.Ctx, "items", lambda self, name: manual if name == "manual_events" else []), \
                self.assertLogs(B.log, "INFO") as logs:
            evs = B.build_events(ctx)
        warnings = [r.getMessage() for r in logs.records if r.levelname == "WARNING"]
        infos = [r.getMessage() for r in logs.records if r.levelname == "INFO" and "is confirmed" in r.getMessage()]
        return ctx, evs, warnings, infos

    FW = "2026-09-26-lv-writing-workshop-fort-worth.md"
    ARL = "2026-10-03-gv-writing-workshop-arlington.md"

    def test_the_value(self):
        files = {f"2027-0{i}-01-x{i}.md": f"title: X{i}\nstart: 2027-0{i}-01\nconfirmed: {v}\n"
                 for i, v in enumerate(["true", "yes", "sí", "false", "no"], 1)}
        got = {e["extra"]["slug"]: e["extra"].get("confirmed") for e in self.manual_events(files)}
        self.assertEqual(got, {"2027-01-01-x1": True, "2027-02-01-x2": True, "2027-03-01-x3": True,
                               "2027-04-01-x4": None, "2027-05-01-x5": None})
        self.assertNotIn("confirmed", self.manual_events({"a.md": "title: A\nstart: 2027-01-01\n"})[0]["extra"])

    def test_the_calendars_other_dates_never_show_and_the_chair_is_not_asked(self):
        feed = ics(
            vevent("30001", "LV Writing Workshop", "20270115T190000", "20270115T210000",
                   "https://neta65.org/event/lv-writing-workshop/", "Grupo Hispano, 4800 Ross Ave, Dallas, TX, 75204"),
            vevent("30002", "Grapevine Writing Workshop", "20261010T150000", "20261010T180000",
                   "https://neta65.org/event/grapevine-writing-workshop-6/",
                   "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX, 76012"))
        files = {k: v for k, v in WORKSHOPS.items() if k in (self.FW, self.ARL)}
        ctx, evs, warnings, infos = self.build(files, feed)
        self.assertEqual([e["id"] for e in evs if e["category"] == "neta65"], [])       # no second event
        by_id = {e["id"]: e for e in evs}
        fw, arl = by_id["ev:manual:" + self.FW[:-3]], by_id["ev:manual:" + self.ARL[:-3]]
        self.assertEqual((fw["extra"]["start"], fw["extra"]["end"]), ("2026-09-27T00:00:00Z", "2026-09-27T02:00:00Z"))
        self.assertEqual((arl["extra"]["start"], arl["extra"]["end"]), ("2026-10-03T19:00:00Z", "2026-10-03T22:00:00Z"))
        self.assertEqual(fw["extra"]["location"], "Grupo Nueva Esperanza, 3401 E Belknap, Fort Worth, TX 76111")
        self.assertEqual(ctx.feeds[0]["notes"], [])
        self.assertEqual(ctx.feeds[0]["duplicates"], 2)
        self.assertEqual(warnings, [])
        self.assertEqual(len(infos), 2)
        self.assertIn("content/events/2026-10-03-gv-writing-workshop-arlington.md is confirmed (confirmed: true): the "
                      "“NETA 65 workshops” calendar lists its event page (https://neta65.org/event/grapevine-writing-"
                      "workshop-6/) on 2026-10-10; the file's 2026-10-03 is kept", " ".join(infos))
        # …and still after the Fort Worth workshop is over (the page's January date never appears)
        ctx, evs, warnings, infos = self.build(files, feed, now=datetime(2026, 12, 1, 12, tzinfo=CHI).astimezone(timezone.utc))
        self.assertEqual([e["id"] for e in evs if e["category"] == "neta65"], [])
        self.assertEqual((ctx.feeds[0]["notes"], warnings), ([], []))

    def test_the_same_day_keeps_the_files_time_and_place(self):
        feed = ics(vevent("30003", "Grapevine Writing Workshop", "20261003T150000", "20261003T180000",
                          "https://neta65.org/event/grapevine-writing-workshop-6/", "Other Hall, 9 Main St, Arlington, TX, 76010"))
        files = {self.ARL: WORKSHOPS[self.ARL]}
        ctx, evs, warnings, infos = self.build(files, feed)
        arl = next(e for e in evs if e["id"] == "ev:manual:" + self.ARL[:-3])
        self.assertEqual((arl["extra"]["start"], arl["extra"]["end"]), ("2026-10-03T19:00:00Z", "2026-10-03T22:00:00Z"))
        self.assertEqual(arl["extra"]["location"], "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012")
        self.assertEqual(arl["extra"]["feed_match"], "url")
        self.assertEqual((ctx.feeds[0]["notes"], warnings), ([], []))
        self.assertEqual(len(infos), 2)                                      # the time and the place, quietly
        self.assertIn("says it starts at 3:00 PM; the file's 2:00 PM (Central time) is kept", infos[0])
        # a confirmed file whose place is still "Venue to be announced" keeps it too
        tba = {self.ARL: WORKSHOPS[self.ARL].replace(
            'location: "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012"', 'location: TBA')}
        ctx, evs, warnings, infos = self.build(tba, feed)
        arl = next(e for e in evs if e["id"] == "ev:manual:" + self.ARL[:-3])
        self.assertEqual((arl["extra"]["location"], arl["extra"]["location_tba"]), ("TBA", True))
        self.assertEqual((ctx.feeds[0]["notes"], warnings), ([], []))

    def test_a_new_file_for_a_reused_page_gets_the_calendars_date(self):
        """The page of a confirmed file used again for a new workshop: a file for the new date takes it."""
        feed = ics(vevent("30001", "LV Writing Workshop", "20270115T190000", "20270115T210000",
                          "https://neta65.org/event/lv-writing-workshop/", "Grupo Hispano, 4800 Ross Ave, Dallas, TX, 75204"))
        files = {self.FW: WORKSHOPS[self.FW], "2027-01-15-lv-writing-workshop-dallas.md": (
            'title: "La Viña Writing Workshop — Dallas"\nstart: 2027-01-15T19:00:00-06:00\n'
            'url: "https://neta65.org/event/lv-writing-workshop/"\nlang: en\n')}
        ctx, evs, warnings, infos = self.build(files, feed)
        new = next(e for e in evs if e["id"] == "ev:manual:2027-01-15-lv-writing-workshop-dallas")
        self.assertEqual(new["extra"]["feed_match"], "url")
        self.assertEqual(new["extra"]["location"], "Grupo Hispano, 4800 Ross Ave, Dallas, TX, 75204")
        self.assertEqual([e["id"] for e in evs if e["category"] == "neta65"], [])
        self.assertEqual((warnings, infos), ([], []))

    def test_the_real_files(self):
        """content/events: the two workshops the committee confirmed keep their own dates; the Summer Assembly's
        venue is still to be announced (and its details still tentative)."""
        folder = ROOT / "content" / "events"
        evs = {e["extra"]["slug"]: e for e in (A.parse_event(p, CHI) for p in A.content_files(folder))}
        fw, arl = evs[self.FW[:-3]], evs[self.ARL[:-3]]
        self.assertIs(fw["extra"].get("confirmed"), True)
        self.assertIs(arl["extra"].get("confirmed"), True)
        self.assertEqual(fw["extra"]["start"], "2026-09-27T00:00:00Z")          # Sat Sep 26, 7 PM CDT
        self.assertEqual(arl["extra"]["start"], "2026-10-03T19:00:00Z")         # Sat Oct 3, 2 PM CDT
        summer = evs["2027-06-25-neta65-summer-assembly"]
        self.assertIs(summer["extra"].get("tentative"), True)
        self.assertTrue(B.location_is_tba(summer["extra"]["location"]))


# --------------------------------------------------------------------------- tentative, place in Spanish
class TentativeAndPlace(TempState):
    def test_tentative_values(self):
        files = {f"2027-0{i}-01-x{i}.md": f"title: X{i}\nstart: 2027-0{i}-01\ntentative: {v}\n"
                 for i, v in enumerate(["true", "yes", "sí", "Sí", "no", "false", '""'], 1)}
        got = {e["extra"]["slug"]: e["extra"].get("tentative") for e in self.manual_events(files)}
        self.assertEqual(got, {"2027-01-01-x1": True, "2027-02-01-x2": True, "2027-03-01-x3": True,
                               "2027-04-01-x4": True, "2027-05-01-x5": None, "2027-06-01-x6": None,
                               "2027-07-01-x7": None})

    def summer(self):
        return self.manual_events({"2027-06-25-neta65-summer-assembly.md": (
            'title: "NETA 65 Summer Assembly 2027"\ntitle_es: "Asamblea de Verano 2027 de NETA 65"\n'
            'start: 2027-06-25\nend: 2027-06-27\nlocation: "Venue to be announced"\n'
            'location_es: "Lugar por anunciarse"\ntentative: true\nlang: en\n')})[0]

    def test_location_in_spanish_and_venue_to_be_announced(self):
        ev = self.summer()
        self.assertEqual(ev["extra"]["own_i18n"]["location"], {"es": "Lugar por anunciarse"})
        self.assertIs(ev["extra"]["tentative"], True)
        ctx = ctx_with()
        with mock.patch.object(B, "ics_events", lambda c: []), \
                mock.patch.object(B.Ctx, "items", lambda self, name: [ev] if name == "manual_events" else []):
            evs = B.build_events(ctx)
        e = next(x for x in evs if x["id"] == ev["id"])
        self.assertIs(e["extra"]["location_tba"], True)
        self.assertIs(e["extra"]["tentative"], True)
        B.I18n(NoTranslator()).apply(e)
        self.assertEqual(e["i18n"]["location"], {"en": "Venue to be announced", "es": "Lugar por anunciarse"})

    def test_a_real_address_is_never_translated_and_tba_gets_the_sites_own_words(self):
        spring = self.manual_events({"a.md": 'title: Spring\nstart: 2027-03-19\nlocation: "DoubleTree, 4099 Valley '
                                              'View Ln, Dallas, TX 75244"\nlang: en\n'})[0]
        B.I18n(NoTranslator()).apply(spring)
        self.assertNotIn("location", spring["i18n"])                 # the page shows extra.location as it is
        tba = self.manual_events({"b.md": "title: Fall\nstart: 2027-09-17\nlocation: TBA\nlang: en\n"})[0]
        B.I18n(NoTranslator()).apply(tba)
        self.assertEqual(tba["i18n"]["location"], {"en": "TBA", "es": "Lugar por anunciarse"})
        spanish = self.manual_events({"c.md": 'title: Taller\nstart: 2027-01-09\nlocation: "Lugar por anunciarse"\n'
                                              'location_en: "Venue to be announced soon"\nlang: es\n'})[0]
        B.I18n(NoTranslator()).apply(spanish)
        self.assertEqual(spanish["i18n"]["location"], {"es": "Lugar por anunciarse", "en": "Venue to be announced soon"})
        for v in ("Venue to be announced", "Lugar por anunciarse", "TBA", "TBD.", "Location: to be determined",
                  "Por confirmar", "Sede: por definir"):
            self.assertTrue(B.location_is_tba(v), v)
        for v in ("Tyler, TX", "TBA Hall, 12 Main St", "", None, "Grupo Por Confirmar, Dallas"):
            self.assertFalse(B.location_is_tba(v), v)

    def test_a_location_es_left_behind_never_hides_the_confirmed_address(self):
        """The venue was confirmed (`location` has the address) but `location_es: "Lugar por anunciarse"` was
        not deleted: the address is shown in both languages (no hourglass, in the calendar files), and the
        chair is told which line to delete."""
        ev = self.manual_events({"2027-06-25-neta65-summer-assembly.md": (
            'title: "NETA 65 Summer Assembly 2027"\nstart: 2027-06-25\nend: 2027-06-27\n'
            'location: "Hilton Tyler, 1 Main St, Tyler, TX 75701"\nlocation_es: "Lugar por anunciarse"\nlang: en\n')})[0]
        ctx = ctx_with()
        with mock.patch.object(B, "ics_events", lambda c: []), \
                mock.patch.object(B.Ctx, "items", lambda self, name: [ev] if name == "manual_events" else []), \
                self.assertLogs(B.log, "WARNING"):       # a made-up venue (the real file still says TBA)
            evs = B.build_events(ctx)
        e = next(x for x in evs if x["id"] == ev["id"])
        self.assertNotIn("location_tba", e["extra"])
        B.I18n(NoTranslator()).apply(e)
        self.assertNotIn("location", e["i18n"])            # the pages show extra.location, in both languages
        self.assertEqual(ctx.raw_problems["content_events"], (
            "content/events/2027-06-25-neta65-summer-assembly.md: location_es says the venue is not known yet, but "
            "location: gives “Hilton Tyler, 1 Main St, Tyler, TX 75701” — that place is shown in both languages. "
            "Delete the location_es line."))
        # a status.json problem that is not a content source: manual_events itself did not fail
        status = B.build_status(ctx, None, B.I18n(None), {}, False, 0.0)
        self.assertNotEqual(next(s for s in status["sources"] if s["source"] == "manual_events").get("error"),
                            ctx.raw_problems["content_events"])


# --------------------------------------------------------------------------- several days
class MultiDay(TempState):
    def test_upcoming_through_the_last_day(self):
        ev = self.manual_events({"2027-03-19-spring.md": "title: Spring Assembly\nstart: 2027-03-19\nend: 2027-03-21\n"})[0]
        self.assertEqual((ev["extra"]["start"], ev["extra"]["end"], ev["extra"]["all_day"]), ("2027-03-19", "2027-03-21", True))
        # (like every event, the data keeps it one more day — cutoff = now − 24 h; the pages hide it at
        # midnight after its last day by themselves)
        for when, past in ((datetime(2027, 3, 20, 12, tzinfo=CHI), False),     # Saturday
                           (datetime(2027, 3, 21, 23, 0, tzinfo=CHI), False),   # Sunday night, the last day
                           (datetime(2027, 3, 22, 23, 0, tzinfo=CHI), False),   # the one-day grace
                           (datetime(2027, 3, 23, 0, 30, tzinfo=CHI), True),
                           (datetime(2027, 3, 23, 12, tzinfo=CHI), True)):
            ctx = ctx_with(now=when.astimezone(timezone.utc))
            with mock.patch.object(B, "ics_events", lambda c: []), \
                    mock.patch.object(B.Ctx, "items", lambda self, name: [ev] if name == "manual_events" else []):
                evs = B.build_events(ctx)
            got = next(e for e in evs if e["id"] == ev["id"])
            self.assertIs(got["extra"]["past"], past, when)

    def test_monthly_email_shows_the_days_and_the_place(self):
        """The monthly digest lists an event that took place with its day(s) and place — no time, no
        "to be confirmed" (it is over) — in the digest of the month it started in."""
        from scripts.notify import send_digest as D
        ev = self.manual_events({"2027-06-25-summer.md": (
            'title: "NETA 65 Summer Assembly 2027"\ntitle_es: "Asamblea de Verano 2027 de NETA 65"\nstart: 2027-06-25\n'
            'end: 2027-06-27\nlocation: "Venue to be announced"\nlocation_es: "Lugar por anunciarse"\ntentative: yes\n'
            'lang: en\n')})[0]
        B.I18n(NoTranslator()).apply(ev)
        en, es = D.event_row(ev, "en", D.Links("https://example.org")), D.event_row(ev, "es", D.Links("https://example.org"))
        self.assertEqual(en["when"], "Fri, Jun 25 – Sun, Jun 27")
        self.assertEqual(es["when"], "vie, 25 de jun – dom, 27 de jun")          # the website's spelling (Intl es-US)
        self.assertEqual((en["where"], es["where"]), ("Venue to be announced", "Lugar por anunciarse"))
        # … in the June 2027 digest, sent July 1 (not in May's, not in July's)
        with mock.patch.object(D, "load_items", lambda name: [ev] if name == "events" else []), \
                mock.patch.object(D, "load_config", lambda: {}):
            june = D.collect(datetime(2027, 7, 1, 15, 5, tzinfo=timezone.utc))
            july = D.collect(datetime(2027, 8, 1, 15, 5, tzinfo=timezone.utc))
            during = D.collect(datetime(2027, 6, 27, 20, 0, tzinfo=CHI).astimezone(timezone.utc))   # May's digest
        self.assertEqual(june["edition"]["key"], "2027-06")
        self.assertEqual([e["id"] for e in june["events"]], [ev["id"]])
        self.assertEqual((july["events"], during["events"]), ([], []))

    def test_monthly_email_uses_the_sites_multi_day_rule(self):
        """A timed event that only runs past midnight is ONE day (as on the website: more than 18 hours, or
        all-day over several dates); an end at midnight belongs to the day before. Days only, never a time."""
        from scripts.notify import send_digest as D
        links = D.Links("https://example.org")

        def when(start, end, all_day=False):
            return D.event_row({"kind": "event", "title": "X", "extra": {"start": start, "end": end, "all_day": all_day}},
                               "en", links)["when"]
        self.assertEqual(when("2026-10-03T19:00:00-05:00", "2026-10-04T01:00:00-05:00"), "Sat, Oct 3")
        self.assertEqual(when("2026-10-03T19:00:00-05:00", "2026-10-04T00:00:00-05:00"), "Sat, Oct 3")
        self.assertEqual(when("2026-10-03T09:00:00-05:00", "2026-10-04T16:00:00-05:00"), "Sat, Oct 3 – Sun, Oct 4")
        self.assertEqual(when("2027-03-19", "2027-03-21", True), "Fri, Mar 19 – Sun, Mar 21")
        self.assertEqual(when("2027-03-19", "2027-03-19", True), "Fri, Mar 19")


# --------------------------------------------------------------------------- dated Drive flyers
class DriveFlyers(TempState):
    """A flyer in the committee's Drive flyers/ folder whose name starts with a date is an event
    (drive.build_item → data/raw/drive.json → build_data.flyer_events)."""

    def flyers(self, *names: str) -> list[dict]:
        from scripts.sync import drive as D
        items = []
        for n, name in enumerate(names, 1):
            mime = "application/pdf" if name.lower().endswith(".pdf") else "image/jpeg"
            e = D.Entry(id=f"file{n}", name=name, mime=mime, modified="2026-09-24")
            items.append(D.build_item(D.Found(e, D.Panel(77, "Panel 77 (2027–2028)", "p77", "2027-2028_Panel77_GVLV"),
                                              ["flyers"], ["root", "p77", "fl"], seq=n), {}))
        return items

    def events(self, *names: str) -> list[dict]:
        items = self.flyers(*names)
        with mock.patch.object(B.Ctx, "items", lambda self, name: items if name == "drive" else []):
            return B.flyer_events(ctx_with())

    def test_times_past_midnight_noon_and_a_time_zone(self):
        evs = {e["title"]: e["extra"] for e in self.events(
            "2026-12-31 New Year's Eve Dance 8pm-1am @ Rowlett Alano Club.pdf",
            "2026-10-31 Halloween Dance 8pm-1am.pdf",
            "2026-10-17 Workshop noon-2pm.pdf",
            "2026-11-05 Nueva reunión abierta de La Viña - jueves a las 12 p. m. (hora del Este) por Zoom.png",
            "2026-10-24 Alcathon 7pm-7pm.pdf",
            "2026-10-17 GV Writing Workshop 2-4pm @ Tyler, TX.pdf")}
        # an end after midnight is the next morning (1 AM CST), not 19 hours before the start
        nye = evs["New Year's Eve Dance"]
        self.assertEqual((nye["start"], nye["end"], nye["location"]),
                         ("2027-01-01T02:00:00Z", "2027-01-01T07:00:00Z", "Rowlett Alano Club"))
        hw = evs["Halloween Dance"]                   # the night daylight saving ends: 1 AM is still CDT
        self.assertEqual((hw["start"], hw["end"]), ("2026-11-01T01:00:00Z", "2026-11-01T06:00:00Z"))
        self.assertEqual((evs["Workshop"]["start"], evs["Workshop"]["end"]), ("2026-10-17T17:00:00Z", "2026-10-17T19:00:00Z"))
        # 12 p.m. Eastern, not Central
        lv = evs["Nueva reunión abierta de La Viña"]
        self.assertEqual((lv["start"], lv["end"], lv["location"]), ("2026-11-05T17:00:00Z", None, "jueves por Zoom"))
        self.assertEqual((evs["Alcathon"]["start"], evs["Alcathon"]["end"]), ("2026-10-25T00:00:00Z", None))
        gv = evs["GV Writing Workshop"]
        self.assertEqual((gv["start"], gv["end"], gv["city"]), ("2026-10-17T19:00:00Z", "2026-10-17T21:00:00Z", "Tyler"))
        # the zone is kept in data/raw/drive.json only when the name gives one
        zones = [it["extra"].get("event_tz") for it in self.flyers(
            "2026-11-05 Open meeting 12pm ET on Zoom.pdf", "2026-10-17 Workshop 2-4pm.pdf", "2026-10-17 Workshop ET.pdf")]
        self.assertEqual(zones, ["America/New_York", None, None])

    def test_a_phone_or_screenshot_name_is_not_an_event(self):
        """A picture saved under its camera / WhatsApp / screenshot name carries the day it was TAKEN: no
        event on that day with a junk title (the flyer stays in the library). A date the chair wrote at the
        start of the name is the event's, whatever follows it — written in any form the README allows
        ("March 14, 2027", "14 de marzo de 2027"), not only as 2026-10-17."""
        capture = ["WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg", "IMG_20261017_183316.jpg",
                   "Screenshot_20261017-183316.png", "20261017_183316.jpg", "PXL_20261017_183316123.jpg"]
        dated = ["2026-10-17 IMG_1234.jpg", "2026-10-17 6.30 PM.jpg", "10-17-2026 IMG_1234.jpg", "2026-10-17.pdf",
                 "2026-10-17 GV Writing Workshop 2-4pm @ Tyler, TX.jpg", "October 17, 2026 at 7 PM.jpg",
                 "17 de octubre de 2026 a las 7 pm.jpg", "2026.10.17 7 PM.jpg", "2026_10_17 IMG_1234.jpg"]
        items = self.flyers(*capture, *dated)
        self.assertEqual([it["extra"].get("event_date") for it in items[:len(capture)]], [None] * len(capture))
        self.assertTrue(all(it["kind"] == "photo" and it["category"] == "flyers" for it in items[:len(capture)]))
        evs = self.events(*capture, *dated)
        self.assertEqual(sorted(e["extra"]["drive_id"] for e in evs), sorted(f"drive:file{n}" for n in range(6, 15)))
        self.assertEqual({B.local_day(ctx_with(), e["extra"]["start"]) for e in evs}, {"2026-10-17"})
        starts = {e["extra"]["drive_id"]: e["extra"]["start"] for e in evs}
        self.assertEqual(starts["drive:file7"], "2026-10-17T23:30:00Z")          # "2026-10-17 6.30 PM": 6:30 PM CDT
        self.assertEqual({starts[f"drive:file{n}"] for n in (11, 12, 13)}, {"2026-10-18T00:00:00Z"})      # 7 PM CDT

    def test_a_range_of_days_spans_its_days(self):
        """A flyer named with a range of days ("Assembly March 14 - 16, 2027.pdf") is ONE event over those days —
        all day to its last day, or from the start time to the end time on the last day — not a one-day event."""
        names = ["Assembly March 14 - 16, 2027.pdf", "2027-03-19 - 2027-03-21 NETA 65 Spring Assembly.pdf",
                 "Asamblea del 14 al 16 de mayo de 2027.pdf", "Roundup March 30 - April 2, 2027 9am-5pm @ Tyler, TX.pdf",
                 "Convention June 4 - 6, 2027 9am.pdf", "2027-03-14 Workshop.pdf"]
        raw = {it["extra"]["name"]: it["extra"] for it in self.flyers(*names)}
        self.assertEqual([(raw[n]["event_date"], raw[n].get("event_end_date")) for n in names],
                         [("2027-03-14", "2027-03-16"), ("2027-03-19", "2027-03-21"), ("2027-05-14", "2027-05-16"),
                          ("2027-03-30", "2027-04-02"), ("2027-06-04", "2027-06-06"), ("2027-03-14", None)])
        evs = {e["title"]: e["extra"] for e in self.events(*names)}
        self.assertEqual((evs["Assembly"]["start"], evs["Assembly"]["end"], evs["Assembly"]["all_day"]), ("2027-03-14", "2027-03-16", True))
        self.assertEqual((evs["NETA 65 Spring Assembly"]["start"], evs["NETA 65 Spring Assembly"]["end"]), ("2027-03-19", "2027-03-21"))
        self.assertEqual((evs["Asamblea"]["start"], evs["Asamblea"]["end"]), ("2027-05-14", "2027-05-16"))
        ru = evs["Roundup"]                                   # 9 AM CDT on the first day to 5 PM CDT on the last
        self.assertEqual((ru["start"], ru["end"], ru["all_day"], ru["city"]), ("2027-03-30T14:00:00Z", "2027-04-02T22:00:00Z", False, "Tyler"))
        cv = evs["Convention"]                                # no end time: to the end of its last day
        self.assertEqual((cv["start"], cv["end"], cv["all_day"]), ("2027-06-04T14:00:00Z", "2027-06-06", False))
        ctx = ctx_with()
        self.assertEqual(B.event_end_ts(ctx, {"extra": cv}),
                         datetime(2027, 6, 6, 23, 59, tzinfo=ZoneInfo("America/Chicago")).timestamp())
        self.assertEqual((evs["Workshop"]["start"], evs["Workshop"]["end"]), ("2027-03-14", None), "one day: as before")

    def test_until_in_a_flyer_name_is_not_its_start(self):
        """Only a bulletin post keeps an undated "(until …)" in its headline: in a flyer's name it is dropped as
        before, so the time in it ("until 5pm", "hasta las 3 pm") never becomes the event's start."""
        evs = self.events("2026-10-17 Book sale (until 5pm).pdf", "2026-10-17 Open House (hasta las 3 pm) @ Iglesia.pdf")
        self.assertEqual(sorted((e["title"], e["extra"]["start"]) for e in evs),
                         [("Book sale", "2026-10-17"), ("Open House", "2026-10-17")])

    def test_the_same_flyer_twice_is_one_event(self):
        """A PDF and a picture of the same flyer ("X.pdf" + "X (1).jpg") are ONE event, the PDF's; two different
        flyers of the same day, time and place (a GV and an LV workshop) stay two."""
        items = self.flyers("2026-10-17 GV Writing Workshop 2-4pm @ Tyler, TX (1).jpg",
                            "2026-10-17 GV Writing Workshop 2-4pm @ Tyler, TX.pdf",
                            "2026-10-17 LV Writing Workshop 2-4pm @ Tyler, TX.pdf")
        with mock.patch.object(B, "ics_events", lambda c: []), \
                mock.patch.object(B.Ctx, "items", lambda self, name: items if name == "drive" else []):
            evs = [e for e in B.build_events(ctx_with()) if e["category"] == "flyer"]
        self.assertEqual(sorted((e["title"], e["extra"]["drive_id"], e["extra"]["is_pdf"]) for e in evs),
                         [("GV Writing Workshop", "drive:file2", True), ("LV Writing Workshop", "drive:file3", True)])


# --------------------------------------------------------------------------- the committee meeting's skip dates
class MeetingSkipDates(unittest.TestCase):
    def test_a_date_that_is_not_a_meeting_day_is_reported_and_ignored(self):
        cfg = {"weekday": "wednesday", "week_of_month": 3,
               "skip_dates": ["2026-12-16", "2026-12-17", "2027-01-13", "garbage", "2027-02-30"]}
        notes = M.meeting_skip_notes(cfg)
        self.assertEqual(notes, [
            "skip date “2026-12-17” is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16)",
            "skip date “2027-01-13” is not the 3rd Wednesday of its month — ignored (that month's is 2027-01-20)",
            "skip date “garbage” is not a date like \"2027-01-09\" — ignored",
            "skip date “2027-02-30” is not a date like \"2027-01-09\" — ignored"])
        self.assertEqual(M.meeting_rule(cfg).skip, frozenset({"2026-12-16"}))
        self.assertEqual(M.meeting_skip_notes({"skip_dates": []}), [])
        self.assertEqual(M.meeting_skip_notes({}), [])

    def test_the_note_reaches_status_json(self):
        cfg = json.loads(json.dumps(CFG))
        cfg["meeting"]["skip_dates"] = ["2026-12-17"]
        ctx = ctx_with(cfg)
        with mock.patch.object(B, "ics_events", lambda c: []), mock.patch.object(B, "committee_meetings", lambda c: []):
            B.build_events(ctx)
        self.assertEqual(ctx.raw_problems["meeting"], "config/site.yml meeting: skip date “2026-12-17” is not the "
                                                      "3rd Wednesday of its month — ignored (that month's is 2026-12-16)")

    def test_the_meetings_follow_the_builds_clock_and_settings(self):
        """Like the recurring events, the committee meetings are counted from the BUILD's clock and settings
        (Ctx.now, Ctx.cfg), never the real clock and config/site.yml: a test on a fixed day (TODAY) keeps its
        meeting inside that day's calendar horizon whenever the suite runs (FeedDuplicates' booth-and-meeting
        test broke for good once the real September 2027 meeting was over)."""
        cfg = json.loads(json.dumps(CFG))
        cfg["meeting"].update({"weekday": "thursday", "week_of_month": 2, "start": "18:30", "end": "19:30"})
        ms = B.committee_meetings(ctx_with(cfg, now=datetime(2030, 1, 1, 12, tzinfo=timezone.utc)))
        self.assertEqual([m["id"] for m in ms[:2]], ["ev:committee:2030-01-10", "ev:committee:2030-02-14"])
        self.assertEqual((ms[0]["extra"]["start"], ms[0]["extra"]["end"]), ("2030-01-11T00:30:00Z", "2030-01-11T01:30:00Z"))
        self.assertEqual(len(ms), 12)
        # the real clock no longer matters: TODAY's first meeting, even a year after the last one in the horizon
        later = datetime(2027, 10, 1, 12, tzinfo=timezone.utc)

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return later.astimezone(tz) if tz else later.replace(tzinfo=None)
        with mock.patch.object(M, "datetime", Clock):
            self.assertEqual(B.committee_meetings(ctx_with())[0]["id"], "ev:committee:2026-10-21")


# --------------------------------------------------------------------------- our own calendar files, read back
# src/pages/events-ics.11ty.js as the build runs it (its `this.t`, the build's clock — fixed here, as it would be
# read by the feed and by /events/ alike) and the cards /events/ has: events.njk lists every date still to come and,
# under "Past events", the newest 40 that took place — but no committee meeting and no date of a monthly series.
FEED_JS = r"""
const RealDate = Date;
const fixed = RealDate.parse(input.now);
class FixedDate extends RealDate {
  constructor(...a) { if (a.length) super(...a); else super(fixed); }
  static now() { return fixed; }
}
const conf = await imp("eleventy.config.js");
const feed = await imp("src/pages/events-ics.11ty.js");
const res = {};
globalThis.Date = FixedDate;
try {
  for (const lang of ["en", "es"]) {
    const ics = feed.render.call({ t: (k, l, v) => conf.translateKey(k, l, v) },
                                 { lang, site: input.site, db: { events: { items: input.items } } });
    const all = filters.cmCollapseRecurring(filters.cmEvents(input.items, input.site, lang));
    const pastRows = all.filter((e) => e.past && !e.committee && !e.recurring).reverse().slice(0, 40);
    res[lang] = { ics, cards: [...all.filter((e) => !e.past), ...pastRows].map((e) => e.anchor) };
  }
} finally {
  globalThis.Date = RealDate;
}
out(res);
"""


class OurCalendarFiles(TempState):
    """/events.ics and /es/events.ics, read back with icalendar: every entry's link — its URL and the "Details:"
    line — leads somewhere that is there. A date still to come, or a one-off event that took place, links to its card
    on /events/ (an anchor the page has); a monthly series' date that has passed (the files keep it 90 days, for
    subscribers) to /events/ itself, as the page lists only a series' dates still to come; a committee meeting to
    /meetings/, an event with a page of its own to that page. And a series' repeat line names its time zone: the
    calendar shows the date's start in its reader's zone, right beside it."""

    NOW = datetime(2026, 9, 24, 21, 0, tzinfo=timezone.utc)      # Thu Sep 24, 4 PM CDT: that day's workshop is over

    def test_the_cards_events_njk_has(self):
        # FEED_JS's list of the cards /events/ has is this selection: every date still to come (a card each, with
        # its anchor), and the newest 40 one-off events that took place
        page = (ROOT / "src" / "pages" / "events.njk").read_text(encoding="utf-8")
        for bit in ('{%- set all = db.events.items | cmEvents(site, lang) | cmCollapseRecurring -%}',
                    '{%- set upcoming = all | where("past", false) -%}',
                    '{%- set past = all | where("past", true) | whereNot("committee", true) | whereNot("recurring", true) | reverse -%}',
                    '{% for ev in past | limit(40) %}', '<li id="{{ ev.anchor }}" data-group="{{ ev.group }}"',
                    '<li id="{{ ev.anchor }}" class="flex flex-wrap'):
            self.assertIn(bit, page)

    def test_every_link_is_there_and_the_times_say_their_zone(self):
        from icalendar import Calendar
        if str(Path(__file__).resolve().parent) not in sys.path:    # run as tests.test_events_feeds
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        from nodejs import run_js
        cfg = json.loads(json.dumps(CFG))
        cfg["recurring_events"] = [
            {"key": "lv-monthly-workshop", "title": "La Viña Monthly Virtual Workshop (in Spanish)",
             "title_es": "Taller Mensual y Virtual de La Viña", "host": "lv", "week_of_month": 4, "weekday": "thursday",
             "start": "14:00", "end": "15:00", "online_url": "https://us06web.zoom.us/j/81595931777"},
            {"key": "citywide-dallas", "title": "GV/LV booth at CityWide Dallas", "title_es": "Mesa de GV/LV en CityWide Dallas",
             "week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "20:00",
             "location": "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220",
             "url": "https://citywidedallasaa.org"}]
        # a workshop that took place (a row of its own under "Past events") and one still to come, no page of their own
        manual = self.manual_events({
            "2026-09-12-gv-writing-workshop-denton.md": ('title: "Grapevine Writing Workshop — Denton"\n'
                                                         "start: 2026-09-12T14:00:00-05:00\nend: 2026-09-12T16:00:00-05:00\n"
                                                         "location: Denton, TX\nlang: en\n"),
            "2026-10-24-gv-writing-workshop-tyler.md": ('title: "Grapevine Writing Workshop — Tyler"\n'
                                                        "start: 2026-10-24T14:00:00-05:00\nend: 2026-10-24T16:00:00-05:00\n"
                                                        "location: Tyler, TX\nlang: en\n")})
        with mock.patch.object(B, "ics_events", lambda c: []), \
                mock.patch.object(B.Ctx, "items", lambda self, name: manual if name == "manual_events" else []):
            items = B.build_events(ctx_with(cfg, now=self.NOW))
        site = {"url": "https://example.org/site", "meeting": cfg["meeting"], "recurring_events": cfg["recurring_events"],
                "links": {}}
        res = run_js(self, FEED_JS, data={"items": items, "site": site, "now": self.NOW.isoformat()})
        lv = "ev-recurring-lv-monthly-workshop-"
        for lang in ("en", "es"):
            page = "https://example.org/site" + ("/es" if lang == "es" else "") + "/events/"
            cal = Calendar.from_ical(res[lang]["ics"])
            self.assertEqual([e for c in cal.walk() for e in (getattr(c, "errors", None) or [])], [])
            entries = {str(e["UID"]).split("@")[0].removesuffix("-es"): e for e in cal.walk("VEVENT")}
            urls = {uid: str(e["URL"]) for uid, e in entries.items()}
            # the series' dates: over (an hour ago, and in August) → the page; still to come → its card
            self.assertEqual((urls[lv + "2026-09-24"], urls[lv + "2026-08-27"]), (page, page), lang)
            self.assertEqual(urls[lv + "2026-10-22"], page + "#" + lv + "2026-10-22")
            self.assertEqual(urls["ev-recurring-citywide-dallas-2026-09-12"], "https://citywidedallasaa.org")
            # one-off workshops keep their card's anchor, past or not: "Past events" lists the one that took place
            self.assertEqual(urls["ev-manual-2026-09-12-gv-writing-workshop-denton"], page + "#2026-09-12-gv-writing-workshop-denton")
            self.assertEqual(urls["ev-manual-2026-10-24-gv-writing-workshop-tyler"], page + "#2026-10-24-gv-writing-workshop-tyler")
            details = {"en": "Details: ", "es": "Detalles: "}[lang]
            for uid, e in entries.items():
                url, desc = urls[uid], str(e.get("DESCRIPTION", "")).splitlines()
                with self.subTest(lang=lang, uid=uid):
                    if url.startswith(page + "#"):
                        self.assertIn(url[len(page) + 1:], res[lang]["cards"])            # the page has that card
                    elif url == page:                                                # only a series' date that is over
                        self.assertTrue(uid.startswith(lv), uid)
                        self.assertLessEqual(e["DTEND"].dt, self.NOW)
                    else:
                        self.assertIn(url, ("https://example.org/site" + ("/es" if lang == "es" else "") + "/meetings/",
                                            "https://citywidedallasaa.org"))
                    self.assertEqual([ln for ln in desc if ln.startswith(details)], [details + url])
                    if uid.startswith("ev-recurring-"):
                        line = next(ln for ln in desc if ln.startswith(("Every ", "Cada ")))
                        self.assertTrue(re.sub("[\u2009\u202f\u00a0]", " ", line).endswith(
                            {"en": " PM Central time", "es": " p. m., hora del Centro"}[lang]), line)
            self.assertEqual(sum(url == page for url in urls.values()), 3, lang)     # Jul 23, Aug 27, Sep 24


# --------------------------------------------------------------------------- the flyers on /events/
# The six workshops' flyers are on neta65.org, whose bot check (Cloudflare) turns other sites away: /events/ could
# show no picture of them. On 2026-10-02 they were copied into the panel's Drive "flyers" folder, with names
# without a date (a dated name makes drive.py create a second event), and the files link those copies.
SIX_WORKSHOPS = ["2026-09-26-lv-writing-workshop-fort-worth.md", "2026-10-03-gv-writing-workshop-arlington.md",
                 "2026-10-07-lv-writing-workshop-mansfield.md", "2026-10-17-lv-recording-workshop-duncanville.md",
                 "2026-10-26-lv-writing-workshop-tyler.md", "2026-11-07-lv-information-workshop-longview.md"]
DRIVE_FLYER = re.compile(r"https://drive\.google\.com/file/d/([\w-]{20,})/view")

# The events' flyers as /events/ shows them (eleventy/filters/committee.js normalizeEvents → ev.flyer).
FLYERS_JS = r"""
const res = {};
for (const lang of ["en", "es"]) res[lang] = filters.cmEvents(input.items, input.site, lang).map((e) => ({ id: e.id, flyer: e.flyer }));
out(res);
"""

# src/pages/events.njk as the build renders it: Eleventy with the site's own config, only that page (the ONLY
# switch of eleventy.config.js), and these events in place of data/site/events.json (all other data as committed).
EVENTS_PAGE_JS = r"""
process.env.ONLY = "events.njk";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-events-page-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { ...(data.db || {}).events, items: input.items } }),
      });
    },
  });
  const pages = (await elev.toJSON()).filter((p) => /\/events\/$/.test(p.url));
  out(Object.fromEntries(pages.map((p) => [p.url.includes("/es/") ? "es" : "en", p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def event_cards(html: str) -> dict[str, str]:
    """The cards of the upcoming events (anchor → the card's HTML, up to its </article>)."""
    return {m.group(1): m.group(0) for m in re.finditer(r'<li id="([^"]+)" data-group="[\s\S]*?</article>', html)}


def card_lines(card: str) -> list[str]:
    """The lines under an event card's title — its time, place, "Online on Zoom", meeting ID … — as text."""
    ul = re.search(r'<ul class="mt-2 flex[^"]*">([\s\S]*?)</ul>', card).group(1)
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", re.sub(r"<svg[\s\S]*?</svg>", "", li))).strip()
            for li in re.findall(r"<li[^>]*>([\s\S]*?)</li>", ul)]


class FlyersOnTheEventsPage(TempState):
    """Every event with a flyer shows it on the side of its card, the same way: its picture when there is one —
    a Drive flyer's, from the Drive by the file's id, also for a content/events `flyer:` that links a Drive copy —
    else the tile's own flyer icon and the word "Flyer" / "Volante"; never nothing. Same link and preview as the
    card's "View flyer" button."""

    def node(self, script: str, data: dict) -> dict:
        if str(Path(__file__).resolve().parent) not in sys.path:    # run as tests.test_events_feeds
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        from nodejs import run_js
        return run_js(self, script, data=data)

    def test_the_six_workshops_link_their_drive_copies(self):
        # (a workshop's file may be deleted once it is over: then there is nothing to check)
        folder = ROOT / "content" / "events"
        present = [n for n in SIX_WORKSHOPS if (folder / n).exists()]
        for name in present:
            with self.subTest(file=name):
                ev = A.parse_event(folder / name, CHI)
                self.assertRegex(ev["extra"]["flyer_url"] or "", DRIVE_FLYER)
                self.assertIsNone(ev["extra"]["flyer_thumb"])           # no picture of its own: the Drive's
                # the neta65.org address it replaced stays in the file, as a note (a YAML comment)
                text = (folder / name).read_text(encoding="utf-8")
                self.assertRegex(text, r"\n# flyer: a copy of https://neta65\.org/\S+, made \d{4}-\d{2}-\d{2}\b[^\n]*\nflyer: ")
        if not present:
            return
        site = {"url": "https://example.org/site", "meeting": CFG["meeting"], "links": {}}
        items = [A.parse_event(folder / n, CHI) for n in present]
        res = self.node(FLYERS_JS, {"items": items, "site": site})
        for lang in ("en", "es"):
            got = {e["id"]: e["flyer"] for e in res[lang] if e["id"].startswith("ev:manual:")}
            self.assertEqual(len(got), len(present), lang)
            for it in items:
                fid = DRIVE_FLYER.fullmatch(it["extra"]["flyer_url"]).group(1)
                with self.subTest(lang=lang, event=it["id"]):
                    self.assertEqual(got[it["id"]], {"view": it["extra"]["flyer_url"],
                                                     "preview": f"https://drive.google.com/file/d/{fid}/preview",
                                                     "thumb": f"https://lh3.googleusercontent.com/d/{fid}=w320"})

    def test_every_card_with_a_flyer_has_the_side_tile(self):
        day = (datetime.now(CHI) + timedelta(days=10)).replace(hour=19, minute=0, second=0, microsecond=0)

        def when(days: int) -> str:
            start = day + timedelta(days=days)
            return f"start: {start.isoformat()}\nend: {(start + timedelta(hours=2)).isoformat()}\n"
        drive_id = "1gghtYzCE6Dl_IQ5_7yLueZviIK_nZqwN"
        neta = "https://neta65.org/wp-content/uploads/2026/09/TALLER-DE-ESCRITURA-LIBRO-GRANDE.jpeg"
        manual = self.manual_events({
            # a Drive copy, as the six workshops now link theirs: the Drive's picture
            "zz-drive-flyer.md": ('title: "Drive Flyer Workshop"\ntitle_es: "Taller con volante en Drive"\n' + when(0)
                                  + f'location: "Tyler, TX"\nflyer: "https://drive.google.com/file/d/{drive_id}/view"\nlang: en\n'),
            # a flyer only neta65.org can show: no picture — the tile's own icon and word
            "zz-neta-flyer.md": ('title: "Neta Flyer Workshop"\ntitle_es: "Taller con volante en neta65.org"\n' + when(1)
                                 + f'location: "Tyler, TX"\nflyer: "{neta}"\nlang: en\n'),
            "zz-no-flyer.md": 'title: "No Flyer Workshop"\ntitle_es: "Taller sin volante"\n' + when(2) + 'location: "Tyler, TX"\nlang: en\n'})
        # an outside calendar's event whose flyer is a picture (an .ics ATTACH): that picture, as before
        feed = {"id": "ev:ics:zz-feed-picture", "source": "calendar", "kind": "event", "category": "neta65",
                "url": "https://example.org/event/zz/", "title": "Feed Picture Workshop", "summary": "", "lang": "en",
                "date": (day + timedelta(days=3)).isoformat(), "status": "ok", "tags": [],
                "extra": {"start": (day + timedelta(days=3)).isoformat(), "end": (day + timedelta(days=3, hours=2)).isoformat(),
                          "all_day": False, "location": "Tyler, TX", "online_url": None,
                          "flyer_url": "https://example.org/flyer.jpg", "flyer_thumb": "https://example.org/flyer.jpg"}}
        pages = self.node(EVENTS_PAGE_JS, {"items": manual + [feed]})
        self.assertEqual(sorted(pages), ["en", "es"])
        tile = re.compile(r'<a class="cm-flyer-thumb" href="([^"]+)"[^>]*>([\s\S]*?)</a>')
        for lang, word, view in (("en", "Flyer", "View flyer"), ("es", "Volante", "Ver volante")):
            cards = event_cards(pages[lang])
            with self.subTest(lang=lang):
                self.assertTrue({"zz-drive-flyer", "zz-neta-flyer", "zz-no-flyer"} <= set(cards), sorted(cards))
                # no picture the site can show: the same tile, with its own flyer icon and the word
                m = tile.search(cards["zz-neta-flyer"])
                self.assertIsNotNone(m, "a flyer without a picture has the side tile")
                self.assertEqual(m.group(1), neta)
                self.assertIn(f'data-cm-preview="{neta}"', m.group(0))
                self.assertIn(f'aria-label="{view}: ', m.group(0))
                self.assertNotIn("<img", m.group(2))
                self.assertRegex(m.group(2), r'<span class="cm-flyer-fallback" aria-hidden="true"><svg[^>]*>[\s\S]*?</svg>'
                                             rf'<span class="cm-flyer-word">{word}</span></span>')
                # a Drive copy: the Drive's picture, and the Drive's preview
                m = tile.search(cards["zz-drive-flyer"])
                self.assertIsNotNone(m)
                self.assertIn(f'<img src="https://lh3.googleusercontent.com/d/{drive_id}=w320"', m.group(2))
                self.assertIn(f'data-cm-preview="https://drive.google.com/file/d/{drive_id}/preview"', m.group(0))
                self.assertIn(f'<span class="cm-flyer-word">{word}</span>', m.group(2))    # under it until it loads
                # an outside calendar's picture: shown as before
                m = tile.search(cards["ev-ics-zz-feed-picture"])
                self.assertIsNotNone(m)
                self.assertIn('<img src="https://example.org/flyer.jpg"', m.group(2))
                # no flyer: no tile
                self.assertNotIn("cm-flyer-thumb", cards["zz-no-flyer"])
                # the rule, on every card of the page: a "View flyer" button ⇔ the side tile (one), same flyer
                for anchor, card in cards.items():
                    buttons = re.findall(rf'<a class="btn-secondary btn-sm" href="([^"]+)"[^>]*>(?:(?!</a>)[\s\S])*?{view}</a>', card)
                    tiles = tile.findall(card)
                    self.assertEqual([t[0] for t in tiles], buttons, anchor)


# --------------------------------------------------------------------------- online and hybrid events
class OnlineAndHybridEvents(TempState):
    """A content/events file with an `online_url` gets its platform from the link (build_data.build_events), as
    `recurring_events:` and the calendars' events do: its card says "Online on Zoom" / "En línea por Zoom", as
    content/events/README.md promises, not just "Online". A hybrid event (a place AND an online link, like the
    Arlington workshop) is both for search engines too: the structured data on /events/ gives its Place and its
    VirtualLocation, attendance "Mixed" — its address is not lost. And the members' help on /events/ ("Add an
    event") explains both kinds of flyers: a dated name makes an event; the flyer of an event written in
    content/events gets a name without a date and is linked with `flyer:` (a dated one would list it twice)."""

    PLACE = "Primary Purpose Group, 1802 West Division Street, Arlington, TX 76012"
    _pages: dict[str, str] | None = None          # /events/ EN + ES, rendered once for the class

    def events(self) -> list[dict]:
        """Four content/events files, ten days on, through build_events as the daily update runs it."""
        day = (datetime.now(CHI) + timedelta(days=10)).replace(hour=14, minute=0, second=0, microsecond=0)

        def when(days: int) -> str:
            start = day + timedelta(days=days)
            return f"start: {start.isoformat()}\nend: {(start + timedelta(hours=3)).isoformat()}\n"
        manual = self.manual_events({
            "zz-hybrid.md": ('title: "Hybrid Writing Workshop"\ntitle_es: "Taller de escritura híbrido"\n' + when(0)
                             + f'location: "{self.PLACE}"\n'
                             'online_url: "https://us02web.zoom.us/j/9494767497"\nmeeting_id: "949 476 7497"\nlang: en\n'),
            "zz-online.md": ('title: "Online Writing Workshop"\ntitle_es: "Taller de escritura en línea"\n' + when(1)
                             + 'online_url: "https://meet.google.com/abc-defg-hij"\nlang: en\n'),
            "zz-other-link.md": ('title: "Streamed Workshop"\ntitle_es: "Taller transmitido"\n' + when(2)
                                 + 'online_url: "https://example.org/live"\nlang: en\n'),
            "zz-in-person.md": ('title: "In-person Workshop"\ntitle_es: "Taller en persona"\n' + when(3)
                                + 'location: "Tyler, TX"\nlang: en\n')})
        with mock.patch.object(B, "ics_events", lambda c: []), \
                mock.patch.object(B.Ctx, "items", lambda self, name: manual if name == "manual_events" else []):
            return B.build_events(ctx_with(now=datetime.now(timezone.utc)))

    def pages(self) -> dict[str, str]:
        if OnlineAndHybridEvents._pages is None:
            if str(Path(__file__).resolve().parent) not in sys.path:    # run as tests.test_events_feeds
                sys.path.insert(0, str(Path(__file__).resolve().parent))
            from nodejs import run_js
            OnlineAndHybridEvents._pages = run_js(self, EVENTS_PAGE_JS, data={"items": self.events()})
        return OnlineAndHybridEvents._pages

    def test_a_files_online_link_gives_its_platform(self):
        extra = {e["id"].removeprefix("ev:manual:"): e["extra"] for e in self.events() if e["id"].startswith("ev:manual:")}
        self.assertEqual(extra["zz-hybrid"].get("platform"), "Zoom")
        self.assertEqual(extra["zz-online"].get("platform"), "Google Meet")
        self.assertIsNone(extra["zz-other-link"].get("platform"))       # a link from anywhere else: just "Online"
        self.assertIsNone(extra["zz-in-person"].get("platform"))

    def test_the_card_names_the_platform_and_search_engines_get_both(self):
        pages = self.pages()
        mode = "https://schema.org/{}EventAttendanceMode".format
        for lang, online in (("en", "Online on {}"), ("es", "En línea por {}")):
            cards = event_cards(pages[lang])
            ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', pages[lang], re.S).group(1))
            by = {e["url"].rsplit("#", 1)[1]: e for e in ld["@graph"]}
            with self.subTest(lang=lang):
                # the cards: the place AND the platform; an online-only one: its platform; another link: "Online"
                hybrid = card_lines(cards["zz-hybrid"])
                self.assertIn(self.PLACE, hybrid)
                self.assertIn(online.format("Zoom"), hybrid)
                self.assertIn(online.format("Google Meet"), card_lines(cards["zz-online"]))
                self.assertIn({"en": "Online", "es": "En línea"}[lang], card_lines(cards["zz-other-link"]))
                # search engines: a hybrid event is Mixed, with its Place and its VirtualLocation (this card)
                hybrid = by["zz-hybrid"]
                self.assertEqual(hybrid["eventAttendanceMode"], mode("Mixed"))
                self.assertEqual(hybrid["location"], [
                    {"@type": "Place", "name": self.PLACE, "address": self.PLACE},
                    {"@type": "VirtualLocation", "url": hybrid["url"]}])
                self.assertTrue(hybrid["url"].endswith("/events/#zz-hybrid"), hybrid["url"])
                # …and the others as before: online only, in person only
                for anchor, want, kind in (("zz-online", "Online", "VirtualLocation"), ("zz-other-link", "Online", "VirtualLocation"),
                                           ("zz-in-person", "Offline", "Place")):
                    self.assertEqual((by[anchor]["eventAttendanceMode"], by[anchor]["location"]["@type"]), (mode(want), kind), anchor)
                # the committee meeting is online only: its "location" (Zoom) is the platform, never a place
                meetings = [e for a, e in by.items() if a.startswith("ev-committee-")]
                self.assertTrue(meetings)
                for e in meetings:
                    self.assertEqual((e["eventAttendanceMode"], e["location"]["@type"]), (mode("Online"), "VirtualLocation"))

    def test_the_members_help_explains_both_kinds_of_flyers(self):
        pages = self.pages()
        for lang in ("en", "es"):
            m = re.search(r'<details class="card group" id="how-events">([\s\S]*?)</details>', pages[lang])
            self.assertIsNotNone(m, lang)
            help_ = m.group(1)
            with self.subTest(lang=lang):
                # a dated name makes an event; an event written in content/events links its flyer (`flyer:`)
                for bit in ("<code>content/events</code>", "<code>flyer:</code>",
                            {"en": "with the date at the start of the file name",
                             "es": "con la fecha al inicio del nombre del archivo"}[lang],
                            {"en": "a name that does not start with a date",
                             "es": "un nombre que no empiece con una fecha"}[lang]):
                    self.assertTrue(bit in help_, f"the members' help has {bit!r}")
                # the examples: two dated names (events of their own) and one without a date (a linked flyer)
                names = re.findall(r'<span role="cell" class="cm-naming-file">[\s\S]*?<code>([^<]+)</code>', help_)
                self.assertEqual([bool(re.match(r"\d{4}-\d{2}-\d{2} ", n)) for n in names], [True, True, False], names)
        # the README says the same: a flyer for a file here gets a name without a date
        readme = (ROOT / "content" / "events" / "README.md").read_text(encoding="utf-8")
        self.assertIn("with a name **without a date**", readme)


class RunSummary(unittest.TestCase):
    """The "Write run summary" step of .github/workflows/update.yml, run on a status.json with a blocked
    feed: it is listed as information, and it is NOT a source that stopped updating (no weekly issue)."""

    def test_blocked_feed_is_informational(self):
        wf = yaml.safe_load((ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8"))
        step = next(s for s in wf["jobs"]["sync"]["steps"] if s.get("name") == "Write run summary")
        code = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        tmp = Path(tempfile.mkdtemp(prefix="gv-summary-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "data" / "site").mkdir(parents=True)
        week_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = {"fixture": False, "sources": [
            {"source": "manual_events", "label": "Events (content/events)", "ok": True, "updated": week_ago, "count": 9}],
            "feeds": [{"key": "neta-65-workshops", "label": "NETA 65 workshops", "url": FEED_URL, "state": "blocked",
                       "http_status": 403, "events_count": 11, "duplicates": 8, "last_success": "2026-09-20T15:00:00Z",
                       "checked_this_run": True, "notes": [
                           "content/events/2026-10-03-gv-writing-workshop-arlington.md: the “NETA 65 workshops” "
                           "calendar lists its event page (https://neta65.org/event/grapevine-writing-workshop-6/) on "
                           "2026-10-10, but the file says 2026-10-03. If the date changed, correct start: and end: in "
                           "the file; if it is another event, give the file its own url:."]}],
            "problems": {"content_events": "content/events/2027-06-25-x.md: location_es says the venue is not known "
                                           "yet, but location: gives “Hilton Tyler” — that place is shown in both "
                                           "languages. Delete the location_es line."}}
        (tmp / "data" / "site" / "status.json").write_text(json.dumps(status), encoding="utf-8")
        (tmp / "script.py").write_text(code, encoding="utf-8")
        env = dict(os.environ, GITHUB_STEP_SUMMARY=str(tmp / "summary.md"), GITHUB_OUTPUT=str(tmp / "out.txt"),
                   PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("::notice title=Calendar feed blocked (NETA 65 workshops)::", r.stdout)
        self.assertNotIn("Nothing is missing", r.stdout)           # it only shows what someone added by hand
        self.assertIn("only after someone on the committee adds it by hand", r.stdout)
        # the feed's notes: a notice + a "Check:" line each (never a warning)
        self.assertIn("::notice title=Check a content/events file (NETA 65 workshops)::content/events/2026-10-03-", r.stdout)
        feed_warnings = [ln for ln in r.stdout.splitlines() if ln.startswith("::warning") and "content_events" not in ln]
        self.assertEqual(feed_warnings, [])
        summary = (tmp / "summary.md").read_text(encoding="utf-8")
        self.assertIn("NETA 65 workshops: blocked by the site's bot protection · HTTP 403 · 11 event(s), 8 already on "
                      "the Events page (shown once) · last read 2026-09-20 (that copy is still used)", summary)
        self.assertIn("  - Check: content/events/2026-10-03-gv-writing-workshop-arlington.md: the “NETA 65 workshops” "
                      "calendar lists its event page", summary)
        # a slip in a content/events file is a Settings problem (the chair fixes the file)
        self.assertIn("::warning title=Settings problem (content_events)::content/events/2027-06-25-x.md", r.stdout)
        self.assertIn("- content/events/2027-06-25-x.md: location_es says", summary)
        health = json.loads((tmp / "out.txt").read_text(encoding="utf-8").split("health=", 1)[1])
        self.assertEqual(health["stale"], [])                    # → no "stopped updating" issue


if __name__ == "__main__":
    unittest.main()
