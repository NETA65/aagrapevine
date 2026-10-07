"""scripts/sync/articles.py over saved pages — the magazines' current issue, archive and story pages →
data/raw/articles.json. (The archive walk's own rules are in tests/test_spotlight.py.)

Saved pages in tests/fixtures/articles/ (offline — nothing here goes to the network), shaped like the live pages from
the selectors the module reads; titles, bylines and teasers are made up, and no story text is in them:
  gv_magazine.html / lv_revista.html     the current issue: header (label, theme, blurb, cover, the issue's address
                                         behind the log-in link), teaser cards, the "In Every Issue" box, links that
                                         are not this issue's stories
  gv_archive.html / lv_archivo.html      one archive page each (the last: no "Next")
  gv_article_paywall.html, gv_article_exclusive.html, lv_article.html
                                         story pages: a paywalled one, a free "Online Exclusive", La Viña's
Run:  python -m unittest tests.test_articles_pages -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import articles as AR  # noqa: E402
from scripts.sync import common  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "articles"
GV, LV = "https://www.aagrapevine.org", "https://www.aalavina.org"
QUIET = f"{GV}/magazine/2026/oct/quiet-morning"
FRIEND = f"{GV}/magazine/2026/sep/old-friend"
CAFE = f"{LV}/revista/septiembre-octubre-2026/el-cafe-de-las-siete"


def page(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class Hubs(unittest.TestCase):
    def test_grapevine_current_issue(self):
        issue, cards = AR.parse_hub(page("gv_magazine.html"), f"{GV}/magazine", "gv")
        self.assertEqual(issue, {
            "label": "October 2026", "theme": "Loneliness", "key": "2026-10",
            "description": "October’s special section is about “Loneliness.” Members share how they got through it.",
            "url": f"{GV}/magazine-issue/october-2026",
            "image": f"{GV}/sites/default/files/styles/issue_feature_image/public/2026-09/Hero%20GV%20Oct%202026.jpg?itok=TEST"})
        by = {c["url"].rsplit("/", 1)[-1]: c for c in cards}
        # the old issue's sample, La Viña's story and the store are not this issue's stories
        self.assertEqual(set(by), {"quiet-morning", "table-for-one", "letter-editor-october-2026",
                                   "dear-grapevine-october-2026"})
        q = by["quiet-morning"]
        self.assertEqual((q["title"], q["author"], q["author_location"]), ("A Quiet Morning", "Sam T.", "Tyler, Texas"))
        self.assertEqual(q["teaser"], "The coffee was still hot when the phone rang. It was my sponsor, and she had a "
                                      "question for me.")
        self.assertTrue(q["image"].startswith(f"{GV}/sites/default/files/styles/card_image/"))
        self.assertFalse(q["department"])
        t = by["table-for-one"]
        self.assertEqual((t["author"], t["author_location"]), ("Anonymous", None))
        self.assertTrue(t["teaser"].endswith("met at…"), t["teaser"])       # Drupal cut it mid-word: a whole word + …
        self.assertTrue(by["letter-editor-october-2026"]["department"])
        self.assertEqual(by["dear-grapevine-october-2026"]["title"], "Dear Grapevine")

    def test_la_vina_current_issue(self):
        issue, cards = AR.parse_hub(page("lv_revista.html"), f"{LV}/la-revista", "lv")
        self.assertEqual((issue["label"], issue["key"], issue["theme"]), ("Septiembre / Octubre 2026", "2026-09",
                                                                         "Servicio en AA"))
        self.assertEqual(issue["url"], f"{LV}/edicion-de-revista/septiembre-octubre-2026")
        by = {c["url"]: c for c in cards}
        self.assertEqual((by[CAFE]["author"], by[CAFE]["author_location"]), ("Rosa M.", "Dallas, Texas"))
        self.assertTrue(by[f"{LV}/revista/septiembre-octubre-2026/cartas-del-lector"]["department"])
        # the other magazine's hub never yields this one's stories
        self.assertEqual(AR.parse_hub(page("lv_revista.html"), f"{LV}/la-revista", "gv")[1], [])


class StoryPages(unittest.TestCase):
    def test_a_paywalled_story(self):
        d = AR.parse_article(page("gv_article_paywall.html"), QUIET)
        self.assertEqual(d, {
            "title": "A Quiet Morning", "issue_label": "October 2026", "topic": "Loneliness",
            "section": "Featured Section", "author": "Sam T.", "author_location": "Tyler, Texas",
            "subtitle": "A phone call at the right time",
            "teaser": "The coffee was still hot when the phone rang. It was my sponsor, and she had a question for me.",
            "image": f"{GV}/sites/default/files/styles/article_image/public/2026-09/quiet-morning-large.jpg?itok=TEST",
            "free": False})

    def test_a_free_online_exclusive(self):
        d = AR.parse_article(page("gv_article_exclusive.html"), FRIEND)
        self.assertTrue(d["online_exclusive"])
        self.assertTrue(d["free"])
        self.assertEqual((d["issue_label"], d["topic"]), ("September 2026", "Sponsorship"))
        self.assertNotIn("section", d)                    # an exclusive prints none (complete without it)
        self.assertEqual(d["image"], f"{GV}/sites/default/files/2026-09/old-friend-og.jpg")    # og:image
        self.assertTrue(AR._is_complete({**d, "title": d["title"]}))

    def test_la_vina_story(self):
        d = AR.parse_article(page("lv_article.html"), CAFE)
        self.assertEqual((d["issue_label"], d["topic"], d["section"]),
                         ("Septiembre / Octubre 2026", "Servicio en AA", "Nuestras historias"))
        self.assertFalse(d["free"])                       # "¿Desea continuar leyendo?"
        self.assertNotIn("online_exclusive", d)


class FakeHttp:
    """The shared session, answering from the saved pages (anything else: 404)."""

    def __init__(self, pages: dict[str, str]):
        self.pages, self.asked, self.requests_made = pages, [], 0

    def get_text(self, url: str) -> str | None:
        self.asked.append(url)
        self.requests_made += 1
        return self.pages.get(url)

    def get(self, url: str):
        text = self.get_text(url)
        return mock.Mock(status_code=200 if text else 404, text=text or "", encoding="utf-8", headers={},
                         content=(text or "").encode())


class Run(unittest.TestCase):
    """main() over the saved pages: hubs → archive → story pages → data/raw/articles.json (data/raw and the
    thumbnail folder redirected to a temporary folder)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-test-"))
        for target, name, value in ((common, "RAW_DIR", self.tmp), (AR, "THUMB_DIR", self.tmp / "thumbs")):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.http = FakeHttp({
            f"{GV}/magazine": page("gv_magazine.html"), f"{LV}/la-revista": page("lv_revista.html"),
            f"{GV}/archive": page("gv_archive.html"), f"{LV}/archivo": page("lv_archivo.html"),
            QUIET: page("gv_article_paywall.html"), FRIEND: page("gv_article_exclusive.html"), CAFE: page("lv_article.html"),
        })
        p = mock.patch.object(AR, "shared_session", return_value=self.http)
        p.start()
        self.addCleanup(p.stop)

    def run_main(self) -> dict:
        # a very long backfill window: the saved stories stay inside it whatever the date of the test run
        AR.main(["--backfill-days", "36500", "--max-seconds", "600"])
        return json.loads((self.tmp / "articles.json").read_text(encoding="utf-8"))

    def test_the_whole_run(self):
        env = self.run_main()
        self.assertTrue(env["ok"], env.get("error"))
        items = {i["id"]: i for i in env["items"]}
        self.assertEqual(set(items), {
            "gv:2026-10:quiet-morning", "gv:2026-10:table-for-one", "gv:2026-10:letter-editor-october-2026",
            "gv:2026-10:dear-grapevine-october-2026", "gv:2026-09:old-friend", "gv:2026-09:letter-editor-september-2026",
            "lv:2026-09:el-cafe-de-las-siete", "lv:2026-09:cartas-del-lector", "lv:2026-07:un-nuevo-dia"})
        q = items["gv:2026-10:quiet-morning"]
        self.assertEqual((q["title"], q["summary"], q["date"], q["lang"], q["category"]),
                         ("A Quiet Morning", "A phone call at the right time", "2026-10-01", "en", "gv"))
        self.assertEqual({k: q["extra"][k] for k in ("issue_label", "issue_theme", "issue_url", "topic", "section",
                                                     "author", "author_location", "free", "online_exclusive")},
                         {"issue_label": "October 2026", "issue_theme": "Loneliness",
                          "issue_url": f"{GV}/magazine-issue/october-2026", "topic": "Loneliness",
                          "section": "Featured Section", "author": "Sam T.", "author_location": "Tyler, Texas",
                          "free": False, "online_exclusive": False})
        self.assertTrue(q["image"].startswith(f"{GV}/sites/default/files/styles/card_image/"))   # the hub card's
        f = items["gv:2026-09:old-friend"]                                     # from the archive + its page
        self.assertEqual((f["extra"]["online_exclusive"], f["extra"]["free"], f["date"]), (True, True, "2026-09-01"))
        self.assertTrue(items["gv:2026-09:letter-editor-september-2026"]["extra"]["department"])
        cafe = items["lv:2026-09:el-cafe-de-las-siete"]
        self.assertEqual((cafe["lang"], cafe["extra"]["issue_label"], cafe["extra"]["section"]),
                         ("es", "Septiembre / Octubre 2026", "Nuestras historias"))
        self.assertEqual(env["issues"]["gv:2026-10"]["theme"], "Loneliness")
        self.assertEqual(env["issues"]["lv:2026-09"]["url"], f"{LV}/edicion-de-revista/septiembre-octubre-2026")
        # La Viña's story listed without a byline: its page was asked for (404 here) and is retried later — never
        # counted as removed while the archive lists it
        self.assertIn(f"{LV}/revista/julio-agosto-2026/un-nuevo-dia", self.http.asked)
        st = env["detail_state"]["lv:2026-07:un-nuevo-dia"]
        self.assertEqual((st["ok"], st["error"], st.get("missing_since")), (False, "HTTP 404", None))
        self.assertEqual(items["lv:2026-07:un-nuevo-dia"]["status"], "ok")
        self.assertEqual(env["archive_state"]["gv"]["backfill_days"], 36500)
        # never the body text: the opening paragraphs are counted, not kept
        self.assertNotIn("would be here", json.dumps(env, ensure_ascii=False))

    def test_a_second_run_asks_only_what_it_must(self):
        self.run_main()
        before = len(self.http.asked)
        env = self.run_main()
        self.assertTrue(env["ok"])
        again = self.http.asked[before:]
        self.assertNotIn(QUIET, again)                     # complete: its page is not read twice
        self.assertNotIn(CAFE, again)
        self.assertEqual(env["stats"]["new"], 0)


class FirstSeenDay(unittest.TestCase):
    """P3-9: a story of a future issue is dated the day it was first seen — that day in Central time, not UTC."""

    def rec(self, key: str = "2026-11") -> dict:
        return {"id": f"gv:{key}:x", "url": f"{GV}/magazine/2026/nov/x", "publication": "gv", "issue_key": key,
                "title": "X"}

    def test_seen_at_8_pm_central_is_that_day(self):
        it = AR.build_item(self.rec(), "2026-10-06T01:00:00Z", {})          # 8:00 PM CDT on October 5
        self.assertEqual(it["date"], "2026-10-05")
        self.assertEqual(it["extra"]["issue_date"], "2026-11-01")
        self.assertEqual(AR.build_item(self.rec(), "2026-10-05T15:00:00Z", {})["date"], "2026-10-05")
        # winter (CST): 11:30 PM on January 9 is still the 9th
        self.assertEqual(AR.build_item(self.rec("2027-02"), "2027-01-10T05:30:00Z", {})["date"], "2027-01-09")

    def test_a_past_issue_keeps_its_cover_date(self):
        self.assertEqual(AR.build_item(self.rec("2026-09"), "2026-10-06T01:00:00Z", {})["date"], "2026-09-01")

    def test_not_seen_yet_is_today_in_central_time(self):
        self.assertEqual(AR.build_item(self.rec("2099-01"), None, {})["date"], common.site_day())


if __name__ == "__main__":
    unittest.main()
