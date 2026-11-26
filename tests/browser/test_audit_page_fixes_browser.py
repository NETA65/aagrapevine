"""Round 33 · the audit's page fixes (group "pages"), measured on the built site in a real browser (tests/browser/
__init__.py says how to run these; they share test_site_in_browser.py's site server and browser; tests/test_audit_page_fixes.py
has the static checks):

  * DarkPanelRings — the focus ring on the dark magazine panels (/contribute/'s "Submit online" panels and workshop
                     band, /read/'s cover headers) stands out at 3 : 1 at least, measured on the pixels (the same
                     element focused and not), in light, dark and high contrast — the site's blue ring was 1.1–2.3.
  * PlayButtonRing — in high contrast a YouTube player's Play button still shows its ring (it was pushed outside the
                     player, which clips it: 0 pixels changed).
  * NarrowRead     — /read/ and /es/read/ never scroll sideways on a 320px phone at the normal text size (an archive
                     row's long theme wraps).
  * OfflineCard    — /offline/'s "Saved on this device" card does not push the page down once it has looked at the
                     device's saved pages (no layout shift), and ends at the empty state's own height.
"""
from __future__ import annotations

import io
import unittest

from .test_site_in_browser import (SIDEWAYS, new_context, open_page, ring_contrast,  # noqa: F401
                                   setUpModule, tearDownModule)

MODES = {"light": ("light", None), "dark": ("dark", None), "high contrast": ("light", {"contrast": "high"})}
VISIBLE = "e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; }"
COUNT = "(sel) => [...document.querySelectorAll(sel)].filter(" + VISIBLE + ").length"
SCROLL = ("([sel, i]) => { [...document.querySelectorAll(sel)].filter(" + VISIBLE + ")[i]"
          ".scrollIntoView({ block: 'center', behavior: 'instant' }); }")
FOCUS = """([sel, i]) => {
  const el = [...document.querySelectorAll(sel)].filter(""" + VISIBLE + """)[i];
  el.focus({ preventScroll: true });
  const cs = getComputedStyle(el), r = el.getBoundingClientRect();
  return { name: (el.getAttribute("aria-label") || el.textContent || el.tagName).replace(/\\s+/g, " ").trim().slice(0, 40),
           visible: el.matches(":focus-visible"), style: cs.outlineStyle, width: parseFloat(cs.outlineWidth) || 0,
           offset: parseFloat(cs.outlineOffset) || 0, radius: parseFloat(cs.borderTopLeftRadius) || 0,
           box: { x: r.x, y: r.y, width: r.width, height: r.height } };
}"""


def rings(test: unittest.TestCase, pages: list[tuple[str, str]], modes: dict, least: float = 3.0) -> list[str]:
    """Every visible focusable `sel` on each page, in each mode: its ring's contrast on the pixels → the failures."""
    from PIL import Image
    failures, measured = [], 0
    for mode, (theme, prefs) in modes.items():
        for path, sel in pages:
            ctx = new_context(1280, 800, theme=theme, prefs=prefs)
            try:
                page = open_page(ctx, path)
                page.keyboard.press("Tab")                     # a keyboard user: the browser shows the ring for focus()
                n = page.evaluate(COUNT, sel)
                test.assertGreater(n, 0, f"/{path}: nothing matches {sel}")
                for i in range(n):
                    page.evaluate("document.activeElement && document.activeElement.blur()")
                    page.evaluate(SCROLL, [sel, i])
                    page.wait_for_timeout(100)
                    before = Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
                    f = page.evaluate(FOCUS, [sel, i])
                    page.wait_for_timeout(50)
                    after = Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
                    label = f"/{path} {f['name']!r}, {mode}"
                    if not f["visible"] or f["style"] == "none" or f["width"] <= 0:
                        failures.append(f"{label}: no focus ring")
                        continue
                    ratio, px = ring_contrast(after, before, f["box"], f["offset"], f["width"], f["radius"])
                    measured += 1
                    if px < 20 or ratio < least:
                        failures.append(f"{label}: {ratio:.2f} : 1 over {px} pixels")
            finally:
                ctx.close()
    test.assertGreater(measured, 0)
    return failures


class DarkPanelRings(unittest.TestCase):
    def test_the_ring_stands_out_on_the_magazine_panels(self):
        panels = ":is(.read-cover--gv, .read-cover--lv) :is(a[href], button, summary)"
        pages = [("contribute/", panels), ("es/contribute/", panels), ("read/", panels)]
        self.assertEqual(rings(self, pages, MODES), [])


class PlayButtonRing(unittest.TestCase):
    def test_high_contrast_keeps_the_play_buttons_ring_inside_the_player(self):
        pages = [("listen/", "lite-youtube > .lyt-playbtn"), ("about/", "lite-youtube > .lyt-playbtn")]
        modes = {k: v for k, v in MODES.items() if k == "high contrast"}
        modes["high contrast dark"] = ("dark", {"contrast": "high"})
        self.assertEqual(rings(self, pages, modes), [])


class NarrowRead(unittest.TestCase):
    def test_no_sideways_scroll_at_320(self):
        problems = []
        for lang in ("en", "es"):
            ctx = new_context(320, 640, lang=lang)
            try:
                path = ("es/" if lang == "es" else "") + "read/"
                page = open_page(ctx, path)
                page.wait_for_timeout(300)
                r = page.evaluate(SIDEWAYS)
                if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                    problems.append(f"/{path}: {r['scrollWidth']} px wide in {r['width']}: {r['wide']}")
            finally:
                ctx.close()
        self.assertEqual(problems, [])


CLS = """window.__cls = 0;
new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
  .observe({ type: "layout-shift", buffered: true });"""


class OfflineCard(unittest.TestCase):
    def test_the_saved_pages_card_does_not_push_the_page_down(self):
        for lang in ("en", "es"):
            for width in (1280, 768):
                with self.subTest(lang=lang, width=width):
                    ctx = new_context(width, 900, lang=lang)
                    ctx.add_init_script(CLS)
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + "offline/")
                        # pwa.js has decided: the empty state (a fresh profile has nothing saved), or the note
                        page.wait_for_function("!document.querySelector('[data-pwa-saved-empty]').hidden || "
                                               "!document.querySelector('[data-pwa-saved-unsupported]').hidden", timeout=10_000)
                        page.wait_for_timeout(500)
                        self.assertLess(page.evaluate("window.__cls"), 0.01)
                        # the reserved height is gone once it has decided (the card is the empty state's own height)
                        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('[data-pwa-saved]')).minHeight"), "0px")
                    finally:
                        ctx.close()


if __name__ == "__main__":
    unittest.main()
