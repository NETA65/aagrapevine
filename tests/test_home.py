"""The home page's filters (eleventy/filters/home.js), run with Node.js like the pages run them.

  * Write  — "Write for the magazines" (homeThemes): half Grapevine, half La Viña, so both magazines are always
             invited. La Viña's dated themes (its yearly themes document) count as La Viña's half — they never
             take Grapevine's places; a magazine with too few fills from the other; the dated themes soonest first.

The checks are skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_home -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

NOW = "2026-10-05T17:00:00Z"        # Monday, October 5, 2026, noon in Texas

SCRIPT = r"""
// "now" fixed for the filter (its Central-time day and its weekly rotation)
const fixed = Date.parse(input.now);
Date.now = () => fixed;
out(Object.fromEntries(Object.entries(input.cases).map(([k, items]) => [k, filters.homeThemes(items, 4).map((t) => t.id)])));
"""


def topic(iid: str, title: str, pub: str, deadline: str | None = None, **kw) -> dict:
    """An editorial topic as scripts/sync/editorial.py writes it (data/site/editorial.json)."""
    extra = {"publication": pub, "evergreen": deadline is None and pub == "lv" and not kw.get("issue_key")}
    if deadline:
        extra["deadline"] = deadline
    extra.update(kw)
    return {"id": iid, "kind": "topic", "status": "ok", "title": title, "lang": "es" if pub == "lv" else "en",
            "source": "lavina" if pub == "lv" else "grapevine", "extra": extra}


GV = [topic("ed:gv:2027-06", "Emotional Sobriety", "gv", "2026-11-01", issue_key="2027-06"),
      topic("ed:gv:2027-07", "Annual Prison Issue", "gv", "2026-12-01", issue_key="2027-07"),
      topic("ed:gv:2027-08", "Fun in Sobriety", "gv", "2027-01-01", issue_key="2027-08"),
      topic("ed:gv:2027-04", "Too Late", "gv", "2026-09-01", issue_key="2027-04")]          # its deadline is over
LV_DATED = [topic("ed:lv:2027-05:recaidas", "Recaídas", "lv", "2026-10-17", issue_key="2027-05"),
            topic("ed:lv:2027-07:prisiones", "Prisiones", "lv", "2026-12-15", issue_key="2027-07")]
LV_TOPICS = [topic("ed:lv:any:miedo", "Cómo trato con el miedo hoy", "lv"), topic("ed:lv:any:rezo", "Como rezo", "lv"),
             topic("ed:lv:any:fiesta", "Tiempos de fiesta en sobriedad", "lv")]
GONE = dict(topic("ed:gv:gone", "Removed theme", "gv", "2026-10-20", issue_key="2027-05"), status="gone")


class Write(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {
            "all": GV + LV_DATED + LV_TOPICS + [GONE],
            "no_lv_dated": GV + LV_TOPICS,
            "one_gv": GV[:1] + LV_DATED + LV_TOPICS,
            "no_gv": LV_DATED + LV_TOPICS,
            "no_lv": GV,
            "lv_dated_only": GV + LV_DATED,
        }

    def setUp(self):
        if not getattr(Write, "_r", None):           # node once for the class (it is slow to start)
            Write._r = run_js(self, SCRIPT, data={"now": NOW, "cases": self.cases})
        self.r = Write._r

    def pubs(self, ids: list[str]) -> list[str]:
        return [i.split(":")[1] for i in ids]

    def test_la_vinas_deadline_is_la_vinas_half(self):
        # La Viña's soonest deadline (Oct 17) comes before Grapevine's, but takes La Viña's place, not Grapevine's:
        # Grapevine's next two deadlines, La Viña's next one and one of its open topics — the dated ones soonest first
        ids = self.r["all"]
        self.assertEqual(ids[:3], ["ed:lv:2027-05:recaidas", "ed:gv:2027-06", "ed:gv:2027-07"])
        self.assertIn(ids[3], [t["id"] for t in LV_TOPICS])
        self.assertEqual(sorted(self.pubs(ids)), ["gv", "gv", "lv", "lv"])
        self.assertNotIn("ed:gv:2027-04", ids)                                   # over
        self.assertNotIn("ed:gv:gone", ids)                                      # removed

    def test_without_la_vina_deadlines_as_before(self):
        ids = self.r["no_lv_dated"]
        self.assertEqual(ids[:2], ["ed:gv:2027-06", "ed:gv:2027-07"])
        self.assertTrue(set(ids[2:]) <= {t["id"] for t in LV_TOPICS})
        self.assertEqual(len(ids), 4)

    def test_a_magazine_with_too_few_fills_from_the_other(self):
        one = self.r["one_gv"]                                                    # one Grapevine deadline: La Viña gives 3
        self.assertEqual(sorted(self.pubs(one)), ["gv", "lv", "lv", "lv"])
        self.assertEqual(one[:2], ["ed:lv:2027-05:recaidas", "ed:gv:2027-06"])
        self.assertEqual(self.pubs(self.r["no_gv"]), ["lv"] * 4)                  # its next deadline + its open topics
        self.assertEqual(self.r["no_gv"][0], "ed:lv:2027-05:recaidas")
        self.assertEqual(self.r["no_lv"], ["ed:gv:2027-06", "ed:gv:2027-07", "ed:gv:2027-08"])
        # no open topics: La Viña's half is its next two deadlines
        self.assertEqual(self.r["lv_dated_only"], ["ed:lv:2027-05:recaidas", "ed:gv:2027-06", "ed:gv:2027-07", "ed:lv:2027-07:prisiones"])


if __name__ == "__main__":
    unittest.main()
