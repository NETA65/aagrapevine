"""Round 27 — the custom domain (grapevine.neta65.org). GitHub Pages serves a new custom domain on http:// until its
certificate is issued and the owner ticks "Enforce HTTPS", and every publish builds for the address Pages reports — so
for a while the site's own address is http://, and with the next publish after "Enforce HTTPS" it is https://.

  * ShortAddresses — the addresses the handouts and print sheets print under a QR code or after a label (GVR / RLV
                     101 and its handout, the orientation decks and lessons, the Shop's sheet) leave out the scheme,
                     http:// as well as https://: "x.test/gvr/", never "http://x.test/gvr/".
  * BoothSources   — a question's "Source" link to a page of this site, written for grapevine.neta65.org, stays a link
                     on every build, the Code check's (neta65.github.io/aagrapevine) too (eleventy/filters/booth.js
                     SOURCE_HOSTS), and the tests' own lists of those sites are the booth's; a qr_url written for
                     the site's address passes the booth's check on every build too (booth.js ALLOWED_HOSTS and its
                     twin in tests/test_booth_csv.py), as how-to/booth.md's "Allowed sites" table says.

(The booth's own pages on an http address: tests/test_booth_csv.py, test_booth_build.py HttpAddress and
test_booth_core.py; the weekly link check's address: tests/test_automation.py LinkCheck.)

    python -m unittest tests.test_r27_domain -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_booth_csv as TBC  # noqa: E402
from nodejs import run_js  # noqa: E402
from test_r12_u5_gvr import SOURCE_SITES  # noqa: E402

BUILD_JS = r"""
process.env.ONLY = "gvr,orientation,shop";        // (here: the helpers above read the config without it)
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r27-domain-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => input.urls.includes(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""

URLS = ["/gvr/", "/es/gvr/", "/orientation/", "/es/orientation/", "/shop/", "/es/shop/"]


def printed(html: str) -> str:
    """What a page prints: its text without the tags, their attributes and the scripts' data."""
    html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)


class ShortAddresses(unittest.TestCase):
    """The same pages built for http://x.test and for https://x.test print the same words, but for the full links of
    the messages to copy ("More about the service position: http://x.test/gvr/"), which keep the site's scheme."""

    pages: dict | None = None

    def setUp(self):
        if ShortAddresses.pages is None:
            ShortAddresses.pages = {scheme: run_js(self, BUILD_JS, data={"urls": URLS}, timeout=900, now="2026-11-12T18:00:00Z",
                                                   env={"PATH_PREFIX": "/", "SITE_URL": f"{scheme}://x.test", "STRICT_BUILD": "",
                                                        "BUILD_WARNINGS": "", "GITHUB_ACTIONS": ""})
                                    for scheme in ("http", "https")}
        self.http, self.https = ShortAddresses.pages["http"], ShortAddresses.pages["https"]

    def test_the_same_words_on_http_and_https(self):
        self.assertEqual((sorted(self.http), sorted(self.https)), (sorted(URLS), sorted(URLS)))
        for url in URLS:
            with self.subTest(url=url):
                self.assertIn('href="http://x.test' + url + '"', self.http[url], "the links keep the site's own address")
                self.assertEqual(printed(self.http[url]), printed(self.https[url]).replace("https://x.test", "http://x.test"))

    def test_the_short_addresses_themselves(self):
        want = {"/gvr/": ["x.test/gvr/", "x.test/gvr/#kits", "x.test/meetings/", "x.test/tracker/"],
                "/es/gvr/": ["x.test/es/gvr/", "x.test/es/meetings/", "x.test/es/tracker/"],
                "/orientation/": ["x.test/gvr/", "x.test/monthly/"],
                "/es/orientation/": ["x.test/es/gvr/", "x.test/es/monthly/"],
                "/shop/": ["x.test/shop/"], "/es/shop/": ["x.test/es/shop/"]}
        for url, shorts in want.items():
            text = printed(self.http[url])
            for short in shorts:
                with self.subTest(url=url, short=short):
                    self.assertRegex(text, r"(?<![/\w])" + re.escape(short), "printed without its scheme")


SOURCES_JS = r"""
const { csvSources } = await imp("eleventy/filters/booth.js");
out(Object.fromEntries(input.sites.map((s) => [s.url, csvSources(input.csv, s)])));
"""


class BoothSources(unittest.TestCase):
    """A question's "Source" link to a page of this site (content/booth/booth.csv source_url, written for the live
    address) stays a link on every build: the live site's, the old address's and the Code check's (built for
    neta65.github.io/aagrapevine)."""

    def test_the_sites_own_pages_on_every_build(self):
        csv = ("id,type,text_en,source_url\n"
               "a,fact,A.,https://grapevine.neta65.org/meetings/#weekly-open\n"
               "b,fact,B.,https://neta65.github.io/aagrapevine/listen/\n"
               "c,fact,C.,https://www.aa.org/\n"
               "d,fact,D.,https://other.example/x\n"
               "e,fact,E.,https://x.test/shop/\n")
        sites = [{"url": u} for u in ("https://grapevine.neta65.org", "http://grapevine.neta65.org",
                                      "https://neta65.github.io/aagrapevine", "https://x.test")]
        r = run_js(self, SOURCES_JS, data={"csv": csv, "sites": sites})
        for s in sites:
            with self.subTest(site=s["url"]):
                got = r[s["url"]]
                self.assertEqual(sorted(k for k in got if k in "abc"), ["a", "b", "c"])
                self.assertNotIn("d", got, "another site is never linked")
                self.assertEqual("e" in got, s["url"] == "https://x.test", "the build's own host")

    def test_the_tests_lists_are_the_booths(self):
        r = run_js(self, 'const B = await imp("eleventy/filters/booth.js"); out({ src: B.SOURCE_HOSTS, ok: B.ALLOWED_HOSTS });')
        self.assertEqual(set(r["src"]), SOURCE_SITES, "test_r12_u5_gvr.SOURCE_SITES (the browser check's too)")
        self.assertEqual(r["ok"], TBC.ALLOWED_HOSTS, "test_booth_csv's checker, line for line")
        self.assertIn("grapevine.neta65.org", r["ok"])

    def test_a_qr_link_written_for_the_sites_address(self):
        """A qr_url written as the live address (how-to/booth.md "Allowed sites": This site) passes on every build —
        the Code check's (neta65.github.io/aagrapevine) and another address's too, in both checkers."""
        text = ("id,type,title_en,qr_url\n"
                "shop,qr,Scan,https://grapevine.neta65.org/shop/\n"
                "old,qr,Scan,https://neta65.github.io/aagrapevine/listen/\n")
        sites = ["https://grapevine.neta65.org", "http://grapevine.neta65.org", "https://neta65.github.io/aagrapevine",
                 "https://x.test"]
        r = run_js(self, """
            const B = await imp("eleventy/filters/booth.js");
            out(input.sites.map((u) => { const c = B.checkCsv(input.text, { site: { url: u }, file: "t.csv" });
              return { lines: c.problems.map((p) => `${p.where}: ${p.en}`), qr: c.items.map((i) => i.qr) }; }));
        """, data={"text": text, "sites": sites})
        for u, js in zip(sites, r):
            with self.subTest(site=u):
                self.assertEqual(js["lines"], [])
                self.assertEqual(js["qr"], ["https://grapevine.neta65.org/shop/", "https://neta65.github.io/aagrapevine/listen/"])
                self.assertEqual(TBC.check_csv(text, file="t.csv", site_url=u)[1], [])


if __name__ == "__main__":
    unittest.main()
