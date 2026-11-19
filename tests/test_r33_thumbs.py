"""Small list copies of the cached thumbnails (round 33, audit perf-4).

The sync keeps ≤ 480 px WebP thumbnails in src/assets/cache/{ig,articles,shop,pod}/, but What's New shows them in
48–128 px boxes and the home page at 50–56 px. So next to every list thumbnail "<name>.webp" it now writes
"<name>.sm.webp" — 256 px wide, at most 384 tall (scripts/sync/instagram.py save_small_copy, used by articles.py,
shop.py and podcasts.py too) — and eleventy/filters/community.js listThumb picks it when it is there.

  * Written      — a downloaded thumbnail comes with its copy, made from the same picture (no second request);
                   an avatar or a picture already that small gets none.
  * Backfill     — a thumbnail kept from an earlier run gets its copy from the local file: no request, not in a
                   dry run; a broken or missing file is skipped and the sync goes on.
  * Sweeps       — the folder sweeps (instagram cleanup_thumbs, podcasts attach_art) keep the copy of every kept
                   thumbnail and delete the copy together with its thumbnail; articles' cover swap moves it along.
  * listThumb    — "/assets/cache/<dir>/<name>.webp" → "<name>.sm.webp" when that file exists, else unchanged.

Every file goes into a temporary folder: nothing is written into src/assets/cache, and no request leaves the
computer.
    python -m unittest tests.test_r33_thumbs -v
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from PIL import Image  # noqa: E402

from scripts.sync import articles as AR  # noqa: E402
from scripts.sync import common  # noqa: E402
from scripts.sync import instagram as I  # noqa: E402
from scripts.sync import podcasts as P  # noqa: E402
from scripts.sync import shop as S  # noqa: E402

import test_instagram as TI  # noqa: E402  (its saved Instagram pages and fake instagram.com)
from nodejs import run_js  # noqa: E402

CACHE = ROOT / "src" / "assets" / "cache"


def picture(w: int, h: int, fmt: str = "JPEG") -> bytes:
    """A picture of that size (with some detail, so the WebP sizes mean something)."""
    im = Image.new("RGB", (w, h), (176, 65, 11))
    for x in range(0, w, 7):
        for y in range(0, h, 11):
            im.putpixel((x, y), (x % 256, y % 256, (x * y) % 256))
    buf = BytesIO()
    im.save(buf, fmt)
    return buf.getvalue()


def write_webp(p: Path, w: int, h: int) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(BytesIO(picture(w, h, "PNG"))) as im:
        im.save(p, "WEBP", quality=70)
    return p


def size_of(p: Path) -> tuple[int, int]:
    with Image.open(p) as im:
        return im.size


def cache_listing() -> dict[str, set[str]]:
    """The names in the real src/assets/cache folders (the tests must never add one)."""
    return {d.name: {f.name for f in d.iterdir()} for d in CACHE.iterdir() if d.is_dir()} if CACHE.is_dir() else {}


class Resp:
    def __init__(self, content: bytes, ctype: str = "image/jpeg", status: int = 200):
        self.status_code, self.content, self.headers, self.text = status, content, {"Content-Type": ctype}, ""


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-r33-thumbs-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.before = cache_listing()
        self.addCleanup(lambda: self.assertEqual(cache_listing(), self.before, "nothing written into src/assets/cache"))

    def patch(self, obj, name, value):
        p = mock.patch.object(obj, name, value)
        p.start()
        self.addCleanup(p.stop)

    def names(self, folder: Path) -> list[str]:
        return sorted(f.name for f in folder.iterdir())


# =========================================================================== the shared helpers
class Helpers(Temp):
    def test_the_copy_is_256_wide_and_at_most_384_tall(self):
        # (256 px on the long side would leave a portrait picture 179 px wide: blown up in a 128 px box on a 2x
        # screen, since the boxes crop — object-fit: cover)
        for (w, h), want in (((480, 320), (256, 171)), ((480, 600), (256, 320)), ((480, 686), (256, 366)),
                             ((405, 720), (216, 384)), ((480, 480), (256, 256))):
            with self.subTest(size=(w, h)):
                src = write_webp(self.tmp / f"x{w}x{h}.webp", w, h)
                self.assertTrue(I.ensure_small_copy(src, 70))
                self.assertEqual(size_of(self.tmp / f"x{w}x{h}.sm.webp"), want)

    def test_a_picture_already_that_small_gets_no_copy(self):
        src = write_webp(self.tmp / "tiny.webp", 200, 300)
        self.assertFalse(I.ensure_small_copy(src, 70))
        self.assertEqual(self.names(self.tmp), ["tiny.webp"])

    def test_names(self):
        self.assertEqual(I.small_copy_path(Path("a/b/DeKDjjTktaM.webp")), Path("a/b/DeKDjjTktaM.sm.webp"))
        self.assertTrue(I.is_small_copy("x.sm.webp"))
        self.assertFalse(I.is_small_copy("x.webp"))
        src = write_webp(self.tmp / "x.webp", 480, 480)
        self.assertTrue(I.ensure_small_copy(src, 70))
        self.assertFalse(I.ensure_small_copy(self.tmp / "x.sm.webp", 70), "never a copy of a copy")
        self.assertEqual(self.names(self.tmp), ["x.sm.webp", "x.webp"])

    def test_a_broken_or_missing_file_is_skipped(self):
        (self.tmp / "broken.webp").write_bytes(b"webp")
        self.assertFalse(I.ensure_small_copy(self.tmp / "broken.webp", 70))
        self.assertFalse(I.ensure_small_copy(self.tmp / "missing.webp", 70))
        self.assertEqual(self.names(self.tmp), ["broken.webp"], "no copy, no leftover .part, the file untouched")
        self.assertEqual((self.tmp / "broken.webp").read_bytes(), b"webp")


# =========================================================================== instagram
class FakeFx:
    dry_run = False

    def __init__(self, images: dict[str, bytes]):
        self.asked: list[str] = []

        def get(url, headers=None, **kw):
            self.asked.append(url)
            return Resp(images[url]) if url in images else Resp(b"", "text/html", 404)
        self.cdn = SimpleNamespace(get=get)

    def time_left(self) -> float:
        return 600.0


class Instagram(Temp):
    def setUp(self):
        super().setUp()
        self.thumbs = self.tmp / "ig"
        self.thumbs.mkdir()
        self.patch(I, "THUMB_DIR", self.thumbs)

    def post(self, sc: str, **extra) -> dict:
        return {"id": f"ig:{sc}", "category": "gv", "image": I.thumb_rel(sc),
                "extra": {"shortcode": sc, "thumb": I.thumb_rel(sc), **extra}}

    def test_a_downloaded_thumbnail_comes_with_its_small_copy(self):
        fx = FakeFx({"https://cdn/p.jpg": picture(1080, 1350)})
        stats: dict = {}
        self.assertEqual(I.ensure_thumb(fx, "DeKDjjTktaM", "https://cdn/p.jpg", stats), "/assets/cache/ig/DeKDjjTktaM.webp")
        self.assertEqual(self.names(self.thumbs), ["DeKDjjTktaM.sm.webp", "DeKDjjTktaM.webp"])
        self.assertEqual(size_of(self.thumbs / "DeKDjjTktaM.webp"), (480, 600))
        self.assertEqual(size_of(self.thumbs / "DeKDjjTktaM.sm.webp"), (256, 320))
        self.assertLess((self.thumbs / "DeKDjjTktaM.sm.webp").stat().st_size, (self.thumbs / "DeKDjjTktaM.webp").stat().st_size)
        self.assertEqual((fx.asked, stats["thumbs_downloaded"]), (["https://cdn/p.jpg"], 1), "one request for both")

    def test_an_avatar_gets_no_copy(self):
        fx = FakeFx({"https://cdn/a.jpg": picture(320, 320)})
        prof = {"avatar_url": "https://cdn/a.jpg"}
        I.ensure_avatar(fx, "gv", prof)
        self.assertEqual(self.names(self.thumbs), [f"{I.AVATAR_PREFIX}gv.webp"])

    def test_the_sweep_keeps_the_copies_of_kept_thumbnails(self):
        for sc in ("kept", "pruned", "orphan"):
            write_webp(self.thumbs / f"{sc}.webp", 480, 600)
            write_webp(self.thumbs / f"{sc}.sm.webp", 256, 320)
        write_webp(self.thumbs / "lonely.sm.webp", 256, 320)                     # a copy whose thumbnail is gone
        write_webp(self.thumbs / f"{I.AVATAR_PREFIX}gv.webp", 160, 160)
        (self.thumbs / "kept.sm.webp.part").write_bytes(b"half")                  # an interrupted copy
        n = I.cleanup_thumbs([self.post("kept")], [self.post("pruned")], dry_run=False)
        self.assertEqual(self.names(self.thumbs), [f"{I.AVATAR_PREFIX}gv.webp", "kept.sm.webp", "kept.webp"])
        self.assertEqual(n, 2, "thumbnails counted, not their copies")

    def test_backfill_from_the_local_file(self):
        write_webp(self.thumbs / "old.webp", 480, 600)                          # made before the copies existed
        (self.thumbs / "broken.webp").write_bytes(b"webp")                      # unreadable
        kept = [self.post("old"), self.post("broken"), self.post("missing"),
                {"id": "ig:manual", "image": "https://elsewhere/x.jpg", "extra": {"manual": True}}]
        self.assertEqual(I.small_thumbs(kept, dry_run=True), 0)
        self.assertNotIn("old.sm.webp", self.names(self.thumbs), "a dry run writes nothing")
        self.assertEqual(I.small_thumbs(kept, dry_run=False), 1)
        self.assertEqual(self.names(self.thumbs), ["broken.webp", "old.sm.webp", "old.webp"])
        self.assertEqual(size_of(self.thumbs / "old.sm.webp"), (256, 320))
        self.assertEqual(I.small_thumbs(kept, dry_run=False), 0, "made once")


class InstagramRun(Temp):
    """The daily run (instagram.main, against tests/test_instagram.py's fake instagram.com — whose CDN answers 404):
    every kept post's thumbnail gets its copy from the local file, one broken thumbnail stops nothing, and a post that
    leaves the site takes its copy along."""

    def setUp(self):
        super().setUp()
        (self.tmp / "raw").mkdir()
        self.thumbs = self.tmp / "ig"
        self.thumbs.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID", "IG_ANONYMOUS")}
        for p in (mock.patch.object(common, "RAW_DIR", self.tmp / "raw"), mock.patch.object(I, "THUMB_DIR", self.thumbs),
                  mock.patch.object(I.time, "sleep", lambda s: None), mock.patch.dict(os.environ, env, clear=True)):
            p.start()
            self.addCleanup(p.stop)
        items = []
        for sc in TI.LISTED + [TI.VANISHED] + TI.OLDER:
            if sc == TI.OLDER[1]:
                (self.thumbs / f"{sc}.webp").write_bytes(b"webp")              # a broken thumbnail
            else:
                write_webp(self.thumbs / f"{sc}.webp", 480, 600)
            rec = I.new_post(sc, "gv", "profile_embed", username=TI.USER, caption=f"Post {sc}", media_type="image",
                             date=I.date_from_shortcode(sc), thumb=I.thumb_rel(sc))
            items.append(I.build_item(rec, {"gv": {"name": "AA Grapevine", "username": TI.USER}}, None))
        common.save_raw("instagram", common.merge_items([], items)[0], extra={"profiles": {}})

    def run_once(self, web) -> dict:
        with mock.patch.object(I, "PoliteSession", lambda **kw: web):
            I.main(["--account", "gv", "--manual-file", str(self.tmp / "none.yml")])
        return json.loads((self.tmp / "raw" / "instagram.json").read_text(encoding="utf-8"))

    def test_backfill_and_removal(self):
        web = TI.FakeInstagram(gone={TI.VANISHED})
        env = self.run_once(web)
        good = [sc for sc in TI.LISTED + [TI.VANISHED] + TI.OLDER if sc != TI.OLDER[1]]
        self.assertTrue(all((self.thumbs / f"{sc}.sm.webp").is_file() for sc in good), self.names(self.thumbs))
        self.assertFalse((self.thumbs / f"{TI.OLDER[1]}.sm.webp").exists())
        self.assertTrue((self.thumbs / f"{TI.OLDER[1]}.webp").exists(), "the broken thumbnail is left alone")
        self.assertIn(TI.OLDER[1], {i["extra"]["shortcode"] for i in env["items"]})
        # the vanished post leaves after the second "not there" answer, half a day later — with its copy
        self.run_once(web)
        p = self.tmp / "raw" / "instagram.json"
        env = json.loads(p.read_text(encoding="utf-8"))
        for v in env["removal"].values():
            if v.get("missing"):
                v["missing"] = TI.iso(datetime.now(timezone.utc) - timedelta(hours=13))
        p.write_text(json.dumps(env), encoding="utf-8")
        env = self.run_once(web)
        self.assertEqual(env["stats"]["removal"]["removed"], [TI.VANISHED])
        self.assertFalse((self.thumbs / f"{TI.VANISHED}.webp").exists())
        self.assertFalse((self.thumbs / f"{TI.VANISHED}.sm.webp").exists(), "the copy goes with its thumbnail")
        self.assertTrue((self.thumbs / f"{TI.LISTED[0]}.sm.webp").is_file())


# =========================================================================== articles
class Http:
    def __init__(self, images: dict[str, bytes]):
        self.images, self.asked, self.requests_made = images, [], 0

    def get(self, url, **kw):
        self.asked.append(url)
        self.requests_made += 1
        return Resp(self.images[url]) if url in self.images else Resp(b"", "text/html", 404)


class Articles(Temp):
    def setUp(self):
        super().setUp()
        self.thumbs = self.tmp / "articles"
        self.patch(AR, "THUMB_DIR", self.thumbs)

    def test_a_thumbnail_comes_with_its_small_copy(self):
        http = Http({"https://x.test/card.jpg": picture(600, 400)})
        self.assertEqual(AR.local_thumb(http, "https://x.test/card.jpg", "k"), ("/assets/cache/articles/k.webp", 480, 320))
        self.assertEqual(self.names(self.thumbs), ["k.sm.webp", "k.webp"])
        self.assertEqual(size_of(self.thumbs / "k.sm.webp"), (256, 171))
        AR.local_thumb(http, "https://x.test/card.jpg", "k")
        self.assertEqual(len(http.asked), 1, "a stored thumbnail is used as it is")

    def test_backfill_for_the_articles_and_the_covers(self):
        write_webp(self.thumbs / "story.webp", 480, 320)
        write_webp(self.thumbs / "cover.webp", 480, 686)
        (self.thumbs / "broken.webp").write_bytes(b"webp")
        items = [{"id": "a", "image": "/assets/cache/articles/story.webp"},
                 {"id": "b", "image": "/assets/cache/articles/broken.webp"},
                 {"id": "c", "image": "/assets/cache/articles/missing.webp"},
                 {"id": "d", "image": "https://www.aagrapevine.org/sites/default/files/card.jpg"},     # hot-linked
                 {"id": "e", "image": None}]
        issues = {"gv:2026-11": {"cover": "/assets/cache/articles/cover.webp"}, "lv:2026-11": {}}
        self.assertEqual(AR.small_copies(items, issues), 2)
        self.assertEqual(size_of(self.thumbs / "cover.sm.webp"), (256, 366))
        self.assertEqual(size_of(self.thumbs / "story.sm.webp"), (256, 171))
        self.assertFalse((self.thumbs / "broken.sm.webp").exists())
        self.assertEqual(AR.small_copies(items, issues), 0, "made once")

    def test_the_cover_takes_the_banners_place_with_its_copy(self):
        hero, cover = "https://x.test/hero.jpg", "https://x.test/cover.jpg"
        http = Http({hero: picture(600, 400), cover: picture(2000, 2863)})
        rec = {"id": "lv:2026-11:carta-de-bienvenida"}
        key = common.short_hash(rec["id"], 16)
        rec["image"] = AR.local_thumb(http, hero, key)[0]                      # the letter's banner picture
        self.assertEqual(size_of(self.thumbs / f"{key}.sm.webp"), (256, 171))
        self.assertEqual(AR.cover_from_letter(http, rec, {"image": cover, "image_size": [2000, 2863]}), rec["image"])
        self.assertEqual(self.names(self.thumbs), [f"{key}.sm.webp", f"{key}.webp"])
        self.assertEqual(size_of(self.thumbs / f"{key}.sm.webp"), (256, 366), "the copy is the cover's, not the banner's")
        # a landscape download that nobody shows is deleted with its copy
        rec2 = {"id": "gv:2026-11:letter-editor-november-2026", "image": "https://x.test/card.jpg"}
        self.assertIsNone(AR.cover_from_letter(http, rec2, {"image": hero}))
        self.assertEqual(self.names(self.thumbs), [f"{key}.sm.webp", f"{key}.webp"])


# =========================================================================== shop
class Shop(Temp):
    def setUp(self):
        super().setUp()
        self.folder = self.tmp / "shop"

    def test_a_picture_comes_with_its_small_copy(self):
        http = Http({"https://www.aagrapevine.org/book.jpg?itok=1": picture(600, 900)})
        images = S.ImageCache(http, folder=self.folder)
        site = images("https://www.aagrapevine.org/book.jpg?itok=1")
        name = site.rsplit("/", 1)[-1]
        self.assertEqual(self.names(self.folder), [name[:-5] + ".sm.webp", name])
        self.assertEqual(size_of(self.folder / name), (480, 720))
        self.assertEqual(size_of(self.folder / (name[:-5] + ".sm.webp")), (256, 384))

    def test_backfill_only_when_pictures_are_on(self):
        write_webp(self.folder / "old.webp", 480, 480)
        (self.folder / "broken.webp").write_bytes(b"webp")
        items = [{"id": "botm:gv", "image": "/assets/cache/shop/old.webp"},
                 {"id": "sub:gv:us:X", "image": "/assets/cache/shop/broken.webp"},
                 {"id": "sub:gv:us:Y", "image": None}]
        self.assertEqual(S.ImageCache(Http({}), enabled=False, folder=self.folder).small_copies(items), 0)
        self.assertEqual(self.names(self.folder), ["broken.webp", "old.webp"], "--no-images / --html-dir: no file")
        http = Http({})
        self.assertEqual(S.ImageCache(http, folder=self.folder).small_copies(items), 1)
        self.assertEqual(self.names(self.folder), ["broken.webp", "old.sm.webp", "old.webp"])
        self.assertEqual(http.asked, [], "no request")


# =========================================================================== podcasts
class Podcasts(Temp):
    def test_the_artwork_its_copy_and_the_sweep(self):
        art = self.tmp / "pod"
        art.mkdir()
        write_webp(art / "stale.webp", 480, 480)
        write_webp(art / "stale.sm.webp", 256, 256)
        http = Http({"https://artwork.example/a.jpeg": picture(1500, 1500)})
        items = [{"id": "pod:gv:1", "image": "https://artwork.example/a.jpeg", "extra": {}}]
        shows = [{"key": "gv", "image": "https://artwork.example/a.jpeg"}]
        self.patch(P, "ART_DIR", art)
        stats = P.attach_art(http, items, shows, dry_run=False)
        name = items[0]["extra"]["thumb"].rsplit("/", 1)[-1]
        small = name[:-5] + ".sm.webp"
        self.assertEqual(self.names(art), [small, name], "the stale artwork went with its copy")
        self.assertEqual((size_of(art / name), size_of(art / small)), ((480, 480), (256, 256)))
        self.assertEqual(stats["artwork_removed"], 1, "files counted, not their copies")
        # artwork saved before the copies existed: its copy is made from the file, with no request — not in a dry run
        (art / small).unlink()
        http.asked.clear()
        P.attach_art(http, items, shows, dry_run=True)
        self.assertEqual(self.names(art), [name])
        stats = P.attach_art(http, items, shows, dry_run=False)
        self.assertEqual((self.names(art), http.asked, stats["artwork_removed"]), ([small, name], [], 0))
        # a broken file: no copy, no crash
        (art / small).unlink()
        (art / name).write_bytes(b"webp")
        P.attach_art(http, items, shows, dry_run=False)
        self.assertEqual(self.names(art), [name])


# =========================================================================== the page side
class ListThumb(Temp):
    def test_the_small_copy_when_there(self):
        site = self.tmp / "site"
        write_webp(site / "src" / "assets" / "cache" / "ig" / "A.sm.webp", 256, 320)
        got = run_js(self, """
            const m = await imp("eleventy/filters/community.js");
            process.chdir(input.dir);
            out(["/assets/cache/ig/A.webp", "/assets/cache/ig/B.webp", "/assets/cache/ig/A.sm.webp",
                 "https://i.ytimg.com/vi/x/hqdefault.jpg"].map((s) => m.listThumb(s)));
        """, data={"dir": str(site)})
        self.assertEqual(got, ["/assets/cache/ig/A.sm.webp", "/assets/cache/ig/B.webp", "/assets/cache/ig/A.sm.webp",
                               "https://i.ytimg.com/vi/x/mqdefault.jpg"])


if __name__ == "__main__":
    unittest.main()
