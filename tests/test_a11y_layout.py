"""Accessibility and layout rules that axe cannot see — static checks of the CSS and templates, with the
contrast worked out from the theme tokens, and the What's New filter bar's script run in Node.js (the measured
browser checks — focus-ring contrast at the top of the page, a focused link under the sticky bar, 150% text on a
360px phone, print, Windows High Contrast — are the QA scripts' job).

  * Focus ring   — in the site header the ring takes the header's text colour (white over the hero, ink once
                   solid): ≥ 3:1 on both, in light, dark and high contrast (the blue ring was ≈ 1.6:1 on the hero).
  * Fields       — text boxes and dropdowns (main.css input, the library / search box, the booth and presenter
                   drawers) have an edge of ≥ 3:1 (--c-field) in every theme; --c-line (1.3:1) is a divider only.
  * Switch       — the pages' on / off switches (.cm-switch) are drawn like the menu's Dark mode switch: a
                   --c-faint ring and knob (≥ 3:1) when off, system colours in Windows High Contrast.
  * Booth        — "Tap for full screen & sound" is dark on gold (≥ 4.5:1), not the inherited near-white; the
                   About page's "How to use it" steps never push a phone page sideways.
  * What's New   — html's scroll-padding-top adds the sticky filter bar's measured height (community.js
                   whatsNew.watchBar → --wn-bar-h), so a focused link never lands under it; on a desktop the
                   chips wrap instead of hiding under the fade; at 130 %+ text the bar stops sticking there.
  * Header ARIA  — the dropdowns are disclosure buttons (aria-expanded + aria-controls, no aria-haspopup); the
                   theme button is a "Dark mode" toggle (aria-pressed); accessible names start with the words
                   shown ("ES …", "Show post here …").
  * Landmarks    — no <aside> inside a named section or an article (axe landmark-complementary-is-top-level).
  * Smaller      — of the footer only the copyright / reprint notice prints; no hero art in Windows High
                   Contrast; the digest's "also on YouTube" link is ≥ 24px tall; Instagram pictures don't repeat
                   the caption printed under them; the Texas archive rows render only near the screen
                   (content-visibility), all of them in print.

    python -m unittest tests.test_a11y_layout -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def contrast(a: str, b: str) -> float:
    def lum(h: str) -> float:
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def tokens(block: str) -> dict:
    return {m.group(1): m.group(2).lower() for m in re.finditer(r"--c-([\w-]+):\s*(#[0-9a-fA-F]{6})\b", block)}


def block(css: str, selector: str, indent: str = "") -> str:
    m = re.search("^" + indent + re.escape(selector) + r" \{(.*?)^" + indent + r"\}", css, re.S | re.M)
    assert m, selector
    return m.group(1)


def themes() -> dict:
    """The colour tokens as each theme resolves them (the later blocks override the earlier ones, as on the page)."""
    css = read("src", "assets", "css", "main.css")
    light = tokens(block(css, ":root"))
    dark = {**light, **tokens(block(css, ':root[data-theme="dark"]'))}
    hc = {**light, **tokens(block(css, ':root[data-contrast="high"]'))}
    hcdark = {**dark, **hc, **tokens(block(css, ':root[data-contrast="high"][data-theme="dark"]'))}
    return {"light": light, "dark": dark, "hc": hc, "hcdark": hcdark}


class FocusRing(unittest.TestCase):
    def test_the_header_ring_takes_the_header_text_colour(self):
        css = read("src", "assets", "css", "main.css")
        self.assertIn(".site-header :focus-visible { outline-color: currentColor; }", css)
        header = read("src", "_includes", "partials", "header.njk")
        tag = re.search(r'<header x-data="siteHeader"(.*?)>', header, re.S).group(1)
        self.assertIn("text-ink!", tag)       # solid (scrolled, or a page without a hero)
        self.assertIn("text-white", tag)      # over the hero
        # white over the hero's gradient (before its darkening scrim): ≥ 3:1 at its lightest stop
        hero = re.search(r"background-image: linear-gradient\(135deg,([^;]*)\);", css).group(1)
        for stop in re.findall(r"#[0-9a-f]{6}", hero):
            with self.subTest(hero=stop):
                self.assertGreaterEqual(contrast("#ffffff", stop), 3)
        # ink on the solid header (surface) in every theme
        for name, t in themes().items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast(t["ink"], t["surface"]), 3)


class Fields(unittest.TestCase):
    def test_the_field_edge_is_3_to_1_in_every_theme(self):
        for name, t in themes().items():
            for bg in ("surface", "surface-2", "paper"):
                with self.subTest(theme=name, bg=bg):
                    self.assertGreaterEqual(contrast(t["field"], t[bg]), 3, (t["field"], t[bg]))
        # (why a token of its own: the soft divider is far below that in the two normal themes)
        for name in ("light", "dark"):
            with self.subTest(theme=name, line="a divider, not a field edge"):
                self.assertLess(contrast(themes()[name]["line"], themes()[name]["surface"]), 3)

    def test_print_keeps_a_field_edge(self):
        css = read("src", "assets", "css", "main.css")
        for sel in (':root[data-theme="dark"]', ':root[data-theme="dark"][data-contrast="high"]'):
            t = tokens(block(css, sel, "  "))
            with self.subTest(print=sel):
                self.assertGreaterEqual(contrast(t["field"], t["surface"]), 3)

    def test_the_boxes_use_it(self):
        css = read("src", "assets", "css", "main.css")
        util = re.search(r"@utility input \{([^}]*)\}", css).group(1)
        self.assertIn("border-field", util)
        self.assertNotIn("border-line", util)
        self.assertIn("--color-field: var(--c-field);", css)
        lib = read("src", "assets", "css", "areas", "library.css")
        self.assertIn("border-radius: 1rem; border: 1px solid var(--c-field);", lib)
        for area, cls in (("booth", ".gvb-input {"), ("presentations", ".gvp-input {")):
            rule = read("src", "assets", "css", "areas", f"{area}.css")
            rule = rule[rule.index(cls):]
            rule = rule[:rule.index("}")]
            edge = re.search(r"border: 1px solid (#[0-9a-f]{6})", rule).group(1)
            with self.subTest(area=area):
                self.assertGreaterEqual(contrast(edge, "#ffffff"), 3)


class Switch(unittest.TestCase):
    def test_the_page_switch_is_the_menu_switch(self):
        css = read("src", "assets", "css", "main.css")
        for bit in (".site-switch, .cm-switch {", ".cm-switch { appearance: none; -webkit-appearance: none; margin: 0; cursor: pointer; }",
                    ".site-switch::after, .cm-switch::after {",
                    '[aria-checked="true"] > .site-switch, .cm-switch:checked { border-color: var(--c-gv); background: var(--c-gv); }',
                    '[aria-checked="true"] > .site-switch::after, .cm-switch:checked::after { transform: translateX(1.25rem);'):
            self.assertIn(bit, css)
        forced = css[css.index("@media (forced-colors: active) {\n  .site-switch"):]
        forced = forced[:forced.index("\n}")]
        self.assertIn(".site-switch, .cm-switch { border-color: ButtonText; }", forced)
        self.assertIn(".site-switch::after, .cm-switch::after { background: ButtonText; forced-color-adjust: none; }", forced)
        self.assertIn(".cm-switch:checked { border-color: Highlight; background: Highlight; forced-color-adjust: none; }", forced)
        # the old soft track is gone from the committee area
        self.assertNotIn(".cm-switch {", read("src", "assets", "css", "areas", "committee.css"))
        # off: the --c-faint ring and knob stand out on the page and on the track
        for name, t in themes().items():
            for bg in ("paper", "surface"):
                with self.subTest(theme=name, bg=bg):
                    self.assertGreaterEqual(contrast(t["faint"], t[bg]), 3)

    def test_both_pages_use_it(self):
        for page in ("events", "meetings"):
            with self.subTest(page=page):
                self.assertRegex(read("src", "pages", f"{page}.njk"), r'<input type="checkbox" class="cm-switch" x-model="\w+">')


class Booth(unittest.TestCase):
    def test_the_tap_chip_is_dark_on_gold(self):
        css = read("src", "assets", "css", "areas", "booth.css")
        # ".gvb-screen button" (0,1,1) sets font and colour to inherit: the chip's own rule must be stronger
        self.assertIn(".gvb-screen button { font: inherit; color: inherit; cursor: pointer; }", css)
        self.assertIsNone(re.search(r"^\.gvb-tapchip\b", css, re.M), "a bare .gvb-tapchip rule loses to .gvb-screen button")
        rule = re.search(r"^\.gvb-screen \.gvb-tapchip \{(.*?)\}", css, re.S | re.M).group(1)
        ink = re.search(r"[^-]color: (#[0-9a-f]{6})", rule).group(1)
        self.assertIn("background: var(--gold)", rule)
        self.assertIn("font-size: calc(2.6 * var(--u))", rule)
        gold = re.search(r"--gold: (#[0-9a-f]{6})", css).group(1)
        self.assertGreaterEqual(contrast(ink, gold), 4.5)

    def test_the_steps_fit_a_phone_at_large_text(self):
        css = read("src", "assets", "css", "areas", "booth.css")
        self.assertIn(".gvb-how-steps { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0.75rem; }", css)
        self.assertIn(".gvb-how-steps > li > :last-child { min-width: 0; overflow-wrap: anywhere; }", css)
        mac = read("src", "_includes", "macros", "booth.njk")
        self.assertIn('{{ ("booth.how_" + n) | t(lang) | escape | replace("/", "/<wbr>") | safe }}', mac)


class WhatsNewBar(unittest.TestCase):
    def test_the_css(self):
        css = read("src", "assets", "css", "areas", "community.css")
        self.assertIn(":root:has(.cm-chipbar) { scroll-padding-top: calc(var(--header-h) + var(--wn-bar-h, 0px) + 1.5rem); }", css)
        self.assertNotIn("scroll-margin-top: 4.5rem", css)          # it would add up with the padding
        desk = css[css.index("@media (width >= 64rem) {\n  .cm-chipbar"):]
        desk = desk[:desk.index("\n}")]
        self.assertIn(".cm-chipbar .cm-chips { flex-wrap: wrap; overflow: visible; padding-right: 0.25rem; -webkit-mask-image: none; mask-image: none; }", desk)
        self.assertIn(':root:is([data-text="130"], [data-text="150"], [data-spacing="relaxed"]) .cm-chipbar { position: static; }', desk)
        self.assertIn("@media (80rem <= width < 96rem) { .cm-chipbar .cm-chips { gap: 0.25rem; } .cm-chipbar .chip { padding-inline: 0.5rem; } }", css)
        self.assertIn("this.watchBar();", read("src", "assets", "js", "community.js"))

    def run_bar(self, script: str):
        return run_js(self, r"""
import vm from "node:vm";
const vars = {}, docL = {}, winL = {}, reg = {};
let ro = null;
const html = { style: { setProperty: (k, v) => { vars[k] = v; } } };
const box = (left, right, top, height, pos) => ({ pos, rect: { left, right, top, height, bottom: top + height } });
const make = (bar, feed) => ({ querySelector: (s) => (s === ".cm-chipbar" ? bar && Object.assign(bar, { getBoundingClientRect: () => bar.rect })
                                                       : s === ".cm-wn-feed" ? feed && Object.assign(feed, { getBoundingClientRect: () => feed.rect }) : null) });
const ctx = { console, JSON, Math, Object, Array, String, Number, RegExp, Intl, Date, URL,
  document: { readyState: "loading", documentElement: html, addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); } },
  location: { search: "" }, history: { replaceState() {} },
  getComputedStyle: (e) => ({ position: e.pos }),
  addEventListener: (t, fn) => { (winL[t] ||= []).push(fn); } };
ctx.window = ctx;
if (!input.noRO) ctx.ResizeObserver = class { constructor(cb) { ro = { cb, el: null }; } observe(el) { ro.el = el; } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync("src/assets/js/community.js", "utf8"), ctx);
ctx.Alpine = { data: (n, fn) => { reg[n] = fn; } };
for (const fn of docL["alpine:init"] || []) fn();
const comp = (bar, feed) => { const c = reg.whatsNew({}); c.$el = make(bar, feed); c.$root = { getAttribute: () => "{n}" }; return c; };
const resize = () => { for (const fn of winL.resize || []) fn(); };
// the next frame (requestAnimationFrame): run by hand — frame()
const frames = [];
ctx.requestAnimationFrame = (fn) => frames.push(fn);
const frame = () => { while (frames.length) frames.shift()(); };
const prefs = () => { for (const fn of winL["gvlv:prefs"] || []) fn({ detail: {} }); };   // a reading setting changed
""" + script, data={"noRO": "noRO" in script}, needs_modules=False, timeout=60)

    def test_the_bar_height_while_it_covers_the_feed(self):
        r = self.run_bar(r"""
const bar = box(80, 880, 64, 56, "sticky"), feed = box(80, 880, 140, 4000, "static");
const c = comp(bar, feed);
c.$el.querySelectorAll = () => [];
c.init();                                         // init measures it
const one = vars["--wn-bar-h"];
bar.rect = { ...bar.rect, height: 110.4 };        // the chips wrap onto a second row (larger text)
ro.cb();
const two = vars["--wn-bar-h"];
bar.pos = "static"; resize();                     // a window under 40rem tall: the bar scrolls away
const short = vars["--wn-bar-h"];
bar.pos = "sticky"; resize();
const back = vars["--wn-bar-h"];
out({ one, two, short, back, observed: ro.el === bar, resizeListeners: (winL.resize || []).length });
""")
        self.assertEqual(r["one"], "56px")
        self.assertEqual(r["two"], "111px")            # rounded up: never a pixel short
        self.assertEqual(r["short"], "0px")
        self.assertEqual(r["back"], "111px")
        self.assertTrue(r["observed"])
        self.assertEqual(r["resizeListeners"], 1)

    def test_measured_again_when_a_reading_setting_changes(self):
        # Round-7 review: from 64rem the bar stays in place at larger text or relaxed spacing, and is sticky otherwise —
        # turning relaxed spacing off in the Aa panel made it sticky at the same size, so neither the ResizeObserver nor
        # a window resize measured it again: --wn-bar-h stayed 0px and keyboard focus could land under the bar
        r = self.run_bar(r"""
const bar = box(80, 880, 64, 56, "static"), feed = box(80, 880, 140, 4000, "static");
comp(bar, feed).watchBar();                       // relaxed spacing: the bar stays in place
const relaxed = vars["--wn-bar-h"];
bar.pos = "sticky";                               // relaxed spacing off: sticky, the same size (no resize)
prefs();
const sameFrame = vars["--wn-bar-h"];             // (measured once the new styles apply: the next frame)
frame();
const normal = vars["--wn-bar-h"];
bar.pos = "static"; prefs(); frame();             // 130 % text: in place again
out({ relaxed, sameFrame, normal, larger: vars["--wn-bar-h"], listeners: (winL["gvlv:prefs"] || []).length });
""")
        self.assertEqual(r, {"relaxed": "0px", "sameFrame": "0px", "normal": "56px", "larger": "0px", "listeners": 1})

    def test_nothing_to_leave_room_for(self):
        r = self.run_bar(r"""
// the three-column layout: the bar is the left column, beside the feed (sticky, but over nothing)
comp(box(80, 304, 88, 420, "sticky"), box(352, 1100, 88, 4000, "static")).watchBar();
const side = vars["--wn-bar-h"];
// hidden (no JavaScript-only bar on screen: display none → no height)
comp(box(0, 0, 0, 0, "sticky"), box(80, 880, 140, 4000, "static")).watchBar();
const hidden = vars["--wn-bar-h"];
delete vars["--wn-bar-h"];
comp(null, box(80, 880, 140, 4000, "static")).watchBar();   // an empty feed: no bar at all
out({ side, hidden, none: vars["--wn-bar-h"] === undefined });
""")
        self.assertEqual(r["side"], "0px")
        self.assertEqual(r["hidden"], "0px")
        self.assertTrue(r["none"])

    def test_without_resize_observer(self):
        r = self.run_bar(r"""
// noRO: an old browser — measured once, and again on every window resize
const bar = box(0, 390, 64, 64, "sticky"), feed = box(16, 374, 150, 4000, "static");
comp(bar, feed).watchBar();
const first = vars["--wn-bar-h"];
bar.rect = { ...bar.rect, height: 96 }; resize();
out({ first, after: vars["--wn-bar-h"], ro: ro === null });
""")
        self.assertEqual(r, {"first": "64px", "after": "96px", "ro": True})


class HeaderAria(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = read("src", "_includes", "partials", "header.njk")
        cls.common = json.loads(read("src", "_i18n", "common.json"))

    def test_dropdowns_are_disclosures(self):
        h = self.header
        self.assertNotIn('aria-haspopup="true"', h)
        self.assertNotIn('aria-haspopup="menu"', h)
        self.assertIn('{%- set menuId = "nav-menu-" + loop.index %}', h)
        btn = re.search(r'<button type="button" x-ref="btn"([^>]*)>', h).group(1)
        for bit in ('aria-expanded="false"', ':aria-expanded="open"', 'aria-controls="{{ menuId }}"', '@click="open = !open"'):
            self.assertIn(bit, btn)
        self.assertIn('<div id="{{ menuId }}" x-show="open" x-cloak', h)
        # the keyboard behaviour stays with app.js navMenu (Escape back to the button, tabbing out closes)
        app = read("src", "assets", "js", "app.js")
        self.assertIn('Alpine.data("navMenu"', app)
        self.assertIn("this.$refs.btn.focus()", app)

    def test_the_theme_button_is_a_dark_mode_toggle(self):
        btn = re.search(r'<button type="button" @click="toggleTheme\(\)" class="hidden[^"]*"([^>]*)>', self.header, re.S).group(1)
        self.assertIn("""aria-label="{{ 'nav.theme_dark' | t(L) }}\"""", btn)
        self.assertIn('aria-pressed="false"', btn)
        self.assertIn(""":aria-pressed="(theme === 'dark').toString()\"""", btn)
        self.assertNotIn("nav.theme_aria", self.common)        # the old "Switch light / dark mode" name

    def test_names_start_with_the_visible_words(self):
        # the header's language button shows "ES" on English pages, "EN" on Spanish ones
        self.assertIn('<span>{{ "ES" if L == "en" else "EN" }}</span>', self.header)
        self.assertIn("""aria-label="{{ 'nav.switch_lang_aria' | t(L) }}\"""", self.header)
        name = self.common["nav.switch_lang_aria"]
        self.assertTrue(name["en"].startswith("ES"), name["en"])
        self.assertTrue(name["es"].startswith("EN"), name["es"])
        # Instagram's "Show post here"
        media = json.loads(read("src", "_i18n", "media.json"))
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertTrue(media["media.ig_load_embed_aria"][lang].startswith(media["media.ig_load_embed"][lang]))
        ig = read("src", "pages", "instagram.njk")
        self.assertIn("""aria-label="{{ 'media.ig_load_embed_aria' | t(lang) }}">{% micon "square-play", "size-4" %} {{ "media.ig_load_embed" | t(lang) }}""", ig)


class Landmarks(unittest.TestCase):
    """axe's landmark-complementary-is-top-level: an <aside> inside a named <section> (a region), an <article>
    or another landmark is a landmark within a landmark — the inner ones are <div>s or named <section>s."""

    TAG = re.compile(r"<(/?)(section|article|aside|main|nav|header|footer|form)\b([^>]*)>", re.I)

    def nested(self, src: str) -> list:
        src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
        stack, found = [], []
        for m in self.TAG.finditer(src):
            close, tag, attrs = m.group(1), m.group(2).lower(), m.group(3)
            if close:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == tag:
                        del stack[i:]
                        break
                continue
            if tag == "aside" and [t for t, named in stack if (t == "section" and named) or t in ("article", "aside", "nav", "header", "footer", "form")]:
                found.append(attrs.strip()[:60])
            stack.append((tag, bool(re.search(r"aria-label(ledby)?=", attrs))))
        return found

    def test_the_check_finds_one(self):
        self.assertEqual(len(self.nested('<section aria-label="x"><div><aside class="a">…</aside></div></section>')), 1)
        self.assertEqual(self.nested('<main><aside class="a"></aside></main><section><aside></aside></section>'), [])

    def test_no_aside_inside_another_landmark(self):
        files = sorted(ROOT.joinpath("src", "pages").glob("*.njk")) + sorted(ROOT.joinpath("src", "_includes").rglob("*.njk"))
        self.assertGreater(len(files), 40)
        for f in files:
            with self.subTest(file=f.name):
                self.assertEqual(self.nested(f.read_text(encoding="utf-8")), [])

    def test_the_inner_ones_kept_their_classes(self):
        self.assertIn('<div class="cm-ann-side">', read("src", "pages", "bulletin.njk"))
        self.assertIn('<div class="sticky-aside">', read("src", "pages", "contribute.njk"))
        self.assertIn('<div class="sticky-aside space-y-5">', read("src", "pages", "gvr.njk"))
        self.assertIn("""<section id="lib-facets" class="lib-facets hidden lg:block" aria-label="{{ 'library.filters' | t(lang) }}">""",
                      read("src", "pages", "library.njk"))
        self.assertIn('<div class="mt-8 flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface-2', read("src", "pages", "read.njk"))


class Smaller(unittest.TestCase):
    def test_only_the_footer_notice_prints(self):
        css = read("src", "assets", "css", "main.css")
        prints = [css[m.start():css.find("\n}", m.start())] for m in re.finditer(r"@media print \{", css)]
        footer = [p for p in prints if ".site-footer {" in p]
        self.assertEqual(len(footer), 1)
        rules = footer[0]
        # the link lists, buttons, "Last updated" and the disclaimer go; the copyright / reprint notice stays
        self.assertIn(".site-footer-main, .site-footer :has(> .site-footer-notice) > :not(.site-footer-notice) { display: none !important; }", rules)
        self.assertNotRegex(rules, r"\.site-footer \{[^}]*display: none")
        self.assertNotRegex(rules, r"\.site-footer-notice \{[^}]*display: none")
        self.assertIn(".site-footer { margin-top: 1.25rem !important; border: 0 !important; background: none !important; }", rules)
        tpl = read("src", "_includes", "partials", "footer.njk")
        self.assertRegex(tpl, r'<footer class="site-footer [^"]*"')
        self.assertRegex(tpl, r'<p class="site-footer-notice [^"]*">\{\{ "footer\.reprints" \| t\(L\) \}\}</p>')
        self.assertEqual(tpl.count("site-footer-notice"), 1)
        # the Accessibility page says so
        pr = json.loads(read("src", "_i18n", "access.json"))["access.pr_page2"]
        self.assertIn("footer (all but its copyright notice)", pr["en"])
        self.assertIn("pie de página (salvo su aviso de derechos de autor)", pr["es"])

    def test_no_hero_art_in_windows_high_contrast(self):
        self.assertIn("@media (forced-colors: active) { .gv-hero-canvas { display: none !important; } }", read("src", "assets", "css", "main.css"))

    def test_the_hidden_hero_art_draws_nothing(self):
        # hero-canvas.js on a pretend page (tests/fakedom.py) with a 2D context that counts what is drawn: in forced
        # colours (the canvas is hidden) nothing — no animation loop, no still picture —; switched off while the page
        # is open, the lights run; switched on again, they stop
        from fakedom import PAGE_JS
        r = run_js(self, PAGE_JS + r"""
          const forced = { matches: true, fns: [] };
          const mm = (q) => /forced-colors/.test(q)
            ? { get matches() { return forced.matches; }, media: q, addEventListener: (t, f) => forced.fns.push(f), removeEventListener() {} }
            : { matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} };
          const p = page({ html: '<section data-gv-hero><canvas class="gv-hero-canvas"></canvas><h1>Hi</h1></section>', scripts: [] });
          let drawn = 0;
          // (setTransform only sizes the canvas: everything else draws)
          const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (...a) => { if (k !== "setTransform") drawn += 1; return new Proxy({}, { get: () => () => {} }); }),
                                        set: (t, k, v) => { t[k] = v; return true; } });
          p.win.matchMedia = mm;
          p.win.Element.prototype.getContext = () => ctx2d;
          const hero = p.$("[data-gv-hero]");
          Object.defineProperty(hero, "offsetWidth", { value: 900 });
          Object.defineProperty(hero, "offsetHeight", { value: 360 });
          vm.runInContext(fs.readFileSync("src/assets/js/hero-canvas.js", "utf8"), p.win, { filename: "hero-canvas.js" });
          await p.ready();
          await p.tick(3000);
          const res = { forced: drawn, art: p.win.GVHeroArt.arts.length };
          forced.matches = false; forced.fns.forEach((f) => f({ matches: false }));
          await p.tick(3000);
          res.off = drawn;
          forced.matches = true; forced.fns.forEach((f) => f({ matches: true }));
          const at = drawn;
          await p.tick(5000);
          res.onAgain = drawn - at;
          res.errors = p.errors.map(String);
          out(res);""", needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["art"], 1)
        self.assertEqual(r["forced"], 0, "hidden in forced colours: nothing drawn")
        self.assertGreater(r["off"], 1000, "switched off: the lights run")
        self.assertEqual(r["onAgain"], 0, "switched on again: the loop stops")

    def test_the_digest_youtube_link_is_24px_tall(self):
        dg = read("src", "pages", "digest.njk")
        link = re.search(r'\{% if it\._twin %\}<span class="whitespace-nowrap"><a class="([^"]*)"', dg).group(1).split()
        self.assertTrue({"inline-flex", "min-h-6", "items-center"} <= set(link), link)

    def test_instagram_alt_text_does_not_repeat_the_caption(self):
        ig = read("src", "pages", "instagram.njk")
        img = re.search(r'<img src="\{\{ img \}\}" alt="([^"]*)" width="480"', ig).group(1)
        self.assertEqual(img, "{{ '' if cap else fromLabel }}")
        self.assertIn('{% if img and cap %}<p class="line-clamp-3', ig)       # the caption is printed under the picture
        self.assertIn('<span class="sr-only">{{ "media.ig_view" | t(lang) }} ({{ "common.external" | t(lang) }})</span>', ig)

    def test_texas_archive_rows_render_near_the_screen(self):
        css = read("src", "assets", "css", "areas", "published.css")
        self.assertIn(".pw-arc-row { content-visibility: auto; contain-intrinsic-block-size: auto 8.5rem; }", css)
        pr = css[css.index("@media print {"):]
        self.assertIn(".pw-arc-row { break-inside: avoid; content-visibility: visible; }", pr)


if __name__ == "__main__":
    unittest.main()
