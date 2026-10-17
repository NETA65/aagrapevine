"""Round 12, the GVR / RLV corner: "Pass it on" (/gvr/#pass-it-on) and the booth's question of the day ("Did you know?
/ ¿Sabías que…?" on About and /gvr/).

  * Daily questions, build side — eleventy/filters/booth.js dailyQuestions on a small CSV and on the committee's
    real one, always at a FIXED clock (never today's date): the build's Central day (also at the clock changes and at
    New Year), DAILY_DAYS days of DAILY_PER questions, none twice in a day; only quiz / truefalse / fill rows that are
    on, in their dates and playable in the page language (GVB.playable, the booth's own rule — now part of GVB), each
    with its dates; none that names {event}, none that speaks as the booth's table ("this table", "Like this one!",
    "Ask us", "esta mesa", "¡Como esta!", "Pregúntanos" — in either language: DailyQuestionsBoothVoice) and none whose
    web column says no, with still a week of 4 a day in each language; on /es/ a La Viña question first every day;
    the words in the page language only; a source link only to AA's own sites (never YouTube or the podcast's host,
    which the booth may play from); only the questions the days use (a few KB, never the booth file); a day's questions depend on the day alone,
    so tomorrow's build shows what today's says for tomorrow. The committee's real CSV (DailyQuestionsRealCsv) is
    judged by the Code check alone (scripts/ops/gate_tests.py CONTENT_TESTS).
  * Daily questions, browser side — src/assets/js/read.js dailyQuestion in a pretend page with its own clock: the
    visitor's Central day picks the list (two days after the build: the third day's; past the last day: round again,
    without a question whose until is over; a clock before the build: the first day; broken data: no card); answers
    (True / False, a choice, "Show the answer"), "Another question" up to the day's last, nothing stored.
  * Pass it on — the page (the section, its nav chip, the three moments, the print-only sheets, the macro on both
    pages, read.js on About), its words in both languages (no classroom words, never "quiz", no "PDF"; the same
    {placeholders}; "no need to register" said with the site's one verb, "registrarse"), the ready-made e-mails (written from the sender, in one register) and read.js gvrPass (the
    copied text keeps the message's lines; Print sets data-print for its sheet and afterprint clears it). The office
    addresses the committee keeps (config/site.yml links.gvr_office_email / rlv_office_email: each an e-mail address —
    La Viña may name one of its own) are OfficeAddresses, judged by the Code check alone (CONTENT_TESTS).
The browser checks are tests/browser/test_r12_u5_gvr.py.

    python -m unittest tests.test_r12_u5_gvr -v
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-16T04:30:00Z"          # 11:30 PM on October 15 in Central time (CDT): the build's day is the 15th
SITE = {"url": "https://neta65.github.io/aagrapevine", "committee": "NETA 65 Grapevine & La Viña Committee",
        "committee_es": "Comité de Grapevine y La Viña de NETA 65"}
COLUMNS = ["id", "on", "type", "pub", "tags", "weight", "from", "until", "seconds", "reveal",
           "title_en", "text_en", "choices_en", "correct", "answer_en", "explain_en", "credit_en",
           "title_es", "text_es", "choices_es", "answer_es", "explain_es", "credit_es",
           "media_url", "start", "end", "qr_url", "source_url", "notes", "web"]
# Words that speak as the booth's table ("Like this one!", "Por eso esta mesa…", "Ask us…", "¡Pregúntanos…!"): right
# at the table, but a web page has no table for them to point to, so the question of the day never carries them. The
# test's own list (booth.js BOOTH_VOICE is the build's, a little wider): a narrower pattern there fails here.
TABLE_TALK = re.compile(r"\b(?:this|our) table\b|\blike this one\b|\bask us\b|\b(?:esta|nuestra) mesa\b|¡como esta!"
                        r"|\bpregúnt[ae]n?nos\b", re.I)


def card_words(it: dict) -> str:
    """Everything a question of the day shows, field by field (never one field's end run into the next one's start)."""
    return "\n".join([it["text"], *it["choices"], it["answer"], it["explain"], it["credit"]])


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def row(id_, type_, pub, en, es=None, **kw) -> dict:
    """A CSV row: en / es = (text, choices "A|B", answer, explain, credit) — es None: English only."""
    r = {c: "" for c in COLUMNS}
    r.update(id=id_, on=kw.pop("on", "yes"), type=type_, pub=pub, source_url=kw.pop("source", "https://www.aagrapevine.org/history"))
    for lang, words in (("en", en), ("es", es)):
        if words:
            text, choices, answer, explain, credit = words
            r.update({f"text_{lang}": text, f"choices_{lang}": choices, f"answer_{lang}": answer,
                      f"explain_{lang}": explain, f"credit_{lang}": credit})
    r.update(kw)
    return r


ROWS = [
    row("q-gv-one", "quiz", "gv", ("When did Grapevine start?", "1944|1960|1975", "", "June 1944.", "Source: aagrapevine.org"),
        ("¿Cuándo empezó Grapevine?", "1944|1960|1975", "", "Junio de 1944.", "Fuente: aagrapevine.org"), correct="1"),
    row("q-lv-one", "quiz", "lv", ("When did La Viña start?", "1996|2001", "", "In 1996.", "Source: aalavina.org"),
        ("¿Cuándo empezó La Viña?", "1996|2001", "", "En 1996.", "Fuente: aalavina.org"), correct="1",
        source="https://example.org/not-aa"),
    row("q-lv-two", "quiz", "lv", ("How often does La Viña come out?", "Monthly|Every two months", "", "Every two months.", ""),
        ("¿Cada cuánto sale La Viña?", "Cada mes|Cada dos meses", "", "Cada dos meses.", ""), correct="2",
        source="https://www.aalavina.org/"),
    row("tf-both", "truefalse", "both", ("Both magazines are AA's.", "", "", "True!", "Source: aa.org"),
        ("Las dos revistas son de AA.", "", "", "¡Verdadero!", "Fuente: aa.org"), correct="true", source="https://www.aa.org/"),
    row("fill-gv", "fill", "gv", ("Grapevine is the ___ in print.", "", "meeting", "Our meeting in print.", ""),
        ("Grapevine es la ___ impresa.", "", "reunión", "Nuestra reunión impresa.", ""),
        source="https://player.captivate.fm/episode/xyz"),
    row("tf-until", "truefalse", "gv", ("Over after the 16th.", "", "", "", ""), ("Termina el 16.", "", "", "", ""),
        correct="false", until="2026-10-16"),
    row("q-from", "quiz", "gv", ("Starts on the 18th?", "Yes|No", "", "", ""), ("¿Empieza el 18?", "Sí|No", "", "", ""),
        correct="1", **{"from": "2026-10-18"}),
    row("q-event", "quiz", "both", ("Is {event} today?", "Yes|No", "", "", ""), ("¿Es hoy {event}?", "Sí|No", "", "", ""), correct="1"),
    row("q-en-only", "quiz", "gv", ("English only?", "Yes|No", "", "", ""), None, correct="1",
        source="https://www.youtube.com/watch?v=abc123"),
    row("q-off", "quiz", "gv", ("Switched off?", "Yes|No", "", "", ""), ("¿Apagada?", "Sí|No", "", "", ""), correct="1", on="no"),
    row("fact-one", "fact", "both", ("A fact.", "", "", "", ""), ("Un dato.", "", "", "", "")),
    row("scr-one", "scramble", "gv", ("Unscramble it", "", "grapevine", "", ""), ("Ordénala", "", "vina", "", "")),
]


# rows that belong to the table (the committee's own four, shortened) and the committee's web switch
VOICE_ROWS = [
    # quiz-service-1960-informative: "this table" / "esta mesa", in both languages
    row("q-this-table", "quiz", "both", ("What attitude did the Conference ask for?", "Informative|Hard sell", "",
                                         "That's why this table shares information.", ""),
        ("¿Qué actitud pidió la Conferencia?", "Informativa|De venta", "", "Por eso esta mesa comparte información.", ""),
        correct="1"),
    # truefalse-service-1978-table: "Like this one!" / "¡Como esta!"
    row("tf-like-this", "truefalse", "gv",
        ("Grapevine tables go back to 1978.", "", "", "True. At all assemblies. Like this one!", ""),
        ("Las mesas de Grapevine vienen de 1978.", "", "", "Verdadero. En todas las asambleas. ¡Como esta!", ""),
        correct="true"),
    # only the Spanish words speak as the table (quiz-gvhist-who-writes): the row stays at the booth on both pages
    row("q-ask-es", "quiz", "lv",
        ("Who writes La Viña?", "Members|Journalists", "", "Members do. See the Share your story page.", ""),
        ("¿Quién escribe La Viña?", "Miembros|Periodistas", "", "Los miembros. ¡Pregúntanos cómo enviar tu historia!", ""),
        correct="1"),
    # only the English words do (quiz-write-five-months)
    row("fill-ask-en", "fill", "gv",
        ("Stories are picked about five ___ ahead.", "", "months", "Ask us for the current themes.", ""),
        ("Las historias se eligen unos cinco ___ antes.", "", "meses", "Los temas actuales están en nuestra página.", "")),
    # nothing in its words, but the committee keeps it at the booth: web = no
    row("q-web-no", "quiz", "both", ("A question for the table?", "Yes|No", "", "", ""),
        ("¿Una pregunta para la mesa?", "Sí|No", "", "", ""), correct="1", web="no"),
    row("q-web-yes", "quiz", "both", ("On the website too?", "Yes|No", "", "", ""),
        ("¿También en el sitio?", "Sí|No", "", "", ""), correct="1", web="Yes"),
    # a table that is not the booth's (quiz-service-photos-online): stays
    row("q-photos", "quiz", "both",
        ("Which photos fit?", "Faces, with no names|Photos of the table or room, with no one in them", "", "", ""),
        ("¿Qué fotos sirven?", "Caras, sin nombres|Fotos de la mesa o del salón, sin personas", "", "", ""),
        correct="2"),
]


def fixture_csv(rows: list[dict] | None = None) -> str:
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in ROWS if rows is None else rows:
        w.writerow(r)
    return out.getvalue()


# loadBooth on the fixture (its text, no file), then dailyQuestions; input: { csv, site, calls: [{ lang, now, per }] }
DAILY_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const booth = B.loadBooth({ csvText: input.csv, driveData: null, manifestData: null, config: {}, site: input.site });
out({ problems: booth.csv.problems, defaults: [B.DAILY_DAYS, B.DAILY_PER],
      runs: input.calls.map((c) => B.dailyQuestions(booth, c.lang, { now: new Date(c.now), per: c.per, csvText: input.csv, site: input.site })) });
"""

# the committee's real CSV (content/booth/booth.csv, as src/_data/booth.js reads it)
REAL_JS = r"""
import vm from "node:vm";
const B = await imp("eleventy/filters/booth.js");
const booth = B.loadBooth({ csv: "content/booth/booth.csv", driveData: null, manifestData: null, config: {}, site: input.site });
const G = B.boothCore();
const byId = Object.fromEntries(booth.csv.items.map((it) => [it.id, it]));
const runs = {};
for (const lang of ["en", "es"]) runs[lang] = input.nows.map((now) => B.dailyQuestions(booth, lang, { now: new Date(now), site: input.site }));
out({ runs, playable: Object.fromEntries(["en", "es"].map((l) => [l, runs[l].every((r) => Object.keys(r.items).every((id) => G.playable(byId[id], l)))])),
      pubs: Object.fromEntries(booth.csv.items.map((it) => [it.id, it.pub])) });
"""

# the same, with every row a day may use (per: 1000 — on /es/ the day's La Viña question and all the rest)
REAL_ALL_JS = r"""
const B = await imp("eleventy/filters/booth.js");
const booth = B.loadBooth({ csv: "content/booth/booth.csv", driveData: null, manifestData: null, config: {}, site: input.site });
const runs = {};
for (const lang of ["en", "es"]) runs[lang] = input.nows.map((now) => ({
  week: B.dailyQuestions(booth, lang, { now: new Date(now), site: input.site }),
  all: B.dailyQuestions(booth, lang, { now: new Date(now), site: input.site, per: 1000 }) }));
out(runs);
"""


class DailyQuestionsBuild(unittest.TestCase):
    def daily(self, calls):
        r = run_js(self, DAILY_JS, data={"csv": fixture_csv(), "site": SITE, "calls": calls}, now=NOW)
        self.assertEqual(r["problems"], [], "the fixture is a good CSV")
        return r

    def test_the_build_day_and_the_shape(self):
        r = self.daily([{"lang": "en", "now": NOW}, {"lang": "es", "now": NOW}])
        self.assertEqual(r["defaults"], [7, 4])
        for d in r["runs"]:
            self.assertEqual(d["from"], "2026-10-15", "the build's day in Central time, not UTC's 16th")
            self.assertEqual(len(d["days"]), 7)
            for ids in d["days"]:
                self.assertEqual(len(ids), 4)
                self.assertEqual(len(set(ids)), 4, "never the same question twice in a day")
            used = {i for ids in d["days"] for i in ids}
            self.assertEqual(set(d["items"]), used, "only the questions the days use")
            for it in d["items"].values():
                self.assertEqual(set(it), {"type", "pub", "text", "choices", "correct", "answer", "explain", "credit", "source",
                                           "from", "until"})
                self.assertIn(it["type"], ("quiz", "truefalse", "fill"))

    def test_which_rows_and_their_dates(self):
        r = self.daily([{"lang": "en", "now": NOW, "per": 20}, {"lang": "es", "now": NOW, "per": 20}])
        en, es = r["runs"]
        day = {d: set(ids) for d, ids in zip(("15", "16", "17", "18", "19", "20", "21"), en["days"])}
        self.assertIn("tf-until", day["15"])
        self.assertIn("tf-until", day["16"], "until is the last day it shows")
        self.assertNotIn("tf-until", day["17"])
        self.assertNotIn("q-from", day["17"])
        self.assertIn("q-from", day["18"], "from is the first day it shows")
        every = set().union(*day.values())
        for gone in ("q-event", "q-off", "fact-one", "scr-one"):
            self.assertNotIn(gone, every)
        self.assertIn("q-en-only", every)
        self.assertNotIn("q-en-only", {i for ids in es["days"] for i in ids}, "no Spanish words: not on /es/")
        self.assertEqual(day["17"], {"q-gv-one", "q-lv-one", "q-lv-two", "tf-both", "fill-gv", "q-en-only"})
        # each question carries its dates: a page kept past its last day still leaves out a row that is over
        self.assertEqual((en["items"]["tf-until"]["from"], en["items"]["tf-until"]["until"]), (None, "2026-10-16"))
        self.assertEqual((en["items"]["q-from"]["from"], en["items"]["q-from"]["until"]), ("2026-10-18", None))
        self.assertEqual((en["items"]["q-gv-one"]["from"], en["items"]["q-gv-one"]["until"]), (None, None))

    def test_la_vina_first_on_spanish_pages(self):
        r = self.daily([{"lang": "es", "now": NOW}])
        es = r["runs"][0]
        for ids in es["days"]:
            self.assertEqual(es["items"][ids[0]]["pub"], "lv")
        # both La Viña questions take turns as the day's own
        self.assertEqual({ids[0] for ids in es["days"]}, {"q-lv-one", "q-lv-two"})

    def test_the_words_of_the_page_language_and_safe_sources(self):
        r = self.daily([{"lang": "en", "now": NOW, "per": 20}, {"lang": "es", "now": NOW, "per": 20}])
        en, es = r["runs"]
        self.assertEqual(en["items"]["q-gv-one"]["text"], "When did Grapevine start?")
        self.assertEqual(es["items"]["q-gv-one"]["text"], "¿Cuándo empezó Grapevine?")
        self.assertEqual(en["items"]["q-gv-one"]["choices"], ["1944", "1960", "1975"])
        self.assertEqual(en["items"]["q-gv-one"]["correct"], 0, "the 1-based CSV number → the 0-based index")
        self.assertEqual(en["items"]["q-lv-two"]["correct"], 1)
        self.assertEqual(es["items"]["q-lv-two"]["choices"], ["Cada mes", "Cada dos meses"])
        self.assertIs(en["items"]["tf-both"]["correct"], True)
        self.assertEqual(en["items"]["tf-both"]["choices"], [])
        self.assertEqual((es["items"]["fill-gv"]["answer"], es["items"]["fill-gv"]["correct"]), ("reunión", None))
        self.assertEqual(en["items"]["q-gv-one"]["source"], "https://www.aagrapevine.org/history")
        self.assertIsNone(en["items"]["q-lv-one"]["source"], "a source on another site is never linked")
        self.assertEqual(en["items"]["q-lv-one"]["credit"], "Source: aalavina.org")
        self.assertEqual(en["items"]["tf-both"]["source"], "https://www.aa.org/")
        # the booth may play from YouTube and the podcast's host, but a "Source" link never leads there: any channel
        # or show could be behind it
        self.assertIsNone(en["items"]["q-en-only"]["source"], "never a link to YouTube")
        self.assertIsNone(es["items"]["fill-gv"]["source"], "never a link to the podcast's host")

    def test_a_day_depends_on_the_day_alone(self):
        # tomorrow's build shows, for tomorrow, what today's build says for tomorrow: a day's questions come from the
        # rows of that day (on, in their dates) and the day's number, whatever day the site was built
        r = self.daily([{"lang": l, "now": n} for l in ("en", "es") for n in ("2026-10-14T17:00:00Z", "2026-10-15T17:00:00Z")])
        for a, b in ((r["runs"][0], r["runs"][1]), (r["runs"][2], r["runs"][3])):
            self.assertEqual(a["days"][1:], b["days"][:-1])

    def test_clock_sweep(self):
        # the build's day at the clock changes (November 1, 2026 and March 14, 2027) and at New Year, in Central time
        cases = {"2026-11-01T05:59:00Z": "2026-11-01", "2026-11-01T06:30:00Z": "2026-11-01", "2026-11-01T07:30:00Z": "2026-11-01",
                 "2026-11-02T05:59:00Z": "2026-11-01", "2026-11-02T06:00:00Z": "2026-11-02",
                 "2027-01-01T05:59:00Z": "2026-12-31", "2027-01-01T06:00:00Z": "2027-01-01",
                 "2027-03-14T07:59:00Z": "2027-03-14", "2027-03-14T08:00:00Z": "2027-03-14",
                 "2027-03-15T04:59:00Z": "2027-03-14", "2027-03-15T05:00:00Z": "2027-03-15"}
        r = self.daily([{"lang": "en", "now": n} for n in cases])
        for (now, day), d in zip(cases.items(), r["runs"]):
            with self.subTest(now=now):
                self.assertEqual(d["from"], day)
                self.assertEqual(len(d["days"]), 7)
                self.assertTrue(all(len(ids) == 4 for ids in d["days"]))


class DailyQuestionsBoothVoice(unittest.TestCase):
    """A row that speaks as the booth's table ("this table", "Like this one!", "Ask us", "esta mesa", "¡Como esta!",
    "Pregúntanos" — in either language) or whose web column says no stays at the booth: the question of the day on
    About and /gvr/ never carries it (booth.js boothOnly, BOOTH_VOICE). A table that is not the booth's stays."""

    def test_rows_that_speak_as_the_table_stay_at_the_booth(self):
        calls = [{"lang": lang, "now": NOW, "per": 40} for lang in ("en", "es")]
        r = run_js(self, DAILY_JS, data={"csv": fixture_csv(ROWS + VOICE_ROWS), "site": SITE, "calls": calls}, now=NOW)
        self.assertEqual(r["problems"], [], "the fixture is a good CSV (web: yes / no)")
        for lang, d in zip(("en", "es"), r["runs"]):
            with self.subTest(lang=lang):
                used = {i for ids in d["days"] for i in ids}
                for gone in ("q-this-table", "tf-like-this", "q-ask-es", "fill-ask-en", "q-web-no", "q-event"):
                    self.assertNotIn(gone, used)
                self.assertLessEqual({"q-web-yes", "q-photos", "q-gv-one", "tf-both"}, used)
                for qid, it in d["items"].items():
                    self.assertIsNone(TABLE_TALK.search(card_words(it)), qid)

    def test_the_pattern(self):
        said = ["That's why this table shares information and experience.", "…at all assemblies. Like this one!",
                "Ask us how to send yours!", "Ask us for the current themes and deadlines.", "Stop by our table.",
                "Ask one of us at the booth.", "Por eso esta mesa comparte información.", "¡Como esta!",
                "¡Pregúntanos cómo enviar tu historia!", "Pregúntanos por los temas.", "Pregúntenos en nuestra mesa.",
                "PREGÚNTANOS", "this\ntable"]
        not_said = ["Photos of the table or room, with no one in them", "Fotos de la mesa o del salón, sin personas",
                    "¿Cómo está tu grupo?", "Ask your sponsor.", "Unlike this one, it is free.", "A task useful to us.",
                    "Los miembros preguntan.", "It comes this one time a year.", "Ask questions at your group."]
        r = run_js(self, """
            const B = await imp("eleventy/filters/booth.js");
            const words = (s) => ({ text: "Q?", choices: ["a", "b"], answer: null, explain: s, credit: null, title: null });
            out({ voice: input.map((s) => B.BOOTH_VOICE.test(s)),
                  en: input.map((s) => B.boothOnly({ en: words(s), es: words("Bien.") }, "es")),
                  es: input.map((s) => B.boothOnly({ en: words("Fine."), es: words(s) }, "en")),
                  event: [B.boothOnly({ en: words("At {event}."), es: words("En {event}.") }, "en"),
                          B.boothOnly({ en: words("At {event}."), es: null }, "es")] });
        """, data=said + not_said)
        expect = [True] * len(said) + [False] * len(not_said)
        for key in ("voice", "en", "es"):
            self.assertEqual(dict(zip(said + not_said, r[key])), dict(zip(said + not_said, expect)), key)
        # {event}: in the page language's words only, as before
        self.assertEqual(r["event"], [True, False])


class DailyQuestionsRealCsv(unittest.TestCase):
    """The committee's own booth.csv: what the About and /gvr/ pages carry."""

    def test_the_real_rows(self):
        nows = ["2026-10-15T17:00:00Z", "2026-10-16T17:00:00Z", "2026-10-31T17:00:00Z", "2026-11-01T17:00:00Z",
                "2026-12-31T17:00:00Z", "2027-01-01T17:00:00Z"]
        r = run_js(self, REAL_JS, data={"site": SITE, "nows": nows}, now=nows[0])
        self.assertEqual(r["playable"], {"en": True, "es": True}, "every question can be answered in its page's language")
        aa = {"www.aa.org", "aa.org", "www.aagrapevine.org", "aagrapevine.org", "www.aalavina.org", "aalavina.org",
              "neta65.org", "www.neta65.org", "neta65.github.io"}
        for lang, runs in r["runs"].items():
            for i, d in enumerate(runs):
                with self.subTest(lang=lang, now=nows[i]):
                    self.assertEqual(len(d["days"]), 7)
                    for ids in d["days"]:
                        self.assertEqual(len(ids), 4)
                        self.assertEqual(len(set(ids)), 4)
                        if lang == "es":
                            self.assertEqual(r["pubs"][ids[0]], "lv", "La Viña first on /es/")
                    self.assertLess(len(json.dumps(d, ensure_ascii=False)), 20000, "a few KB, never the booth file")
                    for it in d["items"].values():
                        if it["source"]:
                            self.assertIn(re.match(r"https://([^/]+)", it["source"]).group(1), aa)
                        self.assertNotIn("{", it["text"] + it["explain"] + it["credit"])
                    if i % 2 == 1:                             # (the times come in pairs of consecutive days)
                        self.assertEqual(runs[i - 1]["days"][1:], d["days"][:-1], "the next day's build agrees")

    def test_no_words_meant_for_the_table(self):
        """The real rows that speak as the booth's table ("Like this one!", "this table", "Ask us", "esta mesa",
        "Pregúntanos" …) stay at the booth: no row a day may use says them, in either language — and what is left
        still fills a week of 4 a day, with no question twice, on the English pages and on the Spanish ones."""
        nows = ["2026-10-15T17:00:00Z", "2026-10-20T17:00:00Z", "2026-11-05T17:00:00Z", "2026-12-31T17:00:00Z",
                "2027-03-01T17:00:00Z", "2027-06-30T17:00:00Z"]
        r = run_js(self, REAL_ALL_JS, data={"site": SITE, "nows": nows}, now=nows[0])
        for lang, runs in r.items():
            for now, d in zip(nows, runs):
                with self.subTest(lang=lang, now=now):
                    for qid, it in {**d["all"]["items"], **d["week"]["items"]}.items():
                        self.assertIsNone(TABLE_TALK.search(card_words(it)), f"{qid}: words meant for the booth's table")
                    week = [i for ids in d["week"]["days"] for i in ids]
                    self.assertEqual((len(d["week"]["days"]), len(week)), (7, 28), "7 days × 4 questions")
                    self.assertEqual(len(set(week)), 28, "no question twice in the week")
                    for ids in d["all"]["days"]:
                        self.assertGreaterEqual(len(ids), 28, "every day, enough rows for a week of 4 a day")


# read.js in a pretend page (window = the vm's global) with its own clock: "alpine:init" registers the components
COMPONENT_JS = r"""
import vm from "node:vm";
let AT = Date.parse(input.now);
const RealDate = Date;
class FakeDate extends RealDate {
  constructor(...a) { if (a.length) super(...a); else super(AT); }
  static now() { return AT; }
}
const reg = {}, on = {}, focus = [];
const listen = (where) => (type, fn) => { (on[where + ":" + type] = on[where + ":" + type] || []).push(fn); };
const attrs = { "data-print": null };
const ctx = vm.createContext({
  console, Date: FakeDate, setTimeout: (f) => f(), clearTimeout() {}, setInterval() {}, clearInterval() {},
  requestAnimationFrame: (f) => f(),
  document: {
    readyState: "loading", addEventListener: listen("doc"), visibilityState: "visible", querySelectorAll: () => [],
    documentElement: { getAttribute: (k) => attrs[k] ?? null, setAttribute: (k, v) => { attrs[k] = String(v); }, removeAttribute: (k) => { attrs[k] = null; } },
  },
  navigator: {}, localStorage: { getItem: () => { throw new Error("no storage expected"); }, setItem: () => { throw new Error("no storage expected"); } },
  addEventListener: listen("win"),
  print: () => { attrs.printed = attrs["data-print"]; },
});
vm.runInContext("var window = globalThis; window.SITE = { tz: 'America/Chicago' }; window.GV = { copy: function (t) { window.__copied = t; } };" +
  "window.Alpine = { data: function (n, f) { window.__reg[n] = f; } };", Object.assign(ctx, { __reg: reg }));
vm.runInContext(fs.readFileSync("src/assets/js/read.js", "utf8"), ctx, { filename: "read.js" });
(on["doc:alpine:init"] || []).forEach((f) => f());
// the card: its JSON and its words (data-t-*), and the elements focusOn() looks for
const shown = { ".read-dyk-fb": true, ".read-dyk-q": true };
const card = (json) => ({
  querySelector: (sel) => sel === "script[data-dyk]" ? { textContent: json }
    : { getClientRects: () => (shown[sel] ? [1] : []), focus: () => focus.push(sel) },
  getAttribute: (k) => ({ "data-t-true": "True", "data-t-false": "False", "data-t-gv": "Grapevine", "data-t-lv": "La Viña",
                          "data-t-both": "Grapevine · La Viña", "data-t-source": "Source" })[k] ?? null,
});
const question = (json, now) => {
  AT = Date.parse(now);
  const C = reg.dailyQuestion();
  C.$el = card(json);
  C.$nextTick = (f) => f();
  C.init();
  return C;
};
"""

DATA = {"from": "2026-10-15",
        "days": [["a", "b"], ["c", "d", "e", "f"], ["g"]],
        "items": {
            "a": {"type": "quiz", "pub": "gv", "text": "A?", "choices": ["x", "y", "z"], "correct": 2, "answer": "", "explain": "Z.", "credit": "", "source": None},
            "b": {"type": "fill", "pub": "both", "text": "B ___", "choices": [], "correct": None, "answer": "bee", "explain": "", "credit": "", "source": None},
            "c": {"type": "truefalse", "pub": "lv", "text": "C.", "choices": [], "correct": False, "answer": "", "explain": "", "credit": "", "source": None},
            "d": {"type": "truefalse", "pub": "gv", "text": "D.", "choices": [], "correct": True, "answer": "", "explain": "", "credit": "", "source": None},
            "e": {"type": "quiz", "pub": "both", "text": "E?", "choices": ["1", "2"], "correct": 0, "answer": "", "explain": "", "credit": "", "source": None},
            "f": {"type": "quiz", "pub": "lv", "text": "F?", "choices": ["1", "2"], "correct": 1, "answer": "", "explain": "", "credit": "", "source": None},
            "g": {"type": "quiz", "pub": "gv", "text": "G?", "choices": ["1", "2"], "correct": 1, "answer": "", "explain": "", "credit": "", "source": None},
        }}


class DailyQuestionsBrowser(unittest.TestCase):
    def run_component(self, script: str, data: dict | None = None):
        return run_js(self, COMPONENT_JS + script, data={"now": "2026-10-15T17:00:00Z", "json": json.dumps(data or DATA)},
                      needs_modules=False)

    def test_the_day_is_the_visitors_central_day(self):
        r = self.run_component(r"""
          const day = (now) => question(input.json, now).list.map((it) => it.text);
          out({
            build: day("2026-10-15T17:00:00Z"),
            lateNight: day("2026-10-16T04:30:00Z"),          // 11:30 PM on the 15th in Central time
            next: day("2026-10-16T05:30:00Z"),               // 12:30 AM on the 16th
            twoLater: day("2026-10-17T17:00:00Z"),
            pastTheEnd: day("2026-10-19T17:00:00Z"),         // day 4 of 3: round again → day 1
            before: day("2026-10-10T17:00:00Z"),
            broken: question("{not json", "2026-10-15T17:00:00Z").list.length,
            empty: question("null", "2026-10-15T17:00:00Z").list.length,
            noDays: question(JSON.stringify({ from: "2026-10-15", days: [], items: {} }), "2026-10-15T17:00:00Z").list.length,
          });""")
        self.assertEqual(r["build"], ["A?", "B ___"])
        self.assertEqual(r["lateNight"], ["A?", "B ___"])
        self.assertEqual(r["next"], ["C.", "D.", "E?", "F?"])
        self.assertEqual(r["twoLater"], ["G?"])
        self.assertEqual(r["pastTheEnd"], ["C.", "D.", "E?", "F?"])
        self.assertEqual(r["before"], ["A?", "B ___"])
        self.assertEqual((r["broken"], r["empty"], r["noDays"]), (0, 0, 0))

    def test_a_kept_page_leaves_out_rows_outside_their_dates(self):
        # a page saved for offline use and opened more than its days later goes round its days again: a day's list
        # was made for an earlier day, so a row whose until is over (an event's question) must not come back
        kept = {"from": "2026-10-15",
                "days": [["a", "b"], ["c", "d"]],
                "items": {
                    "a": {"type": "quiz", "pub": "gv", "text": "A?", "choices": ["x", "y"], "correct": 0, "answer": "", "explain": "", "credit": "", "source": None, "from": None, "until": None},
                    "b": {"type": "quiz", "pub": "gv", "text": "B?", "choices": ["x", "y"], "correct": 0, "answer": "", "explain": "", "credit": "", "source": None, "from": "2026-10-15", "until": None},
                    "c": {"type": "quiz", "pub": "gv", "text": "C?", "choices": ["x", "y"], "correct": 0, "answer": "", "explain": "", "credit": "", "source": None, "from": None, "until": "2026-10-16"},
                    "d": {"type": "quiz", "pub": "gv", "text": "D?", "choices": ["x", "y"], "correct": 0, "answer": "", "explain": "", "credit": "", "source": None, "from": None, "until": "2026-10-20"},
                }}
        r = self.run_component(r"""
          const day = (now) => question(input.json, now).list.map((it) => it.text);
          out({
            build: day("2026-10-15T17:00:00Z"),
            untilDay: day("2026-10-16T17:00:00Z"),       // its until: the last day it shows
            lateNight: day("2026-10-17T04:30:00Z"),      // 11:30 PM on the 16th in Central time: still its day
            roundAgain: day("2026-10-18T17:00:00Z"),     // day 4 of 2 → the second day's list, but c is over
            allOver: day("2026-10-22T17:00:00Z"),        // the second day's list again: c and d are over, no card
            before: day("2026-10-14T17:00:00Z"),         // a clock before the build: the first day, b not begun
          });""", kept)
        self.assertEqual(r["build"], ["A?", "B?"])
        self.assertEqual(r["untilDay"], ["C?", "D?"])
        self.assertEqual(r["lateNight"], ["C?", "D?"])
        self.assertEqual(r["roundAgain"], ["D?"])
        self.assertEqual(r["allOver"], [])
        self.assertEqual(r["before"], ["A?"])

    def test_answers_and_another_question(self):
        r = self.run_component(r"""
          const C = question(input.json, "2026-10-16T17:00:00Z");      // c, d, e, f
          const steps = [];
          const look = () => ({ text: C.cur().text, options: C.options(), shown: C.shown, more: C.more(), pub: C.pubName(), cls: C.pubClass() });
          steps.push(look());
          C.another(); steps.push({ blocked: C.cur().text });          // not before an answer
          C.answer(1); steps.push(Object.assign(look(), { right: C.isRight(1), wrong0: C.isRight(0) }));   // "False": right
          C.answer(0); steps.push({ picked: C.picked });              // a second answer changes nothing
          C.another(); steps.push(look());
          C.answer(1); steps.push({ right: C.isRight(C.picked), rightIs: C.isRight(0) });   // "True" was right
          C.another(); C.answer(0); steps.push({ text: C.cur().text, right: C.isRight(0) });
          C.another(); C.answer(0); steps.push({ text: C.cur().text, right: C.isRight(0), more: C.more() });
          C.another(); steps.push({ text: C.cur().text, i: C.i });     // no further than the day's last
          const F = question(input.json, "2026-10-15T17:00:00Z");      // a, b
          F.answer(2); F.another();
          const fill = { type: F.cur().type, options: F.options(), right: F.isRight(null) };
          F.reveal();
          out({ steps, focus, fill: Object.assign(fill, { shown: F.shown, more: F.more() }) });""")
        s = r["steps"]
        self.assertEqual(s[0], {"text": "C.", "options": ["True", "False"], "shown": False, "more": False, "pub": "La Viña", "cls": "badge-lv"})
        self.assertEqual(s[1], {"blocked": "C."})
        self.assertTrue(s[2]["shown"] and s[2]["right"] and s[2]["more"])
        self.assertFalse(s[2]["wrong0"])
        self.assertEqual(s[3], {"picked": 1})
        self.assertEqual((s[4]["text"], s[4]["shown"], s[4]["pub"], s[4]["cls"]), ("D.", False, "Grapevine", "badge-gv"))
        self.assertEqual(s[5], {"right": False, "rightIs": True})
        self.assertEqual(s[6], {"text": "E?", "right": True})
        self.assertEqual(s[7], {"text": "F?", "right": False, "more": False})
        self.assertEqual(s[8], {"text": "F?", "i": 3})
        # the keyboard: the answer once given, the question after "Another question"
        self.assertEqual(r["focus"][:3], [".read-dyk-fb", ".read-dyk-q", ".read-dyk-fb"])   # (a second answer moves nothing)
        self.assertEqual(r["fill"], {"type": "fill", "options": [], "right": False, "shown": True, "more": False})

    def test_pass_it_on_copy_and_print(self):
        r = self.run_component(r"""
          const P = reg.gvrPass();
          P.$refs = { welcome: { textContent: "  Welcome!\n• one   two\n\n\n\n• three  \n\n  Thanks." } };
          P.init();
          P.copy("welcome");
          P.print("handover");
          const printed = ctx.document.documentElement.getAttribute("data-print");
          (on["win:afterprint"] || []).forEach((f) => f());
          out({ copied: ctx.__copied, printed, after: ctx.document.documentElement.getAttribute("data-print"), canShare: P.canShare,
                missing: P.text("nothing") });""")
        self.assertEqual(r["copied"], "Welcome!\n• one two\n\n• three\n\nThanks.")
        self.assertEqual(r["printed"], "gvr-handover")
        self.assertIsNone(r["after"])
        self.assertFalse(r["canShare"])
        self.assertEqual(r["missing"], "")


class PassItOnPage(unittest.TestCase):
    def setUp(self):
        self.gvr = read("src", "pages", "gvr.njk")
        self.about = read("src", "pages", "about.njk")
        self.i18n = {**json.loads(read("src", "_i18n", "read.json")), **json.loads(read("src", "_i18n", "booth.json"))}

    def test_the_section_and_its_chip(self):
        body = self.gvr.split("-#}", 1)[1]
        nav = re.search(r"ui\.pageNav\(\[(.*?)\], lang\)", body, re.S).group(1)
        hrefs = re.findall(r'href: "([^"]+)"', nav)
        self.assertEqual(hrefs[-3:], ["#ideas", "#pass-it-on", "#next"])
        self.assertLess(body.index('id="ideas"'), body.index('id="pass-it-on"'))
        self.assertLess(body.index('id="pass-it-on"'), body.index('id="next"'))
        sec = body[body.index('id="pass-it-on"'):body.index('id="next"')]
        for key in ("pass_find_t", "pass_welcome_t", "pass_hand_t", "pass_announce", "pass_w_meeting", "pass_print_half"):
            self.assertIn(f"read.gvr.{key}", sec)
        self.assertIn('x-data="gvrPass"', sec)
        self.assertIn("data-gv-meeting", sec, "the welcome's meeting date rolls on in the browser")
        self.assertIn("L.gvr_office_email", sec)
        self.assertIn("L.rlv_office_email", sec)
        # the two printouts: at the end of the page, outside the sections (main > .read-pass-print)
        tail = body[body.rindex("</section>"):]
        self.assertIn('<div class="read-pass-print">', tail)
        self.assertIn('data-sheet="announce"', tail)
        self.assertIn('data-sheet="handover"', tail)
        self.assertIn('cmQrSymbol("gvr-pass-qr")', tail)

    def test_the_question_card_on_both_pages(self):
        for page in (self.gvr, self.about):
            self.assertIn('{% import "macros/question.njk" as question with context %}', page)
            self.assertIn("question.daily(lang", page)
        front = yaml.safe_load(self.about.split("---")[1])
        self.assertIn("/assets/js/read.js", front["pageScripts"])
        self.assertIn("/assets/js/read.js", yaml.safe_load(self.gvr.split("---")[1])["pageScripts"])
        macro = read("src", "_includes", "macros", "question.njk")
        self.assertIn('x-data="dailyQuestion"', macro)
        self.assertIn("data-js-only", macro)
        # its questions move with the clock: they never date the page again in the sitemap (eleventy/lastmod.js)
        self.assertRegex(macro, r'x-data="dailyQuestion"[^>]*data-lastmod="skip"')
        self.assertIn("boothDaily(lang, site)", macro)

    def test_the_words(self):
        keys = [k for k in self.i18n if k.startswith(("read.gvr.pass", "read.gvr.hs_", "read.gvr.nav_pass", "booth.dyk."))]
        self.assertGreater(len(keys), 55)
        classroom = re.compile(r"\b(quiz\w*|lessons?|lecci[oó]n(es)?|training|teach\w*|enseñ\w*|course|curso|class(es)?|clases?|jobs?|pdf)\b", re.I)
        for k in keys:
            with self.subTest(key=k):
                en, es = self.i18n[k]["en"], self.i18n[k]["es"]
                self.assertTrue(en.strip() and es.strip())
                self.assertEqual(set(re.findall(r"\{(\w+)\}", en)), set(re.findall(r"\{(\w+)\}", es)))
                self.assertIsNone(classroom.search(en) or classroom.search(es))
        # the announcement invites; the group conscience decides (Tradition 4)
        self.assertIn("group conscience decides", self.i18n["read.gvr.pass_announce"]["en"])
        self.assertIn("conciencia de grupo decide", self.i18n["read.gvr.pass_announce"]["es"])
        # La Viña first in the Spanish texts that name both magazines
        for k in ("read.gvr.pass_announce", "read.gvr.pass_w_hello", "booth.dyk.sub_about", "booth.dyk.sub_gvr"):
            es = self.i18n[k]["es"]
            self.assertLess(es.index("La Viña"), es.index("Grapevine"), k)

    def test_the_ready_made_emails(self):
        # written from the sender to the office: no hint meant for the rep ("if you have it"), and in Spanish the
        # office is "ustedes" all through (no "tú" after "actualicen")
        for k in ("read.gvr.pass_mail_gvr_body", "read.gvr.pass_mail_rlv_body"):
            en, es = self.i18n[k]["en"], self.i18n[k]["es"]
            self.assertIn("actualicen", es)
            self.assertNotRegex(en, r"\bif you have\b|\byou have it\b")
            self.assertNotRegex(es, r"\b(tienes|tú|tu|puedes|quieres)\b")
            self.assertIn("Group service number (if known):", en)
            self.assertIn("Número de servicio del grupo (si se conoce):", es)
        # the announcement is read to a room: in Spanish it never speaks to one person ("te interesa", "avísanos")
        es = self.i18n["read.gvr.pass_announce"]["es"]
        self.assertNotRegex(es, r"\b(te|quieres|avísanos)\b")
        self.assertIn("Si a alguien le interesa", es)
        # the committee meeting: nothing to register for, said as the rest of the site says it
        for k in ("read.gvr.pass_w_meeting", "read.gvr.pass_w_meeting_rule"):
            self.assertIn("no hace falta registrarse", self.i18n[k]["es"])
            self.assertNotIn("sin registrarse", self.i18n[k]["es"])
            self.assertNotIn("inscrib", self.i18n[k]["es"])

    def test_one_verb_for_no_need_to_register(self):
        """(follow-up to XC-6) "No need to register" has one Spanish verb all over the site's words: "no hace falta
        registrarse" (the Area report, the GVR corner's welcome; the meeting's note, the orientation and the
        committee's reminder say it too) — never "inscribirse"."""
        said: dict[str, list[str]] = {}
        for f in sorted((ROOT / "src" / "_i18n").glob("*.json")):
            for k, v in json.loads(f.read_text(encoding="utf-8")).items():
                es = v.get("es") if isinstance(v, dict) else None
                for m in re.finditer(r"\b(?:no hace falta|no es necesario|no se necesita|sin)\s+(inscrib\w*|registr\w*)",
                                     es if isinstance(es, str) else "", re.I):
                    said.setdefault(m.group(1).lower(), []).append(k)
        self.assertEqual([v for v in said if v.startswith("inscrib")], [], said)
        self.assertLessEqual({"report.c_rule", "read.gvr.pass_w_meeting", "read.gvr.pass_w_meeting_rule"},
                             set(said.get("registrarse", [])), said)


class OfficeAddresses(unittest.TestCase):
    """The office addresses the committee keeps (config/site.yml links): judged by the Code check alone
    (scripts/ops/gate_tests.py CONTENT_TESTS) — the committee may change them (La Viña may name its own)."""

    def test_the_office_addresses(self):
        links = yaml.safe_load(read("config", "site.yml"))["links"]
        for k in ("gvr_office_email", "rlv_office_email"):
            # any e-mail address (an aalavina.org one too), as a mailto: link takes it
            self.assertRegex(links[k], r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$", k)


if __name__ == "__main__":
    unittest.main()
