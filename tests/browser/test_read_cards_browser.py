"""Round 14 · v1, in a real browser (tests/browser/__init__.py says how to run these; the site server, the browser and
the helpers are test_site_in_browser.py's): /read/'s two current-issue cards side by side.

  * IssueCards — from 1440px Grapevine and La Viña sit side by side (read.css .read-issues). They end on one line —
                 never a short card beside blank space (La Viña's blurb and the translation notes make its card up to
                 ~270px longer; with the cover panels now always the same height, the difference showed) — and
                 their "Show all N stories" rows sit level at the bottom (English and Spanish, 1440 / 1920px,
                 130 % text). Once one list is opened, the other card's "Show all" stays under its own list, not
                 pushed down to the foot of the long open card. Below 1440px, or with one magazine chosen
                 (.is-single), each card is as long as its content and "Show all" sits right under its list.
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

# Each shown card: its box, and its visible "Show all" row — where it ends, and how far below the list above it.
CARDS = r"""() => [...document.querySelectorAll('.read-issues > .read-issue')].filter((c) => c.getClientRects().length).map((c) => {
  const r = c.getBoundingClientRect();
  const more = c.querySelector('.read-more');
  const shown = more && more.getClientRects().length;
  const s = shown ? more.querySelector(':scope > summary').getBoundingClientRect() : null;
  const above = shown && more.previousElementSibling ? more.previousElementSibling.getBoundingClientRect().bottom : null;
  return { pub: c.dataset.pub, top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), width: Math.round(r.width),
           more: s ? Math.round(s.bottom) : null, gap: s && above !== null ? Math.round(s.top - above) : null, open: shown ? more.open : null };
})"""


def path(lang: str) -> str:
    return ("es/" if lang == "es" else "") + "read/"


class IssueCards(unittest.TestCase):
    def cards(self, page) -> list:
        cards = page.evaluate(CARDS)
        if len(cards) < 2:
            self.skipTest("this build has fewer than two current issues")
        return cards

    def test_side_by_side_cards_end_on_one_line(self):
        cases = [(w, lang, None) for w in (1440, 1920) for lang in ("en", "es")] + [(1440, "en", 130), (1920, "es", 130)]
        for width, lang, text in cases:
            with self.subTest(width=width, lang=lang, text=text):
                ctx = new_context(width, 900, lang=lang, prefs={"text": text} if text else None)
                try:
                    page = open_page(ctx, path(lang))
                    a, b = self.cards(page)
                    self.assertEqual(a["top"], b["top"], (a, b))                       # side by side …
                    self.assertLess(a["left"] + a["width"], b["left"], (a, b))
                    self.assertLessEqual(abs(a["bottom"] - b["bottom"]), 1, (a, b))    # … ending on one line
                    if a["more"] is not None and b["more"] is not None:
                        self.assertLessEqual(abs(a["more"] - b["more"]), 1, (a, b))    # "Show all" rows level
                    r = page.evaluate(SIDEWAYS)
                    self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                finally:
                    ctx.close()

    def test_an_open_list_leaves_the_other_show_all_under_its_list(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1440, 900, lang=lang)
                try:
                    page = open_page(ctx, path(lang))
                    cards = self.cards(page)
                    if any(c["more"] is None for c in cards):
                        self.skipTest("a card shows no 'Show all' row in this build")
                    page.locator(".read-issues > .read-issue").first.locator(".read-more > summary").click()
                    page.wait_for_function("document.querySelector('.read-issues .read-more').open")
                    a, b = page.evaluate(CARDS)
                    self.assertTrue(a["open"], a)
                    self.assertLessEqual(abs(a["bottom"] - b["bottom"]), 1, (a, b))    # still one line …
                    self.assertLessEqual(b["gap"], 8, b)                               # … B's "Show all" under its list
                finally:
                    ctx.close()

    def test_one_column_or_one_magazine_keeps_each_card_its_own_length(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang, width=1280):
                ctx = new_context(1280, 900, lang=lang)
                try:
                    page = open_page(ctx, path(lang))
                    a, b = self.cards(page)
                    self.assertGreater(b["top"], a["bottom"], (a, b))                 # one column
                    for c in (a, b):
                        if c["gap"] is not None:
                            self.assertLessEqual(c["gap"], 8, c)
                finally:
                    ctx.close()
            with self.subTest(lang=lang, width=1440, single=True):
                ctx = new_context(1440, 900, lang=lang)
                try:
                    page = open_page(ctx, path(lang))
                    self.cards(page)
                    page.locator("button.chip.read-chip-lv").click()                   # La Viña only
                    page.wait_for_function("document.querySelector('.read-issues').classList.contains('is-single')")
                    (c,) = page.evaluate(CARDS)
                    self.assertEqual(c["pub"], "lv", c)
                    if c["gap"] is not None:
                        self.assertLessEqual(c["gap"], 8, c)
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
