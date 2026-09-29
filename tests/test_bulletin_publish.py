"""Scheduled bulletin posts: a post that goes up on a later day by itself.

  * content/bulletin: `publish: 2027-02-01` in the header (scripts/sync/announcements.py → extra.publish);
  * Google Drive "bulletin" folder: "(from 2027-02-01)" / "(desde 2027-02-01)" in the file name
    (scripts/sync/drive.py; "(from the Chair)" is a title, not a date);
  * build_data leaves a post out of the site data (the bulletin, What's New, the feed, the search) until its
    day in Central time, lists it in status.json `scheduled` (the Actions run summary), and dates its news
    from that day once it is up (Ctx.effective_ts).

(tests/test_bulletin.py covers the rest of the bulletin.)

    python -m unittest tests.test_bulletin_publish -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import drive as D  # noqa: E402
from scripts.sync.drive_listing import Entry  # noqa: E402


class Folder(unittest.TestCase):
    """A temporary content/bulletin (and data/raw) for each test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-publish-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dir = self.tmp / "bulletin"
        self.dir.mkdir()
        (self.tmp / "events").mkdir()
        (self.tmp / "raw").mkdir()
        for obj, name, val in ((A, "ANN_DIR", self.dir), (A, "EVENTS_DIR", self.tmp / "events"),
                               (A, "LEGACY_ANN_DIR", self.tmp / "announcements"), (common, "RAW_DIR", self.tmp / "raw")):
            p = mock.patch.object(obj, name, val)
            p.start()
            self.addCleanup(p.stop)

    def write(self, name: str, text: str) -> Path:
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def parse(self, name: str, text: str) -> dict:
        return A.parse_announcement(self.write(name, text))

    def run_sync(self, today: date) -> dict:
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(today.year, today.month, today.day, 12, 0, tzinfo=tz or timezone.utc)
        with mock.patch.object(A, "datetime", Clock):
            A.main([])
        return json.loads((self.tmp / "raw" / "announcements.json").read_text(encoding="utf-8"))


class Header(Folder):
    def test_publish_is_read(self):
        it = self.parse("spring.md", "---\ntitle: Spring Assembly sign-ups\npublish: 2027-02-01\n---\nSign up!\n")
        self.assertEqual(it["extra"]["publish"], "2027-02-01")
        self.assertEqual(it["date"], "2027-02-01", "no date: → the day it goes up")
        plain = self.parse("plain.md", "---\ntitle: Now\n---\nText.\n")
        self.assertNotIn("publish", plain["extra"])

    def test_a_date_or_the_file_name_wins_over_publish(self):
        it = self.parse("x.md", "---\ntitle: X\ndate: 2027-01-10\npublish: 2027-02-01\n---\nx\n")
        self.assertEqual((it["date"], it["extra"]["publish"]), ("2027-01-10", "2027-02-01"))
        it = self.parse("2027-01-15-y.md", "---\ntitle: Y\npublish: 2027-02-01\n---\ny\n")
        self.assertEqual(it["date"], "2027-01-15")
        it = self.parse("z.md", "---\ntitle: Z\npublish: February 1, 2027\n---\nz\n")    # words work too
        self.assertEqual(it["extra"]["publish"], "2027-02-01")

    def test_mistakes_are_reported(self):
        with self.assertRaisesRegex(ValueError, r"the publish date 'next week' is not a date \(use YYYY-MM-DD\)"):
            self.parse("bad.md", "---\ntitle: Bad\npublish: next week\n---\nx\n")
        with self.assertRaisesRegex(ValueError, "publish: is after expires: — the post would never show"):
            self.parse("never.md", "---\ntitle: Never\npublish: 2027-03-01\nexpires: 2027-02-01\n---\nx\n")
        # the same day is fine: it shows that one day
        it = self.parse("day.md", "---\ntitle: Day\npublish: 2027-03-01\nexpires: 2027-03-01\n---\nx\n")
        self.assertEqual((it["extra"]["publish"], it["extra"]["expires"]), ("2027-03-01", "2027-03-01"))

    def test_the_template_parses(self):
        """content/bulletin/_example.md shows every option, publish: included."""
        src = ROOT / "content" / "bulletin" / "_example.md"
        it = A.parse_announcement(self.write("example.md", src.read_text(encoding="utf-8")))
        self.assertTrue(it["extra"].get("publish"), "_example.md shows publish:")
        self.assertLessEqual(it["extra"]["publish"], it["extra"]["expires"])

    def test_active_counts_the_central_day(self):
        self.write("later.md", "---\ntitle: Later\npublish: 2027-02-01\n---\nx\n")
        self.write("gone.md", "---\ntitle: Gone\nexpires: 2027-01-31\n---\nx\n")
        self.write("now.md", "---\ntitle: Now\n---\nx\n")
        env = self.run_sync(date(2027, 1, 31))
        self.assertEqual(env["stats"]["active"], 2)             # now + gone (its last day)
        self.assertEqual(self.run_sync(date(2027, 2, 1))["stats"]["active"], 2)   # now + later
        self.assertEqual(env["stats"]["problems"], 0)


class DriveNames(unittest.TestCase):
    """A Google Doc in the Drive "bulletin" folder, named with "(from …)"."""

    def item(self, name: str, modified: str = "2026-09-28") -> dict:
        e = Entry(id="doc1", name=name, mime="application/vnd.google-apps.document", modified=modified)
        f = D.Found(e, D.Panel(77, "Panel 77 (2027–2028)", "p77", "2027-2028_Panel77_GVLV"), ["bulletin"], ["root", "p77", "b"])
        return D.build_item(f, {})

    def test_from_and_desde(self):
        it = self.item("Spring Assembly sign-ups (from 2027-02-01)")
        self.assertEqual((it["kind"], it["title"], it["extra"]["publish"]), ("announcement", "Spring Assembly sign-ups", "2027-02-01"))
        self.assertEqual(it["date"], "2027-02-01", "an undated scheduled post is dated the day it goes up")
        it = self.item("Inscripciones para la Asamblea [desde 1 de febrero de 2027] (hasta 2027-03-01)")
        self.assertEqual((it["title"], it["extra"]["publish"], it["extra"]["expires"]),
                         ("Inscripciones para la Asamblea", "2027-02-01", "2027-03-01"))

    def test_a_date_in_the_name_is_still_the_date(self):
        it = self.item("2027-01-20 Save the date (publish 2027-02-01)")
        self.assertEqual((it["title"], it["date"], it["extra"]["publish"]), ("Save the date", "2027-01-20", "2027-02-01"))

    def test_words_that_are_not_a_date_stay_in_the_title(self):
        it = self.item("A letter (from the Chair)")
        self.assertEqual(it["title"], "A letter (from the Chair)")
        self.assertNotIn("publish", it["extra"])
        self.assertEqual(it["date"], "2026-09-28")
        it = self.item("A letter (from the Chair) (from 2027-02-01)")
        self.assertEqual((it["title"], it["extra"]["publish"]), ("A letter (from the Chair)", "2027-02-01"))

    def test_only_bulletin_posts_are_scheduled(self):
        e = Entry(id="pdf1", name="Agenda (from 2027-02-01).pdf", mime="application/pdf", modified="2026-09-28")
        it = D.build_item(D.Found(e, D.Panel(77, "Panel 77", "p77", "P77"), ["notes"], ["root", "p77", "n"]), {})
        self.assertEqual(it["kind"], "document")
        self.assertNotIn("publish", it["extra"])


class SiteData(unittest.TestCase):
    """build_data: a scheduled post is not on the site before its day; on the day it is news."""
    PUBLISH = "2026-10-05"

    def ctx(self, now: str) -> B.Ctx:
        c = B.Ctx(offline=True)
        c.now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        c.now_ts = c.now.timestamp()
        c.today_local = c.now.astimezone(c.tz).date()
        post = {"id": "ann:spring", "source": "committee", "kind": "announcement", "url": "/bulletin/#spring",
                "title": "Spring Assembly sign-ups", "summary": "Sign up!", "lang": "en", "date": self.PUBLISH,
                "first_seen": "2026-09-20T15:00:00Z", "category": "manual",
                "extra": {"body_md": "Sign up!", "slug": "spring", "file": "content/bulletin/spring.md",
                          "publish": self.PUBLISH, "pinned": False}}
        dated = {**post, "id": "ann:dated", "date": "2026-09-21", "title": "Written earlier",
                 "extra": {**post["extra"], "slug": "dated", "file": "content/bulletin/dated.md"}}
        now_post = {**post, "id": "ann:now", "date": "2026-09-22", "title": "Up already",
                    "extra": {"body_md": "x", "slug": "now", "file": "content/bulletin/now.md", "pinned": False}}
        drive = {"id": "drive:doc1", "source": "drive", "kind": "announcement", "url": "https://docs.google.com/x",
                 "title": "Inscripciones", "lang": "es", "date": "2026-10-10", "first_seen": "2026-09-21T15:00:00Z",
                 "category": "announcements", "extra": {"publish": "2026-10-10", "name": "Inscripciones (desde 2026-10-10)"}}
        c.raw = {"announcements": {"items": [post, dated, now_post]}, "drive": {"items": [drive]}}
        c.births = {"announcements": 0.0, "drive": 0.0}
        return c

    def status(self, c: B.Ctx) -> dict:
        return B.build_status(c, None, B.I18n(None), {}, False, 0.0)

    def test_the_day_before_it_is_only_listed_as_scheduled(self):
        c = self.ctx("2026-10-05T04:30:00Z")                 # 11:30 PM CDT on October 4
        anns = B.build_announcements(c)
        self.assertEqual([a["id"] for a in anns], ["ann:now"])
        wn = B.materialize_whatsnew(B.plan_whatsnew(c, {"announcements": anns}))
        self.assertEqual([i["id"] for i in wn], ["ann:now"])
        st = self.status(c)
        self.assertEqual(st["scheduled"], [
            {"publish": "2026-10-05", "title": "Spring Assembly sign-ups", "source": "committee", "file": "content/bulletin/spring.md"},
            {"publish": "2026-10-05", "title": "Written earlier", "source": "committee", "file": "content/bulletin/dated.md"},
            {"publish": "2026-10-10", "title": "Inscripciones", "source": "drive", "file": "Inscripciones (desde 2026-10-10)"}])

    def test_on_its_day_it_is_news_from_that_day(self):
        c = self.ctx("2026-10-05T10:05:00Z")                 # 5:05 AM CDT on October 5 (the morning refresh)
        anns = B.build_announcements(c)
        self.assertEqual(sorted(a["id"] for a in anns), ["ann:dated", "ann:now", "ann:spring"])
        spring = next(a for a in anns if a["id"] == "ann:spring")
        self.assertEqual(spring["extra"]["publish"], "2026-10-05", "a published post keeps extra.publish")
        wn = {i["id"]: i for i in B.materialize_whatsnew(B.plan_whatsnew(c, {"announcements": anns}))}
        # news on its publish day in Central time, whatever its date says
        for pid in ("ann:spring", "ann:dated"):
            day = datetime.fromisoformat(wn[pid]["wn_date"].replace("Z", "+00:00")).astimezone(c.tz).date()
            self.assertEqual(day.isoformat(), "2026-10-05", pid)
        self.assertEqual(wn["ann:dated"]["wn_date"], "2026-10-05T05:00:00Z")   # 00:00 CDT, not September 21
        self.assertTrue(c.is_new(spring, "announcements"))
        self.assertTrue(c.is_new(next(a for a in anns if a["id"] == "ann:dated"), "announcements"))
        self.assertEqual([s["title"] for s in self.status(c)["scheduled"]], ["Inscripciones"])

    def test_scheduled_list_is_capped_soonest_first(self):
        c = self.ctx("2026-10-01T15:00:00Z")
        c.raw["announcements"]["items"] = [
            {"id": f"ann:p{n:02d}", "source": "committee", "kind": "announcement", "title": f"Post {n:02d}",
             "date": None, "first_seen": "2026-09-20T15:00:00Z",
             "extra": {"publish": f"2026-11-{30 - n:02d}", "file": f"content/bulletin/p{n:02d}.md"}}
            for n in range(25)]
        c.raw["drive"]["items"] = []
        self.assertEqual(B.build_announcements(c), [])
        st = self.status(c)
        self.assertEqual(len(st["scheduled"]), B.SCHEDULED_MAX)
        days = [s["publish"] for s in st["scheduled"]]
        self.assertEqual(days, sorted(days))
        self.assertEqual(days[0], "2026-11-06")


if __name__ == "__main__":
    unittest.main()
