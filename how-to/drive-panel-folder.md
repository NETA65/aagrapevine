# The Drive panel folder: what you put there and where it shows

> Part of the [how-to guide](README.md). This page covers the committee's Google Drive as a whole: the shared
> folder **A65_GV**, the panel folder **2027-2028_Panel77_GVLV**, every folder you can make inside it, and the rules
> that every Drive file follows: sharing, folder names, file types, dates and titles in file names, what is never
> published, shortcuts, deleting and moving, limits and the optional API key. Each kind of folder also has a page
> of its own; the table in [§3.5](#35-the-category-folders) links them.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start](#2-quick-start) —
   [put a file on the website](#21-put-a-file-on-the-website) ·
   [take one off](#22-take-a-file-off-the-website) ·
   [start the next panel's folder](#23-start-the-next-panels-folder) ·
   [check that the site can read the Drive](#24-check-that-the-website-can-read-the-drive)
3. [Full reference with examples](#3-full-reference-with-examples) —
   [the folder tree](#31-the-folder-tree) ·
   [sharing](#32-sharing-anyone-with-the-link-is-required) ·
   [panel folders](#33-how-a-panel-folder-is-recognised) ·
   [loose folders](#34-loose-folders-and-files-outside-a-panel) ·
   [category folders](#35-the-category-folders) ·
   [the booth folder](#36-the-booth-folder-new) ·
   [file types](#37-file-types) ·
   [dates](#38-dates-in-file-names) ·
   [titles](#39-titles-from-file-name-to-title) ·
   [never published](#310-what-is-never-published) ·
   [shortcuts](#311-shortcuts) ·
   [descriptions](#312-file-descriptions-and-other-drive-extras) ·
   [replace, rename, move, delete](#313-replace-rename-move-delete) ·
   [limits](#314-limits) ·
   [the API key](#315-the-optional-google_api_key)
4. [What happens next (which run, how long)](#4-what-happens-next-which-run-how-long)
5. [Where it shows on the website](#5-where-it-shows-on-the-website) —
   [every place](#51-every-place-a-drive-file-can-appear) ·
   [twenty uploads](#52-twenty-uploads-and-where-each-one-shows) ·
   [pages that link one file](#53-pages-that-link-one-file-by-its-name) ·
   [behind the scenes](#54-behind-the-scenes-the-run-summary-and-the-data-files)
6. [Going further: change the code](#6-going-further-change-the-code) —
   [the chain](#61-the-chain-from-drive-to-page) ·
   [code map](#62-code-map) ·
   [try a rule first](#63-try-a-rule-on-your-pc-first) ·
   [worked example: a new category](#64-worked-example-a-new-category-folder-end-to-end) ·
   [a category with its own page](#65-a-category-with-a-page-of-its-own-the-booth-as-the-model) ·
   [other changes](#66-other-changes-and-where-to-make-them) ·
   [tests](#67-tests-to-run)
7. [Troubleshooting](#7-troubleshooting)
8. [Good practice and AA principles](#8-good-practice-and-aa-principles)
9. [See also](#9-see-also)

---

## 1. What this is

The website has no upload page. The committee keeps its files in one shared Google Drive folder, and the website
reads that folder by itself:

1. Someone puts a file in Google Drive → **A65_GV** → **2027-2028_Panel77_GVLV** → a folder such as `reports` or
   `photos`.
2. The next run of the GitHub workflow **Website update** lists the folders (no password: the folder is shared
   "Anyone with the link"), turns every file into an *item* with a title, a date and a category, and saves the list
   in the repository (`data/raw/drive.json`).
3. The same run builds the website and publishes it. The file is now on the right page, in English and in Spanish.

What you decide from Drive alone, without touching GitHub:

| You decide | With | Example |
|---|---|---|
| Which page a file lands on | the folder you put it in | a file in `flyers/` → the Flyers tab of the Portfolio |
| Whether a flyer becomes an event | a day date in its name | `2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` → an event on March 14, 2027 at 9 AM |
| Its title | its file name | `2027-02-17 Committee report - February.pdf` → "Committee report - February" |
| Its date | a date in its file name | the same file → February 17, 2027 (in a flyer's name the date is the event's; in the booth folder it stays in the caption) |
| Photo album names | sub-folders of `photos` | `photos/2027 Spring Assembly/` → the album "2027 Spring Assembly" |
| Whether it is published at all | words in its name, its type | `PRIVATE budget.pdf` → never on the site |
| How a booth slide plays | the booth naming convention | `GV EN Welcome to our table (first) (15s).png` → shown first, 15 seconds |

**Page addresses in this guide** are relative to `https://neta65.github.io/aagrapevine`. Every page has a Spanish
twin under `/es/`: `/portfolio/` is `https://neta65.github.io/aagrapevine/portfolio/`, its Spanish page is
`/es/portfolio/`.

The code behind this page is mostly [scripts/sync/drive.py](../scripts/sync/drive.py) (reads the folders and the
names), [scripts/sync/drive_listing.py](../scripts/sync/drive_listing.py) (lists one folder) and
[scripts/sync/build_data.py](../scripts/sync/build_data.py) (spreads the items over the site's data files); the
booth folder's names are read by [scripts/sync/booth_names.py](../scripts/sync/booth_names.py). You never need to
open them to use the Drive; [§6](#6-going-further-change-the-code) is for when you want to change a rule.

---

## 2. Quick start

### 2.1 Put a file on the website

1. Open Google Drive → **A65_GV** → **2027-2028_Panel77_GVLV**.
2. Open the folder for the kind of file — the table in [§3.5](#35-the-category-folders) lists them all:
   `reports`, `notes`, `slides`, `workshops`, `forms`, `flyers`, `photos`, `bulletin`, `booth`. If it does not
   exist yet, create it; an English or a Spanish name works (`informes`, `notas`, `fotos` …).
3. Name the file: **date first, written `YYYY-MM-DD`, then a plain title** — for example
   `2027-02-17 Committee report - February.pdf`. Keep these out of the name, because a file with any of them is never
   published: `PRIVATE`, `PRIVADO`, `(Responses)`, `(Respuestas)`, `wrong size`. No full names of AA members.
4. Upload it. Then wait for the next update — the midday or evening refresh, else by the next morning — or start one
   now: GitHub → **Actions** → **Website update** → **Run workflow** → tick **skip_crawl** → green **Run
   workflow**. It takes a few minutes.
5. Look at the page. For the example: `/portfolio/#docs-reports` (and `/es/portfolio/#docs-reports`) shows the card
   "Committee report - February", dated February 17, 2027.

### 2.2 Take a file off the website

1. **Best:** move the file out of A65_GV (into a folder only the committee can open), or delete it. At the next run
   it leaves every page: Portfolio, Photos, Events, Bulletin, the booth display, search, What's New.
2. **To keep it in the panel folder but off the website:** add `wrong size` (or `PRIVATE`) to its name. The site
   stops showing it at the next run — but the file is still in A65_GV, where anyone with the link can open it.
3. To replace a file with a better version, do not delete it: upload the new version over it (see
   [§3.13](#313-replace-rename-move-delete)) so every link already shared keeps working.

### 2.3 Start the next panel's folder

Panel 79 serves 2029–2030. When it begins:

1. In **A65_GV** — next to the Panel 77 folder, not inside it — create a folder named `2029-2030_Panel79_GVLV`.
2. Inside it, create the folders you need (`reports`, `notes`, `slides`, `flyers`, `photos`, `bulletin`, `booth` …).
3. That is all: no setting to change. From the next update on, the site reads both panel folders.
   - Every **Open Drive folder** button (Portfolio, Photos, Bulletin and Events pages) now opens the Panel 79
     folder, the "how to add files" boxes name Panel 79, and the web presentations' `{live:panel}` fact says
     "Panel 79 (2029–2030)". These switch as soon as the folder exists, even while it is empty — so create it when
     the new panel actually starts.
   - Once both panels have files, each Portfolio tab shows a heading per panel: "Panel 79 (2029–2030)", then
     "Panel 77 (2027–2028)".
4. Later, when the Panel 77 files should leave the website, change `min_panel: 77` to `min_panel: 79` in
   [config/site.yml](../config/site.yml) under `drive:` ([Settings](settings.md#35-drive--the-committees-google-drive)).
   The files stay in Drive; the site stops reading them and they leave its pages at the next update (saving
   `config/site.yml` starts one by itself).

Tip: put the year in photo album names (`2029 Spring Assembly`). Albums with the same name in two panels are merged
into one album on `/photos/`. The same goes for the booth display: two panels' booth folders play together, and
sub-folders with the same name form one collection.

### 2.4 Check that the website can read the Drive

1. In Google Drive, right-click **A65_GV** → **Share**. Under **General access** it must say
   **Anyone with the link**, role **Viewer**.
2. Leave the folders inside it as they are: they inherit that setting. Do not restrict a folder inside A65_GV.
3. On the website, open `/status/` (or `/es/status/`). The row **Google Drive (committee uploads)** should be OK,
   with a recent date for the last good check.

---

## 3. Full reference with examples

### 3.1 The folder tree

```
A65_GV/                               the shared root folder: "Anyone with the link" — Viewer
├── 2027-2028_Panel77_GVLV/           a PANEL folder: everything the site reads is inside one
│   ├── reports/                      → Portfolio, tab Reports
│   ├── notes/                        → Portfolio, tab Meeting notes
│   ├── slides/                       → Portfolio, tab Slides
│   ├── workshops/                    → Portfolio, tab Workshops
│   ├── forms/                        → Portfolio, tab Sign-ups (Google Forms)
│   ├── flyers/                       → Portfolio, tab Flyers; a name with a day date also makes an EVENT
│   ├── photos/
│   │   └── 2027 Spring Assembly/     → one album on /photos/
│   ├── bulletin/                     → posts on /bulletin/
│   ├── booth/                        → the booth display on the About page, and nothing else
│   │   └── Spring Assembly 2027/     → a collection the booth player can switch on or off
│   └── Archive/   (any other name)   → its own Portfolio tab "Archive"; its pictures → an album
├── 2029-2030_Panel79_GVLV/           the next panel: read automatically (§3.3)
├── 2025-2026_Panel75_GVLV/           older than min_panel (77): skipped
└── flyers/ notes/ a CSV, a form …    "loose", outside every panel folder: ignored (§3.4)
```

The sub-folders "2027 Spring Assembly", "Spring Assembly 2027", "Archive" and the Panel 79 and Panel 75 folders are
examples. **Today** (October 2026) the panel folder holds `booth` (still empty), `bulletin` (one post), `flyers`
(10 pictures), `notes` (2 PDFs), `photos` (still empty), `reports` (2 PDFs), `slides` (4 PowerPoint files) and
`workshops` (1 PDF) — no `forms` folder yet. The A65_GV root also holds six old loose folders (`flyers`, `notes`,
`photos`, `reports`, `slides`, `workshops`), a CSV file, and a Google Form with its "(Responses)" spreadsheet. The
site ignores all of those — but anyone with the folder's link can open them ([§8](#8-good-practice-and-aa-principles)).

Three rules explain almost everything on this page:

- **Only what is inside a panel folder is read.**
- **The first folder below the panel folder decides what a file becomes** — however deep the file sits.
- **The file name gives the title, the date and the options** (flyer times, bulletin pins, booth settings).

### 3.2 Sharing: "Anyone with the link" is required

**Why.** The site reads Drive without a password. Without the optional API key it opens each folder's public
"embedded folder view" (`https://drive.google.com/embeddedfolderview?id=…`), the page Google shows to anyone who
has the link; with the key it asks the Drive API, which also sees only folders shared that way. A folder the public
cannot open cannot be read.

**What it means.** Anyone who has a link to A65_GV, to a folder in it or to a file in it can open and download it —
including files the website leaves out on purpose ([§3.10](#310-what-is-never-published)). And the links are not
secret: the website's **Open Drive folder** buttons (Portfolio, Photos, Bulletin and Events pages) open the current
panel folder for every visitor, and the address of A65_GV itself is in `config/site.yml` (`drive.root_folder_id`)
and in the data files of the public repository. The website never puts a button to the A65_GV root on a page, but
treat everything inside A65_GV as public.

**Who can add files** is a Drive question: people with Editor access to A65_GV or to the panel folder. The
Portfolio's members' box ("For committee members · How to add documents") has an **Ask for upload access** button
that starts an e-mail to the committee.

**What happens when the sharing changes** (code: `crawl()` and `merge()` in drive.py, `HtmlLister.list()` and
`HtmlLister.parse()` in drive_listing.py):

| Change | What the next run does | Where you see it |
|---|---|---|
| A65_GV is no longer "Anyone with the link" (or `drive.root_folder_id` names a folder that does not exist or is not public) | reads nothing and **keeps every item as it was** — the site does not empty itself (an id of another *public* folder is different: no panel folder is found there, and every Drive file leaves the site — [§3.3](#33-how-a-panel-folder-is-recognised)) | `/status/`: the Drive row shows a problem. Run summary: **PROBLEM** "root folder unreadable: … — is it shared as 'Anyone with the link'?" After 7 days of failures the issue "A content source has stopped updating" opens |
| One folder inside answers with a sign-in page, a "request access" page or an error | keeps the files of that folder (and of its sub-folders) as they were | run summary **Notes**: "1 folder(s) could not be read — check their sharing settings"; `data/raw/drive.json` → `stats.unreadable_folders` names the folder and the reason |
| One file cannot be opened by the public (its own sharing was changed) | it stays listed if the folder view lists it, but its picture cannot load (the card then shows its icon tile instead), and a bulletin post's or booth message's text cannot be downloaded (the last good text is kept) | the page itself; the Actions log ("could not download text", "Drive returned an HTML page instead of the file") |

### 3.3 How a panel folder is recognised

The rules (code: `crawl()` and `panel_label()` in drive.py; settings in `config/site.yml` → `drive:`):

1. Only folders **directly inside A65_GV** are tested. A panel-looking folder deeper down is an ordinary folder.
2. The name must contain **Panel** followed by the number — spaces may stand between them, nothing else.
   Capitals do not matter. (The setting is `panel_folder_pattern: "Panel\\s*(\\d+)"`.)
3. The number must be **`min_panel` (77) or higher**. Older panels are skipped and only their folder names are
   noted (`stats.skipped_panels`).
4. **Every** folder that passes is read. Two or three panels at once are fine.
5. The label comes from a year pair in the name (`2027-2028`, also with `_`, `/`, `–` or a space between the
   years), else from AA's numbering (panel N serves 1950+N to 1951+N).

Examples (each checked with the real pattern and `panel_label()`):

| Folder name in A65_GV | Result |
|---|---|
| `2027-2028_Panel77_GVLV` | panel 77, "Panel 77 (2027–2028)" — the real one |
| `2029-2030_Panel79_GVLV` | panel 79, "Panel 79 (2029–2030)" — read as soon as it exists |
| `Panel 79`, `panel79`, `PANEL 79`, `2029/2030 Panel79` | panel 79, "Panel 79 (2029–2030)" |
| `2027-2028 Panel 77 GVLV`, `Panel 77 (2027-2028)`, `Panel  77`, `Panel 77-78` | panel 77 |
| `GV Panel 81` | panel 81, "Panel 81 (2031–2032)" (years from AA's numbering) |
| `PANEL 76 old`, `2025-2026_Panel75_GVLV` | older than 77 → skipped (`skipped_panels`) |
| `2027-2028_Panel_77_GVLV`, `Panel-77` | **not a panel folder**: an underscore or a dash between "Panel" and the number breaks it → loose → ignored |
| `Paneles 2029`, `Panelists` | not a panel folder (no number right after "Panel") → loose → ignored |
| `Panel 77 backup`, `OLD Panel 77`, `Copy of 2027-2028_Panel77_GVLV` | **panel 77 again** — read as a second Panel 77 folder |

Two warnings that follow from these rules:

- **Do not rename the panel folder carelessly.** If its name stops matching (say `2027-2028_Panel_77_GVLV`), the
  next run finds no panel folder at all, and **every Drive file leaves the website**: Portfolio, Photos, bulletin
  posts from Drive, flyer events, the booth display's Drive files. The run summary's **Notes** then say
  "no Panel folder >= 77 found in the root folder". Rename it back and the files return at the following run — as
  new arrivals (they count again in that month's digest).
- **Do not keep a second folder with the panel's name in A65_GV** — a backup, an old copy, a re-uploaded duplicate.
  It is read too, so every file in it shows twice. Delete it, or move it out of A65_GV.

Which panel the website names and links: the **highest** panel number found. The **Open Drive folder** buttons
open that panel's folder (never the A65_GV root), and the presentations' `{live:panel}` fact names it (code:
`driveInfo()` in [committee.js](../eleventy/filters/committee.js)). When no panel folder is found, the buttons
disappear and the label falls back to "Panel 77" (the `min_panel` value).

Every item remembers its panel: the data gets `panel: 77`, the label "Panel 77 (2027–2028)" and a tag `panel-77`.

### 3.4 Loose folders and files outside a panel

Anything that sits directly in A65_GV and is not a panel folder is **loose**: a folder such as `flyers`, a PDF, a
Google Form. Loose things are **ignored**, and their names are noted in `data/raw/drive.json` →
`stats.loose_skipped` (the first 30). Today that list is the six old folders and the Google Form
"40th Annual Gathering of Eagles - Grapevine Table Signup".

| Setting `include_loose_folders:` | What happens to a loose folder or file |
|---|---|
| `false` (today, recommended) | ignored, named in `stats.loose_skipped` |
| `true` | read like a category folder that belongs to no panel: `A65_GV/flyers/x.pdf` is a flyer, `A65_GV/Old stuff/x.pdf` an "other" file, a loose file is filed by its type ([§3.5](#35-the-category-folders)). These items have no panel; with panel files beside them, each Portfolio tab groups them under "Other files" / "Otros archivos" |

For a one-off look on a PC, `python -m scripts.sync.drive --include-loose --dry-run` does the same without changing
the setting (it reads the real Drive, prints the counts and three items, and writes nothing).

The never-published rules are checked first ([§3.10](#310-what-is-never-published)): a CSV or a "(Responses)" sheet
in the root is only counted in `stats.excluded`, never named.

### 3.5 The category folders

Every file is filed under the **first folder below the panel folder**. Its name is matched against these words
(code: `CATEGORY_SYNONYMS` and `category_for()` in drive.py):

| Folder — any of these words | Each file becomes | Where it shows | Details |
|---|---|---|---|
| **reports** · report, informe, informes, reporte, reportes | a Portfolio file | tab **Reports / Informes** (`/portfolio/#docs-reports`); Library ("Committee reports"); search; home tiles; What's New + RSS; digest | [Photos, slides, reports … §4.2](photos-slides-reports.md#42-reports--area-and-committee-reports) |
| **notes** · note, nota, notas, minutes, minuta, minutas, acta, actas | a Portfolio file | tab **Meeting notes / Notas de reuniones** (`#docs-notes`) — the Meetings page links this tab; Library; search; home; What's New; digest | [§4.3](photos-slides-reports.md#43-notes--minutes-agendas-and-meeting-notes) |
| **slides** · slide, presentation, presentations, presentación, presentaciones, diapositiva, diapositivas, powerpoint, deck, decks | a Portfolio file | tab **Slides / Presentaciones** (`#docs-slides`); a deck named exactly like a web presentation's `drive_title` is also its PowerPoint copy on `/orientation/` and gets **Present on the web** | [§4.4](photos-slides-reports.md#44-slides--presentations-and-the-four-deck-copies) · [Presentations](presentations.md) |
| **workshops** · workshop, taller, talleres | a Portfolio file | tab **Workshops / Talleres** (`#docs-workshops`); Library; search; home; What's New; digest | [§4.5](photos-slides-reports.md#45-workshops--workshop-materials) |
| **forms** · form, formulario, formularios, sign up, sign ups, signup, signups, inscripción, inscripciones | a sign-up card (Google Forms) | tab **Sign-ups / Inscripciones** (`#docs-forms`) with a **Sign up** button; a form that stopped accepting answers disappears from every page | [§4.6](photos-slides-reports.md#46-forms--google-forms-for-sign-ups) |
| **flyers** · flyer, flier, fliers, volante, volantes, folleto, folletos | a Portfolio file — and, when the name holds a day date, an **event** | tab **Flyers / Volantes** (`#docs-flyers`); events on `/events/`, in `/events.ics`, on the home page ("Upcoming events"), in search and What's New | [Flyers and events](flyers-and-events.md) |
| **photos** · photo, foto, fotos, picture, pictures, pics, image, images, imagen, imágenes, gallery, galería | album photos and videos — one album per sub-folder | `/photos/` (`#album-…`); home tiles; What's New ("4 new photos in …"); digest; search (one entry per album); never the Library | [§4.7](photos-slides-reports.md#47-photos--photo-albums) |
| **bulletin** · bulletins, bulletin board, boletín, boletines, announcement, announcements, anuncio, anuncios, aviso, avisos, news, noticias | a bulletin post: the file name is the headline, the text of a Google Doc / .txt / .md / .docx is the body | `/bulletin/`; home ("Bulletin"); monthly toolkit; What's New + RSS; search; digest | [Bulletin](bulletin.md) |
| **booth** · booths, mesa, mesas, kiosk, kiosko, kiosco, display, displays, pantalla, pantallas, stand, stands, exhibit, exhibits, exhibición, exhibiciones | a slide of the booth display | the booth display on the About page (`/about/#booth`) — **and nowhere else** | [§3.6](#36-the-booth-folder-new) · [Booth display](booth.md) |
| **any other name** — `Archive`, `Handouts`, `La Viña` … | an "other" file | documents: a Portfolio tab named after the folder (`#docs-folder-archive`), Library type "Other"; pictures and videos: a `/photos/` album named after the folder; Google Forms: the Sign-ups tab | [§4.8](photos-slides-reports.md#48-any-other-folder-name-other) |

The Spanish pages use the same anchors: `/es/portfolio/#docs-reports`, `/es/photos/#album-…`.

> **Note:** the comment above `drive:` in `config/site.yml` says "Any other folder name shows up in the Library
> under its own name". The code shows such a folder's documents in a **Portfolio** tab named after the folder; the
> Library files them under the type "Other" / "Otros".

**How a folder name is read** (checked with `category_for()`):

- **Only the first folder below the panel folder counts.** Deeper folders never change the category:
  `reports/2027/March.pdf` is a report; `photos/flyers/x.jpg` is a photo in the album "flyers";
  `flyers/photos/x.jpg` is a flyer; `booth/photos/x.jpg` is a booth file.
- **Capitals, accents and punctuation do not matter, and the word can stand anywhere — as a whole word.**
  `Meeting Notes`, `Fotos 2027`, `Informes-Reports`, `Treasurer reports`, `Sign-up sheets`, `BOLETIN 2027` all work.
  `Newsletter` does not ("news" is not a whole word there).
- **When two category words appear, the one written first wins**: `Fotos del taller` → photos, `Taller de fotos`
  → workshops; `Reports and Notes` → reports, `Notes & Reports` → notes.
- Two folders of the same kind are fine: the files of `reports` and `Informes` land in the same tab.
- A Spanish folder word (`informes`, `fotos`, `mesa` …) also tells the site that the titles inside are probably
  Spanish (`_SPANISH_HINTS`; the language is still guessed from each title).

Folder names that surprise people (checked with the real function, booth words included):

| Folder below the panel folder | Becomes | Why |
|---|---|---|
| `Agendas`, `Training`, `Handouts`, `Slideshow`, `Photography`, `Newsletter` | its own Portfolio tab ("other"); its pictures an album | none of the category words — rename (`Meeting Notes and Agendas` → notes) or add a word ([§6.6](#66-other-changes-and-where-to-make-them)) |
| `2027 Spring Assembly` (directly in the panel folder) | "other": a Portfolio tab and an album, both named "2027 Spring Assembly" | it works, but an album belongs inside `photos/` |
| `Booth photos`, `Booth display`, `Display boards`, `Kiosk 2027` | **booth** | the booth word comes first |
| `Literature display photos`, `Exhibit hall photos`, `Mesa de literatura`, `Mesa de GV y LV` | **booth** | "display", "exhibit" and "mesa" are booth words, and they come before "photos" |
| `Booth flyers` | **booth** — these flyers do **not** become events | "booth" comes first; put flyers in `flyers/` |
| `Photos of the booth`, `Pictures of the booth`, `Fotos de la mesa` | photos (an album) | the photo word comes first |
| `photos/Booth at CityWide` | the album "Booth at CityWide" | only the first folder counts, and it is `photos` |
| `Workshop displays`, `Flyers for the booth`, `Notas de la mesa` | workshops, flyers, notes | the first word wins |
| `Stand-up` | **booth** | the dash counts as a space, and "stand" is a booth word |
| `Report Cards` | reports | "report" is a whole word |
| `Responses` | "other" — **published** | only `(Responses)` with the brackets is never published |
| `Private`, `PRIVATE notes` | never read, nor anything inside | the name contains "private" ([§3.10](#310-what-is-never-published)) |

> **Note:** the booth words are new this round. A folder whose **first** category word is a booth word —
> `Booth photos`, `Literature display photos`, `Exhibit hall photos`, `Booth flyers` — used to be a photo album
> (or flyers) and now feeds only the booth display. Pictures of the booth meant for the Photos page go in
> `photos/`, for example `photos/2027 Booth at CityWide/`.

**Files sitting directly in the panel folder** (no folder) are filed by their type (code: the line that sets
`category` in `build_item()`):

| File directly in 2027-2028_Panel77_GVLV | Goes to |
|---|---|
| a picture or video (`Panel photo.jpg`) | photos: the panel's own album "Panel 77 (2027–2028) — photos" |
| a Google Form (`Quick poll`) | forms: the Sign-ups tab |
| slides (`Committee deck`, a Google Slides file or a .pptx) | slides: the Slides tab |
| anything else (`2027-03-14 Spring Assembly.pdf`, a Google Doc …) | "other": a Portfolio tab **Other / Otros** |

It works, but a folder is clearer for everyone ([Photos, slides, reports … §4.9](photos-slides-reports.md#49-files-sitting-directly-in-the-panel-folder)).

### 3.6 The booth folder (new)

The **booth display** is a show that plays by itself on a screen at the committee's table at assemblies and
conventions. It lives on the About page (`/about/#booth`, `/es/about/#booth`). Its photos, videos, sound files and
short texts come from the panel folder's booth folder; its quizzes, facts and quotes come from the CSV file
`content/booth/booth.csv` in the repository; its starting settings from `config/site.yml` → `booth:`. The player,
the CSV and the settings are explained in [Booth display](booth.md). This section covers the Drive side.

**The folder.** Any first folder whose first category word is a booth word (the list and the first-word rule are
in [§3.5](#35-the-category-folders)), for example `booth`, `Mesa` or `Booth display` — not `Photos of the booth`.
Its sub-folders are **collections**: `booth/Spring Assembly 2027/` is the collection "Spring Assembly 2027", which
the player's settings can switch off (all are on by default). A deeper sub-folder belongs to its top collection
(`booth/Spring Assembly 2027/extra/x.jpg` → "Spring Assembly 2027"). Files directly in `booth/` form the
collection "Booth folder".

**A booth file goes to the booth display only.** It is never a Portfolio file, an album photo, a bulletin post, a
flyer's event, a What's New entry, a search result or a digest row. Only `/status/` counts it, with the other
Drive files. (Code: `Ctx.items()` in build_data.py leaves the category `booth` out of every other list;
`build_booth()` writes `data/site/booth.json`, which the build turns into the player's `/about/booth.json`.) So the
booth keeps playing without internet, every deploy also saves a copy of the booth folder's pictures, videos and
sound files with the website, within the limits `max_file_mb` (95) and `max_total_mb` (400) under `booth:` in
`config/site.yml`. A video or sound file without a saved copy (too big, past the folder limit, or a download that
failed) is **left out of the show**, and the player's **Settings → Slides** tab (on the Spanish page **Ajustes →
Diapositivas**) says why; a picture without one still shows, from Google's copy, while the screen is online — see
[Booth display](booth.md).

**The naming convention** (code: `parse_booth_name()` in [scripts/sync/booth_names.py](../scripts/sync/booth_names.py);
its header lists every option):

```
[order] [magazine] [language] Title [(option) (option) …].ext        every part is optional except the title
```

| Part | How to write it | What it does |
|---|---|---|
| order | a number of 1–3 digits and a separator at the very start: `01 `, `02-`, `3_` | its place in the player's "In order" mode; never shown. A year or a date at the start is not an order (`2027 Spring Assembly table.jpg`), nor is a number that counts something (`12 Steps poster.png`, `3 ways to carry the message.png`); `01 12 Steps poster.png` gives that one order 1 and keeps "12 Steps poster" |
| magazine | at the start, any capitals: `GV` (Grapevine), `LV` (La Viña), or both: `GVLV`, `GV-LV`, `GV_LV`, `GV+LV`, `GV&LV`, `GV LV`; `AA` (both) only right before a language code (`AA EN Welcome.png`) — otherwise it is the caption's first word (`AA Preamble.png` → "AA Preamble"); or in brackets anywhere: `(LV)`, `[GV]`, `(AA)`, `(Grapevine)`, `(La Viña)` | the slide's colour (Grapevine blue, La Viña amber, both grape) and the player's Grapevine / La Viña filter. No magazine = both |
| language | at the start, in CAPITALS: `EN`, `ES`, `BI` or `EN-ES` (right after the magazine also the words `English`, `Español`: `GV English Welcome.png`); or in brackets anywhere, any capitals: `(es)`, `[English]`, `(en español)` | which of the player's language modes play it. No language = every mode (photos, music, pictures without words). `En la mesa de Tyler.jpg` and `Esto ES La Viña.jpg` keep those words in the caption |
| title | the rest of the name | the caption (a message's heading). Tidied like other Drive titles (underscores, "Copy of", " (1)"), except that **a date stays in the caption** here, and it is never machine-translated: the same words show in both languages. A camera name (`IMG_2045`, `PXL_…`, `WhatsApp Image …`) gives no caption |
| options | in `( )` or `[ ]`, **one option per pair**, any order, English or Spanish, any capitals: `Welcome (first) (15s).png`. (The reader also takes several in one pair, `(first, 15s)`, but a date takes everything after it: `(until 2027-03-15, first)` is never shown first — so keep to one per pair.) | the table below. Anything else in brackets stays in the caption: `Welcome (parte 2).png`, `Welcome (until further notice).png` |

| Option | Means |
|---|---|
| `(poster)` `(cartel)` `(afiche)` | the whole picture, never cropped — the default for .png .gif .webp .svg .bmp, for documents and for videos |
| `(photo)` `(foto)` | fill the screen with a slow zoom — the default for .jpg .jpeg .heic .heif .tif .tiff |
| `(15s)` `(15 s)` `(15 sec)` `(15 seg)` `(15 seconds)` `(15 segundos)` `(2 min)` | seconds on screen for a picture or a message, kept between 3 and 120; ignored for a video or sound file |
| `(0:15-1:30)` `(0:15-)` `(0:15 a 1:30)` `(15-90)` | play only that part of a video or sound file; no end = to its end. Plain seconds count only on a video or sound file: `Poster (15-90).png` keeps "(15-90)" in its caption |
| `(muted)` `(mute)` `(silent)` `(sin sonido)` `(silencio)` | never play this file's sound |
| `(x2)` … `(x5)`, `(2x)`, `(×3)` | shown 2 to 5 times as often (a bigger number counts as 5) — among many slides. With only a few pictures and videos it makes little difference: each one already comes back as often as the show's rules let it (no slide comes back until many others have shown) |
| `(rare)` `(sometimes)` `(poco)` `(a veces)` | shown half as often — the same limit with only a few pictures and videos |
| `(first)` `(primero)` `(primera)` | shown first when the show starts (and again after the settings change) |
| `(from 2027-03-01)` `(desde …)` · `(until 2027-03-15)` `(hasta …)` | only from / until that day, both days included, Central time (also `starting`, `a partir de`; `till`, `through`, `vence`). Any date form of [§3.8](#38-dates-in-file-names) works, with a year from 2000 to 2099 (`(until 1999-12-31)` stays in the caption, and so does a day without its year, `(until March 15)`); a month alone means its first day (from) or its last day (until). After its until-day the file leaves `booth.json` |
| `(no caption)` `(no text)` `(no title)` `(sin texto)` `(sin título)` | no caption; a message without its heading |
| `(off)` `(apagado)` `(draft)` `(borrador)` — or a name that starts with `_` or `~` | kept in Drive, never shown (not even listed as a problem) |

**What the booth can show:** pictures (jpg, jpeg, png, gif, webp, heic, heif, tif, tiff, bmp, svg); documents, as
the picture of their first page (PDF, PowerPoint, Keynote, OpenDocument presentations, Google Slides, Google
Drawings); videos (mp4 — best with H.264 video and AAC sound —, m4v, webm, mov); sound (mp3, m4a, aac, wav, ogg,
oga, opus — played only while the booth's sound is on); and **messages**: a .txt, .md, Google Doc or .docx becomes a
text slide whose heading is the title and whose text is fetched like a bulletin post's body, kept to **bold**,
line breaks and "- " lists, up to 1,200 characters. A message whose name gives no language plays in the
language(s) its paragraphs are written in. Anything else — a .zip, a .doc, a Google Form, an .avi, .wmv or .mkv
video, a .wma or .flac sound file — is never shown and is listed as a **problem** with the reason (for a video or
sound type also what to do: save it as .mp4, or as .mp3 / .m4a). The full list:
[File types §4.18](file-types.md#418-the-booth-folder).

Examples (each checked with the real parser):

| File in the booth folder | What the booth display does with it |
|---|---|
| `GV EN Welcome to our table (first) (15s).png` | poster · Grapevine · English · shown first · 15 seconds |
| `LV ES Testimonio - Mi primer número (0:05-1:45).mp4` | video · La Viña · Spanish · plays 0:05 to 1:45 |
| `GVLV Our booth at CityWide Dallas.jpg` | photo filling the screen · both magazines · every language · caption "Our booth at CityWide Dallas" |
| `IMG_2045.JPG` | photo · no caption |
| `AA Preamble.png` · `AA EN Preamble.png` | poster with the caption "AA Preamble" · poster, both magazines, English, caption "Preamble" (a leading AA is the magazine code only before a language code) |
| `02 GV Ways to subscribe (x3).png` | poster · Grapevine · number 2 in the "In order" mode · three times as often |
| `Spring Assembly 2027/GV EN Book display.jpg` | photo · Grapevine · English · collection "Spring Assembly 2027" |
| `GV EN Welcome message.txt` | message slide: heading "Welcome message", the file's text below |
| `LV ES Taller de escritura en Tyler (hasta 2026-10-26).jpg` | photo · La Viña · Spanish · shown until October 26, 2026 |
| `[LV][ES] Cita (10s) (muted).mp4` | video · La Viña · Spanish · never its sound (the "10s" is ignored for a video) |
| `2027-03-14 Spring Assembly.jpg` | photo · caption "2027-03-14 Spring Assembly" (the date stays) |
| `Draft poster (off).png`, `_notes for the committee.txt` | never shown |
| `GV EN Donate to Grapevine.png` | left out of the show: its caption says a word the booth never shows (Settings → Slides: "left out of the booth: it says “Donate”") |
| `intro.avi` | a problem: "a video type browsers do not play — save it as .mp4 (H.264 video, AAC sound)" |
| `Welcome (from 2027-03-15) (until 2027-03-01).png` | a problem: "its days never meet — the (from …) day is after the (until …) day" |
| `booth questions.csv` | never published — a CSV ([§3.10](#310-what-is-never-published)). The booth's quizzes and facts live in the repository's CSV ([Booth display](booth.md)) |

**Problems** — files that can never be shown (a type the booth cannot show, a note with no text, `(from …)` after
`(until …)`) — are listed in `data/site/booth.json` → `problems` (in English and Spanish) and, each with its
reason, in the Actions run summary under **Booth folder files the booth display can't show** (the first 10 also as
yellow warnings "Booth folder file to fix"), for example "booth/intro.avi — a video type browsers do not play —
save it as .mp4 (H.264 video, AAC sound)". The player's Settings → Slides tab lists them under "Files and rows the show
couldn't use", and the Drive source adds one note that names up to four of them ("booth folder: 1 file(s) the booth
display cannot show — intro.avi (data/site/booth.json → problems says why)"). A message whose text cannot be read
yet (an empty file, or a download that failed with no earlier text to keep) is a problem too, until a later run
reads it.

**Words the booth never shows.** The words the booth's CSV may not use — "PDF", donate / donation, "buy now",
"hurry", "limited time", "Conference-approved" said of Grapevine or La Viña, and the others listed in
[Booth display](booth.md) — are checked here too: a file whose caption, or a note whose heading or text, says one is
**left out of the show**. That check runs when the website is built, so the run summary's booth list does not show
it; the player's Settings → Slides tab and the build's log (step *Build the website*, the `[booth]` lines) name the
file: "Drive: booth/GV EN Donate to Grapevine.png: left out of the booth: it says “Donate”". Rename the file or
change the note; `(no caption)` shows a picture without its title (a hidden caption is not checked).

**The rules for this folder** (also in [Booth display](booth.md)): photos of tables, displays and rooms only — no
faces and no full names of AA members; no Grapevine or La Viña logos, covers, artwork or cartoons, and none of their
audio or video files (official videos go into the booth CSV as YouTube links); only material the committee made or
may use. Everything in the folder is public, like the rest of A65_GV.

### 3.7 File types

The site goes by Drive's file type. Without the API key it reads it from the small type icon in Drive's folder
view, else from a `docs.google.com` link, else from the file's ending; a file it cannot place is a plain document
(code: `kind_for()` in drive.py; `HtmlLister._parse_entry()` and `guess_mime()` in drive_listing.py). The complete
table — every type in every folder — is in [File types](file-types.md#31-every-file-type-in-every-folder); in short:

| Kind | Which files | What it becomes |
|---|---|---|
| photo | any picture: .jpg .jpeg .png .gif .webp .heic .heif .tif .tiff .bmp .svg | in `photos/`, an "other" folder or loose in the panel folder: an album photo. In `reports`, `notes`, `slides`, `workshops`, `forms` or `flyers`: a Portfolio "Image" card (not in the Library) |
| video | any video: .mp4 .mov .m4v .avi .wmv .webm .mkv .3gp | like a photo: an album video, or a Portfolio "Video" card. It plays in Drive's own player |
| slides | Google Slides, PowerPoint (.ppt .pptx .pps .ppsx), Keynote (.key), OpenDocument (.odp) | a Portfolio "Slides" card; Library |
| form | a Google Form | a card with a **Sign up** button: in the Sign-ups tab when it comes from `forms/`, an unknown folder or the panel folder itself, else in the tab of its folder; Library while it accepts answers |
| document | everything else: PDF, Word (.doc .docx), Google Docs, Google Drawings, .txt, .md, .rtf, .odt, .pages, sound (.mp3 .m4a .wav), .zip, .epub, an unknown type | a Portfolio "Document" card; Library |
| bulletin post | **any** file in the bulletin folder | a post on `/bulletin/`; only a Google Doc, .txt, .md or .docx gives it a text ([Bulletin §3.3](bulletin.md#33-drive-which-files-become-posts-and-what-the-text-is)) |
| booth slide | any file in the booth folder | photo, poster, video, sound or message — or a problem ([§3.6](#36-the-booth-folder-new)) |
| never | spreadsheets (Google Sheets, .xlsx .xls .xlsm .ods .numbers), .csv, .tsv, Google Apps Script, Google Sites | never published ([§3.10](#310-what-is-never-published)) |

> **A document in `photos/`** (a PDF agenda dropped there) is neither a Portfolio file nor an album photo: it shows
> only on the home tiles, in What's New and in the digest. Keep `photos/` for pictures and videos.

**Google's own files** get Google's links (code: `urls_for()` in drive.py):

| File | Open | Preview | Download |
|---|---|---|---|
| Google Doc | in Google Docs | Google's preview | a PDF copy |
| Google Slides | in Google Slides | Google's preview | a PDF copy |
| Google Drawing | in Google Drawings | Google's preview | a PNG picture |
| Google Form | the card's **Sign up** opens the form | none | none |
| any other file (PDF, picture, Word …) | Drive's viewer | Drive's viewer | the original file |

Pictures and thumbnails are not copied into the repository: they load from Google (`lh3.googleusercontent.com`)
when someone opens the page, and videos play from Drive. So Drive pictures and videos need an internet connection
(the site's offline copy does not keep them). The booth display is the exception: each deploy saves copies of its
own files with the website.

### 3.8 Dates in file names

A date **anywhere** in a file name sets the file's date and is taken out of the title. Put it first anyway, so
everyone sees it. (Code: `date_from_text()` in [common.py](../scripts/sync/common.py), `name_date()` in drive.py.)
Two folders are different: in `flyers/` the date is the **event's** date ([Flyers and events](flyers-and-events.md#4-name-a-flyer-so-it-becomes-an-event)),
and in the booth folder a date outside brackets stays in the caption ([§3.6](#36-the-booth-folder-new)).

Accepted forms — tried in this order; the first form that matches wins:

| # | Form | Examples (all March 14, 2027 unless noted) |
|---|---|---|
| 1 | year-month-day with `-` `.` `_` or a space; a one-digit month or day is fine | `2027-03-14`, `2027.03.14`, `2027_03_14`, `2027 03 14`, `2027-3-4` (March 4) |
| 2 | eight digits, year-month-day | `20270314` |
| 3 | month-day-year, **US order**, with `-` or `.` (or `/` in a name typed in Drive, such as a Google Doc's — computers do not allow `/` in file names) | `03-14-2027`, `3-14-2027`, `03.14.2027`, `3/14/2027` |
| 4 | month name, day, year — "st/nd/rd/th" and the comma optional | `March 14, 2027`, `Mar 14 2027`, `Mar. 14th, 2027`, `Sept 5 2027` (September 5), `Setiembre 5 2027` |
| 5 | day, month name, year — Spanish "de" / "del" optional | `14 de marzo de 2027`, `14 marzo 2027`, `14 May 2027` (May 14), `5 de sept. de 2027` (September 5) |
| 6 | month name and year only → the 1st of that month | `March 2027`, `Marzo de 2027`, `Marzo del 2027`, `Dic 2027` (December 1) |

Month words: English names and short forms (jan … dec, sept), Spanish names (enero … diciembre, setiembre) and the
short forms ene, abr, ago, dic; any capitals. Years 2000 to 2099 only.

Not read as a date (the text stays in the title):

| In the name | Why |
|---|---|
| `Report 2027` | a year alone |
| `2026-2027 calendar` | a year range |
| `2027-01 Newsletter` | year and month in digits |
| `14-03-2027`, `14.03.2027` | day first: there is no month 14 |
| `2027/03/14` | slashes are not read with the year first |
| `3-14-27` | a two-digit year |
| `2027-02-30` | a day that does not exist |
| `Q1 2027` | not a date |

Traps (each checked with the real code):

- **US order.** `05-03-2027` is **May 3**, not March 5. Write `2027-03-05`.
- **Two dates in one name.** The form higher in the table wins, wherever it stands:
  `Pricing Update - Effective January 1, 2027 - 2026-10-01.pdf` is dated October 1, 2026 (form 1 beats form 4), and
  "Effective January 1, 2027" stays in the title. Put the date you mean first, as `YYYY-MM-DD`.
- **"14th May 2027"** (a day with "th" before the month) is read as "May 2027", the 1st. Write `14 May 2027` or
  `2027-05-14`.
- **A word that is also a short month name, right before a year, counts**: `Retiro en Viña del Mar 2027.pdf` gets
  the date March 1, 2027 ("Mar 2027").
- **Month and year only** ("March 2027 Committee Meeting") stays in the title — it is what tells the files apart —
  and dates the file on the 1st. A repeated year at the end is dropped: `March 2027 Committee Meeting 2027.pdf` →
  "March 2027 Committee Meeting".
- **A name that is only a date** keeps it as its title: `2027-03-14.pdf` → "2027-03-14".

**Which date a file gets** (code: `build_item()` and `merge()` in drive.py):

| File | Its date is the first of these that exists |
|---|---|
| documents, slides, forms, videos, bulletin posts | the date in the name → (bulletin only) the "(from …)" day → the listing date |
| pictures (anywhere except `flyers/` and the bulletin folder, where a picture is a post) | the date in the name → when the photo was taken (only with the API key) → the listing date |
| flyers | the listing date. The date in a flyer's name is the **event's** date, not the flyer's |
| none of these | the date of the previous run, else the day the site first saw the file |

The **listing date**: without the API key, the "last modified" date that Drive's folder view shows ("Oct 2",
"4/13/25"; a clock time such as "7:49 am" means a change within the last day — Drive writes it in Pacific time and
the site turns it into the Central day). With the API key: the day the file was created in Drive. (The booth
display shows no dates: a booth file is timed with `(from …)` and `(until …)`; its "last modified" only tells the
deploy that the file changed and must be copied again for offline play.)

So, without the key, **an undated file is re-dated whenever someone edits it**: it moves up on the Portfolio, can
show "New" again and comes back in What's New. Start the name with a date and that stops.

What the date changes: the card's date and its order on the Portfolio and in the Library; the "New" badge (14
days); the place in What's New (a date more than a day ahead counts from the day the site first saw the file); the
home tiles (the 6 newest); the digest month (the later of the date and the day the site first saw the file). A
table of these cases with real examples is in
[Photos, slides, reports … §4.1](photos-slides-reports.md#41-name-a-file-so-its-title-and-date-come-out-right).

Flyer names can also carry a time, a time zone and a place ([Flyers and events §4](flyers-and-events.md#4-name-a-flyer-so-it-becomes-an-event));
bulletin names can carry `(pinned)`, `(until …)` and `(from …)` ([Bulletin §3.4](bulletin.md#34-drive-name-the-file));
booth names have their own options ([§3.6](#36-the-booth-folder-new)).

> **Note:** README §2 says "A date at the start of any file name sets its date" — the code finds it anywhere in the
> name. The header of drive.py says "A date anywhere in the name sets the item date" — true except for flyers, whose
> name date is the event's date, and booth files, whose date is not used. README §10a says that without an API key
> the dates come "from the file name or the day the site first saw the file" (the comment under `drive:` in
> `config/site.yml`: "file names / first-seen"); the code uses the folder view's "last modified" date before the
> first-seen day.

### 3.9 Titles: from file name to title

What happens to a file name, in this order (code: `build_item()`, `strip_ext()`, `tidy()` and
`is_generic_media_name()` in drive.py; `fix_title()` in build_data.py). The booth folder has its own reader
([§3.6](#36-the-booth-folder-new)); flyers also make an event title ([Flyers and events §4](flyers-and-events.md#4-name-a-flyer-so-it-becomes-an-event)).

1. **A known ending is cut off**, any capitals: .pdf .doc .docx .ppt .pptx .pps .ppsx .odp .odt .rtf .txt .md .key
   .pages .jpg .jpeg .png .gif .webp .heic .heif .tif .tiff .bmp .svg .mp4 .m4v .mov .avi .wmv .webm .mkv .3gp .mp3
   .m4a .wav .ogg .zip .epub. Any other ending stays: `Notes.markdown` → "Notes.markdown".
2. **Copy marks are dropped**: "Copy of " or "Copia de " at the start, and **one** " (1)", " (2)", " copy" or
   " copia" at the end.
3. **Markers are taken out**: `(pinned)`, `(fijado)`, `(fijo)`, `(pin)` and 📌 everywhere; `(until …)`,
   `(hasta …)`, `(expires …)`, `(vence …)` — in the bulletin only when it holds a date with its year, in every other
   folder always; `(from …)`, `(desde …)`, `(publish …)`, `(publicar …)` only in the bulletin, and only with a date.
   Round or square brackets both work.
4. **The date is taken out** ([§3.8](#38-dates-in-file-names)), except a month-and-year date.
5. **Tidying**: `%20` → a space; `GV_LV`, `GV-LV` and `GV LV` → "GV/LV" (not when a letter, a digit or an
   underscore follows "LV"); underscores → spaces; double spaces → one; dashes, dots, commas, colons and the like
   trimmed at both ends.
6. **Camera and phone names** of pictures and videos (`IMG_1234`, `DSC…`, `PXL_…`, `VID_…`,
   `WhatsApp Image … at 6.33.16 PM`, `Screenshot …`, `Captura de pantalla …`, long codes, `photo`, `unnamed` …)
   become "&lt;album or folder&gt; #&lt;n&gt;", where n is the file's place among that folder's pictures and
   videos sorted by file name. Adding a file whose name sorts earlier renumbers the ones after it.
7. **The language** of the title is guessed (a Spanish folder word leans it Spanish). The other language is
   machine-translated and marked "Auto-translated" until someone writes it in `data/translations/overrides.yml`
   ([Translations §3.7.4](translations.md#374-drive-files-and-flyers-titles-only)).

Examples (each checked with `build_item()`):

| File | Title on the site |
|---|---|
| `reports/2027-02-17 Committee report.pdf` | Committee report (dated February 17, 2027) |
| `reports/Copy of 2027-02-17 Committee report (1).docx` | Committee report |
| `reports/Committee report copy.pdf`, `reports/Committee report (2).pdf` | Committee report |
| `reports/Report v2 (1) (2).pdf` | Report v2 (1) — only one copy mark is dropped |
| `Informes/Copia de Informe del comité.pdf` | Informe del comité (Spanish) |
| `reports/Committee_report_-_February.pdf` | Committee report - February |
| `reports/Committee%20report.PDF` | Committee report |
| `reports/GV_LV Report 2027-02-17.pdf`, `GV-LV Report.pdf`, `GV LV Report.pdf` | GV/LV Report |
| `reports/GV_LV_Report_2027-02-17.pdf` | GV LV Report (the underscore after "LV" blocks the slash) |
| `reports/GVLV Report.pdf` | GVLV Report |
| `reports/Committee report - .pdf` | Committee report |
| `reports/Treasurer report - March 14, 2027.pdf` | Treasurer report (dated March 14, 2027) |
| `reports/March 2027 Committee Meeting 2027.pdf` | March 2027 Committee Meeting (dated March 1, 2027) |
| `reports/2027-03-14.pdf` | 2027-03-14 |
| `notes/Policy (until further notice).pdf` | Policy — outside the bulletin every "(until …)" is dropped |
| `notes/Report (pinned).pdf` | Report — the marker is dropped; pinning does something only in the bulletin |
| `notes/Report (from 2027-03-01).pdf` | **Report (from )**, dated March 1, 2027 — "(from …)" works only in the bulletin; elsewhere its date is read and the brackets stay. Don't use it outside the bulletin |
| `notes/A message (from the Chair).pdf` | A message (from the Chair) |
| `photos/Spring Assembly 2027/IMG_0142.jpg` | Spring Assembly 2027 #1 |
| `photos/2027/Spring Assembly/IMG_0001.jpg` | 2027 / Spring Assembly #1 (the album "2027 / Spring Assembly") |
| `photos/IMG_0142.jpg` (the 4th picture in `photos/`) | Photos #4 |
| `photos/Fall Assembly/clip.mp4` | clip (only camera-like names are replaced) |
| `flyers/WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg` | Flyers #1 when it is the folder's only picture (beside today's ten flyers it would be Flyers #10) — and no event: a phone's date is when the picture was taken |

Dates are taken out of titles, so `2027-02-17 Committee report.pdf` and `2027-03-17 Committee report.pdf` both
read "Committee report" (with different dates). Add a word — "Committee report - February" — or use
"February 2027 Committee report".

### 3.10 What is never published

The rules (code: `exclusion_reason()` in drive.py; settings `exclude_mime_contains` and `exclude_name_contains`
under `drive:` in [config/site.yml](../config/site.yml)):

| Rule | Applies to | Set in |
|---|---|---|
| the type is a spreadsheet (Google Sheets, Excel, OpenDocument …), CSV, TSV, a Google Apps Script or a Google Site | files | built in (`_ALWAYS_EXCLUDE_MIME`), plus `exclude_mime_contains: ["spreadsheet"]` |
| the name contains `(Responses)`, `(Respuestas)`, `PRIVATE`, `PRIVADO` or `wrong size` — any capitals, anywhere in the name | files **and folders** (a folder is skipped with everything inside it) | `exclude_name_contains` |
| the name ends .xls .xlsx .xlsm .csv .tsv .ods .numbers .tmp .lnk .ini .db .ds_store, starts with `~$` or a dot, or is `Thumbs.db` / `desktop.ini` | files | built in (`_ALWAYS_EXCLUDE_NAME`) |

These run first, on every file and folder of every folder, the A65_GV root included.

Examples (each checked with `exclusion_reason()` and today's settings):

| Name | Result |
|---|---|
| `Sign-up (Responses)` (a Google Sheet) | never — a spreadsheet |
| `Volunteer form (Respuestas)` (a Google Form) | never — the name |
| `Spring Assembly volunteers` (the Google Form itself) | published, with a **Sign up** button |
| `budget.xlsx`, `budget.ods`, `Budget` (a Google Sheet), `quiz.tsv`, `booth questions.csv` | never — the type |
| `questions.csv` (Drive gave no type) | never — the ending |
| `PRIVATE budget.pdf`, `Privado - lista.pdf` | never — the name |
| `privately funded.pdf` | **never too**: "privately" contains "private" |
| `Notas privadas.pdf` | **published**: "privadas" does not contain "privado" |
| `flyer wrong size.png` | never — handy for a version you keep but do not want shown |
| folder `PRIVATE notes`, folder `Private` | never read, nor anything inside |
| folder `Responses` | read and published: only "(Responses)" with the brackets counts |
| `~$report.docx`, `.hidden.txt`, `Thumbs.db`, `desktop.ini`, `old.lnk`, `notes.tmp`, `data.numbers` | never — files a computer leaves behind |
| an Apps Script project, a Google Site | never — the type |

**Only the reason is recorded, never the name.** An excluded file shows up in `data/raw/drive.json` only as a count
(`stats.excluded`) and a reason (`stats.excluded_by_reason`, for example `"type text/csv": 1`), because that file and
`data/site/status.json` are public in the repository. A test checks that the name of a PRIVATE file never reaches
the data (`test_private_names_never_stored_and_last_seen_stable` in `tests/test_sync_pipeline.py`).

**The Drive folder itself stays open.** "Never published" means "never on the website". The file is still in
A65_GV, and anyone with the link can open it there. Keep private drafts, phone lists, budgets with names and form
answers out of A65_GV altogether. Adding PRIVATE to a file's name takes it off the website at the next run; it does
not hide it in Drive.

> **Note:** README §2's "Never published" list names spreadsheets, PRIVATE, PRIVADO, (Responses) and (Respuestas).
> The code also leaves out CSV and TSV files, "wrong size", Apps Script projects, Google Sites and the files a
> computer leaves behind.

### 3.11 Shortcuts

A Drive shortcut (**Organize → Add shortcut**) placed inside the panel folder publishes the file or folder it
points to. (Code: `HtmlLister._resolve_shortcut()` and `ApiLister._entry()` in drive_listing.py; the duplicate
rule in `main()` in drive.py.)

- It is filed under the folder the **shortcut** sits in: a shortcut in `flyers/` to a PDF kept elsewhere is a flyer
  — and an event, if the shortcut's name holds a day date.
- The title and the date come from the **shortcut's** name.
- The original must be shared publicly too, else its picture cannot load and its link asks for access.
- A shortcut to a **folder** is read like a folder, under the shortcut's name.
- The same file reachable twice (the original and a shortcut, both inside the panel folder) is **one** item; the
  original wins.
- A shortcut to a folder above itself (a loop) is noticed and not followed again.
- **Without the API key** the folder view only says "shortcut". One extra request asks Drive where it points (the
  answer is remembered for the next runs). The file type comes from the shortcut's **name**: `Handout.pdf` → a
  document, `Deck.pptx` → slides. A shortcut to a Google Doc, Slides file or Form has no ending in its name, so it
  becomes a plain Document card (a form then gets no **Sign up** button and no open/closed check; in the booth
  folder it is a problem). A shortcut Drive will not resolve stays listed with its own link but without a picture,
  and is tried again at the next run.
- **With the API key** Drive gives the target and its real type, so a shortcut works exactly like the file.

Tip: put Google Forms and Google Slides in the folder itself rather than as shortcuts. More:
[File types §4.14](file-types.md#414-shortcuts).

### 3.12 File descriptions and other Drive extras

Drive lets you add a **description** to a file (File information → Details), comments, stars and colours, and it
keeps a version history. The site reads **none** of these — with or without the API key. It uses the file's name,
its type, its folder, its dates (with the key also its size and, for a photo, when it was taken) and, for a
bulletin post or a booth message, the text inside the file. A caption or a summary has to be in the file name — or,
for a bulletin post, in the document.

Reading descriptions would be possible with the API key and a small code change
([§6.6](#66-other-changes-and-where-to-make-them)); the public folder view has no descriptions at all.

### 3.13 Replace, rename, move, delete

Drive is the source of truth: each run keeps what it finds and drops what is gone — with safety rules, so a Google
hiccup never empties a page. (Code: `merge()` in drive.py.) A Drive file keeps its id when you rename it, move it
or upload a new version, and the site recognises it by that id.

| You do this in Drive | At the next run | Good to know |
|---|---|---|
| upload a **new version** (right-click → File information → Manage versions → Upload new version) | the same item with the same links; if the name changed, the title follows it; an undated file takes the new "last modified" date (without the key) | the best way to replace a file: every link already shared keeps working |
| **rename** a file | the same item (same "added" day); a new title, maybe a new date or a new event | renaming so a page's search pattern no longer matches removes that page's link ([§5.3](#53-pages-that-link-one-file-by-its-name)) |
| **move** it to another folder inside the panel folder | the same item, filed again: a new category, tab, album or collection | e.g. from `notes/` to `reports/` |
| move it **out** of the panel folder, **delete** it, or put it in the **trash** | removed from the website | deleting and uploading again makes a new item: "New" again, and old links break |
| rename it to include `PRIVATE` (or another excluded word) | removed from the website | still openable in Drive |
| rename a **folder** to include `PRIVATE`, or delete the folder | every file in it removed | |
| rename the **panel folder** so it no longer matches | every Drive file removed ([§3.3](#33-how-a-panel-folder-is-recognised)) | rename it back |
| **make a copy** (Drive calls it "Copy of …") | a second item with the same title ("Copy of" is dropped) | delete the copy, or rename it |

**When nothing is removed:**

- the A65_GV root cannot be read — the whole run keeps the last good list;
- a folder answers with a sign-in page, a "request access" page, an error, or a page the site does not recognise —
  that folder's files (and those of its sub-folders) are kept exactly as they were;
- with the API key, a folder the key cannot see is not mistaken for an empty folder (the key checks the folder
  first);
- the run stopped early on its time or folder budget — the folders it did not reach are kept;
- the whole Drive step crashed — the last good list is kept and the Drive row on `/status/` shows the problem.

One file the site cannot make sense of is skipped and logged ("skipping …" in the Actions log) and stays off the
site; the others still go up. Each run's counts are in `data/raw/drive.json` → `stats.new`, `stats.removed`, `stats.kept_unverified`.

> **Note:** README §2 says "Deleting or moving a file in Drive removes it from the site on the next update." Moving
> a file to another folder inside the panel folder does not remove it: it is filed again under its new folder.

### 3.14 Limits

| Limit | Value | Beyond it |
|---|---|---|
| Files in one folder, without the API key | about 500 | at 500 entries or more the run summary notes "&lt;folder&gt; has N entries — add a GOOGLE_API_KEY secret (or split the folder) so none are missed". The public folder view may not list them all, and a file it does not list counts as gone. Split big albums into sub-folders |
| Folder depth | 6 levels below the panel folder (the category folder is level 1) | a 7th-level folder is not read; its path is noted in `stats.depth_limited` |
| Folders listed per run | 800 | the rest wait for the next run ("stopped early (time/folder budget); N folder(s) left for the next run"); their files are kept |
| Time to list the Drive | 15 minutes (the morning refresh: 5) | as above |
| Bulletin and booth texts downloaded per run | 40 in all — bulletin posts first; an unchanged file's text is reused, not downloaded again | the rest keep their old text until the next run |
| One bulletin text | 12,000 characters (a download is read up to 3 MB) | cut at the end of a line, with "…" |
| One booth message | 1,200 characters | cut with "…" |
| Files per folder with the API key | 1,000 per page, up to 50 pages | far beyond any committee folder |
| "New" badge | 14 days | |
| What's New / RSS | the newest 150 / 100 entries | older entries fall off |
| Home "Shared by the committee" | the 6 newest committee files | |

(Code: `BIG_FOLDER_WARN`, `MAX_ANNOUNCEMENT_FETCHES`, `MAX_BODY_CHARS`, `MAX_TEXT_DOWNLOAD` and the `--max-depth`,
`--max-minutes`, `--max-folders` options in drive.py; `MORNING_ARGS` in run_all.py; `TEXT_MAX` in booth_names.py;
`NEW_DAYS` and `WHATSNEW_MAX` in build_data.py.) How big a booth file may be for its offline copy is set under
`booth:` in `config/site.yml` ([Booth display](booth.md)).

### 3.15 The optional `GOOGLE_API_KEY`

Without it — the case today: `data/raw/drive.json` → `stats.mode` is `"html"` — the site reads Drive's public
folder view. With a Google API key stored as the GitHub secret `GOOGLE_API_KEY`, it asks the Drive API instead.
(Code: `ApiLister` and `DriveLister` in drive_listing.py; the secret is handed to the sync step in
`.github/workflows/update.yml`.)

| | Without the key (today) | With the key |
|---|---|---|
| An undated file's date | its "last modified" date — editing re-dates it | the day it was created in Drive — editing does not change it |
| A photo's date | the name, else "last modified" | the name, else when the photo was taken (camera data), else created |
| File sizes | unknown | known — shown on the Library cards, and used by the booth display's offline copy |
| Shortcuts | type guessed from the shortcut's name | the real target and type |
| Big folders | about 500 entries may be the limit | 1,000 per page, up to 50 pages |
| Video length | unknown | stored (no page shows it yet) |
| File descriptions | not read | not read either |

What it does **not** change: the folders must still be "Anyone with the link" (an API key only reads public
folders), and every naming rule on this page stays the same.

Safety: the key travels in a request header, never in an address, so it cannot leak into a log. On any API error
that folder is read through the public view instead; after 3 errors the API is switched off for the rest of the
run. The run summary then notes "Drive API error (used the public view instead): …" and `stats.mode` says
`"html (api failed)"`.

**Setting it up.** README §10a has the steps: a Google Cloud project signed in with the committee's Google account,
the **Google Drive API** enabled, an API key restricted to that API (free at this use). Adding the secret needs the
repository's admin account, **NETA65**: GitHub → **Settings** → **Secrets and variables** → **Actions** → **New
repository secret** → name `GOOGLE_API_KEY`. The next run uses it
([Who can do what](automation-and-troubleshooting.md#10-who-can-do-what-mkp715-and-neta65)).

---

## 4. What happens next (which run, how long)

### 4.1 Which runs read the Drive

A Drive upload, rename or delete is not a change to the GitHub repository, so **nothing starts by itself**: nothing
watches Drive. Every run of **Website update** reads the Drive — the quick runs and the full daily run alike
(`drive` is the first module of `run_all.py`, also in `QUICK_MODULES`). No other workflow reads it.

| Run | When | Drive time box | Your change is live |
|---|---|---|---|
| Morning refresh | started by the Morning check when today's update is not on the site yet (with the morning alarm: about 4:30 AM Central) | 5 minutes | about 2–3 minutes after it starts |
| Nightly full update | GitHub's schedule, set 4 hours early on purpose; GitHub usually starts it around 5–7 AM Central | 15 minutes | when the run ends, about 10–15 minutes |
| Midday refresh (quick) | GitHub's schedule; usually starts around 11 AM–1 PM Central | 15 minutes | about 2 minutes |
| Evening refresh (quick) | GitHub's schedule; usually starts around 7–9 PM Central | 15 minutes | about 2 minutes |
| After a push to `main` (settings, content, code, translation fixes — not documentation or tests) | right away (a quick run) | 15 minutes | about 2 minutes |
| By hand | GitHub → **Actions** → **Website update** → **Run workflow**: tick **skip_crawl** for a quick run (about 2 minutes); leave everything empty for a full run (10–15 minutes) | 15 minutes | as said |

GitHub Pages may take up to about 10 more minutes to show the new pages to every visitor. The scheduled runs fall
in the early morning, around midday and in the evening (Central; an hour earlier in winter), so **a file uploaded
in the morning usually shows up after the midday refresh, one uploaded in the afternoon after the evening
refresh, and one uploaded at night the next morning** — or a few minutes after any push or a run started by hand.
The MKP715 login (write access) can start a run; secrets need the
NETA65 (admin) account. Details, schedules and the run modes:
[Automation and troubleshooting §3](automation-and-troubleshooting.md#3-what-happens-next-how-fast-a-change-goes-live)
and [§4.2](automation-and-troubleshooting.md#42-website-update-and-its-three-modes).

### 4.2 What a run does with your files

1. **List.** `drive.py` reads A65_GV, finds the panel folders and lists every sub-folder (up to 6 levels, within
   its time and folder budget). The never-published rules run first on every name.
2. **Make items.** Each file becomes an item: category from the first folder, kind from the type, title and date
   from the name, album, flyer event details or booth settings. Bulletin texts and booth message texts are
   downloaded (unchanged ones reused); each Google Form is checked once (open, closed or members-only).
3. **Merge safely.** The new list is merged with the last one ([§3.13](#313-replace-rename-move-delete)) and saved
   as `data/raw/drive.json`, with its counts and notes in `stats`.
4. **Spread over the site.** `build_data.py` writes `data/site/drive.json` (Portfolio, Photos, Library, home),
   `announcements.json` (bulletin), `events.json` (flyer events), `whatsnew.json` (What's New, RSS), `booth.json`
   (booth display) and `status.json` (Status page, run summary), and translates new titles and album names. A
   title that could not be translated in this run is counted in the run summary's **Translations** line as
   "waiting for the next run" and shows in its own language until then.
5. **Commit and publish.** The data is committed ("chore(data): …"), the booth display's pictures, videos and sound
   files are copied for offline play, and the website is built and published on GitHub Pages. If the Drive step
   fails, the site is still published with the last good Drive list.

---

## 5. Where it shows on the website

### 5.1 Every place a Drive file can appear

| Place | English · Spanish | What comes from the Drive |
|---|---|---|
| Portfolio | `/portfolio/` · `/es/portfolio/` | documents, slides, sign-up forms (and the pictures and videos of document folders), one tab per folder: `#docs-reports`, `#docs-notes`, `#docs-slides`, `#docs-workshops`, `#docs-flyers`, `#docs-forms`, `#docs-folder-<name>`; **Open Drive folder** in the members' box |
| Photos | `/photos/` · `/es/photos/` | the albums of `photos/` (and of "other" folders), `#album-<name>`; **Open Drive folder** |
| Events | `/events/` · `/es/events/`; calendar files `/events.ics` · `/es/events.ics` | an event for every flyer whose name holds a day date, with **View flyer**; the flyers of monthly events and of events written on GitHub; **Open Drive folder** |
| Bulletin | `/bulletin/` · `/es/bulletin/` | the posts of the bulletin folder, beside the ones written on GitHub; **Open Drive folder** |
| Library | `/library/` · `/es/library/` | documents, slides and open forms, with the badge "NETA 65" (not pictures, videos, bulletin posts or booth files) |
| Home | `/` · `/es/` | "Shared by the committee" (the 6 newest committee files), "Upcoming events" (flyer events among them), "Bulletin" (2 posts, pinned first) |
| What's New, RSS feed | `/whats-new/` · `/es/whats-new/`; `/feed.xml` · `/es/feed.xml` | one entry per new file (2 or more photos of one album and day become one entry), new flyer events, bulletin posts |
| Search | `/search/` · `/es/search/` | the Library's documents, one entry per album, bulletin posts, events |
| Monthly toolkit | `/monthly/` · `/es/monthly/` | the number of live bulletin posts and the newest one; the "Full editorial calendar" link ([§5.3](#53-pages-that-link-one-file-by-its-name)) |
| Monthly digest | `/digest/` · `/es/digest/`, and the e-mail when it is switched on | "Committee uploads" of the month, one row per album, the month's bulletin posts and events |
| About → Booth display | `/about/#booth` · `/es/about/#booth` | the booth folder's files, and nothing else ([§3.6](#36-the-booth-folder-new)) |
| Status | `/status/` · `/es/status/` | the row "Google Drive (committee uploads)": state, number of files (booth files included), last good check |
| Committee sub-nav (the bar under the header of the committee pages) | — | the counts "Portfolio N", "Photos N", "Bulletin N" |

Every page has its Spanish twin, with the titles in Spanish: a title written in English is machine-translated
(marked "Auto-translated") until someone writes its Spanish in `data/translations/overrides.yml`, and the other way
round ([Translations](translations.md#34-fix-one-text-datatranslationsoverridesyml)).

### 5.2 Twenty uploads and where each one shows

All inside **2027-2028_Panel77_GVLV** unless noted. "The usual places" means: the home tiles while it is among the
6 newest committee files, What's New and the RSS feed (`/feed.xml`, `/es/feed.xml`), and the digest of the month it
was added (`/digest/`, and the e-mail when it is switched on).

| # | You put this in Drive | It becomes | Where you will see it |
|---|---|---|---|
| 1 | `reports/2027-02-17 Committee report - February.pdf` | a report, "Committee report - February", February 17, 2027 | `/portfolio/#docs-reports` · `/es/portfolio/#docs-reports` (Spanish title machine-made); Library; search; the usual places |
| 2 | `Informes/Informe del comité - 17 de febrero de 2027.pdf` | a report written in Spanish, February 17, 2027 | the same Reports tab; the English page shows a translation marked "Auto-translated" |
| 3 | `notes/2027-03-02 Committee meeting minutes.pdf` | meeting notes, March 2, 2027 | `/portfolio/#docs-notes`; `/meetings/` links that tab ("Agendas and past reports") |
| 4 | `slides/GVR and RLV Orientation Workshop.pptx` | slides | `/portfolio/#docs-slides` with **Present on the web**; the PowerPoint copy on `/orientation/` — its title equals that deck's `drive_title` |
| 5 | `workshops/Writing workshop handout.pdf` | a workshop file | `/portfolio/#docs-workshops`; Library; search; the usual places |
| 6 | `forms/Spring Assembly volunteers` (a Google Form) | a sign-up card | `/portfolio/#docs-forms` with **Sign up**; gone from every page while the form is closed |
| 7 | `forms/Spring Assembly volunteers (Responses)` (its answers sheet) | nothing | never published — but openable by anyone with the folder link: move it out of A65_GV |
| 8 | `flyers/2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` | a flyer **and** an event "Spring Assembly booth", March 14, 2027, 9:00 AM, Tyler Civic Center | `/portfolio/#docs-flyers` (as "Spring Assembly booth 9am @ Tyler Civic Center"); `/events/` · `/es/events/` with **View flyer**; `/events.ics`; home "Upcoming events"; search; What's New as an event |
| 9 | `flyers/Grapevine Writing Workshop - Primary Purpose Group, Arlington.png` (undated, a real one) | a flyer only | `/portfolio/#docs-flyers` and the usual places (a picture flyer is not in the Library). A `content/events` file attaches it to an event with `flyer:` ([Flyers and events §5](flyers-and-events.md#5-use-a-flyer-without-a-date)) |
| 10 | `flyers/WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg` | a flyer "Flyers #10" (its place among the folder's pictures by name: today's ten flyers and this one) — **no event** | `/portfolio/#docs-flyers` and the usual places. Rename it `2026-10-17 Writing workshop 7pm.jpeg` to make the event |
| 11 | `photos/2027 Spring Assembly/IMG_0142.jpg` and three more the same day | album photos "2027 Spring Assembly #1" … | `/photos/#album-2027-spring-assembly`; What's New "4 new photos in 2027 Spring Assembly" (linking the album); home tiles; digest "Photos: 2027 Spring Assembly"; search (the album) |
| 12 | `photos/2027 Spring Assembly/Literature display.jpg` | an album photo captioned "Literature display" | the same album |
| 13 | `bulletin/2027-01-10 Welcome new GVRs` (a Google Doc) | a post "Welcome new GVRs", January 10, 2027, with the Doc's text | `/bulletin/` · `/es/bulletin/`; home "Bulletin"; What's New + RSS (the link opens the Doc); search; digest; monthly toolkit |
| 14 | `bulletin/Spring Assembly sign-ups (from 2027-02-01).md` | a scheduled post | nowhere until February 1, 2027 (Central time); meanwhile the run summary lists it under "Scheduled bulletin posts"; it appears with the first update of that day |
| 15 | `booth/GV EN Welcome to our table (first) (15s).png` | a booth slide | the booth display only (`/about/#booth`); `/status/` counts it |
| 16 | `booth/Spring Assembly 2027/IMG_2045.JPG` | a booth photo without a caption, collection "Spring Assembly 2027" | the booth display only |
| 17 | `Archive/2025 Panel 75 summary.pdf` | an "other" file | tab "Archive" (`/portfolio/#docs-folder-archive`, the same name on the Spanish page); Library type "Other"; the digest e-mail labels the row "Files" |
| 18 | `2027-03-14 Spring Assembly.pdf` (directly in the panel folder) | an "other" file, March 14, 2027 | tab **Other** (`/portfolio/#docs-folder-other`; Spanish page: **Otros**, `#docs-folder-otros`) |
| 19 | `reports/PRIVATE budget.pdf` | nothing | never on the website — only counted in `stats.excluded_by_reason` — but still openable in Drive |
| 20 | `A65_GV/flyers/2027-03-14 Spring Assembly.pdf` (in the root, outside the panel folder) | nothing | ignored; the folder name `flyers` is listed in `stats.loose_skipped` |

### 5.3 Pages that link one file by its name

Some pages pick one committee Drive file by a rule. Rename the file so the rule no longer matches, and the link
quietly disappears (most of them use `driveMatch()` in [committee.js](../eleventy/filters/committee.js): the newest
matching file wins, in any folder unless a folder is named):

| Page | Link | The rule | Set in |
|---|---|---|---|
| Meetings `/meetings/` (chair card) | "Agendas and past reports in the Portfolio" | the notes tab when it has files; else the link stays and opens the top of the Portfolio | [meetings.njk](../src/pages/meetings.njk) |
| Meetings `/meetings/` (La Viña's weekly open meeting) | its flyer | `lavina_weekly_open.flyer_match` | [config/site.yml](../config/site.yml) |
| Share your story `/contribute/` | up to 2 printable flyers, `flyers/` only | the title or file name contains "share your story" or "comparte tu historia" | [contribute.njk](../src/pages/contribute.njk) |
| Monthly toolkit `/monthly/` | "Full editorial calendar" | the title or file name contains "editorial calendar" or "calendario editorial" | [monthly.njk](../src/pages/monthly.njk) |
| Shop `/shop/` (price-change notice) | "Read AA Grapevine's notice" | matches `price_changes[].doc_match` | [config/site.yml](../config/site.yml) |
| GVR / RLV 101 `/orientation/` and the Portfolio | "PowerPoint copy", "Present on the web" | the title equals a deck's `drive_title` | [config/presentations/](../config/presentations/README.md) |
| Events: a monthly event's dates | the flyer of each date | `recurring_events[].flyer_match` | [config/site.yml](../config/site.yml) ([Flyers and events §5](flyers-and-events.md#5-use-a-flyer-without-a-date)) |
| Events written on GitHub | **View flyer** | the `flyer:` line holds the file's Drive link | `content/events/*.md` |

More about each: [Photos, slides, reports … §6](photos-slides-reports.md#6-where-it-shows-on-the-website),
[Flyers and events](flyers-and-events.md), [Settings](settings.md).

### 5.4 Behind the scenes: the run summary and the data files

**The run summary** (GitHub → **Actions** → the newest **Website update** run → its page):

- the **Content sources** table, row "Google Drive (committee uploads)": OK or **PROBLEM** with the message, the
  number of items, new in 7 days, the last success;
- **Notes**: up to two short notes of the Drive source (for example "1 folder(s) could not be read — check their
  sharing settings", or the booth folder's files the booth display cannot show);
- **Booth folder files the booth display can't show**: each file of `data/site/booth.json` → `problems`, with its
  reason ([§3.6](#36-the-booth-folder-new));
- **Scheduled bulletin posts**: each "(from …)" post with "(Google Drive: &lt;file name&gt;)";
- the module table: `drive` with its time, items and new ones;
- **Booth display (copies for offline)**, written by the publishing job: how many booth files are saved for offline
  play, and each one that is not ("Not saved: …"), with why.

Reading the run summary, section by section:
[Automation and troubleshooting §6.3](automation-and-troubleshooting.md#63-the-website-update-summary-section-by-section).

**`data/raw/drive.json`** (in the public repository) holds every Drive item and, near the top, `stats`:

| Field | Tells you |
|---|---|
| `mode` | `"html"` (the public folder view, today), `"api"` (the API key), `"html (api failed)"` |
| `root`, `panels`, `panel_folders` | the root folder's name; the panel folders found, with their labels and ids |
| `include_loose`, `loose_skipped`, `skipped_panels` | the loose setting; the loose names skipped (first 30); the older panels skipped |
| `folders`, `files`, `fetched` | folders read; files in the list (bulletin posts, booth files and closed forms included); files listed in this run |
| `new`, `removed`, `kept_unverified` | this run's arrivals, removals, and files kept because their folder could not be read |
| `by_category`, `by_kind`, `albums` | counts per folder kind, per file kind, per album |
| `events_from_flyers` | how many flyers carry an event date |
| `excluded`, `excluded_by_reason` | never-published files: the count and the reasons (never the names) |
| `unreadable_folders`, `depth_limited` | folders that could not be read (with the reason); folders deeper than 6 levels |
| `shortcuts_resolved` | shortcuts looked up in this run |
| `announcements`, `booth_texts`, `forms` | text downloads (fetched, reused, file only, deferred, failed); the booth messages' downloads (only when there are any); form checks (open, closed, members-only, unknown) |
| `requests`, `truncated`, `warnings` | requests made; whether the run stopped early; the notes the run summary shows |

`data/site/drive.json` holds the files as the pages use them (titles in both languages, "New" flags), without
bulletin posts, closed forms and booth files; `data/site/booth.json` holds the booth display's files and problems;
`data/site/status.json` feeds `/status/`.

---

## 6. Going further: change the code

Edit files on GitHub (or on your PC and push). A login with write access (MKP715) can commit; repository settings
and secrets need the NETA65 (admin) account. A push to `main` starts a quick update — which also reads the Drive —
and a Code check that runs the tests; if the build fails, the old site stays up and the error is in the run log.
Line numbers change all the time, so this guide names files, functions and settings to search for instead.

### 6.1 The chain from Drive to page

```
Google Drive: A65_GV (public folder view, or the Drive API with GOOGLE_API_KEY)
  │   scripts/sync/drive_listing.py   DriveLister.list() → HtmlLister.list() + parse()   or   ApiLister.list()
  ▼
scripts/sync/drive.py   main()
  crawl()              panel folders (panel_label), loose names, exclusion_reason(), depth / time / folder budgets
  build_item()         category_for(), kind_for(); title and date: strip_ext(), tidy(), name_date();
                       album; flyer event: extract_time_zone(), extract_location();
                       booth: booth_names.parse_booth_name()
  fill_announcements(), fill_booth_texts()   texts of bulletin posts and booth messages
  check_forms()        open / closed / members-only Google Forms
  merge()              the safety rules  ──►  data/raw/drive.json  (items + stats)
  ▼
scripts/sync/build_data.py   main()
  Ctx.items("drive")   every Drive item except the booth folder's      Ctx.booth_items()   the booth folder's
  simple()                    ──► data/site/drive.json        (Portfolio, Photos, Library, home, search, digest)
  build_announcements()       ──► data/site/announcements.json (bulletin)
  flyer_events(), build_events() ──► data/site/events.json    (events, calendar files)
  plan_whatsnew(), finish_group() ──► data/site/whatsnew.json (What's New, RSS)
  build_booth()               ──► data/site/booth.json         (booth display)
  build_status()              ──► data/site/status.json        (Status page, run summary)
  ▼
Eleventy: src/_data/db.js reads data/site/ (booth.json: src/_data/booth.js)  →  filters in eleventy/filters/
  (committee.js: documentTabs(), photoAlbums(), driveMatch(), driveInfo(); library.js; home.js; community.js;
  booth.js)  →  pages in src/pages/ (portfolio.njk, photos.njk, events.njk, bulletin.njk, library.njk, index.njk,
  whats-new.njk, about.njk …)  →  GitHub Pages
```

### 6.2 Code map

| File | Look for | What it does |
|---|---|---|
| [scripts/sync/drive.py](../scripts/sync/drive.py) | `main()` and its options (`--include-loose`, `--root`, `--max-depth`, `--max-minutes`, `--max-folders`, `--no-api`, `--dry-run`) | one Drive run, start to end; writes `data/raw/drive.json` and its `stats` |
| | `crawl()`, `_add_files()`, `panel_label()`, `Panel`, `Found`, `Crawl` | walks A65_GV: panel folders, loose names, depth, budgets, unreadable folders |
| | `exclusion_reason()`, `_ALWAYS_EXCLUDE_MIME`, `_ALWAYS_EXCLUDE_NAME` | never published |
| | `CATEGORY_SYNONYMS`, `_norm()`, `category_for()`, `_SPANISH_HINTS`, `lang_prior()` | folder name → category; Spanish hint |
| | `kind_for()`, `file_type_label()`, `urls_for()`, `_NATIVE`, `_KNOWN_EXT` | file kind, type label, open / preview / download / picture links |
| | `build_item()`, `strip_ext()`, `tidy()`, `name_date()`, `_drop_repeated_year()`, `_COPY_PREFIX`, `_COPY_SUFFIX`, `_PINNED`, `_UNTIL`, `_FROM`, `is_generic_media_name()`, `_GENERIC_WORDS` | one file → one item: category, kind, title, date, album, markers, camera names |
| | `extract_time_zone()`, `extract_location()`, `_PLACE`, `_ZONE_AFTER` | a flyer's time, time zone and place ([Flyers and events](flyers-and-events.md)) |
| | `fill_announcements()`, `fill_booth_texts()`, `text_langs()`, `body_url()`, `fetch_body()`, `docx_to_text()`, `normalize_body()`, `_decode()` | the texts of bulletin posts and booth messages |
| | `check_forms()`, `merge()` | form checks; the safety rules |
| | `MAX_BODY_CHARS`, `MAX_TEXT_DOWNLOAD`, `MAX_ANNOUNCEMENT_FETCHES`, `BIG_FOLDER_WARN` | the limits of [§3.14](#314-limits) |
| [scripts/sync/drive_listing.py](../scripts/sync/drive_listing.py) | `DriveLister` (`list()`, `mode`, `MAX_API_FAILURES`) | uses the API when the key exists, else (or after errors) the public view |
| | `HtmlLister` (`list()`, `parse()`, `_parse_entry()`, `_resolve_shortcut()`) | the public "embedded folder view"; refuses sign-in and unknown pages |
| | `ApiLister` (`check_folder()`, `list()`, `_entry()`), `API_FIELDS` | the Drive API: dates, sizes, camera times, shortcut targets |
| | `parse_modified_text()`, `clock_text_day()`, `local_today()`, `guess_mime()`, `Entry`, `Listing` | the "last modified" text → a date; a type from a file ending |
| [scripts/sync/booth_names.py](../scripts/sync/booth_names.py) | `parse_booth_name()`, `media_type()`, `_leading()`, `_read_group()`, `_WORD_OPTIONS`, `message_text()`, `problem_of()`, `PROBLEMS`, `TEXT_MAX` | the booth naming convention ([§3.6](#36-the-booth-folder-new)) |
| [scripts/sync/common.py](../scripts/sync/common.py) | `date_from_text()`, `MONTHS`, `make_item()`, `save_raw()`, `run_module()` | dates in names, the item shape, writing a raw file, a crash never stops the run |
| [scripts/sync/build_data.py](../scripts/sync/build_data.py) | `Ctx` (`items()`, `booth_items()`, `effective_ts()`, `is_new()`) | the raw data; the booth filter; the What's New date; the "New" badge |
| | `simple()`, `closed_form()`, `prep()`, `fix_title()` | `data/site/drive.json` |
| | `build_announcements()` · `flyer_events()`, `series_flyers()`, `pick_flyer()`, `series_dated_flyers()`, `build_events()` · `plan_whatsnew()`, `album_slug()`, `finish_group()` · `build_booth()`, `booth_item()`, `booth_stamp()` · `build_status()` · `text_fields()` | the bulletin, events, What's New, booth and status files; what gets translated |
| [scripts/sync/run_all.py](../scripts/sync/run_all.py) | `MODULES`, `QUICK_MODULES`, `MORNING_ARGS` | the Drive is read in every run mode; the morning refresh gives it 5 minutes |
| [eleventy/filters/committee.js](../eleventy/filters/committee.js) | `DOC_TABS`, `isDocItem()`, `isPhotoItem()`, `documentTabs()`, `photoAlbums()`, `photoAlbumKey()`, `driveMatch()`, `driveInfo()` | Portfolio tabs, albums, pages that link one file, the **Open Drive folder** link and the panel label |
| [eleventy/filters/library.js](../eleventy/filters/library.js) | `CATEGORIES`, `catLabel()`, `docKitType()`, `collectionsFor()` | Library types and collections, the search index |
| [scripts/notify/send_digest.py](../scripts/notify/send_digest.py) | `DRIVE_CATEGORIES` | the digest e-mail's row label per folder kind |
| [.github/workflows/update.yml](../.github/workflows/update.yml) | "Decide what to sync", the sync step (`GOOGLE_API_KEY`), the run summary step | when the Drive is read, the secret, what the summary shows |
| [config/site.yml](../config/site.yml) | `drive:` (`root_folder_id`, `panel_folder_pattern`, `min_panel`, `include_loose_folders`, `exclude_mime_contains`, `exclude_name_contains`), `booth:` | the settings ([Settings](settings.md#35-drive--the-committees-google-drive)) |

### 6.3 Try a rule on your PC first

These commands only read; run them from the repository folder with the project's Python (setting it up:
[Automation and troubleshooting §11.1](automation-and-troubleshooting.md#111-one-time-setup)). The answers shown
are the real ones.

```powershell
python -c "from scripts.sync.drive import category_for; print(category_for('Fotos del taller'))"
# photos

python -c "from scripts.sync.common import date_from_text; print(date_from_text('Report 05-03-2027'))"
# ('2027-05-03', 'Report')        US order: May 3

python -c "from scripts.sync.booth_names import parse_booth_name; print(parse_booth_name('GV EN Welcome (first) (15s).png', 'image/png', ['booth']))"
# {'kind': 'poster', 'pub': 'gv', 'langs': ['en'], 'title': 'Welcome', 'caption': True, 'order': None, 'seconds': 15, …
#  'first': True, … 'collection': 'main', 'collection_label': 'Booth folder', 'text': None, 'problem': None}

python -m scripts.sync.drive --dry-run
# reads the real Drive and prints the stats and three items; writes nothing
```

You can even try a new folder word before editing any file — the change lives only in that one command:

```powershell
python -c "from scripts.sync import drive as D; D.CATEGORY_SYNONYMS['letters'] = ['letter', 'letters', 'carta', 'cartas', 'correspondence', 'correspondencia']; print([D.category_for(n) for n in ['Cartas', 'Letters 2027', 'Cartas y notas', 'Notas y cartas', 'Newsletter']])"
# ['letters', 'letters', 'letters', 'notes', None]
```

### 6.4 Worked example: a new category folder, end to end

**Goal:** the committee keeps letters — AA Grapevine's letters to Intergroups and Central Offices, La Viña's, and
its own letters to the groups. Today a folder called `Cartas` would be an "other" folder: a Portfolio tab named
"Cartas" on both pages, Library type "Other", "Files" in the digest e-mail. We want a real category `letters`: a
built-in tab **Letters / Cartas**, its own Library type, its own label in the digest e-mail, and the folder names
`letters`, `cartas`, `correspondence` and `correspondencia` in either language.

**Step 1 — the folder words** ([scripts/sync/drive.py](../scripts/sync/drive.py), `CATEGORY_SYNONYMS`). Add a
line at the end of the dictionary, after `"booth"`. Words in lower case, without accents (the matcher removes
accents and capitals first):

```python
    # letters from AA Grapevine and La Viña, and the committee's letters to the groups
    "letters": ["letter", "letters", "carta", "cartas", "correspondence", "correspondencia"],
}
```

In the same file add the Spanish words to `_SPANISH_HINTS` (titles in such a folder are then read as Spanish
first): `"carta", "cartas", "correspondencia",`.

Choose words that cannot catch other folders. Whole words protect `Newsletter` (it stays "other"), and when two
category words meet, the first one wins: `Cartas y notas` → letters, `Notas y cartas` → notes ([§6.3](#63-try-a-rule-on-your-pc-first)).

**Step 2 — the data: nothing to change.** `build_item()` now gives a file in `Cartas/` the category `letters`, and
`simple()` in build_data.py puts it in `data/site/drive.json` like any committee file. What's New, the RSS feed,
the home tiles, the Library, search and the digest take it as they take any Drive file. Check with
`python -m scripts.sync.drive --dry-run` once a `Cartas` folder exists in the panel folder: `by_category` shows
`"letters"`.

**Step 3 — the Portfolio tab** ([eleventy/filters/committee.js](../eleventy/filters/committee.js), `DOC_TABS`).
Add the tab where it should appear, with any [Lucide](https://lucide.dev/icons/) icon name:

```js
  { key: "workshops", icon: "pen-line" },
  { key: "letters", icon: "mail-open" },
  { key: "flyers", icon: "megaphone" },
```

Without this step the files would still show — in a tab named after the folder, because `documentTabs()` treats a
category without a tab like an unknown folder. Either way, a picture in this folder is an "Image" card on the
Portfolio, not an album photo (`isPhotoItem()` makes albums only from `photos` and "other" folders).

**Step 4 — the words on the page** ([src/_i18n/committee.json](../src/_i18n/committee.json)). The tab's name and
the line under it, and the label for the members' box (step 5), in both languages:

```json
  "committee.docs.cat.letters": { "en": "Letters", "es": "Cartas" },
  "committee.docs.cat.letters_desc": {
    "en": "Letters from AA Grapevine and La Viña, and our letters to the groups",
    "es": "Cartas de AA Grapevine y La Viña, y nuestras cartas a los grupos"
  },
  "committee.docs.goes_letters": { "en": "Letters", "es": "Cartas" },
```

A missing key stops the build on GitHub (it builds in strict mode), so add all three before you push.

**Step 5 — the members' box** ([src/pages/portfolio.njk](../src/pages/portfolio.njk)). In the folder list of "For
committee members · How to add documents" (search `["reports", "informes", "file-bar-chart"]`) add
`["letters", "cartas", "mail-open"]`.

**Step 6 — the Library** ([eleventy/filters/library.js](../eleventy/filters/library.js), `CATEGORIES`, and
[src/_i18n/library.json](../src/_i18n/library.json)). Add `["letters", "mail-open"]` to `CATEGORIES` before
`["other", "file-text"]` (the place sets the order in the Library's type list), and the type's name:

```json
  "library.cat.letters": { "en": "Letters", "es": "Cartas" },
```

Without them the Library prints "Letters" on both pages (made from the key by `catLabel()`), with a plain icon.

**Step 7 — the digest e-mail** ([scripts/notify/send_digest.py](../scripts/notify/send_digest.py),
`DRIVE_CATEGORIES`). Add `"letters": ("Letters", "Cartas"),` — without it the e-mail labels these rows "Files" /
"Archivos".

**Step 8 — tell people.** The folder lists in the header of drive.py, the comment above `drive:` in
`config/site.yml`, README §2 (the folder tree), the `drive` row of `docs/DATA_SCHEMA.md`, the members' note
`committee.docs.folders_note` (both languages) and the table in [§3.5](#35-the-category-folders) of this guide.

**Step 9 — a test.** For example a new file `tests/test_letters_folder.py`:

```python
import unittest

from scripts.sync.drive import category_for


class LettersFolder(unittest.TestCase):
    def test_folder_names(self):
        for name in ("letters", "Cartas", "Letters 2027", "Correspondencia"):
            self.assertEqual(category_for(name), "letters", name)
        self.assertIsNone(category_for("Newsletter"))
```

Then run all the tests: `python -m unittest discover -s tests` (`tests/test_i18n_keys.py` checks that the new
words exist in both languages).

**Step 10 — push and look.** The push starts a quick run, which reads the Drive. A `Cartas` folder's files leave
the tab "Cartas" (`#docs-folder-cartas`) and appear in the new tab `/portfolio/#docs-letters` ·
`/es/portfolio/#docs-letters`; the Library lists them as "Letters" / "Cartas". Links someone saved to
`#docs-folder-cartas` now open the top of the Portfolio. If the real Pricing Update letter moves from `notes/` to
`Cartas/`, the Shop's notice keeps its link: `doc_match` looks at every Drive file, whatever its folder.

### 6.5 A category with a page of its own: the booth as the model

When a new folder kind must **not** reach the Portfolio, Photos, What's New or the digest — because it feeds a page
of its own — follow what the booth folder does:

1. **The words:** `CATEGORY_SYNONYMS["booth"]` and the Spanish words in `_SPANISH_HINTS` (drive.py).
2. **The item:** in `build_item()`, the block `if category == "booth":` reads the name with
   `booth_names.parse_booth_name()` into `extra.booth` (plus `extra.modified`), and takes the title from it.
3. **The extras:** `fill_booth_texts()` downloads message texts with the bulletin's own `fetch_body()` and
   `normalize_body()`, within the same per-run budget; `check_forms()` skips the folder; `main()` adds a note about
   files that can never be shown (`problem_of()`) and `stats.booth_texts`.
4. **Keep it out of everything else:** `Ctx.items()` in build_data.py drops the category `booth` from the Drive
   list that every other builder reads; `Ctx.booth_items()` returns only those files.
5. **Its own data file:** `build_booth()` and `booth_item()` make `data/site/booth.json`; `main()` writes it (an
   empty one from `empty_booth()` if building it fails, so the build never stops). `build_status()` still counts
   the files with the Drive source, and the run summary step in update.yml lists the file's `problems`.
6. **Its page:** `src/_data/booth.js` (with `loadBooth()` in `eleventy/filters/booth.js`, which also checks the
   captions and notes for the words the booth never shows) reads the file; `src/pages/booth-json.11ty.js`
   publishes `/about/booth.json`; `src/_includes/macros/booth.njk` puts the section on `src/pages/about.njk`; the
   player is `src/assets/js/booth-core.js` and `booth.js`; the build step `scripts/build/booth-media.mjs` (in
   update.yml) saves the files for offline play.
7. **Its tests:** `tests/test_booth_names.py` (the names) and `tests/test_booth_sync.py` — its class `Exclusion`
   checks that a booth file reaches no other site file.

### 6.6 Other changes and where to make them

| I want to … | Change | Good to know |
|---|---|---|
| accept another word for an existing folder kind (`Agendas` → notes) | `CATEGORY_SYNONYMS` (+ `_SPANISH_HINTS`) in drive.py | recipes: [Photos, slides, reports … §7](photos-slides-reports.md#7-going-further-change-the-code), [Bulletin §6](bulletin.md#6-going-further-change-the-code) |
| never publish another word | `exclude_name_contains` under `drive:` in config/site.yml — no code | a plain "contains" test: `DRAFT` also hides `Drafting your report.pdf` |
| never publish another file type | `exclude_mime_contains` (config); the built-in lists `_ALWAYS_EXCLUDE_MIME`, `_ALWAYS_EXCLUDE_NAME` (drive.py) | removing `"spreadsheet"` from the config does not publish spreadsheets: the built-in list still has it |
| read another date form | the patterns in `date_from_text()` and the month words `MONTHS` (common.py) | shared by every Drive file, the `content/bulletin` and `content/events` files and the booth's `(from …)` / `(until …)` |
| accept another marker word, e.g. "(fixed)" | `_PINNED`, `_UNTIL`, `_FROM` in drive.py | [Bulletin §6.1](bulletin.md#61-recipe-accept-destacado-as-a-pin-word) |
| another booth option word | `_WORD_OPTIONS`, `_LANG_WORDS`, `_SECONDS`, `_MINUTES`, `_FROM`, `_UNTIL` in booth_names.py | keep its header table and `tests/test_booth_names.py` in step |
| caption more camera names | `_GENERIC_WORDS` / `is_generic_media_name()` in drive.py | the same test decides whether a flyer is a phone picture (no event) and whether a booth file gets no caption |
| change a limit | `BIG_FOLDER_WARN`, `MAX_ANNOUNCEMENT_FETCHES`, `MAX_BODY_CHARS`, `MAX_TEXT_DOWNLOAD`, the defaults of `--max-depth` / `--max-minutes` / `--max-folders` in `main()` (drive.py); `MORNING_ARGS` (run_all.py); `TEXT_MAX` (booth_names.py) | a bigger time box makes every run longer |
| recognise panel folders differently | `panel_folder_pattern`, `min_panel` (config — no code); the label: `panel_label()` | [Settings](settings.md#35-drive--the-committees-google-drive) |
| read Drive's file descriptions | API key only: `API_FIELDS`, `Entry` and `ApiLister._entry()` in drive_listing.py, then `build_item()` (for example as the item's `summary`) | the public folder view has no descriptions; adding the secret needs NETA65 |
| other picture sizes | `urls_for()` in drive.py (`=w600` thumbnails, `=w1600` pictures); `BOOTH_IMAGE` / `BOOTH_THUMB` in build_data.py | |
| read more from a flyer's name | `extract_time_zone()`, `extract_location()`, `_PLACE` | [Flyers and events §13](flyers-and-events.md#13-going-further-change-the-code) |
| list the booth folder in the Portfolio's members' box | the folder list in portfolio.njk + a `committee.docs.goes_booth` string; `committee.docs.folders_note` | today that box lists eight folders and not the booth |
| change the order of the Portfolio tabs | `DOC_TABS` in committee.js | unknown folders always follow, A to Z |

### 6.7 Tests to run

From the repository folder, with the project's Python:

```powershell
python -m unittest discover -s tests
```

The ones closest to this page: `tests/test_sync_pipeline.py` (the Drive: private names never stored, an API answer
for a hidden folder, unresolved shortcuts), `tests/test_booth_names.py` and `tests/test_booth_sync.py` (the booth
names; booth files kept out of every other file), `tests/test_bulletin.py` (the bulletin folder names),
`tests/test_i18n_keys.py` (words in both languages), `tests/test_send_digest.py` and `tests/test_digest_parity.py`
(the digest page and the e-mail must pick the same items; the second needs Node.js, else it is skipped). More: [Automation and troubleshooting §11.4](automation-and-troubleshooting.md#114-run-the-tests).

---

## 7. Troubleshooting

### 7.1 Where to look

1. **The run summary** — GitHub → **Actions** → the newest **Website update** run: the "Content sources" row
   "Google Drive (committee uploads)" (OK, or **PROBLEM** with the message), the **Notes** below the table, the
   module table (`drive`: items, new) and, for the booth folder, **Booth folder files the booth display can't show**
   and **Booth display (copies for offline)**.
2. **`/status/`** (`/es/status/`): the row "Google Drive (committee uploads)": state, number of files, last good
   check.
3. **`data/raw/drive.json`** on GitHub: search it for your file name (each item keeps the original name in
   `extra.name`, with its `category`, `kind`, `title` and `date`). Its `stats` near the top: `loose_skipped`,
   `skipped_panels`, `excluded_by_reason`, `unreadable_folders`, `depth_limited`, `warnings`
   ([§5.4](#54-behind-the-scenes-the-run-summary-and-the-data-files)).
4. **The page itself.** On an empty Portfolio, Photos or Bulletin page (on Events: when it lists no upcoming
   "NETA 65 events"), the **For committee members** box says "We checked the committee's Google Drive on &lt;date&gt; — nothing
   here yet." — or, after a failed check, "The last check of the committee's Google Drive had a problem — the last
   good check was on &lt;date&gt;."
5. **The issue** "A content source has stopped updating" opens by itself after 7 days of Drive failures
   ([Automation and troubleshooting §8.1](automation-and-troubleshooting.md#81-a-content-source-has-stopped-updating)).

### 7.2 A file does not show: check in this order

1. **Has a run read the Drive since the upload?** Actions → the newest Website update run must have started after
   the upload. If not, start one ([§2.1](#21-put-a-file-on-the-website), step 4).
2. **Did that run read the Drive?** The Drive row says OK. **PROBLEM** "root folder unreadable …" → the sharing of
   A65_GV ([§3.2](#32-sharing-anyone-with-the-link-is-required)).
3. **Is the file inside a panel folder?** Its path must be A65_GV › 2027-2028_Panel77_GVLV › (a folder) › the file.
   The A65_GV root and older panel folders are skipped (`stats.loose_skipped`, `stats.skipped_panels`).
4. **Is it never published?** Its name — or the name of a folder above it — contains `PRIVATE`, `PRIVADO`,
   `(Responses)`, `(Respuestas)` or `wrong size`, or it is a spreadsheet, CSV or TSV ([§3.10](#310-what-is-never-published)).
   `stats.excluded_by_reason` counts it (never by name).
5. **Could its folder be read?** `stats.unreadable_folders` and the run summary's Notes. Is it more than 6 folder
   levels deep? `stats.depth_limited`.
6. **Is it in `data/raw/drive.json`?** If it is, the Drive part worked: look at its `category`, `kind`, `title`
   and `date` there.
7. **Are you looking in the right place?** The folder decides the page ([§3.5](#35-the-category-folders),
   [§5.1](#51-every-place-a-drive-file-can-appear)):
   - a picture in `reports/` is an "Image" card on the Portfolio, not a photo on `/photos/`;
   - a PDF in `photos/` is only on the home tiles, in What's New and in the digest;
   - a file in a folder whose first category word is a booth word (`Booth photos`) is only on the booth display;
   - a Google Form that stopped accepting answers is on no page;
   - a bulletin post with `(from …)` waits for its day; a flyer event whose day is over leaves `/events/`;
   - a file whose name dates it more than 14 days back gets no "New" badge and may be too far down What's New.
8. **Is your browser showing an old page?** GitHub Pages can take about 10 minutes; reload. The installed app may
   show its saved copy until it is online again.
9. **Still nothing?** Open the run's log (step "Sync sources and translate") and search for the file name: "skipping …"
   names a file the site could not read.

### 7.3 Symptom, cause, fix

| Symptom | Cause | Fix |
|---|---|---|
| Nothing new from Drive for days; `/status/` shows a problem for the Drive | A65_GV is no longer "Anyone with the link", or `drive.root_folder_id` changed | share A65_GV "Anyone with the link — Viewer"; meanwhile the site keeps the last good list |
| Every Drive file vanished at once | the panel folder was renamed so it no longer matches, moved into another folder, or `min_panel` was raised; Notes: "no Panel folder >= 77 found in the root folder" | rename or move it back ([§3.3](#33-how-a-panel-folder-is-recognised)); the files return at the next run |
| Every file shows twice | a second folder with the panel's name in A65_GV (a backup, an old copy) | delete it or move it out of A65_GV |
| New uploads in one folder never show, and deleted ones stay | that folder cannot be read; Notes: "N folder(s) could not be read — check their sharing settings" | give it the same sharing as A65_GV; `stats.unreadable_folders` names it |
| The file sits in a tab named after its folder, not in Reports or Meeting notes | the folder name has no category word (`Agendas`, `Training` …) | rename the folder (`Meeting Notes and Agendas`) or add the word ([§6.6](#66-other-changes-and-where-to-make-them)) |
| Pictures of the booth are not on `/photos/` | their folder's first category word is a booth word (`Booth photos`), so they feed the booth display only | put them in `photos/`, e.g. `photos/2027 Booth at CityWide/` |
| A booth file never plays | it is a problem (the run summary's "Booth folder files the booth display can't show", `data/site/booth.json` → `problems`); its caption or note says a word the booth never shows, or it is a video or sound file the deploy could not save for offline play (both named in the player's Settings → Slides); it is switched off (`(off)`, a name starting with `_` or `~`); its `(from …)` day has not come or its `(until …)` day is over; or the player's settings leave out its language, magazine or collection | [§3.6](#36-the-booth-folder-new); the player's settings: [Booth display](booth.md) |
| A booth picture marked `(x3)` comes up no more often than the others | with only a few pictures and videos, each one already comes back as often as the show's rules let it | nothing to fix: the mark counts once the show has more of them (online, or a bigger folder) |
| The date is wrong, or the file jumped to the top | no date in the name (the "last modified" date is used, and editing changes it), a date the site does not read (`14-03-2027`, `2027-01`), or US order (`05-03-2027` = May 3) | start the name with `YYYY-MM-DD` ([§3.8](#38-dates-in-file-names)) |
| Two cards look exactly alike | the date was taken out of both titles | add a word, or use "February 2027 …" ([§3.9](#39-titles-from-file-name-to-title)) |
| An icon tile instead of the picture | the file is not public, Drive has not made its preview yet, or an unusual format | check the sharing; wait a day; save the picture as JPG or PNG |
| A shortcut is a plain "Document" card, without a picture or **Sign up** | without the API key the type comes from the shortcut's name; or Drive did not resolve it | put the file itself in the folder ([§3.11](#311-shortcuts)) |
| A link on Meetings, Shop, Monthly or Share your story is gone | the file was renamed so the page's rule no longer matches | rename it back, or change the rule ([§5.3](#53-pages-that-link-one-file-by-its-name)) |
| The Spanish (or English) title is wrong | machine translation | an entry in `data/translations/overrides.yml` ([Translations](translations.md#374-drive-files-and-flyers-titles-only)) |
| A file I hid with PRIVATE still opens from an old link | "never published" means off the website only | move the file out of A65_GV |

Problems that belong to one folder kind are in its own guide: [Flyers and events](flyers-and-events.md),
[Bulletin](bulletin.md), [Photos, slides, reports …](photos-slides-reports.md#8-troubleshooting),
[Booth display](booth.md).

### 7.4 Messages and what they mean

| Message | Where | What to do |
|---|---|---|
| "root folder unreadable: &lt;reason&gt; — is it shared as 'Anyone with the link'?" | run summary (**PROBLEM**, yellow warning "previous items kept"); `/status/` | share A65_GV "Anyone with the link — Viewer"; check `drive.root_folder_id` |
| "drive.root_folder_id is not set in config/site.yml" | the same | put the folder id back in `config/site.yml` |
| "no Panel folder >= 77 found in the root folder" | Notes | a panel folder was renamed, moved or not created yet ([§3.3](#33-how-a-panel-folder-is-recognised)) |
| "N folder(s) could not be read — check their sharing settings" | Notes | `stats.unreadable_folders` names each folder and why: "not shared publicly (Google asks to sign in)", "not found or not shared publicly (HTTP 404)", "request access page", "unexpected page (not a public folder, or Drive changed its markup)", "network error (no response)" |
| "&lt;folder&gt; has N entries — add a GOOGLE_API_KEY secret (or split the folder) so none are missed" | Notes | split the folder into sub-folders, or ask NETA65 to add the key ([§3.15](#315-the-optional-google_api_key)) |
| "stopped early (time/folder budget); N folder(s) left for the next run" | Notes | nothing, unless it repeats for a week; their files are kept meanwhile |
| "Drive API error (used the public view instead): &lt;message&gt;" | Notes; `stats.mode` = `"html (api failed)"` | check the key in Google Cloud (Drive API enabled, key restricted to it) — a NETA65 task |
| "booth folder: N file(s) the booth display cannot show — …" | Notes | `data/site/booth.json` → `problems` says why for each file; rename, convert or replace it ([§3.6](#36-the-booth-folder-new)) |
| **Booth folder files the booth display can't show** (one line per file), ⚠ "Booth folder file to fix" | run summary; Annotations | each line names the file and what is wrong: rename, convert or replace it in the Drive booth folder ([§3.6](#36-the-booth-folder-new)) |
| ⚠ "Booth display: a file was not saved for offline" | Annotations; the run summary's "Booth display (copies for offline)" lines | too big (over `booth.max_file_mb`), over the folder's limit (`booth.max_total_mb`), Drive's "too many downloads" page, or no answer; a failed download is tried again by the next run. Until it is saved, a video or sound file is left out of the show and a picture shows only online |
| "left out of the booth: it says “…”" | the player's Settings → Slides; the log of *Build the website* (`[booth] …`) | its caption or note says a word the booth never shows: rename the file or change the note ([§3.6](#36-the-booth-folder-new)) |
| "announcement '…': could not download text", "booth message '…': Drive returned an HTML page instead of the file" | the Actions log | the file is not public, or Drive refused the download; the last good text is kept, and the next run tries again |
| "skipping '…': …" | the Actions log | the site could not read that file; rename it, or upload it again as PDF |

---

## 8. Good practice and AA principles

- **Everything in A65_GV is public.** The folder is shared "Anyone with the link", the website's **Open Drive
  folder** buttons open the panel folder for every visitor, and A65_GV's own address is in the public
  repository. "Never published" only keeps a file off the website. Keep private drafts, phone lists, budgets with
  names, expense records and form answers out of A65_GV altogether — today's CSV file and the "(Responses)"
  spreadsheet in the A65_GV root can be opened by anyone with the folder's link.
- **Anonymity first.** Upload only pictures in which no AA member can be recognized: tables, literature, rooms,
  signs (Tradition Eleven: personal anonymity at the level of press, radio and films — a public website included).
  No full names anywhere: not on name tags or signs in a picture, not in file names, captions, minutes, reports or
  sign-in sheets. Use a first name and last initial, or the service position ("the district's GVR").
- **A file name is public.** It becomes the title on the site and is stored in the public repository
  (`data/raw/drive.json`) — and so are some names the site does not show: loose files and folders in the A65_GV
  root, older panel folders, and the paths of folders that could not be read or were too deep. Excluded files
  (PRIVATE, spreadsheets …) are the exception: only the reason is stored. The text of a bulletin post or a booth
  message is stored there too as soon as the site reads it — even before its `(from …)` day. A name that was
  published once stays in the repository's history until a history clean-up.
- **The booth folder's own rules.** Photos of tables, displays and rooms only; no Grapevine or La Viña logos, covers,
  artwork or cartoons, and none of their audio or video files — official videos go into the booth CSV as YouTube
  links; only material the committee made or may use ([Booth display](booth.md)).
- **Whose account owns the files.** Drive's own viewer page (Preview, Open) can carry, in its page data, the e-mail
  address of the Google account that owns the file. Upload with the committee's Google account, or transfer
  ownership of the files to it — the file ids, and so every link on the site, stay the same.
- **Location data.** A phone picture can carry the place where it was taken, and anyone with the folder link can
  download the original. Remove the location before uploading when it matters.
- **Sign-up forms** ask only what is needed; the answers are personal information and belong outside A65_GV.
- **Attraction rather than promotion.** Plain, factual titles and captions ("Literature display at the Spring
  Assembly"); no sales talk.
- **Upload access** is a Drive permission: give Editor access to the people who need it, and remove it when a
  service term ends.
- **Old panels can stay.** The site reads every panel folder whose number is `min_panel` (today 77) or higher;
  older panel folders can stay in Drive — they are skipped (only their folder names are listed in
  `data/raw/drive.json`).

---

## 9. See also

- [How-to guide index](README.md) · [File types](file-types.md) · [Booth display](booth.md)
- [Flyers and events](flyers-and-events.md) · [Bulletin](bulletin.md) ·
  [Photos, slides, reports, notes, workshops and sign-up forms](photos-slides-reports.md)
- [Presentations](presentations.md) · [Settings](settings.md) · [Translations](translations.md)
- [E-mail and alerts](email-and-alerts.md) (the monthly digest e-mail) ·
  [Automation and troubleshooting](automation-and-troubleshooting.md) · [Pages and code](pages-and-code.md) ·
  [Automatic sources](automatic-sources.md)
- Code: [drive.py](../scripts/sync/drive.py) · [drive_listing.py](../scripts/sync/drive_listing.py) ·
  [booth_names.py](../scripts/sync/booth_names.py) · [common.py](../scripts/sync/common.py) ·
  [build_data.py](../scripts/sync/build_data.py) · [run_all.py](../scripts/sync/run_all.py) ·
  [committee.js](../eleventy/filters/committee.js) · [library.js](../eleventy/filters/library.js) ·
  [send_digest.py](../scripts/notify/send_digest.py) · [update.yml](../.github/workflows/update.yml)
- Settings and reference: [config/site.yml](../config/site.yml) (`drive:`, `booth:`) ·
  [content/booth/README.md](../content/booth/README.md) · [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md) (the
  `drive` items, `booth.json`) · [README.md](../README.md) §2 and §10a
