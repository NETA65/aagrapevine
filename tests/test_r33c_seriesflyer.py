"""Round 33c: a dated Drive flyer of a monthly series on a day the host moved is that day's card of the series.

The live case (Nov 17, 2026): La Viña's monthly Zoom workshop (config/site.yml `recurring_events:` key
`lv-monthly-workshop`, the 4th Thursday) moved in November from Thanksgiving, Thu Nov 26 (in its `skip_dates`), to
Wed Nov 18, and the committee put its flyer on the Drive with the day in its name: "2026-11-18 Taller Mensual y
Virtual de La Viña 2pm-3pm.jpeg". The name matches the series' `flyer_match`, so build_data.series_dated_flyers
kept it as an event of its own and gave it the series' host, Zoom link, platform, meeting ID and contact — but
not the series' words or its key: the English /events/ card showed a grey "ES" pill ("Originally in Spanish")
and no summary, while every other date of the workshop shows the series' summary and no pill
(eleventy/filters/committee.js ownLangs counts only a committee item, or one with `extra.series_of`, as the
committee's own words).

Now the flyer is taken in the way series_moved_dates takes in the host's calendar listing of a skipped month: the
series' title and summary in both languages, as config/site.yml writes them (fixed i18n, never machine-
translated), its language, `extra.series_of`, host, online room, meeting ID, contact and platform — keeping the
flyer's own day, time, link and flyer. Nothing else changes: a flyer on one of the series' own dates is that date's
flyer (no second event), the committee meeting's dated flyers are handled as before, and a dated flyer that
matches no series keeps its own words.

These tests read the REAL config/site.yml (the words expected are taken from it, so the chair can reword the
series without turning them red) with a fake Drive flyer shaped as drive.py lists it (data/raw/drive.json), the
clock stopped at Tue Nov 17, 2026. No network, no translation model; the pages' side runs with Node.js.

    python -m unittest tests.test_r33c_seriesflyer -v
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))     # nodejs.py

from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import events_external as E  # noqa: E402

NOW = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)      # Tue Nov 17, 2026, 9 AM CST
CFG = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
KEY = "lv-monthly-workshop"
LV = next(e for e in CFG["recurring_events"] if e.get("key") == KEY)
LV_ID = f"ev:recurring:{KEY}:"
MOVED_ID = "1CIjzw73s0HBGB4wR6qosUiTMIRLOyW_k"                # the real file's id (any id would do)
SERIES_FLYER_ID = "16Tm35F7P7ynir3lH03wZBWmVE0MllVuR"


class NoTranslator:
    """Stands in for the translation model: tests never download or run it."""
    def translate(self, texts, src, tgt):
        return [(None, False) for _ in texts]


def drive_file(name: str, fid: str, title: str, lang: str = "es", day: str = "2026-11-17", **extra) -> dict:
    """A committee Drive file in flyers/ as drive.py lists it (data/raw/drive.json): the title is the name without
    its extension and without the date at its start (drive.py keeps that in extra.event_date …)."""
    view = f"https://drive.google.com/file/d/{fid}/view"
    return {"id": f"drive:{fid}", "source": "drive", "kind": "photo", "url": view, "title": title, "summary": "",
            "lang": lang, "date": day, "first_seen": f"{day}T21:43:18Z", "last_seen": f"{day}T21:43:18Z",
            "image": f"https://lh3.googleusercontent.com/d/{fid}=w600", "tags": ["panel-77", "jpeg"],
            "category": "flyers", "status": "ok",
            "extra": {"file_id": fid, "mime": "image/jpeg", "name": name, "path": ["flyers"], "view_url": view,
                      "preview_url": f"https://drive.google.com/file/d/{fid}/preview",
                      "thumb_url": f"https://lh3.googleusercontent.com/d/{fid}=w600", "is_image": True,
                      "is_video": False, "is_pdf": False, **extra}}


def lv_flyer(day: str, fid: str = MOVED_ID) -> dict:
    """'2026-11-18 Taller Mensual y Virtual de La Viña 2pm-3pm.jpeg': a dated flyer of La Viña's workshop."""
    return drive_file(f"{day} Taller Mensual y Virtual de La Viña 2pm-3pm.jpeg", fid,
                      "Taller Mensual y Virtual de La Viña 2pm-3pm", event_date=day,
                      event_title="Taller Mensual y Virtual de La Viña", event_time="14:00", event_end_time="15:00")


SERIES_NAME = "Taller Mensual y Virtual de La Viña - jueves, 3 p. m. (hora del Este), por Zoom"
SERIES_FLYER = drive_file(SERIES_NAME + ".png", SERIES_FLYER_ID, SERIES_NAME, day="2026-10-01")   # every date's


def ctx_with(**raw: list[dict]) -> B.Ctx:
    """A build context with the real config/site.yml, the clock stopped at NOW and the given raw items
    (drive=[…], events_external=[…]); nothing read from data/raw."""
    ctx = B.Ctx(offline=True)
    ctx.now, ctx.now_ts = NOW, NOW.timestamp()
    ctx.today_local = NOW.astimezone(ctx.tz).date()
    for name, items in raw.items():
        ctx.raw[name] = {"items": items}
    return ctx


def build(**raw: list[dict]) -> tuple[B.Ctx, list[dict]]:
    ctx = ctx_with(**raw)
    with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()), \
            mock.patch.object(B, "ics_events", lambda c: []):
        return ctx, B.build_events(ctx)


def local_day(ctx: B.Ctx, ev: dict) -> str:
    return B._event_day(ctx, ev)


def series_words() -> dict:
    """The series' title and summary in both languages, as config/site.yml writes them."""
    return {"title": {"en": LV["title"], "es": LV["title_es"]},
            "summary": {"en": LV["summary"], "es": LV["summary_es"]}}


class MovedDateFlyer(unittest.TestCase):
    """The Nov 18 flyer: that month's card of the series."""

    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.evs = build(drive=[SERIES_FLYER, lv_flyer("2026-11-18")])
        cls.moved = next(e for e in cls.evs if e["id"] == f"ev:flyer:{MOVED_ID}")

    def test_the_rule_skips_november_and_nov_18_is_no_date_of_the_series(self):
        """(What the case rests on: the config the site runs with.)"""
        self.assertIn("2026-11-26", LV["skip_dates"])
        days = {local_day(self.ctx, e) for e in self.evs if e["id"].startswith(LV_ID)}
        self.assertNotIn("2026-11-26", days)
        self.assertNotIn("2026-11-18", days)

    def test_the_series_words_in_both_languages(self):
        ev = self.moved
        self.assertEqual(ev["i18n"], series_words())
        self.assertEqual((ev["title"], ev["summary"], ev["lang"], ev["machine"]),
                         (LV["title"], LV["summary"], "en", []))
        # the same words as the series' own dates (Jan 28, 2027 …)
        jan = next(e for e in self.evs if e["id"].startswith(LV_ID) and local_day(self.ctx, e) > "2026-11-18")
        for k in ("title", "summary", "lang", "machine"):
            self.assertEqual(ev[k], jan[k], k)
        self.assertEqual((ev["i18n"]["title"], ev["i18n"]["summary"]), (jan["i18n"]["title"], jan["i18n"]["summary"]))

    def test_the_series_key_host_and_room(self):
        ex = self.moved["extra"]
        self.assertEqual((ex["series_of"], ex["host"], ex["online_url"], ex["online"], ex["platform"], ex["meeting_id"],
                          ex["contact"]),
                         (KEY, "lv", LV["online_url"], True, "Zoom", LV["meeting_id"], LV["contact"]))
        self.assertNotIn("series", ex)          # not a date of the rule (no `recurring`, never `later` on the page)
        self.assertNotIn("recurring", ex)

    def test_its_own_day_time_link_and_flyer(self):
        ev, ex = self.moved, self.moved["extra"]
        view = f"https://drive.google.com/file/d/{MOVED_ID}/view"
        self.assertEqual((ev["category"], ev["source"], ev["url"]), ("flyer", "drive", view))
        self.assertEqual((ex["start"], ex["end"], ex["all_day"]),
                         ("2026-11-18T20:00:00Z", "2026-11-18T21:00:00Z", False))       # 2:00–3:00 PM CST
        self.assertEqual((ex["flyer_url"], ex["flyer_thumb"]),
                         (view, f"https://lh3.googleusercontent.com/d/{MOVED_ID}=w600"))
        self.assertEqual((ex["location"], ex["drive_id"]), (None, f"drive:{MOVED_ID}"))

    def test_one_card_that_day(self):
        nov18 = [e for e in self.evs if local_day(self.ctx, e) == "2026-11-18" and e.get("category") != "committee"]
        self.assertEqual([e["id"] for e in nov18], [f"ev:flyer:{MOVED_ID}"])

    def test_the_translation_step_keeps_the_series_words(self):
        """build_data's translation step never machine-translates them again ("Taller Mensual" → "Monthly
        Workshop")."""
        ev = dict(self.moved, i18n=dict(self.moved["i18n"]), _fixed_i18n=True)
        self.assertTrue(self.moved.get("_fixed_i18n"))
        i18n = B.I18n(NoTranslator())
        B.plan_translations(self.ctx, {"events": [ev]}, set(), i18n)
        self.assertEqual(i18n.jobs, {})
        i18n.apply(ev)
        self.assertEqual((ev["i18n"], ev["machine"]), (series_words(), []))
        self.assertNotIn("_fixed_i18n", ev)

    def test_la_vinas_own_listing_of_that_day_shows_once(self):
        """La Viña's calendar listing of Nov 18 (all day, the workshop's Zoom room) is the flyer's day: left out."""
        listing = E.build_item("https://www.aalavina.org/get-involved/events/2026-11-18/taller-mensual",
                               E.decide({"title": "Taller Mensual", "start": "2026-11-18", "all_day": True,
                                         "location_raw": LV["online_url"], "lang": "es"}))
        ctx, evs = build(drive=[SERIES_FLYER, lv_flyer("2026-11-18")], events_external=[listing])
        self.assertEqual([e["id"] for e in evs if e.get("category") == "lv-calendar"], [])
        moved = next(e for e in evs if e["id"] == f"ev:flyer:{MOVED_ID}")
        self.assertEqual((moved["extra"]["also_on_calendar"], moved["extra"]["calendar_match"], moved["title"]),
                         ("lv-calendar", "online", LV["title"]))
        # (no check of ctx.raw_problems here: that judges config/site.yml itself — the committee's file, which the
        # Website update gate's copies edit on purpose: tests/test_automation.py GateLists)


class NothingElseChanges(unittest.TestCase):
    def test_a_flyer_on_a_date_of_the_series_is_that_dates_flyer(self):
        ctx, evs = build(drive=[SERIES_FLYER])
        day = next(local_day(ctx, e) for e in evs if e["id"].startswith(LV_ID) and not e["extra"]["past"])
        fid = "DATED" + day.replace("-", "")
        _ctx, evs = build(drive=[SERIES_FLYER, lv_flyer(day, fid)])
        self.assertEqual([e["id"] for e in evs if e.get("category") == "flyer"], [])
        date_ev = next(e for e in evs if e["id"] == LV_ID + day)
        self.assertEqual(date_ev["extra"]["flyer_url"], f"https://drive.google.com/file/d/{fid}/view")
        self.assertEqual((date_ev["category"], date_ev["title"]), ("recurring", LV["title"]))

    def test_the_committee_meetings_dated_flyers(self):
        """On a meeting's date: that meeting's flyer, no second event. On another day: an event of its own, with
        its own words — no series, no host."""
        ctx, evs = build(drive=[SERIES_FLYER])
        meeting = next(e for e in evs if e.get("category") == "committee" and local_day(ctx, e) > "2026-11-18")
        day = local_day(ctx, meeting)
        other = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
        files = [drive_file(f"{d} Committee Meeting - flyer 7pm-8pm.png", f"CM{d.replace('-', '')}",
                            "Committee Meeting - flyer 7pm-8pm", lang="en", event_date=d,
                            event_title="Committee Meeting - flyer", event_time="19:00", event_end_time="20:00")
                 for d in (day, other)]
        ctx, evs = build(drive=[SERIES_FLYER, *files])
        flyers = [e for e in evs if e.get("category") == "flyer"]
        self.assertEqual([e["id"] for e in flyers], [f"ev:flyer:CM{other.replace('-', '')}"])
        ev = flyers[0]
        self.assertEqual((ev["title"], ev["lang"], ev["summary"]), ("Committee Meeting - flyer", "en", ""))
        for k in ("series_of", "host", "meeting_id", "contact", "platform"):
            self.assertNotIn(k, ev["extra"], k)
        self.assertNotIn("_fixed_i18n", ev)

    def test_a_dated_flyer_of_no_series(self):
        title = "Taller de Escritura de La Viña — Garland"
        f = drive_file(f"2026-12-05 {title} 7pm-9pm.png", "WRITING", f"{title} 7pm-9pm", event_date="2026-12-05",
                       event_title=title, event_time="19:00", event_end_time="21:00")
        _ctx, evs = build(drive=[SERIES_FLYER, f])
        ev = next(e for e in evs if e["id"] == "ev:flyer:WRITING")
        self.assertEqual((ev["title"], ev["lang"], ev["summary"]), (title, "es", ""))
        for k in ("series_of", "host", "online_url", "meeting_id", "contact", "platform"):
            self.assertFalse(ev["extra"].get(k), k)
        self.assertNotIn("_fixed_i18n", ev)            # translated by the build as any flyer is

    def test_a_flyer_of_the_series_in_a_month_the_rule_keeps(self):
        """The flyer's name names the series (unlike a calendar listing, found by its room only): on another day of a
        month whose rule date stands, it is the series' card too — and the rule's date stays (the chair's to
        settle)."""
        ctx, evs = build(drive=[SERIES_FLYER])
        rule = next(local_day(ctx, e) for e in evs if e["id"].startswith(LV_ID) and local_day(ctx, e) > "2026-12-31")
        other = (date.fromisoformat(rule) - timedelta(days=7)).isoformat()
        ctx, evs = build(drive=[SERIES_FLYER, lv_flyer(other, "OTHERDAY")])
        ev = next(e for e in evs if e["id"] == "ev:flyer:OTHERDAY")
        self.assertEqual((ev["title"], ev["i18n"], ev["extra"]["series_of"], ev["extra"]["host"]),
                         (LV["title"], series_words(), KEY, "lv"))
        self.assertIn(LV_ID + rule, {e["id"] for e in evs})

    def test_without_the_series_dates_the_flyer_keeps_its_words(self):
        """recurring_events gave no date (its settings could not be read): the flyer still takes the host and the
        room, as before, and keeps its own words — no series key without the series' words."""
        ctx = ctx_with(drive=[SERIES_FLYER, lv_flyer("2026-11-18")])
        ctx.series = B.recurring_specs(ctx)[0]
        flyers = B.series_dated_flyers(ctx, B.flyer_events(ctx), [], [])
        ev = next(e for e in flyers if e["id"] == f"ev:flyer:{MOVED_ID}")
        self.assertEqual((ev["title"], ev["lang"]), ("Taller Mensual y Virtual de La Viña", "es"))
        self.assertEqual((ev["extra"]["host"], ev["extra"]["online_url"], ev["extra"]["meeting_id"]),
                         ("lv", LV["online_url"], LV["meeting_id"]))
        self.assertNotIn("series_of", ev["extra"])
        self.assertNotIn("_fixed_i18n", ev)

    def test_a_skipped_months_calendar_listing_still_takes_the_series_words(self):
        """series_moved_dates shares the words with series_dated_flyers (_take_series_words): unchanged."""
        listing = E.build_item("https://www.aalavina.org/get-involved/events/2026-11-19/taller-mensual",
                               E.decide({"title": "Taller Mensual", "start": "2026-11-19", "all_day": True,
                                         "location_raw": LV["online_url"], "lang": "es"}))
        _ctx, evs = build(drive=[SERIES_FLYER], events_external=[listing])
        ev = next(e for e in evs if e.get("category") == "lv-calendar")
        self.assertEqual((ev["title"], ev["lang"], ev["machine"], ev["i18n"], ev["extra"]["series_of"]),
                         (LV["title"], "en", [], series_words(), KEY))
        self.assertIs(ev["_fixed_i18n"], True)
        self.assertEqual(ev["extra"]["flyer_url"], f"https://drive.google.com/file/d/{SERIES_FLYER_ID}/view")


PAGE_JS = r"""
const C = await imp("eleventy/filters/committee.js");
const now = new Date(input.now);
const res = {};
for (const lang of ["en", "es"]) {
  const evs = C.normalizeEvents(input.items, input.site, lang, { now });
  const pick = (e) => e && ({ title: e.title, summary: e.summary, ownWords: e.ownWords, seriesOf: e.seriesOf,
    host: e.host, group: e.group, isOnline: e.isOnline, online: e.online, platform: e.platform, meetingId: e.meetingId,
    contact: e.contact, flyer: e.flyer && e.flyer.view, startYmd: e.startYmd, itemLang: e.item.lang });
  res[lang] = { moved: pick(evs.find((e) => e.id === input.moved)), next: pick(evs.find((e) => e.id === input.next)),
                nov18: evs.filter((e) => e.startYmd === "2026-11-18" && !e.committee).map((e) => e.id) };
}
const it = input.items.find((i) => i.id === input.moved);
res.ownLangs = C.ownLangs(it);
out(res);
"""


class OnTheEventsPage(unittest.TestCase):
    """The card /events/ builds of it (eleventy/filters/committee.js normalizeEvents): the series' title and summary
    in each language, no language pill (the English page: its own language; the Spanish page: the committee's own
    words — ownLangs), La Viña's group and colour, "Join online", the meeting ID, the contact and its flyer."""

    def test_the_card(self):
        from nodejs import run_js
        _ctx, evs = build(drive=[SERIES_FLYER, lv_flyer("2026-11-18")])
        for e in evs:
            e.pop("_fixed_i18n", None)
        nxt = next(e["id"] for e in evs if e["id"].startswith(LV_ID) and not e["extra"]["past"])
        site = {"url": "https://grapevine.neta65.org", "meeting": CFG["meeting"],
                "recurring_events": CFG["recurring_events"], "links": {}}
        res = run_js(self, PAGE_JS, data={"items": evs, "site": site, "now": NOW.isoformat().replace("+00:00", "Z"),
                                          "moved": f"ev:flyer:{MOVED_ID}", "next": nxt}, now="2026-11-17T15:00:00Z")
        self.assertEqual(res["ownLangs"], ["es"])
        for lang in ("en", "es"):
            moved, nx = res[lang]["moved"], res[lang]["next"]
            self.assertEqual(res[lang]["nov18"], [f"ev:flyer:{MOVED_ID}"], lang)          # one card that day
            sfx = "" if lang == "en" else "_es"
            self.assertEqual((moved["title"], moved["summary"]), (LV["title" + sfx], LV["summary" + sfx]), lang)
            self.assertEqual((moved["title"], moved["summary"]), (nx["title"], nx["summary"]), lang)
            # no language pill: events.njk shows one when the item's language is not the page's and not ownWords
            self.assertTrue(moved["itemLang"] == lang or moved["ownWords"], lang)
            self.assertEqual((moved["seriesOf"], moved["host"], moved["group"], moved["isOnline"], moved["online"],
                              moved["platform"], moved["meetingId"], moved["contact"], moved["flyer"]),
                             (KEY, "lv", nx["group"], True, LV["online_url"], "Zoom", LV["meeting_id"], LV["contact"],
                              f"https://drive.google.com/file/d/{MOVED_ID}/view"), lang)



class TitleRoute(unittest.TestCase):
    """The moved date keeps being found by the flyer's own words after it took the series': a feed or calendar
    listing of that day under the workshop's Spanish title, with no Zoom link to match the room by (location
    "Online"), is the same event (same_event's "title" route reads the committee's fixed words in both languages:
    _event_titles), never a second card. A machine translation never counts."""

    def moved_and_listing(self, title: str) -> tuple[B.Ctx, dict, dict]:
        ctx = ctx_with(drive=[SERIES_FLYER, lv_flyer("2026-11-18")])
        with mock.patch.object(B.T, "get_translator", lambda **kw: NoTranslator()):
            recurring = B.recurring_events(ctx)
            kept = B.series_dated_flyers(ctx, B.flyer_events(ctx), recurring)
        moved = next(e for e in kept if e["id"] == f"ev:flyer:{MOVED_ID}")
        listing = {"id": "ev:ics:moved", "category": "ics", "title": title, "date": "2026-11-18T20:00:00Z",
                   "extra": {"start": "2026-11-18T20:00:00Z", "end": "2026-11-18T21:00:00Z", "all_day": False,
                             "location": "Online"}}
        return ctx, moved, listing

    def test_a_listing_under_the_series_spanish_title_is_that_days_card(self):
        ctx, moved, listing = self.moved_and_listing(LV["title_es"])
        self.assertEqual(moved["title"], LV["title"])            # it took the series' (English) title …
        self.assertIn(LV["title_es"], B._event_titles(moved))     # … and is still found by the Spanish one
        self.assertEqual(B.same_event(ctx, moved, listing), "title")

    def test_machine_words_never_count(self):
        ev = {"title": "Monthly Workshop", "i18n": {"title": {"en": "Monthly Workshop", "es": "Taller mensual (máquina)"}}}
        self.assertEqual(B._event_titles(ev), ["Monthly Workshop"])
        ev["_fixed_i18n"] = True
        self.assertEqual(B._event_titles(ev), ["Monthly Workshop", "Taller mensual (máquina)"])

if __name__ == "__main__":
    unittest.main()
