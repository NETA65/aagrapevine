# Data contract (sync pipeline ⇄ site templates)

```
 GitHub Action (daily)                                     Eleventy build
 ─────────────────────                                     ──────────────
 scripts/sync/<source>.py ──► data/raw/<source>.json ─┐
                                                      ├─► scripts/sync/build_data.py ──► data/site/<file>.json ──► src/_data/db.js
 scripts/sync/translate.py ◄── (all raw titles) ──────┘         (adds i18n, whatsnew, status)                  (templates: db.<file>)
        └──► data/translations/cache.json  (+ overrides.yml wins)
```

* `data/raw/*.json` — written ONLY by the matching sync module. Cumulative: a run that fails
  (`ok: false`) keeps every item; items get `last_seen` updates and may be marked `"status": "gone"` when
  confirmed deleted. A run that says ok decides what stays, with one safety net since October 2026: a sudden
  drop (no live items where there were some, or fewer than half once there were 10 or more) is held back for
  one run (`held`, §1) except for the sources in `common.DROP_GUARD_EXEMPT`. Smaller drops, and the modules
  that trim on purpose (Instagram's newest `keep_per_account` posts, the editorial window, past events of other sites),
  remove items at once.
* `data/site/*.json` — written ONLY by `build_data.py`. Templates read ONLY these.
* All timestamps are ISO-8601 strings. Dates without time: `YYYY-MM-DD`.
  Datetimes: UTC `YYYY-MM-DDTHH:MM:SSZ`.

## 1. Raw file envelope — `data/raw/<source>.json`

```json
{
  "source": "youtube",
  "updated": "2026-09-23T10:17:00Z",   // last successful run of this module
  "attempted": "2026-09-23T10:17:00Z", // last run, successful or not
  "first_harvest": "2026-09-01T10:17:00Z", // first successful read of this source; never moves
  "ok": true,                          // false if this run failed (items kept from before)
  "error": null,                       // short message when ok=false
  "held": { … },                       // only while a sudden drop is held back (below)
  "changes": { "added": 2, "removed": 0, "held": 0 },   // what this run changed (below)
  "stats": { "fetched": 15, "new": 2 },// free-form counters; stats.warnings is shown on /status/
  "items": [ Item, ... ]
}
```

**`changes`** (every envelope since October 2026, written by `common.save_raw`): this run's live items (status not
`gone`) `added` and `removed`, and `held` = items kept although this run did not find them; plus `confirmed` (an ISO
time, the `held.since` of the hold) only on the run that accepted a held drop — the same items missing again, or a
module removing items it had kept back (Drive: a folder found empty twice).

**`held`** — the mass-drop guard. When a source says ok but its live items fall to zero (from any size) or lose more
than half once the previous list held at least `DROP_GUARD_MIN` = 10, `save_raw` puts the missing items back next
to this run's (new items still come in) and writes `held` = `{since, kept, previous, found, drop, examples[, ids]}`:
since when, how many kept, the counts before and found, `drop: true` (the guard put them back; `ids` = **every** one
of theirs, sorted, in the raw file only) or `false` (the module kept them itself and named them `unconfirmed`:
Drive's empty folders), and up to 5 titles. The next ok run that still misses the held `ids` removes them
(`changes.confirmed`); items that vanish only on that run are judged on their own, as a new drop (so a source that
keeps losing a few more items each run is still confirmed the next run); a run that finds them again ends the
hold; a failed run keeps it as it was — and, while a guard hold lasts, also puts back the held items its list
misses or marks `gone` (`crawl.py` writes its list on a failed run too), with `changes.removed` 0, so only a run that
works confirms the removal. (An envelope written before every id was stored, with `ids_total` larger than its `ids`
list, is read safely: its stored ids are accepted and the rest judged as a new drop; a failed run then puts back
every item it misses.) An item this run marked `gone` that the guard puts back is put back as it was before, not listed
twice. Not guarded: the sources in `common.DROP_GUARD_EXEMPT` (announcements, manual_events, events_external, editorial, instagram,
writers_archive — the reason for each is in the code) and a source switched off (`stats.disabled`, e.g.
`meetings.enabled: false`); a module may pass `save_raw(…, drop_guard=True|False)`. `status.json` `sources[]`
copies `changes` and `held` (without `ids`; `null` when none); `/status/` shows a held source as **On hold**.

**An unreadable raw file** (a hand edit or a bad merge) is never rebuilt from scratch and never written over: since
October 2026 `common.load_raw` raises `UnreadableRaw` and leaves the file exactly as it is (so `save_raw` refuses
too), `run_all` does not run that source's module at all (its row is "failed"), and `build_data` keeps what the last
build made of that source (`carry_unreadable`) until a person restores the file from git (or deletes it to read the
source again from scratch). Its `status.json` row keeps the last values with `ok: false` and "data/raw/<source>.json
cannot be read (<reason>) — restore it from git; the site keeps the last build's items" (`common.unreadable_message`;
the run summary's module row says the same), and the translation cache is not pruned meanwhile.

**A missing raw file** of a source the last build's `status.json` had items from (`count` > 0; a merge or a clean-up
deleted it, or a person did to read the source again): since October 2026 the site keeps the last build's items the
same way, the cache is not pruned ("data/raw/<x>.json is missing"), and the row keeps its count and dates with `ok:
false` and "data/raw/<x>.json is missing — the site keeps the last build's items until an update of this source works
(or restore the file from git)". If that source's next update fails, it writes the file again with `ok: false` and
no items; the last build's items still stay, and the row says "data/raw/<x>.json went missing and this source's
update since did not work (<error>) — the site keeps the last build's items until one works (or restore the file
from git)". The first update that works, even one that finds nothing, ends it. A source with nothing before starts
empty, "not run yet" (`ok: null`).

`attempted` also moves in `pdfs.json` on a full update that leaves the crawl out because
`sources.crawler.minutes_per_run` is 0 (`run_all._note_paused_crawl`; not when the file says `ok: false`): the paused
search counts as tried, so the run summary never calls it "not checked". With it go this run's own values, which the
run summary reads as this run's: `changes` = `{added: 0, removed: 0, held: <the kept count of a hold still in
force>}` and `hub_problems: []`; `updated`, `held`, the items and the stats stay as they were.

`first_harvest` is written by `common.save_raw()` (seeded from the oldest `first_seen` when an older
file has none). `build_data.py` uses it to tell the launch-day back catalog from real news (see
*is_new / What's New* in §3); the oldest `first_seen` cannot do that because it moves forward when a
source drops old items.

Source file names (and `manual_events.json`, the `content/events` files): `drive.json`, `youtube.json`, `podcasts.json`, `instagram.json`,
`articles.json`, `pdfs.json`, `events_external.json`, `editorial.json`,
`weekly_open.json`, `announcements.json`, `shop.json`, `meetings.json`, `quote.json`, `audio_project.json`,
`writers_archive.json` (its items have their own shape — §2, *writers_archive.json*).

## 2. Item (common shape for every piece of content)

```json
{
  "id": "yt:dQw4w9WgXcQ",          // globally unique, prefixed: yt: pod: ig: gv: lv: pdf: drive: ann: ev:
  "source": "youtube",             // youtube | podcast | instagram | grapevine | lavina | crawl | drive | committee | calendar
  "kind": "video",                 // video | episode | post | article | pdf | photo | document | slides | form | announcement | event | video_file
  "url": "https://...",            // where the button/link goes (external canonical)
  "title": "Original title",
  "summary": "Plain-text teaser, ≤ 400 chars, may be empty",
  "lang": "en",                    // en | es | fr | und   (language of title/summary)
  "date": "2026-09-16T14:00:00Z",  // best-known PUBLISH date (or YYYY-MM-DD); null if unknown
  "first_seen": "2026-09-23T10:17:00Z",
  "last_seen": "2026-09-23T10:17:00Z",
  "image": "https://... or /assets/... or null",
  "tags": ["season-11"],
  "category": "gvr",               // optional grouping key (see per-source below)
  "status": "ok",                  // ok | gone
  "extra": { }                     // per-source fields below
}
```

### Per-source `extra` and `category`

| source | kind | category values | extra |
|---|---|---|---|
| podcast | episode | show key (`gv` AA Grapevine's Podcast, `wo` Grapevine Weekly Open AA Meeting — `sources.podcasts[].key`) | `audio_url`, `duration_sec`, `season`, `episode`, `show`, `show_name`, `link` |
| youtube | video | `gv` / `lv` (by language) | `video_id`, `channel_id`, `duration_sec`, `playlists` [names] , `is_short` |
| grapevine / lavina | audio_project | `audio_project` | items `audio:gv` / `audio:lv` (scripts/sync/audio_project.py): see *audio_project.json* in §3 |
| quote | quote | — | `pub` (gv/lv), `text`, `attribution`, `source`, `source_lang`, `signup_url`, `date_label`, `date_from_heading`, `block` (teaser/embed/anchor), `node` — items `quote:<pub>:<date>` (scripts/sync/quote.py): see *quote.json* in §3 |
| instagram | post | account key `gv` / `lv` | `shortcode`, `account`, `username`, `media_type` (image/video/carousel), `thumb` (local path or null), `embed_url` |
| grapevine / lavina | article | publication `gv` / `lv` | `publication`, `issue_label` ("October 2026" / "Septiembre / Octubre 2026"), `issue_key` ("2026-10" / "2026-09"), `topic`, `section`, `author`, `free` (bool\|null) |
| crawl | pdf | `gvr` `rlv` `catalog` `flyer` `postcard` `news` `guidelines` `order-form` `workbook` `service` `literature` `other` | `host`, `file_url`, `size_bytes`, `pages`, `thumb` (site-relative path or null), `referrers` [{`url`,`title`}], `upload_month` ("2026-02"), `link_texts` [..] |
| drive | document / slides / photo / video_file / form | `reports` `notes` `slides` `flyers` `photos` `workshops` `announcements` `forms` `booth` `other` | `file_id`, `mime`, `panel` (77), `panel_label`, `path` ["photos","WhatsApp"], `album` (sub-folder name or null), `view_url`, `preview_url`, `download_url`, `thumb_url`, `image_url`, `is_image`, `is_video`, `is_pdf`; booth folder files (category `booth`) also `booth` (the file's name read by scripts/sync/booth_names.py), `modified` and, for a message, `body_md` — see *booth.json* in §3 (they are in no other site file) |
| committee / drive / calendar | event | `committee` `recurring` `flyer` `gv-calendar` `lv-calendar` `manual` `ics` `neta65` | `start` (ISO datetime or date), `end` (for an all-day event: the LAST day, inclusive), `all_day`, `location`, `online_url`, `flyer_url`, `flyer_thumb`, `city`, `state`, `tentative` (present, `true`, only on an event whose details are not final) (+ `recurring`, `series`, `rule`, `recurrence_label` — see §5; manual: `own_i18n`; .ics feeds: `feed`, `uid`) |
| committee / drive | announcement (a post on `/bulletin/`) | `manual` / `drive` | `body_md` (original-language Markdown), `expires` (date|null), `pinned` (bool), `publish` (date|null — content/bulletin `publish:` or a Drive name's "(from 2027-02-01)" / "(desde …)" / "(publish …)" / "(publicar …)": the post is left out of every site file until that day, Central time; a post without its own date is dated its publish day); content/bulletin: `own_i18n` (below), `link` (the header's `url:`; a file saved next to the post is `/bulletin/files/<name>`); `url` = `/bulletin/#<slug>` unless `url:` names a web page |

`editorial.json` items (kind `topic`, scripts/sync/editorial.py): `extra` = `publication`, `issue_label`, `deadline`
(date\|null), `theme` — three parts, each read and kept on its own: **Grapevine's** editorial calendar
(aagrapevine.org/contribute: an issue a month, `ed:gv:<YYYY-MM>:<slug>`), **La Viña's suggested topics**
(aalavina.org/temas-sugeridos: `evergreen: true`, no issue, `ed:lv:any:<slug>`) and **La Viña's yearly themes**
(`ed:lv:<YYYY-MM>:<slug>`, `evergreen: false`): the newest document linked from aalavina.org/recursos whose name
matches `sources.lavina.themes_link` and names a year ("Temas de LV 2026 y 2027" → Temas_de_LV_2027_2026.pdf, one
page per year: each bimonthly issue's theme and "Fecha límite para enviar tu historial: …"). Such a topic: `title` /
`theme` La Viña's Spanish words (`lang` "es"), `issue_key` the issue's first month ("2027-05"), `issue_label` as for
La Viña's issues ("Mayo / Junio 2027"; `i18n.issue_label` "May / June 2027" / "Mayo / Junio 2027"; the pages, the
report, the digest and the slides name it from `issue_key` in one style — read.js `issueName`: "May–June 2027" /
"Mayo–Junio 2027", in a sentence "mayo–junio de 2027"), `deadline` + `due_text` ("17 de octubre del 2026"), `url` and `pdf_url`
the document (a "document" to visitors), `submit_email` the address that year's page gives. Every year in the
document is read; it replaces the dated La Viña topics of the years it covers (a year it no longer lists stays until
it leaves the window). Kept: the issue on sale (the latest `issue_key` ≤ next month), the one before and all later
ones — the same window for both magazines. A part that cannot be read (a page down, no themes document linked, a
document that cannot be downloaded or read, a changed layout) keeps its previous topics and the envelope says why
(`ok: false`, `error`: "lv-themes: …" → /status/). `stats`: `gv`, `lv`, `lv_themes` (`parsed`, `kept`,
`with_deadline`, `open`; `lv_themes` also `years`, `document`, `label` — the link's text), `new`.
`extra.own_i18n` (content/events and content/bulletin files only, when the header has them):
the author's own words in the other language — `title_es` / `summary_es` (or `title_en` / `summary_en`
for a file written in Spanish) → `{"title": {"es": …}, "summary": {"es": …}, "body_md": {"es": …}}`
(the summary is also that language's `body_md`, the text the pages show). build_data puts them in
`i18n` instead of a machine translation; only a language or field left out is machine-translated
(→ `machine`). Events may also have `{"location": {"es": …}}` from `location_es` (`location_en` in a
Spanish file): the place in the other language — a place is never machine-translated.
`extra.tentative` (content/events `tentative: true` / `yes` / `sí`; an .ics feed's `STATUS:TENTATIVE`):
the details are not final — the pages show "Details to be confirmed" / "Detalles por confirmar" and the
calendar feeds write `STATUS:TENTATIVE` (every other event `STATUS:CONFIRMED`). Absent otherwise.
`weekly_open.json`: items of kind `meeting` with `extra` = `zoom_id`, `passcode`, `day`, `time`, `url`
(+ structured `weekday`, `start_local`, `timezone`, `next_start` — see §5):
1. id `weekly_open` — the **Grapevine Weekly Open** (Wednesdays), read from aagrapevine.org/grapevine-weekly-open.
   Always the FIRST item of `data/site/weekly_open.json`: templates read `db.weekly_open.items[0]`.
2. id `weekly_open_lv` — **La Viña's weekly open meeting** in Spanish (Thursdays, from Nov 5, 2026), written
   from `config/site.yml` → `lavina_weekly_open` (an official La Viña flyer; there is no web page to read), on
   every run — also when the Grapevine page cannot be read. `lang` "es", `source` "lavina", `url` "" until
   La Viña publishes a page (config `url`). Same `extra` fields as the Grapevine item (no `player_url`,
   `sentence`) plus `starts` (first meeting, "2026-11-05") and `source_note`; `next_start` is never before
   `starts`. Title and summary are the config's own words in both languages (`extra.own_i18n` → `i18n.title`,
   `i18n.summary`, never machine-translated); `i18n.day/time/time_central/when/sentence` are written by rules as
   for the Grapevine item ("Thursdays at 11:00 AM Central" / "Los jueves a las 11:00 a. m. (hora del Centro)").
   Delete the config block or set `enabled: false` to take it off the site. A `starts` date that is not on
   the configured weekday is replaced by the first real meeting (with a warning in the log). The title has no
   "New": the /monthly/ poster adds a "New" badge in the first month only.
The raw file may list them in another order (save_raw sorts by date); build_data puts Grapevine first.
Every module adds more `extra` fields than listed here; §5 lists all of them as built.

`writers_archive.json` (scripts/sync/writers_archive.py — the owner's exports of the Grapevine and La Viña online
archives, `content/archive/*.csv`, Texas writers only; read in every mode, no request): items of kind
`archive_story` in a shape of their own (no `summary`, `extra` …), a full replacement on every run, sorted newest
issue first (undated last), then by `key`. Nothing in an item changes from run to run unless the file does
(`first_seen` is kept by address):
```json
{"id": "wa:3f1c0b6e9a2d",              // "wa:" + the first 12 hex digits of sha1(key)
 "source": "writers_archive", "kind": "archive_story",
 "url": "https://www.aagrapevine.org/magazine/1991/oct/what-and-who-we-really-are",   // as in the file (http → https)
 "key": "https://www.aagrapevine.org/magazine/1991/oct/what-and-who-we-really-are",   // canonical URL, lower case:
                                       // what the daily capture is matched by
 "pub": "gv", "lang": "en",            // gv → en, lv → es (the magazine's language)
 "title": "What and Who We Really Are",
 "date": "1991-10-01",                 // the issue's first day; null when the file gives no Month / Year
 "issue_key": "1991-10", "issue_label": "October 1991",   // from the file's Month / Year, NEVER from the URL;
                                       // La Viña "Septiembre / Octubre 2016" (key = the first month)
 "year": 1991, "month": 10, "undated": false,
 "theme": null,                        // the archive listing's theme (display only), when it has one
 "subtitle": "…",                      // the publisher's own subtitle ("Brief"), ≤ 300 characters, cut on a word
 "writers": [{"name": "John W.",       // the byline as printed (only title-cased initials "H.t.b." → "H.T.B.")
              "place": "Denton, Texas",                // the printed place (typos kept: "Forth Worth, Texas")
              "city": "Denton", "state": "Texas",      // the file's own City / State columns
              "anonymous": false}],    // a letters column: one entry per Texas writer, paired by position
 "audio": false, "audio_only": false,  // the two Yes/No columns
 "online_exclusive": false,            // Notes "Web exclusive…" or theme "Grapevine Online Exclusives"
 "column": false,                      // a letters / humor column (several writers, or "Dear Grapevine",
                                       // "PO Box 1980", "At Wit's End" … — writers_archive.COLUMN_TITLE_RE)
 "signature_byline": false,            // Notes: the name was taken from the signature (no byline field)
 "group_byline": false,                // Notes: the byline names a group / institution / area
 "texas_csv": true,                    // the file's "Texas Author?": true / false / null ("Unknown …")
 "first_seen": "2026-10-05T01:02:11Z"} // the run its address first came in: from the last envelope, by address
                                       // (a row saved before rows carried it: its file's imported_at); a new
                                       // address → this run. status.json sources[].new_7d counts from it
```
A row is kept when "Texas Author?" says Yes or the writer's place is in Texas — the better reading of the printed
place and the file's City / State (`geo.classify_writer`). Where a writer is from is NOT stored: build_data works
it out on every run. Text is cleaned (HTML entities before the ";" that separates writers, tags, text saved twice
as UTF-8, NFC, ligatures, soft hyphens). A story listed twice (same magazine, issue, title and writers; the
address differs only by a "-0" ending) is kept once, by the address without the ending.
Envelope extras: `parser_version` (1) and `files` — per magazine the file in use:
`{"gv": {"name": "aagrapevine_archive_2026-10-04.csv", "name_date": "2026-10-04", "sha256": "<of the text with LF
line ends, no BOM>", "rows": 35942, "texas_rows": 819, "first_year": 1944, "imported_at": "…"}, "lv": {…}}`.
`imported_at` moves only when that magazine's file (name or contents) or `parser_version` changed. `stats`:
`files` (the names, comma-separated), `rows` (all rows of the files in use), `texas`, `neta65` (Area 65, as read
this run), `new` (addresses not in the last run), `changed` (a file was imported this run), `notes` ("New archive
file used: … (N rows, M Texas writers)"), `warnings` (an older copy still in the folder "may be deleted" — or, the
file on record while a newer one failed a check, "it stays in use until <newer> is fixed" —, a name that says the
other magazine — used as that magazine's file, or, when that magazine has its file, one line saying it is not used
—, a name without a date, an unknown `.csv` name, a file named like an archive file in another format (`.xlsx`,
`.numbers` …: not read), a missing file — its magazine keeps the last rows —, a file not saved as UTF-8, characters
that are not UTF-8 in a UTF-8 file). `ok: false` only when a file was not used: a needed column is missing (Link,
Title, Month, Year, Written By, Location (as published), Texas Author? — headers matched by how they start, any
case), it cannot be read, or it has fewer rows than `writers_archive.min_rows_ratio` (config, 0.8; 0 = off) × the
rows of the file used before; that magazine then keeps its last rows (`files.<pub>` stays the file on record) and
`error` names the file and the reason and says what stays (", the older rows stay"; the cut-off guard: "so the older
data stays"). Only a magazine with no rows and no file on record yet (a first run) goes on to its newest older file
that passes (the error then ends ", the older <file> is used instead"; with none, ", and there are no older
<magazine> rows to keep"). The other magazine's new file is taken in either way. The newest file of each magazine
is chosen by the date in its name (`2026-10-04`, `20261004`, `10-04-2026`; "(1)" and "_v2" break a tie; no date =
oldest) and its magazine confirmed by the links inside.

## 3. Site files — `data/site/*.json` (what templates read)

Every item in a site file = raw Item (**minus** `last_seen`, which only the sync modules use;
items with `status: "gone"` are left out) **plus**:

```json
"i18n": {
  "title":   { "en": "…", "es": "…" },
  "summary": { "en": "…", "es": "…" },
  "body_md": { "en": "…", "es": "…" },         // bulletin posts + manual events (render with | md; md({ h: 3 }) under an h2;
                                               // /bulletin/: md({ h: 3, ids: <post anchor> }) gives each heading an id
                                               // "<anchor>--<words>", and | mdToc with the same options lists them)
  "location": { "en": "…", "es": "…" }         // events only, and only when the place differs by language:
                                               // content/events location_es / location_en, or a place not known
                                               // yet ("Venue to be announced" → "Lugar por anunciarse")
  // more per kind — see §5 (section, topic, issue_label, album, day, time, when …)
},
"machine": ["es"],     // which languages were machine-translated (show a small "auto-translated" note)
"is_new": true         // see "is_new / What's New" below
```

`i18n.<field>.<original lang>` is always the original text; the other language is the
translation, or the original again when no translation exists (yet). Fields written by rules
(issue labels, Weekly Open day/time, committee meetings) never mark `machine`.

**is_new / What's New.** The "news date" of an item is its publish `date`; for a future-dated item
(next month's magazine issue) or an undated one it is the day the item was first found — but
only if that was more than 2 days after the source's *first* harvest (so launch day is not a
flood of the back catalog). Undated PDFs are never news by themselves (the crawler already dates
PDFs that appear on a page it knew). `is_new` = news date within 14 days. Never new: kind
`topic` (editorial themes; their date is a deadline), kind `meeting` (Weekly Open), committee
meetings, recurring events (category `recurring`, from `recurring_events:` in the config) and **back-catalog magazine stories** (articles of an issue that was never the current
issue on a magazine hub while we watched — the archive backfill found them; their issue is not in
the raw `issues` map). Back-catalog stories are real and appear on /read/ and in the spotlight, but
never in What's New. `whatsnew.json` = the newest 150 by news date (`wn_date`), same exclusions; events
appear there for 30 days after they were first announced; several Drive photos of one album on
one day become one group item (`extra.is_group`, `count`, `thumbs`). Committee meetings and recurring
events never appear in What's New (they come round every month; `SCHEDULED_EVENT_CATEGORIES`).

Files: `episodes.json`, `videos.json`, `instagram.json`, `articles.json`, `pdfs.json`,
`drive.json`, `events.json` (committee meetings auto-generated for 12 months + recurring events from
`recurring_events:` in the config + Drive flyers + TX calendar events + manual + the optional
`sources.ics_feeds` calendars — each real event ONCE, see *Events from several places* in §5), `announcements.json`, `editorial.json`, `weekly_open.json`,
`whatsnew.json` (newest 150 across all sources, sorted by date desc),
`spotlight.json` (published-writers spotlight, below), `writers_archive.json` (the Texas writers archive, below —
its own item shape), `status.json` (below),
`shop.json` (official store data, below — no `items`), `meetings.json` (Grapevine meetings, below),
`quote.json` (the Grapevine / La Viña daily quote, below), `audio_project.json` (the magazines' story lines, below),
`booth.json` (the booth display's Drive files, below — their own shape; nothing translated).

Each site file is `{ "updated": "...", "fixture": false, <extra top-level keys>, "items": [...] }`,
items sorted newest first (events: soonest first). Extra top-level keys: `instagram.profiles`,
`videos.playlists`, `episodes.shows`, `articles.issues` (§5). `drive.json` never contains a Google
Form whose `extra.form_closed` is `true`, nor a file of the booth folder (category `booth`: those are
in `booth.json` only). Output is deterministic: a re-run with the same raw data
changes only `status.json` (and `updated` stamps).

### pdfs.json — the Library (official documents, each once)

`build_data.py` passes the crawler's documents through `scripts/sync/pdf_curate.py`, so every consumer
(/library/, search, What's New, the digest, the home counters, /gvr/ and /shop/) sees the same list:

1. **Official sources only.** A document is kept only when its *file* is on a host listed in
   `config/site.yml` → `library.official_hosts` (default `aagrapevine.org`, `aalavina.org`, `aa.org`,
   `aaws.widen.net`; subdomains such as `www.` included). Local event flyers that a Grapevine event page
   links on other sites are left out (logged with their hosts), and the crawler no longer records them
   (`crawl_rules.pdf_url_from_href`, `OFFICIAL_DOC_HOSTS`).
2. **The same file twice** — the same address (the two magazine sites share one files directory; case and
   %-encoding ignored), or the same `size_bytes` + `pages` and the same title / the same file name apart
   from Drupal's `_0` suffix / an identical first-page thumbnail. Copies in the same document language:
   one stays (a live one; the magazine whose language is the document's; a real title over a file name;
   the newest upload; a rep-kit copy) and takes over the others' `referrers` (max 5) and kits;
   `extra.duplicates` lists the other addresses. Copies filed under different languages by the two sites
   (a bilingual file, e.g. the joint catalog) become one entry with `extra.same_file: true` (rule 4).
3. **Superseded versions** — the same original title, document language, category and type (e.g. a 2019
   "YouTube Channel" postcard and its 2026 replacement): only the newest stays. The title is compared without
   a leading publication name ("Grapevine", "AA Grapevine", "AAGV" — not "La Viña"), a trailing edition code
   ("EE", "Rev 2", "v2") and language markers: the 2013 "Copyright and Reprints Policy" gives way to the 2024
   "Grapevine Copyright and Reprints Policy", the 2023 price-increase release "(English)" to its "EE"
   re-issue. The publication does not count (the two sites share one files directory).
4. **Language editions** — an English and a Spanish (French…) edition of one document (a compatible type
   and a different `doc_lang`, plus one of: the same English title once "(English)" / "(Spa.)" markers and
   edition codes are removed — word order and small words ignored — and dates within 45 days, file names
   that differ only by the language word, or the GVR-kit / RLV-kit counterparts with the same type and page
   count; or, when the titles differ, file names that differ only by the language word AND dates within 45
   days — a French flyer whose French title was never translated —, or dates within 45 days + the same page
   count + a "found on" page in common + one title's words inside the other's once publication names are
   dropped, the title and every link text tried — "Privacy Policy" ⊆ "Privacy and Security Policy") become
   ONE item (chains join: FR ↔ ES ↔ EN): the English edition (else the Spanish one) is the item and
   `extra.versions` lists every edition. A French title the language detector took for English
   (`lang: "en"`, `doc_lang: "fr"`) is not used as the English title:

```json
"extra": { "versions": [
  { "lang": "en", "id": "pdf:98c45b8072b5", "url": "https://www.aagrapevine.org/…/Audio_download_GV_2026.pdf.pdf",
    "title": "Audio Downloads", "title_lang": "en", "i18n_title": { "en": "…", "es": "…" }, "machine": ["es"],
    "source": "gv", "date": "2026-01-08", "first_seen": "…", "category": "gvr", "tags": ["postcard"], "is_new": false,
    "host": "…", "file_url": "…", "filename": "…", "size_bytes": 97595, "pages": 1, "thumb": "…",
    "upload_month": "2026-01", "referrers": [ … ] },
  { "lang": "es", "id": "pdf:12db76ab9b4b", "url": "https://www.aalavina.org/…/Descarga_de_audios_2026.pdf", … }
], "kits": ["gvr", "rlv"] }
```

   `lang` = the edition's document language; order en, es, fr. The item's `i18n.title.<lang>` is the
   title of that language's edition (its original title when written in that language), language markers
   and edition codes removed; `machine` / `is_new` follow. `extra.kits` = every rep kit the document is in when that is more
   than its own `category` says. The Library shows one card per item: the edition in the page language
   (else the item's own), with links to every edition ("English · Español"; none for `same_file`), and the
   language filter counts every edition's language. /gvr/ and /shop/ (eleventy/filters/read.js
   `pdfEditions`) list each edition in its own kit. Every collapse is logged by the build.

### spotlight.json — published writers (home page + /published/)
Grapevine and La Viña stories published in the last 60/90 days, with where each writer is from.
Settings: `config/site.yml` → `spotlight:` (`home_days`, `list_days`, `default_scope`,
`neta65_counties`).
```json
{
  "updated": "2026-09-23T23:40:00Z", "fixture": false,
  "today": "2026-09-23",              // build day (America/Chicago) the windows were counted from
  "home_days": 60,                     // home page window
  "list_days": [60, 90],               // windows offered on the list page (first = default)
  "default_scope": "neta65",           // list page default: neta65 | texas | all
  "counts": {                          // stories per window and scope; "texas" INCLUDES neta65
    "60": { "neta65": 2, "texas": 8, "all": 100 },
    "90": { "neta65": 4, "texas": 15, "all": 156 }
  },
  "items": [ Article, … ]
}
```
* `items` = every **story with a byline** (`extra.author` or `extra.author_location`; "In Every Issue"
  departments such as Letter from the Editor / Dear Grapevine / Cartas del lector are left out) whose
  `extra.pub_date` lies within the longest window (`today − max(list_days)` … `today`, inclusive),
  from **any** place — so the page can offer an "everyone" view.
* Sorted: scope (`neta65`, `texas`, `other`, `unknown`), then `extra.pub_date` newest first, then title.
* Each item is the complete article item of `articles.json` (same fields, `i18n`, `machine`, `is_new`)
  — including `extra.geo` and `extra.pub_date`. To show a window of N days:
  `extra.pub_date >= today − N days`; for "Texas": scope `neta65` or `texas`.
* With no Area 65 writer in the window, `counts[..].neta65` is 0 and the page must say so gracefully.

### writers_archive.json — the Texas writers archive (/published/#archive)
Every Grapevine (since 1944) and La Viña (since 1996) story by a writer from Texas: the rows of the owner's archive
files (raw `writers_archive.json`, §2) joined with every Texas story the daily capture holds (raw `articles.json`
— never pruned, so stories that come out after the files' date join the list; any age). Built on every run by
`build_data.plan_writers_archive` / `build_writers_archive`. Its stories are never put into `spotlight.json` or
`articles.json` (the 60/90-day lists, /read/, the digest, the report and the search keep theirs).
```json
{
  "updated": "2026-10-04T20:00:00Z", "fixture": false,
  "files": { "gv": { "name": "aagrapevine_archive_2026-10-04.csv", "name_date": "2026-10-04", "rows": 35942,
                     "texas_rows": 819, "imported_at": "2026-10-04T19:56:19Z" }, "lv": { … } },   // raw `files` without sha256, first_year
  "since": { "gv": 1944, "lv": 1996 },   // the first year of each file (all rows); without a file the oldest story
                                         // of that magazine listed, else null
  "counts": { "neta65": { "all": 376, "gv": 271, "lv": 105 },
              "texas":  { "all": 1261, "gv": 818, "lv": 443 } },   // "texas" INCLUDES neta65
  "items": [ ArchiveStory, … ]
}
```
ArchiveStory (key order as written; `i18n` / `machine` only when a field has a translation):
```json
{"id": "wa:3f1c0b6e9a2d", "key": "https://www.aagrapevine.org/magazine/1991/oct/…", "url": "https://…",
 "pub": "gv", "lang": "en", "title": "What and Who We Really Are",
 "summary": "…",                        // the publisher's subtitle (≤ 300 characters), or null
 "i18n": {"title": {"en": "…", "es": "…"}, "summary": {"en": "…", "es": "…"}}, "machine": ["es"],
 "issue_key": "1991-10", "issue_label": "October 1991",   // null for an undated story
 "year": 1991, "decade": 1990,          // decade = year // 10 * 10; null when undated
 "theme": "…",                          // or null (display only, in the story's language)
 "writers": [{"name": "John W.", "anonymous": false, "place": "Denton, Texas",       // place: as printed
              "geo": {"scope": "neta65", "city": "Denton", "county": "Denton", "counties": ["Denton"],
                      "state": "TX", "label_en": "Denton, Texas", "label_es": "Denton, Texas"}}],   // geo.py result
 "scope": "neta65",                     // neta65 | texas — the best writer's (geo.best_of)
 "county": "Denton",                    // that writer's principal county, or null
 "audio": false, "online_exclusive": false, "column": false,
 "from": "csv"}                         // csv (the files only) | capture (the daily capture only) | both
```
* **Sorted** newest `issue_key` first (undated stories last), then by title (accents and case ignored), then `key`.
* **Where each writer is from** is worked out on every run — the best reading (lowest scope in `neta65`, `texas`,
  `other`, `unknown`; then the one with counties, then with a principal county) of the printed place, the file's
  City / State and, for a captured story, its byline — so a change of `spotlight.neta65_counties` shows at once.
  `geo.label_en` / `label_es` show a misspelt place spelt right ("Forth Worth, Texas" → "Fort Worth, Texas"); `place`
  keeps the print. A row the file's "Texas Author?" kept without a Texas place is `scope: "texas"`, `county: null`.
* **A story in both** (`from: "both"`, matched by `key`): the capture's title (and so its translation), byline and
  subtitle (when it has one); the file's theme (when the capture has none — `extra.topic`, then `issue_theme`),
  `audio`, `column` and issue (when the capture has no `issue_key`). A letters column keeps the file's writers.
  A story only in the capture (`from: "capture"`): a byline story (`spotlight_candidate`) of Texas scope, not `gone`;
  `issue_key` / `issue_label` (tidied) and `theme` from its `extra`, `summary` = `extra.subtitle`, `audio: false`.
* **Translations**: title and summary like every site item (`I18n`), asked for on every run AFTER every other text
  (tiers 5 and 6, newest issue first) — so a few runs may pass before all are done; until then a story shows its
  original (`lang`). A captured story's title reuses the capture's translation.
* Output is deterministic (no run time inside items).

### shop.json — Book of the Month, bulk discounts, subscription prices, specialty items
Read daily from the official stores by `scripts/sync/shop.py` (URLs: `config/site.yml` → `sources.grapevine` /
`sources.lavina` → `botm`, `subscriptions`, `subscription_regions`, `specialty`; ~12 page requests a day through
the shared polite session, + a product page per subscription type once a month, + the 7 specialty pages once a
week, + each product image once), then
`build_data.py`. Grapevine and La Viña are published by AA Grapevine, Inc.: every `url` is an official store
page — purchases always happen there. **ONE canonical home** for these prices and dates: templates never
hard-code a price, percent or date; other pages show at most a compact teaser that links to the shop page.
```json
{
  "updated": "2026-09-24T15:43:29Z", "fixture": false,
  "botm": [                                   // 0–2 entries, Grapevine first
    { "id": "botm:gv", "pub": "gv", "lang": "en",
      "title": "No Matter What: Dealing With Adversity in Sobriety",
      "url": "https://www.aagrapevine.org/store/no-matter-what-dealing-adversity-sobriety",   // buy here
      "page_url": "https://www.aagrapevine.org/BOTM",                                         // the offer page
      "image": "/assets/cache/shop/657477448ef71903.webp",    // ≤480 px WebP (cover), or null
      "price": 14.99, "sale_price": 11.99, "discount_pct": 20, "currency": "USD", "sku": "GV31",
      "starts": "2026-09-15", "ends": "2026-10-14",           // either may be null (dates not readable)
      "month_label": "October",                               // in the item's language ("Octubre" for LV)
      "blurb": "All recovering alcoholics have had to deal with adversity …",
      "read": "2026-10-01",                                   // the day these prices were read (Central), or null
      "price_stale": false,                                   // read on/after a book price change but still the old price
      "i18n": { "title": {"en","es"}, "blurb": {"en","es"}, "month_label": {"en","es"} },
      "machine": ["es"] } ],                                  // languages machine-translated (title/blurb)
  "bulk_discounts": {                         // physical books only (see note); per-book discount in USD
    "source_url": "https://www.aagrapevine.org/store/no-matter-what-dealing-adversity-sobriety",
    "tiers": [ {"min":1,"max":4,"off":0}, {"min":5,"max":9,"off":0.5}, {"min":10,"max":19,"off":1.0},
               {"min":20,"max":29,"off":2.0}, {"min":30,"max":null,"off":3.0} ],
    "note": { "en": "These discounts apply exclusively to physical books. …", "es": "Esta oferta se aplica …" } },
  "subscriptions": [                          // one entry per publication × region that has plans; gv first, us/ca/intl
    { "pub": "gv", "region": "us", "url": "https://www.aagrapevine.org/store/us-subscriptions",
      "plans": [                              // the store's own order
        { "type": "print", "term_months": 12, "title": "Grapevine Print Subscriptions: 1-Year",
          "price": 36.0, "currency": "USD", "sku": "GVUS1",
          "url": "https://www.aagrapevine.org/store/grapevine-print-subscriptions-1-year",
          "image": "/assets/cache/shop/b863047b363d0518.webp",
          "volume": [ {"min":2,"max":19,"price":35.5}, {"min":20,"max":39,"price":35.0}, {"min":40,"max":null,"price":34.0} ],
          "change": { "key": "2027-01", "new": 39.0, "stale": true } } ] } ],   // only on a plan a price change affects
  "types": {                                  // short official descriptions (first feature of a product page); may be {}
    "gv": { "print": {"en","es"}, "digital": {"en","es"}, "complete": {"en","es"} }, "lv": { … } },
  "specialty": [                              // /shop/#specialty — Grapevine's first, each store's own order; may be []
    { "id": "special:gv:MS08", "pub": "gv", "lang": "en", "type": "calendar",   // cards | planner | calendar | holiday | other
      "title": "Annual Wall Calendar", "url": "https://www.aagrapevine.org/store/annual-wall-calendar",   // buy here
      "image": "/assets/cache/shop/3f0c….webp",                // ≤480 px WebP, or null
      "price": 10.5, "currency": "USD", "sku": "MS08",
      "volume": [ {"min":5,"max":null,"price":10.0} ],         // the store's "Volume Discount Pricing" (price each), or []
      "trilingual": true,                                      // the store says English / Spanish / French
      "pack": null,                                            // "box of 24" → 24 (cards), "12 pack" → 12 (holiday), else null
      "text": "Full of beautiful color photographs shot by AA members, …",   // short official description in `lang`, or ""
      "page_url": "https://www.aagrapevine.org/store/annual-wall-calendar" },  // the page it was read from
    { "id": "special:lv:LVGCH1", "pub": "lv", "lang": "es", "type": "holiday",   // in season only (see below)
      "title": "¡Tarjetas de ocasión para las fiestas! Paquete de 12",
      "url": "https://www.aalavina.org/tienda/tarjetas-de-ocasion-para-las-fiestas-paquete-de-12",
      "image": "/assets/cache/shop/b3aee4f8e7e6f7da.webp", "price": 22.0, "currency": "USD", "sku": "LVGCH1",
      "volume": [ {"min":5,"max":null,"price":20.0} ], "trilingual": false, "pack": 12,
      "text": "¡Dos diseños diferentes, ilustrados por miembros de AA! Cada tarjeta está ilustrada con …",
      "page_url": "https://www.aalavina.org/tienda/tarjetas-de-ocasion-para-las-fiestas-paquete-de-12" } ],
  "price_changes": [                          // config/site.yml price_changes, checked; soonest effective day first; may be []
    { "key": "2027-01", "announced": "2026-10-01", "effective": "2027-01-01", "notice_until": "2027-01-31",
      "at": { "announced": "2026-10-01T05:00:00Z",           // 00:00 Central on those days: the moments the pages switch
              "effective": "2027-01-01T06:00:00Z",
              "notice_end": "2027-02-01T06:00:00Z" },          // the day after notice_until
      "source": { "en": "AA Grapevine's letter to Intergroups and Central Offices, October 1, 2026", "es": "Carta de AA Grapevine …" },
      "source_lang": { "en": "en", "es": "es" },              // the language each one is written in (one given: both the same)
      "doc_match": "pricing update.*2027|actualizaci[oó]n de precios.*2027",   // finds AA Grapevine's notice on Drive, or ""
      "books_more": 2.0,                                      // every book costs this much more (0: books not affected)
      "yearly": [                                             // the 1-year plans it changes, gv first, print · digital · complete
        { "pub": "gv", "type": "print", "new": 39.0,
          "now": 36.0,                                        // the store's price today (the U.S. listing first), or null
          "after": 39.0 } ] } ]                               // what the plan shows from the effective day
}
```
* `type` is `print` | `digital` | `complete` | `other`, from the title (English or Spanish: "Print",
  "impresa", "Digital", "Complete"/"completa"); `term_months` 1 / 12 / 24 / 36 (or null) from "1-Month",
  "2-Years", "1 año", "3 años". `volume` is [] when the store shows no volume pricing (digital/complete).
  Plan titles are the store's own (Spanish for La Viña) — label plans from `type` + `term_months` in the page's
  language. Prices are in USD as the stores list them ("subject to Canadian or International conversion rates").
* `sale_price` = round(`price` × (1 − `discount_pct`/100), 2); the percent is read from the offer page.
* An offer whose `ends` is before today (site time zone) is left out even if the official page still shows it;
  a page with no offer gives no entry. Years are inferred around the sync date ("SEPT. 15 thru OCt. 14"): the
  latest window that has already started (or starts within 31 days), so an old offer left on the page reads as
  past, never as next year's. An offer line with one date ("through October 14") gives `starts: null`.
* The Book of the Month page must look like one (the content block + "Book of the Month" / "Libro del mes" in
  its title or heading): an unrelated 200 page (maintenance, a redirect home) is an error (previous offer kept,
  `ok: false`), never "no offer today".
* `currency` is read from the price ("CA$ 30" → "CAD", else "USD"); `types_checked` is stamped only when every
  publication's type descriptions were read (else the next run tries again). The print plans' card text is always
  the site's own (`shop.desc_print_*`): the store's sentence counts one year's copies.
* A book is always shown under the title it is sold under (`title`, in `lang`) — on /shop/, the home teaser,
  the posters and the monthly toolkit (page and message); `i18n.title` of the other language is only a small subtitle.
* `month_label` i18n is written by rule (never machine-translated); `title`/`blurb`/`types` texts are
  machine-translated into the other language (cached, like every other text).
* A part that cannot be fetched or parsed (GV offer, LV offer, GV subscriptions, LV subscriptions — or one
  region) keeps its previous data; the raw envelope gets `ok: false` with the reason, so /status/ shows
  "Book of the Month & subscription prices" as failing and the 7-day "not updating" report catches it. A
  region listing whose cards show no readable price counts as not parsed (plans are never published without
  prices; the price and SKU are read with Drupal's field label shown or hidden).
* Specialty items (`sources.<pub>.specialty`, a list): ONE item per kind and store. `type` comes from the title
  (or the page address): cards for the holidays — "Holiday Greeting Cards - 12 pack", "¡Tarjetas de ocasión para
  las fiestas! Paquete de 12", "Christmas"/"Navidad" — → holiday; other "Greeting cards"/"Tarjetas" → cards;
  "Planner"/"Agenda de Bolsillo" → planner (never "Agenda de grupo"); "Calendar"/"Calendario" → calendar. A
  product page gives its product (title, price, SKU, picture, `text` = whole sentences of its first real
  paragraphs, 90–230 characters — a short first line such as "Two different cartoons illustrated by AA members!"
  goes on with the next paragraph; a call to action under 40 characters, a size line and a sentence with a price
  are left out —, the "5+" volume price, `trilingual`, `pack` from the name or the text: "box of 24", "12 pack",
  "Paquete de 12", "Cada caja contiene 12"). A category listing then adds the first card of each kind that no
  product page gave, without a `text`, and never a product whose own page is in the list (so an item is never
  there twice): La Viña's `/tienda/articulos-especiales` gives its greeting cards, planner and calendar;
  Grapevine's `/store/specialty-items` is only a fallback (next season's holiday cards at a new address). So
  deleting a product page's line only moves that item to the listing; `sources.<pub>.specialty_skip` (a list of
  kinds, e.g. `[holiday]`; a word that is not a kind is ignored with a warning) is the off switch: that store's
  item of that kind is never added, from any page, its previous item is dropped and its page failing is no
  error (the other store's item of the kind still shows). The pages are read at most once a week
  (`specialty_checked` in the raw envelope, stamped only when every page was read; `--refresh-specialty` forces
  it); in between, and for a page that cannot be read, the previous items are kept (`ok: false`, read again the
  next day). /shop/ shows ONE card per type, in the order cards · planner · calendar · holiday — the page
  language's store first, with a link to the other store's item of the same type.
  `text` is never machine-translated (the store's words, in its language): a card without its own text in the
  page language shows the site's own line (`shop.special_desc_*`). The same product sold by both stores (the
  SKU without its "LV" suffix: MS08LV = MS08) shares its picture and `trilingual` when one store lacks them;
  the holiday cards are two products (GVGCH1 / LVGCH1), so the other store's is linked as its edition.
* The holiday cards are SEASONAL (sold from about September through the holidays). A store that stops showing
  them — their page GONE (not fetched at all: 404 … — and no listing read in that run showing a card at that
  address), or the listing they came from without them — is not an error: shop.py keeps the last good item,
  adds `extra.missing_since` (the first day it was missed; raw file only) and lists it in the raw envelope's
  `stats.specialty_out_of_season` (on every run, the days between the weekly reads too; also in `status.json`
  `sources[].stats`, not shown on /status/); the week's read still counts as done. A holiday page that
  answers but is not understood (a new layout), or is down while a listing still shows the cards at its
  address, is an ordinary failure (`ok: false`, read again the next day; its item kept, never marked), so a
  layout change mid-season is reported instead of quietly dropping the card. build_data keeps a marked item
  on the site for `SHOP_SEASONAL_GRACE_DAYS` (14) days after `missing_since` — a store page down for a few days
  never removes it — and then leaves it out, so /shop/ shows the other three until the next season's read
  finds the cards again (that read is a fresh item: the mark is gone). One missing kind never affects the
  others.
* **Announced price changes** (`config/site.yml` → `price_changes`, checked by `scripts/sync/price_changes.py`
  `specs`; a block with a mistake is skipped or corrected and reported in `status.json` `problems.price_changes` →
  a *Settings problem* in the Actions run summary). Only what an announcement names changes: a **1-year** plan of a
  publication and format in its `yearly` list, in every region the stores list it for (`plans[].change`); the 2- and
  3-year, monthly and other plans keep the stores' prices. `change.new` is the announced price; `change.stale` says
  the plan's store `price` is still the one from before the change: read before the effective day (any build before
  it; after it, while the stores have not been read since — the raw envelope's `attempted`), or read after it but
  equal to the last price read before it (the raw envelope's `price_memory`, below: the store's own page not
  updated yet). From the effective day a stale plan shows `new`; once the store shows anything else, the store's
  price wins (`stale: false`). A plan the memory does not know (a new product) follows the store. With two changes
  for one plan, the next one still to come is given (else the latest one in effect).
  Books have no announced price of their own: before the day the pages say "`books_more` more"; from it, a Book of
  the Month whose prices were `read` before the day — or read on or after it but still at the regular price read
  before it, the same book (`price_stale`: the store's page not updated yet; `price_memory` below) — shows no amounts
  (no "you save" sums on an old price — its percent stays, with a note that the store has the current price); once
  its regular price is anything else, or a new book starts (another `sku`, on the 15th), the store's prices show.
  `price_changes[].yearly` is the notice's table (the U.S. listing first). The pages show both states
  around the effective day — `at` holds the moments — and switch in the browser (eleventy/filters/shop.js
  `shopWindow` → `data-gv-from` / `data-gv-expire`, app.js `GV.expire`, base.njk before the first paint), so a page
  built — or saved for offline use — the day before is right on the day; without JavaScript the build's state shows.
  The notice ("Prices change on …") shows from `announced` to the day before `effective`, "New prices since …" from
  `effective` through `notice_until`; `/shop/`, the Book of the Month cards, the monthly toolkit (its message and
  "Keep up all month"), the GV/LV report, the monthly digest and its e-mail (one pointer row) and GVR / RLV 101
  (the Book of the Month example) all follow them.
* Without data (never synced) the file is `{updated: null, botm: [], bulk_discounts: {source_url: null,
  tiers: []}, subscriptions: [], types: {}, specialty: [], price_changes: []}` — pages must show a graceful "see the
  official store" state (the specialty section and its hero teaser are simply left out). `price_changes` comes from
  the settings, so it is there even without store data (the notice then lists the new prices only).

### meetings.json — Grapevine meetings in our Area and nearby (the Meetings page)
Read once a day by `scripts/sync/meetings.py` from the public "12 Step Meeting List" lists of the offices in
`config/site.yml` → `meetings.feeds` (the same eight lists the Rowlett Group's meetings.html combines: Dallas,
Fort Worth, Tyler, the Spanish-speaking Dallas office, District 71 — and next to our Area the Arkansas Central
Office, OKC Intergroup and NWTA 66), then `build_data.py` (`meetings.build_site`). Only meetings whose types
include `meetings.type` ("GR") and that are not inactive. **ONE canonical home**: other pages link to the
Meetings page (at most a compact teaser); each meeting links to its page on the office's own site, which has
the joining details (Zoom links, phones and contacts are never copied).
```json
{
  "updated": "2026-09-24T22:38:35Z", "fixture": false, "type": "GR",
  "sources": [                                   // every office in config order (no keys, no feed addresses)
    { "id": "aadallas", "name": "Dallas Intergroup", "url": "https://www.aadallas.org", "in_area": true,
      "area_label": { "en": "Dallas area", "es": "Zona de Dallas" },   // config region_label
      "ok": true, "updated": "2026-09-24T22:37:36Z", "count": 5, "error": null } ],   // ok null = never read
  "groups": [                                    // our Area first, then nearby regions (config order); only groups with meetings
    { "id": "neta65", "in_area": true, "label": { "en": "Our Area (NETA 65)", "es": "Nuestra Área (NETA 65)" }, "count": 13 },
    { "id": "okcintergroup", "in_area": false, "label": { "en": "Oklahoma City area", "es": "Zona de Oklahoma City" }, "count": 8 } ],
  "items": [                                     // sorted by day, then time, then name
    { "id": "mtg:24f82f418540", "kind": "meeting", "name": "Richardson Group",
      "day": 3,                                  // 0 = Sunday … 6 = Saturday
      "time": "20:00", "end_time": null,         // local (Central) time as the office gives it; end may be null
      "location": "1144 N Plano Road, Suite 246 (Bus Route Access)",   // the place's own name; null when it only repeats the name/address
      "address": "1144 N Plano Rd, Richardson, TX 75081", "city": "Richardson", "county": "Dallas", "state": "TX",
      "lat": 32.961562, "lng": -96.699295, "approximate": false,       // approximate = the office only gives a city
      "region": "Richardson", "district": null,  // the office's own region / district names (may be null)
      "types": ["C", "D", "GR"],                 // codes → type_labels
      "attendance": "in_person",                 // in_person | online | hybrid
      "lang": "en",                              // "es" for type S or a Spanish-speaking office
      "url": "https://www.aadallas.org/meetings/richardson-group-15/", // the meeting's page on the office's site
      "sources": ["aadallas"],                   // every office that lists it (config order) — shown ONCE
      "directions_url": "https://www.google.com/maps/dir/?api=1&destination=32.961562,-96.699295",   // null: online / approximate
      "in_area": true,                           // city in an Area 65 county (spotlight.neta65_counties)
      "nearby": null,                            // out of our Area: { "id": office id, "label": {en, es} } = its group
      "i18n": {} } ],                            // meeting names are proper names: never translated
  "type_labels": { "C": { "en": "Closed", "es": "Cerrada" }, "GR": { "en": "Grapevine", "es": "Grapevine" } }  // codes in use only
}
```
* `in_area`: the city of the address is matched to its county with `scripts/sync/geo.py`
  (`data/geo/texas_places.json`; the office's region name when the city is not in the gazetteer — "Brazos Bend",
  region "Granbury" → Hood). A Texas city that cannot be matched counts as ours only when its office says
  `in_area: true`. Everything else is "nearby", grouped under its office's `region_label`.
* The same meeting in two lists (same day + time + street address — "Road"/"Rd", suite numbers ignored — or
  ≤ 60 m apart) is ONE item; `sources` names both offices and the id does not depend on which one answered.
  Two records of ONE office with their own meeting pages are never merged (two groups in two rooms of one
  club). `id` = hash of day | time | street address — else the meeting's own page (online meetings), else the
  name; two meetings of one office at one address and time also add their page, so ids are unique.
* `location` = the place's own name ("Serenity Club"); none when it only repeats the meeting's name or the
  address, and a place written as the street again plus a detail keeps only the detail
  ("1144 N Plano Road, Suite 246 (Bus Route Access)" → "Suite 246 (Bus Route Access)" — build_site applies
  this again, so older raw data is fixed without a new sync). A place name with a phone number or an e-mail
  address is dropped, and such a part of a meeting name is cut off.
* How each office is read (`methods`, in order): `feed` = the JSON list (`…/admin-ajax.php?action=meetings`);
  `page` = its public meeting-list page filtered to GR (classic page: `var locations` + table; "TSML UI" page:
  its public `tsml-cache-….json`). robots.txt is obeyed (tyler-aa.org: page only).
* Keys (Dallas, Fort Worth), tried in this order (`key_candidates`): env `TSML_KEY_AADALLAS` /
  `TSML_KEY_FORTWORTHAA` (GitHub secrets, optional) → `feed_obf` in config/site.yml (the full address with
  its key, reversed + base64 exactly like RowlettAA's meetings.html — obfuscation, not encryption;
  regenerate with `python -m scripts.sync.meetings --obfuscate "<address>"`) → RowlettAA's meetings.html
  (`key_source`, constant `key_const`, read only when needed). A key the office refuses (HTTP 401 / 403 →
  `KeyRejected`) moves on to the next source; `feeds[].key_from` names the one that worked and
  `stats.warnings` the refused one. A key is only sent to its own office's host: the keyed request follows
  redirects by hand, on that host only and when robots.txt allows (otherwise the list is not read), and
  robots.txt is checked against the full address with its query. A key is never written in plain text: not
  in data/raw, data/site, status.json or the logs (`redact()` on every address and message).
* An office that cannot be read keeps its previous meetings (`sources[].ok: false`, a note in the run
  summary); the source fails on /status/ only when no list at all could be read. An empty full list (feed or
  TSML UI cache) and a classic page with a meeting table but no `var locations` count as "cannot be read".
* `build_site` follows the settings at once (no new sync needed): `meetings.enabled: false` → the empty file;
  meetings of an office that is switched off (`enabled: false`) or removed are left out.
* Without data the file is `{updated: null, fixture: false, type: "GR", sources: [], groups: [], items: [],
  type_labels: {}}` — the page must show a graceful "see the intergroup websites" state.
* Where it shows: `/meetings/#grapevine-meetings` (`cmGvMeetings` → `gvMeetings()` in
  `eleventy/filters/committee.js`; each meeting's anchor is `#mtg-<hash>`). Elsewhere only pointers: one line
  on the home page (counts) and the site search — one `meeting` entry per group and place (`meeting:<id>`,
  a group that meets several times a week is one result), linking to its row.

### quote.json — the daily quote (home page)
Grapevine's "Daily Quote" and La Viña's "Cita Diaria", read by `scripts/sync/quote.py` from the block
`#quote-of-the-day` of each magazine's home page (`sources.<grapevine|lavina>.quote_page`, default `/`): one
request per site, in every update — the morning refresh the Morning check starts (by 5:30 AM Central; it
reads the quote right after the bulletin), the midday and evening refreshes (the 12:07 and 20:07 UTC schedules),
every push and the nightly full update —
none when an earlier module of the same run already read that home page
(the shared session's page memo). `build_data.py` → `quote.build_site()`; nothing is translated.
```json
{ "updated": "2026-09-25T12:09:40Z", "fixture": false,
  "items": [                                   // the newest quote of each publication: Grapevine, then La Viña
    { "id": "quote:gv:2026-09-25", "pub": "gv", "lang": "en",
      "date": "2026-09-25",                    // the quote's day (Central): from the heading, else the day it was read
      "date_label": "September 25",            // the same day in the quote's language ("25 de septiembre")
      "heading": "Grapevine Daily Quote September 25",
      "text": "During his first AA years …",   // as published: whitespace and the outer quotation marks cleaned
      "attribution": "AA Co-Founder, Bill W., September 1945",
      "source": "“’Rules’ Dangerous but Unity Vital”, The Language of the Heart",   // after "From:" / "De"
      "source_lang": "en",                     // a Spanish quote can come from an English book
      "url": "https://www.aagrapevine.org/#quote-of-the-day",
      "signup_url": "https://visitor.r20.constantcontact.com/…" } ] }  // the publication's own e-mail sign-up
```
* The raw file also keeps `history` (the last 14 days per publication — see *Raw envelope extras*): the guard
  that keeps a newer quote when a page shows an older one and, through each entry's `seen`, the source of
  `status.json` → `quote_days`; it is not copied into the site file.
* A page that cannot be fetched or read keeps that publication's previous quote (item + history); the raw
  envelope gets `ok: false` with the reason ("Daily quote" on /status/). The sign-up link is the teaser's
  own link field; the embed near the top of both pages links Grapevine's list, so a fallback only takes a
  link whose text names the publication's quote ("Sign up … Daily Quote" / "Regístrate … Cita").
* Where it shows: the home page only (`homeDailyQuotes` in `eleventy/filters/home.js` — the page language's
  magazine first, a quote older than 2 days left out; `home.js` adds "Today" / "Yesterday" in Central time
  and names the link "Today's quote on …" when the quote shown is not today's; on phones only the page
  language's quote shows, the other behind a button). No other page repeats it.
* Without data the file is `{updated: null, items: []}` and the home page leaves the card out.

### audio_project.json — record your story by phone (/contribute/#record)
Read daily by `scripts/sync/audio_project.py` from the official pages (`config/site.yml` → `sources.grapevine.audio_project`
= aagrapevine.org/audio-portal; `sources.lavina.record_story` + `record_instructions` = aalavina.org/graba-tu-historia and
its instructions page; `record_tips`, `record_topics`, `sample_audio` are only linked) — 3 requests a day through the
shared polite session, then `build_data.py` (nothing is translated). **ONE canonical home**: /contribute/#record;
Listen and Watch only link to it. The steps on the page are the site's own words (`community.rec.*`, hand-written EN/ES)
around the values below — never the official sentences machine-translated.
```json
{
  "updated": "2026-09-25T14:09:42Z", "fixture": false,
  "checked": "2026-09-25T14:09:27Z",          // the older of the two parts' last good reading
  "gv": {                                     // null when unknown (first run, or never read)
    "page_url": "https://www.aagrapevine.org/audio-portal",
    "phone": "(559) 726-1216", "tel": "+15597261216",     // shown (one style for both lines) / for the tel: link
    "minutes_min": 6, "minutes_max": 8,
    "keys": { "record": "1", "finish": "#", "save": "1", "permission": "2" },   // one of 0-9 # *
    "email": "webcoord@aagrapevine.org",      // Cloudflare-protected on the page: decoded (first byte = XOR key)
    "formats": ["WAV", "MP3"], "no_speakers": true,        // "does not collect recordings from speakers"
    "channel_url": "https://www.youtube.com/@AAGRAPEVINE",
    "playlists": [ { "title": "Sponsorship", "url": "https://www.youtube.com/watch?v=…&list=…" } ],
    "checked": "2026-09-25T14:09:27Z" },
  "lv": {
    "page_url": "https://www.aalavina.org/graba-tu-historia",
    "instructions_url": "…/instrucciones-graba-tu-historia", "tips_url": "…/consejos-de-grabacion",
    "topics_url": "…/temas-sugeridos", "sample_url": "…/audio-de-muestra",
    "phone": "(559) 670-1601", "tel": "+15596701601", "minutes_max": 7,
    "keys": { "record": "1" },
    "permission_text": "Otorgo a La Viña los derechos de autor de la grabación …",   // said on the call, quoted as is (es)
    "long_distance": true, "email": "lveditorial@aagrapevine.org", "formats": ["WAV", "MP3"],
    "no_speakers": true, "checked": "2026-09-25T14:09:42Z" }
}
```
* Raw items `audio:gv` / `audio:lv` (kind `audio_project`) carry the same fields in `extra`, plus `steps_text`
  (the official steps as written, for checking only).
* Each part is independent. A page that cannot be fetched, or on which a number, a key, the length or the
  e-mail address is not found (a layout or process change), keeps the previous data of that part and the raw
  envelope gets `ok: false` with the reason ("Record your story by phone" on /status/). When only La Viña's
  instructions page fails, the keys and the sentence come from the previous run and the source still counts as
  updated (`ok: true`; the problem is a note in `stats.warnings`, shown under "Notes" in the run summary).
* `phone` in the site file is written from `tel` in one style, "(559) 726-1216", whatever way each official
  page writes it (the raw `extra.phone` keeps the page's own spelling).
* `build_data` checks every value again: a part without a dialable `tel` (`+1` and 10 digits) is null; keys
  that are not one digit / `#` / `*` and an address that is not an e-mail address are dropped. The page shows a
  part's steps only when all its keys are there, and "see the official page" when the part is null.

### booth.json — the booth display's Drive files (About page)
The files of the Drive panel folder's **booth** folder (any of these names: booth, mesa, kiosk / kiosko / kiosco,
display / pantalla, stand, exhibit / exhibición — `drive.CATEGORY_SYNONYMS`; "Booth photos" is the booth folder,
"photos/Booth at CityWide" an album) for the booth display that plays at the committee's table (/about/#booth).
Each sub-folder is a COLLECTION the player can switch off; a deeper sub-folder belongs to its top one.
`scripts/sync/drive.py` gives each file `category: "booth"` and reads its NAME into `extra.booth` with
`scripts/sync/booth_names.py` — `[order] [GV|LV|GVLV] [EN|ES|BI] Title (option) (option).ext`, e.g.
`GV EN Welcome to our table (first) (15s).png`; the convention and every option are in that module's header.
`build_data.py` (`build_booth`) writes this file and leaves the booth files out of **every other site file**:
`Ctx.items("drive")` skips them, so they are never in `drive.json` (the Portfolio, the search, the digest), never a
bulletin post, a flyer's event or a series' flyer, never a photo album or a What's New entry. Only /status/
counts them, with the Drive source's other files (`sources[drive].count`; `counts.booth` = the files shown).
Nothing is translated: a title is the caption the committee wrote.

Raw item (`data/raw/drive.json`): the usual Drive `extra`, plus
```json
"booth": { "kind": "poster",              // photo | poster | video | audio | message | unsupported
           "pub": "gv",                   // gv | lv | both (the default)
           "langs": ["en"],               // [] = shown in every language mode · ["en", "es"] = bilingual
           "title": "Welcome to our table",   // "" for a camera name (IMG_1234, WhatsApp Image …, a bare number)
           "caption": true,               // false: "(no caption)", or no title
           "order": 2,                    // the leading "02 " (null without one)
           "seconds": 15,                 // photo / poster / message only, 3–120 (null: the player's default)
           "start": 5, "end": 105,        // a video / sound file's part to play, in seconds (null: its start / end)
           "muted": false,                // video / sound only
           "weight": 1,                   // 0.5 ("(rare)") or 1–5 ("(x3)")
           "first": false,
           "from": "2027-03-01", "until": null,   // days, inclusive, Central time
           "off": false,                  // "(off)" / "(draft)" or a name starting with "_" / "~": never shown
           "fit": "contain",              // cover (photo; a video asked "(photo)") · contain (poster, video) · null
           "collection": "main",          // a sub-folder: "spring-assembly-2027"
           "collection_label": "Booth folder",    // a sub-folder: its name, "Spring Assembly 2027"
           "text": null,                  // a message's text: ≤ 1200 characters, Markdown-light (**bold**, line
                                          // breaks, "- " bullets — every other mark taken out)
           "problem": null },             // why it can never be shown (English words; booth_names.PROBLEMS)
"modified": "2026-10-02"                  // when Drive last saw it changed: an exact time with GOOGLE_API_KEY,
                                          // else the day (null when the listing gave none)
```
A message (a .txt, .md, Google Doc or .docx) also has `body_md`: its text fetched and tidied exactly like a
bulletin post's (`drive.fill_booth_texts`: the same download, the same reuse while the file's `modified_text` is
unchanged, and the same per-run budget — `MAX_ANNOUNCEMENT_FETCHES`, shared with the bulletin, whose posts go
first). `text` is made from it (`booth_names.message_text`); a message whose name gives no language gets the
language(s) of its paragraphs (`drive.text_langs`). The envelope's `stats.booth_texts` (only when the folder holds
messages): `fetched`, `reused`, `failed`, `deferred`.

Site file:
```json
{ "updated": "2026-10-02T15:25:08Z",     // when the booth folder last changed — the newest first_seen / modified of
                                         // the files listed (not the run's time: the file, and the build's media
                                         // cache key, change only when the booth content does); null without files
  "fixture": false,
  "collections": [ { "id": "main", "label": "Booth folder", "count": 7 },          // the booth folder itself first,
                   { "id": "spring-assembly-2027", "label": "Spring Assembly 2027", "count": 3 } ],   // then by name
  "items": [ { "id": "drive:<fileId>", "file_id": "<fileId>", "name": "GV EN Welcome (first).png",
               "mime": "image/png", "size_bytes": 123456,          // null without GOOGLE_API_KEY
               "modified": "2026-10-02", "title": "Welcome", "kind": "poster", "pub": "gv", "langs": ["en"],
               "caption": true, "order": null, "seconds": null, "start": null, "end": null, "muted": false,
               "weight": 1, "first": true, "from": null, "until": null, "fit": "contain", "collection": "main",
               "text": null,                                       // a message's text (above)
               "image_url": "https://lh3.googleusercontent.com/d/<id>=s1920",   // photo, poster (a document's first
               "thumb_url": "https://lh3.googleusercontent.com/d/<id>=w600",    // page), video (a frame); else null
               "download_url": "https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t",
                                                                   // null for a native Google file (Doc, Slides, Drawing)
               "view_url": "https://drive.google.com/file/d/<id>/view",
               "stamp": "3f9c1a0b2d" } ],        // short hash of id + modified + size (+ Drive's clock time while the
                                                 // change is under 24 hours old): changes with every new version,
                                                 // and only then — the next day (only the day listed, no clock
                                                 // time) the file keeps the stamp of its row in the last booth.json
                                                 // (same size, that row's day = the listed day or the day after;
                                                 // never an exact API time): the build names the media copy after
                                                 // it, and a new name means every booth device downloads it again
  "problems": [ { "file": "booth/notes.zip", "problem": "not a type the booth can show",
                  "problem_es": "no es un tipo de archivo que la pantalla de la mesa pueda mostrar",
                  "code": "unsupported" } ] }    // unsupported · video-type · audio-type · no-text · dates
```
* `items` order = the player's "In order" mode: the `first` files, then by `order` (files without one after them),
  then by name (numbers as numbers: "IMG_2" before "IMG_10").
* Left out: `off` files (not even as a problem), and a file whose `until` day has passed (Central time) — it can
  never show again, so the build does not copy it for offline use either.
* `problems`: the files that can never be shown — a type the booth cannot show (`unsupported`; a video or sound
  type browsers do not play: `video-type` / `audio-type`, saying what to do), a message without text (`no-text`:
  an empty file, or one whose text could not be read yet), a `from` day after its `until` day (`dates`) — sorted by
  `file` (the folders under the panel folder + the name); the same rule is `booth_names.problem_of`. The player's
  Items list shows them; drive.py names the files in one note of its `stats.warnings` ("booth folder: 3 file(s)
  the booth display cannot show — …"), which the Actions run summary lists under "Notes".
* Read by `src/_data/booth.js` (→ /about/booth.json) and `scripts/build/booth-media.mjs` (the offline copies of
  the pictures, videos and sound files, named after `stamp`), with `config/site.yml` → `booth:`.
* Without data the file is `{ "updated": null, "fixture": false, "collections": [], "items": [], "problems": [] }`.

### status.json
```json
{
  "generated": "2026-09-23T10:40:00Z", "updated": "…", "fixture": false,
  "sources": [
    { "source": "youtube", "label": "YouTube videos", "label_es": "Videos de YouTube",
      "ok": true,            // true = last run fine · false = last run failed (older data kept) · null = never ran
      "updated": "…",        // last SUCCESSFUL run
      "attempted": "…",      // last run, successful or not
      "count": 528, "new_7d": 3, "error": null, "stats": { /* the module's own counters */ },
      "changes": { "added": 3, "removed": 0, "held": 0 },   // the raw envelope's (§1); null when none
      "held": null }       // the raw envelope's hold without its ids (§1): /status/ "On hold"; null when none
  ],
  "scheduled": [            // bulletin posts whose `publish` day is still to come (build_announcements): soonest
                            // first, at most 20 — not on the site yet; listed in the Actions run summary
    { "publish": "2027-02-01", "title": "Spring Assembly sign-ups", "source": "committee",   // or "drive"
      "file": "content/bulletin/spring.md" } ],            // a Drive post: its file name
  "quote_days": {           // when each of the last 7 mornings' daily quotes came in (quote.py history `seen`)
    "goal": "05:30",        // config site.morning_goal (missing / unreadable → "05:30"), Central time
    "days": [ { "day": "2026-09-29",                  // newest first
                "goal_at": "2026-09-29T10:30:00Z",    // that day's goal as an instant (10:30Z on a CDT day, 11:30Z on CST)
                "gv": "2026-09-29T09:31:00Z",         // when Grapevine's quote of that day was first read (null: not in)
                "lv": null } ] },
  "full_update": "2026-09-28T18:17:20Z",   // when the last FULL daily update ran: the newest `attempted` of the
                                           // sources only it reads (run_all.FULL_ONLY); null when none ran.
                                           // A quick or morning run keeps the last build's value (below)
  "crawl": { "known_pages": 3162, "crawled_pages": 52, "never_crawled": 3110, "never_crawled_events": 2939,
             "queue_remaining": 3110, "est_days_to_full": 9.6, "last_run_pages": 0, "page_errors": 0, "new": 0,
             "pdfs": 92,               // the Library's entries (curated: official, each once) — as sources[pdfs].count (its new_7d counts the same entries)
             "pdfs_gone": 0, "pdfs_with_details": 14,
             "pdfs_with_thumbs": 92,   // Library entries with a first-page preview
             "updated": "…", "attempted": "…" },   // the crawler's page counters: for the run summary / maintainers
  "translations": { "cached": 1620, "engine": "argos1.0-ct2/v6", "model_enabled": true,
                    "translated_this_run": 0, "from_cache": 1620, "pending": 0, "rejected_by_guard": 0,
                    "seconds": 0.1, "model_seconds": 0.0, "texts_per_second": null, "glossary_entries": 162,
                    "problems": [] },   // since October 2026: an unreadable cache.json moved aside
                                        // (cache.json.bad-<UTC time>), a model that could not be installed (a
                                        // failed download, a SHA-256 that does not match) — also added to
                                        // problems.translations; /status/ shows a calm line + the text; the
                                        // run summary lists them under "Translation problems"
  "counts": { "videos": 528, "episodes": 295, "…": 0, "whatsnew": 150 },
  "spotlight": { "today": "2026-09-23", "home_days": 60, "list_days": [60, 90],
                 "counts": { "60": { "neta65": 2, "texas": 8, "all": 100 }, "90": { … } }, "items": 156 },
  "writers_archive": {      // the Texas writers archive (writers_archive.json): the files in use (as there) and how
                            // the list was made
    "files": { "gv": { "name": "aagrapevine_archive_2026-10-04.csv", "name_date": "2026-10-04", "rows": 35942,
                       "texas_rows": 819, "imported_at": "…" }, "lv": { … } },
    "items": 1261, "neta65": 376, "texas": 1261,          // texas includes neta65
    "csv_only": 1245, "capture_only": 0, "both": 16 },
  "reminders": [            // dated settings that run out soon (or did) — for the Actions run summary; [] when none
    { "id": "carry-tips", "file": "config/carry.yml", "due": "2028-01",
      "message": "config/carry.yml has monthly tips only through 2027-12; the /monthly/ pages look 12 months ahead — add tips for the next months." } ],
  "problems": { },         // raw files that were missing/unreadable ("missing" = module never ran; "missing:
                           // data/raw/x.json (the last build had N item(s))" = gone while the site keeps its items, §1;
                           // "unreadable: <reason>"), and settings
                           // build_data could not use: "meeting" (also a skip_dates value that is not a meeting
                           // day), "recurring_events", "ics_feeds", "price_changes" (text says what); and
                           // "content_events": slips in content/events files that were worked around (a
                           // `location_es` still saying "Lugar por anunciarse" next to a real `location` …);
                           // "translations": data/translations/glossary.yml or overrides.yml could not be read
                           // (a YAML typo) — the cache is used as it is, and new texts stay in their original
                           // language until the file is fixed; also the translation memory or a model (above)
  "feeds": [               // the optional outside calendars (config sources.ics_feeds) — NOT content sources:
    { "key": "neta-65-workshops", "url": "https://neta65.org/events/category/workshop/list/?ical=1",
      "label": "NETA 65 workshops", "label_es": "Talleres de NETA 65",
      "category": "neta65", "group": "neta",       // where its events show on /events/ (neta | calendar)
      "state": "blocked",      // ok · blocked (the site's bot protection: HTTP 401/403/429, Cloudflare check) ·
                               // error (no answer, 404/500, not a calendar file) · never (not asked yet)
      "http_status": 403,      // since October 2026 the message is plain ("asked for fewer requests (HTTP 429)",
                               // "refused the request (HTTP 401/403), as its bot protection does" are the others):
      "error": "neta65.org answered with a bot check (HTTP 403) — nothing is wrong on our side; the last good copy is kept",
                               // (… "; there is no good copy of it yet" when none was ever read)
      "last_success": null,    // when a calendar file was last read (its copy is used while the feed fails)
      "last_attempt": "…",     // the last request (at most once a day, whether it worked or not)
      "checked_this_run": true, "from_copy": false,
      "events_count": 0,       // events the feed gave this run (from the copy when it failed)
      "duplicates": 0,         // of those, already on the calendar (content/events, a flyer, the committee
                               // meeting, a recurring_events date) — shown once
      "notes": [] }            // for the chair: what the feed says that a content/events file does not
                               // (its event page on another date, another start time, a venue the file
                               // still calls "to be announced") — listed in the Actions run summary
  ]
}
```
`reminders` (build_data `reminders`, checked against the site's calendar day, Central; English, for whoever keeps
the settings; each check reads its own file and a file that cannot be read is skipped, never a failed build):
`carry-tips` — config/carry.yml has monthly `tips` only through a month before this month + 12 (the /monthly/ pages
look that far ahead; `due` = the first month without tips); `orientation-panel` — the panel of
config/orientation.yml (`starts` + 24 months, or its `ends`) has ended; `skip-dates:<key>` — the last `skip_dates`
day of a config/site.yml `recurring_events` entry is within 90 days or past; `neta65-assemblies` — the last
content/events file whose title, `title_es`, `kind` or `tags` say "assembly" / "asamblea" starts within 60 days or
is past; `price-change:<key>` — a config/site.yml `price_changes` block whose `notice_until` has passed may be
removed (once the stores show the new prices). `due` = the date the reminder is about ("YYYY-MM-DD", or "YYYY-MM").
`counts` also has `writers_archive` (the stories of writers_archive.json).
Since October 2026 `/status/` also shows each source's `stats.warnings` (any state) in a folded *Notes from the last
update (n) — for the site maintainer* box, as raw English text (on `/es/status/` its caption says so). Drive's
`stats` there count what is not published instead of naming it: `loose_skipped`, `unreadable_folders`,
`depth_limited`, `unconfirmed_folders` are numbers, `skipped_panels` a list of panel numbers; since October 2026 the
run's log counts them too and names no file or folder that is not published (an unreadable folder by the folder
above it and its Drive address, a failed file by its folder and file id). There is no reminder for the Tracker's
service panels (the `expenses-panel` one is gone since October 2026): the Tracker works them out itself
(`servicePanels` in `src/assets/js/expenses-core.js`), and `panels:` in `config/expenses.yml` only overrides one.
`updated` of `announcements.json`, `events.json`, `whatsnew.json`, `spotlight.json` and `writers_archive.json` (and
of `shop`, `meetings`, `audio_project`, `quote` before their source first worked) means "when this file's content
last changed" since October 2026 (`build_data.stamped`): a build that changes nothing else in it keeps the last
build's value. `status.json` `generated` / `updated` still mark every build, so a data commit still happens every
run.
`feeds` is kept apart from `sources` on purpose: the /status/ page explains each feed in plain words
("Other calendars we read"), and the Actions run summary lists them as information only, so a feed that
a site's bot protection blocks never counts as failed and never opens the "A content source has stopped
updating" issue.
`pending` > 0 means the translation time budget ran out; the rest is translated on the next run.
`rejected_by_guard` counts sentences whose machine translation was refused (repeated words,
more than 2.5× longer, changed numbers, HTML entities) — those keep their original text.

`quote_days` is shown on /status/ (eleventy/filters/freshness.js `fsQuoteMornings`: the line under "Daily
quote" — naming the magazine whose quote has not come in yet, when only one has — and the last 7 mornings in
the technical details). "Came in" is when the update first READ the quote, not the deploy time; the Morning
check's run summary has that. Days before the first recorded `seen` are left out (the list fills up over its
first week), and so is a day whose quote is in the history without a time (an entry written before the times
were kept): /status/ never shows an invented time. `full_update` goes into /build.json `full` (below). Only a
full update moves it: in quick and morning runs `run_all` calls `build_data --keep-full-update`, which keeps the
value of the `status.json` it replaces (`kept_full_update`; a first build or an unreadable file → the computed
value). A push may also run a source only the full update reads (`run_all --quick --also …`: its own input
changed), and that source's fresh `attempted` must not make the Morning check believe the full update ran.

### /build.json — a note about the build (a site output, not a data file)
Written by `src/pages/build-info.11ty.js` with every build; read only by the Morning check
(`.github/workflows/morning.yml` first job, and `scripts/ops/morning_check.py`):
```json
{ "v": 1, "built": "2026-09-29T09:33:41Z",   // the build's time (UTC; the footer's "Last updated")
  "day": "2026-09-29",                       // that time's day in site.timezone (Central)
  "tz": "America/Chicago",
  "quotes": { "gv": "2026-09-29", "lv": "2026-09-29" },   // the day of each quote in data/site/quote.json
  "data": "2026-09-29T09:33:10Z",            // status.json `generated` (when build_data last ran), or null
  "full": "2026-09-28T18:17:20Z",            // status.json `full_update` (when the last full update ran), or null
  "run": "36480000000",                      // GITHUB_RUN_ID of the run that built it ("" locally)
  "version": "c3f09a1b2d", "commit": "9b44e62" }          // src/_data/build.js
```
"Today's update is on the site" = `day` and both `quotes` are today (Central). The full daily update is due
when `full` is before midnight on the 1st of the month (Central) or more than 30 hours old; the Morning check
then starts one. Not linked, and not in the collections, sitemap or search. Nothing in it is new (/status/
shows the same facts). update.yml warns and check.yml fails when it is missing.

### The monthly toolkit (`/monthly/`) — no data file of its own
`eleventy/filters/monthly.js` builds one model per month at build time (America/Chicago): this month + the
next 12 (`monthlyPages` → `/monthly/YYYY-MM/` × en/es; `mpMonths` / `mpMonth` filters) from `db.editorial`
(themes, both magazines' story deadlines, La Viña's suggested topics), `db.articles` (`issues` and the stories themselves),
`config/carry.yml` (the 10 ways, the "put it to work" tips), `db.events` (+ the committee meeting from
`site.meeting` and recurring dates from `site.recurring_events` for months past `events.json`), `db.weekly_open`
and `db.shop.botm`. The hub (`/monthly/`) is the canonical home of the 10 ways; each month page of that month's
toolkit and poster (PNG 1080 × 1350, share, print on one Letter page). The 12 months before this one
(`PAST_MONTHS`) keep small redirect pages to `/monthly/` (`monthlyPastPages`, `src/pages/monthly-past.njk`), so a
printed poster's QR code never lands on a 404. `MONTHLY_NOW=2026-12-15` (or an instant, `2026-10-22T06:00:00Z`)
fixes "now" for testing; since October 2026 it also moves the committee meeting dates in the month calendar files
(`/monthly/YYYY-MM/…ics`: `committee.js` `meetingDates(cfg, back, ahead, now)`, the months counted in Central time,
as `meeting.py` `upcoming_rule_dates` does — before, a preview far from today dropped the meeting from those files).
The presentation decks' meeting rows (`presentations.js` `meetingInfo`) still use the real clock. A month page built
with `POSTER_SHARE=1` (Website update) names `share.png?v=<8 hex>` beside it as its `og:image` / `twitter:image`
(1200 × 630, alt "The {month} poster of the Grapevine & La Viña committee, NETA 65 — Carry the message", i18n
`monthly.share_alt`); the version is a hash of the poster's HTML and the code version (`shareVersioned`), and
`scripts/ops/poster_share.py` makes the picture. Without the flag the page keeps the committee's card.

* **The plan and what is live now.** Every month page shows that month's plan (the poster, the issues' themes,
  the tips, deadlines, dates, weekly open meetings, Book of the Month) and the same month as a message for a group
  chat or an e-mail; the current month's page and the hub's "This month" card also show what is live now. The
  Monthly digest (below) recaps LAST month; everything current lives here — as a link when another page is its one
  home (the Zoom details on `/meetings/#committee-meeting`, prices on `/shop/`, how to send a story on
  `/contribute/`, the quote on the home page). An issue's highlight stories are the digest's; the toolkit shows the
  themes and the story counts and links to `/read/`.
* **Dates** (`mpMonth(...).dates`): every event in `events.json` that is not `gone` and overlaps the month —
  content/events, dated Drive flyers and the outside calendars (the NETA 65 workshop feed: source `calendar`) —,
  the month's committee meeting (its record, else the `site.meeting` rule) and the recurring series. Each row has
  `overAt` (an ISO instant: a timed event's end — without one, one hour after it starts —, an all-day or date-only
  event's midnight Central after its last day), `past` (`overAt` ≤ now), `href` (`/meetings/#committee-meeting` for
  the committee, else the event's own page or `/events/`), `external` and `category`. Deadlines and Book of the
  Month offers have an `overAt` too (midnight Central after their day). The browser marks a date "Over" when its
  `overAt` passes (`src/assets/js/monthly.js`, `data-mp-over`).
* **The issues' names** (`issueTheme(db, pub, key, lang)`): the theme the issue itself carries (`issues[]`:
  `i18n.theme`, else `theme`); else the theme its stories carry (the first story's `i18n.issue_theme` /
  `extra.issue_theme` — so a month keeps its theme after `issues[]` has moved on to the next issue); else the
  magazine's own call for stories in `db.editorial` for that `issue_key` (Grapevine's editorial calendar, La Viña's
  yearly themes). La Viña's bimonthly issue of a month (`lv`: `{ key, theme, themeLang, label, url, cover }`) is the
  `issues[]` entry whose key is the month or the one before, else — once `issues[]` has moved on — the issue its
  stories belong to (official page from `extra.issue_url`, no cover), else — an issue not out yet — the one La Viña's
  yearly themes name for those keys (no page, no cover); its `label` is the site's one name for a La Viña issue, from
  its key (read.js `issueName`: "September–October 2026" / "Septiembre–Octubre 2026", as /contribute/, Home, the
  report, the digest and the slides write it). `themeLang`: the language its theme is in ("es" on an English page
  while a theme has no English words).
* **Story deadlines**: `deadlines` (Grapevine's, from the 1st of the month through the 1st of the next, not past) and
  `lvDeadlines` (La Viña's dated themes in the same days: `{ id, pub, theme` — its own Spanish words —, `themeLang`
  "es", `gloss` (its English words on an English page, when they differ), `glossMachine`, `issueKey`, `issueLabel`
  ("May–June 2027" / "mayo–junio de 2027", as /contribute/ writes the same deadline), `due`, `dueLabel`, `dueLong`,
  `overAt }`): the month page's two "Share your story" cards, the hub's chips (the page language's magazine first), the
  poster (La Viña's on the Spanish one), the calendar's marks and the message ("Oct 17 — “Recaídas” (La Viña, in
  Spanish, May–June 2027 issue)").
* `mpNow(db, site, lang)` → the current month's live extras (`monthNow`): `nextCommittee` (this month's meeting,
  then next month's once it is over: `{ ymd, day, dayLabel, time, zone, platform, overAt, thisMonth }`), `outNext`
  (an issue already online before its month: `articles.issues` newer than this month's Grapevine key / than the La
  Viña issue covering the month, with the link to that month's toolkit when it is in the window), `quote` (the home
  page shows a quote: one of the last 2 days with its text and link), `instagram` (the handles), `news` (What's New
  entries since the 1st), `bulletin` (`{ n, top }`: the posts not over yet, and the newest of them by its day — its
  date, or its `publish` day when later; never simply the first on /bulletin/, where pinned posts come first),
  `subsFrom` (the lowest subscription price), `gvm` (`{ inArea, nearby }` Grapevine meetings) and `audio` (the
  phone story lines).
* `mpIssues(key, db, carry, site, lang)` → the month's issues with stories on the site (`monthIssueLinks`):
  `{ pub, name, label, theme, url, count, free, readHref }` — `readHref` is `/read/#<pub>-current` while it is the
  newest issue of its magazine on /read/ (`read.js` `groupIssues`), else `/read/#archive-title`.
* `mpMessage(key, db, carry, site, langs, style)` → the month as a text (`monthMessage`): `langs` `[lang]` or
  `[lang, other]`, `style` `whatsapp` (`*bold*` headings with an emoji, "•") or `email` (UPPERCASE headings, "-",
  no emoji). The current month leaves out what is over and adds the next committee meeting, the Grapevine
  meetings count and the subscription price. The month page writes all four texts into the page (the previews,
  the Copy buttons); the language choice is kept in the browser as `localStorage["gv-digest-bi"]` — the digest's.

### The monthly digest (`/digest/` + the monthly e-mail) — no data file of its own
`eleventy/filters/community.js` (`buildMonthlyDigest`, the page and its WhatsApp / e-mail texts) and
`scripts/notify/send_digest.py` (the e-mail; the same rules, compared by `tests/test_digest_parity.py`) recap ONE
calendar month P (America/Chicago) — the edition is named after it ("September 2026 digest" / "Resumen de
septiembre de 2026"), is on `/digest/` from the first build on the 1st of the next month K all through K, and the
e-mail goes out once, early in K. Everything is read from the FULL files (never `whatsnew.json`, which keeps only
its newest 150 entries), a day being its Central calendar day:

| file | in the digest | which items |
|---|---|---|
| `announcements.json` | the bulletin's posts | not `gone`; counted on the day it was added to the site: `first_seen` (its `date` instead when that is the same Central day, for its time, or when there is no `first_seen`), never before its `extra.publish` day — the `date` is only the post's label: a post dated in an earlier month but added later (written on the 28th, saved on the 2nd, after that month's e-mail) is in the edition of the month it appeared, as a committee upload is (below), and so is one dated AHEAD (a notice dated with its event's day, saved weeks before — by that month it has usually expired; What's New dates it on `first_seen` too, `build_data.effective_ts`): every post is in exactly one edition. That day in P and not after now + 1 day; not expired (`extra.expires` before today). Pinned first, then newest; the page's row shows that day |
| `articles.json` | "New in the magazines" (grouped by issue) and the story count | `kind` article, not `gone`, with a `url` and `extra.issue_key`; counted in the month it came out online: `extra.pub_date` in P (so the September digest features the October Grapevine, online since September 23). A story without a `pub_date` (build_data could not work it out) counts on its issue's earliest `pub_date` — never on `first_seen`, so the stories the site found at its launch never all land in one edition. Per issue: the stories of P, all its stories (`total`), the free ones, `current` (the newest issue of its magazine on /read/ — a `gone` story does not count, as on /read/), the theme (`issueTheme`, above) and a few highlights (free to read first, then members' stories — never the writers' stories below) |
| `spotlight.json` | writers from Area 65 & Texas | `extra.pub_date` in P, `extra.geo.scope` `neta65` / `texas` |
| `episodes.json`, `videos.json`, `pdfs.json` | podcasts, videos, documents | `date` in P and not after now + 1 day (undated: never); a podcast episode's YouTube upload is folded into it |
| `instagram.json` | Instagram (the magazines' accounts) and the post count | not `gone`, `date` in P and not after now + 1 day. Per account (`extra.account`, else `category`; Grapevine, La Viña, then any other; the page language's magazine first): how many posts, and the 3 newest (their title — the caption's first line — and day, linking to the post). ONE link to the site's `/instagram/` page, their home; the WhatsApp / e-mail texts and the e-mail's text part give only each account's count and that link. The file keeps the newest `sources.instagram.keep_per_account` (130) posts of each account — about 65 days at the accounts' ~2 posts a day (September 2026), so P's count holds all through K; only a much busier month could lose its oldest posts late in K |
| `drive.json` | the committee's uploads | counted on the LATER of `date` (the date the file's name starts with, else when the photo was taken or the file created — drive.py) and `first_seen` (the day the site first had it): a report named "2026-08-11 …" but added on September 25 is in the September digest, a photo taken on the 30th but uploaded on the 2nd in the next month's — every upload is in exactly one edition, the one of the month it was added. That day in P and not after now + 1 day; not a bulletin document and not a dated flyer (`extra.event_date`: an event). A file's row shows its own `date` (the one in its name). Photos and videos of an album (committee.js `isPhotoItem`) are ONE entry per album for the month: `{ id: "album:<key>", _count, _when: the newest photo's day, url: "/photos/#<album>" }` (the e-mail links `/photos/`) |
| `events.json` | the events that took place | not `gone`, any category but `committee`, starting in P (an event over several days: the month it starts in) and started by now; plus P's committee meeting — its record (`ev:committee:<P>-…`), else the `site.meeting` rule (`skip_dates` honoured) — once it has started. Listed with their days only; never counted as news (events alone never send an e-mail). `events.json` keeps the newest 12 past one-off events, so a very busy month loses its oldest |
| `whatsnew.json` | the page's "N more updates since the 1st" pointer only | `wn_date` from the 1st of K |
| `status.json` | the e-mail's wait | `sources[].attempted` of `announcements`, `manual_events`, `drive`, `articles`, `pdfs`, `youtube`, `podcasts`, `instagram`: the e-mail waits (exit 3) while one was last tried before P ended but within the 3 days before — later ones are there, older ones have stopped |

Not in the digest (current or upcoming — the toolkit's): the next committee meeting (its Zoom details stay on
`/meetings/#committee-meeting`, which the toolkit links to), events not over
yet, the weekly open meetings, story deadlines, La Viña's topics, the phone lines, Book of the Month, the
subscription price, the daily quote, the Instagram accounts to follow (the digest has P's posts). The page and
the texts end with ONE pointer: "Coming up in K" → `/monthly/K/`. Counts (the intro, `COUNT_ORDER`): magazine
stories, podcast episodes, videos, Instagram posts, documents, committee files, photo albums, bulletin posts.
`MONTHLY_NOW=2026-10-01T15:05:00Z` builds the September digest; `send_digest --month 2026-09` is the same
edition.

### The district report (`/monthly/#report`) — no data file of its own
`eleventy/filters/report.js` (`rpModel`) writes the current month's report in English AND Spanish as 12 sections
`{id, title, text}` (plain text; a line starting with "•" is a list item): `header` (blanks `[##]`, name, role,
home group), `committee` (`meeting.next`, `site.meeting`), `issues` (the month model: GV theme, LV issue, the
`config/carry.yml` tips, a newer issue already out), `deadlines` (next 3 Grapevine deadlines in `db.editorial`, the
next 2 of La Viña's yearly themes — its Spanish words, the English ones after them —, La Viña's rotating topics,
`db.audio_project` phone lines), `shop` (`db.shop` Book of the Month and the lowest U.S.
subscription prices, Carry the Message), `events` (`upcomingEvents`: the next 45 days, a monthly series once),
`writers` (`db.spotlight`, Area 65, 60 days), `meetings` (`gvMeetings`; plus `meetings.options`: one option per
county of our Area and per nearby region, with its lines, for the county picker), `weekly` (`db.weekly_open`),
`resources` (`db.pdfs` of the last 45 days, `site.links` GVR/RLV sign-up, contact), `asks`, `notes` (empty). The page
embeds it as JSON (`rpJson`); `src/assets/js/report.js` is the editor; without JavaScript `rpText` shows it as text.
Kept per visitor only (optional): `localStorage["gv-report:YYYY-MM:en|es"]` = the changes to that month's report
`{ order, off, text, titles, custom, meet }` (only what differs from the data; drafts older than 3 months are
removed), `["gv-report:profile"]` = `{ district, name, role, group }`, `["gv-report:lang"]` = the report language.

### GVR / RLV 101 (`/orientation/`) — `config/orientation.yml`
Hand-written lessons for new GVRs / RLVs, loaded by `src/_data/orientation.js` as `orientation`
(`panel`, `lessons[]`, `pages` → `/orientation/<id>/` × en/es, `totalMinutes`, `totalChecks`). Each lesson:
`id` (the page address — keep it), `icon`, `minutes`, `example` (`issue` · `meeting` · `tip` · `botm` ·
`deadline` · `poster`: which live example `src/_includes/macros/orientation.njk` builds from `db.*`, `carry` and
`meeting` — nothing in the file itself goes stale), `title` / `summary` / `goal` / `try` / `discuss` `{en, es}`,
`points[]` `{title, text}`, `links[]` (`href` a page of this site · `link` a `site.links` key · `url`, with
`pub: gv|lv` for the La Viña-first order on `/es/`) and `check[]` (3 questions × 3 options, `answer` 1–3, `why`).
Placeholders `{rule_lc}` `{time}` `{panel}` `{panel_start}` are filled from `site.meeting` and `panel`. The build
fails on a missing language or a malformed question (`I18N_STRICT=1`); `tests/test_orientation.py` checks the
same plus lengths and wording. Filters: `eleventy/filters/orientation.js` (`o101Text`, `o101Vars`, `o101Links`,
`o101Deck` — the slide plan). The search index lists each lesson (`eleventy/filters/library.js`). The only thing
kept per visitor is `localStorage["gv-orientation-v1"]` = `{ v: 1, done: [lesson ids] }` (optional).

## 4. Template helpers (Eleventy filters)

* `{{ "nav.home" | t(lang) }}` — UI string from `src/_i18n/*.json`
* `{{ item | tx("title", lang) }}` — item field in the page language (falls back to original)
* `{{ item.date | fmtDate(lang, "long") }}` — `short` / `long` / `month` / `iso` / `relative` / `time`
* `{{ "/library/" | lurl(lang) }}` — language-prefixed URL (`/es/library/` for Spanish)
* `{{ page.url | altLangUrl(lang) }}` — the same page in the other language
* `{{ items | where("kind", "pdf") }}`, `| whereNot("status", "gone")`, `| limit(6)`, `| groupBy("category")` (the
  list helpers left since October 2026: `where`, `whereNot`, `limit`, `offset`, `groupBy`, `pluck`, `uniq`, `keys`,
  `length` — dates and "upcoming" are each area's own filter's work, `eleventy/filters/*.js`)
* `{% icon "calendar", "size-5" %}` — inline Lucide SVG icon

## 5. Extended fields (as built)

Scanned from the real `data/raw/*.json` and `data/site/*.json` (2026-09-23). "→ i18n" = the
field also gets `i18n.<name> = {en, es}` in the site file.

### Raw envelope extras (besides `source updated attempted ok error held changes stats items first_harvest`)

| raw file | extra top-level keys |
|---|---|
| `articles.json` | `issues` {"gv:2026-10": {`publication`, `key`, `label`, `theme`, `description`, `url`, `image`, `cover` (local WebP; `articles.py` also writes a 128 px JPEG copy next to it for the monthly e-mail), `hub`, `seen`}} — only issues seen as the CURRENT issue on a magazine hub; `detail_state` (module bookkeeping: retry state; `byline_at` = the article page was read and has no author/place, do not ask again); `archive_state` (below) |
| `writers_archive.json` | `parser_version`, `files` {gv/lv: {`name`, `name_date`, `sha256` (of the text with LF line ends, no BOM — the same on the owner's PC and in git), `rows`, `texas_rows`, `first_year`, `imported_at`}} — §2 *writers_archive.json* |
| `podcasts.json` | `shows` [{`key`, `name`, `title`, `feed`, `description`, `image`, `language`, `web`, `apple`, `spotify`, `amazon`, `episodes`}], `discovery` (weekly feed discovery) |
| `youtube.json` | `playlists` [{`id`, `title`, `lang` (en/es/und), `count`, `channel_id`, `url`}], `backfilled_at`, `detail_fails` {video id: per-video detail failures — 3 → not asked again; a bot check, captcha, rate limit or time-out is not counted}, `channel_ids` |
| `instagram.json` | `profiles` {gv/lv: {`username`, `name`, `full_name`, `url`, `followers`, `posts`, `owner_id`, `checked`, `avatar`}}; `removal` {shortcode: {`checked`, `missing`}} — the removal sweep's marks (since October 2026: a post no longer listed is looked up again; two "not there" answers ≥ 12 h apart remove it with its picture — an answer counts only when an embed of a post of the same account and kind, post or Reel, worked after it in that run); `stats.removal` {`checked`, `missing` [ ], `removed` [ ]} |
| `pdfs.json` | `crawl` {`known_pages`, `crawled_pages`, `pdfs`, `last_run_pages`}; `hub_problems` [{`url`, `status`, `since`}] (since October 2026; always written, `[]` when all is well) — the hub / kit pages (`HUB_PATHS` order) asked for this run that gave no readable page: `status` an HTTP code (404, 410, 503 …) or a word (`"no-response"`, `"login"`, `"offsite"`, `"not-html"`, `"robots"`, `"too many redirects"`, `"read: <ExceptionName>"`), `since` the UTC start of the failing streak (a 304 or a page reused from the run's memo counts as fine); crawler counters are in `stats`, with `stats.pruned_pages` (pages forgotten this run) and, when there are problems, `stats.warnings` ("N main page(s) of the magazine sites did not load: aagrapevine.org/gvr-resources (404 since 2026-10-06) — checked again every day"; "robots.txt of www.aagrapevine.org did not answer properly (HTTP 503): its pages were left for the next run"); a run in which that kept every due page unread is not ok (`crawl.run_verdict`, since October 2026): `ok: false` with "no page could be read: robots.txt of www.aagrapevine.org (HTTP 503) did not answer properly — site down?" (or the older "no page could be fetched (N errors) — site down?"), so `updated` keeps the last success; a paused search (`minutes_per_run: 0`) writes `hub_problems: []` with its fresh `attempted` (§1) |
| `drive.json` | `empty_folders` {folder id: since} (since October 2026): folders (or the root) that listed empty although they held files — their files are kept (`held`, `drop: false`) until the next run finds the folder empty again (then they go: `changes.confirmed`) or lists them again |
| `events_external.json` | `cache`, `sitemap` (module bookkeeping — not used by the site) |
| `meetings.json` | `feeds` [{`id`, `name`, `url`, `lang`, `ok`, `count`, `method` (feed/page), `key_from` (secret/config/key_source — never the key), `error` (a bot check since October 2026: "<host> answered with a bot check (HTTP 202) — nothing is wrong on our side; the last good list is kept", the office's previous meetings kept; a robots.txt that answered 5xx / 429 or nothing: "<host>'s robots.txt could not be checked (HTTP 503) — nothing was read; the last good list is kept" (or "(no answer)"; `RobotsUnavailable`), while "… robots.txt does not allow reading <path>" means only that its rules really refuse the page; `stats.warnings` prefixes the office's name), `note`, `updated`, `attempted`}], `type_labels` {code: {en, es}}. `extra.end_time` may be earlier than `time` when the meeting runs past midnight and lasts at most 3 h (`MEETING_OVERNIGHT_HOURS`; `23:00`–`00:30`); a longer one is dropped as before. Items: `mtg:<hash>` (kind `meeting`, `title` = name, `url` = the meeting's page; `extra` = `day`, `time`, `end_time`, `location`, `address`, `street`, `zip`, `city`, `county`, `state`, `lat`, `lng`, `approximate`, `region`, `district`, `types`, `attendance`, `in_area`, `sources`) |
| `quote.json` | `history` {gv/lv: [{`pub`, `lang`, `date`, `heading`, `text`, `attribution`, `source`, `source_lang`, `url`, `signup_url`, `seen` (the UTC time that day's quote was first read; kept on later reads; null in an entry written before these times were kept — it never gets one)}]} — the last 14 days, newest first, one per day (raw only: the guard against a page going back to an older quote, and the times behind `status.json` → `quote_days`; never shown as such). Since October 2026 a heading's date is taken only inside `heading_window` (365 days back to tomorrow, Central); an entry or item dated after tomorrow is dropped, and `stats.warnings` says what happened ("gv: dropped the stored quote of …", "… is already known — kept the newer", "… — over 14 days old …"). Items: `quote:<pub>:<date>` (kind `quote`, `title` = the official heading, `url` = the page anchor; `extra` = `pub`, `text`, `attribution`, `source`, `source_lang`, `signup_url`, `date_label`, `date_from_heading`, `block` (teaser/embed/anchor), `node`) |
| `shop.json` | `bulk_discounts` {`source_url`, `tiers`, `note` {en?, es?}}, `types` {gv/lv: {print/digital/complete: {`text`, `lang`, `url`}}}, `listings` [{`pub`, `region`, `url`}], `types_checked` (ISO; type descriptions are re-read every 30 days), `specialty_checked` (ISO; specialty pages are re-read every 7 days), `price_memory` {effective day: {`sub:…` item id: price, `botm:<pub>:<sku>`: regular price}} — for each announced price change (`config/site.yml` price_changes), the 1-year prices it affects (and, when it changes the book prices, each Book of the Month's regular price, by its book) as the reads BEFORE its day found them: each read until the day before updates the prices it found — a plan or book it did not find keeps its last price, and changes on the same day share one memory —, frozen from the day on (with the clock after the reads, so a run that started before midnight never files a later price as "before"); build_data compares later reads with it (`scripts/sync/price_changes.py` `remember` / `resolve` / `book_stale`); the memory of a change no longer in the settings is kept 400 days after its day (a typo that makes the block unreadable never loses it), then dropped. Items: `botm:gv` / `botm:lv` (kind `botm`; `extra` = `pub`, `page_url`, `price`, `sale_price`, `discount_pct`, `currency`, `sku`, `starts`, `ends`, `month`, `month_label`, `offer_text`, `product_name`, `image_src`, `read` (the day these prices were read, Central; an offer kept from an earlier read keeps its day)), `sub:<pub>:<region>:<sku>` (kind `subscription`; `extra` = `pub`, `region`, `listing_url`, `type`, `term_months`, `price`, `currency`, `sku`, `volume`, `position`, `image_src`) and `special:<pub>:<sku>` (kind `specialty`, `summary` = the short description; `extra` = `pub`, `type` (cards / planner / calendar / holiday / other), `price`, `currency`, `sku`, `volume`, `trilingual`, `pack`, `page_url`, `position`, `image_src`, `missing_since` (a seasonal item the stores no longer show, YYYY-MM-DD)). `stats.specialty_out_of_season` lists those ids on every run |

`articles.json` → `archive_state` — the archive listings (aagrapevine.org/archive, aalavina.org/archivo):
```json
{ "gv": { "backfilled": "2026-09-23T23:31:00Z",   // first full walk back finished (absent until then)
          "backfill_days": 120,                    // how far back it went (--backfill-days)
          "resume_page": 14,                        // only while an interrupted backfill is pending
          "backfill_stopped_at": 40,                // only when the backfill was given up (see below)
          "last_run": "…", "pages_last_run": 1, "new_last_run": 0,
          "oldest_seen": "2026-05",                 // oldest issue on the pages read last run
          "error": "page 0: no answer" },           // only when the last run had a problem
  "lv": { … } }
```
A daily run after the backfill reads page 0 and stops at the first page whose stories are all known.
Delete `archive_state` (or raise `--backfill-days`) to walk back again.
Safety stops for a site whose page links break: a page that still offers "Next" but lists only stories
already read earlier in the same run ends the walk (`error` "page N repeats stories of earlier pages
(pager broken?)", and the source shows as failing on /status/); an unfinished backfill that would have to
resume deeper than 6 pages per month of `--backfill-days` (at least 2 × `--archive-pages`; 40 for 120
days) is given up: it is marked `backfilled`, with `backfill_stopped_at` and an `error`, so it stops
costing requests.

`detail_state` holds only records whose article page still has something to tell. A Grapevine
"Online Exclusive" page prints no section, so for it title + paywall flag (`free`) count as complete and
it is read once.

### Site file top-level keys

| site file | key | shape |
|---|---|---|
| `instagram.json` | `profiles` | {gv: {username, name, full_name, url, followers, posts, owner_id, checked, avatar}, lv: {…}} — config order; names are brands (no i18n) |
| `videos.json` | `playlists` | [{id, title, lang (en/es — `und` is detected), count, channel_id, url, `i18n.title`, `machine`}] in the channel's order |
| `episodes.json` | `shows` | [{key, name, title, feed, description (plain text), image, language, web, apple, spotify, amazon, episodes, lang, `i18n.title`, `i18n.description`, `machine`}] in config order |
| `articles.json` | `issues` | [{id "gv:2026-10", publication, key, label, theme, description, url, image, cover, hub, lang, `i18n.theme`, `i18n.description`, `i18n.label`, `machine`}] newest `key` first. `i18n.label` is written by rules: GV monthly "October 2026" / "Octubre 2026"; LV bimonthly (odd key month) "September / October 2026" / "Septiembre / Octubre 2026" |
| `whatsnew.json` | (per item) `wn_date` | the news date used for sorting (ISO UTC) |
| `booth.json` | `collections`, `problems` | [{id, label, count}] · [{file, problem, problem_es, code}] — its own item shape, §3 *booth.json* |
| `writers_archive.json` | `files`, `since`, `counts` | the archive files in use · each file's first year · stories per scope (neta65 / texas) and magazine — its own item shape, §3 *writers_archive.json* |

### Item `extra` fields per kind (site files carry the same `extra` as raw)

| kind (file) | extra fields | extra i18n |
|---|---|---|
| episode (`episodes`) | `audio_url`, `audio_type`, `audio_bytes`, `duration_sec`, `season`, `episode`, `episode_type`, `show`, `show_name`, `show_web`, `link`, `player_url`, `apple`, `spotify`, `amazon` | — |
| video (`videos`) | `video_id`, `channel_id`, `duration_sec`, `playlists` [names], `is_short`, `views`, `is_live_recording`, `date_approx`, `season`, `episode` (podcast videos only) | — |
| post (`instagram`) | `shortcode`, `account`, `username`, `media_type`, `thumb`, `embed_url`, `permalink`, `is_reel`, `manual`, `strategy`, `caption_known`, `embed_checked` | — |
| article (`articles`, `spotlight`) | `publication`, `issue_key`, `issue_label`, `issue_date` (cover date), `issue_theme`, `issue_url`, `topic`, `section`, `author`, `author_location`, `subtitle`, `teaser`, `free`, `online_exclusive`, `department` (bool); written by build_data: `geo`, `pub_date` (below) | `section`, `topic`, `issue_theme` (machine); `issue_label`, `author_location` (rules — from `geo.label_en/label_es`, only when a place is known) |
| pdf (`pdfs`) | `host`, `file_url`, `filename`, `size_bytes`, `pages`, `thumb`, `referrers` [{url, title}], `upload_month`, `link_texts`, `event_date`, `doc_lang`, `multilingual` (`true` when one file holds several languages — two or more page languages, language-only links for 2+ languages, or a heading such as "Catalog • Catálogo • Catalogue"; otherwise `null`: such a file takes the host site's language and gets no "(Spanish)" title suffix), `section` (heading on the referring page), `external`, `orphan`; after the Library rules (§3 *pdfs.json*): `duplicates` (other addresses of the same file), `kits` (every rep kit it is in), `versions` (language editions), `same_file` | `versions[].i18n_title` |
| topic (`editorial`) | `publication`, `theme`, `evergreen`, and for dated themes `issue_key`, `issue_label`, `deadline`, `due_text`, `pdf_url`; Grapevine's also `submit_url`, `guidelines_url`; La Viña's (its yearly themes document — `pdf_url` and the item's `url`) also `submit_email` | `issue_label` (rules: La Viña's bimonthly from its two months); `theme` when it differs from the title |
| meeting (`weekly_open`) | `zoom_id`, `zoom_url`, `passcode`, `day`, `time`, `time_central`, `sentence`, `weekday`, `start_local`, `timezone`, `next_start`, `url`, `player_url`; La Viña item (`weekly_open_lv`, §2): no `sentence`/`player_url`, plus `starts`, `source_note`, `own_i18n` | written by rules from weekday/start_local/timezone: `day` ("Wednesdays"/"Miércoles"), `time` ("Noon Eastern"/"mediodía (hora del Este)"), `time_central` ("11:00 AM Central"/"11:00 a. m. (hora del Centro)"), `when` ("Wednesdays at 11:00 AM Central"/"Los miércoles a las 11:00 a. m. (hora del Centro)" — capitalized for a line of its own; a sentence lower-cases the first letter), `sentence` (join line with Zoom ID + passcode). Machine-translated only if those fields are missing |
| event (`events`) | common: `start`, `end`, `all_day`, `location`, `online_url`, `flyer_url`, `flyer_thumb`, `city`, `state`, `past`; `tentative` (`true` only: details to be confirmed), `location_tba` (`true` only: the place is not known yet — "Venue to be announced"; decided by the item's own `location`, by `location_es` / `location_en` only when there is no `location`). Committee: `meeting_id`, `passcode`, `recurring`. Recurring (category `recurring`, below): `recurring` (`true`), `series`, `rule`, `recurrence_label`, `host` (`neta` / `lv` / `gv`), `online` (it has an `online_url`), `platform` ("Zoom" …, else `null`), `meeting_id` (else `null`), `contact` (an e-mail address, else `null`). External calendar: `platform`, `online`, `scope`, `site`, `country`, `website`, `organizer`, `date_text`; a listing of a month a series skips also `series_of` (the series key), `host`, `online_url`, `meeting_id`, `contact`, `flyer_url`, `flyer_thumb` (from the series — build_data.series_moved_dates). Drive flyer: `drive_id`, `is_pdf`, `is_image`; a dated flyer of a recurring series on another day of the month also `host`, `online_url`, `online`, `platform`, `meeting_id`, `contact` (from the series). Manual: `body_md`, `slug`, `file`, `own_i18n`; `flyer_url` = the file's `flyer:` (a Drive copy, `https://drive.google.com/file/d/<id>/view`: the pages take its picture from the Drive by its id — committee.js `normalizeEvents` — so `flyer_thumb` stays null unless the file gives `image:`); `host` (`lv` / `gv` only: a file's `host:`), `meeting_id` (a file's `meeting_id:`); `also_in_feed` (the key of an .ics feed that lists the same event — also on a flyer, committee or recurring event) + `feed_match` (`url` / `online` / `title`); `also_on_calendar` (`lv-calendar` / `gv-calendar`: Grapevine's or La Viña's own calendar lists the same event — also on a flyer, committee or recurring event) + `calendar_match` (`url` / `online` / `title`). `host` on any event: `lv` / `gv` = La Viña's or Grapevine's own event that the committee shares — the pages show it with the Grapevine / La Viña calendars, in that magazine's colour (not to be confused with a document's `host`, a website). .ics feed (category `neta65` / `ics` / `gv-calendar` / `lv-calendar`, source `calendar`): `feed` (the feed's key), `uid` | committee meetings and recurring events (and a listing taken into a series: `series_of`): fixed human `title`/`summary` in both languages; recurring: `recurrence_label` (rules); manual: `body_md` (+ the file's own `title_es` / `summary_es`, never machine-translated); `location` (the file's `location_es` / `location_en`, or the site's own words for a place not known yet — never machine-translated) |
| document / slides / photo / video_file / form (`drive`) | `file_id`, `mime`, `name`, `panel`, `panel_label`, `path`, `album`, `view_url`, `preview_url`, `download_url`, `thumb_url`, `image_url`, `is_image`, `is_video`, `is_pdf`, `file_type`, `folder_id`, `folder_url`, `folder_chain`, `modified_text`, `size_bytes`, `duration_sec`, `shortcut_id`, `generic_name`, flyers: `event_date`, `event_end_date` (since October 2026: the last day when the name gives a range of days — "Assembly March 14 - 16, 2027", "2027-03-19 - 2027-03-21 …", "Asamblea del 14 al 16 de mayo de 2027"; `events.json` `extra.end` is then that day, or that day's end time when the name gives one), `event_title`, `event_time`, `event_end_time`, `event_location`, `event_tz` (the IANA zone when the name gives one — "12 p. m. (hora del Este)"; else the time is Central) / `event_month` (camera / WhatsApp / screenshot names are no event; a month and year with no day — "March 2027", "marzo de 2027" — gives only `event_month`, while a Spanish first written "1° / 1º / 1.º / 1ro / primero de marzo de 2027" is a whole date), forms: `form_closed`, `form_signin_required`; raw only — the booth folder's files (category `booth`, never in a site item list): `booth`, `modified`, a message's `body_md` (§3 *booth.json*) | `album` (photos in a sub-folder) |
| announcement (`announcements`: the bulletin's posts) | `body_md`, `expires`, `publish`, `pinned`, `slug`, `file` (`content/bulletin/<name>.md`), `link`, `own_i18n` | `body_md` (+ the file's own `title_es` / `summary_es`) |

#### Recurring events (category `recurring`; build_data.recurring_events)
One item per date of each `recurring_events:` entry in `config/site.yml` — the next `months_ahead` (default 6;
/events/ and the calendar feed list only these — the /monthly/ posters work out later months from the same rule,
`site.recurring_events`, so the booth is on every month's poster without 13 cards on /events/)
dates plus the dates of the last 90 days (those have `extra.past: true`; the pages never list them, the
calendar feed keeps them for subscribers):
```json
{ "id": "ev:recurring:citywide-dallas:2026-10-10",      // key + local date: stable (calendar UID, card anchor)
  "source": "committee", "kind": "event", "category": "recurring",
  "url": "https://citywidedallasaa.org",                // the entry's `url`, or "/events/" without one
  "title": "GV/LV booth at CityWide Dallas", "lang": "en", "date": "2026-10-10T22:00:00Z",
  "first_seen": null, "tags": ["recurring"],
  "extra": { "start": "2026-10-10T22:00:00Z",           // 17:00 CDT; "2026-11-14T23:00:00Z" = 17:00 CST
             "end": "2026-10-11T01:00:00Z", "all_day": false,
             "location": "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220",
             "city": "Dallas", "state": "TX",              // read from the location (or the entry's city/state)
             "online_url": null, "flyer_url": null, "flyer_thumb": null,
             "recurring": true, "series": "citywide-dallas",
             "rule": {"week_of_month": 2, "weekday": "saturday", "start": "17:00", "end": "20:00"},
             "recurrence_label": "Every second Saturday of the month · 5:00 – 8:00 PM",
             "host": "neta", "online": false, "platform": null, "meeting_id": null, "contact": null, "past": false },
  "i18n": { "title": {"en": "GV/LV booth at CityWide Dallas", "es": "Mesa de GV/LV en CityWide Dallas"},
            "summary": {"en": "…", "es": "…"},
            "recurrence_label": {"en": "Every second Saturday of the month · 5:00 – 8:00 PM",
                                 "es": "Cada segundo sábado del mes · 5:00–8:00 p. m."} },   // thin spaces around " – ", no-break in "p. m."
  "machine": [], "is_new": false }
```
* `title`/`summary` are the committee's own words (`title_es`, `summary_es`); a language left out is
  machine-translated and listed in `machine`. `recurrence_label` is written by rule, never translated,
  with the committee meeting's words (src/_i18n/committee.json `committee.rule` / `committee.ord.*`: "Every
  third Wednesday of the month"). `rule` is the entry's rule in the shape of `meeting:` (the end as used:
  a missing one is start + 1 hour); the web pages build the line from it with the meeting's own helpers
  (committee.js `recurrenceText`: same words, the browser's clock format) and fall back to `recurrence_label`
  — either way with the time zone added ("… 5:00 – 8:00 PM Central time" / "… 5:00–8:00 p. m., hora del
  Centro"): the line goes into the calendars' description, beside a start a calendar shows in its reader's zone.
* Never `is_new`, never in `whatsnew.json`, never in the /events/ "Past events" list (so the calendar files,
  which keep a past date 90 days, link it to its `url`, else to /events/ itself — never to its card, which is
  gone). Home and search show only the next date of each `series`; the monthly digest lists the date that
  took place.
* La Viña's monthly workshop (`lv-monthly-workshop`) — an event La Viña holds, online only — differs only in:
  ```json
  "url": "/events/",                                     // no page of its own on aalavina.org
  "extra": { "location": null, "city": null, "state": null,
             "online_url": "https://us06web.zoom.us/j/81595931777", "online": true, "platform": "Zoom",
             "meeting_id": "815 9593 1777", "contact": "lveditorial@aagrapevine.org", "host": "lv",
             "flyer_url": "https://drive.google.com/file/d/<id>/view",              // flyer_match: the newest
             "flyer_thumb": "https://lh3.googleusercontent.com/d/<id>=w600", … }   //   matching Drive file
  ```
  `flyer_url` / `flyer_thumb`: the date's own Drive flyer (a name starting with that date), else its month's,
  else the newest undated one matching the entry's `flyer_match` (build_data.series_flyers / pick_flyer);
  `null` when none matches.
* Entries with a mistake are skipped; `status.json` → `problems.recurring_events` says which and why — and also
  which date to add to `skip_dates` when an outside calendar lists the series (the same online room) on
  another day of a month whose rule date is still to come and is not listed itself (build_data.series_listing_notes).
* A month the rule skips is left to the host's calendar: its listing there (the same online room, one day) is
  that month's date of the series (build_data.series_moved_dates) — still the calendar's event (its id, `url`,
  category `lv-calendar`, `all_day`), with the series' `title` / `summary` / `lang` / `machine` and fixed
  `i18n.title` / `i18n.summary`, and `extra.series_of` (the series key), `host`, `online`, `online_url`,
  `platform`, `meeting_id`, `contact`, `flyer_url` / `flyer_thumb` (the date's flyer) filled from the series.

#### Events from several places; several days (`events.json`)
* **Several days.** An all-day event's `extra.start` / `extra.end` are dates and `end` is the LAST day
  (content/events `start: 2027-03-19`, `end: 2027-03-21`; an .ics feed's exclusive `DTEND;VALUE=DATE:20270322`
  is turned into `2027-03-21`). Its end counts from 23:59 Central on its last day (`event_end_ts`), and like
  every event it keeps `past: false` for one more day after that (`build_events` cutoff = now − 24 h: an
  assembly ending Sunday Mar 21 is `past: true` from 23:59 on Monday Mar 22). The pages do not wait for
  that: they hide it at midnight after its last day (`chicagoDayEndMs`). The pages show a date range; the
  calendar feeds write `DTSTART;VALUE=DATE:20270319` + `DTEND;VALUE=DATE:20270322`.
* **When an event is over** — the same instant on every page, so none disagrees between builds
  (`eleventy/filters/committee.js` `eventSpan` / `eventEndMs`): `/events/` and `/meetings/` (the card's
  `past` and `data-cm-expire`, the calendars' end), the home page (`homeEventEnd` → `data-gv-expire`), the
  monthly toolkit (`overAt` → `data-mp-over`) and the district report (`upcomingEvents`). An all-day or
  date-only event: midnight Central after its last day (an `end` given as an instant: its Central day, or the
  day before when it is exactly midnight). A timed event: its `end` (a date as its end: midnight after that
  day). A timed event without an end — or with one that cannot be read or is not after its start — lasts one
  hour (`EVENT_NO_END_MS`: the hour the calendars give it, and what `meeting:` and `recurring_events:`
  assume — except, since October 2026, an end earlier than the start and at most 12 hours later, which the
  sync reads as the next morning, `meeting.overnight`); its card shows the start time alone.
* **Outside calendars** (`sources.ics_feeds`): one item per VEVENT (RRULE expanded without the dates EXDATE deletes or a RECURRENCE-ID VEVENT moves or cancels; UNTIL in any form; CANCELLED left out), id
  `ev:ics:<hash of UID + start>`, `source: "calendar"`, `category` = the feed's `category:` (`neta65` or `ics`
  → shown with the NETA 65 events; `gv-calendar` / `lv-calendar` → with the GV/LV calendars), `url` = the
  VEVENT's `URL`, `extra.flyer_url` / `flyer_thumb` = its `ATTACH` (an image), `tags` = its `CATEGORIES`,
  `extra.tentative` = `STATUS:TENTATIVE`, `extra.location` without ", United States". The last good copy of
  each feed and its last answer are in `data/state/ics_feeds.json`
  (`{url: {"fetched": last success, "ics": text, "attempted", "state", "http_status", "error"}}`).
* **One real event, one item.** A feed event — or an event of Grapevine's / La Viña's own calendar
  (`events_external`: build_data.merge_calendar_duplicates; nothing is copied from it, the kept event gets
  `extra.also_on_calendar` / `calendar_match`) — that is the same event as one already on the calendar — a
  content/events file, a dated Drive flyer, the committee meeting or a `recurring_events:` date — is left
  out. Both must **start the same local day**, and then either link the same event page (URL compared
  without scheme, `www.`, trailing slash, `?query`, `#fragment` — `neta65.org/event/<slug>`), or meet in the
  same **online room** (build_data.online_room: the Zoom meeting ID whatever the server, path form or
  passcode — `zoom:81595931777` —, a Google Meet code, else the link's host + path; an `extra.meeting_id` of
  9–12 digits counts as a Zoom room) — unless both give a time more than 2 hours apart, or one runs over several
  days and the other does not; a listing that gives only the day counts only against a date of a monthly series
  or the host's own event (`host` `lv` / `gv`: La Viña's all-day "Taller Mensual" is the workshop's date of that
  day, but our workshop at a one-day virtual assembly, in the assembly's Zoom room, is not the assembly) —, or have
  the same shape (both all-day, or both timed and starting at most 2 hours apart; never one over several days
  against one on a single day — a file without `end` may take the feed's), not two different cities, and
  titles that name the same event (`similar_titles`: the words that tell events apart — the kind of event
  included, "workshop", "booth", "assembly" — shared at least 75 %, the shared city and the year ignored;
  word for word when a city is not known). So a workshop or a booth *at* an assembly, on its first day, is
  a separate event. The same event page on another date is another date (a series, a page used again,
  or a date that changed): the feed event is kept. The hand-written item wins and keeps its `own_i18n`;
  the feed only fills what it leaves out — `flyer_url`, `flyer_thumb`, `online_url` and the event-page
  `url` (when the file has none) only on a sure match (the same page, the same online room, or the same start;
  `flyer_thumb` only together with the feed's `flyer_url`: a file's own `flyer:` — a Drive copy, its picture
  taken from the Drive by committee.js `normalizeEvents` — never gets the feed's picture of another copy); a missing
  `location`; a `location` that is "to be announced" (on a sure match: the feed's venue replaces it and
  a TBA `location_es` is dropped); a missing `end` of the same kind — and the item is named in
  `extra.also_in_feed` / `extra.feed_match` (`url` / `online` / `title`). Nothing is copied onto the committee meeting
  or a recurring date. Where the feed says something the file does not — its event page on another date
  (for an upcoming file), another start time, a venue the file still calls "to be announced" —
  `status.json` `feeds[].notes` says so, for the chair to update the file. The same event in two feeds is
  kept once.

#### Articles: `extra.geo` and `extra.pub_date` (site files only; build_data.py)
`extra.geo` = where the writer is from, read from `extra.author_location` by `scripts/sync/geo.py`:
```json
"geo": { "scope": "neta65",                         // neta65 | texas | other | unknown
         "city": "Grand Prairie",                   // as the writer gave it (tidied), or null
         "county": "Dallas",                        // principal county, or null (unknown / not Texas)
         "counties": ["Dallas", "Ellis", "Tarrant"],// every Texas county the place lies in ([] outside Texas)
         "state": "TX",                             // US/Canada postal code, Mexican state name, or null
         "country": "US",                           // ISO code, or null when unknown
         "label_en": "Grand Prairie, Texas",        // display label (null when no place)
         "label_es": "Grand Prairie, Texas" }       // ("Nueva Jersey" / "New Jersey", "Condado de Houston, Texas" …)
```
* `neta65` — the place lies in an Area 65 county (`config/site.yml` `spotlight.neta65_counties`); a place
  in several counties counts if ANY of them is in Area 65. Cities are matched to counties with
  `data/geo/texas_places.json` (U.S. Census 2020 place-by-county table; see `data/geo/README.md`).
* `texas` — elsewhere in Texas, or "Texas" with no usable city. `other` — anywhere else, including a bare
  city name without a state that is not on geo.py's short list of unambiguous Texas cities ("Paris"
  alone is Paris, France; "Dallas" alone is Dallas, Texas). `unknown` — no place given (or a note printed
  where the place goes, e.g. a reprint's "Excerpt. Original title: …, August 1948").
* "Houston, Texas" is Harris County (`texas`); only "Houston County, Texas" is Area 65.
* A region counts only when it stands alone: "West Texas" / "West TX" is the region (`texas`), "West,
  Texas" is the town of West (McLennan County, `neta65`); "Panhandle, Texas" is the town of Panhandle.
  The compass regions (North, Northeast, East, West, South, Central, Southeast, Southwest, Northwest Texas —
  `geo.TEXAS_REGIONS`; North and Northeast Texas are `neta65`) are also read as adjectives: "Southeastern Texas"
  (also "Southeastern, Texas") is Southeast Texas, label "Southeast Texas" / "Sureste de Texas", no city — never a
  town "Southeastern". Any other "city" made only of compass words ("Deep East", "Far West") is shown as printed —
  "Deep East Texas", `texas`, no city or county.
* Also read as Texas: "Denton (Texas)", "Dallas, Texas USA", "Fort Worth, TX, 76102", "Tyler, Texas,
  District 42", "Texarkana, TX-AR"; words around the place are left out ("near Tyler", "Tyler area",
  "cerca de Tyler", "somewhere in East Texas" → East Texas); "N. Richland Hills", "De Soto", "Mc Kinney",
  "North Dallas", "Hurst-Euless-Bedford", Dallas / Fort Worth neighborhoods ("Oak Cliff" → Dallas County)
  and Spanish town names ("Palestina" → Palestine, English label "Palestine, Texas") are matched to
  their county. The list of rules is in the docstring of `scripts/sync/geo.py`.
* Mexican state abbreviations are written out ("Guadalajara, Jal." → Jalisco). "N.L.", "B.C.", "Mich."
  and "Col." are Mexican states in La Viña bylines (Nuevo León, Baja California, Michoacán, Colima)
  unless the country or a well-known city says otherwise ("Vancouver, B.C."); in Grapevine bylines they
  are Newfoundland and Labrador, British Columbia, Michigan, Colorado unless the country or city says
  otherwise ("Tijuana, B.C."). `label_en` is written in English only for a Spanish town name; otherwise
  both labels keep the writer's spelling of the city.

`extra.pub_date` (`YYYY-MM-DD`) = the day the story counts as published for the 60/90-day windows and the
monthly digest (the issues and writers of the month it covers): the EARLIER of the first day of its issue (La Viña's bimonthly issues: the first month) and
the day the story was first seen online (`first_seen`, in America/Chicago) — never later than today. It
does not move: an October issue seen online on September 16 counts from September 16, also after
October 1 (so the digest lists it once); a back-catalog story found by the archive backfill counts
from its issue's first day (its `first_seen` is the later backfill day).

### Crawler state — `data/state/crawl-state.json`
Written only by `scripts/sync/crawl.py` (never edit it by hand; deleting it starts the crawl over).
Top level: `version`, `updated`, `sitemaps` {url: {`fetched`, `status`}}, `runs` (last runs' counters),
`pages` {url: page record}, `pdfs` {normalized url: PDF record}. `data/raw/pdfs.json` is rebuilt from it
on every run. A PDF record:

| field | meaning |
|---|---|
| `url`, `first_seen`, `last_seen_on_page`, `refs` [{`url`, `title`, `section`, `texts`, `alts`, `seen`}], `external` | where the file is and which pages link it |
| `status` | `ok` · `gone` (left out of the site files) · `not-pdf` (the link turned out to be a web page) |
| `gone_strike_at` | the FIRST failing check (404/410, or an HTML page where the file was). The PDF only becomes `gone` when a second check at least 24 h later fails too (`GONE_CONFIRM_H`); a good answer clears it |
| `gone_since` | when it became `gone`. A gone PDF that a page still links is checked again every 7 days during its first 60 days as gone, then every 30 days (`GONE_RECHECK_DAYS`); a good answer brings it back (`status: ok`, both fields removed) |
| `vanished_at` / `recheck` | no page links it any more (→ one check: deleted?) / a gone PDF is linked again (→ check: back?) |
| `hint`, `fresh` | the link is not a `*.pdf` address (the check must confirm it is a PDF) / it appeared on a page crawled before, so `first_seen` ≈ its publish date |
| `head` | last check: `status`, `size`, `type`, `last_modified`, `final_url`, `checked_at`; `error: "robots"` + `next_try` (30 days) when robots.txt forbids the file (since October 2026: the last known size and date kept, never a strike, never gone); after an error or HTML answer (404/410, 5xx, a web page where the file was) `size` and `last_modified` stay the file's last known ones, so an error page never re-dates the PDF; after no answer at all also `error: "unreachable"`, `fails`, `next_try` (2, 4, 8 … ≤ 60 days) and `unreachable_since` (first of those failures) — since October 2026 only after the host was asked twice; while a host is down for the run its other PDFs are re-queued with no record (`pdfs_requeued`). A PDF on another site (`external`) whose host has not answered for 30+ days after 4+ tries becomes `gone` (`UNREACHABLE_GONE`); files on the two magazine sites never do |
| `details` | from the one-time download: `checked_at`, `title` (PDF metadata; the author is never read), `pages`, `chars`, `text_lang`, `page_langs` (language of each of the first 2 pages: `en`/`es`/`fr`, or `null` when a page has < 200 characters of text or no clear language — two different languages make the file `multilingual`), `heading` (a title-like line from the top of page 1), `thumb`; on failure `error`, `final` (do not retry), `attempts`, `next_try`. Since October 2026 the file is read in a child process (`crawl_pdf.analyze_pdf_isolated`, 60 s, 2 GB on Linux) and the attempt is written first (`error: "parse: interrupted"`, kept only if the run died while reading); other errors: `"robots"`, `"parse: no result after N s"`, `"parse: crashed (out of memory)"`, `"parse: crashed (exit code N)"`, `"parse: no result"` — each retried after 2, 4, 8, 16, then 30 days |

A page record (`pages` {url: …}) — since October 2026 also: `gone_strike_at` (the first 404/410 of a page that
answered 200 before: its PDF links are kept until a second 404/410 at least 24 h later, `GONE_CONFIRM_H`, and the
page is checked again the next day), `error_since` (UTC start of the current streak of answers that were not a
readable page — 5xx, no answer, a 404 strike or a confirmed 404/410/400, login, offsite, not-html, robots),
`last_error` (now for all of those, not only 5xx), `linked_at` (gone pages only: when a crawled page last linked it,
refreshed at most weekly); a 200 or 304 clears them. A hub or kit page is due every day whatever it answered (a
failing one after `HUB_RETRY_H` = 12 h). `prune()` forgets, at the start of every crawl run, pages the crawl rules
reject (junk addresses) and pages gone (404/410/400) for `PRUNE_GONE_DAYS` = 90 (counted from `error_since`, else
`crawled_at`) that are not in the sitemap and have no newer `linked_at`; hubs, sitemap pages and working pages
never. `runs[]` entries may carry `pruned_junk`, `pruned_gone`, `parse_failed`, `pdfs_requeued` and
`robots_unavailable`. A PDF's site date is the Central-time day of its `Last-Modified` (or, for a fresh file, of
`first_seen`) — a file uploaded on the evening of the 31st into that month's folder is dated the 31st.

### Push bookkeeping — `data/state/sources-seen.json`
Since October 2026: `{"commit": "<sha>", "by": "push" | "full update", "recorded": "<UTC time>"}` — the last
commit the sources that only the full update reads (`FULL_ONLY`) ran with. Written only by *Website update*
(`python -m scripts.ops.push_modules --record <sha> --by …`, after a sync step that ended well) and carried by the
data commit; a push run compares its files from that commit (`push_modules`, see docs/OPERATIONS.md *Push to
`main`*), so a push whose own run GitHub replaced in the queue is not forgotten. Never edit it by hand; a missing
or unknown commit only means a push counts its own changes.

### Translation rules that affect what you see
* Brand names are never translated (glossary `keep`: Grapevine, La Viña, Dear Grapevine, AA Grapevine,
  GVR, RLV, NETA 65, Grapevine Weekly Open …).
* Written by rules, not by the model: "[Season 11, Episode 12]" ⇄ "[Temporada 11, Episodio 12]"
  (typos such as "[Seaon 3. Episdode 1]" are normalized in the original title too), dates
  ("July 22, 2026" ⇄ "22 de julio de 2026"), prices, ordinals ("13th" → "13.º", "9th Step" → "Noveno Paso"),
  clock times ("7 PM" → "7 p. m."). Hashtag walls (3+ hashtags) are removed from teasers.
* A machine translation that repeats words, grows > 2.5×, changes/loses a number or contains an
  HTML entity is rejected; that sentence keeps its original text (counted in `status.translations.rejected_by_guard`).
