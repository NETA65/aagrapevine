"""No dead code in what builds the site: every Eleventy filter and shortcode is used, every shared macro is
called, every string in src/_i18n is read, and the numbers two files share come from one place.

  * Filters / shortcodes — every name registered in eleventy.config.js and eleventy/filters/*.js is used by a
    template (`| name`, `{% name %}`), a JS page (`this.name(…)`) or looked up by name (getFilter("name")).
  * Macros — every macro of src/_includes/macros/*.njk is called (`ui.name(…)`, `{% call ui.name %}`, or by
    another macro of its file).
  * Strings — every key of src/_i18n/*.json is read by the code (src/, eleventy/, scripts/, config/):
      - written out ("committee.meeting.join"), or
      - built from a written beginning — ("access.f_" + f + "_t"), `community.digest.n_${k}`, "home.nth." ~ n —
        or by adding "_one" to a key that is read (search.njk's (b[5] + "_one")), or
      - an "expenses.*" key whose rest ("toast.saved") the Tracker's scripts read: the page hands the whole
        file to them (src/_data/expenses.js expenses.ui).
    tests/ do not count: a string only a test reads is shown nowhere.
  * One number, one place — the earlier magazine issues /read/ shows itself (eleventy/filters/read.js
    SSR_ARCHIVE): /read-archive.json starts right after the page's last one (an Eleventy build of both, with
    13 earlier issues).
  * Files that are not pages (JSON, XML, calendars, robots.txt, scripts) say `layout: false` (or null).

Skipped without Node.js or the site's npm packages (the build test; tests/nodejs.py).

    python -m unittest tests.test_unused_code -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REGISTER = re.compile(r"\badd(?:Nunjucks)?(Filter|Shortcode|PairedShortcode)\(\s*\"([A-Za-z_]\w*)\"")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def files(*globs: str) -> list[Path]:
    out = []
    for g in globs:
        out += sorted(ROOT.glob(g))
    return [p for p in out if p.is_file() and "node_modules" not in p.parts]


def without_njk_comments(t: str) -> str:
    return re.sub(r"\{#.*?#\}", " ", t, flags=re.S)


# ============================================================================ filters and shortcodes
def registered(extra: str = "") -> list[tuple[str, str, str]]:
    """[(kind, name, file)] of every filter and shortcode the build registers (+ those `extra` registers)."""
    out = []
    for where, text in [(rel(p), read(p)) for p in [ROOT / "eleventy.config.js"] + files("eleventy/filters/*.js")] + [("extra", extra)]:
        for m in REGISTER.finditer(text):
            out.append((m.group(1), m.group(2), where))
    return out


def unused_filters(extra_registry: str = "", extra_templates: str = "") -> list[str]:
    """The filters and shortcodes nothing uses (with a made-up registration / template added, for the tests)."""
    templates = "\n".join(without_njk_comments(read(p)) for p in files("src/**/*.njk")) + without_njk_comments(extra_templates)
    js_pages = "\n".join(read(p) for p in files("src/pages/*.11ty.js"))
    lookups = "\n".join(read(p) for p in [ROOT / "eleventy.config.js"] + files("eleventy/**/*.js"))
    out = []
    for kind, name, where in registered(extra_registry):
        n = re.escape(name)
        used = (re.search(r"\|\s*" + n + r"\b", templates)                         # {{ x | name }}
                or re.search(r"\{%-?\s*(?:call\s+)?" + n + r"\b", templates)       # {% name … %}
                or re.search(r"\bthis\." + n + r"\s*\(", js_pages)                  # this.name(…) in a JS page
                or re.search(r"getFilter\(\s*\"" + n + r"\"", lookups)             # looked up by name
                or re.search(r"filterFn\(\s*\"" + n + r"\"", lookups))
        if not used:
            out.append(f"{kind.lower()} {name} ({where})")
    return out


# ============================================================================ macros
def unused_macros(extra: dict[str, str] | None = None) -> list[str]:
    """The macros of src/_includes/macros nothing calls (`extra`: {file: text} added, for the tests)."""
    everything = {rel(p): without_njk_comments(read(p)) for p in files("src/**/*.njk")}
    everything.update({f: without_njk_comments(t) for f, t in (extra or {}).items()})
    out = []
    for f, own in everything.items():
        if not f.startswith("src/_includes/macros/"):
            continue
        for m in re.finditer(r"\{%-?\s*macro\s+(\w+)", own):
            name = m.group(1)
            elsewhere = any(re.search(r"\.\s*" + name + r"\s*\(", t) for g, t in everything.items() if g != f)
            inside = len(re.findall(r"(?<![\w.])" + name + r"\s*\(", own)) > 1      # the definition is one
            if not (elsewhere or inside):
                out.append(f"{f}: {name}")
    return out


# ============================================================================ strings
CODE_GLOBS = ["src/**/*.njk", "src/**/*.js", "src/**/*.mjs", "eleventy/**/*.js", "eleventy.config.js",
              "scripts/**/*.py", "scripts/**/*.mjs", "config/**/*.yml"]
TOKEN = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+")
QUOTED = re.compile(r"[\"'`]([A-Za-z0-9_][\w.-]*)[\"'`]")
# the written beginning of a key that is built: a text then added to — ("read.gvr.d" + n), ("home.nth." ~ n) —, the
# start of a template literal (`community.digest.n_${k}`), or a text ending in "_" (a ternary's branches:
# (edit ? "form.title_edit_" : "form.title_add_") + type)
BUILT = [re.compile(r"[\"'`]([a-z0-9_]+(?:\.[A-Za-z0-9_-]+)*[._-]?)[\"'`]\s*\)?\s*(?:\+|~)"),
         re.compile(r"`([a-z0-9_]+(?:\.[A-Za-z0-9_-]+)*[._-]?)\$\{"),
         re.compile(r"[\"'`]([a-z0-9_]+(?:\.[A-Za-z0-9_-]+)*_)[\"'`]")]


def strings() -> dict[str, str]:
    out = {}
    for p in files("src/_i18n/*.json"):
        for k in json.loads(read(p)):
            out[k] = p.name
    return out


def unread_strings(keys: dict[str, str], extra_code: str = "") -> list[str]:
    """The keys no code reads (see the module's docstring), in their files' order."""
    code = [read(p) for p in files(*CODE_GLOBS) if "/_i18n/" not in rel(p) and "src/assets/cache" not in rel(p)]
    code.append(extra_code)
    tokens, quoted, built = set(), set(), set()
    for t in code:
        tokens.update(TOKEN.findall(t))
        quoted.update(QUOTED.findall(t))
        for rx in BUILT:
            built.update(p for p in rx.findall(t) if len(p) >= 2)
    # "area.x…" (two parts or more) built: every key that starts so. "area." + name (report.js t("report." + k),
    # the Tracker's whole expenses.* set): a key whose rest is itself read — written ("c_rule", "toast.saved")
    # or built ("icon." + id).
    deep = {p for p in built if "." in p.rstrip("._-")}
    shallow = {p for p in built if p not in deep and p.endswith(".")}

    def rest_read(rest: str) -> bool:
        return rest in quoted or rest in tokens or any(rest.startswith(p) for p in built if len(p) < len(rest))

    def known(k: str) -> bool:
        return (k in tokens or any(k.startswith(p) for p in deep)
                or any(k.startswith(p) and rest_read(k[len(p):]) for p in shallow))

    return [k for k in keys if not (known(k) or (k.endswith("_one") and known(k[:-4])))]


# ============================================================================ the checks
class NothingUnused(unittest.TestCase):
    def test_every_filter_and_shortcode_is_used(self):
        self.assertGreater(len(registered()), 200)
        self.assertEqual(unused_filters(), [], "registered but used nowhere: remove it (and what only it used)")

    def test_an_unused_filter_is_caught(self):
        reg = ('eleventyConfig.addFilter("madeUpFilter", (x) => x);\n'
               'eleventyConfig.addShortcode("madeUpShortcode", () => "");\n')
        self.assertEqual(unused_filters(reg), ["filter madeUpFilter (extra)", "shortcode madeUpShortcode (extra)"])
        # a template that uses them (a comment that names them does not count)
        self.assertEqual(unused_filters(reg, '{# {{ x | madeUpFilter }} #}{% madeUpShortcode lang %}'), ["filter madeUpFilter (extra)"])
        self.assertEqual(unused_filters(reg, "{{ x | madeUpFilter(lang) }}{%- madeUpShortcode %}"), [])
        # mediaCleanTitle is only looked up by name (community.js filterFn("mediaCleanTitle")): used
        self.assertIn("mediaCleanTitle", {name for _, name, _ in registered()})

    def test_every_macro_is_called(self):
        self.assertEqual(unused_macros(), [], "a macro nothing calls: remove it")

    def test_an_unused_macro_is_caught(self):
        made_up = {"src/_includes/macros/made-up.njk": "{% macro card(x) %}{{ x }}{% endmacro %}\n{% macro row(x) %}{{ card(x) }}{% endmacro %}"}
        self.assertEqual(unused_macros(made_up), ["src/_includes/macros/made-up.njk: row"], "card is used by row; row by nobody")
        made_up["src/pages/made-up-page.njk"] = '{% import "macros/made-up.njk" as mu %}{{ mu.row(1) }}'
        self.assertEqual(unused_macros(made_up), [])

    def test_every_string_is_read(self):
        keys = strings()
        self.assertGreater(len(keys), 4000)
        self.assertEqual(unread_strings(keys), [], "strings no code reads: remove them from src/_i18n")

    def test_an_unread_string_is_caught(self):
        keys = {"common.made_up_label": "common.json", "access.f_text_t": "access.json", "search.browse_wn_one": "library.json",
                "expenses.toast.saved": "expenses.json", "expenses.made_up": "expenses.json", "read.gvr.d1_t": "read.json",
                "report.c_rule": "report.json", "report.made_up": "report.json", "common.made_up_one": "common.json"}
        # written out (access.f_text_t: "access.f_" + f + "_t"; read.gvr.d1_t: "read.gvr.d" + loop.index + "_t"),
        # "_one" added to a key that is read (search.njk), the Tracker's rest (toast.saved) and report.js T("c_rule")
        self.assertEqual(unread_strings(keys), ["common.made_up_label", "expenses.made_up", "report.made_up", "common.made_up_one"])
        self.assertEqual(unread_strings(keys, extra_code='{{ "common.made_up_label" | t(lang) }} T("made_up")'), ["common.made_up_one"])
        # "_one" counts once its key is read: {{ (key + "_one") | t(lang) }} with key = "common.made_up"
        self.assertEqual(unread_strings(keys, extra_code='{{ "common.made_up_label" | t(lang) }} T("made_up") ["common.made_up", 1]'), [])


class OneNumberOnePlace(unittest.TestCase):
    def test_the_read_page_and_its_archive_file_share_one_number(self):
        njk, js = read(ROOT / "src/pages/read.njk"), read(ROOT / "src/pages/read-archive.11ty.js")
        self.assertNotRegex(njk, r"set\s+SSR_ARCHIVE\s*=\s*\d", "read.njk takes the number from read.js")
        self.assertNotRegex(js, r"SSR_ARCHIVE\s*=\s*\d", "read-archive.11ty.js takes the number from read.js")
        self.assertRegex(read(ROOT / "eleventy/filters/read.js"), r"export const SSR_ARCHIVE = \d+;")

    def test_the_archive_file_starts_after_the_last_issue_on_the_page(self):
        # 14 Grapevine issues (Jan 2025 … Feb 2026), one story each: Feb 2026 is the current issue, the 13
        # earlier ones are the archive — the page shows the newest SSR_ARCHIVE, the file the rest, in order.
        items = [{"id": f"art:gv:{y}-{m:02d}", "kind": "article", "source": "crawl", "lang": "en", "status": "active",
                  "title": f"Story of {y}-{m:02d}", "url": f"https://www.aagrapevine.org/magazine/{y}/{m:02d}/story",
                  "date": f"{y}-{m:02d}-01", "extra": {"publication": "gv", "issue_key": f"{y}-{m:02d}"}}
                 for y, m in [(2025, k) for k in range(1, 13)] + [(2026, 1), (2026, 2)]]
        r = run_js(self, r"""
process.env.ONLY = "read";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const R = await imp("eleventy/filters/read.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-read-archive-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, articles: { updated: null, items: input.items, issues: [] } }),
      });
    },
  });
  const pages = await elev.toJSON();
  out({ n: R.SSR_ARCHIVE, pages: Object.fromEntries(pages.filter((p) => /read/.test(p.url || "")).map((p) => [p.url, p.content])) });
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
""", data={"items": items}, timeout=300)
        n, pages = r["n"], r["pages"]
        self.assertEqual(n, 8)
        for page, file in (("/read/", "/read-archive.json"), ("/es/read/", "/es/read-archive.json")):
            with self.subTest(page):
                html = pages[page]
                shown_keys = re.findall(r'<details class="read-past card[^"]*" data-pub="gv"', html)
                self.assertEqual(len(shown_keys), n, "the page shows SSR_ARCHIVE earlier issues")
                data = json.loads(pages[file])
                self.assertEqual(data["count"], 13 - n, "the file holds the rest")
                self.assertEqual([i["key"] for i in data["issues"]], [f"2025-{m:02d}" for m in range(13 - n, 0, -1)],
                                 "… starting right after the page's last one (2025-06), newest first")
                self.assertIn(f"remaining: {13 - n}", html, "the page's 'Load older issues' counts them")


class NotPages(unittest.TestCase):
    def test_files_that_are_not_pages_have_no_layout(self):
        checked = []
        for p in files("src/pages/*.11ty.js"):
            t = read(p)
            perm = re.search(r"permalink:\s*(.+)", t)
            if not perm or re.search(r"\.html\b|index\.html", perm.group(1)):
                continue
            checked.append(rel(p))
            with self.subTest(rel(p)):
                self.assertRegex(t, r"\blayout:\s*(?:false|null)\b", "a JSON / XML / calendar / script file has no page layout")
        for p in files("src/*.njk", "src/pages/*.njk"):
            fm = re.match(r"---\n(.*?)\n---", read(p).replace("\r\n", "\n"), re.S)
            data = yaml.safe_load(fm.group(1)) if fm else {}
            perm = str((data or {}).get("permalink") or "")
            if not perm or perm.endswith((".html", "/")) or "index.html" in perm:
                continue
            checked.append(rel(p))
            with self.subTest(rel(p)):
                self.assertIn("layout", data)
                self.assertIn(data["layout"], (False, None))
        self.assertIn("src/pages/read-archive.11ty.js", checked)
        self.assertIn("src/pages/published-archive-json.11ty.js", checked)
        self.assertIn("src/robots.njk", checked)


if __name__ == "__main__":
    unittest.main()
