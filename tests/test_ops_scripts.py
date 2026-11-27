"""The scripts that left .github/workflows/update.yml in November 2026 (scripts/ops/run_summary.py,
scripts/ops/sync_steps.py, scripts/ops/report_issues.py sources / updates): the steps call them, and each one does
what the step's inline script did. (The steps' behaviour in detail is tested through the steps: tests/test_morning.py,
tests/test_events_feeds.py, tests/test_sync_health.py, tests/test_automation.py FailingUpdates …)

  * Wiring       — each step runs its module (`python -m scripts.ops.…`), no inline Python is left in update.yml, and
                   the modules use the standard library only where the step installs nothing.
  * ModelKey     — the translation models' cache key: MODEL_URLS' fingerprint, else the whole file's.
  * ArchiveTaken — exit 0 only when this run (STARTED) took in a new writers archive file.
  * QuoteWords   — the morning commit message's words for the quotes, against the last commit.
  * RunSummary   — no status.json / sample data: a note, nothing else; a real one: the summary and `health`.
"""
from __future__ import annotations

import ast
import io
import json
import os
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

from scripts.ops import run_summary, sync_steps  # noqa: E402

WF = ROOT / ".github" / "workflows"


class InFolder(unittest.TestCase):
    """A temporary working folder (the steps read data/ relative to it)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-steps-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        here = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, here)

    def write(self, rel: str, text: str) -> None:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def run_step(self, fn, env: dict | None = None) -> tuple[int | None, str]:
        out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")       # (a step may write bytes: sys.stdout.buffer)
        code = None
        with mock.patch.dict(os.environ, env or {}), redirect_stdout(out):
            try:
                fn()
            except SystemExit as e:
                code = e.code
        out.flush()
        return code, out.buffer.getvalue().decode("utf-8")


class Wiring(unittest.TestCase):
    def setUp(self):
        self.text = (WF / "update.yml").read_text(encoding="utf-8")
        self.jobs = yaml.safe_load(self.text)["jobs"]

    def run_of(self, job: str, name: str) -> str:
        return next(s for s in self.jobs[job]["steps"] if s.get("name") == name)["run"]

    def test_each_step_runs_its_module(self):
        self.assertEqual(self.run_of("sync", "Write run summary").strip(), "python -m scripts.ops.run_summary")
        self.assertIn('fp="$(python -m scripts.ops.sync_steps model-key)"',
                      self.run_of("sync", "Work out the translation-model cache key"))
        commit = self.run_of("sync", "Commit refreshed data")
        self.assertIn('if python -m scripts.ops.sync_steps archive-taken 2>/dev/null; then archive=" + writers archive"; fi',
                      commit)
        self.assertIn('quotes="$(python -m scripts.ops.sync_steps quote-words 2>/dev/null || true)"', commit)
        self.assertEqual(self.run_of("report", "Open, update or close the report issue").strip(),
                         "python3 -m scripts.ops.report_issues sources")
        self.assertEqual(self.run_of("report", "Open, update or close the issue about failing updates").strip(),
                         "python3 -m scripts.ops.report_issues updates")

    def test_no_inline_python_is_left(self):
        self.assertNotIn("<<'PY'", self.text)
        self.assertNotIn("python - <<", self.text)

    def test_standard_library_only_where_nothing_is_installed(self):
        # report_issues runs on the report job's bare python3; sync_steps' model-key runs before the pip install
        for f in ("scripts/ops/report_issues.py", "scripts/ops/sync_steps.py"):
            for node in ast.walk(ast.parse((ROOT / f).read_text(encoding="utf-8"))):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else [])
                for n in names:
                    with self.subTest(file=f, module=n):
                        self.assertTrue(n.split(".")[0] in sys.stdlib_module_names or n == "__future__", n)


class ModelKey(InFolder):
    def test_the_fingerprint_of_model_urls(self):
        here = os.getcwd()
        os.chdir(ROOT)
        try:
            code, out = self.run_step(sync_steps.model_key)
        finally:
            os.chdir(here)
        self.assertIsNone(code)
        self.assertRegex(out.strip(), r"^urls-[0-9a-f]{16}$")
        # the same URLs written another way: the same key; another URL: another key
        self.write("scripts/sync/translate.py", 'MODEL_URLS = {"b": "y", "a": "x"}\n')
        one = self.run_step(sync_steps.model_key)[1]
        self.write("scripts/sync/translate.py", '# a comment\nMODEL_URLS: dict = {"a": "x", "b": "y"}\n')
        self.assertEqual(self.run_step(sync_steps.model_key)[1], one)
        self.write("scripts/sync/translate.py", 'MODEL_URLS = {"a": "x", "b": "z"}\n')
        self.assertNotEqual(self.run_step(sync_steps.model_key)[1], one)
        # no MODEL_URLS: the whole file (safe, less stable)
        self.write("scripts/sync/translate.py", "x = 1\n")
        self.assertRegex(self.run_step(sync_steps.model_key)[1].strip(), r"^file-[0-9a-f]{16}$")


class ArchiveTaken(InFolder):
    def test_only_a_file_this_run_took_in(self):
        started = {"STARTED": "2026-11-25T12:00:00Z"}
        doc = {"stats": {"changed": True}, "files": {"gv": {"imported_at": "2026-11-25T12:05:00Z"}}}
        self.write("data/raw/writers_archive.json", json.dumps(doc))
        self.assertEqual(self.run_step(sync_steps.archive_taken, started)[0], 0)
        for other in ({**doc, "stats": {"changed": False}},
                      {**doc, "files": {"gv": {"imported_at": "2026-11-24T12:00:00Z"}}},   # an earlier run's
                      {"stats": {"changed": True}, "files": {}}):
            with self.subTest(doc=other):
                self.write("data/raw/writers_archive.json", json.dumps(other))
                self.assertEqual(self.run_step(sync_steps.archive_taken, started)[0], 1)
        self.assertEqual(self.run_step(sync_steps.archive_taken, {"STARTED": ""})[0], 1, "no start known")


class QuoteWords(InFolder):
    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.tmp, check=True, capture_output=True)

    def quotes(self, gv: str, lv: str) -> str:
        return json.dumps({"items": [{"pub": "gv", "date": gv}, {"pub": "lv", "date": lv}]})

    def test_the_words_name_the_new_quotes(self):
        if not shutil.which("git"):
            self.skipTest("needs git")
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.org")
        self.git("config", "user.name", "t")
        self.write("data/site/quote.json", self.quotes("2026-11-24", "2026-11-24"))
        self.git("add", ".")
        self.git("commit", "-q", "-m", "x")
        self.write("data/site/quote.json", self.quotes("2026-11-25", "2026-11-25"))
        self.assertEqual(self.run_step(sync_steps.quote_words)[1], " with the daily quotes of Nov 25")
        self.write("data/site/quote.json", self.quotes("2026-11-24", "2026-11-25"))
        self.assertEqual(self.run_step(sync_steps.quote_words)[1], " with the La Viña quote of Nov 25")
        self.write("data/site/quote.json", self.quotes("2026-11-24", "2026-11-24"))
        self.assertEqual(self.run_step(sync_steps.quote_words)[1], "", "no new quote")

    def test_the_command_line(self):
        with mock.patch.object(sys, "argv", ["sync_steps", "nothing"]), mock.patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                sync_steps.main()
        self.assertEqual(cm.exception.code, 2)


class RunSummary(InFolder):
    def test_no_status_or_sample_data(self):
        code, out = self.run_step(run_summary.main, {"GITHUB_STEP_SUMMARY": "", "GITHUB_OUTPUT": ""})
        self.assertEqual(code, 0)
        self.assertIn("No status.json yet", out)
        self.write("data/site/status.json", json.dumps({"fixture": True, "sources": []}))
        code, out = self.run_step(run_summary.main, {"GITHUB_STEP_SUMMARY": "", "GITHUB_OUTPUT": ""})
        self.assertIn("still sample (fixture) data", out)

    def test_a_summary_and_the_health_it_hands_on(self):
        self.write("data/site/status.json", json.dumps({"fixture": False, "sources": [
            {"source": "drive", "label": "Google Drive", "ok": False, "updated": None, "attempted": "2026-11-25T12:00:00Z",
             "error": "403 Forbidden", "count": 0}]}))
        env = {"GITHUB_STEP_SUMMARY": str(self.tmp / "summary.md"), "GITHUB_OUTPUT": str(self.tmp / "out.txt"),
               "ALSO": "", "ALSO_WHY": "", "DAILY_MINUTES": "40", "STARTED": ""}
        code, out = self.run_step(run_summary.main, env)
        self.assertIsNone(code)
        summary = (self.tmp / "summary.md").read_text(encoding="utf-8")
        self.assertIn("## Content sources", summary)
        self.assertIn("| Google Drive | **PROBLEM** |", summary)
        self.assertIn("::warning title=Google Drive::403 Forbidden (previous items kept) — has not worked yet", out)
        health = json.loads((self.tmp / "out.txt").read_text(encoding="utf-8").split("health=", 1)[1])
        self.assertEqual([x["source"] for x in health["stale"]], ["drive"], "never worked: reported")


if __name__ == "__main__":
    unittest.main()
