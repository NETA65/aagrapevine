"""Round 27 — the small fixes of round 26b's last review (owner, November 12, 2026: "apply this minor fixes"):

  * titles      — an event's title without the spaces a calendar left inside its brackets in every place it shows:
                  also the site search (the title and its original) and the Tracker's list of events.

    python -m unittest tests.test_r27_small_fixes -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402


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
