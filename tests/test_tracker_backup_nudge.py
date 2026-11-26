"""The Tracker's monthly "keep a copy" nudge (src/pages/tracker.njk .xp-nudge, src/assets/js/expenses.js nudgeDue /
nudgeLater, src/_i18n/expenses.json expenses.nudge.*): everything the Tracker holds lives only in the browser, so once
a month it offers a CSV export and the full backup, in one quiet row above the tabs.

  * When      — never on an empty ledger; once the ledger has an entry and no copy was made within the backup
                reminder's days (Settings → Reminders, 30 by default) — a CSV export counts as much as a full backup —;
                never while saving fails (the storage alert says more then).
  * Not now   — puts it off until the next month: the month ("2026-11") is kept in localStorage
                ("gv-expenses:v1:backup-nudge"); next month it comes back; a browser that refuses storage hides it
                for the visit only, without an error.
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
DEC03 = 1796299200000          # 2026-12-03T12:00:00Z
JAN05 = 1799150400000          # 2027-01-05T12:00:00Z


class Nudge(unittest.TestCase):
    def test_when_it_shows_and_not_now(self):
        r = app(self, r"""
          const res = {};
          const w = make("en", null, null, { now: input.nov });
          await tick();
          res.empty = w.a.nudgeDue();
          add(w, "expense", { description: "Big Book", amount: "16" }, "books");
          res.first = w.a.nudgeDue();
          w.a.nudgeLater();
          res.later = [w.a.nudgeDue(), w.store.get(KEY + ":backup-nudge")];
          // the same browser in December: it comes back (the ledger has still no copy)
          const dec = make("en", Object.fromEntries(w.store), null, { now: input.dec });
          await tick();
          res.december = dec.a.nudgeDue();
          // a CSV export is a copy: gone at once, and for the reminder's days
          dec.a.exportAll();
          res.afterCsv = dec.a.nudgeDue();
          const jan = make("en", Object.fromEntries(dec.store), null, { now: input.jan });
          await tick();
          res.january = jan.a.nudgeDue();
          out(res);""", data={"nov": NOV26, "dec": DEC03, "jan": JAN05})
        self.assertFalse(r["empty"], "never on an empty ledger")
        self.assertTrue(r["first"], "an entry and no copy yet")
        self.assertEqual(r["later"], [False, "2026-11"])
        self.assertTrue(r["december"], "Not now lasts until the next month")
        self.assertFalse(r["afterCsv"], "a CSV export counts as a copy")
        self.assertTrue(r["january"], "33 days later: due again")

    def test_a_browser_that_refuses_storage(self):
        r = app(self, r"""
          const w = make("es", null, null, { now: input.nov });
          await tick();
          add(w, "expense", { description: "Libro Grande", amount: "16" }, "books");
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
        self.assertIn("try { window.localStorage.setItem(NUDGE_KEY, today().slice(0, 7)); } catch (e)", js)


if __name__ == "__main__":
    unittest.main()
