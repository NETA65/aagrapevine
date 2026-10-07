# Settings: `config/site.yml` and the other settings files

> Part of the [how-to guide](README.md). This page covers every settings file a person edits by hand:
> everything in the `config/` folder, plus `content/instagram.yml`. Uploading files to the committee's
> Drive is in [drive-panel-folder.md](drive-panel-folder.md); fixing a translation
> (`data/translations/overrides.yml`) or a button text (`src/_i18n/*.json`) is in
> [translations.md](translations.md).

## 1. What this is

The website updates itself every day, but some things only the committee can decide: when the committee
meets, the Zoom link, the contact address, the official links, an announced price change, which Drive
panel folders to show. Those decisions live in a few plain-text settings files in the repository. You edit
them on github.com, and saving a file rebuilds the site by itself.

| File | What it holds | Read by |
|---|---|---|
| [`config/site.yml`](../config/site.yml) | The main settings: names and addresses, the committee meeting, monthly events, price changes, the Drive folder, the booth display, the content sources, La Viña's weekly open meeting, joining by phone, Grapevine meetings near us, published writers, the Texas writers archive's safety check, official links, the library, the monthly digest | The daily sync (Python) **and** the website build (`booth:` only the build) |
| [`config/carry.yml`](../config/carry.yml) | "Put this issue to work": the 10 ways to use an issue and the tips for each month | Website build only |
| [`config/expenses.yml`](../config/expenses.yml) | The service expense Tracker's starting lists (categories, funders, mileage rates …) | Website build only |
| [`config/history.yml`](../config/history.yml) | The Grapevine & La Viña timeline on the About page | Website build only |
| [`config/orientation.yml`](../config/orientation.yml) | "GVR / RLV 101", the six orientation sessions | Website build only |
| [`config/presentations/*.yml`](../config/presentations/README.md) | The four web presentations | Website build only (see [presentations.md](presentations.md)) |
| [`content/instagram.yml`](../content/instagram.yml) | Instagram posts to add by hand (usually empty) | The daily sync (Instagram) only |

Most changes are live within **about 3 minutes**: the push run of your save does not run the tests again (they test
the code, and your settings are not code), and since October 2026 its build also makes the monthly posters' share
pictures, about a minute. The file's own header says "about 10–20 minutes", a safe upper bound that includes up to
10 minutes before every visitor sees the change. A few wait for the next full daily update (section 4).
Section 5 lists, page by page, which settings show where.

**Page addresses in this guide** are relative to the site address, https://neta65.github.io/aagrapevine/.
`/meetings/` means https://neta65.github.io/aagrapevine/meetings/, and its Spanish page is `/es/meetings/`.

---

## 2. Quick start: change a setting on GitHub

Example: there is no committee meeting in December 2026.

1. Sign in to GitHub and open
   [config/site.yml on GitHub](https://github.com/NETA65/aagrapevine/blob/main/config/site.yml).
   The MKP715 login is enough: settings files only need write access.
2. Click the **pencil** (✎ "Edit this file"). Find the section with your browser's Find (Ctrl+F),
   here `meeting:`.
3. Change the value after the colon. Keep the spaces at the start of the line exactly as they are:
   ```yaml
     skip_dates: ["2026-12-16"]
   ```
4. Click **Commit changes…**, write a short message (for example
   `settings: no committee meeting in December 2026`), keep **Commit directly to the main branch**, and
   click **Commit changes**.
5. Open the **Actions** tab. Two runs start: **Website update** (rebuilds and publishes the site) and **Code
   check (tests and test build)** (tests your file; about 10 minutes). When Website update shows a green check, the
   new site is published. A browser may show the old page for up to about 10 more minutes; reload it.
6. Check the result: open `/meetings/` and `/es/meetings/`. December 16 is gone from "Upcoming dates"
   ("Próximas fechas"), and
   also from the home page, `/events/`, the calendar feeds, the monthly toolkit and the presentations.

If the run shows a yellow **Settings problem** or a red ✗, see [section 7](#7-troubleshooting).

### YAML in six rules

All settings files are YAML: `key: value`, with indentation showing what belongs to what.

| Rule | Right | Wrong (and what happens) |
|---|---|---|
| 1. Indent with **spaces**, exactly like the lines around it. Never tabs. | `  start: "19:00"` (two spaces, like its neighbours) | One space too many or too few usually makes the file unreadable: the site is not updated |
| 2. Put **quotes** around text, always when it contains `: ` or ` #`, or starts with `{ [ * & ! \| > @ %` | `title: "Grapevine: La Viña"` | `title: Grapevine: La Viña` → "bad indentation of a mapping entry" — the build stops |
| 3. Quote **codes**: meeting IDs, passcodes, phone numbers, times, dates, `"YYYY-MM"` keys | `passcode: "012345"` | `passcode: 012345` → the sync reads 5349, the website reads 12345: both wrong |
| 4. A **list** is `["a", "b"]` on one line, or one `- item` per line under the key | `skip_dates: ["2026-12-16", "2027-12-15"]` | `skip_dates: 2026-12-16, 2027-12-15` (one text, not two dates) |
| 5. `#` starts a **comment**: the rest of the line is ignored (unless it is inside quotes) | `months_ahead: 6   # how many dates` | `title: Booth #2` → the title is just "Booth" |
| 6. Use `true` / `false` for switches | `enabled: false` | `enabled: no` → the sync reads "false", the website reads the word "no" |

### Undo a change

1. Open the file on GitHub and click **History** (the clock icon above the file).
2. Click the commit **before** yours, find the file in it and open it (**View file**).
3. Copy the old lines, edit the current file, paste them back, and commit.

(github.com has no one-click "revert" for a commit made in the web editor.)

### Who can change what

| Task | Who |
|---|---|
| Edit any settings file and commit it to `main` | Write access (the **MKP715** login is enough) |
| Start a workflow by hand (Actions → the workflow → **Run workflow**) | Write access |
| Add or change a **secret**: the e-mail digest (`SMTP_SERVER`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `DIGEST_TO`, optional `SMTP_PORT`, `DIGEST_FROM`, `DIGEST_REPLY_TO`), `GOOGLE_API_KEY`, `IG_ACCESS_TOKEN`, `IG_BUSINESS_ID`, `TSML_KEY_AADALLAS`, `TSML_KEY_FORTWORTHAA` | **NETA65** (admin) only: Settings → Secrets and variables → Actions |
| A custom domain, the Pages or Actions settings | **NETA65** (admin) only: Settings → Pages / Actions |

> The repository is **public**. Never put a password, a key or a member's personal details in a settings
> file. Secrets go only in GitHub's Secrets page.

---

## 3. Full reference

`config/site.yml` has 15 sections today, in this order: `site`, `meeting`, `recurring_events`,
`price_changes`, `drive`, `booth`, `sources`, `lavina_weekly_open`, `phone_access`, `meetings`, `spotlight`,
`writers_archive`, `links`, `library`, `digest`. Each one is below (`booth:`, the booth display, is 3.14;
`writers_archive:` is with `spotlight:` in 3.10), then the other files (3.15–3.20). Every example says what
happens and where it shows. Examples marked "checked" were run through the site's own code on the real file
(October 2, 2026).

### 3.1 `site:` — names, addresses, contact

| Key | Today | What it does and where it shows |
|---|---|---|
| `title` / `title_es` | `"Grapevine / La Viña"` | The site name in every browser tab: `Events · Grapevine / La Viña — NETA 65` on `/events/`, `Eventos · Grapevine / La Viña — NETA 65` on `/es/events/`; the home page tab `Grapevine / La Viña — NETA 65 Committee`; link previews; the share buttons on `/share/` and `/monthly/YYYY-MM/`; Tracker printouts. The monthly e-mail's subject and masthead always use `title` (subject: `Grapevine / La Viña — September 2026 digest · Resumen de septiembre de 2026`). |
| `committee` / `committee_es` | `"NETA 65 Grapevine & La Viña Committee"` / `"Comité de Grapevine y La Viña de NETA 65"` | The footer of every page (`© 2026 …`); the committee meeting's title: `<committee> Meeting` / `Reunión del <committee_es>` (on `/events/`, in the calendar feeds); the monthly poster; the orientation slides; the organizer search engines see; the monthly e-mail's footer and **From name**. Write the Spanish so it reads well after "Reunión del". |
| `area` / `area_es` | `"Northeast Texas Area 65"` / `"Área 65 del Noreste de Texas"` | `/about/`: the small heading above "Our committee" (#committee) and the text of the Area website link (#contact). |
| `url` | `"https://neta65.github.io/aagrapevine"` | The site's full address for feeds, QR codes, share links, calendar files, presentations and e-mail links. **On GitHub the build uses the address GitHub Pages reports instead**, so a renamed repository or a custom domain is picked up by itself. This value is used by a build on a computer, by the sync scripts, and by the e-mail when that lookup fails. A custom domain is set by NETA65 (admin): see README §12. |
| `repository` | `"https://github.com/NETA65/aagrapevine"` | `/status/`: the **Actions** button and the "how to add an event" link. On GitHub the repository the build runs in wins. |
| `timezone` | `"America/Chicago"` | **Keep it.** The sync scripts, the build (since October 2026: `TZ` in `eleventy.config.js`, used by the page templates and the shared time module `eleventy/central-time.js`), the pages' live scripts (`window.SITE.tz`: countdowns, "today" checks) and `/build.json` (what the Morning check reads) use it; a name that is not a time zone, or none, means America/Chicago everywhere. But a few browser scripts (the booth display, the presentations, the offline worker, the Published page) still assume Central time, and so do the workflows' schedules, the morning goal and the data commits' dates, so another value would make them disagree by hours. |
| `morning_goal` | `"05:30"` | The time (Central, 24-hour) by which the Morning check wants the new day and both daily quotes on the site. `/status/` compares each morning with it. `"5:30"` and `"5:30 AM"` work too; an unreadable value means 05:30. It does **not** move any schedule or the morning alarm ([automation-and-troubleshooting.md](automation-and-troubleshooting.md)). The workflow's name in the Actions list, *Morning check (new day by 5:30 AM)*, says this time too: after a change, also change that `name:` in `.github/workflows/morning.yml` (and in `tests/test_run_names.py`, which pins it). |
| `contact_email` | `"grapevine@neta65.org"` | The footer's mail button on every page; the About page contact buttons; the Accessibility feedback button; the "ask for access" buttons on `/bulletin/`, `/events/`, `/photos/`, `/portfolio/`, `/library/`; "Questions? Write to the committee" under the Grapevine meetings list on `/meetings/`; "Email the committee" on `/published/`; the `/share/` poster; the 404 page; the RSS feed; the GV/LV report; `{live:email}` in the presentations; the monthly e-mail's footer and Reply-To. Also used when `meeting: chair_email` is empty. |
| `area_website` | `"https://neta65.org"` | The footer button (it shows the host name, "neta65.org") and the About page link. Checked by the weekly link check. |
| `committee_page` | `"https://neta65.org/trusted-servants/grapevine-la-vina/"` | `/about/#committee`: the "Our page on neta65.org" link. Checked by the weekly link check. |

> **Removed in October 2026:** `default_lang` and `languages`. No code read them: the two languages are built into
> the site (`src/_data/languages.js` and the `/es/` addresses). A copy of the file that still has them works the
> same.

Examples:

```yaml
site:
  committee_es: "Comité de Grapevine y La Viña del Área 65"
```
→ After the push run, every Spanish page's footer reads `© 2026 Comité de Grapevine y La Viña del Área 65`,
and the meeting is titled `Reunión del Comité de Grapevine y La Viña del Área 65` on `/es/events/` and in
`/es/events.ics`.

```yaml
  contact_email: "new-address@example.org"
```
→ Every place in the table above uses the new address at the next build (the monthly e-mail at its next
send). The chair's buttons and links ("Email the chair" on `/meetings/`, the others listed under
`chair_email` in 3.2) do **not** change: they use `meeting: chair_email`, which today has its own value (the
same address). Change that line too, or empty it so it follows `contact_email`.

> **Not in this file:** the committee tagline used in link previews and the RSS feed (`site.tagline`), and
> the description search engines show (`site.description`), are texts in `src/_i18n/common.json`
> ([translations.md](translations.md)). The name of the installed app ("Grapevine / La Viña — NETA 65",
> short "GV/LV 65") is written in `src/pages/manifest.11ty.js` ([pages-and-code.md](pages-and-code.md)).

#### Featured videos: `listen:`, `watch:` and `about_videos:`

These three sit inside `site:`. Each takes a YouTube id: the last part of `youtube.com/watch?v=<id>` or
`youtube.com/shorts/<id>`.

```yaml
  listen:
    sidebar_short: "0uyVPlTcSeI"            # from youtube.com/shorts/0uyVPlTcSeI
    sidebar_short_title: "Grapevine Get The App!"
```
→ `/listen/` and `/es/listen/`: the card beside the top banner (below it on phones) shows this Short in an
upright player, with its caption (default "AA Grapevine") and the two app buttons (`links.gv_apps` and
`links.lv_apps`; La Viña's first on the Spanish page).

```yaml
  watch:
    hero_video: "_mjB6hXYHn4"
    hero_video_title: "Victor E. is back"
```
→ `/watch/` and `/es/watch/`: the card beside the top banner (below it on phones) shows this video, with its
title and summary from the channel's list (a Short plays upright and links "All Shorts"). The card is **hidden while
this video is the newest one**, because the newest is already the first block of the page.
`hero_video_title` is used only while the video is not in the channel's list yet; meanwhile the card links
to YouTube. Once the video is listed, the card takes the list's title and links to the videos below.

> **Note:** the file says "Delete these lines to hide it". The page does hide the card, but the tests
> `Listen.test_config_has_the_short` and `Watch.test_config_has_the_video` in `tests/test_read_media_asides.py`
> expect both ids (exactly 11 characters). Deleting them, or a 10- or 12-character id, turns **Code check**
> red. **Website update** still publishes the change: these tests judge your settings, not the code, so it leaves
> them to the Code check (`CONTENT_TESTS` in `scripts/ops/gate_tests.py`, since October 2026). Change the test in a
> later commit if you really want the card gone, so the Code check is green again.

```yaml
  about_videos:
    - id: "V3RzyHdgQCY"
      pub: gv
      title: "AA’s Twelfth Step Tools: Grapevine and La Viña"
      tr:
        title: "Herramientas de AA para el Paso Doce: Grapevine y La Viña"
        summary: "Una mirada a lo que son Grapevine y La Viña …"
```
→ `/about/#videos`: one card per entry, the page language's magazine first. Per entry:

| Key | Meaning |
|---|---|
| `id` | The YouTube id (6–20 letters, digits, `-` or `_`; anything else: the entry is skipped). |
| `pub` | `gv` or `lv`. Left out: the magazine the channel's list gives. |
| `title` | Replaces the channel's title (for example one written in capitals). **Needed** while the video is not in the channel's list yet, or the entry is skipped. |
| `tr.title`, `tr.summary` | Our own translation, shown under the original on the other language's page. Without `tr`, the machine translation is shown and marked as such. |

The summary and the length come from the channel; the channel's sign-off ("Thank you for watching… https://…")
is cut. To add a third video, copy an entry (from `- id:` down), change `id` and `pub`, give `title` if
the channel has not listed the video yet, and rewrite the copied `tr` lines for the new video (or delete
them: the marked machine translation is then shown). Delete an entry to hide it.

### 3.2 `meeting:` — the committee meeting

The next date, the countdown and every list of dates are worked out from this block when the site is
built, so they stay right even on a day the daily sync fails.

| Key | Today | Accepted values, and what happens if it is wrong |
|---|---|---|
| `week_of_month` | `3` | `1`–`5`, or `-1` for the last one (`"3"` in quotes works). `5` = only months that have a fifth one. **Words such as `"third"` or `"2nd"` are not read here**: the meeting silently stays on the 3rd. |
| `weekday` | `"wednesday"` | An English or Spanish day name, any capitals, with or without the accent: `Wednesday`, `miércoles`, `miercoles`, `jueves`, `sábado`. **Plurals (`"Wednesdays"`) and short forms (`"Wed"`) are not read here**: silently Wednesday. |
| `start` | `"19:00"` | Central time. `"19:00"`, `"7:00 PM"`, `"7pm"`, `"7 p.m."`, `19`, `"19h00"`, `"19.30"` all work. Unreadable (`"noon"`, `"25:00"`, `"13pm"`): 19:00. |
| `end` | `"20:00"` | Same forms. Missing or unreadable: one hour after the start. An end earlier on the clock than the start and at most 12 hours later, such as `"22:00"`–`"01:00"`, is the **next morning** everywhere since October 2026: the sync, every page ("10:00 PM – 1:00 AM CDT"), the calendar files, both countdowns (the home page's and the one on `/meetings/`) and the e-mail digest. An end further back (`"19:00"`–`"08:00"`), or the same as the start, still gives one hour. |
| `platform` | `"Zoom"` | What the pages call the place, since October 2026 in every sentence about the committee meeting: "Join on Zoom", "Monthly on Zoom", "on Zoom" in the calendar text, the meta description, how to join, the share kit's announcement, the presentations' closing slide, the home card, `/events/`, the `/share/` poster, `/gvr/`, the GV/LV report's committee-meeting lines. Left out (or empty): Zoom. The phone dial-in section and the two weekly open meetings always say Zoom: those are Zoom's own. |
| `zoom_url` | the full Zoom link | Every **Join** button (home, `/meetings/`, `/events/`), "Copy Zoom link", the calendar description. Copy the whole link from Zoom: its `pwd=` part is a token, not the passcode. |
| `meeting_id` | `"949 476 7497"` | `/meetings/` "How to join" (its Copy button copies the digits only), the poster, the calendar text, the tap-to-call links on `/accessibility/#phone`. A test requires 9–11 digits. |
| `passcode` | `"neta65"` | `/meetings/`, the poster, the calendar text. A passcode with letters means phone callers need a numbers-only one: see [3.8](#38-phone_access--joining-by-phone). |
| `chair_title` / `chair_title_es` | `"Grapevine / La Viña Chair"` / `"Coordinador(a) de Grapevine / La Viña"` | The heading of the chair card on `/meetings/`. |
| `chair_email` | `"grapevine@neta65.org"` | The "Email the chair" button and the address on the chair card of `/meetings/`; the chair's address on `/gvr/`; "Write to the chair" on `/digest/` and `/whats-new/` (to ask for the monthly e-mail); "Email the chair" (for the phone passcode) on `/accessibility/#phone`. Empty: `site.contact_email`. |
| `note` / `note_es` | "All AA members are welcome to attend. No registration required." / "Todos los miembros de AA pueden asistir. No hace falta registrarse." | Who may come, in a line (since October 2026): the first sentence of the *Who can come* card on `/meetings/` (`note_es` on `/es/meetings/`) and the end of the meeting's calendar descriptions (`/events.ics`, the Google and Outlook links, the home page's add-to-calendar). Write both: without `note_es` the Spanish pages show the English line (the entries in `data/site/events.json` get a machine translation). |
| `skip_dates` | `[]` | Meeting days that do not happen, `["YYYY-MM-DD", …]`. Only that month's real meeting day counts; any other date is ignored and reported. |

Examples (checked; "today" = October 2, 2026):

| You write | Result |
|---|---|
| Today's block: `3`, `"wednesday"`, `"19:00"`–`"20:00"` | Next dates Oct 21, Nov 18, Dec 16, 2026, then Jan 20, 2027. Rule line "Every third Wednesday of the month" / "Cada tercer miércoles del mes"; time "7:00 – 8:00 PM" / "7:00–8:00 p. m." |
| `skip_dates: ["2026-12-16"]` | December's meeting disappears from the home page, `/meetings/`, `/events/`, the calendar feeds, the toolkit and the presentations. |
| `skip_dates: "2026-12-16"` | The same: one date without brackets works. |
| `skip_dates: ["2026-12-17"]` | Nothing is skipped. Run summary: *config/site.yml meeting: skip date “2026-12-17” is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16)* |
| `weekday: "jueves"`, `week_of_month: 2`, `start: "18:00"`, no `end` | Every 2nd Thursday, 6:00–7:00 PM: Oct 8, Nov 12, Dec 10. |
| `week_of_month: -1`, `weekday: "monday"` | The last Monday: Oct 26, Nov 30, Dec 28. |
| `start: "7pm"`, `end: "6pm"` | 7:00–8:00 PM (the end is not after the start, and 23 hours later is no overnight end: one hour). |
| `weekday: "Thursdays"`, `week_of_month: "second"` | **Still the 3rd Wednesday**, with no Settings problem: neither value can be read here. |

Where the meeting shows:
- **Home** `/` and `/es/`: the "next committee meeting" card with the countdown, date, time, platform, rule
  line, **Join** button and add-to-calendar.
- **`/meetings/#committee-meeting`**: the countdown with Join; "How to join" (Meeting ID and Passcode with
  copy buttons, "Copy Zoom link", "Join by phone"); "Upcoming dates"; the chair card.
- **`/events/`** and the calendar feeds **`/events.ics`**, **`/es/events.ics`**: one card or calendar entry
  per month, up to a year ahead.
- **`/share/`** (the poster), **`/accessibility/#phone`**, **`/gvr/`**, **`/orientation/`** (the
  `{rule_lc}` and `{time}` placeholders, [3.18](#318-configorientationyml--gvr--rlv-101)), **`/about/`**,
  **`/monthly/`** (toolkit, posters, messages), **`/digest/`** and the monthly e-mail, the GV/LV report, and
  the presentations (`{live:meeting_next}`, `meeting_rule`, `meeting_time`, `meeting_zoom_id`,
  `meeting_passcode`, `meeting_phone`). (The search lists the Meetings page, not each meeting.)

> **Note — the rest of the words are the site's own.** After `note`, the *Who can come* card goes on with
> `committee.meeting.who_text` in `src/_i18n/committee.json`, and the calendar text starts with
> `committee.meeting.cal_desc` ("… committee meeting on {platform}."). To change those words, see
> [translations.md](translations.md).

> **The passcode is public.** `meeting_id` and `passcode` are printed on `/meetings/`, in the calendar files, on the
> `/share/` poster and in the presentations, for anyone to read, and so are the weekly open meetings' passcodes. That
> is normal for an open AA meeting, which anyone may attend. It means the host should keep Zoom's own protection on:
> the **waiting room**, or the host controls (admit people, remove a participant, lock the meeting once it has
> started). Changing the passcode is not a protection: the site publishes the new one at its next build.

> **Before you change the day or the time:** three of the four presentations (`committee-meeting.yml`,
> `orientation-workshop.yml`, `information-workshop.yml`) also say "Every 3rd Wednesday", "second Saturday
> … 5 to 8 p.m." (the CityWide booth) and "4th Thursday" (La Viña's workshop) in their own words, about 30
> lines in `config/presentations/`. Search those files for the old words ("3rd Wednesday", "third
> Wednesday", "second Saturday", "4th Thursday", "fourth Thursday") and edit them too
> ([presentations.md](presentations.md)).

### 3.3 `recurring_events:` — things held every month

Two entries today: `citywide-dallas` (our GV/LV booth at CityWide Dallas, every 2nd Saturday, 5–8 PM) and
`lv-monthly-workshop` (La Viña's own monthly workshop on Zoom, every 4th Thursday, 2–3 PM Central,
`host: "lv"`). The full guide — every key, a series' flyer, how La Viña's own calendar listings merge, every
problem message, and how to add a new detail to these events — is in
[flyers-and-events.md](flyers-and-events.md). The short version:

```yaml
recurring_events:
  - key: "citywide-dallas"          # keep it once published: calendars recognize the event by it
    title: "GV/LV booth at CityWide Dallas"
    title_es: "Mesa de GV/LV en CityWide Dallas"
    week_of_month: 2
    weekday: "saturday"
    start: "17:00"                  # Central time
    end: "20:00"
    location: "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220"
    url: "https://citywidedallasaa.org"
    months_ahead: 6
    skip_dates: []
```
→ (checked) Oct 10, Nov 14, Dec 12, 2026, then Jan 9, Feb 13, Mar 13, 2027, 5:00–8:00 PM Central. Each date
gets a card with an "Every month" badge on `/events/` and `/es/events/`, an entry in `/events.ics` and
`/es/events.ics`, a place in the `/monthly/` toolkit and its posters, the search, and — once it has taken
place — the monthly digest. The next date also keeps a place in the home page's "Upcoming events" row (each
series of ours does). A monthly event is never "New" and never in What's New or the RSS feed.

| Key | In short |
|---|---|
| `key` | Short name: letters, numbers, dashes (cut to 32 characters). Missing: made from the title. The same key twice: the second entry is skipped. |
| `title` / `title_es` | At least one. The missing language is machine-translated and marked "auto-translated". |
| `summary` / `summary_es` | Optional. The card shows three lines: keep it to about 100 characters. |
| `week_of_month` | `1`–`5` or `-1`; here words work too: `"2nd"`, `"second"`, `"segundo"`, `"last"`, `"último"`. |
| `weekday` | English or Spanish; plurals work (`"Saturdays"`, `"sábados"`); short forms (`"Sat"`) do not. |
| `start` / `end` | Central time, the same forms as the meeting. An end that is missing or not after the start: one hour — except, as for the meeting, an end at most 12 hours later on the next morning (`"22:00"`–`"01:00"`), which every page, calendar file and the e-mail show as the next morning (since October 2026). |
| `location` | The address. No `location` but an `online_url`: an online-only event ("Online on Zoom", no map). |
| `url` | The "Event details" link. Must start with `https://` or `http://` (a `www.` address gets `https://` added), otherwise it is left out. |
| `online_url`, `meeting_id` | The "Join online" link and the Zoom ID shown on the card and in the calendars. |
| `contact` | One e-mail address: its own line on the card and in the calendars. |
| `host` | `neta` (us, the default), `lv` (La Viña) or `gv` (Grapevine). |
| `flyer_match` | A pattern that finds the series' flyer on the committee's Drive. |
| `months_ahead` | How many dates `/events/` and the calendar feeds list: 1–24, default 6. |
| `skip_dates` | Months without it: that month's own rule day, `["2026-12-12"]`. |

Unlike `meeting:`, a mistake in one of these keys is always reported. A real mistake skips that one event;
a small slip is corrected. Either way the rest of the site still updates, and the Actions run summary shows
a yellow **Settings problem**, for example (checked; the entry's number and key will be yours):
- `weekday: "Sat"` → *recurring_events entry 3 (tyler-booth): weekday “Sat” is not a day of the week — skipped*
- `skip_dates: "2026-12-13"` on the 2nd-Saturday booth → *… skip date “2026-12-13” is not the 2nd Saturday
  of its month — ignored (that month's is 2026-12-12)*
- `url: "tylerbooth.org/info"` → *… url “tylerbooth.org/info” is not a web address (https://…) — left out*

> **Note:** there is no `enabled:` switch. The sync ignores `enabled: false` (only the `/monthly/` pages stop
> working out its months beyond the listed dates), so its next dates would still show on `/events/`, in the
> calendars and in the toolkit. Delete the block to stop an event.

### 3.4 `price_changes:` — prices AA Grapevine has announced

Every price on the site is read from the official stores. A block here adds what the stores cannot say
yet: a notice from the day the change is announced, and the new 1-year prices from the day it takes effect.

| Key | Accepted values | If it is wrong |
|---|---|---|
| `key` | Short name (letters, numbers, dashes). Default: the effective month, `"2027-01"`. | Used twice: the second block is skipped. |
| `effective` | **Required.** `"YYYY-MM-DD"`: the new prices start at 00:00 Central that day. | Missing or not a date: skipped. |
| `announced` | The day the notice starts. Default: `effective` (no advance notice). | After `effective`: the notice starts on `effective` (noted). |
| `notice_until` | The last day of "New prices since …". Default: `effective` + 30 days. | Before `effective`: the default (noted). |
| `source` / `source_es` | Where it was announced, shown in the notice. | — |
| `doc_match` | A pattern that finds AA Grapevine's notice on the Drive → the "Read AA Grapevine's notice" link. Matched by the page itself: capitals ignored, accents **not** folded (write `[oó]`). | Not a valid pattern: no link (noted). |
| `yearly` | The new **1-year** prices in U.S. dollars: `gv` / `lv` → `print` / `digital` / `complete`. `39`, `"39.00"` and `"$39.00"` all work (more than 0, at most 1000). | A word or an absurd amount: that price is left out (noted). |
| `books_more` | How much more every Grapevine and La Viña book costs. | Not an amount: left out (noted). |

A block that changes nothing (no valid yearly price and no `books_more`) is skipped.

Today's block (checked: no problems):

```yaml
price_changes:
  - key: "2027-01"
    effective: "2027-01-01"
    announced: "2026-10-01"
    notice_until: "2027-01-31"
    source: "AA Grapevine's letter to Intergroups and Central Offices, October 1, 2026"
    source_es: "Carta de AA Grapevine a las oficinas intergrupales y centrales, 1 de octubre de 2026"
    doc_match: "pricing update.*2027|actualizaci[oó]n de precios.*2027"
    yearly:
      gv: { print: 39.00, digital: 34.00 }
      lv: { print: 19.50, digital: 17.00 }
    books_more: 2.00
```
→ From October 1, 2026: "Prices change on January 1, 2027" on `/shop/#price-changes` and `/es/shop/`, with
each 1-year plan's price today and its new one ("From Jan 1, 2027: $39.00"), the books line, AA Grapevine's
letter linked (`doc_match` finds the Drive file `notes/2026-10-01 Grapevine & La Viña Pricing Update -
Effective January 1, 2027.pdf`). On January 1 at midnight Central the new prices show by themselves, then
"New prices since …" until January 31. The 2- and 3-year, monthly and Complete plans keep the stores' prices.

To add the next announcement: copy the block (from `- key:` down), paste it under the last one, change the
values. Leave a block in place until the stores show the new prices; after that it may be deleted.

A block with slips (checked — the run summary's words; see [section 7](#7-troubleshooting) for how the
line starts):

```yaml
  - effective: "2028-07-01"
    yearly:
      gv: { print: "$41.00", digital: "thirty" }
      LV: { complete: 55 }
  - key: "early"
    effective: "2029-03-01"
    announced: "2029-04-01"
    notice_until: "2029-02-01"
    books_more: "two dollars"
    yearly:
      gv: { print: 45 }
    doc_match: "(bad"
```
→ Both still apply, with these notes:
- *price_changes entry 1 (2028-07): yearly gv digital: “thirty” is not a price like 39.00 — left out*
  (GV print $41.00 and LV Complete $55.00 apply)
- *price_changes entry 2 (early): announced 2029-04-01 is after effective 2029-03-01 — the notice starts on
  the effective day; notice_until 2029-02-01 is before effective 2029-03-01 — the notice ends 2029-03-31;
  books_more “two dollars” is not an amount like 2.00 — left out; doc_match “(bad” is not a valid pattern —
  no link to the notice*

And blocks that are skipped: a second `key: "2028-07"` → *… the key “2028-07” is used twice (each change
needs its own) — skipped*; `effective: "someday"` → *… effective “someday” is not a date like
"2027-01-01" — skipped*; `yearly: { xx: { print: 1 } }` with `books_more: 0` → *… it changes no price (no
valid yearly price and no books_more) — skipped*.

Where it shows (from `announced` to `notice_until`, in both languages): the `/shop/` notice and the plan
lines, the Book of the Month cards, the monthly toolkit (`/monthly/YYYY-MM/`), the GV/LV report, the
monthly e-mail, and the presentations (`{live:price_change_note}`, `{live:price_change_date}`, the price
facts, and slides marked `when: "price_notice"`). Put AA Grapevine's letter in the Panel's Drive `notes`
folder with the letter's date first in its name. Store prices themselves: [automatic-sources.md](automatic-sources.md).

> The test `test_the_settings_file_has_no_mistakes` in `tests/test_price_changes.py` requires the real
> file's blocks to have **no** problems (any number of blocks, or none, is fine).

### 3.5 `drive:` — the committee's Google Drive

| Key | Today | What it does |
|---|---|---|
| `root_folder_id` | A65_GV's folder id (the last part of the folder's Drive address) | The shared Drive folder **A65_GV**, which must be shared "Anyone with the link: Viewer". It is never linked on the site (it can hold private files); pages link the current panel folder. Empty: the Drive source fails ("drive.root_folder_id is not set in config/site.yml") and the previous items are kept. |
| `panel_folder_pattern` | `"Panel\\s*(\\d+)"` | Folders in A65_GV whose name matches are **panel folders** (capitals ignored); the number is the panel number. |
| `min_panel` | `77` | Older panels are skipped; this panel and newer ones are picked up by themselves, so a future `2029-2030_Panel79_GVLV` folder needs no edit. Also the "Panel 77" label shown when no panel folder was found. |
| `include_loose_folders` | `false` | `true` = also read category folders and files that sit directly in A65_GV, outside any panel folder. |
| `exclude_mime_contains` | `["spreadsheet"]` | File types never published. They are **added to** a built-in list that is always left out (spreadsheets, Excel, CSV/TSV, Apps Script, Google Sites): removing `"spreadsheet"` here does not publish spreadsheets. |
| `exclude_name_contains` | `["(Responses)", "(Respuestas)", "PRIVATE", "PRIVADO", "wrong size"]` | A file or folder whose name contains one of these (capitals ignored) is skipped; for a folder, everything inside it too. |

Examples:
- `2027-2028_Panel77_GVLV` → panel 77, label "Panel 77 (2027–2028)" (the years come from the name; without
  them, 1950 + N to 1951 + N). The "Open Drive folder" buttons and `{live:panel}` in the presentations use it.
- `Panel 76 archive` → skipped (76 is below 77). `panel79` → picked up. `Panelists` → not a panel (no
  number), so a loose folder, ignored while `include_loose_folders` is `false`.
- A Google Form's `Sign-up sheet (Responses)` spreadsheet → never published (both its type and its name).
- **Careful:** the name test is "contains": `PRIVATE` also hides `Privately printed flyer.pdf`.

Only the reason a file was left out is recorded, never its name (the data files are public). The optional
`GOOGLE_API_KEY` secret (added by NETA65, admin) gives exact dates and sizes. Folder names and file naming:
[drive-panel-folder.md](drive-panel-folder.md), [flyers-and-events.md](flyers-and-events.md),
[bulletin.md](bulletin.md), [photos-slides-reports.md](photos-slides-reports.md).

### 3.6 `sources:` — what the robot reads

Every page address under `grapevine:` and `lavina:` also has a default built into the code, so a deleted
line falls back to today's address. The lists (`youtube: channels`, `podcasts`, `instagram: accounts`,
`ics_feeds`) have no default: an entry you delete is no longer read. Most of these are read by the **full
daily run** only — but when you change one, the push run of your save also runs the source that reads it
(`SETTINGS` in [`scripts/ops/push_modules.py`](../scripts/ops/push_modules.py)), except the magazine stories, the
store and the document search. What each source fetches, and how to hide or pin an item:
[automatic-sources.md](automatic-sources.md).

| Part | Keys | What it feeds | An edit shows |
|---|---|---|---|
| `grapevine`, `lavina` | `base`, `magazine_hub`, `contribute`, `weekly_open` (GV), `botm`, `subscriptions`, `subscription_regions`, `specialty`, `specialty_skip`, `audio_project` (GV), `record_story` … (LV), `themes_page` / `themes_link` (LV), `quote_page` | Magazine stories (`/read/`, home, toolkit, digest); story deadlines and La Viña's themes (`/contribute/#deadlines`, `/monthly/`); the Grapevine Weekly Open (`/meetings/#weekly-open`); the Book of the Month and subscription prices (`/shop/`); specialty items (`/shop/#specialty`); the story phone lines (`/contribute/#record`); the daily quotes (home) | Links on the pages: after the push run. The data: `quote_page` in every run (the push run too); `contribute`, `themes_page`, `themes_link`, `rlv_resources` (the themes), `weekly_open` (the Weekly Open), `audio_project` and `record_*` (the story lines) in the push run that changed them (a changed `base` reruns the themes, the story lines and the event calendars — Grapevine's `base` also the Weekly Open); `magazine_hub`, `botm`, `subscriptions`, `subscription_regions`, `specialty` at the next full run — the Book of the Month and prices also in the morning refresh on the 1st and the 15th, the magazines' new issues on the 1st |
| `crawler` | `hosts`, `user_agent`, `minutes_per_run`, `recheck_days`, `pdf_details_per_run`, `pdf_max_mb` | The search for documents for `/library/` | The next full run |
| `youtube` | `channels`: `id`, `handle`, `name` | `/watch/`, home, the digest, the About videos | The push run (the channels' feeds; the complete listing of older videos: a full run, once a week) |
| `podcasts` | `key`, `feed`, `name`, `web`, `apple`, `spotify`, `amazon` | `/listen/` episodes and app buttons | The push run (looking for new feeds: full runs only) |
| `instagram` | `accounts`, `anonymous`, `keep_per_account`, `enrich_per_run`, `recheck_per_run`, `graph_version`, `rsshub_instances` | `/instagram/`, the home card, What's New, the digest | The push run (without the look-ups of each post's own page and the removal check, which wait for the next full run) |
| `ics_feeds` | `url`, `label` / `label_es`, `category`, `key` | Other websites' calendars on `/events/` | The push run, but each calendar is asked at most once in about 20 hours |

Worth knowing:
- `crawler.minutes_per_run: 0` pauses the document search; everything else keeps updating. A manual run can
  set its own minutes (up to 300). The run summary never calls the paused search "not checked", neither during
  the pause nor right after you set the minutes back (each full update during the pause counts as its try).
- **Note:** `crawler.hosts` does not change which sites the document search reads (that list is fixed in
  `scripts/sync/crawl_rules.py`); it is only used to look for new podcast feeds. Changing `user_agent` can
  break a rule at neta65.org that lets the robot's calendar requests through, if one is set up.
- `specialty_skip: [holiday]` hides one kind of specialty item (`cards`, `planner`, `calendar`, `holiday`).
  Deleting a product page's line only stops reading that page.
- `themes_page` / `themes_link`: if La Viña moves its yearly themes document, change these two lines. The
  test in `tests/test_editorial.py` expects the page to resolve to https://www.aalavina.org/recursos —
  update the test with it.
- `podcasts`: an entry without `key` or `feed` is ignored; `key: "wo"` is the Weekly Open (its own label).
  Feeds found on the magazine sites are only listed in the run summary ("New podcast feeds found"), never
  added by themselves.
- `instagram.keep_per_account` must stay at least 124 (a test: the digest needs about 62 days of posts).
  `anonymous: false` = only the official API (secrets `IG_ACCESS_TOKEN`, `IG_BUSINESS_ID`, added by NETA65)
  plus `content/instagram.yml`.
- `instagram.recheck_per_run` (5, since October 2026): how many posts that left the accounts' listing each full
  run looks up again; a post Instagram no longer shows (deleted, archived, private) leaves the site after two such
  look-ups at least 12 hours apart. `0` switches the check off. Details:
  [automatic-sources.md §3.6](automatic-sources.md#36-instagram-posts-and-posts-you-add-by-hand).
- `sources.grapevine.gvr_resources` is **not read** by any code (the pages use `links.gvr_resources`).

**Other calendars (`ics_feeds`).** Today there is one:

```yaml
  ics_feeds:
    - url: "https://neta65.org/events/category/workshop/list/?ical=1"
      label: "NETA 65 workshops"
      label_es: "Talleres de NETA 65"
      category: "neta65"
```
→ Its events would show on `/events/` with the NETA 65 events. Today neta65.org's bot protection turns the
robot away: the "Other calendars" box on `/status/` says so, and workshops must be added by hand in
`content/events/` ([flyers-and-events.md](flyers-and-events.md)).

| You write | Result (checked) |
|---|---|
| `- "webcal://example.org/cal.ics"` | Read as https://example.org/cal.ics, label "example.org", category `ics` (shown with the NETA 65 events). |
| `url: "example.org/x.ics"` | Skipped: *ics_feeds entry 2: “example.org/x.ics” is not a calendar address (https://…) — skipped* |
| `name: "La Viña calendar"`, `category: "LV-Calendar"` | Category `lv-calendar`: shown with the Grapevine / La Viña calendars. |
| `category: "workshops"` | *… category “workshops” is not one of gv-calendar, ics, lv-calendar, neta65 — “ics” used* |

An event that is already on `/events/` (a `content/events` file, a flyer, a monthly event, the meeting)
shows once: ours wins. A calendar's health is informational only (run summary "Other calendars (optional,
informational)" and the `/status/` box); it never opens the "stopped updating" issue.

### 3.7 `lavina_weekly_open:` — La Viña's weekly open meeting

Written from La Viña's official flyer (there is no web page to read yet). It becomes the second weekly open
meeting, after the Grapevine Weekly Open that is read from aagrapevine.org.

| Key | Today | Accepted values |
|---|---|---|
| `enabled` | `true` | `false` (or deleting the block) takes it off the site. |
| `title_es` / `title_en` | "Reunión Abierta de La Viña" / "La Viña Open Meeting (in Spanish)" | Your own words. Missing `title_en`: machine translation; missing `title_es`: "Reunión Abierta de La Viña". |
| `day` | `"thursday"` | Read by its first three letters, English or Spanish: `"Thursday"`, `"Thursdays"`, `"jueves"` all work. |
| `time` | `"12:00"` | In the meeting's own time zone: `"12:00"`, `"12 p. m."`, `"noon"`. |
| `timezone` | `"America/New_York"` | The meeting's zone; the site also shows Central ("11 AM Central"). An unknown zone (`"Eastern"`) takes the meeting off the site. |
| `starts` | `"2026-11-05"` | The first meeting. Until then `/meetings/` says "Starts Thursday, November 5, 2026" (`/es/meetings/`: "Comienza el jueves 5 de noviembre de 2026") and the toolkit "starting …". A date on another weekday is moved to the first real one. |
| `zoom_id` / `passcode` | `"871 2036 8287"` / `"238047"` | 9–11 digits: the formatted ID and a Join link `https://zoom.us/j/<digits>`. Otherwise no Zoom ID (and a test fails). |
| `summary_es` / `summary_en` | | Your own words; a missing one is machine-translated. |
| `url` | `""` | La Viña's page for it, once there is one (the card's details link). |
| `source` | flyer note | Stored, **not shown** on any page. |
| `flyer_match` | `"reuni[oó]n abierta de la vi[nñ]a\|la vi[nñ]a open meeting"` | The newest Drive file whose title or name matches → "View flyer" ("Ver volante") on the La Viña card. Matched by the page: capitals ignored, accents **not** folded (write `vi[nñ]a`). |

Examples (checked, "today" = October 2, 2026):
- Today's block → "Reunión Abierta de La Viña", Jueves, "12 p. m. (hora del Este)", "11 AM Central", first
  meeting Thursday, November 5, 2026, Join https://zoom.us/j/87120368287.
- `time: 720` (what an unquoted 12:00 becomes), `starts: "2026-11-04"`, `zoom_id: "871-2036-8287"` → the
  same result (the first meeting moves to Thursday, November 5).
- `day: "funday"` or `timezone: "Eastern"` → the meeting **silently disappears** from the site; the reason is
  only in the run's log, for example *lavina_weekly_open: unknown timezone 'Eastern' — item left out*.
- `zoom_id: "8712"` → no Zoom ID on the page, and Code check turns red.

> **Note — the push run reads it again.** The weekly open meetings are read by a module of the full daily run;
> when your save changes this block, the push run runs that module too (`scripts/ops/push_modules.py`), so the
> edit is on the site a few minutes later ([section 4](#4-what-happens-after-you-save)). `flyer_match` is read by
> the page itself. Mistakes here are never "Settings problems"; they appear only in the log of the step "Sync
> sources and translate" of the run.

Where it shows: `/meetings/#weekly-open` (both weekly meetings; a shared Zoom room is shown once),
`/accessibility/#phone`, the home page, `/monthly/` (from its first meeting), and the presentations
(`{live:lv_open_meeting}`, `{live:open_meeting_zoom}`).

### 3.8 `phone_access:` — joining by phone

For the "Join by phone" part of `/accessibility/#phone` (tap-to-call buttons, no internet or app needed) and
the presentations (`{live:meeting_phone}`, `{live:meeting_phone_passcode}`). The meeting IDs are not repeated
here: they come from `meeting:` and from the weekly open meetings.

| Key | Today | What it does |
|---|---|---|
| `numbers` | Houston, Chicago, New York, Washington DC | Zoom's U.S. dial-in numbers, as printed in any Zoom invitation under "Dial by your location". Each needs `number` and `city`; `city_es` is the city on `/es/`. **U.S. numbers only**: anything that is not a U.S. number (10 digits, with or without the +1) is silently dropped from the page. Write each one as `+1` and 10 digits: the test wants that form. The **first** number is used for every tap-to-call button. |
| `committee: phone_passcode` | `""` | The numbers-only passcode a caller types for the committee meeting. Zoom makes one because our passcode (`neta65`) has letters: it is in the host's Zoom invitation (the digits after `*` in the "One tap mobile" line, or "Passcode:" under "Dial by your location"). Empty: the page says "Ask the chair for the phone passcode". |
| `weekly_open: phone_passcode` | `""` | Leave it empty: that passcode (`238047`) is numbers only, and callers type it as it is. |

The rule: the digits you set here win; otherwise the meeting's passcode when it is all digits; otherwise
"ask the chair".

Examples (checked):
- Today → the committee's call button dials `tel:+13462487799,,9494767497%23`, with "Ask the chair for the
  phone passcode".
- `committee: { phone_passcode: "123456" }` → `tel:+13462487799,,9494767497%23,,,,*123456%23`, and the
  passcode is shown.
- The weekly open room → `tel:+13462487799,,87120368287%23,,,,*238047%23`.
- `number: "+44 20 7946 0958"` → dropped from the page (not U.S.), and Code check turns red.
  `number: "346 248 7799"` (without +1) works on the page, but Code check turns red: write
  `"+1 346 248 7799"`.

Tests (`tests/test_accessibility.py`): at least 3 numbers, one of them with 346 (Houston), each a valid U.S.
number written with the 1 (`+1` and 10 digits) and with a city; both `phone_passcode` values digits or
empty. Joining by phone works only while the host's Zoom settings allow it.

### 3.9 `meetings:` — Grapevine meetings near us

The "Grapevine meetings" list on `/meetings/#grapevine-meetings`: AA meetings with the Grapevine type
(`"GR"`), read once a day from the public meeting lists of eight offices — our Area's first, then the
nearby regions. Only public details are kept (name, day, time, place, meeting types, the office's own
link); never contacts, e-mails, phone numbers or online links. How the lists are read:
[automatic-sources.md](automatic-sources.md).

| Key | What it does | An edit shows |
|---|---|---|
| `enabled` | `false` = no Grapevine meetings list | After the push run |
| `type` | The meeting-type code to keep (`"GR"`) | After the push run (it reads the lists again) |
| `area_label` | The name of the first group, `{ en: "Our Area (NETA 65)", es: "Nuestra Área (NETA 65)" }` | After the push run |
| `key_source: url` | The Rowlett Group page, the last place the robot looks for a list's key | After the push run (it reads the lists again) |
| `key_source: page` | Not read (a note for people) | — |
| `feeds` | One entry per office; their order is the order on the page | See below |

Per office: `id` (required), `name`, `site`, `feed` (its JSON list), `page` (default `<site>/meetings/`),
`methods` (`feed`, `page`, tried in that order), `key_env` (the name of a GitHub secret holding the list's
key), `feed_obf` (the keyed address written backwards, then base64 — it only hides it from casual reading,
it is **not** encryption), `key_const`, `lang`, `in_area` (`true` = a Texas city that cannot be matched
counts as ours), `region_label` `{en, es}`, `add_types` (for example `["S"]` = in Spanish),
`region_types`, and `enabled: false` (accepted, not in the file today).

Removing an office, or `enabled: false` on it, takes its meetings off at the next build (push run); a
`region_label` shows after the push run; a new office, `feed`, `methods`, keys, types or `in_area` show after the
push run too, because any change in `meetings:` makes that run read the meeting lists again
(`scripts/ops/push_modules.py`). When an office gives out a new key, either ask NETA65 (admin) to store it as the
secret named in `key_env` (a new secret alone changes no file: the next full run uses it), or run
`python -m scripts.sync.meetings --obfuscate "<full address>"` on a computer and paste the result as `feed_obf`.
A key is never written in plain text in the repository. A test (`tests/test_meetings.py`) expects exactly
`aadallas` and `fortworthaa` to carry `feed_obf`. "Our Area" is decided by the counties in
`spotlight: neta65_counties` (next section).

### 3.10 `spotlight:` — published writers

| Key | Today | What it does |
|---|---|---|
| `home_days` | `60` | Home page "published writers": stories of the last N days (1–366; anything else: 60). |
| `list_days` | `[60, 90]` | The choices on `/published/`; the first is the default (invalid or repeated values are dropped). |
| `default_scope` | `"neta65"` | What `/published/` shows first: `neta65`, `texas` or `all` (capitals ignored; anything else: `neta65`). |
| `neta65_counties` | 75 county names | Which Texas counties count as Area 65 (a writer's place is matched with `data/geo/texas_places.json`). Also the Texas writers archive on `/published/#archive` and the "Our Area" group of the Meetings page. The comment above the list names borderline counties left out. |

Examples:
- (checked) `home_days: 0`, `list_days: [30, "x", 30, 400, 90]`, `default_scope: "Texas"` → home 60 days;
  `/published/` offers 30 and 90 days (30 first) and starts with Texas.
- Add `- Brown` to `neta65_counties` → writers from Brown County count as Area 65 on the home page, on
  `/published/` and in its Texas writers archive after the push run; that run also reads the meeting lists again,
  so the Meetings page's "Our Area" group follows in the same run.

#### `writers_archive:` — the Texas writers archive

The section right after `spotlight:`. The archive itself comes from the two exports in the repository folder
`content/archive/`, not from settings ([writers-archive.md](writers-archive.md)); this section holds its one
safety setting:

```yaml
writers_archive:
  min_rows_ratio: 0.8   # a new file with fewer rows than 80 % of the file used before is not used (0 = always use the newest)
```

| Key | Today | What it does |
|---|---|---|
| `min_rows_ratio` | `0.8` | A new archive file with fewer rows than this share of the rows of the file used before for the same magazine is **not used**: the magazine keeps its older rows and the run summary shows **CSV file to fix** ("… it looks cut off …"). `0` turns the check off (the newest file is always used). Missing → 0.8; above 1 → 1; below 0 → 0; not a number → 0.8, with a warning. |
| `folder` | not set | Another folder of the repository to read the files from (default `content/archive`). Not needed. |

Examples (the messages as `writers_archive.py` writes them):
- The Grapevine file in use had 35,942 rows; a new one has 20,000 → not used ("aagrapevine_archive_2026-12-01.csv
  has 20,000 rows, the file used before had 35,942 — it looks cut off, so the older data stays. If the smaller file
  is right, set writers_archive.min_rows_ratio: 0 in config/site.yml for one run").
- `min_rows_ratio: 0`, pushed with that file (or after it) → the file is used; then set `0.8` again.
- `min_rows_ratio: "eighty"` → 0.8 is used, and the archive's lines in the run summary say so.

An edit here shows after the push run (the archive files are read in every run).

### 3.11 `links:` — official links used across the site

Each key is an address that pages use as `site.links.<key>`. Change one here and every page using it
changes after the push run. The **weekly link check** (Sundays) tests every value starting with `http`
(plus `site.area_website`, `site.committee_page` and each podcast's `web`) and lists broken ones under "Fix
these addresses in config/site.yml" in the issue "Broken links found by the weekly check".

| Key | Where it shows |
|---|---|
| `gv_home`, `lv_home` | The footer's "official sites" (La Viña first on `/es/`), About, `/read/`, the organizer of a Grapevine or La Viña event |
| `gv_subscribe`, `lv_subscribe`, `gv_store`, `lv_store` | `/shop/` |
| `carry_the_message` | The `/shop/#carry` button and the GV/LV report on English pages, the orientation "subscriptions" session |
| `lleva_el_mensaje` | Its Spanish twin (La Viña's page): the `/es/shop/#carry` button, the Spanish GV/LV report, the orientation "subscriptions" session |
| `gv_share_story`, `gv_audio_project`, `gv_photo_contest`, `lv_share_story`, `gv_contribute`, `gv_guidelines`, `lv_guidelines` | `/contribute/` (the two guidelines also in the orientation "stories" session) |
| `gvr_register`, `rlv_register` | `/gvr/`, the home page's service band, the GV/LV report, the orientation "role" session |
| `gvr_resources`, `rlv_resources` | The `/gvr/` kits, the `/monthly/` guides, `/shop/`; `gvr_resources` also on `/contribute/` |
| `gv_apps`, `lv_apps` | The `/listen/` top card, `/offline/`, `/shop/` |
| `app_help_iphone`, `app_help_iphone_es`, `app_help_android`, `app_help_android_es` | `/offline/#steps` (the `_es` ones on `/es/offline/`). A test requires support.apple.com / support.google.com, and `/es-mx/` and `hl=es-419` in the Spanish ones |
| `weekly_open` | The "Details on aagrapevine.org" button of the Grapevine Weekly Open on `/meetings/#weekly-open` |
| `podcasts_page` | `/listen/` |
| `youtube_channel` | `/watch/` (subscribe) and the home page |
| `aa_org`, `aa_org_es` | About (the `_es` one on `/es/about/`), the orientation "traditions" session |
| `asl_playlist`, `aa_big_book`, `aa_twelve_and_twelve`, `aa_accessibility_resources`, `aa_access_email` | `/accessibility/`: the ASL, audio and large-print sections (both languages). Tests pin their form (a YouTube playlist; https://www.aa.org/…; an @aa.org address) |
| `aa_twelve_and_twelve_es` | Its Spanish twin: the Twelve and Twelve audio card on `/es/accessibility/` (the ASL list keeps aa.org's English page). A test requires https://www.aa.org/es/… |
| `gv_email_editorial`, `lv_email_editorial`, `gv_mail`, `lv_mail` | `/contribute/` (how to send a story); the two e-mail addresses also on `/monthly/` |
| `support_phone_us`, `support_phone_es`, `support_phone_intl` (and `support_phone_intl_es` on `/es/`) | `/shop/#help` |

> **Spanish twins (since October 2026).** Where a template reads a link through the `langLink` filter
> (`eleventy.config.js`, `LINK_TWINS`), a Spanish page shows the link's twin when the file has one: a key named
> `<name>_es`, or `lleva_el_mensaje` for `carry_the_message`. Today: the Carry the Message button and the help
> phones on `/es/shop/`, and the audio card on `/es/accessibility/`. `about.njk` (`aa_org_es`) and `offline.njk`
> (`app_help_*_es`) pick their twins in the template itself. A test (`tests/test_site_links.py`) checks that every
> key under `links:` is used by some page and that every link a template reads exists.

> **Removed in October 2026:** `sobriety_calculator`, `instagram_gv` and `instagram_lv` (no page used them), and
> the `lv_record_story` the `/contribute/` template looked for: La Viña's *Graba tu historia* link there now comes
> from `sources.lavina.record_story` (3.6), the same page the sync reads.

Example (a page that moved):

```yaml
  gv_guidelines: "https://www.aagrapevine.org/<the page's new address>"
```
→ After the push run, `/contribute/`, `/es/contribute/` and the orientation "stories" session link the new
address, and the next weekly link check tests it. A `<key>_es` next to a key gives the Spanish page its own
address only where the template reads the link with `langLink` (or `pick`), as above. A brand-new key shows
nowhere until a template uses it, and `tests/test_site_links.py` turns the Code check red until one does.

### 3.12 `library:` — official documents only

`official_hosts`: `aagrapevine.org`, `aalavina.org`, `aa.org`, `aaws.widen.net`. A document is kept on
`/library/` only when its file is on one of these hosts, or a subdomain such as `www.`. Documents on other
sites are left out, and the document search stops recording them. Empty or missing: the built-in list.

Example: remove `aaws.widen.net` → AA World Services' asset-library documents leave `/library/` and
`/es/library/` after the push run. Add a host → its documents appear only after the search (full runs)
records them.

### 3.13 `digest:` — the monthly digest

| Key | Today | What it does |
|---|---|---|
| `highlights` | `3` | Stories shown for each magazine issue (the rest are one link away). |
| `per_section` | `5` | Episodes, videos, documents … listed per section before "and N more". |

Both the `/digest/` page (and `/es/digest/`) and the monthly e-mail read them. Use **whole numbers**:
with `4.5` the e-mail uses 4 and the page falls back to its default (3, or 5 for `per_section`), so they
would differ; zero, a negative number or a word means 3 / 5. The page changes after the push run; the
e-mail at its next send (on the 1st of the month, after the month's first full update, at the latest on the
3rd). A test (`tests/test_digest_parity.py`) checks that the page and the e-mail pick the same items.

The e-mail is sent by a plain **SMTP** sender (not a Gmail API), and only when NETA65 (admin) has added the
secrets `SMTP_SERVER`, `SMTP_USERNAME`, `SMTP_PASSWORD` and `DIGEST_TO`. It also uses `site.title` (the
subject), `site.committee` (the From name) and `site.contact_email` (the footer and Reply-To). Recipients,
the sender code and test sends: [email-and-alerts.md](email-and-alerts.md).

### 3.14 `booth:` — the booth display

The booth display is the show that plays by itself at the committee's table (About page, `/about/#booth`). Its
slides come from `content/booth/booth.csv`, the Drive booth folder and the site's own data
([booth.md](booth.md)); this section only holds the size of its offline copy and the player's starting settings.
Every key is optional:

```yaml
booth:
  max_file_mb: 95
  max_total_mb: 400
  defaults:
    event_name: ""        # e.g. "NETA 65 Spring Assembly" (shown big at the top)
    event_name_es: ""     # e.g. "Asamblea de Primavera de NETA 65" (blank = the English one)
    language: "both"      # en | es | both | alternate
    sound: false          # start with the sound on? (true / false)
```

| Key | Today | What it does |
|---|---|---|
| `max_file_mb` | `95` | The biggest video or sound file (MB) the deploy saves for offline play. A bigger one is not saved, and so is left out of the show; the run's page names it (⚠ "Booth display: a file was not saved for offline"). Pictures are not held to it: they are saved as Google's 1920-pixel copies. |
| `max_total_mb` | `400` | The most (MB) of the booth folder saved for offline. The files marked `(first)`, then the ones listed first, are kept first; past the limit a picture shows only while the booth is online and a video or sound file is left out. Never more than 800, whatever it says: the saved files are published with the site, and GitHub Pages takes sites up to 1 GB. |
| `defaults: event_name` / `event_name_es` | `""` | The event's name, big at the top of the booth screen (at most 80 characters): the Spanish one on Spanish slides, the English one when it is blank. A booth can type its own in the player's Settings → Event. |
| `defaults: language` | `"both"` | `en` (English slides, and pictures without words), `es` (Spanish), `both` (every slide in both languages) or `alternate` (one language, then the other). |
| `defaults: sound` | `false` | `true` starts the booth with its sound on (videos, sound files, the podcast). |

These are every device's **starting** settings: a booth keeps only what was changed on it and follows the site for
the rest, and its Settings → Share & reset → **Reset the settings** brings it back to them (on the Spanish page a
booth also puts Spanish first in "both"). Saved here, they reach `/about/booth.json` with the push run; a booth that
is playing picks them up within half an hour, at its next slide. The two limits are read by the build job's
download step in the same run. A value that cannot be read keeps the player's own default and is named in the build
log (`[booth] …`) and in the player's Settings → Slides (Spanish page: Ajustes → Diapositivas) — for example
*config/site.yml booth.defaults.language: "spanish" is not en, es, both or alternate: both is used*.

### 3.15 `config/carry.yml` — "Put this issue to work"

Every text is a pair `{ en: "…", es: "…" }`, and both languages are required.

| Key | Format | Where it shows |
|---|---|---|
| `intro` | `{en, es}` | The lead of `/monthly/#ways` |
| `source` | `{en, es}` | The "Source:" line under the ways |
| `ways` | 10 entries: `id`, `icon` (a [Lucide](https://lucide.dev/icons) name), `title` and `text` `{en, es}` | The cards on `/monthly/#ways`; the "10 ways" link on each month's page |
| `story_note` | `{en, es}` | The note under the ways, with a link to `/contribute/` |
| `guides` | `{en, es}`, optional | "Serving as your group's GVR or RLV?", with links to the GVR Workbook and RLV manual in the Library and to `links.gvr_resources` / `rlv_resources` |
| `tips` | `"YYYY-MM":` (the Grapevine **issue** month, in quotes) → a list of `{ way: <a ways id>, text: {en, es} }` | That month's toolkit, `/monthly/YYYY-MM/` ("Put it to work"); the GV/LV report; the presentations' monthly slide; the orientation "tip" example |

Theme names are not stored here: the pages show the issue's own theme, or the editorial calendar's. The
`# Theme` comment after each key is only a reminder. Today's tips run from `"2026-09"` to `"2027-12"`.

Example — the next editorial year, appended at the end of `tips`:

```yaml
  "2028-01":   # next January's theme (a reminder only)
    - way: group-topic
      text:
        en: "Read one short story aloud and ask the group how it fits their own experience."
        es: "Lean en voz alta una historia corta y pregunten al grupo cómo se relaciona con su propia experiencia."
```
→ `/monthly/2028-01/` and `/es/monthly/2028-01/` show this tip under the "Bring it to your group and talk
about the new issue" way (with its icon) once that toolkit page exists.

A mistake **stops the build** on GitHub (red ✗ on Website update and Code check; the site stays as it was
until it is fixed). For example `way: "newcomers"` (there is no such way) →
*[carry] config/carry.yml: tips 2028-01 #1: unknown way "newcomers"*; a missing Spanish text →
*… tips 2028-01 #1 text: missing "es"*. Also reported: a duplicate way id and a key that is not
`"YYYY-MM"`.

### 3.16 `config/expenses.yml` — the Tracker's starting lists

The Tracker (`/tracker/`, `/es/tracker/`) keeps each visitor's entries and settings in their own browser.
This file gives the lists everyone starts with.

| Key | Rules |
|---|---|
| `tones` | Colours that exist: `gv`, `lv`, `grape`, `vine`, `rose`, `teal`, `gold`, `slate`. |
| `icons` | Lucide icon names (the icon picker). Every category's icon must be in this list. |
| `categories` | `id` (lower-case letters, digits and `_`, **no dashes**; never rename one: exported CSV files map by it), `type` (`expense`, `mileage`, `received`, `giveaway`, `stock` — each type needs at least one category), `template` (`general`, `books`, `subscription`, `lodging`, `meal`, `printing`, `travel`, `mileage`, `received`, `giveaway`, `stock`), `icon`, `color` (a tone), `label` `{en, es}`; optional `default_funder`, `default_claim` (`none` / `to_request`), `giveaway_default: true`. |
| `funders` | `id`, `kind` (`self`, `area`, `district`, `group`, `committee`, `person`, `other`), `name` `{en, es}`. `me` with kind `self` is required. |
| `methods` | `id`, `name` `{en, es}`. `direct` = paid by the funder directly (left out of "my spending"). |
| `activities` | `id`, `name` `{en, es}`: the service report's sections, in this order. |
| `rates`, `default_rate` | Each rate: `id`, `name` `{en, es}` and `rate` as text with up to 3 decimals (`"0.14"`), or `""` for the visitor to fill in. `default_rate` is a rate id (today `irs_charity`). |
| `defaults` | `funder`, `method`, `round_trip`. |
| `panels` | `{id, from, to}` dates, `from` not after `to`. Since October 2026 (Tracker 1.2.0) the Tracker works the panels out by itself: Area 65's terms start on January 1 of an odd year, and Panel N starts in 1950 + N (Panel 75: 2025–2026, Panel 77: 2027–2028, Panel 79: 2029–2030). The period filters and the report offer the current panel, the panel of every year that has an entry, and every panel listed here. An entry here only changes a panel's dates or adds one: **nothing needs adding every two years**. Today it lists Panel 75 and Panel 77. |
| `renewal_days`, `backup_reminder_days` | Whole days, 1–365 (today 60 and 30). |

Example — a new category:

```yaml
  - id: hospitality
    type: expense
    template: general
    icon: coffee
    color: gold
    label: { en: "Coffee & hospitality", es: "Café y hospitalidad" }
```
→ It appears at the end of every visitor's category list the next time they open `/tracker/`.
`id: "coffee-hospitality"` would stop the build: *[expenses] config/expenses.yml: categories
coffee-hospitality: ids are lower-case letters, digits and _*; so would an icon missing from `icons`
(*… icon "cup-soda" is not in the icons list*).

How a change reaches people who already use the Tracker (checked with the Tracker's own code):
- a **new** category, funder, method, activity or rate is added at the end of their lists;
- a **reworded** label reaches everyone who has not renamed it themselves;
- a built-in item a visitor deleted stays deleted;
- a **changed number does not**: someone who has used the Tracker keeps the rate stored in their browser
  (change `"0.14"` to `"0.15"` and they still have 0.14). New visitors get the new rate; tell the others to
  change it in the Tracker's Settings → Mileage.

Tests (`tests/test_expenses_page.py`): unique ids, known types, templates, tones and kinds, the 21 standard
category ids (`books` … `stock_in`) must exist, `default_rate` is `irs_charity`, and more.

### 3.17 `config/history.yml` — the timeline on the About page

| Key | Format |
|---|---|
| `official: grapevine`, `official: lavina` | Links to the official histories, under the timeline (a test requires https://www.aagrapevine.org/…). |
| `milestones` | **Oldest first.** `year`: `"June 1944"`, `"Summer 1996"` or `"1948"` (an English month or season, then the year); `type`: `grapevine`, `lavina` or `both`; `title` `{en, es}` (a short heading, no full stop); `desc` `{en, es}`. |

The Spanish label is made from `year`: "June 1944" → "Junio de 1944", "Summer 1996" → "Verano de 1996",
"1948" stays "1948". The timeline shows on `/about/#history` and `/es/about/#history`, grouped by decade,
with filters All / Grapevine / La Viña and "Show all".

Example — a new milestone, placed last:

```yaml
  - year: "October 2026"
    type: both
    title:
      en: "New prices announced for 2027"
      es: "Se anuncian nuevos precios para 2027"
    desc:
      en: "AA Grapevine announces new subscription and book prices, starting January 1, 2027."
      es: "AA Grapevine anuncia nuevos precios de suscripciones y libros a partir del 1 de enero de 2027."
```
→ A new card in the 2020s on both About pages ("October 2026" / "Octubre de 2026"), counted under both
filters. **But Code check turns red**: `tests/test_history.py` expects exactly 40 milestones — change the 40
(search for `len(self.ms), 40`) in the same commit. The test also checks the wording: curly quotes only
(“ ” ’ in English, « » in Spanish, never `"` or `'`), no words such as PDF, robot, bot, crawl or
automatically, and headings without a full stop.

These stop the build (the site stays as it was until fixed): an unreadable year (`"Octobre 2026"` →
*milestone 41 (Octobre 2026): year must look like "June 1944", "Summer 1996" or "1948"*), an unknown type,
a year out of order, a missing language, an official link that does not start with https://.

### 3.18 `config/orientation.yml` — "GVR / RLV 101"

The pages: `/orientation/` (the hub, slides and printable handout) and one page per session,
`/orientation/<id>/` and `/es/orientation/<id>/`. Every text is `{en, es}`. Wording (the file's header):
"sessions", "facilitator", "review questions", "position" — never lesson, course, class, training,
trainer, quiz or job.

| Key | Format |
|---|---|
| `panel: number`, `panel: starts` | `77`, `"2027-01"` → the placeholders `{panel}` and `{panel_start}` ("January 2027" / "enero de 2027"). |
| `lessons` | The six sessions: `magazines`, `role`, `literature-table`, `subscriptions`, `stories`, `traditions`. Each: `id` (the page address: lower-case letters, digits, dashes — keep it), `icon`, `minutes`, `example` (`issue`, `meeting`, `tip`, `botm`, `deadline`, `poster`: the live example the page shows), `title`, `summary`, `goal`, `points` (3–6, each `{title, text}`), `try`, `discuss`, `links`, `check` (3 questions × 3 `options`, `answer` 1–3, `why`). |
| `links` items | A `label` `{en, es}`, plus `href` (a page of this site, without `/es/`), **or** `link` (a key of `links:` in `config/site.yml`; `link_es` for the Spanish page), **or** `url` (https://; `url_es`). `pub: gv` / `lv` puts La Viña's link first on Spanish pages. |

Placeholders filled on the pages: `{rule_lc}` ("every third Wednesday of the month", from `meeting:`),
`{time}` ("7:00 – 8:00 PM"), `{panel}`, `{panel_start}`. Anything else in braces stays as typed.

Example — the next panel:

```yaml
panel:
  number: 79
  starts: "2029-01"
```
→ The "role" session reads "Panel 79 of our Area runs for two years from January 2029" / "El Panel 79 de
nuestra Área dura dos años a partir de enero de 2029". (The presentations' `{live:panel}` comes from the
Drive panel folder's name instead.)

Two kinds of checks:
- **The build stops** on a missing language, fewer than 3 or more than 6 points, a session without
  exactly 3 questions, a question without 3 options, an `answer` outside 1–3 (*lesson 1 question 1: answer
  must be 1–3*), a bad or repeated `id`, an unknown `example`, `minutes` outside 3–12, a link without
  `href`, `link` or `url` (or a `url` that does not start with https://), or a `panel: starts` that is not
  `"YYYY-MM"`.
- **The build works, but a test fails** (`tests/test_orientation.py`: Code check red; Website update still
  publishes, because it leaves the tests that judge this file to the Code check — fix the file soon): not exactly
  6 sessions; `minutes`
  outside 5–8 (so `minutes: 10` builds but fails the test); a summary over 110 characters (English) or 135
  (Spanish); a title over 32; a point over 240; the right answer always in the same place; an unknown
  placeholder; a banned word; a link that does not resolve (`link` must be a key in `links:`, `url` must
  be on aagrapevine.org or aalavina.org).

### 3.19 `config/presentations/` — the four web presentations

One YAML file per deck (`orientation-workshop`, `information-workshop`, `writing-workshop`,
`committee-meeting`), shown on `/orientation/#presentations`. Their `{live:…}` facts come from the settings
above: `contact_email`, the site address, `meeting:`, `phone_access:`, `price_changes:`, the La Viña
workshop in `recurring_events:` and `lavina_weekly_open:`. One deck problem stops the build. Everything
else: [presentations.md](presentations.md) and
[config/presentations/README.md](../config/presentations/README.md) (editing that README does not start a
rebuild).

### 3.20 `content/instagram.yml` — Instagram posts added by hand

Usually `posts: []`: the site reads @alcoholicsanonymous_gv and @alcoholicosanonimos_lv by itself. Add a
post only when the automatic check missed it, or to feature an older one. The file is read by the **full daily
run**, and by the push run of the save that changes it: that run also reads Instagram
(`scripts/ops/push_modules.py`), without the look-ups of each post's own page.

```yaml
posts:
  - url: https://www.instagram.com/p/DAbcdEFgh12/
    account: gv
    caption: "Our booth at CityWide Dallas"
  - https://www.instagram.com/reel/C9xYz123AbC/
  - url: https://www.instagram.com/alcoholicosanonimos_lv/p/C8LvPost001/
    account: "@alcoholicosanonimos_lv"
```
→ (checked) Three posts on `/instagram/`, the home Instagram card, What's New and the digest, after the push run
(a picture or caption the accounts' pages did not give comes with the next full run): the first as Grapevine's
with our caption; the reel without `account`, shown as Grapevine's unless the look-up finds its account; the
third as La Viña's.

Per entry: `url` (or `link`) of a post or reel (`/p/`, `/reel/`, `/reels/`, `/tv/`, with or without the
account in the address) or a `shortcode`; optional `account` (`gv`, `lv`, or the username with or without
`@`), `caption` (shown instead of Instagram's) and `date` (otherwise worked out from the post's code). A
plain address on its own line works too. Posts listed here are never removed automatically; delete an
entry to remove the post (the push run of that save). Problems (*unknown account 'aa' (use gv or lv)*, *no Instagram
post link found in …*, *YAML error — …*) never stop anything: they appear under **Notes** in the run
summary (at most two per source), not on `/status/`. How Instagram is read:
[automatic-sources.md](automatic-sources.md).

---

## 4. What happens after you save

Every saved settings file starts two GitHub Actions runs (editing `config/presentations/README.md` starts
only Code check):

- **Website update, the push run** — a *quick* run: it reads the committee's Drive, the bulletin, the
  podcasts, the writers archive files and the two daily quotes, rebuilds the data, builds the whole site from the
  current files and publishes it. The tests before publishing do not run again for a settings file: they test the
  code, and since October 2026 the committee's files are not part of the code's fingerprint
  ([automation-and-troubleshooting.md §4.8](automation-and-troubleshooting.md#48-the-tests-before-publishing)).
  Usually **about 3 minutes** (the posters' share pictures take about one of them). When the save changed
  a setting that a source of the full daily run reads (YouTube, Instagram, the editorial themes, the weekly open
  meetings, the story lines, the meeting lists, the event calendars), that source runs in the same push run
  (`scripts/ops/push_modules.py` compares `config/site.yml` with its copy from before the save; the run summary
  says **Also run for this push**). It is listed in the Actions tab under your commit message.
- **Code check (tests and test build)** — every test, a strict test build and the browser checks (about 10
  minutes). It publishes nothing; a red ✗ there means a test disagrees with the change
  ([section 7](#7-troubleshooting)). The push run has published it all the same, leaving out what the build
  could not use: fix the file soon. (What the build itself refuses — a `config/site.yml` YAML cannot read, a
  mistake in `carry.yml`, `orientation.yml`, `history.yml`, `expenses.yml` or a deck that stops the build — is
  not published: the site stays as it was until it is fixed.)

Only one Website update run works at a time. If another one is still going when you save (for example the
full daily update, in the morning), the push run waits for it to finish, so the change shows that much
later.

The rest — the magazine stories, the store's pages and the document search — waits for the **full daily
update** ("Nightly full update" in the Actions tab). GitHub's schedule asks for it at 07:17 UTC (2:17 AM CDT,
1:17 AM CST) — deliberately 4 hours early, because GitHub starts timed runs 4–6 hours late — so it usually starts
about 6–8 AM Central (5–7 AM in winter). The
document search may use up to 40 minutes of it (`sources: crawler: minutes_per_run`), plus up to 40 for
translations; in early October 2026, with every page already found, full updates took
10–15 minutes. On the 1st of the month, and when no full update has run for 30 hours, the Morning check
starts one too.

**Don't want to wait?** Actions → **Website update** → **Run workflow**, leave "skip_crawl" and "morning"
unticked, and click **Run workflow**. Type `0` in "crawl_minutes" for a full update without the document
search (faster). Write access is enough (MKP715).

| You saved … | Live after the push run | Waits for the next full update |
|---|---|---|
| `site:` (all keys), `meeting:`, `recurring_events:`, `price_changes:`, `drive:`, `phone_access:`, `links:` | Yes | — |
| `sources: grapevine / lavina` | The links on the pages; `quote_page`; and what the push run reads again when its key changed: deadlines and themes, the Weekly Open, the story lines (a changed `base`: those and the event calendars) | The magazine stories (`magazine_hub`) and the shop (`botm`, `subscriptions`, `subscription_regions`, `specialty`) |
| `sources: crawler` | — | Yes |
| `sources: youtube` | Yes (the channels' feeds) | The full listing of older videos |
| `sources: instagram` | Yes | The look-ups of single posts |
| `sources: podcasts` | Yes | Looking for new feeds |
| `sources: ics_feeds` | Yes (each calendar is asked at most once in about 20 hours) | — |
| `lavina_weekly_open:` | Yes | — |
| `meetings:` | Yes (the push run reads the meeting lists again) | — |
| `spotlight:` | Yes (home, `/published/` and its Texas writers archive; `neta65_counties` also the Meetings page's "Our Area") | — |
| `writers_archive:` | Yes | — |
| `library:` | Removing a host | A new host's documents |
| `digest:` | The `/digest/` page | The e-mail: at its next monthly send |
| `booth:` | Yes (`/about/booth.json`, and the media limits in the same run's download step); a booth that is playing takes it within half an hour | — |
| `config/carry.yml`, `expenses.yml`, `history.yml`, `orientation.yml`, `presentations/*.yml` | Yes — and a mistake **stops the deploy** | — |
| `content/instagram.yml` | Yes (the push run also reads Instagram) | The look-ups of single posts (their pictures and captions) |

---

## 5. Where each setting shows

| Page (English / Spanish) | Settings that feed it |
|---|---|
| Every page: browser tab, footer | `site: title`, `committee` (©), `area_website` and `contact_email` (footer buttons); `links: gv_home`, `lv_home` |
| Home `/`, `/es/` | `meeting:` (next-meeting card, Join); `recurring_events:` ("Upcoming events"); `spotlight: home_days`; `links: gvr_register`, `rlv_register`, `youtube_channel`; `lavina_weekly_open:`; `sources: grapevine / lavina: quote_page` (the two daily quotes) |
| `/meetings/` | `meeting:` (#committee-meeting, with `platform` and `note` / `note_es` in *Who can come*); `lavina_weekly_open:` and `links: weekly_open` (#weekly-open); `meetings:` and `spotlight: neta65_counties` (#grapevine-meetings); `contact_email` (the question button under the Grapevine meetings) |
| `/events/`, `/events.ics`, `/es/events.ics` | `meeting:`, `recurring_events:`, `sources: ics_feeds`; `site: committee` (the meeting's title); `contact_email` |
| `/accessibility/` | `phone_access:` and the meeting IDs (#phone); `links: asl_playlist`, `aa_big_book`, `aa_twelve_and_twelve` (`aa_twelve_and_twelve_es` on `/es/`), `aa_accessibility_resources`, `aa_access_email`; `contact_email` (#feedback); `meeting: chair_email` ("Email the chair" for the phone passcode) |
| `/listen/`, `/watch/` | `site: listen`, `watch`; `links: gv_apps`, `lv_apps`, `podcasts_page`, `youtube_channel`; `sources: podcasts`, `youtube` |
| `/about/` | `site: area`, `committee_page`, `area_website`, `contact_email`, `about_videos`; `links: gv_home`, `lv_home`, `aa_org`; `config/history.yml` (#history); the next meeting date; `booth:` (#booth, the booth display's starting settings and the size of its offline copy; its live slides use `meeting:`, `recurring_events:`, `lavina_weekly_open:`, `price_changes:`, `site: committee` and `about_videos` too) |
| `/shop/` | `price_changes:` (#price-changes); `links:` (stores, subscriptions, `carry_the_message` / `lleva_el_mensaje` on `/es/`, support phones); `sources: grapevine / lavina` (Book of the Month, prices, specialty items) |
| `/contribute/` | `links:` (share a story, guidelines, e-mails, mail); `sources: lavina` (themes, record your story: `record_story`), `sources: grapevine: audio_project` |
| `/gvr/` | `links: gvr_register`, `rlv_register`, `gvr_resources`, `rlv_resources`; `meeting:` (date, time, platform, chair e-mail); the orientation's total minutes |
| `/monthly/`, `/monthly/YYYY-MM/` | `config/carry.yml`; `meeting:`; `recurring_events:`; `price_changes:`; `links: gvr_resources`, `rlv_resources`, editorial e-mails |
| `/digest/` and the monthly e-mail | `digest:`; `site: title`, `committee`, `contact_email`; `meeting: chair_email` (the page's "Write to the chair") |
| `/orientation/` and its sessions | `config/orientation.yml`; `meeting:` (`{rule_lc}`, `{time}`); `links:` (`link:` keys); `config/presentations/` |
| `/tracker/` | `config/expenses.yml` |
| `/published/` | `spotlight:` (also the Texas writers archive's Area 65, `#archive`); `writers_archive:`; `contact_email` ("Email the committee") |
| `/library/` | `library:`; `contact_email` |
| `/offline/` | `links: app_help_*`, `gv_apps`, `lv_apps` |
| `/share/` | `meeting:` (the poster); `site: title`, `contact_email` (on the poster) |
| `/instagram/` | `sources: instagram: accounts`; `content/instagram.yml` |
| `/status/` | `site: repository` (Actions button), `morning_goal` (the daily quote's mornings); `sources: ics_feeds` ("Other calendars") |
| RSS `/feed.xml`, `/es/feed.xml` | `site: url`, `contact_email` |
| The presentations | `{live:…}` facts from `contact_email`, the site address, `meeting:`, `phone_access:`, `price_changes:`, `recurring_events:`, `lavina_weekly_open:` |

---

## 6. Going further: change the code

### How a setting reaches a page

- **The website build.** [`src/_data/site.js`](../src/_data/site.js) reads `config/site.yml` and hands the
  templates `site`: every key of `site:`, plus `meeting` (with `platform`, Zoom when left out), `recurring_events`,
  `drive`, `sources`, `links`, `phone_access`, `digest`, `lavina_weekly_open`, and since October 2026 `meetings`
  and `spotlight` (so `/meetings/` still lists each office's site when `data/site/meetings.json` is missing).
  **Not** handed over: `price_changes`, `library` — they reach the pages only through the synced data files. On
  GitHub, `url` and `repository` are replaced (search for `process.env.SITE_URL`), and `timezone` is always a
  real zone (`TZ` from `eleventy.config.js`: America/Chicago when the setting is not one).
- **The `pick` filter** ([`eleventy.config.js`](../eleventy.config.js), search for `addFilter("pick"`):
  `site | pick(lang, "title")` gives `title_es` on Spanish pages when it exists, else `title`. So a
  `<key>_es` next to any key works wherever a template reads it with `pick`.
- **The meeting's dates**: [`src/_data/meeting.js`](../src/_data/meeting.js) and
  `eleventy/filters/committee.js` (`meetingDates`, `meetingTitle`, `meetingDescription`), both reading the
  block through `monthlyRule()` in `eleventy.config.js` — the same rules as `meeting_rule()` in
  [`scripts/sync/meeting.py`](../scripts/sync/meeting.py), so the pages and the data always agree.
- **The other files**: `src/_data/carry.js`, `expenses.js`, `history.js`, `orientation.js`,
  `presentations.js`. Each checks its file; with `I18N_STRICT` set (as on GitHub) a problem stops the build.
- **`booth:`** is read straight from `config/site.yml` (not through `site.js`, and never by the sync): by
  [`src/_data/booth.js`](../src/_data/booth.js) (`boothDefaults()` in
  [`eleventy/filters/booth.js`](../eleventy/filters/booth.js): a value it cannot read is a problem line, never a
  stopped build) and by [`scripts/build/booth-media.mjs`](../scripts/build/booth-media.mjs) (the two limits,
  through `parseBoothConfig()` in `booth-media-core.mjs`).
- **The daily sync**: `load_config()` in [`scripts/sync/common.py`](../scripts/sync/common.py) reads
  `config/site.yml` once per run, and each module reads its own section: in
  [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) `committee_meetings()`,
  `recurring_specs()`, `price_change_specs()` (→ `specs()` in `scripts/sync/price_changes.py`),
  `feed_specs()`, `spotlight_settings()`, `quote_days()`; `lavina_item()` in `scripts/sync/weekly_open.py`;
  `main()` and `crawl()` in [`scripts/sync/drive.py`](../scripts/sync/drive.py); `settings()` in
  `scripts/sync/meetings.py`; `load_manual()` in `scripts/sync/instagram.py`; `min_rows_ratio()` and
  `archive_dir()` in [`scripts/sync/writers_archive.py`](../scripts/sync/writers_archive.py).
- **Which settings a push re-reads at once**: `SETTINGS` in
  [`scripts/ops/push_modules.py`](../scripts/ops/push_modules.py) lists, for each source only the full daily run
  reads, the parts of `config/site.yml` it reads while it syncs. A setting you add to such a source belongs there
  too (`tests/test_push_modules.py` checks that each one exists in `config/site.yml` and is named in its module).

### Example: a new detail on the committee meeting

Goal: a short "before you join" note in the "How to join" card on `/meetings/`.

1. In `config/site.yml`, under `meeting:`:
   ```yaml
     join_note: "The waiting room opens 10 minutes early."
     join_note_es: "La sala de espera se abre 10 minutos antes."
   ```
   Templates can already read it as `site.meeting.join_note`: no loader change is needed.
2. In [`src/pages/meetings.njk`](../src/pages/meetings.njk), find the "How to join" card (search for
   `committee.meeting.how_to_join_text`) and add, right after that paragraph:
   ```njk
   {%- set joinNote = m | pick(lang, "join_note") -%}
   {% if joinNote %}<p class="mt-2 max-w-[60ch] text-sm text-muted">{{ joinNote }}</p>{% endif %}
   ```
   (`m` is `site.meeting` in that template; `pick` gives `join_note_es` on `/es/meetings/`.)
3. Other places, if wanted: the home card in `src/pages/index.njk` (`mt` is `site.meeting`; search for
   `home-meet-join`), the poster in `src/pages/share.njk` (the `meetBlock` macro), the calendar text in
   `meetingDescription()` in `eleventy/filters/committee.js`, and — for `data/site/events.json` and the
   e-mail — the `extra` of each item in `committee_meetings()` in `scripts/sync/build_data.py`.
4. A fixed label (for example a heading) goes in `src/_i18n/committee.json` with both `en` and `es`. A key
   the template asks for that no file has stops the build on GitHub; a missing language shows the English
   text on the Spanish page and turns Code check red (`tests/test_i18n_keys.py`)
   ([translations.md](translations.md)).

### Example: a new top-level section

To add, say, `notice:` to `config/site.yml`, hand it to the templates in `src/_data/site.js`, next to
`digest: cfg.digest || {},`:

```js
    digest: cfg.digest || {},
    // a short site-wide notice (config/site.yml notice:) — templates read site.notice.<key>
    notice: cfg.notice || {},
```
The sync scripts read it with `load_config().get("notice") or {}`.

### Other changes, and where they are made

| You want … | Where |
|---|---|
| A new detail on a monthly event | [flyers-and-events.md](flyers-and-events.md) (`recurring_specs()` → `recurring_events()` → `shapeEvent` → `src/pages/events.njk`) |
| A new kind of plan in `price_changes` | `TYPES` in `scripts/sync/price_changes.py` (search for `TYPES = ("print"`), plus `eleventy/filters/shop.js` |
| A new `{live:…}` fact in the presentations | [presentations.md](presentations.md) (`liveFacts()` in `eleventy/filters/presentations.js`) |
| A 41st history milestone | Change the 40 in `tests/test_history.py` (search for `len(self.ms), 40`) |
| A 7th orientation session | Change the 6 in `tests/test_orientation.py` (search for `len(self.lessons), 6`) |
| A fifth presentation | `DECKS` in `tests/test_presentations.py`, and the four names in `tests/test_presentations_core.py` (search for `"writing-workshop", "committee-meeting"}`) |
| A Spanish twin for another link | Give the link a `<name>_es` in `links:` and read it in the template with `langLink` (for example `site.links | langLink("aa_big_book", lang)`; see `src/pages/shop.njk`, search for `langLink`); a twin with another name goes in `LINK_TWINS` in `eleventy.config.js` |
| What the monthly e-mail says, or who gets it | [email-and-alerts.md](email-and-alerts.md) (`scripts/notify/send_digest.py`) |

### Tests

Run them on a computer that has the project set up, from the repository folder:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests            # everything
.venv\Scripts\python.exe -m unittest tests.test_accessibility -v  # one file
```
(With another Python that has `requirements.txt` installed: `python -m unittest discover -s tests`.) Or
simply commit and read **Code check** on GitHub, which runs the same command. To see the strict build on a
computer, set `$env:I18N_STRICT = "1"` (missing texts, and the mistakes above that stop the build) and
`$env:STRICT_BUILD = "1"` (a missing icon, a page missing from the sitemap, a link in the data that had to be
repaired or hidden — what fails the Code check's build since October 2026) before `npx @11ty/eleventy`.

**Every setting must be read by some code** (since October 2026, `tests/test_settings_used.py`). Every key in
`config/site.yml`, `expenses.yml`, `carry.yml`, `history.yml` and `orientation.yml` must be read by the sync, the
build or a page, or the Code check goes red ("settings … that no code reads"): a key added by mistake, misspelled,
or one that no longer does anything. A Spanish twin `<name>_es` counts when `<name>` is read; the keys that are
names rather than settings (the region names under `meetings: feeds: region_types`, the months of `carry.yml`
`tips`) are listed in the test with their reasons. The other way round, every setting the pages, the build or the
sync read must be there, or be read with a default: deleting `meeting: platform` is fine (Zoom), deleting a link a
page reads is not. These parts judge your files, so only the Code check runs them; *Website update* publishes.

Tests that pin values in the settings files. Since October 2026 they are all left to the Code check
(`CONTENT_TESTS` in `scripts/ops/gate_tests.py`): a change that breaks one turns **Code check** red, and *Website
update* still publishes it:

| Test file | What it expects |
|---|---|
| `tests/test_read_media_asides.py` | `site: listen: sidebar_short` and `watch: hero_video` exist and have 11 characters |
| `tests/test_accessibility.py` | `phone_access:` at least 3 U.S. numbers written `+1` and 10 digits, one with 346, each with a city; phone passcodes digits or empty; `meeting_id` and `lavina_weekly_open: zoom_id` 9–11 digits; the form of the accessibility links (`asl_playlist`, `aa_big_book`, `aa_twelve_and_twelve`, `aa_twelve_and_twelve_es`, `aa_accessibility_resources`, `aa_access_email`) |
| `tests/test_pwa_install.py` | `links: app_help_*` on support.apple.com / support.google.com, the Spanish ones with `/es-mx/` and `hl=es-419` |
| `tests/test_site_links.py` | Every key under `links:` is used by some page (a `_es` twin counts with its link), every link a template reads exists, the removed settings stay removed, La Viña's monthly workshop is called by its one name. (`meeting: platform` may be left out or changed: since October 2026 no test pins "Zoom" or a `note`) |
| `tests/test_price_changes.py` | The real `price_changes:` blocks have no problems |
| `tests/test_sync_pipeline.py` | `sources: instagram: keep_per_account` at least 124 |
| `tests/test_meetings.py` | Exactly `aadallas` and `fortworthaa` carry `feed_obf`; no key in plain text |
| `tests/test_editorial.py` | La Viña's themes page resolves to https://www.aalavina.org/recursos |
| `tests/test_push_modules.py` | Every setting `scripts/ops/push_modules.py` names (`sources.youtube`, `sources.lavina.themes_link`, `lavina_weekly_open`, `meetings`, `spotlight.neta65_counties` …) still exists in `config/site.yml` and is read by its module |
| `tests/test_orientation.py` | 6 sessions, 5–8 minutes, lengths, questions, placeholders, wording, links |
| `tests/test_history.py` | Exactly 40 milestones, oldest first, wording, official links |
| `tests/test_expenses_page.py` | Ids, types, the 21 standard categories, `irs_charity` |
| `tests/test_presentations.py`, `tests/test_presentations_core.py` | Exactly the four decks, each passing the checker |

Other tests read the real settings without a fixed value (`test_digest_parity.py`, `test_morning.py`,
`test_presentations_build.py`), or use their own copies (`test_recurring_events.py`,
`test_events_feeds.py`), so changing the real file does not break them.

---

## 7. Troubleshooting

Where problems show up:
- **The run summary** of Website update (Actions → the run → Summary): "**Settings problems** (the rest of
  the site still updated — fix the file and save it again)" lists what `meeting:` (skip dates only),
  `recurring_events:`, `sources: ics_feeds:` and `price_changes:` could not use, each also as a yellow
  "Settings problem (…)" annotation. Each of these settings gets one line that starts with
  `config/site.yml` (for example `config/site.yml price_changes entry 1 (2028-07): …`); several entries'
  notes on one line are separated by " / ". The same text is kept in `data/site/status.json` → `problems`
  in the repository; the public `/status/` page does **not** list them.
- **A red ✗ on Website update**: the build stopped and the site stays as it was. Open the run, then the
  failed step ("Build the website"; for a YAML slip in `config/site.yml` also "Sync sources and translate"): the
  error names the file and the problem.
- **A red ✗ on Code check alone**, after you saved a settings file: a test disagrees with the change. The site
  was still published (since October 2026 the tests that judge the settings files run only in the Code check:
  `CONTENT_TESTS`), without what the build could not use. Open the Code check's job "Python tests (offline)" and
  look for the `FAIL:` or `ERROR:` lines; fix the file (or the test, if the change was meant) soon.
- **A red ✗ on Website update with *Tests failed — not published***: a change of the **code** broke the tests;
  the site keeps the version before
  ([automation-and-troubleshooting.md §14.10](automation-and-troubleshooting.md#1410-tests-failed--not-published)).
  A settings file alone never causes it.
- **Notes** in the run summary: small problems of a source that still updated (for example
  `content/instagram.yml`).
- **The log** of the step "Sync sources and translate": the only place where mistakes in `lavina_weekly_open:` and
  most of `sources:` appear. (A `drive:` mistake that stops the Drive source, such as an empty
  `root_folder_id`, shows as **PROBLEM** in the summary's "Content sources" table and on `/status/`.)

| Symptom | Cause | Fix |
|---|---|---|
| Red ✗ on both runs right after saving `config/site.yml`; "bad indentation of a mapping entry" or "mapping values are not allowed here" | A YAML slip: a space too many or too few, a `: ` in text without quotes, a quote not closed | Open the file's History, compare with the previous version, fix or undo ([section 2](#undo-a-change)). |
| Red ✗; the error starts with `[carry]`, `[expenses]`, `[history]`, `[orientation]` or `[presentations]` | A slip in one of the strict files (unknown way, missing language, bad id, year out of order …) | Fix what the message names and save again. |
| Yellow "Settings problem" | A skip date, a monthly event, a calendar or a price change could not be used as written | Do what the message says; the rest of the site updated. |
| The meeting stays on the 3rd Wednesday after changing the day | A plural (`"Thursdays"`), a short form or a word (`"second"`): not read for the committee meeting, and not reported | Write a day name and a number: `weekday: "thursday"`, `week_of_month: 2`. |
| A skip date changed nothing | It is not that month's meeting day | The run summary names the right date. |
| A monthly event vanished from `/events/` | A real mistake (no title, an unreadable day, week or start, a key used twice) | The run summary says which; fix it. |
| A monthly event still shows after `enabled: false` | There is no such switch | Delete the block. |
| La Viña's weekly open meeting disappeared | An unreadable `day`, `time` or `timezone` | Fix it; it returns after the push run of the fix. The reason is only in the log. |
| An edit to `sources: crawler`, `magazine_hub` or the shop's pages changed nothing | Read only by the full daily update | Wait for it, or start one ([section 4](#4-what-happens-after-you-save)). |
| An edit to `lavina_weekly_open:`, `sources: youtube / instagram`, `meetings:` or `content/instagram.yml` changed nothing | The push run could not tell which files the push changed, or could not compare `config/site.yml` with its earlier copy (a blue notice *Push run* says so), or the source failed in that run | Look at the run's summary (**Also run for this push**); otherwise the next full update reads it. |
| No flyer link on the La Viña weekly open card, or no letter link in the price notice | The page's pattern does not ignore accents | Write both letters: `vi[nñ]a`, `actualizaci[oó]n`. |
| Code check red after deleting the `listen:` or `watch:` lines | A test expects both ids | Put them back, or change the test. |
| Code check red after adding a milestone or a session | The counts 40 and 6 are pinned | Change the test in the same commit. |
| Code check red with "settings … that no code reads" | `tests/test_settings_used.py`: a key no code reads (misspelled, or one that does nothing) | Fix its name, or delete it; Website update published the rest meanwhile. |
| Code check red at "Build the website (as for GitHub Pages)" with `STRICT_BUILD: N build warning(s)` | A build warning: often a link written in `content/events` or `content/bulletin` that had to be hidden, an icon name that does not exist, or a page missing from the sitemap | Fix what the listed line names; Website update published the site (its summary lists the same line under **Build warnings**). |
| Tracker users still see the old mileage rate | Rates are kept in each browser | They change it in the Tracker's Settings → Mileage. |
| A dial-in number is missing on `/accessibility/#phone`, and Code check is red | Not a U.S. number | Only U.S. numbers are shown; write each one as `+1` and 10 digits. |
| "Ask the chair for the phone passcode" | `committee: phone_passcode` is empty and the passcode has letters | Paste the digits from the host's Zoom invitation. |
| The digest page and the e-mail list different numbers of items | A decimal in `digest:` | Use whole numbers. |
| A `booth:` setting changed nothing | A value the build cannot read (a language other than `en`, `es`, `both`, `alternate`; `sound` not true or false; an event name over 80 characters or not a text; a limit that is not a number), or a booth that keeps its own change of that setting | The build log's `[booth]` lines and the player's Settings → Slides name the value; on the booth, Settings → Share & reset → **Reset the settings**. |
| A page still shows the old link after changing it | That page does not use the key, or it is a Spanish page that shows the link's `_es` twin ([3.11](#311-links--official-links-used-across-the-site)) | Change the twin too; otherwise a template change is needed ([section 6](#6-going-further-change-the-code)). |
| Code check red after adding a key to `links:` | `tests/test_site_links.py`: no page uses the new key yet | Use it in a template in the same commit, or leave it out. |
| The run is green but the page looks old | The browser's or GitHub Pages' cache | Wait about 10 minutes and reload. |

---

## 8. Good practice and AA principles

- **Everything here is public**: the settings files, the data and their history. Never put a password, a
  key or private information in a file. The only e-mail addresses are service addresses
  (grapevine@neta65.org and the official @aagrapevine.org and @aa.org ones), never a member's personal
  address.
- **Anonymity**: no full names in captions (`content/instagram.yml`), the history or the summaries, and no
  photo where a member's face can be recognized. A trusted servant is a position ("Grapevine / La Viña
  Chair"), not a person.
- **Attraction rather than promotion**: say what an event or a price change is, calmly; never "buy now
  before prices go up".
- **Write both languages yourself** when you can (`title_es`, `summary_es`, `tr`, the `{en, es}` pairs).
  A machine translation is shown marked as such.
- **One change per commit**, with a clear message, then check the run: a small commit is easy to undo.
- **Keep ids once published**: a monthly event's `key`, an orientation session's `id`, a Tracker `id`, a
  presentation slide's `id`. Calendars, links and people's saved data depend on them.
- Do not change `site: timezone`, and never paste Zoom's `pwd=` token as the passcode.

---

## 9. See also

- [How-to guide index](README.md)
- [Drive panel folder](drive-panel-folder.md) · [File types](file-types.md) ·
  [Flyers and events](flyers-and-events.md) · [Bulletin](bulletin.md) ·
  [Photos, slides and reports](photos-slides-reports.md) · [Booth display](booth.md)
- [Presentations](presentations.md) · [Translations](translations.md) ·
  [E-mail and alerts](email-and-alerts.md) · [Automatic sources](automatic-sources.md)
- [Pages and code](pages-and-code.md) · [Automation and troubleshooting](automation-and-troubleshooting.md)
- The files: [config/site.yml](../config/site.yml) · [config/carry.yml](../config/carry.yml) ·
  [config/expenses.yml](../config/expenses.yml) · [config/history.yml](../config/history.yml) ·
  [config/orientation.yml](../config/orientation.yml) ·
  [config/presentations/README.md](../config/presentations/README.md) ·
  [content/instagram.yml](../content/instagram.yml)
- The code: [src/_data/site.js](../src/_data/site.js) · [src/_data/meeting.js](../src/_data/meeting.js) ·
  [scripts/sync/common.py](../scripts/sync/common.py) · [scripts/sync/meeting.py](../scripts/sync/meeting.py) ·
  [scripts/sync/build_data.py](../scripts/sync/build_data.py) ·
  [scripts/sync/price_changes.py](../scripts/sync/price_changes.py) ·
  [scripts/sync/weekly_open.py](../scripts/sync/weekly_open.py) ·
  [eleventy/filters/access.js](../eleventy/filters/access.js)
- [README §3, "Changing settings"](../README.md) · [docs/OPERATIONS.md](../docs/OPERATIONS.md)
