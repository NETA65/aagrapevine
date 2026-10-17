"""YouTube's bot check in plain words (scripts/sync/youtube.py bot_check_note): when YouTube turns the runner
away ("Sign in to confirm you're not a bot", a captcha, a rate limit), /status/ says that nothing is wrong on
our side and that the videos keep what they had — once, not once per tab or playlist. No network: yt-dlp
and the feeds are faked.
Run:  python -m unittest tests.test_youtube -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import common  # noqa: E402
from scripts.sync import youtube as Y  # noqa: E402

CHANNEL = "UCI9uFLJ__aXT3-At0PlPWUQ"
# yt-dlp's texts after "ERROR: [youtube] <id>: " (the first one is what the Actions runner got in October 2026)
BOT = ("Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. "
       "See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies")
CAPTCHA = "This video is unavailable. YouTube is requiring a captcha challenge before playback"
TOO_MANY = "Unable to download API page: HTTP Error 429: Too Many Requests"
AGE = "Sign in to confirm your age. This video may be inappropriate for some users."
PLAIN_BOT = ("details stopped: YouTube answered with a bot check (“confirm you’re not a bot”) — nothing is wrong on "
             "our side; videos keep their last known details")


class Note(unittest.TestCase):
    def test_the_messages(self):
        self.assertEqual(Y.bot_check_note("details", f"ERROR: [youtube] daNbma33_to: {BOT}"), PLAIN_BOT)
        self.assertIn("a bot check", Y.bot_check_note("details", CAPTCHA))
        self.assertEqual(Y.bot_check_note("listing", TOO_MANY),
                         "listing stopped: YouTube answered with a rate limit (too many requests) — nothing is wrong "
                         "on our side; the last good list is kept")
        for other in (AGE, "TimeoutError: timed out after 60s", "", None):
            self.assertIsNone(Y.bot_check_note("details", other), other)

    def test_the_note_fits_the_status_page(self):
        for step in ("details", "listing"):
            for err in (BOT, TOO_MANY):
                self.assertLessEqual(len(Y.bot_check_note(step, err)), 200)


def video(vid: str, day: int) -> dict:
    """A stored video that still lacks its duration (so it is due for details)."""
    return {"id": f"yt:{vid}", "source": "youtube", "kind": "video", "url": f"https://www.youtube.com/watch?v={vid}",
            "title": f"Video {vid}", "summary": "", "lang": "en", "date": f"2026-09-{day:02d}T12:00:00Z",
            "first_seen": "2026-09-01T12:00:00Z", "last_seen": "2026-09-29T12:00:00Z", "image": None, "tags": [],
            "category": "gv", "status": "ok",
            "extra": {"video_id": vid, "channel_id": CHANNEL, "is_short": False, "playlists": [], "date_approx": False}}


class Runs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-yt-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.answer = BOT                         # what yt-dlp says to every request
        test = self

        class YoutubeDL:                          # ignoreerrors=True: a failure goes to the logger, the answer is None
            def __init__(self, opts):
                self.logger = opts["logger"]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def extract_info(self, url, download=False, process=False):
                self.logger.error(f"ERROR: [youtube] {url.rsplit('/', 1)[-1][-11:]}: {test.answer}")
                return None

            def close(self):
                pass

        for p in (mock.patch.object(common, "RAW_DIR", self.tmp),
                  mock.patch.object(Y, "load_config", lambda: {"sources": {"youtube": {"channels": [{"id": CHANNEL}]}}}),
                  mock.patch.object(Y, "fetch_feed", lambda _http, _url: ([], 200)),
                  mock.patch.object(Y, "probe_is_short", lambda _http, _vid: False),
                  mock.patch.object(Y, "_ytdlp", lambda: SimpleNamespace(YoutubeDL=YoutubeDL))):
            p.start()
            self.addCleanup(p.stop)
        env = {"items": [video("OVern6mSBrk", 29), video("Yf5SFhLiBwc", 25)], "detail_fails": {},
               "backfilled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        (self.tmp / "youtube.json").write_text(json.dumps(env), encoding="utf-8")

    def run_sync(self, *args: str) -> dict:
        Y.main(list(args))
        return json.loads((self.tmp / "youtube.json").read_text(encoding="utf-8"))

    def test_the_detail_step_says_it_plainly_and_keeps_the_videos(self):
        env = self.run_sync("--no-backfill")
        self.assertTrue(env["ok"])
        self.assertEqual(env["stats"]["warnings"], [PLAIN_BOT])
        self.assertEqual({i["id"] for i in env["items"]}, {"yt:OVern6mSBrk", "yt:Yf5SFhLiBwc"})
        self.assertTrue(all(i["status"] == "ok" for i in env["items"]))

    def test_the_listing_says_it_once(self):
        """Every tab and the playlists meet the bot check: one plain line, not four "yt-dlp …" ones."""
        env = self.run_sync("--backfill", "--details", "0")
        listing = [w for w in env["stats"]["warnings"] if w.startswith("listing stopped:")]
        self.assertEqual(listing, ["listing stopped: YouTube answered with a bot check (“confirm you’re not a bot”) — "
                                   "nothing is wrong on our side; the last good list is kept"])
        self.assertFalse([w for w in env["stats"]["warnings"] if "not a bot" in w and w.startswith("yt-dlp")])
        self.assertEqual(len(env["items"]), 2, "the stored videos stay")

    def test_another_error_keeps_its_own_words(self):
        self.answer = "Unable to extract initial player response"
        env = self.run_sync("--no-backfill")
        self.assertFalse(any("YouTube answered" in w for w in env["stats"].get("warnings", [])))


if __name__ == "__main__":
    unittest.main()
