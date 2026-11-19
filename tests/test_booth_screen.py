"""The booth display's screen (src/assets/js/booth.js, with booth-core.js), run in Node.js on a pretend About page
(tests/fakedom.py) — through "Preview here" (the show playing in the page's card), as the booth's own screen
(?booth=start, the dialog) and through "Start the booth":

  * a clip that ends right at its slide's time — YouTube past its end mark, seen by the 250 ms ticker through the
    player's progress — moves the show on ONCE: the next slide stays for its own time (it was skipped at once)
  * the next slide's picture is loaded and decoded while the one before shows (warmUp): the same element then shows
    on its slide, already loaded (no second download, no fade from an empty frame); a picture that fails ahead is
    left out — the show picks another one — and the next one is loaded instead
  * on the booth's own screen the next video starts loading ahead too (muted, preload auto) and its slide plays that
    very element — but not while a clip plays (two would share the signal); "Preview here" never loads a clip ahead
  * with Data saver on and a connection nothing is loaded ahead (offline, the saved copy answers at no cost: it is)
  * a sound loaded ahead is the one its slide plays, also when the slide is drawn again in one language
  * the Photos page's pictures (the gallery, booth-core.js isGallery): Settings → Show gives them a fieldset of their
    own (a switch per group, today's count, "needs internet", how often), never among "What to show"; Timing & sound
    has how often, Kiosk the show's own window; the page's chips count them apart from the show's slides (and drop
    them offline); with nothing else on, the chip and Settings → Show say they play one after another (never "one
    every N slides") — and both count a sound slide as on while the sound is (as set, also before the first tap; the
    slides chip never counts it); a magazine cover shows whole with the publishers' line inside its caption (also
    without a title), and no booth picture — nor the one loaded ahead — tells Google's picture host which page asked
  * "Start the booth" on a laptop or desktop (round 32, a pretend window.open and a mouse that hovers): the show opens
    in a window of its own — opened blank, then sent to …/about/?booth=start (named gvlv-booth; no &bs while this
    browser keeps the settings, the name typed just before kept first) —, the page says so and only brings that window
    forward after (Settings: a message to it); a window of that name playing already (this page loaded again) is handed
    back as it is, never loaded again; Settings without the PIN (&tab) only in the blank window the click made — one of
    that name caught loading again goes to the show alone, its PIN kept; its chips follow the window's offline save and
    its connection, and are given back when it ends (a save it left half-way: the worker asked again, the page's own
    next show saves; a show started on the page meanwhile keeps its own); a "bye" or a window closed with its ✕ ends the
    note, and so does one left with no show and silent for 12 s (a reload that failed — one that says hello again keeps
    it), "Stop the show" asks the window (and closes it if it doesn't answer — never behind a PIN); a blocked window →
    the show on the page and a toast; a phone or tablet → the page, as before. With a PIN set, the page's quick controls
    wait and the note says the window asks for it; in the window, the page's Settings and Stop bring up the PIN box —
    and a PIN box already up keeps its ask (the first wins, as for the window's own keys). Another About tab (no handle
    on the window) hears it over the channel of the site's pages (a pretend BroadcastChannel), asking there at once as
    it opens ("ping"), shows the note and asks the window there — no second window, no second show, never asked both
    ways, and a toast says where the show is ("Show the window", "Preview here", Start); the page that opened the window
    takes its word over the channel once it has said nothing to it for 12 s (another tab took it); a page playing its
    own show keeps its own state. The show's own window: its title, "Move this window …", "… this window closes",
    "hello" / "alive" / "bye" to its page (this site's origin) and over the channel (also with its page gone; "alive" at
    once to a page's ping while its show plays, never a ping of its own; the channel closed as the page goes, opened
    again from the back/forward cache), Leave closes it, "settings" / "stop" heard from every page of this site — by
    postMessage (also from the page that opened it after another tab took it) or over the channel — never from another
    site or itself, with the same PIN rule; &tab opens Settings only there, opened by this site's page; a ?booth=start
    typed in a window stays as before. Settings changed in the other window are read, never written back — and reach a
    field left with the focus once that window is not the one in use.

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


# ------------------------------------------------------------------ the gallery: the Photos page's pictures
ROOT = Path(__file__).resolve().parents[1]
LH3 = "https://lh3.googleusercontent.com/d/"
GALLERY = ["gallery-ours", "gallery-gv", "gallery-lv", "gallery-world", "gallery-archive"]
TABS = ["event", "show", "items", "timing", "screen", "kiosk", "offline", "share"]


def i18n(name: str) -> dict:
    return json.loads((ROOT / "src" / "_i18n" / name).read_text(encoding="utf-8"))


# the /photos/ hero credit: the words the build puts on every magazine cover's slide (≈250 characters)
HERO = i18n("committee.json")["committee.photos.hero_credit"]


def gallery(n: int, channel: str, title: str | None = None, credit: bool = True) -> dict:
    """A Photos-page picture as the build makes it (eleventy/filters/booth.js): the committee's own albums a photo
    (cover), the other groups a poster shown whole; Google's copy (online); words in both languages, langs []."""
    ours = channel == "gallery-ours"
    t = f"Picture {n}" if title is None else title
    en, es = words(t), words(t and t + " (es)")
    if credit and not ours:
        en["credit"], es["credit"] = HERO["en"], HERO["es"]
    pub = {"gallery-gv": "gv", "gallery-lv": "lv", "gallery-archive": "gv"}.get(channel, "both")
    return item(f"live:gallery:f{n}", "photo" if ours else "poster", channel, t, source="live", pub=pub, langs=[], en=en, es=es,
                collection="live", online=True, qr="/photos/", qr_es="/es/photos/", url="/photos/",
                media=media("image", f"{LH3}f{n}={'s1920' if ours else 's1600'}", fit="cover" if ours else "contain"))


def counted(s: dict) -> dict:
    """The show with its channels' counts, as booth.json lists them (Settings → Show reads those)."""
    n: dict[str, int] = {}
    for it in s["items"]:
        n[it["channel"]] = n.get(it["channel"], 0) + 1
    s["channels"] = [{"id": k, "count": v} for k, v in n.items()]
    return s


def config() -> dict:
    """#gvb-config with the real words (the macro's pageKeys in English, screenKeys in both languages)."""
    import re
    macro = (ROOT / "src" / "_includes" / "macros" / "booth.njk").read_text(encoding="utf-8")
    s = i18n("booth.json")

    def listed(name: str) -> list[str]:
        return re.findall(r'"([^"]+)"', re.search(r"\{%-\s*set " + name + r" = \[(.*?)\]\s*-%\}", macro, re.S).group(1))
    return {"lang": "en", "base": B, "json": B + "about/booth.json", "build": B + "build.json",
            "t": {"booth." + k: s["booth." + k]["en"] for k in listed("pageKeys")},
            "screen": {l: {"booth.screen." + k: s["booth.screen." + k][l] for k in listed("screenKeys")} for l in ("en", "es")}}


WORDS = i18n("booth.json")


def en(key: str, **v) -> str:
    text = WORDS[key]["en"]
    for k, x in v.items():
        text = text.replace("{" + k + "}", str(x))
    return text


# the About page's four chips, and the dialog with its Settings drawer (the eight tabs, their panels) — the shell
# the macro prints, cut down to the hooks booth.js uses
DRAWER_HTML = (
    '<section data-gvb-section><div data-gvb-pv-frame><div data-gvb-still>Welcome</div></div><ul class="gvb-chips">'
    + "".join(f'<li class="gvb-chip" data-gvb-chip="{c}"{"" if c == "items" else " hidden"}><span></span></li>'
              for c in ("items", "gallery", "content", "offline"))
    + '</ul></section>\n<script type="application/json" id="gvb-config">__CFG__</script>\n'
    '<template id="gvb-tpl"><div class="gvb" role="dialog" aria-modal="true" tabindex="-1" data-gvb><div class="gvb-host" data-gvb-host></div>'
    '<aside class="gvb-drawer" data-gvb-drawer hidden><div class="gvb-tabs" role="tablist" data-gvb-tabs>'
    + "".join(f'<button type="button" role="tab" data-gvb-tab="{t}">{t}</button>' for t in TABS)
    + '</div><div class="gvb-panels">'
    + "".join(f'<div class="gvb-panel" role="tabpanel" tabindex="0" data-gvb-panel="{t}" hidden></div>' for t in TABS)
    + '</div></aside><p class="sr-only" aria-live="polite" data-gvb-live></p>'
    '<div class="gvb-toast is-idle" data-gvb-toast role="status"></div></div></template>\n'
)

# The show (?booth=start) with Settings opened (S): the page's chips, then Settings → Show's fieldsets, Timing &
# sound's and Kiosk's controls; a group switched off, how often changed, then the connection lost. input.stored:
# this device's settings before. input.popup: this page is the show's own window, opened by this site's page with
# its Settings (?booth=start&tab=event): Settings open on their own, with no tap yet — the sound still held back
# (tap: the "Move this window …" chip still up).
GALLERY_SETTINGS_JS = PAGE_JS + r"""
const fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(input.show))), body: null });
const globals = { fetch, SITE: { lang: "en", base: "/aagrapevine/" } };
if (input.popup) Object.assign(globals, { name: "gvlv-booth", opener: { postMessage() {}, location: { origin: "https://example.test" } } });
const p = page({ html: input.html.replace("__CFG__", JSON.stringify(input.cfg)),
                 url: "https://example.test/aagrapevine/about/?booth=start" + (input.popup ? "&tab=event" : ""),
                 globals, scripts: ["src/assets/js/booth-core.js", "src/assets/js/booth.js"] });
if (input.stored) p.win.localStorage.setItem("gv-booth-v1", JSON.stringify(input.stored));
await p.ready();
await p.tick(500);
const all = (n, s) => Array.from(n.querySelectorAll(s));
const chips = () => Object.fromEntries(all(p.doc, "[data-gvb-chip]").map((c) => [c.getAttribute("data-gvb-chip"), c.hidden ? null : c.querySelector("span").textContent]));
const panel = (name) => { p.click(p.$('[data-gvb-tab="' + name + '"]')); return p.$('[data-gvb-panel="' + name + '"]'); };
const box = (l) => {
  const t = l.querySelector(".gvb-opt-t"), d = l.querySelector(".gvb-opt-d"), n = l.querySelector(".gvb-opt-n"), i = l.querySelector("input");
  return { key: i.getAttribute("data-gvb-key"), on: i.checked, label: t.firstChild.data, desc: d ? d.textContent : null, n: n ? n.textContent : null, net: !!t.querySelector(".gvb-opt-net") };
};
const showPanel = () => {
  const s = panel("show");
  return { sets: all(s, "fieldset.gvb-checks").map((fs) => ({ legend: fs.querySelector("legend").textContent, boxes: all(fs, "label.gvb-check").map(box) })),
           notes: all(s, "p.gvb-pp--muted").map((x) => x.textContent) };
};
const R = { chips: chips() };
if (!input.popup) p.key(p.doc.body, "s");
await p.tick(50);
R.drawer = !p.$("[data-gvb-drawer]").hidden;
R.tap = !!p.$("[data-gvb-tapchip]");
R.show = showPanel();
const timing = panel("timing");
R.timing = all(timing, "input").map((i) => ({ key: i.getAttribute("data-gvb-key"), value: i.value,
                                              label: (timing.querySelector('label[for="' + i.id + '"]') || { textContent: null }).textContent }));
const kiosk = panel("kiosk");
R.kiosk = all(kiosk, "label.gvb-check").map(box);
// a group switched off (on this device), and a picture every 12 slides
const gv = panel("show").querySelector('[data-gvb-key="c:channels.gallery-gv"]');
gv.checked = false;
p.fire(gv, "change");
await p.tick(10);
const every = panel("timing").querySelector('[data-gvb-key="n:galleryEvery"]');
every.value = "12";
p.fire(every, "change");
await p.tick(10);
R.stored = JSON.parse(p.win.localStorage.getItem("gv-booth-v1") || "null");
R.after = { chips: chips(), show: showPanel() };
// the connection lost: Google's copies leave the show
p.win.navigator.onLine = false;
p.fire(p.win, "offline");
await p.tick(10);
R.offline = chips();
R.errors = p.errors.map(String);
out(R);
"""


class GallerySettings(unittest.TestCase):
    RUN = None                                          # (one run of the page for every test here)

    def setUp(self):
        if GallerySettings.RUN is None:
            s = show([photo(1), photo(2), photo(3),
                      gallery(1, "gallery-ours"), gallery(2, "gallery-ours"), gallery(3, "gallery-gv"), gallery(4, "gallery-gv"),
                      gallery(5, "gallery-lv"), gallery(6, "gallery-world"), gallery(7, "gallery-archive")])
            GallerySettings.RUN = run_js(self, GALLERY_SETTINGS_JS, data={"html": DRAWER_HTML, "cfg": config(), "show": counted(s)},
                                         needs_modules=False)
        self.r = GallerySettings.RUN
        self.assertEqual(self.r["errors"], [])

    def test_show_has_a_fieldset_of_its_own_for_the_photos_page(self):
        r = self.r
        self.assertTrue(r["drawer"])
        legends = [fs["legend"] for fs in r["show"]["sets"]]
        self.assertIn(en("booth.sh_channels_h"), legends)
        self.assertIn(en("booth.sh_gallery_h"), legends)
        # right after "What to show"
        self.assertEqual(legends.index(en("booth.sh_gallery_h")), legends.index(en("booth.sh_channels_h")) + 1)
        sets = {fs["legend"]: fs["boxes"] for fs in r["show"]["sets"]}
        what = [b["key"] for b in sets[en("booth.sh_channels_h")]]
        self.assertIn("c:channels.photos", what)
        self.assertFalse([k for k in what if "gallery" in k], "the gallery's groups are never among the show's channels")
        boxes = sets[en("booth.sh_gallery_h")]
        # a switch per group, in the order the groups take turns, each with today's count and "needs internet"
        self.assertEqual([b["key"] for b in boxes], ["c:channels." + g for g in GALLERY])
        self.assertEqual([b["label"] for b in boxes], [en("booth.ch." + g.replace("-", "_")) for g in GALLERY])
        self.assertEqual([b["n"] for b in boxes], [en("booth.n_photos_today", n=2), en("booth.n_photos_today", n=2),
                                                   en("booth.n_photos_today_one"), en("booth.n_photos_today_one"), en("booth.n_photos_today_one")])
        self.assertTrue(all(b["on"] and b["net"] for b in boxes))
        # …and how often they come (Timing & sound)
        self.assertIn(en("booth.sh_gallery_note", n=8), r["show"]["notes"])

    def test_timing_has_how_often_and_kiosk_the_shows_own_window(self):
        keys = [x["key"] for x in self.r["timing"]]
        self.assertEqual(keys.index("n:galleryEvery"), keys.index("n:clipEvery") + 1)
        g = self.r["timing"][keys.index("n:galleryEvery")]
        self.assertEqual(g["value"], "8")
        self.assertEqual(g["label"], en("booth.ti_gallery"))
        kiosk = [b["key"] for b in self.r["kiosk"]]
        self.assertEqual(kiosk.index("c:ownWindow") + 1, kiosk.index("c:autoFullscreen"), "next to full screen")
        own = self.r["kiosk"][kiosk.index("c:ownWindow")]
        self.assertTrue(own["on"], "on by default")
        self.assertEqual(own["label"], en("booth.ki_window"))
        self.assertEqual(own["desc"], en("booth.ki_window_d"))

    def test_the_chips_count_the_pictures_apart(self):
        c = self.r["chips"]
        # the show's own: the three Drive photos and the about slide — the seven pictures are not among them
        self.assertEqual(c["items"], en("booth.st_items", n=4))
        self.assertEqual(c["gallery"], en("booth.st_gallery", n=7, every=8))
        # a group switched off, a picture every 12 slides: the chip follows
        a = self.r["after"]["chips"]
        self.assertEqual(a["items"], en("booth.st_items", n=4))
        self.assertEqual(a["gallery"], en("booth.st_gallery", n=5, every=12))
        # offline the pictures (Google's copy) leave the show: the chip goes, the show's own count stays
        self.assertIsNone(self.r["offline"]["gallery"])
        self.assertEqual(self.r["offline"]["items"], en("booth.st_items", n=4))

    def test_a_group_switched_off_is_kept_like_any_channel(self):
        self.assertEqual(self.r["stored"].get("channels"), {"gallery-gv": False})
        self.assertEqual(self.r["stored"].get("galleryEvery"), 12)
        boxes = {fs["legend"]: fs["boxes"] for fs in self.r["after"]["show"]["sets"]}[en("booth.sh_gallery_h")]
        self.assertEqual([b["on"] for b in boxes], [True, False, True, True, True])
        self.assertIn(en("booth.sh_gallery_note", n=12), self.r["after"]["show"]["notes"])


class GalleryOnly(unittest.TestCase):
    """Everything but the Photos page's pictures switched off: the show plays them one after another (the core's
    fill), so neither the chip nor Settings → Show says "one every N slides" (how often does nothing then)."""

    def test_the_chip_and_the_note_say_they_play_one_after_another(self):
        s = show([photo(1), photo(2), photo(3), gallery(1, "gallery-ours"), gallery(2, "gallery-ours"), gallery(3, "gallery-gv"),
                  gallery(4, "gallery-gv"), gallery(5, "gallery-lv"), gallery(6, "gallery-world"), gallery(7, "gallery-archive")])
        r = run_js(self, GALLERY_SETTINGS_JS, data={"html": DRAWER_HTML, "cfg": config(), "show": counted(s), "stored": {"channels": {"photos": False}}},
                   needs_modules=False)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["chips"]["items"], en("booth.st_items_one"), "the about slide")
        self.assertEqual(r["chips"]["gallery"], en("booth.st_gallery_only", n=7))
        self.assertIn(en("booth.sh_gallery_note_only"), r["show"]["notes"])
        self.assertNotIn(en("booth.sh_gallery_note", n=8), r["show"]["notes"])
        # a group off, how often changed: still one after another
        self.assertEqual(r["after"]["chips"]["gallery"], en("booth.st_gallery_only", n=5))
        self.assertIn(en("booth.sh_gallery_note_only"), r["after"]["show"]["notes"])
        for k in ("booth.st_gallery_only", "booth.st_gallery_only_one", "booth.sh_gallery_note_only"):
            with self.subTest(key=k):
                self.assertNotIn("{every}", WORDS[k]["en"] + WORDS[k]["es"])
                self.assertNotRegex(WORDS[k]["en"], r"every \d|every \{")

    def test_a_sound_slide_counts_alike_for_the_chip_and_the_note(self):
        """Only the sound slides and the pictures are on. The sound on: the sound slides play in the show, so the
        pictures come one every N slides — the chip says so as Settings → Show's note does (the slides chip still
        never counts a sound slide: the page plays no sound) — also in the show's own window opened with its Settings
        and not tapped yet: the sound as set, not the sound held back until the first tap. The sound off: the sound
        slides wait, nothing else is on, and both say one after another."""
        s = counted(show([item("drive:s1", "audio", "sounds", "Sound 1", media=media("audio", f"{B}about/booth/media/s1.mp3", local=True)),
                          gallery(1, "gallery-ours"), gallery(2, "gallery-gv"), gallery(3, "gallery-lv")]))
        for sound, popup in ((True, False), (True, True), (False, False)):
            with self.subTest(sound=sound, popup=popup):
                r = run_js(self, GALLERY_SETTINGS_JS, data={"html": DRAWER_HTML, "cfg": config(), "show": s, "stored": {"sound": sound},
                                                            "popup": popup}, needs_modules=False)
                self.assertEqual(r["errors"], [])
                self.assertTrue(r["drawer"])
                self.assertEqual(r["tap"], popup, "the show's own window, opened with its Settings: not tapped yet")
                self.assertEqual(r["chips"]["items"], en("booth.st_items_one"), "the about slide: never a sound slide")
                if sound:
                    self.assertEqual(r["chips"]["gallery"], en("booth.st_gallery", n=3, every=8))
                    self.assertIn(en("booth.sh_gallery_note", n=8), r["show"]["notes"])
                    self.assertNotIn(en("booth.sh_gallery_note_only"), r["show"]["notes"])
                else:
                    self.assertEqual(r["chips"]["gallery"], en("booth.st_gallery_only", n=3))
                    self.assertIn(en("booth.sh_gallery_note_only"), r["show"]["notes"])


# The booth's own screen with nothing but the gallery: each picture slide as it comes (its type, its pictures and
# their referrer policy, its caption), and every picture loaded ahead (new Image()).
GALLERY_SLIDES_JS = PAGE_JS + r"""
const fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(input.show))), body: null });
const p = page({ html: input.html.replace("__CFG__", JSON.stringify(input.cfg)), url: "https://example.test/aagrapevine/about/?booth=start",
                 globals: { fetch, SITE: { lang: "en", base: "/aagrapevine/" } },
                 scripts: ["src/assets/js/booth-core.js", "src/assets/js/booth.js"] });
const warm = [];
const Img = p.win.Image;
p.win.Image = function () { const i = Img(); warm.push(i); return i; };
await p.ready();
const seen = {};
for (let i = 0; i < 400 && Object.keys(seen).length < input.want; i++) {
  await p.tick(250);
  const st = p.$(".gvb-stage");
  const s = st ? st.children.filter((n) => !n.classList.contains("is-out")) : [];
  const c = s[s.length - 1];
  const id = c && c.getAttribute("data-item");
  if (!id || seen[id] || !/^live:gallery:/.test(id)) continue;
  const img = c.querySelector(".gvb-img"), back = c.querySelector(".gvb-backimg"), cap = c.querySelector(".gvb-caption");
  seen[id] = {
    cls: c.className, lang: c.getAttribute("lang"),
    img: img && { cls: img.className, src: img.getAttribute("src"), alt: img.getAttribute("alt"), ref: img.referrerPolicy || null },
    back: back && { src: back.getAttribute("src"), ref: back.referrerPolicy || null },
    caption: cap && { inSlide: cap.parentNode === c, cls: cap.className,
                      parts: cap.children.map((x) => ({ cls: x.className, text: x.textContent, lang: x.getAttribute("lang") })) },
  };
}
out({ seen, warm: warm.map((w) => ({ src: w.getAttribute("src"), ref: w.referrerPolicy || null })), errors: p.errors.map(String) });
"""


class GallerySlides(unittest.TestCase):
    RUN = None

    def setUp(self):
        if GallerySlides.RUN is None:
            items = [gallery(1, "gallery-gv"), gallery(2, "gallery-lv", title=""), gallery(3, "gallery-ours")]
            GallerySlides.RUN = run_js(self, GALLERY_SLIDES_JS, data={"html": FULL_HTML, "cfg": config(), "show": counted(show(items)), "want": 3},
                                       needs_modules=False)
        self.r = GallerySlides.RUN
        self.assertEqual(self.r["errors"], [])
        self.assertEqual(sorted(self.r["seen"]), ["live:gallery:f1", "live:gallery:f2", "live:gallery:f3"])

    def test_a_cover_shows_whole_with_the_publishers_line_in_its_caption(self):
        s = self.r["seen"]["live:gallery:f1"]
        self.assertIn("gvb-t-poster", s["cls"])
        self.assertIn("gvb-slide--media", s["cls"])
        self.assertIn("gvb-img--contain", s["img"]["cls"])
        self.assertEqual(s["img"]["src"], LH3 + "f1=s1600")
        self.assertEqual(s["back"]["src"], s["img"]["src"], "the blurred copy behind it")
        cap = s["caption"]
        # inside the caption (captionRoom keeps the cover clear of it), the lead language's credit, whole
        self.assertTrue(cap["inSlide"])
        self.assertIn("has-credit", cap["cls"].split())
        self.assertEqual(cap["parts"][0]["text"], "Picture 1")
        credit = [x for x in cap["parts"] if x["cls"] == "gvb-credit"]
        self.assertEqual(len(credit), 1)
        self.assertEqual(credit[0]["text"], HERO[s["lang"]])
        self.assertGreater(len(credit[0]["text"]), 200)

    def test_a_cover_without_a_title_still_carries_its_line(self):
        s = self.r["seen"]["live:gallery:f2"]
        self.assertEqual(s["img"]["alt"], "")
        self.assertEqual([x["cls"] for x in s["caption"]["parts"]], ["gvb-credit"])
        self.assertEqual(s["caption"]["parts"][0]["text"], HERO[s["lang"]])

    def test_the_committees_photo_fills_the_screen_without_a_credit(self):
        s = self.r["seen"]["live:gallery:f3"]
        self.assertIn("gvb-t-photo", s["cls"])
        self.assertIn("gvb-img--cover", s["img"]["cls"])
        self.assertIsNone(s["back"])
        self.assertNotIn("has-credit", s["caption"]["cls"].split())
        self.assertNotIn("gvb-credit", [x["cls"] for x in s["caption"]["parts"]])

    def test_no_picture_tells_googles_host_which_page_asked(self):
        for id_, s in self.r["seen"].items():
            with self.subTest(item=id_):
                self.assertEqual(s["img"]["ref"], "no-referrer")
                if s["back"]:
                    self.assertEqual(s["back"]["ref"], "no-referrer")
        # the pictures loaded ahead (the next slide's, while one shows) too
        self.assertTrue(self.r["warm"])
        for w in self.r["warm"]:
            with self.subTest(src=w["src"]):
                self.assertTrue(w["src"].startswith(LH3))
                self.assertEqual(w["ref"], "no-referrer")


# "Start the booth" on a laptop or desktop (round 32): the show in a window of its own. The About page's section (the
# note with its PIN line, three chips) and the dialog shell (Settings with one tab, the PIN box, "Leave?", the
# toast), the words the script needs, a pretend window.open (input.open: "window" → a pretend window — input.playing:
# one where the show plays already —, "blocked" → null) and a mouse that hovers (input.mouse); input.name /
# input.opener make this page the show's own window ("gvlv-booth", opened by https://example.test or another site);
# input.stored: this device's settings before; input.sw: a pretend service worker; input.bc: a pretend
# BroadcastChannel (the channel of the site's pages).
WIN_HTML = """
<section data-gvb-section>
  <div data-gvb-pv-frame><div data-gvb-still>Welcome</div></div>
  <input type="text" data-gvb-q="event">
  <button type="button" data-gvb-start>Start the booth</button>
  <button type="button" data-gvb-settings>Settings</button>
  <button type="button" data-gvb-preview>Preview here</button>
  <div data-gvb-pv-ctl hidden><button type="button" data-gvb-pv-act="pause"><svg></svg><span>Pause</span></button></div>
  <div data-gvb-win hidden role="status"><button type="button" data-gvb-win-act="focus">Show the window</button><button type="button" data-gvb-win-act="stop">Stop the show</button>
    <p data-gvb-win-pin hidden>Type the PIN in the show's window</p></div>
  <ul><li data-gvb-chip="items"><span></span></li><li data-gvb-chip="gallery" hidden><span></span></li><li data-gvb-chip="offline" hidden><span></span></li></ul>
</section>
<template id="gvb-tpl"><div class="gvb" role="dialog" aria-modal="true" tabindex="-1" data-gvb><div class="gvb-host" data-gvb-host></div>
  <aside class="gvb-drawer" data-gvb-drawer hidden><div data-gvb-tabs><button type="button" data-gvb-tab="event" aria-selected="false">Event</button></div>
    <div data-gvb-panel="event" hidden></div><button type="button" data-gvb-act="leave">Leave the show</button></aside>
  <div class="gvb-modal" data-gvb-pin hidden><form data-gvb-pin-form><p data-gvb-pin-why></p><input type="password" data-gvb-pin-input><p data-gvb-pin-err></p>
    <button type="submit">OK</button></form></div>
  <div class="gvb-modal" data-gvb-leave hidden><p id="gvb-leave-text">The show stops and this page comes back.</p>
    <button type="button" data-gvb-act="leave-yes">Leave</button><button type="button" data-gvb-act="leave-no">Keep playing</button></div>
  <div class="gvb-toast is-idle" data-gvb-toast role="status"></div></div></template>
<script type="application/json" id="gvb-config">__CFG__</script>
"""

WIN_JS = PAGE_JS + r"""
const cfg = { lang: "en", base: "/aagrapevine/", json: "/aagrapevine/about/booth.json", build: "/aagrapevine/build.json",
              t: { "booth.nav": "Booth display", "booth.popup_blocked": "The browser blocked the show's window",
                   "booth.leave_text_win": "The show stops and this window closes.", "booth.of_saving": "Saving {done} of {total} files" },
              screen: { en: { "booth.screen.tap_full": "Tap for full screen & sound", "booth.screen.tap_window": "Move this window, then tap" }, es: {} } };
const fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(input.show))), body: null });
const sent = [];                                       // what this page posted to the page that opened it
const closes = [];
const globals = { fetch, SITE: { lang: "en", base: "/aagrapevine/" } };
// input.sw: a pretend service worker (its MessageChannel answers BOOTH_STATUS: 2 of 3 files kept); every message
// type posted to it is listed (swPosted)
const swPosted = [];
if (input.sw) {
  const reg = { waiting: null, active: { postMessage(m, ports) {
    swPosted.push(m.type);
    if (m.type === "BOOTH_STATUS" && ports && ports[0]) ports[0].postMessage({ type: "BOOTH_STATUS", have: 2, total: 3, bytes: 100 });
  } } };
  globals.navigator = { serviceWorker: { ready: Promise.resolve(reg), controller: reg.active, getRegistration() { return Promise.resolve(reg); },
                                         addEventListener() {}, removeEventListener() {} } };
  globals.isSecureContext = true;
  globals.caches = {};
  globals.MessageChannel = function () {
    const ch = this;
    this.port1 = { onmessage: null };
    this.port2 = { postMessage(d) { Promise.resolve().then(() => { if (ch.port1.onmessage) ch.port1.onmessage({ data: d }); }); } };
  };
}
if (input.name) globals.name = input.name;
if (input.opener) globals.opener = { postMessage(m, o) { sent.push([JSON.parse(JSON.stringify(m)), o]); },
                                     get location() { if (input.opener !== "https://example.test") throw new Error("SecurityError"); return { origin: input.opener }; } };
globals.close = () => { closes.push(1); };
// input.bc: a pretend BroadcastChannel (the channel of this site's pages): what this page posts on it is listed
// (bus.posted); broadcast(data) is another page's — or the show's window's — message on it
const bus = { posted: [], chans: [] };
if (input.bc) globals.BroadcastChannel = function (name) {
  const ch = this;
  this.name = name;
  this.closed = false;
  this.onmessage = null;
  this.postMessage = (m) => { if (ch.closed) throw new Error("InvalidStateError"); bus.posted.push(JSON.parse(JSON.stringify(m))); };
  this.close = () => { ch.closed = true; };
  bus.chans.push(this);
};
const broadcast = (data) => bus.chans.filter((c) => !c.closed && c.onmessage).forEach((c) => c.onmessage({ data: JSON.parse(JSON.stringify(data)) }));
if (input.noStorage) globals.localStorage = { getItem() { throw new Error("SecurityError"); }, setItem() { throw new Error("SecurityError"); },
                                           removeItem() { throw new Error("SecurityError"); } };
const p = page({ html: input.html.replace("__CFG__", JSON.stringify(cfg)), url: "https://example.test/aagrapevine/about/" + (input.search || ""),
                 globals, scripts: ["src/assets/js/booth-core.js", "src/assets/js/booth.js"] });
const opened = [];
// the pretend window: window.open answers it (a blank one, at about:blank; input.playing: one where the show plays
// already, this site's page with the dialog in it; input.loading: one of that name caught loading the show again —
// F5 at the booth —, its dialog not drawn yet); location.replace sends it to an address (opened[…].nav) and the show
// plays in it (win.playing = false: its show went — a reload that failed); a window closed is a blank one next time
const SHOW_AT = "https://example.test/aagrapevine/about/?booth=start";
const win = { closed: false, focused: 0, got: [], navs: 0, playing: !!input.playing, focus() { this.focused += 1; },
              postMessage(m, o) { this.got.push([JSON.parse(JSON.stringify(m)), o]); }, close() { this.closed = true; },
              location: { origin: "https://example.test", href: input.playing || input.loading ? SHOW_AT : "about:blank",
                          replace(u) { win.navs += 1; opened[opened.length - 1].nav = u; win.location.href = u; win.playing = true; } },
              document: { querySelector(s) { return win.playing && s === "body > [data-gvb]" ? {} : null; } } };
p.win.open = (u, n, f) => {
  opened.push({ u, n, f, stored: (() => { try { return p.win.localStorage.getItem("gv-booth-v1"); } catch (e) { return null; } })() });
  if (input.open !== "window") return null;
  if (win.closed) Object.assign(win, { closed: false, playing: false }).location.href = "about:blank";
  return win;
};
if (input.mouse) p.win.matchMedia = (q) => ({ matches: q === "(hover: hover) and (pointer: fine)", media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
if (input.stored) p.win.localStorage.setItem("gv-booth-v1", JSON.stringify(input.stored));   // this device's settings before
const writes = [];
const ls = p.win.localStorage, set = ls.setItem, rem = ls.removeItem;
ls.setItem = (k, v) => { writes.push(k); return set(k, v); };
ls.removeItem = (k) => { writes.push(k); return rem(k); };
const state = () => ({ dialog: !!p.$("body > .gvb"), win: !p.$("[data-gvb-win]").hidden, opened: opened.length, focused: win.focused,
                       got: win.got.slice(), drawer: !!p.$("[data-gvb-drawer]") && !p.$("[data-gvb-drawer]").hidden,
                       toast: (p.$("[data-gvb-toast]") || { textContent: "" }).textContent, title: p.doc.title,
                       chip: (p.$('[data-gvb-chip="offline"] span') || { textContent: "" }).textContent,
                       tap: (p.$("[data-gvb-tapchip]") || { textContent: null }).textContent,
                       leaveText: (p.$("#gvb-leave-text") || { textContent: null }).textContent, sent: sent.slice(), closes: closes.length,
                       evName: (p.$(".gvb-event-name") || { textContent: null }).textContent, quick: p.$('[data-gvb-q="event"]').value,
                       address: p.win.location.pathname + p.win.location.search, sw: swPosted.slice(),
                       pin: !!p.$("[data-gvb-pin]") && !p.$("[data-gvb-pin]").hidden, pinWhy: (p.$("[data-gvb-pin-why]") || { textContent: null }).textContent,
                       locked: p.$('[data-gvb-q="event"]').disabled, pinLine: !p.$("[data-gvb-win-pin]").hidden, winClosed: win.closed,
                       bc: bus.posted.slice(), channels: bus.chans.map((c) => (c.closed ? "closed" : c.name)),
                       chips: Object.fromEntries(Array.from(p.doc.querySelectorAll("[data-gvb-chip]")).map((c) => [c.getAttribute("data-gvb-chip"), c.hidden ? null : c.querySelector("span").textContent])),
                       pageToast: (p.$("#gvb-page-toast") || { textContent: "" }).textContent,
                       preview: p.$("[data-gvb-pv-frame]").classList.contains("is-live") });
const message = (data, origin, source) => p.win.dispatchEvent(new p.win.Event("message", { data, origin, source }));
// the section scrolled into view: the page loads the show's file (its chips)
const seen = () => (p.win.__observers || []).filter((o) => o instanceof p.win.IntersectionObserver)
  .forEach((o) => o.cb(o.targets.map((t) => ({ target: t, isIntersecting: true }))));
const storage = (key, value) => { set(key, value); p.win.dispatchEvent(new p.win.Event("storage", { key, newValue: value })); };
await p.ready();
await p.tick(100);
const R = { start: state() };
"""


def run_win(case: unittest.TestCase, script: str, **data) -> dict:
    data.setdefault("html", WIN_HTML)
    data.setdefault("show", show([photo(1, first=True), photo(2), photo(3), photo(4)]))
    r = run_js(case, WIN_JS + script, data=data, needs_modules=False)
    case.assertEqual(r.get("errors"), [], r.get("errors"))
    return r


class OwnWindow(unittest.TestCase):
    """Round 32: on a laptop or desktop "Start the booth" opens the show in a window of its own (?booth=start in it,
    named gvlv-booth), the page says so and never starts a second show (also after a reload, and from another About
    tab, which hears the window over the channel of the site's pages and asks it there as it opens); a blocked
    window → the show on the page, said in a toast; a phone or tablet → the page, as before. The page borrows the
    window's offline save and connection and gives them back; a PIN guards the window from the page too. In the show's
    window: its own words, its pages told, what every page of this site asks done (also its first page's, after
    another tab took it), leaving closes it, &tab only from this site's page. Both windows hear the other's settings
    without writing them back."""

    def test_start_opens_the_window_and_the_page_says_so(self):
        r = run_win(self, r"""
const box = p.$('[data-gvb-q="event"]');
box.value = "Spring Assembly";
p.fire(box, "input");                                   // typed, then Start at once (inside the 300 ms)
p.click(p.$("[data-gvb-start]"));
R.after = state();
R.call = opened[0];
p.click(p.$("[data-gvb-start]"));                        // again: the window comes forward, no second show
R.again = state();
p.click(p.$("[data-gvb-settings]"));                     // Settings: opened in the window, on the Event tab
R.settings = state();
message({ gvb: "alive", off: { state: "saving", done: 3, total: 9, have: 0, all: 9, bytes: 0, ready: false, checked: true } }, "https://example.test", win);
R.alive = state();
message({ gvb: "bye" }, "https://another.test", win);  // another site's message: not heard
R.foreign = state();
message({ gvb: "bye" }, "https://example.test", win);
R.bye = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True)
        self.assertFalse(r["start"]["win"])
        call = r["call"]
        self.assertEqual(call["u"], "", "opened blank first (a window of that name playing already is handed back as it is)")
        self.assertEqual(call["nav"], "https://example.test/aagrapevine/about/?booth=start")     # no &bs: storage works
        self.assertEqual(call["n"], "gvlv-booth")
        self.assertRegex(call["f"], r"^popup,width=\d+,height=\d+,left=-?\d+,top=-?\d+$")
        self.assertNotIn("noopener", call["f"])
        self.assertEqual(json.loads(call["stored"])["event"]["en"], "Spring Assembly", "the name typed is kept before the window reads it")
        self.assertFalse(r["after"]["dialog"], "no show on the page")
        self.assertTrue(r["after"]["win"])
        self.assertEqual((r["again"]["opened"], r["again"]["focused"], r["again"]["dialog"]), (1, 1, False))
        self.assertEqual(r["settings"]["opened"], 1)
        self.assertEqual(r["settings"]["got"], [[{"gvb": "settings", "tab": "event"}, "https://example.test"]])
        self.assertFalse(r["settings"]["dialog"])
        self.assertEqual(r["alive"]["chip"], "Saving 3 of 9 files", "the chip follows the window's offline save")
        self.assertTrue(r["foreign"]["win"])
        self.assertFalse(r["bye"]["win"])
        self.assertFalse(r["bye"]["dialog"])

    def test_a_save_the_window_left_half_way_is_given_back(self):
        """The page borrowed the window's offline state ("Saving 3 of 9 files"); the window went before its save
        ended: the chip no longer says "Saving …", the worker is asked what it holds, and the page's own next show
        saves for offline (a borrowed "saving" would have made it wait for a save nobody runs)."""
        r = run_win(self, r"""
seen();                                                  // the section on screen: the page has the show's file
await p.tick(9000);
const asked = swPosted.length;
p.click(p.$("[data-gvb-start]"));
message({ gvb: "alive", off: { state: "saving", done: 3, total: 9, have: 0, all: 9, bytes: 0, ready: false, checked: true } }, "https://example.test", win);
R.alive = state();
R.aliveSw = swPosted.slice(asked);
message({ gvb: "bye" }, "https://example.test", win);   // stopped while its save runs
await p.tick(100);
R.bye = state();
R.byeSw = swPosted.slice(asked);
storage("gv-booth-v1", JSON.stringify({ ownWindow: false }));   // the next show on this page (Kiosk, in the other window)
await p.tick(50);
p.click(p.$("[data-gvb-start]"));
await p.tick(3000);
R.inPage = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, sw=True)
        self.assertEqual(r["alive"]["chip"], "Saving 3 of 9 files")
        self.assertEqual(r["aliveSw"], [], "the window saves, not the page")
        self.assertNotIn("Saving", r["bye"]["chip"])
        self.assertEqual(r["byeSw"], ["BOOTH_STATUS"], "the worker is asked what it holds now")
        self.assertTrue(r["inPage"]["dialog"])
        self.assertIn("BOOTH_SAVE", r["inPage"]["sw"], "the page's own show saves for offline")
        self.assertNotIn("Saving 3 of 9", r["inPage"]["chip"])

    def test_a_show_started_on_the_page_as_the_window_went_keeps_its_own_save(self):
        """The window closed with its ✕ and, before the page looked, a show started on the page (Kiosk's switch off):
        the page then ends the note, but the save that show runs stays its own — nothing given back over it."""
        r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));
win.closed = true;                                       // its ✕: the page looks every 2 s
storage("gv-booth-v1", JSON.stringify({ ownWindow: false }));
p.click(p.$("[data-gvb-start]"));                        // a show on this page now
await p.tick(500);
R.saving = state();
const asked = swPosted.length;
await p.tick(2000);                                      // the page looked: the note ends
R.after = state();
R.afterSw = swPosted.slice(asked);
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, sw=True)
        self.assertTrue(r["saving"]["dialog"])
        self.assertIn("BOOTH_SAVE", r["saving"]["sw"])
        self.assertFalse(r["after"]["win"])
        self.assertEqual(r["after"]["chip"], r["saving"]["chip"], "its save still says what it does")
        self.assertEqual(r["afterSw"], [], "nothing asked over it")

    def test_the_chips_follow_the_windows_connection(self):
        """The window's probe finds no internet (a venue's Wi-Fi without it: the browser still says online, and the
        page sends no probe of its own while the window plays): the page's chips say offline, and the Photos page's
        pictures (Google's copy) are not counted — they are not on the TV. Its own again when the show ends."""
        items = [photo(1, first=True), photo(2), gallery(1, "gallery-ours"), gallery(2, "gallery-gv"), gallery(3, "gallery-lv")]
        r = run_win(self, r"""
seen();
await p.tick(500);
R.before = state();
p.click(p.$("[data-gvb-start]"));
const off = { state: "done", done: 9, total: 9, have: 9, all: 9, bytes: 1000, ready: true, checked: true };
message({ gvb: "alive", off: Object.assign({ online: false }, off) }, "https://example.test", win);
await p.tick(0);
R.offline = state();
message({ gvb: "alive", off: Object.assign({ online: true }, off) }, "https://example.test", win);
await p.tick(0);
R.online = state();
message({ gvb: "alive", off: Object.assign({ online: false }, off) }, "https://example.test", win);
message({ gvb: "bye" }, "https://example.test", win);
await p.tick(0);
R.bye = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, show=show(items))
        self.assertIsNotNone(r["before"]["chips"]["gallery"])
        off = r["offline"]["chips"]
        self.assertIsNone(off["gallery"], "the pictures are not on the TV")
        self.assertTrue(off["offline"].startswith("booth.st_offline"), off["offline"])
        self.assertIsNotNone(r["online"]["chips"]["gallery"])
        self.assertFalse(r["online"]["chips"]["offline"].startswith("booth.st_offline"))
        self.assertIsNotNone(r["bye"]["chips"]["gallery"], "this page's own connection again")
        self.assertFalse((r["bye"]["chips"]["offline"] or "").startswith("booth.st_offline"))
        with self.subTest("the window says how it is"):
            r = run_win(self, "out(Object.assign(R, { errors: p.errors.map(String) }));", search="?booth=start", name="gvlv-booth",
                        opener="https://example.test", mouse=True)
            self.assertIs(r["start"]["sent"][0][0]["off"].get("online"), True)

    def test_a_window_closed_with_its_x_ends_the_note(self):
        r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));
R.after = state();
win.closed = true;                                       // its ✕: no "bye"
await p.tick(2100);
R.closed = state();
p.click(p.$("[data-gvb-start]"));                        // a new window then
R.next = state();
p.click(p.$('[data-gvb-win-act="stop"]'));              // "Stop the show": asked of the window, closed if it can't
R.stop = state();
await p.tick(3100);
R.forced = win.closed;
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True)
        self.assertTrue(r["after"]["win"])
        self.assertFalse(r["closed"]["win"])
        self.assertEqual(r["next"]["opened"], 2)
        self.assertTrue(r["next"]["win"])
        self.assertIn([{"gvb": "stop"}, "https://example.test"], r["stop"]["got"])
        self.assertTrue(r["forced"])

    def test_where_the_browser_keeps_no_settings_they_go_in_the_address(self):
        r = run_win(self, r"""
const box = p.$('[data-gvb-q="event"]');
box.value = "Spring Assembly";
p.fire(box, "input");
p.click(p.$("[data-gvb-start]"));
R.call = opened[0];
R.decoded = p.win.GVB.decode(decodeURIComponent(/[?&]bs=([^&#]+)/.exec(opened[0].nav)[1]));
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, noStorage=True)
        self.assertRegex(r["call"]["nav"], r"^https://example\.test/aagrapevine/about/\?booth=start&bs=[A-Za-z0-9_%-]+$")
        self.assertEqual(r["decoded"]["event"]["en"], "Spring Assembly")
        self.assertNotIn("pin", r["decoded"])

    def test_a_blocked_window_plays_the_show_on_the_page(self):
        r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.after = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="blocked", mouse=True)
        self.assertEqual(r["after"]["opened"], 1)
        self.assertTrue(r["after"]["dialog"], "blocked: the show plays on this page")
        self.assertFalse(r["after"]["win"])
        self.assertIn("The browser blocked the show's window", r["after"]["toast"])

    def test_a_window_playing_already_is_handed_back_as_it_is(self):
        """This page loaded again while its window plays (no handle, no message from it yet): Settings or Start find
        the window by its name and never load it again (the show would restart, out of full screen, muted)."""
        for button in ("settings", "start"):
            with self.subTest(button):
                r = run_win(self, r"""
p.click(p.$("[data-gvb-" + input.button + "]"));
await p.tick(0);
R.after = state();
R.call = opened[0];
R.navs = win.navs;
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, playing=True, button=button)
                self.assertEqual((r["call"]["u"], r["call"]["n"]), ("", "gvlv-booth"))
                self.assertEqual(r["navs"], 0, "never loaded again")
                self.assertNotIn("nav", r["call"])
                self.assertTrue(r["after"]["win"], "the page says the show plays in its window")
                self.assertFalse(r["after"]["dialog"])
                self.assertEqual(r["after"]["focused"], 1)
                self.assertEqual(r["after"]["got"], [[{"gvb": "settings", "tab": "event"}, "https://example.test"]] if button == "settings" else [])

    def test_settings_without_the_pin_only_in_the_blank_window_this_click_made(self):
        """The page's Settings opens Settings without the PIN (&tab=event) only in the blank window its click made. A
        window of that name caught loading again (F5 at the booth, its show not drawn yet — a page that has not heard
        it, e.g. loaded during that reload, clicks Settings) is sent to the show alone: a PIN set there is asked."""
        script = r"""
p.click(p.$("[data-gvb-settings]"));
await p.tick(0);
R.after = state();
R.call = opened[0];
R.navs = win.navs;
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        r = run_win(self, script, open="window", mouse=True)
        self.assertEqual(r["call"]["nav"], "https://example.test/aagrapevine/about/?booth=start&tab=event", "a blank window: Settings")
        self.assertTrue(r["after"]["win"])
        r = run_win(self, script, open="window", mouse=True, loading=True, stored={"pin": "1234"})
        self.assertEqual((r["call"]["u"], r["call"]["n"]), ("", "gvlv-booth"))
        self.assertEqual(r["call"]["nav"], "https://example.test/aagrapevine/about/?booth=start", "caught loading: the show alone, its PIN kept")
        self.assertEqual(r["navs"], 1)
        self.assertTrue(r["after"]["win"], "the page says the show plays in its window")
        self.assertEqual(r["after"]["got"], [], "nothing asked of a page that is not there yet")
        self.assertFalse(r["after"]["dialog"])

    def test_a_window_left_without_a_show_ends_the_note(self):
        """The page holds the window's handle. F5 at the booth: the old page's "bye" as it goes comes with no source
        (not heard) and its copy over the channel is not taken (the window spoke a moment ago); the new page says
        hello within a second or two — the note stays. A reload that fails (booth.js does not load, the browser's
        error page) leaves the window open with no show and nothing more is said: once it has been quiet 12 s the
        note ends (with a PIN, the quick controls open again) and Start loads the show in that window again."""
        r = run_win(self, r"""
const PIN = { state: "idle" };
const reload = () => { win.playing = false; message({ gvb: "bye" }, "https://example.test", null); broadcast({ gvb: "bye" }); };
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
message({ gvb: "hello", off: PIN, pin: true }, "https://example.test", win);
await p.tick(5000);
message({ gvb: "alive", off: PIN, pin: true }, "https://example.test", win);
await p.tick(4900);
reload();                                                // F5, just before its next "alive"
await p.tick(2100);                                      // (the page looked while it loads)
R.loading = state();
win.playing = true;
message({ gvb: "hello", off: PIN, pin: true }, "https://example.test", win);
for (let i = 0; i < 3; i += 1) { await p.tick(5000); message({ gvb: "alive", off: PIN, pin: true }, "https://example.test", win); }
await p.tick(0);
R.reloaded = state();
reload();                                                // F5 again, and this time its show never comes
await p.tick(10100);
R.waiting = state();
await p.tick(4000);                                      // 12 s quiet (the page looks every 2 s)
R.quiet = state();
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.again = state();
R.navs = win.navs;
R.nav = opened[opened.length - 1].nav;
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, bc=True, stored={"pin": "1234"})
        for step in ("loading", "reloaded", "waiting"):
            with self.subTest(step):
                self.assertTrue(r[step]["win"], "the note stays")
                self.assertTrue(r[step]["locked"])
        q = r["quiet"]
        self.assertFalse(q["win"], "quiet for 12 s with no show in it: the show ended")
        self.assertFalse(q["locked"], "the quick controls open again")
        self.assertFalse(q["pinLine"])
        a = r["again"]
        self.assertEqual((a["opened"], r["navs"]), (2, 2), "Start loads the show in that window again")
        self.assertEqual(r["nav"], "https://example.test/aagrapevine/about/?booth=start")
        self.assertTrue(a["win"])
        self.assertFalse(a["dialog"])

    def test_a_touch_screen_never_opens_a_window(self):
        # (fakedom's matchMedia answers no: a phone or tablet — no mouse that hovers)
        r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.after = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=False)
        self.assertEqual(r["after"]["opened"], 0)
        self.assertTrue(r["after"]["dialog"])
        self.assertFalse(r["after"]["win"])
        self.assertEqual(r["after"]["toast"], "")

    def test_in_its_own_window_the_show_says_so_tells_its_page_and_leaving_closes_it(self):
        r = run_win(self, r"""
await p.tick(5000);
R.later = state();
p.key(p.doc.body, "Escape");                             // Esc → "Leave?" → Leave
await p.tick(0);
R.asked = state();
p.click(p.$('[data-gvb-act="leave-yes"]'));
await p.tick(0);
R.left = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True, open="window")
        s = r["start"]
        self.assertTrue(s["dialog"])
        self.assertEqual(s["title"], "Booth display — NETA 65")
        self.assertEqual(s["tap"], "Move this window, then tap")
        self.assertEqual(s["leaveText"], "The show stops and this window closes.")
        self.assertEqual(s["sent"][0][0]["gvb"], "hello")
        self.assertEqual(s["sent"][0][1], "https://example.test")
        self.assertIn("off", s["sent"][0][0])
        kinds = [m[0]["gvb"] for m in r["later"]["sent"]]
        self.assertEqual(kinds[0], "hello")
        self.assertIn("alive", kinds)
        self.assertEqual(r["later"]["opened"], 0, "the show's window never opens another one")
        self.assertTrue(r["asked"]["dialog"])
        self.assertFalse(r["left"]["dialog"])
        self.assertEqual(r["left"]["closes"], 1, "leaving closes the show's window")
        self.assertEqual(r["left"]["sent"][-1][0], {"gvb": "bye"})
        self.assertEqual(r["left"]["address"], "/aagrapevine/about/")

    def test_a_start_address_opened_by_hand_stays_as_it_was(self):
        r = run_win(self, r"""
p.key(p.doc.body, "Escape");
await p.tick(0);
p.click(p.$('[data-gvb-act="leave-yes"]'));
await p.tick(0);
R.left = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", search="?booth=start", mouse=True, open="window")
        s = r["start"]
        self.assertTrue(s["dialog"])
        self.assertEqual(s["tap"], "Tap for full screen & sound")
        self.assertEqual(s["leaveText"], "The show stops and this page comes back.")
        self.assertEqual((s["sent"], r["left"]["closes"], r["left"]["opened"]), ([], 0, 0))
        self.assertFalse(r["left"]["dialog"])

    def test_the_settings_tab_only_from_this_sites_page(self):
        cases = {"window opened by the page": ({"name": "gvlv-booth", "opener": "https://example.test"}, True),
                 "the window, no page behind it": ({"name": "gvlv-booth"}, False),
                 "the window, opened by another site": ({"name": "gvlv-booth", "opener": "https://another.test"}, False),
                 "a typed address": ({"opener": "https://example.test"}, False)}
        for label, (extra, drawer) in cases.items():
            with self.subTest(label):
                r = run_win(self, "out(Object.assign(R, { errors: p.errors.map(String) }));", search="?booth=start&tab=event", mouse=True, **extra)
                self.assertTrue(r["start"]["dialog"])
                self.assertEqual(r["start"]["drawer"], drawer)
                # read once: the window keeps its name and opener through a reload, so &tab leaves the address
                # (a reload restarts the show, never Settings without the PIN)
                self.assertEqual(r["start"]["address"], "/aagrapevine/about/?booth=start")
        with self.subTest("a setup in the address stays"):
            r = run_win(self, "out(Object.assign(R, { errors: p.errors.map(String) }));", search="?booth=start&tab=event&bs=xyz",
                        name="gvlv-booth", opener="https://example.test", mouse=True)
            self.assertEqual(r["start"]["address"], "/aagrapevine/about/?booth=start&bs=xyz")

    def test_preview_here_while_the_window_plays_brings_the_window_forward(self):
        r = run_win(self, r"""
const live = () => ({ live: p.$("[data-gvb-pv-frame]").classList.contains("is-live"), ctl: !p.$("[data-gvb-pv-ctl]").hidden,
                      pressed: p.$("[data-gvb-preview]").getAttribute("aria-pressed") === "true" });
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
p.click(p.$("[data-gvb-preview]"));
await p.tick(100);
R.during = Object.assign(state(), live());
win.closed = true;                                       // its ✕, before the page's next look: the preview may play
p.click(p.$("[data-gvb-preview]"));
await p.tick(100);
R.after = Object.assign(state(), live());
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True)
        d = r["during"]
        self.assertEqual((d["opened"], d["focused"]), (1, 1), "the window comes forward")
        self.assertEqual((d["live"], d["ctl"], d["pressed"]), (False, False, False), "no second show in the card")
        self.assertTrue(d["win"])
        a = r["after"]
        self.assertFalse(a["win"])
        self.assertEqual((a["live"], a["ctl"], a["pressed"]), (True, True, True))

    def test_the_page_asks_the_window_for_settings_or_to_stop(self):
        r = run_win(self, r"""
message({ gvb: "settings", tab: "event" }, "https://another.test", globals.opener);   // another site's page
let own = null;                                           // (the window as its own script sees it)
p.win.addEventListener("gvb-self", (e) => { own = e.target; });
p.win.dispatchEvent(new p.win.Event("gvb-self"));
message({ gvb: "settings", tab: "event" }, "https://example.test", own);                // its own word
await p.tick(0);
R.stranger = state();
R.own = !!own;
message({ gvb: "settings", tab: "event" }, "https://example.test", globals.opener);
await p.tick(0);
R.settings = state();
message({ gvb: "stop" }, "https://example.test", globals.opener);
await p.tick(0);
R.stop = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True)
        self.assertTrue(r["own"])
        self.assertFalse(r["stranger"]["drawer"], "never another site's page, nor the window's own word")
        self.assertTrue(r["settings"]["drawer"], "the page's Settings button opens them in the window, no PIN")
        self.assertFalse(r["settings"]["pin"])
        self.assertFalse(r["stop"]["dialog"])
        self.assertEqual(r["stop"]["closes"], 1)
        self.assertIs(r["start"]["sent"][0][0].get("pin"), False, "the page hears no PIN guards the show")

    def test_the_window_does_what_every_page_of_this_site_asks_also_after_another_tab_took_it(self):
        """Edge and Chrome make the last tab that opens the window by its name its opener (an About tab that page
        opened, before it heard the window): the page that opened it still holds its handle and asks it by
        postMessage — its Settings and Stop are still done (with the same PIN rule), while the window's word goes to
        its new opener and over the channel."""
        script = r"""
const first = globals.opener;
const took = [];
p.win.opener = { postMessage(m) { took.push(JSON.parse(JSON.stringify(m))); }, location: { origin: "https://example.test" } };
message({ gvb: "settings", tab: "event" }, "https://example.test", first);
await p.tick(0);
R.settings = state();
p.key(p.doc.body, "Escape");
await p.tick(5000);
R.later = state();
R.took = took.slice();
message({ gvb: "stop" }, "https://example.test", first);
await p.tick(3100);
R.stop = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        r = run_win(self, script, search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True, bc=True)
        self.assertTrue(r["settings"]["drawer"], "the page that opened it is still heard")
        self.assertIn("alive", [m["gvb"] for m in r["took"]], "the window's word goes to its new opener")
        self.assertIn("alive", [m["gvb"] for m in r["later"]["bc"]], "… and over the channel (the first page hears it there)")
        self.assertEqual(len(r["later"]["sent"]), 1, "only its hello reached the first page by postMessage")
        self.assertFalse(r["stop"]["dialog"])
        self.assertEqual(r["stop"]["closes"], 1)
        with self.subTest("a PIN set"):
            r = run_win(self, script, search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True, bc=True,
                        stored={"pin": "1234"})
            self.assertTrue(r["settings"]["pin"], "the PIN box")
            self.assertFalse(r["settings"]["drawer"])
            self.assertTrue(r["stop"]["dialog"], "the show plays on")
            self.assertTrue(r["stop"]["pin"])
            self.assertEqual(r["stop"]["closes"], 0)

    def test_with_a_pin_the_window_asks_for_it_whatever_its_page_asks(self):
        """A PIN set (Settings → Kiosk): the page's Settings and Stop bring up the window's PIN box, as its own keys
        do — never Settings (and "Remove the PIN") or leaving without it."""
        r = run_win(self, r"""
const from = globals.opener;
const typePin = (v) => { const i = p.$("[data-gvb-pin-input]"); if (!i) return; i.value = v; p.fire(p.$("[data-gvb-pin-form]"), "submit"); };
message({ gvb: "settings", tab: "event" }, "https://example.test", from);
await p.tick(0);
R.settings = state();
typePin("1234");                                         // the PIN typed: Settings open
await p.tick(0);
R.typed = state();
message({ gvb: "settings", tab: "event" }, "https://example.test", from);   // Settings open already: no PIN again
await p.tick(0);
R.again = state();
p.key(p.doc.body, "Escape");                             // Settings closed
await p.tick(0);
message({ gvb: "stop" }, "https://example.test", from);
await p.tick(0);
R.stop = state();
message({ gvb: "stop" }, "https://example.test", from);  // asked again while the PIN box is up: it stays as it is
await p.tick(3100);
R.stopAgain = state();
typePin("1234");                                         // the PIN typed: the show leaves, the window closes
await p.tick(0);
R.left = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True, stored={"pin": "1234"})
        s = r["settings"]
        self.assertTrue(s["pin"], "the PIN box")
        self.assertEqual(s["pinWhy"], "booth.pin_for_settings")
        self.assertFalse(s["drawer"])
        self.assertTrue(r["typed"]["drawer"])
        self.assertTrue(r["again"]["drawer"])
        self.assertFalse(r["again"]["pin"])
        st = r["stop"]
        self.assertTrue(st["dialog"], "the show plays on")
        self.assertTrue(st["pin"])
        self.assertEqual(st["pinWhy"], "booth.pin_for_leave")
        self.assertEqual(st["closes"], 0)
        self.assertTrue(r["stopAgain"]["dialog"])
        self.assertEqual(r["stopAgain"]["closes"], 0)
        self.assertFalse(r["left"]["dialog"])
        self.assertEqual(r["left"]["closes"], 1)
        self.assertIs(r["start"]["sent"][0][0].get("pin"), True, "the page hears a PIN guards the show (never the PIN)")
        self.assertNotIn("1234", json.dumps(r["start"]["sent"]))

    def test_a_pin_box_already_up_keeps_its_ask(self):
        """Two asks from the page while the window's PIN box is up: the box stays as it is — its line and the digits
        typed in it — and the PIN does what was asked first, as for the show's own keys (S is not heard while the
        box that leaves is up). Stop then Settings: the PIN leaves (Settings never take over the box that leaves).
        Settings then Stop: the PIN opens Settings and the show plays on; a Stop after that brings the box that
        leaves."""
        script = r"""
const from = globals.opener;
const ask = (m) => message(m, "https://example.test", from);
const typed = () => (p.$("[data-gvb-pin-input]") || { value: null }).value;
const typePin = (v) => { const i = p.$("[data-gvb-pin-input]"); if (!i) return; i.value = v; p.fire(p.$("[data-gvb-pin-form]"), "submit"); };
const first = input.first, then = first.gvb === "stop" ? { gvb: "settings", tab: "event" } : { gvb: "stop" };
ask(first);
await p.tick(0);
R.first = state();
if (p.$("[data-gvb-pin-input]")) p.$("[data-gvb-pin-input]").value = "12";     // half typed
ask(then);
await p.tick(0);
R.then = Object.assign(state(), { typed: typed() });
typePin("1234");
await p.tick(0);
R.pin = state();
if (first.gvb === "settings") {
  ask({ gvb: "stop" });                                  // Settings open now, no box: Stop asks for the PIN that leaves
  await p.tick(0);
  R.stop = state();
  typePin("1234");
  await p.tick(0);
  R.left = state();
}
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        for first in ({"gvb": "stop"}, {"gvb": "settings", "tab": "event"}):
            with self.subTest(first=first["gvb"]):
                r = run_win(self, script, search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True,
                            stored={"pin": "1234"}, first=first)
                why = "booth.pin_for_leave" if first["gvb"] == "stop" else "booth.pin_for_settings"
                self.assertEqual((r["first"]["pin"], r["first"]["pinWhy"]), (True, why))
                t = r["then"]
                self.assertEqual((t["pin"], t["pinWhy"], t["typed"]), (True, why, "12"), "the box stays as it was")
                self.assertFalse(t["drawer"])
                self.assertEqual((t["dialog"], t["closes"]), (True, 0))
                if first["gvb"] == "stop":
                    self.assertFalse(r["pin"]["dialog"], "the PIN typed to stop leaves")
                    self.assertFalse(r["pin"]["drawer"])
                    self.assertEqual(r["pin"]["closes"], 1)
                else:
                    self.assertTrue(r["pin"]["drawer"], "the PIN opens Settings")
                    self.assertEqual((r["pin"]["dialog"], r["pin"]["closes"]), (True, 0), "the show plays on")
                    self.assertEqual((r["stop"]["pin"], r["stop"]["pinWhy"]), (True, "booth.pin_for_leave"))
                    self.assertEqual((r["left"]["dialog"], r["left"]["closes"]), (False, 1))

    def test_with_a_pin_the_page_never_stops_or_changes_the_window_without_it(self):
        """The page beside a window playing behind a PIN: its quick controls wait (the note says the window asks for
        the PIN), and "Stop the show" never closes the window itself — open again when the PIN goes or the show ends.
        The window's own word counts too (a browser that keeps no settings has its PIN only there)."""
        script = r"""
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.on = state();
p.click(p.$('[data-gvb-win-act="stop"]'));
await p.tick(3100);
R.stop = state();
storage("gv-booth-v1", JSON.stringify({}));              // the PIN removed (in the window's Settings)
await p.tick(0);
R.removed = state();
message({ gvb: "alive", pin: true, off: {} }, "https://example.test", win);    // the window: a PIN guards it
await p.tick(0);
R.saysPin = state();
message({ gvb: "alive", pin: false, off: {} }, "https://example.test", win);
await p.tick(0);
R.saysNone = state();
message({ gvb: "alive", pin: true, off: {} }, "https://example.test", win);
message({ gvb: "bye" }, "https://example.test", win);
await p.tick(0);
R.bye = state();
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
p.click(p.$('[data-gvb-win-act="stop"]'));
await p.tick(3100);
R.stopNoPin = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        r = run_win(self, script, open="window", mouse=True, stored={"pin": "1234"})
        self.assertTrue(r["on"]["win"])
        self.assertTrue(r["on"]["locked"], "the quick controls wait")
        self.assertTrue(r["on"]["pinLine"], "the note says the window asks for the PIN")
        self.assertIn([{"gvb": "stop"}, "https://example.test"], r["stop"]["got"])
        self.assertFalse(r["stop"]["winClosed"], "never closed under its PIN box")
        self.assertTrue(r["stop"]["win"])
        self.assertFalse(r["removed"]["locked"])
        self.assertFalse(r["removed"]["pinLine"])
        self.assertTrue(r["saysPin"]["locked"])
        self.assertTrue(r["saysPin"]["pinLine"])
        self.assertFalse(r["saysNone"]["locked"])
        self.assertFalse(r["bye"]["win"])
        self.assertFalse(r["bye"]["locked"], "open again when the show ends")
        self.assertFalse(r["bye"]["pinLine"])
        self.assertTrue(r["stopNoPin"]["winClosed"], "no PIN: a window that does not answer is closed")
        with self.subTest("no PIN"):
            r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.on = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True)
            self.assertTrue(r["on"]["win"])
            self.assertFalse(r["on"]["locked"])
            self.assertFalse(r["on"]["pinLine"])

    def test_another_page_hears_the_window_over_the_channel_and_starts_no_second_show(self):
        """Another About tab (a bookmark, a typed address: the browser finds a window by its name only among those its
        own tab's group opened) has no handle on the window: it hears it over the channel of this site's pages, shows
        the note while the window says it plays, and asks it there — Start, Settings, "Preview here", Stop open no
        second window and no second show."""
        r = run_win(self, r"""
const off = { state: "done", done: 9, total: 9, have: 9, all: 9, bytes: 1000, ready: true, checked: true };
broadcast({ gvb: "hello", off, pin: false });
await p.tick(0);
R.hello = state();
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.start = state();
p.click(p.$("[data-gvb-settings]"));
await p.tick(0);
R.settings = state();
p.click(p.$("[data-gvb-preview]"));
await p.tick(100);
R.preview = state();
p.click(p.$('[data-gvb-win-act="stop"]'));
await p.tick(3100);
R.stop = state();
await p.tick(11000);                                     // the window silent (no "alive") for more than 12 s
R.silent = state();
broadcast({ gvb: "alive", off, pin: true });
await p.tick(0);
R.alive = state();
broadcast({ gvb: "settings", tab: "event" });            // another page asking the window: not for a page
broadcast({ gvb: "stop" });
await p.tick(0);
R.others = state();
broadcast({ gvb: "bye" });
await p.tick(0);
R.bye = state();
p.click(p.$("[data-gvb-start]"));                        // nothing plays now: this page opens the window
await p.tick(0);
R.after = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, bc=True)
        self.assertTrue(r["hello"]["win"], "the note: the show plays in its own window")
        self.assertEqual(r["hello"]["chip"], "booth.st_ready", "the chips follow the window's offline copy")
        st = r["start"]
        self.assertEqual(st["opened"], 0, "no second window")
        self.assertFalse(st["dialog"], "no show on this page")
        self.assertEqual(st["bc"], [{"gvb": "ping"}, {"gvb": "focus"}], "the window is asked to come forward (its ping as the page opened)")
        self.assertEqual(st["pageToast"], "booth.popup_on")
        self.assertEqual(st["channels"], ["gvlv-booth"])
        self.assertEqual(r["settings"]["opened"], 0)
        self.assertEqual(r["settings"]["bc"][-1], {"gvb": "settings", "tab": "event"})
        self.assertFalse(r["preview"]["preview"], "no second show in the card")
        self.assertEqual(r["preview"]["bc"][-1], {"gvb": "focus"})
        self.assertEqual(r["stop"]["bc"][-1], {"gvb": "stop"})
        self.assertEqual(r["stop"]["got"], [], "one way only: no handle, no postMessage")
        self.assertTrue(r["stop"]["win"], "until the window says it ended")
        self.assertFalse(r["silent"]["win"], "a window silent for long is gone")
        self.assertTrue(r["alive"]["win"])
        self.assertTrue(r["alive"]["locked"], "a PIN guards it: the quick controls wait")
        self.assertTrue(r["others"]["win"])
        self.assertEqual(r["others"]["bc"], r["alive"]["bc"], "a page never answers another page's asks")
        self.assertFalse(r["bye"]["win"])
        self.assertFalse(r["bye"]["locked"])
        self.assertEqual(r["after"]["opened"], 1)
        self.assertTrue(r["after"]["win"])

    def test_the_page_with_the_windows_handle_hears_it_and_asks_it_one_way_only(self):
        """The page that opened the window hears it by postMessage and asks it so: the window's word over the channel
        changes nothing there, and nothing is asked twice."""
        r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
broadcast({ gvb: "alive", off: { state: "saving", done: 3, total: 9, have: 0, all: 9, bytes: 0, ready: false, checked: true }, pin: true });
await p.tick(0);
R.channel = state();
p.click(p.$("[data-gvb-settings]"));
p.click(p.$('[data-gvb-win-act="stop"]'));
await p.tick(0);
R.asked = state();
broadcast({ gvb: "bye" });
await p.tick(0);
R.bye = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, bc=True)
        self.assertNotEqual(r["channel"]["chip"], "Saving 3 of 9 files")
        self.assertFalse(r["channel"]["locked"])
        self.assertEqual(r["asked"]["got"], [[{"gvb": "settings", "tab": "event"}, "https://example.test"], [{"gvb": "stop"}, "https://example.test"]])
        self.assertEqual(r["asked"]["bc"], [{"gvb": "ping"}], "never over the channel too (only its ping as it opened)")
        self.assertTrue(r["bye"]["win"], "its own window said nothing: still playing")

    def test_the_page_with_the_handle_hears_the_channel_once_its_window_says_nothing_to_it(self):
        """Another tab took the window (Edge and Chrome: the last tab that opens it by its name is its opener): the
        page that opened it holds its handle but hears nothing from it by postMessage — after 12 s of that it takes
        the window's word over the channel (the chips, the PIN), and its "bye" ends the note."""
        r = run_win(self, r"""
const saving = { state: "saving", done: 3, total: 9, have: 0, all: 9, bytes: 0, ready: false, checked: true };
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
message({ gvb: "hello", off: {}, pin: false }, "https://example.test", win);
await p.tick(11000);
broadcast({ gvb: "alive", off: saving, pin: true });    // its window spoke to it 11 s ago: not yet
await p.tick(0);
R.soon = state();
await p.tick(1100);                                     // 12 s without a word by postMessage, its handle still open
R.silent = state();
broadcast({ gvb: "alive", off: saving, pin: true });
await p.tick(0);
R.channel = state();
broadcast({ gvb: "bye" });
await p.tick(0);
R.bye = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, bc=True)
        self.assertNotEqual(r["soon"]["chip"], "Saving 3 of 9 files")
        self.assertFalse(r["soon"]["locked"])
        self.assertTrue(r["silent"]["win"], "its handle is open: still playing")
        self.assertEqual(r["channel"]["chip"], "Saving 3 of 9 files", "the window's word, over the channel")
        self.assertTrue(r["channel"]["locked"])
        self.assertFalse(r["bye"]["win"])
        self.assertEqual(r["bye"]["got"], [], "nothing asked")

    def test_a_page_asks_the_window_at_once_as_it_opens(self):
        """A page asks over the channel as it opens ("ping", also back from the back/forward cache) and the show's
        window answers "alive" then and there — a Start a moment after the page opened starts no second show; the
        window itself never asks, and says nothing once its show ended."""
        r = run_win(self, r"""
p.fire(p.win, "pagehide");
p.fire(p.win, "pageshow", { persisted: true });
R.back = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", mouse=True, bc=True)
        self.assertEqual(r["start"]["bc"], [{"gvb": "ping"}])
        self.assertEqual(r["back"]["bc"], [{"gvb": "ping"}, {"gvb": "ping"}])
        self.assertFalse(r["start"]["win"], "a ping is no word of the window")
        r = run_win(self, r"""
broadcast({ gvb: "ping" });                            // a page just opened (the window's next "alive" is 5 s away)
await p.tick(0);
R.ping = state();
broadcast({ gvb: "stop" });
await p.tick(0);
broadcast({ gvb: "ping" });                            // its show ended: nothing to say
await p.tick(0);
R.ended = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True, bc=True)
        self.assertEqual([m["gvb"] for m in r["start"]["bc"]], ["hello"], "the window never pings")
        alive = r["ping"]["bc"][-1]
        self.assertEqual(alive["gvb"], "alive", "answered at once")
        self.assertIs(alive["pin"], False)
        self.assertIn("off", alive)
        self.assertEqual([m[0]["gvb"] for m in r["ping"]["sent"]], ["hello", "alive"])
        self.assertTrue(r["ping"]["dialog"], "a ping changes nothing in the show")
        self.assertEqual([m["gvb"] for m in r["ended"]["bc"]], ["hello", "alive", "bye"])

    def test_a_page_that_only_hears_the_window_says_where_the_show_is(self):
        """A page that only hears the window over the channel cannot bring it forward itself (it asks it to, and the
        browser may not let a message do it): "Show the window", "Preview here" and Start each say in a toast that
        the show plays in its own window."""
        r = run_win(self, r"""
const off = { state: "done", done: 9, total: 9, have: 9, all: 9, bytes: 1000, ready: true, checked: true };
broadcast({ gvb: "hello", off, pin: false });
await p.tick(0);
p.click(p.$('[data-gvb-win-act="focus"]'));
await p.tick(0);
R.show = state();
await p.tick(5100);                                     // the toast gone; the window's next "alive"
R.gone = state();
broadcast({ gvb: "alive", off, pin: false });
p.click(p.$("[data-gvb-preview]"));
await p.tick(100);
R.preview = state();
await p.tick(5100);
broadcast({ gvb: "alive", off, pin: false });
p.click(p.$("[data-gvb-start]"));
await p.tick(0);
R.start = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=True, bc=True)
        for step in ("show", "preview", "start"):
            with self.subTest(step):
                s = r[step]
                self.assertEqual(s["bc"][-1], {"gvb": "focus"})
                self.assertEqual(s["pageToast"], "booth.popup_on")
                self.assertEqual(s["opened"], 0)
                self.assertTrue(s["win"])
                self.assertFalse(s["preview"])
        self.assertEqual(r["gone"]["pageToast"], "")

    def test_a_page_playing_its_own_show_keeps_its_own_state(self):
        r = run_win(self, r"""
p.click(p.$("[data-gvb-start]"));                        // a touch screen: the show on this page
await p.tick(100);
broadcast({ gvb: "alive", off: { state: "saving", done: 3, total: 9, have: 0, all: 9, bytes: 0, ready: false, checked: true }, pin: true });
await p.tick(0);
R.after = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", open="window", mouse=False, bc=True)
        self.assertTrue(r["after"]["dialog"])
        self.assertFalse(r["after"]["win"])
        self.assertNotEqual(r["after"]["chip"], "Saving 3 of 9 files")

    def test_in_its_own_window_the_show_talks_to_every_page_over_the_channel_too(self):
        """The show's window says hello / alive / bye over the channel as well (also when the page that opened it
        is gone), and does what another page asks there — with the same PIN rule as its opener's asks."""
        script = r"""
await p.tick(5000);
R.later = state();
broadcast({ gvb: "hello", off: {} });                    // another window's word: not an ask
broadcast({ gvb: "settings", tab: "event" });
await p.tick(0);
R.settings = state();
p.key(p.doc.body, "Escape");
await p.tick(0);
broadcast({ gvb: "focus" });
broadcast({ gvb: "stop" });
await p.tick(0);
R.stop = state();
p.fire(p.win, "pagehide");
R.hidden = state();
p.fire(p.win, "pageshow", { persisted: true });          // back from the back/forward cache: the channel again
R.back = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        for label, extra in {"opened by the page": {"opener": "https://example.test"}, "its page closed": {}}.items():
            with self.subTest(label):
                r = run_win(self, script, search="?booth=start", name="gvlv-booth", mouse=True, bc=True, **extra)
                hello = r["start"]["bc"][0]
                self.assertEqual(hello["gvb"], "hello")
                self.assertIn("off", hello)
                self.assertIs(hello["pin"], False)
                self.assertIn("alive", [m["gvb"] for m in r["later"]["bc"]])
                self.assertEqual(len(r["start"]["sent"]), 1 if extra else 0)
                self.assertTrue(r["settings"]["drawer"], "Settings, asked over the channel (no PIN set)")
                self.assertFalse(r["stop"]["dialog"])
                self.assertEqual(r["stop"]["closes"], 1)
                self.assertEqual(r["stop"]["bc"][-1], {"gvb": "bye"})
                self.assertEqual(r["hidden"]["channels"], ["closed"])
                self.assertEqual(r["back"]["channels"], ["closed", "gvlv-booth"])
        with self.subTest("a PIN set"):
            r = run_win(self, r"""
broadcast({ gvb: "settings", tab: "event" });
await p.tick(0);
R.settings = state();
p.key(p.doc.body, "Escape");
await p.tick(0);
broadcast({ gvb: "stop" });
await p.tick(3100);
R.stop = state();
out(Object.assign(R, { errors: p.errors.map(String) }));
""", search="?booth=start", name="gvlv-booth", mouse=True, bc=True, stored={"pin": "1234"})
            self.assertTrue(r["settings"]["pin"])
            self.assertFalse(r["settings"]["drawer"])
            self.assertTrue(r["stop"]["dialog"])
            self.assertTrue(r["stop"]["pin"])
            self.assertEqual(r["stop"]["closes"], 0)

    def test_settings_changed_in_the_other_window_are_read_not_written_back(self):
        script = r"""
const before = writes.length;
storage("gv-booth-v1", JSON.stringify({ event: { en: "Fall ACM" } }));
await p.tick(0);
R.after = state();
R.written = writes.slice(before).filter((k) => k === "gv-booth-v1");
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        page_ = run_win(self, script, mouse=True)
        self.assertEqual(page_["after"]["quick"], "Fall ACM", "the page's quick controls follow the window's Settings")
        self.assertEqual(page_["written"], [])
        shown = run_win(self, script, search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True)
        self.assertTrue(shown["after"]["dialog"])
        self.assertEqual(shown["after"]["evName"], "Fall ACM", "the page's quick controls change the show as it plays")
        self.assertEqual(shown["written"], [])

    def test_a_name_given_in_the_other_window_reaches_a_field_left_with_the_focus(self):
        """The event's name changed in the other window reaches a field that still holds the focus here once this
        window is not the one in use (its next key would write the old name back) — the page's quick field, and the
        show window's Settings → Event; while this window is typed in, the field keeps what is being typed."""
        page_script = r"""
const box = p.$('[data-gvb-q="event"]');
box.value = "Spring Assembly";
p.fire(box, "input");
await p.tick(400);
box.focus();
storage("gv-booth-v1", JSON.stringify({ event: { en: "Fall ACM" } }));   // this window in use: kept as typed
await p.tick(0);
R.typing = state();
p.doc.hasFocus = () => false;                            // the focus went to the show's window, left in the field
storage("gv-booth-v1", JSON.stringify({ event: { en: "Fall ACM 2026" } }));
await p.tick(0);
R.away = state();
R.active = p.doc.activeElement === box;
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        r = run_win(self, page_script, mouse=True)
        self.assertEqual(r["typing"]["quick"], "Spring Assembly")
        self.assertTrue(r["active"])
        self.assertEqual(r["away"]["quick"], "Fall ACM 2026")
        window_script = r"""
message({ gvb: "settings", tab: "event" }, "https://example.test", globals.opener);
await p.tick(0);
const field = () => p.$('[data-gvb-panel="event"] [data-gvb-key="ev-en"]');
field().focus();
storage("gv-booth-v1", JSON.stringify({ event: { en: "Winter Workshop" } }));   // this window in use: kept
await p.tick(0);
R.typing = field().value;
p.doc.hasFocus = () => false;                            // the page is the one in use
storage("gv-booth-v1", JSON.stringify({ event: { en: "Winter Workshop 2026" } }));
await p.tick(0);
R.away = field().value;
R.focusKept = p.doc.activeElement === field();
R.drawer = state().drawer;
out(Object.assign(R, { errors: p.errors.map(String) }));
"""
        r = run_win(self, window_script, search="?booth=start", name="gvlv-booth", opener="https://example.test", mouse=True)
        self.assertTrue(r["drawer"])
        self.assertEqual(r["typing"], "")
        self.assertEqual(r["away"], "Winter Workshop 2026")
        self.assertTrue(r["focusKept"], "drawn again, the focus where it was")


if __name__ == "__main__":
    unittest.main()
