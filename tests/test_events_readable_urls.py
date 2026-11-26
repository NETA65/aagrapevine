"""Readable addresses for the events made from a dated Drive flyer or an outside calendar, and the two new lines of a
content/events file (since the events list's redesign, November 2026).

  * Slugs (scripts/sync/build_data.py readable_slug, pin_event_slugs): "<its day>-<its title in a few words>", cut at
    a word; PINNED from the last events.json by the event's id — a title that changes later keeps the address; a new
    day makes a new one and keeps the old in extra.slug_aliases (the last 5); two events of one day and title: "-2";
    a content/events file, a monthly date and a committee meeting keep their own; an event of the last file that is
    cancelled now still finds its slug (the file's `cancelled` list is read too).
  * OldAnchors (eleventy/event-redirects.js oldAnchors, eventRedirects): the "ev-<its id>" address and the aliases,
    never the address it has now; one redirect page per old address and language, to its page now — none for a
    cancelled event that is over, none for an event that keeps its address.
  * Lines (scripts/sync/announcements.py event_district, event_language — through parse_event and collect): `district:`
    a district's number ("District 87", "Distrito 91", 87) → extra.district; `language:` en / es / both (English,
    español, bilingual …) → extra.language; anything else is left out and listed (the event still shows); no line, no
    value — a district is never guessed.

    python -m unittest tests.test_events_readable_urls -v
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from nodejs import run_js  # noqa: E402
from test_r20_meeting import ctx_with  # noqa: E402

NOW = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)


def ev(eid: str, category: str, title: str, start: str, **extra) -> dict:
    return {"id": eid, "category": category, "title": title, "date": start, "extra": {"start": start, **extra}}


class Slugs(unittest.TestCase):
    def ctx(self):
        return ctx_with(now=NOW)

    def test_a_readable_slug(self):
        self.assertEqual(B.readable_slug("2026-10-31", "Grapevine Committee Crash"), "2026-10-31-grapevine-committee-crash")
        self.assertEqual(B.readable_slug("2027-01-29", "XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la libertad)"),
                         "2027-01-29-xlii-reunion-de-a-a-zona-norte-de-texas-a-a-un-camino-a-la")
        self.assertLessEqual(len(B.readable_slug("2027-01-29", "word " * 40)) - 11, B.READABLE_SLUG_TITLE_MAX)
        self.assertEqual(B.readable_slug("2027-01-29", "¡!"), "2027-01-29-item")

    def test_pinned_kept_and_moved(self):
        ctx = self.ctx()
        first = [ev("ev:flyer:abc", "flyer", "Grapevine Committee Crash", "2026-12-12T19:00:00Z"),
                 ev("ev:lvcal:x1", "lv-calendar", "Taller Mensual", "2027-01-23"),
                 ev("ev:gvcal:y1", "gv-calendar", "Taller Mensual", "2027-01-23"),
                 ev("ev:manual:2027-02-21-acm", "manual", "Winter ACM", "2027-02-21", slug="2027-02-21-acm"),
                 ev("ev:recurring:citywide-dallas:2026-12-12", "recurring", "Booth", "2026-12-12T23:30:00Z", series="citywide-dallas"),
                 ev("ev:committee:2026-12-16", "committee", "Committee meeting", "2026-12-17T01:00:00Z")]
        B.pin_event_slugs(ctx, first, None)
        slugs = {e["id"]: e["extra"].get("slug") for e in first}
        self.assertEqual(slugs["ev:flyer:abc"], "2026-12-12-grapevine-committee-crash", "its day in Central time")
        self.assertEqual(slugs["ev:lvcal:x1"], "2027-01-23-taller-mensual")
        self.assertEqual(slugs["ev:gvcal:y1"], "2027-01-23-taller-mensual-2", "the same day and title: -2")
        self.assertEqual(slugs["ev:manual:2027-02-21-acm"], "2027-02-21-acm", "a file keeps its name")
        self.assertIsNone(slugs["ev:recurring:citywide-dallas:2026-12-12"])
        self.assertIsNone(slugs["ev:committee:2026-12-16"])
        last = {"items": copy.deepcopy(first[:3]), "cancelled": []}
        # the next day's update: the flyer's title changed, the calendar's listing moved to another day
        nxt = [ev("ev:flyer:abc", "flyer", "Grapevine Committee CRASH — new name", "2026-12-12T19:00:00Z"),
               ev("ev:lvcal:x1", "lv-calendar", "Taller Mensual", "2027-01-30"),
               ev("ev:gvcal:y1", "gv-calendar", "Taller Mensual", "2027-01-23")]
        B.pin_event_slugs(ctx, nxt, last)
        self.assertEqual(nxt[0]["extra"]["slug"], "2026-12-12-grapevine-committee-crash", "a new title keeps the address")
        self.assertNotIn("slug_aliases", nxt[0]["extra"])
        self.assertEqual(nxt[1]["extra"]["slug"], "2027-01-30-taller-mensual", "a new day: a new address")
        self.assertEqual(nxt[1]["extra"]["slug_aliases"], ["2027-01-23-taller-mensual"])
        self.assertEqual(nxt[2]["extra"]["slug"], "2027-01-23-taller-mensual-2", "kept, -2 and all")
        # a day that moves back: the address it had before comes back, and is no alias of itself
        again = [ev("ev:lvcal:x1", "lv-calendar", "Taller Mensual", "2027-01-23")]
        B.pin_event_slugs(ctx, again, {"items": copy.deepcopy(nxt), "cancelled": []})
        self.assertEqual(again[0]["extra"]["slug"], "2027-01-23-taller-mensual")
        self.assertEqual(again[0]["extra"]["slug_aliases"], ["2027-01-30-taller-mensual"])
        # an event of the last file's cancelled list keeps its slug; at most 5 aliases
        gone = {"items": [], "cancelled": [ev("ev:flyer:off", "flyer", "Old", "2026-12-20", slug="2026-12-20-old-name",
                                              slug_aliases=[f"2026-11-0{i}-x" for i in range(1, 7)])]}
        kept = [ev("ev:flyer:off", "flyer", "New", "2026-12-20")]
        B.pin_event_slugs(ctx, kept, gone)
        self.assertEqual(kept[0]["extra"]["slug"], "2026-12-20-old-name")
        self.assertEqual(len(kept[0]["extra"]["slug_aliases"]), B.READABLE_ALIASES_KEEP)

    def test_main_pins_them_from_the_last_file(self):
        src = (ROOT / "scripts" / "sync" / "build_data.py").read_text(encoding="utf-8")
        self.assertIn('"events": pin_event_slugs(ctx, build_events(ctx), read_json(out_dir / "events.json")),', src)


OLD_JS = r"""
const R = await imp("eleventy/event-redirects.js");
const ev = (id, category, start, extra) => ({ id, category, title: "T " + id, i18n: { title: { en: "T", es: "T es" } }, date: start,
  status: "ok", kind: "event", extra: Object.assign({ start, end: start }, extra || {}) });
const items = [
  ev("ev:flyer:abc", "flyer", "2026-12-12", { slug: "2026-12-12-crash", slug_aliases: ["2026-12-11-crash"] }),
  ev("ev:lvcal:x1", "lv-calendar", "2027-01-23"),                                   // no readable slug yet
  ev("ev:manual:zz", "manual", "2027-01-24", { slug: "zz" }),
];
const cancelled = [ev("ev:flyer:off", "flyer", "2026-12-20", { slug: "2026-12-20-off", cancelled: true }),
                   ev("ev:flyer:over", "flyer", "2026-11-01", { slug: "2026-11-01-over", cancelled: true, past: true })];
out({
  old: items.map(R.oldAnchors),
  redirects: R.eventRedirects(items, cancelled, { built: "2026-11-26T18:00:00Z" }, ["en", "es"]),
});
"""


class OldAnchors(unittest.TestCase):
    def test_old_addresses_and_their_pages(self):
        r = run_js(self, OLD_JS)
        self.assertEqual(r["old"], [["ev-flyer-abc", "2026-12-11-crash"], [], []])
        got = {(x["lang"], x["path"]): x["target"] for x in r["redirects"]}
        self.assertEqual(got, {
            ("en", "/events/ev-flyer-abc/"): "/events/2026-12-12-crash/",
            ("en", "/events/2026-12-11-crash/"): "/events/2026-12-12-crash/",
            ("es", "/es/events/ev-flyer-abc/"): "/es/events/2026-12-12-crash/",
            ("es", "/es/events/2026-12-11-crash/"): "/es/events/2026-12-12-crash/",
            ("en", "/events/ev-flyer-off/"): "/events/2026-12-20-off/",
            ("es", "/es/events/ev-flyer-off/"): "/es/events/2026-12-20-off/",
        })
        self.assertEqual({x["title"] for x in r["redirects"] if x["lang"] == "es" and "abc" in x["path"]}, {"T es"})


class Lines(unittest.TestCase):
    def test_district_and_language(self):
        for v, want in (("87", "87"), ("District 87", "87"), ("Distrito 91", "91"), (87, "87"), ("D42", "42"), ("#5", "5")):
            with self.subTest(v=v):
                self.assertEqual(A.event_district({"district": v}), (want, None))
        self.assertEqual(A.event_district({"distrito": "87"}), ("87", None))
        for v in ("north", "0", "1234", "District 87 and 91"):
            with self.subTest(v=v):
                got, problem = A.event_district({"district": v})
                self.assertIsNone(got)
                self.assertIn("is not a district number", problem)
        self.assertEqual(A.event_district({}), (None, None))
        for v, want in (("en", "en"), ("English", "en"), ("inglés", "en"), ("es", "es"), ("Español", "es"), ("Spanish", "es"),
                        ("both", "both"), ("Bilingual", "both"), ("bilingüe", "both")):
            with self.subTest(v=v):
                self.assertEqual(A.event_language({"language": v}), (want, None))
        self.assertEqual(A.event_language({"idioma": "español"}), ("es", None))
        got, problem = A.event_language({"language": "French"})
        self.assertIsNone(got)
        self.assertIn("is not a language the site knows", problem)
        self.assertEqual(A.event_language({}), (None, None))

    def test_a_file_with_them_and_one_with_slips(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "events"
            folder.mkdir()
            (folder / "2027-03-14-zz-workshop.md").write_text(
                '---\ntitle: "ZZ Workshop"\nstart: 2027-03-14T10:00:00-05:00\nlocation: "Hall, 1 Main St, Tyler, TX 75702"\n'
                'district: "District 42"\nlanguage: bilingual\n---\nText.\n', encoding="utf-8")
            (folder / "2027-03-15-zz-slips.md").write_text(
                '---\ntitle: "ZZ Slips"\nstart: 2027-03-15\ndistrict: north\nlanguage: french\n---\nText.\n', encoding="utf-8")
            (folder / "2027-03-16-zz-none.md").write_text('---\ntitle: "ZZ None"\nstart: 2027-03-16\n---\nText.\n', encoding="utf-8")
            tz = B.Ctx(offline=True).tz
            items, problems, failed = A.collect(folder, lambda p: A.parse_event(p, tz), "events")
        by = {it["extra"]["slug"]: it["extra"] for it in items}
        self.assertEqual((by["2027-03-14-zz-workshop"]["district"], by["2027-03-14-zz-workshop"]["language"]), ("42", "both"))
        self.assertNotIn("district", by["2027-03-15-zz-slips"], "the event still shows, without the line")
        self.assertNotIn("language", by["2027-03-15-zz-slips"])
        self.assertNotIn("line_problems", by["2027-03-15-zz-slips"])
        self.assertFalse({"district", "language"} & set(by["2027-03-16-zz-none"]), "never guessed")
        self.assertEqual(failed, set())
        self.assertEqual(len([p for p in problems if "2027-03-15-zz-slips.md" in p]), 2)
        self.assertTrue(any("district: “north”" in p for p in problems))
        self.assertTrue(any("language: “french”" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
