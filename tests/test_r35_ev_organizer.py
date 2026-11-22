"""Round 35 · who organizes an event, for search engines: a content/events file's optional `organizer:` (the name of
the committee or group that organizes it when it is not us — "District 87 La Viña Committee", never a person's) and
`organizer_url:` (its https:// page), read by scripts/sync/announcements.py (event_organizer → extra.organizer /
extra.organizer_url) and named by eleventy/filters/committee.js eventLd as the Event's organizer (tests/
test_seo_events.py). A line the site cannot use is left out and listed on /status/ (collect); the event still shows.

    python -m unittest tests.test_r35_ev_organizer -v
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import announcements as A  # noqa: E402

CHI = ZoneInfo("America/Chicago")


class TheTwoLines(unittest.TestCase):
    def test_what_is_kept(self):
        f = A.event_organizer
        self.assertEqual(f("District 87 La Viña Committee", None), ("District 87 La Viña Committee", None, None))
        self.assertEqual(f("  District 90   La Viña Committee ", "https://neta65.org/district-90/"),
                         ("District 90 La Viña Committee", "https://neta65.org/district-90/", None))
        self.assertEqual(f(None, None), (None, None, None))
        self.assertEqual(f("", ""), (None, None, None))
        self.assertEqual(f("Grupo Volver a Vivir", "HTTPS://example.org"), ("Grupo Volver a Vivir", "https://example.org", None))

    def test_what_is_left_out_and_said(self):
        f = A.event_organizer
        org, url, problem = f("District 87 La Viña Committee", "http://example.org/")
        self.assertEqual((org, url), ("District 87 La Viña Committee", None))
        self.assertEqual(problem, "organizer_url: “http://example.org/” must be a web address that starts with https:// "
                                  "— left out")
        for bad in ("example.org/d87", "https://", "https://localhost", "mailto:x@example.org"):
            with self.subTest(url=bad):
                self.assertIsNotNone(f("District 87", bad)[2])
                self.assertIsNone(f("District 87", bad)[1])
        # an address in the name, a name too long, no name at all: never named (search engines are told what they were
        # before: the Area for its own events, else the committee)
        for bad, said in (("https://district87.example.org", "holds a web or e-mail address"),
                          ("lv87@example.org", "holds a web or e-mail address"),
                          ("District 87 " + "x" * 120, "characters long"),
                          (True, "is not a name"), (["District 87"], "is not a name")):
            with self.subTest(name=bad):
                org, url, problem = f(bad, None)
                self.assertIsNone(org)
                self.assertIn(said, problem)
        # a page without a name: left out too
        self.assertEqual(f(None, "https://example.org/"),
                         (None, None, "organizer_url: “https://example.org/” goes with an organizer: line (the committee's "
                                      "or group's name) — left out"))
        # two slips: both said
        problem = f("<b>District</b>", "ftp://x")[2]
        self.assertTrue(problem.startswith("organizer: “<b>District</b>” holds a web or e-mail address"), problem)
        self.assertIn("; organizer_url: “ftp://x” goes with an organizer: line", problem)


class TheFile(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="gv-organizer-"))
        self.addCleanup(shutil.rmtree, self.folder, True)

    def write(self, name: str, head: str) -> Path:
        p = self.folder / name
        p.write_text(f"---\ntitle: La Viña Writing Workshop — Garland\nstart: 2026-11-28T19:00:00-06:00\n{head}---\n"
                     "Organized by the District 87 La Viña committee.\n", encoding="utf-8")
        return p

    def test_read_into_the_events_extra(self):
        ok = A.parse_event(self.write("2026-11-28-a.md", 'organizer: "District 87 La Viña Committee"\n'
                                                        'organizer_url: "https://example.org/d87/"\n'), CHI)
        self.assertEqual((ok["extra"]["organizer"], ok["extra"]["organizer_url"]),
                         ("District 87 La Viña Committee", "https://example.org/d87/"))
        self.assertNotIn("organizer_problem", ok["extra"])
        plain = A.parse_event(self.write("2026-11-28-b.md", ""), CHI)
        self.assertNotIn("organizer", plain["extra"])
        self.assertNotIn("organizer_url", plain["extra"])

    def test_a_slip_is_listed_and_the_event_still_shows(self):
        self.write("2026-11-28-c.md", 'organizer: "District 87 La Viña Committee"\norganizer_url: "www.example.org"\n')
        items, errors, failed = A.collect(self.folder, lambda p: A.parse_event(p, CHI), "events")
        self.assertEqual(failed, set())
        it = next(i for i in items if i["id"] == "ev:manual:2026-11-28-c")
        self.assertEqual(it["extra"]["organizer"], "District 87 La Viña Committee")
        self.assertNotIn("organizer_url", it["extra"])
        self.assertNotIn("organizer_problem", it["extra"])            # (reported by collect, not kept in the data)
        self.assertEqual(errors, [f"{self.folder.name}/2026-11-28-c.md: organizer_url: “www.example.org” must be a web "
                                  "address that starts with https:// — left out"])


class TheWorkshops(unittest.TestCase):
    """The two district workshops of 2026 say who organizes them (their own texts say so) — copies of their files as
    they were written (tests/fixtures/events/, since round 37: the real ones in content/events may be deleted once
    their day is long over — the Garland one was cancelled on 2026-11-22, `cancelled: true` — and a test of the Code
    check must never depend on the committee's content)."""

    FIXTURES = ROOT / "tests" / "fixtures" / "events"

    def test_their_files(self):
        for name, who in (("2026-11-28-lv-writing-workshop-garland.md", "District 87 La Viña Committee"),
                          ("2026-12-12-lv-writing-workshop-fort-worth.md", "District 90 La Viña Committee")):
            with self.subTest(file=name):
                it = A.parse_event(self.FIXTURES / name, CHI)
                self.assertEqual(it["extra"]["organizer"], who)
                self.assertNotIn("organizer_url", it["extra"])
                self.assertNotIn("organizer_problem", it["extra"])
                self.assertIn(who.split(" La Viña")[0], it["summary"])         # "District 87": what its text says
                # (the organizer stays what search engines are told on the cancelled one's notice page too)
                self.assertEqual(it["extra"].get("cancelled"), True if "garland" in name else None)


if __name__ == "__main__":
    unittest.main()
