"""Round 33 · audit perf-4, the page side (group "thumbtpl"): the small pictures that use the sync's 256 px list copy.

Next to every cached list thumbnail "/assets/cache/<dir>/<name>.webp" (480 px) the daily sync keeps "<name>.sm.webp"
(256 px wide, at most 384 tall — tests/test_r33_thumbs.py), and the filter cmListThumb (eleventy/filters/community.js
listThumb) gives that copy's address when the file is there, else the 480 px address unchanged. These pages use it
for every cached picture they show at 128 px or less on every screen (measured in a browser at 390 and 1280 px):

  * home        — the two magazine covers (home.css .home-mag-cover, 84–128 px), the Book of the Month covers in the
                  Shop card (.shop-teaser-covers, 44 px) and the "More episodes" tiles (56 px) — except a tile whose
                  picture is the featured episode's: that 480 px file is loaded for the episode card anyway (80–160 px).
  * /read/      — an archive row's cover (.read-mini-cover, 36 px).
  * /shop/      — the current issue's cover in each magazine card (.shop-mag-cover, 72–96 px).
  * What's New  — its list tiles (.cm-thumb, 48–80 px; already so before this round).
Everything bigger keeps the 480 px file: the featured episode's square, /read/'s issue covers and their blurred
backgrounds, the Shop's Book of the Month covers, catalogs and specialty pictures, Instagram and PDF tiles.

  * Source  — each of those template lines pipes through cmListThumb; the big pictures' lines do not.
  * Built   — two real builds of /, /read/, /shop/ and /whats-new/ (ONLY=…, both languages): one where every
              "<name>.sm.webp" exists and one where none does (Node's fs.existsSync answers so for those names only —
              no file is written under src/assets/cache). With no copy the pages are what they were (no ".sm.webp"
              anywhere); with copies exactly the small pictures above change, each to its own copy, and nothing else.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("", "read/", "shop/", "whats-new/")
CACHED = re.compile(r"^/assets/cache/[\w-]+/[\w-]+\.webp$")

# Node's fs.existsSync for "src/assets/cache/**/<name>.sm.webp" answers GV_FAKE_SM ("all": yes, else: no); every other
# path is asked of the disk. Loaded with node --import before Eleventy, so listThumb (fs.existsSync) sees it.
PRELOAD = r"""
import fs from "node:fs";
import { syncBuiltinESMExports } from "node:module";
const all = process.env.GV_FAKE_SM === "all";
const real = fs.existsSync;
fs.existsSync = function (p) {
  if (/(^|\/)src\/assets\/cache\/.+\.sm\.webp$/.test(String(p).replace(/\\/g, "/"))) return all;
  return real.apply(this, arguments);
};
syncBuiltinESMExports();
"""


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def small(src: str) -> str:
    return src[:-len(".webp")] + ".sm.webp"


class Source(unittest.TestCase):
    def test_home(self):
        t = read("src", "pages", "index.njk")
        # the magazine cover (84–128 px) and the Book of the Month covers (44 px)
        self.assertRegex(t, r'class="home-mag-cover[^"]*">\s*<img src="\{\{ issue\.cover \| cmListThumb \}\}"')
        self.assertIn('<span class="shop-teaser-covers" aria-hidden="true">{% for b in hBotm %}{% if b.image %}<img src="{{ b.image | cmListThumb }}"', t)
        # (Home's "More episodes", whose tiles took the small copy, went in November 2026: one media row now)
        self.assertNotIn("eTile", t)
        self.assertIn('data-img="{{ (epArt | url) if epArt else \'\' }}"', t)
        # the featured episode's square is 160 px from 640 px up: the 480 px file
        self.assertIn('<img x-ref="art" src="{{ ep.extra.thumb or ep.image }}"', t)
        # exactly those two places on the home page
        self.assertEqual(t.count("| cmListThumb"), 2)

    def test_read(self):
        t = read("src", "pages", "read.njk")
        self.assertIn('{% if v.cover %}<img src="{{ v.cover | cmListThumb }}" width="48" height="69"', t)
        # the issue's big cover and its blurred background stay the 480 px file
        self.assertIn('<img class="read-cover-blur" src="{{ v.cover }}"', t)
        self.assertIn('<img src="{{ v.cover }}" width="480" height="686"', t)
        self.assertEqual(t.count("| cmListThumb"), 1)

    def test_shop(self):
        t = read("src", "pages", "shop.njk")
        self.assertIn('<img src="{{ ci.cover | cmListThumb }}" width="480" height="686"', t)
        # bigger than 128 px (or loaded large further down the page): the 480 px file
        self.assertIn('<img class="shop-book-cover read-cover-frame" src="{{ b.image }}"', t)
        self.assertIn('<img src="{{ sp.image }}" alt="" width="480" height="480"', t)
        self.assertIn('teaser.push({ src: sp.image,', t)
        self.assertEqual(t.count("| cmListThumb"), 1)

    def test_whats_new(self):
        t = read("src", "pages", "whats-new.njk")
        self.assertIn('<img src="{{ issue.cover | cmListThumb }}"', t)
        self.assertIn('<img src="{{ src | cmListThumb }}"', t)
        self.assertIn('<img src="{{ thumb | cmListThumb }}"', t)


class _Imgs(HTMLParser):
    """Every <img>: its attributes and the classes of the elements around it (innermost last)."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str]] = []
        self.imgs: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "img":
            self.imgs.append({**a, "_around": " | ".join(c for _t, c in self.stack if c)})
        if tag not in self.VOID:
            self.stack.append((tag, a.get("class", "")))

    def handle_startendtag(self, tag, attrs):
        if tag == "img":
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def imgs(html: str) -> list[dict]:
    p = _Imgs()
    p.feed(html)
    return p.imgs


def kind(img: dict) -> str:
    """Which small picture an <img> is ("" for every other picture)."""
    around, own = img["_around"], img.get("class", "")
    if "home-mag-cover" in around:
        return "home-mag-cover"
    if "shop-teaser-covers" in around:
        return "shop-teaser-covers"
    if "read-mini-cover" in own:
        return "read-mini-cover"
    if "shop-mag-cover" in around:
        return "shop-mag-cover"
    if re.search(r"(^| )cm-thumb( |$)", around.split(" | ")[-1] if around else ""):
        return "cm-thumb"
    if "x-ref" not in img and re.search(r"(^| )size-14 .*bg-grape-soft", around.split(" | ")[-1] if around else ""):
        return "episode-tile"
    return ""


class Built(unittest.TestCase):
    tmp: Path | None = None
    runs: dict = {}

    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="r33-thumbtpl-"))
        preload = cls.tmp / "fake-sm.mjs"
        preload.write_text(PRELOAD, encoding="utf-8")
        for mode in ("none", "all"):
            env = {**os.environ, "ONLY": "index,read,shop,whats-new", "PATH_PREFIX": "/", "I18N_STRICT": "1",
                   "NODE_NO_WARNINGS": "1", "GV_FAKE_SM": mode}
            env.pop("STRICT_BUILD", None)
            out = cls.tmp / mode
            run = subprocess.run([node_path(), "--import", preload.as_uri(),
                                  str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet", "--output", str(out)],
                                 cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)
            pages = {}
            for lang in ("", "es/"):
                for page in PAGES:
                    f = out / lang / page / "index.html"
                    if f.is_file():
                        pages[f"/{lang}{page}"] = f.read_text(encoding="utf-8")
            cls.runs[mode] = (run, pages)

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            self.skipTest("Node.js or the site's npm packages (npm ci) are missing")
        for mode, (run, pages) in self.runs.items():
            self.assertEqual(run.returncode, 0, f"{mode}: {run.stderr[-3000:]}")
            self.assertEqual(len(pages), 2 * len(PAGES), (mode, sorted(pages)))

    def test_without_copies_the_pages_name_none(self):
        _run, pages = self.runs["none"]
        for path, html in pages.items():
            with self.subTest(path=path):
                self.assertNotIn(".sm.webp", html)

    def test_with_copies_exactly_the_small_pictures_change(self):
        _run, before = self.runs["none"]
        _run, after = self.runs["all"]
        seen: dict[str, int] = {}
        for path in before:
            old, new = imgs(before[path]), imgs(after[path])
            self.assertEqual(len(old), len(new), path)
            featured = next((i["src"] for i in old if i.get("x-ref") == "art"), None)
            for o, n in zip(old, new):
                k = kind(o)
                with self.subTest(path=path, src=o.get("src"), kind=k or "-"):
                    if k == "episode-tile" and o["src"] == featured:
                        k = ""  # the featured episode's own picture: loaded for its card already
                    if k and CACHED.match(o.get("src", "")):
                        self.assertEqual(n["src"], small(o["src"]))
                        seen[k] = seen.get(k, 0) + 1
                    else:
                        self.assertEqual(n.get("src"), o.get("src"))
                    # nothing else of the tag changes (srcset, sizes, width/height …)
                    self.assertEqual({a: v for a, v in n.items() if a != "src"}, {a: v for a, v in o.items() if a != "src"})
            # the player keeps the 480 px pictures (data-img: the episode card's square)
            self.assertEqual(re.findall(r'data-img="([^"]*)"', after[path]), re.findall(r'data-img="([^"]*)"', before[path]))
        # the magazine covers are always there (the cache holds them); the others when the data has them
        self.assertGreater(seen.get("home-mag-cover", 0), 0, seen)
        self.assertGreater(seen.get("read-mini-cover", 0), 0, seen)

    def test_the_big_pictures_keep_the_480_px_file(self):
        _run, pages = self.runs["all"]
        big = 0
        for path, html in pages.items():
            for i in imgs(html):
                if kind(i):
                    continue
                with self.subTest(path=path, src=i.get("src"), around=i["_around"][-80:]):
                    self.assertNotIn(".sm.webp", i.get("src", ""))
                    big += bool(CACHED.match(i.get("src", "")))
        # (the issue covers on /read/ and their blurred backgrounds at least)
        self.assertGreater(big, 0)


if __name__ == "__main__":
    unittest.main()
