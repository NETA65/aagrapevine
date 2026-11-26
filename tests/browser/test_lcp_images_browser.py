"""Round 35 · /listen/ and /watch/ ask for their largest picture early, in a real browser (tests/browser/__init__.py says
how to run these; they share test_site_in_browser.py's site server and browser; tests/test_head_for_crawlers.py has the offline
checks, base.njk's first head script the why):

  * EarlyPoster — on a phone-sized window, /listen/ and /watch/ in English and Spanish: with Data saver off the page
                  has a <link rel="preload" as="image"> with fetchpriority "high" for the YouTube poster it shows (the
                  same address as the poster's), and the poster is asked for; with Data saver on there is no such
                  link and nothing is asked of i.ytimg.com at all (the rule of areas/pwa.css: no thumbnail under Data
                  saver). The browser never reaches another site here (scripts/ops/site_browser.py): the request is
                  made, and fails, which is all this needs to see.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import new_context, open_page, setUpModule, tearDownModule  # noqa: F401

PAGES = ("listen/", "es/listen/", "watch/", "es/watch/")
LINKS = "() => [...document.querySelectorAll('link[rel=preload][as=image]')].map((l) => [l.href, l.fetchPriority])"
# the poster the page shows: /listen/'s hero Short, /watch/'s latest video (the inline background lite-youtube draws)
POSTER = """(cls) => { const el = document.querySelector('lite-youtube.' + cls);
  const m = el && /url\\(["']?([^"')]+)/.exec(el.getAttribute('style') || ''); return m ? m[1] : null; }"""


class EarlyPoster(unittest.TestCase):
    def test_the_poster_is_asked_for_early_unless_data_saver_is_on(self):
        for saver in ("off", "on"):
            ctx = new_context(390, 844, prefs={"saver": saver})
            asked: list[str] = []
            ctx.on("request", lambda r: asked.append(r.url) if "ytimg.com" in r.url else None)
            try:
                for path in PAGES:
                    with self.subTest(page="/" + path, saver=saver):
                        asked.clear()
                        errors: list[str] = []
                        page = open_page(ctx, path, errors)
                        self.assertEqual(page.evaluate("document.documentElement.getAttribute('data-saver')"), saver)
                        poster = page.evaluate(POSTER, "hero-aside-lyt" if "listen" in path else "media-lyt")
                        self.assertRegex(poster or "", r"^https://i\.ytimg\.com/vi/[\w-]+/hqdefault\.jpg$")
                        links = page.evaluate(LINKS)
                        if saver == "off":
                            self.assertEqual(links, [[poster, "high"]])
                            self.assertIn(poster, asked)
                        else:
                            self.assertEqual(links, [], "no early poster under Data saver")
                            self.assertEqual(asked, [], "nothing asked of i.ytimg.com under Data saver")
                        self.assertEqual(errors, [])
                        page.close()
            finally:
                ctx.close()


if __name__ == "__main__":
    unittest.main()
