# Presentations

The presentations on the GVR / RLV 101 page (`/orientation/`, "Presentations": three workshops and the monthly
committee meeting) are made from the files in this folder: **one file per presentation**, written in plain text
(YAML). The site turns each file into a presentation that opens in a pop-up player, with speaker notes, a presenter
view, versions, printing, and the presenter's own changes kept on their own device.

| File | Presentation |
|---|---|
| `orientation-workshop.yml` | GVR and RLV Orientation Workshop |
| `information-workshop.yml` | Grapevine and La Viña Information Workshop |
| `writing-workshop.yml` | Grapevine and La Viña Writing Workshop |
| `committee-meeting.yml` | Grapevine and La Viña Monthly Committee Meeting |

The content of the presentations stays in **English**. On the Spanish page the buttons and the cards are in
Spanish, and each presentation is marked "(en inglés)".

**The PowerPoint copies are separate.** The `.pptx` files in the committee's Drive folder (`slides`, listed on
the Portfolio page) are snapshots made on October 1, 2026. Changing a file here does not change them, and changing
them does not change the presentations on the site. The card's "PowerPoint copy" link opens the Drive file whose
title is the presentation's `drive_title`.

## What stays current by itself

Every time the site is rebuilt (each daily update), the presentations get the day's facts from the site's own
data, the same facts the other pages show:

- the committee's next meeting dates, the rule ("every third Wednesday of the month"), the time and the Zoom details
  (from `config/site.yml`, `meeting:`); the meeting's own date and month (the committee meeting's title slide) and
  the meeting after it (a slide shown during the meeting); and joining it by phone: Zoom's dial-in number and the
  callers' passcode, as the Accessibility page gives them (`config/site.yml`, `phone_access:`). "The next meeting"
  (`meeting_next`) moves on as soon as a meeting ends: a workshop later that evening names next month's. The
  meeting's own date (`meeting_day`), its month and the meeting after it move on at midnight Central after the
  meeting day, so the committee meeting's slides read right during AND after the meeting;
- La Viña's monthly virtual workshop: its next dates, time and Zoom ID;
- the weekly open meetings of the Meetings page — the Grapevine Weekly Open and the Reunión Abierta de La Viña: their
  day, time and Zoom room (`data/site/weekly_open.json`, `config/site.yml` `lavina_weekly_open:`);
- the events on the Events page (workshops, assemblies, the CityWide booth …), and the next NETA 65 assembly;
- the story deadlines and themes of the editorial calendar (the Share your story page);
- this month's Grapevine and La Viña issues and the next ones, with their themes, and this month's toolkit ideas
  (the Monthly page). The month's facts change together at midnight Central on the 1st, so "this issue" and "next
  issue" never skip a month, even on a copy opened after the month changed;
- the 1-year subscription prices and an announced price change (`config/site.yml`, `price_changes:`): before the
  day, the slides show today's price and switch to the new one at midnight Central on the day itself;
- Grapevine's Book of the Month and La Viña's Libro del mes, the story lines for recording a story by phone (the
  Share your story page), the committee bulletin's newest posts, and QR codes.

**A copy opened later stays right.** A presenter may open a presentation that was saved days earlier (offline, or on a
slow connection at the venue). So each fact comes with what it will say next — the next four meetings, workshops,
deadlines and assemblies, the issues of the next months — and switches by the viewer's own clock. A live slide's list
carries every date known for about a year; the player leaves out the dates already past and then shows the slide's
`limit`.

**A fact with nothing to say says where to look.** When the data has nothing (no deadline known yet, a Book of the
Month whose offer is over) or a copy is older than the last date the build knew, the slide never shows a label with
nothing after it: each fact has a short phrase of its own instead (the last column of the table of facts below), and
a list with nothing in it points to the page. Write your sentences so that phrase reads well in them too ("Next
meeting: see the Meetings page"). You never need to update a date, a price or a phone number in these files.

## Check your changes

Before saving a change to the site, run the checker on the file you changed:

    .venv\Scripts\python.exe tests\test_presentations.py config\presentations\writing-workshop.yml

It prints `OK`, or each problem with the slide's number and id. All four at once:

    .venv\Scripts\python.exe -m unittest tests.test_presentations -v

The site's build checks the same things (`src/_data/presentations.js`): on GitHub a file with a problem stops the
build, and the site stays as it was until the file is fixed. To look at the result on your computer, build the site
(see the main README) and open `/orientation/`.

To try the player without the real presentations, build with the two sample decks of
`tests/fixtures/presentations/` instead: set `PRESENTATIONS_DIR=tests/fixtures/presentations` before the build.
They use every kind of slide and every field below, so they are also good examples to copy from.

## The parts of a file

Write every text in double quotes (`"…"`), or as a block that starts with `|` on its own line (for notes and long
texts). A value that starts with `{` must be in quotes, or the file cannot be read.

```yaml
id: "information-workshop"          # the file's name, without .yml
order: 2                            # its place among the cards on /orientation/ (1–4)
lang: "en"                          # always "en"
title: "Grapevine and La Viña Information Workshop"
short: "Information Workshop"       # the short name in the player's header
eyebrow: "Information Workshop"     # the small line above the titles before the first part
footer: "NETA 65 Grapevine & La Viña Committee · {live:panel}"
minutes: 60                         # the length of the full version
icon: "book-open"                   # the card's icon (a Lucide icon name)
tone: "gv"                          # the card's colour: gv · lv · vine · grape
drive_title: "Grapevine and La Viña Information Workshop"   # the PowerPoint copy's title in the Drive
card:                               # the card on /orientation/, in English AND Spanish
  title:    { en: "…", es: "…" }
  summary:  { en: "…", es: "…" }    # one or two sentences: what it is for
  audience: { en: "…", es: "…" }    # who it is for, where it is used
presets: [ … ]                      # the versions (below)
fillins: [ … ]                      # the presenter's blanks (below)
slides: [ … ]                       # the slides (below)
```

The Spanish texts are written by hand (Latin-American Spanish, "tú").

### Versions (`presets`)

A presentation can have several versions — the full one, a shorter one, a 20-minute visit. The presenter picks
one in Customize → Version. **The first one is the full version**, with every slide that is not switched off.

```yaml
presets:
  - id: "full"
    label: { en: "Full workshop (about 60 minutes)", es: "Taller completo (unos 60 minutos)" }
    minutes: 60
  - id: "late"
    label: { en: "Running late (about 48 minutes)", es: "Si vas con retraso (unos 48 minutos)" }
    minutes: 48
    hide: ["history-1", "history-2"]          # these slides are left out
    note: { en: "Leaves out the slides marked optional.", es: "Deja fuera las diapositivas opcionales." }
  - id: "visit"
    label: { en: "20-minute group visit", es: "Visita de 20 minutos a un grupo" }
    minutes: 20
    only: ["title", "about", "closing"]       # ONLY these slides, in the presentation's order
```

A version has `hide` or `only`, never both. `only` shows the slides it names even when they start switched off
(`starts_off`). The checker compares each version's `minutes` with the minutes of its slides — a slide's
`version_minutes` for that version when it has them, else its `minutes`.

### The presenter's blanks (`fillins`)

Blanks like the date and the place are filled in by each presenter in Customize → Your details. Their answers stay
on their own device. A blank left empty shows on the slide as an orange `[hint]`.

```yaml
fillins:
  - key: "date"
    label: { en: "Date", es: "Fecha" }
    hint: "Month DD, YYYY"
  - key: "presenter"
    label: { en: "Presenter's service position", es: "Puesto de servicio de quien presenta" }
    hint: "Service position"
    default: "Area 65 Grapevine / La Viña Chair"
    shared: true                    # one answer for all four presentations
  - key: "first_name"
    label: { en: "Your first name (only in your notes)", es: "Tu nombre (solo en tus notas)" }
    hint: "first name"
    shared: true
    notes_only: true                # may appear ONLY in the notes, never on a slide
```

A slide uses a blank as `{fill:date}`.

### Slides

Each slide has an `id`, a `layout`, a `title` and its `notes`. **Keep an `id` once the presentation is on the
site**: presenters' own changes (a slide they hid, edited or moved) are kept by it. A slide whose id changes is a
new slide for them.

| Field | |
|---|---|
| `id` | lowercase letters, digits and dashes, unique in the file (`history-1`) |
| `layout` | the kind of slide (the list below) |
| `title` | the slide's title |
| `eyebrow` | the small line above the title. Left out: the current part ("Part 3 · Inside an issue …"), or the file's `eyebrow` before the first part — except on a `qa` or `credits` slide, which then has none (as the PowerPoint drew them; write one to show one, like "Closing"). Write it in normal letters; the player shows it in capitals |
| `notes` | the speaker notes: one paragraph per line, each starting with its label — `SAY:` `DO:` `ASK:` `IF TIME, ASK:` `TIP:` `FACILITATOR TIP:` `SOURCES:` `TRANSITION:` `WATCH FOR:` … At least 25 words. No `TIME:` line: give `minutes` instead |
| `minutes` | how long the slide takes (0.25 to 30; a minute and a quarter is `1.25`). The player writes the timing line of the notes ("about 2 minutes; you should be at about 0:08") for the version being shown |
| `version_minutes` | how long the slide takes in one version, when that differs: `{ short: 7 }` (0.25 to 30, a version's `id`). That version's schedule, timing lines and the checker's sums use it |
| `version_fields` | the slide's own text in one version: `{ short: { title: "Today's plan (about 60 minutes)" } }` — any field of its layout (below), its `title`, `eyebrow`, `source` or `takeaway` (an activity's `duration`, a break's `body` …). Not `kind`, `options` or `qr`, which are the same in every version. The checker holds the slide as each version shows it to the same rules. A presenter's own change (Customize → Edit) of a field that has words of its own in any version stays in the version they changed it in: it is stored for that version alone, so the other versions keep their words (typing the version's own words back removes the change; "Reset this slide to the original" removes the changes of every version). A change of any other field, and of `minutes`, applies to every version |
| `optional` | `true`: a slide that can go when running late |
| `starts_off` | `true`: an optional slide that starts switched off (the presenter turns it on in Customize → Slides) |
| `facilitator` | `true`: never shown to the room; it is in Customize → Prepare (checklists, timing plans, pages for the chair). No `minutes` |
| `handout` | `true`: a page printed for the participants — a `facilitator` page (Prepare → Print), or a slide that is shown AND printed |
| `print` | on a `handout` page: `"portrait"` to print it upright. Left out: it prints `"landscape"` (sideways) |
| `accent` | a colour: `gv` `lv` `vine` `grape` `navy`. On a `section` slide, the colour of its part: the slides after it take it. On any other slide, the colour of that slide only |
| `lang` | `"es"`: a slide written in Spanish (a handout, an announcement to read aloud); the player marks it as Spanish. Left out: English |
| `source` | the small "Sources: …" line at the bottom |
| `takeaway` | the highlighted box at the bottom |
| `version_notes` | notes shown (highlighted) only in one version: `{ late: "RUNNING LATE: …" }`. For a line of the notes that only some versions need, or that some leave out, see `{only:…}` below |
| `show_from` / `show_until` | `"YYYY-MM-DD"`: the slide is only in the presentation on those days (Central time, both days included) |
| `when` | `"price_notice"`: only while a price-change notice is current (from `announced` through `notice_until` in `config/site.yml`) |
| `allow_words` | rare: a word of the wording rules a slide may use because it quotes a source word for word (`["teach"]`); say why in a comment |

### Kinds of slides (`layout`)

| Layout | Its fields |
|---|---|
| `title` | `subtitle`, `lines` (a list). The player adds "Current as of <date>" by itself |
| `section` | `number` (1, 2 … or "A"), `subtitle` — starts a part |
| `bullets` | `items` (a list; an item can have sub-items: `{ text: "…", items: ["…", "…"] }`), `numbered: true`, `checklist: true` |
| `columns` | `columns` (2 to 4, each `{ heading, gloss, text or items, accent }`), `style: "panels"`, `"cards"` or `"plain"`, `checklist: true` (tick boxes in place of the bullets: a checklist printed in two languages …). Four columns are drawn two by two |
| `table` | `header` (a list), `rows` (a list of lists), `widths` (`[2, 3, 3]`), `first_col_bold: true` |
| `agenda` | `items`: `{ time: "0:08", title, detail, from: "<slide id>" }` — with `from`, the player works out the time for the version being shown, and leaves out a row whose slides are all left out |
| `quote` | `quote` (word for word) and `credit` (the credit line exactly as on the slide). A short quote sits in the middle of the slide; a long one (the Preamble) is set large enough to read from the back of a room |
| `activity` | `steps` (a list), `duration` (the time card's minutes), `materials` (a list) |
| `qa` | `prompts` (a list), `note` |
| `resources` | `links`: `{ label, url, note }` |
| `credits` | `sources` (a list), `note`, `disclaimer: true` |
| `closing` | `message`, `lines` (a list), `qr: "/"` (a QR code for a page of the site or an https address) |
| `text` | `body`: paragraphs separated by an empty line; a line starting with "- " is a list item. `style: "script"`: an announcement to read aloud, on a tinted card (parts the reader fills in written ‹like this›); `style: "break"`: a pause, centred on the slide |
| `flow` | `steps`: 2 to 6 boxes `{ title, text }` with arrows between them |
| `live` | `kind` (below), `intro` (a sentence above it), `options` |

### Slides that show the site's facts (`layout: "live"`)

| `kind` | What it shows | `options` |
|---|---|---|
| `meeting` | the committee's next meeting dates, the rule, the time, the Zoom ID and passcode | `limit` (3; 12 = the year) |
| `lv-workshop` | La Viña's next monthly virtual workshops, the time, the Zoom ID, the contact | `limit` (3) |
| `events` | the next events of the Events page (never the committee meetings). A monthly event, like the CityWide booth, takes one row: its next date — or, with `series: "all"`, a row for each of its dates (a list of the year ahead). Each row says what the Events page says: a hybrid event shows its place AND "Online on Zoom", and an event whose details are not final says "Details to be confirmed" | `limit` (5), `filter`: `all`, `workshops`, `neta` (NETA 65's own events), `calendar` (Grapevine's and La Viña's calendars) or `assemblies` (NETA 65's assemblies), `series: "all"` (every date of a monthly event; left out: its next date only) |
| `deadlines` | the next story deadlines: date, issue, theme (La Viña's themes in Spanish, with the English; a machine translation is marked as one). An issue with two themes is never cut in half | `pub`: `gv`, `lv` or `both`; `limit` (6); `limit_each`: with `both`, this many of EACH magazine (`limit: 6, limit_each: 3` = the next three of each) |
| `issues` | this month's Grapevine and La Viña issues and their themes (La Viña's with the English, marked when a machine translated it) | — |
| `monthly` | this month's toolkit ideas (the Monthly page) | `limit` (3) |
| `prices` | the 1-year print and online prices of both magazines; during a price notice, the new prices and their date | `pub` |
| `botm` | the Book of the Month of Grapevine and of La Viña | — |
| `bulletin` | the committee bulletin's newest posts | `limit` (3) |
| `qr` | a QR code | `url` (a page of the site like `"/contribute/"`, or an https address), `caption` |

The dated lists (meetings, La Viña's workshops, events, deadlines) carry every date known for about a year; the
player leaves out the ones already past when the slide is shown (and keeps a monthly event's next date only, unless
`series: "all"`) and then shows `limit` of them, so a copy opened weeks later still fills the slide.

```yaml
  - id: "next-meetings"
    layout: "live"
    kind: "meeting"
    title: "The committee's next meetings"
    intro: "We meet {live:meeting_rule}, {live:meeting_time}, on Zoom."
    options: { limit: 3 }
    minutes: 1.5
    notes: |
      SAY: …
```

## Inside any text

- `**bold**`, `_italic_` and links: `[the guidelines](https://www.aagrapevine.org/guidelines-contributing-grapevine)`.
  A link (and a `url`) is an `https://` address, a page of the site written from its first slash
  (`/contribute/#deadlines` — no `/es/` and no `/aagrapevine/`: the site adds them), or an e-mail address.
- `{fill:date}` — one of the presenter's blanks.
- `{slide:history-1}` — "slide 12": that slide's number in the version being shown ("not in this version" when it is
  left out). Use it instead of writing slide numbers.
- `{lang:es}…{/lang}` — words in Spanish inside an English text: a few words, a paragraph, or a whole line of the
  notes (`{lang:es}EN ESPAÑOL: …{/lang}`). The player marks them as Spanish, so a screen reader reads them in Spanish.
  Open and close it on the same line, one at a time (`{lang:en}…{/lang}` marks English words in a Spanish text). A
  slide written all in Spanish takes `lang: "es"` instead.
- `{ui:customize}` — a button of the player, by its name in the language of the page ("Customize" on the English page,
  "Personalizar" on the Spanish one). Write "{ui:customize} → {ui:your_details}" instead of the English names. The
  buttons: `customize`, `version`, `slides`, `edit`, `add`, `your_details`, `prepare`, `save_share`, `notes`,
  `overview`, `presenter_view`, `print`, `full_screen`, `black_screen`.
- `{only:short}` or `{not:short,visit}` at the START of a line of the notes: that line is only in those versions, or in
  every version but those (their `id`s, separated by commas) — a TRANSITION to a slide another version leaves out, a
  paragraph for running late.
- `{live:…}` — a fact of the day, filled in when the slide is shown. The last column is what it says when it has
  nothing to say (no data, an offer that is over, a copy opened after the last date the build knew); "—": always
  known, or empty by design — write it where an empty value reads well:

| Key | Example | When there is nothing to say |
|---|---|---|
| `site`, `site_url` | neta65.github.io/aagrapevine · https://neta65.github.io/aagrapevine/ | — |
| `email` | grapevine@neta65.org | — |
| `panel` | Panel 77 (2027–2028) | — |
| `as_of` | October 2, 2026 — the day the facts were read | — |
| `month`, `year` | October 2026 · 2026 (they switch on the 1st, for a year ahead) | — |
| `meeting_next` | Wednesday, October 21, 2026 — the next meeting, until it ends: from 8 PM on a meeting night it is next month's ("the next meeting" in a workshop) | "see the Meetings page" |
| `meeting_day` | Wednesday, October 21, 2026 — the meeting's own date, until midnight Central after its day: during AND after tonight's meeting it is still tonight's (the committee meeting's title slide) | "see the Meetings page" |
| `meeting_after` | Wednesday, November 18, 2026 — the meeting after `meeting_day`: for a "Next meeting" slide shown DURING a meeting. It moves on with `meeting_day`, at midnight | "see the Meetings page" |
| `meeting_month` | October 2026 — the month of `meeting_day`, switching with it (the title slide's "October 2026 meeting") | "Monthly" |
| `meeting_rule` | every third Wednesday of the month | — |
| `meeting_time` | 7:00 – 8:00 PM Central time | — |
| `meeting_zoom_id`, `meeting_passcode` | the committee meeting's Zoom ID and passcode | — |
| `meeting_phone` | +1 346 248 7799 (Houston) — Zoom's dial-in number for joining by phone (the first of `phone_access:`) | "see the Accessibility page" |
| `meeting_phone_passcode` | what a caller types as the passcode: the chair's numbers-only phone passcode in `phone_access:` (or the meeting's passcode, when it is numbers only). Empty until it is set there | — |
| `lv_workshop_next` | Thursday, October 22, 2026 — the next one, until it ends | "see La Viña's events calendar at aalavina.org" |
| `lv_workshop_time`, `lv_workshop_zoom_id` | 2:00 – 3:00 PM Central time (3:00 PM Eastern) · its Zoom ID | — |
| `price_gv_print`, `price_gv_digital`, `price_lv_print`, `price_lv_digital` | $36.00 … — the 1-year price in effect on the day the slide is shown | "see the Shop page" |
| `price_change_note` | "Prices change on January 1, 2027: …", then "New prices since January 1, 2027." — empty when no notice is current | — |
| `price_change_date` | January 1, 2027 (while a notice is current; empty otherwise) | — |
| `gv_issue` | October 2026 · Loneliness — this month's issue | "see aagrapevine.org" |
| `gv_next_issue` | November 2026 · Classic Grapevine — the next issue | "see aagrapevine.org" |
| `gv_theme` | Loneliness — this month's theme alone, without the month | "see aagrapevine.org" |
| `lv_issue` | September–October 2026 · Servicio en AA — the issue of these months. A La Viña theme has its English words in brackets when they are written by hand ("La alegría de vivir (The Joy of Living)"); a machine's are left out | "see aalavina.org" |
| `lv_next_issue` | November–December 2026 · La alegría de vivir (The Joy of Living) — the next issue | "see aalavina.org" |
| `lv_theme` | Servicio en AA — the theme alone | "see aalavina.org" |
| `next_deadline_gv` | November 1, 2026 — June 2027: Emotional Sobriety — until that day is over, then the next one | "see aagrapevine.org for Grapevine's themes" |
| `next_deadline_lv` | October 17, 2026 — May–June 2027: Recaídas (Relapses) — the English as in `lv_issue` | "see aalavina.org for La Viña's themes" |
| `botm` | the title of Grapevine's Book of the Month, until its offer ends | "see aagrapevine.org's Book of the Month" |
| `botm_lv` | the title of La Viña's Libro del mes, until its offer ends | "see aalavina.org's Libro del mes" |
| `gv_audio_phone`, `lv_audio_phone` | (559) 726-1216 · (559) 670-1601 — the story lines for recording a story by phone | "see the Share your story page" |
| `assembly_next` | NETA 65 Spring Assembly 2027 · Fri, Mar 19 – Sun, Mar 21, 2027 — the next NETA 65 assembly until it is over, then the one after it ("(details to be confirmed)" while the Events page says so) | "see the Events page" |
| `gv_open_meeting` | Wednesdays, 11:00 AM Central (noon Eastern) — the Grapevine Weekly Open | "see the Meetings page" |
| `lv_open_meeting` | Thursdays, 11:00 AM Central (noon Eastern), starting Nov. 5, 2026 — the Reunión Abierta de La Viña ("since Nov. 5, 2026" from that day) | "see the Meetings page" |
| `open_meeting_zoom` | Zoom 871 2036 8287, passcode 238047 — the weekly open meetings' Zoom room | "see the Meetings page" |

**Pair the meeting keys that move on together.** `meeting_day`, `meeting_month` and `meeting_after` move on together,
at midnight Central after the meeting day; `meeting_next` moves on earlier, when the meeting ends (8 PM Central). From
the end of a meeting until midnight, `meeting_next` already names next month's meeting while the other three still go
by tonight's. So in one sentence, and on one slide, use `meeting_day` with `meeting_month` and `meeting_after` (the
committee meeting's title slide: "{live:meeting_month} meeting" over "{live:meeting_day} · {live:meeting_time}";
"Next meeting: {live:meeting_after}" on a slide shown during the meeting), and `meeting_next` on its own, for "the next
meeting" in a workshop ("Next meeting: {live:meeting_next}"). Never mix them: "the {live:meeting_month} meeting on
{live:meeting_next}" names two different meetings between 8 PM and midnight.

Write a Zoom meeting ID as `{live:meeting_zoom_id}`, never as digits: the checker takes digits for a phone number.
The phone numbers the site itself publishes (anywhere in `config/site.yml`, and the two story lines) pass the
checker, but write them with their keys too: `{live:meeting_phone}`, `{live:gv_audio_phone}`,
`{live:lv_audio_phone}` follow the site when a number changes. (The Zoom IDs and the time ranges the facts give never
break across two lines on a slide.)

## The rules every slide and every note follows

Anyone can open the notes, so they follow the same rules as the slides.

- **Anonymity**: no names, faces, personal phone numbers or personal e-mail addresses. A presenter is a service
  position. A first name only in the presenter's own notes (`{fill:first_name}`). Only service e-mail addresses
  (aagrapevine.org, aalavina.org, aa.org, neta65.org), and only phone numbers that are toll-free or that the site
  itself publishes (better: their `{live:…}` keys).
- **Attraction rather than promotion**: describe, never sell — no "subscribe now", "hurry", "last chance", "before
  prices go up".
- Keep the line **"Not an official AA Grapevine, Inc. presentation"** and the credit line under every quotation
  and the Preamble, exactly as in the decks. No logos, covers or artwork of NETA 65, AA, Grapevine or La Viña.
- The site's words: "document", never "PDF" — not even "Save as PDF": the print window can "save it as a
  document"; "stays current", never "automatically"; a session, workshop, facilitator, presenter or review
  questions — AA shares experience, so never lesson, course, class, training, trainer, quiz, teach or taught ("what
  my sponsor shared with me", "showed me"); GVR and RLV service is a "position", never a "job". A word-for-word
  quotation may keep its own words.

## Changing a presentation

- **Change a slide**: edit its text and save; keep its `id`. Presenters who had changed that slide on their device
  see "Changed since you edited it" and choose the new version or theirs.
- **Add a slide**: copy a slide of the same layout, give it a new `id`, and put it where it belongs. It appears in
  its place for everyone, also for presenters who changed the presentation on their device.
- **Remove a slide**: delete it, and take its id out of every version's `hide` / `only` and every `{slide:…}`
  (the checker names any left behind).
- **Move a slide**: move its whole block. Its `{slide:…}` numbers follow by themselves.
- Then run the checker, and have a look at `/orientation/` once the site is rebuilt.

How it is built (for whoever maintains the site): `src/_data/presentations.js` reads and checks these files (the
`presentations` list the page uses), `eleventy/filters/presentations.js` adds the day's facts, and
`src/pages/presentations-json.11ty.js` writes one file per presentation, `/orientation/presentations/<id>.json`,
which the player opens.
