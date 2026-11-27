"""The home page since the UX review of November 2026 (src/pages/index.njk, areas/home.css → /assets/css/home.css):
short — it was 14,240px tall on a phone, with 14 sections and 207 links — and a way in to each page that holds the
whole of something. One build of Home (English and Spanish) on the day's data:

  * Blocks    — the hero, then (under it) the meeting cards below 1024px, "Where would you like to start?", the
                pinned bulletin posts while there are any, and the daily quote, then four sections: the magazines,
                listen & watch, the events and "More on this site" — never the sections that moved to their own pages
                (the bulletin's latest posts, published writers, the library, Instagram, the committee's uploads, the
                service band, the site counters).
  * Pinned    — a build of Home on data of the test's own (SITE_DATA): "Pinned on the Bulletin" lists the pinned
                posts still on (two at most, newest first; never a post that is not pinned, is over or is gone), each
                with its title, one line of it and "Read" (named by the post) to the post on /bulletin/, in the page
                language, and ends with the last day of the one that has one (data-gv-expire); no pinned post: no
                card.
  * Start     — four big buttons, each a link to the page that does it best: I'm new to AA → the "New to AA?" card
                on /meetings/, a group rep → /gvr/, writing → /contribute/, subscribing → /shop/#subscriptions —
                in that order, in the page language; each button's arrow is inside its label (it floats at the end
                of the label's first line, so where a larger-text rule hides it its room goes too), and four in a row
                the third column, "I want to write my story", is the wider one (home.css 1d; what the browser draws:
                tests/browser/test_r38_home_layout.py).
  * Hero      — "Find an AA meeting near you": AA's own finder (links.aa_find / aa_find_es), a new tab, said so.
  * Outline   — one <h1> first; each <h2> once (the meeting cards' titles are a heading only in their copy below
                the hero); no empty heading; no <h3> before the first <h2>.
  * Magazines — at most three stories of each magazine; at most three events.
  * Listen    — Listen & watch (the owner's choice after the review): the featured episode beside "More episodes" —
                three rows at most (the third not on phones), each a play button for the episode card's player, which
                the two cards share (homePlayer on their wrapper) —, the weekly open meetings' line once, then the
                newest video as one compact strip under them (home.css .home-video: a small lite-youtube beside its
                words, "Subscribe on YouTube" from 640px); the strip's video is never the YouTube copy of an episode
                shown above (homeVideos, given the rows too).
  * More      — one link each to the Bulletin, the Library, Published writers, Instagram, the Portfolio, Photos and
                Stay updated, in the page language.
  * Words     — (round 38) at 115 % text with relaxed spacing the start buttons take fewer columns where a word would
                break in two (one under the other below 672px, two in a row below 1440px); the Book of the Month
                card's arrow and "More on this site"'s icon tiles step aside, and that grid takes fewer columns, where
                a word broke in two (what the browser draws: tests/browser/test_r38_home_layout.py WholeWords); the
                meeting cards under the hero are one column at 150 % on tablets, and the Grapevine Meeting's time,
                wrapped, keeps its first letters.
  * Weight    — the page links its own stylesheet (/assets/css/home.css) and no area's rules sit in main.css.

    python -m unittest tests.test_home_start -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import tempfile
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
            want = ["choose-title", "pins-title", "quote-title", "mag-title", "lw-title", "events-title", "more-title"]
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
                self.assertIn('<span class="home-choose-label"><span class="home-choose-go" aria-hidden="true">', inner,
                              "the arrow inside the label, at the end of its first line")
                self.assertEqual(inner.count('class="home-choose-go"'), 1)
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
            self.assertLessEqual(lw.count('class="home-play'), 3, "three more episodes at most")
            if 'aria-labelledby="events-title"' in page:
                ev = page[page.index('aria-labelledby="events-title"'):]
                ev = ev[:ev.index("</section>")]
                self.assertLessEqual(len(re.findall(r'<li data-gv-expire-item', ev)), 3)

    def test_listen_and_watch(self):
        for page, lang, pre in self.each():
            if 'aria-labelledby="lw-title"' not in page:
                self.skipTest("no episode and no video in the day's data")
            lw = page[page.index('aria-labelledby="lw-title"'):]
            lw = lw[:lw.index("</section>")]
            if 'class="home-lw' in lw:
                wrap = re.search(r'<div class="home-lw [^"]*" x-data="homePlayer"\s+data-left="[^"]+" data-resume="[^"]+">', lw)
                self.assertIsNotNone(wrap, "the two cards share one player (homePlayer on their wrapper)")
                self.assertNotIn("x-data", lw[lw.index('class="home-episode'):lw.index('id="ep-title"')], "not the card's own")
                rows = re.findall(r'<li class="flex grow items-center gap-3 py-3( max-sm:hidden)?">', lw)
                if rows:
                    self.assertIn('<div class="home-more-eps card card-pad flex flex-col">', lw)
                    self.assertIn(t("home.more_episodes", lang), text(lw))
                    self.assertLessEqual(len(rows), 3)
                    self.assertEqual([bool(r) for r in rows], [i >= 2 for i in range(len(rows))], "the third not on phones")
                    end = lw.index('class="home-video') if 'class="home-video' in lw else len(lw)
                    plays = re.findall(r'<a href="[^"]+" class="home-play [^"]*"[^>]*aria-label="([^"]+)"', lw[:end])
                    self.assertEqual(len(plays), len(re.findall(r'class="home-play ', lw)), "every play button in the shared player's wrapper")
                    for label in plays:
                        self.assertTrue(html.unescape(label).startswith(t("home.play_episode", lang).split("{")[0]), label)
                self.assertLessEqual(lw.count("/meetings/#weekly-open"), 1, "the weekly open meetings' line once")
            if "<lite-youtube" in lw:
                strip = lw[lw.index('<article class="home-video card'):]
                self.assertIn('class="home-yt" playlabel="', strip)
                self.assertIn('<h3 id="video-title"', strip)
                self.assertIn('class="line-clamp-2', strip, "its title: two lines at most")
                self.assertIn('<p class="home-video-act">', strip)
                if 'class="home-lw' in lw:
                    self.assertGreater(lw.index('<article class="home-video card mt-6"'), lw.index('class="home-lw'), "under the two cards")
        src = (ROOT / "src" / "pages" / "index.njk").read_text(encoding="utf-8")
        self.assertIn("D.videos.items | homeVideos(1, ep, moreEps)", src, "never a video of an episode shown above")

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



VIDEOS_JS = r"""
const ep = (id, title, date) => ({ id, title, date, status: "ok", extra: { audio_url: "https://ep.example.test/" + id + ".mp3" } });
const vid = (id, title, date) => ({ id, title, date, status: "ok", extra: { video_id: id } });
const featured = ep("e1", "God Shot [Season 11, Episode 21]", "2026-11-22T05:15:00Z");
const rows = [ep("e2", "Reunión abierta semanal de Alcohólicos Anónimos de La Viña [Temporada 1, Episodio 3]", "2026-11-23T05:15:00Z")];
const vids = [vid("v1", "Reunión abierta semanal de Alcohólicos Anónimos de La Viña [Temporada 1, Episodio 3]", "2026-11-23T05:27:00Z"),
              vid("v2", "Patience and Tolerance", "2026-11-16T17:00:00Z"), vid("v3", "God Shot [Season 11, Episode 21]", "2026-11-24T05:00:00Z")];
out({ shown: filters.homeVideos(vids, 1, featured, rows).map((v) => v.id), featured: filters.homeVideos(vids, 1, featured).map((v) => v.id) });
"""


class StripVideo(unittest.TestCase):
    def test_never_a_copy_of_an_episode_shown_above(self):
        # the newest video is the YouTube copy of a "More episodes" row (La Viña's meeting): the strip skips it, and the
        # featured episode's copy, for the newest other one
        r = run_js(self, VIDEOS_JS)
        self.assertEqual(r["shown"], ["v2"])
        self.assertEqual(r["featured"], ["v1"], "(given the featured episode alone, the row's copy would show)")

    def test_its_look(self):
        css = (ROOT / "src" / "assets" / "css" / "areas" / "home.css").read_text(encoding="utf-8")
        for rule in (".home-video {", 'grid-template-areas: "yt info";', ".home-video-act { grid-area: act; display: none; }",
                     'grid-template-areas: "yt info act";', ".home-play:hover, .home-play.is-playing {",
                     '@media (64rem <= width < 80rem) { :root:where(.gv-prefs)[data-text="150"] .home-lw { grid-template-columns: minmax(0, 1fr); } }'):
            self.assertIn(rule, css)
        # 130–150 % text from 640 to 1279px: the usual video size, at most 40 % of the strip — never bigger than at 1280px
        self.assertIn("grid-template-columns: min(40%, 13rem) minmax(0, 1fr);", css)
        self.assertIn("grid-template-columns: min(40%, 15rem) minmax(0, 1fr);", css)
        # (round 38) …where its words are taller than it, the video keeps its 16:9 in the strip's top corner — at every
        # text size from 640px, never stretched to the words' height (208 × 143px at 100 %, nearly square at 115 % with
        # relaxed spacing: what tests/browser/test_r38_home_layout.py VideoStrip measures)
        self.assertIn("lite-youtube.home-yt { align-self: start; border-radius: 0; }", css)
        self.assertNotRegex(css, r"lite-youtube\.home-yt \{[^}]*align-self: stretch", "the video stretched to the words' height")

    def test_the_start_buttons_look(self):
        css = (ROOT / "src" / "assets" / "css" / "areas" / "home.css").read_text(encoding="utf-8")
        start = css[css.index("/* ---------- 1d."):css.index("/* ---------- 1e.")]
        self.assertIn("@media (width >= 80rem) { .home-choose-grid { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) "
                      "minmax(0, 1.45fr) minmax(0, 1fr); } }", start, "four in a row: the write button's column the wider one")
        self.assertIn(".home-choose-go { float: right;", start)
        self.assertNotIn("padding-right", start, "the label keeps no room for an arrow that a rule may hide")
        self.assertNotIn("display: contents", start, "the same layout at every width: the icon beside the words")
        # (round 38) at 115 % with relaxed spacing fewer columns where a word would break in two ("representante"):
        # one under the other below 672px, two in a row below 1440px — the 100 % row as it was
        relaxed115 = ':root:where(.gv-prefs)[data-text="115"][data-spacing="relaxed"] .home-choose-grid'
        self.assertIn("@media (40rem <= width < 42rem) { " + relaxed115 + " { grid-template-columns: minmax(0, 1fr); } }", start)
        self.assertIn("@media (80rem <= width < 90rem) { " + relaxed115 + " { grid-template-columns: repeat(2, minmax(0, 1fr)); } }", start)

    def test_whole_words_at_larger_text(self):
        """(round 38) the Book of the Month card's arrow and "More on this site"'s icon tiles step aside, and its grid
        takes fewer columns, where a word broke in two (what the browser draws: tests/browser/test_r38_home_layout.py
        WholeWords, tests/browser/test_r38_large_text.py HomeSmall)"""
        css = (ROOT / "src" / "assets" / "css" / "areas" / "home.css").read_text(encoding="utf-8")
        for rule in ('@media (width < 25rem) { :root:where(.gv-prefs)[data-text="115"] .home-botm-go { display: none; } }',
                     '@media (width < 30rem) { :root:where(.gv-prefs)[data-text="115"] .home-more-icon { display: none; } }',
                     '@media (40rem <= width < 48rem) { :root:where(.gv-prefs)[data-text="150"][data-spacing="relaxed"] .home-more { grid-template-columns: minmax(0, 1fr); } }',
                     '@media (64rem <= width < 72rem) { :root:where(.gv-prefs)[data-text="115"][data-spacing="relaxed"] .home-more { grid-template-columns: repeat(2, minmax(0, 1fr)); } }'):
            self.assertIn(rule, css)
        page = (ROOT / "src" / "pages" / "index.njk").read_text(encoding="utf-8")
        self.assertIn('<span class="home-botm-go shrink-0', page)

    def test_the_meeting_cards_at_larger_text(self):
        """(round 38) the two meeting cards under the hero: one column at 150 % on 768–1023px (beside the countdown or
        the buttons the date broke in two and ran past the card's edge), and a time that wraps inside itself starts its
        next line at the visible edge, as the date does ("ST" for "CST") — its dot keeps its place (what the browser
        draws: tests/browser/test_r38_home_layout.py WholeWords)"""
        css = (ROOT / "src" / "assets" / "css" / "areas" / "home.css").read_text(encoding="utf-8")
        self.assertIn('@media (48rem <= width < 64rem) {\n  :root:where(.gv-prefs)[data-text="150"] :is(.home-meet--page, '
                      '.home-gvm--page) { grid-template-columns: minmax(0, 1fr); }\n}', css)
        self.assertIn(".home-gvm-date { padding-inline-start: 0.75rem; text-indent: -0.75rem; }", css)
        self.assertIn(".home-gvm-time { padding-inline-start: 0.75rem; text-indent: -0.75rem; }", css)
        dot = re.search(r"\.home-gvm-row > \*::before \{[^}]*\}", css)
        self.assertIsNotNone(dot)
        self.assertIn("text-indent: 0;", dot.group(0), "the dot is not moved by the inherited indent")


def post(slug: str, title: str, date: str, pinned: bool = False, expires: str | None = None, status: str = "ok") -> dict:
    extra = {"slug": slug, "pinned": pinned, "body_md": "Words."}
    if expires:
        extra["expires"] = expires
    return {"id": "ann:" + slug, "source": "committee", "kind": "announcement", "url": "/bulletin/#" + slug, "title": title,
            "summary": title + " — " + "a long line of what the post says, " * 8, "lang": "en", "date": date,
            "first_seen": date + "T12:00:00Z", "category": "manual", "status": status, "extra": extra}


PINNED_DATA = {"announcements": {"updated": "2026-11-26T06:00:00Z", "items": [
    post("2026-11-20-newest-not-pinned", "Newest, not pinned", "2026-11-20"),
    post("2026-11-11-holiday-offers", "Holiday offers", "2026-11-11", pinned=True, expires="2026-12-31"),
    post("2026-10-01-over", "Pinned but over", "2026-10-01", pinned=True, expires="2026-11-01"),
    post("2026-09-15-gone", "Pinned but gone", "2026-09-15", pinned=True, status="gone"),
    post("2026-09-01-standing", "A standing notice", "2026-09-01", pinned=True),
    post("2026-08-01-third", "A third pinned post", "2026-08-01", pinned=True),
]}}
NONE_PINNED = {"announcements": {"updated": "2026-11-26T06:00:00Z", "items": [
    post("2026-11-20-newest-not-pinned", "Newest, not pinned", "2026-11-20"),
    post("2026-10-01-over", "Pinned but over", "2026-10-01", pinned=True, expires="2026-11-01"),
]}}


def build_with(case, data: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="gv-home-pins-") as folder:
        for name, body in data.items():
            Path(folder, name + ".json").write_text(json.dumps(body), encoding="utf-8")
        return run_js(case, PAGES_JS, now="2026-11-26T15:00:00Z", timeout=600, env={"SITE_DATA": folder, "WRITERS_ARCHIVE": ""})


class PinnedBulletin(unittest.TestCase):
    built: dict | None = None

    def setUp(self):
        if PinnedBulletin.built is None:
            PinnedBulletin.built = {"pinned": build_with(self, PINNED_DATA), "none": build_with(self, NONE_PINNED)}

    def test_the_pinned_posts_near_the_top(self):
        for url, lang in (("/", "en"), ("/es/", "es")):
            with self.subTest(url=url):
                page = main_of(PinnedBulletin.built["pinned"][url])
                pre = "/es" if lang == "es" else ""
                at = page.index('<section class="card home-pins"')
                self.assertLess(page.index('<section class="card home-choose"'), at, "after the four buttons")
                self.assertLess(at, page.index('aria-labelledby="mag-title"'), "before the magazines")
                sec = page[at:page.index("</section>", at)]
                self.assertIn("data-gv-expire-list", sec)
                self.assertEqual(text(re.search(r'<h2 id="pins-title"[^>]*>(.*?)</h2>', sec, re.S).group(1)), t("home.pins_title", lang))
                rows = re.findall(r'<li class="home-pin"([^>]*)>(.*?)</li>', sec, re.S)
                self.assertEqual([text(re.search(r"<h3[^>]*>(.*?)</h3>", r).group(1)) for _, r in rows], ["Holiday offers", "A standing notice"],
                                 "the pinned posts still on, two at most, newest first")
                self.assertIn('data-gv-expire="2027-01-01T06:00:00.000Z"', rows[0][0], "gone after December 31, Central time")
                self.assertNotIn("data-gv-expire=", rows[1][0])
                for slug, (_, r) in zip(("2026-11-11-holiday-offers", "2026-09-01-standing"), rows):
                    one = text(re.search(r'<p class="home-pin-text">(.*?)</p>', r, re.S).group(1))
                    self.assertLessEqual(len(one), 161, one)
                    link = re.search(r'<a class="home-pin-read[^"]*" href="([^"]+)">(.*?)</a>', r, re.S)
                    self.assertEqual(link.group(1), f"{pre}/bulletin/#{slug}")
                    title = text(re.search(r"<h3[^>]*>(.*?)</h3>", r).group(1))
                    name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", link.group(2)))).strip()
                    self.assertEqual(name, f'{t("home.pins_read", lang)}: {title}', "named by its post")
                for gone in ("Newest, not pinned", "Pinned but over", "Pinned but gone", "A third pinned post"):
                    self.assertNotIn(gone, sec)

    def test_no_pinned_post_no_card(self):
        for url in ("/", "/es/"):
            with self.subTest(url=url):
                page = PinnedBulletin.built["none"][url]
                self.assertNotIn("home-pins", page)
                self.assertNotIn("pins-title", page)

    def test_its_look(self):
        css = (ROOT / "src" / "assets" / "css" / "areas" / "home.css").read_text(encoding="utf-8")
        for rule in (".home-pins {", ".home-pin + .home-pin {", ".home-pin-text {", "line-clamp: 1;"):
            self.assertIn(rule, css)


if __name__ == "__main__":
    unittest.main()
