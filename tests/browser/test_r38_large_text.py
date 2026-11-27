"""Round 38 · larger text on phones, in a real browser (tests/browser/__init__.py says how to run these; the site server,
the browser and the helpers are test_site_in_browser's). The Aa panel's text size (115 / 130 / 150 %) and relaxed
spacing, saved before the page loads:

  * HomeStart     — Home's "Where would you like to start?" (areas/home.css): at 130–150 % on a phone the words get the
                    button's whole width (the icon tile and the arrow step aside), no word breaks in two from 360px
                    and the page never scrolls sideways (320px too); at 100 % the icon and the arrow are there.
  * HomeSmall     — (round 38) the rest of Home on 320–414px phones, at 100 % and larger text and with relaxed spacing,
                    English and Spanish: no word breaks in two in the start buttons (below 360px their icon and arrow
                    step aside at any size), in "More on this site" (its icon tiles step aside below 384px, and below
                    480px at 115 %), in Listen & watch's "Weekly open meetings" link or in the Book of the Month card (its
                    arrow steps aside below 400px at 115 %: "descuento"); the next Grapevine meeting's date, wrapped,
                    keeps its first letter. (At 150 % with relaxed spacing on a 320px phone the start
                    buttons' "representante" is wider than the button itself: hyphenated there, not checked.)
  * CommitteeDates — the committee meeting's dates page at larger text and relaxed spacing on phones: a guest
                    speaker's line has a line of its own (never beside "Google Meet"), no word breaks in two; and at
                    150 % on 640–800px tablets (the flyer tile steps aside below 768px; "View flyer" stays).
  * FooterHub     — the footer's link groups at 115–150 % and relaxed spacing, 480–1440px, English and Spanish: no word
                    breaks in two (the official sites' web addresses may); the Stay updated column's first link loses
                    its icon only at 115 % with relaxed spacing on 640–719px.
  * DrawerGroups  — the phone menu's folding groups (header.njk): at 150 % on a 320px phone each label keeps whole
                    words ("Get involved", "Committee", "Participa") — their icons step aside below 360px.
  * NextDeadlines — Share your story's "Next story deadlines" card: at 150 % on a 320px phone its title and its
                    "Add to my calendar" keep whole words (skipped when no deadline is open).
  * LibraryPill   — a Library card's main button ("Open" / "Preview") at 130 % on a 390px phone, in the phone's list
                    view: still the wide pill, not a round icon (access.css .lib-btn.lib-btn-main, a cascade tie lost
                    when the Library got its own stylesheet).

    GV_BROWSER_SITE=_site python -m unittest browser.test_r38_large_text -v     (from the tests folder)
"""
from __future__ import annotations

import unittest

from browser.test_site_in_browser import SIDEWAYS, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

# Every word (a run without spaces) inside the elements `sel` matches that the browser drew on more than one line —
# a word broken in two. (A break after a dash, "July–" / "August", is a line break between two words, not counted.)
SPLIT_WORDS = r"""(sel) => {
  const out = [], rg = document.createRange();
  for (const root of document.querySelectorAll(sel)) {
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest('.sr-only') || !el.getClientRects().length) continue;
      for (const m of n.textContent.matchAll(/[^\s–—-]+/g)) {
        rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
        const tops = new Set([...rg.getClientRects()].filter((r) => r.width > 0.5).map((r) => Math.round(r.top)));
        if (tops.size > 1) out.push(m[0]);
      }
    }
  }
  return out;
}"""


def sideways(page) -> str:
    r = page.evaluate(SIDEWAYS)
    return f"scrolls {r['moved']} px sideways ({r['scrollWidth']} in {r['width']}): {r['wide']}" if r["moved"] > 0 or r["scrollWidth"] > r["width"] else ""


class HomeStart(unittest.TestCase):
    def test_the_words_get_the_whole_button(self):
        problems = []
        for lang in ("en", "es"):
            for width in (320, 360, 390):
                for prefs in ({"text": 130}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                    ctx = new_context(width, 800, lang=lang, prefs=prefs)
                    try:
                        page = open_page(ctx, "es/" if lang == "es" else "")
                        if not page.locator(".home-choose-btn").count():
                            self.fail("no start buttons on Home")
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs}"
                        hidden = page.evaluate("""() => [...document.querySelectorAll('.home-choose-icon, .home-choose-go')]
                            .every((e) => getComputedStyle(e).display === 'none')""")
                        if not hidden:
                            problems.append(f"{where}: the icon or the arrow still beside the words")
                        # the words' column fills the button (its padding aside)
                        narrow = page.evaluate("""() => [...document.querySelectorAll('.home-choose-btn')].filter((b) => {
                            const s = getComputedStyle(b), inner = b.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
                            return b.querySelector('.home-choose-body').getBoundingClientRect().width < inner - 1; }).length""")
                        if narrow:
                            problems.append(f"{where}: {narrow} button(s) with a narrower text column")
                        if width >= 360:
                            split = page.evaluate(SPLIT_WORDS, ".home-choose")
                            if split:
                                problems.append(f"{where}: words broken in two: {split}")
                        if s := sideways(page):
                            problems.append(f"{where}: {s}")
                        page.close()
                    finally:
                        ctx.close()
        self.assertEqual(problems, [])

    def test_at_100_percent_the_icons_stay(self):
        ctx = new_context(390, 800)
        try:
            page = open_page(ctx, "")
            shown = page.evaluate("""() => [...document.querySelectorAll('.home-choose-icon, .home-choose-go')]
                .map((e) => getComputedStyle(e).display)""")
            self.assertEqual(len(shown), 8)
            self.assertNotIn("none", shown)
        finally:
            ctx.close()


# the next Grapevine meeting's date on Home: a line of its words that starts left of its paragraph's visible edge (the
# row is pulled 0.75rem left inside the clipped paragraph, to cut the leading dot off — a wrapped line was cut too)
GVM_CUT = """() => { let cut = 0;
  for (const p of document.querySelectorAll('.home-gvm-when')) {
    const d = p.querySelector('.home-gvm-date');
    if (!d || !d.getClientRects().length) continue;
    const left = p.getBoundingClientRect().left;
    for (const n of d.childNodes) {
      if (n.nodeType !== 3) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 0.5 && r.left < left - 0.5) cut++;
    }
  }
  return cut; }"""


class HomeSmall(unittest.TestCase):
    def test_whole_words_on_small_phones(self):
        problems = []
        for lang in ("en", "es"):
            for width in (320, 360, 390, 414):
                for prefs in (None, {"spacing": "relaxed"}, {"text": 115}, {"text": 115, "spacing": "relaxed"}, {"text": 150},
                              {"text": 150, "spacing": "relaxed"}):
                    ctx = new_context(width, 800, lang=lang, prefs=prefs)
                    try:
                        page = open_page(ctx, "es/" if lang == "es" else "")
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs or '100 %'}"
                        sel = ".home-more, .home-wo-link, .home-mag-more .shop-teaser"
                        if not (width < 360 and prefs == {"text": 150, "spacing": "relaxed"}):
                            sel += ", .home-choose"
                        split = page.evaluate(SPLIT_WORDS, sel)
                        if split:
                            problems.append(f"{where}: words broken in two: {split}")
                        if cut := page.evaluate(GVM_CUT):
                            problems.append(f"{where}: the Grapevine meeting's date: {cut} line(s) start inside the cut-off strip")
                        if s := sideways(page):
                            problems.append(f"{where}: {s}")
                        page.close()
                    finally:
                        ctx.close()
        self.assertEqual(problems, [])

    def test_the_icon_tiles_stay_where_there_is_room(self):
        ctx = new_context(414, 800)
        try:
            page = open_page(ctx, "")
            shown = page.evaluate("""() => [...document.querySelectorAll('.home-more-icon, .home-wo-icon, .home-wo-go')]
                .map((e) => getComputedStyle(e).display)""")
            self.assertGreaterEqual(len(shown), 7)
            self.assertNotIn("none", shown)
        finally:
            ctx.close()


class CommitteeDates(unittest.TestCase):
    def test_the_speaker_line_keeps_its_own_line(self):
        problems = []
        for lang in ("en", "es"):
            for width in (320, 360, 414):
                for prefs in ({"spacing": "relaxed"}, {"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                    ctx = new_context(width, 800, lang=lang, prefs=prefs)
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + "events/series/committee-meeting/")
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs}"
                        lines = page.evaluate("""() => [...document.querySelectorAll('#evp-all-dates li[id] ul > li.basis-full')].map((li) =>
                            li.getBoundingClientRect().width >= li.parentElement.getBoundingClientRect().width - 1)""")
                        if lines.count(False):
                            problems.append(f"{where}: {lines.count(False)} of {len(lines)} speaker lines beside something")
                        split = page.evaluate(SPLIT_WORDS, "#evp-all-dates ul")
                        if split:
                            problems.append(f"{where}: words broken in two: {sorted(set(split))}")
                        if s := sideways(page):
                            problems.append(f"{where}: {s}")
                        page.close()
                    finally:
                        ctx.close()
        self.assertEqual(problems, [])

    def test_whole_words_at_150_percent_on_tablets(self):
        """(round 38) at 150 % on 640–767px the cards leave out the flyer tile (committee.css, the end): beside the date
        tile and the flyer the words had 174–280px and broke in two ("representatives", "hispanohablantes",
        "Wednesday,"); each card's "View flyer" button is still there"""
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "events/series/committee-meeting/")
                    for width in (640, 656, 664, 680, 696, 712, 728, 744, 767, 768, 800):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs}"
                        split = page.evaluate(SPLIT_WORDS, "#evp-all-dates")
                        if split:
                            problems.append(f"{where}: words broken in two: {sorted(set(split))}")
                        r = page.evaluate("""() => { const cards = [...document.querySelectorAll('#evp-all-dates .cm-event')]
                            .filter((c) => c.querySelector('.cm-flyer-thumb'));
                            return { cards: cards.length, buttons: cards.filter((c) => {
                              const b = c.querySelector('a[data-cm-preview]'); return b && b.getClientRects().length; }).length }; }""")
                        if r["buttons"] != r["cards"]:
                            problems.append(f"{where}: {r['cards'] - r['buttons']} of {r['cards']} cards with a flyer have no "
                                            f"View flyer button")
                        if s := sideways(page):
                            problems.append(f"{where}: {s}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


class FooterHub(unittest.TestCase):
    def test_whole_words_in_the_link_groups(self):
        """(round 38) the footer's link groups (Explore, Get involved, Committee, Stay updated — not the official sites'
        web addresses, which may break anywhere) keep whole words at larger text and relaxed spacing on tablets and
        laptops: at 115 % with relaxed spacing on 640–719px, where the four groups share a row, the Stay updated
        column's first link loses its icon ("mantenert|e" in "Todas las formas de mantenerte al día")"""
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"spacing": "relaxed"}, {"text": 115}, {"text": 115, "spacing": "relaxed"}, {"text": 130},
                          {"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, "es/" if lang == "es" else "")
                    for width in (480, 640, 656, 672, 688, 704, 720, 768, 1024, 1088, 1280, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
                        split = page.evaluate(SPLIT_WORDS, "footer .site-footer-groups :is(h2, a:not([target=_blank]))")
                        if split:
                            problems.append(f"/{'es/' if lang == 'es' else ''} {width}px {prefs}: words broken in two: "
                                            f"{sorted(set(split))}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_its_icon_stays_where_there_is_room(self):
        for prefs, width in (({"text": 115, "spacing": "relaxed"}, 720), ({"text": 115}, 640), (None, 640)):
            with self.subTest(prefs=prefs, width=width):
                ctx = new_context(width, 900, lang="es", prefs=prefs)
                try:
                    page = open_page(ctx, "es/")
                    shown = page.evaluate("() => getComputedStyle(document.querySelector('footer .site-footer-hub > .icon')).display")
                    self.assertNotEqual(shown, "none")
                    page.close()
                finally:
                    ctx.close()


class DrawerGroups(unittest.TestCase):
    def test_whole_words_at_150_percent_on_a_small_phone(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 150}, {"text": 150, "spacing": "relaxed"}, {"text": 130, "spacing": "relaxed"}):
                ctx = new_context(320, 780, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "meetings/")
                    page.locator(".site-menu-btn").first.click()
                    page.wait_for_selector("#mobile-drawer .site-drawer-group", state="attached")
                    page.evaluate("() => document.querySelectorAll('#mobile-drawer details').forEach((d) => { d.open = true; })")
                    split = page.evaluate(SPLIT_WORDS, "#mobile-drawer nav summary")
                    if split:
                        problems.append(f"{lang} {prefs}: {split}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


class NextDeadlines(unittest.TestCase):
    def test_whole_words_at_150_percent_on_a_small_phone(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 780, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "contribute/")
                    if not page.locator("#next-deadlines details.ct-dl-cal").count():
                        self.skipTest("no open story deadline in this build")
                    split = page.evaluate(SPLIT_WORDS, "#nd-title, #next-deadlines .ct-dl-cal > summary")
                    if split:
                        problems.append(f"{lang} {prefs}: {split}")
                    if s := sideways(page):
                        problems.append(f"{lang} {prefs}: {s}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


class LibraryPill(unittest.TestCase):
    def test_the_main_button_stays_a_wide_pill(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(390, 800, lang=lang, prefs={"text": 130})
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "library/")
                    btn = page.locator(".lib-results .lib-btn-main").first
                    btn.wait_for(state="visible")
                    self.assertEqual(page.locator(".lib-results").first.get_attribute("data-view"), "list", "the phone's list view")
                    box = btn.bounding_box()
                    self.assertGreater(box["width"], 1.6 * box["height"], f"a pill, not a round icon: {box}")
                    page.close()
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
