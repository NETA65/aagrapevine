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

## Its own page (automatic)

**Adding the file is enough.** About 3 minutes after you save, the event has a page of its own, in English and in
Spanish: `/events/<file name>/` and `/es/events/<file name>/` — for example
`https://grapevine.neta65.org/events/2026-12-12-lv-writing-workshop-fort-worth/`. Nothing else to write, and
nothing to keep up: when you change the file, the page changes with it. A dated flyer on the Drive and every date of
a monthly series (`config/site.yml` → `recurring_events:`) get a page the same way. (Since round 37, November 2026.)

Every link to the event goes there: its card's title on the Events page and its **Share** button, the home page, the
monthly toolkit, What's New, the site search, the RSS feed and the calendar entries ("Details: …"). The card's
**Event details** button still opens the event's page on another site (`url:`), when it has one.

What the page shows, from the top:

- the title, the day, the time and the place, and one plain sentence that says what the event is — "La Viña Writing
  Workshop (in Spanish) — Fort Worth is a writing workshop on Saturday, December 12, 2026, 7:00 – 9:00 PM CST, at
  Grupo Nuevo Horizonte, …";
- the event's card, as on the Events page: **Join online**, **Add to calendar**, **View flyer**, **Share** and the
  whole description;
- **Quick facts**: what, when, where (with a **Map** link for an event at a real address), the language, who
  organizes it, "Free" for the committee's own events, who can come (workshops and GVR/RLV orientations), how often
  it repeats (a monthly series) and whom to ask;
- **Get ready**: the links that fit its kind (the table below), the presentation for it, and **Make a GVR/RLV Bingo
  card for this event** — the bingo builder opens with the event's name, day, magazine and kind already filled in;
- the next event of the same kind, **Coming up** (the next three events and our next committee meeting), **Past
  events like this** with their flyers, **Flyers of similar events**, and the Grapevine and La Viña issues of the
  event's month with that month's toolkit (a Grapevine Meeting's page also shows the newest Grapevine issue);
- **Subscribe to the calendar**.

| Kind of event | What *Get ready* links |
|---|---|
| Writing workshop | the Writing Workshop presentation, Share your story, writing tips, how to send a story, the story deadlines (and their calendar), the workshop guides (PDF), recording your story (and the phone line), members of our Area in print, GVR / RLV 101's *Stories, audio and workshops*, the booth display |
| Recording workshop | the Writing Workshop presentation (the closest one), recording your story, the workshop guides, the podcasts, members of our Area in print, writing tips, the booth display |
| Information workshop | the Information Workshop presentation, magazine prices, GVR / RLV 101's *What Grapevine and La Viña are* and *Subscriptions and gifts*, the podcasts, the videos, the booth display, *Your literature table* |
| GVR/RLV orientation | the Orientation Workshop presentation, GVR / RLV 101, the GVR / RLV corner (the job, first steps, kits), signing up as a GVR or an RLV, GVR / RLV 101's *The GVR / RLV service position* |
| GSR/DCM orientation | our Area's website, GVR / RLV 101's *The GVR / RLV service position*, the GVR / RLV corner, the booth display, *Your literature table* |
| Assembly, ACM, town hall | its official page (its `url:` — else our Area's website), the booth display, *Your literature table*, photos of our displays, current offers |
| Intergroup meeting | magazine prices, current offers, the booth display |
| Literature booth (CityWide) | the booth display, *Your literature table*, photos of our displays, current offers, magazine prices, our pinned bulletin post |
| Online AA meeting (our Grapevine Meeting) | the Grapevine Meeting presentation, what happens at the meeting, the weekly open meetings, read the magazines, the podcasts |
| Monthly online workshop (La Viña's) | the podcasts, sending your story to La Viña, recording your story |
| An event from Grapevine's or La Viña's own calendar | its own page on their site, and more from the magazines' calendars |
| Anything else | read the magazines, magazine prices, Share your story, our pinned bulletin post |

A link the site cannot make is left out: a presentation whose file is not in `config/presentations/`, a bulletin
post when none is pinned, the displays' photos when there is no such album.

**Which pages search engines get.** The page of every one-off event still to come, and each monthly series' own page
(below), are meant to be found: they are in the sitemap, in both languages. An event held at a real address (a city,
a state or a ZIP code) with no page of its own elsewhere also carries the machine-readable Event Google's event
results read. The page of one date of a monthly series, of an event from Grapevine's or La Viña's own calendar and
of an event that is over is still a full page for people (the Share button sends it), but it tells search engines not
to list it (`noindex`) and is not in the sitemap. Once an event is over, its page says **This event is over**, keeps
its summary (without how to join) and the related links, but no Join or Add to calendar; it stays while the site still lists the event (the 12
newest past events, a series' dates for 90 days). After that the address sends people to the Events page (a series'
date: to its series' page).

**A monthly series' own page:** `/events/series/<key>/` (for example `/events/series/citywide-dallas/`), with how to
join (online), its flyer, its quick facts, its next 6 dates — each linked to that date's page, a date the host
moved included, a cancelled one never — and the same *Get ready* links. A new block under `recurring_events:` gets
one as soon as one of its dates is in the site's data; a block with `enabled: false`, or with no date still to come,
gets none. Its title has no date ("GV/LV booth at CityWide Dallas — Every second Saturday of the month"), so it is
the one address search engines keep for the series.

## The kind of event: `type:` (optional)

The site works out the kind of each event by itself, from its title (in English or Spanish), its tags and where it
comes from: "Taller de Escritura" is a writing workshop, "Spring Assembly" an assembly, a date of the CityWide series
a literature booth. The kind decides the page's presentation, its bingo card's occasion and its *Get ready* links
(above). Write `type:` only when the site guesses wrong:

```markdown
type: information-workshop     # also works: tipo:, kind:
```

The 15 kinds: `writing-workshop`, `recording-workshop`, `information-workshop`, `gvr-orientation`,
`gsr-dcm-orientation`, `assembly`, `acm`, `town-hall`, `intergroup`, `booth`, `online-meeting`, `magazine-workshop`,
`calendar`, `committee-meeting`, `other`. Spaces and capitals are fine here (`type: Writing workshop`). Any other
value is ignored (the site guesses, as without the line) and listed under **Event files to fix** in the run summary
and on the Status page, so you can fix it; the event still shows. A monthly series can take a `type:` too, in its `config/site.yml` block, written exactly as above
(`type: "booth"`); a file's own `type:` comes first. (Don't name a file `series.md`: `/events/series/` belongs to
the series' pages, so such a file gets the address `/events/ev-manual-series/` instead.)

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

**The best way to write a place:** `Venue, street, city, TX ZIP` — for example
`location: "Grupo Libro Grande, 623 West Bow, Tyler, TX 75702"`. Search engines then
get the street, city, state and ZIP code of the event
([README → Search engines](../../README.md#12b-search-engines-google-bing)).
A place still to be announced is not given to them until it is known, and
neither is a venue's name alone (`location: "Hilton Tyler"`): they need at
least its city, state or ZIP code.

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

## Cancelled: `cancelled: true`

When an event is called off, **keep its file** and add one line:

```markdown
cancelled: true            # also works: yes, sí; canceled:, cancelado:, cancelada:; or status: cancelled
```

Optional: a short word to people, in the file's language (`cancelled_note_es:` / `cancelled_note_en:` for the
other one) — one or two sentences, at most 300 characters, shown exactly as written (never machine-translated):

```markdown
cancelled_note: "The host group could not hold it this month. See you at the next workshop!"
```

**What happens at the next update** (about 3 minutes after you save):

- The event leaves the Events page, the home page, the monthly toolkit (its dates, poster and message), the booth
  display, What's New, the presentations, `/llms.txt` and the monthly e-mail. The site search keeps one result for
  it, **"Cancelled: …"** (listed after the others), which opens the notice below, until its day is over.
- A flyer that only this event uses leaves the Portfolio and What's New by itself. (Moving it on the Drive into the
  Panel's `private` folder is tidy-up only.)
- Its own page (`/events/<file name>/`, the link people may have shared) becomes a notice: **"This event has been
  cancelled. It will not take place."**, when and where it was planned, your note, a **Share** button and the next
  events like it — until its day is over. No flyer, no **Add to calendar**, no way to join. After that the address
  no longer exists and sends people to the Events page. Search engines are told the event is cancelled (Google
  shows "Cancelled" on it), and the notice stays in the sitemap until then.
- People who subscribed to the site's calendar see the entry turn into **"Cancelled: …"** (no reminder, shown as
  free time) for 90 days after its day.

**Don't delete the file right away.** Deleting it removes the entry from subscribed calendars without a word,
turns the shared link into a plain "page not found", and lets the NETA 65 calendar bring the event back. The file
can go 90 days after the event's day. To undo a cancellation, delete the `cancelled:` line.

This works for an event that has a file here. An event the site makes from a **dated flyer** on the Drive (its
name starts with a date) is cancelled by moving that flyer into the Panel's `private` folder (or renaming it so
its name no longer starts with a date). One date of a **monthly series** (`config/site.yml` → `recurring_events:`)
is cancelled with that series' `skip_dates:`. When a file here and a dated flyer both list the same event, do both:
add `cancelled: true` to the file and move the flyer.

Example: the La Viña writing workshop in Garland on November 28, 2026 was cancelled this way on November 22, 2026
(`2026-11-28-lv-writing-workshop-garland.md`).

## Online events: `online_url` and `meeting_id`

An event held on Zoom (or another online platform) gives its link instead of — or as well as — a place:

```markdown
online_url: "https://us06web.zoom.us/j/81595931777"
meeting_id: "815 9593 1777"        # optional: shown on the card and in the calendars
```

A Zoom ID (digits) shows as "Meeting ID 815 9593 1777"; a Google Meet code (letters, `abc-defg-hij`) as
"Meeting code abc-defg-hij".

Without `location:` the card says **Online on Zoom**, with a **Join online** button and no map. With a
`location:` too (a hybrid event: come in person or join online), the card shows both — the place and
**Online on Zoom**. Search engines are told only about events held at a place: a hybrid event as one you can
come to in person (never its online link), an online-only one not at all. The description they get also leaves
out every sentence with a meeting ID or meeting code, a passcode, or a Zoom or Google Meet link (the page still
shows them to people), so put those in a sentence of their own. The platform's name comes from the link (Zoom,
Google Meet, Microsoft Teams, Webex …); a link from anywhere else says just **Online**.

Once the event is over, the calendar files keep it for 90 days with its place (or **Online on Zoom**), but no
longer how to join: no link, no meeting ID or code, and none of the description's sentences that give one.

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

## Someone else organizes it: `organizer:`

The site tells search engines who organizes each event (in the page's hidden data — people never see
this line). It says our committee, the Area for the Area's own events (assemblies, ACMs, the GSR/DCM
orientations), or La Viña / AA Grapevine for an event with `host: lv` / `gv` (then `organizer:` is not
used). When **another committee or group** organizes the event — a district's La Viña workshop, say —
write its name:

```markdown
organizer: "District 87 La Viña Committee"
organizer_url: "https://example.org/district-87/"   # optional — its web page, starting with https://
```

Write the name of a **committee or group only, never a person's name** (search engines show it). Use the
committee's own name, as its flyer or its text writes it; the same words are used on the English and the
Spanish page. `organizer_url:` is optional; leave it out when the committee has no page of its own. A name
with a web or e-mail address in it, a name longer than 100 characters, or a page that does not start with
`https://` is left out (search engines are then told what they were before) and the Status page lists the
line to fix; the event still shows. Nothing else changes: the card, the calendars and the colour stay the
same, and the group that hosts the event still goes in `location:` and the description.

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
