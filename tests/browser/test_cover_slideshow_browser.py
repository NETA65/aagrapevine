"""Round 33c · /photos/' magazine covers: the slideshow goes through exactly the covers on screen, on the built site
in a real browser (tests/browser/__init__.py says how to run these; they share test_site_in_browser.py's site server
and browser). The script on its own: tests/test_cover_slideshow.py.

The bug (live, 2026-11-17): /photos/?year=1948&month=9 showed 1 cover, yet its slideshow held 93 — every September of
every year, both magazines — and Next went to "Grapevine — September 1947", which was not on screen.

For each language, on the site's own covers: the address with a year and a month that have one cover (1948 and
September while that cover is in the synced data — the Drive sync of 2026-11-17 took it away —, else the first such
pair on the page: the test checks the code, never which covers the committee has), a month alone, then with the
filter's own chips and lists a decade and the month, a magazine and the month, another month, a year with them, and
last "Clear filters" (each block its own slideshow again). Each time the first cover on screen is opened with the
keyboard, Next (→) goes through every slide — each one a cover on screen, in the page's order, the slide's title its
own —, the count of slides is the count of covers on screen, one more → comes back to the first (the slideshow
loops), and Escape puts the focus back on that cover (round 33). No script error on the page.
"""
from __future__ import annotations

import unittest

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

# the covers on screen, in the page's order: [their title as the slideshow shows it]
ON_SCREEN = """() => { const d = document.createElement('textarea');
  return [...document.querySelectorAll('#covers a.glightbox-cm')].filter((a) => a.getClientRects().length > 0)
    .map((a) => { d.innerHTML = a.getAttribute('data-title') || ''; return d.value; }); }"""
# the slide on show: which cover on screen it is (-1: none), its title, the block it is in
SLIDE = """() => { const lb = CM.lightbox, n = lb.elements[lb.index] && lb.elements[lb.index].node;
  const vis = [...document.querySelectorAll('#covers a.glightbox-cm')].filter((a) => a.getClientRects().length > 0);
  const s = document.querySelectorAll('#glightbox-body .gslide')[lb.index], t = s && s.querySelector('.gslide-title');
  return { index: lb.index, at: vis.indexOf(n), title: t ? t.textContent.trim() : '',
           block: n && n.closest('[data-cm-cover]') ? n.closest('[data-cm-cover]').id : '' }; }"""
FOCUS_FIRST = """() => { const a = [...document.querySelectorAll('#covers a.glightbox-cm')].find((x) => x.getClientRects().length > 0);
  a.scrollIntoView({ block: 'center' }); a.focus(); return a.getAttribute('aria-label'); }"""
ACTIVE = "() => document.activeElement ? document.activeElement.getAttribute('aria-label') || '' : ''"
STATE = """() => { const p = new URLSearchParams(location.search); return ['mag', 'decade', 'year', 'month'].map((k) => p.get(k) || ''); }"""
# a year and a month with ONE cover on the page (the covers are the committee's Drive files: a sync can take one
# away, as it took September 1948 on 2026-11-17) — the bug's own 1948 + September while it is there, else the first
# year among the folded earlier years (data-cm-early: every year but the two newest) and month that has one: [year,
# month] as strings, or null
ONE_COVER = """() => { const one = {};
  for (const li of document.querySelectorAll('#covers [data-cm-cover][data-cm-early] li[data-months]')) {
    const y = li.closest('[data-cm-cover]').dataset.year;
    for (const m of li.dataset.months.split(/\\s+/).filter(Boolean)) { const k = y + ':' + m; one[k] = (one[k] || 0) + 1; }
  }
  const keys = Object.keys(one).filter((k) => one[k] === 1);
  const k = keys.includes('1948:9') ? '1948:9' : keys[0];
  return k ? k.split(':') : null; }"""


class CoversSlideshow(unittest.TestCase):
    def walk(self, page, what: str, flat: bool = True) -> int:
        """Open the first cover on screen, → through every slide, Escape. → the number of slides."""
        vis = page.evaluate(ON_SCREEN)
        self.assertTrue(vis, f"{what}: covers on screen")
        label = page.evaluate(FOCUS_FIRST)
        page.keyboard.press("Enter")
        page.wait_for_selector("#glightbox-body .gslide.current", timeout=10_000)
        n = page.evaluate("document.querySelectorAll('#glightbox-body .gslide').length")
        # (from the slide it opened on, whichever that is: → n − 1 times goes round the whole slideshow)
        start = page.evaluate("CM.lightbox.index")
        slides = []
        for i in range(n):
            if i:
                page.keyboard.press("ArrowRight")
                page.wait_for_function("(i) => CM.lightbox.index === i && document.querySelectorAll('#glightbox-body .gslide')[i]"
                                       ".classList.contains('current')", arg=(start + i) % n, timeout=10_000)
            slides.append(page.evaluate(SLIDE))
        off = [s["title"] for s in slides if s["at"] < 0]
        self.assertEqual(off, [], f"{what}: {len(off)} of {n} slides are covers not on screen ({len(vis)} on screen)")
        self.assertEqual(start, 0, f"{what}: the first cover on screen is the first slide")
        if flat:
            # a Month: every cover on screen, in the page's order
            self.assertEqual(n, len(vis), f"{what}: {n} slides for {len(vis)} covers on screen")
            self.assertEqual([s["at"] for s in slides], list(range(n)), f"{what}: in the page's order")
        else:
            # no Month: the first cover's block, every cover of it on screen, in order
            block = slides[0]["block"]
            ids = page.evaluate("(id) => [...document.getElementById(id).querySelectorAll('a.glightbox-cm')].length", block)
            self.assertEqual(n, ids, f"{what}: the block's {ids} covers")
            self.assertEqual({s["block"] for s in slides}, {block})
            self.assertEqual([s["at"] for s in slides], list(range(n)))
        self.assertEqual([s["title"] for s in slides], vis[:n], f"{what}: each slide's own title")
        if n > 1:                                        # it loops: one more → is the first again
            page.keyboard.press("ArrowRight")
            page.wait_for_function("(s) => CM.lightbox.index === s", arg=start, timeout=10_000)
        page.keyboard.press("Escape")
        page.wait_for_selector("#glightbox-body", state="detached", timeout=10_000)
        page.wait_for_timeout(150)
        self.assertEqual(page.evaluate(ACTIVE), label, f"{what}: Escape puts the focus back on the cover")
        return n

    def test_the_slideshow_holds_the_covers_on_screen(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                pre = "es/" if lang == "es" else ""
                errors: list[str] = []
                ctx = new_context(1280, 900, lang=lang)
                try:
                    # the bug's own address (a year and a month with one cover): one cover, one slide
                    page = open_page(ctx, pre + "photos/", errors)
                    one = page.evaluate(ONE_COVER)
                    self.assertIsNotNone(one, "a year and a month with one cover")
                    page.close()
                    page = open_page(ctx, pre + f"photos/?year={one[0]}&month={one[1]}", errors)
                    self.assertEqual(page.evaluate(STATE), ["", "", one[0], one[1]])
                    self.assertEqual(self.walk(page, f"{one[0]} + month {one[1]}"), 1)
                    page.close()
                    # a month alone (every September), then the filter's own controls on that page
                    page = open_page(ctx, pre + "photos/?month=9", errors)
                    every = self.walk(page, "September")
                    self.assertGreater(every, 50, "every September, both magazines")
                    page.click('#covers [data-cm-decade="1940"]')
                    self.assertEqual(page.evaluate(STATE), ["", "1940", "", "9"])
                    self.assertLess(self.walk(page, "1940s + September"), every)
                    page.click('#covers [data-cm-mag="lv"]')         # La Viña has no 1940s: the decade lets go
                    self.assertEqual(page.evaluate(STATE), ["lv", "", "", "9"])
                    self.walk(page, "La Viña + September")
                    page.select_option("#cm-covers-month", "3")
                    self.walk(page, "La Viña + March")
                    year = page.evaluate("() => [...document.querySelectorAll('#cm-covers-year option[data-cm-year]')]"
                                         ".find((o) => !o.disabled).value")
                    page.select_option("#cm-covers-year", year)
                    self.assertEqual(page.evaluate(STATE)[2:], [year, "3"])
                    self.walk(page, f"La Viña + {year} + March")
                    # Clear filters: each block its own slideshow again (the first block's covers)
                    page.click("#covers .cm-covers-status button")
                    self.assertEqual(page.evaluate(STATE), ["", "", "", ""])
                    self.assertEqual(page.evaluate("() => [...document.querySelectorAll('#covers a.glightbox-cm')]"
                                                   ".filter((a) => a.dataset.gallery !== a.dataset.cmGallery).length"), 0)
                    self.walk(page, "no filter", flat=False)
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
