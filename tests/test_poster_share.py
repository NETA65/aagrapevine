"""The monthly posters' share pictures and the browser tooling behind them and the browser checks — offline:

  * MonthPages      — the /monthly/YYYY-MM/ pages, built for real (Eleventy, only those pages): their preview picture
                      (og:image, twitter:image) is their own share.png — 1200 × 630, with words in the page language,
                      ?v= from the poster — only in a build asked for it (POSTER_SHARE=1); every other build keeps the
                      committee's card;
  * Filter          — mpShareImage / sharePicturePath / posterShareOn / shareVersioned (eleventy/filters/monthly.js:
                      the picture's address changes exactly when the poster or the code that draws it does);
  * PosterScript    — scripts/ops/poster_share.py: which pages want a picture, the PNG size check, and its exit
                      codes: 0 when every picture was made (or none is wanted), 1 — with none left behind — when one
                      could not be;
  * UpdateWorkflow  — Website update's build job: the build with POSTER_SHARE=1, the pictures (never stopping the
                      deploy), and the build again without the flag when they could not be made — all before the
                      build is checked and uploaded;
  * CodeCheck       — the Code check runs the browser checks (tests/browser) on its test build, in the runner's
                      Chrome, a missing browser failing; the browser checks are skipped in the normal test run;
  * Server          — scripts/ops/serve_site.mjs through scripts/ops/site_browser.SiteServer: the site under its
                      folder as GitHub Pages serves it (index pages, 301s, the 404 page, byte ranges, nothing
                      outside the folder or the site) and the overrides a check uses (another file, a slow page);
  * Launch          — site_browser.launch: the first browser that starts (Chrome, Edge, Playwright's Chromium, or
                      GV_BROWSER_CHANNEL), never reaching another site.

    python -m unittest tests.test_poster_share -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import http.client
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import node_path, run_js  # noqa: E402
from scripts.ops import poster_share as P  # noqa: E402
from scripts.ops import site_browser as B  # noqa: E402

PNG_1200 = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 1200, 630) + b"\x08\x06\x00\x00\x00"


def steps_of(job: dict) -> list[dict]:
    return job.get("steps", [])


def step(job: dict, name: str) -> dict:
    found = [s for s in steps_of(job) if s.get("name") == name]
    assert len(found) == 1, f"one step named {name!r}"
    return found[0]


# ------------------------------------------------------------------------------------------------ the month pages
MONTH_PAGES_JS = r"""
process.env.ONLY = "monthly-month";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const res = {};
for (const flag of ["", "1"]) {
  process.env.POSTER_SHARE = flag;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-poster-share-"));
  try {
    const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
    const pages = (await elev.toJSON()).filter((p) => /\/monthly\/\d{4}-\d{2}\/$/.test(p.url));
    res[flag || "off"] = pages.map((p) => ({ url: p.url,
      meta: Object.fromEntries([...p.content.matchAll(/<meta (?:property|name)="((?:og|twitter):image(?::\w+)?)" content="([^"]*)">/g)]
        .map((m) => [m[1], m[2]])) }));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
delete process.env.POSTER_SHARE;
out(res);
"""


class MonthPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def pages(self) -> dict:
        if MonthPages.r is None:
            MonthPages.r = run_js(self, MONTH_PAGES_JS, timeout=600)
        return MonthPages.r

    def test_only_a_build_asked_for_it_points_at_the_pictures(self):
        r = self.pages()
        self.assertEqual(len(r["off"]), len(r["1"]))
        self.assertGreaterEqual(len(r["1"]), 26, "13 months × English and Spanish")
        for page in r["off"]:
            with self.subTest(build="without POSTER_SHARE", page=page["url"]):
                card = "og-default-es.png?v=2" if page["url"].startswith("/es/") else "og-default.png?v=2"
                self.assertTrue(page["meta"]["og:image"].endswith("/assets/img/" + card), page["meta"])
                self.assertEqual((page["meta"]["og:image:width"], page["meta"]["og:image:height"]), ("1200", "630"))
                self.assertNotIn("share.png", json.dumps(page["meta"]))
        versions = set()
        for page in r["1"]:
            with self.subTest(build="POSTER_SHARE=1", page=page["url"]):
                m = page["meta"]
                # ?v=: from the poster (monthly.js shareVersioned) — a link preview that keeps a picture by its address
                # fetches the new one once the poster changes
                self.assertRegex(m["og:image"], r"^https://[^\s\"?]+/(?:es/)?monthly/\d{4}-\d{2}/share\.png\?v=[0-9a-f]{8}$")
                self.assertTrue(m["og:image"].split("?")[0].endswith(page["url"] + "share.png"), "its own picture, beside the page")
                self.assertEqual(m["twitter:image"], m["og:image"])
                self.assertEqual((m["og:image:width"], m["og:image:height"]), ("1200", "630"))
                self.assertEqual(m["twitter:image:alt"], m["og:image:alt"])
                versions.add(m["og:image"].split("?v=")[1])
        self.assertEqual(len(versions), len(r["1"]), "each poster its own version")
        # the words, in the page language (the month in lower case inside the Spanish sentence; escaped once)
        en = {p["url"]: p["meta"]["og:image:alt"] for p in r["1"]}
        oct_en = next(a for u, a in en.items() if u.startswith("/monthly/"))
        self.assertRegex(html.unescape(oct_en), r"^The [A-Z][a-z]+ \d{4} poster of the Grapevine & La Viña committee, "
                                                r"NETA 65 — Carry the message$")
        self.assertIn("&amp; La Viña", oct_en)
        self.assertNotIn("&amp;amp;", oct_en)
        es = next(a for u, a in en.items() if u.startswith("/es/monthly/"))
        self.assertRegex(es, r"^El cartel de [a-z]+ de \d{4} del comité de La Viña y Grapevine, NETA 65 — Lleva el mensaje$")


class Filter(unittest.TestCase):
    def test_the_flag_and_the_path(self):
        r = run_js(self, r"""
const M = await imp("eleventy/filters/monthly.js");
const flags = {};
for (const v of ["1", "true", "TRUE", " 1 ", "", "0", "yes", "false"]) flags[v] = M.posterShareOn({ POSTER_SHARE: v });
const filter = (env) => { if (env === undefined) delete process.env.POSTER_SHARE; else process.env.POSTER_SHARE = env;
  return [filters.mpShareImage("2026-10", "en"), filters.mpShareImage("2026-10", "es"), filters.mpShareImage("../x", "en")]; };
out({ flags, none: M.posterShareOn({}), path: [M.sharePicturePath("2027-01", "en"), M.sharePicturePath("2027-01", "es")],
      on: filter("1"), off: filter(undefined) });
""")
        self.assertEqual(r["flags"], {"1": True, "true": True, "TRUE": True, " 1 ": True, "": False, "0": False,
                                      "yes": False, "false": False})
        self.assertFalse(r["none"])
        self.assertEqual(r["path"], ["/monthly/2027-01/share.png", "/es/monthly/2027-01/share.png"])
        self.assertEqual(r["on"], ["/monthly/2026-10/share.png", "/es/monthly/2026-10/share.png", ""],
                         "a site path (base.njk adds the address and the folder); only a month's key")
        self.assertEqual(r["off"], ["", "", ""])

    def test_the_pictures_address_follows_the_poster(self):
        # Round-7 review: the address never changed, so Facebook, Messenger, Slack… kept showing the first picture they
        # fetched after the month's dates, deadlines or themes changed. shareVersioned (the mpShareVersion transform):
        # ?v= from the poster's HTML and the code's version — a new address exactly when the picture can change
        r = run_js(self, r"""
const M = await imp("eleventy/filters/monthly.js");
const page = (poster, code = "c0ffee1234", img = "https://example.org/site/es/monthly/2026-10/share.png") =>
  `<html><head><link rel="stylesheet" href="/site/assets/css/main.css?v=${code}">` +
  `<meta property="og:image" content="${img}"><meta property="og:image:width" content="1200">` +
  `<meta name="twitter:image" content="${img}"></head><body><main><p>Nov 3</p>` +
  (poster === null ? "" : `<article class="mp-poster mp-l-cork" lang="es" aria-labelledby="t" data-mp-poster><h2 id="t">Octubre</h2>${poster}</article>`) +
  `<section>${poster === null ? "" : "toolkit"}</section></main></body></html>`;
const ver = (html) => [...html.matchAll(/<meta (?:property|name)="(?:og|twitter):image" content="([^"]*)">/g)].map((m) => m[1]);
const a = M.shareVersioned(page("<p>Oct 3 · Taller</p>"));
out({
  a: ver(a), same: ver(M.shareVersioned(page("<p>Oct 3 · Taller</p>"))),
  moved: ver(M.shareVersioned(page("<p>Oct 10 · Taller</p>"))),             // an event moved: another picture
  code: ver(M.shareVersioned(page("<p>Oct 3 · Taller</p>", "deadbeef00"))),  // the styles that draw it changed
  again: ver(M.shareVersioned(a)),                                           // (once only)
  noPoster: M.shareVersioned(page(null)) === page(null),
  card: (() => { const h = page("<p>Oct 3</p>", "c0ffee1234", "https://example.org/site/assets/img/og-default-es.png?v=2"); return M.shareVersioned(h) === h; })(),
  rest: a.replace(/share\.png\?v=[0-9a-f]{8}"/g, 'share.png"') === page("<p>Oct 3 · Taller</p>"),
});
""")
        v = lambda urls: {u.split("?v=")[1] for u in urls}
        self.assertEqual(len(r["a"]), 2)
        self.assertRegex(r["a"][0], r"^https://example\.org/site/es/monthly/2026-10/share\.png\?v=[0-9a-f]{8}$")
        self.assertEqual(r["a"][0], r["a"][1], "og:image and twitter:image: the same address")
        self.assertEqual(r["same"], r["a"])                               # the same poster: the same address
        self.assertNotEqual(v(r["moved"]), v(r["a"]))
        self.assertNotEqual(v(r["code"]), v(r["a"]))
        self.assertEqual(r["again"], r["a"])
        self.assertTrue(r["noPoster"])
        self.assertTrue(r["card"])                                        # the committee's card keeps its own ?v=2
        self.assertTrue(r["rest"], "nothing else on the page changes")


# ------------------------------------------------------------------------------------------------ the script
def page(og: str) -> str:
    return f'<!doctype html><html><head><meta property="og:image" content="{og}"></head><body></body></html>'


class PosterScript(unittest.TestCase):
    def setUp(self):
        self.site = Path(tempfile.mkdtemp(prefix="gv-share-site-"))
        self.addCleanup(shutil.rmtree, self.site, True)
        base = "https://neta65.github.io/aagrapevine"
        for rel, og in (("monthly/2026-10/", f"{base}/monthly/2026-10/share.png?v=0a1b2c3d"),   # (its version: any)
                        ("es/monthly/2026-10/", f"{base}/es/monthly/2026-10/share.png"),
                        ("monthly/2026-11/", f"{base}/monthly/2026-10/share.png"),       # another month's: not its own
                        ("monthly/2025-10/", f"{base}/assets/img/og-default.png?v=2"),   # a past month's redirect page
                        ("monthly/", f"{base}/assets/img/og-default.png?v=2")):
            (self.site / rel).mkdir(parents=True, exist_ok=True)
            (self.site / rel / "index.html").write_text(page(og), encoding="utf-8")
        self.summary = self.site / "summary.md"
        self.env = mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(self.summary)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_main(self, make) -> tuple[int, str]:
        buf = io.StringIO()
        with mock.patch.object(P, "make", make), redirect_stdout(buf):
            code = P.main([str(self.site)])
        return code, buf.getvalue()

    def test_the_pages_that_want_a_picture(self):
        self.assertEqual(P.wanted(self.site), [("monthly/2026-10/", self.site / "monthly" / "2026-10" / "share.png"),
                                               ("es/monthly/2026-10/", self.site / "es" / "monthly" / "2026-10" / "share.png")])
        # a build made without POSTER_SHARE: none
        for f in self.site.rglob("index.html"):
            f.write_text(page("https://neta65.github.io/aagrapevine/assets/img/og-default.png?v=2"), encoding="utf-8")
        self.assertEqual(P.wanted(self.site), [])
        code, out = self.run_main(lambda *a, **k: self.fail("nothing to make"))
        self.assertEqual(code, 0)
        self.assertIn("::notice title=Share pictures::No month page asks for a share picture", out)

    def test_every_picture_made(self):
        def make(site, todo, channel=None):
            self.assertEqual([r for r, _o in todo], ["monthly/2026-10/", "es/monthly/2026-10/"])
            for _rel, out in todo:
                out.write_bytes(PNG_1200)
            return []
        code, _out = self.run_main(make)
        self.assertEqual(code, 0)
        self.assertTrue((self.site / "es" / "monthly" / "2026-10" / "share.png").is_file())
        self.assertEqual(self.summary.read_text(encoding="utf-8"),
                         "**Share pictures of the monthly posters:** 2 (1200 × 630).\n")

    def test_one_that_could_not_be_made_leaves_none(self):
        def make(site, todo, channel=None):
            for _rel, out in todo:
                out.write_bytes(PNG_1200)
            return ["es/monthly/2026-10/: the poster is 0 x 0, not 1080 x 1350"]
        code, out = self.run_main(make)
        self.assertEqual(code, 1, "the workflow builds the site again without the flag")
        self.assertEqual(list(self.site.rglob("share.png")), [], "no picture is left behind")
        self.assertIn("::warning title=Share pictures not made::es/monthly/2026-10/: the poster is 0 x 0", out)
        self.assertIn("not made (es/monthly/2026-10/: the poster is 0 x 0", self.summary.read_text(encoding="utf-8"))

    def test_no_playwright_or_no_browser(self):
        for err in (ImportError("No module named 'playwright'"), B.BrowserMissing("no browser could be started — chrome: x")):
            with self.subTest(err=type(err).__name__):
                def make(site, todo, channel=None, err=err):
                    raise err
                code, out = self.run_main(make)
                self.assertEqual(code, 1)
                self.assertIn(f"::warning title=Share pictures not made::{type(err).__name__}: ", out)

    def test_the_picture_size(self):
        f = self.site / "x.png"
        f.write_bytes(PNG_1200)
        self.assertEqual(P.png_size(f), (1200, 630))
        f.write_bytes(b"GIF89a" + b"\0" * 30)
        self.assertEqual(P.png_size(f), (0, 0))
        self.assertEqual((P.WIDTH, P.HEIGHT, P.CLIP_H), (1200, 630, 567), "the top of the poster, drawn at 10/9")
        self.assertAlmostEqual(P.POSTER_W * P.SCALE, P.WIDTH)
        self.assertAlmostEqual(P.CLIP_H * P.SCALE, P.HEIGHT)


# ------------------------------------------------------------------------------------------------ the workflows
class UpdateWorkflow(unittest.TestCase):
    def setUp(self):
        self.job = yaml.safe_load((WF / "update.yml").read_text(encoding="utf-8"))["jobs"]["build-deploy"]
        self.names = [s.get("name") for s in steps_of(self.job)]

    def test_the_pictures_after_the_build_never_stopping_a_deploy(self):
        build = step(self.job, "Build the website")
        py = step(self.job, "Set up Python (for the posters' share pictures)")
        make = step(self.job, "Make the monthly posters' share pictures")
        again = step(self.job, "Build the website again without the share pictures (only when they could not be made)")
        order = [self.names.index(s["name"]) for s in (build, py, make, again)]
        self.assertEqual(order, list(range(order[0], order[0] + 4)), "right after the build, one after the other")
        self.assertLess(order[-1], self.names.index("Check the build"))
        self.assertLess(self.names.index("Check the build"), self.names.index("Upload the website"))
        # the build points the month pages at their pictures
        self.assertEqual(build["env"]["POSTER_SHARE"], "1")
        self.assertEqual(build["run"], "npx @11ty/eleventy")
        # Python and the pinned Playwright, here only; any failure is the picture step's, never the job's
        self.assertTrue(py["uses"].startswith("actions/setup-python@"))
        self.assertIs(py["continue-on-error"], True)
        self.assertEqual(py["with"]["cache-dependency-path"], "scripts/ops/requirements-browser.txt")
        self.assertEqual((make["id"], make["continue-on-error"]), ("posters", True))
        self.assertLessEqual(make["timeout-minutes"], 10)
        booth = sum(s.get("timeout-minutes", 0) for s in steps_of(self.job) if "booth display" in str(s.get("name")))
        self.assertGreaterEqual(self.job["timeout-minutes"], booth + make["timeout-minutes"] + 8,
                                "the booth's media, the pictures, two builds and the upload fit in the job")
        self.assertIn("python -m pip install -r scripts/ops/requirements-browser.txt", make["run"])
        self.assertIn("python -m scripts.ops.poster_share _site", make["run"])
        self.assertLess(make["run"].index("pip install"), make["run"].index("scripts.ops.poster_share"))
        # without them: the same build, without the flag — so no page points at a missing picture
        self.assertEqual(again["if"], "${{ success() && steps.posters.outcome != 'success' }}")
        self.assertEqual(again["env"], {k: v for k, v in build["env"].items() if k != "POSTER_SHARE"})
        self.assertNotIn("continue-on-error", again, "a site that cannot be built at all is not published")
        run = again["run"]
        self.assertLess(run.index("find _site -path '*/monthly/*/share.png' -delete"), run.index("npx @11ty/eleventy"))

    def test_the_rebuild_takes_away_only_the_pictures(self):
        bash = shutil.which("bash")
        if not bash or not shutil.which("find"):
            self.skipTest("needs bash and find")
        tmp = Path(tempfile.mkdtemp(prefix="gv-share-rebuild-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for f in ("_site/monthly/2026-10/share.png", "_site/es/monthly/2026-10/share.png", "_site/monthly/2026-10/index.html",
                  "_site/assets/img/share.png", "_site/monthly/poster.png"):
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            (tmp / f).write_bytes(b"x")
        line = next(ln.strip() for ln in step(self.job, "Build the website again without the share pictures (only when "
                                                         "they could not be made)")["run"].splitlines() if ln.strip().startswith("find "))
        r = subprocess.run([bash, "-c", line], cwd=tmp, capture_output=True, text=True,
                           env={**os.environ, "MSYS_NO_PATHCONV": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        left = sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*") if p.is_file())
        self.assertEqual(left, ["_site/assets/img/share.png", "_site/monthly/2026-10/index.html", "_site/monthly/poster.png"])


class CodeCheck(unittest.TestCase):
    def test_the_browser_checks_run_on_the_test_build(self):
        job = yaml.safe_load((WF / "check.yml").read_text(encoding="utf-8"))["jobs"]["build"]
        names = [s.get("name") for s in steps_of(job)]
        py = step(job, "Set up Python (for the browser checks)")
        install = step(job, "Install the browser checks' tools (Playwright, for the runner's Chrome)")
        run = step(job, "Browser checks (focus ring, sticky bar, large text, offline update, script errors)")
        at = names.index("Check the build")
        self.assertEqual([names.index(s["name"]) for s in (py, install, run)], [at + 1, at + 2, at + 3])
        self.assertEqual(py["with"]["cache-dependency-path"], "scripts/ops/requirements-browser.txt")
        self.assertEqual(install["run"], "python -m pip install -r scripts/ops/requirements-browser.txt")
        self.assertEqual(run["env"], {"GV_BROWSER_SITE": "_site", "GV_BROWSER_CHANNEL": "chrome", "GV_BROWSER_REQUIRED": "1"})
        self.assertEqual(run["run"], "python -m unittest discover -s tests/browser -t tests -v")
        self.assertNotIn("continue-on-error", run)
        # the build they check is the GitHub Pages one (its folder), the same as Website update's
        build = step(job, "Build the website (as for GitHub Pages)")
        self.assertIn("PATH_PREFIX", build["env"])

    def test_skipped_in_the_normal_test_run(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GV_BROWSER_")}
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests/browser", "-t", "tests"], cwd=ROOT,
                           env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertRegex(r.stderr, r"OK \(skipped=\d+\)")
        self.assertTrue((ROOT / "tests" / "browser" / "__init__.py").is_file(), "found by `discover -s tests`")


# ------------------------------------------------------------------------------------------------ the server
class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = Path(tempfile.mkdtemp(prefix="gv-serve-"))
        (cls.site / "assets" / "css").mkdir(parents=True)
        (cls.site / "about").mkdir()
        (cls.site / "index.html").write_text('<link rel="stylesheet" href="/aagrapevine/assets/css/main.css?v=1">home',
                                             encoding="utf-8")
        (cls.site / "404.html").write_text("not found page", encoding="utf-8")
        (cls.site / "about" / "index.html").write_text("about", encoding="utf-8")
        (cls.site / "assets" / "css" / "main.css").write_text("body{}", encoding="utf-8")
        (cls.site / "big.txt").write_bytes(bytes(range(256)) * 4)
        (cls.site.parent / (cls.site.name + "-secret.txt")).write_text("secret", encoding="utf-8")
        cls.other = cls.site.parent / (cls.site.name + "-sw.js")
        cls.other.write_text("// the next version", encoding="utf-8")
        cls.overrides = cls.site.parent / (cls.site.name + "-overrides.json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.site, True)
        for f in (cls.site.parent / (cls.site.name + "-secret.txt"), cls.other, cls.overrides):
            f.unlink(missing_ok=True)

    def setUp(self):
        if not node_path():
            self.skipTest("Node.js is not installed")
        self.overrides.unlink(missing_ok=True)

    def get(self, server: B.SiteServer, path: str, headers: dict | None = None):
        port = int(re.search(r":(\d+)/", server.url).group(1))
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        try:
            c.request("GET", path, headers=headers or {})
            r = c.getresponse()
            return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
        finally:
            c.close()

    def test_like_github_pages(self):
        self.assertEqual(B.site_prefix(self.site), "/aagrapevine/", "read off the home page's stylesheet")
        with B.SiteServer(self.site) as s:
            self.assertRegex(s.url, r"^http://127\.0\.0\.1:\d+/aagrapevine/$")
            self.assertEqual(s.address("/about/"), s.url + "about/")
            status, head, body = self.get(s, "/aagrapevine/")
            self.assertEqual((status, body[-4:], head["cache-control"]), (200, b"home", "no-store"))
            self.assertEqual(head["content-type"], "text/html; charset=utf-8")
            self.assertEqual(self.get(s, "/aagrapevine")[:2][0], 301)
            status, head, _ = self.get(s, "/aagrapevine/about")
            self.assertEqual((status, head["location"]), (301, "/aagrapevine/about/"))
            self.assertEqual(self.get(s, "/aagrapevine/about/")[2], b"about")
            self.assertEqual(self.get(s, "/aagrapevine/nothing/")[::2], (404, b"not found page"))
            self.assertEqual(self.get(s, "/elsewhere/")[0], 404, "nothing outside the site's folder")
            for sneaky in ("/aagrapevine/%2e%2e/", "/aagrapevine/..%5C", "/aagrapevine/..%2F"):
                with self.subTest(sneaky):
                    status, _head, body = self.get(s, sneaky + self.site.name + "-secret.txt")
                    self.assertIn(status, (403, 404), "nothing outside the built site")
                    self.assertNotIn(b"secret", body)
            status, head, body = self.get(s, "/aagrapevine/big.txt", {"Range": "bytes=10-19"})
            self.assertEqual((status, head["content-range"], body), (206, "bytes 10-19/1024", bytes(range(10, 20))))
            self.assertEqual(self.get(s, "/aagrapevine/big.txt", {"Range": "bytes=5000-"})[0], 416)

    def test_the_overrides_a_check_uses(self):
        with B.SiteServer(self.site, overrides=self.overrides) as s:
            self.assertEqual(self.get(s, "/aagrapevine/about/")[2], b"about", "no file: nothing changed")
            self.overrides.write_text(json.dumps({"files": {"/aagrapevine/sw.js": str(self.other)},
                                                  "delay_ms": {"/aagrapevine/about/": 1200}}), encoding="utf-8")
            status, head, body = self.get(s, "/aagrapevine/sw.js")
            self.assertEqual((status, body, head["content-type"]), (200, b"// the next version", "text/javascript; charset=utf-8"))
            t0 = time.monotonic()
            self.assertEqual(self.get(s, "/aagrapevine/about/")[2], b"about")
            self.assertGreaterEqual(time.monotonic() - t0, 1.1, "held as asked")
            t0 = time.monotonic()
            self.get(s, "/aagrapevine/")
            self.assertLess(time.monotonic() - t0, 1.0, "only that page")
            self.overrides.write_text("{ not json", encoding="utf-8")
            self.assertEqual(self.get(s, "/aagrapevine/sw.js")[0], 404, "an unreadable file: no overrides")

    def test_never_left_running_when_its_python_is_killed(self):
        # a check or the share pictures stopped halfway (killed, a time limit): the server stops with them
        child = subprocess.Popen(
            [sys.executable, "-c", "import sys, time; sys.path.insert(0, sys.argv[1]); "
             "from scripts.ops.site_browser import SiteServer; s = SiteServer(sys.argv[2]).__enter__(); "
             "print(s.url, flush=True); time.sleep(120)", str(ROOT), str(self.site)],
            stdout=subprocess.PIPE, text=True, encoding="utf-8")
        try:
            served = child.stdout.readline().strip()
            port = int(re.search(r":(\d+)/", served).group(1))
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            c.request("GET", "/aagrapevine/about/")
            self.assertEqual(c.getresponse().read(), b"about", "it serves while its Python runs")
            c.close()
        finally:
            child.kill()
            child.wait(10)
            child.stdout.close()
        stopped = False
        for _ in range(100):
            probe = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                probe.connect()
                probe.close()
            except OSError:
                stopped = True
                break
            time.sleep(0.1)
        self.assertTrue(stopped, "the server stopped with the Python process that started it")

    def test_another_folder_and_a_stopped_server(self):
        with B.SiteServer(self.site, prefix="/") as s:
            self.assertRegex(s.url, r"^http://127\.0\.0\.1:\d+/$")
            self.assertEqual(self.get(s, "/about/")[2], b"about")
        self.assertIsNotNone(s.proc.poll(), "stopped")
        with self.assertRaises(RuntimeError):
            B.SiteServer(self.site / "about" / "nothing").__enter__()


class Launch(unittest.TestCase):
    class Chromium:
        def __init__(self, ok):
            self.ok, self.calls = ok, []

        def launch(self, **kw):
            self.calls.append(kw)
            ch = kw.get("channel", "chromium")
            if ch in self.ok:
                return f"browser:{ch}"
            raise RuntimeError(f"Executable doesn't exist at /opt/{ch}\n  (the rest of Playwright's message)")

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop("GV_BROWSER_CHANNEL", None)

    def test_the_first_browser_that_starts(self):
        pw = SimpleNamespace(chromium=self.Chromium({"msedge", "chromium"}))
        self.assertEqual(B.launch(pw), ("browser:msedge", "msedge"))
        self.assertEqual([c.get("channel") for c in pw.chromium.calls], ["chrome", "msedge"])
        for c in pw.chromium.calls:
            self.assertIs(c["headless"], True)
            self.assertEqual(c["args"], ["--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1"],
                             "no other site is ever reached")
        # Playwright's own Chromium: no channel
        pw = SimpleNamespace(chromium=self.Chromium({"chromium"}))
        self.assertEqual(B.launch(pw), ("browser:chromium", "chromium"))
        self.assertNotIn("channel", pw.chromium.calls[-1])

    def test_the_one_asked_for_or_none(self):
        os.environ["GV_BROWSER_CHANNEL"] = "chrome"
        pw = SimpleNamespace(chromium=self.Chromium({"msedge"}))
        with self.assertRaises(B.BrowserMissing) as e:
            B.launch(pw)
        self.assertEqual(str(e.exception), "no browser could be started — chrome: Executable doesn't exist at /opt/chrome")
        self.assertEqual(len(pw.chromium.calls), 1, "only the one asked for")
        del os.environ["GV_BROWSER_CHANNEL"]
        with self.assertRaises(B.BrowserMissing) as e:
            B.launch(SimpleNamespace(chromium=self.Chromium(set())))
        self.assertEqual(str(e.exception).count("Executable doesn't exist"), 3)


if __name__ == "__main__":
    unittest.main()
