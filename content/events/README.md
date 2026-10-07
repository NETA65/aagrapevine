# Manual events (optional)

Committee meetings are generated automatically from `config/site.yml`, and any
flyer in the Drive `flyers` folder whose file name starts with a date becomes an
event. Use this folder for the other events: one without a flyer, or one you write
yourself and link its flyer to (see [The flyer](#the-flyer-flyer) below — the
workshops here do). One Markdown file each:

```markdown
---
title: GV/LV booth — Fall Assembly
title_es: Mesa de GV/LV — Asamblea de Otoño      # optional — your own Spanish title
start: 2027-09-18T09:00:00-05:00
end: 2027-09-18T16:00:00-05:00
location: Tyler, TX
url: https://neta65.org
lang: en                                          # the language of the title and the text below
summary_es: "Visita nuestra mesa en la asamblea." # optional — your own Spanish description
---
Optional description (English or Spanish).
```

**Give the `end` whenever you know it.** Without an end time the site counts the event as one hour long:
an hour after it starts it leaves the upcoming lists (the Events page, the home page, the monthly
toolkit's dates) and calendars get a one-hour entry. The card then shows the start time only.

`end:` can also be just a time (`end: "21:00"` or `end: 9 PM`): that time on the start's day, or the next
morning when it is not after the start (a start at 8 PM with `end: "1:00"`). It needs a `start:` with a
time. An end before the start, or a time of day when `start:` has none, is listed on the Status page, and
the file's last good version stays on the site. A start written in Spanish words keeps its time too:
`start: sábado 14 de marzo de 2027, 7:00 p. m.`

**Always the whole date, with its year.** `start:` and `end:` must be whole dates (`2027-01-10`, `January 10,
2027`, `10 de enero de 2027`, with or without a time; a Spanish first as `1° de marzo de 2027` or `primero de
marzo de 2027` is a whole date too). A date without a year (`January 10`, `10 de enero`, a year in two digits
such as `"3/19/27"`), without a day (`March 2027`, `marzo de 2027`), or a time alone (`"19:00"`, or an unquoted
`19:00`, which YAML reads as the number 1140) leaves the event out — its last good version stays — and the run
summary (and the Status page's notes for "Events added by hand") give a line ready to copy:
`start: “January 10” has no year — the event is left out until it does: write the whole date (start: 2027-01-10)`.
A UTC offset that is not Central time's on that day (`-05:00` from the second Sunday of March to the first
Sunday of November, `-06:00` the rest of the year) still shows the event, at the moment it names, and is listed
too — or leave the offset out: a time without one is Central time. A date in numbers only follows the file's
`lang:` (Spanish: day first, `05-10-2026` is October 5); `2027-10-05` can only be read one way. The **Code check**
reads every file here the same way (`tests/test_content_events.py`) and goes red, naming the file and what to
change, so a slip shows on the push that made it. *Website update* still publishes: it leaves that test to the Code
check (it tests the code, not your files), and the site goes live without the event it could not read (its last
good version stays) — listed under **Event files to fix** in the run summary and on the Status page. Fix it soon.

**Your own translation (optional).** The site translates the title and the
description into the other language automatically, and marks them
"auto-translated". To write them yourself, add `title_es` and `summary_es` to a
file written in English (or `title_en` and `summary_en` to one written in
Spanish). The other-language page then shows your words exactly as written, and
without the "auto-translated" note. `summary_es` is shown **instead of** the
whole description below the header, so write the complete Spanish text there.
Anything you leave out is still translated automatically. Put a value in quotes
when it contains `: ` (for example `title_es: "Taller: Fort Worth"`).

## The place in Spanish: `location_es`

A place is never machine-translated (addresses and group names must stay exactly
as they are). When the place itself needs words in the other language, write them
with `location_es` (or `location_en` in a file written in Spanish):

```markdown
location: "Venue to be announced"
location_es: "Lugar por anunciarse"
```

A place that is not known yet ("Venue to be announced", "TBA", "Lugar por
anunciarse") is shown as plain text, without a map pin, and is left out of the
address field of the calendar files. Without `location_es`, the Spanish page says
"Lugar por anunciarse" by itself. A real address needs no `location_es`.

## Events over several days (assemblies)

Give only dates — no times — and `end` is the **last** day:

```markdown
start: 2027-03-19
end: 2027-03-21
```

The Events page shows the range ("Fri, Mar 19 – Sun, Mar 21, 2027"), the event
stays listed until the end of its last day, and calendars show it on all three days.
A range in one line works too: `start: March 19 - 21, 2027` (or `del 19 al 21 de marzo de 2027`,
`2027-03-19 - 2027-03-21`) is all day from the first day, and its last day is the end unless `end:` says
otherwise. A file with no `start:` whose name holds a range (`Assembly March 19 - 21, 2027.md`) gets that
range.

## Details not final yet: `tentative: true`

When the date is set but the venue, the host districts or the times are not
confirmed, add:

```markdown
tentative: true            # also works: yes, sí
```

The event then shows a **"Details to be confirmed" / "Detalles por confirmar"**
badge on the Events page, the home page and the search, the same words on the
monthly toolkit's dates, poster and message, and people's calendar apps mark it
as *tentative*.

**When the details are final**, edit the file: put the real place in `location`
(and delete `location_es`, unless the Spanish needs other words), fix the dates
or times if they changed, update the description (and `summary_es`), and
**delete the `tentative: true` line**. The next update (about 3 minutes after you
save) shows it as confirmed on the site; subscribed calendars follow the next
time they refresh.

## Online events: `online_url` and `meeting_id`

An event held on Zoom (or another online platform) gives its link instead of — or as well as — a place:

```markdown
online_url: "https://us06web.zoom.us/j/81595931777"
meeting_id: "815 9593 1777"        # optional: shown on the card and in the calendars
```

Without `location:` the card says **Online on Zoom**, with a **Join online** button and no map. With a
`location:` too (a hybrid event: come in person or join online), the card shows both — the place and
**Online on Zoom** — and search engines are told it is both. The platform's name comes from the link (Zoom,
Google Meet, Microsoft Teams, Webex …); a link from anywhere else says just **Online**.

## The flyer: `flyer:`

An event's flyer shows on its card: a **View flyer** button, and beside the card (on a computer or a
tablet) a small picture of the flyer. Both open the flyer in a preview on the page. The site can show
the flyer like that only when it is on the committee's Google Drive:

1. Put a copy of the flyer in the current Panel's **flyers** folder on the Drive
   (`2027-2028_Panel77_GVLV/flyers/`) with a name **without a date**, for example
   `Taller de Escritura de La Viña - Grupo Libro Grande, Tyler.jpg`. A name that starts with a date
   (`2026-10-26 Taller de Escritura ….jpg`) makes the site create an event from the flyer itself, and the
   event would be listed twice: a dated flyer and a file here are never taken for the same event. (The
   members' help on the Events page, "Add an event", says the same.)

   The name, without its ending (`.jpg`), is also the flyer's title on the site (the Portfolio's flyers, for
   one), and the site translates titles by machine — a group's name too ("Grupo Solo por Hoy" came out as
   "Group Only for Today"). When the name contains a group's name, also add a line for it to
   `data/translations/overrides.yml`, with the group's name exactly as written in both languages — in its
   "Spanish → English" part:
   `"Taller de Escritura de La Viña - Grupo Libro Grande, Tyler": { en: "La Viña Writing Workshop - Grupo Libro Grande, Tyler" }`
   (a name in English goes in the "English → Spanish" part, with `es:`).
2. On the Drive, right-click the file → **Share** → **Copy link**, and paste the link in the file as it is
   (the committee's Drive folders are already open to anyone with the link):

```markdown
flyer: "https://drive.google.com/file/d/1gghtYzCE6Dl_IQ5_7yLueZviIK_nZqwN/view"
```

**Flyers on neta65.org can't be shown by other sites.** The Area website's bot check (Cloudflare)
turns away visitors who come from another site, so a `flyer:` that links there gets no picture on the
card (only a flyer sign) and may not open in the preview. Copy the flyer into the Drive as above. To
remember where it came from, keep the old address on the line above as a note — a line that starts with
`#` is not read:

```markdown
# flyer: a copy of https://neta65.org/wp-content/uploads/2026/09/TALLER-DE-ESCRITURA-LIBRO-GRANDE.jpeg, made 2026-10-02
flyer: "https://drive.google.com/file/d/1gghtYzCE6Dl_IQ5_7yLueZviIK_nZqwN/view"
```

If the NETA 65 calendar also lists the event with its flyer (see below), the file's own flyer is the
one shown.

## An event La Viña or Grapevine holds: `host:`

Events here are ours (NETA 65) unless the file says otherwise. For an event that **La Viña** or
**Grapevine** holds themselves, add `host: lv` (or `host: gv`): it shows with the Grapevine / La Viña
calendars on the Events page, in that magazine's colour. Its usual use: a month when La Viña holds its
monthly workshop (`lv-monthly-workshop` in `config/site.yml`) on another day — put the rule's date in
that event's `skip_dates:` and add the new day here, with the same Zoom link:

```markdown
---
title: "La Viña Monthly Virtual Workshop (in Spanish)"
title_es: "Taller Mensual y Virtual de La Viña"
start: 2026-11-19T14:00:00-06:00
end: 2026-11-19T15:00:00-06:00
online_url: "https://us06web.zoom.us/j/81595931777"
meeting_id: "815 9593 1777"
host: lv
lang: en
---
The week before Thanksgiving.
```

La Viña's own calendar lists the same day too: with the same Zoom link the two are recognized as one
event and shown once (this file wins). (Without a file, La Viña's listing of a skipped month still
shows by itself, as that month's date of the workshop — with its title, Zoom ID and flyer, but the day
only, as La Viña's calendar gives no time; a file adds the time.) `host:` takes `neta`, `lv` or `gv`
(also "La Viña", "Grapevine"); anything else — the group or district that hosts a workshop, say — is a
slip: the event still shows, as ours, and the Status page lists the line to fix (the hosting group goes
in the description).

## The same event on the NETA 65 calendar

The site can also read the NETA 65 workshop calendar (`config/site.yml` →
`sources:` → `ics_feeds:`). An event that is both there and in this folder is shown
**once**: this file wins (with your own Spanish), and the calendar only fills in
what the file leaves out (the flyer, the event page link, a venue your file still
gives as "Venue to be announced"). Both must start **the same day**; then they are
matched by their neta65.org event page (`url:`), or by a similar title at about the
same time — so keep `url:` pointing to the event's page on neta65.org when there is
one. A workshop or a booth *at* an assembly is never mixed up with the assembly.

When the calendar says something this file does not — its event page on another
date, another start time, or a real venue while the file says "Venue to be
announced" — the run summary (GitHub → **Actions** → the latest run) shows a
**Check:** line with the file's name. Update the file; nothing else is needed.

## Our dates win for good: `confirmed: true`

When the committee has checked an event's date, time and place itself (and the
NETA 65 calendar still shows something else), add:

```markdown
confirmed: true            # also works: yes, sí
```

From then on the file always wins: its date, time and place are never changed by
the calendar, the calendar's copy of the same event page (`url:`) is never shown as
a second event or on another date, and there is no **Check:** line for it any more
(only a quiet note in the run's log). Keep `url:` pointing to the event's page. If
neta65.org later uses that same page for a *new* workshop, add a file for the new
date (or delete the `confirmed: true` line once the event is over).
`confirmed` is only about the calendar: an event whose details are still open keeps
`tentative: true` as well.

While neta65.org blocks our robot (the **Status** page says so), the calendar is
not read at all: a workshop or assembly shows on the Events page only when it has a
file here.
