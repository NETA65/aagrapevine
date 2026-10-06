"""A bad day at a source must not wipe or hide content (offline: data/raw, data/site, data/state and the
translation cache are temporary folders; Drive, the downloads and the model server are fakes).

  * MassDropGuard   — common.save_raw: a source that says "ok" but suddenly lists far fewer items (zero, or more
                      than half of DROP_GUARD_MIN or more) keeps them for one run, marked `held`; the next run that
                      still misses those same items accepts it (items that vanish only then are held in turn); a
                      recovery clears it; new items still come in; "gone" items count and are put back once; failed
                      runs keep the mark; exempt sources (DROP_GUARD_EXEMPT, drop_guard=, a source switched off) are
                      not held; `changes` = this run's {"added", "removed", "held"}.
  * GuardChoices    — every source that writes a raw file is guarded or exempt on purpose (the table and its
                      reasons).
  * DriveEmptyFolders — drive_listing + drive.main: a folder (or the whole tree) that suddenly looks empty keeps
                      its files (held, `empty_folders`) until the next update finds it empty too; then they go,
                      not held again.
  * DrivePrivateNames — data/raw/drive.json counts what is not published, never names it.
  * DriveDownloads  — downloads stop at their byte cap (Drive texts, an .ics feed); a .docx is unzipped with a
                      size and a part-count cap (zip-bomb safe).
  * TranslationSafety — an unreadable cache.json is moved aside and reported, never silently replaced (nor
                      overwritten when it cannot be moved); a model whose checksum is not the pinned one is not
                      installed — that direction is not translated, the run goes on, the reason is reported.
  * WholeBuilds     — build_data.main: an unreadable raw file keeps the last build's data for its source (never an
                      empty section) and marks it failed on /status/; status.json carries `changes` and `held`;
                      files whose content did not change keep their `updated`; the cache is pruned while a
                      settings note is open, not while a raw file cannot be read.
  * StatusPage      — /status/ and /es/status/ show a source on hold, a source's notes and translation problems.

    python -m unittest tests.test_sync_safety -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import drive as D  # noqa: E402
from scripts.sync import translate as T  # noqa: E402
from scripts.sync.drive_listing import FOLDER_MIME, DriveLister, Entry, Listing  # noqa: E402

T0 = "2026-10-06T12:00:00Z"


def items(n: int, prefix: str = "x", start: int = 1, **kw) -> list[dict]:
    return [{"id": f"{prefix}:{i}", "title": f"Item {i}", "first_seen": "2026-01-01T00:00:00Z", **kw}
            for i in range(start, start + n)]


class TempRaw(unittest.TestCase):
    """data/raw of its own for each test (load_raw / save_raw read common.RAW_DIR when called)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-safety-"))
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        for p in (mock.patch.object(common, "RAW_DIR", self.raw), mock.patch.object(B, "RAW_DIR", self.raw)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def env(self, source: str) -> dict:
        return json.loads((self.raw / f"{source}.json").read_text(encoding="utf-8"))

    def save(self, source: str, its: list[dict], at: str = T0, **kw) -> dict:
        with mock.patch.object(common, "now_iso", return_value=at):
            common.save_raw(source, its, **kw)
        return self.env(source)

    @staticmethod
    def ids(env: dict, live_only: bool = True) -> list[str]:
        return sorted(i["id"] for i in env["items"] if not live_only or i.get("status", "ok") != "gone")


# =========================================================================== the mass-drop guard
class MassDropGuard(TempRaw):
    def test_a_drop_to_zero_is_held_once_then_accepted(self):
        self.save("podcasts", items(4))
        env = self.save("podcasts", [], at="2026-10-06T18:00:00Z")
        self.assertTrue(env["ok"])
        self.assertEqual(self.ids(env), ["x:1", "x:2", "x:3", "x:4"], "the items stay on the site")
        self.assertEqual(env["held"], {"since": "2026-10-06T18:00:00Z", "kept": 4, "previous": 4, "found": 0,
                                       "drop": True, "examples": ["Item 1", "Item 2", "Item 3", "Item 4"],
                                       "ids": ["x:1", "x:2", "x:3", "x:4"]})
        self.assertEqual(env["changes"], {"added": 0, "removed": 0, "held": 4})
        env = self.save("podcasts", [], at="2026-10-07T06:00:00Z")      # the next run sees the same drop
        self.assertEqual(env["items"], [])
        self.assertNotIn("held", env)
        self.assertEqual(env["changes"], {"added": 0, "removed": 4, "held": 0, "confirmed": "2026-10-06T18:00:00Z"})

    def test_more_than_half_of_a_big_list(self):
        self.save("youtube", items(20))
        env = self.save("youtube", items(9))            # 11 of 20 gone: more than half
        self.assertEqual(len(self.ids(env)), 20)
        self.assertEqual((env["held"]["kept"], env["held"]["previous"], env["held"]["found"]), (11, 20, 9))
        env = self.save("youtube", items(20))           # back the next run: nothing to confirm
        self.assertNotIn("held", env)
        self.assertEqual(env["changes"], {"added": 0, "removed": 0, "held": 0})
        env = self.save("youtube", items(10))           # exactly half: an ordinary run
        self.assertNotIn("held", env)
        self.assertEqual(env["changes"]["removed"], 10)

    def test_small_lists_only_for_a_drop_to_zero(self):
        small = common.DROP_GUARD_MIN - 1
        self.save("weekly_open", items(small))
        env = self.save("weekly_open", items(1))        # 8 of 9 gone, but 9 is below DROP_GUARD_MIN
        self.assertEqual((len(env["items"]), "held" in env, env["changes"]["removed"]), (1, False, small - 1))
        self.assertTrue(common.is_mass_drop(2, 0))
        self.assertFalse(common.is_mass_drop(0, 0), "nothing before: nothing dropped")
        self.assertTrue(common.is_mass_drop(10, 4))
        self.assertFalse(common.is_mass_drop(10, 5))

    def test_new_items_of_a_held_run_still_come_in(self):
        self.save("shop", items(12))
        env = self.save("shop", items(2, start=50))
        self.assertEqual(len(env["items"]), 14)
        self.assertEqual(env["changes"], {"added": 2, "removed": 0, "held": 12})

    def test_items_marked_gone_count_and_come_back_live(self):
        self.save("articles", items(12))
        marked = items(12)
        for it in marked[:8]:
            it["status"] = "gone"
        env = self.save("articles", marked)
        self.assertEqual(len(self.ids(env)), 12, "the 8 'gone' ones are put back as they were")
        self.assertEqual(self.ids(env, live_only=False), self.ids(env), "each item once (the 'gone' copy replaced)")
        self.assertEqual(env["held"]["kept"], 8)

    def test_only_the_same_drop_is_accepted(self):
        self.save("pdfs", items(20))
        env = self.save("pdfs", items(8), at="2026-10-06T18:00:00Z")               # 12 of 20 missing: held
        self.assertEqual((env["held"]["kept"], len(env["held"]["ids"])), (12, 12))
        # the next run finds nothing at all: the 12 still missing go (the drop is confirmed), but the 8 found last
        # time and missing only now are a new drop of their own — held back in turn
        env = self.save("pdfs", [], at="2026-10-07T06:00:00Z")
        self.assertEqual(self.ids(env), sorted(f"x:{i}" for i in range(1, 9)))
        self.assertEqual(env["changes"], {"added": 0, "removed": 12, "held": 8, "confirmed": "2026-10-06T18:00:00Z"})
        self.assertEqual((env["held"]["since"], env["held"]["previous"], env["held"]["found"]),
                         ("2026-10-07T06:00:00Z", 8, 0))
        env = self.save("pdfs", [], at="2026-10-07T12:00:00Z")                     # still nothing: now they go
        self.assertEqual((env["items"], "held" in env), ([], False))
        self.assertEqual(env["changes"], {"added": 0, "removed": 8, "held": 0, "confirmed": "2026-10-07T06:00:00Z"})
        # held items still missing while new ones arrive (no mass drop any more): their removal is confirmed too
        self.save("pdfs", items(20, "y"))
        self.save("pdfs", items(8, "y"), at="2026-10-08T06:00:00Z")
        env = self.save("pdfs", [*items(8, "y"), *items(5, "z")], at="2026-10-08T12:00:00Z")
        self.assertEqual((len(env["items"]), "held" in env), (13, False))
        self.assertEqual(env["changes"], {"added": 5, "removed": 12, "held": 0, "confirmed": "2026-10-08T06:00:00Z"})

    def test_a_failed_run_keeps_the_mark_and_extras_never_override_it(self):
        self.save("shop", items(3))
        self.save("shop", [], at="2026-10-06T18:00:00Z")
        env = self.save("shop", [], ok=False, error="site down", at="2026-10-06T20:00:00Z",
                        extra={"held": None, "changes": {"added": 99}, "listings": [1]})
        self.assertFalse(env["ok"])
        self.assertEqual(env["held"]["since"], "2026-10-06T18:00:00Z", "a failed run saw nothing: still held")
        self.assertEqual(env["changes"], {"added": 0, "removed": 0, "held": 3})
        self.assertEqual(env["listings"], [1])
        env = self.save("shop", [], at="2026-10-07T06:00:00Z")           # the next run that sees it accepts it
        self.assertEqual((env["items"], env["changes"]["confirmed"]), ([], "2026-10-06T18:00:00Z"))

    def test_exempt_sources_and_the_switches(self):
        for source in common.DROP_GUARD_EXEMPT:
            with self.subTest(source=source):
                self.save(source, items(12))
                env = self.save(source, [])
                self.assertEqual((env["items"], "held" in env, env["changes"]["removed"]), ([], False, 12))
        self.save("youtube", items(12))
        self.assertEqual(self.save("youtube", [], drop_guard=False)["items"], [], "drop_guard=False")
        self.save("events_external", items(12))
        self.assertEqual(len(self.save("events_external", [], drop_guard=True)["items"]), 12, "drop_guard=True")
        self.save("meetings", items(12))
        env = self.save("meetings", [], stats={"disabled": True})        # meetings.enabled: false
        self.assertEqual((env["items"], "held" in env), ([], False))

    def test_a_module_held_list_and_its_confirmation(self):
        self.save("drive", items(6))
        env = self.save("drive", items(6), unconfirmed=["x:5", "x:6", "nope"])
        self.assertEqual((env["held"]["kept"], env["held"]["drop"], env["held"]["found"]), (2, False, 4))
        self.assertEqual(env["held"]["examples"], ["Item 5", "Item 6"])
        env = self.save("drive", items(4), confirmed=["x:5", "x:6"])
        self.assertNotIn("held", env)
        self.assertEqual(env["changes"], {"added": 0, "removed": 2, "held": 0, "confirmed": T0})
        # confirmed removals never count as a suspicious drop
        self.save("drive", items(12))
        env = self.save("drive", items(2), confirmed=[f"x:{i}" for i in range(3, 13)])
        self.assertEqual((len(env["items"]), "held" in env), (2, False))

    def test_changes_of_an_ordinary_run(self):
        env = self.save("podcasts", items(3))
        self.assertEqual(env["changes"], {"added": 3, "removed": 0, "held": 0})
        env = self.save("podcasts", items(3, start=2))
        self.assertEqual(env["changes"], {"added": 1, "removed": 1, "held": 0})
        self.assertEqual(list(env)[:7], ["source", "updated", "attempted", "ok", "error", "changes", "stats"])


class GuardChoices(unittest.TestCase):
    """Every module that writes a raw file was looked at: guarded unless its list shrinks on purpose."""

    def test_the_exempt_sources(self):
        self.assertEqual(set(common.DROP_GUARD_EXEMPT),
                         {"announcements", "manual_events", "events_external", "editorial", "writers_archive",
                          "instagram"})
        names = {n for n, *_ in B.SOURCES}
        for source, why in common.DROP_GUARD_EXEMPT.items():
            self.assertIn(source, names)
            self.assertGreater(len(why), 30, source)

    def test_every_writer_of_a_raw_file_is_a_known_source(self):
        names = {n for n, *_ in B.SOURCES}
        for path in sorted((ROOT / "scripts" / "sync").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r'\bSOURCE\s*=\s*"([a-z_]+)"', text):
                self.assertIn(m.group(1), names, path.name)
            for m in re.finditer(r'save_raw\("([a-z_]+)"', text):
                self.assertIn(m.group(1), names, path.name)


# =========================================================================== Drive: a folder that looks empty
def file(fid: str, name: str, mime: str = "application/pdf") -> Entry:
    return Entry(fid, name, mime)


def folder(fid: str, name: str) -> Entry:
    return Entry(fid, name, FOLDER_MIME, is_folder=True)


def tree() -> dict[str, list[Entry] | None]:
    return {
        "ROOT": [folder("P77", "2027-2028_Panel77_GVLV"), folder("P75", "2025-2026_Panel75_GVLV"),
                 folder("LOOSE", "flyers"), file("form1", "40th Annual Secret Gathering Signup",
                                                 "application/vnd.google-apps.form")],
        "P77": [folder("NOTES", "notes"), folder("FLY", "flyers"), folder("PRIV", "Private planning")],
        "NOTES": [file(f"n{i}", f"2027-01-{10 + i} Minutes {i}.pdf") for i in range(1, 7)]
        + [folder("DEEP", "Sub Secret Drafts")],
        "FLY": [file(f"f{i}", f"Flyer {i}.pdf") for i in range(1, 4)],
        "PRIV": None,                                   # not shared publicly
        "DEEP": [file("d1", "Hidden.pdf")],
    }


class DriveTempRaw(TempRaw):
    def run_drive(self, t: dict, at: str = T0) -> dict:
        class TreeLister(DriveLister):
            def __init__(self, **kw):
                kw.pop("use_api", None)
                super().__init__(use_api=False, **kw)

            def _list(self, fid):
                entries = t.get(fid)
                if entries is None:
                    return Listing(False, error="not found or not shared publicly (HTTP 404)")
                return Listing(True, [Entry(**vars(e)) for e in entries], title=fid)

        cfg = {"drive": {"root_folder_id": "ROOT", "min_panel": 77}}
        with mock.patch.object(D, "DriveLister", TreeLister), mock.patch.object(D, "load_config", lambda: cfg), \
                mock.patch.object(D, "now_iso", return_value=at), mock.patch.object(common, "now_iso", return_value=at):
            D.main(["--max-depth", "1"])
        return self.env("drive")


class DriveEmptyFolders(DriveTempRaw):
    def test_a_folder_that_looks_empty(self):
        t = tree()
        first = self.run_drive(t)
        self.assertEqual(len(first["items"]), 9)
        t["FLY"] = []
        env = self.run_drive(t, "2026-10-06T18:00:00Z")
        self.assertEqual(len(env["items"]), 9, "the three flyers stay")
        self.assertEqual((env["held"]["kept"], env["held"]["drop"]), (3, False))
        self.assertEqual(env["empty_folders"], {"FLY": "2026-10-06T18:00:00Z"})
        self.assertEqual(env["stats"]["unconfirmed_folders"], 1)
        self.assertTrue(any("looked empty" in w for w in env["stats"]["warnings"]))
        env = self.run_drive(t, "2026-10-07T06:00:00Z")                 # still empty: they go
        self.assertEqual(len(env["items"]), 6)
        self.assertNotIn("held", env)
        self.assertNotIn("empty_folders", env)
        self.assertEqual(env["changes"], {"added": 0, "removed": 3, "held": 0, "confirmed": "2026-10-06T18:00:00Z"})

    def test_a_folder_that_comes_back(self):
        t = tree()
        self.run_drive(t)
        t["FLY"] = []
        self.run_drive(t, "2026-10-06T18:00:00Z")
        env = self.run_drive(tree(), "2026-10-07T06:00:00Z")
        self.assertEqual(len(env["items"]), 9)
        self.assertNotIn("held", env)
        self.assertNotIn("empty_folders", env)

    def test_a_folder_deleted_after_it_looked_empty_is_forgotten(self):
        t = tree()
        self.run_drive(t)
        t["FLY"] = []
        self.run_drive(t, "2026-10-06T18:00:00Z")
        t["P77"] = [e for e in t["P77"] if e.id != "FLY"]                 # the folder itself is gone now
        env = self.run_drive(t, "2026-10-07T06:00:00Z")
        self.assertEqual(len(env["items"]), 6)
        self.assertNotIn("empty_folders", env)

    def test_the_whole_tree_looks_empty(self):
        t = tree()
        first = self.run_drive(t)
        t["ROOT"] = []
        env = self.run_drive(t, "2026-10-06T18:00:00Z")
        self.assertTrue(env["ok"])
        self.assertEqual((len(env["items"]), env["held"]["kept"]), (9, 9))
        self.assertEqual(env["empty_folders"], {"ROOT": "2026-10-06T18:00:00Z"})
        self.assertFalse(any("no Panel folder" in w for w in env["stats"]["warnings"]))
        self.assertEqual(env["stats"]["panel_folders"], first["stats"]["panel_folders"],
                         "nothing was read: the site still links the panel folder")
        env = self.run_drive(t, "2026-10-07T06:00:00Z")
        self.assertEqual(env["items"], [], "confirmed: removed now, not held a second time")
        self.assertNotIn("held", env)
        self.assertEqual(env["changes"]["removed"], 9)

    def test_the_listers_decision(self):
        lister = DriveLister(use_api=False, had_files={"A": 3, "B": 2}, empty_before={"B"})
        lister._list = lambda fid: Listing(True, [])
        a, b, c = lister.list("A"), lister.list("B"), lister.list("C")
        self.assertEqual((a.ok, a.unconfirmed), (False, 3))
        self.assertIn("held 3 file(s)", a.error)
        self.assertEqual((b.ok, b.unconfirmed, lister.confirmed_empty), (True, 0, {"B"}))
        self.assertEqual((c.ok, c.unconfirmed), (True, 0), "a folder that was empty before stays an ordinary one")
        lister._list = lambda fid: Listing(True, [file("x", "x.pdf")])
        self.assertTrue(lister.list("A").ok)
        lister._list = lambda fid: Listing(False, error="HTTP 500")
        self.assertEqual((lister.list("A").ok, lister.list("A").unconfirmed), (False, 0))


class DrivePrivateNames(DriveTempRaw):
    def test_what_is_not_published_is_counted_never_named(self):
        env = self.run_drive(tree())
        text = (self.raw / "drive.json").read_text(encoding="utf-8")
        for name in ("Secret", "40th Annual", "Panel75_GVLV", "Private planning", "Hidden"):
            self.assertNotIn(name, text)
        st = env["stats"]
        self.assertEqual((st["loose_skipped"], st["skipped_panels"], st["unreadable_folders"], st["depth_limited"]),
                         (2, [75], 1, 1))
        self.assertTrue(any("could not be read" in w for w in st["warnings"]))
        self.assertIn("Panel 77 (2027–2028)", st["panels"], "the published panel is still named")


# =========================================================================== byte caps
class Stream:
    """A streamed answer: `size` bytes in 64 KB chunks; counts the chunks read."""

    def __init__(self, size: int, ctype: str = "text/plain", status: int = 200, body: bytes | None = None):
        self.status_code, self.headers = status, {"Content-Type": ctype}
        self.body = body if body is not None else b"a" * size
        self.read = 0
        self.closed = False

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self.body), chunk_size):
            self.read += 1
            yield self.body[i:i + chunk_size]

    def close(self):
        self.closed = True


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def docx(text: str = "Hello from the committee.", extra_parts: int = 0, pad: int = 0) -> bytes:
    """A small .docx; `pad` spaces after its text part (they deflate to almost nothing)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", f"<w:document><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
                                        f"</w:body></w:document>" + " " * pad)
        for i in range(extra_parts):
            z.writestr(f"word/media/p{i}.xml", "x")
    return buf.getvalue()


class DriveDownloads(unittest.TestCase):
    def fetch(self, resp: Stream, name: str, mime: str = "text/plain") -> str | None:
        class Http:
            def __init__(self):
                self.kw = None

            def get(self, url, **kw):
                self.kw = kw
                return resp
        http = Http()
        out = D.fetch_body(http, "fid", mime, name)
        self.assertEqual(http.kw.get("stream"), True)
        self.assertTrue(resp.closed)
        return out

    def test_the_download_stops_at_the_cap(self):
        big = Stream(10 * D.MAX_TEXT_DOWNLOAD)
        text = self.fetch(big, "notes.txt")
        self.assertEqual(len(text), D.MAX_TEXT_DOWNLOAD, "a text file is read up to the cap")
        self.assertLessEqual(big.read, D.MAX_TEXT_DOWNLOAD // 65536 + 1, "the rest is never downloaded")
        big = Stream(2 * D.MAX_TEXT_DOWNLOAD, "application/octet-stream")
        self.assertIsNone(self.fetch(big, "post.docx", DOCX_MIME), "a cut-off .docx is not read")
        self.assertIsNone(self.fetch(Stream(10, "text/html"), "post.txt"), "a sign-in page instead of the file")
        self.assertEqual(self.fetch(Stream(0, body=docx("Hola")), "post.docx", DOCX_MIME), "Hola")
        # a character split by the cap is left out; the rest is still read as UTF-8, not Windows-1252
        body = ("a" * (D.MAX_TEXT_DOWNLOAD - 1) + "ñ La Viña").encode()
        self.assertEqual(self.fetch(Stream(0, body=body), "notes.txt"), "a" * (D.MAX_TEXT_DOWNLOAD - 1))
        self.assertEqual(self.fetch(Stream(0, body="Café ñ".encode("cp1252")), "notes.txt"), "Café ñ")

    def test_docx_caps(self):
        self.assertEqual(D.docx_to_text(docx("Welcome")), "Welcome")
        with self.assertRaisesRegex(ValueError, "parts inside"):
            D.docx_to_text(docx(extra_parts=D.MAX_DOCX_ENTRIES))
        bomb = docx(pad=D.MAX_DOCX_UNZIPPED + 1)               # a few KB that would unpack to more than the cap
        self.assertLess(len(bomb), 200_000)
        with self.assertRaisesRegex(ValueError, "unpack"):
            D.docx_to_text(bomb)
        self.assertIsNone(self.fetch(Stream(0, body=bomb), "bomb.docx", DOCX_MIME), "never a crash of the run")

    def test_an_ics_feed_stops_at_its_cap(self):
        big = Stream(4 * B.ICS_MAX_BYTES, "text/calendar", body=b"BEGIN:VCALENDAR\r\n" + b"x" * (4 * B.ICS_MAX_BYTES))
        with mock.patch("requests.get", lambda url, **kw: big if kw.get("stream") else None):
            res = B.fetch_feed("https://example.org/cal.ics", "test")
        self.assertEqual((res["state"], res["error"]), ("error", "the calendar file is too large"))
        self.assertLessEqual(big.read, B.ICS_MAX_BYTES // 65536 + 1)
        self.assertTrue(big.closed)
        small = Stream(0, "text/calendar; charset=UTF-8", body="BEGIN:VCALENDAR\r\nX-WR-CALNAME:La Viña\r\n".encode())
        with mock.patch("requests.get", lambda url, **kw: small):
            res = B.fetch_feed("https://example.org/cal.ics", "test")
        self.assertEqual(res["state"], "ok")
        self.assertIn("La Viña", res["text"])


# =========================================================================== translation cache and models
class TranslationSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-tr-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = self.tmp / "cache.json"

    def test_an_unreadable_cache_is_moved_aside_and_reported(self):
        for bad in ('{"_meta": {}, "abc": {"s": "x", "t"', "[1, 2, 3]"):
            with self.subTest(bad=bad):
                for f in self.tmp.glob("cache.json*"):
                    f.unlink()
                self.path.write_text(bad, encoding="utf-8")
                c = T.TranslationCache(self.path)
                self.assertEqual(c.entries, {})
                backups = list(self.tmp.glob("cache.json.bad-*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_text(encoding="utf-8"), bad, "kept as it was")
                self.assertIn("could not be read", c.problem)
                self.assertIn(backups[0].name, c.problem)
                c.put("en", "es", "Hello", "Hola")
                c.save()
                self.assertIn("Hola", self.path.read_text(encoding="utf-8"))

    def test_a_cache_that_cannot_be_moved_is_never_overwritten(self):
        self.path.write_text("{broken", encoding="utf-8")
        with mock.patch.object(T.os, "replace", side_effect=PermissionError("in use")):
            tr = T.Translator(cache_path=self.path, glossary_path=self.tmp / "g.yml",
                              overrides_path=self.tmp / "o.yml", models_dir=self.tmp / "models", download=False)
        self.assertTrue(tr.cache.locked)
        self.assertFalse(tr.use_model, "nothing new could be saved: the model is not run")
        tr.cache.put("en", "es", "Hello", "Hola")
        tr.save(prune_unused=True)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{broken")
        self.assertIn("nor moved aside", tr.problems[0])

    def test_a_model_whose_checksum_is_not_the_pinned_one(self):
        class Download:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, n):
                for _ in range(21):
                    yield b"\0" * (1 << 20)
        models = self.tmp / "models"
        with mock.patch("requests.get", lambda *a, **kw: Download()):
            why: dict[str, str] = {}
            self.assertEqual(T.ensure_models(["en_es"], models, errors=why), {"en_es": False})
            self.assertIn("sha256", why["en_es"])
            self.assertFalse((models / "en_es").exists(), "never installed")
            tr = T.Translator(cache_path=self.path, glossary_path=self.tmp / "g.yml",
                              overrides_path=self.tmp / "o.yml", models_dir=models)
            out = tr.translate(["The committee meets on Wednesday evenings."], "en", "es")
        self.assertEqual(out, [(None, False)], "not translated — and no crash")
        self.assertEqual(len(tr.problems), 1)
        self.assertIn("translation model en_es could not be installed", tr.problems[0])
        self.assertIn("MODEL_SHA256", tr.problems[0])


# =========================================================================== whole builds
class WholeBuilds(TempRaw):
    def setUp(self):
        super().setUp()
        self.out = self.tmp / "site"
        self.cache = self.tmp / "cache.json"
        self.cfg = {**common.load_config(), "recurring_events": [], "meeting": {}}
        self.cfg["sources"] = {**(self.cfg.get("sources") or {}), "ics_feeds": []}

    def build(self, *flags: str, at: str = T0, cfg: dict | None = None) -> dict:
        real = B.T.Translator
        conf = cfg or self.cfg
        with mock.patch.object(B, "load_config", lambda: conf), mock.patch.object(B, "STATE_DIR", self.tmp / "state"), \
                mock.patch.object(B.T, "Translator", lambda **kw: real(cache_path=self.cache, use_model=False,
                                                                       models_dir=self.tmp / "models", download=False)), \
                mock.patch.object(B.T, "_DEFAULT", None), mock.patch.object(B, "now_iso", return_value=at):
            self.assertEqual(B.main(["--out", str(self.out), "--offline", *flags]), 0)
        return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in self.out.glob("*.json")}

    def raw_file(self, source: str, its: list[dict], **extra) -> None:
        env = {"source": source, "updated": "2026-10-06T06:00:00Z", "attempted": "2026-10-06T06:00:00Z", "ok": True,
               "error": None, "stats": {}, "items": its, **extra}
        (self.raw / f"{source}.json").write_text(json.dumps(env), encoding="utf-8")

    def sources(self) -> None:
        recent = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        soon = (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d")
        vids = [{"id": f"yt:{i}", "source": "youtube", "kind": "video", "url": f"https://youtube.com/watch?v={i}",
                 "title": f"Video {i}", "lang": "en", "date": recent, "first_seen": recent, "category": "gv",
                 "extra": {}} for i in range(1, 3)]
        self.raw_file("youtube", vids, first_harvest="2026-01-01T00:00:00Z")
        post = {"id": "drive:post", "source": "drive", "kind": "announcement", "url": "https://drive.google.com/x",
                "title": "Welcome GVRs", "lang": "en", "date": recent, "first_seen": recent,
                "category": "announcements", "extra": {"body_md": "Hi", "file_id": "post"}}
        flyer = {"id": "drive:fly", "source": "drive", "kind": "document", "url": "https://drive.google.com/f",
                 "title": "Fall Workshop", "lang": "en", "date": recent, "first_seen": recent, "category": "flyers",
                 "extra": {"file_id": "fly", "event_date": soon, "event_title": "Fall Workshop",
                           "view_url": "https://drive.google.com/f"}}
        self.raw_file("drive", [post, flyer], first_harvest="2026-01-01T00:00:00Z")

    def test_an_unreadable_raw_file_keeps_the_last_builds_data(self):
        self.sources()
        one = self.build()
        self.assertEqual(len(one["videos"]["items"]), 2)
        self.assertIn("drive:post", [i["id"] for i in one["announcements"]["items"]])
        self.assertIn("ev:flyer:fly", [i["id"] for i in one["events"]["items"]])
        wn = {i["id"] for i in one["whatsnew"]["items"]}
        self.assertTrue({"yt:1", "yt:2"} <= wn)
        for source in ("youtube", "drive"):
            (self.raw / f"{source}.json").write_text('{"source": "x", "items": [', encoding="utf-8")
        two = self.build(at="2026-10-06T18:00:00Z")
        self.assertEqual(two["videos"], one["videos"], "the whole file of a single source")
        self.assertEqual(two["drive"], one["drive"])
        self.assertIn("drive:post", [i["id"] for i in two["announcements"]["items"]])
        self.assertIn("ev:flyer:fly", [i["id"] for i in two["events"]["items"]])
        self.assertTrue({"yt:1", "yt:2"} <= {i["id"] for i in two["whatsnew"]["items"]})
        rows = {r["source"]: r for r in two["status"]["sources"]}
        for source, count in (("youtube", 2), ("drive", 2)):
            r = rows[source]
            self.assertFalse(r["ok"], source)
            self.assertEqual(r["count"], count, source)
            self.assertEqual(r["updated"], "2026-10-06T06:00:00Z", "the last success it had")
            self.assertIn(f"data/raw/{source}.json could not be read", r["error"])
        self.assertEqual(two["status"]["counts"]["videos"], 2)

    def test_changes_and_held_reach_status_json(self):
        with mock.patch.object(common, "now_iso", return_value="2026-10-06T06:00:00Z"):
            common.save_raw("podcasts", items(3, "pod"))
            common.save_raw("podcasts", [])
        st = self.build()["status"]
        row = next(r for r in st["sources"] if r["source"] == "podcasts")
        self.assertEqual(row["changes"], {"added": 0, "removed": 0, "held": 3})
        self.assertEqual((row["held"]["kept"], row["held"]["since"]), (3, "2026-10-06T06:00:00Z"))
        self.assertNotIn("ids", row["held"], "the ids stay in data/raw")
        other = next(r for r in st["sources"] if r["source"] == "youtube")
        self.assertEqual((other["changes"], other["held"]), (None, None), "never ran")

    def test_unchanged_files_keep_their_stamp(self):
        self.sources()
        files = ("announcements", "events", "whatsnew", "spotlight", "writers_archive", "shop", "meetings",
                 "audio_project", "quote")
        self.build(at="2026-10-06T12:00:00Z")
        before = {n: (self.out / f"{n}.json").read_bytes() for n in files}
        two = self.build(at="2026-10-06T18:00:00Z")
        for n in files:
            self.assertEqual((self.out / f"{n}.json").read_bytes(), before[n], n)
            self.assertEqual(two[n]["updated"], "2026-10-06T12:00:00Z", n)
        self.assertEqual(two["status"]["generated"], "2026-10-06T18:00:00Z", "/status/ still says when data was made")
        self.assertEqual(two["videos"]["updated"], "2026-10-06T06:00:00Z", "a source's own time: its last read")
        env = json.loads((self.raw / "drive.json").read_text(encoding="utf-8"))
        env["items"][0]["title"] = "Welcome new GVRs"
        (self.raw / "drive.json").write_text(json.dumps(env), encoding="utf-8")
        three = self.build(at="2026-10-07T06:00:00Z")
        self.assertEqual(three["announcements"]["updated"], "2026-10-07T06:00:00Z", "its content changed")
        self.assertEqual(three["events"]["updated"], "2026-10-06T12:00:00Z")

    def cache_with_unused_entry(self) -> None:
        c = T.TranslationCache(self.cache)
        c.put("en", "es", "An old title nobody needs", "Un título viejo")
        c.save()

    def cached(self) -> int:
        return len(T.TranslationCache(self.cache).entries)

    def test_pruning_goes_on_while_a_settings_note_is_open(self):
        self.cache_with_unused_entry()
        cfg = {**self.cfg, "recurring_events": ["not an event"]}
        st = self.build(cfg=cfg)["status"]
        self.assertIn("recurring_events", st["problems"])
        self.assertEqual(st["translations"]["pending"], 0)
        self.assertEqual(self.cached(), 0, "pruned although a settings note is open")

    def test_no_pruning_while_a_raw_file_cannot_be_read(self):
        self.cache_with_unused_entry()
        (self.raw / "youtube.json").write_text("{broken", encoding="utf-8")
        self.build()
        self.assertEqual(self.cached(), 1)
        ctx = B.Ctx(offline=True)
        ctx.load_raw()
        self.assertEqual(B.prune_blockers(ctx, None), ["data/raw/youtube.json could not be read"])
        self.assertEqual(B.prune_blockers(ctx, mock.Mock(file_errors={"glossary": "bad"}))[-1],
                         "data/translations/glossary.yml could not be read")

    def test_translation_problems_reach_status_json(self):
        self.cache.write_text("{broken", encoding="utf-8")
        st = self.build()["status"]
        self.assertEqual(len(st["translations"]["problems"]), 1)
        self.assertIn("cache.json could not be read", st["translations"]["problems"][0])
        self.assertIn("cache.json could not be read", st["problems"]["translations"], "a Settings problem too")
        self.assertEqual(len(list(self.tmp.glob("cache.json.bad-*"))), 1)


# =========================================================================== the /status/ page
STATUS_PAGE_JS = r"""
process.env.ONLY = "status.njk";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-status-page-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) { cfg.addGlobalData("eleventyComputed", { db: (data) => ({ ...data.db, status: input.status }) }); },
  });
  const pages = (await elev.toJSON()).filter((p) => /\/status\/$/.test(p.url));
  out(Object.fromEntries(pages.map((p) => [p.url.includes("/es/") ? "es" : "en", p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class StatusPage(unittest.TestCase):
    def test_every_english_message_says_so(self):
        # the update's own messages are English on /es/status/ too: each block is lang="en", under a caption that
        # says so in Spanish (the failed source's <pre>s are checked by tests/test_accessibility.py)
        page = (ROOT / "src" / "pages" / "status.njk").read_text(encoding="utf-8")
        lists = [m.start() for m in re.finditer(r'<ul lang="en"', page)]
        self.assertEqual(len(lists), 2, "a source's notes, translation problems")
        for at in lists:
            self.assertIn('"community.status.notes_caption" | t(lang)', page[at - 200:at])
        strings = json.loads((ROOT / "src" / "_i18n" / "community.json").read_text(encoding="utf-8"))
        self.assertIn("(en inglés)", strings["community.status.notes_caption"]["es"])

    def test_on_hold_notes_and_translation_problems(self):
        if str(Path(__file__).resolve().parent) not in sys.path:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        from nodejs import run_js
        status = json.loads((ROOT / "data" / "site" / "status.json").read_text(encoding="utf-8"))
        for row in status["sources"]:
            row["held"], row["stats"] = None, {k: v for k, v in (row.get("stats") or {}).items() if k != "warnings"}
            if row["source"] == "drive":
                row["held"] = {"since": "2026-10-06T18:00:00Z", "kept": 3, "previous": 35, "found": 32, "drop": False,
                               "examples": ["Flyer 1"]}
            if row["source"] == "meetings":
                row["stats"]["warnings"] = ["Northwest Texas Area 66: feed answered HTTP 202 <b>bold</b>"]
            if row["source"] == "podcasts":
                row["held"] = {"since": "2026-10-06T18:00:00Z", "kept": 1, "previous": 300, "found": 299, "drop": True}
        status["translations"]["problems"] = ["data/translations/cache.json could not be read (JSONDecodeError)"]
        pages = run_js(self, STATUS_PAGE_JS, data={"status": status})
        words = {"en": ("On hold", "did not find 3 items that were here before", "did not find 1 item that was",
                        "On hold since", "Notes from the last update (1)", "could not translate everything"),
                 "es": ("En espera", "no encontró 3 elementos que antes estaban aquí", "no encontró 1 elemento",
                        "En espera desde", "Notas de la última actualización (1)", "no pudo traducir todo")}
        for lang, html in pages.items():
            with self.subTest(lang=lang):
                text = re.sub(r"\s+", " ", html)
                for w in words[lang]:
                    self.assertIn(w, text)
                self.assertIn("feed answered HTTP 202 &lt;b&gt;bold&lt;/b&gt;", text, "raw text, escaped")
                self.assertIn("cache.json could not be read (JSONDecodeError)", text)
                self.assertNotIn("undefined", text)
                self.assertNotIn("[object Object]", text)
        self.assertEqual(set(pages), {"en", "es"})


if __name__ == "__main__":
    unittest.main()
