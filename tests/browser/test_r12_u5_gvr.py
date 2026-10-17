"""The GVR / RLV corner's "Pass it on" kit and the booth's question of the day ("Did you know?"), in a real browser
(tests/browser/__init__.py says how to run these; the site server, the browser and the helpers are
test_site_in_browser.py's):

  * QuestionOfTheDay — on About (English) and /es/gvr/ (Spanish): the card shows the question of the visitor's Central
                       day, counted from the day the page was built (the page's own list: two days later, the third
                       day's; past the list's last day, round again), La Viña's first on the Spanish page; an answer
                       shows the explanation and moves the keyboard there; "Another question" moves it back to the new
                       question, up to the day's last; the source link goes only to AA's own sites; no script error;
                       no words meant for the booth's table ("Like this one!", "esta mesa", "Ask us" …) on the four
                       pages that carry the card.
  * PassItOn         — /gvr/: Copy puts the welcome message on the clipboard with its lines (the next meeting's date
                       in it); "Print a half-sheet" / "Print the handover sheet" print only their sheet, laid out on
                       the page with its text and QR code (one Letter page each, not a blank one: the browser's own
                       PDF of the page), and the browser's own Print prints the page without them; the "Tell the
                       office" e-mails are ready-made, to the addresses in config/site.yml, with that office's
                       registration page (links.gvr_register / rlv_register there) and no name in them.
  * GvrPhone         — /gvr/ and /es/gvr/ (and About) on a 360-pixel phone at 150 % text: nothing scrolls sideways, also
                       with the question answered.
"""
from __future__ import annotations

import json
import re
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import yaml

from browser.test_site_in_browser import (S, SIDEWAYS, new_context, open_page, setUpModule,  # noqa: F401
                                          tearDownModule, url)
from test_r12_u5_gvr import TABLE_TALK, card_words

ROOT = Path(__file__).resolve().parents[2]
AA_HOSTS = {"www.aa.org", "aa.org", "www.aagrapevine.org", "aagrapevine.org", "www.aalavina.org", "aalavina.org",
            "neta65.org", "www.neta65.org", "neta65.github.io"}


def daily(path: str) -> dict:
    """The question card's data in a built page (its <script data-dyk>)."""
    html = (S["site"] / path / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" data-dyk(?:="")?>(.*?)</script>', html, re.S)
    if not m:
        raise AssertionError(f"/{path}: no question card")
    return json.loads(m.group(1))


def central_noon(ymd: str, plus_days: int = 0) -> datetime:
    """Noon in Central time that many days after a day (18:00 UTC: noon in CST and 1 PM in CDT — the same day)."""
    d = date.fromisoformat(ymd) + timedelta(days=plus_days)
    return datetime(d.year, d.month, d.day, 18, 0, tzinfo=timezone.utc)


# what goes on paper while the page prints (emulate_media "print"): each element really laid out — its own display
# is not enough, an ancestor's display: none hides it too (and a blank page is still one PDF page)
ON_PAPER = """() => {
  const shown = (el) => !!el && el.getBoundingClientRect().height > 0 && getComputedStyle(el).visibility !== "hidden";
  const one = (s) => shown(document.querySelector(s));
  const each = (s) => [...document.querySelectorAll(s)].map(shown);
  return { announce: one(".read-pass-sheet[data-sheet=announce]"),
           halves: each(".read-pass-sheet[data-sheet=announce] .read-pass-body"),
           halfQr: each(".read-pass-sheet[data-sheet=announce] .read-pass-qr"),
           handover: one(".read-pass-sheet[data-sheet=handover]"),
           fields: one(".read-pass-sheet[data-sheet=handover] .read-pass-fields"),
           handQr: one(".read-pass-sheet[data-sheet=handover] .read-pass-qr"),
           header: one(".site-header"), section: one("#pass-it-on") };
}"""
NOTHING_PRINTED = 10_000      # bytes: a blank Letter page is about 1.3 KB, a sheet with its words and QR code ~90 KB

QUESTION = """() => {
  const q = document.querySelector(".read-dyk .read-dyk-q");
  const badge = q && q.previousElementSibling ? q.previousElementSibling.textContent.trim() : "";
  return q ? { text: q.textContent, badge } : null;
}"""


class QuestionOfTheDay(unittest.TestCase):
    def check(self, lang: str, path: str, plus_days: int, expect_day: int):
        data = daily(("es/" if lang == "es" else "") + path)
        self.assertGreaterEqual(len(data["days"]), 3)
        ctx = new_context(1280, 900, lang=lang)
        errors: list[str] = []
        try:
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))
            page.clock.set_fixed_time(central_noon(data["from"], plus_days))
            page.goto(url(("es/" if lang == "es" else "") + path), wait_until="load", timeout=60_000)
            page.wait_for_selector(".read-dyk .read-dyk-q", state="visible", timeout=10_000)
            ids = data["days"][expect_day]
            shown = page.evaluate(QUESTION)
            self.assertEqual(shown["text"], data["items"][ids[0]]["text"], f"/{lang}/{path}: the day's own question")
            if lang == "es" and data["items"][ids[0]]["pub"] == "lv":
                self.assertEqual(shown["badge"], "La Viña")
            for n, qid in enumerate(ids):
                it = data["items"][qid]
                self.assertEqual(page.evaluate(QUESTION)["text"], it["text"])
                if it["type"] == "fill":
                    page.click(".read-dyk button.btn-secondary:has-text('" + ("Ver la respuesta" if lang == "es" else "Show the answer") + "')")
                else:
                    page.locator(".read-dyk .read-dyk-opt").first.click()
                page.wait_for_selector(".read-dyk .read-dyk-fb", state="visible", timeout=5000)
                # the keyboard goes to the answer (once it is shown: Alpine's next tick)
                page.wait_for_function("document.activeElement === document.querySelector('.read-dyk .read-dyk-fb')", timeout=5000)
                fb = page.inner_text(".read-dyk .read-dyk-fb")
                self.assertIsNone(TABLE_TALK.search(fb), f"/{lang}/{path}: words meant for the booth's table")
                if it["explain"]:
                    self.assertIn(it["explain"][:40], fb)
                if it["type"] != "fill":
                    # the right answer is marked with words too (not by colour alone)
                    self.assertEqual(page.locator(".read-dyk .read-dyk-opt.is-right").count(), 1)
                    self.assertIn("la respuesta correcta" if lang == "es" else "the right answer",
                                  page.inner_text(".read-dyk .read-dyk-opt.is-right") + page.text_content(".read-dyk .read-dyk-opt.is-right"))
                link = page.locator(".read-dyk .read-dyk-fb a.link")
                if it["source"]:
                    self.assertEqual(link.get_attribute("href"), it["source"])
                    self.assertIn(urlsplit(it["source"]).hostname, AA_HOSTS)
                more = page.locator(".read-dyk button:has-text('" + ("Otra pregunta" if lang == "es" else "Another question") + "')")
                if n < len(ids) - 1:
                    more.click()
                    page.wait_for_function("(t) => document.querySelector('.read-dyk .read-dyk-q').textContent !== t",
                                           arg=it["text"], timeout=5000)
                    # the keyboard goes back to the new question
                    page.wait_for_function("document.activeElement === document.querySelector('.read-dyk .read-dyk-q')", timeout=5000)
                else:
                    self.assertFalse(more.is_visible(), "no more than the day's questions")
            page.close()
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_about_in_english_two_days_after_the_build(self):
        self.check("en", "about/", 2, 2)

    def test_gvr_in_spanish_past_the_last_day(self):
        n = len(daily("es/gvr/")["days"])
        self.check("es", "gvr/", n + 1, 1)                         # round again: the second day's

    def test_no_words_meant_for_the_table(self):
        # a row that speaks as the booth's table ("Like this one!", "esta mesa", "Ask us" …) stays at the booth: none
        # is among the questions the four pages carry, and each still has its week of 4 a day
        for path in ("about/", "gvr/", "es/about/", "es/gvr/"):
            with self.subTest(page=path):
                data = daily(path)
                self.assertEqual([len(ids) for ids in data["days"]], [4] * 7)
                for qid, it in data["items"].items():
                    self.assertIsNone(TABLE_TALK.search(card_words(it)), f"/{path}: {qid}")


class PassItOn(unittest.TestCase):
    def test_copy_print_and_the_office_emails(self):
        ctx = new_context(1280, 900)
        errors: list[str] = []
        try:
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=url("").split("/aagrapevine")[0])
            page = open_page(ctx, "gvr/", errors)
            # Copy: the welcome message as shown, line by line
            page.locator("#pass-it-on li:nth-child(2) button:has-text('Copy')").click()
            copied = page.evaluate("navigator.clipboard.readText()")
            lines = copied.split("\n")
            self.assertTrue(lines[0].startswith("Welcome to Grapevine and La Viña service"), copied)
            self.assertTrue(lines[1].startswith("• Serving as a GVR?"), copied)
            self.assertTrue(lines[2].startswith("• Serving as an RLV?"), copied)
            self.assertRegex(lines[3], r"^• Our next committee meeting is \w+day, \w+ \d+, \d{4} at \d+:\d\d [AP]M C[SD]T on Zoom\.")
            self.assertTrue(copied.endswith("We're glad you're here."))
            # the announcement: one paragraph, with this page's address
            page.locator("#pass-it-on li:nth-child(1) button:has-text('Copy')").click()
            self.assertIn("/aagrapevine/gvr/", page.evaluate("navigator.clipboard.readText()"))
            # Print: only that sheet goes on paper — the button sets data-print, then prints (stubbed here)
            page.evaluate("window.print = () => { window.__printed = document.documentElement.getAttribute('data-print'); }")
            page.click("#pass-it-on button:has-text('Print a half-sheet')")
            page.wait_for_function("window.__printed === 'gvr-announce'", timeout=5000)
            page.emulate_media(media="print")
            seen = page.evaluate(ON_PAPER)
            self.assertEqual(seen, {"announce": True, "halves": [True, True], "halfQr": [True, True], "handover": False,
                                    "fields": False, "handQr": False, "header": False, "section": False},
                             "the half-sheet alone on paper: the announcement twice, each with its QR code")
            pdf = page.pdf(prefer_css_page_size=True)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 1, "the half-sheet: one Letter page")
            self.assertGreater(len(pdf), NOTHING_PRINTED, "the half-sheet: not a blank page")
            page.evaluate("window.dispatchEvent(new Event('afterprint'))")
            self.assertIsNone(page.evaluate("document.documentElement.getAttribute('data-print')"))
            page.evaluate("document.documentElement.setAttribute('data-print', 'gvr-handover')")
            seen = page.evaluate(ON_PAPER)
            self.assertEqual(seen, {"announce": False, "halves": [False, False], "halfQr": [False, False], "handover": True,
                                    "fields": True, "handQr": True, "header": False, "section": False},
                             "the handover sheet alone on paper, with its fields and QR code")
            pdf = page.pdf(prefer_css_page_size=True)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 1, "the handover sheet: one Letter page")
            self.assertGreater(len(pdf), NOTHING_PRINTED, "the handover sheet: not a blank page")
            page.evaluate("document.documentElement.removeAttribute('data-print')")
            # the browser's own Print: the page, without the two sheets
            seen = page.evaluate(ON_PAPER)
            self.assertEqual((seen["announce"], seen["handover"], seen["header"], seen["section"]), (False, False, True, True))
            page.emulate_media(media="screen")
            # Tell the office: ready-made e-mails to the offices the committee names (config/site.yml), no names
            cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
            hrefs = page.eval_on_selector_all("#pass-it-on a[href^='mailto:']", "els => els.map((a) => a.href)")
            self.assertEqual([unquote(h.split("?")[0]) for h in hrefs],
                             ["mailto:" + cfg["links"]["gvr_office_email"], "mailto:" + cfg["links"]["rlv_office_email"]])
            for h, k in zip(hrefs, ("gvr", "rlv")):
                q = parse_qs(urlsplit(h).query)
                body = q["body"][0]
                self.assertIn("Group name:", body)
                self.assertIn("Area: " + cfg["site"]["area"], body)
                # where the next rep registers: that office's own page, as the committee keeps it (links.*_register)
                self.assertIn(cfg["links"][k + "_register"], body)
            page.close()
        finally:
            ctx.close()
        self.assertEqual(errors, [])


class GvrPhone(unittest.TestCase):
    def test_no_sideways_scroll_at_150_percent(self):
        problems = []
        for lang in ("en", "es"):
            ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
            try:
                for path in ("gvr/", "about/"):
                    where = ("es/" if lang == "es" else "") + path
                    page = open_page(ctx, where)
                    page.wait_for_selector(".read-dyk .read-dyk-q", state="visible", timeout=10_000)
                    first = page.locator(".read-dyk .read-dyk-opt").first
                    if first.is_visible():
                        first.click()
                    else:
                        page.locator(".read-dyk .read-dyk-q ~ p button").first.click()
                    page.wait_for_timeout(300)
                    r = page.evaluate(SIDEWAYS)
                    if r["moved"] > 0 or r["scrollWidth"] > r["width"]:
                        problems.append(f"/{where}: scrolls {r['moved']} px sideways (page {r['scrollWidth']} px wide "
                                        f"in {r['width']}): {r['wide']}")
                    page.close()
            finally:
                ctx.close()
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
