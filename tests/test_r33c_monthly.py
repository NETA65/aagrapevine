"""Round 33c · the monthly toolkit's dates on one day follow their time, and an event's colour never depends on the
page's language (eleventy/filters/monthly.js monthModel, eleventy/filters/event-tone.js eventTone).

The bugs (live, 2026-11-17):
  * /monthly/2026-11/ and /es/monthly/2026-11/ listed the November 18 committee meeting (7–8 PM) ABOVE La Viña's
    monthly workshop (2–3 PM): the month's dates were sorted by their day alone, so on one day the committee meeting
    (always first in the list they are made from) came first. Now an all-day date comes first on its day, then the
    timed ones by their start — the order of /events/ and its calendar's "Next up" — and dates that start at the same
    moment keep the old order (a stable sort, never by title: that would differ between English and Spanish). The
    page's Dates card, its "Earlier in …" fold, the poster, the hub's chips and the month's message all use this list.
  * In the folded "Earlier in November" rows the delegate's town hall ("Delegate — Conference Connect Town Hall",
    Spanish "Reunión Informativa de la Delegada — Conference Connect") had the Area-event colour (ev-tone-assembly) in
    English but the neutral one (ev-tone-other) in Spanish: a monthly date row carried only its title in the page's
    language, and eventTone read nothing else. eventTone now reads the record a shown event was made from (a /events/
    event's item, a date row's src) — its original, English and Spanish titles first, the shown title last — so every
    page agrees in both languages.

Checked with Node.js on a small November 2026 data set (the order on one day, the same ids in the same order in both
languages, the message's order; each event's colour on its data item, its /events/ event and its date row in both
languages) and on the repository's own data (every month of the window, every event).

    python -m unittest tests.test_r33c_monthly -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

NOW = "2026-11-05T18:00:00Z"        # Thursday, November 5, 2026, noon in Texas: every date below is still to come
SITE = {"url": "https://example.org/site", "title": "Grapevine / La Viña",
        "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet"},
        "recurring_events": []}


def event(iid: str, start: str, end: str | None, title: str, title_es: str, **kw) -> dict:
    extra = {"start": start, "end": end, **kw.pop("extra", {})}
    it = {"id": iid, "kind": "event", "status": "ok", "title": title, "url": kw.pop("url", f"https://example.com/{iid}"),
          "date": start, "lang": "en", "category": kw.pop("category", "manual"), "source": "committee", "extra": extra,
          "i18n": {"title": {"en": title, "es": title_es}}, "machine": []}
    it.update(kw)
    return it


EVENTS = [
    # November 18: the committee meeting at 7 PM, La Viña's monthly workshop at 2 PM, an all-day event, and an event
    # that starts at the same moment as the committee meeting (after it: the stable order)
    event("ev:committee:2026-11-18", "2026-11-19T01:00:00Z", "2026-11-19T02:00:00Z",
          "NETA 65 Grapevine & La Viña Committee Meeting", "Reunión del Comité de Grapevine y La Viña de NETA 65",
          category="committee", url="/meetings/#committee-meeting", extra={"recurring": True, "location": "Google Meet"}),
    event("ev:same-time", "2026-11-19T01:00:00Z", "2026-11-19T02:00:00Z", "Service talk", "Charla de servicio"),
    event("ev:lv-workshop:2026-11-18", "2026-11-18T20:00:00Z", "2026-11-18T21:00:00Z",
          "La Viña Monthly Virtual Workshop (in Spanish)", "Taller Mensual y Virtual de La Viña", category="recurring",
          extra={"recurring": True, "series": "lv-monthly-workshop", "host": "lv", "location": "Zoom"}),
    event("ev:all-day-18", "2026-11-18", None, "Unity Day", "Día de la Unidad", extra={"all_day": True, "city": "Tyler"}),
    # November 17 at 9 PM Central: already November 18 in UTC, still the 17th on the page
    event("ev:late-17", "2026-11-18T03:00:00Z", "2026-11-18T04:00:00Z", "Late workshop", "Taller nocturno"),
    # the 1st: an assembly that began in October (its chip on the 1st) before a 9 AM event of that day
    event("ev:assembly", "2026-10-30", "2026-11-01", "NETA 65 Fall Assembly", "Asamblea de Otoño de NETA 65",
          extra={"all_day": True, "city": "Tyler"}),
    event("ev:nov1", "2026-11-01T15:00:00Z", "2026-11-01T16:00:00Z", "Morning workshop", "Taller matutino"),
    # the delegate's town hall: "Town Hall" only in its English (original) title
    event("ev:manual:2026-11-10-neta65-delegate-town-hall", "2026-11-11T01:00:00Z", "2026-11-11T02:00:00Z",
          "Delegate — Conference Connect Town Hall", "Reunión Informativa de la Delegada — Conference Connect",
          url="https://neta65.org/event/delegate-conference-connect-town-hall-2/"),
    # La Viña named first in the original, Grapevine first in the Spanish title: La Viña's colour on both pages
    event("ev:night", "2026-11-22T00:00:00Z", "2026-11-22T02:00:00Z", "La Viña & Grapevine night",
          "Noche de Grapevine y La Viña"),
]

ORDER = ["ev:assembly", "ev:nov1", "ev:manual:2026-11-10-neta65-delegate-town-hall", "ev:late-17", "ev:all-day-18",
         "ev:lv-workshop:2026-11-18", "ev:committee:2026-11-18", "ev:same-time", "ev:night"]

TONES = {"ev:assembly": "assembly", "ev:nov1": "other", "ev:manual:2026-11-10-neta65-delegate-town-hall": "assembly",
         "ev:late-17": "other", "ev:all-day-18": "other", "ev:lv-workshop:2026-11-18": "lv",
         "ev:committee:2026-11-18": "committee", "ev:same-time": "other", "ev:night": "lv"}

MODEL_JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const { eventTone, isAssembly } = await imp("eleventy/filters/event-tone.js");
const { normalizeEvents } = await imp("eleventy/filters/committee.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const now = new Date(input.now);
const { db, site } = input;
const mm = {}, res = { rows: {}, events: {}, msg: {} };
for (const lang of ["en", "es"]) {
  mm[lang] = M.monthModel("2026-11", db, {}, site, lang, now);
  res.rows[lang] = mm[lang].dates.map((d) => ({ id: d.id, ymd: d.chip.ymd, time: d.time, tone: eventTone(d), asm: isAssembly(d),
    title: d.title }));
  res.events[lang] = Object.fromEntries(normalizeEvents(db.events.items, site, lang, { now }).map((e) => [e.item.id, eventTone(e)]));
}
res.raw = Object.fromEntries(db.events.items.map((it) => [it.id, eventTone(it)]));
const nw = { en: M.monthNow(db, site, "en", now), es: M.monthNow(db, site, "es", now) };
const iss = { en: M.monthIssueLinks(db, mm.en), es: M.monthIssueLinks(db, mm.es) };
for (const lang of ["en", "es"]) res.msg[lang] = M.monthMessage({ mm, nw, iss }, [lang], "whatsapp", site, t);
out(res);
"""


def small_db() -> dict:
    return {"events": {"items": EVENTS}, "editorial": {"items": []}, "articles": {"issues": [], "items": []},
            "weekly_open": {"items": []}, "shop": {}}


class SmallMonth(unittest.TestCase):
    """November 2026 of the small data set, in English and Spanish."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def result(self) -> dict:
        if SmallMonth.r is None:
            SmallMonth.r = run_js(self, MODEL_JS, data={"db": small_db(), "site": SITE, "now": NOW}, now=NOW)
        return SmallMonth.r

    def test_one_day_follows_the_clock(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                self.assertEqual([d["id"] for d in self.result()["rows"][lang]], ORDER)

    def test_the_workshop_comes_before_the_committee_meeting(self):
        rows = {lang: {d["id"]: d for d in self.result()["rows"][lang]} for lang in ("en", "es")}
        # (the time's space is a no-break space: never split)
        self.assertEqual(rows["en"]["ev:lv-workshop:2026-11-18"]["time"], "2–3\u00a0PM")
        self.assertEqual(rows["en"]["ev:committee:2026-11-18"]["time"], "7–8\u00a0PM")
        self.assertEqual(rows["en"]["ev:late-17"]["ymd"], "2026-11-17", "9 PM Central is still the 17th")
        self.assertEqual(rows["en"]["ev:assembly"]["ymd"], "2026-11-01", "a date that began in October shows on the 1st")

    def test_the_message_lists_them_in_that_order(self):
        msg = self.result()["msg"]
        for lang, workshop, committee in (("en", "La Viña Monthly Virtual Workshop", "Committee meeting"),
                                          ("es", "Taller Mensual y Virtual de La Viña", "Reunión del comité")):
            with self.subTest(lang=lang):
                text = msg[lang]
                self.assertIn(workshop, text)
                self.assertIn(committee, text)
                self.assertLess(text.index(workshop), text.index(committee))

    def test_one_colour_in_both_languages_on_every_list(self):
        r = self.result()
        rows = {lang: {d["id"]: d["tone"] for d in r["rows"][lang]} for lang in ("en", "es")}
        for iid, want in TONES.items():
            with self.subTest(id=iid):
                self.assertEqual(r["raw"][iid], want, "the data item")
                self.assertEqual(rows["en"][iid], want, "the English date row")
                self.assertEqual(rows["es"][iid], want, "the Spanish date row")
                self.assertEqual(r["events"]["en"].get(iid, want), want, "the English /events/ event")
                self.assertEqual(r["events"]["es"].get(iid, want), want, "the Spanish /events/ event")
        # the town hall and the night are on /events/ too (still to come at NOW)
        for iid in ("ev:manual:2026-11-10-neta65-delegate-town-hall", "ev:night"):
            self.assertIn(iid, r["events"]["es"])

    def test_the_town_hall_is_an_area_event_not_an_assembly(self):
        for lang in ("en", "es"):
            row = next(d for d in self.result()["rows"][lang] if "town-hall" in d["id"])
            self.assertEqual((row["tone"], row["asm"]), ("assembly", False), lang)
        es = next(d for d in self.result()["rows"]["es"] if d["id"] == "ev:assembly")
        self.assertTrue(es["asm"], "an assembly itself stays one in Spanish")


REAL_JS = r"""
const M = await imp("eleventy/filters/monthly.js");
const { eventTone } = await imp("eleventy/filters/event-tone.js");
const { eventSpan } = await imp("eleventy/filters/committee.js");
const db = (await imp("src/_data/db.js")).default();
const site = (await imp("src/_data/site.js")).default();
const carry = (await imp("src/_data/carry.js")).default();
const res = { months: [], events: {}, raw: {} };
for (const key of M.windowKeys()) {
  const one = {};
  for (const lang of ["en", "es"]) {
    const m = filters.mpMonth(key, db, carry, site, lang);
    one[lang] = m.dates.map((d) => {
      const s = d.src ? eventSpan(d.src) : null;
      return { id: d.id, ymd: d.chip.ymd, start: s ? s.startMs : null, tone: eventTone(d) };
    });
  }
  res.months.push({ key, ...one });
}
for (const lang of ["en", "es"])
  res.events[lang] = Object.fromEntries(filters.cmEvents(db.events.items, site, lang).map((e) => [e.item.id, eventTone(e)]));
for (const it of db.events.items) if (it && it.kind === "event") res.raw[it.id] = eventTone(it);
out(res);
"""


class RealData(unittest.TestCase):
    """Every month of the window and every event, from the repository's own data."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def result(self) -> dict:
        if RealData.r is None:
            RealData.r = run_js(self, REAL_JS)
        return RealData.r

    def test_the_same_dates_in_the_same_order_in_both_languages(self):
        for m in self.result()["months"]:
            with self.subTest(month=m["key"]):
                self.assertEqual([d["id"] for d in m["en"]], [d["id"] for d in m["es"]])

    def test_each_day_by_its_start(self):
        for m in self.result()["months"]:
            rows = m["en"]
            for a, b in zip(rows, rows[1:]):
                with self.subTest(month=m["key"], a=a["id"], b=b["id"]):
                    self.assertLessEqual(a["ymd"], b["ymd"])
                    if a["ymd"] == b["ymd"] and a["start"] is not None and b["start"] is not None:
                        self.assertLessEqual(a["start"], b["start"])

    def test_one_colour_per_event_everywhere(self):
        r = self.result()
        seen: dict[str, set[str]] = {}
        for iid, tone in r["raw"].items():
            seen.setdefault(iid, set()).add(tone)
        for lang in ("en", "es"):
            for iid, tone in r["events"][lang].items():
                seen.setdefault(iid, set()).add(tone)
        for m in r["months"]:
            for lang in ("en", "es"):
                for d in m[lang]:
                    seen.setdefault(d["id"], set()).add(d["tone"])
        self.assertGreater(len(seen), 50)
        for iid, tones in sorted(seen.items()):
            with self.subTest(id=iid):
                self.assertEqual(len(tones), 1, tones)


if __name__ == "__main__":
    unittest.main()
