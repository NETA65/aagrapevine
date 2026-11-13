"""Round 30 — the home page's hero holds our two monthly meetings: the next committee meeting (as before) and, under
it, the next Grapevine Meeting (src/pages/index.njk gvmCard, src/assets/js/home.js homeMeeting, src/assets/css/areas/
home.css, eleventy/filters/home.js homeEvents):

  * the built home page (English and Spanish), at a fixed clock, on settings of the test's own (round 20's: the
    committee meeting and the Grapevine Meeting in one Google Meet room, its first date `starts: 2026-12-02`):
    - Nov 26, 2026: the hero's right column holds the committee meeting's card FIRST, then the Grapevine Meeting's;
      below the hero (phones and tablets) the same two, in that order. The Grapevine Meeting's cards say "Wednesday,
      December 2" / "Miércoles, 2 de diciembre" and "First meeting" / "Primera reunión", join the meeting's room
      (the Join button's accessible name names the meeting: both meetings use the same room), and "Details" goes to
      its section, /meetings/#grapevine-meeting (/es/meetings/#grapevine-meeting) — never with the committee card's
      home-meet-more class or a data-cal-url (those are the committee meeting's); on /es/ it says it is in English;
      data-rule carries the series' first date (`starts`), data-first the same day; no countdown tiles, no Add to
      calendar; every id on the page is used once;
    - Dec 17, 2026: January 6 / 6 de enero, "First meeting" waiting for the browser (x-cloak); the committee card's
      guest speaker's topic keeps to one line in the hero (two below it);
    - the Upcoming events row leaves the Grapevine Meeting out (the hero has it) and lists the other events;
  * the browser's roll-on (homeMeeting with data-first): Dec 2 is "First meeting" (and "live" during the meeting),
    then January 6 without it; a card without data-first (the committee meeting's) is never "first";
  * homeEvents' 4th argument (the hero's series): none of that series' dates in the row, its place going to another
    event; without it the row is as before (each series of ours keeps a place for its next date).

    python -m unittest tests.test_r30_home -v      (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import html
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from nodejs import run_js  # noqa: E402
from test_central_time import DOM, plain  # noqa: E402  (the browser stand-in: page(), el())
from test_r20_meeting import GVM_ENTRY, ROOM, YAML, Untranslated, ctx_with  # noqa: E402  (round 20's settings)
from scripts.sync import build_data as B  # noqa: E402

NOV26 = "2026-11-26T18:00:00Z"       # the Grapevine Meeting's first date (Dec 2) is next
DEC17 = "2026-12-17T18:00:00Z"       # Dec 2 is over: January 6 is next (and the committee meeting's Jan 20 has a speaker)

# A one-off event of ours on Saturday, December 5, 2026 (10 AM – noon Central): the row's other event
WORKSHOP = {
    "id": "ev:manual:2026-12-05-gv-writing-workshop-tyler", "source": "committee", "kind": "event",
    "url": "/events/#2026-12-05-gv-writing-workshop-tyler", "title": "Grapevine Writing Workshop — Tyler", "summary": "",
    "lang": "en", "date": "2026-12-05T16:00:00Z", "first_seen": "2026-11-01T12:00:00Z", "image": None, "tags": ["workshop"],
    "category": "manual", "status": "ok",
    "extra": {"start": "2026-12-05T16:00:00Z", "end": "2026-12-05T18:00:00Z", "all_day": False,
              "location": "Tyler Civic Center, 300 Rose Park Dr, Tyler, TX 75702", "online_url": None, "city": "Tyler", "state": "TX"},
    "i18n": {"title": {"en": "Grapevine Writing Workshop — Tyler", "es": "Taller de Escritura de Grapevine — Tyler"},
             "summary": {"en": "", "es": ""}},
    "machine": [], "is_new": False,
}

# Eleventy with the site's config, ONLY the home page, these settings (`site.meeting`, `site.recurring_events`, the
# `meeting` global — src/_data/meeting.js on the same settings) and these events (events.json's)
PAGES_JS = r"""
process.env.ONLY = "index.njk";
process.env.PATH_PREFIX = "/";
const os = await import("node:os");
const yaml = await import("js-yaml");
const { Eleventy } = await import("@11ty/eleventy");
const meetingData = (await imp("src/_data/meeting.js")).default;
const cfg = yaml.load(input.yaml);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r30-home-"));
fs.mkdirSync(path.join(tmp, "config"));
fs.writeFileSync(path.join(tmp, "config", "site.yml"), input.yaml);
const here = process.cwd();
process.chdir(tmp);
let meeting;
try { meeting = meetingData(); } finally { process.chdir(here); fs.rmSync(tmp, { recursive: true, force: true }); }
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r30-home-site-"));
try {
  const elev = new Eleventy("src", dir, {
    quietMode: true, configPath: "eleventy.config.js",
    config(c) {
      // (every key of config/site.yml's own meeting that these settings leave out is set to nothing)
      const none = (o) => Object.fromEntries(Object.keys(o || {}).map((k) => [k, null]));
      c.addGlobalData("eleventyComputed", {
        db: (data) => ({ ...data.db, events: { updated: null, items: input.items } }),
        site: (data) => ({ ...data.site, meeting: { ...none(data.site.meeting), ...cfg.meeting }, recurring_events: cfg.recurring_events }),
        meeting: (data) => ({ ...meeting, next: meeting.next && { ...none(data.meeting && data.meeting.next), ...meeting.next } }),
      });
    },
  });
  const pages = await elev.toJSON();
  out(Object.fromEntries(pages.filter((p) => p.url === "/" || p.url === "/es/").map((p) => [p.url, p.content])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""


def part(page: str, start: str, end: str) -> str:
    i = page.index(start)
    return page[i:page.index(end, i + 1)]


def text(fragment: str) -> str:
    """The words of an HTML fragment (no tags, single spaces)."""
    t = re.sub(r"<script.*?</script>|<svg.*?</svg>", " ", fragment, flags=re.S)
    return plain(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))).strip()


def opening_tag(page: str, needle: str) -> str:
    """The whole start tag that holds `needle`."""
    i = page.index(needle)
    return page[page.rindex("<", 0, i):page.index(">", i) + 1]


def gvm_cards(page: str) -> dict:
    """The Grapevine Meeting's two cards: {"hero": …, "page": …} (each from its opening tag to its actions' end)."""
    out = {}
    for v in ("hero", "page"):
        i = page.index(f'<div class="home-gvm home-gvm--{v}"')
        j = page.index('class="home-gvm-actions"', i)
        out[v] = page[i:page.index("</div>", j) + 6]
    return out


class BuiltHome(Untranslated):
    built: dict = {}

    def pages(self, at: str) -> dict:
        if at not in BuiltHome.built:
            items = B.recurring_events(ctx_with()) + [WORKSHOP]
            BuiltHome.built[at] = run_js(self, PAGES_JS, data={"yaml": YAML, "items": items}, timeout=900, now=at)
        return BuiltHome.built[at]

    def test_the_hero_holds_both_meetings_the_committees_first(self):
        for url in ("/", "/es/"):
            page = self.pages(NOV26)[url]
            hero = part(page, 'id="homeHero"', "</section>")
            with self.subTest(url=url):
                aside = hero[hero.index('<div class="gv-hero-aside">'):]
                self.assertIn('<div class="home-meets">', aside)
                committee = aside.index('<div class="home-meet home-meet--hero"')
                gvm = aside.index('<div class="home-gvm home-gvm--hero"')
                self.assertLess(aside.index('<div class="home-meets">'), committee)
                self.assertLess(committee, gvm, "the committee meeting's card comes first")
                # the committee meeting's card is still the page's first .home-meet--hero (other tests slice from it)
                self.assertGreater(page.index('<div class="home-meet home-meet--hero"'), page.index('<div class="gv-hero-aside">'))
                # below the hero: the same two, in that order, then the counters
                under = part(page, '<div class="card home-under-card', '<div class="home-under-stats">')
                self.assertLess(under.index('<div class="home-under-meet lg:hidden">'), under.index('<div class="home-under-gvm lg:hidden">'))
                self.assertRegex(under, r'<div class="home-under-gvm lg:hidden">\s*<div class="home-gvm home-gvm--page"')
                self.assertNotIn("max-sm:hidden", opening_tag(page, '<div class="card home-under-card'))

    def test_the_first_grapevine_meeting(self):
        for url, date, first, pre in (("/", "Wednesday, December 2", "First meeting", ""),
                                      ("/es/", "Miércoles, 2 de diciembre", "Primera reunión", "/es")):
            page = self.pages(NOV26)[url]
            for v, card in gvm_cards(page).items():
                with self.subTest(url=url, card=v):
                    tag = opening_tag(card, 'x-data="homeMeeting"')
                    self.assertIn(f'aria-labelledby="{"home-gvm-title" if v == "hero" else "home-gvm-title-2"}"', tag)
                    rule = json.loads(html.unescape(re.search(r'data-rule="([^"]*)"', tag).group(1)))
                    self.assertEqual(rule, {"weekday": 3, "n": 1, "start": "19:00", "end": "20:00", "skip": [], "starts": "2026-12-02"})
                    self.assertIn('data-first="2026-12-02"', tag)
                    self.assertIn('data-start="2026-12-03T01:00:00.000Z"', tag)
                    self.assertIn('data-end="2026-12-03T02:00:00.000Z"', tag)
                    words = text(card)
                    self.assertIn(date, words)
                    self.assertIn("7:00", words)
                    # "First meeting" shown from the first paint (no x-cloak) on its first date
                    self.assertNotIn("x-cloak", opening_tag(card, f">{first}<"))
                    self.assertIn(first, words)
                    # Join: the meeting's room, its accessible name names the meeting; Details: its section
                    join = re.search(r'<a class="[^"]*home-gvm-join" href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
                    self.assertEqual(join.group(1), ROOM)
                    self.assertIn("Grapevine Meeting" if url == "/" else "Reunión de Grapevine (en inglés)", text(join.group(2)))
                    self.assertIn("Google Meet", text(join.group(2)))
                    self.assertEqual(re.findall(r'<a class="[^"]*home-gvm-more" href="([^"]+)"', card), [pre + "/meetings/#grapevine-meeting"])
                    # never the committee meeting's hooks; no countdown tiles, no Add to calendar
                    for s in ("home-meet-more", "data-cal-url", "home-meet-count", "addToCalendar", "data-cm-expire"):
                        self.assertNotIn(s, card)
                    # the meeting is held in English: /es/ says so
                    self.assertEqual("En inglés" in words, url == "/es/")
                    self.assertNotIn("In English", words)

    def test_the_next_one_after_the_first(self):
        p = self.pages(DEC17)
        for url, date, first in (("/", "Wednesday, January 6", "First meeting"), ("/es/", "Miércoles, 6 de enero", "Primera reunión")):
            for v, card in gvm_cards(p[url]).items():
                with self.subTest(url=url, card=v):
                    self.assertIn(date, text(card))
                    self.assertIn('data-start="2027-01-07T01:00:00.000Z"', card)
                    self.assertIn("x-cloak", opening_tag(card, f">{first}<"), "the browser shows it only on the first date")
        # the committee card's guest speaker (Jan 20): the topic keeps to one line in the hero, two below it
        page = p["/"]
        hero = part(page, '<div class="home-meet home-meet--hero"', 'class="home-meet-count"')
        below = part(page, '<div class="home-meet home-meet--page"', 'class="home-meet-count"')
        self.assertIn('<span class="line-clamp-1" x-show="speaker && speaker.topic"', hero)
        self.assertIn('<span class="line-clamp-2" x-show="speaker && speaker.topic"', below)
        self.assertIn("Guest speaker: Ann B.", text(hero))

    def test_every_id_once(self):
        for at in (NOV26, DEC17):
            for url, page in self.pages(at).items():
                with self.subTest(at=at, url=url):
                    ids = re.findall(r'\sid="([^"]+)"', page)
                    self.assertEqual(sorted({i for i in ids if ids.count(i) > 1}), [])
                    for i in ("home-gvm-title", "home-gvm-title-2", "home-meeting-title", "home-meeting-title-2"):
                        self.assertIn(i, ids)

    def test_an_area_assembly_keeps_its_word_and_an_acm_is_an_area_event(self):
        """The Area's own events share one colour since round 30 (event-tone.js): on Home's row, as on /events/, an
        assembly's badge still says "Area assembly", an ACM's "Area event" (isAssembly)."""
        def ev(slug, ymd, en, es):
            e = json.loads(json.dumps(WORKSHOP))
            e.update(id=f"ev:manual:{slug}", url=f"/events/#{slug}", title=en, date=f"{ymd}T17:00:00Z", tags=["neta65"])
            e["extra"].update(start=f"{ymd}T17:00:00Z", end=f"{ymd}T22:00:00Z", location="Tyler Civic Center, Tyler, TX 75702")
            e["i18n"]["title"] = {"en": en, "es": es}
            return e
        items = B.recurring_events(ctx_with()) + [
            ev("2026-12-06-winter-acm", "2026-12-06", "Winter ACM 2026", "ACM de invierno 2026"),
            ev("2026-12-11-neta65-winter-assembly", "2026-12-11", "NETA 65 Winter Assembly 2026", "Asamblea de Invierno 2026 de NETA 65"),
        ]
        pages = run_js(self, PAGES_JS, data={"yaml": YAML, "items": items}, timeout=900, now=NOV26)
        for url, words in (("/", ("Area event", "Area assembly")), ("/es/", ("Evento del Área", "Asamblea de Área"))):
            row = part(pages[url], 'aria-labelledby="events-title"', "</section>")
            cards = {("acm" if "acm" in c.lower() else "assembly"): text(c) for c in re.findall(r"<article.*?</article>", row, re.S)
                     if "acm" in c.lower() or "assembl" in c.lower() or "asamblea" in c.lower()}
            with self.subTest(url=url):
                self.assertIn(words[0], cards["acm"])
                self.assertNotIn(words[1], cards["acm"])
                self.assertIn(words[1], cards["assembly"])

    def test_the_upcoming_events_leave_the_grapevine_meeting_to_the_hero(self):
        for url, title in (("/", "Grapevine Writing Workshop — Tyler"), ("/es/", "Taller de Escritura de Grapevine — Tyler")):
            page = self.pages(NOV26)[url]
            row = part(page, 'aria-labelledby="events-title"', "</section>")
            with self.subTest(url=url):
                cards = re.findall(r"<article.*?</article>", row, re.S)
                self.assertIn(title, text(cards[0]))
                self.assertFalse([c for c in cards if "grapevine-meeting" in c or "Grapevine Meeting" in text(c)
                                  or "Reunión de Grapevine" in text(c)], "the hero has it")


# =========================================================================== the browser's roll-on
class RollOn(unittest.TestCase):
    def test_first_meeting_then_the_next(self):
        r = run_js(self, DOM + r"""
          const res = {};
          for (const [name, first] of [["series", "2026-12-02"], ["none", ""], ["bad", "December 2"]]) {
            const p = page([], { files: ["time", "src/assets/js/app.js", "src/assets/js/home.js"], alpine: true, at: "2026-11-26T18:00:00Z" });
            p.ready();
            const c = p.comps.homeMeeting();
            const ds = { rule: JSON.stringify({ weekday: 3, n: 1, start: "19:00", end: "20:00", skip: [], starts: "2026-12-02" }),
                         start: "2026-12-03T01:00:00.000Z", end: "2026-12-03T02:00:00.000Z" };
            if (first) ds.first = first;
            c.$el = { dataset: ds }; c.$root = c.$el;
            c.$refs = { date: el("span", {}, [], "built date"), time: el("span", {}, [], "built time") };
            c.init();
            const before = [c.isFirst, c.live, c.dateLabel];
            p.clock.now = Date.parse("2026-12-03T01:30:00Z"); c.tick();          // 7:30 PM, Dec 2: the meeting is on
            const during = [c.isFirst, c.live];
            p.clock.now = Date.parse("2026-12-03T02:01:00Z"); c.tick();          // it is over: January 6
            res[name] = { before, during, after: [c.isFirst, c.live, c.dateLabel, new Date(c.start).toISOString()] };
            c.destroy();
          }
          out(res);""")
        s = r["series"]
        self.assertEqual(s["before"][:2], [True, False])
        self.assertEqual(s["before"][2], "built date", "the build's own words until the card rolls on")
        self.assertEqual(s["during"], [True, True])
        self.assertEqual(s["after"][:2], [False, False])
        self.assertEqual(plain(s["after"][2]), "Wednesday, January 6")
        self.assertEqual(s["after"][3], "2027-01-07T01:00:00.000Z")
        # without data-first (the committee meeting's card), or with one that is not a day: never "first"
        for name in ("none", "bad"):
            self.assertEqual([r[name]["before"][0], r[name]["during"][0], r[name]["after"][0]], [False, False, False], name)


# =========================================================================== the Upcoming events row
class HomeRow(Untranslated):
    def test_the_heros_series_keeps_no_place(self):
        booth = GVM_ENTRY.replace('"grapevine-meeting"', '"citywide-booth"').replace('"Grapevine Meeting"', '"Booth at CityWide"') \
            .replace("week_of_month: 1", "week_of_month: 2").replace('weekday: "wednesday"', 'weekday: "saturday"') \
            .replace('starts: "2026-12-02"', 'starts: "2026-12-12"')
        items = B.recurring_events(ctx_with(YAML + booth)) + [WORKSHOP]
        got = run_js(self, r"""
          const ids = (xs) => xs.map((e) => e.id);
          out({ before: ids(filters.homeEvents(input.items, null, 4)),
                hero: ids(filters.homeEvents(input.items, null, 4, "grapevine-meeting")),
                none: ids(filters.homeEvents(input.items, null, 4, "")),
                two: ids(filters.homeEvents(input.items, null, 2, "grapevine-meeting")) });
        """, data={"items": items}, now=NOV26)
        gvm = [i for i in got["before"] if ":grapevine-meeting:" in i]
        self.assertEqual(gvm, ["ev:recurring:grapevine-meeting:2026-12-02"], "without the argument: its next date keeps a place")
        self.assertEqual(got["none"], got["before"])
        self.assertFalse([i for i in got["hero"] if ":grapevine-meeting:" in i], "none of its dates")
        # the booth's next date keeps its place and the workshop its own; the row is one shorter here (one place per
        # series, and no other one-off event to take the freed place)
        self.assertEqual(got["hero"], ["ev:manual:2026-12-05-gv-writing-workshop-tyler", "ev:recurring:citywide-booth:2026-12-12"])
        self.assertEqual(got["two"], got["hero"])


if __name__ == "__main__":
    unittest.main()
