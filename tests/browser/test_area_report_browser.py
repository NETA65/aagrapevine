"""Round 12 · the chair's report to the Area on /monthly/#report, in a real browser (tests/browser/__init__.py says how
to run these; the site server, the browser and the helpers are test_site_in_browser.py's):

  * AreaReportInBrowser — "For: Area" in the page's editor, English and Spanish: the dates show, the preview holds the
                          English part, the line, then the Spanish part; the Word file downloads under its dated name
                          for the committee's Drive; back to "District meeting", the district report is as before; no
                          script error. A From typed after the To waits in its field (the reason under the dates) for
                          the To that makes them a period; a day out of reach says which days the page covers. On a
                          360-pixel phone at 150 % text, Area mode never scrolls sideways (two date fields, the switch,
                          the notes, the earlier reports unfolded) — there as Safari on an iPhone, whose line on
                          Safari's 7-day rule shows under the earlier reports and in the note, in the page's language.
  * AreaDraftsInBrowser — the one working report and its earlier reports on a fixed clock (dates taken from the
                          build's own #rp-area), English and Spanish pages: both parts written, the page opened again
                          the next day (To follows today, the words still there), the meeting's day picked as To (no
                          longer following; the words stay), "Next report" (asked first) → a fresh report from the
                          site's text, the offer "Start from your … report?" and the report under "Earlier reports";
                          an earlier report's Word file and print (what was filed, under its dated name; the preview
                          back to the working report after) and Delete; "Start this part over" (asked first, said
                          after) clears only that part — the other part and the dates stay. In Chrome no line on
                          Safari's 7-day rule; the browser is asked to keep the site's data (navigator.storage.persist)
                          once a page, after the first save — never on opening the page.

Nothing here depends on the day the test runs: only the shape of what the page shows (AreaDraftsInBrowser: a fixed
clock, relative to the day the site was built).
"""
from __future__ import annotations

import io
import json
import re
import unittest
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from browser.test_site_in_browser import S, SIDEWAYS, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401

AREA = "(() => { try { localStorage.setItem('gv-report:mode', JSON.stringify('area')); } catch (e) {} })();"
MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
                 "December"],
          "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
                 "diciembre"]}
SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

STRINGS = json.loads((Path(__file__).resolve().parents[2] / "src" / "_i18n" / "report.json").read_text(encoding="utf-8"))
WORDS = "Sep 26 workshop: about 25 attended, 9 stories written"
# Safari on an iPhone, as the page's scripts read it (navigator.userAgent, maxTouchPoints): the line on Safari's 7-day
# rule (report.js sevenKind). Chromium draws the page; only what the scripts read changes.
IPHONE = ("(() => { const ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)"
          " Version/18.6 Mobile/15E148 Safari/604.1';"
          " Object.defineProperty(Navigator.prototype, 'userAgent', { get: () => ua });"
          " Object.defineProperty(Navigator.prototype, 'maxTouchPoints', { get: () => 5 }); })();")
# navigator.storage.persist() counted (window.__persist), then asked of the browser as before
PERSIST = ("(() => { const s = navigator.storage; if (!s || !s.persist) return; const p = s.persist.bind(s); window.__persist = 0;"
           " s.persist = () => { window.__persist++; return p(); }; })();")
WORK = "gv-report:area:work"
DONE = "gv-report:area:done"


def day(ymd: str, n: int) -> str:
    return (date.fromisoformat(ymd) + timedelta(days=n)).isoformat()


def central_noon(ymd: str) -> datetime:
    """Noon in Central time on that day (18:00 UTC: noon in CST, 1 PM in CDT — the same day)."""
    d = date.fromisoformat(ymd)
    return datetime(d.year, d.month, d.day, 18, 0, tzinfo=timezone.utc)


def pieces(lang: str) -> dict:
    """The built page's Area pieces (#rp-area): its today, min, max and events."""
    html = (S["site"] / ("es" if lang == "es" else ".") / "monthly" / "index.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/json" id="rp-area"[^>]*>(.*?)</script>', html, re.S).group(1))


def seeded(store: dict) -> str:
    """An init script that stores these (Area mode, the working report, the earlier ones) once per tab — not again on a
    reload."""
    items = {"gv-report:mode": "area", **store}
    return ("(() => { try { if (sessionStorage.getItem('gv-seeded')) return; sessionStorage.setItem('gv-seeded', '1');"
            + "".join(f"localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))});" for k, v in items.items())
            + "} catch (e) {} })();")


def stored(page, key: str):
    return page.evaluate("k => JSON.parse(localStorage.getItem(k))", key)


def t(key: str, lang: str, **v) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(v.get(m.group(1), m.group(0))), STRINGS[key][lang])


def long_day(ymd: str, lang: str) -> str:
    """"November 21, 2026" / "21 de noviembre de 2026" (report.js longDay)."""
    d = date.fromisoformat(ymd)
    m = MONTHS[lang][d.month - 1]
    return f"{d.day} de {m} de {d.year}" if lang == "es" else f"{m} {d.day}, {d.year}"


def range_label(a: str, b: str, lang: str) -> str:
    """"Aug 12 – Nov 14, 2026" / "12 de agosto – 14 de noviembre de 2026" (report.js rangeLabel)."""
    x, y = date.fromisoformat(a), date.fromisoformat(b)
    if lang == "es":
        f = lambda d, yr: f"{d.day} de {MONTHS['es'][d.month - 1]}" + (f" de {d.year}" if yr else "")
    else:
        f = lambda d, yr: f"{SHORT[d.month - 1]} {d.day}" + (f", {d.year}" if yr else "")
    return f(x, x.year != y.year) + " – " + f(y, True)


class AreaReportInBrowser(unittest.TestCase):
    def test_for_area_in_both_languages(self):
        errors: list[str] = []
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            ctx.set_default_timeout(15_000)
            try:
                page = open_page(ctx, ("es/" if lang == "es" else "") + "monthly/", errors)
                page.locator("#report").scroll_into_view_if_needed()
                page.wait_for_selector("#rp-district", state="visible")
                page.click("label.cm-seg:has(input[name='rp-for'][value='area'])")
                page.wait_for_selector("#rp-from", state="visible")
                self.assertFalse(page.is_visible("#rp-district"), "the district number is the district report's")
                frm, to = page.input_value("#rp-from"), page.input_value("#rp-to")
                self.assertRegex(frm, r"^\d{4}-\d{2}-\d{2}$")
                self.assertRegex(to, r"^\d{4}-\d{2}-\d{2}$")
                self.assertLessEqual(frm, to)
                page.fill("#rp-name", "Maria G.")
                page.select_option("#rp-ameet", "assembly")
                doc = page.locator(".rp-doc")
                text = doc.inner_text()
                en_at, es_at = text.find("Recent activities"), text.find("Actividades recientes")
                self.assertTrue(0 <= en_at < es_at, "the English part, then the Spanish one")
                self.assertEqual(page.locator(".rp-doc hr.rp-doc-split").count(), 1)
                self.assertIn("report to the Area 65 Assembly", text)
                self.assertIn("Prepared by: Maria G.", text)
                # each part says its language; the part being edited is the page language's (its sections the ones
                # highlighted while edited), the other one's sections have their own ids
                other = "es" if lang == "en" else "en"
                self.assertEqual(page.locator(f".rp-doc [data-sec='recent'][lang='{lang}']").count(), 1)
                self.assertEqual(page.locator(f".rp-doc [data-sec='{other}:recent'][lang='{other}']").count(), 1)
                # the Area's Start over says "this part"; nothing filed yet: no earlier reports
                self.assertEqual(page.locator("[data-rp-reset]").inner_text().strip(), STRINGS["report.ar_reset_part"][lang])
                self.assertFalse(page.is_visible(".rp-done"))
                with page.expect_download() as dl:
                    page.click("button:has-text('Word (.docx)')")
                self.assertEqual(dl.value.suggested_filename, f"{to} Grapevine La Vina Area Assembly Report.docx")
                # back to the district meeting: its report, its fields
                page.click("label.cm-seg:has(input[name='rp-for'][value='district'])")
                page.wait_for_selector("#rp-district", state="visible")
                self.assertFalse(page.is_visible("#rp-from"))
                self.assertEqual(page.locator(".rp-doc hr.rp-doc-split").count(), 0)
                self.assertEqual(page.locator("[data-rp-reset]").inner_text().strip(), STRINGS["report.reset_all"][lang])
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_a_from_typed_first_waits_for_its_to(self):
        """A From after the To stays in its field, with the reason under the dates, until a To makes them a period; a
        day the page does not cover says which days it does. Dates picked from the page's own dates, not today's."""
        errors: list[str] = []
        words = {"en": ("Pick a start date on or before the end date.", "Pick dates between {a} and {b}.", "Period: {a} – {b}"),
                 "es": ("Elige una fecha de inicio igual o anterior a la fecha final.", "Elige fechas entre el {a} y el {b}.",
                        "Periodo: del {a} al {b}")}
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            ctx.add_init_script(AREA)
            ctx.set_default_timeout(15_000)
            try:
                page = open_page(ctx, ("es/" if lang == "es" else "") + "monthly/", errors)
                page.wait_for_selector("#rp-from", state="visible")
                A = json.loads(page.text_content("#rp-area"))
                to = date.fromisoformat(page.input_value("#rp-to"))
                frm2, to2 = (to + timedelta(days=1)).isoformat(), (to + timedelta(days=30)).isoformat()
                order, reach, period = words[lang]
                page.fill("#rp-from", frm2)
                err = page.locator("#rp-range-err")
                err.wait_for(state="visible")
                self.assertEqual(err.inner_text().strip(), order)
                self.assertEqual(page.input_value("#rp-from"), frm2, "the From typed stays")
                self.assertIn("rp-range-err", page.get_attribute("#rp-from", "aria-describedby"))
                page.fill("#rp-to", to2)
                err.wait_for(state="hidden")
                self.assertEqual([page.input_value("#rp-from"), page.input_value("#rp-to")], [frm2, to2])
                self.assertIn(period.format(a=long_day(frm2, lang), b=long_day(to2, lang)), page.locator(".rp-doc").inner_text())
                late = (date.fromisoformat(A["max"]) + timedelta(days=1)).isoformat()
                page.fill("#rp-to", late)
                err.wait_for(state="visible")
                self.assertEqual(err.inner_text().strip(), reach.format(a=long_day(A["min"], lang), b=long_day(A["max"], lang)))
                self.assertEqual(page.input_value("#rp-to"), late)
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_no_sideways_scroll_on_a_phone_at_150_percent(self):
        problems = []
        for lang in ("en", "es"):
            t0 = pieces(lang)["today"]
            ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
            ctx.add_init_script(seeded({DONE: [AreaDraftsInBrowser.filed(t0, n) for n in (1, 2)]}))
            ctx.add_init_script(IPHONE)
            try:
                page = open_page(ctx, ("es/" if lang == "es" else "") + "monthly/")
                page.wait_for_selector("#rp-from", state="visible", timeout=15_000)
                page.click(".rp-done-sum")
                page.wait_for_selector("[data-rp-done-delete]", state="visible", timeout=15_000)
                # Safari's 7-day rule: its line under the earlier reports and in the note (Safari on an iPhone: "tapping")
                for where in (".rp-done .rp-hint", "p.rp-note"):
                    for k in ("safari", "browser", "mac"):
                        line = page.locator(f"{where} span", has_text=STRINGS[f"report.ar_keep_{k}"][lang])
                        if line.count() != 1 or line.is_visible() != (k == "safari"):
                            problems.append(f"{lang}: {where}: the '{k}' line {'hidden' if k == 'safari' else 'shown'}")
                page.locator("#rp-from").scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                r = page.evaluate(SIDEWAYS)
                if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                    problems.append(f"/{'es/' if lang == 'es' else ''}monthly/ (Area): scrolls {r['moved']} px sideways "
                                    f"(page {r['scrollWidth']} px wide in {r['width']}): {r['wide']}")
                # every field of the Area details, and the earlier reports' buttons, fit the phone
                for sel in ("#rp-from", "#rp-to", "#rp-ameet", "#rp-name", "[data-rp-done-word] >> nth=0", "[data-rp-done-delete] >> nth=1"):
                    box = page.locator(sel).bounding_box()
                    if not box or box["x"] < 0 or box["x"] + box["width"] > 360:
                        problems.append(f"{lang}: {sel} at {box}")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(problems, [])


class AreaDraftsInBrowser(unittest.TestCase):
    @staticmethod
    def filed(t0: str, n: int = 1) -> dict:
        """An earlier report as the page files it: the n-th one back (91 days each, the newest ending the day before
        t0), its words in both parts, the name and meeting it was given with."""
        to = day(t0, -1 - 91 * (n - 1))
        return {"from": day(to, -90), "to": to,
                "parts": {"en": {"text": {"recent": f"Filed words {n}", "invite": "Ask us for a workshop!"}},
                          "es": {"text": {"notes": f"Notas archivadas {n}"}}},
                "site": {"en": {}, "es": {}}, "prof": {"name": "Ana P.", "ameet": "assembly"}}

    def open_at(self, ctx, lang: str, today: str, errors: list, dialogs: list | None = None):
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))
        page.on("dialog", lambda d: (dialogs.append(d.message) if dialogs is not None else None, d.accept()))
        page.clock.set_fixed_time(central_noon(today))
        page.goto(url(("es/" if lang == "es" else "") + "monthly/"), wait_until="load", timeout=60_000)
        page.wait_for_selector("#rp-from", state="visible", timeout=15_000)
        return page

    def dates(self, page) -> list:
        return [page.input_value("#rp-from"), page.input_value("#rp-to")]

    def part(self, page, lang: str):
        """The report's EN / ES switch: the part being edited."""
        page.click(f"label.cm-seg:has(input[name='rp-lang'][value='{lang}'])")
        page.wait_for_function("L => document.querySelector(\"input[name='rp-lang'][value='\" + L + \"']\").checked", arg=lang)

    def write(self, page, sec: str, text: str):
        page.click(f"[data-rp-edit='{sec}']")
        page.fill(f"#rp-text-{sec}", text)
        page.wait_for_timeout(600)                               # (the save delay)

    def pick(self, page, field: str, ymd: str):
        page.fill(f"#rp-{field}", ymd)
        page.wait_for_function("([f, t]) => document.getElementById('rp-' + f).value === t", arg=[field, ymd])
        page.wait_for_timeout(300)

    def hint(self, page, lang: str):
        return page.locator(".rp-f-range p.rp-hint", has_text=STRINGS["report.ar_open_hint"][lang])

    def test_write_follow_pick_and_next_report(self):
        """Both parts written; the next day To has followed today with the words; the meeting's day picked as To (fixed,
        the words stay); "Next report", asked first: a fresh report from the site's text, the offer, and the report
        under "Earlier reports"; "Start from" brings back only the carry-over."""
        errors: list[str] = []
        for lang in ("en", "es"):
            t0 = pieces(lang)["today"]
            dialogs: list[str] = []
            ctx = new_context(1280, 900, lang=lang)
            ctx.add_init_script(seeded({}))
            ctx.add_init_script(PERSIST)
            ctx.set_default_timeout(15_000)
            try:
                page = self.open_at(ctx, lang, t0, errors, dialogs)
                f0 = self.dates(page)[0]
                self.assertEqual(self.dates(page)[1], t0)
                self.assertTrue(self.hint(page, lang).is_visible(), f"{lang}: To follows today")
                # Chrome: no line on Safari's 7-day rule; nothing asked of the browser before something is saved
                self.assertEqual(page.locator("p.rp-note:visible").count(), 1, "the Area's note")
                self.assertEqual(page.locator("p.rp-note span:visible").count(), 0, f"{lang}: no Safari line in Chrome")
                self.assertEqual(page.evaluate("() => window.__persist"), 0, "opening the page asks nothing")
                self.part(page, "en")
                self.write(page, "recent", WORDS)
                self.assertEqual(page.evaluate("() => window.__persist"), 1, "asked once something is saved")
                self.write(page, "invite", "Ask us for a workshop!")
                self.part(page, "es")
                self.write(page, "notes", "Notas ES")
                self.assertEqual(page.evaluate("() => window.__persist"), 1, "once a page")
                # the next day: To is today, the words are there
                page.clock.set_fixed_time(central_noon(day(t0, 1)))
                page.reload(wait_until="load")
                page.wait_for_selector("#rp-from", state="visible")
                doc = page.locator(".rp-doc")
                self.assertEqual(self.dates(page), [f0, day(t0, 1)], lang)
                self.assertTrue(self.hint(page, lang).is_visible())
                for words in (WORDS, "Notas ES"):
                    self.assertIn(words, doc.inner_text())
                nxt = page.locator("[data-rp-next]")
                self.assertFalse(nxt.is_visible(), f"{lang}: no Next report while To follows today")
                # the meeting's day (yesterday) picked as To: fixed, the words stay, Next report offered
                self.pick(page, "to", t0)
                self.assertFalse(self.hint(page, lang).is_visible())
                self.assertEqual(stored(page, WORK)["toFollowsToday"], False)
                for words in (WORDS, "Notas ES"):
                    self.assertIn(words, doc.inner_text(), f"{lang}: new dates keep the words")
                self.assertTrue(nxt.is_visible())
                self.assertEqual(nxt.inner_text().strip(), t("report.ar_new_period", lang, date=long_day(day(t0, 1), lang)))
                nxt.click()
                page.wait_for_function("t => document.getElementById('rp-from').value === t", arg=day(t0, 1))
                self.assertEqual(dialogs[-1], t("report.ar_next_confirm", lang, dates=range_label(f0, t0, lang), date=long_day(day(t0, 1), lang)))
                # a fresh report: the site's text, To following today, the offer; the old one filed
                self.assertEqual(self.dates(page), [day(t0, 1), day(t0, 1)])
                self.assertTrue(self.hint(page, lang).is_visible())
                text = doc.inner_text()
                for words in (WORDS, "Ask us", "Notas ES"):
                    self.assertNotIn(words, text, f"{lang}: the next report starts from the site's text")
                self.assertTrue("[N]" in text or STRINGS["report.ar_recent_none"]["en"] in text, "Recent activities: the site's text")
                offer = page.locator("[data-rp-prev]")
                offer.wait_for(state="visible")
                self.assertEqual(page.locator("#rp-prev-title").inner_text().strip(), t("report.ar_prev_title", lang, month=range_label(f0, t0, lang)))
                done = stored(page, DONE)
                self.assertEqual([(x["from"], x["to"]) for x in done], [(f0, t0)])
                self.assertEqual([done[0]["parts"]["en"]["text"], done[0]["parts"]["es"]["text"]],
                                 [{"recent": WORDS, "invite": "Ask us for a workshop!"}, {"notes": "Notas ES"}])
                self.assertEqual(page.locator(".rp-done-sum").inner_text().strip(), t("report.ar_done_title", lang, n=1))
                # "Start from": the invitation and the notes come back, never the counts
                offer.click()
                offer.wait_for(state="hidden")
                text = doc.inner_text()
                self.assertIn("Ask us for a workshop!", text)
                self.assertIn("Notas ES", text)
                self.assertNotIn(WORDS, text)
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_earlier_reports_word_print_and_delete(self):
        """An earlier report, read-only: its Word file under its own dated name with what was filed; print shows it
        (the dated name as the title) and the preview is the working report again after; Delete asks first."""
        errors: list[str] = []
        for lang in ("en", "es"):
            t0 = pieces(lang)["today"]
            old = self.filed(t0)
            working = {"from": day(t0, 0), "to": day(t0, 0), "toFollowsToday": True, "parts": {"en": {"text": {"notes": "Working words"}}}}
            dialogs: list[str] = []
            ctx = new_context(1280, 900, lang=lang)
            ctx.add_init_script(seeded({DONE: [old], WORK: working}))
            # (print: what the page would print, then the print dialog closed)
            ctx.add_init_script("window.print = () => { window.__printed = { title: document.title, text: document.querySelector('.rp-doc').innerText };"
                                " window.dispatchEvent(new Event('afterprint')); };")
            ctx.set_default_timeout(15_000)
            try:
                page = self.open_at(ctx, lang, t0, errors, dialogs)
                self.assertFalse(page.is_visible("[data-rp-done]"), "folded at first")
                page.click(".rp-done-sum")
                item = page.locator("[data-rp-done]")
                item.wait_for(state="visible")
                self.assertEqual(page.locator(".rp-done-dates").inner_text().strip(), range_label(old["from"], old["to"], lang))
                name = f"{old['to']} Grapevine La Vina Area Assembly Report"
                with page.expect_download() as dl:
                    page.click("[data-rp-done-word]")
                self.assertEqual(dl.value.suggested_filename, name + ".docx")
                xml = zipfile.ZipFile(io.BytesIO(Path(dl.value.path()).read_bytes())).read("word/document.xml").decode("utf-8")
                for words in ("Filed words 1", "Notas archivadas 1", "Prepared by: Ana P.", "report to the Area 65 Assembly"):
                    self.assertIn(words, xml, lang)
                self.assertNotIn("Working words", xml)
                page.click("[data-rp-done-print]")
                page.wait_for_function("() => !!window.__printed")
                printed = page.evaluate("() => window.__printed")
                self.assertEqual(printed["title"], name)
                self.assertIn("Filed words 1", printed["text"])
                self.assertNotIn("Working words", printed["text"])
                page.wait_for_function("() => document.querySelector('.rp-doc').innerText.includes('Working words')")
                self.assertNotIn("Filed words 1", page.locator(".rp-doc").inner_text(), "the preview is the working report again")
                page.focus("[data-rp-done-delete]")
                page.keyboard.press("Enter")
                page.wait_for_selector(".rp-done", state="hidden")
                # the last one gone (and the list with it): the keyboard goes on from the first date, never <body>
                page.wait_for_function("() => document.activeElement && document.activeElement.id === 'rp-from'", timeout=5_000)
                self.assertEqual(dialogs[-1], t("report.ar_done_del_confirm", lang, dates=range_label(old["from"], old["to"], lang)))
                self.assertEqual(stored(page, DONE), [])
                self.assertEqual(stored(page, WORK), working, "the working report untouched")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_start_over_one_part(self):
        """"Start this part over" on the Spanish part (asked first, naming both parts): that part is the site's text
        again, the English part and the dates stay; the page says so."""
        errors: list[str] = []
        names = {"en": ("Spanish", "English"), "es": ("español", "inglés")}
        for lang in ("en", "es"):
            t0 = pieces(lang)["today"]
            frm, to = day(t0, -40), day(t0, -2)
            working = {"from": frm, "to": to, "toFollowsToday": False,
                       "parts": {"en": {"text": {"recent": WORDS}}, "es": {"text": {"notes": "Notas ES"}}}}
            dialogs: list[str] = []
            ctx = new_context(1280, 900, lang=lang)
            ctx.add_init_script(seeded({WORK: working}))
            ctx.set_default_timeout(15_000)
            try:
                page = self.open_at(ctx, lang, t0, errors, dialogs)
                self.part(page, "es")
                page.click("[data-rp-reset]")
                msg = page.locator(".rp-msg")
                msg.wait_for(state="visible")
                part, other = names[lang]
                self.assertEqual(dialogs[-1], t("report.ar_reset_confirm", lang, part=part, other=other))
                self.assertEqual(msg.inner_text().strip(), t("report.ar_reset_done", lang, part=part, other=other))
                text = page.locator(".rp-doc").inner_text()
                self.assertIn(WORDS, text, f"{lang}: the English part stays")
                self.assertNotIn("Notas ES", text)
                self.assertEqual(self.dates(page), [frm, to], "the dates stay")
                w = stored(page, WORK)
                self.assertEqual([w["from"], w["to"], w["toFollowsToday"], w["parts"]["en"]["text"], w["parts"]["es"]["text"]],
                                 [frm, to, False, {"recent": WORDS}, {}])
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
