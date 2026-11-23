"""Round 37 · a cancelled event: content/events `cancelled: true` (the La Viña writing workshop in Garland, Nov 28,
2026, was the first). The file stays; the event leaves every list of the site, its address keeps a "Cancelled" notice
until its day is over, and the calendar feeds mark the entry their subscribers have as cancelled.

  * TheLines — what the file may say (scripts/sync/announcements.py parse_event): `cancelled:` / `canceled:` /
    `cancelado:` / `cancelada:` with true, yes or sí, or `status: cancelled` (canceled, cancelado, cancelada) →
    extra.cancelled; `cancelled_note:` / `cancelled_note_es:` → extra.cancelled_note; and `type:` (`tipo:`, `kind:`) —
    one of EVENT_TYPES → extra.type, any other value left out and listed on /status/ (collect), the event shown.
  * TheSync — build_data: a cancelled event stays among the others through build_events, so the copy of it a .ics
    feed or La Viña's calendar lists is still recognised and never shown as a new event; split_cancelled writes it to
    events.json `cancelled`; order_events keeps one that is over 90 days, outside the 12 places of past events; What's
    New leaves out the event and the Drive flyer only it uses; carry_unreadable never brings a cancelled event back
    among the events (and keeps the last build's cancelled ones cancelled); a cancelled assembly is no assembly to
    come for the reminder.
  * TheBuildsCut — src/_data/db.js (eleventy/cancelled-events.js): db.events.cancelled is always a list; an item still
    among the events that is marked cancelled, or whose own file says so now (the sync has not run), moves there; the
    Drive flyers only cancelled events use leave drive.items and whatsnew.items, and so does the event itself; a file
    that changes while a preview keeps running is read again.
  * Calendars — committee.js buildIcs (with alarms, as the month's file) and the /events.ics page: the same UID,
    STATUS:CANCELLED, "Cancelled:" before the title, free time, no flyer attached, never a reminder; the description
    says it is cancelled (the file's own note when it has one), then the summary without how to join, then its notice
    page (once its day is over: /events/); the month's file adds the month's cancelled events. eventLd keeps startDate
    and location with EventCancelled, and no picture; cancelledPageMeta's words in both languages (one over several
    days: "from <first day> to <last day>" / "del … al …", in full words); a note written in one language only, and
    its language (ev.cancelledNoteLang).
  * TheNoticePage — a build (ONLY=event-share,events-ics,sitemap; SITE_DATA and CONTENT_EVENTS: never the day's data):
    the notice in both languages at the address the event's page had, indexable and in the sitemap, its Event
    EventCancelled first in <body> (none for an online-only one), no flyer, no "Add to calendar", no join link, Share
    kept, the organizers' note (lang="es" on the English page when written in Spanish only), the next events of the
    same kind (outside the page's sitemap date: data-lastmod="skip"); none for one whose day is over (no page, no
    <loc>), one at its address even when a listed event has that anchor too (round 37: one rule); an event only its
    file calls cancelled gets one too; the [seo]
    check finds nothing.

Runs Eleventy with Node.js (tests/nodejs.py) for the JavaScript parts; those are skipped without Node.js / the npm
packages.

    python -m unittest tests.test_r37_cancelled -v
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402

CHI = ZoneInfo("America/Chicago")
TODAY = datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc)          # Sun Nov 22, 2026, 9 AM CST
FEED_URL = "https://neta65.org/events/category/workshop/list/?ical=1"
CFG = {
    "site": {"timezone": "America/Chicago"},
    "meeting": {"weekday": "wednesday", "week_of_month": 3, "start": "19:00", "end": "20:00", "skip_dates": []},
    "sources": {"crawler": {"user_agent": "NETA65-GrapevineCommitteeBot/2.0 (+https://github.com/NETA65/aagrapevine)"},
                "ics_feeds": [{"url": FEED_URL, "label": "NETA 65 workshops", "category": "neta65"}]},
}
DRIVE_X = "1AbCdEfGhIjKlMnOpQrStUvWx"       # the cancelled workshop's flyer
DRIVE_Y = "1ZyXwVuTsRqPoNmLkJiHgFeDc"       # another workshop's flyer
DRIVE_Z = "1QqQqQqQqQqQqQqQqQqQqQqQq"       # a flyer of no event
PAGE = "https://neta65.org/event/lv-writing-workshop-garland/"
GARLAND = ('title: "La Viña Writing Workshop (in Spanish) — Garland"\n'
           'title_es: "Taller de Escritura de La Viña — Garland"\n'
           "start: 2026-11-28T19:00:00-06:00\nend: 2026-11-28T21:00:00-06:00\n"
           'location: "Grupo Volver a Vivir, 2913 S. Fifth St., Garland, TX 75041"\n'
           f'url: "{PAGE}"\nflyer: "https://drive.google.com/file/d/{DRIVE_X}/view"\n'
           "tags: [workshop, la-vina]\ncancelled: true\nlang: en\n")
FIXTURE = (ROOT / "tests" / "fixtures" / "neta65-workshops.ics").read_text(encoding="utf-8").replace("\n", "\r\n")
VTIMEZONE = FIXTURE[FIXTURE.index("BEGIN:VTIMEZONE"):FIXTURE.index("END:VTIMEZONE") + len("END:VTIMEZONE")]


def ctx_with(now: datetime = TODAY) -> B.Ctx:
    ctx = B.Ctx(offline=True)
    ctx.cfg = json.loads(json.dumps(CFG))
    ctx.now = now
    ctx.now_ts = now.timestamp()
    ctx.today_local = now.astimezone(ctx.tz).date()
    return ctx


def feed(*vevents: str) -> str:
    """A small calendar in The Events Calendar's shape (neta65.org's: VTIMEZONE + TZID=America/Chicago)."""
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//NETA65 - ECPv6.15.1//NONSGML v1.0//EN\r\n" + VTIMEZONE + "\r\n"
            + "".join(vevents) + "END:VCALENDAR\r\n")


def vevent(uid: str, summary: str, start: str, end: str, url: str, location: str) -> str:
    return "\r\n".join(["BEGIN:VEVENT", f"DTSTART;TZID=America/Chicago:{start}", f"DTEND;TZID=America/Chicago:{end}",
                        f"UID:{uid}@neta65.org", f"SUMMARY:{summary}", f"URL:{url}",
                        "LOCATION:" + location.replace(",", "\\,"), "END:VEVENT"]) + "\r\n"


def iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(eid: str, start: datetime, hours: float = 2, **extra) -> dict:
    """A site event as events.json holds it (build_data)."""
    return {"id": eid, "source": "committee", "kind": "event", "category": "manual", "url": "/events/#x",
            "title": eid, "summary": "", "lang": "en", "date": iso(start), "first_seen": iso(TODAY - timedelta(days=2)),
            "tags": [], "status": "ok",
            "extra": {"start": iso(start), "end": iso(start + timedelta(hours=hours)), "all_day": False, **extra}}


class NoTranslator:
    def translate(self, texts, src, tgt):
        return [(None, False) for _ in texts]


# =========================================================================== the file's lines
class TheLines(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="gv-r37-lines-"))
        self.addCleanup(shutil.rmtree, self.folder, True)

    def write(self, lines: str, name: str = "2099-11-28-x.md") -> Path:
        p = self.folder / name
        p.write_text('---\ntitle: "Writing Workshop"\nstart: 2099-11-28T19:00:00-06:00\nend: 2099-11-28T21:00:00-06:00\n'
                     f'location: "Grupo Uno, 100 Main St, Garland, TX 75041"\n{lines}---\nA workshop.\n', encoding="utf-8")
        return p

    def parse(self, lines: str) -> dict:
        return A.parse_event(self.write(lines), CHI)

    def test_the_words_that_cancel_it(self):
        for lines in ("cancelled: true\n", "canceled: yes\n", "cancelado: sí\n", "cancelada: true\n", "cancelled: Yes\n",
                      'cancelled: "true"\n', "cancelled: 1\n", "cancelado: si\n", "status: cancelled\n",
                      "status: Cancelado\n", 'status: "canceled"\n', "status: cancelada\n"):
            with self.subTest(lines=lines):
                self.assertIs(self.parse(lines)["extra"].get("cancelled"), True)
        for lines in ("", "cancelled: false\n", "cancelled: no\n", "cancelled:\n", "status: confirmed\n",
                      "tentative: true\n", "notes:\n  cancelled: true\n"):
            with self.subTest(lines=lines):
                self.assertNotIn("cancelled", self.parse(lines)["extra"])
        # the event is still read as before: its id, title, language and dates
        it = self.parse("cancelled: true\nlang: en\n")
        self.assertEqual((it["id"], it["title"], it["lang"]), ("ev:manual:2099-11-28-x", "Writing Workshop", "en"))
        self.assertEqual(it["extra"]["start"], "2099-11-29T01:00:00Z")

    def test_its_note(self):
        ex = self.parse('cancelled: true\ncancelled_note: "Moved to January 9."\ncancelled_note_es: "Pasó al 9 de enero."\n'
                        "lang: en\n")["extra"]
        self.assertEqual(ex["cancelled_note"], {"en": "Moved to January 9.", "es": "Pasó al 9 de enero."})
        ex = self.parse('cancelado: sí\ncanceled_note: "Se canceló por el clima."\nlang: es\n')["extra"]
        self.assertEqual(ex["cancelled_note"], {"es": "Se canceló por el clima."})
        self.assertNotIn("cancelled_note", self.parse("cancelled: true\n")["extra"])
        self.assertNotIn("cancelled_note", self.parse('cancelled_note: "Only a note."\n')["extra"])   # not cancelled

    def test_its_type(self):
        self.assertEqual(self.parse("type: writing-workshop\n")["extra"]["type"], "writing-workshop")
        self.assertEqual(self.parse('tipo: "Town Hall"\n')["extra"]["type"], "town-hall")
        self.assertEqual(self.parse("kind: ACM\n")["extra"]["type"], "acm")
        self.assertNotIn("type", self.parse("")["extra"])
        self.assertEqual(len(set(A.EVENT_TYPES)), len(A.EVENT_TYPES))
        self.assertTrue(all(re.fullmatch(r"[a-z]+(?:-[a-z]+)*", k) for k in A.EVENT_TYPES))
        # a value the site does not know: left out, listed (→ /status/), and the event still shows
        self.write("type: taller\ncancelled: true\n")
        items, errors, failed = A.collect(self.folder, lambda p: A.parse_event(p, CHI), "events")
        self.assertEqual((len(items), failed), (1, set()))
        self.assertNotIn("type", items[0]["extra"])
        self.assertNotIn("type_problem", items[0]["extra"])            # (reported by collect, not kept in the data)
        self.assertIs(items[0]["extra"]["cancelled"], True)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith(f"{self.folder.name}/2099-11-28-x.md: type: “taller” is not a kind the "
                                             "site knows, left out — write one of writing-workshop, "), errors[0])
        self.assertTrue(errors[0].endswith(", other, or delete the line"), "the whole list, never cut")


# =========================================================================== the sync
class TheSync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-r37-sync-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for p in (mock.patch.object(B, "STATE_DIR", self.tmp),
                  mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator())):
            p.start()
            self.addCleanup(p.stop)

    def manual(self, files: dict[str, str]) -> list[dict]:
        folder = Path(tempfile.mkdtemp(dir=self.tmp, prefix="events-"))
        for name, header in files.items():
            (folder / name).write_text(f"---\n{header}---\nA hand-written description.\n", encoding="utf-8")
        return [A.parse_event(p, CHI) for p in A.content_files(folder)]

    def build(self, files: dict[str, str]) -> list[dict]:
        """build_events over these content/events files, neta65.org's feed listing the Garland workshop (its page,
        the same day and time) and La Viña's calendar listing it too (its title, the same day and time)."""
        ctx = ctx_with()
        manual = self.manual(files)
        listed = feed(vevent("40001", "LV Writing Workshop — Garland", "20261128T190000", "20261128T210000", PAGE,
                             "Grupo Volver a Vivir, 2913 S. Fifth St., Garland, TX, 75041"))
        feed_items = B._parse_ics(ctx, {"_ics": listed, "_spec": B.feed_specs(ctx)[0]})
        ctx.feeds = [{"key": "neta-65-workshops", "label": "NETA 65 workshops"}]
        lv = {"id": "ev:lvcal:abc123abc123", "source": "calendar", "kind": "event", "category": "lv-calendar",
              "url": "https://www.aalavina.org/get-involved/events/2026-11-28/taller-de-escritura-garland",
              "title": "Taller de Escritura de La Viña — Garland", "summary": "", "lang": "es",
              "date": "2026-11-29T01:00:00Z", "status": "ok", "tags": [],
              "extra": {"start": "2026-11-29T01:00:00Z", "end": "2026-11-29T03:00:00Z", "all_day": False,
                        "location": "Grupo Volver a Vivir, 2913 S. Fifth St., Garland, TX 75041", "city": "Garland",
                        "state": "TX"}}
        with mock.patch.object(B, "ics_events", lambda c: feed_items), \
                mock.patch.object(B.Ctx, "items", lambda self, name: {"manual_events": manual, "events_external": [lv]}.get(name, [])):
            return B.build_events(ctx)

    def garland_day(self, evs: list[dict]) -> list[dict]:
        ctx = ctx_with()
        return [e for e in evs if B.local_day(ctx, e["extra"]["start"]) == "2026-11-28" and e.get("category") != "committee"]

    def test_its_copies_elsewhere_are_still_recognised(self):
        evs = self.build({"2026-11-28-lv-writing-workshop-garland.md": GARLAND})
        same = self.garland_day(evs)
        self.assertEqual([e["id"] for e in same], ["ev:manual:2026-11-28-lv-writing-workshop-garland"])
        ex = same[0]["extra"]
        self.assertIs(ex["cancelled"], True)
        self.assertEqual((ex["also_in_feed"], ex["also_on_calendar"]), ("neta-65-workshops", "lv-calendar"))
        items, cancelled = B.split_cancelled(evs)
        self.assertEqual([e["id"] for e in cancelled], ["ev:manual:2026-11-28-lv-writing-workshop-garland"])
        self.assertEqual(self.garland_day(items), [], "neither the feed's copy nor La Viña's listing comes back")
        self.assertEqual(len(items) + 1, len(evs))
        # (had the file been deleted instead, both copies would be shown as events of their own)
        self.assertEqual(sorted(e["category"] for e in self.garland_day(self.build({}))), ["lv-calendar", "neta65"])

    def test_one_that_is_over_is_kept_90_days_outside_the_past_places(self):
        ctx = ctx_with()
        past = [event(f"ev:manual:p{n:02d}", TODAY - timedelta(days=2 + n)) for n in range(14)]
        recent = event("ev:manual:called-off", TODAY - timedelta(days=10), cancelled=True)
        old = event("ev:manual:long-ago", TODAY - timedelta(days=95), cancelled=True)
        soon = event("ev:manual:soon", TODAY + timedelta(days=6), cancelled=True)
        out = B.order_events(ctx, [*past, recent, old, soon])
        ids = [e["id"] for e in out]
        self.assertNotIn("ev:manual:long-ago", ids)
        self.assertEqual(ids[0], "ev:manual:soon")
        self.assertFalse(out[0]["extra"]["past"])
        items, cancelled = B.split_cancelled(out)
        self.assertEqual([e["id"] for e in cancelled], ["ev:manual:soon", "ev:manual:called-off"])
        self.assertTrue(cancelled[1]["extra"]["past"])
        self.assertEqual(len(items), B.PAST_EVENTS_KEEP, "the cancelled one took none of the past events' places")
        self.assertEqual(B.CANCELLED_KEEP_PAST_DAYS, 90)

    def test_whats_new_leaves_it_and_its_flyer_out(self):
        ctx = ctx_with()
        ctx.births = {}
        off = event("ev:manual:off", TODAY + timedelta(days=6), cancelled=True,
                    flyer_url=f"https://drive.google.com/file/d/{DRIVE_X}/view", past=False)
        on = event("ev:manual:on", TODAY + timedelta(days=20), flyer_url=f"https://drive.google.com/file/d/{DRIVE_Y}/view",
                   past=False)
        flyers = [{"id": f"drive:{fid}", "source": "drive", "kind": "photo", "category": "flyers", "title": fid,
                   "date": iso(TODAY - timedelta(days=1)), "first_seen": iso(TODAY - timedelta(days=1)), "status": "ok",
                   "extra": {"file_id": fid}} for fid in (DRIVE_X, DRIVE_Y, DRIVE_Z)]
        self.assertEqual(B.cancelled_flyer_ids([off, on]), {DRIVE_X})
        plan = B.plan_whatsnew(ctx, {"events": [off, on], "drive": flyers})
        self.assertEqual({it["id"] for _wn, it in plan}, {"ev:manual:on", f"drive:{DRIVE_Y}", f"drive:{DRIVE_Z}"})
        # a flyer a cancelled event shares with one that takes place stays (and Google's picture of it counts too)
        both = {**event("ev:manual:both", TODAY + timedelta(days=30)),
                "image": f"https://lh3.googleusercontent.com/d/{DRIVE_X}=w600"}
        self.assertEqual(B.cancelled_flyer_ids([off, on, both]), set())

    def test_the_last_builds_events_never_bring_it_back(self):
        """A raw file that cannot be read (carry_unreadable): its events of the last build come back — never one this
        build has cancelled, and the last build's cancelled ones stay cancelled."""
        ctx = ctx_with()
        ctx.unreadable = {"manual_events"}
        live = event("ev:manual:x", TODAY + timedelta(days=5))
        was_live = event("ev:manual:z", TODAY + timedelta(days=6))
        now_off = event("ev:manual:z", TODAY + timedelta(days=6), cancelled=True)
        was_off = event("ev:manual:y", TODAY + timedelta(days=7), cancelled=True)
        flyer = {**event("ev:flyer:f", TODAY + timedelta(days=8)), "category": "flyer", "source": "drive"}
        prev = {"updated": "x", "items": [live, was_live], "cancelled": [was_off]}
        doc = {"updated": "y", "fixture": False, "items": [flyer], "cancelled": [now_off]}
        with self.assertLogs(B.log, "ERROR"):
            got = B.carry_unreadable(ctx, "events", doc, prev)
        self.assertEqual([e["id"] for e in got["items"]], ["ev:manual:x", "ev:flyer:f"])
        self.assertEqual([e["id"] for e in got["cancelled"]], ["ev:manual:z", "ev:manual:y"])
        self.assertEqual(got["updated"], "y")
        # nothing to bring back: the file as it was
        ctx.unreadable = set()
        self.assertIs(B.carry_unreadable(ctx, "events", doc, prev), doc)

    def test_a_cancelled_assembly_is_no_assembly_to_come(self):
        root = Path(tempfile.mkdtemp(dir=self.tmp, prefix="root-"))
        (root / "content" / "events").mkdir(parents=True)
        (root / "content/events/2027-03-19-neta65-spring-assembly.md").write_text(
            '---\ntitle: "NETA 65 Spring Assembly 2027"\nstart: 2027-03-19\nend: 2027-03-21\n---\n', encoding="utf-8")
        (root / "content/events/2027-09-17-neta65-fall-assembly.md").write_text(
            '---\ntitle: "NETA 65 Fall Assembly 2027"\nstart: 2027-09-17\nstatus: cancelled\n---\n', encoding="utf-8")
        got = B._assembly_reminders(ctx_with(), root, date(2027, 3, 1))
        self.assertEqual([r["due"] for r in got], ["2027-03-19"], "the fall one is cancelled: the spring one is the last")


# =========================================================================== the build's own cut
DB_JS = r"""
const db = (await imp("src/_data/db.js")).default();
const K = await imp("eleventy/cancelled-events.js");
const bare = { items: [{ id: "a", kind: "event", extra: {} }] };
K.splitCancelled(bare, "nowhere");
out({ items: db.events.items.map((i) => i.id), cancelled: db.events.cancelled.map((i) => [i.id, i.extra.cancelled]),
      drive: db.drive.items.map((i) => i.id), whatsnew: db.whatsnew.items.map((i) => i.id), bare });
"""


# a preview that keeps running (`npm start`): the same process asks again after the file changed
FILE_JS = r"""
const K = await imp("eleventy/cancelled-events.js");
const file = path.join(input.dir, "x.md"), it = { category: "manual", extra: { file: "content/events/x.md" } };
const says = [];
for (const head of ["cancelled: true", "cancelled: false   # it takes place after all", null, "status: canceled"]) {
  if (head === null) fs.rmSync(file);
  else fs.writeFileSync(file, `---\ntitle: "x"\n${head}\n---\n`);
  says.push(K.cancelledInFile(it, input.dir), K.cancelledInFile(it, input.dir));
}
out(says);
"""


class TheBuildsCut(unittest.TestCase):
    def test_db_events_cancelled(self):
        tmp = Path(tempfile.mkdtemp(prefix="gv-r37-db-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        files = tmp / "events"
        files.mkdir()
        start = datetime(2099, 11, 28, 19, tzinfo=CHI)

        def manual(slug: str, header: str | None, **extra) -> dict:
            it = event(f"ev:manual:{slug}", start, slug=slug, file=f"content/events/{slug}.md", **extra)
            if header is not None:
                (files / f"{slug}.md").write_text(f'---\ntitle: "{slug}"\n{header}---\nText.\n', encoding="utf-8")
            return it

        flyer = lambda fid: f"https://drive.google.com/file/d/{fid}/view"   # noqa: E731
        items = [
            manual("a-marked", None, cancelled=True, flyer_url=flyer(DRIVE_X)),             # marked, not split yet
            manual("b-file-says", "cancelled: yes   # called off by the district\n", flyer_url=flyer(DRIVE_Z)),
            manual("c-status", "status: Cancelado\n"),
            manual("d-not", "cancelled: false\n"),
            manual("e-nested", "notes:\n  cancelled: true\n"),
            {**manual("f-not-manual", "cancelled: true\n"), "category": "flyer"},
            manual("g-live", "title_es: x\n", flyer_url=flyer(DRIVE_Y)),
            manual("i-no-file", None),
            manual("j-both", None),                     # in both lists (the sync never writes one so): cancelled
        ]
        cancelled = [manual("h-split", None, cancelled=True, flyer_url=flyer(DRIVE_Y)), manual("j-both", None, cancelled=True)]
        drive = [{"id": f"drive:{fid}", "kind": "photo", "category": "flyers", "url": flyer(fid), "extra": {"file_id": fid}}
                 for fid in (DRIVE_X, DRIVE_Y, DRIVE_Z, "1NoEventsFlyer000000000")]
        whatsnew = [{"id": f"drive:{DRIVE_X}", "kind": "photo", "url": flyer(DRIVE_X), "extra": {"file_id": DRIVE_X}},
                    {"id": f"drive:{DRIVE_Y}", "kind": "photo", "url": flyer(DRIVE_Y), "extra": {"file_id": DRIVE_Y}},
                    {**items[0], "url": "/events/#a-marked"}, {**items[6], "url": "/events/#g-live"}]
        for name, doc in (("events", {"items": items, "cancelled": cancelled}), ("drive", {"items": drive}),
                          ("whatsnew", {"items": whatsnew})):
            (tmp / f"{name}.json").write_text(json.dumps(doc), encoding="utf-8")
        r = run_js(self, DB_JS, env={"SITE_DATA": str(tmp), "CONTENT_EVENTS": str(files)})
        self.assertEqual(r["items"], ["ev:manual:d-not", "ev:manual:e-nested", "ev:manual:f-not-manual",
                                      "ev:manual:g-live", "ev:manual:i-no-file"])
        self.assertEqual(r["cancelled"], [["ev:manual:h-split", True], ["ev:manual:j-both", True], ["ev:manual:a-marked", True],
                                          ["ev:manual:b-file-says", True], ["ev:manual:c-status", True]])
        # the flyers only cancelled events use (X, Z) are out; Y — also the live event's — stays
        self.assertEqual(r["drive"], [f"drive:{DRIVE_Y}", "drive:1NoEventsFlyer000000000"])
        self.assertEqual(r["whatsnew"], [f"drive:{DRIVE_Y}", "ev:manual:g-live"])
        # always a list
        self.assertEqual(r["bare"], {"items": [{"id": "a", "kind": "event", "extra": {}}], "cancelled": []})

    def test_a_file_changed_while_the_build_runs_on(self):
        """cancelledInFile reads a file again once it changed (a `cancelled:` line added, taken out, the file gone):
        a preview that keeps running never keeps the first answer."""
        tmp = Path(tempfile.mkdtemp(prefix="gv-r37-file-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        self.assertEqual(run_js(self, FILE_JS, data={"dir": str(tmp)}),
                         [True, True, False, False, False, False, True, True])


# =========================================================================== the calendars and the Event
CAL_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const M = await imp("eleventy/filters/monthly.js");
const ICS = await imp("src/pages/events-ics.11ty.js");
const site = input.site;
const res = {};
for (const lang of ["en", "es"]) {
  const evs = C.normalizeEvents([...input.items, ...input.cancelled], site, lang).filter((e) => !e.committee);
  const m = { key: "2099-11", label: "November 2099", dates: [], deadlines: [], lvDeadlines: [], isCurrent: false };
  const db = { events: { items: input.items, cancelled: input.cancelled }, weekly_open: { items: [] } };
  const page = ICS.render.call({ t: (k, l, v) => filters.t(k, l, v) }, { lang, site, db });
  const g = evs.find((e) => e.id === "ev:manual:2099-11-28-garland");
  res[lang] = {
    feed: C.buildIcs(evs, { lang, now: new Date(), alarms: true }),
    page, month: M.monthIcs(m, db, site, lang),
    ld: C.eventLd([g], site, lang, site.url + C.eventPagePath(g, lang), 1, { url: site.url + C.eventPagePath(g, lang) }),
    meta: Object.fromEntries(evs.filter((e) => e.cancelled).map((e) => [e.id, C.cancelledPageMeta(e, site, lang)])),
    flags: Object.fromEntries(evs.map((e) => [e.id, [e.cancelled, e.icsData.cancelled === true, e.detailsUrl]])),
  };
}
out(res);
"""


def vevents(text: str) -> dict[str, list[str]]:
    """UID → the unfolded lines of its VEVENT."""
    out = {}
    for block in text.replace("\r\n ", "").split("BEGIN:VEVENT")[1:]:
        lines = block.split("END:VEVENT")[0].strip().split("\r\n")
        uid = next(l[4:] for l in lines if l.startswith("UID:"))
        out[uid] = lines
    return out


def field(lines: list[str], key: str) -> list[str]:
    return [l.split(":", 1)[1] for l in lines if l.split(":", 1)[0].split(";")[0] == key]


def unescape_ics(s: str) -> str:
    return s.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


class Calendars(unittest.TestCase):
    r: dict | None = None
    SITE = {"url": "https://x.test", "timezone": "America/Chicago", "committee": "NETA 65 Grapevine & La Viña Committee"}
    SUMMARY = ("A Spanish-language workshop on writing your story. Join on Zoom (meeting ID 123 456 7890, passcode zz65). "
               "Coffee after.")

    def res(self) -> dict:
        if Calendars.r is None:
            loc = {"location": "Grupo Uno, 100 Main St, Garland, TX 75041", "city": "Garland", "state": "TX"}
            g = {**event("ev:manual:2099-11-28-garland", datetime(2099, 11, 28, 19, tzinfo=CHI), cancelled=True,
                         slug="2099-11-28-garland", flyer_url=f"https://drive.google.com/file/d/{DRIVE_X}/view",
                         online_url="https://us02web.zoom.us/j/1234567890?pwd=abc", meeting_id="123 456 7890",
                         organizer="District 87 La Viña Committee", **loc),
                 "title": "Test Writing Workshop — Garland", "summary": self.SUMMARY, "tags": ["workshop", "la-vina"]}
            g["i18n"] = {"title": {"en": g["title"], "es": "Taller de Prueba — Garland"}}
            note = {**event("ev:manual:2099-12-05-noted", datetime(2099, 12, 5, 10, tzinfo=CHI), cancelled=True,
                            slug="2099-12-05-noted", cancelled_note={"en": "Moved to January 9, 2100.",
                                                                     "es": "Pasó al 9 de enero de 2100."}, **loc),
                    "title": "Noted Workshop"}
            online = {**event("ev:manual:2099-12-06-online", datetime(2099, 12, 6, 10, tzinfo=CHI), cancelled=True,
                              slug="2099-12-06-online", online_url="https://meet.google.com/abc-defg-hij",
                              platform="Google Meet"), "title": "Online Workshop"}
            over = {**event("ev:manual:over", datetime.now(timezone.utc) - timedelta(days=3), cancelled=True, slug="over",
                            **loc), "title": "Over Workshop"}
            live = {**event("ev:manual:2099-11-21-live", datetime(2099, 11, 21, 19, tzinfo=CHI), slug="2099-11-21-live",
                            flyer_url=f"https://drive.google.com/file/d/{DRIVE_Y}/view", **loc), "title": "Live Workshop"}
            Calendars.r = run_js(self, CAL_JS, data={"site": self.SITE, "items": [live],
                                                     "cancelled": [g, note, online, over]})
        return Calendars.r

    def test_the_entry_of_a_cancelled_event(self):
        for lang, word, note, page in (("en", "Cancelled", "Cancelled — this event will not take place.", "/events/"),
                                       ("es", "Cancelado", "Cancelado: este evento no se realizará.", "/es/events/")):
            r = self.res()[lang]
            tail = "" if lang == "en" else "-es"
            for text in (r["feed"], r["page"], r["month"]):
                with self.subTest(lang=lang, file=text[:60]):
                    g = vevents(text)[f"ev-manual-2099-11-28-garland{tail}@neta65-gvlv"]
                    title = "Test Writing Workshop — Garland" if lang == "en" else "Taller de Prueba — Garland"
                    self.assertEqual(field(g, "SUMMARY"), [f"{word}: {title}"])
                    self.assertEqual(field(g, "STATUS"), ["CANCELLED"])
                    self.assertEqual(field(g, "TRANSP"), ["TRANSPARENT"])
                    self.assertEqual(field(g, "ATTACH"), [])
                    self.assertNotIn("BEGIN:VALARM", g)
                    self.assertEqual(field(g, "DTSTART"), ["20991129T010000Z"])
                    self.assertEqual(unescape_ics(field(g, "LOCATION")[0]), "Grupo Uno, 100 Main St, Garland, TX 75041")
                    self.assertEqual(field(g, "URL"), [f"https://x.test{page}2099-11-28-garland/"])
                    desc = unescape_ics(field(g, "DESCRIPTION")[0])
                    self.assertTrue(desc.startswith(note + "\n\nA Spanish-language workshop on writing your story. "
                                                           "Coffee after."), desc)
                    self.assertTrue(desc.endswith(f": https://x.test{page}2099-11-28-garland/"), desc)
                    for word_ in ("123 456", "zz65", "zoom.us", "Meeting ID", DRIVE_X):
                        self.assertNotIn(word_, "\n".join(g))
            # its own note first; one that is over: its link is /events/ (it has no page any more), still in the feed
            n = vevents(r["page"])[f"ev-manual-2099-12-05-noted{tail}@neta65-gvlv"]
            self.assertTrue(unescape_ics(field(n, "DESCRIPTION")[0]).startswith(
                f"{word}: " + ("Moved to January 9, 2100." if lang == "en" else "Pasó al 9 de enero de 2100.")))
            over = vevents(r["page"])[f"ev-manual-over{tail}@neta65-gvlv"]
            self.assertEqual((field(over, "STATUS"), field(over, "URL")), (["CANCELLED"], [f"https://x.test{page}"]))
            # an online one: no way to join written anywhere
            on = vevents(r["page"])[f"ev-manual-2099-12-06-online{tail}@neta65-gvlv"]
            self.assertNotIn("meet.google.com", "\n".join(on))
            # the event that takes place: as before, with its reminder and flyer (in the file with alarms)
            live = vevents(r["feed"])[f"ev-manual-2099-11-21-live{tail}@neta65-gvlv"]
            self.assertEqual(field(live, "STATUS"), ["CONFIRMED"])
            self.assertEqual(field(live, "TRANSP"), ["OPAQUE"])
            self.assertEqual(field(live, "ATTACH"), [f"https://drive.google.com/file/d/{DRIVE_Y}/view"])
            self.assertIn("BEGIN:VALARM", live)
            # the month's file: the month's cancelled events (not December's), and the cards' data says it only for them
            self.assertEqual(sorted(vevents(r["month"])), [f"ev-manual-2099-11-28-garland{tail}@neta65-gvlv"])
            self.assertEqual(r["flags"]["ev:manual:2099-11-21-live"][:2], [False, False])
            self.assertEqual(r["flags"]["ev:manual:2099-11-28-garland"][:2], [True, True])

    def test_its_event_for_search_engines(self):
        for lang in ("en", "es"):
            [e] = self.res()[lang]["ld"]
            with self.subTest(lang=lang):
                self.assertEqual(e["eventStatus"], "https://schema.org/EventCancelled")
                self.assertEqual((e["startDate"], e["endDate"]), ("2099-11-28T19:00:00-06:00", "2099-11-28T21:00:00-06:00"))
                self.assertEqual(e["location"]["address"]["addressLocality"], "Garland")
                self.assertEqual(e["location"]["address"]["streetAddress"], "100 Main St")
                self.assertEqual(e["organizer"]["name"], "District 87 La Viña Committee")
                self.assertEqual(e["eventAttendanceMode"], "https://schema.org/MixedEventAttendanceMode")
                self.assertNotIn("image", e)
                self.assertEqual(e["url"], "https://x.test" + ("/es" if lang == "es" else "") + "/events/2099-11-28-garland/")
                text = json.dumps(e, ensure_ascii=False)
                for word in ("zoom.us", "123 456", "zz65", DRIVE_X):
                    self.assertNotIn(word, text)

    def test_its_page_words(self):
        en = self.res()["en"]["meta"]
        es = self.res()["es"]["meta"]
        g, ge = en["ev:manual:2099-11-28-garland"], es["ev:manual:2099-11-28-garland"]
        self.assertEqual(g["title"], "Cancelled: Test Writing Workshop — Garland, November 28, 2099")
        self.assertEqual(ge["title"], "Cancelado: Taller de Prueba — Garland, 28 de noviembre de 2099")
        self.assertEqual((g["h1"], ge["h1"]), ("Cancelled: Test Writing Workshop — Garland", "Cancelado: Taller de Prueba — Garland"))
        self.assertEqual(g["description"], "Cancelled. It was planned for Saturday, November 28, 2099, 7:00 – 9:00 PM CST · "
                                           "Grupo Uno, Garland.")
        self.assertEqual(g["was"], "It was planned for Saturday, November 28, 2099, 7:00 – 9:00 PM CST at Grupo Uno, "
                                   "100 Main St, Garland, TX 75041.")
        self.assertTrue(ge["description"].startswith("Cancelado. Estaba previsto para el sábado, 28 de noviembre de 2099, "),
                        ge["description"])
        self.assertTrue(ge["was"].startswith("Estaba previsto para el sábado, 28 de noviembre de 2099, "), ge["was"])
        self.assertTrue(ge["was"].endswith(" en Grupo Uno, 100 Main St, Garland, TX 75041."), ge["was"])
        self.assertIsNone(g["ogImage"])
        on, one = en["ev:manual:2099-12-06-online"], es["ev:manual:2099-12-06-online"]
        self.assertEqual(on["was"], "It was planned for Sunday, December 6, 2099, 10:00 AM – 12:00 PM CST, online.")
        self.assertTrue(one["was"].endswith(", en línea."), one["was"])
        self.assertTrue(on["description"].endswith(" · Online on Google Meet."), on["description"])
        for m in (*en.values(), *es.values()):
            self.assertLessEqual(len(m["description"]), 160)

    def test_its_page_words_over_several_days(self):
        """An event over several days (an assembly, Fri–Sun): its first and last day in full words — never the cards'
        "Fri, Mar 19 – Sun, Mar 21" —, "from … to …" / "del … al …" (never "para el" before a range); the year on both
        days only when they differ; a timed one with its times."""
        loc = {"location": "Civic Center, 1 Main St, Tyler, TX 75701", "city": "Tyler", "state": "TX"}
        day = lambda eid, a, b, **x: {"id": eid, "source": "committee", "kind": "event", "category": "manual",  # noqa: E731
                                      "url": "/events/#x", "title": "Spring Assembly", "summary": "", "lang": "en",
                                      "tags": [], "date": a, "extra": {"start": a, "end": b, "all_day": True,
                                                                       "cancelled": True, "slug": eid[10:], **x}}
        timed = {**event("ev:manual:2099-03-19-timed", datetime(2099, 3, 19, 18, tzinfo=CHI), hours=43, cancelled=True,
                         slug="2099-03-19-timed", **loc), "title": "Timed Assembly"}
        cancelled = [day("ev:manual:2099-03-19-assembly", "2099-03-19", "2099-03-21", **loc),
                     day("ev:manual:2099-12-31-new-year", "2099-12-31", "2100-01-02", **loc),
                     day("ev:manual:2099-04-09-online", "2099-04-09", "2099-04-10", online_url="https://zoom.us/j/1",
                         platform="Zoom"),
                     day("ev:manual:2099-05-14-tba", "2099-05-14", "2099-05-15", location="Tyler, TX", location_tba=True),
                     timed]
        r = run_js(self, SPAN_JS, data={"site": self.SITE, "cancelled": cancelled})
        # (Intl's narrow and thin spaces — a thin space around the range's dash, a narrow one before PM — as plain ones)
        sp = lambda v: re.sub(r"[\u2009\u202f\xa0]", " ", v) if isinstance(v, str) else v  # noqa: E731
        en, es = ({k: {f: sp(v) for f, v in m.items()} for k, m in r[l].items()} for l in ("en", "es"))
        a, ae = en["ev:manual:2099-03-19-assembly"], es["ev:manual:2099-03-19-assembly"]
        self.assertTrue(a["multiDay"])
        self.assertEqual(a["was"], "It was planned from Thursday, March 19 to Saturday, March 21, 2099 at Civic Center, "
                                   "1 Main St, Tyler, TX 75701.")
        self.assertEqual(a["description"], "Cancelled. It was planned from Thursday, March 19 to Saturday, March 21, 2099 · "
                                           "Civic Center, Tyler.")
        self.assertEqual(ae["was"], "Estaba previsto del jueves, 19 de marzo al sábado, 21 de marzo de 2099 en "
                                    "Civic Center, 1 Main St, Tyler, TX 75701.")
        self.assertEqual(ae["description"], "Cancelado. Estaba previsto del jueves, 19 de marzo al sábado, 21 de marzo "
                                            "de 2099 · Civic Center, Tyler.")
        self.assertEqual(a["title"], "Cancelled: Spring Assembly, March 19 – 21, 2099")
        self.assertEqual(a["when"], "Thursday, March 19 – Saturday, March 21, 2099")
        # across a new year: the year on both days
        self.assertTrue(en["ev:manual:2099-12-31-new-year"]["was"].startswith(
            "It was planned from Thursday, December 31, 2099 to Saturday, January 2, 2100 at "), en["ev:manual:2099-12-31-new-year"]["was"])
        self.assertTrue(es["ev:manual:2099-12-31-new-year"]["was"].startswith(
            "Estaba previsto del jueves, 31 de diciembre de 2099 al sábado, 2 de enero de 2100 en "))
        # online; a place to be announced: its days alone
        self.assertEqual(en["ev:manual:2099-04-09-online"]["was"], "It was planned from Thursday, April 9 to Friday, April 10, "
                                                                   "2099, online.")
        self.assertEqual(es["ev:manual:2099-04-09-online"]["was"], "Estaba previsto del jueves, 9 de abril al viernes, 10 de "
                                                                   "abril de 2099, en línea.")
        self.assertEqual(en["ev:manual:2099-05-14-tba"]["description"], "Cancelled. It was planned from Thursday, May 14 to "
                                                                        "Friday, May 15, 2099.")
        self.assertEqual(es["ev:manual:2099-05-14-tba"]["description"], "Cancelado. Estaba previsto del jueves, 14 de mayo al "
                                                                        "viernes, 15 de mayo de 2099.")
        # a timed one: its start and end times, the zone once (CDT all through)
        t, te = en["ev:manual:2099-03-19-timed"], es["ev:manual:2099-03-19-timed"]
        self.assertTrue(t["multiDay"])
        self.assertEqual(t["was"], "It was planned from Thursday, March 19, 6:00 PM to Saturday, "
                                                          "March 21, 2099, 1:00 PM CDT at Civic Center, 1 Main St, Tyler, TX 75701.")
        self.assertEqual(te["was"],
                         "Estaba previsto del jueves, 19 de marzo, 6:00 p. m. al sábado, 21 de marzo de 2099, 1:00 p. m. CDT en "
                         "Civic Center, 1 Main St, Tyler, TX 75701.")
        for m in (*en.values(), *es.values()):
            self.assertNotIn("para el", m["was"] + m["description"])
            self.assertNotRegex(m["was"] + m["description"], r"\b(?:Fri|Sun|vie|dom|Mar|mar)\b,")
            self.assertLessEqual(len(m["description"]), 160)

    def test_its_note_in_the_other_language(self):
        """A note written in one language only: the other language's page shows it, marked as that language
        (ev.cancelledNoteLang); none: ""."""
        only_es = {**event("ev:manual:2099-12-05-es-note", datetime(2099, 12, 5, 10, tzinfo=CHI), cancelled=True,
                           slug="2099-12-05-es-note", cancelled_note={"es": "Pasó al 9 de enero."}), "title": "Note"}
        bare = {**event("ev:manual:2099-12-06-bare", datetime(2099, 12, 6, 10, tzinfo=CHI), cancelled=True,
                        slug="2099-12-06-bare"), "title": "Bare"}
        r = run_js(self, SPAN_JS, data={"site": self.SITE, "cancelled": [only_es, bare]})
        self.assertEqual([r[l]["ev:manual:2099-12-05-es-note"]["noteLang"] for l in ("en", "es")], ["es", "es"])
        self.assertEqual([r[l]["ev:manual:2099-12-05-es-note"]["note"] for l in ("en", "es")], ["Pasó al 9 de enero."] * 2)
        self.assertEqual([r[l]["ev:manual:2099-12-06-bare"]["noteLang"] for l in ("en", "es")], ["", ""])


SPAN_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const res = {};
for (const lang of ["en", "es"]) {
  const evs = C.normalizeEvents(input.cancelled, input.site, lang, { now: new Date("2099-01-01T12:00:00Z") })
    .filter((e) => e.cancelled);
  res[lang] = Object.fromEntries(evs.map((e) => [e.id, { ...C.cancelledPageMeta(e, input.site, lang),
    multiDay: e.multiDay, note: e.cancelledNote, noteLang: e.cancelledNoteLang }]));
}
out(res);
"""


# =========================================================================== the notice page
BASE = "https://x.test"
BUILD_JS = r"""
process.env.ONLY = "event-share,events-ics,sitemap";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const C = await imp("eleventy/seo-check.js");
const LM = await imp("eleventy/lastmod.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r37-pages-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  out({ pages: Object.fromEntries(pages.filter((p) => p.url).map((p) => [p.url, p.content])),
        problems: C.seoProblems(pages, C.siteAddress()),
        // what a notice page's sitemap date is read from (eleventy/lastmod.js: without its data-lastmod="skip" blocks)
        dated: Object.fromEntries(pages.filter((p) => /\/events\/2099-11-28-garland\/$/.test(p.url || ""))
          .map((p) => [p.url, LM.dropSkipped(p.content)])) });
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""


def text_of(fragment: str) -> str:
    t = re.sub(r"<script\b.*?</script>|<svg\b.*?</svg>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def body_ld(page: str) -> list:
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                              page[page.index("<body"):], re.S)]


def head_ld(page: str) -> list:
    """The site's graph in <head> (base.njk), its nodes."""
    out = []
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page[:page.index("<body")], re.S):
        d = json.loads(b)
        out.extend(d.get("@graph", [d]) if isinstance(d, dict) else d)
    return out


class TheNoticePage(unittest.TestCase):
    r: dict | None = None
    LOC = {"location": "Grupo Uno, 100 Main St, Garland, TX 75041", "city": "Garland", "state": "TX"}

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gv-r37-notice-"))
        files = cls.tmp / "events"
        files.mkdir()
        (files / "2099-11-21-file-cancelled.md").write_text('---\ntitle: "x"\ncancelled: true\n---\n', encoding="utf-8")
        chi = lambda *a: datetime(*a, tzinfo=CHI)   # noqa: E731

        def ev(slug, start, title, title_es="", tags=(), **extra):
            it = {**event(f"ev:manual:{slug}", start, slug=slug, file=f"content/events/{slug}.md", **extra),
                  "title": title, "url": f"/events/#{slug}", "tags": list(tags),
                  "summary": f"{title}: a test event. Join on Zoom (meeting ID 123 456 7890)."}
            if title_es:
                it["i18n"] = {"title": {"en": title, "es": title_es}}
                it["extra"]["own_i18n"] = {"title": {"es": title_es}}
            return it

        cls.items = [
            # the next La Viña workshop (a leaf: its own page) and a La Viña event online (its card): "coming up instead"
            ev("2099-12-12-fort-worth", chi(2099, 12, 12, 19), "Test LV Workshop — Fort Worth", "Taller LV — Fort Worth",
               ("workshop", "la-vina"), location="Grupo Dos, 200 Main St, Fort Worth, TX 76106", city="Fort Worth", state="TX"),
            ev("2099-12-19-lv-online", chi(2099, 12, 19, 10), "Test LV Online Meeting", "Reunión LV en línea", ("la-vina",),
               online_url="https://us02web.zoom.us/j/111", platform="Zoom"),
            # a Grapevine workshop: another kind (its colour) — not listed
            ev("2099-12-05-gv-workshop", chi(2099, 12, 5, 14), "Test Grapevine Workshop", "Taller de Grapevine",
               ("workshop", "grapevine"), **cls.LOC),
            # only its file says it is cancelled (the sync has not run): a notice all the same
            ev("2099-11-21-file-cancelled", chi(2099, 11, 21, 19), "Test File Workshop", "Taller del Archivo",
               ("workshop", "la-vina"), **cls.LOC),
            # an event in both lists (the sync never writes one so): the cancelled one — a notice
            ev("2099-10-10-both", chi(2099, 10, 10, 19), "Test Both Workshop", "Taller Doble", ("workshop",), **cls.LOC),
            # an event of the lists whose address a cancelled one (another event) has: since round 37 ONE rule (the event
            # pages' plan leaves every cancelled anchor out) — the notice has it; the sync never writes such a pair
            ev("2099-10-17-anchor", chi(2099, 10, 17, 19), "Test Anchor Workshop", "Taller Ancla", ("workshop",), **cls.LOC),
        ]
        cls.cancelled = [
            ev("2099-11-28-garland", chi(2099, 11, 28, 19), "Test LV Workshop — Garland", "Taller LV — Garland",
               ("workshop", "la-vina"), cancelled=True, flyer_url=f"https://drive.google.com/file/d/{DRIVE_X}/view",
               organizer="District 87 La Viña Committee", cancelled_note={"es": "Lo pasamos a enero."}, **cls.LOC),
            ev("2099-11-14-online", chi(2099, 11, 14, 10), "Test Online Workshop", "Taller en línea", ("la-vina",),
               cancelled=True, online_url="https://meet.google.com/abc-defg-hij", platform="Google Meet"),
            ev("over", datetime.now(timezone.utc) - timedelta(hours=2), "Test Over Workshop", "Taller Pasado", (),
               cancelled=True, past=False, **cls.LOC),
            ev("2099-10-10-both", chi(2099, 10, 10, 19), "Test Both Workshop", "Taller Doble", ("workshop",),
               cancelled=True, **cls.LOC),
            {**ev("2099-10-17-other", chi(2099, 10, 17, 9), "Test Other Workshop", "Taller Otro", ("workshop",),
                  cancelled=True, **cls.LOC), "id": "ev:manual:2099-10-17-other"},
        ]
        cls.cancelled[-1]["extra"]["slug"] = "2099-10-17-anchor"       # (its card's anchor: the listed event's)
        (cls.tmp / "events.json").write_text(json.dumps({"updated": "2026-11-22T12:00:00Z", "items": cls.items,
                                                         "cancelled": cls.cancelled}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def built(self) -> dict:
        if TheNoticePage.r is None:
            TheNoticePage.r = run_js(self, BUILD_JS, timeout=600,
                                     env={"SITE_DATA": str(self.tmp), "CONTENT_EVENTS": str(self.tmp / "events"),
                                          "SITE_URL": BASE, "PATH_PREFIX": "/", "STRICT_BUILD": "", "LASTMOD": ""})
        return TheNoticePage.r

    def page(self, path: str) -> str:
        return self.built()["pages"][path]

    def test_which_pages(self):
        pages, sitemap = self.built()["pages"], self.built()["pages"]["/sitemap.xml"]
        for lang in ("", "/es"):
            for slug in ("2099-11-28-garland", "2099-11-14-online", "2099-11-21-file-cancelled", "2099-10-10-both"):
                with self.subTest(lang=lang, slug=slug):
                    p = pages[f"{lang}/events/{slug}/"]
                    self.assertIn("<h1", p)
                    self.assertIn("Cancelled: " if not lang else "Cancelado: ", text_of(p[p.index("<h1"):]))
                    self.assertNotIn("evcancel.", p)
                    self.assertNotIn("noindex", "".join(re.findall(r'<meta name="robots"[^>]*>', p)))
                    self.assertIn(f'<link rel="canonical" href="{BASE}{lang}/events/{slug}/">', p)
                    self.assertIn(f"<loc>{BASE}{lang}/events/{slug}/</loc>", sitemap)
            # over: no page, no <loc>
            self.assertNotIn(f"{lang}/events/over/", pages)
            self.assertNotIn(f"{BASE}{lang}/events/over/", sitemap)
            # a cancelled event's anchor is its notice's, even when an event of the lists has it too (round 37: one
            # rule, eleventy/event-pages.js cancelledAnchors) — and no address is written twice
            mine = pages[f"{lang}/events/2099-10-17-anchor/"]
            self.assertIn("Test Other Workshop" if not lang else "Taller Otro", mine)
            self.assertNotIn("Test Anchor Workshop" if not lang else "Taller Ancla", mine)
        self.assertEqual(self.built()["problems"], [])

    def test_the_notice(self):
        for lang, banner, was in (
                ("", "This event has been cancelled. It will not take place.",
                 "It was planned for Saturday, November 28, 2099, 7:00 – 9:00 PM CST at Grupo Uno, 100 Main St, Garland, TX 75041."),
                ("/es", "Este evento se canceló. No se realizará.",
                 "Estaba previsto para el sábado, 28 de noviembre de 2099, 7:00–9:00 p. m. CST en Grupo Uno, 100 Main St, "
                 "Garland, TX 75041.")):
            p = self.page(f"{lang}/events/2099-11-28-garland/")
            main = p[p.index("<main"):p.index("</main>")]
            words = text_of(main)
            with self.subTest(lang=lang):
                title = re.search(r"<title>(.*?)</title>", p).group(1)
                self.assertEqual(html.unescape(title), "Cancelled: Test LV Workshop — Garland, November 28, 2099 · Events — NETA 65"
                                 if not lang else "Cancelado: Taller LV — Garland, 28 de noviembre de 2099 · Eventos — NETA 65")
                desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', p).group(1))
                self.assertLessEqual(len(desc), 160)
                self.assertTrue(desc.startswith("Cancelled. " if not lang else "Cancelado. "), desc)
                self.assertIn(banner, words)
                self.assertIn(was.replace("\u2009", " "), words.replace("\u2009", " "))
                # its Event first in <body>: EventCancelled, every value kept but the picture; never how to join
                ld = body_ld(p)[0]
                self.assertEqual((ld["@type"], ld["eventStatus"]), ("Event", "https://schema.org/EventCancelled"))
                self.assertEqual(ld["startDate"], "2099-11-28T19:00:00-06:00")
                self.assertEqual(ld["location"]["address"]["addressLocality"], "Garland")
                self.assertEqual(ld["url"], f"{BASE}{lang}/events/2099-11-28-garland/")
                self.assertNotIn("image", ld)
                # nothing that invites anyone to come: no flyer, no calendar, no join link; Share is kept
                self.assertNotIn("data-cm-ics", p)
                self.assertNotIn("<img", main)
                self.assertNotIn(DRIVE_X, p)
                self.assertNotIn("zoom.us", main)
                self.assertIn(f'data-share="{BASE}{lang}/events/2099-11-28-garland/"', main)
                self.assertNotIn("123 456 7890", words)
                # (round 37's fixer) the visible breadcrumb — the path the site's graph names: Home › Events › the
                # notice, its title as the tab's (base.njk's BreadcrumbList), as on every event's page
                crumbs = re.search(r'<nav class="evp-crumbs"[^>]*>(.*?)</nav>', main, re.S)
                self.assertIsNotNone(crumbs, "a visible breadcrumb")
                self.assertEqual(re.findall(r'<a [^>]*href="([^"]+)"', crumbs.group(1)), [f"{lang}/", f"{lang}/events/"])
                here = re.search(r'<span aria-current="page">(.*?)</span>', crumbs.group(1)).group(1)
                self.assertEqual(html.unescape(here), html.unescape(title).split(" · ")[0])
                graph = next(x for x in head_ld(p) if x.get("@type") == "BreadcrumbList")
                self.assertEqual([i["name"] for i in graph["itemListElement"]][-1], html.unescape(here))
                # coming up instead: the next La Viña events (each its own page: round 37) — never the Grapevine one
                links = re.findall(r'<a href="([^"]+)" class="card card-link cm-mini-card', main)
                self.assertEqual(links, [f"{lang}/events/2099-12-12-fort-worth/", f"{lang}/events/2099-12-19-lv-online/"])
                self.assertIn(f'href="{lang}/events/"', main)
                # …outside the page's sitemap date: those are other events (eleventy/lastmod.js dropSkipped)
                self.assertRegex(main, r'<section [^>]*aria-labelledby="ev-cancel-next"[^>]*data-lastmod="skip"')
                dated = self.built()["dated"][f"{lang}/events/2099-11-28-garland/"]
                dated = dated[dated.index("<main"):dated.index("</main>")]
                self.assertNotIn("Fort Worth", dated)
                self.assertIn(banner, text_of(dated))
                # the organizers' note, written in Spanish only: on the English page marked lang="es"
                note = re.search(r'<p class="mt-2 font-medium text-ink"( lang="es")?>Lo pasamos a enero\.</p>', main)
                self.assertIsNotNone(note, "the note is shown")
                self.assertEqual(note.group(1), ' lang="es"' if not lang else None)

    def test_an_online_one_has_no_event(self):
        for lang in ("", "/es"):
            p = self.page(f"{lang}/events/2099-11-14-online/")
            self.assertEqual(body_ld(p), [])
            self.assertIn("It was planned for Saturday, November 14, 2099, 10:00 AM – 12:00 PM CST, online." if not lang
                          else ", en línea.", text_of(p).replace("\u2009", " "))
            self.assertNotIn("meet.google.com", p)

    def test_the_calendar_feed(self):
        for lang in ("", "/es"):
            evs = vevents(self.page(f"{lang}/events.ics"))
            tail = "-es" if lang else ""
            for slug in ("2099-11-28-garland", "2099-11-21-file-cancelled", "over"):
                with self.subTest(lang=lang, slug=slug):
                    self.assertEqual(field(evs[f"ev-manual-{slug}{tail}@neta65-gvlv"], "STATUS"), ["CANCELLED"])
            self.assertEqual(field(evs[f"ev-manual-over{tail}@neta65-gvlv"], "URL"), [f"{BASE}{lang}/events/"])
            self.assertEqual(field(evs[f"ev-manual-2099-12-12-fort-worth{tail}@neta65-gvlv"], "STATUS"), ["CONFIRMED"])


if __name__ == "__main__":
    unittest.main()
