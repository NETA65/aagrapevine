"""The booth display's Drive folder through the sync: scripts/sync/drive.py (the "booth" category, extra.booth, the
text of message files) and scripts/sync/build_data.py (data/site/booth.json — and the booth files in NO other site
file). Offline: the Drive folders are a fake listing, the downloads a fake session, data/raw and data/site are
temporary folders; no translation model.

  * Category   — the booth folder's names (English and Spanish, any capitals); the FIRST word that names a category
                 decides ("Booth photos" → booth, "photos/Booth at CityWide" → photos, an album); older folder names
                 keep their category.
  * Drive run  — a whole run of drive.main over a panel with a booth folder (collections, a deeper sub-folder,
                 messages, a camera name, an unsupported file, a form, files switched off, a flyer-like name) next
                 to photos, flyers and the bulletin: every booth file has category "booth" and its parsed name;
                 none is a bulletin post, an album photo or a flyer's event; message texts are fetched like a
                 bulletin post's body (the same budget — bulletin posts first —, reused while unchanged); no
                 request checks a form in the booth folder.
  * booth.json — build_data.build_booth: the shape, the order (first, order number, name), the collections, the
                 problems (with Spanish words and a code), files switched off or past their "until" day left out,
                 `updated`, the stamp (new with every new version of a file; an unchanged file keeps the last
                 booth.json's the next day, when Drive shows only its day — never carried for an exact time; two
                 whole build_data runs in a row).
  * Exclusion  — the booth files are not in drive.json (the Portfolio, the search, the digest), the bulletin, the
                 events, a series' flyers or What's New — even a raw item that carries a bulletin post's kind or a
                 flyer's event fields; /status/ still counts them with the Drive source. A whole build_data.main
                 run writes booth.json and keeps them out of every other file.
  * RunSummary — the "Write run summary" step of .github/workflows/update.yml lists booth.json's problems in full
                 (the file and what to do), with a yellow warning for each (at most 10).

    python -m unittest tests.test_booth_sync -v        (or: python -m unittest discover -s tests)
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
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import booth_names as BN  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import drive as D  # noqa: E402
from scripts.sync.drive_listing import FOLDER_MIME, Entry, Listing  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is in requirements.txt
    yaml = None

GDOC = "application/vnd.google-apps.document"
GFORM = "application/vnd.google-apps.form"


def folder(fid: str, name: str) -> Entry:
    return Entry(fid, name, FOLDER_MIME, is_folder=True)


def file(fid: str, name: str, mime: str, day: str = "2026-09-28", **kw) -> Entry:
    return Entry(fid, name, mime, modified_text=kw.pop("modified_text", "Sep 28"), modified=day, **kw)


# A panel with a booth folder next to photos, flyers and the bulletin (the folder view's own names and types).
TREE = {
    "ROOT": [folder("P77", "2027-2028_Panel77_GVLV")],
    "P77": [folder("BOOTH", "Booth"), folder("PHOTOS", "photos"), folder("FLYERS", "flyers"),
            folder("BULLETIN", "bulletin")],
    "BOOTH": [
        file("b-welcome", "GV EN Welcome to our table (first) (15s).png", "image/png", "2026-09-30"),
        file("b-video", "LV ES Testimonio - Mi primer número (0:05-1:45).mp4", "video/mp4", size=12_345_678),
        file("b-photo", "02 GVLV Our booth at CityWide Dallas.jpg", "image/jpeg"),
        file("b-camera", "IMG_2045.JPG", "image/jpeg"),
        file("b-msg", "GV EN Welcome message.txt", "text/plain"),
        file("b-doc", "Mensaje de bienvenida", GDOC),                     # no language in its name: its text tells
        file("b-empty", "GV EN Empty note.md", "text/markdown"),          # an empty file: a problem
        file("b-zip", "notes.zip", "application/zip"),
        file("b-form", "Sign-up", GFORM),
        file("b-off", "Draft poster (off).png", "image/png"),
        file("b-hidden", "_README naming.txt", "text/plain"),
        file("b-old", "LV ES Taller (hasta 2026-01-31).jpg", "image/jpeg"),   # past its day: left out
        file("b-dated", "2026-10-17 GV booth 9am @ Tyler TX.jpg", "image/jpeg"),   # a flyer's name — not an event
        # matches config/site.yml's flyer_match of La Viña's monthly workshop — never that series' flyer
        file("b-taller", "LV ES Taller Mensual y Virtual de La Viña (cartel).png", "image/png"),
        folder("SPRING", "Spring Assembly 2027"),
    ],
    "SPRING": [file("b-book", "GV EN Book display.jpg", "image/jpeg"), folder("EXTRA", "extra")],
    "EXTRA": [file("b-extra", "01 LV Mesa en Tyler.jpg", "image/jpeg")],
    "PHOTOS": [folder("ALBUM", "Booth at CityWide")],
    "ALBUM": [file("p-1", "IMG_1001.jpg", "image/jpeg"), file("p-2", "IMG_1002.jpg", "image/jpeg")],
    "FLYERS": [file("f-1", "2026-10-17 Fall Assembly GV booth 9am @ Tyler Civic Center.pdf", "application/pdf")],
    "BULLETIN": [file("n-1", "Welcome new GVRs", GDOC)],
}
BOOTH_IDS = {f"drive:{e.id}" for name in ("BOOTH", "SPRING", "EXTRA") for e in TREE[name] if not e.is_folder}
BODIES = {
    "b-msg": "Welcome message\n\nCome by our **Grapevine** and La Viña table and ask us anything.\n\n"
             "* Free sample magazines\n* How to subscribe\n",
    "b-doc": "Bienvenidos a nuestra mesa de La Viña y Grapevine. Pregúntanos cómo suscribirte o cómo ser RLV en tu "
             "grupo base.",
    "b-empty": "",
    "b-hidden": "Notes for the committee only.",
    "n-1": "Welcome to all the new GVRs and RLVs of our Area. Our next meeting is on the third Wednesday.",
}


class Resp:
    def __init__(self, status=200, content=b"", headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}


class FakeHttp:
    """Drive's downloads: a Google Doc's text export and an uploaded file's download, by file id."""

    def __init__(self):
        self.gets: list[str] = []
        self.heads: list[str] = []

    def get(self, url, **kw):
        self.gets.append(url)
        m = re.search(r"/document/d/([^/]+)/export|[?&]id=([^&]+)", url)
        text = BODIES.get((m[1] or m[2]) if m else "")
        if text is None:
            return Resp(404)
        return Resp(200, text.encode("utf-8"), {"Content-Type": "text/plain; charset=utf-8"})

    def head(self, url, **kw):
        self.heads.append(url)
        return Resp(200)

    def fetched(self, fid: str) -> int:
        return sum(1 for u in self.gets if fid in u)


def fake_lister(http: FakeHttp):
    class FakeLister:
        mode, api_error, requests_made = "html", None, 0

        class html:
            shortcuts_resolved = 0

        def __init__(self, **kw):
            self.http = http

        def list(self, fid):
            return Listing(True, [Entry(**vars(e)) for e in TREE[fid]])
    return FakeLister


class TempDirs(unittest.TestCase):
    """data/raw (and a data/state, a data/site) of their own for each test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-booth-"))
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        for p in (mock.patch.object(common, "RAW_DIR", self.raw), mock.patch.object(B, "RAW_DIR", self.raw)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_drive(self, http: FakeHttp | None = None) -> dict:
        """One drive.main run over TREE (→ data/raw/drive.json); its envelope."""
        http = http or FakeHttp()
        cfg = {"drive": {"root_folder_id": "ROOT", "min_panel": 77}}
        with mock.patch.object(D, "DriveLister", fake_lister(http)), mock.patch.object(D, "load_config", lambda: cfg):
            D.main([])
        return json.loads((self.raw / "drive.json").read_text(encoding="utf-8"))

    def ctx(self) -> B.Ctx:
        ctx = B.Ctx(offline=True)
        ctx.load_raw()
        return ctx


# --------------------------------------------------------------------------- category
class Category(unittest.TestCase):
    def test_the_booth_folders_names(self):
        for name in ("booth", "Booth", "BOOTHS", "Booth photos", "Booth display 2027", "Mesa", "mesas", "Kiosk",
                     "Kiosko", "kiosco", "Display", "Displays", "Pantalla", "Pantallas", "Stand", "Stands", "Exhibit",
                     "Exhibits", "Exhibición", "Exhibiciones", "Mesa de GV y LV", "Mesa_Asambleas"):
            self.assertEqual(D.category_for(name), "booth", name)

    def test_the_first_word_that_names_a_category_decides(self):
        cases = {"Booth photos": "booth", "Photos of the booth": "photos", "Flyers for the booth": "flyers",
                 "Workshop displays": "workshops", "Fotos 2027": "photos", "Meeting Notes": "notes",
                 "Informes-Reports": "reports", "bulletin": "announcements", "Misc": None}
        for name, cat in cases.items():
            self.assertEqual(D.category_for(name), cat, name)

    def test_a_photo_album_named_after_the_booth_stays_an_album(self):
        found = D.Found(Entry("p1", "IMG_1001.jpg", "image/jpeg"), D.Panel(77, "Panel 77 (2027–2028)", "P77", "x"),
                        ["photos", "Booth at CityWide"], ["ROOT", "P77", "PH", "AL"], seq=1)
        it = D.build_item(found, {})
        self.assertEqual((it["category"], it["extra"]["album"]), ("photos", "Booth at CityWide"))
        self.assertNotIn("booth", it["extra"])

    def test_spanish_booth_words_hint_at_spanish(self):
        self.assertEqual(D.lang_prior(["Mesa"], "x.jpg"), "es")
        self.assertEqual(D.lang_prior(["Pantallas"], "x.jpg"), "es")
        self.assertEqual(D.lang_prior(["Booth"], "x.jpg"), "en")


# --------------------------------------------------------------------------- the Drive run
SHOWN = ["drive:b-welcome", "drive:b-extra", "drive:b-photo", "drive:b-dated", "drive:b-book", "drive:b-msg",
         "drive:b-camera", "drive:b-taller", "drive:b-video", "drive:b-doc"]       # booth.json order


class DriveRun(TempDirs):
    def test_every_booth_file_has_its_category_and_its_parsed_name(self):
        env = self.run_drive()
        by_id = {i["id"]: i for i in env["items"]}
        self.assertLessEqual(BOOTH_IDS, set(by_id))
        for iid in BOOTH_IDS:
            it, ex = by_id[iid], by_id[iid]["extra"]
            self.assertEqual(it["category"], "booth", iid)
            self.assertEqual(set(ex["booth"]), set(BN.parse_booth_name("x.png", "image/png", ["booth"])), iid)
            # never a bulletin post, an album photo or a flyer's event
            self.assertNotEqual(it["kind"], "announcement", iid)
            self.assertIsNone(ex["album"], iid)
            for k in ("event_date", "event_month", "expires", "publish"):
                self.assertNotIn(k, ex, f"{iid}: {k}")
            if ex["booth"]["kind"] != "message":
                self.assertNotIn("body_md", ex, iid)
        video = by_id["drive:b-video"]
        self.assertEqual({k: video["extra"]["booth"][k] for k in ("kind", "pub", "langs", "start", "end", "collection")},
                         {"kind": "video", "pub": "lv", "langs": ["es"], "start": 5, "end": 105, "collection": "main"})
        self.assertEqual((video["title"], video["extra"]["modified"], video["extra"]["size_bytes"]),
                         ("Testimonio - Mi primer número", "2026-09-28", 12_345_678))
        extra = by_id["drive:b-extra"]["extra"]["booth"]                        # booth/Spring Assembly 2027/extra/
        self.assertEqual((extra["collection"], extra["collection_label"], extra["order"], extra["pub"]),
                         ("spring-assembly-2027", "Spring Assembly 2027", 1, "lv"))
        self.assertEqual(by_id["drive:b-camera"]["extra"]["booth"]["caption"], False)
        self.assertEqual(by_id["drive:b-camera"]["title"], "IMG 2045")          # the raw item keeps a readable title
        self.assertEqual(by_id["drive:b-dated"]["category"], "booth")
        # the folders next to it keep what they were
        self.assertEqual((by_id["drive:p-1"]["category"], by_id["drive:p-1"]["extra"]["album"]),
                         ("photos", "Booth at CityWide"))
        self.assertEqual(by_id["drive:f-1"]["extra"]["event_date"], "2026-10-17")
        self.assertEqual(by_id["drive:n-1"]["kind"], "announcement")
        self.assertEqual(env["stats"]["by_category"]["booth"], len(BOOTH_IDS))
        # one note names the files the booth cannot show (→ the Actions run summary's "Notes")
        self.assertIn("booth folder: 3 file(s) the booth display cannot show — GV EN Empty note.md, notes.zip, Sign-up "
                      "(data/site/booth.json → problems says why)", env["stats"]["warnings"])
        for iid in ("drive:p-1", "drive:f-1", "drive:n-1"):
            self.assertNotIn("booth", by_id[iid]["extra"])
            self.assertNotIn("modified", by_id[iid]["extra"])

    def test_message_texts_are_fetched_like_a_bulletin_posts_body(self):
        http = FakeHttp()
        env = self.run_drive(http)
        by_id = {i["id"]: i for i in env["items"]}
        msg = by_id["drive:b-msg"]["extra"]
        # the heading line the file repeats at its top is dropped (normalize_body); "* " bullets become "- "
        self.assertEqual(msg["body_md"], "Come by our **Grapevine** and La Viña table and ask us anything.\n\n"
                                         "* Free sample magazines\n* How to subscribe")
        self.assertEqual(msg["booth"]["text"], "Come by our **Grapevine** and La Viña table and ask us anything.\n\n"
                                               "- Free sample magazines\n- How to subscribe")
        self.assertEqual(msg["booth"]["langs"], ["en"])                         # from its name
        doc = by_id["drive:b-doc"]["extra"]["booth"]
        self.assertTrue(doc["text"].startswith("Bienvenidos a nuestra mesa"))
        self.assertEqual(doc["langs"], ["es"], "no language in its name: its text tells")
        self.assertIsNone(by_id["drive:b-empty"]["extra"]["booth"]["text"])
        self.assertEqual(http.fetched("b-hidden"), 0, "a message switched off is never downloaded")
        self.assertEqual(env["stats"]["booth_texts"], {"fetched": 3})
        self.assertEqual(env["stats"]["announcements"], {"fetched": 1})
        # the next run: unchanged files are not downloaded again (an empty one is asked again, like a bulletin post)
        again = FakeHttp()
        env = self.run_drive(again)
        self.assertEqual((again.fetched("b-msg"), again.fetched("b-doc"), again.fetched("b-empty")), (0, 0, 1))
        self.assertEqual(env["stats"]["booth_texts"], {"reused": 2, "fetched": 1})
        self.assertEqual({i["id"]: i for i in env["items"]}["drive:b-msg"]["extra"]["booth"]["text"],
                         msg["booth"]["text"])

    def test_the_bulletin_goes_first_within_the_runs_download_budget(self):
        http = FakeHttp()
        with mock.patch.object(D, "MAX_ANNOUNCEMENT_FETCHES", 2):
            env = self.run_drive(http)
        self.assertEqual(env["stats"]["announcements"], {"fetched": 1})
        self.assertEqual(env["stats"]["booth_texts"], {"fetched": 1, "deferred": 2})
        self.assertEqual((http.fetched("n-1"), http.fetched("b-msg"), http.fetched("b-doc")), (1, 1, 0))

    def test_a_body_that_cannot_be_fetched_keeps_the_last_good_one(self):
        self.run_drive()
        broken = FakeHttp()
        broken.get = lambda url, **kw: Resp(500)
        entry = next(e for e in TREE["BOOTH"] if e.id == "b-doc")
        entry.modified_text = "Oct 1"                     # the Google Doc was edited: its listing changed
        try:
            env = self.run_drive(broken)
        finally:
            entry.modified_text = "Sep 28"
        doc = {i["id"]: i for i in env["items"]}["drive:b-doc"]["extra"]
        self.assertTrue(doc["booth"]["text"].startswith("Bienvenidos"))
        self.assertEqual(env["stats"]["booth_texts"], {"reused": 1, "failed": 2})   # b-msg · b-doc, the empty b-empty

    def test_no_request_checks_a_form_in_the_booth_folder(self):
        http = FakeHttp()
        env = self.run_drive(http)
        self.assertEqual(http.heads, [])
        self.assertEqual(env["stats"]["forms"], {})
        form = {i["id"]: i for i in env["items"]}["drive:b-form"]
        self.assertEqual((form["kind"], form["extra"]["booth"]["kind"]), ("form", "unsupported"))
        self.assertNotIn("form_closed", form["extra"])
        # …while a form in the forms folder is still checked
        forms = [{"id": "drive:f", "kind": "form", "category": "forms", "url": "https://docs.google.com/forms/d/f/viewform",
                  "extra": {}},
                 {"id": "drive:g", "kind": "form", "category": "booth", "url": "https://docs.google.com/forms/d/g/viewform",
                  "extra": {}}]
        self.assertEqual(D.check_forms(forms, http), {"open": 1})
        self.assertEqual(http.heads, ["https://docs.google.com/forms/d/f/viewform"])

    def test_text_languages(self):
        self.assertEqual(D.text_langs("Welcome to our table. Ask us how to subscribe to the magazine.\n\n"
                                      "Bienvenidos a nuestra mesa. Pregúntanos cómo suscribirte a la revista."),
                         ["en", "es"])
        self.assertEqual(D.text_langs("Hi!", title="Bienvenidos a nuestra mesa de La Viña"), ["es"])
        self.assertEqual(D.text_langs("12345 — 678", title=""), [])


# --------------------------------------------------------------------------- data/site/booth.json
ITEM_KEYS = ["id", "file_id", "name", "mime", "size_bytes", "modified", "title", "kind", "pub", "langs", "caption",
             "order", "seconds", "start", "end", "muted", "weight", "first", "from", "until", "fit", "collection",
             "text", "image_url", "thumb_url", "download_url", "view_url", "stamp"]


class BoothJson(TempDirs):
    """build_booth over the raw items a whole drive.main run wrote."""

    def setUp(self):
        super().setUp()
        self.env = self.run_drive()
        self.doc = B.build_booth(self.ctx())
        self.rows = {r["id"]: r for r in self.doc["items"]}

    def test_the_shape(self):
        self.assertEqual(list(self.doc), ["updated", "fixture", "collections", "items", "problems"])
        self.assertIs(self.doc["fixture"], False)
        for row in self.doc["items"]:
            self.assertEqual(list(row), ITEM_KEYS, row["id"])
        self.assertEqual(self.rows["drive:b-video"], {
            "id": "drive:b-video", "file_id": "b-video", "name": "LV ES Testimonio - Mi primer número (0:05-1:45).mp4",
            "mime": "video/mp4", "size_bytes": 12_345_678, "modified": "2026-09-28",
            "title": "Testimonio - Mi primer número", "kind": "video", "pub": "lv", "langs": ["es"], "caption": True,
            "order": None, "seconds": None, "start": 5, "end": 105, "muted": False, "weight": 1, "first": False,
            "from": None, "until": None, "fit": "contain", "collection": "main", "text": None,
            "image_url": "https://lh3.googleusercontent.com/d/b-video=s1920",
            "thumb_url": "https://lh3.googleusercontent.com/d/b-video=w600",
            "download_url": "https://drive.usercontent.google.com/download?id=b-video&export=download&confirm=t",
            "view_url": "https://drive.google.com/file/d/b-video/view",
            "stamp": common.short_hash("b-video|2026-09-28|12345678|", 10)})
        welcome = self.rows["drive:b-welcome"]
        self.assertEqual({k: welcome[k] for k in ("kind", "pub", "langs", "title", "first", "seconds", "fit", "size_bytes")},
                         {"kind": "poster", "pub": "gv", "langs": ["en"], "title": "Welcome to our table", "first": True,
                          "seconds": 15, "fit": "contain", "size_bytes": None})
        doc = self.rows["drive:b-doc"]                       # a Google Doc: a message, nothing to download or picture
        self.assertEqual({k: doc[k] for k in ("kind", "langs", "image_url", "thumb_url", "download_url", "view_url")},
                         {"kind": "message", "langs": ["es"], "image_url": None, "thumb_url": None, "download_url": None,
                          "view_url": "https://docs.google.com/document/d/b-doc/edit?usp=sharing"})
        self.assertTrue(doc["text"].startswith("Bienvenidos a nuestra mesa"))
        self.assertEqual(self.rows["drive:b-msg"]["text"], "Come by our **Grapevine** and La Viña table and ask us "
                                                           "anything.\n\n- Free sample magazines\n- How to subscribe")
        self.assertEqual((self.rows["drive:b-camera"]["caption"], self.rows["drive:b-camera"]["title"]), (False, ""))
        self.assertEqual(self.rows["drive:b-extra"]["collection"], "spring-assembly-2027")

    def test_the_order(self):
        # "(first)", then the order numbers (01 in a collection, 02), then the names — numbers as numbers
        self.assertEqual([r["id"] for r in self.doc["items"]], SHOWN)

    def test_the_collections(self):
        self.assertEqual(self.doc["collections"], [{"id": "main", "label": "Booth folder", "count": len(SHOWN) - 2},
                                                   {"id": "spring-assembly-2027", "label": "Spring Assembly 2027",
                                                    "count": 2}])

    def test_problems_and_the_files_left_out(self):
        unsupported, no_text = BN.PROBLEMS["unsupported"], BN.PROBLEMS["no-text"]
        self.assertEqual(self.doc["problems"], [
            {"file": "Booth/GV EN Empty note.md", "problem": no_text[0], "problem_es": no_text[1], "code": "no-text"},
            {"file": "Booth/notes.zip", "problem": "not a type the booth can show", "problem_es": unsupported[1],
             "code": "unsupported"},
            {"file": "Booth/Sign-up", "problem": unsupported[0], "problem_es": unsupported[1], "code": "unsupported"}])
        listed = set(self.rows) | {p["file"] for p in self.doc["problems"]}
        for left_out in ("drive:b-off", "drive:b-hidden", "drive:b-old"):      # off, "_name", past its until day
            self.assertNotIn(left_out, listed)
        self.assertFalse(any("Draft" in p["file"] or "README" in p["file"] for p in self.doc["problems"]))

    def test_updated_is_when_the_booth_folder_last_changed(self):
        by_id = {i["id"]: i for i in self.env["items"]}
        newest = max(by_id[i]["first_seen"] for i in SHOWN + ["drive:b-empty", "drive:b-zip", "drive:b-form"])
        self.assertEqual(self.doc["updated"], newest)


def raw_booth(fid: str, name: str, path=("booth",), first_seen: str = "2026-09-01T10:00:00Z", mime: str | None = None,
              status: str = "ok", booth: dict | None = None, **extra) -> dict:
    """A booth file as drive.py writes it to data/raw/drive.json."""
    from scripts.sync.drive_listing import guess_mime
    mime = (guess_mime(name) or "") if mime is None else mime
    parsed = {**BN.parse_booth_name(name, mime, list(path)), **(booth or {})}
    return {"id": f"drive:{fid}", "source": "drive", "kind": "photo", "url": f"https://drive.google.com/file/d/{fid}/view",
            "title": parsed["title"] or name, "summary": "", "lang": "en", "date": None, "first_seen": first_seen,
            "image": None, "tags": [], "category": "booth", "status": status,
            "extra": {"file_id": fid, "name": name, "mime": mime, "path": list(path), "booth": parsed, **extra}}


class BoothDetails(unittest.TestCase):
    def build(self, *items: dict, today: str | None = None) -> dict:
        ctx = B.Ctx(offline=True)
        if today:
            ctx.today_local = datetime.strptime(today, "%Y-%m-%d").date()
        ctx.raw["drive"] = {"items": list(items)}
        return B.build_booth(ctx)

    def ids(self, doc: dict) -> list[str]:
        return [r["file_id"] for r in doc["items"]]

    def test_first_then_order_then_name(self):
        doc = self.build(raw_booth("z", "Zeta.png"), raw_booth("o2", "02 Beta.png"), raw_booth("o10", "10 Alpha.png"),
                         raw_booth("f2", "Omega (first).png"), raw_booth("f1", "03 Alpha (first).png"),
                         raw_booth("i10", "IMG_10.jpg"), raw_booth("i2", "IMG_2.jpg"))
        self.assertEqual(self.ids(doc), ["f1", "f2", "o2", "o10", "i2", "i10", "z"])

    def test_until_today_shows_yesterday_does_not(self):
        doc = self.build(raw_booth("t", "Taller (hasta 2026-10-02).jpg"), raw_booth("y", "Taller (hasta 2026-10-01).jpg"),
                         raw_booth("f", "Taller (desde 2026-12-01).jpg"), today="2026-10-02")
        self.assertEqual(self.ids(doc), ["f", "t"])          # a later "from": listed now, so it is saved in time
        self.assertEqual(doc["problems"], [])

    def test_updated(self):
        doc = self.build(raw_booth("a", "A.jpg", modified="2026-09-20"),                      # first seen Sep 1
                         raw_booth("b", "B.jpg", first_seen="2026-09-15T08:30:00Z"),
                         raw_booth("off", "C (off).jpg", first_seen="2026-09-30T00:00:00Z"),   # not listed: not counted
                         raw_booth("zip", "notes.zip", first_seen="2026-09-18T00:00:00Z"))     # a problem: counted
        self.assertEqual(doc["updated"], "2026-09-20T12:00:00Z")                              # a day = noon UTC
        self.assertEqual(self.build(), B.empty_booth())
        self.assertIsNone(self.build(raw_booth("off", "Draft (off).jpg"))["updated"])

    def test_gone_files_and_raw_items_without_a_parsed_name(self):
        older = raw_booth("old", "GV EN Welcome (first).png")
        del older["extra"]["booth"]                        # written before drive.py read booth names
        doc = self.build(older, raw_booth("gone", "Gone.png", status="gone"))
        self.assertEqual([(r["file_id"], r["pub"], r["first"], r["title"]) for r in doc["items"]],
                         [("old", "gv", True, "Welcome")])

    def test_where_to_get_each_kind(self):
        doc = self.build(
            raw_booth("pdf", "Ways to carry the message.pdf"), raw_booth("song", "GV Song.mp3"),
            raw_booth("gdoc", "Mensaje", mime=GDOC, booth={"text": "Hola", "langs": ["es"]},
                      view_url="https://docs.google.com/document/d/gdoc/edit?usp=sharing"),
            raw_booth("deck", "Deck", mime="application/vnd.google-apps.presentation"))
        rows = {r["file_id"]: r for r in doc["items"]}
        lh3 = "https://lh3.googleusercontent.com/d/"
        dl = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"
        self.assertEqual([rows["pdf"][k] for k in ("kind", "image_url", "thumb_url", "download_url")],
                         ["poster", lh3 + "pdf=s1920", lh3 + "pdf=w600", dl.format("pdf")])
        self.assertEqual([rows["song"][k] for k in ("kind", "image_url", "thumb_url", "download_url", "fit")],
                         ["audio", None, None, dl.format("song"), None])
        self.assertEqual([rows["gdoc"][k] for k in ("kind", "text", "image_url", "download_url", "view_url")],
                         ["message", "Hola", None, None, "https://docs.google.com/document/d/gdoc/edit?usp=sharing"])
        self.assertEqual([rows["deck"][k] for k in ("kind", "image_url", "download_url")],
                         ["poster", lh3 + "deck=s1920", None])           # Drive's picture of its first slide

    def test_the_stamp_changes_with_every_new_version(self):
        base = {"file_id": "x", "modified": "2026-09-28", "size_bytes": None, "modified_text": "Sep 28"}
        stamp = B.booth_stamp(base)
        self.assertRegex(stamp, r"^[0-9a-f]{10}$")
        self.assertEqual(B.booth_stamp(dict(base)), stamp)
        self.assertEqual(B.booth_stamp({**base, "modified_text": "9/28/26"}), stamp)     # only the day counts…
        self.assertNotEqual(B.booth_stamp({**base, "modified": "2026-09-29"}), stamp)
        self.assertNotEqual(B.booth_stamp({**base, "size_bytes": 1024}), stamp)
        self.assertNotEqual(B.booth_stamp({**base, "file_id": "y"}), stamp)
        morning = B.booth_stamp({**base, "modified_text": "7:49 am"})                    # …but a clock time too
        self.assertNotEqual(morning, stamp)
        self.assertNotEqual(B.booth_stamp({**base, "modified_text": "3:15 pm"}), morning)  # replaced the same day

    def test_an_unchanged_file_keeps_its_stamp_the_next_day(self):
        # Without GOOGLE_API_KEY: "7:49 am" today, "Sep 28" from tomorrow on — the same version of the file, so the
        # same name for its media copy (a new one would make the build and every booth device download it again).
        base = {"file_id": "x", "modified": "2026-09-28", "size_bytes": None, "modified_text": "Sep 28"}
        morning = B.booth_stamp({**base, "modified_text": "7:49 am"})
        last = {"stamp": morning, "modified": "2026-09-28", "size_bytes": None}       # its row in the last booth.json
        self.assertEqual(B.booth_stamp(base, last), morning)
        # an upload late in the evening (Pacific): the clock's day is Central (Sep 28), the listing's Pacific (Sep 27)
        self.assertEqual(B.booth_stamp({**base, "modified": "2026-09-27", "modified_text": "Sep 27"}, last), morning)
        # a later day is a new version (replaced, and no sync saw its clock time) …
        self.assertEqual(B.booth_stamp({**base, "modified": "2026-09-30"}, last),
                         B.booth_stamp({**base, "modified": "2026-09-30"}))
        self.assertNotEqual(B.booth_stamp({**base, "modified": "2026-09-30"}, last), morning)
        # … so is a new clock time (replaced the same day), a new size, and a day more than one day earlier
        self.assertNotEqual(B.booth_stamp({**base, "modified_text": "3:15 pm"}, last), morning)
        self.assertNotEqual(B.booth_stamp({**base, "size_bytes": 1024}, last), morning)
        self.assertNotEqual(B.booth_stamp({**base, "modified": "2026-09-26"}, last), morning)
        # nothing usable in the last row: the stamp is made afresh
        fresh = B.booth_stamp(base)
        for bad in (None, {}, {"stamp": morning}, {**last, "stamp": ""}, {**last, "stamp": "not a stamp"},
                    {**last, "modified": None}, {**last, "modified": "2026-02-30"}, {**last, "modified": "Sep 28"}, "junk"):
            self.assertEqual(B.booth_stamp(base, bad), fresh, bad)
        self.assertEqual(B.booth_stamp({**base, "modified": "2026-02-30"}, {**last, "modified": "2026-02-30"}),
                         B.booth_stamp({**base, "modified": "2026-02-30"}), "not a day")

    def test_an_exact_time_is_never_carried(self):
        # With GOOGLE_API_KEY, `modified` is the exact time of the change: its own hash, whatever the last row says
        api = {"file_id": "x", "modified": "2026-09-28T14:49:00Z", "size_bytes": 1234,
               "modified_text": "2026-09-28T14:49:00.123Z"}
        stamp = B.booth_stamp(api)
        self.assertEqual(stamp, common.short_hash("x|2026-09-28T14:49:00Z|1234|", 10))
        for last in ({"stamp": "0123456789", "modified": "2026-09-28T14:49:00Z", "size_bytes": 1234},
                     {"stamp": "0123456789", "modified": "2026-09-28", "size_bytes": 1234}):
            self.assertEqual(B.booth_stamp(api, last), stamp)
        # a file listed with its day only, after a run that knew its exact time (the key was taken away): fresh
        day = {"file_id": "x", "modified": "2026-09-28", "size_bytes": 1234, "modified_text": "Sep 28"}
        self.assertEqual(B.booth_stamp(day, {"stamp": stamp, "modified": "2026-09-28T14:49:00Z", "size_bytes": 1234}),
                         B.booth_stamp(day))

    def test_build_booth_keeps_the_stamps_of_the_last_booth_json(self):
        # a run while the change is under 24 hours old, then the next morning's run: the same stamps
        today = raw_booth("v", "GVLV BI Bienvenidos - Welcome.mp4", modified="2026-10-01", modified_text="6:30 pm")
        fresh = raw_booth("p", "GV EN Welcome.png", modified="2026-10-01", modified_text="6:35 pm")
        first = self.build(today, fresh, today="2026-10-01")
        stamps = {r["file_id"]: r["stamp"] for r in first["items"]}
        self.assertEqual(stamps["v"], common.short_hash("v|2026-10-01||6:30 pm", 10))
        tomorrow = raw_booth("v", "GVLV BI Bienvenidos - Welcome.mp4", modified="2026-10-01", modified_text="Oct 1")
        replaced = raw_booth("p", "GV EN Welcome.png", modified="2026-10-02", modified_text="9:10 am")  # a new version
        ctx = B.Ctx(offline=True)
        ctx.today_local = datetime.strptime("2026-10-02", "%Y-%m-%d").date()
        ctx.raw["drive"] = {"items": [tomorrow, replaced]}
        second = {r["file_id"]: r["stamp"] for r in B.build_booth(ctx, json.loads(json.dumps(first)))["items"]}
        self.assertEqual(second["v"], stamps["v"], "the same video: the same name for its copy")
        self.assertNotEqual(second["p"], stamps["p"], "a new version: a new name")
        # without the last booth.json — none, unreadable, or sample data — the stamps are made afresh
        made = common.short_hash("v|2026-10-01||", 10)
        for last in (None, {}, [], "junk", {"items": "junk"}, {**first, "fixture": True},
                     {"items": [None, 1, {"file_id": None, "stamp": stamps["v"]}]}):
            self.assertEqual({r["file_id"]: r["stamp"] for r in B.build_booth(ctx, last)["items"]}["v"], made, last)


# --------------------------------------------------------------------------- the booth files in no other site file
class Exclusion(TempDirs):
    def setUp(self):
        super().setUp()
        self.run_drive()
        self.c = self.ctx()
        # booth files that carry what would make any other file a bulletin post or a flyer's event
        post = raw_booth("b-post", "Booth post", mime=GDOC, first_seen="2026-09-30T10:00:00Z", body_md="Hello",
                         pinned=True, expires=None, publish=None)
        post.update({"kind": "announcement", "date": "2026-09-30"})
        event = raw_booth("b-event", "2026-10-17 Booth event 9am @ Tyler TX.jpg", first_seen="2026-09-30T10:00:00Z",
                          view_url="https://drive.google.com/file/d/b-event/view", event_date="2026-10-17",
                          event_title="Booth event", event_time="09:00", event_location="Tyler TX")
        event["date"] = "2026-09-30"
        self.c.raw["drive"]["items"] += [post, event]
        self.booth_ids = BOOTH_IDS | {"drive:b-post", "drive:b-event"}
        self.others = {"drive:p-1", "drive:p-2", "drive:f-1", "drive:n-1"}

    @staticmethod
    def ids(items) -> set[str]:
        return {i["id"] for i in items}

    def test_ctx_items_leaves_the_booth_out(self):
        self.assertEqual(self.ids(self.c.items("drive")), self.others)
        self.assertEqual(self.ids(self.c.booth_items()), self.booth_ids)

    def test_not_in_the_portfolio_the_bulletin_the_events_a_series_or_whats_new(self):
        drive = B.simple(self.c, "drive", exclude=("announcement",), skip=B.closed_form)    # → drive.json
        self.assertEqual(self.ids(drive), {"drive:p-1", "drive:p-2", "drive:f-1"})
        posts = B.build_announcements(self.c)
        self.assertEqual(self.ids(posts), {"drive:n-1"})
        events = B.flyer_events(self.c)
        self.assertEqual(self.ids(events), {"ev:flyer:f-1"})
        flyers = B.series_flyers(self.c, re.compile("tyler|taller mensual", re.I))
        self.assertEqual({f["id"] for f in flyers}, {"drive:f-1"})
        plan = B.plan_whatsnew(self.c, {"drive": drive, "announcements": posts, "events": events})
        shown = {it["id"] for _wn, it in plan} | {p for _wn, it in plan for p in it["extra"].get("photo_ids") or []}
        self.assertIn("drive:n-1", shown)
        self.assertFalse(shown & self.booth_ids)

    def test_status_still_counts_them_with_the_drive_source(self):
        status = B.build_status(self.c, None, B.I18n(None), {}, False, 0.0)
        drive = next(s for s in status["sources"] if s["source"] == "drive")
        self.assertEqual(drive["count"], len(self.booth_ids) + len(self.others))


class WholeBuild(TempDirs):
    """build_data.main over the raw items of a drive.main run (no other source; a recurring series of our own whose
    flyer_match matches a booth poster): booth.json is written, and no booth file is in any other file."""

    SERIES = {"key": "booth-test", "title": "Taller Mensual y Virtual de La Viña", "week_of_month": 4,
              "weekday": "thursday", "start": "14:00", "end": "15:00", "host": "lv", "months_ahead": 2,
              "online_url": "https://us06web.zoom.us/j/81595931777", "flyer_match": "taller mensual"}

    def test_booth_json_and_no_booth_file_anywhere_else(self):
        self.run_drive()
        out = self.tmp / "site"
        cfg = {**common.load_config(), "recurring_events": [dict(self.SERIES)]}
        real_translator = B.T.Translator
        with mock.patch.object(B, "load_config", lambda: cfg), mock.patch.object(B, "STATE_DIR", self.tmp / "state"), \
                mock.patch.object(B.T, "Translator", lambda **kw: real_translator(cache=False, use_model=False)), \
                mock.patch.object(B.T, "_DEFAULT", None):
            self.assertEqual(B.main(["--out", str(out), "--offline", "--no-translate", "--no-prune"]), 0)
        site = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in out.glob("*.json")}
        self.assertEqual([r["id"] for r in site["booth"]["items"]], SHOWN)
        self.assertEqual([p["code"] for p in site["booth"]["problems"]], ["no-text", "unsupported", "unsupported"])
        for f in sorted(out.glob("*.json")):
            if f.name == "booth.json":
                continue
            text = f.read_text(encoding="utf-8")
            for iid in BOOTH_IDS:
                fid = iid.split(":", 1)[1]
                self.assertNotIn(f'"{iid}"', text, f"{iid} in {f.name}")
                self.assertNotIn(f"/d/{fid}", text, f"{fid} in {f.name}")
        self.assertEqual({i["id"] for i in site["drive"]["items"]}, {"drive:p-1", "drive:p-2", "drive:f-1"})
        self.assertIn("drive:n-1", {i["id"] for i in site["announcements"]["items"]})
        self.assertIn("ev:flyer:f-1", {i["id"] for i in site["events"]["items"]})
        series = [e for e in site["events"]["items"] if e["id"].startswith("ev:recurring:booth-test:")]
        self.assertTrue(series)
        self.assertEqual({e["extra"]["flyer_url"] for e in series}, {None}, "a booth poster is never a series' flyer")
        self.assertEqual(site["status"]["counts"]["booth"], len(SHOWN))
        drive = next(s for s in site["status"]["sources"] if s["source"] == "drive")
        self.assertEqual(drive["count"], len(BOOTH_IDS) + 4)

    def test_the_next_run_keeps_the_stamps_of_unchanged_files(self):
        # Two whole build_data runs as the sync makes them without GOOGLE_API_KEY: the evening of an upload the
        # folder view shows its clock time, the next morning only its day. main reads the last booth.json before it
        # writes the new one, so the stamp — the name of the build's media copy — stays the same.
        out = self.tmp / "site"
        real_translator = B.T.Translator

        def run(*items: dict) -> dict[str, str]:
            env = {"source": "drive", "updated": "2026-10-02T12:00:00Z", "ok": True, "error": None, "stats": {},
                   "items": list(items)}
            (self.raw / "drive.json").write_text(json.dumps(env), encoding="utf-8")
            with mock.patch.object(B, "STATE_DIR", self.tmp / "state"), \
                    mock.patch.object(B.T, "Translator", lambda **kw: real_translator(cache=False, use_model=False)), \
                    mock.patch.object(B.T, "_DEFAULT", None):
                self.assertEqual(B.main(["--out", str(out), "--offline", "--no-translate", "--no-prune"]), 0)
            doc = json.loads((out / "booth.json").read_text(encoding="utf-8"))
            return {r["file_id"]: r["stamp"] for r in doc["items"]}

        name = "GVLV BI Bienvenidos - Welcome.mp4"
        evening = run(raw_booth("v1", name, modified="2026-10-01", modified_text="6:30 pm"),
                      raw_booth("p1", "GV EN Welcome.png", modified="2026-09-20", modified_text="Sep 20"))
        self.assertEqual(evening["v1"], common.short_hash("v1|2026-10-01||6:30 pm", 10))
        morning = run(raw_booth("v1", name, modified="2026-10-01", modified_text="Oct 1"),
                      raw_booth("p1", "GV EN Welcome.png", modified="2026-09-20", modified_text="Sep 20"))
        self.assertEqual(morning, evening, "the same files: the same names for their copies")
        replaced = run(raw_booth("v1", name, modified="2026-10-03", modified_text="Oct 3"))
        self.assertEqual(replaced, {"v1": common.short_hash("v1|2026-10-03||", 10)}, "a later day: a new version")


class RunSummary(unittest.TestCase):
    """The "Write run summary" step of .github/workflows/update.yml with a data/site/booth.json that has problems: the
    summary lists each file in full with what to do (the Drive source's own note only counts them), and each one is a
    yellow warning on the run's page; the rest of the summary is unchanged."""

    def test_booth_folder_problems_in_full(self):
        if yaml is None:
            self.skipTest("PyYAML is not installed")
        wf = yaml.safe_load((ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8"))
        step = next(st for st in wf["jobs"]["sync"]["steps"] if st.get("name") == "Write run summary")
        code = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        tmp = Path(tempfile.mkdtemp(prefix="gv-booth-summary-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "data" / "site").mkdir(parents=True)
        (tmp / "data" / "site" / "status.json").write_text(json.dumps({"fixture": False, "sources": []}), encoding="utf-8")
        avi, empty = BN.PROBLEMS["video-type"], BN.PROBLEMS["no-text"]
        booth = {"updated": "2026-10-01T12:00:00Z", "fixture": False, "collections": [], "items": [], "problems": [
            {"file": "booth/Spring Assembly 2027/Testimonio.avi", "problem": avi[0], "problem_es": avi[1], "code": "video-type"},
            {"file": "booth/GV EN Welcome | hello.txt", "problem": empty[0], "problem_es": empty[1], "code": "no-text"}]}
        (tmp / "data" / "site" / "booth.json").write_text(json.dumps(booth), encoding="utf-8")
        (tmp / "script.py").write_text(code, encoding="utf-8")
        env = dict(os.environ, GITHUB_STEP_SUMMARY=str(tmp / "summary.md"), GITHUB_OUTPUT=str(tmp / "out.txt"),
                   PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        summary = (tmp / "summary.md").read_text(encoding="utf-8")
        self.assertIn("**Booth folder files the booth display can't show** (2;", summary)
        self.assertIn(f"- booth/Spring Assembly 2027/Testimonio.avi — {avi[0]}", summary)
        self.assertIn(f"- booth/GV EN Welcome / hello.txt — {empty[0]}", summary, "a | would break the summary's lists")
        warnings = [ln for ln in r.stdout.splitlines() if ln.startswith("::warning title=Booth folder file to fix::")]
        self.assertEqual(len(warnings), 2)
        self.assertIn("Testimonio.avi — a video type browsers do not play", warnings[0])
        # no booth.json, or one without problems: nothing about the booth
        (tmp / "data" / "site" / "booth.json").write_text(json.dumps({**booth, "problems": []}), encoding="utf-8")
        (tmp / "summary.md").unlink()
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Booth folder", (tmp / "summary.md").read_text(encoding="utf-8") + r.stdout)


if __name__ == "__main__":
    unittest.main()
