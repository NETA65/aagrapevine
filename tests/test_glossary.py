"""The service words — GVR, RLV, NETA 65, Area 65, DCM, GSR, ACM, Assembly, Delegate, Panel — explained where they first
appear (eleventy/filters/glossary.js, src/_i18n/glossary.json, app.js GV.glossary, main.css .gl-*):

  * Words    — every entry has its word, what it stands for and one plain sentence, in English and in Spanish (the
               Spanish written for Spanish: "MCD", "RSG", "Asamblea" — not the English copied).
  * Gloss    — the `gloss` filter marks the FIRST appearance of each word in a string (a plural too), as written, with
               <abbr class="gl-term" data-gl title="Name: meaning">; the rest of the string escaped; a word inside a
               definition is never marked again; gloss(lang, keys) marks only those; Spanish finds the Spanish words.
  * Pages    — the hero lines of Home (Area 65), the GVR / RLV corner (GVR, RLV) and the Meetings page's "Who can come"
               (GVRs, RLVs, DCMs) use it; the corner lists every entry (#glossary, in its page nav).
  * Browser  — app.js turns each mark into a disclosure: a button named by the word (aria-expanded, aria-controls) and
               a note right after it, hidden until a tap or Enter; one open at a time; Escape closes it and puts the
               focus back on the word; a tap elsewhere closes it, and so does a new window width (a new height alone
               — a phone's address bar hiding as the page scrolls — leaves it open); a mark inside a link stays a
               plain <abbr>.

    python -m unittest tests.test_glossary -v        (or: python -m unittest discover -s tests)
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
KEYS = ["gvr", "rlv", "neta", "area65", "dcm", "gsr", "acm", "assembly", "delegate", "panel"]


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class Words(unittest.TestCase):
    def test_every_entry_in_both_languages(self):
        g = json.loads(read("src", "_i18n", "glossary.json"))
        for k in KEYS:
            for part in ("term", "name", "def"):
                with self.subTest(key=k, part=part):
                    v = g[f"glossary.{part}.{k}"]
                    self.assertTrue(v["en"].strip() and v["es"].strip())
            with self.subTest(key=k):
                self.assertNotEqual(g[f"glossary.def.{k}"]["en"], g[f"glossary.def.{k}"]["es"], "the Spanish is written, not copied")
        self.assertEqual(g["glossary.term.dcm"]["es"], "MCD")
        self.assertEqual(g["glossary.term.gsr"]["es"], "RSG")
        # a definition is one sentence, without its word's name (the title gives "Name: meaning")
        for k in KEYS:
            for lang in ("en", "es"):
                self.assertTrue(g[f"glossary.def.{k}"][lang].endswith("."), (k, lang))

    def test_the_filter_lists_them_in_order(self):
        r = run_js(self, 'out({ en: filters.glossary("en").map((e) => e.key), es: filters.glossary("es").map((e) => [e.key, e.term]) })')
        self.assertEqual(r["en"], KEYS)
        self.assertEqual(dict(r["es"])["dcm"], "MCD")


GLOSS_JS = r"""
out({
  gvr: filters.gloss("Everything a GVR or RLV needs to bring the meeting in print to the home group.", "en"),
  plural: filters.gloss("GVRs, RLVs, DCMs and anyone curious will find a place here — GVRs again.", "en"),
  some: filters.gloss("GVRs, RLVs, DCMs and anyone curious", "en", ["dcm"]),
  es: filters.gloss("Los RSG, los MCD y los RLV van a la Asamblea del Área 65.", "es"),
  esc: filters.gloss('A <b>GVR</b> & "friends"', "en"),
  none: filters.gloss("Six short sessions for new representatives.", "en"),
  area: filters.gloss("Service tools for Area 65 groups — NETA 65.", "en"),
  panel: filters.gloss("Our Delegate for Panel 75 reports to the assembly.", "en"),
});
"""


class Gloss(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Gloss.r is None:
            Gloss.r = run_js(self, GLOSS_JS)
        self.r = Gloss.r

    def marks(self, html: str) -> list[tuple[str, str]]:
        return re.findall(r'<abbr class="gl-term" data-gl title="([^"]*)">([^<]*)</abbr>', html)

    def test_the_first_appearance_of_each_word(self):
        m = self.marks(self.r["gvr"])
        self.assertEqual([w for _, w in m], ["GVR", "RLV"])
        self.assertTrue(m[0][0].startswith("Grapevine Representative: the member who brings AA Grapevine"))
        self.assertTrue(self.r["gvr"].endswith("to the home group."))
        plural = self.marks(self.r["plural"])
        self.assertEqual([w for _, w in plural], ["GVRs", "RLVs", "DCMs"])
        self.assertIn("— GVRs again.", self.r["plural"], "the second GVRs is plain text")
        self.assertEqual([w for _, w in self.marks(self.r["some"])], ["DCMs"])

    def test_spanish_words(self):
        # in the order they come in the sentence
        self.assertEqual([w for _, w in self.marks(self.r["es"])], ["RSG", "MCD", "RLV", "Asamblea", "Área 65"])
        self.assertTrue(any(t.startswith("Miembro del Comité de Distrito: ") for t, w in self.marks(self.r["es"]) if w == "MCD"))

    def test_escaped_and_never_nested(self):
        self.assertTrue(self.r["esc"].startswith("A &lt;b&gt;<abbr"), self.r["esc"])
        self.assertIn("&amp; &quot;friends&quot;", self.r["esc"])
        self.assertEqual(self.r["none"], "Six short sessions for new representatives.")
        # "Area 65" and "NETA 65": each once; the assembly's definition names GSRs and DCMs — never marked in a title
        self.assertEqual([w for _, w in self.marks(self.r["area"])], ["Area 65", "NETA 65"])
        panel = self.marks(self.r["panel"])
        self.assertEqual([w for _, w in panel], ["Delegate", "Panel 75", "assembly"])
        self.assertNotIn("<abbr", "".join(t for t, _ in panel))


class Pages(unittest.TestCase):
    def test_the_key_pages_use_it(self):
        self.assertIn('("home.hero_lead" | t(L)) | gloss(L)', read("src", "pages", "index.njk"))
        gvr = read("src", "pages", "gvr.njk")
        self.assertIn('("read.gvr.subtitle" | t(lang)) | gloss(lang)', gvr)
        self.assertIn('{ href: "#glossary", label: "glossary.eyebrow" | t(lang), icon: "book-a" }', gvr)
        self.assertIn("{%- for g in lang | glossary %}", gvr)
        self.assertIn('{{ "committee.meeting.who_text" | t(lang) | gloss(lang) | safe }}', read("src", "pages", "meetings.njk"))
        self.assertIn("| gloss(lang)", read("src", "pages", "orientation.njk"))
        # the hero's subtitle is written as HTML (pageHero: subtitle | safe), so the marks are tags, not text
        self.assertIn('<p class="gv-hero-sub">{{ subtitle | safe }}</p>', read("src", "_includes", "macros", "ui.njk"))

    def test_its_look(self):
        css = read("src", "assets", "css", "main.css")
        for rule in ("abbr.gl-term { text-decoration: underline dotted;", ".gl-btn { display: inline;", ".gl-pop {\n    position: fixed;"):
            self.assertIn(rule, css)


BROWSER_JS = r"""
const p = page({ html:
  '<p id="lead">Everything a <abbr class="gl-term" data-gl title="Grapevine Representative: the member who …">GVR</abbr> or ' +
  '<abbr class="gl-term" data-gl title="Representante de La Viña: the member who …">RLV</abbr> needs.</p>' +
  '<a id="link" href="/gvr/"><abbr class="gl-term" data-gl title="In a link">DCM</abbr></a><button id="other">Other</button>',
  scripts: ["src/assets/js/app.js"], globals: { SITE: { lang: "en", base: "/" } } });
await p.ready();
const btns = p.$$(".gl-btn");
const st = () => btns.map((b) => [b.getAttribute("aria-expanded"), p.doc.getElementById(b.getAttribute("aria-controls")).hidden]);
const res = {
  n: btns.length,
  first: { tag: btns[0].tagName, type: btns[0].getAttribute("type"), text: btns[0].textContent, abbrTitle: btns[0].querySelector("abbr").getAttribute("title"),
           note: p.doc.getElementById(btns[0].getAttribute("aria-controls")).textContent,
           role: p.doc.getElementById(btns[0].getAttribute("aria-controls")).getAttribute("role"),
           next: btns[0].nextSibling && btns[0].nextSibling.getAttribute && btns[0].nextSibling.getAttribute("id") === btns[0].getAttribute("aria-controls") },
  start: st(),
};
p.click(btns[0]);
res.open = st();
p.click(btns[1]);
res.other = st();
btns[1].focus();
p.key(btns[1], "Escape");
res.esc = st();
res.focus = p.doc.activeElement === btns[1];
p.click(btns[0]);
p.click(p.$("#other"));
res.outside = st();
res.inLink = { plain: !p.$("#link .gl-btn"), title: p.$("#link abbr").getAttribute("title") };
// a phone's address bar hiding as the page scrolls (a new height only), then the phone turned (a new width)
p.click(btns[0]);
p.win.innerHeight = 700;
p.win.dispatchEvent(new p.win.Event("resize"));
res.taller = st();
p.win.innerWidth = 390;
p.win.dispatchEvent(new p.win.Event("resize"));
res.turned = st();
res.errors = p.errors.map(String);
out(res);
"""


class Browser(unittest.TestCase):
    def test_a_disclosure_that_works_with_a_tap_and_the_keyboard(self):
        r = run_js(self, PAGE_JS + BROWSER_JS, needs_modules=False)
        self.assertEqual(r["n"], 2)
        self.assertEqual(r["first"]["tag"], "BUTTON")
        self.assertEqual(r["first"]["type"], "button")
        self.assertEqual(r["first"]["text"], "GVR", "its name is the word as written")
        self.assertIsNone(r["first"]["abbrTitle"], "no second tooltip once the note is there")
        self.assertEqual(r["first"]["note"], "Grapevine Representative: the member who …")
        self.assertEqual(r["first"]["role"], "note")
        self.assertTrue(r["first"]["next"], "the note comes right after its word")
        self.assertEqual(r["start"], [["false", True], ["false", True]])
        self.assertEqual(r["open"], [["true", False], ["false", True]])
        self.assertEqual(r["other"], [["false", True], ["true", False]], "one open at a time")
        self.assertEqual(r["esc"], [["false", True], ["false", True]])
        self.assertTrue(r["focus"], "Escape puts the focus back on the word")
        self.assertEqual(r["outside"], [["false", True], ["false", True]], "a tap elsewhere closes it")
        self.assertEqual(r["inLink"], {"plain": True, "title": "In a link"})
        self.assertEqual(r["taller"], [["true", False], ["false", True]], "a new height alone leaves it open")
        self.assertEqual(r["turned"], [["false", True], ["false", True]], "a new width closes it")
        self.assertEqual(r["errors"], [])


if __name__ == "__main__":
    unittest.main()
