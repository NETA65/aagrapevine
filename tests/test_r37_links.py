"""Round 37 · every link to an event goes to the event's own page (eleventy/filters/event-links.js evHref / eventLink,
community.js hrefOf, committee.js shapeEvent's detailsUrl), the 404 page forwards an address that is gone, and
/llms.txt lists the events still to come. Checked on made-up events (SITE_DATA: never the day's data), a made-up
monthly series (zz-booth) and the build's clock stopped on Sunday, November 22, 2026:

  * TheLinks — one Eleventy build of every page that links to an event (/events/, the event pages, Home, Contribute,
    the Bulletin, Photos, the monthly toolkit and its report, What's New, the digest, the search page, the RSS feeds,
    the calendar files, /llms.txt, the sitemap):
      - every internal link to an event resolves: each /[es/]events/<anchor>/ address (a page's href, an address in a
        text — the digest's and the report's —, a calendar entry's URL, a feed item, /llms.txt) is a page of the
        build, each /[es/]events/#<anchor> an id on that Events page; a series' page (/events/series/<key>/) too —
        PENDING while the build writes no series' page at all (round 37's unit U2 writes them: before its merge the
        test says so and is skipped; after it, every such link must resolve);
      - each place links the event's page: the /events/ card titles (a series' one card → its series' page, each of its
        dates → the date's own page; the committee meeting's card → /meetings/#committee-meeting, its dates' anchors
        on it; an event with an outside page → its own page, that page its "Organizer's page" button), the "Save the
        date" card, Home, Contribute's workshops, the Bulletin's and Photos' next
        events, the month's dates, What's New, the digest's events, the RSS item, the district report's events;
      - the calendar entries: each one's URL — and its "Details:" line, and a card's .ics data — is the event's own
        page (a date of the series, an event that is over, one from the magazines' calendars, one with a page
        elsewhere alike; a day only, from the magazines' calendars: its "Time not listed" line points to the
        organizer's page, which gives the time); the committee meeting's stays /meetings/#committee-meeting, a
        cancelled event's its notice; a later month's date worked out from a series' rule (no page of its own)
        links to its series' page, and a series whose `url:` is one of our pages (the Grapevine Meeting's section
        of /meetings/) keeps that link.
  * (The booth's countdown QR code and the presentations' event rows keep their link — committee.js shapeEvent's
    cardUrl, the event's own link, else its card: tests/test_booth_build.py, tests/test_presentations_build.py.)
  * TheForwarder — src/assets/js/community.js on the 404 page: /events/series/<key>/ (a series that has no date to
    come) → /events/; /events/ev-recurring-<key>-YYYY-MM-DD/ (a date long over) → /events/series/<key>/; any other
    /events/<anchor>/ → /events/#<anchor> as before; the ?query kept, deeper addresses left to the 404 page.
  * LlmsTxt — "## Upcoming events" just before "## Optional": the series' pages first (since round 38b the committee
    meeting's dates page, /events/series/committee-meeting/, before them), then the one-off events still to come
    whose page may be indexed, soonest first — each a page of the build in the sitemap, its line "- [<its title>](<its
    address>): <its meta description>" (in one line: every space a plain one); never a series' date, an event that is
    over, one from the magazines' calendars, a cancelled one or a single committee meeting, never a meeting ID, code
    or link; at most 20 lines, and none that would take the file past 14 KB (src/pages/llms-txt.11ty.js render, on
    many events).

Runs Eleventy with Node.js (tests/nodejs.py); skipped without Node.js or the site's npm packages.

    python -m unittest tests.test_r37_links -v
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_r30_events_list import at, event  # noqa: E402
from test_r35_head import JOIN  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-11-22T15:00:00Z"             # Sun Nov 22, 2026, 9 AM CST
BASE = "https://x.test"
FW = {"location": "Grupo Dos, 200 Main St, Fort Worth, TX 76106", "city": "Fort Worth", "state": "TX"}
TY = {"location": "Test Center, 1 Main St, Tyler, TX 75702", "city": "Tyler", "state": "TX"}
HALL = {"location": "Test Hall, 1 Main St, Dallas, TX 75201", "city": "Dallas", "state": "TX"}
ZOOM = "https://us06web.zoom.us/j/81595931777"
ZOOM_ID = "815 9593 1777"
# the anchors (and pages) of the test's events
LEAF = "2026-12-12-zz-writing-workshop"          # a writing workshop at a place: a leaf, its Event on its page
ONLINE = "2026-12-19-zz-online-workshop"         # online only, on Zoom with its meeting ID
TBA = "2027-01-16-zz-recording-workshop"         # its place to be announced
ACM = "2027-02-21-zz-acm"                        # its own page on the Area's site
OLD = "2026-10-03-zz-old-workshop"               # over
OFF = "2026-12-05-zz-cancelled"                  # cancelled
CAL = "ev-lvcal-zz1"                             # from La Viña's own calendar
BOOTH = "zz-booth"                               # the test's monthly series
BOOTH_DAYS = (date(2026, 10, 10), date(2026, 11, 14), date(2026, 12, 12), date(2027, 1, 9), date(2027, 2, 13))
HUB = f"/events/series/{BOOTH}/"
RECURRING = [{"key": BOOTH, "title": "GV/LV booth at Test Hall", "title_es": "Mesa de GV/LV en Test Hall",
              "week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "19:00", "location": HALL["location"],
              "url": "https://example.org/zz-booth", "months_ahead": 3}]
# (events-committee: the committee meeting's dates page, since round 38 — /events/ and /meetings/ link it)
ONLY = ("index,events.njk,event-share,events-committee,events-ics,contribute,bulletin,photos,monthly,whats-new,digest,"
        "search.njk,feed,llms,sitemap")


def booth_day(d: date, past: bool) -> dict:
    """A date of the test's series, as build_data writes it (its url: the series' own outside page)."""
    return {**event(f"ev:recurring:{BOOTH}:{d.isoformat()}", "recurring", "GV/LV booth at Test Hall", at(d, "17:00"),
                    at(d, "19:00"), title_es="Mesa de GV/LV en Test Hall", series=BOOTH, recurring=True, host="neta",
                    rule={"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "19:00"}, past=past, **HALL),
            "url": RECURRING[0]["url"]}


def items() -> tuple[list[dict], list[dict]]:
    """events.json's items and cancelled list: one event of each kind a link must find the page of."""
    out = [
        event(f"ev:manual:{LEAF}", "manual", "ZZ Writing Workshop — Fort Worth", at(date(2026, 12, 12), "13:00"),
              at(date(2026, 12, 12), "15:00"), slug=LEAF, title_es="Taller de Escritura ZZ — Fort Worth",
              tags=["workshop", "la-vina"], **FW),
        event(f"ev:manual:{ONLINE}", "manual", "ZZ Online Workshop", at(date(2026, 12, 19), "10:00"),
              at(date(2026, 12, 19), "12:00"), slug=ONLINE, title_es="Taller ZZ en línea", online_url=ZOOM,
              platform="Zoom", meeting_id=ZOOM_ID),
        event(f"ev:manual:{TBA}", "manual", "ZZ Recording Workshop", at(date(2027, 1, 16), "13:00"),
              at(date(2027, 1, 16), "15:00"), slug=TBA, title_es="Taller de Grabación ZZ", tags=["workshop", "grapevine"],
              location="Venue to be announced", location_tba=True, city="Plano", state="TX"),
        {**event(f"ev:manual:{ACM}", "manual", "ZZ Winter ACM", "2027-02-21", "2027-02-21", slug=ACM,
                 title_es="ACM de Invierno ZZ", tags=["neta65", "acm"], **TY), "url": "https://neta65.org/event/zz-acm/"},
        event(f"ev:manual:{OLD}", "manual", "ZZ Old Workshop", at(date(2026, 10, 3), "13:00"), at(date(2026, 10, 3), "15:00"),
              slug=OLD, title_es="Taller ZZ Pasado", past=True, **FW),
        {**event("ev:lvcal:zz1", "lv-calendar", "Taller de La Viña en Riverside", "2027-01-23", "2027-01-23",
                 source="calendar", city="Riverside", state="CA", location="Riverside, CA"),
         "url": "https://www.aalavina.org/events/zz1", "lang": "es"},
        *[booth_day(d, d < date(2026, 11, 22)) for d in BOOTH_DAYS],
    ]
    for it in out:
        if it["category"] == "manual" and not it["url"]:
            it["url"] = f"/events/#{it['extra']['slug']}"
        it["summary"] = f"{it['title']}: a test event."
        it["first_seen"] = "2026-11-20T12:00:00Z"
    out[1]["summary"] = f"Join us on Zoom: meeting ID {ZOOM_ID}. Bring a pen."
    cancelled = [{**event(f"ev:manual:{OFF}", "manual", "ZZ Cancelled Workshop", at(date(2026, 12, 5), "13:00"),
                          at(date(2026, 12, 5), "15:00"), slug=OFF, cancelled=True, **FW), "url": f"/events/#{OFF}"}]
    return out, cancelled


def whatsnew(evs: list[dict]) -> list[dict]:
    """What's New: the three newest events, as build_data writes them (the online one's summary gives its meeting ID)."""
    return [{**it, "wn_date": "2026-11-20T12:00:00Z"} for it in evs if it["id"] in (f"ev:manual:{LEAF}", f"ev:manual:{TBA}",
                                                                                     f"ev:manual:{ONLINE}")]


BUILD_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r37-links-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", { site: (data) => ({ ...data.site, recurring_events: input.recurring }) });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""

HREF = re.compile(r'href="([^"]*)"')
# an address on the site in a text (unescaped; a JSON string's "\n" or "/" ends it too)
ABS = re.compile(re.escape(BASE) + r"(/[^\s\"'<>)\]\\]*)")
# the structured data's node ids ("…/events/#webpage"): names, not links
LD_ID = re.compile(r'"@id"\s*:\s*"[^"]*"')
EVENT_PATH = re.compile(r"^(?:/es)?/events/")
SERIES_PATH = re.compile(r"^(?:/es)?/events/series/")


def unfold(ics: str) -> str:
    return ics.replace("\r\n ", "").replace("\r\n", "\n")


def vevents(ics: str) -> list[dict[str, str]]:
    out = []
    for block in re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", unfold(ics), re.S):
        ev = {}
        for line in block.split("\n"):
            k, _, v = line.partition(":")
            ev.setdefault(k.split(";")[0], v)
        out.append(ev)
    return out


def ics_text(v: str) -> str:
    return v.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def card_of(page: str, anchor: str) -> str:
    """An /events/ card (its <li id="anchor">, through its </article>)."""
    card = page[page.index(f'<li id="{anchor}"'):]
    return card[:card.index("</article>")]


def h3_link(page: str, anchor: str) -> str:
    """The address an /events/ card's title links to."""
    m = re.search(r'<h3 class="h-card[^"]*"><a href="([^"]*)"', card_of(page, anchor))
    assert m, f"{anchor}: its title links nowhere"
    return html.unescape(m.group(1))


class Built:
    """One build for the whole module (TheLinks and LlmsTxt read the same pages)."""
    pages: dict | None = None
    tmp: Path | None = None

    @classmethod
    def get(cls, case: unittest.TestCase) -> dict:
        if cls.pages is None:
            cls.tmp = Path(tempfile.mkdtemp(prefix="gv-r37-links-data-"))
            (cls.tmp / "events").mkdir()
            evs, off = items()
            (cls.tmp / "events.json").write_text(json.dumps({"updated": NOW, "items": evs, "cancelled": off}), encoding="utf-8")
            (cls.tmp / "whatsnew.json").write_text(json.dumps({"updated": NOW, "items": whatsnew(evs)}), encoding="utf-8")
            try:
                cls.pages = run_js(case, BUILD_JS, data={"only": ONLY, "recurring": RECURRING}, timeout=900, now=NOW,
                                   env={"SITE_DATA": str(cls.tmp), "CONTENT_EVENTS": str(cls.tmp / "events"),
                                        "SITE_URL": BASE, "STRICT_BUILD": "", "LASTMOD": ""})
            finally:
                shutil.rmtree(cls.tmp, True)
        return cls.pages


def links_to_events(pages: dict) -> dict[str, set[str]]:
    """Every link to an event page in the build → the pages it is in: the hrefs of the HTML pages and every address
    on the site in any file (a text to copy, a calendar entry, a feed item, /llms.txt), without its ?query."""
    found: dict[str, set[str]] = {}
    for url, content in pages.items():
        targets = [html.unescape(h) for h in HREF.findall(content)] if url.endswith("/") else []
        text = LD_ID.sub("", html.unescape(content.replace("\r\n ", "")))        # (a calendar file's lines unfolded)
        targets += ABS.findall(text)
        for t in targets:
            if not t.startswith("/") or t.startswith("//"):
                continue
            path, _, frag = t.partition("#")
            path = path.split("?")[0]
            if EVENT_PATH.match(path):
                found.setdefault(path + ("#" + frag if frag else ""), set()).add(url)
    return found


class TheLinks(unittest.TestCase):
    def pages(self) -> dict:
        return Built.get(self)

    def test_every_event_link_resolves(self):
        p = self.pages()
        found = links_to_events(p)
        self.assertGreater(len(found), 20)
        broken = []
        for link, where in sorted(found.items()):
            path, _, frag = link.partition("#")
            if SERIES_PATH.match(path):
                continue                                    # (test_every_series_link_resolves)
            if path not in p:
                broken.append(f"{link} (in {', '.join(sorted(where)[:3])})")
            elif frag and f'id="{frag}"' not in p[path]:
                broken.append(f"{link}: no id {frag!r} there (in {', '.join(sorted(where)[:3])})")
        self.assertEqual(broken, [])
        # the event pages themselves are among the links (one-offs, a date of the series, one that is over)
        for path in (f"/events/{LEAF}/", f"/es/events/{LEAF}/", f"/events/ev-recurring-{BOOTH}-2026-12-12/",
                     f"/events/{OLD}/", f"/events/{CAL}/", f"/events/{ACM}/"):
            self.assertIn(path, found)

    def test_every_series_link_resolves(self):
        p = self.pages()
        hubs = {link: where for link, where in links_to_events(p).items() if SERIES_PATH.match(link)}
        self.assertIn(HUB, hubs, "the series' dates link to its page")
        self.assertIn("/es" + HUB, hubs)
        if not any(SERIES_PATH.match(u) for u in p):
            self.skipTest("PENDING round 37 unit U2: this build writes no series' page (/events/series/<key>/) yet — "
                          f"{len(hubs)} links to one wait for it")
        self.assertEqual(sorted(link for link in hubs if link.partition("#")[0] not in p), [])

    def test_each_place_links_the_events_page(self):
        p = self.pages()
        for pre in ("", "/es"):
            with self.subTest(lang=pre or "/"):
                ev = p[f"{pre}/events/"]
                # /events/: every card's title its page — a series' date its series' page, the committee meeting its
                # section of /meetings/; an event with a page elsewhere: its page, that page the "Event details" button
                self.assertEqual(h3_link(ev, LEAF), f"{pre}/events/{LEAF}/")
                self.assertEqual(h3_link(ev, TBA), f"{pre}/events/{TBA}/")
                self.assertEqual(h3_link(ev, ONLINE), f"{pre}/events/{ONLINE}/")
                self.assertEqual(h3_link(ev, CAL), f"{pre}/events/{CAL}/")
                self.assertEqual(h3_link(ev, ACM), f"{pre}/events/{ACM}/")
                # (its outside page: "Organizer's page ↗" — .ev-org-btn, round 38b: on a phone at larger text its icon
                # steps aside, areas/access.css)
                self.assertIn('<a class="btn-secondary btn-sm ev-org-btn" href="https://neta65.org/event/zz-acm/"', card_of(ev, ACM))
                # a monthly series: ONE card, its title its series' page; each date to come an entry of it (its anchor),
                # a link to the date's own page
                self.assertEqual(h3_link(ev, f"ev-series-{BOOTH}"), pre + HUB)
                series = card_of(ev, f"ev-series-{BOOTH}")
                for d in BOOTH_DAYS[2:]:
                    anchor = f"ev-recurring-{BOOTH}-{d.isoformat()}"
                    self.assertRegex(series, f'<li id="{anchor}"[^>]*><a class="ev-series-date" href="{pre}/events/{anchor}/"')
                # the committee meeting: its dates' anchors on its card, whose details go to its section of /meetings/
                pinned = ev[ev.index('<section id="ev-pinned"'):]
                pinned = pinned[:pinned.index('<article class="cm-pinned')]
                pinned_card = ev[ev.index('<article class="cm-pinned'):]
                self.assertRegex(pinned, r'<span id="ev-committee-[0-9-]+"></span>')
                self.assertIn(f'href="{pre}/meetings/#committee-meeting"', pinned_card[:pinned_card.index("</article>")])
                # "Save the date": the event's page, never a #card
                aside = ev[ev.index('aria-labelledby="ev-aside-title"'):]
                aside = aside[:aside.index("</section>")]
                self.assertRegex(aside, r'href="' + pre + r'/events/[a-z0-9-]+/"')
                # Home, Contribute's workshops, the Bulletin's and Photos' next events
                self.assertIn(f'href="{pre}/events/{LEAF}/"', p[f"{pre}/"])
                self.assertIn(f'href="{pre}/events/{LEAF}/"', p[f"{pre}/contribute/"])
                self.assertIn(f'href="{pre}/events/{TBA}/"', p[f"{pre}/contribute/"])
                self.assertIn(f'href="{pre}/events/{LEAF}/"', p[f"{pre}/bulletin/"])
                self.assertIn(f'href="{pre}/events/{LEAF}/"', p[f"{pre}/photos/"])
                self.assertIn(f'href="{pre}{HUB}"', p[f"{pre}/photos/"])
                # the month's dates: the event's page, the series' date its series' page
                month = p[f"{pre}/monthly/2026-12/"]
                self.assertIn(f'href="{pre}/events/{LEAF}/"', month)
                self.assertIn(f'href="{pre}{HUB}"', month)
                self.assertNotIn('href="https://example.org/zz-booth"', month, "the series' outside page is its page's to give")
                # What's New and the RSS feed
                self.assertIn(f'href="{pre}/events/{LEAF}/"', p[f"{pre}/whats-new/"])
                feed = p[f"{pre}/feed.xml"]
                self.assertIn(f"<link>{BASE}{pre}/events/{LEAF}/</link>", feed)
                self.assertNotIn(f"/events/#{LEAF}", feed)
                # (round 37's fixer) a copy made for machines: never how to join — the summary without that sentence
                self.assertIn(f"<link>{BASE}{pre}/events/{ONLINE}/</link>", feed)
                for code in (ZOOM_ID, ZOOM_ID.replace(" ", ""), "zoom.us"):
                    self.assertNotIn(code, feed)
                if not pre:
                    self.assertIn("Bring a pen.", feed)
                # the digest (October's: the events that took place — the one-off's page, the series' page) and its texts
                digest = p[f"{pre}/digest/"]
                self.assertIn(f'href="{pre}/events/{OLD}/"', digest)
                self.assertIn(f'href="{pre}{HUB}"', digest)
                self.assertIn(f"{BASE}{pre}/events/{OLD}/", re.sub(r'href="[^"]*"', "", digest), "the texts to copy")
                # the district report (the month's hub, /monthly/): each upcoming event with its page's address
                report = html.unescape(re.search(r'<pre class="rp-nojs-text"[^>]*>(.*?)</pre>', p[f"{pre}/monthly/"], re.S).group(1))
                self.assertIn(f"{BASE}{pre}/events/{LEAF}/", report)
                self.assertIn(f"{BASE}{pre}{HUB}", report)
                self.assertNotIn("#" + LEAF, report)

    def test_the_calendar_entries_link_the_events_page(self):
        p = self.pages()
        for pre, tail in (("", "@neta65-gvlv"), ("/es", "-es@neta65-gvlv")):
            entries = {e["UID"][:-len(tail)]: e for e in vevents(p[f"{pre}/events.ics"]) if e.get("UID", "").endswith(tail)}
            want = {f"ev-manual-{LEAF}": f"/events/{LEAF}/", f"ev-manual-{ONLINE}": f"/events/{ONLINE}/",
                    f"ev-manual-{TBA}": f"/events/{TBA}/", f"ev-manual-{ACM}": f"/events/{ACM}/",
                    f"ev-manual-{OLD}": f"/events/{OLD}/", f"ev-lvcal-zz1": f"/events/{CAL}/",
                    f"ev-manual-{OFF}": f"/events/{OFF}/",
                    **{f"ev-recurring-{BOOTH}-{d.isoformat()}": f"/events/ev-recurring-{BOOTH}-{d.isoformat()}/"
                       for d in BOOTH_DAYS}}
            with self.subTest(lang=pre or "/"):
                self.assertEqual({k: entries[k]["URL"] for k in want if k in entries},
                                 {k: f"{BASE}{pre}{v}" for k, v in want.items()})
                for k, path in want.items():
                    # (its last line: "Details: <address>" — "Time not listed — see event details: …" for a day only)
                    last = ics_text(entries[k]["DESCRIPTION"]).split("\n")[-1]
                    self.assertEqual(last.rsplit(": ", 1)[1], f"{BASE}{pre}{path}", k)
                # a day only, from the magazines' calendar: the line that says the time was not listed points to the
                # organizer's page (which gives it — its page here does not), then "Details:" its page here
                cal = ics_text(entries["ev-lvcal-zz1"]["DESCRIPTION"]).split("\n")
                when, details = (("Time not listed — see event details", "Details") if not pre
                                 else ("Hora no indicada — ver detalles del evento", "Detalles"))
                self.assertEqual(cal[-2:], [f"{when}: https://www.aalavina.org/events/zz1",
                                            f"{details}: {BASE}{pre}/events/{CAL}/"])
                # a committee meeting: its section of /meetings/, as before
                meetings = [e for k, e in entries.items() if k.startswith("ev-committee-")]
                self.assertTrue(meetings)
                self.assertEqual({e["URL"] for e in meetings}, {f"{BASE}{pre}/meetings/#committee-meeting"})
                # every card's .ics file and calendar links (data-cm-ics): the same address
                ev = p[f"{pre}/events/"]
                ics = json.loads(html.unescape(re.search(r'data-cm-ics="([^"]*)"', card_of(ev, ACM)).group(1)))
                self.assertEqual(ics["url"], f"{BASE}{pre}/events/{ACM}/")
        # the month's calendar file too
        month = {e["UID"]: e["URL"] for e in vevents(p["/monthly/2026-12/neta65-grapevine-2026-12-en.ics"])}
        self.assertEqual(month[f"ev-manual-{LEAF}@neta65-gvlv"], f"{BASE}/events/{LEAF}/")
        self.assertEqual(month[f"ev-recurring-{BOOTH}-2026-12-12@neta65-gvlv"], f"{BASE}/events/ev-recurring-{BOOTH}-2026-12-12/")
        # a later month's date, worked out from the series' rule (events.json does not list it: no page): its series'
        # page
        later = {e["UID"]: e for e in vevents(p["/monthly/2027-03/neta65-grapevine-2027-03-en.ics"])}
        entry = later[f"ev-recurring-{BOOTH}-2027-03-13@neta65-gvlv"]
        self.assertEqual(entry["URL"], f"{BASE}{HUB}")
        self.assertEqual(ics_text(entry["DESCRIPTION"]).split("\n")[-1], f"Details: {BASE}{HUB}")

    def test_a_series_whose_page_is_ours_keeps_it(self):
        """A date of a series whose `url:` is one of our pages (the Grapevine Meeting's "/meetings/#grapevine-meeting")
        keeps that link in its calendar entry: its countdowns hand one date's link to every date they roll on to."""
        r = run_js(self, SERIES_HOME_JS, data={"items": [
            {**booth_day(date(2027, 1, 9), False), "id": "ev:recurring:zz-gvm:2027-01-06", "url": "/meetings/#grapevine-meeting"},
            booth_day(date(2027, 1, 9), False)]}, now=NOW, env={"SITE_URL": BASE})
        for lang, pre in (("en", ""), ("es", "/es")):
            with self.subTest(lang=lang):
                self.assertEqual(r[lang], {"ev:recurring:zz-gvm:2027-01-06": f"{BASE}{pre}/meetings/#grapevine-meeting",
                                           f"ev:recurring:{BOOTH}:2027-01-09": f"{BASE}{pre}/events/ev-recurring-{BOOTH}-2027-01-09/"})


SERIES_HOME_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const site = { url: "https://x.test", meeting: {} };
out(Object.fromEntries(["en", "es"].map((lang) => [lang, Object.fromEntries(C.normalizeEvents(input.items, site, lang)
  .filter((e) => !e.committee).map((e) => [e.id, e.detailsUrl]))])));
"""


# ============================================================================ the 404 page
NOT_FOUND_JS = r"""
import vm from "node:vm";
const run = (pathname, search = "") => {
  const replaced = [], box = { value: "" }, nf = { getAttribute: () => null };
  const document = {
    readyState: "complete", addEventListener() {},
    querySelector: (s) => (s === "[data-nf]" ? nf : null),
    querySelectorAll: (s) => (s === "[data-nf-query]" ? [box] : []),
  };
  const ctx = { console, document, GV: {}, SITE: { lang: "en", base: "/aagrapevine/", tz: "America/Chicago" },
                location: { pathname, search, hash: "", replace: (u) => replaced.push(u) } };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/community.js", "utf8"), ctx, { filename: "community.js" });
  return replaced;
};
out(Object.fromEntries(input.map(([name, p, q]) => [name, run(p, q)])));
"""


class TheForwarder(unittest.TestCase):
    def test_gone_addresses(self):
        cases = {
            # a series' page that is gone (no date to come): the Events page
            "hub": ("/aagrapevine/events/series/citywide-dallas/", "", ["/aagrapevine/events/"]),
            "hubEs": ("/aagrapevine/es/events/series/lv-monthly-workshop", "?utm_source=x", ["/aagrapevine/es/events/?utm_source=x"]),
            "series": ("/aagrapevine/events/series/", "", ["/aagrapevine/events/"]),
            # a date of a series, long over: its series' page (the ?query kept)
            "date": ("/aagrapevine/events/ev-recurring-citywide-dallas-2026-07-11/", "",
                     ["/aagrapevine/events/series/citywide-dallas/"]),
            "dateEs": ("/aagrapevine/es/events/ev-recurring-lv-monthly-workshop-2026-10-22", "?utm_source=x",
                       ["/aagrapevine/es/events/series/lv-monthly-workshop/?utm_source=x"]),
            # any other event: its card on the Events page, as before
            "oneOff": ("/aagrapevine/events/2026-10-07-lv-writing-workshop-mansfield/", "?utm_source=x",
                       ["/aagrapevine/events/?utm_source=x#2026-10-07-lv-writing-workshop-mansfield"]),
            "flyer": ("/aagrapevine/es/events/ev-flyer-1abc/", "", ["/aagrapevine/es/events/#ev-flyer-1abc"]),
            # (not a series' date: the words are not "ev-recurring-…-<a day>")
            "notADate": ("/aagrapevine/events/ev-recurring-booth/", "", ["/aagrapevine/events/#ev-recurring-booth"]),
            # deeper addresses: the 404 page and its search box
            "deeper": ("/aagrapevine/events/series/citywide-dallas/2026/", "", []),
            "other": ("/aagrapevine/events/2026/old-page/", "", []),
        }
        r = run_js(self, NOT_FOUND_JS, data=[[k, v[0], v[1]] for k, v in cases.items()], needs_modules=False)
        self.assertEqual(r, {k: v[2] for k, v in cases.items()})


# ============================================================================ /llms.txt
LINE = re.compile(r"^- \[([^\]]+)\]\(([^)\s]+)\): (.+)$")


class LlmsTxt(unittest.TestCase):
    def section(self, text: str, name: str) -> list[str]:
        lines = text.split("\n")
        h2 = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
        start = lines.index(f"## {name}")
        end = next(i for i in h2 if i > start)
        self.assertEqual(lines[end], "## Optional" if name == "Upcoming events" else "## Opcional", "just before Optional")
        self.assertEqual((lines[start + 1], lines[end - 1]), ("", ""))
        return lines[start + 2:end - 1]

    def test_the_upcoming_events(self):
        p = Built.get(self)
        sitemap = p["/sitemap.xml"]
        for pre, name in (("", "Upcoming events"), ("/es", "Próximos eventos")):
            text = p[f"{pre}/llms.txt"]
            lines = self.section(text, name)
            with self.subTest(lang=pre or "/"):
                got = []
                for ln in lines:
                    m = LINE.match(ln)
                    self.assertTrue(m, ln)
                    title, url, desc = m.groups()
                    self.assertTrue(url.startswith(BASE + "/"), url)
                    path = url[len(BASE):]
                    got.append(path)
                    page = p[path]
                    self.assertIn(f"<loc>{url}</loc>", sitemap, "a page search engines may list")
                    self.assertNotIn('content="noindex"', page)
                    # (its words — in one line, every space a plain one: llms-txt.11ty.js oneLine; the committee
                    # meeting's dates page writes "7:00 – 8:00 PM" with thin spaces)
                    self.assertEqual(desc, " ".join(html.unescape(re.search(r'<meta name="description" content="([^"]*)"', page).group(1)).split()))
                    self.assertEqual(title, html.unescape(re.search(r"<title>(.*?)</title>", page).group(1)).split(" · ")[0])
                # the series' pages first — (round 38b) the committee meeting's dates page, then the test's series (once
                # U2 writes it) —, then the one-off events to come, soonest first — each whose page this build lets
                # search engines list
                order = [f"{pre}/events/series/committee-meeting/", pre + HUB] + [f"{pre}/events/{a}/" for a in (LEAF, ONLINE, TBA, ACM)]
                self.assertEqual(got, [u for u in order if f"<loc>{BASE}{u}</loc>" in sitemap])
                # (round 38b) the committee meeting's dates page is there (the build writes it: the settings' meeting
                # has dates to come) — it was missing, the only series' page left out
                self.assertIn(f"{pre}/events/series/committee-meeting/", got)
                # (round 37's fixer) a series' line gives its next date, the day its page's lede names — never the
                # rule alone, from which a reader works out a date that does not happen (a month it skips)
                hub_desc = LINE.match(lines[got.index(pre + HUB)]).group(3)
                word = "Next: " if not pre else "Próxima fecha: "
                m = re.search(re.escape(word) + r"([^.]+)\.", hub_desc)
                self.assertTrue(m, hub_desc)
                lede = html.unescape(re.sub(r"<[^>]+>", "", p[pre + HUB]))
                self.assertIn(word + m.group(1), lede, "the date its page's lede gives")
                self.assertIn(f"{pre}/events/{LEAF}/", got)
                # never a series' date, an event that is over, the magazines' own, a cancelled one, a committee meeting
                for gone in (f"ev-recurring-{BOOTH}-", OLD, CAL, OFF, "ev-committee-", "/meetings/"):
                    self.assertNotIn(gone, "\n".join(lines))
                # never how to join
                for code in (ZOOM_ID, ZOOM_ID.replace(" ", ""), "zoom.us", "meet.google.com"):
                    self.assertNotIn(code, text)
                # (test_r35_head's check of the rest of the file — the gate judges these lines here, on made-up events:
                # there, they are the day's events)
                hit = JOIN.search("\n".join(lines))
                self.assertIsNone(hit, hit and hit.group(0))

    def test_at_most_20_lines_and_14_kb(self):
        r = run_js(self, RENDER_JS, data={"short": 25, "long": 25}, now=NOW, env={"SITE_URL": BASE})
        for case, want_all in (("short", True), ("long", False)):
            text, events = r[case]["text"], r[case]["events"]
            lines = self.section(text, "Upcoming events")
            with self.subTest(case=case):
                self.assertTrue(all(LINE.match(ln) for ln in lines))
                self.assertLessEqual(len(text.encode("utf-8")), 14 * 1024)
                # the first ones, soonest first: 20 of them — or as many as 14 KB hold
                self.assertEqual([LINE.match(ln).group(2) for ln in lines], [BASE + e for e in events[:len(lines)]])
                if want_all:
                    self.assertEqual(len(lines), 20)
                else:
                    self.assertTrue(0 < len(lines) < 20, len(lines))
                    # (the next line, as long as the last one, would not have fitted: it stopped only when full)
                    nxt = len(lines[-1].encode("utf-8")) + 1
                    self.assertGreater(len(text.encode("utf-8")) + nxt, 14 * 1024)


# The guide's render() on many events still to come: 25 with short titles, 25 with long ones (each line ~ 900 bytes)
RENDER_JS = r"""
const T = await imp("src/pages/llms-txt.11ty.js");
const site = (await imp("src/_data/site.js")).default();
const nav = (await imp("src/_data/nav.js")).default;
const res = {};
for (const [name, n] of Object.entries(input)) {
  const items = [];
  for (let i = 0; i < n; i++) {
    const day = String(i + 1).padStart(2, "0");
    const slug = `2099-03-${day}-zz-${name}-${i}`;
    const words = name === "long" ? " — Taller de escritura de La Viña, en español: ñandú, café, canción, corazón".repeat(8) : "";
    items.push({ id: `ev:manual:${slug}`, source: "committee", kind: "event", category: "manual", url: `/events/#${slug}`,
      title: `Workshop ${i + 1}${words}`, summary: `A workshop.${words}`, lang: "en", date: `2099-03-${day}T19:00:00Z`,
      status: "ok", tags: ["workshop"], is_new: false, machine: [],
      extra: { start: `2099-03-${day}T19:00:00Z`, end: `2099-03-${day}T21:00:00Z`, all_day: false, slug,
        location: "Grupo Uno, 100 Main St, Tyler, TX 75702", city: "Tyler", state: "TX" } });
  }
  const paths = items.map((it) => `/events/${it.extra.slug}/`);
  const data = { site, lang: "en", nav, languages: ["en", "es"],
    db: { events: { items, cancelled: [] } },
    collections: { all: [{ url: paths[0], data: { pagination: { hrefs: [...paths, ...paths.map((p) => "/es" + p)] } } }] } };
  const ctx = { t: filters.t, siteUrl: filters.siteUrl, lurl: filters.lurl };
  res[name] = { text: T.render.call(ctx, data), events: paths };
}
out(res);
"""


if __name__ == "__main__":
    unittest.main()
