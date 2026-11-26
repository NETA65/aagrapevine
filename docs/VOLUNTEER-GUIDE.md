# Volunteer guide — the Grapevine / La Viña website

*Two pages for committee volunteers. No programming needed. En español: [GUIA-VOLUNTARIOS.md](GUIA-VOLUNTARIOS.md).*

The website ([grapevine.neta65.org](https://grapevine.neta65.org/), Spanish at
[/es/](https://grapevine.neta65.org/es/)) **updates itself about four times a day**: a robot on GitHub reads the
committee's Google Drive folder, the magazines' websites, the podcasts and YouTube, translates what is new and
publishes the site. Nobody has to press anything. If one update fails, the site simply keeps the last good
version until the next one works.

## 1. Is the website working?

Look in this order — each takes a few seconds:

1. **The Status page** — [grapevine.neta65.org/status/](https://grapevine.neta65.org/status/). Green
   "Working" next to each source means all is well. It also shows when each morning's daily quote came in.
   The NETA 65 workshop calendar shows as *can't be read right now* (or **Paused**): its site blocks robots, so
   those events are added by hand — on purpose, nothing to do.
2. **The badge** at the top of the repository's [README](../README.md): green = the last update worked.
3. **The Actions tab** — [github.com/NETA65/aagrapevine/actions](https://github.com/NETA65/aagrapevine/actions).
   Each run has a ✓ (worked) or ✗ (failed). The ones that matter:
   - **Website update** — the update itself (four times a day, and after every change you save);
   - **Morning check (new day by 5:30 AM)** — puts the new day and the daily quote on the site in the morning;
   - **Code check** — tests a change to the code; a red ✗ here never takes the site down.
4. **The Issues tab** — [github.com/NETA65/aagrapevine/issues](https://github.com/NETA65/aagrapevine/issues).
   The robot opens an issue by itself when something needs a person, and closes it by itself when it is fixed.

## 2. Something is red — what do I do?

- **One red ✗ on its own:** usually nothing. Wait for the next run (a few hours). The live site is not affected.
- **An issue opened by the robot:** open it and follow its **What to do** part. The usual ones:
  - *"The website update keeps failing"* — two failed updates in a row. Open the linked run, click the job with the
    red ✗, and read the red step. If the last change someone made caused it, undo that change.
  - *"A content source has stopped updating"* — one source (Drive, Instagram, a podcast …) has not worked for a
    week. The issue says what to check for that source.
  - *"Broken links found by the weekly check"* — a link on the site no longer works; the issue lists them.
  - *"The daily quote missed the morning goal"* — only once the morning alarm is set up (section 4).
- **The daily quote is not there in the morning:** Actions → **Morning check (new day by 5:30 AM)** → **Run
  workflow** → **Run workflow**. It only does what is missing, and is safe to press any time.
- **Never needed:** deleting runs, editing files under `data/`, or changing settings you do not understand.
  When in doubt, ask (section 5) — the site keeps working meanwhile.

## 3. How do I add something?

| I want to add… | Where | Step-by-step guide |
|---|---|---|
| A flyer or an event | Drive `flyers` folder (file name starting with the date), or a file in `content/events/` | [Flyers and events](../how-to/flyers-and-events.md) · [content/events/README.md](../content/events/README.md) |
| A bulletin post | Drive `bulletin` folder, or a file in `content/bulletin/` | [Bulletin](../how-to/bulletin.md) |
| Photos, slides, a report | Drive folders | [Photos, slides and reports](../how-to/photos-slides-reports.md) |
| Something for the booth display | Drive `booth` folder | [The booth display](../how-to/booth.md) |
| A change to a setting (meeting time, a link) | `config/site.yml` | [Settings](../how-to/settings.md) |
| A better Spanish wording | `data/translations/overrides.yml` | [Translations](../how-to/translations.md) |

All the guides: [how-to/README.md](../how-to/README.md) ("I want to… → read this"). A Drive file shows on the site
after the next update (a few hours at most); a file saved in the repository starts an update within minutes.

## 4. The morning alarm (to set up later)

Until it is set up, GitHub's own schedule puts the new day and the daily quote on the site: it can run late, so
on some mornings the quote may arrive after 5:30 AM. The **cron-job.org alarm** makes the morning sure: a free
outside alarm clock presses "Run workflow" at 4:30 AM Central. Setting it up takes about 10 minutes and is done
once a year (the key expires): [OPERATIONS → Set up the cron-job.org alarm later](OPERATIONS.md#set-up-the-cron-joborg-alarm-later).
In short: a GitHub **fine-grained token** for this repository only, with **Actions: Read and write**; it goes in the
cron-job.org job's **Authorization** header (never in the repository); the job calls
`POST https://api.github.com/repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches` with the body
`{"ref":"main"}`. Then set `morning_alarm: true` in `config/site.yml`.

## 5. Who to ask

- **The committee's website contact:** [grapevine@neta65.org](mailto:grapevine@neta65.org) — the chair or the
  member who looks after the website (they own the GitHub account **NETA65** and the Google Drive folder).
- **A problem with neta65.org itself** (the Area's website, its calendar): the Area webmaster, through
  [neta65.org](https://neta65.org).
- **For the person who looks after the code:** [README](../README.md), [docs/OPERATIONS.md](OPERATIONS.md) and
  [Automation and troubleshooting](../how-to/automation-and-troubleshooting.md) have every detail.
