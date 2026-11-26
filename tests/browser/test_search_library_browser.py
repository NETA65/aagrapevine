"""Round 33 · Search and Library on the built site, in a real browser (tests/browser/__init__.py says how to run these;
they share test_site_in_browser.py's site server and browser). The scripts' own logic is in tests/test_search_library.py.

  * SearchFirstPaint — (layout-1) a visit that arrives with ?q= doesn't jump: its query state (results layout, type
                       filters, "Loading…") from the first paint, the layout a screen tall while the index loads, so
                       neither the results nor the footer move when they come (CLS was 0.26–0.38, "poor"): measured
                       on /search/?q=grapevine and /es/search/?q=vina, phone and desktop, the index 1.5 s late. Clear
                       and Escape still bring the start state back.
  * SearchTargets    — layout-3: the type chips are 44px on a phone; layout-5: a tap anywhere on "Episode page"
                       opens the episode page, never the result above it; layout-6: on a Library card on a phone a
                       tap anywhere on "English · Español" opens that language, never the "Found on …" link below it.
  * StalledIndex     — (jscode-1) a server that never answers: Search, the Library and a presentation show their error
                       and Retry within ~20 s (they used to say "Loading…" for good), and Retry works once the
                       connection is back — the deck's even after its pointer prefetch had stalled.
"""
from __future__ import annotations

import json
import time
import unittest

from .test_site_in_browser import S, answered, url, setUpModule, tearDownModule  # noqa: F401 (its site server)

CLS_INIT = """window.__cls = 0; window.__shifts = [];
new PerformanceObserver((l) => { for (const e of l.getEntries()) { if (e.hadRecentInput) continue; window.__cls += e.value;
  window.__shifts.push(Math.round(e.value * 1000) / 1000 + ' ' + (e.sources || []).map((s) => s.node ? s.node.nodeName + (s.node.id ? '#' + s.node.id : '') : '?').join(','));
} }).observe({ type: 'layout-shift', buffered: true });"""
STATE = """() => ({ start: !document.getElementById('ss-start').hidden, layout: !document.getElementById('ss-layout').hidden,
  loading: !document.getElementById('ss-loading').hidden, error: !document.getElementById('ss-error').hidden,
  results: document.querySelectorAll('#ss-results li').length })"""


def context(width: int, phone: bool, lang: str = "en"):
    """A fresh profile (light: the site's first visit), a phone (touch, small screen) or a desktop with a mouse."""
    kw = dict(viewport={"width": width, "height": 844 if phone else 800}, reduced_motion="reduce", service_workers="block",
              timezone_id="America/Chicago", locale="es-US" if lang == "es" else "en-US")
    if phone:
        kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
    ctx = S["browser"].new_context(**kw)
    ctx.add_init_script(CLS_INIT)
    return ctx


def overrides(delays: dict[str, int]) -> None:
    prefix = S["server"].prefix
    S["overrides"].write_text(json.dumps({"delay_ms": {prefix + p.lstrip("/"): ms for p, ms in delays.items()}}), encoding="utf-8")


class SearchFirstPaint(unittest.TestCase):
    def tearDown(self):
        S["overrides"].unlink(missing_ok=True)

    def test_a_visit_with_a_query_does_not_jump(self):
        overrides({"search-index.json": 1500, "es/search-index.json": 1500})
        problems = []
        for path in ("search/?q=grapevine", "es/search/?q=vina"):
            for width, phone in ((390, True), (1280, False)):
                ctx = context(width, phone, "es" if path.startswith("es/") else "en")
                try:
                    page = ctx.new_page()
                    answered(page.goto(url(path), wait_until="load", timeout=60_000), path)
                    page.wait_for_selector("#ss-results li", timeout=20_000)
                    page.wait_for_timeout(500)
                    cls, shifts = page.evaluate("[window.__cls, window.__shifts]")
                    if cls > 0.05:
                        problems.append(f"/{path} at {width}: CLS {cls:.3f} {shifts}")
                finally:
                    ctx.close()
        self.assertEqual(problems, [])

    def test_clear_and_escape_bring_the_start_state_back(self):
        ctx = context(1280, False)
        try:
            page = ctx.new_page()
            answered(page.goto(url("search/?q=grapevine"), wait_until="load", timeout=60_000), "search/")
            page.wait_for_selector("#ss-results li", timeout=20_000)
            self.assertEqual(page.evaluate(STATE)["start"], False)
            page.click("#ss-clear")
            self.assertEqual(page.evaluate(STATE), {"start": True, "layout": False, "loading": False, "error": False, "results": 0})
            page.fill("#ss-q", "sponsor")
            page.wait_for_selector("#ss-results li", timeout=10_000)
            page.focus("#ss-q")
            page.keyboard.press("Escape")
            self.assertEqual(page.evaluate(STATE), {"start": True, "layout": False, "loading": False, "error": False, "results": 0})
        finally:
            ctx.close()


class SearchTargets(unittest.TestCase):
    def test_type_chips_are_44px_on_a_phone(self):
        ctx = context(390, True)
        try:
            page = ctx.new_page()
            answered(page.goto(url("search/?q=grapevine"), wait_until="load", timeout=60_000), "search/")
            page.wait_for_selector("#ss-results li", timeout=20_000)
            heights = page.evaluate("[...document.querySelectorAll('.ss-kinds .chip')].map((b) => b.getBoundingClientRect().height)")
            self.assertTrue(heights)
            self.assertTrue(all(h >= 44 for h in heights), heights)
        finally:
            ctx.close()

    def test_episode_page_link_takes_its_whole_height(self):
        for width, phone in ((390, True), (1280, False)):
            ctx = context(width, phone)
            try:
                page = ctx.new_page()
                answered(page.goto(url("search/?q=sponsorship"), wait_until="load", timeout=60_000), "search/")
                try:
                    page.wait_for_selector("#ss-results .ss-alt", timeout=20_000)
                except Exception:
                    self.skipTest("no podcast episode in this build's search results")
                missed = page.evaluate("""() => { const a = document.querySelector('#ss-results .ss-alt'); a.scrollIntoView({ block: 'center' });
                  const b = a.getBoundingClientRect(), out = [];
                  for (let dy = 1; dy < b.height; dy += 2) { const el = document.elementFromPoint(b.left + 20, b.top + dy);
                    if (!(el && el.closest('.ss-alt') === a)) out.push(dy); }
                  return out; }""")
                self.assertEqual(missed, [], f"at {width}: these px from its top open something else")
            finally:
                ctx.close()

    def test_library_language_links_are_not_covered_by_found_on(self):
        for lang in ("", "es/"):
            ctx = context(390, True, "es" if lang else "en")
            try:
                page = ctx.new_page()
                answered(page.goto(url(lang + "library/"), wait_until="load", timeout=60_000), lang + "library/")
                page.wait_for_timeout(1000)
                r = page.evaluate("""() => { const out = { checked: 0, missed: [] };
                  for (const card of document.querySelectorAll('.lib-card')) {
                    if (!card.querySelector('.lib-ref a')) continue;
                    for (const v of card.querySelectorAll('.lib-versions a')) {
                      out.checked++;
                      v.scrollIntoView({ block: 'center' });
                      const b = v.getBoundingClientRect();
                      for (let dy = 1; dy < b.height; dy += 2) { const el = document.elementFromPoint(b.left + b.width / 2, b.top + dy);
                        if (!(el && el.closest('.lib-versions a') === v)) { out.missed.push(card.id + ' ' + v.textContent.trim() + ' +' + dy); break; } }
                    }
                  }
                  return out; }""")
                if not r["checked"]:
                    continue    # (no card with both lines in this build)
                self.assertEqual(r["missed"], [], f"/{lang}library/")
            finally:
                ctx.close()


class StalledIndex(unittest.TestCase):
    def tearDown(self):
        S["overrides"].unlink(missing_ok=True)

    def test_a_server_that_never_answers_ends_in_retry(self):
        ctx = context(1280, False)
        try:
            ss, lib, deck = ctx.new_page(), ctx.new_page(), ctx.new_page()
            answered(deck.goto(url("orientation/"), wait_until="load", timeout=60_000), "orientation/")
            opener = deck.locator("[data-pres-open]").first
            deck_id = opener.get_attribute("data-pres-open")
            overrides({"search-index.json": 200_000, "library-index.json": 200_000,
                       f"orientation/presentations/{deck_id}.json": 200_000})
            ss.goto(url("search/?q=grapevine"), wait_until="domcontentloaded", timeout=60_000)
            lib.goto(url("library/?q=grapevine"), wait_until="domcontentloaded", timeout=60_000)
            opener.click()
            t0 = time.time()
            ss.wait_for_function("!document.getElementById('ss-error').hidden", timeout=30_000)
            lib.wait_for_function("!document.getElementById('lib-error').hidden", timeout=30_000)
            deck.wait_for_selector("[data-gvp-stage] button", timeout=30_000)
            waited = time.time() - t0
            self.assertGreater(waited, 15, "not before the 20 s limit")
            self.assertEqual(ss.evaluate(STATE)["loading"], False)
            self.assertIsNone(lib.get_attribute("#lib-results", "aria-busy"), "the cards are no longer dimmed")
            # the connection is back: Retry works
            S["overrides"].unlink(missing_ok=True)
            ss.click("#ss-retry")
            lib.click("#lib-retry")
            deck.locator("[data-gvp-stage] button").first.click()
            ss.wait_for_selector("#ss-results li", timeout=20_000)
            # (Retry sets aria-busy at once, for a query; it goes when the index is there)
            lib.wait_for_function("document.getElementById('lib-error').hidden && !document.getElementById('lib-results').hasAttribute('aria-busy')",
                                  timeout=20_000)
            deck.wait_for_function("!document.querySelector('[data-gvp-stage] .gvp-loading')", timeout=20_000)
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
