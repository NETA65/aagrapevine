"""The titles of the runs in the Actions list (each workflow's `run-name`), worked out for every kind of run by a
small evaluator of GitHub's expression language — so a title is checked by what it SAYS, not by how it is written:

  * UpdateTitles   — .github/workflows/update.yml: the nightly full update, the midday and evening refreshes (and
                     any other schedule), the morning refresh — always scripts/ops/morning_check.py's MORNING_TITLE,
                     whoever starts it, and no other run's —, the full update the Morning check starts, the ones
                     started by hand; a push keeps GitHub's own title. (tests/test_morning.py checks that each
                     title agrees with what "Decide what to sync" does with the same run.);
  * OtherTitles    — the Morning check, the monthly e-mail digest (its title says what its first step decides),
                     the weekly link check, the Code check (and its build job's name); the workflows' own names
                     (the Morning check's says site.morning_goal);
  * Expressions    — every ${{ … }} (and every `if:`) in every workflow is a well-formed expression, and the
                     steps and jobs it names are there (an earlier step of the same job; a job it needs).

The evaluator: 'strings' ('' inside one is a quote), true / false / null / numbers, github.… / inputs.… / steps.…
(a missing one is null), ! == != && || ( ) and calls; `format()` is evaluated, any other function only parsed. As in
GitHub: && and || give one of their operands (`a && 'x' || b`); false, 0, '' and null are false; strings compare
ignoring case; values of two different kinds are compared as numbers (null == '' is true).

    python -m unittest tests.test_run_names -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import math
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.ops import morning_check as MC  # noqa: E402

WF = ROOT / ".github" / "workflows"
BOT = "github-actions[bot]"


# --------------------------------------------------------------------------- the evaluator
TOKEN = re.compile(r"""\s*(?:(?P<str>'(?:[^']|'')*')|(?P<num>\d+(?:\.\d+)?)|(?P<op>==|!=|<=|>=|&&|\|\||[!()<>,])
                    |(?P<name>[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_*][A-Za-z0-9_-]*)*))""", re.X)


def tokens(text: str) -> list[tuple[str, Any]]:
    out, i = [], 0
    while i < len(text):
        if text[i:].strip() == "":
            break
        m = TOKEN.match(text, i)
        if not m or m.end() == i:
            raise SyntaxError(f"cannot read the expression at {text[i:i + 30]!r}")
        kind = m.lastgroup
        v = m.group(kind)
        out.append((kind, v[1:-1].replace("''", "'") if kind == "str" else float(v) if kind == "num" else v))
        i = m.end()
    return out


def truthy(v: Any) -> bool:
    return not (v is None or v is False or v == "" or (isinstance(v, (int, float)) and not isinstance(v, bool)
                                                        and (v == 0 or math.isnan(v))))


def number(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return math.nan


def equal(a: Any, b: Any) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.lower() == b.lower()
    if type(a) is type(b) and not isinstance(a, (int, float)):
        return a == b
    x, y = number(a), number(b)
    return not (math.isnan(x) or math.isnan(y)) and x == y


def text_of(v: Any) -> str:
    return "" if v is None else ("true" if v else "false") if isinstance(v, bool) else str(v)


class Expr:
    """One expression (without its ${{ }}) → .value(context). Parsing alone checks it is well formed."""

    def __init__(self, text: str):
        self.t, self.i = tokens(text), 0
        self.tree = self.or_()
        if self.i != len(self.t):
            raise SyntaxError(f"unexpected {self.t[self.i][1]!r} in {text!r}")

    def peek(self) -> tuple[str, Any] | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, op: str | None = None) -> tuple[str, Any]:
        tok = self.peek()
        if tok is None or (op is not None and tok != ("op", op)):
            raise SyntaxError(f"expected {op or 'more'}, found {tok}")
        self.i += 1
        return tok

    def or_(self):
        node = self.and_()
        while self.peek() == ("op", "||"):
            self.take()
            node = ("or", node, self.and_())
        return node

    def and_(self):
        node = self.cmp()
        while self.peek() == ("op", "&&"):
            self.take()
            node = ("and", node, self.cmp())
        return node

    def cmp(self):
        node = self.unary()
        while self.peek() in (("op", "=="), ("op", "!="), ("op", "<"), ("op", ">"), ("op", "<="), ("op", ">=")):
            node = (self.take()[1], node, self.unary())
        return node

    def unary(self):
        if self.peek() == ("op", "!"):
            self.take()
            return ("not", self.unary())
        return self.primary()

    def primary(self):
        kind, v = self.take()
        if kind in ("str", "num"):
            return ("lit", v)
        if (kind, v) == ("op", "("):
            node = self.or_()
            self.take(")")
            return node
        if kind == "name":
            if v in ("true", "false", "null"):
                return ("lit", {"true": True, "false": False, "null": None}[v])
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.or_())
                    while self.peek() == ("op", ","):
                        self.take()
                        args.append(self.or_())
                self.take(")")
                return ("call", v, args)
            return ("name", v)
        raise SyntaxError(f"unexpected {v!r}")

    def value(self, ctx: dict) -> Any:
        return self._eval(self.tree, ctx)

    def _eval(self, node, ctx: dict) -> Any:
        op = node[0]
        if op == "lit":
            return node[1]
        if op == "name":
            cur: Any = ctx
            for part in node[1].split("."):
                cur = cur.get(part) if isinstance(cur, dict) else None
            return cur
        if op == "not":
            return not truthy(self._eval(node[1], ctx))
        if op == "and":
            a = self._eval(node[1], ctx)
            return self._eval(node[2], ctx) if truthy(a) else a
        if op == "or":
            a = self._eval(node[1], ctx)
            return a if truthy(a) else self._eval(node[2], ctx)
        if op in ("==", "!="):
            same = equal(self._eval(node[1], ctx), self._eval(node[2], ctx))
            return same if op == "==" else not same
        if op == "call":
            name, args = node[1], [self._eval(a, ctx) for a in node[2]]
            if name == "format":
                return re.sub(r"\{(\d+)\}", lambda m: text_of(args[1 + int(m.group(1))]), str(args[0]))
            raise NotImplementedError(f"{name}() is not evaluated here")
        raise NotImplementedError(op)


def inside(value: str) -> str:
    """'${{ expr }}' (the whole value) → 'expr'."""
    m = re.fullmatch(r"\s*\$\{\{(.*)\}\}\s*", value, re.S)
    assert m, f"not one expression: {value!r}"
    return m.group(1)


def title(run_name: str, event: str, inputs: dict | None = None, schedule: str | None = None,
          actor: str = "a-volunteer", triggering_actor: str | None = None) -> str:
    """The title of a run of this kind ('' = GitHub's own: the commit's subject, the workflow's name)."""
    github = {"event_name": event, "actor": actor, "triggering_actor": triggering_actor or actor,
              "event": {"schedule": schedule} if schedule else {}}
    return text_of(Expr(inside(run_name)).value({"github": github, "inputs": inputs or {}}))


def load(name: str) -> tuple[dict, dict, str]:
    text = (WF / name).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    return doc, doc.get("on", doc.get(True)), text           # PyYAML reads the key `on:` as True


# A Run-workflow form's inputs as GitHub passes them (every input, its default unless changed); the Morning
# check's dispatches send {"morning": "true"} or {} (the defaults then).
def update_inputs(**over) -> dict:
    return {"crawl_minutes": "", "skip_crawl": False, "morning": False, **over}


def update_cases(full: str, midday: str, evening: str) -> list[tuple[str, dict, str]]:
    """(what, the run, its title) for every kind of Website update run — update.yml's three crons given.
    (tests/test_morning.py runs the same runs through the plan step.)"""
    return [
        ("the nightly schedule", dict(event="schedule", schedule=full), "Nightly full update (GitHub schedule)"),
        ("the midday schedule", dict(event="schedule", schedule=midday), "Midday refresh (GitHub schedule)"),
        ("the evening schedule", dict(event="schedule", schedule=evening), "Evening refresh (GitHub schedule)"),
        ("a schedule added later", dict(event="schedule", schedule="5 3 * * *"), "Midday refresh (GitHub schedule)"),
        ("the Morning check's refresh", dict(event="workflow_dispatch", actor=BOT, inputs=update_inputs(morning="true")),
         MC.MORNING_TITLE),
        ("a person who ticked morning (it overrides the rest)",
         dict(event="workflow_dispatch", inputs=update_inputs(morning=True, skip_crawl=True, crawl_minutes="120")),
         MC.MORNING_TITLE),
        ("the Morning check's full update", dict(event="workflow_dispatch", actor=BOT, inputs=update_inputs()),
         "Full update (started by the Morning check)"),
        ("Run workflow, skip_crawl", dict(event="workflow_dispatch", inputs=update_inputs(skip_crawl=True)),
         "Quick refresh (started by hand)"),
        ("Run workflow, crawl_minutes 0", dict(event="workflow_dispatch", inputs=update_inputs(crawl_minutes="0")),
         "Full update without the document search (started by hand)"),
        ("Run workflow, crawl_minutes 120", dict(event="workflow_dispatch", inputs=update_inputs(crawl_minutes="120")),
         "Full update (started by hand)"),
        ("Run workflow, nothing changed", dict(event="workflow_dispatch", inputs=update_inputs()),
         "Full update (started by hand)"),
        ("a push", dict(event="push"), ""),
    ]


class Evaluator(unittest.TestCase):
    def test_it_follows_githubs_rules(self):
        ctx = {"github": {"event_name": "push"}, "inputs": {}}
        for expr, want in (("'a' && 'b' || 'c'", "b"), ("'' && 'b' || 'c'", "c"), ("null || 0 || false || ''", ""),
                           ("inputs.x == ''", True), ("inputs.x == 0", True), ("'ABC' == 'abc'", True),
                           ("'1' == 1", True), ("'it''s'", "it's"), ("!inputs.x && 'yes'", "yes"),
                           ("github.event_name != 'schedule' && (1 == 2 || 'z')", "z"),
                           ("format('{0} by {1}', 'run', github.event_name)", "run by push")):
            with self.subTest(expr=expr):
                self.assertEqual(Expr(expr).value(ctx), want)
        for bad in ("'open", "a &&", "(a", "a b", "a = b"):
            with self.subTest(bad=bad), self.assertRaises(SyntaxError):
                Expr(bad)


# --------------------------------------------------------------------------- update.yml
class UpdateTitles(unittest.TestCase):
    def setUp(self):
        self.wf, self.on, self.text = load("update.yml")
        self.name = self.wf["run-name"]
        self.crons = [s["cron"] for s in self.on["schedule"]]

    def cases(self) -> list[tuple[str, dict, str]]:
        return update_cases(*self.crons)

    def test_one_line_for_github(self):
        # folded (>-): the lines are joined by spaces, nothing is left over at the end
        self.assertNotIn("\n", self.name)
        self.assertEqual(self.name, self.name.strip())
        self.assertIn("run-name: >-\n  ${{ inputs.morning && '", self.text)

    def test_the_title_of_every_kind_of_run(self):
        for what, run, want in self.cases():
            with self.subTest(run=what):
                self.assertEqual(title(self.name, **run), want)
                self.assertLessEqual(len(want), 60, "short enough for the Actions list")

    def test_the_morning_refresh_keeps_the_morning_checks_title(self):
        # scripts/ops/morning_check.py finds the refresh it started by this exact title: the first branch
        self.assertTrue(inside(self.name).strip().startswith(f"inputs.morning && '{MC.MORNING_TITLE}'"))
        titles = [want for _what, _run, want in self.cases()]
        self.assertEqual(titles.count(MC.MORNING_TITLE), 2, "the morning refresh's, and no other run's")

    def test_the_morning_checks_full_update_rule_knows_the_titles(self):
        # maybe_full_run counts a run as "a full update already started" by its title: every full update's title,
        # never a quick or a morning refresh's
        for what, run, want in self.cases():
            if not want:
                continue
            with self.subTest(run=what):
                full = want.startswith(("Full update", "Nightly full update"))
                self.assertEqual(MC.is_full_title(want), full)
        self.assertFalse(MC.is_full_title(""))
        self.assertFalse(MC.is_full_title(None))

    def test_every_input_is_tested_after_the_event(self):
        # a schedule's and a push's inputs are empty — and GitHub's null == '' is true: each branch that tests an
        # input (but the morning one, which only ever is true in a morning refresh) names the event first
        branches = [b.strip() for b in inside(self.name).split("||")]
        for b in branches[1:]:
            if "inputs." in b:
                with self.subTest(branch=b):
                    self.assertTrue(b.startswith("github.event_name == 'workflow_dispatch' && "), b)

    def test_the_schedule_strings_agree(self):
        # the nightly and the evening strings are tested by the run-name; the midday one is "any other schedule"
        # (the plan step and the commit message treat it the same way — tests/test_morning.py)
        self.assertEqual(len(self.crons), 3)
        full, _midday, evening = self.crons
        self.assertIn(f"github.event.schedule == '{full}' && 'Nightly full update (GitHub schedule)'", self.name)
        self.assertIn(f"github.event.schedule == '{evening}' && 'Evening refresh (GitHub schedule)'", self.name)
        self.assertEqual(len(re.findall(r"github\.event\.schedule ==", self.name)), 2)


# --------------------------------------------------------------------------- the other four workflows
class OtherTitles(unittest.TestCase):
    def test_morning_check(self):
        wf, _on, _text = load("morning.yml")
        name = wf["run-name"]
        self.assertNotIn("\n", name)
        self.assertEqual(title(name, "schedule", schedule="25 0-11,21-23 * * *"), "Morning check (GitHub schedule)")
        self.assertEqual(title(name, "workflow_dispatch", {"check_only": True}), "Morning check (look only)")
        # the morning alarm presses Run workflow with the key of its owner; a person shows as themself
        self.assertEqual(title(name, "workflow_dispatch", {"check_only": False}, actor="NETA65"),
                         "Morning check (started by NETA65)")
        self.assertEqual(title(name, "workflow_dispatch", {}, actor="NETA65", triggering_actor="a-volunteer"),
                         "Morning check (started by a-volunteer)", "a re-run: whoever re-ran it")

    def test_monthly_digest(self):
        wf, on, _text = load("monthly-digest.yml")
        name = wf["run-name"]
        self.assertNotIn("\n", name)
        self.assertEqual(title(name, "schedule", schedule=on["schedule"][0]["cron"]),
                         "Monthly e-mail digest (GitHub schedule)")
        # the title says what the first step decides, from the same inputs (its PREVIEW and FORCE)
        env = wf["jobs"]["digest"]["steps"][0]["env"]
        preview, force = Expr(inside(env["PREVIEW"])), Expr(inside(env["FORCE"]))
        for ticked, forced, want in ((True, False, "Monthly e-mail digest: preview only"),
                                     (True, True, "Monthly e-mail digest: preview only"),      # a preview never sends
                                     (False, False, "Monthly e-mail digest: SEND NOW (started by hand)"),
                                     (False, True, "Monthly e-mail digest: SEND AGAIN (forced, started by hand)")):
            with self.subTest(preview_only=ticked, force=forced):
                inputs = {"preview_only": ticked, "month": "", "force": forced}
                self.assertEqual(title(name, "workflow_dispatch", inputs), want)
                self.assertLessEqual(len(want), 60, "short enough for the Actions list")
                ctx = {"github": {"event_name": "workflow_dispatch"}, "inputs": inputs}
                self.assertEqual(truthy(preview.value(ctx)), ticked)
                self.assertEqual(truthy(force.value(ctx)), forced)
        for e in (preview, force):
            self.assertFalse(truthy(e.value({"github": {"event_name": "schedule"}, "inputs": {}})), "a scheduled try")

    def test_weekly_link_check(self):
        wf, _on, _text = load("link-check.yml")
        self.assertEqual(title(wf["run-name"], "schedule", schedule="40 8 * * 0"), "Weekly link check (GitHub schedule)")
        self.assertEqual(title(wf["run-name"], "workflow_dispatch"), "Weekly link check (started by hand)")

    def test_code_check(self):
        wf, _on, _text = load("check.yml")
        self.assertEqual(title(wf["run-name"], "workflow_dispatch"), "Code check (started by hand)")
        self.assertEqual(title(wf["run-name"], "push"), "", "a push: the commit's subject")
        self.assertEqual(title(wf["run-name"], "pull_request"), "", "a pull request: its title")
        # not "Build the website" — that is Website update's build step
        self.assertEqual(wf["jobs"]["build"]["name"], "Test build of the website")

    def test_the_names_stay(self):
        # the workflows' own names (the sidebar, the Run workflow menu, GitHub's "Run failed: …" e-mails; the docs,
        # the morning alarm and morning_check.py use the files). The Morning check's "5:30 AM" is config/site.yml →
        # site.morning_goal (the next test).
        names = {f.name: yaml.safe_load(f.read_text(encoding="utf-8"))["name"] for f in sorted(WF.glob("*.yml"))}
        self.assertEqual(names, {"check.yml": "Code check (tests and test build)", "link-check.yml": "Weekly link check",
                                 "monthly-digest.yml": "Monthly e-mail digest",
                                 "morning.yml": "Morning check (new day by 5:30 AM)", "update.yml": "Website update"})

    def test_the_morning_check_names_its_goal(self):
        # morning.yml's name says the goal, config/site.yml → site.morning_goal, as the Morning check's run summary
        # writes it ("goal 5:30 AM"): a new goal needs the new name (and the line above) in the same commit
        cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        tz, (hour, minute) = MC.settings(cfg)
        goal = MC.clock_label(datetime(2026, 1, 15, hour, minute, tzinfo=tz), tz).rsplit(" ", 1)[0]
        name = yaml.safe_load((WF / "morning.yml").read_text(encoding="utf-8"))["name"]
        self.assertEqual(name, f"Morning check (new day by {goal})")


# --------------------------------------------------------------------------- every expression
def strings(node: Any, path: str = ""):
    """Every string value in a loaded workflow, with where it is."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


class Expressions(unittest.TestCase):
    def test_every_expression_is_well_formed(self):
        for f in sorted(WF.glob("*.yml")):
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            n = 0
            for where, value in strings(doc):
                found = re.findall(r"\$\{\{(.*?)\}\}", value, re.S)
                if where.endswith(".if") and not found:
                    found = [value]                      # an `if:` may leave out the ${{ }}
                for expr in found:
                    n += 1
                    with self.subTest(workflow=f.name, at=where, expr=expr.strip()[:80]):
                        Expr(expr)
            self.assertGreater(n, 0, f.name)

    def test_every_step_and_job_named_in_an_expression_is_there(self):
        # steps.<id>… only of an earlier step of the same job (the job's own keys — its outputs, its environment's
        # address — of any of its steps); needs.<job>… only of a job it needs
        for f in sorted(WF.glob("*.yml")):
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            for jname, job in doc["jobs"].items():
                needs = job.get("needs") or []
                needs = [needs] if isinstance(needs, str) else needs
                steps = job.get("steps") or []
                ids = [s.get("id") for s in steps]
                places = [(len(steps), {k: v for k, v in job.items() if k != "steps"})]
                places += [(i, s) for i, s in enumerate(steps)]
                for at, node in places:
                    for where, value in strings(node):
                        for sid in re.findall(r"\bsteps\.([A-Za-z0-9_-]+)\.", value):
                            with self.subTest(workflow=f.name, job=jname, at=where, step=sid):
                                self.assertIn(sid, ids[:at], "an earlier step of this job")
                        for need in re.findall(r"\bneeds\.([A-Za-z0-9_-]+)\.", value):
                            with self.subTest(workflow=f.name, job=jname, at=where, needs=need):
                                self.assertIn(need, needs)


if __name__ == "__main__":
    unittest.main()
