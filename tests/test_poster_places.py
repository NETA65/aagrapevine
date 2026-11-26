"""Round 33c · where the build puts the poster's blocks, from the words it prints (eleventy/filters/monthly.js
posterPlaces, posterBlocks; macros/monthly.njk poster()).

The bug (2026-11-17, the Code check's browser job — tests/browser/test_monthly_posters_browser.py UnfittedClipped): once La
Viña's monthly workshop moved to November 18, /es/monthly/2026-11/ had ten rows in its Dates block, and before the
page's fit (or without JavaScript) its last two — "Ofertas de regalo para las fiestas en las tiendas de La Viña y
Grapevine" and the price change — ran past the foot of the split layout's content column, under the story and the
issue. The month was already "dense", the densest there is: the density counts the dates, not their words, and the
Spanish words are longer. The English poster lost its Book of the Month at the same foot.

The fix: the build estimates every block's height from the words it prints in the page's language (each letter as
wide as Chrome draws the poster's two typefaces), and puts the blocks that may sit in either column where the dates
end inside their column and nothing else is cut — the template's own places whenever they hold everything. Checked
here with Node.js on hand-made month models (November 2026's own rows in both languages, a quiet month), so nothing
depends on today's data; tests/browser/test_poster_places_browser.py compares the estimate with the browser.

    python -m unittest tests.test_poster_places -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SITE = {"url": "https://neta65.github.io/aagrapevine", "committee": "NETA 65 Grapevine & La Viña Committee",
        "committee_es": "Comité de Grapevine y La Viña de NETA 65",
        "links": {"gv_email_editorial": "gveditorial@aagrapevine.org", "lv_email_editorial": "manuscritoslv@aagrapevine.org"}}


def row(kind: str, title: str, time: str = "", **kw) -> dict:
    es = "hora" in kw.get("zone", "")
    return {"kind": kind, "title": title, "range": "", "time": time, "zone": kw.pop("zone", "Central" if time else ""),
            "place": "", "online": False, "tentative": False, "platform": "", "speaker": None,
            # (the chip as monthModel makes it: its month, day and weekday — a chip is three lines tall)
            "chip": {"mon": "Nov", "day": "18", "wd": "Mié" if es else "Wed"}, "day": "", **kw}


# November 2026 as it is on the posters (its rows, its story, issue, Book of the Month and weekly meetings)
ROWS = {
    "en": [row("event", "La Viña Information Workshop (in Spanish) — Longview", "7–9 PM"),
           row("event", "Delegate — Conference Connect Town Hall", "7–8 PM", online=True),
           row("recurring", "GV/LV booth at CityWide Dallas", "5:30–7:30 PM"),
           row("recurring", "La Viña Monthly Virtual Workshop (in Spanish)", "2–3 PM", online=True),
           row("committee", "", "7–8 PM", platform="Google Meet"),
           row("event", "La Viña-Grapevine Workshop", place="Riverside, CA", online=True),
           row("event", "La Viña Writing Workshop (in Spanish) — Garland", "7–9 PM")],
    "es": [row("event", "Taller de Información de La Viña — Longview", "7–9 p. m.", zone="(hora del Centro)"),
           row("event", "Reunión Informativa de la Delegada — Conference Connect", "7–8 p. m.", zone="(hora del Centro)", online=True),
           row("recurring", "Mesa de GV/LV en CityWide Dallas", "5:30–7:30 p. m.", zone="(hora del Centro)"),
           row("recurring", "Taller Mensual y Virtual de La Viña", "2–3 p. m.", zone="(hora del Centro)", online=True),
           row("committee", "", "7–8 p. m.", zone="(hora del Centro)", platform="Google Meet"),
           row("event", "Taller de La Viña-Grapevine", place="Riverside, CA", online=True),
           row("event", "Taller de Escritura de La Viña — Garland", "7–9 p. m.", zone="(hora del Centro)")],
}
OFFERS = {
    "en": [{"key": "ship", "title": "Free shipping at the Grapevine and La Viña stores", "titleLang": "en", "starts": "2026-11-01",
            "ends": "2026-12-31", "icon": "truck"},
           {"key": "gifts", "title": "Holiday gift offers at the Grapevine and La Viña stores", "titleLang": "en", "starts": "2026-10-02",
            "ends": "2026-12-31", "showStarts": False, "icon": "gift"}],
    "es": [{"key": "ship", "title": "Envío gratis en las tiendas de La Viña y Grapevine", "titleLang": "es", "starts": "2026-11-01",
            "ends": "2026-12-31", "icon": "truck"},
           {"key": "gifts", "title": "Ofertas de regalo para las fiestas en las tiendas de La Viña y Grapevine", "titleLang": "es",
            "starts": "2026-10-02", "ends": "2026-12-31", "showStarts": False, "icon": "gift"}],
}


def model(lang: str, rows: list[dict], offers: list[dict], price: bool, density: str = "dense") -> dict:
    es = lang == "es"
    return {
        "key": "2026-11", "lang": lang, "layout": "split", "design": "harvest", "density": density, "isCurrent": False,
        "name": "Noviembre" if es else "November", "monthName": "noviembre" if es else "November", "year": "2026",
        "calendar": {"offset": 0, "days": 30, "marks": {}, "weekdays": list("DLMMJVS" if es else "SMTWTFS")},
        "absUrl": "https://neta65.github.io/aagrapevine" + ("/es" if es else "") + "/monthly/2026-11/",
        "dates": rows, "offers": offers, "price": {"kind": "before", "effective": "2027-01-01"} if price else None,
        "deadlines": [{"theme": "Edición anual sobre las prisiones" if es else "Annual Prison Issue", "themeEn": "Annual Prison Issue",
                       "machine": es, "hook": "" if es else "Did you find AA in prison?",
                       "issueLabel": "julio de 2027" if es else "July 2027", "dueLabel": "1 de diciembre" if es else "Dec 1"}],
        "lvDeadlines": [],
        "lvTopics": [{"es": "Mi primer trabajo sobrio"}, {"es": "Mi rutina sobria en las mañanas"}, {"es": "Mi servicio favorito"}],
        "gvTopics": [], "posterGvTopics": False,
        "tips": [{"title": "Arma una biblioteca de préstamo en tu grupo" if es else "Build a lending library at your group",
                  "text": "Historias atemporales del archivo — siempre valiosas en una biblioteca de préstamo." if es
                  else "Timeless stories from the archive — a perennial lending-library addition."}],
        "gv": {"theme": "Los miembros de AA y la salud mental" if es else "AA Members & Mental Health", "machine": es,
               "orig": "AA Members & Mental Health" if es else ""},
        "lv": {"label": "Noviembre–Diciembre 2026", "theme": "La alegría de vivir"},
        "botm": [{"title": "El lenguaje del corazón: los escritos de Bill W. para el Grapevine", "discount": 20, "endsLabel": "14 de diciembre" if es else "Dec 14"},
                 {"title": "Into Action: Stories from AA Grapevine", "discount": 20, "endsLabel": "14 de diciembre" if es else "Dec 14"}],
        "botmOffer": {"discount": 20, "endsLabel": "14 de diciembre" if es else "Dec 14"},
        "weekly": [{"title": "Reunión Abierta de La Viña" if es else "La Viña Open Meeting (in Spanish)", "new": True,
                    "when": "Los jueves a las 11:00 a. m. (hora del Centro)" if es else "Thursdays at 11:00 AM Central",
                    "startsLabel": "5 de noviembre" if es else "Nov 5"},
                   {"title": "Grapevine Weekly Open AA Meeting", "new": False,
                    "when": "Los miércoles a las 11:00 a. m. (hora del Centro)" if es else "Wednesdays at 11:00 AM Central", "startsLabel": ""}],
    }


JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const site = input.site, res = { places: {}, blocks: {}, lines: {}, start: M.POSTER_START_PX };
for (const [name, m] of Object.entries(input.models)) {
  res.places[name] = M.posterPlaces(m, site, t);
  const b = M.posterBlocks(m, site, t, res.places[name].T);
  res.blocks[name] = { dates590: b.dates(590), story590: b.story(590), story334: b.story(334), botm334: b.botm(334), T: res.places[name].T };
}
// the line breaks: after a hyphen (Chrome's "lending-" / "library"), a word longer than its line, no text
const x = { face: "sans", wt: 400, size: 1, lh: 1.3 };
const w = M.posterEm("aa lending-", x) * 20 + 1;
res.lines = { hyphen: M.posterLines("aa lending-library", w, x, 20), joined: M.posterLines("aa lendinglibrary", w, x, 20),
              one: M.posterLines("aa lending-", w, x, 20), none: M.posterLines("  ", w, x, 20),
              long: M.posterLines("manuscritoslv@aagrapevine.org", 100, x, 20) };
out(res);
"""


class PosterPlaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def result(self) -> dict:
        if PosterPlaces.r is None:
            busy = {lang: model(lang, ROWS[lang], OFFERS[lang], True) for lang in ("en", "es")}
            quiet = {lang: model(lang, ROWS[lang][:3], [], False, "snug") for lang in ("en", "es")}
            models = {"busy-en": busy["en"], "busy-es": busy["es"], "quiet-en": quiet["en"], "quiet-es": quiet["es"],
                      # the same busy month with one more Spanish row: taller than without it
                      "busier-es": {**busy["es"], "dates": ROWS["es"] + [ROWS["es"][0]]},
                      # another layout: the template's own arrangement, nothing estimated
                      "cork-es": {**busy["es"], "layout": "cork"}}
            PosterPlaces.r = run_js(self, JS, data={"models": models, "site": SITE})
        return PosterPlaces.r

    def test_lines_break_as_chrome_breaks_them(self):
        """A line breaks at a space or after a hyphen ("lending-" / "library", as on November's English poster); a word
        longer than its line takes the lines it needs (an e-mail address: overflow-wrap); no text, no line."""
        n = self.result()["lines"]
        self.assertEqual((n["one"], n["hyphen"], n["joined"], n["none"]), (1, 2, 3, 0))
        self.assertGreaterEqual(n["long"], 3)

    def test_the_spanish_story_makes_room_for_the_dates(self):
        """November 2026 in Spanish: ten rows (seven dates, two offers, the price change) under the story and the issue
        would run past the content column's foot (the Spanish poster starts at 18px with nine rows or more): the story
        goes up into the side column, under the calendar, and the dates end inside their column."""
        p = self.result()["places"]["busy-es"]
        self.assertEqual(p["T"], 18)
        self.assertEqual(p["at"], {"story": "side", "botm": "content", "weekly": "side"})
        self.assertEqual(p["move"], {"story": "side content", "botm": "content side", "weekly": "side content"})
        for col in ("side", "content"):
            self.assertLessEqual(p["cols"][col]["need"], p["cols"][col]["room"], col)
        self.assertLessEqual(p["cols"]["content"]["datesEnd"], p["cols"]["content"]["room"])

    def test_the_english_book_of_the_month_is_no_longer_cut(self):
        """The same month in English: its shorter words keep the dates whole under the story — the story stays — but the
        Book of the Month after them was cut at the column's foot: it goes up into the side column."""
        p = self.result()["places"]["busy-en"]
        self.assertEqual(p["T"], 21.5)
        self.assertEqual(p["at"], {"story": "content", "botm": "side", "weekly": "side"})
        self.assertEqual(p["move"]["botm"], "side content")
        for col in ("side", "content"):
            self.assertLessEqual(p["cols"][col]["need"], p["cols"][col]["room"], col)

    def test_a_month_that_fits_keeps_the_templates_places(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                p = self.result()["places"][f"quiet-{lang}"]
                self.assertEqual(p["at"], {"story": "content", "botm": "content", "weekly": "side"})
                self.assertEqual(p["move"], {"story": "content side", "botm": "content side", "weekly": "side content"})
                self.assertEqual(p["T"], 21 if lang == "es" else 23)

    def test_the_words_decide(self):
        """The estimate reads the words in the page's language: the Spanish dates (longer words, one title on two lines)
        are taller than the English ones at the same type; one more row makes them taller by a row at least; the story
        is taller in the narrow side column than in the content column."""
        b = self.result()["blocks"]
        self.assertGreater(b["busier-es"]["dates590"], b["busy-es"]["dates590"] + 13 + 2.81 * 18)
        self.assertGreater(b["busy-es"]["story334"], b["busy-es"]["story590"])
        self.assertGreater(b["busy-en"]["botm334"], 0)
        # at one type: the Spanish rows against the English ones
        r = run_js(self, r"""
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
out(Object.fromEntries(["en", "es"].map((l) => [l, M.posterBlocks(input[l], {}, t, 20).dates(590)])));
""", data={lang: model(lang, ROWS[lang], OFFERS[lang], True) for lang in ("en", "es")})
        self.assertGreater(r["es"], r["en"])

    def test_other_layouts_keep_the_templates_arrangement(self):
        p = self.result()["places"]["cork-es"]
        self.assertEqual((p["at"], p["move"], p["cols"]), ({}, {}, {}))

    def test_the_starting_type_mirrors_the_stylesheet(self):
        """The build estimates the poster at the type the stylesheet gives it before its fit (areas/monthly.css): the
        densities' and the Spanish poster's own (21px; 18px from the ninth row of its Dates block on)."""
        css = (ROOT / "src" / "assets" / "css" / "areas" / "monthly.css").read_text(encoding="utf-8")
        start = self.result()["start"]
        for d in ("roomy", "snug", "dense"):
            m = re.search(r"\.mp-poster\.mp-" + d + r" \{ font-size: ([\d.]+)px; \}", css)
            self.assertIsNotNone(m, d)
            self.assertEqual(float(m.group(1)), start[d], d)
        m = re.search(r'\[data-mp-poster\]:not\(\[data-mp-fit\]\)\[lang="es"\] \{ font-size: ([\d.]+)px; \}', css)
        self.assertEqual(float(m.group(1)), start["es"])
        m = re.search(r'\[data-mp-poster\]:not\(\[data-mp-fit\]\)\[lang="es"\]:has\(\.mp-dlist > li:nth-child\((\d+)\)\) \{ font-size: ([\d.]+)px; \}', css)
        self.assertEqual((int(m.group(1)), float(m.group(2))), (start["esBusyRows"], start["esBusy"]))

    def test_the_split_columns_mirror_the_stylesheet(self):
        """The columns the estimate fills are the split's as the stylesheet sizes them: the side 404px wide (padding 42px
        32px 32px 38px: 334 × 1276 inside), the content column the rest of the 1080 × 1350 poster (padding 42px 44px 32px
        42px: 590 × 1276), 22px and 20px between their blocks; the issue a card (20px 24px) there."""
        css = (ROOT / "src" / "assets" / "css" / "areas" / "monthly.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.mp-l-split \.mp-side \{ width: var\(--mp-split, 404px\); flex: none; display: flex; "
                              r"flex-direction: column; gap: 22px; padding: 42px 32px 32px 38px;")
        self.assertRegex(css, r"\.mp-l-split \.mp-content \{ flex: 1; min-width: 0; display: flex; flex-direction: column; "
                              r"gap: 20px; padding: 42px 44px 32px 42px; \}")
        self.assertRegex(css, r"\.mp-l-split \.mp-issue \{ padding: 20px 24px;")
        js = (ROOT / "eleventy" / "filters" / "monthly.js").read_text(encoding="utf-8")
        self.assertIn('side: { w: 334, h: 1276, gap: 22, blocks: ["head", "calendar", "foot"] }', js)
        self.assertIn('content: { w: 590, h: 1276, gap: 20, blocks: ["issue", "dates"], pad: { issue: [20, 24] } }', js)


# The split poster rendered by the build's own Eleventy and macros (no page of src/pages: ONLY), from the models above and
# this file's own site (never config/site.yml: a committee edit there changes no answer here)
RENDER_JS = r"""
process.env.ONLY = "-none-";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-poster-places-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js", config(cfg) {
    for (const [name, c] of Object.entries(input.cases)) {
      cfg.addTemplate(`mp-places-${name}.njk`, '{% import "macros/monthly.njk" as mp with context %}{{ mp.poster(m, lang, site, "t") }}',
                      { ...c, site: input.site, layout: false, permalink: `/mp-places-${name}/index.html`, eleventyExcludeFromCollections: true, sitemap: false });
    }
  } });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => /^\/mp-places-/.test(p.url || "")).map((p) => [p.url.slice(11, -1), p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class PosterPlacesRendered(unittest.TestCase):
    """macros/monthly.njk builds each of the split's movable blocks in the column posterPlaces chose, its data-mp-move
    naming that column first (the page's fit reads it as the build's own place), in the reading order of its column —
    and every date is on the poster wherever the blocks go."""

    def test_each_block_in_its_column(self):
        cases = {"busy-es": {"m": model("es", ROWS["es"], OFFERS["es"], True), "lang": "es"},
                 "busy-en": {"m": model("en", ROWS["en"], OFFERS["en"], True), "lang": "en"},
                 "quiet-es": {"m": model("es", ROWS["es"][:3], [], False, "snug"), "lang": "es"}}
        html = run_js(self, RENDER_JS, data={"cases": cases, "site": SITE}, timeout=300)
        self.assertEqual(sorted(html), sorted(cases))
        want = {"busy-es": {"side": ["mp-story", "mp-weekly"], "content": ["mp-dates", "mp-botm"]},
                "busy-en": {"side": ["mp-botm", "mp-weekly"], "content": ["mp-story", "mp-dates"]},
                "quiet-es": {"side": ["mp-weekly"], "content": ["mp-story", "mp-dates", "mp-botm"]}}
        for name, page in html.items():
            with self.subTest(poster=name):
                side = page[page.index('data-mp-slot="side"'):page.index('data-mp-slot="content"')]
                content = page[page.index('data-mp-slot="content"'):]
                for col, text in (("side", side), ("content", content)):
                    movers = re.findall(r'<section class="mp-b (mp-\w+)" data-mp-order="(\d+)"(?: data-mp-move="([^"]*)")?', text)
                    got = [cls for cls, _o, mv in movers if mv]
                    self.assertEqual([c for c in got if c != "mp-dates"], [c for c in want[name][col] if c != "mp-dates"], col)
                    for cls, _o, mv in movers:
                        if mv:
                            self.assertEqual(mv.split()[0], col, f"{cls}: the build's column first")
                    orders = [int(o) for _c, o, _m in movers]
                    self.assertEqual(orders, sorted(orders), f"{col}: the reading order")
                rows = re.findall(r'<li class="mp-date mp-date--(\w+)">', page)
                n = len(cases[name]["m"]["dates"]) + len(cases[name]["m"]["offers"]) + (1 if cases[name]["m"]["price"] else 0)
                self.assertEqual(len(rows), n, "every date, offer and price change on the poster")


if __name__ == "__main__":
    unittest.main()
