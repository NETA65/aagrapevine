"""The Morning check: the new day and both daily quotes on the website by the goal — config/site.yml →
site.morning_goal, 5:30 AM Central — every day. It is the job "Put today's update on the site" of
.github/workflows/morning.yml (that workflow's first job, "look", already found the live site behind, or
the full daily update due).

Why it exists: GitHub starts scheduled runs when it has room — since late August 2026 often 4 to 8 hours
late, and a busy day can skip one — while a run started through the API (workflow_dispatch) starts within
seconds, and a morning refresh is live about 3 minutes later. So this script starts Website update itself
in MORNING mode (update.yml input `morning` → run_all --morning), follows it and reads the live site.

    python -m scripts.ops.morning_check                  # on GitHub (GH_TOKEN, GITHUB_REPOSITORY, SITE_URL)
    python -m scripts.ops.morning_check --check-only     # say what is on the site and what would be done
    python -m scripts.ops.morning_check --check-only --site https://neta65.github.io/aagrapevine
                                                         # on a computer: no token needed (nothing is started;
                                                         # the runs on GitHub are not looked at)

What it does
  1. Reads the LIVE site's /build.json (src/pages/build-info.11ty.js): today's build (its day in Central
     time) with today's Grapevine AND La Viña quotes = done — is_done(), the same test as morning.yml's
     first job.
  2. A Website update run already WAITING in the queue → follows it and never starts another: in the
     update-deploy concurrency group a new run would replace the waiting one. A Website update run already
     RUNNING when this check is about to start a morning refresh (steps 3 and 4), or while a run waits behind
     it — the full daily update (on the 1st, step 5 of an earlier check starts it), a push's, a person's —
     is followed first, for as long as this check may act (GUARD_MAX): the group runs one at a time, so a
     refresh started now would only wait in the queue until it ends, which for a full update or a long
     search of the magazines is longer than FOLLOW_MAX (a false red ✗ while today's update was on its way).
     Every run reads the daily quotes and builds the new day; once it has ended the check reads the site
     and the queue and decides again, and starts a refresh only for what that run did not bring.
  3. The live build is not today's (or cannot be read) → starts the morning refresh, follows it (to the
     run that replaced it, if GitHub replaced it in the queue) and waits until the live build.json shows
     that run's build (GitHub Pages can take a few minutes). A run that finished well but does not show
     within LIVE_MAX is "Cannot confirm" — never a reason to start another.
  4. Today's build is up but a quote is not today's (the magazine has not published it yet): from
     WINDOW_BEFORE before the goal until WINDOW_AFTER after it (4:00–7:00 AM for a 5:30 goal) it asks that
     magazine's home page every POLL_EVERY whether today's quote is out (quote.peek) — never sooner than
     POLL_EVERY after the last look, a run it started or followed included (every update reads the
     quote) — and once it is, starts the morning refresh again. Before the window it stops (a later alarm
     or schedule asks again). A check that begins after the window (a late schedule, or someone pressing
     Run workflow) asks ONCE and starts the refresh if the quote is out. Otherwise — and at the end of the
     window — a yellow note that says when the magazine was last asked: the site shows yesterday's quote,
     labelled "Yesterday" (home.js), until an update brings the new one.
  In steps 3 and 4 together a check starts at most MAX_RUNS morning refreshes, never two without POLL_EVERY
  between them (each refresh reads both magazines' home pages), and none after GUARD_MAX.
  "Today" is the Central day of each moment, not of the check's start: a check still running at midnight
  (a late evening firing, a run that waited in the queue) works for the NEW day from then on — the new
  day's build is today's build, and its goal and asking window apply (right after midnight a late quote is
  "too early to ask": the morning's checks ask). The run summary is then about the new day, with a
  "Began" row that says so.
  5. Once today's update is on the site: on the 1st of the month (Central) before any full daily update of
     that day, and whenever none has run for CATCH_UP_AFTER (GitHub skipped or failed it), it also starts
     the full daily update — Website update with no inputs — without waiting for it; never while a
     Website update run waits or a full one runs, and not again within FULL_RETRY_AFTER of a full update (a
     run titled as one — FULL_TITLES; a quick refresh does not count) that was started after the last full
     update (a full update that fails is tried again the next morning, not at every check). "The last full
     update" = the live /build.json `full` (status.json `full_update`: the newest `attempted` of the sources
     only the full update reads, run_all.FULL_ONLY) — morning.yml's first job applies the same rule
     (full_run_reason) to it, so this step runs even when today's update was already there.
  The run summary says when today's update went live ("on the site since 4:34 AM CDT — goal 5:30 AM"), or,
  when it was already there, when the latest build is from. A check that started, followed and asked
  nothing (the update was already there, or it was too early to ask a magazine) writes idle=true to
  $GITHUB_OUTPUT: morning.yml then runs its step "Nothing to do", and a later check's "tidy" job deletes
  the run a day later.

Politeness: aagrapevine.org / aalavina.org are asked only in step 4, only for a magazine whose quote on
OUR site is late — at most one page request per POLL_EVERY inside the window (16 from the alarm at 4:30 to
7:00 AM), and one per check after it — through the shared polite session (robots.txt first, 5 s apart): on
most mornings not at all. (The morning refresh itself reads each home page once: quote.py.)

Exit codes: 0 = today's update is on the site, or only a magazine's quote is late at the source (also when
an update this check did not start was still running at GUARD_MAX, with today's build on the site), or the
site did not show a finished run yet ("Cannot confirm"), or --check-only; 1 = an update run failed, or did
not start or finish within FOLLOW_MAX, or today's build was still not on the site after MAX_RUNS morning
refreshes or GUARD_MAX — a run this check did not start still running then included (GitHub then e-mails
whoever started this check — for the morning alarm, the owner of its key; the runs this script starts are
the bot's, and GitHub e-mails nobody about those); 2 = no token, repository or site address.
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
# update.yml's run-names of a FULL update ("Full update (started by hand)", "Full update (started by the Morning
# check)", "Full update without the document search (started by hand)", "Nightly full update (GitHub schedule)") —
# a quick one is "Quick refresh …", "Midday refresh …" or "Evening refresh …".
FULL_TITLES = ("Full update", "Nightly full update")
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
MAX_RUNS = 3                                 # morning refreshes one check starts, in all (the new day + 2 for a quote)
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
USER_AGENT = "NETA65-MorningCheck (+https://github.com/NETA65/aagrapevine)"


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
    """Website update runs (waiting, running) — each newest first."""
    runs = gh.runs(UPDATE_WF, per_page=20)
    return ([r for r in runs if r.get("status") in WAITING], [r for r in runs if r.get("status") == "in_progress"])


def follow(gh: GitHub, run_id: int, clock: Clock, limit: timedelta = FOLLOW_MAX) -> dict:
    """Waits for a Website update run to finish → the run (GitHub's fields) + `timed_out`, `hops`.
    A run that GitHub cancelled because a newer one took its place in the queue is followed to that one
    (every mode reads the daily quote), at most MAX_HOPS times. Gives up after `limit`: FOLLOW_MAX for a run
    this check started or found waiting (it must start AND finish within it); a run found already running
    is followed for as long as the check may still act (main → follow_running)."""
    deadline = clock.now() + limit
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
    """The Website update run that took a cancelled one's place: the oldest run created after it that was
    not cancelled itself."""
    after = parse_time(cancelled.get("created_at"))
    later = [r for r in gh.runs(UPDATE_WF, per_page=20)
             if r.get("id") != cancelled.get("id") and after and (parse_time(r.get("created_at")) or after) > after
             and not (r.get("status") == "completed" and r.get("conclusion") == "cancelled")]
    return min(later, key=lambda r: parse_time(r.get("created_at"))) if later else None


def wait_live(site: str, run: dict, today: date, clock: Clock,
              get: Callable[[str], str | None] | None = None) -> tuple[dict | None, bool]:
    """Reads the live build.json every LIVE_EVERY for up to LIVE_MAX until it shows the build of the finished
    run `run` — it names that run, or it was built after the run was created (Website update runs one at a
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
    decided on — else, when the live site cannot say (it could not be read, or its build.json has no `full`
    yet: a build from before the field existed), data/site/status.json `full_update` of this checkout (both:
    the newest `attempted` of the sources only the full update reads, run_all.FULL_ONLY →
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


def is_full_title(title: Any) -> bool:
    """A run titled as a full update (FULL_TITLES)."""
    return str(title or "").startswith(FULL_TITLES)


def maybe_full_run(gh: GitHub | None, last: datetime | None, now: datetime, tz: ZoneInfo, report: "Report",
                   start: bool = True) -> bool:
    """Starts the full daily update (not followed) when full_run_reason() says so → whether it started one.
    Not while a Website update run waits (a new one would replace it) or runs (any but a morning refresh: it may
    be a full one), and not when a full update was already started by Run workflow (a run titled as one,
    is_full_title — not a quick or a morning refresh) after the last full update and within FULL_RETRY_AFTER: it
    is still to finish, or it failed — then it is tried again the next morning, not at every check."""
    why = full_run_reason(last, now, tz)
    if not why:
        return False
    if not start or gh is None:
        report.row("Full daily update", f"would be started ({why})")
        return False
    try:
        waiting, running = active(gh)
        if waiting or any(r.get("display_title") != MORNING_TITLE for r in running):
            report.row("Full daily update", f"not started ({why}): another Website update run is waiting or running")
            return False
        since = max(last, now - FULL_RETRY_AFTER) if last else now - FULL_RETRY_AFTER
        tried = [r for r in gh.runs(UPDATE_WF, event="workflow_dispatch", per_page=20)
                 if is_full_title(r.get("display_title")) and (parse_time(r.get("created_at")) or since) > since]
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
    deletes it a day later. `today` / `goal_at` follow the day (main → new_day); `began`, set when the day
    turned while the check ran, is the table's last row."""

    def __init__(self, today: date, tz: ZoneInfo, goal_at: datetime):
        self.today, self.tz, self.goal_at = today, tz, goal_at
        self.headline = ""
        self.rows: list[tuple[str, str]] = []
        self.notes: list[str] = []
        self.idle = False
        self.began = ""

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
        rows = self.rows + ([("Began", self.began)] if self.began else [])
        if rows:
            lines += ["| | |", "|---|---|", *[f"| {a} | {str(b).replace('|', '/')} |" for a, b in rows], ""]
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
        report.annotate("error", "No GitHub access", "GH_TOKEN and GITHUB_REPOSITORY are needed to start the Website "
                        "update workflow (run it with --check-only on a computer).")
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
        already there, and the live build may be a later one (a midday or evening refresh, a push): its time
        is only "the latest build", and it says nothing about the goal."""
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
            report.row("Website update", f"{run_link(gh, run.get('id'), run)}{took}")
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
                report.annotate("error", "GitHub did not answer", f"The Website update runs could not be listed: {e}")
                report.write()
                return 1
            report.say(f"(the runs on GitHub could not be listed: {e})")

    if check_only:
        # The same decisions as the check itself (below) — with one question per late magazine at most.
        report.headline = "🔎 Look only — nothing was started."
        report.live_rows(live)
        if gh is None:
            report.row("Website update runs", "not looked at (no token)")
        else:
            report.row("Website update runs", f"{len(waiting)} waiting, {len(running)} running")
        # a run already running: a refresh (or the waiting run) would only start when it ends — followed first
        first = (f"follow the running Website update run {running[0].get('id')} (a morning refresh would wait behind "
                 "it), then ") if running else ""
        if waiting and running:
            plan = f"{first}the waiting one, then decide again"
        elif waiting:
            plan = f"follow the waiting Website update run {waiting[0].get('id')} (a new run would replace it)"
        elif not live or live.get("day") != today.isoformat():
            plan = (f"{first}start the morning refresh if the site is still not today's build" if running
                    else "start the morning refresh (the live site is not today's build)")
        else:
            late = late_pubs(live, today)
            if now < poll_from:
                plan = f"nothing yet: {quotes_phrase(late)} not today's, and it is too early to ask (from {clock_label(poll_from, tz)})"
            else:
                shown = peek(late, today, fetch, cfg)
                out = [p for p in late if shown.get(p) == today.isoformat()]
                report.row("The magazines' pages now", ", ".join(f"{PUB_NAMES.get(p, p)}: {shown.get(p) or 'no dated quote'}" for p in late))
                if out and running:
                    plan = f"{first}start the morning refresh if it did not bring today's {pub_names(out)} quote (it is out)"
                elif out:
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

    t_start, start_day = now, today
    poll_end = min(poll_until, t_start + GUARD_MAX)      # this check asks the magazines until then

    def new_day(t: datetime) -> bool:
        """Is `t` on a later Central day than `today`? Then the check works for that day from now on: a check
        still running at midnight (a late evening firing, a run that waited in the queue) must take the new
        day's build as today's — its day check alone would otherwise start a refresh at every look until
        GUARD_MAX — and the new day's goal and asking window apply (right after midnight a late quote is
        "too early to ask"; the morning's checks ask). The run summary is then about the new day, and its
        "Began" row says when the check began."""
        nonlocal today, goal_at, poll_from, poll_until, poll_end
        d = t.astimezone(tz).date()
        if d <= today:
            return False
        today = d
        goal_at = datetime(d.year, d.month, d.day, goal[0], goal[1], tzinfo=tz)
        poll_from, poll_until = goal_at - WINDOW_BEFORE, goal_at + WINDOW_AFTER
        poll_end = min(poll_until, t_start + GUARD_MAX)
        report.today, report.goal_at = today, goal_at
        report.began = f"{day_label(start_day)}, {clock_label(t_start, tz)} — the day turned at midnight while it ran"
        report.say(f"{clock_label(t, tz)}: a new day, {day_label(d)} — this check works for it from now on")
        return True

    def guard() -> int:
        nonlocal live, waiting, running
        runs_started, asks = 0, 0
        last_run: dict | None = None
        # When this check last saw the magazines' pages: its own question (peek), or a run it started or
        # followed (every update reads the daily quote). It asks again POLL_EVERY later — never at once — and
        # starts no refresh sooner than that after it either.
        last_look: datetime | None = None
        missed: list[str] = []        # out on the magazine's page, but the refresh this check started did not bring it
        # Out on the magazine's page while a Website update run was RUNNING: the refresh that brings it waits
        # until that run has ended (follow_running) — and is started only if that run did not bring it.
        pending: list[str] = []
        waited = False                # this check followed a run that was already running (the "How" row says so)
        followed: set[int] = set()    # those runs: a listing that still calls one running (GitHub's lag) is not followed again

        def turned() -> bool:
            """new_day() for this moment — a new day forgets `missed` and `pending` (the day before's quotes)."""
            nonlocal missed, pending
            if not new_day(clock.now()):
                return False
            missed, pending = [], []
            return True

        def late_note(late: list[str]) -> int:
            """The asking is over and a quote is still not today's → the summary with a yellow note, exit 0."""
            report.live_rows(live)
            if last_run:
                report.row("Website update", run_link(gh, last_run.get("id"), last_run))
            report.row("Started by", started_by)
            if missed and not runs_started:
                # out on the page, but this check's time was over when the run it waited for had ended
                report.headline = f"⚠️ Today's build is on the site; {quotes_phrase(missed)} out, but the update did not get it."
                report.annotate("warning", "A daily quote is waiting for an update",
                                f"The {pub_names(missed)} page shows today's quote, but the Website update run that was "
                                "running did not bring it, and this check's "
                                f"{int(GUARD_MAX.total_seconds() // 60)} minutes were over before a morning refresh could "
                                "start — the next update brings it (or Actions → Morning check (new day by 5:30 AM) → Run "
                                "workflow).")
            elif missed:
                report.headline = f"⚠️ Today's build is on the site; {quotes_phrase(missed)} out, but the update did not get it."
                refreshes = "the morning refresh" if runs_started == 1 else f"{runs_started} morning refreshes"
                report.annotate("warning", "A daily quote could not be read",
                                f"The {pub_names(missed)} page shows today's quote, but {refreshes} did not bring it to the "
                                "site — see the quote step in the last Website update run's log.")
            else:
                report.headline = f"⚠️ Today's build is on the site, but {quotes_phrase(late)} late at the source."
                asked = (f"when last asked, at {clock_label(last_look, tz)}" if last_look
                         else f"(not asked: this check ran for {int(GUARD_MAX.total_seconds() // 60)} minutes)")
                report.annotate("warning", "A daily quote is late at the source",
                                f"{pub_names(late)} had not published today's quote{'s' if len(late) > 1 else ''} {asked}; the site "
                                "shows the last one, labelled \"Yesterday\", until an update brings the new one — the next "
                                "one, or Actions → Morning check (new day by 5:30 AM) → Run workflow once it is out.")
            full_run(live)
            report.write()
            return 0

        def too_early(late: list[str]) -> int:
            report.headline = (f"⏳ Today's build is on the site; {quotes_phrase(late)} not out yet. The magazines are "
                               f"asked from {clock_label(poll_from, tz)} — a later check looks again.")
            report.live_rows(live)
            if last_run:
                report.row("Website update", run_link(gh, last_run.get("id"), last_run))
            report.row("Started by", started_by)
            report.idle = last_run is None                  # nothing started, followed or asked
            report.write()
            return 0

        def not_shown(r: dict, shown_live: dict | None) -> int:
            """A run finished well (its deploy included), but the live site does not show it after LIVE_MAX:
            never another run for that — GitHub Pages is slow or in trouble. A yellow note, exit 0."""
            report.headline = "⚠️ The update finished, but the live site does not show it yet."
            report.live_rows(shown_live)
            report.row("Website update", run_link(gh, r.get("id"), r))
            report.row("Started by", started_by)
            still = ("could not be read" if shown_live is None else
                     f"still shows the build of {clock_label(parse_time(shown_live.get('built')), tz)} ({shown_live.get('day') or '?'})")
            report.annotate("warning", "Cannot confirm", f"The Website update run finished, but the site's build.json {still} "
                            f"after {int(LIVE_MAX.total_seconds() // 60)} minutes (GitHub Pages trouble?) — look at the site.")
            full_run(shown_live or live)
            report.write()
            return 0

        def held_up(r: dict) -> int:
            """GUARD_MAX came while this check waited for a Website update run it did not start (follow_running):
            a long search of the magazines, a slow full update. A morning refresh would still only wait behind
            it. Today's build on the site → a yellow note, exit 0 (that run, or the next update, brings the
            quote); not → a red ✗ that says why."""
            began = clock_label(parse_time(r.get("run_started_at") or r.get("created_at")), tz)
            still = (f"a Website update run this check did not start (running since {began}) was still running when "
                     f"this check's {int(GUARD_MAX.total_seconds() // 60)} minutes were over")
            if not live or live.get("day") != today.isoformat():
                return failed(report, gh, r, started_by, live, f"{still} — a morning refresh cannot start before it ends")
            late = late_pubs(live, today)
            report.headline = f"⚠️ Today's build is on the site; {quotes_phrase(late)} not on it yet — an update is still running."
            report.live_rows(live)
            report.row("Website update", f"{run_link(gh, r.get('id'), r)} — running since {began}")
            report.row("Started by", started_by)
            first = quotes_phrase(late)
            what = (f"The {pub_names(pending)} page shows today's quote, but" if pending      # asked: it is out
                    else f"{first[0].upper()}{first[1:]} not on the site yet, and")
            report.annotate("warning", "An update is still running",
                            f"{what} {still}, and a morning refresh would only wait behind it. The site shows the last "
                            "quote, labelled \"Yesterday\", until an update brings the new one — that run, if it read the "
                            "magazine's page after the quote came out, or the next one (Actions → Morning check (new day "
                            "by 5:30 AM) → Run workflow once it has ended).")
            full_run(live)
            report.write()
            return 0

        def follow_running() -> int | None:
            """A Website update run is RUNNING, and this check is about to start a morning refresh — or to follow
            a run that waits behind it: either would only start once the running one ends (update.yml's
            concurrency group runs one at a time; cancel-in-progress is off) — for a full daily update or a long
            search of the magazines, later than FOLLOW_MAX: a false red ✗ while today's update was on its way.
            Every run reads the daily quotes and builds the new day, so the running one is followed instead, for
            as long as this check may act (GUARD_MAX) → None: it has ended, and the loop reads the site and the
            queue and decides again — a refresh only for what it did not bring (its look at the magazines'
            pages counts from when it started). Or an exit code: today's update came with it, the site does not
            show it (not_shown), or it was still running at GUARD_MAX (held_up)."""
            nonlocal live, last_run, last_look, waited
            r0 = running[0]
            began = parse_time(r0.get("run_started_at") or r0.get("created_at")) or clock.now()
            left = t_start + GUARD_MAX - clock.now()
            if left <= timedelta(0):
                return held_up(r0)
            report.say(f"{clock_label(clock.now(), tz)}: following run {r0.get('id')} ({r0.get('display_title') or 'Website update'},"
                       f" running since {clock_label(began, tz)}) — a morning refresh started now would wait behind it")
            r = follow(gh, int(r0["id"]), clock, left)
            last_run, waited = r, True
            followed.update(int(x) for x in (r0.get("id"), r.get("id")) if x)
            if r.get("timed_out"):
                return held_up(r)
            last_look = max(last_look, began) if last_look else began
            if r.get("conclusion") != "success":
                # someone else's run that failed: this check goes on with its own refresh (the loop decides)
                report.row("Waited for", f"{run_link(gh, r.get('id'), r)} — it ended \"{r.get('conclusion') or r.get('status') or '?'}\"")
                return None
            live2, shown = wait_live(site, r, today, clock, get)
            if not shown:
                return not_shown(r, live2)
            live = live2
            turned()
            if is_done(live, today):
                return success(live, "Followed the Website update run that was already running.", r)
            return None

        def wait_to_ask(late: list[str]) -> int | None:
            """Waits until the magazines may be asked again — POLL_EVERY after the last look — → None (the
            loop reads the site and the queue, then asks); or, when that would be after the window, or this
            check is past it already (its one question after the window is asked), ends with the yellow note.
            Never a wait past the window: the job's time is kept for a last refresh. Before the window — the
            day turned while a refresh ran, and the new day's build is up — it ends like a check that began
            too early."""
            t = clock.now()
            if t < poll_from:
                return too_early(late)
            nxt = (last_look or t) + POLL_EVERY
            if t > poll_end or nxt > poll_end:
                return late_note(late)
            clock.sleep((nxt - t).total_seconds())
            return None

        def refresh_for(out: list[str]) -> int | None:
            """Today's build is up and the quotes `out` are out on the magazines' pages: starts the morning refresh
            (at most MAX_RUNS in all — then the yellow note), follows it and reads the site → an exit code, or
            None: the loop reads the site and the queue again (the next question POLL_EVERY after this look —
            or the day turned while the refresh ran, and the new day comes first)."""
            nonlocal live, last_run, last_look, missed, runs_started
            if runs_started >= MAX_RUNS:
                missed = out
                return late_note(late_pubs(live, today))
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
            day_turned = turned()
            if is_done(live, today):
                what = f"the {pub_names(out)} quote{'s' if len(out) > 1 else ''}"
                how = (f"Found {what} out, waited for the Website update run that was running, then started the morning "
                       "refresh." if waited else f"Waited for {what}, then started the morning refresh." if asks > 1
                       else f"Found {what} out, then started the morning refresh.")
                return success(live, how, r)
            late = late_pubs(live, today)
            # a quote found out on the day before is no news about the new day's
            missed = [] if day_turned else [p for p in out if p in late]
            # Today's build: the next question POLL_EVERY after this look. (The day turned while the refresh ran
            # and the site shows the day before's build: the site and the queue are read again, then the new
            # day comes first.)
            return wait_to_ask(late) if live.get("day") == today.isoformat() else None

        while True:
            turned()
            now = clock.now()
            new_day_missing = not live or live.get("day") != today.isoformat()
            if running and (waiting or new_day_missing or pending):
                # A run is going on: whatever this pass would start or follow must wait for it — so it goes first.
                end = follow_running()
                if end is not None:
                    return end
            elif waiting:
                # Never start a run while one waits: it would take the waiting run's place in the queue.
                if now - t_start > GUARD_MAX:
                    return failed(report, gh, last_run, started_by, live, "Website update runs kept waiting in the queue for "
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
                turned()
                if is_done(live, today):
                    return success(live, "Followed the Website update run that was already waiting.", r)
            elif new_day_missing:
                # The NEW DAY first — even before the quote is out.
                if now - t_start > GUARD_MAX:
                    return failed(report, gh, last_run, started_by, live, "today's build was still not on the site after "
                                  f"{int(GUARD_MAX.total_seconds() // 60)} minutes")
                if runs_started >= MAX_RUNS:
                    return failed(report, gh, last_run, started_by, live, "today's build was still not on the site after "
                                  f"{runs_started} morning refreshes")
                if last_look is not None and now < last_look + POLL_EVERY:
                    # A run this check started or followed has just read the magazines' pages, and the site still
                    # does not show today's build (the day turned at midnight since): the next refresh waits
                    # until POLL_EVERY after it — then the site and the queue are read again (below).
                    clock.sleep((last_look + POLL_EVERY - now).total_seconds())
                else:
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
                    turned()
                    if is_done(live, today):
                        return success(live, "Started the morning refresh.", r)
            else:
                # Today's build is up; a magazine's quote is not today's yet.
                late = late_pubs(live, today)
                pending = [p for p in pending if p in late]
                if pending:
                    # Out on the page while an update was running; that run has ended without bringing it: the
                    # refresh now — POLL_EVERY after the last look at the pages, and never after GUARD_MAX.
                    if now - t_start > GUARD_MAX:
                        missed = pending
                        return late_note(late)
                    if last_look is not None and now < last_look + POLL_EVERY:
                        clock.sleep((last_look + POLL_EVERY - now).total_seconds())      # then the site and the queue
                    else:
                        out, pending = pending, []
                        end = refresh_for(out)
                        if end is not None:
                            return end
                elif now < poll_from:
                    return too_early(late)
                elif last_look is not None and now < last_look + POLL_EVERY:
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
                    if out and running:
                        # a refresh started now would only wait behind the running update: the loop follows it first
                        pending = out
                    else:
                        end = refresh_for(out) if out else wait_to_ask(late)
                        if end is not None:
                            return end
            # look again: the live site, and the queue
            live = read_live(site, get, clock) or live
            turned()
            if is_done(live, today):
                return success(live, "Today's update arrived.", last_run)
            try:
                waiting, running = active(gh)
                running = [r for r in running if int(r.get("id") or 0) not in followed]
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
        hint = (" — is the Website update workflow switched off? Actions → Website update → Enable workflow"
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
            why = f"the Website update run is {state} after {int(FOLLOW_MAX.total_seconds() // 60)} minutes"
        elif run.get("conclusion") == "not started":
            why = f"the Website update workflow could not be started: {run.get('error') or '?'}"
        else:
            why = f"the Website update run ended \"{run.get('conclusion') or run.get('status') or '?'}\""
    report.headline = "❌ Today's update did not reach the site."
    report.live_rows(live)
    if link:
        report.row("Website update", link)
    report.row("Started by", started_by)
    report.annotate("error", "Morning update failed", f"{why}{' — ' + link if link else ''}.")
    report.write()
    return 1


if __name__ == "__main__":
    sys.exit(main())
