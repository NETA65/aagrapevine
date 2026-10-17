"""Round 14 · Carry the Message, in a real browser (tests/browser/__init__.py says how to run these; the site server, the
browser and the helpers are test_site_in_browser.py's): the card for anyone who wants to help financially
(macros/ctm.njk) on the 404 page, About and Shop — no box alone beside blank space, no lopsided pair.

  * NotFoundGrid — the 404 page's 9 popular pages stay three even rows of 3 on wide screens (1024–1920px, and at
                   115 / 130 % text), the Carry the Message card under them as a row of its own (as wide as the
                   grid, below its last row, never a 10th card in it); at every width from a phone to 2000px and
                   at 100–150 % text, every row of the grid is full or its one card takes the whole row (where only
                   two fit — tablets, larger text — the 9th spans both columns: community.css .nf-popular), and
                   nothing scrolls sideways. A 10th card in the grid, or a lone 9th, fails it.
  * ProgramButtons — wherever the two programs' buttons show (the 404 card, About's card, the Shop's #carry band),
                   English and Spanish, 390–1920px, light and 150 % text: each at least 44px tall, the two either
                   side by side with one width and one top, or one under the other with one width — never two of
                   different widths in a row; the page language's program first.
  * MissingSpanishAddress — the server answers a missing address with the root /404.html (status 404, as GitHub
                   Pages does): under /es/… La Viña's button comes first, under any other address Grapevine's; the
                   card's words are there in Spanish too (lang="es", shown) — under the English ones in a card
                   narrower than 100rem (1440px), beside them at 1920px.
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

# The grid's cards (rows by their top), the grid's box and the card under it
GRID = r"""() => {
  const ul = document.querySelector('.nf-popular'), card = document.getElementById('nf-ctm');
  const g = ul.getBoundingClientRect(), c = card ? card.getBoundingClientRect() : null;
  const items = [...ul.children].map((li) => { const r = li.getBoundingClientRect();
    return { top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width), bottom: Math.round(r.bottom) }; });
  const rows = {};
  for (const it of items) (rows[it.top] = rows[it.top] || []).push(it);
  const cols = new Set(items.map((it) => it.left)).size;
  return { n: items.length, cols, rows: Object.values(rows).map((r) => ({ n: r.length, width: Math.round(r.reduce((s, it) => s + it.width, 0)) })),
           grid: { left: Math.round(g.left), right: Math.round(g.right), bottom: Math.round(g.bottom), width: Math.round(g.width) },
           card: c && { left: Math.round(c.left), right: Math.round(c.right), top: Math.round(c.top) },
           cardInGrid: !!(card && ul.contains(card)) };
}"""
# The two programs' buttons in one place
BUTTONS = r"""(sel) => {
  const box = document.querySelector(sel); if (!box) return null;
  return [...box.querySelectorAll('.ctm-btn')].map((a) => { const r = a.getBoundingClientRect();
    return { cls: a.className, top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width), height: r.height }; });
}"""


def popular(width: int, lang: str, text: int | None = None):
    ctx = new_context(width, 900, lang=lang, prefs={"text": text} if text else None)
    page = open_page(ctx, ("es/" if lang == "es" else "") + "404.html")
    return ctx, page


class NotFoundGrid(unittest.TestCase):
    def check_rows(self, r: dict, where) -> None:
        self.assertEqual(r["n"], 9, (where, r))
        self.assertFalse(r["cardInGrid"], (where, r))
        full = r["grid"]["width"]
        for row in r["rows"]:
            # a full row, or one card as wide as the grid — never a card alone beside an empty part of the row
            self.assertTrue(row["n"] == r["cols"] or (row["n"] == 1 and row["width"] >= full - 2), (where, r))
        # the card: a row of its own under the grid, as wide as it
        c, g = r["card"], r["grid"]
        self.assertIsNotNone(c, where)
        self.assertLessEqual(abs(c["left"] - g["left"]), 1, (where, r))
        self.assertLessEqual(abs(c["right"] - g["right"]), 1, (where, r))
        self.assertGreater(c["top"], g["bottom"], (where, r))

    def test_three_even_rows_of_three_and_the_card(self):
        cases = [(w, lang, None) for w in (1024, 1280, 1440, 1920) for lang in ("en", "es")] + \
                [(1440, "en", 115), (1920, "es", 130)]
        for width, lang, text in cases:
            with self.subTest(width=width, lang=lang, text=text):
                ctx, page = popular(width, lang, text)
                try:
                    r = page.evaluate(GRID)
                    self.assertEqual((r["cols"], [row["n"] for row in r["rows"]]), (3, [3, 3, 3]), r)
                    self.check_rows(r, (width, lang, text))
                finally:
                    ctx.close()

    def test_no_card_alone_at_any_width_or_text_size(self):
        for text in (None, 115, 130, 150):
            for lang in ("en", "es"):
                ctx, page = popular(360, lang, text)
                try:
                    for width in range(360, 2001, 56):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.wait_for_timeout(30)
                        with self.subTest(text=text, lang=lang, width=width):
                            r = page.evaluate(GRID)
                            self.check_rows(r, (width, lang, text))
                            s = page.evaluate(SIDEWAYS)
                            self.assertFalse(s["moved"] > 0 or s["scrollWidth"] > s["width"], s)
                finally:
                    ctx.close()


class ProgramButtons(unittest.TestCase):
    PLACES = (("404.html", "#nf-ctm"), ("about/", "#ctm"), ("shop/", "#carry"))

    def test_one_width_never_a_lopsided_pair(self):
        for path, sel in self.PLACES:
            for lang in ("en", "es"):
                for text in (None, 150):
                    ctx = new_context(390, 900, lang=lang, prefs={"text": text} if text else None)
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + path)
                        for width in (390, 768, 1024, 1280, 1440, 1920):
                            page.set_viewport_size({"width": width, "height": 900})
                            page.wait_for_timeout(30)
                            with self.subTest(page=path, lang=lang, text=text, width=width):
                                b = page.evaluate(BUTTONS, sel)
                                self.assertEqual(len(b), 2, b)
                                # the page language's program first
                                self.assertIn("btn-lv" if lang == "es" else "btn-primary", b[0]["cls"].split())
                                for x in b:
                                    self.assertGreaterEqual(x["height"], 44, b)
                                self.assertLessEqual(abs(b[0]["width"] - b[1]["width"]), 1, b)
                                if b[0]["top"] == b[1]["top"]:
                                    self.assertLess(b[0]["left"], b[1]["left"], b)
                                else:
                                    self.assertEqual(b[0]["left"], b[1]["left"], b)
                                    self.assertGreater(b[1]["top"], b[0]["top"], b)
                    finally:
                        ctx.close()


# The 404 card: its buttons' programs in order, its heading, its note and the other language's words
CARD = r"""() => {
  const c = document.getElementById('nf-ctm'); if (!c) return null;
  const box = (el) => { const r = el.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), h: r.height }; };
  const o = c.querySelector('.ctm-other'), h = c.querySelector('h2');
  return { order: [...c.querySelectorAll('.ctm-links > li')].map((li) => li.dataset.ctm),
           other: o && { lang: o.getAttribute('lang'), text: o.textContent.replace(/\s+/g, ' ').trim(), ...box(o) },
           h: box(h), words: box(h.parentElement) };
}"""


class MissingSpanishAddress(unittest.TestCase):
    def open(self, path: str, width: int):
        ctx = new_context(width, 900, lang="es" if path.startswith("es/") else "en")
        page = ctx.new_page()
        r = page.goto(url(path), wait_until="load", timeout=60_000)
        self.assertEqual(r.status if r else None, 404, path)
        page.evaluate("async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; }")
        return ctx, page

    def test_la_vina_first_and_the_spanish_words(self):
        for path, order in (("es/esta-pagina-no-existe/", ["es", "en"]), ("es/viejo.pdf", ["es", "en"]),
                            ("una-pagina-que-no-existe/", ["en", "es"]), ("escuela/", ["en", "es"])):
            for width in (390, 1440, 1920):
                with self.subTest(path=path, width=width):
                    ctx, page = self.open(path, width)
                    try:
                        r = page.evaluate(CARD)
                        self.assertIsNotNone(r)
                        self.assertEqual(r["order"], order, r)
                        o = r["other"]
                        self.assertIsNotNone(o, r)
                        self.assertEqual(o["lang"], "es")
                        self.assertIn("¿Quieres ayudar económicamente?", o["text"])
                        self.assertIn("Nuestro comité no recibe dinero.", o["text"])
                        self.assertGreater(o["h"], 0, "shown")
                        if width == 1920:       # beside the English words, its top by the heading's
                            self.assertGreater(o["left"], r["words"]["right"], r)
                            self.assertLess(o["top"], r["h"]["bottom"], r)
                        else:                   # under them
                            self.assertGreater(o["top"], r["words"]["bottom"] - 1, r)
                    finally:
                        ctx.close()


if __name__ == "__main__":
    unittest.main()
