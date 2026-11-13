"""Round 12, unit u2 (Share your story): the story recorder's topic list, its device check, and Grapevine's
"If Walls Could Talk" in the "Photos & art" card.

  * Topics      — recorder-core.js daysLeft() (the device's own day; the clocks changing on Nov 1; Dec 31 → Jan 1;
                  late at night) and fileName() with a topic (shortened, accents, never twice); read.js recorderTopics()
                  (the coming themes first, soonest first, then the suggested topics; the magazine's own words — La
                  Viña's verbatim on the English page, with the English words and the machine mark beside them —; a
                  theme listed twice comes once; past deadlines left out); the component (recorder.js in Node): the
                  list's value follows the e-mail's Topic, "Another topic" and the visitor's own words, a topic of the
                  other magazine goes when the magazine changes, a "Record a story on this topic" link chooses its topic
                  (and says so) and scrolls, never while a take is made; the days left counted with a fixed clock; the
                  topic in the e-mail's subject and, in the Send panel, in the file's name; "Clear details" clears it;
                  a topic typed after the take's file was downloaded or shared never renames it (the file on the
                  device keeps its name: the "Attach …" line, the message, the next download)
  * Check       — recorder-core.js report(): only REPORT's facts, in order, one line each (a value can't add a line),
                  words for codes, the browser's and system's names; never a name, topic or detail given to it;
                  recorder.js diagnose() gives every fact REPORT names and no other, asks for no microphone (the
                  permission is only read), counts the takes, and the e-mail goes to the site's address, sent by the
                  visitor (the whole report copied when it is too long for a mailto: link)
  * Markup      — the partial: the topic list per magazine under the magazine choice (a label, help, "Another topic"),
                  the report's words (#rec-config "d": recReport) all in English and Spanish, the check folded at the
                  bottom; contribute.njk: "Record a story on this topic" on La Viña's suggested topics only (no link on
                  Grapevine's themes, the deadline rows untouched); no word promises publication; the "If Walls Could
                  Talk" links 28px tall with a mouse too (WCAG 2.5.8); one Spanish term for a meeting place
  * Rendered    — Share your story built in memory (both languages, a fixed day) from data of its own (SITE_DATA:
                  FIXTURE, never the day's data/site): #rec-config's topics and words; every topic link's words are in
                  the recorder's La Viña list; the page's lastmod fingerprint is the same the next day and after a deploy
                  (no count of days in the built page; #rec-config data-lastmod="skip:diag"); the "Photos & art" card
                  names "If Walls Could Talk" (in English on the Spanish page), its rules and the three links; La Viña's
                  line never names it
  * RealData    — the day's data/site: La Viña's topics and their links are there (scripts/ops/gate_tests.py
                  DATA_TESTS: the Code check runs it, the publish gate does not)
No test depends on today's date (the clock is fixed). Skipped without Node.js (the rendered page: without node_modules).

    python -m unittest tests.test_r12_u2_contribute -v
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from html import unescape
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_recorder_core import LOAD  # noqa: E402
from test_recorder_page import COMPONENT_JS, config_like_the_partial, partial, strip_js_comments  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "pages" / "contribute.njk"
PARTIAL = ROOT / "src" / "_includes" / "partials" / "story-recorder.njk"
APP = ROOT / "src" / "assets" / "js" / "recorder.js"
CORE = ROOT / "src" / "assets" / "js" / "recorder-core.js"
COMMUNITY = ROOT / "src" / "_i18n" / "community.json"
READ = ROOT / "src" / "_i18n" / "read.json"
NOW = "2026-10-15T15:00:00Z"          # 10:00 in Dallas (Central daylight time)
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")


def strings() -> dict:
    s = json.loads(read(COMMUNITY))
    s.update(json.loads(read(READ)))
    return s


def report_words() -> list[str]:
    """The partial's recReport list: the report's words #rec-config carries as "d"."""
    m = re.search(r"\{%-?\s*set recReport = \[(.*?)\]\s*-?%\}", read(PARTIAL), re.S)
    return re.findall(r'"(\w+)"', m.group(1))


def words_for(lang: str) -> dict:
    s = strings()
    return {k: s["community.recorder.rep_" + k][lang] for k in report_words()}


def core(case, js: str, data=None, **kw):
    return run_js(case, LOAD + js, data=data, needs_modules=False, **kw)


def topics_fixture() -> dict:
    """#rec-config topics as read.js recorderTopics() makes them (Grapevine: two themes; La Viña: a theme and two topics,
    in Spanish, with their English words on the English page)."""
    return {
        "gv": [{"i": 0, "t": "Emotional Sobriety", "l": "en", "g": "", "m": False, "d": "2026-11-01", "dated": True},
               {"i": 1, "t": "Annual Prison Issue", "l": "en", "g": "", "m": False, "d": "2026-12-01", "dated": True}],
        "lv": [{"i": 0, "t": "Recaídas", "l": "es", "g": "Relapses", "m": False, "d": "2026-10-17", "dated": True},
               {"i": 1, "t": "Mi Primer Paso", "l": "es", "g": "My First Step", "m": True, "d": "", "dated": False},
               {"i": 2, "t": "Una reparación de Noveno Paso que cambió mi vida", "l": "es", "g": "", "m": False, "d": "",
                "dated": False}],
    }


def config(lang: str = "en") -> dict:
    cfg = config_like_the_partial(lang)
    cfg["topics"] = topics_fixture()
    cfg["diag"] = {"to": "committee@example.org", "ver": "abc1234567"}
    cfg["d"] = words_for(lang)
    s = strings()
    for k in ("tp_days", "tp_day1", "tp_today", "tp_closed", "a_topic"):
        cfg["s"][k] = s["community.recorder." + k][lang]
    return cfg


# the component harness of tests/test_recorder_page.py, with the clock fixed (run_js now=…) inside the page too, the
# device's time zone pinned (Central), and what is announced or copied kept
HARNESS = (COMPONENT_JS.replace("const ctx = vm.createContext({\n  console, setTimeout,", "process.env.TZ = \"America/Chicago\";\nconst ctx = vm.createContext({\n  console, Date, setTimeout,")
           + r"""
const said = [], copied = [];
const GVp = vm.runInContext("window.GV", ctx);
GVp.announce = (m) => said.push(m);
GVp.copy = (t) => copied.push(t);
if (C) C.$refs = {};
""")


class Topics(unittest.TestCase):
    def test_days_left_on_the_devices_own_day(self):
        r = core(self, r"""
          const at = (iso) => Date.parse(iso);
          out([
            G.daysLeft("2026-10-17", at("2026-10-15T15:00:00Z")), G.daysLeft("2026-10-15", at("2026-10-15T15:00:00Z")),
            G.daysLeft("2026-10-16", at("2026-10-15T15:00:00Z")), G.daysLeft("2026-10-14", at("2026-10-15T15:00:00Z")),
            G.daysLeft("2026-10-15", at("2026-10-15T04:30:00Z")),          // 23:30 on Oct 14 in Dallas: tomorrow
            G.daysLeft("2026-11-02", at("2026-10-31T17:00:00Z")),          // across Nov 1 (the clocks go back): still 2
            G.daysLeft("2027-01-01", at("2027-01-01T05:30:00Z")),          // 23:30 on Dec 31 in Dallas: tomorrow
            G.daysLeft("2027-03-15", at("2027-03-13T18:00:00Z")),          // across Mar 14 (the clocks go forward)
            G.daysLeft("2026-10-17T00:00:00Z", at("2026-10-15T15:00:00Z")),// (a time after the day: the day counts)
            G.daysLeft("2026-02-30", at("2026-10-15T15:00:00Z")), G.daysLeft("", at("2026-10-15T15:00:00Z")),
            G.daysLeft("2026-10-17", 0), G.daysLeft(null, null), G.daysLeft("x", "y")]);""")
        self.assertEqual(r, [2, 0, 1, -1, 1, 2, 1, 2, 2, None, None, None, None, None])

    def test_the_file_name_carries_the_topic(self):
        r = core(self, r"""
          const at = Date.parse("2026-10-13T17:00:00Z"), lv = { pub: "lv", n: 2, created: at }, gv = { pub: "gv", n: 1, created: at };
          out([G.fileName(lv, "mp3", "Recaídas"), G.fileName(gv, "wav", "Young & Sober"),
               G.fileName(lv, "mp3", "Una reparación de Noveno Paso que cambió mi vida"),
               G.fileName({ pub: "lv", n: 3, name: "Mi Primer Paso", created: at }, "mp3", "Mi Primer Paso"),
               G.fileName({ pub: "lv", n: 3, name: "Mi Primer Paso (2)", created: at }, "mp3", "Mi Primer Paso"),
               G.fileName({ pub: "lv", n: 3, name: "Mi Primer Paso", created: at }, "mp3", "Mi Pri"),
               G.fileName(lv, "mp3", ""), G.fileName(lv, "mp3", "!!!"), G.fileName(lv, "mp3", { evil: 1 }), G.fileName(lv, "mp3"),
               G.fileName(lv, "mp3", "  ¿Qué me metió en AA?  ")]);""")
        self.assertEqual(r, [
            "la-vina-historia-2026-10-13-recaidas-toma-2.mp3",
            "grapevine-story-2026-10-13-young-sober-take-1.wav",
            "la-vina-historia-2026-10-13-una-reparacion-de-noveno-toma-2.mp3",       # (at most 24 characters of it)
            "la-vina-historia-2026-10-13-mi-primer-paso.mp3",                        # (not twice)
            "la-vina-historia-2026-10-13-mi-primer-paso-2.mp3",
            "la-vina-historia-2026-10-13-mi-pri-mi-primer-paso.mp3",                 # (whole words only)
            "la-vina-historia-2026-10-13-toma-2.mp3", "la-vina-historia-2026-10-13-toma-2.mp3",
            "la-vina-historia-2026-10-13-toma-2.mp3", "la-vina-historia-2026-10-13-toma-2.mp3",
            "la-vina-historia-2026-10-13-que-me-metio-en-aa-toma-2.mp3"])

    def test_the_magazines_topics_from_the_editorial_calendar(self):
        """read.js recorderTopics() over editorialFor()'s view of made-up items, on a fixed day (Oct 15, 2026)."""
        def item(pub, title, deadline=None, evergreen=False, en=None, machine=False, issue=None):
            it = {"id": f"ed:{pub}:{title}", "source": "lavina" if pub == "lv" else "grapevine", "kind": "topic", "url": "https://example.org",
                  "title": title, "lang": "es" if pub == "lv" else "en", "status": "ok", "category": pub,
                  "extra": {"publication": pub, "theme": title, "evergreen": evergreen}}
            if deadline:
                it["extra"]["deadline"] = deadline
            if issue:
                it["extra"]["issue_key"] = issue
            if en:
                it["i18n"] = {"title": {"en": en, "es": title}}
                if machine:
                    it["machine"] = ["en"]
            return it
        items = [
            item("gv", "Sober Seniors", "2027-01-01", issue="2027-08"), item("gv", "Emotional Sobriety", "2026-11-01", issue="2027-06"),
            item("gv", "Fun in Sobriety", "2026-10-01", issue="2027-05"),                      # past: not in the list
            item("lv", "Prisiones", "2026-12-15", en="Prisons", issue="2027-07"), item("lv", "Recaídas", "2026-10-17", en="Relapses", issue="2027-05"),
            item("lv", "Mi Primer Paso", evergreen=True, en="My First Step", machine=True),
            item("lv", "Mi meditación", evergreen=True),
            item("lv", "Recaídas", "2027-10-17", en="Relapses", issue="2028-05"),               # the same theme again: once
        ]
        r = run_js(self, r"""
          const out1 = {};
          for (const lang of ["en", "es"]) {
            const eds = { gv: filters.readEditorial(input.items, "gv", lang), lv: filters.readEditorial(input.items, "lv", lang) };
            out1[lang] = filters.readRecTopics(eds);
          }
          out1.empty = filters.readRecTopics(null);
          out(out1);""", data={"items": items}, now=NOW)
        self.assertEqual(r["empty"], {"gv": [], "lv": []})
        en, es = r["en"], r["es"]
        self.assertEqual([(o["t"], o["d"], o["dated"]) for o in en["gv"]],
                         [("Emotional Sobriety", "2026-11-01", True), ("Sober Seniors", "2027-01-01", True)])
        # no count of days: the device counts them (topicText), so the built page says the same every day (lastmod)
        self.assertEqual([sorted(o) for o in en["gv"] + en["lv"] + es["gv"] + es["lv"]],
                         [["d", "dated", "g", "i", "l", "m", "t"]] * (len(en["gv"]) + len(en["lv"]) + len(es["gv"]) + len(es["lv"])))
        self.assertEqual([o["i"] for o in en["lv"]], [0, 1, 2, 3])
        # La Viña's own words on the English page, its English words beside them (the machine's marked)
        self.assertEqual([(o["t"], o["l"], o["g"], o["m"], o["dated"]) for o in en["lv"]], [
            ("Recaídas", "es", "Relapses", False, True), ("Prisiones", "es", "Prisons", False, True),
            ("Mi meditación", "es", "", False, False), ("Mi Primer Paso", "es", "My First Step", True, False)])
        # …and as they are on the Spanish page
        self.assertEqual([(o["t"], o["l"], o["g"]) for o in es["lv"]],
                         [("Recaídas", "es", ""), ("Prisiones", "es", ""), ("Mi meditación", "es", ""), ("Mi Primer Paso", "es", "")])
        self.assertEqual([o["l"] for o in es["gv"]], ["en", "en"])


class Component(unittest.TestCase):
    def run_component(self, js: str, lang: str = "en"):
        return run_js(self, HARNESS + js, data={"cfg": config(lang)}, needs_modules=False, now=NOW)

    def test_the_list_follows_the_emails_topic(self):
        r = self.run_component(r"""
          const steps = [];
          const at = (label) => steps.push([label, C.pub, C.send.topic, C.topicPick("gv"), C.topicPick("lv"), C.topicOther, C.topicGloss(), C.topicMachine()]);
          at("start");
          C.pickTopic("gv", "1"); at("gv theme");
          C.setPub("lv"); at("to La Viña: Grapevine's theme goes");
          C.pickTopic("lv", "1"); at("lv topic");
          C.pickTopic("lv", "other"); at("another topic");
          C.send.topic = "Mi propia historia"; at("own words");
          C.setPub("gv"); at("own words stay");
          C.pickTopic("gv", ""); at("none");
          C.send.topic = "Annual Prison Issue"; at("typed in the e-mail's Topic: the list follows");
          C.send.topic = "Something else"; at("typed: another topic");
          C.clearDetails(); at("cleared");
          C.state = "recording"; C.go("lv", "Recaídas"); at("not while a take is made"); C.state = "idle";
          out({ steps, texts: [C.topicText("lv", 0), C.topicText("lv", 1), C.topicText("gv", 0), C.topicText("gv", 9)], said });""")
        self.assertEqual(r["steps"], [
            ["start", "gv", "", "", "", False, "", False],
            ["gv theme", "gv", "Annual Prison Issue", "1", "other", False, "", False],
            ["to La Viña: Grapevine's theme goes", "lv", "", "", "", False, "", False],
            ["lv topic", "lv", "Mi Primer Paso", "other", "1", False, "My First Step", True],
            ["another topic", "lv", "", "other", "other", True, "", False],
            ["own words", "lv", "Mi propia historia", "other", "other", True, "", False],
            ["own words stay", "gv", "Mi propia historia", "other", "other", True, "", False],
            ["none", "gv", "", "", "", False, "", False],
            ["typed in the e-mail's Topic: the list follows", "gv", "Annual Prison Issue", "1", "other", False, "", False],
            ["typed: another topic", "gv", "Something else", "other", "other", False, "", False],
            ["cleared", "gv", "", "", "", False, "", False],
            ["not while a take is made", "gv", "", "", "", False, "", False],
        ])
        # the days left, counted on the device (Oct 15 in Dallas): the page's words
        self.assertEqual(r["texts"], ["Recaídas · 2 days left", "Mi Primer Paso", "Emotional Sobriety · 17 days left", ""])
        self.assertEqual(r["said"], [])

    def test_the_days_left_words(self):
        r = run_js(self, HARNESS + r"""
          const L = C.topicList("lv");
          const at = (d) => { L[0].d = d; return C.topicText("lv", 0); };
          out([at("2026-10-15"), at("2026-10-16"), at("2026-10-14"), at("2026-10-25"), at("nonsense")]);""",
                   data={"cfg": config("es")}, needs_modules=False, now=NOW)
        self.assertEqual(r, ["Recaídas · hoy es el último día", "Recaídas · queda 1 día", "Recaídas · fecha vencida",
                             "Recaídas · quedan 10 días", "Recaídas"])

    def test_a_topic_link_chooses_its_topic_and_scrolls(self):
        r = self.run_component(r"""
          const click = (attrs) => { let stopped = false;
            (on["doc:click"] || []).forEach((f) => f({ target: { closest: (sel) => sel === "[data-rec-go]" ? { getAttribute: (a) => attrs[a] === undefined ? null : attrs[a] } : null },
                                                      preventDefault: () => { stopped = true; } }));
            return stopped; };
          const a = click({ "data-rec-go": "lv", "data-rec-topic": "  Mi Primer   Paso " });
          const first = { pub: C.pub, topic: C.send.topic, pick: C.topicPick("lv") };
          const b = click({ "data-rec-go": "lv", "data-rec-topic": "Un tema que no está en la lista" });
          const second = { topic: C.send.topic, pick: C.topicPick("lv") };
          await new Promise((res) => setTimeout(res, 80));
          out({ a, b, first, second, said, scrolls: calls.scroll.length, focus: calls.focus.length });""")
        self.assertTrue(r["a"] and r["b"])                         # the link's own jump (a hash change) never happens
        self.assertEqual(r["first"], {"pub": "lv", "topic": "Mi Primer Paso", "pick": "1"})
        self.assertEqual(r["second"], {"topic": "Un tema que no está en la lista", "pick": "other"})   # shown as the visitor's own
        self.assertEqual(r["said"], ["Topic chosen: Mi Primer Paso", "Topic chosen: Un tema que no está en la lista"])
        self.assertEqual(r["scrolls"], 2)
        self.assertEqual(r["focus"], 2)

    def test_the_topic_in_the_email_and_the_files_name(self):
        r = self.run_component(r"""
          const t = take("lv", 3);
          C.takes = [t];
          C.go("lv", "Recaídas");
          C.send.pub = "lv";
          const closed = { file: C.fileName(t, "mp3"), subject: C.subject(t) };
          C.openId = t.id; C.panel = "send";
          const open = { file: C.fileName(t, "mp3"), subject: C.subject(t), body: C.body(t) };
          C.send.pub = "gv";
          const toGv = C.fileName(t, "wav");
          out({ closed, open, toGv });""")
        self.assertEqual(r["closed"]["file"], "la-vina-historia-2026-10-13-toma-3.mp3")     # (only in its Send panel)
        self.assertEqual(r["closed"]["subject"], "Graba tu historia: Recaídas")
        self.assertEqual(r["open"]["file"], "la-vina-historia-2026-10-13-recaidas-toma-3.mp3")
        self.assertIn("Tema: Recaídas", r["open"]["body"])
        self.assertIn("Archivo: la-vina-historia-2026-10-13-recaidas-toma-3.mp3", r["open"]["body"])
        self.assertEqual(r["toGv"], "grapevine-story-2026-10-13-recaidas-take-3.wav")

    def test_a_topic_typed_after_the_file_was_saved_never_renames_it(self):
        """The Send panel lists Download first and "Details for the email" (its Topic) below: a topic typed after the
        download stays in the e-mail's subject and Topic line, while the file's name — the "Attach …" line, the
        message's "Archivo:" line, the next download — stays the one of the file on the device. Shared (Share, Save to
        Files) the same; a share sheet closed without sharing saved nothing."""
        r = self.run_component(r"""
          const t = take("lv", 2), u = take("lv", 3), w = take("gv", 4);
          C.takes = [t, u, w];
          const name = (x, fmt) => C.fileName(x, fmt || "mp3");
          const tick = () => new Promise((res) => setTimeout(res, 0));
          // 1. Download first, then a topic in "Details for the email"
          C.openPanel(t, "send");
          const before = name(t);
          C.downloaded(t);
          C.send.topic = "Recaídas"; C.reprep();
          const after = { file: name(t), attach: C.t("s_attach", { file: name(t) }), body: C.body(t), subject: C.subject(t),
                          wav: name(t, "wav"), said: said.slice() };
          C.closePanel(); C.openPanel(t, "send");
          const reopened = name(t);
          // 2. the topic first (a "Record a story on this topic" link), then Download: the name keeps that topic
          C.clearDetails(); C.go("lv", "Mi Primer Paso");
          C.openPanel(u, "send");
          const u1 = name(u);
          C.downloaded(u);
          C.send.topic = "Otra cosa"; C.reprep();
          const u2 = name(u);
          // 3. Share: closed without sharing — nothing saved, the name follows the topic; shared — it stays
          C.clearDetails(); C.setPub("gv");
          C.openPanel(w, "send");
          C.file = () => ({ name: name(w) }); C.prep = Object.assign({}, C.prep, { ready: true });
          ctx.navigator.share = () => Promise.reject({ name: "AbortError" });
          C.share(w, true); await tick();
          C.send.topic = "Gratitude"; const w1 = name(w);
          ctx.navigator.share = () => Promise.resolve();
          C.share(w, false); await tick(); await tick();
          C.send.topic = "Something else"; const w2 = name(w);
          out({ before, after, reopened, u1, u2, w1, w2, closed: C.fileName(t) === before || C.fileName(t) });""")
        self.assertEqual(r["before"], "la-vina-historia-2026-10-13-toma-2.mp3")
        a = r["after"]
        self.assertEqual(a["file"], "la-vina-historia-2026-10-13-toma-2.mp3", "the file on the device keeps its name")
        self.assertEqual(a["attach"], "Attach the file you saved, la-vina-historia-2026-10-13-toma-2.mp3, before you send it.")
        self.assertIn("Archivo: la-vina-historia-2026-10-13-toma-2.mp3", a["body"])
        self.assertIn("Tema: Recaídas", a["body"])                     # the topic still goes into the e-mail …
        self.assertEqual(a["subject"], "Graba tu historia: Recaídas")   # … and its subject
        self.assertEqual(a["wav"], "la-vina-historia-2026-10-13-toma-2.wav")
        self.assertEqual(a["said"], ["Downloading la-vina-historia-2026-10-13-toma-2.mp3."])
        self.assertEqual(r["reopened"], "la-vina-historia-2026-10-13-toma-2.mp3", "(this page: the panel opened again)")
        self.assertEqual(r["u1"], "la-vina-historia-2026-10-13-mi-primer-paso-toma-3.mp3")
        self.assertEqual(r["u2"], "la-vina-historia-2026-10-13-mi-primer-paso-toma-3.mp3")
        self.assertEqual(r["w1"], "grapevine-story-2026-10-13-gratitude-take-4.mp3", "a share sheet closed: nothing saved")
        self.assertEqual(r["w2"], "grapevine-story-2026-10-13-gratitude-take-4.mp3")
        self.assertIs(r["closed"], True, "outside its Send panel, the name without a topic, as before")


class Check(unittest.TestCase):
    def test_the_report_holds_only_its_facts(self):
        w = words_for("en")
        r = core(self, r"""
          const all = {};
          G.REPORT.forEach((k) => { all[k] = true; });
          const facts = Object.assign({}, all, {
            when: "2026-10-15", page: "en-US · abc", browser: { code: "safari", more: 18 }, system: "ios",
            app: { code: "inapp", more: "Facebook" }, mic: "granted", record: "worklet", mp3: "wait", idb: { code: "failed", more: "QuotaExceededError" },
            keep: "on", persisted: null, priv: "maybe", free: "1.2 GB", used: "", takes: 3, unsaved: 1, unreadable: 0, error: "none",
            ua: "Mozilla/5.0 (iPhone)\nTopic: injected",
            // never in a report:
            name: "Ana López", topic: "Mi secreto", phone: "555-0100", file: "la-vina-historia-mi-secreto.mp3", takeNames: ["Mi toma"],
            constructor: "x", __proto__: { evil: 1 } });
          const text = G.report(facts, input.words);
          const junk = [];
          for (const a of [undefined, null, 1, "x", [], { browser: { code: { nested: 1 } } }])
            for (const b of [undefined, null, 1, "x", [], { title: 5, yes: {} }]) { try { junk.push(typeof G.report(a, b)); } catch (e) { junk.push(e.message); } }
          out({ text, keys: G.REPORT, junk, bare: G.report({ takes: 2, ua: "UA" }, null), none: G.report({}, input.words) });""",
                 data={"words": w})
        lines = r["text"].split("\n")
        self.assertEqual(lines[0], w["title"])
        self.assertEqual(lines[1], "")
        self.assertEqual(len(lines), 2 + len(r["keys"]))                   # one line per fact, nothing else
        labels = [line.split(": ", 1)[0] for line in lines[2:]]
        self.assertEqual(labels, [w["l_" + k] for k in r["keys"]])          # REPORT's order, the page's words
        got = dict(line.split(": ", 1) for line in lines[2:])
        self.assertEqual(got[w["l_browser"]], "Safari 18")
        self.assertEqual(got[w["l_system"]], "iOS")
        self.assertEqual(got[w["l_app"]], w["v_app_inapp"] + " (Facebook)")
        self.assertEqual(got[w["l_mic"]], w["v_mic_granted"])
        self.assertEqual(got[w["l_idb"]], w["v_idb_failed"] + " (QuotaExceededError)")
        self.assertEqual(got[w["l_persisted"]], w["unknown"])
        self.assertEqual(got[w["l_used"]], w["unknown"])
        self.assertEqual(got[w["l_online"]], w["yes"])
        self.assertEqual(got[w["l_takes"]], "3")
        self.assertEqual(got[w["l_unreadable"]], "0")
        self.assertEqual(got[w["l_error"]], w["v_error_none"])
        self.assertEqual(got[w["l_ua"]], "Mozilla/5.0 (iPhone) Topic: injected")   # a value can't start a line of its own
        for secret in ("Ana", "secreto", "555-0100", "Mi toma", "evil", "constructor"):
            self.assertNotIn(secret, r["text"])
        self.assertEqual(r["junk"], ["string"] * 36)                          # never throws
        self.assertEqual(r["bare"], "takes: 2\nua: UA")                       # (no words: the keys)
        self.assertEqual(r["none"], w["title"] + "\n\n")
        # nothing personal can be asked for by name
        self.assertFalse({"name", "topic", "phone", "email", "file", "address", "place", "mics", "label"} & set(r["keys"]))

    def test_diagnose_gives_every_fact_and_no_other(self):
        code = strip_js_comments(read(APP))
        body = code[code.index("diagnose: function () {"):]
        body = body[:body.index("\n        },")]
        given = set(re.findall(r"^\s{12}(\w+): ", body[body.index("var facts = {"):body.index("};", body.index("var facts = {"))], re.M))
        given |= set(re.findall(r"\bfacts\.(\w+) =", body))
        report = re.search(r"var REPORT = \[(.*?)\];", read(CORE), re.S).group(1)
        self.assertEqual(sorted(given), sorted(re.findall(r'"(\w+)"', report)))
        # it asks for nothing: no microphone, no permission prompt, no persist() (a question on some browsers)
        for bad in ("getMic(", "getUserMedia(", "this.open(", "self.open(", ".persist()", "requestPermission", "askPersist("):
            self.assertNotIn(bad, body, bad)
        self.assertIn("navigator.permissions.query({ name: \"microphone\" })", code)
        # the IndexedDB try is a database of its own, deleted after: never the takes'
        self.assertIn('var CHECK_DB = "gvlv-rec-check";', code)
        self.assertNotIn("CHECK_DB", read(CORE))
        check = code[code.index("function storageCheck() {"):code.index("document.addEventListener(\"alpine:init\"")]
        self.assertNotIn("R.DB_NAME", check)
        self.assertIn("indexedDB.deleteDatabase(CHECK_DB)", check)

    def test_the_report_in_the_page(self):
        r = run_js(self, HARNESS + r"""
          let mic = 0;
          ctx.navigator.mediaDevices = { getUserMedia: () => { mic++; return Promise.reject(new Error("asked")); } };
          ctx.navigator.permissions = { query: (q) => Promise.resolve({ state: q && q.name === "microphone" ? "prompt" : "denied" }) };
          ctx.navigator.onLine = true;
          C.takes = [take("lv", 1, { name: "Mi toma secreta" }), take("gv", 2, { saved: false }), take("gv", 3, { damaged: true })];
          C.mics = [{ id: "a", label: "Ana's AirPods" }];
          Object.assign(C.send, { topic: "Mi secreto", name: "Ana López", phone: "555-0100", email: "ana@example.org" });
          C.lastErr = "QuotaExceededError";
          C.checkOpen({ target: { open: false } });
          const closedPanel = C.diag.busy;
          C.checkOpen({ target: { open: true } });
          const busy = C.diag.busy;
          for (let i = 0; i < 100 && C.diag.busy; i++) await new Promise((res) => setTimeout(res, 20));
          const text = C.diag.text;
          const mail = C.checkMail();
          C.checkMailClick();
          C.diag.text = text + "\n" + "x".repeat(2000);
          const long = C.checkMail();
          C.checkMailClick();
          out({ closedPanel, busy, text, mail, long: { cut: long.cut, len: long.href.length, href: long.href }, copied, said, mic, to: C.checkTo() });""",
                   data={"cfg": config("en")}, needs_modules=False, now=NOW)
        w = words_for("en")
        self.assertFalse(r["closedPanel"])                                  # closing the panel checks nothing
        self.assertTrue(r["busy"])
        text = r["text"]
        self.assertTrue(text.startswith(w["title"] + "\n\n"), text[:80])
        got = dict(line.split(": ", 1) for line in text.split("\n")[2:])
        self.assertEqual(got[w["l_when"]], "2026-10-15")
        self.assertEqual(got[w["l_page"]], "en-US · abc1234567")
        self.assertEqual(got[w["l_mic"]], w["v_mic_prompt"])                  # read, never asked
        self.assertEqual(got[w["l_idb"]], w["v_idb_none"])                    # (no IndexedDB here)
        self.assertEqual(got[w["l_takes"]], "3")
        self.assertEqual(got[w["l_unsaved"]], "1")
        self.assertEqual(got[w["l_unreadable"]], "1")
        self.assertEqual(got[w["l_error"]], "QuotaExceededError")
        self.assertEqual(got[w["l_keep"]], w["v_keep_on"])
        self.assertEqual(got[w["l_app"]], w["v_app_tab"])
        self.assertEqual(r["mic"], 0)                                       # the microphone was never asked for
        for secret in ("Mi toma secreta", "Mi secreto", "Ana", "555-0100", "ana@example.org", "AirPods"):
            self.assertNotIn(secret, text)
        self.assertEqual(r["said"], [w["ready"], w["short"]])            # (the long one: copied, and said)
        # the e-mail: to the site's address, the report in it, sent by the visitor; too long — the short message, the
        # whole report copied
        self.assertEqual(r["to"], "committee@example.org")
        self.assertFalse(r["mail"]["cut"])
        self.assertTrue(r["mail"]["href"].startswith("mailto:committee@example.org?subject=Story%20recorder%3A%20device%20check&body="))
        self.assertIn("What%20happened%20(optional)%3A", r["mail"]["href"])
        self.assertTrue(r["long"]["cut"])
        self.assertLessEqual(r["long"]["len"], 1800)
        self.assertEqual(r["copied"], [text + "\n" + "x" * 2000])           # (once: the short one needed no copy)


class Markup(unittest.TestCase):
    def test_the_report_words_in_both_languages(self):
        s = strings()
        keys = report_words()
        self.assertEqual(len(keys), len(set(keys)))
        report = re.findall(r'"(\w+)"', re.search(r"var REPORT = \[(.*?)\];", read(CORE), re.S).group(1))
        # a label for each fact, the words report() and recorder.js ask for, a word for each code diagnose() gives
        need = {"title", "ask", "short", "ready", "yes", "no", "unknown"} | {"l_" + k for k in report}
        need |= {"v_app_tab", "v_app_installed", "v_app_inapp", "v_mic_granted", "v_mic_denied", "v_mic_prompt", "v_keep_on", "v_keep_off",
                 "v_priv_yes", "v_priv_maybe", "v_priv_no", "v_error_none", "v_idb_ok", "v_idb_failed", "v_idb_none",
                 "v_mp3_ready", "v_mp3_wait", "v_mp3_failed", "v_mp3_none"}
        need |= {"v_record_" + k for k in ("worklet", "script", "insecure", "no_media", "no_audio")}
        self.assertEqual(sorted(need - set(keys)), [])
        self.assertEqual(sorted(set(keys) - need), [])
        for k in keys:
            with self.subTest(key=k):
                v = s["community.recorder.rep_" + k]
                self.assertTrue(v["en"].strip() and v["es"].strip())
                self.assertEqual(PLACEHOLDER.findall(v["en"]), PLACEHOLDER.findall(v["es"]))
        self.assertIn('"d": { {%- for k in recReport %}"{{ k }}": {{ ("community.recorder.rep_" + k) | t(lang) | jsonScript | safe }}',
                      read(PARTIAL))
        self.assertRegex(partial(), r'diag: \{ to: site\.contact_email or "", ver: build\.version \}')
        self.assertIn("topics: recTopics", partial())
        self.assertIn("{%- set recTopics = { gv: gvEd, lv: lvEd } | readRecTopics -%}", partial())

    def test_the_topic_list_and_the_check_in_the_partial(self):
        part = partial()
        mag = part.index('<fieldset class="cm-rec-mag"')
        topic = part.index('<div class="cm-rec-topic">')
        deck = part.index('<div class="cm-rec-deck"')
        self.assertLess(mag, topic)
        self.assertLess(topic, deck)                                        # under the magazine choice, before the recorder
        block = part[topic:deck]
        self.assertIn("{% for p in pubOrder %}", block)                      # one list per magazine
        self.assertRegex(block, r'<label class="[^"]*"[^>]*>\s*<span>\{\{ "community\.recorder\.tp_label" \| t\(lang\) \}\}')
        self.assertIn('aria-describedby="rec-topic-help"', block)
        self.assertIn('id="rec-topic-help"', block)
        self.assertIn('<option value="other">{{ "community.recorder.tp_other" | t(lang) }}</option>', block)
        self.assertRegex(block, r'x-model="send\.topic" x-ref="topicOwn"')    # the visitor's own words: the e-mail's Topic
        self.assertIn("('community.recorder.tp_group_' + p + '_' + grp[0]) | t(lang)", block)
        self.assertIn('x-show="topicMachine()">{% icon "languages", "size-3" %}{{ "common.auto_translated" | t(lang) }}', block)
        # the check: folded, last in the recorder, made when it opens
        check = part.index('<details class="cm-rec-check')
        self.assertGreater(check, part.index('{{ "community.recorder.b_delete_all" | t(lang) }}'))
        self.assertLess(check, part.index("</article>"))
        self.assertIn('@toggle="checkOpen($event)"', part)
        self.assertIn(':data-copy="diag.text"', part)
        self.assertIn(':href="checkMail().href" @click="checkMailClick()"', part)
        css = read(ROOT / "src" / "assets" / "css" / "areas" / "community.css")
        self.assertIn('grid-template-areas: "mag" "topic" "deck" "say" "before";', css)
        self.assertIn('grid-template-areas: "mag deck" "topic deck" "say deck" "before deck";', css)
        for k in ("tp_label", "tp_optional", "tp_none", "tp_other", "tp_own", "tp_help", "tp_gv_ideas", "tp_days", "tp_day1", "tp_today",
                  "tp_closed", "a_topic", "tp_group_gv_dated", "tp_group_gv_topics", "tp_group_lv_dated", "tp_group_lv_topics",
                  "chk_title", "chk_intro", "chk_busy", "chk_report", "chk_copy", "chk_mail", "chk_again", "chk_mail_note"):
            with self.subTest(key=k):
                v = strings()["community.recorder." + k]
                self.assertTrue(v["en"].strip() and v["es"].strip())
                self.assertEqual(sorted(PLACEHOLDER.findall(v["en"])), sorted(PLACEHOLDER.findall(v["es"])))

    def test_record_on_this_topic_only_on_la_vinas_topics(self):
        page = read(PAGE)
        chip = page[page.index("{% macro topicChip(r, lang, isLv, cls=\"\") %}"):]
        chip = chip[:chip.index("{% endmacro %}")]
        self.assertIn("{% if isLv %}", chip)
        link = re.search(r"<a\s[^>]*data-rec-topic=[^>]*>", chip).group(0)
        self.assertIn('data-rec-go="lv"', link)
        self.assertIn('data-rec-topic="{{ own }}"', link)
        self.assertIn("{%- set own = r.original or r.theme -%}", chip)   # read.js recorderTopics(): t = original || theme
        self.assertRegex(link, r"\sdata-js-only[\s>]")
        self.assertIn('href="#recorder"', link)
        self.assertIn('"community.rec.topic_here" | t(lang)', chip)
        # nowhere else: not on the deadline rows (theirs to keep as they are), not on Grapevine's
        self.assertEqual(page.count("data-rec-topic"), 1)
        for macro in ("dlRow", "themeList", "submitPanel", "recordCard"):
            body = page[page.index("{% macro " + macro + "("):]
            self.assertNotIn("data-rec-topic", body[:body.index("{% endmacro %}")], macro)
        s = strings()["community.rec.topic_here"]
        self.assertEqual((s["en"], s["es"]), ("Record a story on this topic", "Graba sobre este tema"))

    def test_no_word_promises_publication(self):
        s = strings()
        keys = [k for k in s if re.match(r"community\.recorder\.(tp_|chk_|rep_|a_topic)|community\.rec\.topic_here|read\.contrib\.k_walls", k)]
        self.assertGreater(len(keys), 80)
        promise = {"en": r"(?i)\bwill (be )?(publish|print|air|use)|\bguarantee|\bsure to\b|\bselected\b",
                   "es": r"(?i)se publicar[áa]|publicaremos|publicar[áa]n|garantiz|\bseguro que\b"}
        for k in keys:
            for lang in ("en", "es"):
                with self.subTest(key=k, lang=lang):
                    self.assertNotRegex(s[k][lang], promise[lang])
        # Grapevine's themes are ideas; each magazine chooses
        self.assertIn("ideas", s["community.recorder.tp_gv_ideas"]["en"])
        self.assertIn("Ideas", s["community.recorder.tp_group_gv_dated"]["en"])
        self.assertIn("Ideas", s["community.recorder.tp_group_gv_dated"]["es"])

    def test_la_vina_is_never_said_to_have_a_section_of_that_name(self):
        s = strings()
        for k in ("read.contrib.k_walls_lv", "read.contrib.k_walls_lv_link"):
            for lang in ("en", "es"):
                self.assertNotIn("Walls", s[k][lang])
                self.assertNotIn("{name}", s[k][lang])
        for lang in ("en", "es"):
            self.assertIn("{name}", s["read.contrib.k_walls"][lang])
            self.assertIn("Grapevine", s["read.contrib.k_walls"][lang])

    def test_the_walls_links_are_24px_with_a_mouse_too(self):
        """WCAG 2.5.8: "Grapevine's guidelines" and "Send it on Grapevine's site" stand alone in their row (not in a
        sentence): 20px of text, and tap-link only grows them on phones and touch screens — padding makes them 28px
        with a mouse (flex items of the row: in the narrow card they stack without overlapping)."""
        page = read(PAGE)
        row = re.search(r'<p class="([^"]*)">\s*(<a [^>]*href="\{\{ L\.gv_guidelines \}\}"[^>]*>.*?</a>)\s*'
                        r'(<a [^>]*href="\{\{ L\.gv_share_story \}\}"[^>]*>.*?</a>)\s*</p>', page, re.S)
        self.assertTrue(row, "the walls note's two links, alone in their row")
        self.assertTrue({"flex", "flex-wrap"} <= set(row.group(1).split()), row.group(1))
        for link in (row.group(2), row.group(3)):
            cls = set(re.search(r'class="([^"]*)"', link).group(1).split())
            self.assertTrue({"link", "tap-link", "py-1"} <= cls, cls)

    def test_one_word_for_the_meeting_place(self):
        """The note says "meeting place(s)" in English throughout; in Spanish one term too — "lugar(es) de reunión" —, not a
        "sala" in its title and "salones" in La Viña's line."""
        s = strings()
        for k in ("read.contrib.k_walls_t", "read.contrib.k_walls", "read.contrib.k_walls_lv"):
            with self.subTest(key=k):
                self.assertRegex(s[k]["en"], r"\bmeeting places?\b")
                self.assertRegex(s[k]["es"], r"\blugar(?:es)? de reunión\b")
                self.assertNotRegex(s[k]["es"], r"(?i)\bsala\b|\bsal[oó]n(?:es)?\b")


# Share your story built in memory (Eleventy: only that page, both languages) on a fixed day, from data of its own
# (SITE_DATA: the themes and topics below, written to a folder for the build) — what these tests expect never depends
# on the day's synced data; RealData is the one check of the day's data (scripts/ops/gate_tests.py DATA_TESTS). Each
# page also comes with its lastmod fingerprint (eleventy/lastmod.js), as built and as the next deploy of the code
# would make it (another build.version wherever the page has it).
RENDER_JS = r"""
const os = await import("node:os");
process.env.ONLY = "contribute";
const { Eleventy } = await import("@11ty/eleventy");
const L = await imp("eleventy/lastmod.js");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-r12-u2-"));
try {
  const pages = await new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" }).toJSON();
  const res = { html: {}, fp: {}, deployed: {} };
  for (const [lang, url] of [["en", "/contribute/"], ["es", "/es/contribute/"]]) {
    const html = (pages.find((p) => p.url === url) || {}).content || "";
    const cfg = /<script type="application\/json" id="rec-config"[^>]*>([\s\S]*?)<\/script>/.exec(html);
    const ver = cfg ? JSON.parse(cfg[1]).diag.ver : "";
    res.html[lang] = html;
    res.fp[lang] = L.fingerprint(html);
    res.deployed[lang] = ver ? L.fingerprint(html.split(ver).join(ver === "0123456789" ? "9876543210" : "0123456789")) : "";
  }
  out(res);
} finally { fs.rmSync(dir, { recursive: true, force: true }); }
"""
NEXT_DAY = "2026-10-16T15:00:00Z"     # the next day's build, same hour


def theme(pub: str, title: str, deadline: str | None = None, issue: str = "", en: str = "", machine: bool = False) -> dict:
    """An item of data/site/editorial.json (docs/DATA_SCHEMA.md "editorial.json"): a coming issue's theme (a deadline
    and its issue) or, without them, a suggested topic."""
    lv = pub == "lv"
    extra = {"publication": pub, "theme": title, "evergreen": deadline is None}
    if deadline:
        extra.update(deadline=deadline, issue_key=issue)
    it = {"id": f"ed:{pub}:{issue or 'any'}:" + re.sub(r"\W+", "-", title.lower()).strip("-"), "source": "lavina" if lv else "grapevine",
          "kind": "topic", "url": f"https://example.org/{pub}", "title": title, "summary": "", "lang": "es" if lv else "en",
          "status": "ok", "category": pub, "extra": extra}
    if en:
        it["i18n"] = {"title": {"en": en, "es": title}}
        if machine:
            it["machine"] = ["en"]
    return it


LV_TOPICS = ["Mi Primer Paso", "Una reparación de Noveno Paso que cambió mi vida", "Lo que “Dios” significa para mí & mi grupo"]
FIXTURE = {
    "editorial": {"updated": "2026-10-15T06:00:00Z", "items": [
        theme("gv", "Emotional Sobriety", "2026-11-01", "2027-06"),
        theme("gv", "Sober Seniors", "2027-01-01", "2027-08"),
        theme("gv", "Fun in Sobriety", "2026-10-01", "2027-05"),                  # closed: not in the recorder's list
        theme("lv", "Recaídas", "2026-10-17", "2027-05", en="Relapses"),          # 2 days left on Oct 15, 1 on Oct 16
        theme("lv", "Prisiones", "2026-12-15", "2027-07", en="Prisons"),
        theme("lv", LV_TOPICS[0], en="My First Step", machine=True),
        theme("lv", LV_TOPICS[1]),
        theme("lv", LV_TOPICS[2]),                                                # quotes and "&": escaped in the link
    ]},
    # (read.js reads data/site/spotlight.json itself when db.spotlight is empty: a file of its own, with nothing in it)
    "spotlight": {"updated": "2026-10-15T06:00:00Z", "items": [], "counts": {}},
}


def build_contribute(case: unittest.TestCase, now: str, data: dict | None = FIXTURE) -> dict:
    """RENDER_JS at `now`, from `data` (one file per key, in a folder of its own; None: the day's data/site)."""
    if data is None:
        return run_js(case, RENDER_JS, now=now, timeout=300)
    with tempfile.TemporaryDirectory(prefix="gv-r12-u2-data-") as folder:
        for name, body in data.items():
            Path(folder, name + ".json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return run_js(case, RENDER_JS, now=now, timeout=300, env={"SITE_DATA": folder})


def rec_config(html: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="rec-config" data-lastmod="skip:diag">(.*?)</script>', html, re.S).group(1))


class Rendered(unittest.TestCase):
    built: dict | None = None

    def build(self) -> dict:
        if Rendered.built is None:
            Rendered.built = build_contribute(self, NOW)
        return Rendered.built

    def pages(self) -> dict:
        return self.build()["html"]

    def test_the_recorders_topics_and_words(self):
        s = strings()
        for lang, html in self.pages().items():
            with self.subTest(lang=lang):
                self.assertTrue(html, "the page was built")
                cfg = rec_config(html)
                self.assertEqual(sorted(cfg["d"]), sorted(report_words()))
                for k, v in cfg["d"].items():
                    self.assertEqual(v, s["community.recorder.rep_" + k][lang], k)
                self.assertRegex(cfg["diag"]["to"], r"^[^@\s]+@[^@\s]+\.\w+$")
                self.assertRegex(cfg["diag"]["ver"], r"^[0-9a-f]{10}$")
                lv = cfg["topics"]["lv"]
                self.assertEqual([(o["t"], o["d"]) for o in lv if o["dated"]], [("Recaídas", "2026-10-17"), ("Prisiones", "2026-12-15")])
                self.assertEqual(sorted(o["t"] for o in lv if not o["dated"]), sorted(LV_TOPICS))
                self.assertEqual([o["t"] for o in cfg["topics"]["gv"]], ["Emotional Sobriety", "Sober Seniors"])
                self.assertEqual([o["i"] for o in lv], list(range(len(lv))))
                for pub in ("gv", "lv"):
                    seen = [o["dated"] for o in cfg["topics"][pub]]
                    self.assertEqual(seen, sorted(seen, reverse=True), "the coming themes first")
                # every "Record a story on this topic" chooses a topic of the recorder's La Viña list (the same words)
                links = {unescape(v) for v in re.findall(r'data-rec-go="lv" data-rec-topic="([^"]*)"', html)}
                self.assertEqual(links, set(LV_TOPICS), "each suggested topic, in La Viña's own words")
                self.assertEqual(len(re.findall(r'data-rec-go="lv" data-rec-topic=', html)), len(re.findall(r"data-rec-topic=", html)))
                self.assertIn(s["community.rec.topic_here"][lang], html)
                # the list: one per magazine, its words, "Another topic"
                self.assertEqual(html.count(':value="topicPick('), 2)
                self.assertEqual(html.count('<option value="other">' + s["community.recorder.tp_other"][lang].replace("'", "&#39;") + "</option>"), 2)
                # the check
                self.assertIn(s["community.recorder.chk_title"][lang], html)

    def test_the_page_says_the_same_every_day_and_after_a_deploy(self):
        """eleventy/lastmod.js: /contribute/ gets a new sitemap date (and an IndexNow ping) only when what it says
        changes. The recorder's list counts the days left on the visitor's device (x-text topicText): the built page
        holds each theme's words and deadline, never a count — the next day's build has the same fingerprint, though a
        theme's days left went from 2 to 1. The device check's code version (diag.ver, new with every deploy) is left
        out of it (#rec-config data-lastmod="skip:diag")."""
        today = self.build()
        tomorrow = build_contribute(self, NEXT_DAY)
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                html = today["html"][lang]
                self.assertNotEqual(html, tomorrow["html"][lang], "the next day's build: the deadlines' own countdowns moved")
                self.assertEqual(today["fp"][lang], tomorrow["fp"][lang], "… and the page's fingerprint did not")
                self.assertEqual(today["deployed"][lang], today["fp"][lang], "a new code version: the same fingerprint")
                self.assertEqual(rec_config(html)["topics"], rec_config(tomorrow["html"][lang])["topics"])
                options = re.findall(r'<option value="\d+"[^>]*>([^<]*)</option>', html)
                self.assertIn("Recaídas", options)
                self.assertTrue(options and not [o for o in options if "·" in o], options)
                self.assertTrue(all("days" not in o for p in ("gv", "lv") for o in rec_config(html)["topics"][p]))

    def test_if_walls_could_talk_in_the_photos_card(self):
        s = strings()
        for lang, html in self.pages().items():
            with self.subTest(lang=lang):
                start = html.index(s["read.contrib.k_art_t"][lang].replace("&", "&amp;"))
                card = html[start:html.index("</details>", start)]
                name = "If Walls Could Talk" if lang == "en" else '<span lang="en">If Walls Could Talk</span>'
                self.assertIn(name, card)
                text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", card)).replace("&#39;", "'")
                for k in ("k_walls_tip", "k_walls_guide", "k_walls_send", "k_walls_lv", "k_walls_lv_link"):
                    self.assertIn(s["read.contrib." + k][lang], text, k)
                rules = s["read.contrib.k_walls"][lang].replace("{name}", "If Walls Could Talk")
                self.assertIn(rules, text)
                links = yaml.safe_load(read(ROOT / "config" / "site.yml"))["links"]
                for k in ("gv_guidelines", "gv_share_story", "lv_share_story"):
                    self.assertIn(f'href="{links[k]}"', card, k)
                self.assertNotIn("<img", card)                                # words and links only
                self.assertNotIn('type="file"', card)


class RealData(unittest.TestCase):
    """The day's synced data (data/site/editorial.json): La Viña's suggested topics are there, and each one's "Record a
    story on this topic" chooses a topic of the recorder's list. The data alone can change this answer, so the publish
    gate leaves it to the Code check (scripts/ops/gate_tests.py DATA_TESTS); Rendered tests the code on data of its own."""

    def test_la_vinas_topics_and_their_links(self):
        built = build_contribute(self, NOW, data=None)
        for lang, html in built["html"].items():
            with self.subTest(lang=lang):
                lv = rec_config(html)["topics"]["lv"]
                self.assertTrue(lv, "La Viña's topics")
                links = [unescape(v) for v in re.findall(r'data-rec-go="lv" data-rec-topic="([^"]*)"', html)]
                self.assertTrue(links, "La Viña's suggested topics have their links")
                # (recorder.js go() reads a link's words with their spaces made single, as recorderTopics() writes them)
                self.assertEqual(sorted({re.sub(r"\s+", " ", v).strip() for v in links} - {o["t"] for o in lv}), [])


if __name__ == "__main__":
    unittest.main()
