# How-to guides: from a file to the website

These guides explain every file the NETA 65 Grapevine / La Viña Committee can place, on Google Drive or in this
repository, and what the website makes of it: which page it lands on, how long it takes, and what to do when it
does not show. They are written for the committee member who looks after the website, and for whoever comes next.
Most tasks need no programming. Each guide also has a "Going further" part for anyone who wants to change the code.

New here? Read sections 1 to 3 of this page (ten minutes), then open the guide for the task in front of you
([section 4](#4-i-want-to--read-this)).

**Contents**

1. [What the website is](#1-what-the-website-is)
2. [The big picture: how a file becomes a page](#2-the-big-picture-how-a-file-becomes-a-page)
3. [How long a change takes](#3-how-long-a-change-takes)
4. [I want to… → read this](#4-i-want-to--read-this)
5. [The 14 guides](#5-the-14-guides)
6. [Who can do what](#6-who-can-do-what)
7. [AA principles that apply everywhere](#7-aa-principles-that-apply-everywhere)
8. [Words used in these guides](#8-words-used-in-these-guides)
9. [Other documents in this repository](#9-other-documents-in-this-repository)

---

## 1. What the website is

The website of the **Northeast Texas Area 65 (NETA 65) Grapevine & La Viña Committee**:
<https://neta65.github.io/aagrapevine/>, and in Spanish <https://neta65.github.io/aagrapevine/es/>.

- **Two languages, one site.** Every page exists twice: in English (`/events/`) and in Spanish (`/es/events/`).
  Buttons and headings are written in both languages by hand. Content arrives in one language, and free,
  open-source translation models add the other one. Nothing is sent to an outside translation service, and a
  person can always give their own words instead ([Translations](translations.md)).
- **It updates itself.** Every day it reads the official Grapevine and La Viña websites and stores, the podcasts,
  YouTube, Instagram and the intergroups' meeting lists ([Automatic sources](automatic-sources.md)), together with
  the committee's own files.
- **No upload page, no database, no visitor accounts.** The committee places files in two places, the **Drive
  panel folder** and **this repository**, and GitHub's robot turns them into pages.
- **Free to run.** GitHub Actions builds the site and GitHub Pages hosts it, with open-source tools: Python reads
  the sources, Eleventy builds the pages.

What the committee places, and where:

| Where | What goes there | Who can | Guides |
|---|---|---|---|
| **Google Drive**: the shared folder **A65_GV** → the panel folder **2027-2028_Panel77_GVLV** | flyers, bulletin posts, photos and albums, reports, minutes, slides, workshop material, sign-up forms, the booth display's photos, videos, sounds and notes | anyone with upload (Editor) access to the folder; no GitHub login needed | [The Drive panel folder](drive-panel-folder.md), [File types](file-types.md), and one guide per kind of file |
| **This repository** ([NETA65/aagrapevine](https://github.com/NETA65/aagrapevine) on GitHub) | the settings (`config/`), events and bulletin posts written by hand (`content/events/`, `content/bulletin/`), the booth's quizzes and facts (`content/booth/booth.csv`), translation fixes (`data/translations/`), the words on buttons and headings (`src/_i18n/`), the pages themselves (`src/`) | a GitHub login with write access | [Settings](settings.md), [Flyers and events](flyers-and-events.md), [Bulletin](bulletin.md), [Booth display](booth.md), [Presentations](presentations.md), [Translations](translations.md), [Pages and code](pages-and-code.md) |
| **Nowhere: it comes by itself** | magazine stories, official documents, podcast episodes, videos, Instagram posts, prices and the Books of the Month, the daily quotes, story themes and deadlines, meetings | nobody | [Automatic sources](automatic-sources.md) |

---

## 2. The big picture: how a file becomes a page

```text
  Google Drive panel folder            this repository                   the outside sources
  A65_GV › 2027-2028_Panel77_GVLV      config/ · content/ · src/ …       magazine sites and stores, podcasts,
  (flyers, bulletin, photos, booth …)  (settings, posts, events, words)  YouTube, Instagram, meeting lists
                │                                 │                                 │
                └─────────────────────────────────┼─────────────────────────────────┘
                                                  ▼
                      GitHub Actions: the "Update & Deploy" workflow
                      1. sync: scripts/sync/*.py ──────────────► data/raw/*.json
                      2. translate + assemble (English ⇄ Spanish) ► data/site/*.json
                      3. the robot commits data/ back to the repository
                      4. build: Eleventy (src/ + config/ + data/site/) ► the pages
                      5. publish on GitHub Pages
                                                  │
                                                  ▼
                 https://neta65.github.io/aagrapevine/  and  …/aagrapevine/es/
```

In words:

1. **You place a file**: in the Drive panel folder, or by saving a file in this repository on github.com.
2. **A run starts.** The workflow **Update & Deploy** runs on a timetable, by itself a moment after someone saves a
   settings, content or code file in the repository, and whenever someone presses **Run workflow**. Nothing
   watches the Drive: a Drive file waits for the next run.
3. **Sync.** Python scripts (`scripts/sync/`) read the Drive folder, the bulletin and event files of the
   repository and the outside sources, and save what they found in `data/raw/`.
4. **Translate and assemble.** New titles and texts get their other language, and everything is put together in
   `data/site/`, the files the pages are built from. The robot commits `data/` back to the repository (the
   commits named `chore(data): …`), so the history doubles as a backup.
5. **Build.** Eleventy turns the page templates (`src/`), the settings (`config/`) and the data (`data/site/`)
   into the website, every page in English and in Spanish. Some repository files are read only here: the booth's
   CSV, the web presentations, the other settings files in `config/` and the button words.
6. **Publish.** The new site goes to GitHub Pages. If one source failed, the site is still published, with the
   last good data for that source.

The whole chain, step by step: [Automation and troubleshooting](automation-and-troubleshooting.md).

---

## 3. How long a change takes

| You do this | What starts by itself | On the website after about |
|---|---|---|
| Save a settings, content or code file on github.com: `config/`, `content/` (events, bulletin posts, the booth CSV), `data/translations/overrides.yml` or `glossary.yml`, `src/` … | a **quick** Update & Deploy run, and a *Code check* that tests the change | **2 minutes**, plus up to about 10 minutes before every visitor sees it |
| Put, rename or delete a file in the Drive panel folder | **nothing**: nothing watches the Drive | the **next run that reads the Drive**. Normally that is the next morning: with the morning alarm, the morning refresh starts about 4:30 AM Central and the new day is on the site by 5:30 AM. Or a few minutes after you start a run yourself (below) |
| Nothing (a magazine, YouTube, Instagram or a store publishes something new) | the **full daily run** (GitHub usually starts it about 5 to 7 AM Central) | after the next full daily run (the podcasts and the daily quotes are read by every run) |
| Change something only the full run reads (`content/instagram.yml`, a new YouTube channel in `config/site.yml` …) | a quick run, which does not read it | after the next full daily run, or start a full run yourself |
| Edit a guide in `how-to/`, the `README.md` or `docs/` | nothing on the website | GitHub shows the new text at once; the website does not change |
| Any change the booth display shows | — | a booth that is playing online takes the new show within half an hour, at its next slide |

**Start a run yourself** (any login with write access): GitHub → **Actions** → **Update & Deploy** → **Run
workflow** → tick **skip_crawl** → green **Run workflow**. About 2 minutes later the site is published with the
newest Drive files, bulletin posts, events, podcasts and daily quotes. Leave every box empty for a full run of
every source (usually 10 to 15 minutes). Then open the website's **Status page**,
<https://neta65.github.io/aagrapevine/status/>: *Site last published* says when.

> **The timetables are set 4 hours early on purpose.** GitHub starts this repository's timed runs 4 to 6 hours
> late (sometimes 8), so every schedule in `.github/workflows/` asks for a time about 4 hours before the one it
> means. Do not "correct" them: the tests check them
> ([Automation and troubleshooting §4.1](automation-and-troubleshooting.md#41-the-timetable-is-set-4-hours-early-on-purpose)).

---

## 4. I want to… → read this

### Put files on the website from Google Drive

| I want to… | Read |
|---|---|
| put any file on the website | [Drive panel folder §2.1](drive-panel-folder.md#21-put-a-file-on-the-website) |
| know what a file I have (PDF, Word, iPhone photo, video, sound, Google Form …) becomes, and where it goes | [File types §2](file-types.md#2-quick-start-i-have-this-file--where-does-it-go) |
| name a file so its title and date come out right | [Drive panel folder §3.8](drive-panel-folder.md#38-dates-in-file-names) and [§3.9](drive-panel-folder.md#39-titles-from-file-name-to-title) |
| keep a file in the folder but off the website | [Drive panel folder §3.10](drive-panel-folder.md#310-what-is-never-published) |
| take a file off the website, or replace it with a better version | [Drive panel folder §2.2](drive-panel-folder.md#22-take-a-file-off-the-website) and [§3.13](drive-panel-folder.md#313-replace-rename-move-delete) |
| add photos (one album per event) | [Photos, slides, reports §4.7](photos-slides-reports.md#47-photos--photo-albums) |
| add slides, a report, minutes or notes, workshop material, or a sign-up form | [Photos, slides, reports §2](photos-slides-reports.md#add-a-document-report-minutes-slides-workshop-handout-sign-up-form) and [§3](photos-slides-reports.md#3-the-folders-at-a-glance) |
| start the next panel's folder (Panel 79) | [Drive panel folder §2.3](drive-panel-folder.md#23-start-the-next-panels-folder) |
| check that the website can read the Drive (sharing) | [Drive panel folder §2.4](drive-panel-folder.md#24-check-that-the-website-can-read-the-drive) |
| find out why a Drive file does not show | [Drive panel folder §7.2](drive-panel-folder.md#72-a-file-does-not-show-check-in-this-order) |
| get exact dates for Drive files (the optional Google API key) | [Drive panel folder §3.15](drive-panel-folder.md#315-the-optional-google_api_key) |

### Events

| I want to… | Read |
|---|---|
| name a flyer so it becomes an event (date, time, place) | [Flyers and events §2](flyers-and-events.md#2-quick-start-a-new-event-from-a-flyer) and [§4](flyers-and-events.md#4-name-a-flyer-so-it-becomes-an-event) |
| choose the right way to add an event | [Flyers and events §3](flyers-and-events.md#3-pick-the-right-way-to-add-an-event) |
| add details to an event: a description, my own Spanish title, a Zoom link, several days, "details to be confirmed" | [Flyers and events §6](flyers-and-events.md#6-write-an-event-by-hand-contentevents), with its flyer attached as in [§5.1](flyers-and-events.md#51-attach-a-flyer-to-a-hand-written-event-flyer) |
| add something held every month (a booth, a workshop), or skip or move one month | [Flyers and events §7](flyers-and-events.md#7-monthly-events-recurring_events) |
| show the events of another public calendar | [Flyers and events §8.2](flyers-and-events.md#82-extra-calendar-feeds-ics_feeds) |
| fix an event that shows twice | [Flyers and events §9](flyers-and-events.md#9-when-the-same-event-comes-from-two-places) |
| fix an event's translated title | [Flyers and events §12](flyers-and-events.md#12-fix-a-translated-event-title) |
| change the committee meeting's day, time or Zoom details, or skip one meeting | [Settings §3.2](settings.md#32-meeting--the-committee-meeting) |

### The bulletin

| I want to… | Read |
|---|---|
| post on the bulletin from Google Drive (a Google Doc, `.txt`, `.md` or `.docx`) | [Bulletin §2](bulletin.md#from-google-drive-most-posts) |
| post from GitHub, with more options (dates, my own translation, pictures) | [Bulletin §2](bulletin.md#from-github-when-you-want-more-options) and [§3.8](bulletin.md#38-github-the-header--every-option) |
| pin a post, publish it on a later day, or take it down after a date | [Bulletin §3.13](bulletin.md#313-pin-schedule-and-expire--the-exact-rules-both-kinds) |
| write a post's other language myself | [Bulletin §3.14](bulletin.md#314-languages-automatic-and-by-hand) |

### The booth display

| I want to… | Read |
|---|---|
| set up the booth for an event: the night before, and at the table | [Booth display §2](booth.md#2-quick-start-at-an-event) |
| change it at a moment's notice: language, preset, PIN, one start link for every device | [Booth display §3](booth.md#3-change-it-at-a-moments-notice) |
| keep a laptop, iPad or Android tablet in the show (kiosk) | [Booth display §2.3](booth.md#23-lock-the-device-to-the-show) |
| add booth photos, videos, sound files or short notes | [Booth display §7](booth.md#7-photos-videos-sound-and-notes-from-drive), with the naming convention in [§7.3](booth.md#73-the-naming-convention) |
| edit the booth's quizzes, facts, quotes, polls and video links | [Booth display §8](booth.md#8-editing-the-csv) (short version: [content/booth/README.md](../content/booth/README.md)) |
| use it with no internet at the event | [Booth display §9](booth.md#9-offline-and-updates) |
| change every device's starting settings | [Booth display §4.11](booth.md#411-the-sites-starting-settings-configsiteyml) |
| find out why something does not show on the booth | [Booth display §10](booth.md#10-troubleshooting) |

### Presentations, settings and words

| I want to… | Read |
|---|---|
| change the words on a slide of the four web presentations | [Presentations §2](presentations.md#2-quick-start-change-the-words-on-a-slide) |
| present or print a web presentation | [Presentations §3.17](presentations.md#317-presenting-the-player-keys-and-presenter-view) and [§3.18](presentations.md#318-printing) |
| change a setting: names, contact address, Zoom link, official links … | [Settings §2](settings.md#2-quick-start-change-a-setting-on-github) |
| undo a settings change | [Settings: undo a change](settings.md#undo-a-change) |
| announce new prices | [Settings §3.4](settings.md#34-price_changes--prices-aa-grapevine-has-announced) |
| change the GVR / RLV 101 sessions, the About page's timeline, "Put this issue to work" or the Tracker's lists | [Settings §3.18](settings.md#318-configorientationyml--gvr--rlv-101), [§3.17](settings.md#317-confighistoryyml--the-timeline-on-the-about-page), [§3.15](settings.md#315-configcarryyml--put-this-issue-to-work), [§3.16](settings.md#316-configexpensesyml--the-trackers-starting-lists) |
| fix a translation | [Translations §2.1](translations.md#21-fix-one-wrong-translation-the-80-case) |
| make one word always come out the same, or keep a name untranslated | [Translations §3.5](translations.md#35-fix-a-word-everywhere-datatranslationsglossaryyml) |
| change a button's (or a heading's) words | [Translations §2.2](translations.md#22-change-a-button-or-a-heading) |

### E-mail and alerts

| I want to… | Read |
|---|---|
| send the monthly e-mail (the digest) | [E-mail and alerts §2](email-and-alerts.md#2-quick-start-switch-on-the-monthly-e-mail) |
| find "the Gmail API code" | there is none. The digest is sent over plain **SMTP** with an app password, by [`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py); [E-mail and alerts](email-and-alerts.md) explains it, and its [§6.6](email-and-alerts.md#66-if-you-want-the-gmail-api-oauth-instead) says what the Gmail API would need |
| see the e-mail before it goes out | [E-mail and alerts §3.10](email-and-alerts.md#310-preview-it-no-secrets-needed) |
| change who receives it, or stop it | [E-mail and alerts §3.6](email-and-alerts.md#36-who-receives-it) and [§3.15](email-and-alerts.md#315-change-the-password-or-the-recipients-or-stop-the-e-mail) |
| get an e-mail when a run fails | [E-mail and alerts §3.16](email-and-alerts.md#316-githubs-run-failed-e-mails) |
| have today's quote on the site by 5:30 AM (the morning alarm) | [E-mail and alerts §3.18](email-and-alerts.md#318-the-morning-alarm-cron-joborg) |

### Automatic content

| I want to… | Read |
|---|---|
| see everything the site reads by itself, and the setting behind each source | [Automatic sources §3.0](automatic-sources.md#30-all-sources-at-a-glance) |
| add an Instagram post the robot missed | [Automatic sources §3.6](automatic-sources.md#36-instagram-posts-and-posts-you-add-by-hand) |
| add a podcast or a YouTube channel | [Automatic sources §3.4](automatic-sources.md#34-podcasts) and [§3.5](automatic-sources.md#35-youtube-videos) |
| hide one story, document, video, episode or post everywhere | [Automatic sources §6.2](automatic-sources.md#62-hide-one-item-everywhere) (a small code change: there is no setting for it) |
| add a whole new source | [Automatic sources §6.6](automatic-sources.md#66-add-a-whole-new-source) |

### Pages and code

| I want to… | Read |
|---|---|
| change something I see on a page | [Pages and code §2](pages-and-code.md#2-quick-start-change-something-you-see-on-a-page) |
| find the file behind a page | [Pages and code §5](pages-and-code.md#5-every-page-address-template-data-script-style) |
| change a colour | [Pages and code §12.2](pages-and-code.md#122-change-a-colour) |
| add, move or rename a menu item | [Pages and code §12.3](pages-and-code.md#123-add-move-or-rename-a-menu-item) |
| add a new page | [Pages and code §12.4](pages-and-code.md#124-add-a-new-page-end-to-end) |
| run the site on my own computer | [Pages and code §3](pages-and-code.md#3-run-the-site-on-your-own-computer) |

### Runs, checks and problems

| I want to… | Read |
|---|---|
| make the website update right now | [Automation and troubleshooting §2](automation-and-troubleshooting.md#make-the-website-update-right-now) |
| check that everything is healthy | [Automation and troubleshooting §2](automation-and-troubleshooting.md#check-that-everything-is-healthy-2-minutes) |
| understand a failed run (a red ✗ or a yellow ⚠) | [Automation and troubleshooting §6](automation-and-troubleshooting.md#6-read-a-run) and [§14](automation-and-troubleshooting.md#14-troubleshooting) |
| fix a typo that stopped a settings file | [Automation and troubleshooting §14.3](automation-and-troubleshooting.md#143-a-yaml-typo) |
| undo a change, or roll the website back | [Automation and troubleshooting §14.9](automation-and-troubleshooting.md#149-undo-a-change-or-roll-the-website-back) |
| answer the issue "A content source has stopped updating" | [Automation and troubleshooting §8.1](automation-and-troubleshooting.md#81-a-content-source-has-stopped-updating) |
| run the sync, the build and the tests on a PC | [Automation and troubleshooting §11](automation-and-troubleshooting.md#11-run-the-sync-the-build-and-the-tests-on-a-pc) |
| move a schedule (and keep it 4 hours early) | [Automation and troubleshooting §13.1](automation-and-troubleshooting.md#131-move-a-schedule-and-keep-the-4-hour-early-rule) |

---

## 5. The 14 guides

Most guides follow the same order: what this is → quick start → full reference with examples → what happens next
(which run, how long) → where it shows on the website → going further: change the code → troubleshooting → good
practice and AA principles → see also.

| Guide | In one line |
|---|---|
| [README.md](README.md) (this page) | the big picture, how long a change takes, "I want to…", who can do what, the AA principles |
| [drive-panel-folder.md](drive-panel-folder.md) | the Drive folder as a whole: every folder name in English and Spanish, sharing, dates and titles in file names, what is never published, a new panel's folder, replacing and deleting |
| [file-types.md](file-types.md) | starts from the file in your hand (PDF, Word, iPhone photo, video, sound, Google Form …) and shows what it becomes in every folder |
| [flyers-and-events.md](flyers-and-events.md) | how a flyer's name, a file in `content/events/` or a monthly series becomes an event, with every option; outside calendars; duplicates |
| [bulletin.md](bulletin.md) | posts on the bulletin from Drive or GitHub: names, pinning, dates, pictures, languages, and every place a post shows |
| [photos-slides-reports.md](photos-slides-reports.md) | photo albums, reports, minutes, slides, workshop material and sign-up forms: naming, and where they show (Portfolio, Photos, What's New …) |
| [booth.md](booth.md) | the booth display on the About page: running it at an event, every setting, the Drive booth folder's naming convention, the CSV of quizzes and facts, offline use |
| [presentations.md](presentations.md) | the four web presentations on the GVR / RLV 101 page (`config/presentations/`): editing slides, facts that stay current, versions, printing |
| [settings.md](settings.md) | `config/site.yml` section by section, and the other settings files, with examples and where each setting shows |
| [translations.md](translations.md) | English and Spanish: fix a machine translation, one word everywhere, the words on buttons and headings, your own Spanish for a post or an event |
| [email-and-alerts.md](email-and-alerts.md) | the monthly digest e-mail (SMTP, its secrets, previews, recipients), GitHub's "run failed" e-mails, the two automatic issues, the morning alarm |
| [automatic-sources.md](automatic-sources.md) | what the site reads by itself (magazines, documents, podcasts, YouTube, Instagram, the shop, quotes, themes, meetings), its settings, and how to add or hide |
| [pages-and-code.md](pages-and-code.md) | a map of every page (address → template → data → script → style) and recipes: change a text, a colour, a menu; add a page |
| [automation-and-troubleshooting.md](automation-and-troubleshooting.md) | the GitHub Actions workflows and their timetable, running one by hand, reading a run, the Status page, working on a PC, recovering from problems |

---

## 6. Who can do what

The repository belongs to the **NETA65** GitHub account (the owner, with admin rights). **MKP715**, the GitHub login
on the owner's PC, is a collaborator with **write** access. The Drive folder has its own access, given in Google
Drive.

| To… | You need |
|---|---|
| put files in the Drive panel folder (flyers, posts, photos, booth files …) | upload (Editor) access to the Drive folder: ask grapevine@neta65.org. No GitHub login |
| run the booth display at a table, change its settings, set its PIN | nothing but the device: those changes stay on that device |
| edit any file in the repository (settings, events, posts, the booth CSV, translations, button words, pages) | write access: the **MKP715** login is enough |
| start, re-run or cancel a workflow; preview the monthly e-mail; download a run's files | write access (MKP715 or NETA65) |
| see, add, change or delete a **secret**: the e-mail's `SMTP_*` and `DIGEST_*`, `GOOGLE_API_KEY`, the Instagram token, the meeting-list keys | **NETA65 only** (Settings → Secrets and variables → Actions) |
| change the repository's settings: GitHub Pages, a custom domain, Actions, environments, branch rules, collaborators | **NETA65 only** |
| make the morning alarm's key | **NETA65 only** (a key only reaches its owner's repositories) |
| receive GitHub's "run failed" e-mails for the timed runs | they go to whoever last switched each workflow on or changed its timetable: do **Disable → Enable** as NETA65 to send them there ([E-mail and alerts §3.16](email-and-alerts.md#316-githubs-run-failed-e-mails)) |

The website needs **no** secret to run; each one only switches on an extra, such as the monthly e-mail. Nobody can
read a secret back after saving it: it can only be replaced or deleted. The full table:
[Automation and troubleshooting §10](automation-and-troubleshooting.md#10-who-can-do-what-mkp715-and-neta65).

---

## 7. AA principles that apply everywhere

Each guide ends with the principles for its own files. These apply to all of them.

- **Everything in the Drive folder is public.** A65_GV is shared "Anyone with the link", and the website's **Open
  Drive folder** buttons open the panel folder for every visitor. "Never published" (a name with `PRIVATE`, a
  spreadsheet …) only keeps a file off the website: anyone with the link can still open it. File names are public
  too: they become titles, and they are stored in the public repository (`data/raw/drive.json`). Keep private
  drafts, phone lists, budgets with names, expense records and form answers out of A65_GV altogether.
- **This repository is public too.** Every file, commit message, run log and issue can be read by anyone. Never put
  a password, a key, a phone number or a personal e-mail address in a file. Use the committee's address,
  grapevine@neta65.org, or an official @aagrapevine.org address. Secrets go only in GitHub's Secrets page.
- **Anonymity.** Personal anonymity at the level of press, radio and films (Tradition Eleven) includes a public
  website. No picture in which an AA member can be recognized: tables, literature, displays, rooms and signs
  instead, and watch for name tags and sign-in sheets in the background. No full names anywhere: a first name and
  last initial at most, or the service position ("the District 3 GVR"). A recording only with the speaker's
  permission and with no full names in it; the booth display takes none of a member speaking
  ([Booth display §7.10](booth.md#710-aa-rules-for-the-folder)). A phone picture can carry the place where it was
  taken: remove the location before uploading when it matters.
- **Attraction rather than promotion.** Plain, factual titles, captions, posts and slides: what, when, where. No
  sales talk and no urgency ("hurry", "last chance"); prices only as information. Grapevine takes no
  contributions, so no "donate" either. The site has no ads, trackers or analytics.
- **Copyright: respect AA Grapevine, Inc. and A.A. World Services, Inc.** The site shows titles, the publishers' own
  public teasers and links back, never a story's text. No Grapevine or La Viña logos, magazine covers, artwork or
  cartoons, and none of their audio or video files, in the Drive folder: link to the official video or episode
  instead. A.A. World Services texts are quoted word for word with their credit line, and Grapevine and La Viña
  material is paraphrased rather than quoted ([Booth display §8.11](booth.md#811-aa-rules-for-the-content) has the
  details and the exceptions). Share only material the committee made, or has permission to use.
- **Official sources only.** Facts from aa.org, aagrapevine.org, aalavina.org and AA literature; documents only
  from the official websites; only the official accounts and channels.
- **Both languages.** Every new word on a page gets its English and its Spanish. A machine translation is marked
  "Auto-translated" ("Traducción automática") until someone gives the words by hand.
- **The site's own words.** Visitors read "document" ("documento"), never "PDF", and the pages do not describe how
  the sources are read. These guides, the code and the file names keep the technical words.

---

## 8. Words used in these guides

| Word | What it means here |
|---|---|
| **A65_GV** | the committee's shared Google Drive folder, shared "Anyone with the link: Viewer" |
| **panel folder** | one panel's folder inside A65_GV, today `2027-2028_Panel77_GVLV`. The site reads every panel folder from `min_panel` (77) up |
| **repository** | the project on GitHub, NETA65/aagrapevine: every file of the website, its settings and content, and their history |
| **commit** | one saved change in the repository (on github.com: **Commit changes**) |
| **`main`** | the repository's main branch: what is on `main` is what gets published |
| **workflow, run** | a GitHub Actions program, and one time it ran (the **Actions** tab). **Update & Deploy** is the one that builds the site |
| **quick run, full run, morning refresh** | the three modes of Update & Deploy: Drive, posts, events, podcasts and the daily quotes (about 2 minutes); every source (10 to 15 minutes); the early-morning run the Morning check starts |
| **the robot** | GitHub Actions' own account, `github-actions[bot]`, which commits the `data/` files |
| **run summary** | the report on a run's page: files to fix, sources with problems, what was published |
| **Code check** | the workflow that tests every change. A red ✗ means that change broke something; the live site keeps working |
| **Status page** | `/status/` on the website: when the site was last published and how each source is doing |
| **YAML** | the plain-text format of the settings files: `key: value`, indented with spaces |
| **secret** | a password or key kept in the repository's Settings, never in a file. Only NETA65 can see the Secrets page |

---

## 9. Other documents in this repository

- [README.md](../README.md): the overview for the committee, with a summary in Spanish: what updates
  automatically, uploading to Drive, settings, the first-run checklist, troubleshooting.
- [docs/SETUP-GITHUB.md](../docs/SETUP-GITHUB.md): the first-time GitHub setup, click by click, and moving the
  repository.
- [docs/OPERATIONS.md](../docs/OPERATIONS.md): the technical runbook: the workflows, the sync modules, running
  locally, adding a new source.
- [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md): the data files between the sync and the pages, field by field.
- Short guides next to the files they describe: [content/events/README.md](../content/events/README.md),
  [content/bulletin/README.md](../content/bulletin/README.md) (every option in one file:
  [content/bulletin/_example.md](../content/bulletin/_example.md)),
  [content/booth/README.md](../content/booth/README.md),
  [config/presentations/README.md](../config/presentations/README.md) and
  [data/geo/README.md](../data/geo/README.md).
