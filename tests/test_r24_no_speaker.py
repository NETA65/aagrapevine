"""Round 24 · the committee meetings with NO guest speaker: November 18 and December 16, 2026 (the guest speakers start
on January 20, 2027 — config/site.yml `meeting: speakers:`), in the chair's decks and in the orientation:

  * Facts      — the code: eleventy/filters/presentations.js liveFacts at fixed clocks, from the test's own copy of
                 the settings (the speakers from January 20, 2027 to December 15, 2027): a meeting the list gives no
                 speaker says so ("none tonight", "none this time", "no guest speaker this month", the chair's notes
                 which version to choose), never "to be announced" — that is only for a speaker the list doesn't
                 name yet: a month after its last one (January 2028), or a month whose entry the site leaves out (a
                 full last name); an empty list has no speakers at all. The paperwork's meetings carry `no_speaker`
                 for those dates (the sample committee meeting of tests/fixtures/presentations).
The others judge what the committee edits (scripts/ops/gate_tests.py CONTENT_TESTS): the real settings, the
committee's deck and the lessons —
  * Deck       — the committee meeting's deck as the build writes it (deckJson) and the player draws it
                 (presentations-core.js): the "Next meeting" slide on November 11 and 18 says "Guest speaker: none
                 this time" (December 16), in every version, and January's speaker from midnight after November 18
                 (a copy opened later too); the version notes name every meeting before January 20, 2027, in
                 English and Spanish; on January 10, 2027 no slide or note of any version reads "Rick W.." (a
                 name ends with its own period).
  * Paperwork  — the agenda e-mail of November 18 in the first version: its row "Guest speaker: none at this
                 meeting" and the panel's warning (speakerNone), none in "No guest speaker" (and no warning that a
                 listed speaker is left out); "Start next month" after November 18 goes to "No guest speaker" by
                 itself (its Undo too, also after a reload), and after December 16 back to the first version.
  * Wording    — /orientation/role/ (and its handout), the orientation, information and writing workshops: "a guest
                 speaker each month" only with "from January 2027".

Every test runs at a FIXED clock (run_js now=…): nothing here depends on the day the tests run.

    python -m unittest tests.test_r24_no_speaker -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, node_path, run_js  # noqa: E402

TBA = "to be announced"
# The committee meeting's settings as config/site.yml has them on November 11, 2026 — the test's own copy, so the
# code is judged here, not the list (Deck and Paperwork read the real one): on Google Meet, its guest speakers from
# January 20, 2027 (the list's first) to December 15, 2027 (its last; the months between them without one here)
MEETING = {
    "week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet",
    "online_url": "https://meet.google.com/rva-tmst-vdb", "meeting_id": "rva-tmst-vdb", "speaker_until": "19:30",
    "speakers": [
        {"date": "2027-01-20", "name": "Rick W.", "confirmed": True, "position": "Past delegate, Area 65 (Panel 73)",
         "topic": "Grapevine as a Twelfth Step tool"},
        {"date": "2027-02-17", "name": "Jeannie M.", "confirmed": True, "position": "Past delegate, Area 4 (Panel 73)",
         "topic": "Grapevine and La Viña as Public Information tools"},
        {"date": "2027-12-15", "name": "Pat E.", "confirmed": False, "position": "Past delegate", "topic": "Holidays"},
    ]}
SITE = {"url": "https://neta65.github.io/aagrapevine", "contact_email": "grapevine@neta65.org",
        "committee": "NETA 65 Grapevine & La Viña Committee", "meeting": MEETING}
RICK_X, FEB_X = MEETING["speakers"][0], MEETING["speakers"][1]

# The clocks: today (November 11, 2026, a week before the November meeting), midnight Central after November 18
# (December 16 is then the meeting's day), the next day, January 10, 2027, and December 20, 2027 (the list ends with
# December 15, 2027: January 19, 2028 is not listed yet)
NOV11 = "2026-11-11T18:00:00Z"
NOV18_OVER = "2026-11-19T06:00:00.000Z"
NOV19 = "2026-11-19T15:00:00Z"
NOV18_AFTER = "2026-11-19T02:30:00Z"     # 8:30 PM Central, the November meeting over
DEC16_OVER = "2026-12-17T06:00:00.000Z"
DEC16_AFTER = "2026-12-17T02:30:00Z"
JAN10 = "2027-01-10T18:00:00Z"
DEC20_2027 = "2027-12-20T18:00:00Z"

FACTS_JS = r"""
const P = await imp("eleventy/filters/presentations.js");
const site = input.site;
const at = new Date(input.now);
const facts = (s) => P.liveFacts({ db: {}, site: s, carry: {}, meeting: { upcoming: [] }, now: at });
const variant = (speakers) => ({ ...site, meeting: { ...site.meeting, speakers } });
const deck = P.loadDecks("tests/fixtures/presentations").decks.find((d) => d.id === "sample-meeting");
const rows = P.deckJson(deck, { db: {}, site, carry: {}, meeting: { upcoming: [] }, now: at }).paperwork.meetings;
// a February entry the site leaves out (a full last name); no list at all
const feb = site.meeting.speakers.map((s) => (s.date === "2027-02-17" ? { ...s, name: "Jeannie Example" } : s));
out({ live: facts(site), fullName: facts(variant(feb)), empty: facts(variant([])), rows,
      noSpeaker: P.NO_SPEAKER, fallbacks: P.FALLBACKS });
"""


def live_at(v, when: str) -> str:
    """A {live:…} value at an instant (ISO), as the player reads it (presentations-core.js liveText)."""
    if isinstance(v, str):
        return v
    val = v["value"]
    for st in v.get("steps", []):
        if st["from"] <= when:
            val = st["value"]
    if v.get("until") and v["until"] <= when:
        val = ""
    return val or v.get("fallback", "")


def iso(now: str) -> str:
    return now.replace("Z", ".000Z") if "." not in now else now


class Facts(unittest.TestCase):
    """The speaker facts from the test's own copy of the committee's list of guest speakers (MEETING: its first, its
    second and a last one), so the code is judged here, not the list."""

    cache: dict = {}

    def facts(self, now: str) -> dict:
        if not node_path():
            self.skipTest("Node.js is not installed")
        if now not in Facts.cache:
            Facts.cache[now] = run_js(self, FACTS_JS, data={"now": now, "site": SITE}, now=now)
        return Facts.cache[now]

    def test_november_18_and_december_16_have_none(self):
        r = self.facts(NOV11)
        live, ns = r["live"], r["noSpeaker"]
        at = lambda k, t=iso(NOV11): live_at(live[k], t)  # noqa: E731
        self.assertEqual(at("meeting_day"), "Wednesday, November 18, 2026")
        # tonight's (the title slide's meeting: November 18), then December 16's, then January 20's
        for k, v in (("speaker_name", "none tonight"), ("speaker_line", "none tonight"), ("speaker_topic", "none"),
                     ("speaker_position", "the Meetings page lists no guest speaker for this meeting")):
            self.assertEqual([at(k), at(k, NOV18_OVER)], [v, v], k)
        self.assertEqual(at("speaker_name", DEC16_OVER), RICK_X["name"])
        self.assertEqual(at("speaker_note"), "no guest speaker this month", "the Grapevine Meeting's announcement")
        self.assertTrue(at("speaker_slides").startswith("No guest speaker is listed for tonight: choose the version 'No guest speaker'"))
        # next month's, on the "Next meeting" slide: December 16 (none), then January 20 from midnight after November 18
        self.assertEqual(at("meeting_after"), "Wednesday, December 16, 2026")
        self.assertEqual(at("speaker_after"), "none this time")
        self.assertEqual(at("speaker_after", NOV18_OVER), f"{RICK_X['name']} — “{RICK_X['topic']}”")
        # never "to be announced" for a meeting the list gives none
        for k in ns:
            self.assertNotEqual(at(k), TBA, k)
            self.assertNotEqual(at(k, NOV18_OVER), TBA, k)
        self.assertEqual(ns["speaker_after"], "none this time")
        self.assertEqual(r["fallbacks"]["speaker_after"], TBA, "the fallback stays for a speaker not listed yet")

    def test_the_day_after_november_18(self):
        live = self.facts(NOV19)["live"]
        now = iso(NOV19)
        self.assertEqual(live_at(live["meeting_day"], now), "Wednesday, December 16, 2026")
        self.assertEqual(live_at(live["speaker_name"], now), "none tonight")
        self.assertEqual(live_at(live["speaker_note"], now), "no guest speaker this month")
        self.assertEqual(live_at(live["speaker_after"], now), f"{RICK_X['name']} — “{RICK_X['topic']}”")

    def test_january_20_has_rick_w(self):
        live = self.facts(JAN10)["live"]
        now = iso(JAN10)
        self.assertEqual(live_at(live["meeting_day"], now), "Wednesday, January 20, 2027")
        self.assertEqual(live_at(live["speaker_name"], now), "Rick W.")
        self.assertEqual(live_at(live["speaker_line"], now), f"Rick W. — {RICK_X['position']}")
        self.assertEqual(live_at(live["speaker_note"], now), "guest speaker: Rick W.")
        self.assertEqual(live_at(live["speaker_after"], now), f"{FEB_X['name']} — “{FEB_X['topic']}”")

    def test_a_speaker_not_listed_yet_is_to_be_announced(self):
        # December 15, 2027 is the list's last meeting: January 19, 2028 is not known yet
        r = self.facts(DEC20_2027)
        now = iso(DEC20_2027)
        self.assertEqual(live_at(r["live"]["meeting_day"], now), "Wednesday, January 19, 2028")
        for k in ("speaker_name", "speaker_position", "speaker_topic", "speaker_line", "speaker_after"):
            self.assertEqual(live_at(r["live"][k], now), TBA, k)
        self.assertEqual(live_at(r["live"]["speaker_note"], now), "guest speaker: to be announced")
        self.assertTrue(live_at(r["live"]["speaker_slides"], now).startswith("No slides are listed for tonight's guest speaker"))
        # …and a month whose entry the site leaves out (a full last name): there is a speaker, not shown
        r = self.facts(JAN10)
        self.assertEqual(live_at(r["fullName"]["speaker_after"], iso(JAN10)), TBA)
        self.assertEqual(live_at(r["fullName"]["speaker_name"], iso(JAN10)), "Rick W.")

    def test_no_list_at_all_means_no_guest_speakers(self):
        live = self.facts(NOV11)["empty"]
        now = iso(NOV11)
        self.assertEqual(live_at(live["speaker_name"], now), "none tonight")
        self.assertEqual(live_at(live["speaker_after"], now), "none this time")
        self.assertEqual(live_at(live["speaker_note"], now), "no guest speaker this month")

    def test_the_paperwork_knows_which_meetings_have_none(self):
        rows = {x["ymd"]: x for x in self.facts(NOV11)["rows"]}
        for ymd in ("2026-11-18", "2026-12-16"):
            self.assertIs(rows[ymd].get("no_speaker"), True, ymd)
            self.assertNotIn("speaker", rows[ymd], ymd)
        self.assertEqual(rows["2027-01-20"]["speaker"]["name"], "Rick W.")
        self.assertNotIn("no_speaker", rows["2027-01-20"])
        # a month the list doesn't reach yet: neither
        late = {x["ymd"]: x for x in self.facts(DEC20_2027)["rows"]}
        self.assertNotIn("no_speaker", late["2028-01-19"])
        self.assertNotIn("speaker", late["2028-01-19"])


# The committee's deck as the build writes it and the player draws it (the real settings, the build's clock `now`)
DECK_JS = r"""
import vm from "node:vm";
const P = await imp("eleventy/filters/presentations.js");
const site = (await imp("src/_data/site.js")).default();
const loaded = P.loadDecks("config/presentations");
const D = JSON.parse(JSON.stringify(P.deckJson(loaded.decks.find((d) => d.id === "committee-meeting"),
  { site, db: {}, carry: {}, meeting: { upcoming: [] } })));
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/presentations-core.js", "utf8"), ctx, { filename: "presentations-core.js" });
const G = ctx.GVP;
const ms = (s) => Date.parse(s);
const plain = (v) => JSON.parse(JSON.stringify(v));
const draw = (st, preset, at, id, where) => {
  const cur = G.current(D, st, preset, ms(at));
  const s = cur.byId[id];
  if (!s) return null;
  const T = (t) => G.plain(G.rich(t, { deck: D, state: st, live: cur.live, cur, where: where || "slide", lang: "en" }));
  return { shown: s.shown, title: T(s.slide.title || ""), items: (s.slide.items || []).map(T),
           notes: G.noteLines(s.slide.notes || "", cur.preset.id).map((l) => (l.label ? l.label + " " : "") + T(l.text)) };
};
"""


def real_speaker(ymd: str) -> dict:
    """A guest speaker of the committee's real list (config/site.yml meeting.speakers)."""
    cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
    return next(x for x in cfg["meeting"]["speakers"] if x["date"] == ymd)


class Deck(unittest.TestCase):
    """The committee meeting's slides on November 11 and 19, 2026 and January 10, 2027 (the real settings)."""

    def run_deck(self, js: str, clock: str, **data):
        if not node_path():
            self.skipTest("Node.js is not installed")
        return run_js(self, DECK_JS + js, data={"now": clock, **data}, now=clock)

    def test_the_next_meeting_slide_says_december_has_none(self):
        r = self.run_deck("""
            const st = G.emptyState();
            out({ full: draw(st, "", input.now, "next-meeting"), none: draw(st, "no-speaker", input.now, "next-meeting"),
                  topic: draw(st, "topic", input.now, "next-meeting"), later: draw(st, "", input.later, "next-meeting"),
                  intro: draw(st, "", input.now, "speaker-intro"), talk: draw(st, "", input.now, "speaker-talk"),
                  title: draw(st, "", input.now, "title", "notes"),
                  thanks: draw(st, "", input.now, "speaker-thanks", "notes"),
                  presets: D.presets.map((p) => ({ id: p.id, note: p.note })) });""",
            NOV11, later=NOV19)
        for v in ("full", "none", "topic"):
            self.assertTrue(r[v]["shown"], v)
            self.assertTrue(r[v]["items"][0].startswith("Wednesday, December 16, 2026"), r[v]["items"][0])
            self.assertEqual(r[v]["items"][1], "Guest speaker: none this time", v)
        self.assertIn("Our guest speaker next month: none this time.", " ".join(r["full"]["notes"]))
        # a copy made on November 11, opened on November 19: January's speaker
        self.assertTrue(r["later"]["items"][0].startswith("Wednesday, January 20, 2027"))
        rick = real_speaker("2027-01-20")
        self.assertEqual(r["later"]["items"][1], f"Guest speaker: {rick['name']} — “{rick['topic']}”")
        # the guest speaker's slide in the first version: none tonight (the version to choose is in the notes)
        self.assertEqual(r["intro"]["items"], ["none tonight", "the Meetings page lists no guest speaker for this meeting",
                                               "Topic: none"])
        self.assertEqual(r["talk"]["title"], "Our guest speaker: none tonight")
        notes = " ".join(r["title"]["notes"])
        self.assertIn("TONIGHT'S GUEST SPEAKER (from the Meetings page): none tonight; if there is none", notes)
        self.assertIn("No guest speaker is listed for tonight: choose the version 'No guest speaker'", notes)
        self.assertNotIn("December 16, 2026, or the speaker", notes)
        self.assertIn("Next month's guest speaker: none this time.", " ".join(r["thanks"]["notes"]))
        # the version notes: every meeting before January 20, 2027, in English and Spanish
        notes = {p["id"]: p["note"] for p in r["presets"]}
        for pid in ("full", "no-speaker"):
            self.assertIn("before January 20, 2027", notes[pid]["en"], pid)
            self.assertIn("antes del 20 de enero de 2027", notes[pid]["es"], pid)
            self.assertNotIn("December 16", notes[pid]["en"], pid)
            self.assertNotIn("16 de diciembre", notes[pid]["es"], pid)

    def test_january_names_its_speaker(self):
        r = self.run_deck("""
            const st = G.emptyState();
            const every = (preset) => D.slides.map((s) => s.id).map((id) => [id, draw(st, preset, input.now, id, "notes")])
              .filter(([, d]) => d && d.shown);
            out({ intro: draw(st, "", input.now, "speaker-intro"), next: draw(st, "", input.now, "next-meeting"),
                  title: draw(st, "", input.now, "title", "notes"),
                  all: Object.fromEntries(D.presets.map((p) => [p.id, every(p.id)])) });""",
            JAN10)
        rick, feb = real_speaker("2027-01-20"), real_speaker("2027-02-17")
        self.assertEqual(r["intro"]["items"][:2], [rick["name"], rick["position"]])
        self.assertEqual(r["next"]["items"][1], f"Guest speaker: {feb['name']} — “{feb['topic']}”")
        self.assertIn(f"TONIGHT'S GUEST SPEAKER (from the Meetings page): {rick['name']}; if there is none",
                      " ".join(r["title"]["notes"]))
        # a name ends with its own period ("Rick W."): never "Rick W.." after it, on a slide or in its notes, in
        # every version
        stop = re.compile(r"[A-Z]\.\.(?!\.)")
        cfg = yaml.safe_load((ROOT / "config" / "presentations" / "committee-meeting.yml").read_text(encoding="utf-8"))
        self.assertEqual(sorted(r["all"]), sorted(p["id"] for p in cfg["presets"]))
        for pid, slides in r["all"].items():
            self.assertTrue(slides, pid)
            for sid, d in slides:
                for line in [d["title"], *d["items"], *d["notes"]]:
                    with self.subTest(version=pid, slide=sid):
                        self.assertNotRegex(line, stop, line[:160])


class Paperwork(unittest.TestCase):
    """The chair's paperwork for November 18 and "Start next month" after it."""

    def run_paper(self, js: str, now: str = NOV11, **data):
        if not node_path():
            self.skipTest("Node.js is not installed")
        return run_js(self, DECK_JS + js, data={"now": now, **data}, now=now)

    def test_the_agenda_of_november_18(self):
        r = self.run_paper("""
            const texts = (preset) => { const st = G.emptyState(); G.deckState(st, D.id).preset = preset;
              const cur = G.current(D, st, "", ms(input.now));
              const o = {}; for (const w of G.PAPER_TEXTS) o[w] = plain(G.paperText(D, st, cur, w, ms(input.now)));
              return o; };
            out({ full: texts(""), none: texts("no-speaker"), without: plain(G.noSpeakerPreset(D)).id });""", now=NOV11)
        full, none = r["full"], r["none"]
        self.assertEqual(full["agenda"]["meeting"]["ymd"], "2026-11-18")
        self.assertIn("\n7:02  Guest speaker: none at this meeting\n", full["agenda"]["text"])
        self.assertTrue(full["agenda"]["speakerNone"], "the panel warns: the first version keeps the speaker's part")
        self.assertFalse(full["reminder"]["speakerNone"], "the agenda e-mail's word only: the reminder names no speaker")
        self.assertFalse(full["minutes"]["speakerNone"])
        self.assertEqual(r["without"], "no-speaker", "the version the warning names")
        for w in ("agenda", "reminder"):
            self.assertNotIn(TBA, full[w]["text"], w)
            self.assertNotIn("Guest speaker:", full[w]["text"].split("Agenda (Central time)")[0], w)
            self.assertNotIn("Orador(a) invitado(a)", full[w]["text"], w)
            # "No guest speaker": no speaker at all, and no warning either way
            self.assertNotIn("Guest speaker", none[w]["text"], w)
            self.assertFalse(none[w]["speakerNone"], w)
            self.assertEqual(none[w]["speakerLeftOut"], "", w)

    def test_start_next_month_picks_the_version(self):
        r = self.run_paper("""
            const st = G.emptyState();
            const ds = G.deckState(st, D.id);
            // after November 18, in the first version: December 16 has no guest speaker
            const nov = plain(G.startNextMonth(D, st, [], ms(input.nov)));
            const afterNov = ds.preset;
            const stored = plain(G.normState(JSON.parse(JSON.stringify(st))).decks[D.id].prev);
            const reloaded = G.normState(JSON.parse(JSON.stringify(st)));
            G.undoNextMonth(D, reloaded);
            const undone = reloaded.decks[D.id].preset;
            // after December 16, in "No guest speaker": January 20 has Rick W.
            const st2 = G.emptyState(); G.deckState(st2, D.id).preset = "no-speaker";
            const dec = plain(G.startNextMonth(D, st2, [], ms(input.dec)));
            // after November 18, already in "No guest speaker": nothing to change
            const st3 = G.emptyState(); G.deckState(st3, D.id).preset = "no-speaker";
            const kept = plain(G.startNextMonth(D, st3, [], ms(input.nov)));
            out({ nov, afterNov, stored, undone, dec, decPreset: st2.decks[D.id].preset, kept, keptPreset: st3.decks[D.id].preset });""",
            now=NOV11, nov=NOV18_AFTER, dec=DEC16_AFTER)
        self.assertEqual((r["nov"]["version"], r["afterNov"]), ("without", "no-speaker"))
        self.assertEqual(r["stored"]["preset"], "", "the first version, kept for the Undo after a reload")
        self.assertEqual(r["undone"], "")
        self.assertEqual((r["dec"]["version"], r["decPreset"]), ("reset", ""))
        self.assertEqual((r["kept"]["version"], r["keptPreset"]), ("", "no-speaker"))


# A line that says the committee meeting has a guest speaker every month must say from when
CLAIM = re.compile(r"(?i)guest speaker each month|(?:each|every) meeting opens with a guest speaker|a guest speaker first|"
                   r"with a guest speaker\"|a guest speaker, then|primero la charla|cada reunión empieza con|"
                   r"primero habla un\(a\) orador")


class Wording(unittest.TestCase):
    """A claim that every meeting has a guest speaker says "from January 2027": the meetings before it have none."""

    def test_the_orientation_role_lesson(self):
        lessons = {l["id"]: l for l in yaml.safe_load((ROOT / "config" / "orientation.yml").read_text(encoding="utf-8"))["lessons"]}
        point = next(p for p in lessons["role"]["points"] if p["title"]["en"] == "Our committee meets every month")
        self.assertIn("From January 2027 each meeting opens with a guest speaker", point["text"]["en"])
        self.assertIn("Desde enero de 2027", point["text"]["es"])
        self.assertNotIn("a guest speaker first", point["text"]["en"])

    def test_the_decks_and_the_lessons(self):
        files = sorted((ROOT / "config" / "presentations").glob("*.yml")) + [ROOT / "config" / "orientation.yml"]
        for f in files:
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if CLAIM.search(line):
                    with self.subTest(file=f.name, line=n):
                        self.assertRegex(line, r"January 2027|enero de 2027", line.strip()[:160])


if __name__ == "__main__":
    unittest.main()
