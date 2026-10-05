"""scripts/ops/push_modules.py — which sources a push ALSO runs (update.yml "Decide what to sync" → run_all --also):
the ones only the full daily update reads, when the push changed a file or a part of config/site.yml they read
while they sync. Offline: the push payload, both copies of config/site.yml and git are stand-ins — or, in
RealGit, repositories in a temporary folder (a fetch there reads another folder, never the network).

  * Table       — every full-update-only source (run_all.FULL_ONLY, in run_all's order) is in the table, each of
                  its settings is in config/site.yml and named in its module; never the crawl, the stories or the
                  store;
  * Decide      — the files of the push → the sources (instagram.yml, data/geo, each part of config/site.yml),
                  in run_all's order; settings only the build reads add nothing; an unreadable earlier copy of
                  config/site.yml adds nothing (a notice says so);
  * PushFiles   — the files of the push from git (the event file GitHub writes for a workflow run lists none per
                  commit): the commits fetched one commit deep when missing, a payload's own lists added; when git
                  cannot say, those lists alone — and without any, none and a notice;
  * RealGit     — the same with git itself: the repository pushed to, GitHub's one-commit-deep checkout, a run that
                  waited its turn, a renamed file, a commit that cannot be fetched;
  * EarlierCopy — config/site.yml before the push, from git: fetched one commit deep only when it is missing;
                  any trouble → None;
  * Main        — what it writes for the plan step (also=, also_why=), that it never stops the step, and that it
                  never reads the push of the CI run the tests run in ($GITHUB_EVENT_PATH, $GITHUB_SHA).

    python -m unittest tests.test_push_modules -v        (or: python -m unittest discover -s tests)
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.ops import push_modules as P  # noqa: E402
from scripts.sync import run_all  # noqa: E402

GIT = P.Git                                             # (Main replaces P.Git by one with a stand-in)
SHA = "3f2a630" + "0" * 32 + "1"                       # 40 hex digits
AFTER = "c" * 40
CFG = """\
site:
  url: "https://example.org/site"
  timezone: "America/Chicago"
sources:
  grapevine:
    base: "https://www.aagrapevine.org"
    contribute: "/contribute"
    weekly_open: "/grapevine-weekly-open"
    audio_project: "/audio-portal"
    specialty: ["/store/greeting-cards"]
  lavina:
    base: "https://www.aalavina.org"
    contribute: "/temas-sugeridos"
    themes_page: "/recursos"
    themes_link: "\\\\btemas\\\\b"
    record_story: "/graba-tu-historia"
    record_tips: "/consejos-de-grabacion"
  crawler:
    minutes_per_run: 40
    user_agent: "Bot/1.0"
  youtube:
    channels: [{id: "UC1", handle: "@AAGrapevine"}]
  podcasts: [{key: "gv", feed: "https://feeds.example.org/gv/"}]
  instagram:
    accounts: [{key: "gv", username: "gv_account"}]
    keep_per_account: 130
lavina_weekly_open:
  enabled: true
  day: "thursday"   # every week
meetings:
  enabled: true
  feeds: [{id: "aadallas", name: "Dallas Intergroup"}]
spotlight:
  home_days: 60
  neta65_counties: ["Dallas", "Collin"]
booth:
  max_total_mb: 400
"""


def edit(text: str, old: str, new: str) -> str:
    assert old in text, old
    return text.replace(old, new, 1)


def event(*files: str, removed: tuple[str, ...] = (), before: str = SHA) -> dict:
    """A push payload that lists each commit's files (a webhook's): one commit that changed `files` (and a second
    one that removed `removed`)."""
    commits = [{"id": "a" * 40, "added": [], "modified": list(files), "removed": []}]
    if removed:
        commits.append({"id": "b" * 40, "added": [], "modified": [], "removed": list(removed)})
    return {"ref": "refs/heads/main", "before": before, "after": AFTER, "commits": commits}


def actions_event(before: str = SHA, after: str | None = AFTER) -> dict:
    """A push as the event file GitHub writes for a workflow run has it: its commits name no files."""
    ev = {"ref": "refs/heads/main", "before": before, "forced": False, "head_commit": {"id": after},
          "commits": [{"id": after, "tree_id": "e" * 40, "distinct": True, "message": "Edit the settings",
                       "timestamp": "2026-10-04T16:00:00-05:00", "author": {"name": "A"}, "committer": {"name": "A"}}]}
    if after:
        ev["after"] = after
    return ev


def git_stand_in(have: tuple[str, ...] = (), fetch: bool = True, diff: bytes | None = b"",
                 show: bytes | None = b"site: {}\n", fail: type[BaseException] | None = None):
    """A stand-in for subprocess.run running git → (run, calls): the checkout has the commits `have`, a fetch brings
    any other (unless `fetch` is False); git diff prints `diff`, git show `show` (None: git says no)."""
    calls: list[tuple[list[str], dict]] = []
    there = set(have)

    def run(cmd, **kw):
        calls.append((cmd, kw))
        if fail:
            raise fail("git", 1) if fail is subprocess.TimeoutExpired else fail("no git")
        if cmd[1] == "cat-file":
            return SimpleNamespace(returncode=0 if cmd[3].split("^")[0] in there else 1, stdout=b"")
        if cmd[1] == "fetch":
            if fetch:
                there.add(cmd[-1])
            return SimpleNamespace(returncode=0 if fetch else 128, stdout=b"")
        out = {"diff": diff, "show": show}.get(cmd[1])
        return SimpleNamespace(returncode=128 if out is None else 0, stdout=out or b"")
    return run, calls


class Table(unittest.TestCase):
    def test_every_full_update_only_source_in_run_alls_order(self):
        self.assertEqual(list(P.SETTINGS), [m for m in run_all.MODULES if m in run_all.FULL_ONLY])
        self.assertEqual(set(P.SETTINGS), set(run_all.FULL_ONLY))
        self.assertLessEqual(set(P.FILES.values()), set(run_all.FULL_ONLY))

    def test_never_the_crawl_the_stories_or_the_store(self):
        # many polite requests to the magazine sites each: they run every night
        self.assertFalse({"crawl", "articles", "shop"} & (set(P.SETTINGS) | set(P.FILES.values())))

    def test_each_setting_is_in_config_and_read_by_its_module(self):
        cfg = yaml.safe_load((ROOT / "config" / "site.yml").read_text(encoding="utf-8"))
        for module, paths in P.SETTINGS.items():
            src = (ROOT / "scripts" / "sync" / f"{module}.py").read_text(encoding="utf-8")
            for path in paths:
                with self.subTest(module=module, setting=path):
                    self.assertIsNotNone(P.value_at(cfg, path), "a setting config/site.yml has")
                    self.assertIn(path.rsplit(".", 1)[-1], src, "the module reads it")
        for path, module in P.FILES.items():
            self.assertTrue((ROOT / path).exists(), path)
        self.assertIn('MANUAL_FILE = CONTENT_DIR / "instagram.yml"', (ROOT / "scripts/sync/instagram.py").read_text(encoding="utf-8"))
        self.assertIn('"texas_places.json"', (ROOT / "scripts/sync/geo.py").read_text(encoding="utf-8"))


class Decide(unittest.TestCase):
    def decide(self, *files: str, new: str = CFG, old: str | None = CFG) -> tuple[list[str], dict, list[str]]:
        return P.decide(sorted(files), old, new)

    def test_the_files_a_source_reads(self):
        self.assertEqual(self.decide("content/instagram.yml")[:2], (["instagram"], {"instagram": ["content/instagram.yml"]}))
        self.assertEqual(self.decide("data/geo/texas_places.json")[0], ["meetings"])
        for other in ("data/geo/README.md", "content/bulletin/2026-10-04-x.md", "content/archive/aagrapevine_archive_2026-11-05.csv",
                      "content/events/2027-03-19-assembly.md", "src/pages/published.njk", "scripts/sync/meetings.py"):
            with self.subTest(file=other):
                self.assertEqual(self.decide(other), ([], {}, []), "the quick run reads it, or it is code")

    def test_each_part_of_the_settings(self):
        cases = [
            ('day: "thursday"', 'day: "friday"', ["weekly_open"]),
            ('feeds: [{id: "aadallas", name: "Dallas Intergroup"}]', 'feeds: [{id: "aadallas", name: "Dallas"}]', ["meetings"]),
            ('neta65_counties: ["Dallas", "Collin"]', 'neta65_counties: ["Dallas", "Collin", "Rockwall"]', ["meetings"]),
            ('channels: [{id: "UC1", handle: "@AAGrapevine"}]', 'channels: []', ["youtube"]),
            ("keep_per_account: 130", "keep_per_account: 140", ["instagram"]),
            ('themes_link: "\\\\btemas\\\\b"', 'themes_link: "temas de la revista"', ["editorial"]),
            ('record_tips: "/consejos-de-grabacion"', 'record_tips: "/consejos"', ["audio_project"]),
            ('base: "https://www.aagrapevine.org"', 'base: "https://aagrapevine.org"',
             ["editorial", "weekly_open", "audio_project", "events_external"]),
            ('base: "https://www.aalavina.org"', 'base: "https://aalavina.org"',
             ["editorial", "audio_project", "events_external"]),
        ]
        for old, new, want in cases:
            with self.subTest(change=new):
                also, why, notices = self.decide("config/site.yml", new=edit(CFG, old, new))
                self.assertEqual((also, notices), (want, []))
                self.assertTrue(all(w[0].startswith("config/site.yml: ") for w in why.values()), why)

    def test_what_only_the_build_reads_adds_nothing(self):
        # every run rebuilds the site data and the pages: the store, the crawl, the podcasts, the booth, the home
        # page's window, the site's own address, the robot's name — and a comment
        for old, new in (('specialty: ["/store/greeting-cards"]', "specialty: []"), ("minutes_per_run: 40", "minutes_per_run: 0"),
                         ('feed: "https://feeds.example.org/gv/"', 'feed: "https://feeds.example.org/new/"'),
                         ("max_total_mb: 400", "max_total_mb: 300"), ("home_days: 60", "home_days: 30"),
                         ('url: "https://example.org/site"', 'url: "https://example.org/new"'),
                         ('user_agent: "Bot/1.0"', 'user_agent: "Bot/2.0"'), ("# every week", "# each week")):
            with self.subTest(change=new):
                self.assertEqual(self.decide("config/site.yml", new=edit(CFG, old, new)), ([], {}, []))

    def test_run_alls_order_and_every_reason(self):
        new = edit(edit(CFG, 'day: "thursday"', 'day: "friday"'), "keep_per_account: 130", "keep_per_account: 1")
        new = edit(new, 'neta65_counties: ["Dallas", "Collin"]', 'neta65_counties: ["Dallas"]')
        also, why, _n = self.decide("data/geo/texas_places.json", "config/site.yml", "content/instagram.yml", new=new)
        self.assertEqual(also, ["instagram", "weekly_open", "meetings"])
        self.assertEqual(P.reason(why["instagram"]), "content/instagram.yml, config/site.yml: sources.instagram")
        self.assertEqual(P.reason(why["meetings"]), "data/geo/texas_places.json, config/site.yml: spotlight.neta65_counties")
        self.assertEqual(P.reason(why["weekly_open"]), "config/site.yml: lavina_weekly_open")

    def test_an_earlier_copy_that_cannot_be_read_adds_nothing(self):
        new = edit(CFG, 'day: "thursday"', 'day: "friday"')
        for old in (None, "a: [unclosed", "- just a list"):
            with self.subTest(old=old):
                also, why, notices = self.decide("config/site.yml", "content/instagram.yml", new=new, old=old)
                self.assertEqual(also, ["instagram"], "the other files still count")
                self.assertEqual(len(notices), 1)
                self.assertIn("its copy from before the push could not be read", notices[0])
                self.assertIn("after the next one", notices[0])
        also, _why, notices = self.decide("config/site.yml", new="a: [unclosed")
        self.assertEqual(also, [])
        self.assertIn("config/site.yml changed, but it could not be read", notices[0])
        # a settings file that was empty before (or is new): every part it now has is new
        self.assertEqual(self.decide("config/site.yml", old="")[0], list(P.SETTINGS))

    def test_the_changed_files_of_every_commit(self):
        ev = event("content/instagram.yml", "README.md", removed=("data/geo/texas_places.json",))
        ev["commits"][0]["added"] = ["content/bulletin/new.md", ""]
        self.assertEqual(P.changed_files(ev), ["README.md", "content/bulletin/new.md", "content/instagram.yml",
                                               "data/geo/texas_places.json"])
        self.assertEqual(P.changed_files({}), [])
        self.assertEqual(P.changed_files({"commits": None}), [])
        self.assertEqual(P.changed_files({"commits": ["x", {"modified": None}, {"added": "content/instagram.yml"}]}),
                         [], "a list of files, or nothing")
        self.assertEqual(P.changed_files(actions_event()), [], "GitHub's event file for a run lists no files")


class PushFiles(unittest.TestCase):
    def changes(self, ev: dict, head: str | None = None, **git) -> tuple[list[str], str, list[str], list[list[str]]]:
        run, calls = git_stand_in(**git)
        return (*P.push_changes(ev, GIT(run=run), head), [c[0][1:] for c in calls])

    def test_from_git(self):
        # GitHub checks out the branch's newest commit, one commit deep: the one before the push is fetched first
        got, source, notices, calls = self.changes(actions_event(), have=(AFTER,),
                                                   diff=b"content/instagram.yml\0config/site.yml\0src/a b.njk\0")
        self.assertEqual(got, ["config/site.yml", "content/instagram.yml", "src/a b.njk"])
        self.assertEqual((source, notices), ("git diff 3f2a630..ccccccc", []))
        self.assertEqual(calls, [["cat-file", "-e", f"{SHA}^{{commit}}"],
                                 ["fetch", "--quiet", "--no-tags", "--depth=1", "origin", SHA],
                                 ["cat-file", "-e", f"{AFTER}^{{commit}}"],
                                 ["diff", "--name-only", "--no-renames", "-z", SHA, AFTER]])
        # a run that waited its turn checked out a later commit: the push's own is fetched too
        _got, _source, _notices, calls = self.changes(actions_event())
        self.assertEqual([c[0] for c in calls], ["cat-file", "fetch", "cat-file", "fetch", "diff"])
        # an event file that names no `after`: the run's own commit ($GITHUB_SHA), in any case
        got, source, _notices, calls = self.changes(actions_event(after=None), head=AFTER.upper(), diff=b"x.md\0")
        self.assertEqual((got, source, calls[-1][-1]), (["x.md"], "git diff 3f2a630..ccccccc", AFTER))

    def test_a_payloads_own_lists_are_added(self):
        got, _source, notices, _calls = self.changes(event("data/geo/texas_places.json"), diff=b"config/site.yml\0")
        self.assertEqual((got, notices), (["config/site.yml", "data/geo/texas_places.json"], []))

    def test_when_git_cannot_say(self):
        why = "the commit before it (3f2a630) could not be fetched"
        # a payload that lists the files: those
        got, source, notices, calls = self.changes(event("content/instagram.yml"), fetch=False)
        self.assertEqual((got, source), (["content/instagram.yml"], "the files its event file lists"))
        self.assertEqual(notices, [f"Could not compare this push in git — {why} —, so the files its event file lists "
                                   "were used."])
        self.assertNotIn("diff", [c[0] for c in calls])
        # GitHub's event file for a run: nothing — and a notice says so
        got, source, notices, _calls = self.changes(actions_event(), fetch=False)
        self.assertEqual((got, source), ([], ""))
        self.assertEqual(notices, [f"Could not tell which files this push changed — {why} —, so no other source was "
                                   "added for it: a source only the full daily update reads shows its changes after "
                                   "the next one."])
        for kw, said in (({"diff": None}, "git could not compare 3f2a630 with ccccccc"),
                         ({"fail": OSError}, "git did not answer (OSError)"),
                         ({"fail": subprocess.TimeoutExpired}, "git did not answer (TimeoutExpired)")):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                got, _source, notices, _calls = self.changes(actions_event(), **kw)
                self.assertEqual(got, [])
                self.assertIn(f"— {said} —", notices[0])

    def test_no_commit_before_the_push_and_no_event(self):
        # a new branch (000…0): git is not asked; a payload's lists, or nothing
        got, _source, notices, calls = self.changes(event("content/instagram.yml", before="0" * 40))
        self.assertEqual((got, calls), (["content/instagram.yml"], []))
        self.assertIn("— there is no commit before it (a new branch) —, so the files its event file lists", notices[0])
        got, _source, notices, calls = self.changes(actions_event(before="0" * 40))
        self.assertEqual((got, calls), ([], []))
        self.assertIn("Could not tell which files this push changed — there is no commit before it (a new branch)",
                      notices[0])
        got, _source, notices, calls = self.changes({}, head=AFTER)
        self.assertEqual((got, calls), ([], []))
        self.assertIn("— GitHub's event file could not be read —", notices[0])
        for bad in ("HEAD", "abc", SHA + "; rm -rf /", None, 7):
            with self.subTest(before=bad):
                self.assertEqual(self.changes(actions_event(before=bad))[3], [], "not a commit id: git is not asked")

    def test_a_commit_is_fetched_once(self):
        # the comparison fetches the commit before the push; the earlier copy of config/site.yml reads it then
        run, calls = git_stand_in(have=(AFTER,), diff=b"config/site.yml\0")
        git = GIT(run=run)
        self.assertEqual(P.push_changes(actions_event(), git)[0], ["config/site.yml"])
        self.assertEqual(P.previous_config(SHA, git), "site: {}\n")
        self.assertEqual([c[0][1] for c in calls].count("fetch"), 1)
        # a fetch that failed (or never ended) is not tried again
        run, calls = git_stand_in(fail=subprocess.TimeoutExpired)
        git = GIT(run=run)
        self.assertEqual(P.push_changes(event("config/site.yml"), git)[0], ["config/site.yml"])
        self.assertIsNone(P.previous_config(SHA, git))
        self.assertEqual(len(calls), 1)


class RealGit(unittest.TestCase):
    """The repository pushed to (`origin`: the commit before the push, the push's commit) in a temporary folder,
    copies of it one commit deep (GitHub's checkout) that fetch what they lack from it, and payloads as GitHub writes
    them for a workflow run — no files per commit."""

    def setUp(self):
        if not shutil.which("git"):
            self.skipTest("needs git")
        tmp = tempfile.TemporaryDirectory(prefix="gv-push-git-", ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / "no-settings").write_text("", encoding="utf-8")
        # git here knows nothing of this computer's own settings (a signing key, line ends, …) and never asks for a
        # password; never the push of a CI run either
        env = mock.patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": str(self.tmp / "no-settings"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.org", "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.org", "GITHUB_EVENT_PATH": "", "GITHUB_SHA": ""})
        env.start()
        self.addCleanup(env.stop)
        self.origin = self.tmp / "origin"
        self.git(self.tmp, "init", "-q", "origin")
        self.git(self.origin, "config", "uploadpack.allowReachableSHA1InWant", "true")   # as on GitHub
        self.before = self.commit({P.CONFIG: CFG, "content/instagram.yml": "posts: []\n", "src/pages/index.njk": "a\n",
                                   "data/geo/texas_places.json": '{"places": []}\n'})
        self.after = self.commit({P.CONFIG: edit(CFG, 'day: "thursday"', 'day: "friday"'), "src/pages/index.njk": "b\n",
                                  "content/instagram.yml": "posts: [{url: 'https://www.instagram.com/p/x/'}]\n"})

    def git(self, cwd: Path, *args: str) -> str:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def commit(self, files: dict[str, str | None]) -> str:
        """A commit of `origin` that writes these files (None: deletes it) → its id."""
        for path, text in files.items():
            p = self.origin / path
            if text is None:
                p.unlink()
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-q", "-m", "an edit")
        return self.git(self.origin, "rev-parse", "HEAD")

    def checkout(self) -> Path:
        """The branch's newest commit, one commit deep — as actions/checkout leaves it."""
        dest = self.tmp / f"checkout-{len(list(self.tmp.glob('checkout-*')))}"
        self.git(self.tmp, "clone", "-q", "--depth=1", self.origin.as_uri(), dest.name)
        return dest

    def has(self, repo: Path, commit: str) -> bool:
        r = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=repo, capture_output=True)
        return r.returncode == 0

    def main(self, repo: Path, ev: dict) -> tuple[dict[str, str], str]:
        (self.tmp / "event.json").write_text(json.dumps(ev), encoding="utf-8")
        out = self.tmp / "out.txt"
        out.write_text("", encoding="utf-8")
        log = io.StringIO()
        with redirect_stdout(log):
            self.assertEqual(P.main(["--event", str(self.tmp / "event.json"), "--repo", str(repo), "--output", str(out)]), 0)
        return dict(ln.split("=", 1) for ln in out.read_text(encoding="utf-8").splitlines()), log.getvalue()

    def test_the_repository_pushed_to(self):
        got, log = self.main(self.origin, actions_event(self.before, self.after))
        self.assertEqual(got, {"also": "instagram,weekly_open",
                               "also_why": "instagram (content/instagram.yml); weekly_open (config/site.yml: lavina_weekly_open)"})
        self.assertIn(f"Files this push changed: 3 (git diff {self.before[:7]}..{self.after[:7]}).", log)
        self.assertNotIn("::notice", log)

    def test_githubs_checkout_one_commit_deep(self):
        repo = self.checkout()
        self.assertFalse(self.has(repo, self.before), "the commit before the push is not in the checkout")
        got, log = self.main(repo, actions_event(self.before, self.after))
        self.assertEqual(got["also"], "instagram,weekly_open")
        self.assertTrue(self.has(repo, self.before), "fetched")
        self.assertNotIn("::notice", log)
        # an event file that names no `after`: the run's commit ($GITHUB_SHA)
        with mock.patch.dict(os.environ, {"GITHUB_SHA": self.after}):
            got, _log = self.main(self.checkout(), actions_event(self.before, None))
        self.assertEqual(got["also"], "instagram,weekly_open")

    def test_a_run_that_waited_its_turn(self):
        # the branch moved on meanwhile (the previous run's data commit, a later edit with a run of its own): the
        # push's own last commit is fetched too, and only what the push changed counts
        later = self.commit({"data/geo/texas_places.json": '{"places": ["Tyler"]}\n'})
        repo = self.checkout()
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), later)
        got, _log = self.main(repo, actions_event(self.before, self.after))
        self.assertEqual(got["also"], "instagram,weekly_open", "not meetings: the places list changed after the push")
        got, _log = self.main(repo, actions_event(self.after, later))
        self.assertEqual(got, {"also": "meetings", "also_why": "meetings (data/geo/texas_places.json)"})

    def test_a_renamed_file_counts_with_both_names(self):
        moved = self.commit({"data/geo/texas_places.json": None, "data/geo/texas_places_2026.json": '{"places": []}\n'})
        got, _log = self.main(self.checkout(), actions_event(self.after, moved))
        self.assertEqual(got["also"], "meetings")

    def test_a_commit_that_cannot_be_fetched(self):
        got, log = self.main(self.checkout(), actions_event("d" * 40, self.after))
        self.assertEqual(got, {"also": "", "also_why": ""})
        self.assertIn("::notice title=Push run::Could not tell which files this push changed — the commit before it "
                      "(ddddddd) could not be fetched —", log)


class EarlierCopy(unittest.TestCase):
    def test_fetched_one_commit_deep_only_when_missing(self):
        run, calls = git_stand_in()
        self.assertEqual(P.previous_config(SHA, GIT(run=run)), "site: {}\n")
        self.assertEqual([c[0][1] for c in calls], ["cat-file", "fetch", "show"])
        self.assertEqual(calls[1][0], ["git", "fetch", "--quiet", "--no-tags", "--depth=1", "origin", SHA])
        self.assertEqual(calls[2][0], ["git", "show", f"{SHA}:config/site.yml"])
        self.assertEqual(calls[1][1]["env"]["GIT_TERMINAL_PROMPT"], "0", "never a password prompt")
        self.assertTrue(all(c[1].get("timeout") for c in calls), "never waits for ever")
        run, calls = git_stand_in(have=(SHA,))
        self.assertEqual(P.previous_config(SHA.upper(), GIT(run=run)), "site: {}\n")
        self.assertEqual([c[0][1] for c in calls], ["cat-file", "show"], "there already: no fetch")

    def test_any_trouble_is_none(self):
        for before in ("", "0" * 40, "HEAD", "abc", SHA + "; rm -rf /", None):
            run, calls = git_stand_in()
            with self.subTest(before=before):
                self.assertIsNone(P.previous_config(before, GIT(run=run)))
                self.assertEqual(calls, [], "no commit before the push (or not a commit): git is not asked")
        run, calls = git_stand_in(fetch=False)
        self.assertIsNone(P.previous_config(SHA, GIT(run=run)), "the fetch failed")
        self.assertEqual([c[0][1] for c in calls], ["cat-file", "fetch"])
        run, _calls = git_stand_in(have=(SHA,), show=None)
        self.assertIsNone(P.previous_config(SHA, GIT(run=run)), "no such file then")
        for fail in (OSError, subprocess.TimeoutExpired):
            run, _calls = git_stand_in(fail=fail)
            self.assertIsNone(P.previous_config(SHA, GIT(run=run)))

    def test_with_the_real_git(self):
        # this checkout's own newest commit is there already: read without a fetch (offline)
        if not shutil.which("git"):
            self.skipTest("needs git")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        if head.returncode != 0:
            self.skipTest("not a git checkout")
        want = subprocess.run(["git", "show", "HEAD:config/site.yml"], cwd=ROOT, capture_output=True)
        calls = []

        def run(cmd, **kw):
            calls.append(cmd[1])
            return subprocess.run(cmd, **kw)
        got = P.previous_config(head.stdout.strip(), GIT(ROOT, run=run))
        self.assertEqual(got, want.stdout.decode("utf-8"))
        self.assertNotIn("fetch", calls)


class Main(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gv-push-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "new.yml").write_text(edit(CFG, 'day: "thursday"', 'day: "friday"'), encoding="utf-8")
        (self.tmp / "old.yml").write_text(CFG, encoding="utf-8")
        # Never the push of the CI run these tests run in (Code check runs them on a push: its event file and its
        # commit are in the environment) — and never the real git: a stand-in whose checkout has the push's own
        # commit and cannot fetch (a test can give it more).
        env = mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": "", "GITHUB_SHA": ""})
        env.start()
        self.addCleanup(env.stop)
        self.stand_in(have=(AFTER,), fetch=False)

    def stand_in(self, **kw) -> None:
        run, self.git_calls = git_stand_in(**kw)
        p = mock.patch.object(P, "Git", lambda root=P.ROOT: GIT(root, run=run))
        p.start()
        self.addCleanup(p.stop)

    def main(self, ev: dict | str | None, *extra: str) -> tuple[dict[str, str], str]:
        args = ["--config", str(self.tmp / "new.yml"), "--output", str(self.tmp / "out.txt"), *extra]
        if ev is not None:
            (self.tmp / "event.json").write_text(ev if isinstance(ev, str) else json.dumps(ev), encoding="utf-8")
            args += ["--event", str(self.tmp / "event.json")]
        (self.tmp / "out.txt").write_text("", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(P.main(args), 0)
        lines = (self.tmp / "out.txt").read_text(encoding="utf-8").splitlines()
        return dict(ln.split("=", 1) for ln in lines), out.getvalue()

    def test_what_the_plan_step_reads(self):
        got, log = self.main(event("config/site.yml", "content/instagram.yml"), "--previous-config", str(self.tmp / "old.yml"))
        self.assertEqual(got, {"also": "instagram,weekly_open",
                               "also_why": "instagram (content/instagram.yml); weekly_open (config/site.yml: lavina_weekly_open)"})
        self.assertIn("Also run for this push: instagram (content/instagram.yml); weekly_open", log)
        got, log = self.main(event("src/pages/index.njk"))
        self.assertEqual(got, {"also": "", "also_why": ""})
        self.assertIn("No other source needs to run for this push.", log)

    def test_the_earlier_copy_from_git(self):
        with mock.patch.object(P, "previous_config", return_value=None) as prev:
            got, log = self.main(event("config/site.yml"))
        prev.assert_called_once()
        self.assertEqual(prev.call_args.args[0], SHA)
        self.assertEqual(got["also"], "")
        self.assertIn("::notice title=Push run::config/site.yml changed, but its copy from before the push could not be read", log)
        with mock.patch.object(P, "previous_config", return_value=CFG):
            got, _log = self.main(event("config/site.yml"))
        self.assertEqual(got["also"], "weekly_open")
        with mock.patch.object(P, "previous_config") as prev:
            self.main(event("content/instagram.yml"))
        prev.assert_not_called()                     # git is asked only when config/site.yml changed

    def test_githubs_own_event_file(self):
        # no files per commit: they come from git — the commit before the push is fetched, then compared with the
        # push's own; config/site.yml as it was before the push is read from git too
        self.stand_in(have=(AFTER,), diff=b"config/site.yml\0content/instagram.yml\0src/pages/index.njk\0",
                      show=CFG.encode("utf-8"))
        got, log = self.main(actions_event())
        self.assertEqual(got, {"also": "instagram,weekly_open",
                               "also_why": "instagram (content/instagram.yml); weekly_open (config/site.yml: lavina_weekly_open)"})
        self.assertIn("Files this push changed: 3 (git diff 3f2a630..ccccccc).", log)
        self.assertEqual([c[0][1] for c in self.git_calls], ["cat-file", "fetch", "cat-file", "diff", "show"])
        self.assertNotIn("::notice", log)
        # … and when git cannot say: nothing, and a notice
        self.stand_in(have=(AFTER,), fetch=False)
        got, log = self.main(actions_event())
        self.assertEqual(got, {"also": "", "also_why": ""})
        self.assertIn("::notice title=Push run::Could not tell which files this push changed — the commit before it "
                      "(3f2a630) could not be fetched —, so no other source was added for it", log)
        # a new branch (no commit before it): git is not asked
        self.stand_in()
        got, log = self.main(actions_event(before="0" * 40))
        self.assertEqual((got["also"], self.git_calls), ("", []))
        self.assertIn("— there is no commit before it (a new branch) —", log)

    def test_it_never_stops_the_step(self):
        for ev in (None, "{ not json", "[1, 2]"):
            with self.subTest(event=ev):
                got, log = self.main(ev)
                self.assertEqual(got, {"also": "", "also_why": ""})
                self.assertIn("— GitHub's event file could not be read —", log)
        self.assertEqual(self.git_calls, [], "nothing to compare: git is not asked")
        with mock.patch.object(P, "decide", side_effect=RuntimeError("boom")):
            got, log = self.main(event("content/instagram.yml"))
        self.assertEqual(got, {"also": "", "also_why": ""})
        self.assertIn("::notice title=Push run::Could not work out which other sources this push needs (RuntimeError: boom)", log)

    def test_never_the_ci_runs_own_push(self):
        # Code check runs these tests on a push, with that push's event file and commit in the environment: a test
        # that names no event file must not read them (it would see this very push, and fetch from GitHub)
        ci = self.tmp / "ci.json"
        ci.write_text(json.dumps(event("config/site.yml", "content/instagram.yml")), encoding="utf-8")
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(ci), "GITHUB_SHA": AFTER}):
            got, _log = self.main(None)
        self.assertEqual(got["also"], "instagram", "an event file named in the environment is read (as on GitHub)")
        got, _log = self.main(None)
        self.assertEqual(got, {"also": "", "also_why": ""}, "setUp keeps the CI run's own push out")


if __name__ == "__main__":
    unittest.main()
