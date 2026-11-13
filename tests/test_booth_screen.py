"""The booth display's screen (src/assets/js/booth.js, with booth-core.js), run in Node.js on a pretend About page
(tests/fakedom.py) — through "Preview here" (the show playing in the page's card) and as the booth's own screen
(?booth=start, the dialog):

  * a clip that ends right at its slide's time — YouTube past its end mark, seen by the 250 ms ticker through the
    player's progress — moves the show on ONCE: the next slide stays for its own time (it was skipped at once)
  * the next slide's picture is loaded and decoded while the one before shows (warmUp): the same element then shows
    on its slide, already loaded (no second download, no fade from an empty frame); a picture that fails ahead is
    left out — the show picks another one — and the next one is loaded instead
  * on the booth's own screen the next video starts loading ahead too (muted, preload auto) and its slide plays that
    very element — but not while a clip plays (two would share the signal); "Preview here" never loads a clip ahead
  * with Data saver on and a connection nothing is loaded ahead (offline, the saved copy answers at no cost: it is)
  * a sound loaded ahead is the one its slide plays, also when the slide is drawn again in one language

    python -m unittest tests.test_booth_screen -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

B = "/aagrapevine/"


def words(title: str) -> dict:
    return {"title": title, "text": "", "choices": [], "answer": "", "explain": "", "credit": "", "rows": []}


def item(iid: str, typ: str, channel: str, title: str, **extra) -> dict:
    """An ITEM as /about/booth.json has it (tests/test_booth_core.py item): every key present, null when not used."""
    it = {"id": iid, "source": "drive", "type": typ, "channel": channel, "pub": "both", "langs": ["en"], "en": words(title), "es": None,
          "correct": None, "seconds": None, "reveal": None, "weight": 1, "from": None, "until": None, "tags": [],
          "collection": "main", "first": False, "order": None, "media": None, "online": False, "qr": None,
          "qr_es": None, "url": None, "until_ts": None}
    it.update(extra)
    return it


def media(kind: str, src: str = "", **extra) -> dict:
    m = {"kind": kind, "src": src, "id": None, "short": False, "local": False, "poster": None, "start": 0,
         "end": None, "muted": False, "fit": "cover", "w": None, "h": None, "bytes": None}
    m.update(extra)
    return m


def photo(n: int, **extra) -> dict:
    return item(f"drive:p{n}", "photo", "photos", f"Photo {n}", media=media("image", f"{B}about/booth/media/p{n}.jpg", local=True), **extra)


def show(items: list[dict]) -> dict:
    return {"app": "gv-booth", "version": "t1", "built": "2026-10-06T12:00:00Z", "as_of": "2026-10-06", "items": items, "defaults": {}}


HTML = """
<section data-gvb-section>
  <div data-gvb-pv-frame><div data-gvb-still>Welcome</div></div>
  <button type="button" data-gvb-preview>Preview here</button>
  <div data-gvb-pv-ctl hidden><button type="button" data-gvb-pv-act="pause"><svg></svg><span>Pause</span></button></div>
</section>
<script type="application/json" id="gvb-config">__CFG__</script>
"""

# boot(show) → the About page with booth-core.js + booth.js, "Preview here" pressed and the show started; the stage's
# slides are counted as they come (shown: their titles), and every picture made with new Image() is listed (warm).
# A pretend YouTube player API: the player starts at once; yt.time is where it is (the test moves it).
BOOTH_JS = PAGE_JS + r"""
async function boot(data) {
  const cfg = { lang: "en", base: "/aagrapevine/", json: "/aagrapevine/about/booth.json", build: "/aagrapevine/build.json", t: {}, screen: { en: {}, es: {} } };
  const fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(data))), body: null });
  const yt = { time: 0, players: 0 };
  let win = null;                                       // (the page's own timers: they follow its clock)
  class Player {
    constructor(id, o) {
      yt.players += 1;
      this.o = o;
      win.setTimeout(() => { o.events.onReady({ target: this }); }, 0);
    }
    getIframe() { return null; } mute() {} unMute() {} setVolume() {}
    playVideo() { win.setTimeout(() => this.o.events.onStateChange({ target: this, data: 1 }), 0); }
    pauseVideo() {} destroy() { this.dead = true; }
    getCurrentTime() { return yt.time; } getDuration() { return 120; }
  }
  const p = page({ html: input.html.replace("__CFG__", JSON.stringify(cfg)), url: "https://example.test/aagrapevine/about/",
                   globals: { fetch, SITE: { lang: "en", base: "/aagrapevine/" }, YT: { Player } },
                   scripts: ["src/assets/js/booth-core.js", "src/assets/js/booth.js"] });
  win = p.win;
  const warm = [];
  const Img = p.win.Image;
  p.win.Image = function () { const i = Img(); warm.push(i); return i; };
  await p.ready();
  p.click(p.$("[data-gvb-preview]"));
  await p.tick(0);
  const stage = p.$(".gvb-stage");
  const shown = [];
  const add = stage.appendChild.bind(stage), swap = stage.replaceChild.bind(stage);
  stage.appendChild = (n) => { shown.push(n.getAttribute("aria-label") || n.className); return add(n); };
  stage.replaceChild = (n, o) => { shown[shown.length - 1] = n.getAttribute("aria-label") || n.className; return swap(n, o); };
  const current = () => { const s = stage.children.filter((n) => !n.classList.contains("is-out")); const c = s[s.length - 1]; return c ? c.getAttribute("aria-label") : null; };
  return { p, yt, warm, shown, current, stage };
}
"""

CLIP_JS = BOOTH_JS + r"""
const b = await boot(input.show);
const R = { first: null };
await b.p.tick(100);
R.first = b.current();
R.players = b.yt.players;
// the clip plays (its 30 s count from its start); the ticker sees it reach its end mark right at its slide's time
await b.p.tick(29800);                                  // (its time: 30 s from its start — the ticker looks every 250 ms)
const before = b.shown.length;
b.yt.time = 30.2;
await b.p.tick(300);
R.cameAtTheEnd = b.shown.slice(before);
R.next = b.current();
await b.p.tick(2000);
R.stillThere = b.current();
R.errors = b.p.errors.map(String);
out(R);
"""

WARM_JS = BOOTH_JS + r"""
const b = await boot(input.show);
const R = { steps: [] };
const img = () => b.stage.querySelector(".gvb-img:not(.gvb-backimg)");
await b.p.tick(10);
// the first picture shows (made with the slide: nothing was loaded ahead yet)
const first = b.current();
b.p.loadImage(img(), true);
await b.p.tick(1500);                                  // AHEAD_MS: the next one is loaded ahead
const w1 = b.warm[b.warm.length - 1];
R.ahead = { count: b.warm.length, src: w1 && w1.getAttribute("src"), decoding: w1 && w1.getAttribute("decoding") };
b.p.loadImage(w1, true);
await b.p.tick(9000);                                  // the next slide
R.next = { title: b.current(), src: img().getAttribute("src"), same: img() === w1, loaded: img().classList.contains("is-loaded") };
// the one after it fails ahead (a venue's filter): it is left out, another one is loaded
await b.p.tick(1500);
const w2 = b.warm[b.warm.length - 1];
R.failing = w2.getAttribute("src");
b.p.loadImage(w2, false);
await b.p.tick(0);
R.instead = (b.warm[b.warm.length - 1] || {}).getAttribute ? b.warm[b.warm.length - 1].getAttribute("src") : null;
await b.p.tick(12000);
R.afterFail = { title: b.current(), src: img() && img().getAttribute("src") };
R.first = first;
R.errors = b.p.errors.map(String);
out(R);
"""


# The booth's own screen (the dialog, ?booth=start) — or "Preview here" (preview: true) — for 90 s: each slide as it
# comes, with the number of <video> / <audio> elements made so far and, for a clip, which of them its slide plays.
CLIPS_JS = PAGE_JS + r"""
const cfg = { lang: "en", base: "/aagrapevine/", json: "/aagrapevine/about/booth.json", build: "/aagrapevine/build.json", t: {}, screen: { en: {}, es: {} } };
const fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(input.show))), body: null });
const p = page({ html: input.html.replace("__CFG__", JSON.stringify(cfg)), url: "https://example.test/aagrapevine/about/" + (input.preview ? "" : "?booth=start"),
                 globals: { fetch, SITE: { lang: "en", base: "/aagrapevine/" } },
                 scripts: ["src/assets/js/booth-core.js", "src/assets/js/booth.js"] });
const made = [];
const create = p.doc.createElement.bind(p.doc);
p.doc.createElement = (t) => { const e = create(t); if (t === "video" || t === "audio") made.push({ e, connected: () => e.isConnected }); return e; };
await p.ready();
if (input.preview) { p.click(p.$("[data-gvb-preview]")); await p.tick(0); }
const log = [];
for (let i = 0; i < 360; i++) {
  await p.tick(250);
  const st = p.$(".gvb-stage");
  const s = st ? st.children.filter((n) => !n.classList.contains("is-out")) : [];
  const c = s[s.length - 1];
  const title = c ? c.getAttribute("aria-label") : null;
  const v = c && c.querySelector("video");
  const at = { t: i * 250, title, made: made.length, clip: !!v };
  if (v) at.el = made.findIndex((m) => m.e === v);
  if (!log.length || log[log.length - 1].title !== title) log.push(at);
  else log[log.length - 1].madeAtEnd = made.length;
}
out({ log, made: made.map((m) => ({ muted: m.e.muted, preload: m.e.getAttribute("preload") })), errors: p.errors.map(String) });
"""

FULL_HTML = HTML + """
<template id="gvb-tpl"><div class="gvb" role="dialog" aria-modal="true" tabindex="-1" data-gvb><div class="gvb-host" data-gvb-host></div></div></template>
"""


def clip(n: int) -> dict:
    return item(f"drive:v{n}", "video", "videos", f"Clip {n}", media=media("video", f"{B}about/booth/media/v{n}.mp4", local=True))


class ClipsAhead(unittest.TestCase):
    def test_the_next_clip_starts_loading_on_the_booths_screen(self):
        r = run_js(self, CLIPS_JS, data={"html": FULL_HTML, "show": show([photo(1, first=True), photo(2), photo(3), clip(1), clip(2)])},
                   needs_modules=False)
        self.assertEqual(r["errors"], [])
        clips = [s for s in r["log"] if s["clip"]]
        self.assertTrue(clips, r["log"])
        for s in clips:
            # its <video> was made before its slide came (loaded ahead, muted, preload auto) — the slide plays that one
            self.assertGreaterEqual(s["el"], 0)
            self.assertLess(s["el"], r["log"][r["log"].index(s) - 1].get("madeAtEnd", s["made"]))
            self.assertTrue(r["made"][s["el"]]["muted"])
            self.assertEqual(r["made"][s["el"]]["preload"], "auto")
            # … and while a clip plays, no other one loads ahead (two would share the signal)
            self.assertEqual(s.get("madeAtEnd", s["made"]), s["made"], s)

    def test_the_preview_never_loads_a_clip_ahead(self):
        r = run_js(self, CLIPS_JS, data={"html": HTML, "preview": True, "show": show([photo(1, first=True), photo(2), clip(1), clip(2)])},
                   needs_modules=False)
        self.assertEqual(r["errors"], [])
        for k, s in enumerate(r["log"]):
            if s["clip"]:
                # its video was made by its own slide, not ahead
                self.assertEqual(s["el"], r["log"][k - 1].get("madeAtEnd", r["log"][k - 1]["made"]), r["log"])


# The booth's own screen with its sound on, on a screen too small for a slide in two languages (every box 100 px, its
# words 1000 px tall): a sound slide is drawn again in one language. Each <audio> made, with its address and its plays.
SOUND_JS = PAGE_JS + r"""
const cfg = { lang: "en", base: "/aagrapevine/", json: "/aagrapevine/about/booth.json", build: "/aagrapevine/build.json", t: {}, screen: { en: {}, es: {} } };
const fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(input.show))), body: null });
const p = page({ html: input.html.replace("__CFG__", JSON.stringify(cfg)), url: "https://example.test/aagrapevine/about/?booth=start",
                 globals: { fetch, SITE: { lang: "en", base: "/aagrapevine/" }, navigator: { userActivation: { hasBeenActive: true } } },
                 scripts: ["src/assets/js/booth-core.js", "src/assets/js/booth.js"] });
const proto = p.win.Element.prototype;
Object.defineProperty(proto, "clientHeight", { get() { return 100; } });
Object.defineProperty(proto, "clientWidth", { get() { return 100; } });
Object.defineProperty(proto, "scrollHeight", { get() { return 1000; } });
const made = [];
const create = p.doc.createElement.bind(p.doc);
p.doc.createElement = (t) => { const e = create(t); if (t === "audio") made.push(e); return e; };
await p.ready();
const seen = [];
for (let i = 0; i < 160; i++) {
  await p.tick(250);
  const st = p.$(".gvb-stage");
  const s = st ? st.children.filter((n) => !n.classList.contains("is-out")) : [];
  const c = s[s.length - 1];
  const title = c ? c.getAttribute("aria-label") : null;
  if (seen[seen.length - 1] !== title) seen.push(title);
}
out({ seen, audio: made.map((a) => ({ src: a.getAttribute("src"), played: a._played || 0 })), errors: p.errors.map(String) });
"""


class SoundAhead(unittest.TestCase):
    def test_a_sound_loaded_ahead_is_the_one_its_slide_plays(self):
        # its slide drawn twice (two languages that don't fit, then one): the sound loaded ahead is taken both times —
        # no second copy downloading beside it, none left loading once the slide has gone
        snd = item("drive:a1", "audio", "sounds", "A sound", langs=["en", "es"], es=words("Un sonido"),
                   media=media("audio", f"{B}about/booth/media/a1.mp3", local=True))
        s = show([photo(1, first=True), snd, photo(2), photo(3)])
        s["defaults"] = {"sound": True, "lang": "both"}
        r = run_js(self, SOUND_JS, data={"html": FULL_HTML, "show": s}, needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertIn("A sound", r["seen"])
        self.assertEqual(r["audio"], [{"src": None, "played": 1}])               # one, played, emptied when it went


SAVER_JS = BOOTH_JS + r"""
const b = await boot(input.show);
b.p.doc.documentElement.setAttribute("data-saver", "on");               // Data saver, online
await b.p.tick(20000);
const online = b.warm.length;
b.p.win.navigator.onLine = false;                                        // offline: the saved copy answers, at no cost
await b.p.tick(10000);
out({ online, offline: b.warm.length, errors: b.p.errors.map(String) });
"""


class DataSaver(unittest.TestCase):
    def test_nothing_is_fetched_ahead_with_data_saver_on(self):
        r = run_js(self, SAVER_JS, data={"html": HTML, "show": show([photo(1), photo(2), photo(3), photo(4)])}, needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["online"], 0)
        self.assertGreater(r["offline"], 0)


class ClipEnd(unittest.TestCase):
    def test_a_clip_ending_at_its_time_moves_the_show_on_once(self):
        yt = item("yt:clip", "video", "web-video", "The clip", first=True, online=True,
                  media=media("youtube", "https://www.youtube.com/watch?v=abcdefghijk", id="abcdefghijk", end=30))
        r = run_js(self, CLIP_JS, data={"html": HTML, "show": show([yt, photo(1), photo(2), photo(3)])}, needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["first"], "The clip")
        self.assertEqual(r["players"], 1)
        # P8-6: one new slide when the clip ended (before: a second one at once, the first skipped)
        self.assertEqual(len(r["cameAtTheEnd"]), 1, r["cameAtTheEnd"])
        self.assertEqual(r["next"], r["cameAtTheEnd"][0])
        self.assertEqual(r["stillThere"], r["next"])


class PicturesAhead(unittest.TestCase):
    def test_the_next_picture_is_loaded_ahead_and_shown_as_it_is(self):
        r = run_js(self, WARM_JS, data={"html": HTML, "show": show([photo(1), photo(2), photo(3), photo(4)])}, needs_modules=False)
        self.assertEqual(r["errors"], [])
        # F-10: 1.5 s into a slide, the next slide's picture is loading (decoded off the main thread)
        self.assertEqual(r["ahead"]["count"], 1)
        self.assertRegex(r["ahead"]["src"], r"^/aagrapevine/about/booth/media/p\d\.jpg$")
        self.assertEqual(r["ahead"]["decoding"], "async")
        # … and it is that very element on the next slide, already loaded: no fade from an empty frame
        self.assertEqual(r["next"]["src"], r["ahead"]["src"])
        self.assertTrue(r["next"]["same"])
        self.assertTrue(r["next"]["loaded"])
        self.assertNotEqual(r["next"]["title"], r["first"])

    def test_a_picture_that_fails_ahead_is_left_out(self):
        r = run_js(self, WARM_JS, data={"html": HTML, "show": show([photo(1), photo(2), photo(3), photo(4)])}, needs_modules=False)
        self.assertNotEqual(r["instead"], r["failing"])                  # another picture loads instead …
        self.assertNotEqual(r["afterFail"]["src"], r["failing"])          # … and the failed one never shows
        self.assertEqual(r["afterFail"]["src"], r["instead"])


if __name__ == "__main__":
    unittest.main()
