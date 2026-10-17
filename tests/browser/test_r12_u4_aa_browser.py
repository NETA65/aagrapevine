"""Round 12 in a real browser (tests/browser/__init__.py says how to run these): the "Aa" panel's reading speed,
Previous / Next paragraph and "read from where I am", and video captions (tests/test_r12_u4_aa.py has the checks that
need no browser). Speech is a stand-in voice (window.speechSynthesis replaced before the page's scripts: it notes
what it is asked to say, at what rate, and ends a sentence when the test says so) — nothing is heard, and the page
never knows.

  * ReadAloudControls — at the top of the page reading starts with the first paragraph; scrolled down (the Audio
                        section's heading under the header) with the first paragraph on the screen, the page not moved;
                        Next and Previous move a paragraph at a time and read at once (also while paused); a new speed
                        (0.8 / 1.2, Reset: 1) starts the sentence again at that speed, and is saved on the device; Next
                        on the last paragraph does nothing; leaving the page stops it.
                        Half-way down a page with a side column stuck on the screen (What's New in both languages at
                        1600 px, the Library, the Digest, a monthly toolkit at 1280 px): it starts in the main column,
                        not the side column, and goes on down — never back to the top of the page.
                        The AA offices on Meetings' "New to AA?" card (links shown as chips): each read, by name, right
                        after their heading, in its site's language; other chips (Home's library shortcuts) are not.
                        The panel by keyboard (Spanish): Previous / Next are off until reading starts, arrow keys choose
                        the speed, Enter on Next moves on, Next on the last paragraph says it is off and keeps the
                        keyboard; at the end of the page the keyboard goes to the main button.
                        A 360-pixel phone at 150 % text: the bar's four buttons (Previous, Pause, Next, Stop) are named,
                        44 px, inside the screen; Stop — or the end of the page — puts the keyboard on the visible Menu /
                        Aa button; the Accessibility page and the open panel never scroll sideways.
  * VideoCaptions     — with "Video captions" On, Watch's featured preview, its list's video dialog and Home's preview
                        open their players with captions in the page language (Spanish on /es/); Off, they don't. The
                        Accessibility page's one-tap button turns it on (saved; said to a screen reader; the panel shows
                        On) and off again.
"""
from __future__ import annotations

import json
import unittest

try:   # (the browser checks' module: its site server, browser and helpers — one of each for both files)
    from browser import test_site_in_browser as B
except ImportError:  # (run as tests.browser.…)
    from tests.browser import test_site_in_browser as B

setUpModule = B.setUpModule          # noqa: N816 — unittest's own names
tearDownModule = B.tearDownModule    # noqa: N816

# The stand-in voice, installed before any page script (app.js reads window.speechSynthesis when it loads).
FAKE_SPEECH = r"""
(() => {
  const spoken = [];
  let current = null, cancels = 0;
  const synth = {
    speaking: false, paused: false, pending: false,
    getVoices: () => [], addEventListener() {}, removeEventListener() {},
    speak(u) { spoken.push({ text: u.text, rate: u.rate, lang: u.lang }); current = u; this.speaking = true; },
    cancel() {
      cancels++;
      const u = current; current = null; this.speaking = false;
      if (u && u.onerror) setTimeout(() => u.onerror({ error: "interrupted" }), 0);
    },
    pause() {}, resume() {},
  };
  function Utterance(text) { this.text = text; this.rate = 1; this.lang = ""; this.voice = null; }
  Object.defineProperty(window, "speechSynthesis", { value: synth, configurable: true });
  window.SpeechSynthesisUtterance = Utterance;
  window.__speech = {
    spoken,
    cancels: () => cancels,
    // the voice finishes what it is saying (the page then goes on to the next sentence)
    end() { const u = current; current = null; synth.speaking = false; if (u && u.onend) u.onend({}); return !!u; },
  };
})();
"""

STATE = """() => { const s = GV.tts.state(), c = GV.tts.chunks(), last = __speech.spoken[__speech.spoken.length - 1] || null;
  const cur = document.querySelector(".tts-current"), r = cur ? cur.getBoundingClientRect() : null;
  return { s, said: last, n: __speech.spoken.length, text: c[s.index] ? c[s.index].text : null, y: window.scrollY,
           cur: r ? { top: r.top, bottom: r.bottom } : null, h: window.innerHeight,
           padTop: parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0 }; }"""

# The paragraph being read: where it is on the page (from the page's top) and the side column it sits in, if any
# (an element of <main> that is sticky or fixed — e.g. the filters, the poster, the player card).
WHERE = """() => { const cur = document.querySelector(".tts-current"), main = document.querySelector("main");
  let side = null;
  for (let n = cur; n && n !== main; n = n.parentElement) {
    const p = getComputedStyle(n).position;
    if (p === "sticky" || p === "fixed") { side = n.className || n.tagName; break; }
  }
  return { pageTop: cur ? cur.getBoundingClientRect().top + window.scrollY : null, side }; }"""

# The side columns of <main> stuck on the screen right now (sticky, at the line they stick to).
STUCK = """() => [...document.querySelectorAll("main *")].filter((e) => {
  const cs = getComputedStyle(e);
  if (cs.position !== "sticky") return false;
  const r = e.getBoundingClientRect();
  return r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.top <= parseFloat(cs.top) + 1;
}).map((e) => e.className || e.tagName)"""

# The text read aloud for each of the AA offices' links on the New to AA? card: what shows on the link, without its
# screen-reader words and the EN / ES badge; and the language the link says its site is in.
OFFICES = """() => [...document.querySelectorAll("#new-to-aa a.chip")].map((a) => {
  const c = a.cloneNode(true);
  c.querySelectorAll(".sr-only, [aria-hidden='true'], svg").forEach((e) => e.remove());
  return { text: c.textContent.replace(/\\s+/g, " ").trim(), lang: a.getAttribute("hreflang") };
})"""


def speech_context(width: int, height: int, lang: str = "en", prefs: dict | None = None):
    ctx = B.new_context(width, height, lang=lang, prefs=prefs)
    ctx.add_init_script(FAKE_SPEECH)
    return ctx


def said_more(page, n: int, timeout: int = 3000):
    """Wait until the voice has been asked to say more than n things."""
    page.wait_for_function(f"() => __speech.spoken.length > {n}", timeout=timeout)
    return page.evaluate(STATE)


def stored_prefs(page) -> dict:
    return json.loads(page.evaluate("() => localStorage.getItem('gvlv-prefs') || '{}'"))


class ReadAloudControls(unittest.TestCase):
    def test_where_it_starts_back_next_and_speed(self):
        ctx = speech_context(1280, 800)
        try:
            page = B.open_page(ctx, "accessibility/")
            # at the top of the page: the first paragraph
            page.evaluate("GV.tts.play()")
            st = said_more(page, 0)
            self.assertEqual(st["s"]["index"], 0)
            self.assertEqual(st["said"]["text"], page.evaluate("GV.tts.chunks()[0].text"))
            self.assertEqual(st["said"]["rate"], 1)
            page.evaluate("GV.tts.stop()")

            # scrolled down: the first paragraph on the screen, and the page stays where it is
            page.evaluate("document.getElementById('audio-title').scrollIntoView({ block: 'start' })")
            page.wait_for_timeout(100)
            y0 = page.evaluate("window.scrollY")
            n = page.evaluate("__speech.spoken.length")
            page.evaluate("GV.tts.play()")
            st = said_more(page, n)
            self.assertGreater(st["s"]["index"], 0, "it started at the top again")
            self.assertEqual(st["said"]["text"], st["text"])
            self.assertEqual(st["y"], y0, "the page moved")
            self.assertIsNotNone(st["cur"])
            self.assertGreaterEqual(st["cur"]["top"], st["padTop"] - 2, st)
            self.assertLess(st["cur"]["top"], st["h"], st)
            heading = page.inner_text("#audio-title").strip()
            upcoming = page.evaluate(f"GV.tts.chunks().slice({st['s']['index']}, {st['s']['index'] + 3}).map(c => c.text)")
            self.assertIn(heading, upcoming, "not the part of the page on the screen")
            start = st["s"]["index"]

            # Next, then Previous: a paragraph at a time, read at once
            page.evaluate("GV.tts.next()")
            st = said_more(page, st["n"])
            self.assertGreater(st["s"]["index"], start)
            self.assertEqual(st["said"]["text"], st["text"])
            self.assertTrue(st["s"]["next"])
            page.evaluate("GV.tts.prev()")
            st = said_more(page, st["n"])
            self.assertEqual(st["s"]["index"], start)
            self.assertEqual(st["said"]["text"], st["text"])
            # …also while paused (it reads at once)
            page.evaluate("GV.tts.pause()")
            page.evaluate("GV.tts.next()")
            st = said_more(page, st["n"])
            self.assertEqual(st["s"]["state"], "playing")

            # a new speed: the sentence again, at once, at that speed — saved on this device
            here = st["s"]["index"]
            for choice, rate in (("slower", 0.8), ("faster", 1.2)):
                page.evaluate(f"GV.prefs.set({{ rate: '{choice}' }})")
                st = said_more(page, st["n"])
                with self.subTest(speed=choice):
                    self.assertAlmostEqual(st["said"]["rate"], rate)
                    self.assertEqual(st["s"]["index"], here)
                    self.assertEqual(stored_prefs(page).get("rate"), choice)
            page.evaluate("GV.prefs.reset()")
            st = said_more(page, st["n"])
            self.assertEqual(st["said"]["rate"], 1)
            self.assertNotIn("rate", stored_prefs(page))

            # the last paragraph: Next does nothing
            page.evaluate("() => { let k = 0; while (GV.tts.state().next && k++ < 5000) GV.tts.next(); }")
            st = said_more(page, st["n"])
            self.assertFalse(st["s"]["next"])
            last = st["s"]["index"]
            page.evaluate("GV.tts.next()")
            page.wait_for_timeout(200)
            st = page.evaluate(STATE)
            self.assertEqual(st["s"]["index"], last)

            # leaving the page stops it
            cancels = page.evaluate("__speech.cancels()")
            page.evaluate("dispatchEvent(new Event('pagehide'))")
            st = page.evaluate(STATE)
            self.assertEqual(st["s"]["state"], "idle")
            self.assertGreater(page.evaluate("__speech.cancels()"), cancels)
        finally:
            ctx.close()

    def test_scrolled_down_beside_a_side_column_that_stays_on_the_screen(self):
        # A sticky side column (the filters, the poster, the refine column) comes before the page's main column and
        # stays on the screen: reading starts in the main column, where the visitor is, and goes on down from there —
        # it never starts in the side column and then jumps back to the top of the page.
        cases = [("whats-new/", 1600, 900, "en"), ("es/whats-new/", 1600, 900, "es"), ("library/", 1280, 800, "en"),
                 ("digest/", 1280, 800, "en")]
        cases += [(f"monthly/{m}/", 1280, 800, "en") for m in B.poster_months()[:1]]
        for path, w, h, lang in cases:
            ctx = speech_context(w, h, lang=lang)
            try:
                page = B.open_page(ctx, path)
                page.evaluate("window.scrollTo(0, Math.round((document.documentElement.scrollHeight - innerHeight) / 2))")
                page.wait_for_timeout(150)
                with self.subTest(page=path, check="a side column stuck on the screen"):
                    self.assertTrue(page.evaluate(STUCK), "no sticky column on the screen here: the check tests nothing")
                y0 = page.evaluate("window.scrollY")
                page.evaluate("GV.tts.play()")
                st = said_more(page, 0)
                first = page.evaluate(WHERE)
                with self.subTest(page=path, check="where it starts"):
                    self.assertGreater(st["s"]["index"], 0, "it started at the top again")
                    self.assertIsNone(first["side"], f"it started in the side column: {st['text']!r}")
                    self.assertEqual(st["y"], y0, "the page moved")
                    self.assertGreaterEqual(st["cur"]["top"], st["padTop"] - 2, st)
                    self.assertLess(st["cur"]["top"], st["h"], st)
                # the voice finishes: the next sentence is further down the page, never back at the top
                for _ in range(2):
                    page.evaluate("__speech.end()")
                    st = said_more(page, st["n"])
                    nxt = page.evaluate(WHERE)
                    with self.subTest(page=path, check="what comes next", text=st["text"]):
                        self.assertIsNone(nxt["side"])
                        self.assertGreaterEqual(nxt["pageTop"], first["pageTop"] - 1, st["text"])
                        self.assertGreaterEqual(st["y"], y0 - 2, "the page went back up")
                    first = nxt
                page.evaluate("GV.tts.stop()")
            finally:
                ctx.close()

    def test_the_aa_offices_on_new_to_aa_are_read(self):
        # The offices on the New to AA? card are links styled as chips: read, each one, right after their heading, an
        # office's name in its site's language — while chips elsewhere (filters, jump links: Home's library
        # shortcuts) are still left out.
        words = json.loads(B.ROOT.joinpath("src", "_i18n", "common.json").read_text(encoding="utf-8"))
        for path, lang in (("meetings/", "en"), ("es/meetings/", "es")):
            ctx = speech_context(1280, 800, lang=lang)
            try:
                page = B.open_page(ctx, path)
                offices = page.evaluate(OFFICES)
                self.assertGreaterEqual(len(offices), 2, offices)
                read = page.evaluate("GV.tts.collect()")
                texts = [c["text"] for c in read]
                head = words["newcomer.offices"][lang]
                with self.subTest(page=path):
                    self.assertIn(head, texts)
                    i = texts.index(head)
                    self.assertEqual(texts[i + 1:i + 1 + len(offices)], [o["text"] for o in offices])
                    for o, c in zip(offices, read[i + 1:]):
                        self.assertEqual(c["lang"], o["lang"] or lang, o)
            finally:
                ctx.close()
        ctx = speech_context(1280, 800)
        try:
            page = B.open_page(ctx, "")
            quick = page.evaluate("() => [...document.querySelectorAll('main a.chip')].map((a) => a.textContent.replace(/\\s+/g, ' ').trim())")
            self.assertTrue(quick)
            texts = " | ".join(c["text"] for c in page.evaluate("GV.tts.collect()"))
            for q in quick:
                with self.subTest(chip=q):
                    self.assertNotIn(q, texts)
        finally:
            ctx.close()

    def test_the_panel_by_keyboard(self):
        ctx = speech_context(1280, 800, lang="es")
        try:
            page = B.open_page(ctx, "es/accessibility/")
            page.click(".site-header .gvlv-trigger")
            panel = page.locator("#gvlv-panel")
            panel.wait_for(state="visible", timeout=5000)
            prev = panel.get_by_role("button", name="Párrafo anterior", exact=True)
            nxt = panel.get_by_role("button", name="Párrafo siguiente", exact=True)
            self.assertTrue(prev.is_disabled() and nxt.is_disabled(), "off until reading starts")
            speed = panel.get_by_role("group", name="Velocidad de lectura", exact=True)
            normal = speed.get_by_role("radio", name="Normal", exact=True)
            self.assertTrue(normal.is_checked())
            normal.focus()
            page.keyboard.press("ArrowLeft")
            self.assertTrue(speed.get_by_role("radio", name="Más lenta", exact=True).is_checked())
            self.assertEqual(stored_prefs(page).get("rate"), "slower")

            panel.get_by_role("button", name="Leer esta página", exact=True).click()
            st = said_more(page, 0)
            self.assertAlmostEqual(st["said"]["rate"], 0.8)
            self.assertTrue(nxt.is_enabled())
            nxt.focus()
            page.keyboard.press("Enter")
            st2 = said_more(page, st["n"])
            self.assertGreater(st2["s"]["index"], st["s"]["index"])

            # the last paragraph: Next says it is off, and keeps the keyboard
            page.evaluate("() => { let k = 0; while (GV.tts.state().next && k++ < 5000) GV.tts.next(); }")
            said_more(page, st2["n"])
            page.wait_for_function("() => document.querySelector('#gvlv-panel .gvlv-skip button:last-child').getAttribute('aria-disabled') === 'true'", timeout=3000)
            self.assertTrue(page.evaluate("() => document.activeElement === document.querySelector('#gvlv-panel .gvlv-skip button:last-child')"))
            # the end of the page: the keyboard goes to the main button (Back, Next and Stop turn off)
            page.evaluate("() => { let k = 0; while (__speech.end() && k++ < 50); }")
            page.wait_for_function("() => GV.tts.state().state === 'idle'", timeout=3000)
            page.wait_for_timeout(100)
            focused = page.evaluate("() => document.activeElement && document.activeElement.textContent.trim()")
            self.assertIn("Leer esta página", focused)
            self.assertIn("Terminó la lectura", panel.inner_text())

            panel.get_by_role("button", name="Restablecer", exact=True).click()
            self.assertNotIn("rate", stored_prefs(page))
        finally:
            ctx.close()

    def test_the_bar_on_a_phone(self):
        ctx = speech_context(360, 740, prefs={"text": 150})
        try:
            for path in ("accessibility/", "es/accessibility/"):
                page = B.open_page(ctx, path)
                with self.subTest(page=path, check="no sideways scroll"):
                    self.assertEqual(page.evaluate(B.SIDEWAYS)["wide"], [])
                    self.assertEqual(page.evaluate(B.SIDEWAYS)["moved"], 0)
                page.evaluate("Alpine.store('gvlv').show(document.querySelector('.site-menu-btn'))")
                page.locator("#gvlv-panel").wait_for(state="visible", timeout=5000)
                with self.subTest(page=path, check="the open panel"):
                    over = page.evaluate("() => { const p = document.getElementById('gvlv-panel'); return p.scrollWidth - p.clientWidth; }")
                    self.assertLessEqual(over, 0)
                page.close()

            page = B.open_page(ctx, "about/")
            page.evaluate("Alpine.store('gvlv').show(document.querySelector('.site-menu-btn'))")
            panel = page.locator("#gvlv-panel")
            panel.wait_for(state="visible", timeout=5000)
            panel.get_by_role("button", name="Read this page", exact=True).click()   # (a phone: the panel closes)
            bar = page.locator(".tts-bar")
            bar.wait_for(state="visible", timeout=5000)
            st = said_more(page, 0)
            names = bar.locator("button").evaluate_all("bs => bs.map(b => (b.getAttribute('aria-label') || b.innerText).trim().replace(/\\s+/g, ' '))")
            self.assertEqual([n.split(" ")[0] for n in names], ["Previous", "Pause", "Next", "Stop"], names)
            vw = page.evaluate("document.documentElement.clientWidth")
            for b in bar.locator("button").all():
                box = b.bounding_box()
                with self.subTest(button=b.get_attribute("aria-label") or b.text_content().strip()):
                    self.assertGreaterEqual(box["width"] + 0.5, 44, box)     # (44 px touch targets, also at 150 % text)
                    self.assertGreaterEqual(box["height"] + 0.5, 44, box)
                    self.assertGreaterEqual(box["x"], 0)
                    self.assertLessEqual(box["x"] + box["width"], vw + 0.5)
            bar.get_by_role("button", name="Next paragraph", exact=True).click()
            st2 = said_more(page, st["n"])
            self.assertGreater(st2["s"]["index"], st["s"]["index"])
            bar.get_by_role("button", name="Stop", exact=True).click()
            bar.wait_for(state="hidden", timeout=3000)
            self.assertTrue(page.evaluate("() => !!document.activeElement.closest('.site-header') && document.activeElement.offsetParent !== null"))

            # the end of the page with the keyboard in the bar: it goes to the Menu / Aa button too
            page.evaluate("GV.tts.play()")
            bar.wait_for(state="visible", timeout=5000)
            said_more(page, st2["n"])
            bar.get_by_role("button", name="Pause", exact=True).focus()
            n = page.evaluate("__speech.spoken.length")
            page.evaluate("() => { let k = 0; while (GV.tts.state().next && k++ < 5000) GV.tts.next(); }")
            said_more(page, n)
            page.evaluate("() => { let k = 0; while (__speech.end() && k++ < 50); }")
            bar.wait_for(state="hidden", timeout=3000)
            self.assertTrue(page.evaluate("() => !!document.activeElement.closest('.site-header') && document.activeElement.offsetParent !== null"))
        finally:
            ctx.close()


class VideoCaptions(unittest.TestCase):
    def player_src(self, page, root: str) -> str:
        page.wait_for_selector(f"{root} iframe", state="attached", timeout=5000)
        return page.get_attribute(f"{root} iframe", "src") or ""

    def test_players_start_with_captions_while_it_is_on(self):
        for lang, prefs, on in (("es", {"captions": "on"}, True), ("en", {"captions": "on"}, True), ("en", None, False)):
            ctx = B.new_context(1280, 800, lang=lang, prefs=prefs)
            pre = "es/" if lang == "es" else ""
            want = f"cc_load_policy=1&cc_lang_pref={lang}"
            try:
                page = B.open_page(ctx, pre + "watch/")
                page.locator("main lite-youtube.media-lyt .lyt-playbtn").first.click()
                src = self.player_src(page, "main lite-youtube.media-lyt")
                with self.subTest(lang=lang, on=on, player="Watch: the latest video"):
                    self.assertIn("youtube-nocookie.com/embed/", src)
                    self.assertIn(f"hl={lang}", src)
                    (self.assertIn if on else self.assertNotIn)(want if on else "cc_load_policy", src)
                page.locator("main h3 a.line-clamp-3").first.click()
                src = self.player_src(page, ".media-dialog-frame")
                with self.subTest(lang=lang, on=on, player="Watch: the video dialog"):
                    self.assertIn(f"hl={lang}", src)
                    (self.assertIn if on else self.assertNotIn)(want if on else "cc_load_policy", src)
                page.keyboard.press("Escape")
                page.close()

                page = B.open_page(ctx, pre)
                lyt = page.locator("lite-youtube.home-yt:visible").first
                if lyt.count():
                    lyt.locator(".lyt-playbtn").click()
                    page.wait_for_function("() => !!document.querySelector('lite-youtube.home-yt iframe')", timeout=5000)
                    src = page.get_attribute("lite-youtube.home-yt iframe", "src") or ""
                    with self.subTest(lang=lang, on=on, player="Home"):
                        (self.assertIn if on else self.assertNotIn)(want if on else "cc_load_policy", src)
                        if on:
                            self.assertIn(f"hl={lang}", src)
            finally:
                ctx.close()

    def test_the_one_tap_button(self):
        ctx = B.new_context(1280, 800, lang="es")
        try:
            page = B.open_page(ctx, "es/accessibility/")
            btn = page.get_by_role("button", name="Activar subtítulos en todos los videos", exact=True)
            btn.click()
            page.wait_for_function("() => GV.prefs.get().captions === 'on'", timeout=3000)
            self.assertEqual(stored_prefs(page).get("captions"), "on")
            off = page.get_by_role("button", name="Desactivar los subtítulos", exact=True)
            off.wait_for(state="visible", timeout=3000)
            self.assertTrue(page.evaluate("() => document.activeElement && document.activeElement.classList.contains('ax-cc-btn')"))
            page.wait_for_function("() => (document.querySelector('[data-gv-live]') || {}).textContent === 'Subtítulos activados en todos los videos de este sitio.'", timeout=3000)
            self.assertIn("Los subtítulos están activados", page.inner_text(".ax-cc"))
            # the panel shows the same choice
            page.click(".site-header .gvlv-trigger")
            group = page.locator("#gvlv-panel").get_by_role("group", name="Subtítulos en los videos", exact=True)
            self.assertTrue(group.get_by_role("radio", name="Encendido", exact=True).is_checked())
            page.keyboard.press("Escape")
            off.click()
            page.wait_for_function("() => GV.prefs.get().captions === 'off'", timeout=3000)
            self.assertNotIn("captions", stored_prefs(page))
            page.get_by_role("button", name="Activar subtítulos en todos los videos", exact=True).wait_for(state="visible", timeout=3000)
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
