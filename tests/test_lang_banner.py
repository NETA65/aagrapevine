"""The language suggestion (src/_includes/partials/lang-banner.njk: "¿Prefieres español? Ver en español" on an English
page in a Spanish-first browser, and the other way round), its script run in Node.js on a pretend page
(tests/fakedom.py) with the banner's Alpine component made as Alpine makes it:

  * remembered — switching language (the banner's own link, or the header's language switch: [data-lang-switch])
                 is remembered in localStorage "gv-lang-banner" ("switched"), and so is closing it ("dismissed"):
                 the suggestion is not offered again
  * not taken  — a switch the page stopped is not a switch: the story recorder's "Leave this page?" (recorder.js
                 askLeave, a capture listener that calls preventDefault when the visitor chooses to stay) keeps
                 them on the page with an unsaved take — the suggestion stays (r10 nav:F7: it was remembered as
                 "switched" and never offered again)

    python -m unittest tests.test_lang_banner -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fakedom import PAGE_JS  # noqa: E402
from nodejs import run_js  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PARTIAL = ROOT / "src" / "_includes" / "partials" / "lang-banner.njk"

# The banner's script (input.script, from the partial) on an English page in a Spanish-first browser, with the header's
# language switch and the banner's link; input.click: the link's @click, run as Alpine runs it (the component's data and
# $event in scope). stay: the story recorder's leave question is answered "stay" (it stops the click: preventDefault).
BANNER_JS = PAGE_JS + r"""
function banner({ stay = false } = {}) {
  const p = page({ html: '<header><a id="switch" href="/aagrapevine/es/contribute/" data-lang-switch>ES</a></header>' +
                         '<div id="banner"><a id="cta" href="/aagrapevine/es/contribute/" data-lang-switch>Ver en español</a>' +
                         '<button type="button" id="close">x</button></div>',
                   url: "https://example.test/aagrapevine/contribute/",
                   globals: { navigator: { language: "es-MX", languages: ["es-MX", "es", "en"] } } });
  const made = {};
  p.win.Alpine = { data: (name, fn) => { made[name] = fn; } };
  vm.runInContext(input.script, p.win, { filename: "lang-banner.njk" });
  p.doc.dispatchEvent(new p.win.Event("alpine:init"));
  const c = made.langBanner("en");
  Object.assign(c, { $el: p.$("#banner"), $watch() {}, $nextTick: (fn) => fn() });
  c.init();
  // the story recorder's leave question (recorder.js askLeave): a capture listener on the document, before the link's own
  p.doc.addEventListener("click", (e) => { if (stay && e.target.closest("a[href]")) e.preventDefault(); }, true);
  const onClick = new Function("scope", "$event", "with (scope) { return (" + input.click + "); }");
  p.$("#cta").addEventListener("click", (e) => onClick(c, e));
  return { p, c, kept: () => p.win.localStorage.getItem("gv-lang-banner") };
}
const R = {};
for (const stay of [true, false]) {
  for (const id of ["cta", "switch"]) {
    const { p, c, kept } = banner({ stay });
    await p.tick(1300);
    const shown = c.show;
    const went = p.click(p.$("#" + id));                                         // false: the click was stopped
    await p.tick(0);
    R[(stay ? "stay_" : "leave_") + id] = { shown, went, kept: kept(), errors: p.errors.map(String) };
  }
}
{
  const { p, c, kept } = banner();
  await p.tick(1300);
  c.dismiss();
  R.closed = { show: c.show, kept: kept() };
}
out(R);
"""


class Banner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = None

    def setUp(self):
        if Banner.r is None:
            src = PARTIAL.read_text(encoding="utf-8")
            script = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
            self.assertNotIn("{{", script, "the banner's script is plain JavaScript (nothing for Nunjucks to fill in)")
            click = re.search(r'<a [^>]*data-lang-switch @click="([^"]+)"', src).group(1)
            Banner.r = run_js(self, BANNER_JS, data={"script": script, "click": click}, needs_modules=False)
        self.r = Banner.r

    def test_a_switch_is_remembered(self):
        # the banner's own link and the header's language switch: the visitor chose — never offered again
        for id_ in ("cta", "switch"):
            r = self.r["leave_" + id_]
            self.assertTrue(r["shown"], "a Spanish-first browser on an English page is offered Spanish")
            self.assertEqual(r, {"shown": True, "went": True, "kept": "switched", "errors": []}, id_)

    def test_a_switch_the_page_stopped_is_not_remembered(self):
        # r10 nav:F7: "Leave this page?" about an unsaved take, answered "stay" — the visitor did not switch, so the
        # suggestion is not written off (both writers: the link's @click and the page-wide click listener)
        for id_ in ("cta", "switch"):
            self.assertEqual(self.r["stay_" + id_], {"shown": True, "went": False, "kept": None, "errors": []}, id_)

    def test_closing_it_is_remembered(self):
        self.assertEqual(self.r["closed"], {"show": False, "kept": "dismissed"})


if __name__ == "__main__":
    unittest.main()
