"""Round 33 · the text-size and spacing rules wait for class "gv-prefs" on <html> (audit perf-2), measured on the built
site in a real browser (tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's site
server and browser; tests/test_text_size_prefs.py has the static checks and runs the two scripts that set the class):

  * LivePanel   — on a 390px phone, Home and Events: the Aa panel's 150% makes the page's text 1.5 times as big with no
                  reload (the root font size 24px, a paragraph's font size × 1.5, and the larger-text layout rule
                  "overflow-wrap: break-word" on), relaxed spacing gives that paragraph a line height of 1.7 and letter
                  spacing of 0.12em, relaxed spacing alone keeps the class; back to 100% and normal spacing the class
                  goes and every measure is what it was before.
  * AfterReload — the same choices saved, a page opened fresh (Home, Events): the class is there before the page is
                  drawn and the same sizes apply; at the defaults there is no class and the root font size is 16px;
                  the panel's "Reset to defaults" takes the class away, also after a reload.

Chrome may hand a script a paragraph's old rem-based size for a frame or so after the root font size changes (the same
before the gate); each step waits (5 s at most) for the size it expects, then compares everything.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import new_context, open_page, setUpModule, tearDownModule  # noqa: F401

PAGES = ("", "events/")
# The first paragraph in <main> the visitor can see (not inside a printable poster or share frame) — marked, so every
# step measures the same one — and what the settings change on it.
MEASURE = """() => {
  let p = document.querySelector("[data-prefs-probe]");
  if (!p) {
    p = [...document.querySelectorAll("main p")].find((el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && !el.closest(".mp-poster, .cm-frame") && el.textContent.trim().length > 20;
    });
    if (p) p.setAttribute("data-prefs-probe", "");
  }
  const cs = p ? getComputedStyle(p) : null;
  const html = document.documentElement;
  return {
    gate: html.classList.contains("gv-prefs"),
    text: html.getAttribute("data-text"), spacing: html.getAttribute("data-spacing"),
    root: parseFloat(getComputedStyle(html).fontSize),
    font: cs ? parseFloat(cs.fontSize) : 0, line: cs ? parseFloat(cs.lineHeight) || 0 : 0,
    letter: cs ? parseFloat(cs.letterSpacing) || 0 : 0, wrap: cs ? cs.overflowWrap : "",
  };
}"""
SETTLED = "(want) => { const m = (" + MEASURE + ")(); return Object.keys(want).every((k) => Math.abs(m[k] - want[k]) < 0.6); }"


def settle(page, **want) -> dict:
    """Wait (5 s at most) until the probe paragraph shows these sizes, then measure everything."""
    from playwright.sync_api import TimeoutError as Timeout
    try:
        page.wait_for_function(SETTLED, arg=want, timeout=5000)
    except Timeout:
        pass                                          # (the assertions say what is wrong)
    return page.evaluate(MEASURE)


def choose(page, group: str, value: str) -> None:
    """A choice in the open Aa panel, as a visitor makes it (the radio is visually hidden: its label is clicked)."""
    page.locator(f'#gvlv-panel label.gvlv-opt:has(input[name="gvlv-{group}"][value="{value}"])').click()


def open_panel(page) -> None:
    page.locator(".site-header .gvlv-trigger").click()
    page.wait_for_selector("#gvlv-panel", state="visible", timeout=5000)


class LivePanel(unittest.TestCase):
    def test_the_panel_changes_the_page_at_once(self):
        for path in PAGES:
            with self.subTest(page="/" + path):
                ctx = new_context(390, 844)
                try:
                    errors: list[str] = []
                    page = open_page(ctx, path, errors)
                    base = page.evaluate(MEASURE)
                    self.assertEqual((base["gate"], base["text"], base["spacing"], base["root"]), (False, "100", "normal", 16.0))
                    self.assertGreater(base["font"], 0, "a paragraph to measure")
                    open_panel(page)

                    choose(page, "text", "150")
                    big = settle(page, root=24, font=base["font"] * 1.5)
                    self.assertTrue(big["gate"], "the class is on at once")
                    self.assertEqual((big["text"], big["root"]), ("150", 24.0))
                    self.assertAlmostEqual(big["font"], base["font"] * 1.5, delta=0.6, msg="the text grew without a reload")
                    self.assertEqual(big["wrap"], "break-word", "the larger-text layout rules apply")

                    choose(page, "spacing", "relaxed")
                    wide = settle(page, line=big["font"] * 1.7)
                    self.assertTrue(wide["gate"])
                    self.assertEqual(wide["spacing"], "relaxed")
                    self.assertAlmostEqual(wide["line"], wide["font"] * 1.7, delta=0.6, msg="relaxed line height, live")
                    self.assertAlmostEqual(wide["letter"], wide["font"] * 0.12, delta=0.2, msg="relaxed letter spacing, live")

                    choose(page, "text", "100")
                    relaxed_only = settle(page, root=16, font=base["font"], line=base["font"] * 1.7)
                    self.assertTrue(relaxed_only["gate"], "relaxed spacing alone keeps the class")
                    self.assertEqual(relaxed_only["root"], 16.0)
                    self.assertAlmostEqual(relaxed_only["line"], base["font"] * 1.7, delta=0.6)

                    choose(page, "spacing", "normal")
                    back = settle(page, root=16, font=base["font"], line=base["line"])
                    self.assertEqual(back, base, "back at the defaults: no class, every measure as before")
                    self.assertIsNone(page.evaluate("localStorage.getItem('gvlv-prefs')"))
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


class AfterReload(unittest.TestCase):
    def test_saved_choices_apply_before_the_page_is_drawn(self):
        plain = new_context(390, 844)
        try:
            defaults = {path: open_page(plain, path).evaluate(MEASURE) for path in PAGES}
        finally:
            plain.close()
        ctx = new_context(390, 844, prefs={"text": 150, "spacing": "relaxed"})
        try:
            for path in PAGES:
                with self.subTest(page="/" + path):
                    d = defaults[path]
                    self.assertEqual((d["gate"], d["root"]), (False, 16.0))
                    page = open_page(ctx, path)
                    m = settle(page, root=24, font=d["font"] * 1.5)
                    self.assertEqual((m["gate"], m["text"], m["spacing"], m["root"]), (True, "150", "relaxed", 24.0))
                    self.assertAlmostEqual(m["font"], d["font"] * 1.5, delta=0.6)
                    self.assertAlmostEqual(m["line"], m["font"] * 1.7, delta=0.6)
                    self.assertEqual(m["wrap"], "break-word")
                    page.close()
        finally:
            ctx.close()
        # "Reset to defaults" in the panel: the class goes at once and stays gone after a reload (the saved choices are
        # cleared). A profile of its own: new_context(prefs=…) would save them again before every page load.
        ctx = new_context(390, 844)
        try:
            page = open_page(ctx, "events/")
            page.evaluate("""() => localStorage.setItem("gvlv-prefs", JSON.stringify({ text: 130, spacing: "relaxed" }))""")
            page.reload(wait_until="load")
            d = defaults["events/"]
            m = settle(page, root=20.8, font=d["font"] * 1.3)
            self.assertEqual((m["gate"], m["text"], m["spacing"], m["root"]), (True, "130", "relaxed", 20.8))
            open_panel(page)
            page.locator("#gvlv-panel button", has_text="Reset to defaults").click()
            self.assertEqual(settle(page, root=16, font=d["font"], line=d["line"]), d)
            page.reload(wait_until="load")
            self.assertEqual(settle(page, root=16, font=d["font"], line=d["line"]), d)
            page.close()
        finally:
            ctx.close()
