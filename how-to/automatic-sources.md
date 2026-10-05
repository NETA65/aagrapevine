# Automatic sources: what the site reads by itself

Part of the [how-to guide](README.md). This page covers everything the site reads **without anyone
uploading it**: the magazines' stories and documents, podcasts, YouTube, Instagram, the stores, the
daily quotes, the editorial themes, the weekly open meetings, the record-your-story phone lines and the
intergroups' meeting lists. It also covers three things the site works out from your settings: the
committee meeting, announced price changes, and where a magazine writer is from — and, briefly, the Texas
writers archive, which joins two exports of the magazines' online archives with the stories the site captures
([3.16](#316-the-texas-writers-archive-contentarchive)).

Files you put on Google Drive are a different subject: see [The Drive panel folder](drive-panel-folder.md).

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start](#2-quick-start)
3. [Full reference, source by source](#3-full-reference-source-by-source)
   - [3.0 All sources at a glance](#30-all-sources-at-a-glance)
   - [3.1 Magazine stories and issues](#31-magazine-stories-and-issues)
   - [3.2 Where a writer is from (the spotlight)](#32-where-a-writer-is-from-the-spotlight)
   - [3.3 The Document Library (the crawler)](#33-the-document-library-the-crawler)
   - [3.4 Podcasts](#34-podcasts)
   - [3.5 YouTube videos](#35-youtube-videos)
   - [3.6 Instagram posts, and posts you add by hand](#36-instagram-posts-and-posts-you-add-by-hand)
   - [3.7 Shop: Book of the Month, prices, specialty items](#37-shop-book-of-the-month-prices-specialty-items)
   - [3.8 Announce new prices](#38-announce-new-prices)
   - [3.9 Daily quotes](#39-daily-quotes)
   - [3.10 Editorial themes and deadlines](#310-editorial-themes-and-deadlines)
   - [3.11 Weekly open meetings](#311-weekly-open-meetings)
   - [3.12 Record your story by phone](#312-record-your-story-by-phone)
   - [3.13 Grapevine meetings from the intergroup lists](#313-grapevine-meetings-from-the-intergroup-lists)
   - [3.14 The committee meeting](#314-the-committee-meeting)
   - [3.15 GV/LV event calendars](#315-gvlv-event-calendars)
   - [3.16 The Texas writers archive (content/archive)](#316-the-texas-writers-archive-contentarchive)
4. [What happens next (which run, how long)](#4-what-happens-next-which-run-how-long)
5. [Where it shows on the website](#5-where-it-shows-on-the-website)
6. [Going further: change the code](#6-going-further-change-the-code)
7. [Troubleshooting](#7-troubleshooting)
8. [Good practice and AA principles](#8-good-practice-and-aa-principles)
9. [See also](#9-see-also)

> **Addresses in this guide are written short.** `/read/` means
> `https://neta65.github.io/aagrapevine/read/`, and `/es/read/` is the same page in Spanish.

---

## 1. What this is

Every day a robot — the **Website update** workflow on GitHub Actions — reads the official
Grapevine and La Viña websites, their stores, the podcast feeds, YouTube, Instagram and eight
intergroup meeting lists. It saves what it found in the repository and rebuilds the website. Nobody
uploads anything for these sources.

Your part is small and optional: a few settings in [`config/site.yml`](../config/site.yml), a list of
extra Instagram posts in [`content/instagram.yml`](../content/instagram.yml), and fixes for machine
translations in [`data/translations/overrides.yml`](../data/translations/overrides.yml).

**Where it shows:** almost everywhere — Read, Library, Listen, Watch, Instagram, Shop, Share your story
(`/contribute/`), Meetings, Events, the home page, What's New and the RSS feed, the monthly toolkit, the
monthly digest e-mail, search, the booth display on the About page, and the health page `/status/`. Section
[5](#5-where-it-shows-on-the-website) has the full page-by-page list.

---

## 2. Quick start

Most days there is **nothing to do**. When you want to check or change something:

1. **Check that it works.** Open `/status/`. Each source has a row with a badge: **OK**, **Delayed**
   (it worked, but not in the last 3 days), **Failed** (the last try failed; everything found before
   stays on the site) or **Not run yet**.
2. **Find the source** in the table in [3.0](#30-all-sources-at-a-glance). It names the setting that
   controls it.
3. **Edit on GitHub.** Open the file on github.com, click the pencil, change the value, click
   **Commit changes**. The MKP715 GitHub login on the owner's PC can do this (it has write access).
   Only *secrets* and repository *settings* need the **NETA65** admin account.
4. **Wait for the right run.** Most changes show in 10–20 minutes: the quick run your save starts also runs
   the sources whose own settings you changed. Changes to the magazine stories, the shop and the document
   search wait for the next **full update** (it usually starts about 5–7 AM Central). The table in
   [4](#4-what-happens-next-which-run-how-long) says which. Don't want to wait? **Actions → Website update
   → Run workflow**, leave every box empty, click the green **Run workflow** (up to about an hour).
5. **A title is translated badly?** Add the exact original text and your translation to
   `data/translations/overrides.yml` (see [Translations](translations.md)). It shows after the quick
   rebuild that saving the file starts.

**Example — add an Instagram post the robot missed.** In `content/instagram.yml`, replace `posts: []` with:

```yaml
posts:
  - url: https://www.instagram.com/p/ABCdef12345/
    account: lv          # gv = AA Grapevine, lv = La Viña
```

What happens: saving the file starts a quick run that also reads Instagram, so a few minutes later the post is
on `/instagram/` and `/es/instagram/` (La Viña column). Its picture and caption come from the accounts' pages
when the post is among their newest; otherwise the next **full** update looks the post up and fills them in.
Details in [3.6](#36-instagram-posts-and-posts-you-add-by-hand).

---

## 3. Full reference, source by source

### 3.0 All sources at a glance

"Full" = only the full update reads it (every night) — and, for the sources marked "+ push", also the quick
run of a save that changed what that source reads (its settings, or `content/instagram.yml`). "Every run" =
also the quick rebuild after you save a file, the midday and evening refreshes and the morning refresh. Section
[4](#4-what-happens-next-which-run-how-long) explains the runs.

| Source (code) | What the robot reads | Your settings | Read in | Main pages | Row on `/status/` |
|---|---|---|---|---|---|
| Magazine stories (`articles.py`) | Each magazine's current-issue page, its archive, each story page once | `sources.grapevine.magazine_hub`, `sources.lavina.magazine_hub` | Full; morning of the 1st (current-issue pages only) | `/read/`, home, `/published/` | Grapevine & La Viña articles |
| Writer's place (`geo.py`) | Nothing online: the place in each byline | `spotlight:` | Every build | home *Published writers*, `/published/` | — |
| Document Library (`crawl.py`) | Both magazine sites page by page; every official document | `sources.crawler`, `library.official_hosts` | Full only, up to 40 minutes a day | `/library/`, `/shop/`, `/gvr/` | Document library |
| Podcasts (`podcasts.py`) | Each show's RSS feed | `sources.podcasts` | Every run | `/listen/`, home | Podcasts |
| YouTube (`youtube.py`) | The channel's feeds (no key) | `sources.youtube.channels`; `site.watch`, `site.listen`, `site.about_videos` | Full + push | `/watch/`, home, `/about/#videos` | YouTube |
| Instagram (`instagram.py`) | The two accounts' public embed pages (or the official API) + your list | `sources.instagram`, `content/instagram.yml` | Full + push | `/instagram/`, home | Instagram |
| Shop (`shop.py`) | Book of the Month pages, subscription listings, specialty items | `sources.<pub>.botm`, `subscriptions`, `subscription_regions`, `specialty`, `specialty_skip` | Full; morning of the 1st and 15th; specialty items weekly | `/shop/`, home teaser | Book of the Month, prices & specialty items |
| Price changes (`price_changes.py`) | Nothing online: your `price_changes:` block | `price_changes:` | Every build | `/shop/#price-changes` | — (mistakes show as a *Settings problem* in the run summary) |
| Daily quote (`quote.py`) | The two magazines' home pages | `sources.<pub>.quote_page`, `site.morning_goal` | Every run (in the morning refresh, right after Drive and the bulletin) | home quote card | Daily quote |
| Editorial themes (`editorial.py`) | Grapevine's editorial calendar, La Viña's suggested topics and yearly themes document | `sources.grapevine.contribute`, `sources.lavina.contribute`, `themes_page`, `themes_link` | Full + push | `/contribute/#deadlines`, home | Editorial themes & deadlines |
| Weekly open meetings (`weekly_open.py`) | Grapevine's Weekly Open page; La Viña's from your settings | `sources.grapevine.weekly_open`, `lavina_weekly_open:` | Full + push | `/meetings/#weekly-open` | Grapevine Weekly Open meeting |
| Record your story (`audio_project.py`) | Grapevine's audio portal, La Viña's *Graba tu historia* pages | `sources.grapevine.audio_project`, `sources.lavina.record_*` | Full + push | `/contribute/#record` | Record your story by phone (Grapevine & La Viña) |
| Grapevine meetings (`meetings.py`) | 8 intergroup / central office meeting lists | `meetings:` (and `spotlight.neta65_counties`, `data/geo/texas_places.json` for "our Area") | Full + push | `/meetings/#grapevine-meetings` | Grapevine meetings (our Area and nearby) |
| Committee meeting (`meeting.py`) | Nothing online: your `meeting:` block | `meeting:` | Every build | `/meetings/#committee-meeting`, home, `/events/` | — (a wrong skip date shows as a *Settings problem* in the run summary) |
| GV/LV event calendars (`events_external.py`) | The magazines' shared event calendar | — (only the sites' `base` addresses) | Full + push | `/events/` | GV/LV event calendars |
| Texas writers archive (`writers_archive.py`) | Nothing online: the two archive files in `content/archive/` | the files; `writers_archive.min_rows_ratio`; `spotlight.neta65_counties` | Every run | `/published/#archive`, home, search | Texas writers archive (content/archive) |

All code is in [`scripts/sync/`](../scripts/sync/). Each module's opening comment (its *docstring*) is
the detailed technical reference, and every module can be tried without writing its data file
(`data/raw/<source>.json`): `python -m scripts.sync.<name> --dry-run`. (A few modules, such as the shop
and the magazine stories, may still save new pictures under `src/assets/cache/` during a dry run.)

---

### 3.1 Magazine stories and issues

**What it reads** (politely: both sites ask for 5 seconds between requests).

- **The current-issue page** of each magazine: Grapevine `https://www.aagrapevine.org/magazine`
  (monthly) and La Viña `https://www.aalavina.org/la-revista` (every two months). From it: each
  story's title, byline ("By: Jake B. | Cheyenne, Wyoming"), the publisher's public teaser and card
  picture, and the issue's label, theme, blurb and cover. If that page shows no stories, the robot
  tries the home page (and `/revista-2` for La Viña).
- **The archive lists** (`/archive?page=N`, `/archivo?page=N`), back about 120 days, so the
  published-writers spotlight also has the issues before the current one.
- **Each story page once** (up to 40 a run): the issue / topic / section line, author, subtitle,
  whether the story is free to read or for subscribers, and an "Online Exclusive" mark. A missing
  detail is asked again at most 3 times, a week apart.
- It **never stores the story's text** (copyright): only the title, the publisher's teaser, the byline
  and the link back to the official page.

**Settings** in `config/site.yml`. No key or secret is needed.

```yaml
sources:
  grapevine:
    base: "https://www.aagrapevine.org"
    magazine_hub: "/magazine"        # the current-issue page
  lavina:
    base: "https://www.aalavina.org"
    magazine_hub: "/la-revista"
```

**How often.** The full daily update. On the 1st of the month the morning refresh also reads the two
current-issue pages (not the story pages, not the archive), so the new issue is on the site early; the
full run fills in the details later that day.

**A real story** (from `data/raw/articles.json`, October 2026):

| Field | Value |
|---|---|
| id | `gv:2026-10:standing-sunlight` (magazine : issue : the address's last part) |
| title | Standing in the Sunlight |
| summary (the editor's subtitle) | For everything—the good, the bad, the ugly—she is grateful |
| author · place | Meghan R. · Glenmont, N.Y. |
| issue | October 2026, theme "Loneliness" |
| free to read / online exclusive | no (a subscriber story) / yes |
| date | 2026-10-01 |

**How a byline is read** (checked with the module's own `parse_byline`):

| Byline on the magazine's page | Author | Place |
|---|---|---|
| `By: Jake B. \| Cheyenne, Wyoming` | Jake B. | Cheyenne, Wyoming |
| `Por: Victor R. \| Grand Prairie, Texas` | Victor R. | Grand Prairie, Texas |
| `By: Anonymous` | Anonymous | (none) |
| `By: Ann K. \| Tyler \| Texas` | Ann K. | Tyler, Texas |

**How a story's issue is found** from its address (`issue_from_url`):
`…/magazine/2026/oct/hand-hand` → Grapevine, October 2026;
`…/revista/septiembre-octubre-2026/la-llamada` → La Viña, issue key `2026-09`, shown as
"Septiembre / Octubre 2026"; a store address → no issue (not a story).

**Dates.** A story is dated the 1st of its issue month. Magazines go online *before* the cover month
(October is online in mid-September); while the issue date is still in the future, the story is dated
the day the robot first saw it.

**Where it shows**

- `/read/` · `/es/read/` — the current issue of each magazine and the archive (older issues load from
  `/read-archive.json`). La Viña comes first on the Spanish page.
- Home page — *From the magazines*: the latest issue of each, five stories each, plus "this month in
  the Shop".
- *Published writers* on the home page and `/published/` · `/es/published/` (see [3.2](#32-where-a-writer-is-from-the-spotlight)).
- The Texas writers archive, `/published/#archive`: every captured story by a writer from Texas, **of any age**.
  `data/raw/articles.json` keeps every story it ever found — nothing is removed by age; a story the magazine took
  down is only marked "gone" and left out of the pages — so each new Texas story joins the archive by itself,
  after the archive files' date ([3.16](#316-the-texas-writers-archive-contentarchive)).
- `/monthly/` (themes and story counts), the GV/LV report `/monthly/#report`, `/digest/` and the
  monthly e-mail.
- What's New `/whats-new/` and the RSS feeds `/feed.xml` · `/es/feed.xml` — new issues only. Older
  issues found only in the archive ("back catalog") are real stories on `/read/` but never "news".
- Search `/search/`: a story also matches its writer and hometown.
- A **New** badge for 14 days.

#### Change it, hide it

- **The magazine moved its current-issue page:** change `magazine_hub`. Write only the path, starting
  with `/` (for example `/magazine`): the code and the `/read/` page add it to `base`, so a full address
  here would make a broken link. If the magazine moves to another web address altogether, change `base`.
  It takes effect at the next full run.
- **A title or subtitle is badly translated:** add it to `data/translations/overrides.yml`, for example
  `"Standing in the Sunlight": { es: "De pie bajo la luz del sol" }`.
- **Hide one story:** there is no setting. It takes a small code change, see
  [6.2](#62-hide-one-item-everywhere).
- **Add a story by hand:** not possible; the list is exactly what the magazines publish.

**Code pointers.** [`scripts/sync/articles.py`](../scripts/sync/articles.py): `parse_hub` (the
current-issue cards), `parse_archive`, `parse_article` (a story page), `build_item` (the saved item and
its `extra` fields). Display: [`eleventy/filters/read.js`](../eleventy/filters/read.js) → `articleView`,
and [`src/pages/read.njk`](../src/pages/read.njk) → macro `articleRow`. Home:
`eleventy/filters/home.js` → `homeLatestIssue`. Tests: `tests/test_spotlight.py`,
`tests/test_sync_pipeline.py`.

---

### 3.2 Where a writer is from (the spotlight)

**What it does.** No internet. [`scripts/sync/geo.py`](../scripts/sync/geo.py) → `classify_location`
reads the place in each byline and decides its **scope**: `neta65` (in an Area 65 county), `texas`
(elsewhere in Texas), `other`, or `unknown` (no place given). Cities are matched to their counties with
`data/geo/texas_places.json` (the U.S. Census place-by-county table) and your county list. A city that
spans several counties counts as Area 65 when **any** of them is on the list.

**Settings:**

```yaml
spotlight:
  home_days: 60              # home page: stories of the last 60 days
  list_days: [60, 90]        # the choices on /published/ (the first is the default)
  default_scope: "neta65"    # /published/ opens on: neta65 | texas | all
  neta65_counties:           # the Area 65 counties (from the official NETA 65 district map)
    - Dallas
    - Tarrant
    - Smith
    # … the whole list is in config/site.yml
```

Odd values fall back quietly: a number of days outside 1–366 is ignored (60, and 60 / 90), and a
`default_scope` other than `neta65`, `texas` or `all` becomes `neta65`.

**Examples** (checked with `classify_location`):

| Place in the byline | Scope | Why |
|---|---|---|
| `Grand Prairie, Texas` | neta65 | Dallas, Ellis and Tarrant counties |
| `Rowlett, TX 75088` | neta65 | Dallas / Rockwall; the ZIP code is ignored |
| `Tyler area, Texas` | neta65 | "area" is dropped → Tyler, Smith County |
| `Oak Cliff, Texas` | neta65 | a known Dallas neighborhood |
| `West, TX` | neta65 | the town of West, McLennan County |
| `Houston County, Texas` | neta65 | read as the county, which is in Area 65 |
| `Houston, Texas` | texas | Harris County, not Area 65 |
| `Austin, Texas` | texas | Travis County |
| `West Texas` | texas | a region, not a town |
| `Southeastern Texas` | texas | the region Southeast Texas, also when written as an adjective (never a town "Southeastern"); other compass words in a town's place ("Deep East Texas") stay as printed, with no town |
| `Dallas` (no state) | neta65 | on the short list of unmistakable bare city names |
| `Paris` (no state) | other | a bare "Paris" is too likely to mean France — on purpose |
| `Cheyenne, Wyoming` / `Glenmont, N.Y.` | other | another state |
| `Monterrey, N.L.` (a La Viña byline) | other | Nuevo León, Mexico |
| (no place) | unknown | |

**Where it shows.** Home *Published writers* (Area 65 writers first, then the rest of Texas, last 60
days), `/published/` · `/es/published/` (60 or 90 days; Area 65 / Texas / everywhere), `/read/`,
`/contribute/`, `/digest/` and the monthly e-mail. The Texas writers archive below the recent stories reads the
same counties, for the places of its old bylines too (with a few extra rules for typos and small places,
`geo.classify_writer`: [Writers archive §7](writers-archive.md#7-how-area-65-is-decided)). The Meetings page uses
the same county list for its "Our Area" group ([3.13](#313-grapevine-meetings-from-the-intergroup-lists)).

#### Change it

- **Add or remove an Area 65 county:** edit `spotlight.neta65_counties`. The spotlight and the Texas writers
  archive follow at the quick rebuild after you save; that run also reads the meeting lists again, so the
  Meetings page's "Our Area" follows too.
- **A writer's city without a state is not recognized** (for example "Paris" or "Arlington"): that is
  deliberate. To add a bare city, edit `NETA65_BARE` (or `TEXAS_BARE`) in `geo.py` — read the module's
  opening comment first, it explains why each name was kept out.
- **A Dallas or Fort Worth neighborhood is not recognized:** add it to `NEIGHBORHOODS` in `geo.py`.

> Note: "In Every Issue" departments (Letter from the Editor, Dear Grapevine, Cartas del lector …) are
> never spotlight writers: they have no single writer.

**Code pointers.** `geo.py` → `classify_location`, `NETA65_BARE`, `TEXAS_BARE`, `NEIGHBORHOODS`;
`scripts/sync/build_data.py` → `enrich_articles`, `spotlight_settings`, `plan_spotlight`. Test:
`tests/test_spotlight.py`.

---

### 3.3 The Document Library (the crawler)

**What it reads.** [`scripts/sync/crawl.py`](../scripts/sync/crawl.py) walks www.aagrapevine.org and
www.aalavina.org page by page: 5 seconds between pages, robots.txt obeyed, in a 40-minute box each
day, and it carries on the next day where it stopped (`data/state/crawl-state.json`). Pages are taken
in this order: the daily "hub" pages (resource pages, home pages, news), pages never visited, pages the
sitemap says changed, new event pages, then pages not visited for `recheck_days`.

About 30 % of the time goes to documents: each new one is downloaded once for its page count, title,
language and a small picture of page 1. The robot never visits login, cart, search, paywalled story or
podcast pages, never reads a document's author metadata (anonymity), and records a document **only when
the file itself is on an official host**.

**Settings:**

```yaml
sources:
  crawler:
    hosts: ["www.aagrapevine.org", "www.aalavina.org"]    # see the note below
    user_agent: "NETA65-GrapevineCommitteeBot/2.0 (+https://github.com/NETA65/aagrapevine)"
    minutes_per_run: 40      # 0 = pause the document search (everything else keeps updating)
    recheck_days: 21         # look at a known page again after this many days
    pdf_details_per_run: 40  # new documents downloaded per run
    pdf_max_mb: 60           # bigger files are not downloaded (the monthly GV News is ~43 MB)
library:
  official_hosts:            # a document is kept only when its FILE is on one of these
    - aagrapevine.org
    - aalavina.org
    - aa.org
    - aaws.widen.net         # AA World Services' asset library
```

> Note: `sources.crawler.hosts` is **not** the list of sites the crawler visits — that list is in the
> code (`DRUPAL_HOSTS` in [`crawl_rules.py`](../scripts/sync/crawl_rules.py)). `hosts` is only used by
> the weekly podcast feed discovery. If the other keys are missing, the code uses 40 minutes,
> 25 documents, 21 days and 20 MB.

**Each document once.** Before the site files are written,
[`pdf_curate.py`](../scripts/sync/pdf_curate.py) keeps official hosts only, merges copies of one file,
drops older versions of the same document, and joins English / Spanish / French editions into one card
with language links. On October 2, 2026: 142 documents recorded → 92 Library entries, 20 of them with language
versions.

**How a document's title is chosen** (the first that works): an event link with a role ("Registration
form") → the link text (but never "Download", "Aquí", "1.2 MB" …) → the picture's alt text → the
document's own title (unless the file name is more specific) → the event's name → the linking page's
title → the heading on page 1 (only when the file name says little) → the tidied file name. An entry in
`TITLE_OVERRIDES` beats all of them.

| What the crawler sees (checked with `crawl_rules.py`) | Title |
|---|---|
| file `revSubscription-Order-Form_v52424.pdf`, nothing better | Subscription Order Form (upload month 2026-02, from the address) |
| file `GV_Catalog_2026-final%20(1).pdf` | GV Catalog 2026 final |
| link text `Download` / `Descargar aquí` / `1.2 MB` | rejected, the next rule is tried |
| link text `Download App Poster` | App Poster |
| link text `Learn How It Works Here` | How It Works |

**How its type is chosen.** A document on a kit page wins (`/gvr-resources` → GVR kit, La Viña's
`/recursos` → RLV kit). A document linked only from event pages is a **flyer**. Otherwise the first
matching row of the keyword table `DOC_TYPE_RULES` decides (postcard, order form, news, catalog,
workbook, guidelines, service, flyer, literature), else **other**.

| Found on / link text | Type |
|---|---|
| `/gvr-resources`, "GVR Handbook" | gvr (tag: service) |
| only `/get-involved/events/2026-10-03/roundup` | flyer (tag: event) |
| `/news-release` | news |
| `/catalog`, "2026 Catalog" | catalog |
| "Subscription Order Form" | order-form |
| nothing matching | other |
| a file on `www.aawv.org` (not an official host) | never recorded |

A real entry: **GV News October 2026** — 4 pages, 43 MB, found on the GVR Resources page, so it is in
the GVR kit, tagged *news*, with a page-1 picture in `src/assets/cache/pdf/`.

**How often.** Full daily update only (time-boxed). The first full pass finished in September 2026
(3,434 pages). Progress is on the **PDF crawl** line of each run summary, never on the public pages.

**Where it shows.** `/library/` · `/es/library/` (30 cards, the rest load from `/library-index.json`;
filters by source, type, language and year; collections: GVR kit, RLV kit, catalogs, flyers, news,
committee reports), the home page *Library* row (the 6 newest), `/shop/#catalogs` and the order forms,
`/gvr/`, the writer kit on `/contribute/`, `/monthly/`, the GV/LV report, What's New and the RSS feed
(dated documents only), `/digest/`, search. Visitors always read "document", never "PDF".

#### Change it, hide it

| You want to … | Do this | Takes effect |
|---|---|---|
| Pause the document search | `minutes_per_run: 0` | next full run |
| Catch up after a long pause | **Actions → Website update → Run workflow**, `crawl_minutes` = `300` — start it in the morning, it runs up to 6 hours | that run |
| Allow bigger files | raise `pdf_max_mb`; files skipped as "too large" are retried by themselves | next full run |
| Fix a document's Spanish (or English) title | `data/translations/overrides.yml`, e.g. `"GV News October 2026": { es: "GV News, octubre de 2026" }` (in October 2026 the machine gave "Noticias GV octubre de 2026") | quick rebuild after saving |
| Fix a wrong title in both languages | add `"<exact file name>": "<title>"` to `TITLE_OVERRIDES` in `crawl_rules.py` (code) | next full run |
| Hide every document of one site | remove that host from `library.official_hosts` | quick rebuild after saving |
| Hide one document | code change, see [6.2](#62-hide-one-item-everywhere) | next build |
| Check a page every day | add its path to `HUB_PATHS` in `crawl_rules.py` | next full run |
| Never visit a part of a site | add a pattern to `SKIP_PATH_PATTERNS` in `crawl_rules.py` | next full run |

A real `TITLE_OVERRIDES` line (the file name exactly as in the address, decoded):

```python
TITLE_OVERRIDES: dict[str, str] = {
    "GV__Survey_Letter.pdf": "Letter about the Grapevine and La Viña Apps Survey",
    # … add yours here
}
```

> Good to know: a document is called "gone" only after two failed checks at least 24 hours apart; a
> document no page links any more is kept but sorted last on `/library/`.

**Code pointers.** The tables at the top of `crawl_rules.py` (`HUB_PATHS`, `TITLE_OVERRIDES`,
`KIT_PAGES`, `SKIP_PATH_PATTERNS`, `GENERIC_LINK_TEXT`, `DOC_TYPE_RULES`) and its functions
`choose_title`, `classify`; `crawl.py` → `build_item`; `pdf_curate.py` → `official_only`, `curate`;
display `eleventy/filters/library.js` → `libraryDocs`. Tests: `tests/test_library_curation.py`,
`tests/test_crawl_media.py`, `tests/test_sync_pipeline.py`.

---

### 3.4 Podcasts

**What it reads.** Each show's public RSS feed. Once a week (in a full run) it also looks at
aagrapevine.org/podcasts and the La Viña home page for podcast feeds that are **not** in your settings.
It never adds them by itself: they are listed in the run summary under **New podcast feeds found**, with
the address ready to paste.

**Settings** — one block per show:

```yaml
sources:
  podcasts:
    - key: "gv"                      # short id: becomes the episode id (pod:gv:…) and its group
      name: "AA Grapevine's Podcast"
      feed: "https://feeds.captivate.fm/aa-grapevine/"
      apple: "https://podcasts.apple.com/us/podcast/aa-grapevines-podcast/id1591924167"
      spotify: "https://open.spotify.com/show/714djcL57SFf0Nzf40CL8Q"
      amazon: "https://music.amazon.com/podcasts/de231bfa-837b-4a27-a331-a927019cb5d7"
      web: "https://www.aagrapevine.org/podcasts"
    - key: "wo"
      name: "Grapevine Weekly Open AA Meeting"
      feed: "https://feeds.captivate.fm/grapevine-weekly-open/"
      web: "https://www.aagrapevine.org/grapevine-weekly-open"
```

| Key | Needed? | What it does |
|---|---|---|
| `key` | yes | a short id (letters); an entry without it is ignored |
| `feed` | yes | the show's RSS address; an entry without it is ignored |
| `name` | recommended | the show's name on the site (else the feed's own title) |
| `apple`, `spotify`, `amazon`, `web` | no | the show's links on `/listen/` (the weekly link check also tests `web`) |
| `lang` | no | `"es"` = a hint for the language guess (a Spanish show) |

**How often.** **Every run** — the full daily update, the midday and evening refreshes, the quick rebuild after you
save a file, and the morning refresh. A new show appears within minutes of saving.

**A real episode:** `pod:wo:7574d90d16ee` — "Grapevine Weekly Open AA Meeting, September 30, 2026
[Season 2, Episode 14]", 50 minutes, played from the show's own audio file, linked to its Captivate
page. Lengths are read in any common form: `1938`, `32:18` and `PT32M18S` are all 32 min 18 s;
`1:02:03` is 1 h 2 min 3 s.

**Where it shows.** `/listen/` · `/es/listen/` (one group per show, in your settings' order; the newest
24 episodes are on the page, the rest load from `/episodes-index.json`; one shared player). Home
*Listen & Watch*: the **featured** episode is the newest episode of the **first** show in your list if
it is no more than 30 days older than the newest episode overall, otherwise the newest episode; then 3
more, with every show represented. What's New and the RSS feed (with the audio attached), `/digest/` and
the monthly e-mail (Weekly Open episodes get their own label), search. The booth display (`/about/#booth`): the 6
newest episodes of AA Grapevine's podcast (never the Weekly Open recordings), played from the podcast's host only
while the booth's sound is on.

#### Add a show, feature a show, remove a show

**Add a show.** Copy a block, paste it under the last one and change the values. A made-up example:

```yaml
    - key: "lvp"
      name: "Podcast de La Viña"
      feed: "https://feeds.example.org/podcast-de-la-vina/"   # the show's real RSS address
      lang: "es"
```

What happens: at the quick rebuild after saving, `/listen/` gets a new group, the newest episode can
appear on the home page, and new episodes go to What's New and the feed.

**Feature a show on the home page:** put its block **first**. The order is also the order of the groups
on `/listen/`. It takes effect at the next run (any kind).

**Remove a show:** delete its block. No new episodes are read.

> Note: the episodes already collected **stay** on `/listen/` (the robot never deletes on a bad day,
> and the page shows a group for every show it has episodes of). To take them off as well, it takes a
> code change: see [6.2](#62-hide-one-item-everywhere), skipping by `category` (the show's key).

**Translations.** Episode titles and summaries are machine-translated. A tail like
"[Season 2, Episode 14]" is translated on its own (by rule), so an override for the title *without* its
tail still works — and it fixes that same title wherever it appears, for example on the episode's
YouTube copy too.

**Code pointers.** [`scripts/sync/podcasts.py`](../scripts/sync/podcasts.py) → `build_items` (each
episode and its `extra`), `show_meta`, `discover`; display
[`eleventy/filters/media.js`](../eleventy/filters/media.js) → `showList`, `epCompact`, and
`src/pages/listen.njk` → macro `epRow`; home `eleventy/filters/home.js` → `homeEpisodes`. Test:
`tests/test_sync_pipeline.py`.

---

### 3.5 YouTube videos

**What it reads** — no API key:

- Every full run: the channel's RSS feed, its automatic upload lists (long videos, Shorts, past live
  streams) and the feed of each public playlist — plus up to 60 single-video look-ups (exact date,
  length) with the free tool *yt-dlp*, in a 6-minute budget.
- Once a week: the complete video list with *yt-dlp*.
- A deleted or private video is confirmed only after a complete listing.
- YouTube often blocks *yt-dlp* from GitHub's computers. Then only the RSS feeds are read. That is a
  **Note** in the run summary, never a failure (on October 2, 2026: "details stopped: … Sign in to confirm you're
  not a bot").

**Settings:**

```yaml
sources:
  youtube:
    channels:
      - id: "UCI9uFLJ__aXT3-At0PlPWUQ"
        handle: "@AAGrapevine"
        name: "AA Grapevine & La Viña"
links:
  youtube_channel: "https://www.youtube.com/@AAGrapevine"   # the home page's "Subscribe on YouTube" button and "Watch on YouTube" on /watch/
```

> Note: the **Subscribe on YouTube** button in the `/watch/` header does not use `links.youtube_channel`:
> it is built from the first channel's `id` (`…/channel/<id>?sub_confirmation=1`).

An entry with only a `handle` is looked up once and remembered. If no channel can be used, the source
fails with "no YouTube channel configured/resolved".

**Language.** YouTube's own audio-language tag wins; else the playlists a video is in (Spanish
playlists, any title with "Viña"); else English — then the title and description are checked. A Spanish
video counts as La Viña's (`lv`), every other video as Grapevine's (`gv`). On October 2, 2026: 531 videos, 95 of them
Spanish, 18 Shorts, 31 playlists.

**How often.** The full daily update — and the quick run of a save that changed `sources.youtube` (it reads the
channels' feeds; the full listing of older videos waits for a full update).

**Where it shows.** `/watch/` · `/es/watch/`: the **featured** video at the top is always the newest
video that is not a Short; then the grid (24 on the page, the rest from `/videos-index.json`) with type
chips (Shorts, Weekly Open, Podcast, Video), language chips and playlists. Home *Listen & Watch*: 5 of
the newest non-Shorts, skipping YouTube copies of episodes already shown, with at least one La Viña
video from the last year. Also `/about/#videos`, `/accessibility/` (ASL videos), What's New and the RSS
feed, `/digest/`, search, and the booth display (`/about/#booth`: the `about_videos` first, then the newest 30
Shorts and videos of 8 minutes or less — never a Weekly Open meeting or a live recording; they need internet).

#### Pick the videos in the three hand-picked spots

These settings are read by the page templates, so they show at the **quick rebuild after you save**
(no daily run needed). The id is the last part of `youtube.com/watch?v=<id>` or `youtube.com/shorts/<id>`.

```yaml
site:
  watch:
    hero_video: "_mjB6hXYHn4"            # the card on the right of the /watch/ header
    hero_video_title: "Victor E. is back"
  listen:
    sidebar_short: "0uyVPlTcSeI"         # the card on the right of the /listen/ header
    sidebar_short_title: "Grapevine Get The App!"
  about_videos:                          # the cards on /about/#videos
    - id: "V3RzyHdgQCY"
      pub: gv
      title: "AA’s Twelfth Step Tools: Grapevine and La Viña"
      tr:
        title: "Herramientas de AA para el Paso Doce: Grapevine y La Viña"
        summary: "Una mirada a lo que son Grapevine y La Viña …"
    - id: "Bqb1FP0lx1E"
      pub: lv
```

| Spot | What it does |
|---|---|
| `site.watch.hero_video` (+ `hero_video_title`) | The video on the right of the `/watch/` header. Its title and summary come from the channel's list; a Short plays in a tall player with an "All Shorts" link, other videos get "All videos". Not in the list yet → `hero_video_title` and a "Watch on YouTube" link. **Hidden when it is the same video as the featured (newest) one.** Delete both lines to hide the card. In October 2026 `_mjB6hXYHn4` is a Short. |
| `site.listen.sidebar_short` (+ `sidebar_short_title`) | Always shown as a tall player beside the two app links (La Viña's link first on `/es/listen/`). The title is shown as written (default "AA Grapevine"). Delete the lines to hide it. |
| `site.about_videos` | One card each on `/about/#videos`. `id` (6–20 letters, digits, `-`, `_`) and `pub: gv` or `lv`. `title` replaces the channel's title (used for a title written in capitals). `tr` is **your own** translation for the other-language page; without it the machine translation is used and marked. An entry with no title from you or from the channel is skipped. The page language's magazine comes first. |

#### Change it, hide it, pin it

- **Pin a video at the top of the `/watch/` grid:** not possible. The featured video is always the
  newest non-Short (`mediaFeaturedVideo` in `media.js`). Use the hero spot instead.
- **Hide one video:** no setting; a code change, see [6.2](#62-hide-one-item-everywhere).
- **Add a second channel:** add another `- id:` / `handle:` / `name:` block under `channels`. The quick run of
  your save reads the channels' feeds (their newest videos); the full listing of its older videos comes with a
  full update.
- **Remove a channel:** delete its block. No new videos are read, but the videos already collected stay
  (nothing is deleted on a bad day); taking them off too is a code change, see [6.2](#62-hide-one-item-everywhere).
- **Fix a translated title or playlist name:** `overrides.yml` — a real line: `"Coming in": { es: "Llegando a AA" }   # YouTube playlist`.

**Code pointers.** [`scripts/sync/youtube.py`](../scripts/sync/youtube.py) → `build_item` (each video
and its `extra`; note that playlists and approximate dates are re-applied after the merge, see
[6.5](#65-add-a-brand-new-field-from-the-source)); display `eleventy/filters/media.js` (`videoKind`,
`videoCompact`, filter `mediaFeaturedVideo`), `src/pages/watch.njk`; `/about/` cards
`eleventy/filters/read.js` → `aboutVideos`. Tests: `tests/test_crawl_media.py`,
`tests/test_sync_pipeline.py`.

---

### 3.6 Instagram posts, and posts you add by hand

**What it reads.** For each account, the first way that returns posts wins:

1. Instagram's **official API** ("Business Discovery") — only when the two secrets below exist; the
   30 newest posts.
2. The account's **public embed page** (the small widget Instagram offers to websites) — about the 6
   newest posts. This is what works for both accounts (October 2026).
3. Instagram's web data address.
4. The public profile page — about 12 posts; also used to fill a gap when the 6 embed posts do not
   reach back to the newest post already known.
5. RSSHub mirrors, only if you list some.
6. A last-resort embed.

**Plus your list** in `content/instagram.yml`, always.

Posts that still lack a caption, a picture or a type are completed from their own public embed (up to
25 a run). The date comes from the post's code itself, with no request (the code `DXEcB00AFOo`, for
example, was made on 13 April 2026). The picture is saved at once as a small WebP in
`src/assets/cache/ig/`, because Instagram's own picture links expire.

**Settings:**

```yaml
sources:
  instagram:
    accounts:
      - key: "gv"
        username: "alcoholicsanonymous_gv"
        name: "AA Grapevine"
      - key: "lv"
        username: "alcoholicosanonimos_lv"
        name: "La Viña"
    anonymous: true          # false = only the official API + content/instagram.yml
    keep_per_account: 130    # newest posts kept per account (about 65 days)
    enrich_per_run: 25       # post look-ups per daily run
    graph_version: "v21.0"   # version of the official API
    rsshub_instances: []     # optional RSSHub mirrors to try
```

| Key | What it does |
|---|---|
| `accounts` | The two accounts. Their order is the column order on `/instagram/` (reversed on `/es/instagram/`, so La Viña comes first there). |
| `anonymous` | `true`: the robot may read Instagram's public pages. `false`: no visit to Instagram at all except the official API — with no token, only your list appears. (Setting `IG_ANONYMOUS=0` in the workflow does the same.) |
| `keep_per_account` | Older posts and their pictures are deleted. Keep at least ~62 days' worth: the monthly digest of a month stays on `/digest/` all through the next one. |
| `enrich_per_run` | How many single posts may be looked up per run. |
| `graph_version` | The official API's version (`IG_GRAPH_VERSION` in the workflow wins). |
| `rsshub_instances` | Public RSSHub mirrors to try; empty = skipped. |

**Secrets (optional): `IG_ACCESS_TOKEN` and `IG_BUSINESS_ID`.** They turn on the official API — the
most reliable way, and the one Instagram's terms allow. Adding a secret needs the **NETA65** admin
account (*Settings → Secrets and variables → Actions → New repository secret*). The one-time setup
(about 30 minutes, for someone comfortable with Meta's settings) is in README
[section 10 b](../README.md#b-instagram-token-the-official-way) and at the top of
[`scripts/sync/instagram.py`](../scripts/sync/instagram.py). The token is only ever sent to
graph.facebook.com and never written in the logs. An expired token shows as a Note even on a day the
embed page still worked.

**How often.** The full daily update (an 8-minute budget), your list included — and the quick run of a save that
changed `content/instagram.yml` or `sources.instagram` in `config/site.yml`.

> Note: saving `content/instagram.yml` starts a quick rebuild that **also reads Instagram and your list**
> (`scripts/ops/push_modules.py`), so a post you add appears a few minutes later. That run skips the look-ups of
> each post's own page (`--no-enrich`): a post the accounts' pages do not show among their newest gets its
> picture and caption at the next **full** update (or write a `caption:`).

#### Add an Instagram post by hand

Use it for an older post you want to feature, or a post that went up on a day Instagram turned the
robot away. Only list posts of the two official accounts.

1. On Instagram, open the post → **…** → **Copy link**.
2. In `content/instagram.yml`, replace `posts: []` with a list. Keep two spaces before each dash:

   ```yaml
   posts:
     - url: https://www.instagram.com/p/ABCdef12345/
       account: gv                                   # gv, lv, or the username (with or without @) — optional
       caption: "Our table at the Spring Assembly"   # optional — read the note below
   ```

3. Click **Commit changes**. The quick run that starts also reads Instagram: the post is on the site a few
   minutes later (its picture and caption, if the accounts' pages did not have them, after the next full run).

Every form the file accepts (checked with the module's `load_manual` on a test copy):

| Entry | Result |
|---|---|
| `- url: https://www.instagram.com/p/ABCdef12345/` with `account: gv` | added under AA Grapevine, id `ig:ABCdef12345`, marked as yours (`extra.manual`) |
| `- https://www.instagram.com/reel/ABCdef12345/` (just the link) | accepted and marked as a Reel; no account → taken from the post's embed, else AA Grapevine |
| `- link: https://www.instagram.com/alcoholicsanonymous_gv/p/ABCdef12345/` | `link:` works like `url:`; links with the username in them work; `/p/`, `/reel/`, `/reels/`, `/tv/` all work |
| `- shortcode: ABCdef12345` with `date: "2026-09-30"` | the post code alone works; `date:` (a date or Unix seconds) replaces the date read from the code |
| `account: "@alcoholicosanonimos_lv"` | read as `lv` |
| `account: xyz` | Note "unknown account 'xyz' (use gv or lv)" — the post is still added |
| `- url: https://www.instagram.com/p/ABC/` | skipped, Note "instagram.yml entry 3: no Instagram post link found …" (a post code has 8–40 characters) |
| a YAML mistake (wrong indent, missing quote) | Note "instagram.yml: YAML error — …"; the file is not read that run, so the posts you added before **leave the site** (unless the automatic check also read them that day) — they come back in the quick run of the save that fixes the file |

The Notes appear in the run summary under **Notes**, next to "Instagram posts" — on days the Instagram
source itself updated (on a day it failed, the summary shows only its **PROBLEM** row).

> Note: `caption:` only **fills in**. The file's own header calls it text "to show instead of
> Instagram's caption", but the code works like this: on a day the automatic check reads that post
> (it reads only each account's ~6 newest), Instagram's own caption wins; on any other day your caption
> is used. So for an older post your caption shows at once; for a brand-new post it takes over only
> after the post drops out of the newest few. With `anonymous: false` and no token the robot never
> visits Instagram: then write a caption, because it is the only text the post will have (it shows as a
> text tile without a picture).

**Remove a hand-added post:** delete its entry. It leaves the site in the quick run of that save — unless the
automatic check still reads it that day; then it stays like any other post (and leaves once it is no
longer among the newest 130). Hand-added posts are never pruned by age.

> Note: a hand-added post takes its place **by its own date** (newest first). `/instagram/` shows 12
> posts per account (up to 48 with "show more") and the home page row only the 6 newest, so an
> **older** post you add is visible on `/instagram/` only while its account has fewer than 48 newer
> posts on the site. Each account posts about 2 a day and the site keeps 130, so after a few weeks an
> old post drops out of view there (it stays in the data and in the search).

**A post's title** is the first meaningful line of its caption, up to 90 characters (checked with
`title_from_caption`): `October 20% off:` + a new line + `The Best of …` → "October 20% off";
`#aa #sober` + a blank line + `One day at a time, together.` → "One day at a time, together."; no
caption → "AA Grapevine on Instagram" / "La Viña en Instagram". A real one (October 2026): `ig:Dd_kdS2Ri0d`
"This week Jeff welcomes Eileen and Marcheta. Season 2, Episode 14."

**Where it shows.** `/instagram/` · `/es/instagram/`: one column per account, 12 posts shown and up to
48 with "show more", the saved picture in a 4:5 frame; nothing loads from instagram.com until a visitor
presses "Show post here". The home page Instagram row (6 posts, alternating accounts). What's New and
the RSS feed, `/monthly/`, `/digest/` and the monthly e-mail (how many posts each account shared, and
the newest), search.

#### Change it, hide it

- **Use only the official way:** `anonymous: false`, plus the two secrets. Without the secrets only
  your list appears — and the Instagram row on `/status/` shows **Failed** every day ("No posts fetched …
  the automatic check is switched off …"), so after 7 days the "A content source has stopped updating"
  issue opens.
- **Keep more or fewer posts:** `keep_per_account`.
- **Hide one post:** no setting; a code change, see [6.2](#62-hide-one-item-everywhere).
- **A caption is badly translated:** `overrides.yml` with the exact original text.

**Code pointers.** `instagram.py` → `load_manual` (your list), `merge_post` (who wins), `build_item`
(title, summary, `extra`), `prune`, class `Fetcher` (one method per way of reading). Display:
`eleventy/filters/media.js` (filters `mediaIgFor`, `mediaIgCaption`, `mediaIgImage`),
`src/pages/instagram.njk`, home `homeInstagram` in `eleventy/filters/home.js`. Test:
`tests/test_sync_pipeline.py`.

---

### 3.7 Shop: Book of the Month, prices, specialty items

**What it reads** — about 12 page requests a day, 5 seconds apart. For each magazine:

1. The **Book of the Month** page (discount, title, blurb, offer dates, link to the product), then the
   product page (price, SKU, picture, and the bulk-book discount tiers).
2. The **subscriptions** page → the region listings (U.S., Canada, International): each plan's
   title, price, SKU and volume prices.
3. Once a month: one product page per subscription type (print, digital, complete) for a short
   description.
4. Once a week: the **specialty items** — greeting cards, pocket planner, wall calendar and, in season,
   the holiday cards (a pack of 12).

Product pictures are saved once (up to 4 new a run) in `src/assets/cache/shop/`.

**Settings** (a path on the magazine's site, or a full address):

```yaml
sources:
  grapevine:
    botm: "/BOTM"
    subscriptions: "/store/grapevine-subscriptions"
    subscription_regions:              # used only when the subscriptions page lists no region links
      us: "/store/us-subscriptions"
      ca: "/store/canada-subscriptions"
      intl: "/store/international-subscriptions"
    specialty:                         # product pages, then a listing as a fallback
      - "/store/greeting-cards"
      - "/store/annual-pocket-planner"
      - "/store/annual-wall-calendar"
      - "/store/holiday-greeting-cards-12-pack"
      - "/store/specialty-items"
    specialty_skip: []                 # kinds never shown: cards, planner, calendar, holiday
  lavina:
    botm: "/libro-del-mes"
    subscriptions: "/tienda/suscripciones"
    # subscription_regions: us / ca / intl, like Grapevine's
    specialty:
      - "/tienda/articulos-especiales"
      - "/tienda/tarjetas-de-ocasion-para-las-fiestas-paquete-de-12"
    specialty_skip: []
```

**How often.** The Book of the Month and the subscription prices: the full daily update, plus the
morning refresh on the **1st** and the **15th** (the first morning refresh that day that has not read
them yet) — the offer changes on the 15th, the issue month on the 1st. Specialty items: at most once a
week. Type descriptions: at most once a month.

**Real data (October 2, 2026):**

| Item | What the site shows |
|---|---|
| Grapevine Book of the Month | *No Matter What: Dealing With Adversity in Sobriety* — $14.99, 20 % off → $11.99, SKU GV31, Sept 15 – Oct 14, 2026 |
| La Viña *Libro del mes* | *Frente a Frente: El apadrinamiento en acción* — $14.99 → $11.99, until Oct 14, 2026 |
| A subscription plan | Grapevine Print Subscriptions: 1-Year — $36.00; 2–19: $35.50, 20–39: $35.00, 40+: $34.00 |
| A specialty item | Holiday Greeting Cards – 12 pack — $22.00; 5+: $20.00 |

**How the store pages are read** (checked with `shop.py`, as of Oct 2, 2026):

| Text on the store page | Read as |
|---|---|
| `Offer good for this title: SEPT. 15 thru OCt. 14 Only.` | Sept 15 – Oct 14, 2026 |
| `15 de septiembre al 14 de octubre` | the same |
| `Offer good thru Oct. 14` | no start, ends Oct 14, 2026 |
| `Dec. 15 thru Jan. 14` | Dec 15, 2025 – Jan 14, 2026 (the latest window that has started) |
| 20 % off $18.00 | sale price $14.40 |
| `1-Year Print Subscription` · `Digital Subscription 2 years` · `Complete Subscription (Print + Digital) 3 Years` | print / 12 months · digital / 24 · complete / 36 |
| `Suscripción impresa 1 año` · `Gift card` | print / 12 months · other |
| `2027 Annual Pocket Planner` · `Agenda de Bolsillo 2027` | planner |
| `Holiday Greeting Cards - 12 pack` · `¡Tarjetas de ocasión para las fiestas! Paquete de 12` | holiday, pack of 12 |

**Where it shows.** `/shop/` · `/es/shop/`: `#botm` (both books of the month, with a live "N days
left" — "Ends tomorrow", "Last day!" — that switches by itself to "Offer ended — see this month's book"
the day after the last day; the next update then takes the card off), `#bulk`, `#subscriptions` (a magazine ×
region switch; `/shop/?pub=lv#subscriptions` opens La Viña's prices), `#price-changes`, `#specialty`,
`#catalogs`. The home page's "this month in the Shop" teaser. `/monthly/` pages and posters, the GV/LV
report, `/accessibility/`, `/tracker/`, the GVR / RLV orientation lessons, the workshop presentations. The booth
display (`/about/#booth`): both Books of the Month (no covers) and the U.S. 1-year print and digital prices of
both magazines, "as of" the day the stores were read, with an announced price change beside them.

**Translations.** The Book of the Month's title and blurb, the type descriptions and the bulk note are
machine-translated; specialty descriptions are never machine-translated. Real fixes in
`overrides.yml`:

```yaml
"No Matter What: Dealing With Adversity in Sobriety": { es: "Pase lo que pase: cómo enfrentar la adversidad en la sobriedad" }
"Frente a Frente: El apadrinamiento en acción": { en: "One on One: AA Sponsorship in Action" }
```

#### Change it, hide it

- **The store moved a page:** change its path. Next run that reads the shop.
- **Stop showing one kind of specialty item:** name the kind under that magazine, e.g.
  `specialty_skip: [holiday]`. Only `cards`, `planner`, `calendar`, `holiday` count; any other word is
  ignored, with a warning in the run's log ("sources.grapevine.specialty_skip: 'holidays' is not one of
  cards, planner, calendar, holiday — ignored") — a typo never hides anything. The other store's item of
  that kind still shows.
  > Note: specialty pages are read at most once a week, and `specialty_skip` is applied at that weekly
  > read — so the item can stay up to about 7 more days. `data/raw/shop.json` → `specialty_checked`
  > shows the last read. (A maintainer can force a read from a computer:
  > `python -m scripts.sync.shop --refresh-specialty`, see README *Troubleshooting*.)
- **Deleting a product page's line does not hide its item:** the listing page adds it back, without
  its description. Use `specialty_skip`.
- **The holiday cards disappeared:** out of season is not an error. The card stays about 14 days after
  the stores take them down, then comes back by itself next season.
- **Hide the Book of the Month:** no setting. An offer leaves the site by itself after its end date
  (even if the store's page still shows it).
- **A price looks wrong:** prices are never typed by hand; they are what the stores show. The one
  exception is an announced change ([3.8](#38-announce-new-prices)).

> Good to know: each part (GV offer, LV offer, GV plans, LV plans, each specialty page) stands alone. A
> part that fails keeps its previous items and marks the source failed. A region listing without one
> readable price counts as failed (plans are never published without prices). A Book of the Month page
> that shows no offer is fine; a page that is not the Book of the Month page at all (maintenance) is an
> error.

**Code pointers.** [`scripts/sync/shop.py`](../scripts/sync/shop.py) → `settings`, `parse_botm`,
`parse_product`, `parse_listing`, `parse_specialty`, `collect_botm`, `collect_subscriptions`,
`collect_specialty`; `scripts/sync/build_data.py` → `build_shop` (which copies only listed fields, see
[6.4](#64-show-a-field-the-site-file-leaves-out)); display `eleventy/filters/shop.js` → `shopBotm`
(`botmView`), `shopSubs`, `shopSpecialty`, and `src/pages/shop.njk`. Tests: `tests/test_shop.py`,
`tests/test_price_changes.py`.

---

### 3.8 Announce new prices

**What it is.** Not a fetcher. When AA Grapevine announces new prices, you add one block to
`config/site.yml`. The site then shows a calm notice ahead of time and switches the 1-year prices by
itself on the day, comparing with what the stores show. The real block (October 2026):

```yaml
price_changes:
  - key: "2027-01"                 # short name: letters, numbers and dashes
    effective: "2027-01-01"        # the day the new prices start (Central time)
    announced: "2026-10-01"        # the notice shows from this day
    notice_until: "2027-01-31"     # the last day of the "New prices since …" notice
    source: "AA Grapevine's letter to Intergroups and Central Offices, October 1, 2026"
    source_es: "Carta de AA Grapevine a las oficinas intergrupales y centrales, 1 de octubre de 2026"
    doc_match: "pricing update.*2027|actualizaci[oó]n de precios.*2027"
    yearly:                        # new 1-YEAR prices, U.S. dollars
      gv: { print: 39.00, digital: 34.00 }
      lv: { print: 19.50, digital: 17.00 }
    books_more: 2.00               # every Grapevine and La Viña book costs this much more
```

| Key | What it accepts | If missing or odd |
|---|---|---|
| `key` | letters, numbers, dashes (up to 32) | the effective month, e.g. `2027-07`; the same key twice → the second block is skipped |
| `effective` | a date `"2027-01-01"` (quotes optional) | required; not a date → the block is skipped |
| `announced` | a date on or before `effective` | missing: the notice starts on the effective day (no advance notice, no message); not a date, or after `effective`: the same, and a Settings problem says so |
| `notice_until` | a date on or after `effective` | 30 days after `effective` (a value that is not a date, or is before `effective`, also gets 30 days, with a Settings problem) |
| `source`, `source_es` | text | shown as written; only one language → the same text on both pages |
| `doc_match` | a regular expression, capitals ignored | finds AA Grapevine's letter among the committee's Drive files → a "Read AA Grapevine's notice" link; no match → no link; not a valid pattern → no link, with a Settings problem |
| `yearly` | `{gv or lv: {print, digital or complete: 39.00}}` | an unknown magazine, type or price is left out (noted); `"$39.00"` and `39` are fine; a price must be above 0 and at most 1000 |
| `books_more` | an amount, e.g. `2.00` | left out; with no valid `yearly` price either, the block changes nothing and is skipped |

**What visitors see, with the block above:**

- **Until Sept 30, 2026:** nothing.
- **From Oct 1, 2026** (`announced`): `/shop/#price-changes` shows "Prices change on January 1, 2027"
  with what changes, the source and the notice link; each affected 1-year plan says "From Jan 1, 2027:
  $39.00"; the Book of the Month cards say "From January 1, 2027, Grapevine and La Viña books cost
  $2.00 more."
- **Jan 1, 2027 at midnight Central** (`effective`): the new 1-year prices show. The page switches by
  itself in the visitor's browser, even between updates. 2- and 3-year, monthly and other plans keep
  the stores' prices.
- **Until Jan 31, 2027** (`notice_until`): the notice reads "New prices since January 1, 2027".
- **Afterwards:** delete the block once the stores show the new prices. A bulletin post about the
  change is written by hand ([Bulletin](bulletin.md)).

Also on: each 1-year plan in `#subscriptions`, the Book of the Month cards, the monthly toolkit, the
GV/LV report and the monthly e-mail.

**When.** The quick rebuild after you save (the site data is rebuilt in every run). The stores' "price
before the change" memory is updated by the shop runs.

**Mistakes are reported, never fatal** (checked with `price_changes.specs`) — as **Settings problems**
in the run summary:

| You wrote | What happens |
|---|---|
| `effective: "2027-13-01"` | price_changes entry 1 (…): effective "2027-13-01" is not a date like "2027-01-01" — skipped |
| `announced: later` | applied, but "announced "later" is not a date … — no notice before the effective day" |
| `yearly: { gv: { print: abc, digital: 30 } }` | digital applied; "yearly gv print: "abc" is not a price like 39.00 — left out" |
| a block with only `effective` | "it changes no price (no valid yearly price and no books_more) — skipped" |
| two blocks with the same effective month and no `key` | the second: "the key "2027-07" is used twice (each change needs its own) — skipped" |

**Code pointers.** [`scripts/sync/price_changes.py`](../scripts/sync/price_changes.py) → `specs`,
`resolve`, `book_stale`, `remember`; `build_data.py` → `plan_change`, `price_changes_doc`; display
`eleventy/filters/shop.js` → `shopPriceChanges`. Test: `tests/test_price_changes.py`. More: README
[When Grapevine announces new prices](../README.md#when-grapevine-announces-new-prices) and the same
section in [`docs/OPERATIONS.md`](../docs/OPERATIONS.md).

---

### 3.9 Daily quotes

**What it reads.** The two magazines' home pages, one request each (none if an earlier part of the
same run already read them). On each page, the block `#quote-of-the-day`: its heading ("Grapevine Daily
Quote October 2" / "Cita Diaria con La Viña Octubre 2"), the quote, who said it and where it comes
from, and the magazine's own e-mail sign-up link. The year is worked out around today (Central time);
a heading without a date counts as today.

**Settings:**

```yaml
site:
  morning_goal: "05:30"     # /status/ measures each morning's quotes against this time (Central)
sources:
  grapevine:
    quote_page: "/"         # the page with the "Grapevine Daily Quote"
  lavina:
    quote_page: "/"         # the page with the "Cita Diaria con La Viña"
```

**How often.** **Every run**. The morning refresh reads it right after the bulletin, so with the
morning alarm set up both quotes are usually on the site by 5:30 AM Central. If a magazine is late, the
Morning check asks again every 10 minutes from 4:00 to 7:00 AM (see
[Automation and troubleshooting](automation-and-troubleshooting.md)).

**The quotes of October 2, 2026** (`data/site/quote.json`):

| | Grapevine | La Viña |
|---|---|---|
| heading | Grapevine Daily Quote October 2 | Cita Diaria con La Viña Octubre 2 |
| quote | "In the life of each AA member, there still lurks a tyrant. His name is alcohol." | "Mi recuperación depende de que muchas personas me extiendan una mano. …" |
| who / source | AA Co-Founder, Bill W., July 1946, "The Individual in Relation to AA as a Group", The Language of the Heart | "¿A qué reunión irás mañana?" SANTA ROSA, CALIFORNIA, NOVIEMBRE DE 1999 · source: *I Am Responsible* |

The attribution is split from the source book only at a capitalized "From", "Tomado de", "Fuente" or
"De" (checked with `split_attribution`): `AA Co-Founder, Bill W., September 1945, From: "Title", The
Language of the Heart` → who "AA Co-Founder, Bill W., September 1945", source ""Title", The Language of
the Heart". That day's Grapevine attribution has no "From:", so its source stays empty.

**Where it shows.** The home page quote card (`/` · `/es/`): the page language's magazine first; a
quote older than 2 days is hidden; "Today" / "Yesterday" is added in the visitor's browser. `/monthly/`
("Keep up all month"). `/status/`: when today's quotes came in, and the last 7 mornings under
*Technical details*. The run summary's **Daily quote:** line. The booth display (`/about/#booth`): both quotes
as the home page shows them, with their attribution and a QR code to the official page. It is not in What's New
or search.

**Change it.** Nothing to override: each quote is shown exactly as published, in its own language,
never translated. If a magazine moves its quote to another page, change `quote_page`. A page that
falls back to an older quote never replaces a newer one already on the site.

**Code pointers.** [`scripts/sync/quote.py`](../scripts/sync/quote.py) → `parse_quote`, `entry`,
`collect`, `build_site` (copies only the fields in `SITE_KEYS`); display `eleventy/filters/home.js` →
`homeDailyQuotes`, and `src/pages/index.njk`. Tests: `tests/test_quote.py`, `tests/test_morning.py`,
`tests/test_run_wiring.py`.

---

### 3.10 Editorial themes and deadlines

**What it reads** — three parts, each kept and reported on its own:

| Part | Page | What it gives |
|---|---|---|
| `gv` | `https://www.aagrapevine.org/contribute` ("Editorial Calendar") | each monthly issue's theme(s), the "stories due …" deadline and the editors' prompt; the calendar's own document and the submit and guidelines links |
| `lv` | `https://www.aalavina.org/temas-sugeridos` | La Viña's evergreen story suggestions (no issue, no deadline) |
| `lv-themes` | La Viña's **yearly themes document**, linked from `https://www.aalavina.org/recursos` | each two-month issue's theme, its deadline and the address to send stories to — for every year in the document |

**Settings:**

```yaml
sources:
  grapevine:
    contribute: "/contribute"
  lavina:
    contribute: "/temas-sugeridos"
    themes_page: "/recursos"           # the page that links the yearly themes document
    themes_link: "\\btemas\\b"         # how to recognize it (a regular expression)
```

#### Keep La Viña's yearly themes coming

La Viña puts no issue-by-issue calendar on a web page. Once a year it posts a document (January 2026:
"Temas de LV 2026 y 2027", file `Temas_de_LV_2027_2026.pdf`). The robot:

1. opens `themes_page` and looks at every link to a document (`.pdf`) outside menus, headers and
   footers;
2. keeps the links whose file name, link text or picture text matches `themes_link` **and** names a
   year ("_" in a file name counts as a space);
3. takes the newest: the highest year named, then the newest upload folder (`/files/2026-01/`);
4. downloads it (up to 20 MB), reads every page and checks it: as many themes as issues, every
   deadline readable and in order, each deadline 1–15 months before its issue.

Examples (checked with `find_themes_link`) for a resources page with these links:

| Links on the page | `themes_link` | Document chosen |
|---|---|---|
| "Temas de LV 2026 y 2027" (`2026-01/Temas_de_LV_2027_2026.pdf`), "Temas de LV 2025", "Guia del RLV 2026" | `"\\btemas\\b"` (the default) | `Temas_de_LV_2027_2026.pdf` — 2027 is the highest year |
| the same, plus "Calendario editorial 2028" | `"\\btemas\\b"` | still `Temas_de_LV_2027_2026.pdf` — "Calendario" does not match |
| the same | `"\\btemas\\b\|calendario editorial"` | `Calendario_editorial_2028.pdf` — it matches now, and 2028 is higher |

> If La Viña moves or renames the document, change `themes_page` and/or `themes_link`. Until then
> `/status/` and the run summary say "lv-themes: no yearly themes document linked from … — moved or
> renamed?" and the themes read last time stay on the site. In YAML, write each backslash twice
> (`"\\b"`), as above. (Reading this guide as plain text? The `\|` in the table is only how a `|` is
> written inside a Markdown table; in `config/site.yml` you write a plain `|`.)

**Deadlines** (checked with `parse_gv` and `parse_deadline`): "Spiritual Awakenings (stories due June
1, 2026) Share your personal journey…" → theme "Spiritual Awakenings", deadline June 1, 2026, prompt
"Share your personal journey…". A deadline written without a year is the latest such day before the
issue month: "June 1" for January 2027 → June 1, 2026; "Sept. 1" for March 2027 → Sept 1, 2026. La Viña
issues are named the way the magazine does: May 2027 → "Mayo / Junio 2027".

**What is kept.** The issue on sale, the one before it, and every later one. A part that suddenly finds
fewer than 40 % of yesterday's themes (when it had 6 or more) is not believed: the previous themes stay
and the source is marked failed ("only N themes found (had M) — kept the previous …").

**Real data (October 2, 2026):** 44 themes — 17 Grapevine, 8 dated La Viña themes, 19 La Viña suggestions. For
example `ed:gv:2027-12:remote-communities` "Remote Communities" (December 2027, stories due May 1, 2027)
and `ed:lv:2027-07:prisiones` "Prisiones" (Julio / Agosto 2027, due Dec 15, 2026, sent to
lveditorial@aagrapevine.org).

**How often.** The full daily update — and the quick run of a save that changed one of its settings
(`sources.<pub>.contribute`, `themes_page`, `themes_link`, `rlv_resources`, a site's `base`).

**Where it shows.** `/contribute/#deadlines` · `/es/contribute/#deadlines`; the home page *Write for
the magazines* (4 themes); `/published/`; `/monthly/`; the GV/LV report; the workshop presentations;
the GVR / RLV orientation; search; the booth display (the next 3 themes of each magazine whose deadline is still
ahead). Themes are never "new" (their date is a deadline).

**Change it.** Themes and prompts are machine-translated → fix them in `overrides.yml`. There is no
switch to hide one theme.

**Code pointers.** [`scripts/sync/editorial.py`](../scripts/sync/editorial.py) → `parse_gv`,
`parse_lv`, `find_themes_link`, `parse_lv_themes`, `rows_to_items`, `keep_window`, `settings`; display
`eleventy/filters/read.js` → `editorialFor`, home `homeThemes`. Test: `tests/test_editorial.py`.

---

### 3.11 Weekly open meetings

There are two public weekly meetings on Zoom: AA Grapevine's **Weekly Open** (Wednesdays, English),
read from its web page, and La Viña's **Reunión Abierta** (Thursdays, Spanish), written from your
settings because it has no web page yet.

**Grapevine's meeting.** The robot reads `https://www.aagrapevine.org/grapevine-weekly-open`
(setting `sources.grapevine.weekly_open: "/grapevine-weekly-open"`). The page says, in one sentence:

> To join the meeting live on Wednesdays at Noon Eastern, use Zoom code 871 2036 8287 with password 238047

Read as (checked with `parse_page`): Zoom ID "871 2036 8287", passcode "238047", day "Wednesdays",
time "Noon Eastern" → **11 AM Central**, plus the next meeting date. If one detail is missing one day,
yesterday's is kept. If the page cannot be read at all, the previous details stay and the source is
marked failed.

#### Change La Viña's weekly open meeting

Edit the `lavina_weekly_open:` block (the real one):

```yaml
lavina_weekly_open:
  enabled: true
  title_es: "Reunión Abierta de La Viña"
  title_en: "La Viña Open Meeting (in Spanish)"
  day: "thursday"               # every week
  time: "12:00"                 # in `timezone` (12 p. m. Eastern = 11 a. m. Central)
  timezone: "America/New_York"
  starts: "2026-11-05"          # the first meeting (a Thursday)
  zoom_id: "871 2036 8287"
  passcode: "238047"
  summary_es: "Una reunión abierta virtual de AA en español, cada semana: …"
  summary_en: "A weekly virtual open AA meeting in Spanish where two members share …"
  url: ""                       # La Viña's page for the meeting, once there is one
  source: "Official La Viña flyer (November 2026), shared with the committee"
  flyer_match: "reuni[oó]n abierta de la vi[nñ]a|la vi[nñ]a open meeting"
```

| Key | What it accepts |
|---|---|
| `enabled` | `false` (or deleting the block) takes the card off the site |
| `title_es`, `title_en`, `summary_es`, `summary_en` | shown exactly as written — never machine-translated |
| `day` | English or Spanish; the first three letters count (`thursday`, `Jueves`, `jue`) |
| `time` | `"12:00"`, `"12 p. m."`, `"Noon"`, `"mediodía"`, `"11 a. m."`, even an unquoted `12:00` |
| `timezone` | a time-zone name such as `America/New_York` (the default) or `America/Chicago` — **not** `Eastern` |
| `starts` | the first meeting; until then the card says "Starts …". A date that is not on `day` → the first real meeting day is used |
| `zoom_id` | 9–11 digits, shown grouped ("871 2036 8287") |
| `passcode`, `url`, `source` | shown or linked as written |
| `flyer_match` | a regular expression (capitals ignored) that finds the flyer on the committee's Drive → a "See the flyer" link on the card |

Checked with `lavina_item` (as of Oct 2, 2026): the real block gives "Jueves, 12 p. m. (hora del
Este)", **11 AM Central**, next meeting Nov 5, 2026. `time: "11 a. m."` → 10 AM Central.

> Note: if `day` or `time` is not understood (for example `"25:00"`), or `timezone` is not a real
> time-zone name (for example `"Eastern"`), the La Viña card **silently leaves the site** in the quick
> run of that save (which reads this block again). The only trace is a warning line in the run's log
> ("lavina_weekly_open: … — item left out") — nothing on `/status/` and nothing in the run summary. After
> editing this block, look at `/meetings/#weekly-open` a few minutes later.

**How often.** Both meetings: the full daily update — and the quick run of a save that changed
`lavina_weekly_open` or `sources.grapevine.weekly_open` (or `sources.grapevine.base`), so an edit to the La Viña
block (time, Zoom, `enabled: false` …) shows a few minutes after you save. `flyer_match` is read by the page
itself and follows at the quick rebuild in any case.

**Where it shows.** `/meetings/#weekly-open` · `/es/meetings/#weekly-open` — the one place with the
Zoom details, the page language's meeting first. One line on the home page, on `/listen/` and on
`/watch/`; `/accessibility/#phone` and `/offline/` (joining by phone with these IDs); `/monthly/`
posters; the GV/LV report; the presentations; search; the booth display ("Meetings you can join", with the Zoom
meeting ID). Never "new".

**Code pointers.** [`scripts/sync/weekly_open.py`](../scripts/sync/weekly_open.py) → `parse_page`,
`build_item`, `lavina_item`, `with_lavina`, `carry_join_details`; `build_data.py` →
`weekly_open_items` (Grapevine always first); display `eleventy/filters/committee.js` → `cmWeeklyAll`,
and `src/pages/meetings.njk`. Test: `tests/test_sync_pipeline.py`.

---

### 3.12 Record your story by phone

**What it reads** — 3 pages a day: Grapevine's Audio Project `https://www.aagrapevine.org/audio-portal`,
and La Viña's `https://www.aalavina.org/graba-tu-historia` with its instructions page. From them: the
phone number, the keys to press, the length, the e-mail address for recordings (protected addresses
are decoded), the accepted formats, the "no speaker recordings" note and Grapevine's story playlists.
Only North American numbers are read (`Call 559-726-1216 or (559) 670-1601` → +15597261216,
+15596701601).

**Settings:**

```yaml
sources:
  grapevine:
    audio_project: "/audio-portal"
  lavina:
    record_story: "/graba-tu-historia"                        # read
    record_instructions: "/instrucciones-graba-tu-historia"   # read
    record_tips: "/consejos-de-grabacion"                     # only linked
    record_topics: "/temas-sugeridos"                         # only linked
    sample_audio: "/audio-de-muestra"                         # only linked
links:
  gv_audio_project: "https://www.aagrapevine.org/audio-portal"   # links on /contribute/
```

**Real data (October 2026):**

| | Grapevine | La Viña |
|---|---|---|
| phone | (559) 726-1216 | (559) 670-1601 |
| keys | record 1 · finish # · save 1 · permission 2 | record 1 |
| length | 6–8 minutes | up to 7 minutes |
| recordings by e-mail | webcoord@aagrapevine.org (WAV, MP3) | lveditorial@aagrapevine.org (WAV, MP3) |

**How often.** The full daily update — and the quick run of a save that changed `sources.grapevine.audio_project`,
a `sources.lavina.record_*` page or a site's `base`. Each magazine stands alone: a page that cannot be read, or
is missing a number, key or e-mail, keeps that magazine's previous data and marks the source failed —
the site never shows half-read steps. If only La Viña's instructions page fails, the source still
counts as updated and the run summary shows a Note.

**Where it shows.** `/contribute/#record` · `/es/contribute/#record`; `/monthly/`; the GV/LV report;
the presentations. `/listen/`, `/watch/` and `/accessibility/` link to it.

**Change it.** The numbers and addresses are never typed by hand. The **wording** of the steps is the
site's own, in both languages: `src/_i18n/community.json`, keys `community.rec.*` (see
[Translations](translations.md)).

**Code pointers.** [`scripts/sync/audio_project.py`](../scripts/sync/audio_project.py) → `parse_gv`,
`parse_lv`, `parse_lv_instructions`, `phones`; `build_data.py` → `AUDIO_FIELDS` and
`build_audio_project` (only the listed fields, each re-checked: a dialable +1 number, keys 0–9 # *, a
real e-mail address). Test: `tests/test_audio_project.py`.

---

### 3.13 Grapevine meetings from the intergroup lists

**What it reads.** Once a day, the public "12 Step Meeting List" of 8 intergroups and central offices —
the same eight lists the Rowlett Group's meetings page combines: in or at our Area the Dallas
Intergroup, the Fort Worth Central Office, the Tyler Central Service Office, the Spanish-speaking Dallas
office and District 71 (Abilene); nearby the Arkansas Central Office, OKC Intergroup and Northwest Texas
Area 66. It keeps every active meeting whose types include **GR** (Grapevine), shows a meeting listed
by two offices **once**, and decides "our Area" or "nearby" from the meeting's city and your county
list.

**Only public details are copied:** name, day, time, place, address, map position, region, meeting
types, in person / online / hybrid, and the link to the meeting's page on the office's site. Never
phones, e-mails, contact names, Zoom links or passwords, notes, payment or edit links. A place name
that contains a phone number or an e-mail address is dropped.

**Settings** (one office shown; all eight are in `config/site.yml`):

```yaml
meetings:
  enabled: true
  type: "GR"                                   # the meeting-list code for Grapevine meetings
  area_label: { en: "Our Area (NETA 65)", es: "Nuestra Área (NETA 65)" }
  feeds:                                       # order = order on the page
    - id: tyleraa
      name: "AA Central Service Office, Tyler"
      site: "https://www.tyler-aa.org"
      page: "https://www.tyler-aa.org/meetings/"
      methods: ["page"]                        # its robots.txt does not allow the JSON list
      lang: en
      in_area: true
      region_label: { en: "East Texas (Tyler)", es: "Este de Texas (Tyler)" }
```

| Key (per office) | What it does |
|---|---|
| `id`, `name`, `site` | who the office is |
| `feed` | the office's JSON meeting list (`…/wp-admin/admin-ajax.php?action=meetings`) |
| `page` | its public meetings page (default `<site>/meetings/`), read when the list cannot be |
| `methods` | the order to try: `["feed", "page"]` by default |
| `key_env` | the name of an optional GitHub secret with the office's key (`TSML_KEY_AADALLAS`, `TSML_KEY_FORTWORTHAA`) |
| `feed_obf`, `key_const` | the keyed list address, hidden the Rowlett way (see below) |
| `lang`, `in_area` | the office's language; `in_area: true` = a Texas city that cannot be matched still counts as our Area |
| `region_label` | the group name for this office's meetings outside our Area |
| `add_types` | types added to every meeting (`["S"]` = in Spanish) |
| `region_types` | types added to one region's meetings, e.g. `{ "NWA Spanish Speaking GRPS": ["S"] }` |
| `enabled: false` | switches this office off |

**Keys.** Dallas and Fort Worth answer their full list only with a key. Each run tries: (1) the GitHub
secret named in `key_env`; (2) `feed_obf` in the settings — the full address with its key, written
backwards and then base64, exactly as the Rowlett Group's page stores it (this only keeps it from
casual reading; it is **not** encryption); (3) the Rowlett Group's page itself. A refused key is skipped
with a Note. Without any key, the office's public page is read instead. No key is ever written anywhere
in plain text — data, logs and messages show `key=[redacted]`.

- **An office gave out a new key:** either add it as the secret (needs the **NETA65** admin account),
  or, on a computer with the repository, run
  `python -m scripts.sync.meetings --obfuscate "<the full list address with the new key>"` and paste
  the printed value into that office's `feed_obf`.

**Real data (October 2, 2026):** 23 meetings — 13 in our Area, 10 nearby (2 Arkansas, 8 Oklahoma City). Two offices
gave Notes ("Alcohólicos Anónimos Dallas: feed: … did not answer"; "OKC Intergroup: feed: the answer is
not a meeting list (not JSON)"); their earlier meetings were kept.

**How often.** The full daily update — and the quick run of a save that changed the `meetings:` block,
`spotlight.neta65_counties` or `data/geo/texas_places.json`. An office that fails keeps its previous meetings (a Note);
the source is marked failed only when no office at all could be read.

**Where it shows.** `/meetings/#grapevine-meetings` · `/es/meetings/#grapevine-meetings` — their one
home: our Area first, then each nearby region in your order, with filters for place, day, in person /
online and "include nearby areas". One line on the home page, `/monthly/`, the GV/LV report, the
orientation, and the search (one result per group and place: a group that meets several times a week
is one result).

#### Switch an office off, add one, change the groups

| You want to … | Do this | Takes effect |
|---|---|---|
| Hide every meeting of one office | `enabled: false` in its block (or delete the block) | quick rebuild after saving |
| Hide the whole Grapevine meetings list | `meetings.enabled: false` | quick rebuild after saving |
| Rename a group or reorder the nearby groups | `region_label`, `area_label`, the order of `feeds` | quick rebuild after saving |
| Add an office | add a block with `id`, `name`, `site`, `feed` (or `page` + `methods: ["page"]`) … | the quick run of that save (it reads the lists again because `meetings:` changed) |
| Change which counties are "our Area" | `spotlight.neta65_counties` ([3.2](#32-where-a-writer-is-from-the-spotlight)) | the quick run of that save (worked out when the lists are read, and that run reads them) |

**Code pointers.** [`scripts/sync/meetings.py`](../scripts/sync/meetings.py) → `settings`,
`read_office`, `to_record`, `dedupe`, `area_of`, `build_site` (copies only the fields in `EXTRA_KEYS`
and `SITE_KEYS`), `redact`, `obfuscate`; display `eleventy/filters/committee.js` → `cmGvMeetings`, and
`src/pages/meetings.njk`. Test: `tests/test_meetings.py`. More: README
[section 10](../README.md#10-optional-upgrades) ("Meeting-list keys").

---

### 3.14 The committee meeting

**What it is.** Not a fetcher: the dates come from the `meeting:` block — "the Nth weekday of every
month, from–to, Central time", daylight saving included.

```yaml
meeting:
  week_of_month: 3          # 1–5, or -1 for "the last one"
  weekday: "wednesday"
  start: "19:00"            # 24 h, Central time
  end: "20:00"
  platform: "Zoom"
  zoom_url: "…"             # the whole official Zoom link (as in config/site.yml)
  meeting_id: "…"
  passcode: "…"
  chair_title: "Grapevine / La Viña Chair"
  chair_email: "grapevine@neta65.org"
  note: "All AA members are welcome to attend. No registration required."
  skip_dates: []            # e.g. ["2026-12-16"] — dates that do not happen
```

**What the site understands** (checked with `meeting_rule` and `check_skip_dates`):

| You write | The site uses |
|---|---|
| `weekday: "wednesday"`, `"Wednesday"`, `"miércoles"` | Wednesday |
| `weekday: "saturday"` or `"sábado"` | Saturday |
| `weekday: "Saturdays"` (plural) or `"sat"` | **Wednesday** — not understood, and no warning |
| `week_of_month: 3` / `-1` | the 3rd / the last one of the month |
| `week_of_month: "second"` or `6` | **the 3rd** — not understood, and no warning |
| `start: "19:00"`, `"7:00 PM"`, `"7pm"`, `19`, or an unquoted `19:00` | 7:00 PM |
| `start: "19.30"` | 7:30 PM |
| `start: "noon"` or `"25:00"` | 7:00 PM (the default) |
| `end` missing, or not after `start` (e.g. `"18:00"`) | one hour after the start |
| `skip_dates: ["2026-12-16"]` | the December meeting is left out |
| `skip_dates: ["2026-12-17"]` | ignored + Settings problem: skip date "2026-12-17" is not the 3rd Wednesday of its month — ignored (that month's is 2026-12-16) |
| `skip_dates: ["Dec 16"]` | ignored + Settings problem: skip date "Dec 16" is not a date like "2027-01-09" — ignored |

> Note: the committee meeting is strict on purpose — the pages also compute the dates in the visitor's
> browser, and both must agree. Monthly events under `recurring_events:` are forgiving ("Saturdays",
> "2nd", "second", "last" all work there): see [Flyers and events](flyers-and-events.md).

With the settings of October 2026 the next meetings are **Oct 21, Nov 18 and Dec 16, 2026, 7–8 PM Central**. If you
change `note:` without adding a `note_es:`, the Spanish note is machine-translated.

**When.** The quick rebuild after you save: the dates are rebuilt in every run, and the pages compute
them too.

**Where it shows.** `/meetings/#committee-meeting` · `/es/meetings/#committee-meeting` (countdown,
"add to calendar"), the home page's next-meeting card, `/events/` and the calendar feeds `/events.ics`
· `/es/events.ics`, `/monthly/` and its posters, the QR posters, `/accessibility/#phone` (joining by
phone with the meeting ID), and the booth display ("Meetings you can join": its monthly rule, Zoom and the meeting
ID).

**Code pointers.** [`scripts/sync/meeting.py`](../scripts/sync/meeting.py) → `meeting_rule`,
`parse_hhmm`, `check_skip_dates`, `upcoming_rule_dates`; `build_data.py` → `committee_meetings` (12
months into `events.json`); `src/_data/meeting.js`; `eleventy/filters/committee.js` → `meetingDates`.
Tests: `tests/test_build_times.py`, `tests/test_recurring_events.py`, `tests/test_events_feeds.py`.

---

### 3.15 GV/LV event calendars

AA Grapevine runs one event calendar for both magazines. In the full daily update,
[`scripts/sync/events_external.py`](../scripts/sync/events_external.py) reads it (through the sites'
sitemap) and keeps Texas events and Spanish-language online events for `/events/`. It is covered with
the other events in [Flyers and events](flyers-and-events.md). Its row on `/status/` is "GV/LV event
calendars".

---

### 3.16 The Texas writers archive (content/archive)

**What it reads.** Nothing online. [`scripts/sync/writers_archive.py`](../scripts/sync/writers_archive.py) reads
the two exports of the magazines' online archives that the owner keeps in the repository folder
`content/archive/` (`aagrapevine_archive_2026-10-04.csv`, 35,942 rows; `aalavina_archive_2026-10-04.csv`, 3,607
rows), keeps the rows by writers from Texas (1,263 on 4 October 2026: 1,261 stories, as two were listed twice) and
saves them in `data/raw/writers_archive.json`. `build_data` joins them with every Texas story of the magazine stories source
(3.1, any age) into `data/site/writers_archive.json`.

**Settings:** the files themselves (the newest of each magazine, by the date in its name), `writers_archive:
min_rows_ratio` (0.8: a new file much smaller than the last one is not used) and `spotlight.neta65_counties`
(which writers count as Area 65, worked out again on every run).

**How often.** **Every run** (a few seconds, no request): the morning refresh, the midday and evening refreshes,
the nightly full update and every push. A push of a new file shows it about 3 minutes later.

**Where it shows.** `/published/#archive` · `/es/published/#archive` ("Texas writers through the years"), the
JSON file of the rest of Texas (`/published/texas-archive.json`), one line on the home page, the site search
(the writers' towns and counties, never their names), and the row **Texas writers archive** on `/status/`. Its
stories never go into the 60/90-day lists, the digest or the district report.

Everything else — the names, the columns, replacing a file, the safety checks, troubleshooting — is in its own
guide: [Writers archive](writers-archive.md).

---

## 4. What happens next (which run, how long)

Nothing "watches" the magazine sites: the robot reads them when a run starts. A run of the **Website update**
workflow (*Actions* tab on GitHub) can start in five ways:

| Run | Started by | Usually | Reads | Until it is live |
|---|---|---|---|---|
| **Nightly full update** | GitHub's schedule, set for 1:17 AM Central (12:17 AM in winter). It is set **4 hours early on purpose**: GitHub starts this repository's timed runs 4–6 hours late. | starts about 5–7 AM Central | every source, plus up to 40 minutes of document search | up to about an hour (on October 2, 2026, with little left for the document search, about 10 minutes) |
| **Midday refresh** (quick) | GitHub's schedule, set for 7:07 AM Central (6:07 AM in winter), also 4 hours early | about 11 AM–1 PM Central | Google Drive, the bulletin and event files, podcasts, the writers archive files, the daily quote | a few minutes |
| **Evening refresh** (quick) | GitHub's schedule, set for 3:07 PM Central (2:07 PM in winter), also 4 hours early | about 7–9 PM Central | the same as the midday refresh | a few minutes |
| **Quick rebuild after you save** | saving a file in `config/`, `content/`, `src/`, the code, `data/geo/`, `overrides.yml` or `glossary.yml` | right away | the same as the midday refresh, **plus** the sources only the full update reads whose own input you changed (YouTube, Instagram, editorial themes, weekly open meetings, record your story, Grapevine meetings, GV/LV event calendars — never the magazine stories, the shop or the document search) | the run takes a few minutes (about 2 on October 2, 2026); allow 10–20 minutes before every copy of the page shows it |
| **Morning refresh** | the Morning check (the 4:30 AM alarm, plus GitHub's hourly backstop) | before 5:30 AM Central | Drive (5 minutes at most), the bulletin, then the daily quote, then podcasts and the writers archive files; on the **1st** also the magazines' current-issue pages and the shop; on the **15th** the shop | about 3 minutes |
| **By hand** | *Actions → Website update → Run workflow* (your MKP715 login can do this) | when you click | all boxes empty = a full run; **skip_crawl** = quick; **morning** = morning | full: up to about an hour; quick: a few minutes |

On the 1st of the month — and after a day GitHub skipped — the Morning check also starts the full update.

**Which run reads which source:**

| Source | Full | Quick (save, midday, evening) | Morning |
|---|---|---|---|
| Podcasts | yes (+ weekly feed discovery) | yes | yes |
| Daily quote | yes | yes | yes (right after Drive and the bulletin) |
| Texas writers archive files | yes | yes | yes |
| Magazine stories | yes | – | on the 1st (current-issue pages only) |
| Shop | yes (specialty items weekly) | – | on the 1st and the 15th |
| YouTube, Instagram, editorial themes, weekly open meetings, record your story, Grapevine meetings, GV/LV event calendars | yes | only in the quick run of a save that changed that source's own input | – |
| Document search | yes (up to 40 minutes) | – | – |
| Committee meeting, price changes, writer's place, translations (the site data rebuild) | yes | yes | yes |

**When does my change show?**

| You change … | It shows after |
|---|---|
| `site.watch`, `site.listen`, `site.about_videos` | the quick rebuild |
| `price_changes:`, `meeting:` | the quick rebuild |
| `spotlight:` (days, scope, counties) — for the spotlight and the Texas writers archive | the quick rebuild |
| `spotlight.neta65_counties` — for the Meetings page's "Our Area" | the quick rebuild (it also reads the meeting lists) |
| a new file in `content/archive/` | the quick rebuild ([Writers archive](writers-archive.md)) |
| `sources.podcasts` (add, remove, reorder a show) | the quick rebuild |
| `sources.<pub>.quote_page` | the quick rebuild |
| `library.official_hosts` (hiding a host) | the quick rebuild (documents of a newly added host: the next document search) |
| `meetings.enabled`, an office's `enabled: false` or deleted block, `area_label`, `region_label`, office order | the quick rebuild |
| adding or changing an office (`feed`, `page`, `methods`, keys) | the quick rebuild (it reads the meeting lists again) |
| `lavina_weekly_open.flyer_match` | the quick rebuild |
| the rest of `lavina_weekly_open`, `sources.grapevine.weekly_open` | the quick rebuild (it reads the weekly open meetings again) |
| `content/instagram.yml`, `sources.instagram` | the quick rebuild (it reads Instagram again; pictures and captions it could not get: the next full run) |
| `sources.youtube` | the quick rebuild (the channels' feeds; the complete listing of older videos: a full run, once a week) |
| `sources.<pub>.contribute`, `themes_page`, `themes_link` | the quick rebuild (it reads the editorial themes again) |
| `sources.grapevine.audio_project`, `sources.lavina.record_*` | the quick rebuild (it reads the story lines again) |
| `data/geo/texas_places.json` | the quick rebuild (the meeting lists are read again; the writers' places are worked out again anyway) |
| `sources.crawler`, `TITLE_OVERRIDES` and the other `crawl_rules.py` tables | the next full run |
| `sources.<pub>.magazine_hub` | the next full run (or the morning refresh of the 1st) |
| `sources.<pub>.botm`, `subscriptions`, `subscription_regions` | the next full run (or the morning refresh of the 1st / 15th) |
| `sources.<pub>.specialty`, `specialty_skip` | the next weekly read of the specialty items (up to about 7 days) |
| `data/translations/overrides.yml` | the quick rebuild |
| code in `scripts/sync/build_data.py` or `eleventy/` (e.g. [6.2](#62-hide-one-item-everywhere)) | the quick rebuild |

> Good to know: "the quick rebuild" in this table reads a full-update source again only when the save changed
> that source's own setting (`scripts/ops/push_modules.py` compares `config/site.yml` with its copy from before
> the save). A commit message that contains `[skip ci]` starts nothing. Files under `data/` (except
> `overrides.yml`, `glossary.yml` and `data/geo/`), `docs/` and Markdown guides such as this one start no
> rebuild either. Only one update runs at a time: a run started while another is going waits for it
> (it then starts from the newest data). After a run, a page can take up to about 10 more minutes to
> show the change everywhere (browser and GitHub Pages copies).

More on runs, the Morning check and the run summary: [Automation and troubleshooting](automation-and-troubleshooting.md).

---

## 5. Where it shows on the website

| Page (English · Spanish) | What the automatic sources put there |
|---|---|
| Home `/` · `/es/` | daily quote card; *From the magazines* (5 stories per issue) and "this month in the Shop"; *Write for the magazines* (4 themes); *Listen & Watch* (a featured episode + 3, 5 videos, the weekly open line); *Published writers*; the next committee meeting card and a link to the Grapevine meetings; *Library* (the 6 newest documents); *Instagram* (6 posts) |
| `/read/` · `/es/read/` | magazine stories: the current issues and the archive |
| `/published/` · `/es/published/` | stories by writers from Area 65 and Texas; editorial themes; the Texas writers archive (`#archive`: the archive files + every captured Texas story) |
| `/library/` · `/es/library/` | official documents (next to the committee's own documents from Drive) |
| `/listen/` · `/es/listen/` | podcast episodes; the Short in the header; the weekly open line; the record-your-story link |
| `/watch/` · `/es/watch/` | videos; the hero video; the weekly open line; the record-your-story link |
| `/instagram/` · `/es/instagram/` | Instagram posts, one column per account |
| `/shop/` · `/es/shop/` | `#botm`, `#bulk`, `#subscriptions`, `#price-changes`, `#specialty`, `#catalogs` (catalogs and order forms are Library documents) |
| `/contribute/` · `/es/contribute/` | `#deadlines` (editorial themes), `#record` (record your story), the writer kit (documents), published writers |
| `/meetings/` · `/es/meetings/` | `#committee-meeting`, `#grapevine-meetings`, `#weekly-open` |
| `/events/` · `/es/events/`, `/events.ics` · `/es/events.ics` | the committee meeting dates; the GV/LV event calendars (see [Flyers and events](flyers-and-events.md)) |
| `/about/#videos` | the `about_videos` cards |
| `/about/#booth` (the booth display; its show is `/about/booth.json`, rebuilt with every deploy) | the next events and assembly, both daily quotes, the official channel's Shorts and short videos, the 6 newest Grapevine podcast episodes, the next story themes, the 1-year subscription prices, both Books of the Month, the meetings anyone can join (the committee meeting, the weekly open meetings, La Viña's workshop) — beside the committee's own slides. An item that says a word the booth never shows is left out (a list loses only that row) ([Booth display](booth.md)) |
| `/accessibility/` | ASL videos, audio formats (shop), joining by phone (committee meeting and weekly open IDs), a link to record your story |
| `/offline/` | joining by phone (weekly open IDs) |
| `/gvr/` | document collections (GVR kit, RLV kit, catalogs …) |
| `/monthly/` and `/monthly/YYYY-MM/`, the report `/monthly/#report` | issue themes, story counts, deadlines, the Book of the Month, the daily quote, dates, posters |
| `/digest/` · `/es/digest/` and the monthly e-mail | last month's stories, writers, podcasts, videos, Instagram posts, documents; price-change notices |
| `/whats-new/` · `/es/whats-new/`, `/feed.xml` · `/es/feed.xml` | new stories (not back-catalog issues), dated documents, videos, episodes (with audio), Instagram posts — with the bulletin and Drive files; the newest 150 |
| `/search/` · `/es/search/` | stories, themes, episodes, videos, Instagram posts, documents, the weekly open meetings and the Grapevine meetings (one result per group and place) — not the shop items or the quotes |
| `/status/` · `/es/status/` | one row per source: badge, last update, items, new this week |

---

## 6. Going further: change the code

Read this when a setting is not enough. Every change below is a normal edit on GitHub; run the tests
first if you can ([6.7](#67-test-your-change)).

### 6.1 How the pieces fit

```text
scripts/sync/<module>.py  →  data/raw/<source>.json  →  scripts/sync/build_data.py  →  data/site/<file>.json  →  eleventy/filters/*.js + src/pages/*.njk  →  the page
 (reads the source)           (everything ever found)     (translates, "New", What's     (what the pages read,       (data → HTML)
                                                           New, status, hiding)          via src/_data/db.js)
```

Rules worth knowing:

- **Nothing is lost on a bad day.** `merge_items` in `scripts/sync/common.py` keeps every item ever
  found and its first-seen date, and a field that is empty today keeps yesterday's value. (A few
  modules trim on purpose: Instagram keeps the newest 130 posts per account, the editorial themes keep
  their window of issues, and the shop's list is replaced by each good read.)
- **A broken source never stops the others.** `run_module` marks its raw file `ok: false` with the
  error; the old items stay.
- **The robot owns `data/raw`, `data/site`, `data/state`, `data/translations/cache.json` and
  `src/assets/cache`.** Never edit those by hand; change the code or the settings instead.

| Raw file (module) | Site file | Built in `build_data.py` by | New `extra` fields copied by themselves? |
|---|---|---|---|
| `youtube.json` | `videos.json` | `simple(ctx, "youtube", ("video",))` | yes |
| `podcasts.json` | `episodes.json` | `simple(ctx, "podcasts", ("episode",))` | yes |
| `instagram.json` | `instagram.json` | `simple(ctx, "instagram", ("post",))` | yes |
| `articles.json` | `articles.json`, `spotlight.json` (and the captured Texas stories of `writers_archive.json`) | `simple(ctx, "articles", ("article",))`, `enrich_articles`, `plan_spotlight` | yes |
| `writers_archive.json` (the archive files) | `writers_archive.json` | `plan_writers_archive` (joins the captured Texas stories), `build_writers_archive` | **no** — its own item shape ([docs/DATA_SCHEMA.md](../docs/DATA_SCHEMA.md)) |
| `pdfs.json` (the crawler) | `pdfs.json` | `PDF.official_only(simple(ctx, "pdfs", ("pdf",)), …)`, then `pdf_curate.curate` | yes |
| `editorial.json` | `editorial.json` | `simple(ctx, "editorial")` | yes |
| `weekly_open.json` | `weekly_open.json` | `weekly_open_items` | yes |
| `shop.json` | `shop.json` | `build_shop` | **no** — only the fields in its row dictionaries |
| `meetings.json` | `meetings.json` | `meetings.build_site` | **no** — `EXTRA_KEYS` / `SITE_KEYS` in `meetings.py` |
| `audio_project.json` | `audio_project.json` | `build_audio_project` | **no** — `AUDIO_FIELDS` |
| `quote.json` | `quote.json` | `quote.build_site` | **no** — its row and `SITE_KEYS` in `quote.py` |

### 6.2 Hide one item everywhere

There is no setting to hide one story, document, video, episode or Instagram post. But `simple()` in
`scripts/sync/build_data.py` already has a hook, `skip=` — the same one that keeps closed Google
Forms off the site (`skip=closed_form`). An item left out there disappears from its page, the home page, What's New
and the feed, search, the monthly digest and the booth display. The robot still collects it, so removing your line
brings it back.

1. In `scripts/sync/build_data.py`, near the top (search for `NEVER_NEW_KINDS =`), add:

   ```python
   # Items the committee asked to leave off the site (ids as in data/raw/*.json).
   HIDDEN_IDS = {
       "yt:AbCdEfGhIjK",              # a video: "yt:" + the part after watch?v=
       "ig:ABCdef12345",              # an Instagram post: "ig:" + the code after /p/
       "gv:2026-10:some-story",       # a magazine story
   }


   def hidden(it: dict) -> bool:
       return it.get("id") in HIDDEN_IDS
   ```

2. In `main`, find the block that starts `cols: dict[str, list[dict]] = {` (search for
   `"videos": simple(ctx`) and add `skip=hidden` where you need it:

   ```python
               "videos": simple(ctx, "youtube", ("video",), skip=hidden),
               "episodes": simple(ctx, "podcasts", ("episode",), skip=hidden),
               "instagram": simple(ctx, "instagram", ("post",), skip=hidden),
               "articles": simple(ctx, "articles", ("article",), skip=hidden),
               "pdfs": PDF.official_only(simple(ctx, "pdfs", ("pdf",), skip=hidden), PDF.official_hosts(ctx.cfg)),
               "editorial": simple(ctx, "editorial", skip=hidden),
   ```

Variations: hide every episode of a show you removed from the settings with
`skip=lambda it: it.get("category") == "lvp"` on the episodes line (the show's `key`); hide a document
by its file name with `skip=lambda it: (it.get("extra") or {}).get("filename") == "Old_Flyer.pdf"`.

**Find an item's id** in `data/raw/<source>.json` (search for its title on github.com).

**What happens:** the quick rebuild after you save runs `build_data`, and its log says, for example,
`youtube: 1 item(s) left out on purpose` (checked by running `simple()` on the October 2 videos with one id
hidden: 531 → 530).

### 6.3 Show a field that is already in the data

Example: the **Online exclusive** mark. `articles.py` already saves `extra.online_exclusive`, and the
home page spotlight and `/published/` show it — the story lists on `/read/` do not. Two edits:

1. `eleventy/filters/read.js` → function `articleView`: in the object it returns, add

   ```js
       exclusive: e.online_exclusive === true,
   ```

2. `src/pages/read.njk` → macro `articleRow`: add `or a.exclusive` to the line
   `{% if a.author or (a.isNew and showNew) or a.free != null or mtInMeta %}`, and next to the "Free to
   read" / "Subscriber story" badges add

   ```njk
         {% if a.exclusive %}<span class="badge-vine">{{ "published.online_exclusive" | t(lang) }}</span>{% endif %}
   ```

The label already exists in both languages (`src/_i18n/published.json` → `published.online_exclusive`:
"Online exclusive" / "Exclusiva en línea"). A brand-new label goes into a `src/_i18n/*.json` file with
both languages: a key that is missing altogether stops the build (the live site keeps its last
version), and a key with only one language turns the Code check red (see [Translations](translations.md)).
Shows on `/read/` and `/es/read/` after the quick rebuild — on the rows the page draws itself (the
current issues and the first 8 archive issues). The older issues behind "Load older issues" come from
`/read-archive.json` ([`src/pages/read-archive.11ty.js`](../src/pages/read-archive.11ty.js), drawn by
`src/assets/js/read.js`) and would need the same mark added there.

### 6.4 Show a field the site file leaves out

Example: the store's own offer sentence ("Offer good for this title: SEPT. 15 thru OCt. 14 Only.").
`shop.py` already saves it as `extra.offer_text`, but `build_shop` copies only the fields it lists.

1. `scripts/sync/build_data.py` → `build_shop`: in the Book of the Month `row = {…}` (search for
   `"month_label": ex.get("month_label"), "blurb": blurb,`) add

   ```python
                  "offer_text": ex.get("offer_text"),
   ```

2. `eleventy/filters/shop.js` → function `botmView`: add to the object it returns

   ```js
       offerText: b.offer_text || "",
   ```

3. `src/pages/shop.njk` → macro `botmCard`, for example under the blurb (search for `{% if b.blurb %}`):

   ```njk
   {% if b.offerText %}<p class="mt-2 text-xs text-muted" lang="{{ b.itemLang }}">{{ b.offerText }}</p>{% endif %}
   ```

The sentence stays in the store's language (it is not registered for translation). The same pattern
applies to the other "listed fields only" files: meetings (`EXTRA_KEYS` + `SITE_KEYS` in
`meetings.py`), record your story (`AUDIO_FIELDS` in `build_data.py`) and the quote (the row in
`quote.build_site` + `SITE_KEYS`; `tests/test_quote.py` checks that the two match).

### 6.5 Add a brand-new field from the source

Example: keep each podcast episode's one-line subtitle (`<itunes:subtitle>` in the feed — the feed
reader gives it as `e.get("subtitle")`; checked).

1. `scripts/sync/podcasts.py` → `build_items`: in `extra = {` add

   ```python
                   "subtitle": clean_text(e.get("subtitle") or "") or None,
   ```

   (The `make_item(…)` call right after the dictionary leaves out `None` values, so an episode
   without one stays clean.)
2. Nothing to do in `build_data.py`: `prep()` copies every `extra` field into
   `data/site/episodes.json`. To have it machine-translated too, add it to `LABEL_FIELDS` (search for
   `LABEL_FIELDS = {`):

   ```python
   LABEL_FIELDS = {"article": ("section", "topic", "issue_theme", "department"), "episode": ("subtitle",)}
   ```

   The translation then lands in `i18n.subtitle` on each episode.
3. Display. `/listen/` draws its first 24 rows on the server and the rest in the browser from
   `/episodes-index.json`, so both need it:
   - `eleventy/filters/media.js` → `epCompact`: add `st: tx(item, "subtitle", lang),` (it picks the
     page-language translation, else the original);
   - `src/pages/listen.njk` → macro `epRow`: add `{%- set st = e | tx("subtitle", lang) -%}` to the
     `set` lines at its top, then under the title
     `<p class="text-sm text-muted"{% if not srv %} x-show="ep.st" x-text="ep.st"{% endif %}>{% if srv %}{{ st }}{% endif %}</p>`.
4. Try it without saving anything: `python -m scripts.sync.podcasts --dry-run`. Add a test in
   `tests/test_sync_pipeline.py` and describe the field in [`docs/DATA_SCHEMA.md`](../docs/DATA_SCHEMA.md).

> The merge rule matters for new fields: a value that is empty today keeps yesterday's value. If
> "empty" must win (the source really removed it), re-apply the fresh value after the merge, as
> `crawl.py` → `reapply_fresh_fields` and the playlists in `youtube.py` do.

**Where each module builds its items** (add your field to the item's `extra` there):

| Source | Build the field in | Show it in |
|---|---|---|
| Magazine stories | `articles.py` → `parse_hub` / `parse_archive` / `parse_article`, then `build_item` | `read.js` → `articleView`; `read.njk`; `home.js` |
| Documents | `crawl.py` → `build_item` (and `reapply_fresh_fields`) | `library.js` → `libraryDocs`; `library.njk` |
| Podcasts | `podcasts.py` → `build_items` (show-level: `show_meta`) | `media.js` → `epCompact`; `listen.njk` |
| YouTube | `youtube.py` → `build_item` | `media.js` → `videoCompact`; `watch.njk` |
| Instagram | `instagram.py` → `build_item` | `media.js` (`mediaIg*` filters); `instagram.njk` |
| Shop | `shop.py` → `parse_botm` / `parse_product` / `parse_listing` / `parse_specialty`, then `collect_*` | `build_shop` row → `shop.js`; `shop.njk` |
| Daily quote | `quote.py` → `parse_quote`, `entry`, the item in `collect` | `quote.build_site` row + `SITE_KEYS` → `home.js` → `homeDailyQuotes` |
| Editorial themes | `editorial.py` → `parse_gv` / `parse_lv` / `parse_lv_themes`, then `rows_to_items` | `read.js` → `editorialFor` |
| Weekly open meetings | `weekly_open.py` → `parse_page` + `build_item`; `lavina_item` | `committee.js` → `cmWeeklyAll`; `meetings.njk` |
| Record your story | `audio_project.py` → `parse_gv` / `parse_lv` | `AUDIO_FIELDS` → `contribute.njk` |
| Grapevine meetings | `meetings.py` → `to_record` + `EXTRA_KEYS` | `SITE_KEYS` → `committee.js` → `cmGvMeetings`; `meetings.njk` |

### 6.6 Add a whole new source

Follow the checklist in [`docs/OPERATIONS.md`](../docs/OPERATIONS.md), section *Adding a new source*: a
module in `scripts/sync/` (with `--dry-run`, `make_item`, `merge_items`, `save_raw`, `run_module`), its
name in `MODULES` in `scripts/sync/run_all.py` (and whether quick runs read it — a source only the full update
reads also needs its settings in `SETTINGS` of `scripts/ops/push_modules.py`, so a push that changes them runs it;
`tests/test_push_modules.py` checks that the two lists agree), a status label in
`SOURCES` and a site file in `build_data.py`, the file name in `FILES` in `src/_data/db.js`, and the
fields in `docs/DATA_SCHEMA.md`. Optional: an icon in `srcIcons` on `src/pages/status.njk` and a
`community.status.src.<name>` label in `src/_i18n/community.json` (both languages) — without them the
Status page uses a plain icon and the `SOURCES` label; and step 6 of that checklist if the monthly digest
should list the new source.

### 6.7 Test your change

- The whole suite, as the Code check runs it: `python -m unittest discover -s tests`. One file:
  `python -m unittest tests.test_shop -v`.
- Try one source without writing its data file: `python -m scripts.sync.<name> --dry-run` (a few
  modules may still save new pictures under `src/assets/cache/`). Keep local runs short — the magazine
  sites ask for 5 seconds between requests and the daily run already visits them.
- A local full sync rewrites the robot's files: put them back before you commit
  (`git checkout -- data/raw data/site data/state data/translations/cache.json src/assets/cache`, and
  delete any new files it left in `src/assets/cache/`). Setting up a computer:
  [Automation and troubleshooting](automation-and-troubleshooting.md).
- After you save on GitHub, watch the **Code check** (✓ or ✗) and the **Website update** run.

| Source | Tests |
|---|---|
| Magazine stories, writer's place | `test_spotlight.py`, `test_sync_pipeline.py` |
| Document Library | `test_library_curation.py`, `test_crawl_media.py`, `test_sync_pipeline.py` |
| Podcasts, Instagram, weekly open meetings | `test_sync_pipeline.py` |
| YouTube | `test_crawl_media.py`, `test_sync_pipeline.py` |
| Shop, price changes | `test_shop.py`, `test_price_changes.py` |
| Daily quote | `test_quote.py`, `test_morning.py`, `test_run_wiring.py` |
| Editorial themes | `test_editorial.py` |
| Record your story | `test_audio_project.py` |
| Grapevine meetings | `test_meetings.py` |
| Committee meeting | `test_build_times.py`, `test_recurring_events.py`, `test_events_feeds.py` |
| Texas writers archive | `test_writers_archive.py`, `test_published_archive.py` |
| What a push also runs | `test_push_modules.py` |

---

## 7. Troubleshooting

**Where problems are reported**

1. **`/status/`** — a badge per source; a failed source shows a calm note for visitors and, folded
   away, *Technical details* with the real error.
2. **The run summary** (*Actions → Website update →* a run): the *Content sources* table (a
   **PROBLEM** row per failing source), the **Daily quote** line, the **PDF crawl** line, **Notes**
   (small problems of sources that still updated — only worth a look if the same note repeats for a
   week), **Writers archive**, **Settings problems**, **New podcast feeds found**, **Reminders**, and "Not
   updating for 7+ days". A source no run has even tried for 3 days shows **NOT CHECKED**.
3. **Yellow ⚠ marks** on the run page — the site was still published, with that source's old items.
4. **The GitHub issue "A content source has stopped updating"** — opened when a source has failed for
   7 days in a row; it closes itself when the source works again.
5. **The run's log** (step *Sync sources and translate*) — for quiet things that appear nowhere else: the La
   Viña weekly open card being left out, a `specialty_skip` typo, "item(s) left out on purpose".

| What you see | Likely cause | What to do |
|---|---|---|
| A source shows **Failed** for a day | the site was down, slow, or turned the robot away | Nothing: its old items stay and the next run tries again. After 7 days the issue opens. |
| A source shows **Delayed** | it has not succeeded for 3+ days — often only quick runs happened | *Actions*: check that the full daily run ran; run it by hand (all boxes empty). |
| My settings change did not show | that source is read only by the full run (the magazine stories, the shop, the document search); or the save's run could not compare `config/site.yml` with its earlier copy (a blue notice *Push run* says so) | See the table in [4](#4-what-happens-next-which-run-how-long); wait, or run the workflow by hand. |
| Nothing ran after I saved | the commit message contained `[skip ci]`, or the file is under `data/` or `docs/` | Save a small change again with a plain message. |
| Red ✗ right after editing `config/site.yml` | a YAML typo (indentation, a missing quote) | The red step shows the line. Fix it, or undo the edit from the file's *History*. The live site keeps its last version meanwhile. |
| YouTube Note "details stopped: … Sign in to confirm you're not a bot" | YouTube blocks the detail tool on GitHub's computers | Nothing: the feeds keep the list current. |
| Instagram failed: "No new posts for @… (…). Posts already on the site are kept." | Instagram refused the public pages that day | Usually temporary. For good: the official API secrets ([3.6](#36-instagram-posts-and-posts-you-add-by-hand)). |
| "No posts fetched … the automatic check is switched off (sources.instagram.anonymous: false) and IG_ACCESS_TOKEN / IG_BUSINESS_ID are not set." | `anonymous: false` without the secrets | Add the secrets (NETA65 account) or set `anonymous: true`; list posts by hand meanwhile. |
| A post added to `content/instagram.yml` is missing | the save's run is still going, Instagram turned the robot away in that run, or the entry has a mistake | Look at the run; check **Notes** for "no Instagram post link found" or "YAML error"; otherwise the next full run reads the list again. |
| A writers archive file was not used | see the run summary's **Writers archive** lines (**CSV file to fix**) | [Writers archive §13](writers-archive.md#13-troubleshooting) |
| My Instagram caption is not shown | Instagram's own caption wins while the robot still reads that post | Expected — see the note in [3.6](#36-instagram-posts-and-posts-you-add-by-hand). |
| On the 1st, the new issue has titles but few details | the morning refresh reads only the current-issue pages | The full run that day fills in the rest. |
| Stories: "no articles found on the magazine hub (site down or layout changed)" | the current-issue page is down or moved | Wait a day; if it lasts, check `magazine_hub`. |
| Stories: "archive page … repeats earlier pages" | the archive's page links are broken on the magazine's site | Nothing; the robot stops safely and keeps what it has. |
| "lv-themes: no yearly themes document linked from … — moved or renamed?" | La Viña moved or renamed its themes document | Adjust `themes_page` / `themes_link` ([3.10](#310-editorial-themes-and-deadlines)). |
| "… only N themes found (had M) — kept the previous …" | a page suddenly shows far fewer themes | Usually a hiccup. If the page really changed, a maintainer can accept it once with `python -m scripts.sync.editorial --force`. |
| Shop: "page does not look like the Book of the Month page (maintenance? redirect?)" | the store is under maintenance, or the page moved | Wait a day; if it lasts, check `botm`. |
| The holiday cards are gone from `/shop/` | out of season | Nothing; they come back by themselves. |
| An item still shows after `specialty_skip` | specialty items are read weekly | Wait up to about 7 days ([3.7](#37-shop-book-of-the-month-prices-specialty-items)). |
| ⚠ "Settings problem (price_changes)" | a mistake in a `price_changes:` block | The message says which key; fix it and save ([3.8](#38-announce-new-prices)). |
| The committee meeting shows on the wrong day | `weekday` or `week_of_month` was not understood → silently Wednesday / 3rd | Use a plain day name and a number ([3.14](#314-the-committee-meeting)). |
| ⚠ "Settings problem (meeting)": skip date … | a skip date that is not a meeting day or not a date | Fix the date as the message says. |
| La Viña's weekly open card disappeared | `day`, `time` or `timezone` not understood, or `enabled: false` | Fix the block ([3.11](#311-weekly-open-meetings)); the run's log names the problem. |
| Weekly open: "fetch failed: https://www.aagrapevine.org/grapevine-weekly-open" | the page is down or moved | Wait a day; if it lasts, change `sources.grapevine.weekly_open`. |
| Grapevine meetings Note "… did not answer" or "not JSON" | one office's list could not be read | Nothing; its meetings stay. A Note "the key from … was not accepted" (or "no key was accepted for its meeting list …") → the office has a new key ([3.13](#313-grapevine-meetings-from-the-intergroup-lists)). |
| Today's quote is missing at 5:30 AM | the magazine published late, or the morning alarm did not ring | The Morning check asks until 7 AM; the card shows "Yesterday" meanwhile. See [Automation and troubleshooting](automation-and-troubleshooting.md). |
| Quote: "gv: no quote of the day on https://…" | the home page changed | Check `quote_page`; tell whoever helps with the code if it lasts. |
| Podcasts failed with "<key>: …" | one show's feed did not answer | The other shows still update; check that show's `feed`. |
| **New podcast feeds found** in the summary | a magazine site links a show that is not in your settings | Add a block if you want it ([3.4](#34-podcasts)); otherwise ignore it. |
| The Library looks small | normal: each official document once | Check the **PDF crawl** line; if every known page is crawled, it is complete. |
| A document has a poor title | its link text and file name say little | `TITLE_OVERRIDES`, or `overrides.yml` for one language ([3.3](#33-the-document-library-the-crawler)). |
| `/status/` says `data/raw/<x>.json` "was unreadable" | someone edited a robot file by hand | Restore the file from its history on GitHub to keep the first-seen dates. |

---

## 8. Good practice and AA principles

- **Respect AA Grapevine, Inc.'s work.** The site shows titles, the publishers' own public teasers and
  links back — never a story's text. Prices come only from the stores, or from AA Grapevine's own
  announcement. Every purchase links to the official stores.
- **Anonymity.** The site shows only what the official sources publish (first name and last initial).
  Never add a full name or anything that identifies a member — not in a hand-written caption, a
  translation fix or a title. The robot never reads a document's author details, and never copies a
  local meeting's contacts, phone numbers, e-mails or Zoom links.
- **Attraction rather than promotion.** Keep hand-written captions, titles and translations plain and
  factual, in the magazines' own words — no "best", no hype.
- **Official sources only.** Documents only from `library.official_hosts`; hand-added Instagram posts
  only from the two official accounts; shows and channels only the official ones.
- **Everything here is public.** The repository is public: `config/site.yml`, `content/instagram.yml`
  and `overrides.yml` can be read by anyone. `feed_obf` only hides a key from casual reading. Real
  secrets go in GitHub secrets (the NETA65 account).
- **Be a polite guest.** The robot waits 5 seconds between requests to the magazine sites and obeys
  their robots.txt. Keep your own test runs short (`--dry-run`), and never try to get around a site's
  bot protection.
- **Visitor wording.** Pages say "document", never "PDF", and do not describe how the sites are read.

---

## 9. See also

- [How-to guide index](README.md)
- [The Drive panel folder](drive-panel-folder.md) · [File types](file-types.md)
- [Flyers and events](flyers-and-events.md) — monthly events, outside calendars, the GV/LV event calendars
- [Bulletin](bulletin.md) — e.g. the post that goes with a price change
- [Writers archive](writers-archive.md) — the archive files in `content/archive/` and the Texas writers archive
- [Photos, slides and reports](photos-slides-reports.md)
- [Booth display](booth.md) — the display for the committee's table at assemblies; it shows some of these sources'
  items of the day (section 5)
- [Presentations](presentations.md) — they show live themes, prices and meetings from these sources
- [Settings](settings.md) — `config/site.yml` section by section
- [Translations](translations.md) — `overrides.yml`, `glossary.yml`, button texts in `src/_i18n/`
- [E-mail and alerts](email-and-alerts.md) — the monthly digest, the morning alarm, the stale-source issue
- [Pages and code](pages-and-code.md) — every page and its template
- [Automation and troubleshooting](automation-and-troubleshooting.md) — runs, the run summary, `/status/`, working on a computer
- In the repository: [`config/site.yml`](../config/site.yml), [`content/instagram.yml`](../content/instagram.yml),
  [`data/translations/overrides.yml`](../data/translations/overrides.yml), the modules in
  [`scripts/sync/`](../scripts/sync/) (each one's opening comment is its full reference),
  [`docs/OPERATIONS.md`](../docs/OPERATIONS.md) (*Sync modules*, *Adding a new source*),
  [`docs/DATA_SCHEMA.md`](../docs/DATA_SCHEMA.md), and the [README](../README.md) sections 1, 7, 8, 9, 10 and 15.
