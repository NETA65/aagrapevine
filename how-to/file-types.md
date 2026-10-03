# File types: what every kind of file becomes

> Part of the [how-to guide](README.md). The other Drive guides start from a **folder** ("what goes in `flyers`?").
> This page starts from the **file in your hand** — a PDF, a Word file, an iPhone photo, a video, a sound file, a
> Google Form — and shows what it becomes in every folder of the panel folder: which kind of item, whether it gets
> a picture, whether its text is read, whether it can become an event, and where it shows on the website. The
> folder rules themselves (panel folders, sharing, dates in names) are in
> [The Drive panel folder](drive-panel-folder.md).

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start: "I have this file — where does it go?"](#2-quick-start-i-have-this-file--where-does-it-go)
3. [The cross-reference](#3-the-cross-reference) —
   [every type in every folder](#31-every-file-type-in-every-folder) ·
   [what each type carries](#32-what-each-file-type-carries) ·
   [files straight in the panel folder](#33-files-dropped-straight-into-the-panel-folder)
4. [Full reference with examples](#4-full-reference-with-examples) —
   [how the type is read](#41-how-the-site-tells-the-type-of-a-file) ·
   [PDF](#42-pdf) · [Word, .odt, .rtf](#43-word-opendocument-text-and-rtf-docx-doc-odt-rtf) ·
   [.txt, .md](#44-plain-text-and-markdown-txt-md) · [Google Docs](#45-google-docs) ·
   [slides](#46-slides-powerpoint-keynote-opendocument-google-slides) · [Google Drawings](#47-google-drawings) ·
   [Google Forms](#48-google-forms) · [spreadsheets](#49-spreadsheets-never-published) ·
   [pictures and iPhone photos](#410-pictures-and-iphone-heic-photos) ·
   [videos](#411-videos-and-how-big-is-too-big) · [sound](#412-sound-files-mp3-m4a-wav-ogg) ·
   [.zip, .epub](#413-zip-and-epub) · [shortcuts](#414-shortcuts) · [folders](#415-folders) ·
   [other types](#416-any-other-type) · [never published](#417-never-published-the-complete-list) ·
   [the booth folder](#418-the-booth-folder)
5. [The "kind" of a file in the data, and how pages use it](#5-the-kind-of-a-file-in-the-data-and-how-pages-use-it)
6. [Naming tips per type](#6-naming-tips-per-type)
7. [What happens next](#7-what-happens-next)
8. [Where it shows on the website](#8-where-it-shows-on-the-website)
9. [Going further: change the code](#9-going-further-change-the-code)
10. [Troubleshooting](#10-troubleshooting)
11. [Good practice and AA principles](#11-good-practice-and-aa-principles)
12. [See also](#12-see-also)

---

## 1. What this is

The committee's files live in the public Google Drive folder **A65_GV**, inside the panel folder
**2027-2028_Panel77_GVLV**, sorted into folders: `flyers`, `bulletin`, `photos`, `reports`, `notes`, `slides`,
`workshops`, `forms`, `booth` — or any folder name of your own. Every update of the website reads that folder and
turns each file into an item on the site.

Two things decide what a file becomes:

1. **The folder.** Only the first folder below the panel folder counts (`photos/2027/Spring/x.jpg` is in
   `photos`). Its name says the category: flyers, bulletin, photos, documents (reports, notes, slides, workshops),
   sign-ups (forms), booth, or "other" (any other name). English and Spanish names both work — the full list of
   folder words is in [The Drive panel folder](drive-panel-folder.md#35-the-category-folders).
2. **The file type.** Drive tells the site what each file is — its *MIME type*, for example `application/pdf` or
   `image/jpeg`. Only when Drive says nothing useful does the site look at the ending of the name (`.pdf`, `.jpg`).

Three facts explain most of this page:

- **The site reads file names, not files** — with two exceptions: in `bulletin` the text of a Google Doc, `.txt`,
  `.md` or `.docx` becomes the post, and in `booth` the same four types become message slides. Everywhere else
  only the name is used (title, date, event details). (Google Forms are also asked once per update whether they
  still accept answers.)
- **No file is copied into the website's repository** — only its name, its links and, for a bulletin post or a
  booth message, its text (all public, in `data/raw/drive.json`). Cards, albums and players ask Google for the
  picture, preview or video when a visitor opens the page. The one exception is the booth display: each update
  saves copies of its pictures, videos and sound files and publishes them with the site, so it can play offline —
  still never in the repository ([Booth display](booth.md)).
- **Some types are never published**, whatever the folder: spreadsheets (Google Sheets, Excel, CSV, TSV,
  OpenDocument and Numbers sheets), Apps Script projects and Google Sites — plus any file whose name contains
  `PRIVATE`, `PRIVADO`, `(Responses)`, `(Respuestas)` or `wrong size`, and the leftovers computers make
  (`desktop.ini`, `Thumbs.db`, `~$…` lock files).

Where Drive files show up (site address `https://neta65.github.io/aagrapevine`; the Spanish pages add `/es`):

| Page | English | Spanish |
|---|---|---|
| Portfolio (documents, slides, sign-up forms; one tab per folder) | `/portfolio/` | `/es/portfolio/` |
| Photos (albums of pictures and videos) | `/photos/` | `/es/photos/` |
| Events (dated flyers) and the calendar files | `/events/`, `/events.ics` | `/es/events/`, `/es/events.ics` |
| Bulletin (posts from the `bulletin` folder) | `/bulletin/` | `/es/bulletin/` |
| Library (documents, next to the magazines' own PDFs) | `/library/` | `/es/library/` |
| Home page: "Shared by the committee" (Drive files), "From the committee" (bulletin), "Upcoming events" | `/` | `/es/` |
| What's New and the RSS feed | `/whats-new/`, `/feed.xml` | `/es/whats-new/`, `/es/feed.xml` |
| Site search | `/search/` | `/es/search/` |
| Monthly digest (and the monthly e-mail) | `/digest/` | `/es/digest/` |
| Booth display (files of the `booth` folder only) | `/about/#booth` | `/es/about/#booth` |
| Status (how many Drive files were read, when the last good check was) | `/status/` | `/es/status/` |

---

## 2. Quick start: "I have this file — where does it go?"

| I have… | Put it in | Name it like this | What you get |
|---|---|---|---|
| A flyer for a one-day event (PDF, JPG or PNG) | `flyers` | `2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` | a card in the Portfolio's **Flyers** tab **and** an event on `/events/`: "Spring Assembly booth", Sunday, March 14, 2027, 9:00 AM, Tyler Civic Center |
| A notice for groups, GVRs and RLVs | `bulletin` | a Google Doc named `2027-01-10 Welcome new GVRs` | a post on `/bulletin/` headed "Welcome new GVRs", dated January 10, 2027, with the Doc's text |
| Pictures from an event (JPG, or iPhone HEIC) | `photos/2027 Spring Assembly` | `Literature display.jpg` (or keep `IMG_0142.HEIC`) | an album "2027 Spring Assembly" on `/photos/`; caption "Literature display" — or "2027 Spring Assembly #3" for a camera name |
| A short video from an event | the same album folder | `Room setup.mov` | a video in the album, played by Drive's own player |
| A report or minutes (PDF, Word, Google Doc) | `reports` or `notes` | `2027-02-17 Committee report - February.pdf` | a **Document** card in the Reports (or Meeting notes) tab: "Committee report - February", February 17, 2027 |
| A slide deck (PowerPoint, Google Slides) | `slides` | `GVR and RLV Orientation Workshop.pptx` | a **Slides** card — with **Present on the web** when the name is exactly one of the four web decks' |
| A sign-up form | `forms` | a Google Form named `Spring Assembly volunteers` | a **Form** card with a **Sign up** button (it goes away by itself once the form stops accepting answers) |
| A workshop recording (MP3) | `workshops` | `Writing workshop - recording.mp3` | a **Document** card in the Workshops tab; Preview plays it in Drive's player |
| A picture, video, sound file or short text for the screen at our table | `booth` | `GV EN Welcome to our table (first) (15s).png` | a slide of the booth display (and nowhere else on the site) |
| A spreadsheet, a CSV, a form's answers sheet | **not in A65_GV** | — | never published — but anyone with the folder link could open it there |

Then:

1. Upload the file into the folder (Google Drive → **A65_GV** → **2027-2028_Panel77_GVLV** → the folder).
2. Give it a clear name: a date first when it belongs to a day (`2027-03-14 …`), then what it is. No people's names.
3. Wait for the next update — normally the next morning — or start one: GitHub → **Actions** → **Update &
   Deploy** → **Run workflow**, tick **skip_crawl**, press the green **Run workflow**. It takes a few minutes.
4. Check the page from the table above. Nothing there? See [Troubleshooting](#10-troubleshooting).

---

## 3. The cross-reference

### 3.1 Every file type in every folder

How to read the cells:

- **Card: Document / Slides / Image / Video / Form** — a card on the Portfolio (`/portfolio/`) in that folder's
  tab; the word is the label printed on the card (a PDF's card says "Document" too). A Form card has a **Sign up**
  button instead of Preview and Download.
- **+ event** (flyers only) — when the name holds a day date (`2027-03-14 …`) and is not a phone's own name
  (`IMG_20270314_101010.jpg`), the file **also** becomes an event on `/events/`. See
  [Flyers and events](flyers-and-events.md).
- **Post (text)** / **Post (title only)** — a post on `/bulletin/`. "Text": the file's words are the post.
  "Title only": the post is the headline (the file name), the date and an **Open the document** button.
- **Album photo / Album video** — on `/photos/`, in the album named after the sub-folder.
- **Hidden ¹** — no Portfolio card, no album, not in the Library; only the home tiles, What's New, the RSS feed and
  the digest list it. Move such a file to the right folder.
- Booth column — what the booth display does with it: **Photo** (fills the screen), **Poster** (the whole picture),
  **Video**, **Sound**, **Message** (a text slide), or **Problem** (never shown; listed with the reason).
- **Never** — never published ([4.17](#417-never-published-the-complete-list)).

| File type | `flyers` | `bulletin` | `photos` | `reports` `notes` `slides` `workshops` | `forms` | `booth` | any other folder name |
|---|---|---|---|---|---|---|---|
| PDF | Card: Document + event | Post (title only) | Hidden ¹ | Card: Document | Card: Document | Poster (page 1) | Card: Document, in a tab named after the folder |
| Word `.docx` | Card: Document + event | Post (text) ² | Hidden ¹ | Card: Document | Card: Document | Message ² | Card: Document |
| Word `.doc` (old format) | Card: Document + event | Post (title only) | Hidden ¹ | Card: Document | Card: Document | Problem | Card: Document |
| PowerPoint `.pptx` `.ppsx` `.ppt` `.pps` | Card: Slides + event | Post (title only) | Hidden ¹ | Card: Slides | Card: Slides | Poster (slide 1) | Card: Slides |
| Keynote `.key` | Card: Slides + event | Post (title only) | Hidden ¹ | Card: Slides | Card: Slides | Poster (slide 1) ³ | Card: Slides |
| OpenDocument text `.odt` | Card: Document + event | Post (title only) | Hidden ¹ | Card: Document | Card: Document | Problem | Card: Document |
| OpenDocument slides `.odp` | Card: Slides + event | Post (title only) | Hidden ¹ | Card: Slides | Card: Slides | Poster (slide 1) | Card: Slides |
| Plain text `.txt` | Card: Document + event | Post (text) | Hidden ¹ | Card: Document | Card: Document | Message | Card: Document |
| Markdown `.md` | Card: Document + event | Post (text) | Hidden ¹ | Card: Document | Card: Document | Message | Card: Document |
| Rich text `.rtf` | Card: Document + event | Post (title only) ⁴ | Hidden ¹ | Card: Document | Card: Document | Problem | Card: Document |
| Google Doc | Card: Document + event | Post (text) | Hidden ¹ | Card: Document | Card: Document | Message | Card: Document |
| Google Slides | Card: Slides + event | Post (title only) | Hidden ¹ | Card: Slides | Card: Slides | Poster (slide 1) | Card: Slides |
| Google Drawing | Card: Document + event | Post (title only) | Hidden ¹ | Card: Document | Card: Document | Poster | Card: Document |
| Google Form | Card: Form + event ⁵ | Post (title only) ⁶ | Hidden ¹ | Card: Form, in that tab | Card: Form | Problem | Card: Form, in the **Sign-ups** tab |
| Google Sheets | Never | Never | Never | Never | Never | Never | Never |
| Excel `.xlsx` `.xls` `.xlsm`, `.csv`, `.tsv`, `.ods`, `.numbers` | Never | Never | Never | Never | Never | Never | Never |
| Pictures `.jpg` `.jpeg` `.heic` `.heif` `.tif` `.tiff` | Card: Image + event | Post (title only) | Album photo | Card: Image | Card: Image | Photo | Album photo, in an album named after the folder |
| Pictures `.png` `.gif` `.webp` `.bmp` `.svg` | Card: Image + event | Post (title only) | Album photo | Card: Image | Card: Image | Poster | Album photo, in an album named after the folder |
| Videos `.mp4` `.m4v` `.mov` `.webm` | Card: Video + event | Post (title only) | Album video | Card: Video | Card: Video | Video | Album video |
| Videos `.avi` `.wmv` `.mkv` `.3gp` | Card: Video + event | Post (title only) | Album video | Card: Video | Card: Video | Problem ("save it as .mp4") | Album video |
| Sound `.mp3` `.m4a` `.wav` `.ogg` | Card: Document + event | Post (title only) | Hidden ¹ | Card: Document | Card: Document | Sound | Card: Document |
| `.zip`, `.epub` | Card: Document + event | Post (title only) | Hidden ¹ | Card: Document | Card: Document | Problem | Card: Document |
| A Drive shortcut | as the file it points to ⁷ | as the file it points to ⁷ | as the file it points to ⁷ | as the file it points to ⁷ | as the file it points to ⁷ | needs the ending in its name ⁷ | as the file it points to ⁷ |
| A sub-folder | read too; still flyers | read too; still posts | each sub-folder is its own album | read too; same tab | read too; same tab | each sub-folder is a collection | read too; one tab and one album for the whole folder |

¹ `photos` is for pictures and videos only. Anything else there gets no card and no album and is left out of the
Library; it still appears on the home page's "Shared by the committee" tiles, in What's New, the RSS feed and the
digest.
² Only the words of each paragraph: bold, heading styles and the addresses behind links are lost, and a line break
made with Shift+Enter joins two lines into one ("Line oneLine two"). Press Enter for a new line — see
[4.3](#43-word-opendocument-text-and-rtf-docx-doc-odt-rtf).
³ The booth shows Drive's picture of the first slide. Drive may not be able to make one for a Keynote file —
export it as PDF or PowerPoint.
⁴ When Drive reports an `.rtf` file as plain text (`text/rtf`), its raw RTF codes become the "text". Don't post
`.rtf` files; use a Google Doc, `.docx`, `.txt` or `.md`.
⁵ Rarely what you want: a dated form becomes an event whose **View flyer** button opens the form, and the event
stays after the form closes. Keep forms in `forms`.
⁶ A form in `bulletin` is a headline-only post whose button opens the form, and it is never checked for "closed".
⁷ With the optional `GOOGLE_API_KEY` secret the site learns the real type of the file a shortcut points to.
Without it (the case today) the type comes from the **shortcut's name**: `Flyer.pdf` works as a PDF; a shortcut
named `Volunteer sign-up` (no ending) is a plain Document card — see [4.14](#414-shortcuts).

> **Note:** the comment above `drive:` in [config/site.yml](../config/site.yml) says "Any other folder name shows
> up in the Library under its own name". In the code an unknown folder's name is its **Portfolio** tab
> (`documentTabs()` in [committee.js](../eleventy/filters/committee.js)); the Library files those documents under
> the type "Other" / "Otros" (`docKitType()` in [library.js](../eleventy/filters/library.js)).

### 3.2 What each file type carries

**Picture:** every card asks Google for a small picture of the file (600 pixels wide). Drive makes one for most
PDFs, Office and Google files, pictures and videos; when it has none (a sound file, a `.zip`), the card shows its
type icon instead — nothing breaks. **Preview** and **Download** are the Portfolio's buttons (Preview opens Drive's
own viewer inside the page; **Open** opens the file on Drive).

| File type | `kind` in the data | Picture on cards | Preview / Open | Download button gives | Text read? | Can be an event? | Library and search |
|---|---|---|---|---|---|---|---|
| PDF | `document` | first page | yes | the PDF | no | in `flyers` | yes |
| Word `.docx` | `document` | first page | yes | the `.docx` | in `bulletin`, `booth` | in `flyers` | yes |
| Word `.doc`, `.odt`, `.rtf` | `document` | first page, if Drive makes one | yes | the file | no | in `flyers` | yes |
| `.txt`, `.md` | `document` | Drive's picture of the text, if any | yes | the file | in `bulletin`, `booth` | in `flyers` | yes |
| Google Doc | `document` | first page | yes | a PDF copy | in `bulletin`, `booth` | in `flyers` | yes |
| PowerPoint, Keynote, `.odp` | `slides` | first slide, shown whole (16:9) | yes | the file | no | in `flyers` | yes |
| Google Slides | `slides` | first slide, shown whole | yes | a PDF copy | no | in `flyers` | yes |
| Google Drawing | `document` | the drawing | yes | a PNG copy | no | in `flyers` | yes |
| Google Form | `form` | Drive's picture, if any | no — a **Sign up** button | no button | no | in `flyers` ⁵ | yes, while it is open |
| Pictures | `photo` | the picture (a smaller copy Google makes — HEIC and TIFF too) | yes; on `/photos/` a full-screen slideshow | the original file (a HEIC stays HEIC) | no | in `flyers` | no ⁸ |
| Videos | `video_file` | a frame, once Drive has processed the video | Drive's player | the original file | no | in `flyers` | no ⁸ |
| Sound | `document` | usually none — the icon | Drive's player | the original file | no | in `flyers` | yes |
| `.zip`, `.epub` | `document` | usually none — the icon | Drive's viewer (it may only offer a download) | the original file | no | in `flyers` | yes |
| A shortcut without an ending in its name | `document` | the target's picture, once the shortcut is followed | Drive's viewer | no button | no | in `flyers` | yes |
| Anything in `bulletin` | `announcement` (replaces the above) | only in the RSS feed, and only for a PDF or a picture | **Open the document** (none for a `.md` or `.txt` whose text is shown) | — | Google Doc, `.txt`, `.md`, `.docx` | no | the post is searchable; not in the Library |
| Anything in `booth` | its usual kind (the booth has its own: photo, poster, video, audio, message) | made for the booth display | — | — | Google Doc, `.txt`, `.md`, `.docx` | no | no |

⁸ Pictures and videos are never in the Library. Those in albums are searchable through their album (one search
entry per album, linking to `/photos/#…`); a picture or video in another folder has no search entry of its own
(a dated flyer's event does).

"Library and search" means: a card on `/library/` (type = the folder: "Committee reports", "Meeting notes",
"Slides", "Workshops", "Flyers", "Forms", or "Other") and an entry in `/search/` that opens the Drive file. Files in
`photos` and `bulletin` never reach the Library (code: `libraryDocs()` and its `DRIVE_SKIP_KINDS` /
`DRIVE_SKIP_CATS` lists in [library.js](../eleventy/filters/library.js)).

### 3.3 Files dropped straight into the panel folder

A file that sits directly in 2027-2028_Panel77_GVLV (in no sub-folder) gets its category from its kind (code:
`build_item()` in [drive.py](../scripts/sync/drive.py)):

| File | Becomes |
|---|---|
| a picture or video — `Panel photo.jpg`, `IMG_9999.jpg`, `clip.mp4` | an album photo or video in the panel's own album "Panel 77 (2027–2028) — photos" (Spanish: "… — fotos"); a camera name is captioned "Photo #2" (or "Video #3") |
| a Google Form — `Quick poll` | a Form card in the **Sign-ups** tab |
| slides — a Google Slides file `Committee deck`, `Deck.pptx` | a Slides card in the **Slides** tab |
| anything else — `2027-03-14 Spring Assembly.pdf`, a Google Doc, an MP3 | a card in a tab called **Other** / **Otros**; Library type "Other" |

It works, but a folder is clearer for everyone. Details: [Photos, slides, reports …](photos-slides-reports.md).

---

## 4. Full reference with examples

Every example on this page was run through the site's own code (the functions named in each section) with the
real settings. "Upload day" means the "last modified" date the Drive folder shows for the file.

### 4.1 How the site tells the type of a file

**Where the type comes from** (code: `HtmlLister._parse_entry()`, `guess_mime()` and `ApiLister._entry()` in
[drive_listing.py](../scripts/sync/drive_listing.py)):

- **Without the API key** — the case today (`stats.mode` is `html` in `data/raw/drive.json`): Drive's public folder
  view shows a small type icon beside each file, and the icon's address carries the MIME type (`image/png`,
  `application/pdf` …). A Google file without an icon is known by its link (`docs.google.com/document/…`,
  `/presentation/`, `/forms/`, `/spreadsheets/`, `/drawings/`). Failing both, the ending of the name decides
  (`.heic` → `image/heic`, `.md` → `text/markdown` …), and an unknown ending is `application/octet-stream`.
- **With the optional `GOOGLE_API_KEY` secret** — Drive's own `mimeType`, plus exact dates, file sizes (shown on
  `/library/` cards), a photo's camera time and a video's length. Adding the secret needs the NETA65 (admin)
  account ([The Drive panel folder](drive-panel-folder.md#315-the-optional-google_api_key)).

**From the type to the kind** (code: `kind_for()` in [drive.py](../scripts/sync/drive.py)). The first rule that
fits wins:

| Rule | `kind` |
|---|---|
| the MIME type starts with `image/` | `photo` |
| the MIME type starts with `video/` | `video_file` |
| it is a Google Form | `form` |
| the MIME type contains `presentation`, `powerpoint` or `keynote` — or the name ends in `.ppt`, `.pptx`, `.pps`, `.ppsx`, `.odp`, `.key` | `slides` |
| anything else: PDF, Word, Google Doc, Google Drawing, text, sound, `.zip`, `.epub`, unknown types | `document` |
| and then: **every** file in the bulletin folder | `announcement` (replaces the kind above) |

So a Google Drawing and an MP3 are "documents", and a picture in `flyers` is a `photo` (a Portfolio card labelled
Image, not an album photo). What each kind does on the pages: [section 5](#5-the-kind-of-a-file-in-the-data-and-how-pages-use-it).

**Which endings are taken out of the title** (code: `_KNOWN_EXT` and `strip_ext()` in drive.py; any capitals):
`.pdf .doc .docx .ppt .pptx .pps .ppsx .odp .odt .rtf .txt .md .key .pages .jpg .jpeg .png .gif .webp .heic .heif
.tif .tiff .bmp .svg .mp4 .m4v .mov .avi .wmv .webm .mkv .3gp .mp3 .m4a .wav .ogg .zip .epub`. `Report.PDF` and
`Report.Docx` both become "Report". **Any other ending stays in the title**:

| File | Title |
|---|---|
| `photos/2027 Spring Assembly/Literature table.jfif` | "Literature table.jfif" |
| `photos/2027 Spring Assembly/Literature table.avif` | "Literature table.avif" |
| `photos/2027 Spring Assembly/Room.mpg` | "Room.mpg" (a video) |
| `bulletin/Welcome new GVRs.markdown` | headline "Welcome new GVRs.markdown" (its text is still read) |
| `workshops/Song.aac`, `workshops/Notes.html` | "Song.aac", "Notes.html" |

Rename such files (`.jpg`, `.md`, `.mp4`, `.mp3`), or add the ending to the list
([9.1](#91-take-another-ending-out-of-titles-jfif-avif-markdown)). The booth folder has its own, longer list
([4.18](#418-the-booth-folder)).

**The type label** (code: `file_type_label()` in drive.py) is stored as `extra.file_type`: "Google Doc", "Google
Slides", "Google Drawing" or "Google Form" for Google files; otherwise the ending in capitals ("PDF", "DOCX",
"HEIC"; `.jpg` gives "JPEG"); "Shortcut" for a shortcut whose name has no ending. The same word, in small letters,
is the file's second tag (`pdf`, `jpeg`, `google-doc`); the first tag is the panel (`panel-77`).

**The date a file gets** (code: `build_item()` in drive.py) — the same for every type, by folder:

| Where | Date = the first of these that exists |
|---|---|
| `flyers` | the upload day (the date in a flyer's name is the **event's** date, not the card's) |
| a picture anywhere else | a date in the name → when the camera took it (only with the API key) → the upload day |
| everything else | a date in the name → (bulletin) the `(from …)` day → the upload day |
| still nothing | the day the site first saw the file |

Without the API key the "upload day" is the "last modified" date of Drive's folder view, so **editing an undated
file re-dates it** (it moves up the Portfolio and shows as new again). With the key it is the day the file was
created. Start the name with `YYYY-MM-DD` to fix a date for good.

> **Note:** the comment under `drive:` in [config/site.yml](../config/site.yml) ("else dates come from file names /
> first-seen") and README section 10, part a ("from the file name or the day the site first saw the file") leave out
> a step: in the code the folder view's "last modified" date comes **before** the day first seen
> (`build_item()` and `merge()` in drive.py).

Everything else a name can carry — "Copy of", " (1)", camera names, `(pinned)` and the other markers — is the same
for every type: see [The Drive panel folder](drive-panel-folder.md#39-titles-from-file-name-to-title) and, for
photos, [Photos, slides, reports …](photos-slides-reports.md#47-photos--photo-albums).

### 4.2 PDF

The safest type for anything people will read or print: Drive previews it, makes a picture of its first page for
the card, and **Download** gives exactly your file. `kind`: `document`.

| File | What you get | Where it shows |
|---|---|---|
| `reports/2026-08-11 Grapevine Area Chair Meeting Report.pdf` (a real file) | a Document card "Grapevine Area Chair Meeting Report", August 11, 2026, with the first page as its picture | Portfolio → Reports (`/portfolio/#docs-reports`, `/es/portfolio/#docs-reports`); Library, type "Committee reports"; search; home tiles; What's New; digest (row "Reports" in the e-mail) |
| `notes/2026-10-01 Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf` (real) | "Grapevine & La Viña Pricing Update - Effective January 1, 2027", October 1, 2026 | Meeting notes tab; it is also the **Read AA Grapevine's notice** link on `/shop/`, found by its name (`price_changes` → `doc_match` in [config/site.yml](../config/site.yml)) |
| `flyers/2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` | a Flyers card "Spring Assembly booth 9am @ Tyler Civic Center" (dated its upload day) **and** the event "Spring Assembly booth", Sunday, March 14, 2027, 9:00 AM, at Tyler Civic Center | Portfolio → Flyers; `/events/` with a **View flyer** button and page 1 as the flyer picture; `/events.ics`; home "Upcoming events"; Library ("Flyers", "Event: March 14, 2027") |
| `flyers/Spring Assembly booth - Tyler Civic Center.pdf` (no date) | only the Flyers card — no event | Portfolio; it can still be attached to an event ([Flyers and events §5](flyers-and-events.md#5-use-a-flyer-without-a-date)) |
| `bulletin/2027-03-14 Spring Assembly flyer.pdf` | a headline-only post "Spring Assembly flyer", dated March 14, 2027, with **Open the document** | `/bulletin/` (the PDF itself is not shown there), home "From the committee", What's New, RSS (with page 1 as a picture) |
| `photos/2027 Spring Assembly/Program.pdf` | **hidden**: no card, no album, not in the Library | only the home tiles, What's New, RSS and the digest — move it to `workshops` or a folder of its own |
| `forms/Volunteer sign-up sheet.pdf` | a Document card in the **Sign-ups** tab (Preview, Open, Download) | Portfolio → Sign-ups; Library ("Forms") |
| `booth/Grapevine and La Viña - ways to carry the message.pdf` | a **poster** slide: Drive's picture of page 1, both magazines, every language | the booth display only |
| `Archive/2025 Panel 75 summary.pdf` (an unknown folder) | a Document card "2025 Panel 75 summary" (a year alone is not a date) | Portfolio tab "Archive" (`/portfolio/#docs-folder-archive`); Library "Other" |

A bulletin post dated in the future (like the March 14 example) sorts above the other posts until newer-dated
ones arrive; [Bulletin](bulletin.md) explains dates and markers.

### 4.3 Word, OpenDocument text and RTF (`.docx`, `.doc`, `.odt`, `.rtf`)

All four are `document` cards, previewed by Drive; **Download** gives the file itself (people need Word or a
compatible program to open it — a PDF is friendlier for reading). The difference is in the two folders that read
text:

| Type | `bulletin` | `booth` |
|---|---|---|
| `.docx` | a post **with text**: the words of each paragraph (`docx_to_text()` in drive.py) | a **message** slide with that text |
| `.doc` (Word 97–2003) | headline-only post | Problem: "not a type the booth can show" |
| `.odt` (LibreOffice, OpenOffice) | headline-only post | Problem: "not a type the booth can show" |
| `.rtf` | headline-only post — unless Drive calls it `text/rtf`; then its raw codes become the text | Problem: "not a type the booth can show" |

What the Word reader keeps and loses (the same in `bulletin` and `booth`):

- bulleted and numbered items become bullets;
- a paragraph you start with `# ` is a heading (on the booth screen, a bold line);
- a first paragraph that repeats the file name is dropped;
- bold, italics, heading *styles* and the addresses behind links are lost (only the link's words stay);
- a table loses its shape: each cell becomes a paragraph of its own;
- **a line break made with Shift+Enter joins the two lines**: "Line one" + "Line two" becomes "Line oneLine two".
  Use Enter for every new line;
- **a `.docx` bigger than 3 MB is not read at all** (usually because pictures were pasted into it): the site
  downloads only the first 3 MB of a text file (`MAX_TEXT_DOWNLOAD` in drive.py), and a cut Word file cannot be
  opened — the post keeps only its headline (or its last good text), and in the booth the message becomes a
  problem, "no text to show" (unless an earlier run read its text, which is then kept). Keep pictures out of Word
  files meant for the bulletin or the booth.

| File | What you get |
|---|---|
| `notes/2027-02-17 Minutes.docx` | Meeting notes tab: Document card "Minutes", February 17, 2027 |
| `notes/March 2027 Committee Meeting.docx` | "March 2027 Committee Meeting", dated March 1, 2027 (a month alone stays in the title) |
| `notes/2027-02-17 Minutes.doc`, `….odt`, `….rtf` | the same card "Minutes", February 17, 2027 |
| `bulletin/Welcome new GVRs.docx` | post "Welcome new GVRs" with the document's paragraphs, dated its upload day, **Open the document** |
| `bulletin/Welcome new GVRs.odt` | post "Welcome new GVRs" with **no text** — only the headline and **Open the document** |
| `booth/GV EN Welcome message.docx` | booth message slide: heading "Welcome message", Grapevine colour, English |
| `flyers/2027-03-14 Spring Assembly flyer.docx` | Flyers card + event "Spring Assembly flyer" on March 14, 2027 (it works, but people expect a picture or a PDF) |

### 4.4 Plain text and Markdown (`.txt`, `.md`)

Outside `bulletin` and `booth` a text file is just a Document card (Drive shows its raw text in the preview). In
those two folders its words are the content:

- **`bulletin`** — the whole file is the post, and Markdown works: `# ` headings, `- ` lists, `**bold**`, links,
  tables. Because the page already shows every word, a `.txt` or `.md` post gets **no** "Open the document" button.
  The file is read as UTF-8 (with or without the mark Windows Notepad adds), UTF-16 with that mark, else as Windows
  "ANSI" text — so "Viña" survives every common editor (`_decode()` in drive.py). At most 12,000 characters are
  kept.
- **`booth`** — a **message** slide: the name is the heading, the text is the message. The player keeps it
  "Markdown-light": paragraphs, line breaks, `**bold**` and `- ` bullets; a `# ` heading becomes a bold line;
  links keep only their words; pictures, tables and code are dropped. At most 1,200 characters are kept, and about
  the first 600 fit on the screen (`message_text()` in [booth_names.py](../scripts/sync/booth_names.py)).

| File | What you get |
|---|---|
| `bulletin/Welcome_new_GVRs.txt` | post "Welcome new GVRs" (underscores become spaces) with the file's text, no button |
| `bulletin/Grapevine and La Viña — ways to carry the message.md` (the real post) | a long post whose `# ` headings make an "In this post" list beside it |
| `bulletin/Welcome new GVRs.markdown` | the text is read, but the headline keeps ".markdown" — use `.md` |
| `notes/2027-02-17 Minutes.txt` | Meeting notes tab: Document card "Minutes", February 17, 2027 |
| `booth/GV EN Ask us about Grapevine.txt` | message slide "Ask us about Grapevine" (Grapevine, English) with the file's `- ` lines as bullets |
| `booth/LV ES Pregúntanos sobre La Viña.md` | message slide "Pregúntanos sobre La Viña" (La Viña, Spanish) |

A header block (`---` / `title: …` / `---`) at the top of a Drive `.md` file is **not** read: it shows as a line
and a heading. Header options exist only for posts written in the repository's `content/bulletin/` folder —
[Bulletin](bulletin.md).

### 4.5 Google Docs

A Google Doc has no ending in its name; the name is the title. `kind`: `document`. **Download** gives a PDF copy
made by Google; **Open** opens the Doc itself. The Doc must be readable by "anyone with the link" — it inherits
that from the folder unless someone changed its own sharing.

| File (a Google Doc) | What you get |
|---|---|
| `reports/Committee report - February` | Reports tab: Document card "Committee report - February", dated by its last change (no date in the name — without the API key, every edit re-dates it) |
| `bulletin/2027-01-10 Welcome new GVRs` | post "Welcome new GVRs", January 10, 2027, with the Doc's words; **Open the document** |
| `booth/GV EN Welcome message` | booth message slide "Welcome message" |
| `flyers/2027-03-14 Spring Assembly flyer` | Flyers card + event on March 14, 2027 |

In `bulletin` and `booth` the site reads Google's plain-text copy of the Doc: words only. Toolbar formatting (bold,
heading styles, pictures, a link hidden behind words) does not come through — type `# ` in front of a heading and
paste web addresses in full. A first line that repeats the file name is dropped (Docs often start with the
title).

### 4.6 Slides: PowerPoint, Keynote, OpenDocument, Google Slides

`kind`: `slides`. The card's picture is the first slide, shown **whole** (16:9) on the Portfolio and on the home
tiles. **Download** gives the file (for Google Slides, a PDF copy).

| File | What you get |
|---|---|
| `slides/GVR and RLV Orientation Workshop.pptx` (real) | Slides tab: "GVR and RLV Orientation Workshop" with a **Present on the web** button — its title equals the `drive_title` of the web deck in `config/presentations/orientation-workshop.yml` ([Presentations](presentations.md)); `/orientation/` also links it as the deck's "PowerPoint copy" |
| `slides/GVR and RLV Orientation Workshop.ppsx` (a "PowerPoint Show") | the same kind of Slides card; the download opens straight into the show |
| `slides/Spring Assembly report` (Google Slides) | Slides card; Download gives a PDF |
| `slides/Spring Assembly report.key` (Keynote) | Slides card — Drive may not preview a Keynote file; export it to PowerPoint or PDF for everyone else |
| `slides/Slide 1.png` | an **Image** card in the Slides tab (a picture stays a picture) |
| `Committee deck` (Google Slides straight in the panel folder) | Slides tab |
| `booth/…pptx`, Google Slides, `.key`, `.odp` in the booth | a **poster** slide made from Drive's picture of the first slide |
| `photos/2027 Spring Assembly/Slideshow.pptx` | **hidden** (not on the Portfolio) — keep decks in `slides` |

A deck renamed away from its exact `drive_title` ("… v2") loses **Present on the web** and the "PowerPoint copy"
link on `/orientation/` — rename it back or change `drive_title`.

### 4.7 Google Drawings

A Google Drawing is a `document` (not a picture). Its card shows the drawing; **Download** gives a PNG copy. Good
for a quick flyer: in `flyers` with a dated name it becomes an event like any flyer
(`flyers/2027-03-14 Spring Assembly flyer` → Flyers card + event). In `booth` it is a **poster**. In `bulletin` it
is a headline-only post. Pictures exported from it (PNG, JPG) behave as pictures
([4.10](#410-pictures-and-iphone-heic-photos)).

### 4.8 Google Forms

`kind`: `form`. A Form card has one button, **Sign up**, which opens the form; there is no Preview and no
Download. Each update checks every form once (`check_forms()` in drive.py):

- **closed** (Google answers with its "no longer accepting responses" page) → the form is left out of the site data
  — off the Portfolio, the Library, the search, the home tiles, What's New and the digest — and comes back by itself
  at the first update after you switch "Accepting responses" on again;
- **members only** (Google asks people to sign in) → still shown;
- **undecided** (a network hiccup) → yesterday's answer is kept.

| Form | Where it goes |
|---|---|
| `forms/Spring Assembly volunteers` | Sign-ups tab (`/portfolio/#docs-forms`, `/es/portfolio/#docs-forms`); Library "Forms" while open |
| `reports/Volunteer form` | a Form card in the **Reports** tab (a form in a built-in tab stays in that tab) |
| `Archive/Volunteer form` (an unknown folder) | the **Sign-ups** tab (a form never gets a folder tab of its own); Library "Other" |
| `Quick poll`, straight in the panel folder | Sign-ups tab |
| `photos/2027 Spring Assembly/RSVP` | **hidden** — no card (still on the home tiles, What's New and the digest while open) |
| `bulletin/Volunteer sign-up` | a headline-only post whose button opens the form; **not** checked for "closed" |
| `flyers/2027-03-14 Booth volunteers sign-up` | a Form card in Flyers **and** an event whose **View flyer** opens the form — the event stays even after the form closes |
| `booth/Volunteer sign-up` | Problem: "not a type the booth can show" (forms in the booth folder are not checked either) |
| `Sign-up (Responses)` — the form's answers sheet | **never published** (a spreadsheet, and "(Responses)" in its name) |

Ask only what you need on a form: the answers are personal information, and the answers sheet should stay out of
the public folder (or at least keep "(Responses)" in its name). A shortcut to a form needs care —
[4.14](#414-shortcuts).

### 4.9 Spreadsheets: never published

Google Sheets, Excel (`.xlsx`, `.xls`, `.xlsm`), `.csv`, `.tsv`, OpenDocument sheets (`.ods`) and Apple Numbers
(`.numbers`) are **never** published, in any folder, the booth included. Two built-in rules catch them — by type
(`_ALWAYS_EXCLUDE_MIME` in drive.py: "spreadsheet", "ms-excel", "text/csv", "tab-separated-values") and by ending
(`_ALWAYS_EXCLUDE_NAME`) — plus the setting `drive.exclude_mime_contains: ["spreadsheet"]` in
[config/site.yml](../config/site.yml). The reason: answer sheets of sign-up forms hold names, phone numbers and
e-mail addresses.

| File | Result |
|---|---|
| `forms/Sign-up (Responses)` (Google Sheet) | left out — type `application/vnd.google-apps.spreadsheet` |
| `reports/2027 Budget.xlsx`, `….ods` | left out — by type |
| `booth/booth.csv` | left out — type `text/csv` (the booth's quizzes and facts live in the repository, in `content/booth/booth.csv` — [Booth display](booth.md)) |
| `reports/questions.csv` when Drive gives no type | left out — "file type never published" (the ending) |
| `reports/Budget.numbers` | left out — the ending |

Only the **reason** is written to the public data (`stats.excluded_by_reason` in `data/raw/drive.json`), never the
file's name. The file itself can still be opened by anyone browsing the Drive folder — keep such files out of
A65_GV. To share figures, save a PDF of the sheet.

### 4.10 Pictures, and iPhone (HEIC) photos

Types: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.heic`, `.heif`, `.tif`, `.tiff`, `.bmp`, `.svg` — and anything else
Drive calls `image/…` (`.jfif`, `.avif`; their ending stays in the caption). `kind`: `photo`.

**Where a picture goes depends only on the folder:**

- `photos` (and its sub-folders), **any folder with a name of your own**, or loose in the panel folder → an **album
  photo** on `/photos/`. The file name is the caption; a camera or phone name becomes "&lt;album&gt; #n".
- `flyers`, `reports`, `notes`, `slides`, `workshops`, `forms` → an **Image** card on the Portfolio, in that tab
  (code: `isPhotoItem()` and `isDocItem()` in [committee.js](../eleventy/filters/committee.js)). In `flyers` a dated
  name also makes an event, and the home tile says "Flyer".
- `bulletin` → a headline-only post; the picture itself is not shown on `/bulletin/` (only the RSS feed carries it).
- `booth` → a **Photo** (`.jpg` `.jpeg` `.heic` `.heif` `.tif` `.tiff`: fills the screen with a slow zoom) or a
  **Poster** (`.png` `.gif` `.webp` `.bmp` `.svg`: the whole picture, never cropped); `(photo)` / `(poster)` in the
  name switches it.

Pictures are never in the Library. An album is one entry in the site search; a picture outside an album has no
search entry of its own. The date: a date in the name → (only with the `GOOGLE_API_KEY` secret) when the camera
took it → the upload day. A flyer is dated its upload day — the date in a flyer's name is the event's.

| File | What you get |
|---|---|
| `photos/2027 Spring Assembly/Literature display.jpg` | album "2027 Spring Assembly", caption "Literature display", dated its upload day |
| `photos/2027 Spring Assembly/2027-03-14 Literature table.jpg` | caption "Literature table", March 14, 2027 |
| `photos/2027 Spring Assembly/IMG_0142.HEIC` | caption "2027 Spring Assembly #3" — 3 is its place, A→Z by file name, among that folder's photos and videos |
| `…/IMG_E1234.HEIC` (an edit made on the iPhone), `…/IMG_1234 2.HEIC` (a copy made on a Mac) | numbered the same way |
| `…/Screenshot 2026-10-03 at 9.12.44 AM.png` | numbered; dated October 3, 2026 (from the name) |
| `…/IMG-20270314-WA0003.jpg` (WhatsApp on Android), `…/WhatsApp Image 2027-03-14 at 6.33.16 PM.jpeg` | numbered; dated March 14, 2027 |
| `…/PXL_20270314_150102123.MP.jpg` (a Pixel motion photo) | **not** recognized as a camera name: caption "PXL 150102123.MP" — rename it ([Photos … §7.5](photos-slides-reports.md#75-number-more-camera-names-eg-pixel-motion-photos)) |
| `photos/2027/Spring Assembly/IMG_0001.jpg` | album "2027 / Spring Assembly" (every sub-folder level joins the album name), caption "2027 / Spring Assembly #1" |
| `photos/IMG_0142.jpg` (no album folder) | the panel's own album "Panel 77 (2027–2028) — photos", caption "Photos #1" |
| `Archive/Old flyer.png` | an album "Archive" on `/photos/` (an unknown folder's pictures make one album named after it) |
| `flyers/Grapevine Writing Workshop - Primary Purpose Group, Arlington.png` (real) | an Image card in Flyers; no event (no date in the name) — a `content/events` file links it to its event |
| `flyers/IMG_20270314_101010.heic` | an Image card "Flyers #1" and **no event**: a phone's own name says when the picture was taken |
| `flyers/2027-03-14 IMG_1234.heic` | an event on March 14, 2027 titled "IMG 1234" (a date written first counts) — give it a real title |
| `flyers/Spring Assembly 2027-03-14.heic` | an event "Spring Assembly" on March 14, 2027 (the date may be anywhere in the name) |
| `slides/Slide 1.png` | an Image card in the Slides tab |
| `bulletin/Spring flyer.jpg` | a headline-only post "Spring flyer" |
| `booth/GVLV Grapevine leaves (photo).jpg` | booth Photo, both magazines, every language |
| `booth/IMG_2045.HEIC` | booth Photo with no caption |

**iPhone notes (HEIC):**

- iPhones save photos as **HEIC** by default. That is fine for the website: cards, albums, the slideshow and the
  booth all show a copy that Google makes from it. Right after an upload Drive may need a moment to make that copy —
  until then the card shows a grey tile or its icon.
- **Download gives the original `.heic` file**, which some Windows computers cannot open. For files people will
  download and print — flyers above all — upload a JPG or a PDF. To make the iPhone save JPG photos (and H.264
  videos) from now on: **Settings → Camera → Formats → Most Compatible**.
- Camera names (`IMG_0142.HEIC`) become numbered captions, and adding a file whose name sorts earlier renumbers the
  later ones. Rename pictures to say what they show — never who.
- **Location.** A phone can store where a picture was taken inside the file, and anyone with the folder link can
  download the original. On an iPhone, tap **Options** at the top of the Share sheet and switch **Location** off
  before you share or upload.
- **Live Photos** copied from a computer can come as a picture plus a short `.MOV` clip with the same name; the
  clip would show as a separate video in the album — delete the `.MOV` in Drive.

**Other picture notes:** an animated GIF may show as a still picture on cards. TIFF and BMP are shown through
Google's copy, like HEIC. There is no need to shrink phone photos: the site loads Google's 600-pixel copies for
cards and tiles and 1600-pixel ones for the slideshow (`urls_for()` in drive.py); the booth uses 1920-pixel copies.

### 4.11 Videos, and how big is too big

Types: `.mp4`, `.m4v`, `.mov`, `.webm`, `.avi`, `.wmv`, `.mkv`, `.3gp` — and anything else Drive calls `video/…`
(`.mpg` keeps its ending in the title). `kind`: `video_file`.

- `photos`, a folder of your own, or loose in the panel folder → an **album video**: a play mark on its tile,
  counted apart from the photos ("12 photos", "2 videos"); a tap plays it with **Drive's own player** inside the
  slideshow window. Videos are never grouped in What's New — each one is its own entry.
- `flyers`, `reports`, `notes`, `slides`, `workshops`, `forms` → a **Video** card; Preview plays it in Drive's player.
  In `flyers` a dated name also makes an event.
- `bulletin` → a headline-only post.
- `booth` → a **Video** for `.mp4` (best: H.264 video and AAC sound), `.m4v`, `.webm` and `.mov` (a `.mov` plays
  everywhere only when it is H.264 — an iPhone's "High Efficiency" video is not). `.avi`, `.wmv`, `.mkv`, `.3gp`
  (also `.flv`, `.mpg`, `.mpeg`, `.mts`) are a **Problem**: "a video type browsers do not play — save it as .mp4
  (H.264 video, AAC sound)".

Drive's player on `/photos/` and the Portfolio converts almost any video by itself; the booth plays the file
itself in the browser, which is why it is pickier.

Videos are never in the Library and have no search entries of their own. Their date: a date in the name, else the
upload day (only pictures have a camera time).

| File | What you get |
|---|---|
| `photos/2027 Spring Assembly/Room setup.mov` | album video "Room setup" |
| `photos/2027 Spring Assembly/VID_20270314_101010.mov` | album video "2027 Spring Assembly #5", dated March 14, 2027 (from the name) |
| `photos/2027 Spring Assembly/20270314_101010.mp4` (a Samsung name) | numbered too, March 14, 2027 |
| `photos/2027 Spring Assembly/video.mov` | numbered too — "video" counts as a camera word |
| `workshops/Writing workshop - highlights.mp4` | a Video card in the Workshops tab |
| `flyers/2027-03-14 Spring Assembly promo video.mp4` | a Video card in Flyers **and** an event "Spring Assembly promo video" on March 14, 2027 (its picture: a frame of the video) |
| `booth/LV ES Testimonio - Mi primer número (0:05-1:45).mp4` | booth video, La Viña, Spanish, plays 0:05 to 1:45 |
| `booth/Testimony.avi` | booth Problem: "a video type browsers do not play — save it as .mp4 (H.264 video, AAC sound)" |

**How big is too big?** The site sets no size limit for videos on `/photos/` or the Portfolio — Drive plays them.
What size changes:

- **Processing.** Drive must process a new video before its player and its picture work. A short clip is ready in
  minutes; a long or 4K video can take much longer. Until then the tile has no picture and Drive's player says the
  video is still being processed. The site lists the video at the first update anyway.
- **Visitors on phones** wait longer, and use more of their data, for big files.
- **Downloads.** For a large file Google shows a "can't scan this file for viruses" page before the download
  starts; visitors must confirm it.
- **The booth display** plays its videos and sound files from the copies each update saves for offline play: at
  most **95 MB** for one file (`booth.max_file_mb` in [config/site.yml](../config/site.yml)) and about **400 MB**
  for the whole folder (`booth.max_total_mb`). A video or sound file that could not be saved — too big, over the
  folder's limit, or a download that failed — is **left out of the show** (a picture is still shown from Google's
  copy while the screen is online), and the update run's page shows a yellow warning "Booth display: a file was not
  saved for offline" naming it; the run summary lists it too, under "Booth display (copies for offline)", and the
  player's **Settings → Slides** tab (on the Spanish page **Ajustes → Diapositivas**) says "not downloaded in this
  build, so it is left out (videos and sound files play only from the copy saved with the site)", with the reason.
  Details: [Booth display](booth.md).

> **Note:** the comment above `max_file_mb` in [config/site.yml](../config/site.yml) says a bigger video or sound
> file "is not saved for offline use: it is skipped and listed in the run summary". It is listed, but "skipped"
> means more than "not saved": in the booth code (`src/_data/booth.js`, `scripts/build/booth-media.mjs`) a video
> or sound file without a saved copy is left out of the show altogether — it is not played online either.

Good sizes: short clips (a few minutes at most), MP4 with H.264 video and AAC sound, 1080p or 720p. For the booth,
stay under 95 MB per file — with phone video that means clips of well under a minute at 1080p, a little longer at
720p. The iPhone's **Settings → Camera → Record Video** screen shows how many MB a minute takes in each setting;
**Formats → Most Compatible** gives H.264 files that every browser plays. A 4K setting makes files several times
bigger — the website does not need it.

### 4.12 Sound files (`.mp3`, `.m4a`, `.wav`, `.ogg`)

The site has no separate "audio" kind: a sound file is a `document`. (`.aac`, `.flac`, `.wma` are documents too,
with their ending left in the title.)

| Folder | What a sound file becomes |
|---|---|
| `reports`, `notes`, `slides`, `workshops`, `forms`, `flyers`, a folder of your own | a **Document** card with the document icon (usually no picture); **Preview** plays it in Drive's player; **Download** gives the file. Also in the Library (type by folder), the search, the home tiles ("Document"), What's New and the digest. In `flyers` a dated name also makes an event |
| `photos` | **hidden** — no card, no album (`photos` holds pictures and videos) |
| `bulletin` | a headline-only post |
| `booth` | a **Sound** slide for `.mp3`, `.m4a`, `.aac`, `.wav`, `.ogg` (also `.oga`, `.opus`), played only while the booth's sound is on. `.wma`, `.flac`, `.aif`, `.aiff`, `.amr`, `.mid`, `.midi` are a **Problem**: "a sound type browsers do not play — save it as .mp3 or .m4a" |

| File | What you get |
|---|---|
| `workshops/Writing workshop - recording.mp3` | Workshops tab: Document card "Writing workshop - recording"; Library type "Workshops" |
| `Archive/talk.mp3` | tab "Archive": Document card "talk" |
| `booth/GV EN Podcast teaser (0:30-).mp3` | booth Sound, Grapevine, English, from 0:30 to the end |
| `booth/Song.wma` | booth Problem: "a sound type browsers do not play — save it as .mp3 or .m4a" |

A recording is as public as a photo: no full names, and only with the speaker's permission. Grapevine's and La
Viña's own podcasts and recordings are not ours to upload — the site already lists the official episodes
([Automatic sources](automatic-sources.md)).

### 4.13 `.zip` and `.epub`

Both are `document` cards with the document icon (usually no picture). Drive's viewer can list what is inside a
`.zip` but may only offer a download; nobody can open a `.zip` comfortably on a phone. **Upload the files
themselves instead** — each PDF or picture then gets its own preview, title and search entry. An `.epub` (an e-book
file) suits e-readers; add a PDF of the same text for everyone else.

| File | What you get |
|---|---|
| `workshops/Writing workshop kit.zip` | Workshops tab: Document card "Writing workshop kit"; Library "Workshops" |
| `workshops/Writing workshop guide.epub` | Workshops tab: Document card "Writing workshop guide" |
| `bulletin/…zip` | a headline-only post |
| `photos/…/…zip` | hidden |
| `booth/Booth kit.zip` | booth Problem: "not a type the booth can show" |

### 4.14 Shortcuts

A Drive shortcut (in Drive: right-click a file → **Organize** → **Add shortcut**) placed in the panel folder
publishes the file it points to, filed under the **shortcut's** folder. The original must be shared publicly too;
otherwise the card has no picture and **Open** asks for access. The same file reached twice — the original and a
shortcut to it — is one item; the original wins. A shortcut to a **folder** is read like a folder.

**Without the `GOOGLE_API_KEY` secret** (today) the public folder view only says "shortcut". The site asks Drive
once where it points (and remembers the answer), but the file **type** comes from the shortcut's **name**
(`_resolve_shortcut()` in [drive_listing.py](../scripts/sync/drive_listing.py)):

| Shortcut | What you get |
|---|---|
| `flyers/Flyer.pdf` → a PDF elsewhere | works like the PDF: a Flyers card (with a date in its name, an event too) |
| `slides/Deck.pptx` → a PowerPoint file | a Slides card |
| `forms/Volunteer sign-up` → a Google Form (no ending in the name) | a plain **Document** card (`file_type` "Shortcut"): **no Sign up button, no Download button and no open/closed check** |
| `bulletin/Welcome` → a Google Doc | a headline-only post — the Doc's text is not read |
| `booth/Welcome.png` → a picture | a booth Poster |
| `booth/Welcome` → anything, no ending | booth Problem: "not a type the booth can show" |
| a shortcut Drive did not answer for | a card without a picture; the site tries again at the next run |

**With the API key** the site learns the real type of the target, and a shortcut works exactly like the file.
Simplest rule: put Google Forms, Google Docs and Google Slides in the folder itself, and use shortcuts for PDFs and
pictures (keeping the ending in the shortcut's name).

### 4.15 Folders

A folder is never an item itself; it decides where its files go:

- **Only the first folder below the panel folder decides the category** — its name, in English or Spanish, as a
  whole word; the word that comes first wins (`Fotos del taller` is photos, `Taller de fotos` is workshops). The
  full list of folder words is in [The Drive panel folder](drive-panel-folder.md#35-the-category-folders).
- **Sub-folders** are read down to 6 levels below the panel folder (deeper ones are skipped and named in
  `stats.depth_limited`). In `photos` each sub-folder is its own album ("2027 / Spring Assembly" for
  `photos/2027/Spring Assembly/`); in `booth` each sub-folder is a collection; in a folder of your own everything
  stays in one tab and one album; elsewhere sub-folders change nothing.
- A folder whose name contains `PRIVATE`, `PRIVADO`, `(Responses)`, `(Respuestas)` or `wrong size` is skipped
  **with everything in it**.
- A folder whose sharing was changed cannot be read: its files stay on the site as they were (nothing is deleted
  by accident) and the run summary notes "1 folder(s) could not be read — check their sharing settings".
- A folder with 500 or more entries gets the note "… has N entries — add a GOOGLE_API_KEY secret (or split the
  folder) so none are missed": the public folder view may not list them all.
- Folders sitting loose in A65_GV (outside a panel folder) are ignored; their names are listed in
  `stats.loose_skipped` of the public `data/raw/drive.json`.
- Empty folders are fine.

### 4.16 Any other type

| Drive says | `kind` | Examples | Title |
|---|---|---|---|
| `image/…` | `photo` (behaves like the pictures above) | `.jfif`, `.avif` | the ending stays ("Literature table.jfif") |
| `video/…` | `video_file` | `.mpg`, `.flv` | the ending stays ("Room.mpg") |
| anything else | `document` | `.pages`, `.html`, `.json`, `.aac`, `.flac` | the ending stays, except `.pages` (it is on the list in [4.1](#41-how-the-site-tells-the-type-of-a-file)) |

In `bulletin`, a type Drive calls `text/…` is read as text — an `.html` file then shows its raw tags as words (the
site never runs HTML from a post); don't post one. In `booth` the booth's own list decides
([4.18](#418-the-booth-folder)): `.jfif` is a Photo; `.aac`, `.oga`, `.opus` are Sound; `.flv`, `.mpg`, `.mpeg`,
`.mts` and `.wma`, `.flac`, `.aif`, `.aiff`, `.amr`, `.mid`, `.midi` are Problems that say which type to save
instead (so is any other type Drive calls `video/…` or `audio/…`); `.pages`, `.html`, `.htm`, `.avif` and every
other type are Problems: "not a type the booth can show".

### 4.17 Never published: the complete list

| Rule (code) | What it catches | Examples |
|---|---|---|
| By type — `_ALWAYS_EXCLUDE_MIME` in [drive.py](../scripts/sync/drive.py), plus `drive.exclude_mime_contains` in [config/site.yml](../config/site.yml) | spreadsheets, Excel, CSV, TSV, Apps Script projects, Google Sites, Fusion Tables | Google Sheets, `Budget.xlsx`, `booth.csv`, `quiz.tsv`, `Budget.ods` |
| By ending (files only) — `_ALWAYS_EXCLUDE_NAME` | `.xls .xlsx .xlsm .csv .tsv .ods .numbers .tmp .lnk .ini .db .ds_store`; names starting `~$` (Office's lock files) or `.`; `Thumbs.db`, `desktop.ini` | `~$report.docx`, `.DS_Store`, `notes.tmp`, `Old link.lnk` |
| By words in the name — `drive.exclude_name_contains` | `(Responses)`, `(Respuestas)`, `PRIVATE`, `PRIVADO`, `wrong size` — anywhere in the name, capitals ignored, files **and** folders | `Sign-up (Responses)`, `PRIVATE budget.pdf`, `Privado - lista.pdf`, `flyer wrong size.png` |

Watch out: the word test is "contains". `privately funded.pdf` is hidden too (it contains "private");
`Notas privadas.pdf` is published ("privadas" does not contain "privado"); a folder named `Responses` (without the
parentheses) is published.

In the booth folder a name starting with `_` or `~`, or holding `(off)`, `(draft)`, `(apagado)` or `(borrador)`, is
read but never shown (`_README - how to name booth files.txt` is a note for the committee). Elsewhere these marks
mean nothing: a bulletin post named `Notice (draft).md` or `_notice.md` goes live.

What is recorded: for a file left out by these rules, only the **reason** goes into the public data
(`stats.excluded_by_reason`), never its name. But the file itself is still in the Drive folder, which anyone with the
link can open.

### 4.18 The booth folder

New in October 2026: the **booth display**, a show that plays by itself on a screen at the committee's table at
assemblies and conventions (About page: `/about/#booth`, `/es/about/#booth`). Its pictures, videos, sound files and
short texts come from the `booth` folder of the panel folder. This section is the file-type summary; the player,
the CSV with quizzes and facts (`content/booth/booth.csv`, in the repository — never on Drive) and the `booth:`
settings are in [Booth display](booth.md).

**The folder.** Any of these words in the first folder's name (capitals and accents ignored, whole words):
`booth`, `booths`, `mesa`, `mesas`, `kiosk`, `kiosko`, `kiosco`, `display`, `displays`, `pantalla`, `pantallas`,
`stand`, `stands`, `exhibit`, `exhibits`, `exhibición`, `exhibiciones`. When a name holds words of two categories,
the first one wins: `Booth photos` and `Mesa de fotos` are the booth folder; `Fotos de la mesa` is a photo folder,
and `photos/Booth at CityWide` an album. Each sub-folder is a **collection** the player can switch off
(`booth/Spring Assembly 2027/`); deeper folders belong to their top collection; files directly in `booth` form the
collection "Booth folder".

> **Note:** before the booth display these words meant something else: `Booth photos` was a photo folder, and a
> folder named `Display`, `Stand`, `Mesa` or `Exhibit` was a folder of your own (a Portfolio tab and an album).
> Such a folder now feeds the booth, and its files leave the Portfolio and `/photos/` — rename it if it holds
> something else.

**The name says how a file is shown** (code: `parse_booth_name()` in
[booth_names.py](../scripts/sync/booth_names.py), whose header lists every option):

```text
[order] [magazine] [language] Title [(option) (option) …].ext        only the title is needed
```

| Part | How to write it | What it does |
|---|---|---|
| order | `01 `, `02-`, `3_` at the very start (1–3 digits) | its place in the player's "In order" mode; never shown. A year (`2027 Spring…`), a date or a counting number (`12 Steps poster`) is not an order — `01 12 Steps poster` is |
| magazine | `GV`, `LV`, `GVLV` (also `GV-LV`, `GV+LV`, `GV&LV`, `GV/LV`, `GV LV`) at the start; `AA` (both) at the start only right before a language code (`AA EN Welcome.png` — `AA Preamble.png` keeps "AA" in its caption); or `(LV)`, `[GV]`, `(AA)`, `(La Viña)` anywhere | the slide's colour (Grapevine blue, La Viña amber, both grape) and the Grapevine / La Viña switch; none = both |
| language | `EN`, `ES`, `BI` (or `EN-ES`) in **capitals** at the start, or `(es)`, `[English]`, `(en español)` anywhere | which language settings show it; none = every setting (pictures without words, music). `Esto ES La Viña.jpg` keeps "ES" in its title |
| title | the rest of the name | the caption (a message's heading); a camera name (`IMG_2045`) gives no caption |
| options | in `( )` or `[ ]`, one option per pair, any order, English or Spanish | `(poster)` / `(photo)` · `(15s)`, `(2 min)` (3–120 seconds on screen) · `(0:15-1:30)`, `(0:30-)` (the part of a video or sound file to play) · `(muted)` · `(x2)`…`(x5)`, `(rare)` (little difference while the show has only a few pictures and videos: each already comes back as often as the show's rules let it) · `(first)` · `(from 2027-03-01)`, `(until 2027-03-15)` (a year from 2000 to 2099) · `(no caption)` · `(off)`, `(draft)`. Several in one pair are read too, but a date takes everything after it (`(until 2027-03-15, first)` is never shown first). Anything else in brackets stays in the title: `(from the Chair)` |

**The booth display does not read a date written in a file's name** — it stays in the caption:
`2027-03-14 Spring Assembly.jpg` is shown with the caption "2027-03-14 Spring Assembly" (the date only becomes the
file's `date` in `data/raw/drive.json`, which the booth never uses). Time a slide with `(from …)` / `(until …)`
instead, and hide a caption with `(no caption)`.

**What each type becomes in the booth** (code: `media_type()` in booth_names.py — Drive's type first, else the
ending):

| Booth kind | Files |
|---|---|
| Photo — fills the screen, slow zoom | `.jpg` `.jpeg` `.jfif` `.heic` `.heif` `.tif` `.tiff` |
| Poster — the whole picture | `.png` `.gif` `.webp` `.svg` `.bmp`; Drive's picture of the first page of a PDF, PowerPoint (`.ppt` `.pptx` `.pps` `.ppsx`), Keynote, `.odp`, Google Slides, Google Drawing |
| Video | `.mp4` (best), `.m4v`, `.webm`, `.mov` |
| Sound — only while the sound is on | `.mp3` `.m4a` `.aac` `.wav` `.ogg` `.oga` `.opus` |
| Message — the name is the heading, the text the message | `.txt`, `.md` (also `.markdown`), Google Docs, `.docx` |
| Problem — never shown, listed with the reason | everything else: `.doc`, `.odt`, `.rtf`, `.pages`, `.zip`, `.epub`, `.html`, a Google Form, a shortcut with no ending, the video and sound types browsers do not play |

Examples (checked with the real function):

| File in `booth/` | Result |
|---|---|
| `GV EN Welcome to our table (first) (15s).png` | Poster · Grapevine · English · shown first · 15 seconds |
| `LV ES Testimonio - Mi primer número (0:05-1:45).mp4` | Video · La Viña · Spanish · plays 0:05 to 1:45 |
| `02 GVLV Our booth at CityWide Dallas.jpg` | Photo · both magazines · every language · order 2 |
| `GVLV BI Welcome - Bienvenidos (x2) (12s).png` | Poster · both · English and Spanish · twice as often · 12 seconds |
| `[LV][ES] Cita (10s) (muted).mp4` | Video · La Viña · Spanish · never its sound ("10s" is ignored for a video) |
| `GV EN Ask us about Grapevine.txt` | Message "Ask us about Grapevine", the file's text below it |
| `LV ES Taller de escritura en Tyler (hasta 2026-10-26).jpg` | Photo until October 26, 2026; after that day it is left out |
| `Spring Assembly 2027/GV EN Book display.jpg` | Photo in the collection "Spring Assembly 2027" |
| `IMG_2045.HEIC` | Photo with no caption |
| `AA Preamble.png` · `AA EN Preamble.png` | Poster captioned "AA Preamble" · Poster, both magazines, English, captioned "Preamble" |
| `Draft poster (off).png`, `_draft poster.png` | never shown |
| `GV EN Donate to Grapevine.png` | left out of the show — its caption says a word the booth never shows |
| `GV EN Welcome (from 2027-03-01) (until 2027-02-01).png` | Problem: "its days never meet — the (from …) day is after the (until …) day" |

**Where booth files go.** Only to the booth display: `drive.py` reads each name into `extra.booth` in
`data/raw/drive.json`, and `build_booth()` in [build_data.py](../scripts/sync/build_data.py) writes
`data/site/booth.json`. They are **never** on the Portfolio, `/photos/`, the bulletin, the events, What's New, the
search or the digest — `Ctx.items("drive")` leaves them out of everything else. Only `/status/` counts them, with the
other Drive files. Nothing in the booth is translated: a title is the caption you wrote.

**Problems** are listed four ways: in `data/site/booth.json` → `problems` (in English and Spanish); in the run
summary under **Booth folder files the booth display can't show**, one line per file with its reason ("booth/Song.wma
— a sound type browsers do not play — save it as .mp3 or .m4a"; the first 10 also as yellow warnings "Booth folder
file to fix"); in the player's **Settings → Slides** tab (on the Spanish page **Ajustes → Diapositivas**), under
"Files and rows the show couldn't use"; and as one note of the Drive source, for example "booth folder: 2 file(s)
the booth display cannot show — Song.wma, Testimony.avi (data/site/booth.json → problems says why)" (at most four
names, then "…"; the run summary's "Notes" show only the first two notes of each source, and `stats.warnings` in
`data/raw/drive.json` always has it). A message whose text is empty or could not be read yet is a problem too ("no
text to show — the file is empty, or its text could not be read yet"). A file switched off is not a problem, and a
file past its `(until …)` day is simply left out.

**Words the booth never shows** — "PDF", donate / donation, "buy now", "hurry", "limited time" and the others listed
in [Booth display](booth.md) — are checked in the captions and notes too, when the website is built: a file whose
caption, or a note whose heading or text, says one is **left out of the show** and named in Settings → Slides and
in the build's log (the `[booth]` lines of *Build the website*), not in the run summary's booth list: "Drive:
booth/GV EN Donate to Grapevine.png: left out of the booth: it says “Donate”". Rename it or change the note;
`(no caption)` shows a picture without its title (a hidden caption is not checked).

**Text files** (messages) are downloaded like bulletin posts — at most 40 downloads per run, shared with the
bulletin (whose posts go first); an unchanged file keeps its text. A message whose name gives no language is shown
in the language(s) of its paragraphs (`text_langs()` in drive.py).

**The booth folder's own rules** (they are good rules for every folder): no faces and no full names of AA members —
photos of tables, displays and rooms only; no Grapevine or La Viña logos, covers, artwork, cartoons, or their audio
and video files (official videos are added as YouTube links in `content/booth/booth.csv`); only material the
committee made or may use; and everything in the folder is public.

---

## 5. The "kind" of a file in the data, and how pages use it

Each update writes every Drive file into `data/raw/drive.json` as one item (the file is public, in the GitHub
repository). Then [build_data.py](../scripts/sync/build_data.py) spreads the items over the site's data files —
`data/site/drive.json` (Portfolio, Photos, Library, home tiles), `announcements.json` (bulletin posts),
`events.json` (dated flyers), `whatsnew.json` (What's New and the RSS feed), `booth.json` (the booth display) and
`status.json` — and the pages read only those.

The fields that decide where an item goes:

| Field | Values | Set by (drive.py unless noted) |
|---|---|---|
| `kind` | `photo`, `video_file`, `document`, `slides`, `form`, `announcement` | `kind_for()` from the type; `announcement` for every file in the bulletin folder |
| `category` | `reports`, `notes`, `slides`, `flyers`, `photos`, `workshops`, `announcements` (the bulletin), `forms`, `booth`, `other` | `category_for()` from the first folder's name; for a file straight in the panel folder, its kind ([3.3](#33-files-dropped-straight-into-the-panel-folder)) |
| `extra.file_type` | "PDF", "JPEG", "Google Doc" … | `file_type_label()` |
| `extra.is_image`, `is_video`, `is_pdf` | true or false | the MIME type (and a `.pdf` ending) |
| `extra.album` | the sub-folders below `photos`, joined with " / " | `build_item()` |
| `extra.event_date`, `event_title`, `event_time`, `event_end_time`, `event_location`, `event_tz` — or `event_month` | flyers only | `build_item()` |
| `extra.body_md`, `pinned`, `expires`, `publish` | bulletin posts (`body_md` also for a booth message) | `build_item()`, `fill_announcements()`, `fill_booth_texts()` |
| `extra.booth` | how the booth shows the file | `parse_booth_name()` in booth_names.py; `fill_booth_texts()` adds a message's text |

What each kind becomes:

| `kind` | Which files | Data file | How the pages use it |
|---|---|---|---|
| `photo` | every picture (`image/…`) outside the bulletin | `drive.json` | In `photos`, a folder of your own or loose in the panel folder: an **album photo** on `/photos/` — slideshow; What's New groups 2 or more photos of one album and one day into "N new photos in &lt;album&gt;" linking to the album; the digest has one row per album and month; the search one entry per album. In a built-in folder: a Portfolio **Image** card. Never in the Library. Home tile label "Photo" ("Flyer" for a file of `flyers`) |
| `video_file` | every video (`video/…`) outside the bulletin | `drive.json` | An **album video** (play mark, Drive's player) or a Portfolio **Video** card, by the same folder rule. Never grouped in What's New, never in the Library. Home tile "Video" |
| `document` | PDF, Word, Google Docs and Drawings, text, sound, `.zip`, `.epub`, anything unknown | `drive.json` | A Portfolio **Document** card in its folder's tab (none for a file in `photos`); Library (type = folder) and search; home tile "Document"; one What's New entry each; a digest row |
| `slides` | PowerPoint, Keynote, OpenDocument slides, Google Slides | `drive.json` | A Portfolio **Slides** card with the first slide shown whole; **Present on the web** when its title is a web deck's `drive_title`; Library and search; home tile "Slides" |
| `form` | Google Forms | `drive.json`, while open | A Portfolio **Form** card with **Sign up** (from `forms`, an unknown folder or the panel folder: the Sign-ups tab); checked every run — a closed form leaves every page; Library and search while open; home tile "Sign-up form" |
| `announcement` | every file in the bulletin folder | `announcements.json` (never `drive.json`) | A post on `/bulletin/` (text from a Google Doc, `.txt`, `.md` or `.docx`); home "From the committee" (2 posts, pinned first); What's New and RSS (the link opens the Drive file); search (→ `/bulletin/#…`); the digest's bulletin list; the monthly toolkit's count |

Two more things to know:

- A **dated flyer** keeps its own kind (a PDF stays `document`) **and** becomes an `event` item in `events.json`
  (id `ev:flyer:<file id>`, title = `event_title`) — that event is what `/events/`, the calendar files, the home
  page's "Upcoming events" and the search show (`flyer_events()` in build_data.py).
- A **booth file** keeps its kind too (a `.jpg` is still `photo`), but its category `booth` keeps it out of every
  list except `booth.json` (`Ctx.items()` and `build_booth()` in build_data.py). The booth reads `extra.booth.kind`
  instead: `photo`, `poster`, `video`, `audio`, `message` — or `unsupported` (a problem).

In `data/site/*.json` each item also gets `i18n` (its title, and a post's text, in English and Spanish),
`machine` (which language is a machine translation) and `is_new` (the "New" badge, 14 days) — except in
`booth.json`, where nothing is translated.

Three items as `data/raw/drive.json` holds them (shortened; `<file id>` is Drive's id of the file):

```json
{
  "id": "drive:<file id>", "kind": "document", "category": "reports",
  "title": "Grapevine Area Chair Meeting Report", "date": "2026-08-11",
  "image": "https://lh3.googleusercontent.com/d/<file id>=w600", "tags": ["panel-77", "pdf"],
  "extra": {
    "name": "2026-08-11 Grapevine Area Chair Meeting Report.pdf", "mime": "application/pdf",
    "file_type": "PDF", "is_pdf": true, "path": ["reports"], "album": null,
    "view_url": "https://drive.google.com/file/d/<file id>/view",
    "preview_url": "https://drive.google.com/file/d/<file id>/preview",
    "download_url": "https://drive.google.com/uc?export=download&id=<file id>",
    "thumb_url": "https://lh3.googleusercontent.com/d/<file id>=w600", "image_url": null
  }
}
```

```json
{
  "id": "drive:<file id>", "kind": "document", "category": "flyers",
  "title": "Spring Assembly booth 9am @ Tyler Civic Center", "date": "<the upload day>",
  "extra": {
    "name": "2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf", "file_type": "PDF",
    "event_date": "2027-03-14", "event_title": "Spring Assembly booth", "event_time": "09:00",
    "event_location": "Tyler Civic Center"
  }
}
```

```json
{
  "id": "drive:<file id>", "kind": "photo", "category": "booth", "title": "Welcome to our table",
  "extra": {
    "name": "GV EN Welcome to our table (first) (15s).png", "mime": "image/png", "path": ["booth"],
    "booth": {
      "kind": "poster", "pub": "gv", "langs": ["en"], "title": "Welcome to our table", "caption": true,
      "order": null, "seconds": 15, "start": null, "end": null, "muted": false, "weight": 1,
      "first": true, "from": null, "until": null, "off": false, "fit": "contain",
      "collection": "main", "collection_label": "Booth folder", "text": null, "problem": null
    }
  }
}
```

The full field list is in [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md).

---

## 6. Naming tips per type

The name is all the site reads for most files, so it is worth a few seconds. General rules first:

- **A date first when the file belongs to a day**: `2027-03-14 …`. It sorts the file and fixes its date (without
  it, editing the file re-dates it). Other forms work too (`March 14, 2027`, `14 de marzo de 2027`, US order
  `03-14-2027`) — [The Drive panel folder §3.8](drive-panel-folder.md#38-dates-in-file-names).
- **Then what it is**, in plain words. That text is the title on every page, and it is machine-translated for the
  other language (fix a wording in [Translations](translations.md)).
- **Keep the normal ending** (`.pdf`, `.jpg`, `.md`, `.mp4`, `.mp3`); unusual ones stay in the title.
- **No people's names**, and mind the hiding words: a name that merely contains `private`, `privado` or `wrong
  size` (`privately funded.pdf`) is never published.
- Underscores become spaces, and "Copy of" / " (1)" are dropped, so `Copy of 2027-01-10 Flyer (1).pdf` is just
  "Flyer"; `GV_LV` / `GV-LV` / `GV LV` become "GV/LV" (not when a letter, a digit or an underscore follows "LV":
  `GV_LV_Report` becomes "GV LV Report").

| Type | Name it like this | Why | Avoid |
|---|---|---|---|
| PDF, Word, Google Doc — documents | `2027-02-17 Minutes - February committee meeting.pdf` · `March 2027 Committee Meeting.pdf` | dated February 17 / March 1, 2027 (a month alone stays in the title) | "final", "v3" (they stay in the title); a phone photo of a page (it becomes an Image card — a PDF prints better) |
| Any flyer (PDF, JPG, PNG, Google Drawing …) | `2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` · `2027-05-01 Workshop 7pm ET on Zoom.png` | the day makes an event; a time (`9am`, `9-11am`, `7pm ET`) and a place after `@` fill it in | a phone's own name (`IMG_20270314_…`): no event; two days in one name (`2027-03-19 to 2027-03-21 …` gives a one-day event with an odd title) — write a multi-day event in `content/events`; a dated name for a flyer that a `content/events` file already links (two events) |
| Bulletin post (Google Doc, `.docx`, `.txt`, `.md`) | `2027-01-10 Welcome new GVRs` · `Assembly reminder (until 2027-03-15).md` · `New prices (from 2027-01-01).md` · `Welcome (pinned).txt` | the name is the headline; the markers pin, expire or schedule it (a date with its year) | `.markdown`, `.rtf`, `.odt`, `.doc` for a text post; `(until March 15)` without a year (not read) |
| Slides | `Spring Assembly report.pptx` | the title on the Slides card | renaming the four web decks' PowerPoint files (their names are the decks' `drive_title`) |
| Google Form | the form's own name: `Spring Assembly volunteers` | the card's title | removing "(Responses)" from the answers sheet's name |
| Picture | `Literature display at the Spring Assembly.jpg` · `2027-03-14 Literature table.jpg` · or keep `IMG_0142.HEIC` | caption and date; a camera name gets a numbered caption | faces, names (also on name tags in the picture); `.jfif`, `.avif`, Pixel `….MP.jpg` names |
| Album folder (in `photos`) | `2027 Spring Assembly` | the album's title, translated for the Spanish page | people's names; a folder for every few photos (each sub-folder is an album of its own) |
| Video | `Room setup.mp4` · `2027-03-14 Spring Assembly highlights.mp4` | caption and date | `.mpg` (ending stays); for the booth `.avi`, `.wmv`, `.mkv`, `.3gp` |
| Sound | `Writing workshop - recording.mp3` | the card's title | `.aac`, `.flac`, `.wma` outside the booth (ending stays); `.wma`, `.flac` in the booth (a problem) |
| Shortcut | keep the target's ending: `Flyer.pdf`, `Deck.pptx` | without the API key the ending tells the type | shortcuts to Google Forms, Docs and Slides (no ending) — put those files in the folder itself |
| Booth file | `GV EN Welcome to our table (first) (15s).png` · `LV ES Testimonio (0:05-1:45).mp4` · `02 GVLV Our booth at CityWide Dallas.jpg` | order, magazine (GV, LV, GVLV), language (EN, ES, BI), title and options, one per pair of brackets ([4.18](#418-the-booth-folder)) | a lower-case language code at the start (`gv en Welcome.png` reads GV but shows the caption "en Welcome"); a leading `AA` without a language code after it (`AA Preamble.png` keeps "AA" in the caption); a date in the name (it stays in the caption — use `(from …)` / `(until …)`); a word the booth never shows ("PDF", "donate" …: the file is left out) |
| Folder | `photos/2027 Spring Assembly` · `booth/Spring Assembly 2027` · `Archive` | category, album, collection or tab name | booth words (`Display`, `Stand`, `Mesa`, `Exhibit`) in a folder that is not for the booth; `PRIVATE` in a folder name hides everything inside |

> **Note:** the header of [drive.py](../scripts/sync/drive.py) says "A date anywhere in the name sets the item
> date". For a flyer it sets the **event's** date instead — the flyer's card shows its upload day — and in the
> booth folder it sets only the item's date in `data/raw/drive.json`: the booth display ignores it, and the
> caption keeps it.

---

## 7. What happens next

1. **Nothing happens at upload time** — nothing watches the Drive.
2. **The next run that reads the Drive picks the file up.** Every kind of *Update & Deploy* run reads it: the
   morning refresh (about 4:30 AM Central with the morning alarm), the full daily run (GitHub usually starts it
   between 5 and 7 AM Central), the midday quick run (around 7 to 9 AM Central), the quick run after anyone saves a
   settings or content file, and any run you start yourself (**Run workflow**, tick **skip_crawl**). A quick run
   publishes in about 2 minutes; GitHub Pages may then serve the old page for up to 10 more minutes. Details:
   [Automation and troubleshooting §3](automation-and-troubleshooting.md#3-what-happens-next-how-fast-a-change-goes-live).
3. **In that run**, depending on the type:

| What | When it is ready |
|---|---|
| Every file: title, date, folder, card or album, translations of its title | the same run (a long translation queue can leave some titles for the next run) |
| Bulletin texts and booth messages | downloaded in the same run — at most 40 downloads per run in all, bulletin posts first; a file is downloaded again only when its "last modified" text changes; the rest wait for the next run (`stats.announcements.deferred`, `stats.booth_texts.deferred`) |
| Google Forms | checked open or closed in every run |
| Dated flyers | the event appears in the same run; it stays in What's New for 30 days after the site first saw it, with a "New" badge for 14 |
| Pictures and videos | listed in the same run; their pictures and players work once Drive has made them (minutes for a photo, longer for a long video) |
| Booth files | `data/site/booth.json` in the same run; the publishing step then saves new booth pictures, videos and sound files for offline play — downloads stop after about 15 minutes per run, and whatever is left waits for the next run ([Booth display](booth.md)) |

4. **Later changes:**
   - **Rename** — the title follows at the next run; the "added" day stays (the item keeps its Drive id).
   - **Move** to another folder — its category follows (a flyer moved out of `flyers` loses its event).
   - **Delete**, or move out of the panel folder — gone at the next run, but only when its folder could be read; a
     folder that could not be read keeps its files on the site untouched.
   - **Add `PRIVATE`** to the name — gone at the next run.
   - **Replace the file** with a new version (Drive's **Manage versions** → **Upload new version**) — the item keeps
     its id, its links and its "added" day; Google's picture of it may take a while to change; a bulletin text or
     booth message is read again once the folder shows a new "last modified" date or time.

---

## 8. Where it shows on the website

| Place (English · Spanish) | What comes from Drive there | Types |
|---|---|---|
| Portfolio `/portfolio/` · `/es/portfolio/` | one tab per folder: Reports `#docs-reports`, Meeting notes `#docs-notes`, Slides `#docs-slides`, Workshops `#docs-workshops`, Flyers `#docs-flyers`, Sign-ups `#docs-forms`, then each folder of your own (`#docs-folder-archive`); newest first, "New" for 14 days | documents, slides, open forms; pictures and videos of the built-in folders. Nothing from `photos`, `bulletin` or `booth` |
| Photos `/photos/` · `/es/photos/` | one album per sub-folder of `photos`, one per folder of your own, one for pictures loose in the panel folder or directly in `photos` (anchors `#album-…`) | pictures and videos only |
| Events `/events/` · `/es/events/`, calendar files `/events.ics` · `/es/events.ics` | each dated flyer as an event with **View flyer** and the flyer's picture (anchor `#ev-flyer-…`, made from the file's id) | any type in `flyers` with a day date |
| Bulletin `/bulletin/` · `/es/bulletin/` | one post per file (anchor `#ann-drive-…`, made from the file's id) | everything in `bulletin`; text only from a Google Doc, `.txt`, `.md`, `.docx` |
| Library `/library/` · `/es/library/` | source "NETA 65 committee", type = folder; a dated flyer shows "Event: &lt;date&gt;"; file sizes only with the API key | documents, slides, open forms — not pictures or videos, not `photos`, `bulletin`, `booth` |
| Search `/search/` · `/es/search/` | the Library's documents (they open the Drive file), one entry per album, bulletin posts, events | as the Library, plus albums, posts and events |
| Home `/` · `/es/` | "Shared by the committee": the 6 newest Drive items (a file of `flyers` labelled "Flyer"); "From the committee": 2 bulletin posts, pinned first; "Upcoming events" | any kind except bulletin posts, closed forms and booth files; posts; events |
| What's New `/whats-new/` · `/es/whats-new/`, RSS `/feed.xml` · `/es/feed.xml` | each Drive file at its news date (2 or more album photos of one album and day are one entry; dated flyers come as events for 30 days); bulletin posts. A link opens the Drive file (a photo group opens its album). The 150 newest entries | everything but booth files and closed forms |
| Monthly digest `/digest/` · `/es/digest/` and the e-mail | the month's committee uploads (photos one row per album; dated flyers are in the events; bulletin posts in their own list); the e-mail labels rows Reports, Notes, Slides, Flyers, Photos, Workshops, Forms or Files | everything but booth files and closed forms |
| Monthly toolkit `/monthly/` · `/es/monthly/` | the number of live bulletin posts and the newest one; the "editorial calendar" link | bulletin posts; one document found by name |
| Booth display `/about/#booth` · `/es/about/#booth` | the booth folder's files, as slides | [4.18](#418-the-booth-folder) |
| Status `/status/` · `/es/status/` | the row "Google Drive (committee uploads)": state, number of files (bulletin and booth files included), last good check | — |

**Pages that look up one file by its name.** Any type works; the name decides. Rename the file so the words no
longer match, and the link quietly disappears:

| Page | Link | The name must match (setting) |
|---|---|---|
| `/shop/` · `/es/shop/` | **Read AA Grapevine's notice** for a price change | `price_changes` → `doc_match` in [config/site.yml](../config/site.yml) |
| Portfolio, `/orientation/` · `/es/orientation/` | **Present on the web**, the deck's "PowerPoint copy" | exactly the deck's `drive_title` in `config/presentations/*.yml` ([Presentations](presentations.md)) |
| `/meetings/` · `/es/meetings/` | the La Viña weekly open meeting's **View flyer** | `lavina_weekly_open` → `flyer_match` in config/site.yml |
| `/events/` (monthly events) | each date's flyer | `recurring_events` → `flyer_match` ([Flyers and events §5.2](flyers-and-events.md#52-a-monthly-events-flyer-flyer_match)) |
| `/contribute/` · `/es/contribute/` | printable "Share your story" flyers (at most 2, from `flyers`) | "share your story" / "comparte tu historia" |
| `/monthly/` · `/es/monthly/` | the editorial calendar | "editorial calendar" / "calendario editorial" |

---

## 9. Going further: change the code

The rules live in a few functions. Edit them on GitHub or on a computer ([Pages and code](pages-and-code.md)),
run the tests, and the next push rebuilds the site; the next run that reads the Drive applies a sync change to
every file. Each recipe names the file and the function — search the file for the name.

### 9.1 Take another ending out of titles (`.jfif`, `.avif`, `.markdown`)

**File:** [scripts/sync/drive.py](../scripts/sync/drive.py), the constant `_KNOWN_EXT` (used by `strip_ext()`).
Add the endings to the list:

```python
_KNOWN_EXT = ("pdf|docx?|pptx?|ppsx?|odp|odt|rtf|txt|md|markdown|key|pages|jpe?g|jfif|png|gif|webp|avif|heic|heif|"
              "tiff?|bmp|svg|mp4|m4v|mov|avi|wmv|webm|mkv|3gp|mpe?g|mp3|m4a|aac|wav|ogg|zip|epub")
```

What changes: at the next run `Literature table.jfif` is titled "Literature table" and `Room.mpg` "Room". Nothing
else: the kind still comes from Drive's type.

- When Drive's folder view gives no type for the ending, also teach `guess_mime()` through `_EXTRA_TYPES` in
  [drive_listing.py](../scripts/sync/drive_listing.py), for example `".avif": "image/avif"`.
- The booth has its own list, `_EXT` in [booth_names.py](../scripts/sync/booth_names.py), which also says how the
  booth shows the file (`"jfif": "photo"`): add an ending there only with the booth type it should get.
- Test: `python -m unittest tests.test_sync_pipeline` (and `tests.test_booth_names` for the booth list).

### 9.2 Give sound files their own "Sound" label on Portfolio cards

**Files:** [eleventy/filters/committee.js](../eleventy/filters/committee.js), function `fileType()`; the words in
[src/_i18n/committee.json](../src/_i18n/committee.json).

In `fileType()`, before the line that tests for a PDF:

```js
if (mime.startsWith("audio/")) return { key: "audio", icon: "file-audio", tone: "gv" };
```

and in committee.json, next to `committee.type.pdf`:

```json
"committee.type.audio": { "en": "Sound", "es": "Audio" },
```

What changes: MP3, M4A and WAV cards say "Sound" with a sound icon (`file-audio` is in the Lucide icon set the site
uses). Preview still opens Drive's player. The home tiles keep "Document": they print the kind (`kind.document` in
`src/_i18n/common.json`). Making sound a kind of its own (in `kind_for()`) would also change the Library, What's New
and the digest — a bigger job. Test: `python -m unittest tests.test_i18n_keys` (every word has English and
Spanish), then a local build.

### 9.3 Never publish a type (for example `.zip`)

**No code:** in [config/site.yml](../config/site.yml) → `drive:`, add a piece of the name or of the type:

```yaml
  exclude_name_contains: ["(Responses)", "(Respuestas)", "PRIVATE", "PRIVADO", "wrong size", ".zip"]
```

`exclude_name_contains` is a "contains" test on the name (capitals ignored), files and folders. The other list,
`exclude_mime_contains`, tests the type — careful: adding `"zip"` there would also hide `.epub` files (their type is
`application/epub+zip`).

**In the code** (whatever the settings say): `_ALWAYS_EXCLUDE_NAME` (endings) or `_ALWAYS_EXCLUDE_MIME` (types) in
drive.py, used by `exclusion_reason()`. What changes: at the next run such files leave the site; only the reason is
recorded (`stats.excluded_by_reason`). Test: the `DriveSafety` tests in
[tests/test_sync_pipeline.py](../tests/test_sync_pipeline.py).

### 9.4 Read the text of `.odt` bulletin posts and booth messages

**Files:** drive.py — `body_url()` (which files get their text downloaded) and `fetch_body()` (how the bytes
become text), next to `docx_to_text()`; booth_names.py — `_EXT` and `_TEXT_MIME` (so the booth calls an `.odt` a
message).

1. In drive.py, add a reader next to `docx_to_text()`:

   ```python
   def odt_to_text(data: bytes) -> str:
       """Tiny .odt reader (paragraph and heading text only), like docx_to_text."""
       with zipfile.ZipFile(io.BytesIO(data)) as z:
           xml = z.read("content.xml").decode("utf-8", "replace")
       xml = re.sub(r"<text:(?:s|tab)\b[^>]*/>", " ", xml)
       xml = re.sub(r"<text:line-break\s*/>", "\n", xml)
       paras = []
       for _tag, inner in re.findall(r"(?s)<text:(p|h)\b[^>]*?(?<!/)>(.*?)</text:\1>", xml):
           text = html.unescape(re.sub(r"<[^>]+>", "", inner))
           paras.append(text if text.strip() else "")
       return "\n\n".join(paras)
   ```

2. In `body_url()`, add `".odt"` to the endings that get a download (next to `".docx"`).
3. In `fetch_body()`, before the `.docx` test:

   ```python
   if "opendocument.text" in mime or low.endswith(".odt"):
       return odt_to_text(data)
   ```

4. In booth_names.py, change `"odt": "unsupported"` to `"odt": "text"` in `_EXT`, and add
   `"application/vnd.oasis.opendocument.text"` to `_TEXT_MIME`.

What changes: at the next run an `.odt` post shows its text (it keeps its **Open the document** button, like a
`.docx`), and an `.odt` in the booth becomes a message slide. Test: add a test that builds a tiny `.odt` in memory
to tests/test_sync_pipeline.py and one to tests/test_booth_names.py, then run both.

### 9.5 Change the picture sizes

- Cards, tiles and the slideshow: `urls_for()` in drive.py — `=w600` (cards and tiles) and `=w1600` (the slideshow).
  Google resizes the picture on its side; a bigger number is sharper but heavier for phones.
- The booth: `BOOTH_IMAGE` (`=s1920`) and `BOOTH_THUMB` in build_data.py.

### 9.6 Where each rule lives

| Rule | File | Function or name |
|---|---|---|
| the type, from Drive's listing | [drive_listing.py](../scripts/sync/drive_listing.py) | `HtmlLister._parse_entry()`, `guess_mime()`, `_EXTRA_TYPES`, `ApiLister._entry()`, `HtmlLister._resolve_shortcut()` |
| type → kind | [drive.py](../scripts/sync/drive.py) | `kind_for()` |
| folder → category | drive.py | `category_for()`, `CATEGORY_SYNONYMS` |
| never published | drive.py | `exclusion_reason()`, `_ALWAYS_EXCLUDE_MIME`, `_ALWAYS_EXCLUDE_NAME` (+ `drive.exclude_*` in config/site.yml) |
| title, endings, camera names | drive.py | `build_item()`, `_KNOWN_EXT`, `strip_ext()`, `tidy()`, `is_generic_media_name()` |
| type label | drive.py | `file_type_label()` |
| Open, Preview, Download and picture links | drive.py | `_NATIVE`, `urls_for()` |
| bulletin texts | drive.py | `body_url()`, `fetch_body()`, `docx_to_text()`, `_decode()`, `normalize_body()`, `fill_announcements()` |
| forms open or closed | drive.py | `check_forms()` |
| booth names, types and messages | [booth_names.py](../scripts/sync/booth_names.py); drive.py; build_data.py | `parse_booth_name()`, `media_type()`, `_EXT`, `message_text()`, `problem_of()`; `fill_booth_texts()`, `text_langs()`; `build_booth()`, `booth_item()` |
| which site file an item reaches | [build_data.py](../scripts/sync/build_data.py) | `Ctx.items()`, `simple()`, `closed_form()`, `build_announcements()`, `flyer_events()`, `plan_whatsnew()`, `build_booth()` |
| Portfolio cards and albums | [committee.js](../eleventy/filters/committee.js) | `isDocItem()`, `isPhotoItem()`, `fileType()`, `documentTabs()`, `photoAlbums()` |
| Library and search | [library.js](../eleventy/filters/library.js) | `libraryDocs()`, `DRIVE_SKIP_KINDS`, `DRIVE_SKIP_CATS`, `docKitType()` |
| home tiles | [home.js](../eleventy/filters/home.js) | the `homeDrive` filter |
| monthly digest | [community.js](../eleventy/filters/community.js); [send_digest.py](../scripts/notify/send_digest.py) | `monthNews()`; `DRIVE_CATEGORIES` |

**Run the tests** before you push (the *Code check* runs them again on every push): on a computer,
`python -m unittest tests.test_sync_pipeline tests.test_booth_names tests.test_booth_sync`, or all of them with
`python -m unittest discover -s tests` ([Automation and troubleshooting](automation-and-troubleshooting.md) explains
the set-up).

---

## 10. Troubleshooting

**Where to look first:**

1. The run summary of the newest *Update & Deploy* run (GitHub → **Actions**): the **Content sources** table (the
   row "Google Drive (committee uploads)": OK or **PROBLEM**), the **Notes** (up to two per source: unreadable
   folders, a very big folder, booth problems), **Booth folder files the booth display can't show**, **Scheduled
   bulletin posts** and, from the publishing job, **Booth display (copies for offline)**.
2. `/status/` (`/es/status/`): the Drive row — state, number of files, last good check.
3. `data/raw/drive.json` on GitHub → `stats`: `by_kind`, `by_category`, `excluded_by_reason` (why files were left
   out — reasons only, never names), `loose_skipped`, `unreadable_folders`, `depth_limited`, `warnings`,
   `announcements` and `booth_texts` (text downloads), `forms` (open and closed checks).
4. For the booth: `data/site/booth.json` → `problems`, and the player's **Settings → Slides** tab (**Ajustes →
   Diapositivas**), which also names the files the build left out (a word the booth never shows, a video or sound
   file not saved for offline).

| What you see | Likely cause | What to do |
|---|---|---|
| The file is nowhere on the site | no update since the upload; it sits outside the panel folder (loose in A65_GV); its name contains `PRIVATE`, `PRIVADO`, `(Responses)`, `(Respuestas)` or `wrong size` (also inside a word: "privately"); it is a spreadsheet or CSV; it is a form that stopped accepting answers; it is in the booth folder (booth only); its folder's sharing was changed; it sits more than 6 folder levels below the panel folder | run *Update & Deploy* with **skip_crawl**; move it into a folder of 2027-2028_Panel77_GVLV; rename it; share figures as a PDF; switch "Accepting responses" on; move it up; check `excluded_by_reason`, `unreadable_folders` and `depth_limited` |
| It is on the home tiles and in What's New, but not on the Portfolio or `/photos/` | a document, form or deck in `photos` | move it to the right folder |
| A picture is an album photo instead of a Portfolio card (or the other way round) | album photos come from `photos`, folders of your own and the panel folder itself; Portfolio cards from the built-in folders | move it |
| The card shows only an icon | Drive has not made its picture yet (a new video, a HEIC); the type has none (sound, `.zip`); a shortcut whose original is not shared publicly, or that Drive did not answer for | wait; share the original "Anyone with the link"; the site tries a shortcut again at every run |
| The title ends in ".jfif", ".avif", ".markdown", ".aac" … | an ending the site does not know | rename it (`.jpg`, `.md`, `.mp3`) or see [9.1](#91-take-another-ending-out-of-titles-jfif-avif-markdown) |
| The caption is "2027 Spring Assembly #3" | a camera name | rename the file to say what it shows |
| The caption is "PXL 150102123.MP" | a Pixel motion photo's name | rename it ([Photos … §7.5](photos-slides-reports.md#75-number-more-camera-names-eg-pixel-motion-photos)) |
| A bulletin post has only its headline | the file is a PDF, picture, video, `.doc`, `.odt` or `.rtf` (no text is read); a `.docx` bigger than 3 MB (pictures pasted into it); a Google Doc that is not readable by "anyone with the link"; the download failed (the run's log says "could not download text" or "Drive returned an HTML page instead of the file") or waited for the next run (more than 40 text downloads) | use a Google Doc, `.docx`, `.txt` or `.md`; take the pictures out of a big Word file; fix the Doc's sharing; wait for the next run |
| Two lines run together: "Line oneLine two" | a Shift+Enter line break in Word | press Enter between lines ([Bulletin §6.6](bulletin.md#66-recipe-keep-line-breaks-from-word-files) shows how to change the reader) |
| A post shows codes like `{\rtf1\ansi` or `<p>` | an `.rtf` that Drive calls text, or an `.html` file | save it as `.docx`, `.md` or a Google Doc |
| A form shows as a "Document" card with no **Sign up** | it is a shortcut with no ending in its name | put the form itself in `forms` |
| A form disappeared | it no longer accepts answers | switch "Accepting responses" on; it comes back at the next update |
| A flyer did not become an event | no day date in the name, only "Month YYYY", a phone's own name, or the file is not in `flyers` | name it `2027-03-14 …` ([Flyers and events §4.8](flyers-and-events.md#48-names-that-do-not-make-an-event)) |
| An event shows twice | a dated flyer that a `content/events` file also links with `flyer:` | keep a linked flyer undated |
| An event is titled "IMG 1234" | a date written in front of a camera name | rename it: `2027-03-14 Spring Assembly booth.jpg` |
| **Present on the web** vanished from a deck | its title no longer equals its `drive_title` | rename it back (exact words) or change `drive_title` |
| A downloaded photo will not open | it is the HEIC original | upload a JPG for files meant for download; iPhone: **Formats → Most Compatible** |
| Drive's player says the video is still processing | Drive has not finished | wait; very long or 4K videos take longest — upload a shorter 1080p copy |
| A booth file is not in the show | a problem in `booth.json` (type, empty message, `(from …)` after `(until …)`); a word the booth never shows in its caption or note; switched off (`(off)`, `(draft)`, a name starting `_` or `~`); before its `(from …)` day or past its `(until …)` day; a video or sound file that could not be saved for offline (over 95 MB, over the folder's 400 MB, or a failed download); the player's language, magazine or collection settings leave it out | the player's Settings → Slides shows why (a file switched off or past its day is not listed there at all); see [Booth display](booth.md) |
| A booth picture marked `(x3)` comes up no more often than the others | with only a few pictures and videos each one already comes back as often as the show's rules let it | nothing to fix: the mark counts once the show has more of them |
| Booth files show on the Portfolio or `/photos/` | the folder's name has no booth word (for example "Our table") | rename it `booth` or `mesa` |
| The files of a folder left the Portfolio | its name holds a booth word (`Display`, `Stand`, `Mesa`, `Exhibit` …) | rename it |
| A booth file is left out, but the run summary's booth list does not name it | the list shows the sync's problems only (`data/site/booth.json` → `problems`); a word the booth never shows and a video or sound file not saved for offline are found later, when the site is built | the player's **Settings → Slides** tab; the log of *Build the website* (`[booth]` lines); for an unsaved file also the warning "Booth display: a file was not saved for offline" |

---

## 11. Good practice and AA principles

- **Everything in A65_GV is public.** The folders are shared "Anyone with the link", and the site links to them —
  including the files the site leaves out (PRIVATE files, spreadsheets, "(Responses)" sheets). Keep private drafts,
  contact lists, budgets and form answers out of A65_GV altogether.
- **A file name is public too.** It becomes the title on the site and is stored in the public repository
  (`data/raw/drive.json`).
- **Anonymity.** No full names in file names, captions, flyers, minutes or recordings — a service title ("the
  Chair") or a first name at most. No picture in which an AA member's face can be recognized: tables, literature,
  displays, banners and rooms instead. Look for name tags and sign-in sheets in the background.
- **Location data.** Switch the location off before uploading phone pictures ([4.10](#410-pictures-and-iphone-heic-photos)).
- **Recordings** only with the speaker's permission, and no full names in them. Grapevine's and La Viña's own
  audio and video stay on their official channels — link to them instead of uploading copies.
- **Share only what we may share.** Material the committee made, or has permission for. In the booth folder: no
  Grapevine or La Viña logos, covers, artwork or cartoons, and none of their audio or video files.
- **Attraction rather than promotion.** Plain, factual titles and captions ("Literature display at the Spring
  Assembly"); no sales talk.
- **Sign-up forms:** ask only what you need; the answers are personal information.
- **Whose account owns the files.** Drive's viewer page can carry the owner's e-mail address in its page data.
  Upload with the committee's Google account, or transfer ownership to it (the links stay the same).
- **Pick the friendliest type:** PDF for things to read and print, JPG or PNG for flyers, MP4 (H.264) for video,
  MP3 for sound, a Google Doc or `.md` for bulletin posts.

---

## 12. See also

- [How-to guide index](README.md) · [The Drive panel folder](drive-panel-folder.md) — folders, sharing, dates,
  what is never published
- [Flyers and events](flyers-and-events.md) · [Bulletin](bulletin.md) ·
  [Photos, slides, reports …](photos-slides-reports.md) · [Booth display](booth.md) — the player, the CSV, the
  `booth:` settings
- [Presentations](presentations.md) (the four web decks and their `drive_title`) · [Settings](settings.md)
  (`config/site.yml`) · [Translations](translations.md) (fix a translated title)
- [Automation and troubleshooting](automation-and-troubleshooting.md) (runs, the run summary, tests) ·
  [Pages and code](pages-and-code.md) · [E-mail and alerts](email-and-alerts.md) (the monthly digest e-mail) ·
  [Automatic sources](automatic-sources.md)
- Code: [drive.py](../scripts/sync/drive.py) · [drive_listing.py](../scripts/sync/drive_listing.py) ·
  [booth_names.py](../scripts/sync/booth_names.py) · [build_data.py](../scripts/sync/build_data.py) ·
  [committee.js](../eleventy/filters/committee.js) · [library.js](../eleventy/filters/library.js) ·
  [home.js](../eleventy/filters/home.js) · [community.js](../eleventy/filters/community.js) ·
  [send_digest.py](../scripts/notify/send_digest.py)
- Settings and data: [config/site.yml](../config/site.yml) (`drive:`, `booth:`) ·
  [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md) · [README.md](../README.md) section 2
