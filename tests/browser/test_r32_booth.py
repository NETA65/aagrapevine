"""Round 32 · the booth display's own window and the section's Share / Copy link / "#", in a real browser
(tests/browser/__init__.py says how to run these; the site server, the browser and the helpers are
test_site_in_browser.py's; the script's own checks are tests/test_booth_screen.py OwnWindow, on a pretend page):

  * OwnWindow   — on a laptop or desktop (a mouse), English and Spanish: "Start the booth" opens a pop-up window
                  (blank, then at the page language's …/about/?booth=start; named gvlv-booth) that shows the show's
                  dialog with "Move this window where you want it, then tap for full screen & sound"; the About page
                  plays no show of its own and says the show is playing in its own window; Start again brings that
                  window forward (no second one) and Settings opens Settings in it; Esc → "Leave?" ("… this window
                  closes") → Leave closes the window, and the page's note goes.
  * Reload      — the About page reloaded while the show plays in its window (tapped once: sound), Settings at once:
                  the window answers the page's ask as it opens (or, with no channel, is found by its name) and is
                  never loaded again (a mark left on it is still there, no tap asked again), its Settings open, no
                  second window.
  * SecondTab   — tab B, the About page opened on its own (not by tab A, which started the show): B says the show
                  plays in its own window (it hears it over the channel of the site's pages), its Start opens no
                  second window, its Stop stops the show (no PIN) and both pages' notes go. B asks the window as it
                  opens: with the window's 5-s "alive" put off, B still hears it at once and its Start right after
                  opens no second window.
  * TakenOver   — tab C, an About tab that A opened and that has no channel (a browser without one), clicks Settings
                  before it hears the window: the browser finds the window by its name and makes C its opener (Edge,
                  Chrome) — A's Settings and Stop still reach the window.
  * PinBeside   — a PIN set (stored before any page script): with no show playing, the page's Settings opens a new
                  window with Settings and no PIN box (the way back in when the PIN is forgotten: Remove the PIN
                  there, and the page's lock goes); a window caught loading again (F5 at the booth, its booth.js held)
                  when the About page, loaded again meanwhile, clicks Settings is sent to the show alone — no Settings
                  without the PIN, the next Settings brings up the PIN box; a window loaded again keeps the page's
                  note, but one whose reload fails (its booth.js not loaded) frees the page within 12 s and Start
                  brings the show back in that same window; the page's Stop then Settings (and Settings then Stop)
                  leave the window's PIN box as the first ask made it.
  * Blocked     — a browser that blocks the window (window.open answers null): the show plays on the page, its toast
                  says the window was blocked.
  * Touch       — a phone (touch, no mouse): Start plays the show on the page, no window.
  * SectionHead — #booth's head has Share and Copy link of the section's own address (…/about/#booth, …/es/about/#booth)
                  and a "#" link to it, beside the title (never in it); Copy link copies that address.

Nothing reaches another site: on top of the browser's own rule (site_browser.NO_OUTSIDE) every request to another
host is answered 404 here (Google's pictures, YouTube), so the show never waits on the internet.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from browser.test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
WORDS = json.loads((ROOT / "src" / "_i18n" / "booth.json").read_text(encoding="utf-8"))
OUTSIDE = re.compile(r"^https?://(?!127\.0\.0\.1[:/])")
DIALOG = "body > .gvb[role=dialog]"


def w(key: str, lang: str) -> str:
    return WORDS[key][lang]


def about(lang: str) -> str:
    return "es/about/" if lang == "es" else "about/"


def local_only(ctx) -> None:
    """Every other site answers 404 (a picture from Google, YouTube's player): the show goes on without them."""
    ctx.route(OUTSIDE, lambda route: route.fulfill(status=404, body=""))


def phone_context():
    ctx = S["browser"].new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, reduced_motion="reduce",
                                   service_workers="block", timezone_id="America/Chicago", locale="en-US")
    local_only(ctx)
    return ctx


class OwnWindow(unittest.TestCase):
    def test_start_opens_the_show_in_its_own_window(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(lang=lang)
                local_only(ctx)
                errors: list[str] = []
                try:
                    page = open_page(ctx, about(lang), errors)
                    self.assertTrue(page.evaluate("() => matchMedia('(hover: hover) and (pointer: fine)').matches"), "a desktop browser")
                    with page.expect_popup(timeout=15_000) as pop:
                        page.click("[data-gvb-start]")
                    win = pop.value
                    win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
                    # (opened blank, then sent to the show's address)
                    win.wait_for_url(re.compile(r"/" + re.escape(about(lang)) + r"\?booth=start$"), timeout=15_000)
                    self.assertEqual(win.evaluate("() => window.name"), "gvlv-booth")
                    win.wait_for_selector(DIALOG, timeout=15_000)
                    chip = win.wait_for_selector("[data-gvb-tapchip]", timeout=15_000)
                    self.assertEqual(chip.inner_text().strip(), w("booth.screen.tap_window", lang))
                    self.assertEqual(win.title(), w("booth.nav", lang) + " — NETA 65")
                    # the About page: no show of its own, the note while the window plays
                    page.wait_for_selector("[data-gvb-win]", state="visible", timeout=5_000)
                    self.assertIn(w("booth.popup_on", lang), page.inner_text("[data-gvb-win]"))
                    self.assertEqual(page.locator(DIALOG).count(), 0)
                    # Start again: that window comes forward, no second one; Settings: opened in it
                    popups = []
                    page.on("popup", lambda p: popups.append(p))
                    page.click("[data-gvb-start]")
                    page.click("[data-gvb-settings]")
                    win.wait_for_selector("[data-gvb-drawer]", state="visible", timeout=5_000)
                    self.assertEqual(popups, [])
                    self.assertEqual(page.locator(DIALOG).count(), 0)
                    win.click("[data-gvb-drawer] [data-gvb-act='settings']")          # (Settings closed again)
                    # Esc → "Leave?" says the window closes → Leave: it closes, and the page's note goes
                    win.keyboard.press("Escape")
                    win.wait_for_selector("[data-gvb-leave]", state="visible", timeout=5_000)
                    self.assertEqual(win.inner_text("#gvb-leave-text").strip(), w("booth.leave_text_win", lang))
                    with win.expect_event("close", timeout=10_000):
                        win.click("[data-gvb-act='leave-yes']")
                    page.wait_for_selector("[data-gvb-win]", state="hidden", timeout=5_000)
                    self.assertEqual(page.locator(DIALOG).count(), 0)
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


def start_window(page):
    """Start the booth from `page` → the show's window, its show playing."""
    with page.expect_popup(timeout=15_000) as pop:
        page.click("[data-gvb-start]")
    win = pop.value
    win.wait_for_url(re.compile(r"\?booth=start$"), timeout=15_000)
    win.wait_for_selector(DIALOG, timeout=15_000)
    page.wait_for_selector("[data-gvb-win]", state="visible", timeout=5_000)
    return win


# the show's window: its 5-s "alive" put off to ten minutes (only its "hello", and what it answers a page, is said)
LATE_ALIVE = """if (window.name === "gvlv-booth") {
  const si = window.setInterval;
  window.setInterval = function (fn, ms) {
    if (ms === 5000 && typeof fn === "function" && /"alive"/.test(String(fn))) ms = 600000;
    return si.apply(window, [fn, ms].concat(Array.prototype.slice.call(arguments, 2)));
  };
}"""
# a tab named "nobc": a browser without BroadcastChannel — and every About page so (the show's window keeps it)
NO_CHANNEL = 'if (window.name === "nobc") { try { window.BroadcastChannel = undefined; } catch (e) {} }'
NO_CHANNEL_PAGES = 'if (window.name !== "gvlv-booth") { try { window.BroadcastChannel = undefined; } catch (e) {} }'


class Reload(unittest.TestCase):
    def test_a_page_loaded_again_hands_the_playing_window_back_as_it_is(self):
        """The About page reloaded while its show plays in its window, then Settings at once (before the window's
        next "alive"): the page asks over the channel as it opens and the window answers it — or, with no channel
        (the page's BroadcastChannel taken away), the window is found by its name —, never loaded again (the show
        would restart, out of full screen, muted): its Settings open in it."""
        for label, init in (("the channel", None), ("no channel: found by its name", NO_CHANNEL_PAGES)):
            with self.subTest(label):
                ctx = new_context()
                local_only(ctx)
                if init:
                    ctx.add_init_script(init)
                errors: list[str] = []
                try:
                    page = open_page(ctx, "about/", errors)
                    win = start_window(page)
                    win.click("[data-gvb-tapchip]")                    # tapped once at the TV: sound (and full screen)
                    win.wait_for_selector("[data-gvb-tapchip]", state="detached", timeout=5_000)
                    win.evaluate("() => { window.__gvbMark = 'first'; }")
                    navs: list[str] = []
                    win.on("framenavigated", lambda f: navs.append(f.url) if f == win.main_frame else None)
                    popups = []
                    ctx.on("page", lambda p: popups.append(p))
                    page.reload(wait_until="load")
                    self.assertEqual(page.evaluate("() => typeof BroadcastChannel === 'function'"), init is None)
                    page.click("[data-gvb-settings]")
                    win.wait_for_selector("[data-gvb-drawer]", state="visible", timeout=5_000)
                    self.assertEqual(win.evaluate("() => window.__gvbMark || null"), "first", "the same page: never loaded again")
                    self.assertEqual(navs, [])
                    self.assertEqual(popups, [], "no second window")
                    self.assertEqual(win.locator("[data-gvb-tapchip]").count(), 0, "no tap asked again: the show was not restarted")
                    page.wait_for_selector("[data-gvb-win]", state="visible", timeout=5_000)
                    self.assertEqual(page.locator(DIALOG).count(), 0)
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


class SecondTab(unittest.TestCase):
    def test_another_about_tab_sees_the_playing_window_and_starts_no_second_show(self):
        """The show plays in its window, started from tab A; tab B is the About page opened on its own (a bookmark,
        a typed address — not opened by A, so the browser cannot find the window by its name from there): B says
        the show plays in its own window, its Start opens no second window, its Stop stops the show (no PIN)."""
        ctx = new_context()
        local_only(ctx)
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            win = start_window(a)
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            b = open_page(ctx, "about/", errors)
            self.assertIsNone(b.evaluate("() => window.opener"), "a page of its own")
            b.wait_for_selector("[data-gvb-win]", state="visible", timeout=10_000)    # (its ping answered at once)
            pages = []
            ctx.on("page", lambda p: pages.append(p))
            b.click("[data-gvb-start]")
            b.wait_for_timeout(1_500)
            self.assertEqual(pages, [], "no second window")
            self.assertEqual(b.locator(DIALOG).count(), 0, "no show on B")
            self.assertFalse(win.is_closed())
            with win.expect_event("close", timeout=10_000):
                b.click('[data-gvb-win-act="stop"]')
            b.wait_for_selector("[data-gvb-win]", state="hidden", timeout=5_000)
            a.wait_for_selector("[data-gvb-win]", state="hidden", timeout=5_000)
            self.assertEqual(pages, [])
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_a_tab_opened_just_now_hears_the_window_at_once(self):
        """B opened while the window's next "alive" is far off (put off here to ten minutes): B asks over the channel
        as it opens and the window answers then and there — B says the show plays in its own window and a Start right
        after opens no second window (before, B saw nothing for up to 5 s, and its Start opened a second show)."""
        ctx = new_context()
        local_only(ctx)
        ctx.add_init_script(LATE_ALIVE)
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            win = start_window(a)
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            b = open_page(ctx, "about/", errors)
            pages = []
            ctx.on("page", lambda p: pages.append(p))
            b.wait_for_selector("[data-gvb-win]", state="visible", timeout=3_000)
            b.click("[data-gvb-start]")
            b.wait_for_timeout(1_500)
            self.assertEqual(pages, [], "no second window")
            self.assertEqual(b.locator(DIALOG).count(), 0, "no show on B")
            self.assertFalse(win.is_closed())
            self.assertEqual(errors, [])
        finally:
            ctx.close()


class TakenOver(unittest.TestCase):
    def test_the_first_page_still_asks_the_window_after_another_tab_took_it(self):
        """C, an About tab A opened (the same group of tabs) with no channel, clicks Settings before it hears the
        window: the browser finds the window by its name and Edge and Chrome make C its opener. A still holds the
        window's handle and asks it by postMessage: its Settings open in the window, its Stop stops the show at once
        (not the page's 3-s close of a window that does not answer)."""
        ctx = new_context()
        local_only(ctx)
        ctx.add_init_script(NO_CHANNEL)
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            win = start_window(a)
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            with a.expect_popup(timeout=15_000) as pc:
                a.evaluate("() => { window.open(location.href, 'nobc'); }")
            c = pc.value
            c.on("pageerror", lambda e: errors.append(f"C: {str(e).splitlines()[0][:200]}"))
            c.wait_for_load_state("load")
            self.assertFalse(c.evaluate("() => typeof BroadcastChannel === 'function'"))
            pages = []
            ctx.on("page", lambda p: pages.append(p))
            c.click("[data-gvb-settings]")                       # found by its name: C is its opener now
            win.wait_for_selector("[data-gvb-drawer]", state="visible", timeout=5_000)
            self.assertEqual(pages, [], "no second window")
            win.click("[data-gvb-drawer] [data-gvb-act='settings']")          # (Settings closed again)
            win.wait_for_selector("[data-gvb-drawer]", state="hidden", timeout=5_000)
            a.click("[data-gvb-settings]")
            win.wait_for_selector("[data-gvb-drawer]", state="visible", timeout=2_500)
            win.click("[data-gvb-drawer] [data-gvb-act='settings']")
            win.wait_for_selector("[data-gvb-drawer]", state="hidden", timeout=5_000)
            with win.expect_event("close", timeout=2_500):
                a.click('[data-gvb-win-act="stop"]')
            a.wait_for_selector("[data-gvb-win]", state="hidden", timeout=5_000)
            self.assertEqual(pages, [])
            self.assertEqual(errors, [])
        finally:
            ctx.close()


# a PIN set on this device (Settings → Kiosk) before any page script: the show's window asks for it
SEED_PIN = """(() => { try { if (!localStorage.getItem("gv-booth-v1")) localStorage.setItem("gv-booth-v1", '{"pin":"1234"}'); } catch (e) {} })();"""
BOOTH_JS = re.compile(r"/assets/js/booth\.js")


def pin_context():
    ctx = new_context()
    local_only(ctx)
    ctx.add_init_script(SEED_PIN)
    return ctx


def pin_box(win) -> str | None:
    """The window's PIN box: its line ("The PIN opens the settings." …), or None while it is not up."""
    return win.evaluate("() => { const b = document.querySelector('[data-gvb-pin]'); return b && !b.hidden"
                        " ? document.querySelector('[data-gvb-pin-why]').textContent : null; }")


def drawer_open(win) -> bool:
    return win.evaluate("() => { const d = document.querySelector('[data-gvb-drawer]'); return !!d && !d.hidden; }")


def type_pin(win, pin: str = "1234") -> None:
    win.fill("[data-gvb-pin-input]", pin)
    win.press("[data-gvb-pin-input]", "Enter")


class PinBeside(unittest.TestCase):
    """A PIN set and the show in its own window: the About page beside it never gets past the PIN — nor stays stuck."""

    def test_settings_with_no_window_open_them_without_the_pin(self):
        """No show playing: the page's Settings opens a new window — blank as window.open hands it back, so it gets
        Settings without the PIN (&tab=event, dropped from its address at once) — the way back in when the PIN is
        forgotten: Kiosk → Remove the PIN, and the page beside it, which said the window asks for the PIN, no longer
        does."""
        ctx = pin_context()
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            with a.expect_popup(timeout=15_000) as pop:
                a.click("[data-gvb-settings]")
            win = pop.value
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            win.wait_for_url(re.compile(r"/about/\?booth=start(&tab=event)?$"), timeout=15_000)
            win.wait_for_selector("[data-gvb-drawer]", state="visible", timeout=15_000)
            self.assertIsNone(pin_box(win), "no PIN asked")
            self.assertEqual(win.get_attribute('[data-gvb-tab="event"]', "aria-selected"), "true", "on the Event tab")
            self.assertEqual(win.evaluate("() => location.search"), "?booth=start", "&tab left the address")
            a.wait_for_selector("[data-gvb-win]", state="visible", timeout=5_000)
            self.assertTrue(a.locator("[data-gvb-win-pin]").is_visible(), "the page: the window asks for the PIN")
            win.click('[data-gvb-tab="kiosk"]')
            win.click('[data-gvb-key="pin-clear"]')
            win.wait_for_selector(f"[data-gvb-toast]:has-text('{w('booth.ki_pin_removed', 'en')}')", timeout=5_000)
            a.wait_for_selector("[data-gvb-win-pin]", state="hidden", timeout=12_000)
            self.assertFalse(a.locator('[data-gvb-q="event"]').is_disabled(), "the quick controls open again")
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_a_window_caught_loading_keeps_its_pin(self):
        """F5 at the booth, and before its show is drawn again (its booth.js held here) the About page — loaded again
        meanwhile, so it has not heard the window — clicks Settings: the browser hands back the loading window by its
        name and the page sends it to the show alone (Settings without the PIN only go to a blank window the click
        made). The show comes back without Settings; the page's next Settings brings up the PIN box."""
        ctx = pin_context()
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            win = start_window(a)
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            hold, held = {"on": True}, []

            def gate(route):
                if hold["on"]:
                    held.append(route)
                else:
                    route.continue_()
            win.route(BOOTH_JS, gate)
            win.evaluate("() => setTimeout(() => location.reload(), 0)")
            for _ in range(50):
                if held:
                    break
                a.wait_for_timeout(100)
            self.assertTrue(held, "the window's reload waits for its booth.js")
            a.reload(wait_until="load")
            a.wait_for_timeout(800)
            self.assertTrue(a.locator("[data-gvb-win]").is_hidden(), "the page has not heard the window")
            popups = []
            ctx.on("page", lambda p: popups.append(p))
            a.click("[data-gvb-settings]")
            a.wait_for_timeout(400)
            hold["on"] = False
            for r in held:
                try:
                    r.continue_()
                except Exception:   # (its navigation was replaced meanwhile)
                    pass
            win.wait_for_selector(DIALOG, timeout=15_000)
            win.wait_for_timeout(1_500)
            self.assertFalse(drawer_open(win), "no Settings without the PIN")
            self.assertIsNone(pin_box(win))
            self.assertEqual(popups, [], "no second window")
            a.wait_for_selector("[data-gvb-win]", state="visible", timeout=10_000)
            a.click("[data-gvb-settings]")
            win.wait_for_selector("[data-gvb-pin]", state="visible", timeout=5_000)
            self.assertEqual(pin_box(win), w("booth.pin_for_settings", "en"))
            self.assertFalse(drawer_open(win))
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_a_window_left_without_a_show_frees_the_page(self):
        """The window loaded again (F5): the page's note stays. Then a reload that fails (its booth.js does not load,
        as on a venue's network drop): the window stays open with no show and says nothing more — within 12 s and
        the page's next look the note goes, the quick controls open again, and Start brings the show back in that
        same window."""
        ctx = pin_context()
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            win = start_window(a)
            self.assertTrue(a.locator('[data-gvb-q="event"]').is_disabled(), "a PIN: the quick controls wait")
            win.reload(wait_until="load")
            win.wait_for_selector(DIALOG, timeout=15_000)
            a.wait_for_timeout(3_000)
            self.assertTrue(a.locator("[data-gvb-win]").is_visible(), "a reload that plays again: the note stays")
            win.route(BOOTH_JS, lambda route: route.abort())
            win.evaluate("() => setTimeout(() => location.reload(), 0)")
            a.wait_for_selector("[data-gvb-win]", state="hidden", timeout=20_000)
            self.assertFalse(a.locator('[data-gvb-q="event"]').is_disabled(), "the quick controls open again")
            self.assertFalse(win.is_closed())
            win.unroute(BOOTH_JS)
            popups = []
            ctx.on("page", lambda p: popups.append(p))
            a.click("[data-gvb-start]")
            win.wait_for_selector(DIALOG, timeout=15_000)
            a.wait_for_selector("[data-gvb-win]", state="visible", timeout=5_000)
            self.assertEqual(popups, [], "the same window")
            self.assertEqual(a.locator(DIALOG).count(), 0)
            self.assertEqual([e for e in errors if "booth.js" not in e], [])
        finally:
            ctx.close()

    def test_a_pin_box_already_up_keeps_its_ask(self):
        """The page's Stop, then its Settings: the window's box still says the PIN lets you leave, and the PIN closes
        the window. The page's Settings, then its Stop: the box still says the PIN opens the settings, the PIN opens
        them and the show plays on."""
        ctx = pin_context()
        errors: list[str] = []
        try:
            a = open_page(ctx, "about/", errors)
            win = start_window(a)
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            a.click('[data-gvb-win-act="stop"]')
            win.wait_for_selector("[data-gvb-pin]", state="visible", timeout=5_000)
            a.click("[data-gvb-settings]")
            a.wait_for_timeout(700)
            self.assertEqual(pin_box(win), w("booth.pin_for_leave", "en"))
            with win.expect_event("close", timeout=10_000):
                win.fill("[data-gvb-pin-input]", "1234")
                try:
                    win.press("[data-gvb-pin-input]", "Enter")
                except Exception as e:
                    # (the right PIN closes the window: on a busy PC it can close before press() has returned, and
                    # Playwright then raises TargetClosedError — the close itself is what expect_event waits for)
                    if type(e).__name__ != "TargetClosedError":
                        raise
            a.wait_for_selector("[data-gvb-win]", state="hidden", timeout=5_000)
            win = start_window(a)
            win.on("pageerror", lambda e: errors.append(f"window: {str(e).splitlines()[0][:200]}"))
            a.click("[data-gvb-settings]")
            win.wait_for_selector("[data-gvb-pin]", state="visible", timeout=5_000)
            a.click('[data-gvb-win-act="stop"]')
            a.wait_for_timeout(700)
            self.assertEqual(pin_box(win), w("booth.pin_for_settings", "en"))
            type_pin(win)
            win.wait_for_selector("[data-gvb-drawer]", state="visible", timeout=5_000)
            a.wait_for_timeout(3_500)                           # (past the page's 3-s close — never behind a PIN)
            self.assertFalse(win.is_closed(), "the show plays on")
            self.assertEqual(win.locator(DIALOG).count(), 1)
            self.assertEqual(errors, [])
        finally:
            ctx.close()


class Blocked(unittest.TestCase):
    def test_a_blocked_window_plays_the_show_on_the_page(self):
        ctx = new_context()
        local_only(ctx)
        ctx.add_init_script("window.open = function () { return null; };")      # what a pop-up blocker answers
        try:
            page = open_page(ctx, "about/")
            popups = []
            page.on("popup", lambda p: popups.append(p))
            page.click("[data-gvb-start]")
            page.wait_for_selector(DIALOG, timeout=15_000)
            toast = page.wait_for_selector(DIALOG + " [data-gvb-toast]:not(.is-idle)", timeout=5_000)
            self.assertIn(w("booth.popup_blocked", "en"), toast.inner_text())
            self.assertEqual(popups, [])
            self.assertTrue(page.locator("[data-gvb-win]").is_hidden())
        finally:
            ctx.close()


class Touch(unittest.TestCase):
    def test_a_phone_plays_the_show_on_its_own_screen(self):
        ctx = phone_context()
        try:
            page = open_page(ctx, "about/")
            self.assertFalse(page.evaluate("() => matchMedia('(hover: hover) and (pointer: fine)').matches"))
            popups = []
            page.on("popup", lambda p: popups.append(p))
            page.tap("[data-gvb-start]")
            page.wait_for_selector(DIALOG, timeout=15_000)
            page.wait_for_timeout(500)
            self.assertEqual(popups, [])
            self.assertTrue(page.locator("[data-gvb-win]").is_hidden())
        finally:
            ctx.close()


class SectionHead(unittest.TestCase):
    def test_share_copy_link_and_the_hash(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ctx = new_context(lang=lang)
                local_only(ctx)
                try:
                    page = open_page(ctx, about(lang))
                    head = page.locator("#booth .section-head")
                    share, copy, hash_ = (head.locator(s) for s in ("[data-share]", "[data-copy]", "a.gvb-sechash"))
                    for x in (share, copy, hash_):
                        self.assertTrue(x.is_visible())
                    here = ("/es" if lang == "es" else "") + "/about/#booth"
                    self.assertTrue(share.get_attribute("data-share").endswith(here))
                    self.assertEqual(copy.get_attribute("data-copy"), share.get_attribute("data-share"))
                    self.assertEqual(share.get_attribute("data-share-title"), w("booth.nav", lang) + " — NETA 65")
                    self.assertEqual(hash_.get_attribute("href"), "#booth")
                    self.assertEqual(hash_.get_attribute("aria-label"), w("booth.link_section", lang))
                    self.assertEqual(page.inner_text("#booth-title").strip(), w("booth.title", lang))
                    # beside the title, on its line or under it — not stretched across it
                    self.assertLess(hash_.bounding_box()["width"], 80)
                    # Copy link: the address on the clipboard, "Copied!" on the button
                    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
                    copy.click()
                    page.wait_for_function("(b) => /Copied|Copiado/.test(b.textContent)", arg=copy.element_handle(), timeout=5_000)
                    self.assertEqual(page.evaluate("() => navigator.clipboard.readText()"), share.get_attribute("data-share"))
                    # the "#" link: the address names the section
                    hash_.click()
                    page.wait_for_function("() => location.hash === '#booth'", timeout=5_000)
                finally:
                    ctx.close()


if __name__ == "__main__":
    unittest.main()
