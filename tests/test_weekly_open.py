"""scripts/sync/weekly_open.py — the Grapevine Weekly Open AA Meeting page (join details) → data/raw/weekly_open.json.

Saved pages in tests/fixtures/weekly_open/ (offline — nothing here goes to the network), shaped like
https://www.aagrapevine.org/grapevine-weekly-open:
  gv_weekly_open.html            the page as it reads today: "…Wednesdays at Noon Eastern, use Zoom code 871 2036 8287
                                 with password 238047", the page's blurb and the podcast player
  gv_weekly_open_protected.html  the join sentence written another way: "…password protected; the passcode is 238047"
                                 (the word after "password" is not the code — review item P1-10), a Zoom link
Run:  python -m unittest tests.test_weekly_open -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import common  # noqa: E402
from scripts.sync import weekly_open as W  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "weekly_open"
URL = "https://www.aagrapevine.org/grapevine-weekly-open"


def page(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class SavedPages(unittest.TestCase):
    def test_the_page_as_it_reads(self):
        p = W.parse_page(page("gv_weekly_open.html"), URL)
        self.assertEqual(p["title"], "Grapevine Weekly Open AA Meeting")
        self.assertEqual((p["zoom_id"], p["zoom_url"]), ("871 2036 8287", "https://zoom.us/j/87120368287"))
        self.assertEqual(p["passcode"], "238047")
        self.assertEqual((p["day"], p["weekday"], p["weekday_num"]), ("Wednesdays", "wednesday", 2))
        self.assertEqual((p["time"], p["clock"], p["timezone"]), ("Noon Eastern", (12, 0), "America/New_York"))
        self.assertEqual(p["player_url"], "https://player.captivate.fm/show/ba06341c-a708-43df-a334-1cc9f7266f63")
        self.assertTrue(p["sentence"].startswith("To join the meeting live on Wednesdays at Noon Eastern"))
        self.assertTrue(p["summary"].startswith("Each week AA Grapevine holds an open virtual AA meeting"))

    def test_password_protected_then_the_passcode(self):
        """P1-10: "This meeting is password protected; the passcode is 238047" — the first word after "password"
        is "protected" (what the page would have shown as the passcode); the code is the one with digits."""
        p = W.parse_page(page("gv_weekly_open_protected.html"), URL)
        self.assertEqual(W.PASS_RE.search(p["sentence"])[1], "protected")      # the trap is really in the page
        self.assertEqual(p["passcode"], "238047")
        self.assertEqual(p["zoom_id"], "871 2036 8287")
        self.assertEqual((p["time"], p["clock"]), ("12:00 PM Eastern", (12, 0)))
        self.assertEqual(p["title"], "Grapevine Weekly Open AA Meeting")        # its <title>: there is no og:title

    def test_the_item_and_its_central_time(self):
        it = W.build_item(W.parse_page(page("gv_weekly_open.html"), URL), URL)
        ex = it["extra"]
        self.assertEqual((it["id"], it["kind"], it["lang"]), ("weekly_open", "meeting", "en"))
        self.assertEqual((ex["start_local"], ex["time_central"]), ("12:00", "11 AM Central"))
        start = datetime.fromisoformat(ex["next_start"].replace("Z", "+00:00"))
        self.assertEqual(start.weekday(), 2)                                     # a Wednesday …
        self.assertIn(start.astimezone(timezone.utc).hour, (16, 17))            # … at noon Eastern (EDT / EST)
        self.assertGreater(start, datetime.now(timezone.utc))


class Passcode(unittest.TestCase):
    def test_a_code_with_digits_wins(self):
        self.assertEqual(W.find_passcode("This meeting is password protected; the passcode is 238047"), "238047")
        self.assertEqual(W.find_passcode("Passcode: 238047"), "238047")
        self.assertEqual(W.find_passcode("Reunión protegida. Contraseña: neta65"), "neta65")
        self.assertEqual(W.find_passcode("password required", "Zoom code 871 2036 8287, passcode 238047"), "238047")

    def test_a_word_of_the_sentence_is_never_the_code(self):
        self.assertIsNone(W.find_passcode("This meeting is password protected."))
        self.assertIsNone(W.find_passcode("A passcode is required to join."))
        self.assertIsNone(W.find_passcode("No details here"))

    def test_a_code_of_letters_only(self):
        self.assertEqual(W.find_passcode("Passcode: Serenity"), "Serenity")
        self.assertEqual(W.find_passcode("password protected — passcode: Serenity"), "Serenity")


class Run(unittest.TestCase):
    """main() over the saved pages: the envelope it writes (data/raw redirected to a temporary folder)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-test-"))
        p = mock.patch.object(common, "RAW_DIR", self.tmp)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_main(self, html: str) -> dict:
        f = self.tmp / "page.html"
        f.write_text(html, encoding="utf-8")
        W.main(["--html", str(f)])
        return json.loads((self.tmp / "weekly_open.json").read_text(encoding="utf-8"))

    def test_written_with_la_vina_second(self):
        env = self.run_main(page("gv_weekly_open.html"))
        self.assertTrue(env["ok"])
        self.assertEqual(env["stats"]["missing"], [])
        gv = env["items"][0]
        self.assertEqual(gv["id"], "weekly_open")                    # always first: templates read items[0]
        self.assertEqual((gv["extra"]["zoom_id"], gv["extra"]["passcode"]), ("871 2036 8287", "238047"))
        # then La Viña's meeting (config/site.yml lavina_weekly_open), when the settings show one
        self.assertIn([i["id"] for i in env["items"]][1:], ([], ["weekly_open_lv"]))

    def test_a_join_detail_missing_today_keeps_yesterdays(self):
        self.run_main(page("gv_weekly_open.html"))
        no_code = page("gv_weekly_open.html").replace(" with password 238047", "")
        env = self.run_main(no_code)
        self.assertTrue(env["ok"])
        self.assertEqual(env["stats"]["missing"], ["passcode"])
        self.assertEqual(env["stats"]["kept_from_previous"], ["passcode"])
        self.assertEqual(env["items"][0]["extra"]["passcode"], "238047")

    def test_a_page_that_changed_shape_keeps_the_item(self):
        self.run_main(page("gv_weekly_open.html"))
        env = self.run_main("<html><body><main><h1>Page not found</h1></main></body></html>")
        self.assertFalse(env["ok"])
        self.assertIn("could not find the Zoom ID or meeting day", env["error"])
        self.assertEqual(env["items"][0]["extra"]["passcode"], "238047")


if __name__ == "__main__":
    unittest.main()
