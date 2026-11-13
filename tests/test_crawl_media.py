"""One bad answer must not stick: the PDF crawler's error pages (scripts/sync/crawl.py) and YouTube's
per-video details (scripts/sync/youtube.py). Offline: download_pdf, the feeds, oEmbed and yt-dlp are
faked; data/raw goes to a temporary folder.

    python -m unittest tests.test_crawl_media -v        (or: python -m unittest discover -s tests)
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
from scripts.sync import crawl as C  # noqa: E402
from scripts.sync import youtube as Y  # noqa: E402

HUB = "https://www.aagrapevine.org/gvr-resources"
NEW_PDF = "https://www.aagrapevine.org/sites/default/files/2026-10/GVR_Kit_2026.pdf"
# a real kind of record: no upload-month folder, so its date is the file's Last-Modified
AA_PDF = "https://www.aa.org/sites/default/files/literature/Retrofit_Completion_Return_to_Office.pdf"


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def crawler() -> C.Crawler:
    st = {"pages": {}, "pdfs": {}, "sitemaps": {}, "runs": []}
    with mock.patch.object(C, "shared_session", lambda: None):
        return C.Crawler(st, minutes=1, details_cap=5, recheck_days=21, max_mb=5, max_pages=None,
                         dry_run=True, only_urls=None, use_sitemap=False)


# --------------------------------------------------------------------------- crawl.py
class PdfDetailsAfterOneBadAnswer(unittest.TestCase):
    """fetch_details(): a 404 / an HTML page on a PDF's download is a strike like any failing check —
    never a final answer while the PDF is not confirmed gone."""

    def download(self, status: int, ctype: str, err: str):
        now = iso(datetime.now(timezone.utc))
        head = {"status": status, "type": ctype, "size": 18000, "last_modified": now, "checked_at": now}
        return mock.patch.object(C, "download_pdf", lambda *a, **k: (dict(head), None, err, True))

    def new_pdf(self, cr: C.Crawler, **kw) -> dict:
        rec = cr.pdfs["k"] = {"url": NEW_PDF, "status": "ok", "refs": [{"url": HUB}], "external": False, **kw}
        return rec

    def test_a_first_not_found_is_retried_once_the_file_answers(self):
        # e.g. a page links the file minutes before it is uploaded, or the download hits a site deploy
        for status, err in ((404, "http 404"), (410, "http 410"), (200, "not-pdf")):
            with self.subTest(err=err):
                cr = crawler()
                rec = self.new_pdf(cr)
                with self.download(status, "text/html", err):
                    cr.fetch_details("k", rec)
                d = rec["details"]
                self.assertNotIn("final", d)
                self.assertEqual((d["error"], d["attempts"]), (err, 1))
                self.assertEqual(rec["status"], "ok")
                self.assertIn("gone_strike_at", rec)
                now = datetime.now(timezone.utc)
                self.assertFalse(cr.needs_details(rec, now + timedelta(days=1)), "the normal back-off")
                cr._apply_head(rec, {"status": 200, "type": "application/pdf", "size": 250000})   # the next day's check
                self.assertEqual(rec["status"], "ok")
                self.assertTrue(cr.needs_details(rec, now + timedelta(days=3)),
                                "downloaded again: thumbnail, page count, heading, text language")

    def test_a_confirmed_gone_pdf_is_not_downloaded_again(self):
        cr = crawler()
        rec = self.new_pdf(cr, gone_strike_at=iso(datetime.now(timezone.utc) - timedelta(hours=30)))
        with self.download(404, "text/html", "http 404"):          # the second failing check, a day later
            cr.fetch_details("k", rec)
        self.assertEqual(rec["status"], "gone")
        self.assertTrue(rec["details"]["final"])
        self.assertFalse(cr.needs_details(rec, datetime.now(timezone.utc) + timedelta(days=60)))

    def test_what_is_not_a_pdf_stays_final(self):
        cr = crawler()
        hint = cr.pdfs["k"] = {"url": "https://www.aagrapevine.org/node/123/download", "status": "ok", "hint": True,
                               "refs": [{"url": HUB}], "external": False}
        with self.download(200, "text/html", "not-pdf"):           # a link that only looked like a file
            cr.fetch_details("k", hint)
        self.assertEqual(hint["status"], "not-pdf")
        self.assertTrue(hint["details"]["final"])
        cr = crawler()
        rec = self.new_pdf(cr)
        with self.download(200, "application/octet-stream", "not-pdf"):   # a file, but no PDF in it
            cr.fetch_details("k", rec)
        self.assertTrue(rec["details"]["final"])


class PdfErrorPages(unittest.TestCase):
    """_apply_head(): an error / HTML page where the PDF was is not the file — its Last-Modified and
    Content-Length never become the PDF's date (What's New) and size."""
    FILE = {"status": 200, "type": "application/pdf", "size": 250000, "last_modified": "2026-03-31T09:00:00Z",
            "checked_at": "2026-09-01T00:00:00Z"}

    def record(self) -> dict:
        return {"url": AA_PDF, "status": "ok", "external": True, "head": dict(self.FILE),
                "refs": [{"url": "https://www.aa.org/gso-updates", "title": "GSO updates", "texts": ["Retrofit completion"]}]}

    def test_an_error_page_never_redates_the_pdf(self):
        for status, size_bytes in ((404, None), (410, None), (200, 250000), (503, None)):
            with self.subTest(status=status):
                cr, rec = crawler(), self.record()
                self.assertEqual(C.build_item("k", rec, {}, set())["date"], "2026-03-31")
                cr._apply_head(rec, {"status": status, "type": "text/html", "size": 18000,
                                     "last_modified": "2026-10-30T12:00:00Z", "checked_at": "2026-10-30T12:00:00Z"})
                self.assertEqual(rec["status"], "ok", "one failing check is only a strike")
                it = C.build_item("k", rec, {}, set())
                self.assertEqual(it["date"], "2026-03-31", "not the error page's date")
                self.assertEqual(it["extra"]["size_bytes"], size_bytes, "never the error page's size")
                self.assertEqual(rec["head"]["status"], status)

    def test_a_second_failing_check_still_keeps_the_files_date(self):
        # e.g. the first strike's 404, then an outage page at the confirming check: the PDF is still "ok",
        # and a "fresh" one without an upload-month folder would fall back to first_seen → New again
        for answers in ((404, 503), (503, 404), (503, 503), (200, 503), (404, 404), (200, 200)):
            with self.subTest(answers=answers):
                cr, rec = crawler(), {**self.record(), "fresh": True, "first_seen": "2026-10-25T12:00:00Z"}
                for status in answers:
                    cr._apply_head(rec, {"status": status, "type": "text/html", "size": 18000,
                                         "last_modified": "2026-10-30T12:00:00Z"})
                self.assertEqual(rec["status"], "ok", "the strike is not a day old: not confirmed gone")
                self.assertEqual(C.build_item("k", rec, {}, set())["date"], "2026-03-31")
                self.assertEqual((rec["head"]["size"], rec["head"]["last_modified"]),
                                 (self.FILE["size"], self.FILE["last_modified"]), "the file's last known ones")

    def test_the_file_itself_still_updates_its_date(self):
        cr, rec = crawler(), self.record()
        cr._apply_head(rec, {"status": 404, "type": "text/html", "last_modified": "2026-10-30T12:00:00Z"})
        cr._apply_head(rec, {"status": 200, "type": "application/pdf", "size": 260000,
                             "last_modified": "2026-10-31T08:00:00Z"})                  # a new upload
        it = C.build_item("k", rec, {}, set())
        self.assertEqual((it["date"], it["extra"]["size_bytes"]), ("2026-10-31", 260000))
        self.assertNotIn("gone_strike_at", rec)


# --------------------------------------------------------------------------- youtube.py
CHANNEL = "UCI9uFLJ__aXT3-At0PlPWUQ"
LOGIN = ("Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/"
         "wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies")
# yt-dlp's own texts (2026.08.19, extractor/youtube/_video.py) after "ERROR: [youtube] <id>: "
BOT = f"Sign in to confirm you’re not a bot. {LOGIN}"
AGE = f"Sign in to confirm your age. This video may be inappropriate for some users. {LOGIN}"
RATE = ("Video unavailable. This content isn't available, try again later. The current session has been "
        "rate-limited by YouTube for up to an hour.")
CAPTCHA = "This video is unavailable. YouTube is requiring a captcha challenge before playback"
TOO_MANY = "Unable to download API page: HTTP Error 429: Too Many Requests"
READ_TIMEOUT = "Unable to download API page: The read operation timed out (caused by TransportError('The read operation timed out'))"
EXTRACT = "Unable to extract initial player response; please report this issue on  https://github.com/yt-dlp/yt-dlp/issues"


def video(vid: str, day: int) -> dict:
    """A stored video that still lacks its duration (so it is due for details)."""
    return {"id": f"yt:{vid}", "source": "youtube", "kind": "video", "url": f"https://www.youtube.com/watch?v={vid}",
            "title": f"Video {vid}", "summary": "", "lang": "en", "date": f"2026-09-{day:02d}T12:00:00Z",
            "first_seen": "2026-09-01T12:00:00Z", "last_seen": "2026-09-29T12:00:00Z", "image": None, "tags": [],
            "category": "gv", "status": "ok",
            "extra": {"video_id": vid, "channel_id": CHANNEL, "is_short": False, "playlists": [], "date_approx": False}}


class YouTubeDetails(unittest.TestCase):
    """Step 5 of youtube.main(): YouTube turning the runner away (bot check, captcha, rate limit, a
    time-out) stops the details for the run but never counts against a video's MAX_DETAIL_FAILS tries;
    a per-video failure (age gate, extractor error) is still counted and capped."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.answers: dict[str, object] = {}      # video id → an error text or an exception (default: a normal answer)
        self.asked: list[str] = []
        self.oembed: list[str] = []
        test = self

        class YoutubeDL:                          # ignoreerrors=True: a failure goes to the logger, the answer is None
            def __init__(self, opts):
                self.logger = opts["logger"]

            def extract_info(self, url, download=False, process=False):
                vid = url.rsplit("=", 1)[-1]
                test.asked.append(vid)
                answer = test.answers.get(vid)
                if isinstance(answer, BaseException):
                    raise answer
                if answer:
                    self.logger.error(f"ERROR: [youtube] {vid}: {answer}")
                    return None
                return {"id": vid, "title": f"Video {vid}", "timestamp": 1790000000, "duration": 1925,
                        "description": "The full description.", "language": "en"}

            def close(self):
                pass

        def oembed(_http, vid):
            self.oembed.append(vid)
            return 200
        for p in (mock.patch.object(common, "RAW_DIR", self.tmp),
                  mock.patch.object(Y, "load_config", lambda: {"sources": {"youtube": {"channels": [{"id": CHANNEL}]}}}),
                  mock.patch.object(Y, "fetch_feed", lambda _http, _url: ([], 200)),
                  mock.patch.object(Y, "probe_is_short", lambda _http, _vid: False),
                  mock.patch.object(Y, "oembed_status", oembed),
                  mock.patch.object(Y, "_ytdlp", lambda: SimpleNamespace(YoutubeDL=YoutubeDL))):
            p.start()
            self.addCleanup(p.stop)

    def store(self, *videos: dict, fails: dict | None = None) -> None:
        env = {"items": list(videos), "detail_fails": fails or {}, "backfilled_at": iso(datetime.now(timezone.utc))}
        (self.tmp / "youtube.json").write_text(json.dumps(env), encoding="utf-8")

    def run_sync(self) -> dict:
        self.asked.clear()
        Y.main(["--no-backfill"])
        return json.loads((self.tmp / "youtube.json").read_text(encoding="utf-8"))

    def durations(self, env: dict) -> dict:
        return {i["id"][3:]: (i.get("extra") or {}).get("duration_sec") for i in env["items"]}

    def test_a_bot_check_never_uses_up_a_videos_tries(self):
        self.store(video("OVern6mSBrk", 29), video("Yf5SFhLiBwc", 25))
        self.answers = {"OVern6mSBrk": BOT, "Yf5SFhLiBwc": BOT}
        for _ in range(3):                        # three daily runs, every call bot-checked
            env = self.run_sync()
            self.assertEqual(self.asked, ["OVern6mSBrk"], "the run stops at the first bot check")
            self.assertEqual(env["detail_fails"], {})
            self.assertTrue(any("details stopped" in w and "not a bot" in w for w in env["stats"]["warnings"]))
        self.assertEqual(self.oembed, [], "a bot check is not a deleted video")
        self.answers = {}                         # yt-dlp works again: every video gets its details
        env = self.run_sync()
        self.assertEqual(self.asked, ["OVern6mSBrk", "Yf5SFhLiBwc"])
        self.assertEqual(self.durations(env), {"OVern6mSBrk": 1925, "Yf5SFhLiBwc": 1925})
        self.assertNotIn("warnings", env["stats"])

    def test_the_runner_turned_away_or_timed_out_stops_the_run_uncounted(self):
        for answer in (RATE, CAPTCHA, TOO_MANY, READ_TIMEOUT, TimeoutError("timed out after 60s")):
            with self.subTest(answer=str(answer)[:40]):
                self.store(video("aaaaaaaaaaa", 29), video("bbbbbbbbbbb", 25))
                self.answers = {"aaaaaaaaaaa": answer}
                env = self.run_sync()
                self.assertEqual(self.asked, ["aaaaaaaaaaa"])
                self.assertEqual(env["detail_fails"], {})
                self.assertTrue(any(w.startswith("details stopped:") for w in env["stats"]["warnings"]))

    def test_per_video_failures_are_still_counted_and_capped(self):
        # newest first: an age-restricted video, one whose ID holds "429" with an extractor error, a fine one
        self.store(video("ageGated001", 29), video("ab429cdefgh", 27), video("fineVideo01", 25))
        self.answers = {"ageGated001": AGE, "ab429cdefgh": EXTRACT}
        for n in (1, 2, 3):
            env = self.run_sync()
            self.assertEqual(self.asked, ["ageGated001", "ab429cdefgh"] + (["fineVideo01"] if n == 1 else []),
                             "a per-video failure does not stop the run")
            self.assertEqual(env["detail_fails"], {"ageGated001": n, "ab429cdefgh": n})
        self.assertEqual(self.durations(env)["fineVideo01"], 1925)
        self.run_sync()
        self.assertEqual(self.asked, [], f"after {Y.MAX_DETAIL_FAILS} failures a video is not asked again")

    def test_block_and_timeout_patterns(self):
        for text in (BOT, RATE, CAPTCHA, TOO_MANY):
            self.assertTrue(Y.DetailFetcher.BOT_CHECK.search(f"ERROR: [youtube] OVern6mSBrk: {text}"), text)
        for text in (AGE, EXTRACT, "Private video. Sign in if you've been granted access to this video"):
            self.assertFalse(Y.DetailFetcher.BOT_CHECK.search(f"ERROR: [youtube] ab429cdefgh: {text}"), text)
        for text in ("TimeoutError: timed out after 60s", READ_TIMEOUT, "Read timed out. (read timeout=20)"):
            self.assertTrue(Y.DetailFetcher.TIMEOUT.search(text), text)
        self.assertFalse(Y.DetailFetcher.TIMEOUT.search(f"ERROR: [youtube] xTimeoutabc: {EXTRACT}"))


if __name__ == "__main__":
    unittest.main()
