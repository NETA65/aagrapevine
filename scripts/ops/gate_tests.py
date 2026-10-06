"""The tests Website update runs before it publishes (.github/workflows/update.yml, job "tests"; the job "publish"
waits for it): every offline test in tests/ — the Code check's (.github/workflows/check.yml, which only reports on
a change) — so a change that breaks them never goes live; the site keeps the version before.

All but the few in DATA_TESTS: they judge the bot's synced data (data/site) against a fixed expectation, so their
answer can change between two runs without anybody's commit (a video gone from the channel's list, an event title
from another calendar), and a day's data must never keep the site from updating. The Code check still runs them.
A test belongs there only when it reads the synced data AND expects something of it that the data alone can
break; a test of the code on that data (whatever the data says, the page must match it) stays in the gate.
The tests in CONTENT_TESTS are left out too: they judge the committee's own files (content/, config/ — an event
date without its year, a booth.csv row, an archive export, a setting nobody reads). The sync and the build already
leave out what they cannot read, so such a slip must never keep the whole site — the morning's new day and quote
included — from updating; the Code check goes red on the push that made it and tells whoever made it.

The job runs this only for code it has not passed yet (its fingerprint of everything in git but the bot's own data
and the committee's content/ and config/ is remembered in GitHub's Actions cache): the daily data runs and the
committee's content and settings changes — the same code — publish without running the tests again.

    python -m scripts.ops.gate_tests        # exit 0: every test passed (or was skipped), 1: one failed (or none found)

It writes what happened to the run summary ($GITHUB_STEP_SUMMARY). Standard library only.
"""
from __future__ import annotations

import argparse
import os
import sys
import unittest
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
# test id (as `python -m unittest discover -s tests` names it) → what it judges
DATA_TESTS: dict[str, str] = {
    "test_booth_csv.Real.test_videos_and_episodes_are_the_official_ones":
        "the booth file's videos and episodes against the day's lists of the channel and the podcasts",
    "test_event_tone.EventToneTest.test_repository_events":
        "the colours of the day's events (data/site/events.json), outside calendars included",
    "test_bulletin.Rendering.test_the_real_post_lists_its_sections":
        "the sections of the day's bulletin posts, Google Drive's included",
    "test_presentations_build.Json.test_a_value_for_every_live_key":
        "the day's weekly open meetings, Book of the Month and story lines in the presentations' live slides",
}

# test id prefix (a class, or one test) → which of the committee's files it judges
CONTENT_TESTS: dict[str, str] = {
    "test_content_events.ContentEvents.":
        "every event file in content/events (a date without its year, an offset that is not Central time …)",
    "test_booth_csv.Real.":
        "content/booth/booth.csv, the booth display's list the committee edits",
    "test_writers_archive.RealFiles.":
        "the owner's archive exports in content/archive",
    "test_settings_used.SettingsAreRead.test_every_setting_in_site_yml_is_read":
        "config/site.yml: a setting the committee added that no code reads yet",
    "test_settings_used.SettingsAreRead.test_every_setting_in_the_other_settings_files_is_read":
        "the other files in config/: a setting the committee added that no code reads yet",
    "test_settings_used.SettingsAreRead.test_the_lists_of_exceptions_are_current":
        "the settings check's exception lists against the settings the committee keeps in config/",
}


def left_to_the_code_check(test_id: str) -> bool:
    """True for the tests the gate leaves to the Code check: DATA_TESTS and CONTENT_TESTS."""
    return test_id in DATA_TESTS or any(test_id.startswith(p) for p in CONTENT_TESTS)


def each_test(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    """Every test of a (nested) suite, in order."""
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from each_test(t)
        else:
            yield t


def gate_suite(start: Path | None = None) -> tuple[unittest.TestSuite, list[str]]:
    """The tests of `start` (default: tests/; discovered as the Code check does) → (the suite without DATA_TESTS and
    CONTENT_TESTS, the ids left out)."""
    start = start or TESTS
    found = unittest.TestLoader().discover(str(start), top_level_dir=str(start))
    keep, left = unittest.TestSuite(), []
    for t in each_test(found):
        if left_to_the_code_check(t.id()):
            left.append(t.id())
        else:
            keep.addTest(t)
    return keep, left


def summary(result: unittest.TestResult, left: list[str]) -> str:
    """The run summary's lines."""
    bad = [t.id() for t, _ in result.failures + result.errors] + [t.id() for t in result.unexpectedSuccesses]
    skipped = len(result.skipped)
    lines = ["### Tests before publishing", ""]
    if bad:
        lines += [f"**{len(bad)} of {result.testsRun} tests failed — the website was NOT published** (the live site "
                  "keeps the version before). Fix the change that broke them, or undo it; the next run publishes. "
                  "The failing tests (the job's log says why):", "", *[f"- `{b}`" for b in bad[:30]]]
        if len(bad) > 30:
            lines.append(f"- … and {len(bad) - 30} more")
    elif not result.testsRun:
        # (as `python -m unittest` since Python 3.12: no test found is no pass)
        lines.append("**No tests were found — the website was NOT published** (the live site keeps the version "
                     "before): the tests/ folder could not be read.")
    else:
        lines.append(f"All {result.testsRun} tests passed ({skipped} skipped) — the website may be published.")
    if left:
        lines += ["", f"Left to the Code check (they judge the day's synced data or the committee's own files, not "
                      f"the code): {len(left)}."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.ops.gate_tests", description=__doc__.split("\n\n")[0])
    ap.add_argument("-v", "--verbose", action="store_true", help="name every test as it runs")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    suite, left = gate_suite()
    print(f"Running {suite.countTestCases()} tests ({len(left)} left to the Code check: they judge the day's data "
          "or the committee's own files).", flush=True)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2 if a.verbose else 1).run(suite)
    text = summary(result, left)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass
    print(text, flush=True)
    ok = result.wasSuccessful() and result.testsRun > 0
    if not ok:
        print("::error title=Tests failed — not published::Some tests failed (or none was found), so this run does "
              "not publish the website (the live site keeps the version before). See the run summary.", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
