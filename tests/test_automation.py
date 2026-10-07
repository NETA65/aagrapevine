"""The automation's safety rails (.github/ and scripts/ops/) — offline: GitHub's `gh` and git are stand-ins, or git
works in a temporary folder.

  * Publishing     — Website update publishes only a site whose code passed the tests: the "tests" job runs them on
                     the very commit the build job builds (the sync job's data commit), only for code it has not
                     passed yet (a fingerprint of everything in git but the bot's own data, the committee's files
                     and the documentation, remembered in the Actions cache — read back by every run that finds it,
                     which keeps it there), and the "publish" job waits for both and checks it is the same commit; a
                     push of the tests alone starts a run;
  * GateTests      — scripts/ops/gate_tests.py: the Code check's tests but the ones that judge the day's synced data,
                     the committee's files or the documentation (DATA_TESTS, CONTENT_TESTS — each one is there), its
                     exit code and its run summary (which failing tests read the committee's files);
  * GateLists      — those lists are complete: every test the gate runs passes again in copies of the repository with
                     the committee's files edited the way the committee edits them (tests/committee_edits.py);
  * FailingUpdates — the "report" job's issue "The website update keeps failing": opened when a run started by the
                     schedule or the Morning check fails right after a failed run, updated (a comment only for a new
                     kind of failure), closed with a note by the next run that works; never for a person's run;
  * LinkCheck      — link-check.yml: the outside link checker runs with a read-only key, pinned to a commit; a job of
                     its own, with no checkout, writes the issue from its reports (it opens, comments, closes);
  * Pinned         — every action from outside GitHub (not actions/…) in every workflow is pinned to a full commit
                     id, with its "# vX.Y.Z";
  * Dependabot     — it watches the Python packages too (new major versions only, one grouped pull request a month;
                     yt-dlp has no cap), and every other package in requirements.txt is capped below its next major;
                     the browser driver pinned in scripts/ops/requirements-browser.txt gets every release.

    python -m unittest tests.test_automation -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_morning import bash_path, run_bash  # noqa: E402
from scripts.ops import gate_tests as G  # noqa: E402

WF = ROOT / ".github" / "workflows"
BOT = "github-actions[bot]"


def load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


def step(job: dict, name: str) -> dict:
    found = [s for s in job.get("steps", []) if s.get("name") == name]
    assert len(found) == 1, f"one step named {name!r}"
    return found[0]


def python_of(run: str) -> str:
    """The Python of a step's `python3 - <<'PY'` … `PY`."""
    return run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


# --------------------------------------------------------------------------- publishing
class Publishing(unittest.TestCase):
    def setUp(self):
        self.wf = load("update.yml")
        self.jobs = self.wf["jobs"]

    def test_the_tests_and_the_build_on_the_same_commit(self):
        sync, tests, build = self.jobs["sync"], self.jobs["tests"], self.jobs["build-deploy"]
        self.assertEqual(sync["outputs"]["commit"], "${{ steps.commit.outputs.commit }}")
        commit = step(sync, "Commit refreshed data")
        self.assertEqual(commit["id"], "commit")
        # whatever way the step ends: the checkout's commit (on GitHub already), or the data commit once pushed
        self.assertIn('published="$(git rev-parse HEAD 2>/dev/null || true)"', commit["run"])
        self.assertIn("""; echo "commit=${published}" >> "$GITHUB_OUTPUT"' EXIT""", commit["run"])
        self.assertRegex(commit["run"], r'if git push origin "HEAD:\$\{BRANCH\}"; then\n\s+published="\$\(git rev-parse HEAD\)"')
        for job in (tests, build):
            with self.subTest(job=job["name"]):
                self.assertEqual(job["needs"], "sync")
                self.assertEqual(job["if"], "${{ !cancelled() && github.ref == 'refs/heads/main' }}",
                                 "also when the sync failed: the site is then published with the last good data")
                checkout = job["steps"][0]
                self.assertTrue(checkout["uses"].startswith("actions/checkout@"))
                self.assertEqual(checkout["with"], {"ref": "${{ needs.sync.outputs.commit || 'main' }}",
                                                    "persist-credentials": False})
                self.assertEqual(job["outputs"]["commit"], "${{ steps.code.outputs.commit }}")
        # the build job builds and uploads; it can no longer publish
        self.assertEqual(build["permissions"], {"contents": "read", "pages": "read"})
        self.assertNotIn("environment", build)
        self.assertFalse([s for s in build["steps"] if "deploy-pages" in str(s.get("uses"))])
        self.assertEqual(build["steps"][-1]["name"], "Upload the website")

    def test_the_commit_step_names_the_commit_to_build(self):
        # run against a repository in a temporary folder whose `origin` is another folder: a run with new data names
        # the data commit it pushed; a run with nothing new, the commit it checked out
        if not shutil.which("git"):
            self.skipTest("needs git")
        bash = bash_path()
        if not bash:
            self.skipTest("needs bash")
        run = step(self.jobs["sync"], "Commit refreshed data")["run"]
        tmp = Path(tempfile.mkdtemp(prefix="gv-commit-out-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "no-settings").write_text("", encoding="utf-8")
        env = {"GIT_CONFIG_GLOBAL": str(tmp / "no-settings"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
               "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "T",
               "GIT_COMMITTER_EMAIL": "t@example.org"}

        def git(cwd: Path, *args: str) -> str:
            r = subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **env}, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.strip()
        git(tmp, "init", "-q", "--bare", "-b", "main", "origin.git")
        repo = tmp / "repo"
        git(tmp, "clone", "-q", (tmp / "origin.git").as_uri(), "repo")
        git(repo, "checkout", "-q", "-b", "main")
        (repo / "data" / "site").mkdir(parents=True)
        (repo / "data" / "site" / "a.json").write_text("{}\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "start")
        git(repo, "push", "-q", "origin", "main")
        start = git(repo, "rev-parse", "HEAD")

        def commit_step() -> str:
            out = tmp / "out.txt"
            out.write_text("", encoding="utf-8")
            r = run_bash(bash, run, {**env, "GITHUB_OUTPUT": str(out), "EVENT": "schedule", "SCHEDULE": "7 12 * * *",
                                     "MODE": "quick", "STARTED": "", "BRANCH": "main", "GH_TOKEN": "x"}, cwd=repo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return dict(ln.split("=", 1) for ln in out.read_text(encoding="utf-8").splitlines() if "=" in ln)["commit"]
        self.assertEqual(commit_step(), start, "nothing new: the checkout")
        (repo / "data" / "site" / "a.json").write_text('{"items": []}\n', encoding="utf-8")
        pushed = commit_step()
        self.assertNotEqual(pushed, start)
        self.assertEqual(pushed, git(tmp / "origin.git", "rev-parse", "main"), "the data commit, on GitHub")
        self.assertIn("chore(data): midday refresh", git(repo, "log", "-1", "--format=%s"))
        left = subprocess.run(["git", "config", "--local", "--get-all", "http.https://github.com/.extraheader"], cwd=repo,
                              env={**os.environ, **env}, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(left.returncode, 0, "the step's log-in is removed again")

    def test_a_push_of_the_tests_alone_starts_a_run(self):
        # the tests decide whether a run publishes (they are part of the code's fingerprint): a fix made only in
        # tests/ is tested and published at once, not at the next timed run — the documentation still starts nothing
        def included(patterns: list[str], path: str) -> bool:
            # GitHub's path filters: the last pattern that matches decides; ** = any folders, * = within one
            got = False
            for p in patterns:
                neg = p.startswith("!")
                rx = re.escape(p[1:] if neg else p).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
                if re.fullmatch(rx, path):
                    got = not neg
            return got
        on = self.wf.get("on", self.wf.get(True))            # (YAML 1.1 reads a bare `on:` as true)
        paths = on["push"]["paths"]
        for f, want in (("tests/test_price_changes.py", True), ("tests/fixtures/booth_csv/x.csv", True),
                        ("tests/README.md", False), ("README.md", False), ("docs/OPERATIONS.md", False),
                        ("how-to/settings.md", False), ("scripts/ops/gate_tests.py", True), ("config/site.yml", True),
                        ("data/site/status.json", False), (".github/workflows/check.yml", False)):
            with self.subTest(file=f):
                self.assertEqual(included(paths, f), want)

    def test_publish_waits_for_both(self):
        pub = self.jobs["publish"]
        self.assertEqual(pub["needs"], ["build-deploy", "tests"])
        self.assertEqual(pub["if"], "${{ !cancelled() && github.ref == 'refs/heads/main' && needs.build-deploy.result == "
                                    "'success' && needs.tests.result == 'success' }}")
        self.assertEqual(pub["permissions"], {"pages": "write", "id-token": "write"})
        self.assertEqual(pub["environment"], {"name": "github-pages", "url": "${{ steps.deployment.outputs.page_url }}"})
        self.assertEqual([s.get("uses", "").split("@")[0] for s in pub["steps"]], ["", "actions/deploy-pages"])
        same = pub["steps"][0]
        self.assertEqual(same["env"], {"BUILT": "${{ needs.build-deploy.outputs.commit }}",
                                       "TESTED": "${{ needs.tests.outputs.commit }}"})
        bash = bash_path()
        if not bash:
            self.skipTest("needs bash")
        for built, tested, ok in (("a" * 40, "a" * 40, True), ("a" * 40, "b" * 40, False), ("", "", False)):
            with self.subTest(built=built[:3], tested=tested[:3]):
                r = run_bash(bash, same["run"], {"BUILT": built, "TESTED": tested})
                self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
                if not ok:
                    self.assertIn("::error title=Not published::", r.stdout)

    def test_the_tests_run_only_for_new_code(self):
        tests = self.jobs["tests"]
        names = [s["name"] for s in tests["steps"]]
        restore = step(tests, "Were these tests passed already?")
        self.assertTrue(restore["uses"].startswith("actions/cache/restore@"))
        # a real restore of the pass's small file, never a mere lookup: reading it back is what counts as using it,
        # so the daily runs keep it in the cache (GitHub deletes a cache unused for 7 days, and the tests would run
        # again unattended, on code that did not change)
        self.assertEqual(restore["with"], {"path": ".cache/tests-passed",
                                           "key": "tests-passed-v1-${{ steps.code.outputs.fingerprint }}"})
        self.assertNotIn("lookup-only", restore["with"])
        said = step(tests, "Say so when they were passed already")
        self.assertEqual(said["if"], "${{ steps.passed.outputs.cache-hit == 'true' }}")
        self.assertIn('echo "The tests passed already for this code (content, settings and the bot\'s data may have '
                      'changed since) — not run again." | tee -a "$GITHUB_STEP_SUMMARY"', said["run"])
        self.assertIn("cat .cache/tests-passed/passed.txt", said["run"])
        save = step(tests, "Save the pass for the next runs")
        self.assertTrue(save["uses"].startswith("actions/cache/save@"))
        self.assertEqual(save["with"]["key"], restore["with"]["key"])
        miss = "${{ steps.passed.outputs.cache-hit != 'true' }}"
        for name in ("Set up Python", "Install Python packages", "Set up Node.js (for the tests that run the site's JavaScript)",
                     "Install site tools", "Run the tests", "Remember that these tests passed", "Save the pass for the next runs"):
            with self.subTest(step=name):
                self.assertEqual(step(tests, name)["if"], miss)
        self.assertEqual(step(tests, "Run the tests")["run"].strip(), "python -m scripts.ops.gate_tests")
        # saved only after the tests passed: the steps between have no always() / failure()
        self.assertLess(names.index("Run the tests"), names.index("Remember that these tests passed"))
        self.assertLess(names.index("Remember that these tests passed"), names.index("Save the pass for the next runs"))
        self.assertTrue(step(tests, "Save the pass for the next runs")["continue-on-error"])

    def test_the_fingerprint_leaves_out_the_bots_data_the_committees_files_and_the_docs(self):
        # the daily data commits (data/raw, data/site, data/state, the translation cache, the thumbnails), the
        # committee's content/, config/, glossary and overrides, and the documentation (README.md and the other *.md
        # at the top, docs/, how-to/) keep it (an edit or a slip there never stops publishing; the Code check reports
        # it); a change of the code, the tests, the workflow, a Markdown page in src/ or data/geo makes a new one
        if not shutil.which("git"):
            self.skipTest("needs git")
        bash = bash_path()
        if not bash:
            self.skipTest("needs bash")
        run = step(self.jobs["tests"], "Fingerprint the code")["run"]
        tmp = Path(tempfile.mkdtemp(prefix="gv-fingerprint-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "no-settings").write_text("", encoding="utf-8")
        repo = tmp / "repo"
        repo.mkdir()
        env = {"GIT_CONFIG_GLOBAL": str(tmp / "no-settings"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "T",
               "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.org"}

        def git(*args: str) -> None:
            r = subprocess.run(["git", *args], cwd=repo, env={**os.environ, **env}, capture_output=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)

        def commit(files: dict[str, str]) -> dict[str, str]:
            for path, text in files.items():
                (repo / path).parent.mkdir(parents=True, exist_ok=True)
                (repo / path).write_text(text, encoding="utf-8", newline="\n")
            git("add", "-A")
            git("commit", "-q", "-m", "x")
            out = tmp / "out.txt"
            out.write_text("", encoding="utf-8")
            r = run_bash(bash, run, {**env, "GITHUB_OUTPUT": str(out)}, cwd=repo)
            self.assertEqual(r.returncode, 0, r.stderr)
            return dict(ln.split("=", 1) for ln in out.read_text(encoding="utf-8").splitlines())
        git("init", "-q")
        first = commit({"scripts/a.py": "a\n", "config/site.yml": "a: 1\n", "data/site/quote.json": "{}\n",
                        "data/geo/texas_places.json": "[]\n", "src/pages/index.njk": "x\n"})
        self.assertRegex(first["fingerprint"], r"^[0-9a-f]{40}$")
        self.assertRegex(first["commit"], r"^[0-9a-f]{40}$")
        for files in ({"data/site/quote.json": '{"items": []}\n'}, {"data/raw/quote.json": "{}\n"},
                      {"data/state/sources-seen.json": "{}\n"}, {"data/translations/cache.json": "{}\n"},
                      {"src/assets/cache/a.webp": "x"}, {"config/site.yml": "a: 2\n"},
                      {"content/bulletin/x.md": "x\n"}, {"content/events/2027-01-10-x.md": "x\n"},
                      {"content/events/README.md": "x\n"}, {"config/presentations/x.yml": "a: 1\n"},
                      {"data/translations/glossary.yml": "keep: [x]\n"}, {"data/translations/overrides.yml": "a: b\n"},
                      {"README.md": "# x\n"}, {"CHANGES.md": "x\n"}, {"docs/OPERATIONS.md": "x\n"},
                      {"how-to/settings.md": "x\n"}):
            with self.subTest(same_code=list(files)[0]):
                got = commit(files)
                self.assertEqual(got["fingerprint"], first["fingerprint"],
                                 "the bot's data, the committee's files or the documentation: the same code")
                self.assertNotEqual(got["commit"], first["commit"])
        last = first["fingerprint"]
        for files in ({"scripts/a.py": "b\n"}, {"data/geo/texas_places.json": "[1]\n"},
                      {"tests/test_x.py": "x\n"}, {".github/workflows/u.yml": "x\n"},
                      {"src/pages/index.njk": "y\n"}, {"src/pages/notes.md": "a Markdown page\n"},
                      {"scripts/README.md": "x\n"}, {"data/translations/other.yml": "a: b\n"},
                      {"src/_i18n/home.json": "{}\n"}):
            with self.subTest(person=list(files)[0]):
                got = commit(files)
                self.assertNotEqual(got["fingerprint"], last)
                last = got["fingerprint"]


# --------------------------------------------------------------------------- the tests before publishing
class GateTests(unittest.TestCase):
    def test_every_data_test_is_there(self):
        # a renamed test would silently come back into the gate: each id must name a test of tests/
        suite, left = G.gate_suite()
        self.assertTrue(set(G.DATA_TESTS) <= set(left))
        for prefix in (*G.CONTENT_TESTS, *G.LIST_CHECKS):   # each names at least one test of tests/
            self.assertTrue(any(i.startswith(prefix) for i in left), prefix)
        self.assertTrue(all(G.left_to_the_code_check(i) for i in left))
        ids = {t.id() for t in G.each_test(suite)}
        self.assertFalse(ids & set(left))
        self.assertFalse([i for i in ids if G.left_to_the_code_check(i)])
        for why in (*G.CONTENT_TESTS.values(), *G.LIST_CHECKS.values()):
            self.assertTrue(why.strip())
        # a prefix names a class ("….Class.") or one test, never a part of a test's name
        for prefix in (*G.CONTENT_TESTS, *G.LIST_CHECKS):
            self.assertTrue(prefix.endswith(".") or prefix in {i.split(" ")[0] for i in left}, prefix)
        self.assertGreater(len(ids), 1000, "the Code check's tests")
        self.assertIn("test_automation.GateTests.test_every_data_test_is_there", ids)
        for why in G.DATA_TESTS.values():
            self.assertTrue(why.strip())

    def make(self, body: str) -> Path:
        d = Path(tempfile.mkdtemp(prefix="gv-gate-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "test_one.py").write_text("import unittest\n\nclass One(unittest.TestCase):\n" + body, encoding="utf-8")
        return d

    def run_main(self, folder: Path, data_tests: dict | None = None) -> tuple[int, str, str]:
        summary = folder / "summary.md"
        with mock.patch.object(G, "TESTS", folder), mock.patch.object(G, "DATA_TESTS", data_tests or {}), \
                mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}), \
                mock.patch.object(sys, "stderr", io.StringIO()), redirect_stdout(io.StringIO()) as out:
            code = G.main([])
        sys.modules.pop("test_one", None)              # (each test's own module of that name)
        return code, out.getvalue(), summary.read_text(encoding="utf-8")

    def test_all_pass(self):
        folder = self.make("    def test_a(self):\n        pass\n\n    @unittest.skip('x')\n    def test_b(self):\n        pass\n")
        code, log, summary = self.run_main(folder)
        self.assertEqual(code, 0)
        self.assertIn("All 2 tests passed (1 skipped) — the website may be published.", summary)
        self.assertNotIn("::error", log)

    def test_one_fails(self):
        folder = self.make("    def test_a(self):\n        pass\n\n    def test_b(self):\n        self.fail('x')\n\n"
                           "    def test_c(self):\n        raise RuntimeError('boom')\n")
        code, log, summary = self.run_main(folder)
        self.assertEqual(code, 1)
        self.assertIn("**2 of 3 tests failed — the website was NOT published**", summary)
        self.assertIn("- `test_one.One.test_b`\n", summary)
        self.assertIn("- `test_one.One.test_c`\n", summary)
        self.assertIn("None of them was seen reading the committee's own files (content/, config/, the glossary or the "
                      "overrides) or the documentation (Python's own reads are seen, not the site's JavaScript's): most "
                      "likely a change to the code broke them. Fix the change, or undo it; the next run publishes (a fix "
                      "made in tests/ starts one too).", summary)
        self.assertIn("::error title=Tests failed — not published::", log)

    def test_a_failing_test_that_read_the_committees_files_is_named(self):
        # a test that read content/, config/, the glossary or the overrides, or the documentation — in the test, in
        # its class's set-up or when its module was imported — is marked: an edit there may be what it found
        # (a repository of the test's own: the real one's files are the committee's)
        root = Path(tempfile.mkdtemp(prefix="gv-gate-root-"))
        self.addCleanup(shutil.rmtree, root, True)
        for rel in ("config/site.yml", "how-to/settings.md"):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("x\n", encoding="utf-8")
        config, docs = (root / "config" / "site.yml").as_posix(), (root / "how-to" / "settings.md").as_posix()
        folder = self.make(f"    def test_a(self):\n        open({config!r}, encoding='utf-8').read()\n        self.fail('x')\n\n"
                           "    def test_b(self):\n        self.fail('y')\n\n"
                           f"    def test_c(self):\n        open({config!r}, encoding='utf-8').read()\n")
        (folder / "test_two.py").write_text(f"import unittest\nfrom pathlib import Path\nDOC = Path({docs!r}).read_text(encoding='utf-8')\n\n"
                                            "class Two(unittest.TestCase):\n    def test_d(self):\n        self.fail('z')\n",
                                            encoding="utf-8")
        with mock.patch.object(G, "ROOT", root):
            code, _log, summary = self.run_main(folder)
        sys.modules.pop("test_two", None)
        self.assertEqual(code, 1)
        self.assertIn("**3 of 4 tests failed — the website was NOT published**", summary)
        self.assertIn("- `test_one.One.test_a` — it read the committee's files: config/site.yml\n", summary)
        self.assertIn("- `test_one.One.test_b`\n", summary)
        self.assertIn("- `test_two.Two.test_d` — it read the committee's files: how-to/settings.md\n", summary)
        self.assertIn("2 of them read the committee's own files or the documentation (named above). If one of those was "
                      "edited since the tests last passed (the Code check went red on that push), the edit can be what "
                      "they found, not a change to the code: fix the file — or, when the test judges that file rather "
                      "than the code, leave the test to the Code check alone (list it in CONTENT_TESTS, "
                      "scripts/ops/gate_tests.py, or give it data of its own). Otherwise, and for the others: fix the "
                      "change that broke them, or undo it. The next run publishes.", summary)
        self.assertNotIn("None of them", summary)

    def test_a_set_up_or_a_subtest_that_read_them_is_named_too(self):
        # a class's set-up that failed, and a subtest, are marked by what their class / test read
        root = Path(tempfile.mkdtemp(prefix="gv-gate-root-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "content").mkdir()
        (root / "content" / "x.md").write_text("x\n", encoding="utf-8")
        content = (root / "content" / "x.md").as_posix()
        folder = self.make("    def test_a(self):\n"
                           f"        open({content!r}, encoding='utf-8').read()\n"
                           "        for n in (1, 2):\n            with self.subTest(n=n):\n                self.assertEqual(n, 1)\n")
        (folder / "test_three.py").write_text(
            "import unittest\n\nclass Three(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n"
            f"        open({content!r}, encoding='utf-8').read()\n        raise RuntimeError('the file')\n\n"
            "    def test_e(self):\n        pass\n", encoding="utf-8")
        with mock.patch.object(G, "ROOT", root):
            code, _log, summary = self.run_main(folder)
        sys.modules.pop("test_three", None)
        self.assertEqual(code, 1)
        self.assertIn("- `test_one.One.test_a (n=2)` — it read the committee's files: content/x.md\n", summary)
        self.assertIn("- `setUpClass (test_three.Three)` — it read the committee's files: content/x.md\n", summary)
        self.assertIn("2 of them read the committee's own files", summary)

    def test_the_name_unittest_loads(self):
        for test_id, want in (("test_x.C.test_a", "test_x.C.test_a"), ("test_x.C.test_a (lang='en')", "test_x.C.test_a"),
                              ("setUpClass (test_x.C)", "test_x.C"), ("tearDownClass (test_x.C)", "test_x.C"),
                              ("setUpModule (test_x)", "test_x"), ("unittest.loader._FailedTest.test_x", "test_x")):
            with self.subTest(test_id=test_id):
                self.assertEqual(G.runnable(test_id), want)

    def test_the_committees_files(self):
        root = G.ROOT
        for path, want in ((root / "config" / "site.yml", "config/site.yml"), (root / "content" / "events" / "x.md", "content/events/x.md"),
                           (root / "data" / "translations" / "glossary.yml", "data/translations/glossary.yml"),
                           (root / "data" / "translations" / "overrides.yml", "data/translations/overrides.yml"),
                           (root / "README.md", "README.md"), (root / "docs" / "OPERATIONS.md", "docs/OPERATIONS.md"),
                           (root / "how-to" / "x.md", "how-to/x.md"),
                           (root / "data" / "translations" / "cache.json", None), (root / "data" / "site" / "x.json", None),
                           (root / "data" / "geo" / "README.md", None), (root / "src" / "pages" / "x.md", None),
                           (root / "scripts" / "x.py", None), (Path(tempfile.gettempdir()) / "config" / "site.yml", None)):
            with self.subTest(path=str(path)):
                self.assertEqual(G.committee_file(path), want)
                self.assertEqual(G.committee_file(str(path)), want)
        self.assertIsNone(G.committee_file(3))                  # an open file's number

    def test_a_data_test_is_left_to_the_code_check(self):
        folder = self.make("    def test_a(self):\n        pass\n\n    def test_data(self):\n        self.fail('the day')\n")
        code, _log, summary = self.run_main(folder, {"test_one.One.test_data": "the day's data"})
        self.assertEqual(code, 0)
        self.assertIn("All 1 tests passed", summary)
        self.assertIn("Left to the Code check (they judge the day's synced data, the committee's own files or the "
                      "documentation, not the code): 1.", summary)

    def test_no_test_found_is_no_pass(self):
        # an empty (or unreadable) tests/ folder must not publish as "all 0 tests passed"
        d = Path(tempfile.mkdtemp(prefix="gv-gate-"))
        self.addCleanup(shutil.rmtree, d, True)
        code, log, summary = self.run_main(d)
        self.assertEqual(code, 1)
        self.assertIn("**No tests were found — the website was NOT published**", summary)
        self.assertIn("::error title=Tests failed — not published::", log)

    def test_a_module_that_cannot_be_imported_fails(self):
        d = Path(tempfile.mkdtemp(prefix="gv-gate-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "test_broken.py").write_text("import no_such_module_here\n", encoding="utf-8")
        code, _log, summary = self.run_main(d)
        self.assertEqual(code, 1)
        self.assertIn("NOT published", summary)


# --------------------------------------------------------------------------- the gate's lists are complete
# The tests the gate runs of one test module (or of a list of tests: a JSON list), in the working folder (a copy of
# the repository, or the repository) → a JSON file.
GATE_MODULE_RUNNER = r"""
import io, json, sys, unittest
sys.path[:0] = [".", "tests"]
names, out = sys.argv[1], sys.argv[2]
names = json.loads(names) if names.startswith("[") else [names]
try:
    from scripts.ops import gate_tests as G
    found = unittest.defaultTestLoader.loadTestsFromNames(names)
    suite = unittest.TestSuite(t for t in G.each_test(found) if not G.left_to_the_code_check(t.id()))
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    bad = [[t.id(), tb] for t, tb in res.failures + res.errors] + [[t.id(), "passed, but expected to fail"] for t in res.unexpectedSuccesses]
    doc = {"run": res.testsRun, "bad": bad}
except BaseException as e:  # noqa: BLE001 — a module that cannot even be loaded is a failure too (of each name)
    doc = {"run": 0, "bad": [[n, f"{type(e).__name__}: {e}"] for n in names]}
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f)
"""


class GateLists(unittest.TestCase):
    """scripts/ops/gate_tests.py's lists are complete: the tests the gate runs test the code, never what the
    committee edits (content/, config/, the glossary and the overrides) or the documentation — those are left out of
    the code's fingerprint, so a test that judged them would fail only later, on somebody else's change of the code,
    and keep every run from publishing until then. Every test the gate runs, once more, in copies of the repository
    with tests/committee_edits.py's edits made (events, posts, the booth file, the archive, settings, the glossary and
    the overrides edited the way the committee edits them, slips made, the documentation deleted): each one must still
    pass (one that fails in the repository itself too is broken anyway: the suite reports it on its own). Minutes of
    work, several copies at once — the Code check runs it, not the gate (LIST_CHECKS)."""

    def test_no_gated_test_judges_the_committees_files(self):
        if not shutil.which("git") or not (ROOT / ".git").exists():
            self.skipTest("needs git and a git checkout (the copy is made of the files git knows)")
        import concurrent.futures
        import queue
        from collections import Counter
        import committee_edits as CE
        suite, _left = G.gate_suite()
        count = Counter(type(t).__module__ for t in G.each_test(suite))     # (a package's too: "browser.test_…")
        modules = sorted(count, key=lambda m: (-count[m], m))           # the big ones first: the copies stay busy
        tmp = Path(tempfile.mkdtemp(prefix="gv-gate-lists-"))
        (tmp / "results").mkdir()
        copies: list[Path] = []
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT")}
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            for i in range(max(1, min(6, os.cpu_count() or 1, len(modules)))):
                copy = tmp / f"copy{i}"
                copy.mkdir()
                CE.copy_repository(ROOT, copy)
                done = CE.apply_committee_edits(copy)
                copies.append(copy)
            # the edits were made (each kind at least once)
            for kind in ("content/events", "content/bulletin", "content/booth", "content/archive", "config/site.yml",
                         "config/history.yml", "config/presentations/", "config/orientation.yml", "config/expenses.yml",
                         "data/translations/glossary.yml", "data/translations/overrides.yml", "README.md deleted",
                         "how-to/ deleted"):
                self.assertTrue(any(d.startswith(kind) for d in done), kind)
            free: queue.Queue = queue.Queue()
            for copy in copies:
                free.put(copy)

            def run(names: str, where: Path | None = None) -> dict:
                copy = where or free.get()
                fd, name = tempfile.mkstemp(suffix=".json", dir=tmp / "results")
                os.close(fd)
                out = Path(name)
                out.unlink()
                try:
                    r = subprocess.run([sys.executable, "-c", GATE_MODULE_RUNNER, names, str(out)], cwd=copy, env=env,
                                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
                finally:
                    if where is None:
                        free.put(copy)
                if not out.is_file():
                    return {"run": 0, "bad": [[names, f"no result (exit code {r.returncode}): {r.stderr[-1500:]}"]]}
                return json.loads(out.read_text(encoding="utf-8"))
            with concurrent.futures.ThreadPoolExecutor(len(copies)) as pool:
                results = list(pool.map(run, modules))
            bad = [b for res in results for b in res["bad"]]
            # a test that fails without the edits too (here, in the repository itself) is broken anyway — the suite
            # says so on its own; only the ones the edits break are this test's business
            # (each failing test, class or module by the name unittest loads — a set-up that failed is its class's or
            # module's, G.runnable —, one module at a time: one that cannot even be imported spoils no other's answer)
            if bad:
                by_module: dict[str, set[str]] = {}
                for b in bad:
                    name = G.runnable(b[0])
                    by_module.setdefault(name.split(".")[0], set()).add(name)
                anyway = {G.runnable(b[0]) for names in by_module.values()
                          for b in run(json.dumps(sorted(names)), ROOT)["bad"]}
                bad = [b for b in bad if G.runnable(b[0]) not in anyway]
        finally:
            for copy in copies:
                CE.remove_copy(copy)
            shutil.rmtree(tmp, ignore_errors=True)
        why = "\n".join(f"- {test_id}: {(tb.strip().splitlines() or ['?'])[-1][:300]}" for test_id, tb in bad[:40])
        self.assertEqual([b[0] for b in bad], [],
                         "\nThese tests of the gate fail once the committee's files are edited (or the documentation "
                         "is gone) — they judge those files, not the code. Give the test data of its own, or move what "
                         "judges the files into a test of its own and list it in CONTENT_TESTS "
                         f"(scripts/ops/gate_tests.py):\n{why}\nThe edits (tests/committee_edits.py):\n- "
                         + "\n- ".join(done))
        self.assertGreater(sum(res["run"] for res in results), 1000, "the gate's tests ran")


# --------------------------------------------------------------------------- failing updates
class FailingUpdates(unittest.TestCase):
    TITLE = "The website update keeps failing"

    def setUp(self):
        job = load("update.yml")["jobs"]["report"]
        self.job = job
        self.step = step(job, "Open, update or close the issue about failing updates")
        self.code = python_of(self.step["run"])

    def run_step(self, results: dict, prev: list[str], event: str = "schedule", actor: str = BOT,
                 issue: dict | None = None) -> tuple[list[list[str]], str]:
        """The step's script against a stand-in `gh`: this run's job results, the conclusions of the earlier runs
        (newest first), an open issue or none → (every gh call, what it printed)."""
        calls: list[list[str]] = []
        runs = [{"id": 900 + i, "conclusion": c, "html_url": f"https://github.com/o/r/actions/runs/{900 + i}"}
                for i, c in enumerate(prev)]
        runs.insert(0, {"id": 1000, "conclusion": None, "status": "in_progress"})       # this run (never "completed")

        def gh(args, **_kw):
            calls.append(list(args))
            out = ""
            if args[1:3] == ["issue", "list"]:
                out = json.dumps([issue] if issue else [])
            elif args[1] == "api":
                out = json.dumps({"workflow_runs": [r for r in runs if r["id"] != 1000 or "status=completed" not in args[2]]})
            return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")
        env = {"EVENT": event, "ACTOR": actor, "RUN_ID": "1000", "RUN_URL": "https://github.com/o/r/actions/runs/1000",
               "REPO_URL": "https://github.com/o/r", **{k: results.get(k, "success") for k in ("SYNC", "TESTS", "BUILD", "PUBLISH")}}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env), mock.patch("subprocess.run", gh), redirect_stdout(out), _ends_well(self):
            exec(compile(self.code, "failing-updates", "exec"), {"__name__": "__main__"})  # noqa: S102 — the step's script
        return calls, out.getvalue()

    @staticmethod
    def made(calls: list[list[str]], what: str) -> list[list[str]]:
        return [c for c in calls if c[1:3] == ["issue", what]]

    def test_the_step(self):
        self.assertEqual(self.job["needs"], ["sync", "tests", "build-deploy", "publish"])
        self.assertEqual(self.job["if"], "${{ !cancelled() && github.ref == 'refs/heads/main' }}")
        self.assertEqual(self.job["permissions"], {"issues": "write", "actions": "read"})
        self.assertTrue(self.step["continue-on-error"], "it never fails the run")
        for k, job in (("SYNC", "sync"), ("TESTS", "tests"), ("BUILD", "build-deploy"), ("PUBLISH", "publish")):
            self.assertEqual(self.step["env"][k], f"${{{{ needs.{job}.result }}}}")
        self.assertEqual(self.step["env"]["ACTOR"], "${{ github.actor }}")
        # the source report runs only when the sync said how the sources are
        self.assertEqual(step(self.job, "Open, update or close the report issue")["if"], "${{ needs.sync.outputs.health != '' }}")

    def test_one_failure_is_not_yet_an_issue(self):
        calls, log = self.run_step({"TESTS": "failure", "PUBLISH": "skipped"}, ["success"])
        self.assertEqual(self.made(calls, "create"), [])
        self.assertIn("no issue yet", log)

    def test_two_failures_in_a_row_open_it(self):
        for event, actor in (("schedule", BOT), ("schedule", "NETA65"), ("workflow_dispatch", BOT)):
            with self.subTest(event=event, actor=actor):
                calls, _log = self.run_step({"TESTS": "failure", "PUBLISH": "skipped"}, ["failure", "success"], event, actor)
                create = self.made(calls, "create")
                self.assertEqual(len(create), 1)
                c = create[0]
                self.assertEqual(c[c.index("--title") + 1], self.TITLE)
                body = c[c.index("--body") + 1]
                self.assertIn("**The website update has failed 2 times in a row.** The last time: [this run]"
                              "(https://github.com/o/r/actions/runs/1000).", body)
                self.assertIn("- **Test the code before publishing** failed: a change to the code broke the tests, so "
                              "nothing was published (the live site keeps the version before): the run summary lists "
                              "the failing tests and says which of them read the committee's own files — fix the "
                              "change or undo it (a fix in tests/ starts a run too).", body)
                self.assertIn("<!-- failing-jobs: tests --> <!-- failures: 2 -->", body)
        # a run replaced in the queue or cancelled does not break the chain; a timed-out one counts as failed
        calls, _log = self.run_step({"PUBLISH": "failure"}, ["cancelled", "timed_out"])
        self.assertEqual(len(self.made(calls, "create")), 1)
        calls, _log = self.run_step({"PUBLISH": "failure"}, ["cancelled", "success", "failure"])
        self.assertEqual(self.made(calls, "create"), [])
        # a job that ran out of time (its timeout-minutes) is "cancelled" in `needs` — the run itself was not (or this
        # job would not run): it failed
        calls, _log = self.run_step({"BUILD": "cancelled", "PUBLISH": "skipped"}, ["failure"])
        create = self.made(calls, "create")
        self.assertEqual(len(create), 1)
        self.assertIn("- **Build website** failed:", create[0][create[0].index("--body") + 1])

    def test_a_persons_run_never_opens_it(self):
        # whoever started it gets GitHub's own e-mail
        for event, actor in (("push", "NETA65"), ("workflow_dispatch", "NETA65")):
            with self.subTest(event=event):
                calls, log = self.run_step({"BUILD": "failure", "PUBLISH": "skipped"}, ["failure"], event, actor)
                self.assertEqual(self.made(calls, "create"), [])
                self.assertIn("started by a person", log)

    def test_an_open_issue_is_updated_and_commented_only_for_a_new_kind_of_failure(self):
        issue = {"number": 7, "title": self.TITLE, "body": "x <!-- failing-jobs: tests --> <!-- failures: 2 -->"}
        calls, _log = self.run_step({"TESTS": "failure", "PUBLISH": "skipped"}, ["failure"], issue=issue)
        edit = self.made(calls, "edit")
        self.assertEqual(len(edit), 1)
        self.assertIn("has failed 3 times in a row", edit[0][edit[0].index("--body") + 1])
        self.assertEqual(self.made(calls, "comment"), [], "the same failure: no e-mail")
        # another job fails now: a comment (GitHub e-mails it); a person's run counts too
        calls, _log = self.run_step({"SYNC": "failure"}, ["failure"], "push", "NETA65", issue=issue)
        comment = self.made(calls, "comment")
        self.assertEqual(len(comment), 1)
        self.assertEqual(comment[0][comment[0].index("--body") + 1],
                         "Now also failing: Sync content + translate (https://github.com/o/r/actions/runs/1000).")
        self.assertEqual(self.made(calls, "create"), [])

    def test_the_next_run_that_works_closes_it(self):
        issue = {"number": 7, "title": self.TITLE, "body": "<!-- failing-jobs: tests --> <!-- failures: 4 -->"}
        calls, log = self.run_step({}, ["failure"], "push", "NETA65", issue=issue)
        close = self.made(calls, "close")
        self.assertEqual(len(close), 1)
        self.assertEqual(close[0][3], "7")
        self.assertIn("The website update works again: this run published the site", close[0][close[0].index("--comment") + 1])
        # nothing open: nothing to do (the runs are not even listed)
        calls, log = self.run_step({}, ["failure"])
        self.assertEqual([c[1] for c in calls], ["issue"])
        self.assertIn("This run worked.", log)
        # published, but the sync failed (the site kept the last good data): not "works again"
        calls, _log = self.run_step({"SYNC": "failure"}, ["success"], issue=None)
        self.assertEqual(self.made(calls, "close"), [])


class _ends_well:
    """The script ends by itself or with SystemExit(0) — anything else fails the test."""

    def __init__(self, case: unittest.TestCase):
        self.case = case

    def __enter__(self):
        return self

    def __exit__(self, kind, exc, tb):
        if kind is SystemExit:
            self.case.assertIn(exc.code, (0, None), exc.code)
            return True
        return False


# --------------------------------------------------------------------------- the weekly link check
class LinkCheck(unittest.TestCase):
    def setUp(self):
        self.text = (WF / "link-check.yml").read_text(encoding="utf-8")
        self.wf = yaml.safe_load(self.text)
        self.jobs = self.wf["jobs"]

    def test_the_link_checker_can_only_read(self):
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        links = self.jobs["links"]
        self.assertEqual(links["permissions"], {"contents": "read"})
        lychee = step(links, "Check links on every page")
        self.assertRegex(lychee["uses"], r"^lycheeverse/lychee-action@[0-9a-f]{40}$")
        self.assertIn(f"uses: {lychee['uses']} # v2.", self.text)
        self.assertEqual(links["outputs"], {"lychee": "${{ steps.lychee.outputs.exit_code }}",
                                            "broken": "${{ steps.official.outputs.broken }}"})
        keep = step(links, "Keep the reports for the issue")
        self.assertEqual((keep["with"]["name"], keep["with"]["path"]), ("link-check-report", "lychee/"))
        self.assertEqual(keep["if"], "${{ !cancelled() }}")

    def test_a_small_job_of_its_own_writes_the_issue(self):
        report = self.jobs["report"]
        self.assertEqual(report["needs"], "links")
        self.assertEqual(report["permissions"], {"issues": "write"})
        self.assertEqual(report["if"], "${{ !cancelled() && needs.links.result == 'success' }}")
        uses = [s.get("uses", "") for s in report["steps"]]
        self.assertEqual([u.split("@")[0] for u in uses if u], ["actions/download-artifact"], "no checkout, no outside code")
        get = report["steps"][0]
        self.assertEqual((get["with"]["name"], get["with"]["path"]), ("link-check-report", "lychee"))
        issue = step(report, "Open, update or close the report issue")
        self.assertEqual(issue["env"]["GH_REPO"], "${{ github.repository }}", "no checkout: gh is told the repository")
        self.assertEqual(issue["env"]["LYCHEE_EXIT"], "${{ needs.links.outputs.lychee }}")
        self.assertEqual(issue["env"]["OFFICIAL_BROKEN"], "${{ needs.links.outputs.broken }}")

    def issue_step(self, lychee: str, broken: str, open_issue: str = "") -> tuple[list[str], str]:
        """The issue step with a stand-in `gh` (a shell function) → (its gh calls, the issue text it wrote)."""
        bash = bash_path()
        if not bash:
            self.skipTest("needs bash")
        run = step(self.jobs["report"], "Open, update or close the report issue")["run"]
        tmp = Path(tempfile.mkdtemp(prefix="gv-links-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "lychee").mkdir()
        (tmp / "lychee" / "out.md").write_text("## lychee\n- [404] https://example.org/gone\n", encoding="utf-8")
        (tmp / "lychee" / "official.md").write_text("## Official links in config/site.yml\n", encoding="utf-8")
        calls = tmp / "calls.txt"
        stub = (f'gh() {{ printf "%s\\n" "$*" >> "{calls.as_posix()}"; '
                f'if [ "$1 $2" = "issue list" ]; then [ -n "{open_issue}" ] && echo "{open_issue}"; fi; return 0; }}\n')
        r = run_bash(bash, stub + run, {"LYCHEE_EXIT": lychee, "OFFICIAL_BROKEN": broken, "ISSUE_TITLE": "Broken links found by the weekly check",
                                        "RUN_URL": "https://github.com/o/r/actions/runs/5", "GH_REPO": "o/r", "GH_TOKEN": "x"}, cwd=tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (tmp / "lychee" / "issue.md").read_text(encoding="utf-8") if (tmp / "lychee" / "issue.md").exists() else ""
        return calls.read_text(encoding="utf-8").splitlines() if calls.exists() else [], text

    def test_the_issue_from_the_reports(self):
        calls, text = self.issue_step("2", "0")
        self.assertTrue(calls[-1].startswith("issue create --title Broken links found by the weekly check --body-file"), calls)
        self.assertIn("https://example.org/gone", text)
        self.assertIn("## Official links in config/site.yml", text)
        calls, _text = self.issue_step("0", "1", open_issue="12")
        self.assertTrue(calls[-1].startswith("issue comment 12 --body-file"), calls)
        calls, _text = self.issue_step("0", "0", open_issue="12")
        self.assertTrue(calls[-1].startswith("issue close 12 --comment All links look good now"), calls)
        calls, _text = self.issue_step("0", "")
        self.assertEqual([c for c in calls if not c.startswith("issue list")], [], "nothing broken, nothing open")


# --------------------------------------------------------------------------- outside actions
class Pinned(unittest.TestCase):
    def test_every_outside_action_is_pinned_to_a_commit(self):
        seen = 0
        for f in sorted(WF.glob("*.yml")):
            for line in f.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)\s*(#.*)?$", line)
                if not m:
                    continue
                action, note = m.group(1), (m.group(2) or "")
                if action.startswith(("actions/", "./")):
                    continue
                seen += 1
                with self.subTest(workflow=f.name, action=action):
                    self.assertRegex(action, r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$", "a full commit id")
                    self.assertRegex(note, r"^# v\d+\.\d+\.\d+$", "its release, for people and Dependabot")
        self.assertGreaterEqual(seen, 1)


# --------------------------------------------------------------------------- Dependabot
class Dependabot(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        every = yaml.safe_load(self.text)["updates"]
        # the repository's own (directory "/"); scripts/ops has the browser checks' Playwright pin
        self.updates = {u["package-ecosystem"]: u for u in every if u["directory"] == "/"}
        self.others = [u for u in every if u["directory"] != "/"]

    def test_the_browser_driver_every_release(self):
        # scripts/ops/requirements-browser.txt pins Playwright: each release (minor and patch too — the runners'
        # Chrome moves on) is a pull request of its own, never the packages of the daily sync
        self.assertEqual([(u["package-ecosystem"], u["directory"]) for u in self.others], [("pip", "/scripts/ops")])
        ops = self.others[0]
        self.assertEqual(ops["allow"], [{"dependency-name": "playwright"}])
        self.assertNotIn("ignore", ops)
        self.assertEqual((ops["schedule"]["interval"], ops["commit-message"]["prefix"]), ("monthly", "chore(deps)"))
        pins = [ln.split("#")[0].strip() for ln in (ROOT / "scripts" / "ops" / "requirements-browser.txt")
                .read_text(encoding="utf-8").splitlines()]
        self.assertIn("playwright", [re.split(r"[<>=!~ ]", p, maxsplit=1)[0].lower() for p in pins if p])
        self.assertTrue(any(re.fullmatch(r"playwright==\d+\.\d+\.\d+", p) for p in pins), "one exact version")
        self.assertNotIn("playwright", (ROOT / "requirements.txt").read_text(encoding="utf-8").lower(),
                         "never a package of the daily sync")

    def test_the_python_packages_new_major_versions_only(self):
        self.assertEqual(set(self.updates), {"github-actions", "npm", "pip"})
        pip = self.updates["pip"]
        self.assertEqual((pip["directory"], pip["schedule"]["interval"]), ("/", "monthly"))
        self.assertEqual(pip["groups"], {"python-packages": {"patterns": ["*"], "update-types": ["major"]}})
        self.assertIn({"dependency-name": "*", "update-types": ["version-update:semver-minor", "version-update:semver-patch"]},
                      pip["ignore"])
        self.assertIn({"dependency-name": "yt-dlp"}, pip["ignore"])
        self.assertEqual(pip["commit-message"]["prefix"], "chore(deps)")
        self.assertNotIn("NOT listed here on purpose", self.text)

    def test_requirements_are_capped_but_yt_dlp(self):
        lines = [ln.split("#")[0].strip() for ln in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()]
        reqs = {re.split(r"[<>=!~ ]", ln, maxsplit=1)[0].lower(): ln for ln in lines if ln}
        self.assertIn("yt-dlp", reqs)
        for name, line in reqs.items():
            with self.subTest(package=name):
                if name == "yt-dlp":
                    self.assertNotIn("<", line, "deliberately unbounded")
                else:
                    self.assertRegex(line, r">=[\d.]+,<\d+$", "capped below its next major version")
        # and the comments say so (they used to call the requirements uncapped)
        update = (WF / "update.yml").read_text(encoding="utf-8")
        self.assertNotIn('requirements.txt uses ">="', update)
        self.assertIn("a new major version waits for Dependabot's monthly pull request", update)


if __name__ == "__main__":
    unittest.main()
