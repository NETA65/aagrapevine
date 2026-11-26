"""La Viña's Spanish presentations in the player, on the built site, in a real browser (tests/browser/__init__.py says
how to run these; they share test_site_in_browser.py's site server and browser):

  * SpanishDeckPlayer — taller-de-escritura opened on the English page and on /es/: every slide marked lang="es"; the
                        player's own words on the slides in Spanish ("Datos al …" on the title slide, "Parte 1 · …"
                        over a part's slides, the live list's head or its "consulta …" line); the notes marked
                        lang="es", with the TIEMPO line; "(in Spanish)" after the deck's name on the English page and
                        no language note on /es/. The English writing workshop on /es/ still says "(en inglés)".
                        No script error.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import new_context, open_page, setUpModule, tearDownModule  # noqa: F401 (its site server)

DECK = "taller-de-escritura"
# the visible language notes after the deck's name (top bar and control bar): their data-gvp-in and words
NOTES = """() => [...document.querySelectorAll('[data-gvp-in]')].filter((n) => n.getClientRects().length > 0 && !n.closest('[hidden]'))
  .map((n) => n.getAttribute('data-gvp-in') + ':' + n.textContent.trim())"""
STAGE = "() => { const s = document.querySelector('[data-gvp-stage] section.gvp-slide'); return s ? { lang: s.getAttribute('lang'), id: s.getAttribute('data-slide'), text: s.innerText } : null; }"


class SpanishDeckPlayer(unittest.TestCase):
    def open(self, ctx, lang: str, deck: str, slide: int, errors: list):
        page = open_page(ctx, ("es/" if lang == "es" else "") + f"orientation/?present={deck}#slide-{slide}", errors)
        page.locator("[data-gvp-stage] section.gvp-slide").first.wait_for(state="visible", timeout=30_000)
        return page

    def test_a_spanish_deck_on_both_pages(self):
        for lang in ("en", "es"):
            errors: list[str] = []
            ctx = new_context(1280, 900, lang=lang)
            try:
                with self.subTest(lang=lang, slide="title"):
                    page = self.open(ctx, lang, DECK, 1, errors)
                    s = page.evaluate(STAGE)
                    self.assertEqual((s["id"], s["lang"]), ("title", "es"))
                    self.assertRegex(page.locator(".gvp-s-asof").first.inner_text(), r"^Datos al \d{1,2} de [a-z]+ de \d{4}$")
                    # "(in Spanish)" on the English page; nothing on /es/ (the deck is in the page's language)
                    notes = page.evaluate(NOTES)
                    if lang == "en":
                        self.assertTrue(notes and all(n == "es:(in Spanish)" for n in notes), notes)
                    else:
                        self.assertEqual(notes, [])
                    # the notes: in Spanish, with the player's TIEMPO line
                    page.locator('[data-gvp-act="notes"]').first.click()
                    body = page.locator("[data-gvp-notes-body]")
                    body.wait_for(state="visible", timeout=10_000)
                    self.assertEqual(body.get_attribute("lang"), "es")
                    self.assertEqual(page.locator("[data-gvp-notes-body] .gvp-timeline strong").first.inner_text().strip(), "TIEMPO:")
                    self.assertIn("DI:", body.inner_text())
                    page.close()
                with self.subTest(lang=lang, slide="a part's slide"):
                    page = self.open(ctx, lang, DECK, 7, errors)
                    s = page.evaluate(STAGE)
                    self.assertEqual((s["id"], s["lang"]), ("meeting-in-print", "es"))
                    self.assertEqual(page.locator("[data-gvp-stage] .gvp-s-eyebrow").first.inner_text().strip().lower(),
                                     "parte 1 · por qué escribimos")
                    page.close()
                with self.subTest(lang=lang, slide="La Viña's themes"):
                    page = self.open(ctx, lang, DECK, 17, errors)
                    s = page.evaluate(STAGE)
                    self.assertEqual((s["id"], s["lang"]), ("lv-themes", "es"))
                    heads = page.locator("[data-gvp-stage] .gvp-live th").all_inner_texts()
                    if heads:
                        self.assertEqual([h.strip().lower() for h in heads], ["edición", "tema", "fecha límite"])
                    else:
                        self.assertIn("consulta aalavina.org/recursos", s["text"])
                    self.assertNotIn("Stories due", s["text"])
                    page.close()
            finally:
                ctx.close()
            self.assertEqual(errors, [], lang)

    def test_an_english_deck_on_the_spanish_page(self):
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="es")
        try:
            page = self.open(ctx, "es", "writing-workshop", 1, errors)
            s = page.evaluate(STAGE)
            self.assertEqual((s["id"], s["lang"]), ("title", "en"))
            notes = page.evaluate(NOTES)
            self.assertTrue(notes and all(n == "en:(en inglés)" for n in notes), notes)
            self.assertRegex(page.locator(".gvp-s-asof").first.inner_text(), r"^Current as of ")
        finally:
            ctx.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
