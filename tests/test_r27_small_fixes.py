"""Round 27 — the small fixes of round 26b's last review (owner, November 12, 2026: "apply this minor fixes"):

  * prices      — the English "New … price(s) as of {date}" (never "since": a December print of January's poster said
                  "prices since January 1, 2027"): the Shop's title, line, mark and note, the district report, the
                  monthly e-mail; the Spanish keeps "desde el {date}". The Spanish district report names La Viña first
                  in its books' line, as /es/shop/ does;
  * /meetings/  — a night without a guest speaker says so once: in step 2, as the owner approved it; the hour line
                  above the steps only gives the time and the topic;
  * titles      — an event's title without the spaces a calendar left inside its brackets in every place it shows:
                  also the site search (the title and its original) and the Tracker's list of events.

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


if __name__ == "__main__":
    unittest.main()
