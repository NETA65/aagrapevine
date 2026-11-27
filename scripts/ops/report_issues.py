"""The GitHub issues Website update keeps (.github/workflows/update.yml, job "report"):

    python -m scripts.ops.report_issues sources      # "A content source has stopped updating"
    python -m scripts.ops.report_issues updates      # "The website update keeps failing"
    python -m scripts.ops.report_issues mornings     # "The daily quote missed the morning goal"

Each issue opens when something has gone wrong twice in a row (once can be a passing hiccup), is edited silently
while it stays wrong (GitHub e-mails nobody about an edit) and closes by itself, with a comment, once it works again.
The job runs after every Website update run and never fails it (each step is continue-on-error). Standard library
only: the job installs no packages (python3 of the runner). `gh` (GitHub's command line, logged in with the job's
GH_TOKEN, repository GH_REPO) does the issue work.

"sources" and "updates" are the job's two first steps, moved out of the workflow in November 2026 line for line
(report_sources / report_updates are the steps' former scripts; env as the steps give it: HEALTH, SITE_URL, RUN_URL,
REPO_URL — and EVENT, ACTOR, RUN_ID, SYNC, TESTS, BUILD, PUBLISH for "updates"). tests/test_automation.py
(FailingUpdates), tests/test_morning.py, tests/test_r33_misc.py, tests/test_r25_lavina_podcast.py and
tests/test_sync_pipeline.py run them through the steps.

"mornings" — the daily-quote morning goal (config/site.yml site.morning_goal, 5:30 AM Central: the Morning check,
.github/workflows/morning.yml, puts the new day and both quotes on the site by then). Reads HEALTH (the sync job's
`health` output, one line of JSON: `quote_days` = data/site/status.json quote_days, `tz` = site.timezone, `site`)
and decides each morning the same way as /status/ (eleventy/filters/freshness.js quoteMorning): "met" when both
quotes came in by the goal, "missed" when the goal passed without both, "pending" before the goal. Only while the
outside morning alarm is set up (HEALTH `alarm` = config/site.yml site.morning_alarm: true — GitHub's own schedule
alone can run hours late): two missed mornings in a row open the issue (the alarm at cron-job.org has usually
stopped: docs/OPERATIONS.md → "Set up the cron-job.org alarm later") — only mornings whose goal came after the
alarm was switched on (HEALTH `alarm_since` = status.json morning_alarm_since, when a build first saw it on; not
known → every morning counts), so switching it on never opens the issue at once over the mornings before. The
first morning that meets the goal closes an open issue, alarm or not.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

# --------------------------------------------------------------------------- shared
Gh = Callable[..., str]


def run_gh(*args: str) -> str:
    """`gh <args>` → its output; a failure stops the step with gh's message (the step is continue-on-error)."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"'gh {' '.join(args[:2])}' failed: {r.stderr.strip()}")
    return r.stdout


def open_issue(gh: Gh, title: str) -> dict | None:
    """The open issue with exactly this title, or None."""
    issues = json.loads(gh("issue", "list", "--state", "open", "--limit", "100", "--json", "number,title,body") or "[]")
    return next((i for i in issues if i.get("title") == title), None)


def moment(iso: Any) -> datetime | None:
    """An ISO instant ("2026-11-25T14:06:56Z") → an aware datetime; None for anything else."""
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------- sources
def report_sources() -> None:
    """The step 'Open, update or close the report issue': HEALTH's `stale` sources → the issue 'A content source has stopped updating'."""
    import json, os, re, subprocess

    TITLE = "A content source has stopped updating"
    h = json.loads(os.environ["HEALTH"])
    stale, limit = h.get("stale") or [], h.get("days") or 7
    # The Status page link: the live address (SITE_URL, from the Pages settings — the custom domain), else the
    # sync job's stand-in from config/site.yml (a run whose build stopped early)
    site = (os.environ.get("SITE_URL") or h.get("site") or "").rstrip("/")
    run_url, repo_url = os.environ["RUN_URL"], os.environ["REPO_URL"]
    # What the chair can do about each kind of source (everything else: generic advice).
    HINTS = {
        "drive": "check that the committee folder (config/site.yml → drive → root_folder_id) is still "
                 "shared as **Anyone with the link — Viewer** (README → section 2).",
        "instagram": "Instagram keeps refusing the site's robot. The last posts stay on the site; for a lasting "
                     "fix add the free Instagram token (README → section 10 b) or list posts by hand (section 9).",
        "writers_archive": "check the newest file in content/archive: it must keep the archive's columns, and a "
                           "file much smaller than the one used before is not used (the run summary's \"CSV "
                           "file to fix\" line says which). The archive already on the site stays meanwhile.",
        # one podcast show ("podcasts:<key>") — the others still update
        "podcasts:": "the show's feed no longer answers: open its feed address (config/site.yml → sources.podcasts "
                    "→ feed) in a browser. A show that moved to a new feed needs the new address there (its "
                    "Apple Podcasts or host page names it). Its episodes stay on the site meanwhile.",
    }
    # A source that still works but that no run has tried for a week ("not checked" in the run summary).
    UNCHECKED = ("no run has got to it for {n} days: the update stops before it (open the latest \"Nightly full "
                 "update\" run and look for the step that failed or ran out of time), or no longer runs it.")

    def hint(source):   # a source's own advice; "podcasts:<key>" (one show) takes the "podcasts:" one
        s = str(source or "")
        return (HINTS.get(s) or (HINTS.get(s.split(":")[0] + ":") if ":" in s else None)
                or "the other website may have changed or be down. Send this issue to whoever helps with the website.")

    def gh(*args):
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"'gh {' '.join(args[:2])}' failed: {r.stderr.strip()}")
        return r.stdout

    def code(s):   # inline code: keeps "@name" in error texts from notifying GitHub users
        s = re.sub(r"\s+", " ", str(s or "")).replace("`", "'").strip()
        return f"`{s}`" if s else "—"

    issues = json.loads(gh("issue", "list", "--state", "open", "--limit", "100",
                           "--json", "number,title,body") or "[]")
    issue = next((i for i in issues if i.get("title") == TITLE), None)

    if not stale:
        if issue:
            gh("issue", "close", str(issue["number"]), "--comment",
               f"Every content source is updating again ({run_url}). Closing automatically.")
            print(f"Closed issue #{issue['number']}")
        else:
            print(f"No source has been failing for {limit}+ days.")
        raise SystemExit(0)

    rows, todo = [], []
    for x in stale:
        when = (f"{x['updated'][:10]} ({x['days']} days ago)" if x.get("updated") and x.get("days") is not None
                else "never")
        rows.append(f"| {x['label']} | {when} | {code(x.get('error'))} |")
        todo.append(f"- **{x['label']}:** " + (UNCHECKED.format(n=x["unchecked"]) if x.get("unchecked") else hint(x.get("source"))))
    keys = sorted(str(x.get("source")) for x in stale)
    status = f"[Status page]({site}/status/) · " if site else ""
    body = "\n".join([
        f"**{len(stale)} content source(s) of the website have not updated for {limit} days or more.** "
        "The website still works and keeps showing their older items, but nothing new arrives from "
        "them until the cause is fixed.", "",
        "| Source | Last successful update | Problem reported |", "|---|---|---|", *rows, "",
        "**What to do**", "", *todo, "",
        f"{status}[Latest run]({run_url}) · [Troubleshooting]({repo_url}#15-troubleshooting)", "",
        "*This issue is updated after every Website update run and closes by itself once every "
        "source works again.*",
        f"<!-- failing-sources: {','.join(keys)} -->",
    ])

    if not issue:
        gh("issue", "create", "--title", TITLE, "--body", body)
        print("Opened a new issue:\n" + body)
        raise SystemExit(0)
    num = str(issue["number"])
    m = re.search(r"<!-- failing-sources: ([^>]*?) -->", issue.get("body") or "")
    before = set(filter(None, (m.group(1) if m else "").split(",")))
    gh("issue", "edit", num, "--body", body)       # silent: edits send no e-mail
    added = [x["label"] for x in stale if str(x.get("source")) not in before]
    if added:                                      # a comment does: only for a NEW problem
        gh("issue", "comment", num, "--body", "Now also not updating: " + ", ".join(added)
           + f". See the updated description above ({run_url}).")
    print(f"Updated issue #{num}" + (f" (new: {', '.join(added)})" if added else ""))


# --------------------------------------------------------------------------- updates
def report_updates() -> None:
    """The step 'Open, update or close the issue about failing updates': this run's job results against the previous run → 'The website update keeps failing'."""
    import json, os, re, subprocess

    TITLE = "The website update keeps failing"
    BOT = "github-actions[bot]"
    # this run's jobs (their names on the run's page) → how each ended; what to do when one fails
    JOBS = {"sync": ("Sync content + translate", os.environ.get("SYNC", "")),
            "tests": ("Test the code before publishing", os.environ.get("TESTS", "")),
            "build": ("Build website", os.environ.get("BUILD", "")),
            "publish": ("Publish to GitHub Pages", os.environ.get("PUBLISH", ""))}
    HINTS = {
        "sync": "the site data could not be built, or the data commit could not be saved — its log says which "
                "step; the site was still published with the data it had (if the other jobs worked).",
        "tests": "a change to the code broke the tests, so nothing was published (the live site keeps the version "
                 "before): the run summary lists the failing tests and says which of them read the committee's "
                 "own files — fix the change or undo it (a fix in tests/ starts a run too).",
        "build": "the website could not be built (often a text missing from src/_i18n after an edit): fix the "
                 "change or undo it; the live site keeps the version before.",
        "publish": "GitHub Pages did not take the new version — usually GitHub's own trouble: open the run and "
                   "press \"Re-run failed jobs\", or wait for the next run.",
    }
    FAILED = ("failure", "timed_out", "startup_failure")
    run_id, run_url, repo_url = os.environ["RUN_ID"], os.environ["RUN_URL"], os.environ["REPO_URL"]

    def gh(*args):
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"'gh {' '.join(args[:2])}' failed: {r.stderr.strip()}")
        return r.stdout

    # (a job that ran out of time is "cancelled" here: this job runs only when the run itself was not cancelled)
    failed = [k for k, (_name, result) in JOBS.items() if result in ("failure", "cancelled")]
    worked = all(result == "success" for _name, result in JOBS.values())
    unattended = os.environ.get("EVENT") == "schedule" or (os.environ.get("EVENT") == "workflow_dispatch"
                                                           and os.environ.get("ACTOR") == BOT)
    issues = json.loads(gh("issue", "list", "--state", "open", "--limit", "100", "--json", "number,title,body") or "[]")
    issue = next((i for i in issues if i.get("title") == TITLE), None)

    if worked:
        if issue:
            gh("issue", "close", str(issue["number"]), "--comment",
               f"The website update works again: this run published the site ({run_url}). Closing automatically.")
            print(f"Closed issue #{issue['number']}: the update works again.")
        else:
            print("This run worked.")
        raise SystemExit(0)
    if not failed:
        print("No job failed (" + ", ".join(f"{n}: {r or '?'}" for n, r in JOBS.values()) + ") — nothing to report.")
        raise SystemExit(0)

    # the previous Website update run that ended (not this one, still going; not one replaced or cancelled)
    runs = json.loads(gh("api", "repos/{owner}/{repo}/actions/workflows/update.yml/runs?status=completed&per_page=30")
                      or "{}").get("workflow_runs") or []
    prev = next((r for r in runs if str(r.get("id")) != run_id
                 and r.get("conclusion") not in ("cancelled", "skipped", "neutral", None)), None)
    prev_failed = bool(prev) and prev.get("conclusion") in FAILED
    what = [f"- **{JOBS[k][0]}** failed: {HINTS[k]}" for k in failed]
    keys = ",".join(failed)

    def body(n: int) -> str:
        lines = [f"**The website update has failed {n} times in a row.** The last time: [this run]({run_url}).", "",
                 *what, "",
                 "**What to do:** open the run, then the job with the red ✗: its red step says what went wrong. "
                 "The live site stays as it was published last; the Morning check reports a morning that did not "
                 "reach the site.", "",
                 f"[All Website update runs]({repo_url}/actions/workflows/update.yml) · "
                 f"[Troubleshooting]({repo_url}#15-troubleshooting)", "",
                 "*This issue is updated after every failed run and closes by itself after the next run that "
                 "works.*",
                 f"<!-- failing-jobs: {keys} --> <!-- failures: {n} -->"]
        return "\n".join(lines)

    if issue:
        old = issue.get("body") or ""
        m = re.search(r"<!-- failures: (\d+) -->", old)
        n = (int(m.group(1)) if m else 2) + 1
        gh("issue", "edit", str(issue["number"]), "--body", body(n))       # silent: edits send no e-mail
        m = re.search(r"<!-- failing-jobs: ([^>]*?) -->", old)
        new = [k for k in failed if k not in set(filter(None, (m.group(1) if m else "").split(",")))]
        if new:                                                            # a comment does: a new kind of failure
            gh("issue", "comment", str(issue["number"]), "--body",
               "Now also failing: " + ", ".join(JOBS[k][0] for k in new) + f" ({run_url}).")
        print(f"Updated issue #{issue['number']} ({n} failures in a row)")
    elif unattended and prev_failed:
        gh("issue", "create", "--title", TITLE, "--body", body(2))
        print(f"Opened the issue: this run and the previous one ({prev.get('html_url')}) failed.")
    elif unattended:
        print("This run failed, the previous one did not: no issue yet (it opens if the next run fails too).")
    else:
        print("This run failed; it was started by a person, whom GitHub e-mails about it — no issue.")


# --------------------------------------------------------------------------- mornings
MORNING_TITLE = "The daily quote missed the morning goal"
MISSED_IN_A_ROW = 2                    # like the failing-updates issue: one miss can be a passing hiccup
PUBS = (("gv", "Grapevine"), ("lv", "La Viña"))
MARKER = re.compile(r"<!-- missed-mornings: ([^>]*?) -->")


def zone(name: str | None):
    """The site's time zone (site.timezone, America/Chicago); UTC when this computer has no zone data."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name or "America/Chicago")
    except Exception:  # noqa: BLE001 — a missing tzdata never stops the report
        return timezone.utc


def morning_verdicts(quote_days: Any, now: datetime) -> list[dict]:
    """status.json quote_days → its days, newest first, each with `state`: "met" (both quotes came in by the
    goal), "missed" (the goal has passed without both: one came in late, or has not come in) or "pending" (the goal
    is still ahead and not both are in yet). A row without a readable day or goal is left out."""
    days = quote_days.get("days") if isinstance(quote_days, dict) else None
    out = []
    for r in days if isinstance(days, list) else []:
        if not isinstance(r, dict) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("day") or "")):
            continue
        goal = moment(r.get("goal_at"))
        if goal is None:
            continue
        seen = {p: moment(r.get(p)) for p, _name in PUBS}
        if all(seen.values()) and max(seen.values()) <= goal:
            state = "met"
        elif now > goal:
            state = "missed"
        else:
            state = "pending"
        out.append({"day": r["day"], "goal_at": goal, **seen, "state": state})
    return out


def missed_streak(verdicts: Sequence[dict]) -> tuple[list[dict], dict | None]:
    """→ (the missed mornings in a row up to the newest decided one, newest first; the newest decided morning).
    A pending morning (today before the goal) is not decided yet and is skipped."""
    decided = [v for v in verdicts if v["state"] != "pending"]
    streak = []
    for v in decided:
        if v["state"] != "missed":
            break
        streak.append(v)
    return streak, (decided[0] if decided else None)


def _clock(t: datetime | None, tz) -> str:
    if t is None:
        return "not yet"
    local = t.astimezone(tz)
    return local.strftime("%I:%M %p").lstrip("0") + (f" {local.tzname()}" if local.tzname() else "")


def _day(ymd: str) -> str:
    d = datetime.strptime(ymd, "%Y-%m-%d")
    return f"{d:%a}, {d:%b} {d.day}"


def morning_body(streak: Sequence[dict], tz, site: str, repo_url: str, run_url: str) -> str:
    rows = [f"| {_day(v['day'])} | {_clock(v['goal_at'], tz)} | "
            + " | ".join(_clock(v[p], tz) for p, _name in PUBS) + " |" for v in streak]
    goal = _clock(streak[0]["goal_at"], tz).split(" ")
    goal_s = " ".join(goal[:2])
    status = f"[Status page]({site}/status/) · " if site else ""
    return "\n".join([
        f"**The daily quotes were not on the website by the {goal_s} goal on {len(streak)} mornings in a row** "
        f"(the last: {_day(streak[0]['day'])}). The site still works; only the new day's quotes came in late.", "",
        "| Morning | Goal | " + " | ".join(f"{name} quote came in" for _p, name in PUBS) + " |",
        "|---|---|---|---|", *rows, "",
        "**What to do**", "",
        "1. **Check the morning alarm** at cron-job.org (README → 10 d, \"The morning alarm\"). Its history shows "
        "each morning's call: **401** means its GitHub key has expired — make a new one and paste it there; **404** "
        "means the address is wrong (the workflow file was renamed or the repository moved); no call at all means "
        "the alarm is switched off. GitHub's own schedule is only a backstop: it often starts hours late or not "
        "at all.",
        f"2. Open the [Morning check's runs]({repo_url}/actions/workflows/morning.yml): each morning should have a "
        "run at about 4:30 AM Central started by the alarm's owner. A red run there says what went wrong.",
        "3. If a Morning check run says *\"A daily quote is late at the source\"*, the magazine itself published "
        "late: nothing to fix on our side (the issue closes after the next good morning).", "",
        f"{status}[Morning check runs]({repo_url}/actions/workflows/morning.yml) · [Latest run]({run_url})", "",
        "*This issue is updated after every Website update run and closes by itself after the first morning whose "
        "quotes are on the site by the goal.*",
        f"<!-- missed-mornings: {','.join(sorted(v['day'] for v in streak))} -->",
    ])


def report_mornings(health: dict, gh: Gh, now: datetime, repo_url: str, run_url: str, site_url: str = "") -> str:
    """Opens, updates or closes the "missed the morning goal" issue → what it did (printed in the log)."""
    tz = zone(health.get("tz"))
    streak, newest = missed_streak(morning_verdicts(health.get("quote_days"), now))
    site = (site_url or health.get("site") or "").rstrip("/")
    issue = open_issue(gh, MORNING_TITLE)
    if newest is None:
        return "No morning to judge yet (status.json has no quote_days)."
    if newest["state"] == "met":
        if not issue:
            return f"The quotes of {newest['day']} were on the site by the goal."
        gh("issue", "close", str(issue["number"]), "--comment",
           f"The daily quotes of {_day(newest['day'])} came in by the goal "
           f"({_clock(max(newest[p] for p, _n in PUBS), tz)}). Closing automatically ({run_url}).")
        return f"Closed issue #{issue['number']}: the quotes of {newest['day']} were on time."
    if not issue and not health.get("alarm"):
        # GitHub's own schedule alone can run hours late: a missed morning is no news until the alarm is set up
        return (f"The goal was missed on {len(streak)} morning(s) in a row (the last: {newest['day']}), but no outside "
                "morning alarm is set up (config/site.yml site.morning_alarm: false) — GitHub's own schedule can run "
                "late, so no issue is opened.")
    # The alarm was switched on after some of these mornings (status.json morning_alarm_since): they blame no alarm —
    # only the mornings whose goal came after it count, and only they are listed (an issue still open from an
    # earlier time it was on keeps its mornings until one comes after the switch).
    since = moment(health.get("alarm_since"))
    fresh = [v for v in streak if since is None or v["goal_at"] > since]
    if not issue and len(fresh) < len(streak) and len(fresh) < MISSED_IN_A_ROW:
        return (f"The goal was missed on {len(streak)} morning(s) in a row (the last: {newest['day']}), but "
                f"{'only ' + str(len(fresh)) if fresh else 'none'} of them since the morning alarm was switched on "
                f"(config/site.yml site.morning_alarm, first seen {since:%Y-%m-%d %H:%M} UTC): no issue yet (it opens "
                f"after {MISSED_IN_A_ROW} missed mornings in a row with the alarm on).")
    streak = fresh or streak
    if not issue and len(streak) < MISSED_IN_A_ROW:
        return (f"The goal was missed on {newest['day']}, the morning before was not: no issue yet "
                "(it opens if the next morning misses it too).")
    body = morning_body(streak, tz, site, repo_url, run_url)
    if not issue:
        gh("issue", "create", "--title", MORNING_TITLE, "--body", body)
        return f"Opened the issue: {len(streak)} mornings in a row missed the goal.\n{body}"
    m = MARKER.search(issue.get("body") or "")
    if m and m.group(1) == ",".join(sorted(v["day"] for v in streak)):
        return f"Issue #{issue['number']} already lists these mornings."
    gh("issue", "edit", str(issue["number"]), "--body", body)          # silent: edits send no e-mail
    return f"Updated issue #{issue['number']} ({len(streak)} missed mornings in a row)."


# --------------------------------------------------------------------------- command line
def main(argv: Sequence[str] | None = None, gh: Gh = run_gh, now: datetime | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    what = args[0] if args else ""
    env = os.environ
    now = now or datetime.now(timezone.utc)
    if what == "sources":
        report_sources()
        return 0
    if what == "updates":
        report_updates()
        return 0
    if what == "mornings":
        try:
            health = json.loads(env.get("HEALTH") or "{}")
        except ValueError as e:
            print(f"HEALTH is not JSON ({e}) — nothing reported.")
            return 0
        print(report_mornings(health if isinstance(health, dict) else {}, gh, now, env.get("REPO_URL", ""),
                              env.get("RUN_URL", ""), env.get("SITE_URL", "")))
        return 0
    print("usage: python -m scripts.ops.report_issues sources|updates|mornings", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
