"""Round 35 · words that only become true later, in a real browser (tests/browser/__init__.py says how to run these;
they share test_site_in_browser.py's site server and browser). Since round 35 the build leaves such words out of the
HTML — a crawler that runs no script read them as the page's text — and the page writes them in when they become
true (app.js GV.say, data-gv-say; Alpine x-text). The built pages on their own: tests/test_r35_raw.py.

  * LiveLabels  — during the committee meeting Home's card says "Happening now — come on in!" (and the Grapevine
                  Meeting's during its own), /meetings/' countdown "Live now", five minutes before "Starting soon";
                  otherwise the pill is hidden and wordless. "Meets today" on the groups that meet today.
  * EmptyStates — what a list says once it is empty: /bulletin/ when its last post has expired, /meetings/ and
                  /published/ (its cards and its archive) when nothing matches, Home's Published writers once its
                  stories have left the 60 days; the daily quote's "Today" / "Yesterday".
  * Menu        — the phone menu: focus on Close at once, the page behind locked (no scroll, inert) a moment after,
                  never left locked by a close that comes first, and unlocked before focus goes back to Menu; the
                  drawer's reading-settings button still opens the panel.
"""
from __future__ import annotations

import html
import json
import re
import unittest
from datetime import datetime, timedelta, timezone

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

def i18n() -> dict:
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "src" / "_i18n"
    out: dict = {}
    for f in sorted(root.glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


T = i18n()


def built(path: str) -> str:
    return (S["site"] / path / "index.html").read_text(encoding="utf-8")


def iso(s: str, **delta) -> str:
    return (datetime.fromisoformat(s.replace("Z", "+00:00")) + timedelta(**delta)).astimezone(timezone.utc).isoformat()


def central_noon(ymd: str, plus_days: int = 0) -> str:
    d = datetime.fromisoformat(ymd) + timedelta(days=plus_days)
    return datetime(d.year, d.month, d.day, 18, 0, tzinfo=timezone.utc).isoformat()


PILL = """(sel) => { const e = document.querySelector(sel); const s = getComputedStyle(e);
  return { shown: s.display !== 'none' && !!e.offsetParent, text: e.textContent.trim() }; }"""


class LiveLabels(unittest.TestCase):
    def at(self, path: str, moment: str | None, width: int = 1280, lang: str = "en"):
        ctx = new_context(width, 900, lang=lang)
        if moment:
            ctx.clock.set_fixed_time(moment)
        errors: list[str] = []
        page = open_page(ctx, path, errors)
        page.wait_for_timeout(1200)                  # (the countdowns tick every second)
        return ctx, page, errors

    def test_happening_now_on_the_home_cards(self):
        for lang, pre in (("en", ""), ("es", "es/")):
            src = built(pre.rstrip("/") or ".")
            meet = re.search(r'<div class="home-meet home-meet--hero"[^>]*data-start="([^"]+)" data-end="([^"]+)"', src)
            gvm = re.search(r'<div class="home-gvm home-gvm--hero"[^>]*data-start="([^"]+)" data-end="([^"]+)"', src)
            self.assertTrue(meet)
            live = T["home.meeting_live"][lang]
            cases = [(None, ".home-meet--hero .home-live-pill", False), (iso(meet.group(1), minutes=10), ".home-meet--hero .home-live-pill", True)]
            if gvm:
                cases += [(iso(gvm.group(1), minutes=10), ".home-gvm--hero .home-live-pill", True)]
            for moment, sel, on in cases:
                with self.subTest(lang=lang, at=moment, card=sel):
                    ctx, page, errors = self.at(pre, moment, lang=lang)
                    try:
                        st = page.evaluate(PILL, sel)
                        self.assertEqual(st, {"shown": on, "text": live if on else ""})
                        if on and sel.startswith(".home-gvm"):
                            # "First meeting" gives way to "Happening now" during the meeting
                            first = page.evaluate("() => document.querySelector('.home-gvm--hero .home-gvm-pill').textContent.trim()")
                            self.assertEqual(first, "")
                        self.assertEqual(errors, [])
                    finally:
                        ctx.close()

    def test_live_now_and_starting_soon_on_meetings(self):
        for lang, pre in (("en", ""), ("es", "es/")):
            src = built(pre + "meetings")
            cfg = json.loads(html.unescape(re.search(r'<div class="cm-board" x-data="cmMeeting\(([^"]+)\)"', src).group(1)))
            for moment, label in ((None, "committee.meeting.next"), (iso(cfg["start"], minutes=-3), "committee.meeting.starting_soon"),
                                  (iso(cfg["start"], minutes=5), "committee.meeting.live_now")):
                with self.subTest(lang=lang, at=moment):
                    ctx, page, errors = self.at(pre + "meetings/", moment, lang=lang)
                    try:
                        shown = page.evaluate("""() => [...document.querySelectorAll('#next-meeting-h > span')]
                            .filter((s) => getComputedStyle(s).display !== 'none' && s.textContent.trim()).map((s) => s.textContent.trim())""")
                        self.assertEqual(shown, [T[label][lang]])
                        self.assertEqual(errors, [])
                    finally:
                        ctx.close()

    def test_meets_today(self):
        # Saturday, November 21, 2026 (noon in Texas): the groups that meet on Saturdays (data-days "6")
        ctx, page, errors = self.at("meetings/", "2026-11-21T18:00:00+00:00")
        try:
            r = page.evaluate("""() => [...document.querySelectorAll('li[data-gvg]')].map((c) => {
                const b = c.querySelector('[data-gvm-today]');
                return { sat: c.getAttribute('data-days').split(' ').includes('6'), shown: !b.hidden, text: b.textContent.trim() }; })""")
            self.assertTrue(any(x["sat"] for x in r), "a group meets on Saturdays")
            for x in r:
                self.assertEqual(x["shown"], x["sat"], x)
                if x["shown"]:
                    self.assertEqual(x["text"], T["committee.gvm.meets_today"]["en"])
            self.assertEqual(errors, [])
        finally:
            ctx.close()


class EmptyStates(unittest.TestCase):
    def test_the_bulletin_when_its_last_post_has_gone(self):
        for lang, pre in (("en", ""), ("es", "es/")):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                errors: list[str] = []
                try:
                    page = open_page(ctx, pre + "bulletin/", errors)
                    posts = page.locator("[data-gv-expire-item]").count()
                    if not posts:
                        self.skipTest("no post on the bulletin today: its empty card is there from the build")
                    self.assertEqual(page.evaluate("document.getElementById('ann-empty-h').textContent"), "")
                    # every post's day is over (as when the last one expires between two builds)
                    page.evaluate("""() => { document.querySelectorAll('[data-gv-expire-item]').forEach((li) => li.setAttribute('data-gv-expire', '2020-01-01T06:00:00.000Z'));
                                             document.activeElement && document.activeElement.blur(); GV.expire(); }""")
                    st = page.evaluate("""() => { const e = document.getElementById('ann-empty');
                        return { shown: !e.hidden && !!e.offsetParent, h: document.getElementById('ann-empty-h').textContent, p: e.querySelector('p').textContent }; }""")
                    self.assertEqual(st, {"shown": True, "h": T["committee.ann.empty_title"][lang], "p": T["committee.ann.empty_text"][lang]})
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()

    def test_meetings_when_nothing_matches(self):
        ctx = new_context(1280, 900)
        errors: list[str] = []
        try:
            page = open_page(ctx, "meetings/", errors)
            box = """() => { const e = document.querySelector("section[x-data='cmGvMeetings()'] .empty-state.mt-8");
                return { shown: getComputedStyle(e).display !== 'none', text: e.querySelector('p').textContent.trim() }; }"""
            self.assertEqual(page.evaluate(box), {"shown": False, "text": ""})
            page.fill("#gvm-q-en", "zzqqxx nowhere")
            page.wait_for_timeout(600)
            self.assertEqual(page.evaluate(box), {"shown": True, "text": T["committee.gvm.none"]["en"]})
            page.fill("#gvm-q-en", "")
            page.wait_for_timeout(600)
            self.assertEqual(page.evaluate(box), {"shown": False, "text": ""})
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_published_when_nothing_matches(self):
        for lang, pre in (("en", ""), ("es", "es/")):
            with self.subTest(lang=lang):
                ctx = new_context(1280, 900, lang=lang)
                errors: list[str] = []
                try:
                    page = open_page(ctx, pre + "published/", errors)
                    page.wait_for_selector("#pw-q:not([disabled])", timeout=10_000)
                    self.assertEqual(page.evaluate("document.querySelector('#pw-empty .pw-empty-text').textContent"), "")
                    page.fill("#pw-q", "zzqqxx")
                    page.press("#pw-q", "Enter")
                    page.wait_for_timeout(800)
                    st = page.evaluate("""() => { const e = document.getElementById('pw-empty'), a = document.getElementById('pw-arc-empty');
                        return { shown: !e.hidden, title: document.getElementById('pw-empty-title').textContent.trim(), text: e.querySelector('.pw-empty-text').textContent,
                                 arc: a ? { shown: !a.hidden, title: a.querySelector('.pw-empty-title').textContent } : null }; }""")
                    self.assertTrue(st["shown"])
                    self.assertTrue(st["title"])
                    self.assertEqual(st["text"], T["published.empty.text"][lang])
                    if st["arc"]:
                        self.assertEqual(st["arc"], {"shown": True, "title": T["published.archive.empty_title"][lang]})
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()

    def test_home_published_writers_once_the_stories_have_gone(self):
        src = built(".")
        days = int(re.search(r'data-home-spot(?:="")? data-days="(\d+)"', src).group(1))      # ("=''": a /aagrapevine/ build)
        a65 = sorted(re.findall(r'data-pub="(\d{4}-\d{2}-\d{2})" data-scope="neta65"', src))
        tx = sorted(re.findall(r'data-pub="(\d{4}-\d{2}-\d{2})" data-scope="texas"', src))
        if not (a65 or tx):
            self.skipTest("no story in the window today: the empty note is there from the build")
        cases = [(central_noon(max(a65 + tx), days + 1), "empty")]
        if a65 and tx and max(tx) > max(a65):
            cases.append((central_noon(max(a65), days + 1), "none"))
        for moment, which in cases:
            with self.subTest(at=moment, note=which):
                ctx = new_context(1280, 900)
                ctx.clock.set_fixed_time(moment)
                errors: list[str] = []
                try:
                    page = open_page(ctx, "", errors)
                    st = page.evaluate("""() => Object.fromEntries(['data-spot-empty', 'data-spot-none-a65'].map((a) => { const e = document.querySelector('[' + a + ']');
                        return [a, { shown: !e.hidden, h: e.querySelector('h3').textContent }]; }))""")
                    title = re.compile(re.escape(T["home.spot_empty_title" if which == "empty" else "home.spot_none_a65_title"]["en"]).replace(r"\{days\}", r"\d+"))
                    on = st["data-spot-empty" if which == "empty" else "data-spot-none-a65"]
                    off = st["data-spot-none-a65" if which == "empty" else "data-spot-empty"]
                    self.assertTrue(on["shown"])
                    self.assertRegex(on["h"], title)
                    self.assertEqual(off, {"shown": False, "h": ""}, "the other note stays hidden and wordless")
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()

    def test_the_daily_quotes_today_and_yesterday(self):
        src = built(".")
        days = re.findall(r'data-quote-day="(\d{4}-\d{2}-\d{2})"', src)
        if not days:
            self.skipTest("no daily quote in this build")
        for plus, key in ((0, "home.quote_today"), (1, "home.quote_yesterday")):
            with self.subTest(key=key):
                ctx = new_context(1280, 900)
                ctx.clock.set_fixed_time(central_noon(days[0], plus))
                errors: list[str] = []
                try:
                    page = open_page(ctx, "", errors)
                    st = page.evaluate("""() => { const q = document.querySelector('[data-quote-day]');
                        const vis = (s) => { const e = q.querySelector(s); return e.hidden ? null : e.textContent; };
                        return { today: vis('[data-quote-today]'), yesterday: vis('[data-quote-yesterday]') }; }""")
                    want = T[key]["en"]
                    self.assertEqual(st, {"today": want, "yesterday": None} if plus == 0 else {"today": None, "yesterday": want})
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()


STATE = """() => ({ overflow: document.documentElement.style.overflow,
  inert: [...document.body.children].filter((e) => e.inert).map((e) => e.id || e.tagName.toLowerCase()),
  drawerInert: !!document.getElementById('mobile-drawer') && !!document.getElementById('mobile-drawer').closest('[inert]'),
  open: !!document.getElementById('mobile-drawer') && getComputedStyle(document.getElementById('mobile-drawer')).display !== 'none',
  focus: document.activeElement ? (document.activeElement.getAttribute('aria-label') || document.activeElement.className) : '' })"""


class Menu(unittest.TestCase):
    def test_open_lock_close_unlock(self):
        for path in ("", "photos/"):
            with self.subTest(path=path):
                ctx = new_context(390, 844)
                errors: list[str] = []
                try:
                    page = open_page(ctx, path, errors)
                    page.click(".site-header .site-menu-btn")
                    page.wait_for_selector("#mobile-drawer", state="visible", timeout=5000)
                    page.wait_for_timeout(150)                       # (a frame and a task later)
                    st = page.evaluate(STATE)
                    self.assertTrue(st["open"])
                    self.assertEqual(st["overflow"], "hidden")
                    self.assertTrue(page.evaluate("!!document.querySelector('main').closest('[inert]')"), "the page behind is inert")
                    self.assertFalse(st["drawerInert"], "the drawer itself never is")
                    self.assertEqual(st["focus"], "Close")
                    page.keyboard.press("Escape")
                    page.wait_for_selector("#mobile-drawer", state="hidden", timeout=5000)
                    st = page.evaluate(STATE)
                    self.assertEqual((st["overflow"], st["inert"]), ("", []))
                    self.assertTrue(page.evaluate("document.activeElement.classList.contains('site-menu-btn')"), "focus is back on Menu")
                    self.assertEqual(errors, [])
                finally:
                    ctx.close()

    def test_a_quick_close_never_leaves_the_page_locked(self):
        ctx = new_context(390, 844)
        errors: list[str] = []
        try:
            page = open_page(ctx, "", errors)
            # open, then close in the next microtask — before the frame that would lock the page
            page.evaluate("""async () => { const h = Alpine.$data(document.querySelector('.site-menu-btn'));
                h.drawer = true; await Promise.resolve(); await Promise.resolve(); h.drawer = false; }""")
            page.wait_for_timeout(300)
            st = page.evaluate(STATE)
            self.assertEqual((st["overflow"], st["inert"], st["open"]), ("", [], False))
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_the_drawers_reading_settings_button(self):
        ctx = new_context(390, 844)
        errors: list[str] = []
        try:
            page = open_page(ctx, "", errors)
            page.click(".site-header .site-menu-btn")
            page.wait_for_selector("#mobile-drawer", state="visible", timeout=5000)
            page.wait_for_timeout(150)
            page.click("#mobile-drawer button[aria-controls='gvlv-panel']")
            page.wait_for_selector("#mobile-drawer", state="hidden", timeout=5000)
            page.wait_for_timeout(300)
            self.assertTrue(page.evaluate("Alpine.store('gvlv').open"), "the reading settings opened")
            self.assertFalse(page.evaluate("!!document.getElementById('gvlv-panel').closest('[inert]')"), "and can be used")
            self.assertEqual(errors, [])
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
