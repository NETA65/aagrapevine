"""Round 35 · an event's own page (src/pages/event-share-leaf.njk): the events that are LEAVES (eleventy/filters/
committee.js eventLeaf — still to come, held at a place with a real address in both languages, not a date of a monthly
series, not from Grapevine's or La Viña's own calendars, no page of their own elsewhere) get a real page at the address
their card's Share button sends, /events/<anchor>/ (/es/events/<anchor>/). Google's event results take only "a unique
URL (a leaf page) and markup on that URL", on "pages that focus on a single event"; an AI answer quotes such a page
best. Since round 37 every other event has a full page there too (no more small share pages that forwarded to the
card): indexable without Event markup when it is still to come (src/pages/event-share-leaf.njk, eventPagePlan's tier
"page"), noindex and out of the sitemap for a series' date, an outside calendar's event or one that is over
(src/pages/event-share-date.njk) — tests/test_r37_event_pages.py checks those pages' sections.

A build of the two templates and the sitemap (ONLY=event-share,sitemap) with these events (SITE_DATA: never the
day's data), checked as search engines read it:

  * Which pages: the leaves' in both languages, each written once; since round 37 the others' full pages (the site's
    layout, never location.replace): indexable without Event markup, or noindex (a series' date, an outside calendar's
    event, one that is over — out of the sitemap).
  * A leaf page: the site's layout (header, footer, the site's graph with its breadcrumb Home → Events → the event),
    its own canonical, its twin by hreflang (+ x-default), indexable, in the sitemap with its pair; its <title> names
    its day (two events of one name never share one) and ends "· Events — NETA 65"; a description of its day, its
    place in brief (the venue and its city) and its summary, at most 160 characters as every page's (og:description
    the same); its share picture the flyer (else the committee's card), as its share page had it.
  * Its ONE Event (cmEventPageLd), the FIRST ld+json block in the page's <body> (the site graph is in <head>): exactly the Event /events/ gives the same event,
    its url the page itself, its times with the Central offset — never how to join online, never a person's name.
  * What people read, with no script: the title (h1); its day, time and zone; its kind; the place; the WHOLE
    description (the card shows 3 lines of it); how to join a hybrid event, as on the card; Add to calendar (Google,
    Outlook, the .ics file); View flyer; Share (this page); "See all events" (its card on /events/).
  * The [seo] check finds nothing in that build (every listed page its own canonical and indexable, no title twice).

Runs Eleventy with Node.js (tests/nodejs.py); skipped without Node.js / the npm packages.

    python -m unittest tests.test_r35_ev_pages -v
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

BASE = "https://x.test"
DRIVE_ID = "1AbCdEfGhIjKlMnOpQrStUvWx"
LONG = ("A Spanish-language workshop on writing your story for La Viña: guidelines for contributing, how to write "
        "your story, new products, trivia, a raffle, and questions and answers. Members share what it was like to "
        "see their story published. Come in person, or join on Zoom (meeting ID 123 456 7890, passcode zz65). "
        "Coffee and pan dulce after the workshop.")


def item(slug: str, title: str, start: str, end: str, *, category: str = "manual", source: str = "committee",
         url: str = "", summary: str = "", tags: list[str] | None = None, title_es: str = "", **extra) -> dict:
    """An event as data/site/events.json holds it (build_data); a content/events file's (category manual) has its
    file name as its slug — its card's anchor."""
    all_day = len(start) == 10
    own = {"slug": slug} if category == "manual" else {}
    it = {"id": f"ev:{category}:{slug}", "source": source, "kind": "event", "category": category, "url": url,
          "title": title, "summary": summary, "lang": "en", "date": start, "status": "ok", "tags": tags or [],
          "extra": {"start": start, "end": end, "all_day": all_day, **own, "location": None, "online_url": None,
                    "city": None, "state": None, **extra}}
    if title_es:
        it["i18n"] = {"title": {"en": title, "es": title_es}}
        it["extra"]["own_i18n"] = {"title": {"es": title_es}}
    return it


EVENTS = [
    # a district's La Viña workshop, hybrid, with its flyer: a leaf — its summary gives the Zoom ID and passcode
    item("2099-05-02-test-workshop", "Test Writing Workshop", "2099-05-02T19:00:00-05:00", "2099-05-02T21:00:00-05:00",
         title_es="Taller de Escritura de Prueba", summary=LONG, body_md=LONG, tags=["workshop", "la-vina"],
         location="Grupo Uno, 100 Main St, Tyler, TX 75702", city="Tyler", state="TX",
         online_url="https://us02web.zoom.us/j/1234567890?pwd=abc", platform="Zoom",
         flyer_url=f"https://drive.google.com/file/d/{DRIVE_ID}/view", organizer="District 99 La Viña Committee"),
    # the same title another day: a leaf too — its <title> names its own day
    item("2099-06-06-test-workshop", "Test Writing Workshop", "2099-06-06T19:00:00-05:00", "2099-06-06T21:00:00-05:00",
         title_es="Taller de Escritura de Prueba", summary="The same workshop in June.",
         location="Grupo Dos, 200 Main St, Tyler, TX 75702", city="Tyler", state="TX"),
    # the Area's assembly, three days, no page elsewhere: a leaf (its card's own link is no page of its own)
    item("2099-03-19-test-assembly", "Test Spring Assembly", "2099-03-19", "2099-03-21", url="/events/#2099-03-19-test-assembly",
         summary="The Area's spring assembly.", tags=["assembly"],
         location="Hotel Uno, 4099 Valley View Ln, Dallas, TX 75244", city="Dallas", state="TX"),
    # NOT leaves: its own page on the Area's site; online only; a place to be announced; the booth's monthly dates;
    # La Viña's own calendar; one that is over
    item("2099-04-11-test-acm", "Test Spring ACM", "2099-04-11T17:00:00Z", "2099-04-11T22:00:00Z",
         url="https://neta65.org/event/test-acm/", tags=["acm"], location="Hall Uno, 1 Elm St, Plano, TX 75074",
         city="Plano", state="TX"),
    item("2099-05-09-online-workshop", "Online Workshop", "2099-05-09T19:00:00-05:00", "2099-05-09T21:00:00-05:00",
         online_url="https://meet.google.com/abc-defg-hij", platform="Google Meet"),
    item("2099-07-18-test-tba", "Test Summer ACM", "2099-07-18", "2099-07-18", tags=["acm"],
         location="Venue to be announced", location_tba=True),
    *[item(f"citywide-test:{d}", "GV/LV booth at CityWide", f"{d}T22:00:00Z", f"{d}T23:59:00Z", category="recurring",
           url="https://citywide.example.org", summary="Our literature table.", tags=["recurring"], host="neta",
           location="Church Uno, 9200 Inwood Road, Dallas, TX 75220", city="Dallas", state="TX", series="citywide-test",
           rule={"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "18:59"})
      for d in ("2099-04-11", "2099-05-09")],
    item("lvtest", "REUNIÓN DE PRUEBA", "2099-08-01", "2099-08-01", category="lv-calendar", source="calendar",
         url="https://www.aalavina.org/get-involved/events/2099-08-01/prueba", location="Salón Uno, 1 Main St, Dallas, TX 75201"),
    item("2000-02-05-old-workshop", "Old Workshop", "2000-02-05T15:00:00Z", "2000-02-05T17:00:00Z",
         location="Grupo Tres, 300 Main St, Tyler, TX 75702", city="Tyler", state="TX"),
]
LEAVES = ["2099-05-02-test-workshop", "2099-06-06-test-workshop", "2099-03-19-test-assembly"]
# (since round 37: still to come but no leaf — indexable pages without Event markup; the others noindex pages)
PAGES = ["2099-04-11-test-acm", "2099-05-09-online-workshop", "2099-07-18-test-tba"]
STUBS = ["2099-04-11-test-acm", "2099-05-09-online-workshop", "2099-07-18-test-tba", "ev-recurring-citywide-test-2099-04-11",
         "ev-recurring-citywide-test-2099-05-09", "ev-lv-calendar-lvtest", "2000-02-05-old-workshop"]

BUILD_JS = r"""
process.env.ONLY = "event-share,sitemap";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const C = await imp("eleventy/seo-check.js");
const K = await imp("eleventy/filters/committee.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r35-pages-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  const site = (await imp("src/_data/site.js")).default();
  // what /events/ gives each event (its Event; the page's one must be the same)
  const want = {};
  for (const lang of ["en", "es"]) {
    const evs = filters.cmCollapseRecurring(filters.cmEvents(input.items, site, lang)).filter((e) => !e.past);
    want[lang] = filters.cmEventLd(evs, site, lang, site.url + (lang === "es" ? "/es" : "") + "/events/");
  }
  out({ pages: Object.fromEntries(pages.filter((p) => p.url).map((p) => [p.url, p.content])),
        outputs: pages.map((p) => p.outputPath), problems: C.seoProblems(pages, C.siteAddress()), want });
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""


def ld_blocks(page: str) -> list:
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]


def body_ld_blocks(page: str) -> list:
    """The ld+json blocks in the page's <body>: the event's comes first there (the site-wide graph is in <head>)."""
    return ld_blocks(page[page.index("<body"):])


def head_of(page: str) -> str:
    return page.split("</head>", 1)[0]


def text_of(fragment: str) -> str:
    """The words of some HTML (no tags, no scripts, entities read, single spaces)."""
    t = re.sub(r"<script\b.*?</script>|<svg\b.*?</svg>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


class EventPages(unittest.TestCase):
    r: dict | None = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gv-r35-data-"))
        (cls.tmp / "events.json").write_text(json.dumps({"updated": "2026-11-19T12:00:00Z", "items": EVENTS}),
                                             encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def built(self) -> dict:
        if EventPages.r is None:
            EventPages.r = run_js(self, BUILD_JS, data={"items": EVENTS}, timeout=600,
                                  env={"SITE_DATA": str(self.tmp), "SITE_URL": BASE,
                                       "PATH_PREFIX": "/", "STRICT_BUILD": "", "LASTMOD": ""})
        return EventPages.r

    def page(self, path: str) -> str:
        return self.built()["pages"][path]

    def test_which_pages(self):
        r = self.built()
        for a in LEAVES + STUBS:
            for pre in ("", "/es"):
                self.assertIn(f"{pre}/events/{a}/", r["pages"], a)
        # each address written once (Eleventy stops on two templates writing one file; the list says so too)
        self.assertEqual(len(r["outputs"]), len(set(r["outputs"])))
        for a in LEAVES:
            for pre in ("", "/es"):
                with self.subTest(page=f"{pre}/events/{a}/"):
                    p = self.page(f"{pre}/events/{a}/")
                    self.assertIn('<main id="main"', p)                   # the site's layout
                    self.assertIn("</footer>", p)
                    self.assertNotIn("location.replace", p)
                    self.assertNotIn("noindex", head_of(p))
        for a in STUBS:
            for pre in ("", "/es"):
                with self.subTest(page=f"{pre}/events/{a}/"):
                    p = self.page(f"{pre}/events/{a}/")
                    # (round 37) a full page in the site's layout — indexable when still to come, else noindex —,
                    # never Event markup (no leaf) and never a forwarding script
                    self.assertEqual('<meta name="robots" content="noindex">' in p, a not in PAGES)
                    self.assertNotIn("location.replace(", p)
                    self.assertIn('<main id="main"', p)
                    self.assertEqual(body_ld_blocks(p), [])

    def test_the_head_search_engines_read(self):
        sm = self.page("/sitemap.xml")
        locs = re.findall(r"<loc>([^<]*)</loc>", sm)
        self.assertEqual(sorted(locs), sorted(f"{BASE}{pre}/events/{a}/" for a in LEAVES + PAGES for pre in ("", "/es")))
        titles = {}
        for a in LEAVES:
            for lang, pre in (("en", ""), ("es", "/es")):
                path = f"{pre}/events/{a}/"
                with self.subTest(page=path):
                    h = head_of(self.page(path))
                    self.assertIn(f'<link rel="canonical" href="{BASE}{path}">', h)
                    self.assertIn(f'<link rel="alternate" hreflang="en" href="{BASE}/events/{a}/">', h)
                    self.assertIn(f'<link rel="alternate" hreflang="es" href="{BASE}/es/events/{a}/">', h)
                    self.assertIn(f'<link rel="alternate" hreflang="x-default" href="{BASE}/events/{a}/">', h)
                    self.assertIn('<meta name="robots" content="max-image-preview:large', h)
                    # in the sitemap with its pair
                    entry = sm[sm.index(f"<loc>{BASE}{path}</loc>"):]
                    entry = entry[:entry.index("</url>")]
                    self.assertIn(f'hreflang="es" href="{BASE}/es/events/{a}/"', entry)
                    self.assertIn(f'hreflang="en" href="{BASE}/events/{a}/"', entry)
                    title = html.unescape(re.search(r"<title>(.*?)</title>", h).group(1))
                    self.assertTrue(title.endswith(" · Events — NETA 65" if lang == "en" else " · Eventos — NETA 65"), title)
                    self.assertNotIn((lang, title), titles, "no two pages of a language share a title")
                    titles[(lang, title)] = path
                    # a description, at most 160 characters as every page's (README → Search engines) — the same in
                    # og:description and the structured data's WebPage
                    desc = html.unescape(re.search(r'<meta name="description" content="([^"]{20,})"', h).group(1))
                    self.assertLessEqual(len(desc), 160, desc)
                    og = re.search(r'<meta property="og:description" content="([^"]*)"', h).group(1)
                    self.assertEqual(html.unescape(og), desc)
        self.assertEqual(titles[("en", "Test Writing Workshop, May 2, 2099 · Events — NETA 65")], "/events/2099-05-02-test-workshop/")
        self.assertEqual(titles[("en", "Test Writing Workshop, June 6, 2099 · Events — NETA 65")], "/events/2099-06-06-test-workshop/")
        self.assertEqual(titles[("es", "Taller de Escritura de Prueba, 2 de mayo de 2099 · Eventos — NETA 65")],
                         "/es/events/2099-05-02-test-workshop/")
        # its share picture: the flyer, as on its share page; else the committee's card
        h = head_of(self.page("/events/2099-05-02-test-workshop/"))
        self.assertIn(f'<meta property="og:image" content="https://lh3.googleusercontent.com/d/{DRIVE_ID}=w1200">', h)
        self.assertIn('<meta property="og:image:alt" content="Flyer: Test Writing Workshop">', h)
        self.assertIn('<meta property="og:image" content="https://x.test/assets/img/og-default-es.png?v=',
                      head_of(self.page("/es/events/2099-03-19-test-assembly/")))
        # the description: its day and time, its place in brief (the venue and its city), its summary — never how to
        # join online
        d = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', h).group(1))
        self.assertTrue(d.startswith("Saturday, May 2, 2099 · 7:00 – 9:00 PM CDT · Grupo Uno, Tyler — "
                                     "A Spanish-language workshop"), d)
        self.assertNotRegex(d, r"123 456|zz65|zoom\.us|[Pp]asscode")
        # nothing for the [seo] check: every page in the sitemap its own canonical, indexable, no title twice — and no
        # page that may be indexed left out of it (the small share pages are noindex)
        self.assertEqual(self.built()["problems"], [])

    def test_one_event_for_search_engines(self):
        want = self.built()["want"]
        for a in LEAVES:
            for lang, pre in (("en", ""), ("es", "/es")):
                path = f"{pre}/events/{a}/"
                with self.subTest(page=path):
                    p = self.page(path)
                    blocks = ld_blocks(p)
                    first = body_ld_blocks(p)[0]
                    self.assertEqual(first.pop("@context"), "https://schema.org")
                    self.assertEqual(first["@type"], "Event")
                    self.assertEqual(first["url"], BASE + path)
                    # exactly the Event /events/ gives it (its url: this page there too)
                    same = [e for e in want[lang] if e["url"] == BASE + path]
                    self.assertEqual(same, [first])
                    events = [b for b in blocks if b.get("@type") == "Event"] + \
                             [g for b in blocks for g in b.get("@graph", []) if g.get("@type") == "Event"]
                    self.assertEqual(len(events), 1, "ONE Event on the page")
                    # early: in the page content, before the hero
                    at = p.index("application/ld+json", p.index("<body"))
                    self.assertLess(at, p.index('class="gv-hero'))
                    self.assertLess(p.index('<main id="main"'), at)
                    text = json.dumps(blocks, ensure_ascii=False)
                    for word in ("zoom.us", "meet.google.com", "123 456", "zz65", "Meeting ID", "meeting ID", "asscode",
                                 '"Person"'):
                        self.assertNotIn(word, text)
                    # the site's graph: Home → Events → this event
                    crumbs = next(g for b in blocks for g in b.get("@graph", []) if g.get("@type") == "BreadcrumbList")
                    names = [(i["name"], i.get("item")) for i in crumbs["itemListElement"]]
                    self.assertEqual(names[:2], [("Home" if lang == "en" else "Inicio", f"{BASE}{pre}/"),
                                                 ("Events" if lang == "en" else "Eventos", f"{BASE}{pre}/events/")])
                    self.assertEqual(len(names), 3)
                    self.assertIsNone(names[2][1])
        ws = body_ld_blocks(self.page("/events/2099-05-02-test-workshop/"))[0]
        self.assertEqual((ws["startDate"], ws["endDate"]), ("2099-05-02T19:00:00-05:00", "2099-05-02T21:00:00-05:00"))
        self.assertEqual(ws["organizer"], {"@type": "Organization", "name": "District 99 La Viña Committee"})
        self.assertEqual(ws["eventAttendanceMode"], "https://schema.org/MixedEventAttendanceMode")
        asm = body_ld_blocks(self.page("/es/events/2099-03-19-test-assembly/"))[0]
        self.assertEqual((asm["startDate"], asm["endDate"]), ("2099-03-19", "2099-03-21"))

    def test_what_people_read(self):
        p = self.page("/events/2099-05-02-test-workshop/")
        main = p[p.index('<main id="main"'):p.index("</main>")]
        self.assertRegex(main, r'<h1 class="gv-hero-title">.*?<span>Test Writing Workshop</span>\s*</h1>')
        words = text_of(main)
        for bit in ("Saturday, May 2, 2099 · 7:00 – 9:00 PM CDT", "La Viña", "Grupo Uno, 100 Main St, Tyler, TX 75702",
                    "Online on Zoom", "Coffee and pan dulce after the workshop.", "Add to calendar", "View flyer",
                    "See all events"):
            self.assertIn(bit, words)
        # the whole description, how to join included — people see it as on the card (never in the data above); since
        # round 35 its values are never quoted by search engines (data-nosnippet: an inline <span>, no space on screen)
        self.assertIn("join on Zoom (meeting ID 123 456 7890, passcode zz65)", text_of(re.sub(r"</?span\b[^>]*>", "", main)))
        self.assertIn("(meeting ID <span data-nosnippet>123 456 7890</span>, passcode <span data-nosnippet>zz65</span>)", main)
        self.assertIn('href="https://us02web.zoom.us/j/1234567890?pwd=abc"', main)
        # the card's calendar links and file, its flyer, Share (this page), back to its card on /events/
        self.assertIn('href="https://calendar.google.com/calendar/render?action=TEMPLATE&amp;text=Test%20Writing%20Workshop', main)
        self.assertIn('href="https://outlook.live.com/calendar/0/action/compose?', main)
        self.assertIn("data-cm-ics=", main)
        self.assertIn(f'data-cm-preview="https://drive.google.com/file/d/{DRIVE_ID}/preview"', main)
        self.assertIn(f'data-share="{BASE}/events/2099-05-02-test-workshop/"', main)
        self.assertEqual(re.findall(r'href="(/events/#[^"]+)"', main), ["/events/#2099-05-02-test-workshop"] * 2)
        self.assertIn('id="cm-preview"', p)                                  # the flyer's viewer
        self.assertIn("/assets/js/committee.js?v=", p)
        # Spanish: its own words, its card on /es/events/
        es = self.page("/es/events/2099-05-02-test-workshop/")
        es_main = es[es.index('<main id="main"'):es.index("</main>")]
        self.assertIn("<span>Taller de Escritura de Prueba</span>", es_main)
        self.assertIn("Sábado, 2 de mayo de 2099", text_of(es_main))
        self.assertIn("Ver todos los eventos", text_of(es_main))
        self.assertEqual(re.findall(r'href="(/es/events/#[^"]+)"', es_main), ["/es/events/#2099-05-02-test-workshop"] * 2)
        # a range of days for the assembly; its kind
        asm = text_of(self.page("/events/2099-03-19-test-assembly/"))
        self.assertIn("Area assembly", asm)
        self.assertRegex(asm, r"Thu, Mar 19 – Sat, Mar 21, 2099|Thu, Mar 19\s*–\s*Sat, Mar 21, 2099")


class Templates(unittest.TestCase):
    """The templates share one plan (since round 37 eleventy/event-page-model.js eventPageData, from
    eleventy/event-pages.js eventPagePlan), so no address is written twice."""

    def test_the_two_paginations(self):
        leaf = (ROOT / "src" / "pages" / "event-share-leaf.njk").read_text(encoding="utf-8")
        share = (ROOT / "src" / "pages" / "event-share-date.njk").read_text(encoding="utf-8")
        self.assertIn("eventPageData(full).pages.filter((p) => p.index)", leaf)
        self.assertIn("eventPageData(full).pages.filter((p) => !p.index)", share)
        self.assertIn('const layout = "layouts/base.njk";', leaf)
        self.assertIn('const pageKey = "events";', leaf)
        # (a file of the share pages: the names ONLY= builds pick up together — tests/test_r24_retired_room.py)
        self.assertTrue(Path(ROOT / "src" / "pages" / "event-share-leaf.njk").name.startswith("event-share"))


if __name__ == "__main__":
    unittest.main()
