"""Round 21, Unit A — the weekly open meetings (AA Grapevine's Weekly Open, La Viña's Reunión Abierta) come first on
/meetings/, and /events/ lists them in an "every week" block:

  * Meetings      — the order under the hero: New to AA? · the weekly open meetings (#weekly-open) · the committee
                    meeting (#committee-meeting) · the Grapevine meetings (#grapevine-meetings, the band, last); the
                    spacing that order takes (the weekly section's top padding, the committee section's none); the
                    hero's jump links, with the committee meeting's last in both languages (it is no longer right
                    under the hero); the weekly section's eyebrow ("On Zoom", no "Also" — nothing comes before it);
                    on /es/ the Grapevine meetings' "no Spanish-speaking group" line points UP to La Viña's meeting;
  * Events        — #ev-weekly under the pinned committee meeting and before the months: both meetings, the page
                    language's first, each in its magazine's colour, "Every week", its day and time, its next date
                    with the /meetings/ cards' data-cm-weekly markup (committee.js rolls it on in the browser) —
                    La Viña's "Starts Thursday, November 5, 2026" before that day, its next Thursday after it —, How
                    to join (/meetings/#weekly-open: the one home of the Zoom ID and passcode, never shown here) and
                    Add to calendar (the weekly .ics files of /meetings/, Google's weekly link); shown with "All" and
                    "GV & LV calendars", never counted as an event of the month list;
                    The colour key counts the two cards' colours; a card with no day or time has no clock line;
  * the links     — a link to the committee meeting goes to #committee-meeting (Home's meeting card, the pinned card
                    on /events/, /contribute/'s workshop band, /gvr/'s companion card and its "Pass it on" welcome
                    message — the printed handover sheet keeps the short address), no longer the top of the page;
                    the old /meeting/ address (the committee meeting's page) opens #committee-meeting too.

The pages are built by Eleventy with the site's own config, on a fixed clock, with weekly open meetings of the test's
own (WEEKLY — not data/site/weekly_open.json, whatever the day's data says): a Zoom room whose ID and passcode are
nowhere else on the site, so the test sees where they show.

    python -m unittest tests.test_r21_weekly -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BEFORE = "2026-11-02T18:00:00Z"     # Mon Nov 2, noon Central: La Viña's first meeting (Thu Nov 5) is still ahead
AFTER = "2026-11-10T12:00:00Z"      # Tue Nov 10, 6 AM Central: both meetings meet every week now


def i18n() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


T = i18n()
ZOOM_ID, ZOOM_DIGITS, PASSCODE = "834 5678 9012", "83456789012", "975310"


def weekly_item(lv: bool) -> dict:
    """A weekly_open.json item as scripts/sync/weekly_open.py writes it (GV: read from aagrapevine.org; La Viña: from
    config/site.yml lavina_weekly_open, with its first day, `starts`)."""
    extra = {"zoom_id": ZOOM_ID, "passcode": PASSCODE, "zoom_url": f"https://zoom.us/j/{ZOOM_DIGITS}",
             "start_local": "12:00", "timezone": "America/New_York", "time_central": "11 AM Central"}
    if lv:
        extra.update({"day": "Jueves", "time": "12 p. m. (hora del Este)", "weekday": "thursday",
                      "next_start": "2026-11-05T17:00:00Z", "starts": "2026-11-05"})
        title = {"en": "La Viña Open Meeting (in Spanish)", "es": "Reunión Abierta de La Viña"}
        summary = {"en": "A weekly virtual open AA meeting in Spanish.", "es": "Una reunión abierta virtual de AA en español, cada semana."}
        day = {"en": "Thursdays", "es": "Jueves"}
    else:
        extra.update({"day": "Wednesdays", "time": "Noon Eastern", "weekday": "wednesday",
                      "url": "https://www.aagrapevine.org/grapevine-weekly-open", "next_start": "2026-11-04T17:00:00Z"})
        title = {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"}
        summary = {"en": "Each week AA Grapevine holds an open virtual AA meeting.", "es": "Cada semana AA Grapevine celebra una reunión abierta."}
        day = {"en": "Wednesdays", "es": "Miércoles"}
    return {
        "id": "weekly_open_lv" if lv else "weekly_open", "source": "lavina" if lv else "grapevine", "kind": "meeting",
        "url": "" if lv else "https://www.aagrapevine.org/grapevine-weekly-open", "title": title["es" if lv else "en"],
        "summary": summary["es" if lv else "en"], "lang": "es" if lv else "en", "status": "ok", "extra": extra,
        "i18n": {"title": title, "summary": summary, "day": day,
                 "time": {"en": "Noon Eastern", "es": "mediodía (hora del Este)"},
                 "time_central": {"en": "11:00 AM Central", "es": "11:00 a. m. (hora del Centro)"},
                 "when": {"en": f"{day['en']} at 11:00 AM Central", "es": f"Los {day['es'].lower()} a las 11:00 a. m. (hora del Centro)"}},
    }


WEEKLY = [weekly_item(False), weekly_item(True)]
# Grapevine's item with nothing but its title (the page it is read from changed): the card stays, without a clock line
BARE = [{**weekly_item(False), "extra": {}, "i18n": {}}, weekly_item(True)]

# Eleventy with the site's config: only these pages (ONLY), the test's weekly open meetings in place of the day's.
PAGES_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r21-weekly-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(cfg) {
      cfg.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, weekly_open: { updated: "2026-11-02T12:00:00Z", items: input.weekly } }),
      });
    },
  });
  const pages = await elev.toJSON();
  const want = new Set(input.urls);
  out(Object.fromEntries(pages.filter((p) => want.has(p.url)).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
BUILT: dict[str, dict] = {}


def built(case: unittest.TestCase, when: str, bare: bool = False) -> dict:
    """The pages built at `when` (BEFORE: Home, Meetings, the old /meeting/ address, Events, Contribute and GVR in
    both languages; AFTER: Events), with WEEKLY — or, `bare`, Events with BARE."""
    key = when + (" bare" if bare else "")
    if key not in BUILT:
        if when == BEFORE and not bare:
            only = "index.njk,meetings.njk,meeting.njk,events.njk,contribute.njk,gvr.njk"
            pages = ["", "meetings/", "meeting/", "events/", "contribute/", "gvr/"]
        else:
            only, pages = "events.njk", ["events/"]
        urls = [pre + p for p in pages for pre in ("/", "/es/")]
        BUILT[key] = run_js(case, PAGES_JS, data={"only": only, "urls": urls, "weekly": BARE if bare else WEEKLY},
                            timeout=600, now=when)
    return BUILT[key]


def page_url(lang: str, path: str) -> str:
    return ("/es/" if lang == "es" else "/") + path


def visible(html: str) -> str:
    """The page's words: no tags, no icons, no attribute values."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", " ", html, flags=re.S))).strip()


def weekly_block(page: str) -> str:
    i = page.index('<section id="ev-weekly"')
    return page[i:page.index("</section>", i) + len("</section>")]


def weekly_cards(block: str) -> list[tuple[str, str]]:
    """(gv | lv, the card's HTML) in page order."""
    return [(m.group(2), m.group(0)) for m in re.finditer(r'<article class="card ev-accent ev-tone-(gv|lv)[^"]*" aria-labelledby="ev-weekly-(gv|lv)">.*?</article>', block, re.S)]


class MeetingsPage(unittest.TestCase):
    def test_the_weekly_open_meetings_come_first_after_new_to_aa(self):
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                page = p[page_url(lang, "meetings/")]
                at = [page.index(s) for s in ("cm-subnav", 'id="new-to-aa"', 'id="weekly-open"', 'id="committee-meeting"',
                                              'id="grapevine-meetings"')]
                self.assertEqual(at, sorted(at), "sub-nav · New to AA? · weekly open · committee meeting · Grapevine meetings")
                for anchor in ('id="weekly-open"', 'id="committee-meeting"', 'id="grapevine-meetings"'):
                    self.assertEqual(page.count(anchor), 1, anchor)
                # the spacing of that order: the weekly section takes the gap under the card the committee's had;
                # the committee section follows a plain section (no gap of its own); the Grapevine band comes last
                self.assertIn('<section class="container-page section pt-10 sm:pt-12" aria-labelledby="weekly-title">', page)
                self.assertIn('<section class="container-page section pt-0" aria-labelledby="committee-meeting-h">', page)
                self.assertNotIn('section pb-0" aria-labelledby="weekly-title"', page)
                self.assertGreater(page.index('<section class="section section-band" aria-labelledby="gvm-title"'),
                                   page.index('aria-labelledby="committee-meeting-h"'))
                # the test's Zoom room is shown here, its one home (so the fixture is what the pages read)
                self.assertIn(ZOOM_ID, page)
                self.assertIn(PASSCODE, page)

    def test_the_heros_jump_links_end_with_the_committee_meeting(self):
        p = built(self, BEFORE)
        want = {"en": ["#grapevine-meetings", "#weekly-open", "#committee-meeting"],
                "es": ["#weekly-open", "#grapevine-meetings", "#committee-meeting"]}
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                nav = re.search(r'<nav class="hero-actions"[^>]*>(.*?)</nav>', p[page_url(lang, "meetings/")], re.S).group(1)
                links = re.findall(r'<a href="([^"]+)" class="([^"]+)">(.*?)</a>', nav, re.S)
                self.assertEqual([a[0] for a in links], want[lang])
                self.assertEqual([a[1] for a in links][1:], ["btn-on-dark", "btn-on-dark"], "one light button, the first")
                self.assertEqual(visible(links[-1][2]), T["nav.meeting"][lang])
                self.assertIn('<use href="#i-users"', links[-1][2])

    def test_the_eyebrow_and_the_line_that_points_up(self):
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertIn(T["committee.weekly.eyebrow"][lang], p[page_url(lang, "meetings/")])
        self.assertEqual(T["committee.weekly.eyebrow"]["en"], "On Zoom · Open to everyone")
        self.assertEqual(T["committee.weekly.eyebrow"]["es"], "Por Zoom · Abiertas a todos")
        # /es/ with no Spanish-speaking group on the lists: La Viña's meeting is ABOVE now (whether the line shows
        # depends on the day's lists: the template says it, and the page when it is there)
        src = (ROOT / "src" / "pages" / "meetings.njk").read_text(encoding="utf-8")
        self.assertIn('href="#weekly-open">{{ "committee.gvm.no_spanish_link" | t(lang) }}<span aria-hidden="true"> ↑</span></a>', src)
        es = p["/es/meetings/"]
        if T["committee.gvm.no_spanish_link"]["es"] in es:
            self.assertIn(T["committee.gvm.no_spanish_link"]["es"] + '<span aria-hidden="true"> ↑</span>', es)


class EventsPage(unittest.TestCase):
    def test_the_block_sits_under_the_pinned_meeting_and_before_the_months(self):
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                page = p[page_url(lang, "events/")]
                self.assertEqual(page.count('id="ev-weekly"'), 1)
                block = weekly_block(page)
                self.assertTrue(block.startswith('<section id="ev-weekly" class="mb-10" x-show="filter === \'all\' || '
                                                 'filter === \'calendar\'" aria-labelledby="ev-weekly-title">'), block[:200])
                self.assertIn(f'<h2 id="ev-weekly-title" class="cm-month-title">{T["committee.weekly.section_title"][lang]}</h2>', block)
                self.assertIn(T["committee.events.weekly_text"][lang].replace("'", "&#39;"), block)
                start = page.index('<section id="ev-weekly"')
                self.assertGreater(start, page.index('id="ev-next-title"'), "under the pinned committee meeting")
                if 'class="cm-month"' in page:
                    self.assertLess(start, page.index('class="cm-month"'), "before the months")
                # not an event of the list: the chips, "Showing N" and the months never count it
                self.assertNotIn("data-group", block)
                self.assertNotIn("data-dflt-hidden", block)
                self.assertNotIn("data-cm-expire", block)

    def test_both_meetings_the_page_languages_first(self):
        p = built(self, BEFORE)
        for lang, order in (("en", ["gv", "lv"]), ("es", ["lv", "gv"])):
            with self.subTest(lang=lang):
                cards = weekly_cards(weekly_block(p[page_url(lang, "events/")]))
                self.assertEqual([k for k, _ in cards], order)
                for key, card in cards:
                    text = visible(card)
                    self.assertIn('<span class="badge ev-badge">', card)
                    self.assertIn(T[f"committee.events.kind.{key}"][lang], text)
                    self.assertIn(T["committee.events.badge_weekly"][lang], text)
                    self.assertIn(T[f"committee.weekly.lang_{'es' if key == 'lv' else 'en'}"][lang], text)
                    self.assertIn(WEEKLY[key == "lv"]["i18n"]["title"][lang], text)
                    self.assertIn(WEEKLY[key == "lv"]["i18n"]["day"][lang], text)
                    self.assertIn(WEEKLY[key == "lv"]["i18n"]["time_central"][lang], text)
                    self.assertIn(T["committee.events.online_on"][lang].replace("{platform}", "Zoom"), text)

    def test_the_next_date_rolls_on_like_the_meetings_page(self):
        p = built(self, BEFORE)
        starts = {"en": "Starts Thursday, November 5, 2026", "es": "Comienza el jueves 5 de noviembre de 2026"}
        nxt = {"en": "Wednesday, November 4", "es": "Miércoles, 4 de noviembre"}
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                cards = dict(weekly_cards(weekly_block(p[page_url(lang, "events/")])))
                for key, card in cards.items():
                    box = re.search(r"<p [^>]*data-cm-weekly=\"([^\"]+)\"[^>]*>", card)
                    self.assertIsNotNone(box, key)
                    tag = box.group(0)
                    for attr in ('data-cm-weekly-tz="America/New_York"', 'data-cm-weekly-at="12:00"', 'data-cm-weekly-len="60"'):
                        self.assertIn(attr, tag)
                    self.assertIn("data-cm-weekly-label", card)
                    self.assertIn("data-cm-weekly-date", card)
                    self.assertIn(f'data-live="{T["committee.meeting.live_now"][lang]}"', card)
                    self.assertIn("data-cm-weekly-local", card)
                # La Viña's first meeting is still ahead: "Starts …" (the browser keeps it until then)
                self.assertIn('data-cm-weekly-starts="2026-11-05T17:00:00.000Z"', cards["lv"])
                self.assertIn(starts[lang], visible(cards["lv"]))
                self.assertNotIn("data-cm-weekly-starts", cards["gv"])
                self.assertIn(T["committee.weekly.next"][lang] + " " + nxt[lang], visible(cards["gv"]))

    def test_after_la_vinas_first_meeting_its_next_thursday(self):
        p = built(self, AFTER)
        for lang, gv, lv in (("en", "Wednesday, November 11", "Thursday, November 12"),
                             ("es", "Miércoles, 11 de noviembre", "Jueves, 12 de noviembre")):
            with self.subTest(lang=lang):
                cards = dict(weekly_cards(weekly_block(p[page_url(lang, "events/")])))
                self.assertNotIn("data-cm-weekly-starts", cards["lv"])
                self.assertNotIn(T["committee.weekly.starts"][lang].replace(" {date}", "").replace("{date}", ""), visible(cards["lv"]))
                self.assertIn(T["committee.weekly.next"][lang] + " " + lv, visible(cards["lv"]))
                self.assertIn(T["committee.weekly.next"][lang] + " " + gv, visible(cards["gv"]))

    def test_how_to_join_and_add_to_calendar(self):
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            pre = "/es" if lang == "es" else ""
            with self.subTest(lang=lang):
                for key, card in weekly_cards(weekly_block(p[page_url(lang, "events/")])):
                    hrefs = re.findall(r'href="([^"]+)"', card)
                    # How to join: the meetings page, where the Zoom ID and passcode are; never the Zoom link itself
                    join = re.search(r'<a class="btn-primary btn-sm" href="([^"]+)">(.*?)</a>', card, re.S)
                    self.assertEqual(join.group(1), f"{pre}/meetings/#weekly-open")
                    self.assertTrue(visible(join.group(2)).startswith(T["media.wo_join"][lang]))
                    self.assertFalse([h for h in hrefs if re.match(r"https?://([\w-]+\.)*zoom\.us/", h)])
                    # Add to calendar: every week — the weekly .ics file of /meetings/ and Google's repeating link
                    self.assertIn(f'<a href="{pre}/meetings/weekly-open-{key}.ics" download="weekly-open-{key}.ics" type="text/calendar">', card)
                    gcal = [h for h in hrefs if h.startswith("https://calendar.google.com/calendar/render?")]
                    self.assertEqual(len(gcal), 1)
                    self.assertIn("recur=RRULE%3AFREQ%3DWEEKLY%3BBYDAY%3D" + ("TH" if key == "lv" else "WE"), gcal[0])
                    self.assertIn('<details class="cm-menu">', card)
                    self.assertIn(f'<p class="cm-menu-note">{T["committee.cal.reminder_timed"][lang]}</p>', card)
                    name = WEEKLY[key == "lv"]["i18n"]["title"][lang]
                    self.assertIn('aria-label="' + T["committee.weekly.cal_aria"][lang].replace("{name}", name) + '"', card)

    def test_the_colour_key_has_the_cards_colours(self):
        # the two cards are in Grapevine's and La Viña's colours: the key names both, whatever the month list holds
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                legend = re.search(r'<ul class="ev-legend-list"[^>]*>(.*?)</ul>', p[page_url(lang, "events/")], re.S)
                self.assertIsNotNone(legend, "the colour key")
                for key in ("gv", "lv"):
                    self.assertIn(f'<li class="ev-tone-{key}"><span class="ev-dot" aria-hidden="true"></span>'
                                  f'{T["committee.events.kind." + key][lang]}</li>', legend.group(1))

    def test_a_card_without_its_day_and_time(self):
        # Grapevine's page read without the day and time: the card keeps its title and How to join, no clock line
        # (no lone "·"), no date and no calendar menu; La Viña's card is as before
        p = built(self, BEFORE, bare=True)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                cards = dict(weekly_cards(weekly_block(p[page_url(lang, "events/")])))
                gv = cards["gv"]
                self.assertIn(T["committee.weekly.title"][lang], visible(gv))
                self.assertNotIn("clock-3", gv)
                self.assertNotRegex(gv, r'<span class="min-w-0">\s*<span aria-hidden="true">·</span>\s*</span>')
                self.assertNotIn("data-cm-weekly", gv)
                self.assertNotIn("cm-menu", gv)
                self.assertIn('href="' + ("/es" if lang == "es" else "") + '/meetings/#weekly-open"', gv)
                self.assertIn("clock-3", cards["lv"])
                self.assertIn(WEEKLY[1]["i18n"]["day"][lang] + ' <span aria-hidden="true">·</span> '
                              + WEEKLY[1]["i18n"]["time_central"][lang], cards["lv"])

    def test_the_zoom_id_and_passcode_are_never_on_the_page(self):
        # (Google's "add" link carries them in the calendar entry's own description, as on /meetings/: it is the
        # entry people join from — that is not the page's text)
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                page = re.sub(r'href="https://calendar\.google\.com/[^"]*"', 'href=""', p[page_url(lang, "events/")])
                for s in (ZOOM_ID, ZOOM_DIGITS, PASSCODE, "834-5678-9012"):
                    self.assertNotIn(s, page)


class CommitteeMeetingLinks(unittest.TestCase):
    def test_links_to_the_committee_meeting_go_to_its_section(self):
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            want = ("/es" if lang == "es" else "") + "/meetings/#committee-meeting"
            with self.subTest(lang=lang):
                home = p[page_url(lang, "")]
                details = re.findall(r'<a class="[^"]*home-meet-more" href="([^"]+)"', home)
                self.assertTrue(details, "Home's meeting card")
                self.assertEqual(set(details), {want})
                events = p[page_url(lang, "events/")]
                pinned = re.search(r'<article class="cm-pinned.*?</article>', events, re.S).group(0)
                self.assertIn(f'<a href="{want}" class="btn-on-dark btn-sm">', pinned)
                self.assertIn(f'href="{want}">', p[page_url(lang, "contribute/")])
                self.assertRegex(p[page_url(lang, "gvr/")], r'<a class="btn-primary mt-4" href="' + re.escape(want) + '">')
                # /gvr/'s "Pass it on" welcome message (shared and copied as text: the full address), also as the
                # browser rolls it on (data-tpl); the printed handover sheet keeps the page's short address
                gvr = p[page_url(lang, "gvr/")]
                welcome = re.search(r'<div class="read-pass-msg mt-4" x-ref="welcome">(.*?)</div>', gvr, re.S).group(1)
                full = "https://neta65.github.io/aagrapevine" + want
                self.assertEqual(welcome.count(full), 2 if "data-tpl=" in welcome else 1, welcome)
                self.assertNotRegex(welcome, re.escape(full.split("#")[0]) + r"(?!#committee-meeting)")
                sheet = re.search(r'<div class="read-pass-sheet" data-sheet="handover">.*?</dl>', gvr, re.S).group(0)
                self.assertIn(" neta65.github.io/aagrapevine" + want.split("#")[0] + "</dd>", sheet)
                # and no page here links the bare meetings page for it any more
                for path in ("", "events/", "contribute/", "gvr/"):
                    self.assertNotRegex(p[page_url(lang, path)],
                                        r'href="' + re.escape(want.split("#")[0]) + r'"[^>]*>\s*(?:<svg.*?</svg>\s*)?'
                                        + "(?:" + "|".join(re.escape(T[k][lang]) for k in (
                                            "home.meeting_details_short", "committee.events.meeting_details",
                                            "read.contrib.ws_meeting", "read.gvr.help_btn")) + ")")

    def test_the_old_meeting_address_opens_the_committee_meeting(self):
        # /meeting/ was the committee meeting's page: without an #anchor it opens #committee-meeting (JavaScript,
        # the meta refresh and the link); a link's own #anchor (#weekly-open …) is kept
        p = built(self, BEFORE)
        for lang in ("en", "es"):
            target = ("/es" if lang == "es" else "") + "/meetings/"
            with self.subTest(lang=lang):
                stub = p[page_url(lang, "meeting/")]
                self.assertIn(f'location.replace("{target}" + location.search + (location.hash || "#committee-meeting"));', stub)
                self.assertIn(f'<meta http-equiv="refresh" content="0; url={target}#committee-meeting">', stub)
                self.assertIn(f'<a id="go" href="{target}#committee-meeting">', stub)
                self.assertIn('if (location.hash) document.getElementById("go").hash = location.hash;', stub)
                self.assertIn(f'<link rel="canonical" href="https://neta65.github.io/aagrapevine{target}">', stub)


if __name__ == "__main__":
    unittest.main()
