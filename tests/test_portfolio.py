"""The committee Portfolio (/portfolio/) and the home page's "Shared by the committee" tiles — static checks of
how a file's picture is shown, that need no browser (the measured checks — the cards at 390 and 1440px with
the pictures loaded, document.elementFromPoint on the "New" badge — are QA scripts).

  * Decks     — a deck's thumbnail is its first slide, 16:9 (Drive draws it 600×338): it is shown whole
                (object-fit: contain, centred on the tone), never cropped to the 4:3 box — "cover" cut the
                first and last letters of its title, and kept only its middle third in a phone's tall box.
                Documents keep the top of their first page (cover, top).
  * New badge — the "New" badge sits over the thumbnail, like the type label: the picture (z-index 1) painted
                over it once loaded, so it showed only while the picture was loading or had failed.
  * Phones    — below 660px a card is a row (its thumbnail on the left): the phone rules come after the rules
                they override, so the smaller type label applies ("PRESENTACIÓN" broke mid-word at 390px), and
                the title has no line limit there (three lines cut the date off a Spanish title).
  * Web       — the committee's PowerPoint decks are fixed copies: each one's card links to its web presentation
                on /orientation/, which stays current ("Present on the web"; the built pages are checked in
                tests/test_orientation.py, HubBuild.test_portfolio_links_the_web_presentations).

    python -m unittest tests.test_portfolio -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def rule(css: str, selector: str) -> str:
    """The declarations of every rule written for exactly `selector` (any media query), joined — not the rules
    where it is only the end of a longer selector (".cm-doc:hover .cm-doc-thumb img")."""
    found = re.findall(r"(?:^|(?<=[{};]))[ \t]*" + re.escape(selector) + r"\s*\{([^}]*)\}", css, re.M)
    assert found, f"no rule for {selector}"
    return " ".join(found)


def z(decls: str) -> int:
    return max((int(v) for v in re.findall(r"z-index:\s*(\d+)", decls)), default=0)


class Decks(unittest.TestCase):
    def setUp(self):
        self.page, self.css = read("src", "pages", "portfolio.njk"), read("src", "assets", "css", "areas", "committee.css")

    def test_a_deck_is_shown_whole(self):
        # the card's thumbnail box says when it holds a deck — the same key committee.js fileType gives slides
        self.assertIn("""<div class="cm-doc-thumb cm-tone-{{ d.type.tone }}{{ ' is-slides' if d.type.key == 'slides' }} """, self.page)
        self.assertIn('return { key: "slides", icon: "presentation"', read("eleventy", "filters", "committee.js"))
        deck = rule(self.css, ".cm-doc-thumb.is-slides img")
        self.assertIn("object-fit: contain;", deck)
        self.assertIn("object-position: center;", deck)
        # …after the documents' rule, which keeps the top of the first page
        base = rule(self.css, ".cm-doc-thumb img")
        self.assertIn("object-fit: cover;", base)
        self.assertIn("object-position: top;", base)
        self.assertLess(self.css.index(".cm-doc-thumb img {"), self.css.index(".cm-doc-thumb.is-slides img {"))

    def test_the_home_tiles_show_a_deck_whole_too(self):
        home = read("src", "pages", "index.njk")
        self.assertIn("""("object-contain" if f.kind == "slides" else ("object-cover" ~ ("" if isPhoto else " object-top")))""", home)


class NewBadge(unittest.TestCase):
    def test_the_badge_is_over_the_picture(self):
        page, css = read("src", "pages", "portfolio.njk"), read("src", "assets", "css", "areas", "committee.css")
        self.assertIn('<span class="badge-new absolute right-3 top-3">', page)
        picture = z(rule(css, ".cm-doc-thumb img"))
        self.assertGreater(picture, 0)
        self.assertGreater(z(rule(css, ".cm-doc-thumb .badge-new")), picture)
        self.assertGreater(z(rule(css, ".cm-doc-type")), picture)                 # the type label, as before


class Phones(unittest.TestCase):
    """Below 660px (41.25rem: grid-cards has one column there) a document card is a row: the thumbnail on the left,
    8rem wide, the title, date and buttons beside it (portfolio.njk flex-row … min-[41.25rem]:flex-col)."""

    def setUp(self):
        self.page, self.css = read("src", "pages", "portfolio.njk"), read("src", "assets", "css", "areas", "committee.css")

    def test_the_phone_rules_come_after_the_rules_they_override(self):
        # Same layer, same weight: the later rule wins. Written before the base rules, the phone's type label never
        # applied — the label kept its desktop size in the 8rem thumbnail and "PRESENTACIÓN" broke mid-word.
        css = self.css
        start = css.index("@media (width < 41.25rem) {")
        block = css[start:css.index("\n  }", start)]
        phone = dict(re.findall(r"^    (\.cm-doc-[\w-]+) \{([^}]*)\}", block, re.M))
        self.assertEqual(sorted(phone), [".cm-doc-thumb", ".cm-doc-type"])
        for sel in phone:
            base = re.search(r"^  " + re.escape(sel) + r" \{", css, re.M)          # the base rule (the layer's top level)
            self.assertLess(base.start(), start, sel)
        # the phone's label: smaller and closer set than the base one, and kept inside the thumbnail
        def value(decls: str, prop: str) -> float:
            return float(re.search(prop + r":\s*([\d.]+)r?em", decls).group(1))

        base = re.search(r"^  \.cm-doc-type \{([^}]*)\}", css, re.M).group(1)
        for prop in ("font-size", "letter-spacing"):
            self.assertLess(value(phone[".cm-doc-type"], prop), value(base, prop), prop)
        self.assertIn("max-width: calc(100% - 1rem);", phone[".cm-doc-type"])
        self.assertIn("aspect-ratio: auto;", phone[".cm-doc-thumb"])

    def test_the_whole_title_on_a_phone(self):
        # In the row's narrow column three lines cut most titles before the words that tell them apart (the date of
        # the AA Grapevine letter's Spanish title at 390px, "Workshop" / "Meeting" of the decks at 320px): no line
        # limit there — the card grows. The grid's cards (from 660px) keep three lines, so a row of them stays even.
        h3 = re.search(r'<h3 class="([^"]*)">\s*\{%-? if d\.preview', self.page).group(1).split()
        self.assertIn("min-[41.25rem]:line-clamp-3", h3)
        self.assertEqual([c for c in h3 if "line-clamp" in c and not c.startswith("min-[41.25rem]:")], [])
        # the row turns into the grid's card at that same width
        self.assertIn('<article class="card cm-doc group relative flex h-full flex-row overflow-hidden min-[41.25rem]:flex-col">',
                      self.page)


class WebPresentations(unittest.TestCase):
    def test_matched_by_the_drive_files_own_title(self):
        # as /orientation/ finds a deck's PowerPoint copy: the Drive file's own title (spaces evened) is the deck's
        # drive_title — never the card's title, which on /es/ is a translation and would match no deck
        page = read("src", "pages", "portfolio.njk")
        self.assertIn('{%- set rawTitle = (d.item.title or "") | replace(r/\\s+/g, " ") | trim -%}', page)
        self.assertIn('{%- set web = (webDecks | where("drive_title", rawTitle))[0] if rawTitle else null %}', page)
        self.assertIn("""href="{{ ('/orientation/' | lurl(lang)) + '?present=' + web.id }}\"""", page)


if __name__ == "__main__":
    unittest.main()
