"""Round 12, "New to AA? / ¿Eres nuevo en AA?" — the first-steps card (src/_includes/macros/ui.njk newcomerCard and
newcomerLine, eleventy/filters/newcomer.js, config/site.yml links: aa_find / aa_is_aa_for_you / aa_meeting_guide):

  * the offices    — ncOffices lists the offices of meetings.feeds that are in our Area, by their own sites (never a
                     feed address), each once, in the settings' order; on a Spanish page the Spanish-speaking office
                     (Alcohólicos Anónimos Dallas) first;
  * the settings   — the card reads its three links through langLink; the committee's file (RealSettings, a content
                     test: scripts/ops/gate_tests.py CONTENT_TESTS) has them on aa.org, each with its Spanish page on
                     aa.org/es, and a Spanish-speaking office in our Area, first on /es/;
  * the words      — written in both languages (the Spanish is not the English), no phone number, no clinical or
                     treatment words; the Meetings page's search words find it ("help", "ayuda" …);
  * the pages      — one build of Home, Meetings and the 404 page, English and Spanish, with offices and links of the
                     test's own (FEEDS, LINKS — not the committee's file): the card opens Meetings (before
                     the committee's meeting), in the page's language, with aa.org's pages in that language and the
                     Spanish-speaking office first on /es/; it links ONLY to AA (aa.org, the offices, the Area's site:
                     no other host, no tel: link), each new tab said to a screen reader; the 404 page shows the
                     compact card in both languages (the page's first; the root page, which answers a missing /es/…
                     address too, puts the Spanish first there), each with a link to the full card; Home has one
                     line to it, before the service band.

    python -m unittest tests.test_r12_u6_newcomers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-15T15:00:00Z"        # a fixed clock for the build (nothing here depends on the date)


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


COMMON = json.loads(read("src", "_i18n", "common.json"))
LIBRARY = json.loads(read("src", "_i18n", "library.json"))
CARD_LINKS = ("aa_find", "aa_is_aa_for_you", "aa_meeting_guide")


# --------------------------------------------------------------------------------------------- the offices
OFFICES_JS = r"""
const f = filters.ncOffices;
out({ en: f(input.site, "en"), es: f(input.site, "es"), other: f(input.site, "fr"),
      none: f(null, "en"), noFeeds: f({ meetings: { feeds: "x" } }, "es") });
"""


class Offices(unittest.TestCase):
    r: dict | None = None

    def res(self) -> dict:
        if Offices.r is None:
            feeds = [
                {"id": "big", "name": "Big City Intergroup", "site": "https://www.big.example.org", "lang": "en", "in_area": True,
                 "feed": "https://www.big.example.org/wp-admin/admin-ajax.php?action=meetings&key=secret"},
                {"id": "far", "name": "Far Away Office", "site": "https://far.example.org", "lang": "en", "in_area": False},
                {"id": "es", "name": "Alcohólicos Anónimos Ejemplo", "site": "https://es.example.org", "lang": "es", "in_area": True},
                {"id": "feedonly", "name": "Feed Only", "feed": "https://feed.example.org/wp-admin/admin-ajax.php", "in_area": True},
                {"id": "plain", "name": "Plain HTTP", "site": "http://plain.example.org", "in_area": True},
                {"id": "again", "name": "Big City again", "site": "https://big.example.org/meetings/", "in_area": True},
                {"id": "noname", "site": "https://district.example.org/", "in_area": True},
                {"id": "yes", "name": "Says yes", "site": "https://yes.example.org", "in_area": "yes"},
                None, "x",
            ]
            Offices.r = run_js(self, OFFICES_JS, data={"site": {"meetings": {"feeds": feeds}}})
        return Offices.r

    def test_our_areas_offices_by_their_own_sites_each_once(self):
        en = self.res()["en"]
        self.assertEqual([o["name"] for o in en], ["Big City Intergroup", "Alcohólicos Anónimos Ejemplo", "district.example.org"])
        self.assertEqual([o["host"] for o in en], ["big.example.org", "es.example.org", "district.example.org"])
        self.assertEqual([o["lang"] for o in en], ["en", "es", "en"])
        # never a feed address (it can hold an office's key), never a plain http:// one
        for o in en:
            self.assertTrue(o["url"].startswith("https://"), o)
            self.assertNotIn("wp-admin", o["url"])
            self.assertNotIn("key", o["url"])

    def test_spanish_speaking_office_first_on_a_spanish_page(self):
        r = self.res()
        self.assertEqual([o["name"] for o in r["es"]], ["Alcohólicos Anónimos Ejemplo", "Big City Intergroup", "district.example.org"])
        self.assertEqual(r["other"], r["en"])                     # any other language: the settings' order

    def test_nothing_to_list(self):
        self.assertEqual((self.res()["none"], self.res()["noFeeds"]), ([], []))

# --------------------------------------------------------------------------------------------- the settings
class Settings(unittest.TestCase):
    def test_the_card_reads_them_through_lang_link(self):
        ui = read("src", "_includes", "macros", "ui.njk")
        for k in CARD_LINKS:
            self.assertIn(f'site.links | langLink("{k}", L)', ui)


REAL_JS = r"""
out([filters.ncOffices(input, "en"), filters.ncOffices(input, "es")]);
"""


class RealSettings(unittest.TestCase):
    """The committee's config/site.yml as it is — left to the Code check (scripts/ops/gate_tests.py CONTENT_TESTS; it is
    read here only, so the tests of the code never depend on it)."""

    def setUp(self):
        self.cfg = yaml.safe_load(read("config", "site.yml"))

    def test_the_cards_links_are_aa_org_pages_with_their_spanish_pages(self):
        links = self.cfg["links"]
        for k in CARD_LINKS:
            with self.subTest(link=k):
                en, es = links[k], links[k + "_es"]
                self.assertEqual(urlparse(en).scheme, "https")
                self.assertEqual(urlparse(en).netloc, "www.aa.org")
                self.assertEqual(urlparse(es).netloc, "www.aa.org")
                self.assertEqual(urlparse(es).path, "/es" + urlparse(en).path)       # the same page, in Spanish
        self.assertEqual(links["aa_find"], "https://www.aa.org/find-aa")
        self.assertEqual(links["aa_is_aa_for_you"], "https://www.aa.org/self-assessment")
        self.assertEqual(links["aa_meeting_guide"], "https://www.aa.org/meeting-guide-app")

    def test_the_offices_of_our_area(self):
        en, es = run_js(self, REAL_JS, data=self.cfg)
        names_en = [o["name"] for o in en]
        self.assertEqual(es[0]["name"], "Alcohólicos Anónimos Dallas")
        self.assertEqual(es[0]["lang"], "es")
        self.assertEqual(sorted(names_en), sorted(o["name"] for o in es))
        in_area = [f["name"] for f in self.cfg["meetings"]["feeds"] if f.get("in_area") is True]
        self.assertEqual(names_en, in_area)                       # every office of our Area, in the settings' order
        for f in self.cfg["meetings"]["feeds"]:
            if not f.get("in_area"):
                self.assertNotIn(f["name"], names_en)              # nearby areas (Arkansas, Oklahoma City …) are not "ours"


# --------------------------------------------------------------------------------------------- the words
PHONE = re.compile(r"\d{3}\D{0,2}\d{3}\D?\d{4}|\b800\b|tel:")
NOT_OUR_WORDS = ("alcoholism", "addiction", "addict", "treatment", "disease", "rehab", "hotline", "helpline",
                 "diagnos", "therapy", "clinic", "detox", "patient", "recovery center",
                 "alcoholismo", "adicción", "adicto", "tratamiento", "enfermedad", "terapia", "clínica",
                 "línea de ayuda", "desintoxica", "paciente")


class Words(unittest.TestCase):
    def keys(self) -> dict[str, dict]:
        return {k: v for k, v in COMMON.items() if k.startswith("newcomer.")}

    def test_both_languages_written_for_each(self):
        keys = self.keys()
        self.assertGreaterEqual(len(keys), 10)
        for k, v in keys.items():
            with self.subTest(key=k):
                self.assertTrue(v["en"].strip() and v["es"].strip())
                self.assertNotEqual(v["en"], v["es"])
        self.assertEqual(keys["newcomer.title"], {"en": "New to AA?", "es": "¿Eres nuevo en AA?"})

    def test_no_phone_number_and_no_clinical_words(self):
        for k, v in self.keys().items():
            for lang in ("en", "es"):
                with self.subTest(key=k, lang=lang):
                    text = v[lang].lower()
                    self.assertIsNone(PHONE.search(text))
                    for w in NOT_OUR_WORDS:
                        self.assertNotIn(w, text)

    def test_the_meetings_note_names_what_the_page_lists(self):
        # The Meetings page lists the Grapevine meetings (AA groups that use Grapevine or La Viña), the weekly open
        # meetings of AA Grapevine and of La Viña (La Viña's first on /es/) and our committee's meeting: the note
        # under the card names both magazines — La Viña first in Spanish — and still says it is not every AA meeting.
        note = COMMON["newcomer.meetings_note"]
        for lang, only in (("en", "only"), ("es", "solo")):
            with self.subTest(lang=lang):
                self.assertIn("Grapevine", note[lang])
                self.assertIn("La Viña", note[lang])
                self.assertIn(only, note[lang])
        self.assertLess(note["es"].index("La Viña"), note["es"].index("Grapevine"))
        self.assertEqual(note["en"], "This page lists only Grapevine and La Viña meetings, and our committee's monthly "
                                     "meeting. For any AA meeting, start with these links.")
        self.assertEqual(note["es"], "Esta página muestra solo reuniones de La Viña y de Grapevine, y la reunión mensual "
                                     "de nuestro comité. Para cualquier reunión de AA, empieza con estos enlaces.")

    def test_the_meetings_page_is_found_by_a_newcomers_words(self):
        kw = LIBRARY["search.kw.meetings"]
        for w in ("new to aa", "newcomer", "help", "drinking", "meeting guide", "intergroup"):
            self.assertIn(w, kw["en"])
        for w in ("nuevo en aa", "recién llegado", "ayuda", "bebida", "meeting guide", "intergrupo"):
            self.assertIn(w, kw["es"])


# --------------------------------------------------------------------------------------------- the pages
# The build's settings for these tests (over the committee's file): offices and links of their own, so what is checked
# is the code, whatever the committee keeps in config/site.yml.
FEEDS = [
    {"id": "one", "name": "First Test Intergroup", "site": "https://www.one.example.org", "lang": "en", "in_area": True,
     "feed": "https://www.one.example.org/wp-admin/admin-ajax.php?action=meetings", "region_label": {"en": "One", "es": "Uno"}},
    {"id": "far", "name": "Far Test Office", "site": "https://far.example.org", "lang": "en", "in_area": False},
    {"id": "esp", "name": "Oficina Hispana de Prueba", "site": "https://hispana.example.org", "lang": "es", "in_area": True},
    {"id": "two", "name": "Second Test Office", "site": "https://two.example.org", "lang": "en", "in_area": True},
]
LINKS = {"aa_find": "https://www.aa.org/find-test", "aa_find_es": "https://www.aa.org/es/find-test",
         "aa_is_aa_for_you": "https://www.aa.org/questions-test", "aa_is_aa_for_you_es": "https://www.aa.org/es/questions-test",
         "aa_meeting_guide": "https://www.aa.org/app-test", "aa_meeting_guide_es": "https://www.aa.org/es/app-test"}
AREA = "https://area.example.org"
PAGES_JS = r"""
process.env.ONLY = "index.njk,meetings.njk,404";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-newcomer-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        site: (data) => ({ ...data.site, area_website: input.area, links: { ...data.site.links, ...input.links },
                           meetings: { ...(data.site.meetings || {}), feeds: input.feeds } }),
      });
    },
  });
  const pages = await elev.toJSON();
  const want = new Set(["/", "/es/", "/meetings/", "/es/meetings/", "/404.html", "/es/404.html"]);
  out(Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def section(page: str, sid: str) -> str:
    """The card <section id="…">…</section> (it holds no other section)."""
    i = page.index(f'<section id="{sid}"')
    return page[i:page.index("</section>", i) + len("</section>")]


def links(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.S):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))
        out.append({**attrs, "_text": m.group(2)})
    return out


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", " ", html, flags=re.S))).strip()


def chips(card: str) -> list[dict]:
    return [a for a in links(card) if "chip" in a.get("class", "").split()]


class Pages(unittest.TestCase):
    pages: dict | None = None

    def built(self) -> dict:
        if Pages.pages is None:
            Pages.pages = run_js(self, PAGES_JS, data={"feeds": FEEDS, "links": LINKS, "area": AREA}, timeout=600, now=NOW)
        return Pages.pages

    def test_the_card_opens_the_meetings_page_in_its_language(self):
        p = self.built()
        for url, lang in (("/meetings/", "en"), ("/es/meetings/", "es")):
            with self.subTest(url=url):
                page = p[url]
                card = section(page, "new-to-aa")
                self.assertIn(f'lang="{lang}" aria-labelledby="new-to-aa-h"', card)
                self.assertIn('<h2 id="new-to-aa-h" class="card-h">', card)
                self.assertIn(COMMON["newcomer.title"][lang], card)
                self.assertIn(COMMON["newcomer.meetings_note"][lang].replace("'", "&#39;"), card)
                # first, right under the committee sub-nav: before the committee's own meeting
                self.assertLess(page.index('id="new-to-aa"'), page.index('id="committee-meeting"'))
                self.assertGreater(page.index('id="new-to-aa"'), page.index("cm-subnav"))
                aa = [a["href"] for a in links(card) if "chip" not in a.get("class", "").split()]
                self.assertEqual(aa, [LINKS[k + ("_es" if lang == "es" else "")] for k in CARD_LINKS])

    def test_our_areas_offices_spanish_speaking_first_on_spanish_pages(self):
        p = self.built()
        self.assertEqual([a["href"] for a in chips(section(p["/meetings/"], "new-to-aa"))],
                         ["https://www.one.example.org", "https://hispana.example.org", "https://two.example.org", AREA])
        self.assertEqual([a["href"] for a in chips(section(p["/es/meetings/"], "new-to-aa"))],
                         ["https://hispana.example.org", "https://www.one.example.org", "https://two.example.org", AREA])
        # never a feed address; a nearby area's office is not "ours"
        for url in ("/meetings/", "/es/meetings/"):
            card = section(p[url], "new-to-aa")
            self.assertNotIn("wp-admin", card)
            self.assertNotIn("Far Test Office", card)
        # an office whose site is in the other language: said (EN / ES), its name read in that language
        es_on_en = next(a for a in chips(section(p["/meetings/"], "new-to-aa")) if a["href"] == "https://hispana.example.org")
        self.assertEqual(es_on_en.get("hreflang"), "es")
        self.assertIn('<span lang="es">Oficina Hispana de Prueba</span>', es_on_en["_text"])
        self.assertIn('<span class="badge-muted uppercase" aria-hidden="true">es</span>', es_on_en["_text"])
        self.assertIn(f'<span class="sr-only">, {COMMON["common.spanish"]["en"]}</span>', es_on_en["_text"])
        en_on_es = next(a for a in chips(section(p["/es/meetings/"], "new-to-aa")) if a["href"] == "https://two.example.org")
        self.assertEqual(en_on_es.get("hreflang"), "en")
        self.assertIn(f'<span class="sr-only">, {COMMON["common.english"]["es"]}</span>', en_on_es["_text"])
        same = next(a for a in chips(section(p["/es/meetings/"], "new-to-aa")) if a["href"] == "https://hispana.example.org")
        self.assertNotIn("hreflang", same)
        self.assertNotIn("badge-muted", same["_text"])
        # the Area's site, last
        self.assertEqual(chips(section(p["/es/meetings/"], "new-to-aa"))[-1]["href"], AREA)
        # read aloud reads them (data-tts-read: app.js GV.tts skips chips elsewhere — filters and jump links); the
        # browser hears it: tests/browser/test_r12_u4_aa_browser.py ReadAloudControls
        for url in ("/meetings/", "/es/meetings/"):
            card = section(p[url], "new-to-aa")
            self.assertEqual(card.count("data-tts-read"), 1)
            lst = card[card.index("data-tts-read"):]
            lst = lst[:lst.index("</ul>")]
            self.assertEqual(len(chips(lst)), 4)

    def test_it_links_only_to_aa_and_says_each_new_tab(self):
        p = self.built()
        cards = [(u, section(p[u], "new-to-aa")) for u in ("/meetings/", "/es/meetings/")]
        cards += [(u, section(p[u], f"new-to-aa-{lang}")) for u in ("/404.html", "/es/404.html") for lang in ("en", "es")]
        allowed = {"www.aa.org", "area.example.org"} | {urlparse(f["site"]).netloc for f in FEEDS if f["in_area"]}
        for url, card in cards:
            with self.subTest(url=url):
                self.assertNotIn("tel:", card)
                self.assertIsNone(PHONE.search(visible(card)))
                lang = "es" if 'lang="es" aria-labelledby' in card else "en"
                for a in links(card):
                    href = a["href"]
                    if href.startswith("http"):
                        self.assertIn(urlparse(href).netloc, allowed, href)
                        self.assertEqual((a.get("target"), a.get("rel")), ("_blank", "noopener"), href)
                        self.assertIn(f'<span class="sr-only"> ({COMMON["common.external"][lang]})</span>', a["_text"], href)
                    else:
                        self.assertRegex(href, r"^/(es/)?meetings/#new-to-aa$")

    def test_the_404_page_in_both_languages(self):
        p = self.built()
        for url, first, second in (("/404.html", "en", "es"), ("/es/404.html", "es", "en")):
            with self.subTest(url=url):
                page = p[url]
                a, b = page.index(f'id="new-to-aa-{first}"'), page.index(f'id="new-to-aa-{second}"')
                self.assertLess(a, b)                                   # the page's language first
                self.assertLess(b, page.index('id="nf-popular"'))       # before the popular pages
                for lang in (first, second):
                    card = section(page, f"new-to-aa-{lang}")
                    self.assertIn(f'lang="{lang}"', card)
                    self.assertIn(COMMON["newcomer.title"][lang], card)
                    self.assertEqual(chips(card), [])                   # compact: no office list
                    to_full = [x for x in links(card) if not x["href"].startswith("http")]
                    self.assertEqual(len(to_full), 1)
                    self.assertEqual(to_full[0]["href"], ("/es" if lang == "es" else "") + "/meetings/#new-to-aa")
                    self.assertEqual(to_full[0].get("hreflang"), None if lang == first else lang)
                    self.assertEqual([x["href"] for x in links(card) if x["href"].startswith("http")],
                                     [LINKS[k + ("_es" if lang == "es" else "")] for k in CARD_LINKS])

    def test_a_missing_spanish_address_shows_the_spanish_card_first(self):
        """Release check R12-404-ES-ORDER: GitHub Pages (and scripts/ops/serve_site.mjs) answer EVERY missing address
        with the root /404.html — a broken Spanish link (/es/…) too. There a tiny script right after the cards (so
        before the first paint) puts "¿Eres nuevo en AA?" first; elsewhere, on /es/404.html and without JavaScript
        the order stays as built. The site's base path is the build's (here "/"; "/aagrapevine/" on GitHub Pages)."""
        p = self.built()
        page = p["/404.html"]
        start = page.index('<div id="nf-newcomers"')
        m = re.match(r'(<div id="nf-newcomers".*?</div>)\s*<script>(.*?)</script>', page[start:], re.S)
        self.assertIsNotNone(m, "the script right after the cards")
        cards, script = m.group(1), m.group(2)
        self.assertNotIn("<script>(function (g, b)", p["/es/404.html"], "the Spanish page has its card first already")
        r = run_js(self, PAGE_JS + r"""
          const order = (path, base) => {
            const p = page({ url: "https://example.test" + path, html: input.cards, globals: { SITE: { lang: "en", base } } });
            vm.runInContext(input.script, p.win);
            return [...p.$("#nf-newcomers").children].map((c) => c.id + ":" + c.getAttribute("lang"));
          };
          out({ es: order("/es/una-pagina-que-no-existe/", "/"), en: order("/una-pagina/", "/"), file: order("/es/viejo.pdf", "/"),
                word: order("/escuela/", "/"), pages: order("/aagrapevine/es/una-pagina/", "/aagrapevine/"),
                other: order("/es/una-pagina/", "/aagrapevine/") });""", data={"cards": cards, "script": script}, needs_modules=False)
        es_first, en_first = ["new-to-aa-es:es", "new-to-aa-en:en"], ["new-to-aa-en:en", "new-to-aa-es:es"]
        self.assertEqual(r, {"es": es_first, "en": en_first, "file": es_first, "word": en_first, "pages": es_first, "other": en_first})

    def test_home_has_one_line_to_it_before_the_service_band(self):
        p = self.built()
        for url, lang in (("/", "en"), ("/es/", "es")):
            with self.subTest(url=url):
                page = p[url]
                target = ("/es" if lang == "es" else "") + "/meetings/#new-to-aa"
                self.assertEqual(page.count(f'href="{target}"'), 1)
                at = page.index(f'href="{target}"')
                self.assertLess(at, page.index('aria-labelledby="svc-title"'))
                line = page[page.rindex('<p class="panel-muted', 0, at):page.index("</p>", at)]
                self.assertIn(COMMON["newcomer.title"][lang], line)
                self.assertIn(COMMON["newcomer.line"][lang].replace("'", "&#39;"), line)
        self.assertEqual(read("src", "pages", "index.njk").count("ui.newcomerLine(L)"), 1)


if __name__ == "__main__":
    unittest.main()
