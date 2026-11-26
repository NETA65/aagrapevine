"""The committee meeting's 2027 price follow-up (config/presentations/committee-meeting.yml, "prices-since-january":
a block of its own): "New prices since January 1, 2027", in the past tense, with the yearly prices of the day.

The heads-up before it ("price-heads-up") announces AA Grapevine's change of January 1, 2027 with the letter's own
figures, while the price notice is on, and never after December 31, 2026; its notes once asked the chair to write a
past-tense slide of their own after that. The follow-up is that slide:

  * its window — in the show from January 1 through March 31, 2027 (Central time, both days included: the meetings of
    January, February and March), in BOTH versions ("No guest speaker" names it in `only`), never before or after;
    the build's default version numbers it only on those days, and the player (presentations-core.js current) shows
    it by the viewer's own clock, a copy opened later included;
  * its facts — the four 1-year prices are the site's {live:price_…} (the new ones from January 1, 2027, by
    themselves), never typed in; "optional", one minute, and the versions' minutes still add up.

    python -m unittest tests.test_presentations_price_follow_up -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_presentations import FOLDER, check_deck, slide_minutes  # noqa: E402

DECK = FOLDER / "committee-meeting.yml"
ID = "prices-since-january"
# instants (UTC) and whether the slide is in the show then: Central midnight is 06:00 UTC in January (CST) and
# 05:00 UTC from March 14, 2027 (CDT)
CLOCKS = {
    "2026-12-31T23:59:00Z": False,      # 5:59 PM Central, December 31, 2026
    "2027-01-01T05:59:00Z": False,      # 11:59 PM Central, December 31
    "2027-01-01T06:00:00Z": True,       # midnight Central, January 1, 2027
    "2027-01-20T23:30:00Z": True,       # the January meeting (5:30 PM Central)
    "2027-02-18T01:30:00Z": True,       # the February meeting, 7:30 PM Central
    "2027-03-18T00:30:00Z": True,       # the March meeting, 7:30 PM Central (CDT)
    "2027-04-01T04:59:00Z": True,       # 11:59 PM Central, March 31
    "2027-04-01T05:00:00Z": False,      # midnight Central, April 1, 2027
    "2027-06-16T23:00:00Z": False,
}

CORE_JS = r"""
import vm from "node:vm";
const P = await imp("eleventy/filters/presentations.js");
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/presentations-core.js", "utf8"), ctx);
const G = ctx.GVP;
const res = { build: {}, player: {} };
for (const at of input.clocks) {
  // the build of that day (its default version's numbers: n_default), with no price notice on (shop: {})
  const { decks } = P.loadDecks("config/presentations", { now: new Date(at), shop: {} });
  const d = decks.find((x) => x.id === "committee-meeting");
  const s = d.slides.find((x) => x.id === input.id);
  res.build[at] = s.n_default;
  if (!res.slide) res.slide = { show_from: s.show_from, show_until: s.show_until, optional: s.optional, when: s.when };
}
// the player, on a copy built on December 1, 2026, opened on each day (the viewer's own clock)
const { decks } = P.loadDecks("config/presentations", { now: new Date("2026-12-01T18:00:00Z"), shop: {} });
const deck = P.deckJson(decks.find((x) => x.id === "committee-meeting"), { site: { url: "https://neta65.github.io/aagrapevine/" }, db: {}, now: new Date("2026-12-01T18:00:00Z") });
for (const at of input.clocks) {
  res.player[at] = {};
  for (const p of deck.presets) {
    const cur = G.current(deck, G.emptyState(), p.id, Date.parse(at));
    res.player[at][p.id] = cur.shown.some((e) => e.id === input.id);
  }
}
const s = deck.slides.find((x) => x.id === input.id);
res.tokens = JSON.stringify(s.rows);
res.heads_up = deck.slides.find((x) => x.id === "price-heads-up").show_until;
out(res);
"""


class PriceFollowUp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = yaml.safe_load(DECK.read_text(encoding="utf-8"))
        cls.slides = {s["id"]: s for s in cls.d["slides"]}
        cls.r = None

    def js(self) -> dict:
        if PriceFollowUp.r is None:
            PriceFollowUp.r = run_js(self, CORE_JS, data={"clocks": list(CLOCKS), "id": ID}, now="2026-12-01T18:00:00Z")
        return PriceFollowUp.r

    def test_the_deck_still_passes_the_checker(self):
        self.assertEqual(check_deck(DECK), [])

    def test_its_window_as_written(self):
        s = self.slides[ID]
        self.assertEqual((s["show_from"], s["show_until"]), ("2027-01-01", "2027-03-31"))
        self.assertTrue(s.get("optional"))
        self.assertNotIn("when", s, "past tense: shown after the notice too, never only during it")
        self.assertIn("since January 1, 2027", s["title"])
        heads_up = self.slides["price-heads-up"]
        self.assertEqual((heads_up["when"], heads_up["show_until"]), ("price_notice", "2026-12-31"))
        # the price change it follows (config/site.yml price_changes)
        site = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        change = next(c for c in site["price_changes"] if c["key"] == "2027-01")
        self.assertEqual(str(change["effective"]), s["show_from"])
        self.assertLess(str(change["notice_until"]), s["show_until"], "it outlasts the notice")

    def test_its_prices_are_the_sites(self):
        rows = json.dumps(self.slides[ID]["rows"], ensure_ascii=False)
        for key in ("price_gv_print", "price_gv_digital", "price_lv_print", "price_lv_digital"):
            self.assertIn("{live:" + key + "}", rows)
        self.assertNotRegex(rows, r"\$\d+\.\d\d\b(?! more)", "no price typed in (only the books' “$2.00 more”)")
        self.assertNotRegex(self.slides[ID]["notes"], r"\$(?:39|34|19\.50|17)\b", "the notes say the prices of the day")

    def test_in_both_versions_and_the_minutes_add_up(self):
        no_speaker = next(p for p in self.d["presets"] if p["id"] == "no-speaker")
        self.assertIn(ID, no_speaker["only"])
        self.assertEqual(self.slides[ID]["minutes"], 1)
        slides = self.d["slides"]
        for p in self.d["presets"]:
            if "only" in p:
                shown = [s for s in slides if s["id"] in p["only"]]
            else:
                shown = [s for s in slides if not s.get("facilitator") and not s.get("starts_off") and s["id"] not in (p.get("hide") or [])]
            with self.subTest(version=p["id"]):
                self.assertIn(ID, [s["id"] for s in shown])
                total = sum(slide_minutes(s, p["id"]) for s in shown)
                self.assertTrue(0.9 * p["minutes"] <= total <= p["minutes"], f"{total} minutes in an hour")

    def test_the_window_in_the_build_and_in_the_player(self):
        r = self.js()
        self.assertEqual(r["slide"]["show_from"], "2027-01-01T06:00:00.000Z", "midnight Central, January 1")
        self.assertEqual(r["slide"]["show_until"], "2027-04-01T04:59:59.999Z", "the end of March 31, Central (CDT)")
        self.assertTrue(r["slide"]["optional"])
        self.assertIsNone(r["slide"]["when"])
        for at, want in CLOCKS.items():
            with self.subTest(at=at):
                self.assertEqual(r["build"][at] is not None, want, "the build's default version")
                self.assertEqual(r["player"][at], {"full": want, "no-speaker": want}, "the player, by the viewer's clock")
        self.assertEqual(r["heads_up"], "2027-01-01T05:59:59.999Z")
        self.assertIn("{live:price_gv_print}", r["tokens"])


if __name__ == "__main__":
    unittest.main()
