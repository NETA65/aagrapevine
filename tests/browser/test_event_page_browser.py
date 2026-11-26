"""Round 37 · the event pages on the built site, in a real browser at a phone's width (390 px): an indexable event's
own page (with its Event), a monthly series' date (noindex), the series' own page (/events/series/<key>/) and — when
the build has one — a cancelled event's notice (tests/browser/__init__.py says how to run these; they share
test_site_in_browser.py's site server and browser). The build and its markup on their own: tests/test_event_pages.py.

  * Phones   — no page scrolls sideways, no script error, every button and button-like link at least 44 px tall (a
               finger's target); the event's card (its Join and Add to calendar) comes before the quick facts.
  * Bingo    — "Make the Bingo cards" opens the GVR/RLV Bingo builder already filled in with the event's name.
  * (round 37's fixer) on a phone an event's own page shows its flyer (in its card, under its words) and the past
    events' small flyers; the breadcrumb's links are 44 px wide too; "See all events" on the page of an event far down
    the list lands on its card at a desktop's width, though the cards are drawn only near the screen (committee.css
    content-visibility: committee.js reveal draws them all for the jump).

Skipped when the build has no such page.
"""
from __future__ import annotations

import re
import unittest
from urllib.parse import unquote

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401


def pick() -> dict:
    """The pages to check, from the built site's sitemap: {kind: path}."""
    site = S["site"]
    locs = re.findall(r"<loc>([^<]*)</loc>", (site / "sitemap.xml").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for loc in locs:
        m = re.search(r"/(events/(?:series/)?[a-z0-9][a-z0-9-]*/)$", loc)
        if not m:
            continue
        path = m.group(1)
        page = (site / path / "index.html").read_text(encoding="utf-8")
        body = page[page.index("<body"):]
        if path.startswith("events/series/"):
            out.setdefault("hub", path)
            dates = re.search(r'aria-labelledby="evp-dates-h".*?<a href="([^"]+)" class="card card-link', body, re.S)
            if dates and "date" not in out:
                out["date"] = re.sub(r"^/(?:[^/]+/)*?(events/)", r"\1", dates.group(1).split("#")[0]).lstrip("/")
        elif "data-ev-cancelled" in body:
            out.setdefault("notice", path)
        elif "application/ld+json" in body and "data-evp-bingo" in body:
            out.setdefault("leaf", path)
            # (the last one in the sitemap's order with a flyer: the event furthest down /events/)
            if "cm-flyer-thumb" in body:
                out.setdefault("flyer", path)
        if not path.startswith("events/series/") and "data-ev-cancelled" not in body and "evp-crumbs" in body:
            out["far"] = path
    return out


BUTTONS = """() => [...document.querySelectorAll('main :is(a, button, summary):is([class*="btn-"])')]
  .filter((el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width && r.height && s.visibility !== 'hidden' && !el.closest('[hidden], dialog, .cm-menu-panel'); })
  .map((el) => ({ h: el.getBoundingClientRect().height, t: (el.textContent || '').trim().slice(0, 40) }))
  .filter((b) => b.h < 43.5)"""


class Phones(unittest.TestCase):
    def test_at_390(self):
        pages = pick()
        if not pages:
            self.skipTest("no event page in this build")
        for kind in ("leaf", "date", "hub", "notice"):
            path = pages.get(kind)
            if not path:
                continue
            with self.subTest(kind=kind, path=path):
                ctx = new_context(390, 800)
                try:
                    errors: list[str] = []
                    page = open_page(ctx, path, errors)
                    r = page.evaluate("() => ({ scroll: document.scrollingElement.scrollWidth, width: document.documentElement.clientWidth })")
                    self.assertLessEqual(r["scroll"], r["width"], r)
                    self.assertEqual(page.evaluate(BUTTONS), [], "every button at least 44 px tall")
                    self.assertEqual(page.locator("h1").count(), 1)
                    if kind != "notice":
                        # the card (Join, Add to calendar) right under the lede, the quick facts after it
                        self.assertTrue(page.evaluate("""() => document.querySelector('.evp-top-main').getBoundingClientRect().bottom
                            <= document.querySelector('.evp-facts-card').getBoundingClientRect().top"""))
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


CRUMBS = """() => [...document.querySelectorAll('.evp-crumbs a')].map((a) => { const r = a.getBoundingClientRect();
  return { w: r.width, h: r.height, t: a.textContent.trim() }; })"""


class PhoneFlyer(unittest.TestCase):
    def test_the_flyer_and_the_breadcrumb_on_a_phone(self):
        pages = pick()
        path = pages.get("flyer")
        if not path:
            self.skipTest("no event page with a flyer in this build")
        ctx = new_context(390, 800)
        try:
            page = open_page(ctx, path)
            thumb = page.locator("main .evp-card .cm-flyer-thumb").first
            thumb.scroll_into_view_if_needed()
            box = thumb.bounding_box()
            self.assertTrue(box and box["width"] >= 120 and box["height"] >= 160, box)
            # under the card's words and buttons, never squeezing them
            words = page.locator("main .evp-card > .flex-1").first.bounding_box()
            self.assertGreaterEqual(box["y"], words["y"] + words["height"] - 1)
            self.assertLessEqual(page.evaluate("document.scrollingElement.scrollWidth"), 390)
            # the past events' small flyers show too
            for el in page.locator("main img.evp-mini-thumb").all():
                el.scroll_into_view_if_needed()
                b = el.bounding_box()
                self.assertTrue(b and b["width"] >= 40, b)
            for c in page.evaluate(CRUMBS):
                self.assertGreaterEqual(min(c["w"], c["h"]), 43.5, c)
        finally:
            ctx.close()


class FarAnchor(unittest.TestCase):
    def test_see_all_events_lands_on_its_card(self):
        path = pick().get("far")
        if not path:
            self.skipTest("no event page in this build")
        ctx = new_context(1280, 900)
        try:
            page = open_page(ctx, path)
            link = page.locator(".hero-actions a").first
            href = link.get_attribute("href")
            anchor = href.split("#", 1)[1] if "#" in href else ""
            if not anchor:
                self.skipTest(f"{path}: its first button goes to /events/ itself")
            link.click()
            page.wait_for_url(re.compile(r"/events/#"), timeout=30_000)
            page.wait_for_timeout(2500)        # (the layout settles; the jump's class goes after 1.5 s)
            top = page.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", anchor)
            self.assertTrue(-5 <= top < 900 * 0.6, f"{anchor}: its card's top at {top} px")
            page.mouse.wheel(0, 400)
            page.wait_for_timeout(300)
            again = page.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", anchor)
            self.assertLess(abs((top - again) - 400), 60, "a scroll later moves it by the scroll alone")
        finally:
            ctx.close()


class Bingo(unittest.TestCase):
    def test_the_card_comes_filled_in(self):
        path = pick().get("leaf")
        if not path:
            self.skipTest("no event page with a bingo card in this build")
        ctx = new_context(390, 800)
        try:
            page = open_page(ctx, path)
            link = page.locator("main a[data-evp-bingo]")
            href = link.get_attribute("href")
            event = unquote(re.search(r"[#&]event=([^&]+)", href).group(1))
            link.click()
            page.wait_for_url(re.compile(r"/gvr/bingo/#"), timeout=30_000)
            page.wait_for_function("() => { const i = document.getElementById('bgo-event'); return i && i.value; }", timeout=30_000)
            self.assertEqual(page.locator("#bgo-event").input_value(), event)
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
