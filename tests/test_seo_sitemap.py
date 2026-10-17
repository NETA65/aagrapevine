"""What search engines get: /sitemap.xml (src/pages/sitemap.11ty.js), the [seo] build check (eleventy/seo-check.js),
the IndexNow key file (src/pages/indexnow-key.11ty.js) and Website update's IndexNow steps (update.yml).

  * Sitemap      — well-formed XML in the sitemaps.org namespace with the xhtml alternates; every <loc> absolute
                   under site.url, each once; en / es / x-default alternates that answer each other; pages with
                   `sitemap: false` or `noindex: true` left out (both languages of a paginated page), as are feeds,
                   files and the 404 page; valid against the sitemaps.org schema (tests/fixtures/sitemap_xsd/).
  * [seo] check  — silent on a clean site; one problem each for a page the sitemap lists that is not built, is not
                   its own canonical, is noindex, or has no title or description, for two pages of ONE language with
                   one title (never across languages, never about lengths), and for a page that may be indexed but is
                   not in the sitemap (a noindex share page or a redirect is not one); a real build of a few pages
                   passes it; it runs only on a whole build written to disk, and is registered before the build's
                   summing-up, so a full build lists a planted problem with its warnings (one full build).
  * IndexNow     — the key file holds exactly the key, at /<key>.txt, and is not built without a valid key; the build
                   job turns the list of changed pages into the request (host, key, keyLocation, urlList), only from a
                   key file the build made and only for addresses on the site; "Check the build" says how many pages
                   got the build's date and warns when more than 30 changed while the code did not; the publish job
                   sends it after a successful publish only, and can never fail it.

Skipped without Node.js / the site's npm packages (tests/nodejs.py) or bash.

    python -m unittest tests.test_seo_sitemap -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import run_js  # noqa: E402
from test_lastmod import validate  # noqa: E402
from test_morning import bash_path, step_of  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
BASE = "https://x.test/site"


# ============================================================================ the sitemap
class Sitemap(unittest.TestCase):
    def render(self, all_pages: list[dict]) -> str:
        return run_js(self, r"""
          const S = await imp("src/pages/sitemap.11ty.js");
          console.warn = () => {};
          out(S.render({ site: { url: input.base + "/" }, collections: { all: input.all } }));""",
                      data={"all": all_pages, "base": BASE}, env={"ONLY": ""})

    def test_the_file(self):
        def p(url, **data):
            return {"url": url, "data": data}
        langs = {"pagination": {"hrefs": ["/x/", "/es/x/"]}}
        xml = self.render([
            p("/"), p("/es/"), p("/about/", **{"pagination": {"hrefs": ["/about/", "/es/about/"]}}), p("/a&b/"), p("/es/a&b/"),
            p("/only-en/"),
            p("/x/", noindex=True, **langs),                                    # noindex: both languages out
            p("/old/", sitemap=False, pagination={"hrefs": ["/old/", "/es/old/"]}),   # opted out
            p("/feed.xml"), p("/404.html"), p("/es/404.html"), p("/build.json"), p(None), p("/about/"),
        ])
        root = ET.fromstring(xml.encode("utf-8"))
        self.assertEqual(root.tag, "{%s}urlset" % NS["s"])
        self.assertIn('xmlns:xhtml="http://www.w3.org/1999/xhtml"', xml)
        locs = [u.findtext("s:loc", namespaces=NS) for u in root.findall("s:url", NS)]
        self.assertEqual(locs, [f"{BASE}{u}" for u in ("/", "/es/", "/a&b/", "/es/a&b/", "/about/", "/es/about/", "/only-en/")])
        self.assertEqual(len(locs), len(set(locs)), "each page once")
        self.assertNotIn("<changefreq>", xml, "Google and Bing ignore it")
        self.assertNotIn("<lastmod>", xml, "dates come after the build (eleventy/lastmod.js), from content")
        # the alternates: every pair answers the other, x-default is the English page
        alts = {u.findtext("s:loc", namespaces=NS): {a.get("hreflang"): a.get("href") for a in u.findall("x:link", NS)}
                for u in root.findall("s:url", NS)}
        for loc, a in alts.items():
            with self.subTest(loc):
                self.assertTrue(loc.startswith(BASE + "/"))
                if loc.endswith("/only-en/"):
                    self.assertEqual(a, {}, "no twin, no alternates")
                    continue
                self.assertEqual(set(a), {"en", "es", "x-default"})
                self.assertIn(loc, (a["en"], a["es"]))
                self.assertEqual(a["x-default"], a["en"])
                for lang in ("en", "es"):
                    self.assertEqual(alts[a[lang]], a, "the twin lists the same three")
        self.assertEqual(validate(xml), [])

    def test_noindex_and_sitemap_false_are_both_left_out(self):
        src = (ROOT / "src" / "pages" / "sitemap.11ty.js").read_text(encoding="utf-8")
        self.assertIn("if (p.data?.sitemap === false) continue;", src)   # (tests/test_monthly.py pins it too)
        self.assertIn("if (p.data?.noindex) continue;", src)


# ============================================================================ the [seo] check
def head(title: str | None = "About · Site", desc: str | None = "What we do", canonical: str | None = "", robots: str = "") -> str:
    parts = ["<!doctype html><html><head><meta charset=\"utf-8\">"]
    if title is not None:
        parts.append(f"<title>{title}</title>")
    if desc is not None:
        parts.append(f'<meta name="description" content="{desc}">')
    if robots:
        parts.append(f'<meta name="robots" content="{robots}">')
    if canonical is not None:
        parts.append(f'<link rel="canonical" href="{canonical}">')
    parts.append("</head><body><main><p>x</p></main></body></html>")
    return "".join(parts)


def site(pages: dict[str, str], listed: list[str], base: str = BASE) -> list[dict]:
    """Eleventy's results for these pages ({url: html}) and a sitemap listing `listed`."""
    sm = "<urlset>" + "".join(f"<url><loc>{base}{u}</loc></url>" for u in listed) + "</urlset>"
    out = [{"url": "/sitemap.xml", "outputPath": "_site/sitemap.xml", "content": sm}]
    for u, html in pages.items():
        out.append({"url": u, "outputPath": "_site" + u + ("index.html" if u.endswith("/") else ""), "content": html})
    return out


class SeoCheck(unittest.TestCase):
    def problems(self, results: list[dict]) -> list[str]:
        return run_js(self, r"""
          const C = await imp("eleventy/seo-check.js");
          out(C.seoProblems(input.results, input.base));""", data={"results": results, "base": BASE})

    def clean(self) -> dict[str, str]:
        return {
            "/": head("Home · Site", canonical=f"{BASE}/"),
            "/es/": head("Inicio · Sitio", canonical=f"{BASE}/es/"),
            "/instagram/": head("Instagram · Site", canonical=f"{BASE}/instagram/"),
            "/es/instagram/": head("Instagram · Site", canonical=f"{BASE}/es/instagram/"),   # one title in two languages
            "/share/e1/": head("Event", canonical=f"{BASE}/share/e1/", robots="noindex"),      # a share page: noindex
            "/moved/": head("Moved", canonical=f"{BASE}/offline/", robots="noindex"),           # a redirect stub
            "/404.html": head("Not found", canonical=None, robots="noindex"),
            "/googlef.html": "google-site-verification: googlef.html",
        }

    def test_silent_on_a_clean_site(self):
        long_title = "A very long title " * 8
        pages = {**self.clean(), "/long/": head(long_title, desc="d" * 400, canonical=f"{BASE}/long/")}
        self.assertEqual(self.problems(site(pages, ["/", "/es/", "/instagram/", "/es/instagram/", "/long/"])), [],
                         "never lengths, never one title across languages")

    def test_each_problem(self):
        pages = {**self.clean(),
                 "/a/": head("A", canonical=f"{BASE}/elsewhere/"),
                 "/b/": head("B", canonical=f"{BASE}/b/", robots="max-image-preview:large, noindex"),
                 "/c/": head(None, canonical=f"{BASE}/c/"),
                 "/d/": head("D", desc="", canonical=f"{BASE}/d/"),
                 "/e/": head("Home · Site", canonical=f"{BASE}/e/"),
                 "/es/e/": head("Inicio · Sitio", canonical=f"{BASE}/es/e/"),
                 "/f/": head("F", canonical=f"{BASE}/f/"),
                 "/g/": head("G", canonical=None),
                 "/h/": head("H", canonical=f"{BASE}/h/", robots="max-snippet:-1")}
        listed = ["/", "/es/", "/instagram/", "/es/instagram/", "/a/", "/b/", "/c/", "/d/", "/e/", "/es/e/", "/missing/", "/g/"]
        results = site(pages, listed)
        results[0]["content"] = results[0]["content"].replace("</urlset>", "<url><loc>https://other.test/x/</loc></url></urlset>")
        got = self.problems(results)
        self.assertEqual(got, [
            f'/a/: its canonical is "{BASE}/elsewhere/" — the sitemap lists "{BASE}/a/"',
            "/b/: in the sitemap but marked noindex",
            "/c/: no <title>",
            "/d/: no meta description",
            "/e/: the same <title> as / (\"Home · Site\")",
            "/es/e/: the same <title> as /es/ (\"Inicio · Sitio\")",
            "/missing/: in the sitemap but not built",
            f"/g/: its canonical is missing — the sitemap lists \"{BASE}/g/\"",
            f"the sitemap lists https://other.test/x/, which is not under the site's address {BASE}/",
            "/f/: may be indexed (its own canonical, no noindex) but is not in the sitemap — list it, or give it noindex: true",
            "/h/: may be indexed (its own canonical, no noindex) but is not in the sitemap — list it, or give it noindex: true",
        ])

    def test_only_on_a_whole_build_written_to_disk(self):
        bad = site({"/f/": head("F", canonical=f"{BASE}/f/")}, [])
        r = run_js(self, r"""
          const C = await imp("eleventy/seo-check.js");
          const W = await imp("eleventy/build-warnings.js");
          console.warn = () => {};
          const env = { SITE_URL: input.base };
          const res = {};
          for (const [k, args, e] of [["fs", { outputMode: "fs" }, env], ["json", { outputMode: "json" }, env],
                                      ["incremental", { outputMode: "fs", incremental: true }, env],
                                      ["only", { outputMode: "fs" }, { ...env, ONLY: "about" }]]) {
            W.clearBuildWarnings();
            res[k] = { problems: C.seoCheck({ ...args, results: input.results }, e), warnings: W.buildWarnings() };
          }
          res.address = [C.siteAddress({ SITE_URL: "https://a.test/b//" }), C.siteAddress({}, "no-such-file.yml")];
          out(res);""", data={"results": bad, "base": BASE})
        want = "[seo] /f/: may be indexed (its own canonical, no noindex) but is not in the sitemap — list it, or give it noindex: true"
        self.assertEqual(r["fs"]["warnings"], [want])
        for k in ("json", "incremental", "only"):
            self.assertEqual((r[k]["problems"], r[k]["warnings"]), ([], []), k)
        self.assertEqual(r["address"], ["https://a.test/b", ""])

    def test_a_real_build_of_a_few_pages_passes(self):
        """The real templates (base.njk's head, the event share pages, the sitemap) against the check: a build of a
        few pages (ONLY=) — its sitemap lists them, and every share page is noindex."""
        r = run_js(self, r"""
          process.env.ONLY = "about,sitemap,event-share";
          const os = await import("node:os");
          const { Eleventy } = await import("@11ty/eleventy");
          const C = await imp("eleventy/seo-check.js");
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-seo-"));
          try {
            const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js" });
            const pages = await elev.toJSON();
            const base = C.siteAddress();
            out({ problems: C.seoProblems(pages, base), base,
                  sitemap: (pages.find((p) => p.url === "/sitemap.xml") || {}).content || "",
                  shares: pages.filter((p) => /^\/(es\/)?share\//.test(p.url || "")).length,
                  planted: C.seoProblems([...pages, { url: "/about/x/", outputPath: dir + "/about/x/index.html",
                    content: (pages.find((p) => p.url === "/about/") || {}).content.replace(/href="[^"]*\/about\/"/g, `href="${base}/about/x/"`) }], base) });
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }""", env={"PATH_PREFIX": "/aagrapevine/"})
        self.assertIn(f"<loc>{r['base']}/about/</loc>", r["sitemap"])
        self.assertIn(f"<loc>{r['base']}/es/about/</loc>", r["sitemap"])
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["planted"], ["/about/x/: may be indexed (its own canonical, no noindex) but is not in the sitemap — "
                                        "list it, or give it noindex: true"])

    def test_registered_before_the_summing_up(self):
        cfg = (ROOT / "eleventy.config.js").read_text(encoding="utf-8")
        seo = cfg.index('eleventyConfig.on("eleventy.after", (args) => { seoCheck(args); });')
        lastmod = cfg.index('eleventyConfig.on("eleventy.after", (args) => updateLastmod(args));')
        finish = cfg.index("finishBuild(process.env")
        self.assertLess(seo, finish, "Eleventy calls them in order: the [seo] warnings are in before finishBuild")
        self.assertLess(lastmod, finish)

    def test_a_full_build_lists_a_planted_problem(self):
        """One full build written to disk (as the workflows build), with a page that may be indexed but is not in
        the sitemap: the [seo] warning is in the build's list (BUILD_WARNINGS, written by the summing-up — so the
        check ran before it, and STRICT_BUILD would fail on it: tests/test_build_warnings.py)."""
        listed = Path(tempfile.mkdtemp(prefix="gv-seo-warnings-")) / "warnings.txt"
        self.addCleanup(shutil.rmtree, listed.parent, True)
        planted_in_checkout = ROOT / "_site" / "seo-planted"
        was_there = planted_in_checkout.exists()
        r = run_js(self, r"""
          const os = await import("node:os");
          const { Eleventy } = await import("@11ty/eleventy");
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-seo-build-"));
          try {
            const elev = new Eleventy("src", dir, { quietMode: true, configPath: "eleventy.config.js",
              config(cfg) {
                cfg.addTemplate("seo-planted.njk", "<p>Planted</p>", { layout: "layouts/base.njk", lang: "en", pageKey: "seo-test",
                  title: "Planted page", permalink: "/seo-planted/index.html", sitemap: false });
              } });
            // the output given here wins over eleventy.config.js's dir.output ("_site"), as `--output` does on the
            // command line (Eleventy freezes the directories it was given there; a script's are otherwise replaced
            // by the config's) — so the build goes to the temporary folder, never into the checkout's _site
            elev.directories.freeze();
            try { await elev.write(); out({ ok: true, inDir: fs.existsSync(path.join(dir, "seo-planted", "index.html")) }); }
            catch (e) { out({ ok: false, error: String(e && e.message || e) }); }
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }""",
                   env={"ONLY": "", "STRICT_BUILD": "", "BUILD_WARNINGS": str(listed), "GITHUB_ACTIONS": "", "LASTMOD": "",
                        "PATH_PREFIX": "/aagrapevine/"}, timeout=600)
        want = ("[seo] /seo-planted/: may be indexed (its own canonical, no noindex) but is not in the sitemap — list it, "
                "or give it noindex: true")
        self.assertTrue(r["ok"], r.get("error"))
        self.assertIn(want, listed.read_text(encoding="utf-8").splitlines())
        # (the release review, October 2026: it used to write the whole site into ./_site, so the tests that use a
        # fresh ./_site — test_shop, test_booth_page — ran or skipped depending on the order the suite ran in)
        self.assertTrue(r["inDir"], "the build went to the folder it was given")
        if not was_there:
            self.assertFalse(planted_in_checkout.exists(), "nothing written into the checkout's _site")


# ============================================================================ IndexNow
class KeyFile(unittest.TestCase):
    def test_the_file_the_engines_fetch(self):
        r = run_js(self, r"""
          const m = await imp("src/pages/indexnow-key.11ty.js");
          const at = (key) => { const site = { search_engines: key === undefined ? undefined : { indexnow_key: key } };
                                return { permalink: m.data.permalink({ site }), body: m.render({ site }) }; };
          out({ data: { layout: m.data.layout, ex: m.data.eleventyExcludeFromCollections },
                good: at(" b815257cc8be9517930fd5dc42e22363 "), dash: at("abc-1234"), empty: at(""), none: at(undefined),
                short: at("abc123"), bad: at("abc 1234/../x") });""", needs_modules=False)
        self.assertEqual(r["data"], {"layout": False, "ex": True}, "no page around it, not in the sitemap or the search")
        self.assertEqual(r["good"], {"permalink": "/b815257cc8be9517930fd5dc42e22363.txt", "body": "b815257cc8be9517930fd5dc42e22363"},
                         "at the site's top, holding exactly the key")
        self.assertEqual(r["dash"]["permalink"], "/abc-1234.txt")
        for k in ("empty", "none", "short", "bad"):
            self.assertEqual(r[k], {"permalink": False, "body": ""}, f"{k}: no file — IndexNow is off")


def update_wf() -> dict:
    return yaml.safe_load((WF / "update.yml").read_text(encoding="utf-8"))


class Workflow(unittest.TestCase):
    def setUp(self):
        self.wf = update_wf()
        self.build = self.wf["jobs"]["build-deploy"]
        self.publish = self.wf["jobs"]["publish"]
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-indexnow-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def bash(self, script: str, env: dict, cwd: Path) -> subprocess.CompletedProcess:
        bash = bash_path()
        if not bash or not shutil.which("node"):
            self.skipTest("needs bash and Node.js")
        return subprocess.run([bash, "-c", script], cwd=cwd, env={**os.environ, **env}, capture_output=True, text=True,
                              encoding="utf-8", timeout=120)

    def test_the_wiring(self):
        names = [s.get("name") for s in self.build["steps"]]
        changed = "${{ runner.temp }}/lastmod-changed.json"
        for name in ("Build the website", "Build the website again without the share pictures (only when they could not be made)"):
            with self.subTest(name):
                env = step_of(self.build, name)["env"]
                self.assertEqual((env["LASTMOD"], env["LASTMOD_CHANGED"]), ("1", changed))
                # the store of the last publish, brought back from GitHub's Actions cache before the build
                self.assertEqual(env["LASTMOD_STORE"], ".cache/lastmod/lastmod.json")
        back = step_of(self.build, "Bring back the sitemap dates of the last publish")
        self.assertEqual(back["uses"].split("@")[0], "actions/cache/restore")
        self.assertEqual((back["with"]["path"], back["with"]["restore-keys"], back["continue-on-error"]),
                         (".cache/lastmod", "lastmod-v1-", True))
        self.assertLess(names.index(back["name"]), names.index("Build the website"))
        hand = step_of(self.build, "Hand the sitemap dates to the publish job")
        self.assertEqual((hand["uses"].split("@")[0], hand["with"]["name"], hand["with"]["path"], hand["continue-on-error"]),
                         ("actions/upload-artifact", "lastmod-store", "_site/lastmod.json", True))
        self.assertEqual(step_of(self.build, "Check the build")["env"]["LASTMOD_CHANGED"], changed)
        step = step_of(self.build, "Work out which pages to tell search engines about (IndexNow)")
        self.assertEqual((step["id"], step["continue-on-error"], step["env"]["LASTMOD_CHANGED"]), ("indexnow", True, changed))
        self.assertEqual(names.index(step["name"]), names.index("Check the build") + 1)
        self.assertEqual(names[-1], "Upload the website")
        self.assertEqual(self.build["outputs"]["indexnow"], "${{ steps.indexnow.outputs.payload }}")
        # the Code check never dates the sitemap
        check = yaml.safe_load((WF / "check.yml").read_text(encoding="utf-8"))
        self.assertNotIn("LASTMOD", json.dumps(check))
        tell = step_of(self.publish, "Tell search engines which pages changed (IndexNow)")
        steps = [s.get("name") for s in self.publish["steps"]]
        self.assertEqual(steps.index(tell["name"]), steps.index("Publish to GitHub Pages") + 1)
        self.assertEqual(tell["if"], "${{ steps.deployment.outcome == 'success' && needs.build-deploy.outputs.indexnow != '' }}")
        self.assertIs(tell["continue-on-error"], True)
        self.assertLessEqual(tell["timeout-minutes"], 2)
        self.assertEqual(tell["env"], {"PAYLOAD": "${{ needs.build-deploy.outputs.indexnow }}"}, "the request as data, never as code")
        self.assertIn("https://api.indexnow.org/indexnow", tell["run"])
        self.assertIn("Content-Type: application/json; charset=utf-8", tell["run"])
        # the dates of the site just published are kept for the next run — only once it is live
        fetch = step_of(self.publish, "Fetch the sitemap dates of this site")
        keep = step_of(self.publish, "Keep the sitemap dates for the next run")
        self.assertEqual((fetch["uses"].split("@")[0], fetch["with"]["name"], fetch["with"]["path"], fetch["id"]),
                         ("actions/download-artifact", "lastmod-store", ".cache/lastmod", "store"))
        self.assertEqual(fetch["if"], "${{ steps.deployment.outcome == 'success' }}")
        self.assertEqual(keep["uses"].split("@")[0], "actions/cache/save")
        self.assertEqual(keep["with"], {"path": ".cache/lastmod", "key": "lastmod-v1-${{ github.run_id }}-${{ github.run_attempt }}"})
        self.assertEqual(keep["if"], "${{ steps.deployment.outcome == 'success' && steps.store.outcome == 'success' }}")
        self.assertTrue(fetch["continue-on-error"] and keep["continue-on-error"])

    # ------------------------------------------------------------------ Check the build: the sitemap's dates
    def check(self, changed: dict | None) -> tuple[subprocess.CompletedProcess, str]:
        script = step_of(self.build, "Check the build")["run"]
        site = self.tmp / "site"
        (site / "src" / "assets" / "css").mkdir(parents=True)
        (site / "_site" / "es").mkdir(parents=True)
        (site / "_site" / "assets" / "css").mkdir(parents=True)
        for f in (ROOT / "src" / "assets" / "css").glob("*.css"):
            (site / "src" / "assets" / "css" / f.name).write_text("x", encoding="utf-8")
            (site / "_site" / "assets" / "css" / f.name).write_text("x", encoding="utf-8")
        for f in ("index.html", "es/index.html", "build.json"):
            (site / "_site" / f).write_text("x", encoding="utf-8")
        summary = self.tmp / "summary.md"
        summary.write_text("", encoding="utf-8")
        env = {"GITHUB_STEP_SUMMARY": str(summary), "BUILD_WARNINGS": str(self.tmp / "none.txt")}
        if changed is not None:
            (self.tmp / "changed.json").write_text(json.dumps(changed), encoding="utf-8")
            env["LASTMOD_CHANGED"] = str(self.tmp / "changed.json")
        try:
            return self.bash(script, env, site), summary.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(site, True)

    def test_check_the_build_says_how_many_pages_got_the_builds_date(self):
        urls = [f"{BASE}/p{i}/" for i in range(40)]
        cases = {
            "few": ({"site": BASE, "changed": urls[:4], "total": 90, "dated_now": 4, "previous": "ok", "version_changed": False},
                    "4 of 90 page(s) got this build's date", False),
            "many": ({"site": BASE, "changed": urls, "total": 90, "dated_now": 40, "previous": "ok", "version_changed": False},
                     "40 of 90 page(s) got this build's date", True),
            "new code": ({"site": BASE, "changed": urls, "total": 90, "dated_now": 40, "previous": "ok", "version_changed": True},
                         "40 of 90 page(s)", False),
            "left": ({"site": BASE, "changed": urls[:3], "total": 90, "dated_now": 2, "previous": "ok", "version_changed": False},
                     "2 of 90 page(s) got this build's date (their content changed since the last publish); 1 left the sitemap", False),
            "first": ({"site": BASE, "changed": urls, "total": 90, "dated_now": 90, "previous": "missing", "version_changed": False},
                      "all 90 pages got this build's date: no lastmod.json was published yet", False),
            "error": ({"site": BASE, "changed": [], "total": 90, "dated_now": 0, "previous": "error", "version_changed": False},
                      "no page got a date this time: the lastmod.json of the last publish could not be read", False),
        }
        for name, (changed, said, warns) in cases.items():
            with self.subTest(name):
                r, summary = self.check(changed)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn(f"**Sitemap dates:** {said}", summary)
                self.assertEqual("::warning title=Sitemap dates::" in r.stdout, warns, r.stdout)
        r, summary = self.check(None)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("No sitemap dates in this build", r.stdout)
        self.assertNotIn("Sitemap dates", summary)

    # ------------------------------------------------------------------ the request the build job makes
    def request(self, changed: dict | None, key_files: dict[str, str]) -> tuple[subprocess.CompletedProcess, dict]:
        script = step_of(self.build, "Work out which pages to tell search engines about (IndexNow)")["run"]
        site = self.tmp / "req"
        shutil.rmtree(site, True)
        (site / "_site").mkdir(parents=True)
        (site / "_site" / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        for name, body in key_files.items():
            (site / "_site" / name).write_text(body, encoding="utf-8")
        output = self.tmp / "output.txt"
        output.write_text("", encoding="utf-8")
        env = {"GITHUB_OUTPUT": str(output), "LASTMOD_CHANGED": str(self.tmp / "changed.json")}
        (self.tmp / "changed.json").unlink(missing_ok=True)
        if changed is not None:
            (self.tmp / "changed.json").write_text(json.dumps(changed), encoding="utf-8")
        r = self.bash(script, env, site)
        outputs = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines() if "=" in line)
        return r, outputs

    def test_the_request(self):
        key = "b815257cc8be9517930fd5dc42e22363"
        files = {f"{key}.txt": key}
        changed = {"site": BASE, "changed": [f"{BASE}/", f"{BASE}/about/", f"{BASE}/about/", "https://other.test/x/", f"{BASE}x/"],
                   "total": 90, "dated_now": 2, "previous": "ok", "version_changed": False}
        r, out = self.request(changed, files)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        body = json.loads(out["payload"])
        self.assertEqual(body, {"host": "x.test", "key": key, "keyLocation": f"{BASE}/{key}.txt",
                                "urlList": [f"{BASE}/", f"{BASE}/about/"]}, "only the site's own addresses, each once")
        self.assertIn("2 changed page(s) will be sent", r.stdout)
        for name, (ch, kf, said) in {
            "no change": ({**changed, "changed": []}, files, "no page changed since the last publish"),
            "unreadable live file": ({**changed, "changed": [], "previous": "error"}, files, "could not be read"),
            "no list": (None, files, "this build has no list of changed pages"),
            "no key file": (changed, {}, "the build has no key file"),
            "a file that is not the key": (changed, {f"{key}.txt": "something else"}, "the build has no key file"),
        }.items():
            with self.subTest(name):
                r, out = self.request(ch, kf)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertNotIn("payload", out, "nothing to send")
                self.assertIn(said, r.stdout)

    # ------------------------------------------------------------------ the publish job sends it
    def send(self, code: str, curl_exit: int = 0) -> tuple[subprocess.CompletedProcess, str, dict]:
        tell = step_of(self.publish, "Tell search engines which pages changed (IndexNow)")
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        curl = bin_dir / "curl"
        curl.write_text('#!/bin/bash\nout=""; data=""; url=""\n'
                        'while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; --data-binary) data="$2"; shift 2;;'
                        ' -w|-X|-H|--max-time) shift 2;; -*) shift;; *) url="$1"; shift;; esac; done\n'
                        'cp "${data#@}" "$FAKE_DIR/sent.json"; echo "$url" > "$FAKE_DIR/url.txt"; printf "answer" > "$out"\n'
                        'printf "%s" "$FAKE_CODE"; exit "$FAKE_EXIT"\n', encoding="utf-8", newline="\n")
        curl.chmod(0o755)
        summary = self.tmp / "summary.md"
        summary.write_text("", encoding="utf-8")
        payload = {"host": "x.test", "key": "k" * 32, "keyLocation": f"{BASE}/{'k' * 32}.txt", "urlList": [f"{BASE}/", f"{BASE}/about/"]}
        path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        r = self.bash(tell["run"], {"PATH": path, "PAYLOAD": json.dumps(payload), "RUNNER_TEMP": str(self.tmp),
                                    "GITHUB_STEP_SUMMARY": str(summary), "FAKE_DIR": str(self.tmp), "FAKE_CODE": code,
                                    "FAKE_EXIT": str(curl_exit)}, self.tmp)
        sent = json.loads((self.tmp / "sent.json").read_text(encoding="utf-8"))
        url = (self.tmp / "url.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(url, "https://api.indexnow.org/indexnow")
        return r, summary.read_text(encoding="utf-8"), sent

    def test_the_publish_job_sends_it_and_never_fails(self):
        r, summary, sent = self.send("202")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sent["urlList"], [f"{BASE}/", f"{BASE}/about/"], "the request as the build job made it")
        self.assertIn("HTTP 202: received", summary)
        self.assertNotIn("::warning", r.stdout)
        for code, meaning in (("403", "key not found yet"), ("422", "addresses not matching the host"),
                              ("429", "too many requests"), ("400", "bad request")):
            with self.subTest(code):
                r, summary, _ = self.send(code)
                self.assertEqual(r.returncode, 0, "a refusal never fails the publish")
                self.assertIn(f"HTTP {code}: {meaning}", summary)
                self.assertIn("::warning title=IndexNow::", r.stdout)
        r, summary, _ = self.send("000", curl_exit=28)   # no answer in time
        self.assertEqual(r.returncode, 0)
        self.assertIn("HTTP 000: no answer", summary)


if __name__ == "__main__":
    unittest.main()
