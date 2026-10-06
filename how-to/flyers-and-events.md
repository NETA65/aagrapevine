# Flyers and events

How a flyer on the Drive, a small text file in the repository, or a line in the settings becomes an event
on the website, and every option you have.

**On the site:** [Events](https://neta65.github.io/aagrapevine/events/) ·
[Eventos](https://neta65.github.io/aagrapevine/es/events/) · the home page · the calendar files ·
the monthly toolkit · the monthly digest · the search.

## Contents

1. [What this is](#1-what-this-is)
2. [Quick start: a new event from a flyer](#2-quick-start-a-new-event-from-a-flyer)
3. [Pick the right way to add an event](#3-pick-the-right-way-to-add-an-event)
4. [Name a flyer so it becomes an event](#4-name-a-flyer-so-it-becomes-an-event)
5. [Use a flyer without a date](#5-use-a-flyer-without-a-date)
6. [Write an event by hand (`content/events`)](#6-write-an-event-by-hand-contentevents)
7. [Monthly events (`recurring_events:`)](#7-monthly-events-recurring_events)
8. [Events from outside calendars](#8-events-from-outside-calendars)
9. [When the same event comes from two places](#9-when-the-same-event-comes-from-two-places)
10. [What happens next (and how long it takes)](#10-what-happens-next-and-how-long-it-takes)
11. [Where events show on the website](#11-where-events-show-on-the-website)
12. [Fix a translated event title](#12-fix-a-translated-event-title)
13. [Going further: change the code](#13-going-further-change-the-code)
14. [Troubleshooting](#14-troubleshooting)
15. [Good practice and AA principles](#15-good-practice-and-aa-principles)
16. [See also](#16-see-also)

---

## 1. What this is

Every event on the site comes from one of six places. The daily update reads all of them, merges them,
removes duplicates, translates titles (English ⇄ Spanish) and publishes one list. That list feeds the
**Events** page (`/events/`, `/es/events/`), the home page's **Upcoming events**, the calendar files people
subscribe to (`/events.ics`, `/es/events.ics`), the monthly toolkit (`/monthly/`), the monthly digest
(`/digest/` and its e-mail), What's New and the RSS feed, the search, and the web presentations.

| # | Where an event comes from | What you edit | Filter chip on `/events/` |
|---|---|---|---|
| 1 | A **dated flyer** | a file in `A65_GV › 2027-2028_Panel77_GVLV › flyers` on Google Drive | NETA 65 events |
| 2 | A **hand-written event** | a Markdown file in [`content/events/`](../content/events/) | NETA 65 events (GV & LV calendars with `host: lv` / `gv`) |
| 3 | A **monthly series** | `recurring_events:` in [`config/site.yml`](../config/site.yml) | NETA 65 events (GV & LV calendars with `host: lv` / `gv`) |
| 4 | The **committee meeting** | `meeting:` in `config/site.yml` — see [Settings](settings.md) | Committee meetings (a pinned card) |
| 5 | **Grapevine's and La Viña's own calendars** | nothing — read automatically | GV & LV calendars |
| 6 | An **extra calendar feed** (`.ics`) | `sources:` → `ics_feeds:` in `config/site.yml` | depends on the feed's `category:` |

> **Who can do what.** Uploading to the Drive needs upload access to the Drive folder (ask
> grapevine@neta65.org). Editing `content/events/` or `config/site.yml` on GitHub needs **write** access —
> the MKP715 login on the owner's PC is enough. Repository **Settings** and **secrets** need the **NETA65**
> (admin) account; nothing in this guide needs them.

---

## 2. Quick start: a new event from a flyer

1. Open Google Drive → **A65_GV** → **2027-2028_Panel77_GVLV** → **flyers**.
2. Upload the flyer (PDF, JPG or PNG).
3. Rename it: **date first** (year-month-day), then the title, then the time, then `@` and the place:

   ```text
   2027-03-14 Grapevine Writing Workshop 10am-12pm @ First Methodist Church, 123 Main St, Garland, TX 75040.pdf
   ```

4. Wait for the next update (the morning refresh puts it up by about 5:30 AM Central), **or** start one now:
   GitHub → **Actions** → **Website update** → **Run workflow** → tick **skip_crawl** → **Run workflow**.
5. Open [/events/](https://neta65.github.io/aagrapevine/events/). You see a card:
   **Grapevine Writing Workshop** · Sunday, March 14, 2027 · 10:00 AM – 12:00 PM CDT · First Methodist Church,
   123 Main St, Garland, TX 75040 · buttons **Add to calendar** and **View flyer** · the flyer's picture beside
   the card. On [/es/events/](https://neta65.github.io/aagrapevine/es/events/) the title is translated by
   machine (marked "Traducción automática").

The same event also appears on the home page (if it is among the next four), in both calendar files, in the
search, in What's New for 30 days, on the March 2027 monthly toolkit, and — after it has taken place — in
the March monthly digest. Section [11](#11-where-events-show-on-the-website) lists every place.

> A flyer's name can only carry a date, a time, a time zone, a place and a title. For a description, your
> own Spanish title, a Zoom link, several days or "details to be confirmed", write a
> [`content/events` file](#6-write-an-event-by-hand-contentevents) and give the flyer a name **without a
> date** ([5.1](#51-attach-a-flyer-to-a-hand-written-event-flyer)). Never both a dated flyer and a file for
> the same event: you would get **two** events ([9](#9-when-the-same-event-comes-from-two-places)).

---

## 3. Pick the right way to add an event

| You want… | Do this | Section |
|---|---|---|
| A one-day event with a flyer and nothing more | Dated flyer in `flyers` | [4](#4-name-a-flyer-so-it-becomes-an-event) |
| A description, your own Spanish, a Zoom link or meeting ID, a link to the event's page on neta65.org | A `content/events` file + the flyer **undated**, linked with `flyer:` | [6](#6-write-an-event-by-hand-contentevents), [5.1](#51-attach-a-flyer-to-a-hand-written-event-flyer) |
| An event over several days (an Area assembly) | A `content/events` file with `start:` and `end:` dates | [6.6 c](#c-several-days-an-area-assembly) |
| Date set, details not final ("Venue to be announced") | A `content/events` file with `tentative: true` | [6.6 d](#d-details-not-final-yet-tentative-venue-to-be-announced) |
| The same thing every month (a booth, a workshop) | A `recurring_events:` block in `config/site.yml` | [7](#7-monthly-events-recurring_events) |
| A month when a monthly event moves to another day | A skip date + a file (or a dated flyer) for the new day | [7.6](#76-a-month-when-the-date-moves) |
| The committee meeting's day, time or Zoom link | `meeting:` in `config/site.yml` | [Settings](settings.md) |
| An event Grapevine or La Viña lists on their own calendar | Nothing: it is read automatically | [8.1](#81-grapevines-and-la-viñas-website-calendars) |
| Events of another public calendar (Google Calendar, a district's site) | An `ics_feeds:` entry | [8.2](#82-extra-calendar-feeds-ics_feeds) |

---

## 4. Name a flyer so it becomes an event

### 4.1 Put it in the right folder

| Rule | Details |
|---|---|
| Inside the current **Panel folder** | `A65_GV › 2027-2028_Panel77_GVLV`. A folder directly under `A65_GV` whose name has "Panel" and a number of 77 or more (`Panel 79`, `2029-2030_Panel79_GVLV`) is read too. The old `flyers` folder that sits loose in `A65_GV` is **ignored**. |
| In the **flyers** folder | The first folder under the Panel folder decides. Its name must contain one of these words (whole word, any capitals or accents): `flyer`, `flyers`, `flier`, `fliers`, `volante`, `volantes`, `folleto`, `folletos`. So `flyers`, `Volantes`, `Folletos` and `Event Flyers 2027` all work. Sub-folders inside it count too (`flyers/2027/…`). |
| Not anywhere else | A dated file in `workshops`, `reports`, `slides`, `photos`, `booth`, or loose in the Panel folder, is **not** an event. |
| Not hidden | A name containing `PRIVATE`, `PRIVADO`, `(Responses)`, `(Respuestas)` or `wrong size` (any capitals) is never published at all. |
| Any normal file | PDF, JPG, PNG, HEIC, a Google Doc or Drawing… all work. Spreadsheets and CSV files are never published. |

The folder rules for every category are in [The Drive panel folder](drive-panel-folder.md).

### 4.2 How a name is read

The update reads the file name in this order:

1. It drops the ending (`.pdf`, `.jpg` …).
2. It drops `Copy of ` / `Copia de ` at the start and ` (1)`, ` copy`, ` copia` at the end.
3. It drops `(pinned)`, `(fijado)`, `(fijo)`, `(pin)` and 📌 — they do nothing on a flyer.
4. It drops `(until …)`, `(expires …)`, `(hasta …)`, `(vence …)` **with everything inside**.
5. It finds the **date** (the first form that matches wins).
6. In what is left it finds the **time** (and a time zone right after it), then the **place**. The rest is
   the **title**.

So the pattern to teach is:

```text
<date> <title> <time> [time zone] @ <place>.<ending>
2027-03-14 Writing Workshop 9-11am @ Tyler Civic Center.pdf
```

### 4.3 Dates

| Written in the name | Read as | Notes |
|---|---|---|
| `2027-03-14`, `2027.03.14`, `2027_03_14`, `2027 03 14`, `2027-3-4` | Mar 14 2027 (Mar 4) | year-month-day — **use this one** |
| `20270314` | Mar 14 2027 | eight digits together |
| `03-14-2027`, `3.14.2027` | Mar 14 2027 | **month first** (U.S. order) |
| `March 14, 2027`, `Mar 14 2027`, `Sept. 14th, 2027` | Mar 14 2027 / Sep 14 2027 | English month words |
| `14 de marzo de 2027`, `14 marzo 2027`, `14 mar 2027` | Mar 14 2027 | Spanish month words (`ene`, `abr`, `ago`, `dic`, `setiembre` work too) |
| `14-03-2027` | **Mar 14 2027** | a first number over 12 can only be the day: day first (since October 2026; before, no date) |
| `Taller 05-10-2026`, `Informe de La Viña 05-10-2026` | **Oct 5 2026** | a name in Spanish (or French) reads a numbers-only date **day first** (since October 2026) |
| `Writing Workshop 05-10-2026` | **May 10 2026** | a name in English reads it month first |
| `Report 05-10-2026`, `Workshop 05-10-2026`, `La Viña Report 05-10-2026` | **May 10 2026**, with a note | a name whose language is unclear (a word or two) reads month first, and the run summary's *Notes* (and `/status/`) say: `2027-2028_Panel77_GVLV/flyers/Report 05-10-2026.pdf: “Report 05-10-2026”: “05-10-2026” could be May 10 or October 5, 2026 — read as May 10 (month first). Write the date year-month-day (2026-05-10 or 2026-10-05) to be sure`. The magazine names Grapevine, AA Grapevine and La Viña do not count when the language is decided |
| `March 14 - 16, 2027`, `14 al 16 de marzo de 2027`, `2027-03-14 - 2027-03-16` | **Mar 14 2027** | a range of days: a flyer event takes its **first** day (a flyer cannot hold an end date: for the whole range, write a file, [6](#6-write-an-event-by-hand-contentevents)) |
| `Session 2 - 4 March 2027` | **Mar 4 2027**, title "Session 2" | a number right after a counting word (district / distrito, panel, group / grupo, step / paso, session / sesión, week / semana, part / parte, # …) is not the first day of a range |
| `March 2027`, `marzo de 2027` | month only → **no event** | see [5.3](#53-month-only-names) |
| `2027-02-30` | **no date → no event** | an impossible date is skipped |

Only years 2000–2099 count. A year alone (`2027`) or a range of years (`2026-2027`) is not a date. To be sure,
always write the date **year-month-day** (`2027-03-14`): it can only be read one way.

> **Note:** the site's help texts say "date at the start". The code finds a date **anywhere** in the name
> (`Writing Workshop 2027-03-14.pdf` works). Still put it first: the protection against phone-camera names
> ([4.8](#48-names-that-do-not-make-an-event)) only trusts a date written first, and a date in the middle
> leaves a stray ` - - ` in the Portfolio title (`Taller de escritura - 14 de marzo de 2027 - 7pm @ …` is
> listed there as "Taller de escritura - - 7pm @ …").
>
> Do not write the weekday: `sábado 14 de marzo de 2027 Taller.pdf` gives the title "sábado Taller".

### 4.4 Times

Tried in this order: a 12-hour range, a 24-hour range, one 12-hour time, one 24-hour time. No time at all
means an **all-day** event.

| Written | Start – end (Central) | Notes |
|---|---|---|
| `9am`, `9 am`, `9 a.m.`, `9 a. m.` | 9:00 AM | a single time needs am / pm |
| `9:30pm`, `9.30pm` | 9:30 PM | |
| `9-11am`, `9am-12pm`, `9:30am - 11:30am` | 9–11 AM, 9 AM–12 PM, 9:30–11:30 AM | a start without am/pm takes the end's |
| `9 am to 3 pm`, `from 9 to 11am`, `9 a.m. - 1 p.m.` | 9 AM–3 PM, 9–11 AM, 9 AM–1 PM | `from`, `at`, `de`, `desde`, `a las` before a time are removed with it |
| `7 a 9 pm`, `de 7 a 9 pm` | 7–9 PM | Spanish ranges |
| `10-2pm` | 10 AM – 2 PM | the start is moved to the morning when needed |
| `12 noon`, `12 mediodía` | 12:00 PM | |
| `noon-2pm`, `11am-noon`, `10 a mediodía` | 12–2 PM, 11 AM–12 PM, 10 AM–12 PM | "noon" / "mediodía" inside a range |
| `8pm-midnight` | 8 PM – 12 AM (next day) | "midnight" / "medianoche" in a range |
| `19:00`, `19h00`, `19:00 hrs` | 7:00 PM | 24-hour clock needs minutes |
| `10:00-12:00`, `18h00 a 20h00` | 10 AM–12 PM, 6–8 PM | 24-hour ranges |
| `8pm-1am` | 8 PM → 1 AM **the next morning** | an end before the start is the next day; the card says "8:00 PM – 1:00 AM CDT" |
| `7pm-7pm` | 7 PM, **no end** | an end equal to the start is dropped |
| `a las 7 pm`, `at 7pm` | 7:00 PM | |

What does **not** work (it stays in the title, and the event is all-day):

| Written | What happens |
|---|---|
| `noon` or `mediodía` alone (`Workshop noon`) | not a time: all-day, title "Workshop noon". Write `12 noon`. |
| `9-11` (no am/pm) | not a time: title "Workshop 9-11" |
| `19h` (no minutes) | not a time: title "Workshop 19h" |
| `(until 5pm)`, `(hasta las 3 pm)` | removed **with** the time inside it: all-day |
| `Noon Group anniversary` | correct: "Noon Group" stays a name |

### 4.5 Time zones

Without a zone, the time is **Central** (`site.timezone: America/Chicago`). A zone written **right after the
time** is used, and the card shows the Central equivalent.

| Written right after the time | Zone | Example → card |
|---|---|---|
| `(hora del Este)`, `hora del Este` | Eastern | `Taller 12 p. m. (hora del Este)` → 11:00 AM CDT |
| `hora del Centro`, `(Central)`, `CT`, `CST`, `CDT` | Central | `Workshop 7pm CST` → 7:00 PM |
| `hora de la Montaña`, `(Mountain)`, `MST`, `MDT` | Mountain | `Workshop 6pm MST` → 7:00 PM CDT |
| `hora del Pacífico`, `(Pacific)`, `PT`, `PST`, `PDT` | Pacific | `Workshop 5pm PT` → 7:00 PM CDT |
| `(Eastern)`, `Eastern Time`, `ET`, `EST`, `EDT` | Eastern | `Workshop 7pm (Eastern)` → 6:00 PM CDT |

| Not a zone | What happens |
|---|---|
| `MT` | not recognised: 6 PM read as Central, title "Workshop MT" |
| `et`, `est` in small letters | not recognised: time read as Central, title "Workshop et" |
| `10am Mountain Creek Church`, `10am Pacific Ave` | correct: these are places, not zones |

> **Gotcha — "FR" pill:** a short English name with `ET` or `EST`
> (`2027-03-14 Grapevine Writing Workshop 7pm ET.pdf`) is detected as **French** ("et" and "est" are French
> words). The time is right (6:00 PM CDT), but the title is then never translated and the card shows an
> "FR" pill. Write `(Eastern)`, `Eastern Time` or `(hora del Este)` instead.

### 4.6 The place

The place is taken from what is left after the time is removed:

1. Everything after the first `@` is the place.
2. Without `@`: the **last** part after ` - ` (or ` – ` / ` — `, with spaces) is the place **only if** it
   contains a place word or starts with a street number.
3. Otherwise there is no place, and that text stays in the title.

Place words (any capitals): `TX`, `Texas`, church, iglesia, hall, center/centre, centro, club, clubhouse,
room, hotel, inn, library, biblioteca, park, parque, school, escuela, zoom, online, virtual, en línea,
salón, capilla, chapel, street/st, avenue/ave, road/rd, blvd/boulevard, hwy/highway, suite/ste, building,
auditorium, convention, fellowship, alano, campus, ranch, lodge, pavilion/pabellón, casa, district/distrito.

| Name (after the date) | Place | Title |
|---|---|---|
| `Spring Assembly booth 9am @ Tyler Civic Center` | Tyler Civic Center | Spring Assembly booth |
| `Workshop 10am - Mountain Creek Church` | Mountain Creek Church | Workshop |
| `Workshop from 9 to 11am - 123 Main St` | 123 Main St | Workshop |
| `Workshop 10am Mountain Creek Church` | — (needs `@` or ` - `) | Workshop Mountain Creek Church |
| `Taller de Escritura de La Viña - Grupo Libro Grande, Tyler` | — (no place word) | the whole text |
| `Workshop - District 91 @ First Church` | First Church | Workshop - District 91 |
| `Spring Assembly, Tyler TX` | — (a comma does not split) | Spring Assembly, Tyler TX |
| `Workshop - Zoom`, `Workshop 7pm - Online`, `Taller 7pm - En línea` | "Zoom" / "Online" / "En línea" | Workshop / Taller |
| `Workshop 7pm on Zoom` | — | Workshop on Zoom |

**City and state** are read only from `<City>, TX` or `<City>, Texas` (a comma before the state; another
state's two capital letters work too, `Shreveport, LA`): `@ Tyler, TX` and `@ Tyler, Texas` give city
Tyler; `@ Tyler TX` gives none. The city is used by the monthly toolkit (it shows the city when the title
does not already name it), by the duplicate check and by the home card's icon. So end the place with
`, TX` when you can.

**Online flyers:** a place of only "Zoom" makes the `/events/` card say **Online on Zoom** (a video icon,
no map pin), but there is **no Join online button** (a name cannot carry the link). A place of only
"Online", "Virtual" or "En línea" is worse: the `/events/` card hides it and shows **nothing** in its
place (no "Online" line, no calendar LOCATION). The home page card shows the word as a place ("Zoom",
"Online", with a map pin). For a real Zoom link, write a [`content/events` file](#e-online-only) instead.

> **Gotcha — a weekday before "por Zoom":** in
> `Taller Mensual de La Viña - jueves 3 p. m. (hora del Este) por Zoom.png` the last part after ` - ` is
> "jueves … por Zoom"; "Zoom" is a place word, so the place becomes **"jueves por Zoom"** with a map pin.
> Leave the weekday out, or put the online details in a `content/events` file.

### 4.7 Title and language

- The title is what is left, tidied: `_` and `%20` become spaces, `GV_LV` / `GV LV` / `GV-LV` become
  `GV/LV`, and dashes, dots or commas at the ends are trimmed. (`GV_LV_Report` stays "GV LV Report": an
  underscore right after LV blocks the rule.)
- Its **language** is detected from the whole name after the date — **the time and place included** —
  with a lean towards Spanish when the folder or name has Spanish words (`Volantes`, `taller`, `La Viña`,
  `español`). Names like "La Viña" and "Grapevine" are not counted as Spanish or English words (though
  "La Viña" in the name still tips an undecided name towards Spanish).
- The other language is **machine-translated** and marked "Auto-translated" / "Traducción automática"; the
  card on the other-language page shows a small language pill (EN / ES).

> **Gotcha — a Spanish group name in an English title:**
> `2027-03-14 Writing Workshop 10am-12pm @ Grupo Amistad, 123 Main St, Garland, TX 75040.pdf` is detected as
> **Spanish** because of "Grupo Amistad". The Spanish page then shows the English words untranslated and the
> English page gets a "translation" of them. Keep the name clearly in one language, add an override
> ([12](#12-fix-a-translated-event-title)), or use a `content/events` file with `lang:` and `title_es:`.

### 4.8 Names that do NOT make an event

| Name | Why | What you get instead |
|---|---|---|
| `Workshop flyer.pdf` | no date | a Portfolio file only |
| `14-03-2027 Taller.pdf` | day-first date is not understood | a Portfolio file titled "14-03-2027 Taller" |
| `March 2027 Workshops.pdf`, `marzo de 2027 Talleres.pdf` | month only | a Portfolio file; can be a monthly series' flyer for that month ([5.3](#53-month-only-names)) |
| `2027-02-30 Workshop.pdf` | impossible date | a Portfolio file |
| `WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg`, `IMG_20261017_183316.jpg`, `Screenshot_20261017-183316.png`, `PXL_20261017_183316123.jpg` | a phone or camera name: its date is when the picture was **taken** | a Portfolio file titled "Flyers #1", "Flyers #2" … |
| `reports/2027-03-14 Workshop.pdf` | not in the flyers folder | a Reports file |
| `2027-03-14 PRIVATE Workshop.pdf` | excluded word | nothing at all on the site |

A date written **first** is trusted even before a camera-style name — so these do make events, with poor
titles. Always add a real title:

| Name | Event title | When |
|---|---|---|
| `2026-10-17 IMG_1234.jpg` | "IMG 1234" | Oct 17 2026, all day |
| `2026-10-17 6.30 PM.jpg` | "Flyers #1" (the folder name and the picture's number among the folder's pictures) | Oct 17 2026, 6:30 PM |
| `2026-10-17.pdf` | "2026-10-17" | Oct 17 2026, all day |

### 4.9 Examples: file name → event

All verified with the site's own code. Times are Central; "All day" means no time in the name.

| File name in `…/2027-2028_Panel77_GVLV/flyers/` | Title on `/events/` | When | Place |
|---|---|---|---|
| `2027-03-14 Spring Assembly GV booth.pdf` | Spring Assembly GV booth | Sun Mar 14 2027, All day | — |
| `2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` | Spring Assembly booth | 9:00 AM (start only; calendars give 1 hour) | Tyler Civic Center |
| `2027-03-14 Writing workshop 9-11am @ Tyler Civic Center.pdf` | Writing workshop | 9:00 – 11:00 AM | Tyler Civic Center |
| `2027-03-14 Taller de escritura 9-11am @ Centro Cívico de Tyler.pdf` | Taller de escritura (Spanish) | 9:00 – 11:00 AM | Centro Cívico de Tyler |
| `2027-03-14 Spring Assembly GV booth 9am @ Tyler, TX.pdf` | Spring Assembly GV booth | 9:00 AM | Tyler, TX (city Tyler) |
| `2026-10-26 Taller de Escritura de La Viña 7-9pm - Grupo Libro Grande, 623 West Bow, Tyler, TX 75702.jpg` | Taller de Escritura de La Viña | Mon Oct 26 2026, 7:00 – 9:00 PM | Grupo Libro Grande, 623 West Bow, Tyler, TX 75702 |
| `2027-03-14 Grapevine Writing Workshop 10am-12pm @ First Methodist Church, 123 Main St, Garland, TX 75040.pdf` | Grapevine Writing Workshop | 10:00 AM – 12:00 PM | First Methodist Church, … (city Garland) |
| `2027-03-14 Asamblea de primavera - Mesa de La Viña 9am-4pm @ Tyler, TX.pdf` | Asamblea de primavera - Mesa de La Viña | 9:00 AM – 4:00 PM | Tyler, TX |
| `2027-03-14 GV LV booth 5-8pm @ CityWide Dallas.pdf` | GV/LV booth | 5:00 – 8:00 PM | CityWide Dallas |
| `2027-03-14 GV-LV Booth 5pm-8pm - Lovers Lane UMC, Dallas, TX.pdf` | GV/LV Booth | 5:00 – 8:00 PM | Lovers Lane UMC, Dallas, TX |
| `2027-03-14 GV_LV Booth noon-2pm @ Longview.pdf` | GV/LV Booth | 12:00 – 2:00 PM | Longview |
| `2027-03-14 Dance 8pm-1am @ Alano Club.pdf` | Dance | 8:00 PM – 1:00 AM next morning (the card writes "3/14/2027, 8:00 PM CDT – 3/15/2027, 1:00 AM CDT") | Alano Club |
| `2027-03-14 Taller a las 7 pm @ Grupo Amistad.pdf` | Taller | 7:00 PM | Grupo Amistad |
| `2027-03-14 Taller 18h00 a 20h00.pdf` | Taller | 6:00 – 8:00 PM | — |
| `2027-03-14 Taller 12 p. m. (hora del Este).pdf` | Taller | 11:00 AM (12 PM Eastern) | — |
| `2027-03-14 Taller 3 p. m. hora del Este por Zoom.pdf` | Taller por Zoom | 2:00 PM (3 PM Eastern) | — |
| `2027-03-14 Workshop - Zoom.pdf` | Workshop | All day | "Online on Zoom", no Join button |
| `March 14, 2027 Writing Workshop 10am.pdf` | Writing Workshop | 10:00 AM | — |
| `14 de marzo de 2027 Taller de Escritura 10 a. m. - Iglesia San Juan.pdf` | Taller de Escritura | 10:00 AM | Iglesia San Juan |
| `October 17, 2026 7 PM Writing Workshop.jpg` | Writing Workshop | Sat Oct 17 2026, 7:00 PM | — |
| `Copy of 2027-03-14 Workshop (1).pdf` | Workshop | All day | — |
| `2027-03-14 Writing Workshop 9-11am @ Tyler, TX (pinned).pdf` | Writing Workshop | 9:00 – 11:00 AM | Tyler, TX |
| `2027-03-14 Workshop (until 5pm).pdf` | Workshop | **All day** (the time inside the bracket is lost) | — |
| `2027-03-14 Booth (hasta 2027-03-15).pdf` | Booth | Mar 14 only (the until-date is thrown away) | — |
| `2027-03-19 - 2027-03-21 Spring Assembly.pdf` | **2027-03-21 Spring Assembly** | **Mar 19 only** | — |
| `2027-03-19 to 2027-03-21 NETA 65 Spring Assembly @ Tyler.pdf` | **to 2027-03-21 NETA 65 Spring Assembly** | **Mar 19 only** | Tyler |

The last two rows show that **a flyer name cannot make a multi-day event**. Write the assembly in a
`content/events` file ([6.6 c](#c-several-days-an-area-assembly)).

The same file also stays on the **Portfolio** (`/portfolio/`, Flyers tab) under its fuller title — with the
time and place still in it ("Spring Assembly booth 9am @ Tyler Civic Center") — dated by its upload, not by
the event.

### 4.10 What a flyer name cannot say

Only date, one time range, a time zone, a place and a title. It cannot say: an end **date** (several days), a
description, your own title in the other language, a link to the event's page, a Zoom link or meeting ID, a
contact e-mail, "details to be confirmed", `confirmed`, or who holds it (`host`). There is no "side file"
that adds details to a flyer event. For any of these: [6](#6-write-an-event-by-hand-contentevents).

(One exception: a dated flyer of a monthly series held on **another** day inherits the series' Zoom link,
meeting ID, contact and host — see [7.6](#76-a-month-when-the-date-moves).)

### 4.11 Rename, replace or remove a flyer event

| You do this on the Drive | At the next update |
|---|---|
| Rename the file (fix the time, say) | The **same** event is updated: same card anchor, same calendar entry (`UID:ev-flyer-<file id>@neta65-gvlv`) |
| Upload a corrected copy and delete the old one | A **new** event (a new file id); subscribers see the old entry removed and a new one added; the "New" badge starts again |
| Upload a copy and keep the old one | One event if title, start, end and place are all the same (the PDF wins); two events if anything differs |
| Take the date out of the name | The event disappears; the file stays on the Portfolio |
| Delete the file or move it out of `flyers` | The event disappears |
| Add `PRIVATE` to the name | The file and its event leave the site (but anyone with the Drive link can still open the file) |

If a folder cannot be read during a run, nothing in it is removed — it stays as it was until the next good
run.

---

## 5. Use a flyer without a date

A flyer whose name has **no date** never makes an event of its own. It is a Portfolio file (`/portfolio/`,
Flyers tab) — and it can be **attached** to an event in two ways. All ten flyers in the real `flyers`
folder today are undated on purpose: seven are attached to events like this (six with `flyer:`, one with
`flyer_match:`); the others are found by other pages (the La Viña open meeting card on `/meetings/`, the
"Share your story" flyer on `/contribute/`) or simply sit on the Portfolio.

### 5.1 Attach a flyer to a hand-written event (`flyer:`)

1. Put the flyer in `2027-2028_Panel77_GVLV/flyers/` with a name **without a date**, for example
   `Taller de Escritura de La Viña - Grupo Libro Grande, Tyler.jpg`.
2. On the Drive, right-click the file → **Share** → **Copy link**. You get
   `https://drive.google.com/file/d/<file id>/view`.
3. Paste it into the event's file in `content/events/`:

   ```yaml
   flyer: "https://drive.google.com/file/d/1gghtYzCE6Dl_IQ5_7yLueZviIK_nZqwN/view"
   ```

4. The flyer's name is also its title on the Portfolio, and that title is machine-translated — group names
   too ("Grupo Solo por Hoy" once came out as "Group Only for Today"). When the name holds a group's name,
   add a line to [`data/translations/overrides.yml`](../data/translations/overrides.yml) (Spanish name → its
   "Spanish → English" part, English name → its "English → Spanish" part):

   ```yaml
   "Taller de Escritura de La Viña - Grupo Libro Grande, Tyler": { en: "La Viña Writing Workshop - Grupo Libro Grande, Tyler" }
   ```

**What you get:** a **View flyer** button that opens the flyer in a preview on the page; beside the card (on
a computer or tablet) a small picture of the flyer, taken from the Drive by its file id; in the calendar
files an `ATTACH` line and a "Flyer: <link>" line in the description. To show a different picture beside
the card, add `image: "<picture address>"` — it is used **only** together with `flyer:`.

**A flyer from neta65.org cannot be shown.** The Area website's bot check (Cloudflare) turns away visitors
coming from other sites, so a `flyer:` that points there gets no picture (only a flyer icon) and may not
open in the preview. Copy the flyer to the Drive and keep where it came from as a note — a header line
that starts with `#` is not read:

```yaml
# flyer: a copy of https://neta65.org/wp-content/uploads/2026/09/TALLER-DE-ESCRITURA-LIBRO-GRANDE.jpeg, made 2026-10-02
flyer: "https://drive.google.com/file/d/1gghtYzCE6Dl_IQ5_7yLueZviIK_nZqwN/view"
```

### 5.2 A monthly event's flyer (`flyer_match:`)

A block in `recurring_events:` ([7](#7-monthly-events-recurring_events)) can find its flyer by itself:

```yaml
    flyer_match: "taller (informativo )?mensual( y virtual)? de la vi[nñ]a"
```

- It is a pattern (a "regular expression"); capitals are ignored and accents are optional (`vi[nñ]a`
  finds "Viña" and "Vina").
- It is tested against the **title and the file name** of every committee Drive file in **any** folder
  (bulletin posts never count) — so a renamed flyer is still found as long as the pattern matches.
- For each date of the series it picks: a file **dated that very day** → else a file named with **that
  month only** → else the **newest undated** match. No match: the dates show without a flyer.
- **Note:** only names in the `flyers` folder count as "dated" or "month only". A matching file in any
  other folder counts as undated, whatever date its name has — so
  `workshops/2026-12-10 Taller Mensual y Virtual de La Viña.png` would become the flyer of **every** date
  of the series (it is the newest). Keep a series' flyers in `flyers`.
- A pattern that cannot be read, or one that matches everything (`.*`), gives no flyer and a "Settings
  problem" line in the run summary.

Real example: `Taller Mensual y Virtual de La Viña - jueves, 3 p. m. (hora del Este), por Zoom.png` (undated)
is the flyer of every date of `lv-monthly-workshop`.

| Pattern | Matches | Does not match |
|---|---|---|
| `"citywide"` | `CityWide Booth 2027.pdf`, `Booth at CityWide Dallas.png` | `City Wide booth.pdf` (space) |
| `"city ?wide"` | both of the above and `City Wide booth.pdf` | |
| `["taller mensual", "monthly workshop"]` (a list) | either phrase | |
| `"^booth"` | names that **start** with "booth" | `GV booth.pdf` |

A **dated** flyer whose name matches a series behaves specially:

| File | Result |
|---|---|
| `2026-10-22 Taller Mensual y Virtual de La Viña.png` (Oct 22 **is** a date of the series) | Not a separate event: it becomes **that date's flyer** (the run log says "is the flyer of recurring event … — not a separate event"). |
| `2026-11-19 Taller Mensual y Virtual de La Viña 3 p. m. (hora del Este) por Zoom.png` (Nov 19 is **not** a date of the series) | Its own event — a **moved date** — that takes from the series who holds it (`host: lv`), the Zoom link (**Join online**), the meeting ID and the contact. It is shown with the GV & LV calendars, in La Viña's colour, at 2:00 PM CST. |

### 5.3 Month-only names

`March 2027 Taller Mensual de La Viña.png` makes **no event**. Its only use: when a series' `flyer_match`
matches it, it is that series' flyer for **March 2027** (beating the undated flyer, losing to one dated that
day). Verified: with that file on the Drive, the `lv-monthly-workshop` date of March 25, 2027 shows it, the
other months keep the undated flyer.

---

## 6. Write an event by hand (`content/events`)

A small Markdown file per event, in [`content/events/`](../content/events/) in the repository. It can say
everything a flyer name cannot. The repository's own help is
[`content/events/README.md`](../content/events/README.md).

### 6.1 Add or edit a file on GitHub

1. Open the repository on GitHub → `content` → `events`.
2. **Add file** → **Create new file** (or open a file and click the pencil to edit it).
3. Name it `<date>-<short-name>.md`, for example `2027-04-17-gv-writing-workshop-garland.md`
   (lower case, dashes, date first).
4. Paste a template from below and change the values.
5. **Commit changes** (to `main`). The site updates about 5 minutes later (the run tests the change first; a page
   may take up to about 10 more minutes to show it everywhere) — [10](#10-what-happens-next-and-how-long-it-takes).

The file is public as soon as you commit it — comments included. Put the hosting group in the text, never
a member's full name or phone number.

### 6.2 File rules

| Rule | Details |
|---|---|
| Folder | `content/events/` only (sub-folders are not read) |
| Ending | `.md` or `.markdown`, any capitals (`Spring.MD` works) |
| Ignored | names starting with `_` or `.`, and `README…` (use `_draft.md` for a draft) |
| Other files | `notes.txt` is not read — the run summary says "ignored — only files ending in .md are read" |
| Text | UTF-8 (old Windows text is read too) |
| Header | optional, between two `---` lines; a missing closing `---` is an error |
| **The file name is the event's identity** | It becomes the id `ev:manual:<file name>`, the card's anchor (`/events/#2027-04-17-gv-writing-workshop-garland`) and part of the calendar UID. **Renaming the file makes a new event** (new link, new calendar entry, "New" badge again). Fix things inside the file instead. |
| Same name twice | the second file is skipped ("duplicate name") |
| Delete the file | the event disappears at the next update |
| A file with a mistake | it is skipped and reported; if it was already on the site, its **last good version stays** |

### 6.3 The smallest file

A file with no header works: `content/events/2027-04-10-gv-lv-booth.md` containing only
`Come see us at the booth.` gives an all-day event on April 10, 2027 titled **"Gv lv booth"** (the name
without its date, dashes made spaces, **only the first letter capitalised**). So always write `title:`.

The usual template:

```markdown
---
title: "GV/LV booth — Fall Assembly"
title_es: "Mesa de GV/LV — Asamblea de Otoño"
start: 2027-09-18T09:00:00
end: "16:00"
location: "Tyler, TX"
lang: en
summary_es: "Visita nuestra mesa en la asamblea."
---
Visit our table at the assembly.
```

### 6.4 Every field

| Field (also accepted) | Values | When missing | Effect and where it shows |
|---|---|---|---|
| `title` | text — quote it if it contains `: ` | from the file name ("Gv lv booth") | card title, home card, calendars, search, toolkit, digest; machine-translated unless `title_es` / `title_en` |
| `start` (`date`) | a **whole** date with its year, with or without a time, or a range of days — see [6.5](#65-start-and-end-every-form) | a date in the file name (all day; a range in the name, `Assembly March 19 - 21, 2027.md`, gives the start and the end); none → **error** | the day and time everywhere |
| `end` | a date (the **last** day), a date-time, or a clock time | the event counts as **one hour**; the card shows the start only | time range or date range, calendar end, when the card disappears |
| `location` | an address, a group, or "Venue to be announced" / "TBA" / "Lugar por anunciarse" | no place line | place line with a map pin, calendar LOCATION, home card, search, toolkit (its city); **never machine-translated** |
| `location_es` / `location_en` | the place in the other language | a "to be announced" place gets the site's own words in the other language | the other-language page |
| `url` | the event's own page (best: its page on neta65.org) | `/events/#<file name>` (no title link) | the title becomes a link; an **Event details** button when there is no flyer; calendar URL and "Details:" line; matching with the NETA 65 calendar |
| `online_url` (`zoom`) | the meeting link | — | **Join online** button; "Online on Zoom" (the platform comes from the link); the calendar LOCATION when there is no place |
| `meeting_id` | e.g. `"815 9593 1777"` (cut at 40 characters) | — | "Meeting ID 815 9593 1777" on the card and in calendars; also used to recognise the same Zoom room |
| `flyer` (`flyer_url`) | the Drive link of an **undated** flyer ([5.1](#51-attach-a-flyer-to-a-hand-written-event-flyer)) | — | **View flyer**, the picture beside the card, `ATTACH` + "Flyer:" in calendars |
| `image` (`flyer_thumb`) | a picture address | — | replaces the flyer picture — only with `flyer:` |
| `tentative` | `true`, `yes`, `y`, `on`, `1`, `sí`, `si` | final | "Details to be confirmed" / "Detalles por confirmar" badge (events, home, search), first line of the calendar text, `STATUS:TENTATIVE`, "Details to be confirmed" on the monthly toolkit's dates and "details to be confirmed" in the district report |
| `confirmed` | same values | off | only for the NETA 65 calendar feed: the file's date, time and place always win ([6.6 k](#k-the-neta-65-calendar-and-confirmed-true)) |
| `host` | `neta` (default), `lv`, `gv` — also `NETA 65`, `committee`, `La Viña`, `lavina`, `Grapevine`, `AA Grapevine` | ours | `lv` / `gv`: shown with the **GV & LV calendars**, in that magazine's colour, with La Viña / AA Grapevine as organizer for search engines. Anything else ("District 91") → shown as ours + a line in "Event files to fix" |
| `lang` (`language`) | `en` / `es` (the first two letters count: `English`, `Español`) | detected from the title and text | the language you wrote in; it decides which way to translate. (`spanish` gives "sp" → ignored, detected instead.) |
| `title_es` / `title_en` | your own title in the **other** language | machine translation | the other-language title, no "Auto-translated" note, no language pill. A value in the file's own language is ignored. |
| `summary_es` / `summary_en` | one line, or a block `summary_es: \|` with indented lines | the text below the header, machine-translated | shown **instead of the whole description** on the other-language page |
| `tags` | `[workshop, la-vina]` or `workshop, la-vina` | — | stored only — shown nowhere |
| the text below the header | Markdown | — | the card's description; its first 400 characters (plain text) in calendars and search |

### 6.5 Start and end: every form

Verified results (Central time, CDT in March):

| Header lines | Stored | On the card |
|---|---|---|
| `start: 2027-03-14` | all day | All day |
| `start: 2027-03-14T19:00:00-05:00` + `end: 21:00` | 7–9 PM | 7:00 – 9:00 PM CDT |
| `start: 2027-03-14T19:00:00` + `end: 2027-03-14 21:00` | read in Central (summer/winter handled) | 7:00 – 9:00 PM CDT |
| `start: 2027-03-14 19:00` + `end: 9 PM` | 7–9 PM | 7:00 – 9:00 PM CDT |
| `start: 2027-03-14T20:00:00` + `end: 1 AM` | 8 PM – 1 AM **next morning** | 8:00 PM – 1:00 AM CDT (since October 2026; before, the dates were added: "3/14/2027, 8:00 PM CDT – 3/15/2027, 1:00 AM CDT") |
| `start: March 14, 2027 9:00 AM` (no end) | 9 AM, one hour in calendars | 9:00 AM CDT |
| `start: sábado 14 de marzo de 2027, 7:00 p. m.` + `end: "9:00 PM"` | 7–9 PM | 7:00 – 9:00 PM CDT |
| `start: 14 de marzo de 2027 de 7 a 9 p. m.` | all day (a Spanish range is not guessed) | All day |
| `start: 2027-03-19` + `end: 2027-03-21` | three days | Fri, Mar 19 – Sun, Mar 21, 2027 · 3 days |
| `start: March 19 - 21, 2027` (or `del 19 al 21 de marzo de 2027`, `2027-03-19 - 2027-03-21`) | three days, all day (an `end:` line wins over the range's last day) | Fri, Mar 19 – Sun, Mar 21, 2027 · 3 days |
| `start: "05-10-2026"` in a file with `lang: es` | October 5, 2026 (numbers-only dates follow the file's language: Spanish day first) | All day |
| `date: 2027-06-01` | all day | All day |

**Since October 2026 a date must be whole.** These are no longer guessed: the event is left out (its last good
version stays) and listed under **Event files to fix**, with a line ready to copy:

| Written | Message (after `events/<file name>: `) |
|---|---|
| `start: January 10` or `start: 10 de enero` (no year) | `start: “January 10” has no year — the event is left out until it does: write the whole date (start: 2027-01-10)` |
| `start: "3/19/27"` (a year in two digits), `start: March 19 - 21` (a range without its year) | `start: “3/19/27” has no year written in full — the event is left out until it does: write the whole date (start: 2027-03-19)` |
| `start: March 2027` (no day), `start: "2027"` (a year alone) | `… has no day — write the whole date (start: 2027-MM-DD)` |
| `start: "19:00"`, or a weekday alone | a time or a day without its date: left out |
| `start: 19:00` (no quotes: YAML reads it as the number 1140) | `start: 19:00 is a time of day without its date`: left out |
| a year before 2000 or after 2099 | left out |

A time written **with a UTC offset that is not Central time's** on that day still shows, at the moment it names,
and is listed so you can fix it: `start: 2027-01-10T19:00:00-05:00 — -05:00 is not Central time's UTC offset on
2027-01-10 (-06:00), so the event shows at 6:00 PM Central time. If 19:00 is Central time, write start:
2027-01-10T19:00:00-06:00`. Central time is −05:00 from the second Sunday of March to the first Sunday of
November, −06:00 the rest of the year.

> **Leave the UTC offset out.** The real files write `-05:00` in September/October and `-06:00` in
> November. A wrong offset moves the time by an hour (and is now listed under **Event files to fix**).
> `start: 2027-03-14T19:00:00` (no offset) is read as Central time with daylight saving done for you.
>
> An unquoted `end: 21:00` is fine (YAML turns it into a number; the site reads it back as 21:00).

### 6.6 Examples

Each example says what you get. URLs are `/events/` (English) and `/es/events/` (Spanish).

#### a) One day, in person, with a flyer

The real [`2026-10-07-lv-writing-workshop-mansfield.md`](../content/events/2026-10-07-lv-writing-workshop-mansfield.md):

```markdown
---
title: "La Viña Writing Workshop (in Spanish) — Mansfield"
title_es: "Taller de Escritura de La Viña — Mansfield"
start: 2026-10-07T20:00:00-05:00
end: 2026-10-07T22:00:00-05:00
location: "Grupo 7 Defectos y 7 Virtudes, 287 Frontage Road, Mansfield, TX 76063"
url: "https://neta65.org/event/la-vina-writing-workshop-3/"
# flyer: a copy of https://neta65.org/wp-content/uploads/2026/09/New-Taller-7-Defectos-.jpg, made 2026-10-02 — neta65.org's images can't be shown on other sites
flyer: "https://drive.google.com/file/d/1w5NfXJshkEVBmNXK-nMdmEUxqrbDgDQj/view"
tags: [workshop, la-vina]
lang: en
summary_es: "Taller en español para aprender a escribir tu historia para La Viña, en el Grupo 7 Defectos y 7 Virtudes de Mansfield."
---
A Spanish-language workshop on writing your story for La Viña, hosted by Grupo 7 Defectos y 7 Virtudes in Mansfield.
```

You get, on `/events/`: a card in La Viña's colour (the title names La Viña), "Wednesday, October 7, 2026",
"8:00 – 10:00 PM CDT", the address with a map pin, the description, **Add to calendar**, **View flyer**, the
flyer picture beside the card, and the title linking to the neta65.org page. On `/es/events/`: the title
"Taller de Escritura de La Viña — Mansfield", "8:00–10:00 p. m. CDT" and the `summary_es` text — no
"Traducción automática" note, no language pill. Anchor: `/events/#2026-10-07-lv-writing-workshop-mansfield`.
It also appears on the home page (while it is among the next four events), in the October toolkit, in the
search, and in both calendar files.

#### b) All day

```markdown
---
title: "GV/LV booth — Spring Assembly"
title_es: "Mesa de GV/LV — Asamblea de Primavera"
start: 2027-03-20
location: "DoubleTree by Hilton Hotel Dallas Near the Galleria, 4099 Valley View Ln, Dallas, TX 75244"
lang: en
---
Visit our Grapevine and La Viña table during Saturday's sessions.
```

You get "Saturday, March 20, 2027 · All day", the "Literature booth" badge and colour (the word "booth" /
"mesa" decides), and a calendar entry for the whole day. It stays listed until midnight after March 20.

#### c) Several days (an Area assembly)

The real [`2027-03-19-neta65-spring-assembly.md`](../content/events/2027-03-19-neta65-spring-assembly.md):

```markdown
---
title: "NETA 65 Spring Assembly 2027"
title_es: "Asamblea de Primavera 2027 de NETA 65"
start: 2027-03-19
end: 2027-03-21
location: "DoubleTree by Hilton Hotel Dallas Near the Galleria, 4099 Valley View Ln, Dallas, TX 75244"
tags: [assembly, neta65, panel-77]
lang: en
summary_es: "Asamblea del Área 65 (Panel 77), coorganizada por los Distritos 53 y 55, en el DoubleTree by Hilton Hotel Dallas Near the Galleria."
---
Area 65 assembly (Panel 77), co-hosted by Districts 53 and 55, at the DoubleTree by Hilton Hotel Dallas Near the Galleria.
```

Give **dates only** (no times) and `end` = the **last** day. You get "Friday, March 19 – Sunday, March 21,
2027", "3 days", a date tile "MAR · 19–21 · Fri–Sun", the "Area assembly" badge and colour; it stays listed
until midnight after Sunday; calendars show all three days (`DTSTART;VALUE=DATE:20270319`,
`DTEND;VALUE=DATE:20270322`). It can also be the **Save the date** card at the top of `/events/` and the
"next assembly" fact in the web presentations.

#### d) Details not final yet (tentative, venue to be announced)

The real [`2027-06-25-neta65-summer-assembly.md`](../content/events/2027-06-25-neta65-summer-assembly.md):

```markdown
---
title: "NETA 65 Summer Assembly 2027"
title_es: "Asamblea de Verano 2027 de NETA 65"
start: 2027-06-25
end: 2027-06-27
location: "Venue to be announced"
location_es: "Lugar por anunciarse"
tentative: true
tags: [assembly, neta65, panel-77]
lang: en
summary_es: "Asamblea del Área 65 (Panel 77), organizada por el Distrito 91. El lugar se anunciará pronto."
---
Area 65 assembly (Panel 77), hosted by District 91. The venue will be announced soon.
```

You get a **Details to be confirmed** badge (also on the home page and in the search), the place in plain
italic text with an hourglass (no map pin, left out of the calendar LOCATION), "Lugar por anunciarse" on the
Spanish page, a calendar text that starts "Details to be confirmed. The date, place or times may still
change…", and `STATUS:TENTATIVE` so calendar apps mark it tentative.

Words recognised as "not known yet" in `location`: "Venue to be announced", "Location TBD", "TBA", "TBC",
"to be determined/confirmed", "Lugar por anunciarse", "Sede: por confirmar", "a confirmar", "pendiente",
"se anunciará pronto". Without `location_es`, the Spanish page writes "Lugar por anunciarse" by itself.

**When the details are final**, edit the file: put the real place in `location`, **delete** the
`location_es` line and the `tentative: true` line, and update the text and `summary_es`.

```diff
-location: "Venue to be announced"
-location_es: "Lugar por anunciarse"
-tentative: true
+location: "Example Conference Center, 123 Main St, Tyler, TX 75701"
```

(The venue here is made up.) A `location_es: "Lugar por anunciarse"` left next to a real
`location` is ignored and reported under "Settings problems" in the run summary.

#### e) Online only

```markdown
---
title: "Grapevine Writing Workshop on Zoom"
title_es: "Taller de Escritura de Grapevine por Zoom (en inglés)"
start: 2027-05-15T10:00:00
end: "12:00"
online_url: "https://us02web.zoom.us/j/9494767497"
meeting_id: "949 476 7497"
lang: en
summary_es: "Aprende a escribir tu historia para Grapevine, en línea por Zoom."
---
Learn how to write your story for Grapevine. Online on Zoom.
```

You get "Online on Zoom" / "En línea por Zoom" with a video icon (no map pin), a **Join online** button,
"Meeting ID 949 476 7497", and the Zoom link as the calendar LOCATION. The home card says "Online on Zoom".
Search engines are told it is an online event.

#### f) Hybrid (a place and Zoom)

The real [`2026-10-03-gv-writing-workshop-arlington.md`](../content/events/2026-10-03-gv-writing-workshop-arlington.md)
(the Zoom password token is shortened here):

```markdown
---
title: "Grapevine Writing Workshop — Arlington"
title_es: "Taller de Escritura de Grapevine (en inglés) — Arlington"
start: 2026-10-03T14:00:00-05:00
end: 2026-10-03T17:00:00-05:00
location: "Primary Purpose Group – Arlington, 1802 West Division Street, Arlington, TX 76012"
url: "https://neta65.org/event/grapevine-writing-workshop-6/"
flyer: "https://drive.google.com/file/d/1n8FzYA1h3DeamjI9Pp5mxCyrZFz0Oweu/view"
online_url: "https://us02web.zoom.us/j/9494767497?pwd=…"
meeting_id: "949 476 7497"
confirmed: true
lang: en
summary_es: "Aprende a escribir tu historia para Grapevine y La Viña … Es un taller híbrido: ven en persona o conéctate por Zoom …"
---
Learn how to write your story for Grapevine and La Viña … A hybrid workshop: come in person or join on Zoom …
```

You get **both** lines on the card — the address (map pin) and "Online on Zoom" — plus **Join online**,
"Meeting ID 949 476 7497", **View flyer** and the flyer picture. The calendar LOCATION is the address and the
description has "Online on Zoom: <link>". Search engines get both a place and an online location
("mixed attendance"). **The home page card shows only the address.**

#### g) Other platforms

The platform's name comes from the link's address:

| `online_url` points to | The card says |
|---|---|
| `…zoom.us/…` | Online on Zoom · En línea por Zoom |
| `meet.google.com/…` | Online on Google Meet |
| `teams.microsoft.com/…`, `teams.live.com/…` | Online on Microsoft Teams |
| `…webex.com/…` | Online on Webex |
| `gotomeeting.com`, `skype.com`, `whereby.com`, an address with `jitsi` in its name | Online on GoToMeeting / Skype / Whereby / Jitsi |
| anything else — the public `meet.jit.si` too | Online · En línea |

`location: Zoom` (or `Google Meet`, `Teams`, `Webex` …) **without** a link gives "Online on Zoom" (or
"Online on Teams" …) but no **Join online** button — and the home card shows "Zoom" as if it were a place.
`location: Online`, `Virtual` or `En línea` without a link is worse: the `/events/` card shows **no** place
and no "Online" line at all. Give `online_url` for an online event.

#### h) An event La Viña or Grapevine holds (`host: lv` / `gv`)

From [`content/events/README.md`](../content/events/README.md): La Viña holds its monthly workshop the week
before Thanksgiving. Add the series' date (`2026-11-26`) to its `skip_dates` ([7.6](#76-a-month-when-the-date-moves)) and write:

```markdown
---
title: "La Viña Monthly Virtual Workshop (in Spanish)"
title_es: "Taller Mensual y Virtual de La Viña"
start: 2026-11-19T14:00:00
end: "15:00"
online_url: "https://us06web.zoom.us/j/81595931777"
meeting_id: "815 9593 1777"
host: lv
lang: en
---
The week before Thanksgiving.
```

You get the event under the **GV & LV calendars** filter, in La Viña's colour, with **Join online** and the
meeting ID, and La Viña as the organizer for search engines. La Viña's own calendar lists the same day; with
the same Zoom link the two are recognised as one event and shown once (this file wins).

#### i) A file written in Spanish

```markdown
---
title: "Taller de Escritura de La Viña — Garland"
title_en: "La Viña Writing Workshop (in Spanish) — Garland"
start: 2027-04-24T19:00:00
end: "21:00"
location: "Grupo Amistad, 123 Main St, Garland, TX 75040"
lang: es
summary_en: "A Spanish-language workshop on writing your story for La Viña, hosted by Grupo Amistad in Garland."
---
Taller en español para aprender a escribir tu historia para La Viña, en el Grupo Amistad de Garland.
```

With `lang: es`, the **English** words come from `title_en` / `summary_en`. A `title_es` in this file would be
ignored (it is the file's own language). The address is shown as written in both languages.

#### j) A rich description (Markdown) and a long Spanish text

```markdown
---
title: "Grapevine & La Viña Day — Tyler"
title_es: "Día de Grapevine y La Viña — Tyler"
start: 2027-05-01T10:00:00
end: "15:00"
location: "Tyler Public Library, 201 S College Ave, Tyler, TX 75702"
lang: en
summary_es: |
  ## Programa
  - 10:00 a. m. — Bienvenida
  - 11:00 a. m. — Cómo escribir tu historia
  - 1:00 p. m. — Cómo grabar tu historia

  Más eventos en [nuestra página](/events/).
---
## Program
- 10:00 AM — Welcome
- 11:00 AM — How to write your story
- 1:00 PM — How to record your story

More events on [our page](/events/). Bring a pen!
```

You get the description on the card as formatted text: `##` headings become small headings, lists stay
lists, links work, single line breaks are kept, and a bare `https://…` address becomes a link. A link to one
of our pages (`/events/`) goes to the page's Spanish version on `/es/events/`. Raw HTML is shown as text,
never run. The block `summary_es: |` is the **whole** Spanish description; calendars and the search use a
plain-text teaser (the first 400 characters).

#### k) The NETA 65 calendar and `confirmed: true`

The real [`2026-09-26-lv-writing-workshop-fort-worth.md`](../content/events/2026-09-26-lv-writing-workshop-fort-worth.md)
has `url:` pointing to its neta65.org page and `confirmed: true`. When the NETA 65 workshop calendar can be
read ([8.2](#82-extra-calendar-feeds-ics_feeds)), the same workshop there is matched by that page and shown
once; with `confirmed: true` the file's date, time and place always win and there is no "Check:" line about
it. Today that calendar is blocked, so `confirmed` changes nothing visible. This workshop took place on
September 26, so it is now under **Past events** on `/events/` (title · place · View flyer) and stays in
the calendar files while it is among the 12 newest past events.

### 6.7 Lines that do nothing in an event file

These are silently ignored: `summary:` (the English description is always the text below the header —
`summary:` works only for bulletin posts), `contact:` (works only in `recurring_events:`), `passcode:`,
`organizer:`, `time:`, `end_date:`, `enabled:`, `publish:`, `expires:`, `platform:` (always taken from the
link). `tags:` is stored but shown nowhere.

### 6.8 Mistakes and the messages you get

The messages appear in the run summary (GitHub → **Actions** → the latest **Website update** run) under
**Event files to fix**, with a yellow warning. The file is skipped; if it was on the site before, its last
good version stays.

| Mistake | Message (after `events/<file name>: `) |
|---|---|
| no `start:` and no date in the file name | `it has no start date (add a line 'start: 2027-03-14' or 'start: 2027-03-14T09:00:00-05:00' to the header)` |
| `end` before `start` | `the end '…' is before the start — write end: like start: (e.g. 'end: 2027-03-14T21:00:00-05:00', or 'end: 2027-03-16' for the last day)` |
| `end: "21:00"` with `start: 2027-03-14` (no time) | `end: 21:00 is a time of day, but start: has no time — write start: with its time … or leave end: out` |
| no closing `---` | `the header has no closing --- line (add a line with just --- below the header)` |
| a header line that is not `name: value` | `the header between the --- lines is not valid (line N): … put the whole value in quotes …` |
| `host: District 91` | `host: “District 91” must be neta (our committee), lv (La Viña) or gv (Grapevine) — shown as ours (NETA 65); the group that hosts it goes in the description` — the event **still shows**, as ours |
| a date without its year or day, a time alone, a two-digit year, a wrong UTC offset | see [6.5](#65-start-and-end-every-form) |
| a `.txt` or `.docx` in the folder | `ignored — only files ending in .md are read (rename it to end in .md)` |
| two files whose names differ only in capitals, spaces or punctuation (`Spring.md`, `spring.md`) | `duplicate name` — the second one is skipped |

Two slips are fixed for you and reported under **Settings problems** instead:

- `location_es` still says "Lugar por anunciarse" next to a real `location` → the real place is shown in
  both languages ("…Delete the location_es line.").
- `location` says "Venue to be announced" but `location_es` gives a place → the "to be announced" text is
  shown ("…put the place in location: too.").

A title with `: ` and no quotes (`title: Reminder: Assembly Saturday`) is **not** an error: the header is
then read line by line and the title is kept as written.

> **Note:** since October 2026 the same lines are also on `/status/`, in the folded *Notes from the last update*
> under the row "Events added by hand" (in English, for the site maintainer), as well as in the Actions run
> summary and in `data/site/status.json`.

**The Code check tests every file too** (`tests/test_content_events.py`, since October 2026): each real file in
`content/events/` is read exactly as the update reads it, and the check turns red, naming the file and what to
change, when a year is missing, an offset is not Central time's, or the end is not after the start. So a slip
shows as a red ✗ minutes after you save it, and the *Website update* run of that save does not publish it.

---

## 7. Monthly events (`recurring_events:`)

Things that happen **every month** live in `config/site.yml` under `recurring_events:` — one block per
series. Each block produces one event per date: the next `months_ahead` dates, plus the dates of the last 90
days (kept for the calendar files only). Daylight saving is handled.

### 7.1 The two real blocks (shortened)

```yaml
recurring_events:
  - key: "citywide-dallas"
    title: "GV/LV booth at CityWide Dallas"
    title_es: "Mesa de GV/LV en CityWide Dallas"
    summary: "Stop by our Grapevine and La Viña literature table at CityWide Dallas, …"
    summary_es: "Visita nuestra mesa de literatura de Grapevine y La Viña en CityWide Dallas, …"
    week_of_month: 2
    weekday: "saturday"
    start: "17:00"
    end: "20:00"
    location: "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220"
    url: "https://citywidedallasaa.org"
    months_ahead: 6
    skip_dates: []

  - key: "lv-monthly-workshop"
    title: "La Viña Monthly Virtual Workshop (in Spanish)"
    title_es: "Taller Mensual y Virtual de La Viña"
    summary: "In Spanish, open to all: La Viña and Grapevine books, event news and General Service Office updates."
    summary_es: "En español y abierto a todos: libros de La Viña y Grapevine, noticias de eventos y novedades de la OSG."
    host: "lv"
    week_of_month: 4
    weekday: "thursday"
    start: "14:00"
    end: "15:00"
    online_url: "https://us06web.zoom.us/j/81595931777"
    meeting_id: "815 9593 1777"
    contact: "lveditorial@aagrapevine.org"
    flyer_match: "taller (informativo )?mensual( y virtual)? de la vi[nñ]a"
    months_ahead: 6
    skip_dates: ["2026-11-26", "2026-12-24", "2027-11-25", "2027-12-23"]
```

### 7.2 Every key

| Key | Values | When missing or wrong | Effect |
|---|---|---|---|
| `key` | short name: letters, numbers, dashes (cut to 32 characters). **Keep it the same once published.** | made from the title; the same key twice → the second block is skipped | the id `ev:recurring:<key>:<date>`, the card anchor `ev-recurring-<key>-<date>`, the calendar UID |
| `title`, `title_es` | text — at least one | neither → **skipped**; one missing → machine-translated | card and calendar title |
| `summary`, `summary_es` | text (the card shows 3 lines: keep it about 100 characters) | the missing one is machine-translated | card text, calendar description |
| `week_of_month` | `1`–`5`, or `-1` for the last; also `"2nd"`, `"second"`, `"segundo"`, `"2.º"`, `"last"`, `"último"` | missing or unreadable → **skipped** | which week. A month without a 5th one is simply left out. |
| `weekday` | `saturday`, `Saturday`, `Saturdays`, `sábado`, `Sábados`, `miercoles` … | unreadable → **skipped** | which day |
| `start` | `"17:00"`, `"5:00 PM"`, `5pm`, `17`, or unquoted `17:00` — Central time | missing → **skipped** | start |
| `end` | the same forms | unreadable or not after the start → **one hour** + a note. Since October 2026 an end earlier than the start and at most 12 hours later (`"22:00"`–`"01:00"`) is the next morning on `/events/` and in the calendar files, with no note (the `/monthly/` posters still show one hour) | end |
| `location` | an address; the city is read from `…, City, TX` | — (an online series has none) | place |
| `city`, `state` | override the city and state read from `location` | — | toolkit and duplicate matching |
| `url` | `https://…` (a `www.…` address gets `https://`) | not an address → left out + note; none → the event links to its own card on `/events/` | title link, **Event details** button |
| `online_url` | `https://…` | not an address → left out + note | **Join online**; the platform from the link |
| `meeting_id` | letters, digits, spaces, dots, dashes (3–40 characters) | not an ID → left out + note; a Zoom number that differs from the `online_url` meeting → note | "Meeting ID …" line; recognising the same room |
| `contact` | a plain e-mail address (`mailto:` is removed) | not an address → left out + note | a "Contact" mail link on the card and in calendars |
| `host` | `neta` (default), `lv`, `gv` (and the long names) | anything else → `neta` + note | `lv`/`gv`: shown with the GV & LV calendars, in that magazine's colour, and it does **not** get a reserved place on the home page |
| `flyer_match` | a pattern, or a list of patterns | unreadable, or matches everything → no flyer + note | its flyer, [5.2](#52-a-monthly-events-flyer-flyer_match) |
| `months_ahead` | `1`–`24` | default `6`; outside 1–24 → 6 + note | how many upcoming dates `/events/` and the calendar files list (the `/monthly/` posters work out later months themselves) |
| `skip_dates` | `["2026-12-12"]` (one date without brackets works too) | a value that is not a date, or not one of the rule's days → ignored + a note naming the right date | that month has no date |

> **Note:** `enabled: false` is **not** read by the daily update — only the `/monthly/` posters honour it.
> To stop a series, delete its block (as the comment in `config/site.yml` says).

### 7.3 Example: add a new monthly booth

Copy a block, paste it under the last one (keep the two spaces before `- key:`), and change it:

```yaml
  - key: "booth-garland"
    title: "GV/LV booth at the Garland Alano Club"
    title_es: "Mesa de GV/LV en el Club Alano de Garland"
    summary: "Our Grapevine and La Viña literature table, every third Saturday morning."
    summary_es: "Nuestra mesa de literatura de Grapevine y La Viña, cada tercer sábado por la mañana."
    week_of_month: 3
    weekday: "saturday"
    start: "10:00"
    end: "13:00"
    location: "Garland Alano Club, 123 Main St, Garland, TX 75040"
    months_ahead: 6
    skip_dates: []
```

(The address is only an example.) After the next update (say in early October 2026) you get, on
`/events/`: **one** card for the next date (Saturday, October 17), with an **Every month** badge, the repeat
line "Every third Saturday of the month", the time "10:00 AM – 1:00 PM CDT", "Then Nov 21, Dec 19, Jan 16"
(up to three later dates), the Literature booth colour (the word "booth"); the switch **Show every monthly
date** reveals the other dates. On the home page
the next date always keeps a place among the four cards (a series **we** hold is never pushed off by
workshops). The calendar files get every date, with the repeat line and "Central time" in the description.
The toolkit (`/monthly/`) shows it every month; the search has one entry (its next date, found by "every
month" and "booth / literature table"). A series date is never "New", never in What's New, and never in
**Past events**; once a date has taken place it is in that month's digest.

### 7.4 Example: other days

| You want | Write |
|---|---|
| The last Friday | `week_of_month: -1` and `weekday: "friday"` (or `"last"` / `"último"` and `"viernes"`) |
| The first Monday, 7–8:30 PM | `week_of_month: 1`, `weekday: "monday"`, `start: "19:00"`, `end: "20:30"` (or `"7:00 PM"`, `"8:30 PM"`) |
| The 5th Saturday (only some months) | `week_of_month: 5` — months without a 5th Saturday are left out |
| A start only | leave `end` out: each date lasts one hour |

### 7.5 Example: skip a month

```yaml
    skip_dates: ["2026-12-12"]          # no booth in December (that month's 2nd Saturday)
```

A date that is not one of the rule's days is ignored, and the run summary says which date to use:
`skip date “2026-12-13” is not the 2nd Saturday of its month — ignored (that month's is 2026-12-12)`.

### 7.6 A month when the date moves

La Viña holds its workshop the Thursday before Thanksgiving and Christmas. Three ways to show a moved date:

1. **Skip date + a file** (best: you set the time): add `"2026-11-26"` to `skip_dates`, and write
   `content/events/2026-11-19-lv-monthly-workshop.md` with `host: lv` and the **same Zoom link** —
   [6.6 h](#h-an-event-la-viña-or-grapevine-holds-host-lv--gv). La Viña's own listing of that day is
   recognised by the Zoom room and shown once.
2. **Skip date + a dated flyer**: `2026-11-19 Taller Mensual y Virtual de La Viña 3 p. m. (hora del Este) por Zoom.png`
   in `flyers` (its name matches `flyer_match`). It becomes its own event on Nov 19 at 2:00 PM CST and
   takes the series' host, Zoom link, meeting ID and contact ([5.2](#52-a-monthly-events-flyer-flyer_match)).
   It has no end in its name, so it counts as one hour.
3. **Skip date only**: when La Viña's calendar lists the skipped month on another day, that listing is shown
   **as that month's date of the series** — with the series' own titles, Zoom link, meeting ID, contact and
   flyer, but "Time not listed — see event details" (La Viña's calendar gives no time) — and it is named in
   the series' "Then …" line.

If La Viña's calendar lists a month on another day and you have **not** added the skip date, nothing is
changed; the run summary asks you to add it: `… lists it on 2026-11-19 (…), but the rule gives 2026-11-26 —
if that month's date moved, add "2026-11-26" to its skip_dates …`. Thanksgiving is always the 4th Thursday
of November, so add each year's skip date ahead of time — the warning only comes once La Viña lists the
moved date, about three weeks ahead.

### 7.7 What the run summary says about a bad block

Under **Settings problems** you get one line that starts with `config/site.yml`, each block named by its
number and key, blocks separated by ` / ` (wrapped here):

```text
config/site.yml recurring_events entry 3 (booth-garland): end time “9am” is not after the start — shown as
  one hour long; months_ahead “40” must be a number from 1 to 24 — 6 used; url “garland.example.org” is not
  a web address (https://…) — left out; host “District 91” must be "neta" (our committee), "lv" (La Viña) or
  "gv" (Grapevine) — "neta" used; flyer_match “.*” would match every file on the Drive — no flyer
  / recurring_events entry 4 (no name): it needs a title; it needs week_of_month (1–5, or -1 for the last
  one); weekday “funday” is not a day of the week; it needs a start time (like "17:00") — skipped
```

Block 3 still shows (with the fixes applied); block 4 is skipped. The rest of the site still updates.

---

## 8. Events from outside calendars

### 8.1 Grapevine's and La Viña's website calendars

Nobody edits these here. The **full daily run** reads the official calendars of aagrapevine.org and
aalavina.org (through aagrapevine.org's sitemap) and keeps only events that are:

- **in Texas**, or
- **online and in Spanish** (on La Viña's calendar or written in Spanish).

"In Texas" uses the curated lists of [`scripts/sync/geo.py`](../scripts/sync/geo.py) (since October 2026): a state
written in the address wins; then Texas, Tejas or TX in the place or the title; then another state, province or
country named there (Florida, Georgia, Chile …) means not Texas (a street such as "Florida Ave" does not count);
a city alone counts only when it is on geo.py's short lists of unmistakable Texas cities (`NETA65_BARE`,
`TEXAS_BARE`: Dallas, Fort Worth, Houston, Plano, Tyler …). Gainesville, Greenville, Midland, Odessa, Denton and San
Antonio are not on them (other states have them too), so "Hilton University of Florida Conference Center,
Gainesville" is not a Texas event. A Texas event that names neither TX nor Texas nor such a city is left out.

| What | How it shows |
|---|---|
| Filter chip | **GV & LV calendars** · badge "Grapevine calendar" / "La Viña calendar" |
| A listing with a date but no time | "Time not listed — see event details" (never "All day"). Since October 2026 this also covers a time that is only the calendar's placeholder (Drupal's 12:00 UTC, or midnight with no clock time on the page), and an end at midnight makes the day before the last day |
| Title | as listed, machine-translated into the other language; fix one in `overrides.yml` (real example: the "XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS …" gathering) |
| Description | e-mails, phone numbers and web addresses are removed for privacy; a description with fewer than 5 words left is dropped |
| After it ends | it leaves the data the next day — so it is never under **Past events** or in the monthly digest. An event over several days stays until its **last** day (one that started up to 31 days ago, `LONG_EVENT_DAYS`) |
| A listing of an event we already show | dropped: ours wins ([9](#9-when-the-same-event-comes-from-two-places)) |

The window is two days back (31 days for an event still running) to about 18 months ahead; at most 60 new event
pages are read per run, and known upcoming pages are re-checked every 14 days. These events change only after a **full** run (not after a
push or a quick run). The reader is [`scripts/sync/events_external.py`](../scripts/sync/events_external.py);
more in [Automatic sources](automatic-sources.md).

### 8.2 Extra calendar feeds (`ics_feeds:`)

Any public calendar file (`.ics`, "iCal") can be added in `config/site.yml`:

```yaml
sources:
  ics_feeds:
    - url: "https://neta65.org/events/category/workshop/list/?ical=1"
      label: "NETA 65 workshops"
      label_es: "Talleres de NETA 65"
      category: "neta65"
```

| Key | Meaning |
|---|---|
| `url` | the calendar file's address, `https://…` or `webcal://…` |
| `label` (or `name`), `label_es` | its name on `/status/` and in the run summary |
| `category` | `neta65` or `ics` → shown with the **NETA 65 events**; `gv-calendar` / `lv-calendar` → with the **GV & LV calendars**. Anything else → `ics` + a note |
| `key` | optional; made from the label |

How it is read: at most **one request a day** per feed (about every 20 hours, whatever the run); the last
good copy is kept in `data/state/ics_feeds.json` and used in between. Repeating events are expanded
(deleted and moved dates are honoured), cancelled ones are left out, `STATUS:TENTATIVE` gives the "Details to
be confirmed" badge, the event's `URL` becomes its page, an `ATTACH` becomes its flyer, a Zoom / Meet / Teams
link in the location or description becomes **Join online**, ", United States" is removed from places.
Feed descriptions are **not** scrubbed of e-mails or phone numbers (unlike 8.1) — check a new feed before
adding it.

Example — a district's public Google Calendar (the address is a placeholder; take the real one from Google
Calendar → Settings → "Public address in iCal format"):

```yaml
    - url: "https://calendar.google.com/calendar/ical/<calendar id>/public/basic.ics"
      label: "District 91 events"
      label_es: "Eventos del Distrito 91"
      category: "ics"
```

> **Today the only feed is blocked.** neta65.org sits behind Cloudflare's "Just a moment…" check, which
> turns our robot away (HTTP 403). Nothing breaks: the run summary shows it under **Other calendars
> (optional, informational)** as a notice, the `/status/` page shows it in its "Other calendars" section, and
> no "stopped updating" issue is opened. Until it is unblocked, a workshop or assembly shows only when it has
> a `content/events` file. The comment above `ics_feeds:` in `config/site.yml` says what to ask the Area
> webmaster for.

When a feed and one of our events are the same ([9](#9-when-the-same-event-comes-from-two-places)), ours
wins and the feed only fills gaps: a missing flyer, online link, event page, place, a "Venue to be
announced" place, or a missing end. Where the feed says something else — the same event page on another
date, another start time, a real venue while the file says "to be announced" — the run summary shows a
**Check:** line naming the file. `confirmed: true` in the file stops those notes for good.

---

## 9. When the same event comes from two places

| The two | What happens |
|---|---|
| The same flyer twice (`X.pdf` + `X (1).jpg`: same title, start, end and place) | **One** event — the PDF's |
| Two different flyers, same day, time and place (a GV and an LV workshop) | Two events |
| **A dated flyer and a `content/events` file for the same event** | **Two events — never merged** |
| A dated flyer matching a series' `flyer_match`, on a series date | One: it becomes that date's flyer |
| …the same on another day | Its own event, with the series' host, Zoom link, meeting ID and contact |
| A `.ics` feed lists one of ours | Feed copy dropped; it may fill gaps (8.2) |
| Grapevine's or La Viña's calendar lists one of ours | Listing dropped; nothing is copied (the data notes `also_on_calendar` on ours) |
| Two Grapevine / La Viña listings, same date, very similar titles | The richer one is kept |

**How "the same" is decided** (feeds and GV/LV listings): both must **start on the same day** (Central), and
then either point to the same event page (`url`, ignoring `www.`, a trailing `/`, `?…` and `#…`), or use
the same online room (the same Zoom meeting number from the link or `meeting_id`, the same Meet code), or
have the same shape (both all-day, or both timed and starting within 2 hours), not be in two different
cities, and have titles that share at least three quarters of their telling words — all of them when one
of the two has no known city (the city and the year are ignored; "workshop", "booth", "assembly" count,
so a booth **at** an assembly stays separate).

**Avoid the flyer + file double.** There is no merge between a dated flyer and a `content/events` file.
When you write a file for an event:

1. Rename the flyer so its name has **no date** (keep it in `flyers`), e.g.
   `Taller de Escritura de La Viña - Grupo Libro Grande, Tyler.jpg`.
2. Link it from the file with `flyer:` ([5.1](#51-attach-a-flyer-to-a-hand-written-event-flyer)).

Verified: `2026-10-26 Taller de Escritura de La Viña 7-9pm @ Grupo Libro Grande, 623 West Bow, Tyler, TX 75702.jpg`
next to the real Tyler file gives **two** cards for the same evening. (A code change can merge them — see
[13.4](#134-other-changes-people-ask-for).)

---

## 10. What happens next (and how long it takes)

Everything goes through the GitHub workflow **Website update** (`.github/workflows/update.yml`): it reads
the sources, rebuilds `data/site/events.json`, builds the pages and publishes them.

| You changed | What picks it up | Live after about |
|---|---|---|
| A `content/events` file or `config/site.yml`, committed on GitHub | The commit starts a **quick** run at once (Drive, the bulletin and event files in `content/`, podcasts, the writers archive files, the daily quote — and the whole event list is rebuilt), which tests the change before it publishes | about 5 minutes (a page may take up to about 10 more minutes to show it everywhere) |
| A flyer on the Drive | **Not** a commit, so nothing starts. The next run that reads the Drive: the **morning refresh** (on the site by about 5:30 AM Central), the **midday** and **evening** refreshes, the **nightly full** update, any commit to content or settings, or a run you start | the next refresh (the same day when uploaded in the morning or afternoon, else the next morning) — or a few minutes after a run you start |
| `data/translations/overrides.yml` | a quick run, like a content edit | about 5 minutes |
| (Grapevine's / La Viña's calendars) | the **nightly full** update (and a commit that changes `sources.grapevine.base` or `sources.lavina.base`) | the next day |
| (an extra `.ics` feed) | any run, but each feed is asked at most about once every 20 hours | up to a day |

**Start a run yourself:** GitHub → **Actions** → **Website update** → **Run workflow** → tick
**skip_crawl** (a quick refresh) → **Run workflow**. The MKP715 login (write access) can do this.

GitHub starts its scheduled runs late (often 4–6 hours), so all three schedules are deliberately set about 4 hours
early: the nightly full update usually starts around 6–8 AM Central, the midday refresh around 11 AM–1 PM and the
evening refresh around 7–9 PM Central (an hour earlier in winter).
The morning refresh is started separately so the new day is on the site by 5:30 AM. Details:
[Automation and troubleshooting](automation-and-troubleshooting.md).

A few more timings:

- **Between builds** the pages hide an event as soon as it is over (the browser checks the end time), on
  `/events/` and on the home page — so the site never shows yesterday's workshop as upcoming.
- **Subscribed calendars** follow changes the next time they refresh (the file asks every 12 hours; Google
  Calendar may take longer). A copy someone saved with **Add to calendar** is a one-time copy: it does not
  follow later changes.
- **Code check (tests and test build)** (`.github/workflows/check.yml`) also runs after a content or
  settings commit: it builds the site and runs the tests. A red ✗ there means something in that
  change is broken — undo or fix the change. The live site keeps working either way: *Website update* runs the
  same tests before it publishes, so the broken change is not published.

---

## 11. Where events show on the website

### 11.1 Every place

| Place | English | Spanish | Which events | Notes |
|---|---|---|---|---|
| **Events page** | [/events/](https://neta65.github.io/aagrapevine/events/) | [/es/events/](https://neta65.github.io/aagrapevine/es/events/) | every upcoming event, grouped by month; **Past events** (the 12 newest one-off events) | filter chips: All · Committee meetings · NETA 65 events · GV & LV calendars; `?filter=neta` works; a **Save the date** card for the next assembly |
| **Home page**, "Upcoming events" | [/](https://neta65.github.io/aagrapevine/) | [/es/](https://neta65.github.io/aagrapevine/es/) | up to 4 (3 on a phone). The next committee meeting is in the top card instead. The next date of each series **we** hold always keeps a place; the rest go to the soonest one-off events | the title links to: a series → its card on `/events/`; otherwise the event's `url`, else its flyer, else its online link — so a **flyer event opens the Drive flyer** |
| **Calendar files** | [/events.ics](https://neta65.github.io/aagrapevine/events.ics) | [/es/events.ics](https://neta65.github.io/aagrapevine/es/events.ics) | all of `/events/` incl. committee meetings (3 months back to 12 ahead); events that ended more than 90 days ago are dropped | subscribe from the card **Subscribe to calendar** on `/events/#subscribe` (Google, Apple, Outlook); `/events/` also names the file in its page head (`<link rel="alternate" type="text/calendar">`), so calendar apps can find it |
| **Add to calendar** button | on each card | | that one event | Google Calendar, Outlook.com, or an Apple / Outlook `.ics` file |
| **Share** button, and the event's share page | `/events/<card>/` | `/es/events/<card>/` | every event of `/events/` but the committee meeting, past ones too while they are in the data (since October 2026) | the Share button sends the event's own small page: in WhatsApp, Facebook and other link previews it shows the event's title, day, place and **flyer**, then sends the visitor on to the card on `/events/`. Not in the search or the sitemap. When the event has left the data, the address still lands on `/events/` (the 404 page sends it on). The committee meeting's cards share `/events/#<card>` |
| **The month's calendar file** | `/monthly/2027-03/` → "Add March's dates to my calendar" | `/es/monthly/2027-03/` | the month's committee meeting, events and series dates (for the current month, those not over yet) and the story deadlines (since October 2026) | `/monthly/2027-03/neta65-grapevine-2027-03-en.ics` (`…-es.ics` under `/es/`); the same `UID`s as `/events.ics`, so a calendar that has both shows each event once |
| **Monthly toolkit** | [/monthly/](https://neta65.github.io/aagrapevine/monthly/), `/monthly/2027-03/` | `/es/monthly/` | every event of the month (series dates worked out from the rule, also for later months) | day or range, time + "Central" / "(hora del Centro)", the **city** when the title does not name it, "Online", "Details to be confirmed", "Over" once past |
| **District report** (text on `/monthly/`) | | | the next 45 days, at most 10, a series once ("every month") | "details to be confirmed" for tentative events |
| **Monthly digest** + its e-mail | [/digest/](https://neta65.github.io/aagrapevine/digest/) | `/es/digest/` | the events that **took place** in the month covered, plus that month's committee meeting (GV/LV calendar listings are not there: they leave the data the day after they end) | days only; listed, never counted as news; see [E-mail and alerts](email-and-alerts.md) |
| **What's New** and **RSS** | [/whats-new/](https://neta65.github.io/aagrapevine/whats-new/), [/feed.xml](https://neta65.github.io/aagrapevine/feed.xml) | `/es/whats-new/`, `/es/feed.xml` | flyer, file, calendar and feed events first seen in the last 30 days and not over — never meetings or series dates | the link is the event's `url` (a flyer event: the Drive flyer) |
| **Search** | [/search/](https://neta65.github.io/aagrapevine/search/) | `/es/search/` | every event except committee meetings; a series once (its next date); past events only while they are in **Past events** | "every month" (a monthly series), "booth / literature table" (a monthly booth) and "details to be confirmed" are searchable words |
| Bulletin page, "Coming up" | `/bulletin/` | `/es/bulletin/` | the next committee meeting and the next other event | |
| Photos page, "Next chance for photos" | `/photos/` | `/es/photos/` | the next 2 in-person NETA 65 events (no meetings, online events, GV/LV listings or later series dates) | |
| Contribute page, workshops | `/contribute/#workshop` | `/es/contribute/` | the next 3 events whose title says "writing workshop", "recording workshop", "taller de escritura" or "taller de grabación" | name a workshop that way to be listed here |
| Committee menu, "Events" count | | | upcoming events except meetings, a series once | |
| **Web presentations** | `/orientation/` | `/es/orientation/` | live facts: the next NETA 65 assembly (an event coloured "Area assembly"), event lists filtered by workshops / NETA 65 / calendars / assemblies, La Viña's workshop dates | [Presentations](presentations.md) |
| **Booth display** | `/about/#booth` | `/es/about/#booth` | a slide with the next 4 events of `/events/` (never committee meetings; a monthly series once, its next date), each row until its event is over; a countdown to the next NETA 65 assembly; La Viña's monthly workshop in "Meetings you can join"; the next 12 events that are not online-only in the player's "pick the event" (Settings → Event) | a hybrid event shows its place and "Online on Zoom"; a title with a word the booth never shows is left out of the list; [Booth display](booth.md) |
| The flyer **file** itself | `/portfolio/` (Flyers tab), `/library/` (PDF / document flyers only), home "Shared by the committee" | Spanish versions | every flyer, dated or not | [Photos, slides and reports](photos-slides-reports.md) |
| **Status** | [/status/](https://neta65.github.io/aagrapevine/status/) | `/es/status/` | — | only the health of the sources: the rows "Committee Google Drive", "Events added by hand" and "GV/LV event calendars", and the "Other calendars" section |

### 11.2 What each part of an `/events/` card comes from

| Part of the card | From |
|---|---|
| Date tile (`MAR · 14 · Sun`; `MAR · 19–21 · Fri–Sun` for several days) | start and end |
| Kind badge and colour | first match wins: committee meeting → `host: lv` / `gv` → a title with booth, table, kiosk, stall, mesa or puesto ("Literature booth") → assembly / asamblea ("Area assembly") → La Viña / LV or Grapevine / GV (whichever the title names first) → a GV/LV calendar listing → otherwise "NETA 65" (our events) or "Event". (The home card says "Event" for one of ours that matches nothing.) |
| **Details to be confirmed** | `tentative` |
| **Every month** | a series date |
| **New** | first seen in the last 14 days (never meetings, series dates or past events) |
| Language pill (EN / ES / FR) | the event's language differs from the page and the committee did not write that language by hand |
| Title — a link only when `url` is a real page other than the flyer | `title` / `title_es`; `url` |
| Date range line | an event over several days |
| Time line: "2:00 – 5:00 PM CDT", "8:00 PM – 1:00 AM CDT" (past midnight), "9:00 AM CDT" (no end), "All day", "3 days", "Time not listed — see event details" | start, end (on the night the clocks change, the zone is shown at both ends: "7:00 PM CDT – 1:30 AM CST") |
| Place with a map pin, or "to be announced" in italics with an hourglass | `location` (`location_es`) |
| "Online on Zoom" / "Online" | `online_url`, or a place such as "Zoom" |
| "Meeting ID …" | `meeting_id` |
| Contact mail link | `contact` (monthly series) |
| Repeat line + "Then …" | a series |
| Description (formatted) or a 3-line teaser | the text below the header; a series' `summary` |
| "Auto-translated" | the shown text is a machine translation |
| Buttons | **Join online** (`online_url`) · **Add to calendar** · **View flyer** (`flyer`) · **Event details** (an outside `url`, no flyer) · **Share** (the event's share page, 11.1) |
| Picture beside the card | the flyer (or `image:`) |

### 11.3 What goes into the calendar files

| Line | From |
|---|---|
| `UID` | `ev-<kind>-<id>@neta65-gvlv` (`…-es@…` in the Spanish file): `ev-flyer-<Drive file id>`, `ev-manual-<file name>`, `ev-recurring-<key>-<date>` — written in small letters, other signs turned into dashes. It stays the same while the Drive file, the file name or the key stays the same. |
| `DTSTART` / `DTEND` | times in UTC; all-day events as dates (`DTEND` = the day after the last day); no end → one hour |
| `SUMMARY` | the title in the file's language |
| `DESCRIPTION` | "Details to be confirmed. The date, place or times may still change…" (tentative) · the summary · the repeat line with "Central time" · a "to be announced" place · "Online on Zoom: <link>" · "Meeting ID: …" · "Contact: …" · "Flyer: <link>" · "Details: <page>" |
| `LOCATION` | the place; the online link when there is no place; nothing for "to be announced" |
| `URL` | the event's own page; else its card on `/events/`; for a dated flyer, the Drive flyer |
| `ATTACH` | the flyer link |
| `CATEGORIES` | Committee meeting · NETA 65 event · Grapevine / La Viña calendar |
| `STATUS` | `TENTATIVE` or `CONFIRMED` (also in a single event's **Add to calendar** file, since October 2026) |
| `SEQUENCE` | the minutes since 2026-01-01 UTC when the file was made (since October 2026): it grows with every new file, so a calendar app that already has the event takes a changed time instead of keeping the old one |

Example — the flyer `2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` becomes (shortened):

```text
BEGIN:VEVENT
UID:ev-flyer-<file id>@neta65-gvlv
DTSTART:20270314T140000Z
DTEND:20270314T150000Z
SUMMARY:Spring Assembly booth
DESCRIPTION:Flyer: https://drive.google.com/file/d/<file id>/view
LOCATION:Tyler Civic Center
URL:https://drive.google.com/file/d/<file id>/view
ATTACH:https://drive.google.com/file/d/<file id>/view
CATEGORIES:NETA 65 event
STATUS:CONFIRMED
END:VEVENT
```

### 11.4 How long an event stays listed

| Event | Leaves the upcoming lists |
|---|---|
| All day (one or several days) | at midnight Central after its **last** day |
| With a start and an end | at its end |
| With a start and **no end** | **one hour** after the start (calendars also give it one hour) |

After that, a one-off event moves to **Past events** (only the 12 newest are kept) and stays in the
calendar files for about 90 days. Series dates and committee meetings never show under Past events. An event that
ends while `/events/` is open leaves the page, its filter chips' counts and the "Showing N events" line at once
(since October 2026).

---

## 12. Fix a translated event title

Titles are machine-translated into the other language. Three ways to control that:

| Event comes from | Best fix |
|---|---|
| A `content/events` file | write `title_es` (or `title_en` in a Spanish file) and `summary_es` — [6.4](#64-every-field) |
| A monthly series | write both `title` and `title_es`, `summary` and `summary_es` |
| A dated flyer, a GV/LV calendar listing, a feed | a line in [`data/translations/overrides.yml`](../data/translations/overrides.yml) |

For a **flyer event** the key is the **event title** (after the date, time and place are taken out), not the
file name. `2026-10-26 Taller de Escritura de La Viña 7-9pm @ Grupo Libro Grande, Tyler, TX.jpg` has the
event title `Taller de Escritura de La Viña`, so in the "Spanish → English" part:

```yaml
"Taller de Escritura de La Viña": { en: "La Viña Writing Workshop" }
```

The same file's **Portfolio** entry keeps the time and place in its title
(`Taller de Escritura de La Viña 7-9pm @ Grupo Libro Grande, Tyler, TX`) and needs its own line if you want
it fixed too. A real calendar example already in the file:

```yaml
"XLII REUNIÓN DE A.A. ZONA NORTE DE TEXAS ( A.A. Un Camino a la vida )": { en: "XLII North Texas Zone A.A. Gathering (A.A. A Way of Life)" }
```

An override always wins and is not marked "Auto-translated". A typo in `overrides.yml` pauses new
translations and shows under **Settings problems**. Words that must never be translated (names) go in
`data/translations/glossary.yml`. Everything about translations: [Translations](translations.md).

---

## 13. Going further: change the code

Line numbers change all the time, so this section names the **file**, the **function** and a **search
string** (press Ctrl+F in the GitHub editor, or use the repository search). Code changes go through the same
commit → **Code check** → **Website update** path; run the tests first ([13.5](#135-run-the-tests)).

### 13.1 The chain

```text
Drive  …/2027-2028_Panel77_GVLV/flyers/<dated name>
   └─ scripts/sync/drive.py        build_item()            name → extra.event_date, event_title, event_time,
                                                           event_end_time, event_location, event_tz
        └─ data/raw/drive.json
content/events/*.md
   └─ scripts/sync/announcements.py parse_event()          header → extra.start, end, location, flyer_url …
        └─ data/raw/manual_events.json
config/site.yml  recurring_events: / meeting: / sources.ics_feeds:
   └─ scripts/sync/build_data.py   recurring_specs(), committee_meetings(), ics_events()
(GV/LV calendars) scripts/sync/events_external.py  →  data/raw/events_external.json

scripts/sync/build_data.py  build_events()   flyer_events() + files + series + meetings + feeds + listings
   → merge, remove duplicates, tentative / "to be announced" / platform, upcoming vs past
   → I18n.apply() translations
   → data/site/events.json
        └─ eleventy/filters/committee.js  normalizeEvents() → shapeEvent()   one display object per event
             ├─ src/pages/events.njk            /events/, /es/events/
             ├─ src/pages/events-ics.11ty.js     /events.ics, /es/events.ics   (buildIcs())
             ├─ eleventy/filters/home.js          homeEvents(), homeEventInfo()  → src/pages/index.njk
             ├─ eleventy/filters/monthly.js       dateRow()   → /monthly/
             ├─ eleventy/filters/report.js        upcomingEvents()
             ├─ eleventy/filters/library.js       search index ("events" block)
             ├─ eleventy/filters/community.js     monthEventsHeld()  ↔  scripts/notify/send_digest.py month_events()
             └─ eleventy/filters/presentations.js upcomingEvents(), EVENT_FILTERS
```

### 13.2 Where things live

| I want to… | File | Function / search string |
|---|---|---|
| accept another folder name for flyers | [`scripts/sync/drive.py`](../scripts/sync/drive.py) | `CATEGORY_SYNONYMS` → the `"flyers"` list (lower case, no accents) |
| accept another date form in names | [`scripts/sync/common.py`](../scripts/sync/common.py) | `def date_from_text(` (the `pats` list) and `MONTHS = {` — shared by flyers, bulletin posts and `content/events` file names |
| accept another time form | `scripts/sync/drive.py` | `_TIME_RANGE`, `_TIME_12`, `_TIME_24_RANGE`, `_TIME_24`, `_NOON`; `def extract_time_zone(` |
| accept another time-zone word (e.g. `MT`) | `scripts/sync/drive.py` | `_ZONE_AFTER = re.compile(` (the `ab` group) and `_ZONES = {` |
| accept another place word | `scripts/sync/drive.py` | `_PLACE = re.compile(`; `def extract_location(` |
| treat another word as a camera name | `scripts/sync/drive.py` | `_GENERIC_WORDS = {` |
| change how a flyer item becomes an event | [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) | `def flyer_events(` — the dict after `it["extra"] = {"start": start` |
| add a header field to `content/events` | [`scripts/sync/announcements.py`](../scripts/sync/announcements.py) | `def parse_event(` — next to `extra["meeting_id"] = meeting_id[:40]` |
| add a key to `recurring_events:` | `scripts/sync/build_data.py` | `def recurring_specs(` (read and check, `specs.append({`) and `def recurring_events(` (the `"extra": {` dict) |
| machine-translate a new text field | `scripts/sync/build_data.py` | `def text_fields(` |
| how merging and duplicates work | `scripts/sync/build_data.py` | `def build_events(`, `def same_event(`, `def series_dated_flyers(`, `def merge_feed_duplicates(`, `def merge_calendar_duplicates(` |
| keep more past events | `scripts/sync/build_data.py` | `PAST_EVENTS_KEEP = 12` |
| change the "New" days / What's New days | `scripts/sync/build_data.py` | `NEW_DAYS = 14`, `RECENT_EVENT_DAYS = 30` |
| allow more than 24 months ahead | `scripts/sync/build_data.py` | `RECURRING_AHEAD_MAX = 24` |
| change the one-hour length of an event without an end | [`eleventy/filters/committee.js`](../eleventy/filters/committee.js) | `EVENT_NO_END_MS` (the data side assumes one hour too: `MonthlyRule.span` in `scripts/sync/meeting.py`) |
| what the card shows | `eleventy/filters/committee.js` → [`src/pages/events.njk`](../src/pages/events.njk) | `function shapeEvent(` (the `const ev = {` object); in the template the details list (`{% if ev.contact %}`) and the buttons (`cm-ev-btns`) |
| what the calendar text says | `eleventy/filters/committee.js` | `const descLines = [];` (Google / Outlook links, the `.ics` files, the one-event download) and `export function buildIcs(` |
| which words colour an event | [`eleventy/filters/event-tone.js`](../eleventy/filters/event-tone.js) | `const RE = {` |
| words treated as "online, not a place" | `eleventy/filters/committee.js` | `const ONLINE_PLACE =` |
| button and label texts | [`src/_i18n/committee.json`](../src/_i18n/committee.json) | keys `committee.events.*` (both `en` and `es` are required) |
| the members' help box on `/events/` | `src/_i18n/committee.json` | `committee.events.how_text`, `how_linked`, `naming_ex1`…`naming_ex3`, `naming_tip` |

### 13.3 Worked example: add a "cost" detail, end to end

Goal: an event can say what it costs — "Free", "$15", "$10 suggested donation" — on its card, in Spanish on
`/es/events/`, and in the calendar text. Two ways to give it:

- in a `content/events` file: `cost: "$15"` (and optionally `cost_es: "$15 por persona"`);
- in a flyer's name, in brackets: `2027-03-14 Spring Dinner 6-9pm @ Rowlett Alano Club ($15).pdf`.

There are 8 small edits. Do them in one commit.

#### Step 1 — read `cost:` from a `content/events` file

File [`scripts/sync/announcements.py`](../scripts/sync/announcements.py), function `parse_event`. Find
`extra["meeting_id"] = meeting_id[:40]` and add below that `if` block:

```python
    cost = clean_text(meta.get("cost"))
    if cost:
        extra["cost"] = cost[:60]          # "Free", "$15" — a line on the card and in the calendars
```

A few lines further down, the loop that reads `location_es` / `location_en` (search
`# the place in the other language`) — add the hand-written other language of the cost to it:

```python
    for lang in ("en", "es"):            # the place in the other language (never machine-translated)
        loc = clean_text(meta.get(f"location_{lang}"))
        if loc:
            own.setdefault("location", {})[lang] = loc
        own_cost = clean_text(meta.get(f"cost_{lang}"))          # NEW: "cost_es: Gratis"
        if own_cost:
            own.setdefault("cost", {})[lang] = own_cost[:60]
```

Nothing else is needed to keep it: every `extra` key is saved in `data/raw/manual_events.json` and copied to
`data/site/events.json`.

#### Step 2 — read "($15)" from a flyer's name

File [`scripts/sync/drive.py`](../scripts/sync/drive.py). Near the other patterns (search
`_PLACE = re.compile(`) add:

```python
# A cost in brackets in a flyer's name: "($15)", "($20-$25)", "(free)", "(gratis)".
_COST = re.compile(r"(?i)\s*[\[(]\s*(\$\s?\d+(?:\.\d{2})?(?:\s*[-–]\s*\$?\d+(?:\.\d{2})?)?|free|gratis)\s*[\])]\s*")
```

In `build_item`, the flyer branch (search `if ndate and explicit_day and not capture_name:`), take the
cost out **before** the time and place are read, and store it:

```python
        if ndate and explicit_day and not capture_name:
            cost_m = _COST.search(rest)                          # NEW
            if cost_m:                                           # NEW
                rest = rest[: cost_m.start()] + " " + rest[cost_m.end():]
            t_start, t_end, no_time, t_zone = extract_time_zone(rest)
            loc, no_loc = extract_location(no_time)
            extra.update({
                "event_date": ndate, "event_title": tidy(no_loc) or title,
                "event_time": t_start, "event_end_time": t_end, "event_location": loc,
                # the time's own zone ("12 p. m. (hora del Este)"); without one the time is Central
                "event_tz": t_zone if t_start else None,
                "event_cost": cost_m.group(1).strip() if cost_m else None,      # NEW
            })
```

(Empty values are dropped when the item is saved, so flyers without a cost are unchanged. The Portfolio
title keeps the "($15)" — it was made earlier from the full name.) Tried on real code paths:

| Name | Title | Time | Place | Cost |
|---|---|---|---|---|
| `2027-03-14 Spring Dinner 6-9pm @ Rowlett Alano Club ($15).pdf` | Spring Dinner | 6–9 PM | Rowlett Alano Club | `$15` |
| `2027-03-14 Taller de Escritura 7-9pm (gratis) @ Grupo Amistad, Garland, TX.jpg` | Taller de Escritura | 7–9 PM | Grupo Amistad, Garland, TX | `gratis` |
| `2027-03-14 Gratitude Banquet ($20-$25) 6pm - Rowlett Alano Club.pdf` | Gratitude Banquet | 6 PM | Rowlett Alano Club | `$20-$25` |
| `2027-03-14 Writing Workshop 10am-12pm @ Tyler, TX.pdf` | Writing Workshop | 10 AM–12 PM | Tyler, TX | — |

#### Step 3 — carry it from the flyer to the event

File [`scripts/sync/build_data.py`](../scripts/sync/build_data.py), function `flyer_events`. At the end of the
`it["extra"] = {…}` dict (search `"drive_id": d["id"], "is_pdf": ex.get("is_pdf")`) add one key:

```python
                           "drive_id": d["id"], "is_pdf": ex.get("is_pdf"), "is_image": ex.get("is_image"),
                           "cost": ex.get("event_cost")}                      # NEW
```

#### Step 4 — translate it into the other language

Same file, function `text_fields`. Before `return fields` add:

```python
    if kind == "event" and clean_text(ex.get("cost")):                    # NEW: "Free" → "Gratis"
        fields.append(("cost", clean_text(ex["cost"]), False, None))
```

That one line does three things: the translation run translates the cost, `I18n.apply` writes
`i18n.cost = {"en": …, "es": …}` into `data/site/events.json`, and a `cost_es` / `cost_en` from step 1
**replaces** the machine translation (no "Auto-translated" mark for it). A wrong machine translation can be
fixed in `overrides.yml` like any title.

> **Tip:** in a file that has `title_es` / `summary_es`, also write `cost_es`. Otherwise the cost is the
> only machine-translated text, and that is enough to mark the whole Spanish card "Traducción automática"
> with an "EN" pill (`I18n.apply` adds the language to the item's `machine` list).

#### Step 5 — put it in the display object and the calendar text

File [`eleventy/filters/committee.js`](../eleventy/filters/committee.js), function `shapeEvent`.

a) Read it in the page language. Find `const contact = /^[A-Za-z0-9._%+-]+@` and add below it:

```js
  // content/events `cost:` / a flyer's "($15)" (build_data i18n.cost; extra.cost as written)
  const cost = committee ? "" : String(H.pickLang(it, "cost", lang) || "").trim();
```

b) One line in the calendar description (Google / Outlook links, the `.ics` files and the one-event
download all use it). Find `if (contact) descLines.push(` and add below it:

```js
    if (cost) descLines.push(`${t("committee.events.cost", lang)}: ${cost}`);
```

c) Hand it to the templates. Find `host: eventHost(it), meetingId, contact,` and add `cost`:

```js
    host: eventHost(it), meetingId, contact, cost,
```

#### Step 6 — show it on the card

File [`src/pages/events.njk`](../src/pages/events.njk). In the card's details list, right after the line that
starts `{% if ev.contact %}`, add:

```njk
              {% if ev.cost %}<li class="inline-flex items-center gap-1.5">{% icon "ticket", "size-4 text-faint" %} {{ "committee.events.cost" | t(lang) }}: {{ ev.cost }}</li>{% endif %}
```

(`ticket` is one of the icons the site already ships; `circle-dollar-sign` and `hand-coins` exist too.)

#### Step 7 — the label, in both languages

File [`src/_i18n/committee.json`](../src/_i18n/committee.json), next to `"committee.events.contact"`:

```json
  "committee.events.cost": {
    "en": "Cost",
    "es": "Costo"
  },
```

Both languages are required: the published build runs with `I18N_STRICT=1` and stops on a missing text, and
`tests/test_i18n_keys.py` checks it.

#### Step 8 — optional places, docs and tests

Other places that could show it (only if wanted): the home card (`homeEventInfo` in
[`eleventy/filters/home.js`](../eleventy/filters/home.js) + its card in `src/pages/index.njk`), the search
(`library.js`, the `"events"` block), the monthly toolkit (`dateRow` in `monthly.js`), the district report
(`report.js`), and search engines (the JSON-LD at the end of `events.njk` — an `offers` entry). A monthly
series would need the same key read in `recurring_specs` and copied in `recurring_events`.

Document it: add a short "`cost:`" section to [`content/events/README.md`](../content/events/README.md) and the
`extra.cost` key to the events part of [`docs/DATA_SCHEMA.md`](../docs/DATA_SCHEMA.md) — and update this guide.

Tests — add to [`tests/test_events_feeds.py`](../tests/test_events_feeds.py). In class `DriveFlyers`:

```python
    def test_a_cost_in_the_name(self):
        evs = {e["title"]: e["extra"] for e in self.events(
            "2027-03-14 Spring Dinner 6-9pm @ Rowlett Alano Club ($15).pdf",
            "2027-03-14 Taller de Escritura 7-9pm (gratis) @ Grupo Amistad, Garland, TX.jpg",
            "2027-03-14 Writing Workshop 10am-12pm @ Tyler, TX.pdf")}
        self.assertEqual((evs["Spring Dinner"]["cost"], evs["Spring Dinner"]["location"]), ("$15", "Rowlett Alano Club"))
        self.assertEqual(evs["Taller de Escritura"]["cost"], "gratis")
        self.assertIsNone(evs["Writing Workshop"]["cost"])
```

and a new class for the files (it reuses the `manual_events` helper of `TempState`):

```python
class EventCost(TempState):
    def test_cost_and_its_spanish_in_a_file(self):
        ev = self.manual_events({"2027-03-14-spring-dinner.md":
                                 'title: "Spring Dinner"\nstart: 2027-03-14T18:00:00\ncost: "$15"\ncost_es: "$15 por persona"\nlang: en\n'})[0]
        self.assertEqual(ev["extra"]["cost"], "$15")
        self.assertEqual(ev["extra"]["own_i18n"]["cost"], {"es": "$15 por persona"})
```

Then run the tests ([13.5](#135-run-the-tests)), commit, and check a card after the run: "Cost: $15" (with a ticket icon) on
`/events/`, "Costo: $15 por persona" on `/es/events/`, and a "Cost: $15" line in the event's calendar entry.

> These eight steps were tried on a copy of the code: the two new tests pass, and so do the existing
> `DriveFlyers`, `TentativeAndPlace` and `OnlineAndHybridEvents` tests.

### 13.4 Other changes people ask for

**Read `MT` as Mountain time.** In `scripts/sync/drive.py`, `_ZONE_AFTER`, the abbreviation group is
`(?P<ab>E[SD]?T|C[SD]?T|M[SD]T|P[SD]?T)`. Make the S/D optional for Mountain too:

```python
    r"|(?P<ab>E[SD]?T|C[SD]?T|M[SD]?T|P[SD]?T)(?!\w))(?:\s*\))?")
```

(`_ZONES` already maps `"m"` to `America/Denver`.) Then `2027-03-14 Workshop 6pm MT.pdf` is read as 6 PM
Mountain = 7 PM Central, title "Workshop". Add such a name to the
`test_times_past_midnight_noon_and_a_time_zone` test in `DriveFlyers`.

**Recognise another place word** (say "cafe"): add it to `_PLACE` in `drive.py`, e.g.
`…|ranch|lodge|caf[eé]|pavilion|…`. Today `2027-03-14 Coffee night 7pm - Daily Grind Cafe.pdf` has no place
(the title becomes "Coffee night - Daily Grind Cafe"); with the change the place is "Daily Grind Cafe" and the
title "Coffee night". (Both were tried on a copy of the code.)

**Keep more past events** (Past events, calendar history, the digest's month): raise `PAST_EVENTS_KEEP` in
`build_data.py`.

**Make a dated flyer and its `content/events` file one event.** Not supported today ([9](#9-when-the-same-event-comes-from-two-places)).
The natural place is `build_events` in `build_data.py`, between `manual = safe_each(` and
`ours = manual + flyers + recurring + committee`. A sketch:

```python
    manual = safe_each([i for i in ctx.items("manual_events") if i.get("kind") == "event"], prep, "event")
    # NEW: a dated flyer that is the same event as a content/events file is not listed twice; the file
    # wins and gets the flyer when it has none of its own
    keep = []
    for fe in flyers:
        twin = next((m for m in manual if same_event(ctx, m, fe)), None)
        if twin is None:
            keep.append(fe)
            continue
        tx = twin.setdefault("extra", {})
        if not tx.get("flyer_url"):
            tx["flyer_url"], tx["flyer_thumb"] = fe["extra"].get("flyer_url"), fe["extra"].get("flyer_thumb")
    flyers = keep
    ours = manual + flyers + recurring + committee
```

`same_event` already recognises the Tyler pair (same day, then the titles). Then update the members' help
(`committee.events.how_linked` in `src/_i18n/committee.json`), `content/events/README.md` ("The flyer"), this
guide, and add a test next to `test_the_same_flyer_twice_is_one_event`.

**Let `content/events` files have a `contact:` line** (today only series have it). The pages already show
`extra.contact` for any event (card mail link, calendar line), so only `parse_event` needs it: read
`meta.get("contact")`, remove `mailto:`, keep it only when it looks like an e-mail address (the shape of
`_EMAIL` in `build_data.py`), else add a problem line like the `host_problem` one.

**Honour `enabled: false` in `recurring_events:`.** In `recurring_specs`, at the top of the loop (after the
`if not isinstance(e, dict):` block) add `if e.get("enabled") is False: continue`.

### 13.5 Run the tests

On a computer with the repository (once: `pip install -r requirements.txt` and `npm ci`):

```bash
python -m unittest discover -s tests                 # everything (what Code check runs)
python -m unittest tests.test_events_feeds -v        # flyers, content/events, feeds, calendar files
python -m unittest tests.test_recurring_events -v    # recurring_events:, La Viña's workshop, the digest
python -m unittest tests.test_event_tone -v          # card colours and badges
python -m unittest tests.test_content_events -v      # every real content/events file: year, offset, end after start
python -m unittest tests.test_source_dates -v        # dates read from names and headers (day first, ranges, notes)
python -m unittest tests.test_events_external -v     # the GV/LV calendars, from saved pages
python -m unittest tests.test_i18n_keys -v           # every label has English and Spanish
python -m scripts.sync.announcements --dry-run       # prints how each content/events file is read (no files written)
```

Some tests build pages with Node and are skipped without `npm ci`. Without a computer: commit, then open
**Actions** → **Code check (tests and test build)** for that commit — green ✓ means the tests and a test
build passed.

---

## 14. Troubleshooting

**Where problems are reported:**

| What | Where |
|---|---|
| A `content/events` file that cannot be read, a bad `host:`, a non-`.md` file | Actions → latest **Website update** run → summary → **Event files to fix** (+ a yellow warning) |
| `recurring_events:` / `meeting:` / `ics_feeds:` mistakes; a stale `location_es`; a typo in `overrides.yml` | the same summary → **Settings problems** |
| A feed that gives another date, time or venue for one of our events | the same summary → **Other calendars (optional, informational)** → **Check:** lines |
| The Drive or the GV/LV calendars not answering | the summary's source table; `/status/` shows a red row; after 7 days an issue "A content source has stopped updating" is opened |
| A flyer that did not become an event | **nothing is reported** — it is simply a Portfolio file |
| A file that breaks the build | **Code check** shows a red ✗ for that commit |

| Symptom | Likely cause | Fix |
|---|---|---|
| A flyer did not become an event | no date in the name; a month only; a phone/camera name; not in the Panel folder's `flyers`; the next update has not run yet | rename it `2027-03-14 Title 9am @ Place.pdf`; check it is under `2027-2028_Panel77_GVLV/flyers`; start a run ([10](#10-what-happens-next-and-how-long-it-takes)) |
| The event is on the wrong day | a numbers-only date read the other way (`Report 05-10-2026` is May 10; `Taller 05-10-2026` is October 5); *Notes* says "could be May 10 or October 5" | write `2026-10-05` |
| **Event files to fix**: "… has no year — the event is left out until it does" (or "has no day", "has no year written in full") | a `start:` / `end:` that is not a whole date | write the whole date, as the line shows (`start: 2027-01-10`) |
| **Event files to fix**: "… is not Central time's UTC offset on …" | a wrong `-05:00` / `-06:00` | leave the offset out, or use the one the line gives |
| A three-day flyer shows on one day only | a flyer event takes the first day of a range | write a `content/events` file with `start:` and `end:` |
| A GV/LV calendar event in Texas is missing | it names neither TX nor Texas, and its city is not on geo.py's lists | nothing to do here; a `content/events` file can show it |
| The time is an hour off | a wrong `-05:00` / `-06:00` in a file; a zone word not recognised (`MT`, small letters `et`) | leave the offset out; write `(Eastern)`, `(Mountain)`, `hora del Este` |
| The event shows "All day" but the flyer has a time | the time was in `(until …)`, or written `noon`, `9-11`, `19h` | write `12 noon`, `9-11am`, `19:00` outside brackets |
| The card disappears an hour after it starts | no end time | add the end (`9-11am` in the name; `end:` in a file) |
| The title has leftovers ("Workshop et", "sábado Taller", "IMG 1234", "to 2027-03-21 …") | an unrecognised word, a weekday, a camera name or a second date | rename; for several days use a file |
| The place is missing | no `@` and the last ` - ` part has no place word | write `@ Place` |
| The city is not shown on `/monthly/` | no comma before the state (`Tyler TX`) | write `Tyler, TX` |
| The place is "jueves por Zoom" | a weekday before "por Zoom" after ` - ` | leave the weekday out, or use a file |
| The event is listed **twice** | a dated flyer **and** a `content/events` file; or a new copy of a flyer that differs a little | take the date out of the flyer's name and link it with `flyer:`; delete the old copy |
| Card shows "FR" and the title is not translated | `ET` / `EST` in a short English name | write `(Eastern)` |
| An English title is shown as "ES", or not translated | a Spanish group name in the name | add an override ([12](#12-fix-a-translated-event-title)) or use a file with `lang:` and `title_es:` |
| No flyer picture beside the card | the flyer is on neta65.org; or the Drive file is not shared publicly | copy it to the Drive's `flyers` folder ([5.1](#51-attach-a-flyer-to-a-hand-written-event-flyer)) |
| `image:` has no effect | there is no `flyer:` line | add `flyer:` |
| `summary:` or `contact:` in a file has no effect | those keys are not read for events | write the text below the header; `contact:` works only in `recurring_events:` |
| Title is "Gv lv booth" | no `title:` line | add `title:` |
| A file shows the **old** version after an edit | the new version has a mistake | read **Event files to fix** and correct the file |
| Renamed a file and the event got a new link / "New" again | the file name is the event's identity | keep names; change the content instead |
| A monthly event shows on a date it should skip | the skip date is not one of the rule's days | read the note in **Settings problems**; it gives the right date |
| A monthly event still shows after `enabled: false` | the update ignores `enabled` | delete the block |
| A workshop listed on neta65.org is missing | the NETA 65 calendar feed is blocked by Cloudflare | write a `content/events` file |
| A GV/LV calendar event did not appear after my run | those calendars are read only by the full daily run, and only Texas or online-in-Spanish events are kept | wait for the full run; it may simply be outside Texas |
| Past event missing from the digest | only the 12 newest past one-off events are kept; GV/LV listings leave the day after | write important events as files; see [13.4](#134-other-changes-people-ask-for) |
| Subscribers still see the old time | their calendar app has not refreshed yet | wait (up to about a day for Google Calendar) |

---

## 15. Good practice and AA principles

- **Everything in `A65_GV` is public.** The folder is "Anyone with the link", and the website links to the
  Panel folder. A file kept off the website (`PRIVATE` in its name) can still be opened from the Drive. Keep
  private material out of the folder entirely.
- **Everything in the repository is public too** — `content/events` files and their comment lines included.
- **Anonymity.** No full names, phone numbers or personal e-mail addresses in file names, event files or
  descriptions; name the **group** that hosts a workshop, not the person. Flyers should show no faces of
  members (see [Photos, slides and reports](photos-slides-reports.md)). The committee's contact is
  grapevine@neta65.org; La Viña's workshop shows the official lveditorial@aagrapevine.org.
- **Attraction, not promotion.** Keep titles and descriptions factual: what, when, where, in which language.
- **Write the Spanish yourself when you can** (`title_es`, `summary_es`) — it reads better than a machine
  translation and removes the "Auto-translated" mark.
- **Keep identities stable:** the Drive file (rename it instead of re-uploading), the `content/events` file
  name, and each series' `key`. Subscribers' calendars recognise events by them.
- **Always give an end time**, and **date first** in flyer names (`2027-03-14 …`).
- **Mark what is not final** with `tentative: true`, and remove it when the details are confirmed.

---

## 16. See also

- [How-to guides (index)](README.md)
- [The Drive panel folder](drive-panel-folder.md) · [File types](file-types.md) ·
  [Photos, slides and reports](photos-slides-reports.md) · [The bulletin](bulletin.md)
- [Settings (`config/site.yml`)](settings.md) — the committee meeting (`meeting:`) and every other section
- [Translations](translations.md) · [E-mail and alerts](email-and-alerts.md) (the monthly digest) ·
  [Automatic sources](automatic-sources.md) (Grapevine / La Viña calendars)
- [Presentations](presentations.md) (live event facts) · [Pages and code](pages-and-code.md) ·
  [Automation and troubleshooting](automation-and-troubleshooting.md)
- [Booth display](booth.md) — the screen for our table at assemblies: it shows the next events and counts down to
  the next assembly.
- Repository files: [`content/events/README.md`](../content/events/README.md) ·
  [`config/site.yml`](../config/site.yml) · [`scripts/sync/drive.py`](../scripts/sync/drive.py) ·
  [`scripts/sync/announcements.py`](../scripts/sync/announcements.py) ·
  [`scripts/sync/build_data.py`](../scripts/sync/build_data.py) ·
  [`scripts/sync/events_external.py`](../scripts/sync/events_external.py) ·
  [`eleventy/filters/committee.js`](../eleventy/filters/committee.js) ·
  [`src/pages/events.njk`](../src/pages/events.njk) · [`src/pages/events-ics.11ty.js`](../src/pages/events-ics.11ty.js) ·
  [`tests/test_events_feeds.py`](../tests/test_events_feeds.py) · [`tests/test_recurring_events.py`](../tests/test_recurring_events.py)
- The main [README](../README.md): "Naming files", "Add a recurring event", "Bulletin posts and events
  without Drive".
