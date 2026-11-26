"""Round 33 · the audit's small fixes, measured on the built site in a real browser (tests/browser/__init__.py says how
to run these; they share test_site_in_browser.py's site server and browser; tests/test_audit_small_fixes.py has the static
checks):

  * ThemeFollows   — light / dark switched in one tab reaches the site's other open tab (its header button, its
                     Menu switch, the page colour and the address-bar colour), and a page brought back from the
                     browser's page cache (a "pageshow" with persisted) re-reads the saved choice.
  * Layout         — the footer logo (the grape app icon since round 37: a 44px square) keeps its shape in the
                     narrow first column (1024–1095px); the Accessibility page's two Google Meet links are 24px+
                     apart with a mouse (WCAG 2.5.8), in both languages; the
                     weekly-meeting cards' title block spans the card from 640px (/meetings/); the booth preview's
                     controls show right under the preview while it plays and the quick settings keep their column.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import answered, new_context, open_page, url, setUpModule, tearDownModule  # noqa: F401

BTN = '.site-header button[aria-pressed][aria-label="Dark mode"]'
STATE = """() => ({
  theme: document.documentElement.getAttribute("data-theme"),
  pressed: document.querySelector(".site-header button[aria-pressed]").getAttribute("aria-pressed"),
  checked: document.querySelector("[role=switch].site-theme").getAttribute("aria-checked"),
  bar: [...document.querySelectorAll('meta[name="theme-color"]')].map(m => m.getAttribute("content")),
})"""


class ThemeFollows(unittest.TestCase):
    def test_a_switch_reaches_the_other_open_tab(self):
        ctx = new_context(1280, 800)
        try:
            errors: list[str] = []
            a, b = open_page(ctx, "", errors), open_page(ctx, "about/", errors)
            for want, bar in (("dark", "#121019"), ("light", "#07457c")):
                a.bring_to_front()
                a.locator(BTN).click()
                b.wait_for_function(f"document.documentElement.getAttribute('data-theme') === '{want}'", timeout=5000)
                on = "true" if want == "dark" else "false"
                for page in (a, b):
                    self.assertEqual(page.evaluate(STATE), {"theme": want, "pressed": on, "checked": on, "bar": [bar]})
                self.assertEqual(b.evaluate("localStorage.getItem('gvlv-theme')"), want)
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_a_page_back_from_the_page_cache_reads_the_saved_choice(self):
        ctx = new_context(1280, 800)
        try:
            page = open_page(ctx, "events/")
            self.assertEqual(page.evaluate(STATE)["theme"], "light")
            # saved elsewhere while this page sat in the cache (no storage event reaches it), then shown again
            page.evaluate("() => { localStorage.setItem('gvlv-theme', 'dark');"
                          " window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: false })); }")
            self.assertEqual(page.evaluate(STATE)["theme"], "light", "a fresh load's pageshow: nothing to do")
            page.evaluate("() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))")
            self.assertEqual(page.evaluate(STATE), {"theme": "dark", "pressed": "true", "checked": "true", "bar": ["#121019"]})
            self.assertEqual(page.evaluate("localStorage.getItem('gvlv-theme')"), "dark")
        finally:
            ctx.close()


class Layout(unittest.TestCase):
    def test_the_footer_logo_keeps_its_shape(self):
        for width in (1024, 1060, 1090):
            ctx = new_context(width, 800)
            try:
                page = open_page(ctx, "about/")
                # the grape app icon since round 37 (the NETA 65 wordmark is the header's only): a 44px square
                img = page.locator(".site-footer img[src*='app-icon-192']")
                img.scroll_into_view_if_needed()
                box = img.bounding_box()
                self.assertAlmostEqual(box["width"] / box["height"], 1, delta=0.03, msg=f"{width}px: {box}")
                self.assertAlmostEqual(box["height"], 44, delta=1, msg=f"{width}px: {box}")
            finally:
                ctx.close()

    def test_the_meet_links_are_far_enough_apart_with_a_mouse(self):
        for lang in ("", "es/"):
            for width in (768, 1280):
                ctx = new_context(width, 800, lang="es" if lang else "en")
                try:
                    page = open_page(ctx, lang + "accessibility/")
                    boxes = [a.bounding_box() for a in page.locator("#ph-online ul a").all()]
                    self.assertEqual(len(boxes), 2, lang)
                    pitch = (boxes[1]["y"] + boxes[1]["height"] / 2) - (boxes[0]["y"] + boxes[0]["height"] / 2)
                    small = min(b["height"] for b in boxes) < 24
                    self.assertTrue(not small or pitch >= 24, f"/{lang}accessibility/ at {width}px: {pitch:.1f}px apart")
                finally:
                    ctx.close()

    def test_the_weekly_cards_title_block_spans_the_card(self):
        ctx = new_context(1280, 800)
        try:
            page = open_page(ctx, "meetings/")
            blocks = page.evaluate("""() => [...document.querySelectorAll('article[aria-labelledby^="wo-"]')]
              .filter(a => a.querySelector('.cm-flyer-thumb'))
              .map(a => { const h = a.querySelector('h3').parentElement;
                return [h.getAttribute('class'), getComputedStyle(h).gridColumn]; })""")
            self.assertTrue(blocks, "a weekly card with its flyer")
            for cls, col in blocks:
                self.assertEqual((cls, col), ("sm:col-span-2", "span 2 / span 2"))
        finally:
            ctx.close()

    def test_the_booth_preview_controls_sit_under_it_while_it_plays(self):
        ctx = new_context(1280, 800)
        try:
            errors: list[str] = []
            page = open_page(ctx, "about/", errors)
            geo = """() => { const r = (s) => document.querySelector(s).getBoundingClientRect();
              const f = document.querySelector('figure.gvb-pv');
              return { kids: [...f.children].map(k => k.tagName), quick: [r('.gvb-quick').x, r('.gvb-quick').y + scrollY],
                       frame: r('[data-gvb-pv-frame]').bottom, ctl: r('[data-gvb-pv-ctl]').top, cap: r('.gvb-pv-cap').top,
                       ctlBottom: r('[data-gvb-pv-ctl]').bottom, hidden: document.querySelector('[data-gvb-pv-ctl]').hidden }; }"""
            idle = page.evaluate(geo)
            self.assertEqual(idle["kids"][-1], "FIGCAPTION")
            button = page.locator("[data-gvb-preview]").first
            button.scroll_into_view_if_needed()
            button.click()
            page.wait_for_function("!document.querySelector('[data-gvb-pv-ctl]').hidden", timeout=10_000)
            playing = page.evaluate(geo)
            self.assertLess(playing["frame"], playing["ctl"])
            self.assertLessEqual(playing["ctlBottom"], playing["cap"], "the caption comes after the controls")
            self.assertEqual(playing["quick"][0], idle["quick"][0], "the quick settings keep their column")
            self.assertAlmostEqual(playing["quick"][1] - idle["quick"][1], 0, delta=1)
            self.assertEqual(errors, [])
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
