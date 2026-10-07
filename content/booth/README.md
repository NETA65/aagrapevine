# The booth display's rows — `booth.csv`

`content/booth/booth.csv` is the committee's own part of the **booth display**, the show that plays by itself at our
Grapevine / La Viña table at assemblies and events (About page → **Booth display**). Each row is one slide: a quiz,
a true-or-false, a fact, a quote, a moment of history, a fill-in-the-blank, a scrambled word, a poll, a question to
talk about, a message, a QR code, or an official video, podcast episode or picture from the web.

The file holds the committee's fact-checked rows (October 2026: 247 rows — 55 quizzes, 25 true-or-false, 12
fill-in-the-blank, 13 scrambles, 35 facts, 16 moments of history, 15 quotes, 14 polls, 13 talking points, 11
messages, 10 QR codes, 24 official videos and 4 podcast episodes; one video is switched off until someone has
watched it, its `notes` say why). Add, change or switch off rows as you like: the check below keeps every row
complete and in line with AA's principles.

The show adds, by itself: the photos, videos and notes of the Drive panel folder's `booth\` folder (named as in
[The Drive booth folder](#the-drive-booth-folder) below), and the site's own news of the day (the next events and
assembly, both daily quotes, the official channel's short videos, the newest podcast episodes, story themes and
deadlines, prices, the Books of the Month, the meetings anyone can join, the bulletin's newest posts). The full
guide — the player's settings, using it at a table, what to do when something does not show — is
[how-to/booth.md](../../how-to/booth.md).

## Editing it, and when it shows

* **On github.com:** open the file, the pencil icon, edit, **Commit changes**. Or download it, edit it in **Excel**
  (or Google Sheets / LibreOffice) and save it as **CSV UTF-8** (Excel: *File → Save As → CSV UTF-8 (Comma
  delimited)*), then upload it in place of the old one. Plain "CSV" in Excel loses ñ and é.
* Excel may turn dates into `3/1/2027`: format the `from` and `until` columns as **Text** and write `2027-03-01`.
* After the commit, the site rebuilds itself in **about 3 minutes** (a page may take up to about 10 more minutes to
  show it everywhere); a booth that is running picks up the new rows within half an hour, at the next slide.
* **The check:** every commit runs the workflow *Code check (tests and test build)* (GitHub → Actions). A red ✗
  names the row and the mistake — `booth.csv row 14 (quiz-12): correct "4": there are only 3 choices`. A row with a
  mistake is left out of the show (the rest plays), and the player lists it under *Settings → Slides*. *Website
  update* still publishes the file: it leaves the test of this file to the Code check (it tests the code, not your
  files), so only the Code check goes red — fix a mistake soon. On a computer:
  `python tests/test_booth_csv.py content/booth/booth.csv` prints the same lines.

## The rows

The first row is the header. Columns can be in any order and any capitalization; a column the booth does not know is
ignored (so you can add your own). **Blank rows are skipped, and so is a row whose `id` starts with `#`** — use that
for a draft or a note. Put a cell in double quotes when it holds a comma or a line break (Excel does it for you);
a double quote inside is written twice: `"He said ""hi"""`.

| column | for | what to write |
|---|---|---|
| `id` | every row (needed) | a unique name: a–z, 0–9 and dashes, up to 48 characters (`quiz-first-issue`). Keep it once chosen: the booths remember the rows someone switched off by their id |
| `on` | every row | `yes` (also blank) or `no` — a quick switch. A row that is off is still checked |
| `type` | every row (needed) | quiz, truefalse, fact, quote, history, fill, scramble, poll, prompt, message, qr, video, audio, image (see [The types](#the-types)) |
| `pub` | every row | `gv`, `lv` or `both` (blank = both): the slide's colour (Grapevine blue, La Viña amber, both grape) and the magazine filter |
| `tags` | every row | words separated by spaces, `;` or `,` (history, writing, service, gvr, rlv, traditions, newcomer, app, podcast, books, prices …) — a booth can hide a tag. Settings list the tags as topics in the page's language: a NEW tag needs its two words in `src/_i18n/booth.json` (`booth.tag.<tag>`, dashes as underscores) and its name in the `pageKeys` list of `src/_includes/macros/booth.njk` (`tests/test_booth_page.py` says which is missing) |
| `weight` | every row | 0.5 to 5 (blank = 1): how often the row comes up, beside the others |
| `from`, `until` | every row | `YYYY-MM-DD`, a year from 2000 to 2099, Central time, both days included: only show it in that window |
| `seconds` | every row | 4 to 180: time on screen (blank: worked out from the type and the length) |
| `reveal` | quiz, truefalse, fill, scramble | 4 to 60: seconds before the answer shows (blank: the booth's setting, 12) |
| `title_en`, `title_es` | message, qr, history (the WHEN: `June 1947`), video, audio, image, fact | a heading, up to 80 characters |
| `text_en`, `text_es` | every type (a caption on video, audio, image) | the question, statement, fact, quote, message or talking point — up to 300 characters (a quiz, true-or-false or fill question: 180). `{event}` = the event's name set on the booth ("this event" while none is set), `{committee}` = our committee's name, `{site}` = the site's address |
| `choices_en`, `choices_es` | quiz, poll | 2 to 6 choices separated by `|`, up to 70 characters each, the same number and order in both languages |
| `correct` | quiz, truefalse | quiz: the right choice's number (1–6) or letter (A–F); truefalse: `true` / `false` (also yes/no, verdadero/falso, cierto, sí) |
| `answer_en`, `answer_es` | fill, scramble | the missing word(s); the word to unscramble (letters and spaces, 3 to 16 letters) |
| `explain_en`, `explain_es` | quiz, truefalse, fill, scramble, poll | one or two sentences shown with the answer, up to 240 characters |
| `credit_en`, `credit_es` | quote (needed), fact, history, quiz, video, audio, image | the credit line or source note in small type, up to 200 characters |
| `media_url` | video, audio, image (needed) | a YouTube link (watch, youtu.be, shorts, embed — `?t=1m30s` starts it there), or an https `.mp4` / `.webm` video, `.mp3` / `.m4a` / `.ogg` sound, `.jpg` / `.png` / `.webp` picture |
| `start`, `end` | video, audio | seconds (`90`) or m:ss (`1:30`): play only that part |
| `qr_url` | qr (needed), any other row | a link shown as a QR code ("Scan to take it home"). For a page of this site write `{site}` and the page: `{site}contribute/` shows the English page's code on English slides and the Spanish page's (`…/es/contribute/`) on Spanish slides; `{site_es}contribute/` shows the Spanish page on every slide; `{site}` alone is the home page. Another site's link shows the same code in both languages. A page, never a document file (`….pdf`): the link's address is printed under the code — link to the page that offers the document |
| `source_url` | every fact (needed for quiz, truefalse, fact, history, fill) | where the fact can be checked — never shown |
| `notes` | every row | for the committee only — never shown, never checked |

**Languages.** A row is shown in English when it has its English words, in Spanish when it has its Spanish words —
write both, or only one (an English-only quote stays out of a Spanish-only show). Once a row has anything in a
language, it needs everything its type needs in that language. A video, sound or picture with no words at all is
shown in every language.

## The types

What each type looks like on the screen, and one row of the file as an example (English shown; the `_es` columns are
filled the same way):

| type | on the screen | example |
|---|---|---|
| quiz | a question, 2–6 choices, a timer ring; the right choice lights up after `reveal`, then the explanation. A visitor can tap a choice | `text_en` In 1944, how many AA members started the Grapevine? · `choices_en` Two \| Twelve \| Six \| Sixty · `correct` 3 · `explain_en` Six members in the New York area … · `credit_en` Source: aagrapevine.org · `source_url` |
| truefalse | a statement with two big buttons, True and False, then the answer | `text_en` The Grapevine is older than AA's General Service Conference. · `correct` true · `explain_en` True! The first issue came out in June 1944 … · `source_url` |
| fill | a sentence with a blank that fills itself in | `text_en` In 1948, the Grapevine went from a three-column newsletter to the ___ size it still has today. · `answer_en` digest · `source_url` |
| scramble | letter tiles that put themselves in order | `text_en` Unscramble it! A Grapevine editor wrote it, and it first appeared in the June 1947 issue. · `answer_en` Preamble |
| fact | "Did you know?" with an optional heading | `title_en` Our meeting in print · `text_en` In the 1940s, AA members serving overseas wrote to … · `credit_en` · `source_url` |
| history | a big date and what happened | `title_en` June 1944 · `text_en` Six AA members in the New York area … publish the first Grapevine … · `source_url` |
| quote | a big quotation and its exact credit line | `text_en` Maintaining an "informative attitude" in all Grapevine presentation plans … · `credit_en` 1960 Advisory Action. Reprinted from Advisory Actions of the General Service Conference … with permission … |
| poll | a question; visitors tap to vote and see the bars (votes stay on the booth's device, never with names) | `text_en` What's your service connection to Grapevine and La Viña? · `choices_en` I'm a GVR or RLV \| I serve another way (GSR, DCM…) \| Thinking about it \| Just curious! |
| prompt | "Let's talk": a question to talk about with the people at the table | `text_en` What's the funniest thing that's happened to you in sobriety? … |
| message | a heading and a short text, with its QR code beside it when it has one | `title_en` Thanks for stopping by · `text_en` The {committee} meets on Zoom every month … · `qr_url` {site}meetings/ |
| qr | a big QR code with a heading and a line | `title_en` Listen on our site · `text_en` Both Grapevine podcasts in one place … · `qr_url` {site}listen/ |
| video | an official YouTube video (a Short in a phone-shaped frame), muted unless the booth's sound is on; it needs internet | `title_en` AA's Twelfth Step Tools: Grapevine and La Viña · `media_url` https://www.youtube.com/watch?v=V3RzyHdgQCY · `credit_en` AA Grapevine & La Viña on YouTube |
| audio | a podcast episode with moving bars — only while the booth's sound is on; it needs internet | `title_en` Podcast: The Day Hope Arrived · `media_url` https://episodes.captivate.fm/episode/….mp3 · `qr_url` {site}listen/ |
| image | a picture from the web with its caption; it needs internet (none in the file today — photos of our own tables go into the Drive booth folder instead) | `title_en` a caption · `media_url` https://… .jpg on one of the allowed sites |

## The Drive booth folder

Photos, videos, sound files, posters and short notes for the booth go into the committee's Drive panel folder, in a
folder named `booth` (or Booth, booths, mesa, kiosk, kiosko, kiosco, display, pantalla, stand, exhibit, exhibición —
capitals and accents do not matter), e.g. `2027-2028_Panel77_GVLV/booth/`. Its sub-folders are **collections** —
`booth/Spring Assembly 2027/` — that a booth can switch on or off in its settings (all on to start with); a deeper
sub-folder belongs to its top collection. The daily update reads the folder; the site copies the photos and videos
so they play offline too. Everything in the folder is public (the panel folder is "Anyone with the link").

A file's **name** says how the booth shows it — every part is optional but the title:

    [order] [magazine] [language] Title [(option) (option) …].ext

| part | what to write | meaning |
|---|---|---|
| order | a leading number of 1–3 digits and a separator: `01 `, `02-`, `3_` | its place in the player's "In order" mode; never shown. A 4-digit year or a date at the start is not an order, nor a number that counts something (`12 Steps poster`) — write `01 …` to make it one |
| magazine | `GV` (Grapevine), `LV` (La Viña), `GVLV` / `GV-LV` / `GV+LV` / `GV&LV` / `AA` (both, the default) — a leading word, or in parentheses or brackets anywhere: `(LV)`, `[GV]`, `(La Viña)`. A leading `AA` counts only right before a language code (`AA EN Welcome.png`); otherwise it is part of the title: `AA Preamble.png` keeps "AA" in its caption | the slide's colour and the "Grapevine / La Viña" filter |
| language | `EN` (also English, Inglés), `ES` (Spanish, Español), `BI` or `EN-ES` (both) — as a leading word in CAPITALS only (so "En la mesa…" stays a title), or in parentheses anywhere: `(es)`, `[English]` | no language = shown in every language mode (photos, music, pictures without words). `EN` plays in the English, Both and Alternate modes, not in Spanish-only mode, and the other way round. Leading words count only before the title: `Esto ES La Viña.jpg` keeps "ES" in its title |
| Title | the rest of the name (underscores become spaces; "Copy of" and a copy's " (1)" are dropped) | the caption (a note's heading). A camera's name (IMG_1234, PXL_…, WhatsApp Image …, Screenshot …) gives no caption |

Options, in parentheses or brackets, any order, English or Spanish, any capitals (several in one pair work too:
`(first, 15s)`):

| option | meaning |
|---|---|
| `(poster)` `(cartel)` `(afiche)` | show the whole picture, never cropped, over a blurred copy of itself — the default for .png .gif .webp .svg .bmp, documents (a PDF's or a slide deck's first page) and videos |
| `(photo)` `(foto)` | fill the screen with a slow zoom — the default for .jpg .jpeg .heic .heif .tif |
| `(10s)` `(10 s)` `(10 sec)` `(10 seg)` `(10 seconds)` `(10 segundos)` `(2 min)` | seconds on screen of a photo, poster or note (3–120); ignored for a video or sound file |
| `(0:15-1:30)` `(15-90)` `(0:15-)` `(0:15 a 1:30)` | play only this part of a video or sound file (start-end in m:ss or seconds; no end = to its end) |
| `(muted)` `(mute)` `(silent)` `(sin sonido)` `(silencio)` | never play this file's sound |
| `(x2)` … `(x5)` `(2x)` | shown 2–5 times as often |
| `(rare)` `(sometimes)` `(poco)` `(a veces)` | shown half as often |
| `(first)` `(primero)` `(primera)` | shown first when the show starts (and after the settings change) |
| `(from 2027-03-01)` `(desde …)` | only from that day (also "March 1, 2027", "1 de marzo de 2027", "03/01/2027"; a month alone is its first day) |
| `(until 2027-03-15)` `(hasta …)` | only until that day, inclusive (a month alone: its last day) |
| `(no caption)` `(no text)` `(sin texto)` `(sin título)` | the picture or video without its title |
| `(off)` `(apagado)` `(draft)` `(borrador)` | kept in the folder, never shown |

A name starting with `_` or `~` is never shown either — notes for the committee (`_README naming.txt`).

| file | the booth shows |
|---|---|
| `GV EN Welcome to our table (first) (15s).png` | a poster, Grapevine, English, first, 15 seconds |
| `LV ES Testimonio - Mi primer número (0:05-1:45).mp4` | a video, La Viña, Spanish, from 0:05 to 1:45 |
| `GVLV Our booth at CityWide Dallas.jpg` | a photo, both magazines, every language |
| `IMG_2045.JPG` | a photo without a caption |
| `02 GV Literature table display (x3).png` | a poster, Grapevine, second in "In order", three times as often |
| `Spring Assembly 2027/GV EN Book display.jpg` | a photo in the collection "Spring Assembly 2027" |
| `GVLV BI Bienvenidos - Welcome.mp4` | a video in both languages |
| `GV EN Welcome message.txt` | a note: "Welcome message" as its heading, the file's text below |
| `Grapevine and La Viña - ways to carry the message.pdf` | a poster made from the document's first page |
| `[LV][ES] Cita (10s) (muted).mp4` | a video, La Viña, Spanish, never its sound |

**File types:** pictures (jpg, png, gif, webp, heic, tif, bmp, svg); documents shown as a picture of their first page
(PDF, PowerPoint, Keynote, Google Slides, Google Drawings); videos (mp4 is best: H.264 video with AAC sound; also
m4v, webm, mov); sound (mp3, m4a, aac, wav, ogg, opus — played only while the booth's sound is on); notes (txt, md,
Google Docs, docx — a few short lines read best; **bold**, line breaks and "- " lists show, and at most 1,200
characters are kept). Anything else (zip, spreadsheets, forms, avi, wmv …) is never shown and is named, with what to
do, in the update's run summary and in the player's *Settings → Slides*. A video or sound file can be up to 95 MB
and the whole folder about 400 MB (`config/site.yml` → `booth:`): a bigger video or sound file is not copied and is
left out; a picture past the folder's limit shows only while the booth has internet.

**For this folder, the AA rules:** no faces and no full names of AA members (photos of tables, displays and rooms
only); no Grapevine or La Viña logos, covers, artwork, cartoons (Victor E. included: his official videos are already
in this CSV as YouTube rows) or their audio and video files (official videos go into this CSV as YouTube links, which
play from the official channel); only material the committee made or has permission to use. The words the check
refuses in the CSV (PDF, donate, hurry … — see [The rules](#the-rules-aa-principles)) are refused here too: a file
whose caption, or a note whose heading or text, says one is left out and named in *Settings → Slides*; rename it, or
add `(no caption)` to show a picture without its title.

The naming rules are written out in full, with many more examples, at the top of `scripts/sync/booth_names.py`
(the code that reads the names) and in [how-to/booth.md](../../how-to/booth.md).

## The rules (AA principles)

The check refuses a row that breaks one of these; the rest is up to the committee.

* **Only Grapevine and La Viña** (their history, how they work, writing for them, GVR / RLV service, the apps,
  podcast, YouTube, Carry the Message, prices as information, our committee's meetings and events) and AA texts
  about them.
* **Facts:** only facts from an official source (aa.org, aagrapevine.org, aalavina.org, AA literature), with its
  link in `source_url` and a short source note in `credit_*` where it helps ("Source: aagrapevine.org").
* **Quotes:** A.A. World Services texts word for word, with their exact credit line ("Reprinted from The A.A. Service
  Manual, 2024–2026 Edition, p. 85, with permission of Alcoholics Anonymous World Services, Inc."); Spanish only
  from an official Spanish text. Grapevine and La Viña material (stories, the Statement of Purpose, Daily Quotes,
  the Workbook) is **paraphrased**, never quoted — the live Daily Quote is already in the show.
* **Links** (`media_url`, `qr_url`) only to YouTube, aa.org, aagrapevine.org, aalavina.org, neta65.org, the podcast's
  host (captivate.fm: episodes., podcasts. and player.captivate.fm) and this site; a `qr_url` to a page, never a
  document file (`.pdf`) — its address is printed under the code. A video must be an official Grapevine / La Viña
  one (the check compares it with the channel's list the site keeps), a podcast episode one of the episodes the site
  lists. No Grapevine or La Viña covers, logos, cartoons or artwork; pictures of tables, displays and rooms only — no
  faces, no full names (first name and last initial at most).
* **Attraction, not promotion:** information, "you might", "ask us". The check refuses: PDF (say "document"),
  donate / donation / donativo (say "Carry the Message gift"), "contribution to Grapevine" / "contribuir a La
  Viña" (AA Grapevine, Inc. takes no contributions), "buy now", "hurry", "limited time", "subscribe now / today",
  "download now / today", a shouted "Subscribe!", "last chance", "act now", "don't miss", "sale!", "before prices go
  up" and their Spanish twins ("¡Descárgala ahora!", "¡Suscríbete!" …), "Conference-approved" said of Grapevine or La
  Viña (say "recognized by the Conference as the international journal of AA"), and "today only" in a text without
  `{event}`. "Download the app today" and "ask us how to subscribe" stay: they inform.
* **Only verified facts:** the check refuses the claims no source was found for — "reach millions" / "llegan a
  millones" and "the 183 Challenge" / "el Reto 183".
* **Placeholders:** only `{event}`, `{committee}` and `{site}` in a text; `{site}` and `{site_es}` at the start of a
  `qr_url`.

The same words are refused in what the show adds by itself (an official video's title, a bulletin post, an event's
name …): such an item is left out — a list loses only that row — and named in *Settings → Slides*.
