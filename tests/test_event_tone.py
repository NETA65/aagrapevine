"""Event colours by kind, and the Published writers "see more" rule.

  * eventTone (eleventy/filters/event-tone.js) — the one rule every event list uses for its colours
    (/events/, the home page's "Upcoming events", the monthly toolkit, Announcements "Coming up"):
    committee meeting (never the Area's: "Area Committee Meeting", "Reunión del Comité de Área") → La Viña /
    Grapevine holding it themselves (extra.host / host: La Viña's monthly workshop) → booth → the Area's own events
    (since round 30 one kind, "Area event": an assembly, an ACM, the Area's town hall; since round 35 its GSR/DCM
    orientations too — "GSR/DCM Orientation", "Orientación para RSG y MCD" —, never the committee's own GVR / RLV
    orientation or a plain "orientation") → a monthly meeting of ours
    (the Grapevine Meeting: neutral, its badge says NETA 65 — never read as an event of AA Grapevine's) → La Viña /
    Grapevine named in the title (the first one named wins) → the event's own Grapevine / La Viña calendar → other.
    Checked on data items, /events/ events and monthly date rows, in English and Spanish, plus the kinds the
    repository's events use. isAssembly: an Area assembly itself (its own words), never an ACM, a town hall or a
    GSR/DCM orientation — what the "next assembly" pickers and the badge "Area assembly" mean.
  * pwView (eleventy/filters/published.js) — each group shows its 12 most recent stories; the rest of
    the default view is marked `over` (listed without JavaScript, "see more" with it); when Area 65 is
    all shown and the longest period holds more of it, the page offers that period. The cards' search
    words drop apostrophes ("Beginner's" → "beginners") and hold initials together and one by one
    ("H. T. B." → "htb h t b"), so "L.C", "L C", "LC" and "L.C." all find "L.C.".

Runs the JavaScript with Node.js (tests/nodejs.py); skipped without Node.js / the npm packages.

    python -m unittest tests.test_event_tone -v
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

TONE_JS = """
const { eventTone, eventToneSet, EVENT_TONES, isAssembly } = await imp("eleventy/filters/event-tone.js");
out({
  tones: input.cases.map((c) => eventTone(c)),
  assembly: input.asm.map((c) => isAssembly(c)),
  asmFilter: typeof filters.isAssembly === "function",
  set: eventToneSet(input.cases),
  order: EVENT_TONES,
  junk: [eventTone(null), eventTone(undefined), eventTone("x"), eventTone({})],
  filter: typeof filters.eventTone === "function" && typeof filters.eventToneSet === "function",
  data: [...new Set(JSON.parse(fs.readFileSync("data/site/events.json", "utf8")).items
    .filter((it) => it && it.kind === "event").map((it) => it.title + " => " + eventTone(it) + " => " + isAssembly(it)))],
});
"""

# (event, expected kind)
CASES: list[tuple[dict, str]] = [
    # 1. the committee's own meeting — by flag / category / monthly kind / id, before any title rule
    ({"committee": True, "title": "NETA 65 Grapevine & La Viña Committee Meeting"}, "committee"),
    ({"category": "committee", "title": "Reunión del Comité de Grapevine y La Viña de NETA 65"}, "committee"),
    ({"kind": "committee", "title": ""}, "committee"),
    ({"id": "ev:committee:2026-10-22", "title": ""}, "committee"),
    ({"category": "manual", "title": "Special committee meeting — Grapevine"}, "committee"),
    ({"category": "manual", "title": "Reunión del comité de La Viña"}, "committee"),
    ({"committee": True, "title": "", "extra": {"host": "lv"}}, "committee"),
    # 2. La Viña / Grapevine hold it themselves (config/site.yml recurring_events `host:`): their colour,
    #    whatever the title says — on a data item, a /events/ event (.host / .item) and a monthly date row
    ({"category": "recurring", "title": "Monthly Virtual Workshop", "extra": {"host": "lv"}}, "lv"),
    ({"category": "recurring", "title": "Grapevine booth at the Round-Up", "extra": {"host": "lv"}}, "lv"),
    ({"host": "gv", "title": "Taller de La Viña"}, "gv"),
    ({"kind": "recurring", "host": "lv", "title": "Taller Mensual y Virtual"}, "lv"),
    ({"title": "Workshop", "item": {"category": "recurring", "extra": {"host": "LV"}}}, "lv"),
    ({"category": "recurring", "title": "GV/LV booth at CityWide Dallas", "extra": {"host": "neta"}}, "booth"),
    ({"category": "flyer", "title": "Unity Day 2027", "extra": {"host": "somebody"}}, "other"),
    # 3. booth — before the GV / LV names it carries
    ({"category": "recurring", "title": "GV/LV booth at CityWide Dallas"}, "booth"),
    ({"kind": "recurring", "title": "Mesa de GV/LV en CityWide Dallas"}, "booth"),
    ({"title": "Grapevine literature table at the Round-Up"}, "booth"),
    ({"title": "Round table on sponsorship"}, "other"),
    ({"title": "Mesa redonda de servicio"}, "other"),
    # 4. the Area's own events: an assembly …
    ({"category": "manual", "title": "NETA 65 Spring Assembly 2027"}, "assembly"),
    ({"title": "Asamblea de Otoño 2027 de NETA 65"}, "assembly"),
    ({"title": "District 12 Pre-Assembly"}, "assembly"),
    #    … the Area Committee Meeting (round 30: never the committee's own meeting, whatever its words say) …
    ({"category": "manual", "title": "Winter ACM 2027", "tags": ["neta65", "acm"]}, "assembly"),
    ({"title": "ACM de Otoño 2027"}, "assembly"),
    ({"title": "Fall Area Committee Meeting"}, "assembly"),
    ({"title": "Reunión del Comité de Área de Primavera"}, "assembly"),
    ({"title": "Reunion del comite del Area 65"}, "assembly"),
    ({"title": "Taller", "item": {"title": "Spring ACM 2027"}}, "assembly"),
    #    … and its town hall (the delegate's: titled so in English; the Spanish page reads that title too)
    ({"category": "manual", "title": "Delegate — Conference Connect Town Hall"}, "assembly"),
    ({"title": "Reunión Informativa de la Delegada — Conference Connect",
      "item": {"title": "Delegate — Conference Connect Town Hall"}}, "assembly"),
    ({"title": "Area Townhall"}, "assembly"),
    #    … and (round 35) its orientation for GSRs and DCMs, in either language — on a data item, a /events/ event
    #    (its record's titles first) and a monthly date row (.src)
    ({"category": "manual", "title": "GSR/DCM Orientation 2027 — Central", "tags": ["neta65", "gsr-dcm-orientation"]},
     "assembly"),
    ({"title": "GSR/DCM Orientation (East)"}, "assembly"),
    ({"title": "GSR Orientation"}, "assembly"),
    ({"title": "DCM orientation — West"}, "assembly"),
    ({"title": "GSR & DCM Orientations 2027"}, "assembly"),
    ({"title": "Orientation for GSRs and DCMs"}, "assembly"),
    ({"title": "Orientation for new General Service Representatives"}, "assembly"),
    ({"title": "District Committee Member orientation"}, "assembly"),
    ({"title": "Orientación para RSG y MCD 2027 — Este"}, "assembly"),
    ({"title": "Orientación de RSG/MCD"}, "assembly"),
    ({"title": "Orientación de RSG"}, "assembly"),
    ({"title": "ORIENTACION PARA MCDS"}, "assembly"),
    ({"title": "Orientaciones para Representantes de Servicios Generales"}, "assembly"),
    ({"title": "Orientación para Miembros del Comité de Distrito"}, "assembly"),
    ({"title": "Orientación para RSG y MCD 2027 — Oeste",
      "item": {"title": "GSR/DCM Orientation 2027 — West", "i18n": {"title": {"es": "Orientación para RSG y MCD 2027 — Oeste"}}}},
     "assembly"),
    ({"kind": "event", "title": "Orientación para RSG y MCD 2027 — Central",
      "src": {"title": "GSR/DCM Orientation 2027 — Central"}}, "assembly"),
    #    (never the committee's own orientation for GVRs and RLVs — /orientation/ —, nor an orientation that names
    #    no GSR or DCM)
    ({"title": "GVR and RLV Orientation Workshop"}, "other"),
    ({"title": "Taller de orientación para RLV y GVR"}, "other"),
    ({"title": "GVR/RLV Orientation"}, "other"),
    ({"title": "GVR orientation"}, "other"),
    ({"title": "Orientación para RLV"}, "other"),
    ({"title": "New-rep orientation"}, "other"),
    ({"title": "Orientation"}, "other"),
    ({"title": "Orientación"}, "other"),
    ({"title": "GVR orientation for GSRs"}, "other"),
    ({"title": "Orientación de RLV para RSG"}, "other"),
    ({"title": "Grapevine orientation for GSRs and DCMs"}, "gv"),        # ours, by its name: rule 6
    ({"title": "La Viña orientation for DCMs"}, "lv"),
    ({"title": "GSR sharing session"}, "other"),                         # a GSR word, no orientation
    ({"title": "Orienteering day for GSRs"}, "other"),                   # not the word orientation
    ({"title": "GV/LV table at the GSR/DCM Orientation"}, "booth"),      # a booth there: rule 3 first
    #    (words that only look like one: never)
    ({"title": "Academy night"}, "other"),
    ({"title": "Town hallway clean-up"}, "other"),
    # 5. a monthly meeting of ours (recurring_events, no host of theirs — the Grapevine Meeting): never the colour of
    #    an event AA Grapevine holds, whatever its name says — on a data item, a /events/ event and a monthly date row
    ({"category": "recurring", "title": "Grapevine Meeting", "extra": {"host": "neta", "series": "grapevine-meeting"}}, "other"),
    ({"category": "recurring", "title": "Reunión de Grapevine"}, "other"),
    ({"recurring": True, "category": "recurring", "host": "", "title": "Grapevine Meeting"}, "other"),
    ({"kind": "recurring", "host": "", "title": "Reunión de Grapevine"}, "other"),
    ({"category": "recurring", "title": "Grapevine Meeting", "extra": {"host": "gv"}}, "gv"),       # theirs: rule 2
    ({"category": "gv-calendar", "title": "Grapevine Weekly Open AA Meeting"}, "gv"),             # not a series of ours
    ({"category": "manual", "title": "Grapevine meeting night"}, "gv"),                            # a one-off: by title
    # 6. La Viña / Grapevine by title (accents and case ignored; the first one named wins)
    ({"title": "La Viña Writing Workshop (in Spanish) — Fort Worth"}, "lv"),
    ({"title": "Taller de escritura de LA VINA"}, "lv"),
    ({"title": "Grapevine Writing Workshop — Arlington"}, "gv"),
    ({"title": "Taller de Grapevine y La Viña"}, "gv"),
    ({"title": "La Viña & Grapevine night"}, "lv"),
    # every title is read: the record's (item / src) original and translations first, the display title last
    # (round 33c: the same order on the English and the Spanish page — tests/test_monthly_dates.py)
    ({"title": "Taller mensual", "item": {"title": "Monthly La Viña workshop"}}, "lv"),
    ({"title": "Monthly workshop", "i18n": {"title": {"es": "Taller de Grapevine"}}}, "gv"),
    # 7. an event from Grapevine's / La Viña's own calendar
    ({"category": "lv-calendar", "title": "Taller Mensual"}, "lv"),
    ({"category": "gv-calendar", "title": "Weekly Open"}, "gv"),
    ({"item": {"category": "lv-calendar", "title": "Taller"}, "title": "Workshop"}, "lv"),
    # 8. anything else
    ({"category": "flyer", "title": "Unity Day 2027"}, "other"),
    ({"title": "Timetable review"}, "other"),
]


# isAssembly: an Area assembly itself (rule 4's own words) — never an ACM or a town hall (the same colour), a booth at
# an assembly (rule 3), the committee's meeting or La Viña's own event (rules 1 and 2)
ASSEMBLY: list[tuple[dict | None, bool]] = [
    ({"category": "manual", "title": "NETA 65 Spring Assembly 2027"}, True),
    ({"title": "Asamblea de Otoño 2027 de NETA 65"}, True),
    ({"title": "District 12 Pre-Assembly"}, True),
    ({"title": "Taller", "item": {"title": "NETA 65 Summer Assembly 2027"}}, True),
    ({"category": "manual", "title": "Winter ACM 2027"}, False),
    ({"title": "Fall Area Committee Meeting"}, False),
    ({"title": "Reunión del Comité de Área de Primavera"}, False),
    ({"title": "Delegate — Conference Connect Town Hall"}, False),
    ({"category": "manual", "title": "GSR/DCM Orientation 2027 — East"}, False),      # an Area event, not an assembly
    ({"title": "Orientación para RSG y MCD 2027 — Central"}, False),
    ({"title": "GV/LV booth — Fall Assembly"}, False),
    ({"committee": True, "title": "Committee meeting at the assembly"}, False),
    ({"host": "lv", "title": "La Viña workshop at the assembly"}, False),
    ({"title": "Unity Day 2027"}, False),
    (None, False),
]


class EventToneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = None

    def result(self):
        if EventToneTest.res is None:
            EventToneTest.res = run_js(self, TONE_JS, data={"cases": [c for c, _ in CASES], "asm": [c for c, _ in ASSEMBLY]})
        return EventToneTest.res

    def test_rules(self):
        got = self.result()["tones"]
        for (case, want), have in zip(CASES, got):
            with self.subTest(case=case):
                self.assertEqual(have, want)

    def test_set_is_in_key_order_and_only_present_kinds(self):
        r = self.result()
        self.assertEqual(r["order"], ["committee", "gv", "lv", "booth", "assembly", "other"])
        self.assertEqual(r["set"], [k for k in r["order"] if k in {w for _, w in CASES}])

    def test_junk_is_other_and_filters_registered(self):
        r = self.result()
        self.assertEqual(r["junk"], ["other"] * 4)
        self.assertTrue(r["filter"])
        self.assertTrue(r["asmFilter"])

    def test_an_assembly_itself(self):
        for (case, want), have in zip(ASSEMBLY, self.result()["assembly"]):
            with self.subTest(case=case):
                self.assertIs(have, want)

    def test_repository_events(self):
        rows = self.result()["data"]
        for row in rows:
            title, kind, asm = row.rsplit(" => ", 2)
            low = title.lower()
            with self.subTest(title=title):
                # an Area assembly itself: the assembly kind AND its own word
                self.assertEqual(asm, "true" if kind == "assembly" and "assembly" in low else "false")
                if "committee meeting" in low:
                    self.assertEqual(kind, "committee")
                elif "booth" in low:
                    self.assertEqual(kind, "booth")
                elif "assembly" in low:
                    self.assertEqual(kind, "assembly")
                elif re.search(r"\bacm\b|town hall", low):        # the Area's ACMs and town hall: its colour
                    self.assertEqual(kind, "assembly")
                elif (re.search(r"\b(?:gsr|dcm)s?\b", low) and "orientation" in low    # its GSR/DCM orientations
                      and not re.search(r"\b(?:gvrs?|rlvs?|grapevine|la viña|la vina|gv|lv)\b", low)):
                    self.assertEqual(kind, "assembly")
                elif "grapevine meeting" in low:            # our monthly meeting (recurring_events): never theirs
                    self.assertEqual(kind, "other")
                elif "la viña" in low:
                    self.assertEqual(kind, "lv")
                elif "grapevine" in low:
                    self.assertEqual(kind, "gv")


PW_JS = """
const v = filters.pwView({ spotlight: input.spotlight }, "en");
out({
  limit: v.limit, defDays: v.defDays, defScope: v.defScope,
  groups: v.groups.map((g) => ({ key: g.key, matchCount: g.matchCount, shownCount: g.shownCount,
    hiddenByLimit: g.hiddenByLimit, widen: g.widen,
    visible: g.items.filter((i) => i.visible).map((i) => i.date),
    over: g.items.filter((i) => i.over).length })),
});
"""
TODAY = "2026-09-26"


def story(n: int, scope: str, date: str) -> dict:
    return {"id": f"s{n}", "kind": "article", "source": "grapevine", "category": "gv", "lang": "en",
            "url": f"https://www.aagrapevine.org/story/{n}", "title": f"Story {n}", "date": date,
            "extra": {"pub_date": date, "author": f"Writer {n}", "geo": {"scope": scope, "label_en": "Dallas, Texas"}}}


def spotlight(items: list[dict]) -> dict:
    return {"updated": TODAY + "T10:00:00Z", "list_days": [60, 90], "default_scope": "neta65", "items": items}


class PublishedLimitTest(unittest.TestCase):
    def view(self, items):
        return run_js(self, PW_JS, data={"spotlight": spotlight(items)}, env={"PW_TODAY": TODAY})

    def group(self, v, key):
        return next(g for g in v["groups"] if g["key"] == key)

    def test_area_highlight_is_the_12_most_recent(self):
        # 15 Area 65 stories in the default 60 days (Sep 1..15) + 20 from elsewhere
        items = [story(i, "neta65", f"2026-09-{i:02d}") for i in range(1, 16)]
        items += [story(100 + i, "other", f"2026-09-{i:02d}") for i in range(1, 21)]
        v = self.view(items)
        self.assertEqual(v["limit"], 12)
        area = self.group(v, "neta65")
        self.assertEqual((area["matchCount"], area["shownCount"], area["hiddenByLimit"], area["over"]), (15, 12, 3, 3))
        self.assertEqual(area["visible"], [f"2026-09-{i:02d}" for i in range(15, 3, -1)])  # newest first
        self.assertIsNone(area["widen"])
        # outside the default scope: nothing visible, nothing "over" (the no-JS page shows the default view)
        other = self.group(v, "other")
        self.assertEqual((other["matchCount"], other["over"], len(other["visible"])), (0, 0, 0))

    def test_area_all_shown_offers_the_longer_period(self):
        items = [story(1, "neta65", "2026-09-01"), story(2, "neta65", "2026-08-01"),
                 story(3, "neta65", "2026-07-01"), story(4, "neta65", "2026-07-02")]
        area = self.group(self.view(items), "neta65")
        self.assertEqual((area["matchCount"], area["hiddenByLimit"]), (2, 0))
        self.assertEqual(area["widen"], {"days": 90, "n": 4})

    def test_no_widen_when_the_longer_period_adds_nothing(self):
        area = self.group(self.view([story(1, "neta65", "2026-09-01")]), "neta65")
        self.assertIsNone(area["widen"])

    def test_search_words_keep_apostrophes_and_initials_together(self):
        # the cards' data-s (and published.js): "Beginner's" → "beginners", "H. T. B." → "htb" — so the searches
        # "beginners" and "H.T.B." find them; each field on its own (two writers' initials never run together)
        it = story(1, "neta65", "2026-09-01")
        it["title"] = "Beginner’s Luck"
        it["extra"]["author"] = "H. T. B."
        it["extra"]["author_location"] = "Tyler, Texas"
        words = run_js(self, PW_SEARCH_JS, data={"spotlight": spotlight([it]), "queries": []}, env={"PW_TODAY": TODAY})["words"]
        self.assertIn("beginners", words)
        self.assertIn("htb", words)
        self.assertNotIn("s", words)
        self.assertEqual(len(words), len(set(words)))

    def test_initials_are_found_however_they_are_typed(self):
        # a writer printed "L.C.": the search words hold the initials together AND one by one, so "L.C", "L C" (a search
        # keeps initials together only when each letter has its period), "LC" and "L.C." all find the card
        it = story(1, "neta65", "2026-09-01")
        it["extra"]["author"] = "L.C."
        queries = ["L.C", "L C", "LC", "L.C.", "l.c"]
        r = run_js(self, PW_SEARCH_JS, data={"spotlight": spotlight([it]), "queries": queries}, env={"PW_TODAY": TODAY})
        self.assertTrue({"lc", "l", "c"} <= set(r["words"]))
        s = " " + " ".join(r["words"]) + " "
        for q in queries:
            with self.subTest(q=q):
                self.assertTrue(all(" " + t in s for t in r["toks"][q]), r["toks"][q])   # every word starts a word


PW_SEARCH_JS = """
const { pwNorm } = await imp("eleventy/filters/published.js");
const v = filters.pwView({ spotlight: input.spotlight }, "en");
out({ words: v.items[0].search.split(" "), toks: Object.fromEntries(input.queries.map((q) => [q, pwNorm(q).split(" ").filter(Boolean)])) });
"""


if __name__ == "__main__":
    unittest.main()
