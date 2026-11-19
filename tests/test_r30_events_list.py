"""Round 30, Unit B — the /events/ agenda: every date a card of its own, the filters that really filter, our two
monthly meetings pinned on top, all of the next year shown and the year after it behind "Show more".

  * The fold (eleventy/filters/committee.js EVENTS_NEXT_YEAR_FROM = 11, eventsFoldFrom, eventsFold — the
    cmEventsFold filter), by whole years: the rest of the build's year in Central time is open and, from November on,
    all of the next year too — on November 13, 2026: November 2026 … December 2027, all of 2027 —; the first folded
    month is January of the year after ("2028-01" through October 31, 2027, Central midnight, not UTC's; "2029-01"
    from November 1, 2027); the folded months' keys, their events' number and the button's words: their year
    ("2028"), or the first and last year when they run into another one ("2028 – 2029").
  * The page (src/pages/events.njk, built with Eleventy, English and Spanish, ONLY that page, on November 13, 2026,
    with events of the test's own through December 2028 — real data lists dates only to November 2027 — and the
    settings of round 20's tests: the committee meeting and the Grapevine Meeting on Google Meet):
      - no "Show every monthly date" switch, no "Then …" line, no data-later: every date of a monthly series is a
        card; no card is hidden from the first paint (no data-dflt-hidden on an li);
      - a committee meeting's card is in two groups, data-group="committee neta"; the chips count every card of
        theirs (the folded months' too): Committee meetings = the committee cards, NETA 65 events = ours + the
        committee meetings, GV & LV calendars = theirs;
      - the months: through December 2027 open; every 2028 month's section and jump chip carry data-cm-more and
        data-dflt-hidden, its heading tabindex="-1"; one "Show 2028 dates (n)" button (data-js-only, n = the folded
        cards), right after the last open month, its words for the browser in data-label ("{n}");
      - "Our monthly meetings" (#ev-pinned) right after the filter bar and before the weekly open meetings: no
        x-show, no data-group; the committee meeting's dark card first, then the Grapevine Meeting's (#ev-next-gvm);
      - the Area's events (an assembly, an ACM) in one colour, "Area event" in the colour key and on an ACM's badge,
        "Area assembly" on an assembly's; the grey kind is "NETA 65" while every grey card is ours, "Other events"
        when an outside calendar's event is grey too; "Save the date" picks the next ASSEMBLY, never the ACM before it;
      - no id twice on the page.
  * The list in the browser (src/assets/js/committee.js cmEvents, on the page stand-in of tests/test_central_time.py):
    the chips count the committee meetings under NETA 65 events; "All" shows every open card, committee meetings
    included; "Showing N events" leaves the folded months out until they show; "Show 2028 dates" counts the folded
    cards of the chip picked, shows them and moves the keyboard to the first folded month that shows something for
    that chip; a link to a card — a hashchange, or the "Next 5 weeks" calendar's window "cm:reveal" { id } — under a
    chip that hides it sets the chip back to All, into a folded month opens the fold, to a weekly open meeting under
    "Committee meetings" sets All, to the pinned Grapevine Meeting changes nothing; then the target is scrolled to,
    focused (tabindex="-1", no second scroll) and its card marked a moment (.cm-flash); a card that has passed is left
    alone; on load a link into a folded month opens it.

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
    def test_every_date_is_a_card_and_no_switch(self):
        for url in ("/events/", "/es/events/"):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                for gone in ("cm-switch", "showAll", "data-later", "data-committee", "moreDates"):
                    self.assertNotIn(gone, page)
                anchors = [a for a, _ in cards(page)]
                # every booth date to come, a card each (25: December 2026 … December 2028)
                self.assertEqual(len([a for a in anchors if a.startswith("ev-recurring-zz-booth-")]), 25)
                self.assertNotRegex(page, r'<li id="[^"]+" data-group="[^"]+"[^>]*data-dflt-hidden')
                # (the past workshop is in "Past events", not a card of the months)
                self.assertNotIn("zz-held", anchors)
                self.assertIn('<li id="zz-held" class="flex', page)

    def test_the_committee_meetings_are_neta_65_events_too(self):
        for url in ("/events/", "/es/events/"):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                groups = dict(cards(page))
                committee = [a for a in groups if a.startswith("ev-committee-")]
                self.assertGreaterEqual(len(committee), 12)
                self.assertEqual({groups[a] for a in committee}, {"committee neta"})
                self.assertEqual({g for a, g in groups.items() if a not in committee}, {"neta", "calendar"})
                count = Counter(g for g in " ".join(groups.values()).split())
                chips = dict(re.findall(r'data-cm-filter="(\w+)"[^>]*>.*?(?:<span class="cm-chip-count">(\d+)</span>)?\s*</button>',
                                        page, re.S))
                self.assertEqual(chips["committee"], str(len(committee)))
                self.assertEqual(chips["neta"], str(count["neta"]), "ours + the committee meetings, 2028 included")
                self.assertEqual(chips["calendar"], str(count["calendar"]))
                self.assertEqual(chips["all"], "")

    def test_all_of_2027_open_2028_folded_behind_one_button(self):
        for url, words in (("/events/", "Show 2028 dates ({n})"), ("/es/events/", "Mostrar las fechas de 2028 ({n})")):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                ms = months(page)
                keys = [k for k, _ in ms]
                self.assertEqual(keys[0], "2026-11")
                self.assertIn("2027-12", keys)
                self.assertEqual(keys[-1], "2028-12")
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
                # one button, right after December 2027 and before January 2028; it says how many dates it shows
                self.assertEqual(page.count('class="cm-ev-more"'), 1)
                at = page.index('class="cm-ev-more"')
                self.assertLess(page.index('x-ref="m2027-12"'), at)
                self.assertLess(at, page.index('x-ref="m2028-01"'))
                button = page[at:page.index("</div>", at)]
                self.assertIn('data-js-only x-show="!more && moreCount"', button)
                self.assertIn('@click="showMore()"', button)
                self.assertIn("#i-chevron-down", button)
                folded = 0
                for key, _ in ms:
                    if key >= "2028-01":
                        sec = section_of(page, f'<section class="cm-month" data-cm-month x-ref="m{key}"')
                        folded += len(re.findall(r'<li id="[^"]+" data-group=', sec))
                # 12 booth dates, the ACM, the assembly, the roundup (and the 2028 committee meetings once the settings
                # list dates that far: config/site.yml events_until)
                self.assertGreaterEqual(folded, 15)
                self.assertIn(f'data-label="{html.escape(words, quote=True)}"', button)
                self.assertIn(">" + words.replace("{n}", str(folded)) + "</span>", button)

    def test_our_monthly_meetings_are_pinned_on_top(self):
        for url, lang in (("/events/", "en"), ("/es/events/", "es")):
            page = pages(self)["main"][url]
            with self.subTest(url=url):
                self.assertEqual(page.count('id="ev-pinned"'), 1)
                pinned = section_of(page, '<section id="ev-pinned"')
                self.assertTrue(pinned.startswith('<section id="ev-pinned" class="mb-10" aria-labelledby="ev-pinned-title">'))
                self.assertIn(T["committee.events.pinned_title"][lang], text(pinned))
                self.assertIn(T["committee.events.pinned_text"][lang], text(pinned))
                self.assertIn("#i-pin", pinned)
                for never in ("x-show=\"filter", "data-group", "data-cm-expire", "data-dflt-hidden"):
                    self.assertNotIn(never, pinned)
                # after the filter bar and the colour key, before the weekly open meetings and the months
                self.assertLess(page.index('class="ev-legend"'), page.index('id="ev-pinned"'))
                self.assertLess(page.index('id="ev-pinned"'), page.index('<section id="ev-weekly"'))
                self.assertLess(page.index('<section id="ev-weekly"'), page.index('class="cm-month"'))
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
                self.assertIn('href="#zz-spring-assembly"', page)
                self.assertNotIn('href="#zz-winter-acm"', page)
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
# The agenda in miniature: the chips, the pinned section (the Grapevine Meeting), the weekly open meetings, two open
# months and two folded ones — the card ids name their groups and month.
DOM_JS = r"""
const scrolled = [], focused = [];
El.prototype.scrollIntoView = function () { scrolled.push(this.attrs.id || this.tagName); };
El.prototype.focus = function (o) { focused.push([this.attrs.id || this.tagName, !!(o && o.preventScroll)]); };
const chip = (f) => el("button", { "data-cm-filter": f }, f === "all" ? [] : [el("span", { class: "cm-chip-count" }, [], "0")]);
const card = (id, g, end) => el("li", { id, "data-group": g, "data-cm-expire": end || "2030-01-01T00:00:00Z" },
                                [el("article", { class: "card cm-event" })]);
const month = (key, more, kids) => el("section", Object.assign({ class: "cm-month", "data-cm-month": "" }, more ? { "data-cm-more": "" } : {}),
                                      [el("h2", Object.assign({ id: "month-" + key }, more ? { tabindex: "-1" } : {})), el("ol", {}, kids)]);
function setup(opts) {
  opts = opts || {};
  const chips = ["all", "committee", "neta", "calendar"].map(chip);
  const pinned = el("section", { id: "ev-pinned" }, [el("article", { id: "ev-next-gvm", class: "card" }, [el("h3", { id: "ev-next-gvm-title" })])]);
  const weekly = el("section", { id: "ev-weekly" }, [el("article", { class: "card" }, [el("h3", { id: "ev-weekly-gv" })])]);
  const months = [
    month("2026-11", false, [card("ev-committee-2026-11-18", "committee neta", "2026-11-19T02:00:00Z"), card("zz-workshop", "neta")]),
    month("2027-03", false, [card("ev-lv-calendar-zz-taller", "calendar")]),
    month("2028-01", true, [card("ev-committee-2028-01-19", "committee neta"), card("ev-recurring-zz-booth-2028-01-08", "neta")]),
    month("2028-05", true, [card("ev-gv-calendar-zz-roundup", "calendar")]),
  ];
  const root = el("section", { "data-count-label": "Showing {n} events", "data-count-label-one": "Showing 1 event" },
                  [el("div", {}, chips), pinned, weekly].concat(months));
  const p = page([root], { files: ["time", "src/assets/js/app.js", "src/assets/js/committee.js"], alpine: true, at: opts.at || "2026-11-13T18:00:00Z" });
  if (opts.hash) p.win.location.hash = opts.hash;
  if (opts.search) p.win.location.search = opts.search;
  // the mark's timer: kept, so the test sees the mark before it goes
  const timers = [];
  p.win.setTimeout = (fn) => { timers.push(fn); return timers.length; };
  p.ready();
  const c = p.comps.cmEvents();
  c.$root = root; c.$nextTick = (fn) => fn(); c.$refs = {};
  c.init();
  const byId = (id) => p.doc.getElementById(id);
  const state = () => ({ filter: c.filter, more: c.more, text: c.countText(), moreCount: c.moreCount,
    counts: chips.slice(1).map((b) => b.querySelector(".cm-chip-count").textContent),
    shown: [...root.querySelectorAll("li[data-group]")].filter((li) => c.show(li)).map((li) => li.attrs.id) });
  const flashed = () => [...root.querySelectorAll(".cm-flash")].map((a) => a.parent.attrs.id || a.parent.tagName);
  const hash = (h) => { p.win.location.hash = h; p.fireWin("hashchange"); };
  const reveal = (id) => p.win.dispatchEvent(new p.win.CustomEvent("cm:reveal", { detail: { id } }));
  return { p, c, root, months, byId, state, flashed, hash, reveal, timers };
}
"""

LIST_JS = DOM_JS + r"""
const res = {};
{ // the chips, "All", the fold and "Show 2028 dates"
  const t = setup();
  res.start = t.state();
  t.c.set("committee");
  res.committee = t.state();
  t.c.set("calendar");
  res.calendar = t.state();
  // what Alpine re-reads: show() looks at `more` (so the fold opens on the page)
  const seen = new Set();
  const watched = new Proxy(t.c, { get(o, k, r) { seen.add(k); return Reflect.get(o, k, r); } });
  watched.show(t.byId("ev-gv-calendar-zz-roundup"));
  res.readsMore = seen.has("more");
  const label = el("span", { "data-label": "Show 2028 dates ({n})" });
  res.label = t.c.moreText(label);
  scrolled.length = 0; focused.length = 0;
  t.c.showMore();
  res.shown = t.state();
  res.showFocus = focused.slice();
}
{ // a link to a card the chip hides, into the fold, to the weekly meetings and the pinned card
  const t = setup();
  t.c.set("calendar");
  scrolled.length = 0; focused.length = 0;
  t.hash("#ev-committee-2026-11-18");
  res.toCommittee = { state: t.state(), scrolled: scrolled.slice(), focused: focused.slice(), flashed: t.flashed(),
                      tabindex: t.byId("ev-committee-2026-11-18").getAttribute("tabindex") };
  t.timers.splice(0).forEach((fn) => fn());
  res.markGoes = t.flashed();
  t.c.set("neta");
  t.hash("#ev-gv-calendar-zz-roundup");
  res.intoFold = t.state();
  t.timers.splice(0).forEach((fn) => fn());
  t.c.set("committee");
  scrolled.length = 0; focused.length = 0;
  t.reveal("ev-weekly-gv");
  res.toWeekly = { filter: t.c.filter, scrolled: scrolled.slice(), flashed: t.flashed(), tabindex: t.byId("ev-weekly-gv").getAttribute("tabindex") };
  t.c.set("calendar");
  t.reveal("ev-weekly-gv");
  res.weeklyUnderCalendar = t.c.filter;
  t.timers.splice(0).forEach((fn) => fn());
  t.c.set("neta");
  scrolled.length = 0;
  t.reveal("ev-next-gvm");
  res.toPinned = { filter: t.c.filter, scrolled: scrolled.slice(), flashed: t.flashed().length > 0 };
  scrolled.length = 0;
  t.reveal("nowhere");
  t.reveal("");
  res.nothing = { filter: t.c.filter, scrolled: scrolled.slice() };
}
{ // a card that has passed: left alone
  const t = setup();
  t.p.clock.now = Date.parse("2026-11-19T03:00:00Z");      // the committee meeting of Nov 18 is over
  t.p.minute();
  t.c.set("calendar");
  scrolled.length = 0;
  t.hash("#ev-committee-2026-11-18");
  res.passed = { filter: t.c.filter, scrolled: scrolled.slice(), state: t.state() };
}
{ // on load: a link into a folded month opens it; ?filter= and a card it hides: All
  const t = setup({ hash: "#ev-recurring-zz-booth-2028-01-08" });
  res.load = { state: t.state(), scrolled: scrolled.slice(-1) };
  const u = setup({ hash: "#ev-committee-2026-11-18", search: "?filter=calendar" });
  res.loadFilter = u.c.filter;
  const v = setup({ search: "?filter=committee" });
  res.loadOnlyFilter = { filter: v.c.filter, more: v.c.more };
}
out(res);
"""


class InTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def result(self) -> dict:
        if InTheBrowser.r is None:
            InTheBrowser.r = TCT.js(self, LIST_JS)
        return InTheBrowser.r

    def test_chips_all_and_the_fold(self):
        r = self.result()
        s = r["start"]
        # the committee meetings count under NETA 65 events too; the folded months' cards are counted
        self.assertEqual(s["counts"], ["2", "4", "2"])
        self.assertEqual((s["filter"], s["more"]), ("all", False))
        # "All": every open card, the committee meeting's too; the folded months wait for the button
        self.assertEqual(s["shown"], ["ev-committee-2026-11-18", "zz-workshop", "ev-lv-calendar-zz-taller"])
        self.assertEqual(s["text"], "Showing 3 events")
        self.assertEqual(s["moreCount"], 3)
        self.assertEqual((r["committee"]["shown"], r["committee"]["moreCount"]), (["ev-committee-2026-11-18"], 1))
        self.assertEqual(r["committee"]["text"], "Showing 1 event")
        self.assertEqual((r["calendar"]["shown"], r["calendar"]["moreCount"]), (["ev-lv-calendar-zz-taller"], 1))
        self.assertTrue(r["readsMore"])
        self.assertEqual(r["label"], "Show 2028 dates (1)", "the chip picked's count")
        # "Show 2028 dates" under GV & LV calendars: the folded cards show; the keyboard goes to May 2028's heading
        # (January has nothing of the calendars)
        self.assertEqual(r["shown"]["more"], True)
        self.assertEqual(r["shown"]["shown"], ["ev-lv-calendar-zz-taller", "ev-gv-calendar-zz-roundup"])
        self.assertEqual(r["shown"]["text"], "Showing 2 events")
        self.assertEqual(r["showFocus"], [["month-2028-05", False]])

    def test_a_link_shows_its_card(self):
        r = self.result()
        t = r["toCommittee"]
        self.assertEqual(t["state"]["filter"], "all", "the chip that hid it lets go")
        self.assertEqual(t["state"]["more"], False)
        self.assertEqual(t["scrolled"], ["ev-committee-2026-11-18"])
        self.assertEqual(t["focused"], [["ev-committee-2026-11-18", True]], "focused, without a second scroll")
        self.assertEqual(t["tabindex"], "-1")
        self.assertEqual(t["flashed"], ["ev-committee-2026-11-18"], "its card is marked a moment")
        self.assertEqual(r["markGoes"], [])
        # into a folded month: the fold opens; the chip that shows it stays
        self.assertEqual((r["intoFold"]["filter"], r["intoFold"]["more"]), ("all", True))
        # the "Next 5 weeks" calendar's cm:reveal: a weekly open meeting under "Committee meetings" → All
        self.assertEqual(r["toWeekly"]["filter"], "all")
        self.assertEqual(r["toWeekly"]["scrolled"], ["ev-weekly-gv"])
        self.assertEqual(r["toWeekly"]["tabindex"], "-1")
        self.assertEqual(r["toWeekly"]["flashed"], ["ev-weekly"], "its card (the article around the heading)")
        self.assertEqual(r["weeklyUnderCalendar"], "calendar", "shown there already")
        # the pinned Grapevine Meeting: always shown, the chip stays
        self.assertEqual(r["toPinned"], {"filter": "neta", "scrolled": ["ev-next-gvm"], "flashed": True})
        # an id that is not in the list: nothing
        self.assertEqual(r["nothing"], {"filter": "neta", "scrolled": []})

    def test_a_card_that_has_passed_is_left_alone(self):
        p = self.result()["passed"]
        self.assertEqual(p["filter"], "calendar")
        self.assertEqual(p["scrolled"], [])
        self.assertNotIn("ev-committee-2026-11-18", p["state"]["shown"])
        self.assertEqual(p["state"]["counts"], ["1", "3", "2"])

    def test_on_load(self):
        r = self.result()
        self.assertEqual((r["load"]["state"]["more"], r["load"]["state"]["filter"]), (True, "all"))
        self.assertEqual(r["load"]["scrolled"], ["ev-recurring-zz-booth-2028-01-08"])
        self.assertIn("ev-recurring-zz-booth-2028-01-08", r["load"]["state"]["shown"])
        self.assertEqual(r["loadFilter"], "all", "a link to a card the ?filter= hides")
        self.assertEqual(r["loadOnlyFilter"], {"filter": "committee", "more": False})


if __name__ == "__main__":
    unittest.main()
