"""The tests Website update runs before it publishes (.github/workflows/update.yml, job "tests"; the job "publish"
waits for it): every offline test in tests/ — the Code check's (.github/workflows/check.yml, which only reports on
a change) — so a change that breaks them never goes live; the site keeps the version before.

All but the few in DATA_TESTS: they judge the bot's synced data (data/site) against a fixed expectation, so their
answer can change between two runs without anybody's commit (a video gone from the channel's list, an event title
from another calendar), and a day's data must never keep the site from updating. The Code check still runs them.
A test belongs there only when it reads the synced data AND expects something of it that the data alone can
break; a test of the code on that data (whatever the data says, the page must match it) stays in the gate.

The job runs this only for code and content it has not passed yet (its fingerprint of everything in git but the
bot's own data is remembered in GitHub's Actions cache): the daily data runs — the same code — publish without
running the tests again.

    python -m scripts.ops.gate_tests        # exit 0: every test passed (or was skipped), 1: one failed

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


def each_test(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    """Every test of a (nested) suite, in order."""
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from each_test(t)
        else:
            yield t


def gate_suite(start: Path | None = None) -> tuple[unittest.TestSuite, list[str]]:
    """The tests of `start` (default: tests/; discovered as the Code check does) → (the suite without DATA_TESTS,
    the ids left out)."""
    start = start or TESTS
    found = unittest.TestLoader().discover(str(start), top_level_dir=str(start))
    keep, left = unittest.TestSuite(), []
    for t in each_test(found):
        if t.id() in DATA_TESTS:
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
    else:
        lines.append(f"All {result.testsRun} tests passed ({skipped} skipped) — the website may be published.")
    if left:
        lines += ["", f"Left to the Code check (they judge the day's synced data, not the code): {len(left)}."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.ops.gate_tests", description=__doc__.split("\n\n")[0])
    ap.add_argument("-v", "--verbose", action="store_true", help="name every test as it runs")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    suite, left = gate_suite()
    print(f"Running {suite.countTestCases()} tests ({len(left)} left to the Code check: they judge the day's data).",
          flush=True)
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
    if not result.wasSuccessful():
        print("::error title=Tests failed — not published::Some tests failed, so this run does not publish the "
              "website (the live site keeps the version before). See the run summary.", flush=True)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
