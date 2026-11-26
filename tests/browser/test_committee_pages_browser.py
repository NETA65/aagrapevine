"""Round 33 · the committee pages' audit fixes on the built site, in a real browser (tests/browser/__init__.py says how
to run these; they share test_site_in_browser.py's site server and browser). The CSS, the templates and the
slideshow's script on their own: tests/test_committee_pages.py.

  * PhotoSlideshow — /photos/ (en + es): Enter on a photo puts the focus INTO the slideshow (its dialog), Tab stays
                     in it, and Escape or Close puts it back on that photo (the page does not jump); only the slide
                     on show is there for a screen reader. On a phone and at 640px (a desktop at 200%) Previous and
                     Next are on the screen, above the caption, and work. A swipe down with motion reduced closes it
                     without a script error (it threw a TypeError on every swipe).
  * EventCards     — /events/: a card far down is drawn only near the screen (content-visibility: Dark mode / High
                     contrast no longer freeze the page), yet every "Add to calendar" menu opens whole — all its
                     choices can be clicked, at 1280px and on a phone —, print draws every card, and a #ev-… link
                     still lands its card right under the header.
  * Rings          — the pinned committee-meeting card's controls have a ring that shows on its plum (≥ 3:1, light and
                     high contrast); inside the light "Add to calendar" panel (/meetings/' countdown cards, /events/'
                     pinned card) the ring is the site's blue, not white on white.
  * Calendar       — /events/' past days are not see-through and their words keep 4.5:1.
"""
from __future__ import annotations

import io
import json
import unittest

from .test_site_in_browser import S, contrast, new_context, open_page, ring_contrast, setUpModule, tearDownModule, url  # noqa: F401

ACTIVE = """() => { const a = document.activeElement; return a ? { id: a.id, photo: a.matches('a.glightbox-cm'),
  inDialog: !!a.closest('#glightbox-body'), label: a.getAttribute('aria-label') || '' } : null; }"""
SLIDES = """() => { const s = [...document.querySelectorAll('#glightbox-body .gslide')];
  return { n: s.length, current: s.findIndex((x) => x.classList.contains('current')),
           exposed: s.map((x, i) => (!x.inert && x.getAttribute('aria-hidden') !== 'true') ? i : -1).filter((i) => i >= 0) }; }"""


def _photo(page, n: int = 5):
    """The n-th photo of the page, focused by script (the keyboard's Tab walk is the audit's; the result the same)."""
    page.evaluate("(n) => { const a = document.querySelectorAll('a.glightbox-cm')[n]; a.scrollIntoView({ block: 'center' }); a.focus(); }", n)
    return page.evaluate("(n) => document.querySelectorAll('a.glightbox-cm')[n].getAttribute('aria-label')", n)


class PhotoSlideshow(unittest.TestCase):
    def test_the_keyboard_goes_in_and_comes_back(self):
        for lang in ("en", "es"):
            for how in ("escape", "close"):
                with self.subTest(lang=lang, close=how):
                    errors: list[str] = []
                    ctx = new_context(1280, 800, lang=lang)
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + "photos/", errors)
                        label = _photo(page)
                        y = page.evaluate("scrollY")
                        page.keyboard.press("Enter")
                        page.wait_for_selector("#glightbox-body .gslide.current", timeout=10_000)
                        page.wait_for_timeout(300)
                        a = page.evaluate(ACTIVE)
                        self.assertTrue(a["inDialog"], f"the focus is in the slideshow, not behind it: {a}")
                        sl = page.evaluate(SLIDES)
                        self.assertEqual(sl["exposed"], [sl["current"]], "only the slide on show is there for a screen reader")
                        page.keyboard.press("ArrowRight")
                        page.wait_for_timeout(600)
                        sl = page.evaluate(SLIDES)
                        self.assertEqual(sl["exposed"], [sl["current"]], "…after a change of slide too")
                        for _ in range(4):                       # Tab never leaves the dialog
                            page.keyboard.press("Tab")
                            self.assertTrue(page.evaluate(ACTIVE)["inDialog"])
                        if how == "close":
                            for _ in range(3):
                                if "gclose" in page.evaluate("document.activeElement.className"):
                                    break
                                page.keyboard.press("Tab")
                            page.keyboard.press("Enter")
                        else:
                            page.keyboard.press("Escape")
                        page.wait_for_selector("#glightbox-body", state="detached", timeout=10_000)
                        page.wait_for_timeout(200)
                        a = page.evaluate(ACTIVE)
                        self.assertTrue(a["photo"], f"back on the photo: {a}")
                        self.assertEqual(a["label"], label)
                        self.assertEqual(page.evaluate("scrollY"), y, "the page did not move")
                        self.assertEqual(errors, [])
                    finally:
                        ctx.close()

    def test_previous_and_next_are_on_a_phones_screen(self):
        for width, height, touch in ((390, 844, True), (640, 800, False)):
            with self.subTest(width=width):
                kw = dict(viewport={"width": width, "height": height}, reduced_motion="reduce", service_workers="block",
                          timezone_id="America/Chicago")
                if touch:
                    kw.update(is_mobile=True, has_touch=True, device_scale_factor=3)
                ctx = S["browser"].new_context(**kw)
                try:
                    page = open_page(ctx, "photos/")
                    page.evaluate("document.querySelectorAll('a.glightbox-cm')[5].click()")
                    page.wait_for_selector("#glightbox-body .gslide.current", timeout=10_000)
                    page.wait_for_timeout(500)
                    r = page.evaluate("""() => { const o = {}; for (const c of ['gprev', 'gnext']) { const b = document.querySelector('#glightbox-body .' + c);
                        const r = b.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                        o[c] = { top: r.top, bottom: r.bottom, hit: !!(h && b.contains(h)) }; }
                        const d = document.querySelector('#glightbox-body .gslide.current .gslide-description');
                        o.caption = d ? d.getBoundingClientRect().top : innerHeight; return o; }""")
                    for c in ("gprev", "gnext"):
                        self.assertGreaterEqual(r[c]["top"], 0, (c, r))
                        self.assertTrue(r[c]["hit"], (c, r))
                        self.assertLessEqual(r[c]["bottom"], r["caption"], ("clear of the caption", c, r))
                    i = page.evaluate("CM.lightbox.index")
                    box = page.locator("#glightbox-body .gnext").bounding_box()
                    if touch:
                        page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    else:
                        page.locator("#glightbox-body .gnext").click()
                    page.wait_for_timeout(600)
                    self.assertEqual(page.evaluate("CM.lightbox.index"), i + 1)
                finally:
                    ctx.close()

    def test_a_swipe_down_closes_it_without_an_error_with_motion_reduced(self):
        for path in ("photos/", "es/photos/"):
            with self.subTest(path=path):
                ctx = S["browser"].new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                                               device_scale_factor=3, reduced_motion="reduce", service_workers="block")
                errors: list[str] = []
                try:
                    page = open_page(ctx, path, errors)
                    page.evaluate("document.querySelectorAll('a.glightbox-cm')[5].click()")
                    page.wait_for_selector("#glightbox-body .gslide.current", timeout=10_000)
                    page.wait_for_timeout(500)
                    cdp = ctx.new_cdp_session(page)
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 195, "y": 300}]})
                    for y in range(320, 720, 40):
                        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 195, "y": y}]})
                        page.wait_for_timeout(16)
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                    page.wait_for_selector("#glightbox-body", state="detached", timeout=10_000)
                    page.wait_for_timeout(300)
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


MENU = """(i) => { const d = document.querySelectorAll('.cm-event .cm-menu')[i], p = d.querySelector('.cm-menu-panel');
  p.scrollIntoView({ block: 'nearest' });
  return { open: d.open, below: p.getBoundingClientRect().bottom - d.closest('.cm-event').getBoundingClientRect().bottom,
           items: [...p.querySelectorAll('a, button')].map((a) => { const r = a.getBoundingClientRect();
             const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!(h && a.contains(h)); }) }; }"""


class EventCards(unittest.TestCase):
    def test_every_calendar_menu_opens_whole(self):
        for width, height, touch in ((1280, 800, False), (390, 844, True)):
            with self.subTest(width=width):
                kw = dict(viewport={"width": width, "height": height}, reduced_motion="reduce", service_workers="block",
                          timezone_id="America/Chicago")
                if touch:
                    kw.update(is_mobile=True, has_touch=True, device_scale_factor=3)
                ctx = S["browser"].new_context(**kw)
                try:
                    page = open_page(ctx, "events/")
                    shown = page.evaluate("[...document.querySelectorAll('.cm-event .cm-menu')].map((d, i) => d.getClientRects().length ? i : -1).filter((i) => i >= 0)")
                    self.assertGreater(len(shown), 10)
                    # (the mechanism: a card far off the screen is skipped until it comes near)
                    self.assertEqual(page.evaluate("getComputedStyle([...document.querySelectorAll('li[data-group] > .cm-event')].pop()).contentVisibility"), "auto")
                    for i in (shown[0], shown[len(shown) // 2], shown[-1]):
                        s = page.locator(".cm-event .cm-menu > summary").nth(i)
                        s.scroll_into_view_if_needed()
                        s.tap() if touch else s.click()
                        page.wait_for_timeout(150)
                        r = page.evaluate(MENU, i)
                        self.assertTrue(r["open"])
                        self.assertGreater(r["below"], 0, "the panel hangs below the card: the case that was clipped")
                        self.assertEqual(r["items"], [True] * len(r["items"]), f"menu {i}: every choice can be clicked")
                        page.keyboard.press("Escape")
                        page.evaluate("(i) => { document.querySelectorAll('.cm-event .cm-menu')[i].open = false; }", i)
                    page.emulate_media(media="print")
                    self.assertEqual(page.evaluate("[...new Set([...document.querySelectorAll('.cm-event')].map((e) => getComputedStyle(e).contentVisibility))]"),
                                     ["visible"], "print draws every card")
                finally:
                    ctx.close()

    def test_a_link_to_a_card_still_lands_it_under_the_header(self):
        ctx = new_context(1280, 800)
        try:
            page = open_page(ctx, "events/")
            ids = page.evaluate("[...document.querySelectorAll('li[data-group][id]')].filter((li) => li.getClientRects().length).map((li) => li.id)")
            for anchor in (ids[len(ids) // 2], ids[-2]):
                with self.subTest(anchor=anchor):
                    page.goto(url("events/") + "#" + anchor, wait_until="load")
                    page.wait_for_timeout(1500)
                    r = page.evaluate("""(a) => ({ top: document.getElementById(a).getBoundingClientRect().top,
                        pad: parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0 })""", anchor)
                    self.assertAlmostEqual(r["top"], r["pad"], delta=3, msg=r)
        finally:
            ctx.close()


class Rings(unittest.TestCase):
    FOCUS = """(sel) => { const el = document.querySelector(sel); el.focus({ preventScroll: true }); const cs = getComputedStyle(el), r = el.getBoundingClientRect();
      return { fv: el.matches(':focus-visible'), width: parseFloat(cs.outlineWidth) || 0, offset: parseFloat(cs.outlineOffset) || 0,
               radius: parseFloat(cs.borderTopLeftRadius) || 0, box: { x: r.x, y: r.y, width: r.width, height: r.height } }; }"""

    def _ring(self, page, sel: str) -> float:
        from PIL import Image
        page.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", sel)
        page.wait_for_timeout(120)
        before = Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
        f = page.evaluate(self.FOCUS, sel)
        page.wait_for_timeout(80)
        after = Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
        page.evaluate("document.activeElement.blur()")
        self.assertTrue(f["fv"], sel)
        return ring_contrast(after, before, f["box"], f["offset"], f["width"], f["radius"])[0]

    def test_the_pinned_cards_ring_shows_on_its_plum(self):
        for prefs in (None, {"contrast": "high"}):
            ctx = new_context(1280, 800, prefs=prefs)
            try:
                page = open_page(ctx, "events/")
                page.keyboard.press("Tab")               # (a keyboard user: rings show on script focus too)
                n = page.evaluate("""() => { const a = [...document.querySelectorAll('.cm-pinned-actions > a, .cm-pinned-actions > .cm-menu > summary')]
                    .filter((e) => e.getBoundingClientRect().width > 0); a.forEach((e, i) => e.setAttribute('data-r33', i)); return a.length; }""")
                self.assertGreaterEqual(n, 2)
                for i in range(n):
                    with self.subTest(prefs=prefs, control=i):
                        self.assertGreaterEqual(self._ring(page, f'[data-r33="{i}"]'), 3)
            finally:
                ctx.close()

    def test_inside_the_light_menu_panel_the_ring_is_blue(self):
        for path, scope in (("meetings/", ".cm-count"), ("events/", ".cm-pinned")):
            with self.subTest(path=path):
                ctx = new_context(1280, 800)
                try:
                    page = open_page(ctx, path)
                    page.evaluate(f"""() => {{ const s = document.querySelector('{scope} details.cm-menu > summary'); s.scrollIntoView({{ block: 'center' }}); s.focus(); }}""")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(250)
                    page.keyboard.press("Tab")
                    page.wait_for_timeout(150)
                    self.assertTrue(page.evaluate("!!document.activeElement.closest('.cm-menu-panel')"))
                    page.evaluate("document.activeElement.setAttribute('data-r33m', '')")
                    from PIL import Image
                    after = Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
                    f = page.evaluate("""() => { const el = document.activeElement, cs = getComputedStyle(el), r = el.getBoundingClientRect();
                        return { color: cs.outlineColor, width: parseFloat(cs.outlineWidth) || 0, offset: parseFloat(cs.outlineOffset) || 0,
                                 radius: parseFloat(cs.borderTopLeftRadius) || 0, box: { x: r.x, y: r.y, width: r.width, height: r.height } }; }""")
                    page.evaluate(f"document.querySelector('{scope} details.cm-menu > summary').focus()")
                    page.wait_for_timeout(120)
                    before = Image.open(io.BytesIO(page.screenshot(animations="disabled"))).convert("RGB")
                    self.assertNotEqual(f["color"], "rgb(255, 255, 255)", "not white on the white panel")
                    self.assertGreaterEqual(ring_contrast(after, before, f["box"], f["offset"], f["width"], f["radius"])[0], 3)
                finally:
                    ctx.close()


class Calendar(unittest.TestCase):
    def test_past_days_keep_their_contrast(self):
        for theme in ("light", "dark"):
            ctx = new_context(1280, 800, theme=theme)
            try:
                page = open_page(ctx, "events/")
                days = page.evaluate("""() => [...document.querySelectorAll('.cm-cal-d.is-past')].map((td) => {
                    const e = td.querySelector('.cm-cal-day, .cm-cal-link'), card = td.closest('.card');
                    let o = 1; for (let x = e; x; x = x.parentElement) o *= parseFloat(getComputedStyle(x).opacity);
                    const rgb = (s) => s.match(/\\d+/g).slice(0, 3).map(Number);
                    return { day: td.getAttribute('data-cm-day'), opacity: o, fg: rgb(getComputedStyle(e).color), bg: rgb(getComputedStyle(card).backgroundColor) }; })""")
                if not days:
                    self.skipTest("no past day in the calendar's first week today")
                for d in days:
                    with self.subTest(theme=theme, day=d["day"]):
                        self.assertEqual(d["opacity"], 1, "never see-through")
                        self.assertGreaterEqual(contrast(d["fg"], d["bg"]), 4.5, d)
            finally:
                ctx.close()


if __name__ == "__main__":
    unittest.main()
