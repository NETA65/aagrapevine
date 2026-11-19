"""Round 35 · /photos/' magazine covers drawn only near the screen (committee.css .cm-cover-album: content-visibility),
on the built site in a real browser (tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's
site server and browser). The CSS on its own: tests/test_r35_ev_weight.py (Wiring). The "Grapevine" chip took 600–770 ms
on a phone-class CPU before (a poor INP), ~120 ms after.

  * Skipped   — with every year shown, a block far down is skipped (its covers not drawn) while the first one is drawn,
                at 390px and 1280px; scrolled to, it is drawn. Print draws every block.
  * Anchors   — a link to a far block's own id (#album-grapevine-covers-1946, the generic anchors) still lands that block
                right under the header, its covers drawn; a block's ↑ goes back up to the filter; "#covers-gv" (a link
                that sets the filter) lands on the filter, as before.
  * Month     — a Month chosen (?month=4: .is-flat, the blocks are display: contents) skips nothing: every cover on
                screen is drawn, the last one too.
  * Rings     — the first column's covers touch the block's edge: their focus ring is drawn whole, outside the cover
                (light and high contrast) — content-visibility would cut it, overflow-clip-margin keeps it.
"""
from __future__ import annotations

import io
import re
import unittest

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

DRAWN = "(el) => el.checkVisibility({ contentVisibilityAuto: true })"
SHOW_ALL = "() => { const b = document.querySelector('#covers .cm-covers-more button'); if (b && b.getClientRects().length) b.click(); }"


def far_anchor() -> tuple[str, str]:
    """(a far block's id, one of its generic anchors): the build's last covers block."""
    page = (S["site"] / "photos" / "index.html").read_text(encoding="utf-8")
    blocks = re.findall(r'<section id="([^"]+)" class="cm-cover-album"[^>]*>(.*?)<h3', page, re.S)
    sid, inner = blocks[-1]
    return sid, re.findall(r'<span id="([^"]+)" class="cm-anchor"', inner)[0]


class Skipped(unittest.TestCase):
    def test_a_far_block_waits_until_it_comes_near(self):
        for width, height in ((390, 844), (1280, 800)):
            with self.subTest(width=width):
                ctx = new_context(width, height)
                errors: list[str] = []
                try:
                    page = open_page(ctx, "photos/", errors)
                    page.evaluate(SHOW_ALL)
                    page.wait_for_timeout(500)
                    n = page.evaluate("document.querySelectorAll('#covers .cm-cover-album').length")
                    self.assertGreater(n, 20)
                    first = page.locator("#covers .cm-cover-album .cm-cover-grid").first
                    last = page.locator("#covers .cm-cover-album .cm-cover-grid").last
                    self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('#covers .cm-cover-album')).contentVisibility"), "auto")
                    first.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    self.assertTrue(first.evaluate(DRAWN), "a block on the screen is drawn")
                    self.assertFalse(last.evaluate(DRAWN), "a block far down is skipped")
                    last.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    self.assertTrue(last.evaluate(DRAWN), "…until it comes near")
                    page.emulate_media(media="print")
                    self.assertEqual(page.evaluate("[...new Set([...document.querySelectorAll('#covers .cm-cover-album')].map((e) => getComputedStyle(e).contentVisibility))]"),
                                     ["visible"], "print draws every block")
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


class Anchors(unittest.TestCase):
    TOP = """(id) => ({ top: document.getElementById(id).getBoundingClientRect().top,
      pad: parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0 })"""

    def test_a_link_to_a_far_block_lands_it(self):
        sid, anchor = far_anchor()
        for width, height in ((390, 844), (1280, 800)):
            with self.subTest(width=width, anchor=anchor):
                ctx = new_context(width, height)
                try:
                    page = ctx.new_page()
                    page.goto(url("photos/") + "#" + anchor, wait_until="load")
                    page.wait_for_timeout(2000)
                    r = page.evaluate(self.TOP, anchor)
                    self.assertAlmostEqual(r["top"], r["pad"], delta=4, msg=r)
                    self.assertTrue(page.locator(f"#{sid} .cm-cover-grid").evaluate(DRAWN), "its covers are drawn")
                    # its ↑: back up to the filter
                    page.locator(f"#{sid} a[href='#covers']").click()
                    page.wait_for_timeout(1200)
                    bar = page.evaluate("document.querySelector('#covers .cm-covers-filter').getBoundingClientRect().top")
                    self.assertGreaterEqual(bar, 0)
                    self.assertLess(bar, height / 2, "the filter is in view")
                finally:
                    ctx.close()

    def test_a_link_that_sets_the_filter_lands_on_the_filter(self):
        ctx = new_context(1280, 800)
        try:
            page = ctx.new_page()
            page.goto(url("photos/") + "#covers-gv", wait_until="load")
            page.wait_for_timeout(1500)
            self.assertEqual(page.evaluate("document.querySelector('#covers [data-cm-mag=\"gv\"]').getAttribute('aria-pressed')"), "true")
            bar = page.evaluate("document.querySelector('#covers .cm-covers-filter').getBoundingClientRect().top")
            self.assertGreaterEqual(bar, 0)
            self.assertLess(bar, 400)
        finally:
            ctx.close()


class Month(unittest.TestCase):
    def test_a_month_chosen_skips_nothing(self):
        for width, height in ((390, 844), (1280, 800)):
            with self.subTest(width=width):
                ctx = new_context(width, height)
                try:
                    page = open_page(ctx, "photos/?month=4")
                    page.wait_for_timeout(800)
                    self.assertEqual(page.evaluate("document.querySelectorAll('#covers .cm-covers.is-flat, #covers.is-flat').length"), 1)
                    self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('#covers .cm-cover-album')).display"), "contents")
                    r = page.evaluate("""() => { const a = [...document.querySelectorAll('#covers a.glightbox-cm')].filter((x) => x.getClientRects().length);
                      return { n: a.length, drawn: a.filter((x) => x.checkVisibility({ contentVisibilityAuto: true })).length }; }""")
                    self.assertGreater(r["n"], 20)
                    self.assertEqual(r["drawn"], r["n"], "every cover on screen is drawn, none skipped")
                finally:
                    ctx.close()


class Rings(unittest.TestCase):
    FOCUS = """() => { const a = document.querySelector('#covers .cm-cover-album:not([data-cm-early]) a.glightbox-cm');
      a.scrollIntoView({ block: 'center' }); a.focus(); }"""
    RING = """() => { const a = document.activeElement, r = a.getBoundingClientRect(), cs = getComputedStyle(a);
      return { x: r.left, y: r.top + r.height / 2, fv: a.matches(':focus-visible'), color: cs.outlineColor,
               out: (parseFloat(cs.outlineWidth) || 0) + (parseFloat(cs.outlineOffset) || 0) }; }"""

    def test_the_first_columns_focus_ring_is_whole(self):
        from PIL import Image
        for contrast in ("normal", "high"):
            with self.subTest(contrast=contrast):
                ctx = new_context(1280, 800, prefs={"contrast": contrast})
                try:
                    page = open_page(ctx, "photos/")
                    page.keyboard.press("Tab")                     # (the keyboard's focus: a ring that shows)
                    page.evaluate(self.FOCUS)
                    page.wait_for_timeout(400)
                    r = page.evaluate(self.RING)
                    self.assertTrue(r["fv"], r)
                    shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                    want = tuple(int(v) for v in re.findall(r"\d+", r["color"])[:3])
                    left = [shot.getpixel((int(r["x"]) - k, int(r["y"]))) for k in range(1, int(r["out"]) + 1)]
                    hits = [p for p in left if all(abs(a - b) <= 24 for a, b in zip(p, want))]
                    self.assertGreaterEqual(len(hits), 2, f"the ring outside the cover's left edge: {left} (ring {want})")
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
