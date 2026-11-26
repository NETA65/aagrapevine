"""The home page since the UX review of November 2026 (src/pages/index.njk, areas/home.css → /assets/css/home.css):
short — it was 14,240px tall on a phone, with 14 sections and 207 links — and a way in to each page that holds the
whole of something. One build of Home (English and Spanish) on the day's data:

  * Blocks    — the hero, then (under it) the meeting cards below 1024px, "Where would you like to start?" and the
                daily quote, then four sections: the magazines, listen & watch, the events and "More on this site" —
                never the sections that moved to their own pages (the bulletin, published writers, the library,
                Instagram, the committee's uploads, the service band, the site counters).
  * Start     — four big buttons, each a link to the page that does it best: I'm new to AA → the "New to AA?" card
                on /meetings/, a group rep → /gvr/, writing → /contribute/, subscribing → /shop/#subscriptions —
                in that order, in the page language.
  * Hero      — "Find an AA meeting near you": AA's own finder (links.aa_find / aa_find_es), a new tab, said so.
  * Outline   — one <h1> first; each <h2> once (the meeting cards' titles are a heading only in their copy below
                the hero); no empty heading; no <h3> before the first <h2>.
  * Magazines — at most three stories of each magazine; one media row: the featured episode and at most one video;
                at most three events.
  * More      — one link each to the Bulletin, the Library, Published writers, Instagram, the Portfolio, Photos and
                Stay updated, in the page language.
  * Weight    — the page links its own stylesheet (/assets/css/home.css) and no area's rules sit in main.css.

    python -m unittest tests.test_home_start -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
I18N = {}
for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
    I18N.update(json.loads(f.read_text(encoding="utf-8")))

PAGES_JS = r"""
process.env.ONLY = "index.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-home-start-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url === "/" || p.url === "/es/").map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def t(key: str, lang: str) -> str:
    return I18N[key][lang]


def text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def main_of(page: str) -> str:
    return page[page.index('<main id="main"'):page.index("</main>")]


class Home(unittest.TestCase):
    built: dict | None = None

    def setUp(self):
        if Home.built is None:
            Home.built = run_js(self, PAGES_JS, timeout=900)
        self.pages = Home.built

    def each(self):
        for url, lang in (("/", "en"), ("/es/", "es")):
            with self.subTest(url=url):
                yield self.pages[url], lang, ("/es" if lang == "es" else "")

    def test_the_blocks(self):
        for page, lang, pre in self.each():
            main = main_of(page)
            ids = re.findall(r'<section[^>]*aria-labelledby="([^"]+)"', main)
            self.assertEqual(ids[0], "home-title", "the hero first")
            want = ["choose-title", "mag-title", "lw-title", "events-title", "more-title"]
            self.assertEqual([i for i in ids if i in want], [i for i in want if i in ids], "in this order")
            for must in ("choose-title", "mag-title", "more-title"):
                self.assertIn(must, ids)
            self.assertLessEqual(len([i for i in ids if i not in ("quote-title",) and not i.startswith(("quote-", "mag-", "ep-", "video-"))]), 7)
            for gone in ("ann-title", "spot-title", "lib-title", "ig-title", "drive-title", "svc-title", "published-writers",
                         "home-under-stats", "data-home-spot", "home-ig-grid", "home-drive-grid", "home-band"):
                self.assertNotIn(gone, main)

    def test_where_would_you_like_to_start(self):
        for page, lang, pre in self.each():
            sec = page[page.index('<section class="card home-choose"'):]
            sec = sec[:sec.index("</section>")]
            links = re.findall(r'<a class="home-choose-btn[^"]*" href="([^"]+)">(.*?)</a>', sec, re.S)
            self.assertEqual([h for h, _ in links], [pre + "/meetings/#new-to-aa", pre + "/gvr/", pre + "/contribute/", pre + "/shop/#subscriptions"])
            for (href, inner), key in zip(links, ("new", "rep", "write", "sub")):
                self.assertIn(t(f"home.choose_{key}", lang), html.unescape(text(inner)))
            self.assertIn(t("newcomer.line", lang), html.unescape(text(links[0][1])))
            self.assertIn(f'<h2 id="choose-title" class="home-choose-title">{html.escape(t("home.choose_title", lang), quote=False)}</h2>', sec)
            # it comes right after the meeting cards, before the quote and the magazines
            self.assertLess(page.index('class="card home-under-card') if 'home-under-card' in page else 0, page.index('class="card home-choose"'))
            self.assertLess(page.index('class="card home-choose"'), page.index('aria-labelledby="mag-title"'))

    def test_find_an_aa_meeting(self):
        site = (ROOT / "config" / "site.yml").read_text(encoding="utf-8")
        for page, lang, pre in self.each():
            want = re.search(r'^\s*aa_find%s:\s*"([^"]+)"' % ("_es" if lang == "es" else ""), site, re.M).group(1)
            hero = page[page.index('id="homeHero"'):]
            hero = hero[:hero.index("</section>")]
            a = re.search(r'<a class="btn-light home-find-aa" href="([^"]+)" target="_blank" rel="noopener">(.*?)</a>', hero, re.S)
            self.assertIsNotNone(a)
            self.assertEqual(a.group(1), want)
            self.assertIn(t("home.cta_find_aa", lang), text(a.group(2)))
            self.assertIn(t("home.opens_new_tab", lang), text(a.group(2)))

    def test_the_outline(self):
        for page, lang, pre in self.each():
            heads = re.findall(r"<(h[1-6])\b[^>]*>(.*?)</\1>", page, re.S)
            self.assertEqual(heads[0][0], "h1", "the page's own title first (the Aa panel's name is no heading)")
            self.assertEqual(sum(1 for h, _ in heads if h == "h1"), 1)
            h2 = [text(s) for h, s in heads if h == "h2"]
            self.assertEqual(len(h2), len(set(h2)), f"an h2 twice: {h2}")
            self.assertFalse([s for _, s in heads if not text(s)], "no empty heading")
            first_h2 = next(i for i, (h, _) in enumerate(heads) if h == "h2")
            self.assertFalse([h for h, _ in heads[:first_h2] if h == "h3"])

    def test_three_of_each(self):
        for page, lang, pre in self.each():
            for pub in ("gv", "lv"):
                card = page[page.index(f'aria-labelledby="mag-{pub}-title"'):]
                card = card[:card.index("</article>")]
                self.assertLessEqual(card.count("<li class=\"group relative px-5"), 3)
            lw = page[page.index('aria-labelledby="lw-title"'):] if 'aria-labelledby="lw-title"' in page else ""
            self.assertLessEqual(lw.count("<lite-youtube"), 1)
            self.assertNotIn("home-play", lw, "no list of more episodes")
            if 'aria-labelledby="events-title"' in page:
                ev = page[page.index('aria-labelledby="events-title"'):]
                ev = ev[:ev.index("</section>")]
                self.assertLessEqual(len(re.findall(r'<li data-gv-expire-item', ev)), 3)

    def test_more_on_this_site(self):
        for page, lang, pre in self.each():
            sec = page[page.index('aria-labelledby="more-title"'):]
            sec = sec[:sec.index("</section>")]
            hrefs = re.findall(r'<a href="([^"]+)" class="home-more-link', sec)
            self.assertEqual(hrefs, [pre + u for u in ("/bulletin/", "/library/", "/published/", "/instagram/", "/portfolio/", "/photos/", "/stay-updated/")])

    def test_its_own_stylesheet(self):
        for page, lang, pre in self.each():
            sheets = re.findall(r'<link rel="stylesheet" href="([^"?]+)', page)
            self.assertEqual(sheets[:2], ["/assets/css/main.css", "/assets/css/home.css"])
        self.assertNotIn('@import "./areas/home.css";', (ROOT / "src" / "assets" / "css" / "main.css").read_text(encoding="utf-8"))
        self.assertIn('@import "./areas/home.css";', (ROOT / "src" / "assets" / "css" / "home.css").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
