"""Round 33 · small fixes from the site audit, checked without a browser (tests/browser/test_r33_misc.py measures the
same things in a real one):

  * StatusLink      — the "A content source has stopped updating" issue links the LIVE Status page: the address
                      build-deploy works out from the GitHub Pages settings (its `site` output, the custom domain),
                      and config/site.yml's site.url only when that is empty (a run whose build stopped early).
  * MonthDescription — a month whose Grapevine theme already names the issue ("Annual Prison Issue", "Edición
                      anual sobre las prisiones") is not described as the “… Issue” issue / la edición “Edición …”.
  * Markup          — the weekly-meeting cards' title block gets a real class (not an escaped `class=&quot;…`);
                      the monthly posters' miniature wrappers are <div>s (a <span> may not hold the poster's <div>);
                      the booth preview's figcaption is its figure's last child; the footer logo (the grape app
                      icon since round 37) never shrinks; the Accessibility page's Google Meet links are 24px+
                      apart with a mouse.
  * Theme           — light / dark follows the site's other open tabs and a page brought back with Back
                      (app.js siteHeader: "storage" and "pageshow"), reading the saved choice and never writing it.
  * HeadScripts     — the two inline <head> scripts of base.njk carry no // comment lines (they went out with every
                      page); their explanations are Nunjucks comments, which the build drops.

    python -m unittest tests.test_r33_misc -v
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from workflow_steps import step_code  # noqa: E402


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def update_wf() -> dict:
    return yaml.safe_load(read(".github", "workflows", "update.yml"))


def step(job: dict, name: str) -> dict:
    found = [s for s in job.get("steps", []) if s.get("name") == name]
    assert len(found) == 1, f"one step named {name!r}"
    return found[0]


# ------------------------------------------------------------------------------------------------- live-1
class StatusLink(unittest.TestCase):
    def setUp(self):
        self.wf = update_wf()

    def test_build_deploy_hands_on_the_live_address(self):
        build = self.wf["jobs"]["build-deploy"]
        self.assertEqual(build["outputs"]["site"], "${{ steps.addr.outputs.site_url }}")
        self.assertIn('echo "site_url=${url}" >> "$GITHUB_OUTPUT"', step(build, "Work out the site address")["run"])
        report = self.wf["jobs"]["report"]
        self.assertIn("build-deploy", report["needs"])
        env = step(report, "Open, update or close the report issue")["env"]
        self.assertEqual(env["SITE_URL"], "${{ needs.build-deploy.outputs.site }}")
        self.assertEqual(env["HEALTH"], "${{ needs.sync.outputs.health }}")

    def body(self, health: dict, site_url: str | None) -> str:
        """The report step's script with a stand-in `gh` (no open issue yet) → the new issue's text."""
        code = step(self.wf["jobs"]["report"], "Open, update or close the report issue")["run"]
        code = step_code(code)
        calls: list[list[str]] = []

        def gh(args, **_kw):
            calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout="[]" if args[1:3] == ["issue", "list"] else "", stderr="")
        env = {"HEALTH": json.dumps(health), "RUN_URL": "https://github.com/o/r/actions/runs/1",
               "REPO_URL": "https://github.com/o/r"}
        with mock.patch.dict(os.environ, env), mock.patch("subprocess.run", gh), redirect_stdout(io.StringIO()):
            os.environ.pop("SITE_URL", None)
            if site_url is not None:
                os.environ["SITE_URL"] = site_url
            with self.assertRaises(SystemExit):
                exec(compile(code, "report", "exec"), {"__name__": "__main__"})  # noqa: S102 — the workflow's own script
        create = next(c for c in calls if c[1:3] == ["issue", "create"])
        return create[create.index("--body") + 1]

    HEALTH = {"stale": [{"source": "youtube", "label": "YouTube videos", "days": 9, "updated": "2026-09-25T06:00:00Z",
                         "error": "boom"}], "site": "https://neta65.github.io/aagrapevine", "days": 7}

    def test_the_issue_links_the_live_status_page(self):
        body = self.body(self.HEALTH, "https://grapevine.neta65.org/")
        self.assertIn("[Status page](https://grapevine.neta65.org/status/) · ", body)
        self.assertNotIn("github.io/aagrapevine/status", body)

    def test_without_the_live_address_the_settings_one_stands_in(self):
        for missing in (None, ""):
            with self.subTest(site_url=missing):
                body = self.body(self.HEALTH, missing)
                self.assertIn("[Status page](https://neta65.github.io/aagrapevine/status/) · ", body)
        body = self.body({**self.HEALTH, "site": ""}, "")
        self.assertNotIn("Status page", body, "no address at all: no link")


# -------------------------------------------------------------------------------------------------- seo-1
class MonthDescription(unittest.TestCase):
    def test_a_theme_that_names_the_issue_is_not_doubled(self):
        src = read("src", "pages", "monthly-month.njk")
        fm = yaml.safe_load(src.split("---", 2)[1])
        desc = fm["eleventyComputed"]["description"]
        expr = desc.split("%}", 1)[1]                          # without the {% set mm = … %} (the synced month)
        strings = json.loads(read("src", "_i18n", "monthly.json"))
        for lang in ("en", "es"):
            self.assertNotIn("{theme}” issue", strings["monthly.month_desc_named"][lang])
            self.assertNotIn("edición “{theme}", strings["monthly.month_desc_named"][lang])
        got = run_js(self, r"""
          const nunjucks = (await import("nunjucks")).default;
          const env = new nunjucks.Environment(null, { autoescape: true });
          env.addFilter("t", filters.t);
          const res = {};
          for (const [lang, theme] of input.cases)
            res[lang + "|" + theme] = env.renderString(input.expr, { mpage: { lang }, mm: { title: "July 2027", gv: { theme } } });
          res.plain = env.renderString(input.expr, { mpage: { lang: "en" }, mm: { title: "July 2027", gv: null } });
          out(res);""", data={"expr": expr, "cases": [
            ["en", "Annual Prison Issue"], ["es", "Edición anual sobre las prisiones"], ["es", "Edicion especial"],
            ["en", "Sober Seniors"], ["es", "Adultos mayores sobrios"], ["en", "Tissues and Sobriety"]]})
        self.assertEqual(got["en|Annual Prison Issue"], "July 2027: Grapevine's “Annual Prison Issue”, how to use it, "
                         "story deadlines, committee dates and a poster to download or print.")
        self.assertEqual(got["es|Edición anual sobre las prisiones"], "July 2027: “Edición anual sobre las prisiones” de "
                         "Grapevine, cómo usarla, fechas límite, fechas del comité y un cartel.")
        self.assertTrue(got["es|Edicion especial"].startswith("July 2027: “Edicion especial” de Grapevine"))
        # every other theme keeps the usual wording ("tissues" is no issue: a whole word only)
        self.assertEqual(got["en|Sober Seniors"], "July 2027: Grapevine's “Sober Seniors” issue, how to use it, story "
                         "deadlines, committee dates and a poster to download or print.")
        self.assertTrue(got["es|Adultos mayores sobrios"].startswith("July 2027: la edición “Adultos mayores sobrios” de"))
        self.assertIn("“Tissues and Sobriety” issue", got["en|Tissues and Sobriety"])
        self.assertTrue(got["plain"].startswith("July 2027: story deadlines"))


# ------------------------------------------------------------------- validity-1, validity-2, layout-2, layout-4
class Markup(unittest.TestCase):
    def test_the_weekly_cards_title_block_has_a_real_class(self):
        src = read("src", "pages", "meetings.njk")
        self.assertIn('<div{% if wf %} class="sm:col-span-2"{% endif %}>', src)
        # an attribute written by {{ … }} is escaped: class=&quot;…&quot; (the browser keeps the quote marks)
        self.assertIsNone(re.search(r"""\{\{\s*'\s*[\w:-]+="[^']*'\s+if\b""", src))

    def test_the_poster_miniatures_sit_in_divs(self):
        src = read("src", "pages", "monthly.njk")
        self.assertNotRegex(src, r'<span class="mp-(stage|fit)\b')
        self.assertEqual(len(re.findall(r'<div class="mp-stage mp-stage--thumb"[^>]*><div class="mp-fit">\{\{ mp\.posterMini\(',
                                        src)), 3)
        # posterMini starts with a <div> (why a <span> could not hold it)
        self.assertRegex(read("src", "_includes", "macros", "monthly.njk"), r'<div class="mp-poster mp-mini')

    def test_the_booth_preview_caption_is_the_figures_last_child(self):
        src = read("src", "_includes", "macros", "booth.njk")
        fig = src[src.index('<figure class="gvb-pv">'):src.index("</figure>")]
        self.assertLess(fig.index("data-gvb-pv-ctl"), fig.index("<figcaption"), "the controls stay inside, before it")
        self.assertTrue(fig.rstrip().endswith("</figcaption>"))

    def test_the_footer_logo_never_shrinks(self):
        # since round 37 the grape app icon (the NETA 65 wordmark is the header's only)
        foot = read("src", "_includes", "partials", "footer.njk")
        tile = re.search(r'<img src="/assets/img/app-icon-192.png" alt="" width="192" height="192" class="([^"]*)"', foot)
        self.assertIsNotNone(tile)
        self.assertIn("shrink-0", tile.group(1).split())
        self.assertIn("size-11", tile.group(1).split())
        self.assertNotIn('src="/assets/img/logo-wide.png"', foot)

    def test_the_meet_links_are_far_enough_apart(self):
        src = read("src", "pages", "accessibility.njk")
        card = src[src.index('{% for g in phone.online %}'):]
        card = card[:card.index("{% endfor %}\n", card.index("</ul>"))]
        ul = re.search(r'<ul class="([^"]*)" role="list">\s*\{% for it in g\.items %\}<li><a class="link tap-link"', card)
        self.assertIsNotNone(ul)
        self.assertIn("space-y-2", ul.group(1).split())


# ------------------------------------------------------------------------------------------------ jscode-2
class Theme(unittest.TestCase):
    def test_other_tabs_and_a_page_from_the_back_cache_follow(self):
        app = read("src", "assets", "js", "app.js")
        header = app[app.index('Alpine.data("siteHeader"'):app.index('Alpine.data("navMenu"')]
        init = header[header.index("init: function"):header.index("openComfort: function")]
        follow = init[init.index("var followTheme = function"):]
        self.assertIn('localStorage.getItem("gvlv-theme")', follow)
        self.assertIn('t = t === "dark" ? "dark" : "light";', follow)
        self.assertIn("self.theme = t;", follow)
        self.assertIn('document.documentElement.setAttribute("data-theme", t);', follow)
        self.assertIn('window.addEventListener("storage", function (e) { if (e.key === "gvlv-theme" || e.key === null) '
                      'followTheme(); });', follow)
        self.assertIn('window.addEventListener("pageshow", function (e) { if (e.persisted) followTheme(); });', follow)
        # it only reads: a write would bounce between two open tabs
        self.assertNotIn("setItem", follow)
        self.assertNotIn("removeItem", follow)
        # the button still saves, once (test_header_footer pins its words)
        self.assertEqual(header.count('localStorage.setItem("gvlv-theme"'), 1)
        # no newer syntax in a script old Safari runs
        self.assertNotRegex(follow, r"=>|\?\.|\?\?")


# --------------------------------------------------------------------------------------------------- perf-5
class HeadScripts(unittest.TestCase):
    def test_no_comment_lines_go_out_with_every_page(self):
        head = read("src", "_includes", "layouts", "base.njk").split("</head>")[0]
        scripts = re.findall(r"<script>(.*?)</script>", head, re.S)
        self.assertEqual(len(scripts), 2)
        for code in scripts:
            # Nunjucks comments (dropped by the build) are fine; no // line (sent with the page)
            outside = re.sub(r"\{#.*?#\}", "", code, flags=re.S)
            self.assertEqual([ln for ln in outside.splitlines() if ln.strip().startswith("//")], [])
            self.assertNotIn("/*", outside)
        # the explanations are still in the source, as Nunjucks comments
        for words in ("Reading & display settings before the first paint", "The body font, early",
                      "Theme before paint (no flash)", "A part of the page that changes at a set moment"):
            at = head.index(words)
            opened, closed = head.rfind("{#", 0, at), head.rfind("#}", 0, at)
            self.assertGreater(opened, closed, f"{words!r}: inside a Nunjucks comment")
        # a comment inside a script strips the whitespace in front of it ({#-), so its line leaves nothing behind
        for code in scripts:
            for c in re.findall(r"\{#.?", code):
                self.assertEqual(c, "{#-")


if __name__ == "__main__":
    unittest.main()
