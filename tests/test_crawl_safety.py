"""A bad day at a source must not wipe or hide documents: the PDF crawler's safety rules
(scripts/sync/crawl.py, crawl_pdf.py) and robots.txt handling (common.PoliteSession).

  * one 404 from a hub / kit page keeps its documents filed (two strikes a day apart), hubs are asked
    again every day whatever they last answered, and the run reports the ones that did not load;
  * one timeout never marks a whole host down; a host down for the run costs its other documents
    nothing; robots.txt refusals are never "unreachable";
  * the PDF reader runs in a child process with a time (and, on Linux, memory) limit, and the attempt
    is recorded first;
  * robots.txt answered 5xx / not at all closes the host for now (RFC 9309), 4xx allows;
  * crawl-state.json forgets junk addresses and long-gone pages;
  * a document's day counts in Central time.

Offline: every session is faked (no network); nothing is written to data/.

    python -m unittest tests.test_crawl_safety -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import contextlib
import copy
import heapq
import io
import json
import sys
import tempfile
import time
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from scripts.sync import common  # noqa: E402
from scripts.sync import crawl as C  # noqa: E402
from scripts.sync import crawl_pdf as P  # noqa: E402
from scripts.sync import crawl_rules as R  # noqa: E402

KIT_FIXTURE = ROOT / "tests" / "fixtures" / "crawl" / "gvr-kit-state.json"
HUB = "https://www.aagrapevine.org/gvr-resources"
RLV_HUB = "https://www.aalavina.org/recursos"
NEWS_HUB = "https://www.aagrapevine.org/news-release"
PAGE = "https://www.aagrapevine.org/guidelines-contributing-grapevine"    # not a hub
OWN_PDF = "https://www.aagrapevine.org/sites/default/files/2026-10/GVR_Kit_2026.pdf"
AA_PDF = "https://www.aa.org/sites/default/files/literature/f-1_AAataGlance.pdf"
AA_PDF2 = "https://www.aa.org/sites/default/files/literature/p-1_ThisIsAA.pdf"
ON_LINUX = sys.platform.startswith("linux")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def now() -> datetime:
    return datetime.now(timezone.utc)


class Answer:
    """A minimal requests.Response stand-in (pages, PDFs, sitemaps)."""

    def __init__(self, status=200, url="https://x.test/", body=b"", ctype="text/html; charset=utf-8",
                 headers=None):
        self.status_code, self.url, self.content = status, url, body
        self.headers = {"Content-Type": ctype, **(headers or {})}
        self.encoding = "utf-8"
        self.text = body.decode("utf-8", "replace")
        self.is_redirect = False

    def iter_content(self, chunk_size=1):
        yield self.content

    def close(self):
        pass


class FakeSession:
    """Stands in for a PoliteSession: `answers` maps a URL to a list used up call by call — an Answer, or
    a PoliteSession.last_failure string ("unreachable", "robots", "robots-unavailable") for no response.
    `robots` = the robots.txt problem of every host ("HTTP 503", "unreachable") or None."""
    retries = 3

    def __init__(self, answers=None, robots=None):
        self.answers = {k: list(v) if isinstance(v, list) else [v] for k, v in (answers or {}).items()}
        self.robots = robots
        self.sent: list[tuple[str, str]] = []
        self.last_failure = None
        self.requests_made = 0

    def allowed(self, url):
        return self.robots is None

    def robots_problem(self, url):
        return self.robots

    def remembered(self, url):
        return None

    def request(self, method, url, **kw):
        if self.robots:
            self.last_failure = "robots-unreachable" if self.robots == "unreachable" else "robots-unavailable"
            return None
        self.sent.append((method, url))
        queue = self.answers.get(url) or ["unreachable"]
        a = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(a, str):
            self.last_failure = a
            return None
        self.last_failure = None
        self.requests_made += 1
        return a

    def get(self, url, **kw):
        return self.request("GET", url, **kw)


def crawler(st: dict | None = None, *, http=None, ext=None, dry_run=True, details_cap=5) -> C.Crawler:
    st = st or {"pages": {}, "pdfs": {}, "sitemaps": {}, "runs": []}
    with mock.patch.object(C, "shared_session", lambda: http):
        cr = C.Crawler(st, minutes=10, details_cap=details_cap, recheck_days=21, max_mb=5, max_pages=None,
                       dry_run=dry_run, only_urls=None, use_sitemap=False)
    if ext is not None:
        cr.ext = ext
    return cr


def kit_state() -> dict:
    return json.loads(KIT_FIXTURE.read_text(encoding="utf-8"))


def page_html(*pdf_urls: str, links=()) -> bytes:
    a = "".join(f'<a href="{u}">Document {i}</a>' for i, u in enumerate(pdf_urls))
    b = "".join(f'<a href="{u}">Page</a>' for u in links)
    return f"<html><head><title>GVR Resources</title></head><body><h2>Kit</h2>{a}{b}</body></html>".encode()


def pdf_bytes() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (612, 792), "white").save(buf, "PDF")
    return buf.getvalue()


# =========================================================================== P2-1: hubs and kit pages
class OneBadAnswerFromAKitPage(unittest.TestCase):
    """A page 404 needs TWO strikes at least a day apart before its PDF links are dropped (re-filed or
    orphaned); hubs are asked again every day whatever they last answered."""

    def test_a_single_404_keeps_every_kit_document_filed(self):
        # Replay on the real state of the GVR kit page (tests/fixtures/crawl/gvr-kit-state.json): before
        # this rule one 404 re-filed all 49 kit documents and orphaned 46 of them, for 60 days.
        st = kit_state()
        pg = st["pages"][HUB]
        before = C.build_items(st)
        self.assertEqual(Counter(i["category"] for i in before), Counter({"gvr": 49}))
        http = FakeSession({HUB: Answer(404, HUB)})
        cr = crawler(st, http=http)
        cr.crawl_page(HUB, pg)
        items = C.build_items(st)
        self.assertEqual(Counter(i["category"] for i in items), Counter({"gvr": 49}), "every kit document stays filed")
        self.assertFalse(any(i["extra"]["orphan"] for i in items))
        self.assertEqual(len(pg["pdfs"]), 49)
        self.assertEqual(pg["status"], 200, "the page keeps its last good state")
        self.assertEqual((pg["last_error"], pg["gone_strike_at"]), ("404", pg["error_since"]))
        # asked again at the next daily run (every hub, whatever it answered)
        nt = C._dt(pg["next_try"])
        self.assertLessEqual(nt, now() + timedelta(hours=C.HUB_RETRY_H, minutes=1))
        self.assertIsNone(cr.page_priority(HUB, pg, now()))
        self.assertEqual(cr.page_priority(HUB, pg, nt + timedelta(minutes=1))[0], 0)
        # the same 404 later the same day: still only one strike
        cr.crawl_page(HUB, pg)
        self.assertEqual(Counter(i["category"] for i in C.build_items(st)), Counter({"gvr": 49}))
        # a second 404 a day later confirms it: now (and only now) the links are dropped
        pg["gone_strike_at"] = iso(now() - timedelta(hours=25))
        cr.crawl_page(HUB, pg)
        self.assertEqual(pg["status"], "404")
        self.assertEqual(pg["pdfs"], [])
        items = C.build_items(st)
        self.assertEqual(sum(1 for i in items if i["extra"]["orphan"]), 46)
        self.assertLess(Counter(i["category"] for i in items)["gvr"], 49)
        # … and a confirmed-404 hub is still asked again at every run (not after 60 days)
        self.assertEqual(cr.page_priority(HUB, pg, now() + timedelta(hours=C.HUB_RETRY_H + 1))[0], 0)

    def test_an_answer_after_one_404_clears_the_strike(self):
        for answer in (Answer(200, HUB, page_html(OWN_PDF)), Answer(304, HUB)):
            with self.subTest(status=answer.status_code):
                st = {"pages": {HUB: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": iso(now()),
                                      "pdfs": [], "pv": C.PARSER_VERSION}}, "pdfs": {}}
                cr = crawler(st, http=FakeSession({HUB: [Answer(404, HUB), answer]}))
                pg = st["pages"][HUB]
                cr.crawl_page(HUB, pg)
                self.assertIn("gone_strike_at", pg)
                cr.crawl_page(HUB, pg)
                for k in ("gone_strike_at", "error_since", "last_error"):
                    self.assertNotIn(k, pg)
                self.assertEqual(pg["status"], 200)

    def test_an_ordinary_page_gets_the_confirming_check_the_next_day(self):
        crawled = iso(now() - timedelta(days=3))
        st = {"pages": {PAGE: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": crawled,
                               "pdfs": ["k"], "in_sitemap": True}},
              "pdfs": {"k": {"url": OWN_PDF, "status": "ok", "refs": [{"url": PAGE}]}}}
        cr = crawler(st, http=FakeSession({PAGE: Answer(404, PAGE)}))
        pg = st["pages"][PAGE]
        cr.crawl_page(PAGE, pg)
        self.assertEqual((pg["status"], pg["pdfs"], st["pdfs"]["k"]["refs"]), (200, ["k"], [{"url": PAGE}]))
        self.assertIsNone(cr.page_priority(PAGE, pg, now() + timedelta(hours=20)))
        self.assertEqual(cr.page_priority(PAGE, pg, now() + timedelta(hours=25))[:2], (1, -1),
                         "due early in the next day's run (not after recheck_days)")

    def test_a_strike_ends_when_the_page_turns_into_something_else(self):
        st = {"pages": {PAGE: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": iso(now() - timedelta(days=3)),
                               "pdfs": []}}, "pdfs": {}}
        login = Answer(200, "https://www.aagrapevine.org/user/login")
        cr = crawler(st, http=FakeSession({PAGE: [Answer(404, PAGE), login]}))
        pg = st["pages"][PAGE]
        cr.crawl_page(PAGE, pg)
        pg["next_try"] = None
        cr.crawl_page(PAGE, pg)
        self.assertEqual(pg["status"], "login")
        self.assertNotIn("gone_strike_at", pg)
        self.assertIsNone(cr.page_priority(PAGE, pg, now() + timedelta(days=2)), "the usual 30-day re-check")

    def test_a_page_that_never_answered_is_gone_at_once(self):
        st = {"pages": {PAGE: {"src": "link", "depth": 1, "crawled_at": None}}, "pdfs": {}}
        cr = crawler(st, http=FakeSession({PAGE: Answer(404, PAGE)}))
        cr.crawl_page(PAGE, st["pages"][PAGE])
        self.assertEqual(st["pages"][PAGE]["status"], "404", "no links to keep: no strike needed")
        self.assertNotIn("gone_strike_at", st["pages"][PAGE])

    def test_hubs_are_due_daily_whatever_they_last_answered(self):
        cr = crawler()
        t = now()
        two_days = iso(t - timedelta(days=2))
        for status in ("404", "410", "login", "offsite", "not-html", "robots", "400"):
            with self.subTest(status=status):
                self.assertEqual(cr.page_priority(HUB, {"status": status, "crawled_at": two_days}, t)[0], 0)
                self.assertIsNone(cr.page_priority(PAGE, {"status": status, "crawled_at": two_days}, t),
                                  "an ordinary page keeps the long error re-check delay")
        # a hub that failed is due again as soon as its (capped) next_try has passed
        failing = {"status": 200, "crawled_at": iso(t - timedelta(hours=2)), "error_since": iso(t - timedelta(hours=13)),
                   "next_try": iso(t - timedelta(minutes=5))}
        self.assertEqual(cr.page_priority(HUB, failing, t)[0], 0)
        self.assertIsNone(cr.page_priority(HUB, {**failing, "next_try": iso(t + timedelta(hours=3))}, t))
        self.assertIsNone(cr.page_priority(HUB, {"status": 200, "crawled_at": iso(t - timedelta(hours=2))}, t))

    def test_an_outage_never_pushes_a_hub_out_for_weeks(self):
        cr = crawler()
        hub, other = {"status": 200}, {"status": 200}
        for _ in range(5):                                  # five 503s in a row
            cr._fail(HUB, hub, 503)
            cr._fail(PAGE, other, 503)
        self.assertLessEqual(C._dt(hub["next_try"]), now() + timedelta(hours=C.HUB_RETRY_H, minutes=1))
        self.assertGreater(C._dt(other["next_try"]), now() + timedelta(days=15), "other pages: 1, 2, 4, 8, 16 days")
        self.assertEqual((hub["last_error"], hub["fails"]), ("503", 5))


class HubReport(unittest.TestCase):
    """The run records the hub / kit pages that did not load: data/raw/pdfs.json `hub_problems`
    [{url, status, since}] and one plain line in stats.warnings (the run summary's notes)."""

    def run_hubs(self):
        st = {"pages": {u: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": iso(now() - timedelta(days=1)),
                            "pdfs": [], "pv": C.PARSER_VERSION} for u in (HUB, RLV_HUB, NEWS_HUB)}, "pdfs": {}}
        st["pages"][RLV_HUB]["error_since"] = "2026-10-05T09:00:00Z"      # failing since yesterday
        http = FakeSession({HUB: Answer(404, HUB), RLV_HUB: Answer(503, RLV_HUB),
                            NEWS_HUB: Answer(200, NEWS_HUB, page_html())})
        cr = crawler(st, http=http)
        for u in (HUB, RLV_HUB, NEWS_HUB):
            cr.crawl_page(u, st["pages"][u])
        return st, cr

    def test_hubs_that_did_not_load_this_run(self):
        st, cr = self.run_hubs()
        report = cr.hub_report()
        self.assertEqual([(h["url"], h["status"]) for h in report], [(HUB, 404), (RLV_HUB, 503)])
        self.assertEqual(report[1]["since"], "2026-10-05T09:00:00Z", "since = when it began failing")
        self.assertEqual(report[0]["since"], st["pages"][HUB]["gone_strike_at"])
        lines = C.run_warnings(cr, report)
        self.assertEqual(len(lines), 1)
        self.assertIn("2 main page(s) of the magazine sites did not load: aagrapevine.org/gvr-resources (404 since",
                      lines[0])
        self.assertIn("aalavina.org/recursos (503 since 2026-10-05)", lines[0])
        self.assertLessEqual(len(lines[0]), 200)
        # a hub not asked for in this run is not reported, whatever its record says
        cr.tried.discard(RLV_HUB)
        self.assertEqual([h["url"] for h in cr.hub_report()], [HUB])

    def test_a_long_list_is_cut_to_one_summary_line(self):
        many = [{"url": u, "status": 503, "since": "2026-10-06T06:00:00Z"} for u in R.hub_urls()]
        lines = C.run_warnings(None, many)
        self.assertEqual(len(lines), 1)
        self.assertLessEqual(len(lines[0]), 200)
        self.assertTrue(lines[0].startswith(f"{len(many)} main page(s)"))

    def test_main_writes_them_into_the_envelope(self):
        st = {"version": 1, "updated": None, "sitemaps": {}, "runs": [], "pdfs": {},
              "pages": {HUB: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": iso(now() - timedelta(days=1)),
                              "pdfs": [], "pv": C.PARSER_VERSION}}}
        http = FakeSession({HUB: Answer(503, HUB)})

        def fake_run(self):
            self.crawl_page(HUB, self.pages[HUB])

        out = io.StringIO()
        with mock.patch.object(C, "shared_session", lambda: http), \
                mock.patch.object(C.Crawler, "run", fake_run), \
                mock.patch.object(C, "load_state", return_value=(st, True)), \
                mock.patch.object(C, "load_raw", return_value={"items": []}), \
                mock.patch.object(C, "save_state"), \
                mock.patch.object(C, "save_raw") as save_raw, \
                contextlib.redirect_stdout(out):
            C.main(["--minutes", "1", "--no-sitemap"])
        kw = save_raw.call_args.kwargs
        self.assertEqual(kw["extra"]["hub_problems"], [{"url": HUB, "status": 503, "since": st["pages"][HUB]["error_since"]}])
        self.assertIn("aagrapevine.org/gvr-resources (503 since", kw["stats"]["warnings"][0])
        self.assertTrue(kw["ok"], "a failing hub is a note, not a failed source")
        self.assertIn("note: 1 main page(s)", out.getvalue())

    def test_a_rebuild_without_network_reports_nothing(self):
        st = C.empty_state()
        with mock.patch.object(C, "load_state", return_value=(st, True)), \
                mock.patch.object(C, "load_raw", return_value={"items": []}), \
                mock.patch.object(C, "save_raw") as save_raw, \
                mock.patch.object(C, "print_summary"):
            C.main(["--minutes", "0"])
        kw = save_raw.call_args.kwargs
        self.assertEqual(kw["extra"]["hub_problems"], [])
        self.assertNotIn("warnings", kw["stats"])


# =========================================================================== P2-4: hosts that do not answer
class HostsThatDoNotAnswer(unittest.TestCase):
    """One timeout never marks a whole host down; while a host is down for the run its other documents
    wait for the next run (no "unreachable" strike without a request); robots.txt refusals are never
    "unreachable"."""

    def rec(self, url=AA_PDF, **kw) -> dict:
        return {"url": url, "status": "ok", "external": True, "refs": [{"url": "https://www.aa.org/x"}], **kw}

    def test_one_missed_answer_is_asked_again(self):
        ok = Answer(200, AA_PDF, ctype="application/pdf", headers={"Content-Length": "5000"})
        ext = FakeSession({AA_PDF: ["unreachable", ok]})
        cr = crawler(ext=ext)
        rec = cr.pdfs["k"] = self.rec()
        cr.fetch_head("k", rec)
        self.assertEqual(len(ext.sent), 2)
        self.assertEqual((rec["head"]["status"], rec["head"]["size"]), (200, 5000))
        self.assertNotIn("fails", rec["head"])
        self.assertEqual(cr.dead_hosts, set())

    def test_a_host_down_for_the_run_costs_its_other_documents_nothing(self):
        ext = FakeSession({AA_PDF: "unreachable", AA_PDF2: "unreachable"})
        cr = crawler(ext=ext)
        first = cr.pdfs["k1"] = self.rec(AA_PDF)
        second = cr.pdfs["k2"] = self.rec(AA_PDF2, head={"status": 200, "size": 9, "checked_at": "2026-08-01T00:00:00Z"})
        third = cr.pdfs["k3"] = self.rec("https://www.aa.org/sites/default/files/literature/p-2.pdf")
        cr.fetch_head("k1", first)
        self.assertEqual(len(ext.sent), 2, "asked twice before the host counts as down")
        self.assertEqual(cr.dead_hosts, {"www.aa.org"})
        self.assertEqual((first["head"]["error"], first["head"]["fails"]), ("unreachable", 1), "the real miss is a strike")
        before = copy.deepcopy((second, third))
        heapq.heappush(cr.pdf_q, ((3, 0, 0, "k2"), "periodic", "k2"))
        heapq.heappush(cr.pdf_q, ((0, 0, 0, "k3"), "details", "k3"))
        cr.do_pdf_task()
        cr.do_pdf_task()
        cr.fetch_head("k2", second)            # also when asked directly
        self.assertEqual(len(ext.sent), 2, "nothing more is sent to a host that is down")
        self.assertEqual((second, third), before, "no strike, nothing recorded: due again next run")
        self.assertEqual(cr.c["pdfs_requeued"], 3)
        self.assertEqual(cr.c["periodic_checks"], 0, "a skipped check does not use up the run's quota")
        self.assertEqual(cr.c["details"], 0)

    def test_one_miss_with_no_time_left_to_ask_again_is_no_verdict(self):
        ext = FakeSession({AA_PDF: "unreachable"})
        cr = crawler(ext=ext)
        cr.budget.limit = 20.0                 # the run is about to end
        rec = cr.pdfs["k"] = self.rec()
        cr.fetch_head("k", rec)
        self.assertEqual(len(ext.sent), 1)
        self.assertNotIn("head", rec, "no strike: asked again next run")
        self.assertEqual((cr.dead_hosts, cr.c["pdfs_requeued"]), (set(), 1))

    def test_robots_refusals_are_never_unreachable(self):
        ext = FakeSession({AA_PDF: "robots"})
        cr = crawler(ext=ext)
        rec = cr.pdfs["k"] = self.rec(head={"status": 200, "size": 7000, "last_modified": "2026-03-31T09:00:00Z",
                                            "checked_at": "2026-08-01T00:00:00Z"},
                                      details={"pages": 2, "checked_at": "2026-08-01T00:00:00Z"})
        for _ in range(8):                     # many runs: never retired
            cr.fetch_head("k", rec)
        self.assertEqual(rec["status"], "ok")
        self.assertEqual((rec["head"]["error"], rec["head"]["size"], rec["head"]["last_modified"]),
                         ("robots", 7000, "2026-03-31T09:00:00Z"))
        self.assertNotIn("fails", rec["head"])
        self.assertEqual(cr.dead_hosts, set())
        self.assertGreater(C._dt(rec["head"]["next_try"]), now() + timedelta(days=29))
        cr.push_pdf("k")
        self.assertEqual(cr.pdf_q, [], "not asked again before next_try")
        # the download (details) step likewise
        new = cr.pdfs["n"] = self.rec(AA_PDF)
        cr.fetch_details("n", new)
        self.assertEqual(new["details"]["error"], "robots")
        self.assertNotIn("fails", new["head"])

    def test_robots_unavailable_waits_for_the_next_run(self):
        ext = FakeSession(robots="HTTP 503")
        cr = crawler(ext=ext)
        rec = cr.pdfs["k"] = self.rec()
        cr.fetch_head("k", rec)
        cr.fetch_details("k", rec)
        self.assertEqual((rec.get("head"), rec.get("details")), (None, None))
        self.assertEqual((cr.c["pdfs_requeued"], cr.c["details"]), (2, 0))
        self.assertEqual(cr.dead_hosts, set())

    def test_with_a_real_session_one_timeout_then_an_answer(self):
        clock = FakeClock()
        calls = []
        script = {AA_PDF: [requests.Timeout("read timed out"), "ok"],
                  AA_PDF2: [requests.ConnectTimeout("x"), requests.ConnectTimeout("x")]}

        def fake_request(_self, method, url, **kw):
            calls.append(url)
            if url.endswith("/robots.txt"):
                return Answer(404, url)
            step = script[url].pop(0)
            if isinstance(step, Exception):
                raise step
            return Answer(200, url, ctype="application/pdf", headers={"Content-Length": "5000"})

        with mock.patch.object(common.time, "monotonic", clock.monotonic), \
                mock.patch.object(common.time, "sleep", clock.sleep), \
                mock.patch("requests.Session.request", fake_request):
            cr = crawler()                       # the real third-party session (retries=1)
            rec = cr.pdfs["k"] = self.rec(AA_PDF)
            cr.fetch_head("k", rec)
            self.assertEqual(rec["head"]["status"], 200)
            self.assertEqual(cr.dead_hosts, set(), "one timeout is not a dead host")
            rec2 = cr.pdfs["k2"] = self.rec(AA_PDF2)
            cr.fetch_head("k2", rec2)
            self.assertEqual(cr.dead_hosts, {"www.aa.org"})
            self.assertEqual(rec2["head"]["fails"], 1)
            n = len(calls)
            rec3 = cr.pdfs["k3"] = self.rec("https://www.aa.org/sites/default/files/x.pdf")
            cr.fetch_head("k3", rec3)
            self.assertEqual(len(calls), n, "no request to a host that is down")
            self.assertNotIn("head", rec3)

    def test_a_silent_robots_txt_on_the_magazine_sites_strikes_nothing(self):
        # robots.txt of the magazine server gives no answer (PoliteSession asked it twice): its pages AND
        # files wait for the next run — no "unreachable" strike for a file nobody asked for
        crawled = iso(now() - timedelta(days=40))
        st = {"pages": {PAGE: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": crawled, "pdfs": []}},
              "pdfs": {"old": {"url": OWN_PDF, "status": "ok", "refs": [{"url": HUB}], "external": False,
                               "head": {"status": 200, "size": 9, "checked_at": crawled}},
                       "new": {"url": OWN_PDF.replace("Kit", "Flyer"), "status": "ok", "refs": [{"url": HUB}],
                               "external": False}}}
        cr = crawler(st, http=FakeSession(robots="unreachable"))
        before = copy.deepcopy(st)
        heapq.heappush(cr.pdf_q, ((3, 0, 0, "old"), "periodic", "old"))
        heapq.heappush(cr.pdf_q, ((0, 0, 0, "new"), "details", "new"))
        cr.do_pdf_task()
        cr.do_pdf_task()
        self.assertEqual(cr.robots_down, {"www.aagrapevine.org": "unreachable"}, "noted also when only files met it")
        cr.crawl_page(PAGE, st["pages"][PAGE])
        self.assertEqual(st, before, "nothing recorded: no strike, no back-off, the page not marked")
        self.assertEqual((cr.c["pdfs_requeued"], cr.c["periodic_checks"], cr.c["details"]), (2, 0, 0))
        self.assertEqual(C.run_warnings(cr, []), ["robots.txt of www.aagrapevine.org did not answer properly "
                                                  "(no answer): its pages were left for the next run"])

    def test_with_real_sessions_a_silent_robots_txt(self):
        # aa.org: robots.txt asked twice, the file never, no pointless third try → down for the run, one
        # strike (a host that does not answer at all is retired after a month, as before); the magazine
        # site: its file waits for the next run
        clock = FakeClock()
        calls = []

        def fake_request(_self, method, url, **kw):
            calls.append(url)
            if url.endswith("/robots.txt"):
                clock.t += 15
                raise requests.ConnectTimeout("timed out")
            return Answer(200, url, ctype="application/pdf", headers={"Content-Length": "5000"})

        with mock.patch.object(common.time, "monotonic", clock.monotonic), \
                mock.patch.object(common.time, "sleep", clock.sleep), \
                mock.patch("requests.Session.request", fake_request):
            own = common.PoliteSession(min_delay=5.0, respect_robots=True)
            cr = crawler(http=own)
            rec = cr.pdfs["k"] = self.rec(AA_PDF)
            cr.fetch_head("k", rec)
            self.assertEqual(calls, ["https://www.aa.org/robots.txt"] * 2)
            self.assertEqual(cr.dead_hosts, {"www.aa.org"})
            self.assertEqual((rec["head"]["error"], rec["head"]["fails"]), ("unreachable", 1))
            mine = cr.pdfs["m"] = {"url": OWN_PDF, "status": "ok", "refs": [{"url": HUB}], "external": False}
            cr.fetch_head("m", mine)
            self.assertEqual(calls[2:], ["https://www.aagrapevine.org/robots.txt"] * 2)
            self.assertNotIn("head", mine, "no strike: due again next run")
            self.assertEqual(cr.last_failure, "robots-unavailable")
            self.assertEqual(cr.robots_down, {"www.aagrapevine.org": "unreachable"})


# =========================================================================== P2-8: the PDF reader
class PdfReaderInAChildProcess(unittest.TestCase):
    """A document that crashes or hangs the PDF reader costs that document (with a back-off), never the
    nightly run."""

    def child(self, code: str):
        return mock.patch.object(P, "_child_argv", lambda thumb, mem: [sys.executable, "-c", code])

    def test_a_real_pdf_is_read_in_a_child_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            thumb = Path(tmp) / "t.webp"
            a = P.analyze_pdf_isolated(pdf_bytes(), thumb, timeout=60)
            self.assertEqual((a["pages"], a["error"], a["thumb_written"]), (1, None, True))
            self.assertTrue(thumb.exists())
        bad = P.analyze_pdf_isolated(b"not a pdf at all", None, timeout=60)
        self.assertEqual((bad["error"], bad["final"]), ("invalid-pdf", True), "the reader's own answers come back")

    def test_the_memory_limit_leaves_a_normal_pdf_alone(self):
        # on Linux the child runs under RLIMIT_DATA (PARSE_MEMORY_MB); elsewhere the limit is skipped
        a = P.analyze_pdf_isolated(pdf_bytes(), None, timeout=60, memory_mb=P.PARSE_MEMORY_MB)
        self.assertEqual((a["pages"], a["error"]), (1, None))

    def test_a_reader_that_hangs_is_stopped(self):
        t0 = time.monotonic()
        with self.child("import time; time.sleep(120)"):
            a = P.analyze_pdf_isolated(b"%PDF-1.4", None, timeout=2)
        self.assertLess(time.monotonic() - t0, 30)
        self.assertEqual((a["error"], a["final"], a["pages"]), ("parse: no result after 2 s", False, None))

    def test_a_reader_that_crashes(self):
        for code, err in (("import os; os._exit(70)", "parse: crashed (exit code 70)"),
                          ("raise MemoryError", "parse: crashed (out of memory)"),
                          ("print('no json here')", "parse: no result"),
                          ("print('[1, 2]')", "parse: no result")):
            with self.subTest(code=code), self.child(code):
                a = P.analyze_pdf_isolated(b"%PDF-1.4", None, timeout=30)
                self.assertEqual((a["error"], a["final"]), (err, False))

    @unittest.skipUnless(ON_LINUX, "the memory limit applies on Linux (the GitHub runner)")
    def test_the_memory_limit_stops_a_runaway_reader(self):
        code = ("from scripts.sync.crawl_pdf import limit_memory\n"
                "assert limit_memory(256)\n"
                "block = bytearray(1024 ** 3)\n")
        with self.child(code):
            a = P.analyze_pdf_isolated(b"%PDF-1.4", None, timeout=60)
        self.assertEqual(a["error"], "parse: crashed (out of memory)")

    def test_no_memory_limit_off_linux(self):
        with mock.patch.object(P.sys, "platform", "win32"):
            self.assertFalse(P.limit_memory(256))

    def download(self, data=None):
        head = {"status": 200, "type": "application/pdf", "size": 9000, "checked_at": iso(now())}
        return mock.patch.object(C, "download_pdf", lambda *a, **k: (dict(head), data or pdf_bytes(), None, False))

    def test_the_attempt_is_recorded_before_reading(self):
        cr = crawler(dry_run=False)
        rec = cr.pdfs["k"] = {"url": OWN_PDF, "status": "ok", "refs": [{"url": HUB}], "external": False}
        saved = []

        def save_state(st, dry_run=False):
            saved.append(copy.deepcopy(st["pdfs"]["k"].get("details")))

        # the run is stopped (or killed) while the reader works on the file
        with self.download(), mock.patch.object(C, "save_state", save_state), \
                mock.patch.object(C, "analyze_pdf_isolated", side_effect=C.Stop("signal 15")):
            with self.assertRaises(C.Stop):
                cr.fetch_details("k", rec)
        self.assertEqual(len(saved), 1, "saved before the file is read")
        d = saved[0]
        self.assertEqual((d["error"], d["attempts"]), ("parse: interrupted", 1))
        self.assertEqual(rec["details"], d)
        nt = C._dt(d["next_try"])
        self.assertTrue(now() + timedelta(days=1, hours=23) < nt <= now() + timedelta(days=2, minutes=1))
        self.assertFalse(cr.needs_details(rec, now() + timedelta(days=1)), "skipped next time …")
        self.assertTrue(cr.needs_details(rec, now() + timedelta(days=3)), "… until the back-off has passed")

    def test_a_document_that_breaks_the_reader_does_not_stop_the_run(self):
        st = {"pages": {}, "pdfs": {
            "bad": {"url": OWN_PDF, "status": "ok", "refs": [{"url": HUB}], "external": False},
            "hang": {"url": OWN_PDF.replace("Kit", "Hang"), "status": "ok", "refs": [{"url": HUB}], "external": False},
            "good": {"url": OWN_PDF.replace("Kit", "Flyer"), "status": "ok", "refs": [{"url": HUB}], "external": False}}}
        results = {"bad": {"error": "parse: crashed (exit code -11)", "final": False},
                   "hang": {"error": "parse: no result after 60 s", "final": False},
                   "good": {"title": "Flyer", "pages": 2, "text": "", "page_texts": [], "error": None,
                            "final": False, "thumb_written": False}}
        order = []

        def fake_reader(data, thumb, **kw):
            key = data.decode()
            order.append(key)
            return {"title": None, "pages": None, "text": "", "page_texts": [], "thumb_written": False,
                    **results[key]}

        def download(session, url, **kw):
            key = next(k for k, r in st["pdfs"].items() if r["url"] == url)
            return {"status": 200, "type": "application/pdf", "checked_at": iso(now())}, key.encode(), None, False

        cr = crawler(st, http=FakeSession())
        cr.max_pages = 0                    # PDF work only
        with mock.patch.object(C, "download_pdf", download), mock.patch.object(C, "analyze_pdf_isolated", fake_reader):
            cr.run()
        self.assertEqual(sorted(order), ["bad", "good", "hang"], "the run went on after each failure")
        self.assertEqual(st["pdfs"]["good"]["details"]["pages"], 2)
        self.assertNotIn("error", st["pdfs"]["good"]["details"])
        for key in ("bad", "hang"):
            d = st["pdfs"][key]["details"]
            self.assertEqual((d["error"], d["attempts"]), (results[key]["error"], 1))
            self.assertNotIn("final", d)
            self.assertFalse(cr.needs_details(st["pdfs"][key], now() + timedelta(days=1)))
        self.assertEqual(cr.c["parse_failed"], 2)
        # a second failure doubles the wait (2, 4, 8 … ≤ 30 days)
        with mock.patch.object(C, "download_pdf", download), mock.patch.object(C, "analyze_pdf_isolated", fake_reader):
            cr.fetch_details("bad", st["pdfs"]["bad"])
        self.assertEqual(st["pdfs"]["bad"]["details"]["attempts"], 2)
        self.assertGreater(C._dt(st["pdfs"]["bad"]["details"]["next_try"]), now() + timedelta(days=3, hours=23))


# =========================================================================== P2-12: robots.txt answers
class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)


class RobotsTxtAnswers(unittest.TestCase):
    """RFC 9309 §2.3.1: robots.txt answered 4xx → everything allowed; 5xx (or 429) or no answer → the
    whole host is disallowed (until PoliteSession.ROBOTS_RETRY_S has passed, then it is asked again)."""
    SITE = "https://www.aa.org"

    def session(self, robots_answers: list, clock: FakeClock):
        calls = []

        def fake_request(_self, method, url, **kw):
            calls.append(url)
            if url.endswith("/robots.txt") and not url.startswith(self.SITE):
                return Answer(404, url)                     # other hosts: no robots.txt
            if url.endswith("/robots.txt"):
                step = robots_answers.pop(0) if len(robots_answers) > 1 else robots_answers[0]
                if isinstance(step, Exception):
                    raise step
                status, text = step
                a = Answer(status, url, text.encode(), ctype="text/plain")
                return a
            return Answer(200, url, b"%PDF-1.4", ctype="application/pdf")

        patches = [mock.patch.object(common.time, "monotonic", clock.monotonic),
                   mock.patch.object(common.time, "sleep", clock.sleep),
                   mock.patch("requests.Session.request", fake_request)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return common.PoliteSession(min_delay=1.0, respect_robots=True, retries=1), calls

    def test_a_server_error_closes_the_host(self):
        for status in (500, 503, 429):
            with self.subTest(status=status):
                clock = FakeClock()
                s, calls = self.session([(status, "")], clock)
                url = f"{self.SITE}/sites/default/files/a.pdf"
                self.assertIsNone(s.get(url))
                self.assertEqual(s.last_failure, "robots-unavailable")
                self.assertEqual(s.robots_problem(url), f"HTTP {status}")
                self.assertFalse(s.allowed(f"{self.SITE}/anything"))
                self.assertEqual(calls, [f"{self.SITE}/robots.txt"] * 2, "robots.txt asked twice; the file never")
                self.assertTrue(s.allowed("https://other.example/x.pdf"), "other hosts are not affected")

    def test_no_answer_closes_the_host(self):
        clock = FakeClock()
        s, calls = self.session([requests.ConnectTimeout("timed out")], clock)
        self.assertIsNone(s.get(f"{self.SITE}/a.pdf"))
        self.assertEqual((s.last_failure, s.robots_problem(self.SITE)), ("robots-unreachable", "unreachable"))
        self.assertEqual(len(calls), 2)

    def test_a_client_error_allows_everything(self):
        for status in (404, 403, 410, 401):
            with self.subTest(status=status):
                s, _calls = self.session([(status, "")], FakeClock())
                self.assertIsNotNone(s.get(f"{self.SITE}/a.pdf"))
                self.assertIsNone(s.last_failure)
                self.assertIsNone(s.robots_problem(self.SITE))

    def test_rules_still_apply(self):
        s, _calls = self.session([(200, "User-agent: *\nDisallow: /private/\n")], FakeClock())
        self.assertIsNone(s.get(f"{self.SITE}/private/a.pdf"))
        self.assertEqual(s.last_failure, "robots")
        self.assertIsNone(s.robots_problem(self.SITE), "its rules apply: no problem with the file itself")
        self.assertIsNotNone(s.get(f"{self.SITE}/public/a.pdf"))

    def test_one_blip_is_retried_and_a_long_outage_is_asked_again_later(self):
        s, calls = self.session([(503, ""), (200, "User-agent: *\nAllow: /\n")], FakeClock())
        self.assertTrue(s.allowed(f"{self.SITE}/a.pdf"), "the second try answered")
        clock = FakeClock()
        answers = [(503, ""), (503, ""), (200, "")]
        s, calls = self.session(answers, clock)
        self.assertFalse(s.allowed(f"{self.SITE}/a.pdf"))
        clock.t += s.ROBOTS_RETRY_S - 5
        self.assertFalse(s.allowed(f"{self.SITE}/a.pdf"), "closed for now: robots.txt is not asked again yet")
        self.assertEqual(len(calls), 2)
        clock.t += 10
        self.assertTrue(s.allowed(f"{self.SITE}/a.pdf"), "asked again after ROBOTS_RETRY_S")
        self.assertEqual(len(calls), 3)

    def test_the_crawl_leaves_pages_alone_while_robots_txt_is_down(self):
        crawled = iso(now() - timedelta(days=30))
        st = {"pages": {PAGE: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": crawled, "pdfs": []},
                        HUB: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": crawled, "pdfs": []}},
              "pdfs": {"k": {"url": OWN_PDF, "status": "ok", "refs": [{"url": HUB}], "external": False,
                             "head": {"status": 200, "checked_at": crawled}}}}
        cr = crawler(st, http=FakeSession(robots="HTTP 503"))
        before = copy.deepcopy(st)
        cr.crawl_page(PAGE, st["pages"][PAGE])
        cr.crawl_page(HUB, st["pages"][HUB])
        cr.fetch_head("k", st["pdfs"]["k"])
        self.assertEqual(st, before, "nothing recorded (not 'robots' for 30 days, no strike)")
        self.assertIsNotNone(cr.page_priority(PAGE, st["pages"][PAGE], now()), "due again next run")
        self.assertEqual(cr.c["robots_unavailable"], 2)
        self.assertEqual(cr.hub_report(), [], "not asked for: not reported as a hub problem")
        lines = C.run_warnings(cr, [])
        self.assertEqual(lines, ["robots.txt of www.aagrapevine.org did not answer properly (HTTP 503): its pages "
                                 "were left for the next run"])

    def test_an_answer_that_is_retried_is_closed_first(self):
        # a 503 / 429 answer is dropped for a retry: its connection goes back at once (a stream=True download
        # would otherwise hold it until garbage collection); the answer that is returned stays open
        answers = []

        class Closable(Answer):
            closed = False

            def close(self):
                self.closed = True

        def fake_request(_self, method, url, **kw):
            if url.endswith("/robots.txt"):
                return Answer(404, url)
            a = Closable(503 if len(answers) == 0 else 429 if len(answers) == 1 else 200, url, b"%PDF-1.4")
            answers.append(a)
            return a

        clock = FakeClock()
        for p in (mock.patch.object(common.time, "monotonic", clock.monotonic),
                  mock.patch.object(common.time, "sleep", clock.sleep),
                  mock.patch("requests.Session.request", fake_request)):
            p.start()
            self.addCleanup(p.stop)
        s = common.PoliteSession(min_delay=1.0, respect_robots=True, retries=3)
        r = s.get(f"{RobotsTxtAnswers.SITE}/a.pdf", stream=True)
        self.assertIs(r, answers[-1])
        self.assertEqual([(a.status_code, a.closed) for a in answers], [(503, True), (429, True), (200, False)])

    def test_rules_that_forbid_a_page_are_recorded_as_before(self):
        class RulesSay(FakeSession):
            def allowed(self, url):
                return False

        st = {"pages": {PAGE: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": None}}, "pdfs": {}}
        cr = crawler(st, http=RulesSay())
        cr.crawl_page(PAGE, st["pages"][PAGE])
        self.assertEqual(st["pages"][PAGE]["status"], "robots")
        self.assertEqual(cr.c["robots_skipped"], 1)


class MagazineServerDown(unittest.TestCase):
    """Review of round 7: since robots.txt that does not answer closes the host (P2-12), a magazine server that is
    down sends nothing for its pages — the "site down?" rule (pages asked for, none came back) could no longer fire,
    and the run was saved ok, with a fresh "Last success", every day of the outage. A run that could read no page
    because robots.txt of a magazine site did not answer is a failed run now."""

    def state(self) -> dict:
        crawled = iso(now() - timedelta(days=40))
        return {"version": 1, "updated": None, "sitemaps": {}, "runs": [], "pdfs": {},
                "pages": {u: {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": crawled, "pdfs": [],
                              "pv": C.PARSER_VERSION} for u in (HUB, PAGE, RLV_HUB)}}

    def test_the_verdict(self):
        for robots in ("unreachable", "HTTP 503"):
            with self.subTest(robots=robots):
                st = self.state()
                cr = crawler(st, http=FakeSession(robots=robots))
                for url in (HUB, PAGE, RLV_HUB):
                    cr.crawl_page(url, st["pages"][url])
                ok, error = C.run_verdict(cr)
                self.assertFalse(ok)
                why = "no answer" if robots == "unreachable" else robots
                self.assertEqual(error, f"no page could be read: robots.txt of www.aagrapevine.org ({why}), "
                                        f"www.aalavina.org ({why}) did not answer properly — site down?")
        # the robots.txt hold lifted later in the run and pages were read: ok (the note says what happened)
        st = self.state()
        cr = crawler(st, http=FakeSession(robots="unreachable"))
        cr.crawl_page(PAGE, st["pages"][PAGE])
        cr.http = FakeSession({HUB: Answer(200, HUB, page_html())})
        cr.crawl_page(HUB, st["pages"][HUB])
        self.assertEqual(C.run_verdict(cr), (True, None))
        # pages asked for, none came back: as before
        st = self.state()
        cr = crawler(st, http=FakeSession({u: Answer(503, u) for u in (HUB, PAGE, RLV_HUB)}))
        cr.c["requests"] = 9
        for url in (HUB, PAGE, RLV_HUB):
            cr.crawl_page(url, st["pages"][url])
        self.assertEqual(C.run_verdict(cr)[1], f"no page could be fetched ({cr.c['page_errors']} errors) — site down?")
        self.assertEqual(C.run_verdict(None), (True, None), "a rebuild without network")
        cr = crawler(self.state(), http=FakeSession(robots="unreachable"))
        self.assertEqual(C.run_verdict(cr), (True, None), "nothing was due: nothing to say")

    def test_a_whole_run_keeps_the_last_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            with mock.patch.object(common, "RAW_DIR", raw), mock.patch.object(common, "now_iso",
                                                                                return_value="2026-10-05T07:30:00Z"):
                common.save_raw("pdfs", [{"id": "pdf:1", "title": "A PDF", "first_seen": "2026-01-01T00:00:00Z"}])
            out = io.StringIO()
            with mock.patch.object(common, "RAW_DIR", raw), \
                    mock.patch.object(C, "shared_session", lambda: FakeSession(robots="unreachable")), \
                    mock.patch.object(C, "load_state", return_value=(self.state(), True)), \
                    mock.patch.object(C, "save_state"), \
                    contextlib.redirect_stdout(out):
                C.main(["--minutes", "1", "--no-sitemap"])
            env = json.loads((raw / "pdfs.json").read_text(encoding="utf-8"))
        self.assertFalse(env["ok"])
        self.assertIn("did not answer properly — site down?", env["error"])
        self.assertEqual(env["updated"], "2026-10-05T07:30:00Z", "the last success stays")
        self.assertEqual([i["id"] for i in env["items"]], ["pdf:1"], "nothing is lost")


# =========================================================================== P2-13: pruning the state
class StatePruning(unittest.TestCase):
    """crawl-state.json forgets what only takes room under MAX_KNOWN_PAGES: junk addresses and pages gone
    for PRUNE_GONE_DAYS that nothing links any more; everything still linked or useful stays."""

    def state(self) -> dict:
        t = now()
        old = iso(t - timedelta(days=C.PRUNE_GONE_DAYS + 10))
        recent = iso(t - timedelta(days=20))
        p = "https://www.aalavina.org"
        return {"pdfs": {"privacy": {"url": "https://www.aagrapevine.org/sites/default/files/2020-01/Privacy.pdf",
                                     "status": "ok", "refs": [{"url": f"{p}/www.aagrapevine.org"},
                                                              {"url": f"{p}/website-policy"}]}},
                "pages": {
                    # junk: an e-mail address / a host name read as a relative link, a search page
                    f"{p}/lveditorial%40aagrapevine.org": {"src": "link", "status": 200, "crawled_at": recent},
                    f"{p}/www.aagrapevine.org": {"src": "link", "status": 200, "crawled_at": recent,
                                                 "pdfs": ["privacy"]},
                    "https://www.aagrapevine.org/site-search": {"src": "sitemap", "in_sitemap": True, "crawled_at": None},
                    # gone for months, nothing links it
                    f"{p}/history-aa-grapevine": {"src": "link", "status": "404", "crawled_at": old,
                                                  "in_sitemap": False},
                    f"{p}/old-form": {"src": "link", "status": "410", "crawled_at": recent, "error_since": old},
                    # kept: gone only recently / still linked / in the sitemap / a hub / a working page
                    f"{p}/sample-audio": {"src": "link", "status": "404", "crawled_at": recent, "in_sitemap": False},
                    f"{p}/grapevine-fact-sheet": {"src": "link", "status": "404", "crawled_at": old,
                                                  "linked_at": recent},
                    f"{p}/listed": {"src": "sitemap", "status": "404", "crawled_at": old, "in_sitemap": True},
                    RLV_HUB: {"src": "sitemap", "status": "404", "crawled_at": old, "error_since": old},
                    f"{p}/website-policy": {"src": "sitemap", "status": 200, "crawled_at": old, "in_sitemap": True,
                                            "pdfs": ["privacy"]},
                    f"{p}/old-but-fine": {"src": "link", "status": 200, "crawled_at": old},
                    f"{p}/sleeping": {"src": "link", "status": None, "crawled_at": None, "fails": 3},
                }}

    def test_junk_and_long_gone_pages_are_forgotten(self):
        st = self.state()
        p = "https://www.aalavina.org"
        cr = crawler(st)
        cr.prune()
        self.assertEqual(sorted(u.rsplit("/", 1)[-1] for u in st["pages"]),
                         sorted(["sample-audio", "grapevine-fact-sheet", "listed", "recursos", "website-policy",
                                 "old-but-fine", "sleeping"]))
        self.assertEqual((cr.c["pruned_junk"], cr.c["pruned_gone"]), (3, 2))
        self.assertEqual([r["url"] for r in st["pdfs"]["privacy"]["refs"]], [f"{p}/website-policy"],
                         "a forgotten page is no longer a referrer")
        self.assertNotIn(f"{p}/www.aagrapevine.org".lower(), cr.page_lc)
        stats = C.crawl_stats(st, cr, 400)
        self.assertEqual(stats["pruned_pages"], 5)
        self.assertEqual(cr.run_record()["pruned_junk"], 3)
        cr.prune()
        self.assertEqual(C.crawl_stats(st, cr, 400)["pruned_pages"], 5, "nothing more to forget")

    def test_a_gone_page_that_a_page_still_links_is_kept(self):
        st = self.state()
        gone = "https://www.aalavina.org/history-aa-grapevine"
        about = "https://www.aalavina.org/about-us"
        st["pages"][about] = {"src": "sitemap", "depth": 0, "status": 200, "crawled_at": None, "in_sitemap": True}
        cr = crawler(st, http=FakeSession({about: Answer(200, about, page_html(links=[gone]))}))
        cr.crawl_page(about, st["pages"][about])
        self.assertIn("linked_at", st["pages"][gone])
        stamp = st["pages"][gone]["linked_at"]
        cr.discover(about, st["pages"][about], {gone})
        self.assertEqual(st["pages"][gone]["linked_at"], stamp, "refreshed at most weekly (no daily churn)")
        cr.prune()
        self.assertIn(gone, st["pages"])

    def test_the_sitemap_no_longer_brings_back_pages_never_fetched(self):
        sitemap = ("<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                   "<url><loc>https://www.aagrapevine.org/site-search</loc></url>"
                   "<url><loc>https://www.aagrapevine.org/store/search</loc></url>"
                   "<url><loc>https://www.aagrapevine.org/about-us</loc><lastmod>2026-09-01</lastmod></url>"
                   "</urlset>").encode()
        sm = "https://www.aagrapevine.org/sitemap.xml"
        cr = crawler(http=FakeSession({sm: Answer(200, sm, sitemap, ctype="application/xml")}))
        cr.refresh_sitemaps()
        self.assertEqual(list(cr.pages), ["https://www.aagrapevine.org/about-us"])

    def test_the_real_state_file_loses_only_junk_today(self):
        path = C.STATE_FILE
        if not path.exists():
            self.skipTest("no data/state/crawl-state.json")
        st = json.loads(path.read_text(encoding="utf-8"))
        known = dict(st["pages"])
        cr = crawler(st)
        cr.prune()
        gone = set(known) - set(st["pages"])
        cut = now() - timedelta(days=C.PRUNE_GONE_DAYS)
        for url in gone:
            pg = known[url]
            junk = not R.should_crawl_path(urlsplit(url).path)
            since = C._dt(pg.get("error_since") or pg.get("crawled_at"))
            long_gone = (str(pg.get("status")) in C.GONE_PAGE_STATUSES and not pg.get("in_sitemap")
                         and since is not None and since <= cut)
            self.assertTrue(junk or long_gone, url)
            self.assertNotIn(url.lower(), {h.lower() for h in R.hub_urls()})
        self.assertEqual(cr.c["pruned_junk"], sum(1 for u in known if not R.should_crawl_path(urlsplit(u).path)))
        for rec in st["pdfs"].values():
            self.assertFalse({r.get("url") for r in rec.get("refs") or []} & gone, rec["url"])
        self.assertTrue(all(known[u].get("status") != 200 or not R.should_crawl_path(urlsplit(u).path)
                            for u in gone), "no working page is forgotten")


# =========================================================================== P3-5: the document's day
class DocumentDayInCentralTime(unittest.TestCase):
    """A Last-Modified (UTC) counts by its day in America/Chicago before it is compared with the upload
    month: a file uploaded on October 31 in the evening is dated October 31, not October 1."""

    def test_october_31_at_11_30_pm_central(self):
        lm = P.http_date_iso("Sun, 01 Nov 2026 04:30:00 GMT")          # = 31 Oct 2026 23:30 CDT
        self.assertEqual(lm, "2026-11-01T04:30:00Z")
        self.assertEqual(C._item_date("2026-10", lm, None, False), "2026-10-31")
        url = "https://www.aagrapevine.org/sites/default/files/2026-10/GV_Flyer_Halloween.pdf"
        rec = {"url": url, "status": "ok", "refs": [{"url": HUB, "title": "GVR Resources", "texts": ["Flyer"]}],
               "head": {"status": 200, "type": "application/pdf", "last_modified": lm}}
        self.assertEqual(C.build_item("k", rec, {}, set())["date"], "2026-10-31")

    def test_other_days(self):
        self.assertEqual(C._item_date("2026-10", "2026-10-15T12:00:00Z", None, False), "2026-10-15")
        self.assertEqual(C._item_date(None, "2026-11-01T04:30:00Z", None, False), "2026-10-31")
        self.assertEqual(C._item_date(None, "2026-07-01T04:30:00Z", None, False), "2026-06-30", "CDT: UTC-5")
        self.assertEqual(C._item_date(None, "2026-12-01T05:30:00Z", None, False), "2026-11-30", "CST: UTC-6")
        self.assertEqual(C._item_date(None, "2026-11-01T05:30:00Z", None, False), "2026-11-01")
        self.assertEqual(C._item_date(None, "2026-11-01T04:30:00", None, False), "2026-10-31",
                         "no offset: UTC, whatever the machine's own time zone")
        self.assertEqual(C._item_date(None, None, "2026-11-01T02:00:00Z", True), "2026-10-31")
        self.assertIsNone(C._item_date(None, None, "2026-11-01T02:00:00Z", False))
        # a folder month that is not the file's Central month: the folder's first day, as before
        self.assertEqual(C._item_date("2026-11", "2026-11-01T04:30:00Z", None, False), "2026-11-01")
        self.assertEqual(C._item_date("2026-09", "2026-11-01T04:30:00Z", None, False), "2026-09-01")


if __name__ == "__main__":
    unittest.main()
