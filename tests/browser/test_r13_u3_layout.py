"""Round 13 · u3, in a real browser (tests/browser/__init__.py says how to run these; the site server, the browser and
the helpers are test_site_in_browser.py's): four layouts that left a box alone beside blank space, or two columns of
very unequal length (the site-wide audit of October 2026).

  * DigestColumns  — /digest/'s newsletter, from 1280px: its two newspaper columns (community.css .cm-dg-body) end
                     within one unbreakable piece of each other — the tallest row (an issue with its highlights) or a
                     section's title with its first row — never a whole section (English and Spanish, 1280 / 1440 /
                     1920px, 115 % text, "Both languages"; whole sections left the left column 417–780px short);
                     no heading ever ends the left column with its first row in the right one — also where the
                     browser honours no break-after / break-before inside columns, as Firefox (Safari: no
                     "avoid"; emulated here): community.js digestColumns' empty unbreakable box before each
                     heading (.cm-dg-keep) keeps it with its first row — and one before a list's last row keeps
                     the line under the list ("+ 3 more — See all 8") with it —, and in Chromium those boxes move
                     nothing;
                     the pointer rows span the card under the columns; one column (in DOM order) below 1280px
                     and on paper, where the boxes take no room.
  * InstallGuides  — /offline/#steps: the 7 install guides in 2 (1024px) or 3 (1536px) columns, at 115 and 130 % text
                     too: no card alone on the last row with blank beside it (the 7th, "A computer", open on a
                     computer, takes the row), and in that wide card the steps go side by side, 1.5rem apart, no
                     line longer than about 90 characters; one column on a phone.
  * FeaturedWriters — /published/: Area 65's featured cards are 2 per row on wide screens and never 3 (1536 and
                     1920px: 3 + 1 left the 4th alone beside 1180px of nothing), 1 column on a phone; an odd
                     number shown — after "Show all 5 from our Area", or a magazine, period or place chosen — the
                     last one takes the whole row, never alone beside half a row (published.js data-pw-wide).
  * FourCards      — grid-cards-4 with exactly 4 cards (Next steps on /gvr/, /orientation/ and /read/, the Tracker's
                     privacy cards): 4 in a row, 2 × 2 or one column — never 3 + 1 — at every width from a phone to
                     1920px and at 115 / 130 / 150 % text (where the cards grow and 4 fit only on a wider screen);
                     a 3-card grid keeps its 3 columns, and a grid's own [--cards-max:N] still sets the row.
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

# ------------------------------------------------------------------------------------------------ the digest
# Where the two columns end (the bottom of the last content in each — the pointer rows that span the card under them
# left out), the tallest piece a column cannot end inside (a row, or a section's title down to its first row, when
# they are in one column), the headings whose first row is in the other column, and the pointer rows' spans.
# (Safari lists a stray box above the columns among an element's boxes once something spans the card under them:
# only boxes inside the newsletter's body count. Only the content counts — headings, lines, rows: Firefox and Safari
# stretch a section's piece to the foot of its column — and never community.js's empty boxes, .cm-dg-keep.)
DIGEST = r"""() => {
  const body = document.querySelector('.cm-dg-body');
  const cs = getComputedStyle(body);
  if (cs.display !== 'block' || cs.columnCount === 'auto') return { columns: 1, display: cs.display };
  const box = body.getBoundingClientRect(), mid = box.left + box.width / 2;
  const rects = (el) => [...el.getClientRects()].filter((r) => r.height > 0 && r.top >= box.top - 1 && r.bottom <= box.bottom + 1);
  const col = (r) => (r.left < mid ? 0 : 1);
  const ends = [null, null];
  for (const part of body.children) {
    if (part.classList.contains('cm-dg-intro') || getComputedStyle(part).columnSpan === 'all') continue;
    for (const el of part.querySelectorAll('h3, h4, p, li:not(.cm-dg-keep)')) for (const r of rects(el)) {
      if (r.width < 1) continue;
      const c = col(r); ends[c] = Math.max(ends[c] === null ? -1e9 : ends[c], r.bottom);
    }
  }
  const firstRow = (h) => { for (let n = h.nextElementSibling; n; n = n.nextElementSibling) {
    if (n.classList.contains('cm-dg-keep')) continue;
    if (n.tagName === 'UL' || n.tagName === 'OL') return n.querySelector('li:not(.cm-dg-keep)');
    if (!['H3', 'H4', 'P'].includes(n.tagName)) return n; } return null; };
  let piece = 0;
  for (const li of body.querySelectorAll('.cm-digest-group li.cm-avoid-break')) {
    const r = rects(li); if (r.length) piece = Math.max(piece, r[r.length - 1].bottom - r[0].top); }
  const alone = [];
  for (const h of body.querySelectorAll('.cm-digest-group > h3, .cm-digest-group > h4')) {
    const row = firstRow(h), a = rects(h), b = row ? rects(row) : [];
    if (!a.length || !b.length) continue;
    if (col(a[a.length - 1]) !== col(b[0])) alone.push(h.textContent.replace(/\s+/g, ' ').trim().slice(0, 40));
    else if (h.tagName === 'H3') piece = Math.max(piece, b[b.length - 1].bottom - a[0].top);
  }
  // the line under a list ("+ 3 more — See all 8", "See all writers…") never starts a column without its list
  for (const p of body.querySelectorAll('.cm-digest-group > :is(ul, ol) + p')) {
    const rows = p.previousElementSibling.querySelectorAll(':scope > li:not(.cm-dg-keep)'), a = rows.length ? rects(rows[rows.length - 1]) : [], b = rects(p);
    if (a.length && b.length && col(a[a.length - 1]) !== col(b[0])) alone.push('under a list: ' + p.textContent.replace(/\s+/g, ' ').trim().slice(0, 30));
  }
  const spans = [...body.querySelectorAll(':scope > .cm-dg-line')].map((l) => getComputedStyle(l).columnSpan);
  return { columns: 2, ends, gap: ends[0] === null || ends[1] === null ? null : Math.abs(ends[0] - ends[1]), piece, alone, spans,
           rem: parseFloat(getComputedStyle(document.documentElement).fontSize) };
}"""
# Firefox: no break-after / break-before inside CSS columns at all, neither "avoid" nor a forced column break (Safari:
# no "avoid") — only break-inside: avoid, which keeps community.js's boxes whole
NO_AVOID = ".cm-dg-body * { break-after: auto !important; break-before: auto !important; }"
# Where each heading and row is (to the pixel), and the empty boxes' heights
PLACES = r"""() => ({
  places: [...document.querySelectorAll('.cm-dg-body :is(h3, h4, li:not(.cm-dg-keep), .cm-digest-group > p)')].map((e) => {
    const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }),
  boxes: [...document.querySelectorAll('.cm-dg-keep')].map((k) => k.getBoundingClientRect().height),
  heads: document.querySelectorAll('.cm-digest-group > :is(h3, h4)').length,
  tails: document.querySelectorAll('.cm-digest-group > :is(ul, ol) + p').length,
  kinds: [document.querySelectorAll('div.cm-dg-keep').length, document.querySelectorAll('li.cm-dg-keep').length],
  bodies: document.querySelectorAll('.cm-dg-body').length,
  bodyStyle: document.querySelector('.cm-dg-body').getAttribute('style') })"""
NO_BOXES = ".cm-dg-keep { display: none !important; }"


def digest(width: int, lang: str, text: int | None = None, bi: bool = False, avoid: bool = True, css: str = ""):
    ctx = new_context(width, 900, lang=lang, prefs={"text": text} if text else None)
    init = ""
    if bi:
        init += "try { localStorage.setItem('gv-digest-bi', '1'); } catch (e) {}"
    css = (css + " " + ("" if avoid else NO_AVOID)).strip()
    if css:
        init += ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); "
                 f"s.textContent = {css!r}; document.head.append(s); }});")
    if init:
        ctx.add_init_script(init)
    page = open_page(ctx, ("es/" if lang == "es" else "") + "digest/")
    page.wait_for_timeout(250)        # community.js digestColumns measures in the frame after a layout
    return ctx, page


class DigestColumns(unittest.TestCase):
    def test_the_columns_end_close(self):
        cases = [(w, lang, None, False) for w in (1280, 1440, 1920) for lang in ("en", "es")] + \
                [(1440, "en", 115, False), (1440, "es", 115, False), (1440, "en", None, True), (1920, "es", None, True)]
        for width, lang, text, bi in cases:
            with self.subTest(width=width, lang=lang, text=text, bi=bi):
                ctx, page = digest(width, lang, text, bi)
                try:
                    r = page.evaluate(DIGEST)
                    self.assertEqual(r["columns"], 2, r)
                    if r["gap"] is None:
                        continue                    # a quiet month: nothing in the columns (the day's data)
                    # within one piece (+ the 2.25rem between two sections) — never a whole section short
                    self.assertLessEqual(r["gap"], r["piece"] + 2.5 * r["rem"], r)
                    self.assertEqual(r["alone"], [], r)
                    self.assertTrue(all(s == "all" for s in r["spans"]), r)
                    s = page.evaluate(SIDEWAYS)
                    self.assertFalse(s["moved"] > 0 or s["scrollWidth"] > s["width"], s)
                finally:
                    ctx.close()

    def test_no_heading_ends_a_column(self):
        for avoid in (True, False):
            for lang in ("en", "es"):
                for width in (1280, 1366, 1536, 1680, 1920):
                    with self.subTest(avoid=avoid, lang=lang, width=width):
                        ctx, page = digest(width, lang, avoid=avoid)
                        try:
                            r = page.evaluate(DIGEST)
                            self.assertEqual(r["columns"], 2, r)
                            self.assertEqual(r["alone"], [], r)
                            if not avoid and r["gap"] is not None:
                                self.assertLessEqual(r["gap"], r["piece"] + 2.5 * r["rem"], r)
                        finally:
                            ctx.close()

    def test_boxes_measured_again_after_a_resize(self):
        # the window narrows (one column: the boxes take no room) and widens again: measured for each width
        ctx, page = digest(1920, "en", avoid=False)
        try:
            for width in (1280, 1279, 1600, 1920):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(250)
                b = page.evaluate(PLACES)
                self.assertEqual(b["kinds"], [b["heads"], b["tails"]], b)    # one before each heading, one in each list with a line under it
                # measured on a copy, gone at once; the body itself never touched (switched to one column and
                # back, Safari put the intro and the pointer rows, which span the card, in the wrong places)
                self.assertEqual((b["bodies"], b["bodyStyle"]), (1, None), b)
                if width < 1280:
                    self.assertEqual(set(b["boxes"]), {0}, (width, b))
                    continue
                self.assertTrue(all(h > 0 for h in b["boxes"]), (width, b))
                r = page.evaluate(DIGEST)
                self.assertEqual(r["alone"], [], (width, r))
        finally:
            ctx.close()

    def test_the_boxes_move_nothing(self):
        # Chromium keeps a heading with its first row by itself: there, with or without the boxes, every heading and
        # row is in the same place to the pixel (the boxes take no room and carry the headings' top margins)
        for width, lang in ((1280, "en"), (1440, "es"), (1920, "en"), (1536, "es")):
            with self.subTest(width=width, lang=lang):
                places = []
                for css in ("", NO_BOXES):
                    ctx, page = digest(width, lang, css=css)
                    try:
                        places.append(page.evaluate(PLACES)["places"])
                    finally:
                        ctx.close()
                self.assertTrue(places[0])
                self.assertEqual(places[0], places[1])

    def test_one_column_below_1280_and_on_paper(self):
        for width, lang in ((390, "en"), (1024, "es"), (1279, "en")):
            with self.subTest(width=width, lang=lang):
                ctx, page = digest(width, lang)
                try:
                    r = page.evaluate(DIGEST)
                    self.assertEqual(r["columns"], 1, r)
                    self.assertEqual(set(page.evaluate(PLACES)["boxes"]), {0})     # the boxes take no room
                    s = page.evaluate(SIDEWAYS)
                    self.assertFalse(s["moved"] > 0 or s["scrollWidth"] > s["width"], s)
                finally:
                    ctx.close()
        ctx, page = digest(1440, "en")
        try:
            page.emulate_media(media="print")
            self.assertEqual(page.evaluate(DIGEST)["columns"], 1)
            self.assertEqual(set(page.evaluate(PLACES)["boxes"]), {0})
        finally:
            ctx.close()


# --------------------------------------------------------------------------------------------- card grids
# The rows of a grid's shown children: how many cards in each and the blank at the end of the row (px), and the
# number of columns.
ROWS = r"""(sel) => [...document.querySelectorAll(sel)].map((g) => {
  const kids = [...g.children].filter((k) => k.getClientRects().length && getComputedStyle(k).display !== 'none');
  const gr = g.getBoundingClientRect(), rows = [];
  for (const k of kids) {
    const r = k.getBoundingClientRect();
    let row = rows.find((x) => Math.abs(x.top - r.top) < 2);
    if (!row) rows.push(row = { top: r.top, n: 0, right: 0 });
    row.n++; row.right = Math.max(row.right, r.right);
  }
  return { columns: getComputedStyle(g).gridTemplateColumns.split(' ').filter(Boolean).length, n: kids.length,
           rows: rows.map((r) => r.n), blank: rows.map((r) => Math.round(gr.right - r.right)) };
})"""


class InstallGuides(unittest.TestCase):
    STEPS = r"""() => { const last = [...document.querySelectorAll('.pwa-guide > details')].pop();
      const steps = [...last.querySelectorAll('.pwa-guide-steps > li')].filter((s) => s.getClientRects().length);
      const tops = new Set(steps.map((s) => Math.round(s.getBoundingClientRect().top)));
      const ems = steps.map((s) => { const p = s.querySelector('p'); return p.getBoundingClientRect().width / parseFloat(getComputedStyle(p).fontSize); });
      const gap = parseFloat(getComputedStyle(last.querySelector('.pwa-guide-steps')).columnGap) / parseFloat(getComputedStyle(document.documentElement).fontSize);
      return { open: last.open, steps: steps.length, rows: tops.size, widest: Math.max(...ems), gap }; }"""

    def test_no_card_alone_on_the_last_row(self):
        cases = [(w, lang, None) for w in (1024, 1280, 1440, 1536, 1920) for lang in ("en", "es")] + \
                [(1440, "en", 115), (1440, "es", 130), (1920, "en", 130), (1920, "es", 115)]
        for width, lang, text in cases:
            with self.subTest(width=width, lang=lang, text=text):
                ctx = new_context(width, 900, lang=lang, prefs={"text": text} if text else None)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "offline/")
                    (g,) = page.evaluate(ROWS, ".pwa-guide")
                    self.assertGreaterEqual(g["columns"], 2, g)
                    for n, blank in zip(g["rows"], g["blank"]):
                        self.assertFalse(n == 1 and blank > 2, g)   # a card alone with blank beside it
                    s = page.evaluate(self.STEPS)
                    if s["open"] and g["rows"][-1] == 1 and s["steps"] > 1:
                        self.assertLess(s["rows"], s["steps"], s)      # the wide card's steps side by side …
                        self.assertAlmostEqual(s["gap"], 1.5, 2, s)    # … 1.5rem apart (the base rule's 1rem gap came after)
                    self.assertLessEqual(s["widest"], 45, s)           # ≈ 90 characters a line at most
                    r = page.evaluate(SIDEWAYS)
                    self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                finally:
                    ctx.close()

    def test_one_column_on_a_phone(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(390, 844, lang=lang)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "offline/")
                    (g,) = page.evaluate(ROWS, ".pwa-guide")
                    self.assertEqual(g["columns"], 1, g)
                    self.assertTrue(all(n == 1 for n in g["rows"]), g)
                    r = page.evaluate(SIDEWAYS)
                    self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                finally:
                    ctx.close()


class FeaturedWriters(unittest.TestCase):
    SEL = '.pw-group[data-group="neta65"] .pw-grid'

    def test_two_per_row(self):
        checked = 0
        for width in (1536, 1920, 1280):
            for lang in ("en", "es"):
                with self.subTest(width=width, lang=lang):
                    ctx = new_context(width, 900, lang=lang)
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + "published/")
                        grids = page.evaluate(ROWS, self.SEL)
                        if not grids or grids[0]["n"] < 2:
                            continue            # fewer than 2 Area 65 stories in the day's data
                        (g,) = grids
                        checked += 1
                        self.assertEqual(g["columns"], 2, g)
                        self.assertTrue(all(n <= 2 for n in g["rows"]), g)
                        self.assertEqual(g["rows"][0], 2, g)
                    finally:
                        ctx.close()
        if not checked:
            self.skipTest("fewer than 2 Area 65 stories in this build")

    def test_one_column_on_a_phone(self):
        ctx = new_context(390, 844, lang="es")
        try:
            page = open_page(ctx, "es/published/")
            for g in page.evaluate(ROWS, self.SEL):
                self.assertEqual(g["columns"], 1, g)
        finally:
            ctx.close()

    # The cards shown and which of them is marked wide (published.js data-pw-wide), and the wide card's picture beside
    # the other cards' pictures.
    WIDE = r"""(sel) => { const g = document.querySelector(sel); if (!g) return null;
      const shown = [...g.children].filter((k) => !k.hidden && getComputedStyle(k).display !== 'none');
      const w = (k) => Math.round(k.querySelector('.pw-media').getBoundingClientRect().width);
      return { n: shown.length, wide: shown.map((k) => k.hasAttribute('data-pw-wide')),
               marked: g.querySelectorAll('[data-pw-wide]').length, media: shown.map(w) }; }"""

    def test_an_odd_last_card_takes_the_row(self):
        # Every view a visitor can reach from the first one — "Show all 5 from our Area", a magazine, the longer
        # period, all of Texas — at 1024 / 1536 / 1920px: never one card alone beside blank space in a row of two
        # (2 + 2 + 1 after "Show all": the 5th alone beside 486–903px); an odd number → the last card takes the row,
        # its picture as wide as the others'.
        odd = 0
        for width in (1024, 1536, 1920):
            for lang in ("en", "es"):
                ctx = new_context(width, 900, lang=lang)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "published/")
                    views = [("first view", None)]
                    if page.locator('[data-pw-showall="neta65"]').is_visible():
                        views.append(("Show all", '[data-pw-showall="neta65"]'))
                    views += [("Grapevine", 'input[name="pub"][value="gv"]'), ("La Viña", 'input[name="pub"][value="lv"]'),
                              ("all magazines", 'input[name="pub"][value="all"]'), ("longer period", 'input[name="days"]:not(:checked)'),
                              ("all of Texas", 'input[name="scope"][value="texas"]')]
                    for view, sel in views:
                        if sel:
                            el = page.locator(sel).first
                            if not el.count() or el.is_disabled():
                                continue
                            if el.get_attribute("type") == "radio":         # (visually hidden in its chip: as a click on it does)
                                el.evaluate("(e) => { e.checked = true; e.dispatchEvent(new Event('change', { bubbles: true })); }")
                            else:
                                el.click()
                            page.wait_for_timeout(100)
                        with self.subTest(width=width, lang=lang, view=view):
                            grids = page.evaluate(ROWS, self.SEL)
                            w = page.evaluate(self.WIDE, self.SEL)
                            if not grids or not w or w["n"] < 2:
                                continue                      # the group hidden, or a single card (it fills the row)
                            (g,) = grids
                            odd += w["n"] % 2
                            self.assertEqual(g["columns"], 2, g)
                            for n, blank in zip(g["rows"], g["blank"]):
                                self.assertFalse(n == 1 and blank > 2, (g, w))      # a card alone with blank beside it
                            self.assertEqual(w["wide"], [False] * (w["n"] - 1) + [w["n"] % 2 == 1], w)
                            self.assertEqual(w["marked"], w["n"] % 2, w)   # the cards hidden now are not marked
                            if w["n"] % 2:
                                self.assertLessEqual(abs(w["media"][-1] - w["media"][0]), 2, w)
                finally:
                    ctx.close()
        if not odd:
            self.skipTest("no view with an odd number of Area 65 stories in this build")

    def test_first_view_marked_by_the_page_itself(self):
        # before published.js runs (and without it), the template marks the first view's last card when it is odd
        ctx = new_context(1536, 900, lang="en")
        try:
            ctx.route("**/published.js", lambda route: route.abort())
            page = open_page(ctx, "published/")
            w = page.evaluate(self.WIDE, self.SEL)
            if not w:
                self.skipTest("no Area 65 story in this build")
            self.assertEqual(w["wide"], [False] * (w["n"] - 1) + [w["n"] % 2 == 1], w)
        finally:
            ctx.close()


class FourCards(unittest.TestCase):
    PAGES = (("gvr/", "#next"), ("orientation/", "#next"), ("read/", "section[aria-labelledby=more-title]"),
             ("tracker/", "#privacy"))
    OK = ([4], [2, 2], [1, 1, 1, 1])

    def grids(self, page, sec: str) -> list:
        gs = [g for g in page.evaluate(ROWS, sec + " .grid-cards-4") if g["n"] == 4]
        self.assertTrue(gs, f"{sec}: no grid of 4 cards")
        return gs

    def test_never_three_and_one(self):
        cases = [(w, None) for w in (390, 700, 1024, 1180, 1280, 1920)] + [(1440, 115), (1440, 130), (1680, 150)]
        for path, sec in self.PAGES:
            for lang in ("en", "es"):
                ctx = new_context(1280, 900, lang=lang)
                ctx_text = {}
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + path)
                    for width, text in cases:
                        with self.subTest(page=path, lang=lang, width=width, text=text):
                            if text:
                                if text not in ctx_text:
                                    c = new_context(width, 900, lang=lang, prefs={"text": text})
                                    ctx_text[text] = (c, open_page(c, ("es/" if lang == "es" else "") + path))
                                p = ctx_text[text][1]
                            else:
                                p = page
                            p.set_viewport_size({"width": width, "height": 900})
                            for g in self.grids(p, sec):
                                self.assertIn(g["rows"], self.OK, g)
                                if width >= 1280 and not text:
                                    self.assertEqual(g["rows"], [4], g)       # all 4 in a row from 1280px
                            r = p.evaluate(SIDEWAYS)
                            self.assertFalse(r["moved"] > 0 or r["scrollWidth"] > r["width"], r)
                finally:
                    for c, _p in ctx_text.values():
                        c.close()
                    ctx.close()

    def test_every_width_and_text_size(self):
        # one page, the window from a phone to a wide screen, at each text size: never 3 + 1, not even for a pixel
        for text in (None, 115, 130, 150):
            with self.subTest(text=text):
                ctx = new_context(1280, 900, prefs={"text": text} if text else None)
                try:
                    page = open_page(ctx, "gvr/")
                    seen = set()
                    for width in range(600, 2001, 12):
                        page.set_viewport_size({"width": width, "height": 900})
                        (g,) = self.grids(page, "#next")
                        self.assertIn(g["rows"], self.OK, (width, g))
                        seen.add(len(g["rows"]))
                    self.assertIn(2, seen)               # 2 × 2 on the way …
                    self.assertIn(1, seen)               # … to all 4 in one row
                finally:
                    ctx.close()

    def test_three_cards_and_the_grids_own_count(self):
        ctx = new_context(1024, 900)
        try:
            page = open_page(ctx, "offline/")
            for g in page.evaluate(ROWS, "section[aria-labelledby=pwa-how-h] .grid-cards-4"):
                self.assertEqual(g["rows"], [3], g)      # 3 cards: unchanged, one row of 3 at 1024px
            page = open_page(ctx, "gvr/")
            page.set_viewport_size({"width": 1280, "height": 900})
            page.evaluate("document.querySelector('#next .grid-cards-4').style.setProperty('--cards-max', '3')")
            (g,) = self.grids(page, "#next")
            self.assertEqual(g["rows"], [3, 1], g)       # a grid's own [--cards-max:3] still wins
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
