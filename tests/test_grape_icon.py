"""Round 37 · the grape icon everywhere but the header (the owner: "the NETA65 logo is only for the headerbar.
everywhere else for app, the google search, the favicon should all be our icon") — offline:

  * Files      — src/assets/img/favicon.ico holds 16, 32 and 48 px pictures; favicon-32/48/96.png are squares of their
                 size with rounded corners (transparent corners, an opaque middle); favicon.svg parses: a square
                 viewBox, the tile and the grapes, nothing that runs or loads (no script, no text, no outside
                 reference); the NETA 65 favicons are gone (src/favicon.ico, logo-32x32.png, logo-192x192.png) and no
                 file names them; logo-wide.png (the header's wordmark) and logo-180x180.png (e-mails already sent
                 show it) stay.
  * Script     — scripts/dev/make_app_icons.py `favicons` writes exactly the favicon files — never one of the five
                 app icons — and draws what is committed (the same SVG text, the same pictures); its 16 px picture is
                 the bolder mark, not the 48 px one made smaller; an unknown argument stops it before it writes.
  * Templates  — every rel="icon" in src/ names a grape file, never a logo-* one; base.njk and every stand-alone page
                 with a <head> take partials/icon-links.njk (and write no icon link of their own); the partial's
                 sizes are the files' own, and every file it names exists; the root copies come from src/assets/img/;
                 OpenSearch (32 px), the RSS feeds (96 px, its size given), the e-mail digest's tile and the service
                 worker's app shell name grape files.
  * Built      — a build written to disk (the home page, the 404 page, the stand-alone pages, OpenSearch, the feeds,
                 the service worker) under the /aagrapevine/ path prefix: every page's head has the six icon links,
                 the prefix added, none a logo-*; /favicon.ico, /favicon.svg, /apple-touch-icon.png and
                 /apple-touch-icon-precomposed.png are at the site's root, the same bytes as their sources; the files
                 OpenSearch and the feeds name are built.
  * Version    — build.version (src/_data/build.js) changes when only an icon changes (the favicons' sources sit
                 under src/assets/: the service worker's app shell takes a new drawing up), and not with the synced
                 data.

    python -m unittest tests.test_grape_icon -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

IMG = ROOT / "src" / "assets" / "img"
PARTIAL = ROOT / "src" / "_includes" / "partials" / "icon-links.njk"
PNGS = {"favicon-32.png": 32, "favicon-48.png": 48, "favicon-96.png": 96}
ICO_SIZES = {(16, 16), (32, 32), (48, 48)}
# what a rel="icon" may name: the favicons and the app icons — the grape icon (scripts/dev/make_app_icons.py)
GRAPE = re.compile(r"^/(?:favicon\.(?:ico|svg)|assets/img/(?:favicon-\d+\.png|app-icon-\d+\.png))$")
# the partial, in order: (rel, sizes, type, href)
LINKS = [
    ("icon", "16x16 32x32 48x48", None, "/favicon.ico"),
    ("icon", None, "image/svg+xml", "/favicon.svg"),
    ("icon", "48x48", "image/png", "/assets/img/favicon-48.png"),
    ("icon", "96x96", "image/png", "/assets/img/favicon-96.png"),
    ("icon", "192x192", "image/png", "/assets/img/app-icon-192.png"),
    ("apple-touch-icon", None, None, "/assets/img/apple-touch-icon-180.png"),
]
# the site's root copies (eleventy.config.js) → their sources
ROOT_COPIES = {
    "favicon.ico": "src/assets/img/favicon.ico",
    "favicon.svg": "src/assets/img/favicon.svg",
    "apple-touch-icon.png": "src/assets/img/apple-touch-icon-180.png",
    "apple-touch-icon-precomposed.png": "src/assets/img/apple-touch-icon-180.png",
}
GONE = ("logo-32x32", "logo-192x192")


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def icon_links(text: str) -> list[tuple[str, str | None, str | None, str | None]]:
    """The <link rel="icon"> and rel="apple-touch-icon" tags of a page or template: (rel, sizes, type, href)."""
    out = []
    for tag in re.findall(r'<link rel="(?:icon|apple-touch-icon|shortcut icon|apple-touch-icon-precomposed)"[^>]*>', text):
        attr = dict(re.findall(r'([a-z-]+)="([^"]*)"', tag))
        out.append((attr.get("rel"), attr.get("sizes"), attr.get("type"), attr.get("href")))
    return out


def frames(path: Path) -> dict[tuple[int, int], Image.Image]:
    with Image.open(path) as ico:
        out = {}
        for size in sorted(ico.info["sizes"]):
            ico.size = size
            out[size] = ico.copy().convert("RGBA")
        return out


def mean_diff(a: Image.Image, b: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGBA"), b.convert("RGBA"))).mean) / 4


def load_script():
    try:
        import numpy  # noqa: F401  (make_app_icons draws with it: installed with the content sync's packages)
    except ImportError:  # pragma: no cover
        raise unittest.SkipTest("numpy is not installed")
    spec = importlib.util.spec_from_file_location("make_app_icons_r37", ROOT / "scripts" / "dev" / "make_app_icons.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # (its dataclass looks its module up there)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------------------------------ Files
class Files(unittest.TestCase):
    def assert_rounded_square(self, im: Image.Image, size: int, what: str):
        self.assertEqual(im.size, (size, size), what)
        im = im.convert("RGBA")
        self.assertEqual(im.getpixel((0, 0))[3], 0, f"{what}: a transparent corner")
        self.assertEqual(im.getpixel((size - 1, size - 1))[3], 0, f"{what}: a transparent corner")
        self.assertEqual(im.getpixel((size // 2, size // 2))[3], 255, f"{what}: an opaque middle")
        # the gold grapes on the navy tile: some bright, warm pixels and some dark ones
        px = [im.getpixel((x, y)) for y in range(size) for x in range(size)]
        self.assertTrue(any(r > 200 and g > 160 and b < 190 and a == 255 for r, g, b, a in px), f"{what}: no gold grapes")
        self.assertTrue(any(r < 40 and b > 40 and a == 255 for r, g, b, a in px), f"{what}: no navy tile")

    def test_the_ico_holds_16_32_and_48(self):
        with Image.open(IMG / "favicon.ico") as ico:
            self.assertEqual(ico.format, "ICO")
            self.assertEqual(set(ico.info["sizes"]), ICO_SIZES)
        for (w, h), im in frames(IMG / "favicon.ico").items():
            with self.subTest(size=w):
                self.assertEqual(w, h, "square")
                self.assert_rounded_square(im, w, f"favicon.ico {w}px")

    def test_the_pngs_are_squares_of_their_size(self):
        for name, size in PNGS.items():
            with self.subTest(name=name), Image.open(IMG / name) as im:
                self.assertEqual(im.format, "PNG")
                self.assert_rounded_square(im, size, name)
        # Google: a square, a multiple of 48 px
        self.assertEqual([s % 48 for n, s in PNGS.items() if n != "favicon-32.png"], [0, 0])

    def test_the_svg_parses(self):
        text = read("src", "assets", "img", "favicon.svg")
        self.assertLess(len(text.encode("utf-8")), 4096)
        self.assertNotIn("\r", text)
        svg = ET.fromstring(text)
        ns = "{http://www.w3.org/2000/svg}"
        self.assertEqual(svg.tag, ns + "svg")
        self.assertEqual(svg.get("viewBox"), "0 0 48 48")
        tags = [el.tag.replace(ns, "") for el in svg.iter()]
        self.assertIn("rect", tags)
        self.assertGreaterEqual(tags.count("circle"), 6, "the grapes")
        self.assertIn("linearGradient", tags)
        for bad in ("script", "text", "image", "foreignObject", "style", "a", "use"):
            self.assertNotIn(bad, tags)
        for el in svg.iter():
            for k, v in el.attrib.items():
                self.assertFalse(k.startswith("on"), k)
                self.assertNotIn("href", k)
                self.assertTrue("url(" not in v or re.fullmatch(r"url\(#\w+\)", v), v)

    def test_the_neta_favicons_are_gone(self):
        self.assertFalse((ROOT / "src" / "favicon.ico").exists())
        for name in GONE:
            self.assertFalse((IMG / f"{name}.png").exists(), name)
        # the header's wordmark (and the print pieces'), and the digest tile of e-mails already sent, stay
        self.assertTrue((IMG / "logo-wide.png").is_file())
        self.assertTrue((IMG / "logo-180x180.png").is_file())
        me = Path(__file__).resolve()
        hits = []
        # (the code only: never the committee's config/ or content/ — scripts/ops/gate_tests.py)
        for top in ("src", "eleventy", "scripts", "tests", ".github"):
            for f in (ROOT / top).rglob("*"):
                if f.is_file() and f.resolve() != me and f.suffix in {".njk", ".js", ".mjs", ".py", ".json", ".yml", ".yaml",
                                                                        ".css", ".html", ".txt"}:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    hits += [f"{f.relative_to(ROOT)}: {n}" for n in GONE if n in text]
        hits += [f"eleventy.config.js: {n}" for n in GONE if n in read("eleventy.config.js")]
        self.assertEqual(hits, [])


# ------------------------------------------------------------------------------------------------------ Script
class Script(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.M = load_script()

    def run_script(self, *args: str) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="gv-r37-icons-")
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        with mock.patch.object(self.M, "OUT", out), redirect_stdout(io.StringIO()):
            self.M.main(list(args))
        return out

    def test_favicons_writes_the_favicons_only(self):
        out = self.run_script("favicons")
        written = sorted(p.name for p in out.iterdir())
        self.assertEqual(written, sorted([*self.M.FAVICON_JOBS, "favicon.ico", "favicon.svg"]))
        self.assertEqual(set(written) & set(self.M.APP_JOBS), set(), "the five app icons are never drawn again")
        self.assertEqual(set(self.M.APP_JOBS), {"app-icon-192.png", "app-icon-512.png", "app-icon-maskable-192.png",
                                                "app-icon-maskable-512.png", "apple-touch-icon-180.png"})
        # …and draws what is committed
        self.assertEqual((out / "favicon.svg").read_bytes(), (IMG / "favicon.svg").read_bytes())
        for name in PNGS:
            with self.subTest(name=name), Image.open(out / name) as new, Image.open(IMG / name) as old:
                self.assertLessEqual(mean_diff(new, old), 1.0)
        new, old = frames(out / "favicon.ico"), frames(IMG / "favicon.ico")
        self.assertEqual(set(new), set(old))
        for size in new:
            with self.subTest(ico=size):
                self.assertLessEqual(mean_diff(new[size], old[size]), 1.0)

    def test_the_16px_picture_is_the_bolder_mark(self):
        self.assertEqual(self.M.FAVICON_ICO[0][0], 16)
        self.assertIs(self.M.FAVICON_ICO[0][2], self.M.SMALL)
        self.assertIs(self.M.FAVICON_SVG["shape"], self.M.SMALL)
        self.assertLess(len(self.M.SMALL.grapes), len(self.M.FULL.grapes))
        self.assertGreater(self.M.SMALL.r, self.M.FULL.r)
        # its own picture in the ICO, not the 48 px one made smaller
        ico = frames(IMG / "favicon.ico")
        shrunk = ico[(48, 48)].resize((16, 16), Image.LANCZOS)
        self.assertGreater(mean_diff(ico[(16, 16)], shrunk), 4.0)

    def test_an_unknown_argument_stops_before_writing(self):
        tmp = tempfile.TemporaryDirectory(prefix="gv-r37-icons-")
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(self.M, "OUT", Path(tmp.name)), self.assertRaises(SystemExit):
            self.M.main(["favicon"])
        self.assertEqual(list(Path(tmp.name).iterdir()), [])


# ------------------------------------------------------------------------------------------------------ Templates
class Templates(unittest.TestCase):
    def test_every_rel_icon_names_a_grape_file(self):
        seen = 0
        for f in sorted((ROOT / "src").rglob("*")):
            if f.suffix not in {".njk", ".js", ".html", ".md"} or not f.is_file():
                continue
            for rel, _sizes, _type, href in icon_links(f.read_text(encoding="utf-8")):
                seen += 1
                with self.subTest(file=str(f.relative_to(ROOT)), href=href):
                    self.assertNotIn("logo-", href or "")
                    self.assertRegex(href or "", r"^/(?:favicon\.|assets/img/(?:favicon-|app-icon-|apple-touch-icon-))")
                    if rel == "icon":
                        self.assertRegex(href, GRAPE)
        self.assertGreaterEqual(seen, len(LINKS))

    def test_base_and_the_stand_alone_pages_take_the_partial(self):
        include = '{% include "partials/icon-links.njk" %}'
        base = read("src", "_includes", "layouts", "base.njk")
        self.assertEqual(base.count(include), 1)
        self.assertEqual(icon_links(base), [], "no icon link of its own")
        # a page that writes its own <head> (layout: false), not one that only says the word in a comment
        alone = [f for f in sorted((ROOT / "src" / "pages").glob("*.njk"))
                 if re.search(r"^<head>\s*$", f.read_text(encoding="utf-8"), re.M)]
        names = {f.name for f in alone}
        for name in ("announcements-redirect.njk", "app-redirect.njk", "districts-redirect.njk", "documents-redirect.njk",
                     "expenses-redirect.njk", "subscribe-redirect.njk", "meeting.njk", "monthly-past.njk"):
            self.assertIn(name, names)
        for f in alone:
            with self.subTest(page=f.name):
                text = f.read_text(encoding="utf-8")
                self.assertEqual(text.count(include), 1)
                self.assertLess(text.index(include), text.index("</head>"))
                self.assertEqual(icon_links(text), [])

    def test_the_partial(self):
        links = icon_links(read("src", "_includes", "partials", "icon-links.njk"))
        self.assertEqual(links, LINKS)
        with Image.open(IMG / "favicon.ico") as ico:
            self.assertEqual(LINKS[0][1], " ".join(f"{w}x{h}" for w, h in sorted(ico.info["sizes"])))
        for rel, sizes, typ, href in links:
            with self.subTest(href=href):
                src = ROOT / ROOT_COPIES[href[1:]] if href[1:] in ROOT_COPIES else ROOT / "src" / href[1:]
                self.assertTrue(src.is_file(), src)
                if typ == "image/png":
                    with Image.open(src) as im:
                        self.assertEqual(sizes, f"{im.size[0]}x{im.size[1]}")
        tags = [line for line in PARTIAL.read_text(encoding="utf-8").splitlines() if line.startswith("<link")]
        self.assertEqual(len(tags), len(LINKS))
        self.assertFalse([t for t in tags if "?" in t], "no ?v=: Google wants an address that stays")

    def test_the_root_copies_come_from_src_assets(self):
        cfg = read("eleventy.config.js")
        self.assertNotIn('"src/favicon.ico"', cfg)
        for out, src in ROOT_COPIES.items():
            with self.subTest(out=out):
                self.assertRegex(cfg, rf'"(?:\./)?{re.escape(src)}": "{re.escape(out)}"')
                self.assertTrue(src.startswith("src/assets/img/"), "under a root of build.version (src/_data/build.js)")
        self.assertIn('path.join("src", "assets")', read("src", "_data", "build.js"))

    def test_opensearch_the_feeds_the_digest_and_the_worker(self):
        self.assertIn('<Image width="32" height="32" type="image/png">${x(abs("/assets/img/favicon-32.png"))}</Image>',
                      read("src", "pages", "opensearch.11ty.js"))
        feed = read("src", "pages", "feed.11ty.js")
        image = feed[feed.index('out.push("<image>");'):feed.index('out.push("</image>");')]
        self.assertIn('abs(site, "/assets/img/favicon-96.png")', image)
        self.assertIn('out.push("<width>96</width>");', image)
        self.assertIn('out.push("<height>96</height>");', image)
        digest = read("scripts", "notify", "send_digest.py")
        self.assertIn('logo = links.base + "/assets/img/apple-touch-icon-180.png"', digest)
        self.assertNotIn('"/assets/img/logo-180x180.png"', digest)
        sw = read("src", "pages", "sw.11ty.js")
        shell = re.search(r"const shell = \[(.*?)\];", sw, re.S).group(1)
        for f in ("favicon.ico", "favicon.svg", "assets/img/favicon-48.png", "assets/img/app-icon-192.png",
                  "assets/img/logo-wide.png"):
            self.assertIn(f'a("{f}")', shell)
        self.assertNotIn("logo-32x32", shell)


# ------------------------------------------------------------------------------------------------------ Built
BUILD_JS = r"""
process.env.ONLY = input.only;
const os = await import("node:os");
const crypto = await import("node:crypto");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r37-icons-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  // the folder given here wins over eleventy.config.js's "_site" (as --output does): never into the checkout
  elev.directories.freeze();
  await elev.write();
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true })
    .flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
  const files = walk(dir).map((f) => path.relative(dir, f).split(path.sep).join("/"));
  const text = {};
  for (const f of files) if (/\.(html|xml)$/.test(f) || f === "sw.js") text[f] = fs.readFileSync(path.join(dir, f), "utf8");
  const sha = {};
  for (const f of input.hash) if (fs.existsSync(path.join(dir, f))) sha[f] = crypto.createHash("sha256").update(fs.readFileSync(path.join(dir, f))).digest("hex");
  out({ files, text, sha });
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
ONLY = ("index.njk,404,announcements-redirect,app-redirect,districts-redirect,documents-redirect,expenses-redirect,"
        "subscribe-redirect,meeting.njk,monthly-past,opensearch,feed,sw.")
PREFIX = "/aagrapevine"


class Built(unittest.TestCase):
    built: dict | None = None

    def build(self) -> dict:
        if Built.built is None:
            hashes = [*ROOT_COPIES, *(f"assets/img/{n}" for n in PNGS)]
            Built.built = run_js(self, BUILD_JS, data={"only": ONLY, "hash": hashes}, timeout=600,
                                 env={"PATH_PREFIX": PREFIX + "/", "STRICT_BUILD": "", "LASTMOD": "", "BUILD_WARNINGS": "",
                                      "GITHUB_ACTIONS": ""})
        return Built.built

    def pages(self) -> dict[str, str]:
        return {f: t for f, t in self.build()["text"].items() if f.endswith(".html")}

    def test_every_page_has_the_six_icon_links(self):
        pages = self.pages()
        for want in ("index.html", "es/index.html", "404.html", "es/404.html", "meeting/index.html", "app/index.html",
                     "subscribe/index.html", "es/documents/index.html"):
            self.assertIn(want, pages)
        expected = [(rel, sizes, typ, PREFIX + href) for rel, sizes, typ, href in LINKS]
        for f, page in pages.items():
            with self.subTest(page=f):
                head = page.split("</head>")[0]
                self.assertEqual(icon_links(head), expected)
                self.assertNotIn("logo-32x32", page)
                self.assertNotIn("logo-192x192", page)
        # the header keeps the NETA 65 wordmark
        self.assertIn(f'<img src="{PREFIX}/assets/img/logo-wide.png" alt="NETA 65"', pages["index.html"].split("</header>")[0])

    def test_the_root_copies(self):
        r = self.build()
        for out, src in ROOT_COPIES.items():
            with self.subTest(out=out):
                self.assertIn(out, r["files"])
                self.assertEqual(r["sha"][out], hashlib.sha256((ROOT / src).read_bytes()).hexdigest())
        for name in PNGS:
            self.assertIn(f"assets/img/{name}", r["files"])
        for name in GONE:
            self.assertNotIn(f"assets/img/{name}.png", r["files"])

    def test_opensearch_and_the_feeds_name_built_grape_files(self):
        r = self.build()
        for prefix in ("", "es/"):
            with self.subTest(lang=prefix or "en"):
                os_xml = ET.fromstring(r["text"][f"{prefix}opensearch.xml"].encode("utf-8"))
                img = os_xml.find("{http://a9.com/-/spec/opensearch/1.1/}Image")
                self.assertTrue(img.text.endswith("/assets/img/favicon-32.png"), img.text)
                rss = ET.fromstring(r["text"][f"{prefix}feed.xml"].encode("utf-8"))
                image = rss.find("channel/image")
                self.assertTrue(image.findtext("url").endswith("/assets/img/favicon-96.png"), image.findtext("url"))
                self.assertEqual((image.findtext("width"), image.findtext("height")), ("96", "96"))
                # RSS 2.0: url, title, link, then width and height
                self.assertEqual([c.tag for c in image], ["url", "title", "link", "width", "height"])
        sw = r["text"]["sw.js"]
        for f in ("favicon.ico", "favicon.svg", "assets/img/favicon-48.png"):
            self.assertIn(f'"{PREFIX}/{f}"', sw)
            self.assertIn(f, r["files"])
        self.assertNotIn("logo-32x32", sw)


# ------------------------------------------------------------------------------------------------------ Version
VERSION_JS = r"""
const build = await imp("src/_data/build.js");
const os = await import("node:os");
const home = process.cwd();
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r37-version-"));
const put = (p, s) => { fs.mkdirSync(path.dirname(path.join(dir, p)), { recursive: true }); fs.writeFileSync(path.join(dir, p), s); };
try {
  for (const [p, s] of Object.entries(input)) put(p, s);
  process.chdir(dir);
  const v = () => build.default().version;
  const before = v();
  put("data/site/events.json", '{"items": [1]}');
  const data = v();
  put("src/assets/img/favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48"/></svg>');
  const svg = v();
  put("src/assets/img/favicon.ico", "another drawing");
  const ico = v();
  out({ before, data, svg, ico });
} finally {
  process.chdir(home);
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class Version(unittest.TestCase):
    def test_a_new_icon_is_a_new_version(self):
        files = {"src/assets/img/favicon.svg": "<svg/>", "src/assets/img/favicon.ico": "ico", "src/pages/index.njk": "home",
                 "eleventy.config.js": "config", "data/site/events.json": '{"items": []}'}
        r = run_js(self, VERSION_JS, data=files, needs_modules=False, env={"GITHUB_SHA": ""})
        self.assertRegex(r["before"], r"^[0-9a-f]{10}$")
        self.assertEqual(r["data"], r["before"], "the synced data never changes it")
        self.assertNotEqual(r["svg"], r["before"], "a new favicon.svg changes it")
        self.assertNotEqual(r["ico"], r["svg"], "a new favicon.ico changes it")


if __name__ == "__main__":
    unittest.main()
