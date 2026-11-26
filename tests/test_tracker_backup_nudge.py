"""The Tracker's monthly "keep a copy" nudge (src/pages/tracker.njk .xp-nudge, src/assets/js/expenses.js nudgeDue /
nudgeLater, src/_i18n/expenses.json expenses.nudge.*): everything the Tracker holds lives only in the browser, so about
once a month it offers a CSV export and the full backup, in one quiet row above the tabs.

  * When      — never on an empty ledger, nor on a new one: 5 entries of the visitor's own (the examples do not
                count), or 3 days since the first of them; then whenever no copy was made within the backup reminder's
                days (Settings → Reminders, 30 by default) — a CSV export counts as much as a full backup —; never
                while saving fails (the storage alert says more then).
  * Not now   — puts it off for 30 days: the day ("2026-11-26") is kept in localStorage
                ("gv-expenses:v1:backup-nudge") — put off on November 30, it does not come back on December 1 (a
                month kept by the first version, "2026-11", counts from its first day); a browser that refuses storage
                hides it for the visit only, without an error.
  * A copy    — "Export CSV" (and the full backup) stamp the ledger, so the nudge goes at once.
  * The page  — the row is not an alert (nothing went wrong), it holds the two exports and "Not now", in English and
                in Spanish.

    python -m unittest tests.test_tracker_backup_nudge -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_expenses_app import app  # noqa: E402  (the Tracker app in Node.js: make(lang, seed, els, opts), add(), tick())

ROOT = Path(__file__).resolve().parents[1]
NOV26 = 1795694400000          # 2026-11-26T12:00:00Z (the Tracker's own clock: o.now)
NOV30 = 1796040000000          # 2026-11-30T12:00:00Z
DEC01 = 1796126400000          # 2026-12-01T12:00:00Z
DEC03 = 1796299200000          # 2026-12-03T12:00:00Z
DEC29 = 1798545600000          # 2026-12-29T12:00:00Z
JAN05 = 1799150400000          # 2027-01-05T12:00:00Z


class Nudge(unittest.TestCase):
    def test_not_on_a_new_ledger(self):
        r = app(self, r"""
          const res = {};
          const w = make("en", null, null, { now: input.nov });
          await tick();
          res.empty = w.a.nudgeDue();
          w.a.addExamples();
          res.examples = w.a.nudgeDue();
          add(w, "expense", { description: "Big Book", amount: "16" }, "books");
          res.first = w.a.nudgeDue();
          for (let i = 0; i < 3; i++) add(w, "expense", { description: "Grapevine " + i, amount: "4" }, "books");
          res.four = w.a.nudgeDue();
          add(w, "expense", { description: "La Viña", amount: "4" }, "books");
          res.five = w.a.nudgeDue();
          // one entry, a week later: the ledger is no longer new
          const one = make("en", null, null, { now: input.nov });
          await tick();
          add(one, "expense", { description: "Big Book", amount: "16" }, "books");
          const later = make("en", Object.fromEntries(one.store), null, { now: input.dec03 });
          await tick();
          res.weekLater = later.a.nudgeDue();
          out(res);""", data={"nov": NOV26, "dec03": DEC03})
        self.assertFalse(r["empty"], "never on an empty ledger")
        self.assertFalse(r["examples"], "the examples are not the visitor's own")
        self.assertFalse(r["first"], "not right after the first entry")
        self.assertFalse(r["four"])
        self.assertTrue(r["five"], "five entries: worth a copy")
        self.assertTrue(r["weekLater"], "the first entry a week old: worth a copy")

    def test_not_now_keeps_it_away_for_30_days(self):
        r = app(self, r"""
          const res = {};
          const w = make("en", null, null, { now: input.nov26 });
          await tick();
          for (let i = 0; i < 5; i++) add(w, "expense", { description: "Big Book " + i, amount: "16" }, "books");
          const at = async (store, now) => { const x = make("en", Object.fromEntries(store), null, { now }); await tick(); return x; };
          const nov30 = await at(w.store, input.nov30);
          res.before = nov30.a.nudgeDue();
          nov30.a.nudgeLater();
          res.later = [nov30.a.nudgeDue(), nov30.store.get(KEY + ":backup-nudge")];
          res.dec01 = (await at(nov30.store, input.dec01)).a.nudgeDue();
          res.dec29 = (await at(nov30.store, input.dec29)).a.nudgeDue();
          const jan = await at(nov30.store, input.jan05);
          res.jan05 = jan.a.nudgeDue();
          // a CSV export is a copy: gone at once, and for the reminder's days
          jan.a.exportAll();
          res.afterCsv = jan.a.nudgeDue();
          // what the first version kept: the month
          const old = new Map(w.store); old.set(KEY + ":backup-nudge", "2026-11");
          res.oldMonth = [(await at(old, input.nov26)).a.nudgeDue(), (await at(old, input.dec03)).a.nudgeDue()];
          out(res);""", data={"nov26": NOV26, "nov30": NOV30, "dec01": DEC01, "dec03": DEC03, "dec29": DEC29,
                              "jan05": JAN05})
        self.assertTrue(r["before"])
        self.assertEqual(r["later"], [False, "2026-11-30"])
        self.assertFalse(r["dec01"], "put off on November 30: not back on December 1")
        self.assertFalse(r["dec29"], "29 days later: still quiet")
        self.assertTrue(r["jan05"], "36 days later: due again (still no copy)")
        self.assertFalse(r["afterCsv"], "a CSV export counts as a copy")
        self.assertEqual(r["oldMonth"], [False, True], "a kept month counts from its first day")

    def test_a_browser_that_refuses_storage(self):
        r = app(self, r"""
          const w = make("es", null, null, { now: input.nov });
          await tick();
          for (let i = 0; i < 5; i++) add(w, "expense", { description: "Libro Grande " + i, amount: "16" }, "books");
          const before = w.a.nudgeDue();
          w.setFull(true);
          let err = null;
          try { w.a.nudgeLater(); } catch (e) { err = String(e); }
          out({ before, err, after: w.a.nudgeDue(), storageOk: w.a.storageOk });""", data={"nov": NOV26})
        self.assertTrue(r["before"])
        self.assertIsNone(r["err"])
        self.assertFalse(r["after"], "hidden for this visit")


class Page(unittest.TestCase):
    def test_the_row_and_its_words(self):
        page = (ROOT / "src" / "pages" / "tracker.njk").read_text(encoding="utf-8")
        row = page[page.index('<div class="xp-nudge"'):]
        row = row[:row.index("{#- the tab bar")]
        self.assertIn('x-show="nudgeDue()" x-cloak', row)
        self.assertNotIn('role="alert"', row)
        for bit in ('@click="exportAll()"', '@click="exportBackup()"', '@click="nudgeLater()"', '"expenses.nudge.title" | t(lang)',
                    '"expenses.nudge.text" | t(lang)', '"expenses.nudge.later" | t(lang)'):
            self.assertIn(bit, row)
        words = json.loads((ROOT / "src" / "_i18n" / "expenses.json").read_text(encoding="utf-8"))
        for k in ("expenses.nudge.title", "expenses.nudge.text", "expenses.nudge.later"):
            self.assertTrue(words[k]["en"] and words[k]["es"] and words[k]["en"] != words[k]["es"], k)
        js = (ROOT / "src" / "assets" / "js" / "expenses.js").read_text(encoding="utf-8")
        self.assertIn('var NUDGE_KEY = KEY + ":backup-nudge";', js)
        self.assertIn("try { seen = window.localStorage.getItem(NUDGE_KEY); } catch (e)", js)
        self.assertIn("try { window.localStorage.setItem(NUDGE_KEY, today()); } catch (e)", js)


if __name__ == "__main__":
    unittest.main()
