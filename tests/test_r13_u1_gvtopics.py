"""Round 13, unit u1 (Share your story › "Upcoming themes & deadlines"): Grapevine's suggested topics, and the two
deadline cards that end together.

  * Parser      — scripts/sync/editorial.py: Grapevine's /contribute introduction names its departments ("departments
                  such as Emotional Sobriety, Sponsorship, … and Home Group") and what it is "always in need of" (Steps
                  4–12, every Tradition): evergreen topics like La Viña's (no issue, no deadline, ed:gv:any:<slug>,
                  topic_type "department" / "always_needed"), in Grapevine's own words, tidied — from the real page
                  (tests/fixtures/editorial/gv_contribute.html, saved October 16, 2026) and from variants: nbsp, en / em
                  dashes and hyphens, "and" / "&" / an Oxford comma, quotes, "A.A.", "etc." / "to name a few" /
                  remarks in brackets (never a tile the page does not name); the sentences gone → no topics, no error,
                  a note on /status/; a list worded differently (not all names written as titles: "…, which appear
                  in most issues", "any topic") → that list not read, its previous topics kept, the sentence quoted
                  on /status/; only the introduction read (never a theme's prompt); topics without a calendar → "no
                  themes found" (the previous topics stay); the part is authoritative (a topic the page drops leaves;
                  first_seen is kept) and keep_window keeps them.
  * Spanish     — every topic the page names has hand-written Spanish in data/translations/overrides.yml, and the
                  translator build_data uses gives it (never the machine's).
  * Consumers   — read.js editorialFor (Grapevine's topics as La Viña's, what it always needs first) and recorderTopics
                  (its "Ideas: Grapevine's suggested topics", a theme listed twice once); Home's "Write for the
                  magazines" (each magazine's topics turn on their own); the Monthly toolkit (3 a month, on the page and
                  in the message; a machine translation marked on /es/monthly/; on the English poster where its
                  deadlines leave room and the poster stays roomy, La Viña's invitation kept) and the district report;
                  never a topic with the words of a deadline listed beside it (the next in the rotation instead).
  * Balance     — read.js deadlineLayout / dlCardHeight / textLines / dlHide: the numbers each card shows at each width
                  (an even number of rows where they run in two columns; four on a tablet),
                  the classes that hide the rest, community.css's bands equal to DL_BANDS.
  * Rendered    — Share your story built in memory from data of its own: Grapevine's tiles say why they are there ("In
                  every issue" / "Always needed", in both languages), never "Record a story on this topic"; its note
                  names its topics; the rows and tiles carry their widths' classes.
The page in a real browser (both cards end together at 1024–1920px): tests/browser/test_r13_u1_deadline_cards.py.

    python -m unittest tests.test_r13_u1_gvtopics -v
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.sync import editorial as E  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "editorial"
GV = "https://www.aagrapevine.org/contribute"
TODAY = date(2026, 10, 16)
TOPICS = [("Emotional Sobriety", "department"), ("Sponsorship", "department"), ("Newcomers", "department"),
          ("Youth Enjoying Sobriety", "department"), ("Old-Timers", "department"), ("Home Group", "department"),
          ("Steps 4–12", "always_needed"), ("Every Tradition", "always_needed")]
SPANISH = {"Emotional Sobriety": "Sobriedad emocional", "Sponsorship": "Apadrinamiento", "Newcomers": "Recién llegados",
           "Youth Enjoying Sobriety": "Jóvenes que disfrutan de la sobriedad", "Old-Timers": "Veteranos",
           "Home Group": "Grupo base", "Steps 4–12": "Pasos 4 a 12", "Every Tradition": "Cada una de las Tradiciones"}
CALENDAR = ("<h4>Grapevine Editorial Calendar 2027</h4><ul><li><strong>JANUARY</strong><br><em>Spiritual Awakenings "
            "(stories due June 1, 2026)</em><br>Share your journey.</li><li><strong>JUNE</strong><br><em>Emotional Sobriety "
            "(stories due Nov. 1, 2026)</em><br>Serenity.</li></ul>")


def fx(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def page(intro: str = "", calendar: str = CALENDAR) -> str:
    return f"<html><body><main><article class='node--type-page'>{intro}{calendar}</article></main></body></html>"


def topics(html: str) -> list[tuple[str, str]]:
    rows, _ = E.parse_gv(html, GV)
    return [(r["theme"], r["topic_type"]) for r in rows if not r["issue_year"]]


DEPTS = ("<p class='subcopy'>Each month, Grapevine publishes stories on special topics as well as for departments such as "
         "{list}. Each issue also includes a story on the Traditions and the Steps.</p>")
NOTE = "<p class='subcopy'><strong>NOTE:</strong> We are always in need of stories {rest}. Thanks!</p>"


# ---------------------------------------------------------------------------------------------------------- parser
class Parser(unittest.TestCase):
    def test_the_real_page(self):
        rows, meta = E.parse_gv(fx("gv_contribute.html"), GV)
        dated = [r for r in rows if r["issue_year"]]
        self.assertEqual(len(dated), 26)                                           # the calendar, as before
        self.assertEqual(topics(fx("gv_contribute.html")), TOPICS)
        self.assertNotIn("no_topics", meta)
        items = E.rows_to_items(rows, "gv", GV, meta)
        ev = [i for i in items if i["extra"]["evergreen"]]
        self.assertEqual([i["id"] for i in ev], ["ed:gv:any:emotional-sobriety", "ed:gv:any:sponsorship", "ed:gv:any:newcomers",
                                                 "ed:gv:any:youth-enjoying-sobriety", "ed:gv:any:old-timers",
                                                 "ed:gv:any:home-group", "ed:gv:any:steps-4-12", "ed:gv:any:every-tradition"])
        for i in ev:
            with self.subTest(i["id"]):
                self.assertEqual((i["kind"], i["source"], i["category"], i["lang"], i["date"], i["summary"]),
                                 ("topic", "grapevine", "gv", "en", None, ""))
                self.assertEqual(i["extra"]["publication"], "gv")
                self.assertNotIn("issue_key", i["extra"])
                self.assertNotIn("deadline", i["extra"])
                self.assertIn(i["extra"]["topic_type"], ("department", "always_needed"))
        # the dated June 2027 theme and the department are two items
        self.assertIn("ed:gv:2027-06:emotional-sobriety", [i["id"] for i in items])
        # keep_window keeps the topics (no issue) with the issues in the window
        kept = E.keep_window(items, TODAY)
        self.assertEqual(sum(1 for i in kept if i["extra"]["evergreen"]), 8)

    def test_the_names_tidied(self):
        cases = {
            "Emotional Sobriety, Sponsorship, Newcomers, Youth Enjoying Sobriety, Old-Timers and Home Group": TOPICS[:6],
            "Emotional Sobriety, Sponsorship, Newcomers, Youth Enjoying Sobriety, Old-Timers, and Home Group": TOPICS[:6],
            "Emotional Sobriety, Sponsorship, Newcomers, Youth Enjoying Sobriety, Old-Timers &amp; Home Group": TOPICS[:6],
            "“Emotional Sobriety”, ‘Sponsorship’ and \"Home Group\"": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "Emotional&nbsp;Sobriety, Sponsorship&nbsp;and&nbsp;Home Group": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "Young &amp; Sober, Sponsorship and Home Group": [("Young & Sober", "department"), TOPICS[1], TOPICS[5]],
            # (the review, October 2026: rewordings an AA page could use — never a tile the page does not name)
            "A.A. Around the World, Sponsorship and Home Group": [("AA Around the World", "department"), TOPICS[1], TOPICS[5]],
            "A. A. Around the World and Home Group": [("AA Around the World", "department"), TOPICS[5]],
            "Emotional Sobriety, Sponsorship, and Home Group, etc": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "Emotional Sobriety, Sponsorship and Home Group (to name a few)": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "Emotional Sobriety, Sponsorship, Home Group and more": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "Emotional Sobriety, Sponsorship, Home Group, to name a few": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "Emotional Sobriety, Sponsorship and Home Group, among others": [TOPICS[0], TOPICS[1], TOPICS[5]],
            "“Sponsorship” and “Home Group.”": [TOPICS[1], TOPICS[5]],                 # the stop inside the quote
            # (the release review, October 2026: words that name nothing at the end of the last name, no comma before
            # them; what is inside brackets is never split)
            "Emotional Sobriety, Old-Timers and Home Group and more": [TOPICS[0], TOPICS[4], TOPICS[5]],
            "Emotional Sobriety, Old-Timers and Home Group etc": [TOPICS[0], TOPICS[4], TOPICS[5]],
            "Emotional Sobriety, Old-Timers and Home Group and many others": [TOPICS[0], TOPICS[4], TOPICS[5]],
            "Sponsorship, Home Group (meetings, service)": [TOPICS[1], TOPICS[5]],
            "Sponsorship and Home Group (meetings and service)": [TOPICS[1], TOPICS[5]],
        }
        for text, want in cases.items():
            with self.subTest(text):
                self.assertEqual(topics(page(DEPTS.format(list=text))), want)
        notes = {
            "of your experience on Steps 4—12 and on every Tradition": TOPICS[6:],      # the page's own em dash
            "of your experience on Steps 4-12 and on every Tradition": TOPICS[6:],
            "of your experience on Steps 4 – 12, and every Tradition": TOPICS[6:],
            "on Steps 4–12 &amp; every Tradition": TOPICS[6:],
            "about your experiences with Steps 4‑12 and every Tradition": TOPICS[6:],
            "of your experience on Steps 4-12 and on every Tradition (1-12)": TOPICS[6:],
            "of your experience on Steps 4 through 12 and on every Tradition": TOPICS[6:],
        }
        for text, want in notes.items():
            with self.subTest(text):
                self.assertEqual(topics(page(NOTE.format(rest=text))), want)

    def test_only_what_the_page_names(self):
        # "always looking for innovative material" is not a topic; nor is "the Traditions and the Steps"
        intro = ("<p>The editors are always looking for innovative material, as long as it relates to AA experience.</p>"
                 "<p>Each issue also includes a story on the Traditions and the Steps.</p>")
        self.assertEqual(topics(page(intro)), [])
        # a name in both lists counts once (as a department)
        both = DEPTS.format(list="Sponsorship and Home Group") + NOTE.format(rest="on Sponsorship and on every Tradition")
        self.assertEqual(topics(page(both)), [TOPICS[1], TOPICS[5], TOPICS[7]])
        # pieces that name nothing: no tile, the rest of the list read
        for rest in ("e.g. and so on", "many others", "etc."):
            with self.subTest(rest):
                self.assertEqual(topics(page(DEPTS.format(list=f"Sponsorship, {rest}"))), [TOPICS[1]])
        # a sentence-long "name", or one too short to be a name ("AA"): the list is not read at all (the release
        # review: all or nothing — test_a_list_worded_differently)
        long = DEPTS.format(list="Sponsorship and " + "a very long run of words that the page wrote differently " * 2)
        self.assertEqual(topics(page(long)), [])
        for rest in ("A.A.", "AA, etc"):
            with self.subTest(rest):
                self.assertEqual(topics(page(DEPTS.format(list=f"Sponsorship, {rest}"))), [])

    # (the release review, October 2026) rewordings Grapevine could make: each gave tiles that were parts of a sentence
    REWORDED = {
        "department": [
            "Emotional Sobriety, Sponsorship, Newcomers, Youth Enjoying Sobriety, Old-Timers and Home Group, which appear "
            "in most issues",
            "Emotional Sobriety, Sponsorship, Old-Timers and Home Group as well as stories on the Steps and Traditions",
            "Emotional Sobriety, Sponsorship and any topic you like",
            "Sponsorship, Home Group (meetings, service",
        ],
        "always_needed": [
            "on any topic",
            "about your experience, strength and hope",
            "of your experience on Steps 4—12 and on every Tradition, especially Traditions 6 and 7",
            "on Steps 4 and 5",
        ],
    }

    def test_a_list_worded_differently(self):
        """A list that is not all names written as titles is not read at all: no tile from it, the sentence noted —
        "Which appear in most issues", "Any topic", "Your experience", "Especially Traditions 6" are never topics."""
        for kind, lists in self.REWORDED.items():
            for text in lists:
                with self.subTest(kind=kind, text=text):
                    html = page(DEPTS.format(list=text) if kind == "department" else NOTE.format(rest=text))
                    rows, meta = E.parse_gv(html, GV)
                    self.assertEqual([r["theme"] for r in rows if not r["issue_year"]], [])
                    self.assertEqual([u["kind"] for u in meta["topics_unread"]], [kind])
                    self.assertNotIn("no_topics", meta)                           # the sentence is there
        # "departments: see our submission guidelines …" names nothing either
        rows, meta = E.parse_gv(page("<p>Our departments: see our submission guidelines for the full list.</p>"), GV)
        self.assertEqual([r for r in rows if not r["issue_year"]], [])
        self.assertEqual(meta["topics_unread"], [{"kind": "department",
                                                  "sentence": "departments: see our submission guidelines for the full list."}])
        # one list worded differently: the other is still read
        html = page(DEPTS.format(list=self.REWORDED["department"][0]) + NOTE.format(rest="of your experience on Steps 4—12 and on every Tradition"))
        self.assertEqual(topics(html), TOPICS[6:])

    def test_a_list_worded_differently_keeps_its_previous_topics(self):
        """collect: that list's previous topics stay (unchanged, first_seen too), the other list and the calendar are
        read as usual, and /status/ quotes the sentence."""
        def topic(slug, title, kind):
            return {"id": f"ed:gv:any:{slug}", "source": "grapevine", "kind": "topic", "url": GV, "title": title,
                    "summary": "", "lang": "en", "date": None, "first_seen": "2026-10-16T07:00:00Z", "status": "ok",
                    "category": "gv", "extra": {"publication": "gv", "theme": title, "evergreen": True, "topic_type": kind}}
        prev = [topic(slug, title, kind) for (title, kind), slug in zip(TOPICS, ("emotional-sobriety", "sponsorship", "newcomers",
                "youth-enjoying-sobriety", "old-timers", "home-group", "steps-4-12", "every-tradition"))]
        reworded = self.REWORDED["department"][0]
        html = page(DEPTS.format(list=reworded) + NOTE.format(rest="of your experience on Steps 4—12, and every Tradition, and Sponsorship"))
        res = E.collect(lambda url: html if url == GV else None, lambda url: [], prev, TODAY, only="gv")
        self.assertEqual(res["errors"], [])
        self.assertEqual(res["refreshed"], {"gv"})
        fresh = [(i["title"], i["extra"]["topic_type"]) for i in res["fresh"] if i["extra"]["evergreen"]]
        self.assertEqual(fresh, [*TOPICS[6:], ("Sponsorship", "always_needed")])
        # the departments carried over unchanged — five of the six: "Sponsorship" comes once, from today's note
        kept = [i for i in res["kept"] if i["extra"]["evergreen"]]
        self.assertEqual([i["title"] for i in kept], ["Emotional Sobriety", "Newcomers", "Youth Enjoying Sobriety", "Old-Timers",
                                                      "Home Group"])
        self.assertTrue(all(i is p for i, p in zip(kept, [prev[0], *prev[2:6]])))
        self.assertEqual(res["stats"]["gv"]["topics"], 3)
        self.assertEqual(len(res["stats"]["warnings"]), 1)
        note = res["stats"]["warnings"][0]
        self.assertTrue(note.startswith('gv: suggested topics not read — the departments sentence ("departments such as …") '
                                        "changed: “departments such as Emotional Sobriety,"), note)
        self.assertIn("which appear in most issues", note)
        self.assertTrue(note.endswith("” — its 5 earlier topic(s) stay"), note)
        # the first day (nothing to keep): no tile, and the note says so
        res = E.collect(lambda url: html if url == GV else None, lambda url: [], [], TODAY, only="gv")
        self.assertEqual([i["title"] for i in res["fresh"] + res["kept"] if i["extra"]["evergreen"]],
                         ["Steps 4–12", "Every Tradition", "Sponsorship"])
        self.assertTrue(res["stats"]["warnings"][0].endswith("” — no earlier topics of it to keep"), res["stats"]["warnings"])

    def test_never_a_themes_prompt(self):
        """Only the introduction is read: with the NOTE gone, July's prompt ("We are always looking for stories about
        prison sponsorship and correspondence service.") is not a topic."""
        july = ("<h4>Grapevine Editorial Calendar 2027</h4><ul><li><strong>JULY</strong><br><em>Annual Prison Issue (stories due "
                "Dec. 1, 2026)</em><br>We are always looking for stories about prison sponsorship and correspondence service.</li></ul>")
        rows, meta = E.parse_gv(page(DEPTS.format(list="Sponsorship and Home Group"), calendar=july), GV)
        self.assertEqual([(r["theme"], r["topic_type"]) for r in rows if not r["issue_year"]], [TOPICS[1], TOPICS[5]])
        self.assertEqual(rows[0]["theme"], "Annual Prison Issue")
        self.assertNotIn("topics_unread", meta)
        rows, meta = E.parse_gv(page(calendar=july), GV)
        self.assertEqual([r for r in rows if not r["issue_year"]], [])
        self.assertTrue(meta["no_topics"])

    def test_the_sentences_gone(self):
        rows, meta = E.parse_gv(page(), GV)
        self.assertEqual(len(rows), 2)
        self.assertTrue(meta.get("no_topics"))
        res = E.collect(lambda url: page() if url == GV else None, lambda url: [], [], TODAY, only="gv")
        self.assertEqual(res["errors"], [])                                         # not an error …
        self.assertEqual(res["refreshed"], {"gv"})
        self.assertEqual(res["stats"]["gv"]["topics"], 0)
        self.assertEqual(len(res["stats"]["warnings"]), 1)                          # … a note for /status/
        self.assertIn("no suggested topics", res["stats"]["warnings"][0])

    def test_topics_without_a_calendar(self):
        prev = [{"id": "ed:gv:2027-06:emotional-sobriety", "kind": "topic", "title": "Emotional Sobriety", "category": "gv",
                 "extra": {"publication": "gv", "issue_key": "2027-06", "deadline": "2026-11-01", "evergreen": False}}]
        html = page(DEPTS.format(list="Sponsorship and Home Group"), calendar="")
        res = E.collect(lambda url: html if url == GV else None, lambda url: [], prev, TODAY, only="gv")
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("gv: no themes found", res["errors"][0])
        self.assertEqual(res["fresh"], [])
        self.assertEqual([i["id"] for i in res["kept"]], [prev[0]["id"]])

    def test_the_part_is_authoritative(self):
        """A good read of the page replaces Grapevine's topics like its themes: a topic the page no longer names leaves
        the site, one it still names keeps its first day; La Viña's topics are not touched."""
        def topic(pub, slug, title, first="2026-10-01T07:00:00Z"):
            return {"id": f"ed:{pub}:any:{slug}", "source": "grapevine" if pub == "gv" else "lavina", "kind": "topic",
                    "url": GV, "title": title, "summary": "", "lang": "en" if pub == "gv" else "es", "date": None,
                    "first_seen": first, "last_seen": first, "image": None, "tags": [], "category": pub, "status": "ok",
                    "extra": {"publication": pub, "theme": title, "evergreen": True}}
        prev = [topic("gv", "sponsorship", "Sponsorship", "2026-09-01T07:00:00Z"), topic("gv", "dear-grapevine", "Dear Grapevine"),
                topic("lv", "mi-primer-paso", "Mi Primer Paso")]
        saved: dict = {}

        def save(source, items, ok=True, error=None, stats=None, extra=None):
            saved.update(items=items, ok=ok, stats=stats)
        with mock.patch.object(E, "load_raw", return_value={"items": prev}), \
                mock.patch.object(E, "save_raw", side_effect=save), mock.patch.object(E, "_today_central", return_value=TODAY):
            E.main(["--only", "gv", "--gv-html", str(FIX / "gv_contribute.html")])
        self.assertTrue(saved["ok"])
        ids = {i["id"]: i for i in saved["items"]}
        self.assertNotIn("ed:gv:any:dear-grapevine", ids)                         # the page no longer names it
        self.assertEqual(ids["ed:gv:any:sponsorship"]["first_seen"], "2026-09-01T07:00:00Z")
        self.assertEqual(ids["ed:gv:any:sponsorship"]["extra"]["topic_type"], "department")
        self.assertIn("ed:lv:any:mi-primer-paso", ids)                             # La Viña's part: untouched
        self.assertEqual(sum(1 for i in saved["items"] if i["extra"].get("publication") == "gv" and i["extra"].get("evergreen")), 8)
        self.assertEqual(saved["stats"]["gv"]["topics"], 8)
        self.assertNotIn("warnings", saved["stats"])


# --------------------------------------------------------------------------------------------------------- Spanish
class Spanish(unittest.TestCase):
    def test_every_topic_has_hand_written_spanish(self):
        from scripts.sync import translate as T
        ov = T.Overrides.load()
        self.assertIsNone(ov.error)
        names = [t for t, _ in topics(fx("gv_contribute.html"))]
        self.assertEqual({n: ov.get(n, "es") for n in names}, SPANISH)
        # the translator build_data runs (overrides first, never the machine's words) gives exactly these
        tr = T.Translator(cache=False, use_model=False, glossary_path=ROOT / "nonexistent.yml")
        self.assertEqual(tr.translate(names, "en", "es"), [(SPANISH[n], False) for n in names])


# ------------------------------------------------------------------------------------------------- the site's code
def gv_topic(title: str, kind: str, es: str | None = None) -> dict:
    it = {"id": f"ed:gv:any:{E.slugify(title.replace('–', '-'), 48)}", "source": "grapevine", "kind": "topic", "url": GV,
          "title": title, "summary": "", "lang": "en", "status": "ok", "category": "gv",
          "extra": {"publication": "gv", "theme": title, "evergreen": True, "topic_type": kind}, "machine": []}
    it["i18n"] = {"title": {"en": title, "es": es or SPANISH.get(title, title)}}
    return it


def dated(pub: str, title: str, deadline: str, issue: str, en: str = "", es: str = "") -> dict:
    lv = pub == "lv"
    return {"id": f"ed:{pub}:{issue}:{E.slugify(title, 48)}", "source": "lavina" if lv else "grapevine", "kind": "topic",
            "url": "https://example.org", "title": title, "summary": "", "lang": "es" if lv else "en", "status": "ok",
            "category": pub, "machine": [], "i18n": {"title": {"en": en or title, "es": es or title}},
            "extra": {"publication": pub, "theme": title, "evergreen": False, "issue_key": issue, "deadline": deadline}}


def lv_topic(title: str, en: str) -> dict:
    return {"id": f"ed:lv:any:{E.slugify(title, 48)}", "source": "lavina", "kind": "topic", "url": "https://example.org",
            "title": title, "summary": "", "lang": "es", "status": "ok", "category": "lv", "machine": ["en"],
            "i18n": {"title": {"en": en, "es": title}}, "extra": {"publication": "lv", "theme": title, "evergreen": True}}


GV_TOPICS = [gv_topic(t, k) for t, k in TOPICS]
LV_TOPICS = [lv_topic(f"Tema número {i}", f"Topic number {i}") for i in range(19)]
GV_DATED = [dated("gv", "Emotional Sobriety", "2026-11-01", "2027-06", es="Sobriedad emocional"),
            dated("gv", "Annual Prison Issue", "2026-12-01", "2027-07"), dated("gv", "Sober Seniors", "2027-01-01", "2027-08"),
            dated("gv", "Young & Sober", "2027-02-01", "2027-09"), dated("gv", "AA in the Military", "2027-03-01", "2027-10"),
            dated("gv", "Sober Holidays!", "2027-05-01", "2027-12"), dated("gv", "Remote Communities", "2027-05-01", "2027-12")]
LV_DATED = [dated("lv", "Recaídas", "2026-10-17", "2027-05", en="Relapses"), dated("lv", "Prisiones", "2026-12-15", "2027-07", en="Prisons")]
NOW = "2026-10-16T15:00:00Z"


class Consumers(unittest.TestCase):
    def test_the_editorial_view_and_the_recorders_list(self):
        r = run_js(self, r"""
          const res = {};
          for (const lang of ["en", "es"]) {
            const gv = filters.readEditorial(input.items, "gv", lang), lv = filters.readEditorial(input.items, "lv", lang);
            res[lang] = { ev: gv.evergreen.map((v) => [v.theme, v.topicType, v.original, v.themeLang]),
                          next: gv.upcoming[0].theme, lvTypes: lv.evergreen.map((v) => v.topicType),
                          rec: filters.readRecTopics({ gv, lv }).gv.map((o) => [o.t, o.dated]) };
          }
          out(res);""", data={"items": GV_DATED + GV_TOPICS + LV_DATED + LV_TOPICS}, now=NOW)
        en, es = r["en"], r["es"]
        # what Grapevine always needs first, then its departments — alphabetical in the page's language
        self.assertEqual([tuple(x[:2]) for x in en["ev"]], [("Every Tradition", "always_needed"), ("Steps 4–12", "always_needed"),
            ("Emotional Sobriety", "department"), ("Home Group", "department"), ("Newcomers", "department"),
            ("Old-Timers", "department"), ("Sponsorship", "department"), ("Youth Enjoying Sobriety", "department")])
        self.assertEqual([x[0] for x in es["ev"]], ["Cada una de las Tradiciones", "Pasos 4 a 12", "Apadrinamiento", "Grupo base",
            "Jóvenes que disfrutan de la sobriedad", "Recién llegados", "Sobriedad emocional", "Veteranos"])
        # on the Spanish page Grapevine's own words under each (lang "en"), as La Viña's on the English page
        self.assertTrue(all(x[2] and x[3] == "es" for x in es["ev"]))
        self.assertTrue(all(not x[2] and x[3] == "en" for x in en["ev"]))
        self.assertEqual(set(en["lvTypes"]), {""})                                 # La Viña's topics have no type
        # the dated "Emotional Sobriety" is the next deadline and the department is a topic: both
        self.assertEqual(en["next"], "Emotional Sobriety")
        self.assertIn(("Emotional Sobriety", "department"), [tuple(x[:2]) for x in en["ev"]])
        # the recorder: the coming themes, then Grapevine's topics ("Ideas: Grapevine's suggested topics"), each once
        rec = en["rec"]
        self.assertEqual([t for t, d in rec if d][:2], ["Emotional Sobriety", "Annual Prison Issue"])
        self.assertEqual([t for t, d in rec if not d], ["Every Tradition", "Steps 4–12", "Home Group", "Newcomers", "Old-Timers",
                                                        "Sponsorship", "Youth Enjoying Sobriety"])
        groups = json.loads((ROOT / "src" / "_i18n" / "community.json").read_text(encoding="utf-8"))
        self.assertEqual(groups["community.recorder.tp_group_gv_topics"]["en"], "Ideas: Grapevine's suggested topics")

    def test_home_turns_each_magazines_topics_on_its_own(self):
        r = run_js(self, r"""
          const pick = (items) => filters.homeThemes(items, 4).map((t) => t.id);
          out({ both: pick(input.both), lvOnly: pick(input.lvOnly), gvTopicsOnly: pick(input.gvTopicsOnly) });""",
                   data={"both": GV_DATED + GV_TOPICS + LV_DATED + LV_TOPICS, "lvOnly": GV_DATED + LV_DATED + LV_TOPICS,
                         "gvTopicsOnly": GV_TOPICS + LV_DATED + LV_TOPICS}, now=NOW)
        # Grapevine has coming themes: they take its places; La Viña's picks are the same as without Grapevine's topics
        self.assertEqual(r["both"], r["lvOnly"])
        self.assertFalse([i for i in r["both"] if i.startswith("ed:gv:any:")])
        # no coming Grapevine theme: its suggested topics invite instead
        self.assertEqual(sum(1 for i in r["gvTopicsOnly"] if i.startswith("ed:gv:any:")), 2)

    def test_the_monthly_toolkit_and_the_district_report(self):
        from test_monthly import NOW_A, full_db, run
        db = full_db()
        db["editorial"]["items"] += GV_TOPICS
        res = run(self, [("a", NOW_A, "2026-10"), ("b", NOW_A, "2026-11")], db=db)
        a, b = res["a"], res["b"]
        en = a["mm"]["en"]["gvTopics"]
        self.assertEqual(len(en), 3)                                               # 3 a month, like La Viña's
        self.assertEqual(sorted(sorted(x) for x in en), [["en", "id", "machine", "text", "textLang"]] * 3)
        self.assertTrue(all(x["text"] == x["en"] and x["textLang"] == "en" for x in en))
        es = a["mm"]["es"]["gvTopics"]
        self.assertEqual([x["text"] for x in es], [SPANISH[x["en"]] for x in es])
        self.assertTrue(all(x["textLang"] == "es" and not x["machine"] for x in es))
        self.assertNotEqual([x["id"] for x in en], [x["id"] for x in b["mm"]["en"]["gvTopics"]])   # another 3 in November
        self.assertEqual(len(a["mm"]["en"]["lvTopics"]), 3)                        # La Viña's as before
        wa = a["msg"]["en:whatsapp"]
        line = next(x for x in wa.split("\n") if "Grapevine — no deadline:" in x)
        self.assertEqual(line, "• Grapevine — no deadline: " + ", ".join(f"“{x['en']}”" for x in en))
        self.assertLess(wa.index("Grapevine — no deadline:"), wa.index("La Viña — no deadline, in Spanish:"))
        both = a["msg"]["es+en:whatsapp"]
        self.assertIn("• Grapevine — sin fecha límite, en inglés: " + ", ".join(f"“{SPANISH[x['en']]} / {x['en']}”" for x in en), both)

        r = run_js(self, r"""
          const R = await imp("eleventy/filters/report.js");
          const site = (await imp("src/_data/site.js")).default();
          const carry = (await imp("src/_data/carry.js")).default();
          const m = R.reportModel(input.db, input.meeting, carry, site, new Date(input.now));
          out({ en: m.langs.en.sections.find((s) => s.id === "deadlines").text, es: m.langs.es.sections.find((s) => s.id === "deadlines").text });""",
                   data={"db": self.report_db(), "meeting": {"next": {"ymd": "2026-10-21", "start": "2026-10-22T00:00:00Z",
                         "end": "2026-10-22T01:00:00Z"}, "rule": {"weekday": 3, "n": 3, "start": "19:00", "end": "20:00"}},
                         "now": NOW_A})
        for lang, head in (("en", "Grapevine — suggested topics (any time):"), ("es", "Grapevine (en inglés) — temas sugeridos (sin fecha límite):")):
            with self.subTest(lang=lang):
                text = r[lang]
                self.assertIn(head, text)
                after = text.split(head, 1)[1].strip().split("\n")[:3]
                self.assertTrue(all(x.startswith("• “") for x in after), after)
                if lang == "es":                                                   # its own English words after the Spanish
                    self.assertRegex(after[0], r"^• “[^”]+” \(“[^”]+”\)$")
                gv_at = text.index("Grapevine")
                self.assertLess(gv_at, text.index(head))

    def test_a_topic_is_never_a_deadline_beside_it(self):
        """The release review (October 2026): October's toolkit read "Emotional Sobriety — For the June 2027 issue —
        stories due Nov 1, 2026" and then "Any time, Grapevine is looking for stories about: Steps 4–12, Youth Enjoying
        Sobriety, Emotional Sobriety" ("Sobriedad emocional" twice on /es/). A suggested topic with the words of a
        deadline listed beside it — case, accents and punctuation aside, in either language — gives its place to the
        next one in the rotation (monthly.js monthTopics): still 3, the same in English and Spanish, on the page and the
        poster (the model), in the message and in the district report (against the themes the report lists); La Viña's
        the same way. A month without such a deadline keeps its three; /contribute/ keeps both on purpose
        (test_the_editorial_view_and_the_recorders_list)."""
        from test_monthly import NOW_A, full_db, item, run
        steps, youth, emotional, tradition, home = ("ed:gv:any:steps-4-12", "ed:gv:any:youth-enjoying-sobriety",
                                                    "ed:gv:any:emotional-sobriety", "ed:gv:any:every-tradition", "ed:gv:any:home-group")
        recaidas = dict(lv_topic("Recaídas", "Relapses"), id="ed:lv:t1-recaidas")      # in October's window of La Viña's
        lv_due = dated("lv", "RECAIDAS", "2026-10-17", "2027-05", en="Relapses")          # due October 17

        def gv_due(title: str, es: str) -> dict:  # Grapevine's June 2027 theme, due October 15 (full_db's, worded otherwise)
            return item("ed:gv:2027-06", "topic", title=title, source="grapevine",
                        extra={"publication": "gv", "issue_key": "2027-06", "deadline": "2026-10-15"},
                        i18n={"title": {"en": title, "es": es}})

        def db_with(*dated_items) -> dict:
            db = full_db()
            db["editorial"]["items"] = [i for i in db["editorial"]["items"] if i["id"] != "ed:gv:2027-06"] + \
                list(dated_items) + GV_TOPICS + [recaidas]
            return db

        def picks(res: dict, pub: str) -> list[str]:
            ids = {lang: [x["id"] for x in res["mm"][lang][pub]] for lang in ("en", "es")}
            self.assertEqual(ids["en"], ids["es"])                                 # the same three in both languages
            return ids["en"]

        # nothing due beside them: October's rotation is Steps 4–12, Youth Enjoying Sobriety, Emotional Sobriety
        bare = run(self, [("oct", NOW_A, "2026-10"), ("nov", NOW_A, "2026-11")], db=db_with())
        self.assertEqual(picks(bare["oct"], "gvTopics"), [steps, youth, emotional])
        self.assertIn("ed:lv:t1-recaidas", picks(bare["oct"], "lvTopics"))
        # due beside them, however it is written: the next in the rotation instead, still 3
        for title, es in (("Emotional Sobriety", "Sobriedad emocional"), ("EMOTIONAL  sobriety!", "Sobriedad Emocional"),
                          ("Balance in Recovery", "Sobriedad emocional")):           # (the same words in Spanish only)
            with self.subTest(theme=title):
                res = run(self, [("oct", NOW_A, "2026-10"), ("nov", NOW_A, "2026-11")], db=db_with(gv_due(title, es), lv_due))
                oct_ = res["oct"]
                self.assertEqual([d["id"] for d in oct_["mm"]["en"]["deadlines"]][:1], ["ed:gv:2027-06"])
                self.assertEqual(picks(oct_, "gvTopics"), [steps, youth, tradition])
                lv = picks(oct_, "lvTopics")
                self.assertEqual(len(lv), 3)
                self.assertNotIn("ed:lv:t1-recaidas", lv)
                self.assertEqual(lv, [i for i in picks(bare["oct"], "lvTopics") if i != "ed:lv:t1-recaidas"] + ["ed:lv:t3"])
                # the message: the theme once, in its deadline's line — never again among the topics
                en, es_msg = oct_["msg"]["en:whatsapp"], oct_["msg"]["es:whatsapp"]
                topics_en = next(x for x in en.split("\n") if "Grapevine — no deadline:" in x)
                self.assertEqual(topics_en, "• Grapevine — no deadline: “Steps 4–12”, “Youth Enjoying Sobriety”, “Every Tradition”")
                topics_es = next(x for x in es_msg.split("\n") if "Grapevine — sin fecha límite, en inglés:" in x)
                self.assertNotIn("Sobriedad emocional", topics_es)
                self.assertEqual(es_msg.count("Sobriedad emocional"), 1 if es == "Sobriedad emocional" else 0)
                self.assertNotIn("Recaídas", next(x for x in en.split("\n") if "La Viña — no deadline, in Spanish:" in x))
                # November (nothing of the kind due): its three as without the deadline
                self.assertEqual(picks(res["nov"], "gvTopics"), picks(bare["nov"], "gvTopics"))

        # the district report: against the themes IT lists (Grapevine's next 3, La Viña's next 2) — here also Steps
        # 4–12, due December 1 (after October, so not on the toolkit's card, which keeps it)
        db = self.report_db()
        db["editorial"]["items"] += [recaidas,
            item("ed:gv:2027-06", "topic", title="Emotional Sobriety", source="grapevine", i18n={"title": {"en": "Emotional Sobriety", "es": "Sobriedad emocional"}},
                 extra={"publication": "gv", "issue_key": "2027-06", "deadline": "2026-11-01"}),
            item("ed:gv:2027-07", "topic", title="Steps 4-12", source="grapevine", i18n={"title": {"en": "Steps 4-12", "es": "Pasos 4 a 12"}},
                 extra={"publication": "gv", "issue_key": "2027-07", "deadline": "2026-12-01"})]
        r = run_js(self, r"""
          const R = await imp("eleventy/filters/report.js");
          const M = await imp("eleventy/filters/monthly.js");
          const site = (await imp("src/_data/site.js")).default();
          const carry = (await imp("src/_data/carry.js")).default();
          const m = R.reportModel(input.db, input.meeting, carry, site, new Date(input.now));
          out({ en: m.langs.en.sections.find((s) => s.id === "deadlines").text, es: m.langs.es.sections.find((s) => s.id === "deadlines").text,
                card: M.monthModel("2026-10", input.db, carry, site, "en", new Date(input.now)).gvTopics.map((x) => x.id) });""",
                   data={"db": db, "meeting": {"next": {"ymd": "2026-10-21", "start": "2026-10-22T00:00:00Z", "end": "2026-10-22T01:00:00Z"},
                                               "rule": {"weekday": 3, "n": 3, "start": "19:00", "end": "20:00"}}, "now": NOW_A})
        self.assertEqual(r["card"], [steps, youth, tradition])                    # the toolkit: only October's deadlines
        for lang, head, want in (("en", "Grapevine — suggested topics (any time):",
                                  ["• “Youth Enjoying Sobriety”", "• “Every Tradition”", "• “Home Group”"]),
                                 ("es", "Grapevine (en inglés) — temas sugeridos (sin fecha límite):",
                                  ["• “Jóvenes que disfrutan de la sobriedad” (“Youth Enjoying Sobriety”)",
                                   "• “Cada una de las Tradiciones” (“Every Tradition”)", "• “Grupo base” (“Home Group”)"])):
            with self.subTest(report=lang):
                text = r[lang]
                self.assertEqual(text.split(head, 1)[1].strip().split("\n")[:3], want)
                self.assertEqual(text.count("Emotional Sobriety" if lang == "en" else "Sobriedad emocional"), 1)   # its deadline's line
                self.assertEqual(text.count("Recaídas"), 1)                       # La Viña's dated theme, not again as a topic

    def test_a_machine_translated_topic_on_the_monthly_page(self):
        """The review (October 2026): a topic with no hand-written Spanish yet is a machine translation on /es/monthly/
        — marked as one, Grapevine's own words after it, and the site's note under the list, as its deadlines."""
        from test_monthly import NOW_A, full_db, run
        db = full_db()
        db["editorial"]["items"] += [dict(gv_topic("Dear Grapevine", "department", es="Querida Grapevine"), machine=["es"]),
                                     gv_topic("Sponsorship", "department")]
        es = run(self, [("a", NOW_A, "2026-10")], db=db)["a"]["mm"]["es"]["gvTopics"]
        tp = {x["en"]: x for x in es}
        self.assertEqual((tp["Dear Grapevine"]["text"], tp["Dear Grapevine"]["machine"]), ("Querida Grapevine", True))
        self.assertEqual((tp["Sponsorship"]["text"], tp["Sponsorship"]["machine"]), ("Apadrinamiento", False))
        month = (ROOT / "src" / "pages" / "monthly-month.njk").read_text(encoding="utf-8")
        card = month[month.index("{% set gvCard %}"):month.index("{% endset %}", month.index("{% set gvCard %}"))]
        self.assertIn('{% if tp.machine %} {{ mtMark | safe }} <span class="font-normal italic" lang="en">{{ tp.en }}</span>{% endif %}', card)
        self.assertIn('{% if m.gvTopics | selectattr("machine") | length %}{{ mtNote | safe }}{% endif %}', card)

    def test_the_english_poster(self):
        """The review (October 2026): the English poster names Grapevine's 3 topics of the month, as the Spanish poster
        names La Viña's — where its deadlines leave room (fewer than two: each comes with its prompt) and the poster
        stays roomy with them (posterGvTopics: three more lines on a fuller poster make all of its type smaller, and
        the release review found a "snug" one drops La Viña's invitation and a tip); never on the Spanish poster."""
        from test_monthly import CARRY, NOW_A, SITE, event, full_db
        db = full_db()
        db["editorial"]["items"] += GV_TOPICS
        # November with 0–10 more events: the month fills up (the release review: with 7 or 8 dates Grapevine's topics
        # made the roomy poster "snug", which drops La Viña's invitation and a tip)
        more_events = [event(f"ev:nov{d}", f"2026-11-{d:02d}T19:00:00Z", f"2026-11-{d:02d}T21:00:00Z", f"Workshop {d}")
                       for d in range(2, 30, 3)]
        r = run_js(self, r"""
          process.env.ONLY = "-none-";
          const M = await imp("eleventy/filters/monthly.js");
          const os = await import("node:os");
          const { Eleventy } = await import("@11ty/eleventy");
          const { db, site, carry } = input;
          const now = new Date(input.now);
          // November: a quiet month (one deadline); October: a busy one (7 dates, the Book of the Month …); November
          // with a second deadline: quiet, but its deadlines fill the block
          const en = M.monthModel("2026-11", db, carry, site, "en", now), es = M.monthModel("2026-11", db, carry, site, "es", now);
          const busy = M.monthModel("2026-10", db, carry, site, "en", now);
          const more = { id: "ed:gv:2027-09:young-sober", kind: "topic", title: "Young & Sober", source: "grapevine", status: "ok",
                         extra: { publication: "gv", issue_key: "2027-09", theme: "Young & Sober", deadline: "2026-11-20" } };
          const two = M.monthModel("2026-11", { ...db, editorial: { ...db.editorial, items: [...db.editorial.items, more] } },
                                   carry, site, "en", now);
          const filling = input.more.map((_, k) => {
            const m = M.monthModel("2026-11", { ...db, events: { items: [...db.events.items, ...input.more.slice(0, k + 1)] } },
                                   carry, site, "en", now);
            const without = M.monthModel("2026-11", { ...db, events: { items: [...db.events.items, ...input.more.slice(0, k + 1)] },
                                                     editorial: { ...db.editorial, items: db.editorial.items.filter((i) => !i.id.startsWith("ed:gv:any:")) } },
                                         carry, site, "en", now);
            return { dates: m.dates.length, deadlines: m.deadlines.length, topics: m.posterGvTopics, density: m.density, without: without.density };
          });
          const full = filling.find((f) => f.dates === 7);
          const seven = M.monthModel("2026-11", { ...db, events: { items: [...db.events.items, ...input.more.slice(0, filling.indexOf(full) + 1)] } },
                                     carry, site, "en", now);
          const cases = { en: { m: en, lang: "en" }, es: { m: es, lang: "es" }, busy: { m: busy, lang: "en" }, two: { m: two, lang: "en" },
                          seven: { m: seven, lang: "en" } };
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-poster-topics-"));
          try {
            const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js", config(cfg) {
              for (const [name, c] of Object.entries(cases)) {
                cfg.addTemplate(`mp-t-${name}.njk`, '{% import "macros/monthly.njk" as mp with context %}{{ mp.poster(m, lang, site, "t") }}',
                                { ...c, layout: false, permalink: `/mp-t-${name}/index.html`, eleventyExcludeFromCollections: true, sitemap: false });
              }
            } });
            const pages = await elev.toJSON();
            out({ html: Object.fromEntries(pages.filter((p) => /^\/mp-t-/.test(p.url || "")).map((p) => [p.url.slice(6, -1), p.content])),
                  flags: { en: en.posterGvTopics, es: es.posterGvTopics, busy: busy.posterGvTopics, two: two.posterGvTopics,
                           seven: seven.posterGvTopics },
                  density: { en: en.density, busy: busy.density, two: two.density, seven: seven.density },
                  deadlines: [en.deadlines.length, two.deadlines.length, seven.deadlines.length],
                  topics: en.gvTopics.map((x) => x.text), tips: en.tips.length, filling });
          } finally {
            fs.rmSync(dir, { recursive: true, force: true });
          }""", data={"db": db, "site": SITE, "carry": CARRY, "now": NOW_A, "more": more_events}, timeout=300)
        self.assertEqual(r["flags"], {"en": True, "es": False, "busy": False, "two": False, "seven": False})
        self.assertEqual(r["density"]["busy"], "dense")
        self.assertEqual(r["deadlines"], [1, 2, 1])
        self.assertNotEqual(r["density"]["two"], "dense")
        self.assertEqual(len(r["topics"]), 3)
        # with Grapevine's topics the poster is still roomy: La Viña's invitation and every tip (up to three) stay
        self.assertEqual(r["density"]["en"], "roomy")
        mj = json.loads((ROOT / "src" / "_i18n" / "monthly.json").read_text(encoding="utf-8"))
        words, nudge = mj["monthly.gv_topics"], mj["monthly.lv_nudge"]["en"].split("{email}")[0]
        self.assertIn('<p class="mp-send mp-send--lv">' + nudge.replace("'", "&#39;"), r["html"]["en"])
        self.assertEqual(r["html"]["en"].count('class="mp-tip-t"'), min(3, r["tips"]))
        # filling November up: the topics are on the poster only while it stays roomy — never what makes it snug —
        # and come off once they would (7 dates); the month with them is as dense as without them
        fill = r["filling"]
        self.assertGreaterEqual(len(fill), 8, fill)
        for f in fill:
            with self.subTest(dates=f["dates"]):
                self.assertEqual(f["deadlines"], 1)
                if f["topics"]:
                    self.assertEqual(f["density"], "roomy")
                self.assertEqual(f["density"], f["without"])
        self.assertTrue(fill[0]["topics"], fill)
        self.assertIn(False, [f["topics"] for f in fill if f["without"] == "roomy"], "the guard: roomy without, no room with")
        self.assertEqual(next(f for f in fill if f["dates"] == 7)["topics"], False)
        story = re.search(r'<section class="mp-b mp-story">(.*?)</section>', r["html"]["en"], re.S).group(1)
        self.assertIn(f'<p class="mp-sub">{words["en"]}</p>', story)
        self.assertEqual(re.findall(r'<ul class="mp-topics">\s*(.*?)\s*</ul>', story, re.S),
                         ["".join(f"<li>{t}</li>" for t in r["topics"]).replace("&", "&amp;")])
        for name in ("es", "busy", "two", "seven"):
            with self.subTest(poster=name):
                self.assertNotIn(words["en"], r["html"][name])
                self.assertNotIn(words["es"], r["html"][name])

    @staticmethod
    def report_db() -> dict:
        from test_report import full_db
        db = full_db()
        db["editorial"]["items"] += GV_TOPICS
        return db


# ---------------------------------------------------------------------------------------------- the cards' balance
LAYOUT_JS = r"""
const R = await imp("eleventy/filters/read.js");
const res = {};
for (const lang of ["en", "es"]) {
  const gv = filters.readEditorial(input.items, "gv", lang), lv = filters.readEditorial(input.items, "lv", lang);
  res[lang] = filters.readDlLayout(gv, lv, lang);
}
res.bands = R.DL_BANDS;
res.stacked = R.DL_STACKED_WIDE;
res.lines = [R.textLines("Record a story on this topic", 9.8, 0.75, 1.03), R.textLines("Record a story on this topic", 16, 0.75, 1.03),
             R.textLines("", 10, 1, 1), R.textLines("Mis viejos amigos, mis nuevos amigos", 15.86, 0.875, 1.03)];
res.hide = [R.dlHide(3, { n: 3, a: 5, b: 3 }), R.dlHide(3, { n: 3, a: 5, b: 3 }, true), R.dlHide(6, { n: 3, a: 7 }, true),
            R.dlHide(6, { n: 3, a: 5 }, true), R.dlHide(0, { n: 3 })];
const ed = { pub: "gv", ...filters.readEditorial(input.items, "gv", "en") };
const words = { note: "x ".repeat(100), sub: "No deadline", forIssue: () => "For the June 2027 issue", due: "due in 100 days", action: () => "Always needed" };
res.taller = [R.dlCardHeight(ed, 38, 3, 8, words), R.dlCardHeight(ed, 38, 6, 8, words), R.dlCardHeight(ed, 30, 3, 8, words)];
const parts = {};
R.dlCardHeight(ed, 38, 3, 8, words, parts);
res.parts = parts;
out(res);
"""


class Balance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = GV_DATED + GV_TOPICS + LV_DATED + LV_TOPICS

    def layout(self, items=None):
        return run_js(self, LAYOUT_JS, data={"items": items or self.items}, now=NOW)

    def test_the_numbers_each_card_shows(self):
        r = self.layout()
        bands = [b["band"] for b in r["bands"]]
        self.assertEqual(bands, ["a", "b", "c", "d", "e", "f"])
        for lang in ("en", "es"):
            for pub, rest, ev in (("gv", 6, 8), ("lv", 1, 19)):
                lay = r[lang][pub]
                with self.subTest(lang=lang, pub=pub):
                    self.assertEqual(sorted(lay["rows"]), sorted(["n", "m", *bands]))
                    self.assertEqual((lay["rows"]["n"], lay["tiles"]["n"]), (min(3, rest), 8))   # one under the other
                    self.assertEqual((lay["rows"]["m"], lay["tiles"]["m"]), (min(4, rest), 8))   # … rows in two columns
                    for band in bands:
                        rows, tiles = lay["rows"][band], lay["tiles"][band]
                        # never a "Show all" that holds back one row, or fewer than three topics
                        self.assertTrue(rows == rest or 2 <= rows <= rest - 2, (band, rows))
                        self.assertTrue(tiles == ev or (tiles % 2 == 0 and 8 <= tiles <= min(14, ev - 3)), (band, tiles))
                        # where the rows run in two columns (a card from 42rem: e, f), never one alone (the review)
                        if band in ("e", "f"):
                            self.assertTrue(rows % 2 == 0 or rows == rest, (band, rows))
                    self.assertEqual(lay["rowsMax"], max(lay["rows"].values()))
                    self.assertEqual(lay["tilesMin"], min(lay["tiles"].values()))
        # Grapevine's 8 topics always all shown; on the English page, beside La Viña's tall tiles, Grapevine shows more of
        # its coming themes than one under the other
        self.assertEqual(set(r["en"]["gv"]["tiles"].values()), {8})
        self.assertTrue(any(r["en"]["gv"]["rows"][b] > 3 for b in bands), r["en"]["gv"])

    def test_the_estimates(self):
        r = self.layout()
        self.assertEqual(r["lines"], [2, 1, 0, 2])          # (measured in a browser: 9.8rem → two lines, 15.86rem → two)
        low, more, narrow = r["taller"]
        # three more rows (at least 4.6rem each, one column), no "Show all N deadlines" (2.25rem) any more
        self.assertGreater(more, low + 3 * 4.6 - 2.25)
        self.assertGreater(narrow, low)                     # a narrower card wraps more
        blocks = [v for k, v in r["parts"].items() if k not in ("total", "note") and v > 0]   # (no deadline has passed here)
        self.assertEqual(len(blocks), 4)
        self.assertAlmostEqual(sum(blocks) + r["parts"]["note"] + 2.5 + 0.75 * 3, r["parts"]["total"], places=6)

    def test_the_classes_that_hide(self):
        r = self.layout()
        # the 4th row: hidden one under the other and at b (3 shown), its "Show all" copy hidden at a (5 shown in the
        # list); the "Show all" of 7 rows hidden where all 7 are in the list (a), never where 5 are
        self.assertEqual(r["hide"], ["cm-dl-hide-n cm-dl-hide-b", "cm-dl-hide-a", "cm-dl-hide-a", "", ""])

    def test_never_one_row_alone_in_two_columns(self):
        """The review (October 2026): at 1920px Spanish Grapevine showed 3 of its rows in two columns, the third alone; at
        768px (one card under the other, the rows in two columns) both cards did. Odd numbers of rows to choose from —
        5 or 7 coming themes after the next — and an odd one only when it is all of them."""
        for n_rest in (3, 4, 5, 6, 7, 9):
            items = GV_DATED[:1] + [dated("gv", f"Theme {i}", f"2027-0{1 + i // 9}-{10 + i:02d}", f"2028-{1 + i % 12:02d}")
                                    for i in range(n_rest)] + GV_TOPICS + LV_DATED + LV_TOPICS
            r = self.layout(items)
            for lang in ("en", "es"):
                lay = r[lang]["gv"]
                with self.subTest(rest=n_rest, lang=lang):
                    self.assertEqual(lay["rows"]["m"], min(4, n_rest))
                    for band in ("e", "f"):
                        self.assertTrue(lay["rows"][band] % 2 == 0 or lay["rows"][band] == n_rest, (band, lay["rows"]))

    def test_the_css_has_the_same_bands(self):
        css = (ROOT / "src" / "assets" / "css" / "areas" / "community.css").read_text(encoding="utf-8")
        rules = re.findall(r"@container cm-pairs \(([^)]*)\) \{ \.cm-dl-hide-(\w) \{ display: none !important; \} \}", css)
        bands = self.layout()["bands"]
        stacked = self.layout()["stacked"]
        self.assertEqual(stacked, 42.25)                    # a card from 42rem (@2xl) with its 1px borders to spare
        want = [(f"width < {stacked:g}rem", "n"), (f"{stacked:g}rem <= width < 59.5rem", "m")]
        for i, b in enumerate(bands):
            nxt = bands[i + 1]["from"] if i + 1 < len(bands) else None
            f = f"{b['from']:g}rem"
            want.append((f"{f} <= width < {nxt:g}rem" if nxt else f"width >= {f}", b["band"]))
        self.assertEqual(rules, want)
        self.assertIn(".cm-pairs { container: cm-pairs / inline-size; }", css)
        self.assertEqual(bands[0]["from"], 59.5)            # side by side from the same width as .cm-dl-pair
        self.assertIn("@container (width >= 59.5rem) { :is(.cm-rec-pair, .cm-dl-pair)", css)

    def test_without_grapevine_topics_the_layout_still_holds(self):
        r = self.layout(GV_DATED + LV_DATED + LV_TOPICS)
        self.assertEqual(r["en"]["gv"]["tilesMax"], 0)
        self.assertTrue(all(v >= 3 for v in r["en"]["gv"]["rows"].values()))


# --------------------------------------------------------------------------------------------- the page, rendered
class Rendered(unittest.TestCase):
    built: dict | None = None

    def pages(self) -> dict:
        if Rendered.built is None:
            from test_r12_u2_contribute import build_contribute
            data = {"editorial": {"updated": "2026-10-16T06:00:00Z", "items": GV_DATED + GV_TOPICS + LV_DATED + LV_TOPICS},
                    "spotlight": {"updated": "2026-10-16T06:00:00Z", "items": [], "counts": {}}}
            Rendered.built = build_contribute(self, NOW, data=data)["html"]
        return Rendered.built

    @staticmethod
    def card(html: str, name: str) -> str:
        """One magazine's deadline card: from its start to the other card's, or to the end of the section."""
        mark = '<div class="card @container flex flex-col overflow-hidden '
        start = html.index(mark + ("read-accent-lv" if name == "lv" else "read-accent-gv"))
        other = html.find(mark, start + 1)
        return html[start:other if other > 0 else html.index("</section>", start)]

    def test_grapevines_tiles_say_why_they_are_there(self):
        s = json.loads((ROOT / "src" / "_i18n" / "read.json").read_text(encoding="utf-8"))
        self.assertEqual((s["read.contrib.tag_department"]["en"], s["read.contrib.tag_always"]["en"]), ("In every issue", "Always needed"))
        for lang, html in self.pages().items():
            with self.subTest(lang=lang):
                gv = self.card(html, "gv")
                tiles = re.findall(r'<li class="grid[^"]*grid-cols-\[auto_minmax\(0,1fr\)\][^"]*">(.*?)</li>', gv, re.S)
                self.assertEqual(len(tiles), 8)
                self.assertEqual(sum(s["read.contrib.tag_always"][lang] in t for t in tiles), 2)
                self.assertEqual(sum(s["read.contrib.tag_department"][lang] in t for t in tiles), 6)
                self.assertNotIn("data-rec-topic", gv)                             # only ideas: no recording link
                self.assertIn(s["read.contrib.gv_note_topics"][lang], gv.replace("&#39;", "'"))
                lv = self.card(html, "lv")
                # each of La Viña's topics has its link (in the list and, at the widths that hide it there, under "Show all")
                links = re.findall(r'data-rec-go="lv" data-rec-topic="([^"]*)"', lv)
                self.assertEqual(set(links), {t["title"] for t in LV_TOPICS})
                self.assertTrue(19 <= len(links) <= 19 + 14, len(links))
                self.assertNotIn("ct-topic-tag", lv)
                if lang == "es":                                                   # Spanish words, Grapevine's English under them
                    self.assertIn('lang="es">Pasos 4 a 12', gv)
                    self.assertIn('<span class="block text-xs italic text-muted" lang="en">Steps 4–12</span>', gv)
                # the department and the June 2027 theme of the same name: both
                name = "Sobriedad emocional" if lang == "es" else "Emotional Sobriety"
                start = gv.index("read-deadline-next")
                nxt = gv[start:gv.index('class="read-deadline-row flex items-start', start)]   # up to the first row after it
                self.assertIn(f">{name}</p>", nxt)
                tile = next(t for t in tiles if f">{name}" in t)
                self.assertIn(s["read.contrib.tag_department"][lang], tile)

    def test_the_rows_and_tiles_carry_their_widths(self):
        for lang, html in self.pages().items():
            with self.subTest(lang=lang):
                # a row after the usual 3 is hidden one card under the other; La Viña's 9th topic too, and its copy
                # under "Show all" where the list shows it
                self.assertRegex(html, r'class="read-deadline-row [^"]*cm-dl-hide-n')
                lv = self.card(html, "lv")
                tiles = re.findall(r'<li class="grid( [^"]*)? grid-cols-\[auto_minmax\(0,1fr\)\]', lv)
                self.assertNotIn("cm-dl-hide-n", tiles[7])
                self.assertIn("cm-dl-hide-n", tiles[8])
                self.assertNotRegex(html, r"hidden lg:grid|grid lg:hidden")       # the old fixed 8 / 12


if __name__ == "__main__":
    unittest.main()
