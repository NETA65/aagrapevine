"""Round 13, the GVR / RLV corner (/gvr/, /es/gvr/): its two link cards in one row and the About page's two videos beside
"Did you know?" — the static contract (what a browser measures is tests/browser/test_r13_u2_gvr.py).

  * Start cards — #position: "Start with GVR / RLV 101" and the Tracker, one list whose two columns come from an
                  @container query (29rem: side by side when the column has room — also at 1440px with 115 % text —;
                  not a screen width, so larger text and a narrow column stack them), each card a link as a whole
                  (after:absolute), the links as before; the
                  six duty cards beside them in two columns at every width (three left the column 236 px short at
                  1920px).
  * One video card — macros/media.njk magVideo is the one place that draws a video about the magazines: About's full
                  card (about.njk has no <lite-youtube> of its own any more) and the corner's compact one
                  ({ compact: true, h: 4 }: no summary, no button, not printed, our translated title on the
                  other-language page), both privacy-enhanced lite-youtube players with the same parameters; every
                  page that draws a lite-youtube player (itself or through magVideo / ui.heroAsideVideo) loads its
                  script and stylesheet.
  * The row     — #ideas: question.daily and the videos' card in one .read-dyk-row (a wrapping flex row of 33.5rem
                  halves — the list's 30rem two-up step + the card's padding, so beside the question the two videos
                  are always side by side; not the .flex utility, which main.css's larger-text rules would turn into
                  flex: 1 1 0%), the question block in the middle of its card's spare height (only in that row), the
                  videos from site.about_videos through readAboutVideos as on About, a link to /about/#videos; the
                  compact list's steps are @container queries, and a single video takes the whole list.
  * Words       — read.gvr.vid_* in English and Spanish, with the same {placeholders}; the heading gives no number
                  (one video: its own singular heading).

    python -m unittest tests.test_r13_u2_gvr -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted((ROOT / "src" / "pages").glob("*.njk"))


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def front_matter(text: str) -> str:
    m = re.match(r"---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    return m.group(1) if m else ""


def section(page: str, sid: str) -> str:
    start = page.index(f'<section id="{sid}"')
    return page[start:page.index("</section>", start)]


class StartCards(unittest.TestCase):
    def setUp(self):
        self.pos = section(read("src", "pages", "gvr.njk"), "position")

    def test_one_list_two_columns_by_its_container(self):
        lists = re.findall(r'<div class="@container[^"]*">\s*<ul class="([^"]+)" role="list">', self.pos)
        start = next(c for c in lists if "@min-[29rem]:grid-cols-2" in c)
        self.assertIn("grid-cols-1", start)
        ul = self.pos[self.pos.index(start):]
        ul = ul[:ul.index("</ul>")]
        self.assertEqual(ul.count('<li class="card card-link group relative grid'), 2)
        for href in ("'/orientation/'", "'/tracker/'"):
            with self.subTest(href=href):
                self.assertRegex(ul, r"""<h3 class="h-card[^"]*"><a class="no-underline after:absolute after:inset-0[^"]*" href="\{\{ """
                                 + re.escape(href) + r""" \| lurl\(lang\) \}\}">""")
        self.assertLess(ul.index("/orientation/"), ul.index("/tracker/"), "GVR / RLV 101 first: the first stop for someone new")
        # side by side, each card a column: icon and arrow on top, the words under them
        self.assertEqual(ul.count("@min-[29rem]:col-span-2 @min-[29rem]:row-start-2"), 2)
        self.assertEqual(ul.count("@min-[29rem]:col-start-2 @min-[29rem]:row-start-1"), 2)
        self.assertNotIn("@min-[30rem]", ul, "one threshold for the list and its cards")

    def test_the_duty_cards_in_two_columns(self):
        self.assertIn('<ul class="grid grid-cols-1 gap-4 @md:grid-cols-2" role="list">', self.pos)
        self.assertNotIn("@4xl:grid-cols-3", self.pos)


class OneVideoCard(unittest.TestCase):
    def setUp(self):
        self.media = read("src", "_includes", "macros", "media.njk")
        self.macro = self.media[self.media.index("{% macro magVideo("):]
        self.about = read("src", "pages", "about.njk")
        self.gvr = read("src", "pages", "gvr.njk")

    def test_the_macro(self):
        self.assertIn("media.magVideo(v, lang, opts=null)", self.media, "documented in the file's header")
        # one player, privacy-enhanced as before: only the preview picture until it is played
        self.assertEqual(self.macro.count("<lite-youtube "), 1)
        self.assertIn('params="rel=0&amp;playsinline=1&amp;hl={{ lang }}"', self.macro)
        self.assertIn("v.id | ytThumb('hqdefault')", self.macro)
        self.assertIn('class="lyt-playbtn"', self.macro)
        full, compact = self.macro.split("{%- else %}")[1], self.macro.split("{%- else %}")[0]
        # About's card: summary, translation and "Watch on YouTube"
        for part in ("v.summary", '<details class="read-vid-tr', "media.watch_on_yt", "lg:grid-rows-subgrid"):
            self.assertIn(part, full)
        # the compact one: no summary, no button, not printed; our translated title, small, on the other-language page
        self.assertIn('class="read-vid-c min-w-0 print:hidden"', compact)
        for part in ("v.summary", "media.watch_on_yt", "<details"):
            self.assertNotIn(part, compact)
        self.assertIn("v.tr.title", compact)
        self.assertIn('lang="{{ v.lang }}"', compact)
        self.assertIn('"read.about.vid_tr" | t(lang)', compact)

    def test_about_and_the_corner_use_it(self):
        self.assertNotIn("<lite-youtube", self.about, "About's videos come from macros/media.njk magVideo")
        self.assertIn("{% for v in vids %}{{ media.magVideo(v, lang) }}{% endfor %}", self.about)
        self.assertIn("media.magVideo(v, lang, { compact: true, h: 4 })", self.gvr)
        for page in (self.about, self.gvr):
            self.assertIn('{% import "macros/media.njk" as media with context %}', page)
            self.assertIn("site.about_videos | readAboutVideos(db.videos, lang)", page)

    def test_every_page_with_a_player_loads_lite_youtube(self):
        found = []
        for page in PAGES:
            text = page.read_text(encoding="utf-8")
            if not re.search(r"<lite-youtube\b|media\.magVideo\(|ui\.heroAsideVideo\(", text):
                continue
            found.append(page.name)
            fm = front_matter(text)
            with self.subTest(page=page.name):
                self.assertIn("/assets/vendor/lite-yt-embed.js", fm)
                self.assertIn("/assets/vendor/lite-yt-embed.css", fm)
        self.assertIn("gvr.njk", found)
        self.assertIn("about.njk", found)


class TheRow(unittest.TestCase):
    def setUp(self):
        self.ideas = section(read("src", "pages", "gvr.njk"), "ideas")
        self.css = read("src", "assets", "css", "areas", "read.css")

    def test_question_and_videos_in_one_row(self):
        row = self.ideas[self.ideas.index('<div class="read-dyk-row'):]
        self.assertLess(row.index("question.daily(lang"), row.index('class="card card-pad read-vid-c-card print:hidden"'))
        # the question card no longer sets its own width: the row does
        self.assertNotIn("max-w-3xl", re.search(r"question\.daily\(lang, \{[^}]*\}\)", row).group(0))
        self.assertIn("""href="{{ '/about/' | lurl(lang) }}#videos\"""", row)
        self.assertIn('<h3 id="gvr-vids-title" class="h-card">{{ ("read.gvr.vid_title_one" if vids | length == 1 '
                      'else "read.gvr.vid_title") | t(lang) }}</h3>', row)
        self.assertNotIn("<section", row, "no landmark inside the #ideas landmark")

    def test_the_styles(self):
        self.assertRegex(self.css, r"\.read-dyk-row \{ display: flex; flex-wrap: wrap;")
        self.assertIn(".read-dyk-row > * { flex: 1 1 33.5rem; min-width: 0; }", self.css)
        self.assertIn(".read-vid-c-box { container-type: inline-size; }", self.css)
        for step in ("@container (width >= 24rem)", "@container (width >= 30rem)", "@container (width >= 48rem)"):
            self.assertIn(step, self.css)
        # beside the videos: the question block in the middle of the card's spare height (the column's gap = mt-4)
        self.assertIn(".read-dyk-row > .read-dyk { display: flex; flex-direction: column; row-gap: 1rem; }", self.css)
        self.assertIn(".read-dyk-row > .read-dyk > .mt-4 { margin-block: auto; }", self.css)
        # …on screen only: this unlayered display would beat the card's print:hidden utility on paper
        self.assertRegex(self.css, r"@media screen \{[^\n]*\n  \.read-dyk-row > \.read-dyk \{ display: flex;")
        # one video: the whole list, never half of it
        self.assertIn(".read-vid-c-list:has(> li:only-child) { grid-template-columns: minmax(0, 1fr); }", self.css)

    def test_the_question_block_is_the_cards_mt4_child(self):
        # (the centring rule above reaches it as .read-dyk > .mt-4: macros/question.njk's x-if template)
        q = read("src", "_includes", "macros", "question.njk")
        self.assertRegex(q, r'<template x-if="cur\(\)">\s*<div class="mt-4">')


class Words(unittest.TestCase):
    def test_both_languages(self):
        i18n = json.loads(read("src", "_i18n", "read.json"))
        keys = [k for k in i18n if k.startswith("read.gvr.vid_")]
        self.assertEqual(sorted(keys), ["read.gvr.vid_more", "read.gvr.vid_sub", "read.gvr.vid_title", "read.gvr.vid_title_one"])
        # no number in the heading: readAboutVideos may drop an entry (no title), and the list may grow
        for k in ("read.gvr.vid_title", "read.gvr.vid_title_one"):
            for lang, words in (("en", r"\b(two|three|2|3)\b"), ("es", r"\b(dos|tres|2|3)\b")):
                self.assertNotRegex(i18n[k][lang].lower(), words, f"{k} ({lang})")
        for k in keys:
            with self.subTest(key=k):
                en, es = i18n[k]["en"], i18n[k]["es"]
                self.assertTrue(en.strip() and es.strip())
                self.assertNotEqual(en, es)
                self.assertEqual(set(re.findall(r"\{(\w+)\}", en)), set(re.findall(r"\{(\w+)\}", es)))
        self.assertIn("Quiénes somos", i18n["read.gvr.vid_more"]["es"], "the About page by its Spanish name")


if __name__ == "__main__":
    unittest.main()
