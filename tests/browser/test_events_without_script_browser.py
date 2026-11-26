"""Round 35 · /events/ for readers that run no script, on the built site in a real browser (tests/browser/__init__.py says
how to run these; they share test_site_in_browser.py's site server and browser). The markup on its own:
tests/test_events_without_script.py.

  * Menus — a card's "Add to calendar" menu: the page carries brief Google / Outlook links (title, times, place: no
            description); once the menu opens they are the full ones — Google's details and Outlook's body are the
            card's description (its .ics data, data-cm-ics), every other field as the brief link had it — and its note
            says its words (the agenda's one copy: data-cm-note-timed / -day), on the screen. The first, a middle and
            the last card shown, English and Spanish, at 1280px and on a phone; no script error.
  * Live  — the labels whose words wait in data-label (Alpine writes them): during the next committee meeting the
            pinned card says "Live now", during the next Grapevine Meeting its card does (the clock set to ten minutes
            into each); before them, the Grapevine Meeting's card says the true one of "First meeting:" / "Next
            meeting:" — one label on the screen, never an empty one.
"""
from __future__ import annotations

import html
import json
import re
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlparse
from zoneinfo import ZoneInfo

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

I18N = json.loads((Path(__file__).resolve().parents[2] / "src" / "_i18n" / "committee.json").read_text(encoding="utf-8"))


def t(key: str, lang: str) -> str:
    return I18N[key][lang]


def params(href: str) -> list[tuple[str, str]]:
    return parse_qsl(urlparse(href).query, keep_blank_values=True)


MENU = """(i) => { const d = [...document.querySelectorAll('li[data-group] .cm-event .cm-menu')][i];
  const a = (h) => d.querySelector('a[href^="' + h + '"]');
  return { gcal: a('https://calendar.google.com/').getAttribute('href'), outlook: a('https://outlook.live.com/').getAttribute('href'),
           ics: JSON.parse(d.querySelector('[data-cm-ics]').getAttribute('data-cm-ics')),
           note: d.querySelector('.cm-menu-note').textContent, kind: d.querySelector('.cm-menu-note').dataset.cmNote,
           noteShown: d.querySelector('.cm-menu-note').getClientRects().length > 0, open: d.open,
           words: { timed: d.closest('[data-cm-note-timed]').dataset.cmNoteTimed, day: d.closest('[data-cm-note-day]').dataset.cmNoteDay } }; }"""


class Menus(unittest.TestCase):
    def test_an_opened_menu_has_the_full_links_and_its_note(self):
        for width, height, touch in ((1280, 800, False), (390, 844, True)):
            for lang in ("en", "es"):
                with self.subTest(width=width, lang=lang):
                    kw = dict(viewport={"width": width, "height": height}, reduced_motion="reduce", service_workers="block",
                              timezone_id="America/Chicago", locale="es-US" if lang == "es" else "en-US")
                    if touch:
                        kw.update(is_mobile=True, has_touch=True, device_scale_factor=3)
                    ctx = S["browser"].new_context(**kw)
                    errors: list[str] = []
                    try:
                        page = open_page(ctx, ("es/" if lang == "es" else "") + "events/", errors)
                        shown = page.evaluate("[...document.querySelectorAll('li[data-group] .cm-event .cm-menu')]"
                                              ".map((d, i) => d.getClientRects().length ? i : -1).filter((i) => i >= 0)")
                        self.assertGreater(len(shown), 10)
                        for i in (shown[0], shown[len(shown) // 2], shown[-1]):
                            before = page.evaluate(MENU, i)
                            self.assertFalse(before["open"])
                            for k, field in (("gcal", "details"), ("outlook", "body")):
                                self.assertNotIn(field, dict(params(before[k])), f"menu {i}: the page's link is brief")
                            self.assertEqual(before["note"], "", "no words in the page")
                            s = page.locator("li[data-group] .cm-event .cm-menu > summary").nth(i)
                            s.scroll_into_view_if_needed()
                            s.tap() if touch else s.click()
                            page.wait_for_timeout(200)
                            after = page.evaluate(MENU, i)
                            self.assertTrue(after["open"])
                            desc = after["ics"]["description"]
                            self.assertTrue(desc)
                            for k, field in (("gcal", "details"), ("outlook", "body")):
                                full = params(after[k])
                                self.assertEqual(dict(full)[field], desc, f"menu {i}: {k} carries the card's description")
                                self.assertEqual([kv for kv in full if kv[0] != field], params(before[k]),
                                                 f"menu {i}: {k}'s other fields as the brief link had them")
                            g = dict(params(after["gcal"]))
                            self.assertEqual((g["text"], g["location"]), (after["ics"]["title"], after["ics"]["location"]))
                            self.assertEqual(after["kind"], "day" if after["ics"]["allDay"] else "timed")
                            self.assertEqual(after["note"], after["words"][after["kind"]])
                            self.assertEqual(after["note"], t("committee.cal.reminder_" + after["kind"], lang))
                            self.assertTrue(after["noteShown"], "the note is on the screen")
                            page.keyboard.press("Escape")
                            page.evaluate("(i) => { [...document.querySelectorAll('li[data-group] .cm-event .cm-menu')][i].open = false; }", i)
                        self.assertEqual(errors, [])
                    finally:
                        ctx.close()


def x_cfg(page_html: str, needle: str) -> dict:
    """The JSON of the x-data="cmMeeting({…})" of the tag that holds `needle`."""
    i = page_html.index(needle)
    tag = page_html[page_html.rindex("<", 0, i):page_html.index(">", i) + 1]
    return json.loads(html.unescape(re.search(r'x-data="cmMeeting\((.*?)\)"', tag).group(1)))


LABELS = """(sel) => [...document.querySelectorAll(sel + ' [data-label]')].filter((e) => e.getClientRects().length)
  .map((e) => e.textContent.trim())"""


class Live(unittest.TestCase):
    def built(self, lang: str) -> str:
        return (S["site"] / ("es/" if lang == "es" else "") / "events" / "index.html").read_text(encoding="utf-8")

    def at(self, lang: str, moment: datetime | None) -> dict:
        ctx = new_context(1280, 900, lang=lang)
        errors: list[str] = []
        try:
            if moment:
                ctx.clock.set_fixed_time(moment)
            page = open_page(ctx, ("es/" if lang == "es" else "") + "events/", errors)
            page.wait_for_timeout(1500)
            got = {"pinned": page.evaluate(LABELS, "#ev-pinned .cm-pinned"), "gvm": page.evaluate(LABELS, "#ev-next-gvm")}
            self.assertEqual(errors, [])
            return got
        finally:
            ctx.close()

    def test_live_now_shows_during_a_meeting(self):
        for lang in ("en", "es"):
            page = self.built(lang)
            live = t("committee.meeting.live_now", lang)
            with self.subTest(lang=lang, card="committee meeting"):
                if '<article class="cm-pinned' not in page:
                    self.skipTest("no committee meeting to come in this build")
                cfg = x_cfg(page, '<article class="cm-pinned')
                got = self.at(lang, datetime.fromisoformat(cfg["start"].replace("Z", "+00:00")) + timedelta(minutes=10))
                self.assertEqual(got["pinned"], [live])
            with self.subTest(lang=lang, card="Grapevine Meeting"):
                if 'id="ev-next-gvm"' not in page:
                    self.skipTest("no Grapevine Meeting to come in this build")
                cfg = x_cfg(page, 'id="ev-next-gvm"')
                got = self.at(lang, datetime.fromisoformat(cfg["start"].replace("Z", "+00:00")) + timedelta(minutes=10))
                self.assertEqual(got["gvm"], [live])

    def test_before_a_meeting_the_true_label(self):
        for lang in ("en", "es"):
            page = self.built(lang)
            with self.subTest(lang=lang):
                if 'id="ev-next-gvm"' not in page:
                    self.skipTest("no Grapevine Meeting to come in this build")
                cfg = x_cfg(page, 'id="ev-next-gvm"')
                start = datetime.fromisoformat(cfg["start"].replace("Z", "+00:00"))
                got = self.at(lang, start - timedelta(days=2))
                first = cfg.get("first") == start.astimezone(ZoneInfo("America/Chicago")).date().isoformat()
                want = t("committee.events.first_meeting" if first else "committee.weekly.next", lang)
                self.assertEqual(got["gvm"], [want])
                self.assertEqual(got["pinned"], [], "the committee meeting's card: no live label before it")


if __name__ == "__main__":
    unittest.main()
