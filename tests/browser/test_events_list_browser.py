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
              The old ?filter=neta (its "NETA 65 events" chip) shows ours and the committee meetings, its chip
              pressed; pressing it shows every card and drops it from the address (round 38: the chip is always
              there, so it can be picked again). The old ?filter=calendar shows what its chip showed: every card of
              the GV & LV calendars' group (La Viña's monthly workshop and the weekly open meetings too).
  * Large   — (round 38) at 115 / 130 / 150 % text (and relaxed spacing) on 320–414px phones, English and Spanish:
              "Next 5 weeks" never sits under "Show the calendar" (the button goes under it) and keeps most of the
              card's width; the hero's "Save the date" title keeps at least 8rem or the whole width (its date tile
              above it); no page scrolls sideways.
  * Links   — (round 38) an old link to a committee meeting's later date (/events/#ev-committee-…) opens that date
              on the committee meeting's dates page; the date its card shows stays on /events/; an old #month-… of a
              month with only monthly dates lands on "Every month"; a link to a past event's row brings it in view.
              The dates page: every date a card with its own Add to calendar (its full links once opened), no page
              scrolling sideways. A link to a later date there (its Share button's; an old /events/ link sent on, the
              last date too) lands on that date's card with smooth scrolling on, phone and desktop — the page comes
              with every card drawn (cm-cv-all), so without JavaScript too; once the landing has settled it lets the
              cards far off the screen go undrawn again and the date stays where it landed. The calendar
              subscription: /events/#subscribe (/meetings/, /stay-updated/ and Home's calendar card — when Home
              lists fewer than three events — link there) lands on it, and so does a series page's "Every date:
              subscribe to the calendar" (its own card, #subscribe).
  * Pages   — an event's own page at 390px: Add to calendar and Directions in the hero, above the fold. A series'
              card's "See all dates" lands on its page's "All dates", every date there a link to a page of the site.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import S, contrast, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401


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
            # (a card of two kinds — La Viña's monthly workshop is one of the GV & LV calendars' too: "workshop calendar")
            self.assertTrue(all("workshop" in c["kind"].split() for c in shown), shown)
            self.assertIn("kind=workshop", page.url)
            self.assertEqual(page.locator('[data-ev-kind="workshop"]').get_attribute("aria-pressed"), "true")
            self.assertTrue(page.locator(".ev-clear").is_visible())
            # with a language: only those held in it
            langs = sorted({c["lang"] for c in shown})
            page.select_option('select[data-ev-facet="lang"]', langs[-1])
            page.wait_for_timeout(200)
            narrowed = page.evaluate(CARDS)
            self.assertTrue(narrowed)
            self.assertEqual({("workshop" in c["kind"].split(), c["lang"]) for c in narrowed}, {(True, langs[-1])})
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
            self.assertEqual({("workshop" in c["kind"].split(), c["lang"]) for c in again.evaluate(CARDS)}, {(True, langs[-1])})
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
            chip = page.locator('button.chip[data-ev-group="neta"]')
            self.assertTrue(chip.is_visible())
            self.assertEqual(chip.get_attribute("aria-pressed"), "true")
            self.assertTrue(page.locator(".ev-clear").is_visible())
            self.assertIn("filter=neta", page.url)
            chip.click()
            page.wait_for_timeout(200)
            self.assertEqual(len(page.evaluate(CARDS)), len(everything))
            self.assertTrue(chip.is_visible(), "round 38: the chip stays, to be picked again")
            self.assertEqual(chip.get_attribute("aria-pressed"), "false")
            self.assertNotIn("filter=", page.url)
            chip.click()
            page.wait_for_timeout(200)
            self.assertEqual(len(page.evaluate(CARDS)), len(shown), "picked from the page")
            self.assertIn("filter=neta", page.url)
            # the old ?filter=calendar: every card of the GV & LV calendars' group, as its old chip
            page = open_page(ctx, "events/?filter=calendar", errors)
            page.wait_for_timeout(300)
            cal = page.evaluate(CARDS)
            self.assertEqual(sorted(c["id"] for c in cal), sorted(c["id"] for c in everything if "calendar" in c["group"].split()))
            self.assertEqual(errors, [])
        finally:
            ctx.close()


# (round 38) the "Next 5 weeks" heading beside its button, and the hero's "Save the date" title beside its tile
LARGE = """() => {
  const h = document.querySelector('#ev-cal-title'), b = document.querySelector('.ev-cal-toggle'), card = document.querySelector('#ev-cal');
  const hr = h.getBoundingClientRect(), br = b.getBoundingClientRect(), cr = card.getBoundingClientRect();
  const rg = document.createRange(); rg.selectNodeContents(h);
  let under = 0;
  if (br.width) for (const x of rg.getClientRects()) { const w = Math.min(x.right, br.right) - Math.max(x.left, br.left), t = Math.min(x.bottom, br.bottom) - Math.max(x.top, br.top); if (w > 0 && t > 0) under += w * t; }
  const sd = document.querySelector('.cm-ha-ev');
  const body = sd ? sd.querySelector('.cm-ha-ev-body') : null;
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  return { under: Math.round(under), share: hr.width / cr.width, sd: !!(sd && sd.getClientRects().length),
           bodyW: body ? body.getBoundingClientRect().width : 0, sdW: sd ? sd.getBoundingClientRect().width : 0, rem,
           sw: document.documentElement.scrollWidth, vw: innerWidth };
}"""


class Large(unittest.TestCase):
    def test_the_calendar_heading_and_save_the_date(self):
        for w in (320, 390, 414):
            for prefs in ({"text": 115}, {"text": 130}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                for lang in ("en", "es"):
                    with self.subTest(width=w, prefs=prefs, lang=lang):
                        ctx = new_context(w, 844, lang=lang, prefs=prefs)
                        try:
                            page = open_page(ctx, ("es/" if lang == "es" else "") + "events/")
                            r = page.evaluate(LARGE)
                            self.assertEqual(r["under"], 0, "the heading is never under the button")
                            self.assertGreater(r["share"], 0.6, "the heading keeps most of the card's width")
                            if r["sd"]:
                                self.assertTrue(r["bodyW"] >= 8 * r["rem"] - 1 or r["bodyW"] >= r["sdW"] - 1, r)
                            self.assertLessEqual(r["sw"], r["vw"])
                        finally:
                            ctx.close()


class Links(unittest.TestCase):
    def test_old_links_land_where_they_should(self):
        ctx = new_context(390, 844)
        errors: list[str] = []
        try:
            page = open_page(ctx, "events/", errors)
            # (the committee meeting's card: its dates' anchors, the first the date it shows)
            anchors = page.evaluate("() => { const li = document.querySelector('li[data-ev-dates]'); return li ? "
                                    "[...li.querySelectorAll('[data-ev-date-anchors] > span')].map((s) => s.id) : []; }")
            if len(anchors) < 2:
                self.skipTest("no committee meeting with two dates to come in this build")
            # a later date: its card on the committee meeting's dates page
            page = open_page(ctx, "events/#" + anchors[1], errors)
            page.wait_for_url(lambda u: "/events/series/committee-meeting/" in u, timeout=30_000)
            page.wait_for_timeout(800)
            self.assertTrue(page.url.endswith("#" + anchors[1]))
            box = page.locator("#" + anchors[1]).bounding_box()
            self.assertIsNotNone(box)
            self.assertLess(abs(box["y"]), 400, box)
            # (round 38) the last date, smooth scrolling on (the browser's default), phone and desktop: its card
            for w, h in ((390, 844), (1280, 900)):
                smooth = S["browser"].new_context(viewport={"width": w, "height": h}, service_workers="block")
                try:
                    p2 = open_page(smooth, "events/#" + anchors[-1], errors)
                    p2.wait_for_url(lambda u: "/events/series/committee-meeting/" in u, timeout=30_000)
                    p2.wait_for_load_state("load")
                    p2.wait_for_timeout(2500)
                    top = p2.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", anchors[-1])
                    self.assertTrue(-5 <= top < h * 0.5, f"{w}px {anchors[-1]}: its card's top at {top} px")
                finally:
                    smooth.close()
            # the date its card shows: stays
            page = open_page(ctx, "events/#" + anchors[0], errors)
            page.wait_for_timeout(800)
            self.assertIn("/events/#" + anchors[0], page.url)
            # an old month that has only monthly dates now: "Every month"
            months = page.evaluate("() => [...document.querySelectorAll('[data-ev-anchors] > span')].map((s) => s.id)")
            if months:
                page = open_page(ctx, "events/#" + months[-1], errors)
                page.wait_for_timeout(1500)
                top = page.evaluate("() => document.getElementById('ev-pinned-title').getBoundingClientRect().top")
                self.assertTrue(-5 <= top < 300, top)
            # a past event's row: in view, under the header
            past = page.evaluate("() => { const r = document.querySelector('details[data-cm-past] li[id]'); return r ? r.id : ''; }")
            if past:
                smooth = S["browser"].new_context(viewport={"width": 390, "height": 844}, service_workers="block")
                try:
                    p2 = open_page(smooth, "events/#" + past, errors)
                    p2.wait_for_timeout(3500)
                    top = p2.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", past)
                    self.assertTrue(0 <= top < 844 * 0.6, f"{past}: its row's top at {top} px")
                finally:
                    smooth.close()
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_a_link_to_a_later_date_lands_on_its_card(self):
        """(round 38) the dates page's own links (each date's Share): with smooth scrolling on, a date halfway down and
        the last one land on their card — before, the cards skipped until near (content-visibility) were placed by a
        guessed height and the page stopped up to 2,600px past the date, on another month"""
        errors: list[str] = []
        for w, h in ((390, 844), (1280, 900)):
            ctx = S["browser"].new_context(viewport={"width": w, "height": h}, service_workers="block")
            try:
                page = open_page(ctx, "events/series/committee-meeting/", errors)
                ids = page.evaluate("() => [...document.querySelectorAll('#evp-all-dates li[id^=\"ev-committee-\"]')].map((li) => li.id)")
                if len(ids) < 4:
                    self.skipTest("fewer than four committee meeting dates to come in this build")
                page.close()
                for i in (ids[len(ids) // 2], ids[-1]):
                    page = open_page(ctx, "events/series/committee-meeting/#" + i, errors)
                    page.wait_for_timeout(2500)
                    top = page.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", i)
                    self.assertTrue(-5 <= top < h * 0.5, f"{w}px #{i}: its card's top at {top} px")
                    # (round 38) once the landing has settled the page lets the cards far off the screen go undrawn
                    # again (committee.js datesSettle: a Dark / Light switch cost ~290 ms with all 25 drawn) — and
                    # nothing moves: each card keeps the height it was drawn at
                    page.wait_for_function("() => !document.getElementById('evp-all-dates').classList.contains('cm-cv-all')",
                                           timeout=8000)
                    page.wait_for_timeout(300)
                    after = page.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", i)
                    self.assertLessEqual(abs(after - top), 2, f"{w}px #{i}: moved from {top} to {after} px")
                    page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_without_javascript_a_later_date_lands_too(self):
        """(round 38) the dates page comes with every card drawn (cm-cv-all in its HTML): without JavaScript the class
        stays, and the last date lands on its card"""
        for w, h in ((390, 844), (1280, 900)):
            ctx = S["browser"].new_context(viewport={"width": w, "height": h}, service_workers="block", java_script_enabled=False)
            try:
                page = ctx.new_page()
                page.goto(url("events/series/committee-meeting/"), wait_until="load")
                ids = page.evaluate("() => [...document.querySelectorAll('#evp-all-dates li[id^=\"ev-committee-\"]')].map((li) => li.id)")
                if len(ids) < 4:
                    self.skipTest("fewer than four committee meeting dates to come in this build")
                page.goto(url("events/series/committee-meeting/#" + ids[-1]), wait_until="load")
                page.wait_for_timeout(2500)
                self.assertTrue(page.evaluate("() => document.getElementById('evp-all-dates').classList.contains('cm-cv-all')"))
                top = page.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", ids[-1])
                self.assertTrue(-5 <= top < h * 0.5, f"{w}px #{ids[-1]} without JavaScript: its card's top at {top} px")
                page.close()
            finally:
                ctx.close()

    def test_the_calendar_subscription_links_land_on_it(self):
        errors: list[str] = []
        for w, h in ((390, 844), (1280, 900)):
            ctx = S["browser"].new_context(viewport={"width": w, "height": h}, service_workers="block")
            try:
                # /events/#subscribe, a fresh load (/meetings/' and /stay-updated/'s links, and Home's calendar card's
                # when Home lists fewer than three events)
                page = open_page(ctx, "events/#subscribe", errors)
                page.wait_for_timeout(2500)
                top = page.evaluate("() => document.getElementById('subscribe').getBoundingClientRect().top")
                self.assertTrue(-5 <= top < h * 0.5, f"{w}px /events/#subscribe: its top at {top} px")
                page.close()
                # a series page: "Every date: subscribe to the calendar" in its Add to calendar menu → its own card
                series = sorted(d.name for d in (S["site"] / "events" / "series").iterdir()
                                if 'href="#subscribe"' in ((d / "index.html").read_text(encoding="utf-8") if (d / "index.html").is_file() else ""))
                if not series:
                    self.fail("no series page with the subscription line")
                page = open_page(ctx, f"events/series/{series[0]}/", errors)
                page.locator(".hero details.cm-menu > summary, details.cm-menu > summary").first.click()
                line = page.locator("details.cm-menu[open] a[href='#subscribe']")
                self.assertEqual(line.count(), 1)
                line.click()
                page.wait_for_timeout(2500)
                self.assertTrue(page.url.endswith(f"/events/series/{series[0]}/#subscribe"), page.url)
                top = page.evaluate("() => document.getElementById('subscribe').getBoundingClientRect().top")
                self.assertTrue(-5 <= top < h * 0.5, f"{w}px a series page's #subscribe: its top at {top} px")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_the_committee_meetings_dates_page(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = phone(lang)
                errors: list[str] = []
                try:
                    pre = "es/" if lang == "es" else ""
                    page = open_page(ctx, pre + "events/series/committee-meeting/", errors)
                    ids = page.evaluate("() => [...document.querySelectorAll('#evp-all-dates li[id^=\"ev-committee-\"]')].map((li) => li.id)")
                    self.assertGreater(len(ids), 1)
                    menu = page.locator(f"#{ids[-1]} details.cm-menu > summary")
                    menu.scroll_into_view_if_needed()
                    menu.tap()
                    page.wait_for_timeout(200)
                    g = page.locator(f'#{ids[-1]} details.cm-menu a[href^="https://calendar.google.com/"]').get_attribute("href")
                    self.assertIn("details=", g, "the full link once the menu opens")
                    self.assertLessEqual(page.evaluate("document.scrollingElement.scrollWidth"), 390)
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
