"""GVR / RLV 101 (config/orientation.yml → /orientation/): the lesson file stays complete and safe.

The site build (src/_data/orientation.js, I18N_STRICT=1) stops on the same problems; these tests say
which lesson is wrong without running the build, and add the site's wording rules.

The hub also holds the committee's presentations (config/presentations/, SPEC §4): Hub* below build the page for
real (Eleventy, ONLY=orientation,sw,presentations-json,portfolio, as GitHub Pages builds it) with the four decks,
with the two sample decks (tests/fixtures/presentations) and with none, and check the page's order and anchors
(the owner's order: the sessions, their own slides and handout, the presentations, "How presenting works"
closed), one card per deck with the hooks the player (src/assets/js/presentations.js) finds, the no-JavaScript
fallback, "Print or save a copy", "How presenting works" — the service worker keeping the decks with "Save key
pages for offline", and /portfolio/ linking each deck's PowerPoint file to its web presentation. Skipped without
Node.js or node_modules (npm ci), as in tests/nodejs.py.
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
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "config" / "orientation.yml"
I18N = ROOT / "src" / "_i18n" / "orientation.json"
PAGE = ROOT / "src" / "pages" / "orientation.njk"
PLACEHOLDERS = {"rule_lc", "time", "panel", "panel_start"}
EXAMPLES = {"issue", "meeting", "tip", "botm", "deadline", "poster"}
# The site's wording rules for visitors (docs: "document(s)", never "PDF"; no talk of how data is gathered).
BANNED = re.compile(r"\b(pdf|crawl\w*|scrap\w*|robot|bot|automatically|autom[aá]ticamente)\b", re.I)
# AA shares experience rather than teaching: the orientation is "sessions" led by a "facilitator", with
# "review questions" — never classroom words; and GVR / RLV service is a "position", never a job.
CLASSROOM = re.compile(r"\b(lessons?|lecci[oó]n(es)?|trainers?|training|quiz\w*|course|curso|curriculum|class(es)?|"
                       r"clases?|self-check|teach\w*|enseñ\w*|capacitaci[oó]n|jobs?)\b", re.I)


def pairs(node, where=""):
    """Every {en, es} text pair in the lesson data, with a readable location."""
    if isinstance(node, dict):
        if set(node) >= {"en", "es"} and all(isinstance(node[k], str) for k in ("en", "es")):
            yield where, node
            return
        for k, v in node.items():
            yield from pairs(v, f"{where}.{k}" if where else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from pairs(v, f"{where}[{i}]")


class OrientationFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = yaml.safe_load(FILE.read_text(encoding="utf-8"))
        cls.lessons = cls.cfg["lessons"]
        site = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        cls.site_links = site.get("links") or {}

    def test_panel(self):
        self.assertIsInstance(self.cfg["panel"]["number"], int)
        self.assertRegex(str(self.cfg["panel"]["starts"]), r"^\d{4}-\d{2}$")

    def test_six_short_lessons(self):
        self.assertEqual(len(self.lessons), 6)
        ids = [l["id"] for l in self.lessons]
        self.assertEqual(len(ids), len(set(ids)), "lesson ids must be unique (they are page addresses)")
        for l in self.lessons:
            with self.subTest(lesson=l["id"]):
                self.assertRegex(l["id"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertTrue(5 <= l["minutes"] <= 8, "each lesson is read in 5–8 minutes")
                self.assertIn(l["example"], EXAMPLES)
                self.assertTrue(3 <= len(l["points"]) <= 6, "3 to 6 key points")
                for key in ("title", "summary", "goal", "try", "discuss"):
                    self.assertIn(key, l)

    def test_every_text_in_both_languages(self):
        found = list(pairs(self.lessons, "lessons"))
        self.assertGreater(len(found), 100)
        for where, p in found:
            with self.subTest(where=where):
                self.assertTrue(p["en"].strip(), "missing English")
                self.assertTrue(p["es"].strip(), "missing Spanish")

    def test_lengths_fit_heroes_and_slides(self):
        for l in self.lessons:
            with self.subTest(lesson=l["id"]):
                # hero subtitle budget (ui.njk): 110 characters EN / 135 ES; a 2-line title on a phone
                self.assertLessEqual(len(l["summary"]["en"]), 110)
                self.assertLessEqual(len(l["summary"]["es"]), 135)
                self.assertLessEqual(len(l["title"]["en"]), 32)
                self.assertLessEqual(len(l["title"]["es"]), 32)
                for p in l["points"]:
                    for lang in ("en", "es"):
                        self.assertLessEqual(len(p["text"][lang]), 240, p["title"][lang])

    def test_self_check(self):
        for l in self.lessons:
            answers = []
            for i, q in enumerate(l["check"], 1):
                with self.subTest(lesson=l["id"], question=i):
                    self.assertEqual(len(q["options"]), 3)
                    self.assertIn(q["answer"], (1, 2, 3))
                    self.assertTrue(q["why"]["en"] and q["why"]["es"])
                    opts = [o["en"].lower() for o in q["options"]]
                    self.assertEqual(len(opts), len(set(opts)), "options must differ")
                    answers.append(q["answer"])
            with self.subTest(lesson=l["id"]):
                self.assertEqual(len(l["check"]), 3)
                self.assertGreater(len(set(answers)), 1, "the right answer should not always be in the same place")

    def test_placeholders_are_known(self):
        for where, p in pairs(self.lessons, "lessons"):
            for lang in ("en", "es"):
                for name in re.findall(r"\{(\w+)\}", p[lang]):
                    with self.subTest(where=where, lang=lang):
                        self.assertIn(name, PLACEHOLDERS)

    def test_wording_rules(self):
        for where, p in pairs(self.lessons, "lessons"):
            for lang in ("en", "es"):
                with self.subTest(where=where, lang=lang):
                    self.assertIsNone(BANNED.search(p[lang]), p[lang])

    def test_links_resolve(self):
        pages = {p.stem for p in (ROOT / "src" / "pages").glob("*.njk")}
        for l in self.lessons:
            self.assertTrue(l.get("links"), l["id"])
            for k in l["links"]:
                with self.subTest(lesson=l["id"], link=k.get("href") or k.get("link") or k.get("url")):
                    self.assertTrue(k["label"]["en"] and k["label"]["es"])
                    if k.get("href"):
                        seg = k["href"].strip("/").split("/")[0].split("#")[0]
                        self.assertIn(seg, pages, "href must be a page of this site")
                    elif k.get("link"):
                        self.assertIn(k["link"], self.site_links)
                        if k.get("link_es"):
                            self.assertIn(k["link_es"], self.site_links)
                    else:
                        self.assertRegex(k["url"], r"^https://www\.(aagrapevine|aalavina)\.org/")
                    if k.get("pub"):
                        self.assertIn(k["pub"], ("gv", "lv"))


class OrientationFactsTest(unittest.TestCase):
    """Facts the lessons teach, as the official pages give them (checked September 2026)."""

    @classmethod
    def setUpClass(cls):
        cls.lessons = {l["id"]: l for l in yaml.safe_load(FILE.read_text(encoding="utf-8"))["lessons"]}

    def text(self, lesson: str, lang: str) -> str:
        l = self.lessons[lesson]
        parts = [p["text"][lang] for p in l["points"]] + [l["try"][lang]]
        parts += [q["why"][lang] for q in l["check"]] + [o[lang] for q in l["check"] for o in q["options"]]
        return " ".join(parts)

    def test_how_the_magazines_are_supported(self):
        # aalavina.org/Historia-de-LV: La Viña is published by AA Grapevine "con el apoyo de la Junta de
        # Servicios Generales como un servicio a la comunidad" — the General Service Board is funded by
        # the groups' contributions, so the lesson never says the magazines take none
        self.assertIn("General Service Board", self.text("magazines", "en"))
        self.assertIn("Junta de Servicios Generales", self.text("magazines", "es"))
        self.assertNotRegex(self.text("magazines", "en"), r"(?i)(don't|do not) take group contributions|fully self-supporting")
        self.assertNotRegex(self.text("magazines", "es"), r"(?i)no reciben contribuciones")

    def test_meeting_in_print(self):
        # aagrapevine.org/history-aa-grapevine: members in the armed services overseas called it their
        # "meeting in print" — the slide shows the text without its title, so the text says it
        first = self.lessons["magazines"]["points"][0]["text"]
        self.assertIn("meeting in print", first["en"])
        self.assertIn("reunión impresa", first["es"])
        self.assertIn("armed forces", first["en"])

    def test_wording_that_stays_true_for_the_whole_panel(self):
        role = self.text("role", "en") + " " + self.text("role", "es")
        self.assertNotRegex(role, r"starts in \{panel_start\}|empieza en \{panel_start\}")

    def test_anonymity_is_about_the_public_level(self):
        # Tradition Eleven: press, radio, films (today: anything public) — not members' own chats
        self.assertNotIn("WhatsApp", self.text("traditions", "en"))
        self.assertIn("outside AA", self.text("traditions", "en"))
        self.assertIn("fuera de AA", self.text("traditions", "es"))


class OrientationStringsTest(unittest.TestCase):
    def test_ui_strings_in_both_languages(self):
        data = json.loads(I18N.read_text(encoding="utf-8"))
        self.assertGreater(len(data), 50)
        for key, v in data.items():
            with self.subTest(key=key):
                self.assertTrue(v.get("en", "").strip() and v.get("es", "").strip())
                self.assertEqual(set(re.findall(r"\{(\w+)\}", v["en"])), set(re.findall(r"\{(\w+)\}", v["es"])),
                                 "both languages use the same {placeholders}")
                self.assertIsNone(BANNED.search(v["en"]) or BANNED.search(v["es"]))

    def test_aa_wording(self):
        """Every visitor-facing text of GVR / RLV 101 (its strings and its session data), the other strings
        that name it, and the GVR / RLV corner's own strings."""
        texts = [(f"orientation.json {k}", v[lang]) for k, v in json.loads(I18N.read_text(encoding="utf-8")).items()
                 for lang in ("en", "es")]
        texts += [(f"orientation.yml {w}", p[lang]) for w, p in pairs(yaml.safe_load(FILE.read_text(encoding="utf-8")))
                  for lang in ("en", "es")]
        others = {}
        for name in ("common", "access", "pwa", "read"):
            others.update(json.loads((ROOT / "src" / "_i18n" / f"{name}.json").read_text(encoding="utf-8")))
        texts += [(k, v[lang]) for k, v in others.items() for lang in ("en", "es")
                  if k.startswith(("read.gvr.", "nav.orientation")) or "101" in v["en"]]
        self.assertGreater(len(texts), 400)
        for where, s in texts:
            with self.subTest(where=where):
                self.assertIsNone(CLASSROOM.search(s), s)

    def test_length_budgets(self):
        """The hero's subtitle with the presentations, its buttons and the "On this page" chips (ui.njk: subtitle
        110 / 135 characters, buttons 24 / 28, chips 20 / 24)."""
        data = json.loads(I18N.read_text(encoding="utf-8"))
        budgets = {"orientation.hero_sub_pres": (110, 135), "orientation.hero_pres": (24, 28), "orientation.hero_present": (24, 28),
                   "orientation.nav_pres": (20, 24), "orientation.nav_present": (20, 24)}
        for key, (en, es) in budgets.items():
            with self.subTest(key=key):
                self.assertLessEqual(len(data[key]["en"]), en)
                self.assertLessEqual(len(data[key]["es"]), es)

    def test_print_wording(self):
        # the print window's "Save as PDF" is a document on this site (never "PDF"), and a saved version of a
        # presentation is the presenter's own — "your changes stay on this device"
        data = json.loads(I18N.read_text(encoding="utf-8"))
        self.assertIn("document", data["orientation.pres_print_note"]["en"])
        self.assertIn("documento", data["orientation.pres_print_note"]["es"])
        self.assertIn("this device", data["orientation.pres_how_private_t"]["en"])

    def test_one_name_per_action(self):
        """The owner (2026-10-02): one name for each action, on the page and in the player. Resetting one
        presentation and all four, as the buttons say; "a copy" is what prints (Print or save a copy), "your version"
        the file Customize saves (so the how-to's item is "Save your version", not "Save a copy"); "Start over" is
        only the sessions' progress button. And the four print modes described as the player describes them."""
        data = json.loads(I18N.read_text(encoding="utf-8"))
        pick = lambda k: (data[k]["en"], data[k]["es"])                                    # noqa: E731
        self.assertEqual(pick("orientation.pres_reset"), ("Reset to the original", "Volver al original"))
        self.assertEqual(pick("orientation.pres_reset_all"), ("Reset all {n} to the original", "Devolver las {n} al original"))
        self.assertEqual(pick("orientation.pres_how_reset_t"), pick("orientation.pres_reset"))
        # …and the how-to names "Reset all" by its label and says where it is (under the presentations, as the
        # player's Save & share does)
        for lang, where in (("en", "under the presentations"), ("es", "debajo de las presentaciones")):
            self.assertIn(data["orientation.pres_reset_all"][lang], data["orientation.pres_how_reset"][lang])
            self.assertIn(where, data["orientation.pres_how_reset"][lang])
        self.assertEqual(pick("orientation.pres_how_save_t"), ("Save your version", "Guardar tu versión"))
        self.assertNotIn(data["orientation.progress_reset"]["en"], [v["en"] for k, v in data.items() if k.startswith("orientation.pres_")])
        player = json.loads((ROOT / "src" / "_i18n" / "presentations.json").read_text(encoding="utf-8"))
        same = lambda s: re.sub(r"[,.]", "", s).strip().lower()                           # noqa: E731
        for mode in MODES:
            for lang in ("en", "es"):
                with self.subTest(mode=mode, lang=lang):
                    self.assertEqual(data[f"orientation.pres_mode_{mode}_t"][lang], player[f"pres.print_{mode}"][lang])
                    self.assertEqual(same(data[f"orientation.pres_mode_{mode}_d"][lang]), same(player[f"pres.print_{mode}_d"][lang]))


# ----------------------------------------------------------------------------------------------------------------
# The workshop presentations on the hub (SPEC §4)
# ----------------------------------------------------------------------------------------------------------------
MODES = ["slides", "notes", "handout", "script"]
KEPT = ["sessions", "lessons", "present", "facilitators", "trainers", "next"]   # addresses older links use


def node_ready(case: unittest.TestCase) -> None:
    if not node_path():
        case.skipTest("Node.js is not installed")
    if not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
        case.skipTest("the site's npm packages are not installed (npm ci)")


class HubTemplate(unittest.TestCase):
    """What the page needs from the player: its two scripts (after orientation.js) and its dialog shell."""

    def test_the_player_is_loaded_and_called(self):
        text = PAGE.read_text(encoding="utf-8")
        front = text.split("---")[1]
        self.assertIn('pageScripts: ["/assets/js/orientation.js", "/assets/js/presentations-core.js", "/assets/js/presentations.js"]', front)
        self.assertIn('{% import "macros/presentations.njk" as pres with context %}', text)
        self.assertIn("{{ pres.player(lang) }}", text)

    def test_one_key_list(self):
        # "How presenting works" holds the keys of BOTH slide shows: the sessions' card has no list of its own
        text = PAGE.read_text(encoding="utf-8")
        self.assertEqual(text.count('<dl class="o101-keys'), 1)


class HubBuild(unittest.TestCase):
    """/orientation/ and /es/orientation/ (and /portfolio/, whose deck files link to the presentations) built three
    times: the four decks (config/presentations), the two sample decks (tests/fixtures/presentations) and none (an
    empty folder)."""

    @classmethod
    def build(cls, out: Path, decks: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "PRESENTATIONS_DIR": str(decks), "PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1",
               "ONLY": "orientation,sw,presentations-json,portfolio", "NODE_NO_WARNINGS": "1"}
        return subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                               "--output", str(out)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                              timeout=600)

    @classmethod
    def setUpClass(cls):
        cls.tmp = None
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="orientation-hub-"))
        (cls.tmp / "no-decks").mkdir()
        cls.dirs = {"real": ROOT / "config" / "presentations", "sample": ROOT / "tests" / "fixtures" / "presentations",
                    "none": cls.tmp / "no-decks"}
        cls.runs = {k: cls.build(cls.tmp / k, d) for k, d in cls.dirs.items()}
        cls.pages, cls.raw, cls.portfolio = {}, {}, {}
        for k in cls.dirs:
            for lang in ("en", "es"):
                f = cls.tmp / k / ("es" if lang == "es" else "") / "orientation" / "index.html"
                # (the text too: lxml drops Alpine's @event attributes, which browsers read as written)
                cls.raw[(k, lang)] = f.read_text(encoding="utf-8") if f.exists() else ""
                cls.pages[(k, lang)] = BeautifulSoup(cls.raw[(k, lang)], "lxml") if f.exists() else None
                f = cls.tmp / k / ("es" if lang == "es" else "") / "portfolio" / "index.html"
                cls.portfolio[(k, lang)] = BeautifulSoup(f.read_text(encoding="utf-8"), "lxml") if f.exists() else None

    @classmethod
    def tearDownClass(cls):
        if cls.tmp:
            shutil.rmtree(cls.tmp, True)

    def setUp(self):
        node_ready(self)
        for k, r in self.runs.items():
            self.assertEqual(r.returncode, 0, f"{k}: {r.stderr[-3000:]}")

    def decks(self, kind: str) -> list[dict]:
        """The decks as the page gets them (src/_data/presentations.js → loadDecks)."""
        if not hasattr(self, "_decks"):
            type(self)._decks = {}
        if kind not in self._decks:
            self._decks[kind] = run_js(self, """
              const { loadDecks } = await imp("eleventy/filters/presentations.js");
              out(loadDecks(input.dir).decks.map((d) => ({ id: d.id, title: d.title, short: d.short, card: d.card,
                minutes: d.minutes, count: d.count, kinds: d.kinds, presets: d.presets, drive_title: d.drive_title,
                url: d.url })));""",
                data={"dir": str(self.dirs[kind])})
        return self._decks[kind]

    @staticmethod
    def drive_copy(d: dict) -> dict | None:
        """The deck's PowerPoint copy as the page finds it: the newest committee Drive file whose own title is the
        deck's drive_title (data/site/drive.json) — None without one."""
        items = json.loads((ROOT / "data" / "site" / "drive.json").read_text(encoding="utf-8")).get("items") or []
        hits = sorted((it for it in items if it.get("source") == "drive" and it.get("status") != "gone"
                       and re.sub(r"\s+", " ", it.get("title") or "").strip() == d["drive_title"]),
                      key=lambda it: str(it.get("date") or ""), reverse=True)
        return hits[0] if hits else None

    @staticmethod
    def short_name(label: str, minutes: int | None, full: int) -> str:
        """A version on a card's "Also:" line (orientation.njk): its label without the "(about 48 minutes)" it ends
        with — "(48 min)" when that is not the full version's length — and in lower case after the colon."""
        name = re.sub(r"\s*\((?:about|unos|unas)\s[^()]*\)\s*$", "", label)
        if name != label and minutes and minutes != full:
            name += f" ({minutes} min)"
        if not (re.match(r"(?:Grapevine|La Viña|AA|Zoom|NETA)\b", name) or name[1:2] != name[1:2].lower()):
            name = name[:1].lower() + name[1:]
        return name

    def views(self):
        for kind in ("real", "sample", "none"):
            for lang in ("en", "es"):
                yield kind, lang, self.pages[(kind, lang)]

    @staticmethod
    def main_of(soup):
        """The page's <main> without the slide show's <template> (a copy: the parsed pages are shared)."""
        main = BeautifulSoup(str(soup.select_one("main")), "lxml").select_one("main")
        for t in main.select("template"):
            t.decompose()
        return main

    def test_anchors_are_kept_and_presentations_added(self):
        for kind, lang, soup in self.views():
            with self.subTest(kind=kind, lang=lang):
                ids = {e["id"] for e in soup.select("[id]")}
                for a in KEPT + ["presenting"]:
                    self.assertIn(a, ids)
                has = kind != "none"
                self.assertEqual("presentations" in ids, has)
                # the hero leads to the presentations; "On this page" lists every part in the page's order, each to an
                # id of this page — the sessions' slides named as the hero's button names them
                self.assertEqual(bool(soup.select('.gv-hero a[href="#presentations"]')), has)
                chips = [a["href"] for a in soup.select("nav.o101-onpage a.chip")]
                self.assertEqual(chips, ["#sessions", "#present"] + (["#presentations"] if has else []) + ["#facilitators", "#next"])
                for h in chips:
                    self.assertIn(h[1:], ids)
                present = soup.select_one('nav.o101-onpage a.chip[href="#present"]').get_text(" ", strip=True)
                self.assertEqual(present, {"en": "Present the sessions", "es": "Presentar las sesiones"}[lang])
                # a chip reached with Tab is scrolled into view (the row scrolls sideways on phones)
                self.assertRegex(self.raw[(kind, lang)], r'<ul class="chip-row mt-2" role="list" x-data="" @focusin="\$event\.target\.scrollIntoView\(')

    def test_the_page_reads_top_down(self):
        """The owner's order (2026-10-02): the sessions, then their own slides and handout right after them (#present),
        then the presentations, then "How presenting works" — closed — at the end of that band, for both."""
        for kind, lang, soup in self.views():
            with self.subTest(kind=kind, lang=lang):
                main = self.main_of(soup)
                order = [e.get("id") for e in main.select("section[id], nav.o101-onpage, details#presenting") if e.get("id") in
                         ("sessions", "presentations", "present", "presenting", "facilitators", "next") or e.name == "nav"]
                want = [None, "sessions", "present"] + (["presentations"] if kind != "none" else []) + ["presenting", "facilitators", "next"]
                self.assertEqual(order, want)
                # the sessions' slides, the presentations and the how-to share one tinted band; the how-to ends it
                band = main.select_one("#present").parent
                self.assertIn("section-band", band.get("class", []))
                if kind != "none":
                    self.assertIs(main.select_one("#presentations").parent, band)
                how = main.select_one("#presenting")
                self.assertIs(how.find_parent(class_="section-band"), band)
                self.assertIs(band.find_all(recursive=False)[-1], how.parent)
                self.assertEqual(how.name, "details")
                self.assertFalse(how.has_attr("open"), "closed until opened")
                # the section is "Presentations" (one of them is a meeting), not "Workshop presentations"
                if kind != "none":
                    self.assertEqual(main.select_one("#presentations-title").get_text(strip=True),
                                     {"en": "Presentations", "es": "Presentaciones"}[lang])
                    self.assertNotRegex(soup.select_one(".gv-hero").get_text(" "), r"(?i)workshop presentations|presentaciones de talleres")

    def test_headings_never_skip_a_level(self):
        # the page's own parts: the hero (and its card), the welcome card, the sessions, the "Present" band, the
        # facilitators and next steps (not the print-only handout, the slide show's template, the player's shell)
        parts = ".gv-hero, .hero-side, section.page-overlap, #sessions, div.section-band, #facilitators, #next"
        for kind, lang, soup in self.views():
            with self.subTest(kind=kind, lang=lang):
                main = self.main_of(soup)
                levels = [int(h.name[1]) for p in main.select(parts) for h in p.select("h1, h2, h3, h4, h5, h6")]
                self.assertEqual(levels[0], 1)
                self.assertEqual(levels.count(1), 1)
                for a, b in zip(levels, levels[1:]):
                    self.assertLessEqual(b, a + 1)
                self.assertLessEqual(max(levels), 3)

    def test_one_card_per_deck_with_the_players_hooks(self):
        for kind in ("real", "sample"):
            decks = self.decks(kind)
            self.assertGreater(len(decks), 0)
            for lang in ("en", "es"):
                soup = self.pages[(kind, lang)]
                cards = soup.select("#presentations ul.o101-pres-grid > li")
                self.assertEqual([c["id"] for c in cards], ["pres-" + d["id"] for d in decks])
                for c, d in zip(cards, decks):
                    with self.subTest(kind=kind, lang=lang, deck=d["id"]):
                        i = d["id"]
                        self.assertEqual(c.select_one("h3").get_text(strip=True), d["card"]["title"][lang])
                        head = c.select_one(".o101-pres-head .eyebrow").get_text(" ", strip=True)
                        self.assertIn(str(d["count"]), head)
                        # "Also:" the other versions by a short name, in lower case after the colon (not the
                        # Customize labels word for word: "Also: Running late (about 48 minutes)")
                        also = c.select_one(".o101-pres-head .text-xs")
                        others = [self.short_name(p["label"][lang], p.get("minutes"), d["minutes"]) for p in d["presets"][1:]]
                        if others:
                            self.assertEqual(also.get_text(" ", strip=True), {"en": "Also: ", "es": "También: "}[lang] + " · ".join(others))
                            self.assertNotRegex(also.get_text(), r"\((?:about|unos|unas) ")
                        else:
                            self.assertIsNone(also)
                        badge = "Presentación en inglés"
                        self.assertEqual(badge in c.get_text(" "), lang == "es")
                        self.assertEqual(len(c.select(".o101-pres-kinds > li")), len(d["kinds"]))
                        # Present · Customize · Presenter view: told apart by data-pres-mode, and their addresses say
                        # the mode too (a new tab, or a copied link, opens Customize or the presenter view)
                        opens = c.select(f'a[data-pres-open="{i}"]')
                        self.assertEqual([a["href"] for a in opens], [f"?present={i}", f"?present={i}&mode=customize", f"?present={i}&mode=presenter"])
                        self.assertEqual([a.get("data-pres-mode") for a in opens], [None, "customize", "presenter"])
                        # Print, in plain sight (not inside the More menu): the four modes, together under their label
                        prints = c.select(f'button[data-pres-print="{i}"]')
                        self.assertEqual([b["data-pres-print-mode"] for b in prints], MODES)
                        for b in prints:
                            self.assertIsNone(b.find_parent("details"))
                            self.assertIsNotNone(b.find_parent(class_="o101-pres-print-btns"))
                        self.assertEqual(len(c.select(".o101-pres-print-btns > button")), 4)
                        # the status line the script fills; Reset hidden until there is something to reset
                        status = c.select(f'[data-pres-status="{i}"]')
                        self.assertEqual(len(status), 1)
                        self.assertEqual(status[0].decode_contents().strip(), "")
                        reset = c.select(f'button[data-pres-reset="{i}"]')
                        self.assertEqual(len(reset), 1)
                        self.assertTrue(reset[0].has_attr("hidden"))
                        self.assertIsNotNone(reset[0].find_parent("details", class_="cm-menu"))
                        # every JavaScript control is in the data-js-only block; the stand-in (the PowerPoint copy,
                        # when there is one) is data-nojs-only
                        actions = c.select_one(".o101-pres-actions")
                        self.assertTrue(actions.has_attr("data-js-only"))
                        for el in opens + prints + reset:
                            self.assertIs(el.find_parent(class_="o101-pres-actions"), actions)
                        for el in c.select(".o101-pres-nojs"):
                            self.assertTrue(el.has_attr("data-nojs-only"))
                # "Reset all" in plain sight, right under the cards (before "Print or save a copy"), where the
                # player's Save & share says it is — not in the closed "How presenting works", which kept it out of
                # view; hidden until there is something to reset
                every = soup.select('[data-pres-reset="all"]')
                self.assertEqual(len(every), 1)
                ra = every[0]
                self.assertEqual(ra.name, "button")
                self.assertTrue(ra.has_attr("hidden") and ra.has_attr("data-js-only"))
                self.assertIsNone(ra.find_parent("details"))
                self.assertIs(ra.find_previous_sibling(), soup.select_one("#presentations > ul.o101-pres-grid"))
                self.assertIs(ra.find_next_sibling(), soup.select_one("#presentations > .o101-pp"))
                self.assertEqual(ra.get_text(" ", strip=True),
                                 {"en": f"Reset all {len(decks)} to the original", "es": f"Devolver las {len(decks)} al original"}[lang])
                # without JavaScript the section says once why the cards have no buttons (not once per card)
                nojs = soup.select("#presentations [data-nojs-only]:not(.o101-pres-nojs, .o101-pp-nojs)")
                self.assertEqual(len(nojs), 1)
                self.assertIn("JavaScript", nojs[0].get_text())
                for el in soup.select("#presentations .o101-pres-nojs"):
                    self.assertNotIn("JavaScript", el.get_text(), "no per-card JavaScript line")

    def test_no_fact_twice_on_a_card(self):
        """A card says its length and versions in its head and what stays current in its chips — its summary and
        "Who it's for" don't say them again (the four decks' `card` texts)."""
        again = re.compile(r"(?i)\b\d+\s*(?:-\s*)?(?:minutes?|minutos?|hours?|horas?)\b|\ban hour\b|\buna hora\b|"
                           r"stays? current|se mantienen? al día|version|versión")
        for d in self.decks("real"):
            for lang in ("en", "es"):
                for k in ("summary", "audience"):
                    with self.subTest(deck=d["id"], lang=lang, text=k):
                        self.assertIsNone(again.search(d["card"][k][lang]), d["card"][k][lang])

    def test_la_vina_first_in_spanish(self):
        """Spanish running text names La Viña first (proper names such as "Comité de Grapevine y La Viña" aside)."""
        for d in self.decks("real"):
            for k in ("summary", "audience"):
                with self.subTest(deck=d["id"], text=k):
                    self.assertNotIn("Grapevine y La Viña", re.sub(r"Comité de Grapevine y La Viña", "", d["card"][k]["es"]))

    def test_the_powerpoint_copy(self):
        """The More menu and the no-JavaScript stand-in link the deck's PowerPoint copy: the newest committee Drive
        file whose title is the deck's drive_title (data/site/drive.json) — none, no link. It is a fixed copy, and
        says so: the month it was made, and that it doesn't update."""
        for kind in ("real", "sample"):
            for d in self.decks(kind):
                hit = self.drive_copy(d)
                want = ((hit.get("extra") or {}).get("view_url") or hit["url"]) if hit else None
                for lang in ("en", "es"):
                    with self.subTest(kind=kind, deck=d["id"], lang=lang):
                        card = self.pages[(kind, lang)].select_one(f"#pres-{d['id']}")
                        menu = [a["href"] for a in card.select(".o101-pres-more a[target=_blank]")]
                        nojs = [a["href"] for a in card.select(".o101-pres-nojs a")]
                        self.assertEqual(menu, [want] if want else [])
                        self.assertEqual(nojs, [want] if want else [])
                        if not want:
                            self.assertFalse(card.select(".o101-pres-nojs"))
                            continue
                        fixed = {"en": "doesn't update", "es": "no se actualiza"}[lang]
                        month = {"en": "October 2026", "es": "octubre de 2026"}[lang] if str(hit.get("date", "")).startswith("2026-10") else ""
                        for where in (card.select_one(".o101-pres-copy-note"), card.select_one(".o101-pres-nojs p")):
                            self.assertIn(fixed, where.get_text())
                            self.assertIn(month, where.get_text())

    def test_print_or_save_a_copy(self):
        for kind in ("real", "sample"):
            decks = self.decks(kind)
            ids = [d["id"] for d in decks]
            for lang in ("en", "es"):
                with self.subTest(kind=kind, lang=lang):
                    card = self.pages[(kind, lang)].select_one("#presentations .o101-pp")
                    self.assertEqual(card.select_one("h3")["id"], "pres-print-title")
                    self.assertEqual([o["value"] for o in card.select("select#pres-print-deck option")], ids)
                    # in English the short names (three titles start "Grapevine and La Viña…": all a 320px phone shows)
                    names = [o.get_text(strip=True) for o in card.select("select#pres-print-deck option")]
                    self.assertEqual(names, [d["short"] if lang == "en" else d["card"]["title"]["es"] for d in decks])
                    self.assertEqual([r["value"] for r in card.select('input[type=radio][name="mode"]')], MODES)
                    self.assertEqual([r.has_attr("checked") for r in card.select('input[type=radio][name="mode"]')], [True, False, False, False])
                    # …named as the player's print form reads them: the one Print button's two hooks are EMPTY, so the
                    # player prints what the fields say — with Alpine late or blocked too (nothing here uses Alpine)
                    self.assertEqual(card.select_one("select#pres-print-deck")["name"], "deck")
                    self.assertTrue(card.has_attr("data-pres-print-form"))
                    btn = card.select("button[data-pres-print]")
                    self.assertEqual(len(btn), 1)
                    self.assertEqual((btn[0]["data-pres-print"], btn[0]["data-pres-print-mode"]), ("", ""))
                    self.assertFalse([a for el in [card] + card.find_all(True) for a in el.attrs if a.startswith((":", "x-", "@"))],
                                     "no Alpine in the print card")
                    self.assertEqual(len(card.select(".o101-pp-mini .o101-pp-page")), 4)
                    text = card.get_text(" ")
                    self.assertNotRegex(text, r"(?i)\bpdf\b")
                    # without JavaScript: no picker and no "pick a presentation"; one line and the PowerPoint copies
                    for el in (card.select_one(".o101-pp-intro"), card.select_one(".o101-pp-body")):
                        self.assertTrue(el.has_attr("data-js-only"))
                    nojs = card.select_one(".o101-pp-nojs")
                    self.assertTrue(nojs.has_attr("data-nojs-only"))
                    copies = [self.drive_copy(d) for d in decks]
                    want = [((c.get("extra") or {}).get("view_url") or c["url"]) for c in copies if c]
                    self.assertEqual([a["href"] for a in nojs.select("a")], want)
                    self.assertEqual(len(nojs.select("p")), 1)

    def test_how_presenting_works_once(self):
        """One closed <details> for both slide shows (where it sits: test_the_page_reads_top_down): its summary names
        it, and inside, a line for touch screens comes first — a phone has no keyboard — then the keys."""
        for kind, lang, soup in self.views():
            with self.subTest(kind=kind, lang=lang):
                how = soup.select("#presenting")
                self.assertEqual(len(how), 1)
                how = how[0]
                self.assertEqual(how.name, "details")
                self.assertFalse(how.has_attr("open"))
                summary = how.select_one("summary")
                self.assertEqual(summary.select_one("h2")["id"], "presenting-title")
                self.assertIn({"en": "How presenting works", "es": "Cómo presentar"}[lang], summary.get_text())
                body = how.select_one(".o101-how-body")
                parts = [el for el in body.find_all(True) if "o101-how-touch" in el.get("class", []) or el.name == "dl"]
                self.assertEqual([el.name for el in parts], ["p", "dl"], "the touch line, then the keys")
                keys = [k.get_text(strip=True) for k in how.select(".o101-keys kbd")]
                self.assertEqual("N" in keys and "P" in keys and "B" in keys, kind != "none")
                self.assertEqual(len(soup.select(".o101-keys")), 1, "one list of keys")
                # it explains; it holds no control (a button in a closed box stays out of view)
                self.assertFalse(how.select(".o101-how-body button, .o101-how-body [data-pres-reset]"))
                # the sessions' slide show card points to it, and that link opens it (Alpine: [data-o101-how])
                self.assertTrue(soup.select('#present a[href="#presenting"][data-o101-how]'))
                self.assertIn("$el.open = true", how["x-init"])
                self.assertIn("[data-o101-how]", self.raw[(kind, lang)].split('<details id="presenting"', 1)[1].split(">", 1)[0])

    def test_the_sessions_stay_as_they_were(self):
        for kind, lang, soup in self.views():
            with self.subTest(kind=kind, lang=lang):
                self.assertEqual(len(soup.select("#sessions [data-o101-card]")), len(yaml.safe_load(FILE.read_text(encoding="utf-8"))["lessons"]))
                self.assertTrue(soup.select('#present a[href="?slides"][data-o101-present]'))
                self.assertTrue(soup.select("#present button[data-o101-print]"))
                self.assertIsNotNone(soup.select_one("template#o101-deck-tpl"))
                self.assertEqual(len(soup.select(".o101-handout > article.o101-sheet")), 6)
                self.assertIsNotNone(soup.select_one("[data-o101-resume]"))
        # without presentations the hero is the sessions' own: present them, print the handout
        soup = self.pages[("none", "en")]
        self.assertFalse(soup.select("[data-pres-open], [data-pres-print], [data-pres-status], [data-pres-reset]"))
        self.assertTrue(soup.select(".gv-hero button[data-o101-print]"))
        self.assertEqual(len(soup.select(".hero-stats .hero-stat")), 3)
        self.assertEqual(len(self.pages[("real", "en")].select(".hero-stats .hero-stat")), 4)

    def test_facilitators_hear_of_the_orientation_workshop(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                fac = self.pages[("real", lang)].select_one("#facilitators")
                self.assertTrue(fac.select('a[href="#pres-orientation-workshop"]'))
                self.assertIn("90", fac.select_one(".o101-fac-pres").get_text(" "))
                self.assertFalse(self.pages[("sample", lang)].select_one("#facilitators").select(".o101-fac-pres"))

    def test_portfolio_links_the_web_presentations(self):
        """/portfolio/ lists the committee's PowerPoint decks (fixed copies): each deck's card links to its web
        presentation, which stays current — "Present on the web" → /orientation/?present=<id> in the page's language
        — matched by the Drive file's own title (on /es/ the card shows a translated one). Other files: no link."""
        for kind in ("real", "sample", "none"):
            decks = self.decks(kind) if kind != "none" else []
            for lang in ("en", "es"):
                with self.subTest(kind=kind, lang=lang):
                    soup = self.portfolio[(kind, lang)]
                    self.assertIsNotNone(soup)
                    links = soup.select('main a[href*="/orientation/?present="]')
                    want = sorted(f"/aagrapevine/{'es/' if lang == 'es' else ''}orientation/?present={d['id']}"
                                  for d in decks if self.drive_copy(d))
                    self.assertEqual(sorted(a["href"] for a in links), want)
                    for a in links:
                        self.assertIn({"en": "Present on the web", "es": "Presentar en la web"}[lang], a.get_text())
                        card = a.find_parent("article")
                        self.assertIn({"en": "fixed copy", "es": "copia fija"}[lang], card.get_text())

    def test_save_key_pages_keeps_the_presentations(self):
        """sw.js: CONFIG.files lists each deck's JSON (with the GVR 101 hub); none without decks."""
        for kind in ("real", "sample", "none"):
            with self.subTest(kind=kind):
                sw = (self.tmp / kind / "sw.js").read_text(encoding="utf-8")
                config = json.loads(re.search(r"const CONFIG = (\{.*?\n\});", sw, re.S).group(1))
                want = [] if kind == "none" else [d["url"].lstrip("/") for d in self.decks(kind)]
                self.assertEqual(config["files"], want)
                self.assertIn("orientation/", config["save"])
                for f in want:
                    self.assertTrue((self.tmp / kind / f).is_file(), f)


WORKER_JS = r"""
import vm from "node:vm";
const ORIGIN = "https://example.test";
const code = fs.readFileSync(input.sw, "utf8");
const store = new Map();
const make = (url, status, body, headers) => {
  const res = new Response(body, { status, headers });
  Object.defineProperty(res, "type", { value: "basic" });
  Object.defineProperty(res, "url", { value: url });
  return res;
};
class FakeCache {
  constructor() { this.m = new Map(); }
  key(r) { return typeof r === "string" ? new URL(r, ORIGIN).href : r.url; }
  async put(r, res) { const k = this.key(r); this.m.set(k, { body: await res.arrayBuffer(), status: res.status, headers: [...res.headers] }); }
  async match(r, o = {}) {
    const k = this.key(r);
    if (this.m.has(k)) { const e = this.m.get(k); return make(k, e.status, e.body, e.headers); }
    if (o.ignoreSearch) for (const [kk, e] of this.m) if (kk.split("?")[0] === k.split("?")[0]) return make(kk, e.status, e.body, e.headers);
    return undefined;
  }
  async delete(r) { return this.m.delete(this.key(r)); }
  async keys() { return [...this.m.keys()].map((u) => new Request(u)); }
}
const caches = {
  async open(n) { if (!store.has(n)) store.set(n, new FakeCache()); return store.get(n); },
  async keys() { return [...store.keys()]; },
  async delete(n) { return store.delete(n); },
  async has(n) { return store.has(n); },
  async match(r, o) { for (const c of store.values()) { const hit = await c.match(r, o); if (hit) return hit; } return undefined; },
};
const net = new Map(Object.entries(input.net));
async function fetch(req) {
  const url = new URL(typeof req === "string" ? req : req.url, ORIGIN).href;
  const spec = net.get(url);
  if (!spec) throw new TypeError("Failed to fetch");
  return make(url, spec.status || 200, spec.body, { "content-type": spec.ct, date: new Date().toUTCString() });
}
const handlers = {};
const self = { addEventListener: (t, fn) => { handlers[t] = fn; }, location: { origin: ORIGIN }, registration: {},
               clients: { claim: async () => {}, matchAll: async () => [] }, skipWaiting: () => {} };
class WorkerRequest extends Request {
  constructor(i, init) { super(typeof i === "string" ? new URL(i, ORIGIN).href : i, init); }
}
const ctx = vm.createContext({ self, caches, fetch, Request: WorkerRequest, Response, Headers, URL, console, setTimeout, clearTimeout });
vm.runInContext(code, ctx);
const CONFIG = vm.runInContext("CONFIG", ctx);
const until = async (w) => { let n = -1; while (n !== w.length) { n = w.length; await Promise.allSettled(w.slice()); } };
const replies = [], waits = [];
handlers.message({ data: { type: "SAVE", lang: "en" }, ports: [{ postMessage: (m) => replies.push(m) }], waitUntil: (p) => waits.push(p) });
await until(waits);
const data = store.has("gvlv-data-v1") ? [...store.get("gvlv-data-v1").m.keys()] : [];
// …and the network-first rule answers a presentation from that copy when the network is gone
net.clear();
let offline = null;
const first = CONFIG.files[0];
if (first) {
  let answer = null;
  const w2 = [];
  handlers.fetch({ request: new WorkerRequest(CONFIG.base + first + "?v=1"), clientId: "", respondWith: (p) => { answer = p; }, waitUntil: (p) => w2.push(p) });
  const res = answer ? await answer.catch(() => null) : null;
  offline = res ? { status: res.status, body: await res.text() } : null;
}
out({ files: CONFIG.files, base: CONFIG.base, data, done: replies.find((r) => r.type === "SAVE_DONE") || null, offline });
"""


class HubWorker(unittest.TestCase):
    """"Save key pages for offline" (sw-core.js savePages → saveFiles) keeps the presentations' JSON where the
    worker's network-first rule for JSON looks, without counting them as pages; one that can't be fetched is
    skipped quietly. Run against the sw.js of a real build (the sample decks)."""

    def test_saved_with_the_pages(self):
        node_ready(self)
        tmp = Path(tempfile.mkdtemp(prefix="orientation-sw-"))
        try:
            r = HubBuild.build(tmp / "site", ROOT / "tests" / "fixtures" / "presentations")
            self.assertEqual(r.returncode, 0, r.stderr[-3000:])
            sw = tmp / "site" / "sw.js"
            config = json.loads(re.search(r"const CONFIG = (\{.*?\n\});", sw.read_text(encoding="utf-8"), re.S).group(1))
            origin, base = "https://example.test", config["base"]
            page = "<!doctype html><html><head><title>x</title></head><body>page</body></html>"
            net = {origin + base + p: {"body": page, "ct": "text/html; charset=utf-8"} for p in config["save"] if "{month}" not in p}
            files = config["files"]
            self.assertEqual(len(files), 2)
            net[origin + base + files[0]] = {"body": '{"app": "gv-presentation"}', "ct": "application/json"}   # the second one fails
            out = run_js(self, WORKER_JS, data={"sw": str(sw), "net": net}, needs_modules=False)
        finally:
            shutil.rmtree(tmp, True)
        self.assertEqual(out["data"], [origin + base + files[0]])
        done = out["done"]
        self.assertEqual(done["failed"], [])
        self.assertEqual(done["saved"], done["total"])
        self.assertEqual(done["total"], len([p for p in config["save"] if "{month}" not in p]), "pages only")
        self.assertEqual(out["offline"], {"status": 200, "body": '{"app": "gv-presentation"}'})


if __name__ == "__main__":
    unittest.main()
