"""The Python a workflow step runs, for the tests that run a step's script (tests/ is on sys.path under
"unittest discover -s tests"):

    from workflow_steps import step_code
    code = step_code(step["run"])      # → exec(compile(code, …)) or write it to a file and run it with python

A step either holds its script inline (`python - <<'PY'` … `PY`: the heredoc) or — since November 2026, when the
scripts moved out of .github/workflows/update.yml into scripts/ops — runs a module (`python -m scripts.ops.<name>
[args]`): then the code runs that module as the step does (runpy, with the step's arguments), from the repository's
scripts (the tests put the repository's root on PYTHONPATH or sys.path).
"""
from __future__ import annotations

import re
import shlex
import textwrap

# `python -m scripts.ops.<name> [args]` anywhere in a step (`if python -m …; then`, `x="$(python -m … || true)"`): its
# arguments end at a shell operator or a redirection
_MODULE = re.compile(r"\bpython3?\s+-m\s+(scripts\.ops\.[\w.]+)((?:[ \t]+(?![0-9]?[<>])[^\s;|&()<>\"]+)*)")


def step_code(run: str) -> str:
    """The step's Python: its heredoc, or code that runs its `python -m scripts.ops.<name> [args]`."""
    if "<<'PY'\n" in run:
        return run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    m = _MODULE.search(run)
    if not m:
        raise ValueError(f"no Python in this step:\n{run[:400]}")
    module, args = m.group(1), shlex.split(m.group(2) or "")
    return ("import runpy, sys\n"
            f"sys.argv = [{module!r}, *{args!r}]\n"
            f"runpy.run_module({module!r}, run_name='__main__', alter_sys=True)\n")


def module_of(run: str) -> tuple[str, list[str]] | None:
    """(module, args) of a step that runs `python -m scripts.ops.<name> [args]`, else None."""
    m = _MODULE.search(run)
    return (m.group(1), shlex.split(m.group(2) or "")) if m else None


# the function of a module that a step's arguments run (the step's former inline script)
FUNCTIONS = {("scripts.ops.run_summary", ""): "main",
             ("scripts.ops.report_issues", "sources"): "report_sources",
             ("scripts.ops.report_issues", "updates"): "report_updates",
             ("scripts.ops.report_issues", "mornings"): "report_mornings",
             ("scripts.ops.sync_steps", "model-key"): "model_key",
             ("scripts.ops.sync_steps", "archive-taken"): "archive_taken",
             ("scripts.ops.sync_steps", "quote-words"): "quote_words"}


def step_source(run: str) -> str:
    """The source text of what a step runs, for a test that reads it: the step's own text and, for each
    `python -m scripts.ops.<name> <arg>` in it, the source of the function that runs (FUNCTIONS; else the whole
    module) — a step's script reads the same whether it is inline or moved to scripts/ops."""
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    parts = [run]
    for m in _MODULE.finditer(run):
        module, args = m.group(1), shlex.split(m.group(2) or "")
        text = (root / (module.replace(".", "/") + ".py")).read_text(encoding="utf-8")
        fn = FUNCTIONS.get((module, args[0] if args else ""))
        node = next((n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == fn), None) if fn else None
        if node is None:
            parts.append(text)
            continue
        lines = text.splitlines()[node.body[0].lineno - 1:node.end_lineno]     # the body, as the inline script was
        parts.append(textwrap.dedent("\n".join(lines)))
    return "\n".join(parts)
