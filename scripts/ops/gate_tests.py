"""The tests Website update runs before it publishes (.github/workflows/update.yml, job "tests"; the job "publish"
waits for it): the offline tests in tests/ — the Code check's (.github/workflows/check.yml, which only reports on a
change) — that test the CODE, so a change that breaks the code never goes live; the site keeps the version before.

Left out — the Code check still runs them, and goes red on the push that made the problem:

  * DATA_TESTS judge the bot's synced data (data/site) against a fixed expectation, so their answer can change
    between two runs without anybody's commit (a video gone from the channel's list, an event title from another
    calendar). A test belongs there only when it reads the synced data AND expects something of it that the data
    alone can break; a test of the code on that data (whatever the data says, the page must match it) stays here.
  * CONTENT_TESTS judge what the committee edits — content/, config/, data/translations/glossary.yml and
    overrides.yml — or the documentation (README.md, docs/, how-to/, the READMEs in content/ and config/): an
    event date without its year, a booth.csv row, an archive export, a setting nobody reads yet, a post's title as
    written today. The sync and the build already leave out what they cannot read, so nothing the committee edits
    may keep the site — the morning's new day and quote included — from updating, now or later.
  * LIST_CHECKS check these lists themselves (tests/test_automation.py, GateLists: the gate's tests once more, on a
    copy of the repository whose committee files were edited and whose documentation is gone — minutes of work).

"Later" is why the lists must be complete: the job runs this only for code it has not passed yet (a fingerprint of
everything in git but the bot's own data, the committee's files and the documentation is remembered in GitHub's
Actions cache), so the daily data runs, the committee's content and settings changes and documentation edits — the
same code — publish without running the tests again; a test here that judged one of those files would fail only on
the next change of the code, and keep every run from publishing until somebody fixed that file.

When a test fails, the run summary says which failing tests read the committee's files or the documentation (as
far as Python saw them open one): what they found there may be what changed since the tests last passed.

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

# test id prefix (a class, or one test) → which of the committee's files (or which documentation) it judges
CONTENT_TESTS: dict[str, str] = {
    # ---- content/
    "test_content_events.ContentEvents.":
        "every event file in content/events (a date without its year, an offset that is not Central time …)",
    "test_events_feeds.ConfirmedFiles.test_the_real_files":
        "content/events: the workshops the committee confirmed, and the Summer Assembly's venue still to be announced",
    "test_events_feeds.FlyersOnTheEventsPage.test_the_six_workshops_link_their_drive_copies":
        "content/events: the six workshops' flyer: lines (their Drive copies) and the notes above them",
    "test_events_feeds.OnlineAndHybridEvents.test_the_readme_says_the_same":
        "content/events/README.md (documentation): a flyer for a file there gets a name without a date",
    "test_booth_csv.Real.":
        "content/booth/booth.csv, the booth display's list the committee edits",
    "test_booth_page.Strings.test_every_topic_of_the_booth_file_has_its_words":
        "content/booth/booth.csv: each tag has its words in src/_i18n/booth.json",
    "test_writers_archive.RealFiles.":
        "the owner's archive exports in content/archive",
    "test_price_changes.Bulletin.":
        "content/bulletin: the two posts about the January 2027 prices, word for word",
    "test_bulletin.Place.test_the_folder_its_help_and_the_example":
        "content/bulletin: its README and _example.md, the committee's template, as they are",
    "test_bulletin_publish.Header.test_the_template_parses":
        "content/bulletin/_example.md, the committee's template: a valid post that shows publish:",
    # ---- config/
    "test_settings_used.SettingsAreRead.test_every_setting_in_site_yml_is_read":
        "config/site.yml: a setting the committee added that no code reads yet",
    "test_settings_used.SettingsAreRead.test_every_setting_in_the_other_settings_files_is_read":
        "the other files in config/: a setting the committee added that no code reads yet",
    "test_settings_used.SettingsAreRead.test_the_lists_of_exceptions_are_current":
        "the settings check's exception lists against the settings the committee keeps in config/",
    "test_settings_used.ReadsExist.test_every_setting_the_templates_read_is_there":
        "config/site.yml: each setting the templates read without a default is there (one the committee deleted)",
    "test_settings_used.ReadsExist.test_every_setting_the_build_reads_is_there":
        "config/site.yml: each setting the build's JavaScript reads without a default is there",
    "test_settings_used.ReadsExist.test_every_setting_the_sync_reads_is_there":
        "config/site.yml: each setting the sync reads without a default is there",
    "test_site_links.Settings.test_every_link_a_template_reads_exists":
        "config/site.yml links: each link a template reads is there (one the committee deleted)",
    "test_site_links.Settings.test_every_link_in_the_settings_is_used":
        "config/site.yml links: a link the committee added that no page uses yet",
    "test_site_links.SpanishTwins.test_every_twin_in_the_settings_is_shown":
        "config/site.yml links: a Spanish twin the committee added that no page shows yet",
    "test_site_links.Settings.test_settings_that_did_nothing_are_gone":
        "config/site.yml: the settings that did nothing stay out; La Viña's record-your-story page",
    "test_site_links.LaVinaWorkshopName.":
        "config/site.yml and config/presentations: La Viña's monthly workshop under the one name La Viña uses",
    "test_price_changes.Settings.test_the_settings_file_has_no_mistakes":
        "config/site.yml price_changes, as written",
    "test_run_names.OtherTitles.test_the_morning_check_names_its_goal":
        "config/site.yml site.morning_goal against the Morning check's name (morning.yml)",
    "test_spotlight.Gazetteer.test_every_area65_county_is_a_texas_county":
        "config/site.yml spotlight.neta65_counties: each one a Texas county",
    "test_read_media_asides.Listen.test_config_has_the_short":
        "config/site.yml site.listen.sidebar_short (deleting it hides the card)",
    "test_read_media_asides.Watch.test_config_has_the_video":
        "config/site.yml site.watch.hero_video (deleting it hides the card)",
    "test_accessibility.Phone.":
        "config/site.yml phone_access, the meeting ids and the accessibility links, as written",
    "test_pwa_install.Page.test_the_help_links_in_the_settings":
        "config/site.yml links: app_help_* on Apple's and Google's help pages, the Spanish ones in Spanish",
    "test_pwa_install.Wiring.test_nothing_left_of_the_old_page_in_the_docs_settings_and_content":
        "no link to the old app page in config/, content/, docs/ or README.md",
    "test_sync_pipeline.InstagramRetention.test_the_setting_holds_two_months_of_posts":
        "config/site.yml sources.instagram.keep_per_account: two months of posts",
    "test_meetings.Keys.test_config_keys_are_stored_obfuscated_for_their_own_sites":
        "config/site.yml meetings.feeds: the two keyed offices, their keys obfuscated",
    "test_meetings.Settings.test_the_real_config":
        "config/site.yml meetings: the meeting type, the offices' methods and region names",
    "test_editorial.LinkFinder.test_the_settings_name_la_vinas_resources_page":
        "config/site.yml sources.lavina: La Viña's resources page, where its themes document is linked",
    "test_push_modules.Table.test_each_setting_is_in_config":
        "config/site.yml: each setting scripts/ops/push_modules.py names is there",
    "test_orientation.OrientationFileTest.":
        "config/orientation.yml: six sessions, their lengths, questions, placeholders, wording and links",
    "test_orientation.OrientationFactsTest.":
        "config/orientation.yml: the facts the sessions teach",
    "test_history.HistoryFileTest.":
        "config/history.yml: the milestones complete, oldest first, their wording and the official links",
    "test_expenses_page.Config.":
        "config/expenses.yml: ids, types, the standard categories, the default rate",
    "test_presentations.PresentationFiles.test_every_deck":
        "config/presentations: every deck passes the checker",
    "test_presentations.PresentationFiles.test_the_four_decks":
        "config/presentations: the four decks, each with its own order",
    "test_presentations_core.RealDecks.":
        "config/presentations: every text of every slide of the decks",
    "test_presentations_build.Facts.test_the_readme_lists_every_fallback":
        "config/presentations/README.md (the deck writers' guide): every {live:…} key with its fallback",
    # ---- data/translations: the glossary and the overrides
    "test_translate.RealGlossary.":
        "data/translations/glossary.yml and overrides.yml: they can be read, in the right form",
    "test_price_changes.Translations.":
        "data/translations/overrides.yml: the letter's Spanish title, the Drive post's own translation",
    "test_presentations_build.Facts.test_the_committees_english_for_la_vinas_theme":
        "data/translations/overrides.yml: the English the decks print beside La Viña's theme",
    "test_editorial.EnglishWords.":
        "data/translations/overrides.yml: English words for every theme of La Viña's themes document",
}

# test id prefix → what it checks (these lists; slow: the Code check runs them)
LIST_CHECKS: dict[str, str] = {
    "test_automation.GateLists.":
        "these lists are complete: the gate's tests once more, on a copy whose committee files were edited",
}

# What the committee edits, and the documentation (paths in the repository): a test that reads one of them does not
# test the code alone. A folder ends with "/"; "*.md" = the Markdown files at the top.
COMMITTEE_FILES = ("content/", "config/", "data/translations/glossary.yml", "data/translations/overrides.yml",
                   "docs/", "how-to/", "*.md")


def left_to_the_code_check(test_id: str) -> bool:
    """True for the tests the gate leaves to the Code check: DATA_TESTS, CONTENT_TESTS and LIST_CHECKS."""
    return test_id in DATA_TESTS or any(test_id.startswith(p) for p in (*CONTENT_TESTS, *LIST_CHECKS))


def committee_file(path) -> str | None:
    """The repository path ("config/site.yml") of `path` — as a test opened it — when it is one of COMMITTEE_FILES,
    else None."""
    try:
        full = os.path.abspath(os.fsdecode(path))
    except (TypeError, ValueError):
        return None
    root = str(ROOT) + os.sep
    if not os.path.normcase(full).startswith(os.path.normcase(root)):
        return None
    rel = full[len(root):].replace(os.sep, "/")
    key = rel.lower() if os.name == "nt" else rel          # (Windows: names in any case, as COMMITTEE_FILES are)
    for f in COMMITTEE_FILES:
        if f == "*.md":
            if "/" not in key and key.endswith(".md"):
                return rel
        elif key.startswith(f) if f.endswith("/") else key == f:
            return rel
    return None


class Reads:
    """The committee's files (and documents) each test read, as Python's audit hook sees them open (a file the
    site's JavaScript reads in Node.js is not seen): test id → paths; a test module's name → what it read while it
    was imported or set up, outside any test."""

    def __init__(self) -> None:
        self.current: str | None = None
        self.by_test: dict[str, set[str]] = {}
        self.by_module: dict[str, set[str]] = {}

    def of(self, test_id: str) -> list[str]:
        return sorted(self.by_test.get(test_id, set()) | self.by_module.get(test_id.split(".")[0], set()))


_READS: Reads | None = None       # the run being recorded (the hook below stays installed: hooks cannot be removed)
_HOOKED = False
_IN_HOOK = False


def _audit(event: str, args: tuple) -> None:
    global _IN_HOOK
    if _READS is None or _IN_HOOK or event not in ("open", "os.listdir", "os.scandir") or not args:
        return
    _IN_HOOK = True
    try:
        rel = committee_file(args[0]) if isinstance(args[0], (str, bytes, os.PathLike)) else None
        if rel:
            if _READS.current:
                _READS.by_test.setdefault(_READS.current, set()).add(rel)
            else:                                    # a module being imported, a class being set up
                f = sys._getframe(1)
                while f is not None and not os.path.basename(f.f_code.co_filename).startswith("test_"):
                    f = f.f_back
                if f is not None:
                    name = os.path.splitext(os.path.basename(f.f_code.co_filename))[0]
                    _READS.by_module.setdefault(name, set()).add(rel)
    except Exception:  # noqa: BLE001 — the record is a hint: it never fails a test
        pass
    finally:
        _IN_HOOK = False


def record_reads(reads: Reads | None) -> Reads | None:
    """Record the committee's files the tests read into `reads` (None: stop) → the record it replaces."""
    global _READS, _HOOKED
    if not _HOOKED and reads is not None:
        sys.addaudithook(_audit)
        _HOOKED = True
    previous, _READS = _READS, reads
    return previous


class _Result(unittest.TextTestResult):
    """Tells the record which test is running."""

    def startTest(self, test):
        if _READS is not None:
            _READS.current = test.id()
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        if _READS is not None:
            _READS.current = None


def each_test(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    """Every test of a (nested) suite, in order."""
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from each_test(t)
        else:
            yield t


def gate_suite(start: Path | None = None) -> tuple[unittest.TestSuite, list[str]]:
    """The tests of `start` (default: tests/; discovered as the Code check does) → (the suite without the tests
    left to the Code check, the ids left out)."""
    start = start or TESTS
    found = unittest.TestLoader().discover(str(start), top_level_dir=str(start))
    keep, left = unittest.TestSuite(), []
    for t in each_test(found):
        if left_to_the_code_check(t.id()):
            left.append(t.id())
        else:
            keep.addTest(t)
    return keep, left


def summary(result: unittest.TestResult, left: list[str], reads: Reads | None = None) -> str:
    """The run summary's lines."""
    bad = [t.id() for t, _ in result.failures + result.errors] + [t.id() for t in result.unexpectedSuccesses]
    skipped = len(result.skipped)
    lines = ["### Tests before publishing", ""]
    if bad:
        theirs = {b: reads.of(b) for b in bad} if reads else {}
        marked = [b for b in bad if theirs.get(b)]

        def line(b: str) -> str:
            files = theirs.get(b) or []
            more = f" and {len(files) - 3} more" if len(files) > 3 else ""
            return f"- `{b}`" + (f" — it read the committee's files: {', '.join(files[:3])}{more}" if files else "")
        lines += [f"**{len(bad)} of {result.testsRun} tests failed — the website was NOT published** (the live site "
                  "keeps the version before). The failing tests (the job's log says why):", "",
                  *[line(b) for b in bad[:30]]]
        if len(bad) > 30:
            lines.append(f"- … and {len(bad) - 30} more")
        lines.append("")
        if not marked:
            lines.append("None of them read the committee's own files (content/, config/, the glossary or the "
                         "overrides) or the documentation: a change to the code broke them. Fix the change, or undo "
                         "it; the next run publishes (a fix made in tests/ starts one too).")
        else:
            lines.append(f"{len(marked)} of them read the committee's own files or the documentation: an edit there "
                         "since the tests last passed (the Code check went red on it) can be what they found, not a "
                         "change to the code. Such a test judges those files and belongs to the Code check alone "
                         "(scripts/ops/gate_tests.py, CONTENT_TESTS): leave it there, or fix the file. The others: "
                         "fix the change that broke them, or undo it; the next run publishes.")
    elif not result.testsRun:
        # (as `python -m unittest` since Python 3.12: no test found is no pass)
        lines.append("**No tests were found — the website was NOT published** (the live site keeps the version "
                     "before): the tests/ folder could not be read.")
    else:
        lines.append(f"All {result.testsRun} tests passed ({skipped} skipped) — the website may be published.")
    if left:
        lines += ["", f"Left to the Code check (they judge the day's synced data, the committee's own files or the "
                      f"documentation, not the code): {len(left)}."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.ops.gate_tests", description=__doc__.split("\n\n")[0])
    ap.add_argument("-v", "--verbose", action="store_true", help="name every test as it runs")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    reads = Reads()
    before = record_reads(reads)            # (a test of this script runs it inside another run: that one goes on after)
    try:
        suite, left = gate_suite()
        print(f"Running {suite.countTestCases()} tests ({len(left)} left to the Code check: they judge the day's data, "
              "the committee's own files or the documentation).", flush=True)
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2 if a.verbose else 1, resultclass=_Result).run(suite)
    finally:
        record_reads(before)
    text = summary(result, left, reads)
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
