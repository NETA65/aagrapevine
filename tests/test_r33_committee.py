"""Round 33 · the committee pages' audit fixes (/events/, /photos/, /meetings/): the CSS and templates as they keep
them fixed, the photo slideshow's keyboard handling run in Node.js (tests/fakedom.py), and the built /events/ and
/photos/ (en + es) checked for Alpine directives where Alpine no longer looks. The same in a real browser:
tests/browser/test_r33_committee.py.

  * Rings        — the white focus ring on the dark countdown cards (.cm-count) and the pinned committee-meeting
                   card (.cm-pinned) stops at their light "Add to calendar" panel (.cm-menu-panel): its choices keep
                   the site's blue ring (white on white was no ring).
  * Event cards  — drawn only near the screen (content-visibility: a Dark mode / High contrast switch froze /events/
                   for 2–3 s), but a card whose "Add to calendar" menu is open is drawn whole (else the menu is cut
                   off at the card's edge), print draws every card, and only where :has() works.
  * Calendar     — the past days and the entries that are over are in the faint ink (≥ 4.5:1 in every theme), never
                   see-through; only their dots are faded.
  * Slideshow    — Previous / Next on the screen at every width (GLightbox hides them off it below 769px), a white
                   keyboard ring on its buttons; the focus goes into the slideshow when it opens and back to the photo
                   (or "Full screen") that opened it when it closes; only the slide on show is there for a screen
                   reader; with motion reduced, closing waits a moment (a swipe-down threw a TypeError).
  * x-ignore     — Alpine skips the event cards and the cover grids (thousands of elements, no directives); the
                   built pages have no x-…, @… or :… attribute inside an x-ignore, and none on an element that has
                   its own.

    python -m unittest tests.test_r33_committee -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402
from test_a11y_layout import contrast, themes  # noqa: E402


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


CSS = read("src", "assets", "css", "areas", "committee.css")


def flat(css: str) -> str:
    """The CSS without its comments, on one line (a rule's text whatever the wrapping)."""
    return re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", " ", css, flags=re.S))


class Rings(unittest.TestCase):
    def test_the_white_ring_stops_at_the_light_menu_panel(self):
        css = flat(CSS)
        for card in (".cm-count", ".cm-pinned"):
            with self.subTest(card=card):
                self.assertIn(card + " :focus-visible:not(.cm-menu-panel *) { outline-color: #fff; }", css)
                self.assertNotIn(card + " :focus-visible { outline-color", css, "the panel's choices keep the blue ring")
        # the panel really is light (the surface colour), so a white ring there would vanish
        self.assertRegex(css, r"\.cm-menu-panel \{[^}]*background: var\(--c-surface\)")


class EventCards(unittest.TestCase):
    def test_cards_render_near_the_screen_but_an_open_menu_and_print_draw_them_whole(self):
        css = flat(CSS)
        start = css.find("@supports selector(:has(*)) {")
        self.assertNotEqual(start, -1, "only where :has() works: the open-menu exception needs it")
        depth, end = 0, start
        for i in range(start, len(css)):        # the @supports block, to its own closing brace
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            if css[i] == "}" and depth == 0:
                end = i
                break
        sup = css[start:end]
        self.assertIn(".cm-event { content-visibility: auto; contain-intrinsic-block-size: auto 23rem; }", sup)
        # the placeholder follows the median card's height at each width (a reload's scroll position lands on the
        # same card): one size per breakpoint, every one "auto" (a card drawn once keeps its real height)
        sizes = re.findall(r"@media \(width >= (\d+)rem\) \{ \.cm-event \{ contain-intrinsic-block-size: auto ([\d.]+)rem; \} \}", sup)
        self.assertEqual(sizes, [("40", "20"), ("64", "23"), ("72", "17"), ("96", "15"), ("120", "13.5")])
        self.assertIn(".cm-event:has(.cm-menu[open]) { content-visibility: visible; }", sup)
        self.assertIn("@media print { .cm-event { content-visibility: visible; } }", css)
        # (nowhere else on a card: the guard must hold for every content-visibility: auto on a card; since round 35 the
        # /photos/ covers' year blocks have their own, under @supports (overflow-clip-margin) — tests/test_r35_ev_weight.py)
        self.assertEqual(css.count("content-visibility: auto"), 2)
        self.assertEqual(css.count(".cm-cover-album { content-visibility: auto;"), 1)


class Calendar(unittest.TestCase):
    def test_past_days_and_ended_entries_are_faint_not_see_through(self):
        css = flat(CSS)
        self.assertNotRegex(css, r"\.cm-cal-d\.is-past \{[^}]*opacity")
        self.assertNotRegex(css, r"\.cm-cal-list > li\.is-over \{[^}]*opacity")
        self.assertIn(".cm-cal-d.is-past :is(.cm-cal-link, .cm-cal-day, .cm-cal-mon, .cm-cal-more) { color: var(--c-faint); }", css)
        self.assertIn(".cm-cal-d.is-past .cm-cal-dot { opacity: 0.45; }", css)
        self.assertIn(".cm-cal-list > li.is-over :is(.cm-cal-time, .cm-cal-ev, .cm-cal-wk) { color: var(--c-faint); }", css)
        self.assertIn(".cm-cal-list > li.is-over > .cm-cal-dot { opacity: 0.55; }", css)
        # the faint ink on the card (a .card is the surface colour) — small text: 4.5:1, in every theme
        for name, t in themes().items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast(t["faint"], t["surface"]), 4.5, (t["faint"], t["surface"]))


class Slideshow(unittest.TestCase):
    def test_previous_and_next_are_on_the_screen_at_every_width(self):
        css = flat(CSS)
        self.assertIn("@media (width < 769px) { .glightbox-container.cm-lightbox :is(.gprev, .gnext) { top: 45%; } }", css)
        # unlayered (after the components layer has closed), as GLightbox's own rule (top: -100%) is: a layered rule
        # would lose to it whatever its selector
        self.assertGreater(CSS.index(".glightbox-container.cm-lightbox :is(.gprev"), CSS.index("(unlayered) rules that must beat utilities"))

    def test_its_buttons_have_a_white_keyboard_ring(self):
        self.assertIn(".glightbox-container.cm-lightbox .gbtn:is(.focused, :focus-visible) { outline: 3px solid #fff; outline-offset: 2px; }",
                      flat(CSS))


# --------------------------------------------------------------------------- the slideshow's keyboard, in Node.js
# A stand-in GLightbox that behaves as 3.3.1 does where committee.js meets it: a click on a photo opens it (its
# lightboxHTML, one .gslide per photo, the one shown marked .current — with no animation, after
# afterSlideChange has run), onOpen after that; goToSlide → afterSlideChange; close → the dialog removed, then
# onClose. Its own handlers call instance.close(), as GLightbox's touch, Escape and Close handlers do.
LB_JS = PAGE_JS + r"""
const html = `<div id="cm-lb-i18n" data-label="Photos" data-close="Close" data-prev="Previous" data-next="Next"></div>
  <p><a id="p0" class="cm-photo glightbox-cm" href="https://example.test/0.jpg" data-gallery="g">0</a>
     <a id="p1" class="cm-photo glightbox-cm" href="https://example.test/1.jpg" data-gallery="g">1</a>
     <a id="p2" class="cm-photo glightbox-cm" href="https://example.test/2.jpg" data-gallery="g">2</a>
     <button id="full" type="button" data-cm-open-gallery="g">Full screen</button></p>`;
const res = {};
for (const reduced of [false, true]) {
  let opts = null, lb = null;
  const GLightbox = (o) => {
    opts = o;
    lb = {
      index: 0, lightboxOpen: false,
      open(node) {
        const doc = p.doc, links = [...doc.querySelectorAll(o.selector)];
        this.index = Math.max(0, links.indexOf(node));
        doc.body.insertAdjacentHTML("beforeend", o.lightboxHTML.replace(/\{\w+SVG\}/g, ""));
        doc.getElementById("glightbox-slider").innerHTML = links.map(() => '<div class="gslide"><h4 class="gslide-title"></h4></div>').join("");
        this.lightboxOpen = true;
        o.afterSlideChange.call(this, {}, { index: this.index });
        doc.querySelectorAll(".gslide")[this.index].classList.add("current");
        o.onOpen();
      },
      goToSlide(i) {
        const s = p.doc.querySelectorAll(".gslide");
        s[this.index].classList.remove("current");
        this.index = i;
        o.afterSlideChange.call(this, {}, { index: i });
        s[i].classList.add("current");
      },
      close() {
        if (!this.lightboxOpen) return;
        p.doc.getElementById("glightbox-body").remove();
        this.lightboxOpen = false;
        o.onClose();
      },
      swipeDown() { this.close(); this.afterSwipe = this.lightboxOpen; },   // (what its touch handler does next)
    };
    p.doc.querySelectorAll(o.selector).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); lb.open(a); }));
    return lb;
  };
  const p = page({ html, scripts: ["src/assets/js/committee.js"], globals: { GV: { reducedMotion: () => reduced }, GLightbox } });
  await p.ready();
  const $ = (s) => p.doc.querySelector(s), active = () => { const a = p.doc.activeElement; return a ? (a.id || a.tagName) : null; };
  const slides = () => [...p.doc.querySelectorAll(".gslide")].map((s) => (s.hasAttribute("inert") && s.getAttribute("aria-hidden") === "true" ? "hidden" : "shown"));
  const r = {};
  // a photo, clicked (a trusted click: a person's click, or Enter on the focused link)
  $("#p1").focus();
  p.click($("#p1"), { isTrusted: true });
  r.openFocus = active(); r.openSlides = slides();
  lb.goToSlide(2); r.nextSlides = slides();
  lb.close(); r.closedAtOnce = !$("#glightbox-body");
  await p.tick(1);
  r.closeFocus = active();
  // "Full screen": a trusted click on the button, which opens its first photo with a click of its own (untrusted)
  $("#full").focus();
  p.click($("#full"), { isTrusted: true });
  r.fullOpen = [active(), lb.index];
  lb.close(); await p.tick(1);
  r.fullClose = active();
  // a swipe down: GLightbox's touch handler goes on after it calls close()
  p.click($("#p0"), { isTrusted: true });
  lb.swipeDown(); r.openDuringSwipe = lb.afterSwipe;
  await p.tick(1);
  r.swipeClosed = !$("#glightbox-body"); r.swipeFocus = active();
  // opened by a script only (no click a person made): nothing to go back to — the focus is left alone
  $("#p2").focus(); $("#p2").blur();
  lb.open($("#p0")); lb.close(); await p.tick(1);
  r.scriptOnly = active();
  r.errors = p.errors.map(String);
  res[reduced ? "reduced" : "motion"] = r;
}
out(res);
"""


class SlideshowKeyboard(unittest.TestCase):
    r = None

    def setUp(self):
        if SlideshowKeyboard.r is None:
            SlideshowKeyboard.r = run_js(self, LB_JS, needs_modules=False, timeout=120)

    def test_the_focus_goes_in_and_comes_back(self):
        for name, r in self.r.items():
            with self.subTest(motion=name):
                self.assertEqual(r["openFocus"], "glightbox-body", "into the dialog, not left behind it on the photo")
                self.assertEqual(r["closeFocus"], "p1", "back on the photo that opened it")
                self.assertEqual(r["fullOpen"], ["glightbox-body", 0])
                self.assertEqual(r["fullClose"], "full", "back on Full screen, not on the photo its own click opened")
                self.assertEqual(r["swipeFocus"], "p0")
                self.assertEqual(r["scriptOnly"], "BODY", "no stale opener")
                self.assertEqual(r["errors"], [])

    def test_only_the_slide_on_show_is_there_for_a_screen_reader(self):
        for name, r in self.r.items():
            with self.subTest(motion=name):
                self.assertEqual(r["openSlides"], ["hidden", "shown", "hidden"])
                self.assertEqual(r["nextSlides"], ["hidden", "hidden", "shown"])

    def test_with_motion_reduced_closing_waits_for_the_handler_to_finish(self):
        self.assertTrue(self.r["motion"]["closedAtOnce"])
        self.assertFalse(self.r["motion"]["openDuringSwipe"])
        self.assertFalse(self.r["reduced"]["closedAtOnce"], "one moment later")
        self.assertTrue(self.r["reduced"]["openDuringSwipe"], "still open while the touch handler finishes")
        self.assertTrue(self.r["reduced"]["swipeClosed"])


# --------------------------------------------------------------------------- x-ignore, in the templates and built
class XIgnoreTemplates(unittest.TestCase):
    def test_only_the_directive_free_wrappers(self):
        ev = read("src", "pages", "events.njk")
        self.assertIn('<article class="card cm-event ev-accent ev-tone-{{ kind }}" x-ignore>', ev)
        self.assertIn('x-show="show($el)">\n        <article', ev, "the <li> keeps its x-show (no x-ignore on it)")
        for tag in re.findall(r"<(?:article|li|section)\b[^>]*>", ev):
            if "x-ignore" in tag:
                self.assertNotRegex(tag, r'\s(x-(?!ignore)[\w:.-]+|@[\w:.-]+|:[\w:.-]+)=', tag)
        self.assertEqual(ev.count("x-ignore>"), 1)
        ph = read("src", "pages", "photos.njk")
        self.assertIn('<ul class="cm-cover-grid" x-ignore>', ph)
        self.assertEqual(ph.count("x-ignore>"), 1)


class _Scan(HTMLParser):
    """Each outermost [x-ignore] element: its tag + class, how many elements it holds, the Alpine directives in it;
    and any x-ignore element that has a directive of its own (Alpine would skip that too)."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.inside, self.wrappers, self.own = [], 0, [], []

    @staticmethod
    def directive(n: str) -> bool:
        return n.startswith(("x-", "@", ":"))

    def handle_starttag(self, tag, attrs):
        names = [a for a, _ in attrs]
        if self.inside:
            self.wrappers[-1]["elements"] += 1
            self.wrappers[-1]["directives"] += [f"<{tag} {n}>" for n in names if self.directive(n)]
        here = "x-ignore" in names
        if here:
            self.own += [f"<{tag} {n}>" for n in names if self.directive(n) and n != "x-ignore"]
            if not self.inside:
                self.wrappers.append({"what": tag + "." + (dict(attrs).get("class") or "").split(" ")[0], "elements": 0, "directives": []})
        if tag in self.VOID:
            return
        self.stack.append((tag, here))
        self.inside += here

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID and self.stack and self.stack[-1][0] == tag:
            self.inside -= self.stack.pop()[1]

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.inside -= sum(h for _t, h in self.stack[i:])
                del self.stack[i:]
                return


# /events/ and /photos/ as the site builds them (only those two templates, the site's own data)
PAGES_JS = r"""
process.env.ONLY = "events.njk,photos.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r33-cm-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
  out(Object.fromEntries((await elev.toJSON()).filter((p) => /\/(events|photos)\/$/.test(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


class XIgnoreBuilt(unittest.TestCase):
    pages = None

    def setUp(self):
        if XIgnoreBuilt.pages is None:
            XIgnoreBuilt.pages = run_js(self, PAGES_JS, timeout=900)

    def test_no_directive_inside_an_x_ignore(self):
        self.assertEqual(sorted(self.pages), ["/es/events/", "/es/photos/", "/events/", "/photos/"])
        for url, page in self.pages.items():
            with self.subTest(url=url):
                s = _Scan()
                s.feed(page)
                kinds = {w["what"] for w in s.wrappers}
                self.assertEqual(kinds, {"article.card"} if "events" in url else {"ul.cm-cover-grid"}, url)
                self.assertGreater(len(s.wrappers), 0)
                self.assertGreater(sum(w["elements"] for w in s.wrappers), 10 * len(s.wrappers), "they hold the bulk of the page")
                self.assertEqual([d for w in s.wrappers for d in w["directives"]], [], "a directive Alpine would never see")
                self.assertEqual(s.own, [])
                if "events" in url:
                    # the cards Alpine runs (the Grapevine Meeting's countdown: x-data) are not skipped
                    self.assertRegex(page, r'<article id="ev-next-gvm" class="card ev-accent ev-tone-other cm-event" x-data="cmMeeting\(')
                    self.assertNotRegex(page, r'<li [^>]*x-ignore')


if __name__ == "__main__":
    unittest.main()
