"""Structured data on /events/ and /es/events/: what search engines are told about the events — eventLd and
eventPlace in eleventy/filters/committee.js (the `cmEventLd` filter), written by src/pages/events.njk as the page's
FIRST <script type="application/ld+json">.

  * Only events held at a place: Google lists only events at a physical place with a postal address that the public
    may attend (its Event rules, 2026-09-08). An online-only event — the committee meeting's monthly dates, La
    Viña's workshop on Zoom, an event with only an online link — gets no Event, nor does a place "to be announced";
    a hybrid one is "Mixed", at its Place; a monthly series gives its next date only.
  * The place → a schema.org Place with a PostalAddress: "<venue>, <street>, <city>, <ST> <zip>", the data's own
    city and state first, a country at the end, a place written without commas (La Viña's calendar: "… center
    LONGVIEW TX 75604"), a text that cannot be split (the street address as a whole) — and every place in
    data/site/events.json, whatever it holds: nothing made up (every part comes from the text, or is the data's
    own city), never an empty value.
  * Honest facts: the organizer is La Viña / Grapevine for their own events we share, the Area for an Area
    assembly, nobody for an event from their calendars, else the committee — by the site's "#committee" @id;
    isAccessibleForFree only for the committee's own events; inLanguage "es" only for an event held in Spanish.
    description = the summary as one plain line (≤ 300 characters; none for the calendars' events: their words),
    image = the flyer (else the committee's card in the page's language), sameAs = the event's own page on another
    site (never a Drive / Docs flyer, a site's home page or our own site). No performer, no person, no other keys.
  * The page: its first ld+json block is exactly what the filter gives for its events (both languages).

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
    item("zz-doc-link", "Workshop With a Doc", "2026-11-01T19:00:00Z", "2026-11-01T21:00:00Z",
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
         summary="<p>Share your story with us.</p> Come in person or join on Zoom (meeting ID 949 476 7497, "
                 "passcode zz65). Coffee at 1 PM.",
         location="Grupo Seis, 6 Elm St, Tyler, TX 75701", city="Tyler", state="TX",
         online_url="https://us02web.zoom.us/j/9494767497?pwd=abc", platform="Zoom"),
]

LD_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const res = {};
for (const lang of ["en", "es"]) {
  const evs = filters.cmCollapseRecurring(filters.cmEvents(input.items, input.site, lang)).filter((e) => !e.past);
  const page = input.site.url + (lang === "es" ? "/es" : "") + "/events/";
  res[lang] = {
    ld: filters.cmEventLd(evs, input.site, lang, page),
    cards: evs.map((e) => e.anchor),
    byDefault: C.eventLd(evs, input.site, lang).map((e) => e.url),
    capped: C.eventLd(evs, input.site, lang, "", 2).length,
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
    res[lang] = { html: p.content, want: filters.cmEventLd(evs, site, lang, site.url + p.url) };
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
        return {e["url"].rsplit("#", 1)[1]: e for e in EventsOnly.res[lang]["ld"]}

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
                    "zz-hybrid-codes", "zz-assembly", "ev-lv-calendar-zz-lvcal"])
                text = json.dumps(EventsOnly.res[lang]["ld"], ensure_ascii=False)
                for word in ("VirtualLocation", "OnlineEventAttendanceMode", "zoom.us", "meet.google.com", "performer",
                             "Person", "<", "&amp;", "&nbsp;", "Zoom ID", "Virtual (", "Sala virtual", "949 476",
                             "zz65", "Hilton Tyler"):
                    self.assertNotIn(word, text)
                for anchor, e in by.items():
                    self.assertEqual(set(e) - EVENT_KEYS, set(), anchor)                # nothing else said
                    self.assertTrue(all(v not in ("", None, [], {}) for v in e.values()), anchor)
                    self.assertEqual(e["@type"], "Event")
                    self.assertEqual(e["eventStatus"], "https://schema.org/EventScheduled")
                    self.assertEqual(e["url"], SITE["url"] + ("/es" if lang == "es" else "") + "/events/#" + anchor)
                    self.assertEqual(e["location"]["@type"], "Place")
                    self.assertEqual(e["location"]["address"]["@type"], "PostalAddress")
                    self.assertEqual(e["location"]["address"]["addressCountry"], "US")
                    self.assertEqual(e["eventAttendanceMode"], MODE("Mixed" if anchor in ("zz-hybrid", "zz-hybrid-codes") else "Offline"))
                # the page's own address by default, and at most `max` of them
                self.assertEqual(EventsOnly.res[lang]["byDefault"], [e["url"] for e in EventsOnly.res[lang]["ld"]])
                self.assertEqual(EventsOnly.res[lang]["capped"], 2)

    def test_dates_as_before(self):
        by = self.ld("en")
        self.assertEqual((by["zz-workshop"]["startDate"], by["zz-workshop"]["endDate"]),
                         ("2026-10-24T19:00:00.000Z", "2026-10-24T21:00:00.000Z"))
        self.assertEqual((by["zz-assembly"]["startDate"], by["zz-assembly"]["endDate"]), ("2026-11-20", "2026-11-22"))
        self.assertEqual(by["zz-workshop"]["name"], "La Viña Writing Workshop (in Spanish) — Tyler")

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
                # the Area's assembly: the Area
                self.assertEqual(by["zz-assembly"]["organizer"],
                                 {"@type": "Organization", "name": area, "url": "https://area.example.org"})
                # the GV / LV calendars' events: nobody (leaving it out beats guessing)
                for anchor in ("zz-gv-own", "zz-assembly", "ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal"):
                    self.assertNotIn("isAccessibleForFree", by[anchor], anchor)
                for anchor in ("ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal"):
                    self.assertNotIn("organizer", by[anchor], anchor)

    def test_the_language_of_the_event(self):
        for lang in ("en", "es"):
            by = self.ld(lang)
            # held in Spanish: a La Viña workshop (tag la-vina), La Viña's calendar; else not said (not the page's)
            self.assertEqual({a: e.get("inLanguage") for a, e in by.items() if "inLanguage" in e},
                             {"zz-workshop": "es", "ev-lv-calendar-zz-lvcal": "es"}, lang)

    def test_description_image_and_own_page(self):
        for lang, card in (("en", "og-default.png?v=2"), ("es", "og-default-es.png?v=2")):
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
                for anchor in ("zz-assembly", "zz-gv-own", "ev-lv-calendar-zz-lvcal", "ev-gv-calendar-zz-gvcal"):
                    self.assertNotIn("image", by[anchor], anchor)
                # its own page on another site; never a flyer on Drive / Docs, a home page, our own site, its own card
                self.assertEqual({a: e["sameAs"] for a, e in by.items() if "sameAs" in e}, {
                    "zz-workshop": "https://neta65.org/event/zz-workshop/",
                    "ev-lv-calendar-zz-lvcal": "https://www.aalavina.org/get-involved/events/2027-01-29/zz",
                    "ev-gv-calendar-zz-gvcal": "https://www.aagrapevine.org/events/zz-roundup"})


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
                self.assertTrue(e["url"].startswith(L["page"] + "#"), e["url"])
                by[e["url"][len(L["page"]) + 1:]] = e
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
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', p["html"], re.S)
                self.assertTrue(blocks)
                first = json.loads(blocks[0])
                self.assertEqual(first, {"@context": "https://schema.org", "@graph": p["want"]})
                self.assertEqual([e["url"].rsplit("#", 1)[1] for e in first["@graph"]], ["zz-page-place"])
                self.assertIn('id="zz-page-online"', p["html"])                  # its card stays


if __name__ == "__main__":
    unittest.main()
