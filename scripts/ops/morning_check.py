"""The Morning check: the new day and both daily quotes on the website by the goal — config/site.yml →
site.morning_goal, 5:30 AM Central — every day. It is the job "Put today's update on the site" of
.github/workflows/morning.yml (that workflow's first job, "look", already found the live site behind, or
the full daily update due).

Why it exists: GitHub starts scheduled runs when it has room — since late August 2026 often 4 to 8 hours
late, and a busy day can skip one — while a run started through the API (workflow_dispatch) starts within
seconds, and a morning refresh is live about 3 minutes later. So this script starts Update & Deploy itself
in MORNING mode (update.yml input `morning` → run_all --morning), follows it and reads the live site.

    python -m scripts.ops.morning_check                  # on GitHub (GH_TOKEN, GITHUB_REPOSITORY, SITE_URL)
    python -m scripts.ops.morning_check --check-only     # say what is on the site and what would be done
    python -m scripts.ops.morning_check --check-only --site https://mkp715.github.io/AAGrapevine
                                                         # on a computer: no token needed (nothing is started;
                                                         # the runs on GitHub are not looked at)

What it does
  1. Reads the LIVE site's /build.json (src/pages/build-info.11ty.js): today's build (its day in Central
     time) with today's Grapevine AND La Viña quotes = done — is_done(), the same test as morning.yml's
     first job.
  2. An Update & Deploy run already WAITING in the queue → follows it and never starts another: in the
     update-deploy concurrency group a new run would replace the waiting one.
  3. The live build is not today's (or cannot be read) → starts the morning refresh, follows it (to the
     run that replaced it, if GitHub replaced it in the queue) and waits until the live build.json shows
     that run's build (GitHub Pages can take a few minutes). A run that finished well but does not show
     within LIVE_MAX is "Cannot confirm" — never a reason to start another.
  4. Today's build is up but a quote is not today's (the magazine has not published it yet): from
     WINDOW_BEFORE before the goal until WINDOW_AFTER after it (4:00–7:00 AM for a 5:30 goal) it asks that
     magazine's home page every POLL_EVERY whether today's quote is out (quote.peek) — never sooner than
     POLL_EVERY after the last look, a run it started or followed included (every update reads the
     quote) — and once it is, starts the morning refresh again (at most MAX_RUNS refreshes a check).
     Before the window it stops (a later alarm or schedule asks again). A check that begins after the
     window (a late schedule, or someone pressing Run workflow) asks ONCE and starts the refresh if the
     quote is out. Otherwise — and at the end of the window — a yellow note that says when the magazine
     was last asked: the site shows yesterday's quote, labelled "Yesterday" (home.js), until an update
     brings the new one.
  5. Once today's update is on the site: on the 1st of the month (Central) before any full daily update of
     that day, and whenever none has run for CATCH_UP_AFTER (GitHub skipped or failed it), it also starts
     the full daily update — Update & Deploy with no inputs — without waiting for it; never while an
     Update & Deploy run waits or a full one runs, and not again within FULL_RETRY_AFTER of one that was
     started after the last full update (a full update that fails is tried again the next morning, not at
     every check). "The last full update" = the live /build.json `full` (status.json `full_update`: the
     newest `attempted` of the sources only the full update reads, run_all.FULL_ONLY) — morning.yml's
     first job applies the same rule (full_run_reason) to it, so this step runs even when today's update
     was already there.
  The run summary says when today's update went live ("on the site since 4:34 AM CDT — goal 5:30 AM"), or,
  when it was already there, when the latest build is from. A check that started, followed and asked
  nothing (the update was already there, or it was too early to ask a magazine) writes idle=true to
  $GITHUB_OUTPUT: morning.yml then runs its step "Nothing to do", and a later check's "tidy" job deletes
  the run a day later.

Politeness: aagrapevine.org / aalavina.org are asked only in step 4, only for a magazine whose quote on
OUR site is late — at most one page request per POLL_EVERY inside the window (16 from the alarm at 4:30 to
7:00 AM), and one per check after it — through the shared polite session (robots.txt first, 5 s apart): on
most mornings not at all. (The morning refresh itself reads each home page once: quote.py.)

Exit codes: 0 = today's update is on the site, or only a magazine's quote is late at the source, or the
site did not show a finished run yet ("Cannot confirm"), or --check-only; 1 = an update run failed, or did
not start or finish within FOLLOW_MAX (GitHub then e-mails whoever started this check — for the morning
alarm, the owner of its key; the runs this script starts are the bot's, and GitHub e-mails nobody about
those); 2 = no token, repository or site address.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from scripts.sync import quote
from scripts.sync.common import SITE_DIR, load_config, read_json
from scripts.sync.meeting import parse_hhmm

UPDATE_WF = "update.yml"
# The name of morning.yml's job that runs this script (its "tidy" job finds the no-op runs by it).
UPDATE_JOB = "Put today's update on the site"
# update.yml's run-name for a morning refresh — keep the two equal.
MORNING_TITLE = "Morning refresh: new day and daily quote"
GOAL = (5, 30)                               # config site.morning_goal when missing or unreadable
WINDOW_BEFORE = timedelta(minutes=90)        # the magazines are asked about a late quote from goal − 90 min …
WINDOW_AFTER = timedelta(minutes=90)         # … until goal + 90 min (after it: once per check)
POLL_EVERY = timedelta(minutes=10)           # one request per late magazine per POLL_EVERY
FOLLOW_MAX = timedelta(minutes=45)           # an update run must start AND finish within this
FOLLOW_EVERY = timedelta(seconds=20)
LIVE_MAX = timedelta(minutes=5)              # GitHub Pages shows a deploy within minutes
LIVE_EVERY = timedelta(seconds=15)
CATCH_UP_AFTER = timedelta(hours=30)         # no full daily update for this long → start one
FULL_RETRY_AFTER = timedelta(hours=12)       # a full update started (and not finished well) → not again before
MAX_RUNS = 3                                 # morning refreshes one check starts (the new day + 2 for a quote)
MAX_HOPS = 3                                 # replacements followed (GitHub's queue keeps one waiting run)
# A check starts no refresh and asks no magazine after this long: its last refresh — at most FOLLOW_MAX +
# LIVE_MAX, plus a few minutes of GitHub answering slowly — then still ends inside the 240 minutes that
# morning.yml gives the job, its setup included (tests/test_morning.py checks the sum). A check that
# begins at 4:00 AM therefore asks until 6:50; the alarm's, at 4:30, until 7:00.
GUARD_MAX = timedelta(minutes=170)
PUBS = quote.PUB_ORDER
PUB_NAMES = {"gv": "Grapevine", "lv": "La Viña"}
WAITING = ("queued", "pending", "waiting", "requested")
GITHUB_API = "https://api.github.com"
USER_AGENT = "NETA65-MorningCheck (+https://github.com/MKP715/AAGrapevine)"


# --------------------------------------------------------------------------- time
class Clock:
    """The real clock; tests pass a fake one (now() is aware UTC, sleep() advances it)."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def sleep(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds))


def parse_time(v: Any) -> datetime | None:
    """GitHub's / build.json's ISO times ('2026-09-29T09:33:41Z', '…41.780Z') → aware UTC datetime."""
    s = str(v or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def clock_label(d: datetime | None, tz: ZoneInfo) -> str:
    """'4:34 AM CDT' (the site's time zone; no platform-specific strftime flags)."""
    if d is None:
        return "?"
    loc = d.astimezone(tz)
    h = loc.hour % 12 or 12
    return f"{h}:{loc.minute:02d} {'AM' if loc.hour < 12 else 'PM'} {loc.tzname()}"


def day_label(d: date) -> str:
    """'Tuesday, September 29'."""
    return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}"


def minutes_label(seconds: float) -> str:
    """125 → '2 min 5 s'."""
    s = max(0, int(round(seconds)))
    return f"{s // 60} min {s % 60} s" if s >= 60 else f"{s} s"


# --------------------------------------------------------------------------- the live site
def is_done(live: dict | None, today: date | str) -> bool:
    """Today's update is on the site: the live build's Central day is today AND both quotes are dated today.
    The SAME test as the first job of .github/workflows/morning.yml ("Read the live site's build.json",
    in bash + jq) — keep the two equal."""
    t = today.isoformat() if isinstance(today, date) else str(today)
    if not isinstance(live, dict) or live.get("day") != t:
        return False
    quotes = live.get("quotes") if isinstance(live.get("quotes"), dict) else {}
    return all(quotes.get(p) == t for p in PUBS)


def late_pubs(live: dict | None, today: date) -> list[str]:
    """The magazines whose quote in the live build.json is not today's (all of them when it cannot be read)."""
    quotes = live.get("quotes") if isinstance(live, dict) and isinstance(live.get("quotes"), dict) else {}
    return [p for p in PUBS if quotes.get(p) != today.isoformat()]


def pub_names(pubs: list[str]) -> str:
    """['gv', 'lv'] → 'Grapevine and La Viña'."""
    return " and ".join(PUB_NAMES.get(p, p) for p in pubs)


def quotes_phrase(pubs: list[str]) -> str:
    """['lv'] → 'the La Viña quote is'; ['gv', 'lv'] → 'the Grapevine and La Viña quotes are'."""
    return f"the {pub_names(pubs)} quote{'s are' if len(pubs) > 1 else ' is'}"


def http_get(url: str, timeout: float = 20.0, tries: int = 3, sleep: Callable[[float], None] = time.sleep) -> str | None:
    """A plain GET of our OWN site (never the magazines' — those go through the polite session): the text,
    or None after `tries` failures."""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — https to our own site
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 — no answer, a 404, a broken connection: "cannot read it" (None)
            if attempt < tries:
                sleep(3 * attempt)
    return None


def read_live(site: str, get: Callable[[str], str | None] | None = None, clock: Clock | None = None) -> dict | None:
    """The live /build.json ({v, built, day, tz, quotes, data, full, run, version, commit}) or None (no
    answer, not JSON). `?check=<epoch>` keeps GitHub Pages' cache (10 minutes) from answering with an older
    copy."""
    clock = clock or Clock()
    url = f"{site.rstrip('/')}/build.json?check={int(clock.now().timestamp())}"
    text = (get or http_get)(url)
    if not text:
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


# --------------------------------------------------------------------------- GitHub
class GitHubError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


Send = Callable[[str, str, dict, "bytes | None", float], "tuple[int, bytes]"]


def urllib_send(method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> tuple[int, bytes]:
    """One HTTP request → (status, body); an HTTP error status is returned, not raised."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — https://api.github.com
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""


class GitHub:
    """The few REST calls the check needs (standard library only). `send` is the HTTP transport (tests pass
    a fake one); a network error or a 5xx answer is tried 3 times."""

    def __init__(self, repo: str, token: str, api: str = GITHUB_API, send: Send | None = None,
                 clock: Clock | None = None, ref: str = "main"):
        self.repo, self.token, self.api = repo, token, api.rstrip("/")
        self.send = send or urllib_send
        self.clock = clock or Clock()
        self.ref = ref or "main"

    def request(self, method: str, path: str, body: dict | None = None, query: dict | None = None) -> tuple[int, Any]:
        url = f"{self.api}/repos/{self.repo}/{path.lstrip('/')}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": USER_AGENT}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        last = None
        for attempt in range(1, 4):
            try:
                status, raw = self.send(method, url, headers, data, 30.0)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = f"{type(e).__name__}: {e}"
                if attempt < 3:
                    self.clock.sleep(5 * attempt)
                continue
            if status >= 500 and attempt < 3:
                last = f"HTTP {status}"
                self.clock.sleep(5 * attempt)
                continue
            try:
                doc = json.loads(raw.decode("utf-8")) if raw else None
            except ValueError:
                doc = None
            return status, doc
        raise GitHubError(f"{method} {path}: {last}")

    def get(self, path: str, **query) -> Any:
        status, doc = self.request("GET", path, query=query or None)
        if status != 200:
            raise GitHubError(f"GET {path}: HTTP {status} {message_of(doc)}".strip(), status)
        return doc

    def runs(self, wf: str, **query) -> list[dict]:
        """The workflow's runs, newest first (GitHub's order)."""
        doc = self.get(f"actions/workflows/{wf}/runs", **query) or {}
        return [r for r in doc.get("workflow_runs") or [] if isinstance(r, dict)]

    def run(self, run_id: int) -> dict:
        return self.get(f"actions/runs/{run_id}") or {}

    def dispatch(self, wf: str, inputs: dict, title: str | None = None) -> int | None:
        """Start `wf` on self.ref → the new run's id (None when it cannot be found). GitHub answers the
        dispatch with the run's id when asked to (`return_run_details`, 2026); an answer without it (204),
        or a refusal of that field (422 naming it — then the dispatch is sent again without it), is followed
        by a look at the newest workflow_dispatch runs (created from 10 s before the request on, for up to
        60 s; with `title`, only a run of that name)."""
        t0 = self.clock.now()
        body = {"ref": self.ref, "inputs": dict(inputs), "return_run_details": True}
        status, doc = self.request("POST", f"actions/workflows/{wf}/dispatches", body)
        if status == 422 and "return_run_details" in message_of(doc):
            body.pop("return_run_details")
            status, doc = self.request("POST", f"actions/workflows/{wf}/dispatches", body)
        if status == 200 and isinstance(doc, dict) and doc.get("workflow_run_id"):
            return int(doc["workflow_run_id"])
        if status not in (200, 204):
            raise GitHubError(f"could not start {wf}: HTTP {status} {message_of(doc)}".strip(), status)
        since = t0 - timedelta(seconds=10)
        deadline = t0 + timedelta(seconds=60)
        while True:
            for r in self.runs(wf, event="workflow_dispatch", per_page=10):
                created = parse_time(r.get("created_at"))
                if created and created >= since and (not title or r.get("display_title") == title):
                    return int(r["id"])
            if self.clock.now() >= deadline:
                return None
            self.clock.sleep(5)


def message_of(doc: Any) -> str:
    return str(doc.get("message") or "") if isinstance(doc, dict) else ""


def active(gh: GitHub) -> tuple[list[dict], list[dict]]:
    """Update & Deploy runs (waiting, running) — each newest first."""
    runs = gh.runs(UPDATE_WF, per_page=20)
    return ([r for r in runs if r.get("status") in WAITING], [r for r in runs if r.get("status") == "in_progress"])


def follow(gh: GitHub, run_id: int, clock: Clock) -> dict:
    """Waits for an Update & Deploy run to finish → the run (GitHub's fields) + `timed_out`, `hops`.
    A run that GitHub cancelled because a newer one took its place in the queue is followed to that one
    (every mode reads the daily quote), at most MAX_HOPS times. Gives up after FOLLOW_MAX."""
    deadline = clock.now() + FOLLOW_MAX
    hops = 0
    while True:
        r = gh.run(run_id)
        if r.get("status") == "completed":
            if r.get("conclusion") == "cancelled" and hops < MAX_HOPS:
                newer = replacement(gh, r)
                if newer:
                    run_id, hops = int(newer["id"]), hops + 1
                    continue
            return {**r, "timed_out": False, "hops": hops}
        if clock.now() >= deadline:
            return {**r, "timed_out": True, "hops": hops}
        clock.sleep(FOLLOW_EVERY.total_seconds())


def replacement(gh: GitHub, cancelled: dict) -> dict | None:
    """The Update & Deploy run that took a cancelled one's place: the oldest run created after it that was
    not cancelled itself."""
    after = parse_time(cancelled.get("created_at"))
    later = [r for r in gh.runs(UPDATE_WF, per_page=20)
             if r.get("id") != cancelled.get("id") and after and (parse_time(r.get("created_at")) or after) > after
             and not (r.get("status") == "completed" and r.get("conclusion") == "cancelled")]
    return min(later, key=lambda r: parse_time(r.get("created_at"))) if later else None


def wait_live(site: str, run: dict, today: date, clock: Clock,
              get: Callable[[str], str | None] | None = None) -> tuple[dict | None, bool]:
    """Reads the live build.json every LIVE_EVERY for up to LIVE_MAX until it shows the build of the finished
    run `run` — it names that run, or it was built after the run was created (Update & Deploy runs one at a
    time, so a later run's build carries this one's data too) — or today's update is complete → (the last
    build.json read, whether it showed it). (None, False): the site never answered."""
    since = parse_time(run.get("created_at")) or clock.now()
    rid = str(run.get("id") or "")
    deadline = clock.now() + LIVE_MAX
    last = None
    while True:
        live = read_live(site, get, clock)
        if live is not None:
            last = live
            built = parse_time(live.get("built"))
            if is_done(live, today) or (rid and str(live.get("run") or "") == rid) or (built and built >= since):
                return live, True
        if clock.now() >= deadline:
            return last, False
        clock.sleep(LIVE_EVERY.total_seconds())


# --------------------------------------------------------------------------- the magazines
def peek(late: list[str], today: date, fetch: Callable[[str], str | None] | None = None,
         cfg: dict | None = None) -> dict[str, str | None]:
    """{pub: the day of the quote its home page shows now} for the late magazines only — quote.peek through
    the shared polite session (robots.txt, 5 s apart; reuse=False: always the page as it is now)."""
    if fetch is None:
        from scripts.sync.common import shared_session
        fetch = lambda url: shared_session().get_text(url, reuse=False)  # noqa: E731
    return quote.peek(fetch, today, tuple(late), cfg)


# --------------------------------------------------------------------------- the full daily update
def last_full_update(live: dict | None, status: dict | None = None) -> datetime | None:
    """When the last FULL daily update ran: the live /build.json `full` — the value morning.yml's first job
    decided on — else, when the live site could not be read, data/site/status.json `full_update` of this
    checkout (both: the newest `attempted` of the sources only the full update reads, run_all.FULL_ONLY →
    build_data.build_status). None: not known."""
    got = parse_time(live.get("full")) if isinstance(live, dict) else None
    return got or (parse_time(status.get("full_update")) if isinstance(status, dict) else None)


def full_run_reason(last: datetime | None, now: datetime, tz: ZoneInfo) -> str:
    """Why the full daily update should start now ("" = it should not), given when the last one ran (None:
    not known → never): the 1st of the month (Central) before any full update of that day — last month is
    then complete in the site data (the monthly digest waits for it) — or none for CATCH_UP_AFTER. The
    SAME rule as the first job of .github/workflows/morning.yml (bash, on /build.json `full`) — keep the
    two equal (tests/test_morning.py runs both on the same times)."""
    if last is None:
        return ""
    local = now.astimezone(tz)
    midnight = datetime(local.year, local.month, local.day, tzinfo=tz)
    if local.day == 1 and last < midnight:
        return "the 1st of the month"
    if now - last > CATCH_UP_AFTER:
        hours = int((now - last).total_seconds() // 3600)
        return f"no full update for {hours} hours"
    return ""


def maybe_full_run(gh: GitHub | None, last: datetime | None, now: datetime, tz: ZoneInfo, report: "Report",
                   start: bool = True) -> bool:
    """Starts the full daily update (not followed) when full_run_reason() says so → whether it started one.
    Not while an Update & Deploy run waits (a new one would replace it) or a full one runs, and not when one
    was already started by Run workflow (any run that is not a morning refresh) after the last full update
    and within FULL_RETRY_AFTER: it is still to finish, or it failed — then it is tried again the next
    morning, not at every check."""
    why = full_run_reason(last, now, tz)
    if not why:
        return False
    if not start or gh is None:
        report.row("Full daily update", f"would be started ({why})")
        return False
    try:
        waiting, running = active(gh)
        if waiting or any(r.get("display_title") != MORNING_TITLE for r in running):
            report.row("Full daily update", f"not started ({why}): another Update & Deploy run is waiting or running")
            return False
        since = max(last, now - FULL_RETRY_AFTER) if last else now - FULL_RETRY_AFTER
        tried = [r for r in gh.runs(UPDATE_WF, event="workflow_dispatch", per_page=20)
                 if r.get("display_title") != MORNING_TITLE and (parse_time(r.get("created_at")) or since) > since]
        if tried:
            r = tried[0]
            report.row("Full daily update", f"not started ({why}): one was started at "
                       f"{clock_label(parse_time(r.get('created_at')), tz)} — {run_link(gh, r.get('id'), r)}; the next try "
                       f"is {int(FULL_RETRY_AFTER.total_seconds() // 3600)} hours after it")
            return False
        rid = gh.dispatch(UPDATE_WF, {})
    except GitHubError as e:
        report.annotate("warning", "Full update not started", f"The full daily update ({why}) could not be started: {e}")
        return False
    link = run_link(gh, rid)
    report.row("Full daily update", f"started ({why}){' — ' + link if link else ''}")
    return True


# --------------------------------------------------------------------------- the run summary
def run_link(gh: GitHub | None, run_id: int | None, run: dict | None = None) -> str:
    if run and run.get("html_url"):
        return f"[run {run.get('id') or run_id}]({run['html_url']})"
    if gh is None or not run_id:
        return ""
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    return f"[run {run_id}]({server}/{gh.repo}/actions/runs/{run_id})"


class Report:
    """The run summary ($GITHUB_STEP_SUMMARY) and the annotations (a red ✗ / yellow note on the run page).
    `idle`: this check started, followed and asked nothing — written to $GITHUB_OUTPUT (idle=true|false):
    morning.yml then runs its step "Nothing to do", by which a later check's "tidy" job knows the run and
    deletes it a day later."""

    def __init__(self, today: date, tz: ZoneInfo, goal_at: datetime):
        self.today, self.tz, self.goal_at = today, tz, goal_at
        self.headline = ""
        self.rows: list[tuple[str, str]] = []
        self.notes: list[str] = []
        self.idle = False

    def say(self, text: str) -> None:
        print(text, flush=True)

    def annotate(self, level: str, title: str, message: str) -> None:
        msg = " ".join(str(message).split()).replace("%", "%25")
        print(f"::{level} title={title}::{msg}", flush=True)
        self.notes.append(f"{'⚠️' if level == 'warning' else '❌' if level == 'error' else 'ℹ️'} **{title}:** {message}")

    def row(self, what: str, value: str) -> None:
        self.rows.append((what, value))
        self.say(f"{what}: {value}")

    def live_rows(self, live: dict | None) -> None:
        if not isinstance(live, dict):
            self.row("Live site", "build.json could not be read")
            return
        t = self.today.isoformat()
        self.row("New day", f"{'✅' if live.get('day') == t else '⏳'} built {clock_label(parse_time(live.get('built')), self.tz)}"
                            f" ({live.get('day') or '?'})")
        quotes = live.get("quotes") if isinstance(live.get("quotes"), dict) else {}
        for p in PUBS:
            d = str(quotes.get(p) or "")
            self.row(f"{PUB_NAMES.get(p, p)} quote", f"{'✅' if d == t else '⏳'} {d or 'none'}")

    def write(self) -> None:
        lines = [f"## Morning check — {day_label(self.today)} (Central time)", ""]
        if self.headline:
            lines += [self.headline, ""]
        if self.rows:
            lines += ["| | |", "|---|---|", *[f"| {a} | {str(b).replace('|', '/')} |" for a, b in self.rows], ""]
        lines += [*self.notes]
        text = "\n".join(lines).rstrip() + "\n"
        for var, content in (("GITHUB_STEP_SUMMARY", text), ("GITHUB_OUTPUT", f"idle={'true' if self.idle else 'false'}\n")):
            path = os.environ.get(var)
            if path:
                try:
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(content)
                except OSError:
                    pass
        self.say("\n" + text)


def console_safe() -> None:
    """A console that cannot show the summary's ✅ / 🔎 (a Windows one, cp1252) prints '?' for them instead of
    stopping with an error; GitHub's runner (PYTHONIOENCODING=utf-8) shows them as they are."""
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError, OSError):      # not a real console (a test's StringIO), or closed
        pass


# --------------------------------------------------------------------------- main
def settings(cfg: dict) -> tuple[ZoneInfo, tuple[int, int]]:
    site = cfg.get("site") or {}
    try:
        tz = ZoneInfo(site.get("timezone") or "America/Chicago")
    except Exception:  # noqa: BLE001
        tz = ZoneInfo("America/Chicago")
    return tz, parse_hhmm(site.get("morning_goal"), GOAL)


def main(argv: list[str] | None = None, *, clock: Clock | None = None, gh: GitHub | None = None,
         get: Callable[[str], str | None] | None = None, fetch: Callable[[str], str | None] | None = None,
         cfg: dict | None = None, status: dict | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.ops.morning_check", description=__doc__.split("\n\n")[0])
    ap.add_argument("--check-only", action="store_true",
                    help="only say what is on the site and what would be done (starts nothing; no token needed)")
    ap.add_argument("--site", help="the site's address (default: env SITE_URL, else site.url in config/site.yml)")
    a = ap.parse_args(argv)
    console_safe()
    env = os.environ
    check_only = a.check_only or str(env.get("CHECK_ONLY", "")).lower() == "true"
    clock = clock or Clock()
    cfg = cfg if cfg is not None else load_config()
    tz, goal = settings(cfg)
    now = clock.now()
    today = now.astimezone(tz).date()
    goal_at = datetime(today.year, today.month, today.day, goal[0], goal[1], tzinfo=tz)
    poll_from, poll_until = goal_at - WINDOW_BEFORE, goal_at + WINDOW_AFTER
    report = Report(today, tz, goal_at)
    goal_label = clock_label(goal_at, tz).rsplit(" ", 1)[0]          # "5:30 AM"

    site = (a.site or env.get("SITE_URL") or str((cfg.get("site") or {}).get("url") or "")).strip().rstrip("/")
    repo, token = env.get("GITHUB_REPOSITORY", ""), env.get("GH_TOKEN") or env.get("GITHUB_TOKEN") or ""
    if not site:
        report.annotate("error", "No site address", "Give --site, or set SITE_URL or site.url in config/site.yml.")
        return 2
    if gh is None and token and repo:
        gh = GitHub(repo, token, env.get("GITHUB_API_URL", GITHUB_API), clock=clock, ref=env.get("GITHUB_REF_NAME") or "main")
    if gh is None and not check_only:
        report.annotate("error", "No GitHub access", "GH_TOKEN and GITHUB_REPOSITORY are needed to start Update & Deploy"
                        " (run it with --check-only on a computer).")
        return 2
    if status is None:
        status = read_json(Path(SITE_DIR) / "status.json", {}) or {}
    event = env.get("GITHUB_EVENT_NAME", "")
    started_by = (f"GitHub's schedule ({env.get('SCHEDULE')})" if event == "schedule" and env.get("SCHEDULE")
                  else "GitHub's schedule" if event == "schedule"
                  else "Run workflow (the morning alarm or a person)" if event == "workflow_dispatch"
                  else "a computer (not GitHub)" if not event else event)
    report.say(f"Morning check {now.isoformat(timespec='seconds')} — today is {today} (Central), goal {goal_label}, "
               f"site {site}{' — LOOK ONLY' if check_only else ''}")

    def full_run(live: dict | None) -> bool:
        """Step 5: the full daily update, if it is due → whether one was started."""
        return maybe_full_run(gh, last_full_update(live, status), clock.now(), tz, report, start=not check_only)

    def success(live: dict, how: str, run: dict | None = None, seen: bool = True) -> int:
        """Today's update is on the site. `seen`: this check saw it arrive (a run it started or followed, or
        the live site changing while it watched), so the build's time is when it went live. Otherwise it was
        already there, and the live build may be a later one (the midday refresh, a push): its time is only
        "the latest build", and it says nothing about the goal."""
        built = parse_time(live.get("built"))
        if seen:
            report.headline = f"✅ Today's update is on the site since **{clock_label(built, tz)}** — goal {goal_label}."
        else:
            report.headline = f"✅ Today's update is on the site — the latest build is from **{clock_label(built, tz)}**."
        report.live_rows(live)
        if run:
            took = ""
            s, e = parse_time(run.get("run_started_at") or run.get("created_at")), parse_time(run.get("updated_at"))
            if s and e and e >= s:
                took = f" — {minutes_label((e - s).total_seconds())}"
            report.row("Update & Deploy", f"{run_link(gh, run.get('id'), run)}{took}")
        report.row("Started by", started_by)
        if how:
            report.row("How", how)
        if seen and built and built > goal_at:
            report.annotate("warning", "After the goal", f"Today's update went live at {clock_label(built, tz)} — "
                            f"after the {goal_label} goal.")
        started = full_run(live)
        report.idle = not seen and not started and not check_only       # nothing started, followed or asked
        report.write()
        return 0

    live = read_live(site, get, clock)
    if is_done(live, today):
        return success(live, "It was already there — no morning refresh needed.", seen=False)

    waiting, running = [], []
    if gh is not None:
        try:
            waiting, running = active(gh)
        except GitHubError as e:
            if not check_only:
                report.annotate("error", "GitHub did not answer", f"The Update & Deploy runs could not be listed: {e}")
                report.write()
                return 1
            report.say(f"(the runs on GitHub could not be listed: {e})")

    if check_only:
        # The same decisions as the check itself (below) — with one question per late magazine at most.
        report.headline = "🔎 Look only — nothing was started."
        report.live_rows(live)
        if gh is None:
            report.row("Update & Deploy runs", "not looked at (no token)")
        else:
            report.row("Update & Deploy runs", f"{len(waiting)} waiting, {len(running)} running")
        if waiting:
            plan = f"follow the waiting Update & Deploy run {waiting[0].get('id')} (a new run would replace it)"
        elif not live or live.get("day") != today.isoformat():
            plan = "start the morning refresh (the live site is not today's build)"
        else:
            late = late_pubs(live, today)
            if now < poll_from:
                plan = f"nothing yet: {quotes_phrase(late)} not today's, and it is too early to ask (from {clock_label(poll_from, tz)})"
            else:
                shown = peek(late, today, fetch, cfg)
                out = [p for p in late if shown.get(p) == today.isoformat()]
                report.row("The magazines' pages now", ", ".join(f"{PUB_NAMES.get(p, p)}: {shown.get(p) or 'no dated quote'}" for p in late))
                if out:
                    plan = f"start the morning refresh: today's {pub_names(out)} quote is out"
                elif now + POLL_EVERY <= poll_until:
                    plan = f"ask again in {int(POLL_EVERY.total_seconds() // 60)} minutes (until {clock_label(poll_until, tz)})"
                else:
                    plan = (f"a yellow note: {quotes_phrase(late)} not out yet (after {clock_label(poll_until, tz)} each "
                            "check asks once; the next update brings it)")
        report.row("Would", plan)
        full_run(live)
        report.write()
        return 0

    t_start = now
    poll_end = min(poll_until, t_start + GUARD_MAX)      # this check asks the magazines until then

    def guard() -> int:
        nonlocal live, waiting, running
        runs_started, asks = 0, 0
        last_run: dict | None = None
        # When this check last saw the magazines' pages: its own question (peek), or a run it started or
        # followed (every update reads the daily quote). It asks again POLL_EVERY later — never at once.
        last_look: datetime | None = None
        missed: list[str] = []        # out on the magazine's page, but the refresh this check started did not bring it

        def late_note(late: list[str]) -> int:
            """The asking is over and a quote is still not today's → the summary with a yellow note, exit 0."""
            report.live_rows(live)
            if last_run:
                report.row("Update & Deploy", run_link(gh, last_run.get("id"), last_run))
            report.row("Started by", started_by)
            if missed:
                report.headline = f"⚠️ Today's build is on the site; {quotes_phrase(missed)} out, but the update did not get it."
                refreshes = "the morning refresh" if runs_started == 1 else f"{runs_started} morning refreshes"
                report.annotate("warning", "A daily quote could not be read",
                                f"The {pub_names(missed)} page shows today's quote, but {refreshes} did not bring it to the "
                                "site — see the quote step in the last Update & Deploy run's log.")
            else:
                report.headline = f"⚠️ Today's build is on the site, but {quotes_phrase(late)} late at the source."
                asked = (f"when last asked, at {clock_label(last_look, tz)}" if last_look
                         else f"(not asked: this check ran for {int(GUARD_MAX.total_seconds() // 60)} minutes)")
                report.annotate("warning", "A daily quote is late at the source",
                                f"{pub_names(late)} had not published today's quote{'s' if len(late) > 1 else ''} {asked}; the site "
                                "shows the last one, labelled \"Yesterday\", until an update brings the new one — the next "
                                "one, or Actions → Morning check → Run workflow once it is out.")
            full_run(live)
            report.write()
            return 0

        def too_early(late: list[str]) -> int:
            report.headline = (f"⏳ Today's build is on the site; {quotes_phrase(late)} not out yet. The magazines are "
                               f"asked from {clock_label(poll_from, tz)} — a later check looks again.")
            report.live_rows(live)
            if last_run:
                report.row("Update & Deploy", run_link(gh, last_run.get("id"), last_run))
            report.row("Started by", started_by)
            report.idle = last_run is None                  # nothing started, followed or asked
            report.write()
            return 0

        def not_shown(r: dict, shown_live: dict | None) -> int:
            """A run finished well (its deploy included), but the live site does not show it after LIVE_MAX:
            never another run for that — GitHub Pages is slow or in trouble. A yellow note, exit 0."""
            report.headline = "⚠️ The update finished, but the live site does not show it yet."
            report.live_rows(shown_live)
            report.row("Update & Deploy", run_link(gh, r.get("id"), r))
            report.row("Started by", started_by)
            still = ("could not be read" if shown_live is None else
                     f"still shows the build of {clock_label(parse_time(shown_live.get('built')), tz)} ({shown_live.get('day') or '?'})")
            report.annotate("warning", "Cannot confirm", f"The Update & Deploy run finished, but the site's build.json {still} "
                            f"after {int(LIVE_MAX.total_seconds() // 60)} minutes (GitHub Pages trouble?) — look at the site.")
            full_run(shown_live or live)
            report.write()
            return 0

        def wait_to_ask(late: list[str]) -> int | None:
            """Waits until the magazines may be asked again — POLL_EVERY after the last look — → None (the
            loop reads the site and the queue, then asks); or, when that would be after the window, or this
            check is past it already (its one question after the window is asked), ends with the yellow note.
            Never a wait past the window: the job's time is kept for a last refresh."""
            t = clock.now()
            nxt = (last_look or t) + POLL_EVERY
            if t > poll_end or nxt > poll_end:
                return late_note(late)
            clock.sleep((nxt - t).total_seconds())
            return None

        while True:
            now = clock.now()
            if waiting:
                # Never start a run while one waits: it would take the waiting run's place in the queue.
                if now - t_start > GUARD_MAX:
                    return failed(report, gh, last_run, started_by, live, "Update & Deploy runs kept waiting in the queue for "
                                  f"{int(GUARD_MAX.total_seconds() // 60)} minutes")
                r = follow(gh, int(waiting[0]["id"]), clock)
                last_run = r
                if r.get("timed_out") or r.get("conclusion") != "success":
                    return failed(report, gh, r, started_by, live)
                live2, shown = wait_live(site, r, today, clock, get)
                last_look = clock.now()
                if not shown:
                    return not_shown(r, live2)
                live = live2
                if is_done(live, today):
                    return success(live, "Followed the Update & Deploy run that was already waiting.", r)
            elif not live or live.get("day") != today.isoformat():
                # The NEW DAY first — even before the quote is out.
                if now - t_start > GUARD_MAX:
                    return failed(report, gh, last_run, started_by, live, "today's build was still not on the site after "
                                  f"{int(GUARD_MAX.total_seconds() // 60)} minutes")
                r = start_and_follow(gh, clock, report)
                runs_started += 1
                last_run = r
                if r is None or r.get("timed_out") or r.get("conclusion") != "success":
                    return failed(report, gh, r, started_by, live)
                live2, shown = wait_live(site, r, today, clock, get)
                last_look = clock.now()
                if not shown:
                    return not_shown(r, live2)
                live = live2
                if is_done(live, today):
                    return success(live, "Started the morning refresh.", r)
            else:
                # Today's build is up; a magazine's quote is not today's yet.
                late = late_pubs(live, today)
                if now < poll_from:
                    return too_early(late)
                if last_look is not None and now < last_look + POLL_EVERY:
                    # a run this check started or followed has just read the pages: ask POLL_EVERY after it
                    end = wait_to_ask(late)
                    if end is not None:
                        return end
                elif now > poll_end and (last_look is not None or now - t_start > GUARD_MAX):
                    return late_note(late)
                else:
                    # in the window — or this check began after it: then this is its one question
                    shown_now = peek(late, today, fetch, cfg)
                    asks += 1
                    last_look, missed = now, []
                    out = [p for p in late if shown_now.get(p) == today.isoformat()]
                    report.say(f"{clock_label(now, tz)}: " + ", ".join(
                        f"{PUB_NAMES.get(p, p)}'s page shows {shown_now.get(p) or 'no dated quote'}" for p in late))
                    if out and runs_started >= MAX_RUNS:
                        missed = out
                        return late_note(late)
                    if out:
                        r = start_and_follow(gh, clock, report)
                        runs_started += 1
                        last_run = r
                        if r is None or r.get("timed_out") or r.get("conclusion") != "success":
                            return failed(report, gh, r, started_by, live)
                        live2, shown = wait_live(site, r, today, clock, get)
                        last_look = clock.now()
                        if not shown:
                            return not_shown(r, live2)
                        live = live2
                        if is_done(live, today):
                            what = f"the {pub_names(out)} quote{'s' if len(out) > 1 else ''}"
                            how = (f"Waited for {what}, then started the morning refresh." if asks > 1
                                   else f"Found {what} out, then started the morning refresh.")
                            return success(live, how, r)
                        late = late_pubs(live, today)
                        missed = [p for p in out if p in late]
                    end = wait_to_ask(late)
                    if end is not None:
                        return end
            # look again: the live site, and the queue
            live = read_live(site, get, clock) or live
            if is_done(live, today):
                return success(live, "Today's update arrived.", last_run)
            try:
                waiting, running = active(gh)
            except GitHubError as e:
                report.say(f"(the runs on GitHub could not be listed: {e})")
                waiting, running = [], []

    try:
        return guard()
    except GitHubError as e:      # GitHub stopped answering while the check followed a run
        return failed(report, gh, None, started_by, live, f"GitHub did not answer: {e}")


def start_and_follow(gh: GitHub, clock: Clock, report: Report) -> dict | None:
    """Starts the morning refresh and follows it → the finished run; {"conclusion": "not started", "error": …}
    when GitHub refused to start it; None when it started but its run could not be found."""
    try:
        rid = gh.dispatch(UPDATE_WF, {"morning": "true"}, MORNING_TITLE)
    except GitHubError as e:
        hint = (" — is Update & Deploy switched off? Actions → Update & Deploy → Enable workflow"
                if e.status in (403, 404, 422) else "")
        return {"id": None, "conclusion": "not started", "timed_out": False, "error": f"{e}{hint}"}
    if rid is None:
        return None
    report.say(f"Started the morning refresh: run {rid}")
    return follow(gh, rid, clock)


def failed(report: Report, gh: GitHub | None, run: dict | None, started_by: str, live: dict | None,
           why: str = "") -> int:
    """A red ✗: today's update did not reach the site (GitHub e-mails whoever started this check)."""
    link = run_link(gh, (run or {}).get("id"), run) if run and run.get("id") else ""
    if not why:
        if run is None:
            why = "the morning refresh was started but its run could not be found"
        elif run.get("timed_out"):
            state = "still waiting to start" if run.get("status") in WAITING else "still running"
            why = f"the Update & Deploy run is {state} after {int(FOLLOW_MAX.total_seconds() // 60)} minutes"
        elif run.get("conclusion") == "not started":
            why = f"Update & Deploy could not be started: {run.get('error') or '?'}"
        else:
            why = f"the Update & Deploy run ended \"{run.get('conclusion') or run.get('status') or '?'}\""
    report.headline = "❌ Today's update did not reach the site."
    report.live_rows(live)
    if link:
        report.row("Update & Deploy", link)
    report.row("Started by", started_by)
    report.annotate("error", "Morning update failed", f"{why}{' — ' + link if link else ''}.")
    report.write()
    return 1


if __name__ == "__main__":
    sys.exit(main())
