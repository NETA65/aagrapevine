"""Round 14, the publishers' permission credits — the static contract (what a browser measures is
tests/browser/test_r14_v2_credits_browser.py).

  * Daily quote — Home's daily-quote card (index.njk section.home-quote) ends with ONE quiet line under both quotes:
                  A.A.W.S.'s "Reprinted with permission of A.A. World Services, Inc." and AA Grapevine's "Copyright ©
                  The AA Grapevine, Inc. Reprinted with permission. All rights reserved." in their own wording (the
                  Spanish pages: "Reimpreso con permiso …", the company names never translated). It sits after the
                  quotes' grid, not in one quote, so a phone — one quote shown, the other behind its button — keeps
                  it whichever quote shows; 12px in the faint token (areas/home.css .home-quote-rights).
  * Booth       — the live-quote slide (eleventy/filters/booth.js liveQuotes) shows the same quotes: its credit line
                  ends with the same two credits, in the quote's language, " · " between them as on Home
                  (tests/test_booth_build.py has the item).
  * Footer      — the copyright / permission notice (footer.njk .site-footer-notice, the one part of the footer that
                  prints) in two short runs: the credits — Grapevine and La Viña material, covers and other graphics
                  included: AA Grapevine's credit line; A.A. literature reprinted with A.A.W.S.'s permission and its
                  graphics "used with permission of A.A. World Services, Inc." (footer.reprints) — then what that
                  permission does not mean (footer.reprints_note), English and Spanish.
  * Elsewhere   — the same notice where the footer is not: the monthly digest e-mail (it shows the covers:
                  send_digest.py footer_reprints = the site's credits + its own "this summary" sentences; one
                  paragraph per language), the printed /digest/ (it prints without the site footer: digest.njk
                  .cm-dg-notice, on paper only), and the RSS feeds' channel <copyright> (the items carry the
                  publishers' teasers and pictures).

    python -m unittest tests.test_r14_v2_credits -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

AAWS = {"en": "Reprinted with permission of A.A. World Services, Inc.",
        "es": "Reimpreso con permiso de A.A. World Services, Inc."}
GV = {"en": "Copyright © The AA Grapevine, Inc. Reprinted with permission. All rights reserved.",
      "es": "Copyright © The AA Grapevine, Inc. Reimpreso con permiso. Todos los derechos reservados."}


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def i18n(name: str) -> dict:
    return json.loads(read("src", "_i18n", name))


class DailyQuoteCredit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = i18n("home.json")
        page = read("src", "pages", "index.njk")
        cls.card = page[page.index('<section class="card home-quote"'):]
        cls.card = cls.card[:cls.card.index("</section>")]

    def test_the_publishers_own_wording(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertEqual(self.words["home.quote_credit_aaws"][lang], AAWS[lang])
                self.assertEqual(self.words["home.quote_credit_gv"][lang], GV[lang])
        # the company names are never translated
        for lang in ("en", "es"):
            self.assertIn("A.A. World Services, Inc.", self.words["home.quote_credit_aaws"][lang])
            self.assertIn("The AA Grapevine, Inc.", self.words["home.quote_credit_gv"][lang])

    def test_once_under_both_quotes(self):
        # (the dot between the two credits: off a line's start, and not read out)
        line = ('<p class="home-quote-rights">{{ "home.quote_credit_aaws" | t(L) }}&nbsp;<span aria-hidden="true">·</span> '
                '{{ "home.quote_credit_gv" | t(L) }}</p>')
        self.assertEqual(self.card.count(line), 1, "one line for the card")
        self.assertEqual(self.card.count("home.quote_credit_"), 2)
        # after the quotes' grid (closed), never inside one quote: a phone shows one quote, the credit stays
        grid_end = self.card.rindex("</article>")
        self.assertGreater(self.card.index(line), grid_end)
        between = self.card[grid_end:self.card.index(line)]
        self.assertIn("{% endfor %}", between)
        self.assertEqual(between.count("</div>"), 1, "the grid is closed before the credit")
        self.assertNotIn("home-quote-rights", self.card[:grid_end])

    def test_quiet_and_legible(self):
        css = read("src", "assets", "css", "areas", "home.css")
        rule = re.search(r"\.home-quote-rights \{([^}]*)\}", css)
        self.assertIsNotNone(rule)
        body = rule.group(1)
        self.assertIn("font-size: 0.75rem", body)              # 12px, never smaller
        self.assertIn("color: var(--c-faint)", body)           # the token: dark mode and high contrast follow
        self.assertNotRegex(body, r"display:\s*none")
        # never hidden on a phone or on paper
        self.assertNotRegex(css, r"home-quote-rights[^{]*\{[^}]*display:\s*none")
        self.assertNotIn("home-quote-rights", read("src", "assets", "css", "main.css"))

    def test_the_booth_slide_uses_the_same_words(self):
        js = read("eleventy", "filters", "booth.js")
        fn = js[js.index("function liveQuotes(c)"):]
        fn = fn[:fn.index("\n}\n")]
        # the same two keys, each its own part of the line: the line's " · " separates them, as the Home card's dot does
        self.assertIn(r'const aaws = t("home.quote_credit_aaws", lang).replace(/\bA\.A\. (?=World Services)/g, "A.A.\u00a0");', fn)
        self.assertRegex(fn, r'const credit = \[oneLine\(q\.attribution\), from \? [^\]]*, aaws,\s+t\("home\.quote_credit_gv", lang\)\]'
                             r'\.filter\(Boolean\)\.join\(" · "\);')
        self.assertNotIn("${t(\"home.quote_credit_aaws\", lang)} ${t(\"home.quote_credit_gv\", lang)}", fn)


class FooterNotice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = i18n("common.json")

    def test_the_credits_text_and_graphics(self):
        en, es = self.words["footer.reprints"]["en"], self.words["footer.reprints"]["es"]
        # AA Grapevine's credit line, for Grapevine and La Viña material — covers and other graphics included
        self.assertIn(GV["en"], en)
        self.assertIn(GV["es"], es)
        self.assertTrue(en.startswith("Grapevine and La Viña material, including magazine and book covers and other graphics: "))
        self.assertTrue(es.startswith("Material de Grapevine y La Viña, incluidas las portadas de revistas y libros y otras imágenes: "))
        # A.A.W.S.: excerpts of A.A. literature reprinted, and its graphics used, with its permission
        self.assertIn("Excerpts from A.A. literature are reprinted with permission of Alcoholics Anonymous World Services, Inc. (A.A.W.S.)", en)
        self.assertIn("A.A.W.S. graphics are used with permission of A.A. World Services, Inc.", en)
        self.assertIn("Los extractos de la literatura de A.A. se reimprimen con permiso de Alcoholics Anonymous World Services, Inc. (A.A.W.S.)", es)
        self.assertIn("las imágenes de A.A.W.S. se usan con permiso de A.A. World Services, Inc.", es)
        for text in (en, es):
            self.assertNotIn("Derechos de autor", text)          # one notice, one form: "Copyright ©" as the publishers write it
            self.assertNotIn("  ", text)
            self.assertNotRegex(text, r":\S")                     # a space after every colon

    def test_what_the_permission_does_not_mean(self):
        en, es = self.words["footer.reprints_note"]["en"], self.words["footer.reprints_note"]["es"]
        self.assertIn("Permission to reprint or use this material does not mean that AA Grapevine, Inc. or A.A.W.S. has "
                      "reviewed or approved the contents of this website", en)
        self.assertIn("This is not an official website of AA Grapevine, Inc. or A.A.W.S.", en)
        self.assertIn("El permiso para reimprimir o usar este material no significa que AA Grapevine, Inc. o A.A.W.S. "
                      "hayan revisado o aprobado el contenido de este sitio web", es)
        self.assertIn("Este no es un sitio web oficial de AA Grapevine, Inc. ni de A.A.W.S.", es)
        # the two runs do not repeat each other
        self.assertNotIn("does not mean", self.words["footer.reprints"]["en"])
        self.assertNotIn("Copyright", en)

    def test_two_runs_of_the_one_printed_notice(self):
        tpl = read("src", "_includes", "partials", "footer.njk")
        self.assertEqual(tpl.count("site-footer-notice"), 1)
        self.assertIn('<p class="site-footer-notice text-faint text-pretty md:col-span-2"><span class="block">'
                      '{{ "footer.reprints" | t(L) }}</span> <span class="mt-2 block">{{ "footer.reprints_note" | t(L) }}</span></p>', tpl)
        # the template comment says what the notice holds
        self.assertIn("footer.reprints_note", tpl[:tpl.index("<div class=\"border-t border-line\">")])
        # on paper the whole notice stays (main.css keeps .site-footer-notice and everything in it)
        css = read("src", "assets", "css", "main.css")
        self.assertIn(".site-footer-main, .site-footer :has(> .site-footer-notice) > :not(.site-footer-notice) { display: none !important; }", css)


class ElsewhereTheSameNotice(unittest.TestCase):
    def test_the_digest_email(self):
        from scripts.notify import send_digest as D
        words = i18n("common.json")
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                mail = D.T[lang]["footer_reprints"]
                # the site's credits word for word (the e-mail shows the covers), then its own sentences
                self.assertTrue(mail.startswith(words["footer.reprints"][lang] + " "), mail)
                self.assertNotIn("Derechos de autor", mail)
        self.assertIn("has reviewed or approved this summary", D.T["en"]["footer_reprints"])
        self.assertIn("hayan revisado o aprobado este resumen", D.T["es"]["footer_reprints"])
        self.assertIn("This is not an official publication of AA Grapevine, Inc. or A.A.W.S.", D.T["en"]["footer_reprints"])
        src = read("scripts", "notify", "send_digest.py")
        # in the HTML part one paragraph per language, as footer_why's (run together they read as one block)
        self.assertIn("""<p style="margin:0 0 8px;">{_esc(T['en']['footer_reprints'])}</p>
  <p lang="es" style="margin:0 0 8px;">{_esc(T['es']['footer_reprints'])}</p>""", src)
        self.assertNotIn("<span lang=\"es\">{_esc(T['es']['footer_reprints'])}</span>", src)
        self.assertIn('out.append(T["en"]["footer_reprints"])', src)
        self.assertIn('out.append(T["es"]["footer_reprints"])', src)

    def test_the_printed_digest(self):
        page = read("src", "pages", "digest.njk")
        edition = page[page.index('<article'):page.index("</article>")]
        line = ('<p class="cm-dg-notice hidden text-faint print:block"><span class="block">{{ "footer.reprints" | t(lang) }}</span> '
                '<span class="mt-2 block">{{ "footer.reprints_note" | t(lang) }}</span></p>')
        self.assertIn(line, edition)
        self.assertGreater(edition.index(line), edition.index("</footer>"), "at the edition's foot")
        css = read("src", "assets", "css", "areas", "community.css")
        self.assertIn(".cm-page-digest .cm-dg-notice { padding-top: 0.75rem; font-size: 0.6875rem; line-height: 1.35; break-inside: avoid; }", css)
        # the page still prints without the site footer (so the notice is not there twice)
        self.assertIn("body.cm-print-light > header, body.cm-print-light > footer", css)

    def test_the_rss_channel(self):
        from nodejs import run_js
        script = r"""
const feed = await imp("src/pages/feed.11ty.js");
const site = { url: "https://example.org/site", built: "2026-10-16T12:00:00Z", contact_email: "x@example.org" };
const res = {};
for (const lang of ["en", "es"]) {
  const xml = feed.render.call({ t: (k, l, v) => filters.t(k, l, v) }, { site, db: { whatsnew: { items: [] } }, lang });
  res[lang] = (xml.match(/<copyright>([^<]*)<\/copyright>/) || [])[1] || null;
  res[lang + "_count"] = (xml.match(/<copyright>/g) || []).length;
}
out(res);
"""
        r = run_js(self, script)
        words = i18n("common.json")
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertEqual(r[lang + "_count"], 1)
                self.assertEqual(r[lang], words["footer.reprints"][lang].replace("&", "&amp;"))


if __name__ == "__main__":
    unittest.main()
