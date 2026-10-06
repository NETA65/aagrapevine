"""Open a built website in a real browser, on this computer only — for the browser checks (tests/browser) and the
monthly posters' share pictures (scripts/ops/poster_share.py).

    from scripts.ops.site_browser import SiteServer, launch, site_prefix
    with SiteServer(site) as server, sync_playwright() as pw:
        browser, channel = launch(pw)
        page = browser.new_page()
        page.goto(server.address("monthly/"))

SiteServer serves the folder the way GitHub Pages does (scripts/ops/serve_site.mjs, Node.js) at
http://127.0.0.1:<a free port><the build's folder>. launch() starts the browser that is there: Google Chrome
(GitHub's Ubuntu runners have it — nothing is downloaded), else Microsoft Edge (Windows), else Playwright's own
Chromium if it was installed; GV_BROWSER_CHANNEL (chrome, msedge, chromium) picks one. The browser never reaches
another site: every host name but 127.0.0.1 fails to resolve (the pages' pictures, videos and players from other
sites are simply not loaded — also not by the site's offline worker, whose requests Playwright's routes don't see).
Playwright itself (the Python package) is installed only where these run: scripts/ops/requirements-browser.txt.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

SERVER = Path(__file__).with_name("serve_site.mjs")
# Every host name but 127.0.0.1 resolves to nothing (Chromium's own switch: the browser, its pages and their
# workers alike).
NO_OUTSIDE = "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1"
CHANNELS = ("chrome", "msedge", "chromium")


class BrowserMissing(RuntimeError):
    """No browser could be started (none installed, or Playwright cannot drive it)."""


def _drain(stream) -> None:
    for _line in stream:
        pass


def site_prefix(site: Path | str, fallback: str | None = None) -> str:
    """The folder the build was made for (its PATH_PREFIX: "/aagrapevine/", or "/" for a custom domain), read off the
    home page's stylesheet link; else `fallback`, else PATH_PREFIX, else "/"."""
    try:
        html = (Path(site) / "index.html").read_text(encoding="utf-8", errors="replace")
    except OSError:
        html = ""
    m = re.search(r'<link rel="stylesheet" href="(/[^"]*?)assets/css/main\.css', html)
    if m:
        return m.group(1)
    p = (fallback or os.environ.get("PATH_PREFIX") or "/").strip()
    return "/" + p.strip("/") + "/" if p.strip("/") else "/"


class SiteServer:
    """`with SiteServer(site) as s:` — the built site at s.url ("http://127.0.0.1:PORT/aagrapevine/"); s.address(path)
    is a page's address. `overrides`: a JSON file the server reads for every request ({"files": {url path: file},
    "delay_ms": {url path: ms}} — serve_site.mjs), so a check can change what the site answers while it runs."""

    def __init__(self, site: Path | str, prefix: str | None = None, overrides: Path | str | None = None,
                 start_timeout: float = 30):
        self.site = Path(site).resolve()
        self.prefix = prefix or site_prefix(self.site)
        self.overrides = overrides
        self.start_timeout = start_timeout
        self.proc: subprocess.Popen | None = None
        self.url = ""

    def __enter__(self) -> "SiteServer":
        node = shutil.which("node")
        if not node:
            raise RuntimeError("Node.js is not installed (the site server is scripts/ops/serve_site.mjs)")
        if not (self.site / "index.html").is_file():
            raise RuntimeError(f"{self.site} is not a built website (no index.html)")
        cmd = [node, str(SERVER), str(self.site), "--port", "0", "--prefix", self.prefix]
        if self.overrides:
            cmd += ["--overrides", str(self.overrides)]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     encoding="utf-8", errors="replace")
        first: list[str] = []
        reader = threading.Thread(target=lambda: first.append(self.proc.stdout.readline()), daemon=True)
        reader.start()
        reader.join(self.start_timeout)
        m = re.search(r" at (http://127\.0\.0\.1:\d+/\S*)", first[0] if first else "")
        if not m:
            self.__exit__(None, None, None)
            raise RuntimeError(f"the site server did not start: {(first or [''])[0].strip() or 'no answer'}")
        self.url = m.group(1)
        # (nothing else is printed; the pipes are emptied anyway, so a chatty error can never block the server)
        for stream in (self.proc.stdout, self.proc.stderr):
            threading.Thread(target=_drain, args=(stream,), daemon=True).start()
        return self

    def __exit__(self, *_exc) -> None:
        if not self.proc:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(10)
        for stream in (self.proc.stdout, self.proc.stderr):
            try:
                stream.close()
            except Exception:  # (a reader thread may still hold it: closed with the process anyway)
                pass

    def address(self, path: str = "") -> str:
        """A page of the site: address("about/") → "http://127.0.0.1:PORT/aagrapevine/about/"."""
        return self.url + str(path).lstrip("/")


def launch(pw, channel: str | None = None, headless: bool = True, args: list[str] | None = None):
    """(browser, channel) — the first of `channel`, GV_BROWSER_CHANNEL, else chrome → msedge → Playwright's chromium
    that starts; BrowserMissing when none does."""
    want = channel or os.environ.get("GV_BROWSER_CHANNEL", "").strip()
    errors = []
    for ch in ([want] if want else CHANNELS):
        options = {"headless": headless, "args": [NO_OUTSIDE, *(args or [])]}
        if ch != "chromium":
            options["channel"] = ch
        try:
            return pw.chromium.launch(**options), ch
        except Exception as e:  # not installed, or Playwright cannot drive it
            errors.append(f"{ch}: {str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__}")
    raise BrowserMissing("no browser could be started — " + "; ".join(errors))
