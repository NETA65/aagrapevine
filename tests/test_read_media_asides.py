"""The hero asides of the Read & media pages (What's New, Read, Listen, Watch, Instagram, Library,
Search) — static checks of the templates that need no browser. (The measured browser checks — the card
inside the 480px hero at 1024–1920px and below it or hidden on smaller screens and at larger text,
light / dark / high contrast, a random Instagram photo per load, no extra picture with Data saver, the
Listen player alone and sticky from 1440px — are QA scripts.)

  * Every page  — fills the shared hero aside (ui.pageHero opts.side), once.
  * Listen      — the official "Get the app" Short has ONE place, the hero aside: no Short left in
                  the page's right-hand column (.listen-short / .listen-lyt are gone), and the id
                  comes from config/site.yml (site.listen.sidebar_short).
  * Watch       — the featured video comes from config/site.yml (site.watch.hero_video) and its
                  "All Shorts" link opens the list filtered (media.js reads ?type=).
  * What's New  — the random Instagram photo: a JSON pool per account + a script that never runs with
                  Data saver on; the pool's pictures carry the site's base path (| url), the card's
                  own pictures don't (the build adds it to src).
  * Wording     — the new strings say "document", never "PDF", in English and Spanish.

    python -m unittest tests.test_read_media_asides -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("whats-new", "read", "listen", "watch", "instagram", "library", "search")


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class EveryPage(unittest.TestCase):
    def test_each_page_has_one_hero_aside(self):
        for name in PAGES:
            with self.subTest(page=name):
                src = read("src", "pages", f"{name}.njk")
                self.assertEqual(len(re.findall(r"\{%-?\s*call\(slot\)\s+ui\.pageHero\(", src)), 1)
                self.assertRegex(src, r"""side:\s*"(below|hide)\"""")
                self.assertRegex(src, r"""slot\s*==\s*"side\"""")
                self.assertRegex(src, r"ui\.heroAside(Stat|Links|Media|Video)?\(", "the aside uses a ui.heroAside* helper")


class Listen(unittest.TestCase):
    def test_short_lives_only_in_the_hero_aside(self):
        src = read("src", "pages", "listen.njk")
        self.assertEqual(src.count("<lite-youtube"), 0, "the Short is ui.heroAsideVideo's player, not a second one")
        self.assertEqual(src.count("ui.heroAsideVideo("), 1)
        self.assertIn("site.listen.sidebar_short", src)
        for f in (("src", "pages", "listen.njk"), ("src", "assets", "css", "areas", "media.css")):
            self.assertNotRegex(read(*f), r"listen-short|listen-lyt", f"{f[-1]}: the old right-pane Short is gone")

    def test_config_has_the_short(self):
        cfg = yaml.safe_load(read("config", "site.yml"))["site"]
        self.assertRegex(str(cfg["listen"]["sidebar_short"]), r"^[\w-]{11}$")


class Watch(unittest.TestCase):
    def test_featured_video_from_config(self):
        cfg = yaml.safe_load(read("config", "site.yml"))["site"]
        self.assertRegex(str(cfg["watch"]["hero_video"]), r"^[\w-]{11}$")
        src = read("src", "pages", "watch.njk")
        self.assertIn("site.watch.hero_video", src)
        self.assertIn("?type=short#videos", src)

    def test_media_js_reads_type_from_the_address(self):
        js = read("src", "assets", "js", "media.js")
        self.assertRegex(js, r"""get\("type"\)""")
        self.assertIn("short|weekly|podcast", js)


class WhatsNew(unittest.TestCase):
    def test_random_photo_pool_and_data_saver_guard(self):
        src = read("src", "pages", "whats-new.njk")
        self.assertIn('id="wn-ig-pool"', src)
        self.assertIn("jsonScript", src, "the pool is serialized with the shared <script> JSON escaper")
        m = re.search(r"<script>(\(function\(\)\{.*?\}\)\(\);)</script>", src, re.S)
        self.assertIsNotNone(m, "the inline picker right after the card")
        self.assertIn('getAttribute("data-saver")==="on"', m.group(1), "no swap (no extra picture) with Data saver on")
        self.assertIn("Math.random()", m.group(1))
        self.assertRegex(src, r"i:\s*igImg\s*\|\s*url", "the pool's pictures carry the base path")
        self.assertRegex(src, r"src:\s*igSrc\[0\]", "the card's picture is as stored")


class Wording(unittest.TestCase):
    KEYS = {
        "community.json": ("community.wn.ig_",),
        "read.json": ("read.aside_",),
        "media.json": ("media.aside_", "media.ig_aside_", "media.short_"),
        "library.json": ("library.aside_", "search.aside_"),
    }

    def test_new_strings_in_both_languages_without_pdf(self):
        for f, prefixes in self.KEYS.items():
            data = json.loads(read("src", "_i18n", f))
            keys = [k for k in data if k.startswith(prefixes)]
            with self.subTest(file=f):
                self.assertTrue(keys)
            for k in keys:
                with self.subTest(key=k):
                    self.assertTrue(data[k].get("en") and data[k].get("es"))
                    for lang in ("en", "es"):
                        self.assertNotRegex(data[k][lang], r"\bPDF\b")


if __name__ == "__main__":
    unittest.main()
