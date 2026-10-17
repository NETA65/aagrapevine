"""Round 14, the publishers' permission credits, in a real browser (tests/browser/__init__.py says how to run these; the
site server, the browser and the helpers are test_site_in_browser.py's; the static contract is
tests/test_r14_v2_credits.py):

  * QuoteCredit  — Home's daily-quote card ends with one line of small print under the quotes, A.A.W.S.'s and AA
                   Grapevine's credits in the page language: shown (also on a phone, where one quote waits behind its
                   button, and once that quote is opened), at least 12px, at least 4.5:1 against the card in light and
                   dark, inside the card under the quotes' grid, and nothing scrolls sideways (390, 1024 and 1440px;
                   130 % text on a phone). Left out with the card when the build has no quote of the last two days.
  * FooterNotice — the footer's copyright / permission notice: its two runs (the credits for text and graphics, then
                   what the permission does not mean) shown one under the other, the whole width of the bar from
                   768px, at least 12px and 4.5:1 (390, 1024, 1440px).
  * OnPaper      — printed, Home keeps the quote's credit line and the footer's notice; /digest/ (which prints
                   without the site footer) prints its own copy of the notice at the edition's foot — a copy that
                   is not on the screen.
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import (SIDEWAYS, contrast, new_context, open_page, setUpModule,  # noqa: F401
                                          tearDownModule)

WORDS = {"en": ("Reprinted with permission of A.A. World Services, Inc. · Copyright © The AA Grapevine, Inc. "
                "Reprinted with permission. All rights reserved."),
         "es": ("Reimpreso con permiso de A.A. World Services, Inc. · Copyright © The AA Grapevine, Inc. "
                "Reimpreso con permiso. Todos los derechos reservados.")}

# the credit line of the quote card: its words, size, colours (its own and the first painted background behind it),
# where it is against the card and the quotes' grid, the quotes shown
CREDIT = r"""() => {
  const card = document.querySelector('.home-quote');
  if (!card) return null;
  const lines = card.querySelectorAll('.home-quote-rights'), r = lines[0];
  const rgb = (s) => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  let el = r, bg = 'rgba(0, 0, 0, 0)';
  while (el && /^(rgba\(0, 0, 0, 0\)|transparent)$/.test(bg)) { bg = getComputedStyle(el).backgroundColor; el = el.parentElement; }
  const c = card.getBoundingClientRect(), b = r.getBoundingClientRect(), g = card.querySelector('[data-quote-grid]').getBoundingClientRect();
  return { n: lines.length, text: r.textContent.replace(/\s+/g, ' ').trim(), shown: r.getClientRects().length > 0 && b.height > 0,
           px: parseFloat(getComputedStyle(r).fontSize), color: rgb(getComputedStyle(r).color), bg: rgb(bg),
           underGrid: b.top >= g.bottom - 1, inCard: b.left >= c.left - 1 && b.right <= c.right + 1 && b.bottom <= c.bottom + 1,
           quotes: [...card.querySelectorAll('.home-q')].filter((q) => q.getClientRects().length).length };
}"""

NOTICE = r"""() => {
  const n = document.querySelector('.site-footer-notice'), bar = n.parentElement;
  const rgb = (s) => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  let el = n, bg = 'rgba(0, 0, 0, 0)';
  while (el && /^(rgba\(0, 0, 0, 0\)|transparent)$/.test(bg)) { bg = getComputedStyle(el).backgroundColor; el = el.parentElement; }
  const cs = getComputedStyle(bar), inner = bar.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const runs = [...n.children].map((s) => s.getBoundingClientRect());
  return { runs: runs.length, shown: runs.every((r) => r.height > 0), stacked: runs.length === 2 && runs[1].top >= runs[0].bottom,
           full: Math.abs(n.getBoundingClientRect().width - inner) < 2, px: parseFloat(getComputedStyle(n).fontSize),
           color: rgb(getComputedStyle(n).color), bg: rgb(bg), text: n.textContent };
}"""


class QuoteCredit(unittest.TestCase):
    def check(self, r, lang, where):
        self.assertEqual(r["n"], 1, where)
        self.assertTrue(r["shown"], where)
        self.assertEqual(r["text"], WORDS[lang], where)
        self.assertGreaterEqual(r["px"], 12, where)
        self.assertGreaterEqual(contrast(r["color"], r["bg"]), 4.5, f"{where}: {r['color']} on {r['bg']}")
        self.assertTrue(r["underGrid"] and r["inCard"], f"{where}: {r}")

    def test_under_the_quotes_in_every_width_and_theme(self):
        for lang in ("en", "es"):
            for width in (390, 1024, 1440):
                for theme in ("light", "dark"):
                    where = f"{lang} {width}px {theme}"
                    with self.subTest(where):
                        ctx = new_context(width, 900, lang=lang, theme=theme)
                        try:
                            page = open_page(ctx, "es/" if lang == "es" else "")
                            r = page.evaluate(CREDIT)
                            if r is None:
                                self.skipTest("no daily quote of the last two days in this build: no card to check")
                            self.check(r, lang, where)
                            s = page.evaluate(SIDEWAYS)
                            self.assertFalse(s["moved"] > 0 or s["scrollWidth"] > s["width"], s)
                            if width == 390 and theme == "light":
                                toggle = page.locator("[data-quote-toggle]")
                                if toggle.count():
                                    self.assertEqual(r["quotes"], 1, "a phone shows one quote")
                                    toggle.click()
                                    opened = page.evaluate(CREDIT)
                                    self.assertEqual(opened["quotes"], 2)
                                    self.check(opened, lang, where + " (both quotes)")
                        finally:
                            ctx.close()

    def test_larger_text_on_a_phone(self):
        ctx = new_context(390, 900, prefs={"text": 130})
        try:
            page = open_page(ctx, "")
            r = page.evaluate(CREDIT)
            if r is None:
                self.skipTest("no daily quote of the last two days in this build")
            self.check(r, "en", "130 % text")
            self.assertGreater(r["px"], 12)
            s = page.evaluate(SIDEWAYS)
            self.assertFalse(s["moved"] > 0 or s["scrollWidth"] > s["width"], s)
        finally:
            ctx.close()


class FooterNotice(unittest.TestCase):
    def test_two_runs_across_the_bar(self):
        for lang, width in (("en", 390), ("es", 390), ("en", 1024), ("es", 1024), ("en", 1440)):
            with self.subTest(lang=lang, width=width):
                ctx = new_context(width, 900, lang=lang)
                try:
                    page = open_page(ctx, "es/about/" if lang == "es" else "about/")
                    r = page.evaluate(NOTICE)
                    self.assertEqual(r["runs"], 2)
                    self.assertTrue(r["shown"] and r["stacked"], r)
                    self.assertGreaterEqual(r["px"], 12)
                    self.assertGreaterEqual(contrast(r["color"], r["bg"]), 4.5)
                    if width >= 768:
                        self.assertTrue(r["full"], "the whole width of the bar")
                    self.assertIn("Copyright © The AA Grapevine, Inc.", r["text"])
                    self.assertIn("A.A. World Services, Inc.", r["text"])
                    self.assertIn("graphics" if lang == "en" else "imágenes", r["text"])
                finally:
                    ctx.close()


class OnPaper(unittest.TestCase):
    SHOWN = "(sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length && e.getBoundingClientRect().height > 0).length"

    def test_home_keeps_both(self):
        ctx = new_context(1024, 900)
        try:
            page = open_page(ctx, "")
            has_quote = page.evaluate("!!document.querySelector('.home-quote')")
            page.emulate_media(media="print")
            self.assertEqual(page.evaluate(self.SHOWN, ".site-footer-notice"), 1)
            if has_quote:
                self.assertEqual(page.evaluate(self.SHOWN, ".home-quote-rights"), 1)
        finally:
            ctx.close()

    def test_the_digest_prints_its_own_copy(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1024, 900, lang=lang)
                try:
                    page = open_page(ctx, "es/digest/" if lang == "es" else "digest/")
                    self.assertEqual(page.evaluate(self.SHOWN, ".cm-dg-notice"), 0, "not on the screen: the site footer has it")
                    page.emulate_media(media="print")
                    self.assertEqual(page.evaluate(self.SHOWN, ".cm-dg-notice"), 1)
                    self.assertEqual(page.evaluate(self.SHOWN, ".site-footer-notice"), 0, "the site footer does not print here")
                    words = page.evaluate("document.querySelector('.cm-dg-notice').textContent")
                    self.assertIn("Copyright © The AA Grapevine, Inc.", words)
                    self.assertIn("A.A. World Services, Inc.", words)
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
