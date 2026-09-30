"""Monthly e-mail digest (scripts/notify/send_digest.py): LAST month's news, once, early in the month.

  * EditionWindow — the edition is the Central-time month before the run's (January → December), named
                    after the month it covers; news dates are Central calendar days (daylight saving).
  * Sections      — a realistic September 2026 edition (sent October 1) built from a small data/site folder
                    written for each test: the bulletin (a post counts on the day it was added: first_seen —
                    its date on that day —, never before its `publish` day; expired posts), the magazine
                    issues whose stories came out in September (pub_date; a story without one), the writers,
                    the committee's uploads (the later of their date and first_seen; one row per photo album,
                    dated flyers left out), podcasts / videos / Instagram (per account) / documents, the events
                    that took place (the committee meeting by the `meeting:` rule), nothing of what is current
                    (the toolkit's), the one pointer to October's toolkit, the subject and the --dry-run
                    preview (HTML + plain text, English and Spanish halves; headings and text contrast).
  * MonthArgument — --month is the month COVERED; a mistyped one stops the run; a month not over is not sent.
  * Freshness     — the e-mail waits (exit 3) until every source has been updated since the month ended.
  * WorkflowSchedule — .github/workflows/monthly-digest.yml: when it tries, the once-only marker, exit 3.
  * RealData      — the real command on the repository's own data.

Run:  python -m unittest tests.test_send_digest -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import re
import smtplib
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.notify import send_digest as D  # noqa: E402

SITE = "https://example.org/site"
OCT1 = datetime(2026, 10, 1, 15, 5, tzinfo=timezone.utc)      # the September digest goes out (10:05 AM CDT)

CONFIG = """site:
  title: "Grapevine / La Viña"
  committee: "NETA 65 Grapevine & La Viña Committee"
  committee_es: "Comité de Grapevine y La Viña de NETA 65"
  url: "https://example.org/site"
  contact_email: "chair@example.org"
meeting:
  week_of_month: 3
  weekday: "wednesday"
  start: "19:00"
  end: "20:00"
  platform: "Zoom"
  zoom_url: "https://zoom.us/j/123"
  meeting_id: "123 456"
  passcode: "abc"
  note: "All AA members are welcome."
  skip_dates: []
digest:
  highlights: 2
  per_section: 3
"""


def item(iid: str, kind: str, source: str, date_: str | None, title: str, **kw) -> dict:
    it = {"id": iid, "kind": kind, "source": source, "date": date_, "first_seen": kw.pop("first_seen", date_),
          "title": title, "url": kw.pop("url", f"https://example.com/{iid}"), "lang": kw.pop("lang", "en"),
          "status": "ok", "category": kw.pop("category", None), "extra": kw.pop("extra", {}),
          "i18n": kw.pop("i18n", {"title": {"en": title, "es": f"ES {title}"}}), "machine": kw.pop("machine", [])}
    it.update(kw)
    return it


ISSUE_LABEL = {"gv:2026-10": ("October 2026", "Octubre 2026"), "gv:2026-09": ("September 2026", "Septiembre 2026"),
               "lv:2026-09": ("September / October 2026", "Septiembre / Octubre 2026")}


def article(iid: str, pub: str, key: str, pub_date: str, title: str, theme: dict | None = None, **ex) -> dict:
    en, es = ISSUE_LABEL.get(f"{pub}:{key}", (key, key))
    i18n = {"title": {"en": title, "es": f"ES {title}"}, "issue_label": {"en": en, "es": es}}
    extra = {"publication": pub, "issue_key": key, "issue_label": es if pub == "lv" else en, "pub_date": pub_date, **ex}
    if theme:
        i18n["issue_theme"] = theme
        extra["issue_theme"] = theme["en"] if pub == "gv" else theme["es"]
    return item(iid, "article", "grapevine" if pub == "gv" else "lavina", pub_date, title, category=pub,
                url=f"https://example.com/{iid}", extra=extra, i18n=i18n)


def event(iid: str, start: str, end: str | None, title: str, category: str = "manual", **ex) -> dict:
    return item(iid, "event", "committee", start, title, category=category, extra={"start": start, "end": end, **ex})


def post(iid: str, account: str, when: str, title: str | None = None, **kw) -> dict:
    """An Instagram post of one of the magazines' accounts (instagram.json)."""
    user = {"gv": "alcoholicsanonymous_gv", "lv": "alcoholicosanonimos_lv"}.get(account, account)
    title = title or f"Post {iid}"
    return item(iid, "post", "instagram", when, title, category=account, url=f"https://www.instagram.com/p/{iid.split(':')[-1]}/",
                lang="es" if account == "lv" else "en", extra={"account": account, "username": user},
                i18n={"title": {"en": title, "es": f"ES {title}"}}, machine=["es"] if account == "gv" else ["en"], **kw)


IG_PROFILES = {"gv": {"username": "alcoholicsanonymous_gv", "url": "https://www.instagram.com/alcoholicsanonymous_gv/"},
               "lv": {"username": "alcoholicosanonimos_lv", "url": "https://www.instagram.com/alcoholicosanonimos_lv/"}}


def photo(iid: str, day: str, album: str | None, **kw) -> dict:
    extra = {"panel": 77, **({"album": album} if album else {}), **kw.pop("extra", {})}
    return item(iid, kw.pop("kind", "photo"), "drive", day, f"{iid}.jpg", category=kw.pop("category", "photos"),
                url=f"https://drive.google.com/file/d/{iid}/view", extra=extra,
                i18n={"title": {"en": f"{iid}.jpg", "es": f"{iid}.jpg"}, **({"album": {"en": album, "es": f"ES {album}"}} if album else {})}, **kw)


class DigestCase(unittest.TestCase):
    """Each test gets its own data/site folder and config/site.yml, and SITE_URL."""

    config = CONFIG

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)
        self.site_dir = self.tmp_path / "site"
        self.site_dir.mkdir()
        (self.tmp_path / "site.yml").write_text(self.config, encoding="utf-8")
        for name in ("whatsnew", "events", "announcements"):
            self.write(name, {"items": []})
        for p in (mock.patch.object(D, "SITE_DIR", self.site_dir), mock.patch.object(D, "ASSET_DIR", self.tmp_path / "src"),
                  mock.patch.object(D, "CONFIG_PATH", self.tmp_path / "site.yml"), mock.patch.dict(os.environ, {"SITE_URL": SITE})):
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("GITHUB_STEP_SUMMARY", None)

    def write(self, name: str, data: dict) -> None:
        (self.site_dir / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")

    def set_config(self, text: str) -> None:
        (self.tmp_path / "site.yml").write_text(text, encoding="utf-8")

    def preview(self, as_of: str = "2026-10-01", *extra: str) -> tuple[str, str]:
        out = self.tmp_path / "out"
        self.assertEqual(D.main(["--dry-run", "--as-of", as_of, "--out-dir", str(out), *extra]), 0)
        return (out / "digest.html").read_text(encoding="utf-8"), (out / "digest.txt").read_text(encoding="utf-8")

    @staticmethod
    def halves(text: str) -> tuple[str, str]:
        """The plain text's English half and Spanish half (the Spanish one opens with its edition's name)."""
        i = text.index("\nResumen de ")
        return text[:i], text[i:]

    def full_month(self) -> None:
        """A realistic September 2026 edition (sent October 1): everything the site got in September, plus
        items of August and October that must stay out."""
        self.write("announcements", {"items": [
            item("ann:1", "announcement", "committee", "2026-09-05", "New GVR orientation", url="/bulletin/#new",
                 extra={"body_md": "Join us **Saturday**."}),
            item("ann:gone", "announcement", "committee", "2026-09-06", "Expired", extra={"expires": "2026-09-30"}),
            # written in August, scheduled with `publish:` for September 2 → September's
            item("ann:sched", "announcement", "committee", "2026-08-28", "Scheduled post", extra={"publish": "2026-09-02"}),
            item("ann:oct", "announcement", "committee", "2026-10-01", "October post"),
        ]})
        self.write("articles", {"issues": [
            {"id": "gv:2026-10", "publication": "gv", "key": "2026-10", "label": "October 2026", "theme": "Loneliness",
             "url": "https://www.aagrapevine.org/magazine-issue/october-2026", "cover": "/assets/cache/articles/gv.webp",
             "i18n": {"theme": {"en": "Loneliness", "es": "Soledad"}, "label": {"en": "October 2026", "es": "Octubre 2026"}}},
            {"id": "lv:2026-09", "publication": "lv", "key": "2026-09", "label": "Septiembre / Octubre 2026", "theme": "Servicio en AA",
             "url": "https://www.aalavina.org/edicion/septiembre-octubre-2026",
             "i18n": {"theme": {"en": "Service in AA", "es": "Servicio en AA"},
                      "label": {"en": "September / October 2026", "es": "Septiembre / Octubre 2026"}}},
        ], "items": [
            # the October Grapevine, online since September 23 (+ one story found on October 2)
            article("gv:a1", "gv", "2026-10", "2026-09-23", "A Halloween to Remember", free=False, author="Aaron M.",
                    geo={"scope": "texas", "label_en": "Round Rock, Texas"}),
            article("gv:a2", "gv", "2026-10", "2026-09-23", "At Wit's End", free=True, department=True),
            article("gv:a3", "gv", "2026-10", "2026-09-23", "When Loneliness Comes", free=True),
            article("gv:a4", "gv", "2026-10", "2026-09-23", "Who's That Girl?", free=False),
            article("gv:a5", "gv", "2026-10", "2026-10-02", "Found in October", free=False),
            # the September Grapevine (back catalog: the issue's first day) — no theme of its own: the calendar's
            article("gv:b1", "gv", "2026-09", "2026-09-01", "A Well-Worn Path", free=False),
            article("gv:b2", "gv", "2026-09", "2026-09-01", "An Unexpected Gift", free=False),
            article("gv:c1", "gv", "2026-08", "2026-08-01", "August story", free=False),
            # La Viña September / October
            article("lv:a1", "lv", "2026-09", "2026-09-01", "El despertar del espíritu", free=False, author="Victor R.",
                    geo={"scope": "neta65", "label_en": "Grand Prairie, Texas"}),
            article("lv:a2", "lv", "2026-09", "2026-09-30", "Detenido", free=False),
        ]})
        self.write("editorial", {"items": [
            item("ed:gv:2026-09", "topic", "grapevine", "2026-02-01", "Sponsorship",
                 extra={"publication": "gv", "issue_key": "2026-09", "deadline": "2026-02-01"},
                 i18n={"title": {"en": "Sponsorship", "es": "Padrinazgo"}}),
            item("ed:gv:2026-10", "topic", "grapevine", "2026-03-01", "Dealing with Loneliness",
                 extra={"publication": "gv", "issue_key": "2026-10", "deadline": "2026-03-01"}),
            item("ed:gv:2027-05", "topic", "grapevine", "2026-10-01", "Fun in Sobriety",
                 extra={"publication": "gv", "issue_key": "2027-05", "deadline": "2026-10-01"}),
        ]})
        self.write("spotlight", {"items": [
            dict(article("gv:a1", "gv", "2026-10", "2026-09-23", "A Halloween to Remember", author="Aaron M.",
                         geo={"scope": "texas", "label_en": "Round Rock, Texas", "label_es": "Round Rock, Texas"})),
            dict(article("lv:a1", "lv", "2026-09", "2026-09-01", "El despertar del espíritu", author="Victor R.",
                         geo={"scope": "neta65", "label_en": "Grand Prairie, Texas"})),
            item("sp:aug", "article", "grapevine", "2026-08-31", "August story", extra={"pub_date": "2026-08-31", "geo": {"scope": "neta65"}}),
            item("sp:far", "article", "grapevine", "2026-09-10", "Far away", extra={"pub_date": "2026-09-10", "geo": {"scope": "other"}}),
        ]})
        # a podcast episode (Sep 20, 11:15 PM CDT) and its YouTube upload the same evening
        self.write("episodes", {"items": [
            item("pod:1", "episode", "podcast", "2026-09-21T04:15:00Z", "Gated Communities [Season 11, Episode 12]",
                 category="gv", extra={"season": 11, "episode": 12, "duration_sec": 1920}),
            item("pod:old", "episode", "podcast", "2026-08-31T04:15:00Z", "Two Way Prayer [Season 11, Episode 9]"),
        ]})
        self.write("videos", {"items": [
            item("yt:1", "video", "youtube", "2026-09-21T04:33:00Z", "Gated Communities [Season 11, Episode 12]",
                 url="https://www.youtube.com/watch?v=abc", extra={"season": 11, "episode": 12}),
            item("yt:2", "video", "youtube", "2026-09-08T13:29:00Z", "Date with higher power"),
            item("yt:late", "video", "youtube", "2026-10-01T04:30:00Z", "Late on September 30"),    # 11:30 PM CDT
            item("yt:oct", "video", "youtube", "2026-10-01T05:30:00Z", "Early on October 1"),       # 12:30 AM CDT
            item("yt:undated", "video", "youtube", None, "No date"),
        ]})
        self.write("pdfs", {"items": [
            item("pdf:1", "pdf", "crawl", "2026-09-15", "GV News October 2026", extra={"host": "www.aagrapevine.org", "pages": 4}),
            item("pdf:old", "pdf", "crawl", "2026-08-31", "August document"),
            item("pdf:undated", "pdf", "crawl", None, "Undated document"),
        ]})
        # the committee's uploads count on the later of their date and when the site first had them
        self.write("drive", {"items": [
            item("doc1", "document", "drive", "2026-09-10", "District report", category="reports",
                 url="https://drive.google.com/file/d/doc1/view"),
            # named after an August meeting ("2026-08-11 …"), added on September 25: September's
            item("doc:aug", "document", "drive", "2026-08-11", "Area Chair Meeting Report", category="reports",
                 url="https://drive.google.com/file/d/doc-aug/view", first_seen="2026-09-25T15:09:59Z"),
            # named after the September 16 meeting, added on October 5: the October digest's
            item("doc:min", "document", "drive", "2026-09-16", "Committee meeting minutes", category="notes",
                 url="https://drive.google.com/file/d/doc-min/view", first_seen="2026-10-05T14:00:00Z"),
            photo("ph1", "2026-09-12", "Booth"), photo("ph2", "2026-09-12", "Booth"), photo("ph3", "2026-09-13", "Booth"),
            photo("ph4", "2026-10-02", "Booth"),                                     # uploaded in October: the next digest's
            photo("ph5", "2026-09-30", "Booth", first_seen="2026-10-02T13:00:00Z"),  # taken on the 30th, uploaded on the 2nd
            photo("flyer", "2026-09-20", None, category="flyers", extra={"event_date": "2026-09-26"}),   # a dated flyer: an event
            item("drive:ann", "announcement", "drive", "2026-09-18", "A bulletin document", category="announcements"),
        ]})
        # the magazines' Instagram posts: 4 of Grapevine's in September (one at 11:30 PM CDT on the 30th), one
        # on October 1, one of La Viña's
        self.write("instagram", {"profiles": IG_PROFILES, "items": [
            post("ig:g1", "gv", "2026-09-05T15:00:00Z", "The October issue is here!"),
            post("ig:g2", "gv", "2026-09-12T15:00:00Z"), post("ig:g3", "gv", "2026-09-20T15:00:00Z"),
            post("ig:g4", "gv", "2026-10-01T04:30:00Z", "Late on September 30"),
            post("ig:g5", "gv", "2026-10-01T05:30:00Z", "Early on October 1"),
            post("ig:l1", "lv", "2026-09-10T15:00:00Z", "¡Taller de La Viña!"),
        ]})
        self.write("events", {"items": [
            event("ev:rec:2026-08-08", "2026-08-08T22:00:00Z", "2026-08-09T01:00:00Z", "Booth", "recurring", series="citywide"),
            event("ev:rec:2026-09-12", "2026-09-12T22:00:00Z", "2026-09-13T01:00:00Z", "Booth", "recurring", series="citywide",
                  location="Lover's Lane UMC, Dallas"),
            event("ev:ws-sep", "2026-09-26T19:00:00Z", "2026-09-26T21:00:00Z", "La Viña Writing Workshop", location="Fort Worth"),
            event("ev:early", "2026-10-01T13:00:00Z", "2026-10-01T14:00:00Z", "Early on October 1"),
            event("ev:oct", "2026-10-03T19:00:00Z", None, "October workshop"),
            event("ev:committee:2026-10-21", "2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", "Committee meeting", "committee",
                  online_url="https://zoom.us/j/123"),
            dict(event("ev:gone", "2026-09-19T19:00:00Z", None, "Cancelled"), status="gone"),
        ]})
        self.write("whatsnew", {"items": [
            dict(item("wn:1", "pdf", "crawl", "2026-10-01", "Since the 1st"), wn_date="2026-10-01T12:00:00Z"),
        ]})


class EditionWindow(DigestCase):
    def test_the_edition_is_the_month_before(self):
        ed = D.edition_of(OCT1)
        self.assertEqual((ed["key"], ed["out"]), ("2026-09", "2026-10"))
        self.assertEqual((ed["first"], ed["last"], ed["out_first"]), (date(2026, 9, 1), date(2026, 9, 30), date(2026, 10, 1)))
        jan = D.edition_of(datetime(2027, 1, 1, 15, 5, tzinfo=timezone.utc))
        self.assertEqual((jan["key"], jan["first"], jan["last"], jan["out"]), ("2026-12", date(2026, 12, 1), date(2026, 12, 31), "2027-01"))
        self.assertEqual(D.edition_of(OCT1, "2026-12")["key"], "2026-12")      # --month names the month covered
        self.assertEqual(D.edition_of(OCT1, "2027-13")["key"], "2026-09")      # not a month → last month

    def test_the_month_is_counted_in_central_time(self):
        utc = timezone.utc
        # 03:00 UTC on October 1 is still the evening of September 30 in Texas (CDT): August's digest
        self.assertEqual(D.edition_of(datetime(2026, 10, 1, 3, tzinfo=utc))["key"], "2026-08")
        self.assertEqual(D.edition_of(datetime(2026, 10, 1, 6, tzinfo=utc))["key"], "2026-09")
        # November 1, 2026 is the day daylight saving time ends (2 AM): midnight is still CDT (UTC−5)
        self.assertEqual(D.edition_of(datetime(2026, 11, 1, 4, 30, tzinfo=utc))["key"], "2026-09")
        self.assertEqual(D.edition_of(datetime(2026, 11, 1, 5, 30, tzinfo=utc))["key"], "2026-10")
        # December 1 in CST (UTC−6): 05:30 UTC is still November 30
        self.assertEqual(D.edition_of(datetime(2026, 12, 1, 5, 30, tzinfo=utc))["key"], "2026-10")
        self.assertEqual(D.edition_of(datetime(2026, 12, 1, 6, 30, tzinfo=utc))["key"], "2026-11")
        # the 1st at 15:05 UTC (9:05 AM CST / 10:05 AM CDT): the previous month, every month of the year
        for m in range(1, 13):
            self.assertEqual(D.edition_of(datetime(2027, m, 1, 15, 5, tzinfo=utc))["key"], D.month_add(f"2027-{m:02d}", -1))

    def test_news_on_the_edges_of_the_month_across_daylight_saving(self):
        self.write("pdfs", {"items": [
            item("a", "pdf", "crawl", "2026-11-01T04:30:00Z", "Oct 31, 11:30 PM CDT"),     # October
            item("b", "pdf", "crawl", "2026-11-01T05:30:00Z", "Nov 1, 12:30 AM CDT"),      # November
            item("c", "pdf", "crawl", "2026-12-01T05:30:00Z", "Nov 30, 11:30 PM CST"),     # November
            item("d", "pdf", "crawl", "2026-12-01T06:30:00Z", "Dec 1, 12:30 AM CST"),      # December
            item("e", "pdf", "crawl", "2027-01-01T05:00:00Z", "Dec 31, 11 PM CST"),        # December
            item("f", "pdf", "crawl", "2026-12-31", "a date-only value"),                   # December
        ]})
        ids = lambda now: sorted(i["id"] for i in D.collect(now)["groups"]["pdf"])  # noqa: E731
        self.assertEqual(ids(datetime(2026, 11, 1, 15, 5, tzinfo=timezone.utc)), ["a"])
        self.assertEqual(ids(datetime(2026, 12, 1, 15, 5, tzinfo=timezone.utc)), ["b", "c"])
        self.assertEqual(ids(datetime(2027, 1, 1, 15, 5, tzinfo=timezone.utc)), ["d", "e", "f"])


class Sections(DigestCase):
    def setUp(self):
        super().setUp()
        self.full_month()
        self.data = D.collect(OCT1, None, 3, 2)

    def test_a_post_counts_in_the_month_it_was_added(self):
        # A bulletin post counts on the day it was added to the site: when the site first had it (its own date
        # on that same day), never before its publish day. Written in August but saved on September 10 →
        # September's; dated September 28 but saved on October 3, after the September e-mail went out →
        # October's (never in no e-mail); scheduled for October 2 → October's; dated with its event's day,
        # October 10, but saved on September 25 → September's: by the October edition it has expired, so it
        # would be in no edition (What's New dates it on September 25 too); the same, scheduled for October 4
        # → October's.
        self.write("announcements", {"items": [
            item("ann:ahead", "announcement", "committee", "2026-10-10", "Fall Assembly sign-ups", first_seen="2026-09-25T15:00:00Z",
                 extra={"expires": "2026-10-10"}),
            item("ann:ahead-sched", "announcement", "committee", "2026-10-10", "Scheduled ahead", first_seen="2026-09-20T12:00:00Z",
                 extra={"publish": "2026-10-04"}),
            item("ann:aug-saved", "announcement", "committee", "2026-08-20", "Saved in September", first_seen="2026-09-10T14:00:00Z"),
            item("ann:late", "announcement", "committee", "2026-09-28", "Saved on October 3", first_seen="2026-10-03T14:00:00Z"),
            item("ann:sched", "announcement", "committee", "2026-08-28", "Scheduled", first_seen="2026-08-28T12:00:00Z",
                 extra={"publish": "2026-09-02"}),
            item("ann:sched-oct", "announcement", "committee", "2026-09-20", "Scheduled for October",
                 first_seen="2026-09-20T12:00:00Z", extra={"publish": "2026-10-02"}),
            item("ann:same-day", "announcement", "committee", "2026-09-15", "Saved the same day", first_seen="2026-09-15T22:00:00Z"),
        ]})
        sep = D.collect(OCT1, None, 3, 2)["groups"]["announcement"]
        self.assertEqual([(i["id"], i["_when"]) for i in sep],
                         [("ann:ahead", "2026-09-25T15:00:00Z"), ("ann:same-day", "2026-09-15"),
                          ("ann:aug-saved", "2026-09-10T14:00:00Z"), ("ann:sched", "2026-09-02")])
        oct_ = D.collect(datetime(2026, 11, 1, 15, 5, tzinfo=timezone.utc), None, 3, 2)["groups"]["announcement"]
        self.assertEqual([i["id"] for i in oct_], ["ann:ahead-sched", "ann:late", "ann:sched-oct"])
        self.assertEqual([D.post_when(i) for i in oct_], ["2026-10-04", "2026-10-03T14:00:00Z", "2026-10-02"])

    def test_last_months_news(self):
        g = self.data["groups"]
        # the bulletin: the post scheduled for September 2 is September's; the expired and October's are not
        self.assertEqual([i["id"] for i in g["announcement"]], ["ann:1", "ann:sched"])
        # the magazine stories of September (by pub_date): the October issue's, the back catalog's, La Viña's
        self.assertEqual(sorted(i["id"] for i in g["article"]), ["gv:a1", "gv:a2", "gv:a3", "gv:a4", "gv:b1", "gv:b2", "lv:a1", "lv:a2"])
        # the episode with its YouTube upload folded in; 11:30 PM CDT on the 30th is September's; undated never
        self.assertEqual([i["id"] for i in g["episode"]], ["pod:1"])
        self.assertEqual(g["episode"][0]["_twin"]["id"], "yt:1")
        self.assertEqual([i["id"] for i in g["video"]], ["yt:late", "yt:2"])
        self.assertEqual([i["id"] for i in g["pdf"]], ["pdf:1"])
        # the committee's uploads, on the later of their date and when the site first had them: the report
        # named after an August meeting but added on September 25 is September's (its row keeps its own
        # date); the minutes of the 16th added on October 5, the photo taken on the 30th but uploaded on the
        # 2nd and the October photo are October's. The photos are ONE album row; the dated flyer is an event,
        # the bulletin document a post.
        self.assertEqual([i["id"] for i in g["drive"]], ["doc:aug", "album:f:Booth", "doc1"])
        self.assertEqual((g["drive"][0]["_when"], g["drive"][0]["date"]), ("2026-09-25T15:09:59Z", "2026-08-11"))
        album = g["drive"][1]
        self.assertEqual((album["_count"], album["_when"], album["_names"]), (3, "2026-09-13", {"en": "Booth", "es": "ES Booth"}))
        # Instagram: every post of September (11:30 PM CDT on the 30th too), newest first; per account the
        # count and the 3 newest
        self.assertEqual([i["id"] for i in g["post"]], ["ig:g4", "ig:g3", "ig:g2", "ig:l1", "ig:g1"])
        self.assertEqual([(a["key"], a["name"], a["username"], a["count"], [p["id"] for p in a["newest"]]) for a in self.data["instagram"]],
                         [("gv", "Grapevine", "alcoholicsanonymous_gv", 4, ["ig:g4", "ig:g3", "ig:g2"]),
                          ("lv", "La Viña", "alcoholicosanonimos_lv", 1, ["ig:l1"])])
        self.assertEqual([a["key"] for a in D.ordered_accounts(self.data, "es")], ["lv", "gv"])
        self.assertEqual(D.counts(self.data), {"article": 8, "episode": 1, "video": 2, "post": 5, "pdf": 1, "drive": 2, "album": 1,
                                               "announcement": 2})
        self.assertEqual(D.total_count(self.data), 22 + 2)                       # 22 news + 2 writers
        self.assertEqual(D.count_list(self.data, "en"), "8 magazine stories, 1 podcast episode, 2 videos, 5 Instagram posts, 1 document, "
                                                        "2 committee files, 1 photo album and 2 bulletin posts")
        self.assertEqual(D.count_list(self.data, "es"), "8 historias de las revistas, 1 episodio de podcast, 2 videos, 5 publicaciones de "
                                                        "Instagram, 1 documento, 2 archivos del comité, 1 álbum de fotos y 2 avisos del boletín")

    def test_new_in_the_magazines(self):
        gv10, gv09, lv = self.data["issues"]
        self.assertEqual([(i["pub"], i["key"]) for i in self.data["issues"]], [("gv", "2026-10"), ("gv", "2026-09"), ("lv", "2026-09")])
        self.assertEqual([i["pub"] for i in D.ordered_issues(self.data, "es")], ["lv", "gv", "gv"])       # La Viña first in Spanish
        # the October issue: 4 stories came out in September (a 5th in October), 2 free, the newest on /read/
        self.assertEqual((gv10["count"], gv10["total"], gv10["free"], gv10["current"], gv10["read_href"]), (4, 5, 2, True, "/read/#gv-current"))
        self.assertEqual(gv10["theme"], {"en": "Loneliness", "es": "Soledad"})
        # the back catalog's September issue: no theme of its own → the editorial calendar's; not the newest
        self.assertEqual((gv09["count"], gv09["total"], gv09["current"], gv09["read_href"]), (2, 2, False, "/read/"))
        self.assertEqual(gv09["theme"], {"en": "Sponsorship", "es": "Padrinazgo"})
        self.assertEqual((lv["count"], lv["label"]["en"], lv["label"]["es"], lv["theme"]["es"]),
                         (2, "September / October 2026", "septiembre/octubre de 2026", "Servicio en AA"))
        # highlights: free first, members' stories before "In Every Issue" — never the writers' stories
        self.assertEqual([a["id"] for a in gv10["highlights"]], ["gv:a3", "gv:a2"])
        self.assertEqual([a["id"] for a in lv["highlights"]], ["lv:a2"])

    def test_writers_published_last_month(self):
        w = self.data["writers"]
        self.assertEqual([i["id"] for i in w["neta65"]], ["lv:a1"])            # not the August story
        self.assertEqual([i["id"] for i in w["texas"]], ["gv:a1"])

    def test_the_events_that_took_place(self):
        # the booth, the committee meeting (3rd Wednesday, by the rule: events.json no longer has it), the
        # workshop — not August's booth, not October's events, not a cancelled one
        self.assertEqual([e["id"] for e in self.data["events"]], ["ev:rec:2026-09-12", "ev:committee:2026-09-16", "ev:ws-sep"])
        cm = self.data["events"][1]
        self.assertTrue(cm["_committee"])
        row = D.event_row(cm, "en", D.Links(SITE))
        self.assertEqual(row, {"title": "Committee meeting", "when": "Wed, Sep 16", "where": "Zoom", "url": f"{SITE}/meetings/"})
        self.assertEqual(D.event_row(cm, "es", D.Links(SITE))["title"], "Reunión del comité")
        # a skipped meeting has no row; no `meeting:` settings, no row either
        self.set_config(CONFIG.replace("skip_dates: []", 'skip_dates: ["2026-09-16"]'))
        self.assertNotIn("ev:committee:2026-09-16", [e["id"] for e in D.collect(OCT1)["events"]])
        self.set_config("site:\n  title: \"Grapevine / La Viña\"\n")
        self.assertEqual([e["id"] for e in D.collect(OCT1)["events"]], ["ev:rec:2026-09-12", "ev:ws-sep"])
        # a preview of October on October 1: only what has started by then
        self.assertEqual([e["id"] for e in D.collect(OCT1, "2026-10")["events"]], ["ev:early"])

    def test_nothing_of_what_is_current(self):
        for key in ("meeting", "tips", "weekly", "gvm", "deadlines", "lv_topics", "audio", "botm", "subs_from", "quote", "month"):
            self.assertNotIn(key, self.data)
        html, text = self.preview()
        for word in ("NEXT COMMITTEE MEETING", "Join on Zoom", "PUT IT TO WORK", "Every week", "Grapevine meetings near you",
                     "SHARE YOUR STORY", "BOOK OF THE MONTH", "subscriptions from", "Subscriptions from", "daily quote",
                     "zoom.us", "tel:", "Events calendar", "October workshop", "Fun in Sobriety", "every month",
                     "to be confirmed", "7:00 PM", "Committee meeting minutes", "Early on October 1"):
            self.assertNotIn(word, text)
            self.assertNotIn(word, html)

    def test_subject_and_preheader(self):
        self.assertEqual(D.subject_of(self.data, D.load_config()),
                         "Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026")
        jan = D.collect(datetime(2027, 1, 1, 15, 5, tzinfo=timezone.utc))
        self.assertEqual(D.subject_of(jan, {}), "Grapevine / La Viña — December 2026 digest · Resumen de diciembre de 2026")
        html = D.render_html(self.data, D.load_config(), D.Links(SITE), 3, "s")
        preheader = re.search(r'<div style="display:none;[^"]*">([^<]*)</div>', html).group(1)
        self.assertTrue(preheader.startswith("In September: 8 magazine stories, 1 podcast episode"), preheader)
        self.assertLessEqual(len(preheader), 140)

    def test_dry_run_preview_in_both_languages(self):
        html, text = self.preview()
        en, es = self.halves(text)
        for line in ("September 2026 digest", "Everything new on the site in September",
                     "In September: 8 magazine stories, 1 podcast episode, 2 videos, 5 Instagram posts, 1 document, 2 committee files, "
                     "1 photo album and 2 bulletin posts.",
                     "BULLETIN (2)", "* Scheduled post",
                     "EVENTS IN SEPTEMBER", "* Booth — Sat, Sep 12 · Lover's Lane UMC, Dallas",
                     "* Committee meeting — Wed, Sep 16 · Zoom", f"  {SITE}/meetings/",
                     "* La Viña Writing Workshop — Sat, Sep 26 · Fort Worth",
                     "COMMITTEE UPLOADS (3)", "* [Reports] Area Chair Meeting Report (Aug 11)",
                     "* [Photos] Booth (3 new photos)", f"  {SITE}/photos/",
                     "NEW IN THE MAGAZINES", "* Grapevine — October 2026: “Loneliness” (4 stories · 2 free to read)",
                     f"  → See all 5 stories: {SITE}/read/#gv-current",
                     "* Grapevine — September 2026: “Sponsorship” (2 stories)", f"  → See all 2 stories: {SITE}/read/\n",
                     "WRITERS FROM AREA 65 & TEXAS (2)", "PODCASTS (1)", "* [Podcast] Gated Communities (S11 · E12 · 32 min · Sep 20)",
                     "also on YouTube: https://www.youtube.com/watch?v=abc", "VIDEOS (2)",
                     # Instagram in the text part: the counts per account and the one link
                     "INSTAGRAM (5)\n-------------\n* Grapevine @alcoholicsanonymous_gv: 4 posts\n"
                     f"* La Viña @alcoholicosanonimos_lv: 1 post\n  → See the latest posts from both magazines: {SITE}/instagram/\n",
                     "DOCUMENTS (1)",
                     "COMING UP IN OCTOBER", f"The committee meeting, events and story deadlines, this month's magazine issues "
                                            f"and the Book of the Month. {SITE}/monthly/2026-10/"):
            self.assertIn(line, en)
        self.assertEqual(en.count("/monthly/2026-10/"), 1)
        self.assertNotIn("Two Way Prayer", text)
        self.assertNotIn("Early on October 1", text)
        self.assertNotIn("August", text)
        # Spanish half: La Viña first, Spanish words and dates, the Spanish toolkit address
        for line in ("Resumen de septiembre de 2026", "Todo lo nuevo del sitio en septiembre",
                     "En septiembre: 8 historias de las revistas", "EVENTOS EN SEPTIEMBRE",
                     "* Reunión del comité — mié, 16 de sept · Zoom", f"  {SITE}/es/meetings/",   # the website's spelling
                     "ARCHIVOS DEL COMITÉ (3)", "* [Informes] ES Area Chair Meeting Report (11 ago)",
                     "* [Fotos] ES Booth (3 fotos nuevas)", "LO NUEVO EN LAS REVISTAS",
                     "INSTAGRAM (5)\n-------------\n* La Viña @alcoholicosanonimos_lv: 1 publicación\n"
                     "* Grapevine @alcoholicsanonymous_gv: 4 publicaciones\n"
                     f"  → Ver las publicaciones recientes de las dos revistas: {SITE}/es/instagram/\n",
                     "LO QUE VIENE EN OCTUBRE", f"{SITE}/es/monthly/2026-10/"):
            self.assertIn(line, es)
        self.assertEqual(es.count("/monthly/2026-10/"), 1)
        self.assertLess(es.index("* La Viña — septiembre/octubre de 2026: “Servicio en AA”"),
                        es.index("* Grapevine — octubre de 2026 (en inglés): “Soledad”"))
        self.assertLess(en.index("* Grapevine — October 2026: "), en.index("* La Viña — September / October 2026 (in Spanish): "))
        self.assertIn("— Victor R., Grand Prairie, Texas (La Viña, September / October 2026, in Spanish)", en)
        self.assertNotRegex(es, r"(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre) \d{4}")
        # the order of the sections, in both halves
        for half, heads in ((en, ["BULLETIN", "EVENTS IN SEPTEMBER", "COMMITTEE UPLOADS", "NEW IN THE MAGAZINES", "WRITERS FROM",
                                  "PODCASTS", "VIDEOS", "INSTAGRAM", "DOCUMENTS", "COMING UP IN OCTOBER"]),
                            (es, ["BOLETÍN", "EVENTOS EN SEPTIEMBRE", "ARCHIVOS DEL COMITÉ", "LO NUEVO EN LAS REVISTAS", "ESCRITORES DEL",
                                  "PODCASTS", "VIDEOS", "INSTAGRAM", "DOCUMENTOS", "LO QUE VIENE EN OCTUBRE"])):
            at = [half.index(h) for h in heads]
            self.assertEqual(at, sorted(at), heads)
        # HTML: the edition's name once per half, escaped, the Spanish cells marked lang="es"
        self.assertIn("<title>Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026</title>", html)
        body = html.split("</head>", 1)[1]
        self.assertEqual(body.count(">September 2026 digest<"), 1)
        self.assertEqual(body.count(">Resumen de septiembre de 2026<"), 1)
        self.assertIn('lang="es"', html)
        self.assertIn("At Wit&#x27;s End", html)
        self.assertIn(f'href="{SITE}/es/monthly/2026-10/"', html)
        self.assertIn("This month&#x27;s toolkit (October 2026) →", html)
        self.assertIn("El kit de este mes (octubre de 2026) →", html)
        # every section title is a heading — the pointer to the toolkit too (WCAG 1.3.1)
        self.assertRegex(html, r'<h3 style="[^"]*">Coming up in October</h3>')
        self.assertRegex(html, r'<h3 style="[^"]*">Lo que viene en octubre</h3>')
        # Instagram in the HTML: per account a sub-heading, the 3 newest posts (their line and day, on
        # Instagram — the Spanish half in Spanish) and ONE link to the site's Instagram page
        self.assertRegex(html, r"<h4 [^>]*>Grapevine <span [^>]*>@alcoholicsanonymous_gv</span><span [^>]*> · 4 posts</span></h4>")
        self.assertIn('href="https://www.instagram.com/p/g4/"', html)
        self.assertNotIn('href="https://www.instagram.com/p/g1/"', html)           # the 4th newest: on the site's page
        self.assertIn(">Late on September 30</a><div", html)
        self.assertIn(">ES Late on September 30</a><div", html)
        self.assertIn(f'<a href="{SITE}/instagram/" style="color:{D.C["gv"]};">See the latest posts from both magazines →</a>', html)
        self.assertIn(f'<a href="{SITE}/es/instagram/" style="color:{D.C["gv"]};">Ver las publicaciones recientes de las dos revistas →</a>', html)
        # a committee file shows its own date (the one in its name); an event's day starts its line capitalized
        self.assertIn('Area Chair Meeting Report</a><div style="font-size:12px;color:#57526a;margin-top:3px;">Aug 11</div>', html)
        self.assertIn(">Mié, 16 de sept · Zoom</div>", html)
        # classic Outlook for Windows shows no WebP: without a JPEG / PNG copy the cover is left out
        self.assertNotIn(".webp", html)

    def test_every_text_has_enough_contrast(self):
        """WCAG 1.4.3: every text colour of the e-mail is at least 4.5:1 against the background it sits on —
        the small print (dates, counts, labels, the translation note) too."""
        def lum(hexcol: str) -> float:
            rgb = [int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def ratio(a: str, b: str) -> float:
            la, lb = sorted((lum(a), lum(b)), reverse=True)
            return (la + 0.05) / (lb + 0.05)
        self.data["machine"]["es"] = True                                  # the translation note too
        html = D.render_html(self.data, D.load_config(), D.Links(SITE), 3, "s")
        light = (D.C["surface"], D.C["surface2"], D.C["paper"])               # the e-mail's light backgrounds
        dark = (D.C["gv"], D.C["gv_strong"])                                  # the masthead and the main button
        seen = 0
        for style in re.findall(r'style="([^"]*)"', html):
            fg = re.search(r"(?:^|;)color:(#[0-9a-fA-F]{6})", style)
            if not fg:
                continue
            seen += 1
            bg = re.search(r"background:(#[0-9a-fA-F]{6})", style)
            grounds = (bg.group(1),) if bg else dark if lum(fg.group(1)) > 0.5 else light
            for ground in grounds:
                self.assertGreaterEqual(ratio(fg.group(1), ground), 4.5, f"{fg.group(1)} on {ground}: {style}")
        self.assertGreater(seen, 40)
        self.assertNotIn("#8a8599", html)                                     # the site's "faint": 3.6:1 on white

    def test_covers_go_out_as_jpeg(self):
        # the JPEG copy made next to a cover (scripts/sync/articles.py email_copy) is what the e-mail shows
        jpg = self.tmp_path / "src" / "assets" / "cache" / "articles" / "gv.jpg"
        jpg.parent.mkdir(parents=True)
        jpg.write_bytes(b"\xff\xd8\xff\xd9")
        html, _ = self.preview()
        self.assertIn(f'src="{SITE}/assets/cache/articles/gv.jpg"', html)
        self.assertNotIn(".webp", html)
        self.assertEqual(D.email_image("https://example.org/x.webp"), "")
        self.assertEqual(D.email_image("/assets/img/logo.png"), "/assets/img/logo.png")

    def test_nothing_new_means_no_email(self):
        for name in ("announcements", "articles", "episodes", "videos", "instagram", "pdfs", "drive", "spotlight"):
            self.write(name, {"items": []})
        data = D.collect(OCT1)
        self.assertEqual(D.total_count(data), 0)
        self.assertTrue(data["events"])                       # the events of the month alone are not news
        with mock.patch.dict(os.environ, {"SMTP_SERVER": "", "DIGEST_TO": ""}):
            self.assertEqual(D.main(["--as-of", "2026-10-01"]), 0)                # nothing to send
        self.full_month()
        with mock.patch.dict(os.environ, {"SMTP_SERVER": "", "DIGEST_TO": ""}):
            self.assertEqual(D.main(["--as-of", "2026-10-01"]), 2)                # news, but e-mail not set up
        _, text = self.preview("2026-10-01", "--month", "2026-11")
        self.assertIn("November 2026 digest", text)                              # --month previews another edition
        self.assertIn("A quiet November on the site.", text)
        self.assertIn(f"{SITE}/monthly/2026-12/", text)

    def test_the_toolkit_pointer_is_the_month_it_goes_out_in(self):
        data = D.collect(datetime(2026, 10, 1, 3, tzinfo=timezone.utc))      # still September 30 in Texas
        self.assertEqual(data["edition"]["key"], "2026-08")
        kit = D.toolkit_block(data, "es", D.Links(SITE))
        self.assertEqual((kit["title"], kit["url"], kit["label"]),
                         ("Lo que viene en septiembre", f"{SITE}/es/monthly/2026-09/", "El kit de este mes (septiembre de 2026)"))


class Wording(unittest.TestCase):
    """Small wording rules of the e-mail (both halves)."""

    def test_page_counts(self):
        doc = lambda n: item("pdf:x", "pdf", "crawl", "2026-09-01", "Form", extra={"pages": n, "host": "www.aalavina.org"})  # noqa: E731
        self.assertEqual(D.item_meta(doc(1), "en"), "1 page · aalavina.org")
        self.assertEqual(D.item_meta(doc(1), "es"), "1 página · aalavina.org")
        self.assertEqual(D.item_meta(doc(4), "en"), "4 pages · aalavina.org")
        self.assertEqual(D.item_meta(doc(4), "es"), "4 páginas · aalavina.org")

    def test_spanish_months_inside_a_line(self):
        self.assertEqual(D.in_sentence("Septiembre / Octubre 2026", "es"), "septiembre/octubre de 2026")
        self.assertEqual(D.in_sentence("Octubre 2026", "es"), "octubre de 2026")
        self.assertEqual(D.in_sentence("octubre de 2026", "es"), "octubre de 2026")        # already right
        self.assertEqual(D.in_sentence("September / October 2026", "en"), "September / October 2026")
        self.assertEqual(D.in_sentence("Edición especial", "es"), "Edición especial")       # not a month label
        art = {"kind": "article", "extra": {"issue_label": "May 2027"}}
        self.assertEqual(D.issue_label(art, "es"), "mayo de 2027")                         # no i18n: the local rule
        self.assertEqual(D.issue_label(art, "en"), "May 2027")
        art["i18n"] = {"issue_label": {"en": "May 2027", "es": "Mayo 2027"}}
        self.assertEqual(D.issue_label(art, "es"), "mayo de 2027")

    def test_the_weekly_open_pill(self):
        wo = item("pod:wo", "episode", "podcast", "2026-08-27", "Grapevine Weekly Open AA Meeting", category="wo")
        self.assertEqual(D.item_label(wo, "en")[0], "Weekly Open")
        self.assertEqual(D.item_label(wo, "es")[0], "Reunión Abierta Semanal")
        self.assertEqual(D.item_label(dict(wo, category="gv"), "es")[0], "Podcast")

    def test_the_meeting_rule(self):
        """monthly.js meetingByRule: the 3rd Wednesday by default, -1 = the last, skip dates, Central time."""
        r = D.meeting_by_rule("2026-09", {})
        self.assertEqual(r, {"ymd": "2026-09-16", "start": "2026-09-17T00:00:00Z", "end": "2026-09-17T01:00:00Z"})
        self.assertEqual(D.meeting_by_rule("2026-12", {"weekday": "Wednesday", "week_of_month": 3})["start"], "2026-12-17T01:00:00Z")  # CST
        self.assertEqual(D.meeting_by_rule("2026-09", {"weekday": "saturday", "week_of_month": -1})["ymd"], "2026-09-26")
        self.assertEqual(D.meeting_by_rule("2026-09", {"week_of_month": 5})["ymd"], "2026-09-30")
        self.assertIsNone(D.meeting_by_rule("2026-10", {"week_of_month": 5}))               # no 5th Wednesday
        self.assertIsNone(D.meeting_by_rule("2026-09", {"skip_dates": [date(2026, 9, 16)]}))
        self.assertIsNone(D.meeting_by_rule("2026-09", {"week_of_month": "third"}))


class PostMarkdown(unittest.TestCase):
    """A bulletin post in the e-mail: whatever Markdown the chair wrote (content/bulletin/README.md) is
    drawn as HTML with inline styles, and as plain lines in the text part — never the raw marks."""

    POST = ("Join us for the **Fall Assembly**.\n\n"
            "| Time | What | Where |\n|------|------|-------|\n| 9:00 AM | Registration | [Lobby](/events/) |\n\n"
            "> A quotation, a share or a reading.\n\n---\n\n"
            "### What to bring\n- Your subscription\n- A friend\n    - Nested one\n    - Nested two\n1. First\n2. Second\n\n"
            "![Flyer](<https://x.org/f.jpg>) and <https://neta65.org> ~~old~~\nLine two.")

    def site(self, u: str) -> str:
        return "https://example.org/site" + u

    def test_html(self):
        h = D.md_to_html(self.POST, "#00f", self.site)
        for raw in ("| Time", "|---", "> A", "---", "**", "###", "- Your", "~~", "<https"):
            self.assertNotIn(raw, h)
        self.assertIn("<strong>Fall Assembly</strong>", h)
        self.assertRegex(h, r"<table [^>]*><tr><th [^>]*>Time</th><th [^>]*>What</th><th [^>]*>Where</th></tr><tr><td [^>]*>9:00 AM</td>")
        self.assertIn('<a href="https://example.org/site/events/" style="color:#00f;">Lobby</a>', h)
        self.assertRegex(h, r"<blockquote [^>]*>A quotation, a share or a reading\.</blockquote><hr [^>]*>")
        self.assertIn("font-weight:bold;\">What to bring</p>", h)
        # a list inside a list; a numbered list after it is a list of its own
        self.assertRegex(h, r"<ul [^>]*><li [^>]*>Your subscription</li><li [^>]*>A friend<ul [^>]*><li [^>]*>Nested one</li>"
                            r"<li [^>]*>Nested two</li></ul></li></ul><ol [^>]*><li [^>]*>First</li><li [^>]*>Second</li></ol>")
        self.assertIn('<a href="https://x.org/f.jpg" style="color:#00f;">Flyer</a> and <a href="https://neta65.org"', h)
        self.assertIn("<s>old</s><br>Line two.", h)
        self.assertNotIn("<script", D.md_to_html("<script>alert(1)</script> [x](javascript:alert(1))", "#00f"))

    def test_text(self):
        t = D.md_to_text(self.POST, self.site)
        self.assertEqual(t.split("\n\n"), [
            "Join us for the Fall Assembly.",
            "Time · What · Where\n9:00 AM · Registration · Lobby (https://example.org/site/events/)",
            "“A quotation, a share or a reading.”",
            "What to bring",
            "• Your subscription\n• A friend\n  – Nested one\n  – Nested two",
            "• First\n• Second",
            "Flyer (https://x.org/f.jpg) and https://neta65.org old\nLine two.",
        ])

    def test_a_long_post_is_cut_between_blocks(self):
        short, cut = D.md_excerpt(self.POST, 150)
        self.assertTrue(cut)
        self.assertTrue(short.startswith("Join us") and short.endswith("| 9:00 AM | Registration | [Lobby](/events/) |"))  # the table whole
        self.assertEqual(D.md_excerpt("Short.", 150), ("Short.", False))
        long_para, cut = D.md_excerpt("word " * 300, 150)
        self.assertTrue(cut and len(long_para) <= 150 and long_para.endswith("…"))


class FakeSMTP:
    """Stands in for smtplib.SMTP / SMTP_SSL and records what the digest asks of the mail server.
    Each test makes its own subclass (Sending.make_server), so the settings and the log are its own."""
    offers_starttls = True
    connect_errors: list = []       # raised by the next connections, in order
    login_error: Exception | None = None
    send_error: Exception | None = None
    log: list = []

    def __init__(self, host, port, timeout=None, context=None):
        cls = type(self)
        if cls.connect_errors:
            raise cls.connect_errors.pop(0)
        cls.log.append(("connect", host, port))
        self.encrypted = bool(context)                     # only SMTP_SSL is given the TLS context here

    def ehlo(self):
        type(self).log.append(("ehlo",))

    def has_extn(self, name):
        return name.lower() == "starttls" and type(self).offers_starttls

    def starttls(self, context=None):
        self.encrypted = True
        type(self).log.append(("starttls",))

    def login(self, user, password):
        type(self).log.append(("login", "encrypted" if self.encrypted else "PLAIN TEXT"))
        if type(self).login_error:
            raise type(self).login_error

    def send_message(self, msg, from_addr=None, to_addrs=None):
        type(self).log.append(("send", tuple(to_addrs or ())))
        if type(self).send_error:
            raise type(self).send_error
        return {}

    def quit(self):
        type(self).log.append(("quit",))

    def close(self):
        pass


class Sending(unittest.TestCase):
    """send(): the password only over an encrypted connection; retries only before the message goes."""

    def setUp(self):
        env = {"SMTP_SERVER": "smtp.example.org", "SMTP_PORT": "587", "SMTP_USERNAME": "digest@example.org",
               "SMTP_PASSWORD": "app-password"}
        for p in (mock.patch.dict(os.environ, env), mock.patch.object(D.time, "sleep", lambda s: None)):
            p.start()
            self.addCleanup(p.stop)
        self.msg = D.build_message("Subject", "<p>x</p>", "x", "digest@example.org", "Committee",
                                   ["a@example.org", "b@example.org"], "chair@example.org")

    def make_server(self, **kw):
        cls = type("Server", (FakeSMTP,), {"log": [], "connect_errors": list(kw.pop("connect_errors", [])), **kw})
        for name in ("SMTP", "SMTP_SSL"):
            p = mock.patch.object(D.smtplib, name, cls)
            p.start()
            self.addCleanup(p.stop)
        return cls

    @staticmethod
    def steps(server) -> list[str]:
        return [e[0] for e in server.log]

    def test_starttls_before_the_password(self):
        server = self.make_server()
        D.send(self.msg, "digest@example.org", ["a@example.org", "b@example.org"])
        self.assertEqual(self.steps(server), ["connect", "ehlo", "starttls", "ehlo", "login", "send", "quit"])
        self.assertIn(("login", "encrypted"), server.log)
        self.assertIn(("send", ("a@example.org", "b@example.org")), server.log)

    def test_no_starttls_means_no_password(self):
        server = self.make_server(offers_starttls=False)
        with self.assertRaises(RuntimeError) as cm:
            D.send(self.msg, "digest@example.org", ["a@example.org"])
        self.assertIn("does not offer STARTTLS", str(cm.exception))
        self.assertNotIn("login", self.steps(server))                    # the password never left
        self.assertNotIn("send", self.steps(server))
        self.assertEqual(self.steps(server).count("connect"), 1)        # a missing STARTTLS is not retried

    def test_port_465_is_ssl_from_the_start(self):
        with mock.patch.dict(os.environ, {"SMTP_PORT": "465"}):
            server = self.make_server(offers_starttls=False)
            D.send(self.msg, "digest@example.org", ["a@example.org"])
        self.assertEqual(self.steps(server), ["connect", "ehlo", "login", "send", "quit"])
        self.assertIn(("login", "encrypted"), server.log)

    def test_connection_trouble_is_retried_before_sending(self):
        server = self.make_server(connect_errors=[ConnectionRefusedError("refused"), TimeoutError("slow")])
        D.send(self.msg, "digest@example.org", ["a@example.org"])
        self.assertEqual(self.steps(server).count("send"), 1)
        self.make_server(connect_errors=[ConnectionRefusedError("x")] * 3)
        with self.assertRaises(RuntimeError) as cm:
            D.send(self.msg, "digest@example.org", ["a@example.org"])
        self.assertIn("Could not reach the mail server smtp.example.org:587", str(cm.exception))

    def test_a_failure_while_sending_is_never_retried(self):
        for err in (smtplib.SMTPServerDisconnected("gone"), TimeoutError("timed out"), ConnectionResetError("reset")):
            with self.subTest(error=type(err).__name__):
                server = self.make_server(send_error=err)
                with self.assertRaises(RuntimeError) as cm:
                    D.send(self.msg, "digest@example.org", ["a@example.org", "b@example.org"])
                self.assertIn("MAY have been sent", str(cm.exception))
                self.assertEqual(self.steps(server).count("send"), 1)   # one try: nobody gets it twice
                self.assertEqual(self.steps(server).count("connect"), 1)

    def test_refusals_are_reported(self):
        self.make_server(login_error=smtplib.SMTPAuthenticationError(535, b"bad"))
        with self.assertRaisesRegex(RuntimeError, "App Password"):
            D.send(self.msg, "digest@example.org", ["a@example.org"])
        self.make_server(send_error=smtplib.SMTPRecipientsRefused({"a@example.org": (550, b"no")}))
        with self.assertRaisesRegex(RuntimeError, "All recipients were refused"):
            D.send(self.msg, "digest@example.org", ["a@example.org"])
        self.make_server(send_error=smtplib.SMTPDataError(554, b"spam"))
        with self.assertRaisesRegex(RuntimeError, "it was not sent"):
            D.send(self.msg, "digest@example.org", ["a@example.org"])


SMTP_ENV = {"SMTP_SERVER": "smtp.example.org", "SMTP_USERNAME": "u@example.org", "SMTP_PASSWORD": "p",
            "DIGEST_TO": "group@example.org"}


class MonthArgument(DigestCase):
    def test_a_mistyped_month_stops_before_anything_is_sent(self):
        self.full_month()
        out = self.tmp_path / "out"
        with mock.patch.dict(os.environ, SMTP_ENV), mock.patch.object(D, "send") as send:
            for bad in ("2026-9", "Oct", "2026-13", "", "2026-10 "):
                with self.subTest(month=bad):
                    self.assertEqual(D.main(["--as-of", "2026-10-01", "--month", bad]), 2)
                    self.assertEqual(D.main(["--dry-run", "--as-of", "2026-10-01", "--month", bad, "--out-dir", str(out)]), 2)
            send.assert_not_called()
            self.assertFalse(out.exists())
            self.assertEqual(D.main(["--as-of", "2026-10-01", "--month", "2026-09"]), 0)      # the September digest
            send.assert_called_once()

    def test_a_month_that_is_not_over_is_not_sent(self):
        self.full_month()
        with mock.patch.dict(os.environ, SMTP_ENV), mock.patch.object(D, "send") as send:
            self.assertEqual(D.main(["--as-of", "2026-10-01", "--month", "2026-10"]), 2)      # October is not over
            send.assert_not_called()
        self.preview("2026-10-01", "--month", "2026-10")                                    # a preview is fine

    def test_the_workflow_passes_any_month_on(self):
        wf = (ROOT / ".github" / "workflows" / "monthly-digest.yml").read_text(encoding="utf-8")
        self.assertIn('if [ -n "$month" ]; then args+=(--month "$month"); fi', wf)
        self.assertNotIn("=~ ^[0-9]{4}", wf)          # no silent filter: the script rejects a bad month


class Freshness(DigestCase):
    """The e-mail waits (exit 3, nothing sent) until every source it reads was tried after the month ended."""

    def setUp(self):
        super().setUp()
        self.full_month()
        summary = self.tmp_path / "summary.md"
        for p in (mock.patch.dict(os.environ, {**SMTP_ENV, "GITHUB_STEP_SUMMARY": str(summary)}),):
            p.start()
            self.addCleanup(p.stop)
        self.summary = summary

    def status(self, **attempted) -> None:
        fresh = "2026-10-01T14:00:00Z"                  # 9 AM CDT on October 1: after September ended
        self.write("status", {"sources": [
            {"source": s, "ok": True, "updated": attempted.get(s, fresh), "attempted": attempted.get(s, fresh)}
            for s in D.FRESH_SOURCES + ("quote", "shop")]})

    def run_main(self, *extra: str) -> tuple[int, int]:
        with mock.patch.object(D, "send") as send:
            code = D.main(["--as-of", "2026-10-01", *extra])
        return code, send.call_count

    def test_waits_for_a_source_not_updated_since_the_month_ended(self):
        self.status(podcasts="2026-09-30T20:00:00Z")    # 3 PM CDT on the 30th: an episode of that evening may be missing
        self.assertEqual(D.waiting_for(D.edition_of(OCT1)), ["podcasts"])
        self.assertEqual(self.run_main(), (3, 0))
        self.assertIn("Waiting for podcasts", self.summary.read_text(encoding="utf-8"))
        # the preview never waits (exit 0), and says what a scheduled send would wait for
        self.preview()
        self.assertIn("A scheduled send would still wait for: podcasts", self.summary.read_text(encoding="utf-8"))

    def test_sends_once_every_source_is_updated(self):
        self.status()
        self.assertEqual(self.run_main(), (0, 1))

    def test_stale_ok_and_force_send_anyway(self):
        self.status(podcasts="2026-09-30T20:00:00Z")
        self.assertEqual(self.run_main("--stale-ok"), (0, 1))
        self.assertEqual(self.run_main("--force"), (0, 1))

    def test_a_source_that_never_ran_or_stopped_is_not_waited_for(self):
        self.status(podcasts=None, drive="2026-09-20T12:00:00Z")    # never ran · idle for more than 3 days
        self.assertEqual(D.waiting_for(D.edition_of(OCT1)), [])
        self.assertEqual(self.run_main(), (0, 1))

    def test_no_status_file_does_not_block(self):
        (self.site_dir / "status.json").unlink(missing_ok=True)
        self.assertEqual(D.waiting_for(D.edition_of(OCT1)), [])
        self.assertEqual(self.run_main(), (0, 1))


class WorkflowSchedule(unittest.TestCase):
    """.github/workflows/monthly-digest.yml: tries on the 1st–3rd, sends once, waits for the data."""

    def setUp(self):
        self.text = (ROOT / ".github" / "workflows" / "monthly-digest.yml").read_text(encoding="utf-8")
        self.wf = yaml.safe_load(self.text)
        self.on = self.wf.get("on", self.wf.get(True))            # PyYAML (YAML 1.1) reads the key `on` as True
        self.steps = {s.get("id") or s.get("name"): s for s in self.wf["jobs"]["digest"]["steps"]}

    def test_when_it_tries(self):
        crons = [c["cron"] for c in self.on["schedule"]]
        self.assertEqual(crons, ["7 12,15,18,21 1-3 * *"])          # four tries a day on the 1st–3rd (UTC)
        minute, hours, days = crons[0].split()[:3]
        self.assertNotEqual(minute, "0")
        self.assertEqual((hours.split(","), days), (["12", "15", "18", "21"], "1-3"))
        self.assertIn("covers", self.on["workflow_dispatch"]["inputs"]["month"]["description"])
        self.assertEqual(self.wf["permissions"], {"contents": "read", "pages": "read", "actions": "read"})

    def test_the_guard(self):
        run = self.steps["check"]["run"]
        for needle in ("TZ=America/Chicago date +%-d", "TZ=America/Chicago date +%-H", '"$day" -gt 3', '"$hour" -lt 7',
                       'actions/artifacts?name=digest-sent-$edition', "select(.expired|not)", "::warning",
                       '"$day" -eq 3', '"$hour" -ge 12', "last=true", 'if [ "$EVENT" != "schedule" ]'):
            self.assertIn(needle, run)
        for step in ("Check out the repository", "Set up Python", "site", "send"):
            self.assertEqual(self.steps[step]["if"], "contains(fromJSON('[\"preview\",\"send\"]'), steps.check.outputs.mode)")

    def test_it_sends_once_and_waits_for_the_data(self):
        run = self.steps["send"]["run"]
        for needle in ("set -uo pipefail", 'args+=(--stale-ok)', 'code=0', 'python -m scripts.notify.send_digest "${args[@]}" || code=$?',
                       "3)", "::notice title=Digest waits::", 'exit "$code"', "digest-sent/sent.txt", "sent=true"):
            self.assertIn(needle, run)
        # only the scheduled tries before the last ones wait: the last ones and a manual send go with the data there is
        self.assertIn('if [ "${LAST:-}" = "true" ] || { [ "$MODE" = "send" ] && [ "$EVENT" != "schedule" ]; }; then args+=(--stale-ok); fi', run)
        self.assertEqual(self.steps["send"]["env"]["EVENT"], "${{ github.event_name }}")
        mark = self.steps["Mark the month as sent"]
        self.assertEqual(mark["if"], "steps.send.outputs.sent == 'true'")
        self.assertEqual(mark["with"]["name"], "digest-sent-${{ steps.check.outputs.edition }}")
        self.assertEqual(mark["with"]["retention-days"], 40)


class RealData(unittest.TestCase):
    """The command itself, on the repository's own data (like the check workflow): it must always build."""

    def test_the_command_builds_a_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GITHUB_STEP_SUMMARY": ""}
            for extra in ([], ["--month", "2027-01"]):
                r = subprocess.run([sys.executable, "-m", "scripts.notify.send_digest", "--dry-run", "--out-dir", tmp, *extra],
                                   cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("DRY RUN — subject: Grapevine / La Viña — ", r.stdout)
                html = (Path(tmp) / "digest.html").read_text(encoding="utf-8")
                text = (Path(tmp) / "digest.txt").read_text(encoding="utf-8")
                self.assertIn("Versión en español más abajo", html)
                self.assertIn("\nResumen de ", text)
            self.assertIn("January 2027 digest · Resumen de enero de 2027", r.stdout)


if __name__ == "__main__":
    unittest.main()
