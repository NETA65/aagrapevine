"""Round 37 · the site search finds everything on the site (eleventy/filters/library.js searchIndex,
eleventy/search-sections.js, src/assets/js/search.js, src/pages/search.njk, eleventy/seo-check.js searchProblems):

  * The query table (the judge's spec §8 U5), through the /search/ page's own index (search.js kit.siteIndex: its
    fields, weights and ranking) and the vendored MiniSearch, on an index the build's filter makes of made-up data
    (the spine's events, tests/test_r37_spine.py, at its build moment 2099-01-10): "assemblies" finds the assembly,
    "volante" the flyers, "presentation" the five presentations, "exhibidor" the booth display's section, "faq" the
    FAQ, "kit de diciembre" December's toolkit, "into action" the Book of the Month, "current issue" the two current
    issues, "next meeting" the next committee meeting, "citywide" the CityWide series' page, "cancelled picnic" the
    cancelled event's notice ("Cancelled: …", ranked low) — and "december" leaves fewer than 30 cover albums in the
    first 50 results (a year of covers ranks lower: lw). A flyer never comes before its event: "writing workshop" lists
    the next workshop before any flyer, "committee meeting" the next meeting before its guest speaker's flyer, while
    "flyer" still lists the flyers first.
  * The entries: an event links its own page (/[es/]events/<anchor>/), a monthly series its series' page
    (/events/series/<key>/), an upcoming cancelled event its notice; its words add its day of the week in both
    languages, its city, its organizer (never the committee itself), "flyer volante" and its kind in both languages;
    no entry ever carries a meeting link, ID, code or passcode (a weekly open meeting's, an Instagram caption's
    neither), nor the next meeting's guest speaker. The sections of eleventy/search-sections.js, the presentations
    (with "Start the presentation"), the 13 month toolkits, the two current issues, the flyers (each to the page of the
    event, series, weekly meeting it is for — else the Portfolio's flyers —, with its event's date, ranked low once it
    is over), the shop's offers; the next meeting's platform, "faq" for the FAQ alone (never the open calls for
    stories); a series' page linked only once the build writes it; every kind the index has is labelled, grouped and
    has its icon on /search/.
  * The kit: a word's other number (assemblies ↔ assembly, stories ↔ story, veces ↔ vez — exactly, never a guess that
    is no word), the round-37 words of the other language (booth / exhibidor, flyer / volante …), lw ranking, a flyer's
    lower rank (but on "flyer" / "volante"), and a presentation's second link (same tab, "Start the presentation").
  * The [search] check (searchProblems): a sitemap page no entry links, a link to a page or #anchor the build lacks,
    an index over 1,600,000 bytes — each a problem (a "[search]" build warning, seoCheck); a link to a series' page the
    build lacks is one like any other.
  * The sections on the pages: in a build of the pages that have them, every line of eleventy/search-sections.js
    points at a heading that exists in both languages and has the entry's words (a section its page leaves out — the
    history without milestones — has no entry and is not looked for).
  * RealIndex (the day's data — scripts/ops/gate_tests.py DATA_TESTS): the index of the real data keeps to its size
    budget and finds what the day's data has (the current Book of the Month, the CityWide series' page, next month's
    toolkit, the assemblies, the flyers, the five presentations, the current issues), the next workshop before any
    flyer of a workshop that is over, the next committee meeting near the top, and no Zoom ID or meeting link.

Runs the JavaScript with Node.js (tests/nodejs.py); skipped without Node.js / the npm packages.

    python -m unittest tests.test_r37_search -v
"""
from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402
import test_r37_spine as SP  # noqa: E402  (the spine's made-up events, site and build moment)
from test_photos_covers import cover  # noqa: E402  (a magazine cover as data/site/drive.json has it)

MINISEARCH = ROOT / "node_modules" / "minisearch" / "dist" / "umd" / "index.js"
BUILT = SP.BUILT                     # 2099-01-10T18:00:00Z
DECKS = ["orientation-workshop", "information-workshop", "writing-workshop", "committee-meeting", "grapevine-meeting"]
# the made-up flyers (Drive pictures in flyers/): the next writing workshop's, the old one's (over), the CityWide date's,
# the weekly meeting's, one of nothing listed, the moved December session's (over) and the committee meeting's
FLYERS = ("flyerwrite00001", "flyerold000001", "flyercity000001", "flyerweekly0001", "flyerloose00001", "lvflyerdec0001",
          "flyercomm00001")
SECRETS = ("abc-defg-hij", "abcdefghij", "12345678901", "123 4567 8901", "meet.google.com", "zoom.us/j", "871 2036 8287",
           "815 9593 1777", "238047")


def need_minisearch(case: unittest.TestCase) -> None:
    if not MINISEARCH.is_file():
        case.skipTest("node_modules is not installed (npm ci): the vendored MiniSearch comes from there")


def drive_photo(fid: str, title: str, title_es: str, *, category: str = "flyers", kind: str = "photo", date_: str = "2098-12-20") -> dict:
    """A Drive file as data/site/drive.json has it (a flyer: a picture in the flyers/ folder)."""
    x = {"file_id": fid, "mime": "image/jpeg" if kind == "photo" else "application/pdf", "name": title + ".jpg",
         "panel": 77, "panel_label": "Panel 77 (2027–2028)", "path": [category],
         "view_url": f"https://drive.google.com/file/d/{fid}/view", "thumb_url": f"https://lh3.googleusercontent.com/d/{fid}=w600",
         "is_image": kind == "photo", "is_pdf": kind != "photo"}
    return {"id": f"drive:{fid}", "source": "drive", "kind": kind, "url": x["view_url"], "title": title, "summary": "", "lang": "en",
            "date": date_, "image": x["thumb_url"], "tags": [], "category": category, "status": "ok", "extra": x,
            "i18n": {"title": {"en": title, "es": title_es}}, "machine": [], "is_new": False}


def fixture() -> dict:
    """The made-up site: the spine's events (a flyer on the writing workshop, on the old one that is over and on
    January's CityWide date; a summary that gives a Meet link; a date of La Viña's workshop the host moved, over, with its
    flyer; January's committee meeting with its guest speaker's flyer), its cancelled events (as src/_data/db.js splits
    them), flyers, 41 years of Grapevine covers, 30 stories of a December issue, the two current issues, the shop, five
    presentations, a guest speaker, a weekly open meeting and an Instagram post that give a Zoom ID and passcode, an
    open call for stories."""
    events = copy.deepcopy(SP.EVENTS)
    for e in events:
        if e["id"] == "ev:manual:2099-02-07-test-writing":
            e["extra"]["flyer_url"] = "https://drive.google.com/file/d/flyerwrite00001/view"
        if e["id"] == "ev:manual:2098-12-05-old-workshop":
            e["extra"]["flyer_url"] = "https://drive.google.com/file/d/flyerold000001/view"
        if e["id"] == f"ev:recurring:citywide-dallas:{SP.cw1.isoformat()}":
            e["extra"]["flyer_url"] = "https://drive.google.com/file/d/flyercity000001/view"
        if e["id"] == "ev:manual:2099-03-13-gvr-orientation":
            e["summary"] = "Join on Google Meet: meet.google.com/abc-defg-hij. Meet code abc-defg-hij. Bring a friend."
    # December's session of La Viña's workshop, moved by the host and over (a dated Drive flyer: build_data's
    # series_dated_flyers), and January's committee meeting as events.json has it (its guest speaker's flyer)
    events.append(SP.item("x", "La Viña Monthly Virtual Workshop (in Spanish)", SP.at(date(2098, 12, 16), "14:00"),
                          SP.at(date(2098, 12, 16), "15:00"), category="flyer", source="drive", ident="ev:flyer:lvflyerdec0001",
                          url="https://drive.google.com/file/d/lvflyerdec0001/view", series_of="lv-monthly-workshop", host="lv",
                          online=True, platform="Zoom"))
    events.append({"id": "ev:committee:2099-01-21", "source": "committee", "kind": "event", "category": "committee", "status": "ok",
                   "title": "Committee meeting", "lang": "en", "date": "2099-01-22T01:00:00Z",
                   "extra": {"flyer_url": "https://drive.google.com/file/d/flyercomm00001/view"}})
    items = [e for e in events if not e["extra"].get("cancelled")]
    cancelled = copy.deepcopy(SP.CANCELLED) + [e for e in events if e["extra"].get("cancelled")]
    drive = [
        drive_photo("flyerwrite00001", "Test Writing Workshop - flyer", "Taller de escritura de prueba - volante"),
        drive_photo("flyerold000001", "Old Writing Workshop - flyer", "Taller de escritura antiguo - volante", date_="2099-01-05"),
        drive_photo("lvflyerdec0001", "La Viña Monthly Virtual Workshop - December", "Taller Mensual de La Viña - diciembre"),
        drive_photo("flyercomm00001", "January 2099 Committee Meeting - guest speaker", "Reunión del comité de enero de 2099 - orador invitado"),
        drive_photo("flyercity000001", "Test CityWide booth - flyer", "Mesa de CityWide de prueba - volante"),
        drive_photo("flyerweekly0001", "Test Weekly Open Meeting flyer", "Volante de la reunión abierta semanal de prueba"),
        drive_photo("flyerloose00001", "Our online meetings - flyer", "Nuestras reuniones en línea - volante"),
        drive_photo("flyerpdf000001", "Printable workshop flyer", "Volante imprimible del taller", kind="document"),
        *[cover("gv", y, m) for y in range(1990, 2031) for m in range(1, 13)],
    ]
    articles = [{"id": f"art:dec-{n}", "source": "grapevine", "kind": "article", "category": "gv", "status": "ok", "lang": "en",
                 "title": f"A December story {n}", "summary": "Sober holidays.", "date": "2098-12-01",
                 "url": f"https://www.aagrapevine.org/magazine/2098/dec/story-{n}",
                 "extra": {"publication": "gv", "issue_key": "2098-12", "issue_label": "December 2098", "author": "Anonymous"}}
                for n in range(30)]
    issues = [
        {"id": "gv:2099-01", "publication": "gv", "key": "2099-01", "label": "January 2099", "theme": "Test Theme of the Month",
         "description": "The month's stories.", "url": "https://www.aagrapevine.org/magazine-issue/january-2099", "cover": "",
         "i18n": {"theme": {"en": "Test Theme of the Month", "es": "Tema de prueba del mes"}, "label": {"en": "January 2099", "es": "Enero 2099"}},
         "machine": ["es"], "lang": "en"},
        {"id": "lv:2099-01", "publication": "lv", "key": "2099-01", "label": "Enero / Febrero 2099", "theme": "La alegría de prueba",
         "description": "Historias del mes.", "url": "https://www.aalavina.org/edicion-de-revista/enero-febrero-2099", "cover": "",
         "i18n": {"theme": {"en": "The Joy of Testing", "es": "La alegría de prueba"}}, "machine": ["en"], "lang": "es"},
    ]
    shop = {"botm": [{"id": "botm:gv", "pub": "gv", "lang": "en", "title": "Into Action: Stories from AA Grapevine",
                      "url": "https://www.aagrapevine.org/store/into-action", "page_url": "https://www.aagrapevine.org/BOTM",
                      "price": 14.99, "sale_price": 11.99, "discount_pct": 20, "currency": "USD", "starts": "2099-01-01", "ends": "2099-01-31",
                      "blurb": "Stories of members working the program.", "i18n": {"title": {"en": "Into Action: Stories from AA Grapevine",
                                                                                            "es": "En acción: historias de AA Grapevine"}}}],
            "specialty": [{"id": "special:gv:MS09", "pub": "gv", "lang": "en", "type": "planner", "title": "Annual Pocket Planner",
                           "url": "https://www.aagrapevine.org/store/annual-pocket-planner", "price": 6, "currency": "USD", "sku": "MS09",
                           "text": "A companion to the Wall Calendar."}],
            "price_changes": [], "subscriptions": []}
    site = copy.deepcopy(SP.SITE)
    site["grapevine_weekly_open"] = {"flyer_match": "test weekly open meeting flyer"}
    # the next meeting (Wednesday, January 21, 2099) has a guest speaker: never in the index
    site["meeting"]["speakers"] = [{"date": "2099-01-21", "name": "Pat Q.", "position": "Past delegate", "topic": "Carrying the message"}]
    decks = [{"id": d, "order": i, "title": d.replace("-", " ").title(), "short": d.replace("-", " ").title(),
              "card": {"title": {"en": f"Test {d.replace('-', ' ')} deck", "es": f"Presentación de prueba {d}"},
                       "summary": {"en": f"Slides for the {d.replace('-', ' ')}.", "es": f"Diapositivas para {d}."},
                       "audience": {"en": "GVRs and RLVs", "es": "RLV y GVR"}}} for i, d in enumerate(DECKS)]
    weekly = [{"id": "weekly_open", "source": "grapevine", "kind": "meeting", "status": "ok", "lang": "en",
               "title": "Test Weekly Open Meeting", "i18n": {"when": {"en": "Wednesdays at 11:00 AM Central",
                                                                       "es": "Los miércoles a las 11:00 a. m. (hora del Centro)"}},
               "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "zoom_url": "https://us02web.zoom.us/j/87120368287"}}]
    posts = [{"id": "ig:test1", "source": "instagram", "kind": "post", "category": "lv", "status": "ok", "lang": "es",
              "title": "Reunión abierta cada jueves.", "url": "https://www.instagram.com/p/test1/", "date": "2099-01-05",
              "summary": "Reunión abierta cada jueves.\nMeeting ID Zoom: 815 9593 1777\nPasscode: 238047\nEscuche el podcast de prueba.",
              "extra": {"username": "aalavina", "account": "lv"}}]
    editorial = [{"id": "ed:test1", "source": "grapevine", "kind": "topic", "category": "gv", "status": "ok", "lang": "en",
                  "title": "Test Sober Holidays", "extra": {"deadline": "2099-03-01", "publication": "gv", "issue_label": "June 2099"}}]
    # the Texas writers archive (/published/#archive): a story of its own, and one the Library has already
    archive = {"updated": "2099-01-01", "items": [
        {"id": "wa:back0000001", "key": "https://www.aagrapevine.org/magazine/2098/may/back-darkness",
         "url": "https://www.aagrapevine.org/magazine/2098/may/back-darkness", "pub": "gv", "lang": "en",
         "title": "Back from the Darkness", "i18n": {"title": {"en": "Back from the Darkness", "es": "Regreso de la oscuridad"}},
         "machine": ["es"], "issue_key": "2098-05", "issue_label": "May 2098", "year": 2098, "decade": 2090,
         "theme": "How the steps changed my life", "scope": "texas",
         "writers": [{"name": "Will J.", "anonymous": False, "place": "Waco, Texas",
                      "geo": {"scope": "texas", "city": "Waco", "counties": ["McLennan"], "label_en": "Waco, Texas", "label_es": "Waco, Texas"}}]},
        {"id": "wa:dup0000001", "key": articles[0]["url"], "url": articles[0]["url"], "pub": "gv", "lang": "en",
         "title": articles[0]["title"], "issue_key": "2098-12", "issue_label": "December 2098", "year": 2098, "scope": "texas",
         "writers": [{"name": "Anonymous", "anonymous": True, "place": "Tyler, Texas"}]},
    ]}
    return {"db": {"events": {"items": items, "cancelled": cancelled}, "drive": {"items": drive},
                   "articles": {"items": articles, "issues": issues}, "shop": shop, "weekly_open": {"items": weekly},
                   "editorial": {"items": editorial}, "announcements": {"items": []}, "instagram": {"items": posts},
                   "writers_archive": archive},
            "site": site, "presentations": {"decks": decks}}


# The index of the made-up site (the build's filter, in both languages), the page's own index of it (kit.siteIndex)
# and the query table's hits: { index: {lang: entries}, hits: {name: [entries]}, sections, titles, kinds, …}.
INDEX_JS = PAGE_JS + r"""
const nav = (await imp("src/_data/nav.js")).default;
const { SEARCH_SECTIONS } = await imp("eleventy/search-sections.js");
const orientation = (await imp("src/_data/orientation.js")).default();
const conf = await imp("eleventy.config.js");
const index = {};
for (const lang of ["en", "es"]) index[lang] = JSON.parse(filters.searchIndexJson(input.db, nav, lang, input.site, input.presentations)).items;
const p = page({ url: "https://example.test/aagrapevine/search/", globals: { SITE: { lang: "en", base: "/aagrapevine/" } },
                 scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js"] });
vm.runInContext(fs.readFileSync("src/assets/js/search.js", "utf8"), p.win, { filename: "search.js" });
const K = p.win.GV.searchKit;
const ms = { en: K.siteIndex(index.en), es: K.siteIndex(index.es) };
const hits = {};
for (const [name, lang, q] of input.queries) hits[name] = K.search(ms[lang], q).hits.map((h) => ({ ...index[lang][h.id], alt: !!h.alt }));
// each section's words as the page shows them (its heading's key, with the page's placeholders)
const titles = {};
for (const lang of ["en", "es"]) titles[lang] = Object.fromEntries(SEARCH_SECTIONS.map((s) =>
  [s.id, conf.translateKey(s.title, lang, typeof s.titleVars === "function" ? s.titleVars({ orientation }) : undefined)]));
out({ index, hits, sections: SEARCH_SECTIONS.map((s) => ({ id: s.id, page: s.page, anchor: s.anchor, icon: s.icon })), titles });
"""

QUERIES = [
    ("assemblies", "en", "assemblies"), ("volante", "es", "volante"), ("presentation", "en", "presentation"),
    ("exhibidor", "es", "exhibidor"), ("faq", "en", "faq"), ("kit", "es", "kit de diciembre"), ("botm", "en", "into action"),
    ("issue", "en", "current issue"), ("meeting", "en", "next meeting"), ("citywide", "en", "citywide"),
    ("december", "en", "december"), ("cancelled", "en", "cancelled picnic"), ("cancelado", "es", "picnic cancelado"),
    ("saturday", "en", "saturday tyler"), ("sabado", "es", "sábado tyler"), ("typo", "en", "presentaton"),
    ("accents", "es", "presentacion"), ("plural", "en", "flyers"), ("writing", "en", "writing workshop"),
    ("committee", "en", "committee meeting"), ("comite", "es", "reunión del comité"), ("flyer", "en", "flyer"),
    # (round 37's fixer) the events by the word "events" and by their month; the shop's sections by "shop"; a story of
    # the Texas writers archive by its title
    ("events", "en", "events"), ("eventos", "es", "eventos"), ("upcoming", "en", "upcoming events"),
    ("proximos", "es", "próximos eventos"), ("march", "en", "march"), ("marzo", "es", "marzo"),
    ("asamblea-marzo", "es", "asamblea de marzo"), ("march-21", "en", "march 21"), ("shop", "en", "shop"),
    ("tienda", "es", "tienda"), ("suscribirse", "es", "suscribirse"), ("archive", "en", "back from the darkness"),
    ("archivo", "es", "regreso de la oscuridad"), ("waco", "en", "waco darkness"),
]

_BUILT: dict = {}


def built(case: unittest.TestCase) -> dict:
    need_minisearch(case)
    if not _BUILT:
        _BUILT.update(run_js(case, INDEX_JS, data={**fixture(), "queries": QUERIES}, now=BUILT, timeout=300))
    return _BUILT


def rows(hits: list[dict]) -> list[dict]:
    """The results the "all" view lists (search.js: the site's pages go to the "Jump to" box)."""
    return [h for h in hits if h["k"] != "page"]


def entry(index: list[dict], ident: str) -> dict:
    found = [e for e in index if e["id"] == ident]
    if not found:
        raise AssertionError(f"no entry {ident}")
    return found[0]


class QueryTable(unittest.TestCase):
    """The spec's query table, as a visitor of /search/ would get it (the page's own index: kit.siteIndex)."""

    def setUp(self):
        self.r = built(self)
        self.hits = self.r["hits"]

    def test_assemblies_finds_the_assembly(self):
        first = rows(self.hits["assemblies"])[0]
        self.assertEqual((first["k"], first["u"]), ("event", "/events/2099-03-19-test-assembly/"))
        self.assertFalse(first["alt"], "found on its own words (assembly), not through the other language's")

    def test_volante_finds_the_flyers(self):
        got = rows(self.hits["volante"])
        self.assertEqual(got[0]["k"], "flyer")
        flyers = {h["id"] for h in got if h["k"] == "flyer"}
        self.assertEqual(flyers, {f"flyer:drive:{f}" for f in FLYERS})

    def test_presentation_finds_the_five_presentations_first(self):
        self.assertEqual({h["id"] for h in rows(self.hits["presentation"])[:5]}, {f"presentation:{d}" for d in DECKS})
        # (a typo and the Spanish word without its accent find them too)
        self.assertEqual({h["id"] for h in rows(self.hits["typo"])[:5]}, {f"presentation:{d}" for d in DECKS})
        self.assertEqual({h["id"] for h in rows(self.hits["accents"])[:5]}, {f"presentation:{d}" for d in DECKS})

    def test_exhibidor_finds_the_booth_display(self):
        self.assertEqual(rows(self.hits["exhibidor"])[0]["u"], "/es/about/#booth-title")

    def test_faq_finds_the_questions(self):
        want = {"section:contribute-faq", *(f"section:faq{n}" for n in range(1, 7))}
        self.assertEqual({h["id"] for h in rows(self.hits["faq"])[:7]}, want)

    def test_kit_de_diciembre_finds_decembers_toolkit(self):
        first = rows(self.hits["kit"])[0]
        self.assertEqual((first["k"], first["u"]), ("month", "/es/monthly/2099-12/"))

    def test_into_action_finds_the_book_of_the_month(self):
        first = rows(self.hits["botm"])[0]
        self.assertEqual((first["id"], first["u"]), ("botm:gv", "/shop/#botm-gv-title"))

    def test_current_issue_finds_the_issues(self):
        self.assertEqual({h["id"] for h in rows(self.hits["issue"])[:2]}, {"issue:gv", "issue:lv"})

    def test_next_meeting_finds_the_committee_meeting(self):
        first = rows(self.hits["meeting"])[0]
        self.assertEqual((first["id"], first["u"]), ("meeting:next-committee", "/meetings/#next-meeting-h"))

    def test_citywide_finds_the_series_page(self):
        got = rows(self.hits["citywide"])
        # (its flyer, which opens the series' page too, may come first)
        self.assertEqual(got[0]["u"], "/events/series/citywide-dallas/")
        series = [h for h in got[:3] if h["k"] == "event" and h["id"].startswith("ev:recurring:citywide-dallas:")]
        self.assertEqual([h["u"] for h in series], ["/events/series/citywide-dallas/"])

    def test_december_is_not_a_wall_of_cover_albums(self):
        hits = self.hits["december"]
        self.assertGreaterEqual(sum(h["k"] == "album" for h in hits), 41, "every year of covers is still found")
        self.assertLess(sum(h["k"] == "album" for h in hits[:50]), 30)
        self.assertIn("/monthly/2099-12/", [h["u"] for h in rows(hits)[:10]], "the month's own toolkit near the top")

    def test_a_cancelled_event_says_so(self):
        for name, start in (("cancelled", "Cancelled: Cancelled Picnic, "), ("cancelado", "Cancelado: Cancelled Picnic, ")):
            got = rows(self.hits[name])
            self.assertEqual(len(got), 1, name)
            self.assertTrue(got[0]["t"].startswith(start), got[0]["t"])
            self.assertEqual(got[0].get("z"), 1, "ranked low")
            self.assertEqual(got[0]["u"], ("/es" if name == "cancelado" else "") + "/events/2099-02-28-moved-out/")

    def test_the_day_of_the_week_and_the_city(self):
        for name in ("saturday", "sabado"):
            self.assertIn("ev:manual:2099-02-07-test-writing", [h["id"] for h in rows(self.hits[name])], name)

    def test_a_plural_finds_the_singular(self):
        self.assertTrue([h for h in rows(self.hits["plural"]) if h["k"] == "flyer"], "flyers → the flyer entries")

    def test_the_next_workshop_comes_before_any_flyer(self):
        """A flyer repeats its event's title in a short entry: it ranks lower (search.js FLYER_RANK) — the next writing
        workshop is listed before every flyer, and the old workshop's flyer (over: z) after the old workshop."""
        got = rows(self.hits["writing"])
        ids = [h["id"] for h in got]
        flyers = [i for i, h in enumerate(ids) if h.startswith("flyer:")]
        self.assertTrue(flyers, ids)
        self.assertLess(ids.index("ev:manual:2099-02-07-test-writing"), min(flyers), ids)
        self.assertLess(ids.index("ev:manual:2098-12-05-old-workshop"), ids.index("flyer:drive:flyerold000001"))
        self.assertEqual(entry(got, "flyer:drive:flyerold000001").get("z"), 1)

    def test_committee_meeting_lists_the_next_meeting_before_its_flyer(self):
        for name in ("committee", "comite"):
            ids = [h["id"] for h in rows(self.hits[name])]
            self.assertIn("meeting:next-committee", ids[:3], f"{name}: {ids}")
            self.assertLess(ids.index("meeting:next-committee"), ids.index("flyer:drive:flyercomm00001"), name)

    def test_flyer_still_lists_the_flyers_first(self):
        """On "flyer" / "volante" a flyer keeps its full rank: every flyer of what is still to come (or of nothing
        listed) before any event that has a flyer (its words say "flyer volante" too)."""
        ids = [h["id"] for h in rows(self.hits["flyer"])]
        upcoming = [ids.index(f"flyer:drive:{f}") for f in FLYERS if f not in ("flyerold000001", "lvflyerdec0001")]
        events = [i for i, h in enumerate(ids) if h.startswith(("ev:", "cancelled:", "series:"))]
        self.assertTrue(events, ids)
        self.assertLess(max(upcoming), min(events), ids)


    def test_events_and_eventos_list_every_event_to_come(self):
        """(round 37's fixer) every event's words say "event" in both languages, "upcoming" / "próximos" those still to
        come: the committee's events, the series' pages and the magazines' calendars' alike."""
        for name, lang in (("events", "en"), ("eventos", "es"), ("upcoming", "en"), ("proximos", "es")):
            want = {e["id"] for e in self.r["index"][lang] if e["k"] == "event" and not e.get("z")}
            got = {h["id"] for h in rows(self.hits[name]) if h["k"] == "event"}
            self.assertTrue(want, name)
            self.assertLessEqual(want, got, name)
            if name in ("upcoming", "proximos"):
                self.assertFalse([h["id"] for h in rows(self.hits[name]) if h["k"] == "event" and h.get("z")],
                                 f"{name}: none that is over")

    def test_a_month_finds_its_events_first(self):
        """(round 37's fixer) an event over several days by its month's name in either language (its full first and
        last day: searched, never shown), ranked first on a month or a day (search.js DATE_RANK)."""
        for name, lang in (("march", "en"), ("marzo", "es")):
            march = {e["id"] for e in self.r["index"][lang] if e["k"] == "event" and not e.get("z") and e.get("d", "").startswith("2099-03")}
            self.assertIn("ev:manual:2099-03-19-test-assembly", march)
            # every event of March still to come first, before the rest
            self.assertEqual({h["id"] for h in rows(self.hits[name])[:len(march)]}, march, name)
        for name in ("asamblea-marzo", "march-21"):
            first = rows(self.hits[name])[0]
            self.assertEqual(first["id"], "ev:manual:2099-03-19-test-assembly", name)
        x = entry(self.r["index"]["en"], "ev:manual:2099-03-19-test-assembly")["x"]
        for day in ("March 19, 2099", "March 21, 2099", "19 de marzo de 2099", "21 de marzo de 2099"):
            self.assertIn(day, x)

    def test_shop_finds_the_shops_sections(self):
        for name, ids in (("shop", {"botm:gv", "shop:special-planner", "section:shop-subscriptions"}),
                          ("tienda", {"botm:gv", "shop:special-planner", "section:shop-subscriptions"}),
                          ("suscribirse", {"section:shop-subscriptions", "section:shop-group"})):
            self.assertLessEqual(ids, {h["id"] for h in rows(self.hits[name])}, name)

    def test_a_story_of_the_writers_archive(self):
        for name in ("archive", "archivo", "waco"):
            first = rows(self.hits[name])[0]
            self.assertEqual((first["id"], first["u"]), ("wa:back0000001", "https://www.aagrapevine.org/magazine/2098/may/back-darkness"), name)


class TheEntries(unittest.TestCase):
    """What the index says (the made-up site): where each entry links, the words it is found by, nothing private."""

    def setUp(self):
        self.r = built(self)
        self.en, self.es = self.r["index"]["en"], self.r["index"]["es"]

    def test_events_link_their_own_page(self):
        for lang, pre in (("en", ""), ("es", "/es")):
            idx = self.r["index"][lang]
            self.assertEqual(entry(idx, "ev:manual:2099-02-07-test-writing")["u"], pre + "/events/2099-02-07-test-writing/")
            old = entry(idx, "ev:manual:2098-12-05-old-workshop")
            self.assertEqual((old["u"], old.get("z")), (pre + "/events/2098-12-05-old-workshop/", 1), "a past event: its page, ranked low")
            # the online-only orientation and the TBA ACM: pages of their own too
            self.assertEqual(entry(idx, "ev:manual:2099-03-13-gvr-orientation")["u"], pre + "/events/2099-03-13-gvr-orientation/")
            self.assertEqual(entry(idx, "ev:manual:2099-04-11-test-acm-tba")["u"], pre + "/events/2099-04-11-test-acm-tba/")

    def test_a_series_links_its_series_page_once(self):
        for lang, pre in (("en", ""), ("es", "/es")):
            idx = self.r["index"][lang]
            cw = [e for e in idx if e["id"].startswith("ev:recurring:citywide-dallas:")]
            self.assertEqual(len(cw), 1, "the series once: its next date")
            self.assertEqual(cw[0]["u"], pre + "/events/series/citywide-dallas/")
            lv = [e for e in idx if e["id"].startswith("ev:recurring:lv-monthly-workshop:")]
            self.assertEqual([e["u"] for e in lv], [pre + "/events/series/lv-monthly-workshop/"])
            # a disabled series has no series' page: its date's own page
            off = [e for e in idx if e["id"].startswith("ev:recurring:off-series:")]
            self.assertEqual(len(off), 1)
            self.assertTrue(off[0]["u"].startswith(pre + "/events/ev-recurring-off-series-"), off[0]["u"])

    def test_a_series_page_whose_only_dates_were_moved(self):
        """La Viña's workshop with none of its rule's dates in the data — only the sessions the host moved (dated
        flyers): its series' page still has an entry (and each moved date its own)."""
        fx = fixture()
        fx["db"]["events"]["items"] = [e for e in fx["db"]["events"]["items"] if not e["id"].startswith("ev:recurring:lv-monthly-workshop:")]
        r = run_js(self, r"""
          const nav = (await imp("src/_data/nav.js")).default;
          out(Object.fromEntries(["en", "es"].map((l) => [l, JSON.parse(filters.searchIndexJson(input.db, nav, l, input.site, input.presentations)).items
            .filter((e) => e.k === "event" && /lv-monthly-workshop|lvflyer/.test(e.id + " " + e.u))])));""", data=fx, now=BUILT)
        for lang, pre in (("en", ""), ("es", "/es")):
            hub = [e for e in r[lang] if e["id"] == "series:lv-monthly-workshop"]
            self.assertEqual([e["u"] for e in hub], [pre + "/events/series/lv-monthly-workshop/"], lang)
            self.assertIn("La Viña", hub[0]["t"])
            moved = [e for e in r[lang] if e["id"] == "ev:flyer:lvflyerfeb7654"]
            self.assertEqual(len(moved), 1)
            self.assertTrue(moved[0]["u"].startswith(pre + "/events/"), moved[0]["u"])
            self.assertNotEqual(moved[0]["u"], pre + "/events/series/lv-monthly-workshop/")
        # with a date of the rule in the data, no second entry for the series' page
        self.assertFalse([e for e in self.en if e["id"] == "series:lv-monthly-workshop"])

    def test_a_cancelled_event_has_one_entry_at_its_notice(self):
        for lang, pre, word in (("en", "", "Cancelled"), ("es", "/es", "Cancelado")):
            idx = self.r["index"][lang]
            notice = entry(idx, "cancelled:ev:manual:2099-02-28-moved-out")
            self.assertEqual((notice["k"], notice["u"], notice.get("z")), ("event", pre + "/events/2099-02-28-moved-out/", 1))
            self.assertTrue(notice["t"].startswith(word + ": "), notice["t"])
            self.assertFalse([e for e in idx if e["id"] == "ev:manual:2099-02-28-moved-out"], "never an ordinary entry too")
            # one that is over, and the one cancelled in the items themselves, as db.js moves it: none / its notice
            self.assertFalse([e for e in idx if "2098-11-28-old-cancelled" in e["id"]], "over: no notice, no entry")
            self.assertTrue([e for e in idx if e["id"] == "cancelled:ev:manual:2099-02-21-cancelled-workshop"])

    def test_an_events_words(self):
        x = entry(self.en, "ev:manual:2099-02-07-test-writing")["x"]
        for word in ("Saturday", "sábado", "Tyler", "District 99 La Viña Committee", "Writing workshop", "Taller de escritura",
                     "flyer", "volante"):
            self.assertIn(word, x)
        # our own events never get the committee's name (every one of them is the committee's)
        self.assertNotIn("Test Committee", entry(self.en, "ev:manual:2099-02-14-test-recording")["x"])
        # a series: its kind in both languages, the booth's words as before
        cw = next(e for e in self.en if e["id"].startswith("ev:recurring:citywide-dallas:"))
        for word in ("Literature booth", "Mesa de literatura", "booth literature table", "every month monthly"):
            self.assertIn(word, cw["x"])

    def test_nothing_says_how_to_join(self):
        for lang in ("en", "es"):
            text = json.dumps(self.r["index"][lang], ensure_ascii=False)
            for secret in SECRETS:
                self.assertNotIn(secret, text, f"{lang}: {secret}")
        # (the rest of that summary stays searchable)
        self.assertIn("Bring a friend", entry(self.en, "ev:manual:2099-03-13-gvr-orientation")["x"])

    def test_the_next_committee_meeting(self):
        for lang, pre, start in (("en", "", "Next committee meeting: "), ("es", "/es", "Próxima reunión del comité: ")):
            m = entry(self.r["index"][lang], "meeting:next-committee")
            self.assertEqual((m["k"], m["u"]), ("meeting", pre + "/meetings/#next-meeting-h"))
            self.assertTrue(m["t"].startswith(start), m["t"])
            self.assertIn("21", m["t"])
            self.assertNotIn("Pat", json.dumps(m, ensure_ascii=False), "never the guest speaker's name")
            # its platform, as the card's "Join on Google Meet" (config/site.yml meeting:), never its link or code
            self.assertIn("Google Meet", m["s"])
        # (mid-sentence, Spanish writes the day of the week in lower case)
        self.assertTrue(entry(self.es, "meeting:next-committee")["t"].startswith("Próxima reunión del comité: miércoles, 21 de enero"))
        self.assertIn("Wednesday, January 21", entry(self.en, "meeting:next-committee")["t"])

    def test_no_zoom_id_in_the_weekly_meeting_and_the_posts(self):
        """The index is a file anyone can read: a weekly open meeting's result says "Online on Zoom" (its ID and
        passcode are on /meetings/#weekly-open), an Instagram post's caption loses its sentences that say how to join."""
        for lang, word in (("en", "Online on Zoom"), ("es", "En línea por Zoom")):
            w = entry(self.r["index"][lang], "weekly-open:weekly_open")
            self.assertTrue(w["s"].endswith(" · " + word), w["s"])
            post = entry(self.r["index"][lang], "ig:test1")
            self.assertEqual(post["s"], "Reunión abierta cada jueves. Escuche el podcast de prueba.")
            self.assertEqual(post["t"], "Reunión abierta cada jueves.")

    def test_faq_is_the_faqs_word_alone(self):
        """"faq" / "preguntas frecuentes" find the Share your story page (its FAQ), never an open call for stories,
        which shares the page's other words."""
        topic = entry(self.en, "ed:test1")
        self.assertNotIn("faq", topic["x"])
        self.assertIn("faq", entry(self.en, "page:contribute")["x"])
        self.assertIn("preguntas frecuentes", entry(self.es, "page:contribute")["x"])
        self.assertFalse([h for h in self.r["hits"]["faq"] if h["k"] == "topic"])

    def test_the_presentations(self):
        for lang, pre in (("en", ""), ("es", "/es")):
            got = [e for e in self.r["index"][lang] if e["k"] == "presentation"]
            self.assertEqual([e["id"] for e in got], [f"presentation:{d}" for d in DECKS])
            for e, d in zip(got, DECKS):
                self.assertEqual((e["u"], e["u2"]), (f"{pre}/orientation/#pres-{d}", f"{pre}/orientation/?present={d}"))
        self.assertEqual(entry(self.es, "presentation:writing-workshop")["t"], "Presentación de prueba writing-workshop")

    def test_the_sections(self):
        for lang, pre in (("en", ""), ("es", "/es")):
            idx = self.r["index"][lang]
            for s in self.r["sections"]:
                e = entry(idx, "section:" + s["id"])
                self.assertEqual((e["k"], e["u"], e["ic"]), ("section", f"{pre}{s['page']}#{s['anchor']}", s["icon"]))
                self.assertEqual(e["t"], self.r["titles"][lang][s["id"]], s["id"])
        self.assertEqual(len({s["id"] for s in self.r["sections"]}), len(self.r["sections"]), "ids unique")
        self.assertEqual(entry(self.en, "section:orientation-facilitators")["t"], self.r["titles"]["en"]["orientation-facilitators"])
        self.assertNotIn("{", self.r["titles"]["en"]["orientation-facilitators"], "its minutes filled in")

    def test_the_month_toolkits(self):
        months = [e for e in self.es if e["k"] == "month"]
        keys = [f"2099-{m:02d}" for m in range(1, 13)] + ["2100-01"]
        self.assertEqual([e["id"] for e in months], [f"month:{k}" for k in keys])
        for e, k in zip(months, keys):
            self.assertEqual((e["u"], e["d"], e["dp"]), (f"/es/monthly/{k}/", f"{k}-01", "m"))
        self.assertEqual(entry(self.en, "month:2099-12")["t"], "Monthly toolkit: December 2099")

    def test_the_current_issues(self):
        for lang, pre in (("en", ""), ("es", "/es")):
            idx = self.r["index"][lang]
            self.assertEqual(entry(idx, "issue:gv")["u"], pre + "/read/#gv-current")
            self.assertEqual(entry(idx, "issue:lv")["u"], pre + "/read/#lv-current")
        self.assertEqual(entry(self.en, "issue:gv")["t"], "Test Theme of the Month")
        self.assertEqual(entry(self.es, "issue:lv")["t"], "La alegría de prueba")

    def test_the_flyers_open_what_they_are_for(self):
        for lang, pre in (("en", ""), ("es", "/es")):
            idx = self.r["index"][lang]
            want = {"flyerwrite00001": "/events/2099-02-07-test-writing/", "flyercity000001": "/events/series/citywide-dallas/",
                    "flyerweekly0001": "/meetings/#weekly-open", "flyerloose00001": "/portfolio/#docs-flyers",
                    "flyerold000001": "/events/2098-12-05-old-workshop/", "flyercomm00001": "/meetings/#committee-meeting",
                    # (a moved date of a series that is over: its series' page, not that date's)
                    "lvflyerdec0001": "/events/series/lv-monthly-workshop/"}
            for fid, u in want.items():
                self.assertEqual(entry(idx, f"flyer:drive:{fid}")["u"], pre + u, fid)
            self.assertFalse([e for e in idx if e["id"] == "flyer:drive:flyerpdf000001"], "a PDF is a Library document")
            # its date: its event's (never the day it was put on the Drive), ranked low once that is over; a flyer of
            # nothing listed: its Drive date
            dates = {fid: (entry(idx, f"flyer:drive:{fid}").get("d"), entry(idx, f"flyer:drive:{fid}").get("z")) for fid in want}
            self.assertEqual(dates["flyerwrite00001"], ("2099-02-07", None))
            self.assertEqual(dates["flyerold000001"], ("2098-12-05", 1))
            self.assertEqual(dates["lvflyerdec0001"], ("2098-12-16", 1))
            self.assertEqual(dates["flyercomm00001"], ("2099-01-21", None))
            self.assertEqual(dates["flyerloose00001"], ("2098-12-20", None))
        self.assertIn("volante", entry(self.en, "flyer:drive:flyerloose00001")["x"])

    def test_a_series_page_is_linked_once_it_is_built(self):
        """The build's pages, as Eleventy lists them before rendering any ("eleventy.contentMap": every page of every
        template, a pagination's too): a series' page the build does not write is never linked — its next date opens
        its own page, and so does its flyer; once written, the series' page. (Here the build writes CityWide's Spanish
        series' page alone.)"""
        r = run_js(self, r"""
          // eleventy.config.js and its area plugins, as nodejs.py registers them — and their event handlers kept
          const F = {}, P = [], on = {};
          const cfg = new Proxy({}, { get(_t, name) {
            if (name === "addFilter" || name === "addNunjucksFilter") return (n, fn) => { F[n] = fn; };
            if (name === "addPlugin") return (fn) => { P.push(fn); };
            if (name === "on") return (ev, fn) => { (on[ev] = on[ev] || []).push(fn); };
            return () => ({ add() {} });
          } });
          (await imp("eleventy.config.js")).default(cfg);
          for (const fn of P) if (typeof fn === "function" && !fn.name) await fn(cfg);
          const map = Object.fromEntries(["/events/", "/es/events/", "/es/events/series/citywide-dallas/", "/search-index.json"]
            .map((u) => [u, { inputPath: "./src/pages/x.njk", groupNumber: 0 }]));
          for (const fn of on["eleventy.contentMap"] || []) fn({ urlToInputPath: map, inputPathToUrl: {} });
          const nav = (await imp("src/_data/nav.js")).default;
          out(Object.fromEntries(["en", "es"].map((l) => [l, JSON.parse(F.searchIndexJson(input.db, nav, l, input.site, input.presentations)).items
            .filter((e) => /citywide|lv-monthly-workshop|grapevine-meeting|flyercity/.test(e.id) || /\/events\/series\//.test(e.u))
            .map((e) => ({ id: e.id, u: e.u }))])));""", data=fixture(), now=BUILT, needs_modules=False)
        cw_date = f"/events/ev-recurring-citywide-dallas-{SP.cw1.isoformat()}/"
        en = {e["id"]: e["u"] for e in r["en"]}
        self.assertEqual([u for u in en.values() if "/events/series/" in u], [], "no series' page in the English build")
        self.assertEqual(en[f"ev:recurring:citywide-dallas:{SP.cw1.isoformat()}"], cw_date)
        self.assertEqual(en["flyer:drive:flyercity000001"], cw_date)
        self.assertNotIn("series:lv-monthly-workshop", en)
        es = {e["id"]: e["u"] for e in r["es"]}
        self.assertEqual(es[f"ev:recurring:citywide-dallas:{SP.cw1.isoformat()}"], "/es/events/series/citywide-dallas/")
        self.assertEqual(es["flyer:drive:flyercity000001"], "/es/events/series/citywide-dallas/")
        self.assertEqual(sorted({u for u in es.values() if "/events/series/" in u}), ["/es/events/series/citywide-dallas/"])

    def test_the_shop(self):
        self.assertEqual(entry(self.en, "botm:gv")["u"], "/shop/#botm-gv-title")
        self.assertEqual(entry(self.es, "shop:special-planner")["u"], "/es/shop/#special-planner")

    def test_a_year_of_covers_ranks_lower(self):
        covers = [e for e in self.en if e["id"].startswith("covers:")]
        self.assertEqual(len(covers), 41)
        self.assertTrue(all(e.get("lw") == 1 for e in covers))
        # (and since round 37's fixer the Texas writers archive's stories: below the newer articles)
        self.assertFalse([e for e in self.en if e.get("lw") and not e["id"].startswith(("covers:", "wa:"))])

    def test_the_writers_archive(self):
        """(round 37's fixer) each story of /published/#archive at its page on the magazine's site: its title in both
        languages, its writer and hometown, its issue; ranked low (lw); one the Library has already keeps its entry."""
        en, es = entry(self.en, "wa:back0000001"), entry(self.es, "wa:back0000001")
        self.assertEqual((en["k"], en["t"], en["a"], en["s"], en.get("lw")),
                         ("article", "Back from the Darkness", "Will J. · Waco, Texas", "May 2098 · AA Grapevine", 1))
        self.assertEqual(en["x"], "How the steps changed my life")
        self.assertEqual((es["t"], es["o"], es.get("m")), ("Regreso de la oscuridad", "Back from the Darkness", 1))
        self.assertNotIn("d", en, "no date: a lean entry")
        self.assertFalse([e for e in self.en if e["id"] == "wa:dup0000001"], "the Library's own entry stays the one")

    def test_the_weekly_meeting_ranks_above_its_recordings(self):
        self.assertEqual(entry(self.en, "weekly-open:weekly_open").get("pr"), 1)
        self.assertFalse([e["id"] for e in self.en if e.get("pr") and not e["id"].startswith("weekly-open:")])

    def test_every_kind_has_its_label_filter_and_icon(self):
        njk = (ROOT / "src/pages/search.njk").read_text(encoding="utf-8")
        js = (ROOT / "src/assets/js/search.js").read_text(encoding="utf-8")
        kinds_block = re.search(r"kinds: \{(.*?)\n  \},", njk, re.S).group(1)
        labelled = set(re.findall(r"(\w+): \"", kinds_block))
        icons = set(re.findall(r'"([a-z0-9-]+)"', re.search(r'<template id="ss-icons">\s*\{%-? for name in \[(.*?)\] %\}', njk, re.S).group(1)))
        group = set(re.findall(r"(\w+): \"", re.search(r"var GROUP = \{(.*?)\};", js, re.S).group(1)))
        kind_icon = dict(re.findall(r"(\w+): \"([a-z0-9-]+)\"", re.search(r"var KIND_ICON = \{(.*?)\};", js, re.S).group(1)))
        for lang in ("en", "es"):
            for e in self.r["index"][lang]:
                self.assertIn(e["k"], labelled, f"search.njk kinds: {e['k']}")
                self.assertIn(e["k"], group, f"search.js GROUP: {e['k']}")
                if e.get("ic"):
                    self.assertIn(e["ic"], icons, f"ss-icons: {e['ic']} ({e['id']})")
        for k in ("section", "month", "presentation", "issue", "flyer"):
            self.assertIn(kind_icon[k], icons, k)
            self.assertIn(k, kind_icon)
        self.assertIn("monitor-play", icons, "the presentation's second link")


# The kit alone, on a few made-up titles: { [name]: { titles, alt } }, plus the lw scores and a rendered presentation.
KIT_JS = PAGE_JS + r"""
const p = page({ url: "https://example.test/aagrapevine/search/", globals: { SITE: { lang: "en", base: "/aagrapevine/" } },
                 scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js"] });
vm.runInContext(fs.readFileSync("src/assets/js/search.js", "utf8"), p.win, { filename: "search.js" });
const K = p.win.GV.searchKit;
const items = input.titles.map((t, i) => ({ id: "t" + i, k: "article", t }));
const ms = K.siteIndex(items);
const res = {};
for (const q of input.queries) {
  const r = K.search(ms, q);
  res[q] = { titles: r.hits.map((h) => items[h.id].t), alt: r.hits.filter((h) => h.alt).map((h) => items[h.id].t) };
}
// lw: two entries alike but for it
const pair = [{ id: "a", k: "album", t: "December covers", lw: 1 }, { id: "b", k: "album", t: "December covers" }];
const lw = K.search(K.siteIndex(pair), "december").hits.map((h) => ({ id: pair[h.id].id, score: h.score }));
// a flyer and an event alike: the flyer lower on its event's words, the same on "flyer" / "volante"
const fe = [{ id: "f", k: "flyer", t: "Workshop flyer" }, { id: "e", k: "event", t: "Workshop flyer" }];
const fms = K.siteIndex(fe);
const flyer = Object.fromEntries(["workshop", "flyer", "volante"].map((q) => [q, K.search(fms, q).hits.map((h) => ({ id: fe[h.id].id, score: h.score }))]));
// (round 37's fixer) a month or a day: an event still to come ranks well up (one over, or a post, does not); an entry
// marked pr above one alike
const de = [{ id: "ev", k: "event", t: "Spring gathering", s: "March 19, 2999", d: "2999-03-19" },
  { id: "post", k: "post", t: "Spring gathering", s: "March 19, 2999", d: "2999-03-19" },
  { id: "over", k: "event", t: "Spring gathering", s: "March 19, 2999", d: "2999-03-19", z: 1 }];
const dms = K.siteIndex(de);
const dated = Object.fromEntries(["march", "19", "marzo", "spring"].map((q) => [q, Object.fromEntries(K.search(dms, q).hits.map((h) => [de[h.id].id, h.score]))]));
const pe = [{ id: "m", k: "meeting", t: "Weekly Open Meeting", pr: 1 }, { id: "r", k: "video", t: "Weekly Open Meeting" }];
const prime = K.search(K.siteIndex(pe), "weekly open meeting").hits.map((h) => ({ id: pe[h.id].id, score: h.score }));
out({ res, lw, flyer, dated, prime });
"""


class TheKit(unittest.TestCase):
    TITLES = ["Spring Assembly", "Un día a la vez", "My Story", "Stories of hope", "Series of talks", "A booth for the table",
              "Flyer of the month", "Presentation night", "Current issue", "Preguntas frecuentes", "The cancelled picnic",
              "Recording tips", "Writing tips", "Orientation day", "Monthly toolkit", "Plaza mayor", "La luz", "Las cruces"]
    QUERIES = ["assemblies", "veces", "story", "stories", "series", "places", "exhibidor", "pantalla", "volante",
               "presentación", "número", "faq", "cancelado", "grabación", "escritura", "orientación", "kit", "luces", "cruz"]

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        need_minisearch(self)
        if TheKit.r is None:
            TheKit.r = run_js(self, KIT_JS, data={"titles": self.TITLES, "queries": self.QUERIES}, needs_modules=False)
        self.res = TheKit.r["res"]

    def test_a_words_other_number(self):
        self.assertEqual(self.res["assemblies"]["titles"], ["Spring Assembly"])
        self.assertEqual(self.res["assemblies"]["alt"], [], "its own word, not the other language's")
        self.assertEqual(self.res["veces"]["titles"], ["Un día a la vez"])
        self.assertEqual(set(self.res["story"]["titles"]), {"My Story", "Stories of hope"})
        self.assertEqual(set(self.res["stories"]["titles"]), {"My Story", "Stories of hope"})
        self.assertEqual(self.res["luces"]["titles"], ["La luz"])
        self.assertEqual(self.res["cruz"]["titles"], ["Las cruces"])
        # a guess that is no word finds nothing it should not ("series" → "sery", "places" → "plaz", not "Plaza")
        self.assertEqual(self.res["series"]["titles"], ["Series of talks"])
        self.assertNotIn("Plaza mayor", self.res["places"]["titles"])

    def test_the_round_37_words_of_the_other_language(self):
        for q, title in (("exhibidor", "A booth for the table"), ("pantalla", "A booth for the table"), ("volante", "Flyer of the month"),
                         ("número", "Current issue"), ("faq", "Preguntas frecuentes"), ("cancelado", "The cancelled picnic"),
                         ("grabación", "Recording tips"), ("escritura", "Writing tips"), ("kit", "Monthly toolkit")):
            self.assertIn(title, self.res[q]["titles"], q)
            self.assertIn(title, self.res[q]["alt"], f"{q}: through the other language's word, so ranked after")
        # a word one letter from its twin is found by its own (light fuzzy) matching
        for q, title in (("presentación", "Presentation night"), ("orientación", "Orientation day")):
            self.assertIn(title, self.res[q]["titles"], q)

    def test_a_year_of_covers_ranks_lower(self):
        lw = TheKit.r["lw"]
        self.assertEqual([h["id"] for h in lw], ["b", "a"])
        self.assertAlmostEqual(lw[1]["score"] / lw[0]["score"], 0.7, places=2)

    def test_a_flyer_ranks_lower_but_on_flyer(self):
        f = TheKit.r["flyer"]
        self.assertEqual([h["id"] for h in f["workshop"]], ["e", "f"])
        self.assertAlmostEqual(f["workshop"][1]["score"] / f["workshop"][0]["score"], 0.5, places=2)
        for q in ("flyer", "volante"):
            scores = {h["id"]: h["score"] for h in f[q]}
            self.assertAlmostEqual(scores["f"], scores["e"], places=6, msg=q)

    def test_a_month_or_a_day_ranks_an_event_to_come_first(self):
        d = TheKit.r["dated"]
        for q in ("march", "19"):
            self.assertAlmostEqual(d[q]["ev"] / d[q]["post"], 10, places=3, msg=q)
            self.assertAlmostEqual(d[q]["over"] / d[q]["post"], 0.6, places=3, msg=f"{q}: one over ranks low")
        self.assertEqual(d["marzo"], {}, "a word the entries do not have")
        self.assertAlmostEqual(d["spring"]["ev"] / d["spring"]["post"], 1, places=6, msg="any other word: as before")

    def test_the_place_to_go_ranks_above_entries_alike(self):
        p = TheKit.r["prime"]
        self.assertEqual([h["id"] for h in p], ["m", "r"])
        self.assertAlmostEqual(p[0]["score"] / p[1]["score"], 1.8, places=3)

    def test_a_presentation_starts_from_its_result(self):
        r = run_js(self, PAGE_JS + r"""
          const ids = ["ss-q", "ss-clear", "ss-status", "ss-results", "ss-more", "ss-jump-wrap", "ss-jump", "ss-kinds-wrap", "ss-start",
                       "ss-none", "ss-partial", "ss-error", "ss-loading", "ss-did", "ss-none-kind", "ss-layout", "ss-none-title", "ss-none-kind-btn", "ss-retry"];
          const cfg = { lang: "en", locale: "en-US", index: "/search-index.json", title: "Search", kinds: { presentation: "Presentation" }, groups: {},
                        src: { neta: "NETA 65" }, langTitle: {}, s: { count: "{n} results", countOne: "1 result", countIn: "", noneTitle: "", noneKind: "",
                        isNew: "New", auto: "", autoHelp: "", external: "opens a new tab", subscriber: "", subscriberTitle: "", byline: "", tbc: "", tbcHelp: "",
                        episodePage: "Episode page", present: "Start the presentation" } };
          const html = '<form id="ss-form"><input id="ss-q"></form><section id="site-search">' + ids.slice(1).map((i) => (i === "ss-results" ? '<ol id="' + i + '"></ol>' : '<div id="' + i + '"></div>')).join("") +
                       '</section><template id="ss-icons"></template><script type="application/json" id="ss-config">' + JSON.stringify(cfg) + '</script>';
          const fetch = async () => ({ ok: true, json: async () => ({ items: [input] }) });
          const p = page({ url: "https://example.test/aagrapevine/search/?q=writing", html, globals: { SITE: { lang: "en", base: "/aagrapevine/" }, fetch },
                           scripts: ["node_modules/minisearch/dist/umd/index.js", "src/assets/js/app.js", "src/assets/js/search.js"] });
          await p.ready();
          await p.tick(500);
          const li = p.$("#ss-results li");
          const alt = li && li.querySelector("a.ss-alt");
          out({ main: li && li.querySelector("a[data-nav]").getAttribute("href"), alt: alt && alt.getAttribute("href"),
                altText: alt && alt.textContent, altTab: alt && alt.getAttribute("target"), inside: !!(li && li.querySelector("a[data-nav] .ss-alt")) });""",
                   data={"id": "presentation:writing-workshop", "k": "presentation", "t": "Writing Workshop", "u": "/orientation/#pres-writing-workshop",
                         "u2": "/orientation/?present=writing-workshop", "src": "neta"}, needs_modules=False)
        self.assertEqual(r["main"], "/aagrapevine/orientation/#pres-writing-workshop")
        self.assertEqual(r["alt"], "/aagrapevine/orientation/?present=writing-workshop")
        self.assertIsNone(r["altTab"], "one of our own pages: the same tab")
        self.assertIn("Start the presentation", r["altText"])
        self.assertFalse(r["inside"], "never a link inside the result's link")


# searchProblems on made-up build results: [{ url, outputPath, content }]
GUARD_JS = r"""
const S = await imp("eleventy/seo-check.js");
const W = await imp("eleventy/build-warnings.js");
const base = input.base;
const page = (url, ids = []) => ({ url, outputPath: "_site" + url + "index.html",
  content: "<html><head><title>x</title></head><body>" + ids.map((i) => `<h2 id="${i}">x</h2>`).join("") + "</body></html>" });
const sitemap = (paths) => ({ url: "/sitemap.xml", outputPath: "_site/sitemap.xml",
  content: "<urlset>" + paths.map((p) => `<url><loc>${base}${p}</loc></url>`).join("") + "</urlset>" });
const index = (lang, items, pad = 0) => ({ url: lang === "en" ? "/search-index.json" : "/es/search-index.json", outputPath: "x.json",
  content: JSON.stringify({ v: 2, lang, items, pad: "x".repeat(pad) }) });
const e = (id, u, extra = {}) => ({ id, k: "page", t: id, u, ...extra });
const good = () => [
  page("/"), page("/es/"), page("/about/", ["booth-title"]), page("/es/about/", ["booth-title"]), page("/orientation/", ["pres-x"]),
  page("/es/orientation/", ["pres-x"]), sitemap(["/", "/es/", "/about/", "/es/about/"]),
  index("en", [e("home", "/"), e("about", "/about/"), e("booth", "/about/#booth-title"), e("deck", "/orientation/#pres-x", { u2: "/orientation/?present=x" }),
               e("file", "/assets/doc.pdf"), e("away", "https://example.org/")]),
  index("es", [e("home", "/es/"), e("about", "/es/about/#booth-title")]),
];
const R = {};
R.good = S.searchProblems(good(), base);
R.noIndex = S.searchProblems(good().filter((r) => !/search-index/.test(r.url)), base);
R.noSitemap = S.searchProblems(good().filter((r) => r.url !== "/sitemap.xml"), base);
{ const r = good(); r[r.length - 1] = index("es", [e("home", "/es/")]); R.esMissing = S.searchProblems(r, base); }
{ const r = good(); r.push(page("/events/x/")); r[6] = sitemap(["/", "/es/", "/about/", "/es/about/", "/events/x/"]); R.notFound = S.searchProblems(r, base); }
{ const r = good(); r[7] = index("en", [e("home", "/"), e("about", "/about/#gone")]); R.badAnchor = S.searchProblems(r, base); }
{ const r = good(); r[7] = index("en", [e("home", "/"), e("about", "/about/"), e("ghost", "/ghost/")]); R.notBuilt = S.searchProblems(r, base); }
{ const r = good(); r[7] = index("en", [e("home", "/"), e("about", "/about/"), e("deck", "/orientation/", { u2: "/orientation/#nope" })]); R.u2 = S.searchProblems(r, base); }
{ const r = good(); r[7] = index("en", [e("home", "/"), e("about", "/about/"), e("hub", "/events/series/citywide-dallas/")]); R.hubNoSeries = S.searchProblems(r, base); }
{ const r = good(); r.push(page("/events/series/grapevine-meeting/")); r[7] = index("en", [e("home", "/"), e("about", "/about/"), e("hub", "/events/series/citywide-dallas/"), e("hub2", "/events/series/grapevine-meeting/")]);
  R.hubWithSeries = S.searchProblems(r, base); }
{ const r = good(); r[7] = index("en", [e("home", "/"), e("about", "/about/")], S.SEARCH_LIMIT); R.big = S.searchProblems(r, base); }
R.limit = S.SEARCH_LIMIT;
// seoCheck: each one a "[search]" build warning
W.clearBuildWarnings();
{ const r = good(); r[7] = index("en", [e("home", "/"), e("about", "/about/#gone")]);
  R.checkSearch = S.searchProblems(r, base);
  R.check = S.seoCheck({ results: r, outputMode: "fs" }, { SITE_URL: base }, "-none-.yml"); R.warnings = W.buildWarnings(); }
W.clearBuildWarnings();
R.onlyBuild = S.seoCheck({ results: good(), outputMode: "fs" }, { SITE_URL: base, ONLY: "search-index" }, "-none-.yml");
out(R);
"""


class TheCheck(unittest.TestCase):
    """The [search] check (eleventy/seo-check.js searchProblems; a "[search]" build warning each, seoCheck)."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if TheCheck.r is None:
            # a site with a path prefix (the Code check builds under /aagrapevine/): the <loc>s carry it, the pages and
            # the index's paths never do
            TheCheck.r = run_js(self, GUARD_JS, data={"base": "https://x.test/aagrapevine"}, needs_modules=False)
        self.r = TheCheck.r

    def test_a_site_whose_search_finds_everything(self):
        self.assertEqual(self.r["good"], [])
        self.assertEqual(self.r["noIndex"], [], "a build without the index (ONLY=…) has nothing to check")
        self.assertEqual(self.r["noSitemap"], [])
        self.assertEqual(self.r["limit"], 1600000)

    def test_a_page_the_search_cannot_find(self):
        self.assertEqual(len(self.r["notFound"]), 1)
        self.assertIn("/events/x/: in the sitemap, but no entry of /search-index.json links it", self.r["notFound"][0])
        # each language's index finds its own pages: the Spanish one /es/…
        self.assertEqual(len(self.r["esMissing"]), 1)
        self.assertIn("/es/about/", self.r["esMissing"][0])
        self.assertIn("/es/search-index.json", self.r["esMissing"][0])

    def test_a_link_to_what_the_build_lacks(self):
        self.assertEqual(len(self.r["badAnchor"]), 1)
        self.assertIn('/about/ has no id="gone"', self.r["badAnchor"][0])
        self.assertEqual(len(self.r["notBuilt"]), 1)
        self.assertIn("links /ghost/, a page the build has not written", self.r["notBuilt"][0])
        self.assertEqual(len(self.r["u2"]), 1, "the second link too")
        self.assertIn('/orientation/ has no id="nope"', self.r["u2"][0])

    def test_a_series_page_is_checked_like_any_other(self):
        # (the search links one only once the build writes it: library.js, collections.all — a link to one missing is
        # a problem, whether or not the build has any series' page)
        self.assertEqual(len(self.r["hubNoSeries"]), 1)
        self.assertIn("links /events/series/citywide-dallas/, a page the build has not written", self.r["hubNoSeries"][0])
        self.assertEqual(len(self.r["hubWithSeries"]), 1)
        self.assertIn("/events/series/citywide-dallas/", self.r["hubWithSeries"][0])

    def test_the_size_budget(self):
        self.assertEqual(len(self.r["big"]), 1)
        self.assertIn("/search-index.json is ", self.r["big"][0])
        self.assertIn("over its 1,600,000-byte budget", self.r["big"][0])

    def test_each_problem_is_a_search_build_warning(self):
        # (the made-up pages have no canonical or description: their [seo] problems come first)
        self.assertEqual(len(self.r["checkSearch"]), 1)
        self.assertEqual(self.r["check"][-1:], self.r["checkSearch"])
        self.assertEqual([w for w in self.r["warnings"] if w.startswith("[search] ")], ["[search] " + self.r["checkSearch"][0]])
        self.assertTrue([w for w in self.r["warnings"] if w.startswith("[seo] ")], "the [seo] check still runs first")
        self.assertEqual(self.r["onlyBuild"], [], "never in a build of some pages")


# A build (toJSON) of the pages that have sections, both languages; the headings' words by their id
SECTIONS_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const { SEARCH_SECTIONS } = await imp("eleventy/search-sections.js");
const orientation = (await imp("src/_data/orientation.js")).default();
const history = (await imp("src/_data/history.js")).default();
const conf = await imp("eleventy.config.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r37-search-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  const pages = await elev.toJSON();
  const byUrl = new Map(pages.map((p) => [p.url, p.content]));
  const text = (s) => s.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"').replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();
  const res = [];
  for (const lang of ["en", "es"]) {
    for (const s of SEARCH_SECTIONS) {
      const url = (lang === "es" ? "/es" : "") + s.page;
      const html = byUrl.get(url) || "";
      const m = new RegExp(`<(h[1-6]|section|summary|div|article)\\b[^>]*\\bid="${s.anchor}"[^>]*>([\\s\\S]*?)</\\1>`).exec(html);
      const want = conf.translateKey(s.title, lang, typeof s.titleVars === "function" ? s.titleVars({ orientation }) : undefined);
      // (a section its page leaves out — library.js gives it no entry either)
      const shown = typeof s.shown !== "function" || s.shown({ orientation, history });
      res.push({ lang, id: s.id, url, built: byUrl.has(url), found: !!m, tag: m ? m[1] : "", text: m ? text(m[2]) : "", want, shown });
    }
  }
  out(res);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class TheSectionsOnThePages(unittest.TestCase):
    """Every line of eleventy/search-sections.js points at a heading of its page (built, both languages) whose words are
    the entry's title — a heading renamed or moved, or the facilitators' minutes counted differently, fails here."""

    def test_every_section_is_on_its_page(self):
        r = run_js(self, SECTIONS_JS, data={"only": "about,gvr,contribute,meetings,accessibility,orientation.njk,shop,read.njk"},
                   timeout=600, env={"MONTHLY_NOW": BUILT, "STRICT_BUILD": "", "ONLY": ""})
        self.assertTrue(r)
        for row in r:
            with self.subTest(section=row["id"], lang=row["lang"]):
                self.assertTrue(row["built"], f"{row['url']} was not built")
                if not row["shown"]:
                    self.assertFalse(row["found"], f"{row['url']} shows the section its line says it leaves out")
                    continue
                self.assertTrue(row["found"], f"{row['url']} has no element with that id")
                if row["id"].startswith("faq") and row["id"][3:].isdigit():
                    # (the six questions land on the FAQ's section: their words are inside it)
                    self.assertEqual(row["tag"], "section")
                    self.assertIn(row["want"], row["text"])
                    continue
                self.assertEqual(row["text"], row["want"])

    def test_a_section_its_page_leaves_out(self):
        """The history's heading shows only with config/history.yml's milestones (about.njk): without them its line
        says so (shown), and library.js gives it no entry — nothing for the [search] check to miss."""
        r = run_js(self, r"""
          const { SEARCH_SECTIONS } = await imp("eleventy/search-sections.js");
          const h = SEARCH_SECTIONS.find((s) => s.id === "about-history");
          out({ none: h.shown({ history: { items: [] } }), some: h.shown({ history: { items: [{ n: 1 }] } }), unread: h.shown({ history: null }),
                others: SEARCH_SECTIONS.filter((s) => typeof s.shown === "function").map((s) => s.id) });""", needs_modules=False)
        self.assertEqual((r["none"], r["some"], r["unread"]), (False, True, True))
        self.assertEqual(r["others"], ["about-history"])


# The day's index (the real data: src/_data/db.js, site.js, nav.js, presentations.js) and its queries, worked out
# from the day's own data so that they hold whatever it holds
REAL_JS = r"""
const db = (await imp("src/_data/db.js")).default();
const site = (await imp("src/_data/site.js")).default();
const nav = (await imp("src/_data/nav.js")).default;
const presentations = (await imp("src/_data/presentations.js")).default();
const vmod = await import("node:vm");
const json = {}, index = {};
for (const lang of ["en", "es"]) { json[lang] = filters.searchIndexJson(db, nav, lang, site, presentations); index[lang] = JSON.parse(json[lang]).items; }
const ctx = vmod.createContext({ console, URLSearchParams, Intl, Date, setTimeout, clearTimeout, Object, Array, String, RegExp, Math, JSON });
ctx.window = ctx; ctx.location = { search: "" }; ctx.addEventListener = () => {}; ctx.matchMedia = () => ({ matches: false });
ctx.document = { readyState: "complete", getElementById: () => null, addEventListener() {} };
vmod.runInContext(fs.readFileSync("node_modules/minisearch/dist/umd/index.js", "utf8"), ctx);
vmod.runInContext(fs.readFileSync("src/assets/js/search.js", "utf8"), ctx);
const K = ctx.GV.searchKit;
const ms = { en: K.siteIndex(index.en), es: K.siteIndex(index.es) };
const find = (lang, q) => K.search(ms[lang], q).hits.map((h) => index[lang][h.id]);
const botm = ((db.shop && db.shop.botm) || []).find((b) => b && b.pub === "gv" && b.title);
const res = { bytes: { en: Buffer.byteLength(json.en, "utf8"), es: Buffer.byteLength(json.es, "utf8") }, decks: (presentations.decks || []).length,
  kinds: Object.fromEntries(["en", "es"].map((l) => [l, [...new Set(index[l].map((e) => e.k))]])),
  hubs: index.en.filter((e) => /^\/events\/series\//.test(e.u)).map((e) => e.u),
  months: index.es.filter((e) => e.k === "month").map((e) => e.u),
  q: {
    presentation: find("en", "presentation").filter((e) => e.k !== "page").slice(0, (presentations.decks || []).length).map((e) => e.k),
    volante: find("es", "volante").filter((e) => e.k !== "page").slice(0, 3).map((e) => e.k),
    assemblies: find("en", "assemblies").filter((e) => e.k === "event").length,
    issue: find("en", "current issue").filter((e) => e.k !== "page").slice(0, 2).map((e) => e.k),
    meeting: find("en", "next meeting").filter((e) => e.k !== "page").slice(0, 1).map((e) => e.id),
    citywide: find("en", "citywide").filter((e) => e.k !== "page").slice(0, 1).map((e) => e.u),
    december: find("en", "december").slice(0, 50).filter((e) => e.k === "album").length,
    exhibidor: find("es", "exhibidor").filter((e) => e.k !== "page").slice(0, 1).map((e) => e.u),
    faq: find("en", "faq").filter((e) => e.k !== "page").slice(0, 7).map((e) => e.k),
    botm: botm ? find("en", botm.title.split(":")[0]).filter((e) => e.k !== "page").slice(0, 3).map((e) => e.id) : null,
    // the first workshop still to come, and the first flyer of one that is over (their places in the list)
    writing: (() => { const r = find("en", "writing workshop").filter((e) => e.k !== "page");
      return { next: r.findIndex((e) => e.k === "event" && !e.z), pastFlyer: r.findIndex((e) => e.k === "flyer" && e.z) }; })(),
    committee: find("en", "committee meeting").filter((e) => e.k !== "page").slice(0, 3).map((e) => e.id),
    faqTopics: find("en", "faq").filter((e) => e.k === "topic").length,
  },
  // how to join, anywhere in either index: a Zoom ID ("871 2036 8287"), a Zoom or Meet link
  joins: Object.fromEntries(["en", "es"].map((l) => [l, json[l].match(/\b\d{3} \d{4} \d{4}\b|zoom\.us\/j|meet\.google\.com/g) || []])) };
out(res);
"""


class RealIndex(unittest.TestCase):
    """The index of the day's data (scripts/ops/gate_tests.py DATA_TESTS: the data alone can change these answers)."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        need_minisearch(self)
        if RealIndex.r is None:
            RealIndex.r = run_js(self, REAL_JS, timeout=300, env={"STRICT_BUILD": "", "ONLY": ""})
        self.r = RealIndex.r

    def test_the_size_budget(self):
        for lang in ("en", "es"):
            self.assertLessEqual(self.r["bytes"][lang], 1600000, lang)

    def test_the_query_table_on_the_days_data(self):
        q = self.r["q"]
        self.assertEqual(q["presentation"], ["presentation"] * self.r["decks"])
        self.assertEqual(q["volante"], ["flyer"] * 3)
        self.assertGreater(q["assemblies"], 0)
        self.assertEqual(q["issue"], ["issue", "issue"])
        self.assertEqual(q["meeting"], ["meeting:next-committee"])
        self.assertEqual(q["exhibidor"], ["/es/about/#booth-title"])
        self.assertEqual(q["faq"], ["section"] * 7)
        self.assertLess(q["december"], 30)
        if "/events/series/citywide-dallas/" in self.r["hubs"]:
            self.assertEqual(q["citywide"], ["/events/series/citywide-dallas/"])
        if q["botm"] is not None:
            self.assertIn("botm:gv", q["botm"])
        self.assertEqual(len(self.r["months"]), 13)
        if q["writing"]["next"] >= 0 and q["writing"]["pastFlyer"] >= 0:
            self.assertLess(q["writing"]["next"], q["writing"]["pastFlyer"], "the next workshop before any flyer of one that is over")
        self.assertIn("meeting:next-committee", q["committee"])
        self.assertEqual(q["faqTopics"], 0, "an open call for stories is no FAQ")

    def test_nothing_says_how_to_join(self):
        self.assertEqual(self.r["joins"], {"en": [], "es": []})

    def test_every_new_kind_is_there(self):
        for lang in ("en", "es"):
            for k in ("section", "month", "presentation", "issue", "flyer"):
                self.assertIn(k, self.r["kinds"][lang], f"{lang}: {k}")


if __name__ == "__main__":
    unittest.main()
