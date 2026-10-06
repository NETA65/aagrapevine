"""Dates read from the sources' own words (review round 7, unit D):

  * common.date_from_text / date_range_from_text — dates in Drive file names and hand-written files: numbers-only
    dates in day-month order ("Taller 05-10-2026", "14-03-2027"), ranges ("March 14 - 16, 2027"), a note for a
    name that could be read two ways (take_date_notes → drive's stats["warnings"] → /status/)       (P3-3)
  * content/events start / end: a date without its year, a time alone ("start: 19:00" — YAML's 1140), a UTC
    offset that is not Central time's                                                               (P3-4)
  * "first seen" days in Central time, not UTC (common.site_day; announcements.finalize)              (P3-9)
Run:  python -m unittest tests.test_source_dates -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import announcements as A  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import drive as D  # noqa: E402

CHI = ZoneInfo("America/Chicago")


class NumbersOnly(unittest.TestCase):
    """P3-3: "Taller 05-10-2026" (meant as 5 October) became an event on 10 May; "14-03-2027" gave no date."""

    def setUp(self):
        common.take_date_notes()                   # nothing left over from another test

    def test_spanish_names_are_day_first(self):
        self.assertEqual(common.date_from_text("Taller 05-10-2026"), ("2026-10-05", "Taller"))
        self.assertEqual(common.date_from_text("Reunión de servicio 01/02/2027"), ("2027-02-01", "Reunión de servicio"))
        self.assertEqual(common.date_from_text("Report 05-10-2026", lang="es")[0], "2026-10-05")
        self.assertEqual(common.take_date_notes(), [])

    def test_a_day_over_12_tells_the_order(self):
        self.assertEqual(common.date_from_text("14-03-2027"), ("2027-03-14", ""))
        self.assertEqual(common.date_from_text("Workshop 03-14-2027"), ("2027-03-14", "Workshop"))
        self.assertEqual(common.date_from_text("31.12.2026 New Year"), ("2026-12-31", "New Year"))
        self.assertEqual(common.date_from_text("13-13-2026 x"), (None, "13-13-2026 x"))
        self.assertEqual(common.take_date_notes(), [])

    def test_english_names_stay_month_first(self):
        self.assertEqual(common.date_from_text("Writing Workshop 05-10-2026")[0], "2026-05-10")
        self.assertEqual(common.date_from_text("Taller 05-10-2026", lang="en")[0], "2026-05-10")   # the caller knows
        self.assertEqual(common.date_from_text("05-05-2026 Book sale")[0], "2026-05-05")           # the same both ways
        self.assertEqual(common.take_date_notes(), [])

    def test_a_name_that_does_not_tell_is_read_as_before_and_noted(self):
        notes: list[str] = []
        self.assertEqual(common.date_from_text("Report 05-10-2026", notes=notes), ("2026-05-10", "Report"))
        self.assertEqual(notes, ["“Report 05-10-2026”: “05-10-2026” could be May 10 or October 5, 2026 — read as "
                                 "May 10 (month first). Write the date year-month-day (2026-05-10 or 2026-10-05) "
                                 "to be sure"])
        self.assertEqual(common.take_date_notes(), [])                         # given to the caller's list only
        # without a list: kept for the module that saves the source, once each, then forgotten
        common.date_from_text("Report 05-10-2026")
        common.date_from_text("Report 05-10-2026")
        common.date_from_text("GV LV 02/03/2027")
        notes = common.take_date_notes()
        self.assertEqual(len(notes), 2)
        self.assertIn("“GV LV 02/03/2027”: “02/03/2027” could be February 3 or March 2, 2027", notes[1])
        self.assertEqual(common.take_date_notes(), [])


class Ranges(unittest.TestCase):
    """P3-3: "March 14 - 16, 2027" gave no date at all; "14 - 16 de marzo de 2027" gave the LAST day."""

    def test_ranges_give_the_first_day_and_the_last(self):
        cases = {
            "March 14 - 16, 2027": ("2027-03-14", "2027-03-16", ""),
            "Spring Assembly March 14-16 2027": ("2027-03-14", "2027-03-16", "Spring Assembly"),
            "Retreat March 30 - April 2, 2027": ("2027-03-30", "2027-04-02", "Retreat"),
            "Dec. 30 – Jan. 2, 2027": ("2026-12-30", "2027-01-02", ""),
            "Taller del 14 al 16 de marzo de 2027": ("2027-03-14", "2027-03-16", "Taller"),
            "Convención 30 de marzo al 2 de abril de 2027": ("2027-03-30", "2027-04-02", "Convención"),
            "2027-03-14 - 2027-03-16 Assembly": ("2027-03-14", "2027-03-16", "Assembly"),
            "March 14, 2027 – March 16, 2027 Retreat": ("2027-03-14", "2027-03-16", "Retreat"),
        }
        for text, want in cases.items():
            self.assertEqual(common.date_range_from_text(text), want, text)
        self.assertEqual(common.date_from_text("Assembly March 14 - 16, 2027"), ("2027-03-14", "Assembly"))

    def test_what_is_not_a_range(self):
        self.assertEqual(common.date_range_from_text("Distrito 7 - 14 de marzo de 2027"),
                         ("2027-03-14", None, "Distrito 7"))                 # a district, then the day
        self.assertEqual(common.date_range_from_text("Steps 1-12 March 2027")[:2], ("2027-03-12", None))
        self.assertEqual(common.date_range_from_text("March 16 - 14, 2027"), (None, None, "March 16 - 14, 2027"))
        self.assertEqual(common.date_range_from_text("2027-03-14-welcome"), ("2027-03-14", None, "welcome"))
        self.assertEqual(common.date_range_from_text("2026-10-17 Workshop 2-4pm @ Tyler, TX"),
                         ("2026-10-17", None, "Workshop 2-4pm @ Tyler, TX"))
        self.assertEqual(common.date_range_from_text("2026-10-05 a las 7 pm")[:2], ("2026-10-05", None))


class Callers(unittest.TestCase):
    """Every caller keeps its contract: the forms read before are read the same way."""

    def setUp(self):
        common.take_date_notes()

    def test_forms_read_before(self):
        for text, want in {"2026-10-05": ("2026-10-05", ""), "2026.10.05 x": ("2026-10-05", "x"),
                           "IMG_20261017_183316": ("2026-10-17", "IMG_ _183316"),
                           "10-26-2026 Taller en Tyler": ("2026-10-26", "Taller en Tyler"),
                           "October 17, 2026 at 7 PM": ("2026-10-17", "at 7 PM"),
                           "17 de octubre de 2026 a las 7 pm": ("2026-10-17", "a las 7 pm"),
                           "March 2026 Committee Meeting": ("2026-03-01", "Committee Meeting"),
                           "Enero 29, 2027": ("2027-01-29", ""), "no date here": (None, "no date here")}.items():
            self.assertEqual(common.date_from_text(text), want, text)

    def test_drive_flyers_and_names(self):
        self.assertEqual(D.name_date("Taller 05-10-2026"), ("2026-10-05", "Taller", True))

        def flyer(n: int, name: str) -> dict:
            e = D.Entry(id=f"file{n}", name=name, mime="application/pdf", modified="2026-09-24")
            return D.build_item(D.Found(e, D.Panel(77, "Panel 77", "p77", "P77"), ["flyers"], ["root", "p77", "fl"],
                                        seq=n), {})
        got = [flyer(n, name)["extra"] for n, name in enumerate(
            ["Taller 05-10-2026 @ Tyler, TX.pdf", "14-03-2027 Workshop.pdf", "Assembly March 14 - 16, 2027.pdf",
             "Report 05-10-2026.pdf"], 1)]
        self.assertEqual([(x.get("event_date"), x.get("event_title")) for x in got],
                         [("2026-10-05", "Taller"), ("2027-03-14", "Workshop"), ("2027-03-14", "Assembly"),
                          ("2026-05-10", "Report")])
        # drive.main puts these lines in its stats["warnings"] (→ /status/)
        self.assertEqual(len(common.take_date_notes()), 1)

    def test_booth_until_and_from(self):
        from scripts.sync import booth_names as BN
        self.assertEqual(BN._day("14-03-2027", False), "2027-03-14")
        self.assertEqual(BN._day("March 2027", True), "2027-03-31")


class SiteDay(unittest.TestCase):
    """P3-9: a UTC time read after about 7 PM Central is still that evening's day on the site."""

    def test_central_days(self):
        self.assertEqual(common.site_day("2026-10-06T01:00:00Z"), "2026-10-05")          # 8:00 PM CDT
        self.assertEqual(common.site_day("2026-10-06T04:59:59Z"), "2026-10-05")
        self.assertEqual(common.site_day("2026-10-06T05:00:00Z"), "2026-10-06")
        self.assertEqual(common.site_day("2027-01-10T05:30:00Z"), "2027-01-09")          # 11:30 PM CST
        self.assertEqual(common.site_day("2026-10-05T23:59:00-05:00"), "2026-10-05")
        self.assertEqual(common.site_day("2026-10-06T01:00:00"), "2026-10-05")            # no zone: UTC
        self.assertEqual(common.site_day(datetime(2026, 10, 6, 1, tzinfo=timezone.utc)), "2026-10-05")
        self.assertEqual(common.site_day("2026-10-05"), "2026-10-05")                     # a day is that day
        self.assertEqual(common.site_day(None), datetime.now(CHI).date().isoformat())

    def test_bulletin_post_first_seen_in_the_evening(self):
        prev = [{"id": "ann:old", "title": "Old", "date": None, "first_seen": "2026-10-06T01:00:00Z",
                 "last_seen": "2026-10-06T01:00:00Z", "extra": {"file": "content/bulletin/old.md"}}]
        new = [{"id": "ann:old", "title": "Old", "date": None, "extra": {"file": "content/bulletin/old.md"}},
               {"id": "ann:new", "title": "New", "date": None, "extra": {"file": "content/bulletin/new.md"}}]
        with mock.patch.object(common, "now_iso", return_value="2026-10-06T02:30:00Z"):     # 9:30 PM CDT
            merged, added = A.finalize(prev, new)
        self.assertEqual(added, 1)
        self.assertEqual({i["id"]: i["date"] for i in merged}, {"ann:old": "2026-10-05", "ann:new": "2026-10-05"})


class EventFiles(unittest.TestCase):
    """P3-4: content/events start / end must be whole dates; a written UTC offset is checked against Central."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-test-"))
        self.raw, self.evs, self.ann = self.tmp / "raw", self.tmp / "events", self.tmp / "bulletin"
        for d in (self.raw, self.evs, self.ann):
            d.mkdir()
        for target, name, value in ((common, "RAW_DIR", self.raw), (A, "EVENTS_DIR", self.evs),
                                    (A, "ANN_DIR", self.ann), (A, "LEGACY_ANN_DIR", self.tmp / "none")):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, name: str, head: str, folder: Path | None = None, body: str = "An event.") -> None:
        (folder or self.evs).joinpath(name).write_text(f"---\ntitle: X\n{head}---\n{body}\n", encoding="utf-8")

    def run_main(self, source: str = "manual_events") -> dict:
        A.main([])
        return json.loads((self.raw / f"{source}.json").read_text(encoding="utf-8"))

    def test_a_date_without_its_year_is_left_out_and_listed(self):
        self.write("workshop.md", "start: January 10\n")
        self.write("taller.md", "start: 10 de enero\nlang: es\n")
        self.write("supper.md", "start: 2027-01-10T18:00:00-06:00\nend: January 12\n")
        self.write("good.md", "start: 2027-01-10T18:00:00-06:00\nend: 2027-01-10T20:00:00-06:00\n")
        env = self.run_main()
        self.assertEqual([i["extra"]["slug"] for i in env["items"]], ["good"])
        errors = env["stats"]["errors"]
        self.assertEqual(env["stats"]["warnings"], errors)                  # → /status/
        text = " ".join(errors)
        self.assertIn("events/workshop.md: start: “January 10” has no year — the event is left out until it does: "
                      "write the whole date (start: ", text)
        self.assertIn("events/taller.md: start: “10 de enero” has no year", text)
        self.assertIn("events/supper.md: end: “January 12” has no year", text)
        self.assertEqual(env["stats"]["problems"], 3)
        self.assertTrue(env["ok"])

    def test_a_time_alone_is_not_a_start(self):
        self.write("unquoted.md", "start: 19:00\n")                  # YAML: the number 1140 (once "the year 1140")
        self.write("quoted.md", 'start: "19:00"\n')
        self.write("month.md", "start: March 2027\n")
        self.write("weekday.md", "start: Saturday\n")
        env = self.run_main()
        self.assertEqual(env["items"], [])
        text = " ".join(env["stats"]["errors"])
        self.assertIn("unquoted.md: start: 19:00 is a time of day without its date — write both: "
                      "start: 2027-03-14T19:00:00-05:00", text)
        self.assertIn("quoted.md: start: “19:00” has no date", text)
        self.assertIn("month.md: start: “March 2027” has no day", text)
        self.assertIn("weekday.md: start: “Saturday” has no date", text)

    def test_an_offset_that_is_not_centrals(self):
        self.write("winter.md", "start: 2027-01-10T19:00:00-05:00\nend: 2027-01-10T21:00:00-05:00\n")
        self.write("summer.md", "start: 2027-06-10T19:00:00-05:00\n")
        self.write("utc.md", 'start: "2027-06-11T00:00:00Z"\n')
        env = self.run_main()
        starts = {i["extra"]["slug"]: i["extra"]["start"] for i in env["items"]}
        self.assertEqual(starts, {"winter": "2027-01-11T00:00:00Z", "summer": "2027-06-11T00:00:00Z",
                                  "utc": "2027-06-11T00:00:00Z"})       # still shown, at the moment written
        errors = env["stats"]["errors"]
        self.assertEqual(len(errors), 3)                                     # winter start + end, utc
        self.assertIn("events/winter.md: start: 2027-01-10T19:00:00-05:00 — -05:00 is not Central time's UTC offset "
                      "on 2027-01-10 (-06:00), so the event shows at 6:00 PM Central time. If 19:00 is Central "
                      "time, write start: 2027-01-10T19:00:00-06:00", errors)
        self.assertTrue(any(e.startswith("events/winter.md: end: 2027-01-10T21:00:00-05:00") for e in errors))
        self.assertTrue(any(e.startswith("events/utc.md: start: 2027-06-11T00:00:00Z — +00:00 is not") for e in errors))
        self.assertEqual(env["stats"]["warnings"], errors)

    def test_numbers_only_dates_and_a_range_in_the_name(self):
        self.write("taller.md", 'start: "05/10/2027 7 PM"\nlang: es\n')
        self.write("Assembly March 19 - 21, 2027.md", "location: Dallas, TX\n")
        self.write("open-house.md", 'start: "05/10/2027"\n', body="Panel 77.")     # words that do not tell
        env = self.run_main()
        ex = {i["extra"]["slug"]: i["extra"] for i in env["items"]}
        self.assertEqual((ex["taller"]["start"], ex["taller"]["all_day"]), ("2027-10-06T00:00:00Z", False))
        asm = ex["assembly-march-19-21-2027"]
        self.assertEqual((asm["start"], asm["end"], asm["all_day"]), ("2027-03-19", "2027-03-21", True))
        self.assertEqual(ex["open-house"]["start"], "2027-05-10")            # month first, as before …
        self.assertIn("events/open-house.md: “05/10/2027” could be May 10 or October 5, 2027",
                      " ".join(env["stats"]["errors"]))                       # … and the chair is told

    def test_the_last_good_version_stays(self):
        self.write("workshop.md", "start: 2027-01-10\n")
        first = self.run_main()["items"][0]
        self.write("workshop.md", "start: January 10\n")
        env = self.run_main()
        self.assertEqual([(i["id"], i["extra"]["start"]) for i in env["items"]], [(first["id"], "2027-01-10")])
        self.assertEqual(env["stats"]["problems"], 1)

    def test_a_clean_folder_has_no_warnings(self):
        self.write("good.md", "start: 2027-03-19\nend: 2027-03-21\n")
        self.write("2027-01-10-welcome.md", "", self.ann)
        env = self.run_main()
        self.assertNotIn("warnings", env["stats"])
        self.assertNotIn("warnings", json.loads((self.raw / "announcements.json").read_text(encoding="utf-8"))["stats"])

    def test_as_when_directly(self):
        with self.assertRaisesRegex(ValueError, "start: 19:00 is a time of day"):
            A.as_when(1140, CHI)
        with self.assertRaisesRegex(ValueError, "no year"):
            A.as_when("Jan. 10th", CHI)
        with self.assertRaisesRegex(ValueError, "end: 1140 is not a date"):
            A.as_when("1140", CHI, field="end")
        self.assertEqual(A.as_when("to be announced", CHI), (None, False))
        self.assertEqual(A.as_when("March 14, 2027", CHI), ("2027-03-14", True))
        notes: list[str] = []
        self.assertEqual(A.as_when("2027-03-14T19:00:00-05:00", CHI, notes), ("2027-03-15T00:00:00Z", False))
        self.assertEqual(notes, [])                                  # March 14, 2027 7 PM: CDT (-05:00) is right
        self.assertEqual(A.as_when("2026-11-01T01:30:00-06:00", CHI, notes), ("2026-11-01T07:30:00Z", False))
        self.assertEqual(notes, [])                                  # the second 1:30 of the night the clocks go back


class BulletinDates(unittest.TestCase):
    """The bulletin's dates are read the same way: a numbers-only date in a Spanish post is day first."""

    def test_spanish_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bienvenida.md"
            p.write_text("---\ntitle: Bienvenidos\ndate: 05/10/2026\nexpires: 31/12/2026\nlang: es\n---\n"
                         "Bienvenidos, nuevos RLV.\n", encoding="utf-8")
            it = A.parse_announcement(p)
            self.assertEqual((it["date"], it["extra"]["expires"]), ("2026-10-05", "2026-12-31"))
            self.assertNotIn("date_notes", it["extra"])
            p.write_text("---\ntitle: Welcome\ndate: 05/10/2026\n---\nHi.\n", encoding="utf-8")
            it = A.parse_announcement(p)
            self.assertEqual(it["date"], "2026-05-10")
            self.assertEqual(len(it["extra"]["date_notes"]), 1)


if __name__ == "__main__":
    unittest.main()
