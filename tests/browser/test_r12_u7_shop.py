"""/shop/ "What it would cost" (#group-cost) in a real browser (tests/browser/__init__.py says how to run these; the
site server, Playwright and the browser are test_site_in_browser's).

  * ShopCostCalculator — English and Spanish: the card shows the sum once the page has started (the choices a
                         visitor makes are worked out in the page: the total is the copies times the price per copy it
                         names), a term the magazine does not sell is never left chosen, and on a 360-pixel phone at
                         150 % text nothing in the card reaches past the screen. The sum (a live region) is redrawn —
                         said again by a screen reader — only when it changes, never every minute of a page left
                         open; in High Contrast (forced colours) each choice shows which option is chosen.
  * ShopCostSheet      — "Print an information sheet": while it prints, only the sheet is on paper (the page's own
                         sections are not), in the languages chosen — both side by side — with the group's decision
                         under them; afterwards the page is as it was.

The browser's clock is stopped (Playwright's clock) so the page reads the same on any day; what the sums are on a
given day is tests/test_r12_u7_shop.py's (GV.shopQuote in Node).
"""
from __future__ import annotations

import re
import unittest

from browser.test_site_in_browser import (SIDEWAYS, new_context, open_page, setUpModule, tearDownModule)  # noqa: F401

FIXED = "2026-12-31T23:59:00-06:00"   # 11:59 PM Central on December 31, 2026


def money(text: str) -> float:
    """"$1,234.50" → 1234.5 (the first amount in the text)."""
    m = re.search(r"\$\s?([\d,]+\.\d{2})", text)
    if not m:
        raise AssertionError(f"no amount in {text!r}")
    return float(m.group(1).replace(",", ""))


def open_shop(ctx, lang: str, errors: list):
    page = ctx.new_page()
    page.clock.set_fixed_time(FIXED)
    page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))
    path = ("es/" if lang == "es" else "") + "shop/"
    from browser.test_site_in_browser import answered, url
    answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
    page.wait_for_selector("#group-cost .shop-cost-grid:not([x-cloak])", state="visible", timeout=10_000)
    page.locator("#group-cost").scroll_into_view_if_needed()
    return page


class ShopCostCalculator(unittest.TestCase):
    def test_the_sum_is_said_again_only_when_it_changes(self):
        # the sum is aria-live: redrawing it with the same words makes a screen reader say it again. A page left open
        # (its clock running: Playwright's) and a tab brought back must leave it alone; a new choice redraws it.
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="en")
        try:
            from browser.test_site_in_browser import answered, url
            page = ctx.new_page()
            page.clock.install(time="2026-12-30T12:00:00-06:00")      # noon Central, far from any price change
            page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0][:200]))
            answered(page.goto(url("shop/"), wait_until="load", timeout=60_000), "shop/")
            page.wait_for_selector("#group-cost .shop-cost-grid:not([x-cloak])", state="visible", timeout=10_000)
            page.evaluate("""() => { window.__said = 0;
              new MutationObserver((m) => { window.__said += m.length; })
                .observe(document.querySelector('#group-cost .shop-cost-sum'), { childList: true, characterData: true, subtree: true }); }""")
            before = page.inner_text("#group-cost .shop-cost-sum")
            page.clock.run_for(6 * 60_000)                              # six idle minutes
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")   # the tab brought back
            self.assertEqual(page.evaluate("window.__said"), 0, "an idle page leaves the sum alone (else it is said again)")
            self.assertEqual(page.inner_text("#group-cost .shop-cost-sum"), before)
            page.locator("#group-cost input[type=number]").fill("12")
            page.wait_for_function("window.__said > 0", timeout=5000)   # a real change is said
            self.assertNotEqual(page.inner_text("#group-cost .shop-cost-sum"), before)
            page.close()
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_the_choice_shows_in_high_contrast(self):
        # forced colours (Windows High Contrast) drop the chosen pill's background, its only mark: an outline must
        # show it — in every choice of the card (magazine, format, term, the sheet's language) and the price switch
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="en")
        try:
            page = open_shop(ctx, "en", errors)
            page.emulate_media(forced_colors="active")
            groups = page.evaluate("""() => [...document.querySelectorAll('.shop-seg')].filter((g) => g.getClientRects().length).map((g) => {
              const opts = [...g.querySelectorAll('.shop-seg-opt')].filter((o) => o.getClientRects().length);
              const ring = (o) => { const s = getComputedStyle(o.querySelector('input + span'));
                                    return s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2; };
              return { name: g.closest('fieldset').querySelector('legend').textContent.trim(),
                       chosen: opts.filter((o) => o.querySelector('input').checked).map(ring),
                       others: opts.filter((o) => !o.querySelector('input').checked).map(ring) };
            })""")
            self.assertGreaterEqual(len([g for g in groups if g["chosen"]]), 4, groups)
            for g in groups:
                with self.subTest(choice=g["name"]):
                    self.assertEqual(g["chosen"], [True], "the chosen option has an outline")
                    self.assertNotIn(True, g["others"], "the others have none")
            page.close()
        finally:
            ctx.close()
        self.assertEqual(errors, [])

    def test_the_sum_in_both_languages(self):
        errors: list[str] = []
        for lang in ("en", "es"):
            ctx = new_context(1280, 900, lang=lang)
            try:
                page = open_shop(ctx, lang, errors)
                card = page.locator("#group-cost")
                self.assertFalse(card.locator("[data-nojs-only]").is_visible(), "the no-JavaScript links stay hidden")
                first = card.locator(".shop-cost-total").inner_text()
                self.assertRegex(first, r"\$\d", f"/{lang}/: a total at once")
                field = card.locator("input[type=number]")
                field.fill("25")
                page.wait_for_timeout(100)
                total = money(card.locator(".shop-cost-total").inner_text())
                unit_line = card.locator(".shop-cost-lines li", has_text=re.compile(r"(a copy|por ejemplar)")).inner_text()
                self.assertAlmostEqual(total, round(25 * money(unit_line), 2), places=2, msg=f"/{lang}/: {unit_line}")
                self.assertIn("25", card.locator(".shop-cost-for").inner_text())
                # the store link is the chosen plan's page on the official store
                href = card.locator("a.shop-cost-buy").get_attribute("href") or ""
                self.assertRegex(href, r"^https://www\.(aagrapevine|aalavina)\.org/")
                # a term the other magazine does not sell is never left chosen: every chosen radio is shown
                for pub in ("gv", "lv"):
                    card.locator(f"input[name=shop-cost-pub][value={pub}]").check(force=True)
                    for typ in ("print", "digital", "complete"):
                        opt = card.locator(f"input[name=shop-cost-type][value={typ}]")
                        if opt.count() and opt.locator("xpath=..").is_visible():
                            opt.check(force=True)
                            page.wait_for_timeout(50)
                            chosen = card.locator("input[name=shop-cost-term]:checked")
                            self.assertEqual(chosen.count(), 1, f"/{lang}/ {pub} {typ}: a term is chosen")
                            self.assertTrue(chosen.locator("xpath=..").is_visible(), f"/{lang}/ {pub} {typ}: the chosen term is offered")
                            self.assertRegex(card.locator(".shop-cost-total").inner_text(), r"\$\d")
                field.fill("")
                field.blur()
                self.assertEqual(field.input_value(), "1", "an emptied field goes back to 1 copy")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])

    def test_no_sideways_scroll_at_150_percent_on_a_phone(self):
        errors: list[str] = []
        for lang in ("en", "es"):
            ctx = new_context(360, 780, lang=lang, prefs={"text": 150})
            try:
                page = open_shop(ctx, lang, errors)
                page.locator("#group-cost input[type=number]").fill("999")
                card = page.locator("#group-cost input[name=shop-cost-term][value='36']")
                if card.count() and card.locator("xpath=..").is_visible():
                    card.check(force=True)
                page.wait_for_timeout(200)
                wide = page.evaluate("""() => {
                  const w = document.documentElement.clientWidth, out = [];
                  for (const el of document.querySelectorAll('#group-cost *')) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.right > w + 1 && !el.closest('#shop-sheet')) out.push(el.tagName + '.' + el.className + ' → ' + Math.round(r.right));
                  }
                  return out.slice(0, 5);
                }""")
                self.assertEqual(wide, [], f"/{lang}/shop/ at 150 % on a 360px phone")
                page.close()
            finally:
                ctx.close()
        self.assertEqual(errors, [])


class ShopCostSheet(unittest.TestCase):
    def test_the_sheet_prints_alone(self):
        errors: list[str] = []
        ctx = new_context(1280, 900, lang="en")
        try:
            page = open_shop(ctx, "en", errors)
            # window.print is stopped where it would open the dialog: what is on paper then is checked instead
            page.evaluate("""() => { window.__printed = [];
              window.print = () => { window.__printed.push(document.documentElement.getAttribute('data-shop-print')); }; }""")
            card = page.locator("#group-cost")
            card.locator("input[type=number]").fill("12")
            card.locator("input[name=shop-cost-sheet][value=both]").check(force=True)
            # the attribute the button sets, kept while the paper is checked (the stub returns at once; the
            # browser's "afterprint" is held back until then)
            page.evaluate("""() => { const add = window.addEventListener.bind(window);
              window.addEventListener = (t, fn, o) => (t === 'afterprint' ? (window.__after = fn) : add(t, fn, o)); }""")
            card.get_by_role("button", name=re.compile("Print an information sheet")).click()
            page.wait_for_function("() => window.__printed.length === 1", timeout=5000)
            self.assertEqual(page.evaluate("() => window.__printed"), ["both"])
            page.emulate_media(media="print")
            shown = page.evaluate("""() => {
              const vis = (el) => !!el && getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().height > 0;
              return { sheet: vis(document.getElementById('shop-sheet')),
                       parts: [...document.querySelectorAll('.shop-sheet-part')].map((p) => [p.lang, vis(p)]),
                       side: (() => { const [a, b] = document.querySelectorAll('.shop-sheet-part');
                                      return Math.abs(a.getBoundingClientRect().top - b.getBoundingClientRect().top) < 2; })(),
                       decision: vis(document.querySelector('.shop-sheet-decision')),
                       hero: vis(document.querySelector('h1')), group: vis(document.getElementById('group-title')),
                       calc: vis(document.querySelector('.shop-cost-grid')), header: vis(document.querySelector('.site-header')),
                       copies: [...document.querySelectorAll('.shop-sheet-facts dd')].map((d) => d.textContent.trim())[2],
                       total: document.querySelector('.shop-sheet-part[lang=es] .is-total dd').textContent };
            }""")
            self.assertTrue(shown["sheet"])
            self.assertEqual(shown["parts"], [["en", True], ["es", True]])
            self.assertTrue(shown["side"], "both languages side by side")
            self.assertTrue(shown["decision"])
            self.assertEqual((shown["hero"], shown["group"], shown["calc"], shown["header"]), (False, False, False, False),
                             "only the sheet on paper")
            self.assertEqual(shown["copies"], "12")
            self.assertIn("por 1 año", shown["total"])
            # afterwards (the browser's "afterprint"): the page as it was
            page.evaluate("() => window.__after && window.__after()")
            self.assertIsNone(page.evaluate("() => document.documentElement.getAttribute('data-shop-print')"))
            self.assertFalse(page.evaluate("() => getComputedStyle(document.getElementById('shop-sheet')).display !== 'none'"),
                             "Ctrl+P prints the page, not the sheet")
            page.close()
        finally:
            ctx.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
