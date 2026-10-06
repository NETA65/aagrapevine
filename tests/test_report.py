"""The district report (/monthly/#report): eleventy/filters/report.js writes it, src/_i18n/report.json
words it, src/assets/js/report.js lets each GVR / RLV edit it.

  * Strings — every report.* text in English AND Spanish, with the same {placeholders} in both, and
              every key the code asks for exists (the CI build is strict about it too).
  * Model   — reportModel() on a small data set, fixed "today": the 12 sections in order, in both
              languages, what each one says, and the fallback sentence of each section when there
              is nothing to report (no meeting date, no deadlines, no events …); the plain text the
              page shows without JavaScript; the editor's own strings; the events rule.
  * Real    — the model built from the repository's own data: complete, both languages, no
              placeholder left unfilled.
  * Editor  — the page's editor (src/assets/js/report.js) keeps a visitor's choices across visits: a
              section switched off (one of their own too) stays out of the report.
  * DatedOffers — the shop section never quotes a Book of the Month offer outside its days: the text
              at each later moment (`steps`: an offer starts or ends, a price change takes effect, its
              notice ends), fixed dates; the editor shows the step of its own clock.
  * MachineTitles — a machine-translated theme has the magazine's own words after it and the section
              says some titles were translated automatically.
  * WordFile — the .docx is a valid ZIP of well-formed XML whatever the text holds (U+FFFE, U+FFFF,
              control characters, a lone surrogate are left out; an emoji stays).
  * LastMonthsDraft — a new month offers last month's draft on this device as its starting point and
              carries over only the visitor's own parts.

The Model, Real and Editor checks run the JavaScript with Node.js (tests/nodejs.py) and are skipped
without Node.js (Model and Real: or the site's npm packages).

    python -m unittest tests.test_report -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402

STRINGS = ROOT / "src" / "_i18n" / "report.json"
SITE_LINKS = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))["links"]
SECTION_IDS = ["header", "committee", "issues", "deadlines", "shop", "events", "writers", "meetings", "weekly",
               "resources", "asks", "notes"]
SITE_URL = "https://example.org/site"
PLACEHOLDER = re.compile(r"\{(\w+)\}")
NOW = "2026-10-05T17:00:00Z"            # Monday, October 5, 2026, noon in Texas


def strings() -> dict:
    return json.loads(STRINGS.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ a small data set (October 2026)
def item(iid: str, kind: str, **kw) -> dict:
    it = {"id": iid, "kind": kind, "status": "ok", "title": kw.pop("title", iid), "url": kw.pop("url", f"https://example.com/{iid}"),
          "date": kw.pop("date", None), "lang": kw.pop("lang", "en"), "category": kw.pop("category", None),
          "source": kw.pop("source", "committee"), "extra": kw.pop("extra", {}), "i18n": kw.pop("i18n", {}), "machine": []}
    it.update(kw)
    return it


def event(iid: str, start: str, end: str | None = None, **kw) -> dict:
    extra = {"start": start, "end": end, **kw.pop("extra", {})}
    return item(iid, "event", date=start, extra=extra, **kw)


def full_db() -> dict:
    return {
        "events": {"items": [
            event("ev:committee", "2026-10-22T00:00:00Z", "2026-10-22T01:00:00Z", title="Committee meeting", category="committee"),
            event("ev:done", "2026-10-03T19:00:00Z", "2026-10-03T21:00:00Z", title="Already over"),
            event("ev:ws", "2026-10-17T15:00:00Z", "2026-10-17T18:00:00Z", title="Grapevine Writing Workshop",
                  i18n={"title": {"en": "Grapevine Writing Workshop", "es": "Taller de escritura de Grapevine"}},
                  extra={"location": "Arlington, TX"}),
            event("ev:rec:2026-10-10", "2026-10-10T22:00:00Z", "2026-10-11T01:00:00Z", title="CityWide booth", category="recurring",
                  extra={"series": "citywide"}),
            event("ev:rec:2026-11-14", "2026-11-14T23:00:00Z", "2026-11-15T02:00:00Z", title="CityWide booth", category="recurring",
                  extra={"series": "citywide"}),
            event("ev:assembly", "2026-10-30", "2026-11-01", title="Fall Assembly", extra={"all_day": True, "tentative": True}),
            event("ev:far", "2026-12-12T16:00:00Z", None, title="Too far ahead"),
        ]},
        "editorial": {"items": [
            item("ed:gv:2027-05", "topic", title="Fun in Sobriety", source="grapevine",
                 extra={"publication": "gv", "issue_key": "2027-05", "deadline": "2026-10-15"},
                 i18n={"title": {"en": "Fun in Sobriety", "es": "Diversión en sobriedad"}}),
            item("ed:gv:old", "topic", title="Closed", source="grapevine", extra={"publication": "gv", "issue_key": "2027-03", "deadline": "2026-09-01"}),
        ] + [item(f"ed:lv:t{i}", "topic", title=f"Tema {i}", lang="es", source="lavina", extra={"publication": "lv", "evergreen": True},
                  i18n={"title": {"en": f"Topic {i}", "es": f"Tema {i}"}}) for i in range(4)]
          # La Viña's yearly themes (dated topics): the next two still open are reported, in its own Spanish words
          + [item(f"ed:lv:{key}", "topic", title=theme, lang="es", source="lavina",
                  extra={"publication": "lv", "issue_key": key, "issue_label": f"{es_label} 2027", "deadline": due, "evergreen": False},
                  i18n={"title": {"en": en, "es": theme}, "issue_label": {"en": f"{en_label} 2027", "es": f"{es_label} 2027"}})
             for key, theme, en, due, en_label, es_label in (
                 ("2027-03", "Apadrinamiento", "Sponsorship", "2026-09-03", "March / April", "Marzo / Abril"),       # over
                 ("2027-05", "Recaídas", "Relapses", "2026-10-17", "May / June", "Mayo / Junio"),
                 ("2027-07", "Prisiones", "Prisiones", "2026-12-15", "July / August", "Julio / Agosto"),       # no English yet
                 ("2027-09", "Celebrando", "Celebrating", "2027-02-02", "September / October", "Septiembre / Octubre"))]},
        "articles": {"items": [], "issues": [
            {"id": "gv:2026-10", "publication": "gv", "key": "2026-10", "label": "October 2026", "theme": "Loneliness",
             "url": "https://www.aagrapevine.org/magazine-issue/october-2026",
             "i18n": {"theme": {"en": "Loneliness", "es": "Soledad"}, "label": {"en": "October 2026", "es": "Octubre 2026"}}},
            {"id": "lv:2026-09", "publication": "lv", "key": "2026-09", "label": "Septiembre / Octubre 2026", "theme": "Servicio en AA",
             "url": "https://www.aalavina.org/revista/septiembre-octubre-2026",
             "i18n": {"theme": {"en": "Service in AA", "es": "Servicio en AA"},
                      "label": {"en": "September / October 2026", "es": "Septiembre / Octubre 2026"}}},
        ]},
        "shop": {"botm": [], "subscriptions": [
            {"pub": "gv", "region": "us", "plans": [{"type": "print", "term_months": 12, "price": 36.0},
                                                   {"type": "digital", "term_months": 1, "price": 2.99},
                                                   {"type": "digital", "term_months": 12, "price": 29.99}]},
            {"pub": "lv", "region": "us", "plans": [{"type": "print", "term_months": 12, "price": 18.0},
                                                   {"type": "digital", "term_months": 12, "price": 14.99}]},
        ]},
        "meetings": {"items": []},
        "weekly_open": {"items": [
            item("weekly_open", "meeting", title="Grapevine Weekly Open AA Meeting", source="grapevine",
                 extra={"zoom_id": "871 2036 8287", "passcode": "238047", "weekday": "wednesday", "start_local": "12:00",
                        "timezone": "America/New_York", "next_start": "2026-10-07T16:00:00Z"},
                 i18n={"title": {"en": "Grapevine Weekly Open AA Meeting", "es": "Grapevine Weekly Open AA Meeting"},
                       "when": {"en": "Wednesdays at 11:00 AM Central", "es": "Los miércoles a las 11:00 a. m. (hora del Centro)"}}),
        ]},
        "pdfs": {"items": [
            item("pdf:1", "pdf", title="GV News October 2026", date="2026-09-28", url="https://www.aagrapevine.org/gv-news.pdf",
                 i18n={"title": {"en": "GV News October 2026", "es": "Noticias de GV, octubre de 2026"}}),
        ]},
        "spotlight": {"items": [
            item("sp:1", "article", title="My spiritual GPS", source="grapevine", category="gv",
                 extra={"publication": "gv", "pub_date": "2026-09-20", "author": "Jim B.", "issue_label": "October 2026",
                        "geo": {"scope": "neta65", "city": "Pottsboro", "label_en": "Pottsboro, Texas"}},
                 i18n={"title": {"en": "My spiritual GPS", "es": "Mi GPS espiritual"},
                       "issue_label": {"en": "October 2026", "es": "Octubre 2026"}}),
        ]},
        "audio_project": {"gv": {"phone": "(559) 726-1216", "tel": "+15597261216", "minutes_min": 6, "minutes_max": 8},
                          "lv": {"phone": "(559) 670-1601", "tel": "+15596701601", "minutes_max": 7}},
    }


MEETING = {"next": {"ymd": "2026-10-21", "start": "2026-10-22T00:00:00Z", "end": "2026-10-22T01:00:00Z"},
           "rule": {"weekday": 3, "n": 3, "start": "19:00", "end": "20:00"}}

EMPTY_DB = {"events": {"items": []}, "editorial": {"items": []}, "articles": {"items": [], "issues": []},
            "shop": {}, "meetings": {"items": []}, "weekly_open": {"items": []}, "pdfs": {"items": []},
            "spotlight": {"items": []}, "audio_project": {}}

# Build the model(s) the way the page does (the site's own settings and config/carry.yml).
MODEL_JS = """
const R = await imp("eleventy/filters/report.js");
const site = (await imp("src/_data/site.js")).default();
const carry = (await imp("src/_data/carry.js")).default();
const now = new Date(input.now);
const build = (db, meeting) => {
  const model = R.reportModel(db, meeting, carry, site, now);
  return { model, text: { en: R.reportText(model, "en"), es: R.reportText(model, "es") } };
};
out({
  ids: R.SECTION_IDS,
  full: build(input.full, input.meeting),
  empty: build(input.empty, {}),
  ui: { en: R.uiStrings("en"), es: R.uiStrings("es") },
  events: R.upcomingEvents(input.full, now).map((e) => [e.id, e._recurring, e._tentative]),
  safe: R.safeJson({ a: "</script><!-- x" }),
});
"""


class Strings(unittest.TestCase):
    def test_both_languages_and_the_same_placeholders(self):
        s = strings()
        self.assertGreater(len(s), 150)
        for key, v in s.items():
            with self.subTest(key=key):
                self.assertTrue(key.startswith("report."))
                self.assertTrue(isinstance(v.get("en"), str) and v["en"].strip(), "missing English")
                self.assertTrue(isinstance(v.get("es"), str) and v["es"].strip(), "missing Spanish")
                self.assertEqual(sorted(set(PLACEHOLDER.findall(v["en"]))), sorted(set(PLACEHOLDER.findall(v["es"]))),
                                 "both languages use the same {placeholders}")

    def test_every_key_the_code_asks_for_exists(self):
        s = strings()
        code = (ROOT / "eleventy" / "filters" / "report.js").read_text(encoding="utf-8")
        used = set(re.findall(r'\bT\("([a-z0-9_.]+)"', code)) | {k[len("report."):] for k in re.findall(r'"(report\.[a-z0-9_.]+)"', code)}
        self.assertGreater(len(used), 50)
        for k in sorted(used):
            with self.subTest(key=k):
                self.assertIn(f"report.{k}", s)
        for sid in SECTION_IDS + ["custom"]:
            self.assertIn(f"report.s.{sid}", s)
        ui = re.search(r"const UI_KEYS = \[(.*?)\];", code, re.S)
        self.assertIsNotNone(ui)
        for k in re.findall(r'"([a-z0-9_]+)"', ui.group(1)):
            with self.subTest(ui=k):
                self.assertIn(f"report.{k}", s)
        # the page and the editor
        page = (ROOT / "src" / "pages" / "monthly.njk").read_text(encoding="utf-8") \
            + (ROOT / "src" / "assets" / "js" / "report.js").read_text(encoding="utf-8")
        for k in sorted(set(re.findall(r'"(report\.[a-z0-9_.]+)"', page))):
            with self.subTest(page_key=k):
                self.assertIn(k, s)


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = None

    def setUp(self):
        if Model.res is None:
            Model.res = run_js(self, MODEL_JS, data={"now": NOW, "full": full_db(), "meeting": MEETING, "empty": EMPTY_DB},
                               env={"SITE_URL": SITE_URL})
        self.r = Model.res
        self.s = strings()

    def sections(self, which: str, lang: str) -> dict[str, dict]:
        return {x["id"]: x for x in self.r[which]["model"]["langs"][lang]["sections"]}

    def tr(self, key: str, lang: str, **v) -> str:
        return PLACEHOLDER.sub(lambda m: str(v.get(m.group(1), m.group(0))), self.s[key][lang])

    def test_twelve_sections_in_order_in_both_languages(self):
        self.assertEqual(self.r["ids"], SECTION_IDS)
        m = self.r["full"]["model"]
        self.assertEqual((m["v"], m["month"]), (1, "2026-10"))
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                secs = m["langs"][lang]["sections"]
                self.assertEqual([x["id"] for x in secs], SECTION_IDS)
                self.assertEqual([x["title"] for x in secs], [self.s[f"report.s.{i}"][lang] for i in SECTION_IDS])
                for x in secs:
                    self.assertNotRegex(x["text"], r"\{[a-z_]+\}", f"{x['id']}: a placeholder was left unfilled")
                    self.assertNotIn("report.", x["text"])
                    self.assertNotIn("undefined", x["text"])
        self.assertEqual(m["langs"]["en"]["month"], "October 2026")
        self.assertEqual(m["langs"]["es"]["month"], "octubre de 2026")
        en, es = self.sections("full", "en"), self.sections("full", "es")
        for sid in SECTION_IDS:
            with self.subTest(section=sid):
                self.assertEqual(bool(en[sid]["text"].strip()), bool(es[sid]["text"].strip()), "EN and ES say something alike")

    def test_what_the_sections_say(self):
        for lang in ("en", "es"):
            S = {k: v["text"] for k, v in self.sections("full", lang).items()}
            base = SITE_URL + ("/es" if lang == "es" else "")
            with self.subTest(lang=lang, section="header"):
                self.assertTrue(S["header"].startswith(self.tr("report.h_title", lang, district=self.s["report.tok_district"][lang],
                                                               month="October 2026" if lang == "en" else "octubre de 2026")))
            with self.subTest(lang=lang, section="committee"):
                self.assertIn("October 21" if lang == "en" else "21 de octubre", S["committee"])
                self.assertIn(self.tr("report.c_join", lang, url=f"{base}/meetings/"), S["committee"])
                self.assertNotIn(self.s["report.c_none"][lang], S["committee"])
            with self.subTest(lang=lang, section="issues"):
                self.assertIn("Loneliness" if lang == "en" else "Soledad", S["issues"])
                self.assertIn(f"{base}/monthly/2026-10/", S["issues"])
                # La Viña first on the Spanish report
                gv, lv = S["issues"].find("Grapevine"), S["issues"].find("La Viña")
                self.assertTrue(gv >= 0 and lv >= 0)
                self.assertEqual(lv < gv, lang == "es")
            with self.subTest(lang=lang, section="deadlines"):
                self.assertIn("“Fun in Sobriety”" if lang == "en" else "“Diversión en sobriedad” (“Fun in Sobriety”)", S["deadlines"])
                self.assertNotIn("Closed", S["deadlines"])                     # its deadline has passed
                self.assertIn("(559) 726-1216", S["deadlines"])
                self.assertIn("(559) 670-1601", S["deadlines"])
                self.assertIn("“Tema", S["deadlines"])
                # La Viña's next two deadlines (its yearly themes), its theme in Spanish with the English words after it —
                # the issue as /contribute/, the toolkit and the slides write the same deadline ("May–June 2027")
                self.assertIn(self.s["report.d_lv_dl"][lang], S["deadlines"])
                if lang == "en":
                    self.assertIn("• “Recaídas” (Relapses) — May–June 2027 issue — due Oct 17\n• “Prisiones” — July–August "
                                  "2027 issue — due Dec 15", S["deadlines"])
                else:
                    self.assertIn("• “Recaídas” — edición de mayo–junio de 2027 — fecha límite: 17 de octubre", S["deadlines"])
                for not_now in ("Apadrinamiento", "Celebrando"):                # over; a third one
                    self.assertNotIn(not_now, S["deadlines"])
                lv_at, gv_at = S["deadlines"].index(self.s["report.d_lv_dl"][lang]), S["deadlines"].index(self.s["report.d_gv"][lang])
                self.assertEqual(lv_at < gv_at, lang == "es")                  # the page language's magazine first
                self.assertLess(lv_at, S["deadlines"].index(self.s["report.d_lv"][lang]))
            with self.subTest(lang=lang, section="shop"):
                self.assertIn(self.s["report.s_title"][lang], S["shop"])
                self.assertIn(f"{base}/shop/", S["shop"])
                # Carry the Message: La Viña's own Spanish page on the Spanish report (config/site.yml links)
                links = SITE_LINKS
                self.assertIn(links["lleva_el_mensaje"] if lang == "es" else links["carry_the_message"], S["shop"])
                self.assertNotIn(links["carry_the_message"] if lang == "es" else links["lleva_el_mensaje"], S["shop"])
            with self.subTest(lang=lang, section="weekly: in the middle of a line"):
                # the data's "Los miércoles …" goes on in lower case after the dash; English keeps its capital
                self.assertIn("— los miércoles a las 11:00 a. m. (hora del Centro), por Zoom" if lang == "es"
                              else "— Wednesdays at 11:00 AM Central, on Zoom", S["weekly"].replace(" ", " "))
            with self.subTest(lang=lang, section="events"):
                self.assertIn(self.tr("report.e_intro", lang, n=45), S["events"])
                self.assertIn("Grapevine Writing Workshop" if lang == "en" else "Taller de escritura de Grapevine", S["events"])
                self.assertEqual(S["events"].count("CityWide booth"), 1)        # a monthly series once …
                self.assertIn(self.s["report.e_monthly"][lang], S["events"])   # … marked "every month"
                self.assertIn(self.s["report.e_tbc"][lang], S["events"])       # the tentative assembly
                for gone in ("Already over", "Too far ahead", "Committee meeting"):
                    self.assertNotIn(gone, S["events"])
                # the time zone as the committee line says it: "CDT" in English, "(hora del Centro)" in Spanish
                if lang == "es":
                    self.assertRegex(S["events"], r"m\. \(hora del Centro\) —")
                    self.assertNotRegex(S["events"], r"\b(?:CDT|CST)\b")
                else:
                    self.assertIn("CDT", S["events"])
            with self.subTest(lang=lang, section="writers"):
                self.assertIn("Jim B., Pottsboro", S["writers"])
                self.assertIn("My spiritual GPS" if lang == "en" else "Mi GPS espiritual", S["writers"])
            with self.subTest(lang=lang, section="meetings"):
                self.assertEqual(S["meetings"], self.tr("report.m_empty", lang, url=f"{base}/meetings/#grapevine-meetings"))
            with self.subTest(lang=lang, section="weekly"):
                self.assertIn("Grapevine Weekly Open AA Meeting", S["weekly"])
                self.assertIn(f"{base}/meetings/#weekly-open", S["weekly"])
            with self.subTest(lang=lang, section="resources"):
                self.assertIn("https://www.aagrapevine.org/gv-news.pdf", S["resources"])
                self.assertIn(f"{base}/gvr/", S["resources"])
            with self.subTest(lang=lang, section="asks/notes"):
                self.assertEqual(S["asks"], self.s["report.a_default"][lang])
                self.assertEqual(S["notes"], "")

    def test_nothing_to_report_falls_back_to_a_sentence(self):
        for lang in ("en", "es"):
            S = {k: v["text"] for k, v in self.sections("empty", lang).items()}
            base = SITE_URL + ("/es" if lang == "es" else "")
            with self.subTest(lang=lang):
                self.assertTrue(S["committee"].startswith(self.s["report.c_none"][lang]))
                self.assertIn(self.tr("report.i_none", lang, url=f"{base}/read/"), S["issues"])
                self.assertIn(self.s["report.d_none"][lang], S["deadlines"])
                self.assertIn(self.tr("report.e_none", lang, n=45), S["events"])
                self.assertIn(self.s["report.w_none"][lang].replace("{n}", "60"), S["writers"])
                self.assertEqual(S["meetings"], self.tr("report.m_empty", lang, url=f"{base}/meetings/#grapevine-meetings"))
                self.assertEqual(S["weekly"], "")                                # nothing to say: left out
                self.assertIn(self.tr("report.r_library", lang, url=f"{base}/library/"), S["resources"])
                self.assertNotIn(self.s["report.b_title_plain"][lang], S["shop"])  # no Book of the Month offer

    def test_the_plain_text(self):
        for which in ("full", "empty"):
            for lang in ("en", "es"):
                with self.subTest(which=which, lang=lang):
                    text = self.r[which]["text"][lang]
                    secs = self.sections(which, lang)
                    self.assertTrue(text.startswith(secs["header"]["text"] + "\n\n1. "))
                    self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
                    shown = [sid for sid in SECTION_IDS[1:] if secs[sid]["text"].strip()]
                    for n, sid in enumerate(shown, 1):                       # numbered, empty sections left out
                        self.assertIn(f"\n{n}. {secs[sid]['title']}\n", text)
                    self.assertNotIn(f"{len(shown) + 1}. ", text.split("\n\n")[-1][:5])
                    self.assertNotIn(secs["notes"]["title"], text)

    def test_editor_strings_and_json(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                ui = self.r["ui"][lang]
                self.assertGreaterEqual(len(ui), 30)
                for k, v in ui.items():
                    self.assertTrue(isinstance(v, str) and v.strip() and not v.startswith("report."), k)
        self.assertNotIn("</script", self.r["safe"])
        self.assertNotIn("<!--", self.r["safe"])
        self.assertEqual(json.loads(self.r["safe"]), {"a": "</script><!-- x"})

    def test_upcoming_events_rule(self):
        self.assertEqual(self.r["events"], [["ev:rec:2026-10-10", True, False], ["ev:ws", False, False],
                                            ["ev:assembly", False, True]])


class RealData(unittest.TestCase):
    def test_the_report_builds_from_the_repositorys_data(self):
        res = run_js(self, """
            const R = await imp("eleventy/filters/report.js");
            const db = (await imp("src/_data/db.js")).default();
            const site = (await imp("src/_data/site.js")).default();
            const carry = (await imp("src/_data/carry.js")).default();
            const meeting = (await imp("src/_data/meeting.js")).default();
            const model = R.reportModel(db, meeting, carry, site);
            out({ model, en: R.reportText(model, "en"), es: R.reportText(model, "es") });
        """, env={"SITE_URL": SITE_URL})
        m = res["model"]
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                secs = m["langs"][lang]["sections"]
                self.assertEqual([x["id"] for x in secs], SECTION_IDS)
                for x in secs:
                    self.assertNotRegex(x["text"], r"\{[a-z_]+\}", x["id"])
                    self.assertNotIn("undefined", x["text"])
                    self.assertNotIn("NaN", x["text"])
                self.assertGreater(len(res[lang]), 800)
                self.assertIn("1. ", res[lang])
        self.assertIsInstance(m["meetings"]["options"], list)
        for opt in m["meetings"]["options"]:
            self.assertTrue(opt["label"]["en"] and opt["label"]["es"])


# The editor in a vm context, as the page runs it: a small model (<script id="rp-data">), a localStorage
# over one Map, an Alpine that hands back the component. `boot()` = the page opened (again): a new
# component on the same storage.
EDITOR = r"""
import vm from "node:vm";
const lang = (L) => ({
  month: L === "es" ? "octubre de 2026" : "October 2026",
  sections: ["header", "committee", "shop", "notes"].map((id) => ({ id, title: id + " (" + L + ")",
    text: id === "header" ? "District [##] report" : id === "notes" ? "" : "Text of " + id })),
  tokens: { district: "[##]", name: "[name]", role: "[role]", group: "[group]" }, roles: { gvr: "GVR" },
  custom: "My section", paste: "(paste)", meet: { pick: "Meetings in {where}:", none: "none", more: "more" },
});
const D = { v: 1, month: "2026-10", langs: { en: lang("en"), es: lang("es") }, meetings: { options: [] } };
const store = new Map();
const boot = () => {
  const docL = {};
  const ctx = {
    console, JSON, Math, Date, Intl, Object, Array, String, Number, Promise,
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); t.unref?.(); return t; }, clearTimeout,
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { store.set(k, String(v)); },
                    removeItem: (k) => { store.delete(k); }, get length() { return store.size; }, key: (i) => [...store.keys()][i] ?? null },
    navigator: {}, GV: {}, addEventListener() {},
    document: { addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); }, querySelector: () => null,
                getElementById: (id) => (id === "rp-data" ? { textContent: JSON.stringify(D) } : id === "rp-ui" ? { textContent: "{}" } : null) },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/report.js", "utf8"), ctx, { filename: "report.js" });
  let factory = null;
  ctx.Alpine = { data: (name, fn) => { if (name === "rpEditor") factory = fn; } };
  for (const fn of docL["alpine:init"] || []) fn();
  const a = factory("en");
  a.$nextTick = (fn) => fn && fn();
  a.$refs = {};
  a.$root = { querySelector: () => null, querySelectorAll: () => [] };
  a.init();
  return a;
};
"""


class Editor(unittest.TestCase):
    def test_a_section_switched_off_stays_off(self):
        r = run_js(self, EDITOR + r"""
          let a = boot();
          a.addCustom();
          const id = a.d.custom[0].id;
          a.setTitle(id, "Private note for the DCM");
          a.setText(id, "Please do not read this part at the meeting.");
          a.toggle(id);                   // "Include in the report": off — one of their own sections …
          a.toggle("shop");               // … and a built-in one
          a.saveNow();
          const before = [a.isOn(id), a.isOn("shop"), a.plain().includes("do not read")];
          a = boot();                     // the next visit (or the report language switched and back)
          const after = [a.isOn(id), a.isOn("shop"), a.plain().includes("do not read"), a.plain().includes("Text of shop"), a.d.custom.length];
          // removed while off: a section added later gets the same id, and starts switched on
          a.removeCustom(id);
          a.addCustom();
          a.saveNow();
          const again = [a.d.custom[0].id === id, a.isOn(a.d.custom[0].id)];
          out({ before, after, again, reopened: boot().isOn(id) });""", needs_modules=False)
        self.assertEqual(r["before"], [False, False, False])
        self.assertEqual(r["after"], [False, False, False, False, 1])     # still out of the text copied, sent, printed
        self.assertEqual(r["again"], [True, True])
        self.assertTrue(r["reopened"])


# ------------------------------------------------------------------ the shop section's dated offers
def offer(oid: str, pub: str, title: str, starts: str, ends: str) -> dict:
    return {"id": oid, "pub": pub, "title": title, "url": f"https://example.com/{oid}", "lang": "es" if pub == "lv" else "en",
            "price": 14.99, "sale_price": 11.99, "discount_pct": 20, "starts": starts, "ends": ends, "read": "2026-10-01"}


DATED_SHOP = {
    "botm": [offer("botm:gv:oct", "gv", "No Matter What", "2026-09-15", "2026-10-14"),
             offer("botm:gv:nov", "gv", "Into Action", "2026-10-15", "2026-11-14")],      # not on offer yet on October 5
    "subscriptions": [{"pub": "gv", "region": "us", "plans": [{"type": "print", "term_months": 12, "price": 36.0}]}],
    "price_changes": [{"key": "2027-01", "announced": "2026-10-01", "effective": "2027-01-01", "notice_until": "2027-01-31",
                       "at": {"announced": "2026-10-01T05:00:00Z", "effective": "2027-01-01T06:00:00Z", "notice_end": "2027-02-01T06:00:00Z"},
                       "yearly": [{"pub": "gv", "type": "print", "new": 39.0, "now": 36.0, "after": 39.0}], "books_more": 2.0}],
}
DATED_JS = """
const R = await imp("eleventy/filters/report.js");
const res = {};
for (const now of input.nows) {
  const model = R.reportModel({ shop: input.shop }, {}, { ways: [], tips: {}, wayById: {} }, { url: "https://example.org/site", links: {} }, new Date(now));
  res[now] = Object.fromEntries(["en", "es"].map((l) => [l, model.langs[l].sections.find((s) => s.id === "shop")]));
}
out(res);
"""


class DatedOffers(unittest.TestCase):
    """P3-13: a Book of the Month offer is dated data (its starts / ends days, Central time): the report's shop section
    quotes it only while it runs — in the text of the build's day and in every later text (`steps`) the editor
    switches to, so the text "from January 1" (the announced price change) never quotes an offer that ended in
    October."""

    def test_offers_only_while_they_run(self):
        r = run_js(self, DATED_JS, data={"shop": DATED_SHOP, "nows": ["2026-10-05T17:00:00Z", "2026-10-20T17:00:00Z"]})
        oct5 = r["2026-10-05T17:00:00Z"]["en"]
        self.assertIn("No Matter What", oct5["text"])
        self.assertNotIn("Into Action", oct5["text"], "not on offer until October 15")
        steps = [(s["at"], s["text"]) for s in oct5["steps"]]
        # the moments the words change at: the October offer is over and November's starts (00:00 Central, October
        # 15), November's is over (00:00 after November 14), the new prices (January 1), the end of their notice
        self.assertEqual([a for a, _ in steps], ["2026-10-15T05:00:00.000Z", "2026-11-15T06:00:00.000Z",
                                                  "2027-01-01T06:00:00.000Z", "2027-02-01T06:00:00.000Z"])
        texts = dict(steps)
        self.assertNotIn("No Matter What", texts["2026-10-15T05:00:00.000Z"])
        self.assertIn("Into Action", texts["2026-10-15T05:00:00.000Z"])
        for at in ("2026-11-15T06:00:00.000Z", "2027-01-01T06:00:00.000Z", "2027-02-01T06:00:00.000Z"):
            with self.subTest(at=at):
                self.assertNotIn("No Matter What", texts[at])
                self.assertNotIn("Into Action", texts[at])
                self.assertNotIn("Book of the Month", texts[at])
        self.assertIn("New prices since January 1, 2027", texts["2027-01-01T06:00:00.000Z"])
        self.assertNotIn("New prices", texts["2027-02-01T06:00:00.000Z"])
        # the Spanish report: the same moments, but only where its words change ("Nuevos precios desde el 1 de enero"
        # reads the same before and after the day)
        es_steps = r["2026-10-05T17:00:00Z"]["es"]["steps"]
        self.assertEqual([s["at"] for s in es_steps], ["2026-10-15T05:00:00.000Z", "2026-11-15T06:00:00.000Z", "2027-02-01T06:00:00.000Z"])
        self.assertTrue(all("No Matter What" not in s["text"] for s in es_steps))
        # built later in October: November's offer in the text itself, October's nowhere
        oct20 = r["2026-10-20T17:00:00Z"]["en"]
        self.assertIn("Into Action", oct20["text"])
        self.assertTrue(all("No Matter What" not in s["text"] for s in [oct20] + oct20["steps"]))

    def test_a_price_change_announced_later(self):
        # a change whose announcement is still ahead: its "New prices from …" list starts on the day it is announced
        shop = json.loads(json.dumps(DATED_SHOP))
        shop["price_changes"][0].update(announced="2026-11-02")
        shop["price_changes"][0]["at"]["announced"] = "2026-11-02T06:00:00Z"   # midnight CST (DST ended November 1)
        r = run_js(self, DATED_JS, data={"shop": shop, "nows": ["2026-10-05T17:00:00Z"]})
        en = r["2026-10-05T17:00:00Z"]["en"]
        self.assertNotIn("New prices", en["text"])
        texts = {s["at"]: s["text"] for s in en["steps"]}
        self.assertEqual(list(texts), ["2026-10-15T05:00:00.000Z", "2026-11-02T06:00:00.000Z", "2026-11-15T06:00:00.000Z",
                                       "2027-01-01T06:00:00.000Z", "2027-02-01T06:00:00.000Z"])
        self.assertNotIn("New prices", texts["2026-10-15T05:00:00.000Z"])
        self.assertIn("New prices from January 1, 2027", texts["2026-11-02T06:00:00.000Z"])
        self.assertIn("Into Action", texts["2026-11-02T06:00:00.000Z"])


# ------------------------------------------------------------------ machine-translated titles
MT_JS = """
const R = await imp("eleventy/filters/report.js");
const model = R.reportModel(input.db, {}, { ways: [], tips: {}, wayById: {} }, { url: "https://example.org/site", links: {} }, new Date(input.now));
out(Object.fromEntries(["en", "es"].map((l) => [l, Object.fromEntries(model.langs[l].sections.map((s) => [s.id, s.text]))])));
"""


class MachineTitles(unittest.TestCase):
    """P4-11: a theme that is a machine translation (a Grapevine theme in Spanish — the data's `machine`) has the
    magazine's own words after it in brackets, and its section ends with the note that some titles were translated
    automatically; a theme in its own language gets neither."""

    def test_the_issues_and_deadlines(self):
        db = full_db()
        db["articles"]["issues"][0]["machine"] = ["es"]                         # "Soledad": a machine translation
        db["editorial"]["items"][0]["machine"] = ["es"]                         # "Diversión en sobriedad" too
        r = run_js(self, MT_JS, data={"db": db, "now": NOW})
        s = strings()
        es, en = r["es"], r["en"]
        self.assertIn("“Soledad” (“Loneliness”)", es["issues"])
        self.assertIn(s["report.mt_note"]["es"], es["issues"])
        self.assertIn("“Diversión en sobriedad” (“Fun in Sobriety”)", es["deadlines"])
        self.assertIn(s["report.mt_note"]["es"], es["deadlines"])
        self.assertIn("“Loneliness”", en["issues"])
        self.assertNotIn("(“", en["issues"])
        self.assertNotIn(s["report.mt_note"]["en"], en["issues"])
        # without the data's `machine`: no note (the words may be the magazine's own translation)
        plain = run_js(self, MT_JS, data={"db": full_db(), "now": NOW})
        self.assertNotIn(s["report.mt_note"]["es"], plain["es"]["issues"])
        self.assertNotIn("(“Loneliness”)", plain["es"]["issues"])


# ------------------------------------------------------------------ the editor: Word file, last month's draft, timed texts
# The editor in a vm context (as EDITOR above) with a model of five sections, a store that can be filled
# beforehand (input.store), a fixed clock (input.now) and a captured download (the Blob the page would save).
EDITOR2 = r"""
import vm from "node:vm";
const lang = (L) => ({
  month: L === "es" ? "octubre de 2026" : "October 2026",
  sections: ["header", "committee", "shop", "asks", "notes"].map((id) => ({ id, title: id + " (" + L + ")",
    text: id === "header" ? "District [##] report" : id === "notes" ? "" : "Text of " + id,
    ...(id === "shop" && input.steps ? { steps: input.steps } : {}) })),
  tokens: { district: "[##]", name: "[name]", role: "[role]", group: "[group]" }, roles: { gvr: "GVR" },
  custom: "My section", paste: "(paste)", meet: { pick: "Meetings in {where}:", none: "none", more: "more" },
});
const D = { v: 1, month: "2026-10", langs: { en: lang("en"), es: lang("es") }, meetings: { options: [] } };
const UI = { prev_text: "You worked on a {month} report", prev_btn: "Start from my {month} draft", prev_done: "Started from {month}", downloaded: "{file}" };
const store = new Map(Object.entries(input.store || {}).map(([k, v]) => [k, JSON.stringify(v)]));
const nowMs = Date.parse(input.now || "2026-10-05T17:00:00Z");
class FakeDate extends Date { constructor(...a) { if (a.length) super(...a); else super(nowMs); } static now() { return nowMs; } }
let saved = null;
const boot = (pageLang = "en") => {
  const docL = {};
  const ctx = {
    console, JSON, Math, Date: FakeDate, Intl, Object, Array, String, Number, Promise, Blob, TextEncoder,
    URL: { createObjectURL: (b) => { saved = b; return "blob:report"; }, revokeObjectURL() {} },
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); t.unref?.(); return t; }, clearTimeout,
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { store.set(k, String(v)); },
                    removeItem: (k) => { store.delete(k); }, get length() { return store.size; }, key: (i) => [...store.keys()][i] ?? null },
    navigator: {}, GV: {}, addEventListener() {},
    document: { addEventListener: (t, fn) => { (docL[t] ||= []).push(fn); }, querySelector: () => null,
                createElement: () => ({ click() {}, remove() {}, setAttribute() {}, style: {} }), body: { appendChild() {} },
                getElementById: (id) => (id === "rp-data" ? { textContent: JSON.stringify(D) } : id === "rp-ui" ? { textContent: JSON.stringify(UI) } : null) },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync("src/assets/js/report.js", "utf8"), ctx, { filename: "report.js" });
  let factory = null;
  ctx.Alpine = { data: (name, fn) => { if (name === "rpEditor") factory = fn; } };
  for (const fn of docL["alpine:init"] || []) fn();
  const a = factory(pageLang);
  a.$nextTick = (fn) => fn && fn();
  a.$refs = {};
  a.$root = { querySelector: () => null, querySelectorAll: () => [] };
  a.init();
  return a;
};
const docxBytes = async () => Buffer.from(await saved.arrayBuffer()).toString("base64");
"""


class WordFile(unittest.TestCase):
    """P8-5: the report's Word file (.docx: WordprocessingML in a stored ZIP, written in the browser) opens whatever
    the visitor typed or pasted: every part is well-formed XML 1.0 — U+FFFE, U+FFFF, other control characters and a
    lone surrogate are left out; a tab, line breaks and a character above U+FFFF (an emoji) stay."""

    def test_xml_invalid_characters_are_left_out(self):
        nasty = "Notes\ufffe here\uffff \u0001\u0008\u000b\u001f done \ud800 lone \udc00 also 😀 pair\tand tab"
        r = run_js(self, EDITOR2 + r"""
          const a = boot();
          a.setText("notes", input.text);
          a.setTitle("committee", "Committee \uffff meeting");
          a.prof.district = "12\ufffe";
          a.download("docx");
          out({ b64: await docxBytes(), plain: a.plain() });""", data={"text": nasty}, needs_modules=False)
        z = zipfile.ZipFile(io.BytesIO(base64.b64decode(r["b64"])))
        self.assertIsNone(z.testzip())                                        # every part's CRC is right
        self.assertEqual(sorted(z.namelist()), sorted(["[Content_Types].xml", "_rels/.rels", "docProps/core.xml", "word/document.xml",
                                                       "word/styles.xml", "word/_rels/document.xml.rels"]))
        for name in z.namelist():
            with self.subTest(part=name):
                data = z.read(name).decode("utf-8")
                ET.fromstring(data)                                           # well-formed XML (a strict parser)
                self.assertNotRegex(data, "[\ufffe\uffff\u0000-\u0008\u000b\u000c\u000e-\u001f]")
        doc = z.read("word/document.xml").decode("utf-8")
        text = "".join(t.text or "" for t in ET.fromstring(doc).iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        self.assertIn("Notes here", text)
        self.assertIn(" done  lone  also 😀 pair\tand tab", text)
        self.assertIn("Committee  meeting", text)
        self.assertIn("\ufffe", r["plain"], "the text itself keeps what was typed — only the Word file leaves it out")


class LastMonthsDraft(unittest.TestCase):
    """F-9: "Start from last month's draft". A new month starts from the latest data; while this month has no draft
    of its own (in the report language) and an earlier month's is on this device, the editor offers it. Starting
    from it carries over the visitor's own parts — their sections, the order, the sections left out, changed
    titles, the counties picked, the texts of the sections that are their own words ("asks", "notes") — and the
    sections made from the site's data show this month's."""

    SEPT = {"order": ["header", "custom-1", "committee", "shop", "asks", "notes"], "off": {"shop": True},
            "text": {"committee": "September's meeting text", "asks": "Every group: a GVR by November", "notes": "My own notes"},
            "titles": {"notes": "Our district"}, "custom": [{"id": "custom-1", "title": "District news", "text": "Two new GVRs"}], "meet": []}

    def run_editor(self, store: dict, script: str):
        return run_js(self, EDITOR2 + script, data={"store": store}, needs_modules=False)

    def test_the_offer_and_what_it_carries_over(self):
        r = self.run_editor({"gv-report:2026-09:en": self.SEPT, "gv-report:2026-08:en": {"custom": [{"id": "custom-1", "title": "Old", "text": "x"}]}}, r"""
          let a = boot();
          const offered = a.prev && [a.prev.month, a.prev.label, a.prevText(), a.prevBtn()];
          a.startFromPrev();
          const d = JSON.parse(JSON.stringify(a.d));
          const after = [a.prev, a.textOf("committee"), a.textOf("asks"), a.textOf("notes"), a.titleOf("notes"), a.isOn("shop"),
                         a.plain().includes("Two new GVRs"), a.ui && a.msg];
          const again = boot();
          out({ offered, d, after, againPrev: again.prev, stored: JSON.parse(store.get("gv-report:2026-10:en")) });""")
        self.assertEqual(r["offered"], ["2026-09", "September 2026", "You worked on a September 2026 report", "Start from my September 2026 draft"])
        p, committee, asks, notes, notes_title, shop_on, custom_in, msg = r["after"]
        self.assertIsNone(p)                                                   # the offer is gone
        self.assertEqual(committee, "Text of committee", "a section made from the site's data: this month's")
        self.assertEqual((asks, notes, notes_title), ("Every group: a GVR by November", "My own notes", "Our district"))
        self.assertFalse(shop_on)                                              # left out last month: left out now
        self.assertTrue(custom_in)
        self.assertEqual(msg, "Started from September 2026")
        self.assertEqual(r["d"]["order"], ["header", "custom-1", "committee", "shop", "asks", "notes"])
        self.assertEqual(r["stored"]["text"], {"asks": "Every group: a GVR by November", "notes": "My own notes"})
        self.assertIsNone(r["againPrev"], "this month has its own draft now")

    def test_when_it_is_not_offered(self):
        r = self.run_editor({
            # only a data section edited last month (nothing that would carry over); this month blank but saved
            # (typing "Your details" saves it): the offer of an older month with own work still shows
            "gv-report:2026-09:en": {"order": ["header", "committee", "shop", "asks", "notes"], "text": {"committee": "edited"}},
            "gv-report:2026-08:en": {"custom": [{"id": "custom-1", "title": "Mine", "text": "x"}]},
            "gv-report:2026-10:en": {"order": ["header", "committee", "shop", "asks", "notes"], "off": {}, "text": {}},
            "gv-report:2026-06:en": {"custom": [{"id": "custom-1", "title": "Too old", "text": "x"}]},   # pruned: 4 months
            "gv-report:2026-09:es": {"custom": [{"id": "custom-1", "title": "Spanish one", "text": "x"}]},
        }, r"""
          const a = boot();
          const first = a.prev && a.prev.month;
          a.setText("asks", "This month's own words");        // editing this month: the offer goes
          const afterEdit = a.prev;
          a.saveNow();
          const reopened = boot().prev;
          a.setLang("es");                                    // the Spanish report: its own drafts
          const es = a.prev && a.prev.month;
          out({ first, afterEdit, reopened, es, pruned: store.has("gv-report:2026-06:en") });""")
        self.assertEqual(r["first"], "2026-08", "September's draft has nothing to carry over; August's has")
        self.assertIsNone(r["afterEdit"])
        self.assertIsNone(r["reopened"])
        self.assertEqual(r["es"], "2026-09")
        self.assertFalse(r["pruned"])


class TimedTexts(unittest.TestCase):
    """The editor shows the text of the last moment passed by its own clock (section.steps), and still reads an
    older page's single `after` (see tests/test_price_changes.py)."""

    STEPS = [{"at": "2026-10-15T05:00:00.000Z", "text": "after the offer"}, {"at": "2027-01-01T06:00:00.000Z", "text": "new prices"}]

    def test_the_text_of_the_moment(self):
        got = {}
        for now in ("2026-10-15T04:59:59Z", "2026-10-15T05:00:00Z", "2026-12-31T12:00:00Z", "2027-01-01T06:00:00Z"):
            r = run_js(self, EDITOR2 + 'out(boot().textOf("shop"));', data={"steps": self.STEPS, "now": now}, needs_modules=False)
            got[now] = r
        self.assertEqual(got, {"2026-10-15T04:59:59Z": "Text of shop", "2026-10-15T05:00:00Z": "after the offer",
                               "2026-12-31T12:00:00Z": "after the offer", "2027-01-01T06:00:00Z": "new prices"})


if __name__ == "__main__":
    unittest.main()
