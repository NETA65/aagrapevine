"""Page weight: the page-area stylesheets and the icon sprite.

  * Icons      — eleventy/icons.js through the {% icon %} shortcode: an icon is a small <svg> that keeps the
                 file's own attributes (CSS on .icon still reaches the drawing) and points at the page's sprite
                 (<use href="#i-name">); a label is escaped and makes it a named picture (role="img"); an unknown
                 or unsafe name gives nothing (and a warning). The iconSprite transform puts ONE hidden <svg> with a
                 <symbol> per icon the page points at (markup, templates, inline JSON) right after <body>; pages
                 without icons, and other files, are left alone.
  * The poster — src/assets/js/monthly.js puts the sprite's drawings back inline before html-to-image copies the
                 poster (the picture holds the poster alone, not the page's sprite).
  * CSS step   — a build that writes no files (Eleventy's toJSON(), as tests use it) compiles no stylesheet (no
                 stray ./_site).
  * Built site — one real build, as GitHub Pages builds it (PATH_PREFIX=/aagrapevine/, I18N_STRICT=1):
                 - every .css at the top of src/assets/css is in the output folder (--output), main.css without
                   the six page-area stylesheets' rules, each of those with its own;
                 - every page that uses an area's classes (its markup, or a script it loads) links that area's
                   stylesheet, right after main.css; a page that doesn't, doesn't;
                 - every <use> points at a symbol on its own page, every sprite symbol is used and draws something,
                   every icon points at a sprite, and the sprite comes once, right after <body>;
                 - "Save key pages for offline" (and the booth's own save) keeps each saved page's stylesheets:
                   the built service worker's assetUrls() on the built pages.

Skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_page_weight -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = "/aagrapevine/"
# The page-area stylesheets (src/assets/css/<name>.css → /assets/css/<name>.css) and their class prefixes, in the
# order main.css imported them (the order a page links them in).
AREAS = {"monthly": "mp-", "report": "rp-", "expenses": "xp-", "orientation": "o101-", "presentations": "gvp-", "booth": "gvb-"}
AREA_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(p) for p in AREAS.values()) + r")[a-z0-9]")


def css_stamps() -> dict[str, int]:
    """./_site/assets/css/*.css (a preview build's, if any) → modification times."""
    return {f.name: f.stat().st_mtime_ns for f in (ROOT / "_site" / "assets" / "css").glob("*.css")}


def has_modules() -> bool:
    return bool(node_path()) and (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir()


# ---------------------------------------------------------------------------------------------------------- icons
ICON_JS = r"""
const shortcodes = {}, transforms = {}, warned = [];
const cfg = new Proxy({}, {
  get(_t, name) {
    if (name === "addShortcode") return (n, fn) => { shortcodes[n] = fn; };
    if (name === "addTransform") return (n, fn) => { transforms[n] = fn; };
    return () => ({ add() {} });
  },
});
const conf = await imp("eleventy.config.js");
conf.default(cfg);
const warn = console.warn;
console.warn = (...a) => { warned.push(a.join(" ")); };
const icon = shortcodes.icon;
const page = (out, html) => transforms.iconSprite.call({ page: { outputPath: out } }, html);
const r = {
  plain: icon("calendar"),
  sized: icon("calendar", "size-4 shrink-0"),
  labelled: icon("triangle-alert", "size-4", `Q&A "x" <b>it's</b>`),
  badCls: icon("x", 'size-4" onclick="alert(1)'),
  missing: icon("no-such-icon-anywhere"),
  traversal: icon("../package"),
  quoted: icon('x" onload="y'),
  upper: icon("Calendar"),
  local: icon("grapes"),
  localFile: fs.readFileSync("src/_includes/icons/grapes.svg", "utf8"),
  lucideFile: fs.readFileSync("node_modules/lucide-static/icons/calendar.svg", "utf8"),
};
const html = `<!doctype html><html><head><title>t</title></head><body class="min-h-screen">` +
  `<header>${icon("menu")}${icon("calendar")}</header><main>${icon("calendar", "size-8")}` +
  `<template><span data-i="plus">${icon("plus")}</span></template>` +
  `<script type="application/json">{"h":"<svg><use href=\\"#i-check\\"/></svg>"}</script>` +
  `<div data-x="&lt;use href=&quot;#i-download&quot;&gt;"></div><a href="#i-not-an-icon-x">x</a></main></body></html>`;
r.page = page("/site/index.html", html);
r.again = page("/site/index.html", r.page);
r.none = page("/site/plain/index.html", "<!doctype html><html><body><p>No icons</p></body></html>");
r.xml = page("/site/feed.xml", html);
r.fragment = page("/site/frag.html", icon("x"));
// a ">" inside one of <body>'s attribute values (Alpine), and the sprite's name only as words in a script
r.alpine = page("/site/a/index.html", `<html><head><script>document.querySelector("[data-icon-sprite]")</script></head>` +
  `<body x-data="{ wide: innerWidth > 640 }" class='a>b'><main>${icon("menu")}</main></body></html>`);
r.warned = warned;
console.warn = warn;
out(r);
"""


class Icons(unittest.TestCase):
    r = None

    def setUp(self):
        if Icons.r is None:
            Icons.r = run_js(self, ICON_JS)
        self.r = Icons.r

    def test_an_icon_points_at_the_sprite_and_keeps_the_files_attributes(self):
        svg = self.r["plain"]
        self.assertTrue(svg.startswith('<svg class="icon size-5" aria-hidden="true" focusable="false" '), svg)
        self.assertTrue(svg.endswith('><use href="#i-calendar"/></svg>'), svg)
        for attr in ('viewBox="0 0 24 24"', 'fill="none"', 'stroke="currentColor"', 'stroke-width="2"',
                     'stroke-linecap="round"', 'stroke-linejoin="round"'):
            self.assertIn(attr, svg, "the file's own attributes stay on the icon (CSS on .icon reaches the drawing)")
        for gone in ("<path", "<rect", "xmlns", 'width="24"', 'height="24"', "lucide"):
            self.assertNotIn(gone, svg)
        self.assertIn('<svg class="icon size-4 shrink-0" ', self.r["sized"])
        # a local icon (src/_includes/icons) keeps its own attributes (grapes: a thinner line)
        self.assertIn('stroke-width="1.8"', self.r["local"])
        self.assertIn('stroke-width="1.8"', self.r["localFile"])

    def test_a_label_is_escaped_and_names_the_picture(self):
        svg = self.r["labelled"]
        self.assertIn('role="img" aria-label="Q&amp;A &quot;x&quot; &lt;b&gt;it&#39;s&lt;/b&gt;"', svg)
        self.assertNotIn("aria-hidden", svg)
        self.assertNotIn('<b>', svg)
        # the classes are escaped too: no way out of the attribute
        self.assertIn('class="icon size-4&quot; onclick=&quot;alert(1)"', self.r["badCls"])
        self.assertNotIn('" onclick="', self.r["badCls"])

    def test_unknown_or_unsafe_names_give_nothing_and_a_warning(self):
        for k in ("missing", "traversal", "quoted", "upper"):
            with self.subTest(k=k):
                self.assertEqual(self.r[k], "")
        self.assertTrue(any("[icon] missing icon: no-such-icon-anywhere" in w for w in self.r["warned"]))
        self.assertTrue(any("../package" in w for w in self.r["warned"]))

    def test_the_sprite_holds_each_icon_the_page_points_at_once(self):
        page = self.r["page"]
        m = re.search(r'<body class="min-h-screen">(<svg data-icon-sprite [^>]*>.*?</svg>)<header>', page, re.S)
        self.assertIsNotNone(m, "the sprite sits right after <body>")
        sprite = m.group(1)
        self.assertIn('aria-hidden="true"', sprite)
        self.assertIn('focusable="false"', sprite)
        self.assertIn("position:absolute;width:0;height:0;overflow:hidden", sprite)
        ids = re.findall(r'<symbol id="([^"]+)"', sprite)
        # markup, a <template>, inline JSON (\") and an escaped attribute (&quot;) alike — sorted, each once;
        # an anchor that only looks like one (#i-not-an-icon-x) adds nothing
        self.assertEqual(ids, ["i-calendar", "i-check", "i-download", "i-menu", "i-plus"])
        for sym in re.findall(r"<symbol [^>]*>(.*?)</symbol>", sprite, re.S):
            self.assertRegex(sym, r"<(path|line|rect|circle|polyline|polygon|ellipse)\b", "each symbol draws something")
        self.assertRegex(sprite, r'<symbol id="i-calendar" viewBox="0 0 24 24"><path ')
        self.assertNotRegex(sprite, r"<symbol [^>]*(fill|stroke)=", "no presentation attributes on a symbol")
        # the drawing is the file's own
        lucide_paths = re.findall(r'<(?:path|rect)\b[^>]*>', self.r["lucideFile"])
        cal = re.search(r'<symbol id="i-calendar"[^>]*>(.*?)</symbol>', sprite, re.S).group(1)
        self.assertEqual(len(re.findall(r'<(?:path|rect)\b', cal)), len(lucide_paths))
        self.assertEqual(page.count("data-icon-sprite"), 1)
        self.assertEqual(self.r["again"], page, "a page that has its sprite is left as it is")

    def test_pages_without_icons_and_other_files_are_left_alone(self):
        self.assertEqual(self.r["none"], "<!doctype html><html><body><p>No icons</p></body></html>")
        self.assertNotIn("data-icon-sprite", self.r["xml"], "only .html files get a sprite")
        frag = self.r["fragment"]
        self.assertTrue(frag.startswith("<svg class=\"icon"), "a fragment without <body> keeps its start")
        self.assertIn('<symbol id="i-x"', frag)

    def test_the_sprite_goes_after_the_whole_body_tag_whatever_its_attributes_hold(self):
        page = self.r["alpine"]
        self.assertIn("<body x-data=\"{ wide: innerWidth > 640 }\" class='a>b'><svg data-icon-sprite ", page,
                      "after <body …>'s own end, not inside an attribute value that holds a \">\"")
        self.assertEqual(page.count("<svg data-icon-sprite"), 1,
                         "the words data-icon-sprite in a script are not a sprite: the page still gets one")
        self.assertIn('<symbol id="i-menu"', page)


# ------------------------------------------------------------------------------------------ the poster's picture
POSTER_JS = r"""
const src = fs.readFileSync("src/assets/js/monthly.js", "utf8");
const m = /function inlineIcons\(root\) \{[\s\S]*?\n  \}\n/.exec(src);
if (!m) throw new Error("monthly.js: no inlineIcons(root)");
class Node {
  constructor(tag, attrs = {}, kids = []) { this.tagName = tag; this.attrs = { ...attrs }; this.childNodes = []; kids.forEach((k) => this.appendChild(k)); }
  appendChild(n) { n.parentNode = this; this.childNodes.push(n); return n; }
  insertBefore(n, ref) { n.parentNode = this; this.childNodes.splice(this.childNodes.indexOf(ref), 0, n); return n; }
  removeChild(n) { this.childNodes.splice(this.childNodes.indexOf(n), 1); n.parentNode = null; return n; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  cloneNode(deep) { return new Node(this.tagName, this.attrs, deep ? this.childNodes.map((c) => c.cloneNode(true)) : []); }
  *walk() { for (const c of this.childNodes) { yield c; yield* c.walk(); } }
  // the one selector inlineIcons asks for: svg > use[href^='#i-']
  querySelectorAll(sel) {
    if (sel !== "svg > use[href^='#i-']") throw new Error("unexpected selector " + sel);
    return [...this.walk()].filter((n) => n.tagName === "use" && n.parentNode && n.parentNode.tagName === "svg" && String(n.getAttribute("href") || "").startsWith("#i-"));
  }
  html() { const a = Object.entries(this.attrs).map(([k, v]) => ` ${k}="${v}"`).join(""); return `<${this.tagName}${a}>${this.childNodes.map((c) => c.html()).join("")}</${this.tagName}>`; }
}
const N = (t, a, k) => new Node(t, a, k);
const sprite = N("svg", { "data-icon-sprite": "" }, [
  N("symbol", { id: "i-star", viewBox: "0 0 24 24" }, [N("path", { d: "M1 2" }), N("circle", { r: "3" })]),
]);
const ids = { "i-star": sprite.childNodes[0] };
const document = { getElementById: (id) => ids[id] || null };
const poster = N("div", { class: "mp-poster" }, [
  N("svg", { class: "icon mp-m", "stroke-width": "2" }, [N("use", { href: "#i-star" })]),
  N("svg", { class: "icon" }, [N("use", { href: "#i-gone" })]),
  N("svg", { class: "icon" }, [N("use", { href: "#mi-play" })]),
]);
const inlineIcons = new Function("document", m[0] + "\nreturn inlineIcons;")(document);
inlineIcons(poster);
const first = poster.html();
inlineIcons(poster);
out({ poster: first, again: poster.html(), sprite: sprite.html() });
"""


class PosterPicture(unittest.TestCase):
    def test_the_poster_gets_its_drawings_inline_before_the_picture_is_made(self):
        r = run_js(self, POSTER_JS, needs_modules=False)
        self.assertEqual(r["poster"],
                         '<div class="mp-poster">'
                         '<svg class="icon mp-m" stroke-width="2"><path d="M1 2"></path><circle r="3"></circle></svg>'
                         '<svg class="icon"><use href="#i-gone"></use></svg>'      # no such symbol: left as it is
                         '<svg class="icon"><use href="#mi-play"></use></svg>'     # another sprite's: not ours
                         '</div>')
        self.assertEqual(r["again"], r["poster"], "a second picture changes nothing")
        self.assertIn('<symbol id="i-star" viewBox="0 0 24 24"><path d="M1 2"></path><circle r="3"></circle></symbol>',
                      r["sprite"], "the sprite keeps its drawings (copies go to the poster)")
        js = (ROOT / "src" / "assets" / "js" / "monthly.js").read_text(encoding="utf-8")
        render = js[js.index("function render()"):]
        self.assertLess(render.index("inlineIcons(poster)"), render.index("h2i.toBlob(poster"),
                        "the drawings are inline before html-to-image copies the poster")


# ------------------------------------------------------------------------------------------------------ CSS step
CSS_STEP_JS = r"""
const after = [];
const cfg = new Proxy({}, {
  get(_t, name) {
    if (name === "on") return (ev, fn) => { if (ev === "eleventy.after") after.push(fn); };
    return () => ({ add() {} });
  },
});
const conf = await imp("eleventy.config.js");
conf.default(cfg);
const res = {};
for (const mode of ["json", "ndjson"]) {
  const dir = path.join(input.tmp, mode);
  for (const fn of after) await fn({ directories: { output: dir }, dir: { output: dir }, outputMode: mode });
  res[mode] = fs.existsSync(dir);
}
out({ hooks: after.length, res });
"""


class CssStep(unittest.TestCase):
    def test_a_build_that_writes_no_files_compiles_no_stylesheet(self):
        tmp = Path(tempfile.mkdtemp(prefix="css-step-"))
        try:
            r = run_js(self, CSS_STEP_JS, data={"tmp": str(tmp)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertGreaterEqual(r["hooks"], 1)
        self.assertEqual(r["res"], {"json": False, "ndjson": False})


# -------------------------------------------------------------------------------------------------- the built site
SW_JS = r"""
import vm from "node:vm";
const code = fs.readFileSync(input.sw, "utf8");
const self = { addEventListener() {}, location: { origin: "https://example.test" }, registration: {}, clients: {} };
const ctx = vm.createContext({ self, caches: {}, fetch() {}, Request, Response, Headers, URL, console, setTimeout, clearTimeout,
                               setInterval, clearInterval, AbortController });
vm.runInContext(code, ctx);
const res = {};
for (const [key, file] of Object.entries(input.pages)) {
  const html = fs.readFileSync(file, "utf8");
  res[key] = [...vm.runInContext("assetUrls", ctx)(html, "https://example.test" + key)];
}
out({ save: vm.runInContext("CONFIG.save", ctx), booth: vm.runInContext("CONFIG.booth", ctx), assets: res });
"""


class BuiltSite(unittest.TestCase):
    """One real build of the whole site, as GitHub Pages builds it."""

    tmp: Path | None = None
    site: Path
    pages: dict[str, str]

    @classmethod
    def setUpClass(cls):
        if not has_modules():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="page-weight-"))
        cls.site = cls.tmp / "site"
        env = {**os.environ, "PATH_PREFIX": BASE, "I18N_STRICT": "1", "NODE_NO_WARNINGS": "1"}
        env.pop("ONLY", None)
        cls.stamps = css_stamps()
        cls.built = subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                                  "--output", str(cls.site)], cwd=ROOT, env=env, capture_output=True, text=True,
                                 encoding="utf-8", timeout=900)
        cls.pages = {}
        if cls.built.returncode == 0:
            for f in sorted(cls.site.rglob("*.html")):
                cls.pages["/" + f.relative_to(cls.site).as_posix()] = f.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        if not has_modules():
            self.skipTest("Node.js or the site's npm packages (npm ci) are missing")
        self.assertEqual(self.built.returncode, 0, self.built.stderr[-3000:])
        self.assertGreater(len(self.pages), 50)

    # -- stylesheets
    def css(self, name: str) -> str:
        return (self.site / "assets" / "css" / f"{name}.css").read_text(encoding="utf-8")

    def test_every_stylesheet_is_built_into_the_output_folder(self):
        entries = sorted(p.stem for p in (ROOT / "src" / "assets" / "css").glob("*.css"))
        self.assertEqual(entries, sorted(["main", *AREAS]))
        for name in entries:
            with self.subTest(name=name):
                self.assertGreater(len(self.css(name)), 5000)
        self.assertEqual(css_stamps(), self.stamps, "the stylesheets go to --output, never to ./_site")

    def test_main_css_leaves_the_area_rules_to_their_stylesheets(self):
        main = self.css("main")
        own = {"booth": ".gvb-sec{", "presentations": ".gvp-progress{", "expenses": ".xp-root{", "orientation": ".o101-welcome{",
               "monthly": ".mp-layout{", "report": ".rp-grid{"}
        for area, rule in own.items():
            with self.subTest(area=area):
                self.assertNotIn(rule, main)
                sheet = self.css(area)
                self.assertIn(rule, sheet)
                # its own rules only: none of Tailwind's base, theme or utilities again
                self.assertNotIn("--font-sans:", sheet)
                self.assertNotIn(".container-page{", sheet)
                self.assertLess(len(sheet), len(main) / 4)
        # main.css keeps what every page needs: the theme, the shared components, the areas of many pages
        for rule in ("--font-sans:", ".card{", ".site-header", ".gvlv-panel{", ".pwa-toast{", ".home-"):
            self.assertIn(rule, main)

    def test_pages_link_exactly_the_area_stylesheets_they_use(self):
        js_areas = {}
        for f in (ROOT / "src" / "assets" / "js").glob("*.js"):
            prefixes = set(AREA_RE.findall(f.read_text(encoding="utf-8")))
            js_areas[f.name] = {a for a, p in AREAS.items() if p in prefixes}
        seen = set()
        for url, html in self.pages.items():
            if "<link rel=\"stylesheet\"" not in html:
                continue                      # a forwarding page (its own small style)
            classes = set()
            for m in re.finditer(r'\sclass="([^"]*)"', html):
                classes.update(m.group(1).split())
            used = {a for a, p in AREAS.items() if any(c.startswith(p) for c in classes)}
            for s in re.findall(r'<script[^>]*\ssrc="[^"]*/assets/js/([^"?/]+)', html):
                used |= js_areas.get(s, set())
            sheets = re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)
            linked = [re.sub(r"\?.*$", "", s) for s in sheets]
            areas = [s.rsplit("/", 1)[1][:-4] for s in linked if re.match(re.escape(BASE) + r"assets/css/(?!main\.css)[a-z-]+\.css$", s)]
            with self.subTest(page=url):
                self.assertEqual(set(areas), used, "a page links the stylesheet of every area it uses, and no other")
                self.assertEqual(linked[0], BASE + "assets/css/main.css", "main.css first")
                self.assertEqual(linked[1:1 + len(areas)], [f"{BASE}assets/css/{a}.css" for a in AREAS if a in used],
                                 "then the area stylesheets, in main.css's former import order, before any vendor one")
                for s in linked:
                    self.assertTrue((self.site / s[len(BASE):]).is_file(), f"{s} is in the build")
            seen |= used
        self.assertEqual(seen, set(AREAS), "every area stylesheet is used by some page")
        for url, want in (("/about/index.html", {"booth"}), ("/es/tracker/index.html", {"expenses"}),
                          ("/orientation/index.html", {"orientation", "presentations"}),
                          ("/monthly/index.html", {"monthly", "report"}), ("/index.html", set())):
            with self.subTest(page=url):
                got = set(re.findall(r'assets/css/(\w+)\.css', self.pages[url])) - {"main"}
                self.assertEqual(got, want)

    # -- icons
    def test_every_use_points_at_a_symbol_on_its_own_page(self):
        refs = 0
        for url, html in self.pages.items():
            ids = set(re.findall(r'\sid="([^"]+)"', html))
            with self.subTest(page=url):
                for ref in re.findall(r'<use\b[^>]*\shref="#([^"]+)"', html):
                    refs += 1
                    self.assertIn(ref, ids, f"<use href=\"#{ref}\"> has nothing to draw")
        self.assertGreater(refs, 5000)

    def test_the_sprite_comes_once_right_after_body_and_every_symbol_draws(self):
        with_sprite = 0
        for url, html in self.pages.items():
            pointed = set(re.findall(r'href=(?:"|\\"|&quot;)#(i-[a-z0-9-]+)', html))
            with self.subTest(page=url):
                self.assertLessEqual(html.count("<svg data-icon-sprite"), 1)
                if not pointed:
                    self.assertNotIn("<svg data-icon-sprite", html)
                    continue
                with_sprite += 1
                m = re.search(r"""<body\b(?:[^>"']|"[^"]*"|'[^']*')*>(<svg data-icon-sprite [^>]*>)(.*?)</svg>""", html, re.S)
                self.assertIsNotNone(m, "the sprite is the first thing in <body>")
                self.assertIn('aria-hidden="true"', m.group(1))
                symbols = dict(re.findall(r'<symbol id="(i-[a-z0-9-]+)"[^>]*>(.*?)</symbol>', m.group(2), re.S))
                self.assertEqual(set(symbols), pointed, "a symbol for each icon the page uses, and only those")
                for sid, body in symbols.items():
                    self.assertRegex(body, r"<(path|line|rect|circle|polyline|polygon|ellipse)\b", f"{sid} draws nothing")
        self.assertGreater(with_sprite, 50)

    def test_every_icon_points_at_a_sprite(self):
        icons = 0
        for url, html in self.pages.items():
            html = re.sub(r"<svg data-icon-sprite.*?</svg>", "", html, flags=re.S)
            with self.subTest(page=url):
                for m in re.finditer(r'<svg class="icon[^"]*"([^>]*)>(.*?)</svg>', html, re.S):
                    icons += 1
                    self.assertRegex(m.group(2), r'^<use href="#[a-z0-9-]+"(?:/>|></use>)$',
                                     "an icon is a pointer at a sprite (eleventy/icons.js), not its whole drawing")
                    if m.group(2).startswith('<use href="#i-'):
                        self.assertTrue('aria-hidden="true" focusable="false"' in m.group(1) or 'role="img" aria-label="' in m.group(1),
                                        "decoration is hidden from screen readers; a labelled icon is a named picture")
        self.assertGreater(icons, 10000)

    def test_saved_pages_keep_their_area_stylesheets_offline(self):
        months = sorted(p for p in self.pages if re.fullmatch(r"/monthly/\d{4}-\d{2}/index\.html", p))
        self.assertTrue(months)
        pages = {}
        for lang in ("", "es/"):
            for p in ("", "meetings/", "monthly/", months[0][1:-len("index.html")], "tracker/", "orientation/",
                      "orientation/role/", "about/"):
                f = self.site / (lang + p) / "index.html"
                if f.is_file():
                    pages[BASE + lang + p] = str(f)
        r = run_js(self, SW_JS, data={"sw": str(self.site / "sw.js"), "pages": pages},
                   needs_modules=False)
        for key in ("tracker/", "orientation/", "monthly/", "monthly/{month}/"):
            self.assertIn(key, r["save"], "a key page saved for offline")
        self.assertEqual(r["booth"]["json"], "about/booth.json")   # the booth saves the About page itself
        for key, urls in r["assets"].items():
            html = Path(pages[key]).read_text(encoding="utf-8")
            sheets = {"https://example.test" + s.replace("&amp;", "&") for s in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)}
            with self.subTest(page=key):
                self.assertTrue(sheets <= set(urls), f"not kept offline: {sorted(sheets - set(urls))}")
        area_kept = {u.split("/assets/css/")[1].split(".css")[0] for urls in r["assets"].values() for u in urls if "/assets/css/" in u}
        self.assertEqual(area_kept, {"main", *AREAS})


if __name__ == "__main__":
    unittest.main()
