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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import common  # noqa: E402
from scripts.sync import youtube as Y  # noqa: E402
from workflow_steps import step_code  # noqa: E402

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


class BotCheckDays(unittest.TestCase):
    """An occasional day on which YouTube turns the runner away is a WARNING, never a failure: Website update's run
    summary ("Write run summary", .github/workflows/update.yml) shows a yellow ::warning and a Notes line, the source
    stays ok (the feeds worked), its videos keep their last known details (Runs above), and nothing goes into the
    report job's `health` — no "A content source has stopped updating" issue. Even a day on which the feeds fail
    too (the source not ok) is only a warning: the issue waits for 7 days without a success. The warning is only
    for a run that asked YouTube itself (its `attempted` is not older than the run's STARTED): a quick or morning
    run, which never reads it, keeps the last full update's note under "Notes" only."""

    def summary(self, youtube: dict, started: str | None = None) -> tuple[str, str, dict]:
        import os
        import subprocess
        import yaml
        wf = yaml.safe_load((ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8"))
        step = next(s for s in wf["jobs"]["sync"]["steps"] if s.get("name") == "Write run summary")
        code = step_code(step["run"])
        tmp = Path(tempfile.mkdtemp(prefix="gv-yt-summary-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "data" / "site").mkdir(parents=True)
        status = {"fixture": False, "sources": [{"source": "youtube", "label": "YouTube videos", **youtube}]}
        (tmp / "data" / "site" / "status.json").write_text(json.dumps(status), encoding="utf-8")
        (tmp / "script.py").write_text(code, encoding="utf-8")
        env = dict(os.environ, GITHUB_STEP_SUMMARY=str(tmp / "summary.md"), GITHUB_OUTPUT=str(tmp / "out.txt"),
                   PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
        env.pop("STARTED", None)
        if started is not None:
            env["STARTED"] = started
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        health = json.loads((tmp / "out.txt").read_text(encoding="utf-8").split("health=", 1)[1])
        return (tmp / "summary.md").read_text(encoding="utf-8"), r.stdout, health

    def test_a_bot_check_day_is_a_warning(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        started = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 600, timezone.utc)
        summary, printed, health = self.summary({"ok": True, "updated": now, "attempted": now, "count": 553,
                                                 "stats": {"warnings": [PLAIN_BOT]}},
                                                started=started.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertIn(f"::warning title=YouTube videos::{PLAIN_BOT}", printed)
        self.assertIn("| YouTube videos | OK | 553 |", summary)
        self.assertIn(f"- YouTube videos: {PLAIN_BOT}", summary)
        self.assertNotIn("PROBLEM", summary)
        self.assertEqual(health["stale"], [], "no issue")
        # another note of a source that still worked stays a note (no annotation)
        _s, printed, _h = self.summary({"ok": True, "updated": now, "attempted": now, "count": 553,
                                        "stats": {"warnings": ["playlist feeds stopped early (YouTube not answering)"]}})
        self.assertNotIn("::warning", printed)

    def test_only_a_run_that_asked_youtube_warns(self):
        # the nightly full update met the bot check; the midday refresh, hours later, never asked YouTube: the note
        # it carries (status.json keeps the full update's stats and `attempted`) stays under "Notes", no warning
        night = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 9 * 3600, timezone.utc)
        midday = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 120, timezone.utc)
        row = {"ok": True, "updated": night.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "attempted": night.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": 553, "stats": {"warnings": [PLAIN_BOT]}}
        summary, printed, health = self.summary(row, started=midday.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertEqual([ln for ln in printed.splitlines() if ln.startswith("::warning")], [])
        self.assertIn(f"- YouTube videos: {PLAIN_BOT}", summary, "still a note")
        self.assertIn("| YouTube videos | OK | 553 |", summary)
        self.assertEqual(health["stale"], [])
        # the full update itself (it started before it asked YouTube) shows it
        _s, printed, _h = self.summary(row, started=(night - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertIn(f"::warning title=YouTube videos::{PLAIN_BOT}", printed)
        # a run on a computer (no STARTED): shown, as before
        _s, printed, _h = self.summary(row)
        self.assertIn(f"::warning title=YouTube videos::{PLAIN_BOT}", printed)

    def test_a_day_without_the_feeds_too_is_still_only_a_warning(self):
        yesterday = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 86400, timezone.utc)
        y = yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")
        summary, printed, health = self.summary({"ok": False, "updated": y, "attempted": y, "count": 553,
                                                 "error": "channel RSS UC…: HTTP 500"})
        self.assertIn("::warning title=YouTube videos::channel RSS UC…: HTTP 500 (previous items kept)", printed)
        self.assertNotIn("::error", printed)
        self.assertEqual(health["stale"], [], "the issue waits for 7 days without a success")


if __name__ == "__main__":
    unittest.main()
