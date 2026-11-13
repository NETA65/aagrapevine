"""Editorial themes and deadlines (scripts/sync/editorial.py → data/raw/editorial.json): La Viña's yearly themes.

La Viña posts its themes once a year as a document linked from aalavina.org/recursos ("Temas de LV 2026 y 2027" →
Temas_de_LV_2027_2026.pdf: one page per year, six bimonthly issues, each with its theme and the day to send a story
by). Fixtures in tests/fixtures/editorial/ (offline — nothing here goes to the network):
  lv_temas_2027_2026.txt  the document's text exactly as pypdfium2 gives it (October 2, 2026), its two pages
                          separated by a form feed: the 2027 page (issues first, then the themes, the title last, the
                          address line with every letter doubled) and the 2026 page (its title is a picture: no year)
  lv_recursos.html        a trimmed copy of the resources page that links it
Run:  python -m unittest tests.test_editorial -v   (CI: python -m unittest discover -s tests)
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync import articles as A  # noqa: E402
from scripts.sync import editorial as E  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "editorial"
LV = "https://www.aalavina.org"
RESOURCES = f"{LV}/recursos"
DOC = f"{LV}/sites/default/files/2026-01/Temas_de_LV_2027_2026.pdf"
CFG = {"sources": {"grapevine": {"base": "https://www.aagrapevine.org"},
                   "lavina": {"base": LV, "themes_page": "/recursos", "themes_link": "\\btemas\\b"}}}
TODAY = date(2026, 10, 2)

THEMES_2027 = ["Nuevos", "Apadrinamiento", "Recaídas", "Prisiones", "Hispanos Veteranos en AA", "Celebrando en sobriedad"]
THEMES_2026 = ["Nuevos", "Jóvenes en AA", "Pase lo que pase", "Prisiones", "El amor al servicio", "La alegría de vivir"]


def fx(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def pages() -> list[str]:
    return fx("lv_temas_2027_2026.txt").split("\f")


def remove_line(text: str, line: str) -> str:
    return "\n".join(x for x in text.split("\n") if x != line)


def blank_pdf(n_pages: int) -> bytes:
    """A document with n blank pages (no text) — made with pypdfium2 itself."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument.new()
    for _ in range(n_pages):
        pdf.new_page(612, 792)
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    return buf.getvalue()


def prev_topic(key: str, theme: str, deadline: str, pub: str = "lv") -> dict:
    """A dated topic as an earlier run saved it."""
    y, m = map(int, key.split("-"))
    return {"id": f"ed:{pub}:{key}:{E.slugify(theme, 48)}", "source": "lavina" if pub == "lv" else "grapevine",
            "kind": "topic", "url": DOC, "title": theme, "summary": "", "lang": "es", "date": deadline,
            "first_seen": "2026-01-10T07:00:00Z", "last_seen": "2026-09-30T07:00:00Z", "image": None, "tags": [],
            "category": pub, "status": "ok",
            "extra": {"publication": pub, "issue_key": key, "issue_label": E.lv_issue_label(y, m), "deadline": deadline,
                      "theme": theme, "evergreen": False}}


def evergreen(theme: str) -> dict:
    return {"id": f"ed:lv:any:{E.slugify(theme, 48)}", "source": "lavina", "kind": "topic",
            "url": f"{LV}/temas-sugeridos", "title": theme, "summary": "", "lang": "es", "date": None,
            "first_seen": "2026-09-23T16:30:40Z", "last_seen": "2026-10-01T07:21:39Z", "image": None, "tags": [],
            "category": "lv", "status": "ok", "extra": {"publication": "lv", "theme": theme, "evergreen": True}}


class Parser(unittest.TestCase):
    def setUp(self):
        self.rows, self.meta = E.parse_lv_themes(pages())

    def test_every_year_in_the_document(self):
        self.assertEqual(self.meta["years"], [2026, 2027])
        self.assertEqual(self.meta["pages"], 2)
        self.assertEqual(len(self.rows), 12)
        by_year = {y: [r for r in self.rows if r["issue_year"] == y] for y in (2026, 2027)}
        self.assertEqual([r["theme"] for r in by_year[2027]], THEMES_2027)
        self.assertEqual([r["theme"] for r in by_year[2026]], THEMES_2026)
        for y in (2026, 2027):
            self.assertEqual([(r["issue_month"], r["issue_month2"]) for r in by_year[y]],
                             [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)])

    def test_deadlines_issues_and_labels(self):
        r = {(x["issue_year"], x["issue_month"]): x for x in self.rows}
        self.assertEqual((r[2027, 1]["deadline"], r[2027, 1]["due_text"]), ("2026-07-30", "30 de julio del 2026"))
        self.assertEqual(r[2027, 5]["deadline"], "2026-10-17")
        self.assertEqual(r[2027, 11]["deadline"], "2027-04-03")
        self.assertEqual(r[2026, 11]["deadline"], "2026-04-03")      # the 2026 page: its year from the deadlines
        self.assertEqual(r[2027, 5]["issue_label"], "Mayo / Junio 2027")
        self.assertEqual(r[2026, 11]["issue_label"], "Noviembre / Diciembre 2026")
        self.assertTrue(all(x["lang"] == "es" for x in self.rows))
        self.assertEqual([x["deadline"] for x in self.rows], sorted(x["deadline"] for x in self.rows))

    def test_each_years_address(self):
        # the address line comes out of the text layer with every letter doubled
        self.assertEqual(self.meta["emails"], {"2027": "lveditorial@aagrapevine.org",
                                               "2026": "manuscritoslv@aagrapevine.org"})
        self.assertTrue(all(x["submit_email"] == "lveditorial@aagrapevine.org" for x in self.rows if x["issue_year"] == 2027))

    def test_labels_as_articles_writes_them(self):
        for m in (1, 3, 5, 7, 9, 11):
            self.assertEqual(E.lv_issue_label(2027, m, m + 1), A.label_from_key("lv", f"2027-{m:02d}"))
            self.assertEqual(E.lv_issue_label(2027, m), A.label_from_key("lv", f"2027-{m:02d}"))

    def test_doubled_lines_are_read_once(self):
        self.assertEqual(E._undouble("EEnnvvííaa ttuu hhiissttoorriiaall aa llvveeddiittoorriiaall@@aaaaggrraappeevviinnee..oorrgg"),
                         "Envía tu historial a lveditorial@aagrapevine.org")
        for same in ("Hispanos Veteranos en AA", "AA", "Pase lo que pase", "Llamada"):
            self.assertEqual(E._undouble(same), same)

    def test_windows_line_ends_and_interleaved_layout(self):
        crlf = [p.replace("\n", "\r\n") for p in pages()]
        self.assertEqual(E.parse_lv_themes(crlf)[0], self.rows)
        # the same page in reading order: issue, theme, deadline — and the title first
        issues = ["Enero/Febrero", "Marzo/Abril", "Mayo/Junio", "Julio/Agosto", "Septiembre/Octubre", "Noviembre/Diciembre"]
        dls = ["30 de julio del 2026", "3 de septiembre del 2026", "17 de octubre del 2026", "15 de diciembre del 2026",
               "2 de febrero del 2027", "3 de abril del 2027"]
        lines = ["LA VIÑA", "Temas de la revista para 2027"]
        for i, t, d in zip(issues, THEMES_2027, dls):
            lines += [i, t, "Fecha límite para enviar tu historial:", d]
        rows, meta = E.parse_lv_themes(["\n".join(lines)])
        self.assertEqual([(x["issue_year"], x["issue_month"], x["theme"], x["deadline"]) for x in rows],
                         [(x["issue_year"], x["issue_month"], x["theme"], x["deadline"]) for x in self.rows
                          if x["issue_year"] == 2027])
        self.assertEqual(meta["emails"], {})
        self.assertNotIn("submit_email", {k for x in rows for k, v in x.items() if v})

    def test_a_theme_over_two_lines_or_on_its_deadlines_line(self):
        p = pages()[0].replace("Hispanos Veteranos en AA\n", "Hispanos Veteranos\nen AA\n")
        rows, _ = E.parse_lv_themes([p])
        self.assertEqual(rows[4]["theme"], "Hispanos Veteranos en AA")
        p = pages()[0].replace("Prisiones\nFecha límite", "Prisiones Fecha límite")
        self.assertEqual(E.parse_lv_themes([p])[0], self.rows[6:])

    def test_a_title_with_two_years_takes_the_years_from_the_deadlines(self):
        p = pages()[0].replace("Temas de la revista para 2027", "Temas de LV 2026 y 2027")
        rows, _ = E.parse_lv_themes([p])
        self.assertEqual({x["issue_year"] for x in rows}, {2027})

    def test_a_deadline_without_its_year(self):
        p = pages()[0].replace("historial: 30 de julio del 2026", "historial: 30 de julio")
        rows, _ = E.parse_lv_themes([p])
        self.assertEqual(rows[0]["deadline"], "2026-07-30")       # the latest July 30 before January 2027


class ChangedLayout(unittest.TestCase):
    """Anything not understood is an error (ThemesError): a changed layout is never published half-read."""

    def assertProblem(self, pgs: list[str], words: str):
        with self.assertRaisesRegex(E.ThemesError, words):
            E.parse_lv_themes(pgs)

    def test_a_missing_theme(self):
        self.assertProblem([remove_line(pages()[0], "Recaídas")], "the theme for Mayo/Junio could not be read")
        p = pages()[0].replace("Recaídas\nFecha límite para enviar tu\nhistorial: 17 de octubre del 2026\n", "")
        self.assertProblem([p], "6 issues but 5 themes")

    def test_a_missing_issue(self):
        self.assertProblem([remove_line(pages()[0], "Julio/Agosto")], "5 issues but 6 themes")

    def test_deadlines_out_of_order(self):
        p = pages()[0].replace("historial: 3 de septiembre del 2026", "historial: 3 de septiembre del 2025")
        self.assertProblem([p], "does not fit an issue of 2027|not in the issues' order")

    def test_a_deadline_that_cannot_be_read(self):
        p = pages()[0].replace("historial: 17 de octubre del 2026", "historial: pronto")
        self.assertProblem([p], "deadline for Mayo/Junio could not be read")

    def test_a_deadline_after_its_issue(self):
        p = pages()[0].replace("historial: 3 de abril del 2027", "historial: 3 de diciembre del 2027")
        self.assertProblem([p], "does not fit an issue of 2027")

    def test_not_the_themes_document(self):
        self.assertProblem(["Catálogo 2026\nLibros de La Viña\nPrecios"], "no issues with a theme")
        self.assertProblem(["", ""], "no issues with a theme")

    def test_two_themes_for_one_issue(self):
        other = pages()[0].replace("Recaídas", "Recuperación")
        self.assertProblem([pages()[0], other], "two themes for Mayo / Junio 2027")
        self.assertEqual(len(E.parse_lv_themes([pages()[0], pages()[0]])[0]), 6)   # a page repeated: read once

    def test_unreadable_documents(self):
        with self.assertRaisesRegex(E.ThemesError, "could not be opened"):
            E.document_pages(b"<html><body>Site maintenance</body></html>")
        with self.assertRaises(E.ThemesError):                              # no pages (PDFium will not even open it)
            E.document_pages(blank_pdf(0))
        self.assertEqual(E.document_pages(blank_pdf(2)), ["", ""])           # readable, but no text: no themes
        with self.assertRaisesRegex(E.ThemesError, "13 pages"):
            E.document_pages(blank_pdf(13))


class LinkFinder(unittest.TestCase):
    def test_the_resources_page(self):
        link = E.find_themes_link(fx("lv_recursos.html"), RESOURCES)
        self.assertEqual(link, {"url": DOC, "label": "Temas de LV 2026 y 2027", "year": 2027})

    def test_the_newest_document(self):
        html = fx("lv_recursos.html")
        older = '<a href="/sites/default/files/2025-01/Temas_de_LV_2026_2025.pdf">Temas de LV 2025 y 2026</a>'
        newer = '<a href="/sites/default/files/2027-01/Temas-de-LV-2028.pdf"><img src="x.png" alt="Temas de LV 2028"></a>'
        self.assertEqual(E.find_themes_link(html.replace("</main>", older + "</main>"), RESOURCES)["url"], DOC)
        got = E.find_themes_link(html.replace("</main>", older + newer + "</main>"), RESOURCES)
        self.assertEqual(got, {"url": f"{LV}/sites/default/files/2027-01/Temas-de-LV-2028.pdf",
                               "label": "Temas de LV 2028", "year": 2028})
        # the same years: the newer upload folder
        again = '<a href="/sites/default/files/2026-03/Temas_de_LV_2027_2026_v2.pdf">Temas de LV 2026 y 2027</a>'
        self.assertIn("2026-03", E.find_themes_link(html.replace("</main>", again + "</main>"), RESOURCES)["url"])

    def test_what_is_not_the_themes_document(self):
        html = fx("lv_recursos.html").replace("Temas_de_LV_2027_2026.pdf", "Calendario.pdf").replace(
            "Temas de LV 2026 y 2027", "Calendario de La Viña")
        self.assertIsNone(E.find_themes_link(html, RESOURCES))      # the menu's and the footer's do not count
        for a in ('<a href="/temas-sugeridos-2027">Temas sugeridos 2027</a>',                # a page, not a document
                  '<a href="/sites/default/files/2026-01/Temas_de_LV.pdf">Temas de LV</a>',  # no year
                  '<a href="/sites/default/files/2026-01/Sistemas_2027.pdf">Sistemas 2027</a>',
                  '<nav><a href="/sites/default/files/2026-01/Temas_2030.pdf">Temas 2030</a></nav>'):
            self.assertIsNone(E.find_themes_link(html.replace("</main>", a + "</main>"), RESOURCES), a)
        self.assertIsNone(E.find_themes_link("", RESOURCES))

    def test_the_pattern_from_the_settings(self):
        html = fx("lv_recursos.html")
        self.assertIn("Catalogo", E.find_themes_link(html, RESOURCES, "cat[aá]logo")["url"])
        self.assertEqual(E.find_themes_link(html, RESOURCES, "(unbalanced")["url"], DOC)     # bad → the default
        st = E.settings(CFG)
        self.assertEqual((st["lv_themes_page"], st["lv_themes_link"]), (RESOURCES, "\\btemas\\b"))
        self.assertEqual(E.settings({"sources": {"lavina": {"base": LV}}})["lv_themes_page"], RESOURCES)
        self.assertEqual(E.settings({"sources": {"lavina": {"themes_page": "https://example.org/x"}}})["lv_themes_page"],
                         "https://example.org/x")

    def test_the_settings_name_la_vinas_resources_page(self):
        # config/site.yml as the committee keeps it — left to the Code check (scripts/ops/gate_tests.py CONTENT_TESTS)
        self.assertEqual(E.settings(E.load_config())["lv_themes_page"], RESOURCES)


class Items(unittest.TestCase):
    def test_dated_la_vina_topics(self):
        rows, _ = E.parse_lv_themes(pages())
        items = E.rows_to_items(rows, "lv", DOC, {"pdf_url": DOC})
        it = next(i for i in items if i["extra"]["issue_key"] == "2027-05")
        self.assertEqual(it["id"], "ed:lv:2027-05:recaidas")
        self.assertEqual((it["source"], it["kind"], it["category"], it["lang"]), ("lavina", "topic", "lv", "es"))
        self.assertEqual((it["title"], it["date"], it["url"]), ("Recaídas", "2026-10-17", DOC))
        self.assertEqual(it["extra"], {
            "publication": "lv", "issue_label": "Mayo / Junio 2027", "issue_key": "2027-05", "deadline": "2026-10-17",
            "theme": "Recaídas", "evergreen": False, "due_text": "17 de octubre del 2026", "pdf_url": DOC,
            "submit_email": "lveditorial@aagrapevine.org"})
        self.assertEqual(len({i["id"] for i in items}), 12)              # Prisiones twice: 2026-07 and 2027-07
        self.assertEqual(E.part_of(it), "lv-themes")
        self.assertEqual(E.part_of(evergreen("Mi Primer Paso")), "lv")

    def test_the_window(self):
        rows, _ = E.parse_lv_themes(pages())
        items = E.rows_to_items(rows, "lv", DOC, {"pdf_url": DOC})
        # early October 2026: September–October 2026 is on sale, November–December next — kept with what follows
        keys = sorted({i["extra"]["issue_key"] for i in E.keep_window(items, TODAY)})
        self.assertEqual(keys, ["2026-09", "2026-11", "2027-01", "2027-03", "2027-05", "2027-07", "2027-09", "2027-11"])


def fetchers(html: dict | None = None, doc=None):
    """fetch_html by URL ({url: text or None}; /recursos from the fixture) and fetch_pages (the fixture's text, a
    list of pages to return instead, or an exception to raise). Both record their calls."""
    calls: list[str] = []
    pages_html = {RESOURCES: fx("lv_recursos.html"), **(html or {})}

    def fetch_html(url):
        calls.append(url)
        return pages_html.get(url)

    def fetch_pages(url):
        calls.append(url)
        if isinstance(doc, Exception):
            raise doc
        return doc if doc is not None else pages()
    return fetch_html, fetch_pages, calls


PREV = [prev_topic("2026-09", "El amor al servicio", "2026-02-02"), prev_topic("2027-01", "Nuevos", "2026-07-30"),
        evergreen("Mi Primer Paso"), evergreen("Mi meditación"),
        prev_topic("2027-05", "Fun in Sobriety", "2026-10-01", pub="gv")]


class Collect(unittest.TestCase):
    def test_the_themes_document(self):
        fh, fp, calls = fetchers()
        res = E.collect(fh, fp, PREV, TODAY, CFG, only="lv-themes")
        self.assertEqual(res["errors"], [])
        self.assertEqual(calls, [RESOURCES, DOC])
        self.assertEqual(res["refreshed"], {"lv-themes"})
        self.assertEqual(len(res["fresh"]), 8)
        self.assertTrue(all(E.part_of(i) == "lv-themes" for i in res["fresh"]))
        self.assertEqual(sorted(i["id"] for i in res["kept"]),                     # the other parts, untouched
                         sorted(i["id"] for i in PREV if E.part_of(i) != "lv-themes"))
        st = res["stats"]["lv_themes"]
        self.assertEqual((st["parsed"], st["kept"], st["years"], st["document"]), (12, 8, [2026, 2027], DOC))
        self.assertEqual(st["open"], 4)            # Oct 17, 2026 and later (July 30 and Sept 3, 2026 are past)

    def test_problems_keep_the_previous_dated_topics(self):
        no_link = fx("lv_recursos.html").replace("Temas_de_LV_2027_2026.pdf", "Otro.pdf").replace(
            "Temas de LV 2026 y 2027", "Otro documento")
        broken = pages()
        broken[0] = remove_line(broken[0], "Mayo/Junio")
        cases = {
            "no page": ({RESOURCES: None}, None, "could not fetch https://www.aalavina.org/recursos"),
            "no link": ({RESOURCES: no_link}, None, "no yearly themes document linked from"),
            "unreadable": (None, E.ThemesError("could not download x (too-large)"), "could not download"),
            "changed layout": (None, broken, "5 issues but 6 themes"),
            "anything else": (None, ValueError("boom"), "parse error ValueError: boom"),
        }
        for name, (html, doc, words) in cases.items():
            with self.subTest(name):
                fh, fp, _ = fetchers(html, doc)
                res = E.collect(fh, fp, PREV, TODAY, CFG, only="lv-themes")
                self.assertEqual(len(res["errors"]), 1)
                self.assertTrue(res["errors"][0].startswith("lv-themes: "), res["errors"])
                self.assertIn(words, res["errors"][0])
                self.assertEqual(res["fresh"], [])
                self.assertEqual(res["refreshed"], set())
                self.assertEqual(sorted(i["id"] for i in res["kept"]), sorted(i["id"] for i in PREV))

    def test_one_part_failing_never_stops_the_others(self):
        fh, fp, _ = fetchers()        # Grapevine's and La Viña's own pages answer nothing here
        res = E.collect(fh, fp, PREV, TODAY, CFG)
        self.assertEqual([e.split(":")[0] for e in res["errors"]], ["gv", "lv"])
        self.assertEqual(res["refreshed"], {"lv-themes"})
        self.assertEqual(len(res["fresh"]), 8)
        self.assertEqual(sorted(i["id"] for i in res["kept"]), sorted(i["id"] for i in PREV if E.part_of(i) != "lv-themes"))

    def test_a_year_the_new_document_no_longer_lists(self):
        # a document of 2028 alone: the 2027 themes read last year stay until they leave the window
        p2028 = pages()[0].replace("del 2026", "del 2027").replace("2 de febrero del 2027", "2 de febrero del 2028") \
            .replace("3 de abril del 2027", "3 de abril del 2028").replace("para 2027", "para 2028")
        fh, fp, _ = fetchers(doc=[p2028])
        prev = [prev_topic("2027-05", "Recaídas", "2026-10-17"), prev_topic("2026-01", "Nuevos", "2025-07-30"),
                prev_topic("2026-09", "El amor al servicio", "2026-02-02"),
                prev_topic("2026-11", "La alegría de vivir", "2026-04-03")]
        res = E.collect(fh, fp, prev, TODAY, CFG, only="lv-themes")
        self.assertEqual(res["errors"], [])
        self.assertEqual({i["extra"]["issue_key"][:4] for i in res["fresh"]}, {"2028"})
        self.assertEqual(len(res["fresh"]), 6)
        # the issue on sale, the next one and 2027's stay; January 2026 has left the window
        self.assertEqual(sorted(i["id"] for i in res["kept"]), ["ed:lv:2026-09:el-amor-al-servicio",
                                                                 "ed:lv:2026-11:la-alegria-de-vivir",
                                                                 "ed:lv:2027-05:recaidas"])

    def test_a_much_shorter_list_is_held_back(self):
        prev = [prev_topic(f"2027-{m:02d}", f"Tema {m}", f"2026-{m:02d}-01") for m in range(1, 12, 2)] + \
               [prev_topic("2028-01", "Tema 13", "2027-07-01"), prev_topic("2028-03", "Tema 14", "2027-09-01")]
        one = pages()[0].split("Marzo/Abril")[0] + "Nuevos\nFecha límite para enviar tu\nhistorial: 30 de julio del 2026\n" \
            "Temas de la revista para 2027\n"
        fh, fp, _ = fetchers(doc=[one])
        res = E.collect(fh, fp, prev, TODAY, CFG, only="lv-themes")
        self.assertIn("only 3 themes found (had 8)", res["errors"][0])
        self.assertEqual(len(res["kept"]), 8)
        self.assertEqual(len(E.collect(fh, fp, prev, TODAY, CFG, only="lv-themes", force=True)["fresh"]), 1)


class Run(unittest.TestCase):
    """main(): the envelope it writes (data/raw is never touched here: load_raw / save_raw are replaced)."""

    def run_main(self, argv: list[str], prev: list[dict]) -> dict:
        saved: dict = {}

        def save(source, items, ok=True, error=None, stats=None, extra=None):
            saved.update(source=source, items=items, ok=ok, error=error, stats=stats)
        with mock.patch.object(E, "load_raw", return_value={"items": prev}), \
                mock.patch.object(E, "save_raw", side_effect=save), \
                mock.patch.object(E, "_today_central", return_value=TODAY):
            E.main(argv)
        return saved

    def test_written_and_kept(self):
        args = ["--only", "lv-themes", "--lv-resources-html", str(FIX / "lv_recursos.html"),
                "--lv-themes-doc", str(FIX / "lv_temas_2027_2026.txt")]
        env = self.run_main(args, PREV)
        self.assertTrue(env["ok"])
        self.assertIsNone(env["error"])
        ids = [i["id"] for i in env["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        dated = [i for i in env["items"] if E.part_of(i) == "lv-themes"]
        self.assertEqual(len(dated), 8)
        nuevos = next(i for i in dated if i["id"] == "ed:lv:2027-01:nuevos")
        self.assertEqual(nuevos["first_seen"], "2026-01-10T07:00:00Z")     # an earlier run's topic keeps its first day
        self.assertIn("ed:lv:2026-09:el-amor-al-servicio", ids)
        self.assertEqual(sum(1 for i in env["items"] if E.part_of(i) != "lv-themes"), 3)
        self.assertEqual(env["stats"]["lv_themes"]["years"], [2026, 2027])

    def test_a_field_the_page_no_longer_gives_disappears(self):
        """P2-10: a part read successfully replaces its topics field by field (authoritative merge): Grapevine took
        the deadline and the description off a theme — they leave the site too; the topic keeps its first day."""
        old = {"id": "ed:gv:2027-01:spiritual-awakenings", "source": "grapevine", "kind": "topic",
               "url": "https://www.aagrapevine.org/contribute", "title": "Spiritual Awakenings",
               "summary": "Share your personal journey with Step Two.", "lang": "en", "date": "2026-06-01",
               "first_seen": "2026-01-10T07:00:00Z", "last_seen": "2026-09-30T07:00:00Z", "image": None, "tags": [],
               "category": "gv", "status": "ok",
               "extra": {"publication": "gv", "issue_key": "2027-01", "issue_label": "January 2027",
                         "deadline": "2026-06-01", "due_text": "June 1, 2026", "theme": "Spiritual Awakenings",
                         "evergreen": False}}
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "contribute.html"
            html.write_text("<html><body><main><h2>Grapevine Editorial Calendar 2027</h2><p>JANUARY</p>"
                            "<p>Spiritual Awakenings</p></main></body></html>", encoding="utf-8")
            env = self.run_main(["--only", "gv", "--gv-html", str(html)], [old])
        self.assertTrue(env["ok"])
        it = next(i for i in env["items"] if i["id"] == old["id"])
        self.assertEqual((it["date"], it["summary"]), (None, ""))
        self.assertNotIn("deadline", it["extra"])
        self.assertNotIn("due_text", it["extra"])
        self.assertEqual(it["first_seen"], "2026-01-10T07:00:00Z")

    def test_a_problem_is_reported_and_the_old_themes_stay(self):
        bad = FIX / "lv_recursos.html"
        env = self.run_main(["--only", "lv-themes", "--lv-resources-html", str(bad),
                             "--lv-themes-doc", str(FIX / "lv_recursos.html")], PREV)   # not a themes document
        self.assertFalse(env["ok"])
        self.assertIn("lv-themes: no issues with a theme and a deadline", env["error"])
        self.assertEqual(sorted(i["id"] for i in env["items"]), sorted(i["id"] for i in PREV))


class EnglishWords(unittest.TestCase):
    """Every theme of La Viña's current themes document has hand-written English words in
    data/translations/overrides.yml, so no page or slide glosses a theme with a machine translation (the decks print the
    gloss beside the theme: "Recaídas (Relapses)"). A new year's document needs its new themes there too."""

    def test_every_theme_has_its_english_words(self):
        from scripts.sync import translate as T
        ov = T.Overrides.load()
        self.assertIsNone(ov.error)
        themes = sorted({r["theme"] for r in E.parse_lv_themes(pages())[0]})
        self.assertEqual(len(themes), 10)                                    # 12, "Nuevos" and "Prisiones" both years
        self.assertEqual([t for t in themes if not ov.get(t, "en")], [], "themes left to the machine translation")
        # "Veterans", not "Old-Timers": "veteranos" can mean either, and the theme's September–October 2027 issue
        # lines up with Grapevine's October 2027 "AA in the Military" (overrides.yml says why)
        self.assertEqual(ov.get("Hispanos Veteranos en AA", "en"), "Hispanic Veterans in AA")


if __name__ == "__main__":
    unittest.main()
