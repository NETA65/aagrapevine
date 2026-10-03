# Presentations: the four web slide decks on /orientation/

This guide is about the four presentations on the GVR / RLV 101 page: the files in
[`config/presentations/`](../config/presentations/), how to edit them, and what each change does on the website.
The committee's own deck-writing guide is [`config/presentations/README.md`](../config/presentations/README.md).
Read it too. This guide repeats its rules where you need them, adds what the code really does, and shows where to
change the code.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start: change the words on a slide](#2-quick-start-change-the-words-on-a-slide)
3. [Full reference with examples](#3-full-reference-with-examples) — the files, versions, blanks, slides, layouts,
   notes, live facts, tokens, dates, handouts, the checker, common edits, presenting, printing, presenters' own
   versions and Reset, offline use, the JSON file
4. [What happens after you save](#4-what-happens-after-you-save)
5. [Where it shows on the website](#5-where-it-shows-on-the-website)
6. [Going further: change the code](#6-going-further-change-the-code)
7. [Troubleshooting](#7-troubleshooting)
8. [Good practice and AA principles](#8-good-practice-and-aa-principles)
9. [See also](#9-see-also)

---

## 1. What this is

The GVR / RLV 101 page has a "Presentations" section with four cards: three workshops and the committee's monthly
meeting. Each card is made from **one YAML text file** in `config/presentations/`. Every build turns each file into
a slide show that opens in a pop-up player, with speaker notes, a presenter view, shorter versions, four ways to
print, and facts that stay current by themselves (meeting dates, story deadlines, prices, events). Presenters can
make their own version of a deck; it stays on their own device.

**Where it shows** (full addresses start with `https://neta65.github.io/aagrapevine`):

| What | English | Spanish |
|---|---|---|
| The four cards | `/orientation/#presentations` | `/es/orientation/#presentations` |
| One card | `/orientation/#pres-information-workshop` | `/es/orientation/#pres-information-workshop` |
| Open a deck straight away | `/orientation/?present=information-workshop` | `/es/orientation/?present=information-workshop` |
| The file the player reads | `/orientation/presentations/information-workshop.json` (one file per deck, the same for both languages) | — |
| "Present on the web" on each PowerPoint copy | `/portfolio/` (Slides tab) | `/es/portfolio/` |

More detail in [section 5](#5-where-it-shows-on-the-website).

**What this is not**

- The six short GVR / RLV 101 sessions on the same page (`/orientation/magazines/` …) come from
  `config/orientation.yml`. See [Settings](settings.md).
- The PowerPoint copies (`.pptx`) in the Drive folder `2027-2028_Panel77_GVLV/slides` are separate, fixed snapshots,
  made on October 1, 2026. Changing a YAML file never changes them, and changing them never changes the web decks.
  The card links to them as "PowerPoint copy".
- The booth display on `/about/#booth` is a different thing: a show that plays by itself at the committee's table,
  made from `content/booth/booth.csv`, the Drive booth folder and the site's live data (some of the same live facts:
  events, themes, prices, meetings). See [Booth display](booth.md).

**Language.** The slides and the notes are in English (the owner's decision: every file must say `lang: "en"`). On
the Spanish page the cards, buttons and menus are in Spanish, each card shows "Presentación en inglés", and the
player adds "(en inglés)".

**Who can do it.** Editing these files needs only write access to the repository (the MKP715 login is enough).
Nothing in this guide needs the NETA65 admin account.

---

## 2. Quick start: change the words on a slide

This is the most common edit: fix a word, a sentence or a title.

1. On GitHub, open the folder `config/presentations/` and click the file of the presentation
   (the four files are listed in [3.1](#31-the-four-files)).
2. Click the pencil icon (**Edit this file**).
3. Click inside the text and press **Ctrl+F**. Type a few words you see on the slide; the title is easiest.
4. Change the text **between the double quotes**. Do not change the slide's `id:` line, and keep the spaces at the
   start of every line exactly as they are.
5. Click **Commit changes…** → **Commit changes**. (For a bigger change, choose "Create a new branch for this commit
   and start a pull request" instead: see [4](#4-what-happens-after-you-save).)
6. Wait a few minutes. In the **Actions** tab, the run "Update & Deploy" should get a green ✓. Then open the deck,
   type the slide's number and press Enter.

**Example.** In `orientation-workshop.yml`, find `Why we are here`:

```yaml
  - id: "why-we-are-here"
    layout: "columns"
    style: "cards"
    eyebrow: "Welcome"
    title: "Why we are here"
```

Change only the title:

```yaml
    title: "Why we are here today"
```

What happens: a few minutes later, slide 5 of the GVR and RLV Orientation Workshop reads "Why we are here today",
on `/orientation/?present=orientation-workshop` and on `/es/orientation/?present=orientation-workshop` (the slide is
English on both), in every printout, and in `orientation-workshop.json`. A presenter who had edited this slide on
their own device sees "Changed since you edited it" and chooses the new version or theirs
([3.19](#319-what-presenters-can-change-on-their-own-device)). Everyone else simply sees the new title.

**Check before you save (optional, on the PC).** From the repository folder, in PowerShell:

```powershell
.venv\Scripts\python.exe tests\test_presentations.py config\presentations\orientation-workshop.yml
```

It prints `config\presentations\orientation-workshop.yml: OK`, or the number of problems and one line per problem
with the slide's number and id. If you edit on GitHub only, the same check runs by itself after you commit
([4](#4-what-happens-after-you-save)).

---

## 3. Full reference with examples

### 3.1 The four files

| File | Card title (English / Spanish) | `order` | `minutes` | `tone` (card colour) | `icon` | Slides in the file / on the card | Versions |
|---|---|---|---|---|---|---|---|
| `orientation-workshop.yml` | GVR and RLV Orientation Workshop / Taller de orientación para RLV y GVR | 1 | 90 | `vine` (green) | `compass` | 61 / 59 | `full` (90), `short` (60) |
| `information-workshop.yml` | Grapevine and La Viña Information Workshop / Taller informativo de Grapevine y La Viña | 2 | 60 | `gv` (blue) | `book-open` | 53 / 49 | `full` (60), `late` (48), `visit` (20) |
| `writing-workshop.yml` | Grapevine and La Viña Writing Workshop / Taller de escritura de Grapevine y La Viña | 3 | 115 | `lv` (orange) | `pen-line` | 59 / 48 | `full` (115), `short` (84) |
| `committee-meeting.yml` | Grapevine and La Viña Monthly Committee Meeting / Reunión mensual del Comité de Grapevine y La Viña | 4 | 60 | `grape` (purple) | `users` | 43 / 29 | `full` (60), `topic` (60) |

The number on the card ("About 90 minutes · 59 slides") counts the slides of the full version **on the day of the
build**: facilitator pages, slides that start switched off and slides outside their dates are not counted. That is
why the committee meeting shows 29 of its 43 slides (13 pages for the chair and one slide that starts off).

Also in the folder: `README.md`, the committee's writing guide (saving it does not rebuild the site). Two sample
decks are in [`tests/fixtures/presentations/`](../tests/fixtures/presentations/): `sample-workshop.yml` uses every
kind of slide, every kind of live slide and every `{live:…}` key (a test makes sure of it), and `sample-meeting.yml`
is a small one. Both are good examples to copy from.

Each file starts with a long `#` comment that explains the choices made in that deck (where the times come from,
why a slide is left out of a version …). Keep those comments up to date when you change what they describe.

### 3.2 YAML rules that matter in these files

| Rule | Right | Wrong (and what happens) |
|---|---|---|
| Put every text in double quotes | `title: "Coming up"` | `title: Coming up: assemblies` → the file cannot be read |
| A value that starts with `{` must be quoted | `title: "{live:month} at a glance"` | `title: {live:month} at a glance` → `not valid YAML` |
| Long texts and notes: write `notes: \|`, then the text on the lines below it, every line indented the same (6 spaces in these files) | see the notes in any slide | a line indented less ends the block early |
| A double quote inside a quoted text | `“curly quotes”` or `\"` | a plain `"` ends the text |
| Dates in quotes | `show_until: "2027-01-31"` | `show_until: 2027-01-31` → `show_until must be a quoted "YYYY-MM-DD"` |
| Numbers without quotes | `minutes: 1.25` | `minutes: "1.25"` → `minutes (0.25–30) required` |
| Spaces, never tabs | each slide starts with `  - id:` (2 spaces, a dash); its fields have 4 spaces | a tab → the file cannot be read |

> **Note:** the files are read the way the Python checker reads them (YAML 1.1). So `yes`, `on`, `True` also mean
> `true`, and `no`, `off` mean `false`. Write `true` and `false` anyway: it is clearer.

### 3.3 The top of a file

The lines before `presets:` describe the deck and its card. Real example (`information-workshop.yml`):

```yaml
id: "information-workshop"
order: 2
lang: "en"
title: "Grapevine and La Viña Information Workshop"
short: "Information Workshop"
eyebrow: "Information workshop"
footer: "NETA 65 Grapevine & La Viña Committee · {live:panel}"
minutes: 60
icon: "book-open"
tone: "gv"
drive_title: "Grapevine and La Viña Information Workshop"

card:
  title:
    en: "Grapevine and La Viña Information Workshop"
    es: "Taller informativo de Grapevine y La Viña"
  summary:
    en: "Our meeting in print: what Grapevine and La Viña are, where they came from, what's free, and how members, groups and districts use them."
    es: "Nuestra reunión impresa: qué son La Viña y Grapevine, de dónde vienen, qué es gratis y cómo las usan los miembros, los grupos y los distritos."
  audience:
    en: "For any AA members, groups or districts, including those who have never opened an issue."
    es: "Para cualquier miembro, grupo o distrito de AA, incluso para quienes nunca han abierto una revista."
```

| Field | Rule (the checker) | What it does and where it shows |
|---|---|---|
| `id` | the file name without `.yml` | The card's anchor `#pres-<id>`, the address `?present=<id>`, the JSON file name, and the key under which presenters' own versions are kept. **Never rename a deck that is on the site**: presenters would lose their versions of it. |
| `order` | a whole number 1–9, different in each deck | The order of the cards (then by id). |
| `lang` | always `"en"` | — |
| `title` | text | The player's title, the print headings and the speaker script's heading. |
| `short` | text | The player's header; the name in the "Print or save a copy" list on the English page; the start of the name of a saved printout ("Information Workshop – Handout for participants – 2026-10-02"). |
| `eyebrow` | text | The small line above the titles before the first `section` slide. |
| `footer` | text | The line at the bottom of every slide (not on the title, section and closing slides), next to its number. May use `{live:…}` keys. |
| `minutes` | a whole number 5–240 | The card's length: "About 60 minutes"; a deck of 100 minutes or more that is close to a whole hour shows hours (115 → "About 2 hours"). The full version's slides must add up to 75–125 % of it. |
| `icon` | a [Lucide](https://lucide.dev/icons/) icon name | The card's icon. Checked wherever the site's tools are installed (always on GitHub; on the PC after `npm ci`): `icon 'x': no such lucide icon`. |
| `tone` | `gv`, `lv`, `vine` or `grape` | The colour of the card's icon tile: blue, orange, green, purple. |
| `drive_title` | text (optional) | The exact title of the deck's PowerPoint copy in the Drive (see below). |
| `card` | `title`, `summary`, `audience`, each with `en` AND `es` | The card on `/orientation/` (English) and `/es/orientation/` (Spanish): title, one or two sentences, and "Who it's for" / "Para quién es". |
| `presets` | at least one | The versions: [3.4](#34-versions-presets). |
| `fillins` | optional | The presenter's blanks: [3.5](#35-the-presenters-blanks-fillins). |
| `slides` | at least 5 | [3.6](#36-slides-the-fields-every-slide-can-have). |

> **Note:** `README.md` says `order` is 1–4. The checker accepts 1–9; the test `tests/test_presentations.py` only
> asks that each deck has its own number.

**Example: change the card's summary.** Change both languages, in the same commit:

```yaml
  summary:
    en: "Our meeting in print: what Grapevine and La Viña are, what's free, and how groups and districts use them."
    es: "Nuestra reunión impresa: qué son La Viña y Grapevine, qué es gratis y cómo las usan los grupos y los distritos."
```

What happens: the card text changes on `/orientation/#pres-information-workshop` and on
`/es/orientation/#pres-information-workshop`. The slides do not change. Leave out the `es:` line and the checker
says `card.summary: needs an English AND a Spanish text {en: …, es: …}`, and the build stops
([4](#4-what-happens-after-you-save)).

**`drive_title` and the PowerPoint copy.** The build looks for the newest Drive file whose title is exactly the
`drive_title`. A Drive file's title is its name without the extension, without a date and without "Copy of" (see
[The Drive panel folder](drive-panel-folder.md)). So all of these Drive files match
`drive_title: "Grapevine and La Viña Information Workshop"`:

| File in `2027-2028_Panel77_GVLV/slides` | Title | Date |
|---|---|---|
| `Grapevine and La Viña Information Workshop.pptx` | Grapevine and La Viña Information Workshop | the upload day |
| `2027-01-05 Grapevine and La Viña Information Workshop.pptx` | the same | 2027-01-05 (it wins: newest) |
| `Copy of Grapevine and La Viña Information Workshop.pptx` | the same | the upload day |

What the match gives: the card's **More → PowerPoint copy** link with "Made in October 2026 · doesn't update", the
copy offered on the card when JavaScript is off, the list in "Print or save a copy" when JavaScript is off, the
`drive` field of the JSON, and the **Present on the web** button on that file's card on `/portfolio/`. No match: no
link and no button, and nothing else breaks.

> **Note:** only a date with a day is taken out of the title. A month and a year stay in it:
> `January 2027 Grapevine and La Viña Information Workshop.pptx` has the title "January 2027 Grapevine and La Viña
> Information Workshop" and does **not** match. And the match is not limited to the `slides` folder or to `.pptx`
> files: any file in the committee's Drive with exactly that title counts, so a newer document with the same name in
> another folder would become the "PowerPoint copy". Give that title to the PowerPoint file only.

### 3.4 Versions (`presets`)

A version is a length or a special form of the deck. The presenter picks one in **Customize → Version**. The real
versions of the orientation workshop:

```yaml
presets:
  - id: "full"
    label: { en: "Full workshop (about 90 minutes)", es: "Taller completo (unos 90 minutos)" }
    minutes: 90
  - id: "short"
    label: { en: "60-minute version", es: "Versión de 60 minutos" }
    minutes: 60
    hide: ["milestones", "is-and-isnt", "practice", "helping-subscribe", "break", "record", "where-to-send", "tracker",
           "coming-up", "words", "scenarios-d-f"]
    note:
      en: "For example, at a district meeting: no break, introductions in the chat, …"
      es: "Por ejemplo, en una reunión de distrito: sin descanso, presentaciones en el chat, …"
```

| Field | Rule | What it does |
|---|---|---|
| `id` | lowercase letters, digits, dashes; unique | Used by `hide`/`only`, `version_minutes`, `version_fields`, `version_notes` and `{only:…}` / `{not:…}`. |
| `label` | `en` and `es` | The name in Customize → Version, and on the card's "Also:" line. |
| `minutes` | a whole number 1–240 | The version's length. Its slides must add up to 70–130 % of it. |
| `hide` | a list of slide ids | Every slide of the full version **except** these. |
| `only` | a list of slide ids | **Only** these slides, in the deck's order (not the list's), even slides that start switched off. |
| `note` | `en` and `es` (optional) | A line under the version's name in Customize → Version. |

Rules: **the first version is the full one** (no `hide`, no `only`); a version has `hide` OR `only`, never both;
a facilitator page can be in neither list (it is never in the show).

**On the card**, every version after the first is named on the "Also:" line, starting in lower case (unless it
starts with a name such as Grapevine, La Viña, AA, Zoom or NETA, or an abbreviation such as GVR). A label ending in
"(about … minutes)" loses that part, and gets the version's own minutes instead when they differ from the full
version's:

| Labels | The card says |
|---|---|
| "60-minute version" | `Also: 60-minute version` |
| "Running late (about 48 minutes)", "20-minute version (a district or group visit)" | `Also: running late (48 min) · 20-minute version (a district or group visit)` |
| "A month with a topic of the month (about 60 minutes)" (same length as the full one) | `Also: a month with a topic of the month` |

**Example: add a 20-minute visit to the orientation workshop.** Put this after the `short` version. It passes the
checker: its twelve slides add up to 14¼ minutes, and a 20-minute version may add up to anything from 14 to 26.

```yaml
  - id: "visit"
    label: { en: "20-minute visit to a group", es: "Visita de 20 minutos a un grupo" }
    minutes: 20
    only: ["title", "welcome", "why-we-are-here", "two-magazines", "pay-their-way", "what-a-rep-does", "this-month",
           "announcement", "deadlines", "resources", "responsibility", "thank-you"]
    note: { en: "Twelve slides, then questions.", es: "Doce diapositivas y luego las preguntas." }
```

What happens: Customize → Version offers "20-minute visit to a group — 12 slides · about 14 minutes" with its note,
and the card reads `Also: 60-minute version · 20-minute visit to a group` (Spanish: `También: versión de 60 minutos
· visita de 20 minutos a un grupo`). Take `"resources"` and `"responsibility"` out of the list and the checker
complains: `version 'visit': its slides add up to 12 minutes, it says 20` (add slides back, or lower `minutes`).

> **Note:** a slide you add later shows up in every version that uses `hide` (add its id to `hide` to keep it out),
> but in a version that uses `only` it shows up only when you add its id to the list.

**A slide's own values in one version.** Four tools, all written on the slide:

| Tool | Example | What it does |
|---|---|---|
| `version_minutes` | `version_minutes: { short: 1.5 }` | The slide's length in that version: the schedule, the TIME line of the notes, the agenda's times and the checker's sums use it. |
| `version_fields` | see below | The slide's own words in that version (any field of its layout, its `title`, `eyebrow`, `source` or `takeaway`; never `kind`, `options` or `qr`, and never `minutes` or `notes`). |
| `version_notes` | `version_notes: { short: "CUT TO 60: keep." }` | A highlighted line in the notes, only in that version. |
| `{only:…}` / `{not:…}` at the start of a notes line | `{not:short} SAY: We have about ninety minutes together …` | That line of the notes only in those versions, or in every version but those (several: `{only:short,visit}`). |

Real `version_fields` (`orientation-workshop.yml`, slide `welcome`): the 60-minute version has no break, so its
last point is different. When you change a point that both lists have, change it in both.

```yaml
    items:
      - "**Anonymity:** who you see here and what you hear here, let it stay here"
      - "A 10-minute break about halfway; the slides are shared afterward"
    version_fields:
      short:
        items:
          - "**Anonymity:** who you see here and what you hear here, let it stay here"
          - "The slides are shared afterward"
```

(The real lists have six points each; two are shown here.)

### 3.5 The presenter's blanks (`fillins`)

Blanks are what each presenter fills in for their own event: the date, the place, their service position. They type
them in **Customize → Your details**; the answers stay on their device. A slide uses a blank as `{fill:key}`.

```yaml
fillins:
  - key: "date"
    label: { en: "Date", es: "Fecha" }
    hint: "Month DD, YYYY"
  - key: "presenter"
    label: { en: "Presenter's service position", es: "Puesto de servicio de quien presenta" }
    hint: "Service position"
    default: "Area 65 Grapevine / La Viña Chair"
    shared: true
  - key: "first_name"
    label: { en: "Your first name (only in your notes)", es: "Tu nombre de pila (solo en tus notas)" }
    hint: "first name"
    shared: true
    notes_only: true
```

| Field | Rule | What it does |
|---|---|---|
| `key` | lowercase letters, digits and `_`, starting with a letter; unique | The name used in `{fill:key}`. |
| `label` | `en` and `es` | The field's name in Customize → Your details (in the page's language). |
| `hint` | required | What an empty blank shows on the slide, in orange brackets: `[Month DD, YYYY]`. |
| `default` | text (optional) | What the slide says while the blank is empty, instead of the orange hint. |
| `shared` | `true` / `false` | One answer for every deck whose blank has the same key and is shared (today `presenter` and `first_name`, in all four). |
| `notes_only` | `true` / `false` | The answer may appear only in the speaker notes, never on a slide. On a slide the checker refuses it: `{fill:first_name} is notes_only (never on a slide)`. |

Before the show starts, the player warns "3 of your details are still blank" and offers **Fill them in** or
**Present anyway**.

**Example: a new blank for the host group, used on a slide.**

```yaml
  - key: "host_group"
    label: { en: "Host group or district", es: "Grupo o distrito anfitrión" }
    hint: "host group or district"
```

and on a slide:

```yaml
    eyebrow: "Hosted by {fill:host_group}"
```

What happens: Customize → Your details gets a field "Host group or district" ("Grupo o distrito anfitrión" on
`/es/`), listed under the slide that uses it. Until the presenter fills it in, the slide shows
"Hosted by [host group or district]" in orange. A typo such as `{fill:host-group}` is refused by the checker:
`{fill:host-group} is not in fillins`. (The writing workshop already has exactly this blank: add it to the other
decks only. A second `host_group` in the same file gives `duplicate key 'host_group'`.)

### 3.6 Slides: the fields every slide can have

A slide is a block that starts with `  - id:` under `slides:`. It ends where the next `  - id:` starts.

| Field | Rule (the checker) | What it does |
|---|---|---|
| `id` | lowercase letters, digits and dashes; unique in the file | Presenters' own changes are kept by it. `{slide:…}`, `hide`/`only` and an agenda row's `from` point to it. **Keep it once the deck is on the site**: a slide whose id changes is a new slide for presenters. |
| `layout` | one of the 15 kinds | [3.7](#37-the-15-kinds-of-slides-layout) |
| `title` | required | The slide's title. |
| `eyebrow` | text | The small line above the title (the player writes it in capitals). Left out: "Part 3 · <the part's title>" from the last `section` slide, or the deck's `eyebrow` before the first part; a `qa` or `credits` slide then has none. |
| `notes` | required; at least 25 words (facilitator pages: any length); no `TIME:` line | The speaker notes: [3.8](#38-speaker-notes). |
| `minutes` | 0.25 to 30 (none on a facilitator page) | The slide's length: the schedule, the TIME line of the notes, the agenda's times and the checker's sums use it. |
| `optional` | `true` / `false` | The badge "Optional" in Customize → Slides, and "(optional: it can go when you're running late)" in the TIME line. |
| `starts_off` | `true` / `false` | Not in the show until the presenter turns it on (Customize → Slides) or a version's `only` lists it. Not counted on the card or in the deck's minutes. |
| `facilitator` | `true` / `false`; then no `minutes`, `optional` or `starts_off` | Never projected: a page in Customize → Prepare. [3.14](#314-facilitator-pages-and-handouts) |
| `handout` | `true` / `false` | Printed for the participants. On a slide of the show: shown AND printed. |
| `print` | `"portrait"` or `"landscape"`, only with `handout: true` | How a handout page prints. Left out: landscape. |
| `accent` | `gv` `lv` `vine` `grape` `navy` | On a `section` slide: the colour of its part (the slides after it take it). On any other slide: that slide's colour only. Before the first section, and on a section without one: `gv`. |
| `lang` | `"es"` or `"en"` | `"es"`: a slide written in Spanish (a handout, an announcement to read aloud). The player marks it as Spanish for screen readers. |
| `source` | text | The small line in italics at the bottom, exactly as written: the player adds no "Sources:" of its own, so write it yourself (most slides start it with "Sources:" or "Source:"). |
| `takeaway` | text | The highlighted box at the bottom. |
| `version_minutes`, `version_fields`, `version_notes` | version ids of this deck | [3.4](#34-versions-presets) |
| `show_from`, `show_until` | `"YYYY-MM-DD"` in quotes | Only in the show on those days: [3.13](#313-slides-that-come-and-go-by-date). |
| `when` | only `"price_notice"` | Only while a price-change notice is current: [3.13](#313-slides-that-come-and-go-by-date). |
| `allow_words` | a list of words | A word of the wording rules that this slide may use because it quotes a source word for word: [3.15](#315-the-checkers-rules). |

> **Note:** `optional: true` hides nothing by itself. To leave a slide out of the running-late version, put its id in
> that version's `hide` list. `information-workshop.yml` has thirteen optional slides: its "Running late" version
> hides the ten that are in the show, and the other three (the review questions) start switched off.

> **Note:** the checker's message says "0.25–30", but it accepts any number of minutes above 0 up to 30 (0.1
> passes). Keep 0.25 (15 seconds) as the smallest, as the decks do.

Any other field is refused: `unknown field 'subtitle' for layout 'closing'`.

### 3.7 The 15 kinds of slides (`layout`)

| `layout` | Needs | May have | Notes |
|---|---|---|---|
| `title` | — | `subtitle`, `lines` (a list) | The player adds "Current as of <the build's date>". |
| `section` | `number` (1, 2 … or `"A"`) | `subtitle` | Starts a part: the next slides' eyebrow is "Part N · <title>". Its `accent` colours the part. |
| `bullets` | `items` | `numbered`, `checklist` | An item can have one level of sub-items: `{ text: "…", items: ["…"] }`. |
| `columns` | `columns`: 2 to 4, each `heading`, `gloss`, `text` OR `items`, `accent` | `style` (`panels`, `cards`, `plain`), `checklist` | Four columns are drawn two by two. `checklist: true` puts tick boxes in place of bullets. |
| `table` | `rows` (a list of lists) | `header`, `widths`, `first_col_bold` | Every row has as many cells as the header (or the first row). `widths`: one positive number per column. |
| `agenda` | `items`: `{ time, title, detail, from }` | — | With `from: "<slide id>"`, the player works out the row's time for the version shown, and drops a row whose slides are all left out. |
| `quote` | `quote`, `credit` | — | Word for word, with its credit line. The quote is exempt from the wording rules. |
| `activity` | `steps`, `duration` | `materials`, `numbered` | A time card shows `duration` minutes and, when there are `materials`, "You will need" with the list. |
| `qa` | — | `prompts`, `note` | Questions for the room. |
| `resources` | `links`: `{ label, url, note }` | — | `url`: an `https://` address, a page of the site (`/events/`), or an e-mail address. The slide writes the address out. |
| `credits` | `sources` (a list) | `note`, `disclaimer` | `disclaimer: true` adds the two standard lines ("Not an official AA Grapevine, Inc. presentation." …) unless the slide already says them. The sources are exempt from the wording rules. |
| `closing` | — | `message`, `lines`, `qr` | `qr: "/"`: a QR code for a page of the site, or an `https://` address. |
| `text` | `body` | `style` (`script`, `break`) | Paragraphs separated by an empty line; a line starting with "- " is a list item. `script`: a tinted card to read aloud (blanks written ‹like this›). `break`: a pause, centred. |
| `flow` | `steps`: 2 to 6 `{ title, text }` | — | Boxes with arrows between them. |
| `live` | `kind` | `intro`, `options` | Facts from the site's data: [3.10](#310-live-slides-layout-live). |

> **Note:** the checker also accepts `link:` inside a column, but the player does not show it. Put a link in the
> column's text instead: `[the guidelines](https://www.aagrapevine.org/guidelines-contributing-grapevine)`.

**Examples.** Every example below passes the checker when pasted into a deck (before the `credits` slide).

A list with sub-points (`bullets`):

```yaml
  - id: "group-ideas"
    layout: "bullets"
    title: "Three ideas for your group this month"
    items:
      - "Read one story aloud at a meeting, then share on it"
      - text: "Keep the magazines where people can see them"
        items:
          - "On the literature table"
          - "On the shelf where the group keeps its books"
      - "Give one date: Grapevine's next story deadline, {live:next_deadline_gv}"
    takeaway: "Ideas to choose from: your group conscience decides."
    minutes: 1.5
    notes: |
      SAY: Here are three simple ideas to take back to your group this month. Reading one story aloud and sharing on it makes a fine meeting topic. Keep the magazines where people can see them. And give one date, like Grapevine's next story deadline.
      ASK: Which of these has your group tried already?
      TRANSITION: Here's how one district put it into words.
```

What happens: a new slide with three points, the second with two sub-points; the third point ends with the date and
theme of Grapevine's next deadline, such as "November 1, 2026 — June 2027: Emotional Sobriety", and moves on by itself
once that day is over. The slide is in every version that uses `hide`, and the deck's card gets one more slide.

A table:

```yaml
  - id: "contacts-table"
    layout: "table"
    title: "Who to ask"
    header: ["Question", "Ask"]
    rows:
      - ["Registering as a GVR or RLV", "The magazines' rep pages, or {live:email}"]
      - ["A missing issue or a renewal", "Customer service: (800) 631-6025"]
      - ["Our next committee meeting", "{live:meeting_next}, {live:meeting_time}"]
    widths: [4, 7]
    first_col_bold: true
    minutes: 1
    notes: |
      SAY: Here's who to ask. For registering, the magazines' rep pages, or our committee's e-mail. For a missing issue or a renewal, customer service. And our next committee meeting is on the slide; every AA member is welcome.
```

What happens: a two-column table with the first column in bold; the last row always names the next committee
meeting, and the e-mail address follows `config/site.yml`. (A toll-free number such as (800) 631-6025 passes the
checker; a personal number does not: [3.15](#315-the-checkers-rules).)

An agenda that follows the version (real, `information-workshop.yml`, shortened):

```yaml
    items:
      - { time: "0:00", title: "Welcome and opening", from: "title" }
      - { time: "0:08", title: "Parts 1–2 · What Grapevine and La Viña are · A short history", from: "part-1" }
      - { time: "0:17", title: "Part 3 · Inside an issue, and the ways to read", from: "part-3" }
      - { time: "0:50", title: "Questions, and closing", from: "questions" }
```

What happens: the player shows each row at the time its `from` slide starts in the version being shown. In the full
version the rows read 0:00, 0:08, 0:17 … 0:50, as written. In "Running late", which leaves out the optional slides,
they read 0:00, 0:08, 0:14 … 0:38. A row whose slides are all left out disappears. (The orientation
workshop's agenda has a second list of rows for its 60-minute version, in `version_fields`.)

> **Note:** the times you write are a record of the plan; the player shows the times it works out. The test
> `tests/test_presentations_core.py` checks that, in the **full** version, the two agree. So when you change a
> slide's `minutes`, also change the written `time` of the agenda rows after it (see [3.16 F](#f-change-a-slides-length)).

A read-aloud card (`text`, `style: "script"`):

```yaml
  - id: "district-announcement"
    layout: "text"
    style: "script"
    accent: "lv"
    title: "A sample announcement for a district meeting"
    body: |
      **Read it in your own words:**

      “Hi, I'm ‹first name›, the GVR for ‹group›. The committee meets {live:meeting_rule}, {live:meeting_time}, on Zoom, and every AA member is welcome. Next meeting: {live:meeting_next}.”
    minutes: 1
    notes: |
      SAY: Here's a short announcement you can give at a district meeting. Fill in your first name and your group, and say it in your own words. The meeting's date fills in by itself, so it is always the next one.
      TIP: Keep it under a minute, and never read out anyone's full name.
```

What happens: a tinted card in La Viña's orange (`accent: "lv"`), in serif type; the ‹first name› and ‹group› are
drawn in orange and stay blank for the reader to fill in aloud (they are not `{fill:…}` blanks), and the meeting's
rule, time and next date fill in by themselves.

A pause (`text`, `style: "break"`), real, `orientation-workshop.yml`, slide `break`:

```yaml
    layout: "text"
    style: "break"
    accent: "grape"
    title: "Break: 10 minutes"
    body: "We start again at **{fill:break_end}**. Stretch, refill, and please keep the room free of photos."
    minutes: 10
```

What happens: the title and the sentence centred on a purple slide, with the clock time the presenter typed in
Customize → Your details (or an orange `[time]` until they do). The 60-minute version leaves this slide out.

Boxes with arrows (`flow`):

```yaml
  - id: "how-a-story-travels"
    layout: "flow"
    title: "How a story reaches the page"
    steps:
      - { title: "A member writes", text: "One experience, in their own words" }
      - { title: "The editors read", text: "They choose stories for each issue and its theme" }
      - { title: "The issue comes out", text: "In print, online and in the app" }
      - { title: "A group shares it", text: "A member reads it at a meeting" }
    minutes: 1
    notes: |
      SAY: Every story in these magazines started with a member like you, sitting down to write about one moment of their sobriety. The editors choose some for each issue. Months later the story is in print, and somewhere a group reads it aloud.
```

What happens: four boxes in a row, with arrows between them (two to six boxes are allowed).

A new part (`section`): its number and colour carry over to the slides after it.

```yaml
  - id: "part-8"
    layout: "section"
    number: 8
    accent: "grape"
    title: "Your district's own news"
    subtitle: "A few minutes for the districts in the room"
    minutes: 0.25
    notes: |
      SAY: Before we close, a few minutes for the districts in the room. If your district has a workshop, a table or a GV/LV report coming up, tell us in one or two sentences.
      DO: Keep each district to about a minute, and write the dates in the chat.
```

What happens: the slides after it show the eyebrow "Part 8 · Your district's own news" (unless they have their own)
and take the purple colour, up to the next `section` slide. It fits the orientation workshop, whose parts go up to 7.
The information workshop already has a `part-8` (Part 8): there, give the new part its own id and number (`part-9`,
`number: 9`), or the checker says `duplicate id 'part-8'`.

A closing slide with a QR code (real, `information-workshop.yml`, slide `thank-you`):

```yaml
    layout: "closing"
    title: "Thank you"
    message: "For carrying the message: in print, online, and one member to another."
    lines: ["NETA 65 Grapevine & La Viña Committee", "{live:email}", "{live:site}"]
    qr: "/"
```

What happens: the QR code opens the committee website's home page. `qr: "/events/"` would open the Events page.

### 3.8 Speaker notes

Notes are what the presenter reads in the notes panel and the presenter view. Anyone can open them (they are in the
public JSON file), so they follow the same rules as the slides.

- One paragraph per line, each starting with its label in capitals and a colon: `SAY:` `DO:` `ASK:` `IF TIME, ASK:`
  `TIP:` `FACILITATOR TIP:` `SOURCES:` `TRANSITION:` `WATCH FOR:` `UPDATE:` … The player shows the label in bold.
- At least 25 words (a facilitator page may be shorter): `notes look thin (< 25 words): say what to SAY, DO and ASK`.
- No `TIME:` line. The player writes it from `minutes`, for the version being shown: a slide of 1.5 minutes that ends
  8 minutes in gets "TIME: about 1½ minutes. You should be at about 0:08 when you move on." A slide under a minute
  gets seconds ("about 45 seconds").
- Do not talk about PowerPoint in the notes of a slide that is shown ("right-click", "hide slide", "this file",
  "PowerPoint", ".pptx"): `notes still talk about PowerPoint (hidden slides, this file …) — say what to do in the
  web player (Customize → …)`. Name the player's buttons with `{ui:…}` instead ([3.11](#311-the-other-tokens)).
- A line only for some versions starts with `{only:…}` or `{not:…}` ([3.4](#34-versions-presets)).

Real example (`orientation-workshop.yml`, slide `title`):

```yaml
    notes: |
      SAY: Welcome, everyone, and thank you for being here. My name is {fill:first_name}, I'm an alcoholic, and I serve as {fill:presenter}. …
      {not:short} SAY: We have about ninety minutes together, with a ten-minute break in the middle, …
      {only:short} SAY: We have about an hour together, without a break, …
      FOR FACILITATORS: {ui:customize} → {ui:prepare} holds the 'before you present' checklist and the 60-minute plan. …
    version_notes:
      short: "CUT TO 60: keep this slide."
```

What happens: in the full version the presenter reads "about ninety minutes"; in the 60-minute version "about an
hour" plus the highlighted "CUT TO 60" line. On the Spanish page the last line reads "Personalizar → Preparar".
The first name appears only here, never on a slide.

### 3.9 Facts that stay current (`{live:…}`)

Write `{live:key}` in any text (a slide or its notes). The player fills it in **when the slide is shown**, from the
JSON file, by the viewer's own clock. Each fact carries what it will say next, so a copy opened later moves on by
itself (the next meeting after tonight's, the new price on its day). When there is nothing to say, the fact says
where to look instead (last column). Examples are from the build of October 2, 2026.

Tokens (`{live:…}`, `{fill:…}` and the others in [3.11](#311-the-other-tokens)) work in the slides, their notes and
the deck's `footer`. They do **not** work in the `card` texts, the versions' labels and notes, or the blanks' labels:
those show exactly what you type.

| Key | What it says (example) | Comes from | Nothing to say → |
|---|---|---|---|
| `site` / `site_url` | neta65.github.io/aagrapevine / https://neta65.github.io/aagrapevine/ | the site's address (on GitHub: the Pages address) | — |
| `email` | grapevine@neta65.org | `config/site.yml` → `site: contact_email` | — |
| `panel` | Panel 77 (2027–2028) | the newest Panel folder in the Drive (`2027-2028_Panel77_GVLV`) | — |
| `as_of` | October 2, 2026 | the day of the build | — |
| `month` / `year` | October 2026 / 2026 | the viewer's month (switches on the 1st, Central time) | — |
| `meeting_next` | Wednesday, October 21, 2026 | `config/site.yml` → `meeting:` | "see the Meetings page" |
| `meeting_day` | Wednesday, October 21, 2026 | same | "see the Meetings page" |
| `meeting_after` | Wednesday, November 18, 2026 | same | "see the Meetings page" |
| `meeting_month` | October 2026 | same | "Monthly" |
| `meeting_rule` | every third Wednesday of the month | same | — |
| `meeting_time` | 7:00 – 8:00 PM Central time | same | — |
| `meeting_zoom_id`, `meeting_passcode` | the committee meeting's Zoom ID and passcode | same (`meeting_id`, `passcode`) | — |
| `meeting_phone` | +1 346 248 7799 (Houston) | `config/site.yml` → `phone_access: numbers` (the first one) | "see the Accessibility page" |
| `meeting_phone_passcode` | (empty today) | `phone_access: committee: phone_passcode` (or the meeting's passcode when it is numbers only) | — (empty) |
| `lv_workshop_next` | Thursday, October 22, 2026 | the `recurring_events:` entry with `host: lv` | "see La Viña's events calendar at aalavina.org" |
| `lv_workshop_time`, `lv_workshop_zoom_id` | 2:00 – 3:00 PM Central time (3:00 PM Eastern) · its Zoom ID | same | — |
| `price_gv_print`, `price_gv_digital`, `price_lv_print`, `price_lv_digital` | $36.00, $29.99, $18.00, $14.99, then $39.00, $34.00, $19.50, $17.00 from January 1, 2027 | the Shop's data, and `config/site.yml` → `price_changes:` | "see the Shop page" |
| `price_change_note` | "Prices change on January 1, 2027: Grapevine, 1 year: print $39.00, digital $34.00; …", from that day "New prices since January 1, 2027." | `price_changes:` (from `announced` through `notice_until`) | empty outside a notice |
| `price_change_date` | January 1, 2027 | same | empty outside a notice |
| `gv_issue`, `gv_next_issue`, `gv_theme` | October 2026 · Loneliness / November 2026 · Classic Grapevine / Loneliness | the magazines' data (as on `/monthly/`) | "see aagrapevine.org" |
| `lv_issue`, `lv_next_issue`, `lv_theme` | September–October 2026 · Servicio en AA / November–December 2026 · La alegría de vivir (The Joy of Living) / Servicio en AA | same | "see aalavina.org" |
| `next_deadline_gv` | November 1, 2026 — June 2027: Emotional Sobriety | the editorial calendar (as on `/contribute/#deadlines`) | "see aagrapevine.org for Grapevine's themes" |
| `next_deadline_lv` | October 17, 2026 — May–June 2027: Recaídas (Relapses) | same | "see aalavina.org for La Viña's themes" |
| `botm`, `botm_lv` | No Matter What: Dealing With Adversity in Sobriety / Frente a Frente: El apadrinamiento en acción (each until its offer ends) | the Shop's data | "see aagrapevine.org's Book of the Month" / "see aalavina.org's Libro del mes" |
| `gv_audio_phone`, `lv_audio_phone` | (559) 726-1216 / (559) 670-1601 | the magazines' story-line pages (as on `/contribute/#record`) | "see the Share your story page" |
| `assembly_next` | NETA 65 Spring Assembly 2027 · Fri, Mar 19 – Sun, Mar 21, 2027 (an assembly whose details are not final adds "(details to be confirmed)") | NETA 65's assemblies on `/events/` | "see the Events page" |
| `gv_open_meeting` | Wednesdays, 11:00 AM Central (noon Eastern) | the weekly open meetings (as on `/meetings/#weekly-open`) | "see the Meetings page" |
| `lv_open_meeting` | Thursdays, 11:00 AM Central (noon Eastern), starting Nov. 5, 2026 ("since Nov. 5, 2026" from that day) | same, and `config/site.yml` → `lavina_weekly_open:` | "see the Meetings page" |
| `open_meeting_zoom` | the weekly open meetings' Zoom ID and passcode | same | "see the Meetings page" |

When each one moves on: `meeting_next` when the meeting **ends** (8 PM Central on a meeting night it already names
next month's); `meeting_day`, `meeting_month` and `meeting_after` together at **midnight** Central after the meeting
day; the month, the year and the issues at midnight Central on the 1st; a price at midnight Central on its day; a
deadline once its day is over; a Book of the Month when its offer ends (it then says where to look, until a build has
the next book); an assembly once it is over.

**Pair the meeting keys that move together.** In one sentence or on one slide, use `meeting_day` with
`meeting_month` and `meeting_after` (the committee meeting's own slides: "{live:meeting_month} meeting" over
"{live:meeting_day} · {live:meeting_time}"), and `meeting_next` alone ("Next meeting: {live:meeting_next}" in a
workshop). Never "the {live:meeting_month} meeting on {live:meeting_next}": between 8 PM and midnight on a meeting
night that names two different meetings.

**Write your sentence so the "nothing to say" words fit too.** "Next meeting: {live:meeting_next}" reads well both
as "Next meeting: Wednesday, October 21, 2026" and as "Next meeting: see the Meetings page".

**Zoom IDs and phone numbers.** Write `{live:meeting_zoom_id}`, `{live:meeting_phone}`, `{live:gv_audio_phone}` …
rather than digits, so a change in `config/site.yml` (or on the magazines' pages) reaches every deck by itself.

> **Note:** `README.md` says the checker "takes digits for a phone number". It does, but every number written
> anywhere in `config/site.yml` counts as one the site publishes, so the committee's own Zoom ID typed as digits
> passes. Another meeting's ten-digit ID does not: `a personal-looking phone number '883 555 0199' (a Zoom meeting
> ID? write {live:meeting_zoom_id} / {live:lv_workshop_zoom_id}; …)`.

> **Note:** `panel` comes from the Drive's Panel folder names, not from `config/orientation.yml`. When the committee
> makes the folder for the next panel (for example `2029-2030_Panel79_GVLV`), every deck's footer changes to
> "Panel 79 (2029–2030)" at the next run (see [The Drive panel folder](drive-panel-folder.md)).

> **Note:** La Viña's themes show their English in brackets only when the English is written by hand in
> `data/translations/overrides.yml` (for example `"Recaídas": { en: "Relapses" }`). A machine translation is left out
> of a fact's text, and marked "auto-translated" in a live slide's list. See [Translations](translations.md).

### 3.10 Live slides (`layout: "live"`)

A live slide shows a list or a box of facts from the site's data. `intro` is a sentence above it.

| `kind` | What it shows | `options` (default) |
|---|---|---|
| `meeting` | the committee's next meeting dates, the rule, the time, the Zoom ID and passcode | `limit` (3; 12 = a year) |
| `lv-workshop` | La Viña's next monthly virtual workshops, the time, the Zoom ID, the contact | `limit` (3) |
| `events` | the next events of `/events/`, never the committee meetings. A monthly event (the CityWide booth) takes one row, its next date. A hybrid event shows its place AND "Online on Zoom"; an event whose details are not final says "Details to be confirmed" | `limit` (5); `filter`: `all`, `workshops` (a title with workshop / taller), `neta` (NETA 65's own events: the committee's flyers and events, the booth, the Area's calendar, and any other calendar feed in `sources: ics_feeds:` that has no category), `calendar` (Grapevine's and La Viña's calendars, and the events they host), `assemblies` (NETA 65's assemblies); `series: "all"` (every date of a monthly event) |
| `deadlines` | the next story deadlines: date, issue, theme | `pub`: `gv`, `lv` or `both` (both); `limit` (6); `limit_each` (with `both`: this many of each magazine) |
| `issues` | this month's Grapevine and La Viña issues and themes | — |
| `monthly` | this month's ideas from the Monthly toolkit | `limit` (3) |
| `prices` | the 1-year print and online prices of both magazines; during a price notice, the new prices and their date | `pub` |
| `botm` | Grapevine's Book of the Month and La Viña's Libro del mes | — |
| `bulletin` | the committee bulletin's newest posts | `limit` (3) |
| `qr` | a QR code | `url` (required: a page of the site like `"/contribute/"`, or an `https://` address), `caption` |

`limit` is 1–24; `limit_each` 1–12. An option the kind does not use is refused:
`option 'limit_each' is not used by 'events' (['filter', 'limit', 'series'])`.

The dated lists carry every date known for about a year (at most 24 rows). The player leaves out what is already
past, then shows `limit` rows, so a copy opened weeks later still fills the slide. An empty list says
"Nothing is listed right now. See <the page's address>".

Real examples (`orientation-workshop.yml`):

```yaml
  - id: "deadlines"
    layout: "live"
    kind: "deadlines"
    options: { pub: "both", limit: 6, limit_each: 3 }
    title: "Themes and deadlines"
    intro: "Grapevine and La Viña: stories due ({lang:es}fecha límite{/lang})."
```

What happens: the next three deadlines of **each** magazine (so Grapevine's monthly deadlines never push La Viña's
off the slide). An issue with two themes is never cut in half.

```yaml
  - id: "coming-up"
    layout: "live"
    kind: "events"
    options: { filter: "assemblies", limit: 3 }
    title: "Coming up"
```

What happens: the next three NETA 65 assemblies, with "Details to be confirmed" while the Events page says so.

New examples (they pass the checker):

```yaml
  - id: "booth-dates"
    layout: "live"
    kind: "events"
    options: { filter: "neta", limit: 6, series: "all" }
    title: "Coming up, date by date"
    intro: "NETA 65's events in the months ahead, with every date of a monthly event."
    minutes: 1
    notes: |
      SAY: These are NETA 65's events in the months ahead, our committee's own included. A monthly event, like the booth, shows each of its dates here, so you can pick one and offer to help. The list fills in from the committee website's Events page every day.
      TIP: If the list is empty, the slide sends people to the Events page instead.

  - id: "scan-events"
    layout: "live"
    kind: "qr"
    title: "Scan for every event"
    intro: "The committee website's Events page, with the calendar to add."
    options: { url: "/events/", caption: "Events on the committee website" }
    minutes: 0.5
    notes: |
      SAY: Scan this code with your phone's camera to open the committee website's Events page. It has every workshop, assembly and booth date, and a calendar you can add to your own phone.
      TRANSITION: Now, your questions.
```

What happens: the first shows the next six NETA 65 events, each booth Saturday on a row of its own (without
`series: "all"` the booth would take one row, its next date). The committee meeting's page for the chair,
`events-ahead`, is a live slide too, with the same options and `limit: 12`: a facilitator page can hold live facts.
The second shows a QR code for the Events page, with the caption under it.

Other kinds work the same way: `kind: "meeting"` with `options: { limit: 12 }` lists a year of committee meetings;
`kind: "monthly"` shows this month's toolkit ideas; `kind: "bulletin"` the newest bulletin posts.

**The card's "Stays current" chips** come from what a deck uses: its live slides' kinds and its `{live:…}` keys
(any `meeting_…` key → "Committee meeting dates", `lv_workshop_…` → "La Viña's monthly workshop", `price_…` →
"Subscription prices", `…_issue` / `…_theme` → "This month's issues", `next_deadline_…` → "Story deadlines",
`botm…` → "Book of the Month", `assembly_next` → "Upcoming events"; a `monthly` slide → "Ideas for this month",
a `bulletin` slide → "Bulletin posts"). Add a `bulletin` slide to a deck and its card gets a "Bulletin posts" chip
(Spanish: "Avisos del boletín"). A QR code is never a chip.

### 3.11 The other tokens

| Token | Where | What it becomes | Example |
|---|---|---|---|
| `{fill:key}` | any text | the presenter's answer, or the blank's `default`, or an orange `[hint]` | `"{fill:date} · {fill:place}"` |
| `{slide:id}` | any text | that slide's **number** in the version being shown, or "(not in this version)" | `"Look over “This month” ({slide:this-month})"` → "Look over “This month” (23)" |
| `{ui:key}` | any text | the name of a player button in the page's language | `{ui:customize} → {ui:your_details}` → "Customize → Your details" / "Personalizar → Tus datos" |
| `{lang:es}…{/lang}` | any text | marks Spanish words inside English text (screen readers read them in Spanish) | `"{lang:es}Reunión Abierta de La Viña{/lang}"` |
| `{lang:en}…{/lang}` | a Spanish slide | marks English words inside Spanish text | — |
| `{only:a,b}` / `{not:a,b}` | the start of a line of `notes` | that line only in those versions / in every version but those | `{only:short} SAY: …` |

> **Note:** `README.md` describes `{slide:history-1}` as giving "slide 12". The code gives only the number, so
> write the word yourself: `"see slide {slide:ways-to-read}"` → "see slide 18". When the slide is left out, the
> player turns "slide (not in this version)" into just "(not in this version)".

The `{ui:…}` names:

| Key | English page | Spanish page |
|---|---|---|
| `customize` | Customize | Personalizar |
| `version` | Version | Versión |
| `slides` | Slides | Diapositivas |
| `edit` | Edit | Editar |
| `add` | Add | Agregar |
| `your_details` | Your details | Tus datos |
| `prepare` | Prepare | Preparar |
| `save_share` | Save & share | Guardar y compartir |
| `notes` | Notes | Notas |
| `overview` | Overview | Vista general |
| `presenter_view` | Presenter view | Vista de quien presenta |
| `print` | Print | Imprimir |
| `full_screen` | Full screen | Pantalla completa |
| `black_screen` | Black screen | Pantalla en negro |

`{lang:…}` rules: open and close it on the same line, one at a time, with `es` or `en` only. A slide written all in
Spanish takes `lang: "es"` instead. Mistakes: `{lang:es} without its {/lang} on the same line`,
`{lang:fr} — the language is "en" or "es"`, `a {lang:…} inside another one (close the first with {/lang})`.

### 3.12 Formatting inside any text

| You write | You get |
|---|---|
| `**bold**` | **bold** |
| `_italic_` | _italic_ (an underscore inside a word, as in `@alcoholicsanonymous_gv`, stays as written) |
| `[label](https://www.aagrapevine.org/contribute)` | a link to another site |
| `[the deadlines](/contribute/#deadlines)` | a link to a page of this site: write it from its first slash, with no `/es/` and no `/aagrapevine/` (the player adds them; on the Spanish page it opens the Spanish page) |
| `grapevine@neta65.org` as a link address | an e-mail link |
| `<b>bold</b>` | refused: `no HTML in the text (use **bold**, _italic_, [label](url))` |
| `[site](www.aagrapevine.org)` | refused: `link 'www.aagrapevine.org' — https://…, a site path or an e-mail` |

### 3.13 Slides that come and go by date

| Field | Example | The slide is in the show … |
|---|---|---|
| `show_from` | `show_from: "2026-11-15"` | from that day on (Central time) |
| `show_until` | `show_until: "2026-12-31"` | up to and including that day |
| `when` | `when: "price_notice"` | only while a price-change notice is current: from `announced` through `notice_until` of a block in `config/site.yml` → `price_changes:` |

The player decides by the viewer's clock, so a copy opened later is still right. Outside its days the slide is
marked "Not today" in Customize → Slides; a presenter cannot switch it on.

A seasonal slide (passes the checker):

```yaml
  - id: "holiday-gifts"
    layout: "bullets"
    title: "Gift subscriptions for the holidays"
    show_from: "2026-11-15"
    show_until: "2026-12-31"
    optional: true
    items:
      - "A gift subscription carries the message to a sponsee, a newcomer or a family member"
      - "A group can send one to a treatment center, a jail or a public library"
      - "The official stores have gift subscriptions in print and online"
    minutes: 1
    notes: |
      SAY: Around the holidays, many members give a Grapevine or a La Viña subscription as a gift: to a sponsee, to a newcomer, or to a family member who wants to understand AA. Some groups send one to a treatment center or a jail.
      FACILITATOR TIP: This slide is in the show only from November 15 to December 31; the player leaves it out at other times.
```

The real price heads-up of `committee-meeting.yml` uses both conditions: it shows while AA Grapevine's notice is
current, and never after January 31, 2027, even if a later notice starts:

```yaml
  - id: "price-heads-up"
    layout: "table"
    title: "Heads-up: new prices from January 1, 2027"
    when: "price_notice"
    show_until: "2027-01-31"
```

Mistakes: `show_until must be a quoted "YYYY-MM-DD"`, `show_from is after show_until`,
`when: "price_notice" is the only condition`.

### 3.14 Facilitator pages and handouts

- `facilitator: true`: a page for the presenter, never projected. It is listed in **Customize → Prepare** with the
  handouts, and can be viewed and printed there. No `minutes`. A `checklist: true` page has tick boxes whose ticks
  stay on the device. The orientation workshop has two: `before-you-present` and `sixty-minute-plan`.
- `handout: true`: a page printed for the participants (**Prepare → Print**). On a facilitator page it is printed
  only; on a slide of the show it is shown AND printed (the writing workshop's `checklist` slide).
- `print: "portrait"`: on a handout, prints the page upright (otherwise sideways).
- `lang: "es"`: a handout written in Spanish (the writing workshop has four: `planificador-1`, `planificador-2`,
  `lista-de-revision`, `enviar-a-la-vina`).

Printed facilitator pages keep their notes (the instructions); printed handouts never do.

Real example (`orientation-workshop.yml`, start of `before-you-present`):

```yaml
  - id: "before-you-present"
    layout: "bullets"
    checklist: true
    facilitator: true
    eyebrow: "Facilitator"
    accent: "navy"
    title: "For facilitators: before you present"
    items:
      - "Fill every item in square brackets, on the slides and in the notes: {ui:customize} → {ui:your_details}"
      - "Look over “This month” ({slide:this-month}), “Themes and deadlines” ({slide:deadlines}) and “Coming up” ({slide:coming-up}): they stay current by themselves"
```

In the 60-minute version, `coming-up` is left out, so that last point reads "… and “Coming up” (not in this
version): they stay current by themselves".

### 3.15 The checker's rules

The checker is `check_deck` in [`tests/test_presentations.py`](../tests/test_presentations.py). The build runs its
twin, `checkDeck` in [`eleventy/filters/presentations.js`](../eleventy/filters/presentations.js), so both stop on
exactly the same things. The messages below are real.

| Rule | Fails | Message | Fix |
|---|---|---|---|
| Wording: no classroom or robot words | `"Why we are here: a short training"` | `the word 'training' breaks the site's wording rules (…)` | "workshop", "session", "shared with me" |
| Attraction, not promotion | `"Subscribe now: last chance before prices go up"` | `sounds like selling ('Subscribe now') — describe, never sell` | describe: "The official stores have gift subscriptions" |
| Only service e-mail addresses | `someone@example.com` | `e-mail 'someone@example.com' — only service addresses (aagrapevine.org, aalavina.org, aa.org, neta65.org)` | `{live:email}` or an official address |
| Only toll-free or published phone numbers | `214-555-0142` | `a personal-looking phone number '214-555-0142' (…)` | a `{live:…}` key, or leave it out |
| Known tokens only | `{live:gv_issue_theme}` | `unknown {live:gv_issue_theme}` | a key from [3.9](#39-facts-that-stay-current-live) |
| Blanks must exist | `{fill:venue}` | `{fill:venue} is not in fillins` | add the blank, or fix the key |
| A first name only in the notes | `{fill:first_name}` on a slide | `{fill:first_name} is notes_only (never on a slide)` | move it to `notes` |
| Slides named by `{slide:…}` must exist | `{slide:this-months}` | `{slide:this-months} — no such slide` | fix the id |
| A version's slides must exist | a renamed slide still in `hide` | `presets[1].hide: no slide 'milestones'` | update the list |
| Facilitator pages are never in a version | `before-you-present` in `hide` | `presets[1].hide: 'before-you-present' is a facilitator slide (never in the show)` | take it out |
| Unique ids | a copy of `pay-their-way` (slide 12) pasted right after it | `slide 13: duplicate id 'pay-their-way'` | rename one |
| Lengths | a slide of 45 minutes | `slide 33 (break): minutes (0.25–30) required` | 30 at most; split the slide |
| The deck adds up | deck `minutes: 45`, slides 88 | `the slides' minutes add up to 88, the deck says 45` | the full version must be 75–125 % of `minutes` |
| Each version adds up | `visit` too short | `version 'visit': its slides add up to 12 minutes, it says 20` | 70–130 % of the version's `minutes` |
| The disclaimer stays | no text says it | `no slide says "Not an official AA Grapevine, Inc. presentation" (keep it, as in the deck)` | keep the line somewhere in the deck's text |
| Live options | `filter: "assembly"` | `options.filter all \| workshops \| neta \| calendar \| assemblies` | `"assemblies"` |
| Live limits | `limit: 30` | `options.limit 1–24` | 24 at most |
| Colours | `accent: "blue"` | `accent one of ['grape', 'gv', 'lv', 'navy', 'vine']` | `gv` is the blue |
| Deck colour | `tone: "green"` | `tone: one of ['grape', 'gv', 'lv', 'vine']` | `vine` is the green |
| The file name | `id: "orientation"` in `orientation-workshop.yml` | `id 'orientation' must be the file name 'orientation-workshop'` | make them match |
| A version that does not exist | `version_notes: { sixty: … }` | `version_notes for an unknown version 'sixty'` | use a preset id |
| Fields a version may change | `version_fields: { short: { minutes: 1 } }` | `version_fields.short: 'minutes' is not a field a version can change on a 'agenda' slide` | use `version_minutes` |
| `print` needs a handout | `print: "portrait"` alone | `print is for a handout page (handout: true)` | add `handout: true` |
| No minutes on a facilitator page | `minutes: 2` | `a facilitator slide has no minutes` | remove it |
| An unused allowance | `allow_words: ["teach"]` with no "teach" | `allow_words 'teach' is not used on this slide (remove it)` | remove it |

The banned words (in slides and notes, any capitals): PDF(s), crawl…, scrape…, robot(s), bot(s), automatically,
automáticamente, lesson(s), lección/lecciones, trainer(s), training, quiz…, course(s), curso, curriculum,
class(es), clase(s), teach…, taught, enseñ…, capacitación, job(s). Pushy phrases: "before prices go up / rise /
increase / change", "subscribe now / today", "hurry", "last chance", "don't miss out", "limited time",
"act now". A quotation (`quote` of a `quote` slide) and the `sources` of a `credits` slide are exempt. Elsewhere, a
slide that quotes a source word for word may list the word in `allow_words` (say why in a `#` comment):

```yaml
    allow_words: ["taught"]   # the Big Book's own words, quoted word for word
```

### 3.16 Common edits, step by step

#### A. Change a slide's words

See the [quick start](#2-quick-start-change-the-words-on-a-slide). Two things to watch:

- If the slide has `version_fields`, the same words may also be in a version's own copy: change both
  (the comments above such slides say so).
- If you change a fact by hand ("Every 3rd Wednesday"), see G below: most facts should be `{live:…}` keys.

#### B. Leave a slide out

| You want | Do this | What happens |
|---|---|---|
| Gone for good | Delete its block, then see D | It disappears for everyone; presenters' own edits of it are dropped. |
| Out of one version only | Add its id to that version's `hide` (or take it out of an `only` list) | The other versions keep it. |
| Off unless a presenter wants it | `starts_off: true` (and `optional: true`) | Not in the show and not counted; a presenter turns it on in Customize → Slides; a version with `only` can list it. |
| Off after a date | `show_until: "2027-01-31"` | It leaves the show by itself after that day. |
| For the presenter, never projected | `facilitator: true`, delete its `minutes:` line (and any `optional` / `starts_off`), and take its id out of every version's `hide` and `only` | It moves to Customize → Prepare. |

Real example of the third row (`committee-meeting.yml`): the slide `topic-of-the-month` has `starts_off: true`, and
the version `topic` ("A month with a topic of the month") lists it in its `only` list, so choosing that version
shows it.

> **Note:** a presenter's own switch wins over the version. If a presenter had turned a slide on in
> Customize → Slides, it stays on for them even after you give it `starts_off: true`. The date rules
> (`show_from`, `show_until`, `when`) and `facilitator` always win.

#### C. Add a slide

1. Find a slide of the same `layout` and copy its whole block (from its `  - id:` line to the line before the next
   one).
2. Paste it where the new slide belongs.
3. Give it a **new** id: lowercase letters, digits and dashes, not used in the file (`group-ideas`).
4. Write its title, its fields, its `minutes` and notes of at least 25 words.
5. Versions: a version with `hide` shows it at once (add the id to `hide` if it should not); a version with `only`
   shows it only if you add the id.
6. Run the checker, or commit and watch Code check.

What happens: it appears in its place for everyone, also for presenters who changed the order of the slides on their
device. The card's slide count goes up by one, and the numbers of the slides after it go up by one (every
`{slide:…}` follows by itself).

#### D. Remove a slide

1. Delete its block.
2. Take its id out of every version's `hide` and `only`.
3. Search the file for the id: every `{slide:<id>}` and every agenda row with `from: "<id>"` must go or change.
4. Run the checker: it names anything left behind (`presets[1].hide: no slide '…'`,
   `{slide:…} — no such slide`, `from — no slide '…'`).

#### E. Move a slide

Move its whole block. `{slide:…}` numbers and agenda rows with `from` follow by themselves. Two side effects: a slide
moved into another part takes that part's eyebrow ("Part 4 · …") and colour, unless it has its own; and if it moves
past an agenda row's `from` slide, update that row's written `time` (see F).

#### F. Change a slide's length

1. Change `minutes:` (and `version_minutes:` if a version has its own length).
2. Check the sums: the full version must stay within 75–125 % of the deck's `minutes`, each version within 70–130 %
   of its own.
3. Update the written `time` of the agenda rows that come after the slide, so they match what the player now shows.

Example: in `orientation-workshop.yml`, change `two-magazines` (in Part 1) from `minutes: 1.5` to `minutes: 2.5`.
The checker still says OK and the site still builds, but the agenda rows that come after it move one minute later
in the player (0:24 → 0:25, 0:36 → 0:37 … 1:08 → 1:09), and Code check turns red: the test
`tests/test_presentations_core.py` ("the full version's computed agenda times are the ones the deck's author
wrote") fails until you change those `time:` values in the slide `plan`. The slide has no `version_minutes.short`,
so the 60-minute rows (in the `plan` slide's `version_fields`) move too (0:18 → 0:19 …); the test does not check
them, but update them as well so the record stays true.

#### G. A meeting day or time changed

The `{live:…}` facts follow `config/site.yml` by themselves (`meeting:` for the committee, `recurring_events:` for
the booth and La Viña's workshop; see [Settings](settings.md)). But some sentences in the decks were typed by hand.
After such a change, search each deck file for `Wednesday`, `Saturday`, `Thursday`, `5:00`, `five`, `seven` and
`p.m.`, and fix what you find, in the slides and in the notes. Real examples:

| File, slide | Typed by hand |
|---|---|
| `orientation-workshop.yml`, `coming-up` (its `intro`) | "Every 3rd Wednesday: Area GV/LV committee on Zoom, {live:meeting_time} · Every 2nd Saturday: GV/LV booth at CityWide Dallas, 5:00 – 8:00 PM" |
| `orientation-workshop.yml`, `month-at-a-glance` | the rows "3rd Wednesday" and "Usually the 4th Thursday" |
| `orientation-workshop.yml`, `district-and-area` | "3rd Wednesday, {live:meeting_time}" |
| `orientation-workshop.yml`, `thank-you` | "Our committee meets every 3rd Wednesday, {live:meeting_time}, on Zoom." |
| `committee-meeting.yml`, `next-meeting` and `open-meetings` | "Every 3rd Wednesday · …" and "Usually the 4th Thursday, …"; in the notes "third Wednesday", "at seven", "second Saturday … from 5 to 8 p.m." |
| `information-workshop.yml`, `lv-workshop` | "Usually the **4th Thursday**", and "fourth Thursday" in its notes |

Where the sentence allows it, use the fact instead: "Our committee meets {live:meeting_rule}, {live:meeting_time},
on Zoom." reads "Our committee meets every third Wednesday of the month, 7:00 – 8:00 PM Central time, on Zoom."

> **Note:** the booth's hours in the `coming-up` intro contain invisible characters (no-break spaces and a word
> joiner after the dash) that keep "5:00 – 8:00 PM" on one line. If you retype them, the line may break after the
> dash on a narrow screen; that is all.

#### H. A new PowerPoint copy, a new panel

- A new `.pptx` in `2027-2028_Panel77_GVLV/slides` whose title is the deck's `drive_title` becomes the card's
  "PowerPoint copy" at the next run (the newest one wins). Renamed the file? Change `drive_title` to the new title.
- A new Panel folder in the Drive changes `{live:panel}` in every footer at the next run. Nothing to edit here.

#### I. Spanish words in an English slide

Mark them, so screen readers read them in Spanish:

```yaml
      - heading: "{lang:es}Reunión Abierta de La Viña{/lang}"
```

A slide written entirely in Spanish (a handout for Spanish speakers) takes `lang: "es"` instead. The notes stay in
English; a Spanish sentence in them is marked the same way:
`{lang:es}EN ESPAÑOL: Escribe tu historia con tus propias palabras.{/lang}`.

#### J. Point people to a page with a QR code

On the closing slide: `qr: "/contribute/"`. As a slide of its own: a `live` slide of kind `qr`
([3.10](#310-live-slides-layout-live)). Write the page from its first slash; the code holds the full address with
`/aagrapevine/`.

### 3.17 Presenting: the player, keys and presenter view

Each card has **Present** and **Customize**, a **More** menu (Presenter view · PowerPoint copy · Reset to the
original, which appears once there is something to reset) and four **Print** buttons. Present opens the player over
the page.

| Key | Does |
|---|---|
| → ↓ Space Page Down | next slide (a clicker works too) |
| ← ↑ Shift+Space Page Up | previous slide |
| Home / End | first / last slide |
| a number, then Enter | go to that slide |
| N | speaker notes |
| O | overview (all the slides) |
| C | Customize |
| P | presenter view |
| B (or .) | black screen (press again to show the slide) |
| F | full screen |
| Esc | closes a menu, the overview or Customize first, then the player |

On a touch screen: swipe, or tap the slide (its left third goes back, the rest goes on). The page's "How presenting works" box
(`/orientation/#presenting`) lists the same.

**Presenter view** opens a second window for the presenter's own screen: this slide and the next, the notes in
large type, a timer, the clock, and a pace line ("On time", "About 2 min behind"). Either window moves both. If the
browser blocks the second window, the player offers "Presenter mode in this window".

**Link options** (handy in an e-mail or a calendar invitation):

| Address | Opens |
|---|---|
| `/orientation/?present=committee-meeting` | the deck, at its first slide |
| `/orientation/?present=committee-meeting#slide-12` | the deck at slide 12 (while a deck is open, the address keeps its slide, so a reload resumes there) |
| `/orientation/?present=committee-meeting&mode=customize` | the deck with Customize open (the card's Customize button) |
| `/orientation/?present=committee-meeting&mode=presenter` | the presenter view |
| `/orientation/?present=committee-meeting&mode=overview` | the overview |

The same work under `/es/orientation/`.

### 3.18 Printing

Every print is the presenter's **current version**: their version, their switches, edits, added slides and details.

| Mode | Button on the card | What prints |
|---|---|---|
| Slides | Slides / Diapositivas | one slide per page, landscape |
| Slides with notes | With notes / Con notas | each slide with its speaker notes and TIME line |
| Handout for participants | Handout / Hoja | three slides per page, each beside lines for notes |
| Speaker script | Script / Guion | the notes only, under each slide's number and title; the heading gives the version and the slide count ("Speaker script · Full workshop (about 90 minutes) · 59 slides"), and the length too when the version's name does not say it ("Speaker script · 60-minute version · 48 slides, about 60 minutes") |

Where: the four buttons on each card, the player's **Print** menu, and the "Print or save a copy" box under the
cards (pick the presentation and the mode). The facilitator pages and handouts print from **Customize → Prepare**:
one page at a time, or all at once (in the writing workshop: "Print the 8 handouts" and "Print all 13 pages").
The browser's print window can also save it as a
document; its name is then "<short name> – <what> – <date>", such as
"Information Workshop – Handout for participants – 2026-10-02". On paper nothing scrolls, so an over-long slide is
printed smaller.

Without JavaScript the page cannot print a deck; it offers the PowerPoint copies instead.

### 3.19 What presenters can change on their own device

Everything below is kept in the presenter's browser (localStorage) and is **never sent anywhere**. Another
computer, another browser or a private window does not have it.

| Customize tab (Spanish) | What the presenter can do |
|---|---|
| Version (Versión) | Pick a version. Their own changes stay on top of any version. |
| Slides (Diapositivas) | Turn slides on or off, drag them into another order (or Move up / Move down), Show all, Original order. Badges say why a slide is special: Optional, Yours, Edited, Updated, Facilitator, Not today, Handout (Prepare also marks a Checklist). |
| Edit (Editar) | Change the words of the slide on the screen: its title, small line, the layout's fields, highlighted box, sources line, minutes and notes. `{fill:…}`, `{live:…}`, bold, italic and links work. "Reset this slide to the original" undoes it. |
| Add (Agregar) | Add their own slide after the current one: Title and points, Text, Section break, or Discussion question (up to 60 per deck). Marked "Yours". |
| Your details (Tus datos) | Fill in the blanks, grouped by slide. |
| Prepare (Preparar) | The facilitator pages and handouts: view, tick, print. |
| Save & share (Guardar y compartir) | Save my version (.json), open a saved version, print, Reset to the original. |

Under each card, a status line sums it up: "Changed on this device: version “60-minute version”, 3 slides hidden,
2 edited. · Last shown: slide 12 of 48 · Resume" (Resume opens the deck at that slide).

**When the committee changes the deck.** Presenters' changes are kept **by slide id**:

| Committee change | What a presenter who changed that deck sees |
|---|---|
| Edits a slide the presenter had **edited** | A notice ("The committee updated a slide you had changed"), the badge "Updated", and on the slide "Changed since you edited it": **Use the new version** or **Keep mine**. (Any change to that slide's block in the file counts: its words, minutes or notes, even its colour or dates.) |
| Edits a slide the presenter only switched on or off | Nothing special: the switch stays, the new words show. |
| Adds a slide | It appears in its place, also inside the presenter's own order. |
| Deletes a slide | It disappears; the presenter's edits of it are dropped. |
| Changes a slide's `id` | For the presenter it is a new slide: their edits of the old id are dropped. |
| Renames the deck file | Their whole version of that deck is no longer found. |

**Save my version.** Customize → Save & share → **Save my version (.json)** downloads a small file named like
`orientation-workshop-my-version-2026-10-03.json`: the version, switches, order, edits, added slides, details and
ticks. **Open a file…** on another computer puts it in place (it can be undone). The file is checked strictly: a file
from another deck, a broken or very large file, or one with web code in it is refused with a reason ("It belongs to
another presentation", "It contains web code, which these presentations never take" …). It is also the way to hand
a prepared version to the next presenter.

**Reset.**

| Reset | Where | Removes |
|---|---|---|
| One slide | Customize → Edit → Reset this slide to the original | that slide's edits (in every version) |
| One deck | the card's **More → Reset to the original**, or Customize → Save & share | that deck's version, switches, order, edits, added slides, its own details and ticks (the shared details, like the service position, stay) |
| All four | **Reset all 4 to the original**, under the cards (it appears only once something was changed on this device) | everything, the shared details too |

Resetting a deck or all four asks first. Every reset then offers **Undo** for 10 seconds.

If the browser cannot store anything (some private windows), the player says once: "This browser isn't keeping your
changes … To keep them, save your version (Save & share)."

### 3.20 Offline

- A deck opened once online also opens offline: the browser keeps a copy of its JSON file (the site's offline
  helper fetches it "network first", and uses the copy without a connection or after 6 seconds).
- **Save key pages for offline** (in the Aa menu) keeps `/orientation/` and all four decks, even ones never opened.
- The facts in a kept copy still move on by the viewer's clock (the next meeting after tonight's, the new prices on
  their day), for as far ahead as the build knew. Past that, a fact says where to look ("see the Meetings page").
- A copy built more than 14 days earlier gets a notice once per visit: "The dates in this copy are from
  October 2, 2026. Open this page online to bring them up to date."
- Without JavaScript nothing plays; the cards offer the PowerPoint copies.

### 3.21 The JSON file

Each build writes one file per deck: `/orientation/presentations/<id>.json`, for example
`https://neta65.github.io/aagrapevine/orientation/presentations/orientation-workshop.json`. The player fetches it
when someone opens or prints the deck. It is the deck as written in the YAML file, plus what the build adds. It is
the same file for both languages, it is not a page (not in the sitemap, the search, the feeds or the digest), and it
is public: anyone can read the notes in it.

Trimmed real example (build of October 2, 2026):

```json
{
  "app": "gv-presentation", "schema": 1, "id": "orientation-workshop", "lang": "en",
  "title": "GVR and RLV Orientation Workshop", "short": "Orientation Workshop", "eyebrow": "Welcome",
  "footer": "NETA 65 Grapevine & La Viña Committee · {live:panel}", "minutes": 90,
  "built": "2026-10-02T23:40:50.636Z", "as_of": "October 2, 2026", "version": "3757da8073",
  "site": { "url": "https://neta65.github.io/aagrapevine/", "host": "neta65.github.io/aagrapevine" },
  "drive": { "view": "https://drive.google.com/file/d/…/view", "date": "2026-10-01" },
  "presets": [ { "id": "full", "label": { "en": "Full workshop (about 90 minutes)", "es": "…" }, "minutes": 90,
                 "hide": [], "only": null, "note": null }, … ],
  "fillins": [ { "key": "date", "label": { "en": "Date", "es": "Fecha" }, "hint": "Month DD, YYYY",
                 "default": "", "shared": false, "notes_only": false }, … ],
  "live": {
    "panel": "Panel 77 (2027–2028)",
    "meeting_next": { "value": "Wednesday, October 21, 2026",
                      "steps": [ { "from": "2026-10-22T01:00:00.000Z", "value": "Wednesday, November 18, 2026" }, … ],
                      "until": "2027-01-21T02:00:00.000Z", "fallback": "see the Meetings page" },
    "price_gv_print": { "value": "$36.00", "steps": [ { "from": "2027-01-01T06:00:00.000Z", "value": "$39.00" } ] },
    …
  },
  "slides": [
    { "id": "part-1", "layout": "section", "h": "8da8496f9a", "n_default": 7,
      "part": { "n": 1, "title": "Grapevine and La Viña basics" }, "accent": "gv",
      "eyebrow": "Part 1 · Grapevine and La Viña basics", "title": "Grapevine and La Viña basics",
      "number": 1, "subtitle": "AA's meeting in print, in English and in Spanish", "minutes": 0.25, …, "data": null },
    …
  ]
}
```

| Part | Meaning |
|---|---|
| `built`, `as_of` | When the build ran, and the day its facts were read (the title slide's "Current as of …"). |
| `version` | A fingerprint of all the slides: it changes whenever any slide changes. |
| `drive` | The PowerPoint copy found by `drive_title` (or `null`). |
| `live` | Every `{live:…}` key: a plain text, or `value` + `steps` (what it says from each moment `from`) + `until` (after which it says `fallback`). Times are UTC: `2026-10-22T01:00:00.000Z` is 8 PM Central on October 21. |
| `slides[].h` | The slide's fingerprint, from its YAML. When it changes, presenters who edited the slide see "Changed since you edited it". |
| `slides[].n_default` | Its number in the full version on the build day (`null`: not in that show, such as a facilitator page). |
| `slides[].part`, `accent`, `eyebrow` | Its part, the colour and the small line it shows, worked out from the `section` slides. |
| `slides[].data` | For a `live` slide: its rows (about a year of them) and its `limit`; for a closing slide with `qr`: the QR code. |

Tokens such as `{fill:…}` and `{live:…}` stay in the slides' texts: the player fills them in when it shows them.

**Use it to check a change:** after the run, open the file in the browser, press Ctrl+F and search for your slide's
id. If your words are there, the build has them.

---

## 4. What happens after you save

1. **You commit a deck file to `main`** (on GitHub, or by pushing from the PC).
2. **"Update & Deploy" starts at once** (a push run). It is a quick run: it refreshes Google Drive, the bulletin,
   podcasts and the daily quote, rebuilds the site's data, then builds the website **strictly** (`I18N_STRICT=1`)
   and publishes it. The deck files are read only by this build.
3. **A few minutes later the change is live.** A page may take up to about 10 more minutes to show it everywhere.
   Only one run goes at a time: if another run is going (the daily full run can take a while), yours waits for it.
   Two quick commits in a row are fine: the waiting run is replaced by the newest one, which has both.
4. **"Code check" runs too** (for every change under `config/`): the offline tests, including the deck checker
   (`tests/test_presentations.py`), and a strict test build. It never publishes anything. A red ✗ there means the
   change broke a test; the live site is not affected by it.
5. **The presenters** get the new deck the next time they open it online (the file is always asked for fresh).
   A page that is already open keeps the old one until it is reloaded (closing and opening the player again is not
   enough).

**If a deck has a problem, the build stops.** Nothing is published, and the whole site stays as it was, with every
other update of that run held back too: new Drive files, bulletin posts, the day's facts. Every later run stops the
same way until the file is fixed. So fix it, or undo it (the file's **History** on GitHub → the commit before →
copy the old version back), soon.

Where to read the problem: **Actions** → the failed "Update & Deploy" run → the job "Build & publish website" → the
step "Build the website". Look for a line like

```text
[presentations] config/presentations: 1 problem(s):
  orientation-workshop.yml: slide 5 (why-we-are-here) title: the word 'training' breaks the site's wording rules (…)
```

The same lines appear in Code check (job "Build the website", and the test `test_every_deck` in the job
"Python tests (offline)"). These problems are **not** shown on `/status/` or in the run summary.

**Safer for big changes: a pull request.** When you commit on GitHub, choose "Create a new branch for this commit and
start a pull request". Code check runs on the pull request and shows a green ✓ or a red ✗; the live site is not
touched until you merge. Merge only on a green ✓.

**Saving `config/presentations/README.md`** (or any other `.md` file) does not start "Update & Deploy": Markdown
files are documentation.

**The facts are refreshed by every build**: each push, the daily full run (scheduled 4 hours early on purpose,
because GitHub starts timed runs late; it usually starts around 5 to 7 AM Central), the midday quick run, and the
Morning check's refresh. Between builds the player still moves each fact on by the viewer's clock, from the `steps`
in the JSON file. Where a fact's data comes from a source that only the full daily run reads (prices, the editorial
calendar, the weekly open meetings, the story lines), a change there shows up after that run
(see [Automatic sources](automatic-sources.md)).

---

## 5. Where it shows on the website

| Where | English | Spanish | What |
|---|---|---|---|
| GVR / RLV 101, "Presentations" | `/orientation/#presentations` | `/es/orientation/#presentations` | the four cards, by `order`: icon in the deck's `tone`, "About 60 minutes · 49 slides", the "Also:" line, title, summary, "Who it's for", the "Stays current" chips, the device's status line, the buttons |
| One card | `/orientation/#pres-<id>` | `/es/orientation/#pres-<id>` | — |
| The player | `/orientation/?present=<id>` (+ `&mode=…`, `#slide-N`) | `/es/orientation/?present=<id>` | the slides (English), the notes, Customize, presenter view; on `/es/` the controls are Spanish |
| "Print or save a copy" | under the cards | same | the four print modes for any deck |
| "Reset all 4 to the original" | under the cards, only after a change on that device | same | — |
| "How presenting works" | `/orientation/#presenting` | `/es/orientation/#presenting` | keys, presenter view, versions, details, privacy, saving, offline, reset |
| The hero | the "Committee presentations" button and the "4 presentations" figure | "Presentaciones del comité" | — |
| "A longer workshop?" | `/orientation/#facilitators` | `/es/orientation/#facilitators` | a card that names the orientation workshop's length (90 minutes, or 60) and links to its card |
| Portfolio | `/portfolio/`, the PowerPoint copy's card | `/es/portfolio/` | "Present on the web" → `/orientation/?present=<id>`, with "A fixed copy: the web version stays current and can be customized." |
| The data file | `/orientation/presentations/<id>.json` | the same file | [3.21](#321-the-json-file) |
| Offline | kept by "Save key pages for offline" | same | the four JSON files |

**Not shown in**: the site search (it finds the GVR / RLV 101 page, never a deck or its slides), What's New, the RSS feed, the calendar feed (`/events.ics`), the monthly digest
e-mail, `/status/` and the Actions run summary. (The PowerPoint copies are Drive files: they appear on
`/portfolio/` and in the search like any other file of the `slides` folder; see
[Photos, slides and reports](photos-slides-reports.md).)

> **Note:** the "A longer workshop?" card looks for the deck with the id `orientation-workshop`. Rename that file
> and the card disappears.

---

## 6. Going further: change the code

### 6.1 How a deck file becomes a presentation

```text
config/presentations/<id>.yml
  │
  ├─ src/_data/presentations.js ............ the `presentations` list every page can use; on GitHub (I18N_STRICT=1)
  │    └─ eleventy/filters/presentations.js    a problem stops the build, on a PC it is only a warning
  │         loadDecks  → reads every *.yml (as the Python checker reads YAML)
  │         checkDeck  → the rules (the twin of check_deck in tests/test_presentations.py)
  │         shapeDeck  → the card's fields, the slide count, the chips, and per slide: h, n_default, part, accent, eyebrow
  │
  ├─ src/pages/orientation.njk ............. the cards, "Print or save a copy", "How presenting works"
  │    └─ src/_includes/macros/presentations.njk   player(lang): the player's shell, its icons and its words (#gvp-config)
  ├─ src/pages/presentations-json.11ty.js .. one JSON file per deck: filter presDeckJson → deckJson
  │                                            (liveFacts, liveData, driveCopy) → /orientation/presentations/<id>.json
  ├─ src/pages/portfolio.njk ............... "Present on the web" on the PowerPoint copy (matched by drive_title)
  └─ src/pages/sw.11ty.js .................. the JSON files in "Save key pages for offline"

In the browser:
  src/assets/js/presentations-core.js ...... window.GVP, the logic: versions, the clock, tokens, the presenter's
                                              version, "my version" files, reconciling an updated deck
  src/assets/js/presentations.js ........... the screen: the player, Customize, presenter view, printing
  src/assets/css/areas/presentations.css ... the look (class names start with gvp-)
```

### 6.2 Where things are (search for these names)

| File | Search for | What it holds |
|---|---|---|
| [`eleventy/filters/presentations.js`](../eleventy/filters/presentations.js) | `export const LIVE_KEYS`, `LIVE_KINDS`, `EVENT_FILTER_NAMES`, `LAYOUTS`, `STYLES`, `UI_KEYS`, `const BANNED`, `const PUSHY`, `PHONE_OK`, `EMAIL_OK` | the rules' lists |
| same | `export function checkDeck`, `function fieldProblems` | the checks, with their messages |
| same | `function shapeDeck`, `KIND_OF_KEY`, `KIND_ORDER` | the card's count and "Stays current" chips; parts, colours, eyebrows |
| same | `export const FALLBACKS`, `export function liveFacts` | every `{live:…}` value, and what it says when empty |
| same | `export function liveData`, `const EVENT_FILTERS` | the rows of each live slide |
| same | `function driveCopy`, `export function deckJson` | the PowerPoint copy; the whole JSON file |
| [`tests/test_presentations.py`](../tests/test_presentations.py) | `DECKS = (`, `LIVE_KEYS = {`, `LIVE_KINDS = {`, `EVENT_FILTERS = (`, `BANNED = re.compile(`, `def check_deck` | the Python checker: the same lists, kept in step |
| [`src/_data/presentations.js`](../src/_data/presentations.js) | `PRESENTATIONS_DIR`, `I18N_STRICT` | which folder is read; stop or warn |
| [`src/pages/presentations-json.11ty.js`](../src/pages/presentations-json.11ty.js) | `permalink` | the JSON's address |
| [`src/pages/orientation.njk`](../src/pages/orientation.njk) | `id="presentations"`, `o101-pres-card`, `set modes`, `data-pres-reset="all"`, `"orientation-workshop"` | the cards, the print buttons, Reset all, the "A longer workshop?" card |
| [`src/assets/js/presentations-core.js`](../src/assets/js/presentations-core.js) | `var EN = {` | the English words the player writes on slides ("Current as of {date}", "Details to be confirmed", "Online on {platform}", the TIME line) |
| same | `var LIMIT =`, `var LIMITS =`, `ADD_LAYOUTS`, `LAYOUT_FIELDS` | default list lengths; size limits; what Customize → Add and → Edit offer |
| same | `function current`, `function schedule`, `function agendaRows`, `function subst`, `function reconcile`, `function validateImport` | what is in the show; times; tokens; updated decks; imported files |
| [`src/assets/js/presentations.js`](../src/assets/js/presentations.js) | `function renderSlide`, `function buildPrint`, `OLD_COPY_DAYS`, `var UI =` | how each layout is drawn; the four print modes; the "old copy" notice (14 days); the `{ui:…}` names |
| `src/_i18n/presentations.json` | `pres.` | every word of the player, English and Spanish |
| `src/_i18n/orientation.json` | `orientation.pres_` | the cards, the print box, "How presenting works" |
| `src/_i18n/committee.json` | `committee.docs.present_web` | the Portfolio button and its note |
| [`config/presentations/README.md`](../config/presentations/README.md) | `\| Key \| Example \|` | the table of `{live:…}` keys: a test reads it |
| [`tests/fixtures/presentations/sample-workshop.yml`](../tests/fixtures/presentations/sample-workshop.yml) | — | the main sample deck: a test wants it to use every layout, every live kind and every `{live:…}` key |

### 6.3 Example: add a new fact, `{live:meeting_platform}`

Goal: a deck can write "on {live:meeting_platform}" and get "Zoom", from `platform:` under `meeting:` in
`config/site.yml`, so a change of platform reaches every deck. Six places, in one commit:

1. **`eleventy/filters/presentations.js`**, search `export const LIVE_KEYS`, add the key after `"meeting_passcode"`:

   ```js
     "meeting_passcode", "meeting_platform", "meeting_phone", "meeting_phone_passcode",
   ```

2. **Same file, function `liveFacts`**, search `out.meeting_passcode = mt.passcode;` and add a line under it:

   ```js
     out.meeting_platform = clean(c.site.meeting && c.site.meeting.platform);   // "Zoom" (config/site.yml meeting: platform)
   ```

   (`clean` is the file's own helper: it gives "" when the setting is missing.) If the fact needs words for an empty
   value, add them to `FALLBACKS` (search `export const FALLBACKS`); this one does not.

3. **`tests/test_presentations.py`**, search `LIVE_KEYS = {`, add `"meeting_platform"` to the set.
4. **`config/presentations/README.md`**, the table of keys: add a row. The last column is "—" (no fallback), or the
   fallback in quotes; the test `test_the_readme_lists_every_fallback` compares it with `FALLBACKS`.

   ```text
   | `meeting_platform` | Zoom — the committee meeting's platform (`config/site.yml`, `meeting:`) | — |
   ```

5. **`tests/fixtures/presentations/sample-workshop.yml`**: use `{live:meeting_platform}` in one text (for example
   in the notes of its meeting slide). The test `test_the_main_sample_uses_everything` wants every key used there.
6. **Use it in a deck**: `intro: "We meet {live:meeting_rule}, {live:meeting_time}, on {live:meeting_platform}."`

Nothing changes in the player: it fills in any key it finds in the JSON's `live` map. Because the key starts with
`meeting_`, a deck that uses it gets the "Committee meeting dates" chip (`KIND_OF_KEY`). Then run the tests
([6.8](#68-tests)).

### 6.4 Example: a fifth presentation

1. Copy a deck (the small sample `tests/fixtures/presentations/sample-meeting.yml` is a good start) to
   `config/presentations/<new-id>.yml`. Set `id: "<new-id>"`, a new `order` (5), the titles, the card in both
   languages, the versions and the slides. Keep the line "Not an official AA Grapevine, Inc. presentation".
2. Run the checker on it.
3. **`tests/test_presentations.py`**: add the id to `DECKS = (`. In `test_the_four_decks`, the line with
   `"each deck has its own order"` expects 4 different orders: change the 4 to 5.
4. **`tests/test_presentations_core.py`**: search `{"orientation-workshop", "information-workshop",
   "writing-workshop", "committee-meeting"}` and add the id.
5. **`src/_i18n/presentations.json`**: four texts say "four" or "4": `pres.details_shared`, `pres.reset_all_note`,
   `pres.reset_all_confirm`, `pres.reset_all_done` (English and Spanish). `tests/test_presentations_core.py` checks
   the exact words of `pres.reset_all_note` (search `Reset all 4 to the original`): change it there too.
6. **`config/presentations/README.md`**: add the file to the table at the top.

What follows by itself: the fifth card, its JSON file, "5 presentations" in the hero, "Reset all 5 to the
original", the offline copy, and (with a `drive_title`) the PowerPoint link and the Portfolio button.

### 6.5 Example: change what a fact says when it has nothing to say

In `eleventy/filters/presentations.js`, `FALLBACKS`:

```js
  meeting_next: "see the Meetings page on our website",
```

Then change the same key's last column in the README's table of keys (`"see the Meetings page on our website"`), or
`test_the_readme_lists_every_fallback` fails. Re-read the decks' sentences that use the key: the new words must read
well in them.

### 6.6 Example: the wording rules

The banned words and pushy phrases are written twice: `BANNED` and `PUSHY` in `eleventy/filters/presentations.js`,
and `BANNED` and `PUSHY` in `tests/test_presentations.py`. Change both the same way;
`tests/test_presentations_build.py` checks that the two checkers report exactly the same lines. For one slide that
quotes a source word for word, use `allow_words` instead ([3.15](#315-the-checkers-rules)).

### 6.7 Change the words of the buttons and cards

The player's words are `pres.…` keys in `src/_i18n/presentations.json`, the cards' words `orientation.pres_…` keys
in `src/_i18n/orientation.json`, each with `en` and `es`:

```json
  "orientation.pres_present": { "en": "Present", "es": "Presentar" },
```

A key missing altogether stops the strict build. A key that has its English but not its Spanish text does not stop it:
the Spanish page shows the English, and `tests/test_i18n_keys.py` turns Code check red. A button named in the notes
with `{ui:…}` follows by itself.
Some words are pinned by tests (for example `pres.reset_deck` must stay "Reset to the original" / "Volver al
original", and the player's words follow the same wording rules as the decks); a test that fails names the key.
See [Pages and code](pages-and-code.md) for the i18n files in general.

### 6.8 Tests

| Command (from the repository folder) | What it checks |
|---|---|
| `.venv\Scripts\python.exe tests\test_presentations.py config\presentations\writing-workshop.yml` | one deck, with readable messages |
| `.venv\Scripts\python.exe -m unittest tests.test_presentations -v` | the four decks (exactly these four files, each with its own `order`), and the checker itself |
| `.venv\Scripts\python.exe -m unittest tests.test_presentations_build -v` | the build side: the JavaScript checker gives the same lines as the Python one; the sample decks use everything; the JSON's shape; the facts at fixed dates; the README lists every fallback (builds the sample decks in a temporary folder) |
| `.venv\Scripts\python.exe -m unittest tests.test_presentations_core -v` | the player's logic: facts switching on time, versions, the clock and the agenda, tokens, presenters' versions, "my version" files, Reset; and the four real decks (every text shows, the numbering, the full version's agenda times, each version's length) |
| `python -m unittest discover -s tests` | everything (what Code check runs) |

The `_core` tests need Node.js; the `_build` tests and the four-real-decks test of `_core` also need the site's tools
(`npm ci`). Without them those tests are skipped, not failed.

### 6.9 Look at the result on the PC

```powershell
npm ci                                                   # once
npm start                                                # http://localhost:8080/orientation/ — saving a deck rebuilds
$env:ONLY = "orientation,presentations"; npm start       # faster: only /orientation/ and the decks' JSON
$env:PRESENTATIONS_DIR = "tests/fixtures/presentations"; npm start   # the two sample decks instead of the real ones
$env:MONTHLY_NOW = "2026-12-15"; npm start               # the facts as the build would read them on that day
$env:I18N_STRICT = "1"; npx @11ty/eleventy               # stop on a deck problem, as on GitHub
```

A `$env:` value stays set until you close PowerShell (or `Remove-Item Env:PRESENTATIONS_DIR`). Without
`I18N_STRICT`, a deck problem is only a warning in the console: `[presentations] config/presentations: 1 problem(s): …`.
See [Automation and troubleshooting](automation-and-troubleshooting.md) for setting up the PC.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Update & Deploy" fails at "Build & publish website"; the site did not change at all | a deck problem stops the strict build | Open the step "Build the website", read the `[presentations] …` lines, fix the file (or undo it from its History). GitHub also e-mails a "run failed" notice to whoever pushed the change. |
| `not valid YAML: …` with a line and a column | a missing quote, a tab, a line indented wrongly, an unquoted text that starts with `{` or holds `: ` | Look at that line and the one above it ([3.2](#32-yaml-rules-that-matter-in-these-files)). |
| `… left out — the player cannot use it (an id, its slides and a first version are needed)` | the file name is not a valid id (capitals, spaces), or `slides:` / `presets:` is empty. On GitHub the build stops, as for any problem; in a PC build without `I18N_STRICT` the card is simply missing | Rename the file in lowercase with dashes, or restore the lists. |
| Code check is red, "Update & Deploy" is green | a test failed; the build is fine. Often: the agenda's written times ([3.16 F](#f-change-a-slides-length)), a new `{live:…}` key missing from the README or the sample deck ([6.3](#63-example-add-a-new-fact-livemeeting_platform)), a new deck not in `DECKS` | Open the job "Python tests (offline)"; the failing test says what is wrong. |
| The change is not on the site after 20 minutes | the run is still waiting or failed, or the browser shows an old page | Check Actions; reload the page; open the deck's JSON and look at `built`. |
| A slide shows `{live:something}` or `{fill:something}` as typed | a misspelled key in a presenter's own edit (in the files, the checker refuses it) | Fix the spelling in Customize → Edit. |
| An orange `[hint]` on a slide | an empty blank | The presenter fills it in (Customize → Your details), or the committee gives the blank a `default`. |
| A fact says "see the Meetings page" (or similar) | no data for it, or a kept copy older than the dates the build knew | Check the setting it comes from ([3.9](#39-facts-that-stay-current-live)); open the page online. |
| "The dates in this copy are from …" | the deck file kept for offline use is more than 14 days old | Open `/orientation/` online once. |
| No "PowerPoint copy" link, no "Present on the web" button | `drive_title` is not exactly the Drive file's title (a month and year in the file name stay in its title), or the file is not in the panel folder or not shared | Compare the title shown on `/portfolio/` with `drive_title`. |
| A slide is missing from the show | the version's `hide`, `starts_off`, its dates, `when: "price_notice"`, a facilitator page, or the presenter turned it off | Customize → Slides shows its badge ("Not today", "Facilitator" …); **Show all** turns the switches back on. |
| "This version has no slides. Turn some on in Customize → Slides." | the presenter turned every slide off | Customize → Slides → Show all, or Reset to the original. |
| On `/es/`, the notes say "Customize" instead of "Personalizar" | the notes typed the button's name | Write `{ui:customize}`. |
| A presenter's changes are not on their other computer | changes stay in one browser | Save my version → Open a file… on the other computer. |
| "This browser isn't keeping your changes …" | a private window, or storage blocked | Save the version file before closing the page. |
| The presenter view did not open | the browser blocked the second window | Allow pop-ups for the site, or use "Presenter mode in this window". |
| "Changed since you edited it" on a slide | the committee changed a slide the presenter had edited | Use the new version, or Keep mine. |
| The card shows fewer slides than the file has | facilitator pages, slides that start off and slides outside their dates are not counted | Nothing to fix. |
| "Reset all 4 to the original" is not there | nothing was changed on this device yet | Expected: it appears after the first change. |

**Where problems are reported:** the "Update & Deploy" run (step "Build the website"), the two Code check jobs,
the checker on the PC, and a local build's console. Deck problems never appear on `/status/` or in the run summary.
See [Automation and troubleshooting](automation-and-troubleshooting.md).

---

## 8. Good practice and AA principles

- **Anonymity.** No names, no faces, no personal phone numbers or e-mail addresses, on slides **or in notes**: the
  notes are in the public JSON file. A presenter is a service position (`{fill:presenter}`). A first name appears
  only in the presenter's own notes, through a `notes_only` blank (`{fill:first_name}`).
- **Service contacts only.** E-mail addresses on aagrapevine.org, aalavina.org, aa.org or neta65.org (better:
  `{live:email}` for grapevine@neta65.org). Phone numbers that are toll-free or that the site itself publishes
  (better: their `{live:…}` keys).
- **Attraction rather than promotion.** Describe, never sell: no "subscribe now", "hurry", "last chance",
  "before prices go up". A price change is plain information.
- **Credit and the disclaimer.** Keep "Not an official AA Grapevine, Inc. presentation" and the credit line under
  every quotation and the Preamble, word for word, as in the decks. No logos, covers or artwork of NETA 65, AA,
  Grapevine or La Viña.
- **The site's words.** "Document", never "PDF" (the print window "can also save it as a document"); "stays current",
  never "automatically"; session, workshop, facilitator, presenter, review questions, never lesson, course, class,
  training, trainer, quiz, teach or taught; GVR / RLV service is a "position", never a "job". A word-for-word
  quotation keeps its own words.
- **Public by default.** Everything in the Drive folder is public, the PowerPoint copies in
  `2027-2028_Panel77_GVLV/slides` included, and so are the decks and their notes on the site.
- **Keep slide ids** once a deck is on the site; presenters' own versions depend on them.
- **Let facts be facts.** Use `{live:…}` keys for dates, times, prices, phone numbers and Zoom IDs, and write the
  sentence so the "nothing to say" words fit too.
- **Check before you publish.** Run the checker, or use a pull request and merge on a green ✓. A deck mistake on
  `main` holds back every update of the site until it is fixed.

---

## 9. See also

- [How-to guides: index](README.md)
- [The Drive panel folder](drive-panel-folder.md) — the `slides` folder, file titles, the Panel folders (`{live:panel}`)
- [File types](file-types.md) — what a `.pptx` becomes
- [Flyers and events](flyers-and-events.md) — the events behind `{live:assembly_next}` and the `events` live slides
- [Bulletin](bulletin.md) — the posts behind the `bulletin` live slide
- [Photos, slides and reports](photos-slides-reports.md) — the PowerPoint copies on `/portfolio/`
- [Booth display](booth.md)
- [Settings](settings.md) — `meeting:`, `recurring_events:`, `phone_access:`, `price_changes:`, `lavina_weekly_open:`,
  and the six sessions of `config/orientation.yml`
- [Translations](translations.md) — `data/translations/overrides.yml` (La Viña's themes in English) and the i18n files
- [E-mail and alerts](email-and-alerts.md) — "run failed" e-mails and the Morning check
- [Automatic sources](automatic-sources.md) — the shop prices, the editorial calendar, the weekly open meetings,
  the story lines
- [Pages and code](pages-and-code.md) — `/orientation/` and the other pages, the i18n files, the offline list
- [Automation and troubleshooting](automation-and-troubleshooting.md) — the workflows, manual runs, the PC setup
- Repository files: [`config/presentations/README.md`](../config/presentations/README.md),
  [`orientation-workshop.yml`](../config/presentations/orientation-workshop.yml),
  [`information-workshop.yml`](../config/presentations/information-workshop.yml),
  [`writing-workshop.yml`](../config/presentations/writing-workshop.yml),
  [`committee-meeting.yml`](../config/presentations/committee-meeting.yml),
  [`tests/fixtures/presentations/`](../tests/fixtures/presentations/),
  [`tests/test_presentations.py`](../tests/test_presentations.py),
  [`src/_data/presentations.js`](../src/_data/presentations.js),
  [`eleventy/filters/presentations.js`](../eleventy/filters/presentations.js),
  [`src/pages/presentations-json.11ty.js`](../src/pages/presentations-json.11ty.js),
  [`src/assets/js/presentations-core.js`](../src/assets/js/presentations-core.js),
  [`src/assets/js/presentations.js`](../src/assets/js/presentations.js)
