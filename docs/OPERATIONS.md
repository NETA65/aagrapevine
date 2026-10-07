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
- [When Grapevine announces new prices](#when-grapevine-announces-new-prices)
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
  the morning alarm (cron-job.org, 4:30 AM Central) ─────────────┐   POST …/actions/workflows/morning.yml/dispatches
  morning.yml's own schedule (hourly, 21–11 UTC) ────────────────┤
  Actions → Morning check (new day by 5:30 AM) → Run workflow ───┘
        │
        ▼  .github/workflows/morning.yml — Morning check (new day by 5:30 AM), one at a time
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
   • cron 07:17 UTC      │  │        [--crawl-minutes N | --quick [--also A,B] | --morning]  │  │
   • Run workflow        │  │                                                                │  │
   • push to main        │  │  articles.py ──┐  aagrapevine.org /magazine, aalavina.org      │  │
     (config/content/    │  │  crawl.py ─────┤  both sites, sitemap + pages → every PDF      │  │
      templates/code)    │  │  podcasts.py ──┤  feeds.captivate.fm RSS (2 shows: gv, wo)     │  │
   • cron 12:07 + 20:07  │  │  youtube.py ───┤  channel/playlist RSS + yt-dlp listing        │  │
     UTC (quick: the     │  │                │                                               │  │
      midday + evening   │  │                │                                               │  │
      refreshes)         │  │                │                                               │  │
                         │  │  instagram.py ─┤  Graph API w/ token, else public embed pages  │  │
                         │  │  drive.py ─────┤  public Drive folders (or Drive API w/ key)   │  │
                         │  │  editorial.py ─┤  /contribute, /temas-sugeridos, /recursos doc │  │
                         │  │  weekly_open.py┤  /grapevine-weekly-open                       │  │
                         │  │  announcements ┤  content/bulletin, content/events (repo)      │  │
                         │  │  writers_archive┘ content/archive (repo: the 2 archive CSVs)   │  │
                         │  │        │ each writes data/raw/<source>.json (cumulative)       │  │
                         │  │        ▼                                                       │  │
                         │  │  translate.py  EN⇄ES, offline CTranslate2 + Argos models      │  │
                         │  │        │       cache: data/translations/cache.json            │  │
                         │  │        ▼       (overrides.yml + glossary.yml win)             │  │
                         │  │  build_data.py → data/site/*.json (+ i18n, whatsnew, status)  │  │
                         │  └────────────────────────────────────────────────────────────────┘  │
                         │  git add -A data/{raw,site,state} cache.json src/assets/cache → push │
                         │                                                                       │
                         │  JOB 2  build-deploy "Build website" (runs even if JOB 1 failed)     │
                         │  checkout JOB 1's commit → npm ci → configure-pages → PATH_PREFIX/   │
                         │  SITE_URL → eleventy (src/ + data/site/*.json) → tailwind → _site/   │
                         │    (+ _site/build.json: this build's Central day and quote days)     │
                         │  → the posters' share pictures (Chrome) → upload-pages-artifact      │
                         │  JOB 3  tests "Test the code before publishing" (beside JOB 2, same  │
                         │  commit; a few seconds when this code passed already)                │
                         │  JOB 4  publish → deploy-pages, only when JOB 2 and JOB 3 succeeded  │
                         │  on the very same commit                                             │
                         │                                                                      │
                         │  JOB 5  report → one issue while a source has not updated for 7+     │
                         │  days, one while unattended runs keep failing; both close by         │
                         │  themselves                                                          │
                         └───────────────────────────────────────────────────────────────────────┘

   monthly-digest.yml (1st–3rd, 08:07 · 11:07 · 14:07 · 17:07 · 20:07 UTC, until sent) → scripts/notify/send_digest.py → SMTP
   link-check.yml     (Sundays) → build → lychee on _site + polite check of config links → one GitHub issue
   check.yml          (every pull request + every code/settings/workflow push to main) → strict eleventy build
                      (STRICT_BUILD) + checks (build.json included) + the browser checks in Chrome; offline
                      Python tests (all of them); digest dry-run
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
| `data/state/*.json` | Resumable state (`crawl-state.json`; `ics_feeds.json` = the last good copy + last answer of each outside calendar; `sources-seen.json` = `{commit, by, recorded}`, the last commit the `FULL_ONLY` sources ran with — see *Push to `main`*) | sync modules, `build_data.py`, `update.yml` (*Remember the commit the full-update sources ran with*) |
| `data/translations/cache.json` | Translation memory (one entry per line) | `translate.py` |
| `data/site/*.json` | What templates read | `build_data.py` only |
| `src/assets/cache/{pdf,ig,articles,pod}/` | Small WebP thumbnails (≤ 480 px): PDF covers, Instagram posts, story images, podcast covers; plus a 128 px JPEG copy of each magazine cover (`articles/<key>.jpg`) for the monthly e-mail — classic Outlook for Windows shows no WebP | sync modules |
| `src/` | Eleventy templates, CSS, JS, images | people |
| `scripts/sync/` | The sync pipeline | — |
| `scripts/notify/send_digest.py` | Monthly e-mail | — |
| `scripts/ops/morning_check.py` | The Morning check's guard (`morning.yml`): reads the live `/build.json`, starts and follows the morning refresh, asks a late magazine, starts the full update on the 1st / after a skipped day | — |
| `scripts/ops/push_modules.py` | Which `FULL_ONLY` sources a push also runs (`update.yml` → *Decide what to sync* → `run_all --also`): the files and the parts of `config/site.yml` they read; `--record` writes `data/state/sources-seen.json` | — |
| `scripts/ops/gate_tests.py` | The tests *Website update* runs before it publishes (job `tests`): every offline test of `tests/` but `DATA_TESTS` (the day's synced data), `CONTENT_TESTS` (the committee's files and the documentation) and `LIST_CHECKS` (`test_automation.GateLists`, the guard that keeps these lists complete); writes the *Tests before publishing* section of the run summary, naming the committee's files each failing test read (a Python audit hook on `open`) | — |
| `scripts/ops/poster_share.py` (+ `site_browser.py`, `serve_site.mjs`, `requirements-browser.txt`) | The monthly posters' share pictures (build job, after a build with `POSTER_SHARE=1`): each month page's poster top as a 1200 × 630 `share.png`, taken with the runner's Chrome through Playwright; `site_browser.py` starts the site server (`serve_site.mjs`, which serves a built folder the way GitHub Pages does; `--stop-with-parent`) and the browser for these and for the browser checks (`tests/browser`) | — |
| `content/archive/*.csv` | The owner's exports of the magazines' online archives (the Texas writers archive) | people |
| `src/pages/build-info.11ty.js` | `/build.json`: this build's Central day, the days of its two quotes and when the last full update ran (read by the Morning check) | — |
| `.github/workflows/` | Automation | — |
| `.cache/models/` | Translation models (~175 MB; `en_es/`, `es_en/`) — **not committed**, cached by Actions | `translate.py` |
| `.cache/booth-media/` | The booth display's offline copies of the Drive booth folder's photos, videos and sound files (`files/`, published at `/about/booth/media/`; at most `booth.max_total_mb`) + `manifest.json` — **not committed**, cached by Actions (build job) | `scripts/build/booth-media.mjs` |

## Workflows

### `update.yml` — Website update

| Aspect | Behaviour |
|---|---|
| Schedule | `17 7 * * *` (UTC) = 2:17 AM CDT / 1:17 AM CST on time: the **nightly full update** (it was `17 6 * * *` until October 2026: a run 4 hours late then started at 4:17 AM CST, on top of the 4:30 alarm; `test_the_nightly_full_update_keeps_clear_of_the_morning_alarm` checks that on time — a run of up to 2 hours — it ends before 4:30 AM Central and that 4, 5, 6 or 8 hours late it starts at least 30 minutes after it, on a CDT and a CST day). `7 12 * * *` = 7:07 AM CDT / 6:07 AM CST on time: the **midday refresh** (quick). `7 20 * * *` = 3:07 PM CDT / 2:07 PM CST on time: the **evening refresh** (quick). Minutes 17 and 7 avoid GitHub's top-of-hour congestion. **Observed (Sept 2026): GitHub starts these scheduled runs 4–8 hours late** (the old 10:17 cron started 14:33–18:11 UTC, the old 12:07 one 16:17–19:36; on 09-29 neither had started by 15:40 UTC), and a busy day can drop one — so each is set about 4 hours before the time it is meant for: with the usual delay the full update lands about 6–8 AM CDT (5–7 AM CST), the midday refresh about 11 AM–1 PM CDT (10 AM–noon CST), the evening refresh about 7–9 PM CDT (6–8 PM CST); the new day and the daily quote come from the Morning check's `morning` dispatch anyway ([below](#morningyml--morning-check-new-day-by-530-am)). (The midday refresh used to be `7 8 * * *`; it landed in the morning and left the rest of the day without a timed run, hence the move and the evening refresh.) *Decide what to sync* compares `github.event.schedule` with `FULL_CRON="17 7 * * *"`: that one → full; **every other schedule** (the two refreshes, and any `cron:` line added later) → quick, so a new line can never start a long crawl by mistake. The full string is also tested by the run-name; the evening string by the run-name and the commit step; the midday string only sits on its `cron:` line (and in a comment) (`tests/test_run_wiring.py` → `Schedule.test_the_strings_agree`, `tests/test_morning.py`, `tests/test_run_names.py`). |
| Manual run | Inputs `crawl_minutes` (default empty = the config value `sources.crawler.minutes_per_run`; whole minutes, capped at 300), `skip_crawl` (= quick run) and `morning` (the **morning refresh** — what the Morning check dispatches, `{"morning": "true"}`; it wins over the other two). |
| Run name | A folded (`>-`) `run-name:` expression gives each kind of run its title: `inputs.morning` → "Morning refresh: new day and daily quote" (the first branch — `MORNING_TITLE` in `scripts/ops/morning_check.py`, which finds its dispatched run by it when GitHub does not return the run id; whoever ticked `morning`); schedule `17 7 * * *` → "Nightly full update (GitHub schedule)"; schedule `7 20 * * *` → "Evening refresh (GitHub schedule)"; any other schedule → "Midday refresh (GitHub schedule)"; `workflow_dispatch` with `skip_crawl` → "Quick refresh (started by hand)"; by `github-actions[bot]` (the Morning check's full update) → "Full update (started by the Morning check)"; `crawl_minutes` `0` → "Full update without the document search (started by hand)"; any other dispatch → "Full update (started by hand)"; a push → `''`, so GitHub's own title (the commit message). Every branch after the first tests `github.event_name` before an input (a schedule's or a push's inputs are null, and GitHub's `null == '0'` is true). `morning_check.is_full_title` counts a run as a full update by these titles ("Full update…", "Nightly full update…"). `tests/test_run_names.py` evaluates the expression for every kind of run (a small evaluator of GitHub's `&&` / `\|\|` rules). The other workflows: morning.yml "Morning check (GitHub schedule)" / "(look only)" / "Morning check (started by <triggering actor>)"; monthly-digest.yml "Monthly e-mail digest (GitHub schedule)" / ": preview only" / ": SEND AGAIN (forced, started by hand)" / ": SEND NOW (started by hand)"; link-check.yml "Weekly link check (GitHub schedule)" / "(started by hand)"; check.yml "Code check (started by hand)" (a push or a pull request keeps GitHub's title). |
| Push to `main` | Uses a `paths` filter: everything **except** `data/**` (but *including* `data/geo/**` without its `README.md`, and `data/translations/overrides.yml` and `glossary.yml`), `src/assets/cache/**`, Markdown docs (but *including* `content/**` and `src/**`, not `content/**/README.md`), `docs/**`, `LICENSE`, `NOTICE`, other workflows. Since October 2026 `tests/**` (its `.md` files aside) starts a run too: the tests decide whether a run publishes (job `tests`), so a fix made only in `tests/` is tested and published at once. A push runs a **quick** sync and redeploys — plus, through `--also`, the `FULL_ONLY` sources whose own input the push changed: *Decide what to sync* runs `python -m scripts.ops.push_modules --output "$RUNNER_TEMP/push-also.txt"` for push events only, which takes the push's files from git: since October 2026 from the last commit the `FULL_ONLY` sources ran with — `data/state/sources-seen.json` (`{commit, by, recorded}`; env `GV_SOURCES_SEEN` / `--seen FILE` names another file, which tests use) — to the push's last commit, so a push whose run GitHub replaced in the queue still gets its sources run by the next push's run; without that file, or when git cannot fetch its commit (a rewritten history), from the commit the push started from, as GitHub's own `paths:` filter sees the push (a `::notice title=Push run::` "Could not compare this push with the last commit the sources only the full update reads ran with (data/state/sources-seen.json) — … —, so only its own changes count."): `git diff --name-only --no-renames -z <from> <after>` (`before` and `after` from `$GITHUB_EVENT_PATH`; `after` falls back to `$GITHUB_SHA`), each commit the checkout lacks fetched first, one commit deep (`git cat-file -e`, else `git fetch --depth=1 origin <commit>`, once each, `GIT_TERMINAL_PROMPT=0`) — the event file of a workflow run has no per-commit added / modified / removed lists (a webhook-style payload's lists are added when present). When git cannot say (`before` is a new branch's `000…0`, a fetch fails, git errors), the payload's lists are used alone, else nothing, with a `::notice title=Push run::`; the log line `Files this push changed: N (git diff <from>..<after>[, from the last commit the full-update sources ran with (data/state/sources-seen.json)]).` says where they came from. When `config/site.yml` is among the files, it is compared with its copy at that same `<from>` commit (`git show <from>:config/site.yml`). Output also `processed=<the push's last commit>` when git said what changed (the plan step's output `processed`); after a sync step that ended well, the step *Remember the commit the full-update sources ran with* runs `push_modules --record <processed> --by "push"` (a push) or `--record $(git rev-parse HEAD) --by "full update"` (a full update), and the data commit carries the file; quick, midday, evening and morning refreshes record nothing. `--repo` names the checkout to read (default: this one). `FILES`: `content/instagram.yml` → instagram, `data/geo/texas_places.json` → meetings. `SETTINGS` (as read in each module): youtube ← `sources.youtube`; instagram ← `sources.instagram`; editorial ← `sources.grapevine.base`, `.contribute`, `sources.lavina.base`, `.contribute`, `.themes_page`, `.rlv_resources`, `.themes_link`; weekly_open ← `sources.grapevine.base`, `.weekly_open`, `lavina_weekly_open`; audio_project ← `sources.grapevine.base`, `.audio_project`, `sources.lavina.base`, `.record_story`, `.record_instructions`, `.record_tips`, `.record_topics`, `.sample_audio`; meetings ← `meetings`, `spotlight.neta65_counties`; events_external ← `sources.grapevine.base`, `sources.lavina.base`. Never crawl, articles or shop. Output `also=` (run_all order) and `also_why=`; no earlier copy of `config/site.yml` (a new branch's `000…0`, a failed fetch) → nothing added for it and a `::notice title=Push run::`; any exception → nothing added; it never fails the step. `tests/test_push_modules.py` keeps `SETTINGS` equal to `run_all.FULL_ONLY` and checks every path exists in `config/site.yml` and in its module. |
| No loops | Bot commits (a) only touch excluded paths, (b) carry `[skip ci]`, and (c) are pushed with `GITHUB_TOKEN`, which never triggers workflows. |
| Concurrency | Group `update-deploy`, `cancel-in-progress: false`: a new run waits for the current one (GitHub keeps at most one pending run; a newer pending run replaces an older pending one). The sync job checks out `ref: ${{ github.ref }}` — the branch **tip** when the job starts, not the commit that queued the run (`github.sha`) — so a run that waited starts from the data the previous run just pushed instead of re-crawling from older state. |
| Sync command | Step *Sync sources and translate*. Schedule `17 7 * * *` (`FULL_CRON`): `python -m scripts.sync.run_all --crawl-minutes <sources.crawler.minutes_per_run>` (config; missing → 40; **`0` = no crawl**, the other sources still run; a full run that leaves the crawl out because the config says 0 — `run_all.crawl_paused`, read like the plan step — counts as the search's try: `_note_paused_crawl` writes a fresh `attempted` into `data/raw/pdfs.json`, and with it this run's own values — `changes` `{added: 0, removed: 0, held: <the kept count of a hold still in force>}` and `hub_problems: []` —, so the run summary, which takes a source's values as this run's when its `attempted` is not older than the run's start, shows no document counts, no magazine-page list and no *Document search* warning for a paused run; nothing else moves (not `updated`, items, stats or `held`; not when that file says `ok: false` or cannot be read; never in a quick or morning run, nor in a 0-minute run by hand while the config is not 0), and the crawl row says "paused (sources.crawler.minutes_per_run: 0)"). Manual: `--crawl-minutes <input>` (empty → config value). Push, `skip_crawl` or any other schedule (`7 12 * * *`, `7 20 * * *`): `--quick` = only `drive`, `announcements`, `podcasts`, `writers_archive`, `quote` (`QUICK_MODULES` in `run_all.py`, podcasts with `--no-discover`; `writers_archive` reads only `content/archive`; `quote` = 2 page requests to the magazine sites) + translation + `build_data`; for a push also `--also <the plan's list>` (those `FULL_ONLY` modules run with their `QUICK_ARGS`, in `MODULES` order; `--also` is ignored without `--quick` and never runs the crawl); YouTube, Instagram, articles, editorial, Weekly Open, shop (Book of the Month and prices), audio_project (the story lines), meetings, external events and the crawl otherwise wait for the next nightly run. Every quick or morning run passes `build_data --keep-full-update` (`kept_full_update`: `status.json` `full_update` keeps the last build's value — an `--also` run's fresh `attempted` must not look like a full update to the Morning check; a first build or an unreadable file → the computed value). The run table is titled by mode: "Full update", "Quick refresh" or "Morning refresh" (`run_title`). `morning`: `--morning` = the `--quick` sources with their quick flags — the daily quote read right after the bulletin — plus, by the Central day of the month, `MORNING_EXTRA` (`{1: ("shop", "articles"), 15: ("shop",)}`: the Book of the Month changes on the 15th, the month and its issues on the 1st; articles = hub pages only, `--no-details --no-archive`) after the quote, and only when their raw file was not read (or tried) yet that day — the Morning check may start up to three refreshes a morning — and the time boxes `MORNING_ARGS` (`drive --max-minutes 5`); the run table is titled "Morning refresh". `run_source` drops a flag a module does not have, with its value. `run_all` exits non-zero only if `build_data` fails. |
| Sync env | Secrets `GOOGLE_API_KEY`, `IG_ACCESS_TOKEN`, `IG_BUSINESS_ID`, `TSML_KEY_AADALLAS`, `TSML_KEY_FORTWORTHAA` (empty when unset = harmless); `GV_MT_THREADS=4` (runner vCPUs); `GV_TRANSLATE_MINUTES` (see Timeouts); `GV_MODELS_DIR=$GITHUB_WORKSPACE/.cache/models`; `PYTHONIOENCODING=utf-8`. |
| Timeouts | Job 360 min (GitHub's maximum). The *Decide what to sync* step computes: translation budget `T = clamp(345 − crawl − 35, 10, 40)` min and sync-step timeout `min(crawl + 30 + T + 20, 345)` — e.g. 130 min for a 40-min crawl, 345 for 300 (then T = 10). **Morning mode: T = 5, step timeout 20** (the bulletin's texts are translated first; the rest waits for the daily run), so a morning refresh is published in a few minutes even on a busy day. Setup takes ~5 min, so the step limit leaves ~10 min for the data commit even when the sync overruns (a step timeout is a failure, not a cancellation, so the commit and deploy still run). Build job: 40 min since October 2026, 35 before (the booth display's media: at most 20 to download, 5 to save; the posters' share pictures at most 5 — the build, a second build when the pictures could not be made, and the upload still fit). |
| Model cache | `actions/cache/restore` + `actions/cache/save`, path `.cache/models` (= `GV_MODELS_DIR`), key `translation-models-v1-<OS>-urls-<sha256 of MODEL_URLS in translate.py>` — computed from the source with `ast`, so only a change of the model URLs forces a new ~175 MB download; any other edit of `translate.py` keeps the cache. Saved only after a fresh download and only when both `<pair>/model/model.bin` (> 1 MB) and `<pair>/sentencepiece.model` exist (same test as `model_ready()`), so a failed download is never cached. On a cache miss (a new or moved repository, a cleared cache) the step "Download the translation models" fetches both before the sync (`python -m scripts.sync.translate --download`), so any run saves them. If fewer than 2 models are present after a successful sync step, the check step raises a `::warning` "Translation models missing" (the only download source is argos-net.com; translation then keeps new titles in their original language). Daily restores keep it from being evicted (7-day rule). Also: pip cache (setup-python), npm cache (setup-node). |
| Booth media cache | Job `build-deploy`, path `.cache/booth-media` (the booth display's offline copies of the Drive booth folder's files, `scripts/build/booth-media.mjs`): first *Work out the booth display's settings fingerprint*: a sha256 (Node.js + `js-yaml`) of `data/site/booth.json` and of the `booth:` section of `config/site.yml` only (keys sorted) — an unrelated edit of the settings file no longer saves the whole folder again under a new key; a `config/site.yml` that is not readable YAML is fingerprinted whole, and both files whole (`sha256sum`) if Node.js fails, so the step never stops a deploy. Then `actions/cache/restore` with key `booth-media-v1-<fingerprint>` and restore-keys that key + `-`, then `booth-media-v1-` (the newest copy for this booth.json and booth settings, else the newest of any) → the download step → *Work out the booth display's media cache key*: `booth-media-v1-<fingerprint>-<16 hex of the sha256 of the saved files' names and sizes>` (none for an empty folder) → `actions/cache/save` only when that key is not the one restored (`continue-on-error`, 5 min), before the build, so a failed build keeps the downloads. Not the all-in-one `actions/cache`, which saves only when its key was not an exact hit: with one key per booth.json, only the first run of each booth.json would ever be saved, and every later run would download again what that run could not save. |
| Commit | `git add -A -- data/raw data/site data/state data/translations/cache.json src/assets/cache` (added, changed **and deleted** files; human-edited files such as `overrides.yml`, `glossary.yml`, `content/`, `config/` are never committed by the bot; `*.tmp` / `*.part` leftovers of a stopped run are git-ignored). Commit only if something changed; message `chore(data): <what> YYYY-MM-DD [skip ci]` (Central date), `<what>` by the run: a push → `content sync after settings/content change`, the morning refresh (`MODE=morning`, whatever started it) → `morning refresh` followed by the quotes it brings, by the quotes' own day (each magazine whose quote in `data/site/quote.json` has another date than in `git show HEAD:data/site/quote.json`: ` with the daily quotes of Oct 6` when both are new and the same day, else ` with the Grapevine quote of Oct 6 and the La Viña quote of Oct 5`, nothing when no quote is new), the `7 20 * * *` schedule → `evening refresh`, any other quick schedule → `midday refresh`, a quick run by hand (`skip_crawl`) → `quick refresh`, anything else (the full update) → `daily content sync`; when `data/raw/writers_archive.json` has `stats.changed: true` and a file whose `imported_at` is not older than the plan step's `started` output (the time this run began to sync, `date -u`; i.e. THIS run took a new archive file in — whatever `ok` says, so one magazine's new file counts while the other's is turned down, and a crash of the source, which keeps the last run's stats, or a run stopped before it never repeats the last announcement), ` + writers archive` comes before the date (`… content sync after settings/content change + writers archive 2026-11-05 [skip ci]`). Push with up to 5 retries, `git pull --rebase --autostash -X theirs` between attempts (the bot's fresh generated files win a conflict; human edits to other files are kept). Runs even if the sync step failed, timed out **or the run was cancelled** (`always()`; GitHub gives `always()` steps about 5 minutes after a cancel, and the crawler saves its state on SIGTERM), so a cancelled 300-minute crawl keeps its progress. Deploy still skips cancelled runs. Simulated locally (shallow clone, concurrent human push, conflict in a generated file). **Token scope:** the sync job checks out with `persist-credentials: false`, so the write-access `GITHUB_TOKEN` is *not* in `.git/config` while `pip install` (floating versions) and the sync modules run; this step alone sets `http.https://github.com/.extraheader` from `GH_TOKEN` (covers `push` and `pull --rebase`) and unsets it on exit (`trap … EXIT`). |
| Summary | `run_all` writes a per-module table (titled "Full update", "Quick refresh" or "Morning refresh"); a second step (`always()`) writes a per-source table from `data/site/status.json` (skipped while it is fixture data), turns each failing source into a yellow `::warning` (with the days since its last success), marks a source that still works but that no run has **attempted** for `UNCHECKED_DAYS` = 3 days **NOT CHECKED** ("not checked for N days", a `::warning`; into `health` from `STALE_DAYS` = 7, with `unchecked` so the issue gives its own advice; never the PDF search while `sources.crawler.minutes_per_run` is 0 — the plan step's `daily_minutes` output —, nor right after the pause, since each full update during it moves the search's `attempted` (*Sync command*); never a source without an `attempted`), then (since October 2026) **Sync health** — a table *Source · Added · Removed · Held back* from `status.json` `sources[].changes` (counted only when the source's `attempted` is not older than the plan step's `started`; "—" otherwise) and `sources[].held` (shown while the hold lasts, whichever run made it: `drop: true` "**N held back** since … (found F of P): they stay on the site until the next run finds the same — e.g. …", `drop: false` "**N kept** … removed only when the next run confirms they are gone", `changes.confirmed` "removal confirmed (held back since …)"; each hold also a `::warning title=<source>: items held back::` whose title is escaped, as GitHub cuts a title at a comma or a colon; only rows with something to say) — and **Main pages of the magazine sites that did not load** (`data/raw/pdfs.json` `hub_problems`, only when that file's `attempted` is not older than `started` and `ok` is true — a crashed crawl keeps the last run's list —, plus a `::warning title=Document search::`; the same line is then left out of **Notes**), adds **Also run for this push** (the plan's `also_why`), the **Writers archive** block (`status.json` `writers_archive`: each magazine's file, rows, Texas rows, the stories on the site and the Area 65 ones; the source's `stats.notes` — "New archive file used: …", also a `::notice` — only when `stats.changed` and a file's `imported_at` is not older than the plan step's `started` (the same rule as the commit message: not `ok`); a **CSV file to fix** line "(the older rows stay on the site)" when the source failed; its `stats.warnings`, which are left out of **Notes**), **Reminders** (`status.json` `reminders`, one `::notice`), warns "Translation is not working" when texts are pending but none were translated, lists **Notes** (up to 2 `stats.warnings` per source that still updated, e.g. one YouTube feed answering 404; not the writers archive's, the bulletin's or the events' — `announcements` and `manual_events` repeat their `stats.errors` there, which come under *… files to fix*), **Settings problems** (`status.json` → `problems.meeting` / `problems.recurring_events` / `problems.ics_feeds` / `problems.price_changes` / `problems.content_events` / `problems.translations` — a glossary.yml / overrides.yml that could not be read: the cache is kept and nothing new is translated until it is fixed: a settings entry build_data skipped or corrected — e.g. a `meeting: skip_dates` value that is not a meeting day — also a yellow `::warning`), **Translation problems** (since October 2026 a heading of its own, cut out of `problems.translations`' line: `status.json` `translations.problems` — a translation memory that could not be read and was moved aside (`cache.json.bad-<UTC time>`), or a model that could not be installed: a failed download, which the next run simply tries again, or a checksum (`MODEL_SHA256`) that does not match, which needs a person; each a `::warning title=Translation problem::`), **Other calendars (optional, informational)** (`status.json` → `feeds`: each `sources.ics_feeds` entry's state, HTTP status, events and duplicates, and its `notes` as *Check:* lines — each also a `::notice`; a feed that a site's bot protection blocks is only a `::notice`, and feeds are **never** part of `health`, so they never open the "stopped updating" issue) and **New podcast feeds found** (`stats.discovered_feeds` of the podcasts source, plus a `::notice`); the **Daily quote** line (the day of each quote in `data/site/quote.json` after this run: "Grapevine Sep 29 · La Viña Sep 29"), **Bulletin files to fix** / **Event files to fix** (`stats.errors` of `announcements` / `manual_events`, at most 10 each, each also a `::warning`: a file that could not be read, or that links a file not saved next to it — the rest still updated) and **Scheduled bulletin posts** (`status.json` → `scheduled`: "2027-02-01 — Title (content/bulletin/x.md)" or "(Google Drive: name)", plus one `::notice`); and passes the sources that are `ok: false` with no success for **7+ days** (or never) to the `report` job as the job output `health` (one line of JSON). |
| Report | Job `report` — "Report sources that stopped updating, and updates that keep failing" (needs `sync`, `tests`, `build-deploy` and `publish`, `!cancelled()`, only on `main`, `permissions: issues: write, actions: read`, no checkout). Step 1 keeps **one** issue *"A content source has stopped updating"* — opened when the first source crosses 7 days (GitHub e-mails the repository's watchers), with advice per source (`HINTS`: `drive`, `instagram`, `writers_archive`; `UNCHECKED` for a source not checked; else the generic line), body silently edited after every run, a comment only when a *new* source joins (hidden marker `<!-- failing-sources: … -->`), closed automatically when all recover. Error texts are put in code spans so `@handles` in them never notify GitHub users. Step 2 (since October 2026) keeps **one** issue *"The website update keeps failing"*: it reads each job's result (`failure`, or `cancelled` — a job that hit its `timeout-minutes` is reported so here), and compares with the previous Website update run that completed (`gh api …/workflows/update.yml/runs?status=completed`, skipping this run and runs `cancelled` / `skipped` / `neutral`; `timed_out` and `startup_failure` count as failed): a run started by the schedule or by `github-actions[bot]` (the Morning check) that fails right after a failed run opens it (advice per job: `HINTS` `sync`, `tests`, `build`, `publish`); later failures edit its body silently (hidden markers `<!-- failing-jobs: … --> <!-- failures: N -->`) and comment only when a new job fails ("Now also failing: …"); a run where every job succeeded closes it ("The website update works again: this run published the site (…). Closing automatically."); a run a person started never opens it. Both steps `continue-on-error`: never fail the run (e.g. Issues disabled). Tested by `tests/test_automation.py` → `FailingUpdates`. |
| Tests | Job `tests` — "Test the code before publishing" (since October 2026; needs `sync`, `!cancelled()`, only on `main`, `contents: read`, 20 min): checks out `needs.sync.outputs.commit`, the very commit the build job builds; step *Fingerprint the code* fingerprints every file in git but the bot's, the committee's and the documentation (`git ls-files -s -z -- . ':!data/raw' ':!data/site' ':!data/state' ':!data/translations/cache.json' ':!src/assets/cache' ':!content' ':!config' ':!data/translations/glossary.yml' ':!data/translations/overrides.yml' ':(exclude,glob)*.md' ':!docs' ':!how-to' \| sha256sum`; the log line `Code fingerprint: …`; `data/geo`, `tests/` with its fixtures, the workflows, `NOTICE`, `LICENSE` and the Markdown pages in `src/` stay in); `actions/cache/restore` of `.cache/tests-passed` with key `tests-passed-v1-<fingerprint>` — a real restore of its one small file, not `lookup-only` (removed in October 2026: reading the pass back counts as using it, so the daily runs keep the entry alive and the tests do not run again unattended after GitHub's 7-day eviction on unchanged code): a hit → "The tests passed already for this code (content, settings and the bot's data may have changed since) — not run again." in seconds, and the log line `The pass: <UTC time> run <run id> commit <sha>` (the file's content); a miss → Python 3.12 + `requirements.txt`, Node 22 + `npm ci` (for the tests that run the site's JavaScript), `python -m scripts.ops.gate_tests` (every test of `tests/` but `DATA_TESTS`, `CONTENT_TESTS` and `LIST_CHECKS` — 80 of them on 6 October 2026; no translation models, so those tests skip), then `passed.txt` (`<UTC time> run <run id> commit <sha>`) is saved under that key (`continue-on-error`). `gate_tests` prints "Running N tests (M left to the Code check: they judge the day's data, the committee's own files or the documentation)." and writes "### Tests before publishing" to the run summary ("All N tests passed (M skipped) — the website may be published." and "Left to the Code check (they judge the day's synced data, the committee's own files or the documentation, not the code): N." / "**N of M tests failed — the website was NOT published** (the live site keeps the version before). The failing tests (the job's log says why):" with each failing test — " — it read the committee's files: …" when a Python audit hook (`sys.addaudithook`, events `open`, `os.listdir`, `os.scandir`) saw it, its class's set-up or its module read one of `COMMITTEE_FILES`; the site's JavaScript run in Node is not seen — and one of two lines of advice, "None of them was seen reading the committee's own files …" or "K of them read the committee's own files or the documentation …" / "**No tests were found — the website was NOT published** …") and `::error title=Tests failed — not published::` when it fails (exit 1; no test found is no pass). The daily data runs and every commit of content, settings, translation fixes or documentation leave the fingerprint as it is and skip the tests; a commit of code — scripts, templates, texts, tests, a workflow, `data/geo` — makes its run test. So no test the gate runs may judge the day's synced data (`DATA_TESTS`) or what the committee edits and the documentation (`CONTENT_TESTS`): such a test would fail only on the next unrelated change of the code and keep every run from publishing until that file was fixed; the Code check runs them and goes red on the push that made the slip. `test_automation.GateLists.test_no_gated_test_judges_the_committees_files` (a `LIST_CHECKS` entry: the Code check only, a few minutes) keeps the lists complete: it copies the repository (the files git knows, `node_modules` linked) into min(6, CPUs) copies, makes `tests/committee_edits.py`'s committee-like edits and slips in each and deletes the documentation, runs every gated test again there, and re-checks a failure in the repository itself (a test that fails there too is not blamed on the edits). Tested by `tests/test_automation.py` (`Publishing`, `GateTests`, `GateLists`). |
| Build | Job `build-deploy` — "Build website" (named "Build & publish website" until October 2026, when publishing moved to its own job): needs `sync`; runs when sync succeeded, **failed or timed out** (`!cancelled()`: not when a person cancels the run) and only on `main`, so the site always rebuilds the last good committed data. Checks out the sync job's output `commit` (the data commit it pushed, or the commit it checked out — the very commit the tests job tests; `main` when it names none) → names it (output `commit`) → `npm ci` → `actions/configure-pages` → `PATH_PREFIX` = `base_path` with exactly one leading and trailing slash (`/aagrapevine/` for a project site, `/` for a custom domain or a `user.github.io` repo) and `SITE_URL` = `base_url` without trailing slash → `I18N_STRICT=1 POSTER_SHARE=1 BUILD_WARNINGS=$RUNNER_TEMP/build-warnings.txt npx @11ty/eleventy` (Tailwind runs inside the build; a UI string missing from `src/_i18n/` fails the build, so Pages keeps the previous site instead of showing a raw key such as `home.spotlight.title`; `POSTER_SHARE` makes each `/monthly/YYYY-MM/` page name its own `share.png` as its preview picture; `BUILD_WARNINGS` collects the build's warnings, `eleventy/build-warnings.js` — no `STRICT_BUILD`, so a warning never stops publishing) → since October 2026 *Set up Python (for the posters' share pictures)* and *Make the monthly posters' share pictures* (both `continue-on-error`, the second 5 min: `pip install -r scripts/ops/requirements-browser.txt`, then `python -m scripts.ops.poster_share _site`, about a minute) → *Build the website again without the share pictures (only when they could not be made)* (`success() && steps.posters.outcome != 'success'`: deletes `*/monthly/*/share.png`, builds without `POSTER_SHARE`, `::warning title=Share pictures::`). A sanity step (*Check the build*) fails the deploy if `index.html`, `es/index.html` or any stylesheet at the top of `src/assets/css` (`main.css` and the area sheets booth, expenses, monthly, orientation, presentations, report) is missing from `_site/assets/css/` ("The stylesheet X was not built."), warns above 900 MB, warns (never blocks) when `build.json` is missing — the Morning check could not see that build (`check.yml` fails on it instead) —, and prints the build's warnings and adds **Build warnings (N)** (the first 50) to the run summary, still passing. Then `upload-pages-artifact`; publishing is the next job. |
| Publish | Job `publish` — "Publish to GitHub Pages" (needs `build-deploy` and `tests`; only when both succeeded, `!cancelled()`, on `main`; `pages: write`, `id-token: write`, environment `github-pages`): first *The tests passed on the commit that was built* — `::error title=Not published::The website was built from <sha> but the tests ran on <sha> (a change arrived between the two) — nothing was published; the next run publishes.` when the two jobs' `commit` outputs differ —, then `actions/deploy-pages`. A failing test or build therefore never goes live: Pages keeps the previous deployment. |
| Permissions | Workflow default `contents: read`; `sync` gets `contents: write`; `build-deploy` gets `pages: read` (the Pages settings); `tests` `contents: read`; `publish` gets `pages: write` + `id-token: write`; `report` gets `issues: write` + `actions: read`. These job-level `permissions` work with the repository's default read-only *Workflow permissions* setting — it does not need to be changed. Every `actions/checkout` in every workflow uses `persist-credentials: false` (zizmor's `artipacked` audit is clean); only the data-commit step logs in, see *Commit*. |
| Pinned actions | `actions/checkout@v7`, `setup-python@v7`, `setup-node@v7`, `cache@v6` (restore/save), `configure-pages@v6`, `upload-pages-artifact@v5`, `deploy-pages@v5` (Dependabot keeps them current). The one action from outside GitHub, lychee's (`link-check.yml`), is pinned to a full commit SHA with its `# vX.Y.Z` note; `tests/test_automation.py` → `Pinned` checks that every non-`actions/*` `uses:` is. |
| Linting | `actionlint` (with shellcheck) passes on all five workflows: `pip install actionlint-py shellcheck-py`, then `actionlint -shellcheck <path to shellcheck> .github/workflows/*.yml`. (On Windows, actionlint's own shellcheck call can hang on `update.yml`, also before these changes: there, lint with `-shellcheck=` and run shellcheck on each step's script — fed with LF line ends — instead.) |

> **60-day rule.** GitHub disables scheduled workflows in public repos after 60 days without
> repository activity. The daily data commits are activity (the envelope timestamps change every
> run; the morning refresh commits every day too, the quote changes), so this does not happen while
> the jobs work. If the job had been failing for two months, re-enable it under
> **Actions → Website update → Enable workflow**. (Never add an API "enable workflow" keepalive: GitHub
> then sends the failure e-mails to whoever re-enabled it — the bot.)

### `morning.yml` — Morning check (new day by 5:30 AM)

Puts the new day and both daily quotes on the site by the goal — `site.morning_goal` in
`config/site.yml`, default 05:30 Central — every day, although GitHub starts scheduled runs hours late
(see *Schedule* above): a run started through the API (`workflow_dispatch`) starts within seconds, and a
morning refresh is live about 3 minutes later.

| Aspect | Behaviour |
|---|---|
| Triggers | **The morning alarm** (recommended): an outside scheduler — cron-job.org, set up by the chair ([README → 10 d](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)) — sends `POST /repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches` with the body `{"ref":"main"}` at **4:30 AM America/Chicago**, with a fine-grained personal access token that has only *Actions: Read and write* on this repository (it lives at cron-job.org, never in the repository; it expires after a year and is renewed by the chair). Whoever holds it can do what this repository's Actions tab can — start, re-run, cancel and delete runs, clear caches, switch workflows on or off — but not change files or secrets; that is still enough to, for example, send the monthly e-mail to every district again (a manual send with **force** skips the marker guard) or start 300-minute crawls; if it leaks, README 10 d says what to do. It must be made by the repository's owner (a fine-grained key only reaches its resource owner's repositories): a move to another owner needs a new key and URL. **Backstop:** `schedule: "25 0-11,21-23 * * *"` — plain UTC (no `timezone:` key), 25 past every hour from 21:25 to 11:25 UTC = 4:25 PM–6:25 AM CDT / 3:25 PM–5:25 AM CST, never on the hour. GitHub starts this repository's schedules 4–6 (sometimes 8) hours late, so it begins 4 hours before the early-morning window: an evening firing that is delayed lands in the window, while one that runs on time finds today's build already live and is a 5-second no-op. It still ends at 11:25 UTC, so a day on which GitHub is on time is covered too. **By hand:** Actions → Morning check (new day by 5:30 AM) → Run workflow; input `check_only` (look and say, start nothing). |
| Concurrency | Group `morning-check`, `cancel-in-progress: false`: one check at a time; a second one waits and then finds the work done (a third replaces the waiting one). |
| Job `look` | "Is today's update already on the site?" — 5 minutes, `permissions: pages: read`, no checkout: the site's address from `gh api repos/:repo/pages` (a custom domain included), then `curl -fsS --max-time 20 --retry 2 <site>/build.json?check=<epoch>` (the query keeps GitHub Pages' 10-minute cache from answering with an older copy) and `jq`: **done** when `day`, `quotes.gv` and `quotes.lv` are all today in Central time — the same test as `is_done()` in `scripts/ops/morning_check.py` (a unit test runs both on the same files); **full** (the reason, or empty) when the full daily update is due — `build.json` `full` before midnight on the 1st of the month (Central) or more than 30 hours ago, the same rule as `full_run_reason()` (a unit test runs both at fixed moments, across daylight saving). Done and nothing due → one summary line ("Nothing to do: today's update (built 4:34 AM CDT, with today's Grapevine and La Viña quotes) is on the site."), and the next job is skipped. |
| Job `update` | "Put today's update on the site" (the name `UPDATE_JOB` and the tidy job rely on) — when `look` did not say done (also when `look` itself failed: the script reads the live site again), or said the full update is due; 240 minutes; `permissions: actions: write, contents: read`; checkout without credentials, Python 3.12 with a pip cache of its own (`cache-dependency-path` also names `morning.yml`, so it never stands in for the full cache the other workflows share), only the five packages it imports (`requests`, `beautifulsoup4`, `lxml`, `protego`, `PyYAML`, at the versions `requirements.txt` allows — a problem with the update's translation or PDF tools never stops the morning), then `python -m scripts.ops.morning_check [--check-only]` with `GH_TOKEN` (the built-in token), `SITE_URL` (from `look`), `CHECK_ONLY`, `SCHEDULE`. A check that started, followed and asked nothing writes `idle=true`: the step "Nothing to do (deleted a day later)" then runs, and `tidy` finds the run by it. |
| What the guard does | 1. Reads the live `build.json`; done → a summary, and step 5. 2. A Website update run **waiting** in the queue → it follows that one and never dispatches (in the `update-deploy` group a new run would replace the waiting one). A Website update run already **running** when the guard is about to dispatch (steps 3 and 4), or while a run waits behind it — the full daily update (on the 1st an earlier check's step 5 starts it), a push's, a person's long crawl — is followed first, for as long as the check may still act (up to 170 minutes, `GUARD_MAX`): the group runs one at a time and `cancel-in-progress` is off, so a refresh dispatched now would only wait behind it — for a full update or a crawl longer than the 45 minutes a followed run has — and every mode reads the daily quotes and builds the new day. Once it has ended the guard reads the site and the queue and decides again: a refresh only for what that run did not bring (a quote the magazine's page already showed is not asked again; its look at the pages counts from when it started); a run that failed is noted (*Waited for*) and the guard goes on with its own refresh. Still running at 170 minutes → a red ✗ when today's build is not on the site, a yellow note when only a quote is missing. 3. The live build is not today's (or cannot be read) → `workflow_dispatch` of `update.yml` with `{"morning": "true"}` and `return_run_details: true` (the 2026 API answers with the run id; a 204 or a refusal of that field — then sent again without it — is followed by a look at the newest `workflow_dispatch` runs named "Morning refresh: new day and daily quote"); it follows the run every 20 s for up to 45 minutes (a run that GitHub cancelled because a newer one took its place is followed to that one, up to 3 times), then reads `build.json` every 15 s for up to 5 minutes until it shows that run's build (its run id, or a build made after the run was created); a finished run the site does not show is "Cannot confirm" — never a reason for another run. 4. Today's build is up but a magazine's quote is not today's: from 3 h 30 min before the goal (`WINDOW_BEFORE`; the magazines usually publish the new quote about 2 AM Central) to 90 minutes after (2:00–7:00 AM; 4:00–7:00 until October 2026) it asks **only that magazine's** home page, every 10 minutes (`quote.peek`: the date read from the quote's heading; nothing is written), and starts the morning refresh again once the quote is out — never a question sooner than 10 minutes after a run it started or followed read the pages. Before the window it stops (a later check asks). A check that begins after the window (a late schedule, or Run workflow) asks once, and brings the quote if it is out; otherwise — and at the end of the window — a yellow note that says when the magazine was last asked. In steps 3 and 4 together a check starts at most 3 morning refreshes (`MAX_RUNS`; each reads both magazines' home pages), never two in a row without 10 minutes between them, and nothing — no refresh, no question — after 170 minutes (`GUARD_MAX`), so its last refresh still ends inside the job's 240 minutes; today's build still not there after that is a red ✗. "Today" is the Central day of each moment: a check still running at midnight (a late evening firing, a run that waited in the queue) works for the new day from then on — the new day's build is today's, and a late quote right after midnight is too early to ask (the morning's checks ask); its summary is about the new day, with a *Began* row. 5. Once today's update is on the site — also when it already was, or a waiting run or another update brought it — on the 1st of the month (Central) when no full update has run since midnight, and whenever no full update has run for 30 hours (GitHub skipped or failed one), it dispatches `update.yml` with no inputs — the full daily update — without following it; never while a Website update run waits in the queue or runs (any but a morning refresh: it may be a full one), and not again within 12 hours of a full update started by Run workflow after the last full update (`FULL_RETRY_AFTER`; "a full update" = a `workflow_dispatch` run whose title starts with "Full update" or "Nightly full update" — `is_full_title`, `FULL_TITLES`; a quick, midday, evening or morning refresh never counts: a full update that fails is tried again the next morning, not at every hourly check). "The last full update" is the live `build.json` `full` = `status.json` `full_update`: the newest `attempted` of the sources only the full run reads (`run_all.FULL_ONLY`: YouTube, Instagram, editorial, Weekly Open, audio_project, meetings, external events) — no state file of its own; this checkout's `status.json` only when the live site cannot say. |
| Run summary | "## Morning check — Tuesday, September 29 (Central time)", then "✅ Today's update is on the site since **4:34 AM CDT** — goal 5:30 AM." (a check that saw it arrive) or "✅ Today's update is on the site — the latest build is from **1:00 PM CDT**." (it was already there: that build may be a later one, so nothing is said about the goal) and a table: the new day (built at), each quote's day, the Website update run (link, duration), what started the check, the full daily update (started, why). Annotations: `::warning title=After the goal::` (a check saw it go live after the goal), `::warning title=A daily quote is late at the source::` (not out when last asked — the note gives that time; the site shows yesterday's quote labelled "Yesterday"), `::warning title=A daily quote could not be read::` (the page showed it, the refreshes did not bring it), `::warning title=Cannot confirm::` (the run finished but the site did not show it within 5 minutes — never a second dispatch for that), `::warning title=An update is still running::` (a run the check did not start was still running at 170 minutes, today's build on the site), `::warning title=A daily quote is waiting for an update::` (the page showed it; the run the check waited for did not bring it, and the 170 minutes were over), `::error title=Morning update failed::` with the run's link. A *Waited for* row names a running run the check followed that did not end well. |
| Exit codes | **0** — today's update is on the site, or only a quote is late at the source (also while a run the check did not start is still running), or a finished run is not shown yet ("Cannot confirm"), or `--check-only`; **1** — an update run the check started or found waiting failed, or did not start or finish within 45 minutes, or today's build was still not on the site after 3 morning refreshes or 170 minutes — a run the check did not start still running then included (a red ✗: GitHub e-mails whoever started the check — for the alarm, the owner of its key; the runs the guard starts are the bot's, and GitHub e-mails nobody about those, so the guard follows them and fails itself); **2** — no token, repository or site address. |
| Job `tidy` | "Tidy up old runs that had nothing to do" — after `look`, `if: always()`, `permissions: actions: write`, no checkout, bash + `gh api` + `jq`: lists this workflow's own runs of the week before yesterday (`status=success`, `created` up to 24 hours ago — checked again with `jq`) and deletes those whose "Put today's update on the site" job was **skipped** (pure no-ops) or ended at its step "Nothing to do (deleted a day later)" (`IDLE_STEP`: it started, followed and asked nothing — the update was already there, or it was too early to ask a magazine); never a failed run, never one that started or followed an update or asked a magazine, never another workflow's run; at most 50 a run; a problem — the runs or a run's jobs cannot be listed, a run cannot be deleted — is only a `::notice`. |
| `/build.json` | `src/pages/build-info.11ty.js`: `{v, built, day (the build's Central day), tz, quotes {gv, lv} (the days of the quotes on the home page), data (status.json generated), full (status.json full_update: when the last full update ran), run (GITHUB_RUN_ID), version, commit}` — not linked, not in the collections, sitemap or search; `update.yml` warns and `check.yml` fails when it is missing. |
| Failure modes | A magazine late → the new day goes up at once, bounded polling, a yellow note, the site labels the older quote "Yesterday", the later updates pick it up. The alarm fails (401 expired key, 404, cron-job.org down) → cron-job.org e-mails its owner; the hourly schedule still runs (late). Website update fails or never starts → exit 1 (red). The site cannot be read → the refresh is started anyway, then "Cannot confirm". A Website update run already running (the full daily update, a long manual crawl) → the guard follows it instead of queuing a refresh behind it, then starts one only for what it did not bring; one still running after 170 minutes → red when today's build is not on the site (a 300-minute crawl started in the evening delays the morning: start those in the morning), a yellow note when only a quote is missing. Website update disabled → the dispatch is refused → exit 1 with "Enable workflow". If the guard itself crashes before following a run it started, a failed update shows only on `/status/`. |

### `monthly-digest.yml`

Sends **last month's** digest, once. Scheduled tries run five times a day on the 1st–3rd
(`7 8,11,14,17,20 1-3 * *` UTC = 3:07 AM – 3:07 PM CDT / 2:07 AM – 2:07 PM CST on time). GitHub starts them
4–6 hours late, sometimes more, so they are set 4 hours early; the 20:07 try comes after noon Central even
on time, so the 3rd's last try (send with the data there is) always happens.

Except for a preview, the first step (`check`) stops the run unless the four secrets `SMTP_SERVER`,
`SMTP_USERNAME`, `SMTP_PASSWORD` and `DIGEST_TO` exist. A scheduled try then goes on only on the 1st–3rd
**Central** day, from 7 AM Central (`TZ=America/Chicago date`). Then **every** send — a scheduled try or one by
hand, since October 2026 — reads the month's markers (artifacts, kept 40 days; `gh api
repos/:repo/actions/artifacts`, which needs `permissions: actions: read`), unless the `force` input is ticked:
- `digest-sent-YYYY-MM` → done ("The 2026-09 digest was already sent — nothing to do."; by hand also
  `::warning title=Already sent::… To send it a second time, run this workflow again with "force" ticked.`);
- a `digest-sending-YYYY-MM` whose run has no later `digest-unsent-YYYY-MM` of its own → the e-mail **may** have
  gone out (the run was cancelled, timed out or broke off between the two): nothing is sent by itself, every try
  shows `::warning title=Digest send not confirmed::` with the run links, and a person decides (send with `force`
  if it did not arrive). GitHub e-mails nobody about these green runs;
- the API does not answer: `::warning title=Digest not sent yet::`, nothing is sent, and the next try checks again.

Sending is two halves since October 2026. *Build the digest (and decide whether to send it)* runs
`send_digest --prepare "$RUNNER_TEMP/digest-send"` (the same rules as a send: it waits for the data — exit 3, a
`::notice` "Digest waits", the run stays green — while a source it reads has not been tried since the month ended,
below; the tries from noon Central on the 3rd and a send by hand pass `--stale-ok`; it saves `message.eml` and
`envelope.json`, and nothing when the month had nothing new — that month is then marked `digest-sent` with no
e-mail). With a prepared e-mail, *Mark the month as being sent* uploads `digest-sending-<month>` **before** the
e-mail goes (a failed upload sends nothing), then *Send the digest* runs `send_digest --send-prepared …`, the only
step that sees `SMTP_PASSWORD`: exit 0 (sent) or 4 (the connection broke while the e-mail was handed over: it MAY
have been sent — `::error title=The digest MAY have been sent::…`) upload `digest-sent-<month>`, so no later try
sends it again, and 4 still fails the run (*Fail the run — the e-mail may not have gone out*): check the group, and
only if it did not arrive send it with **Run workflow** (*Preview only* unticked, `force` ticked). Any other exit
(1 the server took nothing, 2 settings missing) uploads `digest-unsent-<month>` and fails the run (`::error
title=The digest was not sent::The mail server took nothing … — the next try sends it.`, *Fail the run — the e-mail
was not sent*): nothing was handed over, so the next try sends. On the 1st the Morning check starts the full daily update
early ([`morning.yml`](#morningyml--morning-check-new-day-by-530-am), step 5), so the wait is usually over by the first try.

A manual run defaults to **preview** (`--dry-run`, uploaded as the `digest-preview` artifact). It takes an
optional *month*, the month the digest **covers** (`--month YYYY-MM`). Anything typed there is passed on
(spaces removed), so a mistyped month makes `send_digest` exit 2 instead of sending another month's edition.
Unticking *Preview only* sends at once — no day / hour guard, `--stale-ok` — but **with** the marker check, and
marks the month (a month with nothing new is marked without an e-mail, as on a scheduled try). Ticking `force` too
(run title "Monthly e-mail digest: SEND AGAIN (forced, started by hand)") skips the markers: it sends the month
again. *Preview only* and `force` both ticked is a preview.
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
  - **bulletin** (`announcements.json`): counted on the day it was added to the site — `first_seen` (its
    `date` instead when that is the same Central day, or when there is no `first_seen`), never before its
    `extra.publish` day (a scheduled post). The `date` is only the post's label: a post dated in an earlier
    month but saved later (written on the 28th, saved on the 2nd, after that month's e-mail) is in the
    edition of the month it appeared, like a committee upload, and so is one dated ahead (a notice dated
    with its event's day, saved weeks before; by that month it has usually expired — What's New dates it on
    `first_seen` too); in P, not after now + 1 day, not expired. Pinned first, then newest.
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
    (`issueTheme`: the issue's own, else its stories' `issue_theme`, else the magazine's call for stories —
    Grapevine's editorial calendar, La Viña's yearly themes) and
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
  the digest: the committee meeting (its Zoom details stay on `/meetings/`, which the toolkit links to),
  events not over yet, the weekly meetings, story
  deadlines, La Viña's topics, the phone lines, Book of the Month, subscriptions, the daily quote, the
  Instagram accounts to follow (the digest has last month's posts).
- The intro counts, in this order: magazine stories, podcast episodes, videos, Instagram posts, documents,
  committee files, photo albums, bulletin posts (`COUNT_ORDER`, both files).
- English half, then Spanish half (La Viña first there), from the `i18n` fields build_data produced.
  `digest.per_section` items per list, then "and N more". In the Spanish half, issue labels read as in a
  sentence ("septiembre–octubre de 2026": La Viña's issues are named from their key, `issue_name`, the one
  style of read.js `issueName`) and Grapevine's issues and writers say "(en inglés)"; La Viña's say
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
  handed over **once**: if the connection breaks at that point, it is reported as "It MAY have been sent —
  check the mailbox or the group before sending it again" (exit 4) and never retried, because a retry could
  e-mail every district twice; the workflow marks the month as done all the same, so its later tries do not
  send it either. A refusal at that point (the e-mail, its sender or every recipient refused) sends nothing:
  exit 1, and the next try tries again.
- Nothing new in P (no news — Instagram posts count —, no writers) → nothing sent (exit 0).
- Exit codes: 0 = sent / previewed / prepared / nothing new; 1 = SMTP failure (or the prepared e-mail could not
  be read); 2 = not configured, `--month` not YYYY-MM, or (sending) a month that is not over yet; 3 = waiting for
  the data; 4 = the connection broke while the e-mail was handed over: it MAY have been sent (the workflow marks the
  month as done and fails the run). `--prepare DIR` / `--send-prepared DIR` split a send in two (above).

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

Sundays. Since October 2026 two jobs: **Check links** (`contents: read` only — the workflow's default is
`contents: read` too) and **Report broken links (the issue)** (`issues: write`, no checkout, no outside code: it
downloads the first job's `link-check-report` artifact, kept 7 days, with `actions/download-artifact@v8`, and
`GH_REPO` names the repository). The first job builds the site with `PATH_PREFIX=/`, runs **lychee**
(`lycheeverse/lychee-action@e7477775783ea5526144ba13e8db5eec57747ce8 # v2.9.0`, pinned to the commit the `v2` and
`v2.9.0` tags pointed to on 6 October 2026; Dependabot's `chore(actions)` pull request moves the SHA and the note
together) over `_site/**/*.html` with
`--root-dir _site` (internal links are checked on disk), `--host-concurrency 2`,
`--host-request-interval 1s`, a 3-day response cache, and accepts 403/429 (bot walls). High-volume
or bot-hostile hosts are excluded (aagrapevine.org, aalavina.org, YouTube, Instagram, Google,
Zoom, podcast platforms, social networks). Then it checks every URL under `links:` in the config
with the project's `PoliteSession` (robots.txt + 5 s Crawl-delay). Results: run summary + a single
issue *"Broken links found by the weekly check"* that is commented on while problems persist and
closed automatically when clean. It never fails the workflow.

Checked locally (2026-09-23): lychee 0.24.2 — the version `lychee-action@v2` installed then — accepts every
flag used; `lychee --offline --root-dir <abs path>/_site '_site/**/*.html'` on a `PATH_PREFIX=/`
build resolved all internal links (0 errors), and a page with a deliberately broken link was flagged.
To reproduce on Windows, pass the root dir as `C:/…` (Git Bash: also `MSYS_NO_PATHCONV=1`).

### `check.yml` — Code check (tests and test build)

On every `pull_request`, on every **push to `main`** that touches `scripts/**`, `tests/**`, `src/**`
(not `src/assets/cache/**`), `eleventy/**`, `eleventy.config.js`, `config/**`, `content/**`, `data/geo/**`
(the place tests read the Texas places list), `data/translations/{overrides,glossary}.yml`, `package*.json`,
`requirements.txt` or any workflow in
`.github/workflows/` (the tests read the workflows: the schedules, the morning mode, the Morning check;
most work here is pushed straight to `main`, so without this the tests would never run), and
on `workflow_dispatch` (run name "Code check (started by hand)"; a push or a pull request keeps GitHub's title).
`permissions: contents: read`, nothing published; the bot's data commits never trigger it (pushed with
`GITHUB_TOKEN`). Job `build` (shown as **Test build of the website** — not "Build the website", the name of
Website update's own build step; 20 min): `npm ci` →
`PATH_PREFIX=/<repository name>/ I18N_STRICT=1 STRICT_BUILD=1 npx @11ty/eleventy` (since October 2026
`STRICT_BUILD` fails the build on any build warning — `[icon]`, `[community]` / `[media]` / `[read]` / `[published]`
sprite icons, `[sitemap]`, `[links]`, `eleventy/build-warnings.js`: "STRICT_BUILD: N build warning(s) — fix them (or
build without STRICT_BUILD):" and the list, each also a `::error title=Build warning::`; the booth's "not downloaded
in this build" notes, the `[css]` sizes and a missing data file are not warnings) → the same sanity checks as
*Website update* (`index.html`, `es/index.html`, every stylesheet at the top of `src/assets/css` in
`_site/assets/css/`), plus `build.json` — an error here, where *Website update* only warns → since October 2026 the
**browser checks**: Python 3.12, `pip install -r scripts/ops/requirements-browser.txt` (Playwright, pinned, + Pillow),
then `python -m unittest discover -s tests/browser -t tests -v` with `GV_BROWSER_SITE=_site`,
`GV_BROWSER_CHANNEL=chrome` (the runner's own Google Chrome, headless — nothing is downloaded) and
`GV_BROWSER_REQUIRED=1` (a browser that cannot start fails, never a silent skip); 10 min. The build is served the
way GitHub Pages serves it (`scripts/ops/serve_site.mjs`: no store cache, byte ranges, the 404 page, a 301 for a
folder without its `/`; started by `scripts/ops/site_browser.py` with `--stop-with-parent`), every host name but
127.0.0.1 fails to resolve, and the checks are: `HeaderFocusRing` (Search, ES / EN, Aa and theme at the top and
scrolled, in light, dark, high contrast and high contrast dark: the ring's band, focused against not focused, at
least 3 : 1, measured on the pixels, after confirming the saved theme and contrast took), `StickyBarFocus` (What's
New's sticky filter bar never hides the focused element, 1280 × 800 English and 390 × 844 Spanish, also once
relaxed spacing goes off), `LargeTextPhone` (no sideways scroll at 360 px with 150 % text, `LARGE_TEXT_PAGES`, both
languages), `OfflineUpdate` (a new `sw.js` activates in under 6 s while an open tab's page is held 20 s),
`OfflineAreaStyles` (a page opened online, then a new version, then offline: it keeps its own area stylesheet),
`ScriptErrors` (no `pageerror` on `MAIN_PAGES` and this month's poster page, in both languages, and the phone menu),
`PosterPicture` (one share picture at 1200 × 630) and `TrackerPhotos` (two Tracker tabs: an entry deleted in one
while the other edits it is saved again with its receipt photo, byte for byte; closing a tab whose entries the
browser would not store asks first). Each page must answer 200 ("/<page> answered 404, not 200 — is it still part of
the site?"). About a minute and a half with setup. Job `tests` (25 min since October 2026, 15 before; about 10 minutes with `GateLists`, the
`check.yml` comment reckons): Python 3.12,
`pip install -r requirements.txt`, Node.js 22 + `npm ci` (the tests that run the site's own JavaScript
through `tests/nodejs.py` — the district report, the offline worker, the digest parity, the one-tap
phone links — are skipped without them), `python -m unittest discover -s tests -v` (no translation models
are downloaded, so model tests are skipped; `tests/browser` skips itself without `GV_BROWSER_SITE`), then
`send_digest --dry-run` into the runner's temp folder (a smoke test of the optional e-mail). Dependabot
PRs therefore show a ✓/✗ before merging (the chair merges only on green), and a push that breaks the
tests shows a red ✗ on its commit. A push runs this alongside *Website update*, which since October 2026 runs the
same offline tests (all but `DATA_TESTS`, `CONTENT_TESTS` and `LIST_CHECKS`, `scripts/ops/gate_tests.py`) before it
publishes a change of the code, and publishes nothing when they fail: a red ✗ here means "fix or revert that
change"; the live site keeps the version before. A slip in the committee's files (`content/`, `config/`, the
glossary, the overrides) turns only this check red: *Website update* publishes, and the sync and the build leave out
what they cannot read.

Two tests guard the code itself (both since October 2026). `tests/test_settings_used.py`: every key of
`config/site.yml`, `expenses.yml`, `carry.yml`, `history.yml` and `orientation.yml` must be read by some code (a
Spanish twin `<name>_es` counts when `<name>` is read; the map-like keys — `meetings.feeds[].region_types`, the
months of `carry.yml` `tips` — are listed in the test with their reasons), and every setting the templates, the
build's JavaScript or the sync read must exist or be read with a default. `tests/test_unused_code.py`: a filter,
shortcode, shared macro (`src/_includes/macros`) or i18n key that nothing uses fails (an i18n key counts when it is
written out, built from a written prefix, or `<a read key>_one`), and every non-HTML page declares `layout: false`.
The parts that judge the committee's own settings (a key it added that no code reads yet, one it deleted that a
template reads) are `CONTENT_TESTS`: only this check runs them.

### `dependabot.yml`

Monthly grouped PRs for GitHub Actions and npm (minor/patch only), checked by `check.yml`. Python packages in
`requirements.txt` float within their current **major** version (`>=x,<next-major`), so each daily run picks up
minor/patch releases automatically; since October 2026 a third entry (`package-ecosystem: pip`, group
`python-packages`, `update-types: [major]`, prefix `chore(deps)`) opens one monthly PR when a new **major** version
is out, which raises the cap (minor and patch updates are ignored there). `yt-dlp` is deliberately uncapped — it
must keep up with YouTube changes — and ignored by Dependabot. A fourth entry (since October 2026,
`package-ecosystem: pip`, `directory: /scripts/ops`, `allow: playwright`, monthly, prefix `chore(deps)`, at most one
open PR) moves the exact `playwright==…` pin of `scripts/ops/requirements-browser.txt` — the CI-only file of the
browser checks and the posters' share pictures; `requirements.txt` is unchanged — to each newer release, minor and
patch included, so it keeps up with the runners' Chrome; the Code check's browser checks run with it before it is
merged. `tests/test_automation.py` → `Dependabot` checks the entries and that every package but yt-dlp is capped
below its next major version.

## Sync modules

All modules follow the same conventions (see [DATA_SCHEMA.md](DATA_SCHEMA.md)): `main(argv)`,
`python -m scripts.sync.<name>`, output via `save_raw()`, cumulative `merge_items()` (preserves
`first_seen`, never drops items on a bad day), `ok=false` + error message on failure, time-boxed,
`--dry-run`. Each module's docstring is the detailed reference.

| Module | Source → output | Normal path | Fallbacks / safety | Useful flags |
|---|---|---|---|---|
| `articles.py` | aagrapevine.org `/magazine`, aalavina.org `/la-revista` → `articles.json` | Issue hub pages (titles, bylines, public teasers, card images); each article page fetched once for issue/topic/section/paywall flag | Home page / `/revista-2` if a hub fails; missing fields retried ≤ 3× a week apart. **Never stores article bodies.** | `--max-details 40`, `--max-seconds`, `--no-details`, `--only gv\|lv` |
| `crawl.py` (+ `crawl_rules.py`, `crawl_pdf.py`) | both sites → `pdfs.json` (+ `hub_problems`), `data/state/crawl-state.json`, `src/assets/cache/pdf/` | Sitemaps → priority queue (hubs daily **whatever they last answered** — `HUB_PATHS` / `KIT_PAGES`; a failing hub is retried after `HUB_RETRY_H` = 12 h, so at every run —, new pages, changed `<lastmod>`, events, re-checks every `recheck_days`); conditional GETs; ~30 % of time on PDF work (download ≤ `pdf_details_per_run` new PDFs ≤ `pdf_max_mb` for page count/title/thumbnail, each **read in a child process**, `python -m scripts.sync.crawl_pdf --analyze`, `PARSE_TIMEOUT_S` = 60 s and on Linux `PARSE_MEMORY_MB` = 2048 (`RLIMIT_DATA`); HEAD others) | Resumes daily from state; since October 2026: a page that answered 200 before keeps its PDF links through a first 404/410 (`gone_strike_at`, re-checked the next day) and drops them only on a second at least `GONE_CONFIRM_H` = 24 h later; another host is asked twice before it counts as down for the run, and its other PDFs are re-queued with no strike (`pdfs_requeued`); robots.txt refusals are `head.error = "robots"` with a 30-day `next_try`, never a strike; a robots.txt answering 5xx / 429 / nothing closes its host for `ROBOTS_RETRY_S` = 600 s, and on the magazine sites leaves their pages and PDFs untouched for the next run (a `stats.warnings` line); the parse attempt is recorded before reading (`details.error = "parse: interrupted"`), so a file that crashes or hangs the reader is retried after 2, 4, 8, 16, then 30 days; `prune()` forgets junk paths and pages gone (404/410/400) for `PRUNE_GONE_DAYS` = 90 that are not in the sitemap and no page linked meanwhile (hubs never); PDF dates are the Central day of `Last-Modified`; a PDF becomes `gone` only after **two** failing checks at least 24 h apart (404/410, or an HTML page where the file was — `gone_strike_at` marks the first; until then such an answer is only a strike: the error page's Last-Modified / Content-Length never replace the file's date and size, and a first download that got one is retried with the normal back-off, its details turning final only once the PDF is gone); a gone PDF that a page still links is re-checked after a week, later monthly, and comes back when it answers; a PDF on **another** site whose host has not answered at all for 30+ days (4+ tries, `head.unreachable_since`) is gone too — the magazine sites' own files are never retired that way; skip rules for login/cart/paywalled paths; PDF author metadata deliberately not read (anonymity) | `--minutes N` (0 = rebuild from state, no network), `--details`, `--url`, `--max-pages` |
| `podcasts.py` | shows in `sources.podcasts` (`gv` AA Grapevine's Podcast, `wo` Grapevine Weekly Open AA Meeting) → `podcasts.json` (category = show key) | RSS via requests + feedparser | Previous episodes kept on a bad feed; an episode that leaves the feed is `gone` only when its audio 404/410s; weekly discovery of new show feeds, never auto-added: listed under *New podcast feeds found* in the *Website update* run summary (with a `::notice`), and in `stats.discovered_feeds` of `podcasts.json` / `status.json` (the `/status/` page does not show them) | `--limit`, `--discover`, `--no-discover` |
| `youtube.py` | channel `UCI9uFLJ__aXT3-At0PlPWUQ` → `youtube.json` | Channel + uploads + playlist RSS every run | yt-dlp full listing weekly and a few dozen per-video detail fetches per run; if yt-dlp is blocked on CI IPs, RSS alone keeps the site current; a bot check, captcha, rate limit or time-out stops that run's per-video details without counting against the video (`detail_fails` counts only per-video failures such as an age gate or an extractor error; after 3 a video is not asked again) — since October 2026 said in one plain `stats.warnings` line (`bot_check_note`: "details stopped: YouTube answered with a bot check (“confirm you’re not a bot”) — nothing is wrong on our side; videos keep their last known details", or "listing stopped: …"; warnings capped at 200 characters); deletions confirmed via oEmbed only after a complete listing | `--backfill`, `--no-backfill`, `--details`, `--backfill-minutes` |
| `instagram.py` | two accounts → `instagram.json`, `src/assets/cache/ig/` | Graph API Business Discovery if `IG_ACCESS_TOKEN`+`IG_BUSINESS_ID`; else the public profile **embed** page (a few requests/day) | web_profile_info JSON → profile HTML → optional RSSHub mirrors → post embeds; keeps last posts when all fail. Removal sweep (since October 2026, full runs, public pages only): up to `recheck_per_run` (5) posts no longer listed are looked up through their post embed; two "not there" answers ≥ `GONE_CONFIRM_HOURS` = 12 h apart remove the post and its picture — an answer counts only when a post embed of the **same account and the same kind** (a post or a Reel: `embed_kind`, `Fetcher.last_ok`) worked after it in the same run, so one account's (or kind's) unusable embeds never remove the other's posts; with none yet, one control request per unproved account and kind goes to that account's newest listed post of that kind — or, with none of that kind listed (the listings never say which posts are Reels), to the account's newest listed post of any kind, since every post's embed has the same address and a deleted Reel must still leave the site; with nothing of that account listed today, nothing is decided, and `stats.warnings` says "removal re-check: N post(s) showed no usable embed, but no embed of a post of the same account worked after that (a login wall, a block, or embeds that do not work for that account?) — nothing was decided"; a 429/401/403/login redirect stops the sweep; marks in the envelope's `removal`, results in `stats.removal` `{checked, missing, removed}`; hand-listed posts are never swept. A YAML mistake in `content/instagram.yml` (since October 2026) keeps the last update's hand-listed posts as they were, pictures and all, with the `stats.warnings` line "content/instagram.yml line N: YAML error — … — the N hand-listed post(s) of the last update are kept, pictures and all, until the file is fixed". `sources.instagram.anonymous: false` (or env `IG_ANONYMOUS=0`) disables every non-API request: only the API + `content/instagram.yml` | `--strategies`, `--account`, `--keep`, `--no-enrich` (also skips the removal sweep), `--recheck N`, `-v` |
| `drive.py` (+ `drive_listing.py`) | public Drive tree under `drive.root_folder_id` → `drive.json` (documents, photos, flyer events, bulletin posts — Drive folder `bulletin` / `boletín`, or the older `announcements` / `anuncios`; a post's name may carry `(pinned)` / `(fijado)`, `(until …)` / `(hasta …)` and `(from …)` / `(desde …)` — also `publish` / `publicar` — → `extra.publish`, taken out of the headline only when it holds a date; an undated scheduled post is dated its `(from …)` day) | Public "embedded folder view" HTML (no key) | Drive API v3 when `GOOGLE_API_KEY` is set (falls back per folder); a folder only counts as read when Drive returned a real folder page, so a network error never deletes items; since October 2026 a folder (or the root) that held files and lists empty is kept for one run (`empty_folders` `{id: since}`, its files `unconfirmed` → `held`) and removed when the next run sees it empty too; `stats` count what is not published (`loose_skipped`, `unreadable_folders`, `depth_limited`, `unconfirmed_folders`; `skipped_panels` = panel numbers) — and since October 2026 the run log counts them too, never naming a file or folder that is not published ("N entries outside the panel folders (not published)", "N folder(s) deeper than 6 levels (not read — move their files up)", 6 being `--max-depth`; an unreadable folder by the folder above it and its Drive address `…/drive/folders/<id>`, a file that fails by its folder and file id); text downloads stop at `MAX_TEXT_DOWNLOAD` (3 MB), a `.docx` over `MAX_DOCX_ENTRIES` (500) parts or `MAX_DOCX_UNZIPPED` (25 MB) unpacked is not read; a numbers-only date in a name that could be read two ways → a `stats.warnings` line naming the file; spreadsheets and `PRIVATE`/`(Responses)` names never published | `--no-api`, `--max-depth`, `--max-minutes`, `--include-loose` |
| `editorial.py` | `/contribute`, `/temas-sugeridos`, La Viña's yearly themes document (the newest "Temas de LV <year>" linked from `/recursos`: `sources.lavina.themes_page` / `themes_link`) → `editorial.json` | Grapevine editorial calendar (themes + deadlines); La Viña evergreen topics; La Viña's dated themes — every year in the document (pypdfium2 text; the issues and themes paired in order and checked: as many themes as issues, deadlines readable and in order, each 1–15 months before its issue; ≤ 20 MB). 4 requests a day | Three parts, each on its own: a parsed part replaces its topics (the themes document only for the years it covers); a part not fetched or not understood — no document linked, a document that cannot be downloaded or read, a changed layout — keeps its previous topics (`ok: false`, "lv-themes: …") | `--only gv\|lv\|lv-themes`, `--gv-html FILE`, `--lv-html FILE`, `--lv-resources-html FILE`, `--lv-themes-doc FILE` (the document, or its text with pages split by form feeds), `--force`, `--dry-run` |
| `weekly_open.py` | `/grapevine-weekly-open` → `weekly_open.json` | Parses day/time/Zoom ID/passcode (`find_passcode`: the first word after password / passcode / contraseña / código de acceso that holds a digit; a letters-only one unless it is a sentence word, `PASS_WORDS`), converts to Central | Previous item kept on failure | `--html FILE` |
| `audio_project.py` | aagrapevine.org `/audio-portal`, aalavina.org `/graba-tu-historia` + `/instrucciones-graba-tu-historia` (`sources.grapevine.audio_project`, `sources.lavina.record_*`) → `audio_project.json` | The story lines: phone number, keys to press, length, the e-mail address for recordings (Cloudflare-protected → decoded), the no-speaker-recordings note, Grapevine's playlists, La Viña's copyright sentence. 3 requests a day | A page not fetched or not understood keeps that part's previous data (`ok: false`); when only La Viña's instructions page fails, its steps come from the previous run and the rest is fresh (`ok: true`, a note in `stats.warnings`) | `--dry-run`, `--html-dir DIR`, `--save-html DIR` |
| `shop.py` | aagrapevine.org / aalavina.org store pages (`sources.<pub>.botm`, `subscriptions`, `subscription_regions`, `specialty`) → `shop.json`, `src/assets/cache/shop/` | Daily: each Book of the Month page + its product page (price, bulk-book tiers), each subscriptions page + its region listings (~12 requests); monthly: one product page per subscription type (the short descriptions); weekly: the specialty pages — greeting cards, pocket planner, wall calendar and the holiday cards (7 pages: product pages, La Viña's `/tienda/articulos-especiales` listing, Grapevine's `/store/specialty-items` as a fallback); each product picture once (≤ 4 new a run) | Each part is independent: a page not fetched or not understood keeps that part's previous items (`ok: false`); a region listing without one readable price counts as not parsed; a Book of the Month page with no offer is not an error. The holiday cards are **seasonal**: a store that stops showing them (their page gone and no listing showing them) is not an error — the last good item is kept with `extra.missing_since` (+ `stats.specialty_out_of_season`), `build_data` shows it 14 more days (`SHOP_SEASONAL_GRACE_DAYS`), then leaves it out until the next season's read; a holiday page that answers but is not understood, or is down while a listing still shows it, is an error like any other; the other three kinds never depend on it. `sources.<pub>.specialty_skip` hides a kind (deleting a product page's line only moves the item to the listing) | `--dry-run`, `--refresh-specialty`, `--refresh-types`, `--no-images`, `--html-dir DIR`, `--save-html DIR` |
| `announcements.py` | `content/bulletin/*.md` → `announcements.json` (the `/bulletin/` page; a post needs no header: title from its first heading or file name, date from its file name, else its `publish:` day, else its first sighting; `publish: YYYY-MM-DD` schedules it — `extra.publish`; a bad value, or one after `expires:`, is a file problem; `stats.active` counts the posts shown today, in Central time; pasted HTML → Markdown; links to pictures / documents saved next to it → `/bulletin/files/`, which `eleventy.config.js` publishes); `content/events/*.md` → `manual_events.json` (hand-written `title_es` / `summary_es` — or `title_en` / `summary_en` — → `extra.own_i18n`, used by build_data instead of a machine translation) | Markdown + YAML front matter (no network) | The folder is the source of truth; a file with a formatting mistake is skipped and reported on `/status/` instead of breaking the run | `--dry-run` |
| `quote.py` | aagrapevine.org `/`, aalavina.org `/` (`sources.<pub>.quote_page`) → `data/raw/quote.json` (items + 14-day `history`, raw only; each day's entry has `seen` — the UTC time that day's quote was first read, kept on later reads; an entry written before these times were kept has none and never gets one — which `build_data` turns into `status.json` → `quote_days`) → `data/site/quote.json` (items) | The `#quote-of-the-day` teaser (`article.node--type-quote`): heading date (no year in the heading: the year is chosen inside `heading_window`, from `PAST_DAYS` = 365 days back to tomorrow, Central; a heading outside it is not used — the quote counts as today's, with a warning; a stored quote or history entry dated after tomorrow is dropped), quote text (outer quotation marks cleaned, never translated), attribution / source split at "From:" / "De", the publication's own e-mail sign-up link. One request per site (none when an earlier module of the run read that page), in every run (full, quick, morning). `peek()` is the Morning check's question "is today's quote out?": only a date read from the heading counts; nothing is written | Falls back to the view embed near the top of the page; a publication that fails keeps its previous quote (and last known sign-up link), `ok=false`; an older quote than the one known never replaces it | `--dry-run`, `--only gv\|lv`, `--html-dir DIR`, `--save-html DIR` |
| `writers_archive.py` | the owner's exports of the Grapevine and La Viña online archives, `content/archive/*.csv` (`writers_archive.folder` can move it) → `data/raw/writers_archive.json` (Texas rows only, a full replacement each run) | The newest file of each magazine by the date in its name (`parse_name`: `2026-10-04`, `20261004`, U.S. `10-04-2026`; `(1)` / `_v2` break a tie; undated loses), its magazine confirmed by the majority of its links; read as UTF-8 (the BOM dropped before either reading; a mostly-UTF-8 file with a few bytes that are not UTF-8 stays UTF-8 — they show as U+FFFD — with a warning naming the line of the first; else Windows-1252 + a warning); headers matched by prefix (`map_header`); every field cleaned (`clean_field`: entities before the `;` split, the export's `<lb` breaks, tags, mojibake, NFC, ligatures, soft hyphens); a row kept when "Texas Author?" says yes or `geo.classify_writer` (best of the printed place and City / State) reads Texas; issue from Month / Year only; writers split on `;` and paired by position; flags from Notes (online exclusive, column, signature / group byline) and the two audio columns; content duplicates (`-0` endings) kept once. No network, a few seconds; in every mode (`QUICK_MODULES`) | A file without a needed column (Link, Title, Month, Year, Written By, Location (as published), Texas Author?), with fewer rows than `writers_archive.min_rows_ratio` (0.8; 0 = off) × the rows of the file used before, or unreadable is **not used**: that magazine keeps its previous rows (a file is chosen only once it passes, newest first; a failed one settles its magazine on the rows it had — only a magazine with no rows and no file on record, a first run, goes on to its next older file), `ok: false` with the reason and what stays (", the older rows stay", the cut-off guard's "so the older data stays"; on a first run ", the older <file> is used instead" or ", and there are no older <magazine> rows to keep") (→ "CSV file to fix" in the run summary, the `writers_archive` hint of the report issue); the other magazine's new file is still taken in. A magazine with no file keeps its rows (a warning). Older / undated copies → "older archive file still in … (it is not used and may be deleted)", except the file on record while a newer one failed: "(it stays in use until <newer> is fixed)"; another magazine's export under this magazine's name while that magazine has its file → one warning, not used; unknown `.csv` names and archive-named files in another format (`.xlsx`, `.numbers` …: `candidates`) → warnings. Change detection by a sha256 of the text with LF line ends; `files.<pub>.imported_at` moves only when the name, the hash or `PARSER_VERSION` changed; each row keeps `first_seen` (by address from the last envelope; a new address: this run) → `status.json` `new_7d`; `stats.changed`, `notes` ("New archive file used: …"), `warnings` | `--dry-run` |
| `translate.py` | all raw titles/summaries/bodies → `data/translations/cache.json` | CTranslate2 + Argos 1.0 models (auto-downloaded to `GV_MODELS_DIR`), sentence splitting with per-sentence ¿…? / ¡…! pairing, protected spans (URLs, handles, times, codes, sizes like 8.5 x 11, "Firstname X." names), glossary (+ built-in Step/Tradition ordinals, "[Season N, Episode M]" → "[Temporada N, Episodio M]"), sentence case for Spanish titles / Title Case for English titles, an output guard (rejects repeated-word loops, changed numbers, entity leaks → keeps the original) and a vocabulary guard (never outputs "coger" — vulgar in Latin-American Spanish) | Cache hits never re-translate; `overrides.yml` always wins; glossary edits re-translate only affected texts; bump `ENGINE_VERSION` to re-translate all. An unreadable `cache.json` is moved aside as `cache.json.bad-<UTC time>` and reported (`Translator.problems` → `status.json` `translations.problems` and `problems.translations`); if it cannot be moved it is never overwritten (nothing is translated that run). A downloaded model whose SHA-256 is not `MODEL_SHA256` is not installed (`ModelMismatch`): that direction stays untranslated, with the reason | `"text" --to es`, `--download`, `--stats` |
| `build_data.py` | `data/raw/*` + content/ + config → `data/site/*.json` | Adds `i18n`, `machine`, `is_new`; builds events (12 months of committee meetings + `recurring_events:` from the config + flyers + manual + external + the optional `sources.ics_feeds` calendars, each real event once — see [Events](#events-several-days-to-be-confirmed-places-outside-calendars)), `whatsnew.json` (newest 150), `status.json` (+ `feeds`: the health of each outside calendar; `scheduled`: the bulletin posts whose `publish` day is still to come — left out of every site file until that day, Central time — soonest first, at most 20; `quote_days`: when each of the last 7 mornings' quotes came in against `site.morning_goal`, for `/status/` — a day whose quote came in at a time not recorded is left out; `full_update`: when the last full update ran, for `/build.json` — kept from the last build with `--keep-full-update`, which run_all passes in quick and morning runs; `writers_archive`: the archive files in use and how the list was made; `reminders`: dated settings that run out soon), `writers_archive.json` (the Texas writers archive: the archive files' rows + every captured Texas story of any age, `plan_writers_archive` / `build_writers_archive`; where each writer is from worked out again on every run; its titles and summaries translated last, tiers 5 and 6). A published scheduled post is news from the start of its day (`Ctx.effective_ts`: What's New, the feed, the "New" badge, the digest) | Only writer of `data/site/`; templates read nothing else. A raw file that exists but cannot be read (`Ctx.unreadable`) keeps what the last build made of it (`carry_unreadable`: the whole site file, or that source's items in `announcements.json` / `events.json` / `whatsnew.json`), its `status.json` row keeps the last values with `ok: false` and "data/raw/<source>.json cannot be read (<reason>) — restore it from git; the site keeps the last build's items" (`common.unreadable_message`), and the translation cache is not pruned meanwhile (`prune_blockers`: an unreadable or missing raw file, or glossary / overrides — never a settings note). Since October 2026 the same holds for a raw file that is **missing** although the last build's `status.json` (`Ctx.load_raw(previous)`; a fixture one is ignored) had items from that source (`Ctx.raw_missing`): "data/raw/<x>.json is missing — the site keeps the last build's items until an update of this source works (or restore the file from git)"; and for one that its next update, which failed, wrote again with `ok: false` and nothing in it (`Ctx.missing_failed`): "data/raw/<x>.json went missing and this source's update since did not work (<error>) — the site keeps the last build's items until one works (or restore the file from git)". The first update that works, even one that finds nothing, ends it; a source with nothing before starts empty, "not run yet". Files whose own time would be "now" keep the last build's `updated` when nothing else in them changed (`stamped`). A bad `meeting:` / `recurring_events:` / `ics_feeds:` / `price_changes:` entry (or a `skip_dates` value that is not one of the rule's days) is skipped and listed in `status.json` → `problems` (and as a **Settings problem** in the run summary). Its only network request: each `.ics` feed, at most once a day (`--offline`: none) | `--offline`, `--no-translate` |
| `run_all.py` | orchestrator | Runs every module in turn, isolating failures, then translation + `build_data` (`--keep-full-update` in quick and morning runs); the run table is titled "Full update", "Quick refresh" or "Morning refresh" | A crashing module is recorded as `ok=false` (see `run_module`) and the rest continue. A module whose own raw file cannot be read (`common.raw_unreadable`) is not run at all (since October 2026: it would only rebuild the source from scratch, and Instagram's clean-up would delete the pictures of every older post): its row is "failed" with `common.unreadable_message`, no failure mark is written over the file (`run_module` catches `UnreadableRaw` first; `save_raw` raises it too), and build_data keeps the last build's items until a person restores the file (`RAW_ALSO`: `announcements` also writes `manual_events.json`, so the bulletin still updates while an unreadable `manual_events.json` stays untouched and the row is failed). A full run with `--crawl-minutes 0` while `sources.crawler.minutes_per_run` is 0 (`crawl_paused`) refreshes `attempted` of `data/raw/pdfs.json` with this run's own `changes` (`{added: 0, removed: 0, held: …}`) and `hub_problems: []` (`_note_paused_crawl`; not for `ok: false`, a quick or morning run, or a 0-minute run by hand while the search is on) and names the crawl row "paused (sources.crawler.minutes_per_run: 0)", so the paused search is never "not checked", also after it is switched back on | `--crawl-minutes N`, `--quick`, `--also a,b` (with `--quick` only: also these modules, never the crawl), `--morning` |
| `meeting.py` | config `meeting:` (+ the rule engine for `recurring_events:`) | `upcoming_rule_dates(MonthlyRule, count, tz)`: the Nth weekday (1–5, or −1 = last) of every month, start–end on the local clock → UTC instants (right across DST changes and month/year ends), `skip_dates`. Used for the committee meeting (3rd Wednesday 7–8 PM Central by default) and every recurring event | An end earlier than the start, at most 12 hours later (`overnight`, `OVERNIGHT_MAX_HOURS`), is the next morning (since October 2026; `22:00`–`01:00`); otherwise an end not after the start is one hour, capped at 23:59. Every copy of the rule follows the same overnight rule: `eleventy/central-time.js` `overnight()` / `ruleDate` (the build and, as `GVTime`, the browser's countdowns: `app.js` `GV.nextMeeting`, `committee.js`), `eleventy.config.js` `monthlyRule`, `committee.js` `meetingEnd` / `meetingTimeRange` ("10:00 PM – 1:00 AM"), `monthly.js` `meetingByRule`, `src/_data/meeting.js` and `send_digest.py` `meeting_by_rule` (its own copy of `overnight`). `check_skip_dates()`, shared by the meeting and every recurring event: a skip date that is not a date, or not the rule's day of its month, is ignored and noted ("skip date “2026-12-17” is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16)") → `problems.meeting` / `problems.recurring_events` | — |

## Recurring events

`config/site.yml` → `recurring_events:` lists what the committee does every month (the GV/LV booth
at CityWide Dallas: 2nd Saturday, 17:00–20:00 Central) and what La Viña or Grapevine hold every month that
the committee shares (`host: lv` — La Viña's monthly workshop on Zoom, `lv-monthly-workshop`: 4th Thursday,
14:00–15:00 Central = 3 PM Eastern, online only, its flyer on our Drive). Chair-facing instructions are in
the [README](../README.md#add-a-recurring-event); the data fields in [DATA_SCHEMA.md](DATA_SCHEMA.md).

Why the 4th Thursday (researched October 1, 2026): the flyer and Instagram say "el último jueves de cada mes",
but La Viña's own calendar (aalavina.org, `events_external`) has listed every "Taller mensual" with the same Zoom
link (meeting 815 9593 1777) and no time; in the months with five Thursdays it was the 4th (Aug 22 2024, Jan 23
and Oct 23 2025, Jan 22 and Apr 23 2026 — May 29 2025 was the one exception; Sep 18 2025 and Mar 19 2026 were
3rd Thursdays, which neither rule fits), and in November and December the Thursday before Thanksgiving /
Christmas (Nov 21 and Dec 19 2024, Nov 20 and Dec 18 2025) — hence `skip_dates: ["2026-11-26", "2026-12-24",
"2027-11-25", "2027-12-23"]`. To follow the flyer's "last Thursday" instead, `week_of_month: -1` switches the rule
(its December skip dates are then Dec 31 2026 and Dec 30 2027). Thanksgiving is ALWAYS the 4th Thursday of
November, so each year's must be added ahead of time: `series_listing_notes` warns only once La Viña's calendar
lists the moved date (about 3 weeks ahead), while the `/monthly/` posters project the rule 13 months ahead
(`monthly.js`) and `/events/`, home, the feed and search list each date `months_ahead` months before. No end time
is published anywhere (its pages give the day, its Instagram posts the start): one hour.

| Where | What happens |
|---|---|
| `build_data.recurring_specs()` | Validates each entry. **Skipped** (reason in the log and in `status.json` → `problems.recurring_events`, shown as a *Settings problem* in the run summary): not a mapping, no title, a `week_of_month` other than 1–5 / −1 (also `"2nd"`, `"segundo"`, `"last"`, `"último"`), an unknown `weekday` (English or Spanish, plural and accents accepted), no readable `start` (`parse_hhmm`: `"17:00"`, `"5 PM"`, unquoted `17:00`), a duplicate `key`. **Noted, still shown**: an unreadable / not-later `end` (→ one hour), a `skip_dates` value that is not a date, or not one of the event's own days — e.g. the Sunday or the 1st Saturday for a 2nd-Saturday event — (ignored; the note names that month's real date), a `months_ahead` outside 1–24 (→ 6), a `url` / `online_url` that is not http(s) (left out; the event links to `/events/`), a `host` other than neta / lv / gv (also "La Viña", "Grapevine", "NETA 65": `common.event_host`; → `neta`), a `meeting_id` that is not one (letters, digits, spaces, dots, dashes; → left out) or that is not the Zoom meeting `online_url` opens (shown, the chair checks), a `contact` that is not a plain e-mail address (`_EMAIL`; a leading `mailto:` is dropped; → left out), a `flyer_match` Python cannot compile or that matches an empty name (`.*`) (→ no flyer). A missing `key` is made from the title; keys are slugified and cut to 32 characters so the card anchor keeps its date. An exception anywhere is caught in `build_events` (same as `meeting:`). The usable entries stay in `ctx.series` for `build_events`. |
| `build_data.series_flyers()` / `pick_flyer()` | `flyer_match:` → the committee's Drive files (raw `drive.json`, never a bulletin post) whose title or file name matches the pattern (`re.IGNORECASE`, the name NFC-normalized and also tried without accents, so `vi[nñ]a` finds "Viña", "Vina" and a Mac's decomposed "Viña"), newest first (`date`, else `first_seen`). Found by pattern, never by the exact name: La Viña's flyer was renamed after upload and is still found. Each date takes a file dated that day (`extra.event_date`), else one of its month (`event_month`), else the newest undated one; none → no flyer, no problem. |
| `build_data.recurring_events()` | `meeting.upcoming_rule_dates()` → the next `months_ahead` dates **plus** the dates of the last 90 days. One event per date: id `ev:recurring:<key>:<YYYY-MM-DD>`, source `committee`, category `recurring`, fixed i18n (the config's `title`/`title_es`, `summary`/`summary_es`; a missing language is machine-translated once and marked in `machine`) and a rule-written `recurrence_label` (the committee meeting's wording: "Every second Saturday of the month · 5:00 – 8:00 PM") plus `extra.rule`, from which the pages write the same line with the meeting's helpers, adding its time zone ("… Central time" / "…, hora del Centro"). Each date also carries `host`, `online_url` + `online` + `platform` (`events_external.platform_of`: "Zoom" …), `meeting_id`, `contact` and its flyer (`flyer_url`, `flyer_thumb`). `build_events` marks the past ones `past: true` without counting them in `PAST_EVENTS_KEEP`. Never `is_new`, never in `whatsnew.json` (`SCHEDULED_EVENT_CATEGORIES`). |
| `/events/` (`normalizeEvents` in `eleventy/filters/committee.js`) | Every upcoming date as its own card in the **NETA 65 events** group (`GROUP_OF.recurring = "neta"`) — or, with `host: lv` / `gv` (`eventHost`), in the **GV & LV calendars** group, in that magazine's colour (`event-tone.js`: the host comes right after the committee meeting) — with an "Every month" badge, the day rule, the place and the external "Event details" link; "add to calendar" per date. Online only (no `location`): "Online on Zoom" with a **Join online** button and no map pin; `meeting_id` → a "Meeting ID" line (`ev.meetingId`) and a line in the calendars' description; `contact` → a mailto: line of its own (`ev.contact`, mail icon, `tap-link`; checked again to be a plain e-mail address — it never sits only in the 3-line summary) and "Contact: …" in the calendars' description; the **Join online** button says "(opens a new tab)" to screen readers; the flyer → its picture and "View flyer". The "Show every monthly date" switch is offered for every group that has a monthly series. Search engines (JSON-LD) get La Viña / AA Grapevine as the organizer of a `host: lv` / `gv` event. Past dates are left out of the *Past events* list (`whereNot("recurring", true)`). |
| Calendar feeds (`events-ics.11ty.js`) | One `VEVENT` per date — like the committee meetings — with a stable `UID` from the id (`ev-recurring-<key>-<date>@neta65-gvlv`, `-es` in the Spanish feed), UTC `DTSTART`/`DTEND`, `LOCATION` (the Zoom link for an online-only event), `URL` (the entry's `url`; without one — the data's `/events/` — the date's card, `/events/#ev-recurring-<key>-<date>`, while the date is still to come, and `/events/` itself once it has passed: the page lists only a series' dates still to come. `normalizeEvents` `detailsUrl`: also the "Details:" line, the Google / Outlook links and the card's ".ics file"), `ATTACH` (the flyer), `CATEGORIES` (the group: "Grapevine / La Viña calendar" for `host: lv`), and the rule line with its time zone ("Every fourth Thursday of the month · 2:00 – 3:00 PM Central time" / "… 2:00–3:00 p. m., hora del Centro": a calendar shows `DTSTART` in its reader's own zone, so a bare "2:00 PM" beside it would read as theirs — `recurrenceText`, the words of `report.c_time`), the online link, the meeting ID and the flyer in `DESCRIPTION`. Chosen over one `RRULE` series because UTC instants need no `VTIMEZONE` (an `RRULE` on a UTC start would drift an hour at every DST change; with `TZID` it needs a `VTIMEZONE` that Outlook.com handles unevenly), a skipped month is simply absent (no `EXDATE` quirks), and each date can change on its own. The feed carries the 90 past days (subscribers keep them, as for the committee meetings) and `months_ahead` dates ahead; `REFRESH-INTERVAL` 12 h rolls new dates in. |
| Home, search, GV/LV report (`/monthly/#report`) | Only the **next** date of each series (`extra.series`): `homeEvents` (links to the card on `/events/`; the next date of every series **of ours always keeps a place** in the home row of 4 — the other places go to the soonest one-off events, at least one of them when there is any, then at most one more committee meeting; shown by date. A series a host holds — `host: lv` / `gv`, La Viña's workshop — keeps no place of its own: its next date competes by date with the one-off events, so it never pushes off one of our workshops that comes sooner), the search index (one `event` entry, found by "every month" / "cada mes" too; `src: "lv"` / `"gv"` for a host's event; its line is the repeat line, then the place — "Every fourth Thursday of the month · 2:00 – 3:00 PM Central time · Online on Zoom" — its next date being in the result's meta line, and in its keywords (`x`, searched, never shown), so "october" / "oct 22" / "22 octubre" find it as they find a one-off event), the report (`report.js` → `upcomingEvents`). Online only: home `homeEventInfo.online` ("Online on Zoom" with the video icon), the search line ("Online on Zoom"), the report `eventWhere` ("(Online)"). |
| Monthly toolkit, monthly digest, e-mail | The toolkit (`/monthly/YYYY-MM/`: its dates, poster and message — `monthModel` in `eleventy/filters/monthly.js`) lists every date of its month; on this month's page a date is marked "Over" once it ends (`overAt`, `src/assets/js/monthly.js`). A date row carries `host` (its colour) and `online`: without a city the row, the poster and the message say "Online" / "En línea". The monthly digest (`community.js` → `monthEventsHeld`) and the e-mail (`send_digest.month_events`) list last month's dates that took place — days only, no "every month", "Online" for an online-only one; a date without a page of its own links to its flyer (its card on `/events/` is gone) — and never count them as news (`total_count`), so a month with only the booth sends no e-mail. |
| Outside calendars listing a date (`same_event`, `merge_calendar_duplicates`, `series_listing_notes`) | La Viña's own calendar (`events_external`) lists every date of its workshop as an all-day "Taller Mensual" whose place is the Zoom link; an `.ics` feed may list it too. A listing on a date of the series is the same event (the **online room** route: the same Zoom meeting the same day — `online_room` / `event_rooms`) and is left out: ours wins (`extra.also_on_calendar` / `calendar_match`, or `also_in_feed` / `feed_match` = `online` for a feed). A listing in the same room on **another day** of a month whose rule date is still to come and not skipped stays on the page, and `series_listing_notes` adds a line to `problems.recurring_events` (→ a *Settings problem* in the run summary) naming the skip date to add — unless a calendar lists that month's rule date too (it did not move; the other listing is another session: no note). A skipped month is left to the host's calendar (no note), and its listing there is that month's date of the series: `series_moved_dates` keeps it as the calendar's event (its day, its link, "Time not listed") with the series' fixed title / summary i18n (`_fixed_i18n`, the series' `machine`), `host`, `online_url` / `platform` / `meeting_id` / `contact`, the date's flyer and `extra.series_of` = the series key — committee.js `seriesOf`: named in the series' "Then …" line (`cmCollapseRecurring`), its words count as the committee's own (`ownLangs`: no language pill). A listing over several days in that room (a convention) is left alone. A dated Drive flyer matching `flyer_match` on a date of the series is that date's flyer (`series_dated_flyers` drops the one-off event); on another day it stays a one-off event and takes the series' `host`, Zoom link, platform, meeting ID and contact. |

## Events: several days, "to be confirmed", places, outside calendars

Chair-facing instructions: [content/events/README.md](../content/events/README.md) and the
[README](../README.md#6-bulletin-posts-and-events-without-drive-optional); the data fields:
[DATA_SCHEMA.md](DATA_SCHEMA.md) (§3, events).

| Topic | How it works |
|---|---|
| Several days (the Area assemblies, Fri–Sun) | A content/events file with `start: 2027-03-19` and `end: 2027-03-21` (dates only) is an all-day event whose `end` is the **last** day. `build_data.event_end_ts` puts its end at 23:59 Central on that day (like every event it keeps `past: false` one more day: the `build_events` cutoff is now − 24 h); on the pages `normalizeEvents` (`eleventy/filters/committee.js`) sets `multiDay`, a range tile ("MAR · 19–21 · Fri–Sun"), `rangeLabel` ("Fri, Mar 19 – Sun, Mar 21, 2027" / "Vie, 19 de mar – dom, 21 de mar de 2027") and `timeLabel` "3 days"; the card's `data-cm-expire` is midnight after the last day. `/events.ics`, `/es/events.ics`, the per-event ".ics file" button (`CM.downloadIcs`) and the Google / Outlook links use DATE values with the **exclusive** end (`DTEND;VALUE=DATE:20270322`). Home (`homeEventInfo`, `homeEvents` via `chicagoDayEndMs`), the district report (`eventWhen`: "Fri, Mar 19 – Sun, Mar 21") and the monthly toolkit (`dateRow`, over at midnight after its last day) show the range; the monthly digest and its e-mail (`cmEventDays`, `event_row`) list it with its days only, in the digest of the month it **starts** in, once it has started. Since October 2026 a Drive flyer named with a range of days ("Assembly March 14 - 16, 2027.pdf", "2027-03-19 - 2027-03-21 Spring Assembly.pdf", "Asamblea del 14 al 16 de mayo de 2027.pdf") is one event over those days too: `drive.name_date_range` (`common.date_range_from_text`) → raw `extra.event_end_date` (the last day) → `build_data.flyer_events` makes it all day to the last day, or from the start time to the end time on the last day (with a start time and no end time, the end is the last day as a date, which `eventSpan` / `event_end_ts` treat as the end of that day); its title is the name without the dates. A timed event that only runs past midnight is not "several days" (it must last more than 18 hours). From 12 to 18 hours it stays a one-day card, but its time line names the day and date at both ends (`central-time.js` `timeRange`, through `committee.js` `clockRange`: `/events/` `timeLabel` and the home card's `when`): "Fri, Oct 16, 7:00 PM – Sat, Oct 17, 12:00 PM CDT" / "Vie, 16 de oct, 7:00 p. m. – sáb, 17 de oct, 12:00 p. m. CDT"; up to 12 hours (`OVERNIGHT_MAX_HOURS`) it is a night, "8:00 PM – 1:00 AM CDT". `timeRange` says the zone once only when both ends have the same zone, so on the night the clocks change both ends carry theirs ("1:00 AM CST – 3:00 AM CDT"). |
| Outside calendars' event pages (`events_external.parse_event`) | A Grapevine or La Viña event page with structured data (JSON-LD) gives its dates. Without it, since October 2026 the written date is read whole, a range too ("October 2 - 4, 2026", "Oct. 30 – Nov. 1, 2026", "del 2 al 4 de octubre de 2026"; with a time or a weekday between the days, the last piece after a dash that holds a whole day is the end: "Thu, 10/01/2026 - 12:00 - Sun, 10/04/2026 - 12:00"), day first on aalavina.org. A numbers-only date that could be read two ways is read the way that gives the first day in the page's own address (`/get-involved/events/YYYY-MM-DD/…`, `EVENT_URL_RE`); when neither does (an event moved, its address kept), the site's own order stands (La Viña: day first) and a note goes to `stats.warnings` (at most 10, into the run summary's *Notes* and `/status/`): "<site> event <slug>: “10/05/2026” could be read two ways and neither gives the date in the page's address (2026-10-02) — read as 2026-05-10. Check the event's date". |
| Details to be confirmed | content/events `tentative: true` (also `yes`, `sí`) → `extra.tentative: true` (announcements.py); an outside calendar's `STATUS:TENTATIVE` does the same. Shown as the badge "Details to be confirmed" / "Detalles por confirmar" (`ui.tentativeBadge`, class `badge-tbc`: dashed outline; the explanation is its tooltip and screen-reader text) on `/events/` cards, the home row, the "next event" card of `/announcements/` and search results (index flag `tb`); as " · Details to be confirmed" on the monthly toolkit's date rows, poster and message, and in the district report. The monthly digest lists only events that took place, so it never shows it. Calendar files: `STATUS:TENTATIVE` (every other event `STATUS:CONFIRMED`), and the first line of the description says it (Google / Outlook links cannot carry a status). Deleting the line makes the event confirmed on the next run. |
| The place in both languages | A place is **never** machine-translated. content/events `location_es` (in an English file) / `location_en` (in a Spanish one) → `extra.own_i18n.location` → build_data writes `i18n.location` (`location_pair`). A place that is not known yet ("Venue to be announced", "TBA", "Lugar por anunciarse", "Por confirmar" — `location_is_tba`) gets `extra.location_tba: true` and, when the other language was not written, the site's own words ("Lugar por anunciarse" / "Venue to be announced"). Such a place is shown as plain italic text with an hourglass (no map pin), is left out of `LOCATION` in the calendar files and of the Google / Outlook links (it goes into the description instead) and of the past-events list. Every page reads `i18n.location[lang]`, falling back to `extra.location`. |
| Outside calendars (`sources.ics_feeds`) | `build_data.ics_events()`: per feed ONE request (see [Crawl politeness](#crawl-politeness)); the answer is `ok` (a calendar file that parses), `blocked` (HTTP 401 / 403 / 429, or Cloudflare's "Just a moment…" check: `cf-mitigated: challenge`, `challenges.cloudflare.com`) or `error`. Since October 2026 `fetch_feed`'s message for a blocked feed is plain, without "robot" or "Cloudflare": "<host> answered with a bot check (HTTP 403) — nothing is wrong on our side", "<host> asked for fewer requests (HTTP 429) — …" or "<host> refused the request (HTTP 401/403), as its bot protection does — …", and `ics_events` adds "; the last good copy is kept" or "; there is no good copy of it yet". The last good copy of each feed is kept in `data/state/ics_feeds.json` (with `attempted`, `state`, `http_status`, `error`, and `fetched` = the last success) and used while the feed fails. `_parse_ics` reads The Events Calendar's export (VTIMEZONE + `DTSTART;TZID=America/Chicago`, `UID` `<post id>-<start>-<end>@neta65.org`, `URL` = the event page, `LOCATION` without ", United States", `ATTACH;FMTTYPE=image/…` = the flyer, `CATEGORIES` → tags; CANCELLED left out, RRULE expanded (EXDATE and RECURRENCE-ID overrides applied, UNTIL in any form), an all-day `DTEND` is exclusive → last day). `category:` `neta65` (or `ics`) puts the events with the NETA 65 events; `gv-calendar` / `lv-calendar` with the GV/LV calendars. Health → `status.json` `feeds` → the "Other calendars we read" card on `/status/` and the informational block of the run summary. Feeds are not content sources: a blocked feed never counts as failed, never becomes a warning and never opens the "stopped updating" issue. |
| One event, several sources | `merge_feed_duplicates()` in `build_events`, against everything already on the calendar: content/events files, dated Drive flyers, the committee meeting and every `recurring_events:` date (so a feed that also lists the CityWide Dallas booth or the meeting never doubles them); the Grapevine / La Viña calendars (`events_external`) go through `merge_calendar_duplicates()` — the same test, ours wins, nothing copied from the listing (those pages give little more than the day). Two events are the same only when they **start the same local day** and either (1) link the same event page — `event_url_key()` ignores the scheme, `www.`, the trailing slash, `?query` and `#fragment` (`neta65.org/event/<slug>`) — or (1b) meet in the same **online room** (`online_room`: the Zoom meeting ID whatever the server, path form or passcode; a Google Meet code; else host + path — and a `meeting_id`), unless both give a time more than 2 hours apart or one runs over several days; a listing that gives only the day counts in this route only against a date of a monthly series or the host's own event (`_room_owner`: category `recurring`, or `extra.host` `lv` / `gv` — La Viña's "Taller Mensual" against its workshop), so our workshop at a one-day virtual assembly, in the assembly's own Zoom room, is still its own event (the title route decides, as for an assembly in a building), or (2) have the same shape (`_same_shape`: both all-day, or both timed and starting at most `TITLE_MATCH_MAX_GAP_H` = 2 hours apart; never one over several days against one on a single day), are not in two different cities, and have titles that name the same event (`similar_titles`: the telling words — the kind of event included: "workshop", "booth", "assembly" — shared / all ≥ 0.75, the shared city and the year ignored, `lv` / `gv` expanded, "grapevine", "la viña", "neta 65" ignored; word for word when a city is not known, e.g. a place "to be announced"). "LV Writing Workshop" ~ "La Viña Writing Workshop (in Spanish) — Fort Worth"; not ~ "LV Recording Workshop"; "Grapevine Workshop at the Spring Assembly" (7 PM on the assembly's Friday) is **not** the assembly. The same event page on another date is another date (a series, a page used again for a new workshop, or a date that changed): the feed event is kept. The hand-written event wins and keeps its own Spanish; the feed only fills what it leaves out — `flyer_url` / `flyer_thumb`, `online_url` and the event-page `url` only on a sure match (same page, same online room, or the same start); a missing place, or one "to be announced" (on a sure match: the feed's venue replaces it); a missing end of the same kind — recorded in `extra.also_in_feed` + `extra.feed_match` (`url` / `online` / `title`). Nothing is copied onto the meeting or a recurring date. What the feed says that a file does not (its event page on another date while the file is still upcoming, another start time, a venue the file calls "to be announced") → `feeds[].notes` → a *Check:* line and a `::notice` in the run summary, so the chair updates the file. The same event in two feeds is kept once. `feeds[].duplicates` counts them. Proven by `tests/test_events_feeds.py` with the six real workshop pages and the negative cases (a workshop / booth on an assembly's first day, with a known and with a TBA venue; a workshop in a one-day virtual assembly's Zoom room; the same page on another date; the booth and the meeting in a feed); the La Viña workshop and its listings by `tests/test_recurring_events.py`. |
| neta65.org is blocked | Since Sept 2026 every automated request to neta65.org (the iCal export, `webcal://…&ical=1`, `/wp-json/tribe/events/v1/events`) gets HTTP 403 "Just a moment…" from Cloudflare. The site does not try to get around it. The fix is on the Area's side: a Cloudflare WAF custom rule with the action **Skip** for requests whose query string contains `ical=1` (or whose User-Agent is the robot's); the next daily run then reads the feed by itself. Until then a NETA 65 workshop or assembly shows on the Events page only after the committee adds it to `content/events` by hand (the /status/ card says so and links content/events/README.md). |

## When Grapevine announces new prices

Every price on the site comes from the official stores (`scripts/sync/shop.py`: the subscription prices in every
full daily run, the Book of the Month too — and in the morning refresh on the 1st and the 15th). So the site follows
a price change at its next read — but nothing would announce it, and from the day it starts until a read after the
store's own update (and longer in pages the app saved for offline use) the old 1-year prices would still show. One
block in `config/site.yml` → `price_changes:` covers both (the README's [When Grapevine announces new
prices](../README.md#when-grapevine-announces-new-prices) is the chair's version; the data fields are in
[DATA_SCHEMA.md](DATA_SCHEMA.md) → shop.json; the first one, January 1, 2027, is the model).

**Checklist** (the day the letter arrives):

1. The letter in the Panel's Drive `notes` folder, its name **starting with the letter's own date** —
   `2026-10-01 Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf` — so the Portfolio dates it by the
   letter, not by the effective date in its name (`drive.build_item`: the first date in the name wins). Its Spanish
   Portfolio title: `data/translations/overrides.yml` ("Committee Portfolio" block). A title with "La Viña" in an
   English name is English (`drive.py` detects the language with the magazine names left out: translate.py
   `detect_language`).
2. A block in `config/site.yml` → `price_changes:` — `effective`, `announced`, `notice_until`, `source` /
   `source_es`, `doc_match` (a pattern that finds the letter among the Drive files — make it match the old and the
   new file name), `yearly` (the new 1-YEAR prices by magazine and format, exactly as announced), `books_more`.
   Only what the announcement names: never add the 2- or 3-year, monthly or Complete plans by guesswork.
3. The bulletin posts, written by hand with their own Spanish (`content/bulletin/`, `title_es` and a several-line
   `summary_es: |`): the heads-up (dated the day it was announced, `pinned`, `expires` the day before it takes
   effect) and "now in effect" (`publish` and `date` on the day, `expires` with `notice_until`). Informative, never
   a sales push: what changes, AA Grapevine's own reason, what it means for groups (the treasurer's budget, a
   heads-up at the business meeting), the links to `/shop/#subscriptions` and to the letter — and no claim the
   letter does not make (renewals bought before the day, other plans, other regions, "literature" when only
   Grapevine and La Viña books change). Open each language with one sentence that holds every new price: the home
   page's card, What's New and the feed show the first ~320 characters as plain text, where a list runs together
   into one line (the two posts for January 1, 2027 do this). The heads-up is in the
   monthly e-mail of the month it was posted; the e-mails of the next months, through the day's month, carry one
   pointer row ("Grapevine and La Viña prices change on …" / "New … prices since …") — so do the monthly toolkit's
   messages and the GV/LV report.
4. After the save: the Actions run summary has no *Settings problem (price_changes)*; `/shop/` shows the notice
   above the subscription prices and a line on each Book of the Month card. Preview the day itself before it comes
   (below).

**How it works**

| Where | What happens |
|---|---|
| `scripts/sync/price_changes.py` `specs` | Checks the block. **Skipped** (reason in the log and in `status.json` → `problems.price_changes`, a *Settings problem* in the run summary): not a mapping, no `effective` date, a `key` used twice, nothing to change (no valid `yearly` price and no `books_more`). **Noted, still applied**: an `announced` that is not a date or later than `effective` (→ no advance notice), a `notice_until` that is not a date or before `effective` (→ 30 days), a `yearly` publication other than gv / lv, a format other than print / digital / complete, a price that is not a price (0, a word, over $1,000), a `books_more` that is not an amount, a `doc_match` that is not a valid pattern (→ no link). Dates may be quoted or not. Never raises. |
| `scripts/sync/shop.py` `price_memory` | After each store read: the affected 1-year prices as read (`remember`) — and, for a change with `books_more`, each Book of the Month's regular price under `botm:<pub>:<sku>` (the offer and its book) — into the raw envelope's `price_memory`, keyed by the effective day. Every run until the day before updates the prices it read; a plan or book it did not read (one card missing from a listing that day, a listing that did not answer) keeps its last price, and changes that start on the same day share one memory. Frozen from the day on (the clock is read after the store reads). The Book of the Month items get `extra.read` (the day). |
| `build_data.build_shop` | Marks each affected plan `change {key, new, stale}` (`plan_change` → `price_changes.resolve`): stale = the store price predates the change — any build before the day; after it, while the stores have not been read since (`attempted` before the day) or the price read equals the remembered one. Marks each Book of the Month `price_stale` (`price_changes.book_stale`): read on or after the day of a book price change in effect, the same book still at the regular price remembered from before it. Writes `price_changes[]` with the days, the switch moments `at` (00:00 Central: announced, effective, the day after notice_until) and the notice's rows. |
| `eleventy/filters/shop.js` | `shopPriceChanges` (the notices), `shopSubs` (each plan type: its terms now and — while a change is still ahead — `swap`, its terms from that day: the announced price where the store data is stale, no "save" sums against an announced price, the 1-year volume prices left out with a note that sends readers to the store — it claims nothing about them), `shopBotm` (the books line before the day; from it a Book of the Month price read before the day — or after it but still the old one, `price_stale` — is not shown: `botmPriceState`; a new book, or any other price, shows the store's), `shopWindow` (the window a part shows in), `shopPriceChangeIn` (the change to mention for a month or a day: the toolkit's message, the report, the digest). Clock: `monthly.js nowDate` (`MONTHLY_NOW`). |
| The pages | `/shop/` (`priceNotice` above the prices — its table turns into one small block per plan on a phone with larger text, so the new price is never cut off; `termList` / `volumeBox` in both states; the Book of the Month cards; the prices note), the monthly toolkit (`monthModel.price` → the month's message — the months from the announcement to the day, and the day's month; "Keep up all month" on the current month, with a link that says what it opens), the GV/LV report (`report.js shopSection`: AA Grapevine's list of new prices to pass on — "New prices from …" before the day, "New prices since …" after it; the section's `after` text from the day — `src/assets/js/report.js swapTexts`), the monthly digest and its e-mail (one pointer row after the toolkit's: `community.js digestPrice` = `send_digest.py price_change`, compared by `tests/test_price_changes.py` → Digest), GVR / RLV 101 (the Book of the Month example). |
| Between builds | A part written with `ui.when` (macros/ui.njk) carries `data-gv-when` + `data-gv-from` / `data-gv-expire`: `app.js GV.expire` shows or hides it at the moment, by the visitor's clock (instants, so a browser in any time zone switches at midnight Central), every minute and when the page is shown again; `base.njk`'s first head script does the same while the page is parsed (a MutationObserver until DOMContentLoaded), so the old state never paints first. A part's two states are written one right after the other and swap together (the new one waits while the old one holds keyboard focus). A page left open over the moment swaps while it is open: a one-time reflow where the two states differ in height (the "Save …" lines go, for one). Without JavaScript the build's state shows (the site is rebuilt every morning). |

**Preview a day before it comes** (scratch only — `data/**` is the bot's: restore it with `git checkout -- data/raw
data/site data/state data/translations/cache.json` afterwards, keeping any `overrides.yml` edit). Build the site data
as on that day — `build_data` reads the clock through `datetime`:

```python
from datetime import datetime, timezone
from unittest import mock
from scripts.sync import build_data as B, meeting as M
fake = datetime(2027, 1, 1, 14, tzinfo=timezone.utc)          # 8 AM Central on the day
class Clock(datetime):
    @classmethod
    def now(cls, tz=None): return fake.astimezone(tz) if tz else fake.replace(tzinfo=None)
with mock.patch.object(B, "datetime", Clock), mock.patch.object(M, "datetime", Clock):
    B.main(["--no-translate"])
```

then the pages as built that day (the shop's windows, the toolkit, the report and the digest read `MONTHLY_NOW`):
`MONTHLY_NOW=2027-01-01T14:00:00Z PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy`. The browser's own clock decides
the switch: a page built on Dec 31 shows the new prices from 00:00 Central on Jan 1 (Playwright:
`page.clock.install(time="2027-01-01T00:30:00-06:00")`). Tests: `tests/test_price_changes.py`.

**After the day:** the stores update their pages; the next read shows their prices (equal to the announced ones,
or the store's if it differs — the store wins). The block can then be deleted (left in place it does nothing more
once its notice has ended and the stores' prices are new). Deleting it before the stores update would show their
old prices again until they do. The tests check the live settings only for mistakes (and skip that check when there
is no block), so adding the next block or deleting this one keeps the Code check green.

## Crawl politeness

| Host | Rule we follow | Numbers |
|---|---|---|
| www.aagrapevine.org + www.aalavina.org | robots.txt obeyed (a robots.txt that answers 5xx or 429, or nothing after two tries, closes its host for 10 minutes — `ROBOTS_RETRY_S`, RFC 9309 — and is asked again after; a 4xx allows everything; this holds for every `PoliteSession`, also the meeting lists' and Instagram's web pages); `Crawl-delay: 5` applied **across both hosts and all modules together** (one `shared_session()`); **each page at most once per run**: the session keeps every page it read for the rest of the run (`PoliteSession.get_text` / `remembered`), so what one module read — the home pages (quote, podcast discovery), `/BOTM` and `/libro-del-mes` (shop), `/grapevine-weekly-open`, the sitemap (external events) — is reused by the others and by the crawl; honest User-Agent with a contact URL; conditional GETs; skip login/cart/search/paywalled paths | 5 s between requests → 720 requests/hour max. Default 40 min/day ≈ 450 pages/day. **First coverage is complete** (Sept 2026): 3,445 pages known, 3,441 crawled, queue empty (the other 4 links return errors and are retried now and then), 130 PDFs. From now on the daily run only re-checks pages and picks up new ones — a 300-minute catch-up run is only needed after `crawl-state.json` is deleted. Pages are re-checked every `recheck_days` (21) unless the sitemap says they changed; hub pages daily. PDFs: ≤ `pdf_details_per_run` (40) downloads/run, ≤ `pdf_max_mb` (60 MB) each. |
| YouTube | Fixed set of feed URLs, ~1 s apart, short timeouts; yt-dlp time-boxed (6 min/run) | ~10–90 requests/day |
| Instagram | Public embed pages only (unless the official API token is set), ≤ a few requests per account per day, post-embed look-ups capped by `enrich_per_run`, plus the removal sweep's ≤ `recheck_per_run` (5) post embeds and at most one control request per account and kind (post or Reel) that still needs proof — 4 at most a full run; no hammering on HTTP 429 (it stops the sweep). Instagram's terms discourage automated collection — `anonymous: false` turns all of it off | ~2–36 requests/day |
| Google Drive | One request per folder per run (≤ 800 folders, 15 min budget) | tens of requests/day |
| Podcast feeds | One RSS request per show (2 shows); a few audio HEADs for vanished episodes | ~2–10 requests/day |
| Outside calendars (`sources.ics_feeds`, e.g. neta65.org's workshop calendar) | One plain GET per feed per run with the robot's own User-Agent (`sources.crawler.user_agent`), no retries, no robots.txt fetch (a published calendar file is meant for calendar programs); a feed is asked again only 20 hours later, whether it worked or not (`ICS_RETRY_HOURS_*` in `build_data.py`; the last good copy is used in between), so push-triggered and manual runs add nothing. **Never** get around a bot wall (no browser automation, proxies or faked headers) | ≤ 1 request/day per feed |
| Link check (weekly) | lychee: 2 concurrent / 1 s apart per host; config links via `PoliteSession` | a few hundred requests/week, none to the two magazine sites except ~20 config links at 5 s |
| The Morning check (`scripts/ops/morning_check.py`) | Asks a magazine only while its quote on **our** site is late: from 3 h 30 min before the goal to 90 minutes after (2:00–7:00 AM) one fresh request of its home page (`get_text(reuse=False)`) per late magazine every 10 minutes, and once per check after that, through the same shared polite session (robots.txt first, 5 s apart). Its own site's `build.json` is read with plain requests | usually 0 a day; at worst 31 page requests per late magazine over a morning when the quote is very late (from 2:00 to 7:00 AM; 16 from the alarm at 4:30; one per late magazine for each later check), plus each site's robots.txt. Each morning refresh reads the two home pages itself — about 20 requests on the 1st and 15th, only in the first refresh of the day (shop, articles) |

## Failure handling (design guarantees)

1. **Nothing disappears on a bad day.** `merge_items()` keeps every known item; a module that fails
   writes `ok=false` + `error` and keeps its previous items. Items are only marked `gone` after an
   explicit confirmation (404/410, oEmbed, a successful folder listing without the file). A PDF needs
   **two** failing checks at least 24 hours apart (404/410, or an HTML page where the file was), so one
   bad answer during a site update never hides it; a gone PDF that a page still links is checked again
   after a week, then monthly, and returns when it answers. A PDF on another website whose server has
   not answered at all for 30+ days (after 4+ tries) is gone too; files on aagrapevine.org /
   aalavina.org are never retired just because the site is down. What is and is not guaranteed since
   October 2026 (a bad day can also look like success):
   - **A sudden drop is held for one run** (`common.save_raw`): a source that says ok but finds no live items
     where it had some, or fewer than half once it had `DROP_GUARD_MIN` = 10 or more, keeps the missing ones next
     to the new ones and is marked `held` (`/status/` **On hold**); the next run that still misses the same items
     removes them (`changes.confirmed`), so a real removal is exactly one run late. `held.ids` lists **every**
     held id (sorted), so a hold whose source keeps losing a few more items each run is still confirmed the next
     run, the new losses judged on their own; a run that fails (`ok: false`) during a hold also puts back the held
     items its list misses or marks gone (crawl.py writes its list on a failed run too), so only a run that works
     confirms a removal. Not for the sources in
     `DROP_GUARD_EXEMPT` (announcements, manual_events, events_external, editorial, instagram, writers_archive —
     each with its reason in the code; most have a guard of their own) nor for a source switched off in the
     settings. A drop that stays under those thresholds (say 40 % of a list) is **not** held.
   - **Drive**: a folder (or the root) that held files and lists empty is believed only the second time in a row
     (`empty_folders`).
   - **The document search**: a hub or kit page is retried at every run whatever it answered; one 404 keeps a
     page's PDF links (two, ≥ 24 h apart, drop them); another host is asked twice, and its other PDFs wait with no
     strike; a robots.txt that answers 5xx/429/nothing leaves the magazine sites' pages for the next run — and a
     run in which that kept the search from reading any page while pages were due is a **failed** run
     (`crawl.run_verdict`: "no page could be read: robots.txt of <host> (<problem>) did not answer properly — site
     down?"), so its last success stays and a week of it reaches the failing-sources issue, like the older "no page
     could be fetched (N errors) — site down?"; a PDF that crashes or hangs the reader is skipped with a back-off,
     in a child process, and the run goes on.
   - **An unreadable raw file** (a hand edit, a bad merge) does not empty its section and is never rebuilt from
     scratch: the file stays as it is, `run_all` does not run that source's module (`common.UnreadableRaw`; nothing
     is written over it), and `build_data` keeps the last build's data for it until a person restores the file from
     git. A raw file that went **missing** while the last build had items from it is kept the same way until an
     update of that source works.
   - **Instagram** removes a post only after two "not there" answers 12 h apart, and only when a post embed of
     the same account and kind (post or Reel) worked after them in the same run.
   What still removes items at once: a source that really lists fewer items within the thresholds, a file the
   committee deleted from `content/`, and an Instagram account's posts beyond `keep_per_account`.
2. **One broken source never stops the others** (`run_module()` catches everything and records it).
3. **Atomic writes**: `write_json()` writes a temp file then `os.replace()`, so a killed run never
   leaves half a JSON file (`*.tmp` and half-downloaded `*.part` thumbnails are git-ignored, so the
   data commit never picks them up).
4. **Partial progress is kept**: the commit step runs even when the sync step failed, hit its
   time budget or the run was cancelled, so e.g. 35 minutes of crawling are not lost.
5. **The site always deploys** the latest committed data, even if today's sync failed — as long as the build and
   the tests pass on that commit (`publish` needs both).
6. **A bad code edit cannot take the site down**: the build or the tests fail (job `tests`, since October 2026:
   the offline tests run before every publish of new code), nothing is published, and GitHub Pages keeps serving
   the previous deployment. The data commit is still made, so the next good run publishes everything at once. A
   slip in the committee's own files (`content/`, `config/`, the glossary, the overrides) never stops publishing
   through the tests (they test the code; `CONTENT_TESTS` are the Code check's): the sync and the build leave out
   what they cannot read and say so (the run summary's *Settings problems* and *files to fix*), and the Code check
   goes red on that push. What the build itself refuses still stops it: a `config/site.yml` YAML cannot read, and
   under `I18N_STRICT` a mistake in `config/carry.yml`, `orientation.yml`, `history.yml`, `expenses.yml` or a deck.
7. **Health is visible**: `/status/` page, the run summary table, `::warning` annotations, the badge —
   and a source that has not updated for 7 days opens the issue *"A content source has stopped
   updating"* (the `report` job), because a run stays green while only one source fails.
   GitHub's failure e-mails for the *scheduled* runs (Website update, the hourly backstop of
   Morning check (new day by 5:30 AM), Monthly e-mail digest, Weekly link check) go to the user who
   last enabled each workflow (or last edited its `cron:` line): after a hand-over, or after someone
   else pushed a `cron:` change, the new chair disables and re-enables all four. The runs the morning
   alarm starts e-mail the owner of its key. The runs the Morning check starts (as `github-actions[bot]`) e-mail
   nobody, and a timed run only that one user, so since October 2026 two such runs failing in a row open the
   issue *"The website update keeps failing"* (the `report` job's second step), which closes itself after the
   next run that works.
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
do it only if you understand it, with the scheduled workflow disabled and all your own commits pushed:

```bash
git fetch origin                                  # GitHub's main has the bot's latest data commits
git log --oneline origin/main..main               # must print nothing; otherwise push your commits first
new=$(git commit-tree "origin/main^{tree}" -m "Fresh start: history squashed on $(date +%F)")  # GitHub's files, no history
git push --force-with-lease=main:"$(git rev-parse origin/main)" origin "$new":refs/heads/main   # refused if someone pushed meanwhile: start again at the first line
git checkout -B main origin/main                  # your copy on the new history
```

Then **Actions → Website update → Enable workflow**, and **Run workflow** once (and
**Code check (tests and test build) → Run workflow**): a force-pushed history with a new first commit starts
no push-triggered workflow by itself.

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
python -m scripts.ops.morning_check --check-only --site https://neta65.github.io/aagrapevine
                                                   # the Morning check's view of the live site: what it would
                                                   # do (no token needed; asks a magazine — one request each,
                                                   # plus robots.txt — only from 2:00 AM Central, and only
                                                   # when today's build is up with a quote that is late)
python -m scripts.ops.gate_tests                   # the tests Website update runs before it publishes
ONLY=library,search npx @11ty/eleventy             # build just some pages (fast)
```

Build exactly as GitHub Pages does for a project site:

```powershell
$env:PATH_PREFIX = "/aagrapevine/"; npx @11ty/eleventy      # PowerShell
```
```bash
PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy                # macOS / Linux
MSYS_NO_PATHCONV=1 PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy   # Git Bash on Windows
```

(Git Bash rewrites values that look like paths — `/aagrapevine/` becomes
`C:/Program Files/Git/aagrapevine/` — unless `MSYS_NO_PATHCONV=1` is set.)

**Service worker (offline use).** The built site registers `/sw.js` (README → "Install the app,
offline use and Data saver"). It works on `http://localhost` too, and pages you open while testing are
kept in the browser. Styles and scripts are linked as `…?v=<build.version>` — a fingerprint of the code
(`src/_data/build.js` → `ROOTS`: `src/_includes`, `src/pages`, `src/assets` without `src/assets/cache`, `eleventy/`,
`eleventy.config.js`, `package-lock.json`; not `data/`, `config/`, `src/_i18n` or `src/_data`, which only change the
HTML), which is also the worker's version. To start from a clean first visit: DevTools → Application → Storage →
**Clear site data**.

**Browser checks and share pictures** (`tests/browser`, `scripts/ops/poster_share.py`; Playwright from
`scripts/ops/requirements-browser.txt`, never `playwright install` — they drive the Chrome or Edge already there):

```bash
pip install -r scripts/ops/requirements-browser.txt
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy --output=_site
GV_BROWSER_SITE=_site python -m unittest discover -s tests/browser -t tests -v   # GV_BROWSER_CHANNEL=msedge on Windows
POSTER_SHARE=1 PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy && python -m scripts.ops.poster_share _site
node scripts/ops/serve_site.mjs _site --prefix /aagrapevine/       # serve a build the way GitHub Pages does
```

(`MSYS_NO_PATHCONV` and `MSYS2_ARG_CONV_EXCL` only in Git Bash.) A check of a page that is gone fails with "/<page>
answered 404, not 200 — is it still part of the site?": change `MAIN_PAGES` / `LARGE_TEXT_PAGES` in
`tests/browser/test_site_in_browser.py` together with such a change.

**Tests that depend on the date** must pin their clock: the gate runs them before every publish of new code, so a
real-clock expectation would stop publishing on a date nobody chose. `tests/nodejs.py` `run_js(…, now="2026-10-06T15:00:00Z")`
(`fixed_clock`: stops Node's `Date` before any of the site's code is imported), the Tracker harness's
`make(…, { now })`, the page harness's `at`, or patching `common.now_iso`.

Please keep local test runs short (`--crawl-minutes 5`, `--dry-run`): the magazine sites ask for
5 seconds between requests and the daily job already visits them.

## Resetting state

| Goal | Do this |
|---|---|
| Redeploy without syncing much | Run *Website update* with **skip_crawl** ticked |
| Re-crawl the two sites from scratch | Delete `data/state/crawl-state.json` (commit), then run with `crawl_minutes = 300` |
| Re-read one source completely | Delete `data/raw/<source>.json` (loses `first_seen` dates → everything looks "new" for 14 days), then *Run workflow* with every box empty (a full run, so the source is read again at once). Until an update of that source works, every build keeps the last build's items and `/status/` shows it failed ("data/raw/<source>.json is missing — …"; after a failed update "… went missing and this source's update since did not work (…) — …"), and the translation cache is not pruned (since October 2026) |
| Restore an unreadable raw file | `git checkout <last good sha> -- data/raw/<source>.json` (or GitHub → the file → *History*), commit, then run the workflow: until then the source is not run at all and the site keeps its last items |
| Re-translate one text | Add it to `data/translations/overrides.yml` (preferred) |
| Re-translate everything | Delete `data/translations/cache.json`, or bump `ENGINE_VERSION` in `translate.py` |
| Force a fresh model download | Delete the `translation-models-…` entry under **Actions → Caches** (the key changes by itself when `MODEL_URLS` in `translate.py` changes) |
| Undo a bad data commit | `git revert <sha>` (or GitHub → commit → *Revert*), then run the workflow |
| Roll the website back | Revert the commits, then run *Website update*. (*Re-run all jobs* of an older run re-deploys what `main` has *now*; *Re-run failed jobs* builds, tests and publishes the commit that run's sync job named — its old data — since the jobs check out that commit) |

## Adding a new source

1. **Module:** create `scripts/sync/<name>.py` following an existing one (e.g. `podcasts.py`):
   `main(argv)` with argparse (`--dry-run`), build Items with `make_item()`, merge with
   `merge_items()`, write with `save_raw("<name>", …, ok=…, error=…, stats=…)`, and end with
   `if __name__ == "__main__": raise SystemExit(run_module("<name>", main))`.
   Use `shared_session()` for aagrapevine.org / aalavina.org; `PoliteSession()` elsewhere.
   Put any settings in `config/site.yml` under `sources:`.
2. **Contract:** add the source/kind/`extra` fields to [DATA_SCHEMA.md](DATA_SCHEMA.md).
3. **Pipeline:** register the module in `MODULES` in `run_all.py` (before `quote`; `crawl` stays last) and
   decide whether it belongs in `QUICK_MODULES` (every run: cheap, or local files like `writers_archive`) or only
   in the full update. A full-update-only module becomes part of `FULL_ONLY` by itself — so its `attempted` counts
   for `status.json` `full_update` and the Morning check — and **must** get an entry in `SETTINGS` of
   `scripts/ops/push_modules.py` (the parts of `config/site.yml` it reads while it syncs; a local file it reads goes
   in `FILES`), so a push that changes them runs it with `--also` (`tests/test_push_modules.py` fails otherwise: it
   expects `SETTINGS` to list exactly `FULL_ONLY`, and never `crawl`, `articles` or `shop`, the modules with many
   requests to the magazine sites — none of them is in `FULL_ONLY`: the crawl is left out by name, the other two are
   morning extras). Then map its raw file to a site file in `build_data.py` (plus a label in `SOURCES`, which also
   gives it a row in the run summary, on `/status/` and in the "not checked" rule).
   Decide whether the mass-drop hold suits it: by default `save_raw` holds a sudden drop for one run; a source whose
   list shrinks a lot on purpose (past events leaving, hand-written files) goes in `DROP_GUARD_EXEMPT` in
   `scripts/sync/common.py` with its reason (or passes `drop_guard=False`). `tests/test_sync_safety.py` covers the
   guard.
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
| `TSML_KEY_AADALLAS`, `TSML_KEY_FORTWORTHAA` | secret → sync (`meetings`) | Meeting-list keys (Dallas, Fort Worth); optional — `feed_obf` in the config is tried next |
| `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `DIGEST_TO`, `DIGEST_FROM`, `DIGEST_REPLY_TO` | secrets → digest | Monthly e-mail; optional |
| `PATH_PREFIX` | build | URL folder of the site (`/aagrapevine/` or `/`); set automatically from Pages |
| `SITE_URL` | build, digest | Public address (from Pages); overrides `site.url` where supported |
| `GV_MODELS_DIR` | sync | Translation model folder (default `.cache/models`; the workflow sets it to the same folder it caches) |
| `GV_MT_THREADS` | sync | CPU threads for translation (workflow: 4) |
| `GV_TRANSLATE_MINUTES` | sync (`build_data`) | Time budget for new translations (default 40; the workflow lowers it on very long crawls) |
| `GV_CRAWL_MINUTES` | sync (`run_all`) | Crawl time box when `--crawl-minutes` is not given |
| `IG_ANONYMOUS` | sync | `0` = same as `sources.instagram.anonymous: false` |
| `IG_GRAPH_VERSION` | sync | Graph API version (default from config, `v21.0`) |
| `GV_LOG_LEVEL` | sync | `DEBUG` for verbose logs |
| `I18N_STRICT` | build | Any value: a missing UI string (and a problem in `config/carry.yml`, `orientation.yml`, `history.yml`, `expenses.yml` or a deck) fails the build; both workflows set it |
| `STRICT_BUILD` | build | Any value but empty, `0`, `false`, `no`, `off`: a build warning fails the build (`eleventy/build-warnings.js`); `check.yml` sets it |
| `BUILD_WARNINGS` | build | A file to write the build's warnings to, one per line (empty: none); `update.yml` sets it for *Check the build* |
| `POSTER_SHARE` | build | `1` / `true`: each `/monthly/YYYY-MM/` page names its own `share.png` as its preview picture (`update.yml` only; the pictures come from `scripts/ops/poster_share.py`) |
| `MONTHLY_NOW` | build | A day or an instant the monthly toolkit, the digest, the shop's windows, the report, the booth and the decks take as "now"; also the committee meeting dates of the month calendar files (`committee.js` `meetingDates`). Previews and tests only |
| `SITE_DATA`, `TRANSLATION_OVERRIDES`, `WRITERS_ARCHIVE`, `BOOTH_DRIVE` | build | Tests and previews: read `data/site` from another folder (`src/_data/db.js`), the overrides the decks print beside La Viña's theme from another file (`eleventy/filters/presentations.js`), the writers archive from another file, the booth's Drive data from another file |
| `GV_BROWSER_SITE`, `GV_BROWSER_CHANNEL`, `GV_BROWSER_REQUIRED`, `GV_BROWSER_VERBOSE` | `tests/browser`, `poster_share.py` | The built site to check (without it the browser checks skip); `chrome`, `msedge` or `chromium`; `1` = a missing browser fails; `1` = print the focus rings' contrasts |
| `ONLY` | build (local) | Build only some `src/pages/*` files |
| `WRITERS_ARCHIVE` | build (local, tests) | Read the Texas writers archive from another file than `data/site/writers_archive.json` (`src/_data/db.js`; the sample `tests/fixtures/writers_archive/site_sample.json`) |
| `GV_SOURCES_SEEN` | Website update, push runs (`scripts/ops/push_modules.py`), tests | Another file than `data/state/sources-seen.json` for the last commit the `FULL_ONLY` sources ran with (same as `--seen FILE`) |
| `GITHUB_EVENT_PATH`, `GITHUB_SHA` | Website update, push runs (`scripts/ops/push_modules.py`) | GitHub's push payload: `before` (the commit the push started from) and `after` (its last commit; `GITHUB_SHA` when the payload names none) — the files come from `git diff` between the two; a payload that lists each commit's added / modified / removed files (a webhook's; a run's event file has none) adds those |
| `I18N_STRICT` | build | Fail on missing UI strings (always on in `update.yml` and `check.yml`; unset locally = the raw key is shown instead) |
| `GH_TOKEN`, `GITHUB_REPOSITORY`, `SITE_URL`, `CHECK_ONLY`, `SCHEDULE` | Morning check (`morning_check.py`) | The built-in token (`actions: write`: start and follow Website update), the repository, the site's address (from Pages; else `site.url`), `check_only`, the cron string that started it. No secret: the morning alarm's key lives at cron-job.org (its `Authorization` header), never in the repository |
| `GITHUB_RUN_ID` | build | Written into `/build.json` → `run` (the Morning check waits until the live one names the run it started) |
