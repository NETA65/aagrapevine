"""Round 12 · calendar, in a real browser (tests/browser/__init__.py says how to run these; the site server, the browser
and the helpers are test_site_in_browser's):

  * DeadlineCalendarMenu — Share your story's "Add to my calendar" under a story deadline (contribute.njk dlCalMenu,
                           read.js): on a 360-pixel phone, also at 150 % text, the menu opens inside its row (the
                           deadline cards clip anything that sticks out) without a sideways scroll; its .ics button
                           downloads the deadline with its reminder (9 AM the day before) and closes the menu; Escape
                           closes it and puts the focus back on its button; the deadlines calendar (/deadlines.ics) is
                           served as a calendar file.

What the page lists depends on the day the site was built (the open deadlines): without an open deadline the check is
skipped, never failed.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

MENU = "details.ct-dl-cal"


class DeadlineCalendarMenu(unittest.TestCase):
    def menus(self, page) -> int:
        n = page.locator(MENU).count()
        if not n:
            self.skipTest("no open story deadline in this build")
        return n

    def test_on_a_phone(self):
        for lang, prefs in (("en", None), ("es", {"text": 150})):
            with self.subTest(lang=lang, prefs=prefs):
                errors: list[str] = []
                ctx = new_context(360, 780, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "contribute/", errors)
                    self.menus(page)
                    menu = page.locator(MENU).first
                    menu.locator("summary").scroll_into_view_if_needed()
                    menu.locator("summary").click()
                    self.assertTrue(menu.evaluate("d => d.open"))
                    panel = menu.locator(".cm-menu-panel")
                    self.assertTrue(panel.is_visible())
                    self.assertEqual(panel.evaluate("p => getComputedStyle(p).position"), "static", "it opens inside its row")
                    r = page.evaluate(SIDEWAYS)
                    self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                    # every choice is fully inside the card that would clip it
                    inside = panel.evaluate("""p => { const c = p.closest('.card').getBoundingClientRect();
                        return [...p.children].every((x) => { const b = x.getBoundingClientRect();
                          return b.left >= c.left - 0.5 && b.right <= c.right + 0.5 && b.bottom <= c.bottom + 0.5; }); }""")
                    self.assertTrue(inside)
                    for target in panel.locator("a, button").all():
                        box = target.bounding_box()
                        self.assertGreaterEqual(round(box["height"]), 44, "a 44-pixel target")
                    with page.expect_download() as dl:
                        panel.locator("button[data-dl-ics]").click()
                    text = Path(dl.value.path()).read_bytes().decode("utf-8")      # (its CRLF line ends as they are)
                    self.assertTrue(dl.value.suggested_filename.startswith("story-deadline-") and dl.value.suggested_filename.endswith(".ics"))
                    self.assertIn("BEGIN:VALARM\r\nACTION:DISPLAY\r\n", text)
                    self.assertIn("TRIGGER:-PT15H\r\n", text)
                    self.assertRegex(text, r"UID:deadline-[a-z0-9-]+@neta65-gvlv")
                    self.assertFalse(menu.evaluate("d => d.open"), "the menu closes once the file is made")
                    # Escape: closed, the focus back on its button
                    menu.locator("summary").click()
                    self.assertTrue(menu.evaluate("d => d.open"))
                    page.keyboard.press("Escape")
                    self.assertFalse(menu.evaluate("d => d.open"))
                    self.assertTrue(menu.evaluate("d => document.activeElement === d.querySelector('summary')"))
                    self.assertEqual(errors, [])
                    page.close()
                finally:
                    ctx.close()

    def test_one_menu_open_at_a_time(self):
        ctx = new_context(1280, 800)
        try:
            page = open_page(ctx, "contribute/")
            if self.menus(page) < 2:
                self.skipTest("one open story deadline only")
            first, second = page.locator(MENU).nth(0), page.locator(MENU).nth(1)
            first.locator("summary").click()
            second.locator("summary").click()
            self.assertEqual((first.evaluate("d => d.open"), second.evaluate("d => d.open")), (False, True))
            page.locator("#deadlines-title").click()
            self.assertFalse(second.evaluate("d => d.open"), "a click elsewhere closes it")
        finally:
            ctx.close()

    def test_the_calendar_file_is_served(self):
        ctx = new_context(1280, 800)
        try:
            page = ctx.new_page()
            for path in ("deadlines.ics", "es/deadlines.ics"):
                r = page.request.get(url(path))
                self.assertEqual(r.status, 200, path)
                self.assertTrue(r.text().startswith("BEGIN:VCALENDAR\r\n"), path)
                self.assertIn("calendar", r.headers.get("content-type", ""), path)
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
