"""The version a presentation opens on when the presenter has chosen none (src/assets/js/presentations-core.js
defaultPreset / presetFor / speakerMeeting, src/assets/js/presentations.js), run in Node.js:

  * Default   — a small deck with the chair's paperwork (its meetings: two the site lists NO guest speaker for, one
                with a speaker, one whose speaker is only "to be announced"): with no version chosen it opens on
                "No guest speaker" for a meeting with none — a week before, during it and after it until midnight
                Central after its day, as the speaker facts ({live:speaker_…}) are tonight's until then, whatever
                "Start next month" did — and on the first version for a listed speaker and for one to be
                announced; a deck without paperwork, its first version; a deck file from before the build wrote
                each meeting's `over`, the same. A reload at 8:02 PM shows the slides it showed at 7:58 PM.
  * Chosen    — a version the presenter chose (the first one too, by its id) is never changed by the clock,
                survives a reload (normState) and a "my version" file, and counts as a change (the page's status
                line and Reset); an unknown one is the default. The texts (paperText) and an edit (setField)
                follow the version shown.
  * OldState  — what "Start next month" stored before December 2026 after November 18 ("No guest speaker" by
                itself, "" kept for its Undo) is none chosen: January 20 opens with its speaker, and a version picked
                after it stays.
  * Start next month — pressed at 7:55 PM on December 16 on an empty profile, nothing changes; with "No guest
                speaker" chosen, the version goes back to none chosen: tonight's slides until midnight, January's
                speaker's after.
  * Player    — the player stores the version picked by its id and the one the deck opens on by itself as none
                chosen, keeps a choice on the device, says "Chosen for you" for the default, in English and Spanish.

Every test runs at a FIXED clock and on the test's own deck: nothing here depends on the day the tests run, nor on
the committee's files. The real committee deck of December 16, 2026 (config/site.yml's speakers):
tests/test_r24_no_speaker.py Deck.test_december_16_opens_without_the_guest_speaker (it judges those files: a
CONTENT_TESTS entry of scripts/ops/gate_tests.py). The browser's side: tests/browser/test_deck_default_version.py.

    python -m unittest tests.test_presentations_default_version -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, node_path, run_js  # noqa: E402

CORE = "src/assets/js/presentations-core.js"

# A committee meeting's deck in the shape the build writes it (paperwork.meetings: rows with ymd, start, end, `over`
# — midnight Central after the day —, labels and the speaker facts): November 18 and December 16, 2026 have no guest
# speaker (no_speaker), January 20, 2027 has one, February 17, 2027 is still to be announced (neither)
ROWS = [
    {"ymd": "2026-11-18", "start": "2026-11-19T01:00:00.000Z", "end": "2026-11-19T02:00:00.000Z",
     "over": "2026-11-19T06:00:00.000Z",
     "label": "Wednesday, November 18, 2026", "label_es": "miércoles, 18 de noviembre de 2026", "month": "November 2026",
     "no_speaker": True},
    {"ymd": "2026-12-16", "start": "2026-12-17T01:00:00.000Z", "end": "2026-12-17T02:00:00.000Z",
     "over": "2026-12-17T06:00:00.000Z",
     "label": "Wednesday, December 16, 2026", "label_es": "miércoles, 16 de diciembre de 2026", "month": "December 2026",
     "no_speaker": True},
    {"ymd": "2027-01-20", "start": "2027-01-21T01:00:00.000Z", "end": "2027-01-21T02:00:00.000Z",
     "over": "2027-01-21T06:00:00.000Z",
     "label": "Wednesday, January 20, 2027", "label_es": "miércoles, 20 de enero de 2027", "month": "January 2027",
     "speaker": {"name": "Pat E.", "position": "Past delegate", "topic": "Carrying the message"}},
    {"ymd": "2027-02-17", "start": "2027-02-18T01:00:00.000Z", "end": "2027-02-18T02:00:00.000Z",
     "over": "2027-02-18T06:00:00.000Z",
     "label": "Wednesday, February 17, 2027", "label_es": "miércoles, 17 de febrero de 2027", "month": "February 2027"},
]
NOV18_AFTER = "2026-11-19T02:30:00.000Z"    # 8:30 PM Central, the November meeting over
DEC9 = "2026-12-09T18:00:00.000Z"           # a week before December 16
DEC16_DURING = "2026-12-17T01:45:00.000Z"   # 7:45 PM Central: the meeting is on
DEC16_755 = "2026-12-17T01:55:00.000Z"      # 7:55 PM
DEC16_758 = "2026-12-17T01:58:00.000Z"      # 7:58 PM
DEC16_802 = "2026-12-17T02:02:00.000Z"      # 8:02 PM: the meeting is over, its day is not
DEC16_2359 = "2026-12-17T05:59:00.000Z"     # 11:59 PM
DEC17 = "2026-12-17T06:00:00.000Z"          # midnight Central after December 16: January 20's speaker from now
JAN20_655 = "2027-01-21T00:55:00.000Z"      # 6:55 PM on January 20, 2027
FEB10 = "2027-02-10T18:00:00.000Z"          # a week before February 17 (to be announced)
NONE = {"id": "no-speaker", "slides": ["welcome", "topic", "close"]}
FULL = {"id": "full", "slides": ["welcome", "speaker", "close"]}


def slide(sid: str, title: str, **extra) -> dict:
    s = {"id": sid, "layout": "title", "h": "h-" + sid, "part": None, "accent": "gv", "eyebrow": "Sample", "title": title,
         "notes": "", "minutes": 1, "optional": False, "starts_off": False, "facilitator": False, "handout": False,
         "version_notes": {}, "show_from": None, "show_until": None, "when": None, "data": None}
    s.update(extra)
    return s


def deck(rows: list | None = None, **over) -> dict:
    d = {"app": "gv-presentation", "id": "sample-meeting", "title": "Sample committee meeting", "short": "Sample",
         "version": "v1", "built": "2026-11-26T12:00:00.000Z", "minutes": 60, "live": {}, "fillins": [],
         "presets": [{"id": "full", "label": {"en": "With a guest speaker", "es": "Con orador(a) invitado(a)"}, "hide": []},
                     {"id": "no-speaker", "label": {"en": "No guest speaker", "es": "Sin orador(a) invitado(a)"},
                      "only": ["welcome", "topic", "close"]}],
         "slides": [slide("welcome", "Welcome"), slide("speaker", "Welcome to our guest speaker"),
                    slide("topic", "Tonight's topic", starts_off=True), slide("close", "Thank you")],
         "paperwork": {"speaker_slide": "speaker", "meetings": rows if rows is not None else ROWS,
                       "agenda": {"subject": "Agenda: {paper:meeting}", "body": "Agenda\n{paper:agenda}\n\nGuest speaker: {paper:speaker}"},
                       "next_month": {"actions": [], "old_business": [], "clear": [], "untick": []}}}
    d.update(over)
    return d


PRELUDE = r"""
import vm from "node:vm";
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync(%s, "utf8"), ctx, { filename: "presentations-core.js" });
const G = ctx.GVP;
const ms = (s) => Date.parse(s);
const plain = (v) => JSON.parse(JSON.stringify(v));
const D = input.deck;
const state = (preset, extra) => { const st = G.emptyState(); const ds = G.deckState(st, D.id); if (preset !== undefined) ds.preset = preset;
  Object.assign(ds, extra || {}); return st; };
const shows = (st, at, d) => { const cur = G.current(d || D, st, "", ms(at)); return { id: cur.preset.id, slides: cur.shown.map((e) => e.id) }; };
// what "Start next month" stored before December 2026, pressed after November 18 in the first version
const OLD = { v: 1, shared: { fill: {} }, decks: { "sample-meeting": { preset: "no-speaker",
  prev: { at: "2026-11-19T02:30:00.000Z", held: "2026-11-18", fill: {}, checks: {}, preset: "" } } } };
""" % json.dumps(CORE)


class Case(unittest.TestCase):
    def run_core(self, js: str, rows: list | None = None, **data):
        if not node_path():
            self.skipTest("Node.js is not installed")
        return run_js(self, PRELUDE + js, data={"deck": deck(rows), **data}, needs_modules=False)


class Default(Case):
    def test_no_version_chosen_follows_the_speaker_facts(self):
        r = self.run_core("""
            const st = state();
            const at = (w) => shows(st, w);
            out({ dec9: at(input.dec9), during: at(input.during), at802: at(input.at802), late: at(input.late),
                  dec17: at(input.dec17), feb: at(input.feb),
                  plain: shows(state(), input.dec9, Object.assign({}, D, { paperwork: undefined })),
                  stored: G.deckState(st, D.id).preset, row: G.speakerMeeting(D, ms(input.at802)).ymd,
                  def: G.defaultPreset(D, G.deckState(st, D.id), ms(input.dec9)).id });""",
            dec9=DEC9, during=DEC16_DURING, at802=DEC16_802, late=DEC16_2359, dec17=DEC17, feb=FEB10)
        self.assertEqual(r["dec9"], NONE, "a week before a meeting with no guest speaker")
        self.assertEqual(r["during"], NONE, "while it is on")
        self.assertEqual(r["at802"], NONE, "after it: the speaker facts are tonight's until midnight")
        self.assertEqual(r["late"], NONE, "11:59 PM")
        self.assertEqual(r["row"], "2026-12-16")
        self.assertEqual(r["dec17"], FULL, "from midnight: January 20 has a speaker")
        self.assertEqual(r["feb"], FULL, "a speaker only to be announced: never switched")
        self.assertEqual(r["plain"], FULL, "a deck without the chair's paperwork: its first version")
        self.assertEqual(r["def"], "no-speaker")
        self.assertEqual(r["stored"], "", "the default is worked out, never stored")

    def test_a_reload_after_the_meeting_shows_the_same_slides(self):
        """The chair on a slide at 7:58 PM reloads at 8:02 PM: the same version, the same slides, the same numbers."""
        r = self.run_core("""
            const before = G.current(D, state(), "", ms(input.at758)), after = G.current(D, state(), "", ms(input.at802));
            const n = (cur) => cur.shown.map((e) => e.id + ":" + e.n);
            out({ before: n(before), after: n(after) });""", at758=DEC16_758, at802=DEC16_802)
        self.assertEqual(r["after"], r["before"])

    def test_start_next_month_never_moves_the_default(self):
        """ds.prev.held (the meeting "Start next month" closed) moves the paperwork on, never the version shown."""
        r = self.run_core("""
            const closed = state(undefined, { prev: { at: input.during, held: "2026-12-16", fill: {}, checks: {} } });
            out({ closed: shows(closed, input.during), open: shows(state(), input.during),
                  agenda: G.paperMeetings(D, G.deckState(closed, D.id), ms(input.during)).next.ymd });""", during=DEC16_DURING)
        self.assertEqual((r["closed"], r["open"]), (NONE, NONE))
        self.assertEqual(r["agenda"], "2027-01-20", "the agenda e-mail is next month's at once")

    def test_a_deck_file_without_the_days_end(self):
        """A deck file from before the build wrote `over`: its day ends at 6 AM UTC the day after (midnight Central
        in winter)."""
        rows = [{k: v for k, v in r.items() if k != "over"} for r in ROWS]
        r = self.run_core("out({ at802: shows(state(), input.at802), dec17: shows(state(), input.dec17) });", rows,
                          at802=DEC16_802, dec17=DEC17)
        self.assertEqual((r["at802"], r["dec17"]), (NONE, FULL))


class Chosen(Case):
    def test_a_version_chosen_stays(self):
        r = self.run_core("""
            const full = state("full"), none = state("no-speaker"), odd = state("gone-version");
            const reloaded = G.normState(JSON.parse(JSON.stringify(full)));
            const file = G.exportVersion(D, full, "2026-12-01T00:00:00Z");
            const fileNone = G.exportVersion(D, state(), "2026-12-01T00:00:00Z");
            const back = G.validateImport(JSON.stringify(file), D);
            const sum = G.summary(full.decks[D.id], D), sumNone = G.summary(state().decks[D.id], D);
            out({ full: shows(full, input.dec9), none: shows(none, input.jan), reloaded: shows(reloaded, input.dec9),
                  odd: shows(odd, input.dec9), file: file.preset, fileNone: fileNone.preset,
                  back: back.ok ? back.data.deck.preset : null, sum: [sum.preset, sum.changed], sumNone: [sumNone.preset, sumNone.any],
                  sumOdd: G.summary(odd.decks[D.id], D).preset });""",
            dec9=DEC9, jan="2027-01-10T18:00:00.000Z")
        self.assertEqual(r["full"]["id"], "full", "the first version chosen, by its id: kept on December 16")
        self.assertEqual(r["none"]["id"], "no-speaker", "No guest speaker chosen: kept in January too")
        self.assertEqual(r["reloaded"]["id"], "full", "after a reload")
        self.assertEqual(r["odd"]["id"], "no-speaker", "a version the deck no longer has: the default")
        self.assertEqual((r["file"], r["fileNone"]), ("full", ""), "a 'my version' file keeps the choice, or none")
        self.assertEqual(r["back"], "full", "and opening the file gives it back")
        self.assertEqual(r["sum"], ["full", True], "the first version chosen is a change: the status line and Reset")
        self.assertEqual(r["sumNone"], ["", False], "none chosen is none")
        self.assertEqual(r["sumOdd"], "", "nor a version the deck no longer has")

    def test_the_texts_and_an_edit_follow_the_version_shown(self):
        r = self.run_core("""
            const st = state();
            const cur = G.current(D, st, "", ms(input.dec9));
            const agenda = G.paperText(D, st, cur, "agenda", ms(input.dec9));
            // an edit of a field with words of its own per version, made with no version named: in the one shown
            D.slides[0].version_fields = { full: { title: "Welcome (full)" }, "no-speaker": { title: "Welcome (no speaker)" } };
            G.setField(D, G.deckState(st, D.id), "welcome", "title", "My welcome");
            const edit = plain(G.deckState(st, D.id).edits.welcome);
            out({ text: agenda.text, none: agenda.speakerNone, left: agenda.speakerLeftOut, meeting: agenda.meeting.ymd, edit });""",
            dec9=DEC9)
        self.assertEqual(r["meeting"], "2026-12-16")
        self.assertFalse(r["none"], "no warning: the version shown has no speaker's part")
        self.assertEqual(r["left"], "")
        self.assertNotIn("Guest speaker", r["text"])
        self.assertNotIn("Welcome to our guest speaker", r["text"])
        self.assertIn("no-speaker", r["edit"]["_v"])


class EveningPaperwork(Case):
    """December 16 after 8 PM: the meeting is over, so the agenda and the reminder are already January 20's (a guest
    speaker), while tonight's "No guest speaker" stays on screen until midnight. With no version chosen the texts
    follow the version the deck opens on for January 20 — they name its speaker, as they do after midnight — and say
    nothing about a version that leaves the speaker out; a "No guest speaker" the chair chose still leaves them out."""

    def test_none_chosen_names_next_months_speaker(self):
        r = self.run_core("""
            const text = (st, at) => { const cur = G.current(D, st, "", ms(at)); const p = G.paperText(D, st, cur, "agenda", ms(at));
              return { screen: cur.preset.id, meeting: p.meeting.ymd, left: p.speakerLeftOut, none: p.speakerNone, text: p.text }; };
            const st = state();
            const pressed = state(); G.startNextMonth(D, pressed, [], ms(input.during));
            const chosen = state("no-speaker");
            out({ at802: text(st, input.at802), late: text(st, input.late), dec17: text(st, input.dec17),
                  pressed: text(pressed, input.during), chosen: text(chosen, input.at802),
                  minutes: G.paperText(D, st, G.current(D, st, "", ms(input.at802)), "minutes", ms(input.at802)),
                  stored: G.deckState(st, D.id).preset });""",
            at802=DEC16_802, late=DEC16_2359, dec17=DEC17, during=DEC16_DURING)
        for k in ("at802", "late", "pressed"):
            with self.subTest(k):
                self.assertEqual((r[k]["screen"], r[k]["meeting"]), ("no-speaker", "2027-01-20"), "tonight's slides, January's text")
                self.assertIn("Guest speaker: Pat E. — Past delegate", r[k]["text"])
                self.assertEqual((r[k]["left"], r[k]["none"]), ("", False), "no word about a version leaving the speaker out")
                self.assertEqual(r[k]["text"], r["dec17"]["text"], "the same text as after midnight")
        self.assertEqual(r["dec17"]["screen"], "full")
        self.assertEqual(r["stored"], "", "nothing is stored")
        # a version the chair chose stays theirs: "No guest speaker" chosen leaves the speaker out, and says so
        self.assertEqual(r["chosen"]["left"], "Pat E.")
        self.assertNotIn("Pat E.", r["chosen"]["text"])
        # tonight's notes (the meeting held) are not moved: December 16's, no speaker
        self.assertNotIn("Pat E.", r["minutes"]["text"] if r["minutes"] else "")


class OldState(Case):
    def test_an_older_start_next_month_is_none_chosen(self):
        r = self.run_core("""
            const st = G.normState(JSON.parse(JSON.stringify(OLD)));
            const ds = st.decks[D.id];
            const jan = shows(st, input.jan), dec = shows(st, input.dec9);
            const sum = G.summary(ds, D);
            // a version picked after it stays the presenter's (the old pair is gone once read)
            ds.preset = "full";
            const again = G.normState(JSON.parse(JSON.stringify(st)));
            out({ preset: G.normState(OLD).decks[D.id].preset, prev: plain(G.normState(OLD).decks[D.id].prev), jan, dec,
                  sum: sum.preset, picked: again.decks[D.id].preset, pickedShows: shows(again, input.dec9) });""",
            jan=JAN20_655, dec9=DEC9)
        self.assertEqual(r["preset"], "")
        self.assertNotIn("preset", r["prev"], "its Undo leaves the version alone")
        self.assertEqual(r["prev"]["held"], "2026-11-18", "the rest of its Undo is kept")
        self.assertEqual(r["jan"], FULL, "January 20, 2027: its guest speaker's slides")
        self.assertEqual(r["dec"], NONE, "December 16: none, by the default")
        self.assertEqual(r["sum"], "", "no 'Version: No guest speaker' on the page")
        self.assertEqual((r["picked"], r["pickedShows"]), ("full", FULL))


class StartNextMonth(Case):
    def test_pressed_at_7_55_pm_on_an_empty_profile(self):
        r = self.run_core("""
            const st = state();
            const before = shows(st, input.at);
            const res = plain(G.startNextMonth(D, st, [], ms(input.at)));
            out({ before, res, after: shows(st, input.at), preset: G.deckState(st, D.id).preset });""", at=DEC16_755)
        self.assertEqual((r["before"], r["after"]), (NONE, NONE), "the show keeps its slides")
        self.assertEqual((r["res"]["version"], r["preset"]), ("", ""), "nothing to switch: no word about a version")

    def test_no_guest_speaker_chosen_goes_back_to_none_chosen(self):
        """At 7:45 PM on December 16 (the meeting still on), "Start next month" with "No guest speaker" chosen: the
        next meeting is January 20 (a speaker), so the version goes back to none chosen — tonight's slides until
        midnight, then January's first version."""
        r = self.run_core("""
            const st = state("no-speaker");
            const res = plain(G.startNextMonth(D, st, [], ms(input.during)));
            out({ res, preset: G.deckState(st, D.id).preset, tonight: shows(st, input.during), later: shows(st, input.dec17),
                  prev: plain(G.deckState(st, D.id).prev) });""", during=DEC16_DURING, dec17=DEC17)
        self.assertEqual((r["res"]["version"], r["preset"]), ("reset", ""))
        self.assertEqual((r["tonight"], r["later"]), (NONE, FULL))
        self.assertEqual((r["prev"]["held"], r["prev"]["preset"]), ("2026-12-16", "no-speaker"))

    def test_the_first_version_chosen_after_november_18(self):
        r = self.run_core("""
            const st = state("full");
            const res = plain(G.startNextMonth(D, st, [], ms(input.at)));
            out({ res, preset: G.deckState(st, D.id).preset, shows: shows(st, input.at), dec: shows(st, input.dec9) });""",
            at=NOV18_AFTER, dec9=DEC9)
        self.assertEqual((r["res"]["version"], r["preset"]), ("without", ""))
        self.assertEqual((r["shows"], r["dec"]), (NONE, NONE))


class Player(unittest.TestCase):
    """The player's wiring (src/assets/js/presentations.js, the macro, the strings)."""

    def test_wiring_and_strings(self):
        js = (ROOT / "src" / "assets" / "js" / "presentations.js").read_text(encoding="utf-8")
        macro = (ROOT / "src" / "_includes" / "macros" / "presentations.njk").read_text(encoding="utf-8")
        strings = json.loads((ROOT / "src" / "_i18n" / "presentations.json").read_text(encoding="utf-8"))
        # the version picked is stored by its id (the first one too) — the one the deck opens on by itself is none
        # chosen — and a deck with one is kept on the device
        self.assertIn('ds().preset = pr.id === G.defaultPreset(P.deck, ds(), Date.now()).id ? "" : pr.id;', js)
        self.assertNotIn('ds().preset = pr.id === first ? "" : pr.id;', js)
        self.assertIn("|| d.preset) out.decks[id] = d;", js)
        # "Chosen for you": only while none is chosen and the default is not the first version, with the date of
        # the meeting the speaker facts are for
        self.assertIn('if (!ds().preset && P.cur.preset.id && P.cur.preset.id !== first) {', js)
        self.assertIn("meetingName(G.speakerMeeting(P.deck, P.cur.nowMs))", js)
        self.assertIn('"pres.version_auto"', macro)
        # "back to 'With a guest speaker'" only once the screen shows it: else, at midnight (December 16, 2026)
        self.assertIn('P.cur.preset.id === firstPr.id ? "pres.paper_next_version" : "pres.paper_next_version_later"', js)
        self.assertIn('"pres.paper_next_version_later"', macro)
        later = strings["pres.paper_next_version_later"]
        self.assertIn("until midnight", later["en"])
        self.assertIn("hasta la medianoche", later["es"])
        s = strings["pres.version_auto"]
        self.assertIn("no guest speaker for {date}", s["en"])
        self.assertIn("ningún(a) orador(a) invitado(a) para el {date}", s["es"])
        for lang in ("en", "es"):
            self.assertIn("{version}", s[lang], lang)


if __name__ == "__main__":
    unittest.main()
