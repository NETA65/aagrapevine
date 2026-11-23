"""Round 37 · every event's own page, every monthly series' page — built at every build from the data alone
(eleventy/event-pages.js eventPagePlan: which page, its tier, its address; eleventy/event-page-model.js eventPageData:
what it says; the templates src/pages/event-share-leaf.njk (indexable), event-share-date.njk (noindex) and
event-share-series.njk (/events/series/<key>/); src/_includes/partials/event-page.njk). A build of those templates and
the sitemap (ONLY=event-share,sitemap) from a fixture (SITE_DATA: never the day's data) at a fixed moment in 2099:

  * Tiers        — the sitemap's event addresses are exactly the indexable pages (upcoming one-off events and the series'
                   pages); every other event's page (a series' date, an outside calendar's, one that is over) is noindex
                   and out of the sitemap; each page has its twin; no two pages of a language share a <title>; every
                   description ≤ 160 characters; the [seo] check finds nothing; no page forwards (no location.replace).
  * Each kind    — the links the owner asked for, by kind: a writing workshop's presentation (/orientation/?present=
                   writing-workshop and its card), its GVR/RLV Bingo card filled in (lang, magazine, occasion, title,
                   day), Share your story, the booth display (/about/#booth, and /about/?booth=start — never `bs`, which
                   would replace that device's booth settings), the flyers of similar events (never its own); an
                   assembly with its page on the Area's site: that page first; a GSR/DCM orientation: the Area's site,
                   GVR / RLV 101's lesson, the GVR corner's #job; an outside calendar's event: its own page and the
                   calendars' filter; a series' page: its next dates, each to its date's page.
  * Privacy      — an event that is over shows no way to join (no meeting ID, no online link, no calendar menu, never its
                   body — its summary without how to join); no ld+json or meta description gives a meeting link, ID or
                   code; only a "leaf" carries its Event (the same as /events/ gives it).
  * Lastmod      — the blocks that change with OTHER events and the months (next of its kind, coming up, past ones,
                   similar flyers, the magazines) are data-lastmod="skip" (eleventy/lastmod.js leaves them out of the
                   page's date); a series' list of its dates is its own content.
  * Automation   — a second build with one more event file (a GVR/RLV orientation, a kind the first data lacks) and one
                   more dated Drive flyer: both get their pages, in the sitemap, with their kind's sections — no
                   template, no list written by hand.
  * Parity       — the content/events `type:` values the sync accepts (scripts/sync/announcements.py EVENT_TYPES) are
                   exactly the page kinds (eleventy/event-pages.js EVENT_KINDS).
  * Every kind   — the model alone (eventPageData) on a settings fixture: each kind's presentation, bingo occasion and
                   resources in order (a kind with none: the magazines' own links), a GVR / RLV 101 lesson's own
                   summary, "Official page" only for an event's own page elsewhere (never a site's home page, our own
                   site or a meeting's room), the lede of an online event over several days, our committee's name in
                   Spanish, no "held in English" guessed, a bingo title never cut inside its brackets.

The settings: the build reads config/site.yml, config/presentations and config/orientation.yml as the committee keeps
them (a gated test — scripts/ops/gate_tests.py: the committee's edits may never stop the publishing), so what these
pages show from them FOLLOWS them here: the monthly series' dates are the ones config/site.yml's rules give (the
series' checks only for a series that is on), a presentation's or a lesson's link only when it is there, the links
config/site.yml gives. "Every kind" builds nothing and reads none of them (its own settings, decks and lessons).

Runs Eleventy with Node.js (tests/nodejs.py); skipped without Node.js / the npm packages.

    python -m unittest tests.test_r37_event_pages -v
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_r37_spine import CW, GVM, CW_PLACE, SAT, WED, at, item, nth_weekday, place, series_date  # noqa: E402
from test_r37_spine import SITE as SPINE_SITE  # noqa: E402

NOW = "2099-01-10T18:00:00Z"
BASE = "https://x.test"
OWN = "1OwnFlyerAbCdEfGhIjKlMnOpQr"
OTHER = "1OtherFlyerAbCdEfGhIjKlMnOp"
NEW_FLYER = "1NewDatedFlyerAbCdEfGhIjKl"
TYLER = place("Grupo Uno", "100 Main St", "Tyler", "75702")
PLANO = place("Hall Dos", "2 Elm St", "Plano", "75074")
LONGVIEW = place("Grupo Tres", "3 Oak St", "Longview", "75601")
PAST_SUMMARY = "Learn to write your story. Join on Zoom (meeting ID 987 654 3210, passcode zz65)."
PAST_BODY = "Learn to write your story. Bring a pen and paper. Zoom meeting ID 987 654 3210, passcode zz65."
SVG_FLYER = "https://www.aalavina.org/sites/default/files/flyer.svg"
JPG_FLYER = "https://www.aagrapevine.org/sites/default/files/flyer.jpg"

WS = "2099-02-06-lv-writing-workshop-tyler"
PAST = "2098-12-05-gv-writing-workshop-plano"
ASM = "2099-03-20-test-spring-assembly"
GSR = "2099-01-24-gsr-dcm-orientation-west"
ONLINE = "2099-02-20-lv-information-workshop-online"
CAL = "ev-lv-calendar-lvcal1"
SVG = "ev-lv-calendar-svgflyer"
JPG = "ev-gv-calendar-jpgflyer"
# the monthly series the event pages are checked on — their dates are config/site.yml's (settings(), below)
SERIES = ("citywide-dallas", "grapevine-meeting")
cw = [nth_weekday(2099, m, SAT, 2) for m in (1, 2, 3)]
gvm = [nth_weekday(2099, m, WED, 1) for m in (2, 3)]
CW_DATES = [f"ev-recurring-citywide-dallas-{d.isoformat()}" for d in cw]   # (Every kind's own settings: SPINE_SITE)

EVENTS = [
    # a district's La Viña writing workshop with its flyer: a leaf
    item(WS, "La Viña Writing Workshop — Tyler", at(date(2099, 2, 6), "19:00"), at(date(2099, 2, 6), "21:00"),
         title_es="Taller de Escritura de La Viña — Tyler", tags=["workshop", "la-vina"],
         flyer_url=f"https://drive.google.com/file/d/{OWN}/view", organizer="District 99 La Viña Committee", **TYLER),
    # one that is over, hybrid: its summary and body give its Zoom room
    item(PAST, "Grapevine Writing Workshop — Plano", at(date(2098, 12, 5), "14:00"), at(date(2098, 12, 5), "17:00"),
         tags=["workshop", "grapevine"], summary=PAST_SUMMARY, body_md=PAST_BODY, past=True,
         online_url="https://us02web.zoom.us/j/9876543210?pwd=zzz", meeting_id="987 654 3210", platform="Zoom", **PLANO),
    # the Area's assembly with its page on the Area's site: indexable, no Event markup ("page")
    item(ASM, "Test Spring Assembly", "2099-03-20", "2099-03-22", url="https://neta65.org/event/test-assembly/",
         tags=["neta65", "assembly"], **PLANO),
    # the Area's GSR/DCM orientation: a leaf
    item(GSR, "GSR/DCM Orientation — West", at(date(2099, 1, 24), "13:00"), at(date(2099, 1, 24), "18:00"),
         tags=["neta65", "gsr-dcm-orientation"], **TYLER),
    # an online-only information workshop: indexable, no Event markup
    item(ONLINE, "La Viña Information Workshop (online)", at(date(2099, 2, 20), "10:00"), at(date(2099, 2, 20), "12:00"),
         tags=["workshop", "la-vina"], online_url="https://us02web.zoom.us/j/5555555555", platform="Zoom",
         meeting_id="555 555 5555"),
    # La Viña's own calendar: noindex
    item("lvcal1", "Reunión de Prueba", "2099-02-28", "2099-02-28", category="lv-calendar", source="calendar",
         url="https://www.aalavina.org/get-involved/events/2099-02-28/prueba", location="Salón Uno, 1 Main St, Dallas, TX 75201"),
    # the magazines' calendars with a flyer each: an SVG (no picture the previews show: the committee's share card)
    # and a JPEG (itself) — noindex pages, their heads as rendered
    item("svgflyer", "Reunión del Volante SVG", at(date(2099, 6, 1), "14:00"), at(date(2099, 6, 1), "15:00"),
         category="lv-calendar", source="calendar", flyer_url=SVG_FLYER, flyer_thumb=SVG_FLYER),
    item("jpgflyer", "Grapevine JPEG Flyer Gathering", at(date(2099, 7, 1), "14:00"), at(date(2099, 7, 1), "15:00"),
         category="gv-calendar", source="calendar", flyer_url=JPG_FLYER, flyer_thumb=JPG_FLYER),
    # (+ the CityWide booth's and the Grapevine Meeting's next dates as config/site.yml gives them: events(), below —
    # noindex dates, a page each, and each series' own page)
]
DRIVE = [
    {"id": f"drive:{fid}", "source": "drive", "kind": "photo", "url": f"https://drive.google.com/file/d/{fid}/view",
     "title": title, "lang": "es", "date": "2098-12-01", "category": "flyers", "status": "ok", "tags": [],
     "extra": {"file_id": fid, "view_url": f"https://drive.google.com/file/d/{fid}/view"}}
    for fid, title in ((OWN, "Taller de Escritura de La Viña - Grupo Uno, Tyler"),
                       (OTHER, "Taller de Escritura de La Viña - Grupo Dos, Plano"))
]
# the second build's additions: an event file of a kind the first data lacks, and a dated Drive flyer's event
NEW = "2099-02-13-gvr-rlv-orientation-longview"
NEW_EVENTS = [
    item(NEW, "GVR/RLV Orientation Workshop — Longview", at(date(2099, 2, 13), "10:00"), at(date(2099, 2, 13), "13:00"),
         title_es="Taller de orientación para RLV y GVR — Longview", tags=["workshop"], **LONGVIEW),
    {**item(f"flyer-{NEW_FLYER}", "Grapevine Writing Workshop - Grupo Cuatro, Paris", at(date(2099, 3, 6), "15:00"),
            at(date(2099, 3, 6), "17:00"), category="flyer", source="drive", ident=f"ev:flyer:{NEW_FLYER}",
            url=f"https://drive.google.com/file/d/{NEW_FLYER}/view", drive_id=NEW_FLYER,
            **place("Grupo Cuatro", "4 Pine St", "Paris", "75460")), "tags": []},
]

# What the build reads from the committee's settings, as they are today (see the module's docstring): each series' next
# 6 dates after NOW as config/site.yml's rule gives them (seriesNext — the records build_data writes for them, its
# page's title words, its kind, how to join it), the presentations and the GVR / RLV 101 lessons there are, whether
# the committee meeting has a date to come, config/site.yml's links and the committee's names.
SETTINGS_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const P = await imp("eleventy/event-pages.js");
const val = async (m) => { const d = (await imp(m)).default; return typeof d === "function" ? await d() : d; };
const site = { ...(await val("src/_data/site.js")), built: input.now, url: input.base };
const now = new Date(input.now);
const series = {};
for (const key of input.keys) {
  const s = C.seriesNext(site, key, "en", [], { now, n: 6 });
  if (!s) continue;
  const k = P.eventKind(s.next, site);
  series[key] = { title: s.title, recurrenceDay: s.recurrenceDay, items: s.dates.map((d) => d.item),
    anchors: s.dates.map((d) => d.anchor), meetingId: (s.join && s.join.id) || "", online: (s.join && s.join.url) || "",
    kind: k.kind, deck: k.deck, link: s.next.linkExternal ? String(s.next.link || "") : "" };
}
out({ series, decks: ((await val("src/_data/presentations.js")).decks || []).map((d) => d.id),
      lessons: ((await val("src/_data/orientation.js")).lessons || []).map((l) => l.id),
      meeting: !!C.normalizeEvents([], site, "en", { monthsBack: 0, monthsAhead: 14, now }).find((e) => e.committee && !e.past),
      gvrRegister: (site.links || {}).gvr_register || "", committee: site.committee || "",
      committeeEs: site.committee_es || site.committee || "", area: site.area || "", areaEs: site.area_es || site.area || "" });
"""
_settings: dict | None = None


def settings(case: unittest.TestCase) -> dict:
    global _settings
    if _settings is None:
        _settings = run_js(case, SETTINGS_JS, data={"keys": list(SERIES), "now": NOW, "base": BASE}, now=NOW)
    return _settings


def events(case: unittest.TestCase) -> list:
    """The fixture's events, with each series' next dates as the settings give them."""
    return EVENTS + [it for s in settings(case)["series"].values() for it in s["items"]]


def join_words(case: unittest.TestCase) -> tuple:
    """The ways in no machine copy may give: the fixture's, and the settings' series' (their codes, their links)."""
    s = settings(case)["series"].values()
    return JOIN + tuple(w for x in s for w in (x["meetingId"], re.sub(r"^https?://(?:www\.)?", "", x["online"])) if w)


BUILD_JS = r"""
// (and the deadlines' calendar: an event page links it in its language, /es/deadlines.ics)
process.env.ONLY = "event-share,sitemap,deadlines-ics";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const C = await imp("eleventy/seo-check.js");
const LM = await imp("eleventy/lastmod.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r37-evp-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  const site = (await imp("src/_data/site.js")).default();
  const want = {};
  for (const lang of ["en", "es"]) {
    const evs = filters.cmCollapseRecurring(filters.cmEvents(input.items, { ...site, built: input.now }, lang)).filter((e) => !e.past);
    want[lang] = filters.cmEventLd(evs, site, lang, site.url + (lang === "es" ? "/es" : "") + "/events/");
  }
  const ev = pages.filter((p) => /\/events\/./.test(p.url || "") || p.url === "/sitemap.xml");
  out({ pages: Object.fromEntries(ev.map((p) => [p.url, p.content])), outputs: pages.map((p) => p.outputPath),
        problems: C.seoProblems(pages, C.siteAddress()), want,
        dated: Object.fromEntries(ev.filter((p) => /\/events\//.test(p.url)).map((p) => [p.url, LM.dropSkipped(p.content)])) });
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""

JOIN = ("meet.google.com", "zoom.us", "rva-tmst-vdb", "987 654 3210", "9876543210", "555 555 5555", "zz65")


def build(case: unittest.TestCase, items: list, drive: list) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="gv-r37-evp-data-"))
    try:
        (tmp / "events.json").write_text(json.dumps({"updated": NOW, "items": items, "cancelled": []}), encoding="utf-8")
        (tmp / "drive.json").write_text(json.dumps({"updated": NOW, "items": drive}), encoding="utf-8")
        return run_js(case, BUILD_JS, data={"items": items, "now": NOW}, timeout=900, now=NOW,
                      env={"SITE_DATA": str(tmp), "CONTENT_EVENTS": str(tmp / "none"), "SITE_URL": BASE,
                           "PATH_PREFIX": "/", "STRICT_BUILD": "", "LASTMOD": ""})
    finally:
        shutil.rmtree(tmp, True)


def head_of(page: str) -> str:
    return page.split("</head>", 1)[0]


def main_of(page: str) -> str:
    return page[page.index('<main id="main"'):page.index("</main>")]


def text_of(fragment: str) -> str:
    t = re.sub(r"<script\b.*?</script>|<svg\b.*?</svg>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def body_ld(page: str) -> list:
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                              page[page.index("<body"):], re.S)]


def section(page: str, h_id: str) -> str:
    """The <section> (or the block) labelled by `h_id`, with its opening tag."""
    at_ = page.index(f'aria-labelledby="{h_id}"')
    start = page.rindex("<", 0, at_)
    return page[start:page.index("</section>", at_)]


def noindex(page: str) -> bool:
    return '<meta name="robots" content="noindex">' in head_of(page)


def metas(page: str) -> dict[str, str]:
    """The head's <meta property|name=… content=…> (the first of each)."""
    out: dict[str, str] = {}
    for k, v in re.findall(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"', head_of(page)):
        out.setdefault(k, html.unescape(v))
    return out


class EventPages(unittest.TestCase):
    r: dict | None = None

    def built(self) -> dict:
        if EventPages.r is None:
            EventPages.r = build(self, events(self), DRIVE)
        return EventPages.r

    def page(self, path: str) -> str:
        return self.built()["pages"][path]

    def event_pages(self) -> dict:
        return {u: p for u, p in self.built()["pages"].items() if re.fullmatch(r"(/es)?/events/.+/", u)}

    def series(self, key: str) -> dict | None:
        """A series as config/site.yml gives it (None: it is off, or has no date to come — its checks are left out)."""
        return settings(self)["series"].get(key)

    def test_tiers_and_the_sitemap(self):
        r = self.built()
        pages = self.event_pages()
        sm = r["pages"]["/sitemap.xml"]
        locs = {loc[len(BASE):] for loc in re.findall(r"<loc>([^<]*)</loc>", sm)}
        indexable = {u for u, p in pages.items() if not noindex(p)}
        self.assertEqual({u for u in locs if "/events/" in u}, indexable)
        series = settings(self)["series"]
        want = {f"{pre}/events/{a}/" for a in (WS, ASM, GSR, ONLINE) for pre in ("", "/es")} | \
               {f"{pre}/events/series/{k}/" for k in series for pre in ("", "/es")}
        self.assertEqual(indexable, want)
        for a in (PAST, CAL, SVG, JPG, *(a for s in series.values() for a in s["anchors"])):
            for pre in ("", "/es"):
                p = pages[f"{pre}/events/{a}/"]
                with self.subTest(page=f"{pre}/events/{a}/"):
                    self.assertTrue(noindex(p))
                    self.assertIn(f'<link rel="canonical" href="{BASE}{pre}/events/{a}/">', p)
                    self.assertNotIn("hreflang", head_of(p))
                    self.assertNotIn("application/ld+json", p, "no structured data on a noindex page")
                    self.assertIn('<main id="main"', p)                      # a full page, never a forwarding stub
        # no committee meeting has a page (its page is /meetings/); each address written once
        self.assertFalse([u for u in pages if "ev-committee" in u])
        self.assertEqual(len(r["outputs"]), len(set(r["outputs"])))
        titles = {}
        for u, p in pages.items():
            with self.subTest(page=u):
                lang = "es" if u.startswith("/es/") else "en"
                twin = u[3:] if lang == "es" else "/es" + u
                self.assertIn(twin, pages, "every page has its twin")
                title = html.unescape(re.search(r"<title>(.*?)</title>", p).group(1))
                self.assertNotIn((lang, title), titles, f"the same title as {titles.get((lang, title))}")
                titles[(lang, title)] = u
                desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', p).group(1))
                self.assertTrue(0 < len(desc) <= 160, desc)
                self.assertNotIn("location.replace", p)
                self.assertNotIn("evpage.", text_of(p), "every key translated")
                self.assertLess(len(p.encode("utf-8")), 200_000)
        self.assertEqual(r["problems"], [])

    def test_the_structured_data_and_the_head(self):
        r = self.built()
        for u, p in self.event_pages().items():
            with self.subTest(page=u):
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', p, re.S)
                descs = re.findall(r'<meta (?:name|property)="(?:description|og:description|twitter:description)" content="([^"]*)"', p)
                for word in join_words(self):
                    self.assertFalse([b for b in blocks + descs if word in b], word)
        # only a leaf carries its Event — exactly the one /events/ gives it
        for a in (WS, GSR):
            for lang, pre in (("en", ""), ("es", "/es")):
                ld = body_ld(self.page(f"{pre}/events/{a}/"))
                self.assertEqual(len(ld), 1)
                ld[0].pop("@context")
                self.assertEqual([e for e in r["want"][lang] if e["url"] == f"{BASE}{pre}/events/{a}/"], ld)
        for a in (ASM, ONLINE):
            self.assertEqual(body_ld(self.page(f"/events/{a}/")), [])
        # a series' page: no Event; its twin; its title says how often (its words and its rule: config/site.yml)
        for key, s in settings(self)["series"].items():
            with self.subTest(series=key):
                hub = self.page(f"/events/series/{key}/")
                self.assertEqual(body_ld(hub), [])
                self.assertIn(f'<link rel="alternate" hreflang="es" href="{BASE}/es/events/series/{key}/">', hub)
                # (its tail: "Events — NETA 65", "NETA 65" alone after a title over 60 characters — round 37's fixer)
                name = f"{s['title']} — {s['recurrenceDay']}".replace(" · ", " — ")
                tail = "Events" if re.search(r"\bNETA\s*65\b", name) else "NETA 65" if len(name) > 60 else "Events — NETA 65"
                self.assertEqual(html.unescape(re.search(r"<title>(.*?)</title>", hub).group(1)), f"{name} · {tail}")
                # the visible breadcrumb of one of its dates: Home › Events › its series › the page
                if len(s["anchors"]) > 1:
                    date_page = main_of(self.page(f"/events/{s['anchors'][1]}/"))
                    nav = date_page[date_page.index('<nav class="evp-crumbs"'):date_page.index("</nav>")]
                    self.assertEqual(re.findall(r'<a class="link tap-link" href="([^"]+)"', nav),
                                     ["/", "/events/", f"/events/series/{key}/"])
                    self.assertIn('aria-current="page"', nav)
        # a noindex page's head as rendered (its own address, its language, its share picture): a flyer the previews
        # cannot show (an SVG) → the committee's share card; a JPEG → itself, with its words in the page's language
        for pre, locale, alt, card in (("", "en_US", "Flyer", "og-default.png"), ("/es", "es_US", "Volante", "og-default-es.png")):
            with self.subTest(head=pre or "en"):
                svg, jpg = self.page(f"{pre}/events/{SVG}/"), self.page(f"{pre}/events/{JPG}/")
                self.assertIn(f'<html lang="{pre[1:] or "en"}"', svg)
                m = metas(svg)
                self.assertEqual(m["og:image"], f"{BASE}/assets/img/{card}?v=3")
                self.assertEqual(m["og:url"], f"{BASE}{pre}/events/{SVG}/")
                self.assertEqual(m["og:locale"], locale)
                self.assertTrue(m["og:title"].startswith("Reunión del Volante SVG"), m["og:title"])
                self.assertIn(f'<link rel="canonical" href="{BASE}{pre}/events/{SVG}/">', svg)
                m = metas(jpg)
                self.assertEqual(m["og:image"], JPG_FLYER)
                self.assertEqual(m["twitter:image"], JPG_FLYER)
                self.assertEqual(m["og:image:alt"], f"{alt}: Grapevine JPEG Flyer Gathering")
                self.assertEqual(m["og:locale"], locale)

    def test_a_writing_workshop(self):
        s = settings(self)
        for lang, pre in (("en", ""), ("es", "/es")):
            p = main_of(self.page(f"{pre}/events/{WS}/"))
            with self.subTest(lang=lang):
                hrefs = [html.unescape(h) for h in re.findall(r'href="([^"]+)"', p)]
                for want in (f"{pre}/contribute/#workshop", f"{pre}/contribute/#tips", f"{pre}/contribute/#submit",
                             f"{pre}/contribute/#deadlines", f"{pre}/deadlines.ics", f"{pre}/contribute/#record",
                             f"{pre}/published/?scope=neta65&pub=lv", f"{pre}/about/#booth", f"{pre}/about/?booth=start",
                             f"{pre}/events/#{WS}",
                             # (what the settings have: its presentation, GVR / RLV 101's lesson, the committee's
                             # next meeting)
                             *((f"{pre}/orientation/?present=writing-workshop", f"{pre}/orientation/#pres-writing-workshop")
                               if "writing-workshop" in s["decks"] else ()),
                             *((f"{pre}/orientation/stories/",) if "stories" in s["lessons"] else ()),
                             *((f"{pre}/meetings/#committee-meeting",) if s["meeting"] else ())):
                    self.assertIn(want, hrefs)
                self.assertFalse([h for h in hrefs if "bs=" in h], "never a booth link that replaces its settings")
                # (round 37's fixer) the slides are in English: a page in another language says so on the deck's card
                if "writing-workshop" in s["decks"]:
                    deck = re.search(r'<article class="card card-pad evp-deck".*?</article>', p, re.S).group(0)
                    self.assertEqual("Presentación en inglés" in text_of(deck), lang == "es")
                    self.assertNotIn("Presentation in English", text_of(deck))
                # the bingo card made for it: in Spanish (held in Spanish), La Viña, a workshop, its title and day
                bingo = re.search(r'href="([^"]+)"[^>]*data-evp-bingo', p).group(1)
                self.assertEqual(html.unescape(bingo).split("#")[0], f"{pre}/gvr/bingo/")
                self.assertIn("#lang=es&mag=lv&where=workshop&event=Taller%20de%20Escritura%20de%20La%20Vi%C3%B1a"
                              "%20%E2%80%94%20Tyler&date=2099-02-06", html.unescape(bingo))
                # the flyers of similar events: the other one, never its own
                flyers = section(p, "evp-flyers-h")
                self.assertIn(OTHER, flyers)
                self.assertNotIn(OWN, flyers)
                # the lede and the quick facts, written in the page
                words = text_of(p)
                lede = {"en": "La Viña Writing Workshop — Tyler is a writing workshop on Friday, February 6, 2099, "
                              "7:00 – 9:00 PM CST, at Grupo Uno, 100 Main St, Tyler, TX 75702. It is held in Spanish. "
                              "It is organized by District 99 La Viña Committee.",
                        "es": "Taller de Escritura de La Viña — Tyler es un taller de escritura el viernes, 6 de febrero "
                              "de 2099, 7:00–9:00 p. m. CST, en Grupo Uno, 100 Main St, Tyler, TX 75702. Es en español. "
                              "Lo organiza District 99 La Viña Committee."}[lang]
                self.assertIn(lede.replace(" ", " "), words.replace(" ", " ").replace(" ", " "))
                facts = section(p, "evp-facts-h")
                self.assertIn("https://www.google.com/maps/search/?api=1&amp;query=Grupo%20Uno%2C%20100%20Main%20St", facts)
                self.assertIn({"en": "Spanish", "es": "Español"}[lang], text_of(facts))

    def test_other_kinds(self):
        hrefs = lambda path: [html.unescape(h) for h in re.findall(r'href="([^"]+)"', main_of(self.page(path)))]  # noqa: E731
        asm = hrefs(f"/events/{ASM}/")
        res = section(main_of(self.page(f"/events/{ASM}/")), "evp-prep-h")
        self.assertLess(res.index("https://neta65.org/event/test-assembly/"), res.index("/about/#booth"),
                        "its official page first")
        self.assertIn("/orientation/literature-table/", asm)
        gsr = hrefs(f"/events/{GSR}/")
        for want in ("/orientation/role/", "/gvr/#job", "/about/#booth"):
            self.assertIn(want, gsr)
        self.assertFalse([h for h in gsr if h.startswith("/gvr/#steps")])
        self.assertIn("where=assembly", " ".join(gsr))
        info = hrefs(f"/events/{ONLINE}/")
        for want in ("/shop/#magazines", "/shop/#mag-lv", "/listen/?show=lvo",
                     *(("/orientation/?present=information-workshop",) if "information-workshop" in settings(self)["decks"] else ())):
            self.assertIn(want, info)
        # our committee's own event: its name in the page's language (config/site.yml committee / committee_es), in the
        # lede and the quick facts; its language said only when the data says Spanish (an online information workshop
        # of La Viña's: in Spanish)
        s = settings(self)
        for pre, lede in (("", f"It is organized by the {s['committee']}."), ("/es", f"Lo organiza el {s['committeeEs']}.")):
            with self.subTest(organizer=pre or "en"):
                m = main_of(self.page(f"{pre}/events/{ONLINE}/"))
                self.assertIn(lede, text_of(m))
                self.assertIn({"": s["committee"], "/es": s["committeeEs"]}[pre], text_of(section(m, "evp-facts-h")))
                if s["committeeEs"] != s["committee"] and pre:
                    self.assertNotIn(s["committee"], text_of(m))
        for pre in ("", "/es"):
            self.assertNotRegex(text_of(main_of(self.page(f"{pre}/events/{ASM}/"))), r"It is held in English|Es en inglés")
        # (round 37's fixer) the Area organizes its assembly: by its name — with its article in Spanish ("Lo organiza
        # el Área 65 …", never "Lo organiza Área 65 …")
        for pre, lede in (("", f"It is organized by {s['area']}."), ("/es", f"Lo organiza el {s['areaEs']}.")):
            with self.subTest(area=pre or "en"):
                self.assertIn(lede, text_of(main_of(self.page(f"{pre}/events/{ASM}/"))))
        cal = hrefs(f"/events/{CAL}/")
        self.assertIn("https://www.aalavina.org/get-involved/events/2099-02-28/prueba", cal)
        self.assertIn("/events/?filter=calendar", cal)
        # a series' page: its next dates, each to its own page (its list is its own content: not skipped)
        cws = self.series("citywide-dallas")
        if cws:
            hub = main_of(self.page("/events/series/citywide-dallas/"))
            dates = section(hub, "evp-dates-h")
            self.assertNotIn('data-lastmod="skip"', dates[:dates.index(">")])
            links = re.findall(r'<a href="([^"]+)" class="card card-link cm-mini-card', dates)
            self.assertEqual(links, [f"/events/{a}/" for a in cws["anchors"]])
            self.assertLessEqual(len(links), 6)
            # (round 37's fixer) the series' own site (its `url:`), first under "Get ready": the one page search
            # engines may list for the series links it, as its dates' cards do
            if cws["link"]:
                prep = section(hub, "evp-prep-h")
                first = re.search(r'<a class="[^"]*evp-res-link[^"]*" href="([^"]+)"', prep) or re.search(r'href="(https?://[^"]+)"', prep)
                self.assertEqual(html.unescape(first.group(1)), cws["link"])
            # a date's page: its series' dates (its own marked), "All dates" to its series' page
            d = main_of(self.page(f"/events/{cws['anchors'][0]}/"))
            self.assertIn('aria-current="page"', section(d, "evp-dates-h"))
            self.assertIn('href="/events/series/citywide-dallas/"', d[:d.index('class="evp-crumbs"')])
        # the Grapevine Meeting: its presentation, what happens at it (/meetings/), how to join (its code kept out of
        # snippets)
        gms = self.series("grapevine-meeting")
        if gms:
            gm = main_of(self.page("/events/series/grapevine-meeting/"))
            if gms["deck"] and gms["deck"] in settings(self)["decks"]:
                self.assertIn(f'href="/orientation/?present={gms["deck"]}"', gm)
            if gms["kind"] == "online-meeting":
                self.assertIn('href="/meetings/#grapevine-meeting"', gm)
                self.assertIn("What happens at the meeting", text_of(section(gm, "evp-prep-h")))
            if gms["meetingId"]:
                self.assertIn(f'translate="no" data-nosnippet>{html.escape(gms["meetingId"])}</span>', gm)

    def test_an_event_that_is_over(self):
        for pre in ("", "/es"):
            p = self.page(f"{pre}/events/{PAST}/")
            m = main_of(p)
            with self.subTest(lang=pre or "en"):
                for word in ("987 654 3210", "9876543210", "zoom.us", "zz65", "Bring a pen", "data-cm-ics", "cm-menu"):
                    self.assertNotIn(word, m)
                self.assertIn({"": "Learn to write your story.", "/es": "Learn to write your story."}[pre], text_of(m))
                self.assertIn({"": "This event is over", "/es": "Este evento ya pasó"}[pre], text_of(m))
                self.assertIn({"": "took place on", "/es": "se realizó el"}[pre], text_of(m))
                self.assertNotIn("data-evp-bingo", m, "no bingo card for a day that is over")

    def test_the_blocks_that_change_with_other_events(self):
        p = main_of(self.page(f"/events/{WS}/"))
        for h in ("evp-next-h", "evp-coming-h", "evp-past-h", "evp-flyers-h", "evp-month-h"):
            if f'aria-labelledby="{h}"' not in p:
                continue
            with self.subTest(block=h):
                # the block itself, or the block around it, says data-lastmod="skip"
                at_ = p.index(f'aria-labelledby="{h}"')
                opening = p[p.rindex("<", 0, at_):p.index(">", at_)]
                around = p[:at_].rsplit('data-lastmod="skip"', 1)
                self.assertTrue('data-lastmod="skip"' in opening or len(around) == 2)
        self.assertIn('aria-labelledby="evp-coming-h"', p)
        self.assertIn('aria-labelledby="evp-month-h"', p)
        dated = self.built()["dated"][f"/events/{WS}/"]
        self.assertNotIn("GSR/DCM Orientation — West", text_of(dated[dated.index("<main"):]),
                         "another event's card is not this page's content")
        self.assertIn("La Viña Writing Workshop — Tyler is a writing workshop", text_of(dated))
        # the flyer viewer's own words: never in search snippets
        self.assertRegex(self.page(f"/events/{WS}/"), r'<div data-nosnippet>\s*<dialog id="cm-preview"')


# Every kind's settings, decks and lessons of its own (never the committee's files): test_r37_spine's settings with the
# links a page reads, and the model alone, as the templates' pagination calls it.
KSITE = {**SPINE_SITE, "committee_es": "Comité de Prueba",
         "links": {**SPINE_SITE["links"], "lv_share_story": "https://lv.example.org/share",
                   "gvr_register": "https://gv.example.org/register", "rlv_register": "https://lv.example.org/register"}}


def _both(en: str, es: str) -> dict:
    return {"en": en, "es": es}


KDECKS = [{"id": i, "title": _both(t, t), "card": {"title": _both(t, t), "summary": _both("About it.", "Sobre ella.")},
           "minutes": 60} for i, t in (("writing-workshop", "Test writing deck"), ("information-workshop", "Test info deck"),
                                       ("orientation-workshop", "Test orientation deck"), ("grapevine-meeting", "Test GV deck"))]
LITTABLE = _both("Set up a test table people stop at.", "Arma una mesa de prueba.")
KLESSONS = [{"id": "magazines", "title": _both("The magazines", "Las revistas"), "summary": _both("What they are.", "Qué son.")},
            {"id": "subscriptions", "title": _both("Subscriptions", "Suscripciones"), "summary": _both("How.", "Cómo.")},
            {"id": "role", "title": _both("The role", "El servicio"), "summary": _both("What a rep does.", "Qué hace.")},
            {"id": "literature-table", "title": _both("Your literature table", "Tu mesa de literatura"), "summary": LITTABLE},
            {"id": "stories", "title": _both("Stories", "Historias")}]          # (no summary of its own)

KINDS_JS = r"""
const M = await imp("eleventy/event-page-model.js");
const site = { ...input.site, built: input.now };
const full = { db: { events: { items: input.items, cancelled: [] }, drive: { items: [] }, pdfs: { items: [] },
                     announcements: { items: input.ann }, audio_project: input.audio, articles: { items: [], issues: [] } },
               site, languages: ["en", "es"], presentations: { decks: input.decks, problems: [] },
               orientation: { lessons: input.lessons }, carry: {}, monthlyKeys: [] };
const d = M.eventPageData(full);
const of = (lang) => Object.fromEntries(d.pages.filter((p) => p.lang === lang).map((p) => [p.anchor, { kind: p.kind.kind,
  deck: p.m.prep.deck ? p.m.prep.deck.id : "", close: p.m.prep.deck ? p.m.prep.deck.close : false, bingo: p.m.prep.bingo,
  lede: p.m.lede, facts: p.m.facts, res: p.m.prep.resources.map((r) => r.id),
  resd: p.m.prep.resources.map((r) => ({ id: r.id, labelKey: r.labelKey, textKey: r.textKey, text: r.text, links: r.links })),
  hrefs: p.m.prep.resources.flatMap((r) => [r.href, ...r.links.map((l) => l.href)]) }]));
out({ en: of("en"), es: of("es") });
"""


class EveryKind(unittest.TestCase):
    """Each kind's "Get ready" (eleventy/event-page-model.js, the judge's spec §4 table): its presentation, its bingo
    card's occasion and its resources in order — a resource the data cannot give (no writer's guide in the Library, no
    display album, no official page) left out; a kind with none of its own ("other"): the magazines' own links. And
    the words the model gives: a lesson's own summary, our committee's name in Spanish, an online event over several
    days, no language guessed, a bingo card's name."""
    r: dict | None = None
    LVW_DAY = nth_weekday(2099, 1, 3, 4)

    def got(self) -> dict:
        if EveryKind.r is None:
            d = lambda m, day: date(2099, m, day)  # noqa: E731
            ev = lambda slug, title, day, **kw: item(slug, title, at(day, "10:00"), at(day, "12:00"), **kw)  # noqa: E731
            items = [
                ev("rec", "La Viña Recording Workshop — Duncanville", d(2, 7), tags=["workshop", "la-vina"], **TYLER),
                ev("acm", "Test Winter ACM", d(2, 21), tags=["neta65", "acm"], **PLANO),
                ev("th", "Delegate — Conference Connect Town Hall", d(2, 22), tags=["neta65", "town-hall"], **PLANO),
                ev("ig", "La Viña Intergroup Meeting — Fort Worth", d(2, 23), tags=["intergroup", "la-vina"], **TYLER),
                ev("pic", "Test Picnic", d(2, 24), **TYLER),
                ev("ww", "Test Writing Workshop — Plano", d(2, 25), tags=["workshop"], **PLANO),
                # "Official page": its own page elsewhere only — not the Area's home page, a page of our own site or a
                # meeting's room (each: the Area's site instead); a page about it on the Area's site: first
                ev("acm-home", "Test Spring ACM", d(4, 17), tags=["neta65", "acm"], url="https://area.example.org/", **PLANO),
                ev("acm-ours", "Test Summer ACM", d(7, 17), tags=["neta65", "acm"], url=f"{BASE}/about/", **PLANO),
                ev("th-room", "Test Town Hall Online", d(5, 1), tags=["neta65", "town-hall"],
                   url="https://meet.google.com/abc-defg-hij", **PLANO),
                ev("acm-page", "Test Fall ACM", d(10, 16), tags=["neta65", "acm"],
                   url="https://area.example.org/events/fall-acm/", **PLANO),
                # online over three days
                item("rng", "Online Writing Retreat", at(d(2, 5), "18:00"), at(d(2, 7), "12:00"),
                     online_url="https://us02web.zoom.us/j/4444444444", platform="Zoom", meeting_id="444 444 4444"),
                # La Viña's calendar, a long title with brackets: its bingo card's name never cut inside them
                item("zona", "XLII Reunión de A.A. Zona Norte de Texas (A.A. Un camino a la libertad)", "2099-03-07",
                     "2099-03-07", category="lv-calendar", source="calendar",
                     url="https://www.aalavina.org/get-involved/events/2099-03-07/zona-norte"),
                series_date("citywide-dallas", cw[1], "17:30", "19:30", "GV/LV booth at CityWide Test", rule=CW,
                            location=CW_PLACE, host="neta"),
                series_date("lv-monthly-workshop", self.LVW_DAY, "14:00", "15:00",
                            "La Viña Monthly Virtual Workshop (in Spanish)", rule={"week_of_month": 4, "weekday": "thursday",
                            "start": "14:00", "end": "15:00"}, host="lv", online_url="https://us06web.zoom.us/j/12345678901",
                            platform="Zoom", online=True),
                series_date("grapevine-meeting", gvm[0], "19:00", "20:00", "Grapevine Meeting", rule=GVM, host="neta",
                            online_url="https://meet.google.com/abc-defg-hij", platform="Google Meet",
                            meeting_id="abc-defg-hij", online=True),
            ]
            ann = [{"id": "ann:x", "source": "committee", "kind": "announcement", "title": "Offers", "lang": "en",
                    "date": "2099-01-01", "status": "ok", "extra": {"slug": "2099-01-01-offers", "pinned": True}}]
            audio = {"gv": {"phone": "(555) 010-0001", "tel": "+15550100001"}, "lv": {"phone": "(555) 010-0002", "tel": "+15550100002"}}
            EveryKind.r = run_js(self, KINDS_JS, data={"items": items, "ann": ann, "audio": audio, "now": NOW, "site": KSITE,
                                                       "decks": KDECKS, "lessons": KLESSONS}, now=NOW)
        return EveryKind.r

    def test_the_kinds(self):
        r = self.got()["en"]
        lvw = f"ev-recurring-lv-monthly-workshop-{self.LVW_DAY.isoformat()}"
        gvm0 = f"ev-recurring-grapevine-meeting-{gvm[0].isoformat()}"
        area = ["area", "booth", "littable", "offers"]
        want = {
            "rec": ("recording-workshop", "writing-workshop", "workshop", ["record", "listen", "published", "tips", "booth"]),
            "acm": ("acm", "", "acm", area),
            "th": ("town-hall", "", "assembly", area),
            "ig": ("intergroup", "", "group", ["mags", "offers", "booth"]),
            "pic": ("other", "", "any", ["read", "mags", "contribute", "bulletin"]),
            "ww": ("writing-workshop", "writing-workshop", "workshop",
                   ["contribute", "tips", "submit", "deadlines", "record", "published", "stories", "booth"]),
            "acm-home": ("acm", "", "acm", area), "acm-ours": ("acm", "", "acm", area),
            "th-room": ("town-hall", "", "assembly", area),
            "acm-page": ("acm", "", "acm", ["official", "booth", "littable", "offers"]),
            CW_DATES[1]: ("booth", "", "booth", ["booth", "littable", "offers", "mags", "bulletin"]),
            lvw: ("magazine-workshop", "", "online", ["listen", "lvshare", "record"]),
            gvm0: ("online-meeting", "grapevine-meeting", "online", ["gvm", "weekly", "read", "listen"]),
        }
        for anchor, (kind, deck, where, res) in want.items():
            with self.subTest(anchor=anchor):
                got = r[anchor]
                self.assertEqual((got["kind"], got["deck"], got["res"]), (kind, deck, res))
                self.assertIn(f"&where={where}&", got["bingo"])
        self.assertTrue(r["rec"]["close"], "the recording workshop's deck is the closest one")
        self.assertIn("tel:+15550100002", r["rec"]["hrefs"], "La Viña's record-your-story line")
        self.assertIn("/listen/?show=lvo", r["rec"]["hrefs"])
        self.assertIn("/bulletin/#2099-01-01-offers", r[CW_DATES[1]]["hrefs"])
        self.assertIn("/shop/#mag-lv", r["ig"]["hrefs"])
        self.assertIn("https://lv.example.org/share", r[lvw]["hrefs"])
        self.assertEqual(r["acm-page"]["hrefs"][0], "https://area.example.org/events/fall-acm/")
        for a in ("acm-home", "acm-ours", "th-room"):
            with self.subTest(no_official=a):
                self.assertFalse([h for h in r[a]["hrefs"] if "meet.google.com" in h or h.startswith(BASE)])

    def test_the_words(self):
        g = self.got()
        en, es = g["en"], g["es"]
        res = lambda page, i: next(x for x in page["resd"] if x["id"] == i)  # noqa: E731
        # a GVR / RLV 101 lesson's card: its own summary (config/orientation.yml), else the one shared line
        self.assertEqual((res(en["acm"], "littable")["text"], res(en["acm"], "littable")["textKey"]), (LITTABLE["en"], ""))
        self.assertEqual(res(es["acm"], "littable")["text"], LITTABLE["es"])
        self.assertEqual((res(en["ww"], "stories")["text"], res(en["ww"], "stories")["textKey"]), ("", "evpage.res.lesson_t"))
        # the deadlines' calendar: a file the template puts in the page's language (/es/deadlines.ics)
        self.assertEqual([(x["href"], x.get("file")) for x in res(es["ww"], "deadlines")["links"]], [("/deadlines.ics", True)])
        # the Grapevine Meeting's own page: "What happens at the meeting", not its own name under its own deck
        self.assertEqual(res(en[f"ev-recurring-grapevine-meeting-{gvm[0].isoformat()}"], "gvm")["labelKey"], "evpage.res.gvm_more")
        # our committee: its name in the page's language, "the" before it; in the quick facts too
        for page, name in ((en["ww"], "Test Committee"), (es["ww"], "Comité de Prueba")):
            with self.subTest(organizer=name):
                self.assertEqual((page["lede"]["org"], page["lede"]["orgKey"]), (name, "evpage.lede.org_ours"))
                self.assertEqual([f["v"] for f in page["facts"] if f["k"] == "organizer"], [name])
        # the Area (round 37's fixer): its own name — with its article in Spanish, "Lo organiza el Área 65 …"
        self.assertEqual((es["acm"]["lede"]["orgKey"], en["acm"]["lede"]["orgKey"]), ("evpage.lede.org_area", "evpage.lede.org_area"))
        # its language: only when the data says Spanish (never "held in English" guessed)
        self.assertEqual((es["ww"]["lede"]["held"], es["acm"]["lede"]["held"], en["ww"]["lede"]["held"]), ("", "", ""))
        self.assertEqual((es["ig"]["lede"]["held"], en["rec"]["lede"]["held"]), ("evpage.lede.es", "evpage.lede.es"))
        # online over several days: where (its platform) and from when to when
        self.assertEqual({k: en["rng"]["lede"][k] for k in ("key", "platform", "from", "to")},
                         {"key": "evpage.lede.online_range", "platform": "Zoom", "from": "Thursday, February 5",
                          "to": "Saturday, February 7, 2099"})
        # a bingo card's name: cut at a word, never inside its brackets
        event = unquote(re.search(r"&event=([^&]+)", en["ev-lv-calendar-zona"]["bingo"]).group(1))
        self.assertEqual(event, "XLII Reunión de A.A. Zona Norte de Texas")


class Automation(unittest.TestCase):
    """One event file more and one dated Drive flyer more: their pages appear at the next build, with their kind's
    sections — nothing else changes in the code or the settings."""

    def test_a_new_event_gets_its_page(self):
        s = settings(self)
        r = build(self, events(self) + NEW_EVENTS, DRIVE)
        sm = r["pages"]["/sitemap.xml"]
        flyer_anchor = f"ev-flyer-{NEW_FLYER.lower()}"
        for pre in ("", "/es"):
            for a in (NEW, flyer_anchor):
                with self.subTest(page=f"{pre}/events/{a}/"):
                    self.assertIn(f"<loc>{BASE}{pre}/events/{a}/</loc>", sm)
            p = main_of(r["pages"][f"{pre}/events/{NEW}/"])
            hrefs = [html.unescape(h) for h in re.findall(r'href="([^"]+)"', p)]
            # (and what the settings have: its presentation, GVR / RLV 101's lesson, the sign-up link)
            for want in (f"{pre}/orientation/#sessions", f"{pre}/gvr/#job",
                         *((f"{pre}/orientation/?present=orientation-workshop",) if "orientation-workshop" in s["decks"] else ()),
                         *((f"{pre}/orientation/role/",) if "role" in s["lessons"] else ()),
                         *((s["gvrRegister"],) if s["gvrRegister"] else ())):
                self.assertIn(want, hrefs)
            self.assertIn("where=workshop", " ".join(hrefs))
            self.assertIn({"": "GVR/RLV orientation", "/es": "Orientación para RLV y GVR"}[pre], text_of(p))
            f = main_of(r["pages"][f"{pre}/events/{flyer_anchor}/"])
            self.assertIn(f"{pre}/contribute/#workshop", f)
            if "writing-workshop" in s["decks"]:
                self.assertIn(f"{pre}/orientation/?present=writing-workshop", f)
        self.assertEqual(r["problems"], [])


class Parity(unittest.TestCase):
    def test_the_sync_takes_the_page_kinds(self):
        from scripts.sync.announcements import EVENT_TYPES
        kinds = run_js(self, 'out((await imp("eleventy/event-pages.js")).EVENT_KIND_KEYS);')
        self.assertEqual(sorted(EVENT_TYPES), sorted(kinds))


class Templates(unittest.TestCase):
    """One plan, three templates by tier (plus the cancelled notices'): no address is written twice; the old
    forwarding stubs are gone."""

    def test_the_paginations(self):
        pages = ROOT / "src" / "pages"
        self.assertFalse((pages / "event-share.11ty.js").exists())
        leaf, date_, series = ((pages / f"event-share-{n}.njk").read_text(encoding="utf-8") for n in ("leaf", "date", "series"))
        self.assertIn("eventPageData(full).pages.filter((p) => p.index)", leaf)
        self.assertIn("eventPageData(full).pages.filter((p) => !p.index)", date_)
        self.assertIn("eventPageData(full).hubs", series)
        for t in (leaf, date_, series):
            self.assertIn('const layout = "layouts/base.njk";', t)
            self.assertIn('{% include "partials/event-page.njk" %}', t)
        for flag in ("const noindex = true;", "const sitemap = false;", "const eleventyExcludeFromCollections = true;"):
            self.assertIn(flag, date_)
            self.assertNotIn(flag, leaf + series)


if __name__ == "__main__":
    unittest.main()
