"""The sources a push to main ALSO runs: the ones only the full daily update reads (run_all FULL_ONLY), when the
push changed a file — or the part of config/site.yml — that they read while they sync.

A push (a settings, content or template edit) starts a QUICK run of .github/workflows/update.yml (run_all
--quick: Drive, the bulletin, podcasts, the daily quote, the writers archive, then the site data and the build).
An edit of what a full-update-only source reads — the Instagram posts listed by hand, La Viña's weekly open
meeting, the meeting lists — would otherwise show only after the next nightly run, up to a day later. So the
step "Decide what to sync" runs this script, and passes the sources it names to run_all --also:

    content/instagram.yml          → instagram  (the posts listed by hand)
    data/geo/texas_places.json     → meetings   (which meetings are in our Area)
    config/site.yml                → only the sources whose part of it changed (SETTINGS below); what the site
                                     data or the pages read is rebuilt by every run anyway

Never the search of the magazine sites, their stories or their store (crawl, articles, shop: many polite requests
to aagrapevine.org / aalavina.org) — those run every night.

The changed files come from git, as GitHub's own `paths:` filter sees the push: the files that differ between the
commit the push started from and its last commit — `before` and `after` in the event file GitHub writes for the run
($GITHUB_EVENT_PATH; `after` is also $GITHUB_SHA) — git diff --name-only <before> <after>. The checkout has only
the newest commit, so a commit it lacks is fetched first, one commit deep (git fetch --depth=1 origin <commit>);
config/site.yml as it was before the push is then git show <before>:config/site.yml. The event file of a workflow
run lists no files per commit (a webhook's does: those lists are added). When git cannot say — no commit before
the push (a new branch's 000…0), a commit that cannot be fetched — those lists are used alone; without any,
nothing is added and a notice says so: those sources show the change after the next full daily update. The same
for config/site.yml alone when its copy from before the push cannot be read.

    python -m scripts.ops.push_modules --output "$RUNNER_TEMP/push-also.txt"      # on GitHub (push runs only)
    python -m scripts.ops.push_modules --event push.json --previous-config old-site.yml

It prints what it decided, and writes `also=<the sources, in run_all's order, comma-separated>` and
`also_why=<one line: which change brought each one>` to --output (both empty when nothing is added). It never
stops the step (exit 0): on any surprise it adds nothing and says why. Standard library and PyYAML only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "config/site.yml"

# The sources only the full daily update reads (run_all.FULL_ONLY, in run_all's order — tests/test_push_modules.py
# checks both) → the parts of config/site.yml each one reads while it syncs, as read in the module itself. Left
# out: what a source reads only to name itself (sources.crawler.user_agent; site.url, instagram's referer) or to
# know today's date (site.timezone) — an edit of those changes nothing it collects.
SETTINGS: dict[str, tuple[str, ...]] = {
    # youtube.py main(): the channels
    "youtube": ("sources.youtube",),
    # instagram.py main(): the accounts, anonymous, keep_per_account, enrich_per_run, graph_version, …
    "instagram": ("sources.instagram",),
    # editorial.settings(): the two "contribute" pages, La Viña's themes page and the link to its themes document
    "editorial": ("sources.grapevine.base", "sources.grapevine.contribute", "sources.lavina.base",
                  "sources.lavina.contribute", "sources.lavina.themes_page", "sources.lavina.rlv_resources",
                  "sources.lavina.themes_link"),
    # weekly_open.py main(): the Grapevine Weekly Open page, and La Viña's weekly open meeting (from its flyer)
    "weekly_open": ("sources.grapevine.base", "sources.grapevine.weekly_open", "lavina_weekly_open"),
    # audio_project.settings(): the record-your-story pages (the links to the other three are kept with the item)
    "audio_project": ("sources.grapevine.base", "sources.grapevine.audio_project", "sources.lavina.base",
                      "sources.lavina.record_story", "sources.lavina.record_instructions",
                      "sources.lavina.record_tips", "sources.lavina.record_topics", "sources.lavina.sample_audio"),
    # meetings.settings(): the offices and their lists; area_of() → geo: the Area 65 counties
    "meetings": ("meetings", "spotlight.neta65_counties"),
    # events_external.py: the event calendar's sitemap (Grapevine's site) and the two calendar pages
    "events_external": ("sources.grapevine.base", "sources.lavina.base"),
}
# Files a full-update-only source reads while it syncs (repository paths).
FILES: dict[str, str] = {
    "content/instagram.yml": "instagram",          # instagram.MANUAL_FILE: the posts listed by hand
    "data/geo/texas_places.json": "meetings",      # geo.gazetteer(): a meeting's city → its county (in our Area?)
}
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
LISTS = ("added", "modified", "removed")          # a commit's files, in a payload that lists them


def read_text(path: str | Path | None) -> str | None:
    if not path:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def load_event(path: str | Path | None) -> dict:
    """The push payload GitHub wrote for the run ({} when there is none, or it is not JSON)."""
    try:
        doc = json.loads(read_text(path) or "{}")
    except ValueError:
        return {}
    return doc if isinstance(doc, dict) else {}


def commit_id(value: Any) -> str | None:
    """A full commit id (40 hex digits; 64 in a SHA-256 repository), in lower case — None for anything else, and
    for the 000…0 of a new branch (no commit before the push)."""
    v = str(value or "").strip().lower()
    return v if SHA.fullmatch(v) and v.strip("0") else None


def commits(event: dict) -> list[dict]:
    """The commits of the push, as the payload has them."""
    c = event.get("commits")
    return [x for x in c if isinstance(x, dict)] if isinstance(c, list) else []


def changed_files(event: dict) -> list[str]:
    """Every file a commit of the push added, changed or deleted, as the payload lists them (repository paths,
    sorted). The event file of a workflow run has no such lists — on GitHub the files come from git (push_changes)."""
    out: set[str] = set()
    for c in commits(event):
        for key in LISTS:
            v = c.get(key)
            out.update(str(p).strip() for p in (v if isinstance(v, list) else []) if str(p or "").strip())
    return sorted(out)


class Git:
    """git in the checkout (`run`: subprocess.run; tests: a stand-in), never with a password prompt, never waiting
    for ever. The checkout has only the newest commit: a commit it lacks is fetched, one commit deep, once."""

    def __init__(self, root: str | Path = ROOT, run: Callable[..., Any] = subprocess.run):
        self.root, self.run = Path(root), run
        self.env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        self.known: dict[str, bool] = {}

    def __call__(self, *args: str, timeout: float = 60) -> Any:
        return self.run(["git", *args], cwd=str(self.root), env=self.env, capture_output=True, timeout=timeout)

    def have(self, commit: str) -> bool:
        """The commit is in the checkout (fetched first when it was not)."""
        if commit not in self.known:
            self.known[commit] = False         # a fetch that fails, or never ends (an error), is not tried again
            ok = self("cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
            if not ok:
                ok = self("fetch", "--quiet", "--no-tags", "--depth=1", "origin", commit, timeout=120).returncode == 0
            self.known[commit] = ok
        return self.known[commit]


def git_changes(before: str | None, after: str | None, git: Git) -> tuple[list[str] | None, str]:
    """The files that differ between the commit the push started from and its last commit, as GitHub's `paths:`
    filter sees the push (a renamed file counts with both names) → (the paths, sorted; "") — or (None, why git
    cannot say)."""
    if not before:
        return None, "there is no commit before it (a new branch)"
    if not after:
        return None, "its last commit is not named"
    try:
        for commit, what in ((before, "the commit before it"), (after, "its last commit")):
            if not git.have(commit):
                return None, f"{what} ({commit[:7]}) could not be fetched"
        r = git("diff", "--name-only", "--no-renames", "-z", before, after)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"git did not answer ({type(e).__name__})"
    if r.returncode != 0:
        return None, f"git could not compare {before[:7]} with {after[:7]}"
    out = r.stdout.decode("utf-8", "replace") if isinstance(r.stdout, bytes) else str(r.stdout or "")
    return sorted({p for p in out.split("\0") if p.strip()}), ""


def push_changes(event: dict, git: Git, head: str | None = None) -> tuple[list[str], str, list[str]]:
    """The files the push changed → (the paths, sorted; where they come from; notices). From git (git_changes, with
    the payload's `before` and `after` — `head`, i.e. $GITHUB_SHA, when it names no `after`), plus the payload's own
    lists; when git cannot say, those lists alone — and without any, none (a notice says so)."""
    listed = changed_files(event)
    before, after = commit_id(event.get("before")), commit_id(event.get("after")) or commit_id(head)
    found, why = git_changes(before, after, git) if event else (None, "GitHub's event file could not be read")
    if found is not None:
        return sorted(set(found) | set(listed)), f"git diff {before[:7]}..{after[:7]}", []
    if any(key in c for c in commits(event) for key in LISTS):
        return listed, "the files its event file lists", [
            f"Could not compare this push in git — {why} —, so the files its event file lists were used."]
    return [], "", [f"Could not tell which files this push changed — {why} —, so no other source was added for it: a "
                    "source only the full daily update reads shows its changes after the next one."]


def parse(text: str | None) -> dict | None:
    """A copy of config/site.yml → its settings (None: no copy, or not readable as YAML)."""
    if text is None:
        return None
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    return doc if isinstance(doc, dict) else {} if doc is None else None


def value_at(doc: Any, path: str) -> Any:
    """doc["sources"]["lavina"]["base"] for "sources.lavina.base" — None when a part is missing."""
    for part in path.split("."):
        if not isinstance(doc, dict):
            return None
        doc = doc.get(part)
    return doc


def changed_settings(old: dict, new: dict) -> list[str]:
    """The SETTINGS paths whose value differs between the two copies (each once, in the table's order)."""
    paths = dict.fromkeys(p for ps in SETTINGS.values() for p in ps)
    return [p for p in paths if value_at(old, p) != value_at(new, p)]


def previous_config(before: str | None, git: Git) -> str | None:
    """config/site.yml as it was at `before`, the commit the push started from — None when it cannot be read (no
    commit before it: a new branch's 000…0; the fetch failed; no such file then). Git.have fetches that commit
    when the checkout lacks it (mostly done already, to compare the two commits)."""
    before = commit_id(before)
    if not before:
        return None
    try:
        if not git.have(before):
            return None
        r = git("show", f"{before}:{CONFIG}")
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    out = r.stdout
    return out.decode("utf-8", "replace") if isinstance(out, bytes) else str(out)


def decide(changed: list[str], old_text: str | None, new_text: str | None) -> tuple[list[str], dict[str, list[str]],
                                                                                    list[str]]:
    """The push's changed files (and both copies of config/site.yml, when it is one of them) → (the sources to
    add, in run_all's order; {source: what brought it}; notices)."""
    why: dict[str, list[str]] = {}
    notices: list[str] = []
    for f in changed:
        if f in FILES:
            why.setdefault(FILES[f], []).append(f)
    if CONFIG in changed:
        old, new = parse(old_text), parse(new_text)
        if old is None or new is None:
            which = "its copy from before the push" if old is None else "it"
            notices.append(f"{CONFIG} changed, but {which} could not be read, so no other source was added for it: a "
                           "source only the full daily update reads shows the change after the next one.")
        else:
            for path in changed_settings(old, new):
                for module, paths in SETTINGS.items():
                    if path in paths:
                        why.setdefault(module, []).append(f"{CONFIG}: {path}")
    also = [m for m in SETTINGS if m in why]
    return also, {m: why[m] for m in also}, notices


def reason(items: list[str]) -> str:
    """["content/instagram.yml", "config/site.yml: meetings", "config/site.yml: spotlight.neta65_counties"] →
    "content/instagram.yml, config/site.yml: meetings, spotlight.neta65_counties"."""
    files = [i for i in items if not i.startswith(f"{CONFIG}: ")]
    parts = [i.split(": ", 1)[1] for i in items if i.startswith(f"{CONFIG}: ")]
    return ", ".join(files + ([f"{CONFIG}: " + ", ".join(parts)] if parts else []))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.ops.push_modules", description=__doc__.split("\n\n")[0])
    ap.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"),
                    help="the push payload (default: $GITHUB_EVENT_PATH)")
    ap.add_argument("--repo", default=str(ROOT), help="the git checkout of the push (default: this one)")
    ap.add_argument("--config", help=f"{CONFIG} after the push (default: the checkout's)")
    ap.add_argument("--previous-config", metavar="FILE",
                    help=f"{CONFIG} as it was before the push (default: from git, the commit before the push)")
    ap.add_argument("--output", metavar="FILE", help="append also=… and also_why=… to this file")
    a = ap.parse_args(argv)
    try:
        event = load_event(a.event)
        git = Git(a.repo)
        # the push's last commit, when its payload does not name it: the commit the run is for
        changed, source, notices = push_changes(event, git, os.environ.get("GITHUB_SHA"))
        if source:
            print(f"Files this push changed: {len(changed)} ({source}).", flush=True)
        old_text = None
        if CONFIG in changed:
            old_text = read_text(a.previous_config) if a.previous_config else previous_config(event.get("before"), git)
        also, why, more = decide(changed, old_text, read_text(a.config or Path(a.repo) / CONFIG))
        notices += more
    except Exception as e:  # noqa: BLE001 — never stops the run: the sources then wait for the full daily update
        also, why, notices = [], {}, [f"Could not work out which other sources this push needs ({type(e).__name__}: "
                                      f"{e}) — they show its changes after the next full daily update."]
    for n in notices:
        print(f"::notice title=Push run::{n}", flush=True)
    line = "; ".join(f"{m} ({reason(why[m])})" for m in also)
    print(f"Also run for this push: {line}" if also else "No other source needs to run for this push.", flush=True)
    if a.output:
        try:
            with open(a.output, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"also={','.join(also)}\nalso_why={line}\n")
        except OSError as e:
            print(f"::notice title=Push run::Could not write {a.output}: {e}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
