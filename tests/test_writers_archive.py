"""Offline tests for the Texas writers archive: the owner's archive files in content/archive/
(scripts/sync/writers_archive.py → data/raw/writers_archive.json), the archive site file
(scripts/sync/build_data.py → data/site/writers_archive.json), its status.json entries and the reminders of
dated settings (status.json `reminders`). No network.

    python -m unittest tests.test_writers_archive -v        (or: python -m unittest discover -s tests)

Fixtures: tests/fixtures/writers_archive/gv.csv and lv.csv — small archive files with the real header (the
Grapevine one with a BOM, the La Viña one without), copied under archive names into a temporary folder.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import geo  # noqa: E402
from scripts.sync import writers_archive as W  # noqa: E402
from test_spotlight import AREA65_TEST_COUNTIES  # noqa: E402  (the whole Area 65 list, pinned — RealFiles)

FIX = ROOT / "tests" / "fixtures" / "writers_archive"
GV_NAME, LV_NAME = "aagrapevine_archive_2026-10-04.csv", "aalavina_archive_2026-10-04.csv"
GV, LV = "https://www.aagrapevine.org", "https://www.aalavina.org"
# The Area 65 counties these tests need (a copy on purpose: the chair may edit config/site.yml
# spotlight.neta65_counties — see tests/test_spotlight.py).
AREA65 = frozenset(geo.normalize_place(c) for c in (
    "Dallas", "Tarrant", "Denton", "Collin", "Ellis", "Johnson", "Parker", "Wise", "Smith", "Anderson", "McLennan",
    "Grayson"))


def _area65() -> frozenset:
    return AREA65


def _all_area65() -> frozenset:
    return AREA65_TEST_COUNTIES


_area65.cache_clear = _all_area65.cache_clear = lambda: None          # geo.reset_caches() calls it


class Pinned(unittest.TestCase):
    """The Area 65 counties above, and a temporary folder for each test."""

    def setUp(self):
        p = mock.patch.object(geo, "_neta65_cached", _area65)
        p.start()
        self.addCleanup(p.stop)
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-wa-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def folder(self, *files: tuple[str, str | bytes]) -> Path:
        """content/archive with (name, fixture file name | raw bytes) entries."""
        d = self.tmp / "archive"
        d.mkdir(exist_ok=True)
        for name, src in files:
            (d / name).write_bytes(src if isinstance(src, bytes) else (FIX / src).read_bytes())
        return d

    def both(self) -> Path:
        return self.folder((GV_NAME, "gv.csv"), (LV_NAME, "lv.csv"))


# =========================================================================== file names
class FileNames(unittest.TestCase):
    def test_names_and_their_dates(self):
        cases = {
            "aagrapevine_archive_2026-10-04.csv": ("gv", date(2026, 10, 4), 0, 0),
            "aalavina_archive_2026-10-04.csv": ("lv", date(2026, 10, 4), 0, 0),
            "aagrapevine_archive_2026-10-04 (1).csv": ("gv", date(2026, 10, 4), 1, 0),
            "aagrapevine_archive_20261104.csv": ("gv", date(2026, 11, 4), 0, 0),
            "AAGRAPEVINE_ARCHIVE_2026-11-05.CSV": ("gv", date(2026, 11, 5), 0, 0),
            "aagrapevine-archive-2026.11.05_v2.csv": ("gv", date(2026, 11, 5), 0, 2),
            "aalavina_archive_2026-12-01T0815.csv": ("lv", date(2026, 12, 1), 0, 0),
            "aalavina_archive_202612021530.csv": ("lv", date(2026, 12, 2), 0, 0),
            "aa_la_vina_archive_12-03-2026.csv": ("lv", date(2026, 12, 3), 0, 0),
            "aalaviña_archive_2026-12-04.csv": ("lv", date(2026, 12, 4), 0, 0),
            "aalavin\u0303a_archive_2026-12-05.csv": ("lv", date(2026, 12, 5), 0, 0),      # ñ in two pieces (macOS)
            "grapevine archive 2026-11-06.csv": ("gv", date(2026, 11, 6), 0, 0),
            "GV Archives 2026_11_7.csv": ("gv", date(2026, 11, 7), 0, 0),
            "aalavina_archive.csv": ("lv", None, 0, 0),
            "aagrapevine_archive_2026-13-40.csv": ("gv", None, 0, 0),              # no such day
        }
        for name, want in cases.items():
            with self.subTest(name=name):
                c = W.parse_name(name)
                self.assertIsNotNone(c)
                self.assertEqual((c["pub"], c["date"], c["copy"], c["version"]), want)
        for name in ("notes.txt", "aagrapevine_archive_2026-10-04.xlsx", "README.md", "texas_writers.csv",
                     "archive_2026-10-04.csv", "aagrapevine_2026-10-04.csv"):
            self.assertIsNone(W.parse_name(name), name)

    def test_the_newest_name_wins(self):
        def newest(*names):
            return max((W.parse_name(n) for n in names), key=W.newest_key)["name"]
        self.assertEqual(newest("aagrapevine_archive_2026-10-04.csv", "aagrapevine_archive_2026-11-05.csv"),
                         "aagrapevine_archive_2026-11-05.csv")
        self.assertEqual(newest("aagrapevine_archive_2026-10-04.csv", "aagrapevine_archive_2026-10-04 (1).csv"),
                         "aagrapevine_archive_2026-10-04 (1).csv", "a browser's second download is the later one")
        self.assertEqual(newest("aagrapevine_archive_2026-11-05_v2.csv", "aagrapevine_archive_2026-11-05 (3).csv"),
                         "aagrapevine_archive_2026-11-05_v2.csv", "a version counts before a copy number")
        self.assertEqual(newest("aagrapevine_archive.csv", "aagrapevine_archive_1999-01-01.csv"),
                         "aagrapevine_archive_1999-01-01.csv", "a name without a date loses to any dated one")
        self.assertEqual(newest("aagrapevine_archive_2026-12-01T0815.csv", "aagrapevine_archive_20261130.csv"),
                         "aagrapevine_archive_2026-12-01T0815.csv")

    def test_the_folder_setting(self):
        self.assertEqual(W.archive_dir({}), common.CONTENT_DIR / "archive")
        self.assertEqual(W.archive_dir({"writers_archive": {"folder": "content/old-archive"}}),
                         common.ROOT / "content" / "old-archive")
        self.assertEqual(W.min_rows_ratio({}), (0.8, None))
        self.assertEqual(W.min_rows_ratio({"writers_archive": {"min_rows_ratio": 0}}), (0.0, None))
        self.assertEqual(W.min_rows_ratio({"writers_archive": {"min_rows_ratio": 3}})[0], 1.0)
        ratio, note = W.min_rows_ratio({"writers_archive": {"min_rows_ratio": "most"}})
        self.assertEqual(ratio, 0.8)
        self.assertIn("is not a number", note)


class ContentHash(unittest.TestCase):
    def test_line_ends_and_the_bom_do_not_count(self):
        lf = (FIX / "lv.csv").read_bytes()
        crlf = lf.replace(b"\n", b"\r\n")
        cr = lf.replace(b"\n", b"\r")
        with_bom = b"\xef\xbb\xbf" + crlf
        tmp = Path(tempfile.mkdtemp(prefix="gv-wa-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        hashes = set()
        for i, raw in enumerate((lf, crlf, cr, with_bom)):
            p = tmp / f"{i}.csv"
            p.write_bytes(raw)
            text, note = W.read_text(p)
            self.assertIsNone(note)
            hashes.add(W.content_hash(text))
        self.assertEqual(len(hashes), 1)
        self.assertNotEqual(W.content_hash("a\nb"), W.content_hash("a\nc"))

    def test_a_windows_1252_file_is_read_with_a_warning(self):
        tmp = Path(tempfile.mkdtemp(prefix="gv-wa-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        p = tmp / "x.csv"
        p.write_bytes("Link,Title\nhttps://www.aalavina.org/revista/a/b,La Viña\n".encode("cp1252"))
        text, note = W.read_text(p)
        self.assertIn("La Viña", text)
        self.assertIn("Windows-1252", note)
        p.write_bytes(b"\xef\xbb\xbf" + "Link,Title\nhttps://www.aalavina.org/revista/a/b,La Viña\n".encode("cp1252"))
        text, note = W.read_text(p)
        self.assertEqual((text[:5], W.read_rows(text)[1]["link"]), ("Link,", "Link"),
                         "a UTF-8 BOM in front of Windows-1252 text is dropped, not read as “ï»¿”")
        self.assertIn("La Viña", text)
        self.assertIn("Windows-1252", note)

    def test_a_utf8_file_with_a_stray_byte_stays_utf8(self):
        """A UTF-8 export with one byte that is not UTF-8 (a hand edit, a tool's slip): that byte shows as “\ufffd”
        and the rest as written. Read as Windows-1252, its BOM became “ï»¿Link” (the file was rejected for a missing
        Link column) and its accents “Ã­” — some for good (“Á”, the closing quote ”)."""
        tmp = Path(tempfile.mkdtemp(prefix="gv-wa-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        stray = (FIX / "lv.csv").read_bytes().replace("obligación".encode(), b"obligaci\xf3n")
        for bom in (b"\xef\xbb\xbf", b""):
            p = tmp / "x.csv"
            p.write_bytes(bom + stray)
            text, note = W.read_text(p)
            self.assertEqual(W.read_rows(text)[1]["link"], "Link", bom)
            self.assertIn("obligaci\ufffdn", text)
            self.assertIn("El despertar del espíritu", text)
            self.assertNotIn("Ã", text)
            self.assertEqual(note, "x.csv: 1 character(s) are not UTF-8 (the first on line 2) — they show as "
                                   "“\ufffd”; save it as “CSV UTF-8” again")


# =========================================================================== columns and cleaning
class Columns(unittest.TestCase):
    def test_headers_by_how_they_start(self):
        real = ["\ufeffLink", "Title", "Has Audio Version (audio icon)", "Month", "Year", "Theme", "Written By", "City",
                "State", "Brief", "Audio Only (no article text)", "Texas Author?", "Location (as published)", "Notes"]
        hdr = W.map_header(real)
        self.assertEqual(set(hdr), {f for f, _ in W.COLUMNS})
        self.assertEqual((hdr["has_audio"], hdr["audio_only"], hdr["texas"]),
                         ("Has Audio Version (audio icon)", "Audio Only (no article text)", "Texas Author?"))
        other = W.map_header(["URL", "TITLE", "author ", "  Location  as printed", "month", "YEAR",
                              "Texas  Author (yes/no)", "Link"])
        self.assertEqual(other["link"], "URL", "the first header of a field wins")
        self.assertEqual((other["author"], other["location"], other["texas"]),
                         ("author ", "  Location  as printed", "Texas  Author (yes/no)"))
        self.assertEqual(set(W.REQUIRED) - set(other), set())


class Cleaning(unittest.TestCase):
    def test_every_field(self):
        c = W.clean_field
        self.assertEqual(c("Jos&eacute; D.; Ren&eacute;e S."), "José D.; Renée S.")
        self.assertEqual(c("<p>The &quot;we&quot; of AA</p><br />next"), 'The "we" of AA next')
        self.assertEqual(c("A small miracle in MazatlÃ¡n"), "A small miracle in Mazatlán")
        self.assertEqual(c("meetingâ€”an amends"), "meeting—an amends")
        self.assertEqual(c("86Ã‚Â¢ Toward Recovery"), "86¢ Toward Recovery")           # two layers
        broken = "díaz".encode("utf-8").decode("cp1252").encode("utf-8").decode("cp1252")
        self.assertEqual(c(broken), "díaz")
        self.assertEqual(c("MarÃ\xada Inés"), "María Inés", "good and broken letters in one name")
        self.assertEqual(c("Co\u0301mo llegue\u0301"), "Cómo llegué")
        self.assertEqual(c("Nuestra sobriedad durante las \ufb01estas"), "Nuestra sobriedad durante las fiestas")
        self.assertEqual(c("Re\u00adnacer"), "Renacer")
        self.assertEqual(c("  two   spaces\u00a0here "), "two spaces here")
        self.assertIsNone(c(""))
        self.assertIsNone(c("<br />"))
        self.assertIsNone(c(None))
        self.assertEqual(c("Café"), "Café", "correct text is left alone")

    def test_the_exports_broken_line_breaks(self):
        """"<lb" with no closing ">" (181 Grapevine rows of the 2026-10-04 file) becomes a dash between the parts."""
        c = W.clean_field
        self.assertEqual(c("The Home Group<lbHeartbeat of AA"), "The Home Group — Heartbeat of AA")
        self.assertEqual(c("William Silkworth M.D.<lb1873--1951"), "William Silkworth M.D. — 1873--1951")
        self.assertEqual(c("Sobriety<lb<em>a new life</em>"), "Sobriety — a new life")
        self.assertEqual(c("<lbAt the start"), "At the start")
        self.assertEqual(c("At the end<lb>"), "At the end")
        self.assertEqual(c("— A dash of its own"), "— A dash of its own", "a dash the text has is kept")

    def test_entities_go_before_the_writers_are_split(self):
        ws = W.writers_of(W.clean_field("Bonnie &amp; Frank W."), "Houston, Texas", "Houston", "Texas")
        self.assertEqual([w["name"] for w in ws], ["Bonnie & Frank W."])
        ws = W.writers_of(W.clean_field("Jos&eacute; D."), W.clean_field("Ste. Doroth&eacute;e, Quebec"), None, None)
        self.assertEqual([(w["name"], w["place"]) for w in ws], [("José D.", "Ste. Dorothée, Quebec")])


class Issues(unittest.TestCase):
    def test_month_and_year(self):
        self.assertEqual(W.issue_of("gv", "October", "1991"), ("1991-10", "October 1991", 1991, 10))
        self.assertEqual(W.issue_of("gv", "june", "2026"), ("2026-06", "June 2026", 2026, 6))
        self.assertEqual(W.issue_of("gv", "MAY", "1950"), ("1950-05", "May 1950", 1950, 5))
        self.assertEqual(W.issue_of("lv", "Septiembre / Octubre", "2016"),
                         ("2016-09", "Septiembre / Octubre 2016", 2016, 9))
        self.assertEqual(W.issue_of("lv", "Noviembre/Diciembre", "2021"),
                         ("2021-11", "Noviembre / Diciembre 2021", 2021, 11))
        self.assertEqual(W.issue_of("gv", "", ""), (None, None, None, None))
        self.assertEqual(W.issue_of("gv", None, "1990"), (None, None, 1990, None))
        self.assertEqual(W.issue_of("gv", "Octember", "1990"), (None, None, 1990, None))

    def test_the_copies_of_the_articles_helpers_still_agree(self):
        from scripts.sync import articles as A
        for pub, key in (("gv", "1991-10"), ("lv", "2016-09"), ("lv", "2021-11"), ("lv", "2020-12"), ("gv", None)):
            self.assertEqual(W.label_from_key(pub, key), A.label_from_key(pub, key), (pub, key))
        for label in ("june 2026", "septiembre / octubre 2026", "October 2026", "PO Box", None, ""):
            self.assertEqual(W.tidy_label(label), A.tidy_label(label), label)
        for url in ("https://www.aagrapevine.org/magazine/2011/apr/more-information-FRB/", "HTTP://WWW.AALAVINA.ORG//x?y=1#z",
                    "https://www.aagrapevine.org"):
            self.assertEqual(W.canonical(url), A.canonical(url), url)
            self.assertEqual(W.pub_of_url(url), A.pub_of_url(url), url)


class Writers(unittest.TestCase):
    def test_a_letters_column_lists_each_writer(self):
        ws = W.writers_of("Mike K.; Jim O.; Jim B.", "Palestine, Texas; Texas; San Marcos, Texas",
                          "Palestine; (city not given); San Marcos", "Texas; Texas; Texas")
        self.assertEqual([(w["name"], w["place"], w["city"], w["state"]) for w in ws], [
            ("Mike K.", "Palestine, Texas", "Palestine", "Texas"), ("Jim O.", "Texas", None, "Texas"),
            ("Jim B.", "San Marcos, Texas", "San Marcos", "Texas")])

    def test_pairs_by_position_and_a_missing_state_is_the_last_one(self):
        ws = W.writers_of("Irene H-P.; Stacy C.", "San Antonio, Texas; Horseshoe Bay, Texas", "San Antonio; Horseshoe Bay",
                          "Texas")
        self.assertEqual([(w["name"], w["state"]) for w in ws], [("Irene H-P.", "Texas"), ("Stacy C.", "Texas")])

    def test_one_place_is_one_writer_as_printed(self):
        ws = W.writers_of("Dr. Smith; U.S. Journal", None, None, None)
        self.assertEqual([w["name"] for w in ws], ["Dr. Smith; U.S. Journal"])
        self.assertEqual(W.writers_of(None, None, None, None), [])

    def test_initials_and_anonymous(self):
        for given, shown in (("H.t.b.", "H.T.B."), ("S.g.w.", "S.G.W."), ("R. o.", "R. O."), ("J.G.", "J.G."),
                             ("Tb-d.", "Tb-d."), ("K.sb.", "K.sb."), ("Jake B.", "Jake B."), ("Ann", "Ann")):
            self.assertEqual(W.fix_initials(given), shown, given)
        for name in ("Anonymous", "anonymous.", "Anon.", "Anónimo", "Anónimo.", "Anonima", "Un alcohólico anónimo"):
            self.assertTrue(W.is_anonymous(name), name)
        for name in ("Anonymous Joe", "Ann O.", None, ""):
            self.assertFalse(W.is_anonymous(name), name)


class BestOf(Pinned):
    def test_the_better_of_the_printed_place_and_city_state(self):
        g = W.writer_geo({"place": "Forth Worth, Texas", "city": "Fort Worth", "state": "Texas"}, "gv")
        self.assertEqual((g["scope"], g["county"], g["label_en"]), ("neta65", "Tarrant", "Fort Worth, Texas"))
        g = W.writer_geo({"place": "Irvin, Texas", "city": "Irving", "state": "Texas"}, "lv")
        self.assertEqual((g["scope"], g["county"]), ("neta65", "Dallas"))
        g = W.writer_geo({"place": "Waco, exas", "city": "Waco", "state": "Texas"}, "gv")
        self.assertEqual((g["scope"], g["county"], g["label_en"]), ("neta65", "McLennan", "Waco, Texas"))
        g = W.writer_geo({"place": "Northeast-Texas-Area"}, "gv")          # no City / State at all
        self.assertEqual(g["scope"], "neta65")
        g = W.writer_geo({"place": 'Grupo "Paz", Dallas, Texas', "city": "Dallas", "state": "Texas"}, "lv")
        self.assertEqual(g["scope"], "neta65", "a quoted group name: the City / State columns still find Dallas")
        g = W.writer_geo({"place": "Cheyenne, Wyoming", "city": "Cheyenne", "state": "Wyoming"}, "gv")
        self.assertEqual(g["scope"], "other")

    def test_a_row_takes_its_best_writer(self):
        ws = W.writers_of("Mike K.; Jim O.; Jim B.", "Palestine, Texas; Texas; San Marcos, Texas",
                          "Palestine; (city not given); San Marcos", "Texas; Texas; Texas")
        self.assertEqual(W.row_scope(ws, "gv"), "neta65", "Palestine (Anderson County) is in Area 65")
        self.assertEqual(geo.classify_location("Palestine, Texas; Texas; San Marcos, Texas")["scope"], "texas",
                         "unsplit, the byline would read only the last city")
        self.assertEqual(W.row_scope([], "gv"), "unknown")


# =========================================================================== the rows of the fixtures
class Rows(Pinned):
    def setUp(self):
        super().setUp()
        with mock.patch.object(W, "now_iso", return_value="2026-10-04T12:00:00Z"):
            self.res = W.import_archive(self.both(), {}, {})
        self.items = {it["key"]: it for it in self.res["items"]}

    def get(self, path: str) -> dict:
        return self.items[(GV if path.startswith("/magazine") else LV) + path]

    def test_texas_writers_only(self):
        self.assertTrue(self.res["ok"])
        self.assertEqual(len(self.items), 17)
        for path in ("/magazine/2010/jan/out-west", "/magazine/2011/dec/audio/note-editor", "/revista/mayo-junio-2018/en-miami"):
            self.assertNotIn((GV if path.startswith("/magazine") else LV) + path, self.items)
        self.assertNotIn("https://example.org/not-a-magazine-page", self.items)
        # the file said "Unknown" (a group, no city) — the place is Area 65 itself
        corner = self.get("/magazine/1958/sep/delegates-corner-0")
        self.assertIsNone(corner["texas_csv"])
        self.assertTrue(corner["group_byline"])
        st = self.res["stats"]
        self.assertEqual((st["rows"], st["texas"], st["neta65"], st["new"], st["changed"]), (22, 17, 11, 17, True))
        self.assertEqual(st["notes"], [
            "New archive file used: aagrapevine_archive_2026-10-04.csv (17 rows, 14 Texas writers)",
            "New archive file used: aalavina_archive_2026-10-04.csv (5 rows, 4 Texas writers)"])
        self.assertEqual(st["warnings"], [
            "aagrapevine_archive_2026-10-04.csv: 1 row(s) without a Grapevine or La Viña link were left out"])

    def test_the_raw_item(self):
        it = self.get("/magazine/1991/oct/what-and-who-we-really-are")
        self.assertEqual(it, {
            "id": "wa:" + common.short_hash(it["key"], 12), "source": "writers_archive", "kind": "archive_story",
            "url": f"{GV}/magazine/1991/oct/what-and-who-we-really-are",
            "key": f"{GV}/magazine/1991/oct/what-and-who-we-really-are", "pub": "gv", "lang": "en",
            "title": "What and Who We Really Are", "date": "1991-10-01", "issue_key": "1991-10",
            "issue_label": "October 1991", "year": 1991, "month": 10, "undated": False, "theme": None,
            "subtitle": 'The "we" of AA is us',
            "writers": [{"name": "John W.", "place": "Denton, Texas", "city": "Denton", "state": "Texas",
                         "anonymous": False}],
            "audio": False, "audio_only": False, "online_exclusive": False, "column": False,
            "signature_byline": False, "group_byline": False, "texas_csv": True,
            "first_seen": "2026-10-04T12:00:00Z"})
        self.assertFalse(any("geo" in it or "scope" in it or "geo" in w for it in self.res["items"] for w in it["writers"]),
                         "where writers are from is worked out by build_data")
        self.assertEqual({it["first_seen"] for it in self.res["items"]}, {"2026-10-04T12:00:00Z"},
                         "a first import: every row came in with this run")

    def test_cleaned_fields(self):
        miracle = self.get("/magazine/2003/apr/small-miracle")
        self.assertEqual((miracle["title"], miracle["subtitle"]), ("A small miracle in Mazatlán", "At the meeting—an amends"))
        self.assertEqual([w["name"] for w in miracle["writers"]], ["Bonnie & Frank W."])
        june = self.get("/magazine/2026/jun/june-story")
        self.assertEqual((june["issue_key"], june["issue_label"], june["writers"][0]["name"]),
                         ("2026-06", "June 2026", "José D."))
        sob = self.get("/revista/noviembre-diciembre-2021/nuestra-sobriedad")
        self.assertEqual(sob["theme"], "Nuestra sobriedad durante las fiestas · Cómo llegué a AA")
        self.assertEqual((sob["issue_label"], sob["lang"]), ("Noviembre / Diciembre 2021", "es"))
        self.assertTrue(sob["writers"][0]["anonymous"])
        self.assertEqual(self.get("/revista/marzo-abril-2021/renacer")["title"], "Renacer")
        self.assertEqual(self.get("/magazine/1955/mar/rough-road")["writers"][0]["name"], "H.T.B.")

    def test_undated(self):
        it = self.get("/magazine/true-north")
        self.assertEqual((it["date"], it["issue_key"], it["issue_label"], it["year"], it["undated"]),
                         (None, None, None, None, True))
        self.assertTrue(it["writers"][0]["anonymous"])
        self.assertEqual(self.res["items"][-1]["key"], it["key"], "an undated row sorts last")

    def test_flags(self):
        self.assertTrue(self.get("/magazine/2020/may/one-day-at-a-time-online")["online_exclusive"])
        letters = self.get("/magazine/2022/may/dear-grapevine-may-2022")
        self.assertTrue(letters["column"] and letters["signature_byline"] and letters["audio"])
        self.assertEqual(len(letters["writers"]), 3)
        self.assertTrue(self.get("/magazine/1982/jan/po-box-1980-1")["column"], "a column's own title")
        self.assertTrue(self.get("/magazine/1955/mar/rough-road")["signature_byline"])
        self.assertFalse(self.get("/magazine/1991/oct/what-and-who-we-really-are")["column"])
        for title in ("Dear Grapevine", "P.O. Box 1980", "At Wit's End", "Mail Call for Inmates", "Grass Roots Opinion"):
            self.assertTrue(W.is_column(title), title)
        self.assertFalse(W.is_column("A Dear Friend"))
        self.assertTrue(W.is_column("Anything", "Humor column with multiple contributors; only the Texas …"))

    def test_a_story_listed_twice_is_kept_once(self):
        self.assertIn(f"{GV}/magazine/1973/jul/my-two-sponsors", self.items)
        self.assertNotIn(f"{GV}/magazine/1973/jul/my-two-sponsors-0", self.items)
        a = {"key": "x/a", "pub": "gv", "issue_key": "2020-01", "title": "T", "writers": [{"name": "A.", "place": "P"}]}
        b = {**a, "key": "x/a-1"}
        other = {**a, "key": "x/a-2", "writers": [{"name": "B.", "place": "P"}]}     # another writer: another story
        self.assertEqual([i["key"] for i in W.drop_content_duplicates([b, a, other])], ["x/a", "x/a-2"])

    def test_sorted_newest_issue_first_then_address(self):
        dates = [it["date"] or "" for it in self.res["items"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
        same = [it["key"] for it in self.res["items"] if it["date"] == "2026-10-01"]
        self.assertEqual(same, sorted(same))

    def test_the_envelope_extras(self):
        ex = self.res["extra"]
        self.assertEqual(ex["parser_version"], W.PARSER_VERSION)
        gv = ex["files"]["gv"]
        self.assertEqual({k: gv[k] for k in ("name", "name_date", "rows", "texas_rows", "first_year")},
                         {"name": GV_NAME, "name_date": "2026-10-04", "rows": 17, "texas_rows": 14, "first_year": 1955})
        self.assertEqual(gv["sha256"], W.content_hash(W.read_text(FIX / "gv.csv")[0]))
        self.assertRegex(gv["imported_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


# =========================================================================== the folder
class Folder(Pinned):
    def test_an_older_copy_is_named_and_not_used(self):
        old = (FIX / "gv.csv").read_bytes().replace(b"A Halloween to Remember", b"An Older Title")
        res = W.import_archive(self.folder((GV_NAME, "gv.csv"), ("aagrapevine_archive_2026-09-01.csv", old),
                                           ("aagrapevine_archive.csv", old), (LV_NAME, "lv.csv"),
                                           ("README.md", b"# notes"), ("notes.txt", b"x")), {}, {})
        self.assertNotIn("An Older Title", json.dumps(res["items"]))
        warns = res["stats"]["warnings"]
        self.assertEqual(sorted(warns), [
            "aagrapevine_archive_2026-10-04.csv: 1 row(s) without a Grapevine or La Viña link were left out",
            "older archive file still in archive (it is not used and may be deleted): aagrapevine_archive.csv",
            "older archive file still in archive (it is not used and may be deleted): aagrapevine_archive_2026-09-01.csv"])
        self.assertEqual(res["extra"]["files"]["gv"]["name"], GV_NAME)

    def test_a_name_that_is_not_understood_is_reported(self):
        res = W.import_archive(self.folder((GV_NAME, "gv.csv"), ("texas writers.csv", "lv.csv")), {}, {})
        self.assertTrue(any("whose name is not an archive file's" in w and "texas writers.csv" in w
                            for w in res["stats"]["warnings"]))
        self.assertEqual({it["pub"] for it in res["items"]}, {"gv"})

    def test_an_undated_name_alone_is_used_with_a_warning(self):
        res = W.import_archive(self.folder(("aalavina_archive.csv", "lv.csv")), {}, {})
        self.assertEqual(res["extra"]["files"]["lv"]["name_date"], None)
        self.assertEqual(len(res["items"]), 4)
        self.assertTrue(any("has no date in its name" in w for w in res["stats"]["warnings"]))

    def test_the_links_decide_the_magazine(self):
        res = W.import_archive(self.folder((GV_NAME, "gv.csv"), ("aagrapevine_archive_2026-10-05.csv", "lv.csv")), {}, {})
        files = res["extra"]["files"]
        self.assertEqual((files["gv"]["name"], files["lv"]["name"]), (GV_NAME, "aagrapevine_archive_2026-10-05.csv"))
        self.assertTrue(any("the name says Grapevine but its links are La Viña's" in w for w in res["stats"]["warnings"]))

    def test_a_missing_file_keeps_the_rows_of_the_last_one(self):
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        shutil.rmtree(self.tmp / "archive")
        res = W.import_archive(self.folder((GV_NAME, "gv.csv")), {}, prev)
        self.assertTrue(res["ok"])
        self.assertEqual(json.dumps(res["items"]), json.dumps(first["items"]))
        self.assertEqual(res["extra"]["files"]["lv"], first["extra"]["files"]["lv"])
        self.assertIn("no La Viña archive file in", " ".join(res["stats"]["warnings"]))
        self.assertIn("(4 Texas writers)", " ".join(res["stats"]["warnings"]))

    def test_a_file_without_a_needed_column_is_not_used(self):
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        shutil.rmtree(self.tmp / "archive")
        broken = (FIX / "lv.csv").read_bytes().replace(b"Texas Author?", b"Texan?").replace(b",Year,", b",Yr,")
        res = W.import_archive(self.folder((GV_NAME, "gv.csv"), ("aalavina_archive_2026-11-05.csv", broken)), {}, prev)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "aalavina_archive_2026-11-05.csv: the columns Year, Texas Author? are missing — "
                                       "the file is not used, the older rows stay")
        self.assertEqual([i["key"] for i in res["items"] if i["pub"] == "lv"],
                         [i["key"] for i in first["items"] if i["pub"] == "lv"])
        self.assertEqual(res["extra"]["files"]["lv"]["name"], LV_NAME, "the file used before is still the one in use")

    def test_a_file_that_looks_cut_off_is_not_used(self):
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        prev["files"] = {**prev["files"], "gv": {**prev["files"]["gv"], "rows": 30}}       # the last file had 30 rows
        shutil.rmtree(self.tmp / "archive")
        folder = self.folder(("aagrapevine_archive_2026-11-05.csv", "gv.csv"), (LV_NAME, "lv.csv"))
        res = W.import_archive(folder, {}, prev)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "aagrapevine_archive_2026-11-05.csv has 17 rows, the file used before had 30 — it "
                                       "looks cut off, so the older data stays. If the smaller file is right, set "
                                       "writers_archive.min_rows_ratio: 0 in config/site.yml for one run")
        self.assertEqual(res["extra"]["files"]["gv"]["rows"], 30)
        ok = W.import_archive(folder, {"writers_archive": {"min_rows_ratio": 0}}, prev)
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["extra"]["files"]["gv"]["name"], "aagrapevine_archive_2026-11-05.csv")
        fine = W.import_archive(folder, {"writers_archive": {"min_rows_ratio": 0.5}}, prev)
        self.assertTrue(fine["ok"], "17 of 30 rows is more than half")

    # --- a newer file that fails while older ones are still in the folder
    CUT = b"\n".join((FIX / "gv.csv").read_bytes().split(b"\n")[:5]) + b"\n"           # the header and 4 rows
    NO_TEXAS = (FIX / "gv.csv").read_bytes().replace(b"Texas Author?", b"Texan?")
    OLDER = (FIX / "gv.csv").read_bytes().replace(b"A Halloween to Remember", b"An Older Title")

    def test_the_file_in_use_is_never_called_deletable(self):
        """The newest file fails while the file the site's rows came from is still in the folder: the rows stay, and
        that file "stays in use until" the newer one is fixed — never "not used and may be deleted". A copy older
        than it may go."""
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        folder = self.folder(("aagrapevine_archive_2026-11-05.csv", self.CUT),
                             ("aagrapevine_archive_2026-09-01.csv", self.OLDER))
        res = W.import_archive(folder, {}, prev)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "aagrapevine_archive_2026-11-05.csv has 4 rows, the file used before had 17 — "
                                       "it looks cut off, so the older data stays. If the smaller file is right, set "
                                       "writers_archive.min_rows_ratio: 0 in config/site.yml for one run")
        self.assertEqual(sorted(w for w in res["stats"]["warnings"] if w.startswith("older")), [
            "older archive file still in archive (it is not used and may be deleted): "
            "aagrapevine_archive_2026-09-01.csv",
            "older archive file still in archive (it stays in use until aagrapevine_archive_2026-11-05.csv is fixed): "
            "aagrapevine_archive_2026-10-04.csv"])
        self.assertEqual(res["extra"]["files"]["gv"], first["extra"]["files"]["gv"])
        self.assertEqual(json.dumps(res["items"]), json.dumps(first["items"]))
        (folder / "aagrapevine_archive_2026-11-05.csv").write_bytes(self.NO_TEXAS)          # columns missing: the same
        res = W.import_archive(folder, {}, prev)
        self.assertEqual(res["error"], "aagrapevine_archive_2026-11-05.csv: the column Texas Author? is missing — the "
                                       "file is not used, the older rows stay")
        self.assertIn("older archive file still in archive (it stays in use until aagrapevine_archive_2026-11-05.csv "
                      f"is fixed): {GV_NAME}", res["stats"]["warnings"])
        self.assertFalse(any(GV_NAME in w and "may be deleted" in w for w in res["stats"]["warnings"]))
        self.assertEqual(json.dumps(res["items"]), json.dumps(first["items"]))

    def test_a_first_run_takes_the_newest_older_file_that_passes(self):
        """No rows and no file on record (a first run, or data/raw rebuilt): a newest file that fails gives way to the
        newest older one that passes — the magazine is not left empty while a good file is in the folder."""
        res = W.import_archive(self.folder((GV_NAME, "gv.csv"), (LV_NAME, "lv.csv"),
                                           ("aagrapevine_archive_2026-11-05.csv", self.NO_TEXAS),
                                           ("aagrapevine_archive_2026-09-01.csv", self.OLDER)), {}, {})
        self.assertFalse(res["ok"], "the newest file still has to be fixed")
        self.assertEqual(res["error"], "aagrapevine_archive_2026-11-05.csv: the column Texas Author? is missing — the "
                                       f"file is not used, the older {GV_NAME} is used instead")
        self.assertEqual(res["extra"]["files"]["gv"]["name"], GV_NAME)
        self.assertEqual(len([i for i in res["items"] if i["pub"] == "gv"]), 13)
        self.assertIn(f"New archive file used: {GV_NAME} (17 rows, 14 Texas writers)", res["stats"]["notes"])
        self.assertIn("older archive file still in archive (it is not used and may be deleted): "
                      "aagrapevine_archive_2026-09-01.csv", res["stats"]["warnings"])
        self.assertFalse(any(GV_NAME in w for w in res["stats"]["warnings"] if w.startswith("older")))
        self.assertNotIn("An Older Title", json.dumps(res["items"]))
        shutil.rmtree(self.tmp / "archive")         # nothing older that passes: no rows, and the error says so
        res = W.import_archive(self.folder((LV_NAME, "lv.csv"), ("aagrapevine_archive_2026-11-05.csv", self.NO_TEXAS)),
                               {}, {})
        self.assertEqual(res["error"], "aagrapevine_archive_2026-11-05.csv: the column Texas Author? is missing — the "
                                       "file is not used, and there are no older Grapevine rows to keep")
        self.assertEqual(({i["pub"] for i in res["items"]}, list(res["extra"]["files"])), ({"lv"}, ["lv"]))

    def test_a_rejected_file_never_brings_back_an_older_copy(self):
        """The rows the site has (data/raw) are newer than any copy left in the folder: when the newest file fails,
        an older or undated copy is never read in their place."""
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        shutil.rmtree(self.tmp / "archive")
        res = W.import_archive(self.folder((LV_NAME, "lv.csv"), ("aagrapevine_archive_2026-11-05.csv", self.CUT),
                                           ("aagrapevine_archive.csv", self.OLDER)), {}, prev)
        self.assertFalse(res["ok"])
        self.assertEqual(json.dumps(res["items"]), json.dumps(first["items"]))
        self.assertIn("older archive file still in archive (it is not used and may be deleted): "
                      "aagrapevine_archive.csv", res["stats"]["warnings"])

    def test_a_utf8_file_with_a_stray_byte_is_used(self):
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        stray = b"\xef\xbb\xbf" + (FIX / "lv.csv").read_bytes().replace("obligación".encode(), b"obligaci\xf3n")
        res = W.import_archive(self.folder(("aalavina_archive_2026-11-05.csv", stray)), {}, prev)
        self.assertTrue(res["ok"], res["error"])
        self.assertEqual(res["extra"]["files"]["lv"]["name"], "aalavina_archive_2026-11-05.csv")
        it = next(i for i in res["items"] if i["key"].endswith("/el-despertar-del-espiritu"))
        self.assertEqual((it["title"], it["subtitle"]),
                         ("El despertar del espíritu", "Servir no es una obligaci\ufffdn, sino el privilegio de "
                                                       "compartir con otros"))
        self.assertIn("aalavina_archive_2026-11-05.csv: 1 character(s) are not UTF-8 (the first on line 2) — they show "
                      "as “\ufffd”; save it as “CSV UTF-8” again", res["stats"]["warnings"])

    def test_the_other_magazines_export_under_this_name(self):
        """The La Viña export saved under both names: the copy named Grapevine is not used (La Viña already has its
        file) — one line says so and what Grapevine shows; no line says it is used."""
        first = W.import_archive(self.both(), {}, {})
        prev = {"items": first["items"], **first["extra"]}
        newer = (FIX / "lv.csv").read_bytes().replace(b"Victor R.", b"Victor R")
        folder = self.folder(("aalavina_archive_2026-11-05.csv", newer), ("aagrapevine_archive_2026-11-05.csv", newer))
        res = W.import_archive(folder, {}, prev)
        self.assertTrue(res["ok"])
        files = res["extra"]["files"]
        self.assertEqual((files["gv"]["name"], files["lv"]["name"]), (GV_NAME, "aalavina_archive_2026-11-05.csv"))
        self.assertEqual([w for w in res["stats"]["warnings"] if "aagrapevine_archive_2026-11-05.csv" in w], [
            "aagrapevine_archive_2026-11-05.csv: the name says Grapevine but its links are La Viña's, and La Viña "
            "already has its file (aalavina_archive_2026-11-05.csv) — this file is not used, and Grapevine uses "
            f"{GV_NAME}; export Grapevine again and save it under this name"])
        for n in (GV_NAME, LV_NAME):                 # the old files deleted: one line still says it all
            (folder / n).unlink()
        res = W.import_archive(folder, {}, prev)
        self.assertEqual(res["stats"]["warnings"], [
            "aagrapevine_archive_2026-11-05.csv: the name says Grapevine but its links are La Viña's, and La Viña "
            "already has its file (aalavina_archive_2026-11-05.csv) — this file is not used, and Grapevine keeps the "
            "rows of its last file (13 Texas writers); export Grapevine again and save it under this name"])
        self.assertEqual(res["extra"]["files"]["gv"], first["extra"]["files"]["gv"])

    def test_an_archive_file_in_another_format_is_named(self):
        res = W.import_archive(self.folder((GV_NAME, "gv.csv"), (LV_NAME, "lv.csv"),
                                           ("aagrapevine_archive_2026-11-05.xlsx", b"PK\x03\x04"),
                                           ("aalavina_archive_2026-11-05.csv.numbers", b"x"),
                                           ("~$aagrapevine_archive_2026-11-05.xlsx", b"x"),     # Excel's lock file
                                           ("README.md", b"# notes"), ("notes.txt", b"x")), {}, {})
        self.assertTrue(res["ok"])
        self.assertEqual((res["extra"]["files"]["gv"]["name"], res["extra"]["files"]["lv"]["name"]), (GV_NAME, LV_NAME))
        self.assertEqual([w for w in res["stats"]["warnings"] if "is not read" in w], [
            f"{n} in archive is not read — only .csv files are (in Excel: File → Save As → “CSV UTF-8 (Comma "
            "delimited)”, same name)" for n in ("aagrapevine_archive_2026-11-05.xlsx",
                                                "aalavina_archive_2026-11-05.csv.numbers")])

    def test_no_folder_no_rows(self):
        res = W.import_archive(self.tmp / "nothing-here", {}, {})
        self.assertEqual((res["ok"], res["items"], res["extra"]["files"], res["stats"]["warnings"]), (True, [], {}, []))


# =========================================================================== the module (data/raw)
class Module(Pinned):
    def setUp(self):
        super().setUp()
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        for p in (mock.patch.object(common, "RAW_DIR", self.raw),
                  mock.patch.object(W, "load_config", lambda: {"writers_archive": {"folder": ""}})):
            p.start()
            self.addCleanup(p.stop)
        self.dir = self.both()
        p = mock.patch.object(W, "archive_dir", lambda cfg=None: self.dir)
        p.start()
        self.addCleanup(p.stop)

    def run_main(self, now: str = "2026-10-04T12:00:00Z") -> dict:
        with mock.patch.object(W, "now_iso", return_value=now), mock.patch.object(common, "now_iso", return_value=now):
            W.main([])
        return json.loads((self.raw / "writers_archive.json").read_text(encoding="utf-8"))

    def test_the_same_files_give_the_same_items(self):
        one = self.run_main()
        text1 = json.dumps(one["items"], ensure_ascii=False)
        two = self.run_main("2026-10-05T12:00:00Z")
        self.assertEqual(json.dumps(two["items"], ensure_ascii=False), text1)
        self.assertEqual(two["files"], one["files"], "imported_at stays: the files did not change")
        self.assertEqual(two["files"]["gv"]["imported_at"], "2026-10-04T12:00:00Z")
        self.assertEqual((two["updated"], two["ok"], two["stats"]["changed"], two["stats"]["notes"], two["stats"]["new"]),
                         ("2026-10-05T12:00:00Z", True, False, [], 0))
        self.assertEqual(set(one) - {"items"}, {"source", "updated", "attempted", "ok", "error", "changes", "stats",
                                                "first_harvest", "parser_version", "files"})

    def test_imported_at_moves_only_with_its_file(self):
        self.run_main()
        p = self.dir / LV_NAME
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))          # the owner's copy: CRLF — the same file
        env = self.run_main("2026-10-05T12:00:00Z")
        self.assertEqual(env["files"]["lv"]["imported_at"], "2026-10-04T12:00:00Z")
        p.write_bytes(p.read_bytes().replace(b"Victor R.", b"Victor R"))   # changed contents
        env = self.run_main("2026-10-06T12:00:00Z")
        self.assertEqual(env["files"]["lv"]["imported_at"], "2026-10-06T12:00:00Z")
        self.assertEqual(env["files"]["gv"]["imported_at"], "2026-10-04T12:00:00Z")
        self.assertEqual(env["stats"]["notes"], [f"New archive file used: {LV_NAME} (5 rows, 4 Texas writers)"])
        with mock.patch.object(W, "PARSER_VERSION", W.PARSER_VERSION + 1):
            env = self.run_main("2026-10-07T12:00:00Z")
        self.assertEqual({p: f["imported_at"] for p, f in env["files"].items()},
                         {"gv": "2026-10-07T12:00:00Z", "lv": "2026-10-07T12:00:00Z"}, "a new parser reads both again")

    def test_a_rejected_file_marks_the_source_failed_and_keeps_the_rows(self):
        first = self.run_main()
        (self.dir / "aagrapevine_archive_2026-11-05.csv").write_bytes(b"Link,Title\nhttps://www.aagrapevine.org/x,X\n")
        env = self.run_main("2026-10-05T12:00:00Z")
        self.assertFalse(env["ok"])
        self.assertIn("aagrapevine_archive_2026-11-05.csv: the columns Month, Year, Written By, Location (as "
                      "published), Texas Author? are missing", env["error"])
        self.assertEqual(env["items"], first["items"])
        self.assertEqual(env["updated"], first["updated"], "the last success stays")
        self.assertIn("older archive file still in archive (it stays in use until "
                      f"aagrapevine_archive_2026-11-05.csv is fixed): {GV_NAME}", env["stats"]["warnings"])

    def test_a_story_keeps_the_run_it_first_came_in(self):
        """`first_seen` — /status/ counts the archive's stories found in the last 7 days from it: the run an address
        first came in, kept from run to run (a changed file, a new parser); a newer file's new story gets its own
        run's time."""
        one = self.run_main()
        self.assertEqual({i["first_seen"] for i in one["items"]}, {"2026-10-04T12:00:00Z"})
        newer = (self.dir / GV_NAME).read_bytes().replace(b"A Halloween to Remember", b"A Halloween to Remember!") + (
            b'https://www.aagrapevine.org/magazine/2026/nov/a-new-story,A New Story,No,November,2026,,Lee T.,Tyler,'
            b'Texas,,No,Yes,"Tyler, Texas",\n')
        (self.dir / GV_NAME).unlink()
        (self.dir / "aagrapevine_archive_2026-11-05.csv").write_bytes(newer)
        two = self.run_main("2026-11-05T12:00:00Z")
        seen = {i["key"]: i["first_seen"] for i in two["items"]}
        self.assertEqual(seen.pop(f"{GV}/magazine/2026/nov/a-new-story"), "2026-11-05T12:00:00Z")
        self.assertEqual(set(seen.values()), {"2026-10-04T12:00:00Z"}, "a changed title keeps its day")
        self.assertEqual((two["stats"]["new"], len(two["items"])), (1, 18))
        self.assertEqual(self.run_main("2026-11-06T12:00:00Z")["items"], two["items"], "the same files, the same rows")
        with mock.patch.object(W, "PARSER_VERSION", W.PARSER_VERSION + 1):
            four = self.run_main("2026-11-07T12:00:00Z")
        self.assertEqual(four["files"]["gv"]["imported_at"], "2026-11-07T12:00:00Z")
        self.assertEqual(four["items"], two["items"], "a new parser reads the files again; the days stay")
        c = B.Ctx(offline=True)                       # the archive's row on /status/
        c.raw = {"writers_archive": two}
        c.now_ts = datetime(2026, 11, 6, tzinfo=timezone.utc).timestamp()
        row = next(s for s in B.build_status(c, None, B.I18n(None), {}, False, 0.0)["sources"]
                   if s["source"] == "writers_archive")
        self.assertEqual((row["count"], row["new_7d"]), (18, 1))

    def test_rows_saved_before_first_seen_take_their_files_time(self):
        """An envelope whose rows have no `first_seen` yet (written before they carried it): each row takes its
        file's imported_at — not this run, which would count every story as found this week again."""
        self.run_main()
        p = self.raw / "writers_archive.json"
        env = json.loads(p.read_text(encoding="utf-8"))
        for it in env["items"]:
            del it["first_seen"]
        p.write_text(json.dumps(env), encoding="utf-8")
        env = self.run_main("2026-10-20T12:00:00Z")
        self.assertEqual({i["first_seen"] for i in env["items"]}, {"2026-10-04T12:00:00Z"})

    def test_run_all_marks_nothing_else(self):
        self.run_main()
        self.assertEqual(sorted(p.name for p in self.raw.iterdir()), ["writers_archive.json"])


# =========================================================================== build_data: the site file
def captured(slug: str, title: str, loc: str | None, *, pub: str = "gv", key: str = "2026-10", author: str = "Ann B.",
             status: str = "ok", **ex) -> dict:
    """A raw article of the daily capture (data/raw/articles.json)."""
    base = GV + "/magazine/" + {"2026-10": "2026/oct", "2026-09": "2026/sep", "2026-11": "2026/nov"}.get(key, key) \
        if pub == "gv" else LV + "/revista/septiembre-octubre-2026"
    return {"id": f"{pub}:{key}:{slug}", "source": "grapevine" if pub == "gv" else "lavina", "kind": "article",
            "url": f"{base}/{slug}", "title": title, "summary": ex.pop("summary", ""), "lang": "en" if pub == "gv" else "es",
            "date": f"{key}-01", "first_seen": "2026-09-23T16:34:47Z", "last_seen": None, "image": None, "tags": [],
            "category": pub, "status": status,
            "extra": {"publication": pub, "issue_key": key, "issue_label": ex.pop("issue_label", None), "author": author,
                      "author_location": loc, **ex}}


class SiteBase(Pinned):
    """The fixtures' rows (data/raw/writers_archive.json) and a small capture (data/raw/articles.json) in a Ctx."""

    def ctx(self, articles: list[dict]) -> B.Ctx:
        res = W.import_archive(self.both(), {}, {})
        c = B.Ctx(offline=True)
        c.today_local = date(2026, 10, 4)
        c.raw = {"writers_archive": {"items": res["items"], **res["extra"]},
                 "articles": {"items": articles}}
        return c

    def cols(self, c: B.Ctx) -> list[dict]:
        arts = B.simple(c, "articles", ("article",))
        B.enrich_articles(c, arts)
        return arts

    def capture(self) -> list[dict]:
        return [
            # in both: the capture's title / byline / subtitle win, the file fills the rest
            captured("halloween-remember", "A Halloween to Remember", "Round Rock, Texas", author="Aaron M.",
                     topic="Loneliness", issue_label="October 2026",
                     summary="A sober granddad survives a boozy holiday block party and gets to give the performance "
                             "of a lifetime",
                     subtitle="A sober granddad survives a boozy holiday block party and gets to give the performance "
                              "of a lifetime"),
            # only in the capture (after the files' date): an Area 65 writer, and the rest of Texas
            captured("my-spiritual-gps", "My Spiritual GPS", "Pottsboro, Texas", key="2026-11", author="Jim B.",
                     issue_label="november 2026", topic="Sponsorship", subtitle="A new way to find the road",
                     online_exclusive=True),
            captured("worth-every-step", "Worth Every Step", "Austin, Texas", key="2026-11", author="Carla P."),
            # not shown: elsewhere, a department, gone
            captured("cheyenne-story", "Cheyenne Story", "Cheyenne, Wyoming", key="2026-11"),
            captured("dear-grapevine-november-2026", "Dear Grapevine", "Dallas, Texas", key="2026-11", department=True),
            captured("gone-story", "Gone Story", "Tyler, Texas", key="2026-11", status="gone"),
        ]


class Site(SiteBase):
    """plan_writers_archive + build_writers_archive."""

    def test_csv_and_capture_together(self):
        c = self.ctx(self.capture())
        items = B.plan_writers_archive(c, self.cols(c))
        by = {it["key"]: it for it in items}
        self.assertEqual(len(items), 17 + 2)
        self.assertEqual({it["from"] for it in items if it["key"].endswith("/halloween-remember")}, {"both"})
        gps = by[f"{GV}/magazine/2026/nov/my-spiritual-gps"]
        self.assertEqual((gps["from"], gps["scope"], gps["county"], gps["issue_key"], gps["issue_label"], gps["year"],
                          gps["decade"], gps["theme"], gps["summary"], gps["audio"], gps["online_exclusive"]),
                         ("capture", "neta65", "Grayson", "2026-11", "November 2026", 2026, 2020, "Sponsorship",
                          "A new way to find the road", False, True))
        self.assertEqual(gps["id"], "wa:" + common.short_hash(gps["key"], 12))
        self.assertEqual(by[f"{GV}/magazine/2026/nov/worth-every-step"]["scope"], "texas")
        for slug in ("cheyenne-story", "dear-grapevine-november-2026", "gone-story"):
            self.assertNotIn(f"{GV}/magazine/2026/nov/{slug}", by, slug)

    def test_a_captured_story_of_any_age_joins(self):
        """SPEC D3: every captured Texas story of ANY age — the archive keeps growing between two files — while the
        spotlight lists only its last 60/90 days."""
        c = self.ctx(self.capture() + [captured("old-story", "An Old Story", "Tyler, Texas", key="2019-03",
                                                author="Old W.")])
        arts = self.cols(c)
        it = next(i for i in B.plan_writers_archive(c, arts) if i["key"] == f"{GV}/magazine/2019-03/old-story")
        self.assertEqual((it["from"], it["scope"], it["issue_key"], it["issue_label"], it["year"], it["decade"]),
                         ("capture", "neta65", "2019-03", "March 2019", 2019, 2010))
        self.assertFalse(any(a["url"].endswith("/old-story") for a in B.plan_spotlight(c, arts)[0]),
                         "older than the spotlight's window")

    def test_the_capture_wins_and_the_file_fills(self):
        arts = self.capture()
        hw = arts[0]
        hw["title"] = "A Halloween to Remember!"                       # the capture's own title
        hw["extra"].update(author="Aaron M", author_location="Round Rock, Tex.", subtitle="", topic=None,
                           issue_theme="Loneliness")
        c = self.ctx(arts)
        it = next(i for i in B.plan_writers_archive(c, self.cols(c)) if i["key"].endswith("/halloween-remember"))
        self.assertEqual((it["title"], it["writers"][0]["name"], it["writers"][0]["place"]),
                         ("A Halloween to Remember!", "Aaron M", "Round Rock, Tex."))
        self.assertEqual(it["summary"], "A sober granddad survives a boozy holiday block party and gets to give the "
                                        "performance of a lifetime", "an empty subtitle: the file's brief")
        self.assertEqual((it["theme"], it["audio"], it["issue_label"], it["from"]),
                         ("Loneliness", True, "October 2026", "both"))
        self.assertEqual((it["writers"][0]["geo"]["scope"], it["county"]), ("texas", "Williamson"))

    def test_a_letters_column_keeps_its_writers_and_the_best_place(self):
        c = self.ctx([])
        items = {i["key"]: i for i in B.plan_writers_archive(c, [])}
        letters = items[f"{GV}/magazine/2022/may/dear-grapevine-may-2022"]
        self.assertEqual([(w["name"], w["geo"]["scope"]) for w in letters["writers"]],
                         [("Mike K.", "neta65"), ("Jim O.", "texas"), ("Jim B.", "texas")])
        self.assertEqual((letters["scope"], letters["county"], letters["column"]), ("neta65", "Anderson", True))
        typo = items[f"{GV}/magazine/2014/jun/long-weekend"]
        self.assertEqual((typo["writers"][0]["place"], typo["writers"][0]["geo"]["label_en"], typo["county"]),
                         ("Forth Worth, Texas", "Fort Worth, Texas", "Tarrant"), "printed as printed, labelled right")
        self.assertEqual(items[f"{LV}/revista/marzo-abril-2019/que-le-pasaba"]["scope"], "neta65")
        self.assertEqual(items[f"{GV}/magazine/1958/sep/delegates-corner-0"]["scope"], "neta65")

    def test_a_county_list_change_shows_at_once(self):
        c = self.ctx([])
        before = {i["key"]: i["scope"] for i in B.plan_writers_archive(c, [])}
        with mock.patch.object(geo, "_neta65_cached", lambda: AREA65 - {"denton"}):
            after = {i["key"]: i["scope"] for i in B.plan_writers_archive(c, [])}
        key = f"{GV}/magazine/1991/oct/what-and-who-we-really-are"
        self.assertEqual((before[key], after[key]), ("neta65", "texas"))

    def test_a_row_the_file_calls_texas_stays_texas(self):
        c = self.ctx([])
        rows = c.raw["writers_archive"]["items"]
        rows[0]["writers"] = [{"name": "Ann", "place": "Somewhere", "city": None, "state": None, "anonymous": False}]
        it = next(i for i in B.plan_writers_archive(c, []) if i["key"] == rows[0]["key"])
        self.assertEqual((it["scope"], it["county"]), ("texas", None))

    def test_the_site_file(self):
        c = self.ctx(self.capture())
        arts = self.cols(c)
        doc = B.build_writers_archive(c, B.plan_writers_archive(c, arts), B.I18n(None), "2026-10-04T12:00:00Z")
        self.assertEqual(list(doc), ["updated", "fixture", "files", "since", "counts", "items"])
        self.assertEqual(doc["files"]["gv"], {"name": GV_NAME, "name_date": "2026-10-04", "rows": 17, "texas_rows": 14,
                                              "imported_at": c.raw["writers_archive"]["files"]["gv"]["imported_at"]})
        self.assertEqual(doc["since"], {"gv": 1955, "lv": 2018}, "the files' first year (all rows, not only Texas)")
        self.assertEqual(doc["counts"], {"neta65": {"all": 12, "gv": 9, "lv": 3}, "texas": {"all": 19, "gv": 15, "lv": 4}})
        it = doc["items"][0]
        self.assertEqual(list(it), ["id", "key", "url", "pub", "lang", "title", "summary", "issue_key", "issue_label",
                                    "year", "decade", "theme", "writers", "scope", "county", "audio",
                                    "online_exclusive", "column", "from"], "no i18n while nothing is translated")
        self.assertEqual(list(it["writers"][0]), ["name", "anonymous", "place", "geo"])
        self.assertEqual(list(it["writers"][0]["geo"]), list(B.WA_GEO_KEYS))
        self.assertNotIn("_cap", json.dumps(doc))
        keys = [(i["issue_key"] or "", B.fold(i["title"]), i["key"]) for i in doc["items"]]
        dated = [k for k in keys if k[0]]
        self.assertEqual([k[0] for k in dated], sorted((k[0] for k in dated), reverse=True), "newest issue first")
        self.assertEqual(keys[-1][0], "", "the undated story last")
        nov = [k[1] for k in keys if k[0] == "2026-11"]
        self.assertEqual(nov, sorted(nov), "then by title")
        st = B.writers_archive_status(doc)
        self.assertEqual(st, {"files": doc["files"], "items": 19, "neta65": 12, "texas": 19, "csv_only": 16,
                              "capture_only": 2, "both": 1})
        empty = B.empty_writers_archive("x")
        self.assertEqual((empty["items"], empty["counts"]["texas"]), ([], {"all": 0, "gv": 0, "lv": 0}))

    def test_the_same_input_the_same_file(self):
        c = self.ctx(self.capture())
        arts = self.cols(c)
        one = B.build_writers_archive(c, B.plan_writers_archive(c, arts), B.I18n(None), "t")
        two = B.build_writers_archive(c, B.plan_writers_archive(c, arts), B.I18n(None), "t")
        self.assertEqual(json.dumps(one, ensure_ascii=False), json.dumps(two, ensure_ascii=False))


class FakeTranslator:
    """Every text translated: "<es> …" / "<en> …" (machine)."""
    overrides = None

    def __init__(self):
        self.asked: list[str] = []

    def translate(self, texts, src, tgt):
        self.asked += list(texts)
        return [(f"<{tgt}> {t}", True) for t in texts]


class Translations(SiteBase):
    def test_the_archive_is_translated_last(self):
        c = self.ctx(self.capture())
        arts = self.cols(c)
        archive = B.plan_writers_archive(c, arts)
        i18n = B.I18n(None)
        B.plan_translations(c, {"articles": arts}, set(), i18n, archive)
        tier = {k[3]: prio for k, prio in i18n.jobs.items()}
        self.assertEqual(tier["What and Who We Really Are"], (5, -B.ts("1991-10-01")))
        self.assertEqual(tier['The "we" of AA is us'], (6, -B.ts("1991-10-01")))
        self.assertEqual(tier["True North"], (5, float("inf")), "an undated story after every dated one")
        self.assertLess(tier["You Let Me In"], tier["Rough Road"], "newest issue first")
        self.assertLess(tier["Rough Road"], tier["True North"])
        self.assertLessEqual(tier["A Halloween to Remember"][0], 4, "the capture's title: asked for with the articles")
        self.assertLessEqual(tier["My Spiritual GPS"][0], 4)
        lowest = max(p[0] for k, p in i18n.jobs.items() if k[3] not in {i["title"] for i in archive}
                     and k[3] not in {i["summary"] for i in archive})
        self.assertLess(lowest, 5, "every other text comes first")

    def test_a_captured_story_shows_the_captures_translation(self):
        c = self.ctx(self.capture())
        arts = self.cols(c)
        tr = FakeTranslator()
        i18n = B.I18n(tr)
        B.plan_translations(c, {"articles": arts}, set(), i18n, B.plan_writers_archive(c, arts))
        i18n.run()
        for it in arts:
            i18n.apply(it)
        doc = B.build_writers_archive(c, B.plan_writers_archive(c, arts), i18n, "t")
        by = {i["key"]: i for i in doc["items"]}
        cap = next(a for a in arts if a["url"].endswith("/halloween-remember"))
        hw = by[W.url_key(cap["url"])]
        self.assertEqual(hw["i18n"]["title"], cap["i18n"]["title"])
        self.assertEqual(hw["i18n"]["summary"], cap["i18n"]["summary"])
        self.assertEqual(hw["machine"], ["es"])
        self.assertEqual(tr.asked.count("A Halloween to Remember"), 1, "translated once, for both files")
        lv = by[f"{LV}/revista/septiembre-octubre-2026/el-despertar-del-espiritu"]
        self.assertEqual(lv["i18n"]["title"], {"en": B.T.title_case_en("<en> El despertar del espíritu"),
                                               "es": "El despertar del espíritu"},
                         "Spanish → English titles in Title Case, as for the capture")
        self.assertEqual(lv["machine"], ["en"])
        self.assertEqual(list(lv)[:9], ["id", "key", "url", "pub", "lang", "title", "summary", "i18n", "machine"])
        no_brief = by[f"{GV}/magazine/2014/jun/long-weekend"]
        self.assertEqual(set(no_brief["i18n"]), {"title"}, "only fields that have a translation")


class Status(Pinned):
    def test_the_source_row_comes_after_the_articles(self):
        names = [s[0] for s in B.SOURCES]
        self.assertEqual(names[names.index("articles") + 1], "writers_archive")
        self.assertEqual(B.SOURCES[names.index("writers_archive")][1:],
                         ("Texas writers archive (content/archive)", "Archivo de escritores de Texas (content/archive)"))

    def test_a_whole_build(self):
        raw = self.tmp / "raw"
        raw.mkdir()
        out = self.tmp / "site"
        folder = self.both()
        real_translator = B.T.Translator
        arts = [captured("halloween-remember", "A Halloween to Remember", "Round Rock, Texas", author="Aaron M."),
                captured("my-spiritual-gps", "My Spiritual GPS", "Pottsboro, Texas", key="2026-11", author="Jim B."),
                # only the capture has it, from an issue years old: any age joins the archive (SPEC D3) — B.main
                # hands plan_writers_archive every captured story, never the spotlight's 60/90 days
                captured("old-story", "An Old Story", "Tyler, Texas", key="2019-03", author="Old W.")]
        with mock.patch.object(common, "RAW_DIR", raw), mock.patch.object(B, "RAW_DIR", raw), \
                mock.patch.object(W, "archive_dir", lambda cfg=None: folder):
            W.main([])
            (raw / "articles.json").write_text(json.dumps({"source": "articles", "ok": True, "items": arts}),
                                               encoding="utf-8")
            with mock.patch.object(B, "STATE_DIR", self.tmp / "state"), \
                    mock.patch.object(B.T, "Translator", lambda **kw: real_translator(cache=False, use_model=False)), \
                    mock.patch.object(B.T, "_DEFAULT", None):
                self.assertEqual(B.main(["--out", str(out), "--offline", "--no-translate", "--no-prune"]), 0)
        doc = json.loads((out / "writers_archive.json").read_text(encoding="utf-8"))
        st = json.loads((out / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(len(doc["items"]), 19)
        self.assertIn(f"{GV}/magazine/2019-03/old-story", {i["key"] for i in doc["items"]})
        self.assertEqual(st["writers_archive"], {"files": doc["files"], "items": 19, "neta65": 13, "texas": 19,
                                                 "csv_only": 16, "capture_only": 2, "both": 1})
        self.assertEqual(st["counts"]["writers_archive"], 19)
        row = next(s for s in st["sources"] if s["source"] == "writers_archive")
        self.assertEqual((row["ok"], row["count"], row["stats"]["texas"]), (True, 17, 17))
        self.assertEqual(row["new_7d"], 17, "the rows came in with this run: found this week (first_seen)")
        self.assertIsInstance(st["reminders"], list)
        spot = json.loads((out / "spotlight.json").read_text(encoding="utf-8"))
        self.assertFalse(any("wa:" in i["id"] for i in spot["items"]), "the archive never goes into spotlight.json")
        self.assertEqual(len(json.loads((out / "articles.json").read_text(encoding="utf-8"))["items"]), 3)


# =========================================================================== reminders
class Reminders(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="gv-rem-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "config").mkdir()
        (self.root / "content" / "events").mkdir(parents=True)
        self.write("config/carry.yml", 'tips:\n' + "".join(f'  "{m}":\n    - {{ way: newcomer }}\n' for m in (
            "2026-09", "2026-10", "2027-08", "2027-09")) + '  "2027-10": []\n')
        self.write("config/expenses.yml", 'panels:\n  - id: "77"\n    from: "2027-01-01"\n    to: "2028-12-31"\n')
        self.write("config/orientation.yml", 'panel:\n  number: 77\n  starts: "2027-01"\n')
        self.write("content/events/2027-03-19-neta65-spring-assembly.md",
                   '---\ntitle: "NETA 65 Spring Assembly 2027"\nstart: 2027-03-19\nend: 2027-03-21\n---\nText\n')
        self.write("content/events/2027-06-25-neta65-summer.md",
                   '---\ntitle: "Summer weekend"\ntitle_es: "Asamblea de Verano"\nstart: 2027-06-25\n---\n')
        self.write("content/events/2027-12-01-workshop.md", '---\ntitle: "Writing Workshop"\nstart: 2027-12-01\n---\n')
        self.write("content/events/README.md", "# Manual events — 2030-01-01 assembly example\n")

    def write(self, rel: str, text: str) -> None:
        (self.root / rel).write_text(text, encoding="utf-8")

    def check(self, today: str, cfg: dict | None = None) -> dict[str, dict]:
        c = B.Ctx(offline=True)
        c.today_local = date.fromisoformat(today)
        c.cfg = cfg if cfg is not None else {
            "recurring_events": [{"key": "lv-monthly-workshop", "skip_dates": ["2026-11-26", "2026-12-24"]},
                                 {"key": "citywide-dallas", "skip_dates": []}],
            "price_changes": [{"key": "2027-01", "effective": "2027-01-01", "notice_until": "2027-01-31",
                               "yearly": {"gv": {"print": 39.0}}}]}
        return {r["id"]: r for r in B.reminders(c, self.root)}

    def test_what_is_due_on_a_day(self):
        got = self.check("2026-10-04")
        self.assertEqual(sorted(got), ["carry-tips", "skip-dates:lv-monthly-workshop"])
        self.assertEqual(got["carry-tips"], {
            "id": "carry-tips", "file": "config/carry.yml", "due": "2027-10",
            "message": "config/carry.yml has monthly tips only through 2027-09; the /monthly/ pages look 12 months ahead "
                       "— add tips for the next months."})
        self.assertEqual(got["skip-dates:lv-monthly-workshop"], {
            "id": "skip-dates:lv-monthly-workshop", "file": "config/site.yml", "due": "2026-12-24",
            "message": "config/site.yml recurring_events: the last skip date of “lv-monthly-workshop” is 2026-12-24 — "
                       "add next year's skip dates for lv-monthly-workshop."})

    def test_nothing_due(self):
        self.write("config/carry.yml", 'tips:\n  "2027-10":\n    - { way: newcomer }\n')
        cfg = {"recurring_events": [{"key": "lv", "skip_dates": ["2027-11-25", "2027-12-23"]}],
               "price_changes": [{"key": "2027-01", "effective": "2027-01-01", "notice_until": "2027-01-31",
                                  "books_more": 2.0}]}
        self.assertEqual(self.check("2026-10-04", cfg), {})

    def test_the_panels(self):
        got = self.check("2028-11-01")
        self.assertEqual(got["expenses-panel"]["message"],
                         "config/expenses.yml: the last service panel (Panel 77) ends 2028-12-31 — add the next panel.")
        self.assertEqual(got["expenses-panel"]["due"], "2028-12-31")
        self.assertNotIn("orientation-panel", got, "Panel 77 runs until 2028-12-31")
        got = self.check("2029-01-02")
        self.assertIn("ended 2028-12-31", got["expenses-panel"]["message"])
        self.assertEqual(got["orientation-panel"], {
            "id": "orientation-panel", "file": "config/orientation.yml", "due": "2028-12-31",
            "message": "config/orientation.yml still names Panel 77 (from 2027-01), which ended 2028-12-31 — "
                       "update the panel."})
        self.assertNotIn("expenses-panel", self.check("2028-10-01"), "more than 90 days ahead")

    def test_the_assemblies(self):
        self.assertNotIn("neta65-assemblies", self.check("2027-04-01"), "the summer one (asamblea) is 85 days away")
        got = self.check("2027-05-01")
        self.assertEqual(got["neta65-assemblies"], {
            "id": "neta65-assemblies", "file": "content/events/", "due": "2027-06-25",
            "message": "content/events: the last NETA 65 assembly listed is on 2027-06-25 — add the next NETA 65 "
                       "assemblies."})
        self.assertIn("neta65-assemblies", self.check("2027-08-01"), "also once it is past")

    def test_the_price_changes(self):
        got = self.check("2027-02-01")
        self.assertEqual(got["price-change:2027-01"]["message"],
                         "config/site.yml: the price_changes block for 2027-01 can be removed — its notice ended "
                         "2027-01-31 (keep it until the stores show the new prices).")
        self.assertNotIn("price-change:2027-01", self.check("2027-01-31"))

    def test_a_broken_file_never_stops_the_build(self):
        self.write("config/carry.yml", "tips: [unclosed\n")
        (self.root / "config" / "expenses.yml").unlink()
        self.write("content/events/2027-09-17-broken.md", "---\ntitle: Fall Assembly\nstart: [\n---\n")
        with self.assertLogs("build_data", "WARNING") as logs:
            got = self.check("2026-10-04", {"recurring_events": "not a list", "price_changes": "nonsense"})
        self.assertEqual(got, {})
        self.assertTrue(any("_carry_reminders" in m for m in logs.output))

    def test_the_real_settings_can_be_read(self):
        c = B.Ctx(offline=True)
        c.today_local = date(2026, 10, 4)
        with self.assertNoLogs("build_data", "WARNING"):
            got = B.reminders(c)
        self.assertIsInstance(got, list)
        for r in got:
            self.assertEqual(list(r), ["id", "file", "message", "due"])


# =========================================================================== the real files (when present)
class RealFiles(unittest.TestCase):
    """content/archive as the owner left it, read with the whole Area 65 county list pinned (tests/test_spotlight.py:
    the chair may edit config/site.yml spotlight.neta65_counties). While the files in use are the 2026-10-04 pair —
    by name and normalised hash — the headline numbers are exact: 1,263 Texas rows read (Grapevine 819, La Viña
    444), 1,261 stories once the 2 listed twice are kept once, Area 65 376; a change of the parser or of the place
    rules that moves them shows here. Any newer file only has to make sense: the owner replaces the files, and the
    import's own checks (columns, size) decide whether it is used."""

    SNAPSHOT = {"gv": ("aagrapevine_archive_2026-10-04.csv",
                       "5a3f1beb90c8a8902c62446d51ddffbfb11bc3a7dd32e559786dada05a57e919"),
                "lv": ("aalavina_archive_2026-10-04.csv",
                       "c8698ad5d03ed8365de0d15c90acbb4345fde13b0ead2d621d45deed5d74873a")}

    def setUp(self):
        p = mock.patch.object(geo, "_neta65_cached", _all_area65)
        p.start()
        self.addCleanup(p.stop)

    def test_the_headline_numbers(self):
        folder = W.archive_dir(common.load_config())
        if not any(W.parse_name(p.name) for p in (folder.iterdir() if folder.is_dir() else [])):
            self.skipTest("no archive file in content/archive")
        res = W.import_archive(folder, common.load_config(), {})
        files, st = res["extra"]["files"], res["stats"]
        self.assertTrue(res["ok"], res["error"])
        self.assertTrue(files, "a file in use")
        for pub, f in files.items():               # what every good export gives
            self.assertGreater(f["texas_rows"], 0, pub)
            self.assertLessEqual(f["texas_rows"], f["rows"], pub)
            self.assertIsInstance(f["first_year"], int, pub)
            self.assertGreaterEqual(f["first_year"], {"gv": 1944, "lv": 1996}[pub], f"{pub}: before the magazine began")
        self.assertLessEqual(st["neta65"], st["texas"])
        self.assertLessEqual(st["texas"], sum(f["texas_rows"] for f in files.values()))
        if {p: (f["name"], f["sha256"]) for p, f in files.items()} != self.SNAPSHOT:
            return                                 # a newer file: its numbers are its own
        self.assertEqual((files["gv"]["texas_rows"], files["lv"]["texas_rows"]), (819, 444))
        self.assertEqual((st["texas"], st["neta65"]), (1261, 376))
        self.assertEqual((files["gv"]["first_year"], files["lv"]["first_year"]), (1944, 1996))


if __name__ == "__main__":
    unittest.main()
