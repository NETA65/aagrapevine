"""The Texas writers archive on /published/ (#archive) and /es/published/ — the page side (SPEC round 6, unit B):

  * View    — eleventy/filters/published.js pwArchive, run with Node.js on tests/fixtures/writers_archive/site_sample.json
              (synthetic stories in the shape of data/site/writers_archive.json): rows in decade groups (newest first,
              "Date not shown" last), the byline items as printed (one writer: name · place + county; a letters
              column: one item per writer; anonymous → "Anonymous" / "Anónimo"), the issue named by read.js issueName
              in each language, lang on text in the other language, the search words (writers, places, counties,
              titles in both languages, theme, year, decade, magazine — not the subtitle; apostrophes dropped,
              initials both together and one by one), counts[scope][magazine][decade], the Area 65 hometown chips,
              the first years, only the magazines' own links, a machine-translated subtitle marked only when its title
              has no mark (briefMachine, JSON "rm"); no file → an empty archive.
  * JSON    — src/pages/published-archive-json.11ty.js: the rest of Texas only, compact keys, text only; the page asks
              for it by its fingerprint (?v=, a new address whenever its rows change).
  * Page    — /published/ and /es/published/ built for real (Eleventy, ONLY=published,index,sw, PATH_PREFIX,
              I18N_STRICT=1) from the sample (WRITERS_ARCHIVE=…) and without any archive file: the section and its
              landmarks, the Area 65 rows (one link each, "(opens on …)"), decade headings and lists, the decade radios
              in a fieldset, the live result line, the no-JavaScript note, lang attributes, autoescaped text, a machine
              translation said in the title's link and its original always "Original title:", the note over the list,
              the script's settings, the hero / empty-state / "How" links, the two JSON files, the home page's line,
              the service worker's lists; without the file: no section, no errors.
  * Search  — eleventy/filters/library.js: the /published/ page entry carries the writers' hometowns (the towns geo
              knows, in its spelling; once each, as MiniSearch splits them) and the archive's keywords — no names, no
              initials, no bylines as printed.
  * Home    — eleventy/filters/home.js homeArchive: the same headline numbers as the page.
  * Styles  — published.css: the archive panel's one column never widens the page; the chosen chip in forced colours;
              44px buttons on phones.
  * Copy    — the new strings: no "PDF", no talk of how the site updates itself; button and chip budgets.
The two page scripts themselves run in tests/test_published_scripts.py.

Skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_published_archive -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "fixtures" / "writers_archive" / "site_sample.json"
MAGAZINE_URL = re.compile(r"^https://(?:www\.)?(?:aagrapevine|aalavina)\.org/\S*$")
JSON_KEYS = {"o", "u", "p", "t", "tl", "g", "gl", "m", "b", "w", "c", "i", "y", "d", "h", "hl", "r", "rl", "rm", "a", "x", "k", "s"}


def sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


VIEW_JS = r"""
const out_ = {};
for (const lang of ["en", "es"]) {
  const A = filters.pwArchive({ writers_archive: input.wa }, lang);
  out_[lang] = {
    total: A.total, area: A.area, since: A.since, counts: A.counts, top: A.top, page: A.page, version: A.version, mt: A.mt,
    decades: A.decades.map((d) => ({ key: d.key, label: d.label, n: d.n, all: d.all, over: d.over, rows: d.rows.map((r) => r.id) })),
    rows: A.areaRows.concat(A.restRows).sort((a, b) => a.o - b.o),
    rest: A.restRows.map((r) => r.id),
    json: A.json,
  };
}
out_.empty = filters.pwArchive({}, "en");
out_.emptyFile = filters.pwArchive({ writers_archive: { updated: null, items: [] } }, "es");
out_.totals = (await imp("eleventy/filters/published.js")).pwArchiveTotals({ writers_archive: input.wa });
out_.home = filters.homeArchive({ writers_archive: input.wa });
out_.homeEmpty = filters.homeArchive({});
out_.strings = filters.pwArcStrings("es");
out(out_);
"""


class View(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if View.r is None:
            View.r = run_js(self, VIEW_JS, data={"wa": sample()})
        self.r = View.r

    def row(self, lang, title):
        return next(r for r in self.r[lang]["rows"] if r["title"] == title or r["origTitle"] == title)

    def test_rows_and_the_magazines_links_only(self):
        en = self.r["en"]
        self.assertEqual((en["total"], en["area"], len(en["rest"])), (21, 13, 8))   # the evil.example item is left out
        self.assertTrue(all(MAGAZINE_URL.match(r["url"]) for r in en["rows"]))
        self.assertNotIn("Not a Magazine Page", [r["title"] for r in en["rows"]])
        self.assertEqual(self.r["en"]["page"], 40)

    def test_decades_newest_first_undated_last_and_the_order(self):
        en, es = self.r["en"], self.r["es"]
        self.assertEqual([d["key"] for d in en["decades"]], ["2020", "2010", "2000", "1990", "1980", "1950", "1940", "undated"])
        self.assertEqual([d["label"] for d in en["decades"]][:2] + [en["decades"][-1]["label"]], ["2020s", "2010s", "Date not shown"])
        self.assertEqual([d["label"] for d in es["decades"]][:2] + [es["decades"][-1]["label"]], ["Década de 2020", "Década de 2010", "Fecha no indicada"])
        # o = the place in the whole list, in decade order and newest issue first inside a decade
        rows = en["rows"]
        self.assertEqual([r["o"] for r in rows], list(range(len(rows))))
        decs = [r["dec"] for r in rows]
        rank = {"undated": -1}
        self.assertEqual(decs, sorted(decs, key=lambda d: -rank.get(d, int(d) if d != "undated" else -1)))
        keys = [r["issueKey"] for r in rows if r["dec"] == "2020"]
        self.assertEqual(keys, sorted(keys, reverse=True))
        # the 1950s hold no Area 65 story: the group exists (the rest of Texas fills it) with no rows of its own
        fifties = next(d for d in en["decades"] if d["key"] == "1950")
        self.assertEqual((fifties["n"], fifties["all"], fifties["rows"]), (0, 1, []))

    def test_byline_forms(self):
        porch = self.row("en", "The Porch Light")
        self.assertEqual((porch["by"], porch["county"], porch["multi"]), (["Ann T.", "Tyler, Texas"], "Smith County", False))
        self.assertEqual(self.row("es", "The Porch Light")["county"], "Condado de Smith")
        column = self.row("en", "Dear Grapevine")
        self.assertEqual((column["by"], column["county"], column["multi"]), (["Mike K. (Palestine)", "Jim O. (Texas)"], "", True))
        self.assertEqual(self.row("en", "Mi primer día")["by"][0], "Anonymous")
        self.assertEqual(self.row("es", "Mi primer día")["by"][0], "Anónimo")
        self.assertEqual(self.row("en", "Twelve Questions")["by"], ["Anonymous", "Amarillo, Texas"])
        # a place that is a county already says it: no second county
        back = self.row("en", "Back Roads")
        self.assertEqual((back["by"], back["county"]), (["Gus H.", "Smith County, Texas"], ""))
        self.assertEqual(self.row("es", "Back Roads")["by"], ["Gus H.", "Condado de Smith, Texas"])

    def test_issue_names_in_each_language(self):
        self.assertEqual(self.row("en", "The Porch Light")["issue"], "October 2026")
        self.assertEqual(self.row("es", "The Porch Light")["issue"], "Octubre de 2026")
        self.assertEqual(self.row("en", "Un camino nuevo")["issue"], "September–October 2026")
        self.assertEqual(self.row("es", "Un camino nuevo")["issue"], "Septiembre–Octubre 2026")
        undated = self.row("en", "A Letter Without a Date")
        self.assertEqual((undated["issue"], undated["year"], undated["dec"]), ("", None, "undated"))

    def test_languages_of_the_texts(self):
        # English page: a translated La Viña title, its original in Spanish; an untranslated one keeps lang="es"
        camino = self.row("en", "Un camino nuevo")
        self.assertEqual((camino["title"], camino["titleLang"], camino["origTitle"], camino["origLang"], camino["machine"]),
                         ("A New Road", "en", "Un camino nuevo", "es", True))
        self.assertEqual((camino["brief"], camino["briefLang"], camino["theme"], camino["themeLang"]),
                         ("Serving his group gave him a purpose", "en", "Servicio en AA", "es"))
        familia = self.row("en", "La familia")
        self.assertEqual((familia["titleLang"], familia["origTitle"], familia["themeLang"]), ("es", "", "es"))
        # Spanish page: Grapevine's untranslated title in English; a translation with its English original
        self.assertEqual(self.row("es", "Who We Are")["titleLang"], "en")
        porch = self.row("es", "The Porch Light")
        self.assertEqual((porch["title"], porch["titleLang"], porch["origLang"], porch["machine"], porch["briefLang"]),
                         ("La luz del porche", "es", "en", True, "es"))
        self.assertEqual(self.row("en", "The Porch Light")["titleLang"], "en")
        # the title carries the mark: its translated subtitle does not get a second one
        self.assertFalse(porch["briefMachine"])
        self.assertFalse(camino["briefMachine"])
        self.assertFalse(self.row("es", "Who We Are")["briefMachine"])               # not translated at all

    def test_search_words(self):
        words = lambda lang, title: self.row(lang, title)["search"].split(" ")  # noqa: E731
        porch = words("en", "The Porch Light")
        for w in ("ann", "t", "tyler", "texas", "smith", "county", "porch", "light", "luz", "porche", "gratitude", "2026", "2020s", "grapevine"):
            self.assertIn(w, porch)
        self.assertNotIn("neighbor", porch)                          # not the subtitle
        self.assertEqual(len(porch), len(set(porch)))                # each word once
        self.assertIn("condado", words("es", "The Porch Light"))     # the county as the page says it
        self.assertIn("beginners", words("en", "Beginner’s Meeting"))   # apostrophes dropped (not "beginner s")
        self.assertNotIn("s", words("en", "Beginner’s Meeting"))
        # initials together AND one by one: "C.D.A." / "H.T.B." find them, and so do "C D A" or "H.T.B" (a search
        # keeps initials together only when each letter has its period)
        self.assertTrue({"cda", "c", "d", "a"} <= set(words("en", "Beginner’s Meeting")))
        self.assertTrue({"htb", "h", "t", "b"} <= set(words("en", "Spring Cleaning")))
        self.assertTrue({"em", "e", "m"} <= set(words("en", "Our First Group")))     # "E. M."
        self.assertIn("anonymous", words("en", "Twelve Questions"))
        for w in ("la", "vina", "rosa", "garland", "dallas"):
            self.assertIn(w, words("en", "La familia"))
        column = words("en", "Dear Grapevine")
        self.assertTrue({"mike", "palestine", "anderson", "jim", "texas", "young", "sober"} <= set(column))

    def test_flags_and_the_exclusive_theme(self):
        quiet = self.row("en", "The Quiet Highway")
        self.assertEqual((quiet["exclusive"], quiet["theme"]), (True, ""))   # the flag says it; the words stay searchable
        self.assertIn("exclusives", quiet["search"].split(" "))
        self.assertTrue(self.row("en", "The Porch Light")["audio"])
        self.assertTrue(self.row("en", "Ham on Wry")["column"])

    def test_counts_for_the_chips(self):
        c = self.r["en"]["counts"]
        self.assertEqual((c["neta65"]["all"]["all"], c["texas"]["all"]["all"]), (13, 21))
        self.assertEqual((c["neta65"]["gv"]["all"], c["neta65"]["lv"]["all"]), (10, 3))
        self.assertEqual((c["texas"]["gv"]["all"], c["texas"]["lv"]["all"]), (16, 5))
        self.assertEqual((c["neta65"]["all"]["2020"], c["texas"]["all"]["2020"], c["texas"]["all"]["undated"]), (6, 9, 2))
        self.assertEqual(c["neta65"]["all"]["1950"], 0)
        for scope in ("neta65", "texas"):
            for pub in ("all", "gv", "lv"):
                decs = {k: v for k, v in c[scope][pub].items() if k != "all"}
                self.assertEqual(sum(decs.values()), c[scope][pub]["all"])

    def test_hometown_chips_and_first_years(self):
        top = self.r["en"]["top"]
        self.assertLessEqual(len(top), 8)
        self.assertEqual(top[0], {"label": "Dallas", "n": 3})          # Dallas, Garland and Irving: all in Dallas County
        self.assertIn({"label": "Tyler", "n": 2}, top)
        self.assertNotIn("Houston", [t["label"] for t in top])          # Area 65 hometowns only
        self.assertEqual(self.r["en"]["since"], {"gv": 1944, "lv": 1996, "all": 1944})

    def test_no_archive_file(self):
        for e in (self.r["empty"], self.r["emptyFile"]):
            self.assertEqual((e["total"], e["area"], e["areaRows"], e["restRows"], e["json"], e["top"], e["decades"]), (0, 0, [], [], [], [], []))
        self.assertEqual(self.r["homeEmpty"]["total"], 0)

    def test_home_and_page_agree(self):
        self.assertEqual(self.r["home"], {"total": 21, "area": 13, "since": 1944})
        self.assertEqual(self.r["totals"], self.r["home"])

    def test_script_strings(self):
        s = self.r["strings"]
        for k in ("archive.status.neta65.other", "archive.when.dec", "archive.loading", "archive.load_error", "opens_on",
                  "common.auto_translated", "show_more", "shown_of", "status.q", "archive.empty_text", "archive.empty_filters"):
            self.assertTrue(s.get(k) and not s[k].startswith("published."), k)
        self.assertEqual(s["archive.when.dec"], "de la década de {d}")

    def test_the_json_fingerprint_and_the_note(self):
        en, es = self.r["en"], self.r["es"]
        for lang in ("en", "es"):
            self.assertRegex(self.r[lang]["version"], r"^[0-9a-f]{10}$")
        self.assertNotEqual(en["version"], es["version"])                 # each language's file has its own
        self.assertTrue(en["mt"] and es["mt"])                            # the sample has machine-translated Area 65 titles


# Rows these tests add to the sample: a machine-translated subtitle under a title that is not translated (Grapevine,
# Area 65 and the rest of Texas), and under a title whose "translation" is the title itself (the glossary keeps "At
# Wit’s End" as it is); a writer printed as initials ("M.B.").
EXTRA_JS = r"""
const out_ = {};
for (const lang of ["en", "es"]) {
  const A = filters.pwArchive({ writers_archive: input.wa }, lang);
  out_[lang] = { rows: A.areaRows.concat(A.restRows), json: A.json, mt: A.mt };
}
out_.toks = Object.fromEntries(input.queries.map((q) => [q, pwNorm(q).split(" ").filter(Boolean)]));
out(out_);
"""


def extra_sample() -> dict:
    wa = sample()
    who = next(it for it in wa["items"] if it["title"] == "Who We Are")
    year = next(it for it in wa["items"] if it["title"] == "A New Year")

    def add(src: dict, slug: str, **fields) -> None:
        it = json.loads(json.dumps(src))
        it.update({"id": "wa:x-" + slug, "key": "https://www.aagrapevine.org/magazine/x/" + slug,
                   "url": "https://www.aagrapevine.org/magazine/x/" + slug})
        it.pop("i18n", None)
        it.pop("machine", None)
        it.update(fields)
        wa["items"].append(it)

    add(who, "realtime", title="Real-time Recovery", summary="Letters from readers",
        i18n={"summary": {"en": "Letters from readers", "es": "Cartas de los lectores"}}, machine=["es"])
    add(who, "witsend", title="At Wit’s End", summary="Humor from the readers",
        i18n={"title": {"en": "At Wit’s End", "es": "At Wit’s End"}, "summary": {"en": "Humor from the readers", "es": "Humor de los lectores"}},
        machine=["es"])
    add(year, "whammy", title="The Triple Whammy of Spirituality", summary="Step Seven",
        i18n={"summary": {"en": "Step Seven", "es": "Paso Siete"}}, machine=["es"])
    add(who, "serenity", title="The Serenity Prayer: An Interpretation",
        writers=[dict(who["writers"][0], name="M.B.")])
    return wa


class MachineSubtitleAndInitials(unittest.TestCase):
    QUERIES = ["M.B", "M B", "M.B.", "MB", "H.T.B.", "h.t.b", "C.D.A", "C D A"]

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if MachineSubtitleAndInitials.r is None:
            MachineSubtitleAndInitials.r = run_js(self, 'const { pwNorm } = await imp("eleventy/filters/published.js");\n' + EXTRA_JS,
                                                  data={"wa": extra_sample(), "queries": self.QUERIES})
        self.r = MachineSubtitleAndInitials.r

    def row(self, lang, title):
        return next(r for r in self.r[lang]["rows"] if r["origTitle"] == title or r["title"] == title)

    def test_a_translated_subtitle_under_an_untranslated_title_is_marked(self):
        for title in ("Real-time Recovery", "At Wit’s End", "The Triple Whammy of Spirituality"):
            with self.subTest(title=title):
                es = self.row("es", title)
                self.assertEqual((es["title"], es["machine"], es["origTitle"]), (title, False, ""))
                self.assertTrue(es["briefMachine"])
                self.assertEqual(es["briefLang"], "es")
                self.assertFalse(self.row("en", title)["briefMachine"])            # English page: the magazine's own words
        jes = {x["t"]: x for x in self.r["es"]["json"]}
        self.assertEqual((jes["The Triple Whammy of Spirituality"].get("rm"), jes["The Triple Whammy of Spirituality"]["r"]), (1, "Paso Siete"))
        self.assertNotIn("m", jes["The Triple Whammy of Spirituality"])
        self.assertTrue(all("rm" not in x for x in self.r["en"]["json"]))
        self.assertTrue(all(not (x.get("m") and x.get("rm")) for x in self.r["es"]["json"]))   # one mark per row

    def test_initials_typed_any_way_find_the_writer(self):
        def found(q):
            toks = self.r["toks"][q]
            hits = []
            for r in self.r["en"]["rows"]:
                s = " " + r["search"] + " "
                if all((" " + t + " " if re.fullmatch(r"\d{4}", t) else " " + t) in s for t in toks):
                    hits.append(r["title"])
            return hits
        serenity = "The Serenity Prayer: An Interpretation"
        for q in ("M.B", "M B", "M.B.", "MB"):
            self.assertIn(serenity, found(q), q)
        self.assertEqual(found("M.B."), [serenity])                       # with every period: precise
        self.assertEqual(found("H.T.B."), ["Spring Cleaning"])
        self.assertEqual(found("h.t.b"), ["Spring Cleaning"])
        for q in ("C.D.A", "C D A"):
            self.assertIn("Beginner’s Meeting", found(q), q)


JSON_JS = r"""
const Mod = await imp("src/pages/published-archive-json.11ty.js");
const t = new Mod.default();
t.pwArchive = filters.pwArchive;
const d = t.data();
out({
  permalinks: ["en", "es"].map((lang) => d.permalink({ lang })),
  excluded: d.eleventyExcludeFromCollections, pagination: d.pagination,
  en: t.render({ lang: "en", db: { writers_archive: input.wa } }),
  es: t.render({ lang: "es", db: { writers_archive: input.wa } }),
  none: t.render({ lang: "en", db: {} }),
});
"""


class Json(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Json.r is None:
            Json.r = run_js(self, JSON_JS, data={"wa": sample()})
        self.r = Json.r

    def test_addresses(self):
        self.assertEqual(self.r["permalinks"], ["/published/texas-archive.json", "/es/published/texas-archive.json"])
        self.assertTrue(self.r["excluded"])
        self.assertEqual(self.r["pagination"]["data"], "languages")

    def test_the_rest_of_texas_in_compact_keys(self):
        wa = sample()
        area = {it["url"] for it in wa["items"] if it["scope"] == "neta65"}
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                j = json.loads(self.r[lang])
                self.assertEqual((j["v"], j["lang"], j["count"], len(j["items"])), (1, lang, 8, 8))
                self.assertEqual([x["o"] for x in j["items"]], sorted(x["o"] for x in j["items"]))
                for x in j["items"]:
                    self.assertLessEqual(set(x), JSON_KEYS)
                    self.assertTrue(MAGAZINE_URL.match(x["u"]))
                    self.assertNotIn(x["u"], area)                         # Area 65 stories are in the page itself
                    self.assertIn(x["p"], ("gv", "lv"))
                    self.assertTrue(x["d"] == "undated" or re.fullmatch(r"\d{4}", x["d"]))
                    self.assertIsInstance(x["b"], list)
                    for v in x.values():                                  # text only: nothing that looks like markup
                        self.assertNotRegex(json.dumps(v, ensure_ascii=False), r"<[a-zA-Z/]")
        en = {x["t"]: x for x in json.loads(self.r["en"])["items"]}
        border = en["On the Border"]
        self.assertEqual((border["g"], border["gl"], border["m"]), ("En la frontera", "es", 1))
        self.assertNotIn("tl", border)                                    # translated: in the page's language
        self.assertEqual(en["Mi primer día"]["b"], ["Anonymous", "San Antonio, Texas"])
        self.assertEqual(en["Mi primer día"]["tl"], "es")
        self.assertEqual(en["Beginner’s Meeting"]["d"], "undated")
        self.assertNotIn("y", en["Beginner’s Meeting"])
        self.assertEqual(en["The Quiet Highway"]["x"], 1)
        self.assertNotIn("h", en["The Quiet Highway"])
        self.assertEqual(en["Island Time"]["a"], 1)
        es = {x["t"]: x for x in json.loads(self.r["es"])["items"]}
        self.assertEqual(es["Gulf Breeze"]["tl"], "en")                 # an English title on the Spanish page
        self.assertEqual(es["Gulf Breeze"]["c"], "Condado de Jefferson")

    def test_no_archive(self):
        self.assertEqual(json.loads(self.r["none"]), {"v": 1, "lang": "en", "count": 0, "items": []})


SW_JS = r"""
const SW = await imp("src/pages/sw.11ty.js");
const cfg = (code) => JSON.parse(code.slice(code.indexOf("{"), code.indexOf("};") + 1));
const build = (urls) => cfg(SW.render({ build: { version: "t" }, orientation: { lessons: [] }, collections: { all: urls.map((url) => ({ url })) } }));
const withPage = build(["/", "/published/", "/es/published/"]);
const without = build(["/"]);
out({ withPage: { save: withPage.save, files: withPage.files }, without: { save: without.save, files: without.files } });
"""


class Worker(unittest.TestCase):
    def test_save_key_pages_keeps_published_writers_and_the_archive(self):
        r = run_js(self, SW_JS, needs_modules=False, env={"PATH_PREFIX": "/aagrapevine/"})
        self.assertIn("published/", r["withPage"]["save"])
        self.assertEqual(r["withPage"]["files"], ["published/texas-archive.json", "es/published/texas-archive.json"])
        # the JSON only with the page (a build of a few pages — ONLY=… — has neither)
        self.assertEqual(r["without"]["files"], [])
        self.assertEqual(len(r["withPage"]["save"]), len(set(r["withPage"]["save"])))


SEARCH_JS = r"""
const { searchIndex } = await imp("eleventy/filters/library.js");
const { translateKey } = await imp("eleventy.config.js");
const helpers = { translateKey, pickLang: (it, f, lang) => (it && it.i18n && it.i18n[f] && it.i18n[f][lang]) || (it && it[f]) || "" };
const nav = { primary: [{ key: "nav.published", url: "/published/", page: "published" }], footer: [] };
const page = (db) => searchIndex(db, nav, "en", helpers, {}).find((e) => e.id === "page:published");
// the terms MiniSearch makes of the entry's words (search.js: split on spaces and punctuation, accents and case dropped)
const terms = (e) => [...new Set(String(e.x || "").split(/[\n\r\p{Z}\p{P}]+/u).map((t) => t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase()).filter(Boolean))];
const withArc = page({ writers_archive: input.wa, spotlight: input.spot }), without = page({ spotlight: input.spot });
out({ with: withArc, without, terms: terms(withArc), termsWithout: terms(without) });
"""


def search_sample() -> tuple[dict, dict]:
    """The sample archive plus bylines that are not a person, places printed with a typo, a place geo does not know,
    and initials; recent stories (spotlight) by writers printed as initials and by name."""
    wa = sample()
    who = next(it for it in wa["items"] if it["title"] == "Who We Are")

    def add(slug: str, name: str, place: str, geo: dict) -> None:
        it = json.loads(json.dumps(who))
        it.update({"id": "wa:s-" + slug, "key": "https://www.aagrapevine.org/magazine/s/" + slug,
                   "url": "https://www.aagrapevine.org/magazine/s/" + slug, "title": "Story " + slug,
                   "writers": [{"name": name, "anonymous": False, "place": place, "geo": geo}]})
        wa["items"].append(it)

    def geo(city, county, counties, scope="texas"):
        label = f"{city}, Texas" if city else "Texas"
        return {"scope": scope, "city": city, "county": county, "counties": counties, "state": "TX", "label_en": label, "label_es": label}

    add("delegate", "Panel 31 delegate", "Forth Worth, Texas", geo("Fort Worth", "Tarrant", ["Tarrant", "Denton"]))
    add("newsletter", "Central Office newsletter, Sun-Dry", "El Paso, Texas", geo("El Paso", "El Paso", ["El Paso"]))
    add("initials", "W.M.", "Grand Prarie, Texas", geo("Grand Prairie", "Dallas", ["Dallas", "Ellis", "Tarrant"]))
    add("group", "Ana P.", "Grupo Paz y Sobriedad, Texas", geo("Grupo Paz y Sobriedad", None, []))
    add("theme", "The Theme", "Texas", geo(None, None, []))

    def story(n, author, city, county, scope):
        return {"id": f"s{n}", "kind": "article", "url": f"https://www.aagrapevine.org/story/{n}", "title": f"Story {n}",
                "extra": {"author": author, "geo": geo(city, county, [county], scope)}}
    spot = {"items": [story(1, "J. D. O.", "Lufkin", "Angelina", "neta65"), story(2, "Bill W.", "Austin", "Travis", "texas"),
                      story(3, "Dr. B.", "Boston", "Suffolk", "other")]}
    return wa, spot


class SearchWords(unittest.TestCase):
    def test_the_published_page_is_found_by_the_writers_hometowns(self):
        wa, spot = search_sample()
        r = run_js(self, SEARCH_JS, data={"wa": wa, "spot": spot})
        x = r["with"]["x"]
        words = x.split(" ")
        for w in ("Tyler", "Smith", "Longview", "Gregg", "Pearland", "Brazoria", "Palestine", "Anderson", "Galveston",
                  "Fort", "Worth", "Tarrant", "Grand", "Prairie", "Lufkin", "Angelina", "Austin", "Travis"):
            self.assertIn(w, words)
        self.assertEqual(len([w for w in words if w.casefold() == "tyler"]), 1)       # each word once
        # no names, no initials, no bylines as printed, no printed typos, no place geo does not know, nothing outside Texas
        for w in ("Ann", "Pat", "Mike", "Bill", "Anónimo", "Anonymous", "Panel", "delegate", "Central", "Office", "newsletter",
                  "Sun", "Dry", "Theme", "Forth", "Prarie", "Grupo", "Sobriedad", "Boston", "Suffolk", "Dr"):
            self.assertNotIn(w, words)
        terms = r["terms"]
        self.assertEqual([t for t in terms if len(t) < 2], [])                          # "W.M." / "J. D. O." / "Bill W." give no letters
        for t in ("delegate", "newsletter", "forth", "prarie", "grupo", "theme", "dr"):
            self.assertNotIn(t, terms)
        # the archive's keywords come with the archive; without it, the recent stories' hometowns only
        for t in ("archive", "archivo"):
            self.assertIn(t, terms)
            self.assertNotIn(t, r["termsWithout"])
        self.assertIn("lufkin", r["termsWithout"])
        self.assertNotIn("longview", r["termsWithout"])
        self.assertEqual([t for t in r["termsWithout"] if len(t) < 2], [])
        self.assertLess(len(x) - len(r["without"]["x"]), 600)                          # words, not stories


# ---------------------------------------------------------------------------------------------------------------
#  The page, built for real
# ---------------------------------------------------------------------------------------------------------------
class PageBuild(unittest.TestCase):
    @classmethod
    def build(cls, out: Path, archive: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "WRITERS_ARCHIVE": str(archive), "PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1",
               "ONLY": "published,index,sw", "NODE_NO_WARNINGS": "1"}
        return subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                               "--output", str(out)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                              timeout=600)

    @classmethod
    def setUpClass(cls):
        cls.tmp = None
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="published-archive-"))
        cls.runs = {"sample": cls.build(cls.tmp / "sample", SAMPLE), "none": cls.build(cls.tmp / "none", cls.tmp / "no-such-file.json")}
        cls.raw, cls.pages = {}, {}
        for kind in cls.runs:
            for lang in ("en", "es"):
                for page in ("published", "home"):
                    f = cls.tmp / kind / ("es" if lang == "es" else "") / ("published" if page == "published" else "") / "index.html"
                    cls.raw[(kind, lang, page)] = f.read_text(encoding="utf-8") if f.exists() else ""
                    cls.pages[(kind, lang, page)] = BeautifulSoup(cls.raw[(kind, lang, page)], "lxml")

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, True)

    def setUp(self):
        if not node_path():
            self.skipTest("Node.js is not installed")
        if not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            self.skipTest("the site's npm packages are not installed (npm ci)")
        for kind, r in self.runs.items():
            self.assertEqual(r.returncode, 0, f"{kind}: {r.stderr[-3000:]}")

    def page(self, lang="en", kind="sample", page="published"):
        return self.pages[(kind, lang, page)]

    def test_the_section_and_its_heading(self):
        for lang, title, eyebrow in (("en", "Texas writers through the years", "Archive · since 1944"),
                                     ("es", "Escritores de Texas a lo largo de los años", "Archivo · desde 1944")):
            with self.subTest(lang=lang):
                p = self.page(lang)
                sec = p.select_one("section#archive")
                self.assertIsNotNone(sec)
                self.assertEqual(sec["aria-labelledby"], "pw-arc-title")
                h2 = sec.select_one("h2#pw-arc-title")
                self.assertEqual(h2.get_text(strip=True), title)
                self.assertIn(eyebrow, sec.get_text(" ", strip=True))
                self.assertIn({"en": "21 stories, 13 of them by writers from our Area", "es": "21 historias, 13 de ellas"}[lang],
                              sec.get_text(" ", strip=True))
                # below the recent stories, above "How we find these writers"
                ids = [s.get("id") for s in p.select("main section[id], section[id]")]
                self.assertLess(ids.index("archive"), ids.index("pw-how"))

    def test_area_65_rows(self):
        p = self.page("en")
        rows = p.select("#pw-arc-list li.pw-arc-row")
        self.assertEqual(len(rows), 13)
        for li in rows:
            self.assertEqual(li["data-scope"], "neta65")
            for a in ("data-pub", "data-dec", "data-y", "data-o", "data-s"):
                self.assertTrue(li.has_attr(a), a)
            links = li.select("a")
            self.assertEqual(len(links), 1)                                  # one link per row
            a = links[0]
            self.assertTrue(MAGAZINE_URL.match(a["href"]))
            self.assertEqual((a["target"], a["rel"]), ("_blank", ["noopener"]))
            self.assertRegex(a.select(".sr-only")[-1].get_text(), r"\(opens on (aagrapevine|aalavina)\.org\)")
            self.assertIn("Writer", li.select_one(".pw-arc-by .sr-only").get_text())
        # the order of the page = data-o, decade groups newest first
        self.assertEqual([int(li["data-o"]) for li in rows], sorted(int(li["data-o"]) for li in rows))
        # Spanish: the sr-only texts in Spanish
        es = self.page("es").select("#pw-arc-list li.pw-arc-row")
        self.assertEqual(len(es), 13)
        self.assertIn("(se abre en", es[0].select("a .sr-only")[-1].get_text())

    def test_decade_groups_and_lists(self):
        p = self.page("en")
        groups = p.select("#pw-arc-list .pw-arc-dec")
        self.assertEqual([g["data-dec"] for g in groups], ["2020", "2010", "2000", "1990", "1980", "1950", "1940", "undated"])
        for g in groups:
            h3 = g.select_one("h3")
            ol = g.select_one("ol")
            self.assertEqual((ol["role"], ol["aria-labelledby"]), ("list", h3["id"]))
        fifties = next(g for g in groups if g["data-dec"] == "1950")
        self.assertTrue(fifties.has_attr("hidden"))                        # no Area 65 story: hidden until the JSON comes
        self.assertEqual(groups[0].select_one("h3").get_text(" ", strip=True), "2020s 6 stories")
        self.assertEqual(groups[-1].select_one("h3").get_text(" ", strip=True), "Date not shown 1 story")

    def test_controls_status_and_no_javascript(self):
        p = self.page("en")
        fs = p.select_one("#pw-arc fieldset")
        self.assertEqual(fs.select_one("legend").get_text(strip=True), "Decade")
        radios = fs.select("input[type=radio][name=pw-dec]")
        self.assertEqual([r["value"] for r in radios], ["all", "2020", "2010", "2000", "1990", "1980", "1950", "1940", "undated"])
        self.assertTrue(all(r.has_attr("disabled") and r.has_attr("data-arc-ctl") for r in radios))   # published-archive.js switches them on
        self.assertTrue(radios[0].has_attr("checked"))
        self.assertEqual(radios[0].find_parent("label").get_text(" ", strip=True), "All years 13")
        status = p.select_one("#pw-arc-status")
        self.assertEqual((status["role"], status["aria-live"]), ("status", "polite"))
        self.assertEqual(status.get_text(strip=True), "13 stories by Area 65 writers since 1944")
        raw = self.raw[("sample", "en", "published")]
        self.assertIn("Turn on JavaScript to search the archive and to see all 21 stories by Texas writers.", raw)
        self.assertIn("Activa JavaScript para buscar en el archivo y ver las 21 historias de escritores de Texas.",
                      self.raw[("sample", "es", "published")])
        places = p.select("[data-arc-place]")
        self.assertEqual(places[0]["data-arc-place"], "Dallas")
        self.assertTrue(places[0].find_parent(attrs={"data-js-only": True}))   # chips need the script
        self.assertTrue(p.select_one("#pw-arc-more").has_attr("hidden"))

    def test_lang_attributes_and_escaping(self):
        en = self.page("en")
        familia = next(li for li in en.select("li.pw-arc-row") if "La familia" in li.get_text())
        self.assertEqual(familia.select_one("a span[lang]")["lang"], "es")
        self.assertEqual(familia.select_one(".pw-arc-theme")["lang"], "es")
        camino = next(li for li in en.select("li.pw-arc-row") if "A New Road" in li.get_text())
        self.assertIsNone(camino.select_one("a span[lang]"))               # translated: in the page's language
        self.assertEqual(camino.select_one(".pw-arc-orig span[lang]")["lang"], "es")
        # a machine translation: the title says so in its link; its original is always "Original title:"
        self.assertEqual([x.get_text() for x in camino.select("a .sr-only")], [" (Auto-translated)", " (opens on aalavina.org)"])
        self.assertEqual(camino.select_one(".pw-arc-orig").get_text(), "Original title: Un camino nuevo")
        self.assertIsNotNone(camino.select_one(".pw-arc-orig svg[aria-hidden=true]"))   # the languages icon, decorative
        self.assertTrue(camino.has_attr("data-mt"))
        self.assertEqual(en.select("#archive [title]"), [])                 # no tooltip under the row's link
        porch = next(li for li in self.page("es").select("li.pw-arc-row") if "La luz del porche" in li.get_text())
        self.assertIn(" (Traducción automática)", porch.select_one("a").get_text())
        self.assertEqual(porch.select_one(".pw-arc-orig").get_text(), "Título original: The Porch Light")
        self.assertIsNone(porch.select_one(".pw-arc-brief svg"))           # the title has the mark: the subtitle no second one
        familia = next(li for li in en.select("li.pw-arc-row") if "La familia" in li.get_text())
        self.assertFalse(familia.has_attr("data-mt"))
        es = self.page("es")
        who = next(li for li in es.select("li.pw-arc-row") if "Who We Are" in li.get_text())
        self.assertEqual(who.select_one("a span[lang]")["lang"], "en")
        self.assertEqual(who.select_one(".pw-arc-brief")["lang"], "en")
        # text from the data is escaped (autoescape): the title shows its tags as text
        rose = next(li for li in en.select("li.pw-arc-row") if "Rose" in li.get_text())
        self.assertIsNone(rose.select_one("b"))
        self.assertIsNone(rose.select_one("i"))
        self.assertIn("Faith & Hope’s <b>Rose</b> Garden", rose.select_one("a").get_text())
        self.assertIn("&lt;b&gt;Rose&lt;/b&gt;", self.raw[("sample", "en", "published")])

    def test_the_machine_translation_note(self):
        for lang, text in (("en", "Titles translated automatically from Spanish — originals in italics"),
                           ("es", "Títulos traducidos automáticamente del inglés — originales en cursiva")):
            with self.subTest(lang=lang):
                note = self.page(lang).select_one("#archive #pw-arc-mt")
                self.assertFalse(note.has_attr("hidden"))                      # the sample's Area 65 rows include one
                self.assertEqual(note.get_text(" ", strip=True), text)
                self.assertIsNotNone(note.find_next_sibling(id="pw-arc-list"))   # over the list

    def test_the_empty_state_hooks(self):
        empty = self.page("en").select_one("#pw-arc-empty")
        help_line = empty.select_one("[data-arc-empty-text]")
        self.assertTrue(help_line.has_attr("hidden"))                          # the script fills it for the cause
        self.assertEqual(help_line.get_text(strip=True), "")
        buttons = {b.get_text(strip=True): b for b in empty.select("button")}
        self.assertEqual(list(buttons), ["Clear search", "Show all years", "Show both magazines", "Show all of Texas"])
        self.assertTrue(all(b.has_attr("hidden") for b in buttons.values()))
        self.assertTrue(buttons["Show both magazines"].has_attr("data-arc-allpub"))
        self.assertEqual(self.page("es").select_one("[data-arc-allpub]").get_text(strip=True), "Ver ambas revistas")

    def test_the_scripts_settings(self):
        for lang, url in (("en", "/published/texas-archive.json"), ("es", "/es/published/texas-archive.json")):
            with self.subTest(lang=lang):
                p = self.page(lang)
                cfg = json.loads(p.select_one("script#pw-arc-config").string)
                # the JSON by its fingerprint: a new address whenever its rows change (never an older file's rows)
                self.assertRegex(cfg["json"], "^" + re.escape(url) + r"\?v=[0-9a-f]{10}$")
                self.assertEqual((cfg["lang"], cfg["rest"], cfg["page"]), (lang, 8, 40))
                self.assertEqual(cfg["since"], {"gv": 1944, "lv": 1996, "all": 1944})
                self.assertEqual(cfg["counts"]["texas"]["all"]["all"], 21)
                self.assertTrue(all(v and not v.startswith("published.") for v in cfg["s"].values()))
                scripts = [s["src"] for s in p.select("script[src]")]
                pw = next(i for i, s in enumerate(scripts) if "/assets/js/published.js" in s)
                arc = next(i for i, s in enumerate(scripts) if "/assets/js/published-archive.js" in s)
                self.assertLess(pw, arc)

    def test_ways_to_the_archive(self):
        p = self.page("en")
        hero = [a for a in p.select(".hero-actions a")]
        self.assertEqual([a["href"] for a in hero], ["/aagrapevine/contribute/", "#archive", "#pw-how"])
        self.assertEqual(hero[1].get_text(strip=True), "Texas writers since 1944")
        self.assertIn("max-md:hidden", hero[2]["class"])                   # phones: two buttons
        self.assertEqual(self.page("es").select(".hero-actions a")[1].get_text(strip=True), "Autores de Texas desde 1944")
        self.assertTrue(p.select_one('#pw-empty a[href="#archive"]'))
        how = p.select_one("#pw-how").get_text(" ", strip=True)
        self.assertIn("Grapevine (back to 1944) and La Viña (back to 1996)", how)
        self.assertIn("Newest stories: the 60- and 90-day windows", how)

    def test_the_json_files(self):
        for lang in ("en", "es"):
            f = self.tmp / "sample" / ("es" if lang == "es" else "") / "published" / "texas-archive.json"
            j = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual((j["lang"], j["count"]), (lang, 8))
        none = json.loads((self.tmp / "none" / "published" / "texas-archive.json").read_text(encoding="utf-8"))
        self.assertEqual(none["count"], 0)

    def test_the_home_page_line(self):
        for lang, text, link in (("en", "21 stories by Texas writers since 1944 — 13 from our Area", "/aagrapevine/published/#archive"),
                                 ("es", "21 historias de escritores de Texas desde 1944; 13 de nuestra Área", "/aagrapevine/es/published/#archive")):
            with self.subTest(lang=lang):
                home = self.page(lang, page="home")
                sec = home.select_one("#published-writers")
                self.assertIn(text, sec.get_text(" ", strip=True))
                self.assertTrue(sec.select_one(f'a[href="{link}"]'))
        none = self.page("en", "none", "home").select_one("#published-writers")
        self.assertIsNone(none.select_one('a[href$="#archive"]'))

    def test_the_worker_keeps_published_writers(self):
        sw = (self.tmp / "sample" / "sw.js").read_text(encoding="utf-8")
        config = json.loads(re.search(r"const CONFIG = (\{.*?\n\});", sw, re.S).group(1))
        self.assertIn("published/", config["save"])
        self.assertEqual(config["files"], ["published/texas-archive.json", "es/published/texas-archive.json"])

    def test_without_an_archive_file(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                p = self.page(lang, "none")
                self.assertIsNotNone(p.select_one("#pw-form"))               # the page itself is there
                self.assertIsNone(p.select_one("#archive"))
                self.assertIsNone(p.select_one("#pw-arc-config"))
                self.assertIsNone(p.select_one('a[href="#archive"]'))
                self.assertEqual(len(p.select(".hero-actions a")), 2)
                self.assertIn("max-sm:hidden", p.select(".hero-actions a")[1]["class"])


# ---------------------------------------------------------------------------------------------------------------
#  The browser side (the behaviour itself is checked in a browser: QA scripts outside the repo)
# ---------------------------------------------------------------------------------------------------------------
def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def norm_fn(src: str) -> str:
    """The normalization of a page script: its NON_WORD and INITIALS patterns and its norm() body."""
    start = src.index("  var NON_WORD")
    return src[start:src.index("  }\n", src.index("  function norm(s)", start)) + 4]


def function_body(src: str, name: str) -> str:
    """The text of `function <name>(…)` up to the next function of the script."""
    start = src.index(f"function {name}(")
    nxt = src.find("\n  function ", start + 1)
    return src[start:nxt if nxt > 0 else len(src)]


# Source checks only where behaviour cannot be run cheaply; what the scripts DO (the search, the address, the download,
# the focus, the empty state) runs in tests/test_published_scripts.py.
class Script(unittest.TestCase):
    def setUp(self):
        self.arc = read("src", "assets", "js", "published-archive.js")
        self.pw = read("src", "assets", "js", "published.js")
        self.view = read("eleventy", "filters", "published.js")

    def test_rows_from_the_json_are_built_as_text(self):
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(bad, self.arc)
        self.assertIn("textContent", self.arc)
        # the same link rule as the view model
        js = re.search(r"var SAFE_URL = (/.*?/);", self.arc).group(1)
        node = re.search(r"const ARC_URL = (/.*?/);", self.view).group(1)
        self.assertEqual(js, node)
        self.assertRegex(function_body(self.arc, "buildRow"), r"if \(!SAFE_URL\.test\(\w+\)\) return null;")

    def test_one_search_rule_on_the_page(self):
        # the cards (published.js) and the archive (published-archive.js) normalize a search the same way (the view
        # model's pwNorm agrees with both: tests/test_published_scripts.py runs all three)
        self.assertEqual(norm_fn(self.arc), norm_fn(self.pw))

    def test_the_two_scripts_talk(self):
        self.assertRegex(self.pw, r'dispatchEvent\(\s*new CustomEvent\(\s*"pw:state"')
        self.assertRegex(self.pw, r'dispatchEvent\(\s*new CustomEvent\(\s*"pw:reset"')
        self.assertRegex(self.pw, r"window\.GVPW\s*=")
        self.assertRegex(self.arc, r'document\.addEventListener\(\s*"pw:state"')
        self.assertRegex(self.arc, r'document\.addEventListener\(\s*"pw:reset"')
        # each script's writeUrl starts from the address as it is (keeps the other's keys) and keeps the #hash
        for src in (self.pw, self.arc):
            body = function_body(src, "writeUrl")
            self.assertRegex(body, r"new URLSearchParams\(\s*location\.search\s*\)")
            self.assertIn("location.hash", body)
        self.assertRegex(function_body(self.arc, "writeUrl"), r'\.set\(\s*"dec"')

    def test_a_download_that_can_fail(self):
        load = function_body(self.arc, "load")
        self.assertIn("AbortController", load)
        self.assertRegex(load, r"GV\.url\(\s*C\.json\s*\)")


class Styles(unittest.TestCase):
    def setUp(self):
        self.css = read("src", "assets", "css", "areas", "published.css")

    def rule(self, selector: str) -> str:
        m = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(m, selector)
        return m.group(1)

    def test_the_archive_panel_never_widens_the_page(self):
        # a grid item's minimum is its content (8 hometown chips in one line, 1,100px+): without minmax(0, …) the
        # chip rows widened the whole page on phones instead of scrolling inside the card
        self.assertRegex(self.rule(".pw-arc-panel"), r"grid-template-columns:\s*minmax\(0,\s*1fr\)")

    def test_the_chosen_chip_in_forced_colours(self):
        m = re.search(r"@media \(forced-colors: active\) \{(.*?)\n\}", self.css, re.S)
        self.assertIsNotNone(m)
        self.assertRegex(m.group(1), r"\.pw-chip:has\(> input:checked\) \{[^}]*outline: 3px solid Highlight")
        # after the focus rule (same specificity): a chosen chip with focus keeps the Highlight colour
        self.assertGreater(m.start(), self.css.index(".pw-chip:has(> input:focus-visible)"))

    def test_buttons_are_44px_on_phones_and_touch_screens(self):
        self.assertRegex(self.css, r"@media \(width < 40rem\), \(pointer: coarse\) \{ \.pw-reset \{ min-height: 2\.75rem; \} \}")


# ---------------------------------------------------------------------------------------------------------------
#  The new strings
# ---------------------------------------------------------------------------------------------------------------
def strings() -> dict:
    out = {}
    for f in ("published.json", "home.json", "pwa.json", "community.json"):
        out.update(json.loads((ROOT / "src" / "_i18n" / f).read_text(encoding="utf-8")))
    return out


NEW_KEYS = ("published.meta_desc", "published.cta_archive", "published.btn.archive", "published.how.window", "published.how.archive",
            "home.spot_archive", "home.spot_archive_link", "pwa.offline.how2_t", "community.status.src.writers_archive")


class Copy(unittest.TestCase):
    def setUp(self):
        self.s = strings()
        self.keys = [k for k in self.s if k.startswith("published.archive.")] + list(NEW_KEYS)

    def test_every_key_in_both_languages(self):
        self.assertGreater(len(self.keys), 30)
        for k in self.keys:
            with self.subTest(key=k):
                self.assertTrue(self.s[k]["en"].strip() and self.s[k]["es"].strip())

    def test_wording_rules(self):
        # documents are never "PDF"s; the site never says how it updates itself; the archive is the magazines' ONLINE one
        banned = re.compile(r"\bPDF\b|\bcrawl|\brobot|\bbot\b|automatic|autom[aá]tic|GitHub|every (day|night|morning)|"
                            r"cada (d[ií]a|noche|mañana)|\bCSV\b|spreadsheet", re.I)
        for k in self.keys:
            for lang in ("en", "es"):
                with self.subTest(key=k, lang=lang):
                    self.assertIsNone(banned.search(self.s[k][lang]), self.s[k][lang])
        for lang, word in (("en", "online archives"), ("es", "archivos en línea")):
            self.assertIn(word, self.s["published.archive.sub"][lang])

    def test_length_budgets(self):
        # design spec 1.18: buttons 24 / 28, chips 16 / 20 characters (the hero button with its year in it)
        btn = {k: self.s[k] for k in ("published.cta_archive", "published.btn.archive", "published.archive.btn_all_dec",
                                       "published.archive.btn_all_pub", "home.spot_archive_link")}
        for k, v in btn.items():
            with self.subTest(key=k):
                self.assertLessEqual(len(v["en"].replace("{since}", "1944")), 24)
                self.assertLessEqual(len(v["es"].replace("{since}", "1944")), 28)
        for k in ("published.archive.dec_all", "published.archive.undated", "published.archive.decade"):
            with self.subTest(key=k):
                self.assertLessEqual(len(self.s[k]["en"].replace("{d}", "1990")), 16)
                self.assertLessEqual(len(self.s[k]["es"].replace("{d}", "1990")), 20)


if __name__ == "__main__":
    unittest.main()
