"""Round 30, Unit B — the /events/ agenda: the filters that really filter, all of the next year shown and the year
after it behind "Show more". (Round 30 made every date a card of its own and pinned our two monthly meetings on top;
since the list's redesign, November 2026, a monthly series is ONE card, after the one-off events, and the filters are
the kind, the language, in person / online, the city and the district — tests/test_events_series_cards.py and
tests/test_events_filters.py. The checks below say what of round 30 still holds.)

  * The fold (eleventy/filters/committee.js EVENTS_NEXT_YEAR_FROM = 11, eventsFoldFrom, eventsFold — the
    cmEventsFold filter), by whole years: the rest of the build's year in Central time is open and, from November on,
    all of the next year too — on November 13, 2026: November 2026 … December 2027, all of 2027 —; the first folded
    month is January of the year after ("2028-01" through October 31, 2027, Central midnight, not UTC's; "2029-01"
    from November 1, 2027); the folded months' keys, their events' number and the button's words: their year
    ("2028"), or the first and last year when they run into another one ("2028 – 2029").
  * The page (src/pages/events.njk, built with Eleventy, English and Spanish, ONLY that page, on November 13, 2026,
    with events of the test's own through December 2028 — real data lists dates only to November 2027 — and the
    settings of round 20's tests: the committee meeting and the Grapevine Meeting on Google Meet):
      - no "Show every monthly date" switch, no "Then …" line, no data-later: a monthly series is ONE card, each of
        its dates an entry of it (three shown, the others waiting); no card is hidden from the first paint (no
        data-dflt-hidden on an li);
      - the committee meeting is one card, in two groups (data-group="committee neta"), its dates' anchors on it;
        the kind chips count the cards (no "All" count);
      - the months of the one-off events: through December 2027 open; every 2028 month's section and jump chip carry
        data-cm-more and data-dflt-hidden, its heading tabindex="-1"; one "Show 2028 dates (n)" button (data-js-only,
        n = the folded cards), right after the last open month, its words for the browser in data-label ("{n}");
      - "Every month" (#ev-pinned) after the months and before the weekly open meetings, each series a card of the
        list; the committee meeting's dark card first, the Grapevine Meeting's (#ev-next-gvm) among them;
      - the Area's events (an assembly, an ACM) in one colour, "Area event" in the colour key and on an ACM's badge,
        "Area assembly" on an assembly's; the grey kind is "NETA 65" while every grey card is ours, "Other events"
        when an outside calendar's event is grey too; "Save the date" picks the next ASSEMBLY, never the ACM before it;
      - no id twice on the page.
  * The list in the browser (src/assets/js/committee.js cmEvents, on the page stand-in of tests/test_central_time.py):
    the kind chips count the cards of their kind; no filter shows every open card; "Showing N events" leaves the
    folded months out until they show; "Show 2028 dates" counts the folded cards the filters pick, shows them and
    moves the keyboard to the first folded month that shows something for them; a link to a card — a hashchange, or
    the "Next 5 weeks" calendar's window "cm:reveal" { id } — that the filters hide clears them, into a folded month
    opens the fold, to a weekly open meeting or a series' card brings that card; then the target is scrolled to,
    focused (tabindex="-1", no second scroll) and its card marked a moment (.cm-flash); a card that has passed is left
    alone; on load a link into a folded month opens it, one to a past event (its old anchor too) opens "Past events"
    and marks its row, and ?filter=committee / ?filter=calendar (the old chips) pick
    that kind, ?filter=neta shows what its chip showed (data-group~="neta": ours and the committee meetings) beside
    the menus, until it is let go; "No events match" waits while a folded card matches; the month chips' row
    goes while none of its chips shows. (Round 38) The "NETA 65 events" chip is on the page again: it picks ours and
    the committee meetings (setGroup), counts them under the menus (groupCount), lets go when picked again, and "All"
    lets it and the kind go; a bilingual card (data-lang="both") shows under English and under Spanish; an old
    #month-… anchor kept on "Every month" brings that section's heading; an old link to a committee meeting's later
    date, opened, goes on to its dates page (data-ev-dates) — the date its card shows, or a link inside the page,
    stays; a link to a past event's row brings it in view as a card is (reveal: marked, focused). (Round 38b) The
    chips are one choice, as the old ones were: a kind picked lets the NETA 65 chip go and the NETA 65 chip lets the
    kind go — the two together showed nothing ("No events match": no card of the GV & LV calendars is ours) —, each
    chip counting what it shows once picked (the menus only); ?filter=neta&kind=… (an address of before) keeps the
    kind; with committee.js not loaded (Alpine there) the page's stand-in for cmEvents (events.njk evStandIn) shows
    every card and month — the folded ones too, as without JavaScript — and hides the filters (the list was blank).
  * (Round 38) The committee meeting's dates page (src/pages/events-committee.njk, committee.js datesSettle, on the
    same page stand-in): its list comes with every card drawn (class cm-cv-all, data-cm-cv-settle — the first landing
    works without JavaScript too); 2 s after the page has loaded, and only once no scroll has come for 300 ms (the
    browser's smooth jump to the date), the class goes; a later #hash to one of its dates draws every card again,
    brings that date into view and lets the class go 1.5 s later; a #hash elsewhere, or a page without the list,
    is left alone.

Skipped without Node.js or the site's npm packages (tests/nodejs.py).

    python -m unittest tests.test_r30_events_list -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import unittest
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
import test_central_time as TCT  # noqa: E402  (the page stand-in, TCT.DOM — a module, so its tests don't run twice)
import test_r20_meeting as R20  # noqa: E402  (round 20's settings: the committee meeting + the Grapevine Meeting)
import test_r21_weekly as R21  # noqa: E402  (the weekly open meetings of round 21's tests)

ROOT = Path(__file__).resolve().parents[1]
CHI = ZoneInfo("America/Chicago")
NOW = "2026-11-13T18:00:00Z"             # Fri Nov 13, 2026, noon CST: the day of round 30
T = R21.T                                # every i18n string, by key


def at(day: date, hhmm: str) -> str:
    """A Central wall-clock time → the UTC instant as events.json writes it."""
    h, m = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, h, m, tzinfo=CHI).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(eid: str, category: str, title: str, start: str, end: str, *, source: str = "committee", slug: str = "",
          title_es: str = "", tags: list[str] | None = None, **extra) -> dict:
    """An event as data/site/events.json holds it (build_data)."""
    x = {"start": start, "end": end, "all_day": len(start) == 10, "location": None, "online_url": None, **extra}
    if slug:
        x["slug"] = slug
    return {"id": eid, "source": source, "kind": "event", "category": category, "url": "", "title": title, "summary": "",
            "lang": "en", "date": start, "status": "ok", "tags": tags or [], "extra": x,
            "i18n": {"title": {"en": title, "es": title_es or title}}, "machine": [], "is_new": False}


def second_saturdays(first: date, last: date) -> list[date]:
    out, y, m = [], first.year, first.month
    while (y, m) <= (last.year, last.month):
        d = date(y, m, 1)
        d += timedelta(days=(5 - d.weekday()) % 7 + 7)          # the second Saturday
        if first <= d <= last:
            out.append(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


BOOTH_RULE = {"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "19:00"}
PLACE = {"location": "Test Hall, 1 Main St, Dallas, TX 75201", "city": "Dallas", "state": "TX"}


def items() -> list[dict]:
    """The test's events: a one-off workshop first, an ACM before the Spring Assembly (2027), a monthly booth from
    December 2026 to December 2028 (25 dates: 12 in 2028), the Area's 2028 ACM and assembly, Grapevine's and La
    Viña's calendars (one of them in 2028), and one that took place."""
    out = [
        event("ev:flyer:zz-workshop", "flyer", "Writing Workshop — Tyler", at(date(2026, 11, 28), "13:00"),
              at(date(2026, 11, 28), "15:00"), source="drive", **PLACE),
        event("ev:manual:zz-winter-acm", "manual", "Winter ACM 2027", "2027-02-21", "2027-02-21", slug="zz-winter-acm",
              title_es="ACM de Invierno 2027", tags=["neta65", "acm"], **PLACE),
        event("ev:manual:zz-spring-assembly", "manual", "NETA 65 Spring Assembly 2027", "2027-03-19", "2027-03-21",
              slug="zz-spring-assembly", title_es="Asamblea de Primavera 2027 de NETA 65", tags=["assembly", "neta65"], **PLACE),
        event("ev:manual:zz-acm-2028", "manual", "Winter ACM 2028", "2028-02-20", "2028-02-20", slug="zz-acm-2028",
              title_es="ACM de Invierno 2028", tags=["neta65", "acm"], **PLACE),
        event("ev:manual:zz-assembly-2028", "manual", "NETA 65 Spring Assembly 2028", "2028-03-17", "2028-03-19",
              slug="zz-assembly-2028", title_es="Asamblea de Primavera 2028 de NETA 65", tags=["assembly", "neta65"], **PLACE),
        event("ev:gv-calendar:zz-roundup", "gv-calendar", "Grapevine Roundup 2028", "2028-05-06", "2028-05-06",
              source="calendar", location="Hall Dos, 300 Oak Ave, Austin, TX 78701"),
        event("ev:lv-calendar:zz-taller", "lv-calendar", "Taller de La Viña", "2027-06-05", "2027-06-05", source="calendar",
              location="Salón Uno, Houston, TX"),
        event("ev:manual:zz-held", "manual", "Workshop That Took Place", at(date(2026, 10, 3), "10:00"),
              at(date(2026, 10, 3), "12:00"), slug="zz-held", **PLACE),
    ]
    for d in second_saturdays(date(2026, 12, 1), date(2028, 12, 31)):
        out.append(event(f"ev:recurring:zz-booth:{d.isoformat()}", "recurring", "GV/LV booth at Test Hall",
                         at(d, "17:00"), at(d, "19:00"), title_es="Mesa de GV/LV en Test Hall", series="zz-booth",
                         recurring=True, rule=BOOTH_RULE, host="neta", **PLACE))
    return out


# An event of an outside calendar that names neither magazine: grey, and not ours (the colour key says "Other events")
GREY_OTHER = event("ev:ics:zz-other", "", "Unity Day", "2027-04-10", "2027-04-10", source="calendar",
                   location="Hall Tres, Tyler, TX")

# Eleventy with the site's config: only /events/, with the test's events, round 20's committee meeting and Grapevine
# Meeting (config/site.yml's own settings left aside: what the committee edits there never changes this test) and
# round 21's weekly open meetings — each variant a build of its own.
PAGES_JS = r"""
process.env.ONLY = "events.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const yaml = await import("js-yaml");
const { Eleventy } = await import("@11ty/eleventy");
const cfg = yaml.load(input.yaml);
const res = {};
for (const [name, items] of Object.entries(input.variants)) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r30-list-"));
  try {
    const elev = new Eleventy("src", dir, {
      quietMode: true, configPath: "eleventy.config.js",
      config(c) {
        const none = (o) => Object.fromEntries(Object.keys(o || {}).map((k) => [k, null]));
        c.addGlobalData("eleventyComputed", {
          db: (data) => ({ ...data.db, events: { updated: null, items }, weekly_open: { updated: "2026-11-02T12:00:00Z", items: input.weekly } }),
          site: (data) => ({ ...data.site, meeting: { ...none(data.site.meeting), ...cfg.meeting }, recurring_events: cfg.recurring_events }),
        });
      },
    });
    const pages = await elev.toJSON();
    res[name] = Object.fromEntries(pages.filter((p) => /\/events\/$/.test(p.url)).map((p) => [p.url, p.content]));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
out(res);
"""
BUILT: dict = {}


def pages(case: unittest.TestCase) -> dict:
    if not BUILT:
        BUILT.update(run_js(case, PAGES_JS, data={"yaml": R20.YAML, "weekly": R21.WEEKLY,
                                                   "variants": {"main": items(), "grey": items() + [GREY_OTHER]}},
                            timeout=900, now=NOW))
    return BUILT


def section_of(page: str, start: str) -> str:
    """The <section …> that starts with `start`, to its own </section> (sections inside it counted)."""
    i = page.index(start)
    depth, j = 0, i
    for m in re.finditer(r"<section\b|</section>", page[i:]):
        depth += 1 if m.group(0) == "<section" else -1
        if depth == 0:
            j = i + m.end()
            break
    return page[i:j]


def months(page: str) -> list[tuple[str, str]]:
    """(month key, the month's <section> start tag + its heading) in page order."""
    return [(m.group(2), m.group(0)) for m in re.finditer(
        r'<section class="cm-month"[^>]*x-ref="m(\d{4}-\d{2})"[^>]*>\s*<h2 id="month-(\d{4}-\d{2})"[^>]*>', page)]


def cards(page: str) -> list[tuple[str, str]]:
    """(anchor, data-group) of every card of the months."""
    return re.findall(r'<li id="([^"]+)" data-group="([^"]+)"', page)


def text(fragment: str) -> str:
    t = re.sub(r"<svg.*?</svg>", " ", fragment, flags=re.S)
    return TCT.plain(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))).strip()


# --------------------------------------------------------------------------- the fold
FOLD_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const ev = (key, short) => ({ monthKey: key, monthShort: short, past: false });
out({
  nextYearFrom: C.EVENTS_NEXT_YEAR_FROM,
  from: input.clocks.map((t) => C.eventsFoldFrom(new Date(t))),
  byDefault: C.eventsFoldFrom(),
  oneYear: C.eventsFold([ev("2027-12", "Dec 2027"), ev("2028-01", "Jan 2028"), ev("2028-01", "Jan 2028"), ev("2028-12", "Dec 2028")],
                        new Date(input.now)),
  twoYears: C.eventsFold([ev("2028-01", "Jan 2028"), ev("2028-06", "Jun 2028"), ev("2029-03", "Mar 2029")], new Date(input.now)),
  midYear: C.eventsFold([ev("2027-07", "Jul 2027"), ev("2027-12", "Dec 2027"), ev("2028-02", "Feb 2028"), ev("2028-12", "Dec 2028")],
                        new Date("2027-06-15T18:00:00Z")),
  lateYear: C.eventsFold([ev("2027-12", "Dec 2027"), ev("2028-12", "Dec 2028")], new Date("2027-11-15T18:00:00Z")),
  none: C.eventsFold([ev("2026-11", "Nov 2026"), ev("2027-12", "Dec 2027")], new Date(input.now)),
  pastOnly: C.eventsFold([{ ...ev("2028-01", "Jan 2028"), past: true }], new Date(input.now)),
  empty: C.eventsFold(null, new Date(input.now)),
  filter: typeof filters.cmEventsFold === "function",
});
"""


class Fold(unittest.TestCase):
    def test_the_rest_of_the_year_is_open_and_from_november_the_next_one_too(self):
        clocks = ["2026-11-13T18:00:00Z", "2026-12-01T06:00:00Z", "2027-01-01T06:00:00Z", "2027-06-15T18:00:00Z",
                  "2027-11-01T04:59:00Z", "2027-11-01T05:00:00Z", "2027-12-31T23:00:00Z", "2028-01-01T06:00:00Z"]
        r = run_js(self, FOLD_JS, data={"clocks": clocks, "now": NOW}, now=NOW)
        self.assertEqual(r["nextYearFrom"], 11)
        # November 13, 2026: all of 2027 open, 2028 folded; all through 2027 until October 31 (Central time's month,
        # not UTC's: Oct 31, 11:59 PM CDT = 04:59 UTC is still October), then 2028 opens too
        self.assertEqual(r["from"], ["2028-01", "2028-01", "2028-01", "2028-01", "2028-01", "2029-01", "2029-01",
                                     "2029-01"])
        self.assertEqual(r["byDefault"], "2028-01", "the build's clock")
        self.assertTrue(r["filter"])

    def test_what_is_folded_and_the_buttons_words(self):
        r = run_js(self, FOLD_JS, data={"clocks": [], "now": NOW}, now=NOW)
        self.assertEqual(r["oneYear"], {"from": "2028-01", "keys": ["2028-01", "2028-12"], "n": 3, "range": "2028"})
        self.assertEqual(r["twoYears"], {"from": "2028-01", "keys": ["2028-01", "2028-06", "2029-03"], "n": 3,
                                         "range": "2028 – 2029"})
        # mid-2027: the rest of 2027 open, the whole of 2028 still behind the button; November 2027: nothing folded
        self.assertEqual(r["midYear"], {"from": "2028-01", "keys": ["2028-02", "2028-12"], "n": 2, "range": "2028"})
        self.assertIsNone(r["lateYear"])
        for k in ("none", "pastOnly", "empty"):
            self.assertIsNone(r[k], k)


# --------------------------------------------------------------------------- the page
class EventsPage(unittest.TestCase):
    """(Since the list's redesign, November 2026, a monthly series is ONE card — tests/test_events_series_cards.py has
    the rest of it; round 30's "every date a card" is gone.)"""

    def test_one_card_per_series_and_no_switch(self):
        for url in ("/events/", "/es/events/"):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                for gone in ("cm-switch", "showAll", "data-later", "data-committee", "moreDates"):
                    self.assertNotIn(gone, page)
                anchors = [a for a, _ in cards(page)]
                # the booth: one card; every date to come an entry of it (25: December 2026 … December 2028), three of
                # them shown, the others waiting (expire(): data-cm-max)
                self.assertIn("ev-series-zz-booth", anchors)
                self.assertEqual([a for a in anchors if a.startswith("ev-recurring-zz-booth-")], [])
                series = section_of(page, '<section id="ev-pinned"')
                dates = re.findall(r'<li id="(ev-recurring-zz-booth-[0-9-]+)" data-cm-expire="[^"]+"( class="[^"]*")?>', series)
                self.assertEqual(len(dates), 25)
                self.assertEqual([c for _, c in dates[:3]], [' class="is-next"', "", ""])
                self.assertTrue(all(c == ' class="hidden"' for _, c in dates[3:]))
                self.assertNotRegex(page, r'<li id="[^"]+" data-group="[^"]+"[^>]*data-dflt-hidden')
                # (the past workshop is in "Past events", not a card of the months)
                self.assertNotIn("zz-held", anchors)
                self.assertIn('<li id="zz-held" class="flex', page)

    def test_the_committee_meeting_is_one_card_and_a_neta_65_event_too(self):
        for url in ("/events/", "/es/events/"):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                groups = Counter(g for _, g in re.findall(r'<li( id="[^"]+")? data-group="([^"]+)"', page))
                self.assertEqual(groups["committee neta"], 1, "one card for every committee meeting")
                card = page[page.index('<li data-group="committee neta"'):]
                card = card[:card.index("</article>")]
                self.assertIn('data-kind="committee"', card)
                self.assertGreaterEqual(len(re.findall(r'<span id="ev-committee-[0-9-]+"></span>', card)), 12)
                self.assertNotRegex(page, r'<li id="ev-committee-')
                # the kind chips count the cards (no "All" count)
                chips = dict(re.findall(r'data-ev-kind="(\w*)"[^>]*>.*?(?:<span class="cm-chip-count"[^>]*>(\d+)</span>)?\s*</button>',
                                        page, re.S))
                self.assertEqual(chips["committee"], "1")
                self.assertEqual(chips["booth"], "1")
                self.assertEqual(chips[""], "")

    def test_all_of_2027_open_2028_folded_behind_one_button(self):
        for url, words in (("/events/", "Show 2028 dates ({n})"), ("/es/events/", "Mostrar las fechas de 2028 ({n})")):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                ms = months(page)
                keys = [k for k, _ in ms]
                # (the months of the one-off events: a series' dates are on its card)
                self.assertEqual(keys, ["2026-11", "2027-02", "2027-03", "2027-06", "2028-02", "2028-03", "2028-05"])
                for key, tag in ms:
                    folded = key >= "2028-01"
                    self.assertEqual("data-cm-more data-dflt-hidden" in tag, folded, key)
                    self.assertEqual('tabindex="-1"' in tag, folded, key)
                    self.assertIn("x-show=\"monthVisible($el) && (more || !$el.hasAttribute('data-cm-more'))\"", tag)
                # the jump chips: the same months folded
                chips = re.findall(r"<li x-show=\"monthVisible\(\$refs\['m(\d{4}-\d{2})'\]\)[^\"]*\"([^>]*)><a class=\"chip\"", page)
                self.assertEqual([k for k, _ in chips], keys)
                for key, rest in chips:
                    self.assertEqual("data-cm-more data-dflt-hidden" in rest, key >= "2028-01", key)
                # one button, right after the last open month and before the first folded one; it says how many dates
                # it shows
                self.assertEqual(page.count('class="cm-ev-more"'), 1)
                at = page.index('class="cm-ev-more"')
                self.assertLess(page.index('x-ref="m2027-06"'), at)
                self.assertLess(at, page.index('x-ref="m2028-02"'))
                button = page[at:page.index("</div>", at)]
                self.assertIn('data-js-only x-show="!more && moreCount"', button)
                self.assertIn('@click="showMore()"', button)
                self.assertIn("#i-chevron-down", button)
                folded = 0
                for key, _ in ms:
                    if key >= "2028-01":
                        sec = section_of(page, f'<section class="cm-month" data-cm-month x-ref="m{key}"')
                        folded += len(re.findall(r'<li id="[^"]+" data-group=', sec))
                # the ACM, the assembly, the roundup (a series' 2028 dates are on its card)
                self.assertEqual(folded, 3)
                self.assertIn(f'data-label="{html.escape(words, quote=True)}"', button)
                self.assertIn(">" + words.replace("{n}", str(folded)) + "</span>", button)

    def test_the_monthly_series_come_after_the_one_off_events(self):
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                self.assertEqual(page.count('id="ev-pinned"'), 1)
                pinned = section_of(page, '<section id="ev-pinned"')
                self.assertTrue(pinned.startswith('<section id="ev-pinned" class="ev-series-sec" x-ref="series" '
                                                  'x-show="monthVisible($el)" aria-labelledby="ev-pinned-title">'))
                self.assertIn(T["evlist.series_title"][lang], text(pinned))
                self.assertIn(T["evlist.series_text"][lang], text(pinned))
                self.assertNotIn("data-dflt-hidden", pinned)
                # each series a card of the list (the filters show or hide it like any other)
                self.assertGreaterEqual(pinned.count('x-show="show($el)"'), 3)
                # the one-off events first (the months), then every month, then every week
                self.assertLess(page.index('class="ev-legend"'), page.index('class="cm-month"'))
                self.assertLess(page.rindex('class="cm-month"'), page.index('id="ev-pinned"'))
                self.assertLess(page.index('id="ev-pinned"'), page.index('<section id="ev-weekly"'))
                # the committee meeting's dark card, the page's first .cm-pinned, then the Grapevine Meeting's
                self.assertEqual(page.count('<article class="cm-pinned'), 1)
                self.assertLess(pinned.index('<article class="cm-pinned @container" x-data="cmMeeting('), pinned.index('id="ev-next-gvm"'))
                gvm = pinned[pinned.index('<article id="ev-next-gvm"'):]
                self.assertIn(T["committee.events.first_meeting"][lang], text(gvm))
                self.assertIn("meet.google.com/abc-defg-hij", gvm)

    def test_the_areas_events_share_a_colour_and_say_what_they_are(self):
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                def badge(anchor):
                    i = page.index(f'<li id="{anchor}"')
                    card = page[i:page.index("</article>", i)]
                    self.assertIn("ev-tone-assembly", card)
                    return text(re.search(r'<span class="badge ev-badge">.*?</span>', card, re.S).group(0))
                self.assertEqual(badge("zz-winter-acm"), T["committee.events.kind.assembly"][lang])
                self.assertEqual(badge("zz-spring-assembly"), T["committee.events.badge_assembly"][lang])
                self.assertEqual(T["committee.events.kind.assembly"]["en"], "Area event")
                self.assertEqual(T["committee.events.badge_assembly"]["en"], "Area assembly")
                legend = dict(re.findall(r'<li class="ev-tone-(\w+)"><span class="ev-dot" aria-hidden="true"></span>([^<]+)</li>', page))
                self.assertEqual(legend["assembly"], T["committee.events.kind.assembly"][lang])
                # the grey cards (the workshop, the pinned Grapevine Meeting) are all ours: "NETA 65"
                self.assertEqual(legend["other"], T["committee.events.kind.neta"][lang])
                # "Save the date": the Spring Assembly — the workshop is first in the list, the ACM is no assembly
                # (its link: since round 37 the assembly's own page)
                aside = page[page.index('aria-labelledby="ev-aside-title"'):]
                aside = aside[:aside.index("</section>")]
                pre = "/es" if lang == "es" else ""
                self.assertIn(f'href="{pre}/events/zz-spring-assembly/"', aside)
                self.assertNotIn("zz-winter-acm", aside)
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            with self.subTest(url=url, variant="an outside calendar's grey event"):
                legend = dict(re.findall(r'<li class="ev-tone-(\w+)"><span class="ev-dot" aria-hidden="true"></span>([^<]+)</li>',
                                         pages(self)["grey"][url]))
                self.assertEqual(legend["other"], T["committee.events.kind.other"][lang])

    def test_no_id_twice(self):
        for url in ("/events/", "/es/events/"):
            ids = Counter(re.findall(r'\sid="([^"]+)"', pages(self)["main"][url]))
            with self.subTest(url=url):
                self.assertEqual([i for i, n in ids.items() if n > 1], [])


# --------------------------------------------------------------------------- the list in the browser
# The agenda in miniature: the kind chips and two menus (the language, the city), two open months of one-off events (a
# cancelled one among them) and two folded ones, the monthly series (the committee meeting's card with its dates'
# anchors, the booth's card with a date it lists and one it does not), the weekly open meetings — the card ids name
# what they are.
DOM_JS = r"""
const scrolled = [], focused = [];
const name = (e) => e.attrs.id || e.attrs["data-kind"] || e.tagName;
El.prototype.scrollIntoView = function () { scrolled.push(name(this)); };
El.prototype.focus = function (o) { focused.push([name(this), !!(o && o.preventScroll)]); };
const chip = (k) => el("button", { "data-ev-kind": k }, k ? [el("span", { class: "cm-chip-count" }, [], "0")] : []);
const menu = (k, values) => el("select", { "data-ev-facet": k }, ["", ...values].map((v) => el("option", { value: v })));
const card = (id, g, f, end) => el("li", Object.assign(id ? { id } : {}, { "data-group": g, "data-cm-expire": end || "2030-01-01T00:00:00Z" }, f),
                                   [el("article", { class: "card cm-event" })]);
const facets = (kind, lang, mode, city) => Object.assign({ "data-kind": kind, "data-lang": lang, "data-mode": mode }, city ? { "data-city": city } : {});
const month = (key, more, kids) => el("section", Object.assign({ class: "cm-month", "data-cm-month": "" }, more ? { "data-cm-more": "" } : {}),
                                      [el("h2", Object.assign({ id: "month-" + key }, more ? { tabindex: "-1" } : {})), el("ol", {}, kids)]);
function setup(opts) {
  opts = opts || {};
  const chips = ["", "workshop", "area", "booth", "online", "committee", "calendar"].map(chip);
  const menus = [menu("lang", ["en", "es"]), menu("mode", ["inperson", "online"]), menu("city", ["austin", "dallas", "houston", "tyler"])];
  const months = [
    month("2026-11", false, [card("zz-workshop", "neta", facets("workshop", "en", "inperson", "tyler"), "2026-11-29T00:00:00Z"),
                             Object.assign(card("zz-off", "neta", facets("workshop", "es", "inperson", "dallas")), {})]),
    month("2027-03", false, [card("ev-lv-calendar-zz-taller", "calendar", facets("calendar", "es", "inperson", "houston"))]),
    month("2028-02", true, [card("zz-acm-2028", "neta", facets("area", "en", "inperson", "dallas"))]),
    month("2028-05", true, [card("ev-gv-calendar-zz-roundup", "calendar", facets("calendar", "en", "inperson", "austin"))]),
  ];
  months[0].children[1].children[1].attrs["data-ev-cancelled"] = "";
  const li = (id, g, f, kids) => el("li", Object.assign(id ? { id } : {}, { "data-group": g, "data-cm-expire": "2030-01-01T00:00:00Z" }, f), kids);
  const committee = li("", "committee neta", Object.assign(facets("committee", "en", "online"), { "data-ev-dates": "/events/series/committee-meeting/" }), [
    el("span", { "data-ev-date-anchors": "" }, [el("span", { id: "ev-committee-2026-11-18" }), el("span", { id: "ev-committee-2026-12-16" })]),
    el("article", { class: "cm-pinned" })]);
  const booth = li("ev-series-zz-booth", "neta", facets("booth", "en", "inperson", "dallas"), [
    el("article", { class: "card cm-event" }, [el("ol", { "data-cm-max": "3" }, [
      el("li", { id: "ev-recurring-zz-booth-2026-12-12", class: "is-next" }), el("li", { id: "ev-recurring-zz-booth-2027-03-13", class: "hidden" })])])]);
  const series = el("section", { id: "ev-pinned" }, [el("div", { "data-ev-anchors": "" }, [el("span", { id: "month-2027-05" })]),
                                                      el("h2", { id: "ev-pinned-title" }), el("ul", {}, [committee, booth])]);
  const weekly = el("section", { id: "ev-weekly" }, [el("ul", {}, [
    li("", "calendar", facets("online", "es", "online"), [el("article", { class: "card cm-event" }, [el("h3", { id: "ev-weekly-lv" })])])])]);
  // "Past events": a row with its old anchor (evOldAnchors: an empty span on it)
  const past = el("details", { "data-cm-past": "" }, [el("ol", {}, [
    el("li", { id: "2026-11-07-zz-past" }, [el("span", { id: "ev-flyer-zzpast", class: "sr-only" })])])]);
  const root = el("section", { "data-count-label": "Showing {n} events", "data-count-label-one": "Showing 1 event" },
                  [el("div", { id: "ev-filters" }, chips.concat(menus))].concat(months, [series, weekly, past]));
  const p = page([root], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true, at: opts.at || "2026-11-13T18:00:00Z" });
  if (opts.hash) p.win.location.hash = opts.hash;
  if (opts.search) p.win.location.search = opts.search;
  if (opts.replace) p.win.location.replace = opts.replace;
  // the mark's timer: kept, so the test sees the mark before it goes
  const timers = [];
  p.win.setTimeout = (fn) => { timers.push(fn); return timers.length; };
  p.ready();
  const c = p.comps.cmEvents();
  c.$root = root; c.$nextTick = (fn) => fn(); c.$refs = {};
  c.init();
  const byId = (id) => p.doc.getElementById(id);
  const state = () => ({ f: Object.assign({}, c.f), group: c.group, active: c.active, months: c.anyMonth, more: c.more, text: c.countText(), moreCount: c.moreCount, neta: c.groupCount("neta"),
    counts: Object.fromEntries(chips.slice(1).map((b) => [b.attrs["data-ev-kind"], c.kindCount(b.attrs["data-ev-kind"])])),
    shown: [...root.querySelectorAll("li[data-group]")].filter((li) => c.show(li)).map(name) });
  const flashed = () => [...root.querySelectorAll(".cm-flash")].map((a) => name(a.parent));
  const hash = (h) => { p.win.location.hash = h; p.fireWin("hashchange"); };
  const reveal = (id) => p.win.dispatchEvent(new p.win.CustomEvent("cm:reveal", { detail: { id } }));
  return { p, c, root, months, byId, state, flashed, hash, reveal, timers };
}
"""

LIST_JS = DOM_JS + r"""
const res = {};
{ // the kind chips, the menus, "Clear filters", the fold and "Show 2028 dates"
  const t = setup();
  res.start = t.state();
  t.c.setKind("calendar");
  res.calendar = t.state();
  t.c.setKind("calendar");
  res.calendarAgain = t.state();
  t.c.f.lang = "es"; t.c.changed();
  res.spanish = t.state();
  t.c.setKind("committee");
  res.nothing = t.state();
  t.c.clear();
  res.cleared = t.state();
  // what Alpine re-reads: show() looks at `more` (so the fold opens on the page)
  const seen = new Set();
  const watched = new Proxy(t.c, { get(o, k, r) { seen.add(k); return Reflect.get(o, k, r); } });
  watched.show(t.byId("ev-gv-calendar-zz-roundup"));
  res.readsMore = seen.has("more");
  t.c.setKind("calendar");
  const label = el("span", { "data-label": "Show 2028 dates ({n})" });
  res.label = t.c.moreText(label);
  scrolled.length = 0; focused.length = 0;
  t.c.showMore();
  res.shown = t.state();
  res.showFocus = focused.slice();
}
{ // a link to a card the filters hide, into the fold, to a series' date, the committee meeting, a weekly meeting
  const t = setup();
  t.c.setKind("calendar");
  scrolled.length = 0; focused.length = 0;
  t.hash("#zz-workshop");
  res.toWorkshop = { state: t.state(), scrolled: scrolled.slice(), focused: focused.slice(), flashed: t.flashed(),
                     tabindex: t.byId("zz-workshop").getAttribute("tabindex") };
  t.timers.splice(0).forEach((fn) => fn());
  res.markGoes = t.flashed();
  t.c.setKind("area");
  t.hash("#zz-acm-2028");
  res.intoFold = t.state();
  t.timers.splice(0).forEach((fn) => fn());
  t.c.setKind("committee");
  scrolled.length = 0;
  t.hash("#ev-recurring-zz-booth-2027-03-13");
  res.toSeriesDate = { f: t.state().f, scrolled: scrolled.slice(), flashed: t.flashed() };
  t.timers.splice(0).forEach((fn) => fn());
  t.c.setKind("booth");
  scrolled.length = 0;
  t.reveal("ev-committee-2026-12-16");
  res.toCommittee = { f: t.state().f, scrolled: scrolled.slice() };
  t.timers.splice(0).forEach((fn) => fn());
  t.c.f.lang = "en";
  scrolled.length = 0;
  t.reveal("ev-weekly-lv");
  res.toWeekly = { f: t.state().f, scrolled: scrolled.slice() };
  t.c.clear(); t.c.f.lang = "es";
  t.reveal("ev-weekly-lv");
  res.weeklyUnderSpanish = t.state().f;
  scrolled.length = 0;
  t.reveal("nowhere");
  t.reveal("");
  res.nowhere = { f: t.state().f, scrolled: scrolled.slice() };
}
{ // a card that has passed: left alone
  const t = setup();
  t.p.clock.now = Date.parse("2026-11-29T01:00:00Z");      // the workshop of Nov 28 is over
  t.p.minute();
  t.c.setKind("calendar");
  scrolled.length = 0;
  t.hash("#zz-workshop");
  res.passed = { f: t.state().f, scrolled: scrolled.slice(), state: t.state() };
}
{ // on load: a link into a folded month opens it; the filters from the address (only what the page offers); the old
  // ?filter= chips
  // "No events match these filters" (its x-show, events.njk): not while "Show 2028 dates (n)" has a match
  const empty = (t) => new Function("c", "with (c) { return !!(" + input.emptyShow + "); }")(t.c);
  const t = setup({ hash: "#zz-acm-2028" });
  res.load = { state: t.state(), scrolled: scrolled.slice(-1) };
  res.fromAddress = setup({ search: "?kind=workshop&lang=es&city=tyler&district=99&mode=boat" }).c.f;
  res.oldCalendar = setup({ search: "?filter=calendar" }).c.f.kind;
  res.oldCommittee = setup({ search: "?filter=committee&kind=booth" }).c.f.kind;
  const n = setup({ search: "?filter=neta" });
  res.oldNeta = n.state();
  n.c.setKind("calendar");
  res.oldNetaCalendar = Object.assign(n.state(), { empty: empty(n) });
  n.c.setKind("calendar"); n.c.setKind("booth");
  res.oldNetaBooth = n.state();
  n.c.dropGroup();
  res.oldNetaDropped = n.state();
  const nc = setup({ search: "?filter=neta&lang=es" });
  res.oldNetaSpanish = nc.state();
  nc.c.clear();
  res.oldNetaCleared = nc.state();
  // (round 38b) both in the address — shared while both chips could be picked: the kind
  res.oldNetaAndKind = setup({ search: "?filter=neta&kind=calendar" }).state();
  res.oldNetaAndNoKind = setup({ search: "?filter=neta&kind=boat" }).state();
  const fo = setup(); fo.c.setKind("area");
  res.emptyFolded = { shown: fo.state().shown, moreCount: fo.c.moreCount, empty: empty(fo) };
  fo.c.setKind("committee"); fo.c.f.lang = "es";
  res.emptyNone = empty(fo);
  res.emptyAll = empty(setup());
  const u = setup({ hash: "#zz-workshop", search: "?kind=calendar" });
  res.loadHidden = u.c.active;
  // a link to a past event by its old anchor: "Past events" opens, its row is marked and scrolled to
  scrolled.length = 0; focused.length = 0;
  const pt = setup({ hash: "#ev-flyer-zzpast" });
  res.toPast = { open: !!pt.root.querySelector("details").open, marked: [...pt.root.querySelectorAll(".cm-target")].map(name),
                 scrolled: scrolled.slice(-1), focused: focused.slice(-1) };   // (after the browser's own jump to the anchor)
}
{ // (round 38) the "NETA 65 events" chip, "All", a bilingual card, an old month anchor, an old committee date link
  const t = setup();
  res.netaStart = t.state().neta;
  t.c.setGroup("neta");
  res.netaOn = t.state();
  t.c.setKind("booth");
  res.netaBooth = { shown: t.state().shown, neta: t.state().neta, group: t.state().group, kind: t.state().f.kind };
  // (round 38b) …and the NETA 65 chip after a kind: the kind goes
  t.c.setGroup("neta");
  res.kindThenNeta = { shown: t.state().shown, group: t.state().group, kind: t.state().f.kind, booth: t.state().counts.booth };
  t.c.all();
  res.afterAll = { f: t.state().f, group: t.state().group, active: t.state().active };
  t.c.setGroup("neta"); t.c.setGroup("neta");
  res.netaAgain = t.state().group;
  t.c.f.lang = "en"; t.c.changed();
  res.netaEnglish = t.c.groupCount("neta");
  t.c.clear();
  t.byId("zz-workshop").attrs["data-lang"] = "both";
  const bi = {};
  for (const v of ["en", "es", "both"]) { t.c.f.lang = v; t.c.changed(); bi[v] = t.state().shown.includes("zz-workshop"); }
  t.c.f.lang = "es"; t.c.changed();
  bi.esCount = t.c.kindCount("workshop");
  res.bilingual = bi;
  t.c.clear();
  scrolled.length = 0; focused.length = 0;
  t.hash("#month-2027-05");
  res.toOldMonth = { scrolled: scrolled.slice(), focused: focused.slice() };
  const went = [];
  setup({ hash: "#ev-committee-2026-12-16", replace: (u) => went.push(u) });
  setup({ hash: "#ev-committee-2026-11-18", replace: (u) => went.push(u) });
  const inPage = setup({ replace: (u) => went.push(u) });
  inPage.hash("#ev-committee-2026-12-16");
  res.forward = went;
}
if (input.standIn) { // (round 38b) committee.js not loaded, Alpine there: the page's stand-in for cmEvents (events.njk
  // evStandIn) — every card shows (a folded one, a cancelled one too) and every month (the fold open: `more`), its
  // first-paint rule let go (.cm-ev-ready), the filters hidden; "No events match", "Show 2028 dates" and the empty
  // states' tests answer no
  const t = setup();
  t.p.doc.documentElement.classList.remove("cm-ev-ready");
  const s = new Function("document", "return (" + input.standIn + ");")(t.p.doc);     // (the page's document)
  s.$el = t.root;
  s.init();
  const ask = (expr) => new Function("c", "with (c) { return !!(" + expr + "); }")(s);
  res.standIn = {
    cards: [...t.root.querySelectorAll("li[data-group]")].filter((li) => !s.show(li)).map(name),
    months: [...t.root.querySelectorAll("[data-cm-month]")].filter((m) => !(s.monthVisible(m) && (s.more || !m.hasAttribute("data-cm-more")))).length,
    folded: t.root.querySelectorAll("[data-cm-more]").length,
    ready: t.p.doc.documentElement.classList.contains("cm-ev-ready"), filtersHidden: t.byId("ev-filters").hidden,
    empty: ask(input.emptyShow), more: ask("!more && moreCount"), calendarsEmpty: ask("f.kind === 'calendar'"),
    netaEmpty: ask("!active || group"), anyMonth: ask("anyMonth"),
  };
}
out(res);
"""


class InTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def result(self) -> dict:
        if InTheBrowser.r is None:
            page = (Path(__file__).resolve().parents[1] / "src" / "pages" / "events.njk").read_text(encoding="utf-8")
            show = re.search(r'<div class="mt-2" data-js-only x-show="([^"]+)" x-cloak>\s*<div class="empty-state">', page)
            # (round 38b) the stand-in for cmEvents when committee.js did not load: its JavaScript, as the template
            # writes it into the list's x-data
            stand_in = re.search(r'\{%- set evStandIn = "([^"]+)" %\}', page)
            InTheBrowser.r = TCT.js(self, LIST_JS, data={"emptyShow": show.group(1), "standIn": stand_in.group(1) if stand_in else ""})
            InTheBrowser.r["usesStandIn"] = """x-data="typeof cmEvents == 'function' ? cmEvents() : {{ evStandIn }}\"""" in page
        return InTheBrowser.r

    def test_chips_menus_and_the_fold(self):
        r = self.result()
        s = r["start"]
        # each kind chip counts the cards of its kind — the folded months' too, never a cancelled one
        self.assertEqual(s["counts"], {"workshop": 1, "area": 1, "booth": 1, "online": 1, "committee": 1, "calendar": 2})
        self.assertEqual((s["active"], s["more"]), (False, False))
        # no filter: every open card (the cancelled one too, struck through — never counted); the folded months wait
        self.assertEqual(s["shown"], ["zz-workshop", "zz-off", "ev-lv-calendar-zz-taller", "committee", "ev-series-zz-booth",
                                      "online"])
        self.assertEqual(s["text"], "Showing 5 events")
        self.assertEqual(s["moreCount"], 2)
        self.assertEqual((r["calendar"]["shown"], r["calendar"]["moreCount"]), (["ev-lv-calendar-zz-taller"], 1))
        self.assertEqual(r["calendar"]["text"], "Showing 1 event")
        self.assertEqual(r["calendarAgain"]["f"]["kind"], "", "the chip picked again lets go")
        # Spanish: the Spanish cards; each chip counts its kind in Spanish
        self.assertEqual(r["spanish"]["shown"], ["zz-off", "ev-lv-calendar-zz-taller", "online"])
        self.assertEqual(r["spanish"]["counts"], {"workshop": 0, "area": 0, "booth": 0, "online": 1, "committee": 0, "calendar": 1})
        self.assertEqual((r["nothing"]["shown"], r["nothing"]["text"], r["nothing"]["active"]), ([], "Showing 0 events", True))
        # the month chips' row: there while a chip of it shows, gone with nothing to show (no icon left alone)
        self.assertEqual((s["months"], r["calendar"]["months"], r["nothing"]["months"]), (True, True, False))
        self.assertEqual((r["cleared"]["f"], r["cleared"]["active"]), ({"kind": "", "lang": "", "mode": "", "city": "", "district": ""}, False))
        self.assertTrue(r["readsMore"])
        self.assertEqual(r["label"], "Show 2028 dates (1)", "the cards the filters pick")
        # "Show 2028 dates" under GV & LV calendars: the folded cards show; the keyboard goes to May 2028's heading
        # (February has nothing of the calendars)
        self.assertEqual(r["shown"]["more"], True)
        self.assertEqual(r["shown"]["shown"], ["ev-lv-calendar-zz-taller", "ev-gv-calendar-zz-roundup"])
        self.assertEqual(r["showFocus"], [["month-2028-05", False]])

    def test_a_link_shows_its_card(self):
        r = self.result()
        t = r["toWorkshop"]
        self.assertEqual((t["state"]["f"]["kind"], t["state"]["active"]), ("", False), "the filters that hid it let go")
        self.assertEqual(t["state"]["more"], False)
        self.assertEqual(t["scrolled"], ["zz-workshop"])
        self.assertEqual(t["focused"], [["zz-workshop", True]], "focused, without a second scroll")
        self.assertEqual(t["tabindex"], "-1")
        self.assertEqual(t["flashed"], ["zz-workshop"], "its card is marked a moment")
        self.assertEqual(r["markGoes"], [])
        # into a folded month: the fold opens; the filter that shows it stays
        self.assertEqual((r["intoFold"]["f"]["kind"], r["intoFold"]["more"]), ("area", True))
        # a series' date its card does not list (or the committee meeting's): its card, the filters cleared
        self.assertEqual((r["toSeriesDate"]["f"]["kind"], r["toSeriesDate"]["scrolled"]), ("", ["ev-series-zz-booth"]))
        self.assertEqual(r["toSeriesDate"]["flashed"], ["ev-series-zz-booth"])
        self.assertEqual((r["toCommittee"]["f"]["kind"], r["toCommittee"]["scrolled"]), ("", ["committee"]))
        # the "Next 5 weeks" calendar's cm:reveal: La Viña's weekly meeting under "English" → cleared; under
        # "Spanish" it shows already
        self.assertEqual((r["toWeekly"]["f"]["lang"], r["toWeekly"]["scrolled"]), ("", ["online"]))
        self.assertEqual(r["weeklyUnderSpanish"]["lang"], "es")
        self.assertEqual((r["nowhere"]["f"]["lang"], r["nowhere"]["scrolled"]), ("es", []))

    def test_a_card_that_has_passed_is_left_alone(self):
        p = self.result()["passed"]
        self.assertEqual(p["f"]["kind"], "calendar")
        self.assertEqual(p["scrolled"], [])
        self.assertNotIn("zz-workshop", p["state"]["shown"])
        self.assertEqual(p["state"]["counts"]["workshop"], 0)

    def test_on_load(self):
        r = self.result()
        self.assertEqual((r["load"]["state"]["more"], r["load"]["state"]["active"]), (True, False))
        self.assertEqual(r["load"]["scrolled"], ["zz-acm-2028"])
        self.assertIn("zz-acm-2028", r["load"]["state"]["shown"])
        # the filters of the address, each only when the page offers it (no district menu here, no "boat")
        self.assertEqual(r["fromAddress"], {"kind": "workshop", "lang": "es", "mode": "", "city": "tyler", "district": ""})
        self.assertEqual(r["oldCalendar"], "calendar")
        self.assertEqual(r["oldCommittee"], "booth", "?kind= wins over the old ?filter=")
        # ?filter=neta: what its chip showed — ours and the committee meetings, never the calendars' or the weekly
        # meetings' —, kept in the address; the menus beside it; let go by its chip or "Clear filters"
        neta = r["oldNeta"]
        self.assertEqual((neta["group"], neta["active"], neta["f"]["kind"]), ("neta", True, ""))
        self.assertEqual(neta["shown"], ["zz-workshop", "zz-off", "committee", "ev-series-zz-booth"])
        # (round 38b) each kind chip counts what it shows once picked — the NETA 65 chip let go: the menus only
        self.assertEqual(neta["counts"], {"workshop": 1, "area": 1, "booth": 1, "online": 1, "committee": 1, "calendar": 2})
        self.assertEqual(neta["moreCount"], 1, "the 2028 ACM, folded")
        # (round 38b) a kind picked after it: the kind's cards, the NETA 65 chip let go — it showed nothing, "No
        # events match", both chips pressed
        cal = r["oldNetaCalendar"]
        self.assertEqual((cal["group"], cal["f"]["kind"], cal["shown"], cal["empty"]), ("", "calendar", ["ev-lv-calendar-zz-taller"], False))
        self.assertEqual(cal["counts"]["calendar"], 2, "the open card and the folded one")
        self.assertEqual(r["oldNetaBooth"]["shown"], ["ev-series-zz-booth"])
        # an address with both (shared while both could be picked): the kind (?kind= before ?filter=); a kind the page
        # does not offer: the NETA 65 chip
        both = r["oldNetaAndKind"]
        self.assertEqual((both["group"], both["f"]["kind"], both["shown"]), ("", "calendar", ["ev-lv-calendar-zz-taller"]))
        self.assertEqual((r["oldNetaAndNoKind"]["group"], r["oldNetaAndNoKind"]["f"]["kind"]), ("neta", ""))
        self.assertEqual((r["oldNetaDropped"]["group"], r["oldNetaDropped"]["f"]["kind"], r["oldNetaDropped"]["shown"]),
                         ("", "booth", ["ev-series-zz-booth"]))
        self.assertEqual((r["oldNetaSpanish"]["group"], r["oldNetaSpanish"]["shown"]), ("neta", ["zz-off"]))
        self.assertEqual((r["oldNetaCleared"]["group"], r["oldNetaCleared"]["active"]), ("", False))
        # "No events match": a folded card matches (Assemblies & ACMs: the 2028 ACM) — the "Show 2028 dates (1)"
        # button says so, the empty state waits; nothing anywhere — it shows; no filter — never
        self.assertEqual(r["emptyFolded"], {"shown": [], "moreCount": 1, "empty": False})
        self.assertTrue(r["emptyNone"])
        self.assertFalse(r["emptyAll"])
        self.assertFalse(r["loadHidden"], "a link to a card the address's filter hides clears it")
        # (round 38: brought in view as a card is — reveal: scrolled, then focused without a second scroll)
        self.assertEqual(r["toPast"], {"open": True, "marked": ["2026-11-07-zz-past"], "scrolled": ["2026-11-07-zz-past"],
                                       "focused": [["2026-11-07-zz-past", True]]})

    def test_round38b_without_committee_js_every_card_shows(self):
        """the stand-in for cmEvents (committee.js not loaded, Alpine there — the list was blank: every card's x-show
        asked a cmEvents that was not there): every card and month, the folded ones too; the filters hidden"""
        r = self.result()
        self.assertTrue(r["usesStandIn"], "the list's x-data: cmEvents, else the stand-in")
        st = r.get("standIn")
        self.assertIsNotNone(st, "events.njk sets evStandIn")
        self.assertGreater(st["folded"], 0, "(the page stand-in folds two months)")
        self.assertEqual((st["cards"], st["months"]), ([], 0))
        self.assertEqual((st["ready"], st["filtersHidden"]), (True, True))
        self.assertEqual((st["empty"], st["more"], st["calendarsEmpty"]), (False, False, False))
        self.assertEqual((st["netaEmpty"], st["anyMonth"]), (True, True))

    def test_round38_neta_chip_bilingual_old_links(self):
        r = self.result()
        # "NETA 65 events": ours and the committee meetings — the open ones and the folded 2028 ACM, never a calendar's
        # card or a weekly meeting, never the cancelled one
        self.assertEqual(r["netaStart"], 4)
        self.assertEqual((r["netaOn"]["group"], r["netaOn"]["active"]), ("neta", True))
        self.assertEqual(r["netaOn"]["shown"], ["zz-workshop", "zz-off", "committee", "ev-series-zz-booth"])
        # (round 38b) the kind chips count what each shows once picked: the menus only, the NETA 65 chip let go
        self.assertEqual(r["netaOn"]["counts"], {"workshop": 1, "area": 1, "booth": 1, "online": 1, "committee": 1, "calendar": 2})
        # (round 38b) the chips are one choice: a kind lets the NETA 65 chip go (its count: what it shows once picked
        # again — the menus only), the NETA 65 chip lets the kind go
        self.assertEqual(r["netaBooth"], {"shown": ["ev-series-zz-booth"], "neta": 4, "group": "", "kind": "booth"})
        self.assertEqual(r["kindThenNeta"], {"shown": ["zz-workshop", "zz-off", "committee", "ev-series-zz-booth"],
                                             "group": "neta", "kind": "", "booth": 1})
        self.assertEqual(r["afterAll"], {"f": {"kind": "", "lang": "", "mode": "", "city": "", "district": ""}, "group": "", "active": False})
        self.assertEqual(r["netaAgain"], "", "picked again: let go")
        self.assertEqual(r["netaEnglish"], 4)
        # a bilingual card shows under English, Spanish and "Bilingual"; counted under Spanish (the Spanish workshop is cancelled)
        self.assertEqual(r["bilingual"], {"en": True, "es": True, "both": True, "esCount": 1})
        # an old month's anchor on "Every month": that section's heading
        self.assertEqual(r["toOldMonth"], {"scrolled": ["ev-pinned-title"], "focused": [["ev-pinned-title", True]]})
        # an old link to a committee meeting's later date goes on to its dates page; the date the card shows and a link
        # inside the page stay
        self.assertEqual(r["forward"], ["/events/series/committee-meeting/#ev-committee-2026-12-16"])


# (round 38) the committee meeting's dates page: committee.js datesSettle, on the page stand-in — its timers kept (with
# their delays) and run by the test, the clock moved by hand
SETTLE_JS = r"""
const scrolled = [];
El.prototype.scrollIntoView = function () { scrolled.push(this.attrs.id); };
function setup(withList) {
  const dates = ["2027-01-20", "2027-06-16", "2028-12-20"].map((d) => el("li", { id: "ev-committee-" + d }, [el("article", { class: "card cm-event" })]));
  const list = el("section", Object.assign({ id: "evp-all-dates", class: "mt-8 cm-cv-all" }, withList ? { "data-cm-cv-settle": "" } : {}), [el("ol", {}, dates)]);
  const other = el("div", { id: "subscribe" });
  const p = page([list, other], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], at: "2026-11-26T18:00:00Z" });
  const timers = [];
  p.win.setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
  p.win.clearTimeout = (n) => { if (timers[n - 1]) timers[n - 1].fn = null; };
  const run = () => { const t = timers.filter((x) => x.fn).map((x) => ({ fn: x.fn, ms: x.ms })); timers.forEach((x) => { x.fn = null; });
    t.forEach((x) => x.fn()); return t.map((x) => x.ms); };
  const on = () => list.classList.contains("cm-cv-all");
  const hash = (h) => { p.win.location.hash = h; p.fireWin("hashchange"); };
  return { p, list, timers, run, on, hash };
}
const res = {};
{
  const s = setup(true);
  s.p.ready();
  res.atReady = { on: s.on(), waiting: s.run() };            // nothing waits before the page has loaded
  s.p.fireWin("load");
  res.atLoad = s.on();
  s.p.clock.now += 1900; s.p.fireWin("scroll");             // the browser's smooth jump still running at 2 s
  s.p.clock.now += 100;
  res.whileScrolling = { waited: s.run(), on: s.on() };
  s.p.clock.now += 300;
  res.afterScroll = { waited: s.run(), on: s.on() };
  s.hash("#ev-committee-2028-12-20");
  res.hashed = { on: s.on(), scrolled: scrolled.slice() };
  s.p.clock.now += 1500;
  res.hashedLater = { waited: s.run(), on: s.on() };
  s.hash("#subscribe");
  res.elsewhere = { on: s.on(), scrolled: scrolled.length, waiting: s.run() };
}
{
  const s = setup(false);
  s.p.ready(); s.p.fireWin("load"); s.p.clock.now += 5000;
  res.noList = { waiting: s.run(), on: s.on() };
}
out(res);
"""


class DatesPageSettle(unittest.TestCase):
    """(round 38) The committee meeting's dates page draws every card for its landing only (committee.js datesSettle)"""

    def test_the_page_comes_with_every_card_drawn(self):
        page = (ROOT / "src" / "pages" / "events-committee.njk").read_text(encoding="utf-8")
        tag = re.search(r'<section id="evp-all-dates"[^>]*>', page)
        self.assertIsNotNone(tag)
        self.assertIn('class="mt-8 cm-cv-all"', tag.group(0), "every card drawn from the first paint (no JavaScript too)")
        self.assertIn("data-cm-cv-settle", tag.group(0))
        css = (ROOT / "src" / "assets" / "css" / "areas" / "committee.css").read_text(encoding="utf-8")
        self.assertIn(".cm-cv-all .cm-event { content-visibility: visible; }", css)

    def test_at_150_percent_on_tablets_the_flyer_tile_steps_aside(self):
        """(round 38) at 150 % on 640–767px the dates page's cards leave out the flyer tile (beside it and the date tile
        the words broke in two: "representatives", "hispanohablantes") — unlayered, after the tile's own rules, and only
        on this page; each card keeps its "View flyer" button (what the browser draws: tests/browser/
        test_r38_large_text.py CommitteeDates)"""
        css = (ROOT / "src" / "assets" / "css" / "areas" / "committee.css").read_text(encoding="utf-8")
        rule = ('@media (40rem <= width < 48rem) { :root:where(.gv-prefs)[data-text="150"] #evp-all-dates .cm-flyer-thumb '
                '{ display: none; } }')
        self.assertIn(rule, css)
        self.assertGreater(css.index(rule), css.rindex("@layer"), "unlayered: it wins over the tile's display: block")
        page = (ROOT / "src" / "pages" / "events-committee.njk").read_text(encoding="utf-8")
        self.assertIn("{{ ui.flyerButton(ev.flyer,", page)

    def test_the_class_goes_once_the_landing_has_settled(self):
        r = TCT.js(self, SETTLE_JS)
        self.assertEqual(r["atReady"], {"on": True, "waiting": []})
        self.assertTrue(r["atLoad"])
        # 2 s after load, a scroll 100 ms before: 300 ms more; then the class goes
        self.assertEqual(r["whileScrolling"], {"waited": [2000], "on": True})
        self.assertEqual(r["afterScroll"], {"waited": [300], "on": False})
        # a later #hash to a date: every card drawn again, the date brought into view, the class gone 1.5 s later
        self.assertEqual(r["hashed"], {"on": True, "scrolled": ["ev-committee-2028-12-20"]})
        self.assertEqual(r["hashedLater"], {"waited": [1500], "on": False})
        # a #hash outside the list: left alone
        self.assertEqual(r["elsewhere"], {"on": False, "scrolled": 1, "waiting": []})
        # another page (no data-cm-cv-settle): nothing waits, its class (if any) stays
        self.assertEqual(r["noList"], {"waiting": [], "on": True})


if __name__ == "__main__":
    unittest.main()
