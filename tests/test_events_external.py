"""The outside calendars (scripts/sync/events_external.py): which events are in Texas, all-day dates, long
events, and whole runs on saved pages — no network (every request is answered from tests/fixtures/
events_external/).

Fixtures: lv-event-longview.html is a trimmed copy of a real La Viña event page (the contacts' e-mail
addresses replaced with example.org ones); the other event pages are made up in the same markup (Drupal
fields + JSON-LD), as are the sitemap and calendar pages.
Run:  python -m unittest tests.test_events_external -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import common  # noqa: E402
from scripts.sync import events_external as E  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "events_external"
GV = "https://www.aagrapevine.org/get-involved/events/"
LV = "https://www.aalavina.org/get-involved/events/"
LONGVIEW = LV + "2027-01-29/xlii-reunion-de-aa-zona-norte-de-texas-aa-un-camino-la-vida"
GAINESVILLE = GV + "2026-11-13/florida-state-convention"
DALLAS = GV + "2026-11-07/north-texas-fall-roundup"
ZOOM = LV + "2026-10-22/taller-mensual-lv"
PAGES = {LONGVIEW: "lv-event-longview.html", GAINESVILLE: "gv-event-gainesville.html",
         DALLAS: "gv-event-dallas-dates.html", ZOOM: "lv-event-zoom.html"}


def fx(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def texas(location: str, title: str = "Roundup") -> bool:
    return bool(E.decide({"title": title, "location_raw": location}).get("texas"))


# --------------------------------------------------------------------------- P2-7: Texas or not
class InTexas(unittest.TestCase):
    def test_the_reviews_example_is_florida(self):
        """"Hilton University of Florida Conference Center, Gainesville" + "Florida State Convention": the old
        city list knew a Gainesville in Texas and ignored "Florida" as an everyday word."""
        self.assertFalse(texas("Hilton University of Florida Conference Center, Gainesville",
                               "Florida State Convention"))
        self.assertFalse(texas("1714 SW 34th St, Gainesville, FL 32607", "Florida State Convention"))
        self.assertTrue(texas("Civic Center, Gainesville, TX 76240"), "the Texas Gainesville, when it says so")

    def test_florida_georgia_chile_name_other_places(self):
        self.assertFalse(texas("Lodge, Dallas", "Georgia Mountain Roundup"), "Dallas, Georgia")
        self.assertFalse(texas("Hotel Central, San Antonio", "Convención de Chile"))
        self.assertFalse(texas("Centro de Convenciones", "Convención Hispana de Florida"))
        self.assertFalse(texas("Salón Principal", "Convención de Área en Georgia"))

    def test_a_written_state_or_country_wins(self):
        for loc in ("Bossier City, Louisiana", "6362 South 13th Street, Oak Creek, WI 53154",
                    "Embassy Suites by Hilton Huntsville 800 Monroe St SW, Huntsville, AL 35801",
                    "Powell River, British Columbia, Canada", "Monterrey, N.L.", "Ciudad Juárez, Chihuahua",
                    "Chiang Mai, Thailand", "Santiago, Chile", "Texarkana, AR", "Hotel, Houston, Mexico"):
            self.assertFalse(texas(loc, "Texas Avenue Group Roundup" if "Bossier" in loc else "Roundup"), loc)
        for loc in ("Maude Cobb . Convenció center LONGVIEW TX 75604", "Austin, Texas", "El Paso, TX 79901",
                    "Hotel, 2010 Main St, Dallas, TX 75201", "Texarkana, TX", "Dallas TX", "Tyler, Tejas",
                    "Hyatt Regency DFW, 2334 N International Pkwy, DFW Airport, TX 75261",
                    "Convention Center, Midland, Texas", "Hotel Emma, San Antonio, Texas, USA"):
            self.assertTrue(texas(loc), loc)

    def test_texas_in_the_title(self):
        self.assertTrue(texas("Maude Cobb Convention Center", "XLII Reunión de A.A. Zona Norte de Texas"))
        self.assertTrue(texas("Lake Murray Lodge", "Texas-Oklahoma Roundup"))

    def test_a_city_alone_counts_only_on_geos_short_list(self):
        for loc in ("Iglesia San Juan Diego, Houston", "Hotel Adolphus, 1321 Commerce St, Dallas",
                    "Centro Comunitario - Fort Worth", "Iglesia San Juan Diego, Houston, USA", "Plano"):
            self.assertTrue(texas(loc, "Taller"), loc)
        # names that exist elsewhere too (the old list said Texas for several of them)
        for loc in ("Hotel X, Paris", "Centro, Lancaster", "Hyatt Regency, San Antonio", "Convention Center, Midland",
                    "Civic Center, Odessa", "Hotel, Greenville", "Huntsville", "Hotel Hilton Garden Inn"):
            self.assertFalse(texas(loc, "Taller"), loc)

    def test_street_names_and_everyday_words_are_no_proof(self):
        self.assertTrue(texas("Hotel, 100 Florida Ave, Houston"))
        self.assertTrue(texas("Iglesia, Calle Chile 12, Houston"))
        self.assertTrue(texas("Club, Dallas", "Sierra Nevada Night"))
        self.assertEqual(E.names_elsewhere("Florida State Convention"), "florida")
        self.assertIsNone(E.names_elsewhere("Hotel on Georgia Street"))
        self.assertIsNone(E.names_elsewhere("Georgetown Indian Springs"))

    def test_the_cached_events_keep_their_answer(self):
        """Every event of data/raw/events_external.json (October 2026) reads the same as with the old city
        list — the one Texas event stays Texas."""
        env = json.loads((ROOT / "data" / "raw" / "events_external.json").read_text(encoding="utf-8"))
        known = {"79th Powell River Rally 2026": False, "36th Vancouver RoundUp": False,
                 "International Secular Conference Phoenix 2026": False, "Taller mensual LV": False,
                 "XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la vida )": True,
                 "14th Chiang Mai Roundup 2026": False, "III Convención Hispana del estado de Alabama": False}
        for e in (env.get("cache") or {}).values():
            ev = (e or {}).get("ev")
            if ev and ev.get("title") in known:
                self.assertEqual(bool(E.decide(ev).get("texas")), known[ev["title"]], ev["title"])


# --------------------------------------------------------------------------- P3-11: dates
def page(start: str, end: str | None, when: str, location: str = "Dallas, TX") -> str:
    ld = {"@type": "Event", "name": "Roundup", "startDate": start, "location": {"name": location}}
    if end:
        ld["endDate"] = end
    return (f'<script type="application/ld+json">{json.dumps(ld)}</script><h1>Roundup</h1>'
            f'<div class="field--name-field-daterange"><div class="field__item">{when}</div></div>'
            f'<div class="field--name-field-event-location"><div class="field__item">{location}</div></div>')


class Dates(unittest.TestCase):
    def ev(self, *a, **k) -> dict:
        return E.parse_event(page(*a, **k), GV + "2026-11-07/roundup")

    def test_a_day_without_a_time_is_all_day(self):
        ev = self.ev("2026-11-07", "2026-11-08", "November 7, 2026 - November 8, 2026")
        self.assertEqual((ev["all_day"], ev["start"], ev["end"]), (True, "2026-11-07", "2026-11-08"))
        one = self.ev("2026-11-07", None, "November 7, 2026")
        self.assertEqual((one["all_day"], one["start"], one.get("end")), (True, "2026-11-07", None))

    def test_local_midnight_without_a_clock_time_is_all_day(self):
        ev = self.ev("2026-11-07T00:00:00-0600", "2026-11-09T00:00:00-0600", "November 7, 2026 - November 8, 2026")
        self.assertEqual((ev["all_day"], ev["start"], ev["end"]), (True, "2026-11-07", "2026-11-08"),
                         "an end at midnight is the moment it is over: the 8th is its last day")
        east = self.ev("2026-11-07T00:00:00-0500", "2026-11-09T00:00:00-0500", "November 7, 2026 - November 8, 2026")
        self.assertEqual((east["all_day"], east["start"], east["end"]), (True, "2026-11-07", "2026-11-08"),
                         "midnight in the offset the page writes: the 7th, not 11 PM on the 6th in Central time")

    def test_drupals_noon_utc_dates_stay_all_day(self):
        ev = self.ev("2027-01-29T06:00:00-0600", "2027-01-31T06:00:00-0600", "Enero 29, 2027 - Enero 31, 2027")
        self.assertEqual((ev["all_day"], ev["start"], ev["end"]), (True, "2027-01-29", "2027-01-31"))

    def test_a_written_time_is_a_timed_event(self):
        ev = self.ev("2026-11-07T19:00:00-0600", "2026-11-07T21:00:00-0600", "November 7, 2026 7:00pm - 9:00pm")
        self.assertEqual((ev["all_day"], ev["start"], ev["end"]), (False, "2026-11-08T01:00:00Z", "2026-11-08T03:00:00Z"))
        midnight = self.ev("2026-12-31T00:00:00-0600", None, "December 31, 2026 12:00 am")
        self.assertFalse(midnight["all_day"], "a midnight start the page writes out is a real time")


# --------------------------------------------------------------------------- F-16: saved pages
class SavedPages(unittest.TestCase):
    def test_the_real_la_vina_page(self):
        ev = E.parse_event(fx("lv-event-longview.html"), LONGVIEW)
        self.assertEqual(ev["title"], "XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la vida )")
        self.assertEqual((ev["start"], ev["end"], ev["all_day"]), ("2027-01-29", "2027-01-31", True))
        self.assertEqual(ev["location"], "Maude Cobb . Convenció center LONGVIEW TX 75604")
        self.assertTrue(ev["texas"])
        self.assertEqual(ev["lang"], "es")
        self.assertNotIn("summary", ev, "only contacts' e-mail addresses: no description is kept")
        self.assertNotIn("example.org", json.dumps(ev))
        self.assertNotIn("image", ev, "the generic AA logo is not a flyer")
        item = E.build_item(LONGVIEW, ev)
        self.assertEqual((item["category"], item["extra"]["scope"], item["extra"]["site"]), ("lv-calendar", "texas", "lavina"))
        self.assertTrue(item["id"].startswith("ev:lvcal:"))

    def test_an_out_of_state_page(self):
        ev = E.parse_event(fx("gv-event-gainesville.html"), GAINESVILLE)
        self.assertFalse(ev["texas"])
        self.assertFalse(E.relevant(GAINESVILLE, ev))
        self.assertEqual(ev["website"], "https://convention.example.org/")
        self.assertTrue(ev["image"].endswith("/fl-convention-flyer.jpg"))
        dump = json.dumps(ev)
        for private in ("pat@example.org", "555", "010-0199"):
            self.assertNotIn(private, dump)

    def test_a_dates_only_page_without_a_state(self):
        ev = E.parse_event(fx("gv-event-dallas-dates.html"), DALLAS)
        self.assertEqual((ev["start"], ev["end"], ev["all_day"]), ("2026-11-07", "2026-11-08", True))
        self.assertTrue(ev["texas"])
        self.assertEqual((ev["city"], ev["organizer"]), ("Dallas", "District 12"))
        self.assertNotIn("events calendar", ev["summary"].lower())

    def test_an_online_workshop_with_its_time(self):
        ev = E.parse_event(fx("lv-event-zoom.html"), ZOOM)
        self.assertEqual((ev["start"], ev["end"], ev["all_day"]), ("2026-10-23T00:00:00Z", "2026-10-23T01:30:00Z", False))
        self.assertEqual((ev["platform"], ev["online_url"], ev["location"]),
                         ("Zoom", "https://us06web.zoom.us/j/12345678901", "Zoom"))
        self.assertTrue(E.relevant(ZOOM, ev))
        self.assertEqual(E.build_item(ZOOM, ev)["extra"]["scope"], "online")
        dump = json.dumps(ev)
        self.assertNotIn("comite@example.org", dump)
        self.assertNotIn("010-0123", dump)

    def test_sitemap_and_calendar_discovery(self):
        http = FakeWeb()
        urls, err = E.discover_from_sitemap(http, "https://www.aagrapevine.org", {}, date(2026, 10, 1))
        self.assertIsNone(err)
        self.assertEqual(urls, {LONGVIEW, GAINESVILLE, DALLAS, ZOOM})
        urls, err = E.discover_from_calendars(http, date(2026, 10, 1))
        self.assertIsNone(err)
        self.assertEqual(urls, {ZOOM, LONGVIEW})


class FakeWeb:
    """The calendar's web pages, answered from the fixtures (`pages` maps an event URL to a page text)."""

    class Resp:
        def __init__(self, status: int, text: str = ""):
            self.status_code, self.text, self.encoding = status, text, "utf-8"

    def __init__(self, pages: dict[str, str] | None = None, sitemap: bool = True):
        self.pages = pages if pages is not None else {u: fx(f) for u, f in PAGES.items()}
        self.sitemap = sitemap
        self.requests_made = 0
        self.asked: list[str] = []

    def get_text(self, url: str, **kw):
        self.requests_made += 1
        if url.endswith("/sitemap.xml"):
            # page 1's <lastmod> moves when its list changes (the sitemap is re-read only then)
            stamp = f"2026-10-05T11:{len(self.pages):02d}:41+00:00"
            return fx("sitemap-index.xml").replace("2026-10-05T11:02:41+00:00", stamp) if self.sitemap else None
        if url.endswith("sitemap.xml?page=1"):
            page1 = fx("sitemap-page-1.xml")
            extra = "".join(f"<url><loc>{u}</loc></url>" for u in self.pages if u not in page1)
            return page1.replace("</urlset>", extra + "</urlset>")
        if url.endswith("sitemap.xml?page=2"):
            return fx("sitemap-page-2.xml")
        if url.endswith("/calendario-de-eventos"):
            return fx("lv-calendar.html")
        return None

    def get(self, url: str, **kw):
        self.requests_made += 1
        self.asked.append(url)
        return self.Resp(200, self.pages[url]) if url in self.pages else self.Resp(404)


class Runs(unittest.TestCase):
    """main() over the saved pages, data/raw redirected to a temporary folder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-evx-"))
        p = mock.patch.object(common, "RAW_DIR", self.tmp)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_on(self, today: date, web: FakeWeb) -> dict:
        with mock.patch.object(E, "shared_session", lambda: web), mock.patch.object(E, "_today", lambda: today):
            E.main([])
        return json.loads((self.tmp / "events_external.json").read_text(encoding="utf-8"))

    def test_a_whole_run(self):
        env = self.run_on(date(2026, 10, 6), FakeWeb())
        self.assertTrue(env["ok"])
        by = {i["url"]: i for i in env["items"]}
        self.assertEqual(set(by), {LONGVIEW, DALLAS, ZOOM}, "the Florida convention is not listed")
        self.assertEqual({u: by[u]["extra"]["scope"] for u in by}, {LONGVIEW: "texas", DALLAS: "texas", ZOOM: "online"})
        self.assertEqual((by[DALLAS]["extra"]["start"], by[DALLAS]["extra"]["end"], by[DALLAS]["extra"]["all_day"]),
                         ("2026-11-07", "2026-11-08", True))
        self.assertEqual(env["stats"]["texas"], 2)
        self.assertNotIn("example.org", json.dumps(env["items"]))

    def test_a_long_event_stays_listed_until_its_last_day(self):
        """A convention from Oct 1 to Oct 8: its URL carries Oct 1, which drops out of the two-day window on
        Oct 4 — it must stay on the calendar until the 8th, and leave on the 9th."""
        long_url = GV + "2026-10-01/week-long-retreat"
        text = page("2026-10-01", "2026-10-08", "October 1, 2026 - October 8, 2026", "Retreat Center, Tyler, TX")
        web = FakeWeb({long_url: text, ZOOM: fx("lv-event-zoom.html")})
        self.assertIn(long_url, {i["url"] for i in self.run_on(date(2026, 9, 30), web)["items"]})
        env = self.run_on(date(2026, 10, 6), web)
        self.assertIn(long_url, {i["url"] for i in env["items"]}, "still running on its sixth day")
        self.assertIn(long_url, env["cache"], "its cache entry is kept while it runs")
        env = self.run_on(date(2026, 10, 8), web)
        self.assertIn(long_url, {i["url"] for i in env["items"]}, "its last day")
        env = self.run_on(date(2026, 10, 9), web)
        self.assertNotIn(long_url, {i["url"] for i in env["items"]})
        # removed from the calendar while it runs: gone at once (a complete sitemap is the whole truth)
        self.run_on(date(2026, 10, 3), web)
        web.pages.pop(long_url)
        self.assertNotIn(long_url, {i["url"] for i in self.run_on(date(2026, 10, 6), web)["items"]})

    def test_the_calendar_fallback_keeps_a_running_long_event(self):
        long_url = GV + "2026-10-01/week-long-retreat"
        text = page("2026-10-01", "2026-10-08", "October 1, 2026 - October 8, 2026", "Retreat Center, Tyler, TX")
        web = FakeWeb({long_url: text, ZOOM: fx("lv-event-zoom.html")})
        self.run_on(date(2026, 9, 30), web)
        web.sitemap = False                                # the calendar page does not list it
        env = self.run_on(date(2026, 10, 6), web)
        self.assertEqual(env["stats"]["discovery"], "calendar")
        self.assertIn(long_url, {i["url"] for i in env["items"]})


if __name__ == "__main__":
    unittest.main()
