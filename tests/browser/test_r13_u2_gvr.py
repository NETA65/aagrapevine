"""Round 13, the GVR / RLV corner's layout, in a real browser (tests/browser/__init__.py says how to run these; the site
server, the browser and the helpers are test_site_in_browser.py's):

  * StartCards          — #position: "Start with GVR / RLV 101" and the Tracker share one row (side by side, the same
                          top and height, each half of their list) at 1280, 1440 and 1920px and at 1440px with 115 %
                          text (side by side from about 1220px at 100 %), so the left column ends close to the six
                          duty cards beside it — within 80 px, English and Spanish (stacked, it ran up to 236 px
                          longer); one under the other at 1024px, on a phone and at 150 % text.
  * VideosBesideQuestion — #ideas: the About page's two videos (the page language's magazine first) sit beside "Did you
                          know?" at 1280, 1440 and 1920px (from about 1180px) — one row, the same top and height, each
                          about half of it, the two videos side by side —, the question in the middle of its card (no
                          wide blank band under it), and still one height once answered; with no question card (no
                          JavaScript, or no question for the day) they take the whole row instead of leaving half of
                          it blank; at 1100px and narrower they come under it, nothing scrolls sideways; a single
                          video takes the whole list; neither card is printed; Play turns a preview into YouTube's
                          privacy-enhanced player (youtube-nocookie.com) in place, with no script error.
"""
from __future__ import annotations

import re
import unittest

from browser.test_site_in_browser import (S, SIDEWAYS, new_context, open_page, setUpModule,  # noqa: F401
                                          tearDownModule, url)

# The two link cards of #position, and where each column of the section ends (its last child's bottom: the grid
# stretches both columns to one height, their contents don't)
POSITION = """() => {
  const box = (el) => { const r = el.getBoundingClientRect(); return { top: r.top + scrollY, bottom: r.bottom + scrollY, left: r.left, right: r.right, width: r.width, height: r.height }; };
  const card = (end) => document.querySelector(`#position a[href$="${end}"]`).closest(".card");
  const ends = [...document.querySelector("#position > div").children].map((col) => {
    const kids = [...col.children].filter((k) => k.getBoundingClientRect().height > 0);
    return Math.max(...kids.map((k) => k.getBoundingClientRect().bottom)) + scrollY;
  });
  const list = card("/orientation/").parentElement;
  return { o101: box(card("/orientation/")), tracker: box(card("/tracker/")), list: box(list), ends };
}"""

# "Did you know?", the videos' card and their row (#ideas); the cards' own heights and their tops; inside the question
# card, the spare height above its question block (less the column's gap: the block's mt-4) and below it
IDEAS = """() => {
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
    return { top: r.top + scrollY, bottom: r.bottom + scrollY, left: r.left, right: r.right, width: r.width, height: r.height,
             shown: r.width > 0 && r.height > 0 }; };
  const vids = document.querySelector("#ideas .read-vid-c-card");
  if (!vids) return { vids: null };
  const dyk = document.querySelector("#ideas .read-dyk");
  let spare = null;
  const head = dyk && dyk.querySelector(":scope > .flex"), block = dyk && dyk.querySelector(":scope > .mt-4");
  if (head && block && block.getBoundingClientRect().height > 0) {
    const cs = getComputedStyle(dyk), d = dyk.getBoundingClientRect(), b = block.getBoundingClientRect();
    spare = { above: b.top - head.getBoundingClientRect().bottom - (parseFloat(cs.rowGap) || 0),
              below: d.bottom - parseFloat(cs.paddingBottom) - parseFloat(cs.borderBottomWidth) - b.bottom };
  }
  return { row: box(vids.parentElement), dyk: box(dyk), vids: box(vids), spare,
           list: box(vids.querySelector(".read-vid-c-list")),
           tiles: [...vids.querySelectorAll(".read-vid-c")].map(box),
           langs: [...vids.querySelectorAll(".read-vid-c .badge-muted")].map((b) => b.textContent.trim()) };
}"""


def gvr(lang: str) -> str:
    return ("es/" if lang == "es" else "") + "gvr/"


class StartCards(unittest.TestCase):
    def test_one_row_from_1280(self):
        for lang in ("en", "es"):
            for width, prefs in ((1280, None), (1440, None), (1920, None), (1440, {"text": 115})):
                with self.subTest(lang=lang, width=width, prefs=prefs):
                    ctx = new_context(width, 900, lang=lang, prefs=prefs)
                    try:
                        page = open_page(ctx, gvr(lang))
                        r = page.evaluate(POSITION)
                        a, b = r["o101"], r["tracker"]
                        self.assertAlmostEqual(a["top"], b["top"], delta=1, msg="the two cards start on one row")
                        self.assertAlmostEqual(a["height"], b["height"], delta=1, msg="…and end on it")
                        self.assertGreater(b["left"], a["right"], "the Tracker beside GVR / RLV 101")
                        self.assertAlmostEqual(a["width"], b["width"], delta=1)
                        self.assertGreater(a["width"], r["list"]["width"] * 0.45)
                        left, right = r["ends"]
                        self.assertLessEqual(abs(left - right), 80, f"the left column ends {left - right:+.0f} px from the duty cards")
                    finally:
                        ctx.close()

    def test_one_under_the_other_in_a_narrow_column(self):
        for lang, width, prefs in (("en", 1024, None), ("es", 1024, None), ("en", 390, None), ("es", 1440, {"text": 150})):
            with self.subTest(lang=lang, width=width, prefs=prefs):
                ctx = new_context(width, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, gvr(lang))
                    r = page.evaluate(POSITION)
                    self.assertGreaterEqual(r["tracker"]["top"], r["o101"]["bottom"], "stacked")
                    self.assertAlmostEqual(r["o101"]["width"], r["list"]["width"], delta=1, msg="each the whole column")
                finally:
                    ctx.close()


class VideosBesideQuestion(unittest.TestCase):
    def ideas(self, ctx, lang: str, errors: list | None = None, question: bool = True):
        page = open_page(ctx, gvr(lang), errors)
        if question:
            page.wait_for_selector("#ideas .read-dyk .read-dyk-q", state="visible", timeout=10_000)
        page.wait_for_timeout(200)
        r = page.evaluate(IDEAS)
        self.assertIsNotNone(r["vids"], "the About page's two videos in #ideas")
        return page, r

    def test_beside_the_question_from_1280(self):
        for lang in ("en", "es"):
            for width in (1280, 1440, 1920):
                with self.subTest(lang=lang, width=width):
                    ctx = new_context(width, 900, lang=lang)
                    errors: list[str] = []
                    try:
                        _, r = self.ideas(ctx, lang, errors)
                        dyk, vids, row = r["dyk"], r["vids"], r["row"]
                        self.assertTrue(dyk["shown"])
                        self.assertAlmostEqual(dyk["top"], vids["top"], delta=1, msg="one row")
                        self.assertAlmostEqual(dyk["height"], vids["height"], delta=1, msg="one height")
                        # the question in the middle of the spare height, never a wide blank band under it
                        sp = r["spare"]
                        self.assertIsNotNone(sp)
                        self.assertAlmostEqual(sp["above"], sp["below"], delta=2, msg="the question block centred")
                        self.assertLess(sp["below"], dyk["height"] * 0.25, "no wide blank band under the question")
                        self.assertGreater(vids["left"], dyk["right"], "the videos on the right")
                        for half in (dyk, vids):
                            self.assertGreater(half["width"], row["width"] * 0.45)
                            self.assertLess(half["width"], row["width"] * 0.55)
                        t1, t2 = r["tiles"]
                        self.assertAlmostEqual(t1["top"], t2["top"], delta=1, msg="the two videos side by side")
                        # the page language's magazine first, each video's language said
                        self.assertEqual(r["langs"], ["En español", "En inglés"] if lang == "es" else ["In English", "In Spanish"])
                    finally:
                        ctx.close()
                    self.assertEqual(errors, [])

    def test_under_the_question_when_narrow(self):
        for lang, width in (("en", 1100), ("en", 1024), ("es", 768), ("es", 390), ("en", 390)):
            with self.subTest(lang=lang, width=width):
                ctx = new_context(width, 900, lang=lang)
                try:
                    page, r = self.ideas(ctx, lang)
                    self.assertGreaterEqual(r["vids"]["top"], r["dyk"]["bottom"])
                    self.assertAlmostEqual(r["vids"]["width"], r["row"]["width"], delta=1)
                    self.assertAlmostEqual(r["dyk"]["width"], r["row"]["width"], delta=1)
                    if width == 390:
                        t1, t2 = r["tiles"]
                        self.assertGreaterEqual(t2["top"], t1["bottom"], "one video per row on a phone")
                    s = page.evaluate(SIDEWAYS)
                    self.assertFalse(s["moved"] > 0 or s["scrollWidth"] > s["width"], s["wide"])
                finally:
                    ctx.close()

    def test_the_whole_row_without_a_question_card(self):
        # no JavaScript: no question card (data-js-only) — the videos fill the row
        for width in (1440, 1024):
            with self.subTest(js=False, width=width):
                ctx = S["browser"].new_context(viewport={"width": width, "height": 900}, java_script_enabled=False)
                try:
                    _, r = self.ideas(ctx, "en", question=False)
                    self.assertFalse(r["dyk"]["shown"])
                    self.assertAlmostEqual(r["vids"]["width"], r["row"]["width"], delta=1, msg="no blank half")
                    self.assertAlmostEqual(r["vids"]["left"], r["row"]["left"], delta=1)
                    t1, t2 = r["tiles"]
                    self.assertAlmostEqual(t1["top"], t2["top"], delta=1)
                finally:
                    ctx.close()
        # JavaScript, but no question for the day (the card's list empty: x-show hides it)
        ctx = new_context(1440, 900)
        errors: list[str] = []
        try:
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))

            def no_questions(route):
                body = route.fetch().text()
                body, n = re.subn(r"(<script type=\"application/json\" data-dyk(?:=\"\")?>).*?(</script>)", r"\1{}\2", body, flags=re.S)
                self.assertEqual(n, 1)
                route.fulfill(body=body, headers={"content-type": "text/html; charset=utf-8"})
            page.route(url("gvr/"), no_questions)
            page.goto(url("gvr/"), wait_until="load", timeout=60_000)
            page.wait_for_timeout(500)
            r = page.evaluate(IDEAS)
            self.assertIsNotNone(r["vids"], "the About page's two videos in #ideas")
            self.assertFalse(r["dyk"]["shown"])
            self.assertAlmostEqual(r["vids"]["width"], r["row"]["width"], delta=1, msg="no blank half")
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_still_one_height_once_answered(self):
        ctx = new_context(1440, 900)
        errors: list[str] = []
        try:
            page, before = self.ideas(ctx, "en", errors)
            page.locator("#ideas .read-dyk .read-dyk-opt").first.click()
            page.wait_for_selector("#ideas .read-dyk .read-dyk-fb", state="visible", timeout=5000)
            page.wait_for_timeout(200)
            r = page.evaluate(IDEAS)
            self.assertGreater(r["dyk"]["height"], before["dyk"]["height"] - 1)
            self.assertAlmostEqual(r["dyk"]["top"], r["vids"]["top"], delta=1, msg="one row")
            self.assertAlmostEqual(r["dyk"]["height"], r["vids"]["height"], delta=1, msg="one height")
            self.assertAlmostEqual(r["spare"]["above"], r["spare"]["below"], delta=2)
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_not_printed(self):
        # neither card on paper (print:hidden — the row's screen-only layout never brings the question card back)
        ctx = new_context(1440, 900)
        try:
            page, _ = self.ideas(ctx, "en")
            page.emulate_media(media="print")
            page.wait_for_timeout(100)
            r = page.evaluate(IDEAS)
            self.assertFalse(r["dyk"]["shown"], "the question card is not printed")
            self.assertFalse(r["vids"]["shown"], "the videos are not printed")
        finally:
            ctx.close()

    def test_one_video_takes_the_whole_list(self):
        # an about_videos entry can be dropped (no title from config or the channel): the one left is never half a
        # list with a blank half — beside the question (1440) or under it (1024)
        def one_video(route):
            body = route.fetch().text()
            body, n = re.subn(r'(<ul class="read-vid-c-list" role="list">\s*<li class="min-w-0">.*?</li>)'
                              r'<li class="min-w-0">.*?</article></li>', r"\1", body, count=1, flags=re.S)
            self.assertEqual(n, 1)
            route.fulfill(body=body, headers={"content-type": "text/html; charset=utf-8"})
        for width in (1440, 1024):
            with self.subTest(width=width):
                ctx = new_context(width, 900)
                try:
                    page = ctx.new_page()
                    page.route(url("gvr/"), one_video)
                    page.goto(url("gvr/"), wait_until="load", timeout=60_000)
                    page.wait_for_selector("#ideas .read-dyk .read-dyk-q", state="visible", timeout=10_000)
                    page.wait_for_timeout(200)
                    r = page.evaluate(IDEAS)
                    self.assertEqual(len(r["tiles"]), 1)
                    self.assertAlmostEqual(r["tiles"][0]["width"], r["list"]["width"], delta=1, msg="the whole list")
                    if width == 1440:
                        self.assertAlmostEqual(r["dyk"]["top"], r["vids"]["top"], delta=1, msg="still beside the question")
                finally:
                    ctx.close()

    def test_play(self):
        ctx = new_context(1440, 900)
        errors: list[str] = []
        try:
            page, _ = self.ideas(ctx, "en", errors)
            btn = page.locator("#ideas .read-vid-c lite-youtube .lyt-playbtn").first
            self.assertEqual(btn.get_attribute("role"), "button")
            self.assertTrue((btn.get_attribute("aria-label") or btn.inner_text()).startswith("Play: "))
            btn.click()
            page.wait_for_selector("#ideas .read-vid-c lite-youtube.lyt-activated iframe", state="attached", timeout=5000)
            src = page.get_attribute("#ideas .read-vid-c lite-youtube iframe", "src")
            self.assertTrue(src.startswith("https://www.youtube-nocookie.com/embed/"), src)
            self.assertEqual(len(ctx.pages), 1, "played in place, not in a new tab")
        finally:
            ctx.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
