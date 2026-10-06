"""The daily update: run every content-sync module, then assemble the site data.

    python -m scripts.sync.run_all                       # everything (the nightly full update)
    python -m scripts.sync.run_all --crawl-minutes 40    # crawl budget (or env GV_CRAWL_MINUTES)
    python -m scripts.sync.run_all --crawl-minutes 0     # everything except the PDF crawl (while config
                                                         #   sources.crawler.minutes_per_run is 0 — the search
                                                         #   paused — that counts as its try: only the
                                                         #   `attempted` time of data/raw/pdfs.json moves)
    python -m scripts.sync.run_all --quick               # the quick refresh (a push of a settings/content edit,
                                                         #   the daytime schedules, a quick run by hand):
                                                         #   drive, announcements, podcasts (cheap), the
                                                         #   writers archive files (local), the daily quote
                                                         #   (2 requests) + build_data; no crawl
    python -m scripts.sync.run_all --quick --also instagram,weekly_open
                                                         # … plus these sources (a push that changed what
                                                         #   they read: content/instagram.yml, a config section)
    python -m scripts.sync.run_all --morning             # the morning refresh the Morning check starts
                                                         #   (new day + daily quote by 5:30 AM Central):
                                                         #   --quick with the quote read second, plus the
                                                         #   monthly sources on the 1st and 15th
                                                         #   (MORNING_EXTRA, once that day)
    python -m scripts.sync.run_all --only youtube,podcasts
    python -m scripts.sync.run_all --skip crawl --no-translate

Order: drive, announcements, podcasts, youtube, instagram, articles, editorial, weekly_open,
shop (Book of the Month + subscription prices, ~15 requests), audio_project (the record-your-story
phone lines of Grapevine and La Viña, 3 requests), meetings (Grapevine meetings from
the intergroups' meeting lists, one request per list), events_external, writers_archive (the owner's
archive files in content/archive — no request), quote (Grapevine's and La
Viña's daily quote, one request per home page; as late as possible, so a full run GitHub starts on time
(07:17 UTC = 1:17 AM CST) is more likely to find the new one — except in the morning refresh, which reads it right after
the bulletin: see MORNING_EXTRA), crawl (last, time-boxed), then build_data (which translates).

Each module runs in this same process (so the polite crawl delay for aagrapevine.org /
aalavina.org is shared) and is isolated: if one fails — or is missing — it is logged and the
others still run; its previous data is kept. The exit code is 0 even when a module fails
(a soft failure, shown on /status/); it is non-zero ONLY if build_data fails (then the site
would not update, so the GitHub Action should go red).
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import os
import sys
import time
import traceback
from pathlib import Path

from .common import (RAW_DIR, get_logger, load_config, load_raw, now_iso, parse_iso, raw_path, read_json, run_module,
                     save_raw, write_json)

log = get_logger("run_all")

MODULES = ["drive", "announcements", "podcasts", "youtube", "instagram", "articles", "editorial",
           "weekly_open", "shop", "audio_project", "meetings", "events_external", "writers_archive", "quote", "crawl"]
RAW_NAME = {"crawl": "pdfs"}            # module → data/raw/<name>.json it writes (default: same name)

# --quick (the push refresh after a settings/content edit, the daytime schedules, a quick run by hand —
# and, with MORNING_EXTRA below, the morning refresh the Morning check starts; see
# .github/workflows/update.yml and morning.yml): only the sources that are cheap, then build_data. The
# nightly full update does the rest. "quote" is the one that touches aagrapevine.org / aalavina.org (5 s
# crawl delay): just the two home pages, so the day's quote is on the site early every morning.
# "writers_archive" reads only the files in content/archive (a few seconds, no request): a new file the
# owner pushes is on /published/ minutes later, and every run notices one. In MODULES order.
QUICK_MODULES = ("drive", "announcements", "podcasts", "writers_archive", "quote")
# Flags for the slow, optional parts of a module under --quick / --morning (also with --only … --quick).
# They are only passed if the module supports them.
QUICK_ARGS = {
    "youtube": ["--no-backfill"],
    "podcasts": ["--no-discover"],
    "articles": ["--no-details"],
    "instagram": ["--no-enrich"],
}
# --morning (Website update's MORNING mode, started by the Morning check so the new day and the daily
# quote are on the site by 5:30 AM Central): the --quick sources with their quick options — the daily
# quote, the reason for the run, read right after the bulletin — plus, on these days of the month
# (Central), the sources whose news is monthly: the Book of the Month (shop, ~15 requests) changes on the
# 15th, and the month on the 1st (shop again, and the new magazine issues: articles, hub pages only), so
# /shop/, /monthly/ and /digest/ open the day with it. They come after the quote, so a slow magazine
# server can never keep the quote out of the run's time box, and only in the day's first morning refresh
# that gets to them: one whose raw file was already read (or tried) that day skips them (the Morning check
# may start up to three refreshes a morning, for a late quote).
MORNING_EXTRA = {1: ("shop", "articles"), 15: ("shop",)}
# Time boxes of the morning refresh (on top of QUICK_ARGS); a flag a module does not support is dropped
# with its value by run_source (never left behind as a stray argument).
MORNING_ARGS = {"drive": ["--max-minutes", "5"], "articles": ["--no-archive"]}
# The sources only the FULL daily update reads — neither --quick nor --morning (not even as a monthly
# extra), and not the time-boxed PDF crawl, which a run may leave out (--crawl-minutes 0): the newest
# `attempted` among them is when the last full update ran. build_data writes it to status.json
# `full_update` and the build to /build.json `full`; the Morning check (.github/workflows/morning.yml,
# scripts/ops/morning_check.py) starts a full update when it is older than midnight on the 1st of the
# month, or older than 30 hours (GitHub skipped or failed the day's run).
FULL_ONLY = tuple(m for m in MODULES if m != "crawl" and m not in QUICK_MODULES
                  and not any(m in mods for mods in MORNING_EXTRA.values()))


def _supports(mod, flag: str) -> bool:
    try:
        return f'"{flag}"' in inspect.getsource(mod) or f"'{flag}'" in inspect.getsource(mod)
    except (OSError, TypeError):
        return False


def _attempted_on(name: str, day, tz) -> bool:
    """data/raw/<name>.json was read — or tried — on `day`, the site's calendar day (time zone `tz`)."""
    raw = load_raw(RAW_NAME.get(name, name))
    t = parse_iso(str(raw.get("attempted") or raw.get("updated") or ""))
    return t is not None and t.astimezone(tz).date() == day


def _raw_summary(name: str) -> dict:
    raw = load_raw(RAW_NAME.get(name, name))
    items = raw.get("items") or []
    stats = raw.get("stats") or {}
    new = stats.get("new")
    return {"ok": raw.get("ok"), "items": sum(1 for i in items if i.get("status", "ok") != "gone"),
            "new": new if isinstance(new, int) else None, "error": raw.get("error"),
            "exists": (RAW_DIR / f"{RAW_NAME.get(name, name)}.json").exists()}


def _mark_failed(name: str, note: str) -> None:
    """A module that cannot start (it does not import, or has no main()) never writes its data/raw file, so
    /status/ and the "A content source has stopped updating" issue would go on showing its LAST success:
    mark the file ok=false like a crash does (items, extras and the last success are kept)."""
    raw = RAW_NAME.get(name, name)
    try:
        prev = load_raw(raw)
        keep = {k: v for k, v in prev.items()
                if k not in ("source", "updated", "attempted", "ok", "error", "stats", "items")}
        save_raw(raw, prev.get("items", []), ok=False, error=note[:300], stats=prev.get("stats"), extra=keep)
    except Exception:  # noqa: BLE001 — never stops the run
        log.exception("%s: could not mark data/raw/%s.json as failed", name, raw)


def crawl_paused(cfg: dict | None = None) -> bool:
    """config/site.yml sources.crawler.minutes_per_run is 0: the PDF search is paused on purpose (read the same
    way as the plan step of .github/workflows/update.yml: not set → 40, "0.5" → 0)."""
    try:
        cfg = load_config() if cfg is None else cfg
        v = ((cfg.get("sources") or {}).get("crawler") or {}).get("minutes_per_run")
        return v not in (None, "") and int(float(v)) <= 0
    except Exception:  # noqa: BLE001 — an unreadable setting is the default (40), not a pause
        return False


def _note_paused_crawl() -> None:
    """A full update that leaves the crawl out because the PDF search is paused still counts as having tried it:
    data/raw/pdfs.json gets a fresh `attempted` (and nothing else — not `updated`, the last success /status/
    shows; items, stats and the crawl summary stay), so the run summary never reports the paused search as "not
    checked for N days" — neither during the pause nor on the first runs after it. A file that says ok=false
    keeps its last try, and a missing or unreadable one is left alone."""
    path = raw_path(RAW_NAME["crawl"])
    prev = read_json(path)                    # (never load_raw: it would move an unreadable file aside)
    if not isinstance(prev, dict) or prev.get("ok") is not True:
        return
    try:
        write_json(path, {**prev, "attempted": now_iso()})
    except Exception:  # noqa: BLE001 — never stops the run
        log.exception("could not note the paused PDF search in data/raw/%s.json", RAW_NAME["crawl"])


def run_source(name: str, argv: list[str]) -> dict:
    """Import scripts.sync.<name> lazily and run its main(argv) through run_module()."""
    t0 = time.monotonic()
    row = {"module": name, "status": "ok", "seconds": 0.0, "items": None, "new": None, "note": ""}
    try:
        mod = importlib.import_module(f"scripts.sync.{name}")
    except ModuleNotFoundError as e:
        row.update(status="missing" if e.name == f"scripts.sync.{name}" else "import error",
                   note=f"{type(e).__name__}: {e}"[:160])
        log.error("%s: %s — skipped", name, row["note"])
        _mark_failed(name, row["note"])
        return row
    except Exception as e:
        row.update(status="import error", note=f"{type(e).__name__}: {e}"[:160])
        log.error("%s could not be imported — skipped\n%s", name, traceback.format_exc())
        _mark_failed(name, row["note"])
        return row
    fn = getattr(mod, "main", None)
    if not callable(fn):
        row.update(status="missing", note="no main()")
        _mark_failed(name, "no main()")
        return row
    # A flag the module does not know is dropped — with its value, if it has one ("--max-minutes 5").
    args, dropped, i = [], [], 0
    argv = list(argv)
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and not _supports(mod, a):
            has_value = i + 1 < len(argv) and not argv[i + 1].startswith("--")
            dropped += argv[i:i + 2] if has_value else [a]
            i += 2 if has_value else 1
            continue
        args.append(a)
        i += 1
    if dropped:
        log.warning("%s does not support %s — ignored", name, dropped)

    def call() -> None:
        try:
            fn(args)
        except SystemExit as e:        # argparse error / explicit exit inside the module
            if e.code not in (0, None):
                raise RuntimeError(f"exited with code {e.code}") from None

    log.info("---- %s %s", name, " ".join(args))
    before = _raw_summary(name)
    run_module(RAW_NAME.get(name, name), call)     # never raises; marks the raw file ok=false on crash
    after = _raw_summary(name)
    row["seconds"] = round(time.monotonic() - t0, 1)
    row["items"] = after["items"]
    row["new"] = after["new"] if after["new"] is not None else max(0, after["items"] - before["items"])
    if not after["exists"]:
        row.update(status="failed", note="wrote no data")
    elif after["ok"] is False:
        row.update(status="failed", note=str(after["error"] or "")[:160])
    return row


def run_build(no_translate: bool, out: str | None = None, translate_minutes: float | None = None,
              keep_full_update: bool = False) -> dict:
    t0 = time.monotonic()
    row = {"module": "build_data", "status": "ok", "seconds": 0.0, "items": None, "new": None, "note": ""}
    try:
        from . import build_data
        args = (["--no-translate"] if no_translate else []) + (["--out", out] if out else [])
        if translate_minutes is not None:
            args += ["--translate-minutes", f"{translate_minutes:g}"]
        if keep_full_update:        # a quick / morning run: only a full update moves status.json full_update
            args += ["--keep-full-update"]
        rc = build_data.main(args)
        if rc not in (0, None):
            row.update(status="failed", note=f"exit code {rc}")
    except SystemExit as e:
        if e.code not in (0, None):
            row.update(status="failed", note=f"exit code {e.code}")
    except Exception as e:
        row.update(status="failed", note=f"{type(e).__name__}: {e}"[:200])
        log.error("build_data failed:\n%s", traceback.format_exc())
    row["seconds"] = round(time.monotonic() - t0, 1)
    try:
        st = json.loads(((Path(out) if out else RAW_DIR.parent / "site") / "status.json").read_text(encoding="utf-8"))
        tr = st.get("translations") or {}
        counts = st.get("counts") or {}
        row["items"] = sum(v for k, v in counts.items() if isinstance(v, int) and k != "whatsnew")
        row["note"] = row["note"] or (f"translated {tr.get('translated_this_run', 0)} new in {tr.get('seconds', 0)}s, "
                                      f"{tr.get('pending', 0)} pending, {tr.get('rejected_by_guard', 0)} kept original")
    except Exception:
        pass
    return row


def run_title(quick: bool, morning: bool) -> str:
    """The run table's heading (the Actions run summary): which kind of run this was."""
    return "Morning refresh" if morning else "Quick refresh" if quick else "Full update"


def print_table(rows: list[dict], total_seconds: float | None = None, title: str = "Full update") -> None:
    head = f"{'module':<16}{'status':<14}{'secs':>7}{'items':>8}{'new':>6}  note"
    lines = [head, "─" * len(head)]
    for r in rows:
        items = "" if r["items"] is None else str(r["items"])
        new = "" if r["new"] is None else str(r["new"])
        lines.append(f"{r['module']:<16}{r['status']:<14}{r['seconds']:>7.1f}{items:>8}{new:>6}  {r['note']}")
    failed = [r["module"] for r in rows if r["status"] not in ("ok", "skipped")]
    if total_seconds is not None:
        lines += ["─" * len(head), f"{'total':<16}{'':<14}{total_seconds:>7.1f}{'':>8}{'':>6}  "
                  + (f"problems: {', '.join(failed)}" if failed else "all ok")]
    print("\n" + "\n".join(lines) + "\n", flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:                        # nice table on the GitHub Actions run page
        try:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(f"### {title}\n\n| module | status | seconds | items | new | note |\n"
                        "|---|---|---:|---:|---:|---|\n")
                for r in rows:
                    icon = {"ok": "✅", "skipped": "⏭️"}.get(r["status"], "⚠️")
                    f.write(f"| {r['module']} | {icon} {r['status']} | {r['seconds']} | {r['items'] if r['items'] is not None else ''}"
                            f" | {r['new'] if r['new'] is not None else ''} | {str(r['note']).replace('|', '/')} |\n")
                if total_seconds is not None:
                    f.write(f"| **total** | | {round(total_seconds, 1)} | | | {', '.join(failed) or 'all ok'} |\n")
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.sync.run_all", description="Run the daily content update.")
    ap.add_argument("--only", help=f"comma-separated modules to run (of: {', '.join(MODULES)})")
    ap.add_argument("--skip", help="comma-separated modules to skip")
    ap.add_argument("--crawl-minutes", type=float, default=None, metavar="N",
                    help="time box for the PDF crawl in minutes; 0 = no crawl "
                         "(default: config sources.crawler.minutes_per_run / env GV_CRAWL_MINUTES)")
    ap.add_argument("--quick", action="store_true",
                    help=f"fast refresh: only {', '.join(QUICK_MODULES)} (cheap options) + build_data; "
                         "no crawl unless --crawl-minutes N (N > 0) is also given")
    ap.add_argument("--also", metavar="A,B",
                    help="with --quick only: also run these sources (in the usual order, with their quick options; "
                         "never crawl) — a push that changed what they read")
    ap.add_argument("--morning", action="store_true",
                    help="the morning refresh (the Morning check's): --quick, plus on the 1st and the 15th of "
                         "the month (Central) the monthly sources — " + "; ".join(
                             f"day {d}: {', '.join(m)}" for d, m in sorted(MORNING_EXTRA.items())))
    ap.add_argument("--no-translate", action="store_true", help="build without running the translation model")
    ap.add_argument("--translate-minutes", type=float, default=None, metavar="N",
                    help="time box for new translations in build_data (default 40 / env GV_TRANSLATE_MINUTES)")
    ap.add_argument("--no-build", action="store_true", help="only run the sync modules")
    ap.add_argument("--out", help="write the site data here instead of data/site (testing)")
    a = ap.parse_args(argv)

    only = [m.strip() for m in (a.only or "").split(",") if m.strip()]
    skip = {m.strip() for m in (a.skip or "").split(",") if m.strip()}
    unknown = [m for m in list(only) + list(skip) if m not in MODULES and m != "build_data"]
    if unknown:
        log.warning("unknown module name(s) ignored: %s", unknown)
    # --also (a quick run of a push that changed what a full-only source reads — the plan step of
    # .github/workflows/update.yml works the list out): known sources only, never the crawl
    also_asked = [m.strip() for m in (a.also or "").split(",") if m.strip()]
    also: set[str] = set()
    if also_asked and not a.quick:
        log.warning("--also %s is only used with --quick — ignored", ",".join(also_asked))
    elif also_asked:
        bad = [m for m in also_asked if m not in MODULES or m == "crawl"]
        if bad:
            log.warning("--also: %s ignored (not a source, or the crawl)", bad)
        also = {m for m in also_asked if m not in bad}
    crawl_minutes = a.crawl_minutes
    if crawl_minutes is None and os.environ.get("GV_CRAWL_MINUTES"):
        try:
            crawl_minutes = float(os.environ["GV_CRAWL_MINUTES"])
        except ValueError:
            log.warning("GV_CRAWL_MINUTES=%r is not a number — ignored", os.environ["GV_CRAWL_MINUTES"])
    if crawl_minutes is not None and crawl_minutes < 0:
        log.warning("--crawl-minutes %g is negative — treated as 0 (no crawl)", crawl_minutes)
        crawl_minutes = 0.0

    def skipped(name: str, why: str) -> dict:
        return {"module": name, "status": "skipped", "seconds": 0.0, "items": None, "new": None, "note": why}

    # --quick and --morning are the two lean modes; --morning reads the daily quote right after the
    # bulletin and adds the monthly sources of the day (MORNING_EXTRA, by the Central calendar day —
    # quote.local_today, the day the site shows) that no run has read yet that day.
    lean = a.quick or a.morning
    flag = "--morning" if a.morning else "--quick"
    order = list(MODULES)
    extra: tuple[str, ...] = ()
    read_today: tuple[str, ...] = ()
    if a.morning:
        from .quote import local_today, local_tz
        today = local_today()
        order.remove("quote")
        order.insert(order.index("announcements") + 1, "quote")
        due = MORNING_EXTRA.get(today.day, ())
        read_today = tuple(m for m in due if _attempted_on(m, today, local_tz()))
        extra = tuple(m for m in due if m not in read_today)
        if due:
            log.info("--morning on day %d of the month: also %s%s", today.day, ", ".join(extra) or "nothing more",
                     f" ({', '.join(read_today)} read today already)" if read_today else "")

    t0 = time.monotonic()
    rows = []
    for name in order:
        if (only and name not in only) or name in skip:
            continue
        args: list[str] = []
        if name == "crawl":
            if crawl_minutes is not None and crawl_minutes <= 0:
                # the nightly full update while config sources.crawler.minutes_per_run is 0 (not a 0-minute run
                # started by hand while the search is on): the search is paused, and that counts as its try
                paused = not lean and crawl_paused()
                if paused:
                    _note_paused_crawl()
                rows.append(skipped(name, "paused (sources.crawler.minutes_per_run: 0)" if paused
                                    else "--crawl-minutes 0"))
                continue
            if lean and a.crawl_minutes is None:             # (an env default never forces a crawl)
                rows.append(skipped(name, flag))
                continue
            if crawl_minutes is not None:
                args += ["--minutes", f"{crawl_minutes:g}"]
        elif lean and not only and name not in QUICK_MODULES and name not in extra and name not in also:
            rows.append(skipped(name, f"{flag} (read today already)" if name in read_today else flag))
            continue
        if lean:
            args += QUICK_ARGS.get(name, [])
        if a.morning:
            args += MORNING_ARGS.get(name, [])
        rows.append(run_source(name, args))

    build_ok = True
    if not a.no_build and "build_data" not in skip:      # --only X still rebuilds the site data
        row = run_build(a.no_translate, a.out, a.translate_minutes, keep_full_update=lean)
        rows.append(row)
        build_ok = row["status"] == "ok"
    print_table(rows, time.monotonic() - t0, run_title(a.quick, a.morning))
    log.info("total %.1f min", (time.monotonic() - t0) / 60)
    return 0 if build_ok else 1


if __name__ == "__main__":
    sys.exit(main())
