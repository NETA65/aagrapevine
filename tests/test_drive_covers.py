"""The magazines' front covers on the committee's Drive (round 29) — scripts/sync/drive.py cover_of and its use, from
the Drive listing to the site's data (no network: the Drive tree is faked, data/raw is a temporary folder):

  * Names       — the cover pattern (Grapevine's month, La Viña's bimonthly ISSUE → its two months, .png / .JPG,
                  a month word that disagrees, La Viña's NN of 07–12 and its month words deciding, a name that cannot
                  be read in a covers folder with a year folder, a year that is not its year folder's, a cover's name
                  outside a covers folder — only with nothing but month words after the number: an event's photo
                  named "GV_2026-11-28_workshop.jpg" stays in its album —, folders that only look like one) and the
                  labels in both languages.
  * ListingDays — drive.plausible_day: what Drive's listing says about a file's day is believed only between 2000
                  and a day after today (the "12/31/79" zip stamp, a camera's 1970), for every Drive file.
  * Items       — drive.build_item: a cover's extra.cover, date, lang, title and album; a loose photo and an ordinary
                  album photo exactly as before.
  * WholeRun    — drive.main on a fake tree: photos/AAGrapevine_covers/2026/{GV_2026-11_November.jpg, _index.csv},
                  photos/AALavina_covers/2026/LaVina_2026-06_Noviembre-Diciembre.png and a loose photo, every cover
                  listed as "12/31/79": the dates come from the names, the owner's _index.csv is left out and never
                  named anywhere, the loose photo is unchanged, a 2079 date an earlier run stored is replaced (also
                  on a row kept unread), the stats count the covers and two files of one issue (never naming one).
  * SiteData    — build_data: the covers' i18n written by rule (title + album, EN + ES, `machine` []) and nothing
                  about a cover asked of the translator; "New" only for a recent issue.
  * HomeUploads — Home's "Committee uploads" (eleventy/filters/home.js homeDrive) never shows a cover.

    python -m unittest tests.test_drive_covers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import drive as D  # noqa: E402
from scripts.sync.drive_listing import FOLDER_MIME, Entry, Listing, local_today  # noqa: E402

PANEL = D.Panel(77, "Panel 77 (2027–2028)", "P77", "2027-2028_Panel77_GVLV")
GV_DIR = ["photos", "AAGrapevine_covers", "2026"]
LV_DIR = ["photos", "AALavina_covers", "2026"]


def cover(path: list[str], name: str) -> tuple[dict | None, str | None]:
    return D.cover_of("photos", "photo", path, name)


def built(path: list[str], name: str, mime: str = "image/jpeg", **entry) -> dict:
    e = Entry(entry.pop("fid", "f-" + name), name, mime, **entry)
    return D.build_item(D.Found(e, PANEL, list(path), ["ROOT", "P77"] + [f"F{i}" for i in range(len(path))], seq=1), {})


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


# =========================================================================== the names
class Names(unittest.TestCase):
    def test_the_parsing_table(self):
        # (folders, name) → (pub, year, month, issue, months, key, note)
        table = [
            # the owner's two patterns, as named in Drive
            (GV_DIR, "GV_2026-11_November.jpg", ("gv", 2026, 11, None, [11], "2026-11", None)),
            (["photos", "AAGrapevine_covers", "2015"], "GV_2015-07_July.jpg", ("gv", 2015, 7, None, [7], "2015-07", None)),
            (LV_DIR, "LaVina_2026-06_Noviembre-Diciembre.jpg", ("lv", 2026, None, 6, [11, 12], "2026-11", None)),
            (LV_DIR, "LaVina_2026-01_Enero-Febrero.jpg", ("lv", 2026, None, 1, [1, 2], "2026-01", None)),
            # La Viña's NN is the ISSUE: 03 = May–June (the owner's two .png files)
            (["photos", "AALavina_covers", "2022"], "LaVina_2022-03_Mayo-Junio.png", ("lv", 2022, None, 3, [5, 6], "2022-05", None)),
            (["photos", "AALavina_covers", "2022"], "LaVina_2022-04_Julio-Agosto.png", ("lv", 2022, None, 4, [7, 8], "2022-07", None)),
            # any case, other separators, other picture types
            (GV_DIR, "gv 2026-10 october.JPG", ("gv", 2026, 10, None, [10], "2026-10", None)),
            (GV_DIR, "Grapevine-2026-9-September.jpeg", ("gv", 2026, 9, None, [9], "2026-09", None)),
            (LV_DIR, "La_Vina_2026_05_Septiembre-Octubre.webp", ("lv", 2026, None, 5, [9, 10], "2026-09", None)),
            (LV_DIR, "La Viña 2026-04.heic", ("lv", 2026, None, 4, [7, 8], "2026-07", None)),
            (GV_DIR, "GV_2026-11_November (1).jpg", ("gv", 2026, 11, None, [11], "2026-11", None)),
            # a month word that disagrees: Grapevine's number wins (counted as a correction)
            (GV_DIR, "GV_2026-11_October.jpg", ("gv", 2026, 11, None, [11], "2026-11", "fixed")),
            (LV_DIR, "LaVina_2026-06_Julio-Agosto.jpg", ("lv", 2026, None, 6, [11, 12], "2026-11", "fixed")),
            # Grapevine with an impossible number: its month word decides
            (GV_DIR, "GV_2026-13_March.jpg", ("gv", 2026, 3, None, [3], "2026-03", "fixed")),
            # La Viña's NN of 07–12: the month words decide, else the number is read as a month (rounded up)
            (LV_DIR, "LaVina_2026-11_Noviembre-Diciembre.jpg", ("lv", 2026, None, 6, [11, 12], "2026-11", "fixed")),
            (LV_DIR, "LaVina_2026-08_Julio-Agosto.jpg", ("lv", 2026, None, 4, [7, 8], "2026-07", "fixed")),
            (LV_DIR, "LaVina_2026-11.jpg", ("lv", 2026, None, 6, [11, 12], "2026-11", "fixed")),
            (LV_DIR, "LaVina_2026-07_x.jpg", ("lv", 2026, None, 4, [7, 8], "2026-07", "fixed")),
            # the words decide when NN is outside 1–12 too
            (LV_DIR, "LaVina_2026-00_Marzo-Abril.jpg", ("lv", 2026, None, 2, [3, 4], "2026-03", "fixed")),
            # a name that cannot be read, in a covers folder: still a cover of that folder's magazine, its year from
            # the nearest year folder (else a year in its name), no month
            (["photos", "AAGrapevine_covers", "2019"], "scan 3.jpg", ("gv", 2019, None, None, [], "", "unrecognized")),
            (["photos", "AALavina_covers"], "Portada de 2018.jpg", ("lv", 2018, None, None, [], "", "unrecognized")),
            (["photos", "AALavina_covers"], "portada.jpg", ("lv", None, None, None, [], "", "unrecognized")),
            (GV_DIR, "GV_3026-11_November.jpg", ("gv", 2026, None, None, [], "", "unrecognized")),   # a typo'd year
            (GV_DIR, "GV_2026-00.jpg", ("gv", 2026, None, None, [], "", "unrecognized")),
            # a covers folder that does not name the magazine: another folder of the path does
            (["photos", "Covers", "La Viña", "2020"], "x.jpg", ("lv", 2020, None, None, [], "", "unrecognized")),
            # a cover's name and nothing else (month words at most) OUTSIDE a covers folder: a cover wherever it sits
            # under photos/
            (["photos", "Fall Assembly 2026"], "GV_2020-02_February.jpg", ("gv", 2020, 2, None, [2], "2020-02", None)),
            (["photos"], "LaVina_2024-03_Mayo-Junio.jpg", ("lv", 2024, None, 3, [5, 6], "2024-05", None)),
            (["photos", "Garland workshop"], "GV_2026-11_November.jpg", ("gv", 2026, 11, None, [11], "2026-11", None)),
            (["photos"], "GV 2026-11.jpg", ("gv", 2026, 11, None, [11], "2026-11", None)),
            (["photos", "Fall Assembly 2026"], "la viña 2026-06 noviembre diciembre.JPG", ("lv", 2026, None, 6, [11, 12], "2026-11", None)),
            # inside a covers folder the reading stays tolerant: other words and numbers after the number
            (GV_DIR, "GV_2026-11-28_workshop.jpg", ("gv", 2026, 11, None, [11], "2026-11", None)),
            # the other magazine's name in a covers folder: the file's own name wins (counted)
            (LV_DIR, "GV_2026-01_January.jpg", ("gv", 2026, 1, None, [1], "2026-01", "fixed")),
            # a name whose year is not its year folder's: the name's year wins (counted)
            (["photos", "AALavina_covers", "2019"], "LaVina_2020-03_Mayo-Junio.jpg", ("lv", 2020, None, 3, [5, 6], "2020-05", "fixed")),
            (["photos", "AAGrapevine_covers", "2026"], "GV_2025-12_December.jpg", ("gv", 2025, 12, None, [12], "2025-12", "fixed")),
        ]
        for path, name, want in table:
            with self.subTest(name=name, path="/".join(path)):
                c, note = cover(path, name)
                self.assertIsNotNone(c)
                self.assertEqual((c["pub"], c["year"], c["month"], c["issue"], c["months"], c["key"], note), want)
                self.assertEqual(sorted(c), ["issue", "key", "month", "months", "pub", "year"])   # exactly the contract

    def test_what_is_not_a_cover(self):
        for path, name in [(["photos"], "2026 Dallas Gathering Of Eagles.jpg"),           # the 2 loose photos
                           (["photos"], "2025 Sales Report.jpg"),
                           (["photos", "Booth at CityWide"], "IMG_1001.jpg"),            # an event album
                           (["photos", "Recovery Workshop 2026"], "IMG_1.jpg"),           # "cover" inside a word
                           (["photos", "Discovering La Viña"], "IMG_2.jpg"),
                           (["photos", "Book covers"], "IMG_3.jpg"),                      # a covers folder of no magazine
                           (["photos", "GVLV 2027"], "GV_2027.jpg"),                      # no month part: not the pattern
                           (["photos"], "GV_2026-11_November.pdf"),                       # not a picture
                           # an event's photo named by its date, the magazine in front (rule b: outside a covers
                           # folder nothing but month words may follow the number) — it stays in its album
                           (["photos", "Garland workshop"], "GV_2026-11-28_workshop.jpg"),
                           (["photos", "Garland workshop"], "LV 2026-12-12 Fort Worth taller.jpg"),
                           (["photos", "Garland workshop"], "Grapevine_2026-10-17_booth.png"),
                           (["photos", "Garland workshop"], "Grapevine 2026 10 booth table.jpg"),
                           (["photos", "Fall Assembly 2026"], "GV 2026-10-17 literature table.jpg"),
                           (["photos", "Fall Assembly 2026"], "Grapevine 2026-10-17 Fall Assembly table.jpg"),
                           (["photos", "2027 Spring Assembly"], "LV 2027-03-14 Spring Assembly booth.jpg"),
                           (["photos"], "LV_2026_10_17 workshop.jpg"),
                           (["photos", "Fall Assembly 2026"], "GV_2026-11_November 2.jpg"),   # a further number
                           (["photos", "Fall Assembly 2026"], "GV_2026-11_November (1).jpg")]:
            with self.subTest(name=name):
                self.assertEqual(cover(path, name), (None, None))
        # …and such a photo is built exactly as an album photo (no cover, its album, its name's date)
        it = built(["photos", "Garland workshop"], "GV_2026-11-28_workshop.jpg", modified="2026-11-28")
        self.assertNotIn("cover", it["extra"])
        self.assertEqual((it["extra"]["album"], it["date"]), ("Garland workshop", "2026-11-28"))
        # only photos in photos/: not a flyer, not a video, not a document
        self.assertEqual(D.cover_of("flyers", "photo", ["flyers"], "GV_2026-11_November.jpg"), (None, None))
        self.assertEqual(D.cover_of("photos", "video_file", GV_DIR, "GV_2026-11_November.mp4"), (None, None))
        self.assertEqual(D.cover_of("photos", "document", GV_DIR, "notes.pdf"), (None, None))
        # odd input never raises
        for odd in ("", ".jpg", "GV_.jpg", "GV_9999-99_.jpg", "LaVina_2026-99_Foo-Bar.jpg", "́.png"):
            D.cover_of("photos", "photo", GV_DIR, odd)

    def test_covers_folders(self):
        for name in ("AAGrapevine_covers", "AALavina_covers", "Covers", "covers", "GV covers", "GV-Covers",
                     "Portadas de La Viña", "AAGrapevineCovers", "LaVinaPortadas", "cover"):
            self.assertTrue(D.is_covers_folder(name), name)
        for name in ("Recovery", "Recovery Workshop 2026", "Discover", "2026", "Booth at CityWide", "Coverage"):
            self.assertFalse(D.is_covers_folder(name), name)

    def test_the_labels_in_both_languages(self):
        gv, _ = cover(GV_DIR, "GV_2026-11_November.jpg")
        lv, _ = cover(LV_DIR, "LaVina_2026-06_Noviembre-Diciembre.jpg")
        self.assertEqual([D.cover_title(gv, "en"), D.cover_title(gv, "es")], ["Grapevine — November 2026", "Grapevine — Noviembre 2026"])
        self.assertEqual([D.cover_title(lv, "en"), D.cover_title(lv, "es")],
                         ["La Viña — November–December 2026", "La Viña — Noviembre–Diciembre 2026"])
        self.assertEqual([D.cover_label(lv, "en"), D.cover_label(gv, "es")], ["November–December 2026", "Noviembre 2026"])
        self.assertEqual([D.cover_album(gv, "en"), D.cover_album(gv, "es"), D.cover_album(lv, "en"), D.cover_album(lv, "es")],
                         ["Grapevine covers 2026", "Portadas de Grapevine 2026", "La Viña covers 2026", "Portadas de La Viña 2026"])
        nothing, _ = cover(["photos", "AALavina_covers"], "portada.jpg")
        self.assertEqual((D.cover_title(nothing, "en"), D.cover_label(nothing, "es")), ("", ""))
        self.assertEqual((D.cover_album(nothing, "en"), D.cover_album(nothing, "es")), ("La Viña covers", "Portadas de La Viña"))
        # the same month names as build_data's issue_label (the site's capitalization)
        from scripts.sync import build_data as B
        self.assertEqual(D.COVER_MONTHS["en"], B.MONTHS_EN)
        self.assertEqual(D.COVER_MONTHS["es"], B.MONTHS_ES)


# =========================================================================== the listing's days
class ListingDays(unittest.TestCase):
    def test_only_a_day_that_can_be_true(self):
        today = date(2026, 11, 13)
        for v, want in [("1979-12-31", None), ("1980-01-01", None), ("2079-12-31", None), ("1999-12-31", None),
                        ("2000-01-01", "2000-01-01"), ("2025-04-13", "2025-04-13"), ("2026-11-14", "2026-11-14"),
                        ("2026-11-15", None), ("2026-11-14T23:00:00Z", "2026-11-14T23:00:00Z"),
                        ("1970-01-01T00:00:00Z", None), (None, None), ("", None)]:
            self.assertEqual(D.plausible_day(v, today), want, v)

    def test_the_folder_views_two_digit_years(self):
        """tests/test_sync_pipeline.py pins the rest of parse_modified_text; here the case of the covers: Drive's
        "12/31/79" is 1979 (then no date at all for drive.py), never 2079."""
        from scripts.sync.drive_listing import parse_modified_text
        today = date(2026, 11, 13)
        self.assertEqual(parse_modified_text("12/31/79", today), "1979-12-31")
        self.assertIsNone(D.plausible_day(parse_modified_text("12/31/79", today), today))
        self.assertEqual(parse_modified_text("4/13/25", today), "2025-04-13")


# =========================================================================== the items
class Items(unittest.TestCase):
    def test_a_grapevine_cover(self):
        it = built(GV_DIR, "GV_2026-11_November.jpg", modified_text="12/31/79", modified="1979-12-31")
        self.assertEqual((it["kind"], it["category"], it["lang"], it["date"]), ("photo", "photos", "en", "2026-11-01"))
        self.assertEqual(it["title"], "Grapevine — November 2026")
        self.assertEqual(it["extra"]["album"], "Grapevine covers 2026")
        self.assertEqual(it["extra"]["cover"], {"pub": "gv", "year": 2026, "month": 11, "issue": None, "months": [11],
                                                "key": "2026-11"})
        self.assertTrue(it["extra"]["thumb_url"].endswith("=w600") and it["extra"]["image_url"].endswith("=w1600"))
        self.assertNotIn("generic_name", it["extra"])
        self.assertNotIn("_cover_note", it)

    def test_a_la_vina_cover_png(self):
        it = built(LV_DIR, "LaVina_2026-06_Noviembre-Diciembre.png", "image/png", modified_text="12/31/79",
                   modified="1979-12-31")
        self.assertEqual((it["lang"], it["date"], it["title"], it["extra"]["album"]),
                         ("es", "2026-11-01", "La Viña — Noviembre–Diciembre 2026", "La Viña covers 2026"))
        self.assertEqual(it["extra"]["cover"]["months"], [11, 12])

    def test_never_the_listing_date_for_a_cover(self):
        # even a date that could be true (an API createdTime, the upload day): the issue's day
        it = built(GV_DIR, "GV_2015-07_July.jpg", created="2026-11-12T20:00:00Z", modified="2026-11-12")
        self.assertEqual(it["date"], "2015-07-01")
        unknown = built(["photos", "AAGrapevine_covers", "2019"], "scan 3.jpg", modified="2026-11-12")
        self.assertEqual((unknown["date"], unknown["title"], unknown["extra"]["album"], unknown["_cover_note"]),
                         ("2019-01-01", "scan 3", "Grapevine covers 2019", "unrecognized"))
        # no year at all: the listing's rules (a plausible day, else merge gives the day the site first had it)
        nothing = built(["photos", "AALavina_covers"], "portada.jpg", modified="2026-11-12")
        self.assertEqual((nothing["date"], nothing["extra"]["album"]), ("2026-11-12", "La Viña covers"))
        self.assertIsNone(built(["photos", "AALavina_covers"], "portada.jpg", modified="1979-12-31")["date"])

    def test_the_loose_photos_and_the_event_albums_are_unchanged(self):
        loose = built(["photos"], "2026 Dallas Gathering Of Eagles.jpg", modified_text="Nov 12", modified="2026-11-12")
        self.assertEqual((loose["title"], loose["date"], loose["extra"]["album"], loose["lang"]),
                         ("2026 Dallas Gathering Of Eagles", "2026-11-12", None, "en"))
        self.assertNotIn("cover", loose["extra"])
        album = built(["photos", "Booth at CityWide"], "IMG_1001.jpg", modified="2026-11-12")
        self.assertEqual((album["extra"]["album"], album["title"], album["extra"].get("generic_name")),
                         ("Booth at CityWide", "Booth at CityWide #1", True))
        self.assertNotIn("cover", album["extra"])
        # a 1979 listing day is no date for any file (merge then dates it the day the site first had it)
        report = built(["reports"], "District report.pdf", "application/pdf", modified_text="12/31/79", modified="1979-12-31")
        self.assertIsNone(report["date"])
        self.assertEqual(report["extra"]["modified_text"], "12/31/79")           # (the listing's own text is kept)


# =========================================================================== a whole run
class WholeRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-covers-"))
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        p = mock.patch.object(common, "RAW_DIR", self.raw)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    TREE = {
        "ROOT": [Entry("P77", "2027-2028_Panel77_GVLV", FOLDER_MIME, is_folder=True)],
        "P77": [Entry("PH", "photos", FOLDER_MIME, is_folder=True), Entry("RE", "reports", FOLDER_MIME, is_folder=True)],
        "PH": [Entry("GVC", "AAGrapevine_covers", FOLDER_MIME, is_folder=True),
               Entry("LVC", "AALavina_covers", FOLDER_MIME, is_folder=True),
               Entry("loose1", "2026 Dallas Gathering Of Eagles.jpg", "image/jpeg", modified_text="Nov 12", modified="2026-11-12")],
        "GVC": [Entry("GV26", "2026", FOLDER_MIME, is_folder=True),
                Entry("csv1", "_index.csv", "text/csv", modified_text="12/31/79", modified="1979-12-31")],
        "GV26": [Entry("gv1", "GV_2026-11_November.jpg", "image/jpeg", modified_text="12/31/79", modified="1979-12-31"),
                 Entry("csv2", "_index.csv", "text/csv", modified_text="12/31/79", modified="1979-12-31")],
        "LVC": [Entry("LV26", "2026", FOLDER_MIME, is_folder=True)],
        "LV26": [Entry("lv1", "LaVina_2026-06_Noviembre-Diciembre.png", "image/png", modified_text="12/31/79",
                       modified="1979-12-31"),
                 Entry("lv2", "portada sin nombre.jpg", "image/jpeg", modified_text="12/31/79", modified="1979-12-31")],
        "RE": [Entry("rep1", "District report.pdf", "application/pdf", modified_text="12/31/79", modified="1979-12-31")],
    }

    def run_main(self) -> tuple[dict, str, list[str]]:
        """drive.main on TREE → (data/raw/drive.json, its text, every line drive.py logged)."""
        tree = self.TREE

        class FakeLister:
            mode, api_error, requests_made, http = "html", None, 0, None

            class html:
                shortcuts_resolved = 0
                http = None

            def list(self, fid):
                return Listing(True, [Entry(**vars(e)) for e in tree[fid]])

        cfg = {"drive": {"root_folder_id": "ROOT", "min_panel": 77}}
        logged: list[str] = []
        with mock.patch.object(D, "DriveLister", lambda **kw: FakeLister()), \
                mock.patch.object(D, "load_config", lambda: cfg), \
                mock.patch.object(D, "check_forms", lambda items, http: {}), \
                mock.patch.object(D.log, "warning", lambda msg, *a: logged.append(msg % a if a else msg)), \
                mock.patch.object(D.log, "info", lambda msg, *a: logged.append(msg % a if a else msg)):
            D.main([])
        text = (self.raw / "drive.json").read_text(encoding="utf-8")
        return json.loads(text), text, logged

    def test_the_covers_folders(self):
        env, text, logged = self.run_main()
        items = {i["id"]: i for i in env["items"]}
        gv, lv, odd = items["drive:gv1"], items["drive:lv1"], items["drive:lv2"]
        # the dates come from the names, never from the "12/31/79" of the listing (nor 2079)
        self.assertEqual((gv["date"], lv["date"]), ("2026-11-01", "2026-11-01"))
        self.assertNotIn("2079", text)
        self.assertEqual(gv["extra"]["cover"], {"pub": "gv", "year": 2026, "month": 11, "issue": None, "months": [11], "key": "2026-11"})
        self.assertEqual(lv["extra"]["cover"], {"pub": "lv", "year": 2026, "month": None, "issue": 6, "months": [11, 12], "key": "2026-11"})
        self.assertEqual((gv["extra"]["album"], lv["extra"]["album"], odd["extra"]["album"]),
                         ("Grapevine covers 2026", "La Viña covers 2026", "La Viña covers 2026"))
        self.assertEqual((gv["title"], gv["lang"], lv["title"], lv["lang"]),
                         ("Grapevine — November 2026", "en", "La Viña — Noviembre–Diciembre 2026", "es"))
        self.assertEqual((odd["title"], odd["date"], odd["extra"]["cover"]["key"]), ("portada sin nombre", "2026-01-01", ""))
        self.assertEqual((gv["extra"]["path"], gv["extra"]["is_image"]), (["photos", "AAGrapevine_covers", "2026"], True))
        # the owner's two _index.csv lists: left out, counted by type, never named — in no field, no stat, no log line
        self.assertEqual(set(items), {"drive:gv1", "drive:lv1", "drive:lv2", "drive:loose1", "drive:rep1"})
        self.assertEqual(env["stats"]["excluded_by_reason"], {"type text/csv": 2})
        for where in (text, "\n".join(logged)):
            self.assertNotIn("_index", where)
            self.assertNotIn("csv1", where)
            self.assertNotIn("csv2", where)
        # the loose photo is unchanged: its listing day, no album (the panel's own album on /photos/), no cover
        loose = items["drive:loose1"]
        self.assertEqual((loose["date"], loose["extra"]["album"], loose["title"]), ("2026-11-12", None, "2026 Dallas Gathering Of Eagles"))
        self.assertNotIn("cover", loose["extra"])
        # a 12/31/79 listing day is no date for any file: the report is dated the day the site first had it
        self.assertEqual(items["drive:rep1"]["date"], local_today().isoformat())
        # the stats count the covers and the name that could not be read — and never name one
        st = env["stats"]
        self.assertEqual((st["covers"], st["covers_unrecognized"], st["covers_fixed"], st["covers_duplicate"]), (3, 1, 0, 0))
        self.assertEqual(st["albums"], {"La Viña covers 2026": 2, "Grapevine covers 2026": 1})
        notes = [w for w in st["warnings"] if "magazine covers" in w]
        self.assertEqual(len(notes), 1)
        self.assertNotIn("portada", " ".join(st["warnings"]))
        self.assertNotIn("portada sin nombre", "\n".join(logged))

    def test_a_2079_date_an_earlier_run_stored_is_replaced(self):
        """A run before the fix stored 2079-12-31 for every cover (and any file listed "12/31/79"): the next run
        dates the cover by its name, and a file without a date of its own by the day the site first had it."""
        first = "2026-11-13T06:00:00Z"
        old = []
        for fid, cat, title in (("gv1", "photos", "GV 2026-11 November"), ("rep1", "reports", "District report")):
            old.append({"id": f"drive:{fid}", "source": "drive", "kind": "photo" if cat == "photos" else "document",
                        "url": "", "title": title, "summary": "", "lang": "en", "date": "2079-12-31", "first_seen": first,
                        "last_seen": first, "image": None, "tags": [], "category": cat, "status": "ok",
                        "extra": {"file_id": fid, "album": "AAGrapevine_covers / 2026" if cat == "photos" else None,
                                  "folder_chain": ["ROOT", "P77"]}})
        common.write_json(self.raw / "drive.json", {"source": "drive", "updated": first, "ok": True, "error": None,
                                                    "stats": {}, "items": old, "first_harvest": "2026-09-24T00:00:00Z"})
        env, text, _ = self.run_main()
        items = {i["id"]: i for i in env["items"]}
        self.assertEqual(items["drive:gv1"]["date"], "2026-11-01")
        self.assertEqual(items["drive:gv1"]["first_seen"], first)                  # (still the day it was first seen)
        self.assertEqual(items["drive:gv1"]["extra"]["album"], "Grapevine covers 2026")
        self.assertEqual(items["drive:rep1"]["date"], "2026-11-13")                # its first_seen day, not 2079
        self.assertNotIn("2079", text)

    def test_two_files_of_one_issue_are_counted_never_named(self):
        """A re-upload's "GV_2026-11_November (1).jpg" next to the first: both show (two "November 2026" tiles) —
        the run says how many issues have more than one file, never which."""
        self.TREE = {**WholeRun.TREE, "GV26": WholeRun.TREE["GV26"] + [
            Entry("gv1b", "GV_2026-11_November (1).jpg", "image/jpeg", modified_text="12/31/79", modified="1979-12-31")]}
        env, text, logged = self.run_main()
        st = env["stats"]
        self.assertEqual((st["covers"], st["covers_duplicate"], st["covers_fixed"]), (4, 1, 0))
        notes = [w for w in st["warnings"] if "more than one file" in w]
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("magazine covers: 1 issue(s)"), notes[0])
        for where in (" ".join(st["warnings"]), "\n".join(logged)):
            self.assertNotIn("GV_2026-11", where)

    def test_a_row_kept_unread_gets_a_day_it_can_have(self):
        """merge keeps a row whose folder could not be read this run as it was — with a day it can have: the
        2079-12-31 a run before the "12/31/79" fix stored becomes the day the site first had it; a cover's issue day
        and a day written in the file's name (past or coming) stay."""
        first = "2026-11-13T06:00:00Z"

        def row(fid: str, day: str, name: str, **ex) -> dict:
            return {"id": f"drive:{fid}", "source": "drive", "kind": "photo", "url": "", "title": name, "summary": "",
                    "lang": "en", "date": day, "first_seen": first, "last_seen": first, "image": None, "tags": [],
                    "category": "photos", "status": "ok",
                    "extra": {"file_id": fid, "name": name, "folder_chain": ["ROOT", "P77", "UNREAD"], **ex}}
        prev = [row("old", "2079-12-31", "GV_2026-11_November.jpg", album="AAGrapevine_covers / 2026"),
                row("agenda", "2027-03-14", "2027-03-14 Spring Assembly agenda.pdf"),
                row("minutes", "1995-01-01", "1995 Assembly minutes.pdf"),
                row("cover", "2027-01-01", "GV_2027-01_January.jpg",
                    cover={"pub": "gv", "year": 2027, "month": 1, "issue": None, "months": [1], "key": "2027-01"}),
                row("fine", "2026-10-03", "IMG_1.jpg")]
        with mock.patch.object(D, "local_today", lambda: date(2026, 11, 13)):
            out, st = D.merge(prev, [], {"UNREAD"})
        days = {i["id"]: i["date"] for i in out}
        self.assertEqual(st["kept_unverified"], 5)
        self.assertEqual(days, {"drive:old": "2026-11-13", "drive:agenda": "2027-03-14", "drive:minutes": "1995-01-01",
                                "drive:cover": "2027-01-01", "drive:fine": "2026-10-03"})
        self.assertEqual(prev[0]["date"], "2079-12-31", "the last run's rows are not changed in place")


# =========================================================================== the site's data (build_data)
def site_item(path: list[str], name: str, first_seen: str, mime: str = "image/jpeg", **entry) -> dict:
    """A Drive item as build_data makes it for data/site/drive.json (prep → i18n → is_new → no private keys)."""
    from scripts.sync import build_data as B
    raw = built(path, name, mime, **entry)
    raw.pop("_cover_note", None)
    raw["first_seen"], raw["last_seen"], raw["status"] = first_seen, first_seen, "ok"
    return B.prep(raw)


class SiteData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.sync import build_data as B
        cls.B = B

    def ctx(self):
        ctx = self.B.Ctx(offline=True)
        ctx.births["drive"] = ctx.now_ts - 60 * 86400                     # the source's first harvest: 2 months ago
        return ctx

    def test_the_i18n_is_written_by_rule_and_nothing_is_translated(self):
        B = self.B
        now = iso(datetime.now(timezone.utc))
        covers = [site_item(GV_DIR, "GV_2026-11_November.jpg", now),
                  site_item(LV_DIR, "LaVina_2026-06_Noviembre-Diciembre.png", now, "image/png"),
                  site_item(["photos", "AALavina_covers"], "portada sin nombre.jpg", now)]
        # nothing about a cover is asked of the translator (title and album are not even offered)
        for it in covers:
            self.assertEqual([f for f, *_ in B.text_fields(it)], ["summary"])
        i18n = B.I18n(None)
        B.plan_translations(self.ctx(), {"drive": covers}, {id(c) for c in covers}, i18n)
        self.assertEqual(i18n.jobs, {})
        for it in covers:
            i18n.apply(it)
        gv, lv, odd = covers
        self.assertEqual(gv["i18n"]["title"], {"en": "Grapevine — November 2026", "es": "Grapevine — Noviembre 2026"})
        self.assertEqual(gv["i18n"]["album"], {"en": "Grapevine covers 2026", "es": "Portadas de Grapevine 2026"})
        self.assertEqual(lv["i18n"]["title"], {"en": "La Viña — November–December 2026", "es": "La Viña — Noviembre–Diciembre 2026"})
        self.assertEqual(lv["i18n"]["album"], {"en": "La Viña covers 2026", "es": "Portadas de La Viña 2026"})
        self.assertEqual(odd["i18n"]["title"], {"en": "portada sin nombre", "es": "portada sin nombre"})
        self.assertEqual(odd["i18n"]["album"], {"en": "La Viña covers", "es": "Portadas de La Viña"})
        self.assertEqual([c["machine"] for c in covers], [[], [], []])
        # an ordinary album photo is still translated as before (its title and album are offered)
        photo = site_item(["photos", "Booth at CityWide"], "Booth table.jpg", now)
        self.assertEqual([f for f, *_ in B.text_fields(photo)], ["title", "summary", "album"])

    def test_new_only_for_a_recent_issue(self):
        ctx = self.ctx()
        now = ctx.now
        seen = iso(now - timedelta(days=1))

        def new(path, name, first_seen=seen):
            return ctx.is_new(site_item(path, name, first_seen), "drive")
        key = (now - timedelta(days=30)).strftime("%Y-%m")
        self.assertTrue(new(GV_DIR[:2] + [key[:4]], f"GV_{key}_x.jpg"))                     # an issue of last month
        old = (now - timedelta(days=95)).strftime("%Y-%m")
        self.assertFalse(new(GV_DIR[:2] + [old[:4]], f"GV_{old}_x.jpg"))                     # three months back
        self.assertFalse(new(["photos", "AAGrapevine_covers", "2015"], "GV_2015-07_July.jpg"))   # the back catalogue
        self.assertFalse(new(["photos", "AAGrapevine_covers", "2019"], "scan 3.jpg"))           # month unknown
        ahead = (now + timedelta(days=40)).strftime("%Y-%m")
        self.assertTrue(new(GV_DIR[:2] + [ahead[:4]], f"GV_{ahead}_x.jpg"))                  # next month's issue
        # … and only while the site has had it for less than 14 days
        self.assertFalse(new(GV_DIR[:2] + [key[:4]], f"GV_{key}_x.jpg", iso(now - timedelta(days=20))))
        # the first harvest is never news
        ctx.births["drive"] = ctx.now_ts - 86400
        self.assertFalse(new(GV_DIR[:2] + [key[:4]], f"GV_{key}_x.jpg"))


# =========================================================================== Home's "Committee uploads"
class HomeUploads(unittest.TestCase):
    def test_home_never_shows_a_cover(self):
        now = "2026-11-13T12:00:00Z"
        items = [site_item(GV_DIR, "GV_2026-11_November.jpg", now), site_item(GV_DIR, "GV_2026-12_December.jpg", now),
                 site_item(["reports"], "2026-11-10 District report.pdf", now, "application/pdf"),
                 site_item(["photos"], "2026 Dallas Gathering Of Eagles.jpg", now, modified="2026-11-12")]
        got = run_js(self, "out(filters.homeDrive(input, 6).map((i) => i.id))", data=items, now=now)
        self.assertEqual(got, ["drive:f-2026 Dallas Gathering Of Eagles.jpg", "drive:f-2026-11-10 District report.pdf"])


if __name__ == "__main__":
    unittest.main()
