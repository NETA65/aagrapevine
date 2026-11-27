"""Round 38 · Home after the owner's "tighten spacing" and the compact video, in a real browser (tests/browser/__init__.py
says how to run these; the site server, the browser and the helpers are test_site_in_browser's):

  * StartButtons — "Where would you like to start?" (areas/home.css 1d). Four in a row (English and Spanish, 1280 and
                   1440px) the buttons share one row and one height and none has more than 3.5rem of empty room under
                   its words: the wordiest, "I want to write my story", has the wider column (when the four were as
                   wide, three of them had 65-86px of nothing). At 130-150 % text from 1280px they are one under the
                   other with the icon beside the words, as on a tablet — no button gets a row more. The arrow sits at
                   the end of the label's first line and never covers a word.
  * WholeWords   — (round 38) at 115 % text, relaxed spacing and both, on tablets and laptops (640-1440px), English
                   and Spanish: no word breaks in two in the start buttons, the Book of the Month card and "More on
                   this site" — where four in a row (or two) left a word wider than its column ("representante",
                   "publicaciones"), the buttons and cards take fewer columns there (areas/home.css 1d, 8). The two
                   meeting cards under the hero at 130 % with relaxed spacing and 150 % (320-1000px): whole words, and
                   nothing of the Grapevine Meeting's date or time cut off (areas/home.css 1, --page).
  * VideoStrip   — the newest video's strip under the two Listen & watch cards (areas/home.css .home-video): at
                   130-150 % from 640 to 1279px its video is never wider than its usual size (13rem; 15rem from
                   1024px) nor than 40 % of the strip, so never bigger than at 1280px; and from 640px, at every text
                   size and spacing, it keeps its 16:9 (round 38: stretched to the words' height it was taller than
                   wide at 640px and 150 %, 208 × 143px at 100 %) (skipped with no video).

    GV_BROWSER_SITE=_site python -m unittest browser.test_r38_home_layout -v     (from the tests folder)
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule  # noqa: F401
from browser.test_r38_large_text import SPLIT_WORDS

SETTLE = "() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))"

# Each start button: its box, the bottom of its lowest drawn words (or icon), its padding, and where the icon and the
# words are — what the tests below compare.
BUTTONS = r"""() => [...document.querySelectorAll('.home-choose-btn')].map((b) => {
  const r = b.getBoundingClientRect(), s = getComputedStyle(b);
  const edges = parseFloat(s.paddingTop) + parseFloat(s.paddingBottom) + parseFloat(s.borderTopWidth) + parseFloat(s.borderBottomWidth);
  const box = (sel) => { const e = b.querySelector(sel); return e && e.getClientRects().length ? e.getBoundingClientRect() : null; };
  let low = r.top;
  for (const sel of ['.home-choose-icon', '.home-choose-label', '.home-choose-text', '.home-choose-due']) {
    const x = box(sel); if (x && x.height) low = Math.max(low, x.bottom);
  }
  const icon = box('.home-choose-icon'), body = box('.home-choose-body'), text = box('.home-choose-text');
  return { left: r.left, top: r.top, height: r.height, empty: r.bottom - parseFloat(s.paddingBottom) - parseFloat(s.borderBottomWidth) - low,
           inner: r.height - edges, floor: (parseFloat(s.minHeight) || 0) - edges,
           icon: icon && { right: icon.right, height: icon.height }, body: body && body.height, textLeft: text && text.left };
})"""

# Words of a label that the arrow (where it is drawn) covers.
COVERED = r"""() => {
  const out = [];
  for (const b of document.querySelectorAll('.home-choose-btn')) {
    const go = b.querySelector('.home-choose-go');
    if (!go || !go.getClientRects().length) continue;
    const g = go.getBoundingClientRect(), label = b.querySelector('.home-choose-label');
    const walk = document.createTreeWalker(label, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const x of rg.getClientRects())
        if (x.right > g.left + 0.5 && x.left < g.right - 0.5 && x.bottom > g.top + 0.5 && x.top < g.bottom - 0.5) out.push(label.textContent.trim());
    }
  }
  return out;
}"""

# Lines of the Grapevine Meeting's date and time (under the hero) drawn past the edges of their paragraph, which clips
# them (its row is pulled 0.75rem left to cut the leading dot off): "text left/right" in px past each edge.
GVM_CLIPPED = r"""() => {
  const out = [], rg = document.createRange();
  for (const p of document.querySelectorAll('.home-under-card .home-gvm-when')) {
    if (!p.getClientRects().length) continue;
    const box = p.getBoundingClientRect(), walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      if (!n.textContent.trim()) continue;
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects())
        if (r.width > 0.5 && (r.left < box.left - 1 || r.right > box.right + 1))
          out.push(`${n.textContent.trim().slice(0, 24)} ${Math.round(box.left - r.left)}/${Math.round(r.right - box.right)}`);
    }
  }
  return out;
}"""

VIDEO = r"""() => {
  const strip = document.querySelector('.home-video'), yt = strip && strip.querySelector('lite-youtube');
  if (!yt) return null;
  return { video: yt.getBoundingClientRect().width, height: yt.getBoundingClientRect().height, strip: strip.clientWidth,
           rem: parseFloat(getComputedStyle(document.documentElement).fontSize) };
}"""


def prefix(lang: str) -> str:
    return "es/" if lang == "es" else ""


class StartButtons(unittest.TestCase):
    def test_four_in_a_row_with_little_empty_room(self):
        problems = []
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            try:
                page = open_page(ctx, prefix(lang))
                for width in (1280, 1440):
                    page.set_viewport_size({"width": width, "height": 900})
                    page.evaluate(SETTLE)
                    bs = page.evaluate(BUTTONS)
                    where = f"/{prefix(lang)} {width}px"
                    if len(bs) != 4:
                        problems.append(f"{where}: {len(bs)} buttons, not 4")
                        continue
                    if max(b["top"] for b in bs) - min(b["top"] for b in bs) > 1 or max(b["height"] for b in bs) - min(b["height"] for b in bs) > 1:
                        problems.append(f"{where}: not one row of equal buttons: {[(round(b['top']), round(b['height'])) for b in bs]}")
                    if (most := max(b["empty"] for b in bs)) > 56:
                        problems.append(f"{where}: {round(most)}px empty under a button's words: {[round(b['empty']) for b in bs]}")
                    r = page.evaluate(SIDEWAYS)
                    if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                        problems.append(f"{where}: scrolls sideways ({r['scrollWidth']} in {r['width']}): {r['wide']}")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(problems, [])

    def test_larger_text_from_1280px_one_under_the_other_icon_beside_the_words(self):
        problems = []
        for lang in ("en", "es"):
            for text in (130, 150):
                ctx = new_context(1280, 900, lang=lang, prefs={"text": text})
                try:
                    page = open_page(ctx, prefix(lang))
                    for width in (1280, 1536):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        bs = page.evaluate(BUTTONS)
                        where = f"/{prefix(lang)} {width}px {text}%"
                        if len({round(b["left"]) for b in bs}) != 1:
                            problems.append(f"{where}: not one under the other")
                        for i, b in enumerate(bs):
                            if b["icon"] and b["textLeft"] is not None and b["textLeft"] < b["icon"]["right"]:
                                problems.append(f"{where}: button {i + 1}: its words under the icon, not beside it")
                            # its height is its words' (or its icon's, or the 4.5rem least), nothing more
                            if b["inner"] > max(b["body"] or 0, b["icon"]["height"] if b["icon"] else 0, b["floor"]) + 1.5:
                                problems.append(f"{where}: button {i + 1}: {round(b['inner'])}px inside for "
                                                f"{round(b['body'] or 0)}px of words")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_the_arrow_never_covers_a_word(self):
        problems = []
        for lang in ("en", "es"):
            for text in (100, 115, 130):
                ctx = new_context(1280, 900, lang=lang, prefs={"text": text} if text != 100 else None)
                try:
                    page = open_page(ctx, prefix(lang))
                    for width in (320, 390, 768, 1024, 1280, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        if covered := page.evaluate(COVERED):
                            problems.append(f"/{prefix(lang)} {width}px {text}%: the arrow covers {covered}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


class WholeWords(unittest.TestCase):
    def test_no_word_broken_in_two_at_115_percent_and_relaxed_spacing(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"spacing": "relaxed"}, {"text": 115}, {"text": 115, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, prefix(lang))
                    for width in (640, 672, 768, 1024, 1152, 1280, 1366, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        if split := page.evaluate(SPLIT_WORDS, ".home-choose, .home-mag-more .shop-teaser, .home-more"):
                            problems.append(f"/{prefix(lang)} {width}px {prefs}: words broken in two: {sorted(set(split))}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_the_meeting_cards_under_the_hero_at_larger_text(self):
        """(round 38) the two meeting cards under the hero (below 1024px) at 130 % with relaxed spacing and at 150 %: no
        word broken in two, and no letter of the Grapevine Meeting's date or time cut off at its paragraph's edges. At
        150 % on 768–1023px each card is one column (beside the countdown and the buttons the date broke in two:
        "Wednes|day", "Miérc|oles", and ran past the card's right edge); a time that wraps inside itself starts its next
        line at the visible edge ("ST" for "CST": 320px, 150 % with relaxed spacing)."""
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, prefix(lang))
                    for width in (320, 360, 768, 800, 832, 864, 900, 1000):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        where = f"/{prefix(lang)} {width}px {prefs}"
                        if split := page.evaluate(SPLIT_WORDS, ".home-under-card"):
                            problems.append(f"{where}: words broken in two: {sorted(set(split))}")
                        if cut := page.evaluate(GVM_CLIPPED):
                            problems.append(f"{where}: cut off at the Grapevine Meeting's edges: {cut}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_at_100_percent_four_in_a_row_from_1280px(self):
        """the larger settings' fewer columns leave the 100 % row as it was (the owner's compact row)"""
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                try:
                    page = open_page(ctx, prefix(lang))
                    for width, cols in ((640, 2), (1280, 4), (1366, 4)):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        n = page.evaluate("() => getComputedStyle(document.querySelector('.home-choose-grid')).gridTemplateColumns.split(' ').length")
                        self.assertEqual(n, cols, f"{width}px")
                    page.close()
                finally:
                    ctx.close()


class VideoStrip(unittest.TestCase):
    def test_larger_text_the_video_is_never_bigger_than_at_1280px(self):
        problems = []
        for lang in ("en", "es"):
            for text in (130, 150):
                ctx = new_context(1280, 900, lang=lang, prefs={"text": text})
                try:
                    page = open_page(ctx, prefix(lang))
                    at1280 = page.evaluate(VIDEO)
                    if at1280 is None:
                        self.skipTest("no video on Home in the day's data")
                    for width in (640, 800, 1023, 1024, 1279):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        v = page.evaluate(VIDEO)
                        usual = (15 if width >= 1024 else 13) * v["rem"]
                        where = f"/{prefix(lang)} {width}px {text}%"
                        if v["video"] > min(usual, 0.4 * v["strip"]) + 1:
                            problems.append(f"{where}: the video is {round(v['video'])}px wide in a {v['strip']}px strip "
                                            f"(at most {round(min(usual, 0.4 * v['strip']))})")
                        if v["video"] > at1280["video"] + 1:
                            problems.append(f"{where}: the video ({round(v['video'])}px) is wider than at 1280px "
                                            f"({round(at1280['video'])}px)")
                        if abs(v["height"] - v["video"] * 9 / 16) > 2:
                            problems.append(f"{where}: the video is {round(v['video'])} x {round(v['height'])}px, "
                                            f"not 16:9")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_the_video_keeps_16_9_at_every_text_size(self):
        """(round 38) from 640px the video sits at the strip's top and keeps its 16:9 wherever the words beside it are
        taller (stretched to their height it was 208 × 143px at 640–1023px and 100 %, 239 × 227 in Spanish at 115 % with
        relaxed spacing, 360 × 232 at 1280px and 150 % with relaxed spacing: its picture cropped, played letterboxed)"""
        problems = []
        for lang in ("en", "es"):
            for prefs in (None, {"spacing": "relaxed"}, {"text": 115}, {"text": 115, "spacing": "relaxed"},
                          {"text": 130, "spacing": "relaxed"}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, prefix(lang))
                    if page.evaluate(VIDEO) is None:
                        self.skipTest("no video on Home in the day's data")
                    for width in (640, 768, 1023, 1024, 1279, 1280, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        v = page.evaluate(VIDEO)
                        if abs(v["height"] - v["video"] * 9 / 16) > 2:
                            problems.append(f"/{prefix(lang)} {width}px {prefs or '100 %'}: the video is "
                                            f"{round(v['video'])} x {round(v['height'])}px, not 16:9")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
