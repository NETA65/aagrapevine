# The bingo cards' squares — `bingo.csv`

`content/bingo/bingo.csv` is the committee's pool of squares for **Grapevine & La Viña Bingo** (*Bingo de La Viña y
Grapevine*), the printable bingo cards of the **GVR / RLV corner**: `/gvr/bingo/` (Spanish: `/es/gvr/bingo/`). A GVR
or RLV picks a grid (3×3 up to 10×10, rectangular too), where they are taking it, the kinds of squares, how many
cards — and prints them, or saves them as PDF from the print window. Every card is drawn from this file: each row is
one square, such as "Did you meet a GVR today? Write their first name and group" (`people-gvr-today`), "Did you read
a story from this month's Grapevine? Your one favorite:" (`read-this-month`), "Trade numbers with a GVR, so you know
who to call about Grapevine" (`people-phone-gvr`), or an information square with when and where our Grapevine
Meeting and committee meeting are and how to write to us (`meetings-gv-meeting`, `meetings-committee`,
`meetings-contact`).

The file holds the committee's pool (about 300 rows, every one in English and in Spanish). Add, change or switch off
rows as you like: the check below keeps every row complete and in line with AA's principles.

The squares show only on bingo cards: in the builder on `/gvr/bingo/` (its live preview, its printed and PDF cards,
the sample card shown when a browser runs no JavaScript) and in the small sample card of the **Bingo** section of the
GVR / RLV corner (`/gvr/#bingo`). They never reach the booth display or any other page. Besides its squares, a card
can carry a **Meetings & contact** strip (our Grapevine Meeting and committee meeting, the e-mail address, the site's
address and a QR code to it) — that strip comes from the settings, not from this file.

## Editing it, and when it shows

* **On github.com:** open the file, the pencil icon, edit, **Commit changes**. Or download it, edit it in **Excel**
  (or Google Sheets / LibreOffice) and save it as **CSV UTF-8** (Excel: *File → Save As → CSV UTF-8 (Comma
  delimited)*), then upload it in place of the old one. Plain "CSV" in Excel loses ñ and é.
* Excel may turn dates into `3/1/2027`: format the `from` and `until` columns as **Text** and write `2027-03-01`.
* After the commit, the site rebuilds itself in **about 3 minutes** (a page may take up to about 10 more minutes to
  show it everywhere). A GVR who has the page open gets the new squares when they reload it.
* **The check:** every commit runs the workflow *Code check (tests and test build)* (GitHub → Actions). A red ✗
  names the row and the mistake — `bingo.csv row 14 (people-gvr-today): text_en: 95 characters (90 at most)`. A row
  with a mistake is left out of the cards (the rest still works) and the build's log lists it (`[bingo] 2
  problem(s) — left out:`). *Website update* still publishes the file: it leaves the test of this file to the Code
  check (it tests the code, not your files), so only the Code check goes red — fix a mistake soon. On a computer:
  `python tests/test_bingo_csv.py content/bingo/bingo.csv` prints the same lines.
* The Code check also asks the file for enough squares: at least 200 that are on, both languages on every row, at
  least 100 everyday squares (no `from` / `until`, not information squares) in each language for each magazine
  choice (Both, Grapevine, La Viña) so a 10×10 card always works, at least 24 for each occasion, every category,
  occasion and type used, and the three information squares pinned on every card (below).

## The rows

The first row is the header. Columns can be in any order and any capitalization; a column bingo does not know is
ignored (so you can add your own). **Blank rows are skipped, and so is a row whose `id` starts with `#`** — use that
for a draft or a note. Put a cell in double quotes when it holds a comma or a line break (Excel does it for you); a
double quote inside is written twice: `"Your one ""favorite"" story"`. Every cell is read as one line: a line break
and runs of spaces become one space.

The shipped file's columns (the check asks the real file to keep every one of them, in any order):
`id,on,type,pub,cat,where,pin,weight,from,until,text_en,short_en,label_en,text_es,short_es,label_es,source_url,notes`

| column | for | what to write |
|---|---|---|
| `id` | every row (needed) | a unique name: a–z, 0–9 and dashes, up to 48 characters. The house style starts it with the category: `people-gvr-today`, `read-this-month`. Keep it once chosen: the builder remembers the squares a GVR picked by hand — and a link they copied to their settings — by their ids |
| `on` | every row | `yes` (also blank) or `no` — a quick switch. A row that is off is still checked |
| `type` | every row (needed) | `check`, `name`, `phone`, `write`, `sign` or `info` (see [The types](#the-types)) |
| `pub` | every row | `gv`, `lv` or `both` (blank = both): the square's accent colour and the builder's **Magazine** choice (Both / Grapevine / La Viña) |
| `cat` | every row (needed) | the category, one of the eight in [Categories](#categories-and-occasions) (`people`, `read`, `write`, `listen`, `service`, `meetings`, `history`, `fun`) — or a new one ([Adding a category](#adding-a-category)) |
| `where` | every row | the occasions the square fits, separated by spaces, `;` or `,`: `group`, `district`, `assembly`, `acm`, `workshop`, `booth`, `committee`, `online` ([Categories and occasions](#categories-and-occasions)). **Blank = everywhere** — most rows. A square for an assembly or a booth only: `assembly acm booth` |
| `pin` | every row | `yes`: the square starts ticked **Always** in the builder's *Choose squares yourself*, so it is on every card (the GVR can untick it); blank or `no`: drawn like the others |
| `weight` | every row | 0.5 to 5 (blank = 1; `1.5` or `1,5`): how often the square is drawn beside the others — 2 twice as often, 0.5 half as often |
| `from`, `until` | every row | `YYYY-MM-DD`, a year from 2000 to 2099, Central time, both days included: the square is offered only when the builder's **Date of the event** is inside (a holiday, an anniversary month, a special issue) |
| `text_en`, `text_es` | every row (one of them needed) | the square's words — up to **90** characters: what grids up to 6×6 print |
| `short_en`, `short_es` | when the text is longer than 36 | the words on big grids (**7×7 and up**) — and on any card whose squares come out small, such as two or four cards on a sheet —, up to **36** characters. **Needed** when that language's text is longer than 36; blank = the text itself |
| `label_en`, `label_es` | name, phone, write, sign | the label under the write-in line, up to **24** characters (blank = the type's own: "Name & group", "Name & phone", "Answer", "Initials"). Not on check or info rows |
| `source_url` | a fact (history rows) | where the fact can be checked — an https:// link. Never shown on a card |
| `notes` | every row | for the committee only — never shown, never checked |

**Lengths** are counted as a person counts them: "ñ" is one character, so is an emoji. A placeholder (`{event}`,
`{gv_meeting}` …) counts as **20** whatever it becomes, so almost every text with one needs its `short_*`:
`Questions or ideas? Write to us: {email}` is 33 + 20 = 53, so it has the short words `Write: {email}` (27).

**Small squares.** The smallest squares (a 10×10 card, or four cards on a sheet) are about ⅔ inch wide, and nothing
on a card prints below 6 pt. To keep it so, the builder measures every square a card could draw: when one would not
fit, the cards print a shorter date or a smaller typed title first, and only when that is not enough the meetings'
shorter lines (without the place: "1st Wed · 7 PM") — so one row too long for small squares can cost every such card
the meeting place. There a label of more than about 12 letters takes two lines and leaves the words too little room:
keep labels short — "Year", "Who you told", "Título", "Qué te ayudó". A label breaks only between words (or after a
"/"). A word of more than about 12 letters in the short words, or two words joined by a slash ("sponsor/sponsee"),
may be cut in two there: write "or" ("o").

**Languages.** A square is offered in English when it has `text_en`, in Spanish when it has `text_es` — the card's
language is the GVR's choice, so write both (the check asks the real file for both on every row). Once a row has
anything in a language (`short_es`, `label_es`), it needs that language's `text_*` too. Two rows that are on may not
have the same text in a language (capitals do not count): a card could show the same square twice — the check names
the later row. The same goes for the words on big grids (`short_*`, or the text when it is blank): two rows may not
have the same ones, or a big card could show the same words twice.

**Writing the Spanish.** Talk to the reader as *tú* (Busca, Pregúntale, Escribe), as the rest of the site and the
booth display do. Start every question and exclamation with ¿ and ¡ (an English name keeps its own marks: «Hi!»,
What's On Your Mind?). Quote with « ». Write "padrino o madrina", "veterano o veterana", "compañero o compañera"
where the English says sponsor, old-timer or member — in the short words too when they fit —, and "nombre de pila"
for a first name. Use the site's names: Reunión de Grapevine, Reunión Abierta de La Viña, Kit del mes, grupo base,
RSG, MCD; Grapevine's pages keep their English names, without quotes (Dear Grapevine, At Wit's End, If Walls Could
Talk), and so does Victor E. When a Spanish square names both magazines or both services, La Viña and the RLV come
first ("La Viña o Grapevine", "un RLV o GVR"). `{event}` reads well in English ("at {event}": "at this event", "at
Spring Assembly 2027"), but Spanish needs an article before a typed name ("en la Asamblea de Primavera") and none
before "este evento": the Spanish columns say "aquí", "hoy" or "este evento" instead (the event's name prints at the
top of every card anyway).

## The types

What each type looks like on the card, and one row of the file as an example (English shown; the `_es` columns are
filled the same way):

| type | on the card | example |
|---|---|---|
| `check` | the words and a small circle to tick: do it, cross it off | `listen-gv-podcast`: `text_en` Listen to an episode of AA Grapevine's Podcast · `short_en` Listen to Grapevine's podcast |
| `name` | find someone: a line labelled **Name & group** for their FIRST name and home group | `people-gvr-today`: `text_en` Did you meet a GVR today? Write their first name and group · `short_en` Meet a GVR today |
| `phone` | trade numbers: a line labelled **Name & phone** | `people-phone-gvr`: `text_en` Trade numbers with a GVR, so you know who to call about Grapevine · `short_en` Trade numbers with a GVR |
| `write` | write an answer: a line labelled by `label_*` (blank: **Answer**) | `read-this-month`: `text_en` Did you read a story from this month's Grapevine? Your one favorite: · `short_en` Your favorite story this month · `label_en` Story title |
| `sign` | someone initials it: a small box labelled **Initials** | `service-why-serve`: `text_en` Ask a GVR or RLV why they said yes to this service, and get their initials · `short_en` Why a GVR or RLV serves |
| `info` | an information square — nothing to write: a tinted square with a calendar or mail icon, crossed off like any other once read. **Only in category `meetings`** | `meetings-gv-meeting`: `text_en` Our Grapevine Meeting: {gv_meeting}. Come read and share! · `short_en` GV Meeting: {gv_meeting_short} · `pin` yes |

The builder's **Meetings & contact squares on each card** (0 to 4; 3 to start with) says how many information
squares a card gets; squares marked *Always* count too. Three of them are pinned in the shipped file — our Grapevine
Meeting (`{gv_meeting}`), our committee meeting (`{committee_meeting}`) and the e-mail address (`{email}`) — so a
card starts with all three, and the check asks the real file to keep all three, pinned, in both languages. Pin a
fourth and a card still shows three of them (drawn among the four) until the GVR picks 4.

## The placeholders

A text, short words or label may hold these, and nothing else in `{…}` (the check names any other — `{Event}`,
`{gv-meeting}`, `{}`). They are filled in from the settings when the site is built, each in the card's language —
never typed by hand, so a changed meeting time reaches every card by itself. What they become today:

| placeholder | becomes (English · Spanish) | from |
|---|---|---|
| `{event}` | the builder's **Event name** (`Spring Assembly 2027`); "this event" · "este evento" when it is empty | the GVR, in the builder |
| `{committee}` | NETA 65 Grapevine & La Viña Committee · Comité de Grapevine y La Viña de NETA 65 | `config/site.yml` `site.committee` |
| `{area}` | Northeast Texas Area 65 · Área 65 del Noreste de Texas | `config/site.yml` `site.area` |
| `{email}` | grapevine@neta65.org | `config/site.yml` `meeting.chair_email`, else `site.contact_email` |
| `{site}` | grapevine.neta65.org (the live site's address without https://; a test build on a computer writes its own) | `config/site.yml` `site.url` (the address GitHub Pages serves, on the live site) |
| `{gv_meeting}` | 1st Wednesday of the month, 7 – 8 PM Central, Google Meet · cada primer miércoles del mes, 7–8 p. m. (hora del Centro), por Google Meet | our Grapevine Meeting: `config/site.yml` `recurring_events`, key `grapevine-meeting` |
| `{gv_meeting_short}` | 1st Wed · 7 PM · 1.er miércoles · 7 p. m. | the same |
| `{committee_meeting}` | 3rd Wednesday of the month, 7 – 8 PM Central, Google Meet · cada tercer miércoles del mes, 7–8 p. m. (hora del Centro), por Google Meet | the committee meeting: `config/site.yml` `meeting:` |
| `{committee_meeting_short}` | 3rd Wed · 7 PM · 3.er miércoles · 7 p. m. | the same |
| `{gv_weekly}` | Wednesdays at 11:00 AM Central, Zoom · los miércoles a las 11:00 a. m. (hora del Centro), por Zoom | AA Grapevine's Weekly Open meeting, as the daily update reads it (`data/site/weekly_open.json`) |
| `{gv_weekly_short}` | Wed 11 AM · Zoom · mié. 11 a. m. · Zoom | the same |
| `{lv_weekly}` | Thursdays at 11:00 AM Central, Zoom · los jueves a las 11:00 a. m. (hora del Centro), por Zoom | La Viña's open meeting, the same file, while `config/site.yml` `lavina_weekly_open` is on |
| `{lv_weekly_short}` | Thu 11 AM · Zoom · jue. 11 a. m. · Zoom | the same |

Use the `_short` meeting placeholders in `short_*`: big grids have room for "1st Wed · 7 PM" or "Wed 11 AM · Zoom",
not the whole line (the check asks the real file for it). The short ones leave out "of the month", the end time and
"Central" (every time on the site is Central time); the long ones say "Central" · "(hora del Centro)", for a reader
in another time zone. The cards' *Meetings & contact* strip prints the long meeting lines when they fit (and cost
the squares little: about 8 % of their size at most), else a middle one — the short words and the platform: "1st
Wed · 7 PM · Google Meet" · "1.er mié. · 7 p. m. · Google Meet" (no placeholder: the strip only) —, else the short
ones. Short words read best at about 36 characters once filled in, so count the placeholder as its words there:
`GV Weekly Open: {gv_weekly_short}` becomes "GV Weekly
Open: Wed 11 AM · Zoom" (32) — the Spanish one, "GV Weekly Open: mié. 11 a. m. · Zoom", is 36. A square whose
placeholder has no value in a build — a meeting the settings no longer have, or that is switched off — is left out
of the cards and named in the build's log and by the Code check (`text_en: {gv_meeting} has no value in this build
(…): the square is left out`): switch that row off, or bring the meeting back. The Spanish meeting lines start in
lower case ("cada primer miércoles …", "los miércoles …") to read well after a colon, and use the site's own words:
"cada primer miércoles del mes", "por Google Meet".

## Categories and occasions

The builder lists the categories in this order, each with its number of squares, all on to start with:

| `cat` | in the builder | for squares like |
|---|---|---|
| `people` | Meet & connect · Conocer y conectar | meet a GVR or RLV, someone from another group or district, trade numbers, welcome a newcomer, an old-timer |
| `read` | Read & discuss · Leer y conversar | this month's issue, a favorite story, a section of the magazine, a story to share at a meeting |
| `write` | Share your story · Comparte tu historia | a topic you could write about, the story you would send, a letter to the editor |
| `listen` | Podcasts, video & app · Podcasts, video y app | the podcasts, the official videos, the apps |
| `service` | Carry the message · Llevar el mensaje | why someone serves, Carry the Message, a GVR's or RLV's first step, a group subscription idea |
| `meetings` | Meetings, events & contact · Reuniones, eventos y contacto | our meetings and events, how to reach us — and every `info` square |
| `history` | History & fun facts · Historia y datos curiosos | the first issue, La Viña's first issue, the Preamble, Grapevine's story (each fact with its `source_url`) |
| `fun` | Just for fun · Solo por diversión | a slogan, a birthday month, a clean joke, a laugh |

**Where are you taking it?** — the builder's occasions, the values of `where`:

| `where` | in the builder |
|---|---|
| `group` | Home group · Grupo base |
| `district` | District meeting · Reunión de distrito |
| `assembly` | Area assembly · Asamblea de Área |
| `acm` | Area committee meeting · Reunión del Comité de Área |
| `workshop` | Workshop · Taller |
| `booth` | Our booth or table · Nuestra mesa o stand |
| `committee` | Committee meeting · Reunión del comité (ours) |
| `online` | Online meeting · Reunión en línea |

A GVR who picks **Anywhere** gets every square; one who picks an occasion gets the squares that name it and the
squares with a blank `where`.

### Adding a category

A new category needs its name in both languages before the cards can show it: add a line to
`src/_i18n/bingo.json`, next to the eight others —

    "bingo.cat.games": { "en": "Games & puzzles", "es": "Juegos y acertijos" },

— and use `games` in the `cat` column (a–z, 0–9 and dashes). Until both words are there, the check refuses the rows
and says what to add: `cat "games" is not one of: people, read, … — a new category also needs its name in
src/_i18n/bingo.json ("bingo.cat.games", in English and Spanish)`. The builder lists a new category after the eight.
Information squares (`info`) stay in `meetings`.

## The rules (AA principles)

The check refuses a row that breaks one of these; the rest is up to the committee.

* **Anonymity — first names only, and only with the person's OK.** A square asks for a first name ("Name & group",
  "Name & phone"), never a last or full name: the check refuses "last name", "full name", "surname", "apellido",
  "nombre completo". A name or number written on a card is the player's, traded in person; the committee never
  collects them.
* **Welcome, don't single out** (up to you). A square about a newcomer to AA, or someone at their first meeting or
  assembly, gives — a welcome, your phone number, a copy of the magazine, a walk to our table — rather than
  collecting their name, and is drawn no more often than the others (no weight 2): every card in the room comes from
  the same pool, so the one or two newcomers there would be asked again and again. For the same reason a square asks
  for something many people can answer, never "the person with the most sobriety", "who traveled the farthest" or
  "the person chairing this meeting" (every card sent to one person, and sobriety made a contest): "a trusted servant
  serving here", and a DCM only where several of them meet (not at a district meeting). Squares ask for words, names
  or initials, never a touch the other person did not choose: a high-five or a wave, a smile or a handshake, their
  choice (`fun-high-five`, `fun-hug`).
* **No photos of people.** The check refuses "selfie" / "selfi" / "autofoto", a photo, picture or snapshot "of" or
  "with" a person (your sponsor, someone, a GVR, the group, yourself …) and "group photo" / "foto grupal". A photo of a
  thing is fine: "a picture of the first cover", "una foto de mi libro". A photo square's short words keep "no
  people" too ("Photograph the room, no people"): big grids print only the short words.
* **No money asks.** Grapevine and La Viña take no donations (say "Carry the Message gift"), and AA Grapevine, Inc.
  takes no contributions: the check refuses donate / donation / donativo, "contribution to Grapevine", "contribuir a
  La Viña". Prices only as information.
* **Attraction, not promotion:** information, "you might", "ask us". The check refuses the booth display's sales and
  urgency words — "buy now", "hurry", "limited time", "subscribe now / today", "download now / today", a shouted
  "Subscribe!", "last chance", "act now", "don't miss", "sale!", "before prices go up" and their Spanish twins — and
  "today only" in a text without `{event}`.
* **Say it the AA way:** "document", not PDF, and "recognized by the Conference as the international journal of
  AA", never "Conference-approved" for Grapevine or La Viña — both refused by the check. Up to you, as everywhere on
  the site: a GVR's or RLV's service is a "service position", never a "job", and a square never ties Grapevine or La
  Viña to an outside cause, business or event.
* **Only verified facts:** a history square gets its `source_url` (aagrapevine.org, aalavina.org, aa.org, AA
  literature); the check refuses the claims no source was found for ("reach millions", "the 183 Challenge").
  Grapevine and La Viña stories are paraphrased, never quoted.
* **Placeholders:** only the ones in [The placeholders](#the-placeholders).

The full list of refused words is in `eleventy/filters/booth.js` (the booth display's, `REFUSED`) and
`eleventy/filters/bingo.js` (bingo's own, `BINGO_REFUSED`); `tests/test_bingo_csv.py` is their twin, and
`content/booth/README.md` explains the booth's.
