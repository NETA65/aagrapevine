# Automation and troubleshooting

How the website keeps itself up to date with GitHub Actions. This guide covers what starts each automatic
run, how to start one yourself, the tests a run passes before it publishes, how to read what a run reports, the
website's Status page, the three issues the robot opens by itself, the `data/` folder, how to run everything on a
PC, the size limits, and how to recover when something goes wrong.

You do not need to be a programmer. You need a GitHub login with access to
[NETA65/aagrapevine](https://github.com/NETA65/aagrapevine) and, for section 11, a Windows PC.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start](#2-quick-start)
3. [What happens next: how fast a change goes live](#3-what-happens-next-how-fast-a-change-goes-live)
4. [The five workflows](#4-the-five-workflows)
5. [Run a workflow by hand](#5-run-a-workflow-by-hand)
6. [Read a run](#6-read-a-run)
7. [Where it shows on the website: the Status page](#7-where-it-shows-on-the-website-the-status-page)
8. [The three automatic issues and the failure e-mails](#8-the-three-automatic-issues-and-the-failure-e-mails)
9. [The data folder and what the robot commits](#9-the-data-folder-and-what-the-robot-commits)
10. [Who can do what: MKP715 and NETA65](#10-who-can-do-what-mkp715-and-neta65)
11. [Run the sync, the build and the tests on a PC](#11-run-the-sync-the-build-and-the-tests-on-a-pc)
12. [Repository size and GitHub limits](#12-repository-size-and-github-limits)
13. [Going further: change the automation's code](#13-going-further-change-the-automations-code)
14. [Troubleshooting](#14-troubleshooting)
15. [History clean-ups (squashing)](#15-history-clean-ups-squashing)
16. [Good practice](#16-good-practice)
17. [See also](#17-see-also)

---

## 1. What this is

Nobody edits the website's pages by hand. Five **GitHub Actions workflows** (small programs that run on
GitHub's computers) fetch new content, translate it, save the results in this repository, build the pages, test
the code and publish the pages on GitHub Pages. They run on a timetable, whenever someone saves a settings or
content file, and whenever someone presses **Run workflow**.

Where you see the automation at work:

| Where | What it tells you |
|---|---|
| GitHub → **Actions** tab: <https://github.com/NETA65/aagrapevine/actions> | Every run, with a green ✓ or a red ✗ and a summary of what it did |
| The website's **Status page**: <https://neta65.github.io/aagrapevine/status/> (Spanish: <https://neta65.github.io/aagrapevine/es/status/>) | When each content source last updated, and when the daily quotes came in |
| GitHub → **Issues** tab | Three issues the robot opens and closes by itself (section 8) |
| The footer of every page | "Last updated …" = the time of the last build |
| The badge at the top of the [README](../README.md) | Green when the last *Website update* run succeeded |
| Your inbox | GitHub's e-mail when a run fails (section 8.3) |

The big picture:

```text
 Google Drive panel folder ───┐
 (A65_GV › 2027-2028_Panel77_GVLV)
 files you save in the repo ──┼──► Website update (GitHub Actions)
 (config/, content/, src/ …)  │      1. sync: scripts/sync/*.py ──► data/raw/<source>.json
 magazine sites, podcasts, ───┘      2. translate + assemble   ──► data/site/*.json
 YouTube, Instagram, …               3. the robot commits data/ back to the repository
                                     4. build: Eleventy (src/) ──► _site/
                                        and, at the same time, the tests (when the code or content changed)
                                     5. publish, only if both worked ──► https://neta65.github.io/aagrapevine/
```

---

## 2. Quick start

### Make the website update right now

1. Open <https://github.com/NETA65/aagrapevine/actions> (signed in as MKP715 or NETA65: any login with write
   access works).
2. In the left list, click **Website update**.
3. Click **Run workflow** (right side). Leave *Use workflow from* on `main`. Tick **skip_crawl**. Click the
   green **Run workflow** button.
4. Wait about **2 minutes** until the run shows a green ✓ (refresh the page; about 5 minutes if the code or
   content changed since the tests last passed, because they then run first: 4.8). GitHub Pages may take up to
   about **10 more minutes** to show the change to every visitor.
5. Open <https://neta65.github.io/aagrapevine/status/>: *Site last published* now says "… minutes ago".

This "quick" run (listed as **Quick refresh (started by hand)**) reads Google Drive, `content/bulletin`,
`content/events`, the podcasts, the daily quote and the writers archive files (`content/archive`). Videos, magazine
stories, Instagram and the PDF search wait for the nightly full update. For everything at once, leave every field
empty instead (about 10 to 15 minutes; listed as **Full update (started by hand)**).

### Check that everything is healthy (2 minutes)

1. **Actions** tab: the newest *Website update* run has a green ✓.
2. **Status page**: it says **16/16 sources up to date** (Spanish: *16/16 fuentes al día*).
3. **Issues** tab: there is no open issue called **"A content source has stopped updating"** or **"The website
   update keeps failing"**.

If all three are fine, there is nothing to do, even when a run shows a yellow ⚠ titled with a source's name:
that source had a bad day, and the site kept its older items. The same goes for a source marked **On hold** on
the Status page: it suddenly found far fewer items, so the site keeps the missing ones until the next update
confirms they are gone (7.1). A yellow ⚠ titled *Settings problem …*, *Event files to fix*, *Bulletin files to
fix* or *Booth folder file to fix*, or a **CSV file to fix** line under *Writers archive* in the run summary, is
different: one of your files needs a fix (section 14). So is a red ✗ with **Tests failed — not published**: a
change broke the tests, and the live site keeps the version before it (14.10).

---

## 3. What happens next: how fast a change goes live

| You do this | What starts by itself | Live after about |
|---|---|---|
| Save a file in `config/`, `content/`, `src/`, `scripts/` or `eleventy/` on github.com (or push it from a PC) | a **quick** *Website update* run, whose tests run before it publishes (4.8), plus a *Code check* | about 5 minutes, plus up to 10 minutes of Pages caching (a few changes wait for the full update: see the note in 4.3) |
| Put a new export in `content/archive/` | the same; the run reads the new file | about 5 minutes (+ caching) — [Writers archive](writers-archive.md) |
| Save `data/translations/overrides.yml` or `data/translations/glossary.yml` | the same | about 5 minutes (+ caching) |
| Save `data/geo/texas_places.json` (the Texas places list) | the same, and the quick run also reads the meeting lists again | about 5 minutes (+ caching) |
| Put a file in the Drive panel folder (`A65_GV` › `2027-2028_Panel77_GVLV` › …) | **nothing**: nothing watches Drive | the next run that reads Drive (below), or 2 minutes after you press *Run workflow* with **skip_crawl** |
| Edit `README.md`, `docs/`, `how-to/`, a `content/**/README.md` or a test | no website run (a test file or a `content/**/README.md` starts only a *Code check*) | GitHub shows the new text at once; the website does not change. (The next *Website update* run tests the code once more, because its fingerprint changed: 4.8) |
| Edit a file in `data/raw`, `data/site` or `data/state` | nothing | the next scheduled run (and see section 9 before you do this) |
| Edit `.github/workflows/update.yml` | a quick *Website update* + a *Code check* | about 5 minutes |
| Edit any other workflow file | only a *Code check* | the new schedule counts from its next firing |

**The runs that read Google Drive** (every mode reads it):

- the **morning refresh**, started by the Morning check (with the morning alarm: about 4:30 AM Central);
- the **nightly full update** (scheduled; GitHub usually starts it around 6 to 8 AM Central);
- the **midday refresh** (scheduled, quick; usually around 11 AM to 1 PM Central);
- the **evening refresh** (scheduled, quick; usually around 7 to 9 PM Central);
- every quick run after someone saves a watched file;
- any run you start by hand.

(The times are for summer, CDT; in winter each timed run starts about an hour earlier on the Central clock, 4.1.)

Times measured on 2 October 2026: a quick run took 1.4 to 2.2 minutes from start to published, the full run 10
to 14 minutes, a morning refresh 2 minutes. Since October 2026 a run whose code or content is new to the tests
also waits for them before it publishes (4.8): `update.yml` reckons about 3 to 4 minutes, setup included, and they
run while the site is built, so a save now goes live in about 5 minutes. The runs that only bring new data (the
morning, midday and evening refreshes, the nightly update, a *Run workflow*) skip them and keep the times above.
At the very most a full update takes a little over 2 hours: its sync step's time box is 130 minutes (4.2), and it
gets near that only when the document search uses its whole 40 minutes and translation its whole 40 (a big
catch-up after weeks of new titles, or a lost crawl state).

---

## 4. The five workflows

All five live in [`.github/workflows/`](../.github/workflows/). Their names in the Actions tab's left list:

| Name in the Actions tab | File | Starts on | What it does | Typical length | Leaves behind |
|---|---|---|---|---|---|
| **Website update** | [`update.yml`](../.github/workflows/update.yml) | 3 schedules (the nightly full update, the midday and evening refreshes), a push to a watched file, *Run workflow*, the Morning check | sync → translate → commit the data → build, and test the code at the same time → publish only when both worked; then reports sources that stopped updating and updates that keep failing | data-only runs: quick 2 min, full 10–15 min (time box 2 h 10 min), a 300-minute PDF crawl about 6 h; a save of code or content about 5 min (the tests) | a data commit, the new website, a run summary, maybe an issue |
| **Morning check (new day by 5:30 AM)** | [`morning.yml`](../.github/workflows/morning.yml) | an hourly backstop through the night, the morning alarm, *Run workflow* | makes sure the new day and both daily quotes are on the site by 5:30 AM Central | a few seconds when there is nothing to do | a run summary; its no-op runs are deleted a day later |
| **Code check (tests and test build)** | [`check.yml`](../.github/workflows/check.yml) | every pull request; a push that changes code, settings, content or a workflow; *Run workflow* | a strict test build + the Python tests + an e-mail dry run. Publishes nothing | a few minutes | a ✓ or ✗ on the commit or pull request |
| **Monthly e-mail digest** | [`monthly-digest.yml`](../.github/workflows/monthly-digest.yml) | 5 tries a day on the 1st–3rd; *Run workflow* | e-mails last month's bilingual digest, once. **Off until NETA65 adds the e-mail secrets** | seconds | the e-mail; the month's markers `digest-sending-YYYY-MM`, `digest-sent-YYYY-MM` or `digest-unsent-YYYY-MM`; a `digest-preview` download |
| **Weekly link check** | [`link-check.yml`](../.github/workflows/link-check.yml) | Sundays; *Run workflow* | checks every link on the built site and the official links in the settings (job *Check links*), then keeps the issue (job *Report broken links (the issue)*) | up to 45 min | a summary; the `link-check-report` download (7 days); maybe the issue "Broken links found by the weekly check" |

Plus **Dependabot** ([`.github/dependabot.yml`](../.github/dependabot.yml)): once a month it may open a pull
request that updates the building blocks: `chore(actions)…` for the workflows' actions, `chore(deps)…` for the
site tools (npm: minor and patch versions) and for the Python packages (pip: only a **new major version**, one
grouped pull request; every run already installs the newest minor and patch releases, and `yt-dlp` has no cap,
so it is left out). The Code check tests it. Merge it only when it shows a green ✓.

### 4.1 The timetable is set 4 hours early on purpose

GitHub's timetable (`cron:` lines) runs in **UTC** here (no workflow adds a `timezone:` key), and GitHub
starts this repository's timed runs **4 to 6 hours late, sometimes 8**. So every schedule is set about
**4 hours before** the time it is meant for. The odd minutes (:07, :17, :25, :40) avoid GitHub's busy top of
the hour.

> **Keep it that way.** Do not "correct" a schedule back to the real time. The tests pin the exact strings
> (all but the weekly link check's), so the Code check goes red if one changes without its test (section 13.1
> shows how to move one safely).

Real example: on 2 October 2026 the nightly full update, then set for `17 6 * * *` (06:17 UTC), started at 12:36 UTC
(7:36 AM CDT, 6 h 19 min late), and the midday refresh, then set for `7 8 * * *` (08:07 UTC), at 14:42 UTC (9:42 AM
CDT). That refresh landed in the morning, and no timed run refreshed the site from then until the next night, so
the midday refresh moved to `7 12 * * *` and an evening refresh, `7 20 * * *`, was added. In October 2026 the
nightly moved an hour later, to `17 7 * * *`: at 06:17 UTC, a run 4 hours late would start at 4:17 AM CST in winter,
right when the morning alarm starts the morning refresh, which would then have to wait behind it (one update at
a time) past the 5:30 goal. At 07:17 UTC a run GitHub starts on time is finished long before 4:30 AM, and one 4
or more hours late starts after the morning refresh is live, in summer and in winter
(`test_the_nightly_full_update_keeps_clear_of_the_morning_alarm` checks both).

| Schedule (UTC) | Workflow | On time, summer (CDT) | On time, winter (CST) | Usually really starts (CDT) | What it does |
|---|---|---|---|---|---|
| `17 7 * * *` | Website update, **nightly full update** | 2:17 AM | 1:17 AM | ~6–8 AM | every source + the PDF search |
| `7 12 * * *` | Website update, **midday refresh** (quick) | 7:07 AM | 6:07 AM | ~11 AM–1 PM | Drive, bulletin, events files, podcasts, daily quote, writers archive files |
| `7 20 * * *` | Website update, **evening refresh** (quick) | 3:07 PM | 2:07 PM | ~7–9 PM | the same as the midday refresh |
| `25 0-11,21-23 * * *` | Morning check (new day by 5:30 AM), **backstop** | :25 past every hour, 4:25 PM–6:25 AM | 3:25 PM–5:25 AM | late firings land in the early morning; on-time ones find the work done | checks the live site, starts a morning refresh if needed |
| `7 8,11,14,17,20 1-3 * *` | Monthly e-mail digest | 3:07 AM–3:07 PM | 2:07 AM–2:07 PM | — | acts only from 7 AM Central on the 1st–3rd, once a month |
| `40 8 * * 0` | Weekly link check (Sundays) | 3:40 AM | 2:40 AM | — | the link report |
| outside GitHub | the **morning alarm** at cron-job.org → Morning check (new day by 5:30 AM) | 4:30 AM America/Chicago, **on time** | same | within seconds | the only sure way to the 5:30 AM goal ([README → 10 d](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)) |

CDT = UTC−5 (until 1 November 2026), CST = UTC−6. GitHub's timetable ignores daylight saving, so in winter
every timed run is one hour earlier in Central time (the nightly update then usually starts around 5 to 7 AM, the
midday refresh around 10 AM to noon, the evening one around 6 to 8 PM). The morning alarm is not a GitHub
schedule: leave it at 4:30.

**Only `17 7 * * *` is a full run.** The step *Decide what to sync* compares the schedule that started the run
(`github.event.schedule`) with `FULL_CRON="17 7 * * *"`: that one is the full update, and **every other schedule** —
the midday and evening refreshes, and any `cron:` line added later — is a quick run. So a new schedule can never
start a long document search by mistake.

### 4.2 Website update and its three modes

The step *Decide what to sync* (in the first job, after the set-up steps) picks one of three modes:

| Mode | Started by | Reads | Translation box | Step box | Typical | Data commit message |
|---|---|---|---|---|---|---|
| **morning** | the Morning check, or **morning** ticked | Google Drive (5-minute box), `content/bulletin` + `content/events`, the daily quote (right after the bulletin), the podcasts, the writers archive files. On the 1st also the new magazine issues and the shop; on the 15th the shop (Book of the Month) | 5 min | 20 min | ~2 min | `chore(data): morning refresh with the daily quotes of Oct 6 2026-10-06 [skip ci]` (each magazine whose quote changed, by the quote's own day: `… with the Grapevine quote of Oct 6 and the La Viña quote of Oct 5 2026-10-06 [skip ci]`; no new quote: `chore(data): morning refresh 2026-10-06 [skip ci]`) |
| **quick** | a push to a watched file; **skip_crawl** ticked; every schedule but `17 7 * * *` (the midday `7 12 * * *` and the evening `7 20 * * *` refresh) | Google Drive, `content/bulletin` + `content/events`, the podcasts (no feed discovery), the writers archive files (`content/archive`), the daily quote — and, for a push, the sources only the full update reads whose own input the push changed (below) | 40 min | 90 min | ~2 min | push: `chore(data): content sync after settings/content change 2026-10-02 [skip ci]`; midday: `chore(data): midday refresh …`; evening: `chore(data): evening refresh …`; by hand: `chore(data): quick refresh …` |
| **full** | the `17 7 * * *` schedule; *Run workflow* with no box ticked; the Morning check on the 1st or after 30 hours without one | every source: the 14 sync modules plus the PDF search (`crawl`), time-boxed by `crawl_minutes` (normally 40; `0` skips it) | 40 min (10 on a 300-minute crawl) | 130 min with a 40-minute crawl (at most 345) | ~10–15 min | `chore(data): daily content sync 2026-10-02 [skip ci]` |

The date in the message is the run's Central date, and always the end of the message, before `[skip ci]` (the
morning refresh names its quotes by their own day before it: the step compares each magazine's quote in
`data/site/quote.json` with the last commit's). A run that took a new writers archive file in says so just before
the date: `chore(data): content sync after settings/content change + writers archive 2026-11-05 [skip ci]`
([Writers archive §6.2](writers-archive.md#62-the-data-commit)).

**A push also runs the sources whose input it changed.** A quick run does not read the sources only the full update
reads, so a push used to show an edit of, say, `content/instagram.yml` only after the next night. Now *Decide what
to sync* runs [`scripts/ops/push_modules.py`](../scripts/ops/push_modules.py) for every push: it asks git which files
differ between the last commit those sources ran with and the push's last commit (`git diff --name-only
--no-renames`; the run's checkout has only the newest commit, so a commit it lacks is fetched first, one commit
deep — GitHub's event file for a run lists no files) and, for `config/site.yml`, which settings changed (it
compares the file with its copy from that same earlier commit), and hands `run_all --quick --also …` the sources
to add. "The last commit those sources ran with" is kept in `data/state/sources-seen.json` (`{commit, by,
recorded}`): the step *Remember the commit the full-update sources ran with* writes it after a full update (the
commit it checked out) and after a push run (the push's last commit), each time only when the sync step ended
well. So a push whose own run GitHub replaced in the queue (only one run waits, below) still gets its sources run
by the next push's run. Without that file, or when git cannot fetch its commit, the comparison starts from the
commit the push started from, as GitHub's own `paths:` filter sees the push.

| The push changed | Also runs |
|---|---|
| `content/instagram.yml` | `instagram` (without the look-ups of each post's own page: a picture or caption the accounts' pages did not give waits for the next full update) |
| `data/geo/texas_places.json` | `meetings` (which meetings are in our Area) |
| `config/site.yml` → `sources.youtube` | `youtube` (the channels' feeds; the full listing of older videos stays in the full update) |
| `config/site.yml` → `sources.instagram` | `instagram` |
| `config/site.yml` → `sources.grapevine.contribute`, `sources.lavina.contribute`, `themes_page`, `rlv_resources`, `themes_link` | `editorial` |
| `config/site.yml` → `sources.grapevine.weekly_open`, `lavina_weekly_open` | `weekly_open` |
| `config/site.yml` → `sources.grapevine.audio_project`, `sources.lavina.record_story`, `record_instructions`, `record_tips`, `record_topics`, `sample_audio` | `audio_project` |
| `config/site.yml` → `meetings`, `spotlight.neta65_counties` | `meetings` |
| `config/site.yml` → `sources.grapevine.base` or `sources.lavina.base` | `editorial`, `weekly_open` (Grapevine's base), `audio_project`, `events_external` |

Never added: the document search, the magazine stories and the store (`crawl`, `articles`, `shop`: many polite
requests to the magazine sites; they run every night). Settings only the site data or the pages read need nothing:
every run rebuilds those. The plan step's log says, for example, `Files this push changed: 2 (git diff
1a2b3c4..5d6e7f8, from the last commit the full-update sources ran with (data/state/sources-seen.json)).` and `Also
run for this push: instagram (content/instagram.yml); meetings (data/geo/texas_places.json)`, and the run summary
adds the line **Also run for this push**. When `sources-seen.json` could not be used, a blue notice *Push run* says
"Could not compare this push with the last commit the sources only the full update reads ran with
(data/state/sources-seen.json) — … —, so only its own changes count." If git cannot compare the two commits at all
(a brand-new branch, a commit that cannot be fetched), the files an event file lists are used instead, and a notice
says so; with none — the usual case for a run's event file — nothing is added, and the notice says that. If only
the earlier copy of `config/site.yml` cannot be read, nothing is added for it, with the same kind of notice. Those
sources then show the change after the next full update.
These runs do not count as a full update: `run_all` passes `build_data --keep-full-update` in every quick and morning
run, so `status.json` → `full_update` (and the Morning check's view of "the last full update") moves only with a
full run.

**One at a time.** Website update runs belong to one queue (`concurrency: group: update-deploy`). A new run
waits for the current one. GitHub keeps only **one** waiting run: a newer waiting run replaces the older one,
which then shows as grey "cancelled". Nothing is lost, because the run that starts reads the newest commit.

**What the five jobs do (in every mode):**

1. **Sync content + translate**: installs Python 3.12, restores the translation models from the Actions cache
   (about 175 MB), decides the mode (*Decide what to sync*), runs `python -m scripts.sync.run_all` with `--morning`,
   `--quick` (for a push maybe `--quick --also instagram,meetings`) or `--crawl-minutes N` in the step **Sync sources
   and translate**, remembers the commit the full-update sources ran with (above), commits the data, writes the run
   summary. Its output `commit` is the data commit it pushed (or, with nothing to commit, the commit it checked
   out): the next two jobs check out exactly that commit.
2. **Build website** (job id `build-deploy`; it was called *Build & publish website* until October 2026): runs even
   when the sync failed (the site then shows the last good data), but not when a person cancelled the run. It
   checks out the sync job's commit, saves the booth display's photos and videos for offline play (below), builds
   with Eleventy in strict mode, checks that the English and Spanish home pages and the stylesheet exist, and
   uploads the site for publishing. Its time limit is 35 minutes.
3. **Test the code before publishing** (job id `tests`): at the same time as the build, on the same commit, the
   offline tests, when the code or content is new to them (4.8). Time limit 20 minutes.
4. **Publish to GitHub Pages** (job id `publish`): only when the build **and** the tests succeeded, and only after
   it checked that both used the very same commit (otherwise it stops with *Not published*: "The website was built
   from … but the tests ran on … (a change arrived between the two) — nothing was published; the next run
   publishes."). Time limit 15 minutes.
5. **Report sources that stopped updating, and updates that keep failing**: opens, updates or closes the issues
   in sections 8.1 and 8.4. It never fails the run.

**The booth display's media** (the build job, between *Install site tools* and *Build the website*). The booth on
the About page plays offline, so the Drive booth folder's photos, videos and sound files are published with the
site, at `/about/booth/media/` — never in Git. Five steps keep them in `.cache/booth-media/` from one run to the
next:

| Step | What it does |
|---|---|
| *Work out the booth display's settings fingerprint* | a fingerprint of `data/site/booth.json` and of the **`booth:` section** of `config/site.yml` only (its size limits), so an unrelated edit of the settings file no longer saves the whole folder again under a new key. A settings file that is not readable YAML is fingerprinted whole; this step never stops a deploy |
| *Restore the booth display's media (saved between runs)* | `actions/cache/restore` brings back the folder: the newest copy saved for this fingerprint (key `booth-media-v1-<fingerprint>-…`), else the newest copy of any (`booth-media-v1-`) |
| *Download the booth display's photos and videos (Drive booth folder)* | `node scripts/build/booth-media.mjs`: keeps what is already saved, deletes what left the folder, downloads the rest (a photo as Google's 1920-pixel picture, a video or sound file whole) within `booth.max_file_mb` (95) and `booth.max_total_mb` (400) of `config/site.yml`, and writes `.cache/booth-media/manifest.json`. A picture is kept only when its bytes are a JPEG, PNG, WebP, GIF or AVIF picture, whatever type the answer claims, and it is named by what its bytes are; anything else (an SVG, for example) is listed as skipped: "the answer is not a picture (…): the booth keeps JPEG, PNG, WebP, GIF and AVIF pictures". (A picture an earlier run kept as `.svg` or `.bmp` is deleted and downloaded again.) Downloads stop by the 15th minute (the step allows 20); what is left waits for the next run. `continue-on-error`: it never stops the deploy |
| *Work out the booth display's media cache key* | the same fingerprint plus one of the saved files' names and sizes (no key when nothing is saved) |
| *Save the booth display's media for the next run (only when this run changed it)* | `actions/cache/save` with that key, before the build, so a build that fails later keeps the downloads (5 minutes, `continue-on-error`) |

A run that downloads new booth videos takes that much longer. The *Code check* downloads nothing: its test build
has no saved copies (the booth then shows its pictures from Google's copy and leaves videos out). Details:
[Booth display](booth.md).

### 4.3 Which saved files start a run

These were checked against GitHub's path rules (the last matching rule wins).

| You save (on `main`) | Website update (quick) | Code check (tests and test build) |
|---|---|---|
| `config/site.yml`, `config/presentations/committee-meeting.yml` | yes | yes |
| `config/presentations/README.md` | – | yes |
| `content/bulletin/2027-01-10-welcome-gvrs.md`, or a picture saved next to it | yes | yes |
| `content/events/2027-03-19-neta65-spring-assembly.md`, `content/instagram.yml` | yes | yes |
| `content/archive/aagrapevine_archive_2026-11-05.csv` (a writers archive file) | yes | yes |
| `content/bulletin/README.md`, `content/events/README.md`, `content/archive/README.md` | – | yes |
| `data/translations/overrides.yml`, `data/translations/glossary.yml` | yes | yes |
| `data/geo/texas_places.json` | yes (and the run reads the meeting lists again) | yes |
| `data/geo/README.md` | – | yes |
| `data/raw/*.json`, `data/site/*.json`, `data/state/*`, `data/translations/cache.json` | – | – |
| `src/pages/status.njk`, `src/_i18n/community.json`, a Markdown page in `src/pages/` | yes | yes |
| `src/assets/cache/…` (thumbnails the robot downloads) | – | – |
| `scripts/sync/drive.py`, `eleventy/filters/community.js`, `eleventy.config.js`, `package.json`, `requirements.txt` | yes | yes |
| `tests/test_morning.py` | – | yes |
| `README.md`, `docs/OPERATIONS.md`, `how-to/automation-and-troubleshooting.md`, `LICENSE` | – | – |
| `.github/workflows/update.yml` | yes | yes |
| `.github/workflows/check.yml`, `morning.yml`, `monthly-digest.yml`, `link-check.yml` | – | yes |
| `.github/dependabot.yml` | – | – |

In short: **settings, content and code rebuild the site; documentation and the robot's data files do not.**
Deleting or renaming a file counts as changing it.

> **Note:** the quick run that a save starts reads Drive, `content/bulletin`, `content/events`, the podcasts, the
> writers archive files and the daily quote, then rebuilds everything else from the data already saved. When the
> save changed what a source only the full update reads looks at — a post added to `content/instagram.yml`, a
> channel under `sources:` → `youtube:` → `channels:`, La Viña's weekly open meeting, the meeting lists, the Area 65
> counties — that source runs in the same quick run (the table in 4.2). Only the magazine stories, the store's
> pages and the document search (`magazine_hub`, `botm`, `subscriptions`, `specialty`, `crawler` …) still wait for
> the next **full** update; to see such a change at once, press *Run workflow* with every box empty (section 5).

> **Note:** a commit message that contains `[skip ci]` (also `[ci skip]`, `[no ci]`, `[skip actions]` or
> `[actions skip]`) starts **no** push-triggered workflow. The robot puts `[skip ci]` on its own data commits;
> do not put it in yours unless you mean it. (The robot's pushes would not start a run anyway: a push made with
> GitHub's built-in token never starts a workflow run. That, the path list and `[skip ci]` are the three things
> that keep the data commits from looping.)

### 4.4 Morning check (new day by 5:30 AM)

It puts the new day and both daily quotes on the site by the goal in `config/site.yml` → `site.morning_goal`
(`"05:30"`, Central). It reads the **live** site's `/build.json` (section 7.3):

1. Today's build with today's Grapevine **and** La Viña quotes on the site → nothing to do (a few seconds).
2. A *Website update* run already waiting or running → it follows that run first instead of queueing another.
3. The site does not have today's build → it starts *Website update* in **morning** mode, follows it, then
   reads the live site until the new build shows.
4. Today's build is up but a magazine's quote is not out yet → from 2:00 to 7:00 AM Central (the magazines
   usually publish the new day's quote about 2 AM; `WINDOW_BEFORE`, 3 h 30 min before the 5:30 goal) it asks only
   that magazine's home page every 10 minutes (a check that starts after 7:00 AM asks once), and refreshes again
   once the quote is out (at most 3 refreshes per check; nothing new after 170 minutes, so a check that begins at
   2:00 asks until 4:50, and the alarm's check at 4:30 waits for it, then asks until 7:00).
5. On the 1st of the month, or after 30 hours without a full run, it also starts the **full** update (listed as
   "Full update (started by the Morning check)"), but not while a *Website update* run waits, or runs (any run
   but a morning refresh: it may be a full one), and not again within 12 hours of a full update already started by
   *Run workflow*. It recognises those by their
   titles (`is_full_title` in `scripts/ops/morning_check.py`: a title that starts with "Full update" or "Nightly full
   update"); a quick, midday, evening or morning refresh never counts as one.

What starts it: the **morning alarm** (an outside alarm clock at cron-job.org presses *Run workflow* at 4:30 AM
Central with a key made by NETA65; set up in [README → 10 d](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)),
GitHub's hourly backstop schedule, or anyone pressing *Run workflow* (tick **check_only** to only look).

| Result | Meaning |
|---|---|
| green ✓, summary "✅ Today's update is on the site since **4:34 AM CDT** — goal 5:30 AM." | it saw today's update go live |
| green ✓, summary "✅ Today's update is on the site — the latest build is from **6:40 PM CDT**." | it was already there |
| green ✓ with a yellow note "A daily quote is late at the source" | the magazine had not published its quote yet; the site shows the last one, labelled "Yesterday" |
| green ✓ with a yellow note "Cannot confirm" | the refresh finished but the live site did not show it within 5 minutes; never a reason for another run |
| red ✗ "Morning update failed" | today's update did **not** reach the site; GitHub e-mails whoever started the check (for the alarm: the owner of its key) |

Many *Morning check* runs in the Actions tab are normal: the backstop fires every hour through the night. The
job "Tidy up old runs that had nothing to do" deletes the green runs that did nothing, a day later. The alarm
and its key are covered in [E-mail and alerts](email-and-alerts.md).

### 4.5 Code check (tests and test build)

It builds a test copy of the site exactly like the deploy does (strict about missing button texts, and it
**fails** when `/build.json` is missing), runs `python -m unittest discover -s tests -v` (the tests that need the
translation models are skipped there), and checks that the monthly e-mail still builds
(`send_digest --dry-run`, nothing is sent). Nothing is published. Its two jobs are **Test build of the website**
(steps *Build the website (as for GitHub Pages)* and *Check the build*) and **Python tests (offline)**. A push or a
pull request keeps GitHub's own title (the commit message, the pull request's title); a run started by hand is
"Code check (started by hand)". Besides code, settings, content and workflows, a change of `data/geo/**` (the
Texas places list the place tests read) starts it too.

- A red ✗ on a push means **that change broke something**: fix it or undo it. The live site keeps working:
  *Website update* runs the same tests before it publishes (4.8), so the same change is not published either.
- On a pull request (for example Dependabot's), a red ✗ means: do not merge.
- A newer push cancels a check that is still running, so grey "cancelled" Code check runs are normal.

The Code check runs **every** test. *Website update*'s own tests leave out the few that judge the day's synced
data rather than the code (`DATA_TESTS`, 4.8): those turn only the Code check red.

### 4.6 Monthly e-mail digest (short version)

- **Off today.** Each try ends green with "E-mail digest is not set up — nothing to do. (This is normal.)" until
  **NETA65** adds the secrets `SMTP_SERVER`, `SMTP_USERNAME`, `SMTP_PASSWORD` and `DIGEST_TO`.
- There is **no Gmail API code**. The e-mail goes out over plain SMTP with Python's `smtplib`, in
  [`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py) (functions `connect` and `send`). With
  Gmail that means `smtp.gmail.com`, port 587 and a 16-letter app password.
- **Preview** (anyone with write access, no secrets needed): *Actions → Monthly e-mail digest → Run workflow*,
  keep **Preview only** ticked → the run's **Artifacts** → `digest-preview` (`digest.html` + `digest.txt`).
- **Send it now:** untick *Preview only*. It sends at once to everyone in `DIGEST_TO`, unless that month was
  already sent: then nothing goes out and a yellow ⚠ *Already sent* says so. To send a month **again**, tick
  **force** too (the run is titled "Monthly e-mail digest: SEND AGAIN (forced, started by hand)"). With both
  *Preview only* and *force* ticked, it is only a preview.
- **Sent once, even on a bad day.** Every send first reads the month's markers (artifacts kept 40 days):
  `digest-sending-YYYY-MM` is uploaded just **before** the e-mail is handed to the mail server,
  `digest-sent-YYYY-MM` after it went (or when nothing was new), `digest-unsent-YYYY-MM` when the server took
  nothing (the next try sends). A "sending" marker with no later marker from its run (the run was cancelled or
  broke off in between, so the e-mail **may** have gone) is never sent again by itself: each try shows the yellow
  ⚠ *Digest send not confirmed* with the run's link. Check the group; if it did not arrive, send it with *force*.

Everything else (secrets, recipients, wording, test sends) is in [E-mail and alerts](email-and-alerts.md).

### 4.7 Weekly link check

On Sundays (and by hand) it builds the site, checks every link on every page with
[lychee](https://github.com/lycheeverse/lychee) (2 requests at a time per website, 1 second apart; it skips
aagrapevine.org, aalavina.org, YouTube, Instagram, Google, Zoom and podcast, social and shopping sites, which
limit robots),
then checks the official links in `config/site.yml` (`links:`, `site.area_website`, `site.committee_page`,
each podcast's `web:`) one by one with the site's polite robot. A broken link **never turns it red** (only a
site build that fails would); it keeps one issue instead (8.2).

Since October 2026 it is two jobs: **Check links** (it may only read the repository; it runs lychee and the
official-links check and keeps their reports as the download `link-check-report`, 7 days) and **Report broken
links (the issue)** (the only one allowed to write issues; it runs no outside code and only reads that download).
lychee's action, the one action from outside GitHub in the workflows, is pinned to an exact commit:
`lycheeverse/lychee-action@e7477775783ea5526144ba13e8db5eec57747ce8 # v2.9.0`. Dependabot's monthly
`chore(actions)` pull request moves the commit and its `# v…` note together; a test checks that every outside
action is pinned this way.

### 4.8 The tests before publishing

Since October 2026 *Website update* never publishes code that fails the tests. Its job **Test the code before
publishing** runs `python -m scripts.ops.gate_tests` ([`scripts/ops/gate_tests.py`](../scripts/ops/gate_tests.py)):
every offline test of `tests/`, the same ones the Code check runs, at the same time as the build and on the very
same commit. The job **Publish to GitHub Pages** waits for both. A change that breaks a test therefore never goes
live; the site keeps the version before it.

| Question | Answer |
|---|---|
| Which tests? | all of `tests/` except the few listed in `DATA_TESTS` in `gate_tests.py` (4 today: the booth CSV's videos and episodes, the colours of the day's events, the sections of the day's bulletin posts, the presentations' live values). They judge the day's synced data rather than the code, and a day's data must never keep the site from updating; the Code check still runs them. The tests that need the translation models skip themselves, as in the Code check |
| When do they run? | only when the code or the content is **new to them**. The job takes a fingerprint of every file in git except the robot's own (`data/raw`, `data/site`, `data/state`, `data/translations/cache.json`, `src/assets/cache`) and remembers a pass in the Actions cache (`tests-passed-v1-<fingerprint>`) |
| And the daily runs? | the morning, midday and evening refreshes and the nightly update change only the robot's files, so they find the pass and skip the tests in a few seconds, with the summary line "The tests passed already for this code and content (only the bot's data changed since) — not run again." |
| What makes them run? | any commit of yours: code, settings, content, translation fixes, and also a test or a guide (they are in git too). The run of that save tests it; after a commit that starts no run (a guide, a test), the next run tests once. If GitHub has deleted the remembered pass (a cache unused for 7 days), they simply run again |
| How long? | `update.yml` reckons about 3 to 4 minutes on GitHub, setup included, about as long as the build; on the owner's PC the whole suite takes about 4 minutes |
| What does the summary say? | a section **Tests before publishing**: "All N tests passed (M skipped) — the website may be published." and "Left to the Code check (they judge the day's synced data, not the code): 4." |
| And when one fails? | "**N of M tests failed — the website was NOT published** (the live site keeps the version before). Fix the change that broke them, or undo it; the next run publishes." with the failing tests, and the red annotation *Tests failed — not published*. The data commit was made as usual. What to do: 14.10 |

If a test fails because of the day's synced data rather than anybody's change (it would fail on the Code check of
the same commit too, and keep failing with no new commit), add its id to `DATA_TESTS` in `gate_tests.py`, with a
line saying what it judges: the gate then leaves it to the Code check. Tested by `tests/test_automation.py`
(classes `Publishing`, `GateTests`).

---

## 5. Run a workflow by hand

Any login with write access (MKP715 or NETA65) can do this:

1. Open <https://github.com/NETA65/aagrapevine/actions>.
2. Click the workflow in the left list.
3. Click **Run workflow** (right side, above the list of runs).
4. Leave **Use workflow from: Branch: main**. Fill in the boxes (below).
5. Click the green **Run workflow**. The new run appears at the top of the list after a few seconds.

The website's Status page has a shortcut: *Technical details (for the site maintainer)* → **Open GitHub
Actions**.

| You want to… | Workflow and boxes | What happens | Time |
|---|---|---|---|
| Show a new Drive file, bulletin post, podcast or archive file now | *Website update*, tick **skip_crawl** | quick run, then publish ("Quick refresh (started by hand)") | ~2 min |
| Refresh everything, like the nightly full update | *Website update*, all boxes empty | full run with the 40-minute PDF search ("Full update (started by hand)") | ~10–15 min today |
| A big PDF catch-up (only after the crawl's saved progress was lost) | *Website update*, `crawl_minutes` = `300` | full run with a 5-hour search | ~6 h; start it in the **morning**, never the evening |
| Put today's quote up | *Morning check (new day by 5:30 AM)*, no boxes | does only what is missing | seconds to a few minutes |
| See what the Morning check would do | *Morning check (new day by 5:30 AM)*, tick **check_only** | it looks and reports, starts nothing | seconds |
| The same refresh the Morning check starts | *Website update*, tick **morning** | morning refresh | ~2 min |
| Run the tests and a test build | *Code check (tests and test build)* | ✓ or ✗ | a few minutes |
| Preview the monthly e-mail | *Monthly e-mail digest*, keep **Preview only**, `month` empty or e.g. `2026-09` | the `digest-preview` download | ~1 min |
| Send the monthly e-mail now | *Monthly e-mail digest*, untick **Preview only** | sends at once, unless that month was already sent (⚠ *Already sent*) or a send of it was not confirmed (4.6) | ~1 min |
| Send a month's e-mail **again** | *Monthly e-mail digest*, untick **Preview only**, tick **force** | sends it a second time to everyone (check the group first) | ~1 min |
| Check the links now | *Weekly link check* | summary + issue | up to 45 min |

Why start long crawls in the morning: the Morning check follows a running *Website update* run for up to 170
minutes and goes red if today's build is still missing after that. A 300-minute crawl started in the evening
would block the next morning.

### 5.1 The `crawl_minutes` box: every kind of input

Checked by running the real *Decide what to sync* step (the daily setting is
`sources.crawler.minutes_per_run: 40` in `config/site.yml`):

| You type or tick | Mode | PDF search | Translation box | Step box | Message on the run page |
|---|---|---:|---:|---:|---|
| nothing | full | 40 min | 40 | 130 | — |
| `120` | full | 120 min | 40 | 210 | — |
| `300` | full | 300 min | 10 | 345 | — |
| `500` (or `12345`) | full | 300 min | 10 | 345 | ⚠ "Capped at 300 minutes (GitHub stops jobs after 6 hours)." |
| `abc` (or `2.5`) | full | 40 min | 40 | 130 | ⚠ "'abc' is not a whole number of minutes; using 40." |
| ` 25 ` (with spaces) | full | 25 min | 40 | 115 | — (spaces are removed) |
| `0` | full, no PDF search | 0 | 40 | 90 | notice "PDF search paused: Crawl minutes = 0 …" |
| **skip_crawl** ticked (any minutes) | quick | — | 40 | 90 | — |
| **morning** ticked (wins over both boxes) | morning | — | 5 | 20 | — |

GitHub stops any job after 6 hours, which is why the crawl is capped at 300 minutes: the rest of the time is for
the other sources, translation and the data commit.

The run's title in the Actions list follows the same boxes: **morning** ticked → "Morning refresh: new day and daily
quote" (whatever else the form says); **skip_crawl** ticked → "Quick refresh (started by hand)"; `crawl_minutes` =
`0` → "Full update without the document search (started by hand)"; anything else → "Full update (started by hand)".

### 5.2 Re-run, cancel, delete

| To… | Do this | Good to know |
|---|---|---|
| **Stop** a run | open it → **Cancel workflow** | what it fetched so far is still committed (the commit step always runs); the site is published by the next run |
| **Re-run** a failed run | open it → **Re-run jobs** → *Re-run failed jobs* (or *Re-run all jobs*) | for *Website update*, *Re-run all jobs* starts from the files `main` has **now**; *Re-run failed jobs* builds, tests and publishes the commit that run's sync job saved (since October 2026 both jobs check out that commit). On a run of today that is what you want; on an old run, use *Run workflow* (or *Re-run all jobs*) instead, so no old content is published |
| **Roll the website back** | revert the commits first (section 14.9), then run *Website update* | — |
| **Delete** an old run | the run's **⋯** menu → *Delete workflow run* | deleting a *Monthly e-mail digest* run also deletes its `digest-sending`, `digest-sent` or `digest-unsent` marker, so the next try could send that month again (see [E-mail and alerts](email-and-alerts.md)) |

### 5.3 From a command line (optional)

With the GitHub CLI (`gh`, not installed on the owner's PC by default) and a login with write access:

```bash
gh workflow run update.yml -R NETA65/aagrapevine -f skip_crawl=true
gh workflow run update.yml -R NETA65/aagrapevine -f crawl_minutes=120
gh workflow run update.yml -R NETA65/aagrapevine -f morning=true
gh workflow run morning.yml -R NETA65/aagrapevine -f check_only=true
gh workflow run monthly-digest.yml -R NETA65/aagrapevine -f preview_only=true -f month=2026-09
gh workflow run monthly-digest.yml -R NETA65/aagrapevine -f preview_only=false -f force=true   # send again
gh workflow run check.yml -R NETA65/aagrapevine
```

The morning alarm uses the same thing through GitHub's REST API:
`POST https://api.github.com/repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches` with the body
`{"ref":"main"}`.

---

## 6. Read a run

### 6.1 The list of runs

| You see | Meaning |
|---|---|
| green ✓ | the run finished well (for Website update: the site was built and published, even if one source failed) |
| red ✗ | something needs a person: open the run (section 14) |
| grey ⊘ "cancelled" | someone pressed *Cancel*, or a newer run took its place in the queue (normal for Website update and Code check) |
| yellow dot / spinning circle | waiting or running |

**Run names.** Each run's title says what kind of run it is and what started it (the `run-name:` line at the top of
each workflow file). A run started by a push keeps GitHub's own title, the commit message (for example
"presentations: a hybrid event shows its place…").

| Workflow | Run | Title in the Actions list |
|---|---|---|
| Website update | the `17 7 * * *` schedule | **Nightly full update (GitHub schedule)** |
| | the `7 12 * * *` schedule (and any other schedule but the two named here) | **Midday refresh (GitHub schedule)** |
| | the `7 20 * * *` schedule | **Evening refresh (GitHub schedule)** |
| | the Morning check's refresh, or **morning** ticked by hand | **Morning refresh: new day and daily quote** |
| | the full update the Morning check starts (on the 1st, after 30 hours) | **Full update (started by the Morning check)** |
| | *Run workflow*, **skip_crawl** ticked | **Quick refresh (started by hand)** |
| | *Run workflow*, `crawl_minutes` = `0` | **Full update without the document search (started by hand)** |
| | *Run workflow*, any other input | **Full update (started by hand)** |
| | a push | the commit message |
| Morning check (new day by 5:30 AM) | its hourly schedule | **Morning check (GitHub schedule)** |
| | *Run workflow* with **check_only** | **Morning check (look only)** |
| | *Run workflow* (the morning alarm included) | **Morning check (started by …)**, with the login that started it: the alarm shows the owner of its key |
| Monthly e-mail digest | its schedule | **Monthly e-mail digest (GitHub schedule)** |
| | *Run workflow*, **Preview only** ticked | **Monthly e-mail digest: preview only** |
| | *Run workflow*, **Preview only** unticked | **Monthly e-mail digest: SEND NOW (started by hand)** |
| | *Run workflow*, **Preview only** unticked, **force** ticked | **Monthly e-mail digest: SEND AGAIN (forced, started by hand)** |
| Weekly link check | its Sunday schedule | **Weekly link check (GitHub schedule)** |
| | *Run workflow* | **Weekly link check (started by hand)** |
| Code check (tests and test build) | *Run workflow* | **Code check (started by hand)** |
| | a push or a pull request | the commit message or the pull request's title |

Only the full titles count as "a full update already started" for the Morning check (4.4). The morning refresh's
title is also how the Morning check finds the run it started (`MORNING_TITLE` in `scripts/ops/morning_check.py`),
so it must never change on its own. Older runs, from before these titles, mostly carry only the workflow's name
as it was when they ran.

### 6.2 Inside a run

Click a run. The **Summary** page shows, from top to bottom:

1. how it started (for example "Triggered via push", "Triggered via schedule"), the status and the duration;
2. the jobs as boxes (for *Website update*: *Sync content + translate* → *Build website* and *Test the code
   before publishing* side by side → *Publish to GitHub Pages*, and *Report sources that stopped updating, and
   updates that keep failing*); the publish box shows the website address;
3. **Annotations**: every yellow ⚠ warning, blue ℹ notice and red ✗ error, most with a title;
4. each job's **summary** (the tables in 6.3);
5. **Artifacts** (downloads), for example `digest-preview`.

For the full log: click a job in the left column, then click a step to open it. The log has a search box, and
the ⚙ menu can download the whole log. When you ask someone for help, copy the last 20 lines of the red step.

Times in the *Website update* summary are **UTC**. The Morning check's summary and the commit messages use
Central time (the digest's "Not the time …" line says "Central time" too), and the Status page uses the
visitor's own time zone, except its daily-quote times, which are Central.

### 6.3 The Website update summary, section by section

| # | Section | What it says | When to act |
|---|---|---|---|
| 1 | **Full update**, **Quick refresh** or **Morning refresh** (the kind of run) | one row per source module: status (✅ ok, ⏭️ skipped, ⚠️ failed), seconds, items, new, a note; a **total** row ("all ok" or the failed names) | a ⚠️ row: see 14.1 |
| 2 | **Content sources** | the 16 sources: Status **OK**, **NOT CHECKED** or **PROBLEM**, items, new in 7 days, last success (UTC), the problem | a PROBLEM for many days; a NOT CHECKED row (below) |
| 3 | **Also run for this push** | only in a push's run that also ran sources the nightly update reads, and why: "instagram (content/instagram.yml); meetings (data/geo/texas_places.json)" (4.2) | — |
| 4 | **Daily quote** | the day of each magazine's quote now on the site, e.g. "Grapevine Oct 2 · La Viña Oct 2" | — |
| 5 | **PDF crawl** | pages known · crawled · PDFs · pages this run | crawled far below known (see [Automatic sources](automatic-sources.md)) |
| 6 | **Translations** | cached · new this run · waiting for the next run | ⚠ "Translation is not working" (14.2) |
| 7 | **Writers archive** | the archive files in use (name, rows, rows by Texas writers), the stories on the site and how many are by Area 65 writers; "New archive file used: …" in the run that took a file in (also a blue ℹ); a **CSV file to fix** line when a file was not used; the module's warnings (an older copy that may be deleted …) | a CSV file to fix ([Writers archive §10](writers-archive.md#10-the-safety-checks-and-what-to-do)) |
| 8 | **Notes** | small problems of sources that still updated (the writers archive's are in its own block), at most two per source, for example a meeting list or YouTube answering with a bot check, main pages of the magazine sites that did not load (below), a Drive folder that suddenly looked empty, a date in a Drive file name that could be read two ways | only if the same note repeats for a week (the hub note: see below) |
| 9 | **Other calendars (optional, informational)** | outside calendars (`sources.ics_feeds`): working, blocked, not answering; *Check:* lines | never counts as a failure |
| 10 | **Settings problems** | a part of `config/site.yml`, a translation file or a `content/events` file (for example a venue that is "to be announced" in one language only) that was skipped or corrected, with the reason; also (as *translations*) a translation memory that could not be read and was set aside, or a downloaded translation model that was refused because its checksum is not the expected one | fix the file and save it again; for the translation memory or a model, see [Translations](translations.md) |
| 11 | **Bulletin files to fix** / **Event files to fix** | a file in `content/bulletin` or `content/events` that could not be read, or that links a picture or document not saved next to it (at most 10 each) | fix the file and save it again |
| 12 | **Booth folder files the booth display can't show** | each file of the Drive booth folder that can never be shown (`data/site/booth.json` → `problems`: its type, a note with no text, `(from …)` after `(until …)`), with what to do (at most 30; the first 10 also as ⚠ *Booth folder file to fix*) | rename, convert or replace the file in Drive ([The Drive panel folder §3.6](drive-panel-folder.md#36-the-booth-folder-new)) |
| 13 | **Scheduled bulletin posts** | posts waiting for their `publish:` day (or a Drive bulletin doc's "(from …)" day) | — |
| 14 | **New podcast feeds found** | a feed on the magazine sites the website does not show yet | add it under `sources.podcasts` if wanted |
| 15 | **Reminders** | dated facts kept by hand that run out soon (below); nothing when none is due | edit the file it names before the date |
| 16 | **Not updating for 7+ days** | the sources behind the issue in 8.1 | follow the issue |
| 17 | **Booth display (copies for offline)** | from the build job: the booth files saved for offline, their size and the limits, how many were downloaded, kept and removed; then a "Not saved: …" line per file, with why (the first 10 also as ⚠ *Booth display: a file was not saved for offline*) | a "Not saved" line that repeats day after day (14) |
| 18 | **Website: N pages, M MB** | from the build job | above 900 MB (section 12) |
| 19 | **Tests before publishing** | from the tests job: "All N tests passed …", or "The tests passed already for this code and content … — not run again.", or "**N of M tests failed — the website was NOT published**" with the failing tests (4.8) | a failure: 14.10 |

**Main pages of the magazine sites that did not load.** The document search checks its hub and kit pages
(`HUB_PATHS` and `KIT_PAGES` in [`scripts/sync/crawl_rules.py`](../scripts/sync/crawl_rules.py), such as
`/gvr-resources`) every day. When one does not give a readable page, *Notes* says, for example, "Document library
(Grapevine, La Viña and AA): 1 main page(s) of the magazine sites did not load: aagrapevine.org/gvr-resources (404 since 2026-10-06) —
checked again every day". Its documents stay on the site meanwhile (one 404 never drops them: a second one at
least a day later does). If the note repeats for days, open that page on the magazine's site: if it moved, put
the new path in `HUB_PATHS` / `KIT_PAGES`. A second possible note, "robots.txt of www.aagrapevine.org did not
answer properly (HTTP 503): its pages were left for the next run", needs nothing unless it repeats
([Automatic sources §3.17](automatic-sources.md#317-safety-nets-a-bad-day-at-a-source)).

**"Not checked for N days."** Every source is tried at least once a day (by the nightly full update). A source
that still works (its last try was fine) but that **no run has even tried for 3 days** shows **NOT CHECKED** in the
*Content sources* table, with "not checked for N days" as its problem, and a yellow ⚠ titled with its name: "not
checked for N days — no run has got to it since YYYY-MM-DD (the update stops before it, or no longer runs it); its
items stay on the site". It usually means the nightly full update stopped before that source, or is no longer
running (disabled, or GitHub skipped it). From **7 days** it also goes into the issue of 8.1, with the advice to open
the latest "Nightly full update" run and look for the step that failed or ran out of time. The document search is
never "not checked" while it is paused on purpose (`sources.crawler.minutes_per_run: 0`), nor in the days after it is
switched back on: each full update during the pause counts as its try (`run_all` gives `data/raw/pdfs.json` a fresh
`attempted`, and nothing else, and its row in the module table says "paused (sources.crawler.minutes_per_run: 0)").
A source that never ran yet is not counted either.

**Reminders.** `build_data` checks a few dated facts the committee keeps by hand (`status.json` → `reminders`), in
Central time, and the summary lists the ones that run out soon, each with its file (a blue ℹ *Reminders* counts
them). The site keeps working either way:

| Reminder | When it shows | Example |
|---|---|---|
| monthly tips (`config/carry.yml`) | the last month with tips is less than 12 months ahead | "config/carry.yml has monthly tips only through 2027-12; the /monthly/ pages look 12 months ahead — add tips for the next months." |
| the Tracker's panels (`config/expenses.yml`) | the last panel ends within 90 days, or ended | "… the last service panel (Panel 77) ends 2028-12-31 — add the next panel." Since Tracker 1.2.0 (October 2026) the Tracker works the panels out itself, so nothing needs adding: this line is harmless until the code drops it |
| GVR / RLV 101 (`config/orientation.yml`) | the panel named there has ended | "config/orientation.yml still names Panel 77 (from 2027-01), which ended 2028-12-31 — update the panel." |
| skip dates (`config/site.yml` → `recurring_events`) | an event's last skip date is within 90 days, or past | "… add next year's skip dates for lv-monthly-workshop." |
| the NETA 65 assemblies (`content/events`) | the last assembly listed starts within 60 days, or is past | "content/events: the last NETA 65 assembly listed is on … — add the next NETA 65 assemblies." |
| a price change (`config/site.yml` → `price_changes`) | its `notice_until` has passed | "… the price_changes block for … can be removed — its notice ended … (keep it until the stores show the new prices)." |

Real example: the summary rebuilt from the data of 2 October 2026 (abridged; the seconds vary from run to run; the
heading and the `writers_archive` row are as quick runs write them since the archive was added, with its numbers
of 4 October; the `build_data` row's items, 1400 that day, now also count the archive's 1,261 stories). First the
module table of a quick run:

```text
### Quick refresh
| module          | status     | seconds | items | new | note                                               |
| drive           | ✅ ok       | …       | 20    | 0   |                                                    |
| announcements   | ✅ ok       | …       | 2     | 0   |                                                    |
| podcasts        | ✅ ok       | …       | 298   | 0   |                                                    |
| youtube         | ⏭️ skipped  | 0.0     |       |     | --quick                                            |
| … (instagram, articles, editorial, weekly_open, shop, audio_project, meetings, events_external: skipped, --quick)
| writers_archive | ✅ ok       | …       | 1261  | 0   |                                                    |
| quote           | ✅ ok       | …       | 2     | 0   |                                                    |
| crawl           | ⏭️ skipped  | 0.0     |       |     | --quick                                            |
| build_data      | ✅ ok       | …       | 1400  |     | translated 0 new in 0.1s, 0 pending, 0 kept original |
| **total**       |            | …       |       |     | all ok                                             |
```

Then the rest (this part was produced by running the real summary code on that day's `data/site/status.json`):

```text
## Content sources
| Source | Status | Items | New in 7 days | Last success (UTC) | Problem |
| Google Drive (committee uploads) | OK | 20 | 14 | 2026-10-02 23:40 |  |
| Bulletin (content/bulletin) | OK | 2 | 2 | 2026-10-02 23:40 |  |
| Events (content/events) | OK | 9 | 0 | 2026-10-02 23:40 |  |
| … 12 more rows, all OK (13 since the writers archive was added) …
**Daily quote:** Grapevine Oct 2 · La Viña Oct 2
**PDF crawl:** 3434 pages known · 3434 crawled · 92 PDFs · 5 pages this run
**Translations:** 1919 cached · 0 new this run · 0 waiting for the next run
**Notes** (these sources still updated; only look into a note that repeats for a week):
- YouTube videos: details stopped: ERROR: [youtube] 3IlmqK3taOo: Sign in to confirm you’re not a bot. …
- Grapevine meetings (our Area and nearby): Alcohólicos Anónimos Dallas: feed: alcoholicosanonimosdallas.org did not answer; …
- Grapevine meetings (our Area and nearby): OKC Intergroup: feed: the answer is not a meeting list (not JSON); …
**Other calendars (optional, informational):**
- NETA 65 workshops: blocked by the site's bot protection · HTTP 403 · 0 event(s) · not asked this run (at most once a day)
**Scheduled bulletin posts** (not on the site yet):
- 2027-01-01 — New Grapevine and La Viña prices are now in effect (content/bulletin/2027-01-01-new-prices-in-effect.md)
```

and one annotation of its own: ℹ *Scheduled bulletin posts*: "1 post(s) will appear by themselves on their
day — the first on 2027-01-01 (see the run summary)." (The real runs that day also showed GitHub's own notice
that `ubuntu-latest` moves to Ubuntu 26 from October 19, 2026; see 13.8.) Everything here is fine: no PROBLEM
row, the notes are small, the blocked calendar is informational, and the scheduled post is waiting for its day.
(Since October 2026 a bot check is said plainly instead of YouTube's raw error: "YouTube videos: details stopped:
YouTube answered with a bot check (“confirm you’re not a bot”) — nothing is wrong on our side; videos keep their
last known details", and a meeting list that answers with one, as nwta66.org has since early October 2026: "Grapevine
meetings (our Area and nearby): Northwest Texas Area 66: nwta66.org answered with a bot check (HTTP 202) — nothing
is wrong on our side; the last good list is kept".)
Runs since the archive was added also have the **Writers archive** block right after *Translations*; the one the
files of 4 October 2026 give is shown in [Writers archive §6.1](writers-archive.md#61-the-run-summarys-writers-archive-lines).

### 6.4 What a problem looks like

A made-up example: Google Drive has failed for 9 days, and someone put a wrong `skip_dates` value under
`meeting:` in `config/site.yml`. The parts in "…" depend on the actual error.

```text
| Google Drive (committee uploads) | **PROBLEM** | 20 | 0 | 2026-09-24 04:53 | root folder unreadable: … — is it shared as 'Anyone with the link'? |
**Settings problems** (the rest of the site still updated — fix the file and save it again):
- config/site.yml meeting: skip date “2026-12-17” is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16)
**Not updating for 7+ days:** Google Drive (committee uploads) — reported in the issue *"A content source has stopped updating"*.
```

The annotations of the same run:

```text
⚠ Google Drive (committee uploads): root folder unreadable: … — is it shared as 'Anyone with the link'? (previous items kept) — no successful update for 9 days
⚠ Settings problem (meeting): config/site.yml meeting: skip date “2026-12-17” is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16)
```

The run is still **green**: the site was published with Drive's older items, and the meeting dates simply
ignore the wrong skip date. The *report* job then opens the issue in 8.1. What to do: section 14.1.

### 6.5 The other workflows' summaries

| Workflow | Its summary says |
|---|---|
| Morning check (new day by 5:30 AM) | "## Morning check — Friday, October 2 (Central time)", a ✅ / ⚠ / ❌ headline, then a table: New day (built at), Grapevine quote, La Viña quote, the Website update run it started or followed, what started the check, how, the full daily update |
| Code check (tests and test build) | "**Website:** N pages, M MB — builds fine with this change." from the job *Test build of the website* (the test results are in the *Python tests (offline)* job's log) |
| Monthly e-mail digest | "E-mail digest is not set up — nothing to do. (This is normal.)", "Not the time for the monthly digest (Central time: day 1, hour 3) — nothing to do.", "The 2026-09 digest was already sent — nothing to do.", "E-mail digest preview (not sent)" with the subject and the counts, "E-mail digest: waiting for the data", "Nothing new in September 2026 — no e-mail sent.", or "E-mail digest sent" with the subject and the number of recipients; after a send that broke off, "A send of the 2026-09 digest was started (…) but never confirmed — the e-mail MAY have gone out. …" (⚠ *Digest send not confirmed*); after a refused send, ✗ *The digest was not sent* ("The mail server took nothing … — the next try sends it.") |
| Weekly link check | lychee's link report, then "## Official links in config/site.yml" with "N OK · N broken · N could not be checked" |

---

## 7. Where it shows on the website: the Status page

**English:** <https://neta65.github.io/aagrapevine/status/> · **Spanish:**
<https://neta65.github.io/aagrapevine/es/status/>. Every page links to it from the footer (**Update status**,
next to "Last updated"). The page is built from `data/site/status.json` by [`src/pages/status.njk`](../src/pages/status.njk)
(the `statusView` function in [`eleventy/filters/community.js`](../eleventy/filters/community.js) turns the data
into the badges).

### 7.1 The parts of the page

| Part | What it shows (real values of 2 October 2026) |
|---|---|
| **At a glance** | "15/15 sources up to date" and "1 optional calendar unavailable" (16/16 since the Texas writers archive joined the sources); when something failed: "N/16 sources had a problem on the last run" (a "Delayed" source does not count as failed) |
| Three numbers | *Site last published* (the build time), *Items tracked* (1,372), *Found in the last 7 days* (65). Since the Texas writers archive joined, its rows count in both: in *Found in the last 7 days* all of them for the week after its first import, later only the stories a newer archive file adds |
| **Sources** | one row per source: a badge, "5 hours ago · 20 items · +14 this week"; a source on hold also says what was not found and since when; a source with notes from the last update has a folded *Notes from the last update (n) — for the site maintainer* (since October 2026; below) |
| Daily quote row | "The October 2, 2026 quotes came in at 2:05 AM CDT. Goal: on the site by 5:30 AM CDT every day." |
| **Other calendars** (*Optional*, folded) | each outside calendar: Working / Can't be read right now / Not answering / Not updated yet |
| **Document library** | "92 documents · all with a first-page preview" |
| **Machine translation** | 1,919 translations saved; folded *Technical details*: "… To correct a translation, edit data/translations/overrides.yml; the correction is used from the next update on."; below it, open: "258 glossary terms keep names like Grapevine, La Viña and GVR exactly as they are." (plus a line for texts still waiting, when there are any, and, when the translation memory or a model had a problem, "The last update could not translate everything as usual, so some new texts may stay in their original language for now. Everything translated before stays as it is." with the raw message) |
| **How an update works** | four steps: Start, New content, Translate, Publish |
| *Technical details (for the site maintainer)* (folded) | "Behind the scenes" with the **Open GitHub Actions** button, and "Daily quote — the last 7 mornings" (On time / Late / Not yet / Did not come in) |

The badges always pair an icon with a word:

| Badge (English / Spanish) | Rule |
|---|---|
| **OK** / *Al día* | the last run of that source worked |
| **On hold** / *En espera* | the last run worked but suddenly found far fewer items than before (none at all, or less than half once it had 10 or more), or a Drive folder that held files suddenly looked empty. Not believed the first time: the missing items stay on the site, and the row says "The last update did not find {n} items that were here before. To be safe, they stay on the site until the next update confirms they are gone." with *On hold since*. The next run that still misses them removes them; one that finds them again ends the hold ([Automatic sources §3.17](automatic-sources.md#317-safety-nets-a-bad-day-at-a-source)) |
| **Delayed** / *Retrasado* | it worked, but the last success is more than **3 days** old when the page was built: "No successful update in {n} days" |
| **Failed** / *Falló* | the last run failed; the row says calmly: "The last update couldn't refresh this source. Nothing was lost — everything it found before stays on the site, and the next update tries again." After 3 days it adds "No successful update in {n} days — if this continues, the site maintainer can check the details below.", plus the raw English error under *Technical details (for the site maintainer)* |
| **Not run yet** / *Aún sin ejecutar* | the source never ran (only on a brand-new copy) |

A source with nothing in it gets a hint instead of a bare 0. For example, an empty Drive says "Nothing uploaded
yet — files placed in the Panel 77 (2027–2028) folder on Google Drive show up on the site after the next
update."

**Notes from the last update.** Since October 2026 each source's small problems (its `stats.warnings`, the same
lines as the run summary's *Notes*) are on the page too, whatever its badge: a folded box *Notes from the last
update (n) — for the site maintainer* (Spanish: *Notas de la última actualización (n): para quien mantiene el
sitio*) under the source's row. The notes are shown in English as the update wrote them; on `/es/status/` the
caption says so.

> **Note:** the Status page uses friendlier source names than the run summary. Examples: run summary "Google
> Drive (committee uploads)" = page "Committee Google Drive" (*Google Drive del comité*); "Bulletin
> (content/bulletin)" = "Bulletin" (*Boletín*); "Events (content/events)" = "Events added by hand" (*Eventos
> agregados a mano*). The page names live in `src/_i18n/community.json` under `community.status.src.*`; sources
> without one there use the label from `SOURCES` in [`scripts/sync/build_data.py`](../scripts/sync/build_data.py).

Two things to remember:

- **Times on the page are in the visitor's own time zone** ("Times are shown in your local time zone."),
  except the daily-quote times, which are Central time and say so ("2:05 AM CDT").
- **The page shows the last *published* build.** If a build fails, the page keeps showing the previous state,
  so after a red ✗ look at the Actions tab, not at this page.

### 7.2 Other places that follow every publish

- The footer of every page: "Last updated …" (the build time).
- "Updated … ago" lines on several pages.
- The home page's daily quote card: until the new quote arrives, it shows the last one labelled "Yesterday".
- Every publish rebuilds every page, including the feeds `/feed.xml` and `/es/feed.xml`, the calendar files
  `/events.ics` and `/es/events.ics` (and, since October 2026, each month's
  `/monthly/YYYY-MM/neta65-grapevine-YYYY-MM-en.ics` and `/es/monthly/YYYY-MM/neta65-grapevine-YYYY-MM-es.ics`,
  and the two weekly open meetings' `/meetings/weekly-open-gv.ics` and `/meetings/weekly-open-lv.ics`, also under
  `/es/meetings/`), the share pages of the events (`/events/<card>/`, `/es/events/<card>/`), and the search
  indexes `/search-index.json` and `/es/search-index.json`. They are all as fresh as the last successful publish.

### 7.3 `/build.json`: the note the Morning check reads

<https://neta65.github.io/aagrapevine/build.json> is a small file about the current build. It is not linked from
any page and not in the search or the sitemap. The real copy on 2 October 2026:

```json
{"v":1,"built":"2026-10-02T23:40:50.636Z","day":"2026-10-02","tz":"America/Chicago",
 "quotes":{"gv":"2026-10-02","lv":"2026-10-02"},"data":"2026-10-02T23:40:30Z",
 "full":"2026-10-02T22:31:32Z","run":"37078627589","version":"ab2671a92b","commit":"c62f8ea"}
```

`day` = the build's Central day; `quotes` = the day of each magazine's quote on the home page; `full` = when the
last full run ran (from `status.json` → `full_update`); `run` = the GitHub run that built it; `commit` = the
commit that started that run (here the presentations change, not the robot's data commit `1ded6cf` that the
same run made a moment before building). The Morning check
counts the day as done when `day`, `quotes.gv` and `quotes.lv` are all today. The file is made by
[`src/pages/build-info.11ty.js`](../src/pages/build-info.11ty.js).

---

## 8. The three automatic issues and the failure e-mails

GitHub e-mails a new issue (and new comments) to everyone who **watches** the repository. On the repository
page, click **Watch** → **All Activity** (or **Custom** → tick **Issues**), once for each login that should get
them. As of October 2026 nobody watches it, so set this up.

### 8.1 "A content source has stopped updating"

Kept by the *report* job of *Website update*:

- **Opens** when a source has had no successful update for **7 days or more** (or never had one), or when a source
  that still works has not been **checked** (tried by any run) for 7 days or more (6.3, "Not checked for N days").
  The optional outside calendars never count.
- **Updates** its text silently after every run. It adds a comment (which GitHub e-mails) only when a **new**
  source joins the list.
- **Closes itself** with "Every content source is updating again (link to the run). Closing automatically."

Its text has a table *Source · Last successful update · Problem reported*, then **What to do**:

- Google Drive: check that the committee folder (`config/site.yml` → `drive` → `root_folder_id`) is still shared
  as **Anyone with the link — Viewer**.
- Instagram: Instagram keeps refusing the site's robot; add the Instagram token or list posts by hand (see
  [Automatic sources](automatic-sources.md)).
- Texas writers archive: "check the newest file in content/archive: it must keep the archive's columns, and a file
  much smaller than the one used before is not used (the run summary's "CSV file to fix" line says which). The
  archive already on the site stays meanwhile." ([Writers archive §10](writers-archive.md#10-the-safety-checks-and-what-to-do))
- A source that was not checked: "no run has got to it for N days: the update stops before it (open the latest
  "Nightly full update" run and look for the step that failed or ran out of time), or no longer runs it."
- Any other source: "the other website may have changed or be down. Send this issue to whoever helps with the
  website."

Then come links to the Status page, the latest run and the README's troubleshooting, and a line saying that
the issue updates and closes by itself. Error texts are shown as code, so an `@name` inside an error never
notifies a GitHub user.

You do not close it yourself: fix the cause, and the next run that reads the source closes it. (If you close it
by hand while the source is still failing, the next run simply opens a new one.)

### 8.2 "Broken links found by the weekly check"

Kept by the *Weekly link check*:

- **Opens** (or, if already open, gets a new comment, every Sunday) when lychee found broken links or an official
  link in `config/site.yml` is broken. The text starts "The weekly link check found problems. Most can be fixed
  in **config/site.yml** or the files in **content/**", followed by the report (cut at about 60,000 characters).
- **Closes itself** with "All links look good now (link to the run). Closing automatically." on a clean week.

Links inside content the robot fetches fix themselves when the other website is corrected. Links you wrote
(settings, `content/`) need your fix.

### 8.3 Who gets GitHub's "run failed" e-mails

GitHub, not this repository, sends these. Its rules:

| Run started by | The e-mail goes to |
|---|---|
| a schedule | the person who last **enabled** that workflow, or who last pushed a change to its `cron:` line |
| a push | the person who pushed |
| *Run workflow* | the person who clicked |
| the morning alarm | the owner of the alarm's key (NETA65) |
| the robot (the Morning check's refreshes) | nobody; that is why the Morning check fails itself when its refresh fails, and why two failed *Website update* runs in a row open the issue in 8.4 |

Each person also needs the e-mails switched on: profile picture → **Settings** → **Notifications** → *System* →
**Actions** → **Email**, and tick **Only notify for failed workflows**.

> **Owner step still open (October 2026):** the scheduled runs list **MKP715** as their actor, so their failure
> e-mails go to MKP715. To send them to NETA65 instead: sign in as **NETA65** → *Actions* → **Website update** →
> **⋯** (top right) → **Disable workflow**, then **Enable workflow**. Do the same for
> **Morning check (new day by 5:30 AM)**, **Monthly e-mail digest** and **Weekly link check**. Repeat after
> anyone else changes a `cron:` line.

A green run with yellow ⚠ never sends an e-mail. Neither does a failing source: that is what the issue in 8.1
is for.

### 8.4 "The website update keeps failing"

Since October 2026, kept by the same *report* job of *Website update* (its second step, *Open, update or close the
issue about failing updates*). It covers the runs no person started: those GitHub's schedule starts (the nightly
update, the midday and evening refreshes — GitHub e-mails their failure only to whoever last switched the workflow
on, [Email and alerts §3.16](email-and-alerts.md#316-githubs-run-failed-e-mails)) and those the Morning check starts
(the robot — GitHub e-mails nobody about them).

- **Opens** when such a run fails right after another *Website update* run that failed. One failure alone can be a
  passing hiccup, so it opens no issue. A run GitHub replaced in the queue, or one somebody cancelled, does not
  count as the run before; a job that ran out of time counts as a failure. A run a person started never opens it:
  GitHub e-mails that person (8.3).
- **Updates** its text silently after each later failure ("The website update has failed N times in a row"). It
  adds a comment, which GitHub e-mails, only when another job starts failing: "Now also failing: …".
- **Closes itself** after the next run in which every job worked: "The website update works again: this run
  published the site (link). Closing automatically."

Its text names the job that failed, with what to do:

| Job | The issue says |
|---|---|
| *Sync content + translate* | the site data could not be built, or the data commit could not be saved; the site was still published with the data it had (if the other jobs worked) |
| *Test the code before publishing* | a change broke the tests, so nothing was published; the run summary lists the failing tests: fix the change or undo it (14.10) |
| *Build website* | the website could not be built (often a text missing from `src/_i18n` after an edit): fix the change or undo it (14.4) |
| *Publish to GitHub Pages* | GitHub Pages did not take the new version, usually GitHub's own trouble: **Re-run failed jobs**, or wait for the next run |

The live site stays as it was published last. The Morning check still reports a morning that did not reach the
site (14.7).

---

## 9. The data folder and what the robot commits

The repository is the database: every run's results are committed, so the history is also the backup.

| Folder or file | Written by | Edit by hand? | What it is |
|---|---|---|---|
| `data/raw/<source>.json` (16 files: announcements, articles, audio_project, drive, editorial, events_external, instagram, manual_events, meetings, pdfs, podcasts, quote, shop, weekly_open, writers_archive, youtube), 1.9 MB before the writers archive was added | only the matching sync module | **no** | everything a source ever found: `{source, updated, attempted, first_harvest, ok, error, stats, items}` (`writers_archive.json`: the Texas rows of the archive files in `content/archive`, replaced on every run) |
| `data/site/*.json` (19 files: announcements, articles, audio_project, booth, drive, editorial, episodes, events, instagram, meetings, pdfs, quote, shop, spotlight, status, videos, weekly_open, whatsnew, writers_archive), 3.5 MB before the writers archive was added | only `scripts/sync/build_data.py` | **no** | what the pages read, with translations added (`booth.json`, the booth display's Drive files, has none) |
| `data/state/crawl-state.json` (1.4 MB), `data/state/ics_feeds.json`, `data/state/sources-seen.json` | the PDF crawler; `build_data.py`; the step *Remember the commit the full-update sources ran with* | no | the PDF search's progress; the last answer of each outside calendar; the last commit the sources only the full update reads ran with (4.2) |
| `data/translations/cache.json` (0.8 MB) | the translator | no | every translation made so far (one per line) |
| `data/translations/overrides.yml`, `glossary.yml` | **people** | **yes** | your translation fixes; saving one rebuilds the site ([Translations](translations.md)) |
| `data/geo/texas_places.json` | people, rarely (`python -m scripts.dev.build_texas_gazetteer`) | rarely | Texas town → county, for the published writers (the recent stories and the Texas writers archive) and the Meetings page's "Our Area"; saving it starts a quick run that also reads the meeting lists again, and a Code check |

In `data/raw`: `updated` moves only when a run worked, `attempted` on every try (and `pdfs.json`'s also on each
full update while the document search is paused, `minutes_per_run: 0`), and `ok: false` + `error` mark a failed run
(the older items are kept). Since October 2026 every raw file also says what the run changed, `changes` (items
added, removed, held back), and, while a sudden drop is not believed yet, `held` (since when, how many, a few of
their titles: the Status page's **On hold**, 7.1). `data/site/status.json` is the health report behind the Status
page and the run summary. The fields: [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md).

The booth display's saved photos and videos are not in `data/` and never in Git: the build job keeps them in
`.cache/booth-media/`, saved in the Actions cache between runs (section 4.2), and publishes them with the site. Its
own guide: [Booth display](booth.md).

### 9.1 What the robot commits

The *Commit refreshed data* step of *Website update*:

- **Who:** `github-actions[bot]`, with the built-in token (a push made with it never starts a workflow).
- **What:** `git add -A -- data/raw data/site data/state data/translations/cache.json src/assets/cache`:
  new, changed **and deleted** files there. Never `config/`, `content/` (the archive files included),
  `overrides.yml`, `glossary.yml` or code.
- **When:** only if something changed; and **always tried**, even after a failed, timed-out or cancelled sync
  (so a long PDF search never loses its progress).
- **Message:** see the table in 4.2, always ending in `[skip ci]`.
- **If someone pushed meanwhile:** up to 5 tries; between tries it rebases with `-X theirs` (in a generated file
  the fresh data wins; your edits to other files are kept).

Real examples from 2 October 2026: `1ded6cf` "chore(data): content sync after settings/content change
2026-10-02 [skip ci]" changed 14 files (for example `data/raw/drive.json`, `data/site/status.json`,
`data/translations/cache.json`); `be94f87` "chore(data): daily content sync 2026-10-02 [skip ci]" changed 35
files, including `data/state/crawl-state.json` and a new Instagram thumbnail in `src/assets/cache/ig/`.

Never committed (git ignores them): `.cache/models/` (the translation models, kept in the Actions cache),
`.cache/booth-media/` (the booth display's saved photos and videos, kept in the Actions cache too),
`node_modules/`, `_site/`, `.tmp/`, `.venv/`, `__pycache__/`, `*.tmp`, `*.part`, `*.corrupt-*` and `*.bad-*` (copies
of an unreadable raw file or translation memory, set aside: 9.2), `.env` files, `*.pem`, `client_secret*.json`. Drive files are never copied into the repository: the site links Google's own
viewers and thumbnails (the booth display's copies are published with the site, never committed).

### 9.2 Resetting something on purpose

Most hand edits in `data/` start no run (`overrides.yml`, `glossary.yml` and `data/geo/` are the exceptions), so
press *Run workflow* afterwards.

| Goal | Do this | Side effect |
|---|---|---|
| Re-read one source from scratch | delete `data/raw/<source>.json` | its `first_seen` dates are lost: for a week the Status page counts all its items as "found this week", and the next monthly e-mail can list them as added that month |
| Re-crawl both magazine sites | delete `data/state/crawl-state.json`, then run with `crawl_minutes` = `300` | about 6 hours; may need several runs |
| Re-translate one text | add it to `data/translations/overrides.yml` | — (preferred) |
| Re-translate everything | delete `data/translations/cache.json` (or raise `ENGINE_VERSION` in `scripts/sync/translate.py`) | many runs of translation work |
| Fresh translation models | *Actions* → **Caches** → delete `translation-models-v1-…` | one 175 MB download on the next run |
| Download the booth display's media again | *Actions* → **Caches** → delete every `booth-media-v1-…` | the next runs download every booth file again (up to 15 minutes of downloads a run) |
| Undo a bad data commit | `git revert <sha>`, then *Run workflow* | — |

> **Note:** [docs/OPERATIONS.md → Resetting state](../docs/OPERATIONS.md#resetting-state) says a deleted raw file
> makes everything look "new" for 14 days. For most sources the code no longer does that: items found by a
> source's first run count as old news (`found_ts` in `scripts/sync/build_data.py`), so the "New" badges follow
> the items' own dates. The exception is the committee's own files: the events written in `content/events`
> count from the day the site first saw them, so after deleting `data/raw/manual_events.json` every upcoming
> one shows "New" again for 14 days (a bulletin post follows its own date).

> **Note:** a raw file broken by a hand edit (or a bad merge) is not overwritten, and since October 2026 it no
> longer empties its part of the site. Until its source runs again, every build keeps what the last build made of
> it in `data/site` (whole files such as `videos.json`, or that source's items in `announcements.json`,
> `events.json` and `whatsnew.json`), and its Status page row says "Failed" with "data/raw/<source>.json could not
> be read (…) — the site keeps what the last build had for it until the file is fixed (restore it from the git
> history) or this source's next update rebuilds it". When the source itself runs, it renames the file
> `<source>.json.corrupt-<time>`, rebuilds that source from scratch and marks it failed once, with a message that
> ends "restore the file from the git history to keep older items and first-seen dates" (a source that collects
> over time, such as YouTube or the Library, then shrinks on the site until the file is restored). The
> `*.corrupt-*` copy is git-ignored, so on GitHub it is not kept: restore the file from the history. An unreadable
> translation memory (`data/translations/cache.json`) is set aside the same way, as `cache.json.bad-<time>`
> ([Translations](translations.md)).

---

## 10. Who can do what: MKP715 and NETA65

**NETA65** owns the repository (admin). **MKP715**, the login on the owner's PC, is a collaborator with **write**
access.

| Task | MKP715 (write) | NETA65 (owner) |
|---|:---:|:---:|
| Edit files on github.com, push from a PC, merge pull requests | yes | yes |
| *Run workflow*, *Re-run*, *Cancel* (all five workflows) | yes | yes |
| Download artifacts (the e-mail preview), delete old runs | yes | yes |
| Comment on, close and reopen issues | yes | yes |
| *Disable / Enable workflow* | yes, but then the failure e-mails go to MKP715 | yes: do it as NETA65 to get them (8.3) |
| Delete an Actions cache (*Actions* → *Caches*) | yes | yes |
| Rewrite the history (force push) | yes, while `main` has no branch protection | yes |
| See, add, change or delete **secrets** (`SMTP_*`, `DIGEST_*`, `GOOGLE_API_KEY`, `IG_*`, `TSML_KEY_*`) | **no** | yes |
| *Settings → Pages* (source "GitHub Actions", custom domain) | **no** | yes |
| *Settings → Actions*, *Environments* (`github-pages`), *Rules / Branches* | **no** | yes |
| Invite or remove collaborators; rename, move, make private or delete the repository | **no** | yes |
| Make the morning alarm's key (fine-grained token, resource owner NETA65) | **no**: a key only reaches its owner's repositories | yes |
| *Watch* the repository to get the issues by e-mail | yes (to MKP715's inbox) | yes |

Secrets live only in *Settings → Secrets and variables → Actions* (repository secrets). Nobody can read one back
after saving; it can only be replaced or deleted. The repository needs **none** to run; they only switch on
extras ([docs/SETUP-GITHUB.md → Where to add secrets](../docs/SETUP-GITHUB.md#where-to-add-secrets)).

---

## 11. Run the sync, the build and the tests on a PC

You never *need* a PC: everything runs on GitHub. A PC is useful to try a change before you push it, to see an
error up close, or to preview the site. These steps are for Windows PowerShell.

### 11.1 One-time setup

You need **Python 3.12 or 3.13** (python.org; the workflows use 3.12, and the full test suite also passes on
3.13), **Node.js 22** (20 at least; nodejs.org) and **Git** (or GitHub Desktop).

```powershell
git clone https://github.com/NETA65/aagrapevine.git
cd aagrapevine
py -3.13 -m venv .venv                     # a private Python just for this project (or: py -3.12)
.\.venv\Scripts\Activate.ps1               # the prompt now starts with (.venv)
python -m pip install -r requirements.txt  # the sync's packages (also brings tzdata: Windows has no time-zone data)
npm ci                                     # the site tools, exactly as package-lock.json lists them
$env:PYTHONIOENCODING = "utf-8"            # in every new PowerShell window: accents and dashes print correctly
```

- If PowerShell says *running scripts is disabled on this system*, run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip the activation and type
  `.\.venv\Scripts\python.exe` wherever this guide says `python`.
- `.venv/` and `node_modules/` are git-ignored: they never end up in a commit.

### 11.2 The sync on a PC

You do not need the sync to look at the site: the build reads the data already committed in `data/site/`.

```powershell
python -m scripts.sync.drive --dry-run                    # one source: fetch and print, write nothing
python -m scripts.sync.run_all --quick --no-translate     # Drive, bulletin/events files, podcasts, archive files, daily quote
python -m scripts.sync.run_all --crawl-minutes 5          # a short full run (may download ~175 MB of models the first time)
python -m scripts.sync.translate --download               # fetch the two translation models into .cache\models
python -m scripts.sync.translate "Welcome, new GVRs!" --to es   # try one translation (nothing is saved; may download a model)
python -m scripts.sync.translate --stats                  # the translation memory: 1919 cached on 2 Oct 2026
```

What each `run_all` form runs (checked with the real code, with the fetching switched off):

| Command | Runs, in order |
|---|---|
| `run_all --quick` | drive, announcements, podcasts (no feed discovery), writers_archive, quote, then `build_data` |
| `run_all --quick --also instagram,meetings` | the same, plus instagram (no post look-ups) and meetings in their usual places: drive, announcements, podcasts, instagram, meetings, writers_archive, quote, `build_data` (what a push that changed `content/instagram.yml` and `data/geo/texas_places.json` runs; `--also` never runs the crawl, and does nothing without `--quick`) |
| `run_all --morning` | drive (5-minute box), announcements, quote, podcasts, writers_archive, `build_data`; on the 1st also articles (hub pages only) and shop, before writers_archive; on the 15th shop |
| `run_all --crawl-minutes 40` | all 14 sources, the PDF crawl for 40 minutes, `build_data` |
| `run_all --crawl-minutes 0` | all 14 sources, `build_data` (the crawl is skipped; while `sources.crawler.minutes_per_run` is 0 its row says "paused (sources.crawler.minutes_per_run: 0)" and `data/raw/pdfs.json` gets a fresh `attempted`, so the paused search is never "not checked") |
| `run_all --only youtube,podcasts` | podcasts, youtube, then `build_data` (`--only` still rebuilds the site data) |
| `run_all --skip crawl --no-translate` | all 14 sources, `build_data` without new translations (saved ones are still used) |
| `run_all --no-build --only drive` | drive only |
| `npm run sync` | the same as `python -m scripts.sync.run_all` with nothing after it: everything, with a 40-minute crawl (too long for a PC) |

Other options: `--translate-minutes N`, `--out FOLDER` (write the site data somewhere else).
`run_all` only exits with an error when `build_data` fails; a failed source is a row in its table, which is titled
by the kind of run: "Full update", "Quick refresh" or "Morning refresh". In a quick or morning run it calls
`build_data --keep-full-update`, so `status.json` → `full_update` keeps the value of the last full update (4.2).
For more detail in the log while you hunt a problem, set `$env:GV_LOG_LEVEL = "DEBUG"` first (back to normal:
`Remove-Item Env:GV_LOG_LEVEL`).

> **Before you commit anything after a local sync:** the sync rewrote the robot's files. Put them back so you
> commit only your own change:
>
> ```powershell
> git status                                    # the robot's files show as changed
> git restore data/raw data/site data/state data/translations/cache.json src/assets/cache
> git clean -nd src/assets/cache                # lists new thumbnails it downloaded; run again with -fd to delete them
> ```

Keep local runs short (`--dry-run`, `--crawl-minutes 5`): the magazine sites ask for 5 seconds between
requests, and the daily run already visits them.

### 11.3 Build and look at the site

```powershell
npm start      # builds into _site\ and serves http://localhost:8080 ; rebuilds when you save a file (Ctrl+C stops it)
```

Open <http://localhost:8080/status/> and <http://localhost:8080/es/status/>. (`npm run build` builds once
without serving; `npm run clean` deletes `_site`.)

To build **exactly like GitHub Pages** (strict about missing texts; links then start with `/aagrapevine/`, so this
build is for checking, not for clicking around):

```powershell
$env:PATH_PREFIX = "/aagrapevine/"; $env:I18N_STRICT = "1"; npx @11ty/eleventy
Remove-Item Env:PATH_PREFIX, Env:I18N_STRICT      # back to normal
```

- Faster, only some pages: `$env:ONLY = "status,search"; npx @11ty/eleventy` (then `Remove-Item Env:ONLY`).
- Without `I18N_STRICT`, a missing button text shows as its raw key (for example `community.status.glance`); on
  GitHub the same thing stops the build.
- In Git Bash instead of PowerShell: `MSYS_NO_PATHCONV=1 PATH_PREFIX=/aagrapevine/ I18N_STRICT=1 npx @11ty/eleventy`
  (without `MSYS_NO_PATHCONV=1`, Git Bash turns `/aagrapevine/` into a Windows folder path).
- The site works offline (it has a service worker), so the browser may keep old pages of `localhost:8080`. To
  start clean: Edge → F12 → *Application* → *Storage* → **Clear site data**.

### 11.4 Run the tests

```powershell
python -m unittest discover -s tests                                   # all of them
python -m unittest discover -s tests -v                                # the same, with each test's name (what Code check runs)
python -m unittest tests.test_morning -v                               # one file
python -m unittest tests.test_morning.UpdateWorkflow -v                # one class
python -m unittest tests.test_morning.UpdateWorkflow.test_plan_step -v # one test
python -m scripts.ops.gate_tests                                       # the tests Website update runs before it publishes (4.8)
```

On the owner's PC on 6 October 2026 the whole suite printed `Ran 2010 tests in 254.251s` and `OK (skipped=30)`:
about 4 minutes. Skipped is fine: tests that need the translation models or a fresh local build skip themselves.
Two things to know on Windows:

- Without `node_modules` (no `npm ci`), about 55 tests that run the site's own JavaScript skip silently: run
  `npm ci` once before you trust a green result.
- Run the suite in **Git Bash** (or with Git's `usr\bin` folder on the `PATH`). About 40 tests run workflow steps
  with `bash` and its tools; from a plain PowerShell window they fail with `date: command not found`, which says
  nothing about the code.

`gate_tests` prints the same results and, at the end, the lines it would write to the run summary ("All N tests
passed (M skipped) — the website may be published." and how many it left to the Code check); its exit code is 0
when every test passed, 1 when one failed or none was found.

### 11.5 Look at pages in a real browser (Playwright with Edge)

Optional, for checking how pages really look, on a phone-sized screen, with no JavaScript errors.
Playwright is **not** in `requirements.txt` (the workflows do not need it):

```powershell
python -m pip install playwright      # into the .venv only
```

Do **not** run `playwright install`: it downloads a separate Chromium (blocked on the owner's PC, and not needed).
`channel="msedge"` drives the Edge that Windows already has. Save this as `.tmp\look.py` (`.tmp/` is
git-ignored; and never name a script after a Python module such as `inspect.py` or `json.py`, or Python loads
yours instead of its own):

```python
# .tmp/look.py: phone-size screenshots of a few pages, and any JavaScript errors
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"          # npm start; or "https://neta65.github.io/aagrapevine" for the live site
PAGES = ["/status/", "/es/status/", "/events/", "/es/events/"]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")              # Edge: nothing to download
    context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for path in PAGES:
        errors.clear()
        page.goto(BASE + path, wait_until="networkidle")
        name = path.strip("/").replace("/", "-") or "home"
        page.screenshot(path=f".tmp/{name}.png", full_page=True)
        print(path, page.title(), "| JS errors:", errors or "none")
    browser.close()
```

Run it with `python .tmp\look.py` while `npm start` runs in another window. Pointed at the live site on
2 October 2026 (status pages only), it printed `/status/ Update status · Grapevine / La Viña — NETA 65 | JS
errors: none` and the same for `/es/status/` (*Estado de la actualización*), and saved `status.png` and
`es-status.png`.

To see a page as it will look on another day (for example when new prices start), add
`page.clock.set_fixed_time("2027-01-01T08:00:00-06:00")` before `page.goto(...)`. The page's own date logic
then believes it is that time ([docs/OPERATIONS.md → When Grapevine announces new prices](../docs/OPERATIONS.md#when-grapevine-announces-new-prices)).

### 11.6 Two more tools that only look

```powershell
python -m scripts.notify.send_digest --dry-run       # the monthly e-mail → .tmp\digest.html + .tmp\digest.txt; sends nothing
python -m scripts.ops.morning_check --check-only --site https://neta65.github.io/aagrapevine
```

The second one reads the live `/build.json` and says what the Morning check would do (no token needed; it asks
a magazine's page, once, only when today's build is up but that quote is late, and only from 2:00 AM Central).
Real output on the evening of 2 October 2026 (the lines it prints between its first line and the summary):

```text
New day: ✅ built 6:40 PM CDT (2026-10-02)
Grapevine quote: ✅ 2026-10-02
La Viña quote: ✅ 2026-10-02
Started by: a computer (not GitHub)
How: It was already there — no morning refresh needed.
```

---

## 12. Repository size and GitHub limits

| Measure | Now (October 2026) | Limit or warning | Where you see it |
|---|---|---|---|
| The repository (history included) | about 11 MB as GitHub counts it (the history was squashed in October 2026) | GitHub recommends under 1 GB; strong warnings near 5 GB | `git count-objects -vH` in a fresh clone |
| `data/raw` + `data/site` | 1.9 + 3.5 MB | grows a few MB a year | — |
| `data/state/crawl-state.json` | 1.4 MB | grows only when the magazine sites add pages | — |
| `data/translations/cache.json` | 0.8 MB | grows with new titles | — |
| `src/assets/cache/` thumbnails | 4.8 MB (233 small WebP/JPEG files: 129 PDF covers, 57 Instagram, 26 stories, 18 shop, 3 podcasts) | ~20 KB per new one; Instagram's are capped at 130 per account | — |
| History growth | — | roughly 50–150 MB a year (small daily data commits) | — |
| The published website | about 10 MB compressed (the Pages upload of 2 October 2026), plus the booth display's saved media: at most `booth.max_total_mb` (400 MB; never more than 800, whatever the setting says) | **GitHub Pages: 1 GB**; the deploy warns above 900 MB | "**Website:** N pages, M MB" in every Website update and Code check summary; the booth's part in "**Booth display (copies for offline)**" |
| One file in git | — | GitHub warns above 50 MB and refuses above 100 MB | the push fails |
| One job | — | GitHub stops any job after **6 hours** (hence the 300-minute crawl cap) | the run fails at the timeout |
| Actions caches (translation models ~175 MB, the booth display's media up to 400 MB, pip, npm, link checker, the tests' remembered passes `tests-passed-v1-…`, a few bytes each) | — | 10 GB per repository; a cache unused for 7 days is removed (the daily runs keep the models, the booth media and the newest pass alive) | *Actions* → *Caches* |
| Downloads ("artifacts") | the digest's markers `digest-sending-YYYY-MM`, `digest-sent-YYYY-MM`, `digest-unsent-YYYY-MM` kept 40 days, `digest-preview` 14 days, `link-check-report` 7 days, the Pages upload 1 day | — | a run's *Artifacts* |

GitHub's own published limits for Pages also include a soft 100 GB of traffic a month and a 10-minute limit
per deployment; this site is far from both. Actions minutes are free and unlimited for a **public** repository,
which is one reason the repository must stay public ([docs/SETUP-GITHUB.md](../docs/SETUP-GITHUB.md)).

What keeps it small: photos, videos and other big files stay on Google Drive (the site links them and never
copies them — except the booth display's copies, which are published with the site within `booth.max_total_mb`
and never committed), thumbnails are small and capped, and the CI copies are shallow (history size does not slow
the daily run). If the history ever grows too big, see section 15.

---

## 13. Going further: change the automation's code

Read this before you edit a workflow or a script. Each recipe gives the file, the name to search for, a small
example, and the tests to run. Line numbers change, so search for the quoted text instead.

**Always, before you push:** `python -m unittest discover -s tests` on a PC (section 11.4). After the push,
watch the *Code check* run: it runs the same tests on GitHub.

### 13.1 Move a schedule (and keep the 4-hour-early rule)

Where the timetables are:

| Workflow | File and search text | Test that pins it |
|---|---|---|
| Website update, nightly full update | `.github/workflows/update.yml`: `- cron: "17 7 * * *"`, **and** `FULL_CRON="17 7 * * *"` (step *Decide what to sync*), **and** `github.event.schedule == '17 7 * * *'` (the `run-name:` line) | `tests/test_morning.py` → `UpdateWorkflow.test_the_three_schedules_4_hours_early`, `test_the_nightly_full_update_keeps_clear_of_the_morning_alarm`, `test_plan_step`; `tests/test_run_wiring.py` → `Schedule.FULL_CRON` (`test_the_strings_agree`); `tests/test_run_names.py` → `UpdateTitles` |
| Website update, midday refresh | `update.yml`: `- cron: "7 12 * * *"` only (and a comment) — the plan step, the title and the commit message treat it as "any other schedule" | `UpdateWorkflow.test_the_three_schedules_4_hours_early`; `Schedule.MIDDAY_CRON` (`test_the_strings_agree` checks that the plan step, the title and the commit step do not use it) |
| Website update, evening refresh | `update.yml`: `- cron: "7 20 * * *"`, **and** `github.event.schedule == '7 20 * * *'` (the `run-name:` line), **and** `"${SCHEDULE:-}" = "7 20 * * *"` (step *Commit refreshed data*) | the same, plus `Schedule.EVENING_CRON`, `UpdateWorkflow.test_commit_messages`, `tests/test_run_names.py` |
| Morning check (new day by 5:30 AM) | `.github/workflows/morning.yml`, `- cron: "25 0-11,21-23 * * *"` | `MorningWorkflow.test_schedule_is_plain_utc_off_the_hour_through_the_night` |
| Monthly e-mail digest | `.github/workflows/monthly-digest.yml`, `- cron: "7 8,11,14,17,20 1-3 * *"` | `tests/test_send_digest.py` → `WorkflowSchedule.test_when_it_tries` (the last try must stay after noon Central, even in winter) |
| Weekly link check | `.github/workflows/link-check.yml`, `- cron: "40 8 * * 0"` | none |

The arithmetic: **UTC hour = the Central hour you want it to really start − 4 (the early setting) + 5 (summer
time)**, so in summer simply "wanted hour + 1". In winter the same line runs one hour earlier in Central time.

The nightly and the evening strings are each written in three places in `update.yml` (comments aside);
`Schedule.test_the_strings_agree` checks that every copy agrees, so change them together. `test_the_three_schedules_4_hours_early` also checks that
each schedule, 4 to 6 hours late, lands in its part of the Central day, in summer and in winter (the windows
`(5, 8)`, `(10, 13)` and `(18, 21)`, in hours): change the window too when a run moves to another part of the day.
Moving the nightly also meets `test_the_nightly_full_update_keeps_clear_of_the_morning_alarm`: on time (a run of up to
2 hours) it must end before 4:30 AM Central, and 4, 5, 6 or 8 hours late it must start at least 30 minutes after it,
on a CDT day and on a CST day.

Example: let the evening refresh aim for about 8–10 PM Central instead of 7–9 PM (20 − 4 + 5 = 21):

```yaml
# .github/workflows/update.yml → on: → schedule:
    - cron: "7 21 * * *"     # was "7 20 * * *": 4:07 PM CDT on time; GitHub usually starts it about 8–10 PM
# the run-name line:
  || github.event_name == 'schedule' && github.event.schedule == '7 21 * * *' && 'Evening refresh (GitHub schedule)'
# step "Commit refreshed data":
          elif [ "$EVENT" = "schedule" ] && [ "${SCHEDULE:-}" = "7 21 * * *" ]; then
```

```python
# tests/test_morning.py → class UpdateWorkflow → test_the_three_schedules_4_hours_early
        self.assertEqual(self.on["schedule"], [{"cron": "17 7 * * *"}, {"cron": "7 12 * * *"}, {"cron": "7 21 * * *"}])
        for cron in ("17 7 * * *", "7 12 * * *", "7 21 * * *"):
        for s, (lo, hi) in zip(self.on["schedule"], ((5, 8), (10, 13), (19, 22))):
# tests/test_morning.py → test_commit_messages: each "7 20 * * *" becomes "7 21 * * *"

# tests/test_run_wiring.py → class Schedule
    EVENING_CRON = "7 21 * * *"
```

Then:

1. Run `python -m unittest tests.test_morning tests.test_run_wiring tests.test_run_names -v`.
2. Update the comments above the `cron:` lines and the times quoted in the README (section 1), in this guide (4.1)
   and in [docs/OPERATIONS.md → Workflows](../docs/OPERATIONS.md#workflows).
3. After the push, **as NETA65**: *Actions* → the workflow → **⋯** → *Disable workflow* → *Enable workflow*.
   Otherwise the failure e-mails of the timed runs go to whoever pushed the `cron:` change (8.3).

**A fourth schedule** is a quick refresh by itself (only `FULL_CRON` is a full run), titled "Midday refresh (GitHub
schedule)" and committed as "midday refresh" unless you give it a `run-name:` branch and a commit-message line of
its own, like the evening one. The tests expect exactly three `cron:` lines: update
`test_the_three_schedules_4_hours_early` with it.

### 13.2 Make another kind of saved file rebuild the site

The lists are `on:` → `push:` → `paths:` in `update.yml` (*Website update*) and in `check.yml`
(*Code check (tests and test build)*).
GitHub reads `update.yml`'s list top to bottom and the **last line that matches wins**, so a line that brings a
file back in must come **after** the `!` line that left it out.

Real example: this is how a corrected `data/geo/texas_places.json` was made to rebuild the site (the README in
that folder stays documentation):

```yaml
# .github/workflows/update.yml → on: → push: → paths:
      - "!data/**"                          # the bot's own data commits
      - "data/geo/**"                       # …but a fix of the Texas places list must rebuild
      - "!data/geo/README.md"               # (re-included by the line above)
      - "data/translations/overrides.yml"   # …and so must a translation fix
      - "data/translations/glossary.yml"    # …and so must a glossary change
```

```yaml
# .github/workflows/check.yml → on: → push: → paths:
      - "data/geo/**"                 # the Texas places list (the place tests read it)
```

A file a source only the full update reads while it syncs also belongs in `FILES` in
[`scripts/ops/push_modules.py`](../scripts/ops/push_modules.py) (`"data/geo/texas_places.json": "meetings"`), so
the push's quick run runs that source too (4.2; tested by `tests/test_push_modules.py`).

Simpler for a new hand-edited file: put it in a folder that already rebuilds (`content/`, `config/` or `src/`).
Never add `data/raw`, `data/site`, `data/state` or `data/translations/cache.json`: those are the robot's files,
and leaving them out of the list is one of the three safeguards (with the built-in token and `[skip ci]`, see
4.3) that keep its data commits from starting runs.
Test: `python -m unittest tests.test_morning -v` (it also checks that `check.yml` still lists `.github/workflows/**`,
and `UpdateWorkflow.test_a_fix_of_the_texas_places_list_rebuilds_and_is_tested` checks the `data/geo` lines).

### 13.3 Change what the quick and morning refreshes read

In [`scripts/sync/run_all.py`](../scripts/sync/run_all.py):

| Name | Today | Meaning |
|---|---|---|
| `QUICK_MODULES` | `("drive", "announcements", "podcasts", "writers_archive", "quote")` | the sources of every quick run **and** the base of the morning refresh |
| `QUICK_ARGS` | youtube `--no-backfill`, podcasts `--no-discover`, articles `--no-details`, instagram `--no-enrich` | lighter options in the quick and morning modes |
| `MORNING_EXTRA` | `{1: ("shop", "articles"), 15: ("shop",)}` | extra sources of the morning refresh on those days of the month |
| `MORNING_ARGS` | drive `--max-minutes 5`, articles `--no-archive` | the morning's time boxes |
| `FULL_ONLY` | worked out by itself: youtube, instagram, editorial, weekly_open, audio_project, meetings, events_external | when these last ran = "the last full run" (`status.json` → `full_update`, read by the Morning check); a push that changed their input runs them with `--also` (4.2) without moving `full_update` (`build_data --keep-full-update`) |

Example: refresh the Grapevine Weekly Open meeting details (one page on aagrapevine.org) on every quick run.
Keep the names in the same order as `MODULES`:

```python
# scripts/sync/run_all.py
QUICK_MODULES = ("drive", "announcements", "podcasts", "weekly_open", "writers_archive", "quote")   # was without "weekly_open"
```

Then `--quick` runs drive, announcements, podcasts, weekly_open, writers_archive, quote; `--morning` runs drive,
announcements, quote, podcasts, weekly_open, writers_archive; `FULL_ONLY` loses `weekly_open`. Take its entry out of
`SETTINGS` in [`scripts/ops/push_modules.py`](../scripts/ops/push_modules.py) too (`tests/test_push_modules.py`
expects that table to list exactly `FULL_ONLY`). Update the expected lists in `tests/test_morning.py` → class
`RunAllMorning` (`test_a_normal_morning`, `test_the_first_of_the_month`, `test_the_fifteenth`,
`test_the_monthly_sources_once_a_day`, `test_the_sources_only_the_full_update_reads`, `test_quick_is_unchanged`),
and the wording of the `skip_crawl` and `morning` boxes (`update.yml` → `workflow_dispatch:` → `inputs:`) and of
README section 7.

> Keep these lists short: the morning refresh has 20 minutes to put the day's quote up by 5:30 AM, and every
> extra source on aagrapevine.org or aalavina.org waits 5 seconds per page.

### 13.4 Change when the "stopped updating" issue opens, or its advice

In `.github/workflows/update.yml`:

- **How many days:** job `sync` → step *Write run summary* → search `STALE_DAYS = 7`. The "not checked" warning
  starts at `UNCHECKED_DAYS = 3` in the same step; the sources left alone on purpose are the `paused` set there (the
  document search while `sources.crawler.minutes_per_run` is 0). The other half of that rule is in
  `scripts/sync/run_all.py` (`crawl_paused`, `_note_paused_crawl`): a full update during the pause gives the search
  a fresh `attempted`, so it is not "not checked" right after the pause either.
- **Advice per source:** job `report` → search `HINTS = {` (today `drive`, `instagram` and `writers_archive`). A
  source without an entry gets the general advice; a source that was not checked gets the `UNCHECKED` text.
- **The title:** job `report` → search `TITLE = "A content source has stopped updating"`. If you change it, close
  the old issue by hand: the job finds its issue by the exact title.
- **The other issue of the same job,** "The website update keeps failing" (8.4), is its second step, *Open, update
  or close the issue about failing updates*: `TITLE`, the advice per job (`HINTS`, keys `sync`, `tests`, `build`,
  `publish`) and which runs count (`FAILED`, `unattended`). Tested by `tests/test_automation.py` → class
  `FailingUpdates`, which runs the step against a stand-in for GitHub.

```python
# update.yml → job report → step "Open, update or close the report issue"
          HINTS = {
              "drive": "check that the committee folder (config/site.yml → drive → root_folder_id) is still "
                       "shared as **Anyone with the link — Viewer** (README → section 2).",
              "instagram": "…",
              "writers_archive": "…",
              # NEW: advice for the podcasts
              "podcasts": "check that each feed: address under sources.podcasts in config/site.yml still opens "
                          "in a browser.",
          }
```

The Python inside a workflow's `run: |` block must keep its indentation exactly (10 spaces before `HINTS`).
If you change the number of days, also change "7 days" in the README (sections 8 and 15) and in
[docs/SETUP-GITHUB.md → Step 8](../docs/SETUP-GITHUB.md#step-8--get-told-when-something-breaks).
Test: `python -m unittest tests.test_morning tests.test_events_feeds -v` (they run the summary step that
decides which sources go into the issue; `UpdateWorkflow.test_the_report_issue_says_what_to_do` checks the
writers archive's advice and the "not checked" text — check the quotes and commas of any other change by eye).

### 13.5 Add a line to the run summary

Job `sync` → step *Write run summary* in `update.yml`. It reads `data/site/status.json` (as `s`) and collects
Markdown lines in `lines`. Example: show how many events the site lists. Put this just before the line
`c = s.get("crawl") or {}`:

```python
          n_events = (s.get("counts") or {}).get("events")
          if n_events is not None:
              lines += ["", f"**Events on the site:** {n_events}"]
```

Tried on a copy with the data of 2 October 2026: the summary gained `**Events on the site:** 40` between the
*Daily quote* and *PDF crawl* lines. Test: `python -m unittest tests.test_morning.UpdateWorkflow -v` (these
tests run the step's real code). To make a line also appear in the *Annotations* box, `print()` a line that
starts with `::notice title=…::` or `::warning title=…::`, like the existing ones.

### 13.6 Change when the Status page says "Delayed"

[`eleventy/filters/community.js`](../eleventy/filters/community.js) → function `statusView` → search
`age > 3 * DAY`:

```js
      stale: state === "ok" && age !== null && age > 2 * DAY,   // was 3 * DAY: "Delayed" after 2 days
```

The wording is `community.status.stale_help` in `src/_i18n/community.json` ("No successful update in {n} days",
both languages). The badge is worked out when the page is built. Test: the full suite, then look at
<http://localhost:8080/status/> with `npm start`.

### 13.7 Other knobs

| To change… | Where (search for) | Test or note |
|---|---|---|
| the daily PDF search length (0 pauses it) | `config/site.yml` → `sources:` → `crawler:` → `minutes_per_run` ([Settings](settings.md)) | no code change |
| the time boxes (translation, step) | `update.yml` → step *Decide what to sync* → `translate=$(( 345 - minutes - 30 - 5 ))`; morning: `translate=5`, `budget=20` | `tests/test_morning.py` → `UpdateWorkflow.test_plan_step` |
| the morning goal (5:30 AM) | `config/site.yml` → `site:` → `morning_goal: "05:30"`, and the "5:30 AM" in `morning.yml`'s `name:` line | `tests/test_run_names.py` checks that the two agree; the alarm time itself is set at cron-job.org |
| how the Morning check waits and asks | `scripts/ops/morning_check.py` → `WINDOW_BEFORE` (3 h 30 min before the goal: 2:00 AM), `WINDOW_AFTER`, `POLL_EVERY`, `FOLLOW_MAX`, `MAX_RUNS`, `GUARD_MAX = timedelta(minutes=170)` | `MorningWorkflow.test_update_job` checks that `GUARD_MAX + FOLLOW_MAX + LIVE_MAX` + 10 minutes fit the 240-minute job |
| what the robot commits | `update.yml` → step *Commit refreshed data* → `for p in data/raw data/site data/state …` | — |
| the build checks (and, in `update.yml` only, the 900 MB warning) | `update.yml` and `check.yml` → step *Check the build* | `UpdateWorkflow.test_build_json_is_checked` |
| the booth display's media: size limits, download time | `config/site.yml` → `booth:` → `max_file_mb`, `max_total_mb` ([Settings](settings.md)); the 15 minutes of downloads: `BOOTH_MEDIA_MINUTES` in `scripts/build/booth-media.mjs`, inside the step's `timeout-minutes: 20` and the build job's 35 | `tests/test_booth_media.py` |
| the websites the link check skips | `link-check.yml` → the `--exclude` lines | none |
| the run titles | the `run-name:` line at the top of each workflow (`update.yml`'s first branch must stay `MORNING_TITLE` in `scripts/ops/morning_check.py`) | `tests/test_run_names.py` (it works out the title of every kind of run) |
| a workflow's name in the Actions list | the `name:` line at the top of its file — never the file name, which the morning alarm, `morning_check.py`, the badge and the links use | `tests/test_run_names.py` → `OtherTitles.test_the_names_stay`; the guides name the workflows too |
| which sources a push also runs | `scripts/ops/push_modules.py` → `SETTINGS` (the parts of `config/site.yml` each full-update-only source reads), `FILES` (the files they read) | `tests/test_push_modules.py`; `UpdateWorkflow.test_a_push_also_runs_the_sources_whose_input_it_changed` |
| when "not checked" starts | `update.yml` → step *Write run summary* → `UNCHECKED_DAYS = 3` | `UpdateWorkflow.test_a_source_not_checked_for_days` |
| the reminders of dated settings | `scripts/sync/build_data.py` → `REMINDER_CHECKS`, `CARRY_AHEAD_MONTHS` (12), `PANEL_REMINDER_DAYS` (90), `SKIP_DATES_REMINDER_DAYS` (90), `ASSEMBLY_REMINDER_DAYS` (60) | `tests/test_writers_archive.py` → `Reminders`; `UpdateWorkflow.test_reminders` |
| the booth media cache key | `update.yml` → step *Work out the booth display's settings fingerprint* | `UpdateWorkflow.test_the_booth_medias_cache_key_reads_only_the_booth_settings` |
| the writers archive's cut-off guard | `config/site.yml` → `writers_archive:` → `min_rows_ratio` ([Writers archive §10.1](writers-archive.md#101-the-cut-off-guard-and-min_rows_ratio)) | no code change |
| the Python or Node version | `python-version: "3.12"` / `node-version: 22` in each workflow | the Code check |
| which tests *Website update* leaves to the Code check | `scripts/ops/gate_tests.py` → `DATA_TESTS` (a test id, as `python -m unittest` names it, and what it judges) (4.8) | `tests/test_automation.py` → `GateTests.test_every_data_test_is_there` |
| what the tests' fingerprint leaves out | `update.yml` → job `tests` → step *Fingerprint the code and the content* (the `':!data/raw'` … list) | `tests/test_automation.py` → `Publishing.test_the_fingerprint_leaves_out_only_the_bots_data` |
| the monthly digest's markers and its **force** box | `monthly-digest.yml` → step *Is it time, and is the e-mail digest set up?*; `scripts/notify/send_digest.py` → `--prepare`, `--send-prepared` | `tests/test_send_digest.py` |

### 13.8 Pin the runner's Ubuntu version (only if GitHub's update breaks a run)

Every job says `runs-on: ubuntu-latest` (13 jobs: 5 in `update.yml`, 3 in `morning.yml`, 2 in `check.yml`, 2 in
`link-check.yml`, 1 in `monthly-digest.yml`). GitHub moves `ubuntu-latest` to a newer Ubuntu from time to
time and announces it as a notice on the runs (in autumn 2026: "The ubuntu-latest label will migrate to
Ubuntu 26 beginning October 19, 2026"). If runs start failing right after
such a move (for example Python 3.12 cannot be set up, or a `date` command behaves differently), pin the old one:

```yaml
    runs-on: ubuntu-24.04      # was ubuntu-latest
```

No test pins this line. Try the newer image again a few weeks later.

### 13.9 Add a whole new content source

That is a bigger job (a new module in `scripts/sync/`, a label in `SOURCES` in `build_data.py`, a site file, a
Status page row, maybe the e-mail). Follow
[docs/OPERATIONS.md → Adding a new source](../docs/OPERATIONS.md#adding-a-new-source) step by step.

---

## 14. Troubleshooting

### Where problems are reported

| Place | What you find there |
|---|---|
| The run's **Annotations** (yellow ⚠, blue ℹ, red ✗) | every warning and error, each with a title, for example "Google Drive (committee uploads)" or "Settings problem (meeting)" |
| The **run summary** | the tables of section 6.3, including *Settings problems* and the *files to fix* |
| The **log** of the red step | the exact error lines (copy the last 20 when you ask for help) |
| The **Status page** | per source: Failed or Delayed, with the raw error under *Technical details (for the site maintainer)* |
| **Issues** | a source failing for 7+ days; broken links; timed runs that fail twice in a row |
| **E-mail** | GitHub's "run failed" e-mails (8.3); cron-job.org's e-mails about the morning alarm |

### Symptom → cause → fix

| What you see | Likely cause | What to do |
|---|---|---|
| The site did not change | the run failed, is still running or waiting; the workflow is disabled; the file you saved does not rebuild (docs, `data/`); GitHub Pages' cache; the browser's offline copy | open the newest *Website update* run; *Enable workflow* if it says disabled (14.8); *Run workflow* with **skip_crawl**; wait 10 minutes; reload the page (if a small "Updated" notice appears, choose **Reload**) |
| A yellow ⚠ titled with a source's name | that source failed this run; its older items stay on the site | nothing for a day or two; then 14.1 |
| Status page: a source **On hold** | it suddenly found far fewer items (or a Drive folder looked empty); the missing ones stay on the site until the next update confirms the drop | nothing: the next update removes them if they are really gone, or ends the hold ([Automatic sources §3.17](automatic-sources.md#317-safety-nets-a-bad-day-at-a-source)) |
| *Notes*: "N main page(s) of the magazine sites did not load: … (404 since …) — checked again every day" | a hub or kit page of the document search did not answer properly; its documents stay | if it repeats for days, open the page; if it moved, update `HUB_PATHS` / `KIT_PAGES` in `scripts/sync/crawl_rules.py` (6.3) |
| *Notes*: "… answered with a bot check … — nothing is wrong on our side" | another website (a meeting list, YouTube) turned the robot away; the last good copy is kept | nothing; it usually passes |
| A yellow ⚠ "not checked for N days — no run has got to it since …" (**NOT CHECKED** in the summary) | no run has tried that source for 3 days or more: the nightly full update stops before it (it failed or ran out of time), or does not run (disabled, skipped) | open the latest "Nightly full update" run and its red or timed-out step; *Enable workflow* if needed (14.8); *Run workflow* with every box empty. From 7 days the issue in 8.1 lists it |
| **CSV file to fix** under *Writers archive* in the summary | a new archive file in `content/archive` was not used (a missing column, far fewer rows than before, unreadable); the older rows stay on the site, and the file used before, if it is still in the folder, "stays in use until" the new one is fixed | [Writers archive §10](writers-archive.md#10-the-safety-checks-and-what-to-do) |
| **Reminders** in the summary | a dated fact kept by hand runs out soon (monthly tips, a panel, skip dates, the next assemblies, an old price-change block) | edit the file the line names before its date (6.3); the site keeps working meanwhile |
| ⚠ "Translation models missing" or "Translation is not working" | the free translation models could not be downloaded | 14.2 |
| Red ✗ right after you saved `config/site.yml` | a YAML typo (spaces at the start of a line, a missing quote) | 14.3 |
| ⚠ "Event files to fix" or "Bulletin files to fix" | a mistake in a file in `content/events` or `content/bulletin` | fix that file and save it again; its last good version stays on the site meanwhile (14.3 b) |
| ⚠ "Booth folder file to fix" | a file in the Drive booth folder that the booth display can never show (its type, a note with no text, `(from …)` after `(until …)`) | do what the line says: rename, convert or replace the file in Drive ([The Drive panel folder §3.6](drive-panel-folder.md#36-the-booth-folder-new)) |
| ⚠ "Booth display: a file was not saved for offline" | a booth file too big (`booth.max_file_mb`), over the folder's limit (`booth.max_total_mb`), a web page from Drive instead of the file (too many downloads of it that day, or Drive could not check it for viruses), or no answer; until it is saved, a video or sound file is left out of the show and a picture shows only online | a failed download: nothing, the next run tries again; a file too big: shorten it, or raise the limit ([Booth display](booth.md)) |
| ⚠ "Settings problem (meeting)" (or `recurring_events`, `ics_feeds`, `price_changes`, `content_events`) | one entry in the settings was skipped or corrected; the message says why | fix the entry and save; see [Settings](settings.md) |
| ⚠ "Settings problem (translations)" | a YAML typo in `overrides.yml` or `glossary.yml`; new translations pause | 14.3 c |
| Red ✗ at *Build the website* with `Missing i18n key: …` | a button or heading text is missing in `src/_i18n/` | add the key in both languages ([Translations](translations.md)); the live site is unaffected |
| Red ✗ at *Read GitHub Pages settings*; the site shows "404 — There isn't a GitHub Pages site here" | Pages is not set to deploy from GitHub Actions | **NETA65**: *Settings → Pages → Source: GitHub Actions*, then *Run workflow* |
| Red ✗ at the job *Publish to GitHub Pages* mentioning environment protection | the `github-pages` environment does not allow `main` | **NETA65**: *Settings → Environments → github-pages* → allow `main` |
| Red ✗ at *Commit refreshed data* | another push five times in a row, or branch protection | 14.5 |
| Red ✗ at *Install Python packages* (sync job) | the Python package service had a hiccup, or a just-released package version does not install (`requirements.txt` lets packages move up within their major version, yt-dlp without any limit) | **Re-run failed jobs** later; if it repeats, the log names the package: send it to whoever helps with the website. The site is still published with the last data |
| Red ✗ on *Code check* | the change you pushed broke the build or a test | 14.6 |
| Red ✗ *Tests failed — not published* on *Website update* (job *Test the code before publishing*) | a change broke the tests; the site was not published and keeps the version before | 14.10 |
| Red ✗ *Not published*: "The website was built from … but the tests ran on … (a change arrived between the two)" | a push arrived between the build and the tests | nothing: the next run publishes (or *Run workflow* with **skip_crawl**) |
| Issue "The website update keeps failing" | two timed or Morning-check runs failed in a row | open the run it links and the job it names (8.4); it closes itself after the next run that works |
| ⚠ *Digest send not confirmed* on *Monthly e-mail digest* | a send broke off between "being sent" and "sent", so the e-mail may have gone | check the group; if it did not arrive, *Run workflow* with *Preview only* unticked and **force** ticked (4.6) |
| Red ✗ on *Morning check*, or no quote at 5:30 AM | the morning refresh failed, the alarm did not fire, or the magazine was late | 14.7 |
| No timed runs for a day or more | the workflow is disabled, or GitHub skipped a firing | 14.8 |
| A grey "cancelled" run nobody cancelled | a newer run took its place in the queue | nothing |
| Dozens of *Morning check* runs | the hourly backstop | nothing; the no-op ones are deleted after a day |
| Issue "A content source has stopped updating" | a source failed for 7+ days | follow its *What to do*; it closes itself (8.1) |
| Issue "Broken links found by the weekly check" | a link in the settings or in `content/` moved | fix the address in `config/site.yml` or the `content/` file; it closes itself (8.2) |
| ⚠ "build.json is missing — the Morning check cannot see this build." | `src/pages/build-info.11ty.js` was broken by a change | fix or undo the change; the Code check fails on the same thing |
| ⚠ "The site is N MB — GitHub Pages allows 1 GB." | something big ended up in the site | section 12: big files belong on Drive |
| Status page: a source "Failed" with "data/raw/….json could not be read …" or "… was unreadable …" | a hand edit (or a bad merge) broke a raw data file; the site keeps that source's last good data meanwhile | restore that file from the history (9.2) |
| An item or its button is missing on the site, though the source has it | the build repaired or hid a link it could not use | open the *Build the website* step's log and search for `[links]`: each line names the item and the bad link; fix it where it comes from (the Drive file, the `content/` file, the setting) |
| A notice on every run about `ubuntu-latest` moving to a newer Ubuntu | GitHub's own announcement | nothing, unless runs start failing after the move (13.8) |
| The Status page still shows a problem you fixed | it shows the last *published* build; sources that only the full run reads update with the next full run (unless your push changed their input: then its run read them, 4.2) | *Run workflow* with every box empty |
| The monthly e-mail did not arrive | it is off (no secrets), waiting for data, or nothing was new | [E-mail and alerts](email-and-alerts.md) |
| cron-job.org e-mails that the alarm failed (401, 403, 404, 422) | the alarm's key expired or lacks a permission, the address changed, or the Morning check is disabled | [E-mail and alerts](email-and-alerts.md) and [README → 10 d](../README.md#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended) |

### 14.1 A source is down

1. Open the run. The ⚠ annotation names the source, its error and the days since its last success, for example
   "… (previous items kept) — no successful update for 2 days".
2. Seen for only a day or two: wait. Every run tries again, and nothing is lost.
3. Read the error:
   - **Google Drive**: `root folder unreadable: … — is it shared as 'Anyone with the link'?` → in Google Drive,
     right-click the committee folder **A65_GV** (the folder `drive.root_folder_id` in `config/site.yml` points
     to) → **Share** → *General access* → **Anyone with the link** — **Viewer**. See
     [The Drive panel folder](drive-panel-folder.md).
   - **Instagram**: Instagram refuses robots now and then and usually recovers. For a lasting fix NETA65 adds the
     Instagram token secrets, or the posts are listed by hand ([Automatic sources](automatic-sources.md)).
   - **A magazine site** (articles, editorial, shop, quote …): the site may be down, or it changed its layout and
     the module needs a code fix. Look on a PC, without writing anything: `python -m scripts.sync.articles --dry-run`
     (any module name works the same way).
   - **YouTube** "details stopped: YouTube answered with a bot check (“confirm you’re not a bot”) — nothing is
     wrong on our side; videos keep their last known details" (in *Notes*; before October 2026 the raw "Sign in to
     confirm you're not a bot"): YouTube pushing back on the listing tool. `yt-dlp` is updated by every run
     (`requirements.txt` does not cap it); it usually passes.
   - **A meeting list** "… answered with a bot check (HTTP 202) — nothing is wrong on our side; the last good list
     is kept" (in *Notes*; nwta66.org, since early October 2026): that office's earlier meetings stay; nothing to do.
   - **An outside calendar** "blocked by the site's bot protection" (neta65.org, HTTP 403): informational only.
     Add those events by hand in `content/events` ([Flyers and events](flyers-and-events.md)).
4. To try again at once: *Run workflow* (every box empty for sources only the full run reads; **skip_crawl** is
   enough for Drive, the bulletin, the events files, the podcasts, the daily quote and the writers archive files).
5. After 7 days the issue in 8.1 opens. Follow its advice, or send it to whoever helps with the website.

### 14.2 Translation models missing

**Signs:** ⚠ "Translation models missing" ("Only 0 of 2 translation models could be downloaded (is
argos-net.com down or moved? …") on a run that had to download them; ⚠ "Translation is not working" ("12 texts
are waiting but none could be translated this run …"); the Status page's *Machine translation* card says
"12 texts are still waiting — they are translated on the next update."

**What it means:** new titles stay in their original language. Translations made before are not affected, and
your fixes in `data/translations/overrides.yml` still apply (they need no model).

**What to do:**

1. Wait a day. Each run downloads the models again when the cache has none.
2. Still failing after a few days: check that the two addresses in `MODEL_URLS` in
   [`scripts/sync/translate.py`](../scripts/sync/translate.py) still open. On a PC,
   `python -m scripts.sync.translate --download` prints `en_es: ready` and `es_en: ready` (or `MISSING`).
3. If the files moved, put the new addresses in `MODEL_URLS`. The cache key is worked out from those addresses,
   so the next run downloads and caches the new files by itself. Keep the 1.0 models: the code warns
   "Do NOT switch es_en to 1.9: it needs a different (BPE) tokenizer."
4. To force a fresh download: *Actions* → **Caches** → delete `translation-models-v1-…` → *Run workflow*.

### 14.3 A YAML typo

**a) In `config/site.yml`** (the most common red ✗):

- *Website update* goes red twice: at *Sync sources and translate* (the site data cannot be built without the settings)
  and at *Build the website*, whose log shows for example
  `YAMLException: bad indentation of a mapping entry (26:2)`, meaning line 26, column 2. The Python side says the
  same in its own words: `ParserError: while parsing a block mapping … expected <block end>, but found
  '<block mapping start>' … line 26, column 2`. The *Code check* goes red too.
- **The live site stays as it was** (GitHub Pages keeps the last good version).
- The sources that ran are marked failed in `data/raw` (their older items stay) and that is committed. The next
  good run clears them.

Fix it: open the failed run → the red step → find the line number → open `config/site.yml` on GitHub → fix that
line (usually the spaces at its start, or a missing closing quote) → **Commit changes**. The quick run that
starts is green again. To undo instead: open the file → **History** → the version before your change → copy it
back.

Check the file on a PC before you commit (it prints nothing when the file is fine):

```powershell
python -c "import yaml; yaml.safe_load(open('config/site.yml', encoding='utf-8'))"
```

> **Note:** if a scheduled full run happened while the typo was there, the sources only the full run reads (for
> example YouTube or Instagram) keep showing "Failed" on the Status page until the next full run. Press
> *Run workflow* with every box empty to clear them at once.

**b) In the header of a `content/events/*.md` or `content/bulletin/*.md` file:** not fatal. The run stays green
with ⚠ *Event files to fix* (or *Bulletin files to fix*), for example:

```text
events/2027-03-19-neta65-spring-assembly.md: the header between the --- lines is not valid (line 4): mapping values
are not allowed here — if a value contains ": " (for example a title like "Reminder: Assembly"), put the whole
value in quotes: title: "Reminder: Assembly"
```

or `the header has no closing --- line (add a line with just --- below the header)`. Until you fix it, that
event or post keeps its last good version on the site. (A title that simply contains ": " is fine: such a header
is read line by line.) More in [Flyers and events](flyers-and-events.md) and [Bulletin](bulletin.md).

**c) In `data/translations/overrides.yml` or `glossary.yml`:** not fatal either. ⚠ *Settings problem
(translations)*: "data/translations/overrides.yml could not be read (ParserError: …) — new texts stay untranslated
until it is fixed". The saved translations are used as they are; nothing new is translated until the file is
fixed. See [Translations](translations.md).

### 14.4 A failed deploy

The job *Build website* (called *Build & publish website* before October 2026) or *Publish to GitHub Pages* is red.
The data commit already happened, and the live site keeps its previous version. Look at which step failed:

| Step | Typical message | Fix |
|---|---|---|
| *Install site tools* | `npm ci` errors | a just-merged `chore(deps)` pull request (revert it, README → Housekeeping), or a short outage of the package service (**Re-run failed jobs** later) |
| *Read GitHub Pages settings* | Pages is not enabled for GitHub Actions | **NETA65**: *Settings → Pages → Source: GitHub Actions* |
| *Build the website* | `YAMLException …` / `Missing i18n key: …` / a template error with a file name and line | 14.3; add the missing text; or undo the last code change |
| *Check the build* | `_site/index.html is missing — the build did not produce a home page.`, `_site/es/index.html is missing — the Spanish site was not built.` or `The stylesheet was not built.` | undo the last code change and look at the build log |
| *The tests passed on the commit that was built* (job *Publish to GitHub Pages*) | `Not published: The website was built from … but the tests ran on … (a change arrived between the two)` | nothing: the next run publishes |
| *Publish to GitHub Pages* (job *Publish to GitHub Pages*) | environment protection, or a GitHub hiccup | **NETA65** allows `main` in *Settings → Environments → github-pages*; or **Re-run failed jobs** later |

After the fix, push it (that starts a quick run that publishes), or press **Re-run failed jobs** (it builds the
same commit the run's sync job named: for a fix, push it instead). A red job *Test the code before publishing*
is 14.10.

The booth display's download and cache-save steps (section 4.2) never turn the job red: they may fail on their own
(`continue-on-error`), and the site is then published without the copies that run could not make.

### 14.5 The data commit failed

- `Data commit: Could not rebase the data commit onto main. Tomorrow's run will redo the sync.` or
  `Could not push the data commit after 5 attempts.`: someone (or something) pushed at the same moment, again
  and again. Nothing to fix. What this run fetched is not saved, but the next run fetches it again, and the
  website was still published from what `main` already had.
- `permission denied`, `403` or `protected branch`: a rule protects `main`. **NETA65**: *Settings → Rules* (or
  *Branches*) → add **GitHub Actions** to the bypass list. *Workflow permissions* does not need changing.

### 14.6 Code check is red

1. Open the run and see which job failed: *Test build of the website* (same causes as 14.4) or *Python tests
   (offline)*. (After a new writers archive file, a red `test_the_headline_numbers` means the site would not use the
   file — its message is the run summary's **CSV file to fix** text — or the file holds no rows by Texas writers or
   no believable year; the exact numbers are pinned only for the files of 4 October 2026:
   [Writers archive §6.3](writers-archive.md#63-the-code-check).)
2. In the test log, search for `FAIL:` or `ERROR:`. The line names the test, for example
   `FAIL: test_plan_step (tests.test_morning.UpdateWorkflow.test_plan_step)`, followed by what was expected.
3. Run that one test on a PC: `python -m unittest tests.test_morning.UpdateWorkflow.test_plan_step -v`.
4. Fix it or undo the change (14.9). The live site keeps working meanwhile, and since October 2026 the
   *Website update* run of the same push did not publish the change either (14.10), unless the failing test is
   one of the few it leaves to the Code check (`DATA_TESTS`, 4.8).

On a Dependabot pull request, a red ✗ simply means: do not merge it.

### 14.7 Morning check red, or today's quote is not up

1. Open the *Morning check* run of that morning. Its table names the *Website update* run it started; open that
   run and look at its red step.
2. A yellow "A daily quote is late at the source" is not a failure: the magazine had not published it. The site
   shows the last quote labelled "Yesterday" until an update brings the new one.
3. No *Morning check* run around 4:30 AM Central: the morning alarm is not set up, or it failed (cron-job.org
   e-mails its owner). See [E-mail and alerts](email-and-alerts.md).
4. *Website update* disabled: the Morning check cannot start it and goes red. *Enable workflow* (14.8).
5. A long crawl was still running (someone started a 300-minute run in the evening): start long crawls in the
   morning.
6. To bring the quote now: *Actions* → *Morning check (new day by 5:30 AM)* → *Run workflow*. It does only what
   is missing.

### 14.8 Nothing runs on schedule

- The workflow says **disabled**: GitHub turns timed workflows off after 60 days without repository activity
  (the daily data commits normally prevent that), or someone disabled it. *Actions* → the workflow →
  **Enable workflow**, preferably as **NETA65** so the failure e-mails go there. Do it for *Website update*,
  *Morning check (new day by 5:30 AM)*, *Monthly e-mail digest* and *Weekly link check*. A disabled Morning
  check also turns the morning alarm away (HTTP 422).
- GitHub skipped a firing on a busy day: the Morning check starts the full run after 30 hours without one, or
  press *Run workflow*.
- Never add an automatic "enable workflow" keep-alive: GitHub would then send the failure e-mails to the robot.

### 14.9 Undo a change, or roll the website back

- **Undo your own commit:** GitHub Desktop → *History* → right-click the commit → *Revert Changes in Commit* →
  *Push origin*. On a PC with Git: `git revert <sha>` then `git push`. On github.com: open the file → *History*
  → open the earlier version → copy it → edit the current file → paste → *Commit changes*.
- **Old content back on the website:** revert the commits first, then run *Website update*. Do not count on
  re-running an old run: *Re-run all jobs* publishes what `main` has now, and *Re-run failed jobs* the commit that
  old run had saved, with that day's data (5.2).
- **A bad data commit:** `git revert <sha>`, push, then *Run workflow* (pushes to `data/` start no run).

### 14.10 Tests failed — not published

**Signs:** *Website update* is red; its job **Test the code before publishing** has the red annotation *Tests
failed — not published* ("Some tests failed (or none was found), so this run does not publish the website (the live
site keeps the version before). See the run summary."); the job *Publish to GitHub Pages* was skipped; the run
summary's **Tests before publishing** section lists the failing tests. Usually the *Code check* of the same push is
red too.

**What it means:** a change since the tests last passed broke something. The data commit was still made, but
nothing was published: the live site shows the version before that change, and every later run stays unpublished
until the tests pass again (the daily runs with them: they test the same code).

**What to do:**

1. Open the job's log and search for `FAIL:` or `ERROR:`: each names the test and what was expected (as in 14.6).
2. Fix the change, or undo it (14.9). The run of that save tests again and publishes when they pass.
3. In a hurry and not sure which change it was: undo the most recent commit of code, settings or content. The site
   then publishes the version before it, with that day's data.
4. A test that fails because of the day's synced data, not because of a change (it fails on every run, with no new
   commit, and the Code check of the last change was green): add its id to `DATA_TESTS` in
   [`scripts/ops/gate_tests.py`](../scripts/ops/gate_tests.py) (4.8). The Code check still runs it.

"**No tests were found — the website was NOT published** … the tests/ folder could not be read." means the job
could not even load the tests (a broken `tests/` folder): fix or undo the last change to it.

---

## 15. History clean-ups (squashing)

Every data commit adds a little history (roughly 50–150 MB a year), so GitHub's 1 GB recommendation is years
away; the history has been squashed to a single commit several times, most recently in October 2026. If it
ever needs doing again, follow
the exact recipe in [docs/OPERATIONS.md → Repository size](../docs/OPERATIONS.md#repository-size). In short:
make a backup first (`git bundle create ..\aagrapevine-backup-YYYY-MM-DD.bundle --all`), push all your own
commits, then build one new commit from GitHub's current files (`git commit-tree "origin/main^{tree}"`) and
force-push it with `--force-with-lease` (refused if someone pushed meanwhile; MKP715's write access is enough
while `main` has no branch protection), and reset your local copy to it. Because a force-pushed new first commit
starts **no** push-triggered workflow, press *Run workflow* for **Code check (tests and test build)** and
**Website update** right after (and *Enable workflow* if a timed workflow was switched off for the operation).
Everyone else with a copy must clone again, and a pull request opened before the squash (Dependabot's too) must
be closed, never merged: merging it would bring the old history back. Squashing does not un-publish anything:
commits that a pull request once pointed to can stay reachable on GitHub until GitHub Support removes them, so a
leaked password or token must be revoked and replaced, not just squashed away.

---

## 16. Good practice

- **Everything here is public.** The repository, every commit message, every run log and summary, and every
  issue can be read by anyone. Never paste a password, key, token or personal e-mail address into a file, a
  commit message, an issue or a workflow. Secrets go only in *Settings → Secrets and variables → Actions*
  (NETA65).
- **Anonymity.** Commit messages and issue texts are kept in the history: no full names, no faces, no personal
  stories. Name roles instead ("the chair", "the District 3 GVR").
- **Everything in the Drive panel folder becomes public on the site** after the next run that reads Drive.
  If a file should not be public, it does not belong there.
- **Attraction, not promotion.** The automatic texts (the Status page, the issues, the e-mail) stay calm and
  factual; keep any wording you add the same way.
- **Be polite to the magazine sites.** Keep local runs short, and use 300-minute crawls only when the saved
  progress was lost: one of them asks the two sites for up to about 3,600 pages, 5 seconds apart.
- **One change at a time,** then watch the *Code check*. Run the tests on a PC before bigger changes.
- **Keep the timetables 4 hours early,** keep `[skip ci]` out of your own commit messages, and do the
  NETA65 *Disable → Enable* step after any schedule change (8.3).
- **Watch the repository** (8), so the three automatic issues reach a person.

---

## 17. See also

- [How-to guides: index](README.md)
- [The Drive panel folder](drive-panel-folder.md) · [File types](file-types.md) ·
  [Flyers and events](flyers-and-events.md) · [Bulletin](bulletin.md) ·
  [Photos, slides and reports](photos-slides-reports.md) · [Booth display](booth.md) ·
  [Presentations](presentations.md)
- [Settings](settings.md) · [Translations](translations.md) · [E-mail and alerts](email-and-alerts.md) ·
  [Automatic sources](automatic-sources.md) · [Pages and code](pages-and-code.md) ·
  [Writers archive](writers-archive.md)
- The workflows: [update.yml](../.github/workflows/update.yml) · [morning.yml](../.github/workflows/morning.yml) ·
  [check.yml](../.github/workflows/check.yml) · [monthly-digest.yml](../.github/workflows/monthly-digest.yml) ·
  [link-check.yml](../.github/workflows/link-check.yml) · [dependabot.yml](../.github/dependabot.yml)
- The scripts: [run_all.py](../scripts/sync/run_all.py) · [common.py](../scripts/sync/common.py) ·
  [build_data.py](../scripts/sync/build_data.py) · [morning_check.py](../scripts/ops/morning_check.py) ·
  [push_modules.py](../scripts/ops/push_modules.py) · [gate_tests.py](../scripts/ops/gate_tests.py) ·
  [send_digest.py](../scripts/notify/send_digest.py)
- The website side: [status.njk](../src/pages/status.njk) · [build-info.11ty.js](../src/pages/build-info.11ty.js)
- Background: [README → 7. Running the update right now](../README.md#7-running-the-update-right-now) ·
  [README → 8. Is everything working?](../README.md#8-is-everything-working) ·
  [README → 15. Troubleshooting](../README.md#15-troubleshooting) ·
  [docs/OPERATIONS.md](../docs/OPERATIONS.md) (the technical runbook) ·
  [docs/SETUP-GITHUB.md](../docs/SETUP-GITHUB.md) (first-time setup, secrets, moving the repository) ·
  [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md) (the data files, field by field)
