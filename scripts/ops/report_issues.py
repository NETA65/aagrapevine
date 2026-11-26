"""The GitHub issues Website update keeps (.github/workflows/update.yml, job "report"):

    python -m scripts.ops.report_issues mornings     # "The daily quote missed the morning goal"

Each issue opens when something has gone wrong twice in a row (once can be a passing hiccup), is edited silently
while it stays wrong (GitHub e-mails nobody about an edit) and closes by itself, with a comment, once it works again.
The job runs after every Website update run and never fails it (each step is continue-on-error). Standard library
only: the job installs no packages (python3 of the runner). `gh` (GitHub's command line, logged in with the job's
GH_TOKEN, repository GH_REPO) does the issue work.

"mornings" — the daily-quote morning goal (config/site.yml site.morning_goal, 5:30 AM Central: the Morning check,
.github/workflows/morning.yml, puts the new day and both quotes on the site by then). Reads HEALTH (the sync job's
`health` output, one line of JSON: `quote_days` = data/site/status.json quote_days, `tz` = site.timezone, `site`)
and decides each morning the same way as /status/ (eleventy/filters/freshness.js quoteMorning): "met" when both
quotes came in by the goal, "missed" when the goal passed without both, "pending" before the goal. Only while the
outside morning alarm is set up (HEALTH `alarm` = config/site.yml site.morning_alarm: true — GitHub's own schedule
alone can run hours late): two missed mornings in a row open the issue (the alarm at cron-job.org has usually
stopped: docs/OPERATIONS.md → "Set up the cron-job.org alarm later"). The first morning that meets the goal closes
an open issue, alarm or not.
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
    if what == "mornings":
        try:
            health = json.loads(env.get("HEALTH") or "{}")
        except ValueError as e:
            print(f"HEALTH is not JSON ({e}) — nothing reported.")
            return 0
        print(report_mornings(health if isinstance(health, dict) else {}, gh, now, env.get("REPO_URL", ""),
                              env.get("RUN_URL", ""), env.get("SITE_URL", "")))
        return 0
    print("usage: python -m scripts.ops.report_issues mornings", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
