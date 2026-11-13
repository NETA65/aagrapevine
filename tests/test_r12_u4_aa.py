"""Round 12, the "Aa" panel's new choices: video captions for every YouTube player on the site, and read aloud's
reading speed, Previous / Next paragraph and "read from where I am" (src/assets/js/app.js GV.prefs, GV.ytCaptions,
GV.tts; partials/comfort-panel.njk; the Accessibility page's one-tap captions button; media.js's video dialog).

  * Strings   — every new comfort.* / access.* key in English AND Spanish; the wording promises nothing YouTube may
                not do (it "doesn't always follow" the choice; automatic captions can be wrong).
  * Prefs     — gvlv-prefs gains rate ("slower" | "normal" | "faster", Normal by default) and captions ("off" | "on",
                Off by default): a stored value that is not one of them is the default, Reset brings both back, and
                either one away from its default lights the panel's dot (isCustom). Run in Node.js on a stand-in
                page (tests/test_app_expire.py's), with a stored choice and the page's language.
  * Captions  — GV.ytCaptions() is "" while Off and asks for captions in the page language while On; a lite-youtube
                preview gets the captions' parameters in its `params` just before it turns into a player (a click,
                Enter or Space — capture phase), keeps its own (rel, enablejsapi, hl), gains hl when it had none
                (Home's), and is left alone while Off or once it is a player. Every YouTube player in the site's
                scripts is one of these, the Watch dialog (media.js, which adds GV.ytCaptions()) or the booth (its own
                switch): a new embed elsewhere would miss the visitor's choice.
  * Markup    — the panel: the speed group (3 radios inside the read-aloud group), Previous / Next paragraph (off
                until reading starts; Next aria-disabled on the last paragraph), the captions group before Data saver;
                the read-aloud bar: Previous, Pause, Next, Stop in that order, the icon buttons named; the Accessibility
                page: the one-tap button (JavaScript only; announced), the captions card among the settings.

What only a browser can show (speech with a stand-in voice: where reading starts, Back / Next, the speed heard at
once, the bar's buttons on a phone, the captions in a real player's address) is in
tests/browser/test_r12_u4_aa_browser.py.

    python -m unittest tests.test_r12_u4_aa -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_app_expire import DOM  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


# The stand-in page of test_app_expire, with the page's language and a stored "gvlv-prefs" of the test's choosing
# (globalThis.__LANG, globalThis.__STORE), and a working localStorage.
_HTML = 'el("html", { lang: "en" }, [body])'
_STORE = "localStorage: { getItem: () => null, setItem() {}, removeItem() {} }"
assert _HTML in DOM and _STORE in DOM, "tests/test_app_expire.py's stand-in page changed: update this test"
PAGE = DOM.replace(_HTML, 'Object.assign(el("html", { lang: globalThis.__LANG || "en" }, [body]), { lang: globalThis.__LANG || "en" })').replace(
    _STORE,
    "localStorage: { getItem: (k) => (k in (globalThis.__STORE ||= {}) ? globalThis.__STORE[k] : null), "
    "setItem: (k, v) => { (globalThis.__STORE ||= {})[k] = String(v); }, removeItem: (k) => { delete (globalThis.__STORE ||= {})[k]; } }")


def js(case: unittest.TestCase, script: str):
    return run_js(case, PAGE + script, needs_modules=False, timeout=60)


NEW_KEYS = {
    "common.json": ("comfort.read_prev", "comfort.read_next", "comfort.read_speed", "comfort.read_slower",
                    "comfort.read_faster", "comfort.read_speed_hint", "comfort.captions", "comfort.captions_hint"),
    "access.json": ("access.f_captions_t", "access.f_captions", "access.cc_all_t", "access.cc_all_off", "access.cc_all_on",
                    "access.cc_all_note", "access.cc_all_btn", "access.cc_all_btn_off", "access.cc_all_said_on",
                    "access.cc_all_said_off"),
}


class Strings(unittest.TestCase):
    def test_new_keys_in_both_languages(self):
        for file, keys in NEW_KEYS.items():
            data = json.loads(read("src", "_i18n", file))
            for key in keys:
                with self.subTest(key=key):
                    self.assertIn(key, data)
                    self.assertTrue(data[key]["en"].strip() and data[key]["es"].strip())
                    self.assertNotEqual(data[key]["en"], data[key]["es"])

    def test_honest_about_youtube_and_the_device(self):
        common = json.loads(read("src", "_i18n", "common.json"))
        access = json.loads(read("src", "_i18n", "access.json"))
        # YouTube may ignore it; automatic captions can be wrong (the one-tap card says both)
        self.assertIn("doesn't always follow", access["access.cc_all_note"]["en"])
        self.assertIn("get words wrong", access["access.cc_all_note"]["en"])
        self.assertIn("no siempre respeta", access["access.cc_all_note"]["es"])
        self.assertIn("pueden equivocarse", access["access.cc_all_note"]["es"])
        self.assertIn("doesn't always follow", common["comfort.captions_hint"]["en"])
        self.assertIn("no siempre lo respeta", common["comfort.captions_hint"]["es"])
        # the speed depends on the device and its voice
        self.assertIn("depends on your device", common["comfort.read_speed_hint"]["en"])
        self.assertIn("depende de tu dispositivo", common["comfort.read_speed_hint"]["es"])
        # read aloud says where it starts
        self.assertIn("on your screen", common["comfort.read_hint"]["en"])
        self.assertIn("en pantalla", common["comfort.read_hint"]["es"])
        # (the on-device promise: nothing is sent anywhere)
        self.assertIn("this device only", access["access.cc_all_off"]["en"])
        self.assertIn("solo en este dispositivo", access["access.cc_all_off"]["es"])


class Prefs(unittest.TestCase):
    def test_defaults_values_and_reset(self):
        r = js(self, r"""
          globalThis.__STORE = { "gvlv-prefs": JSON.stringify({ rate: "warp", captions: "yes", text: 130 }) };
          const p = page([]);
          const first = p.G.prefs.get(), custom0 = p.G.prefs.isCustom();
          p.G.prefs.set({ rate: "slower" });
          const slower = p.G.prefs.get().rate, stored = JSON.parse(globalThis.__STORE["gvlv-prefs"]);
          p.G.prefs.set({ rate: "fast" });          // not a value: back to the default
          const bad = p.G.prefs.get().rate;
          p.G.prefs.set({ text: 100, captions: "on" });
          const ccOnly = p.G.prefs.isCustom();
          p.G.prefs.reset();
          out({ first, custom0, slower, stored, bad, ccOnly, after: p.G.prefs.get(), customAfter: p.G.prefs.isCustom(),
                left: "gvlv-prefs" in globalThis.__STORE, defaults: p.G.prefs.defaults });""")
        self.assertEqual(r["first"]["rate"], "normal", "an unknown stored speed is Normal")
        self.assertEqual(r["first"]["captions"], "off", "an unknown stored captions value is Off")
        self.assertEqual(r["first"]["text"], 130, "the other choices are kept")
        self.assertTrue(r["custom0"])
        self.assertEqual(r["slower"], "slower")
        self.assertEqual(r["stored"]["rate"], "slower", "saved on the device")
        self.assertEqual(r["bad"], "normal")
        self.assertTrue(r["ccOnly"], "captions On alone lights the panel's dot")
        self.assertEqual((r["after"]["rate"], r["after"]["captions"]), ("normal", "off"))
        self.assertFalse(r["customAfter"])
        self.assertFalse(r["left"], "all defaults: nothing stored")
        self.assertEqual((r["defaults"]["rate"], r["defaults"]["captions"]), ("normal", "off"))

    def test_app_js_lists_the_values(self):
        app = read("src", "assets", "js", "app.js")
        self.assertRegex(app, r'rate: \["slower", "normal", "faster"\]')
        self.assertRegex(app, r'captions: \["off", "on"\]')
        self.assertIn('rate: "normal", captions: "off" }', app)
        self.assertIn("RATES = { slower: 0.8, normal: 1, faster: 1.2 }", app)
        self.assertIn("u.rate = RATES[rate] || 1;", app)


LYT = r"""
const lyt = (params) => el("lite-youtube", params === null ? { class: "home-yt" } : { class: "media-lyt", params });
const press = (p, target, type = "click", key) => p.fire(type, { key, target: { closest: (s) => (s === "lite-youtube" ? target : null) } });
"""


class Captions(unittest.TestCase):
    def test_off_by_default_and_the_page_language_when_on(self):
        r = js(self, r"""
          globalThis.__LANG = "es";
          const p = page([]);
          const off = p.G.ytCaptions();
          p.G.prefs.set({ captions: "on" });
          out({ off, on: p.G.ytCaptions() });""")
        self.assertEqual(r["off"], "")
        self.assertEqual(r["on"], "cc_load_policy=1&cc_lang_pref=es")

    def test_a_preview_gets_captions_just_before_it_plays(self):
        r = js(self, LYT + r"""
          globalThis.__LANG = "es";
          globalThis.__STORE = { "gvlv-prefs": JSON.stringify({ captions: "on" }) };
          const p = page([]);
          const watch = lyt("rel=0&enablejsapi=1&hl=es"), home = lyt(null), done = lyt("rel=0&hl=es"), keyed = lyt("rel=0&hl=es"),
                other = lyt("rel=0&hl=es");
          done.classList.add("lyt-activated");
          press(p, watch); press(p, watch);              // (Enter on a button is a keydown AND a click: the same result)
          press(p, home); press(p, done);
          press(p, keyed, "keydown", "Enter"); press(p, other, "keydown", "a");
          out({ watch: watch.getAttribute("params"), home: home.getAttribute("params"), done: done.getAttribute("params"),
                keyed: keyed.getAttribute("params"), other: other.getAttribute("params") });""")
        q = lambda s: dict(x.split("=", 1) for x in s.split("&"))  # noqa: E731
        self.assertEqual(q(r["watch"]), {"rel": "0", "enablejsapi": "1", "hl": "es", "cc_load_policy": "1", "cc_lang_pref": "es"})
        self.assertEqual(q(r["home"]), {"cc_load_policy": "1", "cc_lang_pref": "es", "hl": "es"}, "Home's had no params")
        self.assertEqual(r["done"], "rel=0&hl=es", "already a player: left alone")
        self.assertEqual(q(r["keyed"])["cc_load_policy"], "1", "Enter on its button")
        self.assertEqual(r["other"], "rel=0&hl=es", "another key does nothing")

    def test_off_leaves_the_players_alone(self):
        r = js(self, LYT + r"""
          const p = page([]);
          const a = lyt("rel=0&playsinline=1&hl=en"), b = lyt(null);
          press(p, a); press(p, b);
          out({ a: a.getAttribute("params"), b: b.getAttribute("params") });""")
        self.assertEqual(r["a"], "rel=0&playsinline=1&hl=en")
        self.assertIsNone(r["b"])

    def test_every_youtube_player_follows_the_choice(self):
        # an embed address built anywhere else in the site's scripts or pages would not ask for captions
        found = {}
        for p in [*ROOT.glob("src/assets/js/*.js"), *ROOT.glob("src/**/*.njk"), *ROOT.glob("eleventy/**/*.js")]:
            text = p.read_text(encoding="utf-8")
            if re.search(r"youtube(?:-nocookie)?\.com/embed/\"|youtube(?:-nocookie)?\.com/embed/\$\{|youtube(?:-nocookie)?\.com/embed/\{\{", text):
                found[p.relative_to(ROOT).as_posix()] = text
        self.assertEqual(sorted(found), ["src/assets/js/media.js"], "a new YouTube embed: give it GV.ytCaptions()")
        media = found["src/assets/js/media.js"]
        self.assertIn('var cc = GV.ytCaptions ? GV.ytCaptions() : "";', media)
        self.assertRegex(media, r'&hl=" \+ LANG \+ \(cc \? "&" \+ cc : ""\)')
        # the booth builds its player with the YouTube API (its own captions switch, on by default)
        self.assertIn("cc_load_policy: SETTINGS.captions === false ? 0 : 1", read("src", "assets", "js", "booth.js"))
        # no page asks for (or against) captions on its own: the visitor's choice decides
        for p in [*ROOT.glob("src/**/*.njk")]:
            text = p.read_text(encoding="utf-8")
            for m in re.finditer(r"<lite-youtube\b[^>]*>", text):
                with self.subTest(page=p.name):
                    self.assertNotIn("cc_load_policy", m.group(0))
        app = read("src", "assets", "js", "app.js")
        self.assertIn('document.addEventListener("click", lytCaptions, true);', app)


class Markup(unittest.TestCase):
    def setUp(self):
        self.panel = read("src", "_includes", "partials", "comfort-panel.njk")
        self.bar = self.panel[self.panel.index('<div class="tts-bar"'):]
        self.main = self.panel[:self.panel.index('<div class="tts-bar"')]

    def test_panel_speed_skip_and_captions(self):
        read_group = self.main[self.main.index('"comfort.read" | t(L)'):self.main.index('seg("captions"')]
        self.assertEqual(read_group.count('name="gvlv-rate"'), 1)
        self.assertIn('["slower", "comfort.read_slower"], ["normal", "comfort.normal"], ["faster", "comfort.read_faster"]', read_group)
        self.assertIn('<fieldset class="gvlv-speed">', read_group)
        self.assertIn('"comfort.read_speed" | t(L)', read_group)
        for fn in ("ttsPrev()", "ttsNext()"):
            btn = re.search(r'<button[^>]*@click="' + re.escape(fn) + r'"[^>]*>', read_group).group(0)
            with self.subTest(button=fn):
                self.assertIn(":disabled=\"tts.state === 'idle'\" disabled", btn)
        self.assertIn(":aria-disabled=\"tts.next ? null : 'true'\"", re.search(r'<button[^>]*ttsNext\(\)[^>]*>', read_group).group(0))
        # the captions group: after read aloud, before Data saver (and so before #pwa-slot and Reset)
        self.assertLess(self.main.index('"comfort.read" | t(L)'), self.main.index('seg("captions"'))
        self.assertLess(self.main.index('seg("captions"'), self.main.index('seg("saver"'))
        self.assertIn('seg("captions", "comfort.captions", "comfort.captions_hint", "captions", [["off", "comfort.off" | t(L)], ["on", "comfort.on" | t(L)]], L)', self.main)

    def test_bar_buttons_in_order_and_named(self):
        actions = self.bar[self.bar.index('class="tts-bar-actions"'):]
        order = [m.group(1) for m in re.finditer(r'@click="(\w+)\(\)"', actions)]
        self.assertEqual(order, ["prev", "toggle", "next", "stop"])
        for fn, key in (("prev", "comfort.read_prev"), ("next", "comfort.read_next"), ("stop", "comfort.read_stop")):
            btn = re.search(r'<button[^>]*@click="' + fn + r'\(\)"[^>]*>', actions).group(0)
            with self.subTest(button=fn):
                self.assertIn(f"aria-label=\"{{{{ '{key}' | t(L) }}}}\"", btn)
        self.assertIn(":aria-disabled=\"tts.next ? null : 'true'\"", re.search(r'<button[^>]*@click="next\(\)"[^>]*>', actions).group(0))
        css = read("src", "assets", "css", "areas", "access.css")
        self.assertIn(".tts-bar-stop, .tts-bar-skip { display: grid; place-items: center; flex-shrink: 0; width: 2.75rem; height: 2.75rem;", css)
        self.assertIn(':is(.gvlv-read, .tts-bar) [aria-disabled="true"]', css)

    def test_accessibility_page(self):
        page = read("src", "pages", "accessibility.njk")
        cap = page[page.index('id="captions"'):page.index('id="asl"')]
        card = cap[cap.index('class="card card-pad ax-cc'):]
        card = card[:card.index("</button>")]
        self.assertIn("data-js-only", card[:200])
        self.assertIn("GV.prefs.set({ captions: on ? 'off' : 'on' })", card)
        self.assertIn("GV.announce(", card)
        for key in ("access.cc_all_btn", "access.cc_all_btn_off", "access.cc_all_said_on", "access.cc_all_said_off", "access.cc_all_note"):
            with self.subTest(key=key):
                self.assertIn(f"'{key}'" if "said" in key else f'"{key}"', card)
        # before the CC steps (the way when YouTube does not follow it)
        self.assertLess(cap.index("ax-cc"), cap.index('("access.cap_" + c + n)'))
        self.assertIn('["captions", "captions", "grape"]', page)
        self.assertIn("lg:col-span-2 lg:flex-row", page)
        self.assertIn("@media print { .ax-cc { display: none !important; } }", read("src", "assets", "css", "areas", "access.css"))


class ReadAloudScript(unittest.TestCase):
    """The parts of GV.tts a browser runs (tests/browser/test_r12_u4_aa_browser.py hears them): written down here so
    a later edit keeps them."""

    def setUp(self):
        app = read("src", "assets", "js", "app.js")
        self.tts = app[app.index("GV.tts = (function () {"):app.index("/* ---------------- Alpine components")]

    def test_starts_on_screen_and_moves_by_block(self):
        for line in (
            # where it starts; the page stays where it is meanwhile
            'if (state !== "paused") { chunks = collect(); idx = onScreen(); hold = chunks[idx] ? chunks[idx].el : null; }',
            "if ((window.pageYOffset || 0) < 48) return 0;",
            "if (hold && r.top >= top - 2 && r.top < bottom) return;",
            # …not in a side column stuck on the screen (sticky, at its line; or fixed) unless nothing else shows
            "if (pinned(chunks[i].el, root, memo)) {",
            "return seen >= 0 ? seen : side >= 0 ? side : sideSeen >= 0 ? sideSeen : 0;",
            'v = cs.position === "fixed";',
            "v = (!isNaN(t) && r.top <= t + 1) || (!isNaN(b) && r.bottom >= window.innerHeight - b - 1);",
            # chips are skipped (filters, jump links), except a list marked data-tts-read (the AA offices)
            "if (!el || el.closest(SKIP) || chipSkipped(el)) return NodeFilter.FILTER_REJECT;",
            'function chipSkipped(el) { var c = el.closest(".chip"); return !!c && !c.closest("[data-tts-read]"); }',
            # Back / Next, and whether there is a next paragraph
            "play: play, pause: pause, stop: stop, prev: prev, next: next,",
            'next: state !== "idle" && nextBlock(idx) < chunks.length',
            # leaving the page still stops it
            'window.addEventListener("pagehide", stop);',
            'window.addEventListener("beforeunload", stop);',
        ):
            with self.subTest(line=line):
                self.assertTrue(line in self.tts, line)


if __name__ == "__main__":
    unittest.main()
