"""Stay updated (/stay-updated/, /es/stay-updated/ — src/pages/stay-updated.njk, src/_i18n/stay.json): one page that
gathers every way to keep up with the committee.

  * Menus   — src/_data/nav.js lists it in `footer` (group "hub"): the footer's "Stay updated" column opens with it
              ("All the ways to stay updated"), the phone menu's "More" lists it, and the site search finds it (its
              own description and search words); the home page's "More on this site" links it.
  * Page    — one build (English and Spanish): its four parts (#email, #calendar, #feeds, #phone) in the page nav and
              in that order; the monthly digest (this month's on /digest/, and a ready-made e-mail asking to be added,
              to the committee's address — no form, nothing sent by the site —, the address written out too, with a
              button to copy it; its words promise only what the chair does, never the automatic e-mail, which is
              off until its secrets are set); the calendars to subscribe to —
              /events.ics and /deadlines.ics, each with Google Calendar's link, its webcal:// address and its address
              to copy, and the how-to on its own page (the deadlines' only while one is open: Share your story's
              how-to section is there only then) —; the files to add once (this month's dates, the weekly open
              meetings); the RSS feed, Instagram, YouTube and the podcasts; the app and saved pages (/offline/), the QR
              Post (/share/) and WhatsApp (wa.me: the site's name and address only); every address in the page
              language.
  * Search  — the sitemap lists both languages (with their hreflang pair) and each language's search index has the
              page (the whole site's build: tests/test_seo_sitemap.py and the [seo] check do the rest).

    python -m unittest tests.test_stay_updated -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STAY = json.loads((ROOT / "src" / "_i18n" / "stay.json").read_text(encoding="utf-8"))
COMMON = json.loads((ROOT / "src" / "_i18n" / "common.json").read_text(encoding="utf-8"))
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))["site"]

PAGES_JS = r"""
process.env.ONLY = "stay-updated,sitemap,search-index,events-ics,deadlines-ics,feed,meetings-weekly-ics,monthly-ics";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-stay-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  const want = new Set(["/stay-updated/", "/es/stay-updated/", "/sitemap.xml", "/search-index.json", "/es/search-index.json",
                        "/deadlines.ics", "/es/deadlines.ics"]);
  out(Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class Menus(unittest.TestCase):
    def test_footer_drawer_and_home(self):
        nav = read("src", "_data", "nav.js")
        self.assertIn('{ key: "nav.stay_updated", url: "/stay-updated/", page: "stay-updated", icon: "bell-ring", group: "hub" }', nav)
        footer = read("src", "_includes", "partials", "footer.njk")
        self.assertIn('{% if f.group == "hub" %}', footer)
        self.assertIn('"nav.stay_updated_all" | t(L)', footer)
        # the column's first link: before the official sites
        self.assertLess(footer.index('f.group == "hub"'), footer.index("officialSites"))
        # (round 38) its icon steps aside at 115 % with relaxed spacing on 640–719px, where the four groups share a row:
        # beside it "mantenerte" broke in two (what the browser draws: tests/browser/test_r38_large_text.py FooterHub)
        self.assertIn('<a class="site-footer-hub inline-flex', footer)
        access = read("src", "assets", "css", "areas", "access.css")
        self.assertIn('@media (40rem <= width < 45rem) { :root:where(.gv-prefs)[data-text="115"][data-spacing="relaxed"] '
                      '.site-footer-hub > .icon { display: none; } }', access)
        # (round 38b) the official sites after it: a <wbr> before ".org", and never a break inside "aagrapevine" — each
        # link's line is a size container whose grapes icon (and, with relaxed spacing, arrow) steps aside where the line
        # is narrower than the name beside them, in em (what the browser draws: tests/browser/test_r38_large_text.py
        # FooterHub)
        self.assertIn('<li class="site-footer-official flex"><a class="inline-flex', footer)
        self.assertIn('{{ u | hostname | replace(".", "<wbr>.") | safe }}', footer)
        self.assertIn(".site-footer-official { container: ft-site / inline-size; }", access)
        self.assertIn("@container ft-site (width < 9.1em) { .site-footer-official > a > .icon:first-child { display: none; } }", access)
        header = read("src", "_includes", "partials", "header.njk")
        self.assertIn('{%- for f in nav.footer %}{% if f.page != "search" %}', header, "the phone menu's More lists every footer page")
        self.assertIn('{ url: "/stay-updated/", icon: "bell-ring", key: "nav.stay_updated", desc: "stay.short_desc" }', read("src", "pages", "index.njk"))

    def test_its_words(self):
        for k, v in STAY.items():
            with self.subTest(key=k):
                self.assertTrue(v["en"].strip() and v["es"].strip())
                self.assertEqual(set(re.findall(r"\{(\w+)\}", v["en"])), set(re.findall(r"\{(\w+)\}", v["es"])))
        self.assertIn("search.page_desc.stay-updated", STAY)
        self.assertIn("search.kw.stay-updated", STAY)


class Page(unittest.TestCase):
    built: dict | None = None

    def setUp(self):
        if Page.built is None:
            Page.built = run_js(self, PAGES_JS, timeout=900)
        self.p = Page.built

    def each(self):
        for url, lang, pre in (("/stay-updated/", "en", ""), ("/es/stay-updated/", "es", "/es")):
            with self.subTest(url=url):
                yield self.p[url], lang, pre

    def test_the_parts_in_order(self):
        for page, lang, pre in self.each():
            at = [page.index(f'<section id="{s}"') for s in ("email", "calendar", "feeds", "phone")]
            self.assertEqual(at, sorted(at))
            nav = page[page.index('class="page-nav'):]
            nav = nav[:nav.index("</nav>")]
            self.assertEqual(re.findall(r'href="(#[a-z]+)"', nav), ["#email", "#calendar", "#feeds", "#phone"])
            self.assertIn(f"<title>{COMMON['nav.stay_updated'][lang]} · ", page)

    def test_the_digest(self):
        for page, lang, pre in self.each():
            sec = page[page.index('<section id="email"'):page.index('<section id="calendar"')]
            self.assertIn(f'href="{pre}/digest/"', sec)
            mail = html.unescape(re.search(r'href="(mailto:[^"]+)"', sec).group(1))
            u = urlparse(mail)
            self.assertEqual(u.path, SITE["contact_email"])
            q = parse_qs(u.query)
            self.assertEqual(q["subject"], [STAY["stay.email_subject"][lang]])
            self.assertEqual(q["body"], [STAY["stay.email_body"][lang]])
            self.assertNotIn("<form", sec)
            # the address as text, and to copy (a device with no mail app opens nothing for mailto:)
            shown = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(sec)))
            self.assertIn(f'{STAY["stay.email_to"][lang]} {SITE["contact_email"]} ', shown)
            self.assertIn(f'data-copy="{SITE["contact_email"]}"', sec)
            # it promises only what a person does (ask the chair; to stop, write to the same address): the automatic
            # monthly e-mail, and the "unsubscribe" reply its footer asks for, go out only once its secrets are set
            self.assertIn(STAY["stay.email_join_text"][lang], shown)
            self.assertIn(STAY["stay.email_leave"][lang], shown)
            self.assertNotIn("unsubscribe", shown.lower())

    def test_the_calendars(self):
        base = SITE["url"].rstrip("/")
        for page, lang, pre in self.each():
            sec = page[page.index('<section id="calendar"'):page.index('<section id="feeds"')]
            # (the deadlines' how-to, /contribute/#deadlines-calendar, is on that page only while a deadline is open —
            # the same open deadlines as the calendar file's)
            open_dl = "BEGIN:VEVENT" in self.p[pre + "/deadlines.ics"]
            self.assertEqual(f'href="{pre}/contribute/#deadlines-calendar"' in sec, open_dl)
            for path, howto in (("/events.ics", "/events/#subscribe"), ("/deadlines.ics", "/contribute/#deadlines-calendar" if open_dl else "")):
                feed = base + pre + path
                webcal = feed.replace("https://", "webcal://").replace("http://", "webcal://")
                self.assertIn(f'data-copy="{feed}"', sec)
                self.assertIn(f'href="{webcal}"', sec)
                gcal = [unquote(h.replace("&amp;", "&")) for h in re.findall(r'href="(https://calendar\.google\.com/calendar/r\?cid=[^"]+)"', sec)]
                self.assertIn("https://calendar.google.com/calendar/r?cid=" + webcal, gcal)
                if howto:
                    self.assertIn(f'href="{pre}{howto}"', sec)
            # the files to add once: this month's (the Monthly toolkit's) and the weekly open meetings'
            self.assertRegex(sec, r'href="%s/monthly/\d{4}-\d{2}/neta65-grapevine-\d{4}-\d{2}-%s\.ics" type="text/calendar"' % (pre, lang))
            for f in re.findall(r'href="([^"]*weekly-open-[a-z]+\.ics)"', sec):
                self.assertTrue(f.startswith(pre + "/meetings/weekly-open-"), f)

    def test_feeds_and_the_phone(self):
        base = SITE["url"].rstrip("/")
        for page, lang, pre in self.each():
            feeds = page[page.index('<section id="feeds"'):page.index('<section id="phone"')]
            self.assertIn(f'href="{pre}/feed.xml"', feeds)
            self.assertIn(f'data-copy="{base}{pre}/feed.xml"', feeds)
            for u in ("/instagram/", "/watch/", "/listen/"):
                self.assertIn(f'href="{pre}{u}"', feeds)
            phone = page[page.index('<section id="phone"'):page.index("</main>")]
            self.assertIn(f'href="{pre}/offline/#steps"', phone)
            self.assertIn(f'href="{pre}/share/"', phone)
            wa = re.search(r'href="https://wa\.me/\?text=([^"]+)"', phone).group(1)
            msg = unquote(wa)
            self.assertTrue(msg.endswith(base + pre + "/"), msg)
            self.assertNotIn("@", msg, "nothing but the site's name and address")

    def test_in_the_sitemap_and_the_search(self):
        sm = self.p["/sitemap.xml"]
        for url in ("/stay-updated/", "/es/stay-updated/"):
            self.assertIn(f"<loc>{SITE['url'].rstrip('/')}{url}</loc>", sm)
        for lang, url in (("en", "/search-index.json"), ("es", "/es/search-index.json")):
            idx = json.loads(self.p[url])
            docs = idx["items"]
            hit = [d for d in docs if d.get("id") == "page:stay-updated"]
            with self.subTest(lang=lang):
                self.assertEqual(len(hit), 1, "the page is in the site search")
                self.assertEqual(hit[0]["t"], COMMON["nav.stay_updated"][lang])
                self.assertEqual(hit[0]["s"], STAY["search.page_desc.stay-updated"][lang])
                self.assertEqual(hit[0]["ic"], "bell-ring")


if __name__ == "__main__":
    unittest.main()
