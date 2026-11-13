"""The sitemap's <lastmod> (eleventy/lastmod.js): each page's date is when its CONTENT last changed, worked out from a
fingerprint of its <title>, its description and its <main> against the live site's /lastmod.json.

  * Fingerprint  — the code fingerprint ?v=<10 hex> (and &amp;v=) is left out, a YouTube ?v=<id> is not; an element
                   marked data-lastmod="skip" is left out whole (nested tags of its kind too, a void element alone);
                   data-lastmod="skip:a" leaves out attribute a, or the member a of a <script>'s JSON; runs of white
                   space count as one; the head, the header and the footer never count.
  * Marks        — the texts that move with the clock carry the mark in the templates (the "Updated …" line, the
                   digest's "Prepared on", the Drive-checked line, published.njk's "today", the shop's and the
                   contribute page's countdowns), and two builds of the "Updated …" line a day apart have one
                   fingerprint.
  * Dates        — the same fingerprint keeps its date; a changed or new page gets the build's time; no live
                   lastmod.json (404) → every page the build's time, and every page for IndexNow; an unreadable one →
                   every page the build's time, and NONE for IndexNow; a page that left the sitemap is listed for
                   IndexNow; the live file is read with a fresh ?t= query, 10 s per try, tried again after no answer
                   or a server error, never after a 404 or a 403.
  * Sitemap      — <lastmod> right after <loc> (the schema's order: the sitemaps.org XSD, tests/fixtures/sitemap_xsd/,
                   says so), W3C time to the second, replaced (never doubled) when written again.
  * The hook     — only with LASTMOD=1 (never in an ONLY= build, a rebuild or a build that writes no files): writes
                   lastmod.json and the sitemap, and LASTMOD_CHANGED's list; any error leaves the sitemap as the build
                   wrote it and never fails the build. Also with the real fetch() against a local server.

Skipped without Node.js / the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_lastmod -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import http.server
import json
import re
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
XSD = ROOT / "tests" / "fixtures" / "sitemap_xsd"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<meta name="description" content="{desc}"><link rel="stylesheet" href="/aagrapevine/assets/css/main.css?v={v}">
<link rel="canonical" href="https://x.test/site/about/"></head><body><header>Built {built}</header>
<main id="main">{main}</main><footer>Last updated {built}</footer></body></html>"""


def page(main: str, title: str = "About", desc: str = "What we do", v: str = "cfc1657502", built: str = "today") -> str:
    return PAGE.format(title=title, desc=desc, v=v, built=built, main=main)


def validate(xml: str) -> list[str]:
    """Errors of a sitemap against the sitemaps.org 0.9 schema (+ the xhtml:link alternates); [] = valid."""
    from lxml import etree
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    wrap = etree.fromstring(
        '<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="urn:wrap">'
        f'<xsd:import namespace="http://www.sitemaps.org/schemas/sitemap/0.9" schemaLocation="{(XSD / "sitemap.xsd").as_uri()}"/>'
        f'<xsd:import namespace="http://www.w3.org/1999/xhtml" schemaLocation="{(XSD / "xhtml-link.xsd").as_uri()}"/>'
        "</xsd:schema>", parser, base_url=XSD.as_uri() + "/")
    schema = etree.XMLSchema(wrap)
    ok = schema.validate(etree.fromstring(xml.encode("utf-8"), parser))
    return [] if ok else [f"line {e.line}: {e.message}" for e in schema.error_log]


# ============================================================================ the fingerprint
class Fingerprint(unittest.TestCase):
    def test_what_counts(self):
        cases = {
            "base": page("<p>Hello</p>"),
            "other code": page("<p>Hello</p>", v="0123abcd99", built="tomorrow"),
            "spaces": page("\n  <p>Hello</p>\n\n"),
            "text": page("<p>Hello!</p>"),
            "title": page("<p>Hello</p>", title="About us"),
            "desc": page("<p>Hello</p>", desc="Who we are"),
            "vlink": page('<a href="/x.js?v=cfc1657502">x</a><a href="/y?a=1&amp;v=cfc1657502">y</a>'),
            "vlink2": page('<a href="/x.js?v=1111122222">x</a><a href="/y?a=1&amp;v=3333344444">y</a>'),
            "yt": page('<a href="https://www.youtube.com/watch?v=BIjB93zE0sg">v</a>'),
            "yt2": page('<a href="https://www.youtube.com/watch?v=63ebpEXyxVc">v</a>'),
            "skip": page('<p>Hello</p><p class="freshness" data-lastmod="skip"><span>Updated <time>Oct 14</time></span></p>'),
            "skip2": page('<p>Hello</p><p class="freshness" data-lastmod="skip"><span>Updated <time>Oct 15</time></span></p>'),
            "nested": page('<p>Hello</p><div data-lastmod="skip"><div><div>14</div></div></div>'),
            "nested2": page('<p>Hello</p><div data-lastmod="skip"><div><div>15</div></div><div>more</div></div>'),
            "void": page('<p>Hello</p><img data-lastmod="skip" src="/a-2026-10-14.png" alt="">'),
            "after": page('<p>Hello</p><div data-lastmod="skip"><div>14</div></div><p>After</p>'),
            "after2": page('<p>Hello</p><div data-lastmod="skip"><div>15</div></div><p>After!</p>'),
            "json": page('<script type="application/json" id="c" data-lastmod="skip:today">{"lang":"en","today":"2026-10-14"}</script>'),
            "json2": page('<script type="application/json" id="c" data-lastmod="skip:today">{"lang":"en","today":"2026-10-15"}</script>'),
            "json3": page('<script type="application/json" id="c" data-lastmod="skip:today">{"lang":"es","today":"2026-10-15"}</script>'),
            "attr": page('<article data-lastmod="skip:data-day,hidden" data-day="2026-10-14"><p>Q</p></article>'),
            "attr2": page('<article data-lastmod="skip:data-day,hidden" data-day="2026-10-15" hidden><p>Q</p></article>'),
            "attr3": page('<article data-lastmod="skip:data-day,hidden" data-day="2026-10-15"><p>Q!</p></article>'),
            "attr4": page('<span title="it is hidden now" data-lastmod="skip:hidden" hidden>Q</span>'),
            "attr5": page('<span title="it is hidden now" data-lastmod="skip:hidden">Q</span>'),
            "markup": page('<div class="grid gap-2" id="x" data-k="1"><p class="lead" style="color:red">Hello</p></div>'),
            "icon": page('<p><svg class="icon size-4" aria-hidden="true"><use href="#i-arrow-right"></use></svg>Hello</p>'),
            "comment": page('<!-- a note --><p>Hello</p>'),
            "link": page('<p><a class="link" href="/a/">Hello</a></p>'),
            "link2": page('<p><a class="link tap-link" href="/b/">Hello</a></p>'),
            "link3": page('<p><a class="tap-link" href="/a/">Hello</a></p>'),
            "alt": page('<p>Hello</p><img src="/p.png" alt="A poster">'),
            "alt2": page('<p>Hello</p><img src="/p.png" alt="The poster">'),
            "when": page('<p>Hello <time datetime="2026-10-14">Oct 14</time></p>'),
            "when2": page('<p>Hello <time datetime="2026-10-21">Oct 14</time></p>'),
            "nomain": "<html><head><title>T</title></head><body><p>a</p></body></html>",
            "nomain2": "<html><head><title>T</title></head><body><p>b</p></body></html>",
        }
        r = run_js(self, r"""
          const L = await imp("eleventy/lastmod.js");
          const h = {}, c = {};
          for (const [k, html] of Object.entries(input)) { h[k] = L.fingerprint(html); c[k] = L.contentOf(html); }
          out({ h, c });""", data=cases)
        h, c = r["h"], r["c"]
        self.assertRegex(h["base"], r"^[0-9a-f]{16}$")
        self.assertEqual(c["base"], "About What we do Hello", "title, description, what <main> says — spaces as one")
        same = [("base", "other code"), ("base", "spaces"), ("vlink", "vlink2"), ("skip", "skip2"), ("nested", "nested2"),
                ("json", "json2"), ("attr", "attr2"), ("attr4", "attr5"), ("nomain", "nomain2"),
                # markup is not content: classes, ids, styles, data-*, icons, comments, tag names (round-9 review)
                ("base", "markup"), ("base", "icon"), ("base", "comment"), ("link", "link3")]
        for a, b in same:
            with self.subTest(same=(a, b)):
                self.assertEqual(h[a], h[b])
        for a, b in [("base", "text"), ("base", "title"), ("base", "desc"), ("yt", "yt2"), ("after", "after2"), ("json2", "json3"),
                     ("attr2", "attr3"), ("link", "link2"), ("alt", "alt2"), ("when", "when2")]:
            with self.subTest(differ=(a, b)):
                self.assertNotEqual(h[a], h[b])
        self.assertEqual(h["base"], h["skip"], "a marked element is left out whole")
        self.assertEqual(h["base"], h["void"], "a marked void element is its tag")
        self.assertIn("After", c["after"], "what follows a marked element still counts")
        self.assertIn('"lang":"en"', c["json"])
        self.assertNotIn("today", c["json"])
        self.assertNotIn("data-day", c["attr"])
        self.assertIn("title=it is hidden now", c["attr4"], "a name inside another attribute's value stays")
        self.assertIn("href=/a/", c["link"])
        self.assertIn("youtube.com/watch?v=BIjB93zE0sg", c["yt"], "a YouTube ?v= is content")


# ============================================================================ the marks in the templates
class Marks(unittest.TestCase):
    def read(self, *p: str) -> str:
        return ROOT.joinpath(*p).read_text(encoding="utf-8")

    def test_the_texts_that_move_with_the_clock_are_marked(self):
        ui = self.read("src", "_includes", "macros", "ui.njk")
        self.assertRegex(ui, r'\{%- if date %\}<p class="freshness[^"]*\{\{[^}]*\}\}" data-lastmod="skip">', "Updated …")
        self.assertRegex(self.read("src", "pages", "digest.njk"), r'<p [^>]*data-lastmod="skip">\{\{ "community\.digest\.generated"')
        # the Drive-checked line, wherever a list is empty (bulletin, events, portfolio, photos): in the shortcode
        self.assertIn('<p class="cm-checked${bad ? " is-warn" : ""}" data-lastmod="skip">',
                      self.read("eleventy", "filters", "committee.js"))
        self.assertIn('<span data-shop-days data-lastmod="skip" class="shop-days', self.read("src", "pages", "index.njk"))
        self.assertIn('<span data-lastmod="skip">{{ "shop.prices_note"', self.read("src", "pages", "shop.njk"))
        self.assertIn('<script type="application/json" id="pw-config" data-lastmod="skip:today">', self.read("src", "pages", "published.njk"))
        self.assertIn("<span data-shop-days data-lastmod=\"skip\" class=", self.read("src", "pages", "shop.njk"))
        contribute = self.read("src", "pages", "contribute.njk")
        for attr in ("data-days-label", "data-days-num", "data-days-unit"):
            with self.subTest(attr):
                found = re.findall(attr + r'(?: data-lastmod="skip")?>', contribute)
                self.assertTrue(found)
                self.assertEqual(found, [f'{attr} data-lastmod="skip">'] * len(found), "every countdown text")

    def test_the_updated_line_a_day_apart_has_one_fingerprint(self):
        script = r"""
          process.env.ONLY = "no-page-of-the-site";
          const os = await import("node:os");
          const { Eleventy } = await import("@11ty/eleventy");
          const L = await imp("eleventy/lastmod.js");
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-lastmod-"));
          try {
            const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js",
              config(cfg) {
                cfg.addTemplate("lm-test.njk", '{% import "macros/ui.njk" as ui %}<main><p>Same</p>{{ ui.freshness(site.built, "en", { note: true }) }}</main>',
                                { permalink: "/lm-test/index.html", sitemap: false, eleventyExcludeFromCollections: true });
              } });
            const pages = await elev.toJSON();
            const html = (pages.find((p) => p.url === "/lm-test/") || {}).content || "";
            out({ html, h: L.fingerprint(html) });
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }"""
        a = run_js(self, script, now="2026-10-14T15:00:00Z")
        b = run_js(self, script, now="2026-10-15T15:00:00Z")
        self.assertIn('data-lastmod="skip"', a["html"])
        self.assertNotEqual(a["html"], b["html"], "the line says another day …")
        self.assertEqual(a["h"], b["h"], "… and the page's fingerprint stays")


# ============================================================================ the dates
class Dates(unittest.TestCase):
    NOW = "2026-10-15T08:00:00Z"
    OLD = "2026-10-01T12:00:00Z"

    def date(self, hashes, previous):
        return run_js(self, r"""
          const L = await imp("eleventy/lastmod.js");
          out(L.datePages(input.hashes, input.previous, input.now));""",
                      data={"hashes": hashes, "previous": previous, "now": self.NOW})

    def test_same_fingerprint_keeps_its_date(self):
        prev = {"status": "ok", "state": {"v": 1, "version": "a", "pages": {
            "/": {"h": "1", "d": self.OLD}, "/about/": {"h": "2", "d": self.OLD}, "/gone/": {"h": "3", "d": self.OLD},
            "/bad/": {"h": "4", "d": "yesterday"}}}}
        r = self.date({"/": "1", "/about/": "2b", "/new/": "5", "/bad/": "4"}, prev)
        self.assertEqual(r["pages"]["/"], {"h": "1", "d": self.OLD}, "unchanged: its date")
        self.assertEqual(r["pages"]["/about/"], {"h": "2b", "d": self.NOW}, "changed: the build's time")
        self.assertEqual(r["pages"]["/new/"], {"h": "5", "d": self.NOW}, "new: the build's time")
        self.assertEqual(r["pages"]["/bad/"]["d"], self.NOW, "a date that is not one is not kept")
        self.assertNotIn("/gone/", r["pages"])
        self.assertEqual(r["datedNow"], 3)
        self.assertEqual(r["changed"], ["/about/", "/new/", "/bad/", "/gone/"], "… and a page that left the sitemap, for IndexNow")

    def test_no_live_file_dates_every_page_and_sends_every_page(self):
        r = self.date({"/": "1", "/about/": "2"}, {"status": "missing", "why": "HTTP 404"})
        self.assertEqual({p: v["d"] for p, v in r["pages"].items()}, {"/": self.NOW, "/about/": self.NOW})
        self.assertEqual((r["changed"], r["datedNow"]), (["/", "/about/"], 2))

    def test_an_unreadable_store_dates_no_page_and_sends_none(self):
        # round-9 review: an unreadable store says nothing about what changed — no page may claim it changed now
        r = self.date({"/": "1", "/about/": "2"}, {"status": "error", "why": "no answer"})
        self.assertEqual({p: v["d"] for p, v in r["pages"].items()}, {"/": "", "/about/": ""})
        self.assertEqual((r["changed"], r["datedNow"]), ([], 0), "a hiccup never sends the whole site")

    def test_the_live_file(self):
        r = run_js(self, r"""
          const L = await imp("eleventy/lastmod.js");
          const calls = [];
          const answer = (seq) => async (url, opts) => {
            calls.push({ url, signal: !!(opts && opts.signal), nocache: opts && opts.headers && opts.headers["cache-control"] });
            const a = seq.shift();
            if (a instanceof Error) throw a;
            return { status: a.status, ok: a.status >= 200 && a.status < 300, text: async () => a.body };
          };
          const state = JSON.stringify({ v: 1, version: "x", pages: { "/": { h: "1", d: "2026-10-01T12:00:00Z" } } });
          const timeout = Object.assign(new Error("t"), { name: "TimeoutError" });
          const res = {};
          const run = async (name, seq, retries) => {
            calls.length = 0;
            res[name] = { ...(await L.fetchPrevious("https://x.test/site/lastmod.json", { fetch: answer(seq), waitMs: 0, retries })), calls: calls.slice() };
          };
          await run("missing", [{ status: 404 }, { status: 200, body: state }]);
          await run("retried", [{ status: 503 }, timeout, { status: 200, body: state }]);
          await run("down", [timeout, timeout, timeout, { status: 200, body: state }]);
          await run("forbidden", [{ status: 403 }, { status: 200, body: state }]);
          await run("notjson", [{ status: 200, body: "<html>" }]);
          await run("v2", [{ status: 200, body: JSON.stringify({ v: 2, pages: {} }) }]);
          await run("nopages", [{ status: 200, body: JSON.stringify({ v: 1 }) }]);
          out(res);""")
        self.assertEqual((r["missing"]["status"], len(r["missing"]["calls"])), ("missing", 1), "a 404 is not asked again")
        self.assertEqual((r["retried"]["status"], len(r["retried"]["calls"])), ("ok", 3))
        self.assertEqual(r["retried"]["state"]["pages"]["/"]["h"], "1")
        self.assertEqual((r["down"]["status"], len(r["down"]["calls"])), ("error", 3), "10 s per try, 2 tries more")
        self.assertIn("no answer within 10 s", r["down"]["why"])
        self.assertEqual((r["forbidden"]["status"], len(r["forbidden"]["calls"])), ("error", 1))
        for k in ("notjson", "v2", "nopages"):
            self.assertEqual(r[k]["status"], "error", k)
        for c in r["retried"]["calls"]:
            self.assertRegex(c["url"], r"^https://x\.test/site/lastmod\.json\?t=\d+$", "fresh, past GitHub Pages' cache")
            self.assertTrue(c["signal"])
            self.assertEqual(c["nocache"], "no-cache")


# ============================================================================ the sitemap
class Sitemap(unittest.TestCase):
    def test_lastmod_right_after_loc(self):
        r = run_js(self, r"""
          const S = await imp("src/pages/sitemap.11ty.js");
          const L = await imp("eleventy/lastmod.js");
          console.warn = () => {};   // (the required pages are not all here: the sitemap's own warning)
          const p = (url) => ({ url, data: {} });
          const xml = S.render({ site: { url: "https://x.test/site" }, collections: { all: [p("/"), p("/es/"), p("/about/"), p("/es/about/"), p("/a&b/")] } });
          const pages = { "/": { h: "1", d: "2026-10-01T12:00:00Z" }, "/es/": { h: "2", d: "2026-10-02T12:00:00Z" },
                          "/about/": { h: "3", d: "2026-10-03T12:00:00Z" }, "/a&b/": { h: "4", d: "2026-10-04T12:00:00Z" } };
          const once = L.insertLastmod(xml, "https://x.test/site", pages);
          const twice = L.insertLastmod(once, "https://x.test/site", { ...pages, "/": { h: "1b", d: "2026-10-09T12:00:00Z" } });
          out({ xml, once, twice, w: [L.w3cTime("2026-10-14T08:33:05.284Z"), L.w3cTime(Date.UTC(2026, 0, 2, 3, 4, 5)), L.w3cTime("x")] });""",
                   env={"ONLY": ""})
        once = r["once"]
        self.assertNotIn("<lastmod>", r["xml"], "the template itself writes none")
        self.assertIn("    <loc>https://x.test/site/</loc>\n    <lastmod>2026-10-01T12:00:00Z</lastmod>\n    <priority>1.0</priority>", once)
        self.assertIn("<loc>https://x.test/site/a&amp;b/</loc>\n    <lastmod>2026-10-04T12:00:00Z</lastmod>", once)
        self.assertIn("<loc>https://x.test/site/es/about/</loc>\n    <priority>", once, "no date: no <lastmod>")
        self.assertEqual(once.count("<lastmod>"), 4)
        self.assertEqual(r["twice"].count("<lastmod>"), 4, "written again: replaced, never doubled")
        self.assertIn("<loc>https://x.test/site/</loc>\n    <lastmod>2026-10-09T12:00:00Z</lastmod>", r["twice"])
        self.assertEqual(r["w"], ["2026-10-14T08:33:05Z", "2026-01-02T03:04:05Z", ""])
        # the schema's order — loc, lastmod, changefreq, priority, then the alternates
        for url in re.findall(r"<url>(.*?)</url>", once, re.S):
            tags = re.findall(r"<([a-z:]+)[ >]", url)
            order = [t for t in tags if t != "xhtml:link"]
            self.assertEqual(order, sorted(order, key=["loc", "lastmod", "changefreq", "priority"].index))
        self.assertEqual(validate(once), [])
        bad = once.replace("    <lastmod>2026-10-01T12:00:00Z</lastmod>\n    <priority>1.0</priority>",
                           "    <priority>1.0</priority>\n    <lastmod>2026-10-01T12:00:00Z</lastmod>")
        self.assertTrue(validate(bad), "the schema refuses <lastmod> after <priority> (the check works)")


# ============================================================================ the hook
class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-lastmod-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "site"
        self.out.mkdir()
        self.changed = self.tmp / "changed.json"

    def results(self, about: str = "<p>About</p>") -> list[dict]:
        base = "https://x.test/site"
        sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                   + "".join(f"  <url>\n    <loc>{base}{u}</loc>\n    <priority>0.8</priority>\n  </url>\n" for u in ("/", "/about/", "/es/about/"))
                   + "</urlset>\n")
        (self.out / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        return [
            {"url": "/sitemap.xml", "outputPath": str(self.out / "sitemap.xml"), "content": sitemap},
            {"url": "/build.json", "outputPath": str(self.out / "build.json"),
             "content": json.dumps({"built": "2026-10-15T08:00:00.123Z", "version": "abcdef0123"})},
            {"url": "/", "outputPath": str(self.out / "index.html"), "content": page("<p>Home</p>")},
            {"url": "/about/", "outputPath": str(self.out / "about" / "index.html"), "content": page(about)},
            {"url": "/es/about/", "outputPath": str(self.out / "es" / "about" / "index.html"), "content": page("<p>Acerca</p>")},
        ]

    def hook(self, results, env: dict, answers: list | None = None) -> dict:
        return run_js(self, r"""
          const L = await imp("eleventy/lastmod.js");
          const said = [], asked = [];
          const answers = input.answers || [];
          const fetch = async (url) => {
            asked.push(url);
            const a = answers.shift() || { status: 599 };
            if (a.throw) throw new Error(a.throw);
            return { status: a.status, ok: a.status >= 200 && a.status < 300, text: async () => a.body };
          };
          const r = await L.updateLastmod({ results: input.results, directories: { output: input.out }, outputMode: input.mode || "fs",
                                            incremental: !!input.incremental }, input.env, { fetch, log: (s) => said.push(s), waitMs: 0 });
          const read = (f) => { try { return fs.readFileSync(f, "utf8"); } catch { return null; } };
          out({ r, said, asked, sitemap: read(input.out + "/sitemap.xml"), state: read(input.out + "/lastmod.json"),
                changed: read(input.changed) });""",
                      data={"results": results, "out": str(self.out), "changed": str(self.changed), "env": env,
                            "answers": answers or [], **{k: v for k, v in env.items() if k in ("mode", "incremental")}})

    def env(self, **extra) -> dict:
        return {"LASTMOD": "1", "SITE_URL": "https://x.test/site/", "LASTMOD_CHANGED": str(self.changed), **extra}

    def test_off_unless_website_update_asks(self):
        for name, env in (("no LASTMOD", {"SITE_URL": "https://x.test/site"}), ("LASTMOD=0", self.env(LASTMOD="0")),
                          ("ONLY=", self.env(ONLY="sitemap"))):
            with self.subTest(name):
                self.changed.write_text("old", encoding="utf-8")
                h = self.hook(self.results(), env)
                self.assertIsNone(h["r"])
                self.assertEqual(h["asked"], [], "nothing fetched")
                self.assertNotIn("<lastmod>", h["sitemap"])
                self.assertIsNone(h["state"])
                self.assertEqual(h["changed"], "old", "… nothing written at all")
        for k, v in (("mode", "json"), ("incremental", True)):
            with self.subTest(k):
                h = self.hook(self.results(), {**self.env(), k: v})
                self.assertIsNone(h["r"])
                self.assertEqual(h["asked"], [])

    def test_first_run_then_the_next_one(self):
        first = self.hook(self.results(), self.env(), [{"status": 404}])
        self.assertEqual(first["asked"][0].split("?t=")[0], "https://x.test/site/lastmod.json")
        now = "2026-10-15T08:00:00Z"
        self.assertEqual(first["sitemap"].count(f"<lastmod>{now}</lastmod>"), 3)
        state = json.loads(first["state"])
        self.assertEqual((state["v"], state["version"], state["built"]), (1, "abcdef0123", now))
        self.assertEqual(sorted(state["pages"]), ["/", "/about/", "/es/about/"])
        self.assertEqual(json.loads(first["changed"]), {"site": "https://x.test/site", "changed": [
            "https://x.test/site/", "https://x.test/site/about/", "https://x.test/site/es/about/"],
            "total": 3, "dated_now": 3, "previous": "missing", "from": "live", "version_changed": False})
        self.assertTrue(any("no lastmod.json published yet" in s for s in first["said"]), first["said"])
        # the next build: the live site has the first one's file; only /about/ changed
        old = json.loads(first["state"])
        old["pages"] = {p: {**v, "d": "2026-10-01T12:00:00Z"} for p, v in old["pages"].items()}
        second = self.hook(self.results("<p>About us</p>"), self.env(), [{"status": 503}, {"status": 200, "body": json.dumps(old)}])
        self.assertEqual(len(second["asked"]), 2, "a server error is asked again")
        self.assertIn("<loc>https://x.test/site/about/</loc>\n    <lastmod>2026-10-15T08:00:00Z</lastmod>", second["sitemap"])
        self.assertIn("<loc>https://x.test/site/</loc>\n    <lastmod>2026-10-01T12:00:00Z</lastmod>", second["sitemap"])
        got = json.loads(second["changed"])
        self.assertEqual((got["changed"], got["dated_now"], got["previous"], got["version_changed"]),
                         (["https://x.test/site/about/"], 1, "ok", False))
        self.assertTrue(any(s.startswith("[lastmod] 1 of 3 sitemap page(s) changed") for s in second["said"]), second["said"])
        self.assertEqual(validate(second["sitemap"]), [])
        # the code changed since: said so (Check the build then does not warn about many changes)
        old["version"] = "0000000000"
        third = self.hook(self.results("<p>About us</p>"), self.env(), [{"status": 200, "body": json.dumps(old)}])
        self.assertTrue(json.loads(third["changed"])["version_changed"])

    def test_an_unreadable_live_file(self):
        h = self.hook(self.results(), self.env(GITHUB_ACTIONS="true"), [{"throw": "ECONNRESET"}] * 3)
        self.assertEqual(len(h["asked"]), 3)
        got = json.loads(h["changed"])
        self.assertEqual((got["changed"], got["dated_now"], got["previous"]), ([], 0, "error"))
        self.assertNotIn("<lastmod>", h["sitemap"], "no page claims it changed now")
        self.assertIsNone(h["state"], "no store: the next run compares with the last good one again")
        self.assertTrue(any(s.startswith("::warning title=Sitemap dates::") and "ECONNRESET" in s for s in h["said"]), h["said"])

    def test_the_store_of_the_last_publish_comes_first(self):
        # round-9 review: GitHub Pages' cache can serve an old /lastmod.json (or a 404) after a deploy, whatever the
        # query — Website update keeps the published store in GitHub's Actions cache (LASTMOD_STORE) and reads that
        store = self.tmp / "store.json"
        first = self.hook(self.results(), self.env(), [{"status": 404}])
        store.write_text(first["state"], encoding="utf-8")
        h = self.hook(self.results("<p>About us</p>"), self.env(LASTMOD_STORE=str(store)), [{"status": 404}])
        self.assertEqual(h["asked"], [], "the live site is not asked")
        got = json.loads(h["changed"])
        self.assertEqual((got["changed"], got["dated_now"], got["previous"], got["from"]),
                         (["https://x.test/site/about/"], 1, "ok", "store"))
        self.assertTrue(any("changed since the last publish" in s for s in h["said"]), h["said"])
        # a store that is not one (or none at all): the live site is asked
        store.write_text("not json", encoding="utf-8")
        h = self.hook(self.results(), self.env(LASTMOD_STORE=str(store)), [{"status": 200, "body": first["state"]}])
        self.assertEqual(len(h["asked"]), 1)
        self.assertEqual(json.loads(h["changed"])["from"], "live")
        h = self.hook(self.results(), self.env(LASTMOD_STORE=str(self.tmp / "none.json")), [{"status": 200, "body": first["state"]}])
        self.assertEqual((len(h["asked"]), json.loads(h["changed"])["dated_now"]), (1, 0))

    def test_never_fails_the_build(self):
        results = self.results()
        results[0]["outputPath"] = str(self.tmp / "no-such-folder" / "sitemap.xml")   # cannot be written
        self.changed.write_text("from the build before", encoding="utf-8")
        h = self.hook(results, self.env(), [{"status": 404}])
        self.assertIsNone(h["r"])
        self.assertIsNone(h["changed"], "an older list never stands for this build")
        self.assertTrue(any("skipped" in s and "no <lastmod> this time" in s for s in h["said"]), h["said"])
        self.assertNotIn("<lastmod>", h["sitemap"])
        self.assertIsNone(h["state"], "no store when there was none: the next run starts afresh")

    def test_a_failed_run_publishes_the_live_store_again(self):
        # round-9 review: a run that fails half-way must not break the chain of dates (the next run would take it
        # for a first run and send every page to IndexNow again)
        live = {"v": 1, "version": "abcdef0123", "built": "2026-10-01T12:00:00Z",
                "pages": {"/": {"h": "0123456789abcdef", "d": "2026-10-01T12:00:00Z"}}}
        results = self.results()
        results[0]["outputPath"] = str(self.tmp / "no-such-folder" / "sitemap.xml")   # cannot be written
        h = self.hook(results, self.env(), [{"status": 200, "body": json.dumps(live)}])
        self.assertIsNone(h["r"])
        self.assertIsNone(h["changed"])
        self.assertEqual(json.loads(h["state"]), live, "the live store, unchanged")
        self.assertTrue(any("published again unchanged" in s for s in h["said"]), h["said"])

    def test_with_the_real_fetch(self):
        state = {"v": 1, "version": "abcdef0123", "pages": {"/": {"h": "x", "d": "2026-10-01T12:00:00Z"}}}
        asked: list[str] = []

        class Live(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                asked.append(self.path)
                body = json.dumps(state).encode()
                self.send_response(200 if self.path.startswith("/site/lastmod.json?t=") else 404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Live)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        site = f"http://127.0.0.1:{server.server_address[1]}/site"
        results = [dict(r, content=r["content"].replace("https://x.test/site", site)) for r in self.results()]
        r = run_js(self, r"""
          const L = await imp("eleventy/lastmod.js");
          const said = [];
          const r = await L.updateLastmod({ results: input.results, directories: { output: input.out }, outputMode: "fs" },
                                          input.env, { log: (s) => said.push(s) });
          out({ r, said });""", data={"results": results, "out": str(self.out), "env": {**self.env(), "SITE_URL": site}})
        self.assertTrue(asked, "the live file was asked for")
        for p in asked:   # (once — or again after a hiccup of the test's own little server)
            self.assertRegex(p, r"^/site/lastmod\.json\?t=\d+$")
        self.assertEqual((r["r"]["previous"], r["r"]["total"], r["r"]["dated_now"]), ("ok", 3, 3), r["said"])


if __name__ == "__main__":
    unittest.main()
