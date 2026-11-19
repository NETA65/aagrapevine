"""Structured data on /events/ and /es/events/: what search engines are told about the events — eventLd and
eventPlace in eleventy/filters/committee.js (the `cmEventLd` filter), written by src/pages/events.njk as the page's
first <script type="application/ld+json"> in its <body> (since round 35 the site-wide graph comes before it, in <head>).

  * Only events held at a place: Google lists only events at a physical place with a postal address that the public
    may attend (its Event rules, 2026-09-08). An online-only event — the committee meeting's monthly dates, La
    Viña's workshop on Zoom, an event with only an online link — gets no Event, nor does a place "to be announced";
    a hybrid one is "Mixed", at its Place; a monthly series gives its next date only.
  * The place → a schema.org Place with a PostalAddress: "<venue>, <street>, <city>, <ST> <zip>", the data's own
    city and state first, a country at the end, a place written without commas (La Viña's calendar: "… center
    LONGVIEW TX 75604"), a text that cannot be split (the street address as a whole) — and every place in
    data/site/events.json, whatever it holds: nothing made up (every part comes from the text, or is the data's
    own city), never an empty value.
  * Honest facts: the organizer is La Viña / Grapevine for their own events we share, nobody for an event from their
    calendars, since round 35 the committee or group a content/events file names (`organizer:`, with its https
    `organizer_url:` — a district's La Viña workshop; never the words the calendars' pages give), the Area for its
    own events (an assembly; since round 30 its committee meeting, the ACM, too — event-tone.js gives them one kind),
    else the committee — by the site's "#committee" @id;
    isAccessibleForFree only for the committee's own events; inLanguage "es" only for an event held in Spanish.
    description = the summary as one plain line (≤ 300 characters; none for the calendars' events: their words),
    image = the flyer (else the committee's card in the page's language), sameAs = the event's own page on another
    site (never a Drive / Docs flyer, a site's home page or our own site). No performer, no person, no other keys.
  * Times (since round 35): a timed event's startDate / endDate in Central wall time with its offset
    ("2026-10-24T14:00:00-05:00" in daylight time, "…-06:00" in standard time — localIso, right on the nights the
    clocks change), never a UTC time whose date is the next day's for an evening event; an all-day event its days.
  * url (since round 35): the event's own page when it has one (committee.js eventLeaf: "/events/<anchor>/" — still
    to come, held at a place in both languages, not a monthly series' date, not from the magazines' calendars, no
    page of its own elsewhere), else its card (pageAbs#anchor); an event's own page gives its own address (opt.url,
    the cmEventPageLd filter: its one Event, with its @context).
  * The page: its first ld+json block is exactly what the filter gives for its events (both languages), at the start
    of the page (since round 35: before the hero, far ahead of Googlebot's 2 MB).

Runs the JavaScript with Node.js (tests/nodejs.py); skipped without Node.js / the npm packages.

    python -m unittest tests.test_seo_events -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

CHI = ZoneInfo("America/Chicago")
NOW = "2026-10-06T15:00:00Z"                     # Tue Oct 6, 2026, 10 AM CDT: the events below are still to come
SITE = {
    "url": "https://example.org/site",
    "committee": "Test Committee", "committee_es": "Comité de prueba",
    "area": "Test Area 65", "area_es": "Área de prueba 65", "area_website": "https://area.example.org",
    "meeting": {"weekday": "wednesday", "week_of_month": 3, "start": "19:00", "end": "20:00", "platform": "Zoom",
                "zoom_url": "https://zoom.us/j/111"},
    "links": {"lv_home": "https://lv.example.org", "gv_home": "https://gv.example.org"},
}
ROOT_URL = SITE["url"] + "/"
DRIVE_ID = "1AbCdEfGhIjKlMnOpQ"
LONG = ("<p>An <b>afternoon</b> workshop&nbsp;on writing &amp; recording your story.</p>\n"
        + " ".join(["Bring a notebook and a friend."] * 15))
EVENT_KEYS = {"@type", "name", "description", "startDate", "endDate", "eventStatus", "eventAttendanceMode", "location",
              "image", "organizer", "isAccessibleForFree", "inLanguage", "sameAs", "url"}
MODE = "https://schema.org/{}EventAttendanceMode".format


def item(slug: str, title: str, start: str, end: str, *, category: str = "manual", source: str = "committee",
         url: str = "", summary: str = "", tags: list[str] | None = None, lang: str = "en", **extra) -> dict:
    """An event as data/site/events.json holds it (build_data); a content/events file's (category manual) has its
    file name as its slug — its card's anchor."""
    all_day = len(start) == 10
    own = {"slug": slug} if category == "manual" else {}
    return {"id": f"ev:{category}:{slug}", "source": source, "kind": "event", "category": category, "url": url,
            "title": title, "summary": summary, "lang": lang, "date": start, "status": "ok", "tags": tags or [],
            "extra": {"start": start, "end": end, "all_day": all_day, **own, "location": None,
                      "online_url": None, "city": None, "state": None, **extra}}


ITEMS = [
    # a La Viña workshop the committee holds: its flyer on the Drive, its page on neta65.org, a long summary in HTML
    item("zz-workshop", "La Viña Writing Workshop (in Spanish) — Tyler", "2026-10-24T19:00:00Z", "2026-10-24T21:00:00Z",
         url="https://neta65.org/event/zz-workshop/", summary=LONG, tags=["workshop", "la-vina"],
         location="Grupo Uno, 100 Main St, Tyler, TX 75702", city="Tyler", state="TX",
         flyer_url=f"https://drive.google.com/file/d/{DRIVE_ID}/view", flyer_thumb=None),
    # hybrid: a place AND a Zoom link
    item("zz-hybrid", "Grapevine Hybrid Workshop", "2026-10-25T19:00:00Z", "2026-10-25T21:00:00Z",
         summary="Come in person or join on Zoom.", tags=["workshop", "grapevine"],
         location="Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012", city="Arlington",
         state="TX", online_url="https://us02web.zoom.us/j/123", platform="Zoom"),
    # online only (a content/events file with only a link): no Event
    item("zz-online", "Online Writing Workshop", "2026-10-26T19:00:00Z", "2026-10-26T21:00:00Z",
         online_url="https://meet.google.com/abc-defg-hij", platform="Google Meet"),
    # La Viña's own monthly workshop on Zoom (recurring_events host: lv): online only — no Event
    item("zz-lv-zoom:2026-10-22", "La Viña Monthly Virtual Workshop", "2026-10-22T19:00:00Z", "2026-10-22T20:00:00Z",
         category="recurring", url="/events/", summary="In Spanish, open to all.", tags=["recurring"], host="lv",
         online=True, platform="Zoom", online_url="https://us06web.zoom.us/j/999", series="zz-lv-zoom",
         rule={"week_of_month": 4, "weekday": "thursday", "start": "14:00", "end": "15:00"}),
    # Grapevine's own event that we share, in person (a content/events file's host: gv)
    item("zz-gv-own", "Grapevine Open House", "2026-10-27T19:00:00Z", "2026-10-27T21:00:00Z",
         summary="Grapevine's open house.", location="Hall Uno, 5 Oak Ave, Dallas, TX 75201", city="Dallas",
         state="TX", host="gv"),
    # an Area assembly, all day, Fri–Sun; its link is its own card (no page of its own)
    item("zz-assembly", "Test Area Spring Assembly", "2026-11-20", "2026-11-22", url="/events/#zz-assembly",
         summary="The Area's assembly.", tags=["assembly"],
         location="Hotel Uno, 4099 Valley View Ln, Dallas, TX 75244", city="Dallas", state="TX"),
    # from La Viña's calendar: their words, their page, in Spanish; a place written without commas
    item("zz-lvcal", "XLII REUNIÓN DE A.A. ZONA NORTE", "2027-01-29", "2027-01-31", category="lv-calendar",
         source="calendar", lang="es", summary="Con oradores invitados de toda la zona.",
         url="https://www.aalavina.org/get-involved/events/2027-01-29/zz", tags=["texas"],
         location="Maude Cobb . Convenció center LONGVIEW TX 75604"),
    # from Grapevine's calendar
    item("zz-gvcal", "Grapevine Roundup", "2026-11-07", "2026-11-07", category="gv-calendar", source="calendar",
         summary="A day of sharing.", url="https://www.aagrapevine.org/events/zz-roundup",
         location="Hall Dos, 300 Oak Ave, Austin, TX 78701"),
    # a place not known yet: no Event
    item("zz-tba", "Test Area Summer Assembly", "2027-06-25", "2027-06-27", tags=["assembly"],
         location="Venue to be announced", location_tba=True),
    # the booth, monthly: its next date only; its link is the gathering's home page (not the booth's page)
    *[item(f"zz-booth:{d}", "GV/LV booth at CityWide", f"{d}T22:00:00Z", f"{d}T23:59:00Z", category="recurring",
           url="https://citywide.example.org", summary="Our literature table.", tags=["recurring"], host="neta",
           location="Church Uno, 9200 Inwood Road, Dallas, TX 75220", city="Dallas", state="TX", series="zz-booth",
           rule={"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "18:59"})
      for d in ("2026-10-10", "2026-11-14")],
    # a dated Drive flyer: its link is the flyer itself
    item(DRIVE_ID, "Committee Visit", "2026-10-31T16:00:00Z", "2026-10-31T18:00:00Z", category="flyer",
         source="drive", url=f"https://drive.google.com/file/d/{DRIVE_ID}/view",
         location="Grand Prairie Group, 921 W Pioneer Pkwy, Grand Prairie, TX 75052", city="Grand Prairie", state="TX",
         flyer_url=f"https://drive.google.com/file/d/{DRIVE_ID}/view",
         flyer_thumb=f"https://lh3.googleusercontent.com/d/{DRIVE_ID}=w600"),
    # links that are no page of the event's own: a Google Doc, our own site
    item("zz-doc-link", "Workshop With a Doc", "2026-11-01T19:00:00Z", "2026-11-01T21:00:00Z", summary=LONG,
         url="https://docs.google.com/document/d/1xyz/edit", location="Grupo Tres, 7 Pine St, Tyler, TX 75701"),
    item("zz-own-link", "Workshop With Our Page", "2026-11-02T19:00:00Z", "2026-11-02T21:00:00Z",
         url="https://example.org/site/bulletin/", location="Grupo Cuatro, 8 Pine St, Tyler, TX 75701"),
    # online events from La Viña's calendar (scope online): where to join is no place — no Event, whatever the text
    item("zz-lvcal-zoom", "TALLER VIRTUAL", "2026-11-03T01:00:00Z", "2026-11-03T02:00:00Z", category="lv-calendar",
         source="calendar", lang="es", url="https://www.aalavina.org/get-involved/events/2026-11-02/zoom",
         location="Zoom ID: 815 9593 1777 Código: 1234", platform="Zoom", scope="online"),
    item("zz-lvcal-mx", "REUNIÓN VIRTUAL", "2026-11-04T01:00:00Z", "2026-11-04T02:00:00Z", category="lv-calendar",
         source="calendar", lang="es", url="https://www.aalavina.org/get-involved/events/2026-11-03/mx",
         location="Virtual (Ciudad de México)", country="Mexico", scope="online"),
    # a link to join and a "place" with no address at all: online only — no Event
    item("zz-room", "Workshop in the Virtual Room", "2026-11-05T19:00:00Z", "2026-11-05T21:00:00Z",
         location="Sala virtual", online_url="https://us02web.zoom.us/j/555", platform="Zoom"),
    # in person, but only a venue's name (no city, state or ZIP code): no address — no Event
    item("zz-venue-only", "Workshop at the Hotel", "2026-11-06T19:00:00Z", "2026-11-06T21:00:00Z",
         location="Hilton Tyler"),
    # hybrid, its summary with the meeting ID and passcode: never in the description
    item("zz-hybrid-codes", "Hybrid Sharing Session", "2026-11-07T19:00:00Z", "2026-11-07T21:00:00Z",
         summary="<p>Share your story with us.</p> Come in person or join on Zoom (meeting ID 123 456 7890, "
                 "passcode zz65). Coffee at 1 PM.",
         location="Grupo Seis, 6 Elm St, Tyler, TX 75701", city="Tyler", state="TX",
         online_url="https://us02web.zoom.us/j/1234567890?pwd=abc", platform="Zoom"),
    # the Area Committee Meeting (a content/events file tagged acm): the Area's own event, as an assembly is (round 30)
    item("zz-acm", "Test Winter ACM 2026", "2026-11-08T18:00:00Z", "2026-11-08T22:00:00Z", tags=["neta65", "acm"],
         summary="The Area's committee meeting.", location="Hall Tres, 9 Elm St, Plano, TX 75074", city="Plano", state="TX"),
    # a district's La Viña workshop (round 35): its file names who organizes it (`organizer:`, `organizer_url:`)
    item("zz-district", "La Viña Writing Workshop (in Spanish) — Garland", "2026-11-28T19:00:00-06:00",
         "2026-11-28T21:00:00-06:00", summary="Organized by the District 99 La Viña committee.", tags=["workshop", "la-vina"],
         location="Grupo Cinco, 5 Main St, Garland, TX 75041", city="Garland", state="TX",
         organizer="District 99 La Viña Committee", organizer_url="https://district99.example.org/la-vina/"),
    # …and one whose organizer_url is no https page (announcements.py refuses it; eventLd never says it either)
    item("zz-district-http", "La Viña Recording Workshop — Mesquite", "2026-11-29T19:00:00-06:00",
         "2026-11-29T21:00:00-06:00", summary="A recording workshop.", tags=["workshop", "la-vina"],
         location="Grupo Siete, 7 Main St, Mesquite, TX 75149", city="Mesquite", state="TX",
         organizer="District 98 La Viña Committee", organizer_url="http://district98.example.org/"),
]
# (an outside calendar's page names someone as its organizer — extra.organizer, words read from their page: never said)
next(i for i in ITEMS if i["id"] == "ev:lv-calendar:zz-lvcal")["extra"]["organizer"] = "Comité Organizador Zona Norte"

# The events that have a page of their own (eventLeaf) at NOW: still to come, at a place in both languages, not a
# monthly series' date, not from the magazines' calendars, no page of their own elsewhere (zz-workshop has neta65.org's)
LEAVES = {"zz-hybrid", "zz-gv-own", "zz-assembly", f"ev-flyer-{DRIVE_ID.lower()}", "zz-doc-link", "zz-own-link",
          "zz-hybrid-codes", "zz-acm", "zz-district", "zz-district-http"}


def anchor_of(url: str, page: str) -> str:
    """An Event's url → its card's anchor: "<page>#<anchor>", or its own page "<site>[/es]/events/<anchor>/"."""
    if url.startswith(page + "#"):
        return url[len(page) + 1:]
    m = re.fullmatch(re.escape(page) + r"([a-z0-9][a-z0-9-]*)/", url)
    assert m, f"{url}: neither a card on {page} nor an event's own page"
    return m.group(1)

LD_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const res = {};
for (const lang of ["en", "es"]) {
  const evs = filters.cmCollapseRecurring(filters.cmEvents(input.items, input.site, lang)).filter((e) => !e.past);
  const page = input.site.url + (lang === "es" ? "/es" : "") + "/events/";
  // an event's own page: its one Event (cmEventPageLd), its url that page; and what eventPageMeta gives its layout
  const own = {};
  for (const e of evs) {
    if (!filters.cmEventLeaf(e, input.site)) continue;
    const at = input.site.url + C.eventPagePath(e, lang);
    own[e.anchor] = { at, ld: filters.cmEventPageLd(e, input.site, lang, at), meta: C.eventPageMeta(e, input.site, lang) };
  }
  res[lang] = {
    ld: filters.cmEventLd(evs, input.site, lang, page),
    cards: evs.map((e) => e.anchor),
    leaves: evs.filter((e) => C.eventLeaf(e, input.site)).map((e) => e.anchor),
    own,
    byDefault: C.eventLd(evs, input.site, lang).map((e) => e.url),
    capped: C.eventLd(evs, input.site, lang, "", 2).length,
    // every url one address (opt.url)
    given: [...new Set(C.eventLd(evs, input.site, lang, page, 30, { url: "https://x.test/one/" }).map((e) => e.url))],
  };
}
out(res);
"""

PLACE_JS = r"""
const { eventPlace } = await imp("eleventy/filters/committee.js");
out(input.cases.map(([text, extra]) => eventPlace(text, extra)));
"""

# The real data: every place in data/site/events.json (each language's text), and the Events the page would give at
# the moment the data was written (its own clock), with what the page knows of each event.
REAL_JS = r"""
const { eventPlace } = await imp("eleventy/filters/committee.js");
const site = (await imp("src/_data/site.js")).default();
const data = JSON.parse(fs.readFileSync("data/site/events.json", "utf8"));
const items = (data.items || []).filter((it) => it && it.kind === "event" && it.status !== "gone");
const places = [];
for (const it of items) {
  const x = it.extra || {};
  const texts = new Set([x.location, ...Object.values((it.i18n && it.i18n.location) || {})].filter((t) => typeof t === "string" && t.trim()));
  for (const text of texts) places.push({ id: it.id, text, city: x.city || "", state: x.state || "", place: eventPlace(text, x) });
}
const res = { places, site: { url: site.url, committee: site.committee, committee_es: site.committee_es, area: site.area,
  area_es: site.area_es, area_website: site.area_website, lv_home: site.links.lv_home, gv_home: site.links.gv_home }, langs: {} };
for (const lang of ["en", "es"]) {
  const evs = filters.cmCollapseRecurring(filters.cmEvents(items, site, lang)).filter((e) => !e.past);
  const page = site.url + (lang === "es" ? "/es" : "") + "/events/";
  res.langs[lang] = {
    page,
    ld: filters.cmEventLd(evs, site, lang, page),
    evs: evs.map((e) => ({ anchor: e.anchor, committee: e.committee, later: !!e.later, location: e.location,
      tba: e.locationTba, online: e.isOnline, group: e.group, host: e.host, category: e.category,
      tags: (e.item && e.item.tags) || [], tone: filters.eventTone(e), city: (e.item && e.item.extra && e.item.extra.city) || "",
      scope: (e.item && e.item.extra && e.item.extra.scope) || "",
      leaf: filters.cmEventLeaf(e, site),
      organizer: (e.category === "manual" && e.item && e.item.extra && e.item.extra.organizer) || "",
      organizerUrl: (e.category === "manual" && e.item && e.item.extra && e.item.extra.organizer_url) || "",
      address: e.location ? ((eventPlace(e.location, e.item && e.item.extra) || {}).address || {}) : {} })),
  };
}
out(res);
"""

# src/pages/events.njk as the build renders it (only that page), with these events in place of the synced ones; and
# what the filter gives for the same events — the page's first ld+json block must be exactly that.
PAGE_JS = r"""
process.env.ONLY = "events.njk";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const site = (await imp("src/_data/site.js")).default();
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-seo-events-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { ...(data.db || {}).events, items: input.items } }),
      });
    },
  });
  const pages = (await elev.toJSON()).filter((p) => /\/events\/$/.test(p.url));
  const res = {};
  for (const p of pages) {
    const lang = p.url.includes("/es/") ? "es" : "en";
    const evs = filters.cmCollapseRecurring(filters.cmEvents(input.items, site, lang)).filter((e) => !e.past);
    res[lang] = { html: p.content, want: filters.cmEventLd(evs, site, lang, site.url + p.url), site: site.url };
  }
  out(res);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def norm_text(t: str) -> str:
    """A place as the filter reads it: single spaces, ", " between its parts."""
    return ", ".join(p.strip() for p in re.sub(r"\s+", " ", t).split(",") if p.strip())


class EventsOnly(unittest.TestCase):
    """Which events get an Event, and every fact each one states (fixed events, a fixed clock)."""

    res: dict = {}

    @classmethod
    def setUpClass(cls):
        cls.res = {}

    def ld(self, lang: str) -> dict[str, dict]:
        if not EventsOnly.res:
            EventsOnly.res = run_js(self, LD_JS, data={"items": ITEMS, "site": SITE}, now=NOW)
        page = SITE["url"] + ("/es" if lang == "es" else "") + "/events/"
        return {anchor_of(e["url"], page): e for e in EventsOnly.res[lang]["ld"]}

    def test_only_events_held_at_a_place(self):
        for lang in ("en", "es"):
            by = self.ld(lang)
            cards = EventsOnly.res[lang]["cards"]
            with self.subTest(lang=lang):
                # every one of these is on the page (a card) …
                self.assertTrue({"zz-online", "ev-recurring-zz-lv-zoom-2026-10-22", "zz-tba", "zz-room", "zz-venue-only"}
                                <= set(cards), cards)
                self.assertTrue([a for a in cards if a.startswith("ev-committee-")], cards)
                # … but only those held at a place are Events: in the order of the page, the booth by its next date
                self.assertEqual(list(by), [
                    "ev-recurring-zz-booth-2026-10-10", "zz-workshop", "zz-hybrid", "zz-gv-own",
                    f"ev-flyer-{DRIVE_ID.lower()}", "zz-doc-link", "zz-own-link", "ev-gv-calendar-zz-gvcal",
                    "zz-hybrid-codes", "zz-acm", "zz-assembly", "zz-district", "zz-district-http",
                    "ev-lv-calendar-zz-lvcal"])
                text = json.dumps(EventsOnly.res[lang]["ld"], ensure_ascii=False)
                for word in ("VirtualLocation", "OnlineEventAttendanceMode", "zoom.us", "meet.google.com", "performer",
                             "Person", "<", "&amp;", "&nbsp;", "Zoom ID", "Virtual (", "Sala virtual", "123 456",
                             "zz65", "Hilton Tyler", "Comité Organizador", "http://district98"):
                    self.assertNotIn(word, text)
                for anchor, e in by.items():
                    self.assertEqual(set(e) - EVENT_KEYS, set(), anchor)                # nothing else said
                    self.assertTrue(all(v not in ("", None, [], {}) for v in e.values()), anchor)
                    self.assertEqual(e["@type"], "Event")
                    self.assertEqual(e["eventStatus"], "https://schema.org/EventScheduled")
                    # its own page (round 35: eventLeaf), else its card on this page
                    page = SITE["url"] + ("/es" if lang == "es" else "") + "/events/"
                    self.assertEqual(e["url"], page + anchor + "/" if anchor in LEAVES else page + "#" + anchor)
                    self.assertEqual(e["location"]["@type"], "Place")
                    self.assertEqual(e["location"]["address"]["@type"], "PostalAddress")
                    self.assertEqual(e["location"]["address"]["addressCountry"], "US")
                    self.assertEqual(e["eventAttendanceMode"], MODE("Mixed" if anchor in ("zz-hybrid", "zz-hybrid-codes") else "Offline"))
                # the page's own address by default, and at most `max` of them; every url one address when given
                self.assertEqual(EventsOnly.res[lang]["byDefault"], [e["url"] for e in EventsOnly.res[lang]["ld"]])
                self.assertEqual(EventsOnly.res[lang]["capped"], 2)
                self.assertEqual(EventsOnly.res[lang]["given"], ["https://x.test/one/"])

    def test_local_times_with_their_offset(self):
        """Since round 35: the Central wall time the cards show, with its offset — never a UTC time ("…T01:00:00.000Z"
        of the next day for an evening event); the same instant (the calendar files keep their UTC times)."""
        for lang in ("en", "es"):
            by = self.ld(lang)
            with self.subTest(lang=lang):
                # daylight time (CDT, -05:00): Sat Oct 24, 2026, 2–4 PM
                self.assertEqual((by["zz-workshop"]["startDate"], by["zz-workshop"]["endDate"]),
                                 ("2026-10-24T14:00:00-05:00", "2026-10-24T16:00:00-05:00"))
                # standard time (CST, -06:00) once the clocks went back on Nov 1: Sat Nov 7, 1–3 PM; an evening event
                # keeps its own day (Nov 28, 7 PM — 01:00 of Nov 29 in UTC)
                self.assertEqual((by["zz-hybrid-codes"]["startDate"], by["zz-hybrid-codes"]["endDate"]),
                                 ("2026-11-07T13:00:00-06:00", "2026-11-07T15:00:00-06:00"))
                self.assertEqual((by["zz-district"]["startDate"], by["zz-district"]["endDate"]),
                                 ("2026-11-28T19:00:00-06:00", "2026-11-28T21:00:00-06:00"))
                # an all-day event: its days
                self.assertEqual((by["zz-assembly"]["startDate"], by["zz-assembly"]["endDate"]), ("2026-11-20", "2026-11-22"))
                for e in by.values():
                    for k in ("startDate", "endDate"):
                        self.assertRegex(e[k], r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}-0[56]:00)?$", e)
        self.assertEqual(self.ld("en")["zz-workshop"]["name"], "La Viña Writing Workshop (in Spanish) — Tyler")

    def test_the_place_has_a_postal_address(self):
        by = self.ld("es")
        self.assertEqual(by["zz-workshop"]["location"], {
            "@type": "Place", "name": "Grupo Uno",
            "address": {"@type": "PostalAddress", "streetAddress": "100 Main St", "addressLocality": "Tyler",
                        "addressRegion": "TX", "postalCode": "75702", "addressCountry": "US"}})
        # hybrid: its place only (Mixed)
        self.assertEqual(by["zz-hybrid"]["location"]["name"], "Primary Purpose Group – Arlington")
        self.assertEqual(by["zz-hybrid"]["location"]["address"]["streetAddress"], "1802 West Division Street")
        # La Viña's calendar, no commas: ZIP code, state and the city written in capitals, from its end
        self.assertEqual(by["ev-lv-calendar-zz-lvcal"]["location"], {
            "@type": "Place", "name": "Maude Cobb . Convenció center",
            "address": {"@type": "PostalAddress", "addressLocality": "Longview", "addressRegion": "TX",
                        "postalCode": "75604", "addressCountry": "US"}})

    def test_who_holds_it(self):
        for lang, area in (("en", "Test Area 65"), ("es", "Área de prueba 65")):
            by = self.ld(lang)
            # one @id, one name: the site's Organization (base.njk) names the committee in English on every page
            ours = {"@type": "Organization", "@id": ROOT_URL + "#committee", "name": "Test Committee", "url": ROOT_URL}
            with self.subTest(lang=lang):
                # the committee's own events: the site's Organization (one @id in both languages), free
                for anchor in ("zz-workshop", "zz-hybrid", "ev-recurring-zz-booth-2026-10-10",
                               f"ev-flyer-{DRIVE_ID.lower()}", "zz-doc-link", "zz-own-link"):
                    self.assertEqual(by[anchor]["organizer"], ours, anchor)
                    self.assertIs(by[anchor]["isAccessibleForFree"], True, anchor)
                # Grapevine's own event we share: Grapevine; not ours to say it is free
                self.assertEqual(by["zz-gv-own"]["organizer"],
                                 {"@type": "Organization", "name": "AA Grapevine", "url": "https://gv.example.org"})
                # the Area's own events — its assembly, its committee meeting (ACM: round 30) —: the Area
                for anchor in ("zz-assembly", "zz-acm"):
                    self.assertEqual(by[anchor]["organizer"],
                                     {"@type": "Organization", "name": area, "url": "https://area.example.org"}, anchor)
                # a district's workshop (round 35): the committee its file names (`organizer:`), with its page when that
                # is an https one — the same words in both languages (a name); not ours to say it is free
                self.assertEqual(by["zz-district"]["organizer"], {"@type": "Organization", "name": "District 99 La Viña Committee",
                                                                  "url": "https://district99.example.org/la-vina/"})
                self.assertEqual(by["zz-district-http"]["organizer"],
                                 {"@type": "Organization", "name": "District 98 La Viña Committee"})
                # the GV / LV calendars' events: nobody (leaving it out beats guessing) — not even the organizer their own
                # page names (extra.organizer: their words)
                for anchor in ("zz-gv-own", "zz-assembly", "zz-acm", "zz-district", "zz-district-http",
                               "ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal"):
                    self.assertNotIn("isAccessibleForFree", by[anchor], anchor)
                for anchor in ("ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal"):
                    self.assertNotIn("organizer", by[anchor], anchor)

    def test_the_language_of_the_event(self):
        for lang in ("en", "es"):
            by = self.ld(lang)
            # held in Spanish: a La Viña workshop (tag la-vina), La Viña's calendar; else not said (not the page's)
            self.assertEqual({a: e.get("inLanguage") for a, e in by.items() if "inLanguage" in e},
                             {"zz-workshop": "es", "zz-district": "es", "zz-district-http": "es", "ev-lv-calendar-zz-lvcal": "es"},
                             lang)

    def test_the_events_with_a_page_of_their_own(self):
        """Since round 35 (eventLeaf): an event still to come, held at a place in both languages, not a monthly series'
        date, not from the magazines' calendars, with no page of its own elsewhere — never one online only, a place to
        be announced, a venue's name alone, the booth's dates or the Tyler workshop (neta65.org's page)."""
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.ld(lang)
                r = EventsOnly.res[lang]
                self.assertEqual(set(r["leaves"]), LEAVES)
                self.assertEqual(set(r["own"]), LEAVES)
                for word in ("zz-online", "zz-room", "zz-venue-only", "zz-tba", "zz-workshop", "ev-recurring-zz-booth-2026-10-10",
                             "ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal", "ev-recurring-zz-lv-zoom-2026-10-22"):
                    self.assertNotIn(word, r["leaves"])

    def test_an_events_own_page_tells_its_one_event(self):
        """cmEventPageLd: the page's ONE Event, exactly the Event /events/ gives (its url the same page), with its
        @context — never how to join online."""
        for lang in ("en", "es"):
            by = self.ld(lang)
            for anchor, own in EventsOnly.res[lang]["own"].items():
                with self.subTest(lang=lang, event=anchor):
                    ld = own["ld"]
                    self.assertEqual(ld.pop("@context"), "https://schema.org")
                    self.assertEqual(ld, by[anchor])
                    self.assertEqual(ld["url"], own["at"])
                    self.assertEqual(own["at"], SITE["url"] + ("/es" if lang == "es" else "") + f"/events/{anchor}/")
            text = json.dumps([o["ld"] for o in EventsOnly.res[lang]["own"].values()], ensure_ascii=False)
            for word in ("zoom.us", "meet.google.com", "123 456", "zz65", "meeting ID", "passcode", "Person"):
                self.assertNotIn(word, text, word)

    def test_an_events_own_page_title_and_description(self):
        """eventPageMeta: the title with its day (never " · "), the tail "Events — NETA 65", a description of its day,
        its place in brief (the venue and its city) and its summary cut at a word (≤ 160 with its "…", as every page's
        description), without how to join online; the flyer as the share picture."""
        self.ld("en")
        en, es = EventsOnly.res["en"]["own"], EventsOnly.res["es"]["own"]
        self.assertEqual(en["zz-district"]["meta"]["title"], "La Viña Writing Workshop (in Spanish) — Garland, November 28, 2026")
        self.assertEqual(es["zz-district"]["meta"]["title"], "La Viña Writing Workshop (in Spanish) — Garland, 28 de noviembre de 2026")
        # (several days: the range as the card writes its dates — Intl's, thin spaces around the dash in English)
        self.assertEqual(en["zz-assembly"]["meta"]["title"].replace(" ", ""), "Test Area Spring Assembly, November 20–22, 2026")
        self.assertEqual(es["zz-assembly"]["meta"]["title"].replace(" ", ""), "Test Area Spring Assembly, 20–22 de noviembre de 2026")
        self.assertEqual((en["zz-acm"]["meta"]["titleTail"], es["zz-acm"]["meta"]["titleTail"]), ("Events — NETA 65", "Eventos — NETA 65"))
        for own in (*en.values(), *es.values()):
            m = own["meta"]
            self.assertNotIn(" · ", m["title"])
            self.assertLessEqual(len(m["description"]), 160)
            self.assertNotRegex(m["description"], r"\s{2}|[<>]|zoom\.us|123 456|zz65|passcode")
        # the place in brief: the venue and its city (the page shows the whole address)
        self.assertEqual(en["zz-district"]["meta"]["description"],
                         "Saturday, November 28, 2026 · 7:00 – 9:00 PM CST · Grupo Cinco, Garland — "
                         "Organized by the District 99 La Viña committee.")
        self.assertEqual(en["zz-hybrid-codes"]["meta"]["description"],
                         "Saturday, November 7, 2026 · 1:00 – 3:00 PM CST · Grupo Seis, Tyler — "
                         "Share your story with us. Coffee at 1 PM.")
        # (a venue that names its city: the venue alone)
        self.assertIn(" · Primary Purpose Group – Arlington — Come in person or join on Zoom.", en["zz-hybrid"]["meta"]["description"])
        # no summary: its day and place; a long one cut at a word, "…" (the HTML and its entities read)
        self.assertEqual(en["zz-own-link"]["meta"]["description"],
                         "Monday, November 2, 2026 · 1:00 – 3:00 PM CST · Grupo Cuatro, Tyler")
        cut = en["zz-doc-link"]["meta"]["description"]
        head = "Sunday, November 1, 2026 · 1:00 – 3:00 PM CST · Grupo Tres, Tyler — An afternoon workshop on "
        self.assertTrue(cut.startswith(head) and cut.endswith("…") and len(cut) <= 160, cut)
        self.assertTrue((head + "writing & recording your story. " + " ".join(["Bring a notebook and a friend."] * 15))
                        .startswith(cut[:-1] + " "), cut)
        # the flyer (Google's 1200-px picture of the Drive file) as the share picture, its words; else none (the card)
        flyer = en[f"ev-flyer-{DRIVE_ID.lower()}"]["meta"]["ogImage"]
        self.assertEqual(flyer, {"src": f"https://lh3.googleusercontent.com/d/{DRIVE_ID}=w1200", "alt": "Flyer: Committee Visit"})
        self.assertEqual(es[f"ev-flyer-{DRIVE_ID.lower()}"]["meta"]["ogImage"]["alt"], "Volante: Committee Visit")
        self.assertIsNone(en["zz-district"]["meta"]["ogImage"])

    def test_description_image_and_own_page(self):
        # (?v=3: the card shows the site's address, grapevine.neta65.org since round 35)
        for lang, card in (("en", "og-default.png?v=3"), ("es", "og-default-es.png?v=3")):
            by = self.ld(lang)
            with self.subTest(lang=lang):
                # the summary as one plain line (no HTML, its entities read), cut at a word: ≤ 300 characters + "…"
                full = ("An afternoon workshop on writing & recording your story. "
                        + " ".join(["Bring a notebook and a friend."] * 15))
                d = by["zz-workshop"]["description"]
                self.assertLessEqual(len(d), 301)
                self.assertTrue(d.endswith("…"), d)
                self.assertTrue(full.startswith(d[:-1]) and full[len(d) - 1] == " ", d)
                self.assertNotRegex(d, r"\s{2}|[<>]")
                self.assertEqual(by["zz-hybrid"]["description"], "Come in person or join on Zoom.")
                # how to join online (meeting ID, passcode, the Zoom link) never goes into the search engines' copy
                self.assertEqual(by["zz-hybrid-codes"]["description"], "Share your story with us. Coffee at 1 PM.")
                # an outside calendar's words are theirs (their page tells search engines about it); no summary: none
                self.assertNotIn("description", by["ev-lv-calendar-zz-lvcal"])
                self.assertNotIn("description", by["ev-gv-calendar-zz-gvcal"])
                self.assertNotIn("description", by[f"ev-flyer-{DRIVE_ID.lower()}"])
                # the flyer (Google's 1200-px picture of the Drive file), else — the committee's own events only — the
                # committee's card in this language (the card names the committee: never someone else's event)
                flyer = f"https://lh3.googleusercontent.com/d/{DRIVE_ID}=w1200"
                self.assertEqual(by["zz-workshop"]["image"], flyer)
                self.assertEqual(by[f"ev-flyer-{DRIVE_ID.lower()}"]["image"], flyer)
                for anchor in ("zz-hybrid", "ev-recurring-zz-booth-2026-10-10", "zz-doc-link"):
                    self.assertEqual(by[anchor]["image"], SITE["url"] + "/assets/img/" + card, anchor)
                for anchor in ("zz-assembly", "zz-gv-own", "zz-district", "ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal"):
                    self.assertNotIn("image", by[anchor], anchor)
                # its own page on another site; never a flyer on Drive / Docs, a home page, our own site, its own card
                self.assertEqual({a: e["sameAs"] for a, e in by.items() if "sameAs" in e}, {
                    "zz-workshop": "https://neta65.org/event/zz-workshop/",
                    "ev-lv-calendar-zz-lvcal": "https://www.aalavina.org/get-involved/events/2027-01-29/zz",
                    "ev-gv-calendar-zz-gvcal": "https://www.aagrapevine.org/events/zz-roundup"})


LOCAL_JS = r"""
const { localIso } = await imp("eleventy/filters/committee.js");
out(input.cases.map(([iso, tz]) => localIso(Date.parse(iso), tz || undefined)));
"""


class LocalTimes(unittest.TestCase):
    """localIso (since round 35): an instant as the site's wall time with the offset it has at that very instant."""

    CASES = [
        (("2027-01-17T19:00:00Z", None), "2027-01-17T13:00:00-06:00"),          # CST: the Central orientation, 1 PM
        (("2027-01-18T00:00:00Z", None), "2027-01-17T18:00:00-06:00"),          # …its end, 6 PM (UTC: the next day)
        (("2027-03-19T23:00:00Z", None), "2027-03-19T18:00:00-05:00"),          # CDT: the Spring Assembly's Friday
        (("2026-11-29T01:00:00Z", None), "2026-11-28T19:00:00-06:00"),          # an evening event keeps its own day
        # the night the clocks go back (Nov 1, 2026): 1:30 AM twice — first in daylight time, then in standard time
        (("2026-11-01T06:30:00Z", None), "2026-11-01T01:30:00-05:00"),
        (("2026-11-01T07:30:00Z", None), "2026-11-01T01:30:00-06:00"),
        # …and the night they go forward (Mar 14, 2027): 1:59 AM CST, then 3:00 AM CDT
        (("2027-03-14T07:59:00Z", None), "2027-03-14T01:59:00-06:00"),
        (("2027-03-14T08:00:00Z", None), "2027-03-14T03:00:00-05:00"),
        # another zone (the Grapevine Weekly Open's Eastern time), an unknown one (Central), seconds kept
        (("2026-10-21T16:00:00Z", "America/New_York"), "2026-10-21T12:00:00-04:00"),
        (("2026-10-21T16:00:00Z", "Mars/Olympus"), "2026-10-21T11:00:00-05:00"),
        (("2026-12-02T01:00:30Z", None), "2026-12-01T19:00:30-06:00"),
        # no time: nothing (eventLd then keeps its UTC time)
        (("not a time", None), ""),
    ]

    def test_fixed_instants(self):
        got = run_js(self, LOCAL_JS, data={"cases": [c for c, _ in self.CASES]})
        for (case, want), value in zip(self.CASES, got):
            with self.subTest(case=case):
                self.assertEqual(value, want)
                if want:            # the same instant as the UTC time it came from
                    self.assertEqual(datetime.fromisoformat(value), datetime.fromisoformat(case[0].replace("Z", "+00:00")))


class Places(unittest.TestCase):
    """eventPlace: a place as written → name + PostalAddress (fixed texts)."""

    CASES = [
        # "<venue>, <street>, <city>, <ST> <zip>"
        (("Grupo Libro Grande, 623 West Bow, Tyler, TX 75702", {}),
         {"name": "Grupo Libro Grande", "streetAddress": "623 West Bow", "addressLocality": "Tyler",
          "addressRegion": "TX", "postalCode": "75702"}),
        # the data's own city and state; a dash in the venue's name
        (("Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012",
          {"city": "Arlington", "state": "TX"}),
         {"name": "Primary Purpose Group – Arlington", "streetAddress": "1802 West Division Street",
          "addressLocality": "Arlington", "addressRegion": "TX", "postalCode": "76012"}),
        # the neta65.org calendar's way: "TX, 76111, United States"
        (("Grupo Nueva Esperanza, 3401 E Belknap, Fort Worth, TX, 76111, United States", {}),
         {"name": "Grupo Nueva Esperanza", "streetAddress": "3401 E Belknap", "addressLocality": "Fort Worth",
          "addressRegion": "TX", "postalCode": "76111"}),
        (("Tyler Convention Center, Tyler, Texas, United States", {}),
         {"name": "Tyler Convention Center", "addressLocality": "Tyler", "addressRegion": "TX"}),
        # La Viña's calendar: no commas; the city in capitals
        (("Maude Cobb . Convenció center LONGVIEW TX 75604", {"city": None, "state": None}),
         {"name": "Maude Cobb . Convenció center", "addressLocality": "Longview", "addressRegion": "TX",
          "postalCode": "75604"}),
        # …or the data's own city at the end of the street
        (("Grupo Dos, 123 Main St Tyler TX 75702", {"city": "Tyler"}),
         {"name": "Grupo Dos", "streetAddress": "123 Main St", "addressLocality": "Tyler", "addressRegion": "TX",
          "postalCode": "75702"}),
        # a city alone
        (("Tyler, TX", {"city": "Tyler", "state": "TX"}),
         {"name": "Tyler, TX", "addressLocality": "Tyler", "addressRegion": "TX"}),
        (("Fort Worth TX", {}), {"name": "Fort Worth TX", "addressLocality": "Fort Worth", "addressRegion": "TX"}),
        # no venue named: the whole text is its name
        (("123 Main St, Tyler, TX 75702", {}),
         {"name": "123 Main St, Tyler, TX 75702", "streetAddress": "123 Main St", "addressLocality": "Tyler",
          "addressRegion": "TX", "postalCode": "75702"}),
        # a suite; ZIP+4; "tx" written small
        (("Centro Uno, Suite 4, 10 Main, Paris, tx 75460-1234", {}),
         {"name": "Centro Uno", "streetAddress": "Suite 4, 10 Main", "addressLocality": "Paris",
          "addressRegion": "TX", "postalCode": "75460"}),
        # a building and suite after the street, with a comma (the Area's GSR/DCM orientation in Lewisville, 2027): the
        # street keeps both parts
        (("Lewisville Group, 1305 S. State Hwy 121, Bldg A Suite 105, Lewisville, TX 75067",
          {"city": "Lewisville", "state": "TX"}),
         {"name": "Lewisville Group", "streetAddress": "1305 S. State Hwy 121, Bldg A Suite 105",
          "addressLocality": "Lewisville", "addressRegion": "TX", "postalCode": "75067"}),
        # a word like "in" is no state; a venue's name alone is its name, not its street (+ the data's city)
        (("Club in Town", {"city": "Tyler", "state": "texas"}),
         {"name": "Club in Town", "addressLocality": "Tyler", "addressRegion": "TX"}),
        (("Hilton Tyler", {}), {"name": "Hilton Tyler"}),
        # nothing to split but a house number: the street address as a whole
        (("1802 West Division Street", {}), {"name": "1802 West Division Street", "streetAddress": "1802 West Division Street"}),
        # no state written, the data's city and state
        (("Grupo Tres, 1 Elm St, Dallas", {"city": "Dallas", "state": "TX"}),
         {"name": "Grupo Tres", "streetAddress": "1 Elm St", "addressLocality": "Dallas", "addressRegion": "TX"}),
    ]

    def test_fixed_texts(self):
        got = run_js(self, PLACE_JS, data={"cases": [c for c, _ in self.CASES] + [["", {}], ["  ", {}], [None, {}]]})
        for (case, want), place in zip(self.CASES, got):
            with self.subTest(text=case[0]):
                name = want.pop("name") if "name" in want else None
                want = {"@type": "PostalAddress", **want, "addressCountry": "US"}
                self.assertEqual(place, {"@type": "Place", "name": name, "address": want})
        self.assertEqual(got[len(self.CASES):], [None, None, None])         # no place: none


class RealData(unittest.TestCase):
    """data/site/events.json, whatever it holds: every place gives a sensible PostalAddress with nothing made up, and
    the Events of the page (at the data's own clock) follow every rule. Shapes only, never today's venues."""

    def setUp(self):
        data = json.loads((ROOT / "data" / "site" / "events.json").read_text(encoding="utf-8"))
        self.res = run_js(self, REAL_JS, now=str(data.get("updated") or "") or None)

    def test_every_place(self):
        places = self.res["places"]
        for p in places:
            text, place = norm_text(p["text"]), p["place"]
            with self.subTest(id=p["id"], text=text):
                self.assertEqual(place["@type"], "Place")
                a = place["address"]
                self.assertEqual((a["@type"], a["addressCountry"]), ("PostalAddress", "US"))
                self.assertTrue(all(v for v in [place["name"], *a.values()]), place)       # never an empty value
                if not {"streetAddress", "addressLocality", "postalCode", "addressRegion"} & set(a):
                    # a name alone ("Zoom", "Venue to be announced", a venue's name): no address — no Event for it
                    self.assertEqual(place["name"], text)
                    continue
                # nothing made up: every part is in the text (the city: or the data's own)
                self.assertIn(place["name"], text)
                if "streetAddress" in a:
                    self.assertIn(a["streetAddress"], text)
                if "postalCode" in a:
                    self.assertRegex(a["postalCode"], r"^\d{5}$")
                    self.assertIn(a["postalCode"], text)
                if "addressRegion" in a:
                    self.assertRegex(a["addressRegion"], r"^[A-Z]{2}$")
                if p["city"]:
                    self.assertEqual(a.get("addressLocality"), p["city"])
                elif "addressLocality" in a:
                    self.assertIn(a["addressLocality"].lower(), text.lower())
                # what the text says plainly at its end is read: "TX 75702", ", TX" (the data's own state first)
                end = re.search(r"\bTX(?:,? (\d{5})(?:-\d{4})?)?(?:, United States)?$", text)
                if end and end.group(1):
                    self.assertEqual(a.get("postalCode"), end.group(1))
                if p["state"].strip().upper() in ("TX", "TEXAS") or (end and not p["state"]):
                    self.assertEqual(a.get("addressRegion"), "TX")

    def test_the_events_follow_the_rules(self):
        site = self.res["site"]
        root = site["url"] + "/"
        for lang, L in self.res["langs"].items():
            evs = {e["anchor"]: e for e in L["evs"]}
            by = {}
            for e in L["ld"]:
                anchor = anchor_of(e["url"], L["page"])
                # its own page when it has one (eventLeaf), else its card (round 35)
                self.assertEqual(e["url"], L["page"] + anchor + "/" if evs[anchor]["leaf"] else L["page"] + "#" + anchor)
                by[anchor] = e
            # exactly the events held at a known place (a monthly series by its next date), at most 30: not an outside
            # calendar's online event, and only with a real address (a city, a state or a ZIP code)
            real = lambda a: any(a.get(k) for k in ("addressLocality", "addressRegion", "postalCode"))
            placed = [a for a, e in evs.items() if not e["committee"] and not e["later"] and e["location"] and not e["tba"]
                      and e["scope"] != "online" and real(e["address"])]
            self.assertEqual(list(by), placed[:30], lang)
            text = json.dumps(L["ld"], ensure_ascii=False)
            for word in ("VirtualLocation", "OnlineEventAttendanceMode", "performer", '"Person"'):
                self.assertNotIn(word, text)
            for anchor, e in by.items():
                ev = evs[anchor]
                with self.subTest(lang=lang, event=anchor):
                    self.assertEqual(set(e) - EVENT_KEYS, set())
                    self.assertEqual(e["location"]["address"]["@type"], "PostalAddress")
                    self.assertEqual(e["eventAttendanceMode"], MODE("Mixed" if ev["online"] else "Offline"))
                    outside = ev["group"] == "calendar" and not ev["host"]
                    org = e.get("organizer")
                    if ev["host"] == "lv":
                        self.assertEqual(org, {"@type": "Organization", "name": "La Viña", "url": site["lv_home"]})
                    elif ev["host"] == "gv":
                        self.assertEqual(org, {"@type": "Organization", "name": "AA Grapevine", "url": site["gv_home"]})
                    elif outside:
                        self.assertIsNone(org)
                    elif ev["organizer"]:
                        self.assertEqual(org, {"@type": "Organization", "name": ev["organizer"],
                                               **({"url": ev["organizerUrl"]} if ev["organizerUrl"] else {})})
                    elif ev["tone"] == "assembly":
                        self.assertEqual(org, {"@type": "Organization", "url": site["area_website"],
                                               "name": (lang == "es" and site["area_es"]) or site["area"]})
                    else:
                        self.assertEqual(org, {"@type": "Organization", "@id": root + "#committee", "url": root,
                                               "name": site["committee"]})
                    self.assertEqual(e.get("isAccessibleForFree"), True if org and org.get("@id") else None)
                    spanish = ev["host"] == "lv" or ev["category"] == "lv-calendar" or "la-vina" in ev["tags"]
                    self.assertEqual(e.get("inLanguage"), "es" if spanish else None)
                    if outside:
                        self.assertNotIn("description", e)
                    if "description" in e:
                        self.assertLessEqual(len(e["description"]), 301)
                        self.assertNotRegex(e["description"], r"[<>]|\s{2}")
                    # a picture: the flyer, else the committee's card for its own events only
                    if org and org.get("@id"):
                        self.assertRegex(e["image"], r"^https://")
                    elif "image" in e:
                        self.assertRegex(e["image"], r"^https://lh\d\.googleusercontent\.com/")
                    if "sameAs" in e:
                        self.assertRegex(e["sameAs"], r"^https?://[^/]+/.")
                        self.assertNotRegex(e["sameAs"], r"^https?://(?:drive|docs)\.google\.com/")
                        self.assertFalse(e["sameAs"].startswith(root), e["sameAs"])
                        self.assertFalse(ev["leaf"], "an event with a page elsewhere has none here")
                    # its times: the Central wall time with its offset, or an all-day event's days (round 35)
                    for k in ("startDate", "endDate"):
                        self.assertRegex(e[k], r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}-0[56]:00)?$")
            # an event's own page: only one still to come, held at a place, never a monthly series' date or one of the
            # magazines' calendars (every leaf is among the Events above)
            for anchor, ev in evs.items():
                if ev["leaf"]:
                    self.assertIn(anchor, by, lang)
                    self.assertFalse(ev["committee"] or ev["later"] or ev["category"] == "recurring"
                                     or (ev["group"] == "calendar" and not ev["host"]), anchor)


class ThePage(unittest.TestCase):
    """/events/ and /es/events/ rendered by Eleventy: the first ld+json block is the filter's Events, exactly."""

    def test_the_first_block_is_the_events(self):
        day = (datetime.now(CHI) + timedelta(days=10)).replace(hour=14, minute=0, second=0, microsecond=0)

        def iso(days: int, hours: int = 0) -> str:
            return (day + timedelta(days=days, hours=hours)).isoformat()
        items = [
            item("zz-page-place", "Writing Workshop", iso(0), iso(0, 2), summary="A workshop.", tags=["workshop"],
                 location="Grupo Uno, 100 Main St, Tyler, TX 75702", city="Tyler", state="TX"),
            item("zz-page-online", "Online Workshop", iso(1), iso(1, 2), online_url="https://meet.google.com/x",
                 platform="Google Meet"),
        ]
        pages = run_js(self, PAGE_JS, data={"items": items})
        self.assertEqual(sorted(pages), ["en", "es"])
        for lang, p in pages.items():
            with self.subTest(lang=lang):
                # (the first block in its <body>: since round 35 the site-wide graph comes before it, in <head>)
                body = p["html"].index("<body")
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', p["html"][body:], re.S)
                self.assertTrue(blocks)
                first = json.loads(blocks[0])
                self.assertEqual(first, {"@context": "https://schema.org", "@graph": p["want"]})
                # (the place's event has a page of its own: its url, round 35)
                page = p["site"] + ("/es" if lang == "es" else "") + "/events/"
                self.assertEqual([e["url"] for e in first["@graph"]], [page + "zz-page-place/"])
                self.assertIn('id="zz-page-online"', p["html"])                  # its card stays
                # its card's title is a link to that page (search engines find it)
                self.assertIn(f'<a href="{"/es" if lang == "es" else ""}/events/zz-page-place/" class="-my-3 inline-block py-3 '
                              'hover:text-gv">Writing Workshop</a>', p["html"])
                # since round 35 at the very start of the page content: before the hero, far ahead of Googlebot's 2 MB
                main = p["html"].index('<main id="main"')
                at = p["html"].index('<script type="application/ld+json">', body)
                self.assertLess(at, p["html"].index('class="gv-hero', main))
                self.assertLess(main, at)
                self.assertLess(at, 150_000)


if __name__ == "__main__":
    unittest.main()
