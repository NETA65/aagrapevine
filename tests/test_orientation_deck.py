"""The sessions' slide show (src/assets/js/orientation.js, /orientation/), run in Node.js on a pretend page
(tests/fakedom.py): opened from a session's "slides" link (/orientation/?slides#session-<id>), the deck opens at
that session and has the keyboard focus — and keeps it when, as the page finishes loading, the browser's own jump
to the #fragment takes the focus out of it to the page behind (the deck takes it back after the load event); a
focus the visitor already moved inside the deck stays where it is.

    python -m unittest tests.test_orientation_deck -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

HTML = r"""
<main><h1>GVR / RLV 101</h1>
  <article id="session-magazines"><h2>The magazines</h2><a href="#" data-o101-present>Present as slides</a></article>
</main>
<template id="o101-deck-tpl">
  <div class="o101-deck" role="dialog" aria-modal="true" aria-label="Slides" tabindex="-1" data-o101-deck data-t-live="Slide {n} of {total}: {title}">
    <div data-o101-stage>
      <section data-o101-slide id="slide-1" hidden><h2>Welcome</h2></section>
      <section data-o101-slide id="slide-2" data-lesson="magazines" hidden><h2>The magazines</h2></section>
      <section data-o101-slide id="slide-3" hidden><h2>Points</h2></section>
    </div>
    <span data-o101-n></span><p data-o101-live></p>
    <button type="button" data-o101-prev>Back</button><button type="button" data-o101-next>Next</button>
    <button type="button" data-o101-exit>Exit</button>
  </div>
</template>
"""

DECK_JS = PAGE_JS + r"""
async function open(moveTo) {
  const p = page({ html: input.html, url: "https://example.test/aagrapevine/orientation/?slides#session-magazines",
                   scripts: ["src/assets/js/orientation.js"] });
  const deck = () => p.$(".o101-deck");
  const where = () => { const a = p.doc.activeElement; return a === p.doc.body ? "body" : a === deck() ? "deck" : a.getAttribute("data-o101-next") !== null ? "next" : a.tagName; };
  p.doc.readyState = "interactive";
  p.doc.dispatchEvent(new p.win.Event("DOMContentLoaded", { bubbles: true }));
  await p.tick(0);
  const r = { opened: where(), shown: p.$$("[data-o101-slide]").filter((s) => !s.hidden).map((s) => s.id), url: p.win.location.hash };
  // the browser's jump to the address's #fragment as the page finishes loading: the focus leaves the deck
  if (moveTo === "next") p.$("[data-o101-next]").focus(); else p.doc.activeElement.blur();
  r.beforeLoad = where();
  p.doc.readyState = "complete";
  p.win.dispatchEvent(new p.win.Event("load"));
  await p.tick(0);
  r.afterLoad = where();
  r.errors = p.errors.map(String);
  return r;
}
out({ lost: await open(""), inside: await open("next") });
"""


class DeckFocus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if DeckFocus.r is None:
            DeckFocus.r = run_js(self, DECK_JS, data={"html": HTML}, needs_modules=False)
        self.r = DeckFocus.r

    def test_the_deck_takes_the_focus_back_after_the_load(self):
        r = self.r["lost"]
        self.assertEqual(r["opened"], "deck")
        self.assertEqual(r["shown"], ["slide-2"])                         # the session's own slide
        self.assertEqual(r["url"], "#slide-2")
        self.assertEqual(r["beforeLoad"], "body")
        self.assertEqual(r["afterLoad"], "deck")                          # P4-5: back in the deck
        self.assertEqual(r["errors"], [])

    def test_a_focus_inside_the_deck_stays(self):
        self.assertEqual(self.r["inside"]["afterLoad"], "next")


if __name__ == "__main__":
    unittest.main()
