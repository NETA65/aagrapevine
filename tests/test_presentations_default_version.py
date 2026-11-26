"""The version a presentation opens on when the presenter has chosen none (src/assets/js/presentations-core.js
defaultPreset / presetFor, src/assets/js/presentations.js), run in Node.js:

  * Default   — a small deck with the chair's paperwork (its meetings: one the site lists NO guest speaker for, one
                with a speaker, one whose speaker is only "to be announced"): with no version chosen it opens on
                "No guest speaker" for the meeting with none — until that meeting ends, or "Start next month"
                closes it — and on the first version for a listed speaker and for one to be announced; a deck
                without paperwork, its first version. A version the presenter chose (the first one too, by its
                id) is never changed by the clock, survives a reload (normState) and a "my version" file; an
                unknown one is the default. The texts (paperText) and an edit (setField) follow the same version.
  * Start next month — pressed during tonight's meeting, it already looks at the meeting after it: a "No guest
                speaker" chosen for December 16 goes back to none chosen when January 20 has a speaker.
  * Player    — the player stores the version picked (the first one by its id), keeps it on the device, says
                "Chosen for you" for the default, in English and Spanish.

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

# A committee meeting's deck in the shape the build writes it (paperwork.meetings: rows with ymd, start, end, labels
# and the speaker facts): December 16, 2026 has no guest speaker (no_speaker), January 20, 2027 has one, February
# 17, 2027 is still to be announced (neither)
ROWS = [
    {"ymd": "2026-11-18", "start": "2026-11-19T01:00:00.000Z", "end": "2026-11-19T02:00:00.000Z",
     "label": "Wednesday, November 18, 2026", "label_es": "miércoles, 18 de noviembre de 2026", "month": "November 2026",
     "no_speaker": True},
    {"ymd": "2026-12-16", "start": "2026-12-17T01:00:00.000Z", "end": "2026-12-17T02:00:00.000Z",
     "label": "Wednesday, December 16, 2026", "label_es": "miércoles, 16 de diciembre de 2026", "month": "December 2026",
     "no_speaker": True},
    {"ymd": "2027-01-20", "start": "2027-01-21T01:00:00.000Z", "end": "2027-01-21T02:00:00.000Z",
     "label": "Wednesday, January 20, 2027", "label_es": "miércoles, 20 de enero de 2027", "month": "January 2027",
     "speaker": {"name": "Pat E.", "position": "Past delegate", "topic": "Carrying the message"}},
    {"ymd": "2027-02-17", "start": "2027-02-18T01:00:00.000Z", "end": "2027-02-18T02:00:00.000Z",
     "label": "Wednesday, February 17, 2027", "label_es": "miércoles, 17 de febrero de 2027", "month": "February 2027"},
]
DEC9 = "2026-12-09T18:00:00.000Z"           # a week before December 16
DEC16_DURING = "2026-12-17T01:45:00.000Z"   # 7:45 PM Central: the meeting is on
DEC16_OVER = "2026-12-17T02:30:00.000Z"     # 8:30 PM: over — January 20 is next
FEB10 = "2027-02-10T18:00:00.000Z"          # a week before February 17 (to be announced)


def slide(sid: str, title: str, **extra) -> dict:
    s = {"id": sid, "layout": "title", "h": "h-" + sid, "part": None, "accent": "gv", "eyebrow": "Sample", "title": title,
         "notes": "", "minutes": 1, "optional": False, "starts_off": False, "facilitator": False, "handout": False,
         "version_notes": {}, "show_from": None, "show_until": None, "when": None, "data": None}
    s.update(extra)
    return s


def deck(**over) -> dict:
    d = {"app": "gv-presentation", "id": "sample-meeting", "title": "Sample committee meeting", "short": "Sample",
         "version": "v1", "built": "2026-11-26T12:00:00.000Z", "minutes": 60, "live": {}, "fillins": [],
         "presets": [{"id": "full", "label": {"en": "With a guest speaker", "es": "Con orador(a) invitado(a)"}, "hide": []},
                     {"id": "no-speaker", "label": {"en": "No guest speaker", "es": "Sin orador(a) invitado(a)"},
                      "only": ["welcome", "topic", "close"]}],
         "slides": [slide("welcome", "Welcome"), slide("speaker", "Welcome to our guest speaker"),
                    slide("topic", "Tonight's topic", starts_off=True), slide("close", "Thank you")],
         "paperwork": {"speaker_slide": "speaker", "meetings": ROWS,
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
""" % json.dumps(CORE)


class Default(unittest.TestCase):
    def run_core(self, js: str, **data):
        if not node_path():
            self.skipTest("Node.js is not installed")
        return run_js(self, PRELUDE + js, data={"deck": deck(), **data}, needs_modules=False)

    def test_no_version_chosen_follows_the_next_meeting(self):
        r = self.run_core("""
            const st = state();
            out({ dec9: shows(st, input.dec9), during: shows(st, input.during), over: shows(st, input.over),
                  feb: shows(st, input.feb), plain: shows(state(), input.dec9, Object.assign({}, D, { paperwork: undefined })),
                  stored: G.deckState(st, D.id).preset,
                  def: G.defaultPreset(D, G.deckState(st, D.id), ms(input.dec9)).id });""",
            dec9=DEC9, during=DEC16_DURING, over=DEC16_OVER, feb=FEB10)
        none = {"id": "no-speaker", "slides": ["welcome", "topic", "close"]}
        full = {"id": "full", "slides": ["welcome", "speaker", "close"]}
        self.assertEqual(r["dec9"], none, "a week before a meeting with no guest speaker")
        self.assertEqual(r["during"], none, "while it is on")
        self.assertEqual(r["over"], full, "once it is over: January 20 has a speaker")
        self.assertEqual(r["feb"], full, "a speaker only to be announced: never switched")
        self.assertEqual(r["plain"], full, "a deck without the chair's paperwork: its first version")
        self.assertEqual(r["def"], "no-speaker")
        self.assertEqual(r["stored"], "", "the default is worked out, never stored")

    def test_start_next_month_closes_tonights_meeting(self):
        """ds.prev.held (the meeting "Start next month" closed): the default is the next meeting's."""
        r = self.run_core("""
            out({ closed: shows(state(undefined, { prev: { at: input.during, held: "2026-12-16", fill: {}, checks: {} } }), input.during),
                  open: shows(state(), input.during) });""", during=DEC16_DURING)
        self.assertEqual((r["closed"]["id"], r["open"]["id"]), ("full", "no-speaker"))

    def test_a_version_chosen_stays(self):
        r = self.run_core("""
            const full = state("full"), none = state("no-speaker"), odd = state("gone-version");
            const reloaded = G.normState(JSON.parse(JSON.stringify(full)));
            const file = G.exportVersion(D, full, "2026-12-01T00:00:00Z");
            const fileNone = G.exportVersion(D, state(), "2026-12-01T00:00:00Z");
            const back = G.validateImport(JSON.stringify(file), D);
            out({ full: shows(full, input.dec9), none: shows(none, input.jan), reloaded: shows(reloaded, input.dec9),
                  odd: shows(odd, input.dec9), file: file.preset, fileNone: fileNone.preset,
                  back: back.ok ? back.data.deck.preset : null, summary: G.summary(full.decks[D.id], D).preset });""",
            dec9=DEC9, jan="2027-01-10T18:00:00.000Z")
        self.assertEqual(r["full"]["id"], "full", "the first version chosen, by its id: kept on December 16")
        self.assertEqual(r["none"]["id"], "no-speaker", "No guest speaker chosen: kept in January too")
        self.assertEqual(r["reloaded"]["id"], "full", "after a reload")
        self.assertEqual(r["odd"]["id"], "no-speaker", "a version the deck no longer has: the default")
        self.assertEqual((r["file"], r["fileNone"]), ("full", ""), "a 'my version' file keeps the choice, or none")
        self.assertEqual(r["back"], "full", "and opening the file gives it back")
        self.assertEqual(r["summary"], "", "the first version is no change from the deck (no status line, no Reset)")

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


class StartNextMonth(unittest.TestCase):
    def test_pressed_during_tonights_meeting(self):
        """At 7:45 PM on December 16 (the meeting still on), "Start next month" with "No guest speaker" chosen: the
        next meeting is January 20 (a speaker), so the version goes back to none chosen — the first version then."""
        if not node_path():
            self.skipTest("Node.js is not installed")
        r = run_js(self, PRELUDE + """
            const st = state("no-speaker");
            const res = plain(G.startNextMonth(D, st, [], ms(input.during)));
            out({ res, preset: G.deckState(st, D.id).preset, shows: shows(st, input.during),
                  prev: plain(G.deckState(st, D.id).prev) });""",
            data={"deck": deck(), "during": DEC16_DURING}, needs_modules=False)
        self.assertEqual((r["res"]["version"], r["preset"], r["shows"]["id"]), ("reset", "", "full"))
        self.assertEqual((r["prev"]["held"], r["prev"]["preset"]), ("2026-12-16", "no-speaker"))


class Player(unittest.TestCase):
    """The player's wiring (src/assets/js/presentations.js, the macro, the strings)."""

    def test_wiring_and_strings(self):
        js = (ROOT / "src" / "assets" / "js" / "presentations.js").read_text(encoding="utf-8")
        macro = (ROOT / "src" / "_includes" / "macros" / "presentations.njk").read_text(encoding="utf-8")
        strings = json.loads((ROOT / "src" / "_i18n" / "presentations.json").read_text(encoding="utf-8"))
        # the version picked is stored by its id (the first one too), and a deck with one is kept on the device
        self.assertIn("ds().preset = pr.id;", js)
        self.assertNotIn('ds().preset = pr.id === first ? "" : pr.id;', js)
        self.assertIn("|| d.preset) out.decks[id] = d;", js)
        # "Chosen for you": only while none is chosen and the default is not the first version
        self.assertIn('if (!ds().preset && P.cur.preset.id && P.cur.preset.id !== first) {', js)
        self.assertIn('"pres.version_auto"', macro)
        s = strings["pres.version_auto"]
        self.assertIn("no guest speaker for {date}", s["en"])
        self.assertIn("ningún(a) orador(a) invitado(a) para el {date}", s["es"])
        for lang in ("en", "es"):
            self.assertIn("{version}", s[lang], lang)


if __name__ == "__main__":
    unittest.main()
