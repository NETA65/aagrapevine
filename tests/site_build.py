"""A build of the website for the tests, made once and kept while nothing it is built from changes
(tests/ is on sys.path under "unittest discover -s tests"):

    from site_build import cached_build
    r = cached_build({"PATH_PREFIX": "/aagrapevine/", "I18N_STRICT": "1"})   # → BuildResult
    r.returncode, r.stderr, r.site                                            # (r.site: the built folder)

The build is `eleventy --quiet --output <folder>` from the repository's root, with os.environ and `env` (a value of
None removes a variable). It is kept in .cache/test-builds/<key>/ (git ignores .cache) and used again — by the next
test module that asks for the same build, and by the next run of the tests — while its key is the same: a
fingerprint of every file the site is built from (src/, eleventy/, eleventy.config.js, config/, content/, data/,
package-lock.json: each file's path, size and modification time), the variables that steer the build, the Node.js
version and the day (pages say "today", "upcoming", "past"). A failed build is never kept. GV_TEST_BUILD_CACHE=0
builds afresh every time (a temporary folder, removed when the run ends).
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "test-builds"
SOURCES = ("src", "eleventy", "eleventy.config.js", "config", "content", "data", "package-lock.json")
# the variables that change what a build writes (and so its key)
STEERING = ("PATH_PREFIX", "SITE_URL", "I18N_STRICT", "STRICT_BUILD", "ONLY", "SITE_DATA", "POSTER_SHARE", "LASTMOD",
            "LASTMOD_STORE", "BOOTH_CSV", "BOOTH_DRIVE", "BOOTH_MANIFEST", "BOOTH_MEDIA", "PRESENTATIONS_DIR",
            "WRITERS_ARCHIVE", "MONTHLY_NOW", "GITHUB_ACTIONS", "BUILD_WARNINGS")
_MEMO: dict[str, "BuildResult"] = {}


@dataclass
class BuildResult:
    returncode: int
    stdout: str
    stderr: str
    site: Path
    cached: bool = False


def node_path() -> str | None:
    return shutil.which("node")


def fingerprint() -> str:
    """Every file the site is built from: its path, size and modification time."""
    h = hashlib.sha256()
    for name in SOURCES:
        p = ROOT / name
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else []
        for f in files:
            if "__pycache__" in f.parts:
                continue
            st = f.stat()
            h.update(f"{f.relative_to(ROOT).as_posix()}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    return h.hexdigest()


def build_env(env: dict[str, str | None]) -> dict[str, str]:
    full = {**os.environ, "NODE_NO_WARNINGS": "1"}
    for k, v in env.items():
        if v is None:
            full.pop(k, None)
        else:
            full[k] = v
    return full


def key_of(full: dict[str, str]) -> str:
    node = subprocess.run([node_path() or "node", "--version"], capture_output=True, text=True).stdout.strip()
    steer = {k: full.get(k) for k in STEERING}
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob = json.dumps({"files": fingerprint(), "env": steer, "node": node, "day": day}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def cached_build(env: dict[str, str | None], timeout: int = 900) -> BuildResult:
    """The site built with `env` (on top of os.environ) — from the cache when an identical build is there."""
    full = build_env(env)
    key = key_of(full)
    if key in _MEMO:
        return _MEMO[key]
    use_cache = os.environ.get("GV_TEST_BUILD_CACHE", "1") != "0"
    folder = CACHE / key if use_cache else Path(tempfile.mkdtemp(prefix="gv-test-build-"))
    if not use_cache:
        atexit.register(shutil.rmtree, folder, True)
    done = folder / "build.json"
    if use_cache and done.is_file() and (folder / "site").is_dir():
        info = json.loads(done.read_text(encoding="utf-8"))
        res = BuildResult(0, info.get("stdout", ""), info.get("stderr", ""), folder / "site", cached=True)
        _MEMO[key] = res
        return res
    shutil.rmtree(folder / "site", ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([node_path(), str(ROOT / "node_modules" / "@11ty" / "eleventy" / "cmd.cjs"), "--quiet",
                        "--output", str(folder / "site")], cwd=ROOT, env=full, capture_output=True, text=True,
                       encoding="utf-8", timeout=timeout)
    res = BuildResult(r.returncode, r.stdout, r.stderr, folder / "site")
    if r.returncode == 0 and use_cache:
        done.write_text(json.dumps({"stdout": r.stdout[-20000:], "stderr": r.stderr[-20000:]}), encoding="utf-8")
        _prune(keep=key)
    elif r.returncode != 0 and use_cache:
        shutil.rmtree(folder, ignore_errors=True)            # never keep a failed build
    _MEMO[key] = res
    return res


def _prune(keep: str, max_builds: int = 4) -> None:
    """Keep the newest few builds only (each is the whole site, ~150 MB)."""
    try:
        builds = sorted((d for d in CACHE.iterdir() if d.is_dir() and d.name != keep),
                        key=lambda d: d.stat().st_mtime, reverse=True)
    except OSError:
        return
    for d in builds[max_builds - 1:]:
        shutil.rmtree(d, ignore_errors=True)
