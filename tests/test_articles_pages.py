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
Saved from the live sites on October 16, 2026 and trimmed (their markup and pictures as published, the letters'
opening paragraphs and the stories' titles and teasers replaced):
  lv_revista_nov_dic.html                La Viña's hub the day November / December 2026 went up (a hero banner, no cover)
  lv_carta_bienvenida.html, gv_letter_editor.html
                                         the two editors' letters — the only pages with the portrait front cover
Run:  python -m unittest tests.test_articles_pages -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from io import BytesIO
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


LETTER_NOV = f"{LV}/revista/noviembre-diciembre-2026/carta-de-bienvenida"
LV_COVER = f"{LV}/sites/default/files/2026-10/LV%20cover_Nov-Dec26.jpg"
GV_COVER = f"{GV}/sites/default/files/2026-10/GV%20NOV%2026.jpg"
LV_HERO = f"{LV}/sites/default/files/styles/issue_feature_image/public/2026-10/Hero-LV-NovDic-2026.jpg?itok=q9bzErPy"


def jpeg(w: int, h: int) -> bytes:
    """A plain picture of that size (the covers are 2000 × ~2860; the hero banner 600 × 400)."""
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (w, h), (176, 65, 11)).save(buf, "JPEG")
    return buf.getvalue()


class ImageHttp(FakeHttp):
    """FakeHttp that also serves pictures (`images`: url → JPEG bytes)."""

    def __init__(self, pages: dict[str, str], images: dict[str, bytes] | None = None):
        super().__init__(pages)
        self.images = images or {}

    def get(self, url: str):
        if url in self.images:
            self.asked.append(url)
            self.requests_made += 1
            return mock.Mock(status_code=200, text="", encoding=None, headers={"Content-Type": "image/jpeg"},
                             content=self.images[url])
        return super().get(url)


class Covers(unittest.TestCase):
    """The issue's portrait front cover (module docstring §3, COVERS): only the editor's letter shows it (saved pages
    lv_carta_bienvenida.html, gv_letter_editor.html); it is read first, the day the issue goes up (lv_revista_nov_dic.html:
    La Viña's November / December 2026, whose cover the run of October 16, 2026 missed), and a banner is never taken for a
    cover."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-test-"))
        for target, name, value in ((common, "RAW_DIR", self.tmp), (AR, "THUMB_DIR", self.tmp / "thumbs")):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def serve(self, letter: str | None, images: dict[str, bytes] | None = None) -> ImageHttp:
        pages = {f"{LV}/la-revista": page("lv_revista_nov_dic.html")}
        if letter is not None:
            pages[LETTER_NOV] = letter
        self.http = ImageHttp(pages, {LV_COVER: jpeg(2000, 2863), LV_HERO: jpeg(600, 400), **(images or {})})
        p = mock.patch.object(AR, "shared_session", return_value=self.http)
        p.start()
        self.addCleanup(p.stop)
        return self.http

    def run_lv(self, *extra: str) -> dict:
        # no story page but the letter: the caps are 0 — the letter is read outside them
        AR.main(["--only", "lv", "--no-archive", "--max-details", "0", "--max-byline-details", "0",
                 "--backfill-days", "36500", *extra])
        return json.loads((self.tmp / "articles.json").read_text(encoding="utf-8"))

    # ---- the pages
    def test_the_editor_letters_show_the_portrait_cover(self):
        lv = AR.parse_article(page("lv_carta_bienvenida.html"), LETTER_NOV)
        self.assertEqual((lv["image"], lv["image_size"]), (LV_COVER, [2000, 2863]))
        self.assertEqual((lv["issue_label"], lv["section"]), ("Noviembre / Diciembre 2026", "En cada edición"))
        gv = AR.parse_article(page("gv_letter_editor.html"), f"{GV}/magazine/2026/nov/letter-editor-november-2026")
        self.assertEqual((gv["image"], gv["image_size"]), (GV_COVER, [2000, 2857]))
        self.assertEqual(gv["section"], "In Every Issue")
        # the hub's issue picture is the hero banner, not a cover
        issue, cards = AR.parse_hub(page("lv_revista_nov_dic.html"), f"{LV}/la-revista", "lv")
        self.assertEqual((issue["key"], issue["image"]), ("2026-11", LV_HERO))
        letter = next(c for c in cards if c["url"] == LETTER_NOV)
        self.assertEqual((letter["title"], letter["department"], letter.get("image")), ("Bienvenida", True, None))

    def test_which_page_is_the_editors_letter(self):
        for slug in ("letter-editor-november-2026", "letter-editor", "letter-from-the-editor", "carta-de-bienvenida",
                     "carta-de-bienvenida-julioagosto-2026"):
            self.assertTrue(AR._is_editor_letter({"slug": slug}), slug)
        for title in ("Letter from the Editor", "Carta de Bienvenida", "Bienvenida"):
            self.assertTrue(AR._is_editor_letter({"slug": "x", "title": title}), title)
        for slug in ("cartas-del-lector", "dear-grapevine-october-2026", "wits-end", "humor-noviembrediciembre-2026",
                     "tema-de-discusion", "bienvenido-a-casa"):
            self.assertFalse(AR._is_editor_letter({"slug": slug, "title": title_case(slug)}), slug)

    # ---- the run
    def test_the_new_issues_cover_the_day_it_goes_up(self):
        http = self.serve(page("lv_carta_bienvenida.html"))
        env = self.run_lv()
        iss = env["issues"]["lv:2026-11"]
        thumb = "/assets/cache/articles/" + common.short_hash("lv:2026-11:carta-de-bienvenida", 16) + ".webp"
        self.assertEqual(iss["cover"], thumb)
        self.assertEqual(iss["image"], LV_HERO)                         # the banner stays the issue's `image` only
        self.assertNotIn("cover_tries", iss)
        self.assertEqual(AR.thumb_size(thumb), (480, 687))              # a ≤ 480 px portrait copy …
        self.assertTrue((self.tmp / "thumbs" / (thumb.rsplit("/", 1)[-1][:-5] + ".jpg")).is_file())   # … + the e-mail's JPEG
        # read first and alone (the caps are 0): the hub, the letter, its picture — never the banner, no other story
        self.assertEqual(http.asked, [f"{LV}/la-revista", LETTER_NOV, LV_COVER])
        letter = next(i for i in env["items"] if i["id"] == "lv:2026-11:carta-de-bienvenida")
        self.assertEqual((letter["extra"]["section"], letter["extra"]["department"], letter["image"]),
                         ("En cada edición", True, thumb))
        self.assertEqual(env["stats"]["covers"], 1)
        # the next run asks nothing more for it
        before = len(http.asked)
        self.run_lv()
        self.assertEqual(http.asked[before:], [f"{LV}/la-revista"])

    def test_only_a_hero_banner_is_no_cover(self):
        # the letter is up but shows no picture yet: no cover — not the hub's banner either
        bare = re.sub(r'<img [^>]*LV%20cover[^>]*>', "", page("lv_carta_bienvenida.html"))
        http = self.serve(bare)
        env = self.run_lv()
        iss = env["issues"]["lv:2026-11"]
        self.assertNotIn("cover", iss)
        self.assertEqual(iss["cover_tries"], 1)
        self.assertNotIn(LV_HERO, http.asked)
        # asked again only the next day …
        before = len(http.asked)
        self.run_lv()
        self.assertNotIn(LETTER_NOV, http.asked[before:])
        raw = json.loads((self.tmp / "articles.json").read_text(encoding="utf-8"))
        raw["issues"]["lv:2026-11"]["cover_checked"] = "2026-01-01T00:00:00Z"
        (self.tmp / "articles.json").write_text(json.dumps(raw), encoding="utf-8")
        http.pages[LETTER_NOV] = page("lv_carta_bienvenida.html")       # … when the cover is there
        env = self.run_lv()
        self.assertTrue(env["issues"]["lv:2026-11"]["cover"].endswith(".webp"))
        self.assertNotIn("cover_tries", env["issues"]["lv:2026-11"])

    def test_a_letter_without_a_cover_is_asked_a_few_times_only(self):
        bare = re.sub(r'<img [^>]*LV%20cover[^>]*>', "", page("lv_carta_bienvenida.html"))
        http = self.serve(bare)
        for _ in range(AR.COVER_TRIES + 2):
            self.run_lv()
            raw = json.loads((self.tmp / "articles.json").read_text(encoding="utf-8"))
            raw["issues"]["lv:2026-11"]["cover_checked"] = "2026-01-01T00:00:00Z"     # a day later, every time
            (self.tmp / "articles.json").write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(http.asked.count(LETTER_NOV), AR.COVER_TRIES)

    def test_a_banner_on_the_letter_page_is_no_cover(self):
        # the page declares its picture landscape (the hero banner): never the cover. (The letter, which the hub
        # shows without a picture, still gets it as its own small card picture, like any story — not as the cover.)
        banner = page("lv_carta_bienvenida.html").replace(
            'src="/sites/default/files/2026-10/LV%20cover_Nov-Dec26.jpg" width="2000" height="2863"',
            'src="/sites/default/files/styles/issue_feature_image/public/2026-10/Hero-LV-NovDic-2026.jpg?itok=q9bzErPy" '
            'width="600" height="400"')
        self.serve(banner)
        env = self.run_lv()
        self.assertNotIn("cover", env["issues"]["lv:2026-11"])
        # the same with no size declared: the downloaded picture decides
        undeclared = banner.replace('width="600" height="400"', "")
        shutil.rmtree(self.tmp / "thumbs", True)
        (self.tmp / "articles.json").unlink()
        self.serve(undeclared)
        self.assertNotIn("cover", self.run_lv()["issues"]["lv:2026-11"])

    def a_day_later(self):
        raw = json.loads((self.tmp / "articles.json").read_text(encoding="utf-8"))
        raw["issues"]["lv:2026-11"]["cover_checked"] = "2026-01-01T00:00:00Z"
        (self.tmp / "articles.json").write_text(json.dumps(raw), encoding="utf-8")

    def banner_letter(self, declared: bool = True) -> str:
        banner = page("lv_carta_bienvenida.html").replace(
            'src="/sites/default/files/2026-10/LV%20cover_Nov-Dec26.jpg" width="2000" height="2863"',
            'src="/sites/default/files/styles/issue_feature_image/public/2026-10/Hero-LV-NovDic-2026.jpg?itok=q9bzErPy" '
            'width="600" height="400"')
        return banner if declared else banner.replace('width="600" height="400"', "")

    def test_a_banner_first_then_the_cover_the_next_day(self):
        # the letter first shows the hero banner: it becomes the letter's card picture, stored under the cover's file
        # name. A day later the page shows the real cover: the retry downloads it afresh (never the banner back from
        # the cache), and the cover takes the banner's place.
        thumb = "/assets/cache/articles/" + common.short_hash("lv:2026-11:carta-de-bienvenida", 16) + ".webp"
        for declared in (True, False):
            with self.subTest(declared=declared):
                shutil.rmtree(self.tmp / "thumbs", True)
                (self.tmp / "articles.json").unlink(missing_ok=True)
                http = self.serve(self.banner_letter(declared))
                env = self.run_lv()
                self.assertNotIn("cover", env["issues"]["lv:2026-11"])
                letter = next(i for i in env["items"] if i["id"] == "lv:2026-11:carta-de-bienvenida")
                self.assertEqual(letter["image"], thumb)
                self.assertEqual(AR.thumb_size(thumb), (480, 320))
                self.assertEqual(http.asked.count(LV_HERO), 1)                # downloaded once, not again for the cover
                self.a_day_later()
                http.pages[LETTER_NOV] = page("lv_carta_bienvenida.html")
                before = len(http.asked)
                env = self.run_lv()
                self.assertEqual(http.asked[before:], [f"{LV}/la-revista", LETTER_NOV, LV_COVER])
                iss = env["issues"]["lv:2026-11"]
                self.assertEqual(iss["cover"], thumb)
                self.assertEqual(AR.thumb_size(thumb), (480, 687))
                self.assertNotIn("cover_tries", iss)
                self.assertNotIn("cover_checked", iss)
                letter = next(i for i in env["items"] if i["id"] == "lv:2026-11:carta-de-bienvenida")
                self.assertEqual(letter["image"], thumb)                  # the letter's card shows the cover too
                names = sorted(p.name for p in (self.tmp / "thumbs").iterdir())
                self.assertEqual(names, [thumb.rsplit("/", 1)[-1][:-5] + ".jpg", thumb.rsplit("/", 1)[-1]])

    def test_a_failed_retry_keeps_the_letters_picture(self):
        http = ImageHttp({}, {LV_COVER: jpeg(2000, 2863), LV_HERO: jpeg(600, 400)})
        rec = {"id": "lv:2026-11:carta-de-bienvenida"}
        key = common.short_hash(rec["id"], 16)
        rec["image"] = AR.local_thumb(http, LV_HERO, key)[0]               # its earlier (banner) card picture
        (self.tmp / "thumbs" / f"{key}-new.webp").write_bytes(b"left over")  # an interrupted run's leftover
        before = len(http.asked)
        # the picture is not there (404), or it is the banner again: no cover, and the card picture stays
        self.assertIsNone(AR.cover_from_letter(http, rec, {"image": f"{LV}/sites/default/files/missing.jpg"}))
        self.assertIsNone(AR.cover_from_letter(http, rec, {"image": LV_HERO}))
        self.assertEqual(len(http.asked) - before, 2)                      # each asked afresh, not from the cache
        self.assertEqual(AR.thumb_size(rec["image"]), (480, 320))
        self.assertEqual(sorted(p.name for p in (self.tmp / "thumbs").iterdir()), [f"{key}.webp"])
        # the real cover: it takes the banner's place, under the same name
        self.assertEqual(AR.cover_from_letter(http, rec, {"image": LV_COVER, "image_size": [2000, 2863]}),
                         rec["image"])
        self.assertEqual(AR.thumb_size(rec["image"]), (480, 687))
        self.assertEqual(sorted(p.name for p in (self.tmp / "thumbs").iterdir()), [f"{key}.webp"])
        # a stale landscape file under the cover's name that is not the letter's picture: replaced the same way
        rec2 = {"id": "gv:2026-11:letter-editor-november-2026", "image": f"{GV}/card.jpg"}
        key2 = common.short_hash(rec2["id"], 16)
        AR.local_thumb(http, LV_HERO, key2)
        self.assertIsNone(AR.cover_from_letter(http, rec2, {"image": LV_HERO}))
        self.assertFalse((self.tmp / "thumbs" / f"{key2}.webp").exists())  # nobody shows it: deleted

    def test_cover_from_letter(self):
        http = ImageHttp({}, {GV_COVER: jpeg(2000, 2857), LV_HERO: jpeg(600, 400)})
        gv = AR.parse_article(page("gv_letter_editor.html"), f"{GV}/magazine/2026/nov/letter-editor-november-2026")
        card = f"{GV}/sites/default/files/styles/card_image/public/2026-10/letter.jpg"
        # the hub gave the letter a card picture (hot-linked): the cover is still made from the page's picture
        rec = {"id": "gv:2026-11:letter-editor-november-2026", "image": card}
        self.assertEqual(AR.cover_from_letter(http, rec, gv),
                         "/assets/cache/articles/" + common.short_hash(rec["id"], 16) + ".webp")
        self.assertEqual(rec["image"], card)                          # the letter keeps its own picture
        # a landscape picture with no declared size: downloaded, found landscape, and not kept
        rec2 = {"id": "lv:2026-11:carta-de-bienvenida", "image": card}
        self.assertIsNone(AR.cover_from_letter(http, rec2, {"image": LV_HERO}))
        self.assertEqual(sorted(p.name for p in (self.tmp / "thumbs").iterdir()),
                         [common.short_hash(rec["id"], 16) + ".webp"])
        self.assertIsNone(AR.cover_from_letter(http, rec2, {}))       # no picture at all

    def test_a_cartoon_is_not_the_cover(self):
        # Grapevine's November 2026 "At Wit's End" picture is portrait too (480 × 594): only the letter's is the cover
        http = ImageHttp({}, {"https://x.test/cartoon.jpg": jpeg(480, 594), GV_COVER: jpeg(2000, 2857)})
        cartoon = AR.local_thumb(http, "https://x.test/cartoon.jpg", "cartoon")[0]
        cover = AR.local_thumb(http, GV_COVER, "letter")[0]
        issues = {"gv:2026-11": {"key": "2026-11"}}
        recs = {"a": {"id": "a", "publication": "gv", "issue_key": "2026-11", "slug": "wits-end", "department": True,
                      "image": cartoon}}
        self.assertEqual(AR.adopt_covers(recs, issues), 0)
        recs["b"] = {"id": "b", "publication": "gv", "issue_key": "2026-11", "slug": "letter-editor-november-2026",
                     "department": True, "image": cover}
        self.assertEqual((AR.adopt_covers(recs, issues), issues["gv:2026-11"]["cover"]), (1, cover))

    def test_a_cover_found_without_a_retry_drops_the_bookkeeping(self):
        # the letter's own thumbnail became portrait (an ordinary story-page read, after the cover tries ran out):
        # adopt_covers takes it, and cover_tries / cover_checked go, as when the retry finds it (DATA_SCHEMA)
        http = ImageHttp({}, {GV_COVER: jpeg(2000, 2857)})
        cover = AR.local_thumb(http, GV_COVER, "letter")[0]
        issues = {"gv:2026-11": {"key": "2026-11", "cover_tries": AR.COVER_TRIES, "cover_checked": "2026-10-16T05:00:00Z"}}
        recs = {"b": {"id": "b", "publication": "gv", "issue_key": "2026-11", "slug": "letter-editor-november-2026",
                      "department": True, "image": cover}}
        self.assertEqual(AR.adopt_covers(recs, issues), 1)
        self.assertEqual(issues["gv:2026-11"], {"key": "2026-11", "cover": cover})


def title_case(slug: str) -> str:
    return slug.replace("-", " ").title()


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
