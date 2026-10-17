"""Carry the Message · Lleva el Mensaje — for anyone who wants to help financially (src/_includes/macros/ctm.njk, the
words in src/_i18n/common.json ctm.*, the buttons' CSS in src/assets/css/areas/shop.css .ctm-*):

  * the words   — both languages, written by hand (the Spanish is not the English); the card says plainly that our
                  committee collects no money and that a gift is a purchase, not a donation; no amounts, no appeal
                  (no "please", "now", "urgent", "!"); what the programs are, as their own pages say (October 2026):
                  a gift certificate from the official store, which the magazine turns into a subscription for an
                  alcoholic in need — the Shop's "How it works" says the same (never "or to someone you choose": that
                  is an ordinary gift certificate, not Carry the Message);
  * the macro   — it shows BOTH programs, read straight from the settings (links.carry_the_message and
                  links.lleva_el_mensaje — never one picked by the page's language, langLink);
  * the pages   — one build of About, the 404 page and Shop, English and Spanish, with links of the test's own
                  (LINKS — not the committee's file): each shows both programs, the page language's first, each
                  opening a new tab said to a screen reader, the other-language one with lang + hreflang and its
                  small "In English" / "En español" tag in its own language; About's card closes "Our committee"
                  (under the four "Who we serve" cards, an h3), the 404 page's sits under its 9 popular pages as a
                  section of its own (an h2 — never a 10th card in their grid) and is bilingual like the rest of that
                  page (GitHub Pages shows the root /404.html for a missing /es/… address too): the title, the words
                  and the note in the other language as well, with lang on them, and on an /es/… address a small
                  script right after the card puts La Viña's button first; the Shop's #carry band (the address
                  /gvr/ and the orientation lesson link) keeps its design and shows both; a link with no address in
                  the settings is left out. The layout in a browser: tests/browser/test_r14_ctm_browser.py.

    python -m unittest tests.test_r14_ctm -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-16T15:00:00Z"        # a fixed clock for the build (nothing here depends on the date)


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


COMMON = json.loads(read("src", "_i18n", "common.json"))
READ = json.loads(read("src", "_i18n", "read.json"))
EXT = {"en": "opens a new tab", "es": "abre una pestaña nueva"}


# --------------------------------------------------------------------------------------------- the words
class Words(unittest.TestCase):
    def keys(self) -> dict[str, dict]:
        return {k: v for k, v in COMMON.items() if k.startswith("ctm.")}

    def test_both_languages_written_for_each(self):
        keys = self.keys()
        self.assertEqual(sorted(keys), ["ctm.in_lang", "ctm.note", "ctm.text", "ctm.title"])
        for k, v in keys.items():
            with self.subTest(key=k):
                self.assertTrue(v["en"].strip() and v["es"].strip())
                self.assertNotEqual(v["en"], v["es"])
        self.assertEqual(keys["ctm.title"], {"en": "Want to help financially?", "es": "¿Quieres ayudar económicamente?"})
        # the tag names the program's language in that language (each is shown with lang="…" on it)
        self.assertEqual(keys["ctm.in_lang"], {"en": "In English", "es": "En español"})

    def test_the_committee_collects_no_money_and_it_is_no_donation(self):
        text, note = COMMON["ctm.text"], COMMON["ctm.note"]
        self.assertTrue(text["en"].startswith("Our committee doesn't collect money."))
        self.assertTrue(text["es"].startswith("Nuestro comité no recibe dinero."))
        self.assertIn("not a donation", note["en"])
        self.assertIn("no un donativo", note["es"])
        # each program by its own name, the official store, and who gets it — as the programs' own pages say
        self.assertIn("Carry the Message gift certificate", text["en"])
        self.assertIn("certificado de regalo de Lleva el Mensaje", text["es"])
        self.assertIn("official store", text["en"])
        self.assertIn("tienda oficial", text["es"])
        self.assertIn("an alcoholic in need", text["en"])
        self.assertIn("un alcohólico necesitado", text["es"])
        self.assertLess(text["es"].index("La Viña"), text["es"].index("Grapevine"))      # La Viña first in Spanish

    def test_no_amount_and_no_appeal(self):
        appeal = re.compile(r"\$|\d|!|¡|please|por favor|\bnow\b|\bahora\b|urgent|urgente|help us|ayúdanos|"
                            r"\bdonate\b|\bdona\b|\bdonar\b", re.I)
        for k, v in self.keys().items():
            for lang in ("en", "es"):
                with self.subTest(key=k, lang=lang):
                    self.assertIsNone(appeal.search(v[lang]), v[lang])

    def test_the_shops_how_it_works_says_the_same(self):
        how1, how2 = READ["read.subs.ctm_how1"], READ["read.subs.ctm_how2"]
        self.assertIn("gift certificate in the official store", how1["en"])
        self.assertIn("certificado de regalo de Lleva el Mensaje en la tienda oficial", how1["es"])
        self.assertIn("an alcoholic in need", how2["en"])
        self.assertIn("un alcohólico necesitado", how2["es"])
        for lang in ("en", "es"):
            self.assertNotIn("you choose" if lang == "en" else "elijas", how2[lang])
        # the one-program button is gone (both are shown now)
        self.assertNotIn("read.subs.ctm_btn", READ)


# --------------------------------------------------------------------------------------------- the macro
class Macro(unittest.TestCase):
    def test_both_programs_straight_from_the_settings(self):
        m = read("src", "_includes", "macros", "ctm.njk")
        self.assertIn("L.carry_the_message", m)
        self.assertIn("L.lleva_el_mensaje", m)
        self.assertNotIn("langLink", re.sub(r"\{#.*?#\}", "", m, flags=re.S))
        for page in ("about.njk", "404.njk", "shop.njk"):
            with self.subTest(page=page):
                t = read("src", "pages", page)
                self.assertIn('{% import "macros/ctm.njk" as ctm with context %}', t)
                self.assertNotIn("langLink('carry_the_message'", t)
                self.assertNotIn("L.carry_the_message", t)

    def test_links_to_the_shops_band_still_land_on_it(self):
        # /gvr/ links /shop/#carry (a duty's link and the "Carry the Message" idea); the band keeps that id (Pages)
        self.assertIn("""'/shop/' | lurl(lang) }}#carry""", read("src", "pages", "gvr.njk"))
        self.assertIn('"#carry"]', read("src", "pages", "gvr.njk"))


# --------------------------------------------------------------------------------------------- the pages
LINKS = {"carry_the_message": "https://www.gv.example.org/carry-test", "lleva_el_mensaje": "https://www.lv.example.org/lleva-test"}
PAGES_JS = r"""
process.env.ONLY = "about.njk,404,shop.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const result = {};
for (const [name, links] of Object.entries(input.builds)) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-ctm-"));
  try {
    const elev = new Eleventy("src", dir, {
      quietMode: true, configPath: "eleventy.config.js",
      config(cfg) {
        cfg.addGlobalData("eleventyComputed", { site: (data) => ({ ...data.site, links: { ...data.site.links, ...links } }) });
      },
    });
    const pages = await elev.toJSON();
    const want = new Set(input.want);
    result[name] = Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content]));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
out(result);
"""
URLS = ["/about/", "/es/about/", "/404.html", "/es/404.html", "/shop/", "/es/shop/"]


def section(page: str, sid: str) -> str:
    """<section id="…">…</section> (holding no other section)."""
    i = page.index(f'<section id="{sid}"')
    return page[i:page.index("</section>", i) + len("</section>")]


def links(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.S):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))
        out.append({**attrs, "_text": m.group(2)})
    return out


def programs(html: str) -> list[dict]:
    return [a for a in links(html) if "ctm-btn" in a.get("class", "").split()]


class Pages(unittest.TestCase):
    built: dict | None = None

    def pages(self, name: str = "both") -> dict:
        if Pages.built is None:
            builds = {"both": LINKS, "gv_only": {**LINKS, "lleva_el_mensaje": ""}}
            Pages.built = run_js(self, PAGES_JS, data={"builds": builds, "want": URLS}, timeout=900, now=NOW)
        return Pages.built[name]

    def places(self) -> list[tuple[str, str, str]]:
        """(url, lang, the card or band's HTML) for every place it shows."""
        p = self.pages()
        out = []
        for lang, pre in (("en", ""), ("es", "/es")):
            out.append((f"{pre}/about/", lang, section(p[f"{pre}/about/"], "ctm")))
            out.append((f"{pre}/404.html", lang, section(p[f"{pre}/404.html"], "nf-ctm")))
            out.append((f"{pre}/shop/", lang, section(p[f"{pre}/shop/"], "carry")))
        return out

    def test_both_programs_the_page_languages_first(self):
        for url, lang, html in self.places():
            with self.subTest(url=url):
                hrefs = [a["href"] for a in programs(html)]
                want = [LINKS["lleva_el_mensaje"], LINKS["carry_the_message"]] if lang == "es" else \
                       [LINKS["carry_the_message"], LINKS["lleva_el_mensaje"]]
                self.assertEqual(hrefs, want)
                cls = [a["class"].split()[0] for a in programs(html)]
                self.assertEqual(cls, ["btn-lv", "btn-primary"] if lang == "es" else ["btn-primary", "btn-lv"])

    def test_each_opens_a_new_tab_and_says_its_language(self):
        for url, lang, html in self.places():
            other = "en" if lang == "es" else "es"
            for a in programs(html):
                away = (a["href"] == LINKS["carry_the_message"]) == (lang == "es")
                plang = other if away else lang
                with self.subTest(url=url, href=a["href"]):
                    self.assertEqual((a.get("target"), a.get("rel")), ("_blank", "noopener"))
                    self.assertIn(f'<span class="sr-only"> ({EXT[lang]})</span>', a["_text"])
                    name = READ["read.subs.ctm_eyebrow"][plang]
                    if away:
                        self.assertEqual(a.get("hreflang"), plang)
                        self.assertIn(f'<span lang="{plang}">{name}</span>', a["_text"])
                        self.assertIn(f'<span class="ctm-btn-tag" lang="{plang}">{COMMON["ctm.in_lang"][plang]}</span>', a["_text"])
                    else:
                        self.assertNotIn("hreflang", a)
                        self.assertIn(f"<span>{name}</span>", a["_text"])
                        self.assertNotIn("ctm-btn-tag", a["_text"])
                    host = "gv.example.org" if a["href"] == LINKS["carry_the_message"] else "lv.example.org"
                    self.assertIn(host, a["_text"])
                    self.assertIn("AA Grapevine" if host.startswith("gv") else "La Viña", a["_text"])

    def test_the_card_says_the_committee_collects_no_money(self):
        for url, lang, html in self.places():
            if "/shop/" in url:
                continue
            other = "en" if lang == "es" else "es"
            with self.subTest(url=url):
                self.assertIn(COMMON["ctm.title"][lang], html)
                self.assertIn(COMMON["ctm.text"][lang].replace("'", "&#39;"), html)
                self.assertIn(COMMON["ctm.note"][lang].replace("'", "&#39;"), html)
                eyebrow = (f'{READ["read.subs.ctm_eyebrow"][lang]} · <span lang="{other}">'
                           f'{READ["read.subs.ctm_eyebrow"][other]}</span>')
                self.assertIn(eyebrow, html)

    def test_the_404_card_says_it_in_both_languages(self):
        """GitHub Pages answers every missing address, /es/… too, with the root /404.html: its card says "¿Quieres
        ayudar económicamente? / Nuestro comité no recibe dinero" as well (and /es/404.html the English) — in an
        element with lang on it, after the page language's words; About's card is in the page's language only."""
        p = self.pages()
        for url, lang, other in (("/404.html", "en", "es"), ("/es/404.html", "es", "en")):
            with self.subTest(url=url):
                card = section(p[url], "nf-ctm")
                m = re.search(r'<div class="ctm-other[^"]*" lang="(\w+)">(.*?)</div>', card, re.S)
                self.assertIsNotNone(m, "the other language's words")
                self.assertEqual(m.group(1), other)
                words = m.group(2)
                self.assertIn(COMMON["ctm.title"][other], words)
                self.assertIn(COMMON["ctm.text"][other].replace("'", "&#39;"), words)
                self.assertIn(COMMON["ctm.note"][other].replace("'", "&#39;"), words)
                self.assertNotIn("<h2", words)                                   # one card, one heading
                self.assertLess(card.index(COMMON["ctm.title"][lang]), m.start())  # the page language's first
                self.assertLess(m.end(), card.index("ctm-links"))
                self.assertEqual(card.count("<h2 "), 1)
        for url in ("/about/", "/es/about/"):
            with self.subTest(url=url):
                self.assertNotIn("ctm-other", section(p[url], "ctm"))

    def test_a_missing_spanish_address_puts_la_vinas_button_first(self):
        """On the root /404.html a tiny script right after the card (before the first paint) moves La Viña's Lleva
        el Mensaje button first when the address is under <base>es/ — as the "¿Eres nuevo en AA?" card's does; on
        /es/404.html (La Viña first already) there is none, and without JavaScript the order stays as built."""
        p = self.pages()
        page = p["/404.html"]
        start = page.index('<section id="nf-ctm"')
        m = re.match(r'(<section id="nf-ctm".*?</section>)\s*</div>\s*<script>(.*?)</script>', page[start:], re.S)
        self.assertIsNotNone(m, "the script right after the card")
        card, script = m.group(1), m.group(2)
        self.assertNotIn('getElementById("nf-ctm")', p["/es/404.html"])
        self.assertNotIn('getElementById("nf-ctm")', p["/about/"])
        r = run_js(self, PAGE_JS + r"""
          const order = (path, base, html) => {
            const p = page({ url: "https://example.test" + path, html: html || input.card, globals: { SITE: { lang: "en", base } } });
            vm.runInContext(input.script, p.win);
            return [...p.$("#nf-ctm .ctm-links").children].map((li) => li.getAttribute("data-ctm"));
          };
          out({ es: order("/es/una-pagina-que-no-existe/", "/"), en: order("/una-pagina/", "/"), file: order("/es/viejo.pdf", "/"),
                word: order("/escuela/", "/"), pages: order("/aagrapevine/es/una-pagina/", "/aagrapevine/"),
                other: order("/es/una-pagina/", "/aagrapevine/"), noBase: order("/es/una-pagina/", undefined),
                gvOnly: order("/es/una-pagina/", "/", input.gvOnly) });""",
                   data={"card": card, "script": script, "gvOnly": section(self.pages("gv_only")["/404.html"], "nf-ctm")},
                   needs_modules=False)
        es_first, en_first = ["es", "en"], ["en", "es"]
        self.assertEqual(r, {"es": es_first, "en": en_first, "file": es_first, "word": en_first, "pages": es_first,
                             "other": en_first, "noBase": en_first, "gvOnly": ["en"]})

    def test_about_closes_our_committee(self):
        for url, lang in (("/about/", "en"), ("/es/about/", "es")):
            with self.subTest(url=url):
                page = self.pages()[url]
                committee = page[page.index('<section id="committee"'):page.index('id="booth"')]
                self.assertIn('<section id="ctm"', committee)
                # under the four "Who we serve" cards, the last thing in the section
                serve = committee.index(READ["read.about.serve_title"][lang])
                cards = committee.index("</ul>", serve)
                self.assertLess(cards, committee.index('<section id="ctm"'))
                self.assertEqual(committee[committee.index("</section>", committee.index('<section id="ctm"')) + 10:]
                                 .strip()[:6], "</div>")
                card = section(page, "ctm")
                self.assertIn('<h3 id="ctm-h"', card)
                self.assertIn('aria-labelledby="ctm-h"', card)
                self.assertEqual(page.count('id="ctm"'), 1)

    def test_the_404_card_is_a_row_of_its_own_under_the_nine_pages(self):
        for url in ("/404.html", "/es/404.html"):
            with self.subTest(url=url):
                page = self.pages()[url]
                i = page.index('<ul class="nf-popular grid-cards-4')
                grid = page[i:page.index("</ul>", i)]
                self.assertEqual(grid.count("<li "), 9, "three even rows of 3")
                self.assertNotIn("ctm", grid)
                self.assertLess(page.index("nf-popular-h"), page.index('<section id="nf-ctm"'))
                self.assertGreater(page.index('<section id="nf-ctm"'), page.index("</section>", i))  # after the popular section
                self.assertIn('<h2 id="nf-ctm-h"', section(page, "nf-ctm"))

    def test_the_shop_band_keeps_its_place_and_design(self):
        for url, lang in (("/shop/", "en"), ("/es/shop/", "es")):
            with self.subTest(url=url):
                page = self.pages()[url]
                band = section(page, "carry")
                self.assertIn('aria-labelledby="ctm-title"', band)
                self.assertIn(READ["read.subs.ctm_title"][lang], band)
                self.assertIn("shop-ctm-ways", band)                         # the four places a gift goes
                self.assertIn(READ["read.subs.ctm_how_title"][lang], band)    # "How it works"
                self.assertIn(READ["read.subs.ctm_gvr"][lang].replace("&", "&amp;"), band)
                self.assertIn('href="#carry"', page)                          # the page nav still leads there
                other = "en" if lang == "es" else "es"
                self.assertIn(f'<span lang="{other}">{READ["read.subs.ctm_eyebrow"][other]}</span>', band)

    def test_a_link_with_no_address_is_left_out(self):
        p = self.pages("gv_only")
        for url in URLS:
            page = p[url]
            sid = "carry" if "shop" in url else ("nf-ctm" if "404" in url else "ctm")
            with self.subTest(url=url):
                hrefs = [a["href"] for a in programs(section(page, sid))]
                self.assertEqual(hrefs, [LINKS["carry_the_message"]])
                self.assertNotIn('href=""', section(page, sid))


if __name__ == "__main__":
    unittest.main()
