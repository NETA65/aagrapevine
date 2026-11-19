"""Round 33c · the build's estimate of the poster against the browser (tests/browser/__init__.py says how to run these;
they share test_site_in_browser.py's site server and browser).

The build places the split layout's movable blocks (the story, the Book of the Month, the weekly meetings) from an
estimate of each block's height — the words it prints, set in the poster's two typefaces at the poster's starting type
(eleventy/filters/monthly.js posterPlaces, posterBlocks; tests/test_r33c_posterplaces.py). That estimate mirrors the
stylesheet (areas/monthly.css: sizes, spaces, the columns) and the fonts (Inter, Fraunces). Here the posters of
tests/test_r33c_posterplaces.py's fixed month models (November 2026's rows in English and Spanish, a quiet month) are
built by the site's own macro, put into a month page of the build in place of its poster (the page's script blocked:
the poster as built, before its fit) and measured in the browser — the site's own stylesheet and fonts — against the
estimate they were placed by: each column's blocks in all and where the dates end, within 30px (the columns' 32px
bottom padding: an estimate that close still keeps on the sheet what it says fits). Fixed words, so only a change of
the stylesheet or the fonts that the estimate does not follow can fail it — never a month's data.
"""
from __future__ import annotations

import re
import unittest

from .test_site_in_browser import new_context, open_page, poster_months, setUpModule, tearDownModule  # noqa: F401

try:                                    # (discover -s tests/browser -t tests: tests/ is on the path)
    from nodejs import run_js
    from test_r33c_posterplaces import OFFERS, ROWS, SITE, model
except ImportError:                     # (python -m unittest tests.browser.…: the repository is)
    from tests.nodejs import run_js
    from tests.test_r33c_posterplaces import OFFERS, ROWS, SITE, model

TOLERANCE = 30

# the fixed posters, built by the site's macro (no page of src/pages: ONLY), and the estimate each was placed by
BUILD = r"""
process.env.ONLY = "-none-";
const M = await imp("eleventy/filters/monthly.js");
const conf = await imp("eleventy.config.js");
const t = (k, l, v) => conf.translateKey(k, l, v);
const os = await import("node:os");
const { Eleventy } = await import("@11ty/eleventy");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-poster-est-"));
try {
  const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js", config(cfg) {
    for (const [name, c] of Object.entries(input.cases)) {
      cfg.addTemplate(`mp-est-${name}.njk`, '{% import "macros/monthly.njk" as mp with context %}{{ mp.poster(m, lang, site, "t") }}',
                      { ...c, site: input.site, layout: false, permalink: `/mp-est-${name}/index.html`, eleventyExcludeFromCollections: true, sitemap: false });
    }
  } });
  const pages = await elev.toJSON();
  const html = Object.fromEntries(pages.filter((p) => /^\/mp-est-/.test(p.url || "")).map((p) => [p.url.slice(8, -1), p.content]));
  out(Object.fromEntries(Object.entries(input.cases).map(([name, c]) => [name, { html: html[name], est: M.posterPlaces(c.m, input.site, t) }])));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
"""

# the poster in place of the page's own, once its fonts are in: each column's blocks (the ones drawn) stacked with its
# gap, inside its padding, and where the dates end in it
MEASURE = r"""async (html) => {
  const old = document.querySelector("[data-mp-poster]");
  old.insertAdjacentHTML("afterend", html);
  old.remove();
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  const p = document.querySelector("[data-mp-poster]");
  const cols = {};
  p.querySelectorAll("[data-mp-slot]").forEach((s) => {
    const cs = getComputedStyle(s), kids = [...s.children].filter((k) => k.offsetHeight);
    const need = kids.reduce((h, k) => h + k.offsetHeight, 0) + Math.max(0, kids.length - 1) * (parseFloat(cs.rowGap) || 0);
    const d = s.querySelector(":scope > .mp-dates");
    cols[s.getAttribute("data-mp-slot")] = { need: Math.round(need),
      datesEnd: d ? Math.round(d.offsetTop - parseFloat(cs.paddingTop) + d.offsetHeight) : null };
  });
  return { fitted: p.hasAttribute("data-mp-fit"), font: parseFloat(getComputedStyle(p).fontSize), cols };
}"""


class EstimateMatchesTheBrowser(unittest.TestCase):
    def test_the_fixed_split_posters_as_built(self):
        cases = {"busy-en": {"m": model("en", ROWS["en"], OFFERS["en"], True), "lang": "en"},
                 "busy-es": {"m": model("es", ROWS["es"], OFFERS["es"], True), "lang": "es"},
                 "quiet-en": {"m": model("en", ROWS["en"][:3], [], False, "snug"), "lang": "en"},
                 "quiet-es": {"m": model("es", ROWS["es"][:3], [], False, "snug"), "lang": "es"}}
        built = run_js(self, BUILD, data={"cases": cases, "site": SITE}, timeout=300)
        self.assertEqual(sorted(built), sorted(cases))
        month = poster_months()[0]
        problems = []
        ctx = new_context(1280, 1400)
        ctx.route(re.compile(r".*/assets/js/monthly\.js(\?.*)?$"), lambda route: route.abort())
        try:
            for name, c in cases.items():
                page = open_page(ctx, ("es/" if c["lang"] == "es" else "") + f"monthly/{month}/")
                r = page.evaluate(MEASURE, built[name]["html"])
                page.close()
                est = built[name]["est"]
                self.assertFalse(r["fitted"], "the page's script was blocked: the poster as built")
                self.assertEqual(r["font"], est["T"], f"{name}: the starting type")
                for col, e in est["cols"].items():
                    for what in ("need", "datesEnd"):
                        a, b = r["cols"][col][what], e[what]
                        if (a is None) != (b is None) or (a is not None and abs(a - b) > TOLERANCE):
                            problems.append(f"{name} {col} {what}: {a}px in the browser, {b}px estimated")
                    # what the estimate says fits does fit (its padding aside): the dates, the column's blocks
                    if e["need"] <= e["room"] and r["cols"][col]["need"] > e["room"] + 32:
                        problems.append(f"{name} {col}: {r['cols'][col]['need']}px, more than the column's {e['room']}px")
        finally:
            ctx.close()
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
