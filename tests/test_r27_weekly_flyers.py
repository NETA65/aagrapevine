"""Round 27 — the weekly open meetings' flyers, seen like every other event's (November 12, 2026: "i do not see the open
meeting flyers on the site"):

  * the helpers   — committee.js flyerLinks (a flyer's link, its preview for the site's viewer and the tile's picture:
                    the Drive's 320px copy) — the one rule for every card with a flyer tile, the events' ev.flyer too —
                    and weeklyFlyer (a weekly open meeting's newest flyer in the Drive's flyers/ folder, found by its
                    settings' flyer_match; nothing without a pattern or a match);
  * /events/      — each "every week" card (#ev-weekly), English and Spanish, shows its flyer as every event card does:
                    the side tile (a.cm-flyer-thumb, ui.flyerThumb: its picture, the preview, "View flyer: <title>")
                    and a View flyer button after Join on Zoom, Meeting details and Add to calendar; Join stays first;
  * /meetings/    — each card of #weekly-open shows the tile too (beside the day and time, in the meeting's colour,
                    from 640px) and keeps its View flyer by the source line (on a phone the way to it), both opening
                    the flyer in the site's viewer: the page has the viewer ({% cmPreviewDialog %}) once;
  * no flyer      — a card whose pattern finds no flyer shows neither, and keeps no empty column.

The pages are built by Eleventy with the site's own config on a fixed clock, with weekly open meetings and Drive files
of the test's own (the two flyers under their real Drive ids; not the day's data).

    python -m unittest tests.test_r27_weekly_flyers -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from test_r26c_weekly_link import (GV_FLYER, GV_MATCH, LV_FLYER, LV_MATCH, LV_NOVEMBER, NOW, PAGES_JS, T,  # noqa: E402
                                   cards, drive_item, visible, weekly_item)

GV_ID = "1lKJZfFvqs-H_6LjCIqww4jAacEw3NFbF"      # "Grapevine Weekly Open AA Meeting - every Wednesday, …" (flyers/)
LV_ID = "1-bjRcwoLE43Eb_uB1GfDbCTWVaptIvEq"      # "Reunión abierta de La Viña - todos los jueves, …" (flyers/)
LV_OLD_ID = "1oldLaVinaNovemberFlyer0000000"     # La Viña's older edition (an older date): never shown
SLIDES_ID = "1slidesNamedLikeTheGvFlyer0000"     # newer, named like the Grapevine flyer, but in slides/

DRIVE = [
    drive_item(GV_ID, GV_FLYER, "2026-11-12", es="Reunión abierta semanal de Grapevine (en inglés) - todos los miércoles"),
    drive_item(LV_ID, LV_FLYER, "2026-11-12", en="La Viña Open Meeting (in Spanish) - Every Thursday"),
    drive_item(LV_OLD_ID, LV_NOVEMBER, "2026-09-25", en="New La Viña Open Meeting - Thursdays at 12 PM Eastern on Zoom"),
    drive_item(SLIDES_ID, "Grapevine Weekly Open AA Meeting - slides", "2026-11-13", category="slides"),
]
NO_GV_FLYER = [d for d in DRIVE if d["id"] != f"drive:{GV_ID}"]
FLYER_OF = {"gv": GV_ID, "lv": LV_ID}
VIEW = "https://drive.google.com/file/d/{}/view"
PREVIEW = "https://drive.google.com/file/d/{}/preview"
THUMB = "https://lh3.googleusercontent.com/d/{}=w320"
LANGS = (("en", "/"), ("es", "/es/"))

BUILT: dict[str, dict] = {}


def built(case: unittest.TestCase, drive: str = "all") -> dict:
    """/meetings/ and /events/ in both languages, with the test's weekly open meetings and Drive files."""
    if drive not in BUILT:
        urls = [pre + p for p in ("meetings/", "events/") for pre in ("/", "/es/")]
        BUILT[drive] = run_js(case, PAGES_JS, data={"only": "meetings,events.njk", "urls": urls,
                                                    "weekly": [weekly_item(False), weekly_item(True)],
                                                    "drive": DRIVE if drive == "all" else NO_GV_FLYER,
                                                    "gv_match": GV_MATCH, "lv_match": LV_MATCH},
                              timeout=600, now=NOW)
    return BUILT[drive]


TILE = re.compile(r'<a class="cm-flyer-thumb([^"]*)" href="([^"]+)"([^>]*)>([\s\S]*?)</a>')


def tiles(fragment: str) -> list[dict]:
    """The flyer tiles in a piece of a page: {cls (the classes after cm-flyer-thumb), href, attrs, body}."""
    return [{"cls": m.group(1).strip(), "href": html.unescape(m.group(2)), "attrs": m.group(3), "body": m.group(4)}
            for m in TILE.finditer(fragment)]


def attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    return html.unescape(m.group(1)) if m else None


def flyer_buttons(fragment: str, lang: str, cls: str) -> list[dict]:
    """The "View flyer" buttons (class `cls`) in a piece of a page: {href, attrs}."""
    word = re.escape(T["committee.events.view_flyer"][lang])
    return [{"href": html.unescape(m.group(1)), "attrs": m.group(2)}
            for m in re.finditer(rf'<a class="{cls}" href="([^"]+)"([^>]*)>(?:(?!</a>)[\s\S])*?{word}</a>', fragment)]


def weekly_events_cards(page: str) -> dict[str, str]:
    """/events/' "every week" cards: {"gv" | "lv": the card's HTML}."""
    i = page.index('<section id="ev-weekly"')
    block = page[i:page.index("</section>", i)]
    return {m.group(1): m.group(0) for m in re.finditer(r'<article class="card ev-accent ev-tone-(gv|lv)[^"]*".*?</article>', block, re.S)}


def title_of(card: str) -> str:
    return visible(re.search(r"<h3[^>]*>(.*?)</h3>", card, re.S).group(1))


# ---------------------------------------------------------------------------------------------- the helpers
HELPERS_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const site = { grapevine_weekly_open: { flyer_match: input.gv }, lavina_weekly_open: { flyer_match: input.lv } };
const gv = { isLv: false }, lv = { isLv: true };
out({
  drive: C.flyerLinks(input.view),
  ownPicture: C.flyerLinks(input.view, "https://example.org/flyer.jpg"),
  openId: C.flyerLinks(input.open),
  neta: C.flyerLinks("https://neta65.org/wp-content/uploads/2026/09/flyer.jpeg"),
  none: [C.flyerLinks(""), C.flyerLinks(null), C.flyerLinks(undefined)],
  gv: C.weeklyFlyer(gv, site, input.drive), lv: C.weeklyFlyer(lv, site, input.drive),
  gvMissing: C.weeklyFlyer(gv, site, input.noGv),
  gone: C.weeklyFlyer(gv, site, input.drive.map((d) => ({ ...d, status: d.id === input.gvItem ? "gone" : d.status }))),
  noPattern: [C.weeklyFlyer(gv, {}, input.drive), C.weeklyFlyer(lv, { lavina_weekly_open: {} }, input.drive),
              C.weeklyFlyer(gv, null, input.drive), C.weeklyFlyer(null, site, input.drive)],
  noItems: [C.weeklyFlyer(gv, site, []), C.weeklyFlyer(gv, site, null)],
  filter: filters.cmWeeklyFlyer(lv, site, input.drive),
});
"""


class Helpers(unittest.TestCase):
    _r: dict | None = None

    @property
    def r(self) -> dict:
        if Helpers._r is None:
            Helpers._r = run_js(self, HELPERS_JS, data={"view": VIEW.format(GV_ID), "open": f"https://drive.google.com/open?id={LV_ID}",
                                                        "gv": GV_MATCH, "lv": LV_MATCH, "drive": DRIVE, "noGv": NO_GV_FLYER,
                                                        "gvItem": f"drive:{GV_ID}"})
        return Helpers._r

    def test_a_flyers_link_preview_and_picture(self):
        r = self.r
        self.assertEqual(r["drive"], {"view": VIEW.format(GV_ID), "preview": PREVIEW.format(GV_ID), "thumb": THUMB.format(GV_ID)})
        self.assertEqual(r["ownPicture"]["thumb"], "https://example.org/flyer.jpg", "the data's own picture wins")
        self.assertEqual(r["openId"]["preview"], PREVIEW.format(LV_ID))
        self.assertEqual(r["openId"]["thumb"], THUMB.format(LV_ID))
        # a flyer only its own site can show: no picture (the tile's own icon), the link itself as the preview
        self.assertIsNone(r["neta"]["thumb"])
        self.assertEqual(r["neta"]["preview"], r["neta"]["view"])
        self.assertEqual(r["none"], [None, None, None])

    def test_each_meeting_finds_its_own_newest_flyer(self):
        r = self.r
        self.assertEqual(r["gv"], {"view": VIEW.format(GV_ID), "preview": PREVIEW.format(GV_ID), "thumb": THUMB.format(GV_ID)})
        self.assertEqual(r["lv"], {"view": VIEW.format(LV_ID), "preview": PREVIEW.format(LV_ID), "thumb": THUMB.format(LV_ID)})
        self.assertEqual(r["filter"], r["lv"], "the templates' filter is the same rule")

    def test_nothing_without_a_flyer(self):
        r = self.r
        self.assertIsNone(r["gvMissing"], "the newer slides file named like it is not a flyer")
        self.assertIsNone(r["gone"], "a file gone from the Drive")
        self.assertEqual(r["noPattern"], [None, None, None, None])
        self.assertEqual(r["noItems"], [None, None])


# ---------------------------------------------------------------------------------------------- /events/
class EventsPage(unittest.TestCase):
    def test_each_every_week_card_shows_its_flyer_like_every_event(self):
        p = built(self)
        for lang, pre in LANGS:
            found = weekly_events_cards(p[pre + "events/"])
            self.assertEqual(sorted(found), ["gv", "lv"])
            for key, card in found.items():
                fid, title = FLYER_OF[key], title_of(card)
                with self.subTest(lang=lang, card=key):
                    # the tile: the same markup as an event card's (ui.flyerThumb), after the card's text
                    (tile,) = tiles(card)
                    self.assertEqual((tile["cls"], tile["href"]), ("", VIEW.format(fid)))
                    self.assertEqual(attr(tile["attrs"], "data-cm-preview"), PREVIEW.format(fid))
                    self.assertEqual(attr(tile["attrs"], "data-cm-open"), VIEW.format(fid))
                    self.assertEqual(attr(tile["attrs"], "data-cm-title"), title)
                    self.assertEqual(attr(tile["attrs"], "aria-label"),
                                     T["committee.events.view_flyer_of"][lang].replace("{title}", title))
                    self.assertIn(f'<img src="{THUMB.format(fid)}" alt=""', tile["body"])
                    self.assertIn(f'<span class="cm-flyer-word">{T["committee.events.flyer"][lang]}</span>', tile["body"])
                    self.assertIn('class="card ev-accent ev-tone-' + key + ' cm-event"', card, "tile | text, like an event card")
                    self.assertLess(card.index('<div class="min-w-0 flex-1">'), card.index('class="cm-flyer-thumb'))
                    # View flyer: the same flyer and preview, after Join on Zoom (still the first, the primary button)
                    (btn,) = flyer_buttons(card, lang, r"btn-secondary btn-sm(?: col-span-full)?")
                    self.assertEqual(btn["href"], VIEW.format(fid))
                    self.assertEqual(attr(btn["attrs"], "data-cm-preview"), PREVIEW.format(fid))
                    buttons = re.findall(r'<(?:a|summary) class="(btn-[\w-]+)', card)
                    self.assertEqual(buttons[0], "btn-primary")
                    self.assertEqual(buttons.count("btn-primary"), 1)
                    # (with Add to calendar there, View flyer is the odd one on a phone: a row of its own)
                    self.assertIn('<a class="btn-secondary btn-sm col-span-full" href="' + VIEW.format(fid), card)

    def test_the_page_has_one_viewer(self):
        p = built(self)
        for lang, pre in LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(p[pre + "events/"].count('<dialog id="cm-preview"'), 1)

    def test_no_flyer_no_tile_and_no_button(self):
        p = built(self, drive="no-gv")
        for lang, pre in LANGS:
            found = weekly_events_cards(p[pre + "events/"])
            with self.subTest(lang=lang):
                self.assertNotIn("cm-flyer-thumb", found["gv"])
                self.assertEqual(flyer_buttons(found["gv"], lang, r"btn-[\w -]+"), [])
                self.assertNotIn(SLIDES_ID, found["gv"])
                self.assertEqual([t["href"] for t in tiles(found["lv"])], [VIEW.format(LV_ID)])


# ---------------------------------------------------------------------------------------------- /meetings/
class MeetingsPage(unittest.TestCase):
    def test_each_card_shows_its_flyer_beside_the_day_and_time(self):
        p = built(self)
        for lang, pre in LANGS:
            found = cards(p[pre + "meetings/"])
            self.assertEqual(sorted(found), ["gv", "lv"])
            for key, card in found.items():
                fid, title = FLYER_OF[key], title_of(card)
                with self.subTest(lang=lang, card=key):
                    (tile,) = tiles(card)
                    self.assertEqual(tile["href"], VIEW.format(fid))
                    # in the meeting's colour; a column of its own from 640px, beside the day and time (row 3)
                    self.assertEqual(tile["cls"].split(), [f"ev-tone-{key}", "sm:col-start-2", "sm:row-start-3", "sm:mt-5", "sm:ml-5"])
                    self.assertEqual(attr(tile["attrs"], "data-cm-preview"), PREVIEW.format(fid))
                    self.assertEqual(attr(tile["attrs"], "aria-label"),
                                     T["committee.events.view_flyer_of"][lang].replace("{title}", title))
                    self.assertIn(f'<img src="{THUMB.format(fid)}" alt=""', tile["body"])
                    # the card's coloured top part holds it; the title and the text keep the whole width
                    top = card[:card.index('<div class="@container')]
                    self.assertIn("cm-flyer-thumb", top)
                    self.assertIn("sm:grid sm:grid-cols-[minmax(0,1fr)_auto] sm:grid-rows-[auto_auto_1fr]", top)
                    self.assertEqual(top.count("sm:col-span-2"), 2)
                    # View flyer by the source line: the same flyer, in the site's viewer
                    (btn,) = flyer_buttons(card, lang, "btn-ghost btn-sm")
                    self.assertEqual(btn["href"], VIEW.format(fid))
                    self.assertEqual(attr(btn["attrs"], "data-cm-preview"), PREVIEW.format(fid))
                    self.assertEqual(attr(btn["attrs"], "data-cm-title"), title)
                    # Join on Zoom stays the first button of the card
                    self.assertEqual(re.findall(r'<(?:a|summary) class="(btn-[\w-]+)', card)[0], "btn-primary")

    def test_the_page_has_the_viewer_once(self):
        p = built(self)
        for lang, pre in LANGS:
            with self.subTest(lang=lang):
                page = p[pre + "meetings/"]
                self.assertEqual(page.count('<dialog id="cm-preview"'), 1)
                self.assertEqual(page.count('id="cm-preview-title"'), 1)

    def test_no_flyer_no_tile_and_no_empty_column(self):
        p = built(self, drive="no-gv")
        for lang, pre in LANGS:
            found = cards(p[pre + "meetings/"])
            with self.subTest(lang=lang):
                gv = found["gv"]
                self.assertNotIn("cm-flyer-thumb", gv)
                self.assertNotIn("sm:grid-cols-[minmax(0,1fr)_auto]", gv)
                self.assertNotIn("sm:col-span-2", gv)
                self.assertEqual(flyer_buttons(gv, lang, r"btn-[\w -]+"), [])
                self.assertIn(T["committee.weekly.source_gv"][lang], visible(gv))
                self.assertEqual([t["href"] for t in tiles(found["lv"])], [VIEW.format(LV_ID)])


if __name__ == "__main__":
    unittest.main()
