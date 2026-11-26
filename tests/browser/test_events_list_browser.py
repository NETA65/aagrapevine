"""The /events/ list since its redesign (November 2026), on the built site in a real browser (tests/browser/__init__.py
says how to run these; they share test_site_in_browser.py's site server and browser). The markup on its own:
tests/test_events_series_cards.py; the filters on a page stand-in: tests/test_r30_events_list.py.

  * Phone   — at 390 × 844 (touch), English and Spanish: the first one-off event's card starts within the page's first
              2,400px (it was ~2,900px below "Our monthly meetings" and the weekly meetings, on a page ~33,000px
              tall: now under 16,000px); "Next up" shows three events, each a link to a card on the page; "Save the
              date" shows under the hero; the "Next 5 weeks" calendar is folded under its heading near the top, its
              button opens it (aria-expanded) and closes it again; no script error.
  * Desktop — at 1280 × 800: the calendar is the sidebar (to the right of the list, its button hidden), "Next up" is
              not shown (the sidebar says it). A cancelled card's date tile (never faded): its month, day and weekday
              at 4.5:1 or more on the tile, light and dark, English and Spanish.
  * Filters — the "Workshops" chip shows only workshops, its kind in the address (?kind=workshop) so the view can be
              shared; picking it again shows every card; a language picked with it narrows them; an address with
              ?kind=…&lang=… opens with them picked; nothing picked: "Clear filters" is hidden, with one picked it shows.
              The old ?filter=neta (its "NETA 65 events" chip) shows ours and the committee meetings, a pressed chip
              of its own says so; pressing it shows every card and drops it from the address.
  * Pages   — an event's own page at 390px: Add to calendar and Directions in the hero, above the fold. A series'
              card's "See all dates" lands on its page's "All dates", every date there a link to a page of the site.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import S, contrast, new_context, open_page, setUpModule, tearDownModule  # noqa: F401


def phone(lang: str = "en"):
    return S["browser"].new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                                    device_scale_factor=2, reduced_motion="reduce", service_workers="block",
                                    timezone_id="America/Chicago", locale="es-US" if lang == "es" else "en-US")


# the cards shown: their id (a series' card or a weekly meeting's has its kind), top (page px), kind
CARDS = """() => [...document.querySelectorAll('li[data-group]')].filter((li) => li.getClientRects().length)
  .map((li) => ({ id: li.id || li.dataset.kind, kind: li.dataset.kind, lang: li.dataset.lang, group: li.dataset.group, cancelled: li.hasAttribute('data-ev-cancelled'),
                  oneOff: !li.closest('#ev-pinned, #ev-weekly'), top: Math.round(li.getBoundingClientRect().top + scrollY) }))"""


class Phone(unittest.TestCase):
    def test_what_is_new_comes_first(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = phone(lang)
                errors: list[str] = []
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "events/", errors)
                    page.wait_for_timeout(300)
                    cards = page.evaluate(CARDS)
                    one_offs = [c for c in cards if c["oneOff"]]
                    self.assertTrue(one_offs)
                    self.assertLess(one_offs[0]["top"], 2400, one_offs[0])
                    # the series and the weekly meetings after every one-off event
                    series_top = page.evaluate("Math.round(document.getElementById('ev-pinned').getBoundingClientRect().top + scrollY)")
                    self.assertGreater(series_top, max(c["top"] for c in one_offs))
                    height = page.evaluate("document.documentElement.scrollHeight")
                    self.assertLess(height, 16000)
                    # Next up: three shown, each to a card of the page
                    nu = page.evaluate("""() => [...document.querySelectorAll('#ev-nextup li')].filter((li) => li.getClientRects().length)
                      .map((li) => { const a = li.querySelector('a'); const id = decodeURIComponent(a.getAttribute('href').slice(1));
                                     return { id, there: !!document.getElementById(id) }; })""")
                    self.assertEqual(len(nu), 3, nu)
                    self.assertTrue(all(x["there"] for x in nu), nu)
                    self.assertTrue(page.locator("#ev-nextup").is_visible())
                    # "Save the date" under the hero
                    self.assertTrue(page.locator("#ev-aside-title").is_visible())
                    # the calendar: folded near the top, its button opens and closes it
                    toggle = page.locator("[data-ev-cal-toggle]")
                    self.assertTrue(toggle.is_visible())
                    self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
                    self.assertFalse(page.locator("#ev-cal-body").is_visible())
                    self.assertLess(page.evaluate("document.getElementById('ev-cal').getBoundingClientRect().top + scrollY"), one_offs[0]["top"])
                    toggle.tap()
                    self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
                    self.assertTrue(page.locator("#ev-cal-body").is_visible())
                    toggle.tap()
                    self.assertFalse(page.locator("#ev-cal-body").is_visible())
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


class Desktop(unittest.TestCase):
    def test_the_calendar_is_the_sidebar(self):
        ctx = new_context(1280, 800)
        errors: list[str] = []
        try:
            page = open_page(ctx, "events/", errors)
            r = page.evaluate("""() => { const b = (s) => document.querySelector(s).getBoundingClientRect();
              return { cal: b('#ev-cal').left, main: b('.ev-main').right, toggle: document.querySelector('[data-ev-cal-toggle]').getClientRects().length,
                       body: document.getElementById('ev-cal-body').getClientRects().length, nextup: document.getElementById('ev-nextup').getClientRects().length }; }""")
            self.assertGreater(r["cal"], r["main"] - 1, "beside the list, on its right")
            self.assertEqual((r["toggle"], r["nextup"]), (0, 0))
            self.assertGreater(r["body"], 0)
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_a_cancelled_cards_date_keeps_its_contrast(self):
        for theme in ("light", "dark"):
            for pre in ("", "es/"):
                with self.subTest(theme=theme, lang=pre or "en"):
                    ctx = new_context(1280, 900, lang="es" if pre else "en", theme=theme)
                    try:
                        page = open_page(ctx, pre + "events/")
                        found = page.evaluate("""() => [...document.querySelectorAll('.ev-cancelled .cm-date-tile')]
                          .filter((t) => t.getClientRects().length).flatMap((t) => [...t.children].map((s) => {
                            const rgb = (c) => (c.match(/[\\d.]+/g) || []).slice(0, 4).map(Number);
                            const cs = getComputedStyle(s), ts = getComputedStyle(t);
                            return { text: s.textContent.trim(), fg: rgb(cs.color), bg: rgb(ts.backgroundColor), opacity: ts.opacity };
                          }))""")
                        if not found:
                            self.skipTest("no cancelled event in the day's data")
                        for f in found:
                            self.assertEqual(f["opacity"], "1", f)
                            self.assertFalse(len(f["bg"]) == 4 and f["bg"][3] < 1, f"an opaque tile: {f}")
                            self.assertGreaterEqual(contrast(f["fg"], f["bg"]), 4.5, f)
                    finally:
                        ctx.close()


class Filters(unittest.TestCase):
    def test_kind_language_and_the_address(self):
        ctx = new_context(1280, 900)
        errors: list[str] = []
        try:
            page = open_page(ctx, "events/", errors)
            page.wait_for_timeout(300)
            everything = page.evaluate(CARDS)
            self.assertFalse(page.locator(".ev-clear").is_visible())
            page.locator('[data-ev-kind="workshop"]').click()
            page.wait_for_timeout(200)
            shown = page.evaluate(CARDS)
            self.assertTrue(shown)
            self.assertEqual({c["kind"] for c in shown}, {"workshop"})
            self.assertIn("kind=workshop", page.url)
            self.assertEqual(page.locator('[data-ev-kind="workshop"]').get_attribute("aria-pressed"), "true")
            self.assertTrue(page.locator(".ev-clear").is_visible())
            # with a language: only those held in it
            langs = sorted({c["lang"] for c in shown})
            page.select_option('select[data-ev-facet="lang"]', langs[-1])
            page.wait_for_timeout(200)
            narrowed = page.evaluate(CARDS)
            self.assertTrue(narrowed)
            self.assertEqual({(c["kind"], c["lang"]) for c in narrowed}, {("workshop", langs[-1])})
            self.assertIn(f"lang={langs[-1]}", page.url)
            # the same chip again: every kind (the language stays)
            page.locator('[data-ev-kind="workshop"]').click()
            page.wait_for_timeout(200)
            self.assertNotIn("kind=", page.url)
            page.locator(".ev-clear").click()
            page.wait_for_timeout(200)
            self.assertEqual(len(page.evaluate(CARDS)), len(everything))
            self.assertNotIn("?", page.url.split("#")[0])
            # an address with filters: they are picked on arrival
            again = open_page(ctx, "events/?kind=workshop&lang=" + langs[-1], errors)
            again.wait_for_timeout(300)
            self.assertEqual({(c["kind"], c["lang"]) for c in again.evaluate(CARDS)}, {("workshop", langs[-1])})
            self.assertEqual(again.locator('select[data-ev-facet="lang"]').input_value(), langs[-1])
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_the_old_neta_address(self):
        ctx = new_context(1280, 900)
        errors: list[str] = []
        try:
            page = open_page(ctx, "events/", errors)
            page.wait_for_timeout(300)
            everything = page.evaluate(CARDS)
            page = open_page(ctx, "events/?filter=neta", errors)
            page.wait_for_timeout(300)
            shown = page.evaluate(CARDS)
            self.assertTrue(shown)
            self.assertTrue(all("neta" in c["group"].split() for c in shown), shown)
            self.assertEqual(len(shown), len([c for c in everything if "neta" in c["group"].split()]))
            chip = page.locator('button.chip[x-show="group"]')
            self.assertTrue(chip.is_visible())
            self.assertTrue(page.locator(".ev-clear").is_visible())
            self.assertIn("filter=neta", page.url)
            chip.click()
            page.wait_for_timeout(200)
            self.assertEqual(len(page.evaluate(CARDS)), len(everything))
            self.assertFalse(chip.is_visible())
            self.assertNotIn("filter=", page.url)
            self.assertEqual(errors, [])
        finally:
            ctx.close()


class Pages(unittest.TestCase):
    def test_the_hero_actions_above_the_fold(self):
        site = S["site"]
        # an event still to come at a real address: its page has the map link
        leaves = sorted(p.parent.name for p in (site / "events").glob("*/index.html")
                        if "evp-hero-actions" in p.read_text(encoding="utf-8")
                        and "google.com/maps/search" in p.read_text(encoding="utf-8").split("evp-hero-all")[0])
        if not leaves:
            self.skipTest("no event at a real address in the day's data")
        ctx = phone()
        errors: list[str] = []
        try:
            page = open_page(ctx, f"events/{leaves[0]}/", errors)
            for sel in (".evp-hero-actions .cm-menu > summary", '.evp-hero-actions a[href*="google.com/maps/search"]'):
                box = page.locator(sel).first.bounding_box()
                self.assertIsNotNone(box, sel)
                self.assertLess(box["y"] + box["height"], 844, sel)
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_see_all_dates_lands_on_every_date(self):
        site = S["site"]
        ctx = phone()
        errors: list[str] = []
        try:
            page = open_page(ctx, "events/", errors)
            link = page.locator('li[id^="ev-series-"] a[href$="#evp-all-dates"]').first
            if not link.count():
                self.skipTest("no monthly series with a page in the day's data")
            link.tap()
            page.wait_for_load_state("load")
            page.wait_for_timeout(300)
            self.assertIn("/events/series/", page.url)
            sec = page.locator("#evp-all-dates")
            self.assertTrue(sec.is_visible())
            box = sec.bounding_box()
            self.assertLess(abs(box["y"]), 200, "scrolled to it")
            hrefs = page.evaluate("[...document.querySelectorAll('#evp-all-dates a.ev-series-date')].map((a) => a.pathname)")
            self.assertGreater(len(hrefs), 3, "more dates than the card's three")
            prefix = "/" + page.url.split("/", 3)[3].split("events/series/")[0]
            missing = [h for h in hrefs if not (site / h[len(prefix):] / "index.html").is_file()]
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
