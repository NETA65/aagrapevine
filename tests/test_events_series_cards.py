"""The /events/ list since its redesign (November 2026): what is new first, one card per monthly series, the filters'
facets, a cancelled event that stays until its day, "Next up", the events' own pages' hero, the readable addresses'
redirects and the events /status/ asks the committee to look at — on made-up events (SITE_DATA: never the day's
data), a made-up monthly series (zz-booth, with a date the host moved and one that is cancelled), round 20's
committee meeting and Grapevine Meeting, and the build's clock stopped on Thursday, November 26, 2026.

  * TheList (src/pages/events.njk, eleventy/filters/event-list.js evList):
      - the one-off events by month, a cancelled one among them as a struck-through card (data-ev-cancelled) whose
        title and "See the notice" go to its notice page — no calendar menu, no flyer, no way to join;
      - "Every month" after the months: the committee meeting's card (its dates' anchors on it), then one card per
        series — its title its series' page, its next three dates shown and the others waiting (data-cm-max), each a
        link to its date's own page, a moved date marked "new date", what changed ("Jan 9 moved to Jan 10", "Mar 20:
        cancelled" — the notice —; a month the rule skips says nothing when a moved date stands for it); its "Add to
        calendar" and flyer are those of its next date, so they go when that date is over (data-cm-expire: the
        browser rolls its dates on before the next build); "See all dates" goes to its series' page's every date;
      - each card's facets (evFacets): its kind, the language it is held in (La Viña's: Spanish; "bilingual" in its
        title: both), in person / online, its city and its district; the filter bar's choices are what the cards hold;
      - "Next up": the next five events (one-off events and each series' next date, never a cancelled one), three
        shown; "Save the date" shown under the hero on narrower screens too (side-below);
      - the old filter ?filter=neta (our events and the committee meetings) has a chip of its own while it is on;
      - an event with a readable address keeps its old anchor on its card, its series' date entry and its row of
        "Past events" (an old link still lands there).
  * Facets (event-list.js heldIn, kindFacet, cityOf, modesOf, langWord): their rules, on events of their own — words
    that say English ("(in English)", "en inglés") before the host: La Viña's own workshop in English is English.
  * ASeriesPage (event-page.njk #evp-all-dates, eleventy/event-page-model.js everyDate): EVERY date to come, by year,
    each a link to its own page — every date page of the series is linked there —, a moved one marked, and under its
    year what changed (moved: its date's page; cancelled: the notice).
  * ThePages (src/_includes/partials/event-page.njk): the hero's actions — Join online (an online event), Add to
    calendar (the full links), Directions (a map of a real address) —, then "See all events", quieter, last; the
    district in the quick facts; "Organizer's page ↗" for an outside link.
  * Redirects (eleventy/event-redirects.js, src/pages/event-share-redirect.njk): the old address of an event with a
    readable one sends people on (script, meta refresh, a link), noindex, canonical, never in the sitemap.
  * Checks (event-list.js dataChecks, src/pages/status.njk "Events to check"): still tentative 60 days before, a
    venue still to be announced 45 days before, a file with no url:, a flyer event with no summary, an old file —
    each by its title in the page's language (/es/status/: the Spanish one, a file's title_es).

Runs Eleventy with Node.js (tests/nodejs.py); skipped without Node.js or the site's npm packages.

    python -m unittest tests.test_events_series_cards -v
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_r30_events_list import at, event  # noqa: E402
import test_r20_meeting as R20  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-11-26T18:00:00Z"             # Thu Nov 26, 2026, noon CST
BASE = "https://x.test"
T = json.loads((ROOT / "src" / "_i18n" / "evlist.json").read_text(encoding="utf-8"))
DALLAS = {"location": "Test Hall, 1 Main St, Dallas, TX 75201", "city": "Dallas", "state": "TX"}
FW = {"location": "Grupo Dos, 200 Main St, Fort Worth, TX 76106", "city": "Fort Worth", "state": "TX"}
BOOTH = "zz-booth"
BOOTH_RULE = {"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "19:00"}
RECURRING = [{"key": BOOTH, "title": "GV/LV booth at Test Hall", "title_es": "Mesa de GV/LV en Test Hall",
              "summary": "Our literature table at Test Hall.", "summary_es": "Nuestra mesa de literatura en Test Hall.",
              "week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "19:00", "location": DALLAS["location"],
              "months_ahead": 3, "skip_dates": ["2027-01-09"]}]
ZOOM = "https://us06web.zoom.us/j/81595931777"
CAL_SLUG = "2027-01-23-taller-de-la-vina-en-riverside"
OFF = "2026-12-05-zz-cancelled"
MOVED_OFF = "2027-03-20-zz-booth-moved"
PAST = "2026-11-07-zz-past-workshop"


def booth_day(d: date) -> dict:
    return event(f"ev:recurring:{BOOTH}:{d.isoformat()}", "recurring", "GV/LV booth at Test Hall", at(d, "17:00"), at(d, "19:00"),
                 title_es="Mesa de GV/LV en Test Hall", series=BOOTH, recurring=True, host="neta", rule=BOOTH_RULE, **DALLAS)


def items() -> tuple[list[dict], list[dict]]:
    out = [
        event("ev:manual:zz-workshop", "manual", "ZZ Writing Workshop — Fort Worth", at(date(2026, 12, 12), "19:00"),
              at(date(2026, 12, 12), "21:00"), slug="zz-workshop", title_es="Taller de Escritura ZZ — Fort Worth",
              tags=["workshop", "la-vina"], district="87", **FW),
        event("ev:manual:zz-online", "manual", "ZZ Online Writing Workshop", at(date(2026, 12, 19), "10:00"),
              at(date(2026, 12, 19), "12:00"), slug="zz-online", online_url=ZOOM, platform="Zoom"),
        event("ev:manual:zz-bilingual", "manual", "ZZ Bilingual Information Workshop", at(date(2027, 1, 16), "13:00"),
              at(date(2027, 1, 16), "15:00"), slug="zz-bilingual", location="Test Center, 1 Main St, Tyler, TX 75702",
              city="Tyler", state="TX"),
        {**event("ev:manual:zz-acm", "manual", "ZZ Winter ACM", "2027-02-21", "2027-02-21", slug="zz-acm",
                 tags=["neta65", "acm"], location="Mid-Cities Group, 300 West Pipeline Rd, Hurst, TX 76053", city="Hurst",
                 state="TX"), "url": "https://neta65.org/event/zz-acm/"},
        event("ev:manual:zz-tentative", "manual", "ZZ Tentative Workshop", "2027-01-10", "2027-01-10", slug="zz-tentative",
              tentative=True, **DALLAS),
        event("ev:manual:zz-tba", "manual", "ZZ Recording Workshop", at(date(2027, 1, 5), "13:00"), at(date(2027, 1, 5), "15:00"),
              slug="zz-tba", location="Venue to be announced", location_tba=True, city="Plano", state="TX"),
        {**event("ev:lvcal:zz1", "lv-calendar", "Taller de La Viña en Riverside", "2027-01-23", "2027-01-23", source="calendar",
                 slug=CAL_SLUG, city="Riverside", state="CA", location="Riverside, CA"),
         "url": "https://www.aalavina.org/events/zz1", "lang": "es"},
        event("ev:flyer:zzflyer", "flyer", "ZZ Flyer Workshop", "2026-12-28", "2026-12-28", source="drive", **DALLAS),
        # one that took place (its readable address since the redesign; its old anchor on its row of "Past events")
        event("ev:flyer:zzpast", "flyer", "ZZ Past Workshop", at(date(2026, 11, 7), "13:00"), at(date(2026, 11, 7), "15:00"),
              source="drive", slug=PAST, **DALLAS),
        *[booth_day(d) for d in (date(2026, 12, 12), date(2027, 2, 13), date(2027, 3, 13), date(2027, 4, 10))],
        # the host moved January's date (the rule's January 9 is in skip_dates): a dated flyer of the series
        {**event("ev:flyer:zzmoved", "flyer", "GV/LV booth at Test Hall", at(date(2027, 1, 10), "17:00"),
                 at(date(2027, 1, 10), "19:00"), source="drive", title_es="Mesa de GV/LV en Test Hall", series_of=BOOTH,
                 host="neta", slug="2027-01-10-zz-booth-moved", **DALLAS)},
    ]
    for it in out:
        if it["category"] == "manual" and not it["url"]:
            it["url"] = f"/events/#{it['extra']['slug']}"
        it["summary"] = f"{it['title']}: a test event." if it["id"] != "ev:flyer:zzflyer" else ""
        it["extra"]["file"] = f"content/events/{it['extra']['slug']}.md" if it["category"] == "manual" else None
    cancelled = [
        {**event(f"ev:manual:{OFF}", "manual", "ZZ Cancelled Workshop", at(date(2026, 12, 5), "13:00"), at(date(2026, 12, 5), "15:00"),
                 slug=OFF, cancelled=True, cancelled_note={"en": "The host group could not hold it."}, **FW), "url": f"/events/#{OFF}"},
        {**event("ev:flyer:zzmovedoff", "flyer", "GV/LV booth at Test Hall", at(date(2027, 3, 20), "17:00"), at(date(2027, 3, 20), "19:00"),
                 source="drive", series_of=BOOTH, slug=MOVED_OFF, cancelled=True, **DALLAS)},
    ]
    return out, cancelled


BUILD_JS = r"""
process.env.ONLY = input.only;
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const yaml = await import("js-yaml");
const { Eleventy } = await import("@11ty/eleventy");
const cfg = yaml.load(input.yaml);
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-ev-list-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(c) {
      const none = (o) => Object.fromEntries(Object.keys(o || {}).map((k) => [k, null]));
      // the series' pages are worked out from the global data (a pagination's `before`), not a page's computed data
      c.addGlobalData("site", { "override:recurring_events": input.recurring.concat(cfg.recurring_events || []) });
      c.addGlobalData("eleventyComputed", {
        site: (data) => ({ ...data.site, meeting: { ...none(data.site.meeting), ...cfg.meeting }, recurring_events: input.recurring.concat(cfg.recurring_events || []) }),
      });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url).map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""
ONLY = "events.njk,event-share,status,sitemap"


class Built:
    pages: dict | None = None

    @classmethod
    def get(cls, case: unittest.TestCase) -> dict:
        if cls.pages is None:
            tmp = Path(tempfile.mkdtemp(prefix="gv-ev-list-data-"))
            try:
                (tmp / "events").mkdir()
                # an old file (over more than 90 days ago) and one still to come
                (tmp / "events" / "2026-07-01-zz-old.md").write_text('---\ntitle: "ZZ Old Booth"\ntitle_es: "Mesa vieja ZZ"\nstart: 2026-07-01\n---\n', encoding="utf-8")
                (tmp / "events" / "2027-02-21-zz-acm.md").write_text('---\ntitle: "ZZ Winter ACM"\nstart: 2027-02-21\n---\n', encoding="utf-8")
                (tmp / "events" / "README.md").write_text("# not an event\n", encoding="utf-8")
                evs, off = items()
                (tmp / "events.json").write_text(json.dumps({"updated": NOW, "items": evs, "cancelled": off}), encoding="utf-8")
                cls.pages = run_js(case, BUILD_JS, data={"only": ONLY, "recurring": RECURRING, "yaml": R20.YAML}, timeout=900,
                                   now=NOW, env={"SITE_DATA": str(tmp), "CONTENT_EVENTS": str(tmp / "events"),
                                                 "SITE_URL": BASE, "STRICT_BUILD": "", "LASTMOD": ""})
            finally:
                shutil.rmtree(tmp, True)
        return cls.pages


def main_of(page: str) -> str:
    return page[page.index('<main id="main"'):page.index("</main>")]


def text(fragment: str) -> str:
    t = re.sub(r"<(script|style|template)\b.*?</\1>|<svg\b.*?</svg>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def card(page: str, anchor: str) -> str:
    """A card of the list: its <li id="…"> start tag through its </article>."""
    c = page[page.index(f'<li id="{anchor}"'):]
    return c[:c.index("</article>")]


def section(page: str, start: str) -> str:
    i = page.index(start)
    depth, j = 0, i
    for m in re.finditer(r"<section\b|</section>", page[i:]):
        depth += 1 if m.group(0) == "<section" else -1
        if depth == 0:
            j = i + m.end()
            break
    return page[i:j]


class TheList(unittest.TestCase):
    def pages(self) -> dict:
        return Built.get(self)

    def test_the_one_off_events_first_a_cancelled_one_struck_through(self):
        for pre, lang in (("", "en"), ("/es", "es")):
            page = self.pages()[f"{pre}/events/"]
            with self.subTest(lang=lang):
                ids = re.findall(r'<li id="([^"]+)" data-group=', page)
                # the months' cards in date order, then the series' cards
                self.assertEqual(ids[:10], [OFF, "zz-workshop", "zz-online", "ev-flyer-zzflyer", "zz-tba", "zz-tentative",
                                            "zz-bilingual", CAL_SLUG, "zz-acm", f"ev-series-{BOOTH}"])
                self.assertLess(page.index(f'<li id="{OFF}"'), page.index('<section id="ev-pinned"'))
                off = card(page, OFF)
                self.assertIn("data-ev-cancelled", off[:off.index(">")])
                self.assertIn('class="card cm-event ev-accent ev-tone-other ev-cancelled" x-ignore', off)
                self.assertRegex(off, r'<a href="' + re.escape(f"{pre}/events/{OFF}/") + r'" [^>]*><s>ZZ Cancelled Workshop</s>')
                self.assertIn(f'href="{pre}/events/{OFF}/">', off, "See the notice")
                self.assertIn(T["evlist.notice"][lang], text(off))
                self.assertIn("The host group could not hold it.", text(off))
                for never in ("data-cm-ics", "cm-menu", "data-cm-preview", "Join"):
                    self.assertNotIn(never, off)
                # its notice page is built
                self.assertIn(f"{pre}/events/{OFF}/", self.pages())

    def test_one_card_per_series_with_what_changed(self):
        for pre, lang in (("", "en"), ("/es", "es")):
            page = self.pages()[f"{pre}/events/"]
            with self.subTest(lang=lang):
                series = section(page, '<section id="ev-pinned"')
                self.assertGreater(page.index('<section id="ev-pinned"'), page.rindex('class="cm-month"'))
                # the committee meeting first: one card, its dates' anchors on it
                self.assertLess(series.index('<li data-group="committee neta"'), series.index(f'<li id="ev-series-{BOOTH}"'))
                self.assertGreaterEqual(len(re.findall(r'<span id="ev-committee-\d{4}-\d{2}-\d{2}"></span>', series)), 12)
                booth = card(page, f"ev-series-{BOOTH}")
                self.assertRegex(booth, r'<h3 [^>]*><a href="' + re.escape(f"{pre}/events/series/{BOOTH}/") + '"')
                dates = re.findall(r'<li id="([^"]+)" data-cm-expire="[^"]+"(?: class="([^"]*)")?><a class="ev-series-date" href="([^"]+)">(.*?)</a></li>', booth)
                self.assertEqual([d[0] for d in dates], [f"ev-recurring-{BOOTH}-2026-12-12", "2027-01-10-zz-booth-moved",
                                                         f"ev-recurring-{BOOTH}-2027-02-13", f"ev-recurring-{BOOTH}-2027-03-13",
                                                         f"ev-recurring-{BOOTH}-2027-04-10"])
                self.assertEqual([d[1] for d in dates], ["is-next", "", "", "hidden", "hidden"])
                self.assertEqual([d[2] for d in dates], [f"{pre}/events/{d[0]}/" for d in dates])
                self.assertIn(T["evlist.moved"][lang], dates[1][3])
                self.assertIn('data-cm-max="3"', booth)
                notes = text(booth[booth.index('class="ev-series-notes'):])
                if lang == "en":
                    self.assertIn("Jan 9 moved to Jan 10", notes)
                    self.assertIn("Mar 20: cancelled", notes)
                    self.assertNotIn("Not held on Jan 9", notes, "the moved date stands for it")
                else:
                    self.assertIn("El 9 ene se cambió al 10 ene", notes)
                    self.assertIn("20 mar: cancelado", notes)
                self.assertIn(f'href="{pre}/events/{MOVED_OFF}/"', booth, "the cancelled date's notice")
                self.assertIn(T["evlist.series_all"][lang], text(booth))
                self.assertIn(f'href="{pre}/events/series/{BOOTH}/#evp-all-dates"', booth, "See all dates: every date")
                # its next date's "Add to calendar" (and flyer) go when that date is over, as its entry does
                first = re.search(r'<li id="ev-recurring-zz-booth-2026-12-12" data-cm-expire="([^"]+)"', booth).group(1)
                wraps = re.findall(r'<div class="contents" data-cm-expire="([^"]+)">\s*(<details class="cm-menu">)?', booth)
                self.assertEqual([w[0] for w in wraps], [first, first], "the menu and flyer, then the thumbnail")
                self.assertTrue(wraps[0][1], "the calendar menu inside the first")
                self.assertEqual(booth.count('<details class="cm-menu">'), 1)
                self.assertIn("20261212T", booth[booth.index('<details class="cm-menu">'):], "the menu is the next date's")
                # a series' dates are no cards of their own
                self.assertNotRegex(page, rf'<li id="ev-recurring-{BOOTH}-[0-9-]+" data-group=')

    def test_each_card_says_its_facets_and_the_bar_offers_them(self):
        page = self.pages()["/events/"]
        facets = {a: dict(re.findall(r'data-(kind|lang|mode|city|district)="([^"]*)"', tag)) for a, tag in
                  re.findall(r'<li id="([^"]+)"( data-group="[^"]*"[^>]*)>', page) if "data-kind" in tag}
        self.assertEqual(facets["zz-workshop"], {"kind": "workshop", "lang": "es", "mode": "inperson", "city": "fort-worth", "district": "87"})
        self.assertEqual(facets["zz-online"], {"kind": "workshop", "lang": "en", "mode": "online"})
        self.assertEqual(facets["zz-bilingual"]["lang"], "both")
        self.assertEqual(facets["zz-acm"]["kind"], "area")
        self.assertEqual((facets[CAL_SLUG]["kind"], facets[CAL_SLUG]["lang"]), ("calendar", "es"))
        self.assertEqual(facets[f"ev-series-{BOOTH}"], {"kind": "booth", "lang": "en", "mode": "inperson", "city": "dallas"})
        self.assertEqual(facets[OFF]["kind"], "other", "no kind of workshop its title names")
        menus = {m.group(1): re.findall(r'<option value="([^"]*)">', m.group(2))
                 for m in re.finditer(r'<select[^>]*data-ev-facet="(\w+)"[^>]*>(.*?)</select>', page, re.S)}
        self.assertEqual(menus["lang"], ["", "en", "es", "both"])
        self.assertEqual(menus["mode"], ["", "inperson", "online"])
        self.assertEqual(menus["city"], ["", "dallas", "fort-worth", "hurst", "plano", "riverside", "tyler"])
        self.assertEqual(menus["district"], ["", "87"])
        self.assertIn("District 87", text(card(page, "zz-workshop")))
        self.assertIn("Distrito 87", text(card(self.pages()["/es/events/"], "zz-workshop")))
        chips = re.findall(r'data-ev-kind="(\w*)"', page)
        # (no weekly open meetings in this build: no "Online meetings" chip — only the kinds a card has)
        self.assertEqual(chips, ["", "workshop", "area", "booth", "committee", "calendar", "other"])
        # (round 38) "NETA 65 events" (the page's old chip, back): always on the page, just before "GV & LV calendars",
        # a chip of its own (data-ev-group, no kind), its count the browser's (groupCount); ?filter=neta presses it
        neta = re.search(r'<button type="button" class="chip" data-ev-group="neta" @click="setGroup\(\'neta\'\)" '
                         r':aria-pressed="\(group === \'neta\'\)\.toString\(\)" aria-pressed="false">(.*?)</button>', page, re.S)
        self.assertIsNotNone(neta)
        self.assertRegex(text(neta.group(1)), "^" + re.escape(T["evlist.group.neta"]["en"]) + r" \d+$")
        self.assertIn('x-text="groupCount(\'neta\')"', neta.group(1))
        self.assertLess(page.index('data-ev-group="neta"'), page.index('data-ev-kind="calendar"'))
        self.assertIn('data-ev-kind="" @click="all()" :aria-pressed="(!f.kind && !group).toString()"', page)
        self.assertIn(T["evlist.group.neta"]["es"], text(self.pages()["/es/events/"]))
        # "No events match": not while a folded card matches ("Show 2028 dates (n)" says it is there)
        self.assertIn('x-show="active && !visibleCount && !moreCount"', page)
        # the month chips' row goes as a whole while none of its chips shows
        self.assertRegex(page, r'<nav class="[^"]*" x-show="anyMonth" aria-label="[^"]+">\s*<span class="shrink-0 text-faint" aria-hidden="true">')

    def test_next_up_and_save_the_date_on_a_phone(self):
        page = self.pages()["/events/"]
        nu = section(page, '<section id="ev-nextup"')
        self.assertIn('class="ev-nextup lg:hidden"', nu)
        self.assertIn('data-cm-max="3"', nu)
        entries = re.findall(r'<li class="ev-tone-\w+( hidden)?" data-cm-expire="[^"]+"><a class="ev-nextup-item" href="#([^"]+)"', nu)
        self.assertEqual([a for _, a in entries], [f"ev-recurring-{BOOTH}-2026-12-12", "zz-workshop", "ev-committee-2026-12-16",
                                                   "zz-online", "ev-flyer-zzflyer"])
        self.assertEqual([bool(h) for h, _ in entries], [False, False, False, True, True])
        self.assertNotIn(OFF, nu, "never a cancelled event")
        # before the list; "Save the date" under the hero below 1024px (side-below), not hidden there
        self.assertLess(page.index('id="ev-nextup"'), page.index('<section class="ev-main'))
        self.assertIn("side-below", page[:page.index('id="ev-nextup"')])
        self.assertNotIn("side-hide", page)

    def test_an_old_anchor_stays_on_its_card(self):
        for pre in ("", "/es"):
            page = self.pages()[f"{pre}/events/"]
            with self.subTest(lang=pre or "en"):
                self.assertIn('<span id="ev-lvcal-zz1" class="sr-only"></span>', card(page, CAL_SLUG))
                # a series' date made from a flyer: on its entry of the series' card
                entry = re.search(r'<li id="2027-01-10-zz-booth-moved"[^>]*>(.*?)</li>', card(page, f"ev-series-{BOOTH}")).group(1)
                self.assertIn('<span id="ev-flyer-zzmoved"></span>', entry)
                self.assertTrue(entry.endswith("</a>"), "inside its link")
                # an event that took place: on its row of "Past events"
                past = page[page.index("data-cm-past"):]
                row = re.search(rf'<li id="{PAST}"[^>]*>(.*?)</li>', past, re.S).group(1)
                self.assertTrue(row.startswith('<span id="ev-flyer-zzpast" class="sr-only"></span>'))
                ids = re.findall(r'\sid="([^"]+)"', page)
                self.assertEqual([i for i in set(ids) if ids.count(i) > 1], [], "no id twice")


class ASeriesPage(unittest.TestCase):
    def test_every_date_with_what_changed(self):
        pages = Built.get(self)
        for pre, lang in (("", "en"), ("/es", "es")):
            with self.subTest(lang=lang):
                page = pages[f"{pre}/events/series/{BOOTH}/"]
                sec = section(page, '<section id="evp-all-dates"')
                years = re.findall(r'<h3 class="evp-all-year">(\d{4})</h3>', sec)
                self.assertEqual(years, ["2026", "2027"])
                links = re.findall(r'<a class="ev-series-date" href="([^"]+)">(.*?)</a>', sec)
                self.assertEqual([h for h, _ in links], [f"{pre}/events/{a}/" for a in (
                    f"ev-recurring-{BOOTH}-2026-12-12", "2027-01-10-zz-booth-moved", f"ev-recurring-{BOOTH}-2027-02-13",
                    f"ev-recurring-{BOOTH}-2027-03-13", f"ev-recurring-{BOOTH}-2027-04-10")])
                self.assertIn(T["evlist.moved"][lang], links[1][1])
                # every date page of the series is linked from here (the list's card shows three)
                own = sorted(u for u in pages if re.fullmatch(rf"{pre}/events/ev-recurring-{BOOTH}-[0-9-]+/", u))
                self.assertTrue(own)
                self.assertEqual([u for u in own if f'href="{u}"' not in sec], [])
                # what changed, under its year: January's date moved (its page), March 20 cancelled (the notice)
                y2027 = sec[sec.index('<h3 class="evp-all-year">2027</h3>'):]
                notes = y2027[:y2027.index('<ul class="ev-series-dates"')]
                self.assertIn(f'<a class="link" href="{pre}/events/2027-01-10-zz-booth-moved/">', notes)
                self.assertIn(f'<a class="link" href="{pre}/events/{MOVED_OFF}/">', notes)
                if lang == "en":
                    self.assertIn("Jan 9 moved to Jan 10", text(notes))
                    self.assertIn("Mar 20: cancelled", text(notes))
                else:
                    self.assertIn("El 9 ene se cambió al 10 ene", text(notes))
                self.assertNotIn("evp-all-notes", sec[:sec.index('<h3 class="evp-all-year">2027</h3>')], "2026: nothing changed")
                # a date's page: its "Next dates" heading's link comes here
                self.assertIn(f'href="{pre}/events/series/{BOOTH}/#evp-all-dates"', pages[f"{pre}/events/ev-recurring-{BOOTH}-2027-02-13/"])


class ThePages(unittest.TestCase):
    def pages(self) -> dict:
        return Built.get(self)

    def hero(self, url: str) -> str:
        p = self.pages()[url]
        start = p.index('class="hero-actions evp-hero-actions"')
        return p[start:p.index("</a>", p.index("evp-hero-all", start)) + 4]

    def test_the_hero_has_the_actions(self):
        for pre in ("", "/es"):
            with self.subTest(lang=pre or "en"):
                leaf = self.hero(f"{pre}/events/zz-workshop/")
                self.assertIn('<details class="cm-menu">', leaf)
                self.assertRegex(leaf, r'href="https://calendar\.google\.com/calendar/render\?[^"]*details=', "the full links")
                self.assertIn("data-cm-ics=", leaf)
                self.assertIn("https://www.google.com/maps/search/?api=1&amp;query=", leaf, "Directions")
                self.assertNotIn(ZOOM, leaf)
                links = re.findall(r'<a class="([^"]+)" href="([^"]+)"', leaf)
                self.assertEqual(links[-1], ("btn-on-dark btn-sm evp-hero-all", f"{pre}/events/#zz-workshop"), "See all events, last, quieter")
                online = self.hero(f"{pre}/events/zz-online/")
                self.assertTrue(online.split("<a ", 1)[1].startswith(f'class="btn-light" href="{ZOOM}"'), "Join online first")
                self.assertNotIn("google.com/maps", online, "no place: no map")
                # the card below keeps its flyer, its outside page and Share — not a second Join or calendar menu
                page = self.pages()[f"{pre}/events/zz-online/"]
                body = page[page.index('<article class="card cm-event evp-card'):]
                body = body[:body.index("</article>")]
                self.assertNotIn("cm-menu", body)
                self.assertNotIn(ZOOM + '" target', body)

    def test_the_district_and_the_organizers_page(self):
        facts = self.pages()["/events/zz-workshop/"]
        facts = facts[facts.index('id="evp-facts-h"'):]
        facts = text(facts[:facts.index("</section>")])
        self.assertIn("District 87", facts)
        self.assertIn("Distrito 87", text(self.pages()["/es/events/zz-workshop/"][self.pages()["/es/events/zz-workshop/"].index('id="evp-facts-h"'):]))
        acm = main_of(self.pages()["/events/zz-acm/"])
        self.assertIn(T["evlist.organizer"]["en"] + " ↗", text(acm))
        self.assertIn("Página del organizador ↗", text(main_of(self.pages()["/es/events/zz-acm/"])))


class Redirects(unittest.TestCase):
    def test_the_old_address_sends_people_on(self):
        p = Built.get(self)
        for pre in ("", "/es"):
            with self.subTest(lang=pre or "en"):
                old = p[f"{pre}/events/ev-lvcal-zz1/"]
                target = f"{pre}/events/{CAL_SLUG}/"
                self.assertIn(f"location.replace({json.dumps(target)} + location.search + location.hash)", old)
                self.assertIn(f'<meta http-equiv="refresh" content="0; url={target}">', old)
                self.assertIn('<meta name="robots" content="noindex">', old)
                self.assertIn(f'<link rel="canonical" href="{BASE}{target}">', old)
                self.assertIn(f'<a href="{target}">', old)
                self.assertIn(target, p, "the page it sends people to is built")
        sitemap = p["/sitemap.xml"]
        self.assertNotIn("ev-lvcal-zz1", sitemap)
        # a date the host moved, made from a flyer: its old address too (to its date's page)
        self.assertIn('content="0; url=/events/2027-01-10-zz-booth-moved/"', p["/events/ev-flyer-zzmoved/"])
        # an event that keeps its address (a content/events file) has no redirect
        self.assertFalse([u for u in p if u.startswith("/events/ev-manual-")])


class Checks(unittest.TestCase):
    def test_events_to_check_on_the_status_page(self):
        page = Built.get(self)["/status/"]
        sec = section(page, '<section id="event-checks"')
        found = {m.group(1): text(m.group(2)) for m in re.finditer(r'<article class="card card-pad" aria-labelledby="evcheck-(\w+)">(.*?)</article>', sec, re.S)}
        self.assertEqual(list(found), ["tentative", "tba", "nolink", "summary", "stale"])
        self.assertIn("ZZ Tentative Workshop", found["tentative"])
        self.assertIn("ZZ Recording Workshop", found["tba"])
        self.assertIn("content/events/zz-workshop.md", found["nolink"])
        self.assertNotIn("ZZ Winter ACM", found["nolink"], "it has its url:")
        self.assertIn("ZZ Flyer Workshop", found["summary"])
        self.assertIn("content/events/2026-07-01-zz-old.md", found["stale"])
        self.assertNotIn("zz-acm", found["stale"])
        self.assertIn("December 12, 2026", found["nolink"], "its day in Central time (an evening event: not the 13th)")
        es = section(Built.get(self)["/es/status/"], '<section id="event-checks"')
        self.assertIn(T["evlist.check.title"]["es"], text(es))
        # in Spanish: each event's Spanish title (the one the rest of /es/ shows), a file's title_es; the page in Spanish
        found_es = {m.group(1): m.group(2) for m in re.finditer(r'<article class="card card-pad" aria-labelledby="evcheck-(\w+)">(.*?)</article>', es, re.S)}
        self.assertIn("Taller de Escritura ZZ — Fort Worth", text(found_es["nolink"]))
        self.assertNotIn("ZZ Writing Workshop", text(found_es["nolink"]))
        self.assertIn('href="/es/events/zz-workshop/"', found_es["nolink"])
        self.assertIn("Mesa vieja ZZ", text(found_es["stale"]))
        self.assertIn("ZZ Old Booth", found["stale"], "English: its own title")


FACETS_JS = r"""
const L = await imp("eleventy/filters/event-list.js");
const site = { recurring_events: [{ key: "zz", language: "both" }], meeting: { language: "es" } };
const ev = (o) => Object.assign({ title: "", summary: "", location: "", isOnline: false, item: { extra: {}, i18n: {} } }, o);
out({
  words: ["English", "español", "Bilingüe", "en", "ES", "both", "french", ""].map(L.langWord),
  held: {
    plain: L.heldIn(ev({ title: "Writing Workshop" }), site),
    lvHost: L.heldIn(ev({ title: "Workshop", host: "lv" }), site),
    saysSpanish: L.heldIn(ev({ title: "Workshop (in Spanish)" }), site),
    saysBoth: L.heldIn(ev({ title: "Taller", summary: "A bilingual workshop" }), site),
    lvSaysEnglish: L.heldIn(ev({ title: "Workshop (in English)", host: "lv" }), site),
    lvSaysIngles: L.heldIn(ev({ title: "Taller de La Viña (en inglés)", host: "lv" }), site),
    saysEachLanguage: L.heldIn(ev({ title: "Workshop", summary: "Held in English, with a group in Spanish" }), site),
    own: L.heldIn(ev({ title: "Workshop (in Spanish)", item: { extra: { language: "en" } } }), site),
    series: L.heldIn(ev({ recurring: true, series: "zz", title: "Booth" }), site),
    committee: L.heldIn(ev({ committee: true, title: "Committee meeting" }), site),
  },
  modes: [L.modesOf(ev({ location: "Hall, Dallas, TX" })), L.modesOf(ev({ isOnline: true })),
          L.modesOf(ev({ location: "Hall, Dallas, TX", isOnline: true })), L.modesOf(ev({ committee: true, location: "Google Meet" }))],
  city: [L.cityOf(ev({ location: "Grupo Uno, 100 Main St, Garland, TX 75041" })), L.cityOf(ev({ location: "X", item: { extra: { city: "Tyler" } } })),
         L.cityOf(ev({ isOnline: true })), L.cityOf(ev({ committee: true, location: "Google Meet" }))],
  district: [L.districtOf(ev({ item: { extra: { district: "87" } } })), L.districtOf(ev({ item: { extra: { district: "north" } } }))],
  attrs: L.facetAttrs({ kind: "workshop", lang: "es", modes: ["inperson", "online"], citySlug: "fort-worth", district: "87" }),
  kinds: L.KIND_FACETS,
});
"""


class Facets(unittest.TestCase):
    def test_the_rules(self):
        r = run_js(self, FACETS_JS, now=NOW)
        self.assertEqual(r["words"], ["en", "es", "both", "en", "es", "both", "", ""])
        self.assertEqual(r["held"], {"plain": "en", "lvHost": "es", "saysSpanish": "es", "saysBoth": "both", "own": "en",
                                     "series": "both", "committee": "es", "lvSaysEnglish": "en", "lvSaysIngles": "en",
                                     "saysEachLanguage": "both"})
        self.assertEqual(r["modes"], [["inperson"], ["online"], ["inperson", "online"], ["online"]])
        self.assertEqual(r["city"], ["Garland", "Tyler", "", ""])
        self.assertEqual(r["district"], ["87", ""])
        self.assertEqual(r["attrs"], ' data-kind="workshop" data-lang="es" data-mode="inperson online" data-city="fort-worth" data-district="87"')
        self.assertEqual(r["kinds"], ["workshop", "area", "booth", "online", "committee", "calendar", "other"])


if __name__ == "__main__":
    unittest.main()
