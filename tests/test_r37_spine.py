"""Round 37 · the spine of the events' own pages (eleventy/event-pages.js, and its helpers in eleventy/filters/
committee.js): which event gets which page, of what kind, at what address, with what title — the one answer the page
templates, the links to them, /llms.txt and the search read. Checked on made-up events (never the day's data), at a
fixed build moment (site.built 2099-01-10 18:00 UTC):

  * The kinds (eventKind): the title and tag rules on the kinds of events the committee lists — writing, recording
    and information workshops, the GVR/RLV orientation, the Area's GSR/DCM orientations, ACMs, town halls and
    assemblies, an intergroup meeting, a literature table, our three monthly series (CityWide booth, Grapevine
    Meeting, La Viña's workshop), the magazines' own calendars — in English and Spanish, on data items and on
    /events/ events alike; never "taller informativo" for an information workshop. Which magazine (lv / gv / both)
    and whether it is held in Spanish. A `type:` comes first: a content/events file's beats its series' config entry,
    which beats the built-in rules; a `type:` that is no kind is not read.
  * The table (EVENT_KINDS): every kind has its label and phrase in both languages (src/_i18n/evkind.json), "Who can
    come" for exactly the workshops and the GVR/RLV orientation, a bingo occasion the builder knows, flyer patterns
    that match the right flyers; frozen.
  * The tiers (eventPageTier): leaf, page, date, cancelled, none — as the judge's spec §3 table says.
  * The plan (eventPagePlan): every event /events/ lists has a page in both languages (paired: indexable or with its
    Event only when it is so in each), never a committee meeting, a cancelled event or an anchor twice; its path,
    target and hub; titles unique in each language (" — <city>", " — <time>"), descriptions ≤ 160 characters;
    worked out once per build. The series' pages: only for an enabled config entry with a key fit for an address and
    a date still to come in the data — 6 dates in date order (the rule's and the ones the host moved: a skipped
    month's session on another day), never a cancelled one, each linked to its page when it has one.
  * The links (eventPageHref, seriesPagePath): a committee meeting → /meetings/#committee-meeting, an anchor unfit for
    an address → its card (percent-encoded), a cancelled event that is over → /events/, anything else → its own page
    (with a plan: its card when the plan has no page for it). "series" is no anchor (JS and its Python mirror).
  * The bingo card (bingoHref): /[es/]gvr/bingo/#lang=…&mag=…&where=…&event=…&date=…, read back by the builder's own
    code (bingo-core.js decode); the card in Spanish for an event held in Spanish; none for one that is over, nor for
    a data item.
  * The heads keep how to join out: "Meet code …", "código …", and a page's own meeting ID, code or link even bare.
  * Related events (relatedEvents — in the page's language, with a /events/ event as the page too), who holds an
    event (eventOrganizer, isCommitteeOrganizer) and heldInSpanish.

Runs the JavaScript with Node.js (tests/nodejs.py); skipped without Node.js / the npm packages.

    python -m unittest tests.test_r37_spine -v
"""
from __future__ import annotations

import calendar
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

BUILT = "2099-01-10T18:00:00Z"
BASE = "https://x.test"


def nth_weekday(y: int, m: int, weekday: int, n: int) -> date:
    """The n-th `weekday` (Monday 0 … Sunday 6) of a month."""
    first = date(y, m, 1)
    d = 1 + (weekday - first.weekday()) % 7 + 7 * (n - 1)
    assert d <= calendar.monthrange(y, m)[1]
    return date(y, m, d)


DST_2099 = nth_weekday(2099, 3, 6, 2)          # the second Sunday of March: Central daylight time from then


def at(d: date, hhmm: str) -> str:
    """A Central wall-clock time with its offset (CDT from DST_2099 to November)."""
    off = "-05:00" if DST_2099 <= d < date(d.year, 11, 1) else "-06:00"
    return f"{d.isoformat()}T{hhmm}:00{off}"


def item(slug: str, title: str, start: str, end: str, *, category: str = "manual", source: str = "committee",
         url: str = "", summary: str = "", tags: list[str] | None = None, title_es: str = "", ident: str = "",
         **extra) -> dict:
    """An event as data/site/events.json holds it (build_data); a content/events file's (category manual) has its
    file name as its slug — its card's anchor."""
    own = {"slug": slug} if category == "manual" else {}
    it = {"id": ident or f"ev:{category}:{slug}", "source": source, "kind": "event", "category": category, "url": url,
          "title": title, "summary": summary or f"About {title}.", "lang": "en", "date": start, "status": "ok",
          "tags": tags or [], "extra": {"start": start, "end": end, "all_day": len(start) == 10, **own,
                                        "location": None, "online_url": None, "city": None, "state": None, **extra}}
    if title_es:
        it["i18n"] = {"title": {"en": title, "es": title_es}}
        it["extra"]["own_i18n"] = {"title": {"es": title_es}}
    return it


def place(name: str, street: str, city: str, zip_code: str) -> dict:
    return {"location": f"{name}, {street}, {city}, TX {zip_code}", "city": city, "state": "TX"}


def series_date(key: str, d: date, start: str, end: str, title: str, *, rule: dict, **extra) -> dict:
    """A monthly date as build_data.recurring_events writes it."""
    return item(f"{key}:{d.isoformat()}", title, at(d, start), at(d, end), category="recurring",
                ident=f"ev:recurring:{key}:{d.isoformat()}", series=key, recurring=True, rule=rule, **extra)


SAT, WED, THU = 5, 2, 3
CW = {"week_of_month": 2, "weekday": "saturday", "start": "17:30", "end": "19:30"}
GVM = {"week_of_month": 1, "weekday": "wednesday", "start": "19:00", "end": "20:00"}
LVW = {"week_of_month": 4, "weekday": "thursday", "start": "14:00", "end": "15:00"}
TALK = {"week_of_month": 1, "weekday": "saturday", "start": "10:00", "end": "11:00"}
CW_PLACE = "Church Uno, 9200 Inwood Road, Dallas, TX 75220"

SITE = {
    "url": BASE, "built": BUILT, "timezone": "America/Chicago", "committee": "Test Committee",
    "area": "Test Area", "area_es": "Área de Prueba", "area_website": "https://area.example.org",
    "links": {"lv_home": "https://lv.example.org", "gv_home": "https://gv.example.org"},
    "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet",
                "online_url": "https://meet.google.com/abc-defg-hij"},
    "recurring_events": [
        {"key": "citywide-dallas", "title": "GV/LV booth at CityWide Test", "title_es": "Mesa de GV/LV en CityWide Test",
         "summary": "Our literature table at the monthly gathering.", "summary_es": "Nuestra mesa de literatura.",
         **CW, "location": CW_PLACE, "url": "https://citywide.example.org"},
        # (February's 4th Thursday skipped: the host moved that month's session — a dated flyer, below)
        {"key": "lv-monthly-workshop", "title": "La Viña Monthly Virtual Workshop (in Spanish)",
         "title_es": "Taller Mensual y Virtual de La Viña", "summary": "In Spanish, open to all.",
         "summary_es": "En español y abierto a todos.", "host": "lv", **LVW, "skip_dates": ["2099-02-26"],
         "online_url": "https://us06web.zoom.us/j/12345678901", "meeting_id": "123 4567 8901",
         "contact": "test@example.org", "flyer_match": "taller mensual de prueba"},
        {"key": "grapevine-meeting", "title": "Grapevine Meeting", "title_es": "Reunión de Grapevine (en inglés)",
         "summary": "Online AA meeting in English.", "summary_es": "Reunión de AA en línea, en inglés.", **GVM,
         "online_url": "https://meet.google.com/abc-defg-hij", "meeting_id": "abc-defg-hij",
         "url": "/meetings/#grapevine-meeting", "flyer_match": "grapevine meeting test flyer"},
        {"key": "typed-series", "type": "information-workshop", "title": "Test Monthly Talk",
         "title_es": "Charla mensual de prueba", "summary": "A talk.", **TALK, "location": CW_PLACE},
        {"key": "test-table-series", "title": "Test literature table", "title_es": "Mesa de literatura de prueba",
         "summary": "A table.", **TALK, "week_of_month": 3, "location": CW_PLACE},
        {"key": "off-series", "enabled": False, "title": "Test Off Series Picnic", "summary": "Off.", **TALK,
         "week_of_month": 2, "location": CW_PLACE},
        {"key": "past-series", "title": "Test Past Series", "summary": "Gone.", **TALK, "location": CW_PLACE},
        {"key": "no-data", "title": "Test Series Without Data", "summary": "None yet.", **TALK, "location": CW_PLACE},
        {"key": "Bad Key", "title": "Test Badly Named Series", "summary": "Bad key.", **TALK, "location": CW_PLACE},
    ],
}

TYLER = place("Grupo Uno", "100 Main St", "Tyler", "75702")
PLANO = place("Hall Dos", "2 Elm St", "Plano", "75074")
cw1, cw2, cw0 = nth_weekday(2099, 1, SAT, 2), nth_weekday(2099, 2, SAT, 2), nth_weekday(2098, 12, SAT, 2)
cw_cancelled = nth_weekday(2099, 3, SAT, 2)
gvm1, lvw1 = nth_weekday(2099, 2, WED, 1), nth_weekday(2099, 1, THU, 4)
lvw_skipped, lvw_moved = date(2099, 2, 26), date(2099, 2, 18)    # February's rule date (skip_dates) and the day it moved to
assert nth_weekday(2099, 2, THU, 4) == lvw_skipped
talk1, table1 = nth_weekday(2099, 2, SAT, 1), nth_weekday(2099, 2, SAT, 3)

EVENTS = [
    # one-off events (content/events files): their kinds, by title and tag
    item("2099-02-07-test-writing", "Test La Viña Writing Workshop — Tyler", at(date(2099, 2, 7), "10:00"),
         at(date(2099, 2, 7), "12:00"), title_es="Taller de Escritura de Prueba — Tyler", tags=["workshop", "la-vina"],
         organizer="District 99 La Viña Committee", **TYLER),
    item("2099-02-14-test-recording", "Test Recording Workshop", at(date(2099, 2, 14), "10:00"),
         at(date(2099, 2, 14), "12:00"), **TYLER),
    item("2099-03-06-test-info", "Taller de Información de Prueba", at(date(2099, 3, 6), "10:00"),
         at(date(2099, 3, 6), "12:00"), **PLANO),
    item("2099-03-13-gvr-orientation", "GVR and RLV Orientation Workshop", at(date(2099, 3, 13), "10:00"),
         at(date(2099, 3, 13), "11:00"), online_url="https://meet.google.com/abc-defg-hij", platform="Google Meet"),
    item("2099-03-19-test-assembly", "Test Spring Assembly", "2099-03-19", "2099-03-21", tags=["assembly"],
         url="https://area.example.org/event/spring/", **PLANO),
    item("2099-04-11-test-acm-tba", "Test Spring ACM", "2099-04-11", "2099-04-11", tags=["acm"],
         location="Venue to be announced", location_tba=True),
    item("2099-04-18-test-town-hall", "Delegate — Test Conference Connect", at(date(2099, 4, 18), "10:00"),
         at(date(2099, 4, 18), "12:00"), tags=["delegate"], tentative=True, **PLANO),
    item("2099-05-01-test-gsr", "Orientación para RSG y MCD — Norte", at(date(2099, 5, 1), "10:00"),
         at(date(2099, 5, 1), "14:00"), **PLANO),
    item("2099-05-08-test-intergroup", "Reunión intergrupal de prueba", at(date(2099, 5, 8), "18:00"),
         at(date(2099, 5, 8), "20:00"), **TYLER),
    item("2099-05-15-test-table", "Literature table at the Test Picnic", at(date(2099, 5, 15), "10:00"),
         at(date(2099, 5, 15), "14:00"), **PLANO),
    item("2099-05-22-typed", "Test Writing Workshop (typed)", at(date(2099, 5, 22), "10:00"),
         at(date(2099, 5, 22), "12:00"), type="booth", **PLANO),
    item("2099-05-29-bad-type", "Test Writing Workshop (bad type)", at(date(2099, 5, 29), "10:00"),
         at(date(2099, 5, 29), "12:00"), type="party", **PLANO),
    # three of one title on one day: the second in another city, the third in the first one's city at another time
    item("2099-06-05-twin-a", "Test Twin Gathering", at(date(2099, 6, 5), "10:00"), at(date(2099, 6, 5), "12:00"), **TYLER),
    item("2099-06-05-twin-b", "Test Twin Gathering", at(date(2099, 6, 5), "10:00"), at(date(2099, 6, 5), "12:00"), **PLANO),
    item("2099-06-05-twin-c", "Test Twin Gathering", at(date(2099, 6, 5), "14:00"), at(date(2099, 6, 5), "16:00"), **TYLER),
    # one anchor twice (a flyer of a hand-written event's file name): one page, the first one's
    item("2099-07-03-dup", "Dup First", at(date(2099, 7, 3), "10:00"), at(date(2099, 7, 3), "12:00"), **TYLER),
    {**(dup := item("x", "Dup Second", at(date(2099, 7, 3), "10:00"), at(date(2099, 7, 3), "12:00"), category="flyer",
                    source="drive", ident="ev:flyer:dupdupdupdup1", **TYLER)),
     "extra": {**dup["extra"], "slug": "2099-07-03-dup"}},
    # a real address in English only: indexable, but no Event (not a leaf in Spanish)
    {**item("2099-07-10-en-only-place", "Test Open Meeting", at(date(2099, 7, 10), "10:00"), at(date(2099, 7, 10), "12:00"),
            location="Hall Dos, 2 Elm St, Plano, TX 75074"),
     "i18n": {"location": {"en": "Hall Dos, 2 Elm St, Plano, TX 75074", "es": "Salón Dos"}}},
    item("2099-08-07-gv-writing", "Grapevine Writing Workshop — Plano", at(date(2099, 8, 7), "10:00"),
         at(date(2099, 8, 7), "12:00"), tags=["workshop", "grapevine"], **PLANO),
    item("2099-08-14-lv-open-house", "La Viña Open House", at(date(2099, 8, 14), "10:00"), at(date(2099, 8, 14), "12:00"),
         host="lv", **PLANO),
    # an event that is over: a page all the same (noindex)
    item("2098-12-05-old-workshop", "Old Writing Workshop", at(date(2098, 12, 5), "10:00"), at(date(2098, 12, 5), "12:00"),
         **TYLER),
    # cancelled, in the items themselves: no ordinary page
    item("2099-02-21-cancelled-workshop", "Cancelled Writing Workshop", at(date(2099, 2, 21), "10:00"),
         at(date(2099, 2, 21), "12:00"), cancelled=True, **TYLER),
    # the magazines' own calendars
    item("gvtest", "64th Test Convention", "2099-01-29", "2099-01-31", category="gv-calendar", source="calendar",
         url="https://www.aagrapevine.org/events/test", ident="ev:gvcal:abcdef123456", **PLANO),
    item("lvtest", "Taller de La Viña-Grapevine", "2099-02-20", "2099-02-20", category="lv-calendar", source="calendar",
         url="https://www.aalavina.org/events/test", ident="ev:lvcal:fedcba654321", scope="online"),
    # our monthly series' dates (and one the host moved: a dated Drive flyer of La Viña's workshop)
    *[series_date("citywide-dallas", d, "17:30", "19:30", "GV/LV booth at CityWide Test", rule=CW, location=CW_PLACE,
                  host="neta", title_es="Mesa de GV/LV en CityWide Test",
                  summary="Our literature table at the monthly gathering.") for d in (cw0, cw1, cw2)],
    series_date("grapevine-meeting", gvm1, "19:00", "20:00", "Grapevine Meeting", rule=GVM, host="neta",
                title_es="Reunión de Grapevine (en inglés)", summary="Online AA meeting in English.",
                online_url="https://meet.google.com/abc-defg-hij", online=True, platform="Google Meet"),
    series_date("lv-monthly-workshop", lvw1, "14:00", "15:00", "La Viña Monthly Virtual Workshop (in Spanish)", rule=LVW,
                host="lv", online_url="https://us06web.zoom.us/j/12345678901", online=True, platform="Zoom"),
    # (the series' room, as build_data.series_dated_flyers gives a moved date)
    item("x", "La Viña Monthly Virtual Workshop (in Spanish)", "2099-01-21", "2099-01-21", category="flyer",
         source="drive", ident="ev:flyer:lvflyer1234567", url="https://drive.google.com/file/d/lvflyer1234567/view",
         series_of="lv-monthly-workshop", host="lv", online_url="https://us06web.zoom.us/j/12345678901", online=True,
         platform="Zoom"),
    # February's session, moved from the 4th Thursday (skipped) to the Wednesday before: the series' page lists it
    item("x", "La Viña Monthly Virtual Workshop (in Spanish)", at(lvw_moved, "14:00"), at(lvw_moved, "15:00"),
         category="flyer", source="drive", ident="ev:flyer:lvflyerfeb7654", series_of="lv-monthly-workshop", host="lv",
         online_url="https://us06web.zoom.us/j/12345678901", online=True, platform="Zoom", meeting_id="123 4567 8901"),
    series_date("typed-series", talk1, "10:00", "11:00", "Test Monthly Talk", rule=TALK, location=CW_PLACE, host="neta"),
    series_date("test-table-series", table1, "10:00", "11:00", "Test literature table", rule={**TALK, "week_of_month": 3},
                location=CW_PLACE, host="neta"),
    series_date("off-series", nth_weekday(2099, 2, SAT, 2), "10:00", "11:00", "Test Off Series Picnic",
                rule={**TALK, "week_of_month": 2}, location=CW_PLACE, host="neta"),
    series_date("past-series", nth_weekday(2098, 12, SAT, 1), "10:00", "11:00", "Test Past Series", rule=TALK,
                location=CW_PLACE, host="neta"),
    series_date("Bad Key", nth_weekday(2099, 3, SAT, 1), "10:00", "11:00", "Test Badly Named Series", rule=TALK,
                location=CW_PLACE, host="neta"),
]
# db.events.cancelled: an upcoming one and one that is over (records only there), and a CityWide date
CANCELLED = [
    item("2099-02-28-moved-out", "Cancelled Picnic", at(date(2099, 2, 28), "10:00"), at(date(2099, 2, 28), "12:00"),
         cancelled=True, **TYLER),
    item("2098-11-28-old-cancelled", "Old Cancelled Workshop", at(date(2098, 11, 28), "10:00"),
         at(date(2098, 11, 28), "12:00"), cancelled=True, **TYLER),
    series_date("citywide-dallas", cw_cancelled, "17:30", "19:30", "GV/LV booth at CityWide Test", rule=CW,
                location=CW_PLACE, host="neta", cancelled=True),
]

# made-up data items for eventKind alone (no page)
RAW_KINDS: list[tuple[dict, str, str]] = [
    # (item, kind, the rule that decided)
    (item("a", "La Viña Writing Workshop (in Spanish) — Fort Worth", "2099-01-01", "2099-01-01",
          title_es="Taller de Escritura de La Viña — Fort Worth", tags=["workshop", "la-vina"]), "writing-workshop", "title"),
    (item("b", "Grapevine Writing Workshop — Arlington", "2099-01-01", "2099-01-01", tags=["workshop", "grapevine"]),
     "writing-workshop", "title"),
    (item("c", "La Viña Recording Workshop (in Spanish) — Duncanville", "2099-01-01", "2099-01-01",
          title_es="Taller de Grabación de La Viña — Duncanville", tags=["workshop", "la-vina"]), "recording-workshop", "title"),
    (item("d", "Taller de Audio de La Viña", "2099-01-01", "2099-01-01"), "recording-workshop", "title"),
    (item("e", "La Viña Information Workshop (in Spanish) — Longview", "2099-01-01", "2099-01-01",
          title_es="Taller de Información de La Viña — Longview", tags=["workshop", "la-vina"]), "information-workshop", "title"),
    (item("f", "Informational Workshop on the Magazines", "2099-01-01", "2099-01-01"), "information-workshop", "title"),
    # never "taller informativo" (La Viña's monthly flyer says it)
    (item("g", "Taller Informativo Mensual de La Viña", "2099-01-01", "2099-01-01"), "other", "default"),
    (item("h", "GSR/DCM Orientation 2027 — Central", "2099-01-01", "2099-01-01",
          title_es="Orientación para RSG y MCD 2027 — Central", tags=["neta65", "gsr-dcm-orientation", "panel-77"]),
     "gsr-dcm-orientation", "tag"),
    (item("i", "Orientation for GSRs and DCMs", "2099-01-01", "2099-01-01"), "gsr-dcm-orientation", "title"),
    (item("j", "GVR and RLV Orientation Workshop", "2099-01-01", "2099-01-01"), "gvr-orientation", "title"),
    (item("k", "Orientación para RLV", "2099-01-01", "2099-01-01"), "gvr-orientation", "title"),
    (item("l", "Winter ACM 2027", "2099-01-01", "2099-01-01", title_es="ACM de Invierno 2027", tags=["neta65", "acm"]),
     "acm", "tag"),
    (item("m", "Reunión del Comité de Área de Primavera", "2099-01-01", "2099-01-01"), "acm", "title"),
    (item("n", "Delegate — Conference Connect Town Hall", "2099-01-01", "2099-01-01",
          title_es="Reunión Informativa de la Delegada — Conference Connect", tags=["neta65", "delegate", "town-hall"]),
     "town-hall", "tag"),
    (item("o", "The Delegate's Town Hall", "2099-01-01", "2099-01-01"), "town-hall", "title"),
    (item("p", "NETA 65 Spring Assembly 2027", "2099-01-01", "2099-01-01", tags=["assembly", "neta65"]), "assembly", "tag"),
    (item("q", "Asamblea de Verano", "2099-01-01", "2099-01-01"), "assembly", "title"),
    (item("r", "La Viña Intergroup Meeting (in Spanish) — Fort Worth", "2099-01-01", "2099-01-01",
          tags=["intergroup", "la-vina"]), "intergroup", "tag"),
    (item("s", "Reunión Intergrupal", "2099-01-01", "2099-01-01"), "intergroup", "title"),
    (item("t", "64th SETA Convention", "2099-01-01", "2099-01-03", category="gv-calendar", source="calendar",
          ident="ev:gvcal:111111111111"), "calendar", "calendar"),
    (item("u", "Grapevine Committee Crash", "2099-01-01", "2099-01-01", category="flyer", source="drive",
          ident="ev:flyer:crash12345678"), "other", "default"),
    (item("v", "Literature table at the Test Picnic", "2099-01-01", "2099-01-01"), "booth", "tone"),
    # the series: by their key (SERIES_KIND); of another key: by its words, who holds it, online only
    (item("w", "GV/LV booth at CityWide Dallas", "2099-01-01", "2099-01-01", category="recurring",
          ident="ev:recurring:citywide-dallas:2099-01-01", series="citywide-dallas"), "booth", "series"),
    (item("x", "Grapevine Meeting", "2099-01-01", "2099-01-01", category="recurring",
          ident="ev:recurring:grapevine-meeting:2099-01-01", series="grapevine-meeting"), "online-meeting", "series"),
    (item("y", "La Viña Monthly Virtual Workshop (in Spanish)", "2099-01-01", "2099-01-01", category="flyer",
          source="drive", ident="ev:flyer:lvflyer7654321", series_of="lv-monthly-workshop", host="lv"),
     "magazine-workshop", "series"),
    (item("z1", "A Monthly Table", "2099-01-01", "2099-01-01", category="recurring", ident="ev:recurring:other-table:2099-01-01",
          series="other-table"), "booth", "series"),
    (item("z2", "Their Monthly Talk", "2099-01-01", "2099-01-01", category="recurring", ident="ev:recurring:their-talk:2099-01-01",
          series="their-talk", host="gv"), "magazine-workshop", "series"),
    (item("z3", "Our Monthly Hour", "2099-01-01", "2099-01-01", category="recurring", ident="ev:recurring:our-hour:2099-01-01",
          series="our-hour", online_url="https://meet.google.com/abc-defg-hij", platform="Google Meet"), "online-meeting", "series"),
    (item("z4", "Our Monthly Picnic", "2099-01-01", "2099-01-01", category="recurring", ident="ev:recurring:our-picnic:2099-01-01",
          series="our-picnic", location=CW_PLACE), "other", "default"),
    # type: first — a file's own, then its series' entry; a type that is no kind is not read
    (item("t1", "Test Writing Workshop", "2099-01-01", "2099-01-01", type="booth"), "booth", "type"),
    (item("t2", "Test Writing Workshop", "2099-01-01", "2099-01-01", type="party"), "writing-workshop", "title"),
    (item("t3", "Test Monthly Talk", "2099-01-01", "2099-01-01", category="recurring",
          ident="ev:recurring:typed-series:2099-01-01", series="typed-series"), "information-workshop", "series-type"),
    (item("t4", "Test Monthly Talk", "2099-01-01", "2099-01-01", category="recurring",
          ident="ev:recurring:typed-series:2099-01-02", series="typed-series", type="town-hall"), "town-hall", "type"),
    # an ACM title beats "assembly" words, an Area title beats a workshop's
    (item("t5", "ACM and Pre-Assembly Workshop", "2099-01-01", "2099-01-01"), "acm", "title"),
]

SPINE_JS = r"""
const P = await imp("eleventy/event-pages.js");
const K = await imp("eleventy/filters/committee.js");
const vm = await import("node:vm");
const site = input.site, langs = ["en", "es"];
const now = new Date(site.built);
const sum = (p) => ({ lang: p.lang, anchor: p.anchor, path: p.path, tier: p.tier, index: p.index, ld: p.ld,
  kind: p.kind.kind, source: p.kind.source, mag: p.kind.mag, spanish: p.kind.spanish, outside: p.kind.outside,
  series: p.kind.series, hubKey: p.hubKey, hubPath: p.hubPath, target: p.target, titleSuffix: p.titleSuffix,
  head: p.head, title: p.ev.title, past: p.ev.past });
const plan = P.eventPagePlan(input.items, site, langs, { cancelled: input.cancelled });
const r = {};
r.pages = plan.pages.map(sum);
r.hubs = plan.hubs.map((h) => ({ lang: h.lang, key: h.key, path: h.path, kind: h.kind.kind, source: h.kind.source,
  next: h.next.anchor, dates: h.dates.map((d) => d.anchor), datePages: h.datePages.map((p) => (p ? p.path : null)),
  target: h.target, index: h.index, head: h.head, recurrenceDay: h.series.recurrenceDay, title: h.series.title }));
r.hubKeys = plan.hubKeys;
r.cancelledAnchors = plan.cancelledAnchors;
r.byAnchorKeys = Object.keys(plan.byAnchor).sort();
r.byPathKeys = Object.keys(plan.byPath).sort();
r.now = plan.now;
// worked out once per build: the same call → the same plan; another moment, another cancelled list → another
r.memo = [P.eventPagePlan(input.items, site, langs, { cancelled: input.cancelled }) === plan,
  P.eventPagePlan(input.items, { ...site, built: "2099-01-11T18:00:00Z" }, langs, { cancelled: input.cancelled }) === plan,
  P.eventPagePlan(input.items, site, langs, { cancelled: [...input.cancelled] }) === plan,
  P.eventPagePlan([...input.items], site, langs, { cancelled: input.cancelled }) === plan];

// the kinds of data items
r.raw = input.raw.map((it) => { const k = P.eventKind(it, site); return [k.kind, k.source, k.mag, k.spanish, k.outside, k.series, k.deck, k.flyers]; });
r.rawNoSite = P.eventKind(input.raw.find((x) => x.extra.series === "typed-series"), undefined).kind;
// the table
r.kinds = JSON.parse(JSON.stringify(P.EVENT_KINDS));
r.kindKeys = P.EVENT_KIND_KEYS;
r.seriesKind = P.SERIES_KIND;
r.frozen = [Object.isFrozen(P.EVENT_KINDS), Object.isFrozen(P.EVENT_KINDS.booth), Object.isFrozen(P.EVENT_KINDS.booth.resources)];
r.flyers = {};
for (const [k, d] of Object.entries(P.EVENT_KINDS)) {
  if (!d.flyers || d.flyers === "series") continue;
  const re = new RegExp(d.flyers, "i");
  r.flyers[k] = input.flyerNames.filter((n) => re.test(n));
}
r.tiersTable = P.EVENT_TIERS;

// tiers, one language at a time, on /events/ events
const evs = { en: K.normalizeEvents(input.items, site, "en", { now }), es: K.normalizeEvents(input.items, site, "es", { now }) };
const shapedCancelled = K.normalizeEvents(input.cancelled, site, "en", { now }).filter((e) => !e.committee);
const movedOut = shapedCancelled.find((e) => e.anchor === "2099-02-28-moved-out");
r.tiers = {};
for (const ev of evs.en) r.tiers[ev.anchor] = r.tiers[ev.anchor] || P.eventPageTier(ev, site, langs);
for (const ev of shapedCancelled) r.tiers["cancelled:" + ev.anchor] = P.eventPageTier(ev, site, langs);
const tyler = evs.en.find((e) => e.anchor === "2099-02-07-test-writing");
r.tierBadAnchor = P.eventPageTier({ ...tyler, anchor: "Not Fit" }, site, langs);
r.tierNull = P.eventPageTier(null, site, langs);
r.committeeTier = P.eventPageTier(evs.en.find((e) => e.committee), site, langs);

// the links
const raw = (a) => input.items.find((it) => K.eventAnchor(it) === a);
const committeeRaw = { id: "ev:committee:2099-01-20", category: "committee", kind: "event", extra: { start: "2099-01-20T19:00:00-06:00" } };
const fresh = { id: "ev:manual:zz-new", kind: "event", category: "manual", extra: { slug: "zz-new", start: "2099-09-09T10:00:00-05:00" } };
const freshPast = { id: "ev:manual:zz-old", kind: "event", category: "manual", extra: { slug: "zz-old", start: "2098-09-09T10:00:00-05:00" } };
r.href = {
  committeeRaw: [K.eventPageHref(committeeRaw, "en"), K.eventPageHref(committeeRaw, "es")],
  committeeEv: K.eventPageHref(evs.es.find((e) => e.committee), "es"),
  badAnchor: [K.eventPageHref({ ...tyler, anchor: "Not Fit" }, "en"), K.eventPageHref({ ...tyler, anchor: "" }, "es")],
  cancelledPast: [K.eventPageHref(input.cancelled[1], "en", { now }), K.eventPageHref(input.cancelled[1], "es", { now })],
  cancelledUpcoming: [K.eventPageHref(input.cancelled[0], "en", { now }), K.eventPageHref(input.cancelled[0], "es", { now: site.built })],
  cancelledShaped: K.eventPageHref(movedOut, "en"),
  past: [K.eventPageHref(raw("2098-12-05-old-workshop"), "en", { now }), K.eventPageHref(evs.es.find((e) => e.anchor === "2098-12-05-old-workshop"), "es")],
  pastByFlag: K.eventPageHref({ ...fresh, extra: { ...fresh.extra, past: true } }, "en", { now, plan }),
  upcoming: [K.eventPageHref(raw("2099-02-07-test-writing"), "en", { now }), K.eventPageHref(tyler, "es")],
  series: K.eventPageHref(raw("ev-recurring-citywide-dallas-" + input.cw1), "es", { now, plan }),
  notInPlan: [K.eventPageHref(fresh, "en", { now, plan }), K.eventPageHref(freshPast, "es", { now, plan }), K.eventPageHref(fresh, "en", { now })],
  junk: [K.eventPageHref(null, "en"), K.eventPageHref("x", "es")],
  seriesPath: [K.seriesPagePath("citywide-dallas", "en"), K.seriesPagePath("citywide-dallas", "es"), K.seriesPagePath("Bad Key", "en"),
    K.seriesPagePath("", "es"), K.seriesPagePath(undefined)],
};
r.cancelledHelper = [K.eventCancelled({ extra: { cancelled: true } }), K.eventCancelled({ cancelled: true }),
  K.eventCancelled({ item: { extra: { cancelled: true } } }), K.eventCancelled({ extra: { cancelled: "yes" } }), K.eventCancelled(null)];

// the bingo cards
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/bingo-core.js", "utf8"), ctx, { filename: "bingo-core.js" });
const B = ctx.GVBingo;
const page = (lang, a) => plan.byAnchor[a][lang];
const bingo = (lang, a) => { const p = page(lang, a); return P.bingoHref(p.ev, p.kind, lang); };
const long = { ...page("en", "2099-02-14-test-recording").ev, title: "A Very Long Title For A Recording Workshop That Goes On And On Past Sixty" };
r.bingo = {
  tylerEn: bingo("en", "2099-02-07-test-writing"), tylerEs: bingo("es", "2099-02-07-test-writing"),
  recEn: bingo("en", "2099-02-14-test-recording"), recEs: bingo("es", "2099-02-14-test-recording"),
  gvEn: bingo("en", "2099-08-07-gv-writing"), acm: bingo("en", "2099-04-11-test-acm-tba"),
  booth: bingo("en", "ev-recurring-citywide-dallas-" + input.cw1), gvm: bingo("es", "ev-recurring-grapevine-meeting-" + input.gvm1),
  noKind: P.bingoHref(page("en", "2099-02-07-test-writing").ev, null, "en"),
  long: P.bingoHref(long, null, "en"),
  past: bingo("en", "2098-12-05-old-workshop"),
  cancelled: P.bingoHref(movedOut, null, "en"),
  junk: P.bingoHref(null, null, "en"),
  // a data item does not say whether it is over (nor its day): no card
  rawItem: P.bingoHref(raw("2099-02-07-test-writing"), null, "en"),
};
r.bingoDecoded = Object.fromEntries(Object.entries(r.bingo).filter(([, h]) => h).map(([k, h]) => {
  const d = B.decode(h.slice(h.indexOf("#")));
  return [k, { lang: d.lang, pub: d.pub, where: d.where, event: d.event, date: d.date }];
}));
r.wheres = Array.from(B.WHERES);

// related events
const rel = (p, o) => P.relatedEvents(plan, p, o).map((x) => x.anchor);
const tylerEn = page("en", "2099-02-07-test-writing");
const hub = plan.hubs.find((h) => h.key === "citywide-dallas" && h.lang === "en");
const cwPage = page("es", "ev-recurring-citywide-dallas-" + input.cw1);
r.related = {
  sameKind: rel(tylerEn, { sameKind: true, n: 3 }),
  sameKindOne: rel(tylerEn, { sameKind: true, n: 1 }),
  coming: P.relatedEvents(plan, tylerEn, { n: 4 }).map((x) => [x.anchor, x.lang, x.ev.startMs, x.kind.series, x.ev.past]),
  pastSame: rel(tylerEn, { sameKind: true, past: true }),
  pastAny: rel(tylerEn, { past: true, n: 10 }),
  hub: P.relatedEvents(plan, hub, { n: 10 }).map((x) => [x.anchor, x.lang, x.kind.series]),
  cwDate: P.relatedEvents(plan, cwPage, { n: 10 }).map((x) => [x.anchor, x.lang, x.kind.series]),
  list: P.relatedEvents(evs.en.filter((e) => !e.committee), tyler, { sameKind: true, n: 3, site }).map((e) => e.anchor),
  none: [P.relatedEvents(plan, null).length, P.relatedEvents(null, tylerEn).length, P.relatedEvents(plan, tylerEn, { n: 0 }).length],
};
// … with a /events/ event as the page: one of the plan's own (its language read from the plan), any other with
// opt.lang — never both languages' pages; with neither, a plan of two languages is refused
const tylerEsPage = page("es", "2099-02-07-test-writing");
const relOf = (p, o) => P.relatedEvents(plan, p, o).map((x) => x.lang + ":" + x.anchor);
r.relatedLang = { byPage: relOf(tylerEsPage, { n: 4 }), ownEv: relOf(tylerEsPage.ev, { n: 4 }),
  optLang: relOf({ ...tylerEsPage.ev }, { n: 4, lang: "es" }) };
try { P.relatedEvents(plan, { ...tylerEsPage.ev }, { n: 4 }); r.relatedLang.thrown = ""; } catch (e) { r.relatedLang.thrown = String(e.message); }

// the heads never give a meeting's own way in — the words "Meet code" / "código" with a Meet code, or the bare value
const hubOf = (k, lang) => plan.hubs.find((h) => h.key === k && h.lang === lang);
const metaWith = (h, summary) => K.seriesPageMeta({ ...h, series: { ...h.series, summary } }, site, h.lang).description;
const recPage = page("en", "2099-02-14-test-recording");
r.join = {
  meetCode: metaWith(hubOf("grapevine-meeting", "en"), "Online AA meeting. Join with the Google Meet code abc-defg-hij."),
  codigo: metaWith(hubOf("grapevine-meeting", "es"), "Reunión en línea. Entra con el código abc-defg-hij."),
  bare: metaWith(hubOf("grapevine-meeting", "es"), "Reunión en línea. Únete aquí: abc-defg-hij."),
  bareZoom: metaWith(hubOf("lv-monthly-workshop", "en"), "In Spanish. Call in with 123-4567-8901."),
  kept: metaWith(hubOf("grapevine-meeting", "en"), "Bring your two-week-old ideas. Meeting ideas welcome."),
  eventHead: P.eventPageHead({ ...recPage, ev: { ...recPage.ev, summary: "Bring a friend. Call in with 815 9593 1777.",
    meetingId: "815 9593 1777" } }, site).description,
  eventHeadSame: P.eventPageHead(recPage, site).description === recPage.head.description,
  ld: K.eventLd([{ ...tyler, summary: "Come early. Join with the Google Meet code abc-defg-hij." }], site, "en",
    site.url + "/events/", 5)[0].description,
  ldBare: K.eventLd([{ ...tyler, summary: "Come early. Use 815 9593 1777 to get in.", meetingId: "815 9593 1777" }], site,
    "en", site.url + "/events/", 5)[0].description,
  values: [K.withoutJoinValues("Come early. Call in with 815-9593-1777. Bye.", ["815 9593 1777"]),
    K.withoutJoinValues("Line one. Join: abc-defg-hij\nLine two stays.", "abc-defg-hij"),
    K.withoutJoinValues("Short code 12345 stays.", ["12345"]),
    K.withoutJoinValues("Untouched  spacing.  Here.", ["999 999 9999", null, ""]),
    K.withoutJoinValues(undefined, ["815 9593 1777"]),
    K.withoutJoinValues("Go to teams.microsoft.com/l/meetup-join/abc now. See you.", ["https://teams.microsoft.com/l/meetup-join/abc"])],
};
// "series" is no event's anchor (/events/series/ holds the series' pages)
r.seriesAnchor = [K.eventAnchor({ id: "ev:manual:series", extra: { slug: "series" } }),
  K.eventAnchor({ id: "ev:manual:series-night", extra: { slug: "series-night" } })];

// who holds it, in what language
const ev = (a, lang = "en") => evs[lang].find((e) => e.anchor === a);
const org = (e, lang = "en") => K.eventOrganizer(e, site, lang);
r.org = {
  named: org(ev("2099-02-07-test-writing")), host: org(ev("2099-08-14-lv-open-house")),
  outside: org(ev("ev-gvcal-abcdef123456")), areaEn: org(ev("2099-03-19-test-assembly")),
  areaEs: org(ev("2099-03-19-test-assembly", "es"), "es"), ours: org(ev("2099-02-14-test-recording")),
  oursIsUs: K.isCommitteeOrganizer(org(ev("2099-02-14-test-recording")), site),
  areaIsUs: K.isCommitteeOrganizer(org(ev("2099-03-19-test-assembly")), site), nullIsUs: K.isCommitteeOrganizer(null, site),
};
// … the same organizer as the Event /events/ gives search engines, free only when it is the committee's
const lds = K.eventLd(evs.en, site, "en", site.url + "/events/", 100);
r.ld = Object.fromEntries(lds.map((e) => [e.url.split("#")[1] || e.url.split("/events/")[1].replace(/\/$/, ""),
  { organizer: e.organizer || null, free: e.isAccessibleForFree ?? null, inLanguage: e.inLanguage || "" }]));
r.ldOrg = Object.fromEntries(evs.en.filter((e) => !e.past && !e.committee).map((e) => [e.anchor, org(e)]));
r.spanish = Object.fromEntries(["2099-02-07-test-writing", "2099-08-14-lv-open-house", "ev-lvcal-fedcba654321",
  "2099-08-07-gv-writing", "2099-02-14-test-recording"].map((a) => [a, [K.heldInSpanish(ev(a)), K.heldInSpanish(raw(a))]]));
out(r);
"""

FLYER_NAMES = [
    "Taller de Escritura de La Viña - Grupo Uno, Tyler", "Grapevine Writing Workshop flyer",
    "Taller de Audio - Grupo Dos", "Recording Workshop 2099", "Taller de Grabación de La Viña",
    "Taller de Información de La Viña - Longview", "Information Workshop flyer",
    "Taller Informativo Mensual de La Viña", "Orientación para RLV y GVR", "GVR Orientation flyer",
]


class Spine(unittest.TestCase):
    r: dict | None = None

    def run_spine(self) -> dict:
        if Spine.r is None:
            Spine.r = run_js(self, SPINE_JS, data={
                "site": SITE, "items": EVENTS, "cancelled": CANCELLED, "raw": [c[0] for c in RAW_KINDS],
                "flyerNames": FLYER_NAMES, "cw1": cw1.isoformat(), "gvm1": gvm1.isoformat()}, timeout=300)
        return Spine.r

    def pages(self, lang: str | None = None) -> list[dict]:
        return [p for p in self.run_spine()["pages"] if lang is None or p["lang"] == lang]

    def page(self, lang: str, anchor: str) -> dict:
        found = [p for p in self.pages(lang) if p["anchor"] == anchor]
        self.assertEqual(len(found), 1, anchor)
        return found[0]


class TheKinds(Spine):
    def test_data_items(self):
        r = self.run_spine()
        for (it, kind, source), got in zip(RAW_KINDS, r["raw"]):
            with self.subTest(title=it["title"]):
                self.assertEqual((got[0], got[1]), (kind, source))

    def test_flags(self):
        r = self.run_spine()
        got = {it["title"] + "|" + it["id"]: g for (it, _, _), g in zip(RAW_KINDS, r["raw"])}

        def flags(title: str) -> list:
            return next(v for k, v in got.items() if k.startswith(title + "|"))
        # [kind, source, mag, spanish, outside, series, deck, flyers]
        self.assertEqual(flags("La Viña Writing Workshop (in Spanish) — Fort Worth")[2:4], ["lv", True])
        self.assertEqual(flags("Grapevine Writing Workshop — Arlington")[2:4], ["gv", False])
        self.assertEqual(flags("64th SETA Convention")[2:5], ["gv", False, True], "Grapevine's own calendar: outside")
        self.assertEqual(flags("GV/LV booth at CityWide Dallas")[2], "both", "it names neither magazine in words")
        self.assertEqual(flags("GV/LV booth at CityWide Dallas")[5], "citywide-dallas")
        gvm = flags("Grapevine Meeting")
        self.assertEqual((gvm[2], gvm[6]), ("gv", "grapevine-meeting"), "the Grapevine Meeting's deck, for Grapevine's")
        self.assertEqual(flags("Their Monthly Talk")[2], "gv")
        self.assertEqual(flags("Our Monthly Hour")[2::4], ["both", ""], "the online meeting's deck: Grapevine's only")
        lvw = flags("La Viña Monthly Virtual Workshop (in Spanish)")
        self.assertEqual((lvw[2], lvw[3], lvw[5]), ("lv", True, "lv-monthly-workshop"))
        self.assertEqual(lvw[7], "taller mensual de prueba", "a series kind's flyers: its own flyer_match")
        self.assertEqual(flags("La Viña Writing Workshop (in Spanish) — Fort Worth")[6], "writing-workshop")
        self.assertEqual(flags("La Viña Recording Workshop (in Spanish) — Duncanville")[6], "writing-workshop",
                         "the closest deck")
        self.assertEqual(r["rawNoSite"], "other", "without the site, a series' type: is not read")

    def test_the_pages_kinds_are_one_in_both_languages(self):
        for p in self.pages("en"):
            with self.subTest(anchor=p["anchor"]):
                es = self.page("es", p["anchor"])
                self.assertEqual((es["kind"], es["source"], es["mag"], es["spanish"]), (p["kind"], p["source"], p["mag"], p["spanish"]))
        want = {"2099-02-07-test-writing": "writing-workshop", "2099-02-14-test-recording": "recording-workshop",
                "2099-03-06-test-info": "information-workshop", "2099-03-13-gvr-orientation": "gvr-orientation",
                "2099-03-19-test-assembly": "assembly", "2099-04-11-test-acm-tba": "acm",
                "2099-04-18-test-town-hall": "town-hall", "2099-05-01-test-gsr": "gsr-dcm-orientation",
                "2099-05-08-test-intergroup": "intergroup", "2099-05-15-test-table": "booth",
                "2099-05-22-typed": "booth", "2099-05-29-bad-type": "writing-workshop",
                "ev-gvcal-abcdef123456": "calendar", "ev-lvcal-fedcba654321": "calendar",
                f"ev-recurring-citywide-dallas-{cw1}": "booth", f"ev-recurring-grapevine-meeting-{gvm1}": "online-meeting",
                f"ev-recurring-lv-monthly-workshop-{lvw1}": "magazine-workshop",
                "ev-flyer-lvflyer1234567": "magazine-workshop", f"ev-recurring-typed-series-{talk1}": "information-workshop",
                f"ev-recurring-test-table-series-{table1}": "booth", "2099-08-14-lv-open-house": "other"}
        for a, k in want.items():
            with self.subTest(anchor=a):
                self.assertEqual(self.page("en", a)["kind"], k)
        self.assertEqual(self.page("en", "ev-lvcal-fedcba654321")["mag"], "lv")
        self.assertTrue(self.page("en", "ev-lvcal-fedcba654321")["spanish"])

    def test_the_table(self):
        r = self.run_spine()
        kinds = r["kinds"]
        self.assertEqual(r["kindKeys"], list(kinds))
        self.assertEqual(set(kinds), {"writing-workshop", "recording-workshop", "information-workshop", "gvr-orientation",
                                      "gsr-dcm-orientation", "assembly", "acm", "town-hall", "intergroup", "booth",
                                      "online-meeting", "magazine-workshop", "calendar", "committee-meeting", "other"})
        strings = json.loads((ROOT / "src" / "_i18n" / "evkind.json").read_text(encoding="utf-8"))
        for k, d in kinds.items():
            with self.subTest(kind=k):
                self.assertEqual((d["label"], d["phrase"]), (f"evkind.{k}.label", f"evkind.{k}.phrase"))
                for key in (d["label"], d["phrase"]) + ((d["who"],) if d["who"] else ()):
                    self.assertTrue(strings[key]["en"] and strings[key]["es"], key)
                self.assertIn(d["where"], r["wheres"], "an occasion the bingo builder knows")
                self.assertIsInstance(d["resources"], list)
                for f in ("family", "deck", "deckMag", "deckClose", "flyers", "resourceFallback", "resourceAnchors"):
                    self.assertIn(f, d)
        self.assertEqual({k for k, d in kinds.items() if d["who"]},
                         {"writing-workshop", "recording-workshop", "information-workshop", "gvr-orientation"})
        self.assertEqual({k for k in strings if k.endswith(".who")},
                         {f"evkind.{k}.who" for k in ("writing-workshop", "recording-workshop", "information-workshop", "gvr-orientation")})
        self.assertIn("evkind.series_title", strings)
        self.assertEqual(r["seriesKind"], {"citywide-dallas": "booth", "grapevine-meeting": "online-meeting",
                                           "lv-monthly-workshop": "magazine-workshop"})
        self.assertEqual(r["frozen"], [True, True, True])
        self.assertEqual(kinds["writing-workshop"]["resources"][:3], ["contribute", "tips", "submit"])
        self.assertEqual(kinds["assembly"]["resourceFallback"], {"official": "area"})
        self.assertEqual(kinds["gsr-dcm-orientation"]["resourceAnchors"], {"gvr": ["job"]})
        self.assertTrue(kinds["recording-workshop"]["deckClose"])
        self.assertEqual(kinds["online-meeting"]["deckMag"], "gv")
        # the similar flyers: each workshop's own, never La Viña's monthly flyer ("taller informativo")
        self.assertEqual(r["flyers"]["writing-workshop"], ["Taller de Escritura de La Viña - Grupo Uno, Tyler", "Grapevine Writing Workshop flyer"])
        self.assertEqual(r["flyers"]["recording-workshop"], ["Taller de Audio - Grupo Dos", "Recording Workshop 2099", "Taller de Grabación de La Viña"])
        self.assertEqual(r["flyers"]["information-workshop"], ["Taller de Información de La Viña - Longview", "Information Workshop flyer"])
        self.assertEqual(r["flyers"]["gvr-orientation"], ["Orientación para RLV y GVR", "GVR Orientation flyer"])


class TheTiers(Spine):
    def test_the_tier_table(self):
        r = self.run_spine()
        t = r["tiers"]
        for a in ("2099-02-07-test-writing", "2099-02-14-test-recording", "2099-04-18-test-town-hall", "2099-05-01-test-gsr"):
            self.assertEqual(t[a], "leaf", a)                     # tentative too
        for a in ("2099-03-13-gvr-orientation", "2099-03-19-test-assembly", "2099-04-11-test-acm-tba"):
            self.assertEqual(t[a], "page", a)                     # online only, a page elsewhere, a place to be announced
        self.assertEqual(t["2099-07-10-en-only-place"], "page", "a real address in English only (eventLeaf reads both)")
        for a in (f"ev-recurring-citywide-dallas-{cw1}", "ev-flyer-lvflyer1234567", "ev-gvcal-abcdef123456",
                  "2098-12-05-old-workshop", f"ev-recurring-citywide-dallas-{cw0}"):
            self.assertEqual(t[a], "date", a)                     # a series date, a moved date, outside, over
        self.assertEqual(t["2099-08-14-lv-open-house"], "leaf", "La Viña's own event we share: ours to describe")
        self.assertEqual(t["2099-02-21-cancelled-workshop"], "cancelled")
        self.assertEqual(t["cancelled:2099-02-28-moved-out"], "cancelled")
        self.assertEqual(t["cancelled:2098-11-28-old-cancelled"], "none", "cancelled and over: no page")
        self.assertEqual(r["committeeTier"], "none")
        self.assertEqual(r["tierBadAnchor"], "none")
        self.assertEqual(r["tierNull"], "none")
        self.assertEqual(r["tiersTable"]["leaf"], {"index": True, "ld": True})
        self.assertEqual(r["tiersTable"]["page"], {"index": True, "ld": False})
        self.assertEqual(r["tiersTable"]["date"], {"index": False, "ld": False})


class ThePlan(Spine):
    def test_every_page_has_its_twin(self):
        en, es = self.pages("en"), self.pages("es")
        self.assertEqual(sorted(p["anchor"] for p in en), sorted(p["anchor"] for p in es))
        for p in en:
            with self.subTest(anchor=p["anchor"]):
                twin = self.page("es", p["anchor"])
                self.assertEqual((twin["tier"], twin["index"], twin["ld"]), (p["tier"], p["index"], p["ld"]))
                self.assertEqual(p["path"], f"/events/{p['anchor']}/")
                self.assertEqual(twin["path"], f"/es/events/{p['anchor']}/")
                self.assertEqual(p["index"], p["tier"] in ("leaf", "page"))
                self.assertEqual(p["ld"], p["tier"] == "leaf")
        # an address in English only: indexable in both, its Event in neither
        self.assertEqual([(p["tier"], p["ld"]) for p in (self.page("en", "2099-07-10-en-only-place"), self.page("es", "2099-07-10-en-only-place"))],
                         [("page", False), ("page", False)])
        self.assertEqual(self.page("en", "2099-02-07-test-writing")["tier"], "leaf")
        self.assertEqual(self.page("en", "2098-12-05-old-workshop")["tier"], "date")
        self.assertEqual(self.page("en", f"ev-recurring-citywide-dallas-{cw0}")["tier"], "date")

    def test_what_gets_no_page(self):
        r = self.run_spine()
        anchors = {p["anchor"] for p in self.pages()}
        self.assertFalse([a for a in anchors if a.startswith("ev-committee")], "a committee meeting's page is /meetings/")
        for a in ("2099-02-21-cancelled-workshop", "2099-02-28-moved-out", "2098-11-28-old-cancelled",
                  f"ev-recurring-citywide-dallas-{cw_cancelled}"):
            self.assertNotIn(a, anchors)
            self.assertIn(a, r["cancelledAnchors"])
        self.assertEqual(r["cancelledAnchors"], sorted(r["cancelledAnchors"]))
        # one anchor, one page: the first event's
        dup = [p for p in self.pages() if p["anchor"] == "2099-07-03-dup"]
        self.assertEqual([(p["lang"], p["title"]) for p in dup], [("en", "Dup First"), ("es", "Dup First")])
        self.assertEqual(len({(p["lang"], p["path"]) for p in self.pages()}), len(self.pages()))
        self.assertEqual(r["byAnchorKeys"], sorted(anchors))
        self.assertEqual(r["now"], "2099-01-10T18:00:00.000Z")

    def test_targets_and_hubs_of_the_pages(self):
        self.assertEqual(self.page("en", "2099-02-07-test-writing")["target"], "/events/#2099-02-07-test-writing")
        self.assertEqual(self.page("es", "2098-12-05-old-workshop")["target"], "/es/events/#2098-12-05-old-workshop")
        self.assertEqual(self.page("es", f"ev-recurring-citywide-dallas-{cw0}")["target"], "/es/events/",
                         "a series date that is over has no card on /events/")
        self.assertEqual(self.page("en", f"ev-recurring-citywide-dallas-{cw1}")["target"], f"/events/#ev-recurring-citywide-dallas-{cw1}")
        cw = self.page("es", f"ev-recurring-citywide-dallas-{cw1}")
        self.assertEqual((cw["hubKey"], cw["hubPath"]), ("citywide-dallas", "/es/events/series/citywide-dallas/"))
        old = self.page("en", f"ev-recurring-citywide-dallas-{cw0}")
        self.assertEqual(old["hubKey"], "citywide-dallas", "a date that is over still names its series' page")
        moved = self.page("en", "ev-flyer-lvflyer1234567")
        self.assertEqual((moved["hubKey"], moved["hubPath"]), ("lv-monthly-workshop", "/events/series/lv-monthly-workshop/"))
        for a in (f"ev-recurring-off-series-{nth_weekday(2099, 2, SAT, 2)}", f"ev-recurring-past-series-{nth_weekday(2098, 12, SAT, 1)}",
                  f"ev-recurring-bad-key-{nth_weekday(2099, 3, SAT, 1)}", "2099-02-07-test-writing"):
            with self.subTest(anchor=a):
                p = self.page("en", a)
                self.assertEqual((p["hubKey"], p["hubPath"]), ("", ""), "no series page")

    def test_titles_and_descriptions(self):
        for lang in ("en", "es"):
            heads = [p["head"] for p in self.pages(lang)] + [h["head"] for h in self.run_spine()["hubs"] if h["lang"] == lang]
            titles = [h["title"] for h in heads]
            self.assertEqual(len(titles), len(set(titles)), f"{lang}: no two pages share a title")
            for h in heads:
                with self.subTest(lang=lang, title=h["title"]):
                    self.assertNotIn(" · ", h["title"])
                    self.assertLessEqual(len(h["description"]), 160)
                    self.assertTrue(h["description"])
                    self.assertEqual(h["titleTail"], "Events — NETA 65" if lang == "en" else "Eventos — NETA 65")
                    for secret in ("abc-defg-hij", "123 4567 8901", "zoom.us", "meet.google.com"):
                        self.assertNotIn(secret, h["description"])
        a, b, c = (self.page("en", f"2099-06-05-twin-{x}") for x in "abc")
        self.assertEqual(a["head"]["title"], "Test Twin Gathering, June 5, 2099")
        self.assertEqual(a["titleSuffix"], "", "the first keeps its title")
        self.assertEqual(b["head"]["title"], "Test Twin Gathering, June 5, 2099 — Plano")
        self.assertEqual(re.sub(r"\s", " ", c["titleSuffix"]), "2:00 – 4:00 PM CDT", "Tyler has one already: its time")
        self.assertEqual(self.page("es", "2099-06-05-twin-b")["head"]["title"], "Test Twin Gathering, 5 de junio de 2099 — Plano")
        self.assertEqual(self.page("en", "2099-02-07-test-writing")["head"]["title"],
                         "Test La Viña Writing Workshop — Tyler, February 7, 2099")

    def test_worked_out_once(self):
        self.assertEqual(self.run_spine()["memo"], [True, False, False, False])


class TheSeriesPages(Spine):
    def test_which_series(self):
        r = self.run_spine()
        self.assertEqual(r["hubKeys"], ["citywide-dallas", "lv-monthly-workshop", "grapevine-meeting", "typed-series",
                                        "test-table-series"],
                         "enabled, a key fit for an address, a date to come in the data — in config order")
        self.assertEqual([(h["lang"], h["key"]) for h in r["hubs"]],
                         [(lang, k) for k in r["hubKeys"] for lang in ("en", "es")])
        for p in ("/events/series/citywide-dallas/", "/es/events/series/grapevine-meeting/"):
            self.assertIn(p, r["byPathKeys"])

    def test_a_series_page(self):
        r = self.run_spine()
        hubs = {(h["lang"], h["key"]): h for h in r["hubs"]}
        cw = hubs[("en", "citywide-dallas")]
        self.assertEqual((cw["path"], cw["target"], cw["index"], cw["kind"]), ("/events/series/citywide-dallas/", "/events/", True, "booth"))
        self.assertEqual(hubs[("es", "citywide-dallas")]["path"], "/es/events/series/citywide-dallas/")
        self.assertEqual(hubs[("es", "citywide-dallas")]["target"], "/es/events/")
        self.assertEqual(len(cw["dates"]), 6)
        self.assertEqual(cw["next"], cw["dates"][0])
        self.assertEqual(cw["dates"][:2], [f"ev-recurring-citywide-dallas-{cw1}", f"ev-recurring-citywide-dallas-{cw2}"])
        self.assertNotIn(f"ev-recurring-citywide-dallas-{cw_cancelled}", cw["dates"], "a cancelled date is never listed")
        self.assertEqual(cw["datePages"][:2], [f"/events/ev-recurring-citywide-dallas-{cw1}/", f"/events/ev-recurring-citywide-dallas-{cw2}/"])
        self.assertEqual(cw["datePages"][2:], [None] * 4, "dates the data does not have yet: no page to link")
        self.assertEqual(cw["head"]["title"], "GV/LV booth at CityWide Test — Every second Saturday of the month")
        self.assertTrue(cw["head"]["description"].startswith("Every second Saturday of the month · 5:30 – 7:30 PM Central time · Church Uno, Dallas — Our literature table"),
                        cw["head"]["description"])
        es = hubs[("es", "citywide-dallas")]
        self.assertEqual(es["head"]["title"], "Mesa de GV/LV en CityWide Test — Cada segundo sábado del mes")
        gvm = hubs[("en", "grapevine-meeting")]
        self.assertEqual((gvm["kind"], gvm["source"]), ("online-meeting", "series"))
        self.assertIn("Online on Google Meet — Online AA meeting in English.", gvm["head"]["description"])
        self.assertEqual(gvm["datePages"][0], f"/events/ev-recurring-grapevine-meeting-{gvm1}/")
        lvw = hubs[("es", "lv-monthly-workshop")]
        self.assertIn("En línea por Zoom", lvw["head"]["description"])
        self.assertNotIn("123 4567 8901", json.dumps(lvw["head"]))
        self.assertEqual(hubs[("en", "typed-series")]["kind"], "information-workshop")
        self.assertEqual(hubs[("en", "test-table-series")]["kind"], "booth")

    def test_the_dates_the_host_moved(self):
        """La Viña's workshop skips February's 4th Thursday (skip_dates) and holds it on the Wednesday before (a dated
        flyer, extra.series_of): the series' page lists that day among its dates, in date order — and its next date
        is the moved one when it comes first —, never the skipped rule date; each links to its page."""
        r = self.run_spine()
        hubs = {(h["lang"], h["key"]): h for h in r["hubs"]}
        lv_key = "ev-recurring-lv-monthly-workshop-"
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                lv = hubs[(lang, "lv-monthly-workshop")]
                self.assertEqual(lv["dates"], ["ev-flyer-lvflyer1234567", f"{lv_key}{lvw1}", "ev-flyer-lvflyerfeb7654",
                                               f"{lv_key}2099-03-26", f"{lv_key}2099-04-23", f"{lv_key}2099-05-28"])
                self.assertNotIn(f"{lv_key}{lvw_skipped}", lv["dates"], "the skipped rule date")
                self.assertEqual(lv["next"], "ev-flyer-lvflyer1234567", "its next date: a moved one")
                pre = "/es" if lang == "es" else ""
                self.assertEqual(lv["datePages"][:3], [f"{pre}/events/ev-flyer-lvflyer1234567/",
                                                       f"{pre}/events/{lv_key}{lvw1}/", f"{pre}/events/ev-flyer-lvflyerfeb7654/"])
                self.assertEqual(lv["datePages"][3:], [None] * 3)
                moved = self.page(lang, "ev-flyer-lvflyerfeb7654")
                self.assertEqual((moved["tier"], moved["hubPath"]), ("date", f"{pre}/events/series/lv-monthly-workshop/"))
        self.assertIn("Online on Zoom", hubs[("en", "lv-monthly-workshop")]["head"]["description"],
                      "the moved date's room: the series' own")


class TheLinks(Spine):
    def test_event_page_href(self):
        h = self.run_spine()["href"]
        self.assertEqual(h["committeeRaw"], ["/meetings/#committee-meeting", "/es/meetings/#committee-meeting"])
        self.assertEqual(h["committeeEv"], "/es/meetings/#committee-meeting")
        self.assertEqual(h["badAnchor"], ["/events/#Not%20Fit", "/es/events/"], "its card, the anchor percent-encoded")
        self.assertEqual(h["cancelledPast"], ["/events/", "/es/events/"])
        self.assertEqual(h["cancelledUpcoming"], ["/events/2099-02-28-moved-out/", "/es/events/2099-02-28-moved-out/"],
                         "its notice page")
        self.assertEqual(h["cancelledShaped"], "/events/2099-02-28-moved-out/")
        self.assertEqual(h["past"], ["/events/2098-12-05-old-workshop/", "/es/events/2098-12-05-old-workshop/"])
        self.assertEqual(h["upcoming"], ["/events/2099-02-07-test-writing/", "/es/events/2099-02-07-test-writing/"])
        self.assertEqual(h["series"], f"/es/events/ev-recurring-citywide-dallas-{cw1}/")
        self.assertEqual(h["notInPlan"], ["/events/#zz-new", "/es/events/", "/events/zz-new/"],
                         "with a plan: its card (or /events/ once over) when the plan writes no page for it")
        self.assertEqual(h["pastByFlag"], "/events/")
        self.assertEqual(h["junk"], ["/events/", "/es/events/"])
        self.assertEqual(h["seriesPath"], ["/events/series/citywide-dallas/", "/es/events/series/citywide-dallas/",
                                           "/events/", "/es/events/", "/events/"])
        self.assertEqual(self.run_spine()["cancelledHelper"], [True, True, True, False, False])

    def test_bingo_card(self):
        r = self.run_spine()
        b, d = r["bingo"], r["bingoDecoded"]
        self.assertEqual(b["tylerEn"], "/gvr/bingo/#lang=es&mag=lv&where=workshop&event=Taller%20de%20Escritura%20de%20Prueba"
                                       "%20%E2%80%94%20Tyler&date=2099-02-07", "held in Spanish: a Spanish card, its Spanish title")
        self.assertEqual(b["tylerEs"], "/es" + b["tylerEn"])
        self.assertEqual(b["noKind"], b["tylerEn"], "the kind worked out when left out")
        self.assertEqual(b["recEn"], "/gvr/bingo/#lang=en&mag=both&where=workshop&event=Test%20Recording%20Workshop&date=2099-02-14")
        self.assertTrue(b["recEs"].startswith("/es/gvr/bingo/#lang=es&mag=both&where=workshop&"), "the page's language")
        self.assertEqual((d["gvEn"]["pub"], d["gvEn"]["lang"]), ("gv", "en"))
        self.assertEqual(d["acm"]["where"], "acm")
        self.assertEqual((d["booth"]["where"], d["booth"]["date"]), ("booth", cw1.isoformat()))
        self.assertEqual((d["gvm"]["where"], d["gvm"]["pub"], d["gvm"]["event"]), ("online", "gv", "Reunión de Grapevine (en inglés)"))
        for k, v in d.items():
            with self.subTest(card=k):
                href = b[k]
                self.assertRegex(href, r"^(?:/es)?/gvr/bingo/#lang=(?:en|es)&mag=(?:both|gv|lv)&where=[a-z]+&event=[^&]+&date=20\d\d-\d\d-\d\d$")
                # the builder reads it back whole (bingo-core.js decode: a value it would refuse is left out)
                self.assertEqual(v["event"], unquote(re.search(r"&event=([^&]+)", href).group(1)))
                self.assertTrue(v["lang"] and v["pub"] and v["where"] and v["date"])
                self.assertNotIn("booth=", href)
        long = d["long"]["event"]
        self.assertLessEqual(len(long), 60)
        self.assertTrue("A Very Long Title For A Recording Workshop That Goes On And On Past Sixty".startswith(long))
        self.assertEqual(long, "A Very Long Title For A Recording Workshop That Goes On And", "cut at a word")
        self.assertEqual((b["past"], b["cancelled"], b["junk"], b["rawItem"]), ("", "", "", ""))


class Related(Spine):
    def test_related_events(self):
        rel = self.run_spine()["related"]
        self.assertEqual(rel["sameKind"], ["2099-05-29-bad-type", "2099-08-07-gv-writing"], "the next of its kind, soonest first")
        self.assertEqual(rel["sameKindOne"], ["2099-05-29-bad-type"])
        coming = rel["coming"]
        self.assertEqual(len(coming), 4)
        self.assertNotIn("2099-02-07-test-writing", [c[0] for c in coming])
        self.assertEqual([c[2] for c in coming], sorted(c[2] for c in coming))
        self.assertTrue(all(c[1] == "en" and not c[4] for c in coming), "the page's language, still to come")
        series = [c[3] for c in coming if c[3]]
        self.assertEqual(len(series), len(set(series)), "one date per series")
        self.assertEqual(coming[0][0], f"ev-recurring-citywide-dallas-{cw1}")
        self.assertEqual(rel["pastSame"], ["2098-12-05-old-workshop"])
        self.assertNotIn(f"ev-recurring-citywide-dallas-{cw0}", rel["pastSame"])
        self.assertIn("ev-recurring-citywide-dallas-" + cw0.isoformat(), rel["pastAny"])
        self.assertFalse([x for x in rel["hub"] if x[2] == "citywide-dallas"], "a series' page: never its own dates")
        self.assertTrue(rel["hub"])
        self.assertFalse([x for x in rel["cwDate"] if x[2] == "citywide-dallas"], "a series date: never its own series")
        self.assertTrue(all(x[1] == "es" for x in rel["cwDate"]))
        self.assertEqual(rel["list"], rel["sameKind"], "a list of /events/ events gives the same")
        self.assertEqual(rel["none"], [0, 0, 0])

    def test_the_pages_language_with_an_event(self):
        """A /events/ event as the page (it does not say its language): the plan's own event takes its page's
        language, any other takes opt.lang — the same list as with the plan's page, all of it Spanish; with neither,
        a plan of two languages is refused (it would list both twins of an event)."""
        r = self.run_spine()["relatedLang"]
        self.assertEqual(len(r["byPage"]), 4)
        self.assertTrue(all(x.startswith("es:") for x in r["byPage"]), r["byPage"])
        self.assertEqual(r["ownEv"], r["byPage"])
        self.assertEqual(r["optLang"], r["byPage"])
        self.assertIn("opt.lang", r["thrown"])


class TheHeadsKeepJoinDetailsOut(Spine):
    """No meeting code, ID or link in a copy made for machines (meta descriptions, the Event's description): the
    words that say how to join — since round 37 also "Meet code" and a Meet code after "Meet", "code" or "código"
    (committee.js saysHowToJoin: plainLine, withoutJoinDetails) — and an event's or a series' own code or link, even
    bare (withoutJoinValues: eventPageHead, seriesPageMeta, eventLd)."""

    def test_the_series_pages_and_event_pages(self):
        j = self.run_spine()["join"]
        for k in ("meetCode", "codigo", "bare", "bareZoom", "eventHead", "ld", "ldBare"):
            with self.subTest(k):
                for secret in ("abc-defg-hij", "815 9593 1777", "123-4567-8901"):
                    self.assertNotIn(secret, j[k])
        self.assertTrue(j["meetCode"].endswith("Online on Google Meet — Online AA meeting."), j["meetCode"])
        self.assertTrue(j["codigo"].endswith("— Reunión en línea."), j["codigo"])
        self.assertTrue(j["bare"].endswith("— Reunión en línea."), j["bare"])
        self.assertTrue(j["bareZoom"].endswith("— In Spanish."), j["bareZoom"])
        self.assertTrue(j["eventHead"].endswith("— Bring a friend."), j["eventHead"])
        self.assertEqual(j["ld"], "Come early.")
        self.assertEqual(j["ldBare"], "Come early.", "the Event's description: its own meeting ID, bare")
        self.assertIn("Bring your two-week-old ideas. Meeting ideas", j["kept"], "no code, no join words: kept")
        self.assertTrue(j["eventHeadSame"], "nothing to leave out: the head as eventPageMeta gives it")

    def test_without_join_values(self):
        self.assertEqual(self.run_spine()["join"]["values"], [
            "Come early. Bye.", "Line one.\nLine two stays.", "Short code 12345 stays.", "Untouched  spacing.  Here.",
            "", "See you."])


class TheReservedAnchor(Spine):
    def test_series_is_no_anchor(self):
        """/events/series/<key>/ holds the series' pages: a content/events file named series.md gets the fallback
        anchor, and What's New (build_data.album_slug, RESERVED_IDS' Python mirror) gives an album "Series" none."""
        self.assertEqual(self.run_spine()["seriesAnchor"], ["ev-manual-series", "series-night"])
        sys.path.insert(0, str(ROOT))
        from scripts.sync import build_data as B
        self.assertIsNone(B.album_slug("Series"))
        self.assertEqual(B.album_slug("Series night"), "series-night")
        js = (ROOT / "eleventy" / "filters" / "committee.js").read_text(encoding="utf-8")
        reserved = re.search(r"const RESERVED_IDS = new Set\(\[(.*?)\]\);", js, re.S).group(1)
        self.assertIn('"series"', reserved)
        self.assertLessEqual(B._RESERVED_ANCHORS, set(re.findall(r'"([^"]+)"', reserved)),
                             "the Python set: some of the site's reserved ids, none of its own")


class WhoAndLanguage(Spine):
    def test_organizer(self):
        r = self.run_spine()
        o = r["org"]
        self.assertEqual(o["named"], {"@type": "Organization", "name": "District 99 La Viña Committee"})
        self.assertEqual(o["host"], {"@type": "Organization", "name": "La Viña", "url": "https://lv.example.org"})
        self.assertIsNone(o["outside"])
        self.assertEqual(o["areaEn"], {"@type": "Organization", "name": "Test Area", "url": "https://area.example.org"})
        self.assertEqual(o["areaEs"]["name"], "Área de Prueba")
        self.assertEqual(o["ours"], {"@type": "Organization", "@id": BASE + "/#committee", "name": "Test Committee", "url": BASE + "/"})
        self.assertEqual((o["oursIsUs"], o["areaIsUs"], o["nullIsUs"]), (True, False, False))
        # the Events search engines get name the same organizer, free only for the committee's own
        for anchor, ld in r["ld"].items():
            with self.subTest(anchor=anchor):
                self.assertEqual(ld["organizer"], r["ldOrg"][anchor])
                self.assertEqual(ld["free"], True if (ld["organizer"] or {}).get("@id") else None)
        self.assertEqual(r["ld"]["2099-02-07-test-writing"]["inLanguage"], "es")

    def test_held_in_spanish(self):
        s = self.run_spine()["spanish"]
        self.assertEqual(s, {"2099-02-07-test-writing": [True, True], "2099-08-14-lv-open-house": [True, True],
                             "ev-lvcal-fedcba654321": [True, True], "2099-08-07-gv-writing": [False, False],
                             "2099-02-14-test-recording": [False, False]})


if __name__ == "__main__":
    unittest.main()
