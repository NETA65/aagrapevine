# Photos, slides, reports, notes, workshops and sign-up forms

> Part of the [how-to guide](README.md). This page covers the "everyday" folders of the committee's Google Drive
> panel folder. The rules that every Drive file follows (the panel folder, sharing, dates in names, what is never
> published) are in [The Drive panel folder](drive-panel-folder.md); every file type is in [File types](file-types.md).

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start](#2-quick-start)
3. [The folders at a glance](#3-the-folders-at-a-glance)
4. [Full reference with examples](#4-full-reference-with-examples) —
   [names](#41-name-a-file-so-its-title-and-date-come-out-right) ·
   [reports](#42-reports--area-and-committee-reports) ·
   [notes](#43-notes--minutes-agendas-and-meeting-notes) ·
   [slides](#44-slides--presentations-and-the-four-deck-copies) ·
   [workshops](#45-workshops--workshop-materials) ·
   [forms](#46-forms--google-forms-for-sign-ups) ·
   [photos](#47-photos--photo-albums) ·
   [any other folder](#48-any-other-folder-name-other) ·
   [loose files](#49-files-sitting-directly-in-the-panel-folder) ·
   [file types](#410-what-each-file-type-becomes-in-these-folders)
5. [What happens next](#5-what-happens-next)
6. [Where it shows on the website](#6-where-it-shows-on-the-website)
7. [Going further: change the code](#7-going-further-change-the-code)
8. [Troubleshooting](#8-troubleshooting)
9. [Good practice and AA principles](#9-good-practice-and-aa-principles)
10. [See also](#10-see-also)

---

## 1. What this is

The committee shares its files in the public Google Drive folder **A65_GV**, inside the panel folder
**2027-2028_Panel77_GVLV**. Each kind of file goes in its own sub-folder: `reports`, `notes`, `slides`, `workshops`,
`forms` and `photos` (Spanish names work too), plus any folder with a name of your own. You drop a file in; at the
next update the site lists it with a title in English and Spanish. Documents go to the **Portfolio**, pictures and
videos to **Photos**.

Where these files show up (site address `https://neta65.github.io/aagrapevine`; Spanish pages add `/es`):

| Page | English | Spanish |
|---|---|---|
| Portfolio (documents, slides, sign-up forms; one tab per folder) | `/portfolio/` | `/es/portfolio/` |
| Photos (albums) | `/photos/` | `/es/photos/` |
| Library (documents and slides, next to the magazines' PDFs) | `/library/` | `/es/library/` |
| Home page, section "Shared by the committee" | `/` | `/es/` |
| What's new + RSS feed | `/whats-new/`, `/feed.xml` | `/es/whats-new/`, `/es/feed.xml` |
| Site search | `/search/` | `/es/search/` |
| Monthly digest (and the monthly e-mail, when it is switched on) | `/digest/` | `/es/digest/` |
| A few pages that link one particular file (Meetings, Monthly toolkit, Shop, GVR / RLV 101) | see [§6](#6-where-it-shows-on-the-website) | |

None of these files becomes an event or goes into the calendar feed (`/events.ics`). Among Drive files only a dated
flyer does that — see [Flyers and events](flyers-and-events.md).

---

## 2. Quick start

### Add a document (report, minutes, slides, workshop handout, sign-up form)

1. Open Google Drive → **A65_GV** → **2027-2028_Panel77_GVLV**.
2. Open the folder for the kind of file: `reports`, `notes`, `slides`, `workshops` or `forms`. If it is missing,
   create it (today the panel folder has no `forms` folder yet).
3. Name the file **date first, then a clear title**, for example `2027-02-17 Committee report - February.pdf`.
   Keep the words PRIVATE, PRIVADO, (Responses) and (Respuestas) out of the name — files with them are never published.
4. Upload it (PDF is the safest; Word, PowerPoint, Google Docs, Google Slides and Google Forms work too).
5. Wait for the next update — the midday or evening refresh, else by the next morning — or start one now: GitHub →
   **Actions** → **Website update** → **Run workflow**, tick **skip_crawl**, click the green button. It takes a
   few minutes.
6. Check `/portfolio/` (tab **Reports**). The card says "Committee report - February", February 17, 2027.

### Add photos (one album)

1. Open **2027-2028_Panel77_GVLV** → `photos`.
2. Make a sub-folder for the event and **put the year in its name**: `2027 Spring Assembly`. The folder name is the
   album name.
3. Upload pictures (and short videos) **in which no AA member can be recognized**.
4. Optional: rename pictures to say what they show — `Literature display.jpg`. A camera name such as `IMG_0142.jpg`
   becomes something like "2027 Spring Assembly #3" (the number is its place in the folder).
5. After the next update: the album is on `/photos/`, the newest pictures are on the home page tiles, and What's New
   says, for example, "4 new photos in 2027 Spring Assembly".

---

## 3. The folders at a glance

| Folder (any of these names) | Put here | Shows on |
|---|---|---|
| `reports` · report, informes, informe, reportes, reporte | Area and committee reports, treasurer reports | Portfolio tab **Reports / Informes** |
| `notes` · note, notas, nota, minutes, minutas, minuta, actas, acta | Minutes, agendas, meeting notes | Portfolio tab **Meeting notes / Notas de reuniones** |
| `slides` · slide, presentaciones, presentación, presentation(s), diapositivas, powerpoint, deck(s) | PowerPoint, Google Slides, Keynote | Portfolio tab **Slides / Presentaciones** |
| `workshops` · workshop, talleres, taller | Handouts, worksheets, the editorial calendar | Portfolio tab **Workshops / Talleres** |
| `forms` · form, formularios, formulario, sign up(s), signup(s), inscripciones, inscripción | Google Forms for sign-ups | Portfolio tab **Sign-ups / Inscripciones** |
| `photos` · photo, fotos, foto, pictures, picture, pics, images, image, imágenes, imagen, gallery, galería | Pictures and short videos, one sub-folder per album | `/photos/` albums |
| any other name, e.g. `Archive`, `Handouts` | Anything that fits nowhere else | Portfolio tab with the folder's own name; its pictures make a `/photos/` album |
| `flyers` · volantes, folletos … | Event flyers | see [Flyers and events](flyers-and-events.md) |
| `bulletin` · boletín, announcements, anuncios … | Bulletin posts | see [Bulletin](bulletin.md) |
| `booth` · booths, mesa, kiosk, kiosko, kiosco, display, pantalla, stand, exhibit, exhibición … | Photos, videos, sound files and short notes for the booth display | the booth display on `/about/#booth` only — see [The Drive panel folder §3.6](drive-panel-folder.md#36-the-booth-folder-new) and [Booth display](booth.md) |

How the folder name is read (code: `category_for()` in [drive.py](../scripts/sync/drive.py)):

- Only the **first folder below the panel folder** counts. `reports/2027/March.pdf` is a report;
  `reports/photos/x.jpg` is still a report (a picture card on the Portfolio, not an album photo).
- Capitals, accents and punctuation do not matter, and the word can be anywhere in the name as a **whole word**:
  `Meeting Notes`, `Fotos 2027`, `Informes-Reports`, `Treasurer reports` all work.
- When two words match, **the one that comes first in the name wins**: `Fotos del taller` is photos,
  `Taller de fotos` is workshops.
- Two folders of the same kind are fine (`reports` and `Informes`): their files go to the same tab.

Folder names that surprise people (checked with the real function):

| Folder name | Becomes | Why |
|---|---|---|
| `Agendas` | its own tab "Agendas" | "agenda" is not a notes word — use `notes`, or `Meeting Notes and Agendas` |
| `Photography`, `Fotografías`, `Photobooth` | its own tab / one album named after the folder | not photos words (only the words in the table above are) |
| `Booth photos`, `Display boards`, `Mesa de literatura` | the booth display only — no album, no tab | a booth word comes first; pictures for `/photos/` go in `photos/`, e.g. `photos/2027 Booth at CityWide/` |
| `Slideshow`, `Keynote` | its own tab | not slides words |
| `Training`, `Orientation`, `Capacitación` | its own tab | not workshops words |
| `Surveys`, `Encuestas`, `Registration` | its own tab (a Google Form there still lands in Sign-ups) | not forms words |
| `Treasury`, `Financials` | its own tab | `Treasurer reports` would be reports |
| `Gallery 2027`, `Pictures`, `Galería` | photos | photos words |
| `Slide deck`, `Decks`, `PowerPoint` | slides | slides words |

---

## 4. Full reference with examples

### 4.1 Name a file so its title and date come out right

These rules are the same in every folder of this page (the full list of date forms is in
[The Drive panel folder](drive-panel-folder.md)). Code: `build_item()` and `name_date()` in
[drive.py](../scripts/sync/drive.py), `date_from_text()` in [common.py](../scripts/sync/common.py).

- **A date anywhere in the name sets the file's date.** Put it first so everyone sees it. Forms that work:
  `2027-02-17` (also `2027.02.17`, `2027_02_17`, `2027 02 17`), `20270217`, US order `02-17-2027` or `2/17/2027`,
  `February 17, 2027`, `Feb 17 2027`, `17 de febrero de 2027`, and month + year (`February 2027` = February 1).
- **The date is taken out of the title** — except when the name only has a month and a year: then
  "February 2027" stays in the title (it is what tells the files apart), and a repeated year at the end is dropped.
- Also taken out: the extension, "Copy of " / "Copia de " at the start, " (1)", " copy", " copia" at the end,
  `(pinned)`-style markers, and any `(until …)` / `(hasta …)` part (only bulletin posts use those — see
  [Bulletin](bulletin.md)). Scheduling with `(from …)` works only in the bulletin.
- Underscores become spaces; `GV_LV`, `GV-LV` or `GV LV` becomes "GV/LV" (but not in `GV_LV_Report`: an underscore
  right after "LV" blocks it).
- **No date in the name** → the file gets the "last modified" date that the Drive folder shows (with the optional
  `GOOGLE_API_KEY` secret: the day the file was added to Drive), else the day the site first saw it. Without the key,
  editing an undated file re-dates it: it moves up in the Portfolio and can show "New" again.
- **Not read as a date:** a year alone (`2027`), a range (`2026-2027`), year and month in digits (`2027-01`), day
  first (`17-02-2027` — month 17 does not exist), and years outside 2000–2099. Careful: a day-first date whose day
  is 12 or less is read the American way — `05-03-2027` is **May 3**, not March 5.
- Write the name **in the language of the document**. The site makes the other language automatically and marks it
  "Auto-translated" / "Traducción automática". To fix a wrong translation, see [§8](#8-troubleshooting) and
  [Translations](translations.md).

Checked examples (the file name → what the site uses):

| File | Title on the site | Date the site uses |
|---|---|---|
| `reports/2027-02-17 Committee report.docx` | Committee report | 2027-02-17 |
| `reports/2027-02-17 Committee report` (a Google Doc) | Committee report | 2027-02-17 |
| `reports/Treasurer report - March 14, 2027.pdf` | Treasurer report | 2027-03-14 |
| `reports/03-14-2027 Assembly report.pdf` | Assembly report | 2027-03-14 |
| `reports/14-03-2027 Assembly report.pdf` | 14-03-2027 Assembly report | not a date → the "last modified" date |
| `reports/GV-LV Report March 2027.pdf` | GV/LV Report March 2027 | 2027-03-01 |
| `reports/GV_LV_Report_2027-03-14.pdf` | GV LV Report | 2027-03-14 |
| `reports/Area 65 Assembly Report 2027.pdf` | Area 65 Assembly Report 2027 | the "last modified" date |
| `reports/Copy of 2027-02-17 Committee report (1).docx` | Committee report | 2027-02-17 |
| `notes/March 2027 Committee Meeting 2027.pdf` | March 2027 Committee Meeting | 2027-03-01 |
| `notes/Policy (until further notice).pdf` | Policy | the "last modified" date |
| `notes/A message (from the Chair).pdf` | A message (from the Chair) | the "last modified" date |
| `Informes/Informe del comité - 17 de febrero de 2027.pdf` | Informe del comité (Spanish) | 2027-02-17 |
| `Archive/2027-01 Newsletter.pdf` | 2027-01 Newsletter | the "last modified" date |

The Portfolio prints the date as "February 17, 2027" on English pages and "17 de febrero de 2027" on Spanish pages.

**What the date changes besides the card** (code: `Ctx.effective_ts()` and `Ctx.is_new()` in
[build_data.py](../scripts/sync/build_data.py)):

| The date in the name is … | Portfolio / Library order | "New" badge (14 days) | What's New + RSS | Home tiles | Monthly digest |
|---|---|---|---|---|---|
| none (upload day) | at the upload day | yes | at the upload day | yes, while among the 6 newest | the month it was added |
| in the past (a meeting last month) | at that past day | only if that day is less than 14 days ago | at that past day — often too far down to be seen (the list keeps the newest 150 entries) | only if still among the 6 newest | **the month it was added** |
| more than a day in the future (next month's agenda) | at the top | yes | at the day the site first saw it | yes | the month of the date in its name (the digest takes the later of the two days) |

Real case: `2026-08-11 Grapevine Area Chair Meeting Report.pdf`, `2026-05-12 Grapevine Area Chair Meeting Report.pdf`
and `2026-08-11 Grapevine Area Chair Meeting Agenda.pdf` were uploaded on September 25, 2026. They are on the
Portfolio, dated August 11 and May 12, without a "New" badge, not in What's New and not on the home tiles — and they
count in the September digest ("Committee uploads"), because they were added in September.

### 4.2 `reports/` — Area and committee reports

**Folder names:** `reports`, `report`, `informes`, `informe`, `reportes`, `reporte`, or any name with one of these
words (`Treasurer reports`, `Informes-Reports`).

**Put here:** GV/LV reports to the Area and the districts, the chair's report, treasurer reports, assembly reports.
PDF opens everywhere; Word (`.docx`) and Google Docs work too (a Google Doc's **Download** button gives a PDF).

| Example | Result |
|---|---|
| `2027-02-17 Committee report - February.pdf` | Reports tab: "Committee report - February", February 17, 2027 |
| `February 2027 Committee report.pdf` | "February 2027 Committee report", dated February 1 (month + year stay in the title) |
| `2027-02-17 Committee report.docx` | "Committee report" — fine once, but every month's file would look the same: add a word |
| `Informes/Informe del comité - 17 de febrero de 2027.pdf` | "Informe del comité" in Spanish; the English page shows a translation marked "Auto-translated" |
| `2027 budget.xlsx`, a Google Sheet, a `.csv` | **never published** (spreadsheets can hold personal information) |
| `Literature table photo.jpg` in `reports/` | a Portfolio card of type "Image" in the Reports tab (not an album photo, not in the Library) |

Real files today: `2026-08-11 Grapevine Area Chair Meeting Report.pdf` and
`2026-05-12 Grapevine Area Chair Meeting Report.pdf`. Both are titled "Grapevine Area Chair Meeting Report"; the dates on the cards tell them apart.
Their Spanish title, "Informe de la reunión de coordinadores de Área de Grapevine", was written by hand in
[overrides.yml](../data/translations/overrides.yml).

**Where reports show:** Portfolio tab **Reports / Informes** (`/portfolio/#docs-reports`); Library type
"Committee reports" / "Informes del comité" and the collection **Committee reports** (`/library/?col=reports`,
together with the meeting notes); home tiles (labelled "Document"); What's New and RSS; search; the digest
(the e-mail labels the row "Reports" / "Informes").

### 4.3 `notes/` — minutes, agendas and meeting notes

**Folder names:** `notes`, `note`, `notas`, `nota`, `minutes`, `minutas`, `minuta`, `actas`, `acta`, or a name
with one of them (`Meeting Notes`, `Meeting Notes and Agendas`). A folder called only `Agendas` is **not** notes —
it becomes its own tab (see [§4.8](#48-any-other-folder-name-other)).

| Example | Result |
|---|---|
| `2027-01-20 Committee meeting minutes.pdf` | Meeting notes tab: "Committee meeting minutes", January 20, 2027 |
| `2027-01-20 Agenda - January committee meeting.pdf` | "Agenda - January committee meeting" |
| an agenda for next month, uploaded early: `2027-02-17 Agenda - February committee meeting.pdf` | sorts at the top of the tab and counts as new from the day it was uploaded |
| `March 2027 Committee Meeting.pdf` | "March 2027 Committee Meeting", dated March 1, 2027 |
| `Actas/Acta de la reunión - 20 de enero de 2027.docx` | "Acta de la reunión", January 20, 2027, Spanish |
| `Minutes/2027-02-17 Minutes.md` | "Minutes" — a document card that opens in Drive's viewer (a `.md` file is turned into a page only in the bulletin folder) |
| `Notas privadas.pdf` | **published** — "privadas" does not contain "PRIVADO" |
| `privately funded literature.pdf` | **not published** — "privately" contains "PRIVATE" (the check is a plain substring, capitals ignored) |

Real files today: `2026-08-11 Grapevine Area Chair Meeting Agenda.pdf`, and
`2026-10-01 Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf` →
"Grapevine & La Viña Pricing Update - Effective January 1, 2027" (the first date in the name is the file's date;
the second one stays in the title).

**Extra places notes show up:**

- **Meetings page** (`/meetings/`, `/es/meetings/`): the chair card's link "Agendas and past reports in the
  Portfolio" goes to `/portfolio/#docs-notes` when the notes tab has files, else to `/portfolio/`
  (code: `notesTab` in [meetings.njk](../src/pages/meetings.njk)).
- **Shop page** (`/shop/`): while a price change is announced, the notice's link "Read AA Grapevine's notice" opens
  the newest Drive file whose title or file name matches `price_changes[].doc_match` in
  [config/site.yml](../config/site.yml). Today that is the Pricing Update PDF above. Rename it so the pattern no
  longer matches, and the link quietly disappears — see [Settings](settings.md).
- Library: type "Meeting notes" / "Notas de reunión" and the collection **Committee reports**.

### 4.4 `slides/` — presentations and the four deck copies

**Folder names:** `slides`, `slide`, `presentaciones`, `presentación`, `presentations`, `presentation`,
`diapositivas`, `diapositiva`, `powerpoint`, `decks`, `deck` (also `Slide deck`, `PowerPoint`).

**File types:** PowerPoint (`.ppt`, `.pptx`, `.pps`, `.ppsx`), Google Slides, Keynote (`.key`) and `.odp` become
**Slides** cards (the first slide is the card's picture, shown whole). A PDF handout in `slides/` is an ordinary
**Document** card in the same tab; a picture is an "Image" card; a video a "Video" card.

| Example | Result |
|---|---|
| `2027-03-14 Spring Assembly GV report.pptx` | Slides tab: "Spring Assembly GV report", March 14, 2027 |
| `Grapevine 101` (a Google Slides file) | "Grapevine 101"; **Download** gives a PDF |
| `Presentaciones/Taller de escritura.pptx` | "Taller de escritura", Spanish; the English page shows a translation marked "Auto-translated" |
| `Information Workshop handout.pdf` | a Document card in the Slides tab |
| `Committee overview.ppsx` in a folder named `PowerPoint` | Slides tab: "Committee overview" |

#### The four deck copies

The site has four **web presentations** on GVR / RLV 101 (`/orientation/#presentations`), written in
[config/presentations/](../config/presentations/README.md). The four `.pptx` files in `slides/` are fixed PowerPoint
copies of them, made on October 1, 2026. The site links each copy to its web presentation **by the copy's title**:
the title must be exactly the deck's `drive_title`.

| File in `slides/` today | `drive_title` is set in | The web presentation |
|---|---|---|
| `GVR and RLV Orientation Workshop.pptx` | `config/presentations/orientation-workshop.yml` | `/orientation/?present=orientation-workshop` |
| `Grapevine and La Viña Information Workshop.pptx` | `config/presentations/information-workshop.yml` | `/orientation/?present=information-workshop` |
| `Grapevine and La Viña Writing Workshop.pptx` | `config/presentations/writing-workshop.yml` | `/orientation/?present=writing-workshop` |
| `Grapevine and La Viña Monthly Committee Meeting.pptx` | `config/presentations/committee-meeting.yml` | `/orientation/?present=committee-meeting` |

What the match gives:

- **Portfolio** (Slides tab): the card shows "A fixed copy: the web version stays current and can be customized."
  and a **Present on the web** button → `/orientation/?present=<id>` (`/es/orientation/?present=<id>` on the
  Spanish page). Code: [portfolio.njk](../src/pages/portfolio.njk), search `where("drive_title", rawTitle)`.
- **GVR / RLV 101** (`/orientation/`): the deck's card has, in its **More** menu, **PowerPoint copy** with the line
  "Made in October 2026 · doesn't update" (the month of the file's date). Without JavaScript the card shows a
  PowerPoint copy button instead. Code: [orientation.njk](../src/pages/orientation.njk), search `set copies`.
- The deck's data file `/orientation/presentations/<id>.json` carries the same link (`drive`). Code: `driveCopy()` in
  [presentations.js](../eleventy/filters/presentations.js).

The comparison uses the file's title **as the site cleans it** (the extension, a full date anywhere in the
name, "Copy of", " (1)" / " copy" and underscores are removed; spaces are squeezed) and must then match **word for word, with the same capitals and
accents** (checked with the real functions):

| File name in `slides/` | Still linked? |
|---|---|
| `Grapevine and La Viña Information Workshop.pptx` | yes |
| `2026-10-01 Grapevine and La Viña Information Workshop.pptx` | yes — the date leaves the title |
| `Copy of Grapevine and La Viña Information Workshop (1).pptx` | yes |
| `Grapevine_and_La_Viña_Information_Workshop.pptx` | yes — underscores become spaces |
| `Grapevine and La Viña Information Workshop v2.pptx` | **no** — the title ends in "v2" |
| `grapevine and la viña information workshop.pptx` | **no** — the capitals differ |

> **Note:** the match looks at **every** committee Drive file, not only `slides/`. A PDF with exactly the same title
> (say in `workshops/`) also gets "Present on the web" on the Portfolio, and when several files match, the
> "PowerPoint copy" link opens the one with the **newest date**. Keep one copy per deck.

To rename a deck, rename the Drive file **and** change `drive_title` in its YAML file (that is a push to `main`, so a
quick update follows). To refresh a copy, upload the new `.pptx` as a new version of the old file (Drive's
**Manage versions**, in the file's right-click menu — under **File information** in newer Drive menus): the file
keeps its id, so every link stays (without the `GOOGLE_API_KEY` secret, its date — and the "Made in …" month —
becomes the day of the new upload). Or upload it with the same title and delete the old file. The copies never update by themselves: changing a YAML file does not change the
`.pptx`, and changing the `.pptx` does not change the web presentation. Editing the web presentations:
[Presentations](presentations.md).

### 4.5 `workshops/` — workshop materials

**Folder names:** `workshops`, `workshop`, `talleres`, `taller` (also `Workshop materials`, `Writing Workshop`).

**Put here:** handouts, worksheets, writing prompts, facilitator notes, the magazines' editorial calendar. (Workshop
**flyers** go in `flyers/`; workshop **slides** in `slides/`, where a deck copy can get "Present on the web".)

| Example | Result |
|---|---|
| `2027-04-10 Writing workshop handout.pdf` | Workshops tab: "Writing workshop handout", April 10, 2027 |
| `Writing prompts.docx` | "Writing prompts", dated by Drive's "last modified" date |
| `Talleres/Hoja de trabajo - Taller de escritura.docx` | "Hoja de trabajo - Taller de escritura", Spanish |
| `Writing workshop sign-in` (a Google Form) | **stays in the Workshops tab**, with a **Sign up** button (only forms in unknown folders move to Sign-ups) |

Real file today: `Grapevine as a Twelfth Step Tool - Put Them to Work (2026-2027 editorial calendar).pdf` → the title
stays as written (a year range is not a date), dated September 25, 2026 by Drive; its Spanish title is hand-written in
[overrides.yml](../data/translations/overrides.yml).

**The editorial-calendar link.** The Monthly toolkit (`/monthly/`, section "10 ways to put an issue to work") shows a
**Full editorial calendar** link to the newest committee Drive file whose title or file name contains
"editorial calendar" or "calendario editorial" (capitals ignored, any folder). Keep one of those phrases in next
year's file name, or the link disappears. Code: [monthly.njk](../src/pages/monthly.njk), search
`driveMatch("editorial calendar`.

**Where workshop files show:** Portfolio tab **Workshops / Talleres** (`/portfolio/#docs-workshops`); Library type
"Workshops" / "Talleres"; home tiles; What's New and RSS; search; digest (e-mail label "Workshops" / "Talleres").

### 4.6 `forms/` — Google Forms for sign-ups

**Folder names:** `forms`, `form`, `formularios`, `formulario`, `sign up`, `sign ups`, `signup`, `signups`,
`inscripciones`, `inscripción` (`Sign-ups` and `Sign Ups` work: a dash counts as a space).

**Make a sign-up the site shows:**

1. Create the Google Form **inside** 2027-2028_Panel77_GVLV › `forms` (create that folder first — it does not
   exist yet), or move an existing form there (right-click → **Organize** → **Move**).
2. Give it the name visitors should read: `Spring Assembly booth volunteers`. A date in front sets its date:
   `2027-03-01 Writing workshop sign-up` → "Writing workshop sign-up", March 1, 2027.
3. If you link the form to a spreadsheet, Google calls it "&lt;form name&gt; (Responses)". The site never publishes it —
   spreadsheets and names with "(Responses)" / "(Respuestas)" are excluded — but **keep it out of A65_GV**: anyone
   with the folder link can open what is inside.
4. After the next update the form is on the Portfolio.

**What the site does with a form:**

- A card in **Sign-ups / Inscripciones** (`/portfolio/#docs-forms`) with one button, **Sign up** / **Inscribirse**,
  that opens the form (no Preview and no Download).
- Home tile labelled "Sign-up form"; What's New (labelled "Sign-up form") and the RSS feed (filed under "Committee
  uploads"); Library type "Forms" / "Formularios"; search; digest (e-mail label "Forms" / "Formularios").
- **Every update checks each form.** When it no longer accepts responses (Google sends visitors to its "closed"
  page), the form is left out of every page — Portfolio, home, Library, search, What's New, digest — from that
  update on. Turn responses back on in Google Forms and it returns at the next update. When the check cannot decide
  (a network hiccup), yesterday's answer is kept. Code: `check_forms()` in [drive.py](../scripts/sync/drive.py),
  `closed_form()` in [build_data.py](../scripts/sync/build_data.py).
- A form that asks visitors to sign in to Google stays listed (the site only notes it).
- Where a form lands: in `forms/` → Sign-ups; in an unknown folder (`Archive`, `Surveys` …) → Sign-ups too; in
  `reports/`, `notes/`, `slides/`, `workshops/` or `flyers/` → that folder's tab; in `photos/` → not on the
  Portfolio at all (see [§4.10](#410-what-each-file-type-becomes-in-these-folders)).

| Example | Result |
|---|---|
| `forms/Spring Assembly booth volunteers` (Google Form) | Sign-ups tab, **Sign up** button |
| `forms/Spring Assembly booth volunteers (Responses)` (Google Sheet) | never published |
| `forms/Answers (Respuestas)` (a Google Form!) | never published — the name has "(Respuestas)" |
| `Inscripciones/Inscripción para la mesa de La Viña` (Google Form) | Sign-ups tab, Spanish title |
| `forms/Volunteer sign-up sheet.pdf` | a Document card in the Sign-ups tab (Preview / Open / Download) |

Real case: today a sign-up form and its "(Responses)" sheet sit in the **A65_GV root**, outside the panel folder.
The site shows neither (the form is a "loose" file, the sheet a spreadsheet). Since October 2026 the public file
`data/raw/drive.json` only **counts** such loose files (`stats.loose_skipped`); their names are written only in the
run's log (step *Sync sources and translate*), which is public too while GitHub keeps it. To publish such a form,
move it into the panel's `forms/`; move the responses sheet somewhere private.

### 4.7 `photos/` — photo albums

**Folder names:** `photos`, `photo`, `fotos`, `foto`, `pictures`, `picture`, `pics`, `images`, `image`, `imágenes`,
`imagen`, `gallery`, `galería` (also `Fotos 2027`, `Gallery 2027`). Not `Photography` or `Fotografías` — those are
unknown folders ([§4.8](#48-any-other-folder-name-other)).

**Put here:** pictures (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.heic`, `.tif`, `.bmp`, `.svg`) and short videos
(`.mp4`, `.mov`, `.m4v`, `.avi`, `.wmv`, `.webm`, `.mkv`, `.3gp`) — **only where no AA member can be recognized**.
Only pictures and videos belong here: any other file in `photos/` is left off the Portfolio, Photos and Library
(it still shows on the home tiles, in What's New and in the digest).

#### Which album a file goes to

Code: the `album` line in `build_item()` ([drive.py](../scripts/sync/drive.py)); `albumFolder`, `photoAlbumKey()`
and `photoAlbums()` in [committee.js](../eleventy/filters/committee.js).

| Where the file is | Album on `/photos/` |
|---|---|
| `photos/2027 Spring Assembly/IMG_0142.jpg` | "2027 Spring Assembly" |
| `photos/2027/Spring Assembly/IMG_0001.jpg` | "2027 / Spring Assembly" — the folders below `photos/` are joined with " / " |
| `photos/Fall Assembly 2027/Video/intro.mov` | "Fall Assembly 2027 / Video" — a **separate** album from "Fall Assembly 2027" |
| `photos/IMG_0142.jpg` (no sub-folder) | the panel's own album, "Panel 77 (2027–2028) — photos" ("— fotos" in Spanish) |
| `Fotos 2027/IMG_1.jpg` (a photos-word folder, no sub-folder) | the panel's own album too |
| `Panel photo.jpg` sitting directly in 2027-2028_Panel77_GVLV | the panel's own album too |
| `Archive/IMG_0001.jpg`, `Archive/2025/IMG_0002.jpg` (an unknown folder) | one album "Archive" for the folder and all its sub-folders ([§4.8](#48-any-other-folder-name-other)) |
| `reports/IMG_0003.jpg`, `slides/Slide 1.png` | no album: an "Image" card on the Portfolio |

- **Album title:** the folder name as written. On `/es/photos/` it is translated automatically (fix it in
  [overrides.yml](../data/translations/overrides.yml), see [§8](#8-troubleshooting)). An unknown folder's album
  ("Archive") is never translated on `/photos/`.
- **Put the year in album names.** Albums with the same sub-folder name **merge into one** — even across panels,
  and between `photos/` and `fotos/` (the album is known by its sub-folder name only).
- Avoid album names such as "Albums", "Share photos" or "Subscribe", and names that begin with the word "Docs",
  "Month" or "CM" followed by more words ("Docs 2027"): those albums get no short link, so What's New links them to
  the top of `/photos/` (they still have their `#album-…` link).

#### Captions and numbers

- **The file name is the caption** (Drive's own "description" field is not read):
  `Literature display at the Spring Assembly.jpg` → "Literature display at the Spring Assembly". Never put a
  person's name in it.
- **A date in the name** sets the photo's date and leaves the caption: `2027-03-14 Literature table.jpg` →
  "Literature table", March 14, 2027.
- **Camera and phone names get "&lt;album&gt; #n"**: `IMG_0142.jpg`, `DSC_0042.JPG`, `PXL_20270314_150102.jpg`, `MVIMG_…`,
  `VID_20270314_101010.mp4`, `20270314_101010.jpg`, `WhatsApp Image 2027-03-14 at 10.15.32 AM.jpeg`,
  `IMG-20270314-WA0003.jpg`, `Screenshot 2027-03-14 at 9.12.44 AM.png`, `Captura de pantalla …`, long random ids,
  `unnamed`, `download`, `Photo 3`, `Video 1`, `IMG_0142-edited`. Code: `is_generic_media_name()` and
  `_GENERIC_WORDS` in [drive.py](../scripts/sync/drive.py).
- **n** is the file's place among **all** the photos and videos of that same folder, A→Z by file name — named files
  count too. So numbers can skip, and a new file whose name sorts earlier renumbers the ones after it.
- Without an album the label is the folder's own name (`photos/IMG_0142.jpg` → "Photos #1"; `Fotos 2027/IMG_1.jpg`
  → "Fotos 2027 #1"), and "Photo #n" / "Video #n" for a file sitting directly in the panel folder.
- **Not recognized** as camera names (they keep the file name — rename them): GoPro `GOPR0042.JPG` → "GOPR0042";
  Pixel motion photos `PXL_20270314_150102123.MP.jpg` → "PXL 150102123.MP".

Checked example — the folder `photos/2027 Spring Assembly/` with ten files:

| File | Caption | Date |
|---|---|---|
| `2027-03-14 Literature table.jpg` | Literature table | 2027-03-14 (name) |
| `Copy of IMG_0142 (1).jpg` | 2027 Spring Assembly #2 | upload day |
| `IMG_0142.jpg` | 2027 Spring Assembly #3 | upload day |
| `IMG_0150.jpg` | 2027 Spring Assembly #4 | upload day |
| `Literature display at the Spring Assembly.jpg` | Literature display at the Spring Assembly | upload day |
| `PXL_20270314_150102.jpg` | 2027 Spring Assembly #6 | 2027-03-14 (name) |
| `setup.mp4` (video) | setup | upload day |
| `VID_20270314_101010.mp4` (video) | 2027 Spring Assembly #8 | 2027-03-14 (name) |
| `WhatsApp Image 2027-03-14 at 10.15.32 AM.jpeg` | 2027 Spring Assembly #9 | 2027-03-14 (name) |
| `PRIVATE members at the table.jpg` | **never published** | — |

("Upload day" = the "last modified" date the Drive folder shows. `Copy of IMG_0142 (1).jpg` is a second copy of
`IMG_0142.jpg`: the site shows both — delete duplicates in Drive.)

#### Dates and order

- A photo's date: the date in its name → (only with the `GOOGLE_API_KEY` secret) the moment the camera took it →
  the "last modified" date in the Drive folder (with the key: the day it was added to Drive) → the day the site first
  saw it. Camera names that contain a date (`PXL_20270314_…`, `WhatsApp Image 2027-03-14 …`, `20270314_101010`)
  use that date. A video skips the camera step (only pictures have one). (Flyers work differently: see
  [Flyers and events](flyers-and-events.md).)
- Albums are listed newest first (by their newest photo). Inside an album: newest first; photos of the same day in
  A→Z order of their original (untranslated) captions.
- Old pictures named with an old date (last year's assembly) get no "New" badge and usually do not reach What's New;
  the digest still counts them in the month they were added (see the table in [§4.1](#41-name-a-file-so-its-title-and-date-come-out-right)).

#### Videos

A video sits in its album with a play mark and is counted as a video ("12 photos · 2 videos"). Tapping it plays it
with Drive's own player inside the slideshow window. Short clips work best. Right after an upload Drive may need a
while before its player works. Videos are never grouped in What's New — each one is its own entry.

#### On the `/photos/` page

- An album index: a mosaic of up to three pictures per album, "N photos" (and "N videos"), the newest month, and a
  "New" badge when the album has a new photo.
- Then each album: heading with "Panel 77 (2027–2028) · March 2027", buttons **Full screen** (slideshow),
  **Share** (the album's own link) and back to the albums. From 5 photos the first one is shown big and, when rows
  would be cut, a **Show all N** button appears. Tap a photo for the full-screen slideshow, with its caption and
  "album · date".
- Links: `/photos/#album-2027-spring-assembly` always works; the short `/photos/#2027-spring-assembly` is the one
  What's New uses. The panel's own album is `/photos/#album-panel-77-2027-2028`.
- Under the albums: "Protecting anonymity" (what is fine to share, what never is), and the closed box
  "For committee members · How to add photos" (`/photos/#share-photos`) with **Open Drive folder** (the current
  panel folder) and **Ask for upload access** (an e-mail to grapevine@neta65.org).
- No photos yet (the case today — the `photos` folder is empty): the card "Our photo albums are ready for the new
  panel", and in the members' box the line "We checked the committee's Google Drive on &lt;date&gt; — nothing here yet."

#### Elsewhere

| Place | What a photo does there |
|---|---|
| What's New + RSS | **2 or more pictures of the same album with the same day** become ONE entry: "4 new photos in 2027 Spring Assembly" (Spanish: "4 fotos nuevas en …" with the album's Spanish name), type "Photo album", linking to `/photos/#2027-spring-assembly`. A single picture, and every video, is its own entry linking to the Drive file. The day is the photo's date, so pictures dated by their names group by that day: one upload can make two entries. |
| Home, "Shared by the committee" | each picture or video can be one of the 6 newest committee files (the tile opens the Drive file; for an album inside `photos/` the album name shows under the caption); a **Photos** button appears in that section once an album exists |
| Search | one entry per album, type "Photo album", "N photos · Panel 77 (2027–2028)" → `/photos/#album-…`; single photos are not searchable |
| Digest (`/digest/` and the e-mail) | one row per album and month — "Photos: 2027 Spring Assembly", "5 new photos" (photos and videos counted together; the e-mail shows a "Photos" label and the album name) — in the month the photos were added; the page links to the album, the e-mail to `/photos/` |
| Committee sub-nav | "Photos N" (photos + videos; no number while there are none) |
| Library | never |

Code: `plan_whatsnew()`, `album_slug()` and `finish_group()` in [build_data.py](../scripts/sync/build_data.py);
`homeDrive` in [home.js](../eleventy/filters/home.js); the "albums" part of the search index in
[library.js](../eleventy/filters/library.js); `monthNews()` in [community.js](../eleventy/filters/community.js) and
its twin `album_key()` / `is_album_media()` in [send_digest.py](../scripts/notify/send_digest.py).

### 4.8 Any other folder name ("other")

A first folder whose name has none of the category words — the booth words (`booth`, `mesa`, `display`, `stand` …)
count as category words too, see the table in [§3](#3-the-folders-at-a-glance) — is filed as **other**. What
happens to its files:

- **Documents and slides** → a Portfolio tab **named exactly like the folder** (the same on the Spanish page),
  after the built-in tabs, A→Z. Its link is `#docs-folder-<name>` with the name in lower case, accents dropped and
  spaces turned into dashes: `/portfolio/#docs-folder-archive`, `/portfolio/#docs-folder-la-vina`. Files in its
  sub-folders go in the same tab.
- **Pictures and videos** → one `/photos/` album named after the folder, with all its sub-folders merged in; the
  name is not translated there.
- **Google Forms** → the Sign-ups tab.
- **Library:** the type **"Other" / "Otros"** — not the folder's name.
- Home tiles, What's New, search: like any committee file; the digest e-mail labels the row "Files" / "Archivos".
- Spreadsheets and CSV files: never.

> **Note:** the comment above `drive:` in [config/site.yml](../config/site.yml) says "Any other folder name shows up
> in the Library under its own name". The code does it differently: the folder's name is the **Portfolio** tab;
> the Library lists those files as "Other".

Checked examples:

| File | Portfolio | Photos | Library |
|---|---|---|---|
| `Archive/2025 Panel 75 summary.pdf` | tab "Archive": "2025 Panel 75 summary" | — | Other |
| `Archive/2025/Summary.docx` | tab "Archive": "Summary" | — | Other |
| `Archive/IMG_0001.jpg` (with `clip.mp4` and `Old flyer.png` beside it) | — | album "Archive": "Archive #2" | — |
| `Archive/2025/IMG_0002.jpg` | — | album "Archive": "2025 #1" (the caption uses its own folder) | — |
| `Archive/clip.mp4` | — | album "Archive" (a video) | — |
| `Archive/Volunteer form` (Google Form) | Sign-ups tab | — | Other |
| `Archive/talk.mp3` | tab "Archive" (a Document card; opens in Drive's viewer) | — | Other |
| `Handouts/Ways to carry the message.pdf` | tab "Handouts" | — | Other |
| `La Viña/Recursos para RLV.pdf` | tab "La Viña": "Recursos para RLV", Spanish | — | Other |
| `Agendas/2027-02-17 Agenda.pdf` | tab "Agendas": "Agenda", February 17, 2027 | — | Other |

> **Note:** keep pictures one level deep in an unknown folder. What's New names a group after the sub-folder
> ("4 new photos in Archive / 2025", link `#archive-2025`), but `/photos/` has only one album "Archive", and only
> one short link per album — so one of the two links lands at the top of the page.

### 4.9 Files sitting directly in the panel folder

A file dropped straight into 2027-2028_Panel77_GVLV (not in a sub-folder) is filed by its type:

| File | Goes to |
|---|---|
| a picture or video (`Panel photo.jpg`, `IMG_9999.jpg`) | the panel's own album "Panel 77 (2027–2028) — photos"; camera names become "Photo #n" / "Video #n" |
| a Google Form (`Quick poll`) | Sign-ups tab |
| slides (`Committee deck`, a Google Slides file) | Slides tab |
| anything else (`2027-03-14 Spring Assembly.pdf`, a Google Doc …) | a tab **"Other" / "Otros"** (`#docs-folder-other` on English pages, `#docs-folder-otros` on Spanish pages); Library "Other" |

It works, but a folder is clearer for everyone.

### 4.10 What each file type becomes in these folders

The full table for every folder is in [File types](file-types.md); this is the part that matters here (code:
`kind_for()` in [drive.py](../scripts/sync/drive.py); `isDocItem()`, `isPhotoItem()` and `fileType()` in
[committee.js](../eleventy/filters/committee.js); `libraryDocs()` in [library.js](../eleventy/filters/library.js)).

| File | In `reports`, `notes`, `slides`, `workshops`, `forms` | In an unknown folder | In `photos` |
|---|---|---|---|
| PDF, Word, Google Doc, `.txt`, `.md`, `.rtf`, `.odt`, `.zip`, audio (`.mp3`, `.m4a`, `.wav`), Google Drawing | Portfolio "Document" card in that tab; Library | Portfolio tab of the folder; Library "Other" | not on Portfolio, Photos or Library |
| PowerPoint, Google Slides, Keynote, `.odp` | Portfolio "Slides" card; Library | Portfolio tab of the folder; Library "Other" | not on Portfolio, Photos or Library |
| Picture | Portfolio "Image" card; not in the Library | album named after the folder | album photo |
| Video | Portfolio "Video" card; not in the Library | album named after the folder | album video |
| Google Form | "Form" card with **Sign up** in that tab (in `forms/`: Sign-ups); Library while open | Sign-ups tab; Library "Other" while open | not on Portfolio, Photos or Library |
| Spreadsheets (`.xlsx`, `.xls`, `.ods`, `.csv`, `.tsv`, Google Sheets), Apps Script, Google Sites | never published | never published | never published |
| Any file or folder whose name contains PRIVATE, PRIVADO, (Responses), (Respuestas) or "wrong size" | never published | never published | never published |

"Not on Portfolio, Photos or Library" still means: home tiles, What's New and the digest list it.

A Drive **shortcut** is filed under the folder the shortcut sits in and opens the file it points to (the original
must be shared publicly too).

> **Note:** without the optional `GOOGLE_API_KEY` secret (the case today), the public folder view only says
> "shortcut", so the site takes the file type from the **shortcut's name**: `Handout.pdf` → a document,
> `Deck.pptx` → slides. A shortcut to a Google Doc, Google Slides file or Google Form has no extension in its name
> and shows as a plain **Document** card — a form then gets no **Sign up** button and no open/closed check. Put
> Google Forms and Google Slides in the folder itself rather than as shortcuts. With the API key the site learns
> the real file type, so a shortcut works like the file it points to. (Code: `_resolve_shortcut()` and
> `ApiLister._entry()` in [drive_listing.py](../scripts/sync/drive_listing.py).)

---

## 5. What happens next

A Drive upload is not a change to the GitHub repository, so nothing starts by itself. The site reads the Drive
folder in **every** run of the GitHub workflow **Website update** — quick runs and the full daily run alike:

| Run | When | Your file is live |
|---|---|---|
| Morning refresh | every morning, started by the "Morning check", so the new day is on the site by 5:30 AM Central | about 3 minutes after it starts |
| Nightly full update | GitHub's schedule. It is set 4 hours early on purpose, because GitHub usually starts it 4–6 hours late (so about 6–8 AM Central, 5–7 in winter) | when the run ends — usually 10 to 15 minutes (it also searches the magazines' sites for PDFs; at the very most a little over 2 hours) |
| Midday refresh (quick) | GitHub's schedule, about 11 AM–1 PM Central | a few minutes |
| Evening refresh (quick) | GitHub's schedule, about 7–9 PM Central | a few minutes |
| After any edit pushed to `main` (settings, content, code, tests, translation fixes — not documentation) | right away (a quick refresh; it tests a change of the code first) | about 3 minutes (about 5 for a change of the code) |
| By hand | GitHub → **Actions** → **Website update** → **Run workflow** → tick **skip_crawl** → green **Run workflow** | a few minutes |

So without doing anything, a file uploaded in the morning is normally on the site after the midday refresh, one
uploaded in the afternoon after the evening refresh, and one uploaded at night the next morning. The **MKP715** login
(write access) can start the run by hand. Repository settings and secrets — for example adding the optional
`GOOGLE_API_KEY` — need the **NETA65** (admin) account. More: [Automation and troubleshooting](automation-and-troubleshooting.md).

What the run does with your files:

1. `scripts/sync/drive.py` lists A65_GV and its panel folder(s) with every sub-folder, files every item, checks
   each Google Form, and writes `data/raw/drive.json`.
2. `scripts/sync/build_data.py` builds the site data: `data/site/drive.json` (Portfolio, Photos, Library, home),
   `whatsnew.json` (What's New, RSS) and `status.json`; it translates new titles and album names.
3. The data is committed ("chore(data): … content sync …"), the site is built and published on GitHub Pages.

Good to know:

- Pictures are **not** copied into the repository. Thumbnails and full-size pictures load straight from Google
  (`lh3.googleusercontent.com`) when someone opens the page, and videos play from Drive — so photos need an internet
  connection (the site's offline copy does not keep them).
- **Deleting** a file in Drive removes it from the site at the next run (as long as its folder could be read).
  **Renaming** or **moving** keeps the day it was added; the title and the tab follow the new name and folder.
  Adding PRIVATE to the name takes it off at the next run.
- New titles that could not be translated in this run are counted in the run summary's **Translations** line as
  "… waiting for the next run" (when none at all could be translated, a "Translation is not working" warning
  appears too). They stay in their original language until a later run translates them.

---

## 6. Where it shows on the website

| Place | English · Spanish | Documents, slides and forms | Album photos and videos |
|---|---|---|---|
| Portfolio | `/portfolio/` · `/es/portfolio/` | a card in the folder's tab (`#docs-reports`, `#docs-notes`, `#docs-slides`, `#docs-workshops`, `#docs-forms`, `#docs-folder-<name>`): title in the page language, date, "New" for 14 days, **Preview** / **Open** / **Download** (a form: **Sign up**) | — |
| Photos | `/photos/` · `/es/photos/` | — | albums (`#album-<name>`), slideshow, Share |
| Library | `/library/` · `/es/library/` | documents, slides and open forms; badge "NETA 65", source "NETA 65 committee", type by folder (Committee reports, Meeting notes, Slides, Workshops, Forms, Other); reports and notes also in the collection **Committee reports** (`/library/?col=reports`); the file size shows only with the `GOOGLE_API_KEY` secret | never |
| Home, "Shared by the committee" | `/` · `/es/` | one of the 6 newest committee files (by date), labelled Document / Slides / Sign-up form; link "See the portfolio" | one of the 6 newest, with the album name; a **Photos** button |
| What's New | `/whats-new/` · `/es/whats-new/` | one entry per file at its date, badge "NETA 65", "Panel 77 (2027–2028)"; the link opens the Drive file; the list keeps the newest 150 entries | 2+ pictures of one album and day → one "Photo album" entry linking to the album; single pictures and videos one by one |
| RSS feed | `/feed.xml` · `/es/feed.xml` | the newest 100 entries of What's New | same |
| Search | `/search/` · `/es/search/` | the same documents as the Library; they open the Drive file | one entry per album |
| Monthly digest | `/digest/` · `/es/digest/`, and the e-mail when it is switched on | "Committee uploads" / "Archivos del comité": files added last month, 5 rows, then "+ N more" → `/portfolio/`. The page shows "NETA 65" and the file's date; the e-mail labels each row by folder: Reports, Notes, Slides, Workshops, Forms, Files (unknown folders) | one row per album: "Photos: &lt;album&gt;", "N new photos" |
| Committee sub-nav (under the hero of Meetings, Events, Portfolio, Photos, Bulletin, Tracker) | — | "Portfolio N" = the files on the Portfolio | "Photos N" = album photos + videos |
| Status | `/status/` · `/es/status/` | row "Google Drive (committee uploads)": state, number of items, last good check | same |

**Pages that link one particular file by its name.** They pick a committee Drive file (or a Portfolio tab) by a
rule. Rename the file so the rule no longer matches, and the link quietly disappears (most of them use `driveMatch()`
in [committee.js](../eleventy/filters/committee.js): the newest matching file wins):

| Page | Link | The rule | Set in |
|---|---|---|---|
| Meetings `/meetings/` | "Agendas and past reports in the Portfolio" | the notes tab (`/portfolio/#docs-notes`) when it has files | [meetings.njk](../src/pages/meetings.njk) |
| Monthly toolkit `/monthly/` | "Full editorial calendar" | title or file name contains "editorial calendar" or "calendario editorial" | [monthly.njk](../src/pages/monthly.njk) |
| Shop `/shop/` (price-change notice) | "Read AA Grapevine's notice" | matches `price_changes[].doc_match` | [config/site.yml](../config/site.yml) |
| GVR / RLV 101 `/orientation/` and the Portfolio | "PowerPoint copy", "Present on the web" | the title equals a deck's `drive_title` | [config/presentations/](../config/presentations/README.md) |
| Meetings (La Viña's weekly meeting), Share your story, recurring events | flyers | see [Flyers and events](flyers-and-events.md) | |

The **Portfolio page itself** also has: chips per tab with counts and a search box (`#doc-q`) that filters the
cards; a small card on the right of the header on wide screens ("Flyers to share" — or "Latest upload" when there
are no flyers or Flyers is the first tab); and, closed, "For committee members · How to add documents" (`/portfolio/#how-docs`) with the folder list,
**Open Drive folder** (the current panel folder, never the A65_GV root) and **Ask for upload access**
(grapevine@neta65.org). With two panel folders live (say Panel 77 and Panel 79), each tab groups its cards under a
panel heading, newest panel first. The old address `/documents/` (and `/es/documents/`) still works: it forwards to
the Portfolio and (with JavaScript on) keeps its `#…` part, so `/documents/#docs-reports` lands on the Reports tab.

---

## 7. Going further: change the code

Edit files on GitHub (or on your PC and push). The MKP715 login can commit to the repository; repository settings
and secrets need the NETA65 (admin) account. A push to `main` starts a quick update, so a change is live in a few
minutes — if the build fails, the old site stays up and the error is in the run log. Line numbers change all the
time, so this guide gives names to search for instead.

### 7.1 Accept another folder name for a category (e.g. "Agendas" → notes)

File: [scripts/sync/drive.py](../scripts/sync/drive.py), the dictionary `CATEGORY_SYNONYMS` (search
`"notes": ["note"`). Add the word in lower case, without accents (the matcher removes accents and capitals first):

```python
    "notes": ["note", "notes", "nota", "notas", "minutes", "minuta", "minutas", "acta", "actas",
              "agenda", "agendas"],
```

Check it on your PC (read-only):

```powershell
python -c "from scripts.sync.drive import category_for; print(category_for('Agendas'))"
```

Before the change this prints `None` (an unknown folder, its own tab); after it, `notes`. At the next update the
files of an `Agendas` folder move into the Meeting notes tab. If the new word is Spanish only, add it to
`_SPANISH_HINTS` too (titles in that folder are then read as Spanish first). Tell the members: the folder list text
is `committee.docs.folders_note` in [src/_i18n/committee.json](../src/_i18n/committee.json) (both `en` and `es`), and
README §2.

### 7.2 Never publish files with a certain word (no code)

File: [config/site.yml](../config/site.yml), `drive:` → `exclude_name_contains`:

```yaml
  exclude_name_contains: ["(Responses)", "(Respuestas)", "PRIVATE", "PRIVADO", "wrong size", "DRAFT", "BORRADOR"]
```

Checked: `2027-02-17 Committee report DRAFT.docx` and `Informe (borrador).pdf` are left out — and so is
`Drafting your GV report.pdf`, because the test is a plain substring with capitals ignored. A folder whose name
matches is skipped with everything in it. The files stay visible in Drive to anyone with the link. Built-in rules
that you cannot switch off live in `_ALWAYS_EXCLUDE_MIME` and `_ALWAYS_EXCLUDE_NAME` in drive.py. More:
[Settings](settings.md).

### 7.3 Change the order of the Portfolio tabs

File: [eleventy/filters/committee.js](../eleventy/filters/committee.js), `export const DOC_TABS`. The tabs appear in
this order; unknown folders always follow, A→Z. To show Meeting notes first:

```js
export const DOC_TABS = [
  { key: "notes", icon: "notebook-pen" },
  { key: "reports", icon: "file-bar-chart" },
  { key: "slides", icon: "presentation" },
  { key: "workshops", icon: "pen-line" },
  { key: "flyers", icon: "megaphone" },
  { key: "forms", icon: "clipboard-list" },
];
```

The small card at the right of the Portfolio header never repeats the first tab: it shows "Flyers to share" while
Flyers has files and is not the first tab, else "Latest upload" (filter `cmDocTeaser` in the same file).

### 7.4 Rename a tab, its description or the members' folder list

Most words on these pages are in [src/_i18n/committee.json](../src/_i18n/committee.json): the tab names
`committee.docs.cat.<folder>`, for example

```json
"committee.docs.cat.notes": { "en": "Meeting notes", "es": "Notas de reuniones" },
```

In the same file: the line under each tab `committee.docs.cat.<folder>_desc`, the members' box list
`committee.docs.goes_<folder>` and `committee.docs.folders_note`; the Photos page strings start with
`committee.photos.` (e.g. `committee.photos.panel_album` = "{panel} — photos"). Elsewhere: the Library's type names
are `library.cat.<folder>` in [src/_i18n/library.json](../src/_i18n/library.json); the e-mail's row labels are
`DRIVE_CATEGORIES` in [send_digest.py](../scripts/notify/send_digest.py). Keep both languages filled and the same
`{placeholders}`: `tests/test_i18n_keys.py` checks it, and the build on GitHub stops on a missing key. Details:
[Translations](translations.md).

### 7.5 Number more camera names (e.g. Pixel motion photos)

File: [scripts/sync/drive.py](../scripts/sync/drive.py), the set `_GENERIC_WORDS` (used by
`is_generic_media_name()`). Add `"mp"` at the end of the set:

```python
                  "inbound", "unnamed", "download", "file", "mp"}
```

Check it:

```powershell
python -c "from scripts.sync import drive as D; print(D.is_generic_media_name(D.name_date('PXL_20270314_150102123.MP')[1]))"
```

`False` before, `True` after: `PXL_20270314_150102123.MP.jpg` is then captioned "&lt;album&gt; #n" (its date stays
2027-03-14). The same test decides whether a **flyer**'s name is a phone name (no event), so also run
`tests/test_events_feeds.py`. To change the caption pattern itself, edit the `if generic:` block in `build_item()`
(`title = f"{label} #{f.seq}"`).

### 7.6 Show more committee files on the home page

File: [src/pages/index.njk](../src/pages/index.njk), search `homeDrive(6)`:

```jinja
{% set driveItems = D.drive.items | homeDrive(12) %}
```

The tiles are 6 to a row on a wide screen, so 12 makes two full rows. Which files count (not events, not bulletin
posts, not closed forms; newest by date) is the filter `homeDrive` in [home.js](../eleventy/filters/home.js).

### 7.7 Add a new category with its own Portfolio tab

Example: agendas get their own tab instead of joining notes.

1. [drive.py](../scripts/sync/drive.py) `CATEGORY_SYNONYMS`: add `"agendas": ["agenda", "agendas"],`.
2. [committee.js](../eleventy/filters/committee.js) `DOC_TABS`: add `{ key: "agendas", icon: "list-checks" },`
   (any Lucide icon name) where the tab should be.
3. [src/_i18n/committee.json](../src/_i18n/committee.json): add `committee.docs.cat.agendas` and
   `committee.docs.cat.agendas_desc` (English and Spanish). Without them the build on GitHub stops.
4. Library: add `library.cat.agendas` to [src/_i18n/library.json](../src/_i18n/library.json) (else the type reads
   "Agendas", made from the key); optionally add `["agendas", "<icon>"]` to `CATEGORIES` in
   [library.js](../eleventy/filters/library.js), and add the key to the list in `collectionsFor()` to put agendas in
   the "Committee reports" collection.
5. E-mail digest: add `"agendas": ("Agendas", "Agendas"),` to `DRIVE_CATEGORIES` in
   [send_digest.py](../scripts/notify/send_digest.py) (else the row says "Files" / "Archivos").
6. Members' box: add the folder to the list in [portfolio.njk](../src/pages/portfolio.njk) (search
   `["reports", "informes", "file-bar-chart"]`) together with a `committee.docs.goes_agendas` string.
7. Run the tests ([§7.10](#710-tests-to-run)). At the next update the files of an `Agendas` folder move to the new tab.

(A category that feeds a page of its own instead of the Portfolio and `/photos/` — the booth display's — is the
model in [The Drive panel folder §6.5](drive-panel-folder.md#65-a-category-with-a-page-of-its-own-the-booth-as-the-model);
the display itself is in [Booth display](booth.md).)

### 7.8 Change how albums are formed

Albums are computed in four places that must agree, or links land on the wrong spot:

- the album name: the `album = …` line in `build_item()` in [drive.py](../scripts/sync/drive.py)
  (`" / ".join(path[1:])` for sub-folders of `photos`);
- the page: `albumFolder`, `photoAlbumKey()`, `albumAnchors()` and `photoAlbums()` in
  [committee.js](../eleventy/filters/committee.js);
- What's New: `plan_whatsnew()` and `album_slug()` in [build_data.py](../scripts/sync/build_data.py) (the short link
  must equal the alias `albumAnchors()` makes);
- the e-mail digest: `album_key()` and `is_album_media()` in [send_digest.py](../scripts/notify/send_digest.py)
  (copies of `photoAlbumKey()` and `isPhotoItem()`).

Tests: `tests/test_translate.py` (`test_photo_group_links_to_its_album`) and `tests/test_digest_parity.py` (the page
and the e-mail must pick the same albums; it needs Node.js and the site's npm packages, else it is skipped).

### 7.9 Use Drive's own file description as a caption

Not possible without the `GOOGLE_API_KEY` secret: the public folder view has no descriptions. With the key, add
`description` to `API_FIELDS`, a field to `Entry` and to `ApiLister._entry()` in
[drive_listing.py](../scripts/sync/drive_listing.py), then use it in `build_item()` (for example as the item's
`summary`). Today only What's New and the RSS feed print a Drive file's summary; the Portfolio card and the photo
caption would need changes in [portfolio.njk](../src/pages/portfolio.njk) and `photoAlbums()` /
[photos.njk](../src/pages/photos.njk). Adding the secret needs the NETA65 admin account.

### 7.10 Tests to run

From the repository folder, with the project's Python ([docs/OPERATIONS.md](../docs/OPERATIONS.md)):

```powershell
python -m unittest discover -s tests
```

The ones closest to this page: `tests/test_sync_pipeline.py` (Drive: private names never stored, form check,
shortcuts), `tests/test_translate.py` (photo groups, closed forms), `tests/test_events_feeds.py` (camera names),
`tests/test_portfolio.py` and `tests/test_orientation.py` (deck copies), `tests/test_i18n_keys.py` (UI words),
`tests/test_send_digest.py` and `tests/test_digest_parity.py` (the digest). To see what the sync would do with the
real Drive: `python -m scripts.sync.drive --dry-run` (prints the stats and three items instead of saving them).

---

## 8. Troubleshooting

**Where to look first**

1. The Actions run summary (GitHub → **Actions** → the newest **Website update** run): the "Content sources" table,
   row "Google Drive (committee uploads)" — OK, or **PROBLEM** with the message; "Notes" for smaller problems (for
   example "1 folder(s) could not be read — check their sharing settings"); the module table (drive: items, new).
2. `/status/` (`/es/status/`): the row "Google Drive (committee uploads)".
3. The public file `data/raw/drive.json` on GitHub: search it for your file name. Its `stats` part near the top
   (before the list of items) shows `by_category`, `albums`, `excluded_by_reason` (only reasons — never the names
   of excluded files), the counts `loose_skipped`, `unreadable_folders`, `depth_limited` and `unconfirmed_folders`
   (counts only: since October 2026 the run's log names no file or folder that is not published either — an
   unreadable folder appears by the folder above it and its Drive address), and `warnings`. `data/site/drive.json` shows the title, translations and
   `is_new` the site uses.
4. On an empty Portfolio or Photos page, the members' box says "We checked the committee's Google Drive on &lt;date&gt; —
   nothing here yet." or "The last check of the committee's Google Drive had a problem — the last good check was on
   &lt;date&gt;."
5. After 7 days of failures the workflow opens the issue "A content source has stopped updating".

| Symptom | Cause | Fix |
|---|---|---|
| My file is not on the site | no update has run since the upload | run Website update by hand (§5) |
| … still not there after a run | the file is outside the panel folder (A65_GV root, or an older panel) | move it into 2027-2028_Panel77_GVLV; `stats.loose_skipped` counts the loose files and `skipped_panels` lists the older panels (the names: the run's log, "outside the panel folders (not published): …") |
| … still not there | the name contains PRIVATE, PRIVADO, (Responses), (Respuestas) or "wrong size", or it is a spreadsheet / CSV | rename it, or save it as PDF; `stats.excluded_by_reason` counts it |
| … still not there | its folder could not be read | run summary Notes; the run's log ("folder … unreadable: …"); share the folder "Anyone with the link — Viewer" |
| … still not there | more than 6 folder levels below the panel folder | move it up; the run's log ("folders deeper than 6 levels (not read): …") |
| A file you deleted is still there, and `/status/` says the Drive is **On hold** | the update found far fewer files than before (or a folder looked empty) and keeps them one more update, in case it was a Google hiccup | nothing: the next update removes it ([Automatic sources §3.17](automatic-sources.md#317-safety-nets-a-bad-day-at-a-source)) |
| It is in a tab named after the folder, not in Reports / Meeting notes … | the folder name has no category word (`Agendas`, `Training`, `Slideshow` …) | rename the folder (`Meeting Notes and Agendas`) or add the word (§7.1) |
| The date is wrong, or the file jumped to the top | no date in the name: the "last modified" date is used, and editing changes it; or the date was not read (`17-02-2027`, `2027-01`, a year alone), or read the American way (`05-03-2027` = May 3) | start the name with `YYYY-MM-DD` |
| No "New" badge, not in What's New, not on the home tiles | the name dates it more than 14 days back | expected; the digest still counts it. Leave the date out if it should show as new |
| Two cards look exactly alike | the date was taken out of both titles | add a word (`- February`) or use `February 2027 …` |
| Photos are in "Panel 77 (2027–2028) — photos" | they sit directly in `photos/` (or in `Fotos 2027` without a sub-folder, or loose in the panel folder) | make one sub-folder per album |
| Captions read "2027 Spring Assembly #7" | camera names | rename the files to say what they show (no people's names) |
| The numbers in captions changed | a new file sorts earlier in the folder | expected; rename the files if the caption matters |
| Two albums merged | the same sub-folder name in two panels, or in `photos/` and `fotos/` | put the year in album names |
| A What's New photo entry opens the top of `/photos/` | an album name without a short link ("Albums", "Docs 2027" …), or pictures in sub-folders of an unknown folder | rename the album; keep pictures one level deep |
| A grey tile or an icon instead of the picture | the file is not public (sharing changed), Drive has not made its preview yet, or an unusual format | check the sharing; wait a day; save the picture as JPG |
| A video does not play | Drive is still processing it, or it is not public | wait; check the sharing |
| A sign-up form disappeared | it stopped accepting responses | turn "Accepting responses" back on; it returns at the next update |
| "Present on the web" or "PowerPoint copy" is gone | the deck file was renamed ("v2", other capitals) | rename it back to the exact `drive_title`, or change `drive_title` in `config/presentations/<id>.yml` |
| "Full editorial calendar" is gone from `/monthly/` | the file name lost "editorial calendar" / "calendario editorial" | rename the file |
| A PDF in `photos/` is not on the Portfolio | `photos/` is for pictures and videos only | move it to the right folder |
| Run summary note "&lt;path&gt; has N entries — add a GOOGLE_API_KEY secret (or split the folder) so none are missed" | 500+ files in one folder; the public folder view may not list them all | split the album, or ask the NETA65 admin to add the `GOOGLE_API_KEY` secret (README §10a) |
| PROBLEM "root folder unreadable … is it shared as 'Anyone with the link'?" | the sharing of A65_GV changed | share it "Anyone with the link — Viewer"; meanwhile the site keeps the last good list |
| The Spanish (or English) title is wrong | machine translation | add a line to [overrides.yml](../data/translations/overrides.yml) (below) |

**Fix a translation.** In [data/translations/overrides.yml](../data/translations/overrides.yml) the key is the
title **exactly as the site shows it** (no date, no extension):

```yaml
"Committee report - February": { es: "Informe del comité - febrero" }
"Acta de la reunión": { en: "Meeting minutes" }
"2027 Spring Assembly": { es: "Asamblea de primavera 2027" }   # an album name
```

The album line fixes `/es/photos/`, the What's New group title and the digest row (for a nested album use the full
name, e.g. `"2027 / Spring Assembly"`). Names that must never be translated (a group's name) go in
`data/translations/glossary.yml`. An override is a push, so it is applied at the quick update that follows.
More: [Translations](translations.md).

> **Note:** README §10a says that without the API key "Drive file dates come from the file name or the day the site
> first saw the file". The code uses the "last modified" date of the Drive folder view before the first-seen day.

---

## 9. Good practice and AA principles

- **Anonymity first.** Upload only pictures in which no AA member can be recognized — booths, literature, venues,
  signs (the rule printed on `/photos/`). No full names anywhere: not on signs or name tags in a picture, not in file
  names or captions, not in minutes, reports or sign-in sheets. Use a first name and last initial, or the service
  position ("the district's GVR").
- **A file name is public.** It becomes the title on the site and is stored in the public repository
  (`data/raw/drive.json`) — even some names the site does not show are listed there (loose files and folders in
  the A65_GV root, older panel folders, and the paths of folders that could not be read or were too deep).
  Excluded files (PRIVATE, spreadsheets …) are the exception: only the reason is stored, never the name.
- **Everything in A65_GV can be opened by anyone with the link**, including the files the site hides (PRIVATE, the
  "(Responses)" sheets). Keep private drafts, contact lists and form responses out of A65_GV altogether.
- **Whose account owns the files.** Preview and Open use Drive's own viewer, and its page data can carry the
  e-mail address of the Google account that owns the file (not on screen, but readable). Upload with the
  committee's Google account, or transfer ownership of the files to it — the file ids, and so every link on the
  site, stay the same.
- **Location data.** A phone picture can carry the place it was taken inside the file, and anyone with the folder
  link can download the original. Remove the location before uploading when it matters.
- **Attraction rather than promotion.** Plain, factual titles and captions ("Literature display at the Spring
  Assembly"); no sales talk.
- **Sign-up forms:** ask only what you need; the answers are personal information.
- **Old panels can stay.** The site reads every panel folder whose number is `min_panel` (today 77) or higher
  ([Settings](settings.md)) — with two live panels, each Portfolio tab groups its cards by panel. Older panel
  folders can stay in Drive: the site skips them (only their folder names are listed in `data/raw/drive.json`).

---

## 10. See also

- [How-to guide index](README.md) · [The Drive panel folder](drive-panel-folder.md) · [File types](file-types.md)
- [Flyers and events](flyers-and-events.md) · [Bulletin](bulletin.md) · [Booth display](booth.md)
- [Presentations](presentations.md) · [Settings](settings.md) · [Translations](translations.md)
- [E-mail and alerts](email-and-alerts.md) (the monthly digest e-mail) ·
  [Automation and troubleshooting](automation-and-troubleshooting.md) · [Pages and code](pages-and-code.md)
- Code: [drive.py](../scripts/sync/drive.py) · [drive_listing.py](../scripts/sync/drive_listing.py) ·
  [build_data.py](../scripts/sync/build_data.py) · [committee.js](../eleventy/filters/committee.js) ·
  [library.js](../eleventy/filters/library.js) · [home.js](../eleventy/filters/home.js) ·
  [community.js](../eleventy/filters/community.js) · [send_digest.py](../scripts/notify/send_digest.py) ·
  [presentations.js](../eleventy/filters/presentations.js)
- Pages: [portfolio.njk](../src/pages/portfolio.njk) · [photos.njk](../src/pages/photos.njk) ·
  [library.njk](../src/pages/library.njk) · [orientation.njk](../src/pages/orientation.njk) ·
  [index.njk](../src/pages/index.njk)
- Settings and words: [config/site.yml](../config/site.yml) (`drive:`) ·
  [config/presentations/README.md](../config/presentations/README.md) ·
  [src/_i18n/committee.json](../src/_i18n/committee.json) ·
  [data/translations/overrides.yml](../data/translations/overrides.yml) · [README.md](../README.md) §2
