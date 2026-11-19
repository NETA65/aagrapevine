"""Round 33 · the site starts in light mode on a first visit, on the built site, in a real browser
(tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's site server and browser):

  * FirstVisitLight — a fresh profile on a device set to DARK opens Home, Events and the Spanish home page light
                      (<html data-theme="light">, the light page colour, the light address-bar colour) — before any
                      script of the page's own runs, and still after; a saved "dark" (the header's moon button) opens
                      dark, address bar too; the header's button then switches back to light and saves it.
"""
from __future__ import annotations

import json
import unittest

from .test_site_in_browser import S, answered, url, setUpModule, tearDownModule  # noqa: F401 (its site server)

LIGHT_BAR, DARK_BAR = "#07457c", "#121019"
STATE = """() => ({
  theme: document.documentElement.getAttribute("data-theme"),
  bars: [...document.querySelectorAll('meta[name="theme-color"]')].map(m => m.getAttribute("content")),
  scheme: getComputedStyle(document.documentElement).colorScheme,
  saved: (() => { try { return localStorage.getItem("gvlv-theme"); } catch (e) { return "blocked"; } })(),
})"""


def device_dark_context(saved: str | None = None):
    """A fresh browser profile whose DEVICE prefers dark (and, when given, a saved site theme)."""
    ctx = S["browser"].new_context(viewport={"width": 1280, "height": 800}, color_scheme="dark",
                                   reduced_motion="reduce", service_workers="block", timezone_id="America/Chicago")
    if saved:
        ctx.add_init_script("(t => { try { localStorage.setItem('gvlv-theme', t); } catch (e) {} })("
                            + json.dumps(saved) + ");")
    # what the page had right after its head ran (the first paint), before app.js / pwa.js (deferred)
    ctx.add_init_script("""document.addEventListener("readystatechange", () => {
      if (document.readyState !== "interactive" || window.__first) return;
      const d = document.documentElement;
      window.__first = { theme: d.getAttribute("data-theme"),
        bars: [...document.querySelectorAll('meta[name="theme-color"]')].map(m => m.getAttribute("content")) };
    });""")
    return ctx


class FirstVisitLight(unittest.TestCase):
    def test_a_dark_device_still_opens_light(self):
        ctx = device_dark_context()
        try:
            for path in ("", "events/", "es/"):
                errors: list[str] = []
                page = ctx.new_page()
                page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))
                answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
                self.assertTrue(page.evaluate("matchMedia('(prefers-color-scheme: dark)').matches"), "the device is dark")
                first = page.evaluate("() => window.__first")
                self.assertEqual(first, {"theme": "light", "bars": [LIGHT_BAR]}, f"/{path}: light from the first paint")
                state = page.evaluate(STATE)
                self.assertEqual(state["theme"], "light", path)
                self.assertEqual(state["bars"], [LIGHT_BAR], path)
                self.assertEqual(state["scheme"], "light", path)
                self.assertIsNone(state["saved"], f"/{path}: nothing saved until the visitor chooses")
                self.assertEqual(errors, [], path)
                page.close()
        finally:
            ctx.close()

    def test_a_saved_dark_opens_dark_and_the_button_switches_back(self):
        ctx = device_dark_context(saved="dark")
        try:
            page = ctx.new_page()
            answered(page.goto(url(""), wait_until="load", timeout=60_000), "")
            self.assertEqual(page.evaluate("() => window.__first"), {"theme": "dark", "bars": [DARK_BAR]})
            self.assertEqual(page.evaluate(STATE)["scheme"], "dark")
            # the header's moon / sun button (shown from 640px): back to light, saved, address bar too
            page.locator('.site-header button[aria-pressed][aria-label="Dark mode"]').click()
            page.wait_for_function("document.documentElement.getAttribute('data-theme') === 'light'", timeout=5000)
            state = page.evaluate(STATE)
            self.assertEqual((state["theme"], state["bars"], state["saved"]), ("light", [LIGHT_BAR], "light"))
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
