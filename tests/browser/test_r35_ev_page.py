"""Round 35 · an event's own page (src/pages/event-share-leaf.njk) on the built site, in a real browser
(tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's site server and browser). The
build and its markup on their own: tests/test_r35_ev_pages.py.

  * Phones       — no page of an event scrolls sideways on a 320-pixel phone, nor at 150 % text on a 360-pixel one, in
                   light, dark and high contrast (English and Spanish) — an event's own page, and a cancelled event's
                   notice when the build has one (since round 37); its "Add to calendar" menu opens whole on the
                   screen and every choice can be clicked.
  * NoErrors     — every event page of the build (the sitemap's /events/<anchor>/, and since round 37 the monthly
                   series' pages /events/series/<key>/) runs without a script error, and stays where it is (no
                   redirect: since round 37 no event page forwards to /events/ — tests/browser/test_r37_event_page.py
                   checks the noindex date pages too).
  * TheCard      — /events/' card title of such an event goes to its page; the page's "See all events" goes back to
                   the card (its anchor), and Share offers the page's own address.

Skipped when the build has no event with a page of its own (every one online, over or with a page elsewhere).
"""
from __future__ import annotations

import re
import unittest

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

THEMES = (("light", "normal"), ("dark", "normal"), ("light", "high"), ("dark", "high"))


def event_pages(cards_only: bool = False) -> list[str]:
    """The built site's event pages ("events/<anchor>/", "es/events/<anchor>/"), from its sitemap — and, but with
    cards_only, the monthly series' pages ("events/series/<key>/", since round 37). cards_only: only an event's own
    page, with its card — not a cancelled event's notice (since round 37: src/pages/event-share-cancelled.njk,
    data-ev-cancelled — no calendar menu, and no card on /events/ to come from), nor a series' page."""
    sm = (S["site"] / "sitemap.xml").read_text(encoding="utf-8")
    found = []
    for loc in re.findall(r"<loc>([^<]*)</loc>", sm):
        m = re.search(r"/((?:es/)?events/[a-z0-9][a-z0-9-]*/)$", loc) or (
            None if cards_only else re.search(r"/((?:es/)?events/series/[a-z0-9][a-z0-9-]*/)$", loc))
        if m and not (cards_only and "data-ev-cancelled" in (S["site"] / m.group(1) / "index.html").read_text(encoding="utf-8")):
            found.append(m.group(1))
    return found


OVERFLOW = """() => ({ scroll: document.scrollingElement.scrollWidth, width: document.documentElement.clientWidth,
  wide: [...document.querySelectorAll('main *')].filter((el) => { const r = el.getBoundingClientRect();
    return r.width && r.right > document.documentElement.clientWidth + 1; }).slice(0, 5)
    .map((el) => el.tagName + '.' + String(el.className).slice(0, 60)) })"""


class Phones(unittest.TestCase):
    def setUp(self):
        self.pages = event_pages()
        if not self.pages:
            self.skipTest("no event with a page of its own in this build")

    def test_no_sideways_scroll(self):
        # the first event page with its card in each language, and the first cancelled event's notice (since round 37:
        # it sorts first in the sitemap while there is one — each layout checked, never only one of them)
        cards = event_pages(cards_only=True)
        notices = [p for p in self.pages if p not in set(cards)]
        first = lambda group, es: next((p for p in group if p.startswith("es/") == es), None)  # noqa: E731
        paths = [p for p in (first(group, es) for group in (cards, notices) for es in (False, True)) if p]
        for path in paths:
            for theme, contrast in THEMES:
                for width, text in ((320, 100), (360, 150)):
                    with self.subTest(path=path, theme=theme, contrast=contrast, width=width, text=text):
                        ctx = new_context(width, 740, lang="es" if path.startswith("es/") else "en", theme=theme,
                                          prefs={"contrast": contrast, "text": text})
                        try:
                            errors: list[str] = []
                            page = open_page(ctx, path, errors)
                            r = page.evaluate(OVERFLOW)
                            self.assertLessEqual(r["scroll"], r["width"], r)
                            self.assertEqual(errors, [])
                        finally:
                            ctx.close()

    def test_the_calendar_menu_opens_whole(self):
        cards = event_pages(cards_only=True)
        if not cards:
            self.skipTest("no event page with a card (and its calendar menu) in this build")
        path = cards[0]
        for width in (320, 1280):
            with self.subTest(width=width):
                ctx = new_context(width, 800)
                try:
                    page = open_page(ctx, path)
                    page.locator("main details.cm-menu > summary").first.click()
                    page.wait_for_timeout(200)
                    r = page.evaluate("""() => { const p = document.querySelector('main details.cm-menu[open] .cm-menu-panel');
                        if (!p) return null; p.scrollIntoView({ block: 'center' }); const b = p.getBoundingClientRect();
                        return { left: b.left, right: b.right, vw: document.documentElement.clientWidth,
                          hits: [...p.querySelectorAll('a, button')].map((el) => { const r = el.getBoundingClientRect();
                            const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                            return !!(h && el.contains(h)); }) }; }""")
                    self.assertIsNotNone(r, "the menu opened")
                    self.assertGreaterEqual(r["left"], 0, r)
                    self.assertLessEqual(r["right"], r["vw"], r)
                    self.assertTrue(r["hits"] and all(r["hits"]), r)
                finally:
                    ctx.close()


class NoErrors(unittest.TestCase):
    def test_every_event_page(self):
        pages = event_pages()
        if not pages:
            self.skipTest("no event with a page of its own in this build")
        ctx = new_context(1280, 800)
        try:
            for path in pages:
                with self.subTest(path=path):
                    errors: list[str] = []
                    page = open_page(ctx, path, errors)
                    page.wait_for_timeout(300)
                    self.assertEqual(errors, [])
                    self.assertTrue(page.url.rstrip("/").endswith(path.rstrip("/")), f"it stayed on its page: {page.url}")
                    self.assertEqual(page.locator("h1").count(), 1)
                    page.close()
        finally:
            ctx.close()


class TheCard(unittest.TestCase):
    def test_from_the_card_and_back(self):
        pages = [p for p in event_pages(cards_only=True) if not p.startswith("es/")]
        if not pages:
            self.skipTest("no event with a page of its own in this build")
        path = pages[0]
        anchor = path.rstrip("/").rsplit("/", 1)[1]
        ctx = new_context(1280, 800)
        try:
            page = open_page(ctx, "events/")
            link = page.locator(f'li[id="{anchor}"] h3 a[href$="/events/{anchor}/"]')
            self.assertEqual(link.count(), 1, "the card's title links to the event's page")
            link.click()
            page.wait_for_url(re.compile(re.escape(f"/events/{anchor}/") + "$"), timeout=30_000)
            share = page.locator("main [data-share]").first.get_attribute("data-share")
            self.assertTrue(share.endswith(f"/events/{anchor}/"), share)
            page.locator("main .hero-actions a").first.click()
            page.wait_for_url(re.compile(re.escape(f"/events/#{anchor}") + "$"), timeout=30_000)
            self.assertTrue(page.locator(f'li[id="{anchor}"]').is_visible())
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
