"""The robots.txt at the root of the site's address — a step of the Weekly link check
(.github/workflows/link-check.yml, job "Check links", step "Check the root robots.txt (politely)"):

    python -m scripts.ops.root_robots           # the address: env SITE_URL, else site.url in config/site.yml
    python -m scripts.ops.root_robots --site https://neta65.github.io/aagrapevine      # on a computer

Why it exists: crawlers read robots.txt only at the root of an address (RFC 9309 §2.3; Google: "crawlers don't
check for robots.txt files in subdirectories"). The site is a GitHub Pages PROJECT site, so its own
/aagrapevine/robots.txt (src/robots.njk) is never read; the file that counts is https://neta65.github.io/robots.txt,
which only the NETA65 account's own user-site repository (NETA65/neta65.github.io) publishes — its files are
docs/user-site/, the owner's steps README → "Search engines". One wrong line there ("Disallow: /") would hide this
site, and every other NETA65 site under that address, from every search engine, and nothing else would notice.
So once a week this reads it, with the site's own robot (its name, config/site.yml sources.crawler.user_agent;
one request, retried politely on a 429 / 5xx answer — robots.txt itself is always allowed, RFC 9309 §2.2.2):

  * 404       → "not set up yet": the owner's step is still to do. Not a problem — with no robots.txt there
                every crawler may visit everything; only the sitemap's address is not announced.
  * 200       → read with Protego (the parser the site's polite robot uses): Googlebot and Bingbot must be allowed
                to fetch the site (PATHS), and its Sitemap lines must include <site>/sitemap.xml. It also says
                whether the AI-training crawlers are kept out (the owner's optional choice — never a problem) and
                names any AI-search crawler that is kept out (a note: the site then misses those answers).
  * otherwise → a problem: another answer, no answer, or a redirect (a custom domain set on the user site moves
                every NETA65 project site to it).

A site at the root of its own address (a custom domain, README §12: site.url has no path) is skipped: its own
robots.txt is then the root file.

It writes lychee/robots.md (the "report" job adds it to the weekly issue), adds the same text to the run summary
and sets the step output `problems` (the number found; anything but 0 opens or updates the issue). The exit code is
always 0: the check reports, it never fails the job.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from protego import Protego

REPORT = Path("lychee") / "robots.md"
SEARCH_ENGINES = ("Googlebot", "Bingbot")                       # must be allowed: a problem otherwise
# what Googlebot and Bingbot must be able to fetch: the two home pages, and real files a page needs to be read the
# way people see it — a stylesheet, a script, a data file the pages fill their lists from — and the sitemap (a
# pattern rule such as "Disallow: /*.css$" or "Disallow: /*.json" keeps a folder open but hides these)
PATHS = ("/", "/es/", "/assets/css/main.css", "/assets/js/app.js", "/search-index.json", "/sitemap.xml")
AI_TRAINING = ("GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "Applebot-Extended")   # the owner's choice
AI_SEARCH = ("OAI-SearchBot", "Claude-SearchBot", "PerplexityBot")                        # a note when kept out
USER_SITE = "the NETA65/neta65.github.io repository"
OWNER_STEP = "owner step: README → Search engines"


@dataclass
class Result:
    """What the check found: state "skipped" | "missing" | "ok" | "problem", the robots.txt address, the problems
    (each a line for the issue) and notes (information only)."""
    state: str
    url: str = ""
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def root_robots_url(site: str) -> str | None:
    """https://neta65.github.io/robots.txt for https://neta65.github.io/aagrapevine — None when the site is the root
    of its address (a custom domain: its own robots.txt is the root file)."""
    parts = urlsplit(site.strip())
    if not parts.scheme or not parts.netloc or parts.path.strip("/") == "":
        return None
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def judge(text: str, site: str) -> tuple[list[str], list[str]]:
    """A robots.txt's rules for the site → (problems, notes)."""
    site = site.rstrip("/")
    try:
        rules = Protego.parse(text)
    except Exception as e:  # noqa: BLE001 — a file the parser cannot read at all
        return [f"it could not be read ({e})"], []
    problems, notes = [], []
    for bot in SEARCH_ENGINES:
        shut = [site + p for p in PATHS if not rules.can_fetch(site + p, bot)]
        if shut:
            problems.append(f"{bot} may not fetch {', '.join(shut)} — a Disallow line hides the site from "
                            f"{'Google' if bot == 'Googlebot' else 'Bing'}")
    sitemap = f"{site}/sitemap.xml"
    if sitemap not in [s.strip() for s in rules.sitemaps]:
        problems.append(f"no line `Sitemap: {sitemap}` — search engines no longer learn where the sitemap is")
    out = [bot for bot in AI_TRAINING if not rules.can_fetch(site + "/", bot)]
    notes.append(f"AI-model training crawlers kept out (the owner's choice): {', '.join(out)}." if out
                 else "AI-model training crawlers are not kept out (the default; README → Search engines has the "
                      "optional lines).")
    shut = [bot for bot in AI_SEARCH if not rules.can_fetch(site + "/", bot)]
    if shut:
        notes.append(f"Kept out of AI search answers: {', '.join(shut)} — the site does not show in their answers.")
    return problems, notes


def check(site: str, get: Callable[[str], Any]) -> Result:
    """Read the root robots.txt of `site` with `get` (url → a response with .status_code, .text, .url, or None when
    nothing answered) and judge it."""
    url = root_robots_url(site)
    if url is None:
        return Result("skipped")
    r = get(url)
    if r is None:
        return Result("problem", url, ["no answer (GitHub Pages down, or the address is wrong?) — try again later"])
    if getattr(r, "history", None):
        return Result("problem", url, [f"it redirects to {getattr(r, 'url', '') or '?'} — a custom domain set on "
                                       f"{USER_SITE}? That moves every NETA65 site to it; remove it there "
                                       "(Settings → Pages)"])
    if r.status_code == 404:
        return Result("missing", url)
    if r.status_code != 200:
        return Result("problem", url, [f"HTTP {r.status_code} (expected 200, or 404 while {USER_SITE} is not set up)"])
    problems, notes = judge(r.text or "", site)
    return Result("problem" if problems else "ok", url, problems, notes)


def report(result: Result, site: str) -> str:
    """The Markdown for the run summary and the weekly issue."""
    head = f"## The root robots.txt ({result.url})" if result.url else "## The root robots.txt"
    lines = ["", head, ""]
    if result.state == "skipped":
        lines.append(f"Skipped: the site is at the root of its own address ({site}), so its own robots.txt is the "
                     "one search engines read.")
    elif result.state == "missing":
        lines.append(f"Not set up yet ({OWNER_STEP}). Not a problem: with no robots.txt there, search engines may "
                     "crawl everything — they only do not learn the sitemap's address from it.")
    elif result.state == "ok":
        lines.append(f"OK: Googlebot and Bingbot may crawl {site.rstrip('/')}/ and it names the sitemap.")
    else:
        lines += [f"Fix it in **{USER_SITE}** (its robots.txt; the right text is **docs/user-site/robots.txt** "
                  f"in this repository, {OWNER_STEP}):", ""]
        lines += [f"- [ ] {p}" for p in result.problems]
    if result.notes:
        lines.append("")
        lines += [f"- {n}" for n in result.notes]
    return "\n".join(lines) + "\n"


def polite_get(url: str) -> Any:
    """GET with the site's own robot: its name, retries with backoff on 429 / 5xx (scripts/sync/common.py
    PoliteSession). robots.txt itself is always allowed (RFC 9309 §2.2.2), so this one request skips reading it
    first."""
    from scripts.sync.common import PoliteSession
    return PoliteSession(min_delay=5.0, respect_robots=False).get(url, timeout=40)


def append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)


def main(argv: list[str] | None = None, *, get: Callable[[str], Any] | None = None,
         env: dict[str, str] | None = None, cfg: dict | None = None, out: Path = REPORT) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.ops.root_robots", description=__doc__.split("\n\n")[0])
    ap.add_argument("--site", help="the site's address (default: env SITE_URL, else site.url in config/site.yml)")
    a = ap.parse_args(argv)
    try:                                   # a Windows console (cp1252) prints "?" for an arrow instead of stopping
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError, OSError):      # not a real console (a test's StringIO)
        pass
    env = os.environ if env is None else env
    site = a.site or env.get("SITE_URL") or ""
    if not site:
        if cfg is None:
            from scripts.sync.common import load_config
            cfg = load_config()
        site = str((cfg.get("site") or {}).get("url") or "")
    site = site.strip().rstrip("/")
    if not site:
        text = "\n## The root robots.txt\n\nNot checked: no site address (SITE_URL or site.url in config/site.yml).\n"
        result = Result("skipped")
    else:
        result = check(site, get or polite_get)
        text = report(result, site)
    sys.stdout.write(text)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    append(env.get("GITHUB_STEP_SUMMARY"), text)
    append(env.get("GITHUB_OUTPUT"), f"problems={len(result.problems)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
