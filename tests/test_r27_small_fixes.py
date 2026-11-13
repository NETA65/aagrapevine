"""Round 27 — the small fixes of round 26b's last review (owner, November 12, 2026: "apply this minor fixes"):

  * prices      — the English "New … price(s) as of {date}" (never "since": a December print of January's poster said
                  "prices since January 1, 2027"): the Shop's title, line, mark and note, the district report, the
                  monthly e-mail; the Spanish keeps "desde el {date}". The Spanish district report names La Viña first
                  in its books' line, as /es/shop/ does;
  * /meetings/  — a night without a guest speaker says so once: in step 2, as the owner approved it; the hour line
                  above the steps only gives the time and the topic;
  * titles      — an event's title without the spaces a calendar left inside its brackets in every place it shows:
                  also the site search (the title and its original), the Tracker's list of events, Home's event
                  cards, the /digest/ page (and its texts to copy), What's New, the RSS feeds, the district
                  report's coming events, the Area report's events and the monthly e-mail.

    python -m unittest tests.test_r27_small_fixes -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.notify import send_digest as SDM  # noqa: E402


def i18n() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


T = i18n()


# ---------------------------------------------------------------------------------------------- the words
class PriceWords(unittest.TestCase):
    AFTER = ("shop.pc_title_after", "shop.pc_line_after", "shop.pc_new_since", "report.pc_after")

    def test_new_prices_as_of_the_day_in_english(self):
        for key in self.AFTER:
            with self.subTest(key=key):
                en, es = T[key]["en"], T[key]["es"]
                self.assertIn(" as of {date}", en)
                self.assertNotRegex(en, r"\bsince\b")
                self.assertIn(" desde el {date}", es, "the Spanish stays")
        # the note quotes the plans' own mark, word for word
        self.assertIn(f"“{T['shop.pc_new_since']['en']}”", T["shop.pc_prices_note"]["en"])
        self.assertIn(f"“{T['shop.pc_new_since']['es']}”", T["shop.pc_prices_note"]["es"])
        # the monthly e-mail's row is the Shop's line
        self.assertEqual(SDM.T["en"]["pc_after"], T["shop.pc_line_after"]["en"])
        self.assertEqual(SDM.T["en"]["pc_after"], "New Grapevine and La Viña prices as of {date}")
        self.assertEqual(SDM.T["es"]["pc_after"], "Nuevos precios de La Viña y Grapevine desde el {date}")

    def test_the_spanish_report_names_la_vina_first(self):
        self.assertEqual(T["report.pc_books"]["es"], "Libros de La Viña y Grapevine: {amount} más cada uno")
        self.assertEqual(T["report.pc_books"]["en"], "Grapevine and La Viña books: {amount} more each")
        # as the Shop's line says it
        self.assertEqual(T["report.pc_books"]["es"] + ".", T["shop.pc_books_before"]["es"])


class NoSpeakerWords(unittest.TestCase):
    def test_the_hour_line_gives_the_time_and_the_topic(self):
        self.assertEqual(T["committee.meeting.evening_topic_hour"],
                         {"en": "{time} Central time: we share on a topic until {until}.",
                          "es": "{time}, hora del Centro: hasta las {until} compartimos sobre un tema."})
        # step 2 says it, as the owner approved it (round 26b)
        self.assertIn("When there's no guest speaker, as at this meeting,", T["committee.meeting.step_guest_text"]["en"])
        self.assertIn("cuando no hay orador(a) invitado(a), como en esta reunión,", T["committee.meeting.step_guest_text"]["es"])


# ---------------------------------------------------------------------------------------------- the titles
SPACED = "XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la vida )"
SPACED_ES = "XLII Reunión de A.A. Zona Norte de Texas ( A.A. Un camino a la vida )"
EN = "XLII North Texas Zone A.A. Gathering (A.A. A Way of Life)"
TIDY_ES = "XLII Reunión de A.A. Zona Norte de Texas (A.A. Un camino a la vida)"
TIDY = "XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS (A.A. Un Camino a la vida)"


def event_item() -> dict:
    """La Viña's calendar's event as the sync writes it (data/site/events.json), its title as the calendar gives it."""
    return {"id": "ev:lvcal:zz-xlii", "source": "calendar", "kind": "event", "category": "lv-calendar",
            "url": "https://www.aalavina.org/calendario/xlii", "title": SPACED, "summary": "", "lang": "es",
            "date": "2027-01-16T15:00:00Z", "status": "ok", "tags": [],
            "i18n": {"title": {"en": EN, "es": SPACED_ES}},
            "extra": {"start": "2027-01-16T15:00:00Z", "end": "2027-01-16T23:00:00Z", "all_day": False,
                      "location": "Dallas, TX", "online_url": None}}


SEARCH_JS = r"""
const site = (await imp("src/_data/site.js")).default;
const S = typeof site === "function" ? await site() : site;
const res = {};
for (const lang of ["en", "es"]) {
  const items = JSON.parse(filters.searchIndexJson({ events: { items: [input.ev] } }, [], lang, S)).items;
  res[lang] = items.filter((e) => e.k === "event").map((e) => ({ t: e.t, o: e.o || "" }));
}
out(res);
"""

TRACKER_JS = r"""
process.env.ONLY = "tracker.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r27-tracker-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { updated: "2026-11-12T12:00:00Z", items: input.items } }),
      });
    },
  });
  const pages = await elev.toJSON();
  const res = {};
  for (const p of pages) {
    const m = /<script type="application\/json" id="xp-events">([\s\S]*?)<\/script>/.exec(p.content || "");
    if (m) res[p.url] = JSON.parse(m[1]);
  }
  out(res);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""

# Home, /digest/, What's New and the RSS feeds with the given events and What's New items → per page, how often each
# `find` string is in it.
PAGES_JS = r"""
process.env.ONLY = "index.njk,digest.njk,whats-new.njk,feed.11ty.js";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r27-pages-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { updated: "2027-02-03T12:00:00Z", items: input.events },
                         whatsnew: { updated: "2027-02-03T12:00:00Z", items: input.wn } }),
      });
    },
  });
  const pages = await elev.toJSON();
  const res = {};
  for (const p of pages) {
    if (!/^\/(es\/)?(digest\/|whats-new\/|feed\.xml)?$/.test(p.url || "")) continue;
    res[p.url] = Object.fromEntries(Object.entries(input.find).map(([k, s]) => [k, (p.content || "").split(s).length - 1]));
  }
  out(res);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


# The district report (its coming events) and the Area report (its events) with the given events, at `now`
REPORT_JS = r"""
const R = await imp("eleventy/filters/report.js");
const site = { url: "https://example.org/site", links: {} };
const db = { events: { items: input.events } };
const m = R.reportModel(db, {}, { ways: [], tips: {}, wayById: {} }, site, new Date(input.now));
const A = R.areaModel(db, site, new Date(input.now));
out({ district: Object.fromEntries(["en", "es"].map((l) => [l, m.langs[l].sections.find((s) => s.id === "events").text])),
      area: Object.fromEntries(A.ev.map((r) => [r.id, r.t])) });
"""


class TidyTitles(unittest.TestCase):
    def test_the_site_search_shows_the_title_as_events_does(self):
        r = run_js(self, SEARCH_JS, data={"ev": event_item()}, now="2026-11-12T18:00:00Z")
        self.assertEqual(r["es"], [{"t": TIDY_ES, "o": ""}], "the Spanish title is the original's, respelled")
        self.assertEqual(r["en"], [{"t": EN, "o": TIDY}], "its original shown under the English, tidied too")
        for lang in ("en", "es"):
            for e in r[lang]:
                self.assertNotRegex(e["t"] + " " + e["o"], r"\(\s|\s\)")

    def test_the_trackers_list_of_events(self):
        items = [event_item(), {**event_item(), "id": "ev:lvcal:zz-twice", "title": TIDY}]   # the same title once
        r = run_js(self, TRACKER_JS, data={"items": items}, timeout=600, now="2026-11-12T18:00:00Z")
        self.assertEqual(sorted(r), ["/es/tracker/", "/tracker/"])
        self.assertIn(EN, r["/tracker/"])
        self.assertEqual(r["/es/tracker/"].count(TIDY_ES), 1)
        for url, titles in r.items():
            with self.subTest(url=url):
                self.assertFalse([t for t in titles if re.search(r"\(\s|\s\)", t)], titles)

    def test_the_district_and_area_reports(self):
        # La Viña's calendar's gathering as data/site/events.json has it (January 29–31, 2027): in the 45 days of the
        # December and January reports
        xlii = {**event_item(), "id": "ev:lvcal:zz-xlii-jan", "date": "2027-01-29",
                "extra": {**event_item()["extra"], "start": "2027-01-29", "end": "2027-01-31", "all_day": True,
                          "location": "Maude Cobb . Convenció center LONGVIEW TX 75604"}}
        # an Area assembly from a calendar, with the same stray spaces (the Area report lists the Area's assemblies)
        asm = {**event_item(), "id": "ev:areacal:zz-asm", "category": "area-calendar", "lang": "en", "date": "2027-01-23",
               "title": "NETA 65 Winter Assembly ( Tyler, TX )",
               "i18n": {"title": {"en": "NETA 65 Winter Assembly ( Tyler, TX )",
                                  "es": "Asamblea de Invierno de NETA 65 ( Tyler, TX )"}},
               "extra": {**event_item()["extra"], "start": "2027-01-23", "end": "2027-01-23", "all_day": True,
                         "location": "Tyler, TX"}}
        r = run_js(self, REPORT_JS, data={"events": [xlii, asm], "now": "2027-01-05T18:00:00Z"})
        es, en = r["district"]["es"], r["district"]["en"]
        self.assertIn(TIDY_ES, es)
        self.assertIn(EN, en)
        self.assertIn("NETA 65 Winter Assembly (Tyler, TX)", en)
        self.assertIn("Asamblea de Invierno de NETA 65 (Tyler, TX)", es)
        for text in (es, en):
            self.assertNotRegex(text, r"[(¿¡] |\s\)", "a title with the calendar's spaces")
        self.assertEqual(sorted(r["area"]), ["ev:areacal:zz-asm"], "the Area's assembly (the gathering is neither ours nor one)")
        row = r["area"]["ev:areacal:zz-asm"]
        self.assertEqual((row["en"][1], row["es"][1]), ("NETA 65 Winter Assembly (Tyler, TX)",
                                                        "Asamblea de Invierno de NETA 65 (Tyler, TX)"))

    def test_the_monthly_email_tidies_as_the_site_does(self):
        samples = [SPACED, SPACED_ES, EN, "¿ Qué tal ?", "¡  Hola !", "A (\tB\n)", "( )", "(A) ( B )", "", "Sin paréntesis"]
        js = run_js(self, 'const c = await imp("eleventy/filters/committee.js"); out(input.map((s) => c.tidyBrackets(s)));',
                    data=samples)
        self.assertEqual([SDM.tidy_brackets(s) for s in samples], js, "send_digest.tidy_brackets = committee.js tidyBrackets")
        links = SDM.Links("https://example.org")
        self.assertEqual(SDM.event_row(event_item(), "es", links)["title"], TIDY_ES, "the month's events")
        self.assertEqual(SDM.event_row(event_item(), "en", links)["title"], EN)
        self.assertEqual(SDM.title_of(event_item(), "es"), TIDY_ES, "an event among what is new")
        self.assertEqual(SDM.title_of({**event_item(), "kind": "article"}, "es"), SPACED_ES, "an event's title only")

    def test_home_the_digest_page_whats_new_and_the_feeds(self):
        held = event_item()                                                          # January 16: the digest's month
        ahead = {**event_item(), "id": "ev:lvcal:zz-xlii-feb", "date": "2027-02-20T15:00:00Z",   # next on Home
                 "extra": {**event_item()["extra"], "start": "2027-02-20T15:00:00Z", "end": "2027-02-20T23:00:00Z"}}
        new = {**ahead, "first_seen": "2027-02-01T12:00:00Z", "wn_date": "2027-02-01T12:00:00Z", "is_new": True,
               "machine": ["en"]}
        r = run_js(self, PAGES_JS, data={"events": [held, ahead], "wn": [new],
                                         "find": {"tidy_es": TIDY_ES, "spaced_es": SPACED_ES, "spaced": SPACED, "en": EN}},
                   timeout=600, now="2027-02-03T18:00:00Z")
        want = ["/", "/digest/", "/es/", "/es/digest/", "/es/feed.xml", "/es/whats-new/", "/feed.xml", "/whats-new/"]
        self.assertEqual(sorted(r), want)
        for url, n in r.items():
            with self.subTest(url=url):
                self.assertEqual((n["spaced_es"], n["spaced"]), (0, 0), "a title with the calendar's spaces")
                if url.startswith("/es/"):
                    self.assertGreaterEqual(n["tidy_es"], 1, "the Spanish title, tidied")
                else:
                    self.assertGreaterEqual(n["en"], 1, "the English title")
        self.assertGreaterEqual(r["/digest/"]["tidy_es"], 1, "the original under the English title, tidied too")


if __name__ == "__main__":
    unittest.main()
