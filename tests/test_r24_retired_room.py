"""The committee's old Zoom room — meeting ID 949 476 7497, passcode neta65 — retired with the move to Google Meet,
and an event that is over in the calendar files.

  * PastEventsInTheCalendars — an event that is over (the calendar files, /events.ics and /es/events.ics, keep it
    90 days for their subscribers) still says where it was — its place, or "Online on Zoom" — but no longer how to
    join: no link, no meeting ID or code, none of its summary's sentences that give one ("Zoom ID" / "ID de Zoom"
    and a Zoom number right after the word too; "meeting ideas" is not a meeting ID); its "Add to calendar" links
    and its .ics download say the same. An event still to come keeps all of them. (eleventy/filters/committee.js
    shapeEvent: the workshop of October 3, 2026 kept the retired room in the feeds after it.)
  * TheRetiredRoom — no text of ours carries the retired room any more: the sources (content/, config/, src/,
    eleventy/, scripts/), the documentation (README.md, docs/, how-to/) and the other tests' sample data (tests/),
    and a real build of the pages made from the events (the calendar files, /events/, the share pages, the home
    page, /meetings/, the month pages and their calendar files, the search index, the booth's /about/booth.json, the
    presentations' JSON) from data in which the October 3 workshop still has it, as events.json had it — the event
    moved to ten days ago, so the calendar files still keep it on any day this runs. (It judges the committee's
    files too: scripts/ops/gate_tests.py CONTENT_TESTS.)
    One PICTURE shows it, which no text test reads: the workshop's flyer, on our Drive (flyers folder, file
    1n8FzYA1h3DeamjI9Pp5mxCyrZFz0Oweu: "Zoom Meeting ID … / Passcode …" in large type). The owner keeps that flyer
    on purpose (2026-11-11: "do not make arlington flyer private"): it stays on the Drive, on /portfolio/ and on its
    event (the file's flyer: line — "View flyer", its share page's picture, the calendar files' flyer).

    python -m unittest tests.test_r24_retired_room -v
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
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from nodejs import node_path, run_js  # noqa: E402

# The retired room, however it is written: "949 476 7497", "949-476-7497", "9494767497" (a Zoom link's), with
# no-break spaces (the decks keep an ID on one line), and its link's password token; the passcode after its label.
RETIRED_ID = re.compile(r"949[\s  .\-]*476[\s  .\-]*7497|ZnlwNkxaRysxd3BJNUNRcWZsV3RNdz09")
RETIRED_PASSCODE = re.compile(r"(?i)(?:pass\s*code|c[oó]digo(?: de acceso)?|contrase[ñn]a|pwd)\W{0,3}neta65\b")
TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".csv", ".json", ".js", ".mjs", ".cjs", ".njk", ".html", ".css", ".py",
                 ".txt", ".xml", ".svg", ".ics", ".webmanifest", ".sh", ".toml", ".ini"}


def plain(text: str) -> str:
    """A built file's text as a reader gets it: iCalendar lines unfolded (an ID may be cut by a fold, "94\\r\\n 9 476
    7497"), its TEXT escapes read, and HTML's / JSON's no-break spaces as spaces."""
    text = re.sub(r"\r?\n[ \t]", "", text)
    text = text.replace("\\,", ",").replace("\\;", ";").replace("\\n", "\n").replace("\\N", "\n")
    return re.sub(r"&nbsp;|&#160;|&#xa0;|\\u00a0", " ", text, flags=re.I)


def finds(text: str) -> list[str]:
    t = plain(text)
    return [m.group(0) for rx in (RETIRED_ID, RETIRED_PASSCODE) for m in rx.finditer(t)]


# --------------------------------------------------------------------------- an event that is over, in the calendars
NOW = "2026-11-11T18:00:00Z"          # Wed Nov 11, 2026, noon CST
PLACE = "Primary Purpose Group, 1802 West Division Street, Arlington, TX 76012"
ZOOM = "https://us02web.zoom.us/j/1234567890?pwd=AbCdEf123456"
MEET = "https://meet.google.com/abc-defg-hij"


def item(eid: str, title: str, start: str, end: str, summary: str, summary_es: str, **extra) -> dict:
    """An events.json item of a content/events file (docs/DATA_SCHEMA.md → events.json)."""
    return {"id": f"ev:manual:{eid}", "source": "committee", "kind": "event", "category": "manual", "status": "ok",
            "url": "", "title": title, "summary": summary, "lang": "en", "date": start, "tags": ["workshop"],
            "extra": {"start": start, "end": end, "all_day": False, "slug": eid, "past": over_on_now(end), **extra,
                      "own_i18n": {"summary": {"es": summary_es}}},
            "i18n": {"title": {"en": title, "es": title}, "summary": {"en": summary, "es": summary_es}}}


def over_on_now(end: str) -> bool:
    """events.json's extra.past, as the sync writes it on NOW's day."""
    return datetime.fromisoformat(end.replace("Z", "+00:00")) <= datetime.fromisoformat(NOW.replace("Z", "+00:00"))


HYBRID_EN = ("Learn to write your story. A hybrid workshop: come in person or join on Zoom (meeting ID 123 456 7890, "
             "passcode abc123). Bring a pen.")
HYBRID_ES = ("Aprende a escribir tu historia. Es un taller híbrido: ven en persona o conéctate por Zoom (ID de reunión "
             "123 456 7890, código de acceso abc123). Trae una pluma.")
ONLINE_EN = "Share your story with us. Join on Google Meet: meet.google.com/abc-defg-hij (meeting code abc-defg-hij)."
ONLINE_ES = "Comparte tu historia. Conéctate por Google Meet: meet.google.com/abc-defg-hij (código de reunión abc-defg-hij)."


def items() -> list[dict]:
    """The same two events — a hybrid one (a place and Zoom) and an online-only one (Google Meet) — once over and once
    still to come."""
    out = []
    for when, (start, end) in (("over", ("2026-10-03T19:00:00Z", "2026-10-03T22:00:00Z")),
                               ("ahead", ("2026-12-05T19:00:00Z", "2026-12-05T22:00:00Z"))):
        out.append(item(f"zz-hybrid-{when}", f"Hybrid Writing Workshop ({when})", start, end, HYBRID_EN, HYBRID_ES,
                        location=PLACE, online_url=ZOOM, platform="Zoom", meeting_id="123 456 7890"))
        out.append(item(f"zz-online-{when}", f"Online Writing Workshop ({when})", start, end, ONLINE_EN, ONLINE_ES,
                        online_url=MEET, platform="Google Meet", meeting_id="abc-defg-hij"))
    # … and one that is over whose summary gives the room in other words ("Zoom ID", "ID de Zoom", a Zoom number right
    # after the word) — and has "meeting ideas", which is not a meeting ID
    out.append(item("zz-words-over", "Writing Workshop in Other Words", "2026-10-03T19:00:00Z", "2026-10-03T22:00:00Z",
                    WORDS_EN, WORDS_ES, location=PLACE))
    return out


WORDS_EN = "Bring your meeting ideas. Zoom ID: 815 9593 1777. Or join on Zoom 815 9593 1777 from home. See you there."
WORDS_ES = ("Trae tus ideas para la reunión. ID de Zoom: 815 9593 1777. O conéctate por Zoom 815-9593-1777 desde casa. "
            "Te esperamos.")


# The calendar text of each event (committee.js normalizeEvents → calDescription / calLocation, the "Add to calendar"
# links and the .ics download), and /events.ics as src/pages/events-ics.11ty.js renders it — on NOW's day.
CALENDARS_JS = r"""
const conf = await imp("eleventy.config.js");
const feed = await imp("src/pages/events-ics.11ty.js");
const res = {};
for (const lang of ["en", "es"]) {
  const evs = filters.cmEvents(input.items, input.site, lang).filter((e) => !e.committee);
  res[lang] = {
    events: Object.fromEntries(evs.map((e) => [e.anchor, { past: e.past, description: e.calDescription,
      location: e.calLocation, gcal: e.gcal, outlook: e.outlook, ics: e.icsData }])),
    feed: feed.render.call({ t: (k, l, v) => conf.translateKey(k, l, v) },
                           { lang, site: input.site, db: { events: { items: input.items } } }),
  };
}
out(res);
"""


class PastEventsInTheCalendars(unittest.TestCase):
    """An event that is over keeps its place (or "Online on Zoom") in the calendars, never how to join it."""

    res: dict | None = None

    def calendars(self) -> dict:
        if PastEventsInTheCalendars.res is None:
            site = {"url": "https://example.org/gv", "meeting": {"weekday": "wednesday", "week_of_month": 3,
                                                                 "start": "19:00", "end": "20:00"}, "links": {}}
            PastEventsInTheCalendars.res = run_js(self, CALENDARS_JS, data={"items": items(), "site": site}, now=NOW)
        return PastEventsInTheCalendars.res

    def test_an_event_that_is_over_says_where_it_was_but_not_how_to_join(self):
        res = self.calendars()
        for lang, online_on, details in (("en", "Online on {}", "Details: "), ("es", "En línea por {}", "Detalles: ")):
            evs = res[lang]["events"]
            hybrid, online = evs["zz-hybrid-over"], evs["zz-online-over"]
            with self.subTest(lang=lang):
                self.assertTrue(hybrid["past"] and online["past"])
                # the hybrid one: its place, "Online on Zoom" (no link), the summary's other sentences
                self.assertEqual(hybrid["location"], PLACE)
                lines = hybrid["description"].splitlines()
                self.assertIn(online_on.format("Zoom"), lines)
                self.assertEqual(lines[0], {"en": "Learn to write your story. Bring a pen.",
                                            "es": "Aprende a escribir tu historia. Trae una pluma."}[lang])
                self.assertEqual([ln for ln in lines if ln.startswith(details)],
                                 [details + "https://example.org/gv" + ("/es" if lang == "es" else "")
                                  + "/events/#zz-hybrid-over"])
                # the online-only one: "Online on Google Meet" is where it was
                self.assertEqual(online["location"], online_on.format("Google Meet"))
                self.assertIn(online_on.format("Google Meet"), online["description"].splitlines())
                for ev in (hybrid, online):
                    # its text, its "Add to calendar" links (read back from their query) and its .ics download
                    text = " | ".join([ev["description"], ev["location"], unquote(ev["gcal"]), unquote(ev["outlook"]),
                                       json.dumps(ev["ics"], ensure_ascii=False)])
                    for bit in ("zoom.us", "1234567890", "123 456 7890", "pwd", "abc123", "meet.google.com",
                                "abc-defg-hij", "Meeting ID", "Meeting code", "ID de reuni", "digo de la reuni",
                                "digo de reuni", "digo de acceso", "passcode"):
                        self.assertNotIn(bit, text, f"{lang}: an event that is over: {bit!r}")

    def test_the_room_in_other_words(self):
        res = self.calendars()
        for lang, kept in (("en", "Bring your meeting ideas. See you there."),
                           ("es", "Trae tus ideas para la reunión. Te esperamos.")):
            ev = res[lang]["events"]["zz-words-over"]
            with self.subTest(lang=lang):
                self.assertTrue(ev["past"])
                self.assertEqual(ev["description"].splitlines()[0], kept)
                self.assertNotIn("815", ev["description"] + json.dumps(ev["ics"], ensure_ascii=False))

    def test_an_event_still_to_come_keeps_how_to_join(self):
        res = self.calendars()
        for lang, online_on, idk, codek in (("en", "Online on {}", "Meeting ID", "Meeting code"),
                                            ("es", "En línea por {}", "ID de reunión", "Código de la reunión")):
            evs = res[lang]["events"]
            hybrid, online = evs["zz-hybrid-ahead"], evs["zz-online-ahead"]
            with self.subTest(lang=lang):
                self.assertFalse(hybrid["past"] or online["past"])
                self.assertEqual(hybrid["location"], PLACE)
                self.assertIn(f"{online_on.format('Zoom')}: {ZOOM}", hybrid["description"].splitlines())
                self.assertIn(f"{idk}: 123 456 7890", hybrid["description"].splitlines())
                self.assertIn({"en": HYBRID_EN, "es": HYBRID_ES}[lang], hybrid["description"])
                self.assertEqual(online["location"], MEET)
                self.assertIn(f"{codek}: abc-defg-hij", online["description"].splitlines())
                self.assertIn(ZOOM, hybrid["ics"]["description"])

    def test_the_calendar_files(self):
        from icalendar import Calendar
        res = self.calendars()
        for lang in ("en", "es"):
            cal = Calendar.from_ical(res[lang]["feed"])
            entries = {str(e["UID"]).split("@")[0].removesuffix("-es"): e for e in cal.walk("VEVENT")}
            with self.subTest(lang=lang):
                for uid in ("ev-manual-zz-hybrid-over", "ev-manual-zz-online-over"):     # kept 90 days …
                    self.assertIn(uid, entries)
                    text = str(entries[uid].get("DESCRIPTION", "")) + str(entries[uid].get("LOCATION", ""))
                    for bit in ("zoom.us", "123 456 7890", "abc123", "meet.google.com", "abc-defg-hij"):
                        self.assertNotIn(bit, text, f"{uid}: {bit!r}")                     # … without how to join
                self.assertEqual(str(entries["ev-manual-zz-hybrid-over"]["LOCATION"]), PLACE)
                self.assertIn(ZOOM, str(entries["ev-manual-zz-hybrid-ahead"]["DESCRIPTION"]))
                self.assertIn("abc-defg-hij", str(entries["ev-manual-zz-online-ahead"]["DESCRIPTION"]))


# --------------------------------------------------------------------------- the retired room, nowhere of ours
# The workshop of October 3, 2026 as events.json had it until its file lost the room (its words, its link, its ID).
def retired_room_event(now: datetime) -> dict:
    start = (now - timedelta(days=10)).replace(hour=19, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=3)
    z = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")             # noqa: E731
    en = ("Learn how to write your story for Grapevine and La Viña, and hear from members who have been published. "
          "Hosted by the Primary Purpose Group in Arlington. A hybrid workshop: come in person or join on Zoom "
          "(meeting ID 949 476 7497, passcode neta65).")
    es = ("Aprende a escribir tu historia para Grapevine y La Viña, y escucha a miembros que ya han sido publicados. "
          "En el Grupo Primary Purpose de Arlington. Es un taller híbrido: ven en persona o conéctate por Zoom (ID de "
          "reunión 949 476 7497, código de acceso neta65).")
    title, title_es = "Grapevine Writing Workshop — Arlington", "Taller de Escritura de Grapevine (en inglés) — Arlington"
    return {
        "id": "ev:manual:2026-10-03-gv-writing-workshop-arlington", "source": "committee", "kind": "event",
        "url": "https://neta65.org/event/grapevine-writing-workshop-6/", "title": title, "summary": en, "lang": "en",
        "date": z(start), "first_seen": "2026-09-24T11:10:08Z", "image": None, "tags": ["workshop", "grapevine"],
        "category": "manual", "status": "ok",
        "extra": {"start": z(start), "end": z(end), "all_day": False,
                  "location": "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012",
                  "online_url": "https://us02web.zoom.us/j/9494767497?pwd=ZnlwNkxaRysxd3BJNUNRcWZsV3RNdz09",
                  "flyer_url": "https://drive.google.com/file/d/1n8FzYA1h3DeamjI9Pp5mxCyrZFz0Oweu/view",
                  "flyer_thumb": None, "city": "Arlington", "state": "TX", "body_md": en,
                  "slug": "2026-10-03-gv-writing-workshop-arlington",
                  "file": "content/events/2026-10-03-gv-writing-workshop-arlington.md", "confirmed": True,
                  "meeting_id": "949 476 7497", "platform": "Zoom", "past": True,
                  "own_i18n": {"title": {"es": title_es}, "summary": {"es": es}, "body_md": {"es": es}}},
        "i18n": {"title": {"en": title, "es": title_es}, "summary": {"en": en, "es": es}},
    }


# the pages made from the events (eleventy.config.js ONLY: the src/pages files whose names start so)
EVENT_PAGES = ("events", "event-share", "index", "meetings", "monthly", "search-index", "booth-json", "presentations-json",
               "deadlines-ics", "share", "feed")


class TheRetiredRoom(unittest.TestCase):
    """949 476 7497 and its passcode are gone from every text of ours (the owner: that room is retired since the move
    to Google Meet). The one picture that shows them, the Arlington flyer, the owner keeps on purpose — on the Drive,
    /portfolio/ and its event (the module's note)."""

    def test_no_source_carries_it(self):
        # the sources, the documentation, and the other tests' sample data (a made-up room there: 123 456 7890)
        this = Path(__file__).resolve()
        files = [ROOT / "README.md"] + [p for top in ("content", "config", "src", "eleventy", "scripts", "docs", "how-to",
                                                      "tests")
                                        if (ROOT / top).is_dir()
                                        for p in sorted((ROOT / top).rglob("*")) if "__pycache__" not in p.parts]
        found = []
        for p in files:
            if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES and p.resolve() != this:
                for hit in finds(p.read_text(encoding="utf-8", errors="replace")):
                    found.append(f"{p.relative_to(ROOT).as_posix()}: {hit}")
        self.assertEqual(found, [], "the committee's retired Zoom room (949 476 7497, passcode neta65)")

    def test_the_arlington_workshop_names_its_place_only(self):
        text = (ROOT / "content" / "events" / "2026-10-03-gv-writing-workshop-arlington.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^(?:online_url|meeting_id|passcode):")
        self.assertRegex(text, r'(?m)^location: "Primary Purpose Group – Arlington, 1802 West Division Street')

    def test_no_page_made_from_the_events_carries_it(self):
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            self.skipTest("Node.js or the site's npm packages are missing (npm ci)")
        tmp = Path(tempfile.mkdtemp(prefix="gv-retired-room-"))
        try:
            data = tmp / "data"
            data.mkdir()
            ev = retired_room_event(datetime.now(timezone.utc))
            (data / "events.json").write_text(json.dumps({"updated": ev["date"], "items": [ev]}, ensure_ascii=False),
                                              encoding="utf-8")
            env = {**os.environ, "PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1", "NODE_NO_WARNINGS": "1",
                   "ONLY": ",".join(EVENT_PAGES), "SITE_DATA": str(data)}
            env.pop("MONTHLY_NOW", None)
            out = tmp / "site"
            r = subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                                "--output", str(out)], cwd=ROOT, env=env, capture_output=True, text=True,
                               encoding="utf-8", timeout=900)
            self.assertEqual(r.returncode, 0, r.stderr[-3000:])
            built = [p for p in out.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES]
            names = {p.relative_to(out).as_posix() for p in built}
            for must in ("events.ics", "es/events.ics", "events/index.html", "es/events/index.html", "about/booth.json"):
                self.assertIn(must, names)
            found = [f"{p.relative_to(out).as_posix()}: {hit}" for p in built
                     for hit in finds(p.read_text(encoding="utf-8", errors="replace"))]
            self.assertEqual(found, [], "the retired Zoom room in a built file")
            # … and the workshop is in the calendar files all the same (over ten days ago: kept 90 days), at its place
            for name, online in (("events.ics", "Online on Zoom"), ("es/events.ics", "En línea por Zoom")):
                cal = plain((out / name).read_text(encoding="utf-8"))
                vevent = re.search(r"BEGIN:VEVENT\r?\nUID:ev-manual-2026-10-03-gv-writing-workshop-arlington[\s\S]*?"
                                   r"END:VEVENT", cal)
                self.assertIsNotNone(vevent, name)
                self.assertIn("LOCATION:Primary Purpose Group – Arlington, 1802 West Division Street", vevent.group(0))
                self.assertIn(online, vevent.group(0))
                self.assertNotIn("zoom.us", vevent.group(0))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
