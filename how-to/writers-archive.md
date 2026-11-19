# The Texas writers archive: the magazines' archive files

Part of the [how-to guide](README.md). This page is for whoever keeps the two **archive files** in the repository
folder [`content/archive/`](../content/archive/): the exports of the Grapevine and La Viña online archives that
the site turns into **"Texas writers through the years"**, the archive at the bottom of *Published writers*
(`/published/#archive`). It covers the files and their names, the columns that matter, how to replace a file,
what happens next and when, how a writer is placed in Area 65, where the archive shows, the safety checks, and
what to change in the code.

> **Addresses in this guide are written short.** `/published/` means
> `https://neta65.github.io/aagrapevine/published/`, and `/es/published/` is the same page in Spanish.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start: put a new export on the website](#2-quick-start-put-a-new-export-on-the-website)
3. [The two files and their names](#3-the-two-files-and-their-names)
4. [The columns that matter](#4-the-columns-that-matter)
5. [Replace a file, step by step](#5-replace-a-file-step-by-step)
6. [What happens next (which run, how long)](#6-what-happens-next-which-run-how-long)
7. [How Area 65 is decided](#7-how-area-65-is-decided)
8. [How the daily capture keeps the list growing](#8-how-the-daily-capture-keeps-the-list-growing)
9. [Where it shows on the website](#9-where-it-shows-on-the-website)
10. [The safety checks, and what to do](#10-the-safety-checks-and-what-to-do)
11. [Translations of titles and subtitles](#11-translations-of-titles-and-subtitles)
12. [Going further: where to change the code](#12-going-further-where-to-change-the-code)
13. [Troubleshooting](#13-troubleshooting)
14. [Good practice and AA principles](#14-good-practice-and-aa-principles)
15. [See also](#15-see-also)

---

## 1. What this is

Below the recent stories, `/published/` lists **every story by a writer from Texas** in the online archives of
Grapevine (since 1944) and La Viña (since 1996), Area 65 first. On 4 October 2026 that was **1,261 stories, 376 of
them by Area 65 writers**.

The list comes from two files exported from the magazines' online archives, one per magazine:

| File (4 October 2026) | Magazine | Rows | Rows by Texas writers |
|---|---|---:|---:|
| `content/archive/aagrapevine_archive_2026-10-04.csv` | Grapevine | 35,942 | 819 |
| `content/archive/aalavina_archive_2026-10-04.csv` | La Viña | 3,607 | 444 |

Every run of **Website update** reads the folder again (a few seconds; no request to any web site), keeps the
rows by Texas writers, and joins them with every Texas story the site's daily capture of the magazine sites holds.
So stories that come out **after** the files' date join the list by themselves (section 8): a new export is only
needed now and then, for example once a year, or when the magazines correct their archives.

What the site keeps from a row: the title, the publisher's own subtitle ("Brief"), the theme, the byline exactly as
printed and the link to the magazine's page. Never a story's text, never a cover or a picture. The files are not
offered as downloads, and they never go on Google Drive.

```text
content/archive/aagrapevine_archive_YYYY-MM-DD.csv ─┐
content/archive/aalavina_archive_YYYY-MM-DD.csv ────┤  scripts/sync/writers_archive.py (every run)
                                                     ▼
                                     data/raw/writers_archive.json   (Texas rows only)
data/raw/articles.json (the daily capture) ──┐       │
                                             ▼       ▼
                              scripts/sync/build_data.py  (plan_writers_archive → build_writers_archive)
                                             │   where each writer is from: worked out again on every run
                                             ▼
                              data/site/writers_archive.json
                                             │   Eleventy (eleventy/filters/published.js → pwArchive)
                                             ▼
   /published/#archive · /es/published/#archive · /published/texas-archive.json · the home page line ·
   the site search · the /status/ row "Texas writers archive"
```

---

## 2. Quick start: put a new export on the website

Example: new exports of both archives were made on 5 November 2026.

1. **Name them with the day in the name:** `aagrapevine_archive_2026-11-05.csv` and
   `aalavina_archive_2026-11-05.csv` (section 3).
2. **Put them in `content/archive/`** and **delete the two older files** (`…_2026-10-04.csv`).
3. **Commit and push.** In GitHub Desktop: *Commit to main*, then *Push origin* (section 5.1). Or upload them on
   github.com with *Add file → Upload files* (section 5.2).
4. **Wait about 3 minutes.** The push starts a quick *Website update* run that reads the new files, rebuilds the
   site data and publishes the site. GitHub Pages may show the old page for up to about 10 more minutes. (Longer
   when the files bring many stories that are new to the site: their titles are translated first, section 6.)
5. **Check the run summary** (*Actions → Website update →* the run with your commit message): the **Writers
   archive** lines say `New archive file used: aagrapevine_archive_2026-11-05.csv (… rows, … Texas writers)` for each
   new file. A line starting **CSV file to fix** means a file was not used (section 10).
6. **Check the page:** `/published/#archive` and `/es/published/#archive`.

Nothing else needs changing: no setting names the files. The newest file of each magazine is found by the date in
its name.

---

## 3. The two files and their names

### 3.1 The naming rule

```text
aagrapevine_archive_2026-11-05.csv      Grapevine, exported on 5 November 2026
└────┬────┘ └──┬──┘ └───┬────┘
  magazine  archive  the day

aalavina_archive_2026-11-05.csv         La Viña, exported on 5 November 2026
```

A name is read in three parts (`NAME_RE` and `NAME_DATES` in
[`scripts/sync/writers_archive.py`](../scripts/sync/writers_archive.py)):

1. **The magazine**, at the start of the name, any case: `aagrapevine`, `grapevine` or `gv` for Grapevine;
   `aalavina`, `lavina`, `la_vina`, `La Viña` or `lv` for La Viña. The `aa` is optional, and a space, `_`, `.` or
   `-` may stand between the words.
2. **`archive`** (or `archives`).
3. **The day the export was made**, anywhere after `archive`. Best: `2026-11-05`. Also understood: `2026_11_5`,
   `2026.11.05`, `2026 11 05`, `20261105`, `202611051530` (a time after the day is ignored), and the U.S. order
   with the **month first**: `11-05-2026`, `11.05.2026`. The day must exist (`2026-13-40` counts as no date).

The name ends in `.csv`, in any case (`.CSV` works). Git keeps no file times, so the date in the name is the only
way the site can tell a newer file from an older one.

Examples, each checked with the module's own `parse_name`:

| File name | Read as |
|---|---|
| `aagrapevine_archive_2026-11-05.csv` | Grapevine, 5 November 2026 (the recommended form) |
| `aalavina_archive_2026-11-05.csv` | La Viña, 5 November 2026 |
| `AA Grapevine Archive 11-05-2026.csv` | Grapevine, 5 November 2026 (U.S. order) |
| `grapevine-archives-20261105.csv` | Grapevine, 5 November 2026 |
| `gv_archive_202611051530.csv` | Grapevine, 5 November 2026 (the time 15:30 is ignored) |
| `La Viña archive 2026_11_5.csv` | La Viña, 5 November 2026 |
| `aagrapevine_archive_2026-11-05.CSV` | Grapevine, 5 November 2026 |
| `aagrapevine_archive_5-11-2026.csv` | Grapevine, **11 May 2026**: a date with the year last is read month first |
| `aagrapevine_archive_2026-11-05 (1).csv` | Grapevine, 5 November 2026, a browser's second download ("copy 1") |
| `aagrapevine_archive_2026-11-05_v2.csv` | Grapevine, 5 November 2026, version 2 |
| `aagrapevine_archive.csv` | Grapevine, **no date**: it loses to every dated file, and the run summary asks for the day |
| `aagrapevine_archive_2026-13-40.csv` | Grapevine, no date (there is no 40th of a 13th month) |
| `Copy of aagrapevine_archive_2026-11-05.csv` | **not an archive file**: the name must start with the magazine |
| `archive_2026-11-05.csv` | not an archive file: no magazine in the name |
| `gv_export_2026-11-05.csv` | not an archive file: no `archive` in the name |

> **Note:** write the day as `2026-11-05`. A day-first date such as `05-11-2026` (5 November in most of the world)
> is read as **May 11**, and a file named that way can lose to an older one.

### 3.2 Which file is used

For each magazine the site takes **the newest file**: the latest date in the name; on the same date, the higher
`_v2` / `v3`; then the higher browser copy number `(1)`, `(2)`; then the name. A file without a date loses to every
dated one (`newest_key` in `writers_archive.py`).

The links inside then **confirm the magazine**: when most of a file's links are on aagrapevine.org it is the
Grapevine file, on aalavina.org the La Viña file. When the name says one magazine and the links the other, the
links win and the run summary says so. When that other magazine already has its file, this one is not used at all:
one warning says so, says what each magazine uses, and asks for a new export under this name (section 10).

The newest file must also pass the safety checks (section 10). One that fails is not used: its magazine keeps the
rows it had, and the file they came from, if it is still in the folder, "stays in use until" the new one is fixed.

A real test: a folder holding these nine files (checked with the module's own `import_archive`):

| In `content/archive/` | What the run does |
|---|---|
| `aagrapevine_archive_2026-11-05 (1).csv` | **used** for Grapevine: the copy number breaks the tie with the plain name of the same day |
| `aagrapevine_archive_2026-11-05.csv` | not used; warning `older archive file still in content/archive (it is not used and may be deleted): aagrapevine_archive_2026-11-05.csv` |
| `aagrapevine_archive_2026-10-04.csv` | not used; the same warning |
| `aalavina_archive_2026-11-05.csv` | **used** for La Viña |
| `aalavina_archive.csv` | not used (no date); the "older archive file" warning |
| `Copy of aalavina_archive_2026-11-05.csv` | not used; warning `a .csv file in content/archive whose name is not an archive file's (it is not used): Copy of aalavina_archive_2026-11-05.csv — name it like aagrapevine_archive_2026-11-05.csv or aalavina_archive_2026-11-05.csv` |
| `README.md` | ignored, silently |
| `notes.xlsx` | ignored, silently |
| `aagrapevine_archive_2026-11-05.xlsx` | not read; warning `aagrapevine_archive_2026-11-05.xlsx in content/archive is not read — only .csv files are (in Excel: File → Save As → “CSV UTF-8 (Comma delimited)”, same name)` |

The warnings come back in **every** run until the extra files are deleted. They never stop anything.

### 3.3 What is ignored

- Anything whose name does not end in `.csv`: the folder's `README.md`, a spreadsheet, a text file. No warning,
  except for a file **named like an archive file** but saved in another format (`aagrapevine_archive_2026-11-05.xlsx`,
  `….csv.xlsx`, `….numbers`): it is not read either, but the run summary names it (the warning above). Save the
  export again as **CSV UTF-8**, with the same name, and delete the other file.
- Names that start with `.` or `~$` (hidden files, and the lock file Excel leaves next to an open file). No warning.
- Sub-folders: only the top level of `content/archive/` is read.
- Every archive file but the one in use for each magazine (a warning for each, as above). The file in use is the
  newest, unless the newest failed a check: then the file used before stays in use, and its warning says "it stays
  in use until … is fixed" (section 10).

**One file per magazine.** A magazine with no file at all **keeps the rows of its last file** (they are saved in
`data/raw/writers_archive.json`), and the run summary warns:
`no La Viña archive file in content/archive — the rows of the last one are kept (443 Texas writers)` (444 rows by
Texas writers on 4 October 2026, one of them a story listed twice, kept once).
So you can replace one magazine's file without touching the other's.

The folder itself can be moved with `writers_archive.folder` in `config/site.yml` (a folder of the repository).
It is not set today, and there is no reason to set it.

---

## 4. The columns that matter

Both exports have the same 14 columns, in this order: **Link**, **Title**, **Has Audio Version (audio icon)**,
**Month**, **Year**, **Theme**, **Written By**, **City**, **State**, **Brief**, **Audio Only (no article text)**,
**Texas Author?**, **Location (as published)**, **Notes**.

A column is found by **how its header starts**, in any case and with extra spaces ignored (`COLUMNS` and
`map_header` in `writers_archive.py`): `Has Audio Version (audio icon)` is found as "has audio", a header renamed
`Texas author` still works, `Author` stands for `Written By` and `URL` for `Link`. The order of the columns does not
matter.

**Seven columns are needed.** A file without one of them is not used at all (section 10): Link, Title, Month,
Year, Written By, Location (as published), Texas Author?.

| Column | Needed | What the site does with it | Example (real rows, 4 October 2026) |
|---|---|---|---|
| **Link** | yes | The story's page. Only addresses on aagrapevine.org or aalavina.org count: other rows are left out and counted in a warning. `http://` becomes `https://`. The address is also the key that matches the same story in the daily capture (capitals and a trailing `/` ignored). | `https://www.aagrapevine.org/magazine/2026/oct/halloween-remember` |
| **Title** | yes | The row's title (when the daily capture has the story too, the capture's title is shown). An empty title is made from the end of the address. | `A Halloween to Remember` |
| **Month**, **Year** | yes | The issue. Grapevine prints a month in any case (`October`, `june`); La Viña a pair (`Septiembre / Octubre`, filed under its first month). Never taken from the address. A Year without a Month is listed in its decade with no issue name; no Year at all → the group **Date not shown**. | `October` · `2026` → "October 2026"; `Julio / Agosto` · `2026` → "July–August 2026" on the English page |
| **Written By** | yes | The byline **exactly as printed**. The one repair: initials the export wrote in title case ("H.t.b.") become "H.T.B.". "Anonymous" / "Anónimo" (or no name) shows as *Anonymous* (*Anónimo* on the Spanish page). Several writers separated by `;` (a letters column) are paired with the places by position. | `Aaron M.` · `Irene H-P.; Stacy C.` |
| **Location (as published)** | yes | The place as the magazine printed it, typos included. Read for Area 65 together with City and State (section 7). | `Round Rock, Texas` · `Forth Worth, Texas` |
| **Texas Author?** | yes | `Yes` keeps the row even when its place cannot be read as Texas. `No` and `Unknown (no location in byline)` rows are kept only when the place is read as Texas. | `Yes` (818 Grapevine rows) · `No` · `Unknown (no location in byline)` |
| **City**, **State** | no | The export's own reading of the place, which often has the spelling right ("Fort Worth"). `(city not given)` means no city. With several writers: one per writer, `;`-separated; a missing state is the last one given. | `Round Rock` · `Texas` |
| **Brief** | no | The publisher's subtitle, shown under the row (two lines on the page; at most 300 characters, cut on a word with "…") and machine-translated. | `A sober granddad survives a boozy holiday block party …` |
| **Theme** | no | Shown in the row's small print. "Grapevine Online Exclusives" is not shown as a theme: the row gets the **Online exclusive** mark instead. | `Loneliness` |
| **Has Audio Version (audio icon)** | no | `Yes` → the mark **Audio version** with a headphones icon. | `Yes` |
| **Audio Only (no article text)** | no | Kept in `data/raw/writers_archive.json`; not shown. | `No` |
| **Notes** | no | **Never shown.** Read only for marks: "Web exclusive…" → **Online exclusive**; "…multiple contributors…" → **Letter or short piece**. "Names taken from signatures" and "Group/institution: …" are kept in `data/raw` only. | `Web exclusive: the site shows no date, so month and year are taken from the URL` |

A row is also marked **Letter or short piece** when its title is one of the magazines' columns of letters and short
pieces: "Dear Grapevine", "PO Box 1980", "At Wit's End", "Ham on Wry", "Short Takes", "Mail Call…", "From the Grass
Roots", "Carrying the Message", "Your Move", "Sidebar", "Distilled Spirits", "The View from Here…", "Grass Roots…",
"Dear Editors" (`COLUMN_TITLE_RE`).

**A real letters column** (Grapevine, September 2022):

| Column | Value |
|---|---|
| Title | `Dear Grapevine` |
| Written By | `Irene H-P.; Stacy C.` |
| Location (as published) | `San Antonio, Texas; Horseshoe Bay, Texas` |
| City / State | `San Antonio; Horseshoe Bay` / `Texas; Texas` |
| Has Audio Version | `Yes` |
| Notes | `Reader-letters column with multiple contributors; only the Texas contributor(s) are listed. …` |

On the page this is one row: **Dear Grapevine**, the byline "Irene H-P. (San Antonio) · Stacy C. (Horseshoe Bay)",
and the small print "Grapevine · September 2022 · Young & Sober · Audio version · Letter or short piece".

**Every text is tidied** before it is used (`clean_field`): HTML entities (`&amp;` → `&`), the export's own line
breaks (`<lb`, shown as " — "), stray tags, text that was saved twice as UTF-8 ("MazatlÃ¡n" → "Mazatlán"), accents
written in two pieces, the ligatures "ﬁ" / "ﬂ" and soft hyphens. A story the archive lists twice (same magazine,
issue, title and writers; the address differs only by an ending such as `-0`) is kept once.

**Saving the file.** Put the export in as it was made. If you open it in Excel to look at it, close it without
saving, or save it as **CSV UTF-8 (Comma delimited)**. A file saved in another encoding is still read (as
Windows-1252), with a warning. A UTF-8 file with a few characters that are not UTF-8 stays UTF-8: those characters
show as "�", and a warning names the line of the first one. The mark Excel puts at the start of a "CSV UTF-8" file
(a byte-order mark) is dropped before either reading, so the first column is always found. A file saved with
semicolons between the columns (Excel does that when the computer's region writes decimals with a comma) loses its
columns and is not used.

---

## 5. Replace a file, step by step

You need a GitHub login with write access to [NETA65/aagrapevine](https://github.com/NETA65/aagrapevine) (the
MKP715 login is enough). Replace one magazine or both: a magazine whose file you leave alone keeps it.

### 5.1 With GitHub Desktop (on the owner's PC)

1. Open **GitHub Desktop** and choose the repository **aagrapevine** (*Current repository*).
2. Click **Fetch origin**, then **Pull origin** when it appears. The robot adds a data commit after almost every
   run, so your copy is usually behind; GitHub Desktop refuses a push until you have pulled.
3. **Repository → Show in Explorer**, then open the folder `content\archive`.
4. Copy the new export in, named as in section 3, for example `aagrapevine_archive_2026-11-05.csv`.
5. Delete the older file of the same magazine, `aagrapevine_archive_2026-10-04.csv`. (Keeping it breaks nothing,
   but every run then repeats the warning "older archive file still in content/archive (it is not used and may be
   deleted)". The old file stays in the repository's history anyway.)
6. Back in GitHub Desktop, **Changes** shows one file added and one deleted. Write a summary such as
   `archive: Grapevine export of 2026-11-05`, then click **Commit to main**.
7. Click **Push origin**.

Line endings: Windows saves the file with CRLF line ends and git stores it with LF (`.gitattributes`). The site
compares files by a fingerprint of their text with the line ends made equal (`content_hash`), so the same export is
the same file on your PC, on GitHub and in the run.

### 5.2 On github.com: Add file → Upload files

1. Open <https://github.com/NETA65/aagrapevine/tree/main/content/archive>.
2. **Add file → Upload files**, drag the new export onto the page (or *choose your files*), write a message such as
   `archive: Grapevine export of 2026-11-05`, keep **Commit directly to the main branch**, and click **Commit
   changes**.
3. Click the older file's name, then **⋯** (top right) → **Delete file** → **Commit changes**.

Each commit starts its own quick run: the first one takes the new file in, the second only ends the "older archive
file" warning. GitHub's browser upload takes files up to 25 MB; the Grapevine export is about 7 MB.

### 5.3 With Git on a PC (optional)

```powershell
git pull                                                          # the robot's newest data commits
Copy-Item "$HOME\Downloads\aagrapevine_archive_2026-11-05.csv" content\archive\
git rm content/archive/aagrapevine_archive_2026-10-04.csv
git add content/archive/aagrapevine_archive_2026-11-05.csv
git commit -m "archive: Grapevine export of 2026-11-05"
git push
```

**Try it first, without writing anything** (a PC with the project set up, as in
[Automation and troubleshooting §11](automation-and-troubleshooting.md#11-run-the-sync-the-build-and-the-tests-on-a-pc)):

```powershell
python -m scripts.sync.writers_archive --dry-run
```

It prints what the next run would save: `ok`, the `error` of a file that would not be used, the `stats` (the files,
the row counts, the "New archive file used" notes and every warning), each magazine's file and the first three rows.
Nothing is written.

---

## 6. What happens next (which run, how long)

| You do this | What starts by itself | On the website after about |
|---|---|---|
| Push a new or changed file in `content/archive/` | a **quick** *Website update* run (the push's own run) and a *Code check* | about 3 minutes, plus up to about 10 minutes of GitHub Pages caching |
| Nothing | every later run reads the folder again: the **morning refresh**, the **midday** and **evening refreshes**, the **nightly full update** and every push | — (the files' rows stay as they are; newly captured Texas stories still join, section 8) |
| Edit `content/archive/README.md` | only a *Code check* | nothing on the website |
| Change `spotlight.neta65_counties` in `config/site.yml` | the push's quick run | about 3 minutes: every writer's place is read again (section 7) |

The push's run is a quick run (Drive, the bulletin, the podcasts, the writers archive files, the daily quote, then
the site data and the build; the archive files are the committee's, not code, so it does not run the tests again —
the *Code check* tests the files). Quick runs took about 2 minutes in early October 2026; since then the build also
makes the monthly posters' share pictures, about a minute more; reading both archive files adds a few seconds. The
new stories' titles and subtitles are translated within the run's time box, the rest later (section 11). An export
that adds a few stories keeps the run at about 3 minutes; a file that brings many stories
new to the site — above all the very first import, more than 1,200 titles and their subtitles — makes the run translate
longer (up to its 40-minute translation box) before it publishes, so the archive appears later. Only one
*Website update* run works at a time: when another is going (in the morning, the full update), yours waits for it.

In the Actions list a push's run carries your commit message as its title ("archive: Grapevine export of
2026-11-05"). The other runs are named by their kind: "Nightly full update (GitHub schedule)", "Midday refresh (GitHub
schedule)", "Evening refresh (GitHub schedule)", "Morning refresh: new day and daily quote" …
([Automation and troubleshooting §6.1](automation-and-troubleshooting.md#61-the-list-of-runs)).

### 6.1 The run summary's "Writers archive" lines

Every *Website update* run summary has a **Writers archive** block (*Actions → Website update →* a run →
*Summary*). A run that takes in the two files of 4 October 2026 (worked out with the real code and files):

```text
**Writers archive** (content/archive → /published/#archive): 1,261 stories by Texas writers on the site, 376 of them by Area 65 writers
- Grapevine: aagrapevine_archive_2026-10-04.csv — 35,942 rows, 819 by Texas writers
- La Viña: aalavina_archive_2026-10-04.csv — 3,607 rows, 444 by Texas writers
- New archive file used: aagrapevine_archive_2026-10-04.csv (35,942 rows, 819 Texas writers)
- New archive file used: aalavina_archive_2026-10-04.csv (3,607 rows, 444 Texas writers)
```

| Line | When | Meaning |
|---|---|---|
| the heading | every run | the stories on the site now: the files' Texas rows plus the captured stories (section 8), and how many are by Area 65 writers |
| `Grapevine: …` / `La Viña: …` | every run | the file in use for each magazine, its rows and its rows by Texas writers |
| `New archive file used: …` | only in the run that took the file in (also when the other magazine's new file was turned down; a later run never repeats it) | also a blue ℹ annotation titled *Writers archive* |
| **CSV file to fix** (the older rows stay on the site): … | a file was not used | what is wrong with it (section 10) |
| any other line | a warning | an older copy that may be deleted, the file used before that stays in use until a newer one is fixed, a name the site does not understand, an archive file not saved as `.csv`, a name without a date, a name that says the other magazine, rows without a magazine link, a magazine without a file, a file not saved as UTF-8 or with characters that are not UTF-8, a `min_rows_ratio` that is not a number |

The **Content sources** table above it has a row **Texas writers archive (content/archive)**: OK, or **PROBLEM**
when a file was not used. Its "New in 7 days" counts the archive rows whose address first came in during the last
7 days: each row keeps `first_seen`, the time of the run that first took its address in. So in the week after the
first import every row counts (on `/status/` too, in the archive's row and in "Found in the last 7 days"); later,
the stories a newer file adds. The same files give the same rows, run after run. Stories that only the daily
capture adds (section 8) are not counted there.

### 6.2 The data commit

The robot commits what the run changed, as usual. When the run took a new file in (also when the other magazine's
new file was turned down), the message names it before the date; a later run, or a run that stopped before reading
the folder, never repeats it (the step *Commit refreshed data* of
[`update.yml`](../.github/workflows/update.yml) checks that the file's `imported_at` is from this run):

```text
chore(data): content sync after settings/content change + writers archive 2026-11-05 [skip ci]
```

Any kind of run that takes a new file in says so the same way ("chore(data): evening refresh + writers archive …").
The commit holds `data/raw/writers_archive.json` (the Texas rows and the files in use), `data/site/writers_archive.json`
(what the page reads), `data/site/status.json`, and usually `data/translations/cache.json`. **The robot never commits
`content/`**: the archive files are yours.

### 6.3 The Code check

The push also starts a *Code check*. One of its tests reads the real files: `RealFiles.test_the_headline_numbers` in
[`tests/test_writers_archive.py`](../tests/test_writers_archive.py). It reads the folder as a first import would,
with the whole Area 65 county list pinned in the tests (`AREA65_TEST_COUNTIES` in `tests/test_spotlight.py`), so an
edit of `spotlight.neta65_counties` never turns it red. The folder must give no **CSV file to fix**, and every file
in use some rows by Texas writers and a first year not before the magazine began (1944, 1996). While the files in use are
the two of 4 October 2026 (the test knows them by name and fingerprint) it also expects their exact numbers: 819
Grapevine and 444 La Viña rows by Texas writers, 1,261 stories, 376 by Area 65 writers, first years 1944 and 1996.
A newer file only has to make sense, so a good new export keeps the Code check green; nothing in the test needs
changing.

---

## 7. How Area 65 is decided

**The Area 65 counties** are the list `spotlight.neta65_counties` in [`config/site.yml`](../config/site.yml) (75
county names): the same list that sorts the recent stories on `/published/` and the home page, and the Meetings
page's "Our Area" group ([Settings §3.10](settings.md#310-spotlight--published-writers)).

**Each writer's place is read twice**, with the same rules as the magazines' bylines
([`scripts/sync/geo.py`](../scripts/sync/geo.py) → `classify_location`; a city is matched to its counties with
`data/geo/texas_places.json`, the U.S. Census table of every Texas city, town and village):

1. the place as printed: **Location (as published)**;
2. the export's own **City** and **State**.

The better reading counts (`geo.classify_writer` → `best_of`): Area 65 before the rest of Texas, the rest of Texas
before anywhere else; on a tie, the reading that found the place's counties, then one with a principal county. A
place that spans several counties counts as Area 65 when **any** of them is on the list. A story's place is its best
writer's, so a letters column with one writer from Tyler counts as Area 65.

**Worked out again on every run.** Where a writer is from is not stored with the rows (`data/raw/writers_archive.json`
keeps the places as printed); `build_data` reads every place again in each run. Add a county to the list, push, and
the archive follows a few minutes later.

**Help for the archive's old bylines** (in `geo.py`, used only once the state is known to be Texas):

- `TYPO_ALIASES`: misspellings printed in bylines, read as the place they mean and shown spelt right: "Forth Worth"
  → Fort Worth, "Nacagdoches" → Nacogdoches, "Irvin" → Irving, "Grand Prarie" → Grand Prairie, "Huntsvitte" and
  "Hunstville" → Huntsville, "Beaumount" → Beaumont, "Bastrom" → Bastrop, "Bayton" → Baytown, "Braunfels" → New
  Braunfels, "Pfugerville" → Pflugerville, "Leander T" → Leander. A name that is itself a real place is never
  "corrected".
- The state's own typo: "exas" counts as Texas ("Waco, exas").
- `EXTRA_PLACES`: Texas places the Census table has no row for: Kingwood (Harris County), Del Valle and De Valle
  (Travis), Tennessee Colony (Anderson), New Caney (Montgomery), Port Bolivar (Galveston).

**Regions instead of a town** (`TEXAS_REGIONS` in `geo.py`, for every byline on the site): "North Texas",
"Northeast Texas", "North Central Texas", "DFW" / "Metroplex" and "Mid-Cities" count as Area 65; "East", "West",
"South", "Central", "Southeast", "Southwest" and "Northwest Texas", "Hill Country", "Panhandle" and "Rio Grande
Valley" as the rest of Texas. The compass regions are also read when written as adjectives: "Southeastern Texas" is
the region Southeast Texas (a real 2001 byline: "Panel 31 delegate, Southeastern Texas"), never a made-up town
"Southeastern". Other compass words where the town should be ("Deep East Texas", "Far West Texas") are shown as
printed, with no town and no county.

Examples, checked with `geo.classify_writer` and today's county list:

| Location (as published) | City / State | Read as | County | The byline shows |
|---|---|---|---|---|
| `Forth Worth, Texas` | `Fort Worth` / `Texas` | Area 65 | Tarrant | Fort Worth, Texas · Tarrant County |
| `Waco, exas` | `Waco` / `Texas` | Area 65 | McLennan | Waco, Texas · McLennan County |
| `Irvin, Texas` | (empty) | Area 65 | Dallas | Irving, Texas · Dallas County |
| `Tennessee Colony, Texas` | `Tennessee Colony` / `Texas` | Area 65 | Anderson | Tennessee Colony, Texas · Anderson County |
| (empty) | `Tyler` / `Texas` | Area 65 | Smith | Tyler, Texas · Smith County |
| `Houston County, Texas` | (empty) | Area 65 | Houston | Houston County, Texas (the county is already named) |
| `Round Rock, Texas` | `Round Rock` / `Texas` | rest of Texas | Williamson | Round Rock, Texas · Williamson County |
| `Kingwood, Texas` | `Kingwood` / `Texas` | rest of Texas | Harris | Kingwood, Texas · Harris County |
| `Hunstville, Texas` | (empty) | rest of Texas | Walker | Huntsville, Texas · Walker County |
| `Southeastern Texas` | (empty) / `Texas` | rest of Texas | — | Southeast Texas (a region, not a town) |
| `Texas` | `(city not given)` / `Texas` | rest of Texas | — | Texas |

A row that **Texas Author?** kept although no reading finds a Texas place is listed with the rest of Texas, without a
county. On the Spanish page the county reads "Condado de Tarrant".

---

## 8. How the daily capture keeps the list growing

The site reads the magazines' new issues by itself (the magazine stories source,
[`scripts/sync/articles.py`](../scripts/sync/articles.py) → `data/raw/articles.json`;
[Automatic sources §3.1](automatic-sources.md#31-magazine-stories-and-issues)). That file keeps **every story it ever
found**: nothing is removed by age. `build_data` adds to the archive every captured story that has a byline, is still
online and whose writer is from Texas, **of any age**, matched with the files' rows by the address:

| A story is… | `from` | What the archive shows |
|---|---|---|
| in the files only | `csv` | the file's row |
| in both | `both` | the capture's title (and its translation), byline and subtitle; the file fills in the theme, the audio and letter marks, and the issue when the capture lacks them. A letters column keeps the file's writers |
| in the capture only | `capture` | a story that came out after the files' date: its issue and theme from the capture, no audio mark |

On 4 October 2026, with files exported that same day: 1,245 stories from the files only, 16 in both, none from the
capture only. `data/site/status.json` → `writers_archive` keeps these counts (`csv_only`, `both`, `capture_only`).

So **a new export is not needed every month**: each new Texas story joins the archive once the capture has it. A new
export brings what the capture cannot: corrections the magazines made to their archives, older stories the capture
never saw (it reads back about 120 days), and the audio marks.

The archive's stories never go into the *recent* lists: the 60- and 90-day cards on `/published/`, the home page's
writers, `/read/`, the monthly digest and the district report keep theirs exactly as before.

---

## 9. Where it shows on the website

| Place | English | Spanish | What it shows |
|---|---|---|---|
| The archive | `/published/#archive` | `/es/published/#archive` | **Texas writers through the years** / *Escritores de Texas a lo largo de los años*, eyebrow "Archive · since 1944", below the recent stories and above "How we find these writers" |
| The page's hero | `/published/` | `/es/published/` | a button **Texas writers since 1944** / *Autores de Texas desde 1944* → `#archive` |
| No recent story matches | | | the empty list's ways out include a button **Browse the archive** / *Explora el archivo* → `#archive` |
| "How we find these writers" (eyebrow "About this list") | | | one more line: "The archive gathers the stories by Texas writers in the online archives of Grapevine (back to 1944) and La Viña (back to 1996); stories from each new issue join it as they come out." |
| The rest of Texas | `/published/texas-archive.json` | `/es/published/texas-archive.json` | the stories by writers from outside Area 65, loaded only when a visitor chooses **All of Texas** or **Everyone**. The page asks for it as `texas-archive.json?v=` plus a fingerprint of the file: a new address whenever its stories change, so a browser never mixes an older copy's rows into a newer page |
| Home | `/` | `/es/` | one line under *Published writers*: "1,261 stories by Texas writers since 1944 — 376 from our Area" and the link **Browse the archive** (none without the archive) |
| Site search | `/search/` | `/es/search/` | a search for a town or a county the archive's writers come from (for example "Nacogdoches"; towns in the right spelling: "Fort Worth", not a printed "Forth Worth"), or for "archive" / "archivo", offers the Published writers page. Never a writer's name or a byline as printed: names, initials and bylines such as "Panel 31 delegate" would make the page a hit for everyday AA searches ("Bill W.", "delegate") |
| Status | `/status/` | `/es/status/` | the row **Texas writers archive** / *Archivo de escritores de Texas* |
| Offline | | | "Save key pages for offline" keeps `/published/` (with its Area 65 rows) and both `texas-archive.json` files |

**How the archive works on the page:**

- **Area 65 first.** The Area 65 stories are written into the page itself, grouped by decade, newest first: they show
  without JavaScript and after a visit offline. With JavaScript, the first **40** show, then **Show 40 more** and
  **Show all N stories**.
- **One filter card for the whole page.** The card above the recent stories drives the archive too:
  - *Where the writers are from*: **Area 65** (the default) → the Area 65 stories; **All of Texas** → every Texas
    story, the Area 65 ones marked with a green edge and an "Area 65" badge; **Everyone** → the same, plus the line
    "The archive lists writers from Texas only.";
  - *Magazine*: all, Grapevine or La Viña;
  - *Search*: every word must start a word of the story's search words ("dal" finds Dallas): the writers' names,
    places, cities and counties, the title in both languages, the theme, the year, the decade ("1990s") and the
    magazine; never the subtitle. A year is a whole word: "1990" finds the stories of 1990, "1990s" the whole
    decade. Apostrophes are dropped ("beginners" finds "Beginner's"). Initials are found however they are typed:
    "H.T.B." finds "H. T. B." and stays precise, and "M.B.", "M.B", "M B" and "MB" all find "M.B." (a story's
    search words hold its initials both together and one by one; the recent cards above read initials and
    apostrophes the same way).
- **Decades:** chips **All years**, **2020s** … **1940s** and **Date not shown**, each with its count.
- **Hometowns:** up to 8 Area 65 hometowns with the most stories (on 4 October 2026 among them Dallas, Fort Worth,
  Arlington, Irving, Abilene and Wichita Falls). A tap puts the town in the page's search box. On a phone both chip
  rows scroll sideways inside the card; the page itself never gets wider.
- **A row:** the title (it opens the magazine's page in a new tab); under a translated title the original one, in
  italics, after a small languages icon when the translation is a machine's (section 11); the byline: the writer's
  name as printed, the place (spelt right, section 7) and the county ("Aaron M. · Round Rock, Texas · Williamson
  County"; a letters column: "Irene H-P. (San Antonio) · Stacy C. (Horseshoe Bay)"); the small print (magazine ·
  issue · theme · **Audio version** · **Online exclusive** · **Letter or short piece**) and the subtitle, two lines
  at most (with the same icon when the title is shown untranslated and the subtitle is a machine translation).
- **Machine translations:** while a row with a machine-translated title or subtitle is on screen, one note over the
  list says so: "Titles translated automatically from Spanish — originals in italics" on the English page, "Títulos
  traducidos automáticamente del inglés — originales en cursiva" on the Spanish one.
- **Nothing matches:** "No stories in the archive match", with a line for the cause (after a search "Try another
  spelling or a nearby town."; with no search but a decade or a magazine chosen "No stories for this decade and
  magazine. Choose another decade, or both magazines.") and the ways out that apply: **Clear search**, **Show all
  years**, **Show both magazines**, **Show all of Texas**. After a click, keyboard focus stays in the archive (on the
  decade chosen).
- **Printing** shows the rows that are on screen, without the controls.

**Addresses that open a view** (the page's own keys, plus `dec` for the archive; the defaults are left out):

| Address | Opens |
|---|---|
| `/published/#archive` | the archive: Area 65 stories, all years |
| `/published/?scope=texas#archive` | every Texas story, Area 65 marked |
| `/published/?dec=1990s#archive` | Area 65 stories of the 1990s |
| `/published/?scope=texas&dec=undated#archive` | Texas stories without a date |
| `/es/published/?pub=lv&q=dallas#archive` | La Viña stories by Area 65 writers that match "dallas" (Spanish page) |

The keys: `scope` (`neta65` default, `texas`, `all`), `pub` (`gv`, `lv`), `q` (the search), `dec` (`1990s` … or
`undated`); `days` belongs to the recent stories only. The search and the magazine filter the recent cards above as
well. Back and Forward over the page's own links (`#archive`, "How we find these writers") keep the choices on
screen in the address, `dec` included.

---

## 10. The safety checks, and what to do

A new file is checked before it replaces the last one. A file that fails a check is **not used**: its magazine keeps
the rows it had, and the source shows as failed. Nothing on the website breaks. The *Code check* also goes red:
`test_the_headline_numbers` (`tests/test_writers_archive.py`) reads the same folder, and a new file with a missing
column, or one that cannot be read, fails it (the cut-off guard is the one check it cannot repeat: it has no earlier
file to compare with). *Website update* still publishes: it leaves the tests that judge the committee's own files —
this one included — to the Code check (since October 2026, `CONTENT_TESTS`,
[Automation and troubleshooting §4.8](automation-and-troubleshooting.md#48-the-tests-before-publishing)). Fix a
**CSV file to fix** the same day all the same. If the file those rows came from is still in the folder, the run summary says it "stays in use until" the
new one is fixed, never that it "may be deleted". Only a magazine's very first import (no rows and no file on record
yet) goes on to its newest older file that passes, and the error's end then says so.

| Check | It trips when | The run summary says (examples from the real code) | What to do |
|---|---|---|---|
| **Needed columns** | one of Link, Title, Month, Year, Written By, Location (as published), Texas Author? is missing | **CSV file to fix**: `aagrapevine_archive_2026-12-01.csv: the column Texas Author? is missing — the file is not used, the older rows stay` | export again with all the columns, or put the header back (a header is found by how it starts, section 4) |
| **Cut-off guard** | the new file has fewer rows than `writers_archive.min_rows_ratio` (0.8) × the rows of the file used before for that magazine | **CSV file to fix**: `aagrapevine_archive_2026-12-01.csv has 3 rows, the file used before had 17 — it looks cut off, so the older data stays. If the smaller file is right, set writers_archive.min_rows_ratio: 0 in config/site.yml for one run` | check the export (did it stop early?); if the smaller file is right, see below |
| **A file that cannot be read** | the CSV is broken | **CSV file to fix**: `… could not be read (Error: …) — the file is not used, the older rows stay` | export again |
| (how the column and unreadable-file lines end) | the magazine has no older rows yet | instead of `, the older rows stay`: `, the older aagrapevine_archive_2026-10-04.csv is used instead` (a first import: its newest older file that passes) or `, and there are no older Grapevine rows to keep` | fix the new file; nothing else |
| The file used before is still there | a newer file of the same magazine failed a check | `older archive file still in content/archive (it stays in use until aagrapevine_archive_2026-12-01.csv is fixed): aagrapevine_archive_2026-10-04.csv` | keep it, or delete it (its rows stay either way); fix the newer file |
| Not saved as UTF-8 | the file is in another encoding | `… is not saved as UTF-8 — it was read as Windows-1252 (save it as “CSV UTF-8” next time)` (the file **is** used) | check the accents on the page; save as CSV UTF-8 next time |
| A few characters are not UTF-8 | a UTF-8 file with some broken bytes | `aalavina_archive_2026-11-05.csv: 1 character(s) are not UTF-8 (the first on line 2) — they show as “�”; save it as “CSV UTF-8” again` (the file **is** used) | look at that line; export again, or save as CSV UTF-8 |
| Name and links disagree | the name says one magazine, most links the other | `aagrapevine_archive_2026-12-01.csv: the name says Grapevine but its links are La Viña's — it is used as the La Viña file` (used) | rename the file |
| … while that magazine has its file | the same, but the other magazine's own file is newer | one line: `aagrapevine_archive_2026-11-05.csv: the name says Grapevine but its links are La Viña's, and La Viña already has its file (aalavina_archive_2026-12-01.csv) — this file is not used, and Grapevine uses aagrapevine_archive_2026-10-04.csv; export Grapevine again and save it under this name` (not used) | export the magazine the name says, save it under that name |
| No date in the name | | `aagrapevine_archive.csv has no date in its name — add the day it was exported, like aagrapevine_archive_2026-11-05.csv, so a newer file can be told from it` (used when it is the only one) | rename it |
| Older copies | more than one file of a magazine | `older archive file still in content/archive (it is not used and may be deleted): …` | delete the older files |
| A name the site does not understand | a `.csv` file not named like an archive file | `a .csv file in content/archive whose name is not an archive file's (it is not used): … — name it like …` | rename it, or delete it |
| Not a `.csv` file | a file named like an archive file in another format (`.xlsx`, `.numbers` …) | `aagrapevine_archive_2026-11-05.xlsx in content/archive is not read — only .csv files are (in Excel: File → Save As → “CSV UTF-8 (Comma delimited)”, same name)` | save it as CSV UTF-8 with the same name; delete the other file |
| No file for a magazine | | `no La Viña archive file in content/archive — the rows of the last one are kept (443 Texas writers)` | nothing, unless the file was deleted by mistake |
| Rows without a magazine link | a row's Link is empty or on another site | `aagrapevine_archive_2026-11-05.csv: 12 row(s) without a Grapevine or La Viña link were left out` | nothing; look at the export if the number is large |
| A setting that is not a number | `min_rows_ratio: "eighty"` | `writers_archive.min_rows_ratio “eighty” in config/site.yml is not a number like 0.8 — 0.8 is used` | write a number |

**When a file is not used:**

- the **Writers archive** block has a **CSV file to fix** line, and the *Content sources* table shows **PROBLEM** for
  "Texas writers archive (content/archive)", with a yellow ⚠ annotation;
- the *Status* page shows the row **Texas writers archive** as **Failed** (*Falló*), with the error under *Technical
  details*; visitors only read the calm "nothing was lost" text;
- the other magazine's file is still used when it passed;
- after **7 days** without a good run the issue **"A content source has stopped updating"** opens, with this advice:
  "check the newest file in content/archive: it must keep the archive's columns, and a file much smaller than the one
  used before is not used (the run summary's "CSV file to fix" line says which). The archive already on the site
  stays meanwhile." It closes by itself once a file is used again
  ([E-mail and alerts §3.17](email-and-alerts.md#317-the-three-automatic-issues)).

### 10.1 The cut-off guard and `min_rows_ratio`

```yaml
# config/site.yml
writers_archive:
  min_rows_ratio: 0.8   # a new file with fewer rows than 80 % of the file used before is not used (0 = always use the newest)
```

It compares **all** the rows of the new file (Texas or not) with the rows of the file used before for the same
magazine: an export that stopped halfway would otherwise drop hundreds of writers without a word. Values: `0.8`
(the default, also when the line is missing), `0` (off: the newest file is always used), anything between 0 and 1.
A number above 1 counts as 1, below 0 as 0; a value that is not a number counts as 0.8, with a warning.

| The file used before had | The new file has | With 0.8 |
|---|---:|---|
| 35,942 rows | 36,120 | used |
| 35,942 rows | 30,000 | used (more than 28,753.6) |
| 35,942 rows | 20,000 | **not used**: "it looks cut off" |

**To accept a smaller file on purpose** (the magazine really removed many entries):

1. In `config/site.yml`, set `min_rows_ratio: 0`, and commit. The file can be in the same commit: the push's run
   reads the new setting and the new file together.
2. Check the run summary: `New archive file used: …`.
3. Set `min_rows_ratio: 0.8` again and commit. From then on new files are compared with the smaller one.

---

## 11. Translations of titles and subtitles

Archive titles and subtitles are translated like every title on the site: Grapevine's English titles for
`/es/published/`, La Viña's Spanish titles for `/published/`, with the free translation models of the update
([Translations](translations.md)). Three things are different:

- **They come last.** Each run translates for at most 40 minutes (5 in the morning refresh), the newest and most
  visible texts first; the archive's titles come after every other text (newest issue first), then its subtitles
  (`WA_TITLE_TIER`, `WA_SUMMARY_TIER` in `build_data.py`). A large first import may need more than one run. Until
  its turn comes, a row shows its original title, in its own language, and the run summary's **Translations** line
  counts it as "waiting for the next run".
- **They are asked for in every run**, so the translation memory (`data/translations/cache.json`) keeps them; a new
  export only adds the new stories' texts.
- **A captured story** (section 8) shows the capture's title and its translation: it is not translated twice.

After translation the row shows the translated title, with the original under it in italics. A machine translation
is marked by a small languages icon in front of the original (screen readers hear "(Auto-translated)" with the
title and "Original title:" before the original), and by one note over the list while such a row is on screen:
"Titles translated automatically from Spanish — originals in italics" (on the Spanish page: "Títulos traducidos
automáticamente del inglés — originales en cursiva", `read.mt_note_es` / `read.mt_note_en`). A row whose texts were
all translated by hand (`overrides.yml`) gets no icon. When the title is shown untranslated but the subtitle is a
machine translation, the subtitle carries the icon itself.
To fix a translation, add the exact original text and your words to `data/translations/overrides.yml`, as for any
title ([Translations §2.1](translations.md#21-fix-one-wrong-translation-the-80-case)).

---

## 12. Going further: where to change the code

Read the module's opening comment first: [`scripts/sync/writers_archive.py`](../scripts/sync/writers_archive.py)
explains the files, the checks and the cleaning in plain words. The data files are described field by field in
[docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md) (raw `writers_archive.json` in §2, the site file in §3).

| What | File | Function or name |
|---|---|---|
| the folder, the file names, the newest file | `scripts/sync/writers_archive.py` | `archive_dir`, `NAME_RE`, `NAME_DATES`, `COPY_RE`, `VERSION_RE`, `parse_name`, `newest_key`, `candidates`, `links_pub`, `import_archive` |
| the columns and the needed ones | same | `COLUMNS`, `REQUIRED`, `map_header`, `read_rows` |
| reading a file, its fingerprint | same | `read_text`, `content_hash` |
| tidying a text | same | `clean_field`, `repair_mojibake` |
| one row → one story | same | `row_item`, `writers_of`, `issue_of`, `label_from_key`, `texas_answer`, `is_anonymous`, `fix_initials`, `is_column`, `COLUMN_TITLE_RE`, `drop_content_duplicates` |
| the cut-off guard | same + `config/site.yml` | `min_rows_ratio`, `MIN_ROWS_RATIO`; `writers_archive.min_rows_ratio` |
| after a change that alters the rows: count every file as taken in again | same | `PARSER_VERSION` (raise it by one) |
| where a writer is from | `scripts/sync/geo.py` | `classify_writer`, `best_of`, `classify_location`, `TYPO_ALIASES`, `EXTRA_PLACES`, `TEXAS_KEYS`, `TEXAS_REGIONS` |
| the join with the daily capture, the site file, status.json | `scripts/sync/build_data.py` | `plan_writers_archive`, `_wa_from_row`, `_wa_from_capture`, `build_writers_archive`, `writers_archive_status`; translations: `plan_translations` (`WA_TITLE_TIER`, `WA_SUMMARY_TIER`) |
| read in every kind of run | `scripts/sync/run_all.py` | `MODULES`, `QUICK_MODULES` |
| the run summary block, the commit message, the issue's advice | `.github/workflows/update.yml` | step *Write run summary* (search `Writers archive`), step *Commit refreshed data* (search `+ writers archive`), job `report` → `HINTS` |
| the page | `src/pages/published.njk` | the `#archive` section, macros `arcRow` and `arcChip`, `<script id="pw-arc-config">` |
| the page's rows, counts, decades, hometowns | `eleventy/filters/published.js` | `pwArchive`, `pwArchiveTotals`, `PW_ARC_PAGE` (40), `ARC_TOP` (8), `ARC_URL`, `ARC_JS_KEYS` |
| the page's script | `src/assets/js/published-archive.js` | `buildRow` (the rows of the JSON file), `render`, `load` |
| the rest of Texas | `src/pages/published-archive-json.11ty.js` | the short keys are listed at the top of the file |
| the look | `src/assets/css/areas/published.css` | the `pw-arc-*` classes |
| the words | `src/_i18n/published.json`; `src/_i18n/read.json` | `published.archive.*`, `published.cta_archive`, `published.btn.archive`, `published.how.archive`; the note over the list: `read.mt_note_es` (English page), `read.mt_note_en` (Spanish page) |
| home, search, offline, status | `eleventy/filters/home.js`, `src/pages/index.njk`; `eleventy/filters/library.js`; `src/pages/sw.11ty.js`; `src/pages/status.njk` | `homeArchive` (`home.spot_archive`); `searchIndex` (the writers' hometowns, and the keywords `search.kw.published_archive` in `src/_i18n/library.json`); `save` and `files`; `srcIcons` (`community.status.src.writers_archive`) |

**Small recipes:**

- *Another column of letters should get the "Letter or short piece" mark.* Add its title, written in lower case
  with every punctuation mark as a space, to `COLUMN_TITLE_RE` in `writers_archive.py` (for example
  `|letters to the editor`). Every run reads the files whole again, so the next run applies it; also raise
  `PARSER_VERSION`, the module's rule for a change that alters the rows (the files then count as taken in again:
  `imported_at` moves and the run summary says "New archive file used").
- *Show 25 rows before "Show more" instead of 40.* `PW_ARC_PAGE = 25` in `eleventy/filters/published.js` (the page
  and its script both read it), and the two 40s in `tests/test_published_archive.py` (`View`: search `["page"], 40`;
  `PageBuild.test_the_scripts_settings`: `(lang, 8, 40)`).
- *A misspelt town keeps a writer out of Area 65.* Add it to `TYPO_ALIASES` in `geo.py`
  (`"Corsicanna": "Corsicana"`), or a place the Census table lacks to `EXTRA_PLACES` with its county. Run
  `python -m unittest tests.test_writers_archive tests.test_spotlight` afterwards: the place tests must stay green.
- *Look at the page with the test sample instead of the real data* (PowerShell):
  `$env:WRITERS_ARCHIVE = "tests/fixtures/writers_archive/site_sample.json"; npx @11ty/eleventy --serve`
  (`Remove-Item Env:WRITERS_ARCHIVE` afterwards; `src/_data/db.js` reads it).
- *Rebuild the archive on a PC from the files:* `python -m scripts.sync.run_all --only writers_archive --no-translate`
  (the module, then the site data). Put the robot's files back before you commit
  ([Automation and troubleshooting §11.2](automation-and-troubleshooting.md#112-the-sync-on-a-pc)).

**Tests:** [`tests/test_writers_archive.py`](../tests/test_writers_archive.py) (the names, the fingerprint, the
columns, the cleaning, issues, writers, places, the folder, the site file, translations, status.json, the real
files), [`tests/test_published_archive.py`](../tests/test_published_archive.py) (the page's rows and words, the
JSON file, the offline lists, the site search's words, a page build, the script's own rules, the styles) and
[`tests/test_published_scripts.py`](../tests/test_published_scripts.py) (the page's two scripts run in Node.js on a
small stand-in for the page: the search rules, the address, the rest of Texas, *Try again*, the empty state, the
note over the list). Small sample files are in `tests/fixtures/writers_archive/`.

---

## 13. Troubleshooting

**Where to look first:** the **Writers archive** block of the newest *Website update* run summary (section 6.1);
then the row "Texas writers archive" on `/status/`; then `data/raw/writers_archive.json` on GitHub → `files` (the
file in use for each magazine, `imported_at` = when it was taken in) and `stats` (`notes`, `warnings`).

| What you see | Likely cause | What to do |
|---|---|---|
| The archive did not change after the push | the run is still going or waiting; the file was not used (a **CSV file to fix** line); its name is not understood, or it is not a `.csv` file (a warning); the date in its name is older than the file in use | open the run summary's Writers archive lines; rename or fix the file and push again |
| "older archive file still in content/archive (it is not used and may be deleted): …" in every run | an older copy is still in the folder | delete it (section 5) |
| "older archive file still in content/archive (it stays in use until … is fixed): …" | the newer file of that magazine failed a check (its **CSV file to fix** line says why); its rows on the site still come from this file | fix the newer file (section 10); deleting the older one changes nothing on the site |
| "a .csv file in content/archive whose name is not an archive file's (it is not used): …" | "Copy of …", no magazine or no "archive" in the name | rename it like `aagrapevine_archive_2026-11-05.csv` |
| "… in content/archive is not read — only .csv files are …" | the export was saved as `.xlsx`, `.numbers` or another format | save it as CSV UTF-8 with the same name, and delete the other file |
| The older file is used, not the new one | the new name's date is older, missing, or written day first (`05-11-2026` = May 11); or the new file failed a check (a **CSV file to fix** line, and the older file "stays in use until" it is fixed) | write the day as `2026-11-05`; or fix the new file (section 10) |
| **CSV file to fix**: "the column … is missing" | a column was lost in the export, or its header renamed beyond recognition | export again; headers count by how they start |
| **CSV file to fix**: "… has N rows, the file used before had M — it looks cut off" | the export stopped early, or the magazine really removed many entries | check the file; if it is right, `min_rows_ratio: 0` for one run (section 10.1) |
| **CSV file to fix**: "… could not be read" | a broken file | export again |
| Accents look broken on the page ("Ã¡") | the export itself is damaged beyond what the tidying repairs, or it was saved in an unusual encoding | export again; save as CSV UTF-8 |
| A "�" in a title or a byline; a warning "… character(s) are not UTF-8 (the first on line N)" | a few bytes of the file are not UTF-8 (the rest is read normally) | look at that line of the file; export again, or save it as CSV UTF-8 |
| "the name says Grapevine but its links are La Viña's — it is used as the La Viña file" | the two files' names were swapped | rename them |
| "the name says Grapevine but its links are La Viña's, and La Viña already has its file (…) — this file is not used …" | a La Viña export saved under a Grapevine name, while La Viña has a newer file | export Grapevine again and save it under that name (or delete the file) |
| A writer from Area 65 is listed with the rest of Texas | the place is misspelt, missing from the Census table, or its county is not on the list | check the place (section 7); add a county, a `TYPO_ALIASES` or an `EXTRA_PLACES` entry |
| A story is missing | neither reading of its place is in Texas and **Texas Author?** is not `Yes`; its link is not on aagrapevine.org or aalavina.org; it was listed twice (kept once) | fix the row in the next export, or wait for the daily capture (section 8) |
| A Grapevine title is English on the Spanish page | its translation is still waiting | wait a few runs; or `overrides.yml` (section 11) |
| The Code check is red after a new export: `test_the_headline_numbers` (*Website update* stays green: it leaves this test to the Code check) | the new file is one the site does not use (the test's message is the same text as the **CSV file to fix** line: a missing column, a file that cannot be read), or it holds no rows by Texas writers, no year at all, or a year before the magazine began | fix the file and push again, or delete it (section 10); the site keeps the older rows meanwhile. The test pins exact numbers only for the files of 4 October 2026 (section 6.3) |
| `/status/`: "Texas writers archive" **Failed** | a file was not used | the run summary's **CSV file to fix** line says why |
| The issue "A content source has stopped updating" names the Texas writers archive | a file has not been usable for 7 days | follow its advice; it closes by itself |
| "New in 7 days" for the archive is about 1,261, and "Found in the last 7 days" on `/status/` jumped | the first import: every row is new for a week (`first_seen`, section 6.1) | nothing: normal; it drops back after 7 days |
| "New in 7 days" for the archive stays 0 | no file brought new stories in the last 7 days (the same files give the same rows) | nothing: normal |
| "Loading the stories from the rest of Texas…" stays, or "The stories from the rest of Texas didn’t load" | the visitor is offline or on a very slow line (the page waits 20 seconds) | **Try again** (until then the Area 65 stories already on the page still show, and after a failed download the decade chips count those); "Save key pages for offline" keeps the file for next time |
| The archive section is missing on `/published/` | no rows at all: no file and no captured Texas story | put the files back in `content/archive/` |
| Deleting the files did not empty the archive | each magazine keeps the rows of its last file (`data/raw/writers_archive.json`), and the captured Texas stories stay | that is on purpose; ask whoever helps with the code if the archive must really go |

---

## 14. Good practice and AA principles

- **The files are public.** Everything in the repository can be read by anyone, `content/archive/` included. The
  exports hold what the magazines' online archives publish — titles, bylines as printed (a first name and an
  initial), places, the publishers' subtitles, links — plus the export's own readings of them (City, State, Texas
  Author?, Notes). Never add contacts or full names to them.
- **Never the stories' text.** The site shows titles, the publishers' own subtitles and links back to the
  magazines' pages, nothing more; no covers, logos or artwork either.
- **Anonymity.** Bylines stay exactly as the magazines printed them; "Anonymous" stays anonymous. The site never
  adds anything about a writer.
- **Attraction rather than promotion.** The archive lists stories by date; it never ranks writers or counts who
  wrote most.
- **One file per magazine.** Delete the older export when you add a new one: the history keeps it.
- **One change per commit**, with a plain message ("archive: Grapevine export of 2026-11-05"), then a look at the
  run summary.

---

## 15. See also

- [How-to guide index](README.md) · [content/archive/README.md](../content/archive/README.md) (the short version,
  next to the files)
- [Automatic sources](automatic-sources.md) (the magazine stories the daily capture reads; the archive as a source:
  §3.16) · [Settings](settings.md) (`spotlight:` and `writers_archive:`) · [Translations](translations.md)
- [Automation and troubleshooting](automation-and-troubleshooting.md) (the runs, the run summary, the Code check) ·
  [Pages and code](pages-and-code.md) (the `/published/` page and its archive: §5.5)
- [E-mail and alerts](email-and-alerts.md) (the issue "A content source has stopped updating")
- In the repository: [`scripts/sync/writers_archive.py`](../scripts/sync/writers_archive.py) ·
  [`scripts/sync/geo.py`](../scripts/sync/geo.py) · [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) ·
  [`eleventy/filters/published.js`](../eleventy/filters/published.js) ·
  [`src/assets/js/published-archive.js`](../src/assets/js/published-archive.js) ·
  [`docs/DATA_SCHEMA.md`](../docs/DATA_SCHEMA.md) (*writers_archive.json*, raw and site)
