"""Site search and the Library's search (src/assets/js/search.js GV.searchKit, src/assets/js/library.js), run in
Node.js on a pretend page (tests/fakedom.py) with the vendored MiniSearch, on real entries of the site's search
indexes (tests/fixtures/search: titles only):

  * Spanish ñ  — "Año" finds the años (and "40 Años, 9 padrinos" first), never "Anonimato …" or "Alcohólicos
                 Anónimos"; a query typed without the tilde ("ano", "vina") still finds the ñ words; the
                 highlight marks the word found, ñ or not; "Did you mean …?" gives a ñ word once, with its ñ
  * the other language — AA's own words (search.js BILINGUAL): "sponsor" on the English page also finds "padrino",
                 "reuniones" finds "meeting", "big book" finds "Libro Grande"; those matches come after the ones on
                 the words typed (alt), in the Library too; a query with none of those words runs as before
  * older browsers — without \\p{…} in regular expressions the kit still normalizes, splits, highlights and finds
                 (each such expression is made inside try, with a plainer stand-in)
  * the Library — "Load more" moves keyboard focus to the first new card, on the last batch too (where the button
                 hides itself); a card's download address goes through kit.href (a javascript: one becomes "#"),
                 and the preview dialog shows a download link only for a web address or one of the site's own

Skipped without Node.js or without node_modules (the vendored MiniSearch comes from there: npm ci).

    python -m unittest tests.test_search_kit -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import ROOT, run_js  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "search"
MINISEARCH = "node_modules/minisearch/dist/umd/index.js"


def index(lang: str) -> list[dict]:
    return json.loads((FIX / f"index-{lang}.json").read_text(encoding="utf-8"))["items"]


# kit(lang) → { G (window.GV), K (GV.searchKit), ms (an index like the search page's: titles), find(q) → { titles,
# alt (titles found only through the other language), partial } }. oldRegex: a browser without \p{…} in regular
# expressions (new RegExp throws on one).
KIT_JS = PAGE_JS + r"""
function kit(lang, items, oldRegex) {
  const globals = { SITE: { lang, base: "/aagrapevine/" } };
  const p = page({ url: "https://example.test/aagrapevine/" + (lang === "es" ? "es/" : "") + "search/", globals,
                   scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js"] });
  // (the page's own RegExp: a vm context's built-ins are its own)
  if (oldRegex) vm.runInContext('RegExp = new Proxy(RegExp, { construct(t, a) { if (String(a[0]).indexOf(String.fromCharCode(92) + "p{") >= 0) throw new SyntaxError("Invalid escape"); return new t(...a); } });', p.win);
  vm.runInContext(fs.readFileSync("src/assets/js/search.js", "utf8"), p.win, { filename: "search.js" });
  const G = p.win.GV, K = G.searchKit;
  const ms = K.create(["t", "o"], { t: 3, o: 2 });
  ms.addAll(items.map((e, i) => ({ id: i, t: e.t, o: e.o || "" })));
  const find = (q) => {
    const r = K.search(ms, q);
    return { titles: r.hits.map((h) => items[h.id].t), alt: r.hits.filter((h) => h.alt).map((h) => items[h.id].t), partial: r.partial,
             terms: r.hits.map((h) => h.terms) };
  };
  return { G, K, ms, find, p };
}
"""


def need_minisearch(case: unittest.TestCase) -> None:
    if not (ROOT / MINISEARCH).is_file():
        case.skipTest("node_modules is not installed (npm ci): the vendored MiniSearch comes from there")


class SpanishEnye(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        need_minisearch(self)
        if SpanishEnye.r is None:
            SpanishEnye.r = run_js(self, KIT_JS + r"""
const es = kit("es", input.es), en = kit("en", input.en), old = kit("es", input.es, true);
const K = es.K;
out({
  ano: es.find("Año"), anoLower: es.find("año"), anos: es.find("años"), plain: es.find("ano"), vina: es.find("vina"),
  oldAno: old.find("Año"), oldNorm: old.K.norm("Ñandú Viña ÁÉÍÓÚ"),
  norm: [K.norm("Año"), K.norm("AÑO"), K.norm("anónimo"), K.norm("Viña"), K.norm("an\u0303o")],
  hl: [K.highlight("40 Años, 9 padrinos", ["años"]), K.highlight("Anonimato y medios", ["año"]), K.highlight("El mejor año", ["ano"]),
       K.highlight("Alcohólicos Anónimos", ["anonimos"]), old.K.highlight("El mejor año de mi vida", ["año"])],
  enAno: en.find("año"),
  suggest: [K.suggest(es.ms, "vinaa"), K.suggest(es.ms, "anoss")],
});
""", data={"es": index("es"), "en": index("en")}, needs_modules=False)
        self.r = SpanishEnye.r

    def test_ano_is_not_anonimo(self):
        # /es/search/?q=Año listed 181 results led by "Anónimo …" and "Anonimato …": ñ is a letter of its own
        for key in ("ano", "anoLower"):
            got = self.r[key]["titles"]
            self.assertTrue(got, key)
            self.assertTrue(all("año" in t.lower() for t in got), got)        # (a title with both words is fine)
            for only in ("Anonimato y medios de comunicación [Temporada 3, Episodio 16]", "Dios rompiendo su anonimato [Temporada 8, Episodio 25]",
                         "El Intergrupo en línea de Alcohólicos Anónimos [Temporada 7, Episodio 26]"):
                self.assertNotIn(only, got)
        self.assertIn("40 Años, 9 padrinos", self.r["ano"]["titles"])
        self.assertIn("12 años de vida", self.r["ano"]["titles"])
        self.assertIn("Marisol - El mejor año de mi vida", self.r["ano"]["titles"])
        self.assertTrue(all("año" in t.lower() for t in self.r["anos"]["titles"]))
        # the English page's index: its Spanish originals too
        self.assertIn("12 Years of Life", self.r["enAno"]["titles"])                   # (its original: "12 años de vida")
        self.assertNotIn("Anonymity and the Media [Season 3, Episode 16]", self.r["enAno"]["titles"])

    def test_a_query_without_the_tilde_still_finds_the_enye_words(self):
        plain = self.r["plain"]["titles"]
        self.assertIn("12 años de vida", plain)                          # "ano" may find "año" …
        self.assertIn("40 Años, 9 padrinos", plain)
        self.assertIn("Libros de La Viña", self.r["vina"]["titles"])      # … and "vina" "Viña"

    def test_normalizing_and_highlighting(self):
        self.assertEqual(self.r["norm"], ["año", "año", "anonimo", "viña", "año"])   # (a decomposed ñ too)
        hl = self.r["hl"]
        self.assertEqual(hl[0], "40 <mark>Años</mark>, 9 padrinos")
        self.assertEqual(hl[1], "Anonimato y medios")                                # "año" never marks "Anonimato"
        self.assertEqual(hl[2], "El mejor <mark>año</mark>")                         # the index's "ano" for "año"
        self.assertEqual(hl[3], "Alcohólicos <mark>Anónimos</mark>")

    def test_did_you_mean_gives_the_word_once_with_its_enye(self):
        # a ñ word is in the index under both spellings: "Did you mean …?" says it once, as it is written
        self.assertEqual(self.r["suggest"], ["viña", "años"])                       # (not "viña vina", "años anos")

    def test_older_browsers_without_unicode_classes(self):
        # P5-7: a browser without \p{…} in regular expressions — search.js still loads and searches
        self.assertEqual(self.r["oldNorm"], "ñandu viña aeiou")
        self.assertEqual(self.r["oldAno"]["titles"], self.r["ano"]["titles"])
        self.assertEqual(self.r["hl"][4], "El mejor <mark>año</mark> de mi vida")
        # … and none is written out as a regular expression (there, the whole file would not load): each one is a
        # string given to re(), which falls back to a plainer one
        for path in ("src/assets/js/search.js", "src/assets/js/library.js"):
            for n, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
                code = "" if line.lstrip().startswith(("/*", "*")) else line.split("//")[0]
                if "\\p{" in code:
                    self.assertIn('re("', code, f"{path}:{n}")


class OtherLanguage(unittest.TestCase):
    """F-6: AA's words in the other language, ranked after the words typed."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        need_minisearch(self)
        if OtherLanguage.r is None:
            OtherLanguage.r = run_js(self, KIT_JS + r"""
const en = kit("en", input.en), es = kit("es", input.es);
out({
  sponsor: en.find("sponsor"), padrino: en.find("padrino"), sobriedad: en.find("sobriedad"), sobriety: en.find("sobriety"),
  reuniones: en.find("reuniones"), bigBook: en.find("libro grande"), homeGroups: es.find("home groups"),
  steps: es.find("steps"), mixed: en.find("sponsor years"), none: en.find("anonymity media"),
  expand: [en.K.expand("home group"), en.K.expand("the big book"), en.K.expand("reuniones virtuales"), en.K.expand("Yukon"),
           en.K.expand("representante de la vina")],
});
""", data={"es": index("es"), "en": index("en")}, needs_modules=False)
        self.r = OtherLanguage.r

    def test_sponsor_finds_padrino_after_the_direct_matches(self):
        r = self.r["padrino"]
        direct = [t for t in r["titles"] if t not in r["alt"]]
        # the English titles whose Spanish original says "Padrino" match directly; "My Wild Card Sponsor" (English
        # only) through "padrino" ↔ "sponsor" — after them
        self.assertIn("What My Sponsor Taught Me (Something I'll Never Forget)", direct)
        self.assertIn("My Wild Card Sponsor", r["alt"])
        self.assertEqual(r["titles"], direct + r["alt"])
        self.assertLess(r["titles"].index("What My Sponsor Taught Me (Something I'll Never Forget)"), r["titles"].index("My Wild Card Sponsor"))

    def test_sobriedad_finds_sobriety(self):
        r = self.r["sobriedad"]
        self.assertIn("Relationships in Sobriety", r["titles"])            # its Spanish original: a direct match
        self.assertIn("Rain, Mud, Sobriety", r["alt"])                     # English only: through "sobriety"
        self.assertNotIn("Relationships in Sobriety", r["alt"])
        self.assertTrue(set(r["alt"]) <= set(self.r["sobriety"]["titles"]))

    def test_plurals_and_phrases(self):
        self.assertIn("A Very Real Virtual Meeting", self.r["reuniones"]["titles"])       # "reuniones" → "meeting"
        self.assertIn("Discussing The Language in the Big Book [Season 2, Episode 12]", self.r["bigBook"]["titles"])
        self.assertIn("186 Grupos base [Temporada 1, Episodio 3]", self.r["homeGroups"]["titles"])
        self.assertIn("Mi Primer Paso", self.r["steps"]["titles"])                         # "steps" → "paso"
        ex = self.r["expand"]
        self.assertEqual(ex[0]["groups"], [{"words": ["home", "group"], "alts": [["grupo", "base"]]}])
        self.assertEqual(ex[1]["groups"], [{"words": ["big", "book"], "alts": [["libro", "grande"]]}])   # ("the" is a stop word)
        self.assertEqual(ex[2]["groups"][0]["alts"], [["meeting"]])
        self.assertIsNone(ex[3])                                                           # no AA word: as before
        self.assertEqual(ex[4]["groups"][0]["alts"], [["gvr"], ["grapevine", "representative"]])   # "vina" for "viña"

    def test_every_word_still_counts(self):
        # "sponsor years": both words (or their other-language words) — "40 Years, 9 Sponsors" first
        self.assertEqual(self.r["mixed"]["titles"][0], "40 Years, 9 Sponsors")
        self.assertFalse(self.r["mixed"]["partial"])
        self.assertEqual(self.r["none"]["alt"], [])


# The round-7 review's examples (on the built index): the other language's words matched by prefix and fuzzy brought
# in unrelated titles — "prison" put "QR Post" and "Monthly toolkit" (through "cartel", for "cárcel") at the top of
# the search page's "Jump to a page"; "sponsor" found "Sober at 16" by its writer Marina (for "madrina").
EXACT_EN = [
    {"t": "Letters from Prison"}, {"t": "QR Post", "o": "Cartel QR"}, {"t": "Monthly toolkit", "o": "Kit del mes: cartel y carteles"},
    {"t": "Desde la cárcel"}, {"t": "Correccionales y prisiones"},
    {"t": "My Sponsor"}, {"t": "Sober at 16", "o": "Marina B."}, {"t": "Mi madrina"}, {"t": "Padrinos y ahijados"},
    {"t": "A Story of Hope"}, {"t": "GV Plays: History of GV"}, {"t": "The Historian"}, {"t": "Victoria's Journey"},
    {"t": "Historias de vida"}, {"t": "Mi testimonio"},
    {"t": "Convention Memories"}, {"t": "Convinced", "o": "Convencido"}, {"t": "Convención de Texas"},
    {"t": "Mujer y sobria"},
]
EXACT_ES = [
    {"t": "Mi historia"}, {"t": "Tienda", "o": "Store"}, {"t": "Stories of Recovery"}, {"t": "A Story to Tell"},
    {"t": "Mi primer paso"}, {"t": "Stephanie's Birthday"}, {"t": "Stephen at the Booth"}, {"t": "Steps to Freedom"},
    {"t": "Reuniones en el parque"}, {"t": "Meetings in the Park"}, {"t": "Meet the Editors"},
]
# Forms of a word on the dictionary's lines (no longer reached by prefix or near spelling): the other language's
# "sponsorship" / "sponsored" for "padrino", "relapsed" for "recaída", "spiritually", "recover"; "bebía" / "bebido"
FORMS_EN = [
    {"t": "Sponsorship in practice"}, {"t": "Sponsored at last"}, {"t": "Relapsed and back"}, {"t": "Spiritually fit"},
    {"t": "I recover daily"}, {"t": "Mi padrino"},
]
FORMS_ES = [{"t": "Bebía todos los días"}, {"t": "Nunca había bebido tanto"}, {"t": "Ya no bebo"}]


class OtherLanguageExact(unittest.TestCase):
    """F-6, round-7 review: the other language's words are looked for exactly (or in the plural) — never by prefix or
    as a near spelling; the words typed still are."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        need_minisearch(self)
        if OtherLanguageExact.r is None:
            OtherLanguageExact.r = run_js(self, KIT_JS + r"""
const en = kit("en", input.en), es = kit("es", input.es);
const q = {};
for (const w of ["prison", "sponsor", "story", "convention", "woman", "cárcel"]) q["en:" + w] = en.find(w);
for (const w of ["historia", "paso", "reunión", "meeting"]) q["es:" + w] = es.find(w);
const fen = kit("en", input.formsEn), fes = kit("es", input.formsEs);
for (const w of ["padrino", "recaída", "espiritualidad", "recuperación"]) q["forms:" + w] = fen.find(w);
q["forms:drinking"] = fes.find("drinking");
out(q);
""", data={"en": EXACT_EN, "es": EXACT_ES, "formsEn": FORMS_EN, "formsEs": FORMS_ES}, needs_modules=False)
        self.r = OtherLanguageExact.r

    def found(self, key: str) -> tuple[list, list]:
        r = self.r[key]
        return [t for t in r["titles"] if t not in r["alt"]], r["alt"]

    def test_no_near_spelling_or_longer_word_of_the_other_language(self):
        for key, never in (("en:prison", {"QR Post", "Monthly toolkit"}), ("en:sponsor", {"Sober at 16"}),
                           ("en:story", {"GV Plays: History of GV", "The Historian", "Victoria's Journey"}),
                           ("en:convention", {"Convinced"}), ("es:historia", {"Tienda"}),
                           ("es:paso", {"Stephanie's Birthday", "Stephen at the Booth"}), ("es:reunión", {"Meet the Editors"})):
            with self.subTest(query=key):
                self.assertFalse(never & set(self.r[key]["titles"]), self.r[key]["titles"])

    def test_the_other_languages_words_and_their_plurals_still_count_after_the_words_typed(self):
        for key, direct, alt in (("en:prison", ["Letters from Prison"], {"Desde la cárcel", "Correccionales y prisiones"}),
                                 ("en:sponsor", ["My Sponsor"], {"Mi madrina", "Padrinos y ahijados"}),
                                 ("en:story", ["A Story of Hope"], {"Historias de vida", "Mi testimonio"}),
                                 ("en:woman", [], {"Mujer y sobria"}),                          # (a form on the dictionary's line)
                                 ("es:historia", ["Mi historia"], {"Stories of Recovery", "A Story to Tell"}),   # -y → -ies
                                 ("es:paso", ["Mi primer paso"], {"Steps to Freedom"}),
                                 ("es:reunión", ["Reuniones en el parque"], {"Meetings in the Park"})):
            with self.subTest(query=key):
                got, other = self.found(key)
                self.assertEqual(got, direct)
                self.assertEqual(set(other), alt)
                self.assertEqual(self.r[key]["titles"], got + other)              # the words typed first
        # ("convention" typed: "convención" is a near spelling of the word typed itself — found as before)
        self.assertEqual(set(self.r["en:convention"]["titles"]), {"Convention Memories", "Convención de Texas"})

    def test_a_form_on_the_dictionarys_line_is_found(self):
        # the forms the exact matching no longer reaches by prefix or near spelling are words of their own on their line
        for key, direct, alt in (("forms:padrino", ["Mi padrino"], {"Sponsorship in practice", "Sponsored at last"}),
                                 ("forms:recaída", [], {"Relapsed and back"}),
                                 ("forms:espiritualidad", [], {"Spiritually fit"}),
                                 ("forms:recuperación", [], {"I recover daily"}),
                                 ("forms:drinking", [], {"Bebía todos los días", "Nunca había bebido tanto"})):
            with self.subTest(query=key):
                got, other = self.found(key)
                self.assertEqual(got, direct)
                self.assertEqual(set(other), alt)

    def test_the_words_typed_keep_prefix_and_fuzzy(self):
        # "cárcel" typed on the English page: its own word as before (light fuzzy finds "cartel", as it always has) —
        # the change is only on the dictionary's words
        self.assertIn("QR Post", self.found("en:cárcel")[0])
        self.assertIn("Desde la cárcel", self.found("en:cárcel")[0])
        self.assertIn("Meetings in the Park", self.found("es:meeting")[0])               # its own word, by prefix too


LIB_HTML = r"""
<template id="lib-icons"><svg data-icon="file-text"><path d="M0"/></svg><svg data-icon="eye"><path d="M1"/></svg></template>
<script type="application/json" id="lib-config">__CFG__</script>
<h2 id="lib-results-h">Documents</h2>
<form id="lib-form"><input id="lib-q" type="search"><button type="button" id="lib-clear" hidden>x</button><kbd id="lib-kbd">/</kbd></form>
<p id="lib-status"></p><div id="lib-active" hidden></div><p id="lib-partial" hidden></p><p id="lib-error" hidden><button id="lib-retry">Retry</button></p>
<select id="lib-sort"><option value="rel">Best match</option><option value="new">Newest</option></select>
<div id="lib-results"></div>
<div id="lib-empty" hidden><span data-empty-icon></span><p data-empty-title></p><p data-empty-text></p><div class="flex"></div></div>
<div id="lib-more-wrap" hidden><span id="lib-shown"></span><button type="button" id="lib-more">Load more</button></div>
<dialog id="lib-preview"><h2 id="lib-preview-title"></h2><iframe id="lib-preview-frame"></iframe>
  <a id="lib-preview-open" href="#">Open</a><a id="lib-preview-open-m" href="#">Open</a><a id="lib-preview-dl" href="#" hidden>Download</a>
  <button type="button" data-lib-close>Close</button></dialog>
"""

LIB_JS = PAGE_JS + r"""
const CFG = { s: { countShown: "{shown} of {n}" }, lang: "en", locale: "en-US", index: "/library-index.json", search: "/search/",
              pageSize: 12, cols: [], src: {}, srcLong: {}, langs: {}, langTitle: {}, catIcons: {}, ft: {} };
const fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: input.docs, refs: [], cats: {} }) });
const p = page({ html: input.html.replace("__CFG__", JSON.stringify(CFG)), url: "https://example.test/aagrapevine/library/",
                 globals: { SITE: { lang: "en", base: "/aagrapevine/" }, fetch },
                 scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js", "src/assets/js/search.js", "src/assets/js/library.js"] });
await p.ready();
await p.tick(10);
const R = {};
const cards = () => p.$$("#lib-results .lib-card");
const active = () => { const a = p.doc.activeElement; const c = a && a.closest ? a.closest(".lib-card") : null; return c ? cards().indexOf(c) : (a === p.doc.body ? "body" : a.id || a.tagName); };
R.first = cards().length;
const more = p.$("#lib-more");
more.focus();
p.click(more);
R.afterOne = { cards: cards().length, focus: active(), moreHidden: p.$("#lib-more-wrap").hidden };
p.$("#lib-more").focus();
p.click(more);                                                           // the last batch: "Load more" hides itself
R.afterLast = { cards: cards().length, focus: active(), moreHidden: p.$("#lib-more-wrap").hidden };

// a card's download address and the preview dialog
const btn = (id) => p.$("#doc-" + id + " [data-lib-preview]");
R.dl = { bad: btn("bad").getAttribute("data-dl"), site: btn("site").getAttribute("data-dl"), web: btn("web").getAttribute("data-dl") };
const dlg = p.$("#lib-preview"), dl = p.$("#lib-preview-dl");
const open = (id) => { p.click(btn(id)); const r = { open: dlg.open, hidden: dl.hidden, href: dl.getAttribute("href"), frame: p.$("#lib-preview-frame").getAttribute("src") }; dlg.close(); return r; };
R.preview = { bad: open("bad"), site: open("site"), web: open("web") };

// F-6 in the Library: "sponsor" — the documents that say it first, then the ones found through "padrino"
const q = p.$("#lib-q");
q.value = "sponsor";
p.fire(q, "input");
await p.tick(200);
R.sponsor = cards().map((c) => c.querySelector(".lib-title a").textContent);
R.errors = p.errors.map(String);
out(R);
"""


def lib_docs() -> list[dict]:
    docs = [{"id": f"d{i}", "t": f"Document {i}", "s": "gv", "c": "forms", "l": "en", "u": f"https://example.test/files/{i}.pdf",
             "d": f"2026-{1 + i % 9:02d}-01"} for i in range(26)]
    docs[0].update({"id": "bad", "pv": "https://drive.google.com/file/d/bad/preview", "dl": "javascript:alert(1)"})
    docs[1].update({"id": "site", "pv": "https://drive.google.com/file/d/site/preview", "dl": "/library/files/site.pdf"})
    docs[2].update({"id": "web", "pv": "https://drive.google.com/file/d/web/preview", "dl": "https://drive.google.com/uc?export=download&id=web"})
    docs[3].update({"t": "My Wild Card Sponsor"})
    docs[4].update({"t": "Lo que me enseñó mi padrino", "l": "es"})
    docs[5].update({"t": "The Sponsorship Pamphlet"})
    docs[6].update({"t": "Una madrina para todas", "l": "es"})
    return docs


class Library(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        need_minisearch(self)
        if Library.r is None:
            Library.r = run_js(self, LIB_JS, data={"html": LIB_HTML, "docs": lib_docs()}, needs_modules=False)
        self.r = Library.r

    def test_runs_cleanly(self):
        self.assertEqual(self.r["errors"], [])

    def test_load_more_moves_focus_to_the_first_new_card(self):
        # P4-8: 26 documents, 12 a page — the second "Load more" shows the last 2 and hides itself
        self.assertEqual(self.r["first"], 12)
        self.assertEqual(self.r["afterOne"], {"cards": 24, "focus": 12, "moreHidden": False})
        self.assertEqual(self.r["afterLast"], {"cards": 26, "focus": 24, "moreHidden": True})   # not <body>

    def test_download_addresses_go_through_the_url_guard(self):
        # P8-3: data-dl via kit.href — a javascript: address becomes "#", the site's own gets the base path
        self.assertEqual(self.r["dl"], {"bad": "#", "site": "/aagrapevine/library/files/site.pdf",
                                        "web": "https://drive.google.com/uc?export=download&id=web"})
        pv = self.r["preview"]
        self.assertTrue(pv["bad"]["open"])
        self.assertTrue(pv["bad"]["hidden"])                                   # no download link for it
        self.assertEqual(pv["site"]["href"], "/aagrapevine/library/files/site.pdf")
        self.assertFalse(pv["site"]["hidden"])
        self.assertEqual(pv["web"]["frame"], "https://drive.google.com/file/d/web/preview")

    def test_the_other_languages_words_come_last(self):
        # F-6: the English documents that say "sponsor" (and "sponsorship", by prefix) first, the Spanish ones found
        # through "padrino" / "madrina" after them
        got = self.r["sponsor"]
        self.assertEqual(set(got[:2]), {"My Wild Card Sponsor", "The Sponsorship Pamphlet"})
        self.assertEqual(set(got[2:]), {"Lo que me enseñó mi padrino", "Una madrina para todas"})


if __name__ == "__main__":
    unittest.main()
