"""Round 33 — the built site's JavaScript is minified (eleventy.config.js: minifyScripts, JS_MINIFY, and the
"JavaScript minified" eleventy.after step), checked quickly, without a whole build (tests/test_page_weight.py
checks the real build's files):

  * the options  — target es2017 with ??, ?., optional catch binding and ||= &&= ??= turned off (old Safari on a
                   booth's tablet or an older phone stops at the first one), object spread left as written, no
                   `format` (each file stays a plain script), license comments kept;
  * a sample     — a script that minifying WOULD turn into ??, ?. and `catch {` at esbuild's default target comes
                   out without any of them, smaller, with its top-level names, property names and license comment,
                   and gives the same answers when it runs;
  * the vendor   — minisearch.js and lite-yt-embed.js (from node_modules, as the build copies them) come out with
                   the same top-level names (no esbuild helper functions as new globals) and still work; a vendor
                   file that is not in the list (alpine.min.js) and a file that is not a script are left alone;
  * failures     — a script esbuild cannot read rejects (the build fails) naming the file; a folder without
                   scripts is nothing to do;
  * the step     — a build that writes no files (Eleventy's toJSON(), as tests use it) touches nothing.

Skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_js_minify -v
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# What esbuild would write at its default target (esnext) for SAMPLE: `a ?? "none"`, `x?.y`, `catch {`.
SAMPLE = r"""/* A sample script: what minifying would write as newer syntax at esbuild's default target (esnext). */
/*! sample license: keep me */
var gvSampleTop = 1;
function gvSampleFn(o) {
  var a = o.first;
  var b = a != null ? a : "none";
  var x = o.x;
  var d = x == null ? void 0 : x.y;
  try { JSON.parse(o.json); } catch (err) { b = b + "!"; }
  var c = o.count;
  c = c || 1;
  var v = o.v;
  v != null || (v = 0);
  return { first: b, d: d, longPropertyName: o.longPropertyName, count: c, v: v, line: "one\ntwo" };
}
window.GVSample = { fn: gvSampleFn, keepThisName: true };
"""

MINIFY_JS = r"""
import vm from "node:vm";
const { minifyScripts, JS_MINIFY } = await imp("eleventy.config.js");
const { transformSync } = await import("esbuild");
const BUILTIN = new Set(Object.getOwnPropertyNames(vm.runInContext("globalThis", vm.createContext({}))));
// The names a classic script declares at its top level (what it adds to window): they exist before its first
// statement runs, so the script is stopped at once ("throw" first).
const globals = (code) => {
  const ctx = vm.createContext({});
  try { vm.runInContext("throw 0;\n" + code, ctx); } catch (e) { if (e !== 0) throw e; }
  return Object.getOwnPropertyNames(vm.runInContext("globalThis", ctx)).filter((n) => !BUILTIN.has(n)).sort();
};
const marks = (s) => ({ "??": (s.match(/\?\?/g) || []).length, "?.": (s.match(/\?\.(?!\d)/g) || []).length,
                        "catch{": (s.match(/catch\{/g) || []).length, "||=": (s.match(/\|\|=/g) || []).length,
                        "&&=": (s.match(/&&=/g) || []).length });
const run = (code, inputs) => {
  const ctx = vm.createContext({ JSON });
  ctx.window = ctx;
  vm.runInContext(code, ctx);
  return inputs.map((o) => JSON.stringify(ctx.GVSample.fn(o)));
};
const searchWith = (code) => {
  const ctx = vm.createContext({});
  vm.runInContext(code, ctx);
  const ms = new ctx.MiniSearch({ fields: ["title", "text"], storeFields: ["title"] });
  ms.addAll([{ id: 1, title: "Año nuevo", text: "La Viña en Texas" }, { id: 2, title: "Grapevine", text: "Meeting in Dallas" },
             { id: 3, title: "Anónimo", text: "Viña y Grapevine" }]);
  return JSON.stringify([ms.search("vina", { prefix: true, fuzzy: 0.2 }), ms.search("grape", { prefix: true }), ms.autoSuggest("gra")]);
};
const ytDefine = (code) => {
  const defined = {};
  // (lite-youtube-embed 0.3.5 and later ask customElements.get first, and define the element only once)
  const ctx = vm.createContext({ HTMLElement: class {}, customElements: {
    get(n) { return defined[n]; }, define(n, c) { defined[n] = c.name; } } });
  vm.runInContext(code, ctx);
  return defined;
};

const siteDir = path.join(input.tmp, "site");
const js = path.join(siteDir, "assets", "js"), vendor = path.join(siteDir, "assets", "vendor");
fs.mkdirSync(js, { recursive: true });
fs.mkdirSync(vendor, { recursive: true });
fs.writeFileSync(path.join(js, "sample.js"), input.sample);
fs.writeFileSync(path.join(js, "notes.txt"), "not a script ?? ?.\n");
const SRC = {
  minisearch: fs.readFileSync("node_modules/minisearch/dist/umd/index.js", "utf8"),
  yt: fs.readFileSync("node_modules/lite-youtube-embed/src/lite-yt-embed.js", "utf8"),
  alpine: fs.readFileSync("node_modules/alpinejs/dist/cdn.min.js", "utf8"),
};
fs.writeFileSync(path.join(vendor, "minisearch.js"), SRC.minisearch);
fs.writeFileSync(path.join(vendor, "lite-yt-embed.js"), SRC.yt);
fs.writeFileSync(path.join(vendor, "alpine.min.js"), SRC.alpine);

// the step as the build runs it, for a build that writes no files: nothing is touched
const after = [];
const cfg = new Proxy({}, {
  get(_t, name) {
    if (name === "on") return (ev, fn) => { if (ev === "eleventy.after") after.push(fn); };
    return () => ({ add() {} });
  },
});
(await imp("eleventy.config.js")).default(cfg);
for (const mode of ["json", "ndjson"]) for (const fn of after) await fn({ directories: { output: siteDir }, dir: { output: siteDir }, outputMode: mode });
const untouchedByJson = fs.readFileSync(path.join(js, "sample.js"), "utf8") === input.sample;

const result = await minifyScripts(siteDir);
const got = {
  sample: fs.readFileSync(path.join(js, "sample.js"), "utf8"),
  notes: fs.readFileSync(path.join(js, "notes.txt"), "utf8"),
  minisearch: fs.readFileSync(path.join(vendor, "minisearch.js"), "utf8"),
  yt: fs.readFileSync(path.join(vendor, "lite-yt-embed.js"), "utf8"),
  alpine: fs.readFileSync(path.join(vendor, "alpine.min.js"), "utf8"),
};
const inputs = [{ first: null, x: { y: 2 }, json: "{", count: 0, v: null, longPropertyName: 5 },
                { first: "a", x: null, json: "{}", count: 3, v: 7 }];

// a script esbuild cannot read
const bad = path.join(input.tmp, "bad");
fs.mkdirSync(path.join(bad, "assets", "js"), { recursive: true });
fs.writeFileSync(path.join(bad, "assets", "js", "broken.js"), "function (\n");
let rejected = "";
try { await minifyScripts(bad); } catch (e) { rejected = e.message; }
const empty = await minifyScripts(path.join(input.tmp, "nothing-here"));

out({
  options: JS_MINIFY,
  untouchedByJson,
  result,
  esnext: marks(transformSync(input.sample, { minify: true }).code),
  sample: { text: got.sample, marks: marks(got.sample), globals: globals(got.sample), srcGlobals: globals(input.sample),
            runs: run(got.sample, inputs), srcRuns: run(input.sample, inputs) },
  notesSame: got.notes === "not a script ?? ?.\n",
  alpineSame: got.alpine === SRC.alpine,
  minisearch: { marks: marks(got.minisearch), srcMarks: marks(transformSync(SRC.minisearch, { minifyWhitespace: true }).code),
                globals: globals(got.minisearch), srcGlobals: globals(SRC.minisearch),
                search: searchWith(got.minisearch), srcSearch: searchWith(SRC.minisearch),
                bytes: got.minisearch.length, srcBytes: SRC.minisearch.length },
  yt: { marks: marks(got.yt), srcMarks: marks(transformSync(SRC.yt, { minifyWhitespace: true }).code),
        defined: ytDefine(got.yt), srcDefined: ytDefine(SRC.yt), bytes: got.yt.length, srcBytes: SRC.yt.length },
  rejected,
  empty,
});
"""


def has_modules() -> bool:
    return bool(node_path()) and (ROOT / "node_modules" / "esbuild").is_dir() and (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir()


class MinifyScripts(unittest.TestCase):
    r = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="r33-minify-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        if not has_modules():
            self.skipTest("Node.js or the site's npm packages (npm ci) are missing")
        if MinifyScripts.r is None:
            MinifyScripts.r = run_js(self, MINIFY_JS, data={"tmp": str(self.tmp), "sample": SAMPLE}, needs_modules=False)
        self.r = MinifyScripts.r

    def test_the_options_never_let_minifying_write_newer_syntax(self):
        o = self.r["options"]
        self.assertTrue(o["minify"])
        self.assertEqual(o["target"], "es2017", "never raise it: old Safari (booth tablets, older phones)")
        for feature in ("nullish-coalescing", "optional-chain", "optional-catch-binding", "logical-assignment"):
            self.assertIs(o["supported"].get(feature), False, f"{feature} must stay off")
        self.assertIs(o["supported"].get("object-rest-spread"), True,
                      "object spread stays as written (rewriting it adds esbuild's helpers as globals)")
        self.assertNotIn("format", o, "no format: each file stays a plain script, its top-level names kept")
        self.assertEqual(o["legalComments"], "inline")

    def test_the_sample_would_get_newer_syntax_at_esnext(self):
        # (so the next test means something)
        for mark in ("??", "?.", "catch{"):
            self.assertGreater(self.r["esnext"][mark], 0, mark)

    def test_the_sample_comes_out_minified_without_newer_syntax(self):
        s = self.r["sample"]
        self.assertEqual(s["marks"], {"??": 0, "?.": 0, "catch{": 0, "||=": 0, "&&=": 0}, s["text"])
        self.assertLess(len(s["text"]), len(SAMPLE) * 0.75)
        self.assertNotIn("A sample script", s["text"], "comments go")
        self.assertIn("/*! sample license: keep me */", s["text"], "license comments stay")
        self.assertNotIn("\n  ", s["text"])

    def test_the_sample_keeps_its_names_and_its_answers(self):
        s = self.r["sample"]
        self.assertEqual(s["srcGlobals"], ["gvSampleFn", "gvSampleTop"])
        self.assertEqual(s["globals"], s["srcGlobals"], "top-level names (globals) kept, none added")
        for name in ("GVSample", "keepThisName", "longPropertyName"):
            self.assertIn(name, s["text"], "property names are never shortened")
        self.assertEqual(s["runs"], s["srcRuns"], "the same answers")
        self.assertIn('"first":"none!"', s["runs"][0])

    def test_the_vendor_files_keep_their_names_and_still_work(self):
        m = self.r["minisearch"]
        self.assertEqual(m["globals"], m["srcGlobals"], "no esbuild helper functions as new globals (window._, window.C …)")
        for mark, n in m["marks"].items():
            self.assertLessEqual(n, m["srcMarks"][mark], f"minisearch.js: {mark}")
        self.assertEqual(m["search"], m["srcSearch"], "the same search results")
        self.assertIn("Año nuevo", m["search"])
        self.assertLess(m["bytes"], m["srcBytes"] * 0.5)
        y = self.r["yt"]
        self.assertEqual(y["defined"], {"lite-youtube": "LiteYTEmbed"})
        self.assertEqual(y["defined"], y["srcDefined"])
        for mark, n in y["marks"].items():
            self.assertLessEqual(n, y["srcMarks"][mark], f"lite-yt-embed.js: {mark}")
        self.assertLess(y["bytes"], y["srcBytes"] * 0.6)

    def test_only_the_listed_files_are_minified(self):
        self.assertEqual(self.r["result"]["files"], 3, "sample.js, minisearch.js, lite-yt-embed.js")
        self.assertLess(self.r["result"]["after"], self.r["result"]["before"])
        self.assertTrue(self.r["alpineSame"], "a vendor file already minified is left alone")
        self.assertTrue(self.r["notesSame"], "a file that is not a script is left alone")

    def test_a_script_esbuild_cannot_read_fails_the_build(self):
        self.assertIn("[js] assets/js/broken.js: esbuild could not minify it", self.r["rejected"])

    def test_nothing_to_do_without_scripts(self):
        self.assertEqual(self.r["empty"], {"files": 0, "before": 0, "after": 0})

    def test_a_build_that_writes_no_files_touches_nothing(self):
        self.assertTrue(self.r["untouchedByJson"])


if __name__ == "__main__":
    unittest.main()
