"""The monthly posters' share pictures — what WhatsApp, Facebook, iMessage … show when someone shares a
/monthly/YYYY-MM/ page. Run by "Website update" (.github/workflows/update.yml, the build job) right after
"Build the website":

    python -m scripts.ops.poster_share _site

A build made with POSTER_SHARE=1 has every month page point its preview picture (og:image) at share.png beside it
(eleventy/filters/monthly.js mpShareImage); any other build keeps the committee's card there. This makes those
pictures: each month page (English and Spanish) opened in the browser that is there — the runner's Google Chrome,
headless, through Python Playwright (scripts/ops/site_browser.py; nothing is downloaded) —, its poster (1080 × 1350,
real HTML text in the site's own fonts) at its real size, and the top of it (1080 × 567: the masthead with the
month's name, then the start of the month's plan) saved as a 1200 × 630 PNG, the size the previews show.

Exit code 0 when every picture asked for was made (or no page asks for one), 1 when one could not be: then none is
left behind, and the workflow builds the site again without POSTER_SHARE, so no page ever points at a picture that
is not there. The site is published either way.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import struct
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from scripts.ops.site_browser import SiteServer, launch

WIDTH, HEIGHT = 1200, 630                    # the share picture (the size link previews show, 1.91 : 1)
POSTER_W = 1080                              # the poster's own width (areas/monthly.css: 1080 × 1350)
SCALE = WIDTH / POSTER_W                     # drawn at 10/9: sharp text, no resizing afterwards
CLIP_H = round(HEIGHT / SCALE)               # 567: the top of the poster that fills the picture
OG_IMAGE = re.compile(r'<meta property="og:image" content="([^"]*)"')
MONTH = re.compile(r"\d{4}-\d{2}")

# The poster, taken out of its scaled frame on the page into a box at the top left at its real size (its own
# styles and the page's icon sprite still apply); then the fonts and two frames, so everything is drawn.
ISOLATE = """async () => {
  const poster = document.querySelector("[data-mp-poster]");
  if (!poster) return "no poster on the page";
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;left:0;top:0;width:1080px;height:1350px;margin:0;padding:0;border:0;"
    + "overflow:hidden;z-index:2147483647;background:#fff";
  poster.style.position = "static";
  poster.style.transform = "none";
  box.appendChild(poster);
  document.body.appendChild(box);
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
  const r = poster.getBoundingClientRect();
  return Math.round(r.width) + " x " + Math.round(r.height);
}"""


def wanted(site: Path) -> list[tuple[str, Path]]:
    """The month pages whose preview picture is their own share.png: [(the page's path in the site, "monthly/2026-10/"
    or "es/monthly/2026-10/"; where its picture goes)]. (The redirect pages of past months point at none.)"""
    out = []
    for f in [*sorted(site.glob("monthly/*/index.html")), *sorted(site.glob("es/monthly/*/index.html"))]:
        if not MONTH.fullmatch(f.parent.name):
            continue
        rel = f.parent.relative_to(site).as_posix() + "/"
        m = OG_IMAGE.search(f.read_text(encoding="utf-8", errors="replace"))
        if m and urlsplit(html.unescape(m.group(1))).path.endswith("/" + rel + "share.png"):
            out.append((rel, f.parent / "share.png"))
    return out


def png_size(path: Path) -> tuple[int, int]:
    """(width, height) from a PNG's header; (0, 0) when it is not one."""
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return (0, 0)
    return struct.unpack(">II", head[16:24])


def shoot(browser, server: SiteServer, todo: list[tuple[str, Path]]) -> list[str]:
    """Takes the pictures with this browser from this server; → the problems (empty when every one was made)."""
    problems = []
    context = browser.new_context(viewport={"width": POSTER_W, "height": CLIP_H}, device_scale_factor=SCALE,
                                  reduced_motion="reduce", service_workers="block", locale="en-US",
                                  timezone_id="America/Chicago")
    try:
        page = context.new_page()
        for rel, out in todo:
            try:
                page.goto(server.address(rel), wait_until="load", timeout=45_000)
                got = page.evaluate(ISOLATE)
                if got != f"{POSTER_W} x 1350":
                    raise RuntimeError(f"the poster is {got}, not {POSTER_W} x 1350")
                page.screenshot(path=str(out), type="png", animations="disabled", scale="device",
                                clip={"x": 0, "y": 0, "width": POSTER_W, "height": CLIP_H})
                size = png_size(out)
                if size != (WIDTH, HEIGHT):
                    raise RuntimeError(f"the picture is {size[0]} x {size[1]}, not {WIDTH} x {HEIGHT}")
                print(f"  {rel}share.png — {WIDTH} x {HEIGHT}, {out.stat().st_size // 1024} KB")
            except Exception as e:  # one page: say which, go on with the others (none is kept in the end)
                problems.append(f"{rel}: {str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__}")
    finally:
        context.close()
    return problems


def make(site: Path, todo: list[tuple[str, Path]], channel: str | None = None) -> list[str]:
    """Serves the site, starts the browser and takes the pictures; → the problems (empty when every one was made)."""
    from playwright.sync_api import sync_playwright      # (only where it is installed: requirements-browser.txt)

    with SiteServer(site) as server, sync_playwright() as pw:
        browser, used = launch(pw, channel)
        print(f"Browser: {used} {browser.version}; site: {server.url}")
        try:
            return shoot(browser, server, todo)
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("site", nargs="?", default="_site", help="the built website (default: _site)")
    ap.add_argument("--channel", help="chrome, msedge or chromium (default: GV_BROWSER_CHANNEL, else the first that starts)")
    a = ap.parse_args(argv)
    site = Path(a.site).resolve()
    todo = wanted(site)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not todo:
        print("::notice title=Share pictures::No month page asks for a share picture (the build was not made with "
              "POSTER_SHARE=1) — nothing to do.")
        return 0
    started = time.monotonic()
    try:
        problems = make(site, todo, a.channel)
    except Exception as e:  # no Playwright, no browser, no server: none of them made
        problems = [f"{type(e).__name__}: {str(e).strip().splitlines()[0] if str(e).strip() else ''}"]
    if problems:
        for _rel, out in todo:      # none is kept: the site is built again without them
            out.unlink(missing_ok=True)
        for p in problems[:10]:
            print(f"::warning title=Share pictures not made::{p.replace('%', '%25')}")
        print(f"The posters' share pictures could not all be made ({len(problems)} problem(s)); the month pages keep "
              "the committee's card.")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(f"**Share pictures of the monthly posters:** not made ({problems[0].replace('|', '/')}) — "
                        "the month pages show the committee's card.\n")
        return 1
    secs = time.monotonic() - started
    print(f"Made {len(todo)} share pictures in {secs:.0f} s.")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"**Share pictures of the monthly posters:** {len(todo)} ({WIDTH} × {HEIGHT}).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
