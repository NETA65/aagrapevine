"""scripts/ops/report_issues.py — the issues Website update's "report" job keeps (.github/workflows/update.yml):

  * MorningVerdicts — each morning of status.json quote_days judged as /status/ judges it (freshness.js
                      quoteMorning): met (both quotes in by the goal), missed (the goal passed without both),
                      pending (the goal still ahead); the missed mornings in a row up to the newest decided one.
  * MorningIssue    — "The daily quote missed the morning goal": only while the outside morning alarm is set up
                      (config/site.yml site.morning_alarm), two missed mornings in a row open it, a further one
                      edits it silently, the same mornings again change nothing, the first morning on time closes
                      it with a note.
  * MorningWiring   — the step in update.yml (after the sync's `health`, never failing the run, standard library
                      only after a credential-less sparse checkout of scripts/) and the `health` it reads.
"""
from __future__ import annotations

import ast
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops import report_issues as R  # noqa: E402

WF = ROOT / ".github" / "workflows"


def day(ymd: str, gv: str | None, lv: str | None, goal: str = "11:30") -> dict:
    """One quote_days row: the goal and the quotes as UTC clock times of that day (None = not in)."""
    at = lambda hm: f"{ymd}T{hm}:00Z" if hm else None  # noqa: E731
    return {"day": ymd, "goal_at": at(goal), "gv": at(gv), "lv": at(lv)}


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# the week of the review (November 2026, CST = UTC−6: the 5:30 AM goal is 11:30 UTC) — Nov 24 and 25 late
WEEK = {"goal": "05:30", "days": [
    day("2026-11-25", "14:06", "14:07"),
    day("2026-11-24", "15:22", "15:22"),
    day("2026-11-23", "10:57", "10:57"),
    day("2026-11-22", "09:57", "09:57"),
]}
NOW = utc("2026-11-26T02:46:00Z")       # the evening refresh of Nov 25 (Central)


class FakeGh:
    """A stand-in `gh`: the open issues it lists; every call kept."""

    def __init__(self, issues: list[dict] | None = None):
        self.issues = issues or []
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        if args[:2] == ("issue", "list"):
            return json.dumps(self.issues)
        return ""

    def made(self, what: str) -> list[tuple[str, ...]]:
        return [c for c in self.calls if c[:2] == ("issue", what)]

    @staticmethod
    def arg(call: tuple[str, ...], flag: str) -> str:
        return call[call.index(flag) + 1]


class MorningVerdicts(unittest.TestCase):
    def test_the_week_of_the_review(self):
        v = R.morning_verdicts(WEEK, NOW)
        self.assertEqual([(x["day"], x["state"]) for x in v],
                         [("2026-11-25", "missed"), ("2026-11-24", "missed"), ("2026-11-23", "met"), ("2026-11-22", "met")])
        streak, newest = R.missed_streak(v)
        self.assertEqual([x["day"] for x in streak], ["2026-11-25", "2026-11-24"])
        self.assertEqual(newest["day"], "2026-11-25")

    def test_the_rule_of_the_status_page(self):
        # both by the goal (the later one counts; exactly at the goal is on time) — met
        self.assertEqual(R.morning_verdicts({"days": [day("2026-11-26", "10:00", "11:30")]}, NOW)[0]["state"], "met")
        # one late, or one not in once the goal has passed — missed
        later = utc("2026-11-26T12:00:00Z")
        for gv, lv in (("10:00", "11:31"), ("10:00", None), (None, None)):
            with self.subTest(gv=gv, lv=lv):
                self.assertEqual(R.morning_verdicts({"days": [day("2026-11-26", gv, lv)]}, later)[0]["state"], "missed")
        # before the goal, not both in yet — pending, and skipped by the streak
        early = utc("2026-11-26T09:00:00Z")
        rows = {"days": [day("2026-11-26", "08:50", None), *WEEK["days"]]}
        v = R.morning_verdicts(rows, early)
        self.assertEqual(v[0]["state"], "pending")
        self.assertEqual([x["day"] for x in R.missed_streak(v)[0]], ["2026-11-25", "2026-11-24"])

    def test_odd_input_is_left_out(self):
        for bad in (None, {}, {"days": None}, {"days": "x"}, {"days": [None, {"day": "Nov 25"}, {"day": "2026-11-25"}]}):
            with self.subTest(bad=bad):
                self.assertEqual(R.morning_verdicts(bad, NOW), [])
        self.assertEqual(R.missed_streak([]), ([], None))


class MorningIssue(unittest.TestCase):
    URLS = dict(repo_url="https://github.com/o/r", run_url="https://github.com/o/r/actions/runs/1")

    def report(self, quote_days: dict, issues: list[dict] | None = None, now: datetime = NOW, alarm: bool = True):
        gh = FakeGh(issues)
        msg = R.report_mornings({"quote_days": quote_days, "tz": "America/Chicago", "site": "https://example.org",
                                 "alarm": alarm}, gh, now, **self.URLS)
        return gh, msg

    def test_two_missed_mornings_in_a_row_open_it(self):
        gh, msg = self.report(WEEK)
        create = gh.made("create")
        self.assertEqual(len(create), 1, gh.calls)
        self.assertEqual(gh.arg(create[0], "--title"), R.MORNING_TITLE)
        body = gh.arg(create[0], "--body")
        self.assertIn("**The daily quotes were not on the website by the 5:30 AM goal on 2 mornings in a row** "
                      "(the last: Wed, Nov 25).", body)
        # the mornings, in Central time
        self.assertIn("| Wed, Nov 25 | 5:30 AM CST | 8:06 AM CST | 8:07 AM CST |", body)
        self.assertIn("| Tue, Nov 24 | 5:30 AM CST | 9:22 AM CST | 9:22 AM CST |", body)
        # what to do: the alarm first, the runs, a magazine late at the source
        self.assertIn("**Check the morning alarm** at cron-job.org (README → 10 d", body)
        self.assertIn("**401** means its GitHub key has expired", body)
        self.assertIn("(https://github.com/o/r/actions/workflows/morning.yml)", body)
        self.assertIn("[Status page](https://example.org/status/)", body)
        self.assertTrue(body.endswith("<!-- missed-mornings: 2026-11-24,2026-11-25 -->"))
        self.assertIn("Opened the issue", msg)
        self.assertEqual(gh.made("comment") + gh.made("edit") + gh.made("close"), [])

    def test_no_issue_while_no_morning_alarm_is_set_up(self):
        # config/site.yml site.morning_alarm: false — GitHub's own schedule alone can run late: never an issue
        for rows in (WEEK, {"days": [day("2026-11-26", None, None), *WEEK["days"]]}):
            gh, msg = self.report(rows, alarm=False, now=utc("2026-11-26T20:00:00Z"))
            self.assertEqual([c[:2] for c in gh.calls], [("issue", "list")])
            self.assertIn("no outside morning alarm is set up (config/site.yml site.morning_alarm: false)", msg)
        # an issue left open (the alarm was switched off since) still closes after a good morning
        issue = {"number": 9, "title": R.MORNING_TITLE, "body": "<!-- missed-mornings: 2026-11-24,2026-11-25 -->"}
        gh, _msg = self.report({"days": [day("2026-11-26", "10:31", "10:32"), *WEEK["days"]]}, [issue], alarm=False,
                               now=utc("2026-11-26T12:00:00Z"))
        self.assertEqual(len(gh.made("close")), 1)
        # HEALTH from an older sync, without `alarm`: as without the alarm
        gh = FakeGh()
        R.report_mornings({"quote_days": WEEK}, gh, NOW, **self.URLS)
        self.assertEqual(gh.made("create"), [])

    def test_one_missed_morning_is_not_yet_an_issue(self):
        rows = {"days": [WEEK["days"][0], *WEEK["days"][2:]]}
        gh, msg = self.report(rows)
        self.assertEqual(gh.made("create"), [])
        self.assertIn("no issue yet", msg)

    def test_a_further_missed_morning_edits_it_silently(self):
        issue = {"number": 9, "title": R.MORNING_TITLE, "body": "x <!-- missed-mornings: 2026-11-24,2026-11-25 -->"}
        rows = {"days": [day("2026-11-26", None, None), *WEEK["days"]]}
        gh, msg = self.report(rows, [issue], now=utc("2026-11-26T20:00:00Z"))
        edit = gh.made("edit")
        self.assertEqual(len(edit), 1)
        self.assertEqual(edit[0][2], "9")
        self.assertIn("on 3 mornings in a row", gh.arg(edit[0], "--body"))
        self.assertIn("| Thu, Nov 26 | 5:30 AM CST | not yet | not yet |", gh.arg(edit[0], "--body"))
        self.assertEqual(gh.made("create") + gh.made("comment"), [], "no new issue, no e-mail")
        self.assertIn("Updated issue #9", msg)
        # the same mornings again (the next run of the day): nothing changes
        gh, msg = self.report(WEEK, [issue])
        self.assertEqual(gh.made("edit"), [])
        self.assertIn("already lists these mornings", msg)
        # an open issue stays open (and up to date) after one miss: only a good morning closes it
        gh, _msg = self.report({"days": [WEEK["days"][0], *WEEK["days"][2:]]}, [issue])
        self.assertEqual(len(gh.made("edit")), 1)
        self.assertEqual(gh.made("close"), [])

    def test_the_first_morning_on_time_closes_it(self):
        issue = {"number": 9, "title": R.MORNING_TITLE, "body": "<!-- missed-mornings: 2026-11-24,2026-11-25 -->"}
        rows = {"days": [day("2026-11-26", "10:31", "10:32"), *WEEK["days"]]}
        gh, msg = self.report(rows, [issue], now=utc("2026-11-26T12:00:00Z"))
        close = gh.made("close")
        self.assertEqual(len(close), 1)
        self.assertEqual(close[0][2], "9")
        self.assertEqual(gh.arg(close[0], "--comment"),
                         "The daily quotes of Thu, Nov 26 came in by the goal (4:32 AM CST). Closing automatically "
                         "(https://github.com/o/r/actions/runs/1).")
        self.assertIn("Closed issue #9", msg)
        # nothing open and a good morning: nothing to do
        gh, msg = self.report(rows, now=utc("2026-11-26T12:00:00Z"))
        self.assertEqual([c[:2] for c in gh.calls], [("issue", "list")])
        # the morning still ahead does not close it yet (it is not decided)
        gh, _msg = self.report({"days": [day("2026-11-26", "10:31", None), *WEEK["days"]]}, [issue],
                               now=utc("2026-11-26T11:00:00Z"))
        self.assertEqual(gh.made("close"), [])

    def test_summer_time(self):
        # CDT (UTC−5): the 5:30 AM goal is 10:30 UTC
        rows = {"days": [day("2026-07-02", "12:00", "12:00", goal="10:30"), day("2026-07-01", None, "10:00", goal="10:30")]}
        gh, _msg = self.report(rows, now=utc("2026-07-02T20:00:00Z"))
        body = gh.arg(gh.made("create")[0], "--body")
        self.assertIn("| Thu, Jul 2 | 5:30 AM CDT | 7:00 AM CDT | 7:00 AM CDT |", body)
        self.assertIn("| Wed, Jul 1 | 5:30 AM CDT | not yet | 5:00 AM CDT |", body)

    def test_the_command_line(self):
        gh = FakeGh()
        health = {"quote_days": WEEK, "tz": "America/Chicago", "site": "", "alarm": True}
        env = {"HEALTH": json.dumps(health), "REPO_URL": "https://github.com/o/r", "RUN_URL": "u", "SITE_URL": ""}
        out = io.StringIO()
        with mock.patch.dict("os.environ", env), redirect_stdout(out):
            self.assertEqual(R.main(["mornings"], gh=gh, now=NOW), 0)
        self.assertEqual(len(gh.made("create")), 1)
        self.assertNotIn("[Status page]", gh.arg(gh.made("create")[0], "--body"), "no address: no link")
        # broken or missing HEALTH: a message, never a failure
        for bad in ("{", "", "[]"):
            with self.subTest(health=bad), mock.patch.dict("os.environ", {"HEALTH": bad}), redirect_stdout(io.StringIO()):
                self.assertEqual(R.main(["mornings"], gh=FakeGh(), now=NOW), 0)
        with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(R.main(["nothing"], gh=FakeGh(), now=NOW), 2)

    def test_gh_failure_stops_the_step_with_its_message(self):
        failed = mock.Mock(returncode=1, stdout="", stderr="HTTP 403: Resource not accessible")
        with mock.patch("subprocess.run", return_value=failed):
            with self.assertRaises(SystemExit) as cm:
                R.run_gh("issue", "list")
        self.assertIn("'gh issue list' failed: HTTP 403", str(cm.exception.code))


class MorningWiring(unittest.TestCase):
    def setUp(self):
        self.wf = yaml.safe_load((WF / "update.yml").read_text(encoding="utf-8"))
        self.job = self.wf["jobs"]["report"]

    def step(self, name: str) -> dict:
        return next(s for s in self.job["steps"] if s.get("name") == name)

    def test_the_step(self):
        st = self.step("Open, update or close the issue about missed mornings")
        self.assertEqual(st["run"].strip(), "python3 -m scripts.ops.report_issues mornings")
        self.assertEqual(st["if"], "${{ needs.sync.outputs.health != '' }}")
        self.assertTrue(st["continue-on-error"], "it never fails the run")
        self.assertEqual(st["env"]["HEALTH"], "${{ needs.sync.outputs.health }}")
        self.assertEqual(st["env"]["GH_TOKEN"], "${{ github.token }}")
        # the scripts, without credentials (only the job's token, for gh, in the step's env)
        co = self.step("Check out the report scripts")
        self.assertTrue(co["uses"].startswith("actions/checkout@"))
        self.assertIs(co["with"]["persist-credentials"], False)
        self.assertEqual(co["with"]["sparse-checkout"], "scripts")
        self.assertTrue(co["continue-on-error"])
        self.assertLess(self.job["steps"].index(co), self.job["steps"].index(st))
        self.assertEqual(self.job["permissions"]["contents"], "read")

    def test_standard_library_only(self):
        # the report job installs nothing: the runner's python3 runs the module
        tree = ast.parse((ROOT / "scripts" / "ops" / "report_issues.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for n in names:
                top = n.split(".")[0]
                with self.subTest(module=n):
                    self.assertTrue(top in sys.stdlib_module_names or top == "__future__", n)

    def test_the_health_it_reads(self):
        sync = self.wf["jobs"]["sync"]
        run = next(s for s in sync["steps"] if s.get("name") == "Write run summary")["run"]
        self.assertIn('"quote_days": s.get("quote_days"), "tz": tz, "alarm": alarm}', run)
        self.assertIn('alarm = site_cfg.get("morning_alarm") is True', run)
        self.assertEqual(sync["outputs"]["health"], "${{ steps.summary.outputs.health }}")


if __name__ == "__main__":
    unittest.main()
