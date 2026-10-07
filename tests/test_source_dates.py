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

    def test_the_magazines_names_do_not_make_a_name_spanish(self):
        """ "La Viña" in an English name ("Grapevine & La Viña Pricing Update") says nothing about its language."""
        notes: list[str] = []
        self.assertEqual(common.date_from_text("La Viña Report 05-10-2026", notes=notes), ("2026-05-10", "La Viña Report"))
        self.assertEqual(len(notes), 1)                                        # month first, as before — and noted
        self.assertEqual(common.date_from_text("Grapevine & La Viña order form 05-10-2026")[0], "2026-05-10")
        self.assertEqual(common.date_from_text("Informe de La Viña 05-10-2026")[0], "2026-10-05")    # "de": Spanish
        self.assertEqual(common.date_from_text("Revista La Viña 05-10-2026")[0], "2026-10-05")
        common.take_date_notes()

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
        # a part, a session, a week … counted before a dash: that number, then the day
        self.assertEqual(common.date_range_from_text("Session 2 - 4 March 2027"), ("2027-03-04", None, "Session 2"))
        self.assertEqual(common.date_range_from_text("Parte 1 - 3 de marzo de 2027"), ("2027-03-03", None, "Parte 1"))
        self.assertEqual(common.date_range_from_text("Semana 1 al 7 de marzo de 2027")[:2], ("2027-03-01", "2027-03-07"))


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

    def test_drive_run_names_the_file_of_each_note(self):
        """drive.main: each name whose date could be read two ways is one line of its stats["warnings"] (→ /status/)
        with the file's folders and name — also an "(until …)" date, whose own note quotes only the date; a note
        left by an earlier module of the same run is not the Drive source's."""
        from scripts.sync.drive_listing import FOLDER_MIME, Entry, Listing

        def pdf(fid: str, name: str) -> Entry:
            return Entry(fid, name, "application/pdf", modified_text="Sep 28", modified="2026-09-28")
        tree = {"ROOT": [Entry("P77", "2027-2028_Panel77_GVLV", FOLDER_MIME, is_folder=True)],
                "P77": [Entry("FL", "flyers", FOLDER_MIME, is_folder=True)],
                "FL": [pdf("f1", "Report 05-10-2026.pdf"), pdf("f2", "Workshop (until 05-11-2026).pdf"),
                       pdf("f3", "Taller 05-10-2026.pdf"), pdf("f4", "2026-10-17 Assembly.pdf")]}

        class Lister:
            mode, api_error, requests_made = "html", None, 0

            class html:
                shortcuts_resolved = 0

            def __init__(self, **kw):
                self.http = None

            def list(self, fid):
                return Listing(True, [Entry(**vars(e)) for e in tree[fid]])
        cfg = {"drive": {"root_folder_id": "ROOT", "min_panel": 77}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(common, "RAW_DIR", Path(tmp)), \
                mock.patch.object(D, "DriveLister", Lister), mock.patch.object(D, "load_config", lambda: cfg):
            common.date_from_text("Minutes 05-10-2026")          # an earlier module's
            D.main([])
            env = json.loads((Path(tmp) / "drive.json").read_text(encoding="utf-8"))
        notes = sorted(w for w in env["stats"]["warnings"] if "could be" in w)
        self.assertEqual(len(notes), 2, notes)
        self.assertTrue(notes[0].startswith("2027-2028_Panel77_GVLV/flyers/Report 05-10-2026.pdf: “Report 05-10-2026”: "
                                            "“05-10-2026” could be May 10 or October 5, 2026"), notes)
        self.assertTrue(notes[1].startswith("2027-2028_Panel77_GVLV/flyers/Workshop (until 05-11-2026).pdf: "
                                            "“05-11-2026” could be May 11 or November 5, 2026"), notes)
        self.assertEqual(common.take_date_notes(), [])


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

    def test_a_range_written_in_start(self):
        """ "start: March 19 - 21, 2027" is those three days (dateutil alone read it as 8:27 PM in 2016); a range
        without its year, or a year in two digits, is left out like any date without its year."""
        self.write("assembly.md", "start: March 19 - 21, 2027\n")
        self.write("taller.md", "start: del 14 al 16 de mayo de 2027\nlang: es\n")
        self.write("convention.md", "start: March 30 - April 2, 2027\nend: 2027-04-03\n")    # end: as written
        self.write("short.md", "start: March 19 - 21\n")
        self.write("twodigit.md", 'start: "3/19/27"\n')
        env = self.run_main()
        ex = {i["extra"]["slug"]: i["extra"] for i in env["items"]}
        self.assertEqual(set(ex), {"assembly", "taller", "convention"})
        self.assertEqual((ex["assembly"]["start"], ex["assembly"]["end"], ex["assembly"]["all_day"]),
                         ("2027-03-19", "2027-03-21", True))
        self.assertEqual((ex["taller"]["start"], ex["taller"]["end"]), ("2027-05-14", "2027-05-16"))
        self.assertEqual((ex["convention"]["start"], ex["convention"]["end"]), ("2027-03-30", "2027-04-03"))
        text = " ".join(env["stats"]["errors"])
        self.assertIn("events/short.md: start: “March 19 - 21” has no year", text)
        self.assertIn("events/twodigit.md: start: “3/19/27” has no year written in full — the event is left out "
                      "until it does: write the whole date (start: ", text)

    def test_a_date_in_the_name_that_is_not_used_is_not_noted(self):
        self.write("report-05-10-2027.md", "start: 2027-10-05\n", body="Panel 77.")     # start: decides
        self.write("open-house-05-10-2027.md", "", body="Panel 77.")                     # the name decides
        env = self.run_main()
        self.assertEqual(len(env["items"]), 2)
        self.assertEqual(len(env["stats"]["errors"]), 1)
        self.assertIn("events/open-house-05-10-2027.md: “open-house-05-10-2027”: “05-10-2027” could be May 10",
                      env["stats"]["errors"][0])

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
        with self.assertRaisesRegex(ValueError, r"start: “2027” has no day — write the whole date \(start: 2027-MM-DD\)"):
            A.as_when("2027", CHI)
        self.assertEqual(A.as_when("to be announced", CHI), (None, False))
        self.assertEqual(A.as_when("March 14, 2027", CHI), ("2027-03-14", True))
        self.assertEqual(A.as_when("14 - 16 March 2027", CHI), ("2027-03-14", True))             # was 2014
        self.assertEqual(A.as_when("2027-03-14 - 2027-03-16", CHI), ("2027-03-14", True))
        notes: list[str] = []
        self.assertEqual(A.as_when("2027-03-14T19:00:00-05:00", CHI, notes), ("2027-03-15T00:00:00Z", False))
        self.assertEqual(notes, [])                                  # March 14, 2027 7 PM: CDT (-05:00) is right
        self.assertEqual(A.as_when("2026-11-01T01:30:00-06:00", CHI, notes), ("2026-11-01T07:30:00Z", False))
        self.assertEqual(notes, [])                                  # the second 1:30 of the night the clocks go back


class NamesThatAreNotSpanish(unittest.TestCase):
    """Review of round 7: an English Drive name was read day first, silently, when it carried the documented zone
    letters ET / EST ("et" / "est" are French words, and French read the day first) or named a Spanish-named group or
    town ("@ Grupo Solo por Hoy", "- Grupo Progreso Latino, Duncanville", "El Paso"). Only the words of the name's
    own title count now, and only when they clearly tell; English stays month first."""

    def setUp(self):
        common.take_date_notes()

    def read(self, name: str) -> tuple[str | None, int]:
        got = common.date_from_text(name)[0]
        return got, len(common.take_date_notes())

    def test_english_flyer_names_stay_month_first(self):
        for name, want in {
                "03-04-2027 GV Workshop 7pm ET on Zoom": "2027-03-04",
                "03-04-2027 Grapevine Writing Workshop 7pm EST @ Zoom": "2027-03-04",
                "03-04-2027 Writing Workshop 7pm ET @ Tyler Civic Center": "2027-03-04",
                "LV Writing Workshop 03-04-2027 7pm @ Grupo Solo por Hoy": "2027-03-04",
                "Grapevine Writing Workshop 10-03-2026 - Grupo Progreso Latino, Duncanville": "2026-10-03",
                "11-07-2026 Grapevine Writing Workshop 9-11am @ Grupo Libro Grande, Tyler": "2026-11-07",
                "Writing Workshop 03-04-2027 - Grupo Los Amigos de la Calle": "2027-03-04",
                "Writing Workshop 03-04-2027 El Paso": "2027-03-04",
                "03-04-2027 Writing Workshop 7pm CT @ Primary Purpose Group, Arlington": "2027-03-04"}.items():
            with self.subTest(name=name):
                self.assertEqual(self.read(name), (want, 0))

    def test_a_name_whose_own_words_do_not_tell_is_noted(self):
        for name in ("Workshop 03-04-2027 7pm ET", "Workshop 03-04-2027 El Paso", "Panel 77 - 03-04-2027 - Grupo X",
                     "Anniversary 03-04-2027 Grupo Nueva Vida"):
            with self.subTest(name=name):
                self.assertEqual(self.read(name), ("2027-03-04", 1))     # month first, as in the US — and said

    def test_spanish_names_stay_day_first(self):
        for name in ("Taller 05-10-2026", "Taller 05-10-2026 - Grupo Solo por Hoy", "05-10-2026 - Taller de escritura",
                     "Taller de escritura 05-10-2026 12 p. m. hora del Este", "Grupo de Escritura 05-10-2026",
                     "05-10-2026 Grupo Solo por Hoy, Aniversario", "Reunión de La Junta 05-10-2026",
                     "Informe de La Viña 05-10-2026",
                     # (check of the fix: a Spanish name whose only Spanish word but the group's name is what the
                     # event is — read month first, with a note, once the group's name was left out)
                     "Aniversario 05-10-2026 - Grupo Nueva Vida", "Aniversario Grupo Nueva Vida 05-10-2026",
                     "Asamblea 05-10-2026", "Retiro espiritual 05-10-2026", "Sábado 05-10-2026 Taller"):
            with self.subTest(name=name):
                self.assertEqual(self.read(name), ("2026-10-05", 0))

    def test_french_is_not_a_day_first_language(self):
        self.assertEqual(common.date_from_text("Réunion 05-10-2026", lang="fr")[0], "2026-05-10")
        self.assertEqual(len(common.take_date_notes()), 1)

    def test_drive_flyers(self):
        def flyer(n: int, name: str) -> dict:
            e = D.Entry(id=f"f{n}", name=name, mime="application/pdf", modified="2026-09-24")
            return D.build_item(D.Found(e, D.Panel(77, "Panel 77", "p77", "P77"), ["flyers"], ["root", "p77", "fl"],
                                        seq=n), {})["extra"]
        got = [flyer(n, name) for n, name in enumerate(
            ["03-04-2027 GV Workshop 7pm ET on Zoom.pdf", "LV Writing Workshop 03-04-2027 7pm @ Grupo Solo por Hoy.jpg",
             "Grapevine Writing Workshop 10-03-2026 - Grupo Progreso Latino, Duncanville.png",
             "Taller de escritura 05-03-2027 7pm @ Grupo Solo por Hoy.pdf"], 1)]
        self.assertEqual([x["event_date"] for x in got], ["2027-03-04", "2027-03-04", "2026-10-03", "2027-03-05"])
        self.assertEqual((got[0]["event_time"], got[0]["event_tz"]), ("19:00", "America/New_York"))
        self.assertEqual(common.take_date_notes(), [])


class YearMonthDay(unittest.TestCase):
    """Review of round 7: "October 17, 2026 7-9 PM" was read as July 9 — the year-month-day pattern took a
    different mark in each place ("2026 7-9"). The same mark twice now ("2027-03-14", "2027 03 14", "2027_03_14")."""

    def test_a_time_after_a_year_written_in_words(self):
        cases = {"October 17, 2026 7-9 PM Writing Workshop": ("2026-10-17", "7-9 PM Writing Workshop"),
                 "Writing Workshop March 14, 2027 9-11am @ Tyler, TX": ("2027-03-14", "Writing Workshop 9-11am @ Tyler, TX"),
                 "14 de marzo de 2027 10-12 Taller": ("2027-03-14", "10-12 Taller"),
                 "March 14 2027 6.30 PM Booth": ("2027-03-14", "6.30 PM Booth"),
                 "March 14 2027 6 30 PM Booth": ("2027-03-14", "6 30 PM Booth"),
                 "October 17, 2026 1-2 PM": ("2026-10-17", "1-2 PM")}
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(common.date_from_text(text), want)

    def test_the_forms_that_are_one_date(self):
        for text, want in {"2027 03 14 Assembly": "2027-03-14", "2027-3-4 x": "2027-03-04", "2027.03.14": "2027-03-14",
                           "2027_03_14": "2027-03-14", "IMG_2026_10_17": "2026-10-17", "2026-10-17 7pm": "2026-10-17",
                           "2027-03-14 - 2027-03-16 Assembly": "2027-03-14"}.items():
            with self.subTest(text=text):
                self.assertEqual(common.date_from_text(text)[0], want)
        self.assertEqual(common.date_range_from_text("2027-03-14 - 2027-03-16 Assembly")[1], "2027-03-16")
        # a mark of each kind is not one date: the name's real date is found
        self.assertEqual(common.date_from_text("2026-10-01 Pricing Update - Effective January 1, 2027")[0], "2026-10-01")

    def test_a_flyer_and_an_event_file(self):
        e = D.Entry(id="f1", name="October 17, 2026 7-9 PM Writing Workshop.jpg", mime="image/jpeg", modified="2026-09-24")
        x = D.build_item(D.Found(e, D.Panel(77, "Panel 77", "p77", "P77"), ["flyers"], ["root", "p77", "fl"], seq=1),
                         {})["extra"]
        self.assertEqual((x["event_date"], x["event_time"], x["event_end_time"], x["event_title"]),
                         ("2026-10-17", "19:00", "21:00", "Writing Workshop"))
        self.assertEqual(A.as_when("Mar 14, 2027 7-9 PM", CHI), ("2027-03-14", True))     # a range of hours: all day
        self.assertEqual(A.as_when("14 de marzo de 2027 7-9 pm", CHI, lang="es"), ("2027-03-14", True))


class MonthWithoutItsDay(unittest.TestCase):
    """Review of round 7: start: "marzo de 2027" became March 1 — "no day: left out" held for English only."""

    def test_spanish_month_and_year_raise(self):
        for v in ("marzo de 2027", "Enero de 2027", "marzo 2027", "marzo del 2027 a las 7 pm", "Marzo de 2027 19:00"):
            for lang in ("es", None):
                with self.subTest(v=v, lang=lang), self.assertRaisesRegex(ValueError, "has no day — write the whole date"):
                    A.as_when(v, CHI, [], lang)

    def test_the_first_written_as_a_spanish_ordinal_is_a_day(self):
        for v in ("1° de marzo de 2027", "1º de marzo de 2027", "1.º de marzo de 2027", "1ro de marzo de 2027",
                  "primero de marzo de 2027"):
            with self.subTest(v=v):
                self.assertEqual(A.as_when(v, CHI, [], "es"), ("2027-03-01", True))
                self.assertIs(common.date_has_day(v), True)
        self.assertEqual(A.as_when("sábado 1° de marzo de 2027, 7 p. m.", CHI, [], "es"), ("2027-03-02T01:00:00Z", False))
        self.assertEqual(A.as_when("14 de marzo de 2027", CHI, [], "es"), ("2027-03-14", True))
        self.assertEqual(common.date_from_text("2nd March 2027")[0], "2027-03-02")
        self.assertIs(common.date_has_day("marzo de 2027"), False)
        self.assertIsNone(common.date_has_day("no date"))

    def test_an_event_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "taller.md"
            p.write_text("---\ntitle: Taller\nstart: marzo de 2027\nlang: es\n---\nUn taller.\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "has no day"):
                A.parse_event(p, CHI)

    def test_drive_names(self):
        self.assertEqual(D.name_date("Taller 1° de marzo de 2027"), ("2027-03-01", "Taller", True))
        self.assertEqual(D.name_date("Taller marzo de 2027")[2], False)


class UntilAndFromInSpanish(unittest.TestCase):
    """Review of round 7: "(hasta 05-11-2026)" / "(desde …)" in a Drive or booth name was read month first while the
    name's own date was read day first — a Spanish post hidden at once, or put up early."""

    def setUp(self):
        common.take_date_notes()

    def post(self, name: str) -> dict:
        e = D.Entry(id="a1", name=name, mime="application/pdf", modified="2026-10-01")
        return D.build_item(D.Found(e, D.Panel(77, "Panel 77", "p77", "P77"), ["Anuncios"], ["root", "p77", "an"],
                                    seq=1), {})

    def test_bulletin_files(self):
        it = self.post("Aviso de la junta (hasta 05-11-2026).pdf")
        self.assertEqual((it["kind"], it["extra"]["expires"]), ("announcement", "2026-11-05"))
        it = self.post("Taller de escritura 03-10-2026 (hasta 05-11-2026).pdf")
        self.assertEqual((it["date"], it["extra"]["expires"]), ("2026-10-03", "2026-11-05"), "one order in one name")
        self.assertEqual(self.post("Inscripciones (desde 05-11-2026).pdf")["extra"]["publish"], "2026-11-05")
        self.assertEqual(self.post("Aviso (vence 01/02/2027).pdf")["extra"]["expires"], "2027-02-01")
        self.assertEqual(common.take_date_notes(), [])
        # an English word leaves the date to itself: month first, and said
        self.assertEqual(self.post("Workshop (until 05-11-2026).pdf")["extra"]["expires"], "2026-05-11")
        self.assertEqual(len(common.take_date_notes()), 1)
        self.assertEqual(self.post("Aviso (hasta 2027-03-15).pdf")["extra"]["expires"], "2027-03-15")

    def test_booth_files(self):
        from scripts.sync import booth_names as BN
        self.assertEqual(BN.parse_booth_name("LV ES Taller (hasta 05-11-2026).png", "image/png", ["booth"])["until"],
                         "2026-11-05")
        self.assertEqual(BN.parse_booth_name("LV ES Taller (desde 05-11-2026).png", "image/png", ["booth"])["from"],
                         "2026-11-05")
        self.assertEqual(BN.parse_booth_name("LV ES Taller (a partir de 05-11-2026).png", "image/png", ["booth"])["from"],
                         "2026-11-05")
        self.assertEqual(common.take_date_notes(), [])
        self.assertEqual(BN.parse_booth_name("GV EN Workshop (until 05-11-2026).png", "image/png", ["booth"])["until"],
                         "2026-05-11")
        self.assertEqual(len(common.take_date_notes()), 1)


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

    def test_a_date_in_the_name_is_noted_only_when_it_is_the_one_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Report 05-10-2026.md"
            p.write_text("---\ntitle: Report\ndate: 2026-10-05\n---\nHi.\n", encoding="utf-8")
            it = A.parse_announcement(p)
            self.assertEqual(it["date"], "2026-10-05")
            self.assertNotIn("date_notes", it["extra"])                     # date: decides
            p.write_text("---\ntitle: Report\n---\nHi.\n", encoding="utf-8")
            it = A.parse_announcement(p)
            self.assertEqual(it["date"], "2026-05-10")
            self.assertEqual(len(it["extra"]["date_notes"]), 1)              # the name decides: said


if __name__ == "__main__":
    unittest.main()
