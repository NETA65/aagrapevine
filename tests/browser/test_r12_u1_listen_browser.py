"""Round 12 · Listen and Home's player on the built site, in a real browser (tests/browser/__init__.py says how to run
these; they share test_site_in_browser.py's site server and browser). The review's findings that only a browser shows
— what Alpine draws, where the keyboard focus goes:

  * ListenSharedLink — a shared episode (/listen/?ep=…) that is not among the newest 24, its full list slow (held back)
                       or gone (offline): the page says it is opening it; if the visitor plays the latest episode
                       meanwhile, it stays in the player and the shared one is offered ("Go to episode": then it is in
                       the player, its row marked, the keyboard on its play button); with no list, the page says the
                       link didn't open, the address keeps ?ep=, and the note's "Try again" (from the keyboard, in
                       Spanish) opens it.
  * HomeResumeFocus  — Home's "Continue listening": Enter on Resume hides the box, and the keyboard focus goes to the
                       player (it fell to the page's <body>).

Nothing here depends on today's date: the episode is the full list's 31st, whatever the day's episodes are.
"""
from __future__ import annotations

import json
import unittest

from .test_site_in_browser import S, new_context, open_page, setUpModule, tearDownModule, url  # noqa: F401 (its site server)

INDEX = "**/episodes-index.json"
CUR = "() => { const c = Alpine.store('audio').cur; return c ? c.id : null; }"
FOCUS_ROW = "() => { const a = document.activeElement; const r = a && a.closest('[data-ep]'); return r ? [r.getAttribute('data-ep'), a.className.split(' ')[0]] : [a.tagName, a.id]; }"


def older_episode() -> str:
    """An episode the page does not render (the newest 24 are): the full list's 31st."""
    items = json.loads((S["site"] / "episodes-index.json").read_text(encoding="utf-8"))["items"]
    if len(items) <= 30:
        raise unittest.SkipTest("fewer than 31 episodes: every one is among the page's first rows")
    return items[30]["id"]


class ListenSharedLink(unittest.TestCase):
    def test_the_visitors_episode_keeps_playing_and_the_link_is_offered(self):
        ep = older_episode()
        ctx = new_context(1280, 900)
        try:
            page = ctx.new_page()
            held = []
            page.route(INDEX, lambda route: held.append(route))          # a slow phone: the list is on its way
            page.goto(url("listen/?ep=" + ep), wait_until="load")
            page.wait_for_function("() => !!window.Alpine && !!Alpine.store('audio')")
            note = page.locator('[x-ref="linkNote"]')
            waiting = note.inner_text() if note.count() and note.is_visible() else ""
            page.locator(".listen-feature .media-play").click()          # the visitor plays the latest episode
            page.wait_for_function("() => !!Alpine.store('audio').cur")
            latest, y = page.evaluate(CUR), page.evaluate("() => scrollY")
            self.assertNotEqual(latest, ep)
            self.assertTrue(held, "the full list was asked for")
            for route in held:
                route.continue_()
            page.unroute(INDEX)
            # (the list is here: the shared episode is in the player — the old way — or offered)
            page.wait_for_function(f"""() => {{ const c = Alpine.store('audio').cur, n = document.querySelector('[x-ref="linkNote"]');
                                         return (c && c.id === {json.dumps(ep)}) || (!!n && /From your link:/.test(n.innerText)); }}""",
                                   timeout=15_000)
            page.wait_for_timeout(300)
            self.assertEqual(page.evaluate(CUR), latest, "what the visitor plays stays in the player")
            self.assertEqual(page.evaluate("() => scrollY"), y, "the page does not jump")
            self.assertIn("?ep=" + ep, page.url)
            self.assertIn("Opening the episode from your link", waiting, "while the list was on its way, the page said so")
            page.get_by_role("button", name="Go to episode").click()
            page.wait_for_function(f"() => {{ const c = Alpine.store('audio').cur; return c && c.id === {json.dumps(ep)}; }}")
            page.wait_for_function(f"() => document.activeElement && document.activeElement.closest('[data-ep]') "
                                   f"&& document.activeElement.closest('[data-ep]').getAttribute('data-ep') === {json.dumps(ep)}",
                                   timeout=10_000)
            self.assertEqual(page.evaluate(FOCUS_ROW), [ep, "ep-art"], "the keyboard goes on from its row's play button")
            self.assertIn("is-linked", page.get_attribute(f'.ep-list [data-ep="{ep}"]', "class"))
            self.assertFalse(note.is_visible())
            self.assertIn("?ep=" + ep, page.url)
        finally:
            ctx.close()

    def test_offline_the_link_waits_and_try_again_opens_it(self):
        ep = older_episode()
        ctx = new_context(390, 844, lang="es")
        try:
            page = ctx.new_page()
            page.route(INDEX, lambda route: route.abort("internetdisconnected"))      # no signal for the list
            page.goto(url("es/listen/?ep=" + ep), wait_until="load")
            page.wait_for_function("() => { const d = window.Alpine && Alpine.$data(document.querySelector('[x-data=\"podcastPage\"]')); "
                                   "return !!d && d.failed && d.ready; }", timeout=15_000)
            page.wait_for_timeout(200)
            self.assertIn("?ep=" + ep, page.url, "the address keeps it")
            self.assertIsNone(page.evaluate(CUR))
            note = page.locator('[x-ref="linkNote"]')
            self.assertIn("El episodio de tu enlace no se abrió", note.inner_text(), "the visitor is told")
            page.unroute(INDEX)
            again = note.get_by_role("button", name="Intentar de nuevo")
            again.focus()
            page.keyboard.press("Enter")
            page.wait_for_function(f"() => {{ const c = Alpine.store('audio').cur; return c && c.id === {json.dumps(ep)}; }}", timeout=15_000)
            page.wait_for_function(f"() => document.activeElement && document.activeElement.closest('[data-ep]') "
                                   f"&& document.activeElement.closest('[data-ep]').getAttribute('data-ep') === {json.dumps(ep)}",
                                   timeout=10_000)
            self.assertEqual(page.evaluate(FOCUS_ROW), [ep, "ep-art"])
            self.assertTrue(page.evaluate("() => Alpine.store('audio').held"), "loaded, not playing: nothing saved yet")
            self.assertFalse(note.is_visible())
            self.assertIn("?ep=" + ep, page.url)
        finally:
            ctx.close()


class HomeResumeFocus(unittest.TestCase):
    def test_resume_hands_the_keyboard_to_the_player(self):
        ctx = new_context(1280, 900)
        try:
            ctx.add_init_script("""(() => { try {
              localStorage.setItem("gv:audio:pos", JSON.stringify({ "pod:gv:test": [600, Date.now()] }));
              localStorage.setItem("gv:audio:last", JSON.stringify({ id: "pod:gv:test", t: "Half heard", a: "https://ep.example.test/x.mp3",
                                                                     art: "", du: 1800, sh: "gv", u: "", at: Date.now() }));
            } catch (e) {} })();""")
            page = open_page(ctx, "")
            resume = page.locator(".home-episode .media-player button.btn-lv")      # "Resume"
            resume.wait_for(state="visible", timeout=10_000)
            resume.focus()
            page.keyboard.press("Enter")
            resume.wait_for(state="hidden", timeout=5_000)                          # the box goes away
            page.wait_for_timeout(200)
            self.assertEqual(page.evaluate("() => document.activeElement.tagName"), "AUDIO", "the keyboard goes on from the player")
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
