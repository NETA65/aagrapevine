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
                    arrow steps aside below 400px at 115 %: "descuento"); (round 38b) nor in the committee meeting's
                    countdown ("HOUR|S" at 115 % on a 320px phone: its tiles have no side padding there), the episode
                    card's "Also on" buttons, the "More episodes" heading (its icon steps aside at 150 % with relaxed
                    spacing below 360px: "episodios") or the video strip; the next Grapevine meeting's date, wrapped,
                    keeps its first letter. (At 150 % with relaxed spacing on a 320px phone the start
                    buttons' "representante" is wider than the button itself: hyphenated there, not checked.) And
                    (round 38b) "Also on" (Apple Podcasts · Spotify · Amazon Music) stays one line that scrolls sideways
                    below 1024px, as designed: each button on one line at every setting, the page never sideways.
  * CommitteeDates — the committee meeting's dates page at larger text and relaxed spacing on phones: a guest
                    speaker's line has a line of its own (never beside "Google Meet"), no word breaks in two; and at
                    150 % on 640–800px tablets (the flyer tile steps aside below 768px; "View flyer" stays).
  * FooterHub     — the footer's link groups at 115–150 % and relaxed spacing, 480–1440px, English and Spanish: no word
                    breaks in two — (round 38b) the official sites' names too: "aagrapevine.org" breaks only before
                    ".org" (where "aagrapevine" has no room beside its grapes icon and arrow, they step aside) —, and
                    the page never scrolls sideways; the Stay updated column's first link loses its icon only at 115 %
                    with relaxed spacing on 640–719px, an official site's grapes only where its line is too narrow.
  * DrawerGroups  — the phone menu's folding groups (header.njk): at 150 % on a 320px phone each label keeps whole
                    words ("Get involved", "Committee", "Participa") — their icons step aside below 360px.
  * NextDeadlines — Share your story's "Next story deadlines" card: at 150 % on a 320px phone its title and its
                    "Add to my calendar" keep whole words; (round 38b) and its title with relaxed spacing on 320–414px
                    phones, at 100 % text too ("deadline|s" at 360px) (skipped when no deadline is open).
  * LibraryPill   — a Library card's main button ("Open" / "Preview") at 130 % on a 390px phone, in the phone's list
                    view: still the wide pill, not a round icon (access.css .lib-btn.lib-btn-main, a cascade tie lost
                    when the Library got its own stylesheet).
  * EventPages    — (round 38b) EVERY event's own page and series' page in the build (English and Spanish, not the
                    old links' forwarders) at 150 % with relaxed spacing on a 320px phone: no sideways scroll ("Map",
                    "Online on Google Meet" and a section title pushed them 6–76px); the quick facts keep whole words
                    at 115–150 % on 320–390px phones (a value goes under its label when it would get less than 6rem —
                    it had 12px at 150 %, one letter per line), and at 100 % they stay side by side — on pages chosen
                    from the build (a Map link, the longest quick facts, "Online on Google Meet"; the bots' data
                    decides which events there are: a kind it lacks is skipped).
  * BoothStill    — (round 38b) the About page's booth preview with relaxed spacing (100–150 %, 320–1280px): the still
                    welcome slide's lines all inside its 16:9 card (2em under a paragraph pushed the last line out).
  * RecorderNoise — (round 38b) Share your story's recorder, "Reduce background noise", at 130–150 % with relaxed
                    spacing on 320–360px phones: its words stay inside the recorder's card, whole (cut by 18px).
  * OtherPages    — (round 38b) at 150 % (with relaxed spacing too) on 320–375px phones: GVR / RLV's two tool cards
                    (and at 115–130 % — at 100 % their icon stays beside the words), "Your first steps", the Bingo
                    list, the panel titles of /status/, /gvr/ and /stay-updated/ and the feeds' buttons (their
                    .lt-fold icon steps aside), and /events/' "Organizer ↗" / "Organizador ↗" (also with relaxed
                    spacing alone on a 390px phone, two buttons to a row; skipped when no event has an organizer's
                    page): no word broken in two — but a word wider than its whole card ("documentos" on /es/status/
                    at 150 % with relaxed spacing on a 320px phone), left to hyphenation. Also /status/' three numbers
                    at 130–150 % on 640–880px tablets and its maintainer toggles on 320–390px phones (skipped when
                    no source has notes or failed), and the small event cards (Share your story's next workshops, an
                    event page's other events, a cancelled event's notice) at 115–150 % on 320–640px — no word that
                    fits its card broken in two (it had 28px at 150 % on a 320px phone, one letter per line). And
                    (round 38b review) /read/'s "Ways to subscribe" note at 130–150 % on 640–800px tablets: its button
                    goes under the words instead of 20–79px past the screen, no word broken in two; at 100 % and 115 %
                    it stays beside them.
  * DeckNotice    — a presentation's "details still blank" notice on 320–430px phones, 100–150 % text, relaxed
                    spacing on and off, English and Spanish: "Fill them in" and "Present anyway" whole and in sight,
                    also when the notice's words scroll (presentations.css: the buttons stay at its foot).

    GV_BROWSER_SITE=_site python -m unittest browser.test_r38_large_text -v     (from the tests folder)
"""
from __future__ import annotations

import re
import unittest

from browser.test_site_in_browser import S, SIDEWAYS, answered, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

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

# …only the words that would fit on one line of the box `sel` matches (its inside, the padding left out): a word wider
# than its whole box may break (hyphenated where the phone has the dictionary)
SPLIT_FITTING = r"""(sel) => {
  const out = [], rg = document.createRange();
  for (const box of document.querySelectorAll(sel)) {
    if (!box.getClientRects().length) continue;
    const bs = getComputedStyle(box), inner = box.clientWidth - parseFloat(bs.paddingLeft) - parseFloat(bs.paddingRight);
    const walk = document.createTreeWalker(box, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest('.sr-only') || !el.getClientRects().length) continue;
      for (const m of n.textContent.matchAll(/[^\s–—-]+/g)) {
        rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
        if (new Set([...rg.getClientRects()].filter((r) => r.width > 0.5).map((r) => Math.round(r.top))).size < 2) continue;
        const probe = document.createElement('span');
        probe.style.cssText = 'position:absolute;white-space:nowrap;visibility:hidden';
        probe.textContent = m[0]; el.appendChild(probe);
        const w = probe.getBoundingClientRect().width; probe.remove();
        if (w <= inner) out.push(m[0]);
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
                        sel = (".home-more, .home-wo-link, .home-mag-more .shop-teaser, .home-meet-count, .home-episode .chip-row, "
                               ".home-more-eps .card-h, .home-video")
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

    def test_also_on_scrolls_sideways_with_whole_buttons(self):
        """(round 38b) the episode card's "Also on" row (index.njk: one line that scrolls sideways below 1024px, wraps from
        there — the row of Apple Podcasts · Spotify · Amazon Music is wider than a phone's card at 100 % already): below
        1024px each button keeps its label on one line at every text size and spacing (larger text let a label wrap
        inside the row's width and break "Pod|casts", "Spo|tify", "Ama|zon"), the row scrolls and the page does not"""
        problems = []
        for lang in ("en", "es"):
            for prefs in (None, {"spacing": "relaxed"}, {"text": 115}, {"text": 130, "spacing": "relaxed"}, {"text": 150},
                          {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, "es/" if lang == "es" else "")
                    if not page.locator(".home-episode .chip-row").count():
                        self.skipTest("no podcast links on Home in this build")
                    for width in (320, 360, 390, 430, 560, 768, 1023):
                        page.set_viewport_size({"width": width, "height": 800})
                        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs or '100 %'}"
                        r = page.evaluate("""() => { const row = document.querySelector('.home-episode .chip-row'), rg = document.createRange();
                          const lines = [...row.children].map((b) => { const tops = new Set();
                            for (const n of b.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { rg.selectNodeContents(n);
                              for (const x of rg.getClientRects()) if (x.width > 0.5) tops.add(Math.round(x.top)); }
                            return [b.textContent.trim(), tops.size]; });
                          const wide = [...row.children].reduce((s, b) => s + b.getBoundingClientRect().width, 0);
                          return { lines, scrolls: row.scrollWidth > row.clientWidth + 1, wide, room: row.clientWidth }; }""")
                        if more := [b for b, n in r["lines"] if n != 1]:
                            problems.append(f"{where}: a label on more than one line: {more}")
                        if r["wide"] > r["room"] and not r["scrolls"]:
                            problems.append(f"{where}: the buttons ({round(r['wide'])}px) are wider than the row ({r['room']}px), which does not scroll")
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
        """(round 38) the footer's link groups (Explore, Get involved, Committee, Stay updated) keep whole words at larger
        text and relaxed spacing on tablets and laptops: at 115 % with relaxed spacing on 640–719px, where the four
        groups share a row, the Stay updated column's first link loses its icon ("mantenert|e" in "Todas las formas de
        mantenerte al día"). (round 38b) The official sites' names too ("aagrapevi|ne" at 640–768px with 115 % text or
        relaxed spacing): each breaks only at its <wbr> before ".org" — a text node of its own, so the check below never
        counts that break — and the page never scrolls sideways."""
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"spacing": "relaxed"}, {"text": 115}, {"text": 115, "spacing": "relaxed"}, {"text": 130},
                          {"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1280, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, "es/" if lang == "es" else "")
                    if page.locator("footer .site-footer-official").count() != 2:
                        problems.append(f"/{'es/' if lang == 'es' else ''}: not the two official sites in the footer")
                    for width in (480, 640, 656, 672, 688, 704, 720, 736, 752, 768, 1024, 1088, 1100, 1280, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs}"
                        split = page.evaluate(SPLIT_WORDS, "footer .site-footer-groups :is(h2, a)")
                        if split:
                            problems.append(f"{where}: words broken in two: {sorted(set(split))}")
                        if s := sideways(page):
                            problems.append(f"{where}: {s}")
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

    def test_the_official_sites_icons_step_aside_only_where_needed(self):
        """(round 38b) an official site's grapes icon and arrow step aside only where its line is too narrow for
        "aagrapevine" beside them (areas/access.css: a size container, in em): at 100 % and 115 % on wide screens both
        are there, and at 115 % on a 320px phone the grapes (the arrow is never shown below 360px: footer.njk); at 115 %
        on a 640px tablet the grapes go; with relaxed spacing there the arrow too"""
        icons = """() => [...document.querySelectorAll('footer .site-footer-official > a')].map((a) => [
            getComputedStyle(a.querySelector(':scope > svg:first-child')).display !== 'none',
            getComputedStyle(a.querySelector(':scope > svg:last-of-type')).display !== 'none'])"""
        for lang in ("en", "es"):
            for prefs, width, grapes, arrow in ((None, 640, True, True), (None, 1280, True, True), ({"text": 115}, 320, True, False),
                                                ({"text": 115}, 1280, True, True), ({"text": 115}, 640, False, True),
                                                ({"text": 115, "spacing": "relaxed"}, 640, False, False)):
                with self.subTest(lang=lang, prefs=prefs, width=width):
                    ctx = new_context(width, 900, lang=lang, prefs=prefs)
                    try:
                        page = open_page(ctx, "es/" if lang == "es" else "")
                        shown = page.evaluate(icons)
                        self.assertEqual(len(shown), 2)
                        # "aagrapevine.org" (the second link on /es/, where La Viña's comes first)
                        self.assertEqual(shown[1 if lang == "es" else 0], [grapes, arrow])
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

    def test_the_title_keeps_whole_words_with_relaxed_spacing(self):
        """(round 38b) relaxed spacing turns main.css's text-column rule on at 100 % text too: the title was squeezed to
        7em beside "All deadlines ↓" and broke as "deadline|s" on a 360px phone; it keeps 11em there too (access.css)"""
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"spacing": "relaxed"}, {"text": 115, "spacing": "relaxed"}, {"text": 130, "spacing": "relaxed"}):
                ctx = new_context(320, 780, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "contribute/")
                    if not page.locator("#nd-title").count():
                        self.skipTest("no open story deadline in this build")
                    for width in (320, 344, 360, 375, 390, 414):
                        page.set_viewport_size({"width": width, "height": 780})
                        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
                        if split := page.evaluate(SPLIT_WORDS, "#nd-title"):
                            problems.append(f"{lang} {width}px {prefs}: {split}")
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


def settle(page) -> None:
    """Two frames after a window resize, so the layout has caught up."""
    page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")


def event_pages() -> list[str]:
    """Every event's own page and series' page in the build, English and Spanish ("events/<…>/", "es/events/<…>/"): not
    /events/ itself, and not the forwarders of old links (a page that only refreshes to another)."""
    site, out = S["site"], []
    for f in sorted([*site.glob("events/**/index.html"), *site.glob("es/events/**/index.html")]):
        rel = f.parent.relative_to(site).as_posix() + "/"
        if rel not in ("events/", "es/events/") and 'http-equiv="refresh"' not in f.read_text(encoding="utf-8"):
            out.append(rel)
    return out


def fact_pages() -> dict[str, str]:
    """The kinds of quick facts the round-38 measurements named, each on a page chosen from the build — the bots' data
    decides which event pages there are (a "Map" link is there only while its event is still to come, the build keeps
    12 past events, a renamed event changes its address): {kind: English path}. "map": the first event with a Map link
    (a street address: the Fort Worth workshop of December 12, 2026 when this was written); "longest": the page whose
    quick facts have the most text (a CityWide booth date in Dallas, then); "online": the Grapevine Meeting's series
    page ("Online on Google Meet"), or else the first page with an "Online on …" line. A kind the build lacks is left
    out (its check is skipped)."""
    site, out, longest = S["site"], {}, (0, "")
    for path in event_pages():
        if path.startswith("es/"):
            continue
        m = re.search(r'<dl class="evp-facts">(.*?)</dl>', (site / path / "index.html").read_text(encoding="utf-8"), re.S)
        if not m:
            continue
        if 'class="evp-map"' in m.group(1):
            out.setdefault("map", path)
        if 'class="evp-fact-line"' in m.group(1):
            out.setdefault("online", path)
        if (n := len(" ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split()))) > longest[0]:
            longest = (n, path)
    gvm = site / "events/series/grapevine-meeting/index.html"
    if gvm.is_file() and 'class="evp-fact-line"' in gvm.read_text(encoding="utf-8"):
        out["online"] = "events/series/grapevine-meeting/"
    if longest[1]:
        out["longest"] = longest[1]
    return out


def chosen_fact_pages(test: unittest.TestCase) -> list[str]:
    """fact_pages()' pages, each once; a kind the build lacks is a skipped subtest, and no page at all skips the test"""
    pages = fact_pages()
    for kind in ("map", "longest", "online"):
        if kind not in pages:
            with test.subTest(kind=kind):
                test.skipTest(f"no event page with this kind of quick facts ({kind}) in this build")
    if not pages:
        test.skipTest("no event page with quick facts in this build")
    return list(dict.fromkeys(pages.values()))


# the quick facts: how many, how many have their value beside the label, how many of those values are narrower than
# 6rem; the words broken in two in the values (an e-mail address may break anywhere)
FACTS = r"""() => { const rem = parseFloat(getComputedStyle(document.documentElement).fontSize), rg = document.createRange(), split = [];
  const rows = [...document.querySelectorAll('.evp-facts > div')].map((d) => { const dt = d.querySelector('dt').getBoundingClientRect(),
    dd = d.querySelector('dd').getBoundingClientRect(); return { beside: Math.abs(dt.top - dd.top) < 2, narrow: dd.width < 6 * rem - 1 }; });
  for (const dd of document.querySelectorAll('.evp-facts dd')) {
    const walk = document.createTreeWalker(dd, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest('.sr-only, a[href^="mailto:"]') || !el.getClientRects().length) continue;
      for (const m of n.textContent.matchAll(/[^\s–—-]+/g)) {
        rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
        if (new Set([...rg.getClientRects()].filter((r) => r.width > 0.5).map((r) => Math.round(r.top))).size > 1) split.push(m[0]);
      }
    }
  }
  return { n: rows.length, beside: rows.filter((r) => r.beside).length, narrow: rows.filter((r) => r.beside && r.narrow).length, split }; }"""


class EventPages(unittest.TestCase):
    def test_no_event_page_scrolls_sideways(self):
        """(round 38b) at 150 % with relaxed spacing on a 320px phone — where the quick facts' "Map" link, the series'
        "Online on Google Meet" and a section's title beside its icon reached 6–76px past the screen"""
        pages = event_pages()
        self.assertGreater(len(pages), 20, "the event pages of the build")
        problems = []
        for lang in ("en", "es"):
            ctx = new_context(320, 800, lang=lang, prefs={"text": 150, "spacing": "relaxed"})
            try:
                page = ctx.new_page()
                for path in pages:
                    if path.startswith("es/") != (lang == "es"):
                        continue
                    answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
                    page.evaluate("async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; }")
                    if s := sideways(page):
                        problems.append(f"/{path}: {s}")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(problems, [])

    def test_the_quick_facts_keep_their_words(self):
        """(round 38b) on the pages fact_pages() chooses (a Map link, the longest quick facts, "Online on Google Meet")"""
        fact_paths = chosen_fact_pages(self)
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 115}, {"text": 130}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    for path in fact_paths:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + path)
                        for width in (320, 360, 390):
                            page.set_viewport_size({"width": width, "height": 800})
                            settle(page)
                            where = f"/{'es/' if lang == 'es' else ''}{path} {width}px {prefs}"
                            r = page.evaluate(FACTS)
                            if not r["n"]:
                                problems.append(f"{where}: no quick facts")
                            if r["narrow"]:
                                problems.append(f"{where}: {r['narrow']} value(s) narrower than 6rem beside their label")
                            if r["split"]:
                                problems.append(f"{where}: words broken in two: {sorted(set(r['split']))[:8]}")
                            if s := sideways(page):
                                problems.append(f"{where}: {s}")
                        page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_at_100_percent_the_facts_stay_side_by_side(self):
        fact_paths = chosen_fact_pages(self)
        for width in (320, 414, 768):
            with self.subTest(width=width):
                ctx = new_context(width, 800)
                try:
                    for path in fact_paths:
                        page = open_page(ctx, path)
                        r = page.evaluate(FACTS)
                        self.assertGreater(r["n"], 0, f"/{path}: its quick facts")
                        self.assertEqual(r["beside"], r["n"], f"/{path}: every label beside its value")
                        page.close()
                finally:
                    ctx.close()


# the booth preview's still slide: its text lines that reach outside the slide (it clips them, inside the 16:9 card)
BOOTH_CUT = r"""() => { const f = document.querySelector('[data-gvb-pv-frame]'), s = f && f.querySelector('[data-gvb-still]');
  if (!s || !s.getClientRects().length) return null;
  const box = s.querySelector('.gvb-slide').getBoundingClientRect(), rg = document.createRange(), out = [];
  const walk = document.createTreeWalker(s.querySelector('.gvb-stage'), NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    if (!n.textContent.trim()) continue;
    rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) if (r.width > 0.5 && (r.bottom > box.bottom + 0.5 || r.top < box.top - 0.5 || r.right > box.right + 0.5 || r.left < box.left - 0.5)) {
      out.push(n.textContent.trim().slice(0, 40) + ' (' + Math.round(r.bottom - box.bottom) + 'px)'); break; }
  }
  return out; }"""


class BoothStill(unittest.TestCase):
    def test_the_welcome_slide_fits_its_card_with_relaxed_spacing(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"spacing": "relaxed"}, {"text": 130, "spacing": "relaxed"}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "about/")
                    for width in (320, 390, 768, 1280):
                        page.set_viewport_size({"width": width, "height": 800})
                        settle(page)
                        cut = page.evaluate(BOOTH_CUT)
                        if cut is None:
                            problems.append(f"/{lang} about {width}px {prefs}: no still welcome slide in the preview")
                        elif cut:
                            problems.append(f"/{lang} about {width}px {prefs}: lines outside the card: {cut}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


# the recorder's "Reduce background noise": how far its words reach past the deck's inner edge (px), its words broken
# in two
NOISE = r"""() => { const l = document.querySelector('#recorder .cm-switch').closest('label'), deck = l.closest('.cm-rec-deck');
  const cs = getComputedStyle(deck), d = deck.getBoundingClientRect(), right = d.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
  const rg = document.createRange(), split = []; let past = 0;
  const walk = document.createTreeWalker(l, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    rg.selectNodeContents(n); for (const r of rg.getClientRects()) if (r.width > 0.5) past = Math.max(past, r.right - right);
    for (const m of n.textContent.matchAll(/\S+/g)) { rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
      if (new Set([...rg.getClientRects()].filter((r) => r.width > 0.5).map((r) => Math.round(r.top))).size > 1) split.push(m[0]); }
  }
  return { past: Math.round(past), split, text: l.textContent.trim() }; }"""


class RecorderNoise(unittest.TestCase):
    def test_its_words_stay_in_the_card(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "contribute/")
                    page.wait_for_selector("#recorder .cm-switch", state="attached")
                    for width in (320, 340, 360):
                        page.set_viewport_size({"width": width, "height": 800})
                        settle(page)
                        r = page.evaluate(NOISE)
                        where = f"/{'es/' if lang == 'es' else ''}contribute/ {width}px {prefs}"
                        if not r["text"]:
                            problems.append(f"{where}: no noise option")
                        if r["past"] > 1:
                            problems.append(f"{where}: '{r['text']}' {r['past']}px past the recorder's inner edge")
                        if r["split"]:
                            problems.append(f"{where}: words broken in two: {r['split']}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


# GVR / RLV's two tool cards (GVR / RLV 101, the Tracker), an event card's "Organizer ↗" (the button with a phone's
# short label), then the other places the round-38b rules keep whole
GVR_TOOLS = "li.card.card-link.group:has(> div.min-w-0 a[href*='/orientation/'], > div.min-w-0 a[href*='/tracker/'])"
ORGANIZER = '.cm-ev-btns > a:has(> [class~="sm:hidden"])'
OTHER = (
    ("gvr/", GVR_TOOLS + ", .read-check-body, #bingo ul.grid > li, .sticky-aside .card-h"),
    ("status/", ".cm-st-side .card-h"),
    ("stay-updated/", "#feeds .card-h, #feeds a.btn-sm"),
    ("events/", ORGANIZER),
)
# a word wider than its whole card is left to hyphenation (where the phone has the dictionary): "documentos" of
# "Biblioteca de documentos" at 150 % with relaxed spacing on a 320px phone (212px in the card's 210px)
WIDER_THAN_ITS_CARD = {("es/status/", 320, True): {"documentos"}}


class OtherPages(unittest.TestCase):
    def test_whole_words_at_150_percent_on_small_phones(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    for path, sel in OTHER:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + path)
                        if not page.locator(sel).count():
                            if sel == ORGANIZER:          # the bots' data: no event with an organizer's page today
                                with self.subTest(lang=lang, prefs=prefs, page=path):
                                    self.skipTest("no event card with an Organizer button in this build")
                                page.close()
                                continue
                            problems.append(f"/{lang} {path}: nothing matches {sel}")
                        for width in (320, 340, 360, 375):
                            page.set_viewport_size({"width": width, "height": 800})
                            settle(page)
                            pre = "es/" if lang == "es" else ""
                            wider = WIDER_THAN_ITS_CARD.get((pre + path, width, "spacing" in prefs), set())
                            if split := [w for w in page.evaluate(SPLIT_WORDS, sel) if w not in wider]:
                                problems.append(f"/{pre}{path} {width}px {prefs}: words broken in two: {sorted(set(split))}")
                        page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_gvr_tool_cards_at_115_and_130_percent(self):
        problems = []
        for lang in ("en", "es"):
            for prefs in ({"text": 115, "spacing": "relaxed"}, {"text": 130}, {"text": 130, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "gvr/")
                    for width in (320, 360, 390, 414):
                        page.set_viewport_size({"width": width, "height": 800})
                        settle(page)
                        if split := page.evaluate(SPLIT_WORDS, GVR_TOOLS):
                            problems.append(f"/{lang} gvr/ {width}px {prefs}: words broken in two: {sorted(set(split))}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_the_organizer_button_with_relaxed_spacing_two_to_a_row(self):
        ctx = new_context(390, 800, lang="es", prefs={"spacing": "relaxed"})
        try:
            page = open_page(ctx, "es/events/")
            if not page.locator(ORGANIZER).count():
                self.skipTest("no event card with an Organizer button in this build")
            self.assertEqual(page.evaluate(SPLIT_WORDS, ORGANIZER), [])
            page.close()
        finally:
            ctx.close()

    def test_at_100_percent_the_icons_stay(self):
        """the round-38b rules act only at larger text: at 100 % on phones the tool cards keep their icon beside the
        words (three columns), the panel titles and the feeds' buttons their icon, "Organizer ↗" its icon"""
        for lang in ("en", "es"):
            for width in (320, 414):
                with self.subTest(lang=lang, width=width):
                    ctx = new_context(width, 800, lang=lang)
                    pre = "es/" if lang == "es" else ""
                    try:
                        for path, sel in (("gvr/", ".lt-fold"), ("stay-updated/", ".lt-fold"), ("status/", ".lt-fold"),
                                          ("events/", ".ev-org-btn > svg")):
                            page = open_page(ctx, pre + path)
                            if path == "gvr/":
                                cols = page.evaluate("(sel) => [...document.querySelectorAll(sel)].map((li) => "
                                                     "getComputedStyle(li).gridTemplateColumns.split(' ').length)", GVR_TOOLS)
                                self.assertEqual(cols, [3, 3], "the tool cards: icon · words · arrow")
                            shown = page.evaluate("(sel) => [...document.querySelectorAll(sel)].map((e) => getComputedStyle(e).display)", sel)
                            if not shown and path == "events/":     # (as above)
                                with self.subTest(page=path):
                                    self.skipTest("no event card with an Organizer button in this build")
                                page.close()
                                continue
                            self.assertTrue(shown, f"/{pre}{path}: {sel}")
                            self.assertNotIn("none", shown, f"/{pre}{path}: {sel}")
                            page.close()
                    finally:
                        ctx.close()

    def test_the_status_numbers_and_toggles(self):
        """/status/ at 130–150 %: the three numbers under the hero (.cm-st-stats) on 640–880px — three to a row their
        words had 125–180px, and "4,208", "minutes", "Encontrados", "registrados" broke in two; they go one under the
        other below 896px —; and on 320–390px phones a source's maintainer toggles (details.cm-preview.ml-6, "Notes
        from the last update", "Technical details": "maintaine|r", "actualizació|n") — they lose their indent and part
        of their padding, and the source's words go under its icon below 9em. (The toggles are there only while a
        source has notes or failed: that part is skipped when none is.)"""
        problems, toggles = [], 0
        for lang in ("en", "es"):
            pre = "es/" if lang == "es" else ""
            for prefs in ({"text": 130}, {"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(1024, 800, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, pre + "status/")
                    if not page.locator(".cm-st-stats").count():
                        problems.append(f"/{pre}status/: no .cm-st-stats")
                    for width in (640, 720, 768, 880):
                        page.set_viewport_size({"width": width, "height": 800})
                        settle(page)
                        if split := page.evaluate(SPLIT_WORDS, ".cm-st-stats"):
                            problems.append(f"/{pre}status/ {width}px {prefs}: the numbers' words broken in two: {split}")
                    for width in (320, 340, 360, 375, 390):
                        page.set_viewport_size({"width": width, "height": 800})
                        settle(page)
                        toggles += page.evaluate("() => [...document.querySelectorAll('details.cm-preview.ml-6 > summary')]"
                                                 ".filter((e) => e.getClientRects().length).length")
                        if split := page.evaluate(SPLIT_WORDS, "details.cm-preview.ml-6 > summary"):
                            problems.append(f"/{pre}status/ {width}px {prefs}: a maintainer toggle's words broken in two: "
                                            f"{sorted(set(split))}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])
        if not toggles:
            self.skipTest("the numbers checked; no source has notes or failed in this build, so no maintainer toggle")

    def test_the_small_event_cards_keep_their_words(self):
        """the small event cards (.cm-mini-card) at 115–150 % on phones and in the two-column grid at 640px: Share your
        story's next workshops (28px for the words at 150 % on a 320px phone, one letter per line), an event page's
        other events beside a flyer's thumbnail (75–82px at 115 %: "Worksho|p"), a cancelled event's notice — pages
        chosen from the build, skipped when it has none. A word wider than the card's whole inside (at 150 % with
        relaxed spacing on a 320px phone "Workshop", 160px in 145px) is left to hyphenation."""
        site, pages = S["site"], []
        if "data-ws-list" in (site / "contribute/index.html").read_text(encoding="utf-8"):
            pages.append("contribute/")
        for kind, mark in (("thumbs", 'class="evp-mini-thumb"'), ("cancelled", 'id="ev-cancel-next"')):
            path = next((p for p in event_pages()
                         if not p.startswith("es/") and mark in (site / p / "index.html").read_text(encoding="utf-8")), None)
            if path:
                pages.append(path)
            else:
                with self.subTest(kind=kind):
                    self.skipTest(f"no event page with small cards of this kind ({kind}) in this build")
        if not pages:
            self.skipTest("no small event cards in this build")
        problems = []
        for lang in ("en", "es"):
            pre = "es/" if lang == "es" else ""
            for prefs in ({"text": 115}, {"text": 115, "spacing": "relaxed"}, {"text": 130}, {"text": 130, "spacing": "relaxed"},
                          {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(320, 800, lang=lang, prefs=prefs)
                try:
                    for path in pages:
                        page = open_page(ctx, pre + path)
                        for width in (320, 340, 360, 390, 414, 640):
                            page.set_viewport_size({"width": width, "height": 800})
                            settle(page)
                            if split := page.evaluate(SPLIT_FITTING, "a.cm-mini-card"):
                                problems.append(f"/{pre}{path} {width}px {prefs}: words broken in two: {sorted(set(split))}")
                        page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_the_read_pages_subscribe_note_on_tablets(self):
        """(round 38b review) /read/'s "Ways to subscribe" note (from 640px one row: the key, the words, the button —
        read.njk) at 130–150 % with relaxed spacing too, on 640–800px tablets: the page never scrolls sideways (the
        button kept its whole width and ran 20–79px past the screen at 640–720px: "Formas de suscribirte"), the button
        stays inside the note — it goes under the words —, and no word of the note breaks in two ("suscriptores",
        "autosuficiente," beside it); at 100 % and 115 % the button stays beside the words, as before."""
        problems = []
        for lang in ("en", "es"):
            pre = "es/" if lang == "es" else ""
            for prefs in (None, {"text": 115}, {"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                ctx = new_context(640, 900, lang=lang, prefs=prefs)
                try:
                    page = open_page(ctx, pre + "read/")
                    for width in (640, 656, 672, 688, 704, 720, 752, 800):
                        page.set_viewport_size({"width": width, "height": 900})
                        settle(page)
                        where = f"/{pre}read/ {width}px {prefs or '100 %'}"
                        if s := sideways(page):
                            problems.append(f"{where}: {s}")
                        r = page.evaluate(READ_NOTE)
                        if not r:
                            problems.append(f"{where}: no Ways to subscribe note")
                            continue
                        if r["btn"]["right"] > r["box"]["right"] + 0.5:
                            problems.append(f"{where}: the button runs {round(r['btn']['right'] - r['box']['right'])}px past its note")
                        if prefs in (None, {"text": 115}) and r["btn"]["top"] >= r["words"]["bottom"]:
                            problems.append(f"{where}: the button went under the words")
                        if split := page.evaluate(SPLIT_WORDS, READ_NOTE_SEL):
                            problems.append(f"{where}: words broken in two: {sorted(set(split))}")
                    page.close()
                finally:
                    ctx.close()
        self.assertEqual(problems, [])


# /read/'s "Ways to subscribe" note (read.njk: the key, the words, the button), found by its button: the note's box, the
# button's and the words' column's
READ_NOTE_SEL = 'section.page-start > div:has(> a.btn-primary[href*="#subscriptions"])'
READ_NOTE = """() => {
  const box = document.querySelector('section.page-start > div:has(> a.btn-primary[href*="#subscriptions"])');
  if (!box) return null;
  const rect = (e) => { const r = e.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }; };
  return { box: rect(box), btn: rect(box.querySelector(':scope > a.btn-primary')), words: rect(box.querySelector(':scope > div')) };
}"""


# Each button of the open notice: where it is against the notice's own box (which scrolls) and the control bar, and
# whether the button itself is what a tap at its middle and near each end reaches (nothing over it, not scrolled away)
NOTICE_BUTTONS = """() => {
  const box = document.querySelector('[data-gvp-notice]:not([hidden])'), bar = document.querySelector('.gvp-bar');
  if (!box) return null;
  const nb = box.getBoundingClientRect(), bb = bar.getBoundingClientRect();
  return [...box.querySelectorAll('.gvp-notice-actions button')].map((b) => {
    const r = b.getBoundingClientRect();
    const hit = [[0.5, 0.5], [0.5, 0.08], [0.5, 0.92], [0.08, 0.5], [0.92, 0.5]].every(([fx, fy]) => {
      const e = document.elementFromPoint(r.left + r.width * fx, r.top + r.height * fy);
      return !!e && (e === b || b.contains(e)); });
    return { text: b.textContent.trim(), top: Math.round(r.top), bottom: Math.round(r.bottom), inBox: r.top >= nb.top - 0.5 && r.bottom <= nb.bottom + 0.5,
             overBar: r.bottom > bb.top + 0.5, hit, scrolls: box.scrollHeight > box.clientHeight + 1 };
  });
}"""


class DeckNotice(unittest.TestCase):
    """A presentation's "details still blank" notice (presentations.js fillNotice: the Grapevine Meeting's deck opened
    with its blanks empty) on a phone held upright — the stage reflowed —, 320–430px, at 100–150 % text with and
    without relaxed spacing, English and Spanish: its buttons ("Fill them in", "Present anyway") are whole and in
    sight, inside the notice's box and above the control bar, also when its words are taller than the room and it
    scrolls (round 38: at 150 % with relaxed spacing on a 320px phone they were below the notice's fold —
    presentations.css keeps them at its foot)."""

    def test_its_buttons_stay_in_sight(self):
        problems = []
        for lang in ("en", "es"):
            for width in (320, 360, 430):
                for prefs in ({}, {"text": 130, "spacing": "relaxed"}, {"text": 150}, {"text": 150, "spacing": "relaxed"}):
                    ctx = new_context(width, 800, lang=lang, prefs=prefs)
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + "orientation/?present=grapevine-meeting")
                        page.locator("[data-gvp-notice]:not([hidden]) .gvp-notice-actions button").first.wait_for(timeout=30_000)
                        page.wait_for_timeout(300)
                        where = f"/{'es/' if lang == 'es' else ''} {width}px {prefs or '100 %'}"
                        self.assertTrue(page.evaluate("() => document.querySelector('.gvp').classList.contains('is-reflow')"), where)
                        buttons = page.evaluate(NOTICE_BUTTONS)
                        self.assertEqual(len(buttons or []), 2, where)
                        for b in buttons:
                            if not (b["inBox"] and not b["overBar"] and b["hit"]):
                                problems.append(f"{where}: {b}")
                        page.close()
                    finally:
                        ctx.close()
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
