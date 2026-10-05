"""The presentations ("Presentations" on /orientation/), build side: src/_data/presentations.js (the `presentations`
global — the deck files read, checked and shaped), eleventy/filters/presentations.js (the facts that keep a deck
current) and src/pages/presentations-json.11ty.js (/orientation/presentations/<id>.json, what the player on
/orientation/ opens).

  * Checker — the build stops on exactly what tests/test_presentations.py reports (its JS twin gives the same lines
    for broken decks, for the rules of SPEC "UPDATE 2" and "UPDATE 3" and for yes / no where a whole number
    belongs); a deck the player cannot use is left out; I18N_STRICT=1 stops the build; no folder, no decks;
  * SampleDecks — tests/fixtures/presentations (the sample the player and the page are developed against) passes
    both checkers and uses every layout, live kind, {live:…} key and deck feature;
  * Json — a real Eleventy build of the sample decks (PRESENTATIONS_DIR) into a temporary folder, twice: the file's
    contract (every field and its type, version_minutes, version_fields, print, lang, the accent each slide shows),
    stable hashes, tokens kept, a value for every {live:…} key (a text, or its steps, until and fallback), each live
    kind's data with its limits, absolute addresses with the base path, left out of the sitemap; no decks → no files;
  * Facts — the facts from made-up data at fixed clocks (2099, far from today): the prices' switch while an
    announced change is ahead, the notice before / after / over, the next meeting moving on when it ends, the
    meeting's day, its month and the one after it rolling over at midnight after a meeting day (also during and
    after tonight's meeting), joining it by phone, deadlines (La Viña's themes in Spanish with the English beside
    them — a machine's marked gloss_machine, never in a fact's text, a hand-written one kept —, whole issues, one
    issue-name style), this month's and the next issues and themes switching with the month, events (every date of
    a series, each with the series' id) and their filters, the next assembly, the weekly open meetings, La Viña's
    workshop, both Books of the Month, the story lines, the bulletin's newest posts, the Drive copy — and missing
    data giving each key's fallback and empty rows, never an invented value (README lists every fallback).
Offline. The Node.js parts are skipped without Node.js or without node_modules (npm ci), as in tests/nodejs.py.

    python -m unittest tests.test_presentations_build -v
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402
from test_presentations import (ACCENTS, LAYOUTS, LIVE_KEYS, LIVE_KINDS, TOKEN, UI_KEYS, UPDATE_THREE_PROBLEMS,  # noqa: E402
                                UPDATE_TWO_PROBLEMS, check_deck, strings, update_three_deck, update_two_deck)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "presentations"
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
# the site's address as src/_data/site.js reads it (SITE_URL from the GitHub Action wins)
BASE = (os.environ.get("SITE_URL") or SITE["site"]["url"]).rstrip("/") + "/"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
HASH = re.compile(r"^[0-9a-f]{10}$")
SPACES = re.compile(r"[   ]")   # Intl's thin / narrow no-break spaces in "7:00 – 8:00 PM"


WJ = "\N{WORD JOINER}"   # after the dash of a time range: never "7:00 –" / "8:00 PM" on two lines


def plain(s: str) -> str:
    return SPACES.sub(" ", s).replace(WJ, "")


def node_ready(case: unittest.TestCase) -> None:
    if not node_path():
        case.skipTest("Node.js is not installed")
    if not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
        case.skipTest("the site's npm packages are not installed (npm ci)")


def dump(deck: dict) -> str:
    return yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=10**6)


# ----------------------------------------------------------------------------------------------------------------
# A deck with a mistake of nearly every kind the checker knows (each slide and field is named after its problem)
# ----------------------------------------------------------------------------------------------------------------
NOTES = "SAY: " + " ".join(["word"] * 30)


def slide(i: str, layout: str = "bullets", **kw) -> dict:
    s = {"id": i, "layout": layout, "title": f"Slide {i}", "notes": NOTES, "minutes": 1}
    if layout == "bullets":
        s["items"] = ["An item"]
    s.update(kw)
    return {k: v for k, v in s.items() if v is not None}


def broken_deck() -> dict:
    return {
        "id": "not-the-file-name", "order": 12, "lang": "es", "title": "", "short": "S", "eyebrow": "E", "footer": "F",
        "minutes": 3, "icon": "no-such-icon-anywhere", "tone": "blue", "drive_title": 5, "colour": "red",
        "card": {"title": {"en": "a", "es": "b"}, "summary": {"en": "a"}, "audience": "both"},
        "presets": [
            {"id": "full", "label": {"en": "Full", "es": "Completa"}, "minutes": 10, "hide": ["ok"]},
            {"id": "Bad Id", "label": {"en": "x"}, "minutes": 0, "hide": ["nope"], "only": ["ok"], "extra": 1},
            {"id": "fac", "label": {"en": "F", "es": "F"}, "minutes": 2, "only": ["fac-page"], "note": "plain"},
            "not a mapping",
        ],
        "fillins": [
            {"key": "date", "label": {"en": "Date", "es": "Fecha"}, "hint": "Month DD, YYYY"},
            {"key": "first_name", "label": {"en": "a", "es": "b"}, "hint": "first name", "notes_only": True, "shared": "yes"},
            {"key": "date", "label": {"en": "a", "es": "b"}, "hint": "x"},
            {"key": "Bad", "label": {"en": "a"}, "hint": "", "default": 3, "colour": 1},
        ],
        "slides": [
            slide("ok", eyebrow="{fill:first_name}", source="", version_notes={"nope": "x", "full": ""}),
            slide("ok"),
            slide("Bad_Id"),
            "not a mapping",
            slide("odd-layout", layout="poster"),
            slide("missing", layout="quote", colour="x"),
            slide("flags", optional="yes", handout=True, starts_off=False, accent="pink", when="sunny",
                  show_from="2026-12-01", show_until="2026-01-01"),
            slide("fac-page", facilitator=True, optional=True, minutes=3, notes="DO: short"),
            slide("thin", notes="SAY: too short", minutes=None),
            slide("time-line", notes=NOTES + "\nTIME: about 2 minutes", minutes=45),
            slide("ppt", notes=NOTES + " Right-click it and choose Hide Slide in this file."),
            slide("tokens", items=["{fill:place} {fill:first_name} {live:nope} {slide:nowhere} {thing} {live:panel}",
                                   "[a link](javascript:alert) and [ok](/events/) <b>bold</b>"]),
            slide("words", items=["Our PDF training course, a class for the trainer", "Subscribe now, hurry!"],
                  allow_words=["teach", "lesson"], takeaway="Our lesson today"),
            slide("privacy", items=["Call 214-555-0199 or 1-800-631-6025", "Write to someone@gmail.com or grapevine@neta65.org"]),
            slide("columns", layout="columns", items=None, style="grid",
                  columns=[{"heading": "A", "text": "x", "items": ["y"], "accent": "teal"}, {"heading": "B", "wrong": 1}]),
            slide("columns-one", layout="columns", items=None, columns=[{"heading": "A", "text": "x"}]),
            slide("table", layout="table", items=None, header=["A", "B"], rows=[["1", "2"], ["only one"]], widths=[1]),
            slide("agenda", layout="agenda", items=[{"time": "0:00", "title": "A", "from": "nowhere"}, {"title": "no time"}]),
            slide("activity", layout="activity", items=None, steps=[], duration=0, materials=[1]),
            slide("qa", layout="qa", items=None, prompts=[{"text": "x", "items": [{"text": "too deep"}]}]),
            slide("resources", layout="resources", items=None, links=[{"label": "x", "url": "ftp://x"}, {"url": "/"}]),
            slide("credits", layout="credits", items=None, sources=[""]),
            slide("closing", layout="closing", items=None, qr="grapevine@neta65.org", lines="one line"),
            slide("flow", layout="flow", items=None, steps=[{"title": "only one"}]),
            slide("live-kind", layout="live", items=None, kind="weather"),
            slide("live-options", layout="live", items=None, kind="events", options={"limit": 40, "filter": "some", "pub": "gv"}),
            slide("live-qr", layout="live", items=None, kind="qr", options={"caption": "x"}),
            slide("section", layout="section", items=None, number=1.5, show_until=20261231),
        ],
    }


class Checker(unittest.TestCase):
    """The build's checker (eleventy/filters/presentations.js checkDeck, used by src/_data/presentations.js) is the
    twin of tests/test_presentations.py: the same lines, so a deck that passes one passes the other."""

    def setUp(self):
        node_ready(self)
        self.tmp = Path(tempfile.mkdtemp(prefix="presentations-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def js_load(self, folder: Path, now: str = "2026-10-15T17:00:00Z") -> dict:
        return run_js(self, """
            const P = await imp("eleventy/filters/presentations.js");
            out(P.loadDecks(input.dir, { now: new Date(input.now), shop: {} }));
        """, data={"dir": str(folder), "now": now})

    def test_the_same_lines_as_the_python_checker(self):
        decks = {
            "broken.yml": broken_deck(),
            # tests/test_presentations.py test_checker_catches_problems' own sample
            "sample.yml": {
                "id": "sample", "order": 1, "lang": "en", "title": "T", "short": "S", "eyebrow": "E", "footer": "F",
                "minutes": 10, "icon": "book-open", "tone": "gv",
                "card": {"title": {"en": "a", "es": "b"}, "summary": {"en": "a"}, "audience": {"en": "a", "es": "b"}},
                "presets": [{"id": "full", "label": {"en": "Full", "es": "Completo"}, "minutes": 10}],
                "fillins": [{"key": "first_name", "label": {"en": "a", "es": "b"}, "hint": "first name", "notes_only": True}],
                "slides": [{"id": f"s{i}", "layout": "bullets", "title": "Hi", "items": ["Subscribe now before prices go up"],
                            "notes": "SAY: " + "word " * 30 + "{fill:first_name} {live:nope}", "minutes": 2} for i in range(5)]
                + [{"id": "q", "layout": "quote", "title": "Q", "quote": "We teach", "credit": "X",
                    "notes": "SAY: " + "word " * 30 + "\nTIME: about 2 minutes", "minutes": 1, "eyebrow": "{fill:first_name}"}],
            },
            "few-slides.yml": {**broken_deck(), "id": "few-slides", "slides": [slide("a"), slide("b")]},
            # SPEC "UPDATE 2": version_minutes and the sums that use them (a sum of 2.5 → "3" in both), lang, a
            # shown handout, a slide's own accent, `only` naming a slide that starts off, the site's own numbers
            "update-two.yml": update_two_deck(),
            # SPEC "UPDATE 3": version_fields, {only:…} / {not:…} notes lines, {lang:…}…{/lang}, {ui:…}, the text
            # styles, `print`, limit_each, the "assemblies" filter, the new {live:…} keys, "taught"
            "update-three.yml": update_three_deck(),
            # yes / no where a whole number belongs: never 1 / 0 (Python counts True as 1, JavaScript does not)
            "booleans.yml": {**broken_deck(), "id": "booleans", "order": True,
                             "presets": [{"id": "full", "label": {"en": "Full", "es": "Completa"}, "minutes": True}],
                             "slides": broken_deck()["slides"] + [
                                 slide("yes-number", layout="section", items=None, number=True),
                                 slide("yes-limit", layout="live", items=None, kind="events", options={"limit": True})]},
        }
        for name, deck in decks.items():
            (self.tmp / name).write_text(dump(deck), encoding="utf-8")
        res = self.js_load(self.tmp)
        for name in decks:
            with self.subTest(deck=name):
                py = check_deck(self.tmp / name)
                self.assertGreater(len(py), 3)
                js = [p[len(name) + 2:] for p in res["problems"] if p.startswith(name + ": ") and "left out" not in p]
                # (sorted: the Python checker walks a few sets, whose order changes from run to run)
                self.assertEqual(sorted(js), sorted(py))
        self.assertEqual(sorted(check_deck(self.tmp / "update-two.yml")), sorted(UPDATE_TWO_PROBLEMS))
        self.assertEqual(sorted(check_deck(self.tmp / "update-three.yml")), sorted(UPDATE_THREE_PROBLEMS))
        booleans = check_deck(self.tmp / "booleans.yml")
        for expect in ("order: a whole number 1–9", "presets[0]: minutes, a whole number", "slide 29 (yes-number): number",
                       "slide 30 (yes-limit): options.limit 1–24"):
            self.assertIn(expect, booleans)

    def test_yaml_is_read_as_the_python_checker_reads_it(self):
        # YAML 1.1, as PyYAML reads it: yes / no / on / off are true / false, an unquoted date is a date (no text
        # field takes one), `<<:` merges — a deck the checker passes must not stop the build
        words = " ".join(["word"] * 30)
        text = f"""id: "yaml-eleven"
order: 3
lang: "en"
title: "T"
short: "S"
eyebrow: "E"
footer: "F"
minutes: 10
icon: "book-open"
tone: "gv"
card:
  title: {{ en: "a", es: "b" }}
  summary: {{ en: "a", es: "b" }}
  audience: {{ en: "a", es: "b" }}
presets:
  - id: "full"
    label: {{ en: "Full", es: "Completa" }}
    minutes: 10
slides:
  - &first
    id: "one"
    layout: "bullets"
    title: "One"
    items: ["Not an official AA Grapevine, Inc. presentation"]
    notes: "SAY: {words}"
    minutes: 2
    optional: yes
  - <<: *first
    id: "two"
    optional: No
    numbered: on
  - <<: *first
    id: "three"
    show_from: 2026-10-01
  - <<: *first
    id: "four"
    starts_off: YES
  - <<: *first
    id: "five"
    title: 2026-10-02
"""
        (self.tmp / "yaml-eleven.yml").write_text(text, encoding="utf-8")
        py = check_deck(self.tmp / "yaml-eleven.yml")
        self.assertEqual(sorted(py), ['slide 3 (three): show_from must be a quoted "YYYY-MM-DD"', "slide 5 (five): title required"])
        res = self.js_load(self.tmp)
        self.assertEqual(sorted(p.split(": ", 1)[1] for p in res["problems"]), sorted(py))
        deck = res["decks"][0]
        self.assertEqual([(s["id"], s["optional"], s["starts_off"]) for s in deck["slides"]],
                         [("one", True, False), ("two", False, False), ("three", True, False), ("four", True, True), ("five", True, False)])
        self.assertIs(deck["slides"][1]["numbered"], True)

    def test_the_broken_deck_is_named_line_by_line(self):
        (self.tmp / "broken.yml").write_text(dump(broken_deck()), encoding="utf-8")
        problems = "\n".join(self.js_load(self.tmp)["problems"])
        for expect in (
            "broken.yml: id 'not-the-file-name' must be the file name 'broken'", "unknown top-level field 'colour'",
            "order: a whole number 1–9", 'lang: "en"', "tone: one of", "icon 'no-such-icon-anywhere': no such lucide icon",
            "card.summary: needs an English AND a Spanish text", "slide 2: duplicate id 'ok'",
            "slide 3: id 'Bad_Id' must be lowercase", "slide 4: a mapping", "layout 'poster' is not one of",
            "'quote' needs 'credit'", "unknown field 'colour' for layout 'quote'", "optional must be true or false",
            "a facilitator slide is never in the show", "notes look thin",
            "no TIME: line in the notes", "notes still talk about PowerPoint", "minutes (0.25–30) required",
            "accent one of", 'when: "price_notice" is the only condition', 'show_until must be a quoted "YYYY-MM-DD"',
            "show_from is after show_until",
            "version_notes for an unknown version 'nope'", "version_notes.full must be text",
            "{fill:first_name} is notes_only (never on a slide)", "unknown {live:nope}", "{slide:nowhere} — no such slide",
            "unknown placeholder {thing}", "link 'javascript:alert'", "no HTML in the text", "the word 'PDF' breaks",
            "the word 'training' breaks", "the word 'course' breaks", "the word 'class' breaks", "the word 'trainer' breaks",
            "sounds like selling ('Subscribe now')", "a personal-looking phone number '214-555-0199'",
            "e-mail 'someone@gmail.com'", "allow_words 'teach' is not used", "columns[0]: text OR items",
            "columns[0]: accent one of", "columns[1]: {heading, gloss, text | items, accent}", "style panels | cards | plain",
            "columns — 2 to 4", "rows[1]: 2 cells (text)", "widths — 2 positive numbers", "items[0]: from — no slide 'nowhere'",
            'items[1]: {time: "0:08", title, detail, from}', "steps: needs a list with at least one item",
            "duration (the time card's minutes)", "materials — text or a list", "(one level of sub-items only)",
            "url 'ftp://x' — https://…", "links[1]: {label, url, note}", "sources — a list of strings",
            "qr — a site path or an https:// address", "lines — a list of strings", "steps — 2 to 6", "kind one of",
            "options.limit 1–24", "options.filter all | workshops | neta | calendar", "option 'pub' is not used by 'events'",
            "options.url (a site path or https://) for the QR code", "slide 28 (section): number",
            "presets[0]: the first version is the full one", "presets[1]: id 'Bad Id' must be unique",
            "presets[1]: hide OR only, not both", "presets[1].hide: no slide 'nope'", "presets[1]: unknown field 'extra'",
            "presets[2].only: 'fac-page' is a facilitator slide", "presets[2].note: needs an English AND a Spanish text",
            "presets[3]: a mapping", "fillins[1].shared: true or false", "fillins[2]: duplicate key 'date'",
            "fillins[3]: key 'Bad' must be lowercase", "fillins[3]: hint (what an empty blank shows) is required",
            "fillins[3].default: a string", "fillins[3]: unknown field 'colour'",
            'no slide says "Not an official AA Grapevine, Inc. presentation"', "the slides' minutes add up to",
        ):
            self.assertIn(expect, problems)
        # the verbatim exemption and the allowed words: no false alarms
        self.assertNotIn("handout", problems, "a handout may be a shown slide too (projected AND printed)")
        self.assertNotIn("the word 'lesson'", problems, "allow_words lets a quoted word through")
        self.assertNotIn("'1-800-631-6025'", problems, "a toll-free number is fine")
        self.assertNotIn("grapevine@neta65.org'", problems, "a service address is fine")
        self.assertNotIn("{live:panel}", problems)

    def test_a_deck_the_player_cannot_use_is_left_out(self):
        files = {
            "not-yaml.yml": "title: [unclosed\n  - : :\n",
            "a-list.yml": "- one\n- two\n",
            "Bad Name.yml": dump({**broken_deck(), "id": "Bad Name"}),
            "no-slides.yml": dump({**broken_deck(), "id": "no-slides", "slides": []}),
            "no-version.yml": dump({**broken_deck(), "id": "no-version", "presets": []}),
            "kept.yml": dump({**broken_deck(), "id": "kept"}),
        }
        for name, text in files.items():
            (self.tmp / name).write_text(text, encoding="utf-8")
        res = self.js_load(self.tmp)
        self.assertEqual([d["id"] for d in res["decks"]], ["kept"], "only a deck it can use (with its problems named)")
        problems = res["problems"]
        self.assertTrue(any(p.startswith("not-yaml.yml: not valid YAML") for p in problems))
        self.assertIn("a-list.yml: the file must be a mapping", problems)
        for name in ("Bad Name.yml", "no-slides.yml", "no-version.yml"):
            self.assertIn(f"{name}: left out — the player cannot use it (an id, its slides and a first version are needed)", problems)
        kept = res["decks"][0]
        # the slides it can show, in order: no slide without a mapping, a usable id or a known layout
        ids = [s["id"] for s in kept["slides"]]
        self.assertEqual(ids[:2], ["ok", "missing"], "the second 'ok', 'Bad_Id', the string and 'poster' are left out")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(s["layout"] in LAYOUTS for s in kept["slides"]))

    def test_what_the_player_gets_of_the_update_two_fields(self):
        """version_minutes it can use (a version of the deck, minutes), each slide's language, the accent it shows (a
        section's carries on, another slide's is its own), a handout that is also in the show."""
        (self.tmp / "update-two.yml").write_text(dump(update_two_deck()), encoding="utf-8")
        s = {x["id"]: x for x in self.js_load(self.tmp)["decks"][0]["slides"]}
        self.assertEqual(s["vm-ok"]["version_minutes"], {"short": 1, "long": 30, "half": 2.5})
        self.assertEqual(s["vm-unknown"]["version_minutes"], {}, "an unknown version: left out")
        self.assertEqual(s["vm-bad"]["version_minutes"], {}, "not minutes: left out")
        self.assertEqual(s["title"]["version_minutes"], {})
        self.assertEqual((s["spanish"]["lang"], s["bad-lang"]["lang"], s["title"]["lang"]), ("es", "en", "en"))
        self.assertEqual((s["title"]["accent"], s["own-accent"]["accent"], s["spanish"]["accent"]), ("gv", "lv", "gv"),
                         "a slide's own accent is its alone")
        self.assertIs(s["handout-shown"]["handout"], True)
        self.assertEqual(s["handout-shown"]["n_default"], 2, "a shown handout is in the show")
        self.assertIsNone(s["off-in-visit"]["n_default"], "a slide that starts off is not in the default version")
        # the deck's eyebrow before the first part — but none over the credits, as the decks drew them
        self.assertEqual((s["own-accent"]["eyebrow"], s["credits"]["eyebrow"]), ("E", ""))

    def test_what_the_player_gets_of_the_update_three_fields(self):
        """version_fields it can use (a version of the deck, a field the version may change: tokens kept), `print` of a
        handout page (landscape unless it says portrait; none on another slide), a text slide's style and the live
        options as written."""
        (self.tmp / "update-three.yml").write_text(dump(update_three_deck()), encoding="utf-8")
        s = {x["id"]: x for x in self.js_load(self.tmp)["decks"][0]["slides"]}
        self.assertEqual(s["agenda"]["version_fields"], {"short": {"title": "Today's plan (about 25 minutes)"},
                                                         "visit": {"items": [{"time": "0:00", "title": "Hello"}]}})
        self.assertEqual(s["activity"]["version_fields"], {"short": {"duration": 5, "steps": ["Write three lines"], "takeaway": "Short and sweet"}})
        self.assertEqual(s["vf-unknown"]["version_fields"], {}, "an unknown version: left out")
        self.assertEqual(s["vf-fields"]["version_fields"], {"short": {"items": ["ok"]}}, "minutes and notes are not the version's to change")
        self.assertEqual(s["vf-live"]["version_fields"], {"short": {"intro": "Due soon"}}, "the build makes the data from the options")
        self.assertEqual((s["vf-shape"]["version_fields"], s["vf-empty"]["version_fields"], s["title"]["version_fields"]), ({}, {}, {}))
        self.assertEqual((s["handout-portrait"]["print"], s["handout-landscape"]["print"], s["print-bad"]["print"]),
                         ("portrait", "landscape", "landscape"))
        self.assertIsNone(s["print-not-handout"]["print"], "not a handout: no print orientation")
        self.assertIsNone(s["title"]["print"])
        self.assertEqual((s["break"]["style"], s["script"]["style"], s["script"]["lang"]), ("break", "script", "es"))
        self.assertEqual(s["deadlines"]["options"], {"pub": "both", "limit": 6, "limit_each": 3})
        self.assertEqual(s["assemblies"]["options"], {"filter": "assemblies", "limit": 3})
        self.assertIn("{only:short} TRANSITION:", s["title"]["notes"], "notes lines for some versions: the player picks them")
        self.assertIn("{lang:es}bienvenidos{/lang}", s["spans"]["items"][0])

    def test_strict_stops_the_build_otherwise_it_warns(self):
        (self.tmp / "broken.yml").write_text(dump(broken_deck()), encoding="utf-8")
        script = """
            const data = await imp("src/_data/presentations.js");
            try { const r = data.default(); out({ threw: false, decks: r.decks.map((d) => d.id), problems: r.problems.length }); }
            catch (e) { out({ threw: true, message: String(e.message) }); }
        """
        strict = run_js(self, script, env={"PRESENTATIONS_DIR": str(self.tmp)})
        self.assertTrue(strict["threw"])
        self.assertIn("[presentations]", strict["message"])
        self.assertIn("broken.yml: order: a whole number 1–9", strict["message"])
        lenient = run_js(self, script, env={"PRESENTATIONS_DIR": str(self.tmp), "I18N_STRICT": ""})
        self.assertFalse(lenient["threw"])
        self.assertEqual(lenient["decks"], ["broken"])
        self.assertGreater(lenient["problems"], 40)

    def test_no_folder_or_no_files_no_decks(self):
        script = """
            const data = await imp("src/_data/presentations.js");
            out(data.default());
        """
        self.assertEqual(run_js(self, script, env={"PRESENTATIONS_DIR": str(self.tmp / "missing")}), {"decks": [], "problems": []})
        (self.tmp / "README.md").write_text("not a deck", encoding="utf-8")
        self.assertEqual(run_js(self, script, env={"PRESENTATIONS_DIR": str(self.tmp)}), {"decks": [], "problems": []})


class SampleDecks(unittest.TestCase):
    """tests/fixtures/presentations: what the player and the page are developed against — so it must use everything."""

    @classmethod
    def setUpClass(cls):
        cls.files = sorted(FIXTURES.glob("*.yml"))
        cls.decks = {f.stem: yaml.safe_load(f.read_text(encoding="utf-8")) for f in cls.files}
        cls.main = cls.decks["sample-workshop"]
        cls.slides = [s for d in cls.decks.values() for s in d["slides"]]

    def test_they_pass_the_checker(self):
        self.assertGreaterEqual(len(self.files), 2)
        for f in self.files:
            with self.subTest(deck=f.name):
                self.assertEqual(check_deck(f), [])
        self.assertEqual(len({d["order"] for d in self.decks.values()}), len(self.decks), "each deck has its own order")

    def test_the_main_sample_uses_everything(self):
        s = self.main["slides"]
        self.assertEqual({x["layout"] for x in s}, set(LAYOUTS), "every layout")
        self.assertEqual({x["kind"] for x in s if x["layout"] == "live"}, set(LIVE_KINDS), "every live kind")
        used = {m.group(2) for x in s for _, text in strings(x) for m in TOKEN.finditer(text) if m.group(1) == "live"}
        self.assertEqual(used, LIVE_KEYS, "every {live:…} key")
        fills = {m.group(2) for x in s for _, text in strings(x) for m in TOKEN.finditer(text) if m.group(1) == "fill"}
        decl = {f["key"]: f for f in self.main["fillins"]}
        self.assertEqual(fills, set(decl), "every fill-in is used")
        self.assertTrue(any(f.get("shared") for f in decl.values()) and any(f.get("notes_only") for f in decl.values()))
        self.assertTrue(any(f.get("default") for f in decl.values()))
        self.assertTrue(any(m.group(1) == "slide" for x in s for _, text in strings(x) for m in TOKEN.finditer(text)), "{slide:…}")
        presets = self.main["presets"]
        self.assertTrue(any("hide" in p for p in presets) and any("only" in p for p in presets))
        self.assertTrue(any("note" in p for p in presets))
        flags = lambda k: [x for x in s if x.get(k)]  # noqa: E731
        for k in ("version_notes", "version_minutes", "facilitator", "handout", "starts_off", "optional", "show_from",
                  "show_until", "when", "source", "takeaway", "eyebrow", "accent", "lang"):
            self.assertTrue(flags(k), k)
        self.assertEqual({x["when"] for x in flags("when")}, {"price_notice"})
        # SPEC "UPDATE 2": a handout that is also shown, a slide's own accent (not a section), a slide in Spanish, a
        # version's `only` naming a slide that starts off
        self.assertTrue(any(x.get("handout") and not x.get("facilitator") for x in s), "a shown handout")
        self.assertTrue(any(x.get("handout") and x.get("facilitator") for x in s), "a facilitator handout")
        self.assertTrue(any(x.get("accent") and x["layout"] != "section" for x in s), "a slide's own accent")
        self.assertEqual({x["lang"] for x in flags("lang")}, {"es"})
        starts_off = {x["id"] for x in flags("starts_off")}
        self.assertTrue(any(starts_off & set(p.get("only", [])) for p in presets), "`only` names a slide that starts off")
        self.assertTrue(all(set(x["version_minutes"]) <= {p["id"] for p in presets} for x in flags("version_minutes")))
        # SPEC "UPDATE 3": a version's own text for a slide (an agenda's title, an activity's time card), notes lines for
        # some versions only, Spanish spans (on a slide and a whole notes line), every control's name, the text styles,
        # four columns as cards, a short quote beside the long Preamble, a handout printed portrait and one landscape,
        # deadlines of EACH magazine, the assemblies
        self.assertTrue(any(x["layout"] == "agenda" and "title" in v for x in flags("version_fields") for v in x["version_fields"].values()))
        self.assertTrue(any(x["layout"] == "activity" and "duration" in v for x in flags("version_fields") for v in x["version_fields"].values()))
        notes = "\n".join(x["notes"] for x in s)
        for tag in ("{only:", "{not:"):
            self.assertRegex(notes, r"(?m)^" + re.escape(tag), tag)
        texts = [t for x in s for _, t in strings(x)]
        self.assertTrue(any(re.search(r"\{lang:es\}.+\{/lang\}", t) for x in s for w, t in strings(x) if w != "notes"), "a span on a slide")
        self.assertRegex(notes, r"(?m)^\{lang:es\}.*\{/lang\}$", "a whole notes line in Spanish")
        self.assertEqual({m for t in texts for m in re.findall(r"\{ui:([a-z_]+)\}", t)}, set(UI_KEYS), "every control's name")
        self.assertEqual({x.get("style") for x in s if x["layout"] == "text"} - {None}, {"script", "break"})
        self.assertTrue(any(x["layout"] == "columns" and len(x["columns"]) == 4 and x.get("style") == "cards" for x in s))
        quotes = sorted(len(x["quote"]) for x in s if x["layout"] == "quote")
        self.assertTrue(len(quotes) >= 2 and quotes[0] < 200 < quotes[-1], "a short quote and a long one")
        self.assertEqual({x.get("print", "landscape") for x in flags("handout")}, {"portrait", "landscape"})
        self.assertTrue(any(x.get("kind") == "deadlines" and x["options"].get("limit_each") for x in s))
        self.assertTrue(any(x.get("kind") == "events" and x["options"].get("filter") == "assemblies" for x in s))
        self.assertTrue(any(x.get("checklist") for x in s) and any(x.get("numbered") for x in s))
        self.assertTrue(any(x["layout"] == "columns" and x.get("checklist") for x in s), "tick boxes in columns")
        self.assertTrue(any(isinstance(i, dict) and i.get("items") for x in s for i in x.get("items", []) if x["layout"] == "bullets"), "sub-items")
        agenda = next(x for x in s if x["layout"] == "agenda")
        self.assertTrue(all("from" in i for i in agenda["items"]))
        self.assertTrue(any(x["layout"] == "closing" and x.get("qr") for x in s))
        # long texts, for the player's text fitting: a long item, a long table cell, long notes
        self.assertTrue(any(len(t) > 160 for x in s if x["layout"] in ("bullets", "activity") for _, t in strings(x.get("items", x.get("steps")))))
        self.assertTrue(any(len(c) > 120 for x in s if x["layout"] == "table" for r in x["rows"] for c in r))
        self.assertTrue(any(len(x["notes"].split()) > 120 for x in s))

    def test_the_second_sample(self):
        d = self.decks["sample-meeting"]
        self.assertTrue(any(x["layout"] == "section" and x.get("facilitator") for x in d["slides"]), "a facilitator part")
        self.assertTrue(any(x.get("kind") == "meeting" and x["options"]["limit"] == 12 for x in d["slides"]), "the year's dates")
        self.assertTrue(any(x.get("lang") == "es" and not x.get("facilitator") for x in d["slides"]), "a shown slide in Spanish")
        closing = next(x for x in d["slides"] if x["layout"] == "closing")
        self.assertIn("{live:meeting_after}", closing["lines"][0], "during the meeting, the next one is the one after it")
        title = next(x for x in d["slides"] if x["layout"] == "title")
        self.assertIn("{live:meeting_month}", title["subtitle"], "the meeting's own month, never the calendar's")
        self.assertTrue(any("{live:meeting_day}" in line for line in title["lines"]),
                        "the meeting's own day: tonight's until midnight, also after the meeting has ended")
        self.assertTrue(any(x.get("lang") == "es" and x.get("style") == "script" for x in d["slides"]), "an announcement card in Spanish")


class Json(unittest.TestCase):
    """A real build of the sample decks (PRESENTATIONS_DIR=tests/fixtures/presentations), as GitHub Pages builds the
    site (PATH_PREFIX=/aagrapevine/, I18N_STRICT=1) — only the JSON files and the sitemap (ONLY=…), twice."""

    @classmethod
    def build(cls, out: Path, decks: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "PRESENTATIONS_DIR": str(decks), "PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1",
               "ONLY": "presentations-json,sitemap", "NODE_NO_WARNINGS": "1"}
        env.pop("MONTHLY_NOW", None)
        return subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                               "--output", str(out)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                              timeout=600)

    @classmethod
    def setUpClass(cls):
        cls.tmp = None
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="presentations-build-"))
        cls.runs = [cls.build(cls.tmp / f"site{i}", FIXTURES) for i in (1, 2)]
        (cls.tmp / "no-decks").mkdir()
        cls.empty = cls.build(cls.tmp / "site-empty", cls.tmp / "no-decks")
        folder = cls.tmp / "site1" / "orientation" / "presentations"
        cls.files = sorted(folder.glob("*.json")) if folder.is_dir() else []
        cls.json = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in cls.files}
        cls.json2 = {f.stem: json.loads((cls.tmp / "site2" / "orientation" / "presentations" / f.name).read_text(encoding="utf-8"))
                     for f in cls.files}
        cls.yaml = {f.stem: yaml.safe_load(f.read_text(encoding="utf-8")) for f in FIXTURES.glob("*.yml")}

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, True)

    def setUp(self):
        node_ready(self)
        for r in self.runs:
            self.assertEqual(r.returncode, 0, r.stderr[-3000:])

    def test_one_file_per_deck_and_none_without_decks(self):
        self.assertEqual([f.name for f in self.files], ["sample-meeting.json", "sample-workshop.json"])
        self.assertEqual(self.empty.returncode, 0, self.empty.stderr[-3000:])
        self.assertFalse((self.tmp / "site-empty" / "orientation").exists(), "no decks: no files")

    def test_not_a_page_of_the_sitemap(self):
        sitemap = (self.tmp / "site1" / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("presentations", sitemap)
        src = (ROOT / "src" / "pages" / "presentations-json.11ty.js").read_text(encoding="utf-8")
        self.assertIn("eleventyExcludeFromCollections: true", src)
        self.assertIn("layout: null", src)

    def test_the_top_level(self):
        for deck_id, j in self.json.items():
            with self.subTest(deck=deck_id):
                y = self.yaml[deck_id]
                self.assertEqual(list(j), ["app", "schema", "id", "lang", "title", "short", "eyebrow", "footer", "minutes",
                                           "built", "as_of", "version", "site", "drive", "presets", "fillins", "live", "slides"])
                self.assertEqual((j["app"], j["schema"], j["id"], j["lang"]), ("gv-presentation", 1, deck_id, "en"))
                for k in ("title", "short", "eyebrow", "footer", "minutes"):
                    self.assertEqual(j[k], y[k], k)
                self.assertIn("{live:panel}", j["footer"], "tokens stay: the player fills them")
                self.assertRegex(j["built"], ISO)
                datetime.strptime(j["as_of"], "%B %d, %Y")
                self.assertRegex(j["version"], HASH)
                self.assertEqual(j["site"], {"url": BASE, "host": BASE.split("://", 1)[1].rstrip("/")})
                if j["drive"] is not None:
                    self.assertEqual(set(j["drive"]), {"view", "date"})
                    self.assertTrue(j["drive"]["view"].startswith("https://drive.google.com/"))
                    self.assertRegex(j["drive"]["date"], r"^(\d{4}-\d{2}-\d{2})?$")
                self.assertIsNone(self.json["sample-meeting"]["drive"], "no Drive file of that title")
                # the versions and the blanks, normalized
                self.assertEqual([p["id"] for p in j["presets"]], [p["id"] for p in y["presets"]])
                for p, yp in zip(j["presets"], y["presets"]):
                    self.assertEqual(list(p), ["id", "label", "minutes", "hide", "only", "note"])
                    self.assertEqual((p["label"], p["minutes"]), (yp["label"], yp["minutes"]))
                    self.assertEqual(p["hide"], yp.get("hide", []))
                    self.assertEqual(p["only"], yp.get("only"))
                    self.assertEqual(p["note"], yp.get("note"))
                for f, yf in zip(j["fillins"], y["fillins"]):
                    self.assertEqual(f, {"key": yf["key"], "label": yf["label"], "hint": yf["hint"], "default": yf.get("default", ""),
                                         "shared": yf.get("shared", False), "notes_only": yf.get("notes_only", False)})

    def test_the_slides(self):
        common = ["id", "layout", "h", "n_default", "part", "accent", "eyebrow", "title"]
        tail = ["notes", "minutes", "version_minutes", "optional", "starts_off", "facilitator", "handout", "print",
                "version_notes", "version_fields", "show_from", "show_until", "when", "lang", "data"]
        for deck_id, j in self.json.items():
            y = self.yaml[deck_id]
            today = datetime.strptime(j["as_of"], "%B %d, %Y").strftime("%Y-%m-%d")
            self.assertEqual([s["id"] for s in j["slides"]], [s["id"] for s in y["slides"]])
            n = 0
            part = None
            accent = "gv"
            for s, ys in zip(j["slides"], y["slides"]):
                with self.subTest(deck=deck_id, slide=s["id"]):
                    extra = [k for k in ys if k not in common and k not in tail and k != "allow_words"]
                    self.assertEqual(list(s), common + extra + tail, "the fields in the SPEC's order")
                    # its YAML exactly as written: tokens kept
                    for k in extra + ["title", "notes"]:
                        self.assertEqual(s[k], ys[k], k)
                    self.assertRegex(s["h"], HASH)
                    self.assertEqual(s["layout"], ys["layout"])
                    self.assertIsInstance(s["eyebrow"], str)
                    if ys["layout"] == "section":
                        part = {"n": ys["number"], "title": ys["title"]}
                        accent = ys.get("accent", "gv")
                    self.assertEqual(s["part"], part)
                    # a section's accent carries to the slides after it; another slide's own accent is its alone
                    self.assertEqual(s["accent"], ys.get("accent") or accent)
                    self.assertIn(s["accent"], ACCENTS)
                    # its own eyebrow, else its part's ("Part 3 · …") or the deck's before the first part — but a Q&A or
                    # credits slide has none of its own unless it names one, as the decks drew them (cosmetic-eyebrows)
                    if ys["layout"] in ("qa", "credits"):
                        self.assertEqual(s["eyebrow"], ys.get("eyebrow") or "")
                    else:
                        self.assertTrue(s["eyebrow"])
                        self.assertEqual(s["eyebrow"], ys.get("eyebrow") or (f"Part {part['n']} · {part['title']}" if part else y["eyebrow"]))
                    self.assertEqual(s["minutes"], ys.get("minutes"))
                    self.assertEqual(s["version_minutes"], ys.get("version_minutes", {}))
                    for k in ("optional", "starts_off", "facilitator", "handout"):
                        self.assertIs(s[k], ys.get(k, False), k)
                    self.assertEqual(s["version_notes"], ys.get("version_notes", {}))
                    # a version's own text, as written (tokens kept); a handout page's orientation
                    self.assertEqual(s["version_fields"], ys.get("version_fields", {}))
                    self.assertEqual(s["print"], ys.get("print", "landscape") if ys.get("handout") else None)
                    self.assertEqual(s["when"], ys.get("when"))
                    self.assertEqual(s["lang"], ys.get("lang", "en"))
                    for k in ("show_from", "show_until"):
                        if ys.get(k):
                            self.assertRegex(s[k], ISO)
                        else:
                            self.assertIsNone(s[k])
                    # the default version, today: numbered 1, 2, 3 …; facilitator, starts_off and out-of-window
                    # slides have no number
                    shown = not ys.get("facilitator") and not ys.get("starts_off") \
                        and (not ys.get("show_from") or ys["show_from"] <= today) \
                        and (not ys.get("show_until") or today <= ys["show_until"]) \
                        and (ys.get("when") != "price_notice" or self.notice_on(today))
                    if shown:
                        n += 1
                    self.assertEqual(s["n_default"], n if shown else None)
                    if ys["layout"] == "live" or (ys["layout"] == "closing" and ys.get("qr")):
                        self.assertIsInstance(s["data"], dict)
                    else:
                        self.assertIsNone(s["data"])

    @staticmethod
    def notice_on(today: str) -> bool:
        """shop.js shopPriceChangeIn for one day: from `announced` to the day before `effective`, then through
        `notice_until` (data/site/shop.json price_changes)."""
        shop = json.loads((ROOT / "data" / "site" / "shop.json").read_text(encoding="utf-8"))
        for c in shop.get("price_changes") or []:
            until = c.get("notice_until") or c["effective"]
            if c["announced"] <= today < c["effective"] or c["effective"] <= today <= until:
                return True
        return False

    def test_show_window_instants(self):
        s = {x["id"]: x for x in self.json["sample-workshop"]["slides"]}
        # Central time: the start of the first day, the last moment of the last day
        self.assertEqual(s["holiday-gifts"]["show_from"], "2026-11-15T06:00:00.000Z")
        self.assertEqual(s["holiday-gifts"]["show_until"], "2027-01-01T05:59:59.999Z")
        self.assertEqual(s["new-panel"]["show_from"], "2026-09-01T05:00:00.000Z")
        self.assertEqual(s["new-panel"]["show_until"], "2027-07-01T04:59:59.999Z")

    def test_stable_hashes(self):
        for deck_id, j in self.json.items():
            with self.subTest(deck=deck_id):
                j2 = self.json2[deck_id]
                self.assertEqual(j["version"], j2["version"])
                self.assertEqual([s["h"] for s in j["slides"]], [s["h"] for s in j2["slides"]])
                self.assertEqual(len({s["h"] for s in j["slides"]}), len(j["slides"]), "each slide its own hash")
        self.assertNotEqual(self.json["sample-workshop"]["version"], self.json["sample-meeting"]["version"])
        # a slide's hash is its content's: the same slide in another deck has the same one
        r = run_js(self, """
            const P = await imp("eleventy/filters/presentations.js");
            const a = { id: "x", layout: "text", title: "T", body: "B", notes: "N", minutes: 1 };
            const b = { minutes: 1, notes: "N", body: "B", title: "T", layout: "text", id: "x" };
            out([P.slideHash(a), P.slideHash(b), P.slideHash({ ...a, body: "C" })]);
        """)
        self.assertEqual(r[0], r[1], "the order of the fields does not count")
        self.assertNotEqual(r[0], r[2])

    def test_a_value_for_every_live_key(self):
        for deck_id, j in self.json.items():
            with self.subTest(deck=deck_id):
                self.assertEqual(set(j["live"]), LIVE_KEYS)
                used = {m.group(2) for s in self.yaml[deck_id]["slides"] for _, t in strings(s) for m in TOKEN.finditer(t) if m.group(1) == "live"}
                self.assertLessEqual(used, set(j["live"]))
                for k, v in j["live"].items():
                    if isinstance(v, str):
                        continue
                    # { value, steps?, until?, fallback? } — never a lone value (that is written as a text)
                    self.assertIsInstance(v, dict, k)
                    self.assertLessEqual(set(v), {"value", "steps", "until", "fallback"}, k)
                    self.assertGreater(len(v), 1, k)
                    self.assertIsInstance(v["value"], str)
                    froms = []
                    for st in v.get("steps", []):
                        self.assertEqual(set(st), {"from", "value"}, k)
                        self.assertRegex(st["from"], ISO)
                        self.assertIsInstance(st["value"], str)
                        froms.append(st["from"])
                    self.assertEqual(froms, sorted(set(froms)), f"{k}: the steps in order")
                    if "until" in v:
                        self.assertRegex(v["until"], ISO)
                        self.assertTrue(not froms or v["until"] > froms[-1], k)
                    if "fallback" in v:
                        self.assertTrue(v["fallback"].strip(), k)
                    else:
                        self.assertTrue(v["value"] and all(st["value"] for st in v.get("steps", [])), f"{k}: empty, with nothing to say")
        live = self.json["sample-workshop"]["live"]
        value = lambda k: live[k] if isinstance(live[k], str) else live[k]["value"]  # noqa: E731
        self.assertEqual(live["site"], BASE.split("://", 1)[1].rstrip("/"))
        self.assertEqual(live["site_url"], BASE)
        self.assertEqual(live["email"], SITE["site"]["contact_email"])
        # a Zoom ID never breaks in the middle (no-break spaces)
        self.assertEqual(plain(live["meeting_zoom_id"]), SITE["meeting"]["meeting_id"])
        self.assertNotIn(" ", live["meeting_zoom_id"])
        self.assertEqual(live["meeting_passcode"], SITE["meeting"]["passcode"])
        self.assertTrue(plain(live["meeting_time"]).endswith(" Central time"))
        self.assertNotIn("\u2009", live["meeting_time"], "the time range is never cut at its dash")
        # no break on either side of the dash (a word joiner after it), nor before PM
        self.assertRegex(live["meeting_time"], "^\\d{1,2}:\\d{2}\u202f\u2013" + WJ + "\u202f\\d{1,2}:\\d{2}\u202f[AP]M Central time$")
        self.assertRegex(live["meeting_rule"], r"^every (first|second|third|fourth|fifth|last) \w+day of the month$")
        # the month's facts switch at midnight Central on the 1st: the month and the year for a year ahead
        today = datetime.strptime(live["as_of"], "%B %d, %Y")
        self.assertEqual(live["month"]["value"], today.strftime("%B %Y"))
        nxt = datetime(today.year + today.month // 12, today.month % 12 + 1, 1)
        self.assertEqual(live["month"]["steps"][0]["value"], nxt.strftime("%B %Y"))
        self.assertRegex(live["month"]["steps"][0]["from"], rf"^{nxt:%Y-%m-%d}T0[56]:00:00\.000Z$")
        self.assertEqual(len(live["month"]["steps"]), 11)
        self.assertEqual(value("year"), str(today.year))
        firsts = {st["from"] for st in live["month"]["steps"]}
        for k in ("gv_issue", "gv_next_issue", "gv_theme", "lv_issue", "lv_next_issue", "lv_theme"):
            if isinstance(live[k], dict):
                self.assertLessEqual({st["from"] for st in live[k].get("steps", [])}, firsts, f"{k}: on the 1st")
                if "until" in live[k]:
                    self.assertRegex(live[k]["until"], r"-01T0[56]:00:00\.000Z$", k)
        # the next meeting: each until it ends (its row's `end`, the meeting slide's data); the meeting's day until
        # midnight Central after it, and the one after it and the meeting's month moving on at the same moments
        nxt_m, day, after, month = live["meeting_next"], live["meeting_day"], live["meeting_after"], live["meeting_month"]
        rows = next(s for s in self.json["sample-workshop"]["slides"] if s.get("kind") == "meeting")["data"]["rows"]
        ahead = [r for r in rows if r["end"] > self.json["sample-workshop"]["built"]]
        self.assertRegex(nxt_m["value"], r"^\w+day, \w+ \d{1,2}, \d{4}$")
        self.assertEqual(nxt_m["value"], ahead[0]["label"])
        self.assertEqual(nxt_m["steps"], [{"from": a["end"], "value": b["label"]} for a, b in zip(ahead[:3], ahead[1:4])],
                         "the next four meetings, each until it ends")
        self.assertEqual(nxt_m["until"], ahead[3]["end"])
        self.assertEqual(day["value"], rows[0]["label"])
        self.assertEqual(len(day["steps"]), 3, "the next four meetings")
        for st in day["steps"]:
            self.assertRegex(st["from"], r"T0[56]:00:00\.000Z$", "midnight Central")
        self.assertEqual([st["from"] for st in after["steps"]], [st["from"] for st in day["steps"]])
        self.assertEqual(after["value"], day["steps"][0]["value"])
        self.assertEqual(after["until"], day["until"])
        self.assertEqual(month["value"], datetime.strptime(day["value"], "%A, %B %d, %Y").strftime("%B %Y"))
        self.assertEqual([st["from"] for st in month["steps"]], [st["from"] for st in day["steps"]])
        self.assertEqual((nxt_m["fallback"], day["fallback"], after["fallback"], month["fallback"]),
                         ("see the Meetings page", "see the Meetings page", "see the Meetings page", "Monthly"))
        first = SITE["phone_access"]["numbers"][0]
        self.assertEqual(live["meeting_phone"], f"{first['number']} ({first['city']})")
        configured = str(SITE["phone_access"].get("committee", {}).get("phone_passcode") or "")
        passcode = str(SITE["meeting"]["passcode"])
        self.assertEqual(live["meeting_phone_passcode"], configured if configured.isdigit() else passcode if passcode.isdigit() else "")
        audio = json.loads((ROOT / "data" / "site" / "audio_project.json").read_text(encoding="utf-8"))
        self.assertEqual(value("gv_audio_phone"), (audio.get("gv") or {}).get("phone", ""))
        self.assertEqual(value("lv_audio_phone"), (audio.get("lv") or {}).get("phone", ""))
        for key, pub in (("botm", "gv"), ("botm_lv", "lv")):
            on = [b for b in json.loads((ROOT / "data" / "site" / "shop.json").read_text(encoding="utf-8")).get("botm") or []
                  if b.get("pub") == pub and b.get("ends", "9999") >= today.strftime("%Y-%m-%d")]
            self.assertEqual(value(key), on[0]["title"] if on else "", key)
            self.assertIn("fallback", live[key], "a book on offer until a day; none: where to look")
        # the weekly open meetings of /meetings/ (data/site/weekly_open.json): the day, the time in Central and
        # Eastern, La Viña's first meeting; their Zoom room
        wo = json.loads((ROOT / "data" / "site" / "weekly_open.json").read_text(encoding="utf-8"))["items"]
        gv = next(w for w in wo if w["id"] == "weekly_open")["extra"]
        self.assertRegex(plain(value("gv_open_meeting")), r"^Wednesdays, \d{1,2}:\d{2} [AP]M Central \(\w+.* Eastern\)$")
        self.assertIn(f"Zoom {gv['zoom_id']}, passcode {gv['passcode']}", plain(value("open_meeting_zoom")))
        self.assertRegex(plain(value("lv_open_meeting")), r"^Thursdays, .*Central .*, (starting|since) \w+\.? \d{1,2}, \d{4}$")
        self.assertRegex(plain(value("assembly_next")) or "see", r"^(NETA 65 \w+ Assembly \d{4} · \w{3}, \w{3} \d{1,2} – \w{3}, \w{3} \d{1,2}, \d{4}|see)")

    def test_each_kind_of_live_data(self):
        data = {s["kind"]: s["data"] for s in self.json["sample-workshop"]["slides"] if s["layout"] == "live" and s["id"] != "assemblies"}
        self.assertEqual(set(data), set(LIVE_KINDS))
        on_site = lambda u: self.assertTrue(u.startswith(BASE), u)  # noqa: E731
        absolute = lambda u: self.assertRegex(u, r"^https://")  # noqa: E731

        # every row known within about a year (whole issues), with the slide's limits: the player applies them
        d = data["deadlines"]
        self.assertEqual(list(d), ["rows", "limit", "limit_each", "url"])
        self.assertEqual((d["limit"], d["limit_each"]), (6, 3))
        on_site(d["url"])
        for r in d["rows"]:
            self.assertEqual(list(r), ["pub", "due", "due_label", "issue", "issue_key", "theme", "theme_lang", "gloss", "gloss_machine"])
            self.assertIsInstance(r["gloss_machine"], bool)
            self.assertTrue(r["gloss"] or not r["gloss_machine"], "a machine's words are a gloss")
            self.assertIn(r["pub"], ("gv", "lv"))
            self.assertRegex(r["due"], ISO)
            self.assertTrue(r["due"].endswith(":59:59.999Z"), "the last moment of the deadline day")
            datetime.strptime(r["due_label"], "%B %d, %Y")
            self.assertIn(r["theme_lang"], ("en", "es"))
            self.assertRegex(r["issue_key"], r"^(\d{4}-\d{2})?$")
            if r["pub"] == "lv" and r["issue_key"]:
                self.assertRegex(r["issue"], r"^[A-Z][a-z]+–[A-Z][a-z]+ \d{4}$", "La Viña's issues in one style")
        self.assertLessEqual(len(d["rows"]), 30)
        self.assertEqual([r["due"] for r in d["rows"]], sorted(r["due"] for r in d["rows"]))

        d = data["events"]
        self.assertEqual(list(d), ["rows", "limit", "url"])
        self.assertEqual(d["limit"], 5)
        on_site(d["url"])
        self.assertLessEqual(len(d["rows"]), 24)
        series = {}
        for r in d["rows"]:
            self.assertEqual(list(r), ["start", "end", "all_day", "date_label", "time_label", "title", "place", "online", "platform", "kind", "url",
                                     "series", "tentative"])
            self.assertIsInstance(r["series"], str)
            if r["series"]:
                series.setdefault(r["series"], set()).add(r["title"])
            self.assertRegex(r["start"], ISO)
            self.assertRegex(r["end"], ISO)
            self.assertLess(r["start"], r["end"])
            self.assertIsInstance(r["all_day"], bool)
            self.assertIsInstance(r["online"], bool)
            self.assertIn(r["kind"], ("committee", "gv", "lv", "booth", "assembly", "other"))
            self.assertNotEqual(r["kind"], "committee", "no committee meetings")
            absolute(r["url"])
            self.assertRegex(r["title"], r"(?i)workshop|taller", "filter: workshops")
        # a series' id names one series: its dates (the player keeps the next one) all have its title
        self.assertTrue(all(len(t) == 1 for t in series.values()), series)

        d = data["prices"]
        self.assertEqual(set(d), {"rows", "change", "url"})
        on_site(d["url"])
        for r in d["rows"]:
            self.assertEqual(list(r), ["pub", "plan", "price", "then"])
            self.assertIn(r["pub"], ("gv", "lv"))
            self.assertIn(r["plan"], ("print", "digital"))
            self.assertRegex(r["price"], r"^\$\d+\.\d{2}$")
            self.assertTrue(r["then"] is None or re.match(r"^\$\d+\.\d{2}$", r["then"]))
        if d["change"] is not None:
            self.assertEqual(list(d["change"]), ["at", "label", "notice_from", "notice_until", "books_more"])
            for k in ("at", "notice_from", "notice_until"):
                self.assertRegex(d["change"][k], ISO)

        for d in [s["data"] for j in self.json.values() for s in j["slides"] if s.get("kind") == "meeting"]:
            self.assertEqual(list(d), ["rows", "limit", "rule", "time", "zoom_id", "passcode", "url", "page"])
            self.assertGreaterEqual(len(d["rows"]), 12, "the rule gives a year of dates")
            for r in d["rows"]:
                self.assertEqual(list(r), ["start", "end", "label"])
                self.assertRegex(r["start"], ISO)
                self.assertRegex(r["end"], ISO)
                self.assertLess(r["start"], r["end"])
                self.assertRegex(r["label"], r"^\w+day, \w+ \d{1,2}, \d{4}$")
            self.assertRegex(d["rule"], r"^Every ")
            self.assertTrue(d["url"].startswith("https://") and "zoom.us" in d["url"])
            on_site(d["page"])
        limits = sorted(s["data"]["limit"] for j in self.json.values() for s in j["slides"] if s.get("kind") == "meeting")
        self.assertEqual(limits, [3, 12], "limit 3, and 12 = the year")

        d = data["lv-workshop"]
        self.assertEqual(list(d), ["rows", "limit", "time", "zoom_id", "url", "contact", "page"])
        self.assertEqual(d["limit"], 3)
        for r in d["rows"]:
            self.assertEqual(list(r), ["start", "end", "label"])
        if d["rows"]:
            self.assertRegex(plain(d["time"]), r"Central time \(\d{1,2}:\d{2} [AP]M Eastern\)$")
            absolute(d["page"])

        d = data["issues"]
        self.assertEqual(list(d), ["month", "gv", "lv", "url"])
        on_site(d["url"])
        for pub in ("gv", "lv"):
            if d[pub] is not None:
                self.assertEqual(list(d[pub]), ["label", "theme", "theme_lang", "gloss", "gloss_machine"])
                self.assertIsInstance(d[pub]["gloss_machine"], bool)

        d = data["monthly"]
        self.assertEqual(list(d), ["month", "url", "tips", "limit"])
        on_site(d["url"])
        self.assertRegex(d["url"], r"/monthly/\d{4}-\d{2}/$")
        self.assertLessEqual(len(d["tips"]), 3)
        for tip in d["tips"]:
            self.assertEqual(list(tip), ["title", "text"])

        d = data["botm"]
        self.assertEqual(list(d), ["title", "mag", "lang", "note", "url", "until", "also"])
        on_site(d["url"])
        if d["also"] is not None:
            self.assertEqual(list(d["also"]), ["title", "mag", "lang", "note", "url", "until"])

        d = data["bulletin"]
        self.assertEqual(list(d), ["rows", "limit", "url"])
        self.assertLessEqual(len(d["rows"]), d["limit"])
        on_site(d["url"])
        for r in d["rows"]:
            self.assertEqual(list(r), ["title", "date_label", "url"])
            self.assertTrue(r["url"].startswith(BASE + "bulletin/#"))

        d = data["qr"]
        self.assertEqual(list(d), ["url", "label", "svg"])
        self.assertEqual(d["url"], BASE + "contribute/")
        self.assertEqual(d["label"], "Share your story on the committee website")
        self.assertTrue(d["svg"].startswith("<svg ") and 'role="img"' in d["svg"])
        # NETA 65's assemblies only
        asm = next(s for s in self.json["sample-workshop"]["slides"] if s["id"] == "assemblies")["data"]
        self.assertEqual(asm["limit"], 3)
        self.assertTrue(all(r["kind"] == "assembly" for r in asm["rows"]))
        closing = next(s for s in self.json["sample-workshop"]["slides"] if s["id"] == "closing")
        self.assertEqual(closing["qr"], "/", "the YAML value stays")
        self.assertEqual(closing["data"]["url"], BASE)
        self.assertTrue(closing["data"]["svg"].startswith("<svg "))

    def test_the_global_agrees_with_the_files(self):
        r = run_js(self, """
            const data = await imp("src/_data/presentations.js");
            out(data.default());
        """, env={"PRESENTATIONS_DIR": "tests/fixtures/presentations"})
        self.assertEqual(r["problems"], [])
        self.assertEqual([d["id"] for d in r["decks"]], ["sample-workshop", "sample-meeting"], "by order")
        for d in r["decks"]:
            with self.subTest(deck=d["id"]):
                j = self.json[d["id"]]
                y = self.yaml[d["id"]]
                for k in ("id", "order", "title", "short", "card", "minutes", "icon", "tone", "drive_title", "count", "parts",
                          "kinds", "presets", "fillins", "url"):
                    self.assertIn(k, d)
                self.assertEqual(d["url"], f"/orientation/presentations/{d['id']}.json")
                self.assertEqual(d["card"], y["card"])
                self.assertEqual(d["count"], max(s["n_default"] or 0 for s in j["slides"]))
                self.assertEqual(d["version"], j["version"])
                self.assertEqual(d["parts"], [{"n": s["number"], "title": s["title"], "id": s["id"]} for s in y["slides"]
                                              if s["layout"] == "section" and not s.get("facilitator")])
        main = next(d for d in r["decks"] if d["id"] == "sample-workshop")
        self.assertEqual(main["kinds"], ["meeting", "lv-workshop", "events", "deadlines", "issues", "monthly", "prices", "botm", "bulletin"],
                         "what stays current: the live kinds and the facts used, never a QR code")
        meeting = next(d for d in r["decks"] if d["id"] == "sample-meeting")
        self.assertEqual(meeting["kinds"], ["meeting", "events", "issues"])
        self.assertEqual(meeting["parts"], [{"n": 1, "title": "Dates and events", "id": "reports"}], "no facilitator part")


# ----------------------------------------------------------------------------------------------------------------
# Facts from made-up data at a fixed clock (2099: the editorial calendar is read against today's date as well)
# ----------------------------------------------------------------------------------------------------------------
SITE_X = {
    "url": "https://neta65.github.io/aagrapevine", "contact_email": "grapevine@neta65.org",
    "committee": "NETA 65 Grapevine & La Viña Committee",
    "meeting": {"week_of_month": 3, "weekday": "wednesday", "start": "19:00", "end": "20:00", "platform": "Zoom",
                "zoom_url": "https://us02web.zoom.us/j/9494767497", "meeting_id": "949 476 7497", "passcode": "neta65"},
    # the passcode has letters and no phone passcode is set yet: a caller's passcode is unknown ("")
    "phone_access": {"numbers": [{"number": "+1 346 248 7799", "city": "Houston"}, {"number": "+1 312 626 6799", "city": "Chicago"}],
                     "committee": {"phone_passcode": ""}},
}
PLAN = lambda typ, price, new=None: {  # noqa: E731
    "type": typ, "term_months": 12, "price": price, "url": "https://www.aagrapevine.org/store/x", "currency": "USD",
    **({"change": {"key": "2100-01", "new": new, "stale": True}} if new else {})}
SHOP_X = {
    "subscriptions": [
        {"pub": "gv", "region": "us", "plans": [PLAN("print", 36, 39), PLAN("digital", 29.99, 34), {**PLAN("digital", 2.99), "term_months": 1}]},
        {"pub": "lv", "region": "us", "plans": [PLAN("print", 18, 19.5), PLAN("digital", 14.99, 17)]},
    ],
    "price_changes": [{
        "key": "2100-01", "announced": "2099-10-01", "effective": "2100-01-01", "notice_until": "2100-01-31",
        "at": {"announced": "2099-10-01T05:00:00Z", "effective": "2100-01-01T06:00:00Z", "notice_end": "2100-02-01T06:00:00Z"},
        "yearly": [{"pub": "gv", "type": "print", "new": 39, "now": 36, "after": 39}, {"pub": "gv", "type": "digital", "new": 34, "now": 29.99, "after": 34},
                   {"pub": "lv", "type": "print", "new": 19.5, "now": 18, "after": 19.5}, {"pub": "lv", "type": "digital", "new": 17, "now": 14.99, "after": 17}],
        "books_more": 2,
    }],
    "botm": [
        {"id": "botm:gv", "pub": "gv", "lang": "en", "title": "No Matter What", "url": "https://www.aagrapevine.org/store/a",
         "price": 14.99, "sale_price": 11.99, "discount_pct": 20, "starts": "2099-09-15", "ends": "2099-10-20", "read": "2099-10-02"},
        {"id": "botm:lv", "pub": "lv", "lang": "es", "title": "Frente a Frente", "url": "https://www.aalavina.org/tienda/b",
         "price": 14.99, "sale_price": 11.99, "starts": "2099-08-15", "ends": "2099-10-20", "read": "2099-10-02"},
    ],
}


def ev(id_: str, title: str, start: str, end: str | None = None, **extra) -> dict:
    cat = extra.pop("category", "manual")
    return {"id": id_, "kind": "event", "source": extra.pop("source", "committee"), "category": cat, "lang": "en",
            "title": title, "url": extra.pop("url", "/events/"), "date": start, "status": "ok",
            "extra": {"start": start, **({"end": end} if end else {}), **extra}}


LV_RULE = {"week_of_month": 4, "weekday": "thursday", "start": "14:00", "end": "15:00"}
BOOTH_RULE = {"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "20:00"}
DB_X = {
    "shop": SHOP_X,
    "events": {"items": [
        ev("ev:manual:old", "Grapevine Writing Workshop — Past", "2099-10-01T19:00:00Z", "2099-10-01T21:00:00Z"),
        ev("ev:manual:2099-10-20-gv-writing-workshop-tyler", "Grapevine Writing Workshop — Tyler", "2099-10-20T23:00:00Z",
           "2099-10-21T01:00:00Z", location="Tyler, TX", slug="2099-10-20-gv-writing-workshop-tyler", url="/events/#2099-10-20-gv-writing-workshop-tyler"),
        ev("ev:recurring:lv-monthly-workshop:2099-10-22", "La Viña Monthly Virtual Workshop (in Spanish)", "2099-10-22T19:00:00Z",
           "2099-10-22T20:00:00Z", category="recurring", recurring=True, series="lv-monthly-workshop", rule=LV_RULE, host="lv",
           online=True, platform="Zoom", online_url="https://us06web.zoom.us/j/81595931777", meeting_id="815 9593 1777",
           contact="lveditorial@aagrapevine.org"),
        ev("ev:recurring:lv-monthly-workshop:2099-11-19", "La Viña Monthly Virtual Workshop (in Spanish)", "2099-11-19T20:00:00Z",
           "2099-11-19T21:00:00Z", category="recurring", recurring=True, series="lv-monthly-workshop", rule=LV_RULE, host="lv",
           online=True, platform="Zoom", online_url="https://us06web.zoom.us/j/81595931777", meeting_id="815 9593 1777",
           contact="lveditorial@aagrapevine.org"),
        ev("ev:manual:2099-11-06-fall-assembly", "NETA 65 Fall Assembly 2099", "2099-11-06", "2099-11-08", location="Tyler, TX"),
        ev("ev:gv:day", "Grapevine Day", "2099-11-01", source="calendar", category="gv-calendar", url="https://www.aagrapevine.org/events/day"),
        ev("ev:recurring:citywide-dallas:2099-11-14", "GV/LV booth at CityWide Dallas", "2099-11-14T23:00:00Z", "2099-11-15T02:00:00Z",
           category="recurring", recurring=True, series="citywide-dallas", rule=BOOTH_RULE, location="Dallas, TX"),
        ev("ev:recurring:citywide-dallas:2099-12-12", "GV/LV booth at CityWide Dallas", "2099-12-12T23:00:00Z", "2099-12-13T02:00:00Z",
           category="recurring", recurring=True, series="citywide-dallas", rule=BOOTH_RULE, location="Dallas, TX"),
        # the assembly after the next one (its details to be confirmed), and another Area's assembly on an outside
        # calendar — never one of NETA 65's
        ev("ev:manual:2100-03-19-spring-assembly", "NETA 65 Spring Assembly 2100", "2100-03-19", "2100-03-21", location="Dallas, TX", tentative=True),
        ev("ev:gv:other-assembly", "Area 68 Assembly", "2099-12-04", source="calendar", category="gv-calendar", url="https://www.aagrapevine.org/events/a68"),
    ]},
    "editorial": {"items": [
        # the next issues before they are out: Grapevine's November and December (its deadline long past), La Viña's
        # November / December (a dated theme of its own calendar: "en" in `machine` — its summary's, say — but its
        # English words are the hand-written ones of data/translations/overrides.yml, never a machine's)
        {"id": "ed:gv:2099-11", "lang": "en", "title": "Classic Grapevine", "extra": {"publication": "gv", "issue_key": "2099-11"}},
        {"id": "ed:gv:2099-12", "lang": "en", "title": "Sober Holidays!", "extra": {"publication": "gv", "issue_key": "2099-12", "deadline": "2099-05-01"}},
        {"id": "ed:lv:2099-11", "lang": "es", "title": "La alegría de vivir", "machine": ["en"],
         "i18n": {"title": {"en": "The Joy of Living", "es": "La alegría de vivir"},
                  "issue_label": {"en": "November / December 2099", "es": "Noviembre / Diciembre 2099"}},
         "extra": {"publication": "lv", "issue_key": "2099-11", "issue_label": "Noviembre 2099", "deadline": "2099-06-01"}},
        {"id": "ed:gv:past", "lang": "en", "title": "Too Late", "extra": {"publication": "gv", "issue_key": "2100-05", "deadline": "2099-10-01"}},
        {"id": "ed:gv:2100-07", "lang": "en", "title": "Annual Prison Issue", "extra": {"publication": "gv", "issue_key": "2100-07", "deadline": "2099-12-01"}},
        # a machine-translated English gloss (no hand-written English for it)
        {"id": "ed:lv:2100-05", "lang": "es", "title": "Servicio en AA", "machine": ["en"], "i18n": {"title": {"en": "AA Service", "es": "Servicio en AA"}},
         "extra": {"publication": "lv", "issue_key": "2100-05", "issue_label": "Mayo / Junio 2100", "deadline": "2100-02-15"}},
        {"id": "ed:gv:2101-02:a", "lang": "en", "title": "Sober Holidays!", "extra": {"publication": "gv", "issue_key": "2101-02", "deadline": "2100-07-01"}},
        {"id": "ed:gv:2101-02:b", "lang": "en", "title": "Remote Communities", "extra": {"publication": "gv", "issue_key": "2101-02", "deadline": "2100-07-01"}},
        {"id": "ed:lv:any", "lang": "es", "title": "Mi Primer Paso", "extra": {"publication": "lv", "evergreen": True}},
    ]},
    "articles": {"issues": [
        {"id": "gv:2099-10", "publication": "gv", "key": "2099-10", "label": "October 2099", "theme": "Loneliness", "lang": "en"},
        # La Viña's issue of these months: its theme's English is a machine's
        {"id": "lv:2099-09", "publication": "lv", "key": "2099-09", "label": "Septiembre / Octubre 2099", "theme": "Servicio en AA", "lang": "es",
         "machine": ["en"],
         "i18n": {"theme": {"en": "AA Service", "es": "Servicio en AA"}, "label": {"en": "September / October 2099", "es": "Septiembre / Octubre 2099"}}},
    ], "items": []},
    "announcements": {"items": [
        {"id": "ann:pinned", "kind": "announcement", "lang": "en", "title": "Pinned and older", "date": "2099-10-01",
         "extra": {"slug": "2099-10-01-pinned", "pinned": True}},
        {"id": "ann:new", "kind": "announcement", "lang": "en", "title": "The newest post", "date": "2099-10-10",
         "extra": {"slug": "2099-10-10-new"}},
        {"id": "ann:over", "kind": "announcement", "lang": "en", "title": "Over", "date": "2099-09-01",
         "extra": {"slug": "2099-09-01-over", "expires": "2099-10-01"}},
    ]},
    "drive": {"items": [
        {"id": "drive:old", "source": "drive", "kind": "slides", "category": "slides", "title": "Sample Deck", "date": "2099-01-01",
         "url": "https://drive.google.com/file/d/old/view"},
        {"id": "drive:new", "source": "drive", "kind": "slides", "category": "slides", "title": "Sample Deck", "date": "2099-10-01",
         "url": "https://drive.google.com/file/d/new/view", "extra": {"view_url": "https://drive.google.com/file/d/new/view"}},
    ]},
    "status": {"sources": [{"source": "drive", "stats": {"panel_folders": [{"panel": 77, "label": "Panel 77 (2027–2028)", "id": "x"}]}}]},
    "audio_project": {"gv": {"phone": "(559) 726-1216", "tel": "+15597261216"}, "lv": {"phone": "(559) 670-1601", "tel": "+15596701601"}},
    # the weekly open meetings (/meetings/#weekly-open): Grapevine's on Wednesdays, La Viña's on Thursdays from its
    # first meeting on (a Thursday, November 5), in the same Zoom room
    "weekly_open": {"items": [
        {"id": "weekly_open", "source": "grapevine", "kind": "meeting", "title": "Grapevine Weekly Open AA Meeting", "lang": "en", "status": "ok",
         "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "day": "Wednesdays", "time": "Noon Eastern", "weekday": "wednesday",
                   "start_local": "12:00", "timezone": "America/New_York", "time_central": "11 AM Central", "next_start": "2099-10-21T16:00:00Z"},
         "i18n": {"day": {"en": "Wednesdays"}, "time": {"en": "Noon Eastern"}, "time_central": {"en": "11:00 AM Central"},
                  "when": {"en": "Wednesdays at 11:00 AM Central"}}},
        {"id": "weekly_open_lv", "source": "lavina", "kind": "meeting", "title": "Reunión Abierta de La Viña", "lang": "es", "status": "ok",
         "extra": {"zoom_id": "871 2036 8287", "passcode": "238047", "day": "Jueves", "weekday": "thursday", "start_local": "12:00",
                   "timezone": "America/New_York", "time_central": "11 AM Central", "next_start": "2099-11-05T17:00:00Z", "starts": "2099-11-05"},
         "i18n": {"day": {"en": "Thursdays", "es": "Jueves"}, "time": {"en": "Noon Eastern"}, "time_central": {"en": "11:00 AM Central"},
                  "when": {"en": "Thursdays at 11:00 AM Central"}}},
    ]},
}
CARRY_X = {"wayById": {"newcomer": {"id": "newcomer", "title": {"en": "Give it to a newcomer", "es": "Dáselo a un recién llegado"}}},
           "tips": {"2099-10": [{"way": "newcomer", "text": {"en": "Newcomers feel isolated: this issue speaks to that.", "es": "x"}}]}}
MEETING_X = {"upcoming": [
    {"ymd": "2099-10-14", "start": "2099-10-15T00:00:00Z", "end": "2099-10-15T01:00:00Z"},   # over at the clock below
    {"ymd": "2099-10-21", "start": "2099-10-22T00:00:00Z", "end": "2099-10-22T01:00:00Z"},
    {"ymd": "2099-11-18", "start": "2099-11-19T01:00:00Z", "end": "2099-11-19T02:00:00Z"},
    {"ymd": "2099-12-16", "start": "2099-12-17T01:00:00Z", "end": "2099-12-17T02:00:00Z"},
]}
FACTS_JS = r"""
const P = await imp("eleventy/filters/presentations.js");
const C = await imp("eleventy/filters/committee.js");
const res = {};
for (const [name, now] of Object.entries(input.clocks)) {
  const ctx = { db: input.db, site: input.site, carry: input.carry, meeting: input.meeting, now: new Date(now) };
  const kinds = {};
  for (const [kind, opts] of input.kinds) kinds[kind + (opts.filter ? ":" + opts.filter : "") + (opts.pub ? ":" + opts.pub : "") + (opts.limit_each ? ":each" : "")] = P.liveData(kind, opts, ctx);
  res[name] = { live: P.liveFacts(ctx), kinds };
}
const deck = { id: "x", lang: "en", title: "T", short: "S", eyebrow: "E", footer: "F", minutes: 30, version: "v", presets: [],
  fillins: [], drive_title: "Sample Deck", slides: [{ id: "q", layout: "closing", qr: "/meetings/" }, { id: "w", layout: "text", body: "b" }] };
res.deck = P.deckJson(deck, { db: input.db, site: { ...input.site, built: "2099-10-15T17:00:00Z" }, carry: input.carry, meeting: input.meeting, now: new Date("2099-10-15T17:00:00Z") });
res.deck.slides.forEach((s) => { if (s.data && s.data.svg) s.data.svg = s.data.svg.slice(0, 5); });
res.empty = { live: P.liveFacts({ db: {}, site: { url: input.site.url }, now: new Date("2099-10-15T17:00:00Z") }), kinds: {} };
for (const [kind, opts] of input.kinds) res.empty.kinds[kind] = P.liveData(kind, opts, { db: {}, site: { url: input.site.url }, now: new Date("2099-10-15T17:00:00Z") });
res.empty.kinds.qr.svg = res.empty.kinds.qr.svg.slice(0, 5);
// one fact changed at a time (October): only La Viña's book on offer; a caller's passcode set, or numbers only; no numbers;
// the weekly open meetings in two Zoom rooms
const oct = (db, site) => P.liveFacts({ db, site, carry: input.carry, meeting: input.meeting, now: new Date("2099-10-15T17:00:00Z") });
const lvRoom = (it) => (it.id === "weekly_open_lv" ? { ...it, extra: { ...it.extra, zoom_id: "815 9593 1777", passcode: "" } } : it);
res.more = {
  lvBookOnly: oct({ ...input.db, shop: { ...input.db.shop, botm: input.db.shop.botm.filter((b) => b.pub === "lv") } }, input.site),
  phonePass: oct(input.db, { ...input.site, phone_access: { ...input.site.phone_access, committee: { phone_passcode: "4417092" } } }),
  digitsPass: oct(input.db, { ...input.site, meeting: { ...input.site.meeting, passcode: "238047" } }),
  noNumbers: oct(input.db, { ...input.site, phone_access: {} }),
  twoRooms: oct({ ...input.db, weekly_open: { items: input.db.weekly_open.items.map(lvRoom) } }, input.site),
};
// more deadlines than a slide carries: 23 issues of one theme, then one issue of two themes (the 24th and 25th rows),
// then one more — the rows stop after the whole 24th issue
const items = [];
const day = (n) => new Date(Date.UTC(2099, 10, 1 + 10 * n)).toISOString().slice(0, 10);
const key = (n) => { const m = 2100 * 12 + n; return `${Math.floor(m / 12)}-${String((m % 12) + 1).padStart(2, "0")}`; };
for (let i = 0; i < 23; i++) items.push({ id: `ed:gv:${i}`, lang: "en", title: `Theme ${i}`, extra: { publication: "gv", issue_key: key(i), deadline: day(i) } });
for (const t of ["Pair A", "Pair B"]) items.push({ id: `ed:gv:pair:${t}`, lang: "en", title: t, extra: { publication: "gv", issue_key: key(23), deadline: day(23) } });
items.push({ id: "ed:gv:last", lang: "en", title: "After", extra: { publication: "gv", issue_key: key(24), deadline: day(24) } });
res.many = P.liveData("deadlines", { pub: "gv" }, { db: { editorial: { items } }, site: input.site, now: new Date("2099-10-15T17:00:00Z") });
// tonight, after its meeting ended: the site's own list has dropped it (src/_data/meeting.js keeps a meeting until it
// ends), the rule still gives it — the next meeting stays tonight's until midnight Central
const m = C.meetingDates(input.site.meeting, 0, 2).find((d) => Date.parse(d.end) > Date.now());
res.tonight = { ymd: m.ymd, live: P.liveFacts({ db: {}, site: input.site, meeting: { upcoming: [] }, now: new Date(Date.parse(m.end) + 30 * 60000) }) };
res.fallbacks = P.FALLBACKS;
out(res);
"""
KINDS_X = [["deadlines", {}], ["deadlines", {"pub": "lv"}], ["deadlines", {"pub": "both", "limit": 3, "limit_each": 1}],
           ["events", {"limit": 10}], ["events", {"filter": "workshops"}], ["events", {"filter": "neta", "limit": 10}],
           ["events", {"filter": "calendar"}], ["events", {"filter": "assemblies"}], ["prices", {}], ["prices", {"pub": "lv"}],
           ["meeting", {}], ["lv-workshop", {}], ["issues", {}], ["monthly", {}], ["botm", {}], ["bulletin", {}],
           ["qr", {"url": "/contribute/", "caption": "Share"}]]
# Midnight Central on the 1st of a month (2099: summer time until Sunday, November 1; 2100: from Sunday, March 14)
NOV1, DEC1, JAN1, FEB1, MAR1 = ("2099-11-01T05:00:00.000Z", "2099-12-01T06:00:00.000Z", "2100-01-01T06:00:00.000Z",
                                "2100-02-01T06:00:00.000Z", "2100-03-01T06:00:00.000Z")
MAY1, JUL1 = "2100-05-01T05:00:00.000Z", "2100-07-01T05:00:00.000Z"
# The last moment of a meeting's day: midnight Central after it
OCT21_OVER, NOV18_OVER, DEC16_OVER = "2099-10-22T05:00:00.000Z", "2099-11-19T06:00:00.000Z", "2099-12-17T06:00:00.000Z"
# The end of the meeting itself: 8 PM Central
OCT21_END, NOV18_END, DEC16_END = "2099-10-22T01:00:00.000Z", "2099-11-19T02:00:00.000Z", "2099-12-17T02:00:00.000Z"
OCT21, NOV18, DEC16 = "Wednesday, October 21, 2099", "Wednesday, November 18, 2099", "Wednesday, December 16, 2099"
FB = {"meetings": "see the Meetings page"}


def live_at(v, when: str) -> str:
    """A {live:…} value at an instant (ISO), as the player reads it: a step's value from its `from`, nothing from
    `until`, and then — or for an empty value — the fallback."""
    if isinstance(v, str):
        return v
    val = v["value"]
    for st in v.get("steps", []):
        if st["from"] <= when:
            val = st["value"]
    if v.get("until") and v["until"] <= when:
        val = ""
    return val or v.get("fallback", "")


class Facts(unittest.TestCase):
    """The facts from made-up data at fixed clocks: before the price notice, during it, after the new prices start,
    after the notice; on a meeting night, during and after the meeting — and with no data at all."""

    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        node_ready(self)
        if Facts.r is None:
            Facts.r = run_js(self, FACTS_JS, data={
                "db": DB_X, "site": SITE_X, "carry": CARRY_X, "meeting": MEETING_X, "kinds": KINDS_X,
                "clocks": {"september": "2099-09-15T17:00:00Z", "october": "2099-10-15T17:00:00Z",
                           # the meeting night: 8:30 PM Central (the meeting ended at 8), then half past midnight
                           "meeting_night": "2099-10-22T01:30:00Z", "after_midnight": "2099-10-22T05:30:00Z",
                           "november": "2099-11-05T18:00:00Z", "december": "2099-12-10T18:00:00Z",
                           "january": "2100-01-15T18:00:00Z", "march": "2100-03-01T18:00:00Z", "may": "2100-05-15T17:00:00Z"}})
        self.oct = self.r["october"]

    def test_prices_switch_while_a_change_is_ahead(self):
        live = self.oct["live"]
        self.assertEqual(live["price_gv_print"], {"value": "$36.00", "steps": [{"from": JAN1, "value": "$39.00"}]})
        self.assertEqual(live["price_gv_digital"], {"value": "$29.99", "steps": [{"from": JAN1, "value": "$34.00"}]})
        self.assertEqual(live["price_lv_print"], {"value": "$18.00", "steps": [{"from": JAN1, "value": "$19.50"}]})
        self.assertEqual(live["price_lv_digital"], {"value": "$14.99", "steps": [{"from": JAN1, "value": "$17.00"}]})
        self.assertEqual(live["price_change_note"], {
            "value": "Prices change on January 1, 2100: Grapevine, 1 year: print $39.00, digital $34.00; La Viña, 1 year: "
                     "print $19.50, digital $17.00; Grapevine and La Viña books: $2.00 more each.",
            "steps": [{"from": JAN1, "value": "New prices since January 1, 2100."}], "until": FEB1})
        self.assertEqual(live["price_change_date"], {"value": "January 1, 2100", "until": FEB1})
        p = self.oct["kinds"]["prices"]
        self.assertEqual(p["rows"], [
            {"pub": "gv", "plan": "print", "price": "$36.00", "then": "$39.00"}, {"pub": "gv", "plan": "digital", "price": "$29.99", "then": "$34.00"},
            {"pub": "lv", "plan": "print", "price": "$18.00", "then": "$19.50"}, {"pub": "lv", "plan": "digital", "price": "$14.99", "then": "$17.00"}])
        self.assertEqual(p["change"], {"at": JAN1, "label": "January 1, 2100", "notice_from": "2099-10-01T05:00:00.000Z",
                                       "notice_until": FEB1, "books_more": "$2.00"})
        self.assertEqual(p["url"], "https://neta65.github.io/aagrapevine/shop/#price-changes")
        self.assertEqual([r["pub"] for r in self.oct["kinds"]["prices:lv"]["rows"]], ["lv", "lv"])

    def test_before_the_announcement_after_the_day_and_after_the_notice(self):
        sep, jan, mar = self.r["september"], self.r["january"], self.r["march"]
        # not announced yet: today's prices, no notice
        self.assertEqual(sep["live"]["price_gv_print"], "$36.00")
        self.assertEqual((sep["live"]["price_change_note"], sep["live"]["price_change_date"]), ("", ""))
        self.assertIsNone(sep["kinds"]["prices"]["change"])
        self.assertTrue(all(r["then"] is None for r in sep["kinds"]["prices"]["rows"]))
        # from the day: the announced price stands in for the store's old one; "New prices since …" until the notice ends
        self.assertEqual(jan["live"]["price_gv_print"], "$39.00")
        self.assertEqual(jan["live"]["price_lv_digital"], "$17.00")
        self.assertEqual(jan["live"]["price_change_note"], {"value": "New prices since January 1, 2100.", "until": FEB1})
        self.assertEqual(jan["live"]["price_change_date"], {"value": "January 1, 2100", "until": FEB1})
        self.assertTrue(all(r["then"] is None for r in jan["kinds"]["prices"]["rows"]))
        self.assertIsNotNone(jan["kinds"]["prices"]["change"])
        # after the notice: nothing more to say (empty by design: no fallback)
        self.assertEqual((mar["live"]["price_change_note"], mar["live"]["price_change_date"]), ("", ""))
        self.assertEqual(mar["live"]["price_gv_print"], "$39.00")
        self.assertIsNone(mar["kinds"]["prices"]["change"])
        self.assertEqual(mar["kinds"]["prices"]["url"], "https://neta65.github.io/aagrapevine/shop/#subscriptions")
        # a copy opened after the notice ended says nothing of it either
        note = self.oct["live"]["price_change_note"]
        self.assertEqual(live_at(note, "2100-02-02T00:00:00.000Z"), "")
        self.assertEqual(live_at(note, "2100-01-02T00:00:00.000Z"), "New prices since January 1, 2100.")

    def test_the_meeting(self):
        live = self.oct["live"]
        # the next meetings, each until it ends (a workshop's "the next meeting"); then "see the Meetings page"
        self.assertEqual(live["meeting_next"], {"value": OCT21, "steps": [{"from": OCT21_END, "value": NOV18}, {"from": NOV18_END, "value": DEC16}],
                                                "until": DEC16_END, "fallback": FB["meetings"]})
        # the meeting's day, each until midnight Central after it (the committee's title slide)
        self.assertEqual(live["meeting_day"], {"value": OCT21, "steps": [{"from": OCT21_OVER, "value": NOV18}, {"from": NOV18_OVER, "value": DEC16}],
                                               "until": DEC16_OVER, "fallback": FB["meetings"]})
        # the one after it (the committee's "Next meeting" slide, shown during the meeting): it moves on with it
        self.assertEqual(live["meeting_after"], {"value": NOV18, "steps": [{"from": OCT21_OVER, "value": DEC16}], "until": NOV18_OVER,
                                                 "fallback": FB["meetings"]})
        # the meeting's month (the title slide's "October 2099 meeting"), with its day
        self.assertEqual(live["meeting_month"], {"value": "October 2099", "steps": [{"from": OCT21_OVER, "value": "November 2099"},
                                                                                     {"from": NOV18_OVER, "value": "December 2099"}],
                                                 "until": DEC16_OVER, "fallback": "Monthly"})
        self.assertEqual(live["meeting_rule"], "every third Wednesday of the month")
        self.assertEqual(plain(live["meeting_time"]), "7:00 – 8:00 PM Central time")
        self.assertNotIn("\u2009", live["meeting_time"], "no break inside the time range")
        self.assertIn("\u202f\u2013" + WJ + "\u202f", live["meeting_time"], "not even after the dash (UAX #14 LB12a)")
        self.assertEqual((live["meeting_zoom_id"], live["meeting_passcode"]), ("949\u00a0476\u00a07497", "neta65"))
        m = self.oct["kinds"]["meeting"]
        self.assertEqual(m["rows"], [{"start": "2099-10-22T00:00:00.000Z", "end": "2099-10-22T01:00:00.000Z", "label": OCT21},
                                     {"start": "2099-11-19T01:00:00.000Z", "end": "2099-11-19T02:00:00.000Z", "label": NOV18},
                                     {"start": "2099-12-17T01:00:00.000Z", "end": "2099-12-17T02:00:00.000Z", "label": DEC16}])
        self.assertEqual(m["limit"], 3, "every date known; the player shows the next three")
        self.assertEqual(m["rule"], "Every third Wednesday of the month")
        self.assertEqual((m["zoom_id"], m["passcode"], m["url"]), ("949\u00a0476\u00a07497", "neta65", "https://us02web.zoom.us/j/9494767497"))
        self.assertEqual(m["page"], "https://neta65.github.io/aagrapevine/meetings/#committee-meeting")
        # no date after the last one known: the fallback from then on, never a date that is over
        nov = self.r["november"]["live"]
        self.assertEqual(nov["meeting_after"], {"value": DEC16, "until": NOV18_OVER, "fallback": FB["meetings"]})
        self.assertEqual(live_at(nov["meeting_after"], NOV18_OVER), FB["meetings"])
        self.assertEqual(nov["meeting_next"], {"value": NOV18, "steps": [{"from": NOV18_END, "value": DEC16}], "until": DEC16_END,
                                               "fallback": FB["meetings"]})
        self.assertEqual(live_at(nov["meeting_next"], DEC16_END), FB["meetings"])
        mar = self.r["march"]["live"]
        for k in ("meeting_next", "meeting_day", "meeting_after"):
            self.assertEqual(mar[k], {"value": "", "fallback": FB["meetings"]}, k)
        self.assertEqual(mar["meeting_month"], {"value": "", "fallback": "Monthly"})

    def test_the_meeting_night(self):
        """During and after tonight's meeting (8:30 PM Central, the meeting ended at 8) the meeting's day is still
        tonight's and the one after it next month's — the committee deck reads right until midnight Central — while a
        workshop's "the next meeting" is next month's as soon as tonight's has ended."""
        night, late = self.r["meeting_night"]["live"], self.r["after_midnight"]["live"]
        self.assertEqual(night["meeting_next"], {"value": NOV18, "steps": [{"from": NOV18_END, "value": DEC16}], "until": DEC16_END,
                                                 "fallback": FB["meetings"]}, "tonight's meeting is over: the next one")
        self.assertEqual(night["meeting_day"]["value"], OCT21)
        self.assertEqual(night["meeting_after"]["value"], NOV18)
        self.assertEqual(night["meeting_month"]["value"], "October 2099")
        # a copy opened at 8:30 PM says the same (the viewer's clock reads the steps)
        at = "2099-10-22T01:30:00.000Z"
        self.assertEqual(live_at(self.oct["live"]["meeting_next"], at), NOV18)
        self.assertEqual(live_at(self.oct["live"]["meeting_day"], at), OCT21)
        self.assertEqual(live_at(self.oct["live"]["meeting_after"], at), NOV18)
        self.assertEqual(live_at(self.oct["live"]["meeting_month"], at), "October 2099")
        # …and at 7:30 PM, during the meeting, the next meeting is tonight's
        self.assertEqual(live_at(self.oct["live"]["meeting_next"], "2099-10-22T00:30:00.000Z"), OCT21)
        # from midnight: the next month's
        self.assertEqual(late["meeting_next"], night["meeting_next"])
        self.assertEqual(late["meeting_day"], {"value": NOV18, "steps": [{"from": NOV18_OVER, "value": DEC16}], "until": DEC16_OVER,
                                               "fallback": FB["meetings"]})
        self.assertEqual(late["meeting_after"], {"value": DEC16, "until": NOV18_OVER, "fallback": FB["meetings"]})
        self.assertEqual(live_at(self.oct["live"]["meeting_day"], "2099-10-22T05:30:00.000Z"), NOV18)
        # the meeting rows: the player leaves tonight's out once it has ended (its `end`)
        self.assertEqual(self.r["meeting_night"]["kinds"]["meeting"]["rows"][0]["end"], "2099-10-22T01:00:00.000Z")
        # a build made after the meeting ended, when the site's own list (src/_data/meeting.js) has dropped it: the
        # rule still gives it (committee.js meetingDates), and it stays the meeting's day until midnight
        t = self.r["tonight"]
        d = datetime.strptime(t["ymd"], "%Y-%m-%d")
        self.assertEqual(t["live"]["meeting_day"]["value"], f"{d:%A, %B} {d.day}, {d.year}")
        nxt = d + timedelta(days=1)
        self.assertRegex(t["live"]["meeting_day"]["steps"][0]["from"], rf"^{nxt:%Y-%m-%d}T0[56]:00:00\.000Z$", "midnight Central after it")
        self.assertEqual(t["live"]["meeting_month"]["value"], f"{d:%B %Y}")
        self.assertEqual(t["live"]["meeting_next"]["value"], t["live"]["meeting_after"]["value"], "the next one is next month's")
        self.assertNotEqual(t["live"]["meeting_next"]["value"], t["live"]["meeting_day"]["value"])

    def test_joining_the_meeting_by_phone(self):
        # /accessibility/#phone's facts (access.js axPhone): Zoom's first number and its city; what a caller types
        live, more = self.oct["live"], self.r["more"]
        self.assertEqual(live["meeting_phone"], "+1 346 248 7799 (Houston)")
        self.assertEqual(live["meeting_phone_passcode"], "", "a passcode with letters and no phone passcode yet: unknown")
        self.assertEqual(more["phonePass"]["meeting_phone_passcode"], "4417092", "the chair's numbers-only phone passcode")
        self.assertEqual(more["digitsPass"]["meeting_phone_passcode"], "238047", "a numbers-only passcode: the same by phone")
        self.assertEqual(more["noNumbers"]["meeting_phone"], {"value": "", "fallback": "see the Accessibility page"})
        self.assertEqual(more["noNumbers"]["meeting_phone_passcode"], "", "empty by design")
        # the magazines' story lines (db.audio_project — /contribute/#record)
        self.assertEqual((live["gv_audio_phone"], live["lv_audio_phone"]), ("(559) 726-1216", "(559) 670-1601"))

    def test_deadlines(self):
        d = self.oct["kinds"]["deadlines"]
        may = "May–June 2100"
        # (La Viña's theme with its English beside it: a machine's, so gloss_machine — the player marks it)
        self.assertEqual(d["rows"], [
            {"pub": "gv", "due": "2099-12-02T05:59:59.999Z", "due_label": "December 1, 2099", "issue": "July 2100", "issue_key": "2100-07",
             "theme": "Annual Prison Issue", "theme_lang": "en", "gloss": "", "gloss_machine": False},
            {"pub": "lv", "due": "2100-02-16T05:59:59.999Z", "due_label": "February 15, 2100", "issue": may, "issue_key": "2100-05",
             "theme": "Servicio en AA", "theme_lang": "es", "gloss": "AA Service", "gloss_machine": True},
            {"pub": "gv", "due": "2100-07-02T04:59:59.999Z", "due_label": "July 1, 2100", "issue": "February 2101", "issue_key": "2101-02",
             "theme": "Sober Holidays!", "theme_lang": "en", "gloss": "", "gloss_machine": False},
            {"pub": "gv", "due": "2100-07-02T04:59:59.999Z", "due_label": "July 1, 2100", "issue": "February 2101", "issue_key": "2101-02",
             "theme": "Remote Communities", "theme_lang": "en", "gloss": "", "gloss_machine": False}])
        self.assertEqual((d["limit"], d["limit_each"], d["url"]), (6, None, "https://neta65.github.io/aagrapevine/contribute/#deadlines"))
        self.assertEqual([r["pub"] for r in self.oct["kinds"]["deadlines:lv"]["rows"]], ["lv"])
        each = self.oct["kinds"]["deadlines:both:each"]
        self.assertEqual((len(each["rows"]), each["limit"], each["limit_each"]), (4, 3, 1), "every row; the player applies the limits")
        live = self.oct["live"]
        self.assertEqual(live["next_deadline_gv"], {
            "value": "December 1, 2099 — July 2100: Annual Prison Issue",
            "steps": [{"from": "2099-12-02T06:00:00.000Z", "value": "July 1, 2100 — February 2101: Sober Holidays! / Remote Communities"}],
            "until": "2100-07-02T05:00:00.000Z", "fallback": "see aagrapevine.org for Grapevine's themes"})
        # a fact's text cannot mark a machine translation: it leaves it out
        self.assertEqual(live["next_deadline_lv"], {"value": f"February 15, 2100 — {may}: Servicio en AA",
                                                    "until": "2100-02-16T06:00:00.000Z", "fallback": "see aalavina.org for La Viña's themes"})
        # past the last deadline known: where to look, never a date that is over
        self.assertEqual(live_at(live["next_deadline_lv"], "2100-03-01T00:00:00.000Z"), "see aalavina.org for La Viña's themes")

    def test_deadlines_keep_whole_issues(self):
        """More open deadlines than a slide carries: the rows stop after MAX_ROWS (24), but never between two themes
        of one issue (the 24th row's issue has a second theme: it comes along)."""
        rows = self.r["many"]["rows"]
        self.assertEqual(len(rows), 25)
        self.assertEqual([r["theme"] for r in rows[-2:]], ["Pair A", "Pair B"])
        self.assertEqual(rows[-1]["issue_key"], rows[-2]["issue_key"])
        self.assertNotIn("After", [r["theme"] for r in rows])

    def test_events_and_their_filters(self):
        k = self.oct["kinds"]
        titles = lambda key: [r["title"] for r in k[key]["rows"]]  # noqa: E731
        booth, lvw = "GV/LV booth at CityWide Dallas", "La Viña Monthly Virtual Workshop (in Spanish)"
        fall, spring = "NETA 65 Fall Assembly 2099", "NETA 65 Spring Assembly 2100"
        # soonest first, nothing over, every date of a monthly series (the player shows the first `limit` still ahead)
        self.assertEqual(titles("events"), ["Grapevine Writing Workshop — Tyler", lvw, "Grapevine Day", fall, booth, lvw,
                                            "Area 68 Assembly", booth, spring])
        self.assertEqual(k["events"]["limit"], 10)
        self.assertEqual(titles("events:workshops"), ["Grapevine Writing Workshop — Tyler", lvw, lvw])
        self.assertEqual(k["events:workshops"]["limit"], 5, "the default")
        self.assertEqual(titles("events:neta"), ["Grapevine Writing Workshop — Tyler", fall, booth, booth, spring])
        self.assertEqual(titles("events:calendar"), [lvw, "Grapevine Day", lvw, "Area 68 Assembly"])
        # NETA 65's assemblies, never another Area's on an outside calendar
        self.assertEqual(titles("events:assemblies"), [fall, spring])
        self.assertEqual({r["kind"] for r in k["events:assemblies"]["rows"]}, {"assembly"})
        rows = {r["title"]: r for r in k["events"]["rows"]}
        self.assertEqual([r["kind"] for r in k["events"]["rows"]], ["gv", "lv", "gv", "assembly", "booth", "lv", "assembly", "booth", "assembly"])
        # each date of a series carries its id, the same on every date (the player keeps one row per series: its next
        # date still ahead); a one-off event: ""
        self.assertEqual([r["series"] for r in k["events"]["rows"]],
                         ["", "lv-monthly-workshop", "", "", "citywide-dallas", "lv-monthly-workshop", "", "citywide-dallas", ""])
        tyler = rows["Grapevine Writing Workshop — Tyler"]
        self.assertEqual((tyler["start"], tyler["end"], tyler["all_day"], tyler["place"], tyler["online"]),
                         ("2099-10-20T23:00:00.000Z", "2099-10-21T01:00:00.000Z", False, "Tyler, TX", False))
        self.assertEqual(tyler["date_label"], "Tuesday, October 20, 2099")
        # its time range never cut at the dash, as the meeting's time (a word joiner after it, no-break spaces)
        self.assertEqual(plain(tyler["time_label"]), "6:00 – 8:00 PM CDT")
        self.assertIn(" –" + WJ + " ", tyler["time_label"])
        self.assertEqual(tyler["url"], "https://neta65.github.io/aagrapevine/events/#2099-10-20-gv-writing-workshop-tyler")
        assembly = rows[fall]
        self.assertTrue(assembly["all_day"])
        self.assertEqual((assembly["start"], assembly["end"]), ("2099-11-06T06:00:00.000Z", "2099-11-09T06:00:00.000Z"),
                         "an assembly lasts from midnight before its first day to midnight after its last (Central)")
        lv = rows[lvw]
        self.assertEqual((lv["online"], lv["place"]), (True, ""))
        self.assertEqual(rows["Grapevine Day"]["url"], "https://www.aagrapevine.org/events/day")
        self.assertEqual(k["events"]["url"], "https://neta65.github.io/aagrapevine/events/")

    def test_the_next_assembly(self):
        """The next NETA 65 assembly until it is over, then the one after it (its details to be confirmed), then
        "see the Events page"."""
        fall = "NETA 65 Fall Assembly 2099 · Fri, Nov 6 – Sun, Nov 8, 2099"
        spring = "NETA 65 Spring Assembly 2100 · Fri, Mar 19 – Sun, Mar 21, 2100 (details to be confirmed)"
        v = self.oct["live"]["assembly_next"]
        self.assertEqual(plain(v["value"]), fall)
        self.assertEqual(len(v["steps"]), 1)
        self.assertEqual((v["steps"][0]["from"], plain(v["steps"][0]["value"])), ("2099-11-09T06:00:00.000Z", spring))
        self.assertEqual((v["until"], v["fallback"]), ("2100-03-22T05:00:00.000Z", "see the Events page"))
        self.assertEqual(self.r["empty"]["live"]["assembly_next"], {"value": "", "fallback": "see the Events page"})

    def test_the_weekly_open_meetings(self):
        """/meetings/#weekly-open's facts: the day, the time in Central and Eastern, La Viña's first meeting
        ("starting" before it, "since" from its day), and their Zoom room (no-break spaces: never cut in the middle)."""
        live, nov = self.oct["live"], self.r["november"]["live"]
        self.assertEqual(live["gv_open_meeting"], "Wednesdays, 11:00 AM Central (noon Eastern)")
        lv = "Thursdays, 11:00 AM Central (noon Eastern)"
        self.assertEqual(live["lv_open_meeting"], {"value": f"{lv}, starting Nov. 5, 2099",
                                                   "steps": [{"from": "2099-11-05T06:00:00.000Z", "value": f"{lv}, since Nov. 5, 2099"}]})
        self.assertEqual(nov["lv_open_meeting"], f"{lv}, since Nov. 5, 2099", "a build after the first meeting")
        self.assertEqual(live["open_meeting_zoom"], "Zoom\u00a0871\u00a02036\u00a08287, passcode\u00a0238047", "one room for both")
        self.assertEqual(plain(self.r["more"]["twoRooms"]["open_meeting_zoom"]),
                         "Grapevine: Zoom 871 2036 8287, passcode 238047 · La Viña: Zoom 815 9593 1777")
        for k in ("gv_open_meeting", "lv_open_meeting", "open_meeting_zoom"):
            self.assertEqual(self.r["empty"]["live"][k], {"value": "", "fallback": "see the Meetings page"}, k)

    def test_la_vinas_workshop(self):
        w = self.oct["kinds"]["lv-workshop"]
        self.assertEqual(w["rows"], [{"start": "2099-10-22T19:00:00.000Z", "end": "2099-10-22T20:00:00.000Z", "label": "Thursday, October 22, 2099"},
                                     {"start": "2099-11-19T20:00:00.000Z", "end": "2099-11-19T21:00:00.000Z", "label": "Thursday, November 19, 2099"}])
        self.assertEqual(w["limit"], 3)
        self.assertEqual(plain(w["time"]), "2:00 – 3:00 PM Central time (3:00 PM Eastern)")
        # one line on a slide: no break on either side of the dash, nor before a PM
        self.assertIn(" –" + WJ + " ", w["time"])
        self.assertNotRegex(w["time"], "\\d[  ][AP]M")
        self.assertEqual((w["zoom_id"], w["url"], w["contact"]), ("815\u00a09593\u00a01777", "https://us06web.zoom.us/j/81595931777", "lveditorial@aagrapevine.org"))
        self.assertTrue(w["page"].startswith("https://neta65.github.io/aagrapevine/events/#"))
        live = self.oct["live"]
        self.assertEqual(live["lv_workshop_next"], {"value": "Thursday, October 22, 2099",
                                                    "steps": [{"from": "2099-10-22T20:00:00.000Z", "value": "Thursday, November 19, 2099"}],
                                                    "until": "2099-11-19T21:00:00.000Z", "fallback": "see La Viña's events calendar at aalavina.org"})
        self.assertEqual(live["lv_workshop_time"], w["time"])
        self.assertEqual(live["lv_workshop_zoom_id"], "815\u00a09593\u00a01777")

    def test_this_month_and_the_next_issues(self):
        # the month's facts switch together at midnight Central on the 1st: this month's issue, the next one and this
        # month's theme for the months ahead (Grapevine: the calendar's call for stories of an issue not out yet;
        # La Viña: its dated theme, Spanish with the English beside it), La Viña's issues named in one style
        live = self.oct["live"]
        self.assertEqual(live["month"]["value"], "October 2099")
        self.assertEqual(live["month"]["steps"][:3], [{"from": NOV1, "value": "November 2099"}, {"from": DEC1, "value": "December 2099"},
                                                      {"from": JAN1, "value": "January 2100"}])
        self.assertEqual(len(live["month"]["steps"]), 11, "a year of months")
        self.assertEqual(live["year"], {"value": "2099", "steps": [{"from": JAN1, "value": "2100"}]})
        gv = {"value": "October 2099 · Loneliness", "steps": [{"from": NOV1, "value": "November 2099 · Classic Grapevine"},
                                                              {"from": DEC1, "value": "December 2099 · Sober Holidays!"}],
              "until": JAN1, "fallback": "see aagrapevine.org"}
        self.assertEqual(live["gv_issue"], gv)
        self.assertEqual(live["gv_next_issue"], {"value": "November 2099 · Classic Grapevine", "steps": [
            {"from": NOV1, "value": "December 2099 · Sober Holidays!"}, {"from": DEC1, "value": ""}], "until": JAN1, "fallback": "see aagrapevine.org"})
        self.assertEqual(live["gv_theme"], {"value": "Loneliness", "steps": [{"from": NOV1, "value": "Classic Grapevine"},
                                                                             {"from": DEC1, "value": "Sober Holidays!"}],
                                            "until": JAN1, "fallback": "see aagrapevine.org"})
        # (the English words of a theme beside it when they are ours — "The Joy of Living" is written by hand in
        # data/translations/overrides.yml —, never a machine's: "AA Service" is left out of the facts' text)
        overrides = yaml.safe_load((ROOT / "data" / "translations" / "overrides.yml").read_text(encoding="utf-8"))
        self.assertEqual((overrides.get("La alegría de vivir") or {}).get("en"), "The Joy of Living", "the hand-written English this leans on")
        joy = "November–December 2099 · La alegría de vivir (The Joy of Living)"
        self.assertEqual(live["lv_issue"], {"value": "September–October 2099 · Servicio en AA", "steps": [{"from": NOV1, "value": joy}],
                                            "until": JAN1, "fallback": "see aalavina.org"})
        self.assertEqual(live["lv_next_issue"], {"value": joy, "steps": [{"from": NOV1, "value": ""}], "until": JAN1, "fallback": "see aalavina.org"})
        self.assertEqual(live["lv_theme"], {"value": "Servicio en AA", "steps": [{"from": NOV1, "value": "La alegría de vivir (The Joy of Living)"}],
                                            "until": JAN1, "fallback": "see aalavina.org"})
        # nothing known of the next issue: the fallback, never "Next issue:" with nothing after it
        self.assertEqual(live_at(live["lv_next_issue"], "2099-11-02T00:00:00.000Z"), "see aalavina.org")
        # a build in November says what October's said from the 1st; La Viña's moves on on January 1
        nov = self.r["november"]["live"]
        self.assertEqual(nov["gv_issue"], {"value": "November 2099 · Classic Grapevine", "steps": [
            {"from": DEC1, "value": "December 2099 · Sober Holidays!"}, {"from": JAN1, "value": ""}], "until": FEB1, "fallback": "see aagrapevine.org"})
        self.assertEqual(nov["gv_next_issue"], {"value": "December 2099 · Sober Holidays!", "steps": [{"from": DEC1, "value": ""}],
                                                "until": FEB1, "fallback": "see aagrapevine.org"})
        self.assertEqual(nov["lv_issue"], {"value": joy, "steps": [{"from": JAN1, "value": ""}], "until": MAR1, "fallback": "see aalavina.org"})
        self.assertEqual(nov["lv_next_issue"], {"value": "", "fallback": "see aalavina.org"})
        self.assertEqual(self.r["november"]["kinds"]["issues"]["lv"],
                         {"label": "November–December 2099", "theme": "La alegría de vivir", "theme_lang": "es", "gloss": "The Joy of Living",
                          "gloss_machine": False},
                         "the issues block shows what {live:lv_issue} says; hand-written English, though its item lists \"en\" in `machine`")
        # a new year: the year switches with the month
        self.assertEqual(self.r["december"]["live"]["year"], {"value": "2099", "steps": [{"from": JAN1, "value": "2100"}]})
        # nothing known of La Viña's issue of the months now (no data, no dated theme): its calendar still says which
        # issue comes next, and when (La Viña's issues start in odd months)
        may = "May–June 2100 · Servicio en AA"
        self.assertEqual(self.r["january"]["live"]["lv_next_issue"], {"value": "", "steps": [{"from": MAR1, "value": may}], "until": MAY1,
                                                                      "fallback": "see aalavina.org"})
        self.assertEqual(self.r["march"]["live"]["lv_next_issue"], {"value": may, "steps": [{"from": MAY1, "value": ""}], "until": JUL1,
                                                                    "fallback": "see aalavina.org"})
        self.assertEqual(self.r["march"]["live"]["lv_issue"], {"value": "", "steps": [{"from": MAY1, "value": may}], "until": JUL1,
                                                               "fallback": "see aalavina.org"})
        # in May that issue's block: its theme from La Viña's call for stories, the machine's English marked
        self.assertEqual(self.r["may"]["kinds"]["issues"]["lv"], {"label": "May–June 2100", "theme": "Servicio en AA", "theme_lang": "es",
                                                                  "gloss": "AA Service", "gloss_machine": True})

    def test_issues_toolkit_book_bulletin_and_the_rest(self):
        live, k = self.oct["live"], self.oct["kinds"]
        self.assertEqual(k["issues"], {"month": "October 2099",
                                       "gv": {"label": "October 2099", "theme": "Loneliness", "theme_lang": "en", "gloss": "", "gloss_machine": False},
                                       "lv": {"label": "September–October 2099", "theme": "Servicio en AA", "theme_lang": "es", "gloss": "AA Service",
                                              "gloss_machine": True},
                                       "url": "https://neta65.github.io/aagrapevine/read/"})
        self.assertEqual(k["monthly"], {"month": "October 2099", "url": "https://neta65.github.io/aagrapevine/monthly/2099-10/",
                                        "tips": [{"title": "Give it to a newcomer", "text": "Newcomers feel isolated: this issue speaks to that."}],
                                        "limit": 3})
        # Grapevine's Book of the Month, La Viña's Libro del mes — each its own, even when only one is on offer; when an
        # offer is over (or none is known), where to find the month's book
        gv_fb, lv_fb = "see aagrapevine.org's Book of the Month", "see aalavina.org's Libro del mes"
        self.assertEqual(live["botm"], {"value": "No Matter What", "until": "2099-10-21T05:00:00.000Z", "fallback": gv_fb})
        self.assertEqual(live["botm_lv"], {"value": "Frente a Frente", "until": "2099-10-21T05:00:00.000Z", "fallback": lv_fb})
        self.assertEqual(live_at(live["botm"], "2099-10-21T05:00:00.000Z"), gv_fb, "the day after the offer ends")
        lv_only = self.r["more"]["lvBookOnly"]
        self.assertEqual((lv_only["botm"], lv_only["botm_lv"]), ({"value": "", "fallback": gv_fb},
                                                                {"value": "Frente a Frente", "until": "2099-10-21T05:00:00.000Z", "fallback": lv_fb}))
        self.assertEqual((self.r["january"]["live"]["botm"], self.r["january"]["live"]["botm_lv"]),
                         ({"value": "", "fallback": gv_fb}, {"value": "", "fallback": lv_fb}), "both offers over")
        b = k["botm"]
        self.assertEqual((b["title"], b["mag"], b["lang"], b["note"], b["until"]), ("No Matter What", "Grapevine", "en", "20% off through October 20", "2099-10-21T05:00:00.000Z"))
        self.assertEqual(b["url"], "https://neta65.github.io/aagrapevine/shop/#botm")
        self.assertEqual((b["also"]["title"], b["also"]["mag"], b["also"]["lang"]), ("Frente a Frente", "La Viña", "es"))
        self.assertEqual(k["bulletin"]["rows"], [
            {"title": "The newest post", "date_label": "October 10, 2099", "url": "https://neta65.github.io/aagrapevine/bulletin/#2099-10-10-new"},
            {"title": "Pinned and older", "date_label": "October 1, 2099", "url": "https://neta65.github.io/aagrapevine/bulletin/#2099-10-01-pinned"}],
            "the newest first, whatever is pinned; nothing over")
        self.assertEqual(k["bulletin"]["limit"], 3)
        self.assertEqual(k["qr"]["url"], "https://neta65.github.io/aagrapevine/contribute/")
        self.assertEqual(k["qr"]["label"], "Share")
        self.assertEqual((live["site"], live["site_url"], live["email"], live["panel"]),
                         ("neta65.github.io/aagrapevine", "https://neta65.github.io/aagrapevine/", "grapevine@neta65.org", "Panel 77 (2027–2028)"))
        self.assertEqual((live["as_of"], live["month"]["value"], live["year"]["value"]), ("October 15, 2099", "October 2099", "2099"))

    def test_the_deck_file_drive_copy_and_closing_qr(self):
        d = self.r["deck"]
        self.assertEqual(d["drive"], {"view": "https://drive.google.com/file/d/new/view", "date": "2099-10-01"}, "the newest file of that title")
        self.assertEqual(d["built"], "2099-10-15T17:00:00.000Z")
        self.assertEqual(d["as_of"], "October 15, 2099")
        q, w = d["slides"]
        self.assertEqual(q["data"], {"url": "https://neta65.github.io/aagrapevine/meetings/", "label": "neta65.github.io/aagrapevine/meetings/", "svg": "<svg "})
        self.assertIsNone(w["data"])
        self.assertEqual(set(d["live"]), LIVE_KEYS)

    def test_missing_data_gives_fallbacks_never_invented_values(self):
        e = self.r["empty"]
        fallbacks = self.r["fallbacks"]
        self.assertLessEqual(set(fallbacks), LIVE_KEYS)
        # only what the clock and the site's address say; every other fact says where to look, or nothing
        months = e["live"]["month"]["steps"]
        filled = {"site": "neta65.github.io/aagrapevine", "site_url": "https://neta65.github.io/aagrapevine/",
                  "as_of": "October 15, 2099", "year": {"value": "2099", "steps": [{"from": JAN1, "value": "2100"}]},
                  "month": {"value": "October 2099", "steps": months}}
        self.assertEqual((months[0], months[-1]), ({"from": NOV1, "value": "November 2099"}, {"from": "2100-09-01T05:00:00.000Z", "value": "September 2100"}))
        self.assertEqual(set(e["live"]), LIVE_KEYS)
        for k, v in e["live"].items():
            self.assertEqual(v, filled.get(k, {"value": "", "fallback": fallbacks[k]} if k in fallbacks else ""), k)
        # empty by design: no price notice, no phone passcode yet; known from the site's settings alone
        for k in ("price_change_note", "price_change_date", "meeting_phone_passcode", "meeting_rule", "meeting_time", "email"):
            self.assertNotIn(k, fallbacks)
        k = e["kinds"]
        for kind in ("deadlines", "events", "bulletin"):
            self.assertEqual(k[kind]["rows"], [], kind)
        self.assertEqual((k["prices"]["rows"], k["prices"]["change"]), ([], None))
        self.assertEqual((k["meeting"]["rows"], k["meeting"]["rule"], k["meeting"]["time"], k["meeting"]["url"]), ([], "", "", ""))
        self.assertEqual((k["lv-workshop"]["rows"], k["lv-workshop"]["time"], k["lv-workshop"]["contact"]), ([], "", ""))
        self.assertEqual((k["issues"]["gv"], k["issues"]["lv"]), (None, None))
        self.assertEqual(k["monthly"]["tips"], [])
        self.assertEqual((k["botm"]["title"], k["botm"]["also"]), ("", None))
        # the player still gets somewhere to point: "see <url>"
        for kind in ("deadlines", "events", "prices", "issues", "monthly", "botm", "bulletin"):
            self.assertTrue(k[kind]["url"].startswith("https://neta65.github.io/aagrapevine/"), kind)
        self.assertEqual(k["qr"]["svg"], "<svg ")

    def test_the_readme_lists_every_fallback(self):
        """config/presentations/README.md (the deck writers' guide): every {live:…} key, with what it says when there is
        nothing to say — the build's own words (FALLBACKS), or "—"."""
        readme = (ROOT / "config" / "presentations" / "README.md").read_text(encoding="utf-8")
        table = readme[readme.index("| Key | Example |"):].split("\n\n", 1)[0]
        rows = [line for line in table.splitlines() if line.startswith("| `")]
        for key in sorted(LIVE_KEYS):
            with self.subTest(key=key):
                row = next((r for r in rows if f"`{key}`" in r.split("|")[1]), None)
                self.assertIsNotNone(row, f"{key}: no row in the README's table of {{live:…}} keys")
                last = row.rstrip(" |").split("|")[-1].strip()
                self.assertEqual(last, f'"{self.r["fallbacks"][key]}"' if key in self.r["fallbacks"] else "—", key)


if __name__ == "__main__":
    unittest.main()
