"""Website update's run summary (.github/workflows/update.yml, job "Sync content + translate", step "Write run
summary"): data/site/status.json → the tables and notes of the run's summary ($GITHUB_STEP_SUMMARY), the yellow
::warning / ::notice lines of the run's page, and the job output `health` ($GITHUB_OUTPUT, one line of JSON) that
the "report" job opens its issues from (scripts/ops/report_issues.py).

    python -m scripts.ops.run_summary       # from the repository's root, after the sync (status.json written)

Moved out of the workflow in November 2026, line for line (main() is the step's former script). Its env: ALSO,
ALSO_WHY, DAILY_MINUTES, STARTED (the plan step's outputs). Never fails the step: a missing or sample status.json
ends it with a note. Tested through the step by tests/test_morning.py (QuoteDays, the summary's lines),
tests/test_events_feeds.py (RunSummary), tests/test_sync_health.py, tests/test_booth_sync.py,
tests/test_price_changes.py, tests/test_youtube.py (BotCheckDays) and tests/test_ops_scripts.py.
"""
from __future__ import annotations


def main() -> None:
    """The step's script: reads data/site/status.json in the current folder; writes $GITHUB_STEP_SUMMARY and $GITHUB_OUTPUT."""
    import json, os
    from datetime import datetime, timezone
    from urllib.parse import urlsplit
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    try:
        with open("data/site/status.json", encoding="utf-8") as f:
            s = json.load(f)
    except Exception as e:
        print(f"No status.json yet ({e})")
        raise SystemExit(0)
    if s.get("fixture"):
        print("status.json is still sample (fixture) data: the site data was not rebuilt this run.")
        raise SystemExit(0)

    STALE_DAYS = 7          # README → "Only worry if the same source fails for more than a week"
    # A source that still works but that no run has even TRIED for this many days is "not checked": every
    # source is tried at least once a day (the nightly full update), so the update stops before it, or no
    # longer runs it. A warning from then on; in the report issue from STALE_DAYS.
    UNCHECKED_DAYS = 3
    # Never "not checked" while left alone on purpose: the PDF search while sources.crawler.minutes_per_run
    # is 0 (run_all skips the crawl; DAILY_MINUTES is that setting, from the plan step). Every other source
    # writes its data/raw file — so its `attempted` time — whenever it runs, also with nothing set up for
    # it (drive, youtube and podcasts then fail with an error of their own; meetings.enabled: false is a
    # normal, empty run); one that never ran yet has no `attempted` and is not counted either.
    paused = {"pdfs"} if os.environ.get("DAILY_MINUTES", "").strip() == "0" else set()
    now = datetime.now(timezone.utc)

    def days_since(iso):
        try:
            return (now - datetime.fromisoformat(str(iso).replace("Z", "+00:00"))).days
        except (TypeError, ValueError):
            return None

    def moment(iso):
        try:
            t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        except ValueError:
            return None
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)

    started = moment(os.environ.get("STARTED"))      # when this run started to sync (the plan step)

    lines = ["## Content sources", "",
             "| Source | Status | Items | New in 7 days | Last success (UTC) | Problem |",
             "|---|---|---:|---:|---|---|"]
    stale = []
    for src in s.get("sources", []):
        ok = bool(src.get("ok"))
        label = src.get("label") or src.get("source")
        err = (src.get("error") or "").replace("|", "/").replace("\n", " ")[:160]
        unchecked = (days_since(src.get("attempted"))
                     if src.get("ok") is True and src.get("source") not in paused else None)
        if unchecked is not None and unchecked < UNCHECKED_DAYS:
            unchecked = None
        state = "**PROBLEM**" if not ok else "**NOT CHECKED**" if unchecked is not None else "OK"
        problem = err or (f"not checked for {unchecked} days" if unchecked is not None else "")
        lines.append(f"| {label} | {state} | "
                     f"{src.get('count', '')} | {src.get('new_7d', '')} | {(src.get('updated') or '—')[:16].replace('T', ' ')} | {problem} |")
        if unchecked is not None:
            print(f"::warning title={label}::not checked for {unchecked} days — no run has got to it since "
                  f"{str(src.get('attempted'))[:10]} (the update stops before it, or no longer runs it); its "
                  "items stay on the site")
            if unchecked >= STALE_DAYS:
                stale.append({"source": src.get("source"), "label": label, "days": days_since(src.get("updated")),
                              "updated": src.get("updated"), "error": f"not checked for {unchecked} days",
                              "unchecked": unchecked})
        if not ok:
            # Shows as a yellow warning on the run page (the site still deploys).
            days = days_since(src.get("updated"))
            since = (f" — no successful update for {days} days" if days and days >= 1
                     else " — has not worked yet" if src.get("ok") is False and not src.get("updated") else "")
            print(f"::warning title={label}::{err or 'failed'} (previous items kept){since}")
            # ok is None = never ran (e.g. only quick runs so far): nothing to report yet.
            if src.get("ok") is False and (days is None or days >= STALE_DAYS):
                stale.append({"source": src.get("source"), "label": label, "days": days,
                              "updated": src.get("updated"), "error": err})
        # A podcast show whose feed fails while the other shows still update (scripts/sync/podcasts.py: the
        # source stays ok, the show is in stats.shows with ok false, `updated` = its last good read and
        # `failing_since`): named under "Notes" below, and a source that stopped once it has failed for
        # STALE_DAYS — "Podcasts — <show>" in the report issue. Every show failing fails the source itself (its
        # warning above says so); a show that was already down for a week still counts then — one bad run of
        # the whole source (all the feeds are on one host) must not close that issue for a day — unless the
        # source itself is in the list (it then says it all).
        shows = (src.get("stats") or {}).get("shows") if isinstance(src.get("stats"), dict) else None
        source_stale = any(x.get("source") == src.get("source") for x in stale)
        if src.get("source") == "podcasts" and isinstance(shows, dict) and not source_stale:
            for key, sh in shows.items():
                if not isinstance(sh, dict) or sh.get("ok") is not False:
                    continue
                days = days_since(sh.get("updated")) if sh.get("updated") else days_since(sh.get("failing_since"))
                name = str(sh.get("name") or key)
                title = f"{label} — {name}".replace("%", "%25").replace(",", "%2C").replace(":", "%3A")
                if ok:
                    print(f"::warning title={title}::" + (f"{str(sh.get('error') or 'failed')[:160]} (its episodes are kept; "
                          "the other shows still update)" + (f" — not read for {days} days" if days else "")).replace("%", "%25"))
                if days is not None and days >= STALE_DAYS:
                    stale.append({"source": f"podcasts:{key}", "label": f"{label} — {sh.get('name') or key}",
                                  "days": days_since(sh.get("updated")) if sh.get("updated") else None,
                                  "updated": sh.get("updated"), "error": str(sh.get("error") or "")[:160]})
    # Sync health — so a source that suddenly loses items, or a magazine page the document search depends on,
    # shows the day it happens. Per source, what THIS run added and removed (common.save_raw `changes`, which
    # build_data copies into status.json sources[]) — only for a source this run read (its `attempted` is not
    # older than STARTED: a source it did not read still shows its last run's counts) — and the items the
    # mass-drop guard holds back (`held`: a source that suddenly lists far fewer items keeps the missing ones
    # until the next run finds the same; "drop" false = the source kept them itself, e.g. a Drive folder that
    # looked empty), shown while the hold lasts, whichever run made it. Then the document search's hub / kit
    # pages that did not load in this run (data/raw/pdfs.json `hub_problems` — only from a search this run
    # made that ended normally: a crashed one keeps the last run's list). Only rows with something to say.
    def plain(v):
        return " ".join(str(v if v is not None else "").split()).replace("|", "/")

    def utc(iso):
        t = moment(iso) if iso else None
        return f"{t:%Y-%m-%d %H:%M} UTC" if t else "?"

    def whole(v):
        return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0

    def prop(v):    # an annotation's title: a comma or a colon in a source's name would cut it
        return str(v).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A").replace(",", "%2C").replace(":", "%3A")

    health = []
    for src in s.get("sources", []):
        label = plain(src.get("label") or src.get("source"))
        ch = src.get("changes") if isinstance(src.get("changes"), dict) else {}
        hd = src.get("held") if isinstance(src.get("held"), dict) else None
        at = moment(src.get("attempted")) if src.get("attempted") else None
        ran = bool(started and at and at >= started)
        added, removed = (whole(ch.get("added")), whole(ch.get("removed"))) if ran else (0, 0)
        what = []
        if hd and whole(hd.get("kept")):
            ex = [plain(x)[:60] for x in (hd.get("examples") or []) if plain(x)][:3]
            seen = f"found {plain(hd.get('found'))} of {plain(hd.get('previous'))}"
            if hd.get("drop"):
                what.append(f"**{hd['kept']} held back** since {utc(hd.get('since'))} ({seen}): they stay on "
                            "the site until the next run finds the same")
            else:
                what.append(f"**{hd['kept']} kept** since {utc(hd.get('since'))} ({seen}): removed only when "
                            "the next run confirms they are gone")
            if ex:
                what[-1] += " — e.g. " + "; ".join(f"“{x}”" for x in ex)
            print(f"::warning title={prop(label + ': items held back')}::{hd['kept']} of "
                  f"{plain(hd.get('previous'))} item(s) kept on the site although "
                  f"{'this run' if ran else 'its last run'} did not find them (since {utc(hd.get('since'))}) — see "
                  "the run summary")
        if ran and ch.get("confirmed"):
            what.append(f"removal confirmed (held back since {utc(ch.get('confirmed'))})")
        if added or removed or what:
            health.append(f"| {label} | {added if ran else '—'} | {removed if ran else '—'} | {' · '.join(what)} |")
    try:
        with open("data/raw/pdfs.json", encoding="utf-8") as f:
            penv = json.load(f)
    except Exception:
        penv = {}
    penv = penv if isinstance(penv, dict) else {}
    pat = moment(penv.get("attempted")) if penv.get("attempted") else None
    hub_lines = []
    if started and pat and pat >= started and penv.get("ok") is True:
        for h in penv.get("hub_problems") or []:
            if isinstance(h, dict) and h.get("url"):
                u = urlsplit(str(h["url"]))
                where = (u.hostname or "").removeprefix("www.") + (u.path or "/")
                hub_lines.append(f"- {plain(where)} — {plain(h.get('status')) or 'error'} since {utc(h.get('since'))}")
    if health:
        lines += ["", "**Sync health** (what each source added and removed in this run — \"—\" when this run did "
                      "not read it — and items held back after a sudden drop):", "",
                  "| Source | Added | Removed | Held back |", "|---|---:|---:|---|", *health]
    if hub_lines:
        lines += ["", f"**Main pages of the magazine sites that did not load** (this run's document search; the "
                      "documents they list stay on the site, and each page is tried again every day):",
                  *hub_lines[:15]]
        if len(hub_lines) > 15:
            lines.append(f"- … and {len(hub_lines) - 15} more")
        print(f"::warning title=Document search::{len(hub_lines)} main page(s) of the magazine sites did not load "
              "— see the run summary (checked again every day)")
    # A push that changed what a source only the full update reads (content/instagram.yml, data/geo, its
    # part of config/site.yml) ran that source too — the plan step (scripts/ops/push_modules.py) says why.
    also = [m.strip() for m in os.environ.get("ALSO", "").split(",") if m.strip()]
    if also:
        lines += ["", "**Also run for this push** (sources the nightly update reads, whose input this push "
                      "changed): " + (os.environ.get("ALSO_WHY") or ", ".join(also)).replace("|", "/")]
    # The day of each magazine's daily quote on the site after this run (data/site/quote.json) —
    # the Morning check's summary says when it went live.
    try:
        with open("data/site/quote.json", encoding="utf-8") as f:
            qitems = [q for q in (json.load(f).get("items") or []) if isinstance(q, dict)]
    except Exception:
        qitems = []
    mags, qbits = {"gv": "Grapevine", "lv": "La Viña"}, []
    for q in qitems:
        try:
            qd = datetime.strptime(str(q.get("date") or "")[:10], "%Y-%m-%d")
        except ValueError:
            continue
        qbits.append(f"{mags.get(q.get('pub'), q.get('pub'))} {qd:%b} {qd.day}")
    if qbits:
        lines += ["", "**Daily quote:** " + " · ".join(qbits)]
    c = s.get("crawl") or {}
    if c:
        line = (f"**PDF crawl:** {c.get('known_pages', 0)} pages known · {c.get('crawled_pages', 0)} crawled · "
                f"{c.get('pdfs', 0)} PDFs · {c.get('last_run_pages') or 0} pages this run")
        if c.get("est_days_to_full"):
            line += f" · about {c['est_days_to_full']} more day(s) to reach every page"
        lines += ["", line]
    t = s.get("translations") or {}
    if t:
        lines += ["", f"**Translations:** {t.get('cached', 0)} cached · {t.get('translated_this_run', 0)} new this run"
                      f" · {t.get('pending', 0)} waiting for the next run"]
        if t.get("model_enabled", True) and t.get("pending") and not t.get("translated_this_run"):
            print(f"::warning title=Translation is not working::{t['pending']} texts are waiting but none could be translated "
                  "this run. The translation models are probably missing (see 'Check the translation models are "
                  "complete' and the 'Sync sources and translate' log). New titles stay in their original language until then.")
    # The Texas writers archive (/published/#archive): the owner's CSV files in content/archive, read in every
    # run (scripts/sync/writers_archive.py). status.json `writers_archive` = the file of each magazine in use
    # and what is on the site; the source's stats: `notes` = a new file taken in, `warnings` = older copies
    # left in the folder, a file whose name and content are different magazines. A file that cannot be used
    # (columns missing, cut off) makes the source fail: its magazine keeps the rows it had, while the other
    # magazine's new file is still taken in. So a new file is announced whatever `ok` says — but only when
    # THIS run took it in (its imported_at is not older than STARTED): a crash of the source keeps the last
    # run's stats, and a run stopped before the site data were rebuilt leaves the last run's status.json.
    wa = s.get("writers_archive") if isinstance(s.get("writers_archive"), dict) else {}
    wsrc = next((x for x in s.get("sources", []) if x.get("source") == "writers_archive"), None) or {}
    wst = wsrc.get("stats") if isinstance(wsrc.get("stats"), dict) else {}
    if wa or wsrc:
        def num(v):
            return f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else "?"
        head = "**Writers archive** (content/archive → /published/#archive)"
        if isinstance(wa.get("items"), int):
            head += (f": {num(wa['items'])} stories by Texas writers on the site, {num(wa.get('neta65'))} of them "
                     "by Area 65 writers")
        alines = [head]
        wfiles = wa.get("files") if isinstance(wa.get("files"), dict) else {}
        for pub in ("gv", "lv"):
            f = wfiles.get(pub)
            if isinstance(f, dict) and f.get("name"):
                alines.append(f"- {mags.get(pub, pub)}: {f['name']} — {num(f.get('rows'))} rows, "
                              f"{num(f.get('texas_rows'))} by Texas writers")
        def texts(key, most):
            v = wst.get(key)
            return [" ".join(str(x).split()) for x in (v if isinstance(v, list) else []) if str(x).strip()][:most]
        taken = [moment(f.get("imported_at")) for f in wfiles.values() if isinstance(f, dict)]
        if wst.get("changed") is True and started and any(t is not None and t >= started for t in taken):
            for note in texts("notes", 5):
                alines.append(f"- {note}")
                print(f"::notice title=Writers archive::{note.replace('%', '%25')}")
        if wsrc.get("ok") is False:
            werr = " ".join(str(wsrc.get("error") or "").split()) or "the newest file could not be used"
            alines.append(f"- **CSV file to fix** (the older rows stay on the site): {werr}")
        alines += [f"- {w}" for w in texts("warnings", 10)]
        lines += ["", *[a.replace("|", "/") for a in alines]]
    # Smaller problems of a source that still updated (e.g. one of several feeds did not answer).
    # Nothing to do unless the same note shows up here day after day. (The writers archive's are in its
    # own lines above; the bulletin's and the events' files come under "… files to fix" below, and the
    # document search's main pages under "Sync health" above, when this run asked for them.)
    notes = []
    for src in s.get("sources", []):
        warns = (src.get("stats") or {}).get("warnings") if isinstance(src.get("stats"), dict) else None
        if src.get("source") in ("writers_archive", "announcements", "manual_events"):
            continue
        if src.get("source") == "pdfs" and hub_lines and isinstance(warns, list):
            warns = [w for w in warns if "did not load" not in str(w)]
        if src.get("ok") and isinstance(warns, list) and warns:
            label = src.get("label") or src.get("source")
            notes += [f"- {label}: " + str(w).replace("\n", " ")[:200] for w in warns[:2]]
            # YouTube's bot check ("confirm you're not a bot") on a day the feeds still worked: a yellow warning
            # on the run's page, never a failure — the source stays ok, its videos keep their last known
            # details, and no issue opens (youtube.py bot_check_note; tests/test_youtube.py BotCheckDays).
            for w in warns:
                if src.get("source") == "youtube" and "YouTube answered with" in str(w):
                    print(f"::warning title={label}::" + str(w).replace("\n", " ")[:200].replace("%", "%25"))
    if notes:
        lines += ["", "**Notes** (these sources still updated; only look into a note that repeats for a week):", *notes]
    # Optional outside calendars (config/site.yml sources.ics_feeds) — INFORMATIONAL only: they are
    # kept apart from the content sources above, so a feed that a site's bot protection blocks
    # (neta65.org's Cloudflare check) is a notice here, never a warning, and never opens the
    # "A content source has stopped updating" issue. Its `notes` (the feed gives another date or
    # time, or a venue a content/events file still calls "to be announced") are notices too.
    # A feed config/site.yml marks `paused:` (known not to work: "paused", with the reason) is said so, with no
    # notice at all; one that works again while still marked says to delete the line.
    feeds = [f for f in (s.get("feeds") or []) if isinstance(f, dict)]
    if feeds:
        words = {"ok": "working", "blocked": "blocked by the site's bot protection",
                 "error": "not answering", "never": "not checked yet", "paused": "paused on purpose"}
        lines += ["", "**Other calendars (optional, informational):**"]
        for f in feeds:
            state = str(f.get("state") or "never")
            bits = [words.get(state, state) + (f" ({f['paused']}; asked once a week)"
                                               if state == "paused" and f.get("paused") else "")]
            if state == "ok" and f.get("paused") and f.get("checked_this_run"):
                print(f"::notice title=Calendar feed works again ({f.get('label') or f.get('url')})::It is still "
                      "marked paused in config/site.yml (sources.ics_feeds): delete its paused: line.")
            if f.get("http_status"):
                bits.append(f"HTTP {f['http_status']}")
            bits.append(f"{f.get('events_count') or 0} event(s)"
                        + (f", {f['duplicates']} already on the Events page (shown once)" if f.get("duplicates") else ""))
            if state != "ok" and f.get("last_success"):
                bits.append(f"last read {str(f['last_success'])[:10]} (that copy is still used)")
            if not f.get("checked_this_run"):
                bits.append("not asked this run (at most once a day)")
            lines.append(f"- {f.get('label') or f.get('url')}: " + " · ".join(bits))
            fnotes = [" ".join(str(n).split()) for n in (f.get("notes") or [])][:10]
            lines += [f"  - Check: {n.replace('|', '/')}" for n in fnotes]
            for n in fnotes:
                print(f"::notice title=Check a content/events file ({f.get('label') or f.get('url')})::{n.replace('%', '%25')}")
            if state == "blocked" and f.get("checked_this_run"):
                print(f"::notice title=Calendar feed blocked ({f.get('label') or f.get('url')})::"
                      "The site's bot protection turned the robot away, so this calendar can't be read. Until "
                      "it can, a workshop or assembly shows on the Events page only after someone on the "
                      "committee adds it by hand to content/events (see content/events/README.md). To fix it, "
                      "the site's webmaster can let calendar requests through (see the comment above "
                      "ics_feeds in config/site.yml).")
    # Settings build_data could not use (config/site.yml `meeting:` / `recurring_events:` /
    # `sources.ics_feeds:` / `price_changes:`, a slip in a content/events file such as a
    # location_es left saying "Lugar por anunciarse", a YAML typo in data/translations/glossary.yml
    # or overrides.yml): that part was skipped or corrected, the rest of the site still updated.
    probs = s.get("problems") if isinstance(s.get("problems"), dict) else {}
    # What kept translation from working fully, which is no settings file to fix (translate.Translator.problems →
    # status.json translations.problems): a translation model that could not be installed — its download
    # failed (the next run tries again by itself) or the package's checksum is not the pinned one
    # (MODEL_SHA256 in scripts/sync/translate.py: a person checks the new package first) — or an unreadable
    # data/translations/cache.json (moved aside; the line says how to restore it). Under a heading of their
    # own; build_data also adds them after the glossary / overrides typos in problems.translations, so they
    # are cut from that Settings problem below.
    tr = s.get("translations") if isinstance(s.get("translations"), dict) else {}
    tprobs = [" ".join(str(p).split()) for p in (tr.get("problems") if isinstance(tr.get("problems"), list) else [])
              if str(p).strip()]

    def setting_text(k, v):
        text = " ".join(str(v).split())
        if k == "translations" and tprobs:
            cut = text.find(tprobs[0][:40])
            if cut >= 0:
                text = text[:cut].rstrip(" /")
        return text.replace("|", "/")[:1000]
    settings = [(k, msg) for k, v in probs.items()
                if k in ("meeting", "recurring_events", "ics_feeds", "price_changes", "content_events", "translations")
                for msg in [setting_text(k, v)] if msg]
    if settings:
        lines += ["", "**Settings problems** (the rest of the site still updated — fix the file and save it again):",
                  *[f"- {msg}" for _k, msg in settings]]
        for k, msg in settings:
            print(f"::warning title=Settings problem ({k})::{msg.replace('%', '%25')}")
    if tprobs:
        tlines = [p.replace("|", "/")[:600] for p in tprobs[:6]]
        lines += ["", "**Translation problems** (the rest of the site still updated; new titles may stay in their "
                      "original language meanwhile — a model download that failed is simply tried again by the next "
                      "run, a checksum that does not match needs a person to check the new package first):",
                  *[f"- {p}" for p in tlines]]
        for p in tlines:
            print(f"::warning title=Translation problem::{p.replace('%', '%25')}")
    # Bulletin posts and events written by hand (content/bulletin, content/events) that could not be
    # read — or that link a picture or document not saved next to them (announcements.py
    # stats.errors): the rest of the site still updated; the chair fixes the file.
    for key, title in (("announcements", "Bulletin files to fix"), ("manual_events", "Event files to fix")):
        src = next((x for x in s.get("sources", []) if x.get("source") == key), None) or {}
        st = src.get("stats") if isinstance(src.get("stats"), dict) else {}
        errs = [" ".join(str(e).split()).replace("|", "/") for e in (st.get("errors") or []) if str(e).strip()][:10]
        if errs:
            lines += ["", f"**{title}** (the rest of the site still updated — fix the file and save it again):",
                      *[f"- {e}" for e in errs]]
            for e in errs:
                print(f"::warning title={title}::{e.replace('%', '%25')}")
    # Files in the committee's Drive booth folder that the booth display (About page → "Booth display") can
    # never show — data/site/booth.json `problems` (build_data.build_booth): a type it can't show, a video or
    # sound type browsers don't play, a note with no text, (from …) after (until …) — each with what to do.
    # The rest of the booth and of the site still updated; rename, convert or replace the file in Drive
    # (content/booth/README.md has the naming rules). Drive's own note above only counts them.
    try:
        with open("data/site/booth.json", encoding="utf-8") as f:
            bprobs = [p for p in (json.load(f).get("problems") or []) if isinstance(p, dict) and p.get("problem")]
    except Exception:
        bprobs = []
    if bprobs:
        blines = [" ".join(f"{p.get('file') or 'booth'} — {p['problem']}".split()).replace("|", "/") for p in bprobs]
        lines += ["", f"**Booth folder files the booth display can't show** ({len(bprobs)}; the rest of the booth "
                      "still updated — fix the file in the Drive booth folder):", *[f"- {b}" for b in blines[:30]]]
        if len(blines) > 30:
            lines.append(f"- … and {len(blines) - 30} more (the player's Settings → Slides lists them all)")
        for b in blines[:10]:
            print(f"::warning title=Booth folder file to fix::{b.replace('%', '%25')}")
    # Bulletin posts scheduled for a later day (content/bulletin `publish:`, Drive "(from …)"):
    # build_data leaves them off the site until their day (status.json `scheduled`, soonest first).
    sched = [x for x in (s.get("scheduled") or []) if isinstance(x, dict) and x.get("publish")]
    if sched:
        def where(x):
            f = str(x.get("file") or "")
            return f"({f})" if f.startswith("content/") else f"(Google Drive: {f})" if f else ""
        lines += ["", "**Scheduled bulletin posts** (not on the site yet):",
                  *[" ".join(b for b in (f"- {x['publish']} —", str(x.get("title") or "(no title)"), where(x)) if b)
                    .replace("|", "/") for x in sched]]
        print(f"::notice title=Scheduled bulletin posts::{len(sched)} post(s) will appear by themselves on their day"
              f" — the first on {sched[0]['publish']} (see the run summary).")
    # Weekly podcast discovery (scripts/sync/podcasts.py): feeds found on the magazine sites that
    # are not in config/site.yml yet. They are never added automatically.
    pod = next((x for x in s.get("sources", []) if x.get("source") == "podcasts"), None) or {}
    pstats = pod.get("stats") if isinstance(pod.get("stats"), dict) else {}
    feeds = [f for f in (pstats.get("discovered_feeds") or []) if isinstance(f, dict) and f.get("feed")]
    if feeds:
        lines += ["", "**New podcast feeds found** (not on the website yet; to show one, add it under "
                      "`sources.podcasts` in `config/site.yml`):"]
        for f in feeds[:6]:
            bits = [str(f.get("title") or "(no title)"),
                    f"{f['episodes']} episodes" if f.get("episodes") else "",
                    "Spanish" if f.get("spanish") else "",
                    f"latest {str(f['latest'])[:10]}" if f.get("latest") else ""]
            lines.append("- " + " · ".join(b for b in bits if b) + f" — {f['feed']}")
        print(f"::notice title=New podcast feed found::{len(feeds)} podcast feed(s) on the magazine sites "
              "are not on the website yet. See the run summary.")
    # Dated facts the committee keeps by hand that run out soon — the monthly tips, the panels, next year's
    # skip dates, the next NETA 65 assemblies, an old price-change notice (build_data: status.json
    # `reminders`, each with the file to edit). Nothing when none is due.
    rem = [r for r in (s.get("reminders") or []) if isinstance(r, dict) and str(r.get("message") or "").strip()]
    if rem:
        def remind(r):
            msg, file, due = (" ".join(str(r.get(k) or "").split()) for k in ("message", "file", "due"))
            return ("- " + msg + (f" ({file})" if file and file not in msg else "")
                    + (f" — due {due}" if due and due not in msg else "")).replace("|", "/")
        lines += ["", "**Reminders** (dates in the settings that need a look soon — the site still works):",
                  *[remind(r) for r in rem]]
        print(f"::notice title=Reminders::{len(rem)} dated fact(s) the committee keeps by hand need a look soon "
              "(see the run summary).")
    if stale:
        lines += ["", f"**Not updating for {STALE_DAYS}+ days:** " + ", ".join(x["label"] for x in stale)
                  + " — reported in the issue *\"A content source has stopped updating\"*."]
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))

    # For the "Report sources that stopped updating" job below (one line of JSON). Its "site" is config/site.yml's
    # site.url, only the report's stand-in: this job cannot ask GitHub Pages for the live address, so the report
    # links the address build-deploy works out (its `site` output) and uses this one only when that is empty.
    # `quote_days` (status.json: when each morning's quotes came in, against the goal), `tz` (site.timezone) and
    # `alarm` (site.morning_alarm: is the outside morning alarm set up?) are for the issue about missed mornings
    # (scripts/ops/report_issues.py mornings) — it opens only while the alarm is set up.
    try:
        from scripts.sync.common import load_config
        site_cfg = load_config().get("site") or {}
        site = str(site_cfg.get("url") or "").rstrip("/")
        tz = str(site_cfg.get("timezone") or "America/Chicago")
        alarm = site_cfg.get("morning_alarm") is True or str(site_cfg.get("morning_alarm")).lower() in ("true", "yes", "on")
    except Exception:
        site, tz, alarm = "", "America/Chicago", False
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("health=" + json.dumps({"stale": stale, "site": site, "days": STALE_DAYS,
                                            "quote_days": s.get("quote_days"), "tz": tz, "alarm": alarm}) + "\n")


if __name__ == "__main__":
    main()
