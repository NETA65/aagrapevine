"""Small steps of Website update's sync job (.github/workflows/update.yml, job "Sync content + translate"), moved out
of the workflow in November 2026 line for line (each function is a step's former inline script). Standard library
only (they run before or without the sync's packages). From the repository's root:

    python -m scripts.ops.sync_steps model-key       # "Work out the translation-model cache key": prints the
                                                     # fingerprint of MODEL_URLS in scripts/sync/translate.py
    python -m scripts.ops.sync_steps archive-taken   # "Commit refreshed data": exit 0 when this run took in a new
                                                     # writers archive file (env STARTED), else 1
    python -m scripts.ops.sync_steps quote-words     # "Commit refreshed data", a morning refresh: the words that
                                                     # name the daily quotes it brings (" with the daily quotes of
                                                     # Oct 6"), against the last commit's data/site/quote.json

Tested by tests/test_ops_scripts.py and, through the steps, tests/test_morning.py (the commit message) and
tests/test_automation.py.
"""
from __future__ import annotations

import sys


def model_key() -> None:
    """The translation models' cache key: a fingerprint of MODEL_URLS (else of the whole file)."""
    import ast, hashlib, json, pathlib
    src = pathlib.Path("scripts/sync/translate.py").read_text(encoding="utf-8")
    urls = None
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if node.value is not None and any(getattr(t, "id", None) == "MODEL_URLS" for t in targets):
            urls = ast.literal_eval(node.value)
    blob = json.dumps(urls, sort_keys=True) if urls else src
    print(("urls-" if urls else "file-") + hashlib.sha256(blob.encode()).hexdigest()[:16])


def archive_taken() -> None:
    """Exit 0 when data/raw/writers_archive.json says this run (env STARTED) took in a new archive file, else 1."""
    import json, os, sys
    from datetime import datetime, timezone
    def moment(v):
        try:
            t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            return None
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    r = json.load(open("data/raw/writers_archive.json", encoding="utf-8"))
    files = r.get("files") if isinstance(r.get("files"), dict) else {}
    start = moment(os.environ.get("STARTED"))
    taken = [moment(f.get("imported_at")) for f in files.values() if isinstance(f, dict)]
    this_run = start is not None and any(t is not None and t >= start for t in taken)
    sys.exit(0 if (r.get("stats") or {}).get("changed") is True and this_run else 1)


def quote_words() -> None:
    """The commit message's words for the daily quotes a morning refresh brings (stdout, UTF-8; nothing when none is new)."""
    import json, subprocess, sys
    from datetime import date
    NAMES = {"gv": "Grapevine", "lv": "La Viña"}
    def days(text):
        try:
            items = json.loads(text or "{}").get("items") or []
        except (ValueError, AttributeError):
            return {}
        out = {}
        for q in items if isinstance(items, list) else []:
            if isinstance(q, dict) and q.get("pub") in NAMES:
                try:
                    out[q["pub"]] = date.fromisoformat(str(q.get("date") or "")[:10])
                except ValueError:
                    pass
        return out
    try:
        with open("data/site/quote.json", encoding="utf-8") as f:
            now = days(f.read())
    except OSError:
        now = {}
    try:
        r = subprocess.run(["git", "show", "HEAD:data/site/quote.json"], capture_output=True, timeout=60)
        before = days(r.stdout.decode("utf-8", "replace")) if r.returncode == 0 else {}
    except (OSError, subprocess.SubprocessError):
        before = {}
    new = {p: d for p, d in now.items() if before.get(p) != d}
    label = lambda d: f"{d:%b} {d.day}"
    if len(new) == len(NAMES) and len(set(new.values())) == 1:
        words = f" with the daily quotes of {label(next(iter(new.values())))}"
    else:
        words = "".join((" with " if i == 0 else " and ") + f"the {NAMES[p]} quote of {label(new[p])}"
                        for i, p in enumerate(p for p in NAMES if p in new))
    sys.stdout.buffer.write(words.encode("utf-8"))


STEPS = {"model-key": model_key, "archive-taken": archive_taken, "quote-words": quote_words}


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    step = STEPS.get(args[0] if args else "")
    if step is None:
        print("usage: python -m scripts.ops.sync_steps " + "|".join(STEPS), file=sys.stderr)
        raise SystemExit(2)
    step()


if __name__ == "__main__":
    main()
