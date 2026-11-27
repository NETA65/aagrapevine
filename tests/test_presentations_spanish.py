"""La Viña's presentations in Spanish (config/presentations/taller-de-escritura.yml, orientacion-rlv.yml): decks
written in Spanish (`lang: "es"`), shown and stood up like the English ones, with their facts in Spanish.

  * SpanishDecks    — both decks are there, pass the checker, say lang "es", have their own order; every slide shown
                      has notes, with Spanish labels (DI:, HAZ: …) and no TIME / TIEMPO line; each version's minutes
                      add up to what it says, and each deck keeps its English source's versions (the same ids,
                      lengths and left-out slides); the register is the Spanish site's ("tú", "ustedes", never
                      "usted" or "vosotros").
  * SpanishRules    — the checker (Python and the build's twin) takes lang "es" and refuses any other language,
                      takes the Spanish line "No es una presentación oficial de AA Grapevine, Inc." and refuses a
                      "TIEMPO:" line like a "TIME:" one.
  * SpanishBuild    — the build shapes a Spanish deck in Spanish: its lang, each slide's, "Parte 1 · …" for a part's
                      eyebrow, and its facts in Spanish (dates, the meeting's rule and time, "Datos al …", La Viña's
                      themes without an English gloss, the fallbacks: "consulta la página de Reuniones") — the English
                      decks' facts as before.
  * SpanishPlayer   — the player's words on a Spanish deck's slides and in its notes are Spanish (presentations-core.js
                      words): the TIEMPO line, "(no está en esta versión)", tidied after "diapositivas".
  * SpanishEvents   — a writing workshop held in Spanish (La Viña's: the Fort Worth workshop of December 12, 2026)
                      links taller-de-escritura, an orientation held in Spanish orientacion-rlv; an English one keeps
                      the English deck; without the Spanish deck the English one stands in.

    python -m unittest tests.test_presentations_spanish -v
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import ROOT, run_js  # noqa: E402
from test_presentations import FOLDER, check_deck  # noqa: E402

SPANISH = {"taller-de-escritura": "writing-workshop", "orientacion-rlv": "orientation-workshop"}
# the notes' English labels, which a Spanish deck's notes never use (their Spanish: DI, HAZ, PREGUNTA, CONSEJO …)
EN_LABELS = re.compile(r"^(?:\{(?:only|not):[^}]*\}\s*)?(?:SAY|DO|ASK|IF TIME, ASK|TIP|FACILITATOR TIP|TRANSITION|UPDATE|SOURCE|"
                       r"SOURCES|TIME SPLIT|TIMING|WATCH FOR)\b[^:\n]*:", re.M)
DEC12 = "2026-12-12-lv-writing-workshop-fort-worth"


def load(stem: str) -> dict:
    return yaml.safe_load((FOLDER / f"{stem}.yml").read_text(encoding="utf-8"))


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for x in node:
            yield from strings(x)
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings(v)


def sums(deck: dict) -> dict:
    """Each version's minutes, as the checker adds them: {version id: (slides, minutes)}."""
    slides = deck["slides"]
    by = {s["id"]: s for s in slides}
    base = [s for s in slides if not s.get("facilitator") and not s.get("starts_off")]
    out = {}
    for p in deck["presets"]:
        shown = [by[i] for i in p["only"]] if "only" in p else [s for s in base if s["id"] not in set(p.get("hide", []))]
        out[p["id"]] = (len(shown), sum((s.get("version_minutes") or {}).get(p["id"], s.get("minutes") or 0) for s in shown))
    return out


class SpanishDecks(unittest.TestCase):
    def test_both_are_there_and_pass_the_checker(self):
        orders = {}
        for f in sorted(FOLDER.glob("*.yml")):
            orders[f.stem] = yaml.safe_load(f.read_text(encoding="utf-8")).get("order")
        for stem in SPANISH:
            with self.subTest(deck=stem):
                self.assertTrue((FOLDER / f"{stem}.yml").exists())
                self.assertEqual(check_deck(FOLDER / f"{stem}.yml"), [])
                d = load(stem)
                self.assertEqual((d["id"], d["lang"]), (stem, "es"))
                self.assertNotIn("lang", {k for s in d["slides"] for k in s}, "the deck's lang covers every slide")
                # its own place among the cards, and the card in both languages
                self.assertEqual(list(orders.values()).count(d["order"]), 1)
                for k in ("title", "summary", "audience"):
                    self.assertTrue(d["card"][k]["en"] and d["card"][k]["es"])

    def test_every_slide_shown_has_its_notes_in_spanish(self):
        for stem in SPANISH:
            d = load(stem)
            for s in d["slides"]:
                with self.subTest(deck=stem, slide=s["id"]):
                    notes = s.get("notes") or ""
                    if not s.get("facilitator"):
                        self.assertGreaterEqual(len(notes.split()), 25)
                        self.assertRegex(notes, r"(?m)^(?:\{(?:only|not):[^}]*\}\s*)?(?:DI|HAZ|PREGUNTA|CONSEJO|POSIBLES RESPUESTAS|"
                                                r"ACTUALIZA[^:\n]*)\b[^:\n]*:", "a Spanish label on a line of its own")
                    self.assertEqual(EN_LABELS.findall(notes), [], "the notes' labels are Spanish")
                    self.assertNotRegex(notes, r"(?m)^\s*(?:TIME|TIEMPO):", "the player writes the time line")

    def test_the_versions_add_up_as_in_the_english_decks(self):
        for stem, english in SPANISH.items():
            es, en = load(stem), load(english)
            with self.subTest(deck=stem):
                got = sums(es)
                for p in es["presets"]:
                    self.assertLessEqual(abs(got[p["id"]][1] - p["minutes"]), 3, f"{p['id']}: {got[p['id']][1]} minutes")
                # the English source's versions: the same ids and lengths, the same slides left out, the same sums
                self.assertEqual([(p["id"], p["minutes"]) for p in es["presets"]], [(p["id"], p["minutes"]) for p in en["presets"]])
                self.assertEqual([p.get("hide") for p in es["presets"]], [p.get("hide") for p in en["presets"]])
                self.assertEqual({k: v[1] for k, v in got.items()}, {k: v[1] for k, v in sums(en).items()})
                self.assertEqual(es["minutes"], en["minutes"])

    def test_the_spanish_sites_register(self):
        # "tú" to one person, "ustedes" to the room (src/_i18n's Spanish): never "usted", never Spain's "vosotros"
        for stem in SPANISH:
            text = "\n".join(strings(load(stem)))
            with self.subTest(deck=stem):
                self.assertNotRegex(text, r"(?i)\busted\b|\bvosotr|\bhabéis\b|\bpodéis\b|\bsabéis\b")
                self.assertRegex(text, r"\bustedes\b")
                self.assertRegex(text, r"\bEscribe\b|\bescribe tu\b|\btu historia\b")

    def test_no_invented_contact(self):
        # every e-mail address is one the English decks or config/site.yml already give
        known = set()
        for f in list(FOLDER.glob("*.yml")) + [ROOT / "config" / "site.yml"]:
            if f.stem not in SPANISH:
                known |= set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", f.read_text(encoding="utf-8")))
        for stem in SPANISH:
            used = set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", (FOLDER / f"{stem}.yml").read_text(encoding="utf-8")))
            with self.subTest(deck=stem):
                self.assertTrue(used)
                self.assertLessEqual(used, known)

    def test_the_spanish_quotations_are_the_repositorys(self):
        # the Preamble and the Responsibility Statement word for word as orientation-workshop.yml gives them in Spanish
        src = (FOLDER / "orientation-workshop.yml").read_text(encoding="utf-8")
        for stem in SPANISH:
            quotes = [s for s in load(stem)["slides"] if s["layout"] == "quote"]
            with self.subTest(deck=stem):
                self.assertEqual({s["id"] for s in quotes}, {"preamble", "responsibility"})
                for s in quotes:
                    for para in [p for p in re.split(r"\n+", s["quote"]) if p.strip()]:
                        self.assertIn(para.strip(), src)
                    self.assertTrue(s["credit"].strip())


class SpanishRules(unittest.TestCase):
    """The checker's language rules, in Python and in the build (eleventy/filters/presentations.js checkDeck)."""

    def deck(self, lang: str, notes_extra: str = "", disclaimer: str = "No es una presentación oficial de AA Grapevine, Inc.") -> dict:
        words = "DI: " + " ".join(["palabra"] * 30)
        return {
            "id": "prueba", "order": 1, "lang": lang, "title": "T", "short": "S", "eyebrow": "E", "footer": "F",
            "minutes": 10, "icon": "book-open", "tone": "lv",
            "card": {k: {"en": "a", "es": "b"} for k in ("title", "summary", "audience")},
            "presets": [{"id": "full", "label": {"en": "Full", "es": "Completo"}, "minutes": 10}],
            "slides": [{"id": f"s{i}", "layout": "bullets", "title": "Hola", "items": ["Uno"], "notes": words + notes_extra,
                        "minutes": 2} for i in range(4)]
                      + [{"id": "c", "layout": "credits", "title": "Créditos", "sources": ["x"], "note": disclaimer,
                          "notes": words, "minutes": 2}],
        }

    def problems(self, d: dict) -> tuple[list, list]:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "prueba.yml"
            p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
            py = check_deck(p)
            js = run_js(self, 'const P = await imp("eleventy/filters/presentations.js"); out(P.loadDecks(input.dir).problems);',
                        data={"dir": tmp})
        return sorted(py), sorted(x.split(": ", 1)[1] for x in js)

    def test_a_spanish_deck_passes(self):
        py, js = self.problems(self.deck("es"))
        self.assertEqual((py, js), ([], []))

    def test_another_language_is_refused(self):
        py, js = self.problems(self.deck("fr"))
        self.assertEqual(py, ['lang: "en" or "es" (the language the presentation is written in)'])
        self.assertEqual(js, py, "the build's checker says the same")

    def test_the_disclaimer_in_either_language_and_no_tiempo_line(self):
        self.assertEqual(self.problems(self.deck("es", disclaimer="Not an official AA Grapevine, Inc. presentation."))[0], [])
        py, js = self.problems(self.deck("es", disclaimer="Una presentación del comité."))
        self.assertEqual(py, ['no slide says "Not an official AA Grapevine, Inc. presentation" (keep it, as in the deck)'])
        self.assertEqual(js, py)
        py, js = self.problems(self.deck("es", notes_extra="\nTIEMPO: unos 2 minutos"))
        self.assertTrue(py and all("no TIME: line in the notes" in x for x in py), py)
        self.assertEqual(js, py)


# The two Spanish decks shaped and built with made-up data at a fixed clock, beside the English writing workshop
BUILD_JS = r"""
const P = await imp("eleventy/filters/presentations.js");
const val = async (m) => { const d = (await imp(m)).default; return typeof d === "function" ? await d() : d; };
const site = { ...(await val("src/_data/site.js")), url: "https://x.test/aagrapevine", built: input.now };
const now = new Date(input.now);
const { decks, problems } = P.loadDecks("config/presentations", { now, shop: {} });
const db = { editorial: { items: input.editorial }, events: { items: [] } };
const pick = (d) => { const j = P.deckJson(d, { db, site, carry: {}, meeting: null, now });
  const v = (k) => (typeof j.live[k] === "string" ? j.live[k] : j.live[k].value);
  const fb = (k) => (typeof j.live[k] === "string" ? "" : j.live[k].fallback || "");
  return { lang: j.lang, as_of: j.as_of, rule: v("meeting_rule"), time: v("meeting_time"), next: v("meeting_next"),
    deadline: v("next_deadline_lv"), fbLv: fb("lv_workshop_next"), fbMeet: fb("meeting_link"), month: v("month"),
    rows: (j.slides.find((s) => s.id === "lv-themes" || s.id === "deadlines") || {}).data,
    eyebrows: j.slides.filter((s) => s.part && !s.facilitator && s.layout !== "section" && s.layout !== "qa" && s.layout !== "credits")
      .map((s) => [s.id, s.eyebrow]), langs: [...new Set(j.slides.map((s) => s.lang))] }; };
const by = Object.fromEntries(decks.map((d) => [d.id, d]));
// no data at all: every fact says where to look, in the deck's language
const empty = P.deckJson(by["taller-de-escritura"], { db: {}, site: { url: site.url }, now });
out({ problems, cards: decks.map((d) => [d.id, d.lang]),
      es: pick(by["taller-de-escritura"]), rlv: pick(by["orientacion-rlv"]), en: pick(by["writing-workshop"]),
      emptyLive: empty.live, fallbacksEs: P.FALLBACKS_ES, fallbacks: P.FALLBACKS });
"""
EDITORIAL = [
    {"id": "ed:lv:2027-07", "lang": "es", "title": "Prisiones", "i18n": {"title": {"en": "Prisons", "es": "Prisiones"}},
     "extra": {"publication": "lv", "issue_key": "2027-07", "deadline": "2026-12-15"}},
    {"id": "ed:gv:2027-07", "lang": "en", "title": "Annual Prison Issue",
     "extra": {"publication": "gv", "issue_key": "2027-07", "deadline": "2026-12-01"}},
]


class SpanishBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def got(self) -> dict:
        if SpanishBuild.r is None:
            SpanishBuild.r = run_js(self, BUILD_JS, data={"now": "2026-11-26T18:00:00Z", "editorial": EDITORIAL},
                                    now="2026-11-26T18:00:00Z")
        return SpanishBuild.r

    def test_the_decks_and_their_language(self):
        r = self.got()
        self.assertEqual(r["problems"], [])
        cards = dict(r["cards"])
        self.assertEqual((cards["taller-de-escritura"], cards["orientacion-rlv"], cards["writing-workshop"]), ("es", "es", "en"))
        self.assertEqual({k for k, v in cards.items() if v == "es"} >= set(SPANISH), True)
        for k in ("es", "rlv"):
            with self.subTest(deck=k):
                self.assertEqual((r[k]["lang"], r[k]["langs"]), ("es", ["es"]))
                # a part's eyebrow in Spanish, never "Part 1 · …"
                self.assertTrue(r[k]["eyebrows"])
                for sid, brow in r[k]["eyebrows"]:
                    self.assertNotRegex(brow, r"^Part \d", sid)
                self.assertTrue(any(b.startswith("Parte ") for _, b in r[k]["eyebrows"]))
        # the English deck: English, its own Spanish handouts aside (their own lang: "es")
        self.assertEqual((r["en"]["lang"], r["en"]["langs"][0]), ("en", "en"))

    def test_the_facts_in_spanish(self):
        r = self.got()
        es, en = r["es"], r["en"]
        self.assertEqual(es["as_of"], "26 de noviembre de 2026")
        self.assertEqual(en["as_of"], "November 26, 2026")
        self.assertEqual(es["rule"], "cada tercer miércoles del mes")
        self.assertEqual(en["rule"], "every third Wednesday of the month")
        self.assertRegex(es["time"], r"p\. m\., hora del Centro$")
        self.assertRegex(es["next"], r"^miércoles, \d{1,2} de [a-z]+ de \d{4}$", "a date inside a Spanish sentence")
        self.assertEqual(es["month"], "noviembre de 2026")
        # La Viña's theme in Spanish without an English gloss; the English deck keeps its gloss
        self.assertEqual(es["deadline"], "15 de diciembre de 2026 — Julio–Agosto 2027: Prisiones")
        self.assertEqual(en["deadline"], "December 15, 2026 — July–August 2027: Prisiones (Prisons)")
        row = es["rows"]["rows"][0]
        self.assertEqual((row["due_label"], row["issue"], row["theme"], row["theme_lang"], row["gloss"]),
                         ("15 de diciembre de 2026", "Julio–Agosto 2027", "Prisiones", "es", ""))
        self.assertTrue(es["rows"]["url"].endswith("/aagrapevine/es/contribute/#deadlines"), "the Spanish page")
        self.assertTrue(en["rows"]["url"].endswith("/aagrapevine/contribute/#deadlines"))
        self.assertEqual(es["fbLv"], "consulta el calendario de eventos de La Viña en aalavina.org")

    def test_every_fallback_has_its_spanish(self):
        r = self.got()
        self.assertEqual(set(r["fallbacksEs"]), set(r["fallbacks"]))
        for k, v in r["fallbacksEs"].items():
            with self.subTest(key=k):
                self.assertTrue(v.strip())
                self.assertNotEqual(v, r["fallbacks"][k], "its own Spanish words")
        # with no data, a Spanish deck's facts say where to look in Spanish
        live = r["emptyLive"]
        for k in ("meeting_next", "lv_workshop_next", "next_deadline_lv", "lv_issue", "lv_audio_phone", "assembly_next"):
            with self.subTest(empty=k):
                v = live[k] if isinstance(live[k], str) else live[k].get("fallback", "")
                self.assertEqual(v, r["fallbacksEs"][k])


CORE_JS = r"""
import vm from "node:vm";
const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync("src/assets/js/presentations-core.js", "utf8"), ctx);
const G = ctx.GVP;
const entry = { shown: true, mins: 1.5, end: 12, slide: { optional: true } };
const deck = (lang) => ({ id: "x", lang, presets: [{ id: "full" }], fillins: [], live: {},
  slides: [{ id: "a", layout: "bullets", items: ["x"], minutes: 1 }, { id: "b", layout: "bullets", items: ["y"], minutes: 1, starts_off: true }] });
const ref = (lang, text) => { const d = deck(lang); const st = G.emptyState(); const cur = G.current(d, st, "", Date.now());
  return G.subst(text, { deck: d, state: st, cur, where: "notes" }); };
// a link to a page of the site, in a slide's text and on a resources card (safeHref + showUrl, as the player does),
// for a deck in each language on each page
const hrefs = (nodes) => nodes.flatMap((n) => (n.t === "a" ? [n.href] : []).concat(n.c ? hrefs(n.c) : []));
const link = (lang, page) => { const d = deck(lang);
  return { text: hrefs(G.rich("[aquí](/contribute/) · [web](https://www.aalavina.org/)", { deck: d, base: "/aagrapevine/", lang: page })),
           card: G.safeHref("/contribute/", { base: "/aagrapevine/", lang: G.linkLang(d, page) }),
           shown: G.showUrl("/contribute/", "grapevine.neta65.org", d.lang),
           other: G.showUrl("https://www.aalavina.org/", "grapevine.neta65.org", d.lang) }; };
const links = { esOnEn: link("es", "en"), esOnEs: link("es", "es"), enOnEn: link("en", "en"), enOnEs: link("en", "es") };
out({ es: G.timeLine(entry, "es"), en: G.timeLine(entry), enLang: G.timeLine(entry, "en"), about: G.aboutText(0.5, "es"),
      one: [G.timeLine(Object.assign({}, entry, { mins: 1, slide: {} }), "es"), G.timeLine(Object.assign({}, entry, { mins: 0.75, slide: {} }), "es"),
            G.timeLine(Object.assign({}, entry, { mins: 2, slide: {} }), "es")],
      leftEs: ref("es", "las diapositivas {slide:b} y la {slide:a}"), leftEn: ref("en", "slides {slide:b} and {slide:a}"),
      words: [G.words("es").current_as_of, G.words("es").tentative, G.words("en").tentative, G.words("fr") === G.EN],
      disclaimer: G.words("es").disclaimer, links: links });
"""


class SpanishPlayer(unittest.TestCase):
    def test_the_players_words_in_the_decks_language(self):
        r = run_js(self, CORE_JS, needs_modules=False)
        self.assertEqual(r["es"], "TIEMPO: alrededor de 1½ minutos (opcional: se puede quitar si vas con retraso). Al pasar a la siguiente deberías ir por 0:12.")
        # one minute, seconds, whole minutes: never "unos 1 minuto" (wrong Spanish: "unos" with a single minute)
        self.assertEqual(r["one"], ["TIEMPO: alrededor de 1 minuto. Al pasar a la siguiente deberías ir por 0:12.",
                                    "TIEMPO: alrededor de 45 segundos. Al pasar a la siguiente deberías ir por 0:12.",
                                    "TIEMPO: alrededor de 2 minutos. Al pasar a la siguiente deberías ir por 0:12."])
        self.assertNotIn("unos 1 minuto", " ".join(r["one"]))
        self.assertEqual(r["en"], "TIME: about 1½ minutes (optional: it can go when you're running late). You should be at about 0:12 when you move on.")
        self.assertEqual(r["enLang"], r["en"])
        self.assertEqual(r["about"], "30 segundos")
        # a slide the version leaves out: in the deck's language, and "slides (…)" / "diapositivas (…)" tidied
        self.assertEqual(r["leftEs"], "las (no está en esta versión) y la 1")
        self.assertEqual(r["leftEn"], "(not in this version) and 1")
        self.assertEqual(r["words"], ["Datos al {date}", "Detalles por confirmar", "Details to be confirmed", True])
        self.assertTrue(r["disclaimer"][0].startswith("No es una presentación oficial de AA Grapevine, Inc."))
        # a Spanish deck's links to the site show and open its Spanish pages, on the English page too (never
        # /es/es/ on the Spanish page); an English deck's follow the page, as before; other sites are left alone
        es = {"text": ["/aagrapevine/es/contribute/", "https://www.aalavina.org/"], "card": "/aagrapevine/es/contribute/",
              "shown": "grapevine.neta65.org/es/contribute/", "other": "aalavina.org"}
        self.assertEqual(r["links"]["esOnEn"], es)
        self.assertEqual(r["links"]["esOnEs"], es)
        self.assertEqual(r["links"]["enOnEn"], {"text": ["/aagrapevine/contribute/", "https://www.aalavina.org/"],
                                                "card": "/aagrapevine/contribute/", "shown": "grapevine.neta65.org/contribute/",
                                                "other": "aalavina.org"})
        self.assertEqual(r["links"]["enOnEs"]["text"][0], "/aagrapevine/es/contribute/")
        self.assertEqual((r["links"]["enOnEs"]["card"], r["links"]["enOnEs"]["shown"]),
                         ("/aagrapevine/es/contribute/", "grapevine.neta65.org/contribute/"))

    def test_the_screen_marks_the_decks_language(self):
        js = (ROOT / "src" / "assets" / "js" / "presentations.js").read_text(encoding="utf-8")
        self.assertNotIn("G.EN.", js, "the player writes a deck's words in its language (W(deck))")
        self.assertIn('qa("[data-gvp-in]")', js)
        macro = (ROOT / "src" / "_includes" / "macros" / "presentations.njk").read_text(encoding="utf-8")
        for key in ("pres.in_english", "pres.in_spanish", "pres.notes_en", "pres.notes_es"):
            self.assertIn(key, macro)
        self.assertNotIn('{% if lang == "es" %} <span class="gvp-top-lang">', macro, "never '(en inglés)' for every deck")


# The Fort Worth workshop of December 12, 2026 (content/events), as data/site/events.json holds it — or, once a sync
# has dropped it, the same record made from its file's own words — on its event pages, with the site's decks.
EVENTS_JS = r"""
const M = await imp("eleventy/event-page-model.js");
const E = await imp("eleventy/event-pages.js");
const val = async (m) => { const d = (await imp(m)).default; return typeof d === "function" ? await d() : d; };
const site = { ...(await val("src/_data/site.js")), built: input.now, url: "https://x.test" };
const decks = (await val("src/_data/presentations.js")).decks;
const page = (items, ds) => {
  const full = { db: { events: { items, cancelled: [] }, drive: { items: [] }, pdfs: { items: [] }, announcements: { items: [] },
                       audio_project: {}, articles: { items: [], issues: [] } },
                 site, languages: ["en", "es"], presentations: { decks: ds, problems: [] }, orientation: { lessons: [] },
                 carry: {}, monthlyKeys: [] };
  return Object.fromEntries(M.eventPageData(full).pages.filter((p) => input.anchors.includes(p.anchor))
    .map((p) => [p.anchor + ":" + p.lang, p.m.prep.deck ? [p.m.prep.deck.id, p.m.prep.deck.lang, p.m.prep.deck.href] : null]));
};
const kinds = Object.fromEntries(input.items.map((it) => { const k = E.eventKind(it, site); return [it.extra.slug, [k.kind, k.spanish, k.deck, k.deckEs]]; }));
out({ decks: decks.map((d) => d.id), withSpanish: page(input.items, decks),
      withoutSpanish: page(input.items, decks.filter((d) => d.lang !== "es")), kinds });
"""


def event_item(slug: str, title: str, start: str, end: str, tags: list, title_es: str = "", location: str = "") -> dict:
    """An event as data/site/events.json holds a content/events file's (build_data: category manual)."""
    it = {"id": f"ev:manual:{slug}", "source": "committee", "kind": "event", "category": "manual", "url": "", "title": title,
          "summary": f"About {title}.", "lang": "en", "date": start, "status": "ok", "tags": tags,
          "extra": {"start": start, "end": end, "all_day": False, "slug": slug, "location": location or None,
                    "online_url": None, "city": None, "state": None}}
    if title_es:
        it["i18n"] = {"title": {"en": title, "es": title_es}}
        it["extra"]["own_i18n"] = {"title": {"es": title_es}}
    return it


def dec12() -> dict:
    """The December 12 workshop's record: the synced one, else one made from its content/events file."""
    items = json.loads((ROOT / "data" / "site" / "events.json").read_text(encoding="utf-8")).get("items") or []
    hit = next((it for it in items if it.get("id") == f"ev:manual:{DEC12}"), None)
    if hit:
        return hit
    text = (ROOT / "content" / "events" / f"{DEC12}.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---")[1])
    return event_item(DEC12, fm["title"], str(fm["start"]).replace(" ", "T"), str(fm["end"]).replace(" ", "T"), fm["tags"],
                      fm.get("title_es", ""), fm.get("location", ""))


class SpanishEvents(unittest.TestCase):
    def test_spanish_workshops_link_the_spanish_decks(self):
        items = [
            dec12(),
            event_item("2099-01-09-gv-writing-workshop-plano", "Grapevine Writing Workshop — Plano", "2099-01-09T14:00:00-06:00",
                       "2099-01-09T17:00:00-06:00", ["workshop", "grapevine"], location="Grupo Dos, 2 Elm St, Plano, TX 75074"),
            event_item("2099-01-16-rlv-orientation-dallas", "GVR/RLV Orientation Workshop (in Spanish) — Dallas",
                       "2099-01-16T10:00:00-06:00", "2099-01-16T13:00:00-06:00", ["workshop", "la-vina"],
                       title_es="Orientación para RLV y GVR — Dallas", location="Grupo Tres, 3 Oak St, Dallas, TX 75201"),
            # a joint Grapevine and La Viña workshop held in English: the English deck, never the Spanish one
            event_item("2099-01-23-gv-lv-writing-workshop-irving", "Grapevine & La Viña Writing Workshop — Irving",
                       "2099-01-23T10:00:00-06:00", "2099-01-23T13:00:00-06:00", ["workshop", "grapevine", "la-vina"],
                       location="Grupo Cuatro, 4 Pine St, Irving, TX 75060"),
            # the same, said to be held in Spanish: the Spanish deck
            event_item("2099-01-30-gv-lv-writing-workshop-garland", "Grapevine & La Viña Writing Workshop (in Spanish) — Garland",
                       "2099-01-30T10:00:00-06:00", "2099-01-30T13:00:00-06:00", ["workshop", "grapevine", "la-vina"],
                       location="Grupo Cinco, 5 Ash St, Garland, TX 75040"),
        ]
        anchors = [it["extra"]["slug"] for it in items]
        r = run_js(self, EVENTS_JS, data={"items": items, "anchors": anchors, "now": "2026-11-26T18:00:00Z"},
                   now="2026-11-26T18:00:00Z")
        self.assertLessEqual(set(SPANISH), set(r["decks"]))
        k = r["kinds"]
        self.assertEqual(k[DEC12], ["writing-workshop", True, "writing-workshop", "taller-de-escritura"])
        self.assertEqual(k["2099-01-09-gv-writing-workshop-plano"], ["writing-workshop", False, "writing-workshop", ""])
        self.assertEqual(k["2099-01-16-rlv-orientation-dallas"], ["gvr-orientation", True, "orientation-workshop", "orientacion-rlv"])
        self.assertEqual(k["2099-01-23-gv-lv-writing-workshop-irving"][2:], ["writing-workshop", ""])
        self.assertEqual(k["2099-01-30-gv-lv-writing-workshop-garland"][2:], ["writing-workshop", "taller-de-escritura"])
        w = r["withSpanish"]
        for lang, pre in (("en", ""), ("es", "/es")):
            with self.subTest(lang=lang):
                # the December 12 workshop: "Start the presentation" opens taller-de-escritura, on both pages
                self.assertEqual(w[f"{DEC12}:{lang}"], ["taller-de-escritura", "es", f"{pre}/orientation/?present=taller-de-escritura"])
                self.assertEqual(w[f"2099-01-09-gv-writing-workshop-plano:{lang}"][:2], ["writing-workshop", "en"])
                self.assertEqual(w[f"2099-01-16-rlv-orientation-dallas:{lang}"][:2], ["orientacion-rlv", "es"])
                # without the Spanish decks, the English ones stand in
                wo = r["withoutSpanish"]
                self.assertEqual(wo[f"{DEC12}:{lang}"][:2], ["writing-workshop", "en"])
                self.assertEqual(wo[f"2099-01-16-rlv-orientation-dallas:{lang}"][:2], ["orientation-workshop", "en"])

    def test_the_built_pages(self):
        # (after a build: the December 12 event's pages, as tests/browser and CI build the site)
        site = ROOT / "_site"
        pages = {lang: site / pre / "events" / DEC12 / "index.html" for lang, pre in (("en", ""), ("es", "es"))}
        if not all(p.exists() for p in pages.values()):
            self.skipTest("no built site with the December 12 workshop (build it first)")
        for lang, p in pages.items():
            html = p.read_text(encoding="utf-8")
            deck = re.search(r'<article class="card card-pad evp-deck".*?</article>', html, re.S)
            with self.subTest(lang=lang):
                self.assertIsNotNone(deck)
                self.assertIn("?present=taller-de-escritura", deck.group(0))
                self.assertNotIn("?present=writing-workshop", deck.group(0))
                self.assertEqual("Presentation in Spanish" in deck.group(0), lang == "en")
                self.assertNotIn("Presentación en inglés", deck.group(0))


if __name__ == "__main__":
    unittest.main()
