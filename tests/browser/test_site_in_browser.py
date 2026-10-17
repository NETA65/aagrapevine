"""The built site in a real browser (tests/browser/__init__.py says how to run these). Each check guards a problem the
round-7 review found that no offline test could see (StoryRecorder: round 8's recorder, whose work only a browser
can do):

  * HeaderFocusRing   — the keyboard focus ring on the header's Search, ES / EN, Aa and theme buttons stands out from
                        what is behind it (3 : 1 at least), at the top of the page (over the dark hero) and scrolled
                        (solid header), in light, dark, high contrast and high contrast dark. Measured on the pixels:
                        the ring's band, focused against not focused (it was 1.45 : 1).
  * StickyBarFocus    — What's New's sticky filter bar never hides the element keyboard focus is on, tabbing forward
                        and back, on a laptop and a phone (it hid 7 of them); the room left for it is measured again
                        when relaxed spacing goes off (the bar turns sticky at the same size).
  * LargeTextPhone    — no page scrolls sideways on a 360-pixel phone at 150 % text: Home, About, Published, Events,
                        Meetings, and Search with a podcast episode among its results, in English and Spanish (About's
                        booth steps did; round 12, an episode result's "Episode page · player.captivate.fm" link).
  * OfflineUpdate     — a new version of the offline worker takes over at once, even while an open tab's page is slow
                        to download again ("Reload" used to wait for every open tab: 12 s on a weak signal).
  * OfflineAreaStyles — a page opened online (not saved), then a new version, then no signal: the page opens with its
                        own stylesheet (the Monthly poster lost its look: its sheet went with the old version).
  * ScriptErrors      — the main pages, English and Spanish, run without a script error.
  * PosterPicture     — a month's poster share picture (scripts/ops/poster_share.py, made by Website update) can be
                        made with this browser: 1200 × 630.
  * TrackerPhotos     — the Tracker, in two tabs: an entry with a receipt photo, open in one tab's edit form while the
                        other deletes it (and then its photo), is saved again with its photo, byte for byte; and
                        closing a tab whose entries the browser would not store asks first.
  * StoryRecorder     — Share your story's recorder, English and Spanish, with Chromium's fake microphone (a browser
                        of its own, its profile kept): the test moves the meter; a take of about 3 s after the 3-2-1
                        countdown plays as an MP3; closing the tab asks nothing, and on the next visit (the browser
                        started again) the take is still there, downloads under the magazine's file name
                        (grapevine-story-…-take-1.mp3, la-vina-historia-…-toma-1.mp3) — a topic typed in "Details for
                        the email" after that goes into the e-mail, never into the name of the file already saved —
                        and as a WAV whose header has the device's rate, and its e-mail goes to the magazine's address
                        (#rec-config); "Delete all recordings from this device" leaves none, also after a reload.
  * RecorderKeepsTakes  — round 10: a take stays on the device until the visitor deletes it (on iPhones takes vanished
                        on the next page of the site). The offline worker runs, as on a phone; the take is a recording
                        added with "Add a recording" (a WAV made here: no microphone). Saved, then a footer link to
                        Events and one back to Share your story, in the same tab: still listed, saved, and it plays as
                        an MP3 — also on /es/contribute/ (the header's ES). The same where every put of a Blob is
                        refused ("UnknownError: Error preparing Blob/File data to be stored in object store": Safari's
                        private window, WebKit 156347). A full device (the sound's puts refused: QuotaExceededError):
                        the lasting box says so, the take says "Not saved on this device yet" (and the notice by the main
                        button), a link asks first and Cancel stays, the footer's calendar file asks nothing; with room
                        again, "Try again" saves it (said; the keyboard goes to the takes' heading) and the next link
                        leaves without a question. Each page's "This device" line is Chrome's (not Safari's 7 days).
  * RecorderTopicAndCheck — round 12, English and Spanish, on a phone-sized window with no microphone granted: a La
                        Viña topic's "Record a story on this topic" chooses La Viña and that topic in the recorder (the
                        list shows it; a scroll to the recorder's heading, the address unchanged); "Having trouble?
                        Check this device" makes its report in the page's language — IndexedDB written and read
                        back, no take, not the topic — without ever asking for the microphone, its own database
                        deleted after, and its e-mail addressed to the site's address.
  * WallsLinks        — round 12 review: the "If Walls Could Talk" note's two links on Share your story (Grapevine's
                        guidelines, Send it on Grapevine's site), alone in their row, are 24px tall at least with a
                        mouse (1280px: 20px they were, WCAG 2.5.8) and 44px on a phone, English and Spanish, never
                        overlapping each other or La Viña's link below.
  * RecorderHoldsUpdate — the "Updated — Reload" notice of a new version of the offline worker waits while a take is
                        being recorded (fake microphone; its Reload would end the take, and an iPhone never asks), and
                        shows once the take is saved — only then is it said to a screen reader (once).
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import statistics
import sys
import tempfile
import time
import unittest
import wave
from array import array
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.site_browser import NO_OUTSIDE, BrowserMissing, SiteServer, launch  # noqa: E402

SITE = os.environ.get("GV_BROWSER_SITE", "").strip()
REQUIRED = os.environ.get("GV_BROWSER_REQUIRED", "").strip() not in ("", "0")
S: dict = {}          # the module's site server, Playwright and browser (setUpModule)


def _unavailable(why: str):
    """A missing tool: skipped — or, where the checks must run (GV_BROWSER_REQUIRED, the Code check), an error."""
    if REQUIRED:
        raise RuntimeError(why)
    raise unittest.SkipTest(why)


def setUpModule():
    if not SITE:
        raise unittest.SkipTest("GV_BROWSER_SITE is not set — the browser checks need a built site "
                                "(tests/browser/__init__.py)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _unavailable("Playwright is not installed (pip install -r scripts/ops/requirements-browser.txt)")
    try:
        from PIL import Image  # noqa: F401 — the focus-ring check compares pictures
    except ImportError:
        _unavailable("Pillow is not installed (pip install -r scripts/ops/requirements-browser.txt)")
    site = Path(SITE).resolve()
    if not (site / "index.html").is_file():
        raise RuntimeError(f"GV_BROWSER_SITE={SITE}: no built website there (no index.html)")
    S["site"] = site
    S["tmp"] = Path(tempfile.mkdtemp(prefix="gv-browser-"))
    S["overrides"] = S["tmp"] / "overrides.json"
    try:
        S["server"] = SiteServer(site, overrides=S["overrides"]).__enter__()
    except RuntimeError as e:
        tearDownModule()
        _unavailable(str(e))
    try:
        S["pw"] = sync_playwright().start()
        S["browser"], S["channel"] = launch(S["pw"])
    except BrowserMissing as e:
        tearDownModule()
        _unavailable(str(e))
    except BaseException:   # (Playwright could not start: the site server is never left running)
        tearDownModule()
        raise


def tearDownModule():
    for close in (lambda: S["browser"].close(), lambda: S["pw"].stop(), lambda: S["server"].__exit__(None, None, None)):
        try:
            close()
        except Exception:  # (not started)
            pass
    if S.get("tmp"):
        shutil.rmtree(S["tmp"], ignore_errors=True)
    S.clear()


def url(path: str = "") -> str:
    return S["server"].address(path)


def new_context(width: int = 1280, height: int = 800, lang: str = "en", theme: str | None = None,
                prefs: dict | None = None, service_workers: str = "block"):
    """A fresh browser profile at this window size: reduced motion (the hero's art is one still picture), Central
    time, the page language's locale, and the site's saved settings (localStorage, before any page script)."""
    ctx = S["browser"].new_context(viewport={"width": width, "height": height}, reduced_motion="reduce",
                                   service_workers=service_workers, timezone_id="America/Chicago",
                                   locale="es-US" if lang == "es" else "en-US")
    store = {}
    if theme:
        store["gvlv-theme"] = theme
    if prefs:
        store["gvlv-prefs"] = json.dumps(prefs)
    if store:
        ctx.add_init_script("(s => { try { for (const k in s) localStorage.setItem(k, s[k]); } catch (e) {} })("
                            + json.dumps(store) + ");")
    return ctx


def poster_months() -> list[str]:
    """The months with a poster page ("2026-10" …, this month first) — not the past months' small redirect pages."""
    return sorted(p.parent.name for p in (S["site"] / "monthly").glob("*/index.html")
                  if re.fullmatch(r"\d{4}-\d{2}", p.parent.name) and "data-mp-poster" in p.read_text(encoding="utf-8"))


def answered(response, path: str) -> None:
    """The page is in the build: a page renamed or gone would otherwise be checked as the site's 404 page."""
    status = response.status if response else None
    if status != 200:
        raise AssertionError(f"/{path} answered {status or 'nothing'}, not 200 — is it still part of the site?")


def open_page(ctx, path: str, errors: list | None = None):
    page = ctx.new_page()
    if errors is not None:
        page.on("pageerror", lambda e: errors.append(f"{path}: {str(e).splitlines()[0][:200]}"))
    answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
    page.evaluate("async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; }")
    return page


# ----------------------------------------------------------------------------------------------- focus ring
def _luminance(rgb) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _in_rounded(x: float, y: float, box: dict, grow: float, radius: float) -> bool:
    """Is (x, y) inside the element's box grown by `grow` on every side, its corners rounded as the browser draws an
    outline (the element's border radius + `grow`, at most half the side)?"""
    l, t = box["x"] - grow, box["y"] - grow
    r, b = box["x"] + box["width"] + grow, box["y"] + box["height"] + grow
    if not (l <= x <= r and t <= y <= b):
        return False
    rad = min(radius + grow, (r - l) / 2, (b - t) / 2) if radius > 0 else 0
    cx = l + rad if x < l + rad else r - rad if x > r - rad else x
    cy = t + rad if y < t + rad else b - rad if y > b - rad else y
    return (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad + 1e-9


def ring_contrast(focused, unfocused, box: dict, offset: float, width: float, radius: float = 0) -> tuple[float, int]:
    """The focus ring's contrast, pixel by pixel: in its band (from outline-offset to outline-offset + outline-width
    around the element, following its rounded corners), each pixel focused against the same pixel not focused — what
    the ring looks like against what it is drawn on. → (the median over the band, the band's size in pixels). A ring
    the colour of what is behind it, or none, gives about 1."""
    a, b = focused.load(), unfocused.load()
    outer = offset + width
    values = []
    for py in range(max(0, int(box["y"] - outer)), min(focused.height, int(box["y"] + box["height"] + outer) + 1)):
        for px in range(max(0, int(box["x"] - outer)), min(focused.width, int(box["x"] + box["width"] + outer) + 1)):
            cx, cy = px + 0.5, py + 0.5
            if _in_rounded(cx, cy, box, outer, radius) and not _in_rounded(cx, cy, box, offset, radius):
                values.append(contrast(a[px, py], b[px, py]))
    return (statistics.median(values) if values else 1.0), len(values)


RING_CONTROLS = {
    "Search": ".site-header .site-search-btn",
    "ES / EN": ".site-header [data-lang-switch]",
    "Aa": ".site-header .gvlv-trigger",
    "theme": ".site-header button[aria-pressed]",
}
RING_MODES = {
    "light": ("light", None),
    "dark": ("dark", None),
    "high contrast": ("light", {"contrast": "high"}),
    "high contrast dark": ("dark", {"contrast": "high"}),
}
FOCUSED = """(sel) => {
  const el = document.querySelector(sel);
  el.focus();
  const cs = getComputedStyle(el), r = el.getBoundingClientRect();
  return { visible: el.matches(":focus-visible"), style: cs.outlineStyle, width: parseFloat(cs.outlineWidth) || 0,
           offset: parseFloat(cs.outlineOffset) || 0, radius: parseFloat(cs.borderTopLeftRadius) || 0,
           box: { x: r.x, y: r.y, width: r.width, height: r.height } };
}"""


class HeaderFocusRing(unittest.TestCase):
    def test_the_ring_stands_out_on_the_header_buttons(self):
        from PIL import Image
        failures, measured = [], []
        for mode, (theme, prefs) in RING_MODES.items():
            ctx = new_context(1280, 800, theme=theme, prefs=prefs)
            try:
                page = open_page(ctx, "")
                # the saved theme and contrast took (else every mode would measure the light one)
                self.assertEqual(page.evaluate("[document.documentElement.getAttribute('data-theme'), "
                                               "document.documentElement.getAttribute('data-contrast')]"),
                                 [theme, (prefs or {}).get("contrast", "normal")], mode)
                page.keyboard.press("Tab")                  # a keyboard user: the browser shows the ring for focus()
                page.evaluate("document.activeElement && document.activeElement.blur()")
                for where, y in (("over the hero", 0), ("scrolled", 900)):
                    page.evaluate(f"window.scrollTo({{ top: {y}, behavior: 'instant' }})")
                    page.wait_for_function(f"(document.querySelector('.site-header').classList.contains('shadow-sm')) "
                                           f"=== {'true' if y else 'false'}", timeout=5000)
                    head = page.evaluate("document.querySelector('.site-header').getBoundingClientRect().bottom")
                    clip = {"x": 0, "y": 0, "width": 1280, "height": int(head) + 12}
                    shot = lambda: Image.open(io.BytesIO(page.screenshot(clip=clip, animations="disabled"))).convert("RGB")
                    before = shot()
                    for name, sel in RING_CONTROLS.items():
                        f = page.evaluate(FOCUSED, sel)
                        label = f"{name}, {mode}, {where}"
                        self.assertEqual(page.evaluate("scrollY"), y, f"{label}: the page stayed where it was")
                        if not f["visible"] or f["style"] == "none" or f["width"] <= 0:
                            failures.append(f"{label}: no focus ring ({f['style']} {f['width']}px)")
                            continue
                        ratio, n = ring_contrast(shot(), before, f["box"], f["offset"], f["width"], f["radius"])
                        measured.append(f"{label}: {ratio:.2f}")
                        if n < 20 or ratio < 3.0:
                            failures.append(f"{label}: {ratio:.2f} : 1 over {n} pixels")
                        page.evaluate("document.activeElement && document.activeElement.blur()")
            finally:
                ctx.close()
        self.assertEqual(failures, [], "the header's focus ring must stand out at 3 : 1 at least — measured: "
                         + "; ".join(measured))
        self.assertEqual(len(measured), len(RING_MODES) * 2 * len(RING_CONTROLS), "every button in every case")
        if os.environ.get("GV_BROWSER_VERBOSE"):
            print("\n  " + "\n  ".join(measured))


# ----------------------------------------------------------------------------------------------- sticky bar
# Where the focused element is against What's New's sticky filter bar (.cm-chipbar) and the fixed header: hidden =
# entirely under them while the bar is stuck. Elements in the bar or the header, and fixed ones (the skip link, a
# notice at the bottom), are not judged.
WHERE_FOCUS = """() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const bar = document.querySelector(".cm-chipbar"), head = document.querySelector(".site-header");
  if (!bar) return { error: "no filter bar on the page" };
  for (let n = el; n && n !== document.body; n = n.parentElement) {
    if (n === bar || n === head || getComputedStyle(n).position === "fixed") return { skip: true };
  }
  const r = el.getBoundingClientRect(), b = bar.getBoundingClientRect(), h = head.getBoundingClientRect();
  if (!r.width && !r.height) return { skip: true };
  const stuck = getComputedStyle(bar).position === "sticky" && b.top <= h.bottom + 2 && b.bottom > h.bottom;
  const cover = stuck ? b.bottom : h.bottom;
  const what = (el.getAttribute("aria-label") || el.textContent || el.tagName).replace(/\\s+/g, " ").trim().slice(0, 50);
  return { stuck, hidden: r.bottom <= cover + 1, partly: r.top < cover - 1, top: Math.round(r.top),
           bottom: Math.round(r.bottom), cover: Math.round(cover), what };
}"""


class StickyBarFocus(unittest.TestCase):
    def tab_through(self, width: int, height: int, lang: str, forward: int, back: int) -> tuple[list, int]:
        ctx = new_context(width, height, lang=lang)
        try:
            page = open_page(ctx, ("es/" if lang == "es" else "") + "whats-new/")
            hidden, stuck = [], 0
            for i in range(forward + back):
                page.keyboard.press("Tab" if i < forward else "Shift+Tab")
                w = page.evaluate(WHERE_FOCUS)
                if not w or w.get("skip"):
                    continue
                self.assertNotIn("error", w, w)
                stuck += bool(w["stuck"])
                if w["stuck"] and (w["hidden"] or w["partly"]):
                    hidden.append(f"{'forward' if i < forward else 'back'} {i}: “{w['what']}” at {w['top']}–{w['bottom']}"
                                  f" under the bar (to {w['cover']})")
            return hidden, stuck
        finally:
            ctx.close()

    def test_the_focused_element_is_never_under_the_bar(self):
        for width, height, lang in ((1280, 800, "en"), (390, 844, "es")):
            with self.subTest(window=f"{width}×{height}", lang=lang):
                hidden, stuck = self.tab_through(width, height, lang, forward=70, back=50)
                self.assertGreater(stuck, 10, "the bar was stuck at the top while tabbing (else nothing was checked)")
                self.assertEqual(hidden, [])

    def test_measured_again_when_relaxed_spacing_goes_off(self):
        # Round-7 review: from 64rem the bar stays in place with relaxed spacing and is sticky without it — at the same
        # size, so nothing measured it again: the room left for it (--wn-bar-h) stayed 0px while it covered the feed
        bar = """() => { const b = document.querySelector(".cm-chipbar");
          return { position: getComputedStyle(b).position, height: Math.ceil(b.getBoundingClientRect().height),
                   room: document.documentElement.style.getPropertyValue("--wn-bar-h") }; }"""
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(1440, 900, lang=lang, prefs={"spacing": "relaxed"})
                try:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "whats-new/")
                    before = page.evaluate(bar)
                    self.assertEqual((before["position"], before["room"]), ("static", "0px"), before)
                    page.evaluate("GV.prefs.set({ spacing: 'normal' })")            # what the Aa panel does
                    try:                                                             # (measured a frame later)
                        page.wait_for_function("() => { const b = document.querySelector('.cm-chipbar'); "
                                               "return getComputedStyle(b).position === 'sticky' && "
                                               "document.documentElement.style.getPropertyValue('--wn-bar-h') === "
                                               "Math.ceil(b.getBoundingClientRect().height) + 'px'; }", timeout=3000)
                    except Exception:  # (not measured: the assertions below say how)
                        pass
                    after = page.evaluate(bar)
                    self.assertEqual(after["position"], "sticky", after)
                    self.assertGreater(after["height"], 0)
                    self.assertEqual(after["room"], f"{after['height']}px", after)
                finally:
                    ctx.close()


# ----------------------------------------------------------------------------------------------- large text
SIDEWAYS = """() => {
  const w = document.documentElement.clientWidth;
  window.scrollTo(100000, window.scrollY);
  const moved = window.scrollX;
  window.scrollTo(0, window.scrollY);
  const scrollWidth = document.documentElement.scrollWidth, wide = [];
  // (for the message: the first elements that reach past the edge — not those inside a box that scrolls or clips)
  const inBox = (el) => { for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
    if (getComputedStyle(n).overflowX !== "visible") return true; } return false; };
  if (moved > 0 || scrollWidth > w) {
    for (const el of document.body.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.right > w + 1 && r.width > 0 && getComputedStyle(el).position !== "fixed" && !inBox(el)) {
        const cls = typeof el.className === "string" ? el.className.trim().split(/\\s+/).slice(0, 3).join(".") : "";
        wide.push(el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (cls ? "." + cls : "") + " → " + Math.round(r.right));
        if (wide.length >= 5) break;
      }
    }
  }
  return { moved, scrollWidth, width: w, wide };
}"""
LARGE_TEXT_PAGES = ("", "about/", "published/", "events/", "meetings/")
EPISODE_LINK = "#ss-results .ss-alt"     # an episode result's second link, "Episode page · player.captivate.fm ↗"


def episode_search(lang: str) -> str:
    """Search with a podcast episode among the results ("search/?q=sponsorship"), so its result shows its second link
    (search.js altLink): the longest word of the first episode's title in that language's search index — whatever
    the day's episodes are. "" when the index has no episode with a host page."""
    pre = "es/" if lang == "es" else ""
    try:
        items = json.loads((S["site"] / pre / "search-index.json").read_text(encoding="utf-8"))["items"]
    except (OSError, ValueError, KeyError):
        return ""
    for e in items:
        words = re.findall(r"[^\W\d_]{5,}", str(e.get("t", ""))) if e.get("k") == "episode" and e.get("u2") else []
        if words:
            return f"{pre}search/?q={max(words, key=len).lower()}"
    return ""


class LargeTextPhone(unittest.TestCase):
    def test_no_sideways_scroll_at_150_percent_on_a_phone(self):
        problems = []
        for lang in ("en", "es"):
            ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
            try:
                search = episode_search(lang)
                for path in [("es/" if lang == "es" else "") + p for p in LARGE_TEXT_PAGES] + ([search] if search else []):
                    page = open_page(ctx, path)
                    self.assertEqual(page.get_attribute("html", "data-text"), "150", "the page took the saved text size")
                    if path == search:                        # (the results come from the search index, a moment later)
                        page.wait_for_selector(EPISODE_LINK, timeout=20_000)
                    page.wait_for_timeout(300)                # (late layout: pictures, the scripts' own changes)
                    r = page.evaluate(SIDEWAYS)
                    if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                        problems.append(f"/{path}: scrolls {r['moved']} px sideways "
                                        f"(page {r['scrollWidth']} px wide in {r['width']}): {r['wide']}")
                    page.close()
            finally:
                ctx.close()
        self.assertEqual(problems, [])


# ----------------------------------------------------------------------------------------------- offline update
WORKER_READY = "async () => { const r = await navigator.serviceWorker.ready; return !!(r.active && navigator.serviceWorker.controller); }"
# The new version, installed and waiting — its own state "installed", not only the registration's `waiting` slot: the
# browser hands the page the two as separate updates, and the slot can come first (the worker still "installing" for a
# moment). An update() that found nothing new (the browser's own check after a navigation, still on the old file) is
# asked again every 2 s. 30 s at most.
NEW_VERSION_WAITING = """async () => {
  const reg = await navigator.serviceWorker.getRegistration();
  await reg.update().catch(() => {});
  for (let i = 0; i < 300 && !(reg.waiting && reg.waiting.state === "installed"); i++) {
    if (!reg.waiting && !reg.installing && i % 20 === 19) await reg.update().catch(() => {});
    await new Promise((r) => setTimeout(r, 100));
  }
  return reg.waiting ? reg.waiting.state : (reg.installing ? "still installing" : "none");
}"""
TAKE_OVER = """async () => {
  const reg = await navigator.serviceWorker.getRegistration();
  const w = reg.waiting;
  if (!w) return { state: "nothing waiting" };
  const t0 = performance.now();
  const done = new Promise((r) => { w.addEventListener("statechange", () => { if (w.state === "activated") r(); }); });
  w.postMessage({ type: "SKIP_WAITING" });       // what "Reload" on the "Updated" notice sends (pwa.js)
  await Promise.race([done, new Promise((r) => setTimeout(r, 15000))]);
  return { state: w.state, ms: Math.round(performance.now() - t0) };
}"""


class OfflineUpdate(unittest.TestCase):
    SLOW_MS = 20_000

    def tearDown(self):
        S["overrides"].unlink(missing_ok=True)

    def test_a_new_version_takes_over_without_waiting_for_the_open_tabs(self):
        prefix = S["server"].prefix
        sw = (S["site"] / "sw.js").read_text(encoding="utf-8")
        m = re.search(r'"version": "([^"]+)"', sw)
        self.assertIsNotNone(m, "sw.js names its version")
        newer = S["tmp"] / "sw-next.js"
        newer.write_text(sw.replace(m.group(0), f'"version": "{m.group(1)}-next"', 1), encoding="utf-8")
        ctx = new_context(1280, 800, service_workers="allow")
        try:
            slow = open_page(ctx, "about/")            # an open tab, the site's worker installed by the first visit
            slow.wait_for_function(WORKER_READY, timeout=30_000)
            page = open_page(ctx, "")                  # the tab where the visitor presses "Reload"
            page.wait_for_function(WORKER_READY, timeout=30_000)
            page.wait_for_timeout(1500)                # (the first visit's own keeping of the open tab)
            # a new version of the site; the open tab's page now takes 20 s to come (a weak signal)
            S["overrides"].write_text(json.dumps({"files": {prefix + "sw.js": str(newer)},
                                                  "delay_ms": {prefix + "about/": self.SLOW_MS}}), encoding="utf-8")
            self.assertEqual(page.evaluate(NEW_VERSION_WAITING), "installed", "the new version installed and waits")
            took = page.evaluate(TAKE_OVER)
            self.assertEqual(took["state"], "activated", took)
            # (about 1 s; waiting for the open tab would take its 20 s — or the 8 s each download of it is given)
            self.assertLess(took["ms"], 6000, f"the new version took over in {took['ms']} ms — it must not wait for "
                                              "the open tab's page")
            t0 = time.monotonic()
            page.reload(wait_until="domcontentloaded", timeout=30_000)
            self.assertLess(time.monotonic() - t0, 5, "Reload opens the page at once")
            self.assertEqual(page.evaluate("navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL")
                             .split("/")[-1], "sw.js")
        finally:
            ctx.close()


# A page's own stylesheet (pageStyles: monthly.css, booth.css …): { linked, rules (-1: can't be read), href }
AREA_SHEET = """(name) => {
  const s = [...document.styleSheets].find((x) => x.href && x.href.split("?")[0].endsWith("/assets/css/" + name + ".css"));
  if (!s) return { linked: false, rules: 0, href: "" };
  try { return { linked: true, rules: s.cssRules.length, href: s.href }; } catch (e) { return { linked: true, rules: -1, href: s.href }; }
}"""
IN_CACHE = "async (u) => !!(await caches.match(u))"
CACHE_NAMES = "async () => (await caches.keys()).filter((n) => n.startsWith('gvlv-static-') || n.startsWith('gvlv-shell-')).sort()"


class OfflineAreaStyles(unittest.TestCase):
    """A page opened online (not saved), then a new version of the site, then no signal: the page opens from the worker's
    copy WITH its own stylesheet (the round-7 review: the Monthly poster came out as a page-wide unstyled picture — the
    stylesheet went with the old version's cache; the worker now carries an old version's stylesheets on)."""

    def tearDown(self):
        S["overrides"].unlink(missing_ok=True)

    def test_a_page_opened_before_an_update_keeps_its_own_styles_offline(self):
        prefix = S["server"].prefix
        month = f"monthly/{poster_months()[0]}/"
        sw = (S["site"] / "sw.js").read_text(encoding="utf-8")
        m = re.search(r'"version": "([^"]+)"', sw)
        self.assertIsNotNone(m, "sw.js names its version")
        version = m.group(1)
        newer = S["tmp"] / "sw-area-next.js"
        newer.write_text(sw.replace(m.group(0), f'"version": "{version}-area"', 1), encoding="utf-8")
        ctx = new_context(1280, 800, service_workers="allow")
        try:
            page = open_page(ctx, "")
            page.wait_for_function(WORKER_READY, timeout=30_000)
            page.wait_for_timeout(1500)                # (the first visit's own keeping of the open tab)
            visit = open_page(ctx, month)              # opened online, not saved: the worker keeps it, and its stylesheet
            online = visit.evaluate(AREA_SHEET, "monthly")
            self.assertGreater(online["rules"], 100, online)
            shape = visit.evaluate("getComputedStyle(document.querySelector('[data-mp-poster]')).display")
            visit.wait_for_function(IN_CACHE, arg=url(month), timeout=10_000)
            visit.wait_for_function(IN_CACHE, arg=online["href"], timeout=10_000)
            visit.close()                              # (closed: not an open tab the new version keeps again)
            S["overrides"].write_text(json.dumps({"files": {prefix + "sw.js": str(newer)}}), encoding="utf-8")
            self.assertEqual(page.evaluate(NEW_VERSION_WAITING), "installed", "the new version installed and waits")
            took = page.evaluate(TAKE_OVER)
            self.assertEqual(took["state"], "activated", took)
            # the old version's caches are gone: what answers below is the new version's
            names = page.evaluate(CACHE_NAMES)
            self.assertIn(f"gvlv-shell-{version}-area", names)
            self.assertEqual([n for n in names if not n.endswith(f"-{version}-area")], [], names)
            ctx.set_offline(True)
            again = ctx.new_page()
            answered(again.goto(url(month), wait_until="load", timeout=60_000), month)
            offline = again.evaluate(AREA_SHEET, "monthly")
            self.assertEqual(offline["href"], online["href"], "the copy kept before the update (its old ?v= address)")
            self.assertEqual(offline["rules"], online["rules"], "its own stylesheet, offline after the update")
            self.assertEqual(again.evaluate("getComputedStyle(document.querySelector('[data-mp-poster]')).display"), shape)
        finally:
            ctx.close()


# ----------------------------------------------------------------------------------------------- script errors
MAIN_PAGES = ("", "about/", "read/", "listen/", "watch/", "published/", "library/", "events/", "meetings/", "monthly/",
              "whats-new/", "bulletin/", "shop/", "contribute/", "search/?q=sponsor", "status/", "tracker/",
              "orientation/", "accessibility/", "gvr/", "instagram/", "digest/", "share/", "offline/")


class ScriptErrors(unittest.TestCase):
    def test_the_main_pages_run_without_a_script_error(self):
        pages = [*MAIN_PAGES, *(f"monthly/{m}/" for m in poster_months()[:1])]     # (+ this month's page)
        errors: list[str] = []
        for lang in ("en", "es"):
            ctx = new_context(1280, 800, lang=lang)
            try:
                # six pages at a time (the browser loads them side by side)
                for i in range(0, len(pages), 6):
                    batch = []
                    for path in pages[i:i + 6]:
                        page = ctx.new_page()
                        where = ("es/" if lang == "es" else "") + path
                        page.on("pageerror", lambda e, where=where: errors.append(f"/{where}: {str(e).splitlines()[0][:200]}"))
                        answered(page.goto(url(where), wait_until="commit", timeout=60_000), where)
                        batch.append(page)
                    for page in batch:
                        page.wait_for_load_state("load", timeout=60_000)
                    batch[-1].wait_for_timeout(300)        # (scripts that start once the page is shown)
                    for page in batch:
                        page.close()
            finally:
                ctx.close()
        # a phone: the menu and the phone layouts' scripts
        ctx = new_context(390, 844)
        try:
            page = open_page(ctx, "", errors)
            page.click(".site-header .site-menu-btn")
            page.wait_for_selector("#mobile-drawer", state="visible", timeout=5000)
            page.keyboard.press("Escape")
            page.close()
        finally:
            ctx.close()
        self.assertEqual(errors, [])


# ----------------------------------------------------------------------------------------------- poster picture
class PosterPicture(unittest.TestCase):
    def test_a_posters_share_picture_can_be_made(self):
        from scripts.ops import poster_share as P
        month = poster_months()
        self.assertTrue(month, "a month page with its poster")
        out = S["tmp"] / "share.png"
        with redirect_stdout(io.StringIO()):
            problems = P.shoot(S["browser"], S["server"], [(f"es/monthly/{month[0]}/", out)])
        self.assertEqual(problems, [])
        self.assertEqual(P.png_size(out), (P.WIDTH, P.HEIGHT))
        self.assertGreater(out.stat().st_size, 30_000, "a picture with something on it")


# ----------------------------------------------------------------------------------------------- the Tracker
XP_APP = "Alpine.$data(document.querySelector('.xp-root'))"
XP_IDB = """async ({ put, get }) => {
  const db = await new Promise((res, rej) => { const r = indexedDB.open("gv-expenses", 1);
    r.onupgradeneeded = () => { if (!r.result.objectStoreNames.contains("receipts")) r.result.createObjectStore("receipts", { keyPath: "id" }); };
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const run = (mode, fn) => new Promise((res, rej) => { const tx = db.transaction("receipts", mode), q = fn(tx.objectStore("receipts"));
    tx.oncomplete = () => res(q.result); tx.onerror = () => rej(tx.error); });
  let out = null;
  if (put) {
    const c = document.createElement("canvas"); c.width = 64; c.height = 48; c.getContext("2d").fillRect(8, 8, 30, 20);
    const blob = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.8));
    await run("readwrite", (s) => s.put({ id: put, type: "image/jpeg", blob, w: 64, h: 48, name: "IMG_1.jpg", added: "2026-09-26T10:00:00.000Z" }));
  }
  if (get) {
    const rec = await run("readonly", (s) => s.get(get));
    out = rec ? Array.from(new Uint8Array(await rec.blob.arrayBuffer())).reduce((a, x) => (a * 31 + x) % 1000000007, rec.blob.size) : null;
  }
  db.close();
  return out;
}"""


class TrackerPhotos(unittest.TestCase):
    """The Tracker keeps its data in this browser (localStorage and IndexedDB, shared by the tabs of one profile)."""

    def tracker(self, ctx, errors):
        page = open_page(ctx, "tracker/", errors)
        page.wait_for_function(f"() => window.Alpine && document.querySelector('.xp-root') && {XP_APP}.ready", timeout=30_000)
        return page

    def test_an_entry_deleted_in_another_tab_keeps_its_photo_when_saved_again(self):
        # Tab B has the entry open in its edit form; tab A deletes it, and its undo time runs out (A deletes the photo).
        # B saves it again: the entry is back under its own id, with its photo, byte for byte, also after the next
        # visit's clean-up (it used to come back as a new entry claiming a photo that was gone).
        errors: list = []
        ctx = new_context(1280, 900)
        try:
            a = self.tracker(ctx, errors)
            a.evaluate("(l) => localStorage.setItem('gv-expenses:v1', l)", json.dumps({"v": 1, "settings": {}, "meta": {}, "entries": [
                {"id": "xhotel1", "type": "expense", "date": "2026-09-26", "category": "lodging", "description": "Hotel for the assembly",
                 "amount_cents": 9000, "receipt": "photo"}]}))
            a.evaluate(XP_IDB, {"put": "xhotel1", "get": None})
            a.reload()
            a.wait_for_function(f"() => {XP_APP}.ready")
            b = self.tracker(ctx, errors)
            photo = b.evaluate(XP_IDB, {"put": None, "get": "xhotel1"})
            self.assertIsNotNone(photo)
            b.evaluate(f"() => {XP_APP}.openEdit('xhotel1')")
            b.wait_for_function("() => { const i = document.querySelector('.xp-photo img'); return !!(i && i.src.startsWith('blob:') && i.naturalWidth); }")
            b.fill("#xp-f-description", "Hotel for the Fall Assembly")
            a.evaluate(f"() => {{ {XP_APP}.remove(['xhotel1']); }}")
            a.click("dialog.xp-ask[open] .xp-ask-acts button.btn-primary")
            a.wait_for_selector("[data-xp-undo]", state="visible")
            b.wait_for_function("() => /deleted in another tab/.test(document.querySelector('.xp-dlg-msg').textContent)")
            a.click(".xp-toast-x")                                   # A's undo time is over: its photo goes
            a.wait_for_function("() => !document.querySelector('[data-xp-undo]') || !document.querySelector('[data-xp-undo]').offsetParent")
            a.wait_for_timeout(300)
            self.assertIsNone(a.evaluate(XP_IDB, {"put": None, "get": "xhotel1"}), "tab A deleted the photo (else nothing was checked)")
            b.click("footer.xp-dlg-foot button[type=submit]")
            b.wait_for_selector("dialog.xp-dialog[open]", state="hidden")
            b.wait_for_timeout(300)
            entries = a.evaluate("() => JSON.parse(localStorage.getItem('gv-expenses:v1')).entries.map((e) => [e.id, e.receipt, e.description])")
            self.assertEqual(entries, [["xhotel1", "photo", "Hotel for the Fall Assembly"]])
            self.assertEqual(a.evaluate(XP_IDB, {"put": None, "get": "xhotel1"}), photo)
            c = self.tracker(ctx, errors)
            c.wait_for_timeout(2200)                                 # the next visit's clean-up (1.5 s after it starts)
            self.assertEqual(c.evaluate(XP_IDB, {"put": None, "get": "xhotel1"}), photo)
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_closing_the_tab_asks_while_the_browser_keeps_nothing(self):
        # Storage refused (full, or blocked by the browser's settings): an entry added exists only in the tab, and
        # closing it asks first; with nothing added, it does not.
        ctx = new_context(1280, 900)
        ctx.add_init_script("(() => { const set = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) {"
                            " if (String(k).startsWith('gv-expenses:v1')) throw new DOMException('full', 'QuotaExceededError');"
                            " return set.call(this, k, v); }; })();")
        try:
            asked = {}
            for add in (False, True):
                page = self.tracker(ctx, [])
                asked[add] = []
                page.on("dialog", lambda d, k=add: (asked[k].append(d.type), d.accept()))
                if add:
                    page.evaluate(f"() => {XP_APP}.openAdd('expense', 'books')")
                    page.wait_for_selector("dialog.xp-dialog[open] #xp-f-description")
                    page.fill("#xp-f-description", "Big Book")
                    page.fill("#xp-f-amount", "12")
                    page.click("footer.xp-dlg-foot button[type=submit]")
                    page.wait_for_selector("dialog.xp-dialog[open]", state="hidden")
                page.close(run_before_unload=True)
                other = ctx.new_page()                               # (the dialog's event arrives meanwhile)
                other.wait_for_timeout(600)
                other.close()
            self.assertEqual(asked, {False: [], True: ["beforeunload"]})
        finally:
            ctx.close()


# ----------------------------------------------------------------------------------------------- the story recorder
# Chromium's own stand-ins for a microphone: a fake one (a beep every second), allowed without asking. They go on a
# browser of its own: the other checks' browser has no microphone at all, as a visitor's without one.
FAKE_MIC = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
REC_APP = "Alpine.$data(document.getElementById('recorder'))"
REC_STATE = "document.querySelector('#recorder .cm-rec-deck').dataset.state"
# the deck's level meter: how far its bar is drawn (0 … 1)
REC_METER = ("parseFloat((document.querySelector('#recorder .cm-rec-deck .cm-rec-meter span').style.transform"
             ".match(/scaleX\\(([\\d.]+)\\)/) || [0, 0])[1])")
# what the recorder keeps on this device (IndexedDB "gvlv-recorder" v2: takes = the records, sound = rows of bytes):
# final takes, drafts (a take being made or saved), the PCM and MP3 rows, how many bytes they hold, and any value that
# is not an ArrayBuffer (a Blob: Safari's private store refuses them) — null before the recorder made its database
# (never made here: opened before the recorder made it, it would have no stores — so a database that would have to be
# made is not)
REC_IDB = """async () => {
  const db = await new Promise((res) => { const r = indexedDB.open("gvlv-recorder");
    r.onupgradeneeded = () => r.transaction.abort();
    r.onsuccess = () => res(r.result); r.onerror = () => res(null); });
  if (!db) return null;
  if (!["takes", "sound"].every((n) => db.objectStoreNames.contains(n))) { db.close(); return null; }
  const all = (n) => new Promise((res) => { const q = db.transaction([n], "readonly").objectStore(n).getAll();
    q.onsuccess = () => res(q.result); q.onerror = () => res([]); });
  const takes = await all("takes"), sound = await all("sound");
  db.close();
  const rows = (kind) => sound.filter((r) => r.kind === kind);
  const bytes = (kind) => rows(kind).reduce((n, r) => n + (r.buf ? r.buf.byteLength : 0), 0);
  return { takes: takes.filter((t) => !t.draft).length, drafts: takes.filter((t) => t.draft).length, pcm: rows("pcm").length,
           mp3: rows("mp3").length, pcmBytes: bytes("pcm"), samples: takes.reduce((n, t) => n + (t.draft ? 0 : t.samples), 0),
           notBytes: sound.filter((r) => !(r.buf instanceof ArrayBuffer)).length };
}"""
REC_IDB_NONE = {"takes": 0, "drafts": 0, "pcm": 0, "mp3": 0, "pcmBytes": 0, "samples": 0, "notBytes": 0}
# the take's player: its address, its first bytes and its length (once the browser has read the file's start)
REC_AUDIO = """async () => {
  const a = document.querySelector('#recorder li.cm-rec-take audio');
  if (!a || !a.src) return null;
  if (a.readyState < 1) await new Promise((r) => { a.addEventListener('loadedmetadata', r, { once: true }); setTimeout(r, 5000); });
  const b = new Uint8Array(await (await fetch(a.src)).arrayBuffer());
  return { src: a.src, head: Array.from(b.slice(0, 4)), size: b.length, duration: a.duration };
}"""
# the rate the device records at: what a new AudioContext gets (the recorder never asks for another)
AUDIO_RATE = "async () => { const c = new AudioContext(); const r = c.sampleRate; await c.close(); return r; }"
# the day in the browser's own time zone (Central): a take's file name carries the day it was recorded
TODAY = ("(() => { const d = new Date(); return [d.getFullYear(), d.getMonth() + 1, d.getDate()]"
         ".map((n) => String(n).padStart(2, '0')).join('-'); })()")
# per page: the magazine its takes go to at first (the page's language's), and the file name's words
REC_PAGES = {"en": ("contribute/", "gv", "grapevine-story", "take"),
             "es": ("es/contribute/", "lv", "la-vina-historia", "toma")}


def mpeg_frame(head: bytes) -> bool:
    """An MP3's first frame: the 11 sync bits, then "Layer III" (0xFF 0xFB, 0xF3, 0xE3 …) — not a WAV, not WebM."""
    return len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE6) == 0xE2


class RecorderPage:
    """What the recorder's checks share (not a check itself)."""

    def browser(self, profile: Path, lang: str, service_workers: str = "block"):
        """This check's own browser (the one the module found), with the fake microphone, the other checks' settings
        (new_context) and a profile kept in `profile`: what the site stores outlives the browser — the next visit
        is a new browser on the same profile. (Not a reload, nor a new tab: headless Chrome on Windows sometimes
        loads no new page at all after a take was recorded — about 1 visitor in 6 here, with or without the wake
        lock or the MP3 encoder; a new browser always does.)"""
        options = {"headless": True, "args": [NO_OUTSIDE, *FAKE_MIC], "permissions": ["microphone"],
                   "viewport": {"width": 1280, "height": 900}, "reduced_motion": "reduce",
                   "service_workers": service_workers,
                   "timezone_id": "America/Chicago", "locale": "es-US" if lang == "es" else "en-US"}
        if S["channel"] != "chromium":
            options["channel"] = S["channel"]
        return S["pw"].chromium.launch_persistent_context(str(profile), **options)

    def ready(self, page) -> None:
        """The recorder has started and listed the takes this device keeps."""
        page.wait_for_function(f"() => window.Alpine && document.getElementById('recorder') && {REC_APP}.loaded",
                               timeout=30_000)

    def visit(self, ctx, path: str, errors: list, asked: list):
        """The page in a new tab, the recorder ready (a question on leaving it is answered "leave" and noted)."""
        page = open_page(ctx, path, errors)
        page.on("dialog", lambda d: (asked.append(d.type), d.accept()))
        self.ready(page)
        return page

    def shows(self, page, js: str, want, msg: str = "", timeout: float = 5.0) -> None:
        """What the page shows (`js`'s answer) is `want` once drawn — Alpine draws a change a frame after it (x-show
        hides and shows on the next animation frame) —, else the last answer is compared, so the check says what it
        was."""
        end = time.monotonic() + timeout
        while True:
            got = page.evaluate(js)
            if got == want or time.monotonic() > end:
                break
            page.wait_for_timeout(100)
        self.assertEqual(got, want, msg)


class StoryRecorder(RecorderPage, unittest.TestCase):
    """Share your story's recorder (/contribute/#record): the sound, the MP3 (LAME in WebAssembly) and the takes kept
    on the device (IndexedDB) are all made in the browser, so no offline test can see them work together."""

    def test_a_take_is_recorded_kept_sent_and_deleted(self):
        for lang in REC_PAGES:
            with self.subTest(lang=lang):
                self.one_take(lang)

    def download(self, page, link: str) -> tuple[str, bytes]:
        with page.expect_download(timeout=15_000) as dl:
            page.click(link)
        d = dl.value
        return d.suggested_filename, Path(d.path()).read_bytes()

    def one_take(self, lang: str) -> None:
        path, pub, base, word = REC_PAGES[lang]
        errors, asked = [], []
        profile = S["tmp"] / f"recorder-{lang}"
        ctx = self.browser(profile, lang)
        try:
            page = self.visit(ctx, path, errors, asked)
            self.assertTrue(page.is_visible("#recorder"), "the recorder shows (the page's scripts run)")
            cfg = json.loads(page.text_content("#rec-config"))
            self.assertEqual(cfg["pub"], pub, "the page's language's magazine first")
            email = cfg["pubs"][pub]["email"]
            self.assertIn("@", email, "the magazine's address is in #rec-config")
            self.assertEqual(page.locator("#recorder li.cm-rec-take").count(), 0, "a new profile has no take")
            self.assertEqual(page.evaluate(REC_IDB), REC_IDB_NONE)
            days = {page.evaluate(TODAY)}
            rate = page.evaluate(AUDIO_RATE)

            # Test the microphone: the meter shows the (fake) voice
            page.click("#recorder .cm-rec-deck [data-rec-test]")
            page.wait_for_function(f"() => {REC_STATE} === 'testing'", timeout=10_000)
            page.wait_for_function(f"() => {REC_METER} > 0", timeout=5000)

            # Start recording: 3, 2, 1 — then about 3 seconds, and Stop and save (the same main button)
            t0 = time.monotonic()
            page.click("#recorder .cm-rec-go")
            page.wait_for_function(f"() => {REC_STATE} === 'countdown'", timeout=2000)
            page.wait_for_function(f"() => {REC_STATE} === 'recording'", timeout=10_000)
            self.assertGreater(time.monotonic() - t0, 2.5, "the take starts after the 3-second countdown")
            # (the "Install this site as an app" notice keeps out of the way while this is on: pwa.js busy())
            self.assertTrue(page.evaluate("document.documentElement.classList.contains('cm-rec-on')"))
            page.wait_for_timeout(3000)
            page.click("#recorder .cm-rec-go")
            page.wait_for_function(f"() => {REC_STATE} === 'idle' && {REC_APP}.takes.length === 1 && "
                                   f"{REC_APP}.takes[0].saved", timeout=20_000)
            self.assertFalse(page.evaluate("document.documentElement.classList.contains('cm-rec-on')"))
            self.assertEqual(page.locator("#recorder li.cm-rec-take").count(), 1)
            audio = page.evaluate(REC_AUDIO)
            self.assertIsNotNone(audio, "the take has a player")
            self.assertTrue(audio["src"].startswith("blob:"), audio["src"])
            self.assertTrue(mpeg_frame(bytes(audio["head"])), f"the take plays as an MP3: {bytes(audio['head']).hex()}")
            self.assertAlmostEqual(audio["duration"], 3, delta=1.5, msg="a take of about 3 seconds")
            kept = page.evaluate(REC_IDB)
            # kept on this device: one final record (no draft left), its PCM — written as it was recorded, every byte
            # once — and its MP3, all as bytes
            self.assertEqual((kept["takes"], kept["drafts"], kept["notBytes"]), (1, 0, 0), kept)
            self.assertGreaterEqual(kept["pcm"], 1, kept)
            self.assertGreaterEqual(kept["mp3"], 1, kept)
            self.assertEqual(kept["pcmBytes"], kept["samples"] * 2, kept)
            take = page.evaluate(f"{REC_APP}.takes[0].id")

            # the visitor closes the tab — it asks nothing, the take is kept — and the browser
            page.close(run_before_unload=True)
            ctx.new_page().wait_for_timeout(600)       # (the question's event, if any, arrives meanwhile)
        finally:
            ctx.close()

        # the next visit: the take is still there, its MP3 read back from IndexedDB
        ctx = self.browser(profile, lang)
        try:
            page = self.visit(ctx, path, errors, asked)
            self.assertEqual(page.evaluate(f"{REC_APP}.takes.map((t) => t.id)"), [take])
            page.wait_for_selector("#recorder li.cm-rec-take", timeout=5000)
            again = page.evaluate(REC_AUDIO)
            self.assertTrue(mpeg_frame(bytes(again["head"])) and again["size"] == audio["size"], again)

            # Send or save: the MP3 under the magazine's file name, then the WAV; the e-mail goes to the magazine
            page.click("#recorder li.cm-rec-take button[aria-controls^='rec-send-']")
            link = "#recorder .cm-rec-panel a[download]"
            page.wait_for_selector(link + "[download$='.mp3']", state="visible", timeout=10_000)
            name, mp3 = self.download(page, link)
            days.add(page.evaluate(TODAY))             # (either side of midnight: the day it was recorded)
            self.assertRegex(name, rf"^{base}-\d{{4}}-\d{{2}}-\d{{2}}-{word}-1\.mp3$")
            day = name[len(base) + 1:len(base) + 11]
            self.assertIn(day, days, f"{name}: the day it was recorded")
            self.assertTrue(mpeg_frame(mp3[:4]), f"{name}: an MP3 ({mp3[:4].hex()})")
            self.assertEqual(len(mp3), audio["size"], "the file the take plays")
            # a topic typed in "Details for the email" after the download: in the e-mail, never in the name of the file
            # the member has (the "Attach …" line, the link, the next download keep it)
            topic = "Recaídas" if pub == "lv" else "Gratitude"
            field = "#recorder .cm-rec-panel .cm-rec-mail input[autocomplete=off]"
            page.click("#recorder .cm-rec-panel .cm-rec-mail > summary")
            page.fill(field, topic)
            page.press(field, "Tab")                   # (its change: the file made again — under the same name)
            until(page, f"() => {REC_APP}.subject({REC_APP}.takes[0]).includes({json.dumps(topic)})", "the topic is in the subject", 5000)
            page.wait_for_selector(link + "[download$='.mp3']", state="visible", timeout=10_000)
            self.assertEqual(page.get_attribute(link, "download"), name)
            self.assertIn(name, page.inner_text("#recorder .cm-rec-panel"), "the Attach line names the file saved")
            page.check("#recorder .cm-rec-panel input[value=wav]")
            page.wait_for_selector(link + "[download$='.wav']", state="visible", timeout=10_000)
            name, wav = self.download(page, link)
            self.assertEqual(name, f"{base}-{day}-{word}-1.wav")
            self.assertEqual(wav[:4] + wav[8:16], b"RIFFWAVEfmt ", f"{name}: a WAV")
            self.assertEqual((int.from_bytes(wav[22:24], "little"), int.from_bytes(wav[34:36], "little")), (1, 16),
                             "mono, 16-bit")
            self.assertEqual(int.from_bytes(wav[24:28], "little"), rate, "the device's own rate, as the header says")
            data = int.from_bytes(wav[40:44], "little")
            self.assertEqual(data % 2, 0, "whole 16-bit samples")
            self.assertEqual(len(wav), 44 + data, "the header's size is the file's")
            self.assertAlmostEqual(data / 2 / rate, 3, delta=1.5, msg="the WAV's length")
            href = page.get_attribute("#recorder .cm-rec-panel a[href^='mailto:']", "href") or ""
            self.assertTrue(href.startswith(f"mailto:{email}?subject="), href[:120])

            # "Delete all recordings from this device", and yes: none left, also after a reload
            page.click("#recorder [x-ref='allBtn']")
            page.click("#recorder [aria-labelledby='rec-all-q'] button.text-danger")
            page.wait_for_selector("#recorder li.cm-rec-take", state="detached", timeout=5000)
            page.wait_for_function(f"async () => {{ const n = await ({REC_IDB})(); "
                                   "return !!n && n.takes + n.drafts + n.pcm + n.mp3 === 0; }", timeout=5000)
            page.reload(wait_until="load", timeout=30_000)
            self.ready(page)
            self.assertEqual(page.locator("#recorder li.cm-rec-take").count(), 0)
            self.assertEqual(page.evaluate(REC_IDB), REC_IDB_NONE)
        finally:
            ctx.close()
        self.assertEqual(errors, [])
        self.assertEqual(asked, [], "leaving asked first, though the take was kept on this device (or deleted)")


# ----------------------------------------------------------------------------------------------- takes stay (round 10)
# Round 10: on phones (an iPhone above all) a take vanished after a link to another page of the site — Safari's private
# store refuses every Blob in IndexedDB, and the take then lived in the page only, which an iPhone leaves without a
# question. The recorder keeps bytes now, a take it could not save stays in the page with all its sound, and leaving by
# a link asks first, in the page. These checks run with the site's offline worker on, as a phone has it.
SITE_LINK = "footer.site-footer a[href='{}']"             # a link in every page's footer: .format(prefix + page)
REC_IMPORT = "#recorder .cm-rec-tail button"               # "Add a recording" (it opens the file chooser)
REC_RETRY = "#recorder [role=status] .cm-rec-note button"  # "Try again", in the lasting box about storage
REC_HOLD = "document.documentElement.classList.contains('cm-rec-hold')"
# the words the markup shows (community.recorder.*: st_full, t_unsaved, b_retry …), as the build renders them
REC_WORDS = ROOT / "src" / "_i18n" / "community.json"
# where the recorder is, for a check's message: the storage box, each take, the page's classes
REC_NOW = f"""() => {{ const a = {REC_APP};
  return {{ note: a.storeNote(), full: a.full, lastErr: a.lastErr, state: a.state, kept: a.kept, notice: a.notice,
           takes: a.takes.map((t) => ({{ saved: t.saved, saving: t.saving, failed: t.failed, damaged: t.damaged }})),
           html: document.documentElement.className }}; }}"""
# what is shown (a hidden element has no box): the lasting box's lines, the takes' badges, their sizes
_SHOWN = "].filter((e) => e.getClientRects().length).map((e) => e.textContent.replace(/\\s+/g, ' ').trim())"
REC_STORE_BOX = "() => [...document.querySelectorAll('#recorder [role=status] .cm-rec-note p')" + _SHOWN
REC_BADGES = "() => [...document.querySelectorAll('#recorder li.cm-rec-take [class*=badge]')" + _SHOWN
REC_SIZES = "() => [...document.querySelectorAll('#recorder li.cm-rec-take [x-show=\"showSizes()\"]')" + _SHOWN
# the notice by the main button (the deck's), and the "This device" line on how long the browser keeps takes
REC_NOTICE = "() => [...document.querySelectorAll('#recorder .cm-rec-deck .cm-rec-note:not(.is-error) p')" + _SHOWN
REC_KEPT_LINE = "() => [...document.querySelectorAll('#recorder span[x-show^=\"keptLine()\"]')" + _SHOWN
# IndexedDB refusing a put the way a browser does — the request fails, then the transaction aborts with that error
# (tx.error) — for each put `refuse(store name, value)` gives an error for; each one noted (localStorage
# "gv-test-refused": the store's name). (The record is put, then added again: the clash — ConstraintError — aborts the
# transaction, and both say `refuse`'s error instead.)
IDB_REFUSE = """(() => {
  const refuse = %s;
  const put = IDBObjectStore.prototype.put, add = IDBObjectStore.prototype.add;
  IDBObjectStore.prototype.put = function (...args) {
    const err = refuse(this.name, args[0]);
    if (!err) return put.apply(this, args);
    try { const n = JSON.parse(localStorage.getItem("gv-test-refused") || "[]"); n.push(this.name);
          localStorage.setItem("gv-test-refused", JSON.stringify(n)); } catch (e) { /* storage blocked */ }
    if (this.autoIncrement) throw err;                       // (add() would only make another key)
    const req = put.apply(this, args), clash = add.apply(this, args);
    for (const o of [clash, this.transaction]) Object.defineProperty(o, "error", { configurable: true, get: () => err });
    return req;
  };
})();"""
REC_REFUSED = "JSON.parse(localStorage.getItem('gv-test-refused') || '[]')"
# a full device: the sound's puts, while the check says so (window.__gvFull)
IDB_FULL = IDB_REFUSE % """(store) => window.__gvFull && store === "sound"
    ? new DOMException("The device is out of space (a test)", "QuotaExceededError") : null"""
# Safari's private window (WebKit 156347): any put whose value holds a Blob (or File)
BLOB_REFUSED = "UnknownError: Error preparing Blob/File data to be stored in object store"
IDB_NO_BLOBS = IDB_REFUSE % """(store, value) => {
    const blob = (v, depth) => v instanceof Blob || (depth < 5 && !!v && typeof v === "object" && !(v instanceof ArrayBuffer)
      && !ArrayBuffer.isView(v) && Object.values(v).some((x) => blob(x, depth + 1)));
    return blob(value, 0) ? new DOMException("Error preparing Blob/File data to be stored in object store", "UnknownError") : null;
  }"""
# the refusal works: in a database of its own, a record holding a Blob is refused, one holding bytes is stored
# (→ what each put came to; then the database is deleted and the note of refusals emptied)
BLOB_PROBE = """async () => {
  const db = await new Promise((res, rej) => { const r = indexedDB.open("gv-test-probe", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("s", { keyPath: "k" });
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const put = (v) => new Promise((res) => { const tx = db.transaction(["s"], "readwrite");
    tx.oncomplete = () => res("stored");
    tx.onabort = () => res(tx.error ? tx.error.name + ": " + tx.error.message : "aborted");
    tx.objectStore("s").put(v); });
  const out = [await put({ k: 1, sound: new Blob([new Uint8Array(8)]) }), await put({ k: 2, sound: new Uint8Array(8).buffer })];
  db.close();
  await new Promise((r) => { const q = indexedDB.deleteDatabase("gv-test-probe"); q.onsuccess = q.onerror = q.onblocked = () => r(); });
  localStorage.removeItem("gv-test-refused");
  return out;
}"""


def tone_wav(sec: float, rate: int = 44100) -> bytes:
    """A recording the visitor made elsewhere (Voice Memos …): a WAV of a 440 Hz tone, mono, 16-bit."""
    pcm = array("h", (round(12000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(round(sec * rate))))
    if sys.byteorder == "big":
        pcm.byteswap()
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


def until(page, js: str, what: str, timeout: int = 15_000) -> None:
    """Wait for `js` (a function's source) to be true — else fail saying `what`, and where the recorder was."""
    from playwright.sync_api import TimeoutError as Timeout
    try:
        page.wait_for_function(js, timeout=timeout)
    except Timeout:
        try:
            now = page.evaluate(REC_NOW)
        except Exception as e:  # (the page went)
            now = f"({type(e).__name__}: {str(e).splitlines()[0][:120]})"
        raise AssertionError(f"{what} — not within {timeout / 1000:g} s; the recorder: {now}") from None


class RecorderKeepsTakes(RecorderPage, unittest.TestCase):
    """A take stays on the device until the visitor deletes it: across the site's pages, where the browser refuses
    Blobs, and on a full device (it asks before a link is followed, and saves the take once there is room)."""

    SECONDS = 4                                   # the recording added (44.1 kHz: what the recorder decodes it to)

    @classmethod
    def setUpClass(cls):
        words = json.loads(REC_WORDS.read_text(encoding="utf-8"))
        cls.words = {k.rsplit(".", 1)[1]: v["en"] for k, v in words.items() if k.startswith("community.recorder.")}
        cls.words_es = {k.rsplit(".", 1)[1]: v["es"] for k, v in words.items() if k.startswith("community.recorder.")}

    def add_recording(self, page) -> None:
        """'Add a recording', and a WAV chosen in the file chooser."""
        with page.expect_file_chooser(timeout=10_000) as chooser:
            page.click(REC_IMPORT)
        chooser.value.set_files(files=[{"name": "My story.wav", "mimeType": "audio/wav",
                                        "buffer": tone_wav(self.SECONDS)}])

    def follow(self, page, link: str, path: str) -> None:
        """A tap on a link of the page, and the page it opens (`path`) loaded, in the same tab."""
        page.click(link)
        page.wait_for_url(url(path), wait_until="load", timeout=30_000)

    def kept(self, page, take: str, mp3: int) -> None:
        """This page lists the take, saved, and its player plays its MP3 (`mp3` bytes), read back from the device."""
        where = page.url
        self.assertEqual(page.evaluate(f"{REC_APP}.takes.map((t) => [t.id, t.saved, t.damaged])"),
                         [[take, True, False]], f"{where}: the take is listed, saved")
        page.wait_for_selector("#recorder li.cm-rec-take audio", state="visible", timeout=5000)
        audio = page.evaluate(REC_AUDIO)
        self.assertIsNotNone(audio, f"{where}: the take has a player")
        self.assertTrue(mpeg_frame(bytes(audio["head"])), f"{where}: it plays as an MP3 ({bytes(audio['head']).hex()})")
        self.assertEqual(audio["size"], mp3, f"{where}: the MP3 it was saved with")
        self.assertAlmostEqual(audio["duration"], self.SECONDS, delta=0.5, msg=f"{where}: the take's length")
        self.shows(page, REC_STORE_BOX, [], f"{where}: nothing to say about where the takes are")
        self.shows(page, REC_BADGES, [], f"{where}: no badge (saved)")
        # how long it is kept: Chrome's line (headless Chrome is Chrome — not Safari's 7 days, r10 A24), after the sentence
        # that a closed page loses nothing — true in a normal tab (r10 V2: shown only where it holds)
        said = self.words_es if "/es/" in where else self.words
        self.shows(page, REC_KEPT_LINE, [said["p_kept_base"], said["p_kept_may"]], f"{where}: the “This device” line")
        self.assertFalse(page.evaluate(REC_HOLD), f"{where}: nothing holds the page")

    def kept_across_pages(self, ctx):
        """(a) A recording added and saved; a footer link to Events, one back to Share your story, then the header's
        ES: it is there all along, and nothing asked. → the last page (/es/contribute/)."""
        prefix = S["server"].prefix
        errors, asked = [], []
        page = self.visit(ctx, "contribute/", errors, asked)
        page.wait_for_function(WORKER_READY, timeout=30_000)        # the offline worker runs the site, as on a phone
        self.assertEqual(page.evaluate(REC_IDB), REC_IDB_NONE, "a new profile has no take")
        self.add_recording(page)
        until(page, f"() => {REC_APP}.takes.length === 1 && {REC_APP}.takes[0].saved && !{REC_APP}.atRisk()",
              "the recording added is saved on this device", 30_000)
        take = page.evaluate(f"(({{ id, src, samples, rate }}) => ({{ id, src, samples, rate }}))({REC_APP}.takes[0])")
        self.assertEqual((take["src"], take["rate"], take["samples"]), ("file", 44100, self.SECONDS * 44100), take)
        stored = page.evaluate(REC_IDB)
        # on this device: one final record (no draft left), its PCM — every byte once — and its MP3, all as bytes
        self.assertEqual((stored["takes"], stored["drafts"], stored["notBytes"]), (1, 0, 0), stored)
        self.assertGreaterEqual(stored["mp3"], 1, stored)
        self.assertEqual(stored["pcmBytes"], take["samples"] * 2, stored)
        audio = page.evaluate(REC_AUDIO)
        self.assertTrue(audio and mpeg_frame(bytes(audio["head"])), f"the take plays as an MP3: {audio}")
        self.kept(page, take["id"], audio["size"])

        self.follow(page, SITE_LINK.format(prefix + "events/"), "events/")
        self.assertTrue(page.evaluate("!!navigator.serviceWorker.controller"), "Events came through the offline worker")
        self.follow(page, SITE_LINK.format(prefix + "contribute/"), "contribute/")
        self.ready(page)
        self.kept(page, take["id"], audio["size"])
        self.follow(page, ".site-header [data-lang-switch]", "es/contribute/")
        self.ready(page)
        self.kept(page, take["id"], audio["size"])
        self.assertEqual(page.evaluate(REC_IDB), stored, "the device keeps it as it was saved")
        self.assertEqual(errors, [])
        self.assertEqual(asked, [], "a saved take: leaving the page asks nothing")
        return page

    def test_a_take_is_still_there_after_a_link_away_and_back(self):
        ctx = new_context(1280, 900, service_workers="allow")
        try:
            self.kept_across_pages(ctx)
        finally:
            ctx.close()

    def test_a_take_is_kept_where_the_browser_refuses_blobs(self):
        # (c) Safari's private window, in this browser: any put of a Blob fails as WebKit fails it
        ctx = new_context(1280, 900, service_workers="allow")
        ctx.add_init_script(IDB_NO_BLOBS)
        try:
            probe = open_page(ctx, "about/")
            self.assertEqual(probe.evaluate(BLOB_PROBE), [BLOB_REFUSED, "stored"],
                             "this browser refuses a Blob now, and stores bytes (else nothing was checked)")
            probe.close()
            page = self.kept_across_pages(ctx)
            self.assertEqual(page.evaluate(REC_REFUSED), [], "the recorder never offered IndexedDB a Blob")
        finally:
            ctx.close()

    def test_a_full_device_asks_before_a_link_and_saves_once_there_is_room(self):
        # (b) the device is full: the take's sound can't be written (puts to "sound": QuotaExceededError)
        prefix, w = S["server"].prefix, self.words
        events = SITE_LINK.format(prefix + "events/")
        errors, asked = [], []

        def answer(d):                                 # Cancel ("stay"), as a person answers: not at once
            asked.append((d.type, d.message))
            # (an answer within 50 ms counts as "no dialog shown" — a browser that has none: the link goes on)
            time.sleep(0.15)
            d.dismiss()

        ctx = new_context(1280, 900, service_workers="allow")
        ctx.add_init_script(IDB_FULL)
        try:
            page = open_page(ctx, "contribute/", errors)
            page.on("dialog", answer)
            self.ready(page)
            page.wait_for_function(WORKER_READY, timeout=30_000)
            say = json.loads(page.text_content("#rec-config"))["s"]
            page.evaluate("window.__gvFull = true")
            self.add_recording(page)
            until(page, f"() => {{ const a = {REC_APP}; return a.takes.length === 1 && a.storeNote() === 'full' && "
                        "!a.takes[0].saving; }", "a full device: the take isn't saved, and the page says so", 30_000)
            # the lasting box says the device is full (with Try again); the take says it isn't saved, and its size
            self.shows(page, REC_STORE_BOX, [w["st_full"], w["b_retry"]])
            self.shows(page, REC_BADGES, [w["t_unsaved"]])
            # …and so does the notice by the main button (on a phone the box is a screen or two below it, r10 A12)
            self.shows(page, REC_NOTICE, [w["n_unsaved"].replace("{name}", "Take 1")], "the main button's notice")
            self.shows(page, f"() => ({REC_SIZES})().length", 1, "the take's size is shown")
            self.assertRegex(page.evaluate(REC_SIZES)[0], r"\d", "the take's size on the device")
            self.assertTrue(page.evaluate(REC_HOLD), "html.cm-rec-hold: the page holds on to the take")
            audio = page.evaluate(REC_AUDIO)
            self.assertTrue(audio and mpeg_frame(bytes(audio["head"])), f"it still plays, from this page: {audio}")

            # a link to another page of the site: asked first; Cancel — the page stays as it was
            page.evaluate("window.__gvStay = 1")
            page.click(events)
            page.wait_for_timeout(1000)                # (a page that leaves has begun to by now)
            self.assertEqual(asked, [("confirm", say["leave_unsaved"])])
            self.assertEqual(page.url, url("contribute/"))
            self.assertEqual(page.evaluate("window.__gvStay"), 1, "the same page, not a new one")
            self.assertEqual(page.evaluate(f"{REC_APP}.takes.map((t) => t.saved)"), [False])

            # the footer's calendar file (.ics, this tab, no download attribute): nothing leaves — no question from the
            # page, and the browser's own lets it pass (r10 A22)
            page.click(SITE_LINK.format(prefix + "events.ics"))
            page.wait_for_timeout(1000)
            self.assertEqual(len(asked), 1, f"the calendar link: no question ({asked})")
            self.assertEqual((page.url, page.evaluate("window.__gvStay")), (url("contribute/"), 1), "the page stayed")

            # room again (the device has space at the tap: the 20-second retry can't come first), and Try again
            page.evaluate(f"() => document.querySelector({json.dumps(REC_RETRY)}).addEventListener('pointerdown', "
                          "() => { window.__gvFull = false; }, { once: true })")
            page.evaluate(NOTE_SAID)
            page.click(REC_RETRY)
            until(page, f"() => {{ const a = {REC_APP}; return a.takes.length === 1 && a.takes[0].saved && "
                        f"a.storeNote() === '' && !{REC_HOLD}; }}", "Try again, with room: the take is saved", 20_000)
            self.shows(page, REC_STORE_BOX, [], "the box is gone")
            self.shows(page, REC_BADGES, [], "and the take's badge")
            self.shows(page, REC_SIZES, [], "and its size")
            self.shows(page, REC_NOTICE, [], "and the main button's notice")
            # the button went with the box: the keyboard goes to the takes' heading, and the save is said (r10 A14)
            self.shows(page, "() => document.activeElement && document.activeElement.id", "rec-takes-title",
                       "the keyboard, once Try again's box is gone")
            self.assertIn(w["a_saved"].replace("{name}", "Take 1").replace("{time}", "4 seconds"), page.evaluate("window.__gvSaid"))

            # the link now leaves, asking nothing
            self.follow(page, events, "events/")
            self.assertEqual(len(asked), 1, f"a saved take: no question ({asked})")
            stored = page.evaluate(REC_IDB)
            self.assertEqual((stored["takes"], stored["drafts"], stored["notBytes"]), (1, 0, 0), stored)
            self.assertEqual(stored["pcmBytes"], stored["samples"] * 2, stored)
            self.assertIn("sound", page.evaluate(REC_REFUSED), "the device was full (else nothing was checked)")
        finally:
            ctx.close()
        self.assertEqual(errors, [])


# the "Updated — Reload" notice of a new version, shown (its Reload button visible)
UPDATE_SHOWN = """() => { const b = document.querySelector('.pwa-toast[data-kind="update"]:not([hidden]) [data-pwa-act="update"]');
  return !!(b && b.getClientRects().length); }"""
# what the page says to a screen reader (GV.announce), from now on: window.__gvSaid
NOTE_SAID = """() => { window.__gvSaid = []; const say = GV.announce;
  GV.announce = (m) => { window.__gvSaid.push(String(m)); if (say) say(m); }; }"""
# how often the page has said that a new version is ready (since NOTE_SAID)
UPDATE_SAID = "window.__gvSaid.filter((m) => /new version/i.test(m)).length"


def newer_worker(tag: str) -> Path:
    """sw.js as a new version of the site would have it (its version + "-tag"): a file the site server can answer
    with (overrides)."""
    sw = (S["site"] / "sw.js").read_text(encoding="utf-8")
    m = re.search(r'"version": "([^"]+)"', sw)
    if not m:
        raise AssertionError("sw.js names its version")
    newer = S["tmp"] / f"sw-{tag}.js"
    newer.write_text(sw.replace(m.group(0), f'"version": "{m.group(1)}-{tag}"', 1), encoding="utf-8")
    return newer


class RecorderTopicAndCheck(RecorderPage, unittest.TestCase):
    """Round 12: "What will you talk about?" chosen from a La Viña topic's link, and the device check — in a browser, where
    the scroll, the list's drawing, the Permissions API and IndexedDB are real."""

    def test_a_topic_link_and_the_device_check(self):
        words = json.loads(REC_WORDS.read_text(encoding="utf-8"))
        for lang, path in (("en", "contribute/"), ("es", "es/contribute/")):
            with self.subTest(lang=lang):
                w = {k[len("community.recorder.rep_"):]: v[lang] for k, v in words.items() if k.startswith("community.recorder.rep_")}
                errors, asked = [], []
                ctx = new_context(390, 844, lang=lang)
                # every request for the microphone counted (none is granted here: a request would show the browser's question)
                ctx.add_init_script("(() => { window.__gvMic = 0; const md = navigator.mediaDevices;"
                                    " if (md && md.getUserMedia) { const g = md.getUserMedia.bind(md);"
                                    " md.getUserMedia = (c) => { window.__gvMic++; return g(c); }; } })();")
                try:
                    page = self.visit(ctx, path, errors, asked)
                    link = page.locator("a[data-rec-topic]").first
                    topic = link.get_attribute("data-rec-topic")
                    link.scroll_into_view_if_needed()
                    link.click()
                    until(page, f"() => {REC_APP}.send.topic === {json.dumps(topic)} && {REC_APP}.pub === 'lv'",
                          "the link chose La Viña and its topic", 5000)
                    self.assertEqual(page.evaluate("location.hash"), "", "a scroll, never a change of address")
                    until(page, "() => document.activeElement && document.activeElement.id === 'recorder-title'",
                          "the recorder's heading has the focus", 5000)
                    shown = page.evaluate("[...document.querySelectorAll('#recorder .cm-rec-topic select')].filter((s) => s.offsetParent)"
                                          ".map((s) => s.options[s.selectedIndex].textContent.trim())")
                    self.assertEqual(len(shown), 1, "one list shows: La Viña's")
                    self.assertTrue(shown[0].startswith(topic), shown)

                    # the device check: made as it opens, in the page's language
                    page.click("#recorder .cm-rec-check > summary")
                    until(page, f"() => !!{REC_APP}.diag.text && !{REC_APP}.diag.busy", "the report is made", 30_000)
                    text = page.inner_text("#recorder .cm-rec-check pre")
                    self.assertTrue(text.startswith(w["title"]), text[:80])
                    self.assertIn(f"{w['l_takes']}: 0", text)
                    self.assertIn(f"{w['l_idb']}: {w['v_idb_ok']}", text)
                    self.assertIn(f"{w['l_record']}: {w['v_record_worklet']}", text)
                    self.assertNotIn(topic, text, "the topic chosen is not in the report")
                    self.assertEqual(page.evaluate("window.__gvMic"), 0, "the check never asks for the microphone")
                    cfg = json.loads(page.text_content("#rec-config"))
                    href = page.get_attribute("#recorder .cm-rec-check a[href^='mailto:']", "href") or ""
                    self.assertTrue(href.startswith(f"mailto:{cfg['diag']['to']}?subject="), href[:80])
                    # its own database is deleted after; the takes' is never made by it
                    until(page, "async () => !indexedDB.databases || !(await indexedDB.databases()).some((d) => d.name === 'gvlv-rec-check')",
                          "the check's own database is deleted", 5000)
                finally:
                    ctx.close()
                self.assertEqual(errors, [])
                self.assertEqual(asked, [], "nothing asked")


# the "If Walls Could Talk" note opened, and the boxes of its links: the two alone in their row (a.tap-link), and La
# Viña's in its sentence below
WALLS_BOXES = """() => {
  const d = [...document.querySelectorAll("details")].find((x) => /If Walls Could Talk/.test((x.querySelector("summary") || {}).textContent || ""));
  if (!d) return null;
  d.open = true;
  const box = (el) => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, text: el.textContent.trim() }; };
  return { links: [...d.querySelectorAll("a.tap-link")].map(box), lv: [...d.querySelectorAll("a:not(.tap-link)")].map(box) };
}"""


class WallsLinks(unittest.TestCase):
    """Round 12 review: the "If Walls Could Talk" note's two standalone links are a target of 24px at least with a mouse
    too (WCAG 2.5.8 — axe target-size: 20px at 1280, with the La Viña link right below), 44px on a phone (tap-link)."""

    def test_the_two_links_are_big_enough_and_apart(self):
        for lang, path in (("en", "contribute/"), ("es", "es/contribute/")):
            for width, least in ((1280, 24), (390, 44)):
                with self.subTest(lang=lang, width=width):
                    ctx = new_context(width, 800, lang=lang)
                    try:
                        got = open_page(ctx, path).evaluate(WALLS_BOXES)
                    finally:
                        ctx.close()
                    self.assertIsNotNone(got, "the note is on the page")
                    links, lv = got["links"], got["lv"]
                    self.assertEqual(len(links), 2, links)
                    self.assertEqual(len(lv), 1, lv)
                    for b in links:
                        self.assertGreaterEqual(round(b["h"], 1), least, b)
                        self.assertGreaterEqual(b["w"], 24, b)
                    boxes = links + lv
                    for i, a in enumerate(boxes):
                        for b in boxes[i + 1:]:
                            apart = (a["x"] + a["w"] <= b["x"] + 0.5 or b["x"] + b["w"] <= a["x"] + 0.5
                                     or a["y"] + a["h"] <= b["y"] + 0.5 or b["y"] + b["h"] <= a["y"] + 0.5)
                            self.assertTrue(apart, f"{a['text']!r} and {b['text']!r} overlap: {a} {b}")


class RecorderHoldsUpdate(RecorderPage, unittest.TestCase):
    """(d) A new version of the site while a take is being recorded: pwa.js holds its "Updated — Reload" notice
    (html.cm-rec-on / cm-rec-hold: its Reload would end the take — an iPhone never asks before a reload), and shows it
    once the take is saved; what it says to a screen reader waits with it (said once, as it shows). The fake
    microphone's browser with the offline worker on, and a new sw.js from the site server's overrides (as
    OfflineUpdate)."""

    def tearDown(self):
        S["overrides"].unlink(missing_ok=True)

    def test_the_update_notice_waits_until_the_take_is_saved(self):
        prefix = S["server"].prefix
        newer = newer_worker("rec")
        errors, asked = [], []
        ctx = self.browser(S["tmp"] / "recorder-update", "en", service_workers="allow")
        try:
            page = self.visit(ctx, "contribute/", errors, asked)
            page.wait_for_function(WORKER_READY, timeout=30_000)
            page.wait_for_timeout(1500)                # (the first visit's own keeping of the open tab)
            page.evaluate(NOTE_SAID)
            self.assertFalse(page.evaluate(UPDATE_SHOWN), "no new version yet")
            page.click("#recorder .cm-rec-go")
            page.wait_for_function(f"() => {REC_STATE} === 'recording'", timeout=15_000)

            # a new version of the site, installed and waiting, while the take is being recorded
            S["overrides"].write_text(json.dumps({"files": {prefix + "sw.js": str(newer)}}), encoding="utf-8")
            self.assertEqual(page.evaluate(NEW_VERSION_WAITING), "installed", "the new version installed and waits")
            # no notice — and nothing said to a screen reader (r10 nav:F4: spoken mid-take, the line went into the
            # recording, and it said "Reload" just when a reload would lose the take)
            page.wait_for_timeout(2000)
            self.assertEqual(page.evaluate(REC_STATE), "recording")
            self.assertFalse(page.evaluate(UPDATE_SHOWN), "“Updated — Reload” must wait while a take is being recorded")
            self.assertEqual(page.evaluate(UPDATE_SAID), 0, "nothing said about the new version while it waits")

            # Stop and save: once the take is saved, the notice shows — and is said then, once
            page.click("#recorder .cm-rec-go")
            until(page, f"() => {REC_STATE} === 'idle' && {REC_APP}.takes.length === 1 && {REC_APP}.takes[0].saved",
                  "the take is saved", 20_000)
            until(page, UPDATE_SHOWN, "“Updated — Reload” shows once the take is saved", 5000)
            until(page, f"() => {UPDATE_SAID} > 0", "the notice is said as it shows", 5000)
            page.wait_for_timeout(500)
            self.assertEqual(page.evaluate(UPDATE_SAID), 1, "said once")
            self.assertEqual(page.evaluate("['cm-rec-on', 'cm-rec-hold'].filter((c) => "
                                           "document.documentElement.classList.contains(c))"), [])
        finally:
            ctx.close()
        self.assertEqual(errors, [])
        self.assertEqual(asked, [])


if __name__ == "__main__":
    unittest.main()
