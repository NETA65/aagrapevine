"""Round 26b · the monthly posters in a real browser (tests/browser/__init__.py says how to run these; they share
test_site_in_browser.py's site server and browser). The owner: "every event of the month on the poster, with smaller
borders":

  * EveryDateFits — every month page the build has (poster_months: this month and the next 12), English and Spanish:
                    once the page has fitted its poster (src/assets/js/monthly.js: data-mp-fit), the poster holds every
                    date of the page's Dates list, nothing overflows its column or the 1080 × 1350 sheet (the fit's own
                    measure), each block is there once and in the reading order of its column, and the type is 15px at
                    least (7.5 pt on a Letter page).
  * PrintOnePage  — the busiest month's poster prints on one US Letter page, English and Spanish, every date on it.

Nothing here depends on today's date: the months are the build's, the dates are each page's own.
"""
from __future__ import annotations

import re
import unittest

from .test_site_in_browser import S, new_context, open_page, poster_months, setUpModule, tearDownModule  # noqa: F401

FITTED = "() => { const p = document.querySelector('[data-mp-poster]'); return !!p && p.hasAttribute('data-mp-fit'); }"

# The fitted poster against the page: its dates, its size and type, and the fit's own overflow measure (offsets: no
# scale, no tilt of the cork's cards) on every block, column and band.
CHECK = r"""() => {
  const p = document.querySelector("[data-mp-poster]");
  const BLOCKS = ".mp-b, .mp-foot, .mp-head, .mp-row, .mp-col, .mp-body, .mp-board, .mp-cover, .mp-strip, .mp-page, .mp-main, .mp-stub, .mp-side, .mp-content, .mp-top, .mp-feature, .mp-rail, .mp-band";
  const box = (el) => { let t = 0, l = 0, e = el; while (e && e !== p) { t += e.offsetTop; l += e.offsetLeft; e = e.offsetParent; } return { t, b: t + el.offsetHeight, r: l + el.offsetWidth }; };
  const over = [];
  p.querySelectorAll(BLOCKS).forEach((b) => {
    if (getComputedStyle(b).display === "none") return;
    const par = b.parentElement, bb = box(b);
    const pad = parseFloat(getComputedStyle(par).paddingBottom) || 0;
    const limit = par === p ? p.clientHeight - pad : box(par).t + par.clientTop + par.clientHeight - pad;
    if (bb.b > limit + 2) over.push(b.className + " +" + Math.round(bb.b - limit) + "px");
    if (bb.r > p.clientWidth + 2) over.push(b.className + " → +" + Math.round(bb.r - p.clientWidth) + "px");
  });
  // (a row's words without what only a screen reader hears: " (external)" after an outside link)
  const text = (el) => { const c = el.cloneNode(true); c.querySelectorAll(".sr-only, .mp-sr").forEach((s) => s.remove()); return c.textContent.replace(/\s+/g, " ").trim(); };
  const order = [];
  p.querySelectorAll("[data-mp-slot]").forEach((s) => {
    const o = [...s.children].filter((k) => k.hasAttribute("data-mp-order")).map((k) => Number(k.getAttribute("data-mp-order")));
    if (o.some((v, i) => i && v < o[i - 1])) order.push(s.getAttribute("data-mp-slot") + ": " + o.join(","));
  });
  const kinds = [...p.querySelectorAll(".mp-b")].map((b) => [...b.classList].find((c) => c !== "mp-b" && c !== "mp-dates--cols"));
  return {
    size: p.offsetWidth + " x " + p.offsetHeight, font: parseFloat(getComputedStyle(p).fontSize),
    poster: [...p.querySelectorAll(".mp-dlist > li .mp-date-t")].map(text).sort(),
    page: [...document.querySelectorAll("#mp-dates li.mp-drow .mp-drow-t")].map(text).sort(),
    more: !!p.querySelector(".mp-more"), over, order,
    twice: kinds.filter((k, i) => kinds.indexOf(k) !== i),
  };
}"""


class EveryDateFits(unittest.TestCase):
    def test_every_months_poster_holds_every_date(self):
        months = poster_months()
        self.assertGreaterEqual(len(months), 1, "month pages with their poster")
        problems: list[str] = []
        errors: list[str] = []
        ctx = new_context(1280, 900)
        try:
            for month in months:
                for lang in ("en", "es"):
                    path = ("es/" if lang == "es" else "") + f"monthly/{month}/"
                    page = open_page(ctx, path, errors)
                    page.wait_for_function(FITTED, timeout=30_000)
                    r = page.evaluate(CHECK)
                    page.close()
                    where = f"/{path}"
                    if r["size"] != "1080 x 1350":
                        problems.append(f"{where}: the poster is {r['size']}")
                    if r["poster"] != r["page"]:
                        problems.append(f"{where}: the poster's dates {r['poster']} are not the page's {r['page']}")
                    if r["more"]:
                        problems.append(f"{where}: \"more on the website\"")
                    if r["over"]:
                        problems.append(f"{where}: overflows at {r['font']}px — {r['over'][:4]}")
                    if r["font"] < 15:
                        problems.append(f"{where}: type {r['font']}px")
                    if r["order"]:
                        problems.append(f"{where}: out of the reading order — {r['order']}")
                    if r["twice"]:
                        problems.append(f"{where}: twice on the poster — {r['twice']}")
        finally:
            ctx.close()
        self.assertEqual(errors, [])
        self.assertEqual(problems, [], "\n".join(problems))


class PrintOnePage(unittest.TestCase):
    def test_the_busiest_months_poster_prints_on_one_letter_page(self):
        months = poster_months()
        self.assertTrue(months)
        rows = {m: (S["site"] / "monthly" / m / "index.html").read_text(encoding="utf-8").count('class="mp-date mp-date--')
                for m in months}
        busiest = max(months, key=lambda m: (rows[m], m))
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            try:
                page = open_page(ctx, ("es/" if lang == "es" else "") + f"monthly/{busiest}/")
                page.wait_for_function(FITTED, timeout=30_000)
                shown = page.evaluate("document.querySelectorAll('[data-mp-poster] .mp-dlist > li').length")
                page.emulate_media(media="print")
                pdf = page.pdf(prefer_css_page_size=True, print_background=True)
            finally:
                ctx.close()
            with self.subTest(month=busiest, lang=lang):
                self.assertEqual(shown, rows[busiest])
                self.assertEqual(len(re.findall(rb"/Type\s*/Page(?!s)", pdf)), 1, "one Letter page")
                self.assertIn(b"/MediaBox [0 0 612 792]", pdf.replace(b"  ", b" "))


if __name__ == "__main__":
    unittest.main()
