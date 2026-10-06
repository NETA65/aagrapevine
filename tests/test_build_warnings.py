"""Build warnings (eleventy/build-warnings.js): a missing icon, a page missing from the sitemap, a link in the
data that had to be repaired or hidden.

  * Each is printed as before ("[icon] missing icon: x", "[sitemap] missing page(s): …", "[links] …") and
    remembered; at the end of the build: STRICT_BUILD=1 fails it, listing them; BUILD_WARNINGS=<file> gets them,
    one per line (empty: none); on GitHub Actions each is an annotation (an error when strict, else a warning).
  * Where they come from: the {% icon %} shortcode and the area sprites ({% micon %} …), the sitemap's required
    pages, src/_data/db.js's link cleaning.
  * The real command line: a strict build with the booth display's expected "not downloaded in this build"
    notes passes; one with a bad link in the data fails (exit code ≠ 0); without STRICT_BUILD it passes and
    writes the list.
  * The workflows: the Code check (check.yml) builds with STRICT_BUILD=1; Website update (update.yml) builds
    without it, hands BUILD_WARNINGS to "Check the build", which lists the warnings in the run's summary and
    still passes. Both "Check the build" steps require every stylesheet — main.css and the page-area ones — and
    fail, naming it, when one is missing (their bash, run here against a stand-in _site).

Skipped without Node.js / the site's npm packages (tests/nodejs.py) or bash.

    python -m unittest tests.test_build_warnings -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nodejs import node_path, run_js  # noqa: E402
from test_morning import bash_path, step_of  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
BOOTH_FIX = "tests/fixtures/booth_csv/"
AREA_SHEETS = ["booth.css", "expenses.css", "monthly.css", "orientation.css", "presentations.css", "report.css"]
SHEETS = sorted(p.name for p in (ROOT / "src" / "assets" / "css").glob("*.css"))   # what the build makes: each one


def workflow(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


# ============================================================================ the module
class Module(unittest.TestCase):
    def test_strict_fails_listing_them_and_the_list_goes_to_the_file(self):
        r = run_js(self, r"""
          const W = await imp("eleventy/build-warnings.js");
          const said = [], logged = [], files = {};
          const warn = console.warn, log = console.log;
          console.warn = (s) => said.push(s); console.log = (s) => logged.push(s);
          const write = (f, t) => { files[f] = t; };
          const res = {};
          try {
            W.buildWarning("icon", "missing icon: nope");
            W.buildWarning("links", "events.json ev:x: url \"www.x.org\" → https://www.x.org");
            res.soFar = W.buildWarnings();
            res.lenient = W.finishBuild({ BUILD_WARNINGS: "w.txt" }, write);
            res.afterLenient = W.buildWarnings();
            W.buildWarning("sitemap", "missing page(s): /offline/, /es/offline/");
            try { W.finishBuild({ STRICT_BUILD: "1", BUILD_WARNINGS: "s.txt", GITHUB_ACTIONS: "true" }, write); res.threw = null; }
            catch (e) { res.threw = e.message; }
            res.annotations = logged.splice(0);
            res.clean = W.finishBuild({ STRICT_BUILD: "1", BUILD_WARNINGS: "c.txt" }, write);   // none: no failure
            W.buildWarning("icon", "missing icon: 100%\nsure");
            res.zero = W.finishBuild({ STRICT_BUILD: "0", GITHUB_ACTIONS: "true" }, write);       // "0" is not strict
            res.annotations2 = logged.splice(0);
          } finally { console.warn = warn; console.log = log; }
          out({ ...res, said, files });""", needs_modules=False)
        self.assertEqual(r["said"][:3], ["[icon] missing icon: nope", '[links] events.json ev:x: url "www.x.org" → https://www.x.org',
                                         "[sitemap] missing page(s): /offline/, /es/offline/"], "printed as before")
        self.assertEqual(r["soFar"], r["said"][:2])
        self.assertEqual(r["lenient"], r["said"][:2], "without STRICT_BUILD: listed, no failure")
        self.assertEqual(r["afterLenient"], [], "a build summed up starts the next one clean")
        self.assertEqual(r["files"]["w.txt"], "\n".join(r["said"][:2]) + "\n")
        self.assertIn("STRICT_BUILD: 1 build warning(s)", r["threw"])
        self.assertIn("[sitemap] missing page(s): /offline/, /es/offline/", r["threw"])
        self.assertEqual(r["files"]["s.txt"], "[sitemap] missing page(s): /offline/, /es/offline/\n", "the list is written before failing")
        self.assertEqual(r["annotations"], ["::error title=Build warning::[sitemap] missing page(s): /offline/, /es/offline/"])
        self.assertEqual((r["clean"], r["files"]["c.txt"]), ([], ""), "no warning: an empty file, no failure")
        self.assertEqual(r["zero"], ["[icon] missing icon: 100%\nsure"])
        self.assertEqual(r["annotations2"], ["::warning title=Build warning::[icon] missing icon: 100%25%0Asure"])


# ============================================================================ where they come from
class Sources(unittest.TestCase):
    def test_sitemap_and_data_links(self):
        tmp = Path(tempfile.mkdtemp(prefix="gv-build-warnings-"))
        try:
            archive = tmp / "writers_archive.json"
            archive.write_text(json.dumps({"updated": None, "items": [
                {"id": "wa:bad", "kind": "article", "title": "Bad", "url": "javascript:alert(1)"},
                {"id": "wa:www", "kind": "article", "title": "Repaired", "url": "www.example.org/story"},
            ]}), encoding="utf-8")
            r = run_js(self, r"""
              const W = await imp("eleventy/build-warnings.js");
              const S = await imp("src/pages/sitemap.11ty.js");
              const D = await imp("src/_data/db.js");
              const warn = console.warn; console.warn = () => {};
              try {
                S.render({ site: { url: "https://x.example/aagrapevine" }, collections: { all: [] } });
                const sitemap = W.buildWarnings(); W.clearBuildWarnings();
                const db = D.default();
                out({ sitemap, links: W.buildWarnings(), kept: db.writers_archive.items.map((i) => i.url) });
              } finally { console.warn = warn; }""", env={"ONLY": "", "WRITERS_ARCHIVE": str(archive)})
        finally:
            shutil.rmtree(tmp, True)
        self.assertEqual(r["sitemap"], ["[sitemap] missing page(s): /, /es/, /whats-new/, /es/whats-new/, /published/, /es/published/, "
                                        "/read/, /es/read/, /monthly/, /es/monthly/, /digest/, /es/digest/, /offline/, /es/offline/"])
        self.assertEqual(r["kept"], ["https://www.example.org/story"])
        self.assertEqual(r["links"][0], "[links] 3 link value(s) in data/site repaired or hidden:")
        self.assertEqual(r["links"][1:], [
            '[links] writers_archive.json wa:bad: url "javascript:alert(1)" is not a usable link — hidden',
            '[links] writers_archive.json wa:www: url "www.example.org/story" → https://www.example.org/story',
            "[links] writers_archive.json wa:bad: left out — its link is not usable"])

    def test_icons_in_a_build(self):
        """An Eleventy build (no files written) of one page with an unknown icon and an icon outside its sprite."""
        tmp = Path(tempfile.mkdtemp(prefix="gv-build-warnings-"))
        listed = tmp / "warnings.txt"
        script = r"""
          process.env.ONLY = "no-page-of-the-site";
          const os = await import("node:os");
          const { Eleventy } = await import("@11ty/eleventy");
          const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gv-build-warnings-"));
          try {
            const elev = new Eleventy("src", dir, {
              quietMode: true, configPath: "eleventy.config.js",
              config(cfg) {
                cfg.addTemplate("warn-test.njk", '<p>{% icon "no-such-icon-anywhere" %}{% icon "calendar-days" %}{% micon "not-in-the-sprite" %}</p>',
                                { permalink: "/warn-test/index.html", sitemap: false, eleventyExcludeFromCollections: true });
              },
            });
            try { const pages = await elev.toJSON(); out({ ok: true, page: (pages.find((p) => p.url === "/warn-test/") || {}).content || "" }); }
            catch (e) { out({ ok: false, error: String(e && e.message || e) }); }
          } finally { fs.rmSync(dir, { recursive: true, force: true }); }"""
        try:
            strict = run_js(self, script, env={"STRICT_BUILD": "1", "BUILD_WARNINGS": str(listed), "GITHUB_ACTIONS": ""})
            strict_list = listed.read_text(encoding="utf-8")
            lenient = run_js(self, script, env={"STRICT_BUILD": "", "BUILD_WARNINGS": str(listed), "GITHUB_ACTIONS": ""})
            lenient_list = listed.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp, True)
        want = ["[icon] missing icon: no-such-icon-anywhere", '[media] micon: "not-in-the-sprite" is not in SPRITE_ICONS']
        self.assertFalse(strict["ok"], "STRICT_BUILD=1 fails the build")
        self.assertIn("STRICT_BUILD: 2 build warning(s)", strict["error"])
        for w in want:
            self.assertIn(w, strict["error"])
        self.assertEqual(strict_list.splitlines(), want)
        self.assertTrue(lenient["ok"], "without STRICT_BUILD the build goes on")
        self.assertIn("<svg", lenient["page"], "the known icon is drawn")
        self.assertEqual(lenient_list.splitlines(), want, "… and the warnings are listed for the run's summary")


# ============================================================================ the real command line
class CommandLine(unittest.TestCase):
    """`eleventy` as the workflows run it (only the sitemap page: ONLY=sitemap), with the booth's video and sound
    files not downloaded (BOOTH_MANIFEST: none) — the Code check's expected notes."""

    def run_build(self, out: Path, **env_extra) -> subprocess.CompletedProcess:
        if not node_path() or not (ROOT / "node_modules" / "@11ty" / "eleventy").is_dir():
            self.skipTest("Node.js or the site's npm packages are missing")
        env = {**os.environ, "PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1", "ONLY": "sitemap", "NODE_NO_WARNINGS": "1",
               "BOOTH_DRIVE": BOOTH_FIX + "drive-booth.json", "BOOTH_MANIFEST": BOOTH_FIX + "no-such-manifest.json",
               "GITHUB_ACTIONS": "", **env_extra}
        for k in ("STRICT_BUILD", "BUILD_WARNINGS", "WRITERS_ARCHIVE"):
            if k not in env_extra:
                env.pop(k, None)
        return subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--output", str(out)],
                              cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)

    def test_strict_passes_with_the_expected_notes_and_fails_on_a_warning(self):
        tmp = Path(tempfile.mkdtemp(prefix="gv-cli-warnings-"))
        try:
            ok = self.run_build(tmp / "a", STRICT_BUILD="1")
            self.assertEqual(ok.returncode, 0, ok.stderr[-3000:])
            self.assertIn("not downloaded in this build", ok.stdout + ok.stderr, "the booth's notes are there …")
            self.assertNotIn("STRICT_BUILD", ok.stdout + ok.stderr, "… and do not count")
            self.assertTrue((tmp / "a" / "sitemap.xml").is_file())

            archive = tmp / "writers_archive.json"
            archive.write_text(json.dumps({"updated": None, "items": [{"id": "wa:bad", "kind": "article", "title": "Bad", "url": "javascript:x"}]}),
                               encoding="utf-8")
            bad = self.run_build(tmp / "b", STRICT_BUILD="1", WRITERS_ARCHIVE=str(archive))
            self.assertNotEqual(bad.returncode, 0, "a build warning fails a strict build")
            self.assertIn("STRICT_BUILD: 3 build warning(s)", bad.stdout + bad.stderr)
            self.assertIn("[links] writers_archive.json wa:bad: left out — its link is not usable", bad.stdout + bad.stderr)

            listed = tmp / "warnings.txt"
            lenient = self.run_build(tmp / "c", WRITERS_ARCHIVE=str(archive), BUILD_WARNINGS=str(listed))
            self.assertEqual(lenient.returncode, 0, lenient.stderr[-3000:])
            self.assertEqual(listed.read_text(encoding="utf-8").splitlines(),
                             ["[links] 2 link value(s) in data/site repaired or hidden:",
                              '[links] writers_archive.json wa:bad: url "javascript:x" is not a usable link — hidden',
                              "[links] writers_archive.json wa:bad: left out — its link is not usable"])
            self.assertFalse((tmp / "c" / "build-warnings.txt").exists(), "the list is never published with the site")
        finally:
            shutil.rmtree(tmp, True)


# ============================================================================ the workflows
class Workflows(unittest.TestCase):
    def test_the_code_check_is_strict_and_website_update_is_not(self):
        check = step_of(workflow("check.yml")["jobs"]["build"], "Build the website (as for GitHub Pages)")
        self.assertEqual(check["env"].get("STRICT_BUILD"), "1")
        self.assertEqual(check["run"].strip(), "npx @11ty/eleventy")
        update = workflow("update.yml")["jobs"]["build-deploy"]
        build = step_of(update, "Build the website")
        self.assertNotIn("STRICT_BUILD", build["env"], "a warning never stops publishing")
        self.assertEqual(build["env"].get("BUILD_WARNINGS"), "${{ runner.temp }}/build-warnings.txt")
        self.assertEqual(step_of(update, "Check the build")["env"].get("BUILD_WARNINGS"), build["env"]["BUILD_WARNINGS"],
                         "Check the build reads the list the build wrote")

    def stand_in_site(self, root: Path, missing: str = "") -> None:
        (root / "src" / "assets" / "css").mkdir(parents=True)
        for f in SHEETS:
            (root / "src" / "assets" / "css" / f).write_text("@import 'x';", encoding="utf-8")
        (root / "_site" / "es").mkdir(parents=True)
        (root / "_site" / "assets" / "css").mkdir(parents=True)
        for f in ("index.html", "es/index.html", "build.json"):
            (root / "_site" / f).write_text("x", encoding="utf-8")
        for f in SHEETS:
            if f != missing:
                (root / "_site" / "assets" / "css" / f).write_text("body{}", encoding="utf-8")

    def run_check(self, wf: str, job: str, missing: str = "", warnings: str | None = None) -> tuple[subprocess.CompletedProcess, str]:
        bash = bash_path()
        if not bash:
            self.skipTest("bash is not installed")
        script = step_of(workflow(wf)["jobs"][job], "Check the build")["run"]
        tmp = Path(tempfile.mkdtemp(prefix="gv-check-build-"))
        try:
            self.stand_in_site(tmp, missing)
            summary = tmp / "summary.md"
            summary.write_text("", encoding="utf-8")
            env = {**os.environ, "GITHUB_STEP_SUMMARY": str(summary), "BUILD_WARNINGS": str(tmp / "warnings.txt")}
            if warnings is not None:
                (tmp / "warnings.txt").write_text(warnings, encoding="utf-8")
            r = subprocess.run([bash, "-c", script], cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
            return r, summary.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp, True)

    def test_check_the_build_requires_every_stylesheet(self):
        for wf, job in (("check.yml", "build"), ("update.yml", "build-deploy")):
            with self.subTest(wf):
                ok, _ = self.run_check(wf, job)
                self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
                for sheet in SHEETS:
                    bad, _ = self.run_check(wf, job, missing=sheet)
                    self.assertEqual(bad.returncode, 1, f"{sheet} missing")
                    self.assertIn(f"::error::The stylesheet {sheet} was not built.", bad.stdout)
        # every stylesheet the site has, the six page-area ones among them
        self.assertLessEqual({"main.css", *AREA_SHEETS}, set(SHEETS), "main.css and the six page-area stylesheets are among them")

    def test_website_update_lists_the_warnings_in_the_summary(self):
        lines = "[icon] missing icon: nope\n[links] events.json ev:x: url \"www.x.org\" → https://www.x.org\n"
        r, summary = self.run_check("update.yml", "build-deploy", warnings=lines)
        self.assertEqual(r.returncode, 0, "a warning never stops publishing")
        self.assertIn("**Build warnings (2)**", summary)
        self.assertIn("~~~~\n" + lines + "~~~~", summary)
        self.assertIn("The build printed 2 warning(s):", r.stdout)
        for none in ("", None):
            with self.subTest(warnings=none):
                r, summary = self.run_check("update.yml", "build-deploy", warnings=none)
                self.assertEqual(r.returncode, 0)
                self.assertNotIn("Build warnings", summary)
                self.assertIn("**Website:**", summary)


if __name__ == "__main__":
    unittest.main()
