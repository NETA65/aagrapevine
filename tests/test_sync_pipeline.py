"""Offline tests for the sync pipeline's safety rules (no network: every session is faked,
data/raw and the cache folders are redirected to a temporary directory).

    python -m unittest tests.test_sync_pipeline -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import common  # noqa: E402


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


class TempRaw(unittest.TestCase):
    """Each test gets its own data/raw (load_raw/save_raw read common.RAW_DIR at call time)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-test-"))
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        p = mock.patch.object(common, "RAW_DIR", self.raw)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def env(self, source: str) -> dict:
        return json.loads((self.raw / f"{source}.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- merge_items
class MergeItems(unittest.TestCase):
    def _pair(self):
        old = [{"id": "a", "title": "A", "image": "/old.png", "summary": "old", "date": "2026-01-01",
                "first_seen": "2026-01-01T00:00:00Z", "last_seen": iso(datetime.now(timezone.utc)),
                "extra": {"expires": "2026-09-01", "link": "https://old.example"}}]
        new = [{"id": "a", "title": "A", "image": None, "summary": "", "date": None,
                "first_seen": None, "last_seen": None, "extra": {"expires": None, "link": None}}]
        return old, new

    def test_default_mode_keeps_previous_values(self):
        old, new = self._pair()
        merged, added = common.merge_items(old, new)
        self.assertEqual(added, 0)
        self.assertEqual(merged[0]["image"], "/old.png")
        self.assertEqual(merged[0]["extra"]["expires"], "2026-09-01")

    def test_authoritative_mode_takes_the_new_item_as_is(self):
        old, new = self._pair()
        merged, _ = common.merge_items(old, new, authoritative=True)
        it = merged[0]
        self.assertEqual(it["first_seen"], "2026-01-01T00:00:00Z")      # history kept
        self.assertEqual(it["last_seen"], old[0]["last_seen"])          # weekly throttle kept
        self.assertIsNone(it["image"])
        self.assertIsNone(it["date"])
        self.assertIsNone(it["extra"]["expires"])
        self.assertIsNone(it["extra"]["link"])


# --------------------------------------------------------------------------- raw file I/O
class RawFiles(TempRaw):
    def test_corrupt_raw_file_is_kept_aside_and_reported(self):
        common.save_raw("demo", [{"id": "x", "title": "X", "first_seen": "2026-01-01T00:00:00Z"}])
        p = self.raw / "demo.json"
        p.write_text(p.read_text(encoding="utf-8")[:-5], encoding="utf-8")   # truncated file
        env = common.load_raw("demo")
        self.assertEqual(env["items"], [])
        backups = list(self.raw.glob("demo.json.corrupt-*"))
        self.assertEqual(len(backups), 1, "the unreadable file must be kept for recovery")
        self.assertFalse(p.exists())
        common.save_raw("demo", [{"id": "y", "title": "Y"}], ok=True)
        env = self.env("demo")
        self.assertFalse(env["ok"])
        self.assertIn("unreadable", env["error"])
        self.assertEqual([i["id"] for i in env["items"]], ["y"])
        common.save_raw("demo", [{"id": "y", "title": "Y"}], ok=True)     # reported once, then healthy
        self.assertTrue(self.env("demo")["ok"])

    def test_write_json_accepts_dates(self):
        common.write_json(self.raw / "d.json", {"when": date(2026, 9, 1), "tags": {"b", "a"}})
        self.assertEqual(json.loads((self.raw / "d.json").read_text(encoding="utf-8")),
                         {"when": "2026-09-01", "tags": ["a", "b"]})


# --------------------------------------------------------------------------- polite session
class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)


class CrossHostPacing(unittest.TestCase):
    def test_both_magazine_hosts_share_one_delay(self):
        clock = FakeClock()
        stamps = []

        class Resp:
            status_code, headers, text, encoding = 200, {}, "<html/>", "utf-8"

        def fake_request(_self, method, url, **kw):
            stamps.append((clock.t, url))
            return Resp()

        with mock.patch.object(common.time, "monotonic", clock.monotonic), \
                mock.patch.object(common.time, "sleep", clock.sleep), \
                mock.patch("requests.Session.request", fake_request):
            s = common.PoliteSession(min_delay=5.0, respect_robots=False)
            for u in ["https://www.aagrapevine.org/magazine", "https://www.aalavina.org/la-revista",
                      "https://aalavina.org/revista/a", "https://www.aagrapevine.org/magazine/b",
                      "https://feeds.example.com/rss"]:
                s.get(u)
        gaps = [b[0] - a[0] for a, b in zip(stamps, stamps[1:])]
        self.assertEqual(gaps[:3], [5.0, 5.0, 5.0])
        self.assertEqual(gaps[3], 0.0, "an unrelated host is not delayed by the magazine sites")
        self.assertEqual(common.PoliteSession.pace_key("https://WWW.AALAVINA.ORG/x"),
                         common.PoliteSession.pace_key("https://www.aagrapevine.org/y"))


# --------------------------------------------------------------------------- the bulletin (content/bulletin)
class Announcements(TempRaw):
    def setUp(self):
        super().setUp()
        from scripts.sync import announcements as A
        self.A = A
        self.ann, self.evs = self.tmp / "bulletin", self.tmp / "events"
        self.ann.mkdir()
        self.evs.mkdir()
        for name, val in (("ANN_DIR", self.ann), ("EVENTS_DIR", self.evs)):
            p = mock.patch.object(A, name, val)
            p.start()
            self.addCleanup(p.stop)

    def test_removed_header_lines_disappear(self):
        (self.ann / "welcome.md").write_text(
            "---\ntitle: Welcome\nexpires: 2026-09-01\nurl: https://old.example/link\nimage: /assets/img/old.png\n"
            "---\nBody text one.\n", encoding="utf-8")
        (self.evs / "2027-03-14-assembly.md").write_text(
            "---\ntitle: Assembly\nstart: 2027-03-14\nonline_url: https://zoom.us/j/111\nlocation: Tyler, TX\n"
            "---\nOld body.\n", encoding="utf-8")
        self.A.main([])
        first = self.env("announcements")["items"][0]["first_seen"]
        (self.ann / "welcome.md").write_text("---\ntitle: Welcome\n---\nBody text one.\n", encoding="utf-8")
        (self.evs / "2027-03-14-assembly.md").write_text("---\ntitle: Assembly\nstart: 2027-03-14\n---\n",
                                                          encoding="utf-8")
        self.A.main([])
        a = self.env("announcements")["items"][0]
        e = self.env("manual_events")["items"][0]
        self.assertEqual(a["first_seen"], first)
        self.assertIsNone(a["image"])
        self.assertIsNone(a["extra"]["expires"])
        self.assertIsNone(a["extra"]["link"])
        self.assertEqual(a["url"], "/bulletin/#welcome")
        self.assertIsNone(e["extra"]["online_url"])
        self.assertIsNone(e["extra"]["location"])
        self.assertEqual(e["extra"]["body_md"], "")

    def test_extension_case_and_other_files(self):
        (self.ann / "Spring-Assembly.MD").write_text("---\ntitle: Spring\n---\nHi.\n", encoding="utf-8")
        (self.ann / "notes.txt").write_text("not markdown", encoding="utf-8")
        (self.ann / "README.md").write_text("# help", encoding="utf-8")
        (self.ann / ".gitkeep").write_text("", encoding="utf-8")
        self.assertEqual([p.name for p in self.A.content_files(self.ann)], ["Spring-Assembly.MD"])
        self.A.main([])
        env = self.env("announcements")
        self.assertEqual(len(env["items"]), 1)
        self.assertEqual(env["stats"]["problems"], 1)
        self.assertIn("notes.txt", env["stats"]["errors"][0])


# --------------------------------------------------------------------------- external events
class ExternalEvents(TempRaw):
    def _run(self, sitemap_ok: bool, listed: tuple[str, ...]):
        from scripts.sync import events_external as E
        d1 = (date.today() + timedelta(days=20)).isoformat()
        d2 = (date.today() + timedelta(days=200)).isoformat()
        urls = {"dallas": f"https://www.aagrapevine.org/get-involved/events/{d1}/dallas-roundup",
                "tyler": f"https://www.aagrapevine.org/get-involved/events/{d2}/tyler-assembly"}
        titles = {urls["dallas"]: ("Dallas Roundup", d1), urls["tyler"]: ("Tyler Assembly", d2)}
        index = ("<sitemapindex><sitemap><loc>https://www.aagrapevine.org/sitemap.xml?page=1</loc>"
                 f"<lastmod>{'-'.join(listed)}</lastmod></sitemap></sitemapindex>")
        page = "<urlset>" + "".join(f"<url><loc>{urls[k]}</loc></url>" for k in listed) + "</urlset>"
        cal = ('<script type="application/json" data-drupal-selector="drupal-settings-json">'
               + json.dumps({"fullCalendarView": [{"calendar_options": json.dumps(
                   {"events": [{"url": urls["dallas"]}]})}]}) + "</script>")

        class Resp:
            def __init__(self, text):
                self.status_code, self.text, self.encoding = 200, text, "utf-8"

        class Http:
            requests_made = 0

            def get_text(self, url, **kw):
                if url.endswith("/sitemap.xml"):
                    return index if sitemap_ok else None
                if "sitemap.xml?page=1" in url:
                    return page
                if "calendar" in url or "calendario" in url:
                    return cal
                return None

            def get(self, url, **kw):
                title, day = titles[url]
                ld = {"@type": "Event", "name": title, "startDate": f"{day}T12:00:00+0000"}
                return Resp(f'<script type="application/ld+json">{json.dumps(ld)}</script><h1>{title}</h1>'
                            '<div class="field--name-field-event-location"><div class="field__item">Dallas, TX'
                            '</div></div>')

        with mock.patch.object(E, "shared_session", lambda: Http()):
            E.main([])
        env = self.env("events_external")
        return {i["title"]: i["first_seen"] for i in env["items"]}

    def test_calendar_fallback_keeps_known_events(self):
        day1 = self._run(True, ("dallas", "tyler"))
        self.assertEqual(set(day1), {"Dallas Roundup", "Tyler Assembly"})
        day2 = self._run(False, ())                      # sitemap down → calendar lists only Dallas
        self.assertEqual(day2, day1, "known upcoming events stay, with their first_seen")
        day3 = self._run(True, ("dallas",))              # a complete sitemap without Tyler → removed
        self.assertEqual(set(day3), {"Dallas Roundup"})


# --------------------------------------------------------------------------- articles
HUB = """<html><body><div class="main-region"><div class="large-eyebrow">October 2026</div>
<h1>Loneliness</h1></div>
<div class="node--type-article view-mode-teaser"><h3><a href="/magazine/2026/oct/{slug}">My Story</a></h3>
<div class="author">By: Jake B. | Tyler, Texas</div><div class="field--name-body"><p>A teaser sentence that is
long enough to be kept here.</p></div><img src="/sites/default/files/card.jpg"></div></body></html>"""
ARTICLE = ("""<html><body><article class="node--type-article"><h1>My Story</h1>
<div class="article-publication-date">October 2026 | Loneliness | Our Personal Stories</div>
<div class="author">By: Jake B.</div><p>""" + "x " * 30 + "</p></article></body></html>")


class Articles(TempRaw):
    def setUp(self):
        super().setUp()
        from scripts.sync import articles as AR
        self.AR = AR
        p = mock.patch.object(AR, "THUMB_DIR", self.tmp / "thumbs")
        p.start()
        self.addCleanup(p.stop)

    def _run(self, hub_slug: str, article_code: int) -> list:
        calls = []

        class Resp:
            def __init__(self, code, text=""):
                self.status_code, self.text, self.encoding, self.headers, self.content = \
                    code, text, "utf-8", {}, text.encode()

        class Http:
            requests_made = 0

            def get_text(self, url, **kw):
                return HUB.replace("{slug}", hub_slug) if url.endswith("/magazine") else None

            def get(self, url, **kw):
                calls.append(url)
                return Resp(article_code, ARTICLE if article_code == 200 else "")

        with mock.patch.object(self.AR, "shared_session", lambda: Http()):
            self.AR.main(["--only", "gv"])
        return calls

    def _item(self, slug="my-story"):
        env = self.env("articles")
        it = next(i for i in env["items"] if i["url"].endswith(slug))
        return it, env["detail_state"].get(it["id"])

    def _age_state(self, iid, days):
        """Pretend the last check (and first 404) happened `days` ago."""
        env = self.env("articles")
        old = iso(datetime.now(timezone.utc) - timedelta(days=days))
        st = env["detail_state"][iid]
        st["at"] = old
        if "missing_since" in st:
            st["missing_since"] = old
        common.write_json(self.raw / "articles.json", env)

    def test_404_while_the_hub_links_it_does_not_hide_it(self):
        self._run("my-story", 404)
        it, st = self._item()
        self.assertEqual(it["status"], "ok")
        self.assertNotIn("gone", st)

    def test_hub_listing_revives_an_article_marked_gone(self):
        self._run("my-story", 200)
        env = self.env("articles")
        it = env["items"][0]
        it["status"] = "gone"                               # as the old code left it after one 404
        env["detail_state"] = {it["id"]: {"tries": 1, "at": it["first_seen"], "gone": True, "ok": False}}
        common.write_json(self.raw / "articles.json", env)
        self._run("my-story", 200)
        it, st = self._item()
        self.assertEqual(it["status"], "ok")
        self.assertFalse((st or {}).get("gone"))

    def test_gone_needs_two_404s_a_week_apart(self):
        self._run("my-story", 200)                            # known, but make it need a re-check
        env = self.env("articles")
        iid = env["items"][0]["id"]
        env["items"][0]["extra"]["section"] = None            # incomplete → retried
        env["detail_state"] = {iid: {"tries": 1, "at": env["items"][0]["first_seen"], "ok": False}}
        common.write_json(self.raw / "articles.json", env)
        self._age_state(iid, 8)
        self._run("next-story", 404)                          # hub moved on; first 404
        it, st = self._item()
        self.assertEqual(it["status"], "ok")
        self.assertIn("missing_since", st)
        self.assertEqual(self._run("next-story", 404), [], "no re-check before a week has passed")
        self._age_state(iid, 8)
        self._run("next-story", 404)                          # second 404, a week later
        it, st = self._item()
        self.assertEqual(it["status"], "gone")
        self.assertTrue(st["gone"])


# --------------------------------------------------------------------------- drive
class Drive(TempRaw):
    def test_private_names_never_stored_and_last_seen_stable(self):
        from scripts.sync import drive as D
        from scripts.sync.drive_listing import FOLDER_MIME, Entry, Listing
        tree = {
            "ROOT": [Entry("P77", "2027-2028_Panel77_GVLV", FOLDER_MIME, is_folder=True)],
            "P77": [Entry("NOTES", "notes", FOLDER_MIME, is_folder=True)],
            "NOTES": [Entry("f1", "2027-01-20 Minutes.pdf", "application/pdf", modified_text="Jan 20"),
                      Entry("f2", "PRIVATE - Maria G. sponsor phone list.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                      Entry("f3", "GVR sign-up (Responses)", "application/vnd.google-apps.spreadsheet")],
        }

        class FakeLister:
            mode, api_error, requests_made, http = "html", None, 0, None

            class html:
                shortcuts_resolved = 0
                http = None

            def list(self, fid):
                return Listing(True, [Entry(**vars(e)) for e in tree[fid]])

        cfg = {"drive": {"root_folder_id": "ROOT", "min_panel": 77,
                         "exclude_name_contains": ["(Responses)", "PRIVATE"]}}
        with mock.patch.object(D, "DriveLister", lambda **kw: FakeLister()), \
                mock.patch.object(D, "load_config", lambda: cfg), \
                mock.patch.object(D, "check_forms", lambda items, http: {}):
            D.main([])
            text = (self.raw / "drive.json").read_text(encoding="utf-8")
            first = self.env("drive")
            with mock.patch.object(D, "now_iso", lambda: "2099-01-01T00:00:00Z"):
                D.main([])
        self.assertNotIn("Maria", text)
        self.assertNotIn("sign-up", text)
        self.assertEqual(first["stats"]["excluded"], 2)
        self.assertEqual(sum(first["stats"]["excluded_by_reason"].values()), 2)
        second = self.env("drive")
        self.assertEqual(first["items"][0]["last_seen"], second["items"][0]["last_seen"])


# --------------------------------------------------------------------------- meeting + build_data
class MeetingConfig(unittest.TestCase):
    def test_times_in_every_shape(self):
        import yaml
        from scripts.sync.meeting import parse_hhmm
        cases = {"19:00": (19, 0), '"19:00"': (19, 0), "7:30": (7, 30), '"7:00 PM"': (19, 0),
                 "19": (19, 0), "19:00:00": (19, 0), '"nonsense"': (19, 0), '"25:00"': (19, 0)}
        for raw, want in cases.items():
            self.assertEqual(parse_hhmm(yaml.safe_load(f"x: {raw}")["x"], (19, 0)), want, raw)

    def test_unquoted_time_in_config_works(self):
        import yaml
        from scripts.sync import meeting as M
        cfg = yaml.safe_load("site: {timezone: America/Chicago}\nmeeting:\n  weekday: wednesday\n"
                             "  week_of_month: 3\n  start: 19:00\n  end: 20:00\n")
        with mock.patch.object(M, "load_config", lambda: cfg):
            ms = M.upcoming_meetings(2)
        self.assertEqual(len(ms), 2)
        start = datetime.fromisoformat(ms[0]["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(ms[0]["end"].replace("Z", "+00:00"))
        self.assertEqual(end - start, timedelta(hours=1))
        self.assertIn(start.astimezone(timezone.utc).hour, (0, 1))   # 19:00 Central = 00:00/01:00 UTC


class BuildData(TempRaw):
    def test_same_language_override_only_restores_accents_and_capitals(self):
        from scripts.sync import build_data as B
        from scripts.sync import translate as T

        class TrStub:
            overrides = T.Overrides({"UN DIA A LA VEZ": {"es": "Un día a la vez", "en": "One Day at a Time"},
                                     "Sin temor": {"es": "Sin miedo"}})
        i18n = B.I18n(TrStub())
        i18n.done[("es", "en", False, "UN DIA A LA VEZ")] = ("One Day at a Time", False)
        pair, machine = i18n.pair("UN DIA A LA VEZ", "es")
        self.assertEqual(pair, {"es": "Un día a la vez", "en": "One Day at a Time"})
        self.assertFalse(machine)
        # a same-language entry that changes the WORDS is ignored: the original is never rewritten
        self.assertEqual(i18n.pair("Sin temor", "es")[0]["es"], "Sin temor")
        self.assertEqual(i18n.pair("Otro título", "es")[0], {"es": "Otro título", "en": "Otro título"})

    def test_bad_meeting_config_is_reported_not_fatal(self):
        from scripts.sync import build_data as B
        ctx = B.Ctx(offline=True)
        with mock.patch.object(B, "committee_meetings", side_effect=ValueError("bad time")), \
                mock.patch.object(B, "ics_events", lambda c: []):
            evs = B.build_events(ctx)
        self.assertIn("meeting", ctx.raw_problems)
        self.assertIsInstance(evs, list)


# --------------------------------------------------------------------------- weekly open, crawl
class WeeklyOpen(unittest.TestCase):
    def test_join_details_carried_other_fields_not(self):
        from scripts.sync.weekly_open import ITEM_ID, carry_join_details
        prev = [{"id": ITEM_ID, "extra": {"zoom_id": "1", "passcode": "p", "day": "Wednesday", "weekday": 2,
                                          "time": "Noon", "start_local": "12:00", "player_url": "https://old"}}]
        item = {"id": ITEM_ID, "extra": {"zoom_id": "2", "day": "Wednesday", "weekday": 2, "time": "Noon",
                                         "start_local": "12:00"}}
        self.assertEqual(carry_join_details(item, prev), ["passcode"])
        self.assertEqual(item["extra"]["passcode"], "p")
        self.assertEqual(item["extra"]["zoom_id"], "2")
        self.assertNotIn("player_url", item["extra"])

    def test_la_vina_meeting_time_in_every_shape(self):
        """config/site.yml `lavina_weekly_open: time:` is edited by hand: an UNQUOTED 12:00 (the YAML reader
        makes it the number 720) keeps the La Viña card on /meetings/, like `meeting:` / `recurring_events:`."""
        import yaml
        from scripts.sync import weekly_open as W
        now = datetime(2026, 9, 30, 15, tzinfo=timezone.utc)
        base = {"enabled": True, "day": "thursday", "timezone": "America/New_York", "starts": "2026-11-05",
                "zoom_id": "871 2036 8287"}
        for raw, want in (("12:00", "2026-11-05T17:00:00Z"), ('"12:00"', "2026-11-05T17:00:00Z"),
                          ('"12 p. m."', "2026-11-05T17:00:00Z"), ("Noon", "2026-11-05T17:00:00Z"),
                          ("12", "2026-11-05T17:00:00Z"), ("13:30", "2026-11-05T18:30:00Z")):
            cfg = dict(base, time=yaml.safe_load(f"x: {raw}")["x"])
            it = W.lavina_item(cfg, now)
            self.assertIsNotNone(it, raw)
            self.assertEqual(it["extra"]["next_start"], want, raw)
            self.assertEqual([i["id"] for i in W.with_lavina([{"id": W.ITEM_ID}], [], cfg)], [W.ITEM_ID, W.LV_ITEM_ID])
        with self.assertLogs("weekly_open", "WARNING"):
            self.assertIsNone(W.lavina_item(dict(base, time="late"), now))


class CrawlMerge(unittest.TestCase):
    def test_rebuild_without_network_leaves_the_state_file_alone(self):
        # `crawl --minutes 0` only rebuilds pdfs.json; rewriting an unchanged 1.5 MB state file would
        # only churn git (and clash with the daily bot's copy). A state recovered from pdfs.json is saved.
        from scripts.sync import crawl as C
        st = C.empty_state()
        for loaded_ok, saved in ((True, False), (False, True)):
            with mock.patch.object(C, "load_state", return_value=(st, loaded_ok)),                     mock.patch.object(C, "load_raw", return_value={"items": []}),                     mock.patch.object(C, "save_state") as save_state,                     mock.patch.object(C, "save_raw") as save_raw,                     mock.patch.object(C, "print_summary"):
                C.main(["--minutes", "0"])
            self.assertEqual(save_state.called, saved)
            self.assertTrue(save_raw.called)

    def test_fresh_fields_win_and_last_seen_is_throttled(self):
        from scripts.sync import crawl as C
        now = datetime.now(timezone.utc)
        old = [{"id": "pdf:1", "image": "/assets/cache/pdf/x.webp", "first_seen": "2026-01-01T00:00:00Z",
                "last_seen": iso(now - timedelta(days=2)),
                "extra": {"thumb": "/assets/cache/pdf/x.webp", "referrers": [{"url": "u", "title": "t"}],
                          "event_date": "2026-05-01", "orphan": False, "size_bytes": 10}}]
        new = [{"id": "pdf:1", "image": None, "first_seen": "2026-01-01T00:00:00Z",
                "extra": {"thumb": None, "referrers": [], "event_date": None, "orphan": True, "size_bytes": None}}]
        merged, _ = common.merge_items(old, new)
        C.reapply_fresh_fields(merged, new)
        ex = merged[0]["extra"]
        self.assertIsNone(merged[0]["image"])
        self.assertEqual((ex["thumb"], ex["referrers"], ex["event_date"], ex["orphan"]), (None, [], None, True))
        self.assertEqual(ex["size_bytes"], 10, "a transient HEAD failure keeps the known size")
        cur = iso(now - timedelta(days=2))
        self.assertFalse(C._last_seen_changed(cur, iso(now)))                        # < a week newer
        self.assertTrue(C._last_seen_changed(cur, iso(now - timedelta(days=30))))    # moved back
        self.assertTrue(C._last_seen_changed(iso(now - timedelta(days=9)), iso(now)))


# --------------------------------------------------------------------------- podcasts, instagram
def png_bytes(size=(1200, 1200)) -> bytes:
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", size, (120, 40, 90)).save(buf, "PNG")
    return buf.getvalue()


class PodcastArt(TempRaw):
    def test_one_small_local_copy_per_artwork(self):
        from PIL import Image
        from scripts.sync import podcasts as P
        art = self.tmp / "pod"
        art.mkdir()
        (art / "stale.webp").write_bytes(b"x")
        data = png_bytes()
        calls = []

        class Resp:
            status_code, headers, content = 200, {"Content-Type": "image/png"}, data

        class Http:
            def get(self, url, **kw):
                calls.append(url)
                return Resp()

        items = [{"id": f"pod:gv:{n}", "image": "https://artwork.example/a.jpeg", "extra": {}} for n in range(3)]
        items.append({"id": "pod:wo:1", "image": "https://artwork.example/b.jpeg", "extra": {"thumb": "/old"}})
        shows = [{"key": "gv", "image": "https://artwork.example/a.jpeg"}]
        with mock.patch.object(P, "ART_DIR", art):
            stats = P.attach_art(Http(), items, shows, dry_run=False)
            self.assertEqual(sorted(calls), ["https://artwork.example/a.jpeg", "https://artwork.example/b.jpeg"])
            thumb = items[0]["extra"]["thumb"]
            self.assertTrue(thumb.startswith("/assets/cache/pod/") and thumb.endswith(".webp"))
            self.assertEqual(shows[0]["thumb"], thumb)
            self.assertNotEqual(items[3]["extra"]["thumb"], thumb)
            with Image.open(art / thumb.rsplit("/", 1)[-1]) as im:
                self.assertLessEqual(max(im.size), 480)
            self.assertFalse((art / "stale.webp").exists())
            self.assertEqual(stats["artwork"], 2)
            calls.clear()
            P.attach_art(Http(), items, shows, dry_run=False)
            self.assertEqual(calls, [], "artwork is downloaded once, then reused")


class InstagramAvatar(unittest.TestCase):
    def test_freshness_comes_from_the_envelope_not_file_time(self):
        from scripts.sync import instagram as I
        tmp = Path(tempfile.mkdtemp(prefix="gv-ig-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / f"{I.AVATAR_PREFIX}gv.webp").write_bytes(b"x")     # fresh mtime, like a new checkout
        calls = []

        def fake_download(fx, url, dest, *a, **k):
            calls.append(url)
            return True

        with mock.patch.object(I, "THUMB_DIR", tmp), mock.patch.object(I, "download_image", fake_download):
            prof = {"avatar_url": "https://cdn/a.jpg"}
            I.ensure_avatar(None, "gv", prof)                        # never checked → refresh
            self.assertEqual(len(calls), 1)
            self.assertIn("_avatar_checked", prof)
            I.ensure_avatar(None, "gv", dict(prof))                  # checked just now → no request
            self.assertEqual(len(calls), 1)
            old = dict(prof, _avatar_checked=iso(datetime.now(timezone.utc) - timedelta(days=8)))
            I.ensure_avatar(None, "gv", old)                         # a week later → refresh
            self.assertEqual(len(calls), 2)


class InstagramRetention(unittest.TestCase):
    """instagram.json keeps the newest sources.instagram.keep_per_account posts of each account (prune(), which
    also deletes the pruned posts' thumbnails). The monthly digest of a month P is on /digest/ all through the
    next month and counts P's posts from this file, so the setting must hold about 62 days of posts — the two
    accounts post about 2 a day (September 2026) — or P's Instagram count shrinks late in that month."""

    def test_the_setting_holds_two_months_of_posts(self):
        from scripts.sync import instagram as I
        from scripts.sync.common import load_config
        cfg = (load_config().get("sources") or {}).get("instagram") or {}
        keep = int(cfg.get("keep_per_account") or I.DEFAULT_KEEP_PER_ACCOUNT)
        self.assertGreaterEqual(keep, 62 * 2)
        self.assertGreaterEqual(I.DEFAULT_KEEP_PER_ACCOUNT, 62 * 2, "without the setting too")
        # two posts a day for 70 days on each account, plus a manual post: every post of the last 62 days stays
        start = datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc)
        items = [{"id": f"ig:{a}:{n}", "category": a, "date": iso(start + timedelta(hours=12 * n)), "extra": {"shortcode": f"{a}{n}"}}
                 for a in ("gv", "lv") for n in range(140)]
        items.append({"id": "ig:gv:manual", "category": "gv", "date": iso(start - timedelta(days=90)), "extra": {"manual": True}})
        kept, removed = I.prune(items, keep)
        last = start + timedelta(hours=12 * 139)
        recent = {i["id"] for i in items if not i["extra"].get("manual")
                  and datetime.fromisoformat(i["date"].replace("Z", "+00:00")) > last - timedelta(days=62)}
        self.assertEqual(len(recent), 2 * 124)
        self.assertTrue(recent <= {i["id"] for i in kept})
        self.assertIn("ig:gv:manual", {i["id"] for i in kept}, "a manual post is never pruned")
        self.assertEqual(len(removed), 2 * (140 - keep))


# --------------------------------------------------------------------------- review 2026-09 fixes
class Resp:
    """A minimal requests.Response stand-in."""

    def __init__(self, status=200, payload=None, headers=None, url="https://x.test/"):
        self.status_code, self._payload, self.headers, self.url = status, payload, headers or {}, url
        self.text = json.dumps(payload) if payload is not None else ""
        self.is_redirect = "Location" in self.headers and status in (301, 302, 303, 307, 308)

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def close(self):
        pass


class DriveSafety(TempRaw):
    def test_api_empty_answer_for_a_hidden_folder_is_not_an_empty_folder(self):
        from scripts.sync.drive_listing import ApiLister, FOLDER_MIME
        lister = ApiLister("k")

        def get(url, **kw):
            if url.endswith("/files"):
                return Resp(200, {"files": []})                  # files.list: 200 + nothing
            return Resp(404, {"error": {"message": "File not found"}})
        lister.http.get = get
        res = lister.list("HIDDEN")
        self.assertFalse(res.ok)
        self.assertIn("404", res.error)
        lister.http.get = lambda url, **kw: (Resp(200, {"files": []}) if url.endswith("/files")
                                             else Resp(200, {"id": "F", "mimeType": FOLDER_MIME, "trashed": False}))
        self.assertTrue(lister.list("F").ok, "a readable folder that is really empty")
        lister.http.get = lambda url, **kw: Resp(200, {"id": "F", "mimeType": FOLDER_MIME, "trashed": True})
        self.assertFalse(lister.list("F").ok)

    def test_flyer_time_ranges(self):
        from scripts.sync.drive import extract_time
        cases = {
            "Asamblea 7pm-9pm": ("19:00", "21:00"), "Workshop 9am-12pm": ("09:00", "12:00"),
            "Workshop 9am to 3pm": ("09:00", "15:00"), "Taller 9:30am - 11:30am": ("09:30", "11:30"),
            "Workshop 9 a.m. - 1 p.m.": ("09:00", "13:00"), "Booth 10am-2pm": ("10:00", "14:00"),
            "Assembly 9-11am": ("09:00", "11:00"), "Booth 10-2pm": ("10:00", "14:00"), "Event 10-12pm": ("10:00", "12:00"),
            "Taller 7 a 9 pm": ("19:00", "21:00"), "Meeting 10:00-12:00": ("10:00", "12:00"),
            "Booth 9am": ("09:00", None), "Reunión 18:30": ("18:30", None),
        }
        for text, want in cases.items():
            start, end, rest = extract_time(text)
            self.assertEqual((start, end), want, text)
            self.assertNotRegex(rest, r"\d", f"{text!r} left {rest!r}")
        self.assertEqual(extract_time("Taller de 9 am a 1 pm")[2].strip(), "Taller")

    def test_noon_midnight_and_a_time_zone_in_a_flyer_name(self):
        """"noon" / "mediodía" / "midnight" count where they ARE a time, and a time zone written right after
        the time ("12 p. m. (hora del Este)") is read and taken out of the title — but a place that only
        looks like one ("Noon Group", "Mountain Creek Church", "Pacific Ave") stays as written."""
        from scripts.sync.drive import extract_time, extract_time_zone
        cases = {
            "Workshop noon-2pm": ("12:00", "14:00", None), "Workshop 11am-noon": ("11:00", "12:00", None),
            "Workshop 12 noon": ("12:00", None, None), "Taller mediodía a 2pm": ("12:00", "14:00", None),
            "Taller de 10 a mediodía": ("10:00", "12:00", None), "Dance 8pm-midnight": ("20:00", "00:00", None),
            "jueves a las 12 p. m. (hora del Este) por Zoom": ("12:00", None, "America/New_York"),
            "Open meeting 12pm ET on Zoom": ("12:00", None, "America/New_York"),
            "Workshop 12pm Eastern Time": ("12:00", None, "America/New_York"),
            "Workshop 7pm (Central)": ("19:00", None, "America/Chicago"), "Workshop 7pm CDT": ("19:00", None, "America/Chicago"),
            "Taller 11 a. m. hora de la Montaña": ("11:00", None, "America/Denver"),
            "Workshop 6-8pm PT": ("18:00", "20:00", "America/Los_Angeles"),
        }
        for text, want in cases.items():
            start, end, rest, zone = extract_time_zone(text)
            self.assertEqual((start, end, zone), want, text)
            self.assertNotRegex(rest, r"(?i)\d|noon|mediod|midnight|hora|eastern|central|\b[ECP]D?T\b", f"{text!r} left {rest!r}")
        self.assertEqual(extract_time("Workshop noon-2pm"), ("12:00", "14:00", "Workshop  "))
        for text, start, words in (("Noon Group Anniversary 7pm", "19:00", "Noon Group Anniversary"),
                                   ("High Noon Group GV Workshop 7-9pm", "19:00", "High Noon Group GV Workshop"),
                                   ("Workshop 2-4pm @ Noon Group, Garland, TX", "14:00", "Workshop @ Noon Group, Garland, TX"),
                                   ("GV Workshop 10am Mountain Creek Church", "10:00", "GV Workshop Mountain Creek Church"),
                                   ("GV Workshop 10am Pacific Ave Group", "10:00", "GV Workshop Pacific Ave Group"),
                                   ("GV Workshop 7pm Central Christian Church", "19:00", "GV Workshop Central Christian Church")):
            got, _end, rest, zone = extract_time_zone(text)
            self.assertEqual((got, zone, " ".join(rest.split())), (start, None, words), text)

    def test_a_markdown_post_on_drive_has_a_plain_text_summary(self):
        """A bulletin post uploaded to Drive as Markdown (.md) gets the teaser rule of content/bulletin posts:
        the home page card and the feed show its summary as text — never "**", "[label](url)" or "`" — and an
        unchanged file (its body reused from the last run) gets it too."""
        from scripts.sync import drive as D
        body = ("A living list of ways to carry the message.\n\n# Why it matters\n\n"
                "- **A meeting in print, every day.** Read [the magazine](https://www.aagrapevine.org/magazine).\n"
                "- __Most of it is free.__ `Subscribe` ~~today~~ now.\n")
        it = {"id": "drive:md1", "kind": "announcement", "title": "Ways to carry the message", "lang": "en",
              "summary": "", "extra": {"file_id": "md1", "mime": "text/markdown", "name": "Ways to carry the message.md",
                                       "modified_text": "Sep 29", "body_md": ""}}
        prev = {"drive:md1": {"extra": {"body_md": body, "modified_text": "Sep 29"}}}
        self.assertEqual(D.fill_announcements([it], prev, http=None), {"reused": 1})
        self.assertEqual(it["summary"], "A living list of ways to carry the message. Why it matters A meeting in print, "
                                        "every day. Read the magazine. Most of it is free. Subscribe today now.")
        self.assertEqual(it["extra"]["body_md"], body)              # the page still renders the Markdown

    def test_a_clock_time_in_the_folder_view_is_pacific_time(self):
        """Drive's embedded folder view writes a change of the last 24 hours as a clock time on the PACIFIC
        wall clock — "11:07 pm" for a file saved at 06:07 UTC — which may be yesterday's: it is dated by the
        site's (Central) calendar, not simply "today"."""
        from scripts.sync.drive_listing import parse_modified_text
        seen = datetime(2026, 9, 30, 17, 51, tzinfo=timezone.utc)                  # 12:51 PM CDT
        cases = [("11:07 pm", seen, "2026-09-30"),        # 11:07 PM PDT on the 29th = 1:07 AM CDT on the 30th
                 ("7:49 am", seen, "2026-09-30"),
                 ("6:00 pm", datetime(2026, 9, 30, 10, 17, tzinfo=timezone.utc), "2026-09-29"),     # 8 PM CDT the 29th
                 ("9:00 pm", datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc), "2026-12-31")]       # 11 PM CST Dec 31
        for text, now, want in cases:
            self.assertEqual(parse_modified_text(text, date(2026, 9, 30), now=now), want, text)
        self.assertEqual(parse_modified_text("Feb 20", date(2026, 9, 30)), "2026-02-20")
        self.assertEqual(parse_modified_text("99:99 pm", date(2026, 9, 30)), "2026-09-30")

    def test_unresolved_shortcut_is_retried_and_has_no_thumbnail(self):
        from scripts.sync.drive_listing import HtmlLister, SHORTCUT_MIME, Entry
        heads = []

        class Http:
            requests_made = 0

            def head(self, url, **kw):
                heads.append(url)
                return None                                      # Drive did not answer
        sid = "S" * 33
        lister = HtmlLister(session=Http(), shortcut_cache={sid: sid})   # as a run before the fix saved it
        e = Entry(sid, "Flyer.pdf", SHORTCUT_MIME)
        lister._resolve_shortcut(e)
        self.assertEqual(len(heads), 1, "a failed lookup is not treated as resolved")
        self.assertTrue(e.unresolved_shortcut)
        self.assertNotIn(sid, lister.shortcut_cache)

    def test_undecided_form_check_keeps_yesterdays_answer(self):
        from scripts.sync import drive as D
        prev = [{"id": "drive:f", "kind": "form", "first_seen": "2026-01-01T00:00:00Z", "last_seen": None,
                 "extra": {"form_closed": True, "folder_chain": []}}]
        new = [{"id": "drive:f", "kind": "form", "date": "2026-01-01", "extra": {"folder_chain": []}}]
        merged, _ = D.merge(prev, new, set())
        self.assertIs(merged[0]["extra"]["form_closed"], True)
        new = [{"id": "drive:f", "kind": "form", "date": "2026-01-01", "extra": {"form_closed": False}}]
        merged, _ = D.merge(prev, new, set())
        self.assertIs(merged[0]["extra"]["form_closed"], False, "a decided check wins")


class AnnouncementHeaders(TempRaw):
    def setUp(self):
        super().setUp()
        from scripts.sync import announcements as A
        self.A = A
        self.ann, self.evs = self.tmp / "bulletin", self.tmp / "events"
        self.ann.mkdir()
        self.evs.mkdir()
        for name, val in (("ANN_DIR", self.ann), ("EVENTS_DIR", self.evs)):
            p = mock.patch.object(A, name, val)
            p.start()
            self.addCleanup(p.stop)

    def write(self, name, text, folder=None):
        (folder or self.ann).joinpath(name).write_text(text, encoding="utf-8")

    def test_header_mistakes_are_reported_or_read(self):
        self.write("empty.md", "---\n---\nJust a body line.\n")
        self.write("colon.md", "---\ntitle: Reminder: Assembly Saturday\nexpires: 2099-03-31  # a note\n---\nBody\n")
        self.write("unclosed.md", "---\ntitle: never closed\nBody\n")
        self.write("expires.md", "---\ntitle: Old\nexpires: March 31\n---\nx\n")
        self.A.main([])
        env = self.env("announcements")
        by = {i["extra"]["file"].rsplit("/", 1)[-1]: i for i in env["items"]}
        self.assertEqual(by["empty.md"]["extra"]["body_md"], "Just a body line.")
        self.assertEqual(by["colon.md"]["title"], "Reminder: Assembly Saturday")
        self.assertEqual(by["colon.md"]["extra"]["expires"], "2099-03-31")
        errors = " ".join(env["stats"]["errors"])
        self.assertIn("unclosed.md: the header has no closing ---", errors)
        self.assertIn("expires.md: the expires date 'March 31' is not a date", errors)
        self.assertEqual(set(by), {"empty.md", "colon.md"})

    def test_a_mistake_keeps_the_last_good_version(self):
        self.write("live.md", "---\ntitle: Assembly\n---\nSee you there.\n")
        self.A.main([])
        first = self.env("announcements")["items"][0]
        self.write("live.md", "---\ntitle: \"Assembly\nsee: [unclosed\n---\nSee you there.\n")   # broken header
        self.A.main([])
        env = self.env("announcements")
        self.assertEqual(env["stats"]["problems"], 1)
        self.assertEqual([(i["id"], i["first_seen"], i["title"]) for i in env["items"]],
                         [(first["id"], first["first_seen"], "Assembly")])
        (self.ann / "live.md").unlink()                          # deleting the file still removes it
        self.A.main([])
        self.assertEqual(self.env("announcements")["items"], [])

    def test_hand_written_translations_are_kept(self):
        """title_es / summary_es (content/events, content/bulletin) are shown as written — never
        replaced by a machine translation ("Fort Worth" once became "Valía la pena") — and only a
        language left out is machine-translated."""
        from scripts.sync import build_data as B
        self.write("2026-09-26-lv-writing-workshop-fort-worth.md",
                   '---\ntitle: "La Viña Writing Workshop (in Spanish) — Fort Worth"\n'
                   'title_es: "Taller de Escritura de La Viña — Fort Worth"\n'
                   'start: 2026-09-26T19:00:00-05:00\nlocation: "Fort Worth, TX 76111"\nlang: en\n'
                   'summary_es: "Taller en español para aprender a escribir tu historia para La Viña."\n'
                   "---\nA Spanish-language workshop on writing your story for La Viña.\n", self.evs)
        self.write("2027-03-19-assembly.md", "---\ntitle: Spring Assembly\ntitle_es: Asamblea de Primavera\n"
                   "start: 2027-03-19\nlang: en\n---\nArea 65 assembly.\n", self.evs)
        self.write("2027-01-10-bienvenida.md", "---\ntitle: Bienvenidos\nlang: es\ntitle_es: Ignorado\n"
                   "title_en: Welcome\nsummary_en: Welcome, new GVRs.\n---\nBienvenidos, nuevos GVR.\n")
        self.A.main([])
        evs = {i["extra"]["slug"]: i for i in self.env("manual_events")["items"]}
        fw, asm = evs["2026-09-26-lv-writing-workshop-fort-worth"], evs["2027-03-19-assembly"]
        spanish = "Taller en español para aprender a escribir tu historia para La Viña."
        self.assertEqual(fw["extra"]["own_i18n"], {"title": {"es": "Taller de Escritura de La Viña — Fort Worth"},
                                                   "summary": {"es": spanish}, "body_md": {"es": spanish}})
        self.assertEqual(asm["extra"]["own_i18n"], {"title": {"es": "Asamblea de Primavera"}})
        ann = self.env("announcements")["items"][0]
        self.assertEqual(ann["extra"]["own_i18n"]["title"], {"es": "Ignorado", "en": "Welcome"})

        class Tr:                                  # a "machine" that marks what it translated
            def translate(self, texts, src, tgt):
                return [(f"[{tgt}] {t}", True) for t in texts]

            def translate_markdown(self, md, src, tgt):
                return f"[{tgt}] {md}", True

        i18n = B.I18n(Tr())
        items = [B.prep(fw), B.prep(asm), B.prep(ann)]
        B.plan_translations(B.Ctx(offline=True), {"events": items[:2], "announcements": items[2:]}, set(), i18n)
        wanted = {k[3] for k in i18n.jobs}
        self.assertNotIn("La Viña Writing Workshop (in Spanish) — Fort Worth", wanted)   # nothing to translate
        self.assertNotIn("Spring Assembly", wanted)
        self.assertIn("Area 65 assembly.", wanted)                  # no summary_es → still translated
        i18n.run()
        for it in items:
            i18n.apply(it)
        fw_i, asm_i, ann_i = items
        self.assertEqual(fw_i["i18n"]["title"], {"en": "La Viña Writing Workshop (in Spanish) — Fort Worth",
                                                 "es": "Taller de Escritura de La Viña — Fort Worth"})
        self.assertEqual((fw_i["i18n"]["summary"]["es"], fw_i["i18n"]["body_md"]["es"]), (spanish, spanish))
        self.assertEqual(fw_i["i18n"]["body_md"]["en"], "A Spanish-language workshop on writing your story for La Viña.")
        self.assertEqual(fw_i["machine"], [])                       # nothing "auto-translated"
        self.assertEqual(asm_i["i18n"]["title"]["es"], "Asamblea de Primavera")
        self.assertEqual(asm_i["i18n"]["body_md"]["es"], "[es] Area 65 assembly.")
        self.assertEqual(asm_i["machine"], ["es"])                  # only the description was machine-translated
        # a file written in Spanish: title_en / summary_en are its English; its own-language title_es is ignored
        self.assertEqual(ann_i["i18n"]["title"], {"es": "Bienvenidos", "en": "Welcome"})
        self.assertEqual(ann_i["i18n"]["body_md"], {"es": "Bienvenidos, nuevos GVR.", "en": "Welcome, new GVRs."})
        self.assertEqual(ann_i["machine"], [])

    def test_an_event_end_written_as_a_time_or_before_the_start(self):
        """content/events `end:` as a clock time — "end: 21:00" (YAML reads it unquoted as the number 1260),
        "9 PM", "1:00" after an evening start — is that time on the start's day (the next morning when it is
        not after the start), never a date in the year 1260 or the day of the run. An end before the start,
        or a time after a start that has none, is a mistake shown on /status/; the last good version stays."""
        heads = {"2026-11-14-workshop.md": "start: 2026-11-14T19:00:00-06:00\nend: 21:00\n",
                 "2026-11-21-workshop.md": 'start: 2026-11-21T19:00:00-06:00\nend: "9 PM"\n',
                 "2026-12-31-dance.md": "start: 2026-12-31T20:00:00-06:00\nend: 1:00\n",
                 "2027-03-19-assembly.md": "start: 2027-03-19\nend: 2027-03-21\n"}
        for name, head in heads.items():
            self.write(name, f"---\ntitle: X\n{head}---\nx\n", self.evs)
        self.A.main([])
        env = self.env("manual_events")
        self.assertEqual({i["extra"]["slug"]: (i["extra"]["start"], i["extra"]["end"]) for i in env["items"]}, {
            "2026-11-14-workshop": ("2026-11-15T01:00:00Z", "2026-11-15T03:00:00Z"),
            "2026-11-21-workshop": ("2026-11-22T01:00:00Z", "2026-11-22T03:00:00Z"),
            "2026-12-31-dance": ("2027-01-01T02:00:00Z", "2027-01-01T07:00:00Z"),
            "2027-03-19-assembly": ("2027-03-19", "2027-03-21")})
        self.assertEqual(env["stats"]["problems"], 0)
        self.write("2027-03-19-assembly.md", "---\ntitle: X\nstart: 2027-03-19\nend: 2027-03-12\n---\nx\n", self.evs)
        self.write("2026-11-28-open-house.md", '---\ntitle: X\nstart: 2026-11-28\nend: "9 PM"\n---\nx\n', self.evs)
        self.A.main([])
        env = self.env("manual_events")
        errors = " ".join(env["stats"]["errors"])
        self.assertIn("2027-03-19-assembly.md: the end '2027-03-12' is before the start", errors)
        self.assertIn("2026-11-28-open-house.md: end: 21:00 is a time of day, but start: has no time", errors)
        ends = {i["extra"]["slug"]: i["extra"]["end"] for i in env["items"]}
        self.assertEqual(ends["2027-03-19-assembly"], "2027-03-21")          # the last good version
        self.assertNotIn("2026-11-28-open-house", ends)

    def test_word_dates_without_a_time_are_all_day(self):
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        for text in ("March 14, 2027", "03/14/2027", "Sat March 14 2027", "14 de marzo de 2027", "2027-03-14"):
            self.assertEqual(self.A.as_when(text, tz), ("2027-03-14", True), text)
        self.assertEqual(self.A.as_when("March 14, 2027 9 AM", tz), ("2027-03-14T14:00:00Z", False))

    def test_word_dates_in_spanish_keep_their_time(self):
        """A start written in Spanish words with a time is a timed event, not "All day" (the date reader
        knows no Spanish month names). A range ("de 7 a 9 p. m.") is not guessed at: all-day, as before."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        cases = {"14 de marzo de 2027 19:00": "2027-03-15T00:00:00Z",                  # CDT (from March 14)
                 "sábado 14 de marzo de 2027, 7:00 p. m.": "2027-03-15T00:00:00Z",
                 "14 de noviembre de 2026 a las 7 pm": "2026-11-15T01:00:00Z",           # CST
                 "14 de marzo de 2027 a las 12 p.m.": "2027-03-14T17:00:00Z"}
        for text, want in cases.items():
            self.assertEqual(self.A.as_when(text, tz), (want, False), text)
        for text, day in (("sábado 14 de marzo de 2027 de 7:00 a 9:00 p. m.", "2027-03-14"),
                          ("14 de noviembre de 2026 de 7 a 9 pm", "2026-11-14"),
                          ("14 de marzo de 2027 13 pm", "2027-03-14"), ("14 de marzo de 2027 7:75 pm", "2027-03-14")):
            self.assertEqual(self.A.as_when(text, tz), (day, True), text)


class MediaFixes(unittest.TestCase):
    def test_a_link_shared_by_another_show_is_not_an_episode_page(self):
        from types import SimpleNamespace
        from scripts.sync import podcasts as P
        general = "https://www.aagrapevine.org/podcast"

        def feed(key, n, link):
            entries = [{"title": f"{key} {i}", "id": f"{key}-{i}", "link": link,
                        "links": [{"rel": "enclosure", "href": f"https://podcasts.captivate.fm/media/"
                                   f"0000000{i}-0000-0000-0000-00000000000{i}/x.mp3"}]} for i in range(n)]
            return SimpleNamespace(feed={"title": key, "link": f"https://www.aagrapevine.org/{key}"}, entries=entries)
        shows = [{"key": "gv", "feed": "https://feeds.example/gv", "web": general},
                 {"key": "wo", "feed": "https://feeds.example/wo", "web": "https://www.aagrapevine.org/grapevine-weekly-open"}]
        feeds = {"gv": feed("gv", 3, general), "wo": feed("wo", 1, general)}
        counts, generic = P.shared_link_info(shows, feeds)
        wo = P.build_items(shows[1], feeds["wo"], link_counts=counts, generic_pages=generic)
        self.assertTrue(wo[0]["url"].startswith("https://player.captivate.fm/episode/"), wo[0]["url"])

    def test_flat_listing_estimates_never_replace_exact_values(self):
        from scripts.sync import youtube as Y
        v = Y.Video("abcdefghijk")
        v.duration, v.duration_approx, v.views, v.views_approx = 3304, True, 3800, True
        self.assertEqual(Y.merged_duration_views(v, {"duration_sec": 3303, "views": 3875}), (3303, 3875))
        v.views = 4100                                            # a higher estimate: views only go up
        self.assertEqual(Y.merged_duration_views(v, {"duration_sec": 3303, "views": 3875})[1], 4100)
        v.duration, v.duration_approx, v.views, v.views_approx = 3600, False, 3700, False   # exact details
        self.assertEqual(Y.merged_duration_views(v, {"duration_sec": 3303, "views": 3875}), (3600, 3700))
        col = Y.Collector()
        col.add_flat({"id": "abcdefghijk", "title": "T", "duration": 61, "view_count": 3800}, "UC")
        w = col.videos["abcdefghijk"]
        self.assertTrue(w.duration_approx and w.views_approx)

    def test_texas_city_without_a_state(self):
        from scripts.sync import events_external as E
        for loc in ("Iglesia San Juan Diego, Houston", "Hotel Adolphus, 1321 Commerce St, Dallas",
                    "Centro Comunitario - Fort Worth"):
            self.assertTrue(E.decide({"title": "Taller", "location_raw": loc, "lang": "es"}).get("texas"), loc)
        for loc in ("Hotel X, Paris", "Centro, Lancaster", "Hotel, Houston, Mexico"):
            self.assertFalse(E.decide({"title": "Taller", "location_raw": loc, "lang": "es"}).get("texas"), loc)


class ArchiveDepartments(unittest.TestCase):
    def test_every_issue_slugs(self):
        from scripts.sync import articles as AR
        for slug in ("alcoholism-large", "alcoholism-large-july-2026", "cartas-del-lector"):
            self.assertTrue(AR.DEPARTMENT_SLUG_RE.match(slug), slug)


class PdfTitles(unittest.TestCase):
    def test_link_texts(self):
        from scripts.sync import crawl_rules as R
        for t in ("/ Download letter", "Read / Download Letter", "Leer / Descargar Carta", "Download letter",
                  "Download the announcement PDF version here", "View | Download"):
            self.assertIsNone(R.clean_link_text(t), t)
        self.assertEqual(R.clean_link_text("Descarga el Poster de la App"), "Poster de la App")
        self.assertEqual(R.clean_link_text("GV/LV Workshop"), "GV/LV Workshop")
        self.assertEqual(R.language_of_link("Read it in Spanish here"), "es")
        self.assertEqual(R.language_of_link("French and Spanish click here"), R.MULTILINGUAL)
        self.assertEqual(R.language_of_link("Inglés y Español"), R.MULTILINGUAL)
        self.assertEqual(R.language_of_link("leer en Inglés"), "en")
        self.assertIsNone(R.language_of_link("Women in AA (Spanish-language)"))

    def test_titles_categories_languages(self):
        from scripts.sync import crawl_rules as R
        form = "https://www.aalavina.org/sites/default/files/2020-08/Formulario%20Pedido%20de%20Materiales%20Gratuitos%20.pdf"
        self.assertEqual(R.choose_title(link_texts=[], img_alts=[], meta_title=None, text_heading=None, url=form,
                                        page_title="Calendario de Eventos"),
                         ("Formulario Pedido de Materiales Gratuitos", "file"))
        self.assertEqual(R.choose_title(link_texts=[], img_alts=[], meta_title=None, text_heading=None,
                                        url="https://x/Announcement_GV-Podcast.pdf", page_title="Grapevine's New Podcast"),
                         ("Grapevine's New Podcast", "page"))
        self.assertEqual(R.choose_title(link_texts=[], img_alts=[], meta_title="SP Letter to the Fellowship",
                                        text_heading=None, url="https://x/SP_Letter.pdf")[0], "Letter to the Fellowship")
        news = R.classify(referrer_urls=["https://www.aagrapevine.org/anncmnt", "https://www.aalavina.org/anuncio-2021"],
                          texts=["New Publisher (English)"], sections=[], url="https://x/y.pdf")
        self.assertEqual(news[0], "news", "a news page that is not the last referrer counts too")
        policy = R.classify(referrer_urls=["https://www.aagrapevine.org/agreement"], texts=["Privacy Policy"],
                            sections=["Agreement for AAGrapevine.org Usage, Grapevine Online Subscription & Grapevine S"],
                            url="https://x/Privacy-Policy.pdf")
        self.assertEqual(policy[0], "guidelines")
        self.assertTrue(R.multilingual_heading("Catalog • Catálogo • Catalogue"))
        self.assertEqual(R.doc_language(url="https://x/LV_Catalogo_2026.pdf", texts=["Catálogo 2026"], text_sample=None,
                                        text_lang="en", host_prior="es", multilingual=True), "es")
        # an English front + Spanish back (text sample mostly Spanish) on an English kit page
        self.assertEqual(R.doc_language(url="https://x/GV_LV_annual_Prices_2024.pdf", texts=["GV Annual Prices"],
                                        text_sample=None, text_lang="es", host_prior="en",
                                        heading="Subscription Prices", link_text="GV Annual Prices"), "en")
        self.assertEqual(R.doc_language(url="https://x/GV_catalog_postcard_2026.pdf", texts=["2026 Catalog Postcard"],
                                        text_sample=None, text_lang="es", host_prior="en",
                                        heading="Aagrapevine /la Viña", link_text="2026 Catalog Postcard"), "en")
        # a Spanish document linked from an English page keeps its language
        self.assertEqual(R.doc_language(url="https://x/Libres.pdf", texts=["Libres por dentro"], text_sample=None,
                                        text_lang="es", host_prior="en", heading="Muy Pronto – ¡dos Nuevos Libros!",
                                        link_text="Libres por dentro: Historias de recuperación"), "es")

    def test_title_overrides_for_unusable_names(self):
        from scripts.sync import crawl_rules as R
        for url, title in (
                ("https://www.aagrapevine.org/sites/default/files/2023-01/GV__Survey_Letter.pdf",
                 "Letter about the Grapevine and La Viña Apps Survey"),
                ("https://www.aalavina.org/sites/default/files/2020-08/Formulario%20Pedido%20de%20Materiales%20Gratuitos%20.pdf",
                 "Formulario de pedido de materiales gratuitos")):
            self.assertEqual(R.TITLE_OVERRIDES.get(R.filename_of(url)), title)
        for k, v in R.TITLE_OVERRIDES.items():
            self.assertTrue(k.lower().endswith(".pdf") and "%" not in k and v.strip() == v and v, k)

    def test_junk_links_are_not_pages(self):
        from scripts.sync import crawl_rules as R
        base = "https://www.aalavina.org/website-policy"
        for href in ("registration@midwinterconference.com ", "www.aagrapevine.org", "store.aagrapevine.org/x",
                     "lveditorial%40aagrapevine.org"):
            self.assertIsNone(R.normalize_page_url(href, base), href)
        self.assertEqual(R.normalize_page_url("servicio/rlv", base), "https://www.aalavina.org/servicio/rlv")
        self.assertFalse(R.should_crawl_path("/www.aagrapevine.org"))
        self.assertFalse(R.should_crawl_path("/get-involved/events/2013-01-17/registration%40x.com%20"))
        self.assertNotIn("https://www.aagrapevine.org/home", R.hub_urls(), "a redirect is not a hub")


class CrawlerRechecks(unittest.TestCase):
    def crawler(self, pdfs):
        from scripts.sync import crawl as C
        st = {"pages": {}, "pdfs": pdfs, "sitemaps": {}, "runs": []}
        with mock.patch.object(C, "shared_session", lambda: None):
            return C, C.Crawler(st, minutes=1, details_cap=0, recheck_days=21, max_mb=1, max_pages=None,
                                dry_run=True, only_urls=None, use_sitemap=False)

    def test_stop_is_not_swallowed(self):
        from scripts.sync import crawl as C
        self.assertTrue(issubclass(C.Stop, BaseException) and not issubclass(C.Stop, Exception))

    def test_gone_but_linked_pdf_is_checked_again(self):
        old = iso(datetime.now(timezone.utc) - timedelta(days=400))
        C, cr = self.crawler({"k": {"url": "https://x.test/a.pdf", "status": "gone", "external": True,
                                    "refs": [{"url": "https://www.aagrapevine.org/gvr-resources"}],
                                    "head": {"status": 404, "checked_at": old}}})
        cr.push_pdf("k")
        self.assertEqual([k for _p, k, _key in cr.pdf_q], ["periodic"])
        C2, cr2 = self.crawler({"k": {"url": "https://x.test/a.pdf", "status": "gone", "refs": [],
                                      "head": {"status": 404, "checked_at": old}}})
        cr2.push_pdf("k")
        self.assertEqual(cr2.pdf_q, [], "no page links it → no reason to look again")

    def test_gone_needs_two_failing_checks_a_day_apart(self):
        C, cr = self.crawler({})
        rec = {"url": "https://x.test/a.pdf", "status": "ok", "refs": [{"url": "u"}]}
        cr._apply_head(rec, {"status": 404, "checked_at": iso(datetime.now(timezone.utc))})
        self.assertEqual(rec["status"], "ok")
        self.assertIn("gone_strike_at", rec)
        cr._apply_head(rec, {"status": 404})                      # the same day: still one strike
        self.assertEqual(rec["status"], "ok")
        rec["gone_strike_at"] = iso(datetime.now(timezone.utc) - timedelta(hours=30))
        cr._apply_head(rec, {"status": 200, "type": "text/html"})   # an error page instead of the file
        self.assertEqual(rec["status"], "gone")
        cr._apply_head(rec, {"status": 200, "type": "application/pdf"})
        self.assertEqual(rec["status"], "ok")
        self.assertNotIn("gone_since", rec)

    def test_dead_external_host_is_retired_after_a_month(self):
        C, cr = self.crawler({})
        rec = {"url": "http://www.aataiwan.com/x.pdf", "status": "ok", "external": True}
        for _ in range(3):
            cr._unreachable(rec)
        self.assertEqual(rec["status"], "ok")
        rec["head"]["unreachable_since"] = iso(datetime.now(timezone.utc) - timedelta(days=31))
        cr._unreachable(rec)
        self.assertEqual(rec["status"], "gone")
        own = {"url": "https://www.aagrapevine.org/sites/default/files/x.pdf", "status": "ok", "external": False,
               "head": {"fails": 9, "unreachable_since": "2020-01-01T00:00:00Z", "error": "unreachable"}}
        cr._unreachable(own)
        self.assertEqual(own["status"], "ok", "the magazine sites' own files are never retired this way")


class RedirectsArePaced(unittest.TestCase):
    def test_every_hop_waits_and_is_checked(self):
        clock = FakeClock()
        stamps = []
        hops = {"https://www.aagrapevine.org/home": "https://www.aagrapevine.org/",
                "https://www.aagrapevine.org/": None}

        def fake_request(_self, method, url, **kw):
            stamps.append((clock.t, url, kw.get("allow_redirects")))
            nxt = hops.get(url)
            return Resp(301, headers={"Location": nxt}, url=url) if nxt else Resp(200, url=url)

        with mock.patch.object(common.time, "monotonic", clock.monotonic), \
                mock.patch.object(common.time, "sleep", clock.sleep), \
                mock.patch("requests.Session.request", fake_request):
            s = common.PoliteSession(min_delay=5.0, respect_robots=False)
            r = s.get("https://www.aagrapevine.org/home")
        self.assertEqual(r.url, "https://www.aagrapevine.org/")
        self.assertEqual([u for _t, u, _f in stamps], list(hops))
        self.assertEqual(stamps[1][0] - stamps[0][0], 5.0, "the redirect hop waits the crawl delay")
        self.assertTrue(all(f is False for _t, _u, f in stamps))


class LaunchDayCutoff(TempRaw):
    def test_first_harvest_does_not_move_when_old_items_are_dropped(self):
        from scripts.sync import build_data as B
        day1 = iso(datetime.now(timezone.utc) - timedelta(days=30))
        common.save_raw("events_external", [{"id": "ev:1", "first_seen": day1, "date": "2026-01-01"}])
        self.assertEqual(self.env("events_external")["first_harvest"], day1)
        today = iso(datetime.now(timezone.utc) - timedelta(hours=1))
        # the old event is past and dropped; a newly announced one arrives
        new = {"id": "ev:2", "kind": "event", "source": "grapevine", "first_seen": today, "date": "2027-01-01",
               "category": "gv", "extra": {}}
        common.save_raw("events_external", [new])
        self.assertEqual(self.env("events_external")["first_harvest"], day1)
        c = B.Ctx(offline=True)
        with mock.patch.object(B, "RAW_DIR", self.raw):
            c.load_raw()
        self.assertTrue(c.is_new(new, "events_external"), "a newly announced event is news")
        common.save_raw("empty_source", [])
        self.assertTrue(self.env("empty_source")["first_harvest"], "stamped even with 0 items")


# --------------------------------------------------------------------------- run_all
class RunAllStartFailure(TempRaw):
    """A module that cannot even start — it does not import (a syntax error, a dependency that breaks at
    import time) or has no main() — is a failed source like one that crashes: its data/raw file says
    ok=false and why, so /status/ and the run summary show it and the "stopped updating" issue can open.
    What the file held (items, extras, the last success) is kept."""

    def test_the_raw_file_says_why_and_keeps_what_it_held(self):
        from types import SimpleNamespace
        from scripts.sync import run_all as R
        cases = [("import error", "SyntaxError: invalid syntax (youtube.py, line 948)",
                  SyntaxError("invalid syntax (youtube.py, line 948)")),
                 ("import error", "ModuleNotFoundError: No module named 'feedparser'",
                  ModuleNotFoundError("No module named 'feedparser'", name="feedparser")),
                 ("missing", "ModuleNotFoundError: No module named 'scripts.sync.youtube'",
                  ModuleNotFoundError("No module named 'scripts.sync.youtube'", name="scripts.sync.youtube")),
                 ("missing", "no main()", SimpleNamespace())]
        for status, why, answer in cases:
            common.save_raw("youtube", [{"id": "yt:1", "title": "A video", "first_seen": "2026-01-01T00:00:00Z"}],
                            stats={"new": 0}, extra={"channel_ids": ["UC1"]})
            before = self.env("youtube")

            def import_module(name, answer=answer):
                if isinstance(answer, BaseException):
                    raise answer
                return answer
            with mock.patch.object(R.importlib, "import_module", import_module):
                row = R.run_source("youtube", [])
            env = self.env("youtube")
            self.assertEqual((row["status"], row["note"]), (status, why))
            self.assertEqual((env["ok"], env["error"]), (False, why), why)
            for k in ("items", "updated", "stats", "first_harvest", "channel_ids"):
                self.assertEqual(env[k], before[k], f"{why}: {k}")
        # the crawl writes pdfs.json
        common.save_raw("pdfs", [{"id": "pdf:1", "title": "A PDF", "first_seen": "2026-01-01T00:00:00Z"}])
        with mock.patch.object(R.importlib, "import_module", side_effect=ImportError("cannot import name 'x'")):
            R.run_source("crawl", [])
        self.assertEqual((self.env("pdfs")["ok"], len(self.env("pdfs")["items"])), (False, 1))
        self.assertFalse((self.raw / "crawl.json").exists())


class RunAllModes(unittest.TestCase):
    """run_all's lists and modes: the writers archive (content/archive, no request) in every mode; `--also` adds
    sources to a quick run (a push that changed what they read); the run table says which kind of run it was."""

    def run_all(self, *flags: str) -> tuple[list[str], dict[str, list[str]], str, list[str]]:
        """run_all.main with stand-in modules → (the modules run, in order; their arguments; the run summary; the
        log lines)."""
        import io
        import os
        from contextlib import redirect_stdout
        from scripts.sync import run_all as R
        calls: list[tuple[str, list[str]]] = []

        def fake(name, args):
            calls.append((name, list(args)))
            return {"module": name, "status": "ok", "seconds": 0.0, "items": 0, "new": 0, "note": ""}
        tmp = Path(tempfile.mkdtemp(prefix="gv-runall-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        summary = tmp / "summary.md"
        summary.write_text("", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "GV_CRAWL_MINUTES"}
        env["GITHUB_STEP_SUMMARY"] = str(summary)
        with mock.patch.object(R, "run_source", fake), mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("scripts.sync.quote.local_today", return_value=date(2026, 10, 6)), \
                self.assertLogs("run_all", "INFO") as logs, redirect_stdout(io.StringIO()):
            R.log.info("start")          # (assertLogs needs one line even when run_all logs nothing)
            self.assertEqual(R.main([*flags, "--no-build"]), 0)
        return [n for n, _a in calls], dict(calls), summary.read_text(encoding="utf-8"), logs.output

    def test_the_lists(self):
        from scripts.sync import run_all as R
        self.assertEqual(R.MODULES[-2:], ["quote", "crawl"])
        self.assertLess(R.MODULES.index("writers_archive"), R.MODULES.index("quote"))
        self.assertEqual(list(R.QUICK_MODULES), [m for m in R.MODULES if m in R.QUICK_MODULES], "in MODULES order")
        self.assertIn("writers_archive", R.QUICK_MODULES)
        self.assertNotIn("writers_archive", R.FULL_ONLY, "it never holds back the Morning check's full-update rule")

    def test_every_mode_reads_the_archive_files(self):
        for flags, before in (((), "quote"), (("--quick",), "quote"), (("--morning",), None)):
            order, _args, _s, _l = self.run_all(*flags, "--crawl-minutes", "0")
            self.assertIn("writers_archive", order, flags)
            if before:       # right before the daily quote (the morning refresh reads the quote second)
                self.assertEqual(order[order.index("writers_archive") + 1], before, flags)
            else:
                self.assertEqual(order[-1], "writers_archive", flags)

    def test_also_adds_sources_to_a_quick_run(self):
        order, args, summary, _logs = self.run_all("--quick", "--also", "weekly_open,instagram")
        self.assertEqual(order, ["drive", "announcements", "podcasts", "instagram", "weekly_open", "writers_archive",
                                 "quote"], "in the usual order")
        self.assertEqual(args["instagram"], ["--no-enrich"], "with their quick options")
        self.assertRegex(summary, r"\| instagram \| ✅ ok \|")
        self.assertRegex(summary, r"\| youtube \| ⏭️ skipped \| [\d.]+ \|  \|  \| --quick \|")
        self.assertIn("### Quick refresh", summary)

    def test_also_never_adds_the_crawl_or_an_unknown_name(self):
        order, _args, summary, logs = self.run_all("--quick", "--also", "crawl,meetngs,meetings")
        self.assertIn("meetings", order)
        self.assertNotIn("crawl", order)
        self.assertTrue(any("--also: ['crawl', 'meetngs'] ignored" in m for m in logs), logs)
        self.assertRegex(summary, r"\| crawl \| ⏭️ skipped \| [\d.]+ \|  \|  \| --quick \|")

    def test_also_only_with_quick(self):
        order, _args, summary, logs = self.run_all("--morning", "--also", "instagram")
        self.assertNotIn("instagram", order)
        self.assertTrue(any("is only used with --quick" in m for m in logs), logs)
        self.assertIn("### Morning refresh", summary)
        order, _args, summary, _logs = self.run_all("--also", "instagram", "--crawl-minutes", "0")
        self.assertIn("youtube", order, "a full run reads everything anyway")
        self.assertIn("### Full update", summary)

    def test_the_run_titles(self):
        from scripts.sync import run_all as R
        self.assertEqual((R.run_title(False, False), R.run_title(True, False), R.run_title(False, True),
                          R.run_title(True, True)), ("Full update", "Quick refresh", "Morning refresh", "Morning refresh"))

    def test_only_a_full_run_moves_full_update(self):
        """A push run's --also instagram writes instagram's `attempted`; build_data.full_update() would then say a
        full update just ran and the Morning check would skip the 1st of the month's — so quick and morning runs
        ask build_data to keep status.json full_update (--keep-full-update), and only a full run computes it."""
        import io
        import os
        from contextlib import redirect_stdout
        from scripts.sync import run_all as R
        seen: list[list[str]] = []
        fake_bd = mock.MagicMock()
        fake_bd.main.side_effect = lambda args: seen.append(list(args)) or 0
        env = {k: v for k, v in os.environ.items() if k not in ("GV_CRAWL_MINUTES", "GITHUB_STEP_SUMMARY")}
        for flags, keep in ((("--quick", "--also", "instagram"), True), (("--quick",), True), (("--morning",), True),
                            (("--crawl-minutes", "0"), False), (("--only", "writers_archive"), False)):
            seen.clear()
            with mock.patch.object(R, "run_source", lambda n, a: {"module": n, "status": "ok", "seconds": 0.0,
                                                                   "items": 0, "new": 0, "note": ""}), \
                    mock.patch.dict("sys.modules", {"scripts.sync.build_data": fake_bd}), \
                    mock.patch.object(sys.modules["scripts.sync"], "build_data", fake_bd, create=True), \
                    mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch("scripts.sync.quote.local_today", return_value=date(2026, 10, 6)), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(R.main(list(flags)), 0)
            self.assertEqual(len(seen), 1, flags)
            self.assertEqual("--keep-full-update" in seen[0], keep, flags)

    def test_the_pause_setting_is_read_like_the_plan_step(self):
        from scripts.sync import run_all as R
        for value, paused in ((0, True), ("0", True), (0.5, True), (-5, True), (40, False), ("40", False),
                              (None, False), ("", False), ("soon", False)):
            self.assertEqual(R.crawl_paused({"sources": {"crawler": {"minutes_per_run": value}}}), paused, value)
        self.assertFalse(R.crawl_paused({}), "not set: 40")
        self.assertFalse(R.crawl_paused({"sources": "nonsense"}))

    def test_kept_full_update(self):
        from scripts.sync import build_data as B
        tmp = Path(tempfile.mkdtemp(prefix="gv-fullupd-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        st = tmp / "status.json"
        self.assertEqual(B.kept_full_update(st, "2026-10-04T12:00:00Z"), "2026-10-04T12:00:00Z", "no earlier build")
        st.write_text(json.dumps({"full_update": "2026-10-03T12:23:00Z"}), encoding="utf-8")
        self.assertEqual(B.kept_full_update(st, "2026-10-04T18:00:00Z"), "2026-10-03T12:23:00Z", "the last value stays")
        st.write_text(json.dumps({"full_update": None}), encoding="utf-8")
        self.assertEqual(B.kept_full_update(st, None), None)
        self.assertEqual(B.kept_full_update(st, "2026-10-04T18:00:00Z"), "2026-10-04T18:00:00Z")
        st.write_text("{not json", encoding="utf-8")
        self.assertEqual(B.kept_full_update(st, "2026-10-04T18:00:00Z"), "2026-10-04T18:00:00Z", "unreadable → computed")


class RunAllPausedCrawl(TempRaw):
    """The nightly full update while the PDF search is paused (config/site.yml sources.crawler.minutes_per_run: 0 —
    the workflow then passes --crawl-minutes 0): the crawl's try is noted in data/raw/pdfs.json `attempted` and
    nothing else moves (not `updated`, the last success), so the run summary never calls the paused search "not
    checked for N days" — also on the first runs after the pause ends. Not in a quick or morning run, not in a
    0-minute run started by hand while the search is on, and not while the file says ok=false."""

    def setUp(self):
        super().setUp()
        with mock.patch.object(common, "now_iso", return_value="2026-10-04T06:40:00Z"):
            common.save_raw("pdfs", [{"id": "pdf:1", "title": "A document", "first_seen": "2026-01-01T00:00:00Z"}],
                            stats={"known_pages": 9, "new": 0}, extra={"crawl": {"known_pages": 9}})
        self.text = (self.raw / "pdfs.json").read_text(encoding="utf-8")

    def run_all(self, minutes_per_run, *flags: str) -> str:
        """run_all.main (stand-in modules, the setting given) on 2026-10-14 → the printed run table."""
        import io
        import os
        from contextlib import redirect_stdout
        from scripts.sync import run_all as R
        env = {k: v for k, v in os.environ.items() if k not in ("GV_CRAWL_MINUTES", "GITHUB_STEP_SUMMARY")}
        cfg = {"sources": {"crawler": {"minutes_per_run": minutes_per_run}}}
        out = io.StringIO()
        with mock.patch.object(R, "run_source", lambda n, a: {"module": n, "status": "ok", "seconds": 0.0,
                                                               "items": 0, "new": 0, "note": ""}), \
                mock.patch.object(R, "load_config", lambda: cfg), \
                mock.patch.object(R, "now_iso", return_value="2026-10-14T06:40:00Z"), \
                mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("scripts.sync.quote.local_today", return_value=date(2026, 10, 6)), redirect_stdout(out):
            self.assertEqual(R.main([*flags, "--no-build"]), 0)
        return out.getvalue()

    def test_a_paused_full_run_notes_only_the_try(self):
        table = self.run_all(0, "--crawl-minutes", "0")
        self.assertEqual((self.raw / "pdfs.json").read_text(encoding="utf-8"),
                         self.text.replace('"attempted": "2026-10-04T06:40:00Z"',
                                           '"attempted": "2026-10-14T06:40:00Z"'))
        self.assertEqual(self.env("pdfs")["updated"], "2026-10-04T06:40:00Z", "the last success stays")
        self.assertIn("paused (sources.crawler.minutes_per_run: 0)", table)

    def test_nothing_else_notes_it(self):
        for setting, flags in ((40, ("--crawl-minutes", "0")),            # a 0-minute run by hand, the search on
                               (None, ("--crawl-minutes", "0")),          # not set: 40
                               (0, ("--quick",)), (0, ("--quick", "--crawl-minutes", "0")), (0, ("--morning",)),
                               (0, ("--skip", "crawl", "--crawl-minutes", "0"))):
            with self.subTest(setting=setting, flags=flags):
                table = self.run_all(setting, *flags)
                self.assertEqual((self.raw / "pdfs.json").read_text(encoding="utf-8"), self.text)
                self.assertNotIn("paused (", table)
        with mock.patch.object(common, "now_iso", return_value="2026-10-04T06:40:00Z"):
            common.save_raw("pdfs", [], ok=False, error="no page could be fetched — site down?")
        failed = (self.raw / "pdfs.json").read_text(encoding="utf-8")
        self.run_all(0, "--crawl-minutes", "0")
        self.assertEqual((self.raw / "pdfs.json").read_text(encoding="utf-8"), failed,
                         "a failed crawl keeps its last try")
        (self.raw / "pdfs.json").unlink()
        self.run_all(0, "--crawl-minutes", "0")
        self.assertFalse((self.raw / "pdfs.json").exists(), "no file: none is made")


if __name__ == "__main__":
    unittest.main()
