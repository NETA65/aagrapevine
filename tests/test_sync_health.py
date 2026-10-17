"""Website update's run summary ("Write run summary", .github/workflows/update.yml, sync job) — what a source that
loses items, the document search's main pages and the translation set-up look like there, run on stand-in
data/site/status.json and data/raw/pdfs.json files:

  * SyncHealth          — per source, what THIS run added and removed (status.json sources[].changes — common.save_raw,
                          copied by build_data) and the items the mass-drop guard holds back (sources[].held), only
                          rows with something to say; a source this run did not read shows no counts (its row is the
                          last run's), while a hold still shows. A held drop is a warning on the run page.
  * HubPages            — the document search's hub / kit pages that did not load (data/raw/pdfs.json
                          `hub_problems`), only from a search THIS run made that ended normally (a crashed one keeps
                          the last run's list); then the same line is not repeated under "Notes".
  * Notes               — the bulletin's and the events' own warnings are not repeated under "Notes" (they are
                          listed as "… files to fix"), like the writers archive's.
  * TranslationProblems — a translation model that could not be installed (download, checksum) or an unreadable
                          cache: a heading and advice of their own, not "Settings problems … fix the file".

    python -m unittest tests.test_sync_health -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
NOW = datetime.now(timezone.utc).replace(microsecond=0)
STARTED = NOW - timedelta(minutes=30)          # this run started to sync half an hour ago


def iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def src(name: str, label: str, ran: bool = True, changes: dict | None = None, held: dict | None = None,
        ok: bool = True, warnings: list | None = None, **extra) -> dict:
    """A status.json sources[] row; `ran`: this run read it (attempted after STARTED), else yesterday."""
    at = iso(NOW - timedelta(minutes=5) if ran else NOW - timedelta(days=1))
    return {"source": name, "label": label, "ok": ok, "updated": at, "attempted": at, "count": 50, "new_7d": 0,
            "error": None if ok else "boom", "stats": {"warnings": warnings} if warnings else {},
            "changes": changes, "held": held, **extra}


class RunSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wf = yaml.safe_load((WF / "update.yml").read_text(encoding="utf-8"))
        step = next(s for s in wf["jobs"]["sync"]["steps"] if s.get("name") == "Write run summary")
        cls.code = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]

    def summary(self, status: dict, pdfs: dict | None = None, started: datetime | None = STARTED) -> tuple[str, str]:
        """Runs the step's script on this status.json (and data/raw/pdfs.json) → (the summary, what it printed)."""
        tmp = Path(tempfile.mkdtemp(prefix="gv-health-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "data" / "site").mkdir(parents=True)
        (tmp / "data" / "raw").mkdir(parents=True)
        (tmp / "data" / "site" / "status.json").write_text(json.dumps({"fixture": False, **status}), encoding="utf-8")
        if pdfs is not None:
            (tmp / "data" / "raw" / "pdfs.json").write_text(json.dumps(pdfs), encoding="utf-8")
        (tmp / "script.py").write_text(self.code, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in ("ALSO", "ALSO_WHY", "DAILY_MINUTES", "STARTED")}
        env.update(GITHUB_STEP_SUMMARY=str(tmp / "summary.md"), GITHUB_OUTPUT=str(tmp / "out.txt"),
                   PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT), DAILY_MINUTES="40")
        if started:
            env["STARTED"] = iso(started)
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return (tmp / "summary.md").read_text(encoding="utf-8"), r.stdout


class SyncHealth(RunSummary):
    def test_what_each_source_added_and_removed_in_this_run(self):
        status = {"sources": [
            src("youtube", "YouTube videos", changes={"added": 3, "removed": 1, "held": 0}),
            src("podcasts", "Podcasts", changes={"added": 0, "removed": 0, "held": 0}),           # nothing to say
            src("articles", "Magazine stories", ran=False, changes={"added": 9, "removed": 2, "held": 0}),  # last run's
            src("shop", "Store", changes=None)]}
        summary, log = self.summary(status)
        self.assertIn("**Sync health** (what each source added and removed in this run", summary)
        health = summary.split("**Sync health**", 1)[1]
        self.assertIn("| Source | Added | Removed | Held back |\n|---|---:|---:|---|\n| YouTube videos | 3 | 1 |  |\n", health)
        for quiet in ("| Podcasts |", "| Magazine stories |", "| Store |"):
            self.assertNotIn(quiet, health)
        self.assertNotIn("::warning", log)
        # nothing changed anywhere: no section at all
        summary, _log = self.summary({"sources": [src("podcasts", "Podcasts", changes={"added": 0, "removed": 0, "held": 0})]})
        self.assertNotIn("Sync health", summary)
        # without the run's start time (the plan step did not run) no count can be called this run's
        summary, _log = self.summary(status, started=None)
        self.assertNotIn("Sync health", summary)

    def test_items_held_back_after_a_sudden_drop(self):
        since = iso(NOW - timedelta(minutes=4))
        held = {"since": since, "kept": 40, "previous": 100, "found": 60, "drop": True,
                "examples": ["Sobriety at work", "  A new   way  ", "Third | story", "Fourth"]}
        status = {"sources": [
            src("articles", "Magazine stories", changes={"added": 2, "removed": 0, "held": 40}, held=held),
            # Drive kept a folder's files itself (it looked empty): kept, removed only when the next run confirms
            src("drive", "Google Drive", changes={"added": 0, "removed": 0, "held": 3},
                held={"since": since, "kept": 3, "previous": 35, "found": 32, "drop": False, "examples": ["Flyer"]}),
            # a hold from the last run of a source this run did not read: still there, no counts
            src("pdfs", "Documents", ran=False, changes={"added": 1, "removed": 0, "held": 7},
                held={"since": iso(NOW - timedelta(days=1)), "kept": 7, "previous": 140, "found": 133, "drop": True}),
            src("shop", "Book of the Month, prices & specialty items", changes={"added": 0, "removed": 0, "held": 30},
                held={"since": since, "kept": 30, "previous": 62, "found": 32, "drop": True})]}
        summary, log = self.summary(status)
        when = (NOW - timedelta(minutes=4)).strftime("%Y-%m-%d %H:%M")
        self.assertIn(f"| Magazine stories | 2 | 0 | **40 held back** since {when} UTC (found 60 of 100): they stay on "
                      "the site until the next run finds the same — e.g. “Sobriety at work”; “A new way”; “Third / story” |",
                      summary)
        self.assertIn(f"| Google Drive | 0 | 0 | **3 kept** since {when} UTC (found 32 of 35): removed only when the next "
                      "run confirms they are gone — e.g. “Flyer” |", summary)
        self.assertRegex(summary, r"\| Documents \| — \| — \| \*\*7 held back\*\* since [\d-]+ [\d:]+ UTC \(found 133 of 140\)")
        # a warning on the run page, its title escaped (GitHub cuts a title at a comma)
        self.assertIn("::warning title=Magazine stories%3A items held back::40 of 100 item(s) kept on the site although "
                      "this run did not find them", log)
        self.assertIn("::warning title=Documents%3A items held back::7 of 140 item(s) kept on the site although its last "
                      "run did not find them", log)
        self.assertIn("::warning title=Book of the Month%2C prices & specialty items%3A items held back::30 of 62", log)
        self.assertIn("| Book of the Month, prices & specialty items | 0 | 0 | **30 held back**", summary)

    def test_a_removal_the_next_run_confirmed(self):
        status = {"sources": [src("articles", "Magazine stories", changes={
            "added": 0, "removed": 40, "held": 0, "confirmed": iso(NOW - timedelta(days=1))})]}
        summary, log = self.summary(status)
        self.assertRegex(summary, r"\| Magazine stories \| 0 \| 40 \| removal confirmed \(held back since [\d-]+ [\d:]+ UTC\) \|")
        self.assertNotIn("::warning", log)


class HubPages(RunSummary):
    HUBS = [{"url": "https://www.aagrapevine.org/gvr-resources", "status": 404, "since": iso(NOW - timedelta(hours=26))},
            {"url": "https://www.aalavina.org/recursos", "status": "no-response", "since": iso(NOW - timedelta(minutes=9))}]
    NOTE = "2 main page(s) of the magazine sites did not load: aagrapevine.org/gvr-resources (404 since …) — checked again every day"

    def status(self, ok: bool = True) -> dict:
        return {"sources": [src("pdfs", "Documents", ok=ok, warnings=[
            self.NOTE, "robots.txt of www.aalavina.org did not answer properly (no answer): its pages were left for the next run"])]}

    def pdfs(self, attempted: datetime, ok: bool = True) -> dict:
        return {"source": "pdfs", "ok": ok, "attempted": iso(attempted), "updated": iso(attempted), "items": [],
                "hub_problems": self.HUBS}

    def test_this_runs_search(self):
        summary, log = self.summary(self.status(), self.pdfs(NOW - timedelta(minutes=3)))
        since = (NOW - timedelta(hours=26)).strftime("%Y-%m-%d %H:%M")
        self.assertIn("**Main pages of the magazine sites that did not load** (this run's document search; the documents "
                      "they list stay on the site, and each page is tried again every day):\n"
                      f"- aagrapevine.org/gvr-resources — 404 since {since} UTC\n- aalavina.org/recursos — no-response since",
                      summary)
        self.assertIn("::warning title=Document search::2 main page(s) of the magazine sites did not load", log)
        # the same line is not repeated in the notes; the search's other note is
        self.assertNotIn("main page(s) of the magazine sites did not load: aagrapevine.org", summary)
        self.assertIn("- Documents: robots.txt of www.aalavina.org did not answer properly", summary)

    def test_never_an_older_list(self):
        # a search an earlier run made (this one did not search), a crashed search (it keeps the last run's list), no
        # start time: no list — the search's own note stays in the notes
        for what, status, pdfs, started in (
                ("an earlier run's", self.status(), self.pdfs(NOW - timedelta(hours=20)), STARTED),
                ("a crashed search", self.status(ok=True), self.pdfs(NOW - timedelta(minutes=3), ok=False), STARTED),
                ("no start time", self.status(), self.pdfs(NOW - timedelta(minutes=3)), None),
                ("no file", self.status(), None, STARTED)):
            with self.subTest(what):
                summary, log = self.summary(status, pdfs, started)
                self.assertNotIn("Main pages of the magazine sites", summary)
                self.assertNotIn("title=Document search", log)
                self.assertIn("- Documents: " + self.NOTE, summary)


class Notes(RunSummary):
    def test_the_bulletin_and_event_files_are_not_repeated(self):
        bad = "bulletin/p1.md: the publish date 'soon' is not a date (use YYYY-MM-DD)"
        bad_ev = "events/2027-03-14-a.md: it has no start date (add a line 'start: 2027-03-14')"
        status = {"sources": [
            {**src("announcements", "Bulletin (content/bulletin)"), "stats": {"errors": [bad], "warnings": [bad]}},
            {**src("manual_events", "Events (content/events)"), "stats": {"errors": [bad_ev], "warnings": [bad_ev]}},
            src("meetings", "Meeting lists", warnings=["Fort Worth Central Office: feed answered HTTP 503"])]}
        summary, _log = self.summary(status)
        self.assertEqual(summary.count(bad), 1, "under Bulletin files to fix only")
        self.assertEqual(summary.count(bad_ev), 1, "under Event files to fix only")
        self.assertIn("**Bulletin files to fix**", summary)
        self.assertIn("**Notes** (these sources still updated; only look into a note that repeats for a week):\n"
                      "- Meeting lists: Fort Worth Central Office: feed answered HTTP 503", summary)


class TranslationProblems(RunSummary):
    MODEL = ("translation model en_es could not be installed — ModelMismatch: the downloaded package's sha256 "
             "0123456789abcdef… is not the pinned d698d0ef87ad70d5… (MODEL_SHA256 in scripts/sync/translate.py) — not "
             "installed; this direction is not translated until the package is checked and its checksum updated")
    NET = "translation model es_en could not be installed — ConnectionError: argos-net.com did not answer"
    GLOSSARY = ("data/translations/glossary.yml could not be read (YAMLError: bad indent) — new texts stay untranslated "
                "until it is fixed")

    def status(self, file_errors: bool) -> dict:
        tr = [self.MODEL, self.NET]
        return {"sources": [], "translations": {"cached": 3800, "translated_this_run": 0, "pending": 0, "problems": tr},
                "problems": {"translations": " / ".join([*([self.GLOSSARY] if file_errors else []), *tr])}}

    def test_a_model_that_could_not_be_installed_is_no_settings_problem(self):
        summary, log = self.summary(self.status(file_errors=False))
        self.assertNotIn("Settings problems", summary)
        self.assertNotIn("title=Settings problem", log)
        self.assertIn("**Translation problems** (the rest of the site still updated; new titles may stay in their "
                      "original language meanwhile — a model download that failed is simply tried again by the next run, "
                      "a checksum that does not match needs a person to check the new package first):\n"
                      f"- {self.MODEL}\n- {self.NET}\n", summary)
        self.assertIn(f"::warning title=Translation problem::{self.MODEL}", log)
        self.assertIn(f"::warning title=Translation problem::{self.NET}", log)

    def test_next_to_a_glossary_typo(self):
        summary, log = self.summary(self.status(file_errors=True))
        self.assertIn("**Settings problems** (the rest of the site still updated — fix the file and save it again):\n"
                      f"- {self.GLOSSARY}\n", summary, "the typo alone")
        self.assertIn(f"::warning title=Settings problem (translations)::{self.GLOSSARY}\n", log)
        settings = summary.split("**Settings problems**", 1)[1].split("\n\n", 1)[0]
        self.assertNotIn("translation model", settings)
        self.assertIn(f"- {self.MODEL}\n", summary.split("**Translation problems**", 1)[1])
        # an unreadable cache, moved aside: its own line says how to restore it
        cache = ("data/translations/cache.json could not be read (JSONDecodeError: x); it was saved as "
                 "cache.json.bad-20261006T120000Z and the translations are being redone — restore the file from the "
                 "git history to keep them")
        summary, _log = self.summary({"sources": [], "translations": {"problems": [cache]},
                                      "problems": {"translations": cache}})
        self.assertNotIn("Settings problems", summary)
        self.assertIn(f"**Translation problems**", summary)
        self.assertIn(f"- {cache}\n", summary)


if __name__ == "__main__":
    unittest.main()
