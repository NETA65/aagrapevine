# The bulletin: post news and notices

The committee's notice board on the website: **`/bulletin/`** in English and **`/es/bulletin/`** in Spanish
(full address `https://neta65.github.io/aagrapevine/bulletin/`). This guide shows every way to put a post there,
every option you can use, and every place a post turns up.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start](#2-quick-start)
3. [Full reference](#3-full-reference) — Drive posts (3.1–3.6), GitHub posts (3.7–3.12), dates and pinning (3.13), languages (3.14)
4. [What happens next](#4-what-happens-next)
5. [Where it shows on the website](#5-where-it-shows-on-the-website)
6. [Going further: change the code](#6-going-further-change-the-code)
7. [Troubleshooting](#7-troubleshooting)
8. [Good practice and AA principles](#8-good-practice-and-aa-principles)
9. [See also](#9-see-also)

---

## 1. What this is

The bulletin holds short news from the committee for groups, districts, GVRs and RLVs: an orientation, a
workshop, a price change, a service opportunity. A post comes from one of two places:

- **(A) Google Drive** — a document in the **bulletin** folder of the current Panel folder. This is the easy way:
  no GitHub needed. The file name is the headline.
- **(B) GitHub** — a Markdown file in [`content/bulletin/`](../content/bulletin/). More options: a header with
  dates and switches, your own translation, pictures saved next to the post.

Both kinds look the same on the site. Every post is translated English ⇄ Spanish and shows on the Bulletin page,
the home page, What's New, the RSS feed, the site search and the monthly digest (page and e-mail).
[Section 5](#5-where-it-shows-on-the-website) lists every place.

> **Note — the old name.** Until September 2026 the bulletin was called "Announcements", and the code and data
> still use that name: the data file is `data/site/announcements.json`, a post's kind is `announcement`, and a
> GitHub post's id is `ann:` plus its file name (small letters and dashes, without `.md`). The old address
> `/announcements/` forwards to `/bulletin/`.

---

## 2. Quick start

### From Google Drive (most posts)

1. Open the Drive folder **A65_GV › 2027-2028_Panel77_GVLV › bulletin**. (Shortcut: at the bottom of `/bulletin/`,
   open *For committee members · Post to the bulletin*. **Open Drive folder** opens the current Panel folder;
   **Ask for upload access** writes to grapevine@neta65.org.)
2. Create a Google Doc in that folder. Name it with the date first, then the headline:
   `2027-01-10 Welcome new GVRs`
3. Write the notice in the document. Plain paragraphs work best. For a heading, type `# ` at the start of the line.
4. Optional words at the end of the name: `(pinned)` keeps it on top, `(from 2027-02-01)` keeps it off the site until
   that day, `(until 2027-03-01)` takes it down after that day.
5. Wait for the next update: the midday refresh (usually around 11 AM to 1 PM Central) or the evening refresh
   (around 7 to 9 PM), else early the next morning (by about 5:30 AM Central when the morning alarm is set up — see
   [Automation and troubleshooting](automation-and-troubleshooting.md)). In a hurry? On GitHub go to
   **Actions** → **Website update** → **Run workflow**, tick the box *Quick refresh only: Google Drive, the
   bulletin, podcasts, the daily quote and the writers archive* (the `skip_crawl` option), press **Run workflow** (a
   few minutes).

What you get: a post headed "Welcome new GVRs", dated Sunday, January 10, 2027, on `/bulletin/` and, translated,
on `/es/bulletin/`; on the home page under "From the committee"; in What's New and the RSS feed.

### From GitHub (when you want more options)

1. On github.com open the folder `content/bulletin/` → **Add file** → **Create new file**.
2. Name the file `2027-01-10-welcome-new-gvrs.md` (the date, then words joined by dashes, ending in `.md`).
3. Paste this and change the words:

   ```markdown
   ---
   title: Welcome, new GVRs and RLVs!
   expires: 2027-03-31
   ---
   Come to our committee meeting on the third Wednesday of the month.
   ```

4. Press **Commit changes** (on the `main` branch). That starts **Website update** by itself; the post is usually
   live a few minutes later (a page may take up to about 10 more minutes to show it everywhere).

What you get: the post at `/bulletin/#2027-01-10-welcome-new-gvrs` (and `/es/bulletin/#2027-01-10-welcome-new-gvrs`),
dated January 10, 2027 (from the file name), shown through March 31, 2027.

> **Tip.** [`content/bulletin/_example.md`](../content/bulletin/_example.md) shows every option in one file. Copy it,
> name the copy without the `_`, and delete what you don't need. A file whose name starts with `_` is never posted.

---

## 3. Full reference

### 3.1 Drive or GitHub? What each can do

| You want… | Drive document | GitHub file (`content/bulletin/*.md`) |
|---|---|---|
| Post without a GitHub login | yes | no (needs write access to the repository) |
| The headline | the file name | `title:` (else the first `# ` heading, else the file name) |
| The date shown | a date in the name | `date:` (else a date in the file name) |
| Keep it on top | `(pinned)`, `(fijado)` or `📌` in the name | `pinned: true` |
| Appear on a later day | `(from 2027-02-01)` / `(desde 2027-02-01)` | `publish: 2027-02-01` |
| Come down after a day | `(until 2027-03-01)` / `(hasta 2027-03-01)` | `expires: 2027-03-01` |
| A **More information** button | no (a Drive post gets **Open the document** instead; a `.md`/`.txt` post gets no button) | `url:` |
| Your own Spanish (or English) | only through `data/translations/overrides.yml` ([3.14](#314-languages-automatic-and-by-hand)) | `title_es` + `summary_es` in the header |
| Pictures inside the text | only with a full `https://…` address | files saved next to the post, or a full address |
| HTML pasted from an e-mail | shown as raw text | turned into clean Markdown |
| A picture next to the item in the RSS feed | a PDF's or picture's own thumbnail | `image:` |
| Headings, lists, links, tables | `.md`/`.txt` files: all of it. Google Doc or Word: only the marks you type | all of it |

### 3.2 Drive: put the file in the right folder

The **first folder under the Panel folder** decides what a file becomes. These folder names make a bulletin folder.
Capitals and accents don't matter, and the word may stand anywhere in the folder name, as a whole word:

`bulletin` · `bulletins` · `bulletin board` · `boletín` (`boletin`) · `boletines` · `announcement` · `announcements` ·
`anuncio` · `anuncios` · `aviso` · `avisos` · `news` · `noticias`

| Folder | Result |
|---|---|
| `A65_GV › 2027-2028_Panel77_GVLV › bulletin` | bulletin posts (this is the real folder) |
| `… › 2027-2028_Panel77_GVLV › Boletín` | bulletin posts; a Spanish folder name also hints that the posts are in Spanish |
| `… › 2027-2028_Panel77_GVLV › bulletin › 2027 spring` | bulletin posts too (sub-folders are read) |
| `… › Bulletin Board`, `… › bulletins 2027`, `… › La Viña news` | bulletin posts |
| `… › Newsletter`, `… › Board`, `… › Notices` | **not** the bulletin: these files become Portfolio files in a tab named after the folder (pictures and videos: a `/photos/` album of that name) |
| `A65_GV › bulletin` (directly in the root) | **ignored** — only folders inside a Panel folder are read |
| `A65_GV › 2029-2030_Panel79_GVLV › bulletin` | bulletin posts as soon as that Panel folder exists (Panels from 77 up are read) |

More about Panel folders, sharing and the other folders: [The Drive panel folder](drive-panel-folder.md). The booth
display has its own folder (`booth`, also `mesa`, `kiosk`, `display`, `stand` …): a text file there becomes a note
on the booth's screen, never a bulletin post ([The Drive panel folder §3.6](drive-panel-folder.md#36-the-booth-folder-new),
[Booth display](booth.md)).

### 3.3 Drive: which files become posts, and what the text is

Every file in the bulletin folder becomes a post. What the post shows depends on the file type:

| File type | Text of the post | Button on the post |
|---|---|---|
| Google Doc | the Doc's words (the site reads Google's plain-text copy of it) | **Open the document** |
| `.md` or `.txt` | the file's text; all Markdown works | none — the whole text is already shown |
| `.docx` (Word) | the words of each paragraph (see below) | **Open the document** |
| PDF, picture (`.jpg`, `.png` …), `.doc`, `.odt`, `.rtf`, slides, anything else | **no text** — only the headline and the date | **Open the document** (opens the file on Drive) |

Never published, in any folder: spreadsheets and CSV files, and any file whose name contains `PRIVATE`, `PRIVADO`,
`(Responses)`, `(Respuestas)` or `wrong size` (capitals don't matter). They stay visible to anyone who opens the
Drive folder, though.

> **Note.** The help texts say to use "a Google Doc, .txt, .md or .docx". That is the right advice, but the code also
> turns a PDF or a picture into a post — a headline-only post. The picture itself is not shown on `/bulletin/`;
> only its thumbnail goes into the RSS feed. For a flyer, a short Google Doc with the details works better, or put the
> flyer in `flyers/` with its date in the name so it becomes an event ([Flyers and events](flyers-and-events.md)).

**Google Docs.** Write plain paragraphs. What you make with Google's toolbar — bold, heading styles, pictures, a link
hidden behind words — does not reach the site. Instead:

- type `# ` at the start of a line for a heading (`## ` for a smaller one);
- paste web addresses in full (`https://www.aagrapevine.org`): the site makes them clickable;
- look at the post after the update. If a heading or a list does not come out the way you want, upload the same text
  as a `.md` or `.txt` file instead (everything in [3.11](#311-what-the-text-can-hold-markdown) works there).

**`.md` and `.txt` files.** Full Markdown works. Use the ending `.md`, **not** `.markdown`: on Drive, `.markdown` stays
in the headline ("Welcome.markdown"). A header block (`---` / `title: …` / `---`) is **not** read in a Drive file —
it shows up as a line and a heading "title: …". Use a GitHub post for header options.

**Word (`.docx`).** Only the words of each paragraph come through:

- bold, italics and heading styles are lost; a table loses its shape (each cell becomes a paragraph of its own);
  a link keeps only its words;
- every bulleted or numbered item becomes a `*` bullet;
- **a line break made with Shift+Enter is lost and the two lines run together** ("Line one" + "Line two" →
  "Line oneLine two"). Press Enter (a new paragraph) instead;
- a paragraph you start with `# ` becomes a heading.

**Clean-up (every file with text).** A first line that repeats the headline is dropped (Google Docs often start with
the title). Runs of blank lines become one; stray no-break and zero-width spaces are tidied. A text longer than
**12,000 characters** is cut at the end of a line and ends with "…".

### 3.4 Drive: name the file

The file name gives the headline, the date and three switches. The site reads it in this order:

1. The ending (`.pdf`, `.docx`, `.md`, `.txt`, `.jpg` …) is removed. So are `Copy of` / `Copia de` at the start and
   `(1)`, `(2)`, `copy`, `copia` at the end.
2. **Pin:** `(pinned)`, `(fijado)`, `(fijo)` or `(pin)` — round or square brackets, any capitals — or the 📌 emoji,
   anywhere in the name. Always removed from the headline.
3. **Until:** `(until …)`, `(expires …)`, `(expire …)`, `(hasta …)` or `(vence …)`; a colon after the word is fine.
   Removed **only when it holds a date with its year** (any form in the table below; a month and year alone counts
   as the 1st).
4. **From:** `(from …)`, `(publish …)`, `(desde …)` or `(publicar …)`; colon optional. Removed only when it holds a
   date with its year.
5. **Date:** a date found in what is left (anywhere; the start is best) is the post's date and is removed
   from the headline — except a month-only date ("March 2027 Newsletter"), which stays in it. With two dates in
   the name, the first one of the same form wins, but a number date beats a written one:
   `October 5, 2027 Fall Assembly moved to 2027-10-12` is dated October 12 and keeps "October 5, 2027" in its
   headline. Keep a second date out of the name, or write it without its year.
6. **Tidy:** `_` and `%20` become spaces, `GV_LV` / `GV-LV` / `GV LV` become `GV/LV`, double spaces go, and dashes,
   dots and commas at either end are trimmed.

Everything else stays in the headline exactly as you typed it — including other words in brackets, like
`(draft)` or `(from the Chair)`.

#### The three switches

| Switch | Write in the name | What it does | If the date has no year (or is not a date) |
|---|---|---|---|
| Pin | `(pinned)` `(fijado)` `(fijo)` `(pin)` `[pinned]` `📌` | first on the bulletin, on the home page and in the digest, with a "Pinned" / "Destacado" badge | — (no date needed) |
| Until | `(until 2027-03-01)` `(expires 2027-03-01)` `(hasta 2027-03-01)` `(vence 2027-03-01)` | shown **through** that day (Central time), gone after it | the words stay in the headline and the post never comes down |
| From | `(from 2027-02-01)` `(publish 2027-02-01)` `(desde 2027-02-01)` `(publicar 2027-02-01)` | not on the site before that day; appears with that day's first update | the words stay in the headline and the post shows at once |

#### Dates the site understands

These forms work in a file name and inside `(until …)` / `(from …)`. The year must be written in full (20xx).

| You write | The site reads |
|---|---|
| `2027-01-10`, `2027.01.10`, `2027_01_10`, `2027 01 10`, `2027-1-5` | January 10, 2027 (January 5 for the last one) |
| `20270110` | January 10, 2027 |
| `01-10-2027`, `01/10/2027`, `1.10.2027` in an English name | January 10, 2027 — **month first** (US order) |
| the same in a Spanish name (`01-10-2027 Asamblea de otoño`) | **October 1**, 2027 — **day first** (since October 2026) |
| `01/02/2027` after a Spanish word in brackets: `(hasta 01/02/2027)`, `(vence …)`, `(desde …)`, `(publicar …)` | **February 1**, 2027 — **day first**, with no note (since October 2026: the bracket's word decides) |
| `01/02/2027` with no words to tell the language (a short name, or after an English word: `(until …)`, `(expires …)`, `(from …)`, `(publish …)`) | **January 2**, 2027 (month first), and the run summary's *Notes* say it "could be January 2 or February 1, 2027" |
| `14-03-2027` | March 14, 2027: a first number over 12 can only be the day (since October 2026; before, nothing) |
| `Jan 10 2027`, `January 10, 2027`, `Jan. 10th, 2027`, `Sept 5 2027` | that day |
| `10 de enero de 2027`, `10 enero 2027`, `el 1 de febrero de 2027` | that day |
| `January 2027`, `enero de 2027` | **the 1st** of that month |
| `Feb 1`, `2/1/27`, `2027`, `2027-2028` | not a date |

**Safest: always write `YYYY-MM-DD`** (`2027-02-01`). Nobody can misread it, in either language.

#### Examples (each checked with the site's own code)

"Drive's date" is explained below the table.

| File name in `bulletin/` | Headline | Date shown | Pinned | Until | From |
|---|---|---|---|---|---|
| `2027-01-10 Welcome new GVRs` | Welcome new GVRs | Jan 10, 2027 | – | – | – |
| `2027-01-10 Welcome new GVRs (pinned)` | Welcome new GVRs | Jan 10, 2027 | yes | – | – |
| `2027-01-10 Bienvenidos nuevos RLV (fijado)` | Bienvenidos nuevos RLV | Jan 10, 2027 | yes | – | – |
| `📌 Reminder for GVRs` | Reminder for GVRs | Drive's date | yes | – | – |
| `Reminder [PINNED]` · `Reminder (pin)` · `Aviso (fijo)` | Reminder · Reminder · Aviso | Drive's date | yes | – | – |
| `Summer schedule (until 2027-08-31)` | Summer schedule | Drive's date | – | Aug 31, 2027 | – |
| `Horario de verano (hasta 2027-08-31)` | Horario de verano | Drive's date | – | Aug 31, 2027 | – |
| `Aviso (hasta el 1 de febrero de 2027)` | Aviso | Drive's date | – | Feb 1, 2027 | – |
| `Aviso (hasta el 1 de febrero)` | **Aviso (hasta el 1 de febrero)** | Drive's date | – | never (no year) | – |
| `Notice (until Feb 1, 2027)` · `Notice (expires: 2027-02-01)` | Notice | Drive's date | – | Feb 1, 2027 | – |
| `Notice (until Feb 1)` | **Notice (until Feb 1)** | Drive's date | – | never (no year) | – |
| `Notice (until further notice)` | Notice (until further notice) | Drive's date | – | never | – |
| `Notice (until March 2027)` | Notice | Drive's date | – | **Mar 1**, 2027 | – |
| `Aviso (hasta 01/02/2027)` | Aviso | Drive's date | – | **Feb 1**, 2027 (day first after `hasta`; since October 2026) | – |
| `Aviso de la junta (hasta 05-11-2026)` | Aviso de la junta | Drive's date | – | **Nov 5**, 2026 | – |
| `Spring Assembly sign-ups (from 2027-02-01)` | Spring Assembly sign-ups | Feb 1, 2027 | – | – | Feb 1, 2027 |
| `Inscripciones (desde 2027-02-01)` · `Inscripciones (publicar: 2027-02-01)` | Inscripciones | Feb 1, 2027 | – | – | Feb 1, 2027 |
| `2027-01-20 Sign-ups open (from 2027-02-01)` | Sign-ups open | Jan 20, 2027 | – | – | Feb 1, 2027 |
| `A note (from the Chair)` | A note (from the Chair) | Drive's date | – | – | – |
| `A letter (from the Chair) (from 2027-02-01)` | A letter (from the Chair) | Feb 1, 2027 | – | – | Feb 1, 2027 |
| `Workshop (from 2027-02-01) (until 2027-02-28) (pinned)` | Workshop | Feb 1, 2027 | yes | Feb 28, 2027 | Feb 1, 2027 |
| `Copy of 2027-01-10 Welcome new GVRs` | Welcome new GVRs | Jan 10, 2027 | – | – | – |
| `2027-01-10 Welcome new GVRs (1).docx` | Welcome new GVRs | Jan 10, 2027 | – | – | – |
| `Welcome new GVRs 2027-01-10` | Welcome new GVRs | Jan 10, 2027 | – | – | – |
| `2027-01-10 Meeting moved to 2027-01-17` | Meeting moved to 2027-01-17 | Jan 10, 2027 | – | – | – |
| `October 5, 2027 Fall Assembly` | Fall Assembly | Oct 5, 2027 | – | – | – |
| `5 de octubre de 2027 Asamblea de otoño` | Asamblea de otoño | Oct 5, 2027 | – | – | – |
| `10-05-2027 Fall Assembly.txt` | Fall Assembly | **Oct 5**, 2027 (month first) | – | – | – |
| `10-05-2027 Asamblea de otoño.txt` | Asamblea de otoño | **May 10**, 2027 (a Spanish name: day first) | – | – | – |
| `March 2027 Newsletter.md` | March 2027 Newsletter | Mar 1, 2027 | – | – | – |
| `Welcome_new_GVRs.txt` | Welcome new GVRs | Drive's date | – | – | – |
| `GV_LV booth volunteers` | GV/LV booth volunteers | Drive's date | – | – | – |
| `Welcome.markdown` | **Welcome.markdown** | Drive's date | – | – | – |
| `Welcome (draft)` | **Welcome (draft)** — and it is live! | Drive's date | – | – | – |
| `2027-03-14 Spring Assembly flyer.pdf` | Spring Assembly flyer (no text, "Open the document") | Mar 14, 2027 | – | – | – |

**Drive's date.** When the name has no date (and no `(from …)` date), the post is dated with what Drive shows as the
file's "last modified" day. (Today the site reads Drive without an API key. If the NETA65 admin account ever adds a
`GOOGLE_API_KEY` secret, it is the day the file was created instead.) So **an undated doc jumps to the top and takes
a new date each time someone edits it**. Start the name with a date to avoid that.

**Language.** A Drive post's language is guessed from the headline and the first 600 characters of its text. A
Spanish folder name such as `boletín` tips a close call to Spanish.

### 3.5 Drive: what a Drive post cannot do

- No header lines: no `url:` button, no `image:`, no `title_es`/`summary_es`. Only the name switches above.
- No pictures from the same folder: `![flyer](flyer.jpg)` in a Drive `.md` file is a broken picture. Use the full
  `https://…` address of a picture that anyone can open.
- No HTML clean-up: tags such as `<b>` in a `.md` or `.txt` file show as text.
- The headline is always the file name, never the first heading of the text.
- Your own Spanish wording only through `overrides.yml` ([3.14](#314-languages-automatic-and-by-hand)).

### 3.6 Drive: the real post today

The Drive folder `bulletin/` holds one file, `Grapevine and La Viña — ways to carry the message.md`. The site makes:

- the headline "Grapevine and La Viña — ways to carry the message", dated October 1, 2026 — its "last modified" day,
  because the name has no date;
- a text with 7 `# ` headings (Why it matters, What groups can do, At meetings, One on one, Online, Beyond the meeting
  room, Every month), so a computer screen shows an **In this post** list beside it;
- no **Open the document** button, because a plain `.md` text is shown in full already;
- the anchor `/bulletin/#ann-drive-18tn2g-nxzokd8rmd9xq5pnmpata5jsnw`. A Drive post's anchor is `ann-drive-` plus
  its Drive file id in small letters (a `_` in the id becomes `-`), so it stays the same when the file is renamed;
- Spanish written by hand in `data/translations/overrides.yml` (headline, summary and whole text), so
  `/es/bulletin/` shows no "Auto-translated" note.

### 3.7 GitHub: the folder and the file name

- The folder is [`content/bulletin/`](../content/bulletin/). (The old folder `content/announcements/` still works,
  but the run summary asks you to move the post; a post of the same name in `content/bulletin/` wins.)
- A post is a file ending in `.md` or `.markdown`, any capitals (`Spring.MD` works).
- Never a post: names starting with `_` (like `_example.md` or `_draft-welcome.md`), with `.`, or with `README`.
- Pictures and documents for the posts sit in the same folder: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.pdf`
  ([3.10](#310-github-pictures-and-documents-next-to-the-post)).
- Any other file (`Assembly.txt`, `notes.docx`) is not read. The run summary says:
  `bulletin/Assembly.txt: ignored — only files ending in .md are read (rename it to end in .md); pictures and documents (.jpg, .jpeg, .png, .gif, .webp, .pdf) are published for the posts to link to`

The file name does three jobs:

| Part of the name | Used for | `2027-01-10-welcome-new-gvrs.md` gives |
|---|---|---|
| a date anywhere in it | the date shown, when there is no `date:` line | January 10, 2027 |
| the whole name, in small letters with dashes | the post's id (`ann:…`) and its anchor | `/bulletin/#2027-01-10-welcome-new-gvrs` |
| the words after the date | the headline, when there is no `title:` and no heading | "Welcome new gvrs" (so give it a title!) |

Rules that follow from this:

- **Use short names:** small letters, digits and dashes. Only the first 80 characters of the name count for the id
  and the anchor (a longer name is cut there — links still work, but two long names that start with the same
  80 characters clash as a `duplicate name`). A name such as `how-to-post`, `subscribe`, `main` or `item`, or one
  starting with `month-`, `docs-` or `cm-`, gets a different anchor on the page (`ann-…`) than the links in What's
  New and the search, which then don't jump to the post.
- **Renaming a file makes it a new post:** new id, new anchor (links shared before stop jumping to it) and a new
  "first seen" day — a post without a date gets a new date and the "New" badge again.
- **Two files that give the same name** (`Spring.MD` and `spring.markdown`): the second is skipped, and the run summary
  says `duplicate name`.

### 3.8 GitHub: the header — every option

The header is optional. It sits between a first line `---` and the next `---` line. A line starting with `#` inside
it is a note for you; the site ignores it.

| Header line | What you can write | If you leave it out | What it does and where it shows |
|---|---|---|---|
| `title:` | text | the first line if it is a heading, else the first `# ` heading, else the file name | the headline everywhere |
| `date:` | a date (forms below) | a date in the file name, else the `publish:` day, else the day the post first appears (its Central-time day: a post first seen at 9:30 PM CDT keeps that evening's date) | the date printed on the post; the order of the lists (newest first); the "New" badge and What's New |
| `publish:` | a date | on the site as soon as it is saved | keeps the post out of every page until that day (Central time); meanwhile the run summary lists it under "Scheduled bulletin posts" |
| `expires:` | a date | never comes down | shown through that day, gone after it; "until …" shows under the date |
| `pinned:` | `true` `yes` `y` `on` `1` `sí` `si` (any capitals) = pinned; anything else = not | not pinned | first on the bulletin, on the home page and in the digest; "Pinned" / "Destacado" badge |
| `lang:` (or `language:`) | `en` or `es` — only the first two letters count, so `English`, `Español` and `es-MX` work, but `Spanish` does **not** | guessed from the title and text | the language you wrote in; the other page gets the translation |
| `url:` (or `link:`) | a web address (`www.…` without `https://` is repaired by itself), a page of the site like `/events/`, or a file saved next to the post | none | a **More information** button; also where What's New, the RSS feed and the digest link to ([5.2](#52-which-link-goes-where)) |
| `image:` | a picture saved next to the post (`flyer.jpg`) or a web address | none | **only the RSS feed** shows it (see the note below) |
| `summary:` | one line of text | the text below the header, as plain words | the teaser (400 characters at most): home card of a long post, What's New, the feed, the search, the Share text, the digest page. The Bulletin page still shows the whole text |
| `tags:` | `prices, books` or a YAML list | none | stored only — not shown or searched anywhere |
| `title_es:` + `summary_es:` (file written in English), `title_en:` + `summary_en:` (file written in Spanish) | text; for paragraphs or a list, write `summary_es: \|` and the text on the lines below, each indented two spaces | machine translation | your own words on the other-language page, with no "Auto-translated" note. `summary_es` is the **whole** Spanish text, not just a teaser ([3.14](#314-languages-automatic-and-by-hand)) |

> **Note — `image:`.** `_example.md` and the folder README describe `image:` as a picture "for the post's card in
> lists". In the code today only the RSS feed (`/feed.xml`, `/es/feed.xml`) uses it. To show a picture on the page,
> put it in the text: `![The flyer](flyer.jpg)`. To show `image:` on the cards too, see recipe 6.4.

> **Note — `until:` and `from:` are Drive words.** In a GitHub header they are silently ignored (checked). Use
> `expires:` and `publish:`.

**Date forms** for `date:`, `publish:` and `expires:`: `2027-01-10`, `2027-1-5`, `March 5, 2027`,
`5 de marzo de 2027`, `03/05/2027` (= March 5 in a post written in English; since October 2026 = **May 3** in a post
written in Spanish: a date in numbers only follows the post's language), `2027.03.05`, `20270305`, and `March 2027`
(= **March 1**). For `expires:` always write the last day itself: `expires: 2027-03-31`, not `expires: March 2027`.

**When to put a value in double quotes:**

- it contains `: ` — `title: "Reminder: Assembly Saturday"` (without quotes the site still manages, by reading the
  header line by line, but quotes are safer);
- it starts with `#` — `title: "#1 priority for GVRs"` (without quotes everything after `#` is a note, and the title
  is lost);
- it is `Yes`, `No`, `On`, `Off`, `True` or `False` — `title: "Yes"` (unquoted, `Yes` and `On` make the headline
  **"True"**, `No` and `Off` make it **"False"**);
- whenever you are unsure. Quotes never hurt.

**Mistakes the site reports.** A file with a mistake is not posted. If it was already on the site, its last good
version stays until you fix it. The run summary (section 7) lists the line, starting with the file's name:

| Mistake | Message |
|---|---|
| no closing `---` | `the header has no closing --- line (add a line with just --- below the header)` |
| a date it cannot read: `date: tomorrow` | `the date 'tomorrow' is not a date (use YYYY-MM-DD)` — also "the expires date …" and "the publish date …" |
| a date that does not exist: `expires: 2027-02-30` | `day is out of range for month` |
| `publish:` after `expires:` | `publish: is after expires: — the post would never show` |
| a broken header (a quote that is never closed, a tab used to indent) | `the header between the --- lines is not valid (line 2): … — if a value contains ": " … put the whole value in quotes: title: "Reminder: Assembly"` |
| a header that is a list (`- a`) | `the header between the --- lines must be 'name: value' lines` |
| nothing to make a headline from | `it has no title (add a line 'title: …' to the header)` |

On a PC with the repository (and Python with the packages of `requirements.txt`) you can check the posts before you
push: `python -m scripts.sync.announcements --dry-run`, run in the repository folder, prints every post as the site
reads it (and the `content/events/` files too), plus the problem list, and writes nothing. A post without a date
shows `"date": null` there; the real run gives it the day it first appears, in Central time.

### 3.9 GitHub: how the headline and the date are chosen

**Headline** — the first of these that exists:

1. `title:`. HTML tags in it are removed. If the text then starts with a `#` heading of the same words, that heading
   is dropped, so the title is not shown twice.
2. The text's first line, when it is a heading: `# Welcome`, `### Welcome`, or a line underlined with `===` or `---`.
   That line is taken out of the text.
3. The first `# ` heading anywhere in the text (a flyer picture may come before it).
4. The file name without its date: dashes and underscores become spaces, and only the first letter is raised.

| File | It starts with | Headline |
|---|---|---|
| `2027-01-10-welcome-new-gvrs.md` | `# Welcome, new GVRs and RLVs!` | Welcome, new GVRs and RLVs! |
| `2027-01-10-welcome-new-gvrs.md` | plain text, no header | **Welcome new gvrs** |
| `welcome-new-GVRs.md` | plain text | Welcome new GVRs |
| `setext.md` | `Spring news` with `===========` under it | Spring news |
| `flyer-first.md` | `![Flyer](flyer.jpg)`, then `# Fall Assembly` | Fall Assembly (the picture stays in the text) |
| `2027-01-11.md` | plain text | **2027 01 11** |
| `Panel 77 — Welcome_GVRs.md` | plain text | Panel 77 — Welcome GVRs |
| `yes.md` | `title: Yes` | **True** |
| `hash.md` | `title: #1 priority for GVRs`, then `# Heading in the text` | **Heading in the text** |

**Date shown** — the first that exists: `date:` → a date anywhere in the file name (`welcome-2027-02-14.md` works) →
`publish:` → the day the site first saw the file. Since October 2026 that last one is the Central-time day (before,
it was counted in UTC, so a file first seen late in the evening got the next day's date). Give important posts a
date.

The date is a label and the sort order. It does **not** decide when the post goes up (that is `publish:`) or
comes down (`expires:`).

### 3.10 GitHub: pictures and documents next to the post

1. Upload the file into `content/bulletin/` (**Add file** → **Upload files**): a `.jpg`, `.jpeg`, `.png`, `.gif`,
   `.webp` or `.pdf`. Keep a flyer photo under 1 MB.
2. Link it by its name in the text:

   ```markdown
   ![The Spring Assembly flyer](flyer.jpg)

   [The sign-up form](<Sign-up form.pdf>)
   ```

   A name with spaces goes between `< >` (or write `%20` for each space). Capitals don't matter for the match.
   Sub-folders don't work.

The site points these links to `/bulletin/files/flyer.jpg` and `/bulletin/files/Sign-up%20form.pdf` — the same
address on both language pages. `image:` and `url:` in the header may name such a file too.

If the file is missing, the picture shows its description in italics (*The Spring Assembly flyer*), a link shows only
its words, the post still appears, and the run summary says:
`bulletin/2027-03-01-fall-workshop.md: links to “flyer.jpg”, which is not in the folder (save it next to the post, with exactly that name)`

> **Careful.** Every picture and PDF in `content/bulletin/` is published at `/bulletin/files/` — also one that no
> post links to, and also for a post scheduled for later. Never upload anything private there.

### 3.11 What the text can hold (Markdown)

Bulletin text is Markdown. All of this works in GitHub posts and in Drive `.md`/`.txt` files. In a Google Doc or a
Word file, only what you type as plain characters works. A GitHub post has no length limit; a Drive text is cut at
12,000 characters.

| You write | You get |
|---|---|
| a single line break | a line break (no need for two spaces at the end) |
| a blank line | a new paragraph |
| `# Heading` … `###### Heading` | headings, one size under the post's own title, never skipping a size |
| `**bold**`, `*italic*`, `~~crossed out~~`, `` `code` `` | bold, italic, crossed out, code |
| `- item`, `* item`, `1. item`; two spaces in front for an item inside an item (three under a numbered item) | lists |
| `> a quotation` | a quotation |
| a table: cells between `\|`, and a row of `---` under the first row | a table that scrolls sideways on a phone |
| `---` alone on a line, **after a blank line** | a horizontal line (without the blank line, the line above becomes a heading) |
| `[words](https://…)`, `[words](mailto:grapevine@neta65.org)`, `[words](tel:+1…)` | links |
| `[our meetings](/meetings/)` | a link to the site's own page; on the Spanish page it goes to `/es/meetings/` by itself |
| `https://www.aalavina.org` or `grapevine@neta65.org` typed plainly | clickable |
| `www.neta65.org` without `https://` | **plain text, not a link** — always write `https://` |
| `![description](https://…/picture.jpg)` | a picture (in a GitHub post also a file saved next to the post) |
| emoji 🎉 | emoji |
| `- [ ] task` | the text "[ ] task" (no check boxes) |
| raw HTML | GitHub post: common tags are converted first (below); anything left shows as text. Drive post: shown as text |

**Two or more top-level headings** give the post an **In this post** list beside it on a wide screen
(about 1024 pixels and up). Each heading gets its own link, `/bulletin/#<post anchor>--<heading words>`, for example
`/bulletin/#2027-01-10-welcome-new-gvrs--who-can-come`. (One top heading with two or more smaller headings under it
works too; one `#` heading with a single `##` under it gives no list.)

**HTML pasted into a GitHub post** — from an e-mail or a web page — is turned into Markdown first:

| HTML | Becomes |
|---|---|
| `<b>`, `<strong>` · `<i>`, `<em>` · `<s>`, `<del>` · `<code>` | `**bold**` · `*italic*` · `~~crossed out~~` · `` `code` `` |
| `<h1>` … `<h6>` | `#` … `######` headings |
| `<br>` · `<hr>` · `<li>` | a line break · a horizontal line · a `- ` list item |
| `<a href="https://…">words</a>` (also `mailto:`, `tel:`, site pages, files next to the post) | `[words](https://…)` |
| `<a href="javascript:…">words</a>` | only the words |
| `<img src="https://…" alt="Logo">` | `![Logo](https://…)` |
| `<img src="cid:image001.png…" alt="Logo">` (a picture that lived inside the e-mail) | *Logo* in italics, and the run summary names `image001.png` |
| `<script>`, `<style>`, `<iframe>`, `<svg>` and the like | removed, with everything inside |
| `<table>` | only the cells' words — the table shape is lost (write a Markdown table instead) |
| `<u>under</u>` and every other tag | the words stay, the tag goes |

Checked example: `<p><b>Hello</b> GVRs, see <a href="https://www.aagrapevine.org">the site</a>.</p><script>alert(1)</script>`
becomes `**Hello** GVRs, see [the site](https://www.aagrapevine.org).` Nothing in a post can ever run on the site.

### 3.12 Complete GitHub examples

**Example 1 — the smallest post.** File `content/bulletin/2027-01-10-welcome-new-gvrs.md`:

```markdown
# Welcome, new GVRs and RLVs!

Come to our committee meeting on the third Wednesday of the month.
```

What happens: headline "Welcome, new GVRs and RLVs!", dated January 10, 2027 (from the name), language guessed
(English). On `/bulletin/#2027-01-10-welcome-new-gvrs`; machine-translated on `/es/bulletin/#2027-01-10-welcome-new-gvrs`
with an "Auto-translated" note and a "Show original" box. On the home page in full (the text is short). In What's
New, the RSS feed and the search.

**Example 2 — a pinned notice with an end date and a button.** File `2027-02-15-booth-volunteers.md`:

```markdown
---
title: "Spring Assembly: our table needs volunteers"
date: 2027-02-15
expires: 2027-03-20
pinned: true
url: https://www.neta65.org
---
We need four people for the Grapevine and La Viña table on Saturday, March 20.

Sign up at the March committee meeting, or write to grapevine@neta65.org.
```

What happens: first on `/bulletin/` — with the badge "Pinned" / "Destacado" and "until March 20, 2027" / "hasta el
20 de marzo de 2027" under the date — and first in the home page's "From the committee". A **More information** button
opens neta65.org in a new tab. What's New, the RSS feed and the digest link the headline to neta65.org (the `url:`),
not to the post. After March 20 it is gone (pages already open hide it at midnight Central).

**Example 3 — a post that waits for its day.** File `2027-02-01-spring-assembly-sign-ups.md`:

```markdown
---
title: Spring Assembly sign-ups are open
publish: 2027-02-01
expires: 2027-03-01
---
Sign up at the February committee meeting. Every GVR and RLV is welcome.
```

What happens: until January 31 the post is in no page at all — not the bulletin, the home page, What's New, the feed,
the search or the digest. Each update's run summary lists it under **Scheduled bulletin posts (not on the site yet)**:
`- 2027-02-01 — Spring Assembly sign-ups are open (content/bulletin/2027-02-01-spring-assembly-sign-ups.md)`.
On February 1 the day's first update (normally the morning refresh, by about 5:30 AM Central) puts it up, marked
"New". After March 1 it is gone. The file itself is public on GitHub from the moment you save it. A real one waits
in the folder now: `2027-01-01-new-prices-in-effect.md` goes up on January 1, 2027.

**Example 4 — your own Spanish (the real prices post, shortened).**
File `2026-10-01-prices-change-january-1-2027.md`:

```markdown
---
title: "Grapevine and La Viña prices change on January 1, 2027"
date: 2026-10-01
expires: 2026-12-31
pinned: true
lang: en
tags: prices, subscriptions, books
title_es: "Los precios de Grapevine y La Viña cambian el 1 de enero de 2027"
summary_es: |
  A partir del **1 de enero de 2027**, la suscripción anual a La Viña cuesta **$19.50** impresa o **$17.00** digital; …

  AA Grapevine anunció los nuevos precios en una carta a las oficinas intergrupales y centrales. …

  - Los precios de hoy y los nuevos, lado a lado: [Tienda: suscripciones y precios](/shop/#subscriptions)
---
From **January 1, 2027**, a yearly Grapevine subscription costs **$39.00** in print or **$34.00** digital, …

AA Grapevine announced the new prices in a letter to Intergroups and Central Offices. …

- Today's prices and the new ones, side by side: [Shop — subscriptions and prices](/shop/#subscriptions)
```

What happens: `/es/bulletin/#2026-10-01-prices-change-january-1-2027` shows the `title_es` headline and the
`summary_es` text exactly as written (paragraphs and list kept), with no "Auto-translated" note and no "Show
original" box. The `/shop/#subscriptions` link opens `/es/shop/#subscriptions` on the Spanish page. The Spanish teaser
(home card, What's New) is the first 400 characters of `summary_es` without the Markdown marks. The text is longer
than 700 characters, so the home card shows a 320-character teaser and "Read more". Pinned, so it comes first on
the bulletin, on the home page and in the digest (What's New and the feed keep their date order); shown through
December 31, 2026; in the October 2026 digest.

Rules for `summary_es` (and `summary_en`):

- It replaces the **whole** text on the other page. Write all of it.
- Write `summary_es: |`, then every line indented by two spaces; leave a blank line between paragraphs.
- It is used exactly as written: no HTML clean-up and no picture fix. For a picture write the site address,
  `![El volante](/bulletin/files/flyer.jpg)`, not `flyer.jpg`.
- Give it as many headings as the original, and each section link works on both pages.
- Set `lang:` as well, so the site cannot guess the wrong side.
- `title_es` alone does not remove the "Auto-translated" note: the text is still machine-made.
- A one-line `summary_es: Todo el texto en una línea.` becomes the whole Spanish text, on one line.

**Example 5 — a post written in Spanish.** File `2027-04-01-taller-de-escritura.md`:

```markdown
---
title: "Taller de escritura de La Viña"
lang: es
title_en: "La Viña writing workshop"
summary_en: |
  Come and write your story for La Viña. Bring paper and a pen.
---
Ven a escribir tu historia para La Viña. Trae papel y pluma.
```

What happens: `/es/bulletin/` shows the Spanish as written; `/bulletin/` shows your English, with no note. Without
`title_en` and `summary_en` the English page would show a machine translation with "Auto-translated" and a
"Show original" box.

**Example 6 — a flyer picture and a sign-up form.** Three files in `content/bulletin/`:
`2027-03-01-fall-workshop.md`, `fall-workshop.jpg` and `Sign-up form.pdf`.

```markdown
---
title: Writing workshop in the fall
image: fall-workshop.jpg
url: Sign-up form.pdf
---
![Flyer: writing workshop in the fall](fall-workshop.jpg)

Bring a story to share. [Download the sign-up form](<Sign-up form.pdf>).
```

What happens: the flyer shows inside the post. **More information** opens `/bulletin/files/Sign-up%20form.pdf` (the
same file from both pages). `image:` puts the flyer next to the item in the RSS feed. Because `url:` names a file next
to the post, What's New and the digest still link to the post itself, `/bulletin/#2027-03-01-fall-workshop`.

**Example 7 — a long post with sections.** File `2027-01-10-orientation.md`:

```markdown
---
title: Orientation for new GVRs and RLVs
date: 2027-01-10
---
Everything a new GVR or RLV needs for the first months.

# Who we are
The committee serves the groups of our Area with Grapevine and La Viña.

# What a GVR does
Brings the magazines to the home group and news back to the committee.

# How to reach us
Write to grapevine@neta65.org.
```

What happens: on a wide screen the post gets **In this post** with three links: `#2027-01-10-orientation--who-we-are`,
`…--what-a-gvr-does`, `…--how-to-reach-us`. Each section can be shared on its own. A text longer than about 700
characters shows in the digest e-mail as its first whole paragraphs, then "Details →"; on the home card, as a
320-character teaser and "Read more".

**Example 8 — send readers to another page.** File `2027-04-10-citywide.md`:

```markdown
---
title: Visit our table at CityWide Dallas
url: /events/
---
The committee hosts the Grapevine and La Viña table. Times and place are on the Events page.
```

What happens: **More information** goes to `/events/` (to `/es/events/` from the Spanish page). What's New, the feed
and the digest link to the Events page; the search still links to the post. A bulletin post is never an entry in the
calendar file — for that, add the event itself ([Flyers and events](flyers-and-events.md)).

### 3.13 Pin, schedule and expire — the exact rules (both kinds)

| | Drive file name | GitHub header | What exactly happens |
|---|---|---|---|
| Show from a day | `(from 2027-02-01)` | `publish: 2027-02-01` | Not in any page before February 1 (Central time). Goes up with the first update on February 1 — normally the morning refresh, by about 5:30 AM. Counts as "New" and as news (What's New, the feed, the digest month) from that day, whatever its date says |
| Show through a day | `(until 2027-03-01)` | `expires: 2027-03-01` | Shown all of March 1. At midnight Central, pages already open hide it; the next update removes it from the data. "until March 1, 2027" / "hasta el 1 de marzo de 2027" shows under the date |
| Both | `(from 2027-02-01) (until 2027-03-01)` | both lines | Shown February 1 through March 1. A GitHub post with `publish:` after `expires:` is reported as a mistake; a Drive name with them the wrong way round is listed as scheduled until its until-day and then dropped, without a warning |
| Pin | `(pinned)`, `(fijado)`, `📌` | `pinned: true` | First on `/bulletin/`, on the home page and in the digest, with the badge "Pinned" / "Destacado". Several pinned posts: newest first among them |
| Unpin | rename the file without the word | `pinned: false`, or delete the line | at the next update |
| Take down now | delete the file, move it out of the folder, or put `PRIVATE` in its name | delete the file (or set `expires:` to yesterday) | at the next update |

More timing facts:

- **Order:** pinned posts first, then by the post's date, newest first. A post dated ahead (for example with its
  event's day) stays at the top until a post with a later date comes.
- **"New" badge:** for 14 days from the post's date — or from the day it first appeared, when the date is more than a
  day ahead — and never before its `publish` day. A post with an old `date:` is not "New" and sits low in What's New.
- **Monthly digest:** a post is in the edition of the month it was **added** to the site (its first day on the site;
  its `publish` day if that is later), whatever its date. A post that has expired before the e-mail goes out (the
  1st–3rd of the next month) is left out. To have a notice e-mailed, let it run at least until the 3rd of the next
  month. Real example: `2027-01-01-new-prices-in-effect.md` expires January 31, so it will never be in an e-mail —
  the January edition goes out February 1–3.
- Scheduling is about timing, not secrecy (section 8).

### 3.14 Languages: automatic and by hand

**Which language is the original.** A GitHub post: `lang:` when it starts with `en` or `es`; otherwise guessed from the
headline and the text (names like "Grapevine" and "La Viña" are left out of the guess). A Drive post: guessed from the
headline and the first 600 characters of the text.

**Automatic translation.** During the update the headline, the teaser and the whole text are machine-translated into
the other language — offline, inside the GitHub job; nothing is sent to an outside service. Links, pictures and code
stay as they are; heading and list marks are kept. On the other language's page the post shows:

- an **Auto-translated** / **Traducción automática** note (also on the home card, in What's New, the RSS feed and the
  digest);
- a **Show original** / **Ver el original** box with the original headline and text.

Bulletin texts are among the first to be translated. The morning refresh allows only 5 minutes of new translations
(other runs up to 40); what does not fit waits for the next run and meanwhile shows in its original language on both
pages, without the note.

**Your own translation, GitHub post:** `title_es` + `summary_es` in a file written in English, or `title_en` +
`summary_en` in one written in Spanish — examples 4 and 5 above. Only what you leave out is machine-translated. A value
in the file's own language (`title_en` in an English file) is ignored.

**Your own translation, Drive post:** a Drive file has no header, so the Spanish goes into
[`data/translations/overrides.yml`](../data/translations/overrides.yml), one entry per piece of text. Each key must be
the original text exactly. Spaces, line breaks, capitals and accents don't matter; dashes, quote marks and the final
period do.

1. Wait until the post is on the site. Open [`data/site/announcements.json`](../data/site/announcements.json) and find
   the post (search for its headline). A post scheduled for a later day is not there yet: find it in
   `data/raw/drive.json` instead (same fields).
2. Copy three things: its `"title"`, its `"summary"` (the first 400 characters of the text as plain words, ending in
   "…" when cut) and `"extra"` → `"body_md"` (the whole text).
3. Add three entries at the end of the English → Spanish part of `overrides.yml`. For a Doc named
   `Spring Assembly sign-ups` whose text is "Sign up by March 1 at the committee meeting. / # Who can come / Every GVR
   and RLV.", that is:

   ```yaml
   "Spring Assembly sign-ups": { es: "Inscripciones para la Asamblea de Primavera" }
   "Sign up by March 1 at the committee meeting. Who can come Every GVR and RLV.": { es: "Inscríbete antes del 1 de marzo en la reunión del comité." }
   ? |-
     Sign up by March 1 at the committee meeting.

     # Who can come

     Every GVR and RLV.
   : es: |-
       Inscríbete antes del 1 de marzo en la reunión del comité.

       # Quién puede venir

       Todos los RLV y GVR.
   ```

   The whole text is a long key: `? |-`, then the English indented two spaces; `: es: |-`, then the Spanish indented
   four spaces. (All three keys were checked against what the site makes from such a Doc.)
4. Commit. A quick update runs; a few minutes later `/es/bulletin/` shows your Spanish, with no "Auto-translated" note.

If the Drive file is edited later, the changed text no longer matches, and the post goes back to the machine
translation until you update the keys. (The real Drive post has its whole text in the file twice — before and after
one sentence was changed — for that reason.) A typo in `overrides.yml` pauses all new translations; the run summary
shows it under **Settings problems**. More on overrides, the glossary of names that are never translated, and the
words of buttons: [Translations](translations.md).

**Don't write both languages in one post.** The site takes one language as the original, keeps the sentences that are
already in the other language, and translates the rest — so one page shows the same message twice. Use `summary_es`
instead, or make two posts.

**A wrong `lang:` means no translation.** An English text marked `lang: es` shows in English on both pages, with no
note. `lang: Spanish` is not understood (write `es`).

---

## 4. What happens next

```text
Google Drive: …/bulletin/<file>           GitHub: content/bulletin/<name>.md
            │                                         │
  scripts/sync/drive.py                   scripts/sync/announcements.py
  (folder, file name, text download)      (header and text)
            │                                         │
  data/raw/drive.json                     data/raw/announcements.json
            └────────────────────┬────────────────────┘
                   scripts/sync/build_data.py
     (drops expired and not-yet-due posts, translates EN ⇄ ES, sorts)
                                 │
                   data/site/announcements.json
                                 │
           Eleventy builds the pages  ─►  GitHub Pages (the live site)
```

| You did… | What picks it up | Live roughly |
|---|---|---|
| Saved, changed or deleted a file in `content/bulletin/` (a picture too; not its `README.md`) on github.com | **Website update** starts by itself, as a quick run: Drive, the bulletin, the podcasts, the writers archive files and the daily quote, then the build | a few minutes (a page may take up to about 10 more minutes to show it everywhere). Runs never overlap: if another update is busy (the full daily run can take a couple of hours), yours waits its turn |
| Added, renamed, edited or deleted a file in the Drive bulletin folder | Nothing starts at upload time. The next update reads Drive: the **morning refresh** (started by the Morning check; by about 5:30 AM Central when the morning alarm is set up), the **nightly full update**, the **midday refresh** and the **evening refresh** (GitHub's own schedules — set 4 hours early on purpose, because GitHub starts them late; in practice the full update runs in the early morning, the refreshes around midday and in the evening, Central time), or any run started by a push | the next refresh: the same day when uploaded in the morning or afternoon, else the next morning |
| Want a Drive change on the site now | GitHub → **Actions** → **Website update** → **Run workflow** → tick *Quick refresh only: Google Drive, the bulletin, podcasts, the daily quote and the writers archive* (the `skip_crawl` option) → **Run workflow** | a few minutes |
| A `publish:` / `(from …)` day comes | the first update of that day (Central time) | normally the morning refresh, by about 5:30 AM Central |
| An `expires:` / `(until …)` day ends | pages already open hide the post at midnight Central; the next update removes it | midnight Central |
| Fixed a translation in `overrides.yml` | **Website update** starts by itself, as a quick run | a few minutes |

Two Drive details:

- A doc's text is downloaded again only when Drive shows a new "last modified" time for it, and at most 40 changed
  docs are downloaded per run (the rest follow at the next run). A download that fails keeps the previous text.
- The file must be readable by "anyone with the link" — it normally inherits that from the folder. Otherwise Drive
  answers with a sign-in page and the post has no text.

**Who can do what.** The owner's GitHub login (MKP715) has write access. That is enough to edit `content/bulletin/`,
`data/translations/overrides.yml` and `config/site.yml`, and to press **Run workflow**. Repository settings and secrets —
the optional `GOOGLE_API_KEY` for exact Drive dates, the e-mail secrets of the monthly digest — need the NETA65 admin
account. Uploading to the Drive folder needs edit access to it (ask grapevine@neta65.org).

Every workflow, the run summary and manual runs in detail: [Automation and troubleshooting](automation-and-troubleshooting.md).

---

## 5. Where it shows on the website

### 5.1 Every place

All addresses below are under `https://neta65.github.io/aagrapevine/`.

| Place | English · Spanish | What shows |
|---|---|---|
| Bulletin page | `/bulletin/` · `/es/bulletin/` | Every live post: pinned first, then newest. Each one has the badges "Pinned" and "New", the date ("Sunday, January 10, 2027" / "Domingo, 10 de enero de 2027"), "until …" when it expires, the headline (a link to the post itself), the whole text, **In this post** (2+ top-level headings, wide screens), the button **More information** or **Open the document**, the "Auto-translated" note, **Copy link** and **Share**. A machine-translated post also gets **Show original**. With no posts: "Nothing on the bulletin right now" |
| One post | `/bulletin/#<anchor>` · `/es/bulletin/#<anchor>` | GitHub post: the file name, e.g. `#2026-10-01-prices-change-january-1-2027`. Drive post: `#ann-drive-<file id>` (in small letters, `-` for `_`). The same anchor in both languages; the language switch keeps it |
| Home page | `/` · `/es/` — "From the committee" / "Noticias del comité" | The first 2 posts (pinned first). A text of up to 700 characters is shown in full; a longer one as a 320-character teaser with **Read more**. No posts: the section is left out |
| What's New | `/whats-new/` · `/es/whats-new/` (filter "Bulletin") | Headline and a two-line teaser, at the post's news date (see 3.13). Where the link goes: 5.2 |
| RSS feed | `/feed.xml` · `/es/feed.xml` | Headline, teaser, "NETA 65 · Bulletin", "Auto-translated" when machine-made, and a picture (`image:`, or a Drive PDF's or picture's thumbnail). The newest 100 What's New entries |
| Search | `/search/` · `/es/search/` | Headline (in both languages), a 170-character snippet, a link to the post on `/bulletin/` |
| Monthly digest page | `/digest/` · `/es/digest/` | The bulletin comes first: the posts added that month, pinned first, 5 of them and then "N more" |
| Monthly digest e-mail | sent the 1st–3rd of the month, when the e-mail is switched on | In both halves (English and Spanish) the bulletin comes first, pinned posts first: each headline as a link, the first whole paragraphs up to about 700 characters, then "Details →" when the text was cut. At most 5 posts, then "and N more on the website →". Pictures become links. How it is sent: [E-mail and alerts](email-and-alerts.md) |
| Monthly toolkit | the current month's page, e.g. `/monthly/2026-10/` · `/es/monthly/2026-10/` | In "Keep up all month": a Bulletin row with the number of live posts and a link to the newest |
| Committee decks | a `bulletin` slide ([Presentations](presentations.md)) | The 3 newest posts, with English headlines |
| Booth display | `/about/#booth` · `/es/about/#booth` | The 2 newest posts (pinned first), each a slide of its own: the headline and the first paragraph (a `summary:` written by hand instead), at most 280 characters, in each language, with a QR code to the post on `/bulletin/`; gone after its last day (`expires:` / `(until …)`). A post that says a word the booth never shows ("PDF", "donate", "buy now" …) is left out and the next one takes its place ([Booth display](booth.md)) |
| Committee menu | the sub-menu on the Committee pages | "Bulletin" with the number of live posts |
| Old address | `/announcements/` · `/es/announcements/` | forwards to `/bulletin/`, keeping the `#anchor` |
| Status | `/status/` · `/es/status/` | Row "Bulletin (content/bulletin)": OK or not, last update, the number of posts in `content/bulletin/` (scheduled and expired ones included). Drive posts are counted in the "Google Drive" row. No per-file problems here (section 7) |

Not used for posts: the events calendar file (`/events.ics`), the Portfolio and the Library (a file in the Drive
bulletin folder is never listed there), and the sitemap.

### 5.2 Which link goes where

| Kind of post | Home "Read more" | What's New, RSS feed, digest page and e-mail | Search | Copy link and Share |
|---|---|---|---|---|
| GitHub post | the post (`/bulletin/#<anchor>`) | the post (`/es/bulletin/#…` from Spanish pages) | the post | the post |
| GitHub post with `url: https://…` | `/bulletin/` (top of the page) | **that web page** | the post | the post |
| GitHub post with `url: /events/` | `/bulletin/` (top) | `/events/` (`/es/events/`) | the post | the post |
| GitHub post whose `url:` is a file next to it | the post | the post | the post | the post |
| Drive post | `/bulletin/` (top) | **the file on Google Drive** (new tab) | the post | the post |

> **Note.** What's New, the RSS feed and the digest send readers of a Drive post to the Drive file, not to the
> bulletin: in the data, a Drive post's own address is the Drive file. For a `.md` or `.txt` file, Drive then shows the
> raw text. Recipe 6.5 changes that.

---

## 6. Going further: change the code

Where everything lives (search for the name in the right-hand column; line numbers change, names don't):

| What | File | Look for |
|---|---|---|
| Drive folder names for the bulletin | `scripts/sync/drive.py` | `CATEGORY_SYNONYMS`, key `"announcements"` |
| The name switches pinned / until / from | `scripts/sync/drive.py` | `_PINNED`, `_UNTIL`, `_FROM`, used in `build_item` |
| Headline and date from a Drive name | `scripts/sync/drive.py`, `scripts/sync/common.py` | `# ---- title / date from the file name` in `build_item`; `tidy`; `date_from_text` |
| Which Drive files have text; download; clean-up | `scripts/sync/drive.py` | `body_url`, `fetch_body`, `docx_to_text`, `normalize_body`, `fill_announcements`, `MAX_BODY_CHARS` |
| GitHub posts: header, headline, HTML, pictures, own translation | `scripts/sync/announcements.py` | `parse_announcement`, `read_front_matter`, `title_from_body`, `tidy_html`, `link_attachments`, `own_translations`, `ATTACH_EXT` |
| Expired and scheduled posts, the order | `scripts/sync/build_data.py` | `build_announcements`, `SCHEDULED_MAX` |
| "New" badge, What's New timing | `scripts/sync/build_data.py` | `effective_ts`, `is_new`, `NEW_DAYS`, `plan_whatsnew` |
| Which fields get translated | `scripts/sync/build_data.py` | `text_fields`, `own_words`, `def apply` (class `I18n`) |
| The Bulletin page | `src/pages/bulletin.njk` | `cm-ann`, `committee.ann.more_info` |
| Home cards | `src/pages/index.njk`, `eleventy/filters/home.js` | `homeAnnouncements`, `body.length <= 700` |
| The page's list and anchors | `eleventy/filters/committee.js` | `announcementList`, `itemAnchor`, `RESERVED_IDS` |
| How Markdown is shown | `eleventy.config.js` | `markdownIt({ html: false, linkify: true, breaks: true })`, `mdHeadingPlan`, `mdToc` |
| What's New and RSS | `src/pages/whats-new.njk`, `src/pages/feed.11ty.js`, `eleventy/filters/community.js` | `hrefOf` |
| Search | `eleventy/filters/library.js` | `the bulletin's posts` |
| Digest page and e-mail | `eleventy/filters/community.js`, `src/pages/digest.njk`, `scripts/notify/send_digest.py` | `monthNews`; `month_news`, `post_when`, `md_excerpt` |
| Words on the pages | `src/_i18n/committee.json`, `src/_i18n/home.json`, `src/_i18n/common.json` | `committee.ann.`, `home.ann_`, `home.pinned`, `nav.bulletin` |
| Run summary lists | `.github/workflows/update.yml` | `Bulletin files to fix`, `Scheduled bulletin posts` |

What the site stores for a post (real data, shortened) — `data/site/announcements.json`:

```json
{ "id": "ann:2026-10-01-prices-change-january-1-2027", "source": "committee", "kind": "announcement",
  "url": "/bulletin/#2026-10-01-prices-change-january-1-2027",
  "title": "Grapevine and La Viña prices change on January 1, 2027", "summary": "From January 1, 2027, …",
  "lang": "en", "date": "2026-10-01", "first_seen": "2026-10-02T04:55:24Z", "image": null,
  "extra": { "body_md": "From **January 1, 2027**, …", "expires": "2026-12-31", "pinned": true,
             "slug": "2026-10-01-prices-change-january-1-2027", "link": null,
             "file": "content/bulletin/2026-10-01-prices-change-january-1-2027.md", "own_i18n": { "…": "…" } },
  "i18n": { "title": { "en": "…", "es": "…" }, "summary": { "en": "…", "es": "…" }, "body_md": { "en": "…", "es": "…" } },
  "machine": [], "is_new": true }
```

A Drive post has the same shape, with `"source": "drive"`, `"id": "drive:<file id>"`, `"url"` = the Drive file, and
Drive fields in `extra` (`name`, `file_type`, `mime`, `view_url`, `modified_text` …). Every key in `extra` passes
unchanged from the sync scripts to the site data, so a new field needs no change in between.

**Tests.** Run them before and after a change, from the repository folder on a PC:

```bash
python -m unittest discover -s tests                         # all tests
python -m unittest discover -s tests -p "test_bulletin*.py"   # only the bulletin tests
```

The bulletin's own tests are `tests/test_bulletin.py` and `tests/test_bulletin_publish.py`; `test_digest_parity.py`,
`test_send_digest.py`, `test_home.py`, `test_app_expire.py`, `test_translate.py` and `test_sync_pipeline.py` touch it
too. Some tests run small JavaScript checks with Node.js. On GitHub, the **Code check (tests and test build)**
workflow runs all tests after every push that changes code, templates, settings or content — a red ✗ there means the
change broke something.

### 6.1 Recipe: accept "(destacado)" as a pin word

The site's Spanish badge says "Destacado", so a Spanish speaker may well type `(destacado)` — today that word just stays
in the headline. In `scripts/sync/drive.py`, find `_PINNED = re.compile(` and add the word:

```python
_PINNED = re.compile(r"(?i)\s*[\[(](pinned|fijado|fijo|pin|destacado)[\])]\s*|📌")
```

Add a test to `tests/test_bulletin_publish.py`, class `DriveNames` (it has an `item()` helper that builds a Drive post
from a name):

```python
    def test_destacado_pins(self):
        it = self.item("Aviso importante (destacado)")
        self.assertEqual((it["title"], it["extra"]["pinned"]), ("Aviso importante", True))
```

Then add the word where people read the rules: `README.md` (section 2, "The Bulletin"), `content/bulletin/README.md`,
and the notes at the top of `drive.py`. (The same pattern also tidies the names of other Drive files, such as flyers.)

### 6.2 Recipe: accept another Drive folder name

Say the committee wants a folder called `Notices`. In `scripts/sync/drive.py`, `CATEGORY_SYNONYMS`, add the words to
the `"announcements"` list — small letters, no accents:

```python
    "announcements": ["bulletin", "bulletins", "bulletin board", "boletin", "boletines", "announcement",
                      "announcements", "anuncio", "anuncios", "aviso", "avisos", "news", "noticias",
                      "notice", "notices"],
```

A Spanish word also goes into `_SPANISH_HINTS` just below, so posts in that folder lean Spanish. Test: add
`"Notices"` to the names in `test_drive_folder_names` in `tests/test_bulletin.py`. Check that the word is not already
used by another category in the same list.

### 6.3 Recipe: a new header line — `button:` for the button's words

1. **Read it** — `scripts/sync/announcements.py`, `parse_announcement`, right after the block that starts
   `link = clean_text(meta.get("url")`:

   ```python
       button = clean_text(meta.get("button")) or None
   ```

   and below the `extra = {"body_md": body, …, "link": link}` lines:

   ```python
       if button:
           extra["button"] = button        # the words on the "More information" button
   ```

2. **Translate it** (optional) — `scripts/sync/build_data.py`, function `text_fields`, before `return fields`:

   ```python
       if kind == "announcement" and clean_text(ex.get("button")):
           fields.append(("button", clean_text(ex.get("button")), False, None))
   ```

   (For a hand-written `button_es`, extend `own_translations` in `announcements.py` the way it reads `title_es`.)

3. **Show it** — `src/pages/bulletin.njk`, in the line that contains `committee.ann.more_info`, replace
   `{{ ("committee.ann.open_doc" if isDoc else "committee.ann.more_info") | t(lang) }}` with:

   ```njk
   {{ (a | tx("button", lang)) if (a.extra.button and not isDoc) else (("committee.ann.open_doc" if isDoc else "committee.ann.more_info") | t(lang)) }}
   ```

   (`tx` takes the page language's version from the translations, else the words as written.)

4. **Test it** — `tests/test_bulletin.py`; the `Folder` class gives you a temporary bulletin folder and `self.parse()`:

   ```python
   class ButtonWords(Folder):
       def test_button_line(self):
           it = self.parse("b.md", "---\ntitle: T\nurl: https://www.neta65.org\nbutton: Sign up\n---\nText")
           self.assertEqual(it["extra"]["button"], "Sign up")
   ```

5. **Document it** in `content/bulletin/README.md`, `content/bulletin/_example.md` and `docs/DATA_SCHEMA.md`.

### 6.4 Recipe: show `image:` on the bulletin card

In `src/pages/bulletin.njk`, right after the `</h2>` that closes the post's headline (search `cm-anchor-link`):

```njk
{%- if a.image %}
<img src="{{ a.image }}" alt="" loading="lazy" decoding="async" class="mt-4 max-h-80 w-auto rounded-lg">
{%- endif %}
```

`a.image` is `/bulletin/files/<name>` for a file next to the post (the build adds the site's `/aagrapevine` prefix by
itself), a web address, or — for a Drive PDF or picture post — its Drive thumbnail. Do the same in the home card in
`src/pages/index.njk` (inside `<article class="home-ann`) if you want. Keep `alt=""` only when the text says what the
picture says; otherwise describe the picture.

### 6.5 Recipe: make Drive posts link to the bulletin (What's New, RSS, digest)

1. `scripts/sync/build_data.py`, `build_announcements`: in the loop, just before `kept.append(it)`:

   ```python
           if it.get("source") == "drive":
               # the post on /bulletin/ — the same anchor eleventy/filters/committee.js announcementList gives it
               it["url"] = "/bulletin/#ann-" + slugify(it["id"], 70).rstrip("-")
   ```

2. `src/pages/bulletin.njk`: the **Open the document** button reads `a.url`. In the line that starts `{%- set more =`,
   change both `a.url` to `a.extra.view_url` (the Drive address stays there).
3. Update the test that reads that line: in `tests/test_bulletin.py`, `test_a_plain_text_drive_post_has_no_open_the_document`
   looks for the old text `(a.url if (a.source == "drive" and a.url and not plainText) else "")` — change it to the
   new line, or the test fails. Then run the tests (`tests/test_digest_parity.py` checks that the e-mail and the digest
   page still agree).

The home card's **Read more** then goes to the post as well (it follows any `url` that starts with `/bulletin/`).

### 6.6 Recipe: keep line breaks from Word files

In `scripts/sync/drive.py`, `docx_to_text`, the break and the tab are put outside the text, which is read only from
inside `<w:t>` elements. Replace

```python
        p = re.sub(r"<w:tab/>", "\t", p)
        p = re.sub(r"<w:br[^>]*/>", "\n", p)
```

with

```python
        p = re.sub(r"<w:tab/>", "<w:t>\t</w:t>", p)
        p = re.sub(r"<w:br[^>]*/>", "<w:t>\n</w:t>", p)
```

Checked on a sample: "Line one" + Shift+Enter + "Line two" then gives `Line one` / `Line two`. A post's text is read
again only when its Word file changes on Drive. To read another type as text (`.odt`, `.rtf`), add it in `body_url` and
give `fetch_body` a reader like `docx_to_text`.

### 6.7 Change a limit

| Limit | File | Look for |
|---|---|---|
| Drive text: 12,000 characters | `scripts/sync/drive.py` | `MAX_BODY_CHARS` |
| Drive downloads per run: 40 | `scripts/sync/drive.py` | `MAX_ANNOUNCEMENT_FETCHES` |
| Teaser: 400 characters | `scripts/sync/announcements.py` (`parse_announcement`, `own_translations`), `scripts/sync/drive.py` (`fill_announcements`) | `truncate(summary, 400)`, the `400` in `own_translations`, `truncate(plain, 400)` |
| Home page: 2 posts | `src/pages/index.njk` | `homeAnnouncements) \| limit(2)` |
| Home page: full text up to 700 characters, else a 320-character teaser | `src/pages/index.njk` | `body.length <= 700`, `excerpt(320)` |
| "New" badge: 14 days | `scripts/sync/build_data.py` | `NEW_DAYS` |
| What's New teaser: 220 characters | `src/pages/whats-new.njk` | `excerpt(220)` |
| Share text: 140 characters | `src/pages/bulletin.njk` | `excerpt(140)` |
| Digest: 5 posts per section | `config/site.yml` | `digest:` → `per_section` |
| Digest e-mail text: about 700 characters (600 in the plain-text part) | `scripts/notify/send_digest.py` | `md_excerpt(text, 700)`, and the `600` in `render_text` |
| Scheduled posts listed: 20 | `scripts/sync/build_data.py` | `SCHEDULED_MAX` |

### 6.8 Change the words on the page

Each entry has an `"en"` and an `"es"` value; change both and keep placeholders such as `{date}` and `{panel}` in both.

| Words | Key |
|---|---|
| Pinned / Destacado (Bulletin page) | `committee.ann.pinned` |
| until {date} / hasta el {date} | `committee.ann.until` |
| Show original / Ver el original | `committee.ann.show_original` |
| In this post / En esta publicación | `committee.ann.in_post` |
| More information · Open the document | `committee.ann.more_info` · `committee.ann.open_doc` |
| Nothing on the bulletin right now (and its text) | `committee.ann.empty_title`, `committee.ann.empty_text` |
| The four steps in *Post to the bulletin*, and the example name | `committee.ann.how_1` … `committee.ann.how_4`, `committee.ann.example_name` |
| Home: "From the committee", its subtitle, "Read the bulletin", "Pinned" | `home.ann_title`, `home.ann_sub`, `home.ann_all`, `home.pinned` |
| The menu's "Bulletin" / "Boletín" | `nav.bulletin` |
| The e-mail's "Bulletin" and "Details" | the `T` table in `scripts/notify/send_digest.py` (keys `"announcement"`, `"details"`) — separate from the site's words |

More: [Translations](translations.md).

### 6.9 Change the order or the expiry rule

The rule is written in several places that must agree:

- `scripts/sync/build_data.py`, `build_announcements` — the data;
- `eleventy/filters/committee.js`, `announcementList` — the Bulletin page, the search, the decks, the toolkit;
- `eleventy/filters/home.js`, `homeAnnouncements` — the home page;
- `eleventy/filters/community.js`, `monthNews`, and `scripts/notify/send_digest.py`, `month_news` — the digest page and
  e-mail (`tests/test_digest_parity.py` keeps the two equal);
- `data-gv-expire` in `src/pages/bulletin.njk` and `src/pages/index.njk`, with `GV.expire` in `src/assets/js/app.js` —
  hiding at midnight in the browser.

The picture and document types of GitHub posts are listed twice, too: `ATTACH_EXT` in `scripts/sync/announcements.py`
and the copy rule in `eleventy.config.js` (search `bulletin/files`). Keep both lists the same.

---

## 7. Troubleshooting

**Where problems are reported:**

1. **GitHub → Actions → the latest "Website update" run → Summary.** Look for **Bulletin files to fix** (GitHub posts
   that could not be read, missing pictures, ignored files — up to 10 lines), **Scheduled bulletin posts**,
   **Settings problems** (for example a typo in `overrides.yml`) and the **Content sources** table (the Drive row says
   OK or PROBLEM). The run's annotations repeat each problem line as a yellow warning, plus one short notice that
   names the first scheduled day.
2. **The run's log**, step "Sync sources and translate", for Drive text downloads: `announcement '…': could not
   download text (403)` or `Drive returned an HTML page instead of the file`.
3. **`/status/`**: only OK or not, counts and the last update, for "Bulletin (content/bulletin)" and the Google Drive row.
4. **The data files**: `data/site/announcements.json` (every live post, exactly as the site uses it),
   `data/site/status.json` (`scheduled`, and each source's `stats.errors`), `data/raw/drive.json` (Drive posts,
   scheduled ones included, and `stats.announcements`: fetched, reused, file_only, deferred, failed).

> **Note.** Comments in `announcements.py` say problems are "listed on /status/". Today the `/status/` page shows only
> counts; the list of files to fix is in the Actions run summary (and in `data/site/status.json`).

| Symptom | Likely cause | Fix |
|---|---|---|
| A Drive doc does not show up at all | No update has run since the upload (an upload starts nothing) | Wait for the morning, or **Run workflow** with *Quick refresh only* (`skip_crawl`) ticked |
| | It is not in the Panel folder's bulletin folder (for example in `A65_GV › bulletin`, or in a folder called `Newsletter` or `Notices`) | Move it to `A65_GV › 2027-2028_Panel77_GVLV › bulletin` |
| | Its name holds `(from …)` with a later day | It goes up that day; the run summary lists it under Scheduled bulletin posts |
| | Its `(until …)` day has passed | Rename it with a later date, or without the switch |
| | Its name contains `PRIVATE`, `PRIVADO`, `(Responses)`, `(Respuestas)` or `wrong size`, or it is a spreadsheet | Rename it, or use a Doc |
| | The Drive folder could not be read | The Drive row on `/status/` and in the run summary says so; check the folder is shared "Anyone with the link — Viewer" ([The Drive panel folder](drive-panel-folder.md)) |
| The post shows only its headline | It is a PDF, picture, `.doc`, `.odt` or `.rtf` — no text is read from those | Use a Google Doc, `.md`, `.txt` or `.docx`; link a PDF by its full Drive address inside the text |
| | The file is not open to "anyone with the link" (Drive sent a sign-in page) | Fix the file's sharing; the run log says "Drive returned an HTML page instead of the file" |
| An edit to a Drive doc does not show | The text is fetched again only when Drive's "last modified" changes, at most 40 docs per run | Wait for the next update, or start one |
| The headline still shows `(until Feb 1)`, and the post never comes down | No year, so it is not a date | Write `(until 2027-02-01)` |
| The post came down on the wrong day | `(until 01/02/2027)` means January 2 (month first; *Notes* says "could be January 2 or February 1"); `(until March 2027)` means March 1 | Write `YYYY-MM-DD` |
| A scheduled post is not there on its day | It goes up with that day's first update (by about 5:30 AM Central) | Is it still under Scheduled bulletin posts? Then its day has not come in Central time. A Drive name whose `(until …)` is before its `(from …)` never shows, without a warning |
| A GitHub post does not show up | The file has a mistake | Run summary → **Bulletin files to fix** names it, e.g. `the header has no closing --- line …` |
| | Its name starts with `_` or `README`, or does not end in `.md` | Rename it (`_draft.md` → `2027-01-10-welcome.md`) |
| | `publish:` is still ahead, or `expires:` has passed | Check the dates |
| | Another update was running, so yours waits | See the Actions tab |
| My change to a GitHub post does not show | The changed file has a mistake: the last good version stays until it is fixed | Run summary → Bulletin files to fix |
| The headline is "True" or "False" | `title: Yes` or `On` gives "True"; `No` or `Off` gives "False" | Put it in quotes: `title: "Yes"` |
| The headline is a heading from the text, or the file name | `title: #1 …` — everything after `#` is a note | `title: "#1 …"` |
| The headline is "Welcome new gvrs" in small letters | No `title:` and no heading, so the file name was used | Add `title:` or start the text with `# ` |
| A picture shows only its description, in italics | The file is not next to the post, or its name differs (a name with spaces needs `< >`) | Upload it to `content/bulletin/` with exactly that name; the run summary names the missing file |
| A picture in a Drive `.md` is broken | Drive posts can't use files next to them | Use the full `https://` address of a public picture, or post on GitHub |
| A Drive `.md` starts with a line and a heading "title: …" | Drive posts don't read a header | Delete the header lines (the file name is the headline), or post on GitHub |
| `<b>` and other tags show as text | A Drive post is not cleaned of HTML | Write Markdown (`**bold**`) |
| Words run together in a Word post | Shift+Enter breaks are lost in `.docx` | Press Enter for a new paragraph, use a Google Doc, or recipe 6.6 |
| The headline ends in ".markdown" | `.markdown` is not removed from Drive names | Rename the file to `.md` |
| An undated Drive post jumps to the top with a new date | Without a date in its name, a post is dated with Drive's "last modified" day | Start the name with `YYYY-MM-DD` |
| `www.example.org` in the text is not a link | Only addresses with `https://` become links | Write `https://www.example.org` |
| Both pages show the same language (a Drive post) | The language guess went wrong (a very short text, or mostly names) | Start with a full sentence in the post's language, or post on GitHub with `lang:` |
| The Spanish page shows the English text, with no note | The translation has not run yet (the morning refresh has 5 minutes), or `lang:` is wrong | Wait for the next update; set `lang: en` / `es` correctly |
| The Spanish page shows a paragraph twice | Both languages in one post | One language per post; add the other with `summary_es` |
| "Auto-translated" stays although I wrote `title_es` | The text is still machine-made | Add `summary_es` (the whole Spanish text) |
| My `overrides.yml` translation of a Drive post stopped working | The doc was edited, so the old keys no longer match | Copy the new title, summary and text from `data/site/announcements.json` into the keys |
| New translations stopped everywhere | A typo in `overrides.yml` | Run summary → **Settings problems**; fix the line |
| What's New, the feed or the e-mail opens Google Drive | That is where Drive posts link today | Post on GitHub, or recipe 6.5 |
| A post is missing from the monthly e-mail | It expired before the e-mail went out (1st–3rd), it was added in another month, there were more than 5 posts ("N more"), or the e-mail is not switched on | See 3.13, and [E-mail and alerts](email-and-alerts.md) |
| A shared link to a post does not jump to it | The GitHub file was renamed (new anchor), or its name is reserved (or starts with `month-`, `docs-`, `cm-`) | Don't rename a file once shared; avoid names like `how-to-post`, `subscribe`, `main`, `item` |
| `duplicate name` in the run summary | Two files give the same name (`Spring.MD` and `spring.markdown`), or two long names share their first 80 characters | Rename one of them |
| `ignored — only files ending in .md are read` | A `.txt` or `.docx` file in `content/bulletin/` | Rename it to `.md` (or put the Word file on Drive) |

---

## 8. Good practice and AA principles

- **Anonymity.** No full names: use a service title ("the Chair", "the GVR coordinator") or a first name at most. No
  personal phone numbers or e-mail addresses — use grapevine@neta65.org. No picture in which an AA member's face can
  be recognized.
- **Attraction rather than promotion.** Share facts and invitations: what, when, where, how to take part. No hard
  sell and no outside causes. For prices and orders, link to the official pages (aagrapevine.org, aalavina.org) and the
  site's own Shop page (`/shop/`).
- **Everything is public — even before its day.** The Drive folder is open to anyone with the link. A scheduled Drive
  doc's headline and whole text are in `data/raw/drive.json` in the public GitHub repository from the first update.
  Every file in `content/bulletin/` — `_draft…` files and every picture and PDF included — is public the moment it is
  saved. There is no draft mode in the Drive bulletin folder: `(draft)` in a name is just a word, and the post goes
  live. Write drafts outside A65_GV and outside the repository.
- **Put the message in the first sentence.** The home card, What's New (two lines), Share (140 characters) and the
  e-mail (about 700 characters) show only the beginning, and a list at the start runs together into one line in a
  teaser.
- **Date every post.** Start each Drive name with `YYYY-MM-DD`. An undated doc takes a new date whenever it is edited.
- **Let time-bound notices expire** — but if a notice should go out in the monthly e-mail, let it run at least until
  the 3rd of the next month.
- **Pin sparingly.** The home page shows only 2 posts; one or two pinned posts is plenty.
- **One language per post**, and add the other by hand when the wording matters (`title_es` + `summary_es`, or
  `overrides.yml` for a Drive post).
- **Keep files small:** a flyer photo under 1 MB.

---

## 9. See also

- [How-to index](README.md)
- [The Drive panel folder](drive-panel-folder.md) — folder names, sharing, what is never published
- [File types](file-types.md) — what every kind of file becomes in every folder
- [Flyers and events](flyers-and-events.md) — events and the calendar (bulletin posts are not in the calendar)
- [Photos, slides and reports](photos-slides-reports.md)
- [Translations](translations.md) — `overrides.yml`, the glossary, the words on the pages
- [E-mail and alerts](email-and-alerts.md) — the monthly digest e-mail and its secrets
- [Settings](settings.md) — `config/site.yml` (`digest:`, `drive:`)
- [Presentations](presentations.md) — the `bulletin` slide
- [Pages and code](pages-and-code.md) — every page and template
- [Automation and troubleshooting](automation-and-troubleshooting.md) — workflows, manual runs, the run summary
- [Booth display](booth.md)
- [Automatic sources](automatic-sources.md)
- Repository files: [content/bulletin/README.md](../content/bulletin/README.md),
  [content/bulletin/_example.md](../content/bulletin/_example.md),
  [scripts/sync/announcements.py](../scripts/sync/announcements.py), [scripts/sync/drive.py](../scripts/sync/drive.py),
  [scripts/sync/build_data.py](../scripts/sync/build_data.py), [src/pages/bulletin.njk](../src/pages/bulletin.njk),
  [src/pages/index.njk](../src/pages/index.njk), [data/translations/overrides.yml](../data/translations/overrides.yml),
  and [README.md](../README.md) (sections 2 and 6).
