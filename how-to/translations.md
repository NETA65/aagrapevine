# Translations: English and Spanish on every page

The whole site exists twice: in English at `/…` and in Spanish at `/es/…`. This guide shows where each
word comes from, how to fix a translation that reads badly, how to write your own Spanish (or English)
for a post or an event, and where to change the code.

**In this guide**

1. [What this is](#1-what-this-is)
2. [Quick start](#2-quick-start)
3. [Full reference with examples](#3-full-reference-with-examples)
   - [3.1 The two languages and the page addresses](#31-the-two-languages-and-the-page-addresses)
   - [3.2 Buttons, menus and headings: `src/_i18n/*.json`](#32-buttons-menus-and-headings-src_i18njson)
   - [3.3 Automatic translation of synced content](#33-automatic-translation-of-synced-content)
   - [3.4 Fix one text: `data/translations/overrides.yml`](#34-fix-one-text-datatranslationsoverridesyml)
   - [3.5 Fix a word everywhere: `data/translations/glossary.yml`](#35-fix-a-word-everywhere-datatranslationsglossaryyml)
   - [3.6 The translation memory: `data/translations/cache.json`](#36-the-translation-memory-datatranslationscachejson)
   - [3.7 Make a bulletin post or an event bilingual by hand](#37-make-a-bulletin-post-or-an-event-bilingual-by-hand)
4. [What happens next](#4-what-happens-next)
5. [Where it shows on the website](#5-where-it-shows-on-the-website)
6. [Going further: change the code](#6-going-further-change-the-code)
7. [Troubleshooting](#7-troubleshooting)
8. [Good practice and AA principles](#8-good-practice-and-aa-principles)
9. [See also](#9-see-also)

---

## 1. What this is

The site has **two kinds of text**, and each is fixed in its own place:

| Kind | Examples | Where it lives | Who writes the other language |
|---|---|---|---|
| **Interface words** (buttons, menus, headings, notes) | "Events / Eventos", "View flyer / Ver volante", "Auto-translated / Traducción automática" | [`src/_i18n/*.json`](../src/_i18n/) — one entry holds both languages | A person, by hand |
| **Content** (titles, summaries, bulletin posts, events, Drive file names, podcast and video titles …) | "Bottle to Throttle" → "De la botella al volante" | Comes in ONE language from its source (Drive, a feed, a file in the repo). Every update run adds the other language with **offline translation models** and saves both in `data/site/*.json` | The machine — unless you give your own words |

You can correct the machine in three ways:

- **One text** that reads badly → [`data/translations/overrides.yml`](../data/translations/overrides.yml).
- **One word or name, everywhere** → [`data/translations/glossary.yml`](../data/translations/glossary.yml).
- **Your own words** for a post or an event you write in the repo → `title_es` / `summary_es` in its header
  (`title_en` / `summary_en` when the file is in Spanish).

**Where it shows:** every page in both languages (`/events/` and `/es/events/`, `/bulletin/` and `/es/bulletin/` …),
the news feeds (`/feed.xml`, `/es/feed.xml`), the calendar files (`/events.ics`, `/es/events.ics`), the search,
and the monthly digest e-mail. A text the machine translated carries a small **Auto-translated** pill
(**Traducción automática** on Spanish pages).

> **Good to know:** the translation runs inside GitHub Actions with free, open-source models (Argos Translate /
> OPUS-MT, run by CTranslate2). No text is sent to an outside translation service, and there is no API key.
> Every file in this guide can be edited with the everyday GitHub login (MKP715, write access). Nothing here needs
> the admin account (NETA65).

**I want to …**

| … | Go to |
|---|---|
| fix a title or summary that the machine got wrong | [3.4](#34-fix-one-text-datatranslationsoverridesyml) |
| stop the machine from translating a group's name or a place | [3.5](#35-fix-a-word-everywhere-datatranslationsglossaryyml) (`keep:`) or [3.4](#34-fix-one-text-datatranslationsoverridesyml) |
| make "sponsor" always come out as "padrino" | [3.5](#35-fix-a-word-everywhere-datatranslationsglossaryyml) (`terms:`) |
| change the words on a button or a heading | [3.2](#32-buttons-menus-and-headings-src_i18njson) |
| write the Spanish of a bulletin post or an event myself | [3.7](#37-make-a-bulletin-post-or-an-event-bilingual-by-hand) |
| hand-translate a bulletin post that lives on Google Drive | [3.7.3](#373-a-bulletin-post-on-google-drive) |
| know why a fix does not show | [7](#7-troubleshooting) |

---

## 2. Quick start

### 2.1 Fix one wrong translation (the 80% case)

Say the podcast episode "Bottle to Throttle [Season 5, Episode 8]" shows on `/es/listen/` with an odd Spanish title.

1. Open the item on the page **in its original language** (an English podcast → the English page `/listen/`;
   a La Viña title → the Spanish page). Copy the text **exactly**: same dashes, same quote marks, same final period.
   A tail such as "[Season 5, Episode 8]" or "(Spanish)" may be left out: it is translated on its own.
2. On github.com open [`data/translations/overrides.yml`](../data/translations/overrides.yml) and click the
   **pencil** (Edit).
3. Add **one line** at the end of the right section:

   ```yaml
   # English original → your Spanish (in the "English → Spanish" part)
   "Bottle to Throttle": { es: "De la botella al volante" }

   # Spanish original → your English (in the "Spanish → English" part)
   "Tocaron Fondo": { en: "Hitting Bottom" }
   ```

   (Both lines are already in the file: they show the pattern. Add your own text the same way, once.)
4. Click **Commit changes…** → commit to `main`.
5. Wait for the **Website update** run (GitHub → **Actions**). About 5 minutes later (the run tests the change
   first; allow up to 10 more minutes before every visitor sees it, so 10–20 minutes is a safe guess) the
   other-language page shows your words. The "Auto-translated" pill goes away only when **every** machine-made part of the item
   is covered. This episode keeps it: its title has a "[Season …]" tail (a part fix) and its summary is still
   machine-made (see [Whole text or part of it](#whole-text-or-part-of-it)).

If the run summary says **Settings problems: data/translations/overrides.yml could not be read**, a quote or a
colon is wrong. Fix the line and commit again (see [Troubleshooting](#7-troubleshooting)).

### 2.2 Change a button or a heading

Say you want "Upcoming events" on the Events page to read "Coming up".

1. Search the repo for the words (GitHub's search box, or open the folder [`src/_i18n/`](../src/_i18n/)).
   "Upcoming events" is the key `committee.events.upcoming` in `src/_i18n/committee.json`. (The same words are
   also under `home.events_title`, the home page's heading, and two other keys: each page has its own key.)
2. Click the pencil and edit **both** languages:

   ```json
   "committee.events.upcoming": {
     "en": "Coming up",
     "es": "Lo que viene"
   },
   ```

3. Commit to `main`. Website update rebuilds the site; the **Code check** run tests the files.

### 2.3 Write your own Spanish for a post or an event

In a file in [`content/bulletin/`](../content/bulletin/README.md) or [`content/events/`](../content/events/README.md)
written in English, add two lines to the header:

```yaml
title_es: "¡Bienvenidos, nuevos RLV y GVR!"
summary_es: "Texto completo del aviso en español."
```

The Spanish page then shows your words exactly as written, with no "Auto-translated" pill.
Details and every option: [3.7](#37-make-a-bulletin-post-or-an-event-bilingual-by-hand).

---

## 3. Full reference with examples

### 3.1 The two languages and the page addresses

Every page template is built twice, once per language in [`src/_data/languages.js`](../src/_data/languages.js)
(`["en", "es"]`). English pages live at `/…`, Spanish pages at `/es/…`. On GitHub Pages the folder
`/aagrapevine/` comes first, so the public address of the Spanish Events page is
`https://neta65.github.io/aagrapevine/es/events/`.

| Page or file | English | Spanish |
|---|---|---|
| Home | `/` | `/es/` |
| Events | `/events/` | `/es/events/` |
| Bulletin (one post: `#<slug>`, the same slug in both) | `/bulletin/` | `/es/bulletin/` |
| News feed (RSS) | `/feed.xml` | `/es/feed.xml` |
| Calendar file | `/events.ics` | `/es/events.ics` |
| Search index | `/search-index.json` | `/es/search-index.json` |
| Sitemap | `/sitemap.xml` lists both languages, paired | — |

- The **EN / ES** pill in the header and the **Ver en español / View in English** button in the menu go to the same
  page in the other language, and keep the `#anchor` and `?query` (so `/bulletin/#ann-x` → `/es/bulletin/#ann-x`).
- A visitor whose browser prefers the other language sees a small card after about a second:
  **¿Prefieres español? · Ver en español** (or **Prefer English? · View in English**). Once dismissed, or once the
  visitor switched language, it never comes back on that browser.
- A link to one of our own pages inside a post or an event description (`[podcast](/listen/)`) opens the Spanish page
  (`/es/listen/`) when it is clicked on a Spanish page. Links to files (`/bulletin/files/flyer.pdf`, `/feed.xml`) and
  outside sites are left as they are.
- Dates and times follow the page: "Wednesday, October 21, 2026" / "Miércoles, 21 de octubre de 2026", and
  "7:00 PM" / "7:00 p. m." (Central time).

> **Note:** "English and Spanish" is wired into the code in several places (the page list, the Python translation
> code, every `src/_i18n` entry). Adding a third language is a programming project, not a setting.

### 3.2 Buttons, menus and headings: `src/_i18n/*.json`

#### The format

Each file is one JSON object. Each **key** holds both languages:

```json
"committee.events.view_flyer": {
  "en": "View flyer",
  "es": "Ver volante"
},
"committee.events.view_flyer_of": {
  "en": "View flyer: {title}",
  "es": "Ver volante: {title}"
},
"community.banner.q": { "en": "Prefer English?", "es": "¿Prefieres español?" },
```

- One line or several lines — both are fine.
- `{title}`, `{date}`, `{n}` … are **placeholders**: the page puts a value there. Keep the same placeholders in both
  languages.
- JSON is strict: double quotes only, a comma between entries, **no comma after the last entry** (of the file,
  and inside each `{ }`).
- Write plain text. Most templates show a string exactly as typed, so `<b>…</b>` or `**…**` would appear on the
  page as typed; only a template line that adds `| safe` or `| mdInline | safe` turns them into formatting. Check
  the template before you put markup in a string.

#### Which file holds what

The build merges all 18 files into one table (4,756 keys today). The first part of a key tells you the page area:

| File | Holds (key prefix → area) |
|---|---|
| `common.json` | `nav.*` (menu, language switch), `footer.*`, `common.*` (shared buttons, "Auto-translated"), `lang.*` ("Originally in English"), `kind.*`, `feeds.*`, `comfort.*` (reading settings), `a11y.*`, `site.*` |
| `committee.json` | `committee.events.*` (/events/), `committee.ann.*` (/bulletin/), `committee.meeting*` (/meetings/), `committee.docs.*` (/portfolio/), `committee.photos.*`, `committee.ics.*` (calendar file name and description) … |
| `community.json` | `community.status.*` (/status/), `community.digest.*` (/digest/), `community.wn.*` (What's New), `community.banner.*` (language suggestion card), `community.nf.*` (404) … |
| `booth.json` | `booth.*`: the booth display on `/about/#booth` — the section, the player's buttons and Settings in the page's language; `booth.screen.*`, the words on the booth's screen ("Right!", "Show the answer" …), which reach the player in **both** languages because a slide shows its own language(s), not the page's; `booth.tag.*`, the topic names. `tests/test_booth_page.py` checks that every key the player uses exists |
| `home.json`, `read.json`, `media.json`, `library.json` (+ the /search/ page's `search.*`), `shop.json`, `monthly.json`, `orientation.json`, `presentations.json` (`pres.*`), `published.json`, `report.json`, `pwa.json`, `access.json`, `expenses.json`, `freshness.json` | one file per page area |

#### Change an existing button or heading

1. Find the words on the page, then find the key: search the repo for the English words inside `src/_i18n/`.
   Example: "View flyer" → `committee.events.view_flyer` in `committee.json`.
2. If the same words appear under several keys, check which key the page's template uses. Templates are in
   `src/pages/` (one per page: `events.njk`, `bulletin.njk`, `index.njk` for the home page …). Search the template for
   the key's name, e.g. `committee.events.view_flyer` (it is written `{{ "committee.events.view_flyer" | t(lang) }}`).
   Some keys are used in `eleventy/filters/*.js` instead (for example `committee.events.online_on`): search there too.
3. Edit `"en"` and/or `"es"`. Keep every `{placeholder}`.
4. Commit to `main`.

Example — the online line of an event card:

```json
"committee.events.online_on": {
  "en": "Online on {platform}",
  "es": "En línea por {platform}"
},
```

Shows "Online on Zoom" on `/events/` and "En línea por Zoom" on `/es/events/` (also on the home page, `/contribute/`
and in the calendar files' descriptions). Change it to `"en": "Join on {platform}", "es": "Únete por {platform}"` and
both languages change. Writing `"es": "Únete por Zoom"` (no placeholder) would print "Zoom" even for a Google Meet
event — and the test `test_the_same_placeholders` fails.

> **Note:** `tests/test_events_feeds.py` and `tests/test_recurring_events.py` check the words "Online on Zoom" /
> "En línea por Zoom". If you change this key, update those tests in the same commit, or the Code check turns red.

#### Add a new string

Add an entry to the file of that page area, with **both** `"en"` and `"es"`, and use it in the template **in the same
commit**:

```json
"committee.events.bring_friend": {
  "en": "Bring a friend: everyone is welcome.",
  "es": "Trae a un amigo: todos son bienvenidos."
},
```

```njk
<p class="text-sm text-muted">{{ "committee.events.bring_friend" | t(lang) }}</p>
```

With a value: `{{ "committee.ann.until" | t(lang, { date: someDate }) }}` fills `"until {date}"` /
`"hasta el {date}"`.

#### What happens with a mistake (`I18N_STRICT`)

The GitHub builds set `I18N_STRICT=1` (in [`update.yml`](../.github/workflows/update.yml) "Build the website" and in
[`check.yml`](../.github/workflows/check.yml)). A local build on a PC does not, unless you set it.

| Mistake | Build on a PC (no `I18N_STRICT`) | Build on GitHub (`I18N_STRICT=1`) | Caught by the tests |
|---|---|---|---|
| A template uses a key that is in no file (a typo, or the entry was not committed) | the raw key is printed on the page, e.g. `committee.events.view_flyr` | **the build stops**: `Error: Missing i18n key: committee.events.view_flyr`. Nothing is published; GitHub Pages keeps the previous site | — |
| The key exists but has no `"es"` | the Spanish page silently shows the English | same | `test_english_and_spanish` fails |
| `"es": ""` while `"en"` has text | the Spanish page shows nothing there | same | same test ("one language is empty") |
| `{date}` in one language only | `{date}` printed as is, or the value missing | same | `test_the_same_placeholders` |
| The same key in two files | the later file (alphabetical) wins, silently | same | `test_no_key_in_two_files` |
| A JSON typo (missing comma, comma after the last entry) | the build stops with a message such as `Expected ',' or '}' after property value in JSON at position 21 (line 2 column 20)` (a missing comma) or `Expected double-quoted property name in JSON at position … (line N column M)` (a comma after the last entry) | same | — |

> **Note:** the JSON error gives a line and column but not the file name. It is the file you just edited.

The tests are in [`tests/test_i18n_keys.py`](../tests/test_i18n_keys.py). A key whose two values are both empty
(`lang.und`) is allowed on purpose.

The same switch also guards the bilingual settings files: `config/carry.yml`, `config/orientation.yml`,
`config/history.yml`, `config/expenses.yml` and `config/presentations/*.yml` hold `{ en: "…", es: "…" }` pairs.
A missing language is copied from the other one (with a warning) on a PC, and **stops the build** on GitHub.
See [Settings](settings.md) and [Presentations](presentations.md).

#### Keys that look "inverted" (do not fix them)

- `nav.switch_lang` is `{ "en": "Ver en español", "es": "View in English" }`, and `nav.switch_lang_aria` likewise.
  The button invites to the **other** language, so its "en" value (shown on English pages) is written in Spanish.
- `community.banner.*` (the language suggestion card) is normal, but it is shown on the **other** language's page:
  the `"en"` text "Prefer English?" appears on Spanish pages, for English speakers.

#### Words that are NOT in `src/_i18n`

| Where | What | Change it in |
|---|---|---|
| The monthly digest **e-mail** | its own copy of the `community.digest.*` words, plus "Some titles were translated automatically." / "Algunos títulos se tradujeron automáticamente." | the table `T = {"en": …, "es": …}` in [`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py). Changing the site's digest words does not change the e-mail: edit both. See [E-mail and alerts](email-and-alerts.md) |
| Small browser messages | "Copied to clipboard" / "Copiado al portapapeles" | `GV.t("English", "Español")` calls in [`src/assets/js/app.js`](../src/assets/js/app.js) |
| Committee meeting title and summary, Weekly Open day and time sentences | written by rules in both languages, never machine-translated (except a changed meeting `note` without `note_es`, see [3.7.5](#375-settings-texts-configsiteyml)) | [`scripts/sync/build_data.py`](../scripts/sync/build_data.py): `committee_meetings`, `weekly_open_labels` |
| Source names on `/status/` ("Google Drive (committee uploads)" / "Google Drive (archivos del comité)") | an English and a Spanish name per source | the `SOURCES` list in [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) |
| The workshop presentations' slide words (English) | "(auto-translated)" after a machine gloss, "Online on {platform}" … | the `EN` table in [`src/assets/js/presentations-core.js`](../src/assets/js/presentations-core.js) — see [Presentations](presentations.md) |
| The repeat line "Every second Saturday of the month" / "Cada segundo sábado del mes" | the pages build it from `committee.rule` and `committee.ord.*` in `src/_i18n/committee.json`; `build_data.py` keeps a copy (`_RULE`, `_ORD_WORDS`) | **both** places — `tests/test_recurring_events.py` checks that they say the same |
| Settings texts (`title_es`, `committee_es`, `chair_title_es`, `summary_es` of recurring events …) | the committee's own words | [`config/site.yml`](../config/site.yml) — see [3.7.5](#375-settings-texts-configsiteyml) |

#### Tests that pin exact words

A few tests check exact wording. After you change a word, watch the **Code check** (or run the tests, see
[section 6](#6-going-further-change-the-code)). Examples:

- [`tests/test_bulletin.py`](../tests/test_bulletin.py) expects `nav.bulletin` to be "Bulletin" / "Boletín".
- [`tests/test_events_feeds.py`](../tests/test_events_feeds.py) looks for "View flyer" / "Ver volante" on the built
  Events page, and (with [`tests/test_recurring_events.py`](../tests/test_recurring_events.py)) for "Online on Zoom" /
  "En línea por Zoom".

If one fails, its message shows the words it expected. Update the test to your new words in the same commit (or keep
the old words).

### 3.3 Automatic translation of synced content

#### What the machine translates

The sync ([`scripts/sync/build_data.py`](../scripts/sync/build_data.py), function `text_fields`) asks for a translation
of these fields, each item into the other language:

| Content | Fields translated |
|---|---|
| Every item (podcast episode, video, story, PDF, Drive file, Instagram post, bulletin post, event …) | `title`, `summary` |
| Bulletin posts, and events with a description | the whole text (`body_md`, Markdown kept) |
| Magazine stories | section, topic, issue theme, department |
| Drive photos | the album (folder) name |
| YouTube playlists · podcast shows · magazine issues | playlist titles · show titles and descriptions · issue themes and descriptions |
| Shop | Book of the Month title and blurb, type descriptions, the bulk-discount note |
| A recurring event or the committee meeting note written in one language only | the missing language |

**Never machine-translated:** an event's **place** (addresses and group names stay as written), the daily quote
(shown as published), meeting names, issue labels, Weekly Open times, the published writers' home towns (written by
rules), the committee meeting's own title, and the text **inside** a PDF, picture or slide deck — only its title is
translated.

#### Which way it translates (the original language)

Every item has a `lang`: the language it was written in. That decides the direction (`en → es` or `es → en`).

- **A file in the repo** (`content/bulletin/*.md`, `content/events/*.md`): the header line `lang:` (or `language:`).
  Only the first two letters count. If they are not `en` or `es`, the language is detected from the title and text.

  | Header line | Result |
  |---|---|
  | `lang: es` | `es` |
  | `lang: Español`, `lang: es-MX` | `es` |
  | `language: English` | `en` |
  | `lang: Spanish` ("sp") or `lang: inglés` ("in") | not understood → detected from the text |
  | no line, text "¡Bienvenidos, nuevos RLV! Ven a la reunión del comité." | `es` (detected) |
  | no line, text "La Viña" only | `en` (not enough clues → English) |

- **A file on Google Drive:** first a guess from the folder and file name — Spanish when a Spanish hint word appears
  (informe, reporte, nota, minuta, acta, presentación, diapositiva, volante, folleto, foto, imagen, galería, taller,
  boletín, anuncio, aviso, noticias, formulario, inscripción, **la viña**, español; most also in the plural —
  informes, talleres …; accents and capitals ignored) — then a check of the title itself, with the magazine names
  left out (so "Grapevine & La Viña …" does not make an English title look Spanish). A bulletin document is checked
  once more with the first lines of its text, after it is downloaded.

  | Folder / file name | Result |
  |---|---|
  | `flyers/Taller de Escritura de La Viña - Grupo Libro Grande, Tyler.jpg` | `es` |
  | `flyers/Grapevine Writing Workshop - Primary Purpose Group, Arlington.png` | `en` |
  | `bulletin/2027-01-10 Welcome new GVRs.docx` | `en` |
  | `boletín/2027-01-10 Bienvenidos nuevos RLV.docx` | `es` |
  | `notes/2026-10-01 Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf` | `en` (the name has "La Viña", but the title is English) |
  | `photos/Asamblea 2027/IMG_1234.jpg` | `en` — camera names give no clue, and "asamblea" is not a hint word (see [6.4](#64-example-teach-the-site-a-spanish-word-for-drive-names)) |

- **Feeds and outside sites** give their own language or are detected. La Viña items are Spanish, Grapevine items English.
  A text in a third language (French, for example) is shown as it is on both pages.

> **Note:** a wrong `lang` means **no translation at all**. An English text marked `lang: es` is "translated" from
> Spanish; the translator sees it is already English and leaves it as is. The Spanish page then shows English with no
> "Auto-translated" pill.

#### What the translator does with each text

For every title, summary or text, in this order ([`scripts/sync/translate.py`](../scripts/sync/translate.py),
`Translator.translate` → `_quick`):

1. **Nothing to translate** (same language, a web address, a number, a code like `Panel77` or `2026-27`) → kept as is.
2. **`overrides.yml` has the whole text** → your words. Not marked "Auto-translated".
3. **Translated before** (`cache.json`) → reused.
4. **Already written in the other language** (a bilingual caption) → kept as is.
5. Otherwise **the model**, one sentence at a time. Before the model, each sentence is checked against
   `overrides.yml` (a fix for that sentence wins), names from the glossary `keep:` list and `terms:` are protected,
   and dates, prices and "[Season 3, Episode 7]" are written by rules. A **guard** throws away a bad result (a word
   repeated in a loop, an output more than 2.5 times longer, changed numbers): that sentence keeps its original words.

Capitals follow the magazines' style: a machine-made English title gets Title Case ("Bound by the same illness" →
"Bound by the Same Illness"), and the Spanish of an English Title Case title gets sentence case.

The result goes into the cache and into the site data as a pair, with a list of the languages that are machine-made:

```json
"i18n": { "title": { "en": "Bottle to Throttle", "es": "De la botella al volante" }, "summary": { … } },
"machine": []
```

`"machine": ["es"]` means at least one field of the item is a machine translation on the Spanish page → the
**Auto-translated** pill shows there.

#### Time budget: what is not done yet

The sync gives new translations up to **40 minutes** per run (push runs, the midday and evening refreshes and the
nightly full update; only a very long manual PDF crawl squeezes it, down to 10) and **5 minutes** to the
early-morning refresh. The newest and most visible texts go first (bulletin, events, the Weekly Open and editorial
themes, then What's New and the home page's writers, then other titles, then other summaries), and the Texas writers
archive's titles and then its subtitles come last of all (newest issue first; they are asked for in every run, so
the translation memory keeps them — [Writers archive §11](writers-archive.md#11-translations-of-titles-and-subtitles)).
What does not fit is **pending**: it shows in its original language on both pages (no pill) and is translated on a
later run. A translation problem never stops the site from
updating.

### 3.4 Fix one text: `data/translations/overrides.yml`

An override says: "when the site meets **this exact original text**, use **these words** in the other language."
Overrides always win over the machine and over the cache.

#### The recipe

1. Find the original text, exactly as written in its own language (where to copy it from:
   [the table below](#where-to-copy-the-exact-original-by-kind-of-item)).
2. Open [`data/translations/overrides.yml`](../data/translations/overrides.yml) on github.com → pencil.
3. Add one entry at the end of the right part of the file: **"English → Spanish"** (top) for an English original,
   **"Spanish → English"** (bottom) for a Spanish one. The order only helps people; the code does not care.
4. Commit to `main`. The site rebuilds by itself ([section 4](#4-what-happens-next)).

#### Every way to write an entry

The **key** (left) is the original text. The **value** (right) says which language you are giving: `es:` for the
Spanish of an English text, `en:` for the English of a Spanish text.

**1. One line, English original → your Spanish**

```yaml
"Bottle to Throttle": { es: "De la botella al volante" }
```

**2. One line, Spanish original → your English**

```yaml
"Nuevos": { en: "Newcomers" }
```

**3. Both languages in one entry**

```yaml
"UN DIA A LA VEZ": { es: "Un día a la vez", en: "One Day at a Time" }
```

The original here is Spanish, so `en:` is the translation. The `es:` value is in the text's **own** language: it can
only restore accents and capitals ([see below](#same-language-entries-fix-only-accents-and-capitals)).

**4. Block style** (the same meaning, on two lines; indent the second line two spaces)

```yaml
"Tocaron Fondo":
  en: "Hitting Bottom"
```

**5. Quote marks inside the text**

```yaml
# a straight double quote inside double quotes: write \"
"International Voices: \"Stories from ICYPAA and EURYPAA.”": { es: "Voces internacionales: “Historias de ICYPAA y EURYPAA”" }
# or use single quotes outside; a single quote inside is then written twice
'It''s Never Too Late': { es: 'Nunca es demasiado tarde' }
# curly quotes “ ” ’ need nothing special
"Sky “I grew up in A.A.”": { es: "Sky “Crecí en A.A.”" }
```

**6. A long key (a whole summary)**: start the line with `? ` and put the value on the next line, starting `: `.
This is **required** when the key is longer than about 1,000 characters (on one line, YAML refuses it and the whole
file becomes unreadable). It works for any length.

```yaml
? "A living list of simple ways members, groups and districts can support Grapevine and La Viña and carry the message. Take what works for your group … magazine content on…"
: { es: "Una lista viva de formas sencillas en que los miembros, los grupos y los distritos pueden apoyar a Grapevine y La Viña y llevar el mensaje. …" }
```

**7. A whole Markdown text** (a bulletin post's body): the key and the value as indented blocks (`|-`).
Indent the original two spaces; indent the translation four spaces under `: es: |-`.

```yaml
? |-
  A living list of simple ways members, groups and districts can support Grapevine and La Viña.

  # Why it matters

  - **A meeting in print, every day.** Grapevine and La Viña reach millions of people.
: es: |-
    Una lista viva de formas sencillas en que los miembros, los grupos y los distritos pueden apoyar a Grapevine y La Viña.

    # Por qué importa

    - **Una reunión impresa, todos los días.** Grapevine y La Viña llegan a millones de personas.
```

**8. Paste the text straight from the site data.** In `data/site/*.json` a text is one string with `\n` for line
breaks and `\"` for quotes. You can paste that string, **with its double quotes**, after `? ` — YAML reads `\n` and
`\"` the same way:

```yaml
? "A living list of simple ways …\n\n# Why it matters\n\n- **A meeting in print, every day.** Grapevine and La Viña reach …"
: { es: "Una lista viva de …" }
```

**Comments:** anything after ` #` outside the quotes is a note for people:
`"Coming in": { es: "Llegando a AA" }   # YouTube playlist`. A `#` inside the quotes is part of the text.

> **Tip:** always put both sides in double quotes. Without quotes, a comma or a colon in the text breaks the entry
> (examples in [Odd input](#odd-input-what-happens)).

#### How a text matches a key

Line breaks and runs of spaces count as one space. Then the key must match exactly — or match when accents and
capitals are ignored. Everything else counts: dashes, quote marks, the final period.

| Text on the site | Asking for | Result |
|---|---|---|
| `Bottle to Throttle` | Spanish | `De la botella al volante` |
| `bottle to throttle` | Spanish | same (capitals ignored) |
| `Bottle  to   Throttle ` | Spanish | same (spaces ignored) |
| `Bottle to Throttle.` | Spanish | **no match** (the final period counts) |
| `Bottle to Throttle` | English | no match (the entry only gives `es`) |
| `Un día a la vez` | English | `One Day at a Time` (matches the key `UN DIA A LA VEZ`: accents and capitals ignored) |
| `A Happy Father’s Day` (curly ’) | Spanish | `Un feliz Día del Padre` |
| `A Happy Father's Day` (straight ') | Spanish | **no match** — the key has ’ |
| `Grapevine and La Viña - ways to carry the message` (hyphen -) | Spanish | **no match** — the key has an em dash — |
| `GRAPEVINE AND LA VINA — WAYS TO CARRY THE MESSAGE` | Spanish | match |

#### Whole text or part of it

An override can fix a **whole field** or **a piece** of a longer text. The difference matters for the
"Auto-translated" pill.

| You fix | Example | Result on the other page | Pill |
|---|---|---|---|
| The **whole** title or summary | `"Bottle to Throttle": { es: "De la botella al volante" }` | "De la botella al volante" | **gone** (when every machine-made field of the item is covered) |
| A title before a **"[Season …, Episode …]"** tail | same entry, episode "Bottle to Throttle [Season 5, Episode 8]" | "De la botella al volante [Temporada 5, Episodio 8]" | stays |
| A title before a **"(Spanish)"** tail (library PDFs) | `"The Home Group: Heartbeat of AA": { es: "El Grupo Base: Corazón de AA" }` and `"(Spanish)": { es: "(español)" }` | "The Home Group: Heartbeat of AA (Spanish)" → "El Grupo Base: Corazón de AA (español)" | stays (even with both pieces fixed) |
| **One sentence** of a summary (copy it with its final period) | `"She learned later that alcoholism is a tricky disease.": { es: "Más tarde aprendió que el alcoholismo es una enfermedad engañosa." }` | that sentence in your words, the others by machine | stays |
| A **piece of a short title** (110 characters or less), cut at ` - `, ` – `, ` — `, ` \| ` or ` · ` | `"Grupo Solo por Hoy, Longview": { en: "Grupo Solo por Hoy, Longview" }` | in "Taller de Escritura de La Viña - Grupo Solo por Hoy, Longview" the group's name is kept, the rest by machine | stays |
| In a Markdown text: a **list line**, a **link's words**, **bold words**, or a sentence without a link or bold in it | `"current prices": { es: "los precios de hoy" }` | `[current prices](/shop/)` → `[los precios de hoy](/shop/)` | stays |

What a part fix can **not** reach:

- A sentence that **contains** a link or bold words — those words are taken out and translated on their own first.
  Fix the link's words alone, or the whole text.
- A piece of a **long** line (more than 110 characters): long lines are only cut at ` | ` and ` · `, never at a dash.
- One very long sentence (more than 320 characters): it is cut at a comma, a colon, a semicolon or a dash before
  the file is looked up, so a fix for the whole sentence never matches. Fix the whole text instead.
- A part fix needs the models, because the longer text must be translated again. While the models are missing,
  the longer text waits: it shows in its original language on both pages until a run can translate it. (A
  whole-text fix needs no model.)

> **Note:** a fix for a whole one-line title also keeps that title in one piece. Without it, a short title is cut at
> " - " and each half is translated alone. With `"Grapevine Writing Workshop - Primary Purpose Group, Arlington"` in
> the file, the whole name is replaced; without it, the group's name would go through the machine.

**Old translations are redone by themselves.** When you add or change an override, the next run throws away every
saved translation (in that direction) whose original **contains** your key (whole words, accents and capitals
ignored), and translates them again. So `"Bottle to Throttle"` also redoes "Bottle to Throttle [Season 5, Episode 8]"
and "A ride from bottle to throttle, with friends".

#### Same-language entries fix only accents and capitals

An entry in the text's **own** language may only restore what the source lost: accents and capital letters.

| Entry | Original | Shown in its own language |
|---|---|---|
| `"UN DIA A LA VEZ": { es: "Un día a la vez" }` | a Spanish YouTube playlist in capitals, no accents | `/es/watch/`: "Un día a la vez" |
| `"MUJERES EN AA": { es: "Mujeres en AA" }` | same idea (another playlist in capitals) | `/es/watch/`: "Mujeres en AA" |
| `"Hola amigos": { es: "Saludos, amigos" }` | other **words** | **ignored** — the original wording is never rewritten |

This is not applied to whole Markdown texts.

> **Note:** keep **one fix per text**. If the file already has an entry for the same words in other capitals or
> accents, add your language to that entry (`"Tocaron Fondo": { en: "Hitting Bottom", es: "…" }`) instead of
> adding a second one. Two entries for the same words must give exactly the same fix (as `"Como rezo"` and
> `"Cómo rezo"` do), or the Code check fails ("two different fixes").

#### Where to copy the exact original (by kind of item)

The safest source is always the **site data**, `data/site/<file>.json` → the item's `"title"`, `"summary"` or
`"extra"` → `"body_md"`. The page in the **original** language works too (careful with dashes and quote marks).

| Kind of item | The original text is … | Example entry | Fix shows on |
|---|---|---|---|
| Podcast episode | the feed's title or summary (`episodes.json`). A summary the feed cut off ends in "…": keep the "…" | `"Bottle to Throttle": { es: "De la botella al volante" }` · `"He says that in his guided life part of his job is too…": { es: "Dice que, en su vida guiada, parte de su trabajo es…" }` | `/es/listen/`, home, What's New, `/es/search/`, `/es/feed.xml` |
| YouTube video or playlist | `videos.json` (`title`, `playlists[].title`) | `"Coming in": { es: "Llegando a AA" }` | `/es/watch/`, home |
| Magazine story | `articles.json` | `"A Well-Worn Path": { es: "Un camino muy transitado" }` | `/es/read/`, `/es/published/`, home |
| Library PDF | `pdfs.json`; the "(Spanish)"-style tail is translated on its own | `"Grapevine Open Meeting": { es: "Reunión abierta de Grapevine" }` | `/es/library/` |
| Drive file (report, notes, slides, workshop, flyer copy) | the **file name** without its ending (`.pdf`), without a date at the start, and without the words the site takes out: "Copy of" / "Copia de", "(1)", `(pinned)` / `(fijado)`, `(until …)` / `(hasta …)`; underscores become spaces | `slides/GVR and RLV Orientation Workshop.pptx` → `"GVR and RLV Orientation Workshop": { es: "Taller de orientación para RLV y GVR" }` | `/es/portfolio/`, What's New, `/es/search/` |
| Dated flyer → event | the **event's** title: the file name without the date and the time (and without the place, when the name gives it in a form the site reads — see [Flyers and events](flyers-and-events.md)). It can differ from the flyer's own title | `flyers/2027-03-14 Taller de Escritura 7pm - Grupo Libro Grande, Tyler.jpg` → flyer title "Taller de Escritura 7pm - Grupo Libro Grande, Tyler" (Portfolio), event title "Taller de Escritura - Grupo Libro Grande, Tyler" (Events). Fix both: two entries | the other language's pages — for this Spanish name `/events/`, the home page's "Upcoming events", `/events.ics`, `/monthly/` |
| Grapevine / La Viña calendar event | `events.json` — keep the source's odd spaces | `"XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la vida )": { en: "XLII North Texas Zone A.A. Gathering (A.A. A Way of Life)" }` | `/events/`, `/events.ics`, home |
| La Viña editorial theme | `editorial.json`. Give **every** theme an entry, so no page or slide shows a machine gloss. `tests/test_editorial.py` checks the themes of its saved copy of the 2026–2027 document; a new year's document needs its new themes added by hand | `"Nuevos": { en: "Newcomers" }` | `/contribute/#deadlines`, `/monthly/`, home, presentations, district report |
| Book of the Month | `shop.json` → `botm` title and blurb | `"Frente a Frente: El apadrinamiento en acción": { en: "One on One: AA Sponsorship in Action" }` | `/shop/` |
| Drive photo album | the folder path under `photos/`, folders joined with " / " | `photos/Asamblea de Otoño 2027/…` → `"Asamblea de Otoño 2027": { en: "Fall Assembly 2027" }` | `/photos/` (the album's name), home photo strip, What's New |
| Bulletin post from Drive | three texts: title, summary, whole text | see [3.7.3](#373-a-bulletin-post-on-google-drive) | `/es/bulletin/`, home, What's New, feed, digest |
| Bulletin post or event written in the repo | use `title_es` / `summary_es` instead ([3.7](#37-make-a-bulletin-post-or-an-event-bilingual-by-hand)); an override for its title also works | — | — |

> **Note:** an override only works **in the direction the site translates**. If the site took a Spanish name for
> English (for example a camera-named photo in `photos/Asamblea 2027/`), it translates English → Spanish, and an
> `en:` value is a same-language entry that can only fix accents. Give the folder a clearer Spanish name
> ("Asamblea de Otoño 2027") or teach the site the word ([6.4](#64-example-teach-the-site-a-spanish-word-for-drive-names)).

#### Real entries in the file today

| Entry | What it fixes |
|---|---|
| `"Bottle to Throttle": { es: "De la botella al volante" }` | a podcast title — whole, and inside "[Season …]" titles |
| `"(Spanish)": { es: "(español)" }` and `"(español)": { en: "(Spanish)" }` | the language tail of library PDF titles, both ways |
| `"She learned later that alcoholism is a tricky disease.": { es: … }` | one sentence of a podcast summary |
| `"GVR and RLV Orientation Workshop": { es: "Taller de orientación para RLV y GVR" }` | a Drive slide deck's title (the machine kept the English word order) |
| `"Taller de Escritura de La Viña - Grupo Libro Grande, Tyler": { en: "La Viña Writing Workshop - Grupo Libro Grande, Tyler" }` | a flyer copy's title — the group keeps its own name (the machine wrote "Big Book, Tyler Group") |
| `"Grapevine Writing Workshop - Primary Purpose Group, Arlington": { es: "Taller de Escritura de Grapevine - Primary Purpose Group, Arlington" }` | the same for an English group name |
| `"Grapevine & La Viña Pricing Update - Effective January 1, 2027": { es: … }` | a Drive notes file (`notes/2026-10-01 Grapevine & La Viña Pricing Update - …pdf`) |
| `"Nuevos": { en: "Newcomers" }` … `"La alegría de vivir": { en: "The Joy of Living" }` | all of La Viña's editorial themes |
| `"XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la vida )": { en: … }` | a La Viña calendar event (the machine wrote "Xlii") |
| five entries for "Grapevine and La Viña — ways to carry the message" | a whole Drive bulletin post, by hand ([3.7.3](#373-a-bulletin-post-on-google-drive)) |

#### Odd input: what happens

Checked with the site's own code:

| You write | What happens |
|---|---|
| `"Foo": "Bar"` (no `{ es: … }`) | ignored; the Code check test `test_overrides_are_well_formed` fails |
| `"Foo": { fr: "Bonjour" }` | ignored (only `en` and `es`); the test fails |
| `"Foo": { ES: "Hola" }` (capital letters) | works on the site, but the Code check test fails: write `es` |
| `"Foo": { es: }` (nothing after the colon) | ignored; the test fails |
| `"Foo": { es: "" }` (empty quotes) | the Spanish page shows the **original** text, with no pill; the test fails |
| the same key twice | the **last** one wins, silently |
| two spellings with different fixes (`"Como rezo"` and `"Cómo rezo"`) | each exact spelling gets its own fix; any other spelling (`"COMO REZO"`) gets the later one; the test reports "two different fixes" |
| `Grupo Solo por Hoy, Longview: { en: Grupo Solo por Hoy, Longview }` (no quotes) | the value is **cut at the comma**: the English page shows "Grupo Solo por Hoy"; the test fails |
| `"Note": { es: Nota: Servicio }` (a colon in an unquoted value) | the **whole file** can't be read: nothing new is translated anywhere until it is fixed (saved translations stay); a **Settings problem** in the run summary |
| `"Say "hi"": { es: "Di hola" }` (a straight quote not written as `\"`) | the whole file can't be read (same as above) |
| a key of more than about 1,000 characters on one line | the whole file can't be read ("mapping values are not allowed here"): use the `? ` form |
| a key that differs from the site text by a dash, a quote mark or the final period | it simply never matches |

#### When the original changes

An override is tied to the exact text. If the source changes (a Drive file is renamed, a podcast fixes a typo, a
Drive document is edited), the new text no longer matches. It goes back to the machine — with the pill — until you
update the key. The file can hold both versions: that is why the Drive post's whole text is in it twice (before and
after one sentence changed for the January 2027 prices).

### 3.5 Fix a word everywhere: `data/translations/glossary.yml`

The glossary teaches the machine AA vocabulary. It has two lists:

```yaml
keep:                      # 1) names that are never translated (the same in both languages)
  - Grapevine
  - La Viña
  - Dear Grapevine         # letters section of the magazine
  - Fort Worth             # the model turned "Fort Worth" into "Valía la pena"
  - GVR

terms:                     # 2) fixed translations, used in both directions unless `only`
  - { en: "home group", es: "grupo base" }
  - { en: "sponsor", es: "padrino" }
  - { en: "sponsor", es: "madrina", only: en }          # only when translating INTO English
  - { en: "booth", es: "mesa informativa", only: es }   # only when translating INTO Spanish
  - { en: "the Fellowship", es: "la Comunidad", only: es, exact: true }
  - { en: "Season", es: "Temporada", exact: true }
```

Today: 59 names under `keep:` (magazines and their sections, AA and NETA, the committee's short names GV, LV, GVR,
RLV, ASL …, place names that are also English words, the co-founders, apps) and 199 `terms:` (Steps and Traditions,
service structure, Grapevine and La Viña service, meetings and podcasts). A term may only have the keys `en`, `es`,
`only` and `exact`.

#### How it matches

- Capitals and accents are ignored ("la vina" matches "La Viña"); whole words only; a space also matches a hyphen
  or an underscore ("home group" = "home-group"); `'` and `’` are the same.
- A `keep:` name written in ALL CAPITALS, and a term of up to 6 capital letters (GSR, DCM), only match in capitals.
  `exact: true` requires the same capitals.
- `only: es` = only when translating **into** Spanish; `only: en` = only **into** English.
- The longest phrase wins ("Twelve Traditions Checklist" beats "Twelve Traditions"). For the same phrase in one
  direction, the **first** entry in the file wins (`keep:` names before terms).
- Add plurals as their own lines ("sponsor" and "sponsors").

What the machine is given (checked with the real glossary; `XQ1`, `XQ2` … are protected slots put back afterwards):

| Text (direction) | The model sees | Put back as |
|---|---|---|
| "Dear Grapevine: letters from Fort Worth about my sponsor" (EN → ES) | `XQ1: letters from XQ2 about my XQ3` | Dear Grapevine · Fort Worth · padrino |
| "Ask your DCM or GVR about the booth" (EN → ES) | `Ask your XQ1 or XQ2 about the XQ3` | MCD · GVR · mesa informativa |
| "Ask your dcm about the Booth" (EN → ES) | `Ask your dcm about the XQ1` | lower-case "dcm" is **not** matched (capitals rule); Booth → mesa informativa |
| "Mi madrina me habló de la Comunidad" (ES → EN) | `Mi XQ1 me habló de la Comunidad` | madrina → sponsor (an `only: en` term) |
| "We love the Fellowship and its fellowship" (EN → ES) | `We love XQ1 and its XQ2` | la Comunidad (`exact`) · compañerismo |
| "Taller de Escritura en el Grupo Solo por Hoy" (ES → EN) with `- Grupo Solo por Hoy` added to `keep:` | `XQ1 en el XQ2` | Writing Workshop · Grupo Solo por Hoy |

Real results from the memory: "God Cookies [Season 3, Episode 11] - AA Grapevine Podcast" → "Galletas de Dios
[Temporada 3, Episodio 11] - AA Grapevine Podcast"; "Connections in the AA Fellowship [Season 2, Episode 2]" →
"Conexiones en la Comunidad de AA [Temporada 2, Episodio 2]".

#### Add a name or a term

1. Open [`data/translations/glossary.yml`](../data/translations/glossary.yml) → pencil.
2. A name: add a line under `keep:` (two spaces, a dash, a space), e.g. `  - Grupo Solo por Hoy`.
   A term: add a line under `terms:`, e.g. `  - { en: "literature table", es: "mesa de literatura" }`.
3. Commit to `main`.

On the next run, every saved translation (in that direction) whose original contains an added, removed or changed
phrase is thrown away and done again; the rest is kept.

> **Note:** the file's own header says changes apply "on the next daily run". In fact, saving the file starts a
> quick Website update run right away, and that run already re-translates (up to 40 minutes). A big change may need
> one or two more runs to finish; until then the texts not redone yet show in their **original language on both
> pages** (no pill) — their old translation was thrown away.

#### Glossary or override?

| You want | Use |
|---|---|
| a group's name, a place or a product never translated, wherever it appears | `keep:` |
| an AA word that the machine gets wrong everywhere ("Fellowship" came out as "Beca", a scholarship) | `terms:` (with `only:` when one direction needs another word) |
| one title or one sentence that reads badly | `overrides.yml` (the glossary's header says so too) |

#### Odd input

| You write | What happens |
|---|---|
| `only: spanish` (anything but `es` or `en`) | the term is **never used**; the test `test_glossary_is_well_formed` fails |
| a term without `es:` (or without `en:`) | skipped; the test fails |
| an extra key (`note: …`) in a term | the term still works; the test fails (use a `#` comment instead) |
| a YAML typo (a missing `}`, a tab) | the whole file can't be read: nothing new is translated until it is fixed; saved translations stay and are **not** thrown away; a **Settings problem** in the run summary |

### 3.6 The translation memory: `data/translations/cache.json`

Every translation the machine makes is saved here and reused, so a text is translated only once. One line per text:

```json
"0014276dbdaf7f2374e6bde7af2eaa9cc87c2a7c": {"s": "God Cookies [Season 3, Episode 11] - AA Grapevine Podcast", "t": "Galletas de Dios [Temporada 3, Episodio 11] - AA Grapevine Podcast", "v": "argos1.0-ct2/v6", "d": "en>es"},
```

`s` = the original, `t` = the translation, `v` = the engine version, `d` = the direction. The first entry, `_meta`,
keeps a snapshot of the glossary and the overrides, so the next run knows what changed. Today: 1,919 entries (1,513
English → Spanish, 406 Spanish → English), about 0.8 MB.

- An entry is used only when its engine version is the current one (`ENGINE_VERSION` in `translate.py`) and its
  original is exactly the text.
- The robot saves the file at the end of every run (even when a later step failed) and commits it. Unused entries are
  removed only after a complete, healthy run with nothing waiting. Since October 2026 a Settings problem (a skip
  date, a monthly event, a calendar feed, a price change, a `content/events` slip) no longer holds that clean-up back;
  an unreadable raw data file, or an unreadable `glossary.yml` / `overrides.yml`, still does.

> **Never edit `cache.json` by hand.**
> - Saving it alone does not rebuild the site (the robot's data files never start a run).
> - A hand-edited line still counts as a machine translation (the pill stays).
> - The robot's copy wins when both changed.
> - A JSON typo makes the whole memory unreadable. Since October 2026 the next run does not overwrite it: it moves
>   the file aside as `cache.json.bad-<UTC time>` (on GitHub's computer only; git still has the last good file),
>   starts a new, empty memory and reports it (the run summary's **Translation problems**, and a line on the
>   `/status/` translation card). Restore the file from its git history to keep the old translations;
>   otherwise everything is translated again (40 minutes per run, over several runs). If the file cannot even be
>   moved aside, it is left untouched and nothing new is translated that run.
>
> To redo **one** text, add an override. To redo **everything**, see [6.5](#65-re-translate-everything).

To look at the numbers on a PC: `python -m scripts.sync.translate --stats` (it only reads the file).

### 3.7 Make a bulletin post or an event bilingual by hand

#### 3.7.1 A bulletin post written on GitHub (`content/bulletin/*.md`)

Add your own words for the other language to the header:

| The file is written in … | Add | Ignored (the file's own language) |
|---|---|---|
| English (`lang: en`, or detected) | `title_es`, `summary_es` | `title_en`, `summary_en` |
| Spanish (`lang: es`, or detected) | `title_en`, `summary_en` | `title_es`, `summary_es` |

- `summary_es` is **both** the short Spanish preview (home page card, What's New, feed) **and** the whole Spanish text
  shown on `/es/bulletin/`. Write the complete text there.
- For more than one paragraph, a list or headings, write `summary_es: |` and the text on the lines below, each line
  indented **two spaces**. It keeps its paragraphs and lists, and the preview is made of its words without the
  Markdown marks.
- A **one-line** `summary_es` is used exactly as typed, in the text and in the preview (the preview stops after
  about 400 characters). Leave out `**bold**` and `[links](…)` on one line: the home card would show the marks as
  typed. Use the `|` block for those.
- Give the Spanish **as many headings** as the English, and each heading's link (`/bulletin/#<post>--<heading>`) finds
  its section on both pages.
- Put a value in double quotes when it contains `: ` or ` #`: `title_es: "Taller: Fort Worth"`. Without quotes,
  ` #` starts a note for people: `title_es: Grupo #1` would give just "Grupo". Quotes never hurt.

The real example, [`content/bulletin/2026-10-01-prices-change-january-1-2027.md`](../content/bulletin/2026-10-01-prices-change-january-1-2027.md)
(shortened):

```yaml
---
title: "Grapevine and La Viña prices change on January 1, 2027"
date: 2026-10-01
expires: 2026-12-31
pinned: true
lang: en
title_es: "Los precios de Grapevine y La Viña cambian el 1 de enero de 2027"
summary_es: |
  A partir del **1 de enero de 2027**, la suscripción anual a La Viña cuesta **$19.50** impresa …

  **Qué significa para tu grupo.** Si tu grupo compra libros o suscripciones …

  - Los precios de hoy y los nuevos, lado a lado: [Tienda: suscripciones y precios](/shop/#subscriptions)
---
From **January 1, 2027**, a yearly Grapevine subscription costs **$39.00** in print …
```

**What happens:** on `/es/bulletin/` the post shows the `title_es` and the `summary_es` text exactly as written
(Markdown kept), with no "Auto-translated" pill and no "Show original" box. The link `(/shop/#subscriptions)` opens
`/es/shop/#subscriptions` on the Spanish page. The home page card, What's New, `/es/feed.xml`, the search and the
Spanish half of the digest (`/es/digest/` and the e-mail) use the same words.

**What if you give only part of it?** (checked with the site's code)

| Header | Spanish title | Spanish text | "Auto-translated" on the Spanish page |
|---|---|---|---|
| no `_es` lines | machine | machine | yes |
| `title_es` only | yours | machine | **yes** — one machine-made field marks the whole item |
| `title_es` + `summary_es` | yours | yours | no |
| `title_en` in an English file | ignored → machine | machine | yes |

#### 3.7.2 An event written on GitHub (`content/events/*.md`)

The same keys, plus the place:

| Key | In an English file | Effect |
|---|---|---|
| `title_es` | your Spanish title | instead of the machine's |
| `summary_es` | your Spanish description | shown **instead of** the whole text below the header on `/es/events/` |
| `location_es` | the place in Spanish | only when the place itself needs other words; a place is **never** machine-translated |

(`title_en`, `summary_en`, `location_en` in a file written in Spanish.)

The real example, [`content/events/2026-10-26-lv-writing-workshop-tyler.md`](../content/events/2026-10-26-lv-writing-workshop-tyler.md)
(shortened: its `url:`, `flyer:` and `tags:` lines are left out):

```yaml
---
title: "La Viña Writing Workshop (in Spanish) — Tyler"
title_es: "Taller de Escritura de La Viña — Tyler"
start: 2026-10-26T19:00:00-05:00
end: 2026-10-26T21:00:00-05:00
location: "Grupo Libro Grande, 623 West Bow, Tyler, TX 75702"
lang: en
summary_es: "Taller en español para aprender a escribir tu historia para La Viña, en el Grupo Libro Grande de Tyler."
---
A Spanish-language workshop on writing your story for La Viña, hosted by Grupo Libro Grande in Tyler.
```

**What happens:** `/es/events/` shows "Taller de Escritura de La Viña — Tyler" with the Spanish description and the
address as written; `machine` is empty, so no pill. The same Spanish words go to the home page's "Próximos
eventos" (Upcoming events), `/es/monthly/`, `/es/events.ics`, `/es/search/` and the Spanish half of the digest.

**Places and "to be announced"** (checked with the site's code):

| Header | English page | Spanish page |
|---|---|---|
| `location: "Grupo Libro Grande, 623 West Bow, Tyler, TX 75702"` | the address | the same address (never translated) |
| `location: "Venue to be announced"` | Venue to be announced | **Lugar por anunciarse** (by itself) |
| `location: "Venue to be announced"` + `location_es: "Lugar por confirmar"` | Venue to be announced | Lugar por confirmar |

When the venue is confirmed, put the address in `location:` and delete `location_es:` (an address needs no
translation). If you forget, a left-over "to be announced" `location_es` is ignored (the address shows in both
languages), and the run summary lists it under **Settings problems** ("… Delete the location_es line."). More in
[Flyers and events](flyers-and-events.md).

> **Note:** an event with **no description** below the header but with a `summary_es` shows a description on the
> Spanish page and none on the English page. Write the English description too.

#### 3.7.3 A bulletin post on Google Drive

A Google Doc (or `.txt`, `.md`, `.docx`) in the panel folder's `bulletin/` folder has no header, so there is no
place for `title_es`. You have two choices:

**A. Hand-translate it in `overrides.yml`** — three entries: the title, the summary and the whole text.

1. Wait until the post is on the site (the sync must have read it).
2. Open `data/site/announcements.json` on github.com and find the post (its `"id"` starts with `drive:`). Copy:
   - `"title"` — the file name without its date and without `(pinned)`, `(until …)` or `(from …)` words;
   - `"summary"` — the first 400 characters of the text without Markdown marks, cut at a word, ending in "…";
   - `"extra"` → `"body_md"` — the whole text as Markdown.
3. Add three entries (form 8 above lets you paste the JSON strings as they are):

   ```yaml
   "Grapevine and La Viña — ways to carry the message": { es: "Grapevine y La Viña — formas de llevar el mensaje" }
   ? "A living list of simple ways members, groups and districts can support … magazine content on…"
   : { es: "Una lista viva de formas sencillas en que los miembros, los grupos y los distritos pueden apoyar … para que todos aprendamos." }
   ? |-
     A living list of simple ways members, groups and districts can support Grapevine and La Viña and carry the message. …

     # Why it matters
     …
   : es: |-
       Una lista viva de formas sencillas … llevar el mensaje. …

       # Por qué importa
       …
   ```

4. Commit. Result: `machine` is empty → `/es/bulletin/` shows your Spanish, no pill, no "Show original" box.

The real file does exactly this for "Grapevine and La Viña — ways to carry the message" (five entries: the title, two
spellings of the summary — older runs kept the `**` marks — and two versions of the whole text).

> **Note:** if someone edits the document on Drive later, the new text no longer matches and goes back to the
> machine until you update the keys. Keep the old entries too if the change may be undone.

**B. Post it on GitHub instead** (`content/bulletin/`), where `title_es` and `summary_es` sit in the same file
([3.7.1](#371-a-bulletin-post-written-on-github-contentbulletinmd)). See [Bulletin](bulletin.md).

#### 3.7.4 Drive files and flyers (titles only)

Every Drive file's **title** (its file name, see the table in [3.4](#where-to-copy-the-exact-original-by-kind-of-item))
is machine-translated unless `overrides.yml` has it. Today all 19 Drive files on the site have an override, so none
is marked "Auto-translated".

- **A group's name in a file name** is translated word for word ("Grupo Solo por Hoy" came out as "Group Only for
  Today"). Add an override with the group's name unchanged in both languages, or add the name to the glossary's
  `keep:` list once for all files:

  ```yaml
  # overrides.yml, "Spanish → English" part (the file name without .jpg)
  "Taller de Información de La Viña - Grupo Solo por Hoy, Longview": { en: "La Viña Information Workshop - Grupo Solo por Hoy, Longview" }
  ```

- **The words inside a flyer, a PDF or a slide deck are never translated** — only the title. A flyer that must speak
  both languages has to have both on the picture itself.
- More on naming: [Drive panel folder](drive-panel-folder.md), [Flyers and events](flyers-and-events.md),
  [Photos, slides and reports](photos-slides-reports.md).

#### 3.7.5 Settings texts (`config/site.yml`)

Some texts are written in the settings file, in both languages. `config/site.yml` is an ordinary file: the everyday
login can edit it. Details: [Settings](settings.md).

| Key | Shows | Effect |
|---|---|---|
| `recurring_events:` → `title` + `title_es`, `summary` + `summary_es` | Events page, home, calendar files, monthly toolkit | both given → your words, no pill; only one given → the other is machine-translated once and marked (an override for that exact text also works) |
| `meeting:` → `note` (+ optional `note_es`) | the committee meeting cards | the default note has built-in Spanish; a changed `note` without `note_es` is machine-translated and marked. Write `note_es` to fix it — an override does **not** work here (see the note below) |
| `site:` → `title` / `title_es`, `committee` / `committee_es`, `area` / `area_es`; `meeting:` → `chair_title` / `chair_title_es` | headers, meeting titles | Spanish pages use the `_es` value |
| `lavina_weekly_open:` → `title_es` + `title_en`, `summary_es` + `summary_en` | La Viña's weekly open meeting (its card at `/meetings/#weekly-open`) | the English words are yours, not the machine's |
| `phone_access:` → `numbers:` → `city_es` | `/accessibility/#phone` | the city's name on the Spanish page ("Nueva York") |

Real result: the CityWide Dallas booth (`title_es: "Mesa de GV/LV en CityWide Dallas"`) shows on `/es/events/` as
"Mesa de GV/LV en CityWide Dallas", with no pill.

> **Note:** a quirk of `committee_meetings` in `build_data.py`: when `overrides.yml` has the meeting `note`, the code
> treats the answer as "not translated" and puts the **English** note on the Spanish cards (no pill). So for the
> meeting note, always write `note_es` in `config/site.yml`.

#### 3.7.6 Do not write both languages in one text

If one post or description holds both languages, the result depends on the mix (from the site's code):

- about half and half → the English sentences are translated and the Spanish ones are kept: the Spanish page shows
  the Spanish **twice** (the translation, then your own), with the pill;
- mostly Spanish → the whole text counts as "already Spanish" and is shown as it is on the Spanish page, English
  sentences included.

Write one language in the text and the other in `title_es` / `summary_es`.

---

## 4. What happens next

### Which edit starts which run

[`update.yml`](../.github/workflows/update.yml) ("Website update") rebuilds the site after a push to `main`, except for
documentation and the robot's own data. [`check.yml`](../.github/workflows/check.yml)
("Code check (tests and test build)") runs the tests and a test build; it publishes nothing.

| You commit … | Starts Website update? | Starts Code check (tests and test build)? |
|---|---|---|
| `data/translations/overrides.yml` | **yes** | yes |
| `data/translations/glossary.yml` | **yes** | yes |
| `data/translations/cache.json` | no (robot's data) | no |
| `src/_i18n/*.json` | **yes** | yes |
| a template, `eleventy.config.js`, `eleventy/filters/*.js` | yes | yes |
| `scripts/sync/translate.py`, `build_data.py` … | yes | yes |
| `content/bulletin/*.md`, `content/events/*.md` (with `title_es` …) | yes | yes |
| `content/bulletin/README.md`, `content/events/README.md` | no | yes |
| `config/site.yml` (`title_es`, `summary_es` …) | yes | yes |
| `docs/*.md`, the root `README.md`, this `how-to/` folder | no | no |

### What the run does, and how long it takes

A push starts a **quick** run: it reads Google Drive, the bulletin, the podcasts, the writers archive files and the
daily quote, then rebuilds
**all** the site data — so a new override or glossary line applies to every item on the site, not only to the
quick sources. It translates for up to 40 minutes, commits the data (commit message
`chore(data): content sync after settings/content change …`), builds the site with `I18N_STRICT=1` and publishes it.

- Usually **about 3 minutes** from your commit to the live page (the run does not test again: since October 2026 the
  glossary and the overrides are the committee's files, not code), plus up to 10 minutes before every visitor sees
  it. A change of the strings in `src/_i18n/` is code: its run tests it first, about 5 minutes. A glossary change
  that redoes many texts takes longer; what does not fit is finished by the next runs.
- Runs never overlap: a second commit made meanwhile waits its turn, then runs.
- Every other run (the morning refresh, the midday and evening refreshes, the nightly full update) also applies your
  fixes. The morning refresh gives new translations only 5 minutes, so it may leave texts waiting. (The nightly,
  midday and evening schedules are set about 4 hours early on purpose, because GitHub starts scheduled runs late — see
  [Automation and troubleshooting](automation-and-troubleshooting.md).)

### Where to watch

GitHub → **Actions** → **Website update** → the newest run → **Summary**:

- `Translations: 1919 cached · 0 new this run · 0 waiting for the next run`
- **Settings problems** — a YAML typo in `glossary.yml` or `overrides.yml`, with the line and column.
- Yellow warnings **Translation models missing** or **Translation is not working** ([Troubleshooting](#7-troubleshooting)).
- A failed **Build the website** step — a missing `src/_i18n` key, a JSON typo, or a language missing in a bilingual
  settings file; the live site stays as it was.

The **Code check** run shows a red ✗ when a test fails (a malformed entry, a missing language, different
placeholders, a pinned wording). For `glossary.yml` and `overrides.yml` that is all: *Website update* leaves the
tests that judge those files to the Code check (`CONTENT_TESTS`, since October 2026) and publishes, so a translation
problem never stops the site from updating — fix the file soon. A failing test after a change of the **strings in
`src/_i18n/`** (code) does stop that change: Website update is red with *Tests failed — not published* and the site
keeps the version before ([Automation and troubleshooting §14.10](automation-and-troubleshooting.md#1410-tests-failed--not-published)).

---

## 5. Where it shows on the website

### Pages and files that change with the language

| Where | English | Spanish | What is translated there |
|---|---|---|---|
| Home | `/` | `/es/` | bulletin cards, "Upcoming events", podcast and video, magazine stories, published writers, photo album names |
| Bulletin | `/bulletin/` | `/es/bulletin/` | post titles and whole texts |
| Events | `/events/` | `/es/events/` | event titles, descriptions, "to be announced" places |
| Portfolio | `/portfolio/` | `/es/portfolio/` | Drive file titles |
| Photos | `/photos/` | `/es/photos/` | album names (Drive folder names) |
| Listen · Watch · Read · Published | `/listen/` · `/watch/` · `/read/` · `/published/` | `/es/…` | episode, video and story titles and summaries |
| Library · Shop · Instagram | `/library/` · `/shop/` · `/instagram/` | `/es/…` | PDF titles, Book of the Month, captions |
| Contribute · Monthly toolkit | `/contribute/` · `/monthly/` | `/es/…` | editorial themes, issue themes |
| What's New · Search · Digest | `/whats-new/` · `/search/` · `/digest/` | `/es/…` | everything new; the search index is per language |
| News feed | `/feed.xml` | `/es/feed.xml` | item titles and texts |
| Calendar file | `/events.ics` | `/es/events.ics` | event titles and descriptions |
| Monthly digest e-mail | one bilingual e-mail: each section in English, then in Spanish | (same e-mail) | titles of everything listed |

### How a machine translation is marked

| Mark | Where | Its words (key) |
|---|---|---|
| A small pill with a languages icon: **Auto-translated** / **Traducción automática** (tooltip: "Translated automatically from the original language …") | bulletin posts, event cards, home cards, What's New, `/watch/`, `/listen/`, `/instagram/`, `/portfolio/`, `/library/`, `/shop/`, `/published/`, `/contribute/`, the monthly pages, `/about/`, `/digest/`, search results | `common.auto_translated`, `common.auto_translated_help` |
| **Show original** / **Ver el original** box under a machine-translated bulletin post, with the original title and text | `/bulletin/`, `/es/bulletin/` | `committee.ann.show_original`, `lang.en` / `lang.es` ("Originally in English") |
| A small **EN** / **ES** pill: the item's original language differs from the page | cards across the site | `lang.en`, `lang.es` |
| One note for a group instead of a pill per story ("Titles auto-translated from Spanish — the stories are in Spanish") | the home page's magazine block, `/read/`, `/published/` (`#archive`: over the Texas writers archive's list, while a row with a machine-translated title or subtitle is shown — "Titles translated automatically from Spanish — originals in italics"; such a row also has a small languages icon) | `home.mag_mt_from_en` / `_es`, `read.mt_note_en` / `_es` |
| `Auto-translated` in small print | each machine-translated item of the news feed | `common.auto_translated` |
| "Some titles were translated automatically." / "Algunos títulos se tradujeron automáticamente." | the end of the English half / of the Spanish half of the digest e-mail (only when that half lists a machine translation) | the e-mail's own table in `send_digest.py` |

An item written by hand (`title_es` + `summary_es`, or fully covered by overrides) gets no "Auto-translated" pill, no
"Show original" box and no e-mail note. The Events page and What's New also leave out the EN / ES pill for the
committee's own posts and events (repo files, recurring events) whose other language is written by hand.

### The status page

`/status/` (`/es/status/`) has a **Machine translation** card: how many translations are saved, how many texts are
still waiting ("they are translated on the next update"), how many machine translations looked wrong and were not
used, and how many glossary entries there are. Since October 2026, when the translation memory could not be read or
a model was refused (below), it also says calmly "The last update could not translate everything as usual, so some
new texts may stay in their original language for now. Everything translated before stays as it is.", with the raw
message under it.

> **Note:** `/status/` does not show a YAML typo in `overrides.yml` or `glossary.yml`. Only the Actions run summary
> does (**Settings problems**).

**A model that is not the expected one is refused** (since October 2026). Each downloaded translation model is
checked against its SHA-256 fingerprint (`MODEL_SHA256` in `scripts/sync/translate.py`). One that does not match is
**not installed** (it used to be installed with a warning): that direction stays untranslated, the reason shows on
`/status/` and in the run summary — since October 2026 under its own heading, **Translation problems**, with a
yellow ⚠ *Translation problem* (a model whose download failed is listed there too, and simply tried again by the next
run; an unreadable translation memory set aside as well) — and `python -m scripts.sync.translate --download` prints
it next to `MISSING`. If the model's publisher really uploaded a new file, check it and put its fingerprint in
`MODEL_SHA256`.

---

## 6. Going further: change the code

Search strings below are exact words to find in the file (GitHub: open the file, press `Ctrl`+`F`; or the repo
search box). Line numbers are not given on purpose: they change.

### 6.1 Map of the code

| To … | File | Look for |
|---|---|---|
| change or add a button, menu or heading text | [`src/_i18n/<area>.json`](../src/_i18n/) + the page template in `src/pages/` | the key, e.g. `"committee.events.upcoming"` |
| see how a key is looked up, and the strict switch | [`eleventy.config.js`](../eleventy.config.js) | `function translateKey`, `I18N_STRICT`, `function loadI18n` |
| see how a page picks a content field's language | [`eleventy.config.js`](../eleventy.config.js) | `function pickLang` (the `tx` filter), `addFilter("machineFor"` |
| change how or where the pill shows | [`src/_includes/macros/ui.njk`](../src/_includes/macros/ui.njk); several pages write the same pill themselves | `macro autoNote` (and `macro langPill` for EN / ES); search `src/pages/` and `src/assets/js/` for `auto-note` |
| choose which content fields are translated | [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) | `def text_fields`, `LABEL_FIELDS`, `TITLE_FIELDS` |
| change how own words, places and machine flags are put together | [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) | `class I18n` → `def apply`, `def pair`, `def respell`; `def own_words`; `def location_pair`, `TBA_LOCATION` |
| add a hand-written header key for posts and events | [`scripts/sync/announcements.py`](../scripts/sync/announcements.py) | `def own_translations`, `def parse_event` (`location_`) |
| change how a repo file's `lang:` is read | [`scripts/sync/announcements.py`](../scripts/sync/announcements.py) | `def pick_lang` |
| change which Drive names count as Spanish | [`scripts/sync/drive.py`](../scripts/sync/drive.py) | `_SPANISH_HINTS`, `def lang_prior` |
| change override matching | [`scripts/sync/translate.py`](../scripts/sync/translate.py) | `class Overrides`, `def _norm_key` |
| change glossary matching | [`scripts/sync/translate.py`](../scripts/sync/translate.py) | `class Glossary`, `def _term_regex` |
| change the order of the steps | [`scripts/sync/translate.py`](../scripts/sync/translate.py) | `def _quick`, `def _units`, `def _translate_segments_masked` |
| change the built-in Spanish word rules ("vacaciones" → "fiestas", "reunión de negocios" → "reunión de trabajo", "altavoces" → "oradores") | [`scripts/sync/translate.py`](../scripts/sync/translate.py) | `_POST_EDITS_ES`, `def post_edit_es` (re-applied to the saved translations on every run) |
| re-translate everything | [`scripts/sync/translate.py`](../scripts/sync/translate.py) | `ENGINE_VERSION` ([6.5](#65-re-translate-everything)) |
| change where the models are downloaded from | [`scripts/sync/translate.py`](../scripts/sync/translate.py) | `MODEL_URLS` (the Actions cache key follows it, so a change downloads them again) |
| change the translation time budget | [`.github/workflows/update.yml`](../.github/workflows/update.yml) step "Decide what to sync"; default in `build_data.py` | `translate=`; `--translate-minutes`, `GV_TRANSLATE_MINUTES` |
| change the run summary's translation line | [`.github/workflows/update.yml`](../.github/workflows/update.yml) step "Write run summary" | `**Translations:**` |
| change the status page card | [`src/pages/status.njk`](../src/pages/status.njk); words in `community.json` | `community.status.tr_` |
| change the language suggestion card | [`src/_includes/partials/lang-banner.njk`](../src/_includes/partials/lang-banner.njk) | `community.banner.` |
| change the language switch | [`src/_includes/partials/header.njk`](../src/_includes/partials/header.njk); filters in `eleventy.config.js` | `altLangUrl`, `lurl`, `data-lang-switch` |
| make a new page in both languages | its template's front matter | `pagination: { data: languages, size: 1, alias: lang }` and `permalink: "{{ '/' if lang == 'en' else '/es/' }}<name>/index.html"` |
| change the digest e-mail's words | [`scripts/notify/send_digest.py`](../scripts/notify/send_digest.py) | `T = {` |
| see how the presentations decide that a theme's English is hand-written (they read `overrides.yml` themselves) | [`eleventy/filters/presentations.js`](../eleventy/filters/presentations.js) | `function handEnglish`, `machineGloss` |

### 6.2 Example: add a new string with a value

1. In `src/_i18n/committee.json`, next to the other `committee.events.*` keys:

   ```json
   "committee.events.count_note": {
     "en": "{n} upcoming events",
     "es": "{n} próximos eventos"
   },
   ```

2. In the template (for example `src/pages/events.njk`), where it should show:

   ```njk
   <p class="text-sm text-muted">{{ "committee.events.count_note" | t(lang, { n: upcoming | length }) }}</p>
   ```

3. Commit both files **together**. A template that names a key that is not in the files stops the GitHub build.
4. Run `python -m unittest tests.test_i18n_keys` (both languages, same placeholders, one file per key).

### 6.3 Example: change the "Auto-translated" words everywhere

1. `src/_i18n/common.json`:

   ```json
   "common.auto_translated": {
     "en": "Machine translation",
     "es": "Traducción automática"
   },
   ```

   This changes the pill on every page, the search results and the news feed's small print.
2. The digest e-mail has its own copy: in `scripts/notify/send_digest.py`, search for `"machine":` — there is one in
   the `"en"` part of the `T` table ("Some titles were translated automatically.") and one in the `"es"` part
   ("Algunos títulos se tradujeron automáticamente."). Change both if you want the e-mail to match.
3. The workshop presentations write their own "(auto-translated)" after a machine-made English gloss:
   `auto_translated` in the `EN` table of `src/assets/js/presentations-core.js` (English only).
4. Run `python -m unittest discover -s tests`.

### 6.4 Example: teach the site a Spanish word for Drive names

Photos named by a camera (`IMG_1234.jpg`) give no language clue, so the folder decides. In
`photos/Asamblea 2027/`, "asamblea" is not a hint word: the photos count as English, and the album name
"Asamblea 2027" is "translated" from English (the English page shows it unchanged). An override cannot help, because
the site translates in the wrong direction.

Add the words to `_SPANISH_HINTS` in [`scripts/sync/drive.py`](../scripts/sync/drive.py), **without accents and in
lower case** (names are compared that way):

```python
_SPANISH_HINTS = {"informe", "informes", "reporte", "reportes", "nota", "notas", "minuta", "minutas", "acta",
                  # … the words already there …
                  "inscripcion", "inscripciones", "la vina", "lavina", "espanol",
                  "asamblea", "asambleas", "aniversario"}
```

After the next run, the album counts as Spanish and is translated Spanish → English; an override such as
`"Asamblea 2027": { en: "Assembly 2027" }` then works. A clearly English file name in such a folder still comes out
English (the title check decides when it is clear); a short, unclear one follows the folder.

Then run `python -m unittest discover -s tests`. The quicker fix without code: name the folder in a clearly Spanish
way ("Asamblea de Otoño 2027").

### 6.5 Re-translate everything

Only after a change to the translation code itself (for wording, use overrides or the glossary). Either:

- change `ENGINE_VERSION` in [`scripts/sync/translate.py`](../scripts/sync/translate.py) (for example
  `"argos1.0-ct2/v6"` → `"argos1.0-ct2/v7"`) and add a comment line above it saying what changed; or
- delete `data/translations/cache.json`.

> **Warning:** then no saved translation counts any more. About 1,900 texts are translated again, 40 minutes per run,
> newest and most visible first. Until a text is redone it shows in its **original language on both pages** (no
> pill). It can take a few runs (or a day) to finish.

### 6.6 Example: translate one more field

Fields are listed in `def text_fields` in `build_data.py`. Each entry is `(field name, original text, is Markdown,
source language or None)`. The Drive photo album is a good pattern to copy:

```python
    album = ex.get("album")
    if it.get("source") == "drive" and isinstance(album, str) and clean_text(album):
        a = clean_text(album)
        fields.append(("album", a, False, T.detect_language(a, it.get("lang") if it.get("lang") in LANGS else "en")))
```

A new field appears in the site data as `i18n.<field>` (and counts for `machine`). Show it in a template with
`{{ item | tx("<field>", lang) }}`. If it is a title, add its name to `TITLE_FIELDS` (English Title Case for
machine-made English). Overrides and the glossary work for it automatically.

### 6.7 Test on a PC

On a PC with the repository, Python and Node set up ([Automation and troubleshooting](automation-and-troubleshooting.md)):

```bash
# all the offline tests (what the Code check runs)
python -m unittest discover -s tests

# just the translation-related ones
python -m unittest tests.test_i18n_keys tests.test_translate tests.test_editorial -v

# numbers of the translation memory (only reads it)
python -m scripts.sync.translate --stats

# try a translation (the first time it downloads the model it needs, English → Spanish, about 90 MB, into .cache/models)
python -m scripts.sync.translate "Welcome, new GVRs!" --to es

# download both models at once (about 175 MB)
python -m scripts.sync.translate --download
```

The translation command prints `[en->es, …] …` and changes no file of the repository (the models go to
`.cache/models`, which is never committed). Never add `--save`: it writes into `cache.json`, which belongs to the robot.

To build the site the way GitHub does, so a missing key stops the build instead of showing the raw key:

```powershell
$env:I18N_STRICT = "1"; npx @11ty/eleventy
```

(In Git Bash: `I18N_STRICT=1 npx @11ty/eleventy`.) The site is written to `_site/`, which is never committed.

---

## 7. Troubleshooting

Errors are reported in three places: the **Actions** run summary of Website update (translation counts, **Settings
problems**, warnings), the **Code check** run (red ✗ when a test fails), and `/status/` (translation counts only).

### My override does not show

| Cause | How to tell | Fix |
|---|---|---|
| The run has not finished yet | Actions shows it running or queued (runs wait their turn) | wait; then reload the page (your browser may show a saved copy: reload once more) |
| The key is not exactly the original: a hyphen for a dash, ' for ’, a missing or extra final period | compare with `data/site/<file>.json` | copy the text from the site data ([3.4](#where-to-copy-the-exact-original-by-kind-of-item)) |
| The wrong language: `es:` for a Spanish original, or `en:` for an English one | the item's `"lang"` in `data/site/<file>.json` | an English original needs `es:`, a Spanish one `en:` |
| The site took the text for the other language (a wrong `lang:`, an unclear Drive name) | `"lang"` in the site data is not what you expect | fix `lang:` in the repo file; rename the Drive file or folder; or [6.4](#64-example-teach-the-site-a-spanish-word-for-drive-names) |
| The file cannot be read (a YAML typo) | the run summary: **Settings problems: data/translations/overrides.yml could not be read (…, line N, column M)** | fix that line, commit again. Meanwhile nothing new is translated anywhere; saved translations stay |
| The value was cut (an unquoted comma) | the Code check test `test_overrides_are_well_formed` fails | quote both sides |
| The same key appears twice in the file (the last one wins, silently — no test can see it) | search the file for the key | keep one entry per key |
| The original changed at the source | the site data shows a different text | update the key (keep the old one if it may come back) |
| You fixed only a part, and expected the pill to go | the text has a "[Season …]" or "(Spanish)" tail, or you fixed one sentence | normal: a part fix leaves the pill; fix the whole text to remove it |
| A part fix while the models are missing | the warnings below | it waits for the models; a whole-text fix works without them |

### The "Auto-translated" pill is still there

- Another field of the same item is still machine-made (one machine field marks the whole item). For a repo post or
  event: give **both** `title_es` and `summary_es`. For other items: fix the summary too.
- The fix covers only a part of the text (see above).

### The Spanish page shows English, with no pill (or the other way round)

| Cause | Fix |
|---|---|
| The text is **waiting** (time budget used up, or the morning refresh's 5 minutes) | wait for the next run; the run summary says "N waiting for the next run" |
| The item's language is wrong (an English text marked `lang: es` is passed through untouched) | fix `lang:`; `lang: Spanish` is not understood — write `es` |
| The guard threw a bad machine result away (that sentence keeps its original words) | `/status/` counts them for the latest run ("looked wrong and were not used"); add an override |
| The text was taken as already written in the other language (a bilingual caption) | an override, or write one language per text ([3.7.6](#376-do-not-write-both-languages-in-one-text)) |
| The models are missing | see the warnings below |

### Warnings "Translation models missing" or "Translation is not working"

- **What it means:** the two offline models (about 175 MB, from argos-net.com) could not be downloaded, or no text
  could be translated although some were waiting. New titles stay in their original language; everything already
  translated, and every whole-text override, still works. Texts redone because of a glossary change or a part fix
  made meanwhile also wait, in their original language.
- **What to do:** run **Website update** again by hand (Actions → Website update → **Run workflow**). If it lasts
  more than a few days, open the "Sync sources and translate" log of the run and look for "could not install translation model".
  The download address is `MODEL_URLS` in `translate.py`. To force a fresh download, delete the `translation-models-…`
  entry under **Actions → Caches**, then run the workflow again.

### Many texts "waiting for the next run"

Normal after a glossary change, after `ENGINE_VERSION` changed, or on the first runs of a new repository: 40 minutes
per run, the most visible texts first. It goes down by itself over the next runs.

### A raw key such as `committee.events.view_flyr` on the page, or the build failed

| Symptom | Cause | Fix |
|---|---|---|
| A local build shows `committee.events.view_flyr` as text | the key is in no `src/_i18n` file | add the entry, or fix the spelling in the template |
| Website update failed at **Build the website**: `Missing i18n key: …` | the same, on GitHub (strict) | same; the live site stays as it was until the next good build |
| The build failed with `Expected ',' or '}' after property value in JSON …` or `Expected double-quoted property name in JSON … (line N column M)` | a JSON typo in the `src/_i18n` file you just edited (a missing comma; a comma after the last entry) | fix the comma or quote at that line |
| The build failed with a message starting `[carry]`, `[orientation]`, `[history]`, `[expenses]` or `[presentations]` | a problem in that bilingual settings file, for example one language missing | add the missing `en` or `es` ([Settings](settings.md), [Presentations](presentations.md)) |

### The Code check is red after a wording change

- `test_english_and_spanish` — one language is empty or missing.
- `test_the_same_placeholders` — a `{placeholder}` is in one language only.
- `test_no_key_in_two_files` — the same key in two files.
- `test_overrides_are_well_formed`, `test_glossary_is_well_formed` — a malformed entry ([Odd input](#odd-input-what-happens)).
- `tests/test_editorial.py` "themes left to the machine translation" — one of La Viña's themes lost its `en:` line
  in `overrides.yml` (renamed or deleted).
- A test that pins words (for example `tests/test_bulletin.py`, `tests/test_events_feeds.py`,
  `tests/test_recurring_events.py`) — update it to your new words in the same commit, or keep the old words.

### Other surprises

| Symptom | Cause | Fix |
|---|---|---|
| A group's or a place's name was translated ("Group Only for Today") | the machine translates names word for word | `keep:` in the glossary, or an override for the title |
| In a short title like "Spring Assembly - Tyler", the first words stay English on the Spanish page | one or two capitalized words before a dash are taken for a member's name ("Anselmo M. - …") and are never translated | an override for the whole title; or `title_es` for a repo event; or put three or more words before the dash |
| The Spanish preview on the home page shows `**` marks | a one-line `summary_es` with Markdown | write it as a `summary_es: \|` block |
| The Spanish page shows the Spanish part twice | both languages in one text | [3.7.6](#376-do-not-write-both-languages-in-one-text) |
| The Spanish event has a description, the English one none | `summary_es` without an English text below the header | write the English description |
| `nav.switch_lang` looks swapped in `common.json` | on purpose ([3.2](#keys-that-look-inverted-do-not-fix-them)) | leave it |
| The digest e-mail still uses the old words | the e-mail has its own copy | edit `send_digest.py` too |

---

## 8. Good practice and AA principles

- **Everything here is public.** `overrides.yml`, `glossary.yml`, `cache.json`, the `src/_i18n` files and the content
  files sit in a public repository, like everything in the Drive panel folder. Never put private words, personal
  e-mail addresses or phone numbers in them. The memory only ever holds texts that are already on the site.
- **Anonymity.** No full names in a translation either: members appear by first name and last initial, as in the
  glossary's `Bill W.` and `Dr. Bob`. The site protects "First name X." names so the machine does not change them;
  do the same by hand.
- **Attraction, not promotion.** Keep the tone of the original: plain, warm, informative. A hand translation is not
  the place to add sales words.
- **Use the Fellowship's own words.** La Viña says *padrinazgo* (the glossary's choice for "sponsorship"), *RLV* and
  *GVR*, *Libro Grande*, *Doce Pasos*. Quotes from AA literature take the official wording of the other language's
  edition, not a back-translation (the overrides file does this for Big Book and Twelve and Twelve quotes, with the
  English-edition page numbers).
- **A group's name is its own.** "Grupo Solo por Hoy" stays "Grupo Solo por Hoy" on the English page.
- **Fix at the right level.** One text → override. A word everywhere → glossary. Your own post → `title_es` /
  `summary_es`. Never hand-edit `cache.json`.
- **Nothing leaves GitHub.** The models run inside GitHub Actions; no text goes to an outside translation service.
- **Who can do this.** The everyday login (MKP715, write access) can edit every file in this guide and run the
  workflows. The admin account (NETA65) is only needed for repository settings and secrets, which translation does
  not use.

---

## 9. See also

- [How-to index](README.md) — the big picture and every guide
- [Drive panel folder](drive-panel-folder.md) — folders, names and what becomes public
- [File types](file-types.md) — what each kind of file becomes
- [Flyers and events](flyers-and-events.md) — flyer names, `content/events/` files, places, recurring events
- [Bulletin](bulletin.md) — Drive and GitHub bulletin posts
- [Photos, slides and reports](photos-slides-reports.md) — Portfolio and photo albums
- [Presentations](presentations.md) — the web presentations and their `{ en, es }` card texts
- [Settings](settings.md) — `config/site.yml` and the other bilingual settings files
- [E-mail and alerts](email-and-alerts.md) — the monthly digest e-mail and its word table
- [Automatic sources](automatic-sources.md) — podcasts, videos, magazines, PDFs, shop
- [Pages and code](pages-and-code.md) — every page, its template and its data
- [Automation and troubleshooting](automation-and-troubleshooting.md) — workflows, run summaries, running things on a PC
- [Booth display](booth.md) — the booth display: its slides are written in both languages by hand
  (`content/booth/booth.csv`), and nothing in it is machine-translated except what it takes from the site's data
- Repository files: [overrides.yml](../data/translations/overrides.yml), [glossary.yml](../data/translations/glossary.yml),
  [src/_i18n/](../src/_i18n/), [translate.py](../scripts/sync/translate.py), [build_data.py](../scripts/sync/build_data.py),
  [announcements.py](../scripts/sync/announcements.py), [drive.py](../scripts/sync/drive.py),
  [content/bulletin/README.md](../content/bulletin/README.md), [content/events/README.md](../content/events/README.md),
  [README §5 "Fixing a translation"](../README.md#5-fixing-a-translation), [docs/OPERATIONS.md](../docs/OPERATIONS.md),
  [docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md)
