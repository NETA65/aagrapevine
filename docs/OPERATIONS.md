# Operations runbook

Technical companion to the [README](../README.md). For the data contract between the sync
scripts and the templates see [DATA_SCHEMA.md](DATA_SCHEMA.md); for first-time setup see
[SETUP-GITHUB.md](SETUP-GITHUB.md).

- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Workflows](#workflows)
- [Sync modules](#sync-modules)
- [Recurring events](#recurring-events)
- [Events: several days, "to be confirmed", places, outside calendars](#events-several-days-to-be-confirmed-places-outside-calendars)
- [Crawl politeness](#crawl-politeness)
- [Failure handling (design guarantees)](#failure-handling-design-guarantees)
- [Repository size](#repository-size)
- [Running locally](#running-locally)
- [Resetting state](#resetting-state)
- [Adding a new source](#adding-a-new-source)
- [Environment variables and secrets](#environment-variables-and-secrets)

---

## Architecture

```
  the morning alarm (cron-job.org, 4:30 AM Central) ─┐   POST …/actions/workflows/morning.yml/dispatches
  morning.yml's own schedule (25 1-11 * * * UTC) ─────┤
  Actions → Morning check → Run workflow ─────────────┘
        │
        ▼  .github/workflows/morning.yml — Morning check (one at a time)
     look:   curl <site>/build.json → today's Central day + today's GV and LV quotes? → done (seconds)
             + its "full" too old (the 1st / 30 h)? → the full update is due (then update runs too)
     update: python -m scripts.ops.morning_check → workflow_dispatch update.yml {morning: "true"} ──┐
             follow the run → read the live build.json → (a late quote: quote.peek every 10 min)   │
             → on the 1st / after a skipped day: dispatch the full update (not followed)           │
     tidy:   delete this workflow's own no-op runs older than a day                                │
                                                                                                    │
                         ┌──────────────────── .github/workflows/update.yml ────────────────────┐  │
  triggers:              │                                                                       │  │
   • workflow_dispatch   │  JOB 1  sync  (ubuntu, Python 3.12)                                    │ ◄┘
     morning=true (the   │  ┌────────────────────────────────────────────────────────────────┐  │
     Morning check)      │  │ python -m scripts.sync.run_all                                  │  │
   • cron 10:17 UTC      │  │        [--crawl-minutes N | --quick | --morning]               │  │
   • Run workflow        │  │                                                                │  │
   • push to main        │  │  articles.py ──┐  aagrapevine.org /magazine, aalavina.org      │  │
     (config/content/    │  │  crawl.py ─────┤  both sites, sitemap + pages → every PDF      │  │
      templates/code)    │  │  podcasts.py ──┤  feeds.captivate.fm RSS (2 shows: gv, wo)     │  │
   • cron 12:07 UTC      │  │  youtube.py ───┤  channel/playlist RSS + yt-dlp listing        │  │
     (quick: the midday  │  │                │                                               │  │
      refresh)           │  │                │                                               │  │
                         │  │  instagram.py ─┤  Graph API w/ token, else public embed pages  │  │
                         │  │  drive.py ─────┤  public Drive folders (or Drive API w/ key)   │  │
                         │  │  editorial.py ─┤  /contribute, /temas-sugeridos                │  │
                         │  │  weekly_open.py┤  /grapevine-weekly-open                       │  │
                         │  │  announcements ┘  content/bulletin, content/events (repo)      │  │
                         │  │        │ each writes data/raw/<source>.json (cumulative)       │  │
                         │  │        ▼                                                       │  │
                         │  │  translate.py  EN⇄ES, offline CTranslate2 + Argos models      │  │
                         │  │        │       cache: data/translations/cache.json            │  │
                         │  │        ▼       (overrides.yml + glossary.yml win)             │  │
                         │  │  build_data.py → data/site/*.json (+ i18n, whatsnew, status)  │  │
                         │  └────────────────────────────────────────────────────────────────┘  │
                         │  git add -A data/{raw,site,state} cache.json src/assets/cache → push │
                         │                                                                       │
                         │  JOB 2  build-deploy  (runs even if JOB 1 failed → last good data)   │
                         │  checkout main → npm ci → configure-pages → PATH_PREFIX/SITE_URL      │
                         │  → eleventy (src/ + data/site/*.json) → tailwind → _site/             │
                         │    (+ _site/build.json: this build's Central day and quote days)     │
                         │  → upload-pages-artifact → deploy-pages                              │
                         │                                                                       │
                         │  JOB 3  report  (parallel to JOB 2) → one issue while a source has   │
                         │  not updated for 7+ days; closed automatically when it recovers      │
                         └───────────────────────────────────────────────────────────────────────┘

   monthly-digest.yml (1st–3rd, 12:07 · 15:07 · 18:07 · 21:07 UTC, until sent) → scripts/notify/send_digest.py → SMTP
   link-check.yml     (Sundays) → build → lychee on _site + polite check of config links → one GitHub issue
   check.yml          (every pull request + every code/settings/workflow push to main) → strict eleventy build +
                      checks (build.json included); offline Python tests; digest dry-run
```

The repository *is* the database: every run's results are committed, so the git history is also
the backup, and any past day can be inspected or restored.

## Repository layout

| Path | What | Written by |
|---|---|---|
| `config/site.yml` | All settings | people |
| `content/bulletin/*.md` (+ its pictures and documents), `content/events/*.md` | Hand-written content (optional) | people |
| `data/translations/overrides.yml`, `glossary.yml` | Translation fixes | people |
| `data/raw/<source>.json` | Cumulative per-source items (envelope + Items) | the matching sync module only |
| `data/state/*.json` | Resumable state (`crawl-state.json`; `ics_feeds.json` = the last good copy + last answer of each outside calendar) | sync modules, `build_data.py` |
| `data/translations/cache.json` | Translation memory (one entry per line) | `translate.py` |
| `data/site/*.json` | What templates read | `build_data.py` only |
| `src/assets/cache/{pdf,ig,articles,pod}/` | Small WebP thumbnails (≤ 480 px): PDF covers, Instagram posts, story images, podcast covers; plus a 128 px JPEG copy of each magazine cover (`articles/<key>.jpg`) for the monthly e-mail — classic Outlook for Windows shows no WebP | sync modules |
| `src/` | Eleventy templates, CSS, JS, images | people |
| `scripts/sync/` | The sync pipeline | — |
| `scripts/notify/send_digest.py` | Monthly e-mail | — |
| `scripts/ops/morning_check.py` | The Morning check's guard (`morning.yml`): reads the live `/build.json`, starts and follows the morning refresh, asks a late magazine, starts the full update on the 1st / after a skipped day | — |
| `src/pages/build-info.11ty.js` | `/build.json`: this build's Central day, the days of its two quotes and when the last full update ran (read by the Morning check) | — |
| `.github/workflows/` | Automation | — |
| `.cache/models/` | Translation models (~175 MB; `en_es/`, `es_en/`) — **not committed**, cached by Actions | `translate.py` |

## Workflows

### `update.yml` — Update & Deploy

| Aspect | Behaviour |
|---|---|
| Schedule | `17 10 * * *` (UTC) = 5:17 AM CDT / 4:17 AM CST: the **full** daily run. Plus `7 12 * * *` (UTC) = 7:07 AM CDT / 6:07 AM CST, the **midday refresh** (a quick run; the daily quote's backstop on GitHub's side). Minutes 17 and 7 avoid GitHub's top-of-hour congestion. **Observed (Sept 2026): GitHub starts these scheduled runs 4–8 hours late** (the 10:17 cron started 14:33–18:11 UTC, the 12:07 one 16:17–19:36; on 09-29 neither had started by 15:40 UTC), and a busy day can drop one — so the new day and the daily quote come from the Morning check's `morning` dispatch instead ([below](#morningyml--morning-check)). The two cron lines are kept byte-identical (a re-registered schedule might not fire during GitHub's incident; these do). *Decide what to sync* tells them apart by `github.event.schedule` (the exact cron string; the commit step uses it too — keep the three equal) — `schedule` + `7 12 * * *` → quick, any other schedule → full. |
| Manual run | Inputs `crawl_minutes` (default empty = the config value `sources.crawler.minutes_per_run`; whole minutes, capped at 300), `skip_crawl` (= quick run) and `morning` (the **morning refresh** — what the Morning check dispatches, `{"morning": "true"}`; it wins over the other two). |
| Run name | `run-name: "${{ inputs.morning && 'Morning refresh: new day and daily quote' || '' }}"` — a morning refresh is listed under that name (`MORNING_TITLE` in `scripts/ops/morning_check.py`, which finds its dispatched run by it when GitHub does not return the run id); every other run keeps GitHub's own name (an empty run-name falls back to it). Quoted, because the name contains ": ". |
| Push to `main` | Uses a `paths` filter: everything **except** `data/**` (but *including* `data/translations/overrides.yml` and `glossary.yml`), `src/assets/cache/**`, Markdown docs (but *including* `content/**` and `src/**`), `docs/**`, `tests/**`, other workflows. A push runs a **quick** sync and redeploys. |
| No loops | Bot commits (a) only touch excluded paths, (b) carry `[skip ci]`, and (c) are pushed with `GITHUB_TOKEN`, which never triggers workflows. |
| Concurrency | Group `update-deploy`, `cancel-in-progress: false`: a new run waits for the current one (GitHub keeps at most one pending run; a newer pending run replaces an older pending one). The sync job checks out `ref: ${{ github.ref }}` — the branch **tip** when the job starts, not the commit that queued the run (`github.sha`) — so a run that waited starts from the data the previous run just pushed instead of re-crawling from older state. |
| Sync command | Schedule 10:17 UTC: `python -m scripts.sync.run_all --crawl-minutes <sources.crawler.minutes_per_run>` (config; missing → 40; **`0` = no crawl**, the other sources still run). Manual: `--crawl-minutes <input>` (empty → config value). Push, `skip_crawl` or the 12:07 UTC schedule: `--quick` = only `drive`, `announcements`, `podcasts`, `quote` (`QUICK_MODULES` in `run_all.py`, podcasts with `--no-discover`; `quote` = 2 page requests to the magazine sites) + translation + `build_data`; YouTube, Instagram, articles, editorial, Weekly Open, shop (Book of the Month and prices), audio_project (the story lines), meetings, external events and the crawl wait for the next daily run. `morning`: `--morning` = the `--quick` sources with their quick flags — the daily quote read right after the bulletin — plus, by the Central day of the month, `MORNING_EXTRA` (`{1: ("shop", "articles"), 15: ("shop",)}`: the Book of the Month changes on the 15th, the month and its issues on the 1st; articles = hub pages only, `--no-details --no-archive`) after the quote, and only when their raw file was not read (or tried) yet that day — the Morning check may start up to three refreshes a morning — and the time boxes `MORNING_ARGS` (`drive --max-minutes 5`); the run table is titled "Morning refresh". `run_source` drops a flag a module does not have, with its value. `run_all` exits non-zero only if `build_data` fails. |
| Sync env | Secrets `GOOGLE_API_KEY`, `IG_ACCESS_TOKEN`, `IG_BUSINESS_ID` (empty when unset = harmless); `GV_MT_THREADS=4` (runner vCPUs); `GV_TRANSLATE_MINUTES` (see Timeouts); `GV_MODELS_DIR=$GITHUB_WORKSPACE/.cache/models`; `PYTHONIOENCODING=utf-8`. |
| Timeouts | Job 360 min (GitHub's maximum). The *Decide what to sync* step computes: translation budget `T = clamp(345 − crawl − 35, 10, 40)` min and sync-step timeout `min(crawl + 30 + T + 20, 345)` — e.g. 130 min for a 40-min crawl, 345 for 300 (then T = 10). **Morning mode: T = 5, step timeout 20** (the bulletin's texts are translated first; the rest waits for the daily run), so a morning refresh is published in a few minutes even on a busy day. Setup takes ~5 min, so the step limit leaves ~10 min for the data commit even when the sync overruns (a step timeout is a failure, not a cancellation, so the commit and deploy still run). Build job: 30 min. |
| Model cache | `actions/cache/restore` + `actions/cache/save`, path `.cache/models` (= `GV_MODELS_DIR`), key `translation-models-v1-<OS>-urls-<sha256 of MODEL_URLS in translate.py>` — computed from the source with `ast`, so only a change of the model URLs forces a new ~175 MB download; any other edit of `translate.py` keeps the cache. Saved only after a fresh download and only when both `<pair>/model/model.bin` (> 1 MB) and `<pair>/sentencepiece.model` exist (same test as `model_ready()`), so a failed download is never cached. If fewer than 2 models are present after a successful sync step, the check step raises a `::warning` "Translation models missing" (the only download source is argos-net.com; translation then keeps new titles in their original language). Daily restores keep it from being evicted (7-day rule). Also: pip cache (setup-python), npm cache (setup-node). |
| Commit | `git add -A -- data/raw data/site data/state data/translations/cache.json src/assets/cache` (added, changed **and deleted** files; human-edited files such as `overrides.yml`, `glossary.yml`, `content/`, `config/` are never committed by the bot; `*.tmp` / `*.part` leftovers of a stopped run are git-ignored). Commit only if something changed; message `chore(data): <what> YYYY-MM-DD [skip ci]` (Central date), `<what>` by the run: a push → `content sync after settings/content change`, the morning refresh (`MODE=morning`, whatever started it) → `morning refresh with the daily quote`, the `7 12 * * *` schedule → `midday refresh`, anything else → `daily content sync`. Push with up to 5 retries, `git pull --rebase --autostash -X theirs` between attempts (the bot's fresh generated files win a conflict; human edits to other files are kept). Runs even if the sync step failed, timed out **or the run was cancelled** (`always()`; GitHub gives `always()` steps about 5 minutes after a cancel, and the crawler saves its state on SIGTERM), so a cancelled 300-minute crawl keeps its progress. Deploy still skips cancelled runs. Simulated locally (shallow clone, concurrent human push, conflict in a generated file). **Token scope:** the sync job checks out with `persist-credentials: false`, so the write-access `GITHUB_TOKEN` is *not* in `.git/config` while `pip install` (floating versions) and the sync modules run; this step alone sets `http.https://github.com/.extraheader` from `GH_TOKEN` (covers `push` and `pull --rebase`) and unsets it on exit (`trap … EXIT`). |
| Summary | `run_all` writes a per-module table; a second step (`always()`) writes a per-source table from `data/site/status.json` (skipped while it is fixture data), turns each failing source into a yellow `::warning` (with the days since its last success), warns "Translation is not working" when texts are pending but none were translated, lists **Notes** (up to 2 `stats.warnings` per source that still updated, e.g. one YouTube feed answering 404), **Settings problems** (`status.json` → `problems.meeting` / `problems.recurring_events` / `problems.ics_feeds` / `problems.content_events`: a settings entry build_data skipped or corrected — e.g. a `meeting: skip_dates` value that is not a meeting day — also a yellow `::warning`), **Other calendars (optional, informational)** (`status.json` → `feeds`: each `sources.ics_feeds` entry's state, HTTP status, events and duplicates, and its `notes` as *Check:* lines — each also a `::notice`; a feed that a site's bot protection blocks is only a `::notice`, and feeds are **never** part of `health`, so they never open the "stopped updating" issue) and **New podcast feeds found** (`stats.discovered_feeds` of the podcasts source, plus a `::notice`); the **Daily quote** line (the day of each quote in `data/site/quote.json` after this run: "Grapevine Sep 29 · La Viña Sep 29"), **Bulletin files to fix** / **Event files to fix** (`stats.errors` of `announcements` / `manual_events`, at most 10 each, each also a `::warning`: a file that could not be read, or that links a file not saved next to it — the rest still updated) and **Scheduled bulletin posts** (`status.json` → `scheduled`: "2027-02-01 — Title (content/bulletin/x.md)" or "(Google Drive: name)", plus one `::notice`); and passes the sources that are `ok: false` with no success for **7+ days** (or never) to the `report` job as the job output `health` (one line of JSON). |
| Report | Job `report` (needs `sync`, `!cancelled()`, only on `main`, `permissions: issues: write`, no checkout): keeps **one** issue *"A content source has stopped updating"* — opened when the first source crosses 7 days (GitHub e-mails the repository's watchers), body silently edited after every run, a comment only when a *new* source joins (hidden marker `<!-- failing-sources: … -->`), closed automatically when all recover. Error texts are put in code spans so `@handles` in them never notify GitHub users. `continue-on-error`: never fails the run (e.g. Issues disabled). |
| Deploy | Needs `sync`; runs when sync succeeded, **failed or timed out** (`!cancelled()`: not when a person cancels the run) and only on `main`, so the site always redeploys the last good committed data. Checks out `main` fresh (to include the data commit) → `npm ci` → `actions/configure-pages` → `PATH_PREFIX` = `base_path` with exactly one leading and trailing slash (`/AAGrapevine/` for a project site, `/` for a custom domain or a `user.github.io` repo) and `SITE_URL` = `base_url` without trailing slash → `I18N_STRICT=1 npx @11ty/eleventy` (Tailwind runs inside the build; a UI string missing from `src/_i18n/` fails the build, so Pages keeps the previous site instead of showing a raw key such as `home.spotlight.title`). A sanity step fails the deploy if `index.html`, `es/index.html` or the CSS is missing, warns above 900 MB, and warns (never blocks) when `build.json` is missing — the Morning check could not see that build (`check.yml` fails on it instead). |
| Permissions | Workflow default `contents: read`; `sync` gets `contents: write`; `build-deploy` gets `pages: write` + `id-token: write`; `report` gets `issues: write`. These job-level `permissions` work with the repository's default read-only *Workflow permissions* setting — it does not need to be changed. Every `actions/checkout` in every workflow uses `persist-credentials: false` (zizmor's `artipacked` audit is clean); only the data-commit step logs in, see *Commit*. |
| Pinned actions | `actions/checkout@v7`, `setup-python@v7`, `setup-node@v7`, `cache@v6` (restore/save), `configure-pages@v6`, `upload-pages-artifact@v5`, `deploy-pages@v5` (Dependabot keeps them current). |
| Linting | `actionlint` (with shellcheck) passes on all five workflows: `pip install actionlint-py shellcheck-py`, then `actionlint -shellcheck <path to shellcheck> .github/workflows/*.yml`. (On Windows, actionlint's own shellcheck call can hang on `update.yml`, also before these changes: there, lint with `-shellcheck=` and run shellcheck on each step's script — fed with LF line ends — instead.) |

> **60-day rule.** GitHub disables scheduled workflows in public repos after 60 days without
> repository activity. The daily data commits are activity (the envelope timestamps change every
> run; the morning refresh commits every day too, the quote changes), so this does not happen while
> the jobs work. If the job had been failing for two months, re-enable it under **Actions → Update &
> Deploy → Enable workflow**. (Never add an API "enable workflow" keepalive: GitHub then sends the
> failure e-mails to whoever re-enabled it — the bot.)

### `morning.yml` — Morning check

Puts the new day and both daily quotes on the site by the goal — `site.morning_goal` in
`config/site.yml`, default 05:30 Central — every day, although GitHub starts scheduled runs hours late
(see *Schedule* above): a run started through the API (`workflow_dispatch`) starts within seconds, and a
morning refresh is live about 3 minutes later.

| Aspect | Behaviour |
|---|---|
| Triggers | **The morning alarm** (recommended): an outside scheduler — cron-job.org, set up by the chair ([README → 10 d](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)) — sends `POST /repos/MKP715/AAGrapevine/actions/workflows/morning.yml/dispatches` with the body `{"ref":"main"}` at **4:30 AM America/Chicago**, with a fine-grained personal access token that has only *Actions: Read and write* on this repository (it lives at cron-job.org, never in the repository; it expires after a year and is renewed by the chair). Whoever holds it can do what this repository's Actions tab can — start, re-run, cancel and delete runs, clear caches, switch workflows on or off — but not change files or secrets; if it leaks, README 10 d says what to do. **Backstop:** `schedule: "25 1-11 * * *"` — plain UTC (no `timezone:` key), 25 past every hour from 01:25 to 11:25 UTC = 8:25 PM–6:25 AM CDT / 7:25 PM–5:25 AM CST, never on the hour. GitHub starts this repository's schedules 4–8 hours late, so an evening firing that is delayed lands in the early-morning window, while one that runs on time finds today's build already live and is a 5-second no-op. **By hand:** Actions → Morning check → Run workflow; input `check_only` (look and say, start nothing). |
| Concurrency | Group `morning-check`, `cancel-in-progress: false`: one check at a time; a second one waits and then finds the work done (a third replaces the waiting one). |
| Job `look` | "Is today's update already on the site?" — 5 minutes, `permissions: pages: read`, no checkout: the site's address from `gh api repos/:repo/pages` (a custom domain included), then `curl -fsS --max-time 20 --retry 2 <site>/build.json?check=<epoch>` (the query keeps GitHub Pages' 10-minute cache from answering with an older copy) and `jq`: **done** when `day`, `quotes.gv` and `quotes.lv` are all today in Central time — the same test as `is_done()` in `scripts/ops/morning_check.py` (a unit test runs both on the same files); **full** (the reason, or empty) when the full daily update is due — `build.json` `full` before midnight on the 1st of the month (Central) or more than 30 hours ago, the same rule as `full_run_reason()` (a unit test runs both at fixed moments, across daylight saving). Done and nothing due → one summary line ("Nothing to do: today's update (built 4:34 AM CDT, with today's Grapevine and La Viña quotes) is on the site."), and the next job is skipped. |
| Job `update` | "Put today's update on the site" (the name `UPDATE_JOB` and the tidy job rely on) — when `look` did not say done (also when `look` itself failed: the script reads the live site again), or said the full update is due; 240 minutes; `permissions: actions: write, contents: read`; checkout without credentials, Python 3.12 with a pip cache of its own (`cache-dependency-path` also names `morning.yml`, so it never stands in for the full cache the other workflows share), only the five packages it imports (`requests`, `beautifulsoup4`, `lxml`, `protego`, `PyYAML`, at the versions `requirements.txt` allows — a problem with the update's translation or PDF tools never stops the morning), then `python -m scripts.ops.morning_check [--check-only]` with `GH_TOKEN` (the built-in token), `SITE_URL` (from `look`), `CHECK_ONLY`, `SCHEDULE`. A check that started, followed and asked nothing writes `idle=true`: the step "Nothing to do (deleted a day later)" then runs, and `tidy` finds the run by it. |
| What the guard does | 1. Reads the live `build.json`; done → a summary, and step 5. 2. An Update & Deploy run **waiting** in the queue → it follows that one and never dispatches (in the `update-deploy` group a new run would replace the waiting one). 3. The live build is not today's (or cannot be read) → `workflow_dispatch` of `update.yml` with `{"morning": "true"}` and `return_run_details: true` (the 2026 API answers with the run id; a 204 or a refusal of that field — then sent again without it — is followed by a look at the newest `workflow_dispatch` runs named "Morning refresh: new day and daily quote"); it follows the run every 20 s for up to 45 minutes (a run that GitHub cancelled because a newer one took its place is followed to that one, up to 3 times), then reads `build.json` every 15 s for up to 5 minutes until it shows that run's build (its run id, or a build made after the run was created); a finished run the site does not show is "Cannot confirm" — never a reason for another run. 4. Today's build is up but a magazine's quote is not today's: from 90 minutes before the goal to 90 minutes after (4:00–7:00 AM) it asks **only that magazine's** home page, every 10 minutes (`quote.peek`: the date read from the quote's heading; nothing is written), and starts the morning refresh again once the quote is out — never a question sooner than 10 minutes after a run it started or followed read the pages. Before the window it stops (a later check asks). A check that begins after the window (a late schedule, or Run workflow) asks once, and brings the quote if it is out; otherwise — and at the end of the window — a yellow note that says when the magazine was last asked. In steps 3 and 4 together a check starts at most 3 morning refreshes (`MAX_RUNS`; each reads both magazines' home pages), never two in a row without 10 minutes between them, and nothing — no refresh, no question — after 170 minutes (`GUARD_MAX`), so its last refresh still ends inside the job's 240 minutes; today's build still not there after that is a red ✗. "Today" is the Central day of each moment: a check still running at midnight (a late evening firing, a run that waited in the queue) works for the new day from then on — the new day's build is today's, and a late quote right after midnight is too early to ask (the morning's checks ask); its summary is about the new day, with a *Began* row. 5. Once today's update is on the site — also when it already was, or a waiting run or another update brought it — on the 1st of the month (Central) when no full update has run since midnight, and whenever no full update has run for 30 hours (GitHub skipped or failed one), it dispatches `update.yml` with no inputs — the full daily update — without following it; never while an Update & Deploy run waits in the queue or a full one runs, and not again within 12 hours of one started by Run workflow after the last full update (`FULL_RETRY_AFTER`: a full update that fails is tried again the next morning, not at every hourly check). "The last full update" is the live `build.json` `full` = `status.json` `full_update`: the newest `attempted` of the sources only the full run reads (`run_all.FULL_ONLY`: YouTube, Instagram, editorial, Weekly Open, audio_project, meetings, external events) — no state file of its own; this checkout's `status.json` only when the live site cannot say. |
| Run summary | "## Morning check — Tuesday, September 29 (Central time)", then "✅ Today's update is on the site since **4:34 AM CDT** — goal 5:30 AM." (a check that saw it arrive) or "✅ Today's update is on the site — the latest build is from **1:00 PM CDT**." (it was already there: that build may be a later one, so nothing is said about the goal) and a table: the new day (built at), each quote's day, the Update & Deploy run (link, duration), what started the check, the full daily update (started, why). Annotations: `::warning title=After the goal::` (a check saw it go live after the goal), `::warning title=A daily quote is late at the source::` (not out when last asked — the note gives that time; the site shows yesterday's quote labelled "Yesterday"), `::warning title=A daily quote could not be read::` (the page showed it, the refreshes did not bring it), `::warning title=Cannot confirm::` (the run finished but the site did not show it within 5 minutes — never a second dispatch for that), `::error title=Morning update failed::` with the run's link. |
| Exit codes | **0** — today's update is on the site, or only a quote is late at the source, or a finished run is not shown yet ("Cannot confirm"), or `--check-only`; **1** — an update run failed, or did not start or finish within 45 minutes, or today's build was still not on the site after 3 morning refreshes or 170 minutes (a red ✗: GitHub e-mails whoever started the check — for the alarm, the owner of its key; the runs the guard starts are the bot's, and GitHub e-mails nobody about those, so the guard follows them and fails itself); **2** — no token, repository or site address. |
| Job `tidy` | "Tidy up old runs that had nothing to do" — after `look`, `if: always()`, `permissions: actions: write`, no checkout, bash + `gh api` + `jq`: lists this workflow's own runs of the week before yesterday (`status=success`, `created` up to 24 hours ago — checked again with `jq`) and deletes those whose "Put today's update on the site" job was **skipped** (pure no-ops) or ended at its step "Nothing to do (deleted a day later)" (`IDLE_STEP`: it started, followed and asked nothing — the update was already there, or it was too early to ask a magazine); never a failed run, never one that started or followed an update or asked a magazine, never another workflow's run; at most 50 a run; a problem — the runs or a run's jobs cannot be listed, a run cannot be deleted — is only a `::notice`. |
| `/build.json` | `src/pages/build-info.11ty.js`: `{v, built, day (the build's Central day), tz, quotes {gv, lv} (the days of the quotes on the home page), data (status.json generated), full (status.json full_update: when the last full update ran), run (GITHUB_RUN_ID), version, commit}` — not linked, not in the collections, sitemap or search; `update.yml` warns and `check.yml` fails when it is missing. |
| Failure modes | A magazine late → the new day goes up at once, bounded polling, a yellow note, the site labels the older quote "Yesterday", the later updates pick it up. The alarm fails (401 expired key, 404, cron-job.org down) → cron-job.org e-mails its owner; the hourly schedule still runs (late). Update & Deploy fails or never starts → exit 1 (red). The site cannot be read → the refresh is started anyway, then "Cannot confirm". A long manual crawl in the evening → the morning refresh waits behind it and the guard gives up after 45 minutes (red) — start 300-minute crawls in the morning. Update & Deploy disabled → the dispatch is refused → exit 1 with "Enable workflow". If the guard itself crashes before following a run it started, a failed update shows only on `/status/`. |

### `monthly-digest.yml`

Sends **last month's** digest, once. Scheduled tries run four times a day on the 1st–3rd
(`7 12,15,18,21 1-3 * *` UTC = 7:07 AM – 4:07 PM CDT / 6:07 AM – 3:07 PM CST; GitHub starts them late,
sometimes by hours).

Except for a preview, the first step (`check`) stops the run unless the four secrets `SMTP_SERVER`,
`SMTP_USERNAME`, `SMTP_PASSWORD` and `DIGEST_TO` exist. A scheduled try then goes on only if both hold:
- it is the 1st–3rd **Central** day, from 7 AM Central (`TZ=America/Chicago date`);
- the month has no unexpired `digest-sent-YYYY-MM` artifact. The check is
  `gh api repos/:repo/actions/artifacts?name=digest-sent-<month>`, which needs `permissions: actions: read`.
  If the API does not answer: a `::warning`, nothing is sent, and the next try checks again.

`send_digest` then waits for the data. It exits 3 (a `::notice` "Digest waits"; the run stays green) while a
source it reads has not been tried since the month ended (below). The tries from noon Central on the 3rd pass
`--stale-ok`. Exit 0 in send mode (sent, or nothing new in the month) uploads the `digest-sent-<month>`
artifact (kept 40 days), so the later tries skip. On the 1st the Morning check starts the full daily update
early ([`morning.yml`](#morningyml--morning-check), step 5), so the wait is usually over by the first try.

A manual run defaults to **preview** (`--dry-run`, uploaded as the `digest-preview` artifact). It takes an
optional *month*, the month the digest **covers** (`--month YYYY-MM`). Anything typed there is passed on
(spaces removed), so a mistyped month makes `send_digest` exit 2 instead of sending another month's edition.
Unticking *Preview only* sends at once — no day / hour / marker guard, `--stale-ok` — and marks the month (a
month with nothing new is marked without an e-mail, as on a scheduled try).
The public address comes from the Pages API (`gh api repos/:repo/pages`), falling back to `site.url`.

`scripts/notify/send_digest.py` (standard library only; PyYAML for `config/site.yml`, with a small built-in
reader as the fallback) builds the same **edition** as the `/digest/` page (`eleventy/filters/community.js`
→ `buildMonthlyDigest`, `monthlyDigestText`). Keep their rules in step:

- **edition** = ONE Central-time calendar month P, named after it (*September 2026 digest* / *Resumen de
  septiembre de 2026*). By default it is the month before the run's Central month (`edition_of` /
  `digestEdition`); `--month` / `MONTHLY_NOW` choose another. It is on `/digest/` from the first build on the
  1st of K = P+1 all through K. A date counts on its Central calendar day (11:30 PM CDT on September 30 is
  September).
- Everything is read from the **full** data files, never `whatsnew.json` (it keeps only its newest
  `WHATSNEW_MAX` = 150 entries):
  - **bulletin** (`announcements.json`): counted on the day it was added to the site — the **latest** of
    `date` (else `first_seen`), `first_seen` and `extra.publish` (a scheduled post), so a post dated in an
    earlier month but saved later (written on the 28th, saved on the 2nd, after that month's e-mail) is in
    the edition of the month it appeared, like a committee upload; in P, not after now + 1 day, not expired.
    Pinned first, then newest.
  - **events that took place** (`events.json`, any category but `committee`): starting in P (an event over
    several days counts in the month it starts) and started by now. P's committee meeting is added once it
    has started: its record, else the `meeting:` rule (`skip_dates` honoured; `events.json` drops a meeting
    once it is over). Listed with their days only (no time, no "every month", no "to be confirmed"). Never
    counted as news, so events alone never send an e-mail. `events.json` keeps only the newest 12 past
    one-off events, so a very busy month loses its oldest.
  - **committee uploads** (`drive.json`): counted on the **later** of `date` (the date the file's name starts
    with, else when the photo was taken or the file created — drive.py) and `first_seen` (when the site first
    had it: `later_of` / `laterOf`). A report named "2026-08-11 …" but added on September 25 is in the
    September digest; a photo taken on the 30th but uploaded on the 2nd is in the next one — every upload is in
    exactly one edition. Each file's row shows its own `date`. Not bulletin documents, and not dated flyers
    (events). The photos and videos of an album (`isPhotoItem`) are ONE row per album for the month: "Photos:
    Booth — 5 new photos", linking `/photos/#<album>` on the page and `/photos/` in the e-mail.
  - **magazines** (`articles.json`): the issues with stories whose `extra.pub_date` is in P (so the September
    digest features the October Grapevine, online since September 23). A story without a `pub_date` counts on
    its issue's earliest `pub_date` (`story_day_of` / `storyDayOf`) — never on `first_seen`, so the stories
    the site found at its launch never all land in one edition. Per issue: the count, all its stories, the
    free-to-read count, and whether it is the newest issue on `/read/` (a removed story does not count, as on
    `/read/`; its link is then `/read/#gv-current` / `#lv-current`, else `/read/`). Also the theme
    (`issueTheme`: the issue's own, else its stories' `issue_theme`, else the editorial calendar) and
    `digest.highlights` stories (free to read first, then members' stories; never the writers' stories).
  - **writers**: `spotlight.json` stories by Area 65 / Texas writers whose `extra.pub_date` is in P. Every
    story is in exactly one edition.
  - **podcasts, videos, documents** (`episodes`, `videos`, `pdfs`): `date` in P and not after now + 1 day.
    A YouTube upload of a podcast episode (same Central day, same title or season/episode) is folded into
    the episode as "also on YouTube".
  - **Instagram** (`instagram.json`): the magazines' posts dated in P (not after now + 1 day), per account
    (`extra.account`, else `category`; Grapevine, La Viña, then any other; La Viña first in Spanish): how
    many, and the 3 newest (their title — the caption's first line — and day, linking to the post), plus ONE
    link to the site's `/instagram/` page. The WhatsApp / e-mail texts and the e-mail's text part give only
    each account's count and that link. The file keeps each account's newest `keep_per_account` (130) posts
    — about 65 days at the accounts' ~2 posts a day — so P's count holds on the page all through K (a much
    busier month could lose its oldest posts late in K; the e-mail, sent early in K, is complete).
- ONE pointer at the end: "Coming up in K" → `/monthly/K/`. These belong to the **toolkit** and are never in
  the digest: the committee meeting and its Zoom details, events not over yet, the weekly meetings, story
  deadlines, La Viña's topics, the phone lines, Book of the Month, subscriptions, the daily quote, the
  Instagram accounts to follow (the digest has last month's posts).
- The intro counts, in this order: magazine stories, podcast episodes, videos, Instagram posts, documents,
  committee files, photo albums, bulletin posts (`COUNT_ORDER`, both files).
- English half, then Spanish half (La Viña first there), from the `i18n` fields build_data produced.
  `digest.per_section` items per list, then "and N more". In the Spanish half, issue labels read as in a
  sentence ("septiembre/octubre de 2026") and Grapevine's issues and writers say "(en inglés)"; La Viña's say
  "(in Spanish)" in the English half. Days are written like the website (Intl): "Sat, Sep 12" / "sáb, 12 de
  sept", with the year when it is another year (`tests/test_digest_parity.py` DaySpelling). Items with the
  same date are listed in the site's order (`js_order`).
- The HTML: every section title is an `h3` (the "Coming up" box too), sub-groups are `h4`, and every text is at
  least 4.5:1 against its background (the small print is "muted", never "faint"; a test checks it).
- Subject: `Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026` (`site.title` first).
  Multipart HTML + plain text, RFC 2047 headers, `List-Unsubscribe`, several recipients → Bcc.
- **Waiting for the data**: before sending, `data/site/status.json` must show every source it reads
  (`FRESH_SOURCES`: announcements, manual_events, drive, articles, pdfs, youtube, podcasts, instagram) tried
  (`sources[].attempted`, else `updated`) since 00:00 Central on the 1st of K. A source last tried before
  that, but within `FRESH_IDLE_DAYS` = 3 days of it, gives exit 3 and nothing is sent. An older one has
  stopped running and is not waited for (`/status/` shows it). `--stale-ok` and `--force` send anyway;
  `--dry-run` never waits and says what a scheduled send would wait for. (The morning refresh reads only the
  quick sources — on the 1st also `articles` —, so in practice the e-mail waits for the month's first full
  update: `pdfs`, `youtube` and `instagram` are read only there.)
- Sending: port 465 = SSL; any other port must offer STARTTLS, or the run stops before the password is sent
  (`RuntimeError`, exit 1). Connecting and logging in are tried 3 times on network trouble. The message is
  handed over **once**: a failure at that point is reported as "It MAY have been sent — check before
  re-running" and never retried, because a retry could e-mail every district twice.
- Nothing new in P (no news — Instagram posts count —, no writers) → nothing sent (exit 0).
- Exit codes: 0 = sent / previewed / nothing new; 1 = SMTP failure; 2 = not configured, `--month` not
  YYYY-MM, or (sending) a month that is not over yet; 3 = waiting for the data.

`tests/test_digest_parity.py` builds the same editions with `buildMonthlyDigest` (Node.js) and
`send_digest.collect`, on a small data set with the edge cases and on the repository's own data. It fails on
any difference in what they pick (news, albums, twins, Instagram accounts, issues, writers, events), so a rule
changed on one side only is caught by the Code check.

```bash
python -m scripts.notify.send_digest --dry-run                                     # last month → .tmp/digest.html + .tmp/digest.txt
python -m scripts.notify.send_digest --dry-run --month 2026-09 --as-of 2026-10-01  # the September digest, as on October 1
MONTHLY_NOW=2026-10-01T15:05:00Z npx @11ty/eleventy                                # that /digest/ page (and October's toolkit)
```

### `link-check.yml`

Sundays. Builds the site with `PATH_PREFIX=/`, runs **lychee** over `_site/**/*.html` with
`--root-dir _site` (internal links are checked on disk), `--host-concurrency 2`,
`--host-request-interval 1s`, a 3-day response cache, and accepts 403/429 (bot walls). High-volume
or bot-hostile hosts are excluded (aagrapevine.org, aalavina.org, YouTube, Instagram, Google,
Zoom, podcast platforms, social networks). Then it checks every URL under `links:` in the config
with the project's `PoliteSession` (robots.txt + 5 s Crawl-delay). Results: run summary + a single
issue *"Broken links found by the weekly check"* that is commented on while problems persist and
closed automatically when clean. It never fails the workflow.

Checked locally (2026-09-23): lychee 0.24.2 — the version `lychee-action@v2` installs — accepts every
flag used; `lychee --offline --root-dir <abs path>/_site '_site/**/*.html'` on a `PATH_PREFIX=/`
build resolved all internal links (0 errors), and a page with a deliberately broken link was flagged.
To reproduce on Windows, pass the root dir as `C:/…` (Git Bash: also `MSYS_NO_PATHCONV=1`).

### `check.yml` — Code check

On every `pull_request`, on every **push to `main`** that touches `scripts/**`, `tests/**`, `src/**`
(not `src/assets/cache/**`), `eleventy/**`, `eleventy.config.js`, `config/**`, `content/**`,
`data/translations/{overrides,glossary}.yml`, `package*.json`, `requirements.txt` or any workflow in
`.github/workflows/` (the tests read the workflows: the schedules, the morning mode, the Morning check;
most work here is pushed straight to `main`, so without this the tests would never run), and
on `workflow_dispatch`. `permissions: contents: read`, nothing published; the bot's data commits
never trigger it (pushed with `GITHUB_TOKEN`). Job `build`: `npm ci` →
`PATH_PREFIX=/<repository name>/ I18N_STRICT=1 npx @11ty/eleventy` → the same sanity checks as
*Update & Deploy* (`index.html`, `es/index.html`, `assets/css/main.css`), plus `build.json` — an error
here, where *Update & Deploy* only warns. Job `tests`: Python 3.12,
`pip install -r requirements.txt`, Node.js 22 + `npm ci` (the tests that run the site's own JavaScript
through `tests/nodejs.py` — the district report, the offline worker, the digest parity, the one-tap
phone links — are skipped without them), `python -m unittest discover -s tests -v` (no translation models
are downloaded, so model tests are skipped; the rest runs offline in a few seconds), then
`send_digest --dry-run` into the runner's temp folder (a smoke test of the optional e-mail). Dependabot
PRs therefore show a ✓/✗ before merging (the chair merges only on green), and a push that breaks the
tests shows a red ✗ on its commit. A push runs this alongside *Update & Deploy*, which still deploys:
a red ✗ here means "fix or revert that change", not "the site is down".

### `dependabot.yml`

Monthly grouped PRs for GitHub Actions and npm (minor/patch only), checked by `check.yml`. Python packages in
`requirements.txt` float within their current **major** version (`>=x,<next-major`), so each daily run picks up
minor/patch releases automatically; a new major version is only installed after someone raises the cap by hand.
`yt-dlp` is deliberately uncapped — it must keep up with YouTube changes.

## Sync modules

All modules follow the same conventions (see [DATA_SCHEMA.md](DATA_SCHEMA.md)): `main(argv)`,
`python -m scripts.sync.<name>`, output via `save_raw()`, cumulative `merge_items()` (preserves
`first_seen`, never drops items on a bad day), `ok=false` + error message on failure, time-boxed,
`--dry-run`. Each module's docstring is the detailed reference.

| Module | Source → output | Normal path | Fallbacks / safety | Useful flags |
|---|---|---|---|---|
| `articles.py` | aagrapevine.org `/magazine`, aalavina.org `/la-revista` → `articles.json` | Issue hub pages (titles, bylines, public teasers, card images); each article page fetched once for issue/topic/section/paywall flag | Home page / `/revista-2` if a hub fails; missing fields retried ≤ 3× a week apart. **Never stores article bodies.** | `--max-details 40`, `--max-seconds`, `--no-details`, `--only gv\|lv` |
| `crawl.py` (+ `crawl_rules.py`, `crawl_pdf.py`) | both sites → `pdfs.json`, `data/state/crawl-state.json`, `src/assets/cache/pdf/` | Sitemaps → priority queue (hubs daily, new pages, changed `<lastmod>`, events, re-checks every `recheck_days`); conditional GETs; ~30 % of time on PDF work (download ≤ `pdf_details_per_run` new PDFs ≤ `pdf_max_mb` for page count/title/thumbnail; HEAD others) | Resumes daily from state; a PDF becomes `gone` only after **two** failing checks at least 24 h apart (404/410, or an HTML page where the file was — `gone_strike_at` marks the first); a gone PDF that a page still links is re-checked after a week, later monthly, and comes back when it answers; a PDF on **another** site whose host has not answered at all for 30+ days (4+ tries, `head.unreachable_since`) is gone too — the magazine sites' own files are never retired that way; skip rules for login/cart/paywalled paths; PDF author metadata deliberately not read (anonymity) | `--minutes N` (0 = rebuild from state, no network), `--details`, `--url`, `--max-pages` |
| `podcasts.py` | shows in `sources.podcasts` (`gv` AA Grapevine's Podcast, `wo` Grapevine Weekly Open AA Meeting) → `podcasts.json` (category = show key) | RSS via requests + feedparser | Previous episodes kept on a bad feed; an episode that leaves the feed is `gone` only when its audio 404/410s; weekly discovery of new show feeds, never auto-added: listed under *New podcast feeds found* in the *Update & Deploy* run summary (with a `::notice`), and in `stats.discovered_feeds` of `podcasts.json` / `status.json` (the `/status/` page does not show them) | `--limit`, `--discover`, `--no-discover` |
| `youtube.py` | channel `UCI9uFLJ__aXT3-At0PlPWUQ` → `youtube.json` | Channel + uploads + playlist RSS every run | yt-dlp full listing weekly and a few dozen per-video detail fetches per run; if yt-dlp is blocked on CI IPs, RSS alone keeps the site current; deletions confirmed via oEmbed only after a complete listing | `--backfill`, `--no-backfill`, `--details`, `--backfill-minutes` |
| `instagram.py` | two accounts → `instagram.json`, `src/assets/cache/ig/` | Graph API Business Discovery if `IG_ACCESS_TOKEN`+`IG_BUSINESS_ID`; else the public profile **embed** page (a few requests/day) | web_profile_info JSON → profile HTML → optional RSSHub mirrors → post embeds; keeps last posts when all fail. `sources.instagram.anonymous: false` (or env `IG_ANONYMOUS=0`) disables every non-API request: only the API + `content/instagram.yml` | `--strategies`, `--account`, `--keep`, `--no-enrich`, `-v` |
| `drive.py` (+ `drive_listing.py`) | public Drive tree under `drive.root_folder_id` → `drive.json` (documents, photos, flyer events, bulletin posts — Drive folder `bulletin` / `boletín`, or the older `announcements` / `anuncios`; a post's name may carry `(pinned)` / `(fijado)`, `(until …)` / `(hasta …)` and `(from …)` / `(desde …)` — also `publish` / `publicar` — → `extra.publish`, taken out of the headline only when it holds a date; an undated scheduled post is dated its `(from …)` day) | Public "embedded folder view" HTML (no key) | Drive API v3 when `GOOGLE_API_KEY` is set (falls back per folder); a folder only counts as read when Drive returned a real folder page, so a network error never deletes items; spreadsheets and `PRIVATE`/`(Responses)` names never published | `--no-api`, `--max-depth`, `--max-minutes`, `--include-loose` |
| `editorial.py` | `/contribute`, `/temas-sugeridos` → `editorial.json` | Grapevine editorial calendar (themes + deadlines); La Viña evergreen topics | A parsed page replaces that publication's topics; a failed page keeps the previous ones | `--only`, `--gv-html FILE` |
| `weekly_open.py` | `/grapevine-weekly-open` → `weekly_open.json` | Parses day/time/Zoom ID/passcode, converts to Central | Previous item kept on failure | `--html FILE` |
| `audio_project.py` | aagrapevine.org `/audio-portal`, aalavina.org `/graba-tu-historia` + `/instrucciones-graba-tu-historia` (`sources.grapevine.audio_project`, `sources.lavina.record_*`) → `audio_project.json` | The story lines: phone number, keys to press, length, the e-mail address for recordings (Cloudflare-protected → decoded), the no-speaker-recordings note, Grapevine's playlists, La Viña's copyright sentence. 3 requests a day | A page not fetched or not understood keeps that part's previous data (`ok: false`); when only La Viña's instructions page fails, its steps come from the previous run and the rest is fresh (`ok: true`, a note in `stats.warnings`) | `--dry-run`, `--html-dir DIR`, `--save-html DIR` |
| `announcements.py` | `content/bulletin/*.md` → `announcements.json` (the `/bulletin/` page; a post needs no header: title from its first heading or file name, date from its file name, else its `publish:` day, else its first sighting; `publish: YYYY-MM-DD` schedules it — `extra.publish`; a bad value, or one after `expires:`, is a file problem; `stats.active` counts the posts shown today, in Central time; pasted HTML → Markdown; links to pictures / documents saved next to it → `/bulletin/files/`, which `eleventy.config.js` publishes); `content/events/*.md` → `manual_events.json` (hand-written `title_es` / `summary_es` — or `title_en` / `summary_en` — → `extra.own_i18n`, used by build_data instead of a machine translation) | Markdown + YAML front matter (no network) | The folder is the source of truth; a file with a formatting mistake is skipped and reported on `/status/` instead of breaking the run | `--dry-run` |
| `quote.py` | aagrapevine.org `/`, aalavina.org `/` (`sources.<pub>.quote_page`) → `data/raw/quote.json` (items + 14-day `history`, raw only; each day's entry has `seen` — the UTC time that day's quote was first read, kept on later reads; an entry written before these times were kept has none and never gets one — which `build_data` turns into `status.json` → `quote_days`) → `data/site/quote.json` (items) | The `#quote-of-the-day` teaser (`article.node--type-quote`): heading date (year inferred around today, Central), quote text (outer quotation marks cleaned, never translated), attribution / source split at "From:" / "De", the publication's own e-mail sign-up link. One request per site (none when an earlier module of the run read that page), in every run (full, quick, morning). `peek()` is the Morning check's question "is today's quote out?": only a date read from the heading counts; nothing is written | Falls back to the view embed near the top of the page; a publication that fails keeps its previous quote (and last known sign-up link), `ok=false`; an older quote than the one known never replaces it | `--dry-run`, `--only gv\|lv`, `--html-dir DIR`, `--save-html DIR` |
| `translate.py` | all raw titles/summaries/bodies → `data/translations/cache.json` | CTranslate2 + Argos 1.0 models (auto-downloaded to `GV_MODELS_DIR`), sentence splitting with per-sentence ¿…? / ¡…! pairing, protected spans (URLs, handles, times, codes, sizes like 8.5 x 11, "Firstname X." names), glossary (+ built-in Step/Tradition ordinals, "[Season N, Episode M]" → "[Temporada N, Episodio M]"), sentence case for Spanish titles / Title Case for English titles, an output guard (rejects repeated-word loops, changed numbers, entity leaks → keeps the original) and a vocabulary guard (never outputs "coger" — vulgar in Latin-American Spanish) | Cache hits never re-translate; `overrides.yml` always wins; glossary edits re-translate only affected texts; bump `ENGINE_VERSION` to re-translate all | `"text" --to es`, `--download`, `--stats` |
| `build_data.py` | `data/raw/*` + content/ + config → `data/site/*.json` | Adds `i18n`, `machine`, `is_new`; builds events (12 months of committee meetings + `recurring_events:` from the config + flyers + manual + external + the optional `sources.ics_feeds` calendars, each real event once — see [Events](#events-several-days-to-be-confirmed-places-outside-calendars)), `whatsnew.json` (newest 150), `status.json` (+ `feeds`: the health of each outside calendar; `scheduled`: the bulletin posts whose `publish` day is still to come — left out of every site file until that day, Central time — soonest first, at most 20; `quote_days`: when each of the last 7 mornings' quotes came in against `site.morning_goal`, for `/status/` — a day whose quote came in at a time not recorded is left out; `full_update`: when the last full update ran, for `/build.json`). A published scheduled post is news from the start of its day (`Ctx.effective_ts`: What's New, the feed, the "New" badge, the digest) | Only writer of `data/site/`; templates read nothing else. A bad `meeting:` / `recurring_events:` / `ics_feeds:` entry (or a `skip_dates` value that is not one of the rule's days) is skipped and listed in `status.json` → `problems` (and as a **Settings problem** in the run summary). Its only network request: each `.ics` feed, at most once a day (`--offline`: none) | `--offline`, `--no-translate` |
| `run_all.py` | orchestrator | Runs every module in turn, isolating failures, then translation + `build_data` | A crashing module is recorded as `ok=false` (see `run_module`) and the rest continue | `--crawl-minutes N`, `--quick`, `--morning` |
| `meeting.py` | config `meeting:` (+ the rule engine for `recurring_events:`) | `upcoming_rule_dates(MonthlyRule, count, tz)`: the Nth weekday (1–5, or −1 = last) of every month, start–end on the local clock → UTC instants (right across DST changes and month/year ends), `skip_dates`. Used for the committee meeting (3rd Wednesday 7–8 PM Central by default) and every recurring event | `check_skip_dates()`, shared by the meeting and every recurring event: a skip date that is not a date, or not the rule's day of its month, is ignored and noted ("skip date “2026-12-17” is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16)") → `problems.meeting` / `problems.recurring_events` | — |

## Recurring events

`config/site.yml` → `recurring_events:` lists what the committee does every month (the GV/LV booth
at CityWide Dallas: 2nd Saturday, 17:00–20:00 Central). Chair-facing instructions are in the
[README](../README.md#add-a-recurring-event); the data fields in [DATA_SCHEMA.md](DATA_SCHEMA.md).

| Where | What happens |
|---|---|
| `build_data.recurring_specs()` | Validates each entry. **Skipped** (reason in the log and in `status.json` → `problems.recurring_events`, shown as a *Settings problem* in the run summary): not a mapping, no title, a `week_of_month` other than 1–5 / −1 (also `"2nd"`, `"segundo"`, `"last"`, `"último"`), an unknown `weekday` (English or Spanish, plural and accents accepted), no readable `start` (`parse_hhmm`: `"17:00"`, `"5 PM"`, unquoted `17:00`), a duplicate `key`. **Noted, still shown**: an unreadable / not-later `end` (→ one hour), a `skip_dates` value that is not a date, or not one of the event's own days — e.g. the Sunday or the 1st Saturday for a 2nd-Saturday event — (ignored; the note names that month's real date), a `months_ahead` outside 1–24 (→ 6), a `url` / `online_url` that is not http(s) (left out; the event links to `/events/`). A missing `key` is made from the title; keys are slugified and cut to 32 characters so the card anchor keeps its date. An exception anywhere is caught in `build_events` (same as `meeting:`). |
| `build_data.recurring_events()` | `meeting.upcoming_rule_dates()` → the next `months_ahead` dates **plus** the dates of the last 90 days. One event per date: id `ev:recurring:<key>:<YYYY-MM-DD>`, source `committee`, category `recurring`, fixed i18n (the config's `title`/`title_es`, `summary`/`summary_es`; a missing language is machine-translated once and marked in `machine`) and a rule-written `recurrence_label` (the committee meeting's wording: "Every second Saturday of the month · 5:00 – 8:00 PM") plus `extra.rule`, from which the pages write the same line with the meeting's helpers. `build_events` marks the past ones `past: true` without counting them in `PAST_EVENTS_KEEP`. Never `is_new`, never in `whatsnew.json` (`SCHEDULED_EVENT_CATEGORIES`). |
| `/events/` (`normalizeEvents` in `eleventy/filters/committee.js`) | Every upcoming date as its own card in the **NETA 65 events** group (`GROUP_OF.recurring = "neta"`), with an "Every month" badge, the day rule, the place and the external "Event details" link; "add to calendar" per date. Past dates are left out of the *Past events* list (`whereNot("recurring", true)`). |
| Calendar feeds (`events-ics.11ty.js`) | One `VEVENT` per date — like the committee meetings — with a stable `UID` from the id (`ev-recurring-<key>-<date>@neta65-gvlv`, `-es` in the Spanish feed), UTC `DTSTART`/`DTEND`, `LOCATION`, `URL`, and the rule line in `DESCRIPTION`. Chosen over one `RRULE` series because UTC instants need no `VTIMEZONE` (an `RRULE` on a UTC start would drift an hour at every DST change; with `TZID` it needs a `VTIMEZONE` that Outlook.com handles unevenly), a skipped month is simply absent (no `EXDATE` quirks), and each date can change on its own. The feed carries the 90 past days (subscribers keep them, as for the committee meetings) and `months_ahead` dates ahead; `REFRESH-INTERVAL` 12 h rolls new dates in. |
| Home, search, GV/LV report (`/monthly/#report`) | Only the **next** date of each series (`extra.series`): `homeEvents` (links to the card on `/events/`; the next date of every series **always keeps a place** in the home row of 4 — the other places go to the soonest one-off events, at least one of them when there is any, then at most one more committee meeting; shown by date), the search index (one `event` entry, found by "every month" / "cada mes" too), the report (`report.js` → `upcomingEvents`). `/meetings/` shows an "Also every month" box (`cmRecurringNext`). |
| Monthly toolkit, monthly digest, e-mail | The toolkit (`/monthly/YYYY-MM/`: its dates, poster and message — `monthModel` in `eleventy/filters/monthly.js`) lists every date of its month; on this month's page a date is marked "Over" once it ends (`overAt`, `src/assets/js/monthly.js`). The monthly digest (`community.js` → `monthEventsHeld`) and the e-mail (`send_digest.month_events`) list last month's dates that took place — days only, no "every month" — and never count them as news (`total_count`), so a month with only the booth sends no e-mail. |

## Events: several days, "to be confirmed", places, outside calendars

Chair-facing instructions: [content/events/README.md](../content/events/README.md) and the
[README](../README.md#6-bulletin-posts-and-events-without-drive-optional); the data fields:
[DATA_SCHEMA.md](DATA_SCHEMA.md) (§3, events).

| Topic | How it works |
|---|---|
| Several days (the Area assemblies, Fri–Sun) | A content/events file with `start: 2027-03-19` and `end: 2027-03-21` (dates only) is an all-day event whose `end` is the **last** day. `build_data.event_end_ts` puts its end at 23:59 Central on that day (like every event it keeps `past: false` one more day: the `build_events` cutoff is now − 24 h); on the pages `normalizeEvents` (`eleventy/filters/committee.js`) sets `multiDay`, a range tile ("MAR · 19–21 · Fri–Sun"), `rangeLabel` ("Fri, Mar 19 – Sun, Mar 21, 2027" / "Vie, 19 de mar – dom, 21 de mar de 2027") and `timeLabel` "3 days"; the card's `data-cm-expire` is midnight after the last day. `/events.ics`, `/es/events.ics`, the per-event ".ics file" button (`CM.downloadIcs`) and the Google / Outlook links use DATE values with the **exclusive** end (`DTEND;VALUE=DATE:20270322`). Home (`homeEventInfo`, `homeEvents` via `chicagoDayEndMs`), the district report (`eventWhen`: "Fri, Mar 19 – Sun, Mar 21") and the monthly toolkit (`dateRow`, over at midnight after its last day) show the range; the monthly digest and its e-mail (`cmEventDays`, `event_row`) list it with its days only, in the digest of the month it **starts** in, once it has started. A timed event that only runs past midnight is not "several days" (it must last more than 18 hours). |
| Details to be confirmed | content/events `tentative: true` (also `yes`, `sí`) → `extra.tentative: true` (announcements.py); an outside calendar's `STATUS:TENTATIVE` does the same. Shown as the badge "Details to be confirmed" / "Detalles por confirmar" (`ui.tentativeBadge`, class `badge-tbc`: dashed outline; the explanation is its tooltip and screen-reader text) on `/events/` cards, the home row, the "next event" card of `/announcements/` and search results (index flag `tb`); as " · Details to be confirmed" on the monthly toolkit's date rows, poster and message, and in the district report. The monthly digest lists only events that took place, so it never shows it. Calendar files: `STATUS:TENTATIVE` (every other event `STATUS:CONFIRMED`), and the first line of the description says it (Google / Outlook links cannot carry a status). Deleting the line makes the event confirmed on the next run. |
| The place in both languages | A place is **never** machine-translated. content/events `location_es` (in an English file) / `location_en` (in a Spanish one) → `extra.own_i18n.location` → build_data writes `i18n.location` (`location_pair`). A place that is not known yet ("Venue to be announced", "TBA", "Lugar por anunciarse", "Por confirmar" — `location_is_tba`) gets `extra.location_tba: true` and, when the other language was not written, the site's own words ("Lugar por anunciarse" / "Venue to be announced"). Such a place is shown as plain italic text with an hourglass (no map pin), is left out of `LOCATION` in the calendar files and of the Google / Outlook links (it goes into the description instead) and of the past-events list. Every page reads `i18n.location[lang]`, falling back to `extra.location`. |
| Outside calendars (`sources.ics_feeds`) | `build_data.ics_events()`: per feed ONE request (see [Crawl politeness](#crawl-politeness)); the answer is `ok` (a calendar file that parses), `blocked` (HTTP 401 / 403 / 429, or Cloudflare's "Just a moment…" check: `cf-mitigated: challenge`, `challenges.cloudflare.com`) or `error`. The last good copy of each feed is kept in `data/state/ics_feeds.json` (with `attempted`, `state`, `http_status`, `error`, and `fetched` = the last success) and used while the feed fails. `_parse_ics` reads The Events Calendar's export (VTIMEZONE + `DTSTART;TZID=America/Chicago`, `UID` `<post id>-<start>-<end>@neta65.org`, `URL` = the event page, `LOCATION` without ", United States", `ATTACH;FMTTYPE=image/…` = the flyer, `CATEGORIES` → tags; CANCELLED left out, RRULE expanded, an all-day `DTEND` is exclusive → last day). `category:` `neta65` (or `ics`) puts the events with the NETA 65 events; `gv-calendar` / `lv-calendar` with the GV/LV calendars. Health → `status.json` `feeds` → the "Other calendars we read" card on `/status/` and the informational block of the run summary. Feeds are not content sources: a blocked feed never counts as failed, never becomes a warning and never opens the "stopped updating" issue. |
| One event, several sources | `merge_feed_duplicates()` in `build_events`, against everything already on the calendar: content/events files, dated Drive flyers, the committee meeting and every `recurring_events:` date (so a feed that also lists the CityWide Dallas booth or the meeting never doubles them). Two events are the same only when they **start the same local day** and either (1) link the same event page — `event_url_key()` ignores the scheme, `www.`, the trailing slash, `?query` and `#fragment` (`neta65.org/event/<slug>`) — or (2) have the same shape (`_same_shape`: both all-day, or both timed and starting at most `TITLE_MATCH_MAX_GAP_H` = 2 hours apart; never one over several days against one on a single day), are not in two different cities, and have titles that name the same event (`similar_titles`: the telling words — the kind of event included: "workshop", "booth", "assembly" — shared / all ≥ 0.75, the shared city and the year ignored, `lv` / `gv` expanded, "grapevine", "la viña", "neta 65" ignored; word for word when a city is not known, e.g. a place "to be announced"). "LV Writing Workshop" ~ "La Viña Writing Workshop (in Spanish) — Fort Worth"; not ~ "LV Recording Workshop"; "Grapevine Workshop at the Spring Assembly" (7 PM on the assembly's Friday) is **not** the assembly. The same event page on another date is another date (a series, a page used again for a new workshop, or a date that changed): the feed event is kept. The hand-written event wins and keeps its own Spanish; the feed only fills what it leaves out — `flyer_url` / `flyer_thumb`, `online_url` and the event-page `url` only on a sure match (same page, or the same start); a missing place, or one "to be announced" (on a sure match: the feed's venue replaces it); a missing end of the same kind — recorded in `extra.also_in_feed` + `extra.feed_match` (`url` / `title`). Nothing is copied onto the meeting or a recurring date. What the feed says that a file does not (its event page on another date while the file is still upcoming, another start time, a venue the file calls "to be announced") → `feeds[].notes` → a *Check:* line and a `::notice` in the run summary, so the chair updates the file. The same event in two feeds is kept once. `feeds[].duplicates` counts them. Proven by `tests/test_events_feeds.py` with the six real workshop pages and the negative cases (a workshop / booth on an assembly's first day, with a known and with a TBA venue; the same page on another date; the booth and the meeting in a feed). |
| neta65.org is blocked | Since Sept 2026 every automated request to neta65.org (the iCal export, `webcal://…&ical=1`, `/wp-json/tribe/events/v1/events`) gets HTTP 403 "Just a moment…" from Cloudflare. The site does not try to get around it. The fix is on the Area's side: a Cloudflare WAF custom rule with the action **Skip** for requests whose query string contains `ical=1` (or whose User-Agent is the robot's); the next daily run then reads the feed by itself. Until then a NETA 65 workshop or assembly shows on the Events page only after the committee adds it to `content/events` by hand (the /status/ card says so and links content/events/README.md). |

## Crawl politeness

| Host | Rule we follow | Numbers |
|---|---|---|
| www.aagrapevine.org + www.aalavina.org | robots.txt obeyed; `Crawl-delay: 5` applied **across both hosts and all modules together** (one `shared_session()`); **each page at most once per run**: the session keeps every page it read for the rest of the run (`PoliteSession.get_text` / `remembered`), so what one module read — the home pages (quote, podcast discovery), `/BOTM` and `/libro-del-mes` (shop), `/grapevine-weekly-open`, the sitemap (external events) — is reused by the others and by the crawl; honest User-Agent with a contact URL; conditional GETs; skip login/cart/search/paywalled paths | 5 s between requests → 720 requests/hour max. Default 40 min/day ≈ 450 pages/day. **First coverage is complete** (Sept 2026): 3,445 pages known, 3,441 crawled, queue empty (the other 4 links return errors and are retried now and then), 130 PDFs. From now on the daily run only re-checks pages and picks up new ones — a 300-minute catch-up run is only needed after `crawl-state.json` is deleted. Pages are re-checked every `recheck_days` (21) unless the sitemap says they changed; hub pages daily. PDFs: ≤ `pdf_details_per_run` (40) downloads/run, ≤ `pdf_max_mb` (60 MB) each. |
| YouTube | Fixed set of feed URLs, ~1 s apart, short timeouts; yt-dlp time-boxed (6 min/run) | ~10–90 requests/day |
| Instagram | Public embed pages only (unless the official API token is set), ≤ a few requests per account per day, post-embed look-ups capped by `enrich_per_run`; no hammering on HTTP 429. Instagram's terms discourage automated collection — `anonymous: false` turns all of it off | ~2–30 requests/day |
| Google Drive | One request per folder per run (≤ 800 folders, 15 min budget) | tens of requests/day |
| Podcast feeds | One RSS request per show (2 shows); a few audio HEADs for vanished episodes | ~2–10 requests/day |
| Outside calendars (`sources.ics_feeds`, e.g. neta65.org's workshop calendar) | One plain GET per feed per run with the robot's own User-Agent (`sources.crawler.user_agent`), no retries, no robots.txt fetch (a published calendar file is meant for calendar programs); a feed is asked again only 20 hours later, whether it worked or not (`ICS_RETRY_HOURS_*` in `build_data.py`; the last good copy is used in between), so push-triggered and manual runs add nothing. **Never** get around a bot wall (no browser automation, proxies or faked headers) | ≤ 1 request/day per feed |
| Link check (weekly) | lychee: 2 concurrent / 1 s apart per host; config links via `PoliteSession` | a few hundred requests/week, none to the two magazine sites except ~20 config links at 5 s |
| The Morning check (`scripts/ops/morning_check.py`) | Asks a magazine only while its quote on **our** site is late: between 90 minutes before and 90 minutes after the goal (4:00–7:00 AM) one fresh request of its home page (`get_text(reuse=False)`) per late magazine every 10 minutes, and once per check after that, through the same shared polite session (robots.txt first, 5 s apart). Its own site's `build.json` is read with plain requests | usually 0 a day; at worst about 40 page requests over a morning when both quotes are very late (16 per magazine from the alarm at 4:30 to 7:00 AM, 18 for a check that begins at 4:00; one per late magazine for each later check), plus each site's robots.txt. Each morning refresh reads the two home pages itself — about 20 requests on the 1st and 15th, only in the first refresh of the day (shop, articles) |

## Failure handling (design guarantees)

1. **Nothing disappears on a bad day.** `merge_items()` keeps every known item; a module that fails
   writes `ok=false` + `error` and keeps its previous items. Items are only marked `gone` after an
   explicit confirmation (404/410, oEmbed, a successful folder listing without the file). A PDF needs
   **two** failing checks at least 24 hours apart (404/410, or an HTML page where the file was), so one
   bad answer during a site update never hides it; a gone PDF that a page still links is checked again
   after a week, then monthly, and returns when it answers. A PDF on another website whose server has
   not answered at all for 30+ days (after 4+ tries) is gone too; files on aagrapevine.org /
   aalavina.org are never retired just because the site is down.
2. **One broken source never stops the others** (`run_module()` catches everything and records it).
3. **Atomic writes**: `write_json()` writes a temp file then `os.replace()`, so a killed run never
   leaves half a JSON file (`*.tmp` and half-downloaded `*.part` thumbnails are git-ignored, so the
   data commit never picks them up).
4. **Partial progress is kept**: the commit step runs even when the sync step failed, hit its
   time budget or the run was cancelled, so e.g. 35 minutes of crawling are not lost.
5. **The site always deploys** the latest committed data, even if today's sync failed.
6. **A bad settings edit cannot take the site down**: the build fails, GitHub Pages keeps serving
   the previous deployment.
7. **Health is visible**: `/status/` page, the run summary table, `::warning` annotations, the badge —
   and a source that has not updated for 7 days opens the issue *"A content source has stopped
   updating"* (the `report` job), because a run stays green while only one source fails.
   GitHub's failure e-mails for the *scheduled* run go to the user who last enabled the workflow
   (or last edited its `cron:` line): after a hand-over, the new chair disables and re-enables it.
8. **The new day and the quote by the goal, or a red run**: the Morning check either sees today's
   update live on the site (its summary says since when), or ends with a yellow note (only a
   magazine's quote was late at the source — the note says when it was last asked — or the site had
   not shown a finished update yet), or goes red — so a morning that did not work never passes
   silently, even though the runs the bot starts e-mail nobody.

## Repository size

Measured per item (JSON, indented one field per line): ~1.1–1.8 KB in `data/raw`, a bit more in
`data/site` (translations added). Thumbnails: WebP ≤ 480 px, ~16–23 KB each. The first full PDF
crawl is done, so these are real numbers, not estimates:

| Part | Measured (Sept 2026) | Growth |
|---|---|---|
| `data/raw` + `data/site` (130 PDFs, 528 videos, 295 episodes, 224 magazine stories, Instagram, events) | ~5 MB (1.6 + 3.3 MB) | a few MB a year (mostly new stories, episodes and videos) |
| `data/state/crawl-state.json` (3,445 pages) | ~1.4 MB | only when the two sites add pages |
| `data/translations/cache.json` | ~0.7 MB | grows with new titles |
| `src/assets/cache/` thumbnails (`pdf` 129 · `ig` 26 · `articles` 22 · `pod` 3) | ~3.5 MB | ~20 KB per new thumbnail; Instagram's stay at most `keep_per_account` (130) per account — about 6 MB for the two, older ones are deleted |
| Git history growth (daily commits are small line-level changes, delta-compressed) | — | roughly 50–150 MB per year |

GitHub recommends repositories stay under 1 GB (hard warnings start around 5 GB); GitHub Pages
sites must stay under 1 GB (the deploy step warns at 900 MB). CI clones are shallow (depth 1), so
history size does not slow the daily run.

**If the repository ever gets too big** (years from now), squash the history. This rewrites history —
do it only if you understand it, with the scheduled workflow disabled:

```bash
git checkout --orphan fresh main          # same files, no history
git commit -m "Fresh start: history squashed on $(date +%F)"
git branch -M fresh main
git push --force origin main
```

## Running locally

Requirements: **Python 3.12+**, **Node 20+ (22 recommended)**, Git.

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
$env:PYTHONIOENCODING = "utf-8"          # Windows console + non-ASCII text
python -m scripts.sync.run_all --crawl-minutes 5
npm start                                 # http://localhost:8080 (live reload)
```

**macOS / Linux:**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm ci
python -m scripts.sync.run_all --crawl-minutes 5
npm start
```

Single modules and tools:

```bash
python -m scripts.sync.youtube --dry-run           # any module: fetch + print, write nothing
python -m scripts.sync.crawl --minutes 0           # rebuild pdfs.json from state, no network
python -m scripts.sync.translate "Dear Grapevine" --to es
python -m scripts.sync.translate --download        # fetch the models (~175 MB) once
python -m scripts.notify.send_digest --dry-run     # preview the e-mail in .tmp/
python -m scripts.ops.morning_check --check-only --site https://mkp715.github.io/AAGrapevine
                                                   # the Morning check's view of the live site: what it would
                                                   # do (no token needed; asks a magazine — one request each,
                                                   # plus robots.txt — only from 4:00 AM Central, and only
                                                   # when today's build is up with a quote that is late)
ONLY=library,search npx @11ty/eleventy             # build just some pages (fast)
```

Build exactly as GitHub Pages does for a project site:

```powershell
$env:PATH_PREFIX = "/AAGrapevine/"; npx @11ty/eleventy      # PowerShell
```
```bash
PATH_PREFIX=/AAGrapevine/ npx @11ty/eleventy                # macOS / Linux
MSYS_NO_PATHCONV=1 PATH_PREFIX=/AAGrapevine/ npx @11ty/eleventy   # Git Bash on Windows
```

(Git Bash rewrites values that look like paths — `/AAGrapevine/` becomes
`C:/Program Files/Git/AAGrapevine/` — unless `MSYS_NO_PATHCONV=1` is set.)

**Service worker (offline use).** The built site registers `/sw.js` (README → "Install the app,
offline use and Data saver"). It works on `http://localhost` too, and pages you open while testing are
kept in the browser. Styles and scripts are linked as `…?v=<build.version>` — a fingerprint of the code
(`src/_data/build.js`: `src/`, `eleventy/`, `config/`, `eleventy.config.js`, `package-lock.json`; not
`data/` or `src/assets/cache/`), which is also the worker's version. To start from a clean first visit:
DevTools → Application → Storage → **Clear site data**.

Please keep local test runs short (`--crawl-minutes 5`, `--dry-run`): the magazine sites ask for
5 seconds between requests and the daily job already visits them.

## Resetting state

| Goal | Do this |
|---|---|
| Redeploy without syncing much | Run *Update & Deploy* with **skip_crawl** ticked |
| Re-crawl the two sites from scratch | Delete `data/state/crawl-state.json` (commit), then run with `crawl_minutes = 300` |
| Re-read one source completely | Delete `data/raw/<source>.json` (loses `first_seen` dates → everything looks "new" for 14 days) |
| Re-translate one text | Add it to `data/translations/overrides.yml` (preferred) |
| Re-translate everything | Delete `data/translations/cache.json`, or bump `ENGINE_VERSION` in `translate.py` |
| Force a fresh model download | Delete the `translation-models-…` entry under **Actions → Caches** (the key changes by itself when `MODEL_URLS` in `translate.py` changes) |
| Undo a bad data commit | `git revert <sha>` (or GitHub → commit → *Revert*), then run the workflow |
| Roll the website back | **Actions** → an older successful run → *Re-run jobs* re-deploys what `main` has *now*; to publish old content, revert the commits first |

## Adding a new source

1. **Module:** create `scripts/sync/<name>.py` following an existing one (e.g. `podcasts.py`):
   `main(argv)` with argparse (`--dry-run`), build Items with `make_item()`, merge with
   `merge_items()`, write with `save_raw("<name>", …, ok=…, error=…, stats=…)`, and end with
   `if __name__ == "__main__": raise SystemExit(run_module("<name>", main))`.
   Use `shared_session()` for aagrapevine.org / aalavina.org; `PoliteSession()` elsewhere.
   Put any settings in `config/site.yml` under `sources:`.
2. **Contract:** add the source/kind/`extra` fields to [DATA_SCHEMA.md](DATA_SCHEMA.md).
3. **Pipeline:** register the module in `run_all.py` (decide whether it belongs in `--quick`), and
   map its raw file to a site file in `build_data.py` (plus a status label).
4. **Templates:** add the site file name to `FILES` in `src/_data/db.js`, then use
   `db.<file>.items` in a page; add UI strings to `src/_i18n/`.
5. **Test:** `python -m scripts.sync.<name> --dry-run`, then a real run, `npm start`, check `/status/`.
6. **Digest (optional):** in `scripts/notify/send_digest.py`, add its data file to `NEWS_SOURCES`, its group to
   `NEWS_GROUPS` and `COUNT_ORDER`, a list of its own to `MEDIA_GROUPS` and its `status.json` source to
   `FRESH_SOURCES` (so the e-mail waits for it). In `eleventy/filters/community.js`, add the same to
   `MONTH_SOURCES`, `MONTH_NEWS` and `COUNT_ORDER`, and a section to `src/pages/digest.njk` (`dgList`), so the
   e-mail and the `/digest/` page stay the same; `tests/test_digest_parity.py` compares them.

## Environment variables and secrets

| Name | Where | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | secret → sync | Drive API (exact dates/sizes); optional |
| `IG_ACCESS_TOKEN`, `IG_BUSINESS_ID` | secret → sync | Instagram Graph API; optional |
| `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `DIGEST_TO`, `DIGEST_FROM`, `DIGEST_REPLY_TO` | secrets → digest | Monthly e-mail; optional |
| `PATH_PREFIX` | build | URL folder of the site (`/AAGrapevine/` or `/`); set automatically from Pages |
| `SITE_URL` | build, digest | Public address (from Pages); overrides `site.url` where supported |
| `GV_MODELS_DIR` | sync | Translation model folder (default `.cache/models`; the workflow sets it to the same folder it caches) |
| `GV_MT_THREADS` | sync | CPU threads for translation (workflow: 4) |
| `GV_TRANSLATE_MINUTES` | sync (`build_data`) | Time budget for new translations (default 40; the workflow lowers it on very long crawls) |
| `GV_CRAWL_MINUTES` | sync (`run_all`) | Crawl time box when `--crawl-minutes` is not given |
| `IG_ANONYMOUS` | sync | `0` = same as `sources.instagram.anonymous: false` |
| `IG_GRAPH_VERSION` | sync | Graph API version (default from config, `v21.0`) |
| `GV_LOG_LEVEL` | sync | `DEBUG` for verbose logs |
| `ONLY` | build (local) | Build only some `src/pages/*` files |
| `I18N_STRICT` | build | Fail on missing UI strings (always on in `update.yml` and `check.yml`; unset locally = the raw key is shown instead) |
| `GH_TOKEN`, `GITHUB_REPOSITORY`, `SITE_URL`, `CHECK_ONLY`, `SCHEDULE` | Morning check (`morning_check.py`) | The built-in token (`actions: write`: start and follow Update & Deploy), the repository, the site's address (from Pages; else `site.url`), `check_only`, the cron string that started it. No secret: the morning alarm's key lives at cron-job.org (its `Authorization` header), never in the repository |
| `GITHUB_RUN_ID` | build | Written into `/build.json` → `run` (the Morning check waits until the live one names the run it started) |
