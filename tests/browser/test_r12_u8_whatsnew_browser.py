"""What's New's "New since your last visit" in a real browser (round 12) — the same built site, server and browser as
test_site_in_browser.py (its module set-up; tests/browser/__init__.py says how to run them):

  * WhatsNewSince — a visit two days after the last one (this device's record, "gv-wn-seen", as the page keeps it):
                    the line says how many updates came since, every entry that came after the last visit — and no
                    other — shows "New for you", and the line was there before the feed was drawn (nothing moves:
                    the page's layout shifts add up to almost nothing, where a line popping in above the feed would
                    move it a tenth of the window). "Mark all as read" from the keyboard hides the line and the marks,
                    tells screen readers, and keyboard focus goes to the first day's heading; a reload in the same
                    visit shows nothing again. On a 360-pixel phone at 150 % text (English and Spanish) the line
                    fits: no sideways scroll. A first visit (no record) shows nothing.

The record's times are the browser's own clock (two days before it): nothing here depends on a date.
"""
from __future__ import annotations

import json
import re
import unittest

from .test_site_in_browser import S, SIDEWAYS, new_context, open_page, setUpModule, tearDownModule  # noqa: F401

# Before the page's own scripts, once per browser tab (a reload keeps what the page itself stored since): the record
# of a visit two days ago whose newest entry was `upto`; and the page's layout shifts, as they happen.
SEED = """((upto) => {
  try {
    if (!sessionStorage.getItem("gv-test-seeded")) {
      localStorage.setItem("gv-wn-seen", JSON.stringify({ upto: upto, last: Date.now() - 2 * 864e5, base: null }));
      sessionStorage.setItem("gv-test-seeded", "1");
    }
  } catch (e) {}
  window.__shifts = [];
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__shifts.push(e.value); })
      .observe({ type: "layout-shift", buffered: true });
  } catch (e) {}
})(%s);"""
STATE = """() => {
  const box = document.getElementById("wn-since");
  const shown = (el) => getComputedStyle(el).display !== "none";
  return {
    line: !box.hidden, text: box.querySelector("[data-wn-since-text]").textContent,
    marked: [...document.querySelectorAll(".cm-entry")].filter((e) => shown(e.querySelector(".cm-wn-new"))).map((e) => e.getAttribute("data-seen")),
    shifts: (window.__shifts || []).reduce((a, v) => a + v, 0),
    status: document.querySelector(".cm-wn-feed [aria-live=polite]").textContent,
    focus: document.activeElement.classList.contains("cm-day-head") ? "day heading" : document.activeElement.tagName,
  };
}"""


def seen_list(lang: str) -> list[list[int]]:
    page = (S["site"] / ("es" if lang == "es" else "") / "whats-new" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="wn-seen">(.*?)</script>', page, re.S)
    if not m:
        raise AssertionError("whats-new/index.html: no wn-seen list (the line's data)")
    return json.loads(m.group(1))


class WhatsNewSince(unittest.TestCase):
    def last_visit(self, lang: str = "en") -> tuple[int, list[str], int]:
        """The last visit's newest entry (the 10th newest time on the page), the entries newer than it and their items."""
        lst = seen_list(lang)
        times = sorted({s for s, _ in lst}, reverse=True)
        self.assertGreater(len(times), 10, "the built What's New has entries enough to test with")
        upto = times[9]
        return upto, sorted(str(s) for s, _ in lst if s > upto), sum(n for s, n in lst if s > upto)

    def test_a_later_visit_marks_what_came_since_and_mark_all_as_read(self):
        upto, fresh, n = self.last_visit()
        ctx = new_context(1280, 900)
        try:
            ctx.add_init_script(SEED % upto)
            page = open_page(ctx, "whats-new/")
            page.wait_for_timeout(300)
            r = page.evaluate(STATE)
            self.assertTrue(r["line"], "the line is shown")
            self.assertEqual(r["text"].replace("\u00a0", " ").split(": ")[-1], f"{n} updates")
            self.assertTrue(r["text"].startswith("New since your last visit ("), r["text"])
            self.assertEqual(sorted(r["marked"]), fresh, "“New for you” on exactly the entries that came after it")
            self.assertLess(r["shifts"], 0.01, "nothing moved: the line was there before the feed was drawn")
            page.focus("#wn-since button")
            page.keyboard.press("Enter")
            page.wait_for_timeout(200)
            r = page.evaluate(STATE)
            self.assertEqual((r["line"], r["marked"]), (False, []))
            self.assertEqual(r["status"], "Marked as read. Your next visit counts from now.")
            self.assertEqual(r["focus"], "day heading")
            page.reload(wait_until="load")
            page.wait_for_timeout(300)
            r = page.evaluate(STATE)
            self.assertEqual((r["line"], r["marked"]), (False, []), "the same visit: nothing comes back")
        finally:
            ctx.close()

    def test_it_fits_a_phone_at_150_percent(self):
        for lang in ("en", "es"):
            with self.subTest(lang=lang):
                upto, fresh, _n = self.last_visit(lang)
                ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
                try:
                    ctx.add_init_script(SEED % upto)
                    page = open_page(ctx, ("es/" if lang == "es" else "") + "whats-new/")
                    page.wait_for_timeout(300)
                    r = page.evaluate(STATE)
                    self.assertTrue(r["line"])
                    self.assertEqual(sorted(r["marked"]), fresh)
                    side = page.evaluate(SIDEWAYS)
                    self.assertEqual((side["moved"], side["scrollWidth"] <= side["width"]), (0, True), side)
                finally:
                    ctx.close()

    def test_nothing_on_a_first_visit(self):
        ctx = new_context(1280, 900)
        try:
            page = open_page(ctx, "whats-new/")
            r = page.evaluate(STATE)
            self.assertEqual((r["line"], r["marked"]), (False, []))
            rec = json.loads(page.evaluate("() => localStorage.getItem('gv-wn-seen')"))
            self.assertIsNone(rec["base"], "remembered for next time, nothing to compare with yet")
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
