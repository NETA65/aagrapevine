"""Round 38 · Home after the owner's "tighten spacing" and the compact video, in a real browser (tests/browser/__init__.py
says how to run these; the site server, the browser and the helpers are test_site_in_browser's):

  * StartButtons — "Where would you like to start?" (areas/home.css 1d). Four in a row (English and Spanish, 1280 and
                   1440px) the buttons share one row and one height and none has more than 3.5rem of empty room under
                   its words: the wordiest, "I want to write my story", has the wider column (when the four were as
                   wide, three of them had 65-86px of nothing). At 130-150 % text from 1280px they are one under the
                   other with the icon beside the words, as on a tablet — no button gets a row more. The arrow sits at
                   the end of the label's first line and never covers a word. (round 38b) Two in a row (640-1279px, 100
                   and 115 %): two to a line, each line's two buttons one height; the write button, with its deadline,
                   the wider one on its line, and no button with more than 4.5rem of empty room under its words ("I want
                   to subscribe" had 84-107px beside it at 640-800px; at 100 % with normal spacing from 896px no
                   more than 2rem: it had 45px at 960-1200px) — never taller than two halves would be; at 130 % and
                   at 115 % with relaxed spacing below 672px one under the other.
  * WholeWords   — (round 38) at 115 % text, relaxed spacing and both, on tablets and laptops (640-1440px), English
                   and Spanish: no word breaks in two in the start buttons, the Book of the Month card and "More on
                   this site" — where four in a row (or two) left a word wider than its column ("representante",
                   "publicaciones"), the buttons and cards take fewer columns there (areas/home.css 1d, 8). The two
                   meeting cards under the hero at 130 % with relaxed spacing and 150 % (320-1000px): whole words, and
                   nothing of the Grapevine Meeting's date or time cut off (areas/home.css 1, --page). (round 38b) "Write
                   for the magazines" keeps whole words beside its links at relaxed spacing and larger text (462-479px,
                   100 % with relaxed spacing: "magazi|nes").
  * VideoStrip   — the newest video's strip under the two Listen & watch cards (areas/home.css .home-video): at
                   130-150 % from 640 to 1279px its video is never wider than its usual size (13rem; 15rem from
                   1024px) nor than 40 % of the strip, so never bigger than at 1280px; and from 640px, at every text
                   size and spacing, it keeps its 16:9 (round 38: stretched to the words' height it was taller than
                   wide at 640px and 150 %, 208 × 143px at 100 %); (round 38b) at 115 % below 360px (below 400px with
                   relaxed spacing) the words go under the video, as at 130-150 % on a phone, and each badge keeps one
                   line (beside its words the video was 95 × 53px in a strip 229px tall, "Nuevo en YouTube" on two
                   lines; with relaxed spacing up to 393px, beside a 111-124px video) (skipped with no video).

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

    def test_two_in_a_row_the_write_button_the_wider_one(self):
        """(round 38b) two in a row (640-1279px) the buttons are a flex row that wraps two to a line (areas/home.css 1d):
        the line with "I want to write my story" and its deadline gives that button about 63 % (about 70 % from 896px at
        100 % text), the other line two halves. With two grid columns "I want to subscribe" had 84-107px of nothing under
        its words at 640-800px (85-168 at 115 %); now at most 4.5rem — and (round 38b review) at 100 % text with normal
        spacing from 896px at most 2rem (it had 45px at 960-1200px beside the write button's longer words) — and the
        buttons are never taller than with two halves on each line"""
        halves = ("(on) => { let s = document.getElementById('t-halves'); if (!s) { s = document.createElement('style'); "
                  "s.id = 't-halves'; document.head.appendChild(s); } "
                  "s.textContent = on ? '.home-choose-grid > li { flex: 1 1 34% !important; }' : ''; }")
        grid_h = "() => document.querySelector('.home-choose-grid').getBoundingClientRect().height"
        problems = []
        for lang in ("en", "es"):
            for text in (100, 115):
                ctx = new_context(1280, 900, lang=lang, prefs={"text": text} if text != 100 else None)
                try:
                    page = open_page(ctx, prefix(lang))
                    due = page.locator(".home-choose-due:visible").count() > 0
                    rem = page.evaluate("() => parseFloat(getComputedStyle(document.documentElement).fontSize)")
                    for width in (640, 656, 672, 700, 720, 768, 800, 900, 960, 1000, 1023, 1060, 1100, 1150, 1200, 1279):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        where = f"/{prefix(lang)} {width}px {text}%"
                        bs = page.evaluate(BUTTONS)
                        tops = sorted({round(b["top"]) for b in bs})
                        if len(bs) != 4 or len(tops) != 2:
                            problems.append(f"{where}: not two lines of two: {[(round(b['left']), round(b['top'])) for b in bs]}")
                            continue
                        lines = [[b for b in bs if abs(b["top"] - t) <= 1] for t in tops]
                        for ln in lines:
                            if len(ln) != 2 or abs(ln[0]["height"] - ln[1]["height"]) > 1:
                                problems.append(f"{where}: a line is not two buttons of one height: {[round(b['height']) for b in ln]}")
                        widths = page.evaluate("() => [...document.querySelectorAll('.home-choose-btn')].map((b) => b.getBoundingClientRect().width)")
                        if abs(widths[0] - widths[1]) > 1:
                            problems.append(f"{where}: the first line is not two halves: {[round(w) for w in widths]}")
                        if due and widths[2] < 1.3 * widths[3]:
                            problems.append(f"{where}: the write button is not the wider one on its line: {[round(w) for w in widths]}")
                        if (most := max(b["empty"] for b in bs)) > (2 if text == 100 and width >= 896 else 4.5) * rem:
                            problems.append(f"{where}: {round(most)}px empty under a button's words: {[round(b['empty']) for b in bs]}")
                        now = page.evaluate(grid_h)
                        page.evaluate(halves, True)
                        page.evaluate(SETTLE)
                        even = page.evaluate(grid_h)
                        page.evaluate(halves, False)
                        if now > even + 1:
                            problems.append(f"{where}: {round(now)}px tall, {round(even)}px with two halves on each line")
                        if s := page.evaluate(SIDEWAYS)["moved"]:
                            problems.append(f"{where}: scrolls {s}px sideways")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_one_under_the_other_where_the_larger_text_rules_say(self):
        """(round 38b) …and where a larger-text rule puts them one under the other (a grid again, one column): 130-150 %
        at every width, 115 % with relaxed spacing on 640-671px"""
        problems = []
        for prefs, widths in (({"text": 130}, (640, 768, 1024, 1279)), ({"text": 150}, (768, 1100)),
                              ({"text": 115, "spacing": "relaxed"}, (640, 656, 671))):
            ctx = new_context(1280, 900, lang="es", prefs=prefs)
            try:
                page = open_page(ctx, "es/")
                for width in widths:
                    page.set_viewport_size({"width": width, "height": 900})
                    page.evaluate(SETTLE)
                    lefts = {round(b["left"]) for b in page.evaluate(BUTTONS)}
                    if len(lefts) != 1:
                        problems.append(f"/es/ {width}px {prefs}: not one under the other ({sorted(lefts)})")
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

    def test_the_write_line_keeps_whole_words(self):
        """(round 38b) "Write for the magazines" and its two links (index.njk .home-write-line) at relaxed spacing and
        larger text, 320-1440px: the title keeps 9em beside a link (7em was 101-116px at 462-479px with relaxed spacing:
        "magazi|nes")"""
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"spacing": "relaxed"}, {"text": 115, "spacing": "relaxed"}, {"text": 130}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, prefix(lang))
                    for width in (320, 390, 440, 456, 462, 464, 468, 472, 476, 477, 478, 479, 480, 484, 496, 520, 560, 600,
                                  640, 768, 900, 1024, 1280, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        if split := page.evaluate(SPLIT_WORDS, ".home-write-line"):
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
        """the larger settings' fewer columns leave the 100 % row as it was (the owner's compact row). (Counted as the
        buttons beside the first one: two in a row is a flex row since round 38b, with no grid columns to count.)"""
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                try:
                    page = open_page(ctx, prefix(lang))
                    for width, cols in ((640, 2), (1280, 4), (1366, 4)):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate(SETTLE)
                        bs = page.evaluate(BUTTONS)
                        n = len([b for b in bs if abs(b["top"] - bs[0]["top"]) <= 1])
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

    def test_at_115_percent_on_a_small_phone_the_words_go_under_the_video(self):
        """(round 38b) at 115 % below 360px — below 400px with relaxed spacing — the strip is the video over its words,
        as at 130-150 % on a phone, and each badge keeps one line: beside them the video was 95 × 53px in a strip 229px
        tall (Spanish, 320px) and "Nuevo en YouTube" wrapped onto two lines — with relaxed spacing up to 393px (368 in
        English), beside a 111-124px video in a strip 266px tall; from 360px (400 with relaxed spacing) they are side
        by side again"""
        place = """() => { const s = document.querySelector('.home-video'); if (!s) return null;
          const v = s.querySelector('lite-youtube').getBoundingClientRect(), i = s.querySelector('.home-video-info').getBoundingClientRect();
          const badges = [...s.querySelectorAll('.home-video-info > p:first-child > span')].filter((b) => b.getClientRects().length)
            .map((b) => { const cs = getComputedStyle(b), lh = parseFloat(cs.lineHeight) || 1.5 * parseFloat(cs.fontSize);
              return b.getBoundingClientRect().height < 1.9 * lh + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom); });
          return { under: i.top >= v.bottom - 1, beside: i.left >= v.right - 1, video: v.width, inner: s.clientWidth, badges }; }"""
        problems = []
        for lang in ("en", "es"):
            for prefs, stacked in (({"text": 115}, 360), ({"text": 115, "spacing": "relaxed"}, 400)):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, prefix(lang))
                    if page.evaluate(place) is None:
                        self.skipTest("no video on Home in the day's data")
                    for width in (320, 344, 359, 360, 375, 390, 399, 400):
                        page.set_viewport_size({"width": width, "height": 800})
                        page.evaluate(SETTLE)
                        r = page.evaluate(place)
                        where = f"/{prefix(lang)} {width}px {prefs}"
                        if width < stacked:
                            if not r["under"] or r["video"] < 0.8 * r["inner"]:
                                problems.append(f"{where}: the words are not under a full-width video ({round(r['video'])}px in {r['inner']}px)")
                            if not all(r["badges"]):
                                problems.append(f"{where}: a badge on two lines: {r['badges']}")
                        elif not r["beside"]:
                            problems.append(f"{where}: the words are not beside the video")
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
