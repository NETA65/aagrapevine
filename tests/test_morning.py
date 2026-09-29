"""The Morning check — the new day and both daily quotes on the site by 5:30 AM Central (config
site.morning_goal) every day, while GitHub starts its own schedules hours late:

  * MorningWorkflow  — .github/workflows/morning.yml: a plain-UTC schedule (no `timezone:`, never on the
                       hour, 01–11 UTC), the one input, one check at a time, least privilege, the job names
                       the script and the tidy job rely on, the packages it installs;
  * FastPathParity   — its first job's bash + curl + jq test of the live build.json says "done" exactly
                       when morning_check.is_done() does (skipped without bash, curl and jq);
  * Tidy             — its "tidy" job deletes only its own green no-op runs older than a day, at most 50
                       (run against a stand-in for `gh`; skipped without bash and jq);
  * UpdateWorkflow   — update.yml: the two schedules unchanged, the `morning` input and run-name, the plan
                       step's modes and budgets, the sync flags, the commit messages, the run summary;
  * RunAllMorning    — run_all --morning: the quick sources, plus the monthly ones on the 1st and the 15th;
  * Guard            — scripts/ops/morning_check.py against a stand-in GitHub, site, clock and magazines:
                       what it starts, follows, waits for and reports, and its exit codes;
  * FullRun          — when it also starts the full daily update (the 1st; a skipped day);
  * BuildInfo        — /build.json (src/pages/build-info.11ty.js), run in Node.js;
  * QuoteDays        — status.json quote_days (build_data) and the /status/ view of it (freshness.js).

    python -m unittest tests.test_morning -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import ast
import copy
import http.server
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodejs import run_js  # noqa: E402
from scripts.ops import morning_check as MC  # noqa: E402
from scripts.sync import build_data as B  # noqa: E402
from scripts.sync import run_all  # noqa: E402

WF = ROOT / ".github" / "workflows"
CHICAGO = ZoneInfo("America/Chicago")
FIX = Path(__file__).parent / "fixtures" / "quote"


def load_wf(name: str) -> tuple[dict, dict]:
    doc = yaml.safe_load((WF / name).read_text(encoding="utf-8"))
    return doc, doc.get("on", doc.get(True))          # PyYAML reads the key `on:` as True


def step_run(job: dict, name: str) -> str:
    found = [s for s in job.get("steps", []) if s.get("name") == name]
    assert len(found) == 1, f"one step named {name!r}"
    return found[0].get("run") or ""


def step_of(job: dict, name: str) -> dict:
    return next(s for s in job.get("steps", []) if s.get("name") == name)


def expand(field: str, lo: int, hi: int) -> set[int]:
    """One cron field ("25", "1-11", "*/2", "7,19") → the values it fires on."""
    out: set[int] = set()
    for part in field.split(","):
        rng, _, every = part.partition("/")
        a, b = (lo, hi) if rng == "*" else tuple(map(int, rng.split("-"))) if "-" in rng else (int(rng), int(rng))
        out.update(range(a, b + 1, int(every or 1)))
    return out


def iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bash_path() -> str | None:
    """A bash that runs the workflows' scripts here: Linux / macOS bash, or Git Bash on Windows — never
    WSL's launcher in System32 (another file system)."""
    b = shutil.which("bash")
    if b and not (os.name == "nt" and "\\windows\\" in b.lower()):
        return b
    if os.name == "nt":
        for cand in (r"C:\Program Files\Git\usr\bin\bash.exe", r"C:\Program Files\Git\bin\bash.exe"):
            if Path(cand).exists():
                return cand
    return None


def tz_prefix(bash: str) -> str | None:
    """How a script here names Central time: "America/Chicago" when the system knows it (Linux, macOS);
    Git Bash on Windows has no time zone files, so the tzdata package's own copy (":<path>") instead."""
    r = subprocess.run([bash, "-c", "TZ=America/Chicago date +%Z"], capture_output=True, text=True)
    if r.stdout.strip() in ("CDT", "CST"):
        return "America/Chicago"
    import importlib.util
    spec = importlib.util.find_spec("tzdata")               # the zoneinfo data Python uses on Windows
    if spec is None or not spec.origin:
        return None
    f = Path(spec.origin).parent / "zoneinfo" / "America" / "Chicago"
    if not f.exists():
        return None
    p = f.as_posix()
    if re.match(r"^[A-Za-z]:/", p):
        p = "/" + p[0].lower() + p[2:]                 # C:/… → /c/… (Git Bash)
    r = subprocess.run([bash, "-c", f"TZ=':{p}' date +%Z"], capture_output=True, text=True)
    return f":{p}" if r.stdout.strip() in ("CDT", "CST") else None


def run_bash(bash: str, script: str, env: dict, cwd: Path | None = None) -> subprocess.CompletedProcess:
    full = {**os.environ, **env}
    # python and the tools found next to it (the venv's) first
    full["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), full.get("PATH", "")])
    return subprocess.run([bash, "-c", script], cwd=cwd or ROOT, env=full, capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


def shim_bin(tmp: Path) -> Path:
    """A folder to put first on PATH: on Windows a `jq` that writes plain LF line ends (jq.exe writes CRLF,
    which bash keeps in a list of ids), so the workflows' scripts run here as on the GitHub runner."""
    d = tmp / "shim"
    d.mkdir(exist_ok=True)
    jq = shutil.which("jq")
    if os.name == "nt" and jq:
        (d / "jq").write_text(f'#!/usr/bin/env bash\nexec "{Path(jq).as_posix()}" -b "$@"\n', encoding="utf-8", newline="\n")
    return d


def outputs(path: Path) -> dict[str, str]:
    """A $GITHUB_OUTPUT file → {name: value} (the last value wins)."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


# --------------------------------------------------------------------------- morning.yml
class MorningWorkflow(unittest.TestCase):
    def setUp(self):
        self.wf, self.on = load_wf("morning.yml")
        self.jobs = self.wf["jobs"]

    def test_schedule_is_plain_utc_off_the_hour_through_the_night(self):
        firings = set()
        for s in self.on["schedule"]:
            self.assertEqual(set(s), {"cron"}, "plain UTC: no timezone key")
            minute, hour, dom, mon, dow = s["cron"].split()
            self.assertNotEqual(minute, "*")
            mins, hours = expand(minute, 0, 59), expand(hour, 0, 23)
            self.assertNotIn(0, mins, "never on the hour (GitHub's busiest minute)")
            self.assertEqual((dom, mon, dow), ("*", "*", "*"))
            firings |= {(h, m) for h in hours for m in mins}
        self.assertGreaterEqual(len(firings), 2)
        self.assertLessEqual(set(range(1, 12)), {h for h, _m in firings}, "firings from 01 to 11 UTC")
        self.assertEqual([s["cron"] for s in self.on["schedule"]], ["25 1-11 * * *"])
        # the early morning in Central time, summer (UTC−5) and winter (UTC−6): 4 and 5 AM are both covered
        for offset in (5, 6):
            self.assertLessEqual({4, 5}, {(h - offset) % 24 for h, _m in firings})

    def test_the_only_input_is_check_only(self):
        inputs = self.on["workflow_dispatch"]["inputs"]
        self.assertEqual(list(inputs), ["check_only"])
        self.assertEqual((inputs["check_only"]["type"], inputs["check_only"]["default"]), ("boolean", False))
        self.assertNotIn("push", self.on)

    def test_one_check_at_a_time(self):
        self.assertEqual(self.wf["concurrency"], {"group": "morning-check", "cancel-in-progress": False})
        self.assertNotIn("queue", self.wf["concurrency"])

    def test_least_privilege(self):
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        self.assertEqual(self.jobs["look"]["permissions"], {"pages": "read"})
        self.assertEqual(self.jobs["update"]["permissions"], {"actions": "write", "contents": "read"})
        self.assertEqual(self.jobs["tidy"]["permissions"], {"actions": "write"})
        text = (WF / "morning.yml").read_text(encoding="utf-8")
        self.assertNotIn("secrets.", text, "only the built-in github.token")
        self.assertEqual(set(re.findall(r"\$\{\{\s*github\.token\s*\}\}", text)), {"${{ github.token }}"})

    def test_every_checkout_in_every_workflow_keeps_no_credentials(self):
        for f in sorted(WF.glob("*.yml")):
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            for jname, job in doc["jobs"].items():
                for s in job.get("steps", []):
                    if str(s.get("uses", "")).startswith("actions/checkout@"):
                        with self.subTest(workflow=f.name, job=jname):
                            self.assertIs((s.get("with") or {}).get("persist-credentials"), False)

    def test_update_job(self):
        job = self.jobs["update"]
        self.assertEqual(job["name"], MC.UPDATE_JOB)
        self.assertEqual(job["needs"], "look")
        # it runs when the site lacks today's update, and when it has it but the full update is due
        self.assertEqual(job["if"], "${{ !cancelled() && (needs.look.outputs.done != 'true' || needs.look.outputs.full != '') }}")
        self.assertEqual(job["timeout-minutes"], 240)
        run = step_run(job, "Start the morning update, follow it, check the live site")
        self.assertIn('python -m scripts.ops.morning_check "${args[@]}"', run)
        self.assertIn('if [ "${CHECK_ONLY:-false}" = "true" ]; then args+=(--check-only); fi', run)
        st = step_of(job, "Start the morning update, follow it, check the live site")
        self.assertEqual(st["id"], "check")
        env = st["env"]
        self.assertEqual(env["GH_TOKEN"], "${{ github.token }}")
        self.assertEqual(env["SITE_URL"], "${{ needs.look.outputs.site }}")
        self.assertEqual(env["CHECK_ONLY"], "${{ inputs.check_only }}")
        # The guard's own time limits fit in the job's: its last refresh may start at GUARD_MAX and take
        # FOLLOW_MAX + LIVE_MAX (never a sleep after it: the window is over) — plus 10 minutes for the
        # job's setup (checkout, Python, five packages) and GitHub answering slowly.
        worst = MC.GUARD_MAX + MC.FOLLOW_MAX + MC.LIVE_MAX + timedelta(minutes=10)
        self.assertLessEqual(worst, timedelta(minutes=job["timeout-minutes"]))
        # a check that did nothing ends at a step of its own, by which "tidy" deletes the run later
        idle = step_of(job, "Nothing to do (deleted a day later)")
        self.assertEqual(idle["if"], "${{ steps.check.outputs.idle == 'true' }}")

    def test_its_own_pip_cache(self):
        # five packages only: its cache must never stand in for the full one under requirements.txt's key
        py = step_of(self.jobs["update"], "Set up Python")["with"]
        self.assertEqual(py["cache"], "pip")
        self.assertEqual(py["cache-dependency-path"].split(), ["requirements.txt", ".github/workflows/morning.yml"])
        for f in sorted(WF.glob("*.yml")):
            if f.name == "morning.yml":
                continue
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            for job in doc["jobs"].values():
                for s in job.get("steps", []):
                    if str(s.get("uses", "")).startswith("actions/setup-python@") and (s.get("with") or {}).get("cache"):
                        with self.subTest(workflow=f.name):
                            self.assertNotIn("morning.yml", str(s["with"].get("cache-dependency-path")))

    def test_look_job(self):
        job = self.jobs["look"]
        self.assertEqual(job["outputs"], {"done": "${{ steps.live.outputs.done }}", "full": "${{ steps.live.outputs.full }}",
                                          "site": "${{ steps.site.outputs.url }}"})
        self.assertFalse(any("uses" in s for s in job["steps"]), "no checkout: a few seconds")
        run = step_run(job, "Read the live site's build.json")
        self.assertIn('"${SITE}/build.json?check=$(date +%s)"', run)
        self.assertIn("is_done() in scripts/ops/morning_check.py", run)
        self.assertIn("full_run_reason() there", run)

    def test_tidy_job(self):
        job = self.jobs["tidy"]
        self.assertEqual(job["needs"], "look")
        self.assertEqual(job["if"], "${{ always() }}")
        self.assertFalse(any("uses" in s for s in job["steps"]), "no checkout")
        st = step_of(job, "Delete this workflow's no-op runs older than a day")
        self.assertEqual(st["env"]["UPDATE_JOB"], MC.UPDATE_JOB)
        self.assertEqual(st["env"]["WORKFLOW_FILE"], "morning.yml")
        self.assertEqual(st["env"]["MAX_DELETE"], "50")
        # the update job's "nothing to do" step, found by its name
        self.assertEqual(st["env"]["IDLE_STEP"], step_of(self.jobs["update"], st["env"]["IDLE_STEP"])["name"])
        run = st["run"]
        for bit in ("date -u -d '24 hours ago'", "status=success", '.conclusion == "success"', "::notice title=Tidy::",
                    "gh api -X DELETE", '.[0].conclusion == "skipped"', "select(.name == $idle and .conclusion == \"success\")"):
            self.assertIn(bit, run)
        self.assertNotRegex(run, r"(?m)^\s*set -e", "a problem is a notice, never a failed run")

    def test_packages_it_installs_are_the_ones_it_imports(self):
        run = step_run(self.jobs["update"], "Install Python packages (the polite session and the quote reader)")
        pat = re.search(r"grep -iE '([^']+)' requirements\.txt", run).group(1)
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        picked = {re.split(r"[<>=!~ ]", ln, maxsplit=1)[0].lower() for ln in req if re.search(pat, ln, re.I)}
        self.assertEqual(picked, {"requests", "beautifulsoup4", "lxml", "protego", "pyyaml"})
        # every outside package the Morning check's modules import (lxml is BeautifulSoup's parser, by name)
        pkg = {"requests": "requests", "bs4": "beautifulsoup4", "yaml": "pyyaml", "protego": "protego", "lxml": "lxml"}
        used = set()
        for f in ("scripts/ops/morning_check.py", "scripts/sync/quote.py", "scripts/sync/common.py",
                  "scripts/sync/meeting.py"):
            for node in ast.walk(ast.parse((ROOT / f).read_text(encoding="utf-8"))):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else [])
                for n in names:
                    top = n.split(".")[0]
                    if top != "scripts" and top not in sys.stdlib_module_names and top != "__future__":
                        used.add(top)
        self.assertLessEqual({pkg.get(u, u) for u in used}, picked, used)

    def test_run_names(self):
        self.assertIn("'Morning check (GitHub schedule)'", self.wf["run-name"])
        self.assertIn("'Morning check (look only)'", self.wf["run-name"])


# --------------------------------------------------------------------------- the fast path (bash)
class _Serve:
    """build.json from a local web server: `body` None = 404."""

    def __init__(self):
        self.body: str | None = None
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if urlsplit(self.path).path != "/build.json" or owner.body is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                data = owner.body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class FastPathParity(unittest.TestCase):
    """morning.yml's first job decides "done" with bash + curl + jq; the script with is_done(). Same answer."""

    def setUp(self):
        self.bash = bash_path()
        if not self.bash or not shutil.which("curl") or not shutil.which("jq"):
            self.skipTest("needs bash, curl and jq (the GitHub runner has them)")
        self.tz = tz_prefix(self.bash)
        if not self.tz:
            self.skipTest("this bash does not know Central time")
        wf, _on = load_wf("morning.yml")
        self.script = step_run(wf["jobs"]["look"], "Read the live site's build.json").replace("TZ=America/Chicago", f"TZ='{self.tz}'")
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-look-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.server = _Serve()
        self.addCleanup(self.server.close)

    def look_at(self, site: str, env: dict | None = None, first: list[str] | None = None) -> tuple[dict, str, str]:
        """Runs the step → ($GITHUB_OUTPUT as a dict, the summary, what it printed). `first`: folders put
        before everything else on PATH (a stand-in `date`)."""
        out, summary = self.tmp / "out.txt", self.tmp / "summary.md"
        out.write_text("", encoding="utf-8")
        summary.write_text("", encoding="utf-8")
        path = os.pathsep.join([*(first or []), str(shim_bin(self.tmp)), os.environ.get("PATH", "")])
        r = run_bash(self.bash, self.script, {"SITE": site, "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(summary),
                                              "PATH": path, **(env or {})})
        self.assertEqual(r.returncode, 0, r.stderr)
        return outputs(out), summary.read_text(encoding="utf-8"), r.stdout

    def look(self, site: str) -> tuple[str, str, str]:
        got, summary, log = self.look_at(site)
        return got.get("done", ""), summary, log

    def test_same_answer_as_is_done(self):
        now = datetime.now(timezone.utc)
        t = now.astimezone(CHICAGO).date()
        today, yesterday = t.isoformat(), (t - timedelta(days=1)).isoformat()
        built = iso(now - timedelta(minutes=3))
        variants = {
            "done": {"v": 1, "built": built, "day": today, "tz": "America/Chicago", "quotes": {"gv": today, "lv": today}},
            "yesterday": {"v": 1, "built": built, "day": yesterday, "quotes": {"gv": yesterday, "lv": yesterday}},
            "old La Viña quote": {"v": 1, "built": built, "day": today, "quotes": {"gv": today, "lv": yesterday}},
            "no quotes": {"v": 1, "built": built, "day": today, "quotes": {}},
            "old day, new quotes": {"v": 1, "built": built, "day": yesterday, "quotes": {"gv": today, "lv": today}},
            "missing": None,
            "garbage": "{ not json",
            "a list": "[1, 2]",
        }
        for name, v in variants.items():
            with self.subTest(variant=name):
                self.server.body = v if v is None or isinstance(v, str) else json.dumps(v)
                done, summary, _log = self.look(self.server.url)
                parsed = v if isinstance(v, dict) else None
                self.assertIn(done, ("true", "false"))
                self.assertEqual(done == "true", MC.is_done(parsed, today))
                if done == "true":
                    self.assertRegex(summary, r"Nothing to do: today's update \(built \d{1,2}:\d\d [AP]M C[DS]T, with today's "
                                              r"Grapevine and La Viña quotes\) is on the site\.")
                else:
                    self.assertEqual(summary, "")
        self.assertEqual(self.look("")[0], "false", "no site address: the next job looks closer")

    def test_the_full_update_rule_is_full_run_reason(self):
        # The same build.json at fixed moments (a stand-in `date` answers FAKE_NOW unless it is asked about
        # another time): "full" says what full_run_reason() says — the 1st of the month before any full
        # update that day (in daylight saving time and in winter), 30 hours without one, and nothing when
        # the time is not known or not a time.
        real = subprocess.run([self.bash, "-c", "command -v date"], capture_output=True, text=True).stdout.strip()
        fake = self.tmp / "fake"
        fake.mkdir()
        (fake / "date").write_text('#!/usr/bin/env bash\n'
                                   'for a in "$@"; do case "$a" in -d|--date|--date=*) exec "$REAL_DATE" "$@";; esac; done\n'
                                   'exec "$REAL_DATE" -d "@${FAKE_NOW}" "$@"\n', encoding="utf-8", newline="\n")
        (fake / "date").chmod(0o755)
        first, oct3 = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc), datetime(2026, 10, 3, 9, 30, tzinfo=timezone.utc)
        nov1, dec1 = datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc), datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc)
        cases = [
            (first, "2026-09-30T19:00:00Z", "the 1st of the month"),       # 4:30 AM CDT; the last one yesterday
            (first, "2026-10-01T06:00:00Z", ""),                           # … 1 AM that day: done
            (oct3, "2026-10-01T17:30:00Z", "no full update for 40 hours"),
            (oct3, "2026-10-02T23:30:00Z", ""),                            # 10 hours
            (nov1, "2026-11-01T04:30:00Z", "the 1st of the month"),       # 1:30 AM CDT, the night daylight saving ends
            (nov1, "2026-11-01T05:30:00Z", ""),                            # 12:30 AM CDT that day
            (dec1, "2026-12-01T05:30:00Z", "the 1st of the month"),       # 5 AM CST; 11:30 PM CST the day before
            (dec1, "2026-12-01T06:30:00Z", ""),                            # 12:30 AM CST that day
            (oct3, None, ""),                                              # not known
            (first, "soon", ""),                                           # not a time
        ]
        for now, full, want in cases:
            with self.subTest(now=iso(now), full=full):
                t = now.astimezone(CHICAGO).date().isoformat()
                doc = {"v": 1, "built": iso(now - timedelta(minutes=5)), "day": t, "quotes": {"gv": t, "lv": t}}
                if full is not None:
                    doc["full"] = full
                self.server.body = json.dumps(doc)
                got, summary, _log = self.look_at(self.server.url, {"FAKE_NOW": str(int(now.timestamp())), "REAL_DATE": real},
                                                  [str(fake)])
                self.assertEqual(MC.full_run_reason(MC.parse_time(full), now, CHICAGO), want)
                self.assertEqual((got.get("done"), got.get("full")), ("true", want))
                if want:
                    self.assertIn(f"is on the site; the full daily update is due ({want}) — the next job starts it.", summary)
                else:
                    self.assertIn("Nothing to do: today's update", summary)


# --------------------------------------------------------------------------- the tidy job (bash + a stand-in gh)
FAKE_GH = """
import json, os, sys
world = json.load(open(os.environ["FAKE_GH_WORLD"], encoding="utf-8"))
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
if args[:1] != ["api"]:
    sys.exit(2)
method = args[args.index("-X") + 1] if "-X" in args else "GET"
path = [a for a in args[1:] if a.startswith("repos/")][0]
if method == "DELETE":
    rid = int(path.rsplit("/", 1)[1])
    if rid in world.get("fail_delete", []):
        sys.stderr.write("HTTP 403: Resource not accessible\\n")
        sys.exit(1)
    sys.exit(0)
if "/actions/workflows/" in path:
    if world.get("fail_list"):
        sys.stderr.write("HTTP 500: Server Error\\n")
        sys.exit(1)
    print(json.dumps({"total_count": len(world["runs"]), "workflow_runs": world["runs"]}))
    sys.exit(0)
if path.split("?")[0].endswith("/jobs"):
    rid = path.split("/actions/runs/")[1].split("/")[0]
    if int(rid) in world.get("fail_jobs", []):
        sys.stderr.write("HTTP 502: Bad Gateway\\n")
        sys.exit(1)
    print(json.dumps({"jobs": world["jobs"].get(rid, [])}))
    sys.exit(0)
sys.exit(3)
"""


class Tidy(unittest.TestCase):
    """morning.yml's "tidy" job against a stand-in `gh` that serves a list of runs and records every call."""

    def setUp(self):
        self.bash = bash_path()
        if not self.bash or not shutil.which("jq"):
            self.skipTest("needs bash and jq (the GitHub runner has them)")
        wf, _on = load_wf("morning.yml")
        self.step = step_of(wf["jobs"]["tidy"], "Delete this workflow's no-op runs older than a day")
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-tidy-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "fake_gh.py").write_text(FAKE_GH, encoding="utf-8")
        gh = self.tmp / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(f'#!/usr/bin/env bash\nexec "{Path(sys.executable).as_posix()}" "{(self.tmp / "fake_gh.py").as_posix()}" "$@"\n',
                      encoding="utf-8", newline="\n")
        gh.chmod(0o755)
        self.now = datetime.now(timezone.utc)

    def run_tidy(self, world: dict) -> tuple[list[int], str, list[list[str]]]:
        (self.tmp / "world.json").write_text(json.dumps(world), encoding="utf-8")
        (self.tmp / "log.txt").write_text("", encoding="utf-8")
        env = {k: str(v) for k, v in self.step["env"].items() if k != "GH_TOKEN"}
        env.update(GH_TOKEN="x", GITHUB_REPOSITORY="o/r", RUNNER_TEMP=str(self.tmp),
                   FAKE_GH_WORLD=str(self.tmp / "world.json"), FAKE_GH_LOG=str(self.tmp / "log.txt"),
                   PATH=os.pathsep.join([str(self.tmp / "bin"), str(shim_bin(self.tmp)), os.environ.get("PATH", "")]))
        r = subprocess.run([self.bash, "-c", self.step["run"]], cwd=self.tmp, env={**os.environ, **env},
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        calls = [json.loads(ln) for ln in (self.tmp / "log.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
        deleted = [int(c[-1].rsplit("/", 1)[1]) for c in calls if "-X" in c and c[c.index("-X") + 1] == "DELETE"]
        return deleted, r.stdout, calls

    def run_(self, rid: int, hours_ago: float, conclusion: str | None = "success", status: str = "completed") -> dict:
        return {"id": rid, "status": status, "conclusion": conclusion, "created_at": iso(self.now - timedelta(hours=hours_ago))}

    def jobs(self, update: str | None, idle: str | None = None) -> list[dict]:
        """A run's jobs: the update job's conclusion (None: no such job), and — when it ran — how its step
        "Nothing to do" ended (success: the check did nothing; skipped: it did something)."""
        out = [{"name": "Is today's update already on the site?", "conclusion": "success", "steps": []},
               {"name": "Tidy up old runs that had nothing to do", "conclusion": "success", "steps": []}]
        if update is not None:
            steps = [{"name": "Set up job", "conclusion": "success"},
                     {"name": "Start the morning update, follow it, check the live site", "conclusion": "success"}]
            if idle is not None:
                steps.append({"name": self.step["env"]["IDLE_STEP"], "conclusion": idle})
            out.insert(1, {"name": MC.UPDATE_JOB, "conclusion": update, "steps": steps})
        return out

    def test_only_old_green_runs_that_did_nothing(self):
        runs = [self.run_(1, 30), self.run_(2, 30), self.run_(3, 30, "failure"), self.run_(4, 2), self.run_(5, 50),
                self.run_(6, 30), self.run_(7, 30, "cancelled"), self.run_(8, 30, None, "in_progress")]
        jobs = {"1": self.jobs("skipped"), "2": self.jobs("success"), "3": self.jobs("skipped"), "4": self.jobs("skipped"),
                "5": self.jobs("skipped"), "6": self.jobs(None), "7": self.jobs("skipped"), "8": self.jobs("skipped")}
        deleted, log, calls = self.run_tidy({"runs": runs, "jobs": jobs})
        self.assertEqual(sorted(deleted), [1, 5])
        self.assertIn("Deleted 2 Morning check run(s)", log)
        listing = [c for c in calls if any("/actions/workflows/morning.yml/runs?" in a for a in c)]
        self.assertEqual(len(listing), 1)
        self.assertIn("status=success", listing[0][-1])
        self.assertFalse(any("update.yml" in a for c in calls for a in c), "never another workflow's runs")

    def test_checks_that_did_nothing_go_too(self):
        # the update job ran and ended at "Nothing to do" (the update was already there — the full update
        # was due, but another run had it — or it was too early to ask): deleted; the same step skipped (it
        # started, followed or asked something): kept
        runs = [self.run_(1, 30), self.run_(2, 30), self.run_(3, 2)]
        jobs = {"1": self.jobs("success", idle="success"), "2": self.jobs("success", idle="skipped"),
                "3": self.jobs("success", idle="success")}
        deleted, log, _calls = self.run_tidy({"runs": runs, "jobs": jobs})
        self.assertEqual(deleted, [1])
        self.assertIn("Deleted 1 Morning check run(s)", log)

    def test_at_most_fifty(self):
        runs = [self.run_(100 + n, 30 + n / 10) for n in range(55)]
        deleted, log, _calls = self.run_tidy({"runs": runs, "jobs": {str(r["id"]): self.jobs("skipped") for r in runs}})
        self.assertEqual(len(deleted), 50)
        self.assertIn("Deleted 50 Morning check run(s)", log)

    def test_problems_are_only_notices(self):
        deleted, log, _calls = self.run_tidy({"runs": [], "jobs": {}, "fail_list": True})
        self.assertEqual(deleted, [])
        self.assertIn("::notice title=Tidy::Could not list the Morning check's runs, so none were deleted: HTTP 500", log)
        runs = [self.run_(1, 30), self.run_(2, 30)]
        deleted, log, _calls = self.run_tidy({"runs": runs, "jobs": {"1": self.jobs("skipped"), "2": self.jobs("skipped")},
                                              "fail_delete": [1]})
        self.assertIn("::notice title=Tidy::Could not delete run 1 — it stays.", log)
        self.assertIn("Deleted 1 Morning check run(s)", log)
        # a run whose jobs cannot be listed stays — and says so
        deleted, log, _calls = self.run_tidy({"runs": runs, "jobs": {"1": self.jobs("skipped"), "2": self.jobs("skipped")},
                                              "fail_jobs": [2]})
        self.assertEqual(deleted, [1])
        self.assertIn("::notice title=Tidy::Could not look at run 2, so it stays: HTTP 502: Bad Gateway", log)


# --------------------------------------------------------------------------- update.yml
class UpdateWorkflow(unittest.TestCase):
    def setUp(self):
        self.text = (WF / "update.yml").read_text(encoding="utf-8")
        self.wf, self.on = load_wf("update.yml")
        self.sync = self.wf["jobs"]["sync"]

    def bash(self) -> str:
        b = bash_path()
        if not b:
            self.skipTest("needs bash")
        return b

    def test_the_two_schedules_are_unchanged(self):
        self.assertEqual(self.on["schedule"], [{"cron": "17 10 * * *"}, {"cron": "7 12 * * *"}])
        self.assertIn('    - cron: "17 10 * * *"\n', self.text)
        self.assertIn('    - cron: "7 12 * * *"\n', self.text)

    def test_morning_input_and_run_name(self):
        inputs = self.on["workflow_dispatch"]["inputs"]
        self.assertEqual(list(inputs), ["crawl_minutes", "skip_crawl", "morning"])
        self.assertEqual((inputs["morning"]["type"], inputs["morning"]["default"]), ("boolean", False))
        self.assertIn("Overrides the two fields above", inputs["morning"]["description"])
        self.assertEqual(self.wf["run-name"], "${{ inputs.morning && '" + MC.MORNING_TITLE + "' || '' }}")

    def plan(self, **env) -> dict:
        tmp = Path(tempfile.mkdtemp(prefix="gv-plan-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        out = tmp / "out.txt"
        out.write_text("", encoding="utf-8")
        base = {"EVENT": "workflow_dispatch", "SCHEDULE": "", "INPUT_MINUTES": "", "INPUT_SKIP": "", "INPUT_MORNING": "",
                "GITHUB_OUTPUT": str(out)}
        r = run_bash(self.bash(), step_run(self.sync, "Decide what to sync"), {**base, **env})
        self.assertEqual(r.returncode, 0, r.stderr)
        return outputs(out)

    def test_plan_step(self):
        from scripts.sync.common import load_config
        v = ((load_config().get("sources") or {}).get("crawler") or {}).get("minutes_per_run")
        daily = 40 if v in (None, "") else max(0, int(float(v)))
        translate = min(40, max(10, 345 - daily - 35))
        self.assertEqual(self.plan(INPUT_MORNING="true"), {"mode": "morning", "minutes": "0", "translate": "5", "budget": "20"})
        # "morning" wins over the two other fields
        self.assertEqual(self.plan(INPUT_MORNING="true", INPUT_SKIP="true", INPUT_MINUTES="120")["mode"], "morning")
        self.assertEqual(self.plan(EVENT="schedule", SCHEDULE="7 12 * * *"),
                         {"mode": "quick", "minutes": "0", "translate": "40", "budget": "90"})
        self.assertEqual(self.plan(EVENT="schedule", SCHEDULE="17 10 * * *"),
                         {"mode": "crawl", "minutes": str(daily), "translate": str(translate),
                          "budget": str(min(345, daily + 30 + translate + 20))})
        self.assertEqual(self.plan(EVENT="push")["mode"], "quick")
        self.assertEqual(self.plan(INPUT_SKIP="true")["mode"], "quick")
        self.assertEqual(self.plan(INPUT_MINUTES="25")["minutes"], "25")
        self.assertEqual(self.plan(INPUT_MORNING="false")["mode"], "crawl")

    def test_sync_step_flags(self):
        run = step_run(self.sync, "Sync all sources (articles, PDFs, podcasts, videos, Instagram, Drive) + translate")
        block = re.search(r'(case "\$MODE" in\n.*?\nesac\n)', run, re.S).group(1)
        for mode, want in (("morning", "--morning"), ("quick", "--quick"), ("crawl", "--crawl-minutes 40")):
            r = run_bash(self.bash(), block + 'echo "${args[*]}"\n', {"MODE": mode, "MINUTES": "40"})
            self.assertEqual(r.stdout.strip(), want, mode)

    def test_commit_messages(self):
        run = step_run(self.sync, "Commit refreshed data")
        block = re.search(r'(day="\$\(TZ=America/Chicago date \+%F\)"\n.*?\nfi\n)', run, re.S).group(1)
        self.assertIn('"${SCHEDULE:-}" = "7 12 * * *"', block)

        def msg(**env) -> str:
            r = run_bash(self.bash(), block + 'echo "$msg"\n', {"EVENT": "", "SCHEDULE": "", "MODE": "", **env})
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout.strip()
            self.assertRegex(out, r" \d{4}-\d{2}-\d{2} \[skip ci\]$")
            return re.sub(r" \d{4}-\d{2}-\d{2} \[skip ci\]$", "", out)
        self.assertEqual(msg(EVENT="push", MODE="quick"), "chore(data): content sync after settings/content change")
        self.assertEqual(msg(EVENT="workflow_dispatch", MODE="morning"), "chore(data): morning refresh with the daily quote")
        self.assertEqual(msg(EVENT="schedule", SCHEDULE="7 12 * * *", MODE="quick"), "chore(data): midday refresh")
        self.assertEqual(msg(EVENT="schedule", SCHEDULE="17 10 * * *", MODE="crawl"), "chore(data): daily content sync")
        self.assertEqual(msg(EVENT="workflow_dispatch", MODE="crawl"), "chore(data): daily content sync")
        env = step_of(self.sync, "Commit refreshed data")["env"]
        self.assertEqual(env["MODE"], "${{ steps.plan.outputs.mode }}")

    def test_build_json_is_checked(self):
        run = step_run(self.wf["jobs"]["build-deploy"], "Check the build")
        self.assertIn('test -s _site/build.json || echo "::warning::build.json is missing — the Morning check cannot see this build."', run)
        check, check_on = load_wf("check.yml")
        self.assertRegex(step_run(check["jobs"]["build"], "Check the build"),
                         r'test -s _site/build\.json \|\| \{ echo "::error::[^"]+"; exit 1; \}')
        self.assertIn(".github/workflows/**", check_on["push"]["paths"])

    def summary(self, status: dict, quote: dict | None) -> tuple[str, str]:
        step = next(s for s in self.sync["steps"] if s.get("name") == "Write run summary")
        code = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        tmp = Path(tempfile.mkdtemp(prefix="gv-summary-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "data" / "site").mkdir(parents=True)
        (tmp / "data" / "site" / "status.json").write_text(json.dumps(status), encoding="utf-8")
        if quote is not None:
            (tmp / "data" / "site" / "quote.json").write_text(json.dumps(quote), encoding="utf-8")
        (tmp / "script.py").write_text(code, encoding="utf-8")
        env = dict(os.environ, GITHUB_STEP_SUMMARY=str(tmp / "summary.md"), GITHUB_OUTPUT=str(tmp / "out.txt"),
                   PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
        r = subprocess.run([sys.executable, str(tmp / "script.py")], cwd=tmp, env=env, capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return (tmp / "summary.md").read_text(encoding="utf-8"), r.stdout

    def test_run_summary_lists_files_to_fix_scheduled_posts_and_the_quote(self):
        ok = iso(datetime.now(timezone.utc) - timedelta(hours=1))
        bad = [f"bulletin/p{n}.md: the publish date 'soon' is not a date (use YYYY-MM-DD)" for n in range(12)]
        status = {"fixture": False, "sources": [
            {"source": "announcements", "label": "Bulletin (content/bulletin)", "ok": True, "updated": ok, "count": 1,
             "stats": {"errors": bad}},
            {"source": "manual_events", "label": "Events (content/events)", "ok": True, "updated": ok, "count": 2,
             "stats": {"errors": ["events/2027-03-14-a.md: it has no start date (add a line 'start: 2027-03-14')"]}}],
            "scheduled": [{"publish": "2027-02-01", "title": "Spring Assembly sign-ups", "source": "committee",
                           "file": "content/bulletin/spring.md"},
                          {"publish": "2027-02-10", "title": "Inscripciones", "source": "drive",
                           "file": "Inscripciones (desde 2027-02-10)"}]}
        quote = {"items": [{"pub": "gv", "date": "2026-09-29"}, {"pub": "lv", "date": "2026-09-28"}]}
        summary, log = self.summary(status, quote)
        self.assertIn("**Daily quote:** Grapevine Sep 29 · La Viña Sep 28", summary)
        self.assertIn("**Bulletin files to fix** (the rest of the site still updated — fix the file and save it again):", summary)
        self.assertEqual(summary.count("- bulletin/p"), 10, "at most 10 listed")
        self.assertIn("**Event files to fix**", summary)
        self.assertIn("- events/2027-03-14-a.md: it has no start date (add a line 'start: 2027-03-14')", summary)
        self.assertIn("**Scheduled bulletin posts** (not on the site yet):", summary)
        self.assertIn("- 2027-02-01 — Spring Assembly sign-ups (content/bulletin/spring.md)", summary)
        self.assertIn("- 2027-02-10 — Inscripciones (Google Drive: Inscripciones (desde 2027-02-10))", summary)
        self.assertIn("::warning title=Bulletin files to fix::bulletin/p0.md: the publish date 'soon' is not a date", log)
        self.assertIn("::warning title=Event files to fix::events/2027-03-14-a.md", log)
        self.assertIn("::notice title=Scheduled bulletin posts::2 post(s) will appear by themselves on their day — the "
                      "first on 2027-02-01", log)
        # nothing of the kind: none of those lines
        summary, log = self.summary({"fixture": False, "sources": []}, None)
        for bit in ("Daily quote", "files to fix", "Scheduled bulletin posts"):
            self.assertNotIn(bit, summary)
        self.assertNotIn("::warning", log)


# --------------------------------------------------------------------------- run_all --morning
class RunAllMorning(unittest.TestCase):
    def run_all(self, day: date, *flags: str, attempted: dict | None = None) -> tuple[list[str], dict[str, list[str]], str]:
        """run_all.main with stand-in modules on `day` (Central) → (the modules run, in order; their
        arguments; the run summary). `attempted`: {raw file name: when it was last read or tried}."""
        calls: list[tuple[str, list[str]]] = []

        def fake(name, args):
            calls.append((name, list(args)))
            return {"module": name, "status": "ok", "seconds": 0.0, "items": 0, "new": 0, "note": ""}

        def raw(name):
            return {"source": name, "attempted": (attempted or {}).get(name), "items": []}
        tmp = Path(tempfile.mkdtemp(prefix="gv-runall-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        summary = tmp / "summary.md"
        summary.write_text("", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "GV_CRAWL_MINUTES"}
        env["GITHUB_STEP_SUMMARY"] = str(summary)
        with mock.patch.object(run_all, "run_source", fake), mock.patch.object(run_all, "load_raw", raw), \
                mock.patch("scripts.sync.quote.local_today", return_value=day), \
                mock.patch.dict(os.environ, env, clear=True), redirect_stdout(io.StringIO()):
            self.assertEqual(run_all.main([*flags, "--no-build"]), 0)
        return [n for n, _a in calls], dict(calls), summary.read_text(encoding="utf-8")

    def test_a_normal_morning(self):
        order, args, summary = self.run_all(date(2026, 9, 29), "--morning")
        # the quick sources — the daily quote, the reason for the run, right after the bulletin
        self.assertEqual(order, ["drive", "announcements", "quote", "podcasts"])
        self.assertEqual(set(order), set(run_all.QUICK_MODULES))
        self.assertEqual(args["drive"], ["--max-minutes", "5"])
        self.assertEqual(args["podcasts"], ["--no-discover"])
        self.assertIn("### Morning refresh", summary)
        self.assertRegex(summary, r"\| crawl \| ⏭️ skipped \| [\d.]+ \|  \|  \| --morning \|")
        self.assertRegex(summary, r"\| youtube \| ⏭️ skipped \| [\d.]+ \|  \|  \| --morning \|")

    def test_the_first_of_the_month(self):
        # the monthly sources come after the quote: a slow magazine server never keeps the quote out
        order, args, _s = self.run_all(date(2026, 10, 1), "--morning")
        self.assertEqual(order, ["drive", "announcements", "quote", "podcasts", "articles", "shop"])
        self.assertEqual(args["articles"], ["--no-details", "--no-archive"])
        self.assertEqual(args["shop"], [])

    def test_the_fifteenth(self):
        order, _args, _s = self.run_all(date(2026, 10, 15), "--morning")
        self.assertEqual(order, ["drive", "announcements", "quote", "podcasts", "shop"])

    def test_the_monthly_sources_once_a_day(self):
        # a later morning refresh that day (the Morning check waited for a late quote) — or one after the
        # full update — does not read them again; yesterday's reading does not count (Central days)
        order, _args, summary = self.run_all(date(2026, 10, 1), "--morning", attempted={
            "shop": "2026-10-01T09:31:00Z",                  # 4:31 AM CDT today
            "articles": "2026-10-01T04:50:00Z"})             # 11:50 PM CDT on September 30
        self.assertEqual(order, ["drive", "announcements", "quote", "podcasts", "articles"])
        self.assertRegex(summary, r"\| shop \| ⏭️ skipped \| [\d.]+ \|  \|  \| --morning \(read today already\) \|")
        order, _args, _s = self.run_all(date(2026, 10, 15), "--morning", attempted={"shop": "2026-10-15T15:02:00Z"})
        self.assertEqual(order, ["drive", "announcements", "quote", "podcasts"])
        # --quick never reads them, whatever the day
        order, _args, _s = self.run_all(date(2026, 10, 1), "--quick")
        self.assertEqual(order, list(run_all.QUICK_MODULES))

    def test_the_sources_only_the_full_update_reads(self):
        # status.json full_update (the newest `attempted` of these) is "when the last full update ran"
        self.assertEqual(set(run_all.FULL_ONLY), {"youtube", "instagram", "editorial", "weekly_open", "audio_project",
                                                  "meetings", "events_external"})
        lean = set(run_all.QUICK_MODULES) | {m for mods in run_all.MORNING_EXTRA.values() for m in mods}
        self.assertFalse(set(run_all.FULL_ONLY) & lean)
        self.assertEqual(set(run_all.FULL_ONLY) | lean | {"crawl"}, set(run_all.MODULES))
        self.assertLessEqual(set(run_all.FULL_ONLY), {name for name, *_ in B.SOURCES}, "each one is on /status/")

    def test_quick_is_unchanged(self):
        order, args, summary = self.run_all(date(2026, 10, 1), "--quick")
        self.assertEqual(order, list(run_all.QUICK_MODULES))
        self.assertEqual(args["drive"], [])
        self.assertIn("### Daily content update", summary)

    def test_every_flag_is_one_the_module_has(self):
        import importlib
        flags: dict[str, list[str]] = {}
        for table in (run_all.QUICK_ARGS, run_all.MORNING_ARGS):
            for name, fl in table.items():
                flags.setdefault(name, []).extend(f for f in fl if f.startswith("--"))
        self.assertTrue(set(run_all.MORNING_EXTRA[1]) | set(run_all.MORNING_EXTRA[15]) <= set(run_all.MODULES))
        for name, fl in flags.items():
            mod = importlib.import_module(f"scripts.sync.{name}")
            for f in fl:
                with self.subTest(module=name, flag=f):
                    self.assertTrue(run_all._supports(mod, f))

    def test_a_flag_the_module_lacks_goes_with_its_value(self):
        got = []

        class Mod:
            @staticmethod
            def main(argv):
                got.append(list(argv))
        with mock.patch.object(run_all.importlib, "import_module", return_value=Mod), \
                mock.patch.object(run_all, "_supports", lambda mod, flag: flag == "--keep"), \
                mock.patch.object(run_all, "run_module", lambda name, fn: fn()), \
                mock.patch.object(run_all, "_raw_summary", lambda name: {"ok": True, "items": 0, "new": 0, "error": None, "exists": True}), \
                self.assertLogs("run_all", "WARNING") as logs:
            row = run_all.run_source("drive", ["--max-minutes", "5", "--keep", "--gone", "--x", "3"])
        self.assertEqual(got, [["--keep"]])
        self.assertEqual(row["status"], "ok")
        self.assertIn("['--max-minutes', '5', '--gone', '--x', '3']", logs.output[0])


# --------------------------------------------------------------------------- the guard: a stand-in world
T0 = datetime(2026, 9, 29, 9, 30, tzinfo=timezone.utc)          # 4:30 AM CDT, Tuesday September 29 — the alarm
TODAY, YESTERDAY = "2026-09-29", "2026-09-28"
CFG = {"site": {"timezone": "America/Chicago", "morning_goal": "05:30", "url": "https://example.org/gvlv"},
       "sources": {"grapevine": {"base": "https://www.aagrapevine.org"}, "lavina": {"base": "https://www.aalavina.org"}}}
MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December")
MONTHS_ES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre")
OLD = {"v": 1, "built": "2026-09-28T17:40:00Z", "day": YESTERDAY, "tz": "America/Chicago",
       "quotes": {"gv": YESTERDAY, "lv": YESTERDAY}, "run": "4000"}


def magazine_page(pub: str, day: str) -> str:
    """A magazine's home page (the fixture) showing the quote of `day`."""
    d = date.fromisoformat(day)
    if pub == "gv":
        return (FIX / "gv_home.html").read_text(encoding="utf-8").replace("September 25", f"{MONTHS_EN[d.month - 1]} {d.day}")
    return (FIX / "lv_home.html").read_text(encoding="utf-8").replace("Septiembre 25", f"{MONTHS_ES[d.month - 1]} {d.day}")


class FakeClock:
    def __init__(self, t: datetime):
        self.t = t

    def now(self) -> datetime:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += timedelta(seconds=seconds)


class World:
    """Update & Deploy's runs on GitHub, the live site's build.json and the two magazines' home pages, on one
    fake clock. A run that ends well is on the site DEPLOY seconds later; it carries today's quote of each
    magazine that had published it by the run's end (`published`), unless that magazine is in `misses`, and
    — a full update (dispatched with no inputs) — its end as `full`."""
    PLAN = {"start": 5, "end": 160, "conclusion": "success"}     # seconds after a dispatch
    DEPLOY = 20

    def __init__(self, now: datetime = T0, live: dict | None = None, published: dict | None = None):
        self.clock = FakeClock(now)
        self.live = copy.deepcopy(live)
        self.full = (live or {}).get("full") if isinstance(live, dict) else None
        self.site_down = False
        long_ago = now - timedelta(hours=5)
        self.published = dict(published or {"gv": long_ago, "lv": long_ago})
        self.misses: set[str] = set()
        self.runs: list[dict] = []
        self.posts: list[tuple[str, dict, dict]] = []
        self.fetches: list[tuple[datetime, str]] = []
        self.dispatch_mode = "details"
        self.plans: list[dict] = []
        self.api_down_after: datetime | None = None        # from then on GitHub answers 502
        self._id = 5000

    # ---- GitHub
    def add_run(self, created: datetime, start: float | None = 5, end: float | None = 160, conclusion: str = "success",
                title: str = "Update & Deploy", event: str = "schedule", cancel: float | None = None,
                full: bool = False) -> dict:
        self._id += 1
        at = lambda s: None if s is None else created + timedelta(seconds=s)  # noqa: E731
        r = {"id": self._id, "created": created, "start": at(start), "end": at(end), "cancel": at(cancel),
             "conclusion": conclusion, "title": title, "event": event, "full": full}
        self.runs.append(r)
        return r

    def view(self, r: dict) -> dict:
        now = self.clock.now()
        if r["cancel"] and now >= r["cancel"]:
            status, concl = "completed", "cancelled"
        elif r["start"] is None or now < r["start"]:
            status, concl = "queued", None
        elif r["end"] is None or now < r["end"]:
            status, concl = "in_progress", None
        else:
            status, concl = "completed", r["conclusion"]
        started = r["start"] is not None and now >= r["start"] and status != "queued"
        return {"id": r["id"], "status": status, "conclusion": concl, "created_at": iso(r["created"]),
                "run_started_at": iso(r["start"]) if started else None,
                "updated_at": iso(min(now, r["end"]) if r["end"] else now), "display_title": r["title"],
                "event": r["event"], "html_url": f"https://github.com/o/r/actions/runs/{r['id']}"}

    def send(self, method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> tuple[int, bytes]:
        parts = urlsplit(url)
        assert parts.path.startswith("/repos/o/r/"), url
        if self.api_down_after and self.clock.now() >= self.api_down_after:
            return 502, b'{"message": "Server Error"}'
        if method == "POST":
            doc = json.loads(body.decode("utf-8"))
            self.posts.append((url, dict(headers), doc))
            return self.dispatch(doc)
        m = re.search(r"/actions/runs/(\d+)$", parts.path)
        if m:
            r = next((x for x in self.runs if x["id"] == int(m.group(1))), None)
            return (200, json.dumps(self.view(r)).encode()) if r else (404, b'{"message": "Not Found"}')
        if parts.path.endswith("/actions/workflows/update.yml/runs"):
            event = parse_qs(parts.query).get("event", [""])[0]
            runs = [self.view(r) for r in sorted(self.runs, key=lambda x: x["created"], reverse=True)
                    if r["created"] <= self.clock.now() and (not event or r["event"] == event)]
            return 200, json.dumps({"total_count": len(runs), "workflow_runs": runs}).encode()
        return 404, b'{"message": "Not Found"}'

    def dispatch(self, doc: dict) -> tuple[int, bytes]:
        if self.dispatch_mode == "403":
            return 403, b'{"message": "Resource not accessible by integration"}'
        if self.dispatch_mode == "422" and "return_run_details" in doc:
            return 422, json.dumps({"message": 'Invalid request.\n\n"return_run_details" is not a permitted key.'}).encode()
        plan = {**self.PLAN, **(self.plans.pop(0) if self.plans else {})}
        morning = (doc.get("inputs") or {}).get("morning") == "true"
        r = self.add_run(self.clock.now(), plan["start"], plan["end"], plan["conclusion"],
                         MC.MORNING_TITLE if morning else "Update & Deploy", "workflow_dispatch", plan.get("cancel"),
                         full=not morning)
        if "replaced_by" in plan:                     # someone's run takes its place in the queue
            rb = plan["replaced_by"]
            self.add_run(self.clock.now() + timedelta(seconds=rb["after"]), rb["start"] - rb["after"], rb["end"] - rb["after"],
                         "success", "Update & Deploy", "push")
        if self.dispatch_mode == "details" and doc.get("return_run_details"):
            return 200, json.dumps({"workflow_run_id": r["id"], "run_url": f"https://api.github.com/repos/o/r/actions/runs/{r['id']}",
                                    "html_url": f"https://github.com/o/r/actions/runs/{r['id']}"}).encode()
        return 204, b""

    # ---- our site
    def build(self):
        now = self.clock.now()
        done = sorted((r for r in self.runs if r["conclusion"] == "success" and r["end"] and r["start"]
                       and not (r["cancel"] and r["cancel"] <= r["end"]) and r["end"] + timedelta(seconds=self.DEPLOY) <= now),
                      key=lambda r: r["end"])
        if not done:
            return self.live
        quotes = dict((self.live or {}).get("quotes") or {}) if isinstance(self.live, dict) else {}
        full = self.full
        for r in done:
            day = r["end"].astimezone(CHICAGO).date().isoformat()
            for p in ("gv", "lv"):
                t = self.published.get(p)
                if t and t <= r["end"] and p not in self.misses:
                    quotes[p] = day
            if r["full"]:                                 # a full update: when the last one ran
                full = iso(r["end"])
        r = done[-1]
        return {"v": 1, "built": iso(r["end"]), "day": r["end"].astimezone(CHICAGO).date().isoformat(),
                "tz": "America/Chicago", "quotes": quotes, "data": iso(r["end"]), "full": full, "run": str(r["id"]),
                "version": "x", "commit": "y"}

    def get(self, url: str) -> str | None:
        assert url.startswith("https://example.org/gvlv/build.json?check="), url
        if self.site_down:
            return None
        b = self.build()
        return None if b is None else (b if isinstance(b, str) else json.dumps(b))

    # ---- the magazines
    def fetch(self, url: str) -> str | None:
        self.fetches.append((self.clock.now(), url))
        pub = "gv" if "aagrapevine" in url else "lv"
        t = self.published.get(pub)
        return magazine_page(pub, TODAY if t and t <= self.clock.now() else YESTERDAY)

    # ---- one Morning check
    def check(self, *argv: str, status: dict | None = None, token: bool = True, env: dict | None = None) -> tuple[int, str, str]:
        """→ (exit code, what it printed, the run summary); its $GITHUB_OUTPUT lands in self.outputs."""
        tmp = Path(tempfile.mkdtemp(prefix="gv-morning-"))
        try:
            summary, output = tmp / "summary.md", tmp / "output.txt"
            keep = {k: v for k, v in os.environ.items() if k not in (
                "GH_TOKEN", "GITHUB_TOKEN", "GITHUB_REPOSITORY", "SITE_URL", "CHECK_ONLY", "SCHEDULE", "GITHUB_REF_NAME",
                "GITHUB_EVENT_NAME", "GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT")}
            keep.update({"GITHUB_STEP_SUMMARY": str(summary), "GITHUB_OUTPUT": str(output), "GITHUB_EVENT_NAME": "workflow_dispatch",
                         "GITHUB_SERVER_URL": "https://github.com", **(env or {})})
            gh = MC.GitHub("o/r", "tok", send=self.send, clock=self.clock) if token else None
            out = io.StringIO()
            with mock.patch.dict(os.environ, keep, clear=True), redirect_stdout(out):
                rc = MC.main(list(argv), clock=self.clock, gh=gh, get=self.get, fetch=self.fetch, cfg=CFG,
                             status=status if status is not None else {})
            self.outputs = outputs(output) if output.exists() else {}
            return rc, out.getvalue(), summary.read_text(encoding="utf-8") if summary.exists() else ""
        finally:
            shutil.rmtree(tmp, True)


def live_today(built: str = "2026-09-29T05:40:00Z", gv: str = TODAY, lv: str = TODAY) -> dict:
    return {"v": 1, "built": built, "day": TODAY, "tz": "America/Chicago", "quotes": {"gv": gv, "lv": lv}, "run": "4999"}


class Guard(unittest.TestCase):
    def test_is_done(self):
        self.assertTrue(MC.is_done(live_today(), TODAY))
        self.assertTrue(MC.is_done(live_today(), date(2026, 9, 29)))
        self.assertFalse(MC.is_done(live_today(lv=YESTERDAY), TODAY))
        self.assertFalse(MC.is_done(OLD, TODAY))
        for odd in (None, {}, {"day": TODAY}, {"day": TODAY, "quotes": [TODAY, TODAY]}, "x"):
            self.assertFalse(MC.is_done(odd, TODAY))

    def test_the_day_turns_at_midnight_central_across_daylight_saving(self):
        live = {"v": 1, "built": "2026-11-01T04:40:00Z", "day": "2026-10-31", "quotes": {"gv": "2026-10-31", "lv": "2026-10-31"}}
        rc, _log, summary = World(datetime(2026, 11, 1, 4, 59, tzinfo=timezone.utc), live).check("--check-only")
        self.assertEqual(rc, 0)
        self.assertIn("## Morning check — Saturday, October 31 (Central time)", summary)
        self.assertIn("It was already there", summary)            # 11:59 PM CDT: still October 31
        rc, _log, summary = World(datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc), live).check("--check-only")
        self.assertIn("## Morning check — Sunday, November 1 (Central time)", summary)
        self.assertIn("| Would | start the morning refresh (the live site is not today's build) |", summary)

    def test_already_on_the_site(self):
        w = World(live=live_today("2026-09-29T09:25:00Z"))
        rc, log, summary = w.check()
        self.assertEqual((rc, w.posts, w.fetches), (0, [], []))
        self.assertIn("✅ Today's update is on the site — the latest build is from **4:25 AM CDT**.", summary)
        self.assertIn("| How | It was already there — no morning refresh needed. |", summary)
        self.assertNotIn("::warning", log)
        self.assertEqual(w.outputs, {"idle": "true"}, "nothing started, followed or asked: tidied away a day later")

    def test_already_there_is_only_the_latest_build(self):
        # 2 PM: the live build is the 1 PM one (a push, the midday refresh) — not when today's update went live,
        # so no "since" and no "after the goal"
        w = World(datetime(2026, 9, 29, 19, 0, tzinfo=timezone.utc), live_today(built="2026-09-29T18:00:00Z"))
        for argv in ((), ("--check-only",)):
            rc, log, summary = w.check(*argv)
            self.assertEqual(rc, 0)
            self.assertIn("✅ Today's update is on the site — the latest build is from **1:00 PM CDT**.", summary)
            self.assertNotIn("since", summary)
            self.assertNotIn("goal", summary)
            self.assertNotIn("After the goal", log)
        self.assertEqual(w.outputs, {"idle": "false"}, "a look-only run is somebody's question: kept")

    def test_a_console_that_cannot_show_the_symbols(self):
        # a Windows console (cp1252) has no ✅ / 🔎: a "?" instead — never a crash (exit 1)
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="\n")
        w = World(live=OLD)
        with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "", "GITHUB_OUTPUT": "", "GITHUB_EVENT_NAME": ""}), \
                mock.patch.object(sys, "stdout", console):
            rc = MC.main(["--check-only"], clock=w.clock, gh=None, get=w.get, fetch=w.fetch, cfg=CFG, status={})
            console.flush()
        self.assertEqual(rc, 0)
        text = raw.getvalue().decode("cp1252")
        self.assertIn("? Look only — nothing was started.", text)
        self.assertIn("| Would | start the morning refresh (the live site is not today's build) |", text)

    def test_an_old_build_starts_one_morning_refresh(self):
        w = World(live=OLD)
        rc, log, summary = w.check()
        self.assertEqual(rc, 0, log)
        self.assertEqual(len(w.posts), 1)
        url, headers, body = w.posts[0]
        self.assertEqual(url, "https://api.github.com/repos/o/r/actions/workflows/update.yml/dispatches")
        self.assertEqual(body, {"ref": "main", "inputs": {"morning": "true"}, "return_run_details": True})
        self.assertEqual(headers["Authorization"], "Bearer tok")
        self.assertEqual(headers["X-GitHub-Api-Version"], "2022-11-28")
        self.assertEqual(headers["Accept"], "application/vnd.github+json")
        self.assertIn("## Morning check — Tuesday, September 29 (Central time)", summary)
        self.assertIn("✅ Today's update is on the site since **4:32 AM CDT** — goal 5:30 AM.", summary)
        self.assertIn("| Update & Deploy | [run 5001](https://github.com/o/r/actions/runs/5001) — 2 min 35 s |", summary)
        self.assertIn("| Started by | Run workflow (the morning alarm or a person) |", summary)
        self.assertIn("| How | Started the morning refresh. |", summary)
        self.assertEqual(w.fetches, [], "the magazines are not asked: the refresh reads them itself")
        self.assertNotIn("::warning", log)

    def test_a_waiting_run_is_followed_and_never_replaced(self):
        w = World(live=OLD)
        w.add_run(T0 - timedelta(seconds=60), start=90, end=240, event="push")
        rc, log, summary = w.check()
        self.assertEqual((rc, w.posts), (0, []))
        self.assertIn("Followed the Update & Deploy run that was already waiting.", summary)
        self.assertIn("[run 5001]", summary)

    def test_an_answer_without_the_run_id_is_found_by_listing(self):
        w = World(live=OLD)
        w.dispatch_mode = "204"
        rc, log, summary = w.check()
        self.assertEqual((rc, len(w.posts)), (0, 1), log)
        self.assertTrue(w.posts[0][2]["return_run_details"])
        self.assertIn("[run 5001]", summary)

    def test_a_refused_field_is_sent_again_without_it(self):
        w = World(live=OLD)
        w.dispatch_mode = "422"
        rc, log, _summary = w.check()
        self.assertEqual(rc, 0, log)
        self.assertEqual([("return_run_details" in b) for _u, _h, b in w.posts], [True, False])
        self.assertEqual(w.posts[1][2], {"ref": "main", "inputs": {"morning": "true"}})

    def test_a_replaced_run_is_followed_to_its_replacement(self):
        w = World(live=OLD)
        w.plans = [{"start": None, "end": None, "cancel": 10, "replaced_by": {"after": 8, "start": 12, "end": 200}}]
        rc, log, summary = w.check()
        self.assertEqual((rc, len(w.posts)), (0, 1), log)
        self.assertIn("[run 5002]", summary)

    def test_a_failed_update_is_a_red_x(self):
        w = World(live=OLD)
        w.plans = [{"conclusion": "failure"}]
        rc, log, summary = w.check()
        self.assertEqual(rc, 1)
        self.assertIn('::error title=Morning update failed::the Update & Deploy run ended "failure" — '
                      "[run 5001](https://github.com/o/r/actions/runs/5001).", log)
        self.assertIn("❌ Today's update did not reach the site.", summary)

    def test_a_run_that_never_starts_is_a_red_x(self):
        w = World(live=OLD)
        w.plans = [{"start": 50 * 60, "end": 55 * 60}]
        rc, log, _summary = w.check()
        self.assertEqual(rc, 1)
        self.assertIn("still waiting to start after 45 minutes", log)
        self.assertLessEqual(w.clock.now() - T0, timedelta(minutes=46))

    def test_github_stops_answering_is_a_red_x(self):
        w = World(live=OLD)
        w.api_down_after = T0 + timedelta(seconds=30)
        rc, log, summary = w.check()
        self.assertEqual((rc, len(w.posts)), (1, 1))
        self.assertIn("::error title=Morning update failed::GitHub did not answer: GET actions/runs/5001: HTTP 502", log)
        self.assertIn("❌ Today's update did not reach the site.", summary)

    def test_update_switched_off(self):
        w = World(live=OLD)
        w.dispatch_mode = "403"
        rc, log, _summary = w.check()
        self.assertEqual(rc, 1)
        self.assertIn("Enable workflow", log)

    def test_an_unreadable_site_starts_the_refresh_then_warns(self):
        w = World(live=OLD)
        w.site_down = True
        rc, log, _summary = w.check()
        self.assertEqual((rc, len(w.posts)), (0, 1))
        self.assertIn("::warning title=Cannot confirm::The Update & Deploy run finished, but the site's build.json could not "
                      "be read after 5 minutes", log)

    def test_a_site_that_does_not_show_a_finished_run_is_never_a_reason_for_another(self):
        # the waiting run is followed and ends well, but GitHub Pages keeps the old build: a yellow note,
        # no dispatch — the same for a refresh the check started
        w = World(live=OLD)
        w.add_run(T0 - timedelta(seconds=60), start=90, end=240, event="push")
        w.DEPLOY = 3600                                   # the deploy "never" shows
        rc, log, summary = w.check()
        self.assertEqual((rc, w.posts), (0, []))
        self.assertIn("⚠️ The update finished, but the live site does not show it yet.", summary)
        self.assertIn("still shows the build of 12:40 PM CDT (2026-09-28)", log)
        w = World(live=OLD)
        w.DEPLOY = 3600
        rc, log, _summary = w.check()
        self.assertEqual((rc, len(w.posts)), (0, 1))
        self.assertIn("::warning title=Cannot confirm::", log)
        self.assertEqual(w.outputs, {"idle": "false"})

    def test_after_the_goal_is_a_yellow_note(self):
        w = World(datetime(2026, 9, 29, 10, 40, tzinfo=timezone.utc), OLD)           # 5:40 AM CDT
        rc, log, summary = w.check()
        self.assertEqual(rc, 0)
        self.assertIn("since **5:42 AM CDT** — goal 5:30 AM.", summary)
        self.assertIn("::warning title=After the goal::Today's update went live at 5:42 AM CDT — after the 5:30 AM goal.", log)

    def test_look_only_starts_nothing(self):
        w = World(live=OLD)
        rc, _log, summary = w.check("--check-only")
        self.assertEqual((rc, w.posts), (0, []))
        self.assertIn("🔎 Look only — nothing was started.", summary)
        self.assertIn("| Would | start the morning refresh (the live site is not today's build) |", summary)
        w.add_run(T0 - timedelta(seconds=60), start=900, end=1000)
        _rc, _log, summary = w.check("--check-only")
        self.assertIn("| Would | follow the waiting Update & Deploy run 5001 (a new run would replace it) |", summary)
        self.assertEqual(w.posts, [])
        # CHECK_ONLY from morning.yml's input does the same
        rc, _log, summary = World(live=OLD).check(env={"CHECK_ONLY": "true"})
        self.assertIn("🔎 Look only", summary)

    def test_without_a_token_only_look_only_works(self):
        rc, log, _summary = World(live=OLD).check(token=False)
        self.assertEqual(rc, 2)
        self.assertIn("::error title=No GitHub access::", log)
        rc, _log, summary = World(live=OLD).check("--check-only", token=False)
        self.assertEqual(rc, 0)
        self.assertIn("| Update & Deploy runs | not looked at (no token) |", summary)


class GuardLateMagazine(unittest.TestCase):
    """Today's build is up, La Viña's quote is not out yet: the magazine is asked every 10 minutes."""

    def test_asked_every_ten_minutes_then_one_refresh(self):
        w = World(live=live_today(lv=YESTERDAY), published={"gv": T0 - timedelta(hours=5), "lv": T0 + timedelta(minutes=25)})
        rc, log, summary = w.check()
        self.assertEqual(rc, 0, log)
        self.assertEqual(len(w.posts), 1)
        self.assertTrue(all("aalavina.org" in u for _t, u in w.fetches), "only the late magazine is asked")
        times = [t for t, _u in w.fetches]
        self.assertEqual(len(times), 4)                           # 4:30, 4:40, 4:50: not yet · 5:00: out
        self.assertTrue(all(b - a == MC.POLL_EVERY for a, b in zip(times, times[1:])), times)
        self.assertEqual(w.runs[-1]["created"], T0 + timedelta(minutes=30))
        self.assertIn("since **5:02 AM CDT** — goal 5:30 AM.", summary)
        self.assertIn("Waited for the La Viña quote, then started the morning refresh.", summary)

    def test_too_early_to_ask(self):
        w = World(datetime(2026, 9, 29, 8, 30, tzinfo=timezone.utc), live_today(lv=YESTERDAY))      # 3:30 AM CDT
        rc, _log, summary = w.check()
        self.assertEqual((rc, w.fetches, w.posts), (0, [], []))
        self.assertIn("The magazines are asked from 4:00 AM CDT", summary)
        self.assertEqual(w.outputs, {"idle": "true"}, "nothing started, followed or asked: tidied away a day later")

    def test_after_the_window_it_asks_once(self):
        # 7:10 AM (a late schedule, or someone pressing Run workflow): one question, and a note that says
        # when the magazine was asked — never a claim about a time nobody asked
        w = World(datetime(2026, 9, 29, 12, 10, tzinfo=timezone.utc), live_today(lv=YESTERDAY),       # 7:10 AM CDT
                  published={"gv": T0, "lv": None})
        rc, log, _summary = w.check()
        self.assertEqual((rc, w.posts), (0, []))
        self.assertEqual(w.fetches, [(datetime(2026, 9, 29, 12, 10, tzinfo=timezone.utc), "https://www.aalavina.org/")])
        self.assertIn("::warning title=A daily quote is late at the source::La Viña had not published today's quote when "
                      "last asked, at 7:10 AM CDT; the site shows the last one, labelled \"Yesterday\", until an update "
                      "brings the new one", log)
        self.assertEqual(w.outputs, {"idle": "false"}, "it asked a magazine: kept")

    def test_after_the_window_a_quote_that_is_out_comes_in(self):
        # 8:00 AM, La Viña published at 7:05: Run workflow brings it (one question, one morning refresh)
        at = datetime(2026, 9, 29, 13, 0, tzinfo=timezone.utc)
        pub = {"gv": T0 - timedelta(hours=1), "lv": at - timedelta(minutes=55)}
        w = World(at, live_today(lv=YESTERDAY), published=pub)
        rc, log, summary = w.check()
        self.assertEqual(rc, 0, log)
        self.assertEqual([b["inputs"] for _u, _h, b in w.posts], [{"morning": "true"}])
        self.assertEqual(len(w.fetches), 1)
        self.assertIn("✅ Today's update is on the site since **8:02 AM CDT** — goal 5:30 AM.", summary)
        self.assertIn("| How | Found the La Viña quote out, then started the morning refresh. |", summary)
        self.assertIn("::warning title=After the goal::Today's update went live at 8:02 AM CDT", log)
        # the same, only looking: it says what it would do (one question)
        w = World(at, live_today(lv=YESTERDAY), published=pub)
        _rc, _log, summary = w.check("--check-only")
        self.assertEqual((len(w.fetches), w.posts), (1, []))
        self.assertIn("| Would | start the morning refresh: today's La Viña quote is out |", summary)
        w = World(at, live_today(lv=YESTERDAY), published={"gv": pub["gv"], "lv": None})
        _rc, _log, summary = w.check("--check-only")
        self.assertIn("| Would | a yellow note: the La Viña quote is not out yet (after 7:00 AM CDT each check asks once; "
                      "the next update brings it) |", summary)

    def test_never_asked_again_right_after_a_refresh(self):
        # 4:30 AM, yesterday's build, La Viña publishes at 4:55: the new-day refresh reads both pages itself
        # (4:30–4:33), so the first question comes POLL_EVERY after it — never at once
        w = World(live=OLD, published={"gv": T0 - timedelta(hours=5), "lv": T0 + timedelta(minutes=25)})
        rc, log, summary = w.check()
        self.assertEqual(rc, 0, log)
        refresh_end = w.runs[0]["end"]
        self.assertGreaterEqual(w.fetches[0][0] - refresh_end, MC.POLL_EVERY)
        self.assertTrue(all(b - a >= MC.POLL_EVERY for (a, _u), (b, _v) in zip(w.fetches, w.fetches[1:])))
        self.assertTrue(all("aalavina.org" in u for _t, u in w.fetches), "only the late magazine")
        self.assertEqual([b["inputs"] for _u, _h, b in w.posts], [{"morning": "true"}, {"morning": "true"}])
        self.assertIn("| How | Waited for the La Viña quote, then started the morning refresh. |", summary)

    def test_the_worst_case_fits_in_the_job(self):
        # A check that begins at 4:00 AM (a late schedule) asks until 6:50 (GUARD_MAX); the quote is out at
        # 6:49; the refresh takes 44 minutes and does not bring it: the check ends right after it, with the
        # note — inside GUARD_MAX + FOLLOW_MAX + LIVE_MAX, never a sleep after it
        start = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)                    # 4:00 AM CDT
        w = World(start, live_today(lv=YESTERDAY),
                  published={"gv": start - timedelta(hours=5), "lv": start + timedelta(minutes=169)})
        w.misses = {"lv"}
        w.plans = [{"start": 5, "end": 44 * 60}] * 3
        rc, log, _summary = w.check(env={"GITHUB_EVENT_NAME": "schedule"})
        self.assertEqual(rc, 0, log)
        self.assertEqual(len(w.posts), 1)
        self.assertEqual(w.fetches[-1][0], start + MC.GUARD_MAX)                    # 6:50: its last question
        self.assertIn("::warning title=A daily quote could not be read::", log)
        self.assertLessEqual(w.clock.now() - start, MC.GUARD_MAX + MC.FOLLOW_MAX + MC.LIVE_MAX)

    def test_never_more_than_three_refreshes(self):
        w = World(live=live_today(lv=YESTERDAY))
        w.misses = {"lv"}                                       # the page shows it; the update never gets it
        rc, log, _summary = w.check()
        self.assertEqual(rc, 0)
        self.assertEqual(len(w.posts), MC.MAX_RUNS)
        self.assertIn("::warning title=A daily quote could not be read::", log)
        times = [r["created"] for r in w.runs]
        self.assertTrue(all(b - a >= MC.POLL_EVERY for a, b in zip(times, times[1:])), "never one right after another")


class FullRun(unittest.TestCase):
    """The full daily update on the 1st, and after a skipped day — also when today's update was already
    there (morning.yml's first job then runs the check for it: FastPathParity has the same rule in bash).
    "The last full update" is the live build.json `full` (status.json full_update)."""
    FIRST = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)          # 4:30 AM CDT, October 1

    def done_on(self, now: datetime, full: str | None) -> dict:
        d = now.astimezone(CHICAGO).date().isoformat()
        return {"v": 1, "built": iso(now - timedelta(minutes=20)), "day": d, "quotes": {"gv": d, "lv": d}, "run": "4999",
                "full": full}

    def test_the_first_of_the_month(self):
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-09-30T19:00:00Z"))
        rc, _log, summary = w.check()
        self.assertEqual(rc, 0)
        self.assertEqual([b for _u, _h, b in w.posts], [{"ref": "main", "inputs": {}, "return_run_details": True}])
        self.assertIn("| Full daily update | started (the 1st of the month) — [run 5001]", summary)
        self.assertEqual(w.outputs, {"idle": "false"}, "it started the full update: kept")
        # already after midnight: nothing more
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-10-01T06:00:00Z"))
        w.check()
        self.assertEqual(w.posts, [])
        self.assertEqual(w.outputs, {"idle": "true"})

    def test_after_a_skipped_day(self):
        now = datetime(2026, 10, 3, 9, 30, tzinfo=timezone.utc)
        w = World(now, self.done_on(now, "2026-10-01T17:30:00Z"))
        _rc, _log, summary = w.check()
        self.assertEqual([b["inputs"] for _u, _h, b in w.posts], [{}])
        self.assertIn("started (no full update for 40 hours)", summary)
        w = World(now, self.done_on(now, "2026-10-02T23:30:00Z"))           # 10 hours: fine
        w.check()
        self.assertEqual(w.posts, [])
        w = World(now, self.done_on(now, None))                             # nothing known: nothing started
        w.check(status={"sources": []})
        self.assertEqual(w.posts, [])

    def test_the_checkouts_status_json_only_when_the_site_cannot_say(self):
        # a live build.json without `full` (built before it existed): data/site/status.json full_update
        now = datetime(2026, 10, 3, 9, 30, tzinfo=timezone.utc)
        w = World(now, self.done_on(now, None))
        w.check(status={"full_update": "2026-10-01T17:30:00Z"})
        self.assertEqual([b["inputs"] for _u, _h, b in w.posts], [{}])
        # the live value wins over the checkout's
        w = World(now, self.done_on(now, "2026-10-02T23:30:00Z"))
        w.check(status={"full_update": "2026-10-01T17:30:00Z"})
        self.assertEqual(w.posts, [])

    def test_never_while_another_run_waits_or_a_full_one_runs(self):
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-09-30T19:00:00Z"))
        w.add_run(self.FIRST - timedelta(minutes=1), start=600, end=900, event="push")       # waiting
        _rc, _log, summary = w.check()
        self.assertEqual(w.posts, [])
        self.assertIn("not started (the 1st of the month): another Update & Deploy run is waiting or running", summary)
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-09-30T19:00:00Z"))
        w.add_run(self.FIRST - timedelta(minutes=5), start=0, end=3600)                          # a full run going on
        w.check()
        self.assertEqual(w.posts, [])
        self.assertEqual(w.outputs, {"idle": "true"}, "another run has it: nothing done here")

    def test_one_that_was_started_is_not_started_again_for_twelve_hours(self):
        # an hourly check after the one that started it (it failed, or its build is not live yet): not again —
        # the next morning, if it is still due
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-09-30T19:00:00Z"))
        w.add_run(self.FIRST - timedelta(hours=2), start=5, end=1800, conclusion="failure", event="workflow_dispatch")
        _rc, _log, summary = w.check()
        self.assertEqual(w.posts, [])
        self.assertIn("| Full daily update | not started (the 1st of the month): one was started at 2:30 AM CDT — "
                      "[run 5001](https://github.com/o/r/actions/runs/5001); the next try is 12 hours after it |", summary)
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-09-30T19:00:00Z"))
        w.add_run(self.FIRST - timedelta(hours=13), start=5, end=1800, conclusion="failure", event="workflow_dispatch")
        w.check()
        self.assertEqual([b["inputs"] for _u, _h, b in w.posts], [{}], "13 hours ago: tried again")

    def test_after_its_own_morning_refresh(self):
        old = {**OLD, "day": "2026-09-30", "quotes": {"gv": "2026-09-30", "lv": "2026-09-30"}, "full": "2026-09-30T19:00:00Z"}
        w = World(self.FIRST, old)
        rc, log, _summary = w.check()
        self.assertEqual(rc, 0, log)
        self.assertEqual([b["inputs"] for _u, _h, b in w.posts], [{"morning": "true"}, {}])

    def test_look_only_says_so(self):
        w = World(self.FIRST, self.done_on(self.FIRST, "2026-09-30T19:00:00Z"))
        _rc, _log, summary = w.check("--check-only")
        self.assertEqual(w.posts, [])
        self.assertIn("| Full daily update | would be started (the 1st of the month) |", summary)


# --------------------------------------------------------------------------- /build.json
class BuildInfo(unittest.TestCase):
    def test_the_note_about_this_build(self):
        r = run_js(self, """
          const m = await imp("src/pages/build-info.11ty.js");
          const at = (built) => JSON.parse(m.render({
            site: { built, timezone: "America/Chicago" },
            db: { quote: { items: [{ pub: "gv", date: "2026-10-31" }, { pub: "lv", date: "2026-10-30T12:00:00Z" }, { pub: "", date: "x" }, null] },
                  status: { generated: "2026-10-31T09:00:00Z", full_update: "2026-10-30T17:05:00Z" } },
            build: { version: "c3f09a1b2d", commit: "9b44e62" },
          }));
          out({ data: m.data, a: at("2026-11-01T04:59:00Z"), b: at("2026-11-01T05:30:00Z"), c: at("2026-12-15T05:59:00Z"),
                empty: JSON.parse(m.render({})), raw: m.render({ site: { built: "2026-09-29T09:33:41.780Z" } }) });
        """, needs_modules=False, env={"GITHUB_RUN_ID": "98765"})
        self.assertEqual(r["data"], {"permalink": "/build.json", "eleventyExcludeFromCollections": True, "layout": False})
        a = r["a"]
        self.assertEqual(set(a), {"v", "built", "day", "tz", "quotes", "data", "full", "run", "version", "commit"})
        self.assertEqual((a["v"], a["tz"], a["run"], a["version"], a["commit"], a["data"], a["full"]),
                         (1, "America/Chicago", "98765", "c3f09a1b2d", "9b44e62", "2026-10-31T09:00:00Z", "2026-10-30T17:05:00Z"))
        self.assertEqual(a["quotes"], {"gv": "2026-10-31", "lv": "2026-10-30"})
        # the build's day in Central time, across the end of daylight saving
        self.assertEqual((a["day"], r["b"]["day"], r["c"]["day"]), ("2026-10-31", "2026-11-01", "2026-12-14"))
        self.assertEqual((r["empty"]["quotes"], r["empty"]["data"], r["empty"]["full"], r["empty"]["tz"]),
                         ({}, None, None, "America/Chicago"))
        self.assertTrue(r["raw"].endswith("}\n"))
        self.assertTrue(MC.is_done(r["b"] | {"quotes": {"gv": "2026-11-01", "lv": "2026-11-01"}}, "2026-11-01"))


# --------------------------------------------------------------------------- status.json quote_days + /status/
class QuoteDays(unittest.TestCase):
    def ctx(self, now: datetime, goal=..., hist: dict | None = None) -> B.Ctx:
        c = B.Ctx(offline=True)
        c.cfg = copy.deepcopy(c.cfg)                     # (the loaded config is shared: never change it in place)
        site = c.cfg.setdefault("site", {})
        site.pop("morning_goal", None)
        if goal is not ...:
            site["morning_goal"] = goal
        c.now, c.now_ts = now, now.timestamp()
        c.today_local = now.astimezone(c.tz).date()
        c.raw = {"quote": {"history": hist or {}}}
        return c

    def hist(self, days: list[str], at: str = "10:05") -> dict:
        return {p: [{"date": d, "text": "x", "seen": f"{d}T{at}:00Z"} for d in reversed(sorted(days))] for p in ("gv", "lv")}

    def test_seven_mornings_newest_first_against_the_goal(self):
        now = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
        days = [(date(2026, 10, 25) + timedelta(days=n)).isoformat() for n in range(10)]
        qd = B.quote_days(self.ctx(now, hist=self.hist(days)))
        self.assertEqual(qd["goal"], "05:30")
        self.assertEqual([r["day"] for r in qd["days"]], ["2026-11-03", "2026-11-02", "2026-11-01", "2026-10-31", "2026-10-30",
                                                          "2026-10-29", "2026-10-28"])
        by = {r["day"]: r for r in qd["days"]}
        self.assertEqual(by["2026-11-03"]["goal_at"], "2026-11-03T11:30:00Z")        # CST
        self.assertEqual(by["2026-11-01"]["goal_at"], "2026-11-01T11:30:00Z")        # the day daylight saving ends
        self.assertEqual(by["2026-10-31"]["goal_at"], "2026-10-31T10:30:00Z")        # CDT
        self.assertEqual((by["2026-10-31"]["gv"], by["2026-10-31"]["lv"]), ("2026-10-31T10:05:00Z", "2026-10-31T10:05:00Z"))
        self.assertEqual(set(by["2026-10-31"]), {"day", "goal_at", "gv", "lv"})

    def test_the_goal_setting(self):
        now = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)
        qd = B.quote_days(self.ctx(now, "6:00", self.hist(["2026-09-29"])))
        self.assertEqual((qd["goal"], qd["days"][0]["goal_at"]), ("06:00", "2026-09-29T11:00:00Z"))
        for bad in ("soon", "", None, "25:99", True):
            with self.subTest(goal=bad):
                qd = B.quote_days(self.ctx(now, bad, self.hist(["2026-09-29"])))
                self.assertEqual((qd["goal"], qd["days"][0]["goal_at"]), ("05:30", "2026-09-29T10:30:00Z"))

    def test_a_missing_quote_and_the_first_week(self):
        now = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)
        hist = self.hist(["2026-09-27", "2026-09-29"])
        hist["lv"] = [h for h in hist["lv"] if h["date"] != "2026-09-29"]       # La Viña: not in yet today
        hist["gv"].append({"date": "2026-09-20", "text": "x"})                # older than the times: no `seen`
        qd = B.quote_days(self.ctx(now, hist=hist))
        self.assertEqual([(r["day"], bool(r["gv"]), bool(r["lv"])) for r in qd["days"]],
                         [("2026-09-29", True, False), ("2026-09-28", False, False), ("2026-09-27", True, True)])
        # nothing recorded yet: today only (never "did not come in" for days nobody watched)
        qd = B.quote_days(self.ctx(now, hist={"gv": [{"date": "2026-09-28", "text": "x"}]}))
        self.assertEqual([(r["day"], r["gv"], r["lv"]) for r in qd["days"]], [("2026-09-29", None, None)])

    def test_a_day_whose_quote_came_in_at_an_unknown_time_is_left_out(self):
        # The day this comes in: today's quotes are already in the history, written before the times were
        # kept (quote.py never stamps them later). Their time is not known: no row — /status/ shows no
        # line rather than an invented time, or "not come in yet" for quotes that are on the site.
        now = datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc)
        legacy = {p: [{"date": "2026-09-29", "text": "x"}, {"date": "2026-09-28", "text": "x"}] for p in ("gv", "lv")}
        self.assertEqual(B.quote_days(self.ctx(now, hist=legacy))["days"], [])
        # one magazine's quote of that day known, the other's not: still left out
        mixed = copy.deepcopy(legacy)
        mixed["lv"][0]["seen"] = "2026-09-29T19:05:00Z"
        self.assertEqual(B.quote_days(self.ctx(now, hist=mixed))["days"], [])
        # the next day: that day's quotes are timed, the day before stays out
        nxt = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
        for p in ("gv", "lv"):
            legacy[p].insert(0, {"date": "2026-09-30", "text": "x", "seen": "2026-09-30T09:31:00Z"})
        qd = B.quote_days(self.ctx(nxt, hist=legacy))
        self.assertEqual([(r["day"], r["gv"], r["lv"]) for r in qd["days"]],
                         [("2026-09-30", "2026-09-30T09:31:00Z", "2026-09-30T09:31:00Z")])
        # no rows: /status/ shows neither the line nor the table (freshness.js)
        self.assertIsNone(run_js(self, """out(filters.fsQuoteMornings({ quote_days: { goal: "05:30", days: [] } }, Date.now()));"""))

    def test_in_status_json(self):
        now = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)
        st = B.build_status(self.ctx(now, hist=self.hist(["2026-09-29"])), None, B.I18n(None), {}, False, 0.0)
        self.assertEqual(st["quote_days"]["days"][0]["day"], "2026-09-29")
        self.assertEqual(st["scheduled"], [])
        self.assertIn("full_update", st)

    def test_when_the_last_full_update_ran(self):
        # status.json full_update: the newest `attempted` of the sources only the full update reads
        # (run_all.FULL_ONLY) — the quick ones, read by every refresh, never count; a source that is off or
        # never ran does not hold it back
        rows = [{"source": "youtube", "attempted": "2026-09-28T16:02:11Z"},
                {"source": "meetings", "attempted": "2026-09-28T16:40:00Z"},
                {"source": "instagram", "attempted": None},
                {"source": "quote", "attempted": "2026-09-29T09:31:00Z"},
                {"source": "drive", "attempted": "2026-09-29T09:30:40Z"},
                {"source": "shop", "attempted": "2026-09-29T09:32:00Z"}]
        self.assertEqual(B.full_update(rows), "2026-09-28T16:40:00Z")
        self.assertIsNone(B.full_update([r for r in rows if r["source"] not in run_all.FULL_ONLY]))
        self.assertIsNone(B.full_update([]))

    def test_the_status_page_view(self):
        r = run_js(self, """
          const f = filters.fsQuoteMornings;
          const st = { quote_days: { goal: "05:30", days: [
            { day: "2026-09-29", goal_at: "2026-09-29T10:30:00Z", gv: "2026-09-29T10:30:00Z", lv: "2026-09-29T09:31:00Z" },
            { day: "2026-09-28", goal_at: "2026-09-28T10:30:00Z", gv: "2026-09-28T10:30:01Z", lv: "2026-09-28T09:00:00Z" },
            { day: "2026-09-27", goal_at: "2026-09-27T10:30:00Z", gv: null, lv: "2026-09-27T09:00:00Z" },
          ] } };
          const now = Date.parse("2026-09-29T15:00:00Z");
          const today = { quote_days: { goal: "05:30", days: [{ day: "2026-09-29", goal_at: "2026-09-29T10:30:00Z", gv: null, lv: null }] } };
          out({ a: f(st, now), none: f({}, now), nothing: f(null, now), empty: f({ quote_days: { days: [] } }, now), today: f(today, now) });
        """)
        a = r["a"]
        self.assertEqual(a["goal"], "05:30")
        d0, d1, d2 = a["days"]
        self.assertEqual(a["today"], d0)
        self.assertEqual((d0["both"], d0["onTime"], d0["gvState"], d0["lvState"]), ("2026-09-29T10:30:00Z", True, "on_time", "on_time"))
        self.assertEqual((d1["both"], d1["onTime"], d1["gvState"], d1["lvState"]), ("2026-09-28T10:30:01Z", False, "late", "on_time"))
        self.assertEqual((d2["both"], d2["onTime"], d2["gvState"], d2["lvState"], d2["gvOnTime"], d2["lvOnTime"]),
                         (None, False, "none", "on_time", False, True))
        self.assertEqual((r["none"], r["nothing"], r["empty"]), (None, None, None))
        t = r["today"]["today"]
        self.assertEqual((t["both"], t["one"], t["gvState"], t["lvState"]), (None, None, "waiting", "waiting"))
        # exactly one in: named, with its time (the line then says which one has not come in)
        self.assertEqual((d0["one"], d2["one"]), (None, {"pub": "lv", "at": "2026-09-27T09:00:00Z", "other": "gv"}))

    def test_the_short_labels_of_the_seven_mornings(self):
        r = run_js(self, """
          const day = filters.fsShortDay, clock = filters.fsClock;
          out({ days: ["2026-09-29", "2026-11-01", "2027-01-01"].map((d) => [day(d, "en"), day(d, "es")]),
                clocks: ["2026-09-29T10:52:00Z", "2026-12-01T19:05:00Z", "2026-11-01T06:30:00Z"].map((t) => [clock(t, "en"), clock(t, "es")]),
                junk: [day("2026-02-30", "en"), day("soon", "es"), day(null, "en"), clock("soon", "en"), clock(null, "es"), clock(5, "en")] });
        """)
        self.assertEqual(r["days"], [["Tue, Sep 29", "Mar, 29 de sept"], ["Sun, Nov 1", "Dom, 1 de nov"],
                                     ["Fri, Jan 1", "Vie, 1 de ene"]])
        # Central time, without the zone (the subtitle says it once); the site's Spanish "a. m." (no-break spaces)
        self.assertEqual(r["clocks"], [["5:52 AM", "5:52 a. m."], ["1:05 PM", "1:05 p. m."],
                                       ["1:30 AM", "1:30 a. m."]])
        self.assertEqual(r["junk"], [""] * 6)
