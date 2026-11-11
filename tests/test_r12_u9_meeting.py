"""Round 12 · the committee meeting's paperwork (Customize → Agenda & minutes): the deck's `paperwork:` block
(config/presentations/committee-meeting.yml), its checks (tests/test_presentations.py and its twin in
eleventy/filters/presentations.js), the meetings the build adds to the deck's JSON, and the player's logic
(src/assets/js/presentations-core.js paperText / nextMonthPlan / startNextMonth / undoNextMonth):

  * the checker twins  — a broken block gets the same lines from the Python checker and the build's
  * the build          — the deck's JSON carries the last two meetings held and the year ahead, with their dates in
                         English and in Spanish, their month, the meeting's time in the site's Spanish words and the
                         committee's Spanish name (config/site.yml site.committee_es); the decks without a block carry
                         none
  * the sample         — the sample committee meeting (tests/fixtures/presentations) uses every part of a block: the
                         agenda for the next meeting (until it ENDS), the minutes for the last one held, a paragraph in
                         Spanish that names the committee as the Spanish pages do, "Start next month" and its Undo
  * the last start     — its Undo (and the minutes' word about it) lasts until the next meeting begins: after that
                         the details are that meeting's own, and an Undo would replace them (G.lastStart)
  * the player         — the tab only for a deck with paperwork; e-mails open with NO address (mailto:?…)

The committee's own deck (config/presentations/committee-meeting.yml) — what the publish gate leaves to the Code
check (scripts/ops/gate_tests.py CONTENT_TESTS: the committee edits that file, so these judge it, not the code):

  * RealDeck           — its block passes both checkers; the minutes' anonymity rule as written; the reminder's
                         Spanish names the committee as the Spanish pages do; what its "Start next month" clears
                         and keeps
  * Texts              — the agenda e-mail, the reminder and the draft minutes made from the October meeting's
                         details, word for word: the agenda slide's rows of the chosen version; a line whose blanks
                         are all empty is left out (and a heading left with nothing), a half-filled one shows its
                         [hint]; a notes_only blank (the presenter's first name) never shows; the only e-mail address
                         is the committee's service address — never an attendance list or a name; the Google Meet
                         link and code, no phone line; the guest speaker of the meeting each text is for (the
                         agenda's speaker row too, also on the evening the agenda is already next month's), never
                         named in the minutes, and no speaker line for a meeting that has none
  * NextMonth          — "Start next month" on the committee's blanks: old business still open, then the action
                         items (its room at most); the one-night blanks cleared and the others kept; the minutes'
                         month; the checklist unticked; the agenda moves on at once; Undo puts everything back, and it
                         survives a reload (normState) but never goes into a saved "my version" file

Every test runs at a FIXED clock (run_js now=…): nothing here depends on the day the tests run.

    python -m unittest tests.test_r12_u9_meeting -v
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402
from test_presentations import EMAIL, check_deck  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "presentations"
# The site's settings the facts come from (the committee's meeting in its Google Meet room — no passcode, no number
# to call — and its guest speakers: October's confirmed, with slides, its position and topic in Spanish too;
# November's not confirmed yet, in English only; December not listed: the list ends in November)
SITE = {
    "url": "https://neta65.github.io/aagrapevine", "contact_email": "grapevine@neta65.org",
    "committee": "NETA 65 Grapevine & La Viña Committee", "committee_es": "Comité de Grapevine y La Viña de NETA 65",
    "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Google Meet",
                "online_url": "https://meet.google.com/rva-tmst-vdb", "meeting_id": "rva-tmst-vdb", "speaker_until": "19:30",
                "speakers": [
                    {"date": "2026-10-21", "name": "Rick W.", "confirmed": True, "slides": True,
                     "position": "Past delegate, Area 65 (Panel 73)", "topic": "Grapevine as a Twelfth Step tool",
                     "position_es": "Ex delegado, Área 65 (Panel 73)", "topic_es": "Grapevine como herramienta del Paso Doce"},
                    {"date": "2026-11-18", "name": "Jeannie M.", "confirmed": False,
                     "position": "Past delegate, Area 4 (Panel 73)", "topic": "Grapevine and La Viña as Public Information tools"},
                ]},
    "phone_access": {"numbers": [{"number": "+1 346 248 7799", "city": "Houston"}]},
}
# The build's clock (a week before the October 21, 2026 meeting) and the moments the player is used at. The meeting
# runs 7–8 PM Central: 00:00Z–01:00Z on October 22 (summer time); November 18 is in winter time (01:00Z).
BUILD = "2026-10-14T15:00:00Z"
WEEK_BEFORE = "2026-10-14T15:00:00Z"
DURING = "2026-10-22T00:30:00Z"       # 7:30 PM, tonight's meeting
AFTER = "2026-10-22T01:30:00Z"        # 8:30 PM, tonight's meeting over
NEXT_DAY = "2026-10-22T15:00:00Z"
NOV_BEFORE = "2026-11-18T23:00:00Z"   # 5 PM on November 18, before that meeting
NOV_DURING = "2026-11-19T01:30:00Z"   # 7:30 PM, the November meeting has begun
NOV_AFTER = "2026-11-19T02:30:00Z"    # 8:30 PM, the November meeting over
DEC_BEFORE = "2026-12-09T18:00:00Z"   # the week before December 16, a meeting with no guest speaker
# the sample committee meeting: the code's tests (the committee's own deck is the content's: RealDeck, Texts, NextMonth)
SAMPLE = {"dir": "tests/fixtures/presentations", "id": "sample-meeting"}

# Loads a deck's JSON as the build makes it (eleventy/filters/presentations.js deckJson, the site above) and the
# player's logic into a fresh vm context: G = window.GVP, D = the deck, ms(iso) = its instant.
LOAD = r"""
import vm from "node:vm";
const P = await imp("eleventy/filters/presentations.js");
const loaded = P.loadDecks(input.dir || "config/presentations");
const D = JSON.parse(JSON.stringify(P.deckJson(loaded.decks.find((d) => d.id === (input.id || "committee-meeting")), { site: input.site, db: {}, carry: {} })));
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/presentations-core.js", "utf8"), ctx, { filename: "presentations-core.js" });
const G = ctx.GVP;
const ms = (s) => Date.parse(s);
const plain = (v) => JSON.parse(JSON.stringify(v));
const texts = (st, at) => {
  const cur = G.current(D, st, "", ms(at));
  const o = {};
  for (const w of G.PAPER_TEXTS) o[w] = plain(G.paperText(D, st, cur, w, ms(at)));
  return o;
};
"""

# What the chair typed during the October meeting (the shared first name is notes_only: never in any text)
FILL = {
    "minutes_month": "September 2026", "minutes_sent": "by email on October 7", "minutes_taker": "the alternate chair",
    "old_1_item": "Booth schedule for 2027", "old_1_status": "done",
    "old_2_item": "Writing workshop in District 22", "old_2_status": "keep working",
    "new_1_item": "Bilingual flyer", "new_1_by": "District 3 GVR",
    "new_2_item": "Literature for a jail meeting",
    "action_1_what": "Ask the Area for a table", "action_1_who": "the alternate chair", "action_1_when": "Nov 1",
    "action_2_what": "Send the flyer to DCMs",
    "district_order": "3, 22, 91", "treasurer_budget": "within budget", "treasurer_reimburse": "receipts to the treasurer",
    "chair_since": "Two group visits", "since_1_event": "CityWide booth",
}
STATE_JS = """
const st = G.emptyState();
st.shared.fill.first_name = "Pat";
const ds = G.deckState(st, D.id);
Object.assign(ds.fill, input.fill);
ds.checks["week-before"] = ["0", "5"];
"""


def deck_js(case: unittest.TestCase, js: str, now: str = BUILD, **data):
    return run_js(case, LOAD + js, data={"site": SITE, **data}, now=now)


class CheckerTwins(unittest.TestCase):
    """A `paperwork:` block with every mistake: the Python checker (what deck writers run) and the build's twin say
    the same, line for line."""

    BROKEN = {
        "agenda_slide": "opening",
        "speaker_slide": "missing",
        "extra": 1,
        "agenda": {
            "subject": "Agenda {paper:agenda}\nsecond line",
            "body": "Hi {fill:first_name} and {fill:nope}, {live:nope} {paper:nope} {slide:agenda} {ui:customize}\n"
                    "See [the page](/meetings/) or <b>this</b>, write to someone@gmail.com or (214) 555-0123.\n"
                    "Rows: {paper:agenda}\nA class {lang:es}sin cierre\n",
        },
        "reminder": "plain text",
        "minutes": {"subject": "", "body": "Fine {fill:presenter}", "title": "x"},
        "next_month": {
            "actions": ["action_1", "nope_1"], "minutes_month": "nope", "clear": ["zzz_*", "presenter", "old_*"],
            "untick": ["agenda", "missing"], "other": True,
        },
    }
    EXPECTED = [
        "paperwork: unknown field 'extra'",
        "paperwork.agenda_slide: 'opening' is not an agenda slide",
        "paperwork.speaker_slide: no slide 'missing'",
        "paperwork.agenda.subject: one line",
        "paperwork.agenda.subject: {paper:agenda} goes on a line of its own (in a body)",
        "paperwork.agenda.body: {fill:first_name} is notes_only (never in the paperwork)",
        "paperwork.agenda.body: {fill:nope} is not in fillins",
        "paperwork.agenda.body: unknown {live:nope}",
        "paperwork.agenda.body: unknown {paper:nope}",
        "paperwork.agenda.body: {paper:agenda} goes on a line of its own (in a body)",
        "paperwork.agenda.body: unknown placeholder {slide:agenda}",
        "paperwork.agenda.body: unknown placeholder {ui:customize}",
        "paperwork.agenda.body: {lang:es} without its {/lang} on the same line",
        "paperwork.agenda.body: plain text — write an address as it is, not [label](url)",
        "paperwork.agenda.body: no HTML (the paperwork is plain text)",
        "paperwork.agenda.body: the word 'class' breaks the site's wording rules (… (214) 555-0123.\nRows: {paper:agenda}\nA class {lang:es}sin cierre\n…)",
        "paperwork.agenda.body: a personal-looking phone number '(214) 555-0123' (write {live:meeting_phone} or {live:meeting_zoom_id})",
        "paperwork.agenda.body: e-mail 'someone@gmail.com' — only service addresses (aagrapevine.org, aalavina.org, aa.org, neta65.org)",
        "paperwork.reminder: {subject, body}",
        "paperwork.minutes: unknown field 'title'",
        "paperwork.minutes.subject: a non-empty string",
        "paperwork.next_month: unknown field 'other'",
        "paperwork.next_month.actions: no blank 'nope_1_what'",
        "paperwork.next_month.actions: no blank 'nope_1_who'",
        "paperwork.next_month.actions: no blank 'nope_1_when'",
        "paperwork.next_month: actions AND old_business (open action items become next month's old business)",
        "paperwork.next_month.minutes_month: no blank 'nope'",
        "paperwork.next_month.clear: 'zzz_*' names no blank",
        "paperwork.next_month.clear: 'presenter' is shared by every presentation (never cleared)",
        "paperwork.next_month.untick: 'agenda' is not a checklist",
        "paperwork.next_month.untick: no slide 'missing'",
    ]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="r12-u9-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, name: str, block) -> Path:
        d = yaml.safe_load((FIXTURES / "sample-meeting.yml").read_text(encoding="utf-8"))
        d["id"] = name
        if block is None:
            d.pop("paperwork", None)
        else:
            d["paperwork"] = block
        p = self.tmp / f"{name}.yml"
        p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return p

    def build_problems(self) -> list[str]:
        return run_js(self, "const P = await imp('eleventy/filters/presentations.js'); out(P.loadDecks(input.dir).problems);",
                      data={"dir": str(self.tmp)})

    def test_a_broken_block_gets_the_same_lines_from_both(self):
        p = self.write("broken-paper", self.BROKEN)
        py = [x for x in check_deck(p) if x.startswith("paperwork")]
        self.assertEqual(sorted(py), sorted(self.EXPECTED))
        js = [x.split(": ", 1)[1] for x in self.build_problems()]
        self.assertEqual(sorted(x for x in js if x.startswith("paperwork")), sorted(py))
        self.assertEqual([x for x in js if not x.startswith("paperwork")], [], "nothing else in the sample is wrong")

    def test_not_a_mapping_and_no_text(self):
        self.write("odd-paper", "yes please")
        self.write("empty-paper", {"agenda_slide": "agenda"})
        self.assertEqual(check_deck(self.tmp / "odd-paper.yml"), ["paperwork: a mapping"])
        self.assertEqual(check_deck(self.tmp / "empty-paper.yml"), ["paperwork: at least one text (agenda, reminder, minutes)"])
        js = sorted(self.build_problems())
        self.assertEqual(js, ["empty-paper.yml: paperwork: at least one text (agenda, reminder, minutes)",
                              "odd-paper.yml: paperwork: a mapping"])

    def test_the_sample_passes_both(self):
        """Every part of a block, every {paper:…} fact among them, passes both checkers (the committee's own deck:
        RealDeck)."""
        self.assertEqual(check_deck(FIXTURES / "sample-meeting.yml"), [])
        r = run_js(self, """
            const P = await imp("eleventy/filters/presentations.js");
            out(P.loadDecks("tests/fixtures/presentations").problems);""")
        self.assertEqual(r, [])


class RealDeck(unittest.TestCase):
    """The committee's own block (config/presentations/committee-meeting.yml) — left to the Code check
    (scripts/ops/gate_tests.py CONTENT_TESTS): it judges the file the committee edits."""

    def test_the_real_block_passes_both(self):
        self.assertEqual(check_deck(ROOT / "config" / "presentations" / "committee-meeting.yml"), [])
        r = run_js(self, """
            const P = await imp("eleventy/filters/presentations.js");
            out(P.loadDecks("config/presentations").problems);""")
        self.assertEqual(r, [])

    def test_the_minutes_follow_the_decks_rules(self):
        """Anonymity: service positions and counts only (the presenter's first name is notes_only, so it cannot be
        in any text); the only address is the committee's service e-mail."""
        d = yaml.safe_load((ROOT / "config" / "presentations" / "committee-meeting.yml").read_text(encoding="utf-8"))
        pw = d["paperwork"]
        body = pw["minutes"]["body"]
        self.assertIn("no attendance list", body)
        self.assertIn("Attended: about ___ members (by district: ___)", body)
        self.assertNotIn("first_name", json.dumps(pw))
        self.assertEqual(EMAIL.findall(json.dumps(pw)), [], "addresses come from {live:email}, never typed in")
        self.assertIn("{live:email}", pw["agenda"]["body"])
        # the reminder's Spanish names the committee as the rest of the Spanish site does (config/site.yml)
        self.assertIn("la reunión mensual del {paper:committee_es} es el", pw["reminder"]["body"])
        self.assertNotIn("Comité de Grapevine / La Viña", pw["reminder"]["body"])
        # the guest speaker by their service position in the minutes (never a name), by name in the agenda e-mail
        # and the reminder; the Google Meet link, never a phone line or a passcode
        self.assertIn("Guest speaker: {paper:speaker_position}", body)
        self.assertNotIn("{paper:speaker}", body)
        for k in ("agenda", "reminder"):
            self.assertIn("Guest speaker: {paper:speaker}", pw[k]["body"], k)
            self.assertIn("{live:meeting_url}", pw[k]["body"], k)
        text = json.dumps(pw)
        for gone in ("meeting_phone", "phone_passcode", "meeting_passcode", "meeting_zoom_id", "Zoom", "By phone"):
            self.assertNotIn(gone, text, gone)

    def test_what_start_next_month_clears_and_keeps(self):
        r = deck_js(self, "out(D.paperwork);")
        self.assertEqual((r["agenda_slide"], r["speaker_slide"]), ("agenda", "speaker-intro"))
        nm = r["next_month"]
        self.assertEqual((nm["actions"], nm["old_business"], nm["minutes_month"], nm["untick"]),
                         (["action_1", "action_2", "action_3", "action_4"], ["old_1", "old_2", "old_3", "old_4"], "minutes_month", ["week-before"]))
        # the patterns named: every chair_* blank, never a shared one or one the chair keeps month to month
        self.assertTrue({"chair_since", "chair_area", "chair_office", "chair_next", "since_3_count", "action_4_when", "topic"} <= set(nm["clear"]))
        self.assertFalse({"presenter", "first_name", "district_order", "treasurer_budget"} & set(nm["clear"]))


class Build(unittest.TestCase):
    """The meetings the deck's JSON carries for the paperwork (eleventy/filters/presentations.js paperMeetings), on
    the sample committee meeting (tests/fixtures/presentations)."""

    def test_the_meetings_and_the_spanish_words(self):
        r = deck_js(self, """
            const other = P.deckJson(loaded.decks.find((d) => d.id === "sample-workshop"), { site: input.site, db: {}, carry: {} });
            const noName = P.deckJson(loaded.decks.find((d) => d.id === input.id), { site: { ...input.site, committee_es: "  " }, db: {}, carry: {} });
            out({ pw: D.paperwork, other: Object.keys(other).includes("paperwork"), keys: Object.keys(D).slice(-3),
                  noName: noName.paperwork.committee_es });""", **SAMPLE)
        pw = r["pw"]
        rows = pw["meetings"]
        self.assertEqual([x["ymd"] for x in rows[:5]], ["2026-08-19", "2026-09-16", "2026-10-21", "2026-11-18", "2026-12-16"],
                         "the last two held, then the year ahead")
        # each meeting with its guest speaker (name, service position, topic) — never `confirmed` or `slides`, which
        # are the chair's notes': the paperwork goes out by e-mail
        self.assertEqual(rows[2], {"ymd": "2026-10-21", "start": "2026-10-22T00:00:00.000Z", "end": "2026-10-22T01:00:00.000Z",
                                   "label": "Wednesday, October 21, 2026", "label_es": "miércoles, 21 de octubre de 2026",
                                   "month": "October 2026",
                                   "speaker": {"name": "Rick W.", "position": "Past delegate, Area 65 (Panel 73)",
                                               "topic": "Grapevine as a Twelfth Step tool",
                                               "position_es": "Ex delegado, Área 65 (Panel 73)",
                                               "topic_es": "Grapevine como herramienta del Paso Doce"}})
        self.assertEqual(rows[3]["speaker"]["name"], "Jeannie M.", "listed, not confirmed yet: shown all the same")
        self.assertEqual(rows[3]["speaker"]["position_es"], "Past delegate, Area 4 (Panel 73)", "no Spanish: the English, as /es/meetings/")
        self.assertNotIn("speaker", rows[4], "December 16: no guest speaker")
        self.assertEqual(rows[3]["start"], "2026-11-19T01:00:00.000Z", "winter time")
        self.assertLessEqual(rows[-1]["ymd"], "2027-10-20", "about a year ahead")
        self.assertIn("p. m., hora del Centro", pw["time_es"])
        self.assertEqual(pw["committee_es"], "Comité de Grapevine y La Viña de NETA 65", "config/site.yml site.committee_es")
        self.assertEqual(r["noName"], "", "none set: the player says the committee's name in its own words")
        self.assertEqual((pw["agenda_slide"], pw["speaker_slide"]), ("agenda", "guest-speaker"))
        self.assertIn("{paper:agenda}", pw["agenda"]["body"], "tokens stay: the player fills them")
        self.assertIn("{paper:committee_es}", pw["reminder"]["body"])
        nm = pw["next_month"]
        self.assertEqual((nm["actions"], nm["old_business"], nm["minutes_month"], nm["untick"]),
                         (["action_1"], ["old_1"], "minutes_month", ["chair-checklist"]))
        # the patterns named ("old_*", "action_*"): every blank of their rows, never a shared one
        self.assertEqual(sorted(nm["clear"]), ["action_1_what", "action_1_when", "action_1_who", "old_1_item", "old_1_status"])
        self.assertFalse(r["other"], "a deck without a paperwork block has none")
        self.assertEqual(r["keys"], ["live", "slides", "paperwork"])


class Texts(unittest.TestCase):
    """The agenda e-mail, the reminder and the draft minutes, from the October meeting's details."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def run_texts(self):
        if Texts.r is None:
            Texts.r = deck_js(self, STATE_JS + """
                const empty = G.emptyState();
                const version = (p, at) => { const s2 = JSON.parse(JSON.stringify(st)); s2.decks[D.id].preset = p; return texts(s2, at); };
                // "Start next month" at 8:30 PM on the meeting night: the agenda is November's at once
                const started = JSON.parse(JSON.stringify(st));
                G.startNextMonth(D, started, [], ms(input.after));
                out({ week: texts(st, input.week), during: texts(st, input.during), after: texts(st, input.after),
                      emptyWeek: texts(empty, input.week), topic: version("topic", input.week).agenda.text,
                      noSpeaker: version("no-speaker", input.week).agenda.text, started: texts(started, input.after),
                      noSpeakerWeek: version("no-speaker", input.week), noSpeakerAfter: version("no-speaker", input.after),
                      dec: texts(st, input.dec), decNoSpeaker: version("no-speaker", input.dec) });""",
                fill=FILL, week=WEEK_BEFORE, during=DURING, after=AFTER, dec=DEC_BEFORE)
        return Texts.r

    def test_the_agenda_is_for_the_next_meeting(self):
        r = self.run_texts()
        a = r["week"]["agenda"]
        self.assertEqual(a["subject"], "Agenda: Grapevine and La Viña Committee meeting, Wednesday, October 21, 2026")
        self.assertEqual(a["meeting"]["ymd"], "2026-10-21")
        t = a["text"]
        self.assertIn("Here is the agenda for the October 2026 meeting", t)
        self.assertIn("When: Wednesday, October 21, 2026, 7:00", t)
        # that meeting's guest speaker, and how to join on Google Meet: the link and its code — no phone, no passcode
        self.assertIn("\nGuest speaker: Rick W. — Past delegate, Area 65 (Panel 73)\nTopic: Grapevine as a Twelfth Step tool\n"
                      "Join on Google Meet: https://meet.google.com/rva-tmst-vdb (meeting code rva-tmst-vdb)\n", t)
        for gone in ("Zoom", "phone", "passcode"):
            self.assertNotIn(gone, t)
        # the agenda slide's rows, in the chosen version: with the guest speaker (the first version), or the
        # committee's business for the whole hour
        self.assertIn("Agenda (Central time)\n7:00  Welcome and opening\n7:02  Guest speaker: Rick W.\n"
                      "7:22  Questions for our guest speaker\n7:30  Committee business: the Preamble, introductions, minutes\n", t)
        self.assertIn("7:37  Grapevine and La Viña news", t)
        self.assertIn("7:59  Closing", t)
        self.assertIn("Agenda (Central time)\n7:00  Welcome and opening\n7:03  Reading\n", r["noSpeaker"])
        self.assertIn("7:17  Grapevine and La Viña news", r["noSpeaker"])
        self.assertIn("7:17  News and topic of the month", r["topic"], "the version's own agenda")
        # lines whose blanks are all empty are left out; a half-filled one shows its [hint]
        self.assertIn("Old business\n- Booth schedule for 2027\n- Writing workshop in District 22\n\nNew business", t)
        self.assertIn("- Bilingual flyer (brought by District 3 GVR)\n- Literature for a jail meeting (brought by [service position])", t)
        self.assertEqual(re.findall(r"\[[^\]]*\]", t), ["[service position]"])
        self.assertIn("The minutes of the September 2026 meeting were sent by email on October 7.", t)
        self.assertIn("District reports, in this order: 3, 22, 91.", t)
        self.assertTrue(t.endswith("In service,\nArea 65 Grapevine / La Viña Chair\ngrapevine@neta65.org\n"
                                   "Meeting details: https://neta65.github.io/aagrapevine/meetings/#committee-meeting"), t[-200:])
        self.assertEqual(set(EMAIL.findall(t)), {"grapevine@neta65.org"})
        self.assertEqual({b["lang"] for b in a["blocks"]}, {"en"})

    def test_the_speaker_of_the_meeting_each_text_is_for(self):
        r = self.run_texts()
        # after "Start next month" at 8:30 PM on October 21 the agenda is November's: its speaker in the e-mail AND in
        # the agenda's speaker row, though the slides still show tonight's until midnight
        nov = r["started"]["agenda"]["text"]
        self.assertTrue(r["started"]["agenda"]["subject"].endswith("Wednesday, November 18, 2026"))
        self.assertIn("Guest speaker: Jeannie M. — Past delegate, Area 4 (Panel 73)\nTopic: Grapevine and La Viña as Public Information tools\n", nov)
        self.assertIn("\n7:02  Guest speaker: Jeannie M.\n", nov)
        self.assertNotIn("Rick W.", nov)
        # the minutes of October 21: the speaker by service position, never by name
        m = r["after"]["minutes"]["text"]
        self.assertIn("Opened with a moment of silence and the Serenity Prayer.\nGuest speaker: Past delegate, Area 65 (Panel 73)\n"
                      "Topic: Grapevine as a Twelfth Step tool, then the members' questions\n"
                      "The committee's business opened with the AA Preamble.", m)
        self.assertNotIn("Rick W.", m)
        self.assertIn("monthly meeting on Google Meet: Wednesday, October 21, 2026", m)
        self.assertIn("Next meeting: Wednesday, November 18, 2026, 7:00", m)
        self.assertTrue(r["after"]["minutes"]["text"].split("Next meeting: ", 1)[1].startswith("Wednesday, November 18, 2026"))
        # December 16: the list (October and November) doesn't reach it, so its speaker is not known yet: no speaker
        # line in any text; the speaker version's row says "to be announced" (a meeting the list gives NO speaker:
        # "none at this meeting", tests/test_r24_no_speaker.py)
        for w in ("agenda", "reminder"):
            self.assertNotIn("Guest speaker:", r["dec"][w]["text"].split("Agenda (Central time)")[0], w)
            self.assertNotIn("Topic:", r["dec"][w]["text"], w)
        self.assertIn("\n7:02  Guest speaker: to be announced\n", r["dec"]["agenda"]["text"])
        self.assertNotIn("Guest speaker", r["decNoSpeaker"]["agenda"]["text"], "the version without a speaker: none at all")
        self.assertNotIn("Guest speaker", r["decNoSpeaker"]["reminder"]["text"])
        # a speaker who can't come: the version 'No guest speaker' names none, though the site still lists one
        for w, at in (("agenda", "noSpeakerWeek"), ("reminder", "noSpeakerWeek"), ("minutes", "noSpeakerAfter")):
            self.assertNotIn("Guest speaker", r[at][w]["text"], w)
            self.assertNotIn("Rick W.", r[at][w]["text"], w)
            self.assertNotIn("Twelfth Step", r[at][w]["text"], w)

    def test_an_empty_version_never_shows_an_empty_blank(self):
        t = self.run_texts()["emptyWeek"]["agenda"]["text"]
        self.assertNotIn("[", t)
        # (the agenda's rows say "Old business" too: a heading is the first line of its paragraph)
        for gone in ("\n\nOld business\n", "\n\nNew business\n", "Last month's minutes", "District reports, in this order", "phone"):
            self.assertNotIn(gone, t, gone)
        self.assertIn("Anything to add under new business?", t, "a line with no blank always stays")
        self.assertIn("Area 65 Grapevine / La Viña Chair", t, "a blank's default counts as filled in")
        m = self.run_texts()["emptyWeek"]["minutes"]["text"]
        self.assertIn("District reports\n- Highlights (carrying the message, events, needs): ___", m,
                      "a heading over a line with no blank stays")
        self.assertNotIn("\n\nAction items", m)
        self.assertNotIn("Topic of the month", m)

    def test_the_reminder_in_english_and_spanish(self):
        rem = self.run_texts()["week"]["reminder"]
        self.assertEqual(rem["subject"], "Reminder: Grapevine and La Viña Committee meeting, Wednesday, October 21, 2026")
        self.assertEqual([b["lang"] for b in rem["blocks"]], ["en", "es", "en"])
        es = rem["blocks"][1]["text"]
        self.assertTrue(es.startswith("Recordatorio: la reunión mensual del Comité de Grapevine y La Viña de NETA 65 es el "
                                      "miércoles, 21 de octubre de 2026, 7:00"), es)
        self.assertIn("p. m., hora del Centro, por Google Meet: https://meet.google.com/rva-tmst-vdb (código de la reunión: rva-tmst-vdb).", es)
        en = rem["blocks"][0]["text"]
        self.assertIn(", on Google Meet: https://meet.google.com/rva-tmst-vdb (meeting code rva-tmst-vdb).\n"
                      "Guest speaker: Rick W. — Past delegate, Area 65 (Panel 73)\nTopic: Grapevine as a Twelfth Step tool\n", en)
        # that meeting's guest speaker and topic in Spanish too, as /es/meetings/ gives them
        self.assertIn("(código de la reunión: rva-tmst-vdb).\nOrador(a) invitado(a): Rick W. — Ex delegado, Área 65 (Panel 73)\n"
                      "Tema: Grapevine como herramienta del Paso Doce\nLa reunión es en inglés.", es)
        # "no need to register" as the rest of the site says it (Meetings, the orientation, the GVR corner)
        self.assertTrue(es.endswith("Todos los miembros de AA son bienvenidos, y no hace falta registrarse."), es)
        self.assertNotIn("{lang", rem["text"])
        self.assertNotIn("⁠", rem["text"], "no invisible word joiners in an e-mail")

    def test_the_minutes_are_for_the_meeting_held(self):
        r = self.run_texts()
        self.assertEqual(r["week"]["minutes"]["meeting"]["ymd"], "2026-09-16", "the week before: last month's")
        self.assertEqual(r["during"]["minutes"]["meeting"]["ymd"], "2026-10-21", "tonight's, from its start")
        self.assertEqual(r["during"]["agenda"]["meeting"]["ymd"], "2026-10-21", "the agenda: tonight's until it ends")
        self.assertEqual(r["after"]["agenda"]["meeting"]["ymd"], "2026-11-18", "then next month's")
        m = r["after"]["minutes"]
        self.assertEqual(m["subject"], "Draft minutes: Grapevine and La Viña Committee meeting, Wednesday, October 21, 2026")
        t = m["text"]
        self.assertTrue(t.startswith("DRAFT, for the committee's approval"))
        self.assertIn("Chair: Area 65 Grapevine / La Viña Chair\nMinutes taken by: the alternate chair\n"
                      "Attended: about ___ members (by district: ___)", t)
        self.assertIn("Old business\n- Booth schedule for 2027: done\n- Writing workshop in District 22: keep working", t)
        self.assertIn("- Ask the Area for a table · the alternate chair · by Nov 1\n- Send the flyer to DCMs · [Service position] · by [Date]", t)
        self.assertIn("Since we last met\n- CityWide booth · [date] · [district or city]: about [number] attended", t)
        self.assertIn("Next meeting: Wednesday, November 18, 2026, 7:00", t)
        for text in (r["after"][w]["text"] for w in ("agenda", "reminder", "minutes")):
            self.assertNotIn("Pat", text, "the presenter's first name (notes_only) is never in the paperwork")


class NextMonth(unittest.TestCase):
    """"Start next month" after the October meeting, and its Undo."""

    def test_start_then_undo(self):
        r = deck_js(self, STATE_JS + """
            const before = plain(ds.fill);
            const plan = G.nextMonthPlan(D, st, ms(input.after));
            const res = plain(G.startNextMonth(D, st, ["action_2", "old_2", "action_1", "nope"], ms(input.after)));
            const after = { fill: plain(ds.fill), checks: plain(ds.checks), shared: plain(st.shared.fill), prev: plain(ds.prev) };
            const agenda = G.paperText(D, st, G.current(D, st, "", ms(input.after)), "agenda", ms(input.after));
            const done = G.nextMonthPlan(D, st, ms(input.next_day)).done;
            const stored = plain(G.normState(JSON.parse(JSON.stringify(st))).decks[D.id].prev);
            const exported = Object.keys(G.exportVersion(D, st, "2026-10-22T03:00:00.000Z"));
            const undo = G.undoNextMonth(D, st);
            out({ plan: plain(plan), res, after, agenda: agenda.subject, done, stored, exported, undo, again: G.undoNextMonth(D, st),
                  back: plain(ds.fill), backChecks: plain(ds.checks), prev: ds.prev, same: JSON.stringify(before) === JSON.stringify(plain(ds.fill)) });""",
            fill=FILL, after=AFTER, next_day=NEXT_DAY)
        plan = r["plan"]
        self.assertEqual([(i["id"], i["kind"], i["checked"]) for i in plan["items"]],
                         [("action_1", "action", True), ("action_2", "action", True), ("old_1", "old", False), ("old_2", "old", False)])
        self.assertEqual(plan["items"][0]["text"], "Ask the Area for a table (the alternate chair, by Nov 1)")
        self.assertEqual(plan["items"][1]["text"], "Send the flyer to DCMs")
        self.assertEqual(plan["items"][3]["status"], "keep working")
        self.assertEqual((plan["room"], plan["held"]["ymd"], plan["done"]), (4, "2026-10-21", False))
        self.assertEqual(plan["keep"], ["treasurer_budget", "treasurer_reimburse", "district_order"])
        self.assertEqual(r["res"]["carried"], 3)
        fill = r["after"]["fill"]
        # old business still open first, then tonight's action items (an unknown pick is ignored); statuses cleared
        self.assertEqual(fill, {
            "minutes_month": "October 2026",
            "old_1_item": "Writing workshop in District 22",
            "old_2_item": "Ask the Area for a table (the alternate chair, by Nov 1)",
            "old_3_item": "Send the flyer to DCMs",
            "district_order": "3, 22, 91", "treasurer_budget": "within budget", "treasurer_reimburse": "receipts to the treasurer",
        })
        self.assertEqual(r["after"]["checks"], {}, "the week-before checklist starts over")
        self.assertEqual(r["after"]["shared"], {"first_name": "Pat"}, "a shared blank is never touched")
        self.assertEqual(r["after"]["prev"]["held"], "2026-10-21")
        self.assertEqual(r["after"]["prev"]["at"], "2026-10-22T01:30:00.000Z")
        self.assertEqual(r["agenda"], "Agenda: Grapevine and La Viña Committee meeting, Wednesday, November 18, 2026")
        self.assertTrue(r["done"], "already started after this meeting (the next day too)")
        self.assertEqual(r["stored"]["fill"]["action_1_what"], "Ask the Area for a table", "the Undo survives a reload")
        self.assertEqual(r["stored"]["checks"], {"week-before": ["0", "5"]})
        self.assertNotIn("prev", r["exported"], "never in a saved \"my version\" file")
        self.assertTrue(r["undo"])
        self.assertFalse(r["again"], "one Undo")
        self.assertTrue(r["same"], "every blank back as it was")
        self.assertEqual(r["backChecks"], {"week-before": ["0", "5"]})
        self.assertIsNone(r["prev"])

    def test_a_no_speaker_version_kept_into_a_month_with_a_speaker(self):
        # "No guest speaker", chosen for a month without one, is still the version when the next meeting has one: the
        # paperwork names none but says so; "Start next month" goes back to the first version (its Undo too); hiding
        # only the speaker's slide by hand is no version, so the texts keep the listed speaker
        r = deck_js(self, STATE_JS + """
            const left = (p, hidden, at) => { const s2 = JSON.parse(JSON.stringify(st)); const d2 = s2.decks[D.id];
              d2.preset = p; d2.hidden = hidden;
              return plain(G.paperText(D, s2, G.current(D, s2, "", ms(at)), "agenda", ms(at))); };
            const noSp = left("no-speaker", [], input.week);
            const byHand = left("", ["speaker-intro"], input.week);
            // after the October meeting (Rick W.): November lists Jeannie M.
            ds.preset = "no-speaker";
            const res = plain(G.startNextMonth(D, st, [], ms(input.after)));
            const reset = ds.preset;
            const stored = plain(G.normState(JSON.parse(JSON.stringify(st))).decks[D.id].prev);
            G.undoNextMonth(D, st);
            const undone = ds.preset;
            // after the November meeting: the list doesn't reach December (not known yet), so the version stays
            const s3 = JSON.parse(JSON.stringify(st)); s3.decks[D.id].preset = "no-speaker"; s3.decks[D.id].prev = null;
            const res3 = plain(G.startNextMonth(D, s3, [], ms(input.nov_after)));
            out({ noSp, byHand, res, reset, stored, undone, res3, kept: s3.decks[D.id].preset });""",
            fill=FILL, week=WEEK_BEFORE, after=AFTER, nov_after=NOV_AFTER)
        self.assertEqual(r["noSp"]["speakerLeftOut"], "Rick W.", "the panel can say the version leaves him out")
        self.assertNotIn("Rick W.", r["noSp"]["text"])
        self.assertEqual(r["byHand"]["speakerLeftOut"], "")
        self.assertIn("Guest speaker: Rick W.", r["byHand"]["text"], "a slide hidden by hand is no version")
        self.assertEqual((r["res"]["version"], r["reset"]), ("reset", ""), "back to the first version: November has a speaker")
        self.assertEqual(r["stored"]["preset"], "no-speaker", "its Undo survives a reload")
        self.assertEqual(r["undone"], "no-speaker")
        self.assertEqual((r["res3"]["version"], r["kept"]), ("", "no-speaker"), "December is not listed: the version stays")

    def test_during_the_meeting_the_agenda_moves_on_at_once(self):
        r = deck_js(self, STATE_JS + """
            const plan = G.nextMonthPlan(D, st, ms(input.during));
            G.startNextMonth(D, st, ["action_1"], ms(input.during));
            const m = G.paperMeetings(D, st.decks[D.id], ms(input.during));
            out({ held: plan.held.ymd, next: m.next.ymd, month: ds.fill.minutes_month, old: ds.fill.old_1_item });""",
            fill=FILL, during=DURING)
        self.assertEqual(r, {"held": "2026-10-21", "next": "2026-11-18", "month": "October 2026",
                             "old": "Ask the Area for a table (the alternate chair, by Nov 1)"})

    def test_old_business_holds_four(self):
        fill = {**FILL, "old_3_item": "Third", "old_4_item": "Fourth"}
        r = deck_js(self, STATE_JS + """
            const res = G.startNextMonth(D, st, ["action_1", "action_2", "old_1", "old_2", "old_3", "old_4"], ms(input.after));
            out({ n: res.carried, items: [1, 2, 3, 4, 5].map((i) => ds.fill["old_" + i + "_item"] || null) });""",
            fill=fill, after=AFTER)
        self.assertEqual(r["n"], 4)
        self.assertEqual(r["items"], ["Booth schedule for 2027", "Writing workshop in District 22", "Third", "Fourth", None])



class StoredUndo(unittest.TestCase):
    """What is kept for the Undo, read back from the browser's storage (normState)."""

    def test_a_broken_stored_undo_is_dropped(self):
        r = deck_js(self, """
            const junk = { v: 1, decks: { "committee-meeting": { fill: { a: "x" }, prev: { at: "nonsense", fill: { a: "y" } } },
                                          other: { prev: { at: "2026-10-22T01:30:00.000Z", held: "21/10", fill: { a: "<b>", "Bad-Key": 1 }, checks: { "week-before": ["0", "x"] } } } } };
            const s = G.normState(junk);
            out({ bad: s.decks["committee-meeting"].prev, odd: plain(s.decks.other.prev), none: G.emptyDeck().prev });""", **SAMPLE)
        self.assertIsNone(r["bad"])
        self.assertEqual(r["odd"], {"at": "2026-10-22T01:30:00.000Z", "held": "", "fill": {"a": "<b>"}, "checks": {"week-before": ["0"]}})
        self.assertIsNone(r["none"])


class Sample(unittest.TestCase):
    """The sample committee meeting (tests/fixtures/presentations) uses every part of a block."""

    def test_the_samples_paperwork(self):
        r = deck_js(self, """
            const st = G.emptyState();
            const ds = G.deckState(st, D.id);
            ds.fill.old_1_item = "Flyers"; ds.fill.action_1_what = "Print them";
            ds.checks["chair-checklist"] = ["1"];
            const t = texts(st, input.at);
            G.startNextMonth(D, st, ["action_1"], ms(input.at));
            out({ t, fill: plain(ds.fill), checks: plain(ds.checks) });""",
            dir="tests/fixtures/presentations", id="sample-meeting", at=AFTER)
        self.assertIn("Agenda\n0:00  Opening and welcome\n0:04  Dates and events — The year's meeting dates", r["t"]["agenda"]["text"])
        # the guest speaker of the meeting each text is for: November's agenda (by name), October's minutes (by
        # service position only)
        self.assertIn("\nGuest speaker: Jeannie M. — Past delegate, Area 4 (Panel 73), on Grapevine and La Viña as Public Information tools\n",
                      r["t"]["agenda"]["text"])
        self.assertIn("\nGuest speaker: Past delegate, Area 65 (Panel 73)\n", r["t"]["minutes"]["text"])
        self.assertEqual([b["lang"] for b in r["t"]["reminder"]["blocks"]], ["en", "es"])
        self.assertIn("Old business\n- Flyers: [status]", r["t"]["minutes"]["text"])
        self.assertEqual(r["fill"], {"old_1_item": "Print them", "minutes_month": "October 2026"})
        self.assertEqual(r["checks"], {})

    def test_a_version_without_the_speakers_slide_names_no_speaker(self):
        """paperwork.speaker_slide: the version that leaves out the guest speaker's slide (the short meeting) has no
        speaker lines in any text, though the site lists a speaker; the full one names them."""
        r = deck_js(self, """
            const st = G.emptyState();
            const short = JSON.parse(JSON.stringify(st));
            G.deckState(short, D.id).preset = "short";
            out({ full: texts(st, input.week), short: texts(short, input.week), shortAfter: texts(short, input.after) });""",
            **SAMPLE, week=WEEK_BEFORE, after=AFTER)
        self.assertIn("\nGuest speaker: Rick W. — Past delegate, Area 65 (Panel 73), on Grapevine as a Twelfth Step tool\n",
                      r["full"]["agenda"]["text"])
        for w, t in (("agenda", r["short"]["agenda"]["text"]), ("minutes", r["shortAfter"]["minutes"]["text"])):
            self.assertNotIn("Guest speaker", t, w)
            self.assertNotIn("Rick W.", t, w)
        self.assertIn("Meeting of Wednesday, October 21, 2026.", r["shortAfter"]["minutes"]["text"], "the rest stays")

    def test_each_text_is_for_its_meeting(self):
        """The agenda and the reminder: the next meeting, until it ENDS; the minutes: the last one that has begun."""
        r = deck_js(self, """
            const st = G.emptyState();
            st.shared.fill.first_name = "Pat";
            G.deckState(st, D.id).fill.old_1_item = "Flyers";
            const at = {};
            for (const k of ["week", "during", "after"]) at[k] = texts(st, input[k]);
            const empty = texts(G.emptyState(), input.week);
            out({ at, empty });""", **SAMPLE, week=WEEK_BEFORE, during=DURING, after=AFTER)
        at = r["at"]
        self.assertEqual([at[k]["agenda"]["meeting"]["ymd"] for k in ("week", "during", "after")], ["2026-10-21", "2026-10-21", "2026-11-18"])
        self.assertEqual([at[k]["reminder"]["meeting"]["ymd"] for k in ("week", "during", "after")], ["2026-10-21", "2026-10-21", "2026-11-18"])
        self.assertEqual([at[k]["minutes"]["meeting"]["ymd"] for k in ("week", "during", "after")], ["2026-09-16", "2026-10-21", "2026-10-21"])
        self.assertEqual(at["after"]["minutes"]["subject"], "Draft minutes: sample committee meeting, Wednesday, October 21, 2026")
        self.assertIn("Next meeting: Wednesday, November 18, 2026.", at["after"]["minutes"]["text"])
        self.assertIn("Old business\n- Flyers", at["week"]["agenda"]["text"])
        for k in at:
            for w in ("agenda", "reminder", "minutes"):
                self.assertNotIn("Pat", at[k][w]["text"], "a notes_only blank is never in the paperwork")
        # a line whose blanks are all empty goes, and a heading left with nothing; a line with no blank stays
        self.assertNotIn("Old business", r["empty"]["agenda"]["text"])
        self.assertIn("Attended: about ___ members", r["empty"]["minutes"]["text"])
        self.assertNotIn("[", r["empty"]["agenda"]["text"])

    def test_the_reminder_names_the_committee_as_the_spanish_pages_do(self):
        """{paper:committee_es}: config/site.yml site.committee_es, as every Spanish page says it — and the player's
        own words when a deck's file carries none."""
        r = deck_js(self, """
            const st = G.emptyState();
            const named = plain(texts(st, input.week).reminder);
            delete D.paperwork.committee_es;
            out({ named, unnamed: plain(texts(st, input.week).reminder) });""", **SAMPLE, week=WEEK_BEFORE)
        es = r["named"]["blocks"][1]
        self.assertEqual(es["lang"], "es")
        self.assertTrue(es["text"].startswith("Recordatorio: el Comité de Grapevine y La Viña de NETA 65 se reúne el "
                                              "miércoles, 21 de octubre de 2026, 7:00"), es["text"])
        first, speaker = es["text"].split("\n")
        self.assertTrue(first.endswith("hora del Centro, por Zoom."), es["text"])
        self.assertEqual(speaker, "Orador(a) invitado(a): Rick W. — Ex delegado, Área 65 (Panel 73), sobre Grapevine como herramienta del Paso Doce")
        self.assertTrue(r["unnamed"]["blocks"][1]["text"].startswith("Recordatorio: el Comité de Grapevine y La Viña se reúne el "),
                        r["unnamed"]["blocks"][1]["text"])
        self.assertNotIn("{paper", r["named"]["text"] + r["unnamed"]["text"])

    def test_start_next_month_then_undo(self):
        r = deck_js(self, """
            const st = G.emptyState();
            const ds = G.deckState(st, D.id);
            Object.assign(ds.fill, { old_1_item: "Flyers", old_1_status: "keep working", action_1_what: "Print them",
                                     action_1_who: "the alternate chair", minutes_month: "September 2026" });
            ds.checks["chair-checklist"] = ["0", "1"];
            const before = JSON.stringify(plain(ds.fill));
            const plan = plain(G.nextMonthPlan(D, st, ms(input.after)));
            const res = plain(G.startNextMonth(D, st, ["action_1", "old_1"], ms(input.after)));
            const after = { fill: plain(ds.fill), checks: plain(ds.checks), held: ds.prev.held,
                            agenda: texts(st, input.after).agenda.meeting.ymd, done: G.nextMonthPlan(D, st, ms(input.next_day)).done };
            const undo = G.undoNextMonth(D, st);
            out({ plan, res, after, undo, again: G.undoNextMonth(D, st), same: before === JSON.stringify(plain(ds.fill)),
                  checks: plain(ds.checks), prev: ds.prev });""", **SAMPLE, after=AFTER, next_day=NEXT_DAY)
        self.assertEqual([(i["id"], i["checked"]) for i in r["plan"]["items"]], [("action_1", True), ("old_1", False)])
        self.assertEqual(r["plan"]["room"], 1)
        self.assertEqual(r["res"]["carried"], 1, "the room of old business at most: old business still open first")
        self.assertEqual(r["after"]["fill"], {"old_1_item": "Flyers", "minutes_month": "October 2026"})
        self.assertEqual(r["after"]["checks"], {})
        self.assertEqual(r["after"]["held"], "2026-10-21")
        self.assertEqual(r["after"]["agenda"], "2026-11-18", "the agenda moves on at once")
        self.assertTrue(r["after"]["done"])
        self.assertTrue(r["undo"])
        self.assertFalse(r["again"])
        self.assertTrue(r["same"])
        self.assertEqual(r["checks"], {"chair-checklist": ["0", "1"]})
        self.assertIsNone(r["prev"])


class LastStart(unittest.TestCase):
    """The Undo of "Start next month" — and the draft minutes' word that their meeting's details are gone — last
    until the next meeting begins (G.lastStart): from then on the details are that meeting's own, the minutes are
    for it, and an Undo would put the details from before the start over them."""

    def test_until_the_next_meeting_begins(self):
        r = deck_js(self, """
            const st = G.emptyState();
            const ds = G.deckState(st, D.id);
            ds.fill.action_1_what = "Print them";
            const none = G.lastStart(D, ds, ms(input.after));
            G.startNextMonth(D, st, ["action_1"], ms(input.after));
            // the chair types November's details after the start
            ds.fill.action_1_what = "Order the 2027 calendars";
            const at = (k) => {
              const ls = plain(G.lastStart(D, ds, ms(input[k])));
              return { ls, minutes: texts(st, input[k]).minutes.meeting.ymd, done: G.nextMonthPlan(D, st, ms(input[k])).done };
            };
            const seen = {};
            for (const k of ["after", "next_day", "nov_before", "nov_during", "nov_after"]) seen[k] = at(k);
            G.startNextMonth(D, st, ["action_1"], ms(input.nov_after));
            out({ none, seen, again: plain(G.lastStart(D, ds, ms(input.nov_after))), noDeck: G.lastStart(D, null, ms(input.after)) });""",
            **SAMPLE, after=AFTER, next_day=NEXT_DAY, nov_before=NOV_BEFORE, nov_during=NOV_DURING, nov_after=NOV_AFTER)
        self.assertIsNone(r["none"], "nothing started")
        self.assertIsNone(r["noDeck"])
        seen = r["seen"]
        for k in ("after", "next_day", "nov_before"):
            with self.subTest(at=k):
                self.assertEqual(seen[k]["ls"], {"at": "2026-10-22T01:30:00.000Z", "held": "2026-10-21", "current": True})
                self.assertEqual(seen[k]["minutes"], "2026-10-21", "the minutes of the meeting it closed: the word and the Undo")
                self.assertTrue(seen[k]["done"])
        for k in ("nov_during", "nov_after"):
            with self.subTest(at=k):
                self.assertFalse(seen[k]["ls"]["current"], "the November meeting has begun: no word, no Undo")
                self.assertEqual(seen[k]["minutes"], "2026-11-18", "the minutes are November's, from November's details")
                self.assertFalse(seen[k]["done"], "and next month can be started again")
        self.assertEqual(r["again"], {"at": "2026-11-19T02:30:00.000Z", "held": "2026-11-18", "current": True})

    def test_a_start_with_no_meeting_dates(self):
        """A site with no meeting dates (no `meeting:` settings): the start closed no dated meeting, and it stays
        undoable."""
        r = deck_js(self, """
            D.paperwork.meetings = [];
            const st = G.emptyState();
            const ds = G.deckState(st, D.id);
            ds.fill.action_1_what = "Print them";
            G.startNextMonth(D, st, ["action_1"], ms(input.after));
            out({ ls: plain(G.lastStart(D, ds, ms(input.nov_after))), minutes: texts(st, input.nov_after).minutes.meeting });""",
            **SAMPLE, after=AFTER, nov_after=NOV_AFTER)
        self.assertEqual(r["ls"], {"at": "2026-10-22T01:30:00.000Z", "held": "", "current": True})
        self.assertIsNone(r["minutes"])


class Player(unittest.TestCase):
    """The player's wiring (src/assets/js/presentations.js, the macro): the tab only for a deck with paperwork, and
    e-mails that open with no address filled in."""

    def test_wiring(self):
        js = (ROOT / "src" / "assets" / "js" / "presentations.js").read_text(encoding="utf-8")
        macro = (ROOT / "src" / "_includes" / "macros" / "presentations.njk").read_text(encoding="utf-8")
        self.assertIn('var TABS = ["version", "slides", "edit", "add", "details", "prepare", "paper", "save"];', js)
        self.assertIn('["paper", "mail"]', macro)
        self.assertIn('{% if tb[0] == "paper" %} hidden{% endif %}', macro, "hidden until the deck has paperwork")
        self.assertIn("qa('[data-gvp-tab=\"paper\"]').forEach(function (t) { t.hidden = !hasPaper(); });", js)
        # every mailto: link has no address: the chair puts every one in BCC
        self.assertEqual(set(re.findall(r'"mailto:([^"]*)"', js)), {"?subject="})
        self.assertIn("if (G.summary(d).any || d.last || d.prev) out.decks[id] = d;", js, "the Undo is stored")
        for name in ("copy", "mail", "calendar-plus"):
            self.assertIn(f'"{name}"', macro.split('<template id="gvp-icons">', 1)[1], name)


if __name__ == "__main__":
    unittest.main()
