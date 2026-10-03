"""The booth display's photos and videos, saved for offline (r5 SPEC §2.3): scripts/build/booth-media-core.mjs (the
rules, run in Node.js), scripts/build/booth-media.mjs (the downloader, against a small web server of this test — never
the internet), the two steps of .github/workflows/update.yml and the passthrough in eleventy.config.js.

  * Config      — config/site.yml's `booth:` section read without a YAML library: the defaults 95 / 400, comments,
                  quotes, the one-line form, CRLF and a BOM, deeper keys and other sections never mixed up, a number it
                  can't read keeps its default, nothing above 800 MB (GitHub Pages takes 1 GB); the real config/site.yml
                  read as PyYAML reads it
  * Names       — "<stamp>-<slug>.<ext>": plain ASCII words of the title (or the name), booth.json's stamp tidied (or
                  the same kind of hash made here), the extension from the answer's type, else the name, else the type
                  booth.json gives, else ".bin"; the type each extension is served as
  * Plan        — booth.json's order with the "first" files first; a video or sound file over max_file_mb skipped as
                  too big (also a saved one, after the limit went down); the folder's limit with pictures counted (by a
                  guess before they are downloaded) and saved files by their real size, video and sound files of
                  unknown size never skipped by it (the downloader gives them the room left); saved files kept by their
                  stamp (a new title keeps the old name); everything else in the folder deleted; messages need nothing;
                  files past their "until" day not saved; no file id; listed twice; the addresses Google gives every
                  public file when booth.json has none; each download's limits and time
  * Pictures    — the width and height from the first bytes: hand-made PNG, JPEG (baseline, progressive, an EXIF
                  quarter turn in either byte order), GIF and WebP (VP8, VP8L, VP8X) headers, and real files Pillow
                  makes; anything else, or a file cut short: null
  * WebPages    — an answer that is a web page (by its type, or by its first bytes) is not the file
  * Results     — the manifest's shape, GitHub's warning lines, sizes in words
  * Downloader  — the script end to end: the files and the manifest, what is skipped and why (warnings, the run
                  summary), retries, a second run downloads nothing, files no longer listed are deleted, --dry-run and
                  BOOTH_MEDIA=0 change nothing, booth.json missing / empty / sample data / unreadable, out of time, the
                  folder's limit with the real sizes, files of unknown size filling the room really left (one that
                  would pass it stopped there: over the folder's limit, not too big — nothing of it kept, the files
                  after it still tried), a compressed answer; exit code 0 throughout
  * Workflow    — the four steps in the build-deploy job, after "Install site tools" and before "Build the website":
                  restore (actions/cache/restore, this booth.json's newest copy, else any), download, the key of the
                  folder as the download left it (the saved files' names and sizes — the key step's own script run
                  in bash) and save (actions/cache/save, only when this run changed the folder); the script's own
                  time inside the step's and the job's; the Code check downloads nothing
  * Passthrough — eleventy.config.js publishes .cache/booth-media/files at /about/booth/media only when the folder is
                  there, and never watches .cache/
Offline. Skipped without Node.js (the Passthrough test also without node_modules), as in tests/nodejs.py; the real
pictures need Pillow (requirements.txt).

    python -m unittest tests.test_booth_media -v
"""
from __future__ import annotations

import base64
import gzip
import http.server
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, node_path, run_js  # noqa: E402

CORE = "scripts/build/booth-media-core.mjs"
SCRIPT = ROOT / "scripts" / "build" / "booth-media.mjs"
WF = ROOT / ".github" / "workflows"
MB = 1024 * 1024

try:
    from PIL import Image
except ImportError:          # pragma: no cover — Pillow is in requirements.txt
    Image = None


def core(case: unittest.TestCase, expr: str, data=None):
    """`expr` evaluated in Node.js with the core module as C and the Python `data` as input."""
    return run_js(case, f'const C = await imp("{CORE}");\nout({expr});', data=data, needs_modules=False)


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# ---------------------------------------------------------------------------------------------------------- config
class Config(unittest.TestCase):
    def read(self, texts: list[str]) -> list[dict]:
        return core(self, "input.map((t) => C.parseBoothConfig(t))", texts)

    def test_defaults_and_the_block_form(self):
        texts = [
            "",
            "site:\n  title: x\n",
            # comments, quotes, a deeper key and another section with the same key names
            "site:\n  title: x\nbooth:\n  max_file_mb: 120          # a comment\n  max_total_mb: \"300\"\n"
            "  defaults:\n    max_file_mb: 5\n    language: both\nsources:\n  max_total_mb: 9\n",
            # 4 spaces, the section last without a line end, single quotes
            "a: 1\nbooth:\n    max_total_mb: '250'\n    max_file_mb: 12.5",
            # a comment line and a blank line inside the section; CRLF; a BOM
            "﻿booth:\r\n  # the limits\r\n\r\n  max_file_mb: 10\r\n  max_total_mb: 20\r\nnext: 1\r\n",
            # the one-line form
            "booth: { max_file_mb: 50, max_total_mb: 2000 }  # big\n",
            # `booth_old:` is another key; a `booth:` written inside another section is not the section
            "booth_old:\n  max_file_mb: 1\nsources:\n  booth:\n    max_file_mb: 2\n",
        ]
        self.assertEqual(self.read(texts), [
            {"max_file_mb": 95, "max_total_mb": 400},
            {"max_file_mb": 95, "max_total_mb": 400},
            {"max_file_mb": 120, "max_total_mb": 300},
            {"max_file_mb": 12.5, "max_total_mb": 250},
            {"max_file_mb": 10, "max_total_mb": 20},
            {"max_file_mb": 50, "max_total_mb": 800},      # 2000 → the ceiling (GitHub Pages: 1 GB for the whole site)
            {"max_file_mb": 95, "max_total_mb": 400},
        ])

    def test_numbers_it_cannot_read_keep_their_default(self):
        values = ["95MB", "-1", "lots", "", "~", "null", "1e3", "[1]", "0", "0.5", "+7", "5000"]
        texts = [f"booth:\n  max_file_mb: {v}\n  max_total_mb: {v}\n" for v in values]
        got = [(c["max_file_mb"], c["max_total_mb"]) for c in self.read(texts)]
        self.assertEqual(got, [(95, 400)] * 8 + [(0, 0), (0.5, 0.5), (7, 7), (800, 800)])

    def test_the_real_config_reads_as_pyyaml_reads_it(self):
        text = (ROOT / "config" / "site.yml").read_text(encoding="utf-8")
        booth = (yaml.safe_load(text) or {}).get("booth") or {}

        def want(key, default):
            v = booth.get(key) if isinstance(booth, dict) else None
            return default if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 else min(800, v)
        self.assertEqual(self.read([text])[0], {"max_file_mb": want("max_file_mb", 95), "max_total_mb": want("max_total_mb", 400)})

    def test_caps_in_bytes(self):
        got = core(self, "[C.caps({}), C.caps({ max_file_mb: 1, max_total_mb: '2' }), C.caps({ max_file_mb: NaN, max_total_mb: -5 }),"
                         " C.caps(null), C.caps({ max_file_mb: 0.5, max_total_mb: 9999 })]")
        self.assertEqual(got, [
            {"fileBytes": 95 * MB, "totalBytes": 400 * MB},
            {"fileBytes": MB, "totalBytes": 2 * MB},
            {"fileBytes": 95 * MB, "totalBytes": 0},
            {"fileBytes": 95 * MB, "totalBytes": 400 * MB},
            {"fileBytes": MB // 2, "totalBytes": 800 * MB},
        ])


# ---------------------------------------------------------------------------------------------------------- names
class Names(unittest.TestCase):
    def test_slugs(self):
        got = core(self, "input.map((t) => C.slugify(t))", [
            "LV ES Testimonio - Mi primer número", "", "¡¿?!", "Welcome to our table",
            "Grapevine and La Viña - ways to carry the message in our area", "a" * 60, "GV_LV  Our   booth"])
        self.assertEqual(got, ["lv-es-testimonio-mi-primer-numero", "file", "file", "welcome-to-our-table",
                               "grapevine-and-la-vina-ways-to-carry-the", "a" * 40, "gv-lv-our-booth"])
        self.assertTrue(all(len(s) <= 40 for s in got))

    def test_stamps(self):
        a = {"file_id": "1AbCdEfGhIjK", "modified": "2026-09-30T12:00:00Z", "size_bytes": 1234}
        got = core(self, "[C.stampOf({ stamp: 'AB-12_cd' }), C.stampOf({ stamp: 'x'.repeat(30) }), C.stampOf(input.a),"
                         " C.stampOf(input.a), C.stampOf({ ...input.a, modified: '2026-10-01T12:00:00Z' }),"
                         " C.stampOf({ ...input.a, size_bytes: 1235 }), C.stampOf({ ...input.a, stamp: '!!' })]", {"a": a})
        self.assertEqual(got[0], "ab12cd")
        self.assertEqual(got[1], "x" * 16)
        self.assertRegex(got[2], r"^[0-9a-f]{10}$")
        self.assertEqual(got[2], got[3], "the same file, the same stamp")
        self.assertEqual(len({got[2], got[4], got[5]}), 3, "a new version (modified time or size) changes it")
        self.assertEqual(got[6], got[2], "a stamp with nothing usable in it: made here")

    def test_file_names(self):
        item = {"file_id": "1AbCdEfGhIjK", "stamp": "ab12cd", "title": "Mi primer número", "name": "LV ES Mi primer número.mp4",
                "mime": "video/mp4"}
        got = core(self, """[
          C.fileName(input.item, "video/mp4"),
          C.fileName(input.item, "VIDEO/QUICKTIME; codecs=avc1"),
          C.fileName(input.item, "application/octet-stream"),
          C.fileName({ ...input.item, name: "clip.MOV" }, "application/octet-stream"),
          C.fileName({ ...input.item, name: "clip" }, ""),
          C.fileName({ ...input.item, name: "clip", mime: "" }, ""),
          C.fileName({ ...input.item, title: "", name: "IMG_2045.JPG", mime: "image/jpeg" }, "image/jpeg"),
          C.stemOf(input.item),
        ]""", {"item": item})
        self.assertEqual(got, ["ab12cd-mi-primer-numero.mp4", "ab12cd-mi-primer-numero.mov", "ab12cd-mi-primer-numero.mp4",
                               "ab12cd-mi-primer-numero.mov", "ab12cd-mi-primer-numero.mp4", "ab12cd-mi-primer-numero.bin",
                               "ab12cd-img-2045.jpg", "ab12cd-mi-primer-numero"])
        for name in got[:7]:
            self.assertRegex(name, r"^[a-z0-9]{1,16}-[a-z0-9-]{1,40}\.[a-z0-9]{1,5}$", "a plain web address")

    def test_extensions_and_types(self):
        spec = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "video/mp4": "mp4",
                "video/webm": "webm", "video/quicktime": "mov", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/ogg": "ogg",
                "audio/wav": "wav"}
        got = core(self, "Object.fromEntries(Object.keys(input).map((t) => [t, C.extFor(t, '')]))", spec)
        self.assertEqual(got, spec, "the SPEC's table (§2.3)")
        got = core(self, """[
          C.extFor("Image/JPEG; charset=binary", ""), C.extFor("audio/x-wav", ""), C.extFor("audio/x-m4a", ""),
          C.extFor("", "a.JPEG"), C.extFor("", "song.Mp3"), C.extFor("", "a.exe"), C.extFor("", "a.pdf"),
          C.extFor("", "noext"), C.extFor("text/html", "page.html"), C.extFor("application/octet-stream", "v.webm"),
          C.extOf("", "x", "audio/mpeg"), C.extOf("", "", ""),
          C.typeForExt("jpg"), C.typeForExt(".JPEG"), C.typeForExt("mov"), C.typeForExt("m4a"), C.typeForExt("mp3"),
          C.typeForExt("webm"), C.typeForExt("exe"), C.typeForExt(""),
          C.savedStamp("st1-words.jpg"), C.savedStamp("Thumbs.db"), C.savedStamp("abc.part"), C.savedStamp("ST1-X.JPG"),
        ]""")
        self.assertEqual(got, ["jpg", "wav", "m4a", "jpg", "mp3", "", "", "", "", "webm", "mp3", "bin",
                               "image/jpeg", "image/jpeg", "video/quicktime", "audio/mp4", "audio/mpeg", "video/webm",
                               "application/octet-stream", "application/octet-stream",
                               "st1", "", "", ""])


# ---------------------------------------------------------------------------------------------------------- the plan
def item(n: int, kind: str = "photo", **kw) -> dict:
    """A row of data/site/booth.json (SPEC §2.2) for Drive file n."""
    fid = f"F{n:09d}"
    ext = {"photo": "jpg", "poster": "png", "video": "mp4", "audio": "mp3", "message": "txt"}.get(kind, "zip")
    row = {"id": f"drive:{fid}", "file_id": fid, "name": f"GV EN File {n}.{ext}", "mime": "", "size_bytes": 1000,
           "modified": "2026-09-30T12:00:00Z", "title": f"File {n}", "kind": kind, "first": False, "until": None,
           "stamp": f"st{n}"}
    row.update(kw)
    return row


def ids(rows: list[dict]) -> list[str]:
    return [r["file_id"] for r in rows]


def codes(rows: list[dict]) -> list[tuple[str, str]]:
    return [(r["file_id"], r["code"]) for r in rows]


class Plan(unittest.TestCase):
    def plan(self, items, cfg=None, cached=None) -> dict:
        return core(self, "C.plan({ items: input.items }, input.cfg, input.cached)",
                    {"items": items, "cfg": cfg or {}, "cached": cached or []})

    def test_a_video_or_sound_file_over_the_file_limit_is_too_big(self):
        p = self.plan([item(1, "video", size_bytes=96 * MB), item(2, "video", size_bytes=95 * MB),
                       item(3, "audio", size_bytes=96 * MB + 1),
                       item(4, "photo", size_bytes=300 * MB)])   # a picture's size is its original's: never "too big"
        self.assertEqual(ids(p["downloads"]), ["F000000002", "F000000004"])
        self.assertEqual(codes(p["skipped"]), [("F000000001", "too_big"), ("F000000003", "too_big")])
        self.assertIn("too big to save for offline (96.0 MB; one video or sound file may have 95 MB — config/site.yml "
                      "booth.max_file_mb)", p["skipped"][0]["reason"])
        self.assertEqual(p["skipped"][0]["name"], "GV EN File 1.mp4")
        self.assertEqual(p["limits"], {"fileBytes": 95 * MB, "totalBytes": 400 * MB})

    def test_the_folder_limit_counts_pictures_too(self):
        rows = [item(1, "video", size_bytes=60 * MB), item(2, "video", size_bytes=30 * MB), item(3, "video", size_bytes=20 * MB),
                item(4, "photo"), item(5, "poster"), item(6, "video", size_bytes=9 * MB), item(7, "photo", first=True)]
        p = self.plan(rows, {"max_total_mb": 100})
        # 7 ("first": a 2 MB guess) · 1 (60) · 2 (30) = 92 · 3 (20) would make 112 · 4 (2) = 94 · 5 (2) = 96 · 6 (9) → 105
        self.assertEqual(ids(p["downloads"]), ["F000000007", "F000000001", "F000000002", "F000000004", "F000000005"])
        self.assertEqual(codes(p["skipped"]), [("F000000003", "over_limit"), ("F000000006", "over_limit")])
        self.assertEqual(p["bytes"], 96 * MB)
        self.assertIn("would pass 100 MB (config/site.yml booth.max_total_mb;", p["skipped"][0]["reason"])
        # pictures alone, 2 MB each until they are downloaded
        p = self.plan([item(n, "photo") for n in range(1, 5)], {"max_total_mb": 5})
        self.assertEqual(ids(p["downloads"]), ["F000000001", "F000000002"])
        self.assertEqual([c for _f, c in codes(p["skipped"])], ["over_limit", "over_limit"])
        got = core(self, "[C.fits(0, 10, { totalBytes: 10 }), C.fits(1, 10, { totalBytes: 10 })]")
        self.assertEqual(got, [True, False])

    def test_the_first_files_come_first(self):
        p = self.plan([item(1), item(2, first=True), item(3), item(4, first=True)])
        self.assertEqual(ids(p["downloads"]), ["F000000002", "F000000004", "F000000001", "F000000003"])

    def test_saved_files_are_kept_by_their_stamp_and_counted_by_their_size(self):
        cached = [{"name": "st1-old-words.jpg", "bytes": 123}, {"name": "st2-file-2.mp4", "bytes": int(2.5 * MB)}]
        rows = [item(1, "photo", title="New words"), item(2, "video", size_bytes=None), item(3, "photo")]
        p = self.plan(rows, {"max_total_mb": 4}, cached)
        # a new title keeps the saved name (a device that saved the file keeps its copy)
        self.assertEqual([(r["file_id"], r["file"], r["bytes"], r["group"]) for r in p["reuse"]],
                         [("F000000001", "st1-old-words.jpg", 123, "picture"), ("F000000002", "st2-file-2.mp4", int(2.5 * MB), "media")])
        self.assertEqual(p["downloads"], [])
        self.assertEqual(codes(p["skipped"]), [("F000000003", "over_limit")], "123 B + 2.5 MB + a 2 MB guess pass 4 MB")
        self.assertEqual(p["delete"], [])
        self.assertEqual(p["bytes"], 123 + int(2.5 * MB))

    def test_everything_else_in_the_folder_is_deleted(self):
        cached = [{"name": "st1-x.jpg", "bytes": 10}, {"name": "st9-gone.jpg", "bytes": 10}, {"name": "Thumbs.db", "bytes": 1},
                  {"name": "st2-empty.jpg", "bytes": 0}, {"name": "ST3-X.JPG", "bytes": 10}, {"name": "st4-v.mp4", "bytes": 50 * MB},
                  {"name": "st5-a.jpg", "bytes": 10}, {"name": "st5-b.jpg", "bytes": 10}, "st6-name-only.png"]
        rows = [item(1), item(2), item(3), item(4, "video", size_bytes=None), item(5), item(6, "poster")]
        p = self.plan(rows, {"max_file_mb": 10}, cached)
        self.assertEqual(sorted(r["file"] for r in p["reuse"]), ["st1-x.jpg", "st5-a.jpg", "st6-name-only.png"])
        self.assertEqual(ids(p["downloads"]), ["F000000002", "F000000003"], "an empty file, a name not ours: downloaded again")
        self.assertEqual(codes(p["skipped"]), [("F000000004", "too_big")], "saved before the limit went down")
        self.assertEqual(sorted(p["delete"]), sorted(["st9-gone.jpg", "Thumbs.db", "st2-empty.jpg", "ST3-X.JPG", "st4-v.mp4", "st5-b.jpg"]))

    def test_messages_need_nothing(self):
        p = self.plan([item(1, "message"), item(2, "unsupported"), item(3, "poster"), {"kind": "photo"}, "junk", None, [1]])
        self.assertEqual(ids(p["downloads"]), ["F000000003"])
        self.assertEqual([(s["code"], s["reason"]) for s in p["skipped"]], [("no_file", "no Drive file id in data/site/booth.json")])
        self.assertEqual(p["reuse"], [])

    def test_files_past_their_last_day_are_not_saved(self):
        rows = [item(1, until="2026-10-01"), item(2, until="2026-10-02"), item(3, until="someday"), item(4, until="2026-10-03")]
        cached = [{"name": "st1-file-1.jpg", "bytes": 10}]
        p = self.plan(rows, {"today": "2026-10-02"}, cached)
        self.assertEqual(ids(p["downloads"]), ["F000000002", "F000000003", "F000000004"], "the last day itself still counts")
        self.assertEqual([(s["file_id"], s["code"], s["reason"]) for s in p["skipped"]],
                         [("F000000001", "expired", "past its last day (2026-10-01), so it is not saved")])
        self.assertEqual(p["delete"], ["st1-file-1.jpg"])
        p = self.plan(rows, {}, cached)                       # without a day the core never guesses one
        self.assertEqual(len(p["downloads"]) + len(p["reuse"]), 4)

    def test_file_ids(self):
        rows = [item(1, file_id="", id="x"), item(2, file_id=None), item(3), item(3, title="Again")]
        p = self.plan(rows)
        self.assertEqual(ids(p["downloads"]), ["F000000002", "F000000003"], "the id from drive:<id>; listed twice: once")
        self.assertEqual([s["code"] for s in p["skipped"]], ["no_file"])

    def test_addresses_limits_and_times(self):
        rows = [item(1, "photo"), item(2, "video", size_bytes=5 * MB), item(3, "audio", size_bytes=None),
                item(4, "poster", image_url="https://lh3.googleusercontent.com/d/F000000004=s1920"),
                item(5, "video", download_url="https://example.org/v.mp4"), item(6, "photo", image_url="javascript:alert(1)")]
        d = {x["file_id"]: x for x in self.plan(rows)["downloads"]}
        self.assertEqual(d["F000000001"]["url"], "https://lh3.googleusercontent.com/d/F000000001=s1920")
        self.assertEqual(d["F000000002"]["url"],
                         "https://drive.usercontent.google.com/download?id=F000000002&export=download&confirm=t")
        self.assertEqual(d["F000000005"]["url"], "https://example.org/v.mp4", "booth.json's own address")
        self.assertEqual(d["F000000006"]["url"], "https://lh3.googleusercontent.com/d/F000000006=s1920", "not a web address")
        keys = ("group", "estimate", "expect_bytes", "max_bytes", "timeout_ms")
        self.assertEqual({k: d["F000000001"][k] for k in keys},
                         {"group": "picture", "estimate": 2 * MB, "expect_bytes": None, "max_bytes": 30 * MB, "timeout_ms": 60000})
        self.assertEqual({k: d["F000000002"][k] for k in keys},
                         {"group": "media", "estimate": 5 * MB, "expect_bytes": 5 * MB, "max_bytes": 95 * MB, "timeout_ms": 480000})
        self.assertEqual((d["F000000003"]["estimate"], d["F000000003"]["expect_bytes"], d["F000000003"]["max_bytes"]),
                         (0, None, 95 * MB), "a sound file of unknown size: the downloader caps it at the room left")
        self.assertEqual(d["F000000004"]["stem"], "st4-file-4")

    def test_video_and_sound_files_of_unknown_size_are_all_planned(self):
        # booth.json has no sizes without GOOGLE_API_KEY: counted as 95 MB each, only 4 would fit in 400 MB —
        # however small they really are. They are all planned; the downloader checks the real sizes.
        rows = [item(n, "video" if n % 2 else "audio", size_bytes=None) for n in range(1, 11)]
        p = self.plan(rows)
        self.assertEqual(len(p["downloads"]), 10)
        self.assertEqual((p["skipped"], p["bytes"]), ([], 0))
        self.assertEqual({(d["estimate"], d["expect_bytes"], d["max_bytes"]) for d in p["downloads"]}, {(0, None, 95 * MB)})
        # pictures and known sizes still count (and still meet the limit at planning time); unknown sizes never do
        rows = [item(1, "video", size_bytes=3 * MB), item(2, "video", size_bytes=None), item(3, "photo"),
                item(4, "video", size_bytes=2 * MB), item(5, "audio", size_bytes=None)]
        p = self.plan(rows, {"max_total_mb": 5})
        self.assertEqual(ids(p["downloads"]), ["F000000001", "F000000002", "F000000003", "F000000005"])
        self.assertEqual(codes(p["skipped"]), [("F000000004", "over_limit")], "3 MB + a 2 MB guess + 2 MB pass 5 MB")
        self.assertEqual(p["bytes"], 5 * MB)

    def test_garbage_in_nothing_out(self):
        got = core(self, "[C.plan(null, null, null), C.plan({ items: 'x' }, {}, 'y'), "
                         "C.plan({ items: [null, 1, 'a', []] }, {}, [null, 1, {}])]")
        for p in got:
            self.assertEqual((p["downloads"], p["reuse"], p["delete"], p["skipped"], p["bytes"]), ([], [], [], [], 0))


# ---------------------------------------------------------------------------------------------------------- pictures
def png_header(w: int, h: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0) + bytes(4)


def gif_header(w: int, h: int, version: bytes = b"89a") -> bytes:
    return b"GIF" + version + struct.pack("<HH", w, h) + b"\xf7\x00\x00"


def exif_segment(orientation: int, little: bool = True) -> bytes:
    """A JPEG APP1 segment whose EXIF holds only the orientation (tag 0x0112, a SHORT) in IFD0."""
    e = "<" if little else ">"
    tiff = (b"II" if little else b"MM") + struct.pack(e + "HI", 42, 8)
    ifd = struct.pack(e + "H", 1) + struct.pack(e + "HHI", 0x0112, 3, 1) + struct.pack(e + "HH", orientation, 0) + struct.pack(e + "I", 0)
    data = b"Exif\0\0" + tiff + ifd
    return b"\xff\xe1" + struct.pack(">H", len(data) + 2) + data


def jpeg_header(w: int, h: int, sof: int = 0xC0, app1: bytes = b"", scan_first: bool = False) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\0\x01\x01\0\0\x01\0\x01\0\0"
    dqt = b"\xff\xdb" + struct.pack(">H", 67) + bytes(65)
    dht = b"\xff\xc4" + struct.pack(">H", 31) + bytes(29)           # C4: inside the SOF range, but not a frame header
    frame = bytes([0xFF, sof]) + struct.pack(">HBHHB", 17, 8, h, w, 3) + b"\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    scan = b"\xff\xda" + struct.pack(">H", 12) + bytes(10)
    return b"\xff\xd8" + app0 + app1 + dqt + dht + (scan + frame if scan_first else frame + scan) + bytes(16) + b"\xff\xd9"


def riff_webp(fourcc: bytes, chunk: bytes) -> bytes:
    body = fourcc + struct.pack("<I", len(chunk)) + chunk
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body


def webp_vp8(w: int, h: int, scale_bits: int = 0) -> bytes:
    return riff_webp(b"VP8 ", b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", w | scale_bits, h | scale_bits) + bytes(10))


def webp_vp8l(w: int, h: int) -> bytes:
    return riff_webp(b"VP8L", b"\x2f" + struct.pack("<I", (w - 1) | ((h - 1) << 14)) + bytes(8))


def webp_vp8x(w: int, h: int) -> bytes:
    return riff_webp(b"VP8X", b"\x10\0\0\0" + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little"))


class Pictures(unittest.TestCase):
    def sizes(self, blobs: list[bytes]) -> list:
        return core(self, 'input.map((s) => C.imageSize(Buffer.from(s, "base64")))', [b64(x) for x in blobs])

    def test_hand_made_headers(self):
        blobs = [png_header(3000, 2000), gif_header(17, 9, b"87a"), gif_header(640, 480),
                 jpeg_header(1920, 1080), jpeg_header(800, 600, sof=0xC2), jpeg_header(1, 65535, sof=0xC1),
                 webp_vp8(1024, 768, scale_bits=0xC000), webp_vp8l(4000, 3000), webp_vp8x(20000, 100)]
        self.assertEqual(self.sizes(blobs), [
            {"type": "image/png", "w": 3000, "h": 2000},
            {"type": "image/gif", "w": 17, "h": 9},
            {"type": "image/gif", "w": 640, "h": 480},
            {"type": "image/jpeg", "w": 1920, "h": 1080},
            {"type": "image/jpeg", "w": 800, "h": 600},             # progressive
            {"type": "image/jpeg", "w": 1, "h": 65535},
            {"type": "image/webp", "w": 1024, "h": 768},            # lossy: the two scale bits are not the size
            {"type": "image/webp", "w": 4000, "h": 3000},           # lossless
            {"type": "image/webp", "w": 20000, "h": 100},           # extended
        ])

    def test_a_phone_photo_turned_by_its_exif_note(self):
        blobs = [jpeg_header(1920, 1080, app1=exif_segment(6)), jpeg_header(1920, 1080, app1=exif_segment(8, little=False)),
                 jpeg_header(1920, 1080, app1=exif_segment(5)), jpeg_header(1920, 1080, app1=exif_segment(3)),
                 jpeg_header(1920, 1080, app1=exif_segment(1, little=False)), jpeg_header(1920, 1080, app1=exif_segment(9)),
                 # an APP1 that is not EXIF (XMP) changes nothing
                 jpeg_header(1920, 1080, app1=b"\xff\xe1" + struct.pack(">H", 2 + 29) + b"http://ns.adobe.com/xap/1.0/\0")]
        self.assertEqual([(s["w"], s["h"]) for s in self.sizes(blobs)],
                         [(1080, 1920), (1080, 1920), (1080, 1920), (1920, 1080), (1920, 1080), (1920, 1080), (1920, 1080)])

    def test_anything_else_or_cut_short_is_none(self):
        png, jpg, vp8 = png_header(10, 10), jpeg_header(10, 10), webp_vp8(10, 10)
        blobs = [b"", b"hello world", png[:20], jpg[:jpg.index(b"\xff\xc0") + 6], jpeg_header(10, 10, scan_first=True),
                 jpeg_header(0, 10), png_header(0, 5), vp8[:28], b"RIFF\x24\x00\x00\x00WAVEfmt ", b"\xff\xd8",
                 b"\x00\x00\x00\x18ftypmp42" + bytes(20)]
        self.assertEqual(self.sizes(blobs), [None] * len(blobs))

    @unittest.skipIf(Image is None, "needs Pillow")
    def test_real_files(self):
        def make(fmt: str, size: tuple[int, int], mode: str = "RGB", **save) -> bytes:
            im = Image.new(mode, size, (200, 30, 90) if mode == "RGB" else (200, 30, 90, 128))
            buf = io.BytesIO()
            im.save(buf, fmt, **save)
            return buf.getvalue()
        exif = Image.Exif()
        exif[0x0112] = 6
        cases = [
            (make("PNG", (37, 23)), {"type": "image/png", "w": 37, "h": 23}),
            (make("PNG", (37, 23), "RGBA"), {"type": "image/png", "w": 37, "h": 23}),
            (make("JPEG", (41, 29)), {"type": "image/jpeg", "w": 41, "h": 29}),
            (make("JPEG", (41, 29), progressive=True), {"type": "image/jpeg", "w": 41, "h": 29}),
            (make("JPEG", (41, 29), exif=exif.tobytes()), {"type": "image/jpeg", "w": 29, "h": 41}),
            (make("GIF", (17, 9)), {"type": "image/gif", "w": 17, "h": 9}),
            (make("WEBP", (33, 21)), {"type": "image/webp", "w": 33, "h": 21}),
            (make("WEBP", (33, 21), lossless=True), {"type": "image/webp", "w": 33, "h": 21}),
            (make("WEBP", (33, 21), "RGBA"), {"type": "image/webp", "w": 33, "h": 21}),
        ]
        # the three kinds of WebP really are there
        self.assertEqual([c[0][12:16] for c in cases[6:]], [b"VP8 ", b"VP8L", b"VP8X"])
        self.assertEqual(self.sizes([c[0] for c in cases]), [c[1] for c in cases])


# ---------------------------------------------------------------------------------------------------------- web pages
class WebPages(unittest.TestCase):
    def test_an_answer_that_is_a_web_page_is_not_the_file(self):
        virus = (b'<!DOCTYPE html><html><head><title>Google Drive - Virus scan warning</title><meta http-equiv="content-type" '
                 b'content="text/html; charset=utf-8"/></head><body>Google Drive can\'t scan this file for viruses.</body></html>')
        cases = [
            (b"", "text/html; charset=utf-8", True),
            (b"", "application/xhtml+xml", True),
            (virus, "application/octet-stream", True),
            (b"\xef\xbb\xbf \r\n <!-- a note --> <html lang=\"en\">", "", True),
            (b"<HTML><BODY>Quota exceeded</BODY></HTML>", "video/mp4", True),
            (b"<head><title>Sign in</title>", None, True),
            (png_header(2, 2), "image/png", False),
            (b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>', "image/svg+xml", False),
            (b"<svg></svg>", "", False),
            (b'{"error": "rate limited"}', "application/json", False),
            (b"<!-- never closed <html>", "", False),
            (b"\x00\x00\x00\x18ftypmp42", "video/mp4", False),
            (b"", "", False),
        ]
        got = core(self, 'input.map(([s, t]) => C.isHtml(Buffer.from(s, "base64"), t))', [[b64(b), t] for b, t, _ in cases])
        self.assertEqual(got, [want for _b, _t, want in cases])


# ---------------------------------------------------------------------------------------------------------- results
class Results(unittest.TestCase):
    def test_the_manifest(self):
        entries = [{"file_id": "F1", "file": "st1-a.jpg", "bytes": 10, "type": "image/jpeg", "w": 4, "h": 3},
                   {"file_id": "F2", "file": "st2-b.mp4", "bytes": 20},
                   {"file_id": "", "file": "x.jpg"}, {"file_id": "F3"}, None]
        skipped = [{"file_id": "F4", "name": "big.mp4", "kind": "video", "code": "too_big", "reason": "too big"},
                   {"name": "no id", "reason": "?"}, None]
        got = core(self, "C.manifestOf(input.entries, input.skipped, '2026-10-02T12:00:00.000Z')",
                   {"entries": entries, "skipped": skipped})
        self.assertEqual(got, {
            "built": "2026-10-02T12:00:00.000Z",
            "items": {"F1": {"file": "st1-a.jpg", "bytes": 10, "type": "image/jpeg", "w": 4, "h": 3},
                      "F2": {"file": "st2-b.mp4", "bytes": 20, "type": "video/mp4", "w": None, "h": None}},
            "skipped": [{"file_id": "F4", "name": "big.mp4", "reason": "too big", "code": "too_big"},
                        {"file_id": None, "name": "no id", "reason": "?", "code": "failed"}],
        })
        self.assertEqual(core(self, "C.manifestOf(null, null)"), {"built": None, "items": {}, "skipped": []})

    def test_warning_lines_and_sizes(self):
        got = core(self, """[
          C.annotation("Booth display: a file, not saved", "50% done\\r\\nnext line"),
          C.annotation("T", "m", "notice"),
          [0, 512, 1023, 1024, 1536, 12.3 * 1024 * 1024, 3 * 1024 ** 3, -5, "x"].map(C.formatBytes),
          [95 * C.MB, 0.5 * C.MB, 400 * C.MB].map(C.mbLabel),
        ]""")
        self.assertEqual(got[0], "::warning title=Booth display%3A a file%2C not saved::50%25 done%0D%0Anext line")
        self.assertEqual(got[1], "::notice title=T::m")
        self.assertEqual(got[2], ["0 B", "512 B", "1023 B", "1.0 KB", "1.5 KB", "12.3 MB", "3.0 GB", "-5 B", "0 B"])
        self.assertEqual(got[3], ["95 MB", "0.5 MB", "400 MB"])

    def test_reasons(self):
        got = core(self, """[
          C.reasonText("too_big", { bytes: 120 * C.MB, limit: 95 * C.MB }),
          C.reasonText("too_big", { atLeast: true, bytes: 96 * C.MB, limit: 95 * C.MB }),
          C.reasonText("html"), C.reasonText("incomplete", { detail: "5 of 9 bytes arrived" }),
          C.reasonText("out_of_time"), C.reasonText("failed", { detail: "HTTP 503" }), C.reasonText("whatever"),
        ]""")
        self.assertEqual(got[0], "too big to save for offline (120.0 MB; one video or sound file may have 95 MB — config/site.yml booth.max_file_mb)")
        self.assertEqual(got[1], "too big to save for offline (over the 95 MB one video or sound file may have — config/site.yml booth.max_file_mb)")
        self.assertIn("web page instead of the file", got[2])
        self.assertIn("(5 of 9 bytes arrived); the next run tries again", got[3])
        self.assertIn("ran out (the next run tries again)", got[4])
        self.assertEqual(got[5], "the download failed (HTTP 503); the next run tries again")
        self.assertEqual(got[6], "the download failed (no answer); the next run tries again")
        for text in got:
            self.assertNotRegex(text, r"(?i)\bpdf\b", "a reason may reach the player's Items list: never that word")


# ---------------------------------------------------------------------------------------------------------- downloader
class _Handler(http.server.BaseHTTPRequestHandler):
    # HTTP/1.1 with keep-alive, as Google answers: the connection stays open until the downloader has read the answer
    # and hangs up. (Closing it right after writing — HTTP/1.0 — can lose the end of a big answer on Windows.)
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802 — http.server's name
        site = self.server.site
        path = self.path.split("?", 1)[0]
        with site.lock:
            site.hits[path] += 1
            n = site.hits[path]
        route = site.routes.get(path)
        if route is None:
            self.answer(404, "text/plain", b"not here")
        else:
            route(self, n)

    def answer(self, status: int, ctype: str, body: bytes, chunked: bool = False, headers: dict | None = None):
        """chunked: the size is not announced (no Content-Length); headers: more of them."""
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        if chunked:
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            if chunked:
                for i in range(0, len(body), 65536):
                    part = body[i:i + 65536]
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(part), part))
                self.wfile.write(b"0\r\n\r\n")
            else:
                self.wfile.write(body)
        except OSError:          # the downloader stopped reading (too big): fine
            self.close_connection = True

    def handle(self):
        try:
            super().handle()
        except OSError:          # the downloader hung up
            pass

    def log_message(self, *args):
        pass


class Site:
    """A web server on 127.0.0.1 standing in for Google: routes {path: fn(handler, nth request)}; hits counts them."""

    def __init__(self, routes: dict):
        self.routes, self.hits, self.lock = routes, Counter(), threading.Lock()
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.site = self
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


PIC = png_header(64, 48) + bytes(200)
JPG = jpeg_header(40, 30)
VIDEO = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 800
VIRUS_PAGE = b"<!DOCTYPE html><html><head><title>Google Drive - Virus scan warning</title></head><body>...</body></html>"
SITE_YML = "site:\n  title: test\nbooth:\n  max_file_mb: 1\n  max_total_mb: 50\n"


def routes() -> dict:
    def flaky(h, n):
        if n == 1:
            h.answer(503, "text/plain", b"busy")
        else:
            h.answer(200, "image/png", PIC)
    return {
        "/pic.png": lambda h, n: h.answer(200, "image/png", PIC),
        "/photo": lambda h, n: h.answer(200, "application/octet-stream", JPG),        # the bytes say it is a JPEG
        "/video.mp4": lambda h, n: h.answer(200, "video/mp4", VIDEO),
        "/video2.mp4": lambda h, n: h.answer(200, "video/mp4", VIDEO),
        "/sound": lambda h, n: h.answer(200, "audio/mpeg", bytes(3 * MB), chunked=True),      # no size given
        "/html": lambda h, n: h.answer(200, "text/html; charset=utf-8", VIRUS_PAGE),
        "/html-octet": lambda h, n: h.answer(200, "application/octet-stream", VIRUS_PAGE),
        "/flaky": flaky,
        # a complete answer that brings only 500 of the file's 1000 bytes (no size announced). (A server that hangs up
        # halfway instead can cost a minute of TCP retries on Windows' loopback — not what this test is about.)
        "/short": lambda h, n: h.answer(200, "video/mp4", b"x" * 500, chunked=True),
        "/text": lambda h, n: h.answer(200, "text/plain", b"hello"),
        "/big": lambda h, n: h.answer(200, "video/mp4", VIDEO),
        "/old": lambda h, n: h.answer(200, "image/png", PIC),
    }


def booth_rows(base: str) -> list[dict]:
    return [
        item(1, "poster", title="First poster", first=True, image_url=f"{base}/pic.png", stamp="aa1"),
        item(2, "photo", image_url=f"{base}/photo", stamp="aa2"),
        item(3, "video", download_url=f"{base}/video.mp4", size_bytes=len(VIDEO), stamp="aa3"),
        item(4, "audio", download_url=f"{base}/sound", size_bytes=None, stamp="aa4"),
        item(5, "photo", image_url=f"{base}/html", stamp="aa5"),
        item(6, "photo", image_url=f"{base}/html-octet", stamp="aa6"),
        item(7, "photo", image_url=f"{base}/flaky", stamp="aa7"),
        item(8, "photo", image_url=f"{base}/missing", stamp="aa8"),
        item(9, "video", download_url=f"{base}/short", size_bytes=1000, stamp="aa9"),
        item(10, "photo", image_url=f"{base}/text", stamp="ab0"),
        item(11, "message", text="Welcome to our table", stamp="ab1"),
        item(12, "video", download_url=f"{base}/big", size_bytes=5 * MB, stamp="ab2"),
        item(13, "photo", image_url=f"{base}/old", until="2000-01-01", stamp="ab3"),
        item(14, "video", download_url=f"{base}/video2.mp4", size_bytes=12345, stamp="ab4"),
    ]


class Downloader(unittest.TestCase):
    def setUp(self):
        if not node_path():
            self.skipTest("Node.js is not installed")
        self.site = Site(routes())
        self.addCleanup(self.site.close)

    def make_root(self, booth, site_yml: str = SITE_YML) -> Path:
        root = Path(tempfile.mkdtemp(prefix="gv-booth-media-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "data" / "site").mkdir(parents=True)
        (root / "config").mkdir()
        if booth is not None:
            text = booth if isinstance(booth, str) else json.dumps(booth, ensure_ascii=False)
            (root / "data" / "site" / "booth.json").write_text(text, encoding="utf-8")
        (root / "config" / "site.yml").write_text(site_yml, encoding="utf-8")
        return root

    def run_script(self, root: Path, *args: str, **env: str) -> str:
        base = {k: v for k, v in os.environ.items()
                if not k.startswith("BOOTH_MEDIA") and k not in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY")}
        base.update({"BOOTH_MEDIA_RETRY_WAITS": "0,0", "GITHUB_ACTIONS": "true", "NODE_NO_WARNINGS": "1",
                     "GITHUB_STEP_SUMMARY": str(root / "summary.md")})
        base.update(env)
        r = subprocess.run([node_path(), str(SCRIPT), "--root", str(root), *args], cwd=root, env=base,
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(r.returncode, 0, f"exit code 0 whatever happens to the downloads:\n{r.stdout}\n{r.stderr}")
        return r.stdout

    @staticmethod
    def manifest(root: Path) -> dict:
        return json.loads((root / ".cache" / "booth-media" / "manifest.json").read_text(encoding="utf-8"))

    @staticmethod
    def saved(root: Path) -> list[str]:
        d = root / ".cache" / "booth-media" / "files"
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []

    def test_end_to_end(self):
        root = self.make_root({"updated": "2026-10-02T12:00:00Z", "fixture": False, "items": booth_rows(self.site.base)})
        out = self.run_script(root)

        # the files and the manifest
        self.assertEqual(self.saved(root), ["aa1-first-poster.png", "aa2-file-2.jpg", "aa3-file-3.mp4", "aa7-file-7.png"])
        m = self.manifest(root)
        self.assertRegex(m["built"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        self.assertEqual(m["items"], {
            "F000000001": {"file": "aa1-first-poster.png", "bytes": len(PIC), "type": "image/png", "w": 64, "h": 48},
            "F000000002": {"file": "aa2-file-2.jpg", "bytes": len(JPG), "type": "image/jpeg", "w": 40, "h": 30},
            "F000000003": {"file": "aa3-file-3.mp4", "bytes": len(VIDEO), "type": "video/mp4", "w": None, "h": None},
            "F000000007": {"file": "aa7-file-7.png", "bytes": len(PIC), "type": "image/png", "w": 64, "h": 48},
        })
        self.assertEqual((root / ".cache" / "booth-media" / "files" / "aa3-file-3.mp4").read_bytes(), VIDEO)
        # what was skipped, and why
        why = {s["file_id"]: s["code"] for s in m["skipped"]}
        self.assertEqual(why, {"F000000004": "too_big", "F000000005": "html", "F000000006": "html", "F000000008": "failed",
                               "F000000009": "incomplete", "F000000010": "failed", "F000000012": "too_big",
                               "F000000013": "expired", "F000000014": "incomplete"})
        reason = {s["file_id"]: s["reason"] for s in m["skipped"]}
        self.assertIn("over the 1 MB one video or sound file may have", reason["F000000004"])
        self.assertIn("(500 of the file's 1000 bytes arrived); the next run tries again", reason["F000000009"])
        self.assertIn("HTTP 404 — is the file still in the booth folder", reason["F000000008"])
        self.assertIn("not a picture (text/plain)", reason["F000000010"])
        self.assertIn("Google announced", reason["F000000014"])
        self.assertTrue(all(set(s) == {"file_id", "name", "reason", "code"} for s in m["skipped"]))
        # tries: a busy server twice, half an answer three times, a web page or a missing file once; nothing for the
        # files the plan skipped
        hits = self.site.hits
        self.assertEqual((hits["/flaky"], hits["/short"], hits["/html"], hits["/missing"], hits["/text"], hits["/video2.mp4"]),
                         (2, 3, 1, 1, 1, 1))
        self.assertEqual((hits["/big"], hits["/old"]), (0, 0))
        # the yellow warnings (none for a file past its day), the run summary, nothing half-downloaded left
        warnings = [ln for ln in out.splitlines() if ln.startswith("::warning title=Booth display%3A a file was not saved for offline::")]
        self.assertEqual(len(warnings), 8, out)
        self.assertFalse(any("GV EN File 13" in w for w in warnings))
        self.assertIn("1 file(s) past their last day: not saved.", out)
        self.assertIn("4 file(s) saved for offline", out)
        summary = (root / "summary.md").read_text(encoding="utf-8")
        self.assertIn("**Booth display (copies for offline):** 4 file(s) saved for offline", summary)
        self.assertIn("- Not saved: GV EN File 12.mp4 — too big to save for offline (5.0 MB;", summary)
        self.assertFalse((root / ".cache" / "booth-media" / "tmp").exists())

        # a second run downloads nothing it has (and tries the others again)
        self.site.hits.clear()
        out = self.run_script(root)
        self.assertEqual((hits["/pic.png"], hits["/photo"], hits["/video.mp4"], hits["/flaky"]), (0, 0, 0, 0))
        self.assertEqual(hits["/missing"], 1)
        self.assertIn("0 downloaded (0 B), 4 kept from the last run, 0 removed", out)
        self.assertEqual(self.manifest(root)["items"], m["items"])

        # a file no longer listed, a stranger in the folder and a stopped run's leftover are removed
        rows = [r for r in booth_rows(self.site.base) if r["file_id"] != "F000000002"]
        (root / "data" / "site" / "booth.json").write_text(json.dumps({"items": rows}), encoding="utf-8")
        (root / ".cache" / "booth-media" / "files" / "junk.txt").write_text("x", encoding="utf-8")
        (root / ".cache" / "booth-media" / "tmp").mkdir()
        (root / ".cache" / "booth-media" / "tmp" / "aa9-file-9.part").write_bytes(b"half")
        out = self.run_script(root)
        self.assertEqual(self.saved(root), ["aa1-first-poster.png", "aa3-file-3.mp4", "aa7-file-7.png"])
        self.assertEqual(sorted(self.manifest(root)["items"]), ["F000000001", "F000000003", "F000000007"])
        self.assertIn("2 removed", out)
        self.assertFalse((root / ".cache" / "booth-media" / "tmp").exists())

    def test_dry_run_and_booth_media_0_change_nothing(self):
        root = self.make_root({"items": booth_rows(self.site.base)})
        out = self.run_script(root, "--dry-run")
        self.assertIn("--dry-run: nothing is downloaded, deleted or written", out)
        self.assertIn("  download: 11\n", out)
        self.assertIn("  skip: 2\n", out)
        self.assertFalse((root / ".cache").exists())
        self.assertEqual(sum(self.site.hits.values()), 0)
        # BOOTH_MEDIA=0: the folder and its manifest stay exactly as they are
        files = root / ".cache" / "booth-media" / "files"
        files.mkdir(parents=True)
        (files / "zz1-old.png").write_bytes(PIC)
        old = '{"built": "then", "items": {}, "skipped": []}\n'
        (root / ".cache" / "booth-media" / "manifest.json").write_text(old, encoding="utf-8")
        out = self.run_script(root, BOOTH_MEDIA="0")
        self.assertIn("BOOTH_MEDIA=0", out)
        self.assertEqual(self.saved(root), ["zz1-old.png"])
        self.assertEqual((root / ".cache" / "booth-media" / "manifest.json").read_text(encoding="utf-8"), old)
        self.assertEqual(sum(self.site.hits.values()), 0)

    def test_booth_json_missing_empty_sample_or_unreadable(self):
        cases = [(None, "not there", False), ("", "lists no booth files", False), ({"items": []}, "lists no booth files", False),
                 ({"fixture": True, "items": booth_rows(self.site.base)}, "sample data", False),
                 ("{not json", "could not be read", True)]
        for booth, words, kept in cases:
            with self.subTest(booth=str(booth)[:40]):
                root = self.make_root(booth)
                files = root / ".cache" / "booth-media" / "files"
                files.mkdir(parents=True)
                (files / "zz1-old.png").write_bytes(PIC)
                (root / ".cache" / "booth-media" / "manifest.json").write_text(
                    json.dumps({"built": "then", "items": {"F1": {"file": "zz1-old.png"}}, "skipped": []}), encoding="utf-8")
                out = self.run_script(root)
                m = self.manifest(root)
                self.assertEqual((m["items"], m["skipped"]), ({}, []), "an empty manifest")
                self.assertIn(f"data/site/booth.json {words}", out)
                self.assertEqual(self.saved(root), ["zz1-old.png"] if kept else [], "unreadable: kept for the next run")
                if kept:
                    self.assertIn("::warning title=Booth display::data/site/booth.json could not be read", out)
        self.assertEqual(sum(self.site.hits.values()), 0)

    def test_a_compressed_answer_is_saved_whole(self):
        # fetch hands over the bytes uncompressed; the announced length is the compressed one — not a short download
        self.site.routes["/gz.png"] = lambda h, n: h.answer(200, "image/png", gzip.compress(PIC), headers={"Content-Encoding": "gzip"})
        root = self.make_root({"items": [item(1, "photo", image_url=f"{self.site.base}/gz.png", stamp="cc1")]})
        self.run_script(root)
        self.assertEqual(self.manifest(root)["items"],
                         {"F000000001": {"file": "cc1-file-1.png", "bytes": len(PIC), "type": "image/png", "w": 64, "h": 48}})
        self.assertEqual((root / ".cache" / "booth-media" / "files" / "cc1-file-1.png").read_bytes(), PIC)

    def test_out_of_time(self):
        root = self.make_root({"items": booth_rows(self.site.base)})
        self.run_script(root, BOOTH_MEDIA_MINUTES="0")
        m = self.manifest(root)
        self.assertEqual(m["items"], {})
        self.assertEqual(sum(1 for s in m["skipped"] if s["code"] == "out_of_time"), 11)
        self.assertIn("ran out (the next run tries again)", m["skipped"][-1]["reason"])
        self.assertEqual(sum(self.site.hits.values()), 0)

    def test_the_folder_limit_with_the_real_sizes(self):
        big = png_header(1000, 900) + bytes(int(2.7 * MB))         # bigger than the 2 MB a picture is guessed at
        self.site.routes.update({"/big.png": lambda h, n: h.answer(200, "image/png", big),
                                 "/small.png": lambda h, n: h.answer(200, "image/png", PIC)})
        rows = [item(1, "photo", image_url=f"{self.site.base}/big.png", stamp="bb1"),
                item(2, "photo", image_url=f"{self.site.base}/small.png", stamp="bb2")]
        # 2.5 MB: the big picture is planned (a 2 MB guess) but 2.7 MB once downloaded — not kept; the small one
        # never fitted the plan (2 + 2 MB)
        root = self.make_root({"items": rows}, "booth:\n  max_total_mb: 2.5\n")
        self.run_script(root)
        m = self.manifest(root)
        self.assertEqual((m["items"], [(s["file_id"], s["code"]) for s in m["skipped"]]),
                         ({}, [("F000000002", "over_limit"), ("F000000001", "over_limit")]))
        self.assertEqual(self.saved(root), [])
        self.assertEqual((self.site.hits["/big.png"], self.site.hits["/small.png"]), (1, 0))
        # 4 MB: the big one is kept; then 2.7 MB + the small one's 2 MB guess would pass 4 MB, so it is not tried
        self.site.hits.clear()
        root = self.make_root({"items": rows}, "booth:\n  max_total_mb: 4\n")
        self.run_script(root)
        m = self.manifest(root)
        self.assertEqual(sorted(m["items"]), ["F000000001"])
        self.assertEqual(m["items"]["F000000001"]["w"], 1000)
        self.assertEqual([(s["file_id"], s["code"]) for s in m["skipped"]], [("F000000002", "over_limit")])
        self.assertEqual((self.site.hits["/big.png"], self.site.hits["/small.png"]), (1, 0))

    def test_files_of_unknown_size_fill_the_room_really_left(self):
        # No sizes in booth.json (the live sync without GOOGLE_API_KEY). 1 MB a file, 2 MB in all: three clips of
        # 600 KB are all saved (counted as 1 MB each, only two would have been tried)
        clip = b"\x00\x00\x00\x18ftypmp42" + bytes(600 * 1024 - 12)
        for n in range(1, 4):
            self.site.routes[f"/clip{n}"] = lambda h, n_: h.answer(200, "video/mp4", clip, chunked=True)
        rows = [item(n, "video", download_url=f"{self.site.base}/clip{n}", size_bytes=None, stamp=f"dd{n}") for n in range(1, 4)]
        root = self.make_root({"items": rows}, "booth:\n  max_file_mb: 1\n  max_total_mb: 2\n")
        out = self.run_script(root, "--dry-run")
        self.assertIn("  download: 3\n", out)
        self.assertIn("  skip: 0\n", out)
        self.assertIn("the folder afterwards: about 0 B + 3 video or sound file(s) of unknown size", out)
        self.run_script(root)
        m = self.manifest(root)
        self.assertEqual(sorted(m["items"]), ["F000000001", "F000000002", "F000000003"])
        self.assertEqual(m["skipped"], [])
        self.assertEqual(self.saved(root), ["dd1-file-1.mp4", "dd2-file-2.mp4", "dd3-file-3.mp4"])

    def test_a_download_of_unknown_size_stops_where_the_room_ends(self):
        # 1 MB a file, 1.5 MB in all. Two 600 KB clips leave 336 KB: the third (600 KB, streamed without a size) is
        # stopped there — over the FOLDER's limit, not too big —, nothing of it is kept, and the files after it are
        # still tried: a small clip that fits, one that announces 600 KB (over the room, within the file limit:
        # over_limit, without downloading it) and one that announces 1.5 MB (over the one-file limit: too big)
        clip = b"\x00\x00\x00\x18ftypmp42" + bytes(600 * 1024 - 12)
        small = b"\x00\x00\x00\x18ftypmp42" + bytes(50 * 1024 - 12)
        self.site.routes.update({
            "/c1": lambda h, n: h.answer(200, "video/mp4", clip, chunked=True),
            "/c2": lambda h, n: h.answer(200, "audio/mpeg", clip, chunked=True),
            "/c3": lambda h, n: h.answer(200, "video/mp4", clip, chunked=True),
            "/c4": lambda h, n: h.answer(200, "video/mp4", small, chunked=True),
            "/c5": lambda h, n: h.answer(200, "video/mp4", clip),                          # a Content-Length
            "/c6": lambda h, n: h.answer(200, "video/mp4", bytes(int(1.5 * MB))),
        })
        rows = [item(n, "audio" if n == 2 else "video", download_url=f"{self.site.base}/c{n}", size_bytes=None,
                     stamp=f"ee{n}") for n in range(1, 7)]
        root = self.make_root({"items": rows}, "booth:\n  max_file_mb: 1\n  max_total_mb: 1.5\n")
        out = self.run_script(root)
        m = self.manifest(root)
        self.assertEqual(sorted(m["items"]), ["F000000001", "F000000002", "F000000004"])
        self.assertEqual([(s["file_id"], s["code"]) for s in m["skipped"]],
                         [("F000000003", "over_limit"), ("F000000005", "over_limit"), ("F000000006", "too_big")])
        reason = {s["file_id"]: s["reason"] for s in m["skipped"]}
        self.assertIn("the booth folder's saved files would pass 1.5 MB (config/site.yml booth.max_total_mb", reason["F000000003"])
        self.assertIn("would pass 1.5 MB", reason["F000000005"])
        self.assertIn("too big to save for offline (1.5 MB; one video or sound file may have 1 MB", reason["F000000006"])
        # nothing half-downloaded kept: only the saved files, no .part left, no tmp folder
        self.assertEqual(self.saved(root), ["ee1-file-1.mp4", "ee2-file-2.mp3", "ee4-file-4.mp4"])
        self.assertFalse((root / ".cache" / "booth-media" / "tmp").exists())
        self.assertEqual(sum(m["items"][f]["bytes"] for f in m["items"]), 2 * len(clip) + len(small))
        # each asked once (a full folder is not worth another try now)
        self.assertEqual([self.site.hits[f"/c{n}"] for n in range(1, 7)], [1] * 6)
        self.assertIn("GV EN File 3.mp4: not saved for offline: the booth folder's saved files would pass 1.5 MB", out)
        # the folder full to the byte: the next file of unknown size is not even asked for
        self.site.hits.clear()
        exact = self.make_root({"items": rows[:2] + [rows[3]]}, f"booth:\n  max_file_mb: 1\n  max_total_mb: {1200 / 1024}\n")
        self.run_script(exact)
        m = self.manifest(exact)
        self.assertEqual((sorted(m["items"]), [(s["file_id"], s["code"]) for s in m["skipped"]]),
                         (["F000000001", "F000000002"], [("F000000004", "over_limit")]))
        self.assertEqual(self.site.hits["/c4"], 0)


# ---------------------------------------------------------------------------------------------------------- workflow
RESTORE = "Restore the booth display's media (saved between runs)"
DOWNLOAD = "Download the booth display's photos and videos (Drive booth folder)"
KEY = "Work out the booth display's media cache key"
SAVE = "Save the booth display's media for the next run (only when this run changed it)"
BOOTH_HASH = "${{ hashFiles('data/site/booth.json', 'config/site.yml') }}"


def bash_path() -> str | None:
    """A bash that runs the workflow's script here: Linux / macOS bash, or Git Bash on Windows — never WSL's launcher
    in System32 (the same rule as tests/test_morning.py)."""
    b = shutil.which("bash")
    if b and not (os.name == "nt" and "\\windows\\" in b.lower()):
        return b
    if os.name == "nt":
        for cand in (r"C:\Program Files\Git\usr\bin\bash.exe", r"C:\Program Files\Git\bin\bash.exe"):
            if Path(cand).exists():
                return cand
    return None


class Workflow(unittest.TestCase):
    def setUp(self):
        self.text = (WF / "update.yml").read_text(encoding="utf-8")
        self.job = yaml.safe_load(self.text)["jobs"]["build-deploy"]
        self.names = [s.get("name") for s in self.job["steps"]]

    def step(self, name: str) -> dict:
        found = [s for s in self.job["steps"] if s.get("name") == name]
        self.assertEqual(len(found), 1, f"one step named {name!r}")
        return found[0]

    def test_the_steps_in_their_place(self):
        order = [self.names.index(n) for n in ("Install site tools (Eleventy, Tailwind, …)", RESTORE, DOWNLOAD, KEY, SAVE,
                                               "Build the website")]
        self.assertEqual(order, sorted(order), "after the site tools: restore, download, the key, save — then the build")
        at = self.names.index(RESTORE)
        self.assertEqual([self.names.index(n) for n in (DOWNLOAD, KEY, SAVE)], [at + 1, at + 2, at + 3])
        # restored here, saved by a step of its own: the all-in-one actions/cache saves only when its key was not an
        # exact hit — the first run of each booth.json would be the only one ever saved
        restore = self.step(RESTORE)
        self.assertEqual((restore["uses"], restore["id"]), ("actions/cache/restore@v6", "boothmedia"))
        self.assertEqual(restore["with"], {
            "path": ".cache/booth-media",
            "key": f"booth-media-v1-{BOOTH_HASH}",
            "restore-keys": f"booth-media-v1-{BOOTH_HASH}-\nbooth-media-v1-\n",   # this booth.json's newest, else any
        })
        self.assertFalse([s for s in self.job["steps"] if str(s.get("uses", "")).startswith("actions/cache@")])
        download = self.step(DOWNLOAD)
        self.assertEqual({k: v for k, v in download.items() if k != "name"},
                         {"continue-on-error": True, "timeout-minutes": 20, "run": "node scripts/build/booth-media.mjs"},
                         "never stops a deploy; no BOOTH_MEDIA=0 left in")
        key = self.step(KEY)
        self.assertEqual((key["id"], key["if"], key["env"]), ("boothkey", "${{ !cancelled() }}", {"BOOTH_KEY": BOOTH_HASH}))
        save = self.step(SAVE)
        self.assertEqual((save["uses"], save["with"]),
                         ("actions/cache/save@v6", {"path": ".cache/booth-media", "key": "${{ steps.boothkey.outputs.key }}"}))
        self.assertEqual(save["if"], "${{ !cancelled() && steps.boothkey.outputs.key != '' && "
                                     "steps.boothkey.outputs.key != steps.boothmedia.outputs.cache-matched-key }}",
                         "only when this run changed the folder (and never an empty one)")
        self.assertEqual((save["continue-on-error"], save["timeout-minutes"]), (True, 5), "never stops a deploy")
        # the folder the cache keeps is the one the script writes and Eleventy publishes
        self.assertIn('export const CACHE_DIR = ".cache/booth-media";', (ROOT / CORE).read_text(encoding="utf-8"))
        self.assertIn('export const FILES_DIR = ".cache/booth-media/files";', (ROOT / CORE).read_text(encoding="utf-8"))
        self.assertIn("dir=.cache/booth-media/files\n", key["run"])
        self.assertIn('".cache/booth-media/files": "about/booth/media"', (ROOT / "eleventy.config.js").read_text(encoding="utf-8"))
        # only this job downloads them
        sync = [s.get("name") for s in yaml.safe_load(self.text)["jobs"]["sync"]["steps"]]
        self.assertNotIn(DOWNLOAD, sync)

    def test_the_key_names_the_saved_files(self):
        bash = bash_path()
        if not bash:
            self.skipTest("needs bash (Git Bash on Windows)")
        script = self.step(KEY)["run"]
        tmp = Path(tempfile.mkdtemp(prefix="gv-booth-key-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        out = tmp / "out.txt"

        def key() -> str:
            out.write_text("", encoding="utf-8")
            env = dict(os.environ, BOOTH_KEY="abc123", GITHUB_OUTPUT=out.as_posix())
            env["PATH"] = os.pathsep.join([str(Path(bash).parent), env.get("PATH", "")])     # Git Bash's own tools
            r = subprocess.run([bash, "-c", script], cwd=tmp, env=env, capture_output=True, text=True,
                               encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = out.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1, lines)
            self.assertTrue(lines[0].startswith("key="), lines)
            return lines[0][4:]

        def fingerprint(files: dict[str, int]) -> str:
            import hashlib
            listing = "".join(sorted(f"{name} {size}\n" for name, size in files.items()))
            return hashlib.sha256(listing.encode("ascii")).hexdigest()[:16]

        self.assertEqual(key(), "", "no folder: no key (nothing saved)")
        files = tmp / ".cache" / "booth-media" / "files"
        files.mkdir(parents=True)
        self.assertEqual(key(), "", "an empty folder: no key either")
        (files / "aa1-first-poster.png").write_bytes(b"x" * 10)
        (files / "aa3-file-3.mp4").write_bytes(b"y" * 2000)
        (tmp / ".cache" / "booth-media" / "manifest.json").write_text("{}", encoding="utf-8")   # not part of the key
        first = key()
        self.assertEqual(first, "booth-media-v1-abc123-" + fingerprint({"aa1-first-poster.png": 10, "aa3-file-3.mp4": 2000}))
        self.assertEqual(key(), first, "the same files: the same key (the save step then saves nothing)")
        (files / "aa3-file-3.mp4").write_bytes(b"y" * 2001)
        self.assertNotEqual(key(), first, "another size")
        (files / "aa3-file-3.mp4").write_bytes(b"y" * 2000)
        (files / "aa7-file-7.png").write_bytes(b"z")
        self.assertEqual(key(), "booth-media-v1-abc123-" + fingerprint(
            {"aa1-first-poster.png": 10, "aa3-file-3.mp4": 2000, "aa7-file-7.png": 1}), "a file more: a new key")

    def test_the_script_s_time_fits_the_step_and_the_job(self):
        minutes = int(re.search(r'envNumber\("BOOTH_MEDIA_MINUTES", (\d+)', SCRIPT.read_text(encoding="utf-8")).group(1))
        step = self.step(DOWNLOAD)["timeout-minutes"]
        save = self.step(SAVE)["timeout-minutes"]
        self.assertLessEqual(minutes + 3, step, "the script's downloads end well inside the step's limit")
        self.assertGreaterEqual(self.job["timeout-minutes"], step + save + 8,
                                "…and the job still has time to save them, build and publish")

    def test_the_code_check_downloads_nothing(self):
        self.assertNotIn("booth-media", (WF / "check.yml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------------------- eleventy
class Passthrough(unittest.TestCase):
    def test_published_only_when_the_folder_is_there_and_never_watched(self):
        dirs = []
        for with_folder in (True, False):
            d = Path(tempfile.mkdtemp(prefix="gv-booth-pt-"))
            self.addCleanup(shutil.rmtree, d, True)
            if with_folder:
                (d / ".cache" / "booth-media" / "files").mkdir(parents=True)
            dirs.append(str(d))
        # eleventy.config.js run in each folder with a stand-in configuration that records what it is asked to do
        got = run_js(self, r"""
            const conf = await imp("eleventy.config.js");
            const home = process.cwd();
            delete process.env.ONLY;
            const results = [];
            for (const dir of input) {
              process.chdir(dir);
              const copies = [];
              const watchIgnores = new Set(["**/node_modules/**", ".git/**"]);
              const cfg = new Proxy({}, { get(_t, name) {
                if (name === "watchIgnores") return watchIgnores;
                if (name === "ignores") return new Set();
                if (name === "addPassthroughCopy") return (o) => { copies.push(o); };
                return () => ({ add() {} });
              } });
              conf.default(cfg);
              results.push({ copies: copies.filter((o) => o && typeof o === "object" && Object.keys(o).some((k) => k.includes(".cache"))),
                             ignores: [...watchIgnores] });
            }
            process.chdir(home);
            out(results);
        """, data=dirs)
        self.assertEqual(got[0]["copies"], [{".cache/booth-media/files": "about/booth/media"}])
        self.assertEqual(got[1]["copies"], [], "no folder (the Code check, a fresh checkout): nothing to copy")
        for g in got:
            self.assertIn(".cache/**", g["ignores"], "npm start never watches .cache/")
        # (and the tests' own stand-in, whose watchIgnores is no Set, still loads the file: run_js got this far)
