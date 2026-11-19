"""Round 33 · the text-size and spacing rules wait for class "gv-prefs" on <html> (audit perf-2) — static checks and the
two scripts that set the class, run in Node.js with a stand-in <html> (the measured browser checks — the Aa panel
changing the page live, and after a reload — are in tests/browser/test_r33_prefs.py).

<html> always carries data-text and data-spacing, so a rule like ':root[data-text="150"] main .x' made the browser try
it on every element of the page at every style update, also at the default settings, where none of them ever applies
(almost half of all selector work on /events/). Every such rule now starts with ':root:where(.gv-prefs)'; the class is
on only while the size is not 100% or the spacing is relaxed:

  * Css      — no text-size / spacing rule in main.css or areas/*.css is left without the gate; the "only at the
               default" forms (':root:not([data-text="115"], …)', ':root:not([data-spacing="relaxed"])') and
               ':root:not([data-text="100"])' are left as they are; the class is never used any other way (no
               specificity added: :where()).
  * HeadScript — base.njk's first <head> script, run as the page runs it: the class for a saved size of 115 / 130 /
               150 or relaxed spacing, none at the defaults, for a saved 100, for bad JSON or blocked storage.
  * LiveSwitch — app.js GV.prefs.set() / .reset() (the Aa panel) turn the class on and off at once, with the
               attributes; contrast, motion and data saver alone never turn it on.

    python -m unittest tests.test_r33_prefs -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

CSS_FILES = [ROOT / "src" / "assets" / "css" / "main.css", *sorted((ROOT / "src" / "assets" / "css" / "areas").glob("*.css"))]
GATE = ":where(.gv-prefs)"


def code_only(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def root_compounds(css: str):
    """Every ':root…' compound selector of the stylesheet's rules (comments left out): the text right after ':root'
    up to the next combinator, comma or '{' at the top level."""
    s = code_only(css)
    for m in re.finditer(r":root", s):
        i = j = m.end()
        depth = 0
        while j < len(s):
            c = s[j]
            if c in "([":
                depth += 1
            elif c in ")]":
                if depth == 0:
                    break
                depth -= 1
            elif c in "\"'":
                j = s.index(c, j + 1)
            elif depth == 0 and (c.isspace() or c in ",{>+~"):
                break
            j += 1
        yield s[i:j]


def without_not(comp: str) -> str:
    """The compound without its :not(…) groups — what is left is what it asks for."""
    out, i = [], 0
    while i < len(comp):
        if comp.startswith(":not(", i):
            depth, j = 0, i + 4
            while j < len(comp):
                depth += {"(": 1, ")": -1}.get(comp[j], 0)
                if depth == 0:
                    break
                j += 1
            i = j + 1
            continue
        out.append(comp[i])
        i += 1
    return "".join(out)


def asks_for_prefs(comp: str) -> bool:
    return bool(re.search(r"\[data-(text|spacing)", without_not(comp)))


class Css(unittest.TestCase):
    def test_every_text_size_and_spacing_rule_waits_for_the_class(self):
        ungated, gated = [], 0
        for f in CSS_FILES:
            for comp in root_compounds(f.read_text(encoding="utf-8")):
                if asks_for_prefs(comp):
                    if comp.startswith(GATE):
                        gated += 1
                    else:
                        ungated.append(f"{f.name}: :root{comp[:100]}")
        self.assertEqual(ungated, [], "start these with :root:where(.gv-prefs) (main.css, READING & DISPLAY SETTINGS)")
        self.assertGreater(gated, 300, "the few hundred rules for a larger text size or relaxed spacing")

    def test_no_prefs_attribute_outside_a_root_compound(self):
        # a bare '[data-text="150"] .x' or 'html[data-spacing…]' would go round the gate
        for f in CSS_FILES:
            for line in code_only(f.read_text(encoding="utf-8")).splitlines():
                for m in re.finditer(r"\[data-(text|spacing)", line):
                    with self.subTest(file=f.name, line=line.strip()[:120]):
                        self.assertIn(":root", line[: m.start()])

    def test_the_default_only_forms_are_left_alone(self):
        main = (ROOT / "src" / "assets" / "css" / "main.css").read_text(encoding="utf-8")
        self.assertIn(':root:not([data-text="100"]) :is(.gv-hero, .page-hero) { min-height: calc(var(--hero-min) / var(--text-scale)); }', main)
        self.assertIn(':root:not([data-text="115"], [data-text="130"], [data-text="150"], [data-spacing="relaxed"])', main)
        for f in CSS_FILES:
            css = code_only(f.read_text(encoding="utf-8"))
            with self.subTest(file=f.name):
                # a gate only where the compound asks for a size or relaxed spacing (a gated pure :not() would stop
                # applying at the defaults, where it is meant to)
                for comp in root_compounds(css):
                    if comp.startswith(GATE):
                        self.assertTrue(asks_for_prefs(comp[len(GATE):]), comp[:100])
                # the class only ever as the gate on :root (':root.gv-prefs' or '.gv-prefs .x' would add specificity
                # or match without the attributes)
                self.assertEqual(css.count("gv-prefs"), css.count(":root" + GATE), f.name)

    def test_the_root_font_size_and_the_spacing(self):
        main = (ROOT / "src" / "assets" / "css" / "main.css").read_text(encoding="utf-8")
        for pct, scale in (("115", "1.15"), ("130", "1.3"), ("150", "1.5")):
            self.assertIn(f':root:where(.gv-prefs)[data-text="{pct}"] {{ font-size: {pct}%; --text-scale: {scale}; }}', main)
        self.assertIn(':root:where(.gv-prefs)[data-spacing="relaxed"] body :is(p, li, dd, dt, td, th, blockquote, figcaption, label, summary)', main)
        self.assertIn("THE GATE", main[: main.index(":root { --text-scale: 1; }")])


FAKE_HTML = r"""
function fakeHtml() {
  const attrs = {}, cls = new Set(["scroll-smooth"]);
  return {
    attrs, cls,
    getAttribute: (k) => (k in attrs ? attrs[k] : null),
    setAttribute: (k, v) => { attrs[k] = String(v); },
    classList: {
      add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c),
      toggle: (c, on) => { if (on === undefined) on = !cls.has(c); if (on) cls.add(c); else cls.delete(c); return on; },
    },
  };
}
function fakeStorage(value, blocked) {
  const m = new Map(value === undefined ? [] : [["gvlv-prefs", value]]);
  const no = () => { throw new Error("SecurityError"); };
  return blocked ? { getItem: no, setItem: no, removeItem: no }
    : { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) };
}
"""


class HeadScript(unittest.TestCase):
    def head_script(self) -> str:
        base = (ROOT / "src" / "_includes" / "layouts" / "base.njk").read_text(encoding="utf-8")
        head = re.sub(r"\{#.*?#\}", "", base.split("<title>")[0], flags=re.S)     # Nunjucks comments (they name <script>)
        js = head[head.index("<script>") + len("<script>"): head.index("</script>")]
        js = re.sub(r"\{%.*?%\}", "", js, flags=re.S)                 # {% if pageKey == "home" %} … (the fonts)
        return re.sub(r"\{\{.*?\}\}", "/font.woff2", js, flags=re.S)

    def test_the_head_script_sets_the_class_with_the_attributes(self):
        js = self.head_script()
        self.assertIn('d.classList.add("gv-prefs")', js)
        # after both attributes it reads
        self.assertLess(js.index('setAttribute("data-spacing"'), js.index('classList.add("gv-prefs")'))
        cases = {
            "none": None, "defaults": '{"text":100,"spacing":"normal"}', "text115": '{"text":115}', "text130": '{"text":"130"}',
            "text150": '{"text":150}', "relaxed": '{"spacing":"relaxed"}', "both": '{"text":130,"spacing":"relaxed"}',
            "contrast": '{"contrast":"high","motion":"reduce","saver":"on"}', "bad": "{not json", "odd": '{"text":120}',
            "blocked": "BLOCKED",
        }
        res = run_js(self, FAKE_HTML + r"""
const src = input.js, res = {};
for (const [name, value] of Object.entries(input.cases)) {
  const d = fakeHtml();
  const head = { appendChild() {} };
  const document = { documentElement: d, head, createElement: () => ({}) };
  const navigator = { connection: {}, onLine: true };
  const localStorage = fakeStorage(value === null ? undefined : value, value === "BLOCKED");
  new Function("document", "navigator", "localStorage", src)(document, navigator, localStorage);
  res[name] = [d.attrs["data-text"], d.attrs["data-spacing"], d.cls.has("gv-prefs"), d.cls.has("scroll-smooth")];
}
out(res);
""", data={"js": js, "cases": cases}, needs_modules=False)
        want = {
            "none": ["100", "normal", False], "defaults": ["100", "normal", False], "text115": ["115", "normal", True],
            "text130": ["130", "normal", True], "text150": ["150", "normal", True], "relaxed": ["100", "relaxed", True],
            "both": ["130", "relaxed", True], "contrast": ["100", "normal", False], "bad": ["100", "normal", False],
            "odd": ["100", "normal", False], "blocked": ["100", "normal", False],
        }
        for name, w in want.items():
            with self.subTest(case=name):
                self.assertEqual(res[name], w + [True], "data-text, data-spacing, gv-prefs (the page's own class kept)")


class LiveSwitch(unittest.TestCase):
    def test_the_panel_turns_the_class_on_and_off_at_once(self):
        app = (ROOT / "src" / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        part = app[app.index('  var PREF_KEY = "gvlv-prefs";'): app.index("  // Another tab changed them")]
        self.assertIn('d.classList.toggle("gv-prefs", String(prefs.text) !== "100" || prefs.spacing === "relaxed");', part)
        res = run_js(self, FAKE_HTML + r"""
const d = fakeHtml(), events = [];
const document = { documentElement: d };
const window = { dispatchEvent: (e) => events.push(e.detail) };
const navigator = { connection: {}, onLine: true };
class CustomEvent { constructor(type, o) { this.type = type; this.detail = o.detail; } }
const run = (saved) => {
  const GV = {};
  new Function("GV", "document", "window", "navigator", "localStorage", "CustomEvent", input.part)(
    GV, document, window, navigator, fakeStorage(saved), CustomEvent);
  return GV;
};
const GV = run(undefined), steps = [];
const look = (what) => steps.push([what, d.attrs["data-text"], d.attrs["data-spacing"], d.cls.has("gv-prefs")]);
GV.prefs.set({ text: 130 }); look("130");
GV.prefs.set({ text: 100 }); look("back to 100");
GV.prefs.set({ spacing: "relaxed" }); look("relaxed");
GV.prefs.set({ text: 150 }); look("150 + relaxed");
GV.prefs.set({ text: 100 }); look("100, still relaxed");
GV.prefs.set({ spacing: "normal" }); look("defaults");
GV.prefs.set({ contrast: "high", motion: "reduce", saver: "on", rate: "faster", captions: "on" }); look("other settings only");
GV.prefs.set({ text: 115 }); look("115");
GV.prefs.reset(); look("reset");
out({ steps, events: events.length, scroll: d.cls.has("scroll-smooth") });
""", data={"part": part}, needs_modules=False)
        self.assertEqual(res["steps"], [
            ["130", "130", "normal", True],
            ["back to 100", "100", "normal", False],
            ["relaxed", "100", "relaxed", True],
            ["150 + relaxed", "150", "relaxed", True],
            ["100, still relaxed", "100", "relaxed", True],
            ["defaults", "100", "normal", False],
            ["other settings only", "100", "normal", False],
            ["115", "115", "normal", True],
            ["reset", "100", "normal", False],
        ])
        self.assertEqual(res["events"], 9, "each change still fires gvlv:prefs (after the class is in place)")
        self.assertTrue(res["scroll"], "the page's own class stays")
        # the class goes on before the event: a listener measuring the new layout (community.js) sees the new rules
        self.assertLess(part.index('classList.toggle("gv-prefs"'), part.index("function firePrefs()"))


if __name__ == "__main__":
    unittest.main()
