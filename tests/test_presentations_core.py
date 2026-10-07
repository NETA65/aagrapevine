"""The workshop presentations' logic (src/assets/js/presentations-core.js, window.GVP) run in Node.js.

What a presenter relies on, checked against values worked out by hand:
  * the facts of the day  — a {live:…} value switches at each of its `steps` (and the old `from` / `then`) and
                            gives its `fallback` from `until` (or when empty) by the VIEWER's clock; any key of the
                            map works (keys added later too); show_from / show_until and `when: "price_notice"`
                            leave slides out; a live block's rows: the past ones out, a monthly series once
                            (unless `series: "all"`), then `limit` / `limit_each`, an issue's themes never cut
                            apart, meetings until they end
  * the current version   — facilitator slides never shown, `starts_off`, `hide`, `only` (also a slide that starts
                            off), `version_fields` before the presenter's own edits (an edit of a version's own
                            words stays in that version), the presenter's own switches on top, numbering
  * the clock             — version_minutes, an edited `minutes` (typing back the version's own is no edit), the
                            TIME line ("about 1½ minutes … 0:08"), the agenda's times from `from` (a row whose
                            slides are all left out is dropped; a typed time wins; an agenda back to the version's
                            own is no edit)
  * text                  — tokens replaced first, then **bold**, _italic_ at word edges only (@handle_names stay),
                            [label](url) with checked addresses only (never javascript:), [hint] blanks; a
                            notes_only blank never on a slide; nothing ever becomes HTML; {lang:es} spans; {ui:…}
                            in the page's language; notes lines {only:…} / {not:…}; "(not in this version)" read
                            as one; {fill:constructor} and friends are unknown tokens
  * the presenter's state — normState never throws on garbage; edits remember the slide's hash ("Changed since you
                            edited it"); added slides; moving; an updated deck (reconcile)
  * "my version" files    — export → import gives the same version back; strict refusal of foreign, broken,
                            oversized or HTML-carrying files
  * reset + Undo          — a deck, all four
  * the four real decks   — every text of every slide goes through the core; the information workshop's agenda
                            computes the times the deck's author wrote; each version's length
The file runs in a vm context, as tests/test_expenses_core.py runs expenses-core.js. Skipped without Node.js.

    python -m unittest tests.test_presentations_core -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402

CORE = "src/assets/js/presentations-core.js"

# Instants used below (UTC). The committee's meeting on Wednesday, October 21, 2026 ends 8 PM Central = 01:00Z.
OCT2 = "2026-10-02T15:00:00.000Z"
OCT22 = "2026-10-22T02:00:00.000Z"
JAN2 = "2027-01-02T15:00:00.000Z"
FEB2 = "2027-02-02T15:00:00.000Z"


def slide(sid, layout, title, minutes=1, **extra):
    """A slide as the deck's JSON has it (src/pages/presentations-json.11ty.js)."""
    s = {"id": sid, "layout": layout, "h": "h-" + sid, "n_default": None, "part": None, "accent": "gv",
         "eyebrow": "Sample", "title": title, "notes": f"SAY: the notes of {title}.", "minutes": minutes,
         "optional": False, "starts_off": False, "facilitator": False, "handout": False, "version_notes": {},
         "show_from": None, "show_until": None, "when": None, "data": None}
    s.update(extra)
    if s["facilitator"]:
        s["minutes"] = None
    return s


def sample_deck():
    """A small deck with every rule the core applies (hand-checked numbers in the tests)."""
    slides = [
        slide("title", "title", "Sample Workshop", 1, subtitle="Our meeting in print",
              lines=["{fill:presenter} · {live:panel}", "{fill:date} · {fill:place}"],
              notes="SAY: My name is {fill:first_name}. Welcome.\nDO: Fill in {fill:date}."),
        slide("agenda", "agenda", "Our hour", 0.5, items=[
            {"time": "0:00", "title": "Welcome", "from": "title"},
            {"time": "0:05", "title": "Part 1", "from": "part-1"},
            {"time": "0:20", "title": "Extras", "from": "extra-1"},
            {"time": "0:30", "title": "Prices", "from": "prices"},
            {"time": "0:40", "title": "Closing", "from": "closing"},
            {"time": "Later", "title": "Coffee"},
        ]),
        slide("part-1", "section", "Part one", 0.5, number=1, subtitle="The basics", accent="lv",
              part={"n": 1, "title": "Part one"}),
        slide("basics", "bullets", "The basics", 2, items=["One **bold** point", {"text": "Two", "items": ["2a", "2b"]}],
              takeaway="Remember {slide:closing}.", version_minutes={"short": 1}),
        slide("extra-1", "bullets", "Extra one", 3, items=["x"], optional=True),
        slide("extra-2", "text", "Extra two", 2, body="Body", optional=True),
        slide("topic", "bullets", "Topic of the month", 5, items=["t"], optional=True, starts_off=True),
        slide("holiday", "bullets", "Holidays", 1, items=["h"],
              show_from="2026-11-15T06:00:00.000Z", show_until="2027-01-01T05:59:59.999Z"),
        slide("prices", "bullets", "New prices", 1, items=["{live:price_change_note}"], when="price_notice"),
        slide("closing", "closing", "Thank you", 0.5, message="See you {live:meeting_next}", lines=["{live:email}"]),
        slide("checklist", "bullets", "Before the workshop", items=["Fill in {fill:date}", "Print"], facilitator=True,
              checklist=True),
    ]
    # as the build shapes them (eleventy/filters/presentations.js shapeDeck): a section starts a part, whose slides
    # take its accent and the eyebrow "Part 1 · …"
    part = None
    for s in slides:
        if s["layout"] == "section":
            part = {"n": s["number"], "title": s["title"], "accent": s["accent"]}
        if part:
            s["part"] = {"n": part["n"], "title": part["title"]}
            s["accent"] = part["accent"]
            if s["eyebrow"] == "Sample":
                s["eyebrow"] = f"Part {part['n']} · {part['title']}"
    return {
        "app": "gv-presentation", "schema": 1, "id": "sample", "lang": "en", "title": "Sample Workshop",
        "short": "Sample", "eyebrow": "Sample", "footer": "Committee · {live:panel}", "minutes": 16,
        "as_of": "October 2, 2026", "version": "v1", "site": {"url": "https://x.org/aagrapevine/", "host": "x.org/aagrapevine"},
        "presets": [
            {"id": "full", "label": {"en": "Full", "es": "Completo"}, "minutes": 16, "hide": [], "only": None, "note": None},
            {"id": "short", "label": {"en": "Short", "es": "Corto"}, "minutes": 9, "hide": ["extra-1", "extra-2"], "only": None,
             "note": None},
            {"id": "visit", "label": {"en": "Visit", "es": "Visita"}, "minutes": 7, "hide": [],
             "only": ["title", "basics", "topic", "closing"], "note": None},
        ],
        "fillins": [
            {"key": "date", "label": {"en": "Date", "es": "Fecha"}, "hint": "Month DD, YYYY", "default": "", "shared": False, "notes_only": False},
            {"key": "place", "label": {"en": "Place", "es": "Lugar"}, "hint": "Place, or Zoom", "default": "", "shared": False, "notes_only": False},
            {"key": "presenter", "label": {"en": "Presenter", "es": "Presenta"}, "hint": "Service position",
             "default": "Area 65 Chair", "shared": True, "notes_only": False},
            {"key": "first_name", "label": {"en": "First name", "es": "Nombre"}, "hint": "first name", "default": "",
             "shared": True, "notes_only": True},
            {"key": "spare", "label": {"en": "Spare", "es": "Extra"}, "hint": "spare", "default": "", "shared": False, "notes_only": False},
        ],
        "live": {
            "panel": "Panel 77 (2027–2028)",
            "email": "grapevine@neta65.org",
            "meeting_next": {"value": "Wednesday, October 21, 2026", "from": "2026-10-22T01:00:00.000Z",
                             "then": "Wednesday, November 18, 2026"},
            "price_change_note": {"value": "Prices change on January 1, 2027.", "from": "2027-01-01T06:00:00.000Z",
                                  "then": "New prices since January 1, 2027.", "until": "2027-02-01T06:00:00.000Z"},
            "meeting_after": "Wednesday, November 18, 2026",
            "handle": "@alcoholicsanonymous_gv",
        },
        "slides": slides,
    }


# Loads the core into a fresh vm context: G = window.GVP, D = the sample deck, ms(iso) = its instant.
LOAD = r"""
import vm from "node:vm";
const ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync("src/assets/js/presentations-core.js", "utf8"), ctx, { filename: "presentations-core.js" });
const G = ctx.GVP;
const D = input.deck;
const ms = (s) => Date.parse(s);
const plain = (v) => JSON.parse(JSON.stringify(v));
const ids = (cur) => cur.shown.map((e) => e.id);
const T = (text, cur, state, where, extra) => G.rich(text, Object.assign({ deck: cur.deck, state, live: cur.live, cur, where: where || "slide", base: "/aagrapevine/", lang: "en" }, extra || {}));
"""


def core(case: unittest.TestCase, js: str, data: dict | None = None, deck: dict | None = None, **kw):
    """Run `js` (it calls out(value)) with the core loaded; returns the value."""
    return run_js(case, LOAD + js, data={"deck": deck or sample_deck(), **(data or {})}, needs_modules=False, **kw)


class Facts(unittest.TestCase):
    def test_live_text_switches_by_the_viewers_clock(self):
        r = core(self, """
          const v = D.live.meeting_next, n = D.live.price_change_note;
          out({
            plain: G.liveText("Panel 77", ms("2026-10-02T00:00:00Z")),
            before: G.liveText(v, ms("2026-10-22T00:59:59Z")), after: G.liveText(v, ms("2026-10-22T01:00:00Z")),
            note: [ms("2026-12-31T12:00:00Z"), ms("2027-01-01T06:00:00Z"), ms("2027-01-31T12:00:00Z"), ms("2027-02-01T06:00:00Z")].map((t) => G.liveText(n, t)),
            odd: [G.liveText(null, 0), G.liveText(42, 0), G.liveText({ value: "a", from: "nonsense", then: "b" }, 0), G.liveText({ value: "a", until: "2000-01-01T00:00:00Z" }, Date.now()), G.liveText({}, 0)],
            all: G.liveValues(D.live, ms("2026-10-02T15:00:00Z")),
          });""")
        self.assertEqual(r["plain"], "Panel 77")
        self.assertEqual(r["before"], "Wednesday, October 21, 2026")
        self.assertEqual(r["after"], "Wednesday, November 18, 2026")
        self.assertEqual(r["note"], ["Prices change on January 1, 2027.", "New prices since January 1, 2027.",
                                     "New prices since January 1, 2027.", ""])
        self.assertEqual(r["odd"], ["", "42", "a", "", ""])
        # generic over the map: keys the build adds later (SPEC UPDATE 2: meeting_after …) come through
        self.assertEqual(r["all"]["meeting_after"], "Wednesday, November 18, 2026")
        self.assertEqual(r["all"]["handle"], "@alcoholicsanonymous_gv")

    def test_windows_and_the_price_notice(self):
        r = core(self, """
          const at = (iso) => ids(G.current(D, G.emptyState(), "", ms(iso)));
          out({ oct: at("2026-10-02T15:00:00Z"), nov: at("2026-11-20T15:00:00Z"), jan: at("2027-01-02T15:00:00Z"),
                feb: at("2027-02-02T15:00:00Z"),
                first: G.inWindow(D.slides[7], ms("2026-11-15T06:00:00Z"), D.live), last: G.inWindow(D.slides[7], ms("2027-01-01T05:59:59.999Z"), D.live),
                gone: G.inWindow(D.slides[7], ms("2027-01-01T06:00:00Z"), D.live) });""")
        base = ["title", "agenda", "part-1", "basics", "extra-1", "extra-2"]
        self.assertEqual(r["oct"], base + ["prices", "closing"])         # the notice is on (the build said so)
        self.assertEqual(r["nov"], base + ["holiday", "prices", "closing"])
        self.assertEqual(r["jan"], base + ["prices", "closing"])          # holidays over; the notice says "New prices since …"
        self.assertEqual(r["feb"], base + ["closing"])                    # the notice is over
        self.assertEqual([r["first"], r["last"], r["gone"]], [True, True, False])


class Versions(unittest.TestCase):
    def test_presets_and_switches(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const full = G.current(D, st, "", at);
          const short = G.current(D, st, "short", at);
          const visit = G.current(D, st, "visit", at);
          const why = Object.fromEntries(full.list.map((e) => [e.id, e.why]));
          // the presenter's switches, on top of the version
          G.setShown(full, "topic", true);
          G.setShown(full, "extra-1", false);
          const refused = [G.setShown(full, "checklist", true), G.setShown(full, "holiday", true)];
          const mine = G.current(D, st, "", at);
          // a switch equal to what the version does is not remembered
          G.setShown(mine, "extra-1", true);
          const back = plain(st.decks.sample);
          out({ full: ids(full), short: ids(short), visit: ids(visit), why, mine: ids(mine), refused,
                hidden: back.hidden, shown: back.shown, n: full.shown.map((e) => e.n) });""")
        self.assertEqual(r["full"], ["title", "agenda", "part-1", "basics", "extra-1", "extra-2", "prices", "closing"])
        self.assertEqual(r["short"], ["title", "agenda", "part-1", "basics", "prices", "closing"])
        # `only` shows exactly its slides, also one that starts off (SPEC UPDATE 2)
        self.assertEqual(r["visit"], ["title", "basics", "topic", "closing"])
        self.assertEqual(r["why"]["topic"], "starts_off")
        self.assertEqual(r["why"]["checklist"], "facilitator")
        self.assertEqual(r["why"]["holiday"], "window")
        self.assertEqual(r["mine"], ["title", "agenda", "part-1", "basics", "extra-2", "topic", "prices", "closing"])
        self.assertEqual(r["refused"], [False, False])
        self.assertEqual(r["hidden"], [])
        self.assertEqual(r["shown"], ["topic"])
        self.assertEqual(r["n"], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_the_clock(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const full = G.current(D, st, "", at);
          const short = G.current(D, st, "short", at);
          const lines = full.shown.map((e) => G.timeLine(e));
          G.setField(D, full.ds, "basics", "minutes", 4);
          const edited = G.current(D, st, "short", at);
          out({ total: full.total, short: short.total, lines,
                basicsShort: short.byId.basics.mins, edited: edited.byId.basics.mins, editedTotal: edited.total,
                about: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.4, 2.9, 12].map(G.aboutText),
                clock: [0, 0.4, 7.5, 59.75, 75, 125].map(G.clock),
                hidden: G.timeLine(full.byId.topic) });""")
        # 1 + 0.5 + 0.5 + 2 + 3 + 2 + 1 (prices) + 0.5 = 10.5
        self.assertEqual(r["total"], 10.5)
        # short: extra-1 / extra-2 out, and basics takes its version_minutes (1): 1 + 0.5 + 0.5 + 1 + 1 + 0.5
        self.assertEqual(r["short"], 4.5)
        self.assertEqual(r["basicsShort"], 1)
        self.assertEqual(r["edited"], 4)                 # an edited `minutes` wins over version_minutes
        self.assertEqual(r["editedTotal"], 7.5)
        self.assertEqual(r["lines"][0], "TIME: about 1 minute. You should be at about 0:01 when you move on.")
        self.assertEqual(r["lines"][3], "TIME: about 2 minutes. You should be at about 0:04 when you move on.")
        self.assertEqual(r["lines"][4], "TIME: about 3 minutes (optional: it can go when you're running late). "
                                        "You should be at about 0:07 when you move on.")
        self.assertEqual(r["about"], ["15 seconds", "30 seconds", "45 seconds", "1 minute", "1¼ minutes", "1½ minutes",
                                      "1¾ minutes", "2 minutes", "2½ minutes", "3 minutes", "12 minutes"])
        self.assertEqual(r["clock"], ["0:00", "0:00", "0:08", "1:00", "1:15", "2:05"])
        self.assertEqual(r["hidden"], "")

    def test_agenda_times_follow_the_version(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const rows = (cur) => G.agendaRows(cur.byId.agenda, cur).map((x) => [x.time, x.title, x.auto]);
          const full = G.current(D, st, "", at), short = G.current(D, st, "short", at);
          // a typed time wins over the computed one; an empty one is computed (the form writes "" for the rows
          // with `from` — its "auto" — unless a time was typed)
          const items = plain(D.slides[1].items).map((it) => (it.from ? Object.assign(it, { time: "" }) : it));
          items[1].time = "0:10";
          G.setField(D, full.ds, "agenda", "items", items);
          const typed = G.current(D, st, "", at);
          out({ full: rows(full), short: rows(short), typed: rows(typed) });""")
        # full: title 0 · agenda 1 · part-1 1.5 · basics 2 · extra-1 4 · extra-2 7 · prices 9 · closing 10
        self.assertEqual(r["full"], [["0:00", "Welcome", True], ["0:02", "Part 1", True], ["0:04", "Extras", True],
                                     ["0:09", "Prices", True], ["0:10", "Closing", True], ["Later", "Coffee", False]])
        # short: the extras are left out, so their row goes (and basics takes its 1 minute of version_minutes)
        self.assertEqual(r["short"], [["0:00", "Welcome", True], ["0:02", "Part 1", True], ["0:03", "Prices", True],
                                      ["0:04", "Closing", True], ["Later", "Coffee", False]])
        self.assertEqual(r["typed"], [["0:00", "Welcome", True], ["0:10", "Part 1", False], ["0:04", "Extras", True],
                                      ["0:09", "Prices", True], ["0:10", "Closing", True], ["Later", "Coffee", False]])


class Text(unittest.TestCase):
    def test_tokens(self):
        r = core(self, """
          const st = G.emptyState();
          const cur = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          const S = (t, where) => G.subst(t, { deck: D, state: st, live: cur.live, cur, where: where || "slide" });
          const empty = [S("{fill:date}"), S("{fill:presenter}"), S("{fill:first_name}"), S("{fill:first_name}", "notes")];
          st.decks.sample.fill.date = "October 3, 2026";
          st.shared.fill.presenter = "District 22 GVR";
          st.shared.fill.first_name = "Ana";
          st.decks.sample.fill.place = "  \\uE000sneaky\\uE001  ";
          const set = [S("{fill:date}"), S("{fill:presenter}"), S("{fill:first_name}"), S("{fill:first_name}", "notes"), S("{fill:place}")];
          G.setShown(cur, "extra-1", false);
          const cur2 = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          const S2 = (t) => G.subst(t, { deck: D, state: st, live: cur2.live, cur: cur2, where: "slide" });
          out({ empty, set,
                live: S("{live:panel} · {live:meeting_after} · {live:nope} · {fill:nope} · {other:x}"),
                refs: [S2("slide {slide:basics}"), S2("{slide:extra-1}"), S2("{slide:checklist}"), S2("{slide:nope}")],
                injected: S("a \\uE000x\\uE001 b") });""")
        b = lambda s: "" + s + ""  # noqa: E731 — an empty blank, as the formatter receives it
        self.assertEqual(r["empty"], [b("Month DD, YYYY"), "Area 65 Chair", b("first name"), b("first name")])
        # a notes_only blank never shows its value on a slide — only in the notes
        self.assertEqual(r["set"], ["October 3, 2026", "District 22 GVR", b("first name"), "Ana", "sneaky"])
        self.assertEqual(r["live"], "Panel 77 (2027–2028) · Wednesday, November 18, 2026 · {live:nope} · {fill:nope} · {other:x}")
        self.assertEqual(r["refs"], ["slide 4", "(not in this version)", "(not in this version)", "{slide:nope}"])
        self.assertEqual(r["injected"], "a x b")

    def test_inline_formatting(self):
        r = core(self, """
          const F = (s, o) => G.inline(s, Object.assign({ base: "/aagrapevine/", lang: "en" }, o || {}));
          out({
            bold: F("a **b _c_ d** e"),
            handle: F("Instagram: @alcoholicsanonymous_gv · @alcoholicosanonimos_lv and first_name"),
            italic: F("_The Language of the Heart:_ Bill W.'s writings, **_Pasos_**"),
            unmatched: F("2 * 3 ** 4 _x and [y]"),
            links: F("[a](https://www.aagrapevine.org) [b](/contribute/#deadlines) [c](grapevine@neta65.org) [d](mailto:x@y.org) [e](javascript:alert(1)) [f](http://x.org) [g](//evil.org)"),
            es: F("[b](/events/)", { lang: "es" }),
            br: F("one\\ntwo"),
            blank: F("by \\uE000end time\\uE001."),
            plain: G.plain(F("**A** [b](/x/) \\uE000c\\uE001")),
          });""")
        self.assertEqual(r["bold"], [{"t": "text", "v": "a "}, {"t": "b", "c": [{"t": "text", "v": "b "}, {"t": "i", "c": [{"t": "text", "v": "c"}]},
                                                                                {"t": "text", "v": " d"}]}, {"t": "text", "v": " e"}])
        self.assertEqual(r["handle"], [{"t": "text", "v": "Instagram: @alcoholicsanonymous_gv · @alcoholicosanonimos_lv and first_name"}])
        self.assertEqual(r["italic"][0], {"t": "i", "c": [{"t": "text", "v": "The Language of the Heart:"}]})
        self.assertEqual(r["italic"][2], {"t": "b", "c": [{"t": "i", "c": [{"t": "text", "v": "Pasos"}]}]})
        self.assertEqual(r["unmatched"], [{"t": "text", "v": "2 * 3 ** 4 _x and [y]"}])
        links = [n for n in r["links"] if n["t"] == "a"]
        self.assertEqual([n["href"] for n in links], ["https://www.aagrapevine.org", "/aagrapevine/contribute/#deadlines",
                                                       "mailto:grapevine@neta65.org", "mailto:x@y.org"])
        texts = "".join(n.get("v", "") for n in r["links"] if n["t"] == "text")
        for refused in ("e", "f", "g"):
            self.assertIn(refused, texts)        # a refused address leaves its label as plain text
        self.assertNotIn("javascript", json.dumps([n for n in r["links"] if n["t"] == "a"]))
        self.assertEqual(r["es"][0]["href"], "/aagrapevine/es/events/")
        self.assertEqual(r["br"], [{"t": "text", "v": "one"}, {"t": "br"}, {"t": "text", "v": "two"}])
        self.assertEqual(r["blank"], [{"t": "text", "v": "by "}, {"t": "blank", "v": "end time"}, {"t": "text", "v": "."}])
        self.assertEqual(r["plain"], "A b [c]")

    def test_tokens_before_formatting(self):
        r = core(self, """
          const st = G.emptyState();
          st.decks.sample = G.emptyDeck();
          st.decks.sample.fill.place = "**Room 4** <b>x</b>";
          const cur = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          out({ place: T("At {fill:place}", cur, st), handle: T("Follow {live:handle} _here_", cur, st),
                link: T("[{live:email}](grapevine@neta65.org)", cur, st) });""")
        # the presenter's own **bold** works; their "<b>" is text (the player only ever sets textContent)
        self.assertEqual(r["place"][1], {"t": "b", "c": [{"t": "text", "v": "Room 4"}]})
        self.assertEqual(r["place"][2], {"t": "text", "v": " <b>x</b>"})
        self.assertEqual(r["handle"][0], {"t": "text", "v": "Follow @alcoholicsanonymous_gv "})
        self.assertEqual(r["handle"][1], {"t": "i", "c": [{"t": "text", "v": "here"}]})
        self.assertEqual(r["link"], [{"t": "a", "href": "mailto:grapevine@neta65.org", "c": [{"t": "text", "v": "grapevine@neta65.org"}]}])

    def test_notes_labels_and_addresses(self):
        r = core(self, """
          const ui = G.noteLines("YOU FILL IN ({ui:customize} → {ui:your_details}): the month")[0];
          const st = G.emptyState();
          const cur = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          const es = { ui: { customize: "Personalizar", your_details: "Tus datos" }, lang: "es" };
          // the writing workshop's prompts (WW-11): a label in capitals with Spanish accents, the prompt in Spanish
          const esLine = G.noteLines("EN ESPAÑOL (read it aloud or paste it in the chat): {lang:es}Piensa en una vez. ¿Qué te sorprendió?{/lang}")[0];
          out({
          lines: G.noteLines("SAY: hi\\r\\nIF TIME, ASK: q?\\n\\n20-MINUTE VERSION (a district or group visit): show\\nRUNNING LATE? The slides\\n(Read it.)\\nI'm here: yes\\nAA members: all\\nFACILITATOR TIP: keep it light"),
          show: [G.showUrl("https://www.aagrapevine.org/podcasts"), G.showUrl("/events/", "x.org/aagrapevine"), G.showUrl("grapevine@neta65.org"), G.showUrl("https://aalavina.org/")],
          ui, uiEn: G.plain(T(ui.label, cur, st, "notes")), uiEs: T(ui.label, cur, st, "notes", es),
          esLine, esText: T(esLine.text, cur, st, "notes"),
          accents: G.noteLines("{lang:es}EN ESPAÑOL: léelo despacio.{/lang}\\nÚLTIMO AVISO, AÑO NUEVO: x\\nÉsta es la idea: y\\nEN ESPAÑOL, por favor"),
        });""")
        # a label naming controls: the player draws it through the tokens too (renderNotes), in the page's language
        self.assertEqual(r["ui"], {"label": "YOU FILL IN ({ui:customize} → {ui:your_details}):", "text": "the month"})
        self.assertEqual(r["uiEn"], "YOU FILL IN (Customize → Your details):")
        self.assertEqual(r["uiEs"], [{"t": "text", "v": "YOU FILL IN ("}, {"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Personalizar"}]},
                                     {"t": "text", "v": " → "}, {"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Tus datos"}]},
                                     {"t": "text", "v": "):"}])
        # capitals with accents make a label too (drawn bold), and the prompt keeps its Spanish mark
        self.assertEqual(r["esLine"], {"label": "EN ESPAÑOL (read it aloud or paste it in the chat):",
                                       "text": "{lang:es}Piensa en una vez. ¿Qué te sorprendió?{/lang}"})
        self.assertEqual(r["esText"], [{"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Piensa en una vez. ¿Qué te sorprendió?"}]}])
        self.assertEqual(r["accents"], [{"label": "EN ESPAÑOL:", "text": "{lang:es}léelo despacio.{/lang}"},
                                        {"label": "ÚLTIMO AVISO, AÑO NUEVO:", "text": "x"},
                                        {"label": "", "text": "Ésta es la idea: y"},          # a sentence, not a label
                                        {"label": "", "text": "EN ESPAÑOL, por favor"}])
        self.assertEqual([x["label"] for x in r["lines"]], ["SAY:", "IF TIME, ASK:", "20-MINUTE VERSION (a district or group visit):",
                                                             "RUNNING LATE?", "", "", "", "FACILITATOR TIP:"])
        self.assertEqual(r["lines"][0]["text"], "hi")
        self.assertEqual(r["lines"][5]["text"], "I'm here: yes")
        self.assertEqual(r["show"], ["aagrapevine.org/podcasts", "x.org/aagrapevine/events/", "grapevine@neta65.org", "aalavina.org"])


class Details(unittest.TestCase):
    def test_grouped_by_slide_and_empty_blanks(self):
        r = core(self, """
          const st = G.emptyState();
          const cur = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          const groups = G.fillGroups(cur).map((g) => [g.entry ? g.entry.id : null, g.keys]);
          const before = G.emptyBlanks(cur, st);
          st.decks.sample.fill.date = "Oct 3";
          out({ groups, before, after: G.emptyBlanks(cur, st) });""")
        # the title slide names date, place, presenter (and first_name, in its notes); "spare" is on no slide
        self.assertEqual(r["groups"], [["title", ["date", "place", "presenter", "first_name"]], [None, ["spare"]]])
        # the room never sees notes or notes_only blanks; presenter has a default
        self.assertEqual(r["before"], ["date", "place"])
        self.assertEqual(r["after"], ["place"])


class State(unittest.TestCase):
    def test_garbage_never_throws(self):
        r = core(self, """
          const junk = [null, 1, "x", "{", [], { v: 9 }, { decks: [] }, { decks: { "Bad Id": {} } },
            { shared: { fill: { date: "<script>x</script>", ok: "fine", "Bad-Key": "x" } },
              decks: { sample: { preset: "../x", hidden: ["ok-1", "../", 5], shown: "x", order: [], edits: { basics: { title: 5 }, title: { title: "Mine", _h: "h-title", nope: 1 }, agenda: { title: "A <img src=x>" } },
                added: [{ id: "my-1", layout: "bullets", title: "Mine", items: ["a"], after: "basics" }, { id: "my-2", layout: "evil" }, { id: "x", layout: "text" }],
                fill: { date: "Oct 3" }, checks: { checklist: ["0", "1.2", "x"] }, last: 3.7, last_of: -1 } } }];
          out(junk.map((j) => plain(G.normState(j))));""")
        for s in r[:8]:
            self.assertEqual(s, {"v": 1, "shared": {"fill": {}}, "decks": {}})
        last = r[8]
        # what was typed on this device stays as typed (the player only draws text); a bad key goes
        self.assertEqual(last["shared"]["fill"], {"date": "<script>x</script>", "ok": "fine"})
        d = last["decks"]["sample"]
        self.assertEqual(d["preset"], "")
        self.assertEqual(d["hidden"], ["ok-1"])
        self.assertEqual(d["shown"], [])
        self.assertIsNone(d["order"])
        self.assertEqual(list(d["edits"]), ["agenda"])  # a wrong type or an unknown field drops the whole edit
        self.assertEqual(d["edits"]["agenda"], {"title": "A <img src=x>"})
        self.assertEqual([a["id"] for a in d["added"]], ["my-1"])
        self.assertEqual(d["fill"], {"date": "Oct 3"})
        self.assertEqual(d["checks"], {"checklist": ["0", "1.2"]})
        self.assertEqual([d["last"], d["last_of"]], [3, 0])

    def test_edits_added_slides_and_order(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          let cur = G.current(D, st, "", at);
          G.setField(D, cur.ds, "basics", "title", "My basics");
          G.setField(D, cur.ds, "basics", "items", G.fromText("outline", "One\\n  sub a\\n  sub b\\nTwo"));
          G.setField(D, cur.ds, "title", "subtitle", D.slides[0].subtitle);       // the deck's own value: no edit
          const a = G.addSlide(D, cur.ds, "bullets", "basics");
          const b = G.addSlide(D, cur.ds, "qa", "basics");                       // the newest goes right after it
          G.setField(D, cur.ds, a, "title", "Added A");
          cur = G.current(D, st, "", at);
          const order1 = cur.list.map((e) => e.id);
          const basics = cur.byId.basics;
          const qaBrow = cur.byId[b].slide.eyebrow;
          G.move(cur, "closing", -3);
          cur = G.current(D, st, "", at);
          const order2 = cur.shown.map((e) => e.id);
          G.originalOrder(cur.ds);
          G.resetSlide(cur.ds, b);
          cur = G.current(D, st, "", at);
          out({ a, b, order1, order2, order3: cur.shown.map((e) => e.id), edits: plain(st.decks.sample.edits),
                title: basics.slide.title, items: basics.slide.items, edited: basics.edited, added: cur.byId[a].slide.title,
                inherited: [cur.byId[a].slide.accent, cur.byId[a].slide.eyebrow], qaBrow,
                outlineBack: G.toText("outline", basics.slide.items) });""")
        self.assertEqual([r["a"], r["b"]], ["my-1", "my-2"])
        self.assertEqual(r["order1"][3:6], ["basics", "my-2", "my-1"])
        self.assertEqual(r["edits"], {"basics": {"title": "My basics", "items": [{"text": "One", "items": ["sub a", "sub b"]}, "Two"], "_h": "h-basics"}})
        self.assertEqual(r["edited"], ["title", "items"])
        self.assertEqual(r["added"], "Added A")
        # an added slide takes its part's colours from the slide before it ("Part 1 · …" eyebrow, lv accent); an added
        # Q&A slide has no eyebrow, as the build gives the deck's own (cosmetic-eyebrows)
        self.assertEqual(r["inherited"], ["lv", "Part 1 · Part one"])
        self.assertEqual(r["qaBrow"], "")
        # three places up among ALL the slides (topic and holiday are not in the show, so it passes prices only)
        self.assertEqual(r["order2"], ["title", "agenda", "part-1", "basics", "my-2", "my-1", "extra-1", "extra-2", "closing", "prices"])
        self.assertEqual(r["order3"], ["title", "agenda", "part-1", "basics", "my-1", "extra-1", "extra-2", "prices", "closing"])
        self.assertEqual(r["outlineBack"], "One\n  sub a\n  sub b\nTwo")

    def test_an_updated_deck(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          let cur = G.current(D, st, "short", at);
          cur.ds.preset = "short";
          G.setField(D, cur.ds, "basics", "title", "Mine");
          G.setField(D, cur.ds, "extra-2", "body", "My body");
          G.setField(D, cur.ds, "closing", "message", "Bye");
          G.setShown(cur, "extra-2", true);
          G.move(cur, "closing", -1);
          cur.ds.checks.checklist = ["1"];
          // the committee changes basics, removes extra-2, adds a slide and turns closing into a text slide
          const D2 = plain(D);
          D2.version = "v2";
          D2.slides[3].h = "h-basics-2"; D2.slides[3].items = ["New point"];
          D2.slides.splice(5, 1);
          D2.slides.splice(4, 0, Object.assign(plain(D.slides[4]), { id: "brand-new", h: "h-new", title: "Brand new" }));
          const ci = D2.slides.findIndex((s) => s.id === "closing");
          D2.slides[ci] = Object.assign(plain(D2.slides[ci]), { layout: "text", body: "x", h: "h-closing-2" });
          delete D2.slides[ci].message; delete D2.slides[ci].lines;
          D2.presets = D2.presets.filter((p) => p.id !== "short");
          const rec = G.reconcile(D2, st.decks.sample);
          const cur2 = G.current(D2, st, "", at);
          const stale = cur2.byId.basics.stale;
          G.keepEdit(D2, cur2.ds, "basics");
          const kept = G.current(D2, st, "", at).byId.basics.stale;
          G.dropEdit(cur2.ds, "basics");
          out({ rec, ds: plain(st.decks.sample), order: cur2.list.map((e) => e.id), stale, kept,
                title: G.current(D2, st, "", at).byId.basics.slide.title });""")
        self.assertEqual(r["rec"]["stale"], ["basics"])
        ds = r["ds"]
        self.assertEqual(ds["shown"], [])                                    # extra-2 is gone
        self.assertNotIn("extra-2", ds["edits"])
        self.assertNotIn("closing", ds["edits"])                             # its layout has no `message` any more
        self.assertEqual(ds["preset"], "")                                   # a version the deck no longer has
        self.assertEqual(ds["seen"], "v2")
        self.assertEqual(ds["checks"], {"checklist": ["1"]})
        # the new slide takes its default place inside the presenter's own order
        self.assertEqual(r["order"][:6], ["title", "agenda", "part-1", "basics", "brand-new", "extra-1"])
        self.assertTrue(r["stale"])
        self.assertFalse(r["kept"])
        self.assertEqual(r["title"], "The basics")              # "Use the new version": the committee's slide


class Files(unittest.TestCase):
    def test_round_trip(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          let cur = G.current(D, st, "", at);
          cur.ds.preset = "short";
          G.setField(D, cur.ds, "basics", "title", "Mine **bold**");
          const a = G.addSlide(D, cur.ds, "text", "basics");
          G.setField(D, cur.ds, a, "body", "My own text");
          G.setShown(cur, "topic", true);
          cur.ds.fill.date = "Oct 3";
          st.shared.fill.presenter = "District 22 GVR";
          st.shared.fill.unrelated = "keep out";
          cur.ds.checks.checklist = ["0"];
          const file = JSON.stringify(G.exportVersion(D, st, "2026-10-02T15:00:00.000Z"));
          const res = G.validateImport(file, D);
          const st2 = G.emptyState();
          const before = G.importVersion(st2, D, res.data);
          const strip = (d) => { const x = plain(d); delete x.updated; delete x.seen; delete x.last; delete x.last_of; return x; };
          out({ ok: res.ok, file: JSON.parse(file), a: strip(st.decks.sample), b: strip(st2.decks.sample), shared: st2.shared.fill, before });""")
        self.assertTrue(r["ok"])
        self.assertEqual(r["file"]["app"], "gv-presentation-version")
        self.assertEqual(r["file"]["shared"], {"presenter": "District 22 GVR"})   # only this deck's shared blanks
        self.assertEqual(r["a"], r["b"])
        self.assertEqual(r["shared"], {"presenter": "District 22 GVR"})
        self.assertEqual(r["before"], {"deck": None, "shared": {}})

    def test_strict_refusals(self):
        good = {"app": "gv-presentation-version", "v": 1, "deck": "sample", "deck_title": "Sample", "preset": "",
                "hidden": [], "shown": [], "order": None, "edits": {}, "added": [], "fill": {}, "shared": {}, "checks": {}}

        def bad(**kw):
            f = copy.deepcopy(good)
            for k, v in kw.items():
                if v is ...:
                    f.pop(k, None)
                else:
                    f[k] = v
            return f
        files = {
            "not_json": "{nope",
            "not_ours": {"app": "gv-expenses-backup"},
            "array": [1, 2],
            "newer": bad(v=2),
            "other": bad(deck="information-workshop", deck_title="Information Workshop"),
            "unknown_key": bad(extra=1),
            "html_fill": bad(fill={"date": "<img src=x onerror=alert(1)>"}),
            "html_edit": bad(edits={"basics": {"title": "<script>alert(1)</script>"}}),
            "edit_field": bad(edits={"basics": {"onclick": "x"}}),
            "edit_type": bad(edits={"basics": {"items": "not a list"}}),
            "edit_wrong_layout_field": bad(edits={"basics": {"quote": "a quote on a bullets slide"}}),
            "added_layout": bad(added=[{"id": "my-1", "layout": "live", "title": "x", "after": "basics"}]),
            "added_id": bad(added=[{"id": "../x", "layout": "text", "title": "x", "body": "y"}]),
            "added_twice": bad(added=[{"id": "my-1", "layout": "text", "title": "x", "body": "y"}] * 2),
            "ids": bad(hidden=["ok", "<x>"]),
            "big": "x" * 2_000_001,
            "long_text": bad(edits={"basics": {"title": "x" * 700}}),
            "fill_key": bad(fill={"Bad Key": "x"}),
            "checks": bad(checks={"checklist": ["zero"]}),
        }
        r = core(self, """
          const out1 = {};
          for (const [k, f] of Object.entries(input.files)) {
            const res = G.validateImport(typeof f === "string" ? f : JSON.stringify(f), D);
            out1[k] = [res.ok, res.errors.map((e) => e.key)];
          }
          // edits of slides the deck no longer has are left out quietly (as when the deck changes)
          const gone = G.validateImport(JSON.stringify(Object.assign({}, input.good, { edits: { "old-slide": { title: "x" }, basics: { title: "Mine" } } })), D);
          out1.gone = [gone.ok, Object.keys(gone.data.deck.edits)];
          out1.good = [G.validateImport(input.good, D).ok, []];
          out(out1);""", {"files": files, "good": good})
        self.assertEqual(r["good"], [True, []])
        self.assertEqual(r["gone"], [True, ["basics"]])
        expect = {"not_json": "pres.err.not_json", "not_ours": "pres.err.not_ours", "array": "pres.err.not_ours",
                  "newer": "pres.err.newer", "other": "pres.err.other_deck", "unknown_key": "pres.err.unknown",
                  "html_fill": "pres.err.html", "html_edit": "pres.err.html", "edit_field": "pres.err.bad_edit",
                  "edit_type": "pres.err.bad_edit", "edit_wrong_layout_field": "pres.err.bad_edit",
                  "added_layout": "pres.err.bad_added", "added_id": "pres.err.bad_added", "added_twice": "pres.err.bad_added",
                  "ids": "pres.err.bad_field", "big": "pres.err.too_big", "long_text": "pres.err.bad_edit",
                  "fill_key": "pres.err.bad_field", "checks": "pres.err.bad_field"}
        for k, key in expect.items():
            with self.subTest(file=k):
                ok, keys = r[k]
                self.assertFalse(ok)
                self.assertIn(key, keys)

    def test_reset_and_undo(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const cur = G.current(D, st, "", at);
          G.setShown(cur, "extra-1", false);
          G.setField(D, cur.ds, "basics", "title", "Mine");
          cur.ds.fill.date = "Oct 3";
          st.shared.fill.presenter = "GVR";
          st.decks.other = G.normDeck({ hidden: ["a"] });
          const sum = G.summary(st.decks.sample, D);
          // the same value whatever the order of the keys (a restored deck comes back last in `decks`)
          const canon = (v) => Array.isArray(v) ? "[" + v.map(canon).join(",") + "]" : v && typeof v === "object"
            ? "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}" : JSON.stringify(v);
          const snapshot = canon(st);
          const before = G.resetDeck(st, "sample");
          const afterReset = [Object.keys(st.decks), st.shared.fill.presenter];
          G.restoreDeck(st, "sample", before);
          const undone = canon(st) === snapshot;
          const all = G.resetAll(st);
          const empty = plain(st);
          Object.assign(st, all);
          out({ sum, afterReset, undone, empty, back: canon(st) === snapshot, none: G.summary(undefined, D) });""")
        self.assertEqual(r["sum"]["hidden"], 1)
        self.assertEqual(r["sum"]["edited"], 1)
        self.assertEqual(r["sum"]["details"], 1)
        self.assertTrue(r["sum"]["changed"])
        self.assertEqual(r["afterReset"], [["other"], "GVR"])     # the shared blanks stay with one deck's reset
        self.assertTrue(r["undone"])
        self.assertEqual(r["empty"], {"v": 1, "shared": {"fill": {}}, "decks": {}})
        self.assertTrue(r["back"])
        self.assertFalse(r["none"]["any"])

    def test_form_texts(self):
        r = core(self, """
          const kinds = { outline: ["a", { text: "b", items: ["b1", "b2"] }], list: ["x", "y"], cells: ["", "Grapevine", "La Viña"],
            table: [["Print", "$36.00"], ["Digital", "$29.99"]], links: [{ label: "Events", url: "/events/", note: "All" }, { label: "Site", url: "https://x.org" }],
            flow: [{ title: "Write", text: "A story" }, { title: "Send" }] };
          const back = {};
          for (const [k, v] of Object.entries(kinds)) back[k] = G.fromText(k, G.toText(k, v));
          out({ kinds, back, num: ["1,5", "2", "-1", "x", ""].map((t) => G.fromText("num", t)),
                line: G.fromText("line", " a\\n b "), text: G.fromText("text", "\\n a \\r\\nb\\n\\n"),
                dash: G.fromText("outline", "- one\\n    - sub\\n• two") });""")
        self.assertEqual(r["back"], r["kinds"])
        self.assertEqual(r["num"], [1.5, 2, None, None, None])
        self.assertEqual(r["line"], "a b")
        self.assertEqual(r["text"], " a\nb")
        self.assertEqual(r["dash"], [{"text": "one", "items": ["sub"]}, "two"])


class LiveSteps(unittest.TestCase):
    """SPEC UPDATE 3 §1: values that keep switching ({value, steps, until, fallback}), by the viewer's clock."""

    def test_steps_until_and_fallback(self):
        r = core(self, """
          // the committee meeting: tonight's date until midnight Central after it, then the next ones; a copy opened
          // after the last known step gives the fallback, never a past date
          const m = { value: "Wednesday, October 21, 2026", steps: [
              { from: "2026-10-22T05:00:00.000Z", value: "Wednesday, November 18, 2026" },
              { from: "2026-11-19T06:00:00.000Z", value: "Wednesday, December 16, 2026" }],
            until: "2026-12-17T06:00:00.000Z", fallback: "see the committee's page" };
          const at = (v, iso, raw) => G.liveText(v, ms(iso), raw);
          out({
            night: at(m, "2026-10-22T01:30:00Z"), next: at(m, "2026-10-22T05:00:00Z"), dec: at(m, "2026-11-20T12:00:00Z"),
            stale: at(m, "2026-12-20T12:00:00Z"), raw: at(m, "2026-12-20T12:00:00Z", true),
            unsorted: at({ value: "a", steps: [{ from: "2026-03-01T00:00:00Z", value: "c" }, { from: "2026-02-01T00:00:00Z", value: "b" }] }, "2026-03-02T00:00:00Z"),
            empty: at({ value: "", fallback: "see aalavina.org for La Viña's themes" }, "2026-10-02T00:00:00Z"),
            thenEmpty: at({ value: "Sept.–Oct. 2026", from: "2026-11-01T05:00:00Z", then: "", fallback: "see aalavina.org" }, "2026-11-02T00:00:00Z"),
            old: at({ value: "x", from: "2026-11-01T05:00:00Z", then: "y" }, "2026-11-02T00:00:00Z"),
            noticeOff: G.noticeOn({ price_change_note: { value: "Prices change …", until: "2027-02-01T06:00:00Z", fallback: "see the shop" } }, ms("2027-03-01T00:00:00Z")),
          });""")
        self.assertEqual(r["night"], "Wednesday, October 21, 2026")       # during and after tonight's meeting
        self.assertEqual(r["next"], "Wednesday, November 18, 2026")
        self.assertEqual(r["dec"], "Wednesday, December 16, 2026")
        self.assertEqual(r["stale"], "see the committee's page")
        self.assertEqual(r["raw"], "")
        self.assertEqual(r["unsorted"], "c")
        self.assertEqual(r["empty"], "see aalavina.org for La Viña's themes")
        self.assertEqual(r["thenEmpty"], "see aalavina.org")
        self.assertEqual(r["old"], "y")
        self.assertFalse(r["noticeOff"])                                    # a fallback is never "a notice is on"

    def test_rows_beyond_the_limit(self):
        dl = lambda pub, due, key, theme: {"pub": pub, "due": due, "due_label": due[:10], "issue": key, "issue_key": key,  # noqa: E731
                                            "theme": theme, "theme_lang": "en", "gloss": ""}
        data = {"rows": [
            dl("lv", "2026-10-18T04:59:59.999Z", "lv-2027-05", "Recaídas"),
            dl("gv", "2026-11-02T05:59:59.999Z", "gv-2027-06", "Emotional Sobriety"),
            dl("gv", "2026-12-02T05:59:59.999Z", "gv-2027-07", "Prison A"),
            dl("gv", "2026-12-02T05:59:59.999Z", "gv-2027-07", "Prison B"),
            dl("lv", "2026-12-16T05:59:59.999Z", "lv-2027-07", "Prisiones"),
            dl("gv", "2027-01-02T05:59:59.999Z", "gv-2027-08", "Young"),
            dl("lv", "2027-02-03T05:59:59.999Z", "lv-2027-09", "Hispanos"),
        ]}
        ev = {"rows": [{"start": "2026-10-03T14:00:00Z", "end": "2026-10-03T18:00:00Z", "title": "A", "series": ""},
                       {"start": "2026-10-10T22:00:00Z", "end": "2026-10-11T01:00:00Z", "title": "Booth Oct", "series": "booth"},
                       {"start": "2026-11-14T23:00:00Z", "end": "2026-11-15T02:00:00Z", "title": "Booth Nov", "series": "booth"},
                       {"start": "2026-12-12T23:00:00Z", "end": "2026-12-13T02:00:00Z", "title": "Booth Dec", "series": "booth"},
                       {"start": "2027-03-19T23:00:00Z", "title": "Assembly"}]}
        mt = {"rows": [{"start": "2026-10-22T00:00:00Z", "end": "2026-10-22T01:00:00Z", "label": "Oct 21"},
                       {"start": "2026-11-19T01:00:00Z", "end": "2026-11-19T02:00:00Z", "label": "Nov 18"},
                       {"start": "2026-12-17T01:00:00Z", "label": "Dec 16"}]}
        r = core(self, """
          const names = (rows) => rows.map((x) => x.theme || x.title || x.label);
          const d = input.dl, e = input.ev, m = input.mt;
          out({
            oct2: names(G.liveRows("deadlines", d, { limit: 3 }, ms("2026-10-02T12:00:00Z"))),
            whole: names(G.liveRows("deadlines", d, { limit: 3 }, ms("2026-10-20T12:00:00Z"))),
            each: names(G.liveRows("deadlines", d, { pub: "both", limit: 6, limit_each: 1 }, ms("2026-10-20T12:00:00Z"))),
            each2: names(G.liveRows("deadlines", d, { limit_each: 2 }, ms("2026-11-03T12:00:00Z"))),
            dataLimit: names(G.liveRows("deadlines", Object.assign({ limit: 1 }, d), { limit: 6 }, ms("2026-10-02T12:00:00Z"))),
            dflt: G.liveRows("deadlines", d, {}, ms("2026-10-02T12:00:00Z")).length,
            later: names(G.liveRows("deadlines", d, { limit: 4 }, ms("2026-12-31T12:00:00Z"))),
            events: names(G.liveRows("events", e, { limit: 2 }, ms("2026-10-05T12:00:00Z"))),
            eventsAll: names(G.liveRows("events", e, { limit: 2, series: "all" }, ms("2026-10-05T12:00:00Z"))),
            eventsDataAll: names(G.liveRows("events", Object.assign({ series: "all" }, e), { limit: 3 }, ms("2026-10-05T12:00:00Z"))),
            eventsNov: names(G.liveRows("events", e, {}, ms("2026-10-12T12:00:00Z"))),
            eventsDec: names(G.liveRows("events", e, {}, ms("2026-12-14T12:00:00Z"))),
            meetingNight: names(G.liveRows("meeting", m, {}, ms("2026-10-22T00:30:00Z"))),
            meetingAfter: names(G.liveRows("meeting", m, {}, ms("2026-10-22T01:05:00Z"))),
            noEnd: names(G.liveRows("meeting", m, {}, ms("2026-12-17T02:30:00Z"))),
            gone: names(G.liveRows("meeting", m, {}, ms("2026-12-17T03:30:00Z"))),
            tips: G.liveRows("monthly", { tips: [{ title: "a" }, { title: "b" }, { title: "c" }, { title: "d" }] }, {}, 0).length,
          });""", {"dl": data, "ev": ev, "mt": mt})
        self.assertEqual(r["oct2"], ["Recaídas", "Emotional Sobriety", "Prison A", "Prison B"])   # the issue stays whole
        self.assertEqual(r["whole"], ["Emotional Sobriety", "Prison A", "Prison B"])              # Recaídas is past
        self.assertEqual(r["each"], ["Emotional Sobriety", "Prisiones"])                         # one of each magazine
        # two rows of each: Grapevine's are one issue's two themes, La Viña's two issues
        self.assertEqual(r["each2"], ["Prison A", "Prison B", "Prisiones", "Hispanos"])
        self.assertEqual(r["dataLimit"], ["Recaídas"])                                           # the block's own limit
        self.assertEqual(r["dflt"], 6)                                                            # deadlines: 6
        self.assertEqual(r["later"], ["Young", "Hispanos"])                                      # a copy opened in December
        # a monthly series once (its next date), then the limit — every date only when the block asks for it
        self.assertEqual(r["events"], ["Booth Oct", "Assembly"])
        self.assertEqual(r["eventsAll"], ["Booth Oct", "Booth Nov"])
        self.assertEqual(r["eventsDataAll"], ["Booth Oct", "Booth Nov", "Booth Dec"])
        self.assertEqual(r["eventsNov"], ["Booth Nov", "Assembly"])                              # the October one is past
        self.assertEqual(r["eventsDec"], ["Assembly"])                                           # no end: its start
        self.assertEqual(r["meetingNight"], ["Oct 21", "Nov 18", "Dec 16"])                      # during the meeting
        self.assertEqual(r["meetingAfter"], ["Nov 18", "Dec 16"])                                # once it has ended
        self.assertEqual(r["noEnd"], ["Dec 16"])                                                 # no end: 2 h after it starts
        self.assertEqual(r["gone"], [])
        self.assertEqual(r["tips"], 3)


class VersionText(unittest.TestCase):
    """SPEC UPDATE 3 §5: a version's own words (version_fields), notes lines per version, "(not in this version)"."""

    def deck(self):
        d = sample_deck()
        agenda = d["slides"][1]
        agenda["version_fields"] = {"short": {"title": "Our 45 minutes", "nope": "ignored"}}
        basics = d["slides"][3]
        basics["notes"] = ("SAY: all versions.\n{only:short}RUNNING LATE: the extras are out.\n{not:short}TIP: the extras "
                           "(slides {slide:extra-1}–{slide:extra-2}; or skip them) and ({slide:extra-1}).\n"
                           "{only:short,visit}BOTH: short or visit.\n{lang:es}SAY: Hola, {ui:customize}{/lang}")
        return d

    def test_version_fields_and_edits(self):
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const titles = () => [G.current(D, st, "", at).byId.agenda.slide.title, G.current(D, st, "short", at).byId.agenda.slide.title];
          const before = titles();
          const short = G.current(D, st, "short", at);
          G.setField(D, short.ds, "agenda", "title", "Our 45 minutes", "short");     // the version's own words: no edit
          const noEdit = plain(st.decks.sample.edits);
          G.setField(D, short.ds, "agenda", "title", "Mine", "short");
          const mine = titles();
          // minutes: basics is 2, and 1 in the short version
          G.setField(D, short.ds, "basics", "minutes", 1, "short");
          const m1 = plain(st.decks.sample.edits.basics || null);
          G.setField(D, short.ds, "basics", "minutes", 2, "short");
          const m2 = [plain(st.decks.sample.edits.basics), G.current(D, st, "", at).byId.basics.mins, G.current(D, st, "short", at).byId.basics.mins];
          G.setField(D, short.ds, "basics", "minutes", 1, "short");
          const m3 = plain(st.decks.sample.edits.basics || null);
          out({ before, noEdit, mine, m1, m2, m3, vv: [G.versionValue(D.slides[1], "title", "short"), G.versionValue(D.slides[3], "minutes", "short"), G.versionValue(D.slides[3], "minutes", "full")] });""",
                 deck=self.deck())
        self.assertEqual(r["before"], ["Our hour", "Our 45 minutes"])
        self.assertEqual(r["noEdit"], {})
        # the title has words of its own in the short version: the edit made there stays there (the full one keeps
        # its own title)
        self.assertEqual(r["mine"], ["Our hour", "Mine"])
        self.assertIsNone(r["m1"])                                        # typing the version's own minutes: no edit
        self.assertEqual(r["m2"][0]["minutes"], 2)                        # the full version's 2, typed in the short one
        self.assertEqual(r["m2"][1:], [2, 2])
        self.assertIsNone(r["m3"])
        self.assertEqual(r["vv"], ["Our 45 minutes", 1, 2])

    def test_an_edit_of_a_versions_own_words_stays_in_that_version(self):
        """ow-version-edit-spill: an agenda edited in the 60-minute version never shows above the full one's rows."""
        r = core(self, """
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const cur = (p) => G.current(D, st, p, at);
          const title = (p) => cur(p).byId.agenda.slide.title;
          const ds = cur("short").ds;
          G.setField(D, ds, "agenda", "title", "Our three quarters", "short");    // short has its own title
          G.setField(D, ds, "agenda", "title", "Our full hour", "full");          // made in the full version
          G.setField(D, ds, "agenda", "eyebrow", "Today", "short");              // no version has its own: every one
          const stored = plain(ds.edits.agenda);
          const seen = { full: title("full"), short: title("short"), visit: title("visit"),
                         edited: [cur("full").byId.agenda.edited, cur("short").byId.agenda.edited, cur("visit").byId.agenda.edited],
                         brows: [cur("full").byId.agenda.slide.eyebrow, cur("short").byId.agenda.slide.eyebrow] };
          // typing the version's own words back: that version's edit goes, the other one stays
          G.setField(D, ds, "agenda", "title", "Our 45 minutes", "short");
          const back = plain(ds.edits.agenda);
          // a stored or imported version: _v is checked like any edit (and a version the deck no longer has goes)
          const norm = G.normDeck({ edits: { agenda: { _h: "h-agenda", _v: { short: { title: "x" }, gone: { title: "y" }, "Bad Id": { title: "z" } } } } });
          const nested = G.cleanEdit({ _v: { short: { _v: { full: { title: "x" } } } } }, "agenda");
          const html = G.cleanEdit({ _v: { short: { title: "<b>x</b>" } } }, "agenda");
          const fine = G.cleanEdit({ title: "a", _v: { short: { title: "b", nope: 1 } } }, "agenda");
          const kept = G.normDeck({ edits: { agenda: { _h: "h-agenda", _v: { short: { title: "x" }, gone: { title: "y" } } } } });
          const rec = G.reconcile(D, kept);
          // Reset this slide: every version's edits go
          const before = plain(ds.edits.agenda);
          const had = G.resetSlide(ds, "agenda");
          const after = plain(ds.edits.agenda || null);
          // a file keeps them (export → import)
          G.setField(D, ds, "agenda", "title", "Again", "short");
          const res = G.validateImport(JSON.stringify(G.exportVersion(D, st, "2026-10-02T15:00:00.000Z")), D);
          // the committee changes the slide: "Changed since you edited it" in every version (Use the new version
          // drops the edits of all of them)
          const D2 = plain(D); D2.slides[1].h = "h-agenda-2";
          const stale = ["full", "short"].map((v) => G.current(D2, st, v, at).byId.agenda.stale);
          out({ stored, seen, back, norm: plain(norm.edits), nested: [nested.ok, nested.field], html: [html.ok, html.error],
                fine: [fine.ok, fine.error, fine.field], kept: plain(kept.edits), rec, before, had, after,
                file: [res.ok, plain(res.data.deck.edits.agenda)], stale, versioned: [G.versioned(D.slides[1], "title"), G.versioned(D.slides[1], "items"), G.versioned(D.slides[3], "minutes")] });""",
                 deck=self.deck())
        self.assertEqual(r["stored"], {"eyebrow": "Today", "_h": "h-agenda", "_v": {"short": {"title": "Our three quarters"}, "full": {"title": "Our full hour"}}})
        self.assertEqual(r["seen"]["full"], "Our full hour")
        self.assertEqual(r["seen"]["short"], "Our three quarters")
        self.assertEqual(r["seen"]["visit"], "Our hour")                       # a version without an edit of its own
        self.assertEqual(r["seen"]["edited"], [["eyebrow", "title"], ["eyebrow", "title"], ["eyebrow"]])
        self.assertEqual(r["seen"]["brows"], ["Today", "Today"])
        self.assertEqual(r["back"]["_v"], {"full": {"title": "Our full hour"}})
        self.assertEqual(r["norm"], {})                                         # "Bad Id": the whole edit is refused
        self.assertEqual(r["nested"], [False, "_v"])
        self.assertEqual(r["html"], [True, None])                              # (only a file refuses HTML-looking text)
        self.assertEqual(r["fine"], [False, "pres.err.bad_edit", "nope"])
        self.assertEqual(r["kept"], {"agenda": {"_h": "h-agenda", "_v": {"short": {"title": "x"}}}})
        self.assertTrue(r["rec"]["changed"])
        self.assertIn("_v", r["before"])
        self.assertTrue(r["had"])
        self.assertIsNone(r["after"])                                           # Reset: every version's edits gone
        self.assertEqual(r["file"], [True, {"_h": "h-agenda", "_v": {"short": {"title": "Again"}}}])
        self.assertEqual(r["versioned"], [True, False, False])
        self.assertEqual(r["stale"], [True, True])

    def test_notes_lines_per_version(self):
        r = core(self, """
          const notes = D.slides[3].notes;
          const L = (p) => G.noteLines(notes, p).map((l) => l.label + " " + l.text);
          const st = G.emptyState();
          const at = ms("2026-10-02T15:00:00Z");
          const full = G.current(D, st, "", at), short = G.current(D, st, "short", at);
          const text = (cur) => G.noteLines(notes, cur.preset.id).map((l) => G.plain(G.rich(l.text, { deck: D, state: st, live: cur.live, cur, where: "notes", ui: { customize: "Personalizar" }, lang: "es" })));
          out({ full: L("full"), short: L("short"), visit: L("visit"), none: L(), fullText: text(full), shortText: text(short),
                es: G.rich(G.noteLines(notes, "full").pop().text, { deck: D, state: st, live: full.live, cur: full, where: "notes", ui: { customize: "Personalizar" }, lang: "es" }) });""",
                 deck=self.deck())
        self.assertEqual(r["full"][0], "SAY: all versions.")
        self.assertEqual([x.split(" ")[0] for x in r["full"]], ["SAY:", "TIP:", "SAY:"])
        self.assertEqual([x.split(" ")[0] for x in r["short"]], ["SAY:", "RUNNING", "BOTH:", "SAY:"])
        self.assertEqual([x.split(" ")[0] for x in r["visit"]], ["SAY:", "TIP:", "BOTH:", "SAY:"])
        self.assertEqual([x.split(" ")[0] for x in r["none"]], ["SAY:", "TIP:", "SAY:"])
        self.assertIn("the extras (slides 5–6; or skip them) and (5).", r["fullText"][1])
        # the Spanish line keeps its label apart; the control's name is the page's, marked as Spanish
        self.assertEqual(r["es"], [{"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Hola, "},
                                                                      {"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Personalizar"}]}]}])

    def test_left_out_reads_as_one(self):
        r = core(self, """
          const st = G.emptyState();
          const cur = G.current(D, st, "short", ms("2026-10-02T15:00:00Z"));
          const S = (t) => G.subst(t, { deck: D, state: st, live: cur.live, cur, where: "notes" });
          out([S("history (slides {slide:extra-1}–{slide:extra-2}; say one sentence instead)"),
               S("the tours ({slide:extra-1}–{slide:extra-2}, skip both or neither)"),
               S("the addresses ({slide:extra-1}), the activity ({slide:extra-2})"),
               S("slide {slide:extra-1} and slide {slide:basics}"),
               S("(Inside an issue, slides {slide:extra-1}–{slide:extra-2}; This month, {slide:basics})")]);""")
        self.assertEqual(r, ["history (not in this version; say one sentence instead)",
                             "the tours (not in this version, skip both or neither)",
                             "the addresses (not in this version), the activity (not in this version)",
                             "(not in this version) and slide 4",
                             "(Inside an issue, (not in this version); This month, 4)"])


class TextMarks(unittest.TestCase):
    def test_lang_spans_and_ui_names(self):
        r = core(self, """
          const F = (s) => G.inline(s, { base: "/aagrapevine/", lang: "en" });
          const st = G.emptyState();
          const cur = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          const S = (t, extra) => G.subst(t, Object.assign({ deck: D, state: st, live: cur.live, cur, where: "notes" }, extra || {}));
          out({
            span: F("Say {lang:es}Hola **amigo**{/lang} and smile"),
            open: F("{lang:es}Hola, soy ‹nombre›"),
            stray: F("one{/lang} two"),
            nested: F("{lang:es}uno {lang:en}two{/lang} tres{/lang}"),
            other: F("{lang:fr}non{/lang}"),
            en: S("{ui:customize} → {ui:your_details} · {ui:nope} · {ui:constructor}"),
            es: S("{ui:customize} → {ui:your_details}", { ui: { customize: "Personalizar", your_details: "Tus datos" }, lang: "es" }),
            same: S("{ui:notes}", { ui: { notes: "Notes" }, lang: "es" }),
          });""")
        self.assertEqual(r["span"], [{"t": "text", "v": "Say "}, {"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Hola "}, {"t": "b", "c": [{"t": "text", "v": "amigo"}]}]},
                                     {"t": "text", "v": " and smile"}])
        self.assertEqual(r["open"], [{"t": "lang", "lang": "es", "c": [{"t": "text", "v": "Hola, soy ‹nombre›"}]}])
        self.assertEqual(r["stray"], [{"t": "text", "v": "one two"}])          # a stray end mark: nothing
        self.assertEqual(r["nested"][0]["c"][1], {"t": "lang", "lang": "en", "c": [{"t": "text", "v": "two"}]})
        self.assertEqual(r["other"], [{"t": "text", "v": "{lang:fr}non"}])   # only es / en: the rest stays as written
        self.assertEqual(r["en"], "Customize → Your details · {ui:nope} · {ui:constructor}")
        self.assertEqual(r["es"], "{lang:es}Personalizar{/lang} → {lang:es}Tus datos{/lang}")
        self.assertEqual(r["same"], "Notes")

    def test_prototype_names_are_unknown(self):
        r = core(self, """
          const st = G.emptyState();
          st.decks.sample = G.normDeck({ added: [{ id: "my-1", layout: "bullets", title: "Mine {fill:constructor}", items: ["See {slide:constructor} {slide:toString}"], after: "basics" }] });
          const cur = G.current(D, st, "", ms("2026-10-02T15:00:00Z"));
          const S = (t) => G.subst(t, { deck: D, state: st, live: cur.live, cur, where: "slide" });
          out({ t: S("Mine {fill:constructor} {fill:__proto__} {slide:constructor} {live:constructor}"),
                blanks: G.emptyBlanks(cur, st), groups: G.fillGroups(cur).map((g) => g.keys) });""")
        self.assertEqual(r["t"], "Mine {fill:constructor} {fill:__proto__} {slide:constructor} {live:constructor}")
        self.assertEqual(r["blanks"], ["date", "place"])
        self.assertNotIn("constructor", json.dumps(r["groups"]))


class Merging(unittest.TestCase):
    def test_seen_alone_is_no_change_and_a_newer_file_is_not_pruned(self):
        r = core(self, """
          const st = G.emptyState();
          const ds = G.deckState(st, "sample");
          ds.fill.date = "Oct 3"; ds.seen = "v0";
          const D1 = Object.assign(plain(D), { built: "2026-10-02T12:00:00.000Z" });
          const first = G.reconcile(D1, ds);
          const again = G.reconcile(Object.assign(plain(D1), { version: "v9" }), ds);
          // the state was fitted to a newer file by another window: hidden / edits of slides this file lacks stay
          ds.hidden = ["brand-new"]; ds.edits["brand-new"] = { title: "x", _h: "h" }; ds.seen_built = "2026-11-01T12:00:00.000Z";
          const older = G.reconcile(D1, ds);
          const kept = plain(ds);
          const newer = G.reconcile(Object.assign(plain(D1), { built: "2026-12-01T12:00:00.000Z" }), ds);
          out({ first, again, older, kept: [kept.hidden, Object.keys(kept.edits)], after: [plain(ds).hidden, Object.keys(ds.edits)],
                newer, seen: [ds.seen, ds.seen_built], is: [G.newerSeen({ seen_built: "2026-11-01T00:00:00Z" }, D1), G.newerSeen({}, D1)] });""")
        self.assertFalse(r["first"]["changed"])       # fitting it to the file (seen, seen_built) is no change to store
        self.assertFalse(r["again"]["changed"])
        self.assertTrue(r["older"]["newer"])
        self.assertFalse(r["older"]["changed"])
        self.assertEqual(r["kept"], [["brand-new"], ["brand-new"]])
        self.assertFalse(r["newer"]["newer"])
        self.assertEqual(r["after"], [[], []])         # the newer file itself has no such slide: now pruned
        self.assertEqual(r["seen"][1], "2026-12-01T12:00:00.000Z")
        self.assertEqual(r["is"], [True, False])

    def test_agenda_back_to_the_version(self):
        r = core(self, """
          const items = D.slides[1].items;
          const rows = items.map((it) => ({ time: it.from ? "" : it.time, title: it.title, detail: it.detail || "", from: it.from || "" }));
          const typed = rows.map((x, i) => (i === 1 ? Object.assign({}, x, { time: "0:20" }) : x));
          const retitled = rows.map((x, i) => (i === 0 ? Object.assign({}, x, { title: "Hello" }) : x));
          const lastTime = rows.map((x, i) => (i === 5 ? Object.assign({}, x, { time: "Later!" }) : x));
          out([G.agendaUnchanged(rows, items), G.agendaUnchanged(typed, items), G.agendaUnchanged(retitled, items),
               G.agendaUnchanged(lastTime, items), G.agendaUnchanged(rows.slice(1), items)]);""")
        self.assertEqual(r, [True, False, False, False, False])


class Wording(unittest.TestCase):
    """The player's words follow the site's rules (README "Wording on the site"): never "PDF" — the print window
    saves "a document" — nothing about how data is gathered, no classroom words."""
    # ("auto-translated" is the site's own mark of a machine translation — common.auto_translated — not "auto")
    BANNED = re.compile(r"\b(pdf|crawl\w*|scrap\w*|robot|bot|automatically|autom[aá]ticamente|auto(?!-translated\b))\b", re.I)
    CLASSROOM = re.compile(r"\b(lessons?|lecci[oó]n(es)?|trainers?|training|quiz\w*|course|curso|curriculum|class(es)?|"
                           r"clases?|teach\w*|taught|enseñ\w*|capacitaci[oó]n|jobs?)\b", re.I)

    def test_strings(self):
        i18n = json.loads((ROOT / "src" / "_i18n" / "presentations.json").read_text(encoding="utf-8"))
        core_js = (ROOT / CORE).read_text(encoding="utf-8")
        core_words = re.search(r"var EN = \{(.*?)\n  \};", core_js, re.S).group(1)
        for key, pair in i18n.items():
            for lang in ("en", "es"):
                with self.subTest(key=key, lang=lang):
                    self.assertIsNone(self.BANNED.search(pair[lang]), pair[lang])
                    self.assertIsNone(self.CLASSROOM.search(pair[lang]), pair[lang])
        # the words the player writes on the slides themselves (presentations-core.js EN), keys left out
        words = " ".join(re.findall(r':\s*"([^"]*)"', core_words))
        self.assertIsNone(self.BANNED.search(words), words)
        self.assertIsNone(self.CLASSROOM.search(words), words)
        # one name per action, as the page has them (the owner's decision); the section of Save & share over it says
        # the same (not "Start over": that is the sessions' progress, orientation.progress_reset)
        self.assertEqual(i18n["pres.reset_deck"], {"en": "Reset to the original", "es": "Volver al original"})
        self.assertEqual(i18n["pres.reset_h"], i18n["pres.reset_deck"])
        page = json.loads((ROOT / "src" / "_i18n" / "orientation.json").read_text(encoding="utf-8"))
        self.assertNotEqual(i18n["pres.reset_h"], page["orientation.progress_reset"])
        self.assertEqual(i18n["pres.reset_all_note"], {"en": "“Reset all 4 to the original” is on the page, under the presentations.",
                                                       "es": "«Devolver las 4 al original» está en la página, debajo de las presentaciones."})
        self.assertIn("al original", i18n["pres.reset_slide"]["es"])
        self.assertIn("document", i18n["pres.save_doc"]["en"])


class RealDecks(unittest.TestCase):
    """The committee's four decks (config/presentations/), shaped by the build's own loader."""

    @classmethod
    def setUpClass(cls):
        cls.decks_dir = ROOT / "config" / "presentations"

    def test_every_text_of_every_slide(self):
        if not any(self.decks_dir.glob("*.yml")):
            self.skipTest("no deck files")
        r = run_js(self, r"""
          import vm from "node:vm";
          const P = await imp("eleventy/filters/presentations.js");
          const { decks } = P.loadDecks("config/presentations");
          const ctx = vm.createContext({ console });
          vm.runInContext(fs.readFileSync("src/assets/js/presentations-core.js", "utf8"), ctx);
          const G = ctx.GVP;
          const now = Date.now();               // the build's own clock (n_default, the facts) is today too
          const report = {};
          const strings = (v, f) => { if (typeof v === "string") f(v); else if (Array.isArray(v)) v.forEach((x) => strings(x, f)); else if (v && typeof v === "object") Object.entries(v).forEach(([k, x]) => k !== "data" && strings(x, f)); };
          // the facts the build's loader saw (data/site/shop.json: whether a price notice is on), so the default
          // version numbers its slides as the deck file's n_default does
          let shop = {};
          try { shop = JSON.parse(fs.readFileSync("data/site/shop.json", "utf8")); } catch (e) {}
          for (const d of decks) {
            const deck = P.deckJson(d, { site: { url: "https://neta65.github.io/aagrapevine/" }, db: { shop } });
            const st = G.emptyState();
            const r = { versions: {}, leftovers: [], errors: [], numbers: [], agenda: null };
            for (const p of deck.presets) {
              const cur = G.current(deck, st, p.id, now);
              r.versions[p.id] = [cur.shown.length, Math.round(cur.total * 100) / 100, p.minutes];
              // every mark the player reads ({lang:…}, {/lang}, {ui:…}, {only:…} / {not:…} at a notes line's start)
              // is gone from what it shows; the notes are read line by line for the version, as the player does
              const LEFT = /\{(?:fill|live|slide|ui|lang|only|not):[^}]*\}|\{\/lang\}/g;
              const ui = { customize: "Personalizar", your_details: "Tus datos" };
              for (const e of cur.list) {
                const show = (s, where) => {
                  try {
                    const nodes = G.rich(s, { deck, state: st, live: cur.live, cur, where, base: "/aagrapevine/", lang: "es", ui });
                    const left = G.plain(nodes).match(LEFT);
                    if (left) r.leftovers.push(e.id + ": " + left.join(", "));
                  } catch (err) { r.errors.push(e.id + ": " + err.message); }
                };
                strings(Object.assign({}, e.slide, { notes: "", version_fields: null, version_notes: null }), (s) => show(s, "slide"));
                strings(e.slide.version_notes || {}, (s) => show(s, "notes"));
                for (const n of G.noteLines(e.slide.notes, p.id)) {
                  if (!n.text) r.errors.push(e.id + ": empty notes line");
                  // the writing workshop's "EN ESPAÑOL (…):" prompts are labels, drawn bold like every other one
                  if (/^(?:\{lang:es\})?EN ESPAÑOL\b/.test(n.text)) r.errors.push(e.id + ": a label left in the text: " + n.text.slice(0, 40));
                  show(n.text, "notes");
                }
              }
              if (p.id === deck.presets[0].id) {
                r.numbers = cur.list.filter((e) => !e.added).map((e) => [e.id, e.n, e.src.n_default]).filter((x) => x[1] !== x[2]);
                const ag = cur.list.find((e) => e.slide.layout === "agenda" && (e.slide.items || []).some((i) => i.from));
                if (ag) r.agenda = G.agendaRows(ag, cur).map((x) => [x.time, ag.slide.items.find((i) => i.title === x.title).time]);
              }
            }
            report[deck.id] = r;
          }
          out(report);""", needs_modules=True)
        self.assertEqual(set(r), {"orientation-workshop", "information-workshop", "writing-workshop", "committee-meeting"})
        for deck, rep in r.items():
            with self.subTest(deck=deck):
                self.assertEqual(rep["errors"], [])
                self.assertEqual(rep["leftovers"], [], "every token of the decks is one the core knows")
                self.assertEqual(rep["numbers"], [], "the default version numbers slides as the build does")
                for pid, (n, total, minutes) in rep["versions"].items():
                    self.assertGreater(n, 3, pid)
                    self.assertTrue(0.7 * minutes <= total <= 1.3 * minutes, f"{pid}: {total} minutes, the deck says {minutes}")
                if rep["agenda"]:
                    # the full version's computed agenda times are the ones the deck's author wrote
                    self.assertEqual([a for a, _ in rep["agenda"]], [b for _, b in rep["agenda"]])


class Wiring(unittest.TestCase):
    """The player's strings: every pres.* key the scripts use exists in English and Spanish, and the macro hands
    every one of them to the script."""

    def test_keys(self):
        i18n = json.loads((ROOT / "src" / "_i18n" / "presentations.json").read_text(encoding="utf-8"))
        js = (ROOT / "src" / "assets" / "js" / "presentations.js").read_text(encoding="utf-8")
        core_js = (ROOT / CORE).read_text(encoding="utf-8")
        macro = (ROOT / "src" / "_includes" / "macros" / "presentations.njk").read_text(encoding="utf-8")
        # every whole key the script names: T("pres.key"), tInto(…, "pres.key", …), the {ui:…} control names, the
        # keys of a ternary … (not the start of one built with +, which ends in "_")
        used = {k for k in re.findall(r"""["'](pres\.[a-z0-9_.]+)["']""", js) if not k.endswith("_")}
        plural = set(re.findall(r"""\bTN\(\s*["'](pres\.[a-z0-9_.]+)["']\s*,""", js))
        plural |= set(re.findall(r"""printAll\(\s*["'](pres\.[a-z0-9_.]+)["']""", js))
        used |= plural | {k + "_one" for k in plural}
        used |= set(re.findall(r"""["'](pres\.err\.[a-z_]+)["']""", core_js))
        # the names the script builds from parts
        used |= {f"pres.print_{m}" for m in ("slides", "notes", "handout", "script")}
        used |= {f"pres.print_{m}_d" for m in ("slides", "notes", "handout", "script")}
        self.assertGreater(len(used), 140)
        # {ui:<key>}: every control the notes may name has its name in the page language (SPEC UPDATE 3 §6)
        ui_core = re.search(r"ui: \{(.*?)\}", core_js, re.S).group(1)
        ui_keys = set(re.findall(r"(\w+):", ui_core))
        ui_js = re.search(r"var UI = \(function \(\) \{\s*var keys = \{(.*?)\};", js, re.S).group(1)
        self.assertEqual(set(re.findall(r"(\w+):", ui_js)), ui_keys)
        self.assertEqual(ui_keys, {"customize", "version", "slides", "edit", "add", "your_details", "prepare", "save_share",
                                   "notes", "overview", "presenter_view", "print", "full_screen", "black_screen"})
        for key in sorted(used):
            with self.subTest(key=key):
                self.assertTrue(key in i18n, f"{key} is not in src/_i18n/presentations.json")
                self.assertTrue(i18n[key]["en"].strip() and i18n[key]["es"].strip())
                self.assertTrue(key in macro, f"{key}: the macro hands every string the script uses to it")
        for key in i18n:
            with self.subTest(macro=key):
                self.assertTrue(key in macro, f"{key}: listed in the macro, or used in its markup")

    def test_player_wiring(self):
        """Fixed in the player (the browser checks are in the review's scripts): a notes label goes through the
        tokens (notes-label-raw-ui-tokens); a version sent along by a window that could not store it is applied
        even where reading works (no-storage-silent); "Resume" only past slide 1 (status-line-columns)."""
        js = (ROOT / "src" / "assets" / "js" / "presentations.js").read_text(encoding="utf-8")
        notes = re.search(r"function renderNotes\(.*?\n  \}\n", js, re.S).group(0)
        self.assertIn("G.rich(l.label, ctx)", notes)
        self.assertNotIn('"gvp-note-label", l.label)', notes)
        sync = re.search(r"function onSync\(.*?\n  \}\n", js, re.S).group(0)
        self.assertRegex(sync, r"if \(msg\.ds\) applyState\(msg\.ds, msg\.shared\);\s*else reloadFromStorage\(\);")
        self.assertIn("if (sum.last > 1) {", js)


if __name__ == "__main__":
    unittest.main()
