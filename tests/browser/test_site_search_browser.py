"""Round 37 · the site search's new kinds on the built /search/ page, in a real browser (tests/browser/__init__.py says
how to run these; they share test_site_in_browser.py's site server and browser). The index's logic is in
tests/test_site_search.py.

  * NewKinds — "presentation" (English) lists the five presentations, each labelled "Presentation" with its own icon
               (never the page's fall-back icon), its result opening its card on /orientation/ and, beside it (never
               inside its link), "Start the presentation" — the player's address, in the same tab; "volante" (Spanish)
               lists the flyers ("Volante"); "faq" lists the FAQ's sections, counted under the Pages filter; no script
               error. On a 360px phone with text at 150 %, the presentations' results (and their second link) never
               scroll the page sideways, in both languages.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import S, SIDEWAYS, answered, new_context, open_page, url, setUpModule, tearDownModule  # noqa: F401 (its site server)

RESULTS = """() => [...document.querySelectorAll('#ss-results li')].map((li) => {
  const a = li.querySelector('a[data-nav]'), alt = li.querySelector('a.ss-alt'), kind = li.querySelector('.ss-kind');
  return { href: a.getAttribute('href'), kind: kind ? kind.textContent.trim() : '', icon: !!(kind && kind.querySelector('svg')),
           title: li.querySelector('.ss-title').textContent, alt: alt && alt.getAttribute('href'), altText: alt && alt.textContent.trim(),
           altTab: alt && alt.getAttribute('target'), inside: !!li.querySelector('a[data-nav] .ss-alt') };
})"""


class NewKinds(unittest.TestCase):
    def run_query(self, path: str, lang: str = "en"):
        ctx = S["browser"].new_context(viewport={"width": 1280, "height": 900}, service_workers="block",
                                       locale="es-US" if lang == "es" else "en-US", timezone_id="America/Chicago")
        errors: list[str] = []
        try:
            page = ctx.new_page()
            # (a script error; a picture from another site the test server cannot reach is no fault of the page's)
            page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))
            answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
            page.wait_for_selector("#ss-results li", timeout=20_000)
            pages_chip = page.evaluate("() => { const c = document.querySelector('[data-kind=\"pages\"] [data-n]'); return c ? c.textContent.trim() : ''; }")
            return page.evaluate(RESULTS), pages_chip, errors
        finally:
            ctx.close()

    def test_presentations(self):
        rows, _, errors = self.run_query("search/?q=presentation")
        decks = [r for r in rows if r["kind"] == "Presentation"]
        self.assertEqual(len(decks), 5, rows[:8])
        prefix = S["server"].prefix
        for r in decks:
            self.assertTrue(r["href"].startswith(prefix + "orientation/#pres-"), r["href"])
            self.assertTrue(r["alt"].startswith(prefix + "orientation/?present="), r["alt"])
            self.assertEqual(r["alt"].split("=", 1)[1], r["href"].split("#pres-", 1)[1], "the same deck")
            self.assertIn("Start the presentation", r["altText"])
            self.assertIsNone(r["altTab"], "our own page: the same tab")
            self.assertFalse(r["inside"], "never a link inside the result's link")
            self.assertTrue(r["icon"])
        self.assertEqual(errors, [])

    def test_flyers_in_spanish(self):
        rows, _, errors = self.run_query("es/search/?q=volante", "es")
        flyers = [r for r in rows if r["kind"] == "Volante"]
        self.assertGreaterEqual(len(flyers), 3, rows[:6])
        self.assertEqual(rows[0]["kind"], "Volante")
        self.assertTrue(all(r["icon"] for r in flyers))
        self.assertEqual(errors, [])

    def test_a_presentations_second_link_fits_a_phone_with_large_text(self):
        problems = []
        for lang, path in (("en", "search/?q=presentation"), ("es", "es/search/?q=presentaci%C3%B3n")):
            ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
            try:
                page = open_page(ctx, path)
                page.wait_for_selector("#ss-results a.ss-alt", timeout=20_000)
                page.wait_for_timeout(300)
                r = page.evaluate(SIDEWAYS)
                if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                    problems.append(f"/{path}: scrolls {r['moved']} px sideways ({r['scrollWidth']} px in {r['width']}): {r['wide']}")
                h = page.evaluate("() => document.querySelector('#ss-results a.ss-alt').getBoundingClientRect().height")
                if h < 24:
                    problems.append(f"/{path}: the second link is {h:.0f} px tall")
            finally:
                ctx.close()
        self.assertEqual(problems, [])

    def test_the_faq_is_counted_with_the_pages(self):
        rows, chip, errors = self.run_query("search/?q=faq")
        sections = [r for r in rows if r["kind"] == "Section"]
        self.assertGreaterEqual(len(sections), 7)
        self.assertTrue(all("contribute/#faq" in r["href"] for r in sections[:7]), sections[:7])
        self.assertGreaterEqual(int(chip.replace(",", "") or 0), 7, "the Pages filter counts them")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
