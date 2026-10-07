"""The built site in a real browser (tests/browser/__init__.py says how to run these). Each check guards a problem the
round-7 review found that no offline test could see:

  * HeaderFocusRing   — the keyboard focus ring on the header's Search, ES / EN, Aa and theme buttons stands out from
                        what is behind it (3 : 1 at least), at the top of the page (over the dark hero) and scrolled
                        (solid header), in light, dark, high contrast and high contrast dark. Measured on the pixels:
                        the ring's band, focused against not focused (it was 1.45 : 1).
  * StickyBarFocus    — What's New's sticky filter bar never hides the element keyboard focus is on, tabbing forward
                        and back, on a laptop and a phone (it hid 7 of them); the room left for it is measured again
                        when relaxed spacing goes off (the bar turns sticky at the same size).
  * LargeTextPhone    — no page scrolls sideways on a 360-pixel phone at 150 % text: Home, About, Published, Events,
                        Meetings, in English and Spanish (About's booth steps did).
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
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import statistics
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.site_browser import BrowserMissing, SiteServer, launch  # noqa: E402

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


class LargeTextPhone(unittest.TestCase):
    def test_no_sideways_scroll_at_150_percent_on_a_phone(self):
        problems = []
        for lang in ("en", "es"):
            ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
            try:
                for path in LARGE_TEXT_PAGES:
                    page = open_page(ctx, ("es/" if lang == "es" else "") + path)
                    self.assertEqual(page.get_attribute("html", "data-text"), "150", "the page took the saved text size")
                    page.wait_for_timeout(300)                # (late layout: pictures, the scripts' own changes)
                    r = page.evaluate(SIDEWAYS)
                    if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                        problems.append(f"/{'es/' if lang == 'es' else ''}{path}: scrolls {r['moved']} px sideways "
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


if __name__ == "__main__":
    unittest.main()
