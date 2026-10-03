# Pages and code: a map of the website's code

This guide is for whoever wants to change how the website looks or works. It lists every page, the
file behind it, the data it reads and its script and style. Then it shows exactly where to change a
word, a colour, a menu or a whole page. You can do most of it on github.com. A few recipes are easier
on your own computer (section 3).

> **Before you start.** The repository is public. Everything you commit can be read by anyone. Never
> commit passwords, private e-mail addresses, phone numbers or the names of members.

**Contents**

1. [What this is](#1-what-this-is)
2. [Quick start: change something you see on a page](#2-quick-start-change-something-you-see-on-a-page)
3. [Run the site on your own computer](#3-run-the-site-on-your-own-computer)
4. [How the site is put together](#4-how-the-site-is-put-together)
5. [Every page: address, template, data, script, style](#5-every-page-address-template-data-script-style)
6. [The layout, partials and macros](#6-the-layout-partials-and-macros)
7. [eleventy.config.js and the filters](#7-eleventyconfigjs-and-the-filters)
8. [Global data (src/_data)](#8-global-data-src_data)
9. [The two languages and the /aagrapevine/ path prefix](#9-the-two-languages-and-the-aagrapevine-path-prefix)
10. [Styles: main.css, area files and theme tokens](#10-styles-maincss-area-files-and-theme-tokens)
11. [Scripts (src/assets/js)](#11-scripts-srcassetsjs)
12. [Recipes](#12-recipes)
13. [The installable app and offline use, in short](#13-the-installable-app-and-offline-use-in-short)
14. [What happens after you push](#14-what-happens-after-you-push)
15. [Check your change on the live site](#15-check-your-change-on-the-live-site)
16. [Going further: filters, data files and tests](#16-going-further-filters-data-files-and-tests)
17. [Troubleshooting](#17-troubleshooting)
18. [Good practice and AA principles](#18-good-practice-and-aa-principles)
19. [See also](#19-see-also)

---

## 1. What this is

The website is a static site. A tool called **Eleventy** builds it from three kinds of input: page
templates in `src/`, settings in `config/`, and content files in `data/site/` that the daily sync
writes. Every page template is built twice: English at `/x/` and Spanish at `/es/x/`. GitHub Actions
builds the site and publishes it to GitHub Pages at <https://neta65.github.io/aagrapevine/>.

**Where it shows:** everywhere. Every page in both languages, and the files the build writes next to
them: `/feed.xml` (RSS), `/events.ics` (calendar feed), `/sitemap.xml`, `/search-index.json` (site
search), `/manifest.webmanifest` and `/sw.js` (the installable app), `/build.json` (read by the
Morning check) and `/about/booth.json` (the booth display's show).

> **Who can do what.** The GitHub login on the owner's PC (MKP715) has **write** access. It can
> edit any file, commit to `main` and start a workflow by hand (Actions → Run workflow). Repository
> **settings** (GitHub Pages, a custom domain, secrets and variables, Actions permissions) need the **NETA65**
> (admin) account. Nothing in this guide needs the admin account, except moving the site to a custom
> domain.

---

## 2. Quick start: change something you see on a page

Most changes are a word or a sentence. Example: change the button "Subscribe to calendar" on the
Events page.

1. Open <https://neta65.github.io/aagrapevine/events/> and copy the exact words:
   `Subscribe to calendar`.
2. On github.com, open the repository **NETA65/aagrapevine**. In the search box type
   `"Subscribe to calendar" path:src/_i18n` and press Enter. It finds `src/_i18n/committee.json`:
   ```json
   "committee.events.subscribe_btn": {
     "en": "Subscribe to calendar",
     "es": "Suscribirse al calendario"
   },
   ```
3. Open the file, click the pencil (**Edit**) and change **both** texts. Keep the quotes and the
   comma:
   ```json
   "committee.events.subscribe_btn": {
     "en": "Add our calendar",
     "es": "Agrega nuestro calendario"
   },
   ```
4. Click **Commit changes** (to the `main` branch).
5. Open the **Actions** tab. **Update & Deploy** starts by itself (and **Code check** next to it).
   A few minutes later the new words are on `/events/` and `/es/events/`. A page may take up to about
   10 more minutes to show the change everywhere.

The words are not in `src/_i18n`? Then they come from somewhere else:

| The words are… | They live in | Guide |
|---|---|---|
| A button, heading, label or sentence of the site itself | `src/_i18n/<area>.json` | [12.1](#121-change-a-text-ui-words) and [Translations](translations.md) |
| The committee name, contact e-mail, meeting day and time, Zoom details, official links | `config/site.yml` | [Settings](settings.md) |
| A GVR / RLV 101 session, a milestone of the timeline on `/about/`, a "Put this issue to work" idea, a Tracker category | `config/orientation.yml`, `config/history.yml`, `config/carry.yml`, `config/expenses.yml` (each with `en` and `es`) | [Settings](settings.md) |
| An event, a flyer, a bulletin post | the Drive panel folder, `content/events/`, `content/bulletin/` | [Flyers and events](flyers-and-events.md), [Bulletin](bulletin.md) |
| A story, video, episode or PDF title, or its machine translation | the outside sources; fix a translation in `data/translations/overrides.yml` | [Automatic sources](automatic-sources.md), [Translations](translations.md) |
| "Grapevine / La Viña" next to the logo | written into `src/_includes/partials/header.njk` and `footer.njk` | [6.3](#63-partials-on-every-page) |
| A slide of a web presentation | `config/presentations/<id>.yml` | [Presentations](presentations.md) |
| A slide of the booth display (a quiz, fact, quote, message …) or a booth photo's caption | `content/booth/booth.csv`; the file names in the Drive booth folder | [Booth display](booth.md) |

---

## 3. Run the site on your own computer

You need **Node.js 20 or newer** (22 LTS is what GitHub uses) and **Git**. Python is only needed for
the tests (section 16). You do not need the content sync: the build reads the content that is already
committed in `data/site/`.

**First time** (PowerShell, in the folder where you keep your projects):

```powershell
git clone https://github.com/NETA65/aagrapevine.git
cd aagrapevine
npm ci            # installs Eleventy, Tailwind and the other site tools into node_modules/
```

**Every time:**

```powershell
git pull                      # the newest code and content
npx @11ty/eleventy --serve    # the same as: npm start
```

Open <http://localhost:8080/> (Spanish: <http://localhost:8080/es/>). The page reloads by itself when
you save a template, a string file (`src/_i18n/`), a setting (`config/`) or a content file
(`data/site/`). Stop the server with **Ctrl+C**. If port 8080 is busy, the server takes the next one:
use the address it prints. Run `npm ci` again after `package-lock.json` changes (for example after a
"chore(deps)" update).

**Useful switches** (in PowerShell `$env:NAME = "value"` stays set for that window;
`Remove-Item Env:NAME` clears it):

| Command | What it does | Use it when |
|---|---|---|
| `$env:I18N_STRICT = "1"; npx @11ty/eleventy` | Stops the build on a missing string, or on a problem in `config/carry.yml`, `orientation.yml`, `history.yml`, `expenses.yml` or a presentation deck. This is how GitHub builds. Without it a missing string shows its raw key (for example `nav.faq`) on the page. | Before you push a template or string change |
| `$env:ONLY = "events"; npx @11ty/eleventy --serve` | Builds only the `src/pages/` files whose **name starts with** one of the words. `events` builds `events.njk` and `events-ics.11ty.js`; `"library,search"` builds both pages. Much faster, but links to the other pages say "not found". | You work on one page |
| `$env:PATH_PREFIX = "/aagrapevine/"; npx @11ty/eleventy` | Builds with the GitHub Pages folder in every link, like the live site. With `--serve` the site then opens at <http://localhost:8080/aagrapevine/>. | You changed how links are written |
| `$env:COMMITTEE_EMPTY = "1"` (also `HOME_EMPTY`, `LIB_EMPTY`, `READ_EMPTY`, `MEDIA_EMPTY`, `PW_EMPTY`) | Shows the committee pages (or the home page, Library, Read pages, media pages, Published writers) as if there were no content: the "nothing here yet" cards. | You change an empty state |
| `$env:MONTHLY_NOW = "2026-11-01"` | Pretends today is that day for the monthly toolkit and the digest. | You preview next month |

> **Note:** `I18N_STRICT` (and the `…_EMPTY` switches) are on for **any** value, even `"0"`. To turn
> one off, remove it: `Remove-Item Env:I18N_STRICT`.

> **Note:** in **Git Bash** write `MSYS_NO_PATHCONV=1 PATH_PREFIX=/aagrapevine/ npx @11ty/eleventy`.
> Without `MSYS_NO_PATHCONV=1`, Git Bash turns `/aagrapevine/` into a Windows folder path.

> **Note:** saving only a `.css` file does not start a rebuild while the server runs. Eleventy watches
> templates, `src/_includes`, `src/_data`, `src/_i18n`, `config/`, `data/site/` and the copied files,
> not the stylesheets. Save any template, or stop and start the server, to see a style change. After a
> change to `eleventy.config.js` or a file in `eleventy/filters/`, always stop (Ctrl+C) and start the
> server again, so the new code is loaded.

> **Note:** the built site installs a service worker on `localhost` too, so your browser keeps copies
> of the pages you opened. For a clean first visit: browser DevTools → Application → Storage →
> **Clear site data**.

The build writes everything into the folder `_site/`. Git ignores it. Never edit it: it is rebuilt
every time.

---

## 4. How the site is put together

```text
 INPUTS                              THE BUILD  (npx @11ty/eleventy)              OUTPUT  _site/  →  GitHub Pages
 config/*.yml       settings         src/_data/*.js      global data              /  and  /es/   (every page twice)
 data/site/*.json   the daily sync   src/pages/          one template per page    /feed.xml  /events.ics  /sitemap.xml
 src/_i18n/*.json   all UI words     src/_includes/      layout, partials, macros /search-index.json  /sw.js  /build.json
 content/bulletin/  attachments      eleventy/filters/   view models              /bulletin/files/…
                                     Tailwind, after the build → main.css          /assets/css/main.css, js, img, fonts
```

- **The build never fetches anything.** All content comes from the committed JSON in `data/site/`
  (the daily sync writes it) and the YAML in `config/`. A source that is down never breaks the build.
  The build stops only on a code error, a missing UI string or a bad config file (on GitHub, where
  `I18N_STRICT=1` is always on).
- **One template, two pages.** Every page template "paginates" over the list `languages`
  (`["en", "es"]`, in `src/_data/languages.js`). The variable `lang` is `"en"` on the first page and
  `"es"` on the second. (The month and session pages paginate over their own lists, which hold both
  languages: `monthlyPages`, `orientation.pages`.) The `permalink` line decides the two addresses:

  ```yaml
  ---
  pagination: { data: languages, size: 1, alias: lang }
  permalink: "{{ '/' if lang == 'en' else '/es/' }}events/index.html"
  layout: layouts/base.njk
  pageKey: events
  titleKey: nav.events
  descKey: committee.events.meta_desc
  pageScripts: ["/assets/js/committee.js"]
  ---
  ```

  This is the real front matter of `src/pages/events.njk`. It writes `/events/` and `/es/events/`.
  Spanish addresses keep the English word (`/es/events/`, never `/es/eventos/`).

**Folder map**

| Folder or file | What is in it | Edit it? |
|---|---|---|
| `src/pages/` | One template per page (`*.njk`) and the generators of non-HTML files (`*.11ty.js`) | Yes |
| `src/_includes/layouts/base.njk` | The frame of every page: `<head>`, header, footer, scripts | Carefully |
| `src/_includes/partials/` | `header.njk`, `footer.njk`, `comfort-panel.njk` (the "Aa" panel), `lang-banner.njk` | Yes |
| `src/_includes/macros/` | Reusable building blocks: `ui.njk` (hero, section heads, cards…), `media.njk`, `monthly.njk`, `orientation.njk`, `presentations.njk`, `booth.njk` | Yes |
| `src/_includes/icons/` | Our own SVG icons (grapes, instagram, safari-menu, spotify, youtube) | Add new ones here |
| `src/_includes/pwa/sw-core.js` | The service worker's logic | Rarely |
| `src/_data/` | Global data every template can read (`site`, `nav`, `db`, `meeting`, …) | Yes |
| `src/_i18n/` | Every button, heading and sentence, in English and Spanish (one JSON file per area) | Yes, often |
| `src/assets/css/` | `main.css` (design system) and `areas/*.css` (one file per page area) | Yes |
| `src/assets/js/` | The browser scripts | Yes |
| `src/assets/img/` | Logo, app icons, share pictures, app screenshots | Yes |
| `src/assets/cache/` | Thumbnails the daily sync downloads | No (the bot writes it) |
| `eleventy.config.js` | Eleventy's settings, the shared filters, the Markdown rules, Tailwind | Carefully |
| `eleventy/filters/*.js` | One file of filters per page area (the "view models") | Yes |
| `eleventy/script-json.js` | The safe way to put JSON inside a `<script>` | Rarely |
| `config/` | Settings: `site.yml`, `carry.yml`, `orientation.yml`, `history.yml`, `expenses.yml`, `presentations/` | Yes ([Settings](settings.md)) |
| `content/` | Hand-written events and bulletin posts, `instagram.yml`, the booth display's slides (`booth/booth.csv`) | Yes ([Flyers and events](flyers-and-events.md), [Bulletin](bulletin.md), [Booth display](booth.md)) |
| `data/site/*.json` | The content the sync writes (events, articles, videos, Drive files, status…) | No (the bot writes it) |
| `data/translations/` | Translation fixes (`overrides.yml`, `glossary.yml`) | Yes ([Translations](translations.md)) |
| `tests/` | Python tests (some run the site's JavaScript with Node) | When you change code |
| `_site/`, `node_modules/`, `.cache/` | Built site, installed tools, downloads (the booth display's saved photos and videos, the translation models) | No (generated, not in Git) |

---

## 5. Every page: address, template, data, script, style

Every page below exists in English and Spanish: the Spanish address is `/es/` plus the same path
(`/meetings/` → `/es/meetings/`). The live address is `https://neta65.github.io/aagrapevine` plus the
path. Every page also loads the shared scripts (`app.js`, `install-core.js`, `pwa.js`,
`hero-canvas.js`, Alpine) and the one stylesheet `main.css`. `main.css` imports **all** the area
files, so there is no per-page stylesheet to link: "CSS area" says which file holds the page's own
styles.

### 5.1 The pages

| Page (English address) | Template in `src/pages/` | `pageKey` | Main data | Own scripts (`pageScripts`) | CSS area |
|---|---|---|---|---|---|
| Home `/` | `index.njk` | `home` | everything, through `db \| homeData`; `meeting`; `site` | `lite-yt-embed.js`, `home.js`, `shop.js` (style `lite-yt-embed.css`) | `home.css` |
| What's new `/whats-new/` | `whats-new.njk` | `whats-new` | `db.whatsnew` | `community.js` | `community.css` |
| Read `/read/` | `read.njk` | `read` | `db.articles`, `db.spotlight` | `read.js` | `read.css` |
| Listen `/listen/` | `listen.njk` | `listen` | `db.episodes`, `db.weekly_open`, `site.listen` | `lite-yt-embed.js`, `media.js` (style `lite-yt-embed.css`) | `media.css` |
| Watch `/watch/` | `watch.njk` | `watch` | `db.videos`, `site.watch` | `lite-yt-embed.js`, `media.js` (style `lite-yt-embed.css`) | `media.css` |
| Library `/library/` | `library.njk` | `library` | `db.pdfs` + `db.drive` (filter `libDocs`) | `minisearch.js`, `search.js`, `library.js` | `library.css` |
| Shop `/shop/` | `shop.njk` | `shop` | `db.shop`, `db.pdfs`, `db.articles`, `db.drive` | `shop.js` | `read.css` + `shop.css` |
| GVR / RLV corner `/gvr/` | `gvr.njk` | `gvr` | `db.pdfs`, Library collections, this month (`mpMonths`), `meeting`, `orientation` | `read.js` | `read.css` |
| GVR / RLV 101 `/orientation/` | `orientation.njk` | `orientation` | `orientation` (config/orientation.yml), `presentations` (config/presentations/), `db.drive` | `orientation.js`, `presentations-core.js`, `presentations.js` | `orientation.css` + `presentations.css` |
| One session `/orientation/<id>/` (6 today) | `orientation-lesson.njk` | `orientation` | one lesson of `orientation` | `orientation.js` | `orientation.css` |
| Monthly toolkit `/monthly/` | `monthly.njk` | `monthly` | `db \| mpMonths`, `carry`, `db \| rpModel` (the district report at `#report`) | `monthly.js`, `report.js` | `monthly.css` + `report.css` |
| One month `/monthly/2026-10/` (13 months) | `monthly-month.njk` | `monthly` | `monthlyPages`, `mpMonth` | `monthly.js` | `monthly.css` |
| Monthly digest `/digest/` | `digest.njk` | `digest` | `db \| cmMonthlyDigest` (last month) | `community.js` | `community.css` |
| Share your story `/contribute/` | `contribute.njk` | `contribute` | `db.editorial`, `db.audio_project`, `db.events` (workshops), `db.drive`, `db.pdfs` | `read.js` | `read.css` |
| Published writers `/published/` | `published.njk` | `published` | `db.spotlight` (filter `pwView`), `db.editorial` | `published.js` | `published.css` |
| Meetings `/meetings/` | `meetings.njk` | `meetings` | `site.meeting`, `db.meetings`, `db.weekly_open`, `db.drive` | `committee.js` | `committee.css` |
| Events `/events/` | `events.njk` | `events` | `db.events` (filter `cmEvents`) + the meeting rule | `committee.js` | `committee.css` |
| Portfolio `/portfolio/` | `portfolio.njk` | `portfolio` | `db.drive` (filter `cmDocTabs`), `presentations.decks` | `committee.js` | `committee.css` |
| Photos `/photos/` | `photos.njk` | `photos` | `db.drive` (filter `cmAlbums`), `db.events` | `glightbox.min.js`, `committee.js` (style `glightbox.min.css`) | `committee.css` |
| Bulletin `/bulletin/` | `bulletin.njk` | `bulletin` | `db.announcements` (filter `cmAnnouncements`) | `committee.js` | `committee.css` |
| Tracker `/tracker/` | `tracker.njk` | **`expenses`** | `expenses` (config/expenses.yml) | `expenses-core.js`, `expenses.js`, `committee.js` | `expenses.css` |
| Instagram `/instagram/` | `instagram.njk` | `instagram` | `db.instagram` | `media.js` | `media.css` |
| QR Post `/share/` | `share.njk` | `share` | `site.url` (QR codes), `site.meeting` | `community.js` | `community.css` |
| About us `/about/` | `about.njk` | `about` | `history` (config/history.yml), `site.about_videos`, `db.videos`; the booth display reads `/about/booth.json` in the browser | `lite-yt-embed.js` (style `lite-yt-embed.css`), `booth-core.js`, `booth.js` | `read.css` + `booth.css` |
| Accessibility `/accessibility/` | `accessibility.njk` | `accessibility` | `site.phone_access`, `site.meeting`, `db.weekly_open`, `db.shop`, `db.videos` | none | `access.css` |
| Saved pages & app `/offline/` | `offline.njk` | `offline` | `site.links`, `site.phone_access`, `db.weekly_open` | none (`pwa.js` is on every page) | `pwa.css` |
| Search `/search/` | `search.njk` | `search` | `/search-index.json` (loaded in the browser) | `minisearch.js`, `search.js` | `library.css` |
| Update status `/status/` | `status.njk` | `status` | `db.status` | `community.js` | `community.css` |
| Page not found `/404.html` | `404.njk` | `404` | `site.contact_email` | `community.js` | `community.css` |

`lite-yt-embed.js`, `minisearch.js` and `glightbox.min.js` are open-source libraries the build copies
to `/assets/vendor/`. All other scripts are in `src/assets/js/` (published at `/assets/js/`).

> **Note:** the Tracker's `pageKey` is `expenses` (its old name), while its address is `/tracker/`
> and its committee tab is called `tracker`. Menu highlighting uses the `pageKey`.

The **booth display** is a section of its own on `/about/` (`#booth`, after `#committee`; "Booth display" /
"Pantalla para la mesa" in the page's "On this page" bar). `src/_includes/macros/booth.njk` prints the section and,
at the end of the page, the player's dialog shell and its words (`#gvb-config`); `src/assets/js/booth-core.js` (the
logic, `window.GVB`) and `booth.js` (the screen) run the show; `src/assets/css/areas/booth.css` is its look; its
words are the `booth.*` keys of `src/_i18n/booth.json`. The show itself is the file `/about/booth.json` (section
5.4). The address `/about/?booth=start` opens it at once. Everything else about it — the CSV, the Drive folder, the
settings, the player — is in [Booth display](booth.md).

### 5.2 The home page, section by section

`src/pages/index.njk` is the biggest template. Every section is left out when it has no data, so the
home page never shows an empty section. All data goes through `D = db | homeData` (the `HOME_EMPTY`
switch blanks it). The filters are in `eleventy/filters/home.js`. To find a section in the template,
search for its heading id.

| Section (heading id) | English heading | What it shows | Filter |
|---|---|---|---|
| Hero (`homeHero`, `home-title`) | key `home.hero_title` | The welcome; `*words*` in that string show in gold italics. From 1024 px the next committee meeting card with a live countdown (`src/assets/js/home.js`). | `meeting.next` |
| `quote-title` | Daily quote | Today's Grapevine and La Viña quotes (at most 2 days old) | `homeDailyQuotes` |
| `ann-title` | From the committee | The 2 newest bulletin posts, pinned first; the whole post when it is at most 700 characters, else a teaser and "Read more" | `homeAnnouncements` |
| `mag-title` | The latest from Grapevine & La Viña | Latest issues, "Write for the magazines" themes, the Shop teaser | `homeLatestIssue`, `homeThemes` |
| `lw-title` | Stories you can hear and see | Podcast episodes and videos | `homeEpisodes`, `homeVideos` |
| `spot-title` | Published writers from our Area | Recent stories by Texas writers, Area 65 first | `homeSpotlight` |
| `events-title` | Upcoming events | Up to 4 coming events: the next date of each monthly series the committee holds, then the soonest one-off events (the very next committee meeting is left out: the hero shows it) | `homeEvents`, `homeEventInfo` |
| `lib-title` | Every Grapevine & La Viña document, in one place | The 6 newest documents, a search box, collection chips | `homeNewestPdfs`, `homeLibChips` |
| `ig-title` | A daily dose of the message | The 6 newest Instagram posts | `homeInstagram` |
| `drive-title` | Shared by the committee | The 6 newest committee Drive files | `homeDrive` |
| `svc-title` | Carry the message to your group | The band for GVRs, RLVs and districts | the list `svcLinks` in `index.njk` |

### 5.3 Old addresses that still work (redirect stubs)

These tiny pages send visitors to the new address. They keep the `#anchor` and `?query`, work
without JavaScript (a "meta refresh"), are marked `noindex` and are left out of the sitemap.

| Old address (and its `/es/` twin) | Goes to | Template |
|---|---|---|
| `/announcements/` | `/bulletin/` | `announcements-redirect.njk` |
| `/app/` | `/offline/#steps` | `app-redirect.njk` |
| `/districts/` | `/monthly/#report` | `districts-redirect.njk` |
| `/documents/` | `/portfolio/` | `documents-redirect.njk` |
| `/expenses/` | `/tracker/` | `expenses-redirect.njk` |
| `/meeting/` | `/meetings/` | `meeting.njk` (not the Meetings page: that is `meetings.njk`) |
| `/subscribe/` | `/shop/` | `subscribe-redirect.njk` |
| `/monthly/<one of the 3 months before this one>/` | `/monthly/` | `monthly-past.njk` |

To keep an address alive after renaming a page, copy one of these (recipe [12.5](#125-rename-a-page-and-keep-the-old-address-working)).

### 5.4 Files that are not pages

These generators live in `src/pages/` too (`robots.njk` sits in `src/`). None of them is in the
sitemap. Eleventy's HTML base plugin (section 9) rewrites links in HTML only, so each of these files
writes its addresses its own way: the feeds, the calendar and the sitemap use full addresses, the
manifest and `sw.js` add the `/aagrapevine/` folder themselves, and the JSON indexes keep plain site
paths that the page scripts complete (section 9, rule 5).

| Address | Generator | What it is | Who reads it |
|---|---|---|---|
| `/sitemap.xml` | `sitemap.11ty.js` | Every page in both languages, paired with `hreflang` | Search engines (submit it by hand in Google Search Console: on a project site `robots.txt` is not read) |
| `/robots.txt` | `src/robots.njk` | "Allow all" + the sitemap address | Search engines (only on a custom domain) |
| `/feed.xml`, `/es/feed.xml` | `feed.11ty.js` | RSS of What's New, newest 100 items | Feed readers; linked in the footer |
| `/events.ics`, `/es/events.ics` | `events-ics.11ty.js` | The calendar feed: the events of `/events/`, except those that ended more than 90 days ago | Google / Apple / Outlook calendars; the `#subscribe` card on `/events/` |
| `/search-index.json` (+ `/es/`) | `search-index.11ty.js` | Everything the site search can find | `search.js` on `/search/` |
| `/library-index.json` (+ `/es/`) | `library-index.11ty.js` | Every document | `library.js` on `/library/` |
| `/episodes-index.json`, `/videos-index.json` (+ `/es/`) | `media-index.11ty.js` | All episodes and videos | `media.js` ("Load more") |
| `/read-archive.json` (+ `/es/`) | `read-archive.11ty.js` | Older magazine issues | `read.js` ("Load older issues") |
| `/orientation/presentations/<id>.json` | `presentations-json.11ty.js` | One web presentation each | The player on `/orientation/` |
| `/about/booth.json` | `booth-json.11ty.js` (from the `booth` global, section 8, and `eleventy/filters/booth.js`) | The booth display's show, one file for both languages: the CSV's rows, the Drive booth folder's files, the day's live items (events, daily quotes, videos, podcast, story themes, prices, Books of the Month, meetings, bulletin posts), the QR codes and the problems | The booth player on `/about/` (again every 30 minutes while it plays online) |
| `/about/booth/media/<file>` | none: `eleventy.config.js` copies `.cache/booth-media/files/` when the folder exists | The booth display's saved photos, videos and sound files (downloaded just before the build by `scripts/build/booth-media.mjs`; never in Git) | The booth player, and its offline copy |
| `/manifest.webmanifest` (+ `/es/`) | `manifest.11ty.js` | App name, icons, shortcuts | Phones, when the site is installed as an app |
| `/sw.js` | `sw.11ty.js` + `src/_includes/pwa/sw-core.js` | The service worker | Browsers (offline use) |
| `/build.json` | `build-info.11ty.js` | When this build ran, which code and data | The Morning check |

---

## 6. The layout, partials and macros

### 6.1 The page frame: `src/_includes/layouts/base.njk`

Every page uses this layout. The page's front matter tells it what to do:

| Front matter key | Needed? | What it does | Example |
|---|---|---|---|
| `pagination: { data: languages, size: 1, alias: lang }` + `permalink` | Yes | Makes the English and the Spanish page | see section 4 |
| `layout: layouts/base.njk` | Yes | Uses this frame (the redirect stubs use `layout: false`) | |
| `pageKey` | Yes | Marks the current page in the header, the phone menu and the footer. Must equal the `page` of its menu entry in `src/_data/nav.js`. `home` changes the tab title; `404` adds `noindex`. | `pageKey: events` |
| `titleKey` (a string key) or `title` | Yes | The browser tab title: `<page title> · Grapevine / La Viña — NETA 65` | `titleKey: nav.events` → "Events · Grapevine / La Viña — NETA 65", Spanish "Eventos · Grapevine / La Viña — NETA 65" |
| `descKey` or `description` | Recommended | The search-engine and share description (default: the string `site.description` in `src/_i18n/common.json`, not a setting in `config/site.yml`) | `descKey: committee.events.meta_desc` |
| `pageScripts: [...]` | Optional | Extra scripts, loaded after the shared ones and before Alpine | `pageScripts: ["/assets/js/committee.js"]` |
| `pageStyles: [...]` | Optional | Extra stylesheets after `main.css` (only the vendor ones use it) | `pageStyles: ["/assets/vendor/glightbox.min.css"]` |
| `bodyClass` | Optional | Classes on `<body>` (print layouts and page-wide styles) | `bodyClass: "cm-page-digest cm-print-light"` |
| `ogImage` | Optional | Another share picture (no page uses it today) | |
| `sitemap: false`, `eleventyExcludeFromCollections: true` | Optional | Leaves the page out of the sitemap and the page lists | the 404 page and the redirect stubs |
| `eleventyComputed: { lang, title, description }` | For pages made per item | Title and description per lesson or month | `orientation-lesson.njk`, `monthly-month.njk` |

> **Note:** the comment at the top of `base.njk` also lists `noHero`. Nothing uses it: every page
> starts with the shared hero (`ui.pageHero`).

What the layout writes, in order: a small script that applies the visitor's reading settings before
the page appears; the tab title, description, canonical address and the `hreflang` links to the
other language; the RSS link; the manifest of the page language; theme colours, app and share
(Open Graph) tags, icons; the theme script (saved choice `gvlv-theme`, else the phone's own
light/dark setting) and `window.SITE = { lang, base, tz }`; the stylesheet with `?v=<build.version>`.
Then the body: a "Skip to content" link, the header, the language banner, `<main id="main">` with
the page, the footer, and the scripts (`app.js`, `install-core.js`, `pwa.js`, `hero-canvas.js`, the
`pageScripts`, and Alpine last).

### 6.2 The menus are data: `src/_data/nav.js`

The header menu, the phone menu, the footer and the site search are all built from one list. Each
entry has:

| Field | Meaning | Example |
|---|---|---|
| `key` | The label: a string key in `src/_i18n/common.json` | `"nav.events"` → Events / Eventos |
| `url` | The English address; templates add `/es` with `lurl` | `"/events/"` |
| `icon` | A Lucide icon name, or one of our own in `src/_includes/icons/` | `"calendar-days"` |
| `page` | Must equal the page's `pageKey` (for the "you are here" mark) | `"events"` |
| `descKey` | One line under the label in a dropdown; also the page's description in the site search | `"nav.events_desc"` → "Workshops, booths, assemblies & calendar" |
| `group` | Footer entries only: `stay` (the "Stay updated" column) or `site` (the bottom bar) | `"stay"` |
| `children` | A dropdown | "Get involved", "Committee" |

Where each list shows:

| List in `nav.js` | Header (from 1280 px) | Phone menu | Footer |
|---|---|---|---|
| `primary`, no `children`: What's new, Read, Listen, Watch, Library, Shop | Top links | Top links | "Explore" column |
| `primary` → "Get involved" (`nav.get_involved`): GVR / RLV corner, GVR / RLV 101, Monthly toolkit, Monthly digest, Share your story, Published writers | Dropdown | Headed list | Its own column |
| `primary` → "Committee" (`nav.committee`): Meetings, Events, Portfolio, Photos, Bulletin, Tracker | Dropdown | Headed list | Its own column |
| `footer`, `group: "stay"`: Instagram, QR Post | | "More" | "Stay updated" (after aagrapevine.org / aalavina.org, before the RSS and calendar feeds) |
| `footer`, `group: "site"`: About us, Accessibility, Saved pages & app, Search, Update status | | "More" (Search has its own button) | Bottom bar (About us is a button under the footer's blurb) |

> **Note:** a dropdown child **must** have a `descKey`. The dropdown prints `c.descKey | t(L)`; without
> one, the GitHub build stops with `Missing i18n key: undefined`.

> **Note:** entries without a `descKey` (most top links and all footer entries) take their site-search
> description from a key `search.page_desc.<page>` (most are in `src/_i18n/library.json`). `/instagram/`
> has none today, so its search result shows no description line.

Some lists are **not** built from `nav.js` and must be kept in step by hand:

| List | Where | When to update it |
|---|---|---|
| The committee pill bar under the hero of Meetings, Events, Portfolio, Photos, Bulletin, Tracker | the `pages` array inside the shortcode `committeeNav` in `eleventy/filters/committee.js` (search for `addShortcode("committeeNav"`), labels `committee.subnav.<key>` | You add or rename a Committee page |
| The 404 page's popular pages | the list `popular` at the top of `src/pages/404.njk` | You want a page suggested there |
| The home page's service band | the list `svcLinks` in `src/pages/index.njk` | You change the GVR / RLV tiles |
| App shortcuts (long-press on the app icon) | `shortcuts:` in `src/pages/manifest.11ty.js` | Rarely |
| Pages that must be in the sitemap | `REQUIRED` in `src/pages/sitemap.11ty.js` | Rarely |
| "Save key pages for offline" | `save` in `src/pages/sw.11ty.js` | recipe [12.8](#128-save-a-page-for-offline-use-or-add-an-app-shortcut) |

### 6.3 Partials on every page

| File | What it is | Notes |
|---|---|---|
| `partials/header.njk` | Logo, desktop menu (from 1280 px), search icon, the ES/EN pill, the "Aa" button, the light/dark button (from 640 px), the Menu button and the phone drawer | "Grapevine / La Viña" next to the logo is written right here. The language pill links to `page.url \| altLangUrl(L)`; `app.js` keeps the `#anchor` and `?query` when you switch. |
| `partials/footer.njk` | The about blurb (About us, neta65.org, e-mail), "Explore", one column per dropdown, "Stay updated" (official sites, Instagram, QR Post, RSS, calendar feed), the bottom bar ("Last updated", ©, the disclaimer and the reprint notice) | The e-mail and neta65.org come from `site.contact_email` and `site.area_website` in `config/site.yml`; the texts from `footer.*` keys in `src/_i18n/common.json`. |
| `partials/comfort-panel.njk` | The "Aa" panel: text size, spacing, contrast, motion, read aloud, data saver, install / save pages | Saved in the visitor's browser only (`gvlv-prefs`). Logic in `app.js`, look in `areas/access.css`. |
| `partials/lang-banner.njk` | "¿Prefieres español?" / "Prefer English?" | Shown after about a second, only when the browser's first language is the other one; a dismissal is remembered (`gv-lang-banner`). Look in `areas/community.css`. |

### 6.4 The building blocks: `src/_includes/macros/ui.njk`

Import it at the top of a page with `{% import "macros/ui.njk" as ui with context %}`. The long
comment at the top of `ui.njk` is the full manual, with rules and examples. The macros:

| Macro | What it makes | Example |
|---|---|---|
| `pageHero(lang, title, subtitle, icon, eyebrow, opts)` | The animated grapevine hero every page starts with (same height everywhere). Rules: eyebrow a short label, title at most 2 lines on a phone, subtitle at most 110 characters in English and 135 in Spanish, one `btn-light` button and at most 2 `btn-on-dark`. | `{{ ui.pageHero(lang, "nav.events" \| t(lang), "committee.events.hero_sub" \| t(lang), "calendar-days", "committee.events.eyebrow" \| t(lang)) }}` |
| `heroAside`, `heroAsideStat`, `heroAsideLinks`, `heroAsideLink`, `heroAsideMedia`, `heroAsideVideo` | One small card on the right of the hero (from 1024 px), else the first card under it or hidden (`opts.side: "below"` / `"hide"`) | Worked example: `src/pages/status.njk` |
| `heroStats(stats)` | Up to 4 small numbers in the hero (hidden below 768 px) | `{{ ui.heroStats([{ value: 56, label: "stories" }]) }}` |
| `sectionHead(title, subtitle, href, linkLabel, icon, opts)` | Every section's heading: eyebrow, h2, one-line intro, a "see all" button. Always pass `lang` in `opts`. | see recipe 12.4 |
| `pageNav(items, lang, opts)` | "On this page" chips for long pages | `{{ ui.pageNav([{ href: "#botm", label: "Book of the Month" }], lang) }}` |
| `freshness(date, lang, opts)` | "Updated 2 hours ago" (at most once per page) | `{{ ui.freshness(site.built, lang) }}` |
| `when(w)` | Attributes for something that appears or disappears at a set moment | used for price changes |
| `nextSteps(items, lang)` | Up to 4 closing link cards | |
| `memberHelp(lang, summary, opts)` | A closed "For committee members" how-to box | `{% call ui.memberHelp(lang, "How to add documents") %}…{% endcall %}` |
| `pageEmpty(icon, title, text, opts)` | A page-level "nothing here yet" card | |
| `emptyState(icon, title, text, ctaHref, ctaLabel)` | A small "no results" box inside a list | |
| `sourceBadge`, `autoNote`, `tentativeBadge`, `langPill`, `itemCard` | Source badge, the "Auto-translated" note, "Details to be confirmed", the original-language pill, a generic content card | |

> **Rule (checked by `tests/test_hero_aside.py`):** a page that puts a card on the hero's right must
> use `{% call(slot) ui.pageHero(…, { side: "below" }) %}` and test `slot == "side"`. A page without
> that card can use a plain `{% call ui.pageHero(…) %}`.

Other macro files:

| File | Macros | Used by |
|---|---|---|
| `macros/media.njk` | `shareBlock(…)`: the closing "Tell your group" block | Listen, Watch, Instagram |
| `macros/monthly.njk` | `head`, `story`, `issue`, `botm`, `dates`, `weekly`, `foot`, `calendar`, `deco`, `poster`: the 1080 × 1350 monthly poster | Monthly toolkit, month pages |
| `macros/orientation.njk` | `live(kind, lang, variant)` (a live example from the site's data), `linkList(lesson, lang)` | GVR / RLV 101 |
| `macros/presentations.njk` | `player(lang)`: the presentation player | GVR / RLV 101 |
| `macros/booth.njk` | `section(lang)`: the `#booth` section (preview card, quick controls, Start / Settings / Preview here, status chips, "How to use it at a booth"); `player(lang)`: the booth player's dialog shell, its icons and `#gvb-config`. Import it under another name than `booth` (`boothUi` in `about.njk`): `booth` is the global data | About us |

### 6.5 Shortcodes

| Shortcode | Output | Defined in |
|---|---|---|
| `{% icon "name", "classes", "label" %}` | An inline SVG icon. Our own SVG in `src/_includes/icons/` wins over the Lucide icon of the same name. Without a label it is hidden from screen readers. An unknown name prints nothing and logs `[icon] missing icon: name`. | `eleventy.config.js` |
| `{% committeeNav lang, "events", db %}` | The committee pill bar, with counts (upcoming events, Portfolio files, photos, bulletin posts) | `eleventy/filters/committee.js` |
| `{% cmSubscribe lang, site %}` | The calendar subscription card (Google, Apple, Outlook) | `committee.js` |
| `{% cmPreviewDialog lang %}` | The flyer / document preview window | `committee.js` |
| `{% cmDrivePath … %}`, `{% cmDriveChecked lang, di %}` | The "Drive › Panel folder › flyers" picture and the "last checked" line in the member how-tos | `committee.js` |
| `{% mediaSprite %}`, `{% micon … %}`, `{% readSprite %}`, `{% ricon … %}` | Icon sprites of the media and Read pages | `media.js`, `read.js` |

Example: `{% icon "calendar-days", "size-4" %}` prints `<svg class="icon size-4" aria-hidden="true" …>`
(recipe [12.10](#1210-add-an-icon)).

---

## 7. `eleventy.config.js` and the filters

### 7.1 A tour of `eleventy.config.js`

Line numbers change, so search for the words in the middle column.

| Part | Search for | What it does |
|---|---|---|
| Markdown for committee text | `markdownIt({ html: false, linkify: true, breaks: true })` | The `md` filter. HTML in a post is shown as text (a `<script>` can never run). A single line break becomes a line break. Tables get a sideways-scrolling box, pictures load lazily, links to site pages get `/es` on Spanish pages (`md.renderer.rules.link_open`). |
| Time zone | `const TZ = "America/Chicago";` | Every date on the site is Central time. |
| Strings | `function loadI18n()`, `export function translateKey` | Merges every `src/_i18n/*.json` (alphabetical order) into one table. `{name}` placeholders. A missing key: the raw key, or a build error with `I18N_STRICT`. A missing language falls back to English. |
| Synced text in the page language | `function pickLang` | The `tx` filter: `item.i18n[field][lang]` (when the item has translations but none in that language, the English one), then `item[field + "_" + lang]`, then `item.extra[field]`, then `item[field]`. |
| Dates | `function fmtDate` | The `fmtDate` styles (table in 7.2). A bare `YYYY-MM-DD` is read at noon so it never moves a day. |
| Spanish times | `export function esMeridiem` | "7:00 p.m." → "7:00 p. m." (twin in `app.js`: `GV.esMeridiem`) |
| Safe links | `export function safeUrl` | The `extUrl` filter; `src/_data/db.js` runs it on every link in the data. Keeps `http://…` and `https://…`, `mailto:`, `tel:`, `#…`, `/path`; repairs `www.x.org`, `zoom.us/j/1` and `//host/x` to `https://…`; anything else becomes `""` and the page hides the link. |
| Meeting rules | `export function hhmm`, `export function monthlyRule` | Read `meeting:` and `recurring_events:` of `config/site.yml` exactly like the Python sync ("7:00 PM", "7pm", "19h00", "sábado", "2nd", "último"…). |
| Path prefix | `const pathPrefix = process.env.PATH_PREFIX \|\| "/";` and `addPlugin(EleventyHtmlBasePlugin)` | Section 9 |
| Fast builds | `if (process.env.ONLY)` | The `ONLY` switch (section 3) |
| Safety | `setNunjucksEnvironmentOptions` | `autoescape: true` must stay on: titles come from outside sources. |
| Live reload | `addWatchTarget` | `npm start` also rebuilds when `src/_i18n/`, `data/site/`, `config/` or `content/booth/` change. |
| Copied files | `/* ---------- passthrough ---------- */` | `src/assets/img`, `src/assets/js`, `src/assets/cache`, `favicon.ico`, `.nojekyll`; bulletin attachments (`content/bulletin/*.jpg`, `.png`, `.pdf`… in any letter case) to `/bulletin/files/`; the booth display's saved media (`.cache/booth-media/files` → `/about/booth/media/`, only when that folder exists); vendor libraries and fonts from `node_modules`. CSS is **not** copied: Tailwind writes it. |
| Filters | `/* ---------- i18n filters ---------- */`, `/* ---------- dates ---------- */`, `/* ---------- collections helpers ---------- */`, `/* ---------- text ---------- */` | The shared filters (7.2) |
| Icons | `addShortcode("icon"` | 6.5 |
| CSS | `/* ---------- Tailwind CSS (compiled after each build) ---------- */` | After every build: `src/assets/css/main.css` → `_site/assets/css/main.css`, minified. |
| Area filters | `/* ---------- area-specific filters (auto-loaded) ---------- */` | Loads every `.js` file in `eleventy/filters/` by itself (alphabetical). A new file there needs no other change. |
| Folders | `dir: { input: "src"` | Input `src`, includes `src/_includes`, data `src/_data`, output `_site`. |

### 7.2 The filters you will use most

Every result below was produced by the repo's own code.

| You write | You get |
|---|---|
| `"nav.events" \| t("es")` | `Eventos` |
| `"committee.events.online_on" \| t("es", { platform: "Zoom" })` | `En línea por Zoom` |
| `"nav.does_not_exist" \| t("es")` | `nav.does_not_exist` on your computer; on GitHub the build stops with `Missing i18n key: nav.does_not_exist` |
| `item \| tx("title", lang)` | The item's title in the page language (its Spanish translation on `/es/`) |
| `site \| pick("es", "committee")` | `Comité de Grapevine y La Viña de NETA 65` (from `committee_es` in `config/site.yml`) |
| `"/events/" \| lurl("es")` | `/es/events/` (and `"/events/" \| lurl("en")` → `/events/`) |
| `page.url \| altLangUrl("en")` on `/events/` | `/es/events/` (on `/es/events/` with `"es"` → `/events/`) |
| `"/es/library/" \| siteUrl(site)` | `https://neta65.github.io/aagrapevine/es/library/` |
| `"2026-10-21" \| fmtDate("en", "long")` | `Wednesday, October 21, 2026` (Spanish: `Miércoles, 21 de octubre de 2026`) |
| `"2026-10-21" \| fmtDate("en", "short")` | `Oct 21, 2026` (Spanish: `21 oct 2026`) |
| `"2026-10-21" \| fmtDate("es", "month")` | `octubre de 2026` |
| `"2026-10-22T00:00:00Z" \| fmtDate("en", "time")` | `7:00 PM CDT` (Spanish: `7:00 p. m. CDT`) |
| Other `fmtDate` styles | `medium`, `monthShort`, `day`, `weekday`, `datetime`, `iso`, `ymd`, `relative` |
| `"zoom.us/j/123" \| extUrl` | `https://zoom.us/j/123` (`"www.district5.org"` → `https://www.district5.org`) |
| `"javascript:alert(1)" \| extUrl`, `"flyer.pdf" \| extUrl` | `""`: the template hides the link |
| `text \| md({ h: 3, lang: lang })` | Committee Markdown as HTML; its `#` headings start at h3. `"<script>…"` comes out as plain text. |
| `md("# Why it matters\n# Parking", { h: 3, ids: "ann-x" })` | `<h3 id="ann-x--why-it-matters">` and `<h3 id="ann-x--parking">` (`mdToc` with the same options gives the list for "In this post") |
| `"Grapevine and La Viña prices change on January 1, 2027." \| excerpt(40)` | `Grapevine and La Viña prices change on…` (cut at a whole word; the default is 160 characters) |
| `"https://www.neta65.org/x/" \| hostname` | `neta65.org` |
| `1536000 \| fileSize` / `3725 \| duration` | `1.5 MB` / `1:02:05` |
| List helpers | `where`, `whereNot`, `whereIncludes` (dotted keys like `"extra.past"`), `limit`, `offset`, `groupBy`, `countBy`, `pluck`, `uniq`, `sortByDate`, `upcoming`, `past`, `withinDays`, `isRecent` |

### 7.3 The area filter files: `eleventy/filters/*.js`

Each file serves one area of the site and is loaded by itself. Each exports
`export default function (eleventyConfig, helpers)`; the helpers are `translateKey`, `pickLang`,
`fmtDate`, `toDate` and `esMeridiem` from `eleventy.config.js`.

| File | Pages it serves | Main filters and functions |
|---|---|---|
| `access.js` | `/accessibility/` | `axPhone`, `axAudioTypes`, `axAslPlaylist` |
| `booth.js` | `/about/booth.json` (the booth display's show) | `boothJson`; `loadBooth` (used by `src/_data/booth.js`), `checkCsv` (the CSV's rules — `tests/test_booth_csv.py` is their Python twin), `driveItems`, `liveItems`, `boothShow`, `refusedIn` (the words the booth never shows) |
| `committee.js` | `/meetings/`, `/events/`, `/portfolio/`, `/photos/`, `/bulletin/`, `/events.ics`, parts of home, monthly, report | `cmEvents` (functions `normalizeEvents` + `shapeEvent`: one event card), `cmCollapseRecurring`, `cmAnnouncements` (`announcementList`), `cmDocTabs`, `cmAlbums`, `cmDriveInfo` (`driveInfo`), `cmWorkshops`, `buildIcs`; shortcodes `committeeNav`, `cmSubscribe`, `cmPreviewDialog`, `cmDrivePath`, `cmDriveChecked` |
| `community.js` | `/whats-new/`, `/digest/`, `/share/`, `/status/`, 404, `/feed.xml` | `cmWnPrepare`, `cmMonthlyDigest`, `cmDigestText`, `cmStatus` (`statusView`), `qrSvg`, `cmTOr` (a string with a fallback that never stops the build) |
| `event-tone.js` | everywhere events are listed | `eventTone`: committee · gv · lv · booth · assembly · other (the card colour) |
| `freshness.js` | `/status/`, `/bulletin/`, home | `fsQuoteMornings`, `fsDayEnd`, `fsShortDay`, `fsClock` |
| `home.js` | home page | `homeData`, `homeEvents`, `homeEventInfo`, `homeAnnouncements`, `homeDrive`, `homeSpotlight`, `homeLatestIssue`, `homeThemes`, `homeDailyQuotes`… |
| `library.js` | `/library/`, `/search/`, the two JSON indexes | `libDocs`, `libFacets`, `libCollections`, `libIndexJson`, `searchIndexJson` (function `searchIndex`) |
| `media.js` | `/listen/`, `/watch/`, `/instagram/` | `mediaItems`, `mediaTitle`, `mediaShowList`, `mediaIndexJson` |
| `monthly.js` | `/monthly/`, month pages, digest, gvr, orientation | `mpMonths`, `mpMonth`, `mpNow`, `mpIssues`, `mpMessage`, `mpQr`; global data `monthlyKeys`, `monthlyPages`, `monthlyPastPages` |
| `orientation.js` | `/orientation/` and its sessions | `o101Text`, `o101Lesson`, `o101Links`, `o101Deck` |
| `presentations.js` | the presentation JSON files | `presDeckJson`; `loadDecks` (used by `src/_data/presentations.js`) |
| `published.js` | `/published/`, a search tile | `pwView`, `pwJson` |
| `read.js` | `/read/`, `/contribute/`, `/shop/`, `/gvr/`, `/about/` | `readIssues`, `readArchive`, `readEditorial`, `readCatalogs`, `readForms`, `readPdfsMatching` |
| `report.js` | `/monthly/#report` | `rpModel`, `rpJson`, `rpUi` |
| `shop.js` | `/shop/`, home, `/tracker/`, month pages, GVR / RLV 101 examples | `shopBotm`, `shopSubs`, `shopBulk`, `shopSpecialty`, `shopPriceChanges`, `shopMoney` |

`eleventy/script-json.js` (`scriptJson`) is the one safe way to put data inside a `<script>` tag: it
escapes `<`, `>` and `&` so no text can end the script early. In a template it is the filter
`jsonScript` (registered in `library.js`): `{{ data | jsonScript | safe }}`.

---

## 8. Global data (`src/_data`)

Each file's name is a variable in every template. Eleventy runs each file once per build.

| Variable | File | Reads | What it holds |
|---|---|---|---|
| `site` | `site.js` | `config/site.yml` | Everything under `site:` (`title`, `title_es`, `committee`, `contact_email`, `area_website`, `listen`, `watch`, `about_videos`, …) plus the top-level sections `meeting`, `recurring_events`, `drive`, `sources`, `links`, `phone_access`, `digest`, `lavina_weekly_open`. `url` is the public address (`SITE_URL` on GitHub, else `site.url`), `built` the build time. |
| `languages` | `languages.js` | | `["en", "es"]` |
| `build` | `build.js` | the code files | `version` (a fingerprint of the code, the `?v=` on CSS and JS and the service-worker version), `commit`, `time` |
| `db` | `db.js` | `data/site/<name>.json` for every name in its `FILES` list | `db.events`, `db.announcements`, `db.drive`, `db.articles`, `db.videos`, `db.status`, … A missing or broken file becomes `{ updated: null, items: [] }`. Every link is cleaned with `safeUrl`. |
| `nav` | `nav.js` | | The menus (6.2) |
| `meeting` | `meeting.js` | `config/site.yml` `meeting:` | The rule, the next meeting and the next 12 dates (default: third Wednesday, 7 PM, one hour) |
| `carry` | `carry.js` | `config/carry.yml` | "Put this issue to work" ideas for the monthly toolkit |
| `orientation` | `orientation.js` | `config/orientation.yml` | The GVR / RLV 101 sessions |
| `history` | `history.js` | `config/history.yml` | The timeline on `/about/#history` |
| `expenses` | `expenses.js` | `config/expenses.yml` | The Tracker's defaults and words |
| `presentations` | `presentations.js` | `config/presentations/*.yml` | The web presentations |
| `booth` | `booth.js` | `content/booth/booth.csv`, `data/site/booth.json`, `.cache/booth-media/manifest.json`, `config/site.yml` `booth:` | The booth display's own parts, read and checked once per build (`loadBooth` in `eleventy/filters/booth.js`): the CSV's rows, the Drive booth folder's files with their saved copies, the starting settings, and every problem (written to the build log as `[booth] …`). `src/pages/booth-json.11ty.js` adds the day's live items |
| `monthlyKeys`, `monthlyPages`, `monthlyPastPages` | added by `eleventy/filters/monthly.js` | the build's clock | The 13 month pages and the 3 redirect months |

> **Note (a real gotcha):** a new top-level section in `config/site.yml` is **not** visible as
> `site.<name>` until you add it to the object returned by `src/_data/site.js`. Today `price_changes`,
> `meetings`, `spotlight` and `library` are not passed (the sync reads them instead), nor `booth`
> (`src/_data/booth.js` reads it from the file itself). Example: the home page asks for
> `site.spotlight.home_days`, which is always empty, so its fallback 60 is used; the real number comes
> from `data/site/spotlight.json` (`home_days: 60`). Recipe
> [12.6](#126-read-a-new-setting-from-configsiteyml).

> **Note:** `src/_data/db.js` writes the links it had to repair or hide to the build log
> (`[links] …`, at most 25 lines) and every one of them to `db.status.link_problems`. No page shows
> that list.

---

## 9. The two languages and the `/aagrapevine/` path prefix

The live site lives in a folder: `https://neta65.github.io/aagrapevine/`. On GitHub the build gets
`PATH_PREFIX=/aagrapevine/` (from the Pages settings), and every link must include that folder. On
your computer `PATH_PREFIX` is not set, so the site lives at `/`. The rules below make both work.

### 9.1 The five rules

1. **In HTML attributes, write the plain site path.** Write `href="/events/"` or
   `href="{{ '/events/' | lurl(lang) }}"`. At build time Eleventy's HTML base plugin adds the folder
   to every root path in `href`, `src`, `srcset`, `action` and similar attributes. Live result:
   `href="/aagrapevine/es/meetings/"`, `href="/aagrapevine/assets/css/main.css?v=ab2671a92b"`.
2. **Never put `| url` in an HTML attribute.** The plugin adds the folder again:
   `/aagrapevine/aagrapevine/events/`. Use `| url` only where the plugin does not look, inside
   `<script>` text and JSON. Real examples: `window.SITE = { lang: "{{ L }}", base: "{{ '/' | url }}", … }`
   in `base.njk` (live: `base: "/aagrapevine/"`), and the redirect stubs' `location.replace(…)`.
3. **`data-*` attributes, inline `style`, JSON and plain text are not rewritten.** There, make the
   address absolute with `| siteUrl(site)`, or add the folder in the browser with `GV.url()`.
4. **Full public addresses** (canonical, `hreflang`, share buttons, QR codes, feeds, calendar links)
   use `"/path/" | siteUrl(site)`: `"/events.ics" | siteUrl(site)` →
   `https://neta65.github.io/aagrapevine/events.ics`.
5. **Non-HTML files** (the manifest, `sw.js`, the feeds, the calendar, the sitemap) are not touched by
   the plugin. They read `PATH_PREFIX` or `site.url` themselves. The JSON indexes store plain site
   paths (`/events/#…`) and the page scripts add the folder with `GV.url(u)`.

| Write this | Not this | Why |
|---|---|---|
| `<a href="{{ '/library/' \| lurl(lang) }}">` | `<a href="{{ '/library/' \| url }}">` | `\| url` + the plugin = the folder twice |
| `<a href="/bulletin/files/flyer.pdf">` (a file that exists once) | `<a href="{{ '/bulletin/files/flyer.pdf' \| lurl(lang) }}">` | `lurl("es")` gives `/es/bulletin/files/flyer.pdf`, which does not exist. Of the non-page files, only the feed, the calendar, the manifest and the JSON indexes have `/es/` copies. |
| `data-share="{{ page.url \| siteUrl(site) }}#{{ ev.anchor }}"` (as in `events.njk`) | `data-share="/events/#{{ ev.anchor }}"` | `data-*` is not rewritten: the link would miss `/aagrapevine/` |
| `fetch(GV.url("/search-index.json"))` in a script | `fetch("/search-index.json")` | Scripts are not rewritten |
| `{{ item.url \| extUrl }}` for a link from data | `{{ item.url }}` | `extUrl` hides unsafe or broken links |

### 9.2 Spanish pages in practice

- The permalink makes `/es/…` (section 4). Links inside templates go through `| lurl(lang)`.
  `"/events/#subscribe" | lurl("es")` → `/es/events/#subscribe`; `"/" | lurl("es")` → `/es/`;
  `https://…`, `mailto:` and `#anchor` links stay as they are.
- Links inside committee Markdown go through `md({ lang })`: on a Spanish page
  `[Events](/events/)` becomes `/es/events/`, while `/bulletin/files/f.pdf` and `/feed.xml` stay as
  written (files never get `/es`).
- The language switch is `page.url | altLangUrl(lang)`: `/events/` ⇄ `/es/events/`, `/es/` → `/`.
- `<html lang>`, the `hreflang` links and the sitemap pairs come from the layout and
  `sitemap.11ty.js` by themselves.

### 9.3 In the browser

`base.njk` writes `window.SITE = { lang, base, tz }`. `app.js` turns it into `GV.lang`, `GV.base` and
`GV.url(p)`: `GV.url("/library-index.json")` → `/aagrapevine/library-index.json` on the live site,
`/library-index.json` on your computer. A few short messages are written in the scripts themselves
with `GV.t("English", "Español")` (for example "Copied!" / "¡Copiado!" in `app.js`); everything else a
script shows comes from the page (`data-*` attributes or a JSON block made from `src/_i18n`).

---

## 10. Styles: `main.css`, area files and theme tokens

### 10.1 How the CSS is made

The site uses **Tailwind CSS 4**. Templates mostly use utility classes (`mt-4`, `text-muted`,
`rounded-full`…). After every build Tailwind reads the templates, finds the classes they use and
writes one file, `/assets/css/main.css`, from `src/assets/css/main.css`.

- Tailwind reads **only** these folders for class names (the `@source` lines at the top of
  `main.css`): `src/_includes`, `src/pages`, `src/assets/js` and `eleventy`. A class written only in
  `src/_data/`, `config/`, `content/` or `data/` is never generated.
- Tailwind finds a class only when the **whole name** is written somewhere. `{{ 'text-gv' if gv else 'text-lv' }}`
  works (both names are written out); `"text-" + tone` does not.
- Dark mode follows the site's own switch: `dark:` utilities apply under `<html data-theme="dark">`
  (set from the visitor's choice, else the phone's setting).

### 10.2 Theme tokens (colours)

Colours are **tokens** in `main.css`. Use them as utilities (`bg-paper`, `bg-surface`, `text-ink`,
`text-muted`, `border-line`, `bg-gv`, `text-gv`, `bg-gv-soft`, `text-lv`, `bg-grape-soft`,
`text-vine`…) or in CSS as `var(--c-ink)`. Each one has a light and a dark value, so dark mode works
by itself.

| Token | Used for | Light (`:root`) | Dark (`:root[data-theme="dark"]`) |
|---|---|---|---|
| `--c-paper` | Page background | `#fbf8f2` | `#121019` |
| `--c-surface` / `--c-surface-2` | Cards / tinted panels | `#ffffff` / `#f4efe6` | `#1b1825` / `#231f30` |
| `--c-ink` | Main text | `#1d1a26` | `#eeeaf6` |
| `--c-muted` / `--c-faint` | Secondary / small text | `#57526a` / `#6e6980` | `#b3adc4` / `#948ea6` |
| `--c-line` | Borders | `#e6dfd2` | `#312c40` |
| `--c-gv`, `--c-gv-strong`, `--c-gv-soft` | Grapevine / NETA blue (main colour, links, buttons) | `#0a5fa8`, `#07457c`, `#e5f0fa` | `#6cb0ef`, `#9ccbf5`, `#16283d` |
| `--c-lv`, `--c-lv-strong`, `--c-lv-soft` | La Viña amber | `#b8430b`, `#8f3207`, `#fdeee3` | `#f59a5b`, `#f8b88a`, `#33200f` |
| `--c-grape`, `--c-grape-soft` | Accent | `#5b2a86`, `#f1e8f8` | `#c29ae8`, `#2a1f3a` |
| `--c-vine`, `--c-vine-soft` | "Fresh" / success green | `#2f6e2c`, `#e7f3e3` | `#8fd08a`, `#16281a` |
| `--c-danger` | Errors | `#b42318` | `#f97066` |

The **high contrast** setting of the "Aa" panel has its own values under `:root[data-contrast="high"]`
(light) and `:root[data-contrast="high"][data-theme="dark"]` (dark). The fonts are tokens too:
`--font-sans` (Inter) and `--font-display` (Fraunces, the headings).

The "Aa" panel's other settings are attributes on `<html>` that `main.css` reacts to: `data-text`
(100, 115, 130 or 150 % text size), `data-spacing` (relaxed text spacing), `data-motion` (reduced
motion) and `data-saver` (Data saver).

### 10.3 Shared classes

`main.css` defines the shared components. The full list is in its first comment; the ones you will
use most:

| Kind | Classes |
|---|---|
| Layout | `container-page` (page width and side margins), `page-overlap` / `page-start` (exactly one, right after the hero), `section`, `layout-aside`, `sticky-aside`, `measure` |
| Cards | `card`, `card-pad`, `card-link`, `card-media`, `card-h`, `panel-muted`, `section-band` |
| Buttons | `btn-primary` (one per section), `btn-secondary`, `btn-ghost`, `btn-lv`, `btn-light` / `btn-on-dark` (in the hero), `btn-sm` |
| Badges and chips | `badge-gv`, `badge-lv`, `badge-grape`, `badge-vine`, `badge-muted`, `badge-new`, `badge-tbc`; `chip`, `chip-row` |
| Grids | `grid-cards`, `grid-cards-4`, `grid-cards-fit`, `rail` |
| Text | `eyebrow`, `h-section`, `h-card`, `lead`, `meta-row`, `link`, `tap-link` |

### 10.4 The area files: `src/assets/css/areas/*.css`

Each area of the site has one file, imported at the bottom of `main.css`. Put there only what utility
classes cannot do (pseudo-elements, animations, complex grids, print layouts). Each file uses its own
class prefix:

| File | Pages | Class prefix |
|---|---|---|
| `home.css` | Home | `home-` |
| `library.css` | Library, Search | `lib-`, `ss-` |
| `media.css` | Listen, Watch, Instagram | `media-`, `ep-`, `ig-`, `listen-` |
| `committee.css` | Meetings, Events, Portfolio, Photos, Bulletin | `cm-`, `ev-` (`ev-tone-*` = the event colours) |
| `read.css` | Read, Share your story, Shop, GVR / RLV corner, About us | `read-` |
| `community.css` | What's new, Digest, QR Post, Status, 404, the language banner | `cm-`, `nf-` |
| `published.css` | Published writers (and its home section) | `pw-` |
| `shop.css` | Shop (and the home teaser) | `shop-` |
| `monthly.css` | Monthly toolkit, month pages, the poster | `mp-` |
| `report.css` | The district report on `/monthly/#report` | `rp-` |
| `expenses.css` | Tracker | `xp-` |
| `orientation.css` | GVR / RLV 101 | `o101-` |
| `presentations.css` | The presentation player | `gvp-` |
| `booth.css` | The booth display (About us) | `gvb-` |
| `access.css` | The "Aa" panel, read aloud, Accessibility | `gvlv-`, `tts-`, `ax-` |
| `pwa.css` | Saved pages & app, Data saver, offline notices | `pwa-` |

---

## 11. Scripts (`src/assets/js`)

Every page loads, in this order (all `defer`): `app.js`, `install-core.js`, `pwa.js`,
`hero-canvas.js`, then the page's `pageScripts`, then **Alpine** last. So a page script registers its
Alpine components on `alpine:init` and they are ready when Alpine starts. Every script is an extra:
the pages can be read without JavaScript.

| File | Loaded on | What it does |
|---|---|---|
| `app.js` | every page | `window.GV` helpers: `GV.url`, `GV.t`, `GV.copy`, `GV.share`, `GV.fmtDate`, `GV.ics`, `GV.nextMeeting`, `GV.expire` (hides things whose time has passed between builds), `GV.prefs` and `GV.tts` (the "Aa" panel and read aloud); the header, menus, theme, language switch |
| `install-core.js` | every page | Which phone and browser this is, and which install guide fits it |
| `pwa.js` | every page | Registers the service worker, "Save key pages", offline and "Updated — reload" notices, Data saver |
| `hero-canvas.js` | every page | The animated grapevine art in the hero (the committee's original artwork) |
| `home.js` | Home | The meeting countdown and the podcast player |
| `committee.js` | Meetings, Events, Portfolio, Photos, Bulletin, Tracker | Event filters and calendar buttons, the Drive preview window, photo albums (GLightbox), the committee pill bar, the meeting countdown on `/meetings/` |
| `community.js` | What's new, Digest, QR Post, Status, 404 | The What's New timeline ("Today" / "Yesterday"), the digest's ready-to-copy texts, the QR Post kit, the 404 search box |
| `read.js` | Read, Share your story, GVR / RLV corner | Older issues, "days left" countdowns, workshops that hide when over, the GVR first-steps checklist |
| `shop.js` | Shop, Home | Offer countdowns, the subscription price table |
| `media.js` | Listen, Watch, Instagram | The audio player, the video window, "Load more" |
| `library.js` | Library | Search, filters and paging over `/library-index.json` |
| `search.js` | Search, Library | The site search over `/search-index.json` (with the MiniSearch library) |
| `published.js` | Published writers | Filters (who, when, which magazine) |
| `monthly.js` | Monthly toolkit, month pages | The poster (download PNG, share, print), "over" dates |
| `report.js` | Monthly toolkit (`#report`) | The district report editor |
| `orientation.js` | GVR / RLV 101 | Progress, the review questions, printing |
| `presentations-core.js`, `presentations.js` | GVR / RLV 101 | The presentation player (logic / screen) |
| `booth-core.js`, `booth.js` | About us | The booth display: the logic (`window.GVB`: which slides may show now, which comes next, in which language and for how long) / the screen (the full-screen show, the visitors' bar, Settings, the offline copy) |
| `expenses-core.js`, `expenses.js` | Tracker | The Tracker (logic / screen); everything stays in the visitor's browser |

Open-source libraries are copied from `node_modules` to `/assets/vendor/` by `eleventy.config.js`:
Alpine, MiniSearch, GLightbox (Photos), lite-youtube-embed (videos that load nothing until Play) and
html-to-image (the monthly poster PNG). The fonts (Inter and Fraunces) are copied the same way, so
no script or font is loaded from another site's servers.

---

## 12. Recipes

Each recipe says which files to edit, what happens, where it shows and what to test. Push and timing
are in section 14.

### 12.1 Change a text (UI words)

All the site's own words are in `src/_i18n/*.json`, one file per area (`common.json` holds the menu,
footer and shared words: `nav.*`, `footer.*`, `site.*`, `comfort.*`…). Every key has an English and a
Spanish text:

```json
"nav.events": { "en": "Events", "es": "Eventos" },
"committee.events.online_on": { "en": "Online on {platform}", "es": "En línea por {platform}" }
```

**Find the key.** On github.com search `"the words" path:src/_i18n`. On your computer:
`git grep -n "Subscribe to calendar" -- src/_i18n`. The first word of a key usually names its file
(`committee.*` → `committee.json`), but not always (`search.page_desc.accessibility` is in
`access.json`): searching is the sure way. To see every place a key is used:
`git grep -n "committee.events.subscribe_btn" -- src eleventy`.

**Examples:**

1. *Change the line under the Events title.* Key `committee.events.hero_sub` in
   `src/_i18n/committee.json`. Keep it under 110 characters in English and 135 in Spanish (the hero
   rule). Shows under the title of `/events/` and `/es/events/`.
2. *Change a text with a placeholder.* `"Online on {platform}"` → `"Join on {platform}"`. Keep
   `{platform}` in **both** languages, spelled the same: the event card fills it in ("Join on Zoom").
   A language whose text has no `{platform}` just leaves the name out; a misspelled one
   (`{platfrom}`) is printed as it is. The same key is used on the home page's event cards,
   `/contribute/`, the QR Post poster and the "Add to calendar" text.
   > **Note:** this sentence is pinned by tests: `tests/test_events_feeds.py` and
   > `tests/test_recurring_events.py` expect "Online on Zoom" / "En línea por Zoom". Change those
   > words in the tests in the same commit, or **Code check** shows a red ✗ (the live site still
   > updates: Update & Deploy does not run the tests).
3. *Gold italics in the home title.* `home.hero_title` in `src/_i18n/home.json` is
   `"AA's *meeting in print*, here in Northeast Texas"`. The words between `*stars*` show in gold
   italics on the home page hero (`/` and `/es/`).
4. *Add a new key* (for a new label in a template). Add it once, in the file of its area, with both
   languages, and mind the commas:
   ```json
   "committee.events.cost": { "en": "Cost", "es": "Costo" },
   ```
   and use it in the template: `{{ "committee.events.cost" | t(lang) }}`. A key may exist in only
   **one** file: the files are merged, and a duplicate would silently win.

**What happens:** Update & Deploy rebuilds the site in a few minutes. A missing key stops the GitHub
build (`Missing i18n key: …`) and the live site keeps the old version.

**Test:** `python -m unittest tests.test_i18n_keys` (no key in two files, both languages present,
the same `{placeholders}` in both). If you edit the "Aa" panel words (`comfort.*`) or the
Accessibility page (`access.*`), also run `tests.test_accessibility`: it checks length limits. A few
tests check exact words (for example `tests/test_bulletin.py` expects the menu names "Bulletin" /
"Boletín" and "QR Post" / "Cartel QR"), so after a word change run them all
(`python -m unittest discover -s tests`) or watch the **Code check**: a failing test names the words it
expected.

> Text that is **not** UI words (a story title, an event, the committee name) lives elsewhere: see
> the table in section 2 and [Translations](translations.md).

### 12.2 Change a colour

**The whole site's colour** (for example La Viña's amber): search `src/assets/css/main.css` for
`--c-lv:`. The token is set in six rules (each rule holds all the tokens together):

| Rule in `main.css` | `--c-lv` today | Used for |
|---|---|---|
| `:root` | `#b8430b` | Light theme |
| `:root[data-theme="dark"]` | `#f59a5b` | Dark theme |
| `:root[data-contrast="high"]` | `#7a2b05` | High contrast, light |
| `:root[data-contrast="high"][data-theme="dark"]` | `#ffb47f` | High contrast, dark |
| `@media print` → `:root[data-theme="dark"]` | `#b8430b` | Printing from dark mode (paper always gets the light value) |
| `@media print` → `:root[data-theme="dark"][data-contrast="high"]` | `#7a2b05` | Printing from dark high contrast |

Change the light value in `:root` **and** in the first print rule, and the others to match. Every
`text-lv`, `bg-lv`, `border-lv`, `btn-lv`, `badge-lv` and `var(--c-lv)` follows. Text must stay
readable: at least 4.5 : 1 against its background (check with any online contrast checker), in light
**and** dark.

**One element's colour:** use another token class in the template (`text-gv` → `text-grape`), or a
rule in the area file with `var(--c-…)`. Never a fixed `#hex` in a template: it would not follow dark
mode.

**Colours that do not follow the tokens** (change them by hand if you change the main blue):

| Where | What |
|---|---|
| `main.css`, the `.gv-hero, .page-hero` rule | The hero's navy → NETA blue gradient |
| `main.css`, `@utility btn-light` | The hero button's text colour `#07457c` |
| `base.njk` (`<meta name="theme-color">`) and `pwa.js` | The phone's address-bar colour (`#07457c` / `#121019`) |
| `manifest.11ty.js` (`theme_color`, `background_color`) | The installed app's colours |
| The redirect stubs (`*-redirect.njk`, `meeting.njk`, `monthly-past.njk`) | Their own small inline style |
| `areas/monthly.css`, `areas/presentations.css` | The poster and the slides use fixed, print- and projector-safe colours on purpose |
| `areas/home.css` | The meeting card and the service band are always dark (fixed white on navy) |
| `areas/community.css` (`@media print`) | The digest and the QR Post print with their own colours |

### 12.3 Add, move or rename a menu item

All menus come from `src/_data/nav.js` (section 6.2).

- **Rename** a menu item: change its text, not its key. "Events" is `nav.events` in
  `src/_i18n/common.json`.
- **Reorder:** move the line inside its list. The header, the phone menu and the footer follow.
- **Move Instagram into the top menu** (example): cut its line from `footer`, paste it into
  `primary` after Watch, and drop `group`:
  ```js
  { key: "nav.watch", url: "/watch/", icon: "circle-play", page: "watch" },
  { key: "nav.instagram", url: "/instagram/", page: "instagram", icon: "instagram" },
  ```
  Result: Instagram appears in the header (from 1280 px), the phone menu's top list and the footer's
  "Explore" column, and leaves "Stay updated" and "More".
  > **Note:** two tests pin today's footer: `tests/test_bulletin.py` and `tests/test_pwa_install.py`
  > expect "Stay updated" to hold exactly Instagram, then QR Post (search both files for
  > `group: "stay"`). Change that list in both tests in the same commit, or **Code check** shows a red
  > ✗ (the live site still updates).
- **Add a page to a dropdown:** give it a `descKey` (required, see 6.2), and add both strings to
  `common.json`.

Other menu facts the tests check: the names "Bulletin" / "Boletín" and "QR Post" / "Cartel QR"
(`tests/test_bulletin.py`), and the Tracker staying under Committee, after the Bulletin
(`tests/test_expenses_page.py`).

**Test:** `python -m unittest tests.test_header_footer tests.test_i18n_keys tests.test_bulletin tests.test_pwa_install tests.test_expenses_page`
(or simply `python -m unittest discover -s tests`), then look at a phone width and at 1280 px.

### 12.4 Add a new page, end to end

Worked example: a "Questions" page at `/faq/` (Spanish `/es/faq/`).

1. **The template.** Create `src/pages/faq.njk` (the file name is free; the address comes from
   `permalink`):
   ```njk
   ---
   pagination: { data: languages, size: 1, alias: lang }
   permalink: "{{ '/' if lang == 'en' else '/es/' }}faq/index.html"
   layout: layouts/base.njk
   pageKey: faq
   titleKey: nav.faq
   descKey: faq.meta_desc
   pageScripts: ["/assets/js/faq.js"]
   ---
   {% import "macros/ui.njk" as ui with context %}
   {% call ui.pageHero(lang, "nav.faq" | t(lang), "faq.hero_sub" | t(lang), "circle-help", "faq.eyebrow" | t(lang)) %}
     <div class="hero-actions">
       <a class="btn-light" href="#questions">{% icon "list", "size-4" %} {{ "faq.jump" | t(lang) }}</a>
     </div>
   {% endcall %}

   <section id="questions" class="container-page page-start" aria-labelledby="faq-title">
     {{ ui.sectionHead("faq.title" | t(lang), "faq.sub" | t(lang), "", "", "circle-help", { eyebrow: "faq.eyebrow" | t(lang), id: "faq-title", lang: lang }) }}
     <div class="card card-pad faq-list" x-data="faqList">
       <details class="faq-item">
         <summary>{{ "faq.q_meeting" | t(lang) }}</summary>
         <p>{{ "faq.a_meeting" | t(lang) }} <a class="link" href="{{ '/meetings/' | lurl(lang) }}">{{ "nav.meetings" | t(lang) }}</a></p>
       </details>
     </div>
   </section>
   ```
   Rules: start with `ui.pageHero`, then exactly one `page-start` or `page-overlap` block; every
   section opens with `ui.sectionHead` (always pass `lang`); site links with `| lurl(lang)`, never
   `| url`; text from data with `| tx("title", lang)`; links from data with `| extUrl`.
2. **The menu.** In `src/_data/nav.js`, under "Get involved" (a dropdown child needs `descKey`):
   ```js
   { key: "nav.faq", url: "/faq/", icon: "circle-help", page: "faq", descKey: "nav.faq_desc" },
   ```
   This one line puts the page in the header, the phone menu, the footer **and** the site search.
   `page` must equal `pageKey`. (A Committee page also needs an entry in the `pages` list of the
   `committeeNav` shortcode in `eleventy/filters/committee.js`, a `committee.subnav.faq` string and
   `{% committeeNav lang, "faq", db %}` under its hero.)
3. **The words, in both languages.** In `src/_i18n/common.json`:
   ```json
   "nav.faq": { "en": "Questions", "es": "Preguntas" },
   "nav.faq_desc": { "en": "Short answers about our service", "es": "Respuestas breves sobre nuestro servicio" },
   ```
   and a new file `src/_i18n/faq.json` (any new `.json` file there is read by itself):
   ```json
   {
     "faq.meta_desc": { "en": "Short answers to common questions about the NETA 65 Grapevine / La Viña committee.", "es": "Respuestas breves a preguntas frecuentes sobre el comité de Grapevine / La Viña de NETA 65." },
     "faq.eyebrow": { "en": "Get involved · Questions", "es": "Participa · Preguntas" },
     "faq.hero_sub": { "en": "Short answers about meetings, magazines and service.", "es": "Respuestas breves sobre reuniones, revistas y servicio." },
     "faq.jump": { "en": "See the questions", "es": "Ver las preguntas" },
     "faq.title": { "en": "Frequent questions", "es": "Preguntas frecuentes" },
     "faq.sub": { "en": "Tap a question to open it.", "es": "Toca una pregunta para abrirla." },
     "faq.q_meeting": { "en": "When does the committee meet?", "es": "¿Cuándo se reúne el comité?" },
     "faq.a_meeting": { "en": "Once a month on Zoom. Everyone is welcome.", "es": "Una vez al mes por Zoom. Todos son bienvenidos." }
   }
   ```
   Optional extra search words: `"search.kw.faq": { "en": "faq questions help", "es": "preguntas ayuda" }`
   next to the other `search.kw.*` keys in `src/_i18n/library.json`.
4. **Styles, only for what utilities cannot do.** Create `src/assets/css/areas/faq.css` with the
   prefix `faq-` and tokens only:
   ```css
   /* Area styles: FAQ (/faq/). Prefix "faq-". Tokens only, so dark mode works. */
   .faq-item { border-bottom: 1px solid var(--c-line); padding-block: 0.75rem; }
   .faq-item > summary { cursor: pointer; font-weight: 600; color: var(--c-ink); min-height: 2.75rem; }
   ```
   and add one line at the end of `src/assets/css/main.css`, after the other area imports:
   `@import "./areas/faq.css";`
5. **A script (optional).** Create `src/assets/js/faq.js` (copied by itself) and list it in
   `pageScripts` (done in step 1). Register Alpine components on `alpine:init`, as the other page
   scripts do:
   ```js
   /* /faq/ — open one question at a time. Loaded before Alpine (defer). */
   (function () {
     "use strict";
     document.addEventListener("alpine:init", function () {
       window.Alpine.data("faqList", function () {
         return {
           init: function () {
             var items = this.$el.querySelectorAll("details");
             items.forEach(function (d) {
               d.addEventListener("toggle", function () {
                 if (d.open) items.forEach(function (o) { if (o !== d) o.open = false; });
               });
             });
           },
         };
       });
     });
   })();
   ```
   Use `GV.url("/path")` for any site address in a script.
6. **Sitemap: nothing to do.** Every page is added by itself, in both languages. Add `"/faq/"` to
   `REQUIRED` in `src/pages/sitemap.11ty.js` only if you want a warning when it goes missing.
7. **Search: nothing to do** (step 2 did it). A page that is **not** in `nav.js` is not found by the
   site search unless you add it in `searchIndex` in `eleventy/filters/library.js` (search for
   `site pages (always present`).
8. **Offline and app (optional):** recipe [12.8](#128-save-a-page-for-offline-use-or-add-an-app-shortcut).
9. **Check on your computer:** `npx @11ty/eleventy --serve`, open <http://localhost:8080/faq/> and
   <http://localhost:8080/es/faq/>, try dark mode, a phone width and larger text (the "Aa" panel).
   Then `$env:I18N_STRICT = "1"; npx @11ty/eleventy` (no missing keys) and
   `python -m unittest discover -s tests`.
10. **Publish:** commit and push to `main`. A few minutes later the page is live at
    <https://neta65.github.io/aagrapevine/faq/> and <https://neta65.github.io/aagrapevine/es/faq/>.

### 12.5 Rename a page and keep the old address working

Example: you move `/faq/` to `/questions/`.

1. In `src/pages/faq.njk` change `permalink` to `…questions/index.html`. In `nav.js` change
   `url: "/questions/"`. If you added `"faq/"` to the offline save list or an app shortcut
   (recipe 12.8), change it there too.
2. Copy `src/pages/documents-redirect.njk` to `src/pages/faq-redirect.njk` and change three things:
   the `permalink` (the **old** address, `…faq/index.html`), the `target`
   (`{%- set target = "/questions/" | lurl(lang) -%}`) and the texts (title and "moved" keys).
3. Result: `/faq/#anything` and `/es/faq/` send visitors to `/questions/#anything` and
   `/es/questions/`, keeping the `#anchor` and `?query`. The stub is `noindex`, out of the sitemap and
   out of the search. QR codes and links printed with the old address keep working.

### 12.6 Read a new setting from `config/site.yml`

- **Under `site:`** a new key is available at once. Add `faq_intro: "…"` under `site:` and write
  `{{ site.faq_intro }}` in a template (for two languages add `faq_intro_es` and use
  `{{ site | pick(lang, "faq_intro") }}`).
- **A new top-level section** needs one line in `src/_data/site.js`. Example, a section
  `faq:` in `config/site.yml`:
  ```yaml
  faq:
    show_zoom_help: true
  ```
  In `src/_data/site.js`, inside the returned object, next to `digest: cfg.digest || {},` add:
  ```js
      faq: cfg.faq || {},
  ```
  Now `{% if site.faq.show_zoom_help %}…{% endif %}` works. Without that line `site.faq` is empty and
  nothing shows (no error).

A settings change rebuilds the site like a template change. See [Settings](settings.md) for every
section that exists today.

### 12.7 Change a number or a rule on a page

Example: on the home page a bulletin post shows in full when it is at most 700 characters; longer
posts show a teaser and "Read more". To allow 1,000 characters:

1. Open `src/pages/index.njk` and search for the section's heading id `ann-title`.
2. A few lines below, find `body.length <= 700` and change it to `body.length <= 1000`.
3. How many posts show is decided earlier in the file, in the `set` lines just after the hero:
   search for `homeAnnouncements) | limit(2)`.

**Where it shows:** the "From the committee" section of `/` and `/es/`. The same approach works for
every home section (section 5.2): find the heading id, then the filter call and its number, for
example `homeDrive(6)` (committee uploads) or `homeNewestPdfs(6)` (newest documents). Check a phone
width and a wide screen after the change: the grids are designed for these counts.

### 12.8 Save a page for offline use, or add an app shortcut

- **"Save key pages for offline"** (the button on `/offline/` and in the "Aa" panel) keeps the pages
  listed in `const save = [` in `src/pages/sw.11ty.js`: today the home page, `meetings/`, `monthly/`, this month's page,
  `contribute/`, `shop/`, then `accessibility/`, `orientation/` (with every session) and `tracker/`.
  To add `/faq/`, add `"faq/"` to that list. Write the English path only: the worker adds `es/` for
  Spanish visitors. Keep the existing entries (`tests/test_pwa.py` checks some of them).
- **An app shortcut** (long-press on the installed app's icon): add one line to the `shortcuts:`
  list in `src/pages/manifest.11ty.js`, after the three that are there:
  ```js
  { name: t("nav.faq"), url: `${home}faq/` },
  ```
  Shortcuts should also be in the save list, so they open without a signal.
  > **Note:** the install steps on `/offline/` name the three shortcuts in one sentence ("On Android,
  > touch and hold the icon to go straight to {a}, {b} or {c}.": the key `pwa.app.more_shortcuts` in
  > `src/_i18n/pwa.json`, filled in `src/pages/offline.njk`), and `tests/test_pwa_install.py` checks
  > that this sentence and the manifest name exactly the same three pages (search it for
  > `more_shortcuts` and for `"orientation/")`). A fourth shortcut therefore also needs that sentence
  > (both languages), its line in `offline.njk` and those two checks updated in the same commit, or
  > **Code check** shows a red ✗. Swapping one of the three for another page needs the same edits.

**Test:** `python -m unittest tests.test_pwa tests.test_pwa_worker tests.test_pwa_install`.

### 12.9 Change the share picture or the app icons

- **Share picture** (what WhatsApp or Facebook show for a link): `src/assets/img/og-default.png`
  (English) and `og-default-es.png` (Spanish), 1200 × 630 pixels. After replacing them, change `?v=2`
  to `?v=3` in `base.njk` (search for `og-default.png?v=2`: both pictures are on that one line):
  apps keep old previews until the address changes. Use no faces and no full names (section 18).
- **App icons:** `src/assets/img/app-icon-*.png`, made by `scripts/dev/make_app_icons.py`.
  `tests/test_pwa.py` checks their sizes and safe areas.

### 12.10 Add an icon

Use any icon name from lucide.dev: `{% icon "calendar-days", "size-5" %}`. For your own drawing, save
it as `src/_includes/icons/<name>.svg` in the same style as `grapes.svg` (a 24 × 24 `viewBox`,
`fill="none"`, `stroke="currentColor"`). Your file wins over a Lucide icon of the same name. A
misspelled name prints nothing and the build log says `[icon] missing icon: <name>`. The same happens
with an icon that is newer than the copy of Lucide the site installs: the names that work are the file
names in `node_modules/lucide-static/icons/` after `npm ci`.

---

## 13. The installable app and offline use, in short

The site can be installed on a phone like an app, and it keeps working with a weak signal.

- **The manifest** (`/manifest.webmanifest`, `/es/manifest.webmanifest`, made by
  `src/pages/manifest.11ty.js`): name "Grapevine / La Viña — NETA 65", short name "GV/LV 65", icons,
  colours, three shortcuts (Meetings, Monthly toolkit, GVR / RLV 101).
- **The service worker** (`/sw.js`): `src/pages/sw.11ty.js` writes `const CONFIG = { version, base,
  shell, required, offline, save, files, … }` above the logic in `src/_includes/pwa/sw-core.js`.
  `pwa.js` registers it for the whole site.
- **What it does:** pages come from the network first (a saved copy only when offline, on a server
  error or after 4 seconds; the last 80 pages are kept). CSS, scripts, fonts and pictures come from
  the browser's copy and refresh in the background; files with `?v=` never change under the same
  address. It never stores other sites, feeds or the `.ics` calendar.
- **Updates:** the worker's version is `build.version`, a fingerprint of the code. A code change makes
  a new version: it installs in the background and visitors see "Updated — reload". A content,
  settings or string change does not (pages are fetched fresh anyway).
- **The booth display's own offline copy:** started with internet, the booth asks the worker (`BOOTH_SAVE`) to
  save both About pages, `/about/booth.json` and the files its slides use (the photos and videos under
  `/about/booth/media/`) in the cache `gvlv-booth-v1`. A new worker version keeps that cache and never trims it:
  only the booth's own list removes files (a new show, or "Remove the offline copy" in the player's Settings →
  Offline). The worker answers `/about/booth.json` network first (after 6 seconds, the saved copy) and the media
  from the saved copy first, byte ranges too, so a video plays and seeks offline (`CONFIG.booth` in `sw.11ty.js`;
  `boothMedia`, `boothJson` and the `BOOTH_SAVE` / `BOOTH_STATUS` / `BOOTH_CLEAR` messages in `sw-core.js`).
  "Save key pages for offline" does not make this copy. More: [Booth display](booth.md).
- **Where visitors control it:** the "Aa" panel (install, save pages, Data saver) and
  `/offline/` ("Saved pages & app", with install steps for iPhone, Android and computers).

---

## 14. What happens after you push

A commit to `main` (on github.com or `git push`) starts the workflows by itself:

| You changed | Workflows that start | What they do |
|---|---|---|
| Templates, CSS, JS, strings or data files in `src/`, `eleventy/`, `eleventy.config.js`, `config/`, `content/`, `package.json` / `package-lock.json` | **Code check** and **Update & Deploy** | Code check: a test build exactly like GitHub Pages (`I18N_STRICT=1`) and the Python tests; nothing is published. Update & Deploy: a quick content sync (Google Drive, the bulletin, podcasts, the daily quote), then build and publish. |
| `data/translations/overrides.yml` or `glossary.yml` | both | the same |
| Only `tests/` | Code check | nothing is published |
| Only Markdown documentation outside `src/` and `content/` (including this `how-to/` folder), or `docs/` | none | |

- **How long:** the site is live **a few minutes** after the push (watch the run in the **Actions**
  tab). A page may take up to about 10 more minutes to show the change everywhere.
- **If the build fails,** GitHub Pages keeps the previous site. Nothing half-built goes live.
- **The daily runs** (the full daily update, the midday quick run and the Morning check's morning
  refresh) also rebuild the site with the newest code. GitHub's schedules are set 4 hours early on
  purpose, because GitHub starts them late; see
  [Automation and troubleshooting](automation-and-troubleshooting.md).
- **Visitors' copies:** a code change (templates, `src/assets`, `eleventy/`, `eleventy.config.js`,
  `package-lock.json`) gives the CSS and JS a new `?v=` and the service worker a new version, so
  returning visitors get the new files ("Updated — reload" in the installed app). A change to strings,
  settings or content does not change the version; pages are fetched fresh anyway.

> **Note:** `docs/OPERATIONS.md` says the version fingerprint also covers `config/`. The code
> (`src/_data/build.js`, the list `ROOTS`) hashes only `src/_includes`, `src/pages`, `src/assets`
> (without `src/assets/cache`), `eleventy/`, `eleventy.config.js` and `package-lock.json`. Follow the
> code: settings, strings (`src/_i18n`) and global data (`src/_data`) do not change the version.

**Where errors are reported:**

- A red ✗ next to the commit on github.com (and, when GitHub notifications are on, an e-mail to the
  person who pushed).
- **Update & Deploy** → the run → job **Build & publish website** → step **Build the website**.
- **Code check** → the run → job **Build the website** → step **Build the website (as for GitHub
  Pages)**; the tests are in the job **Python tests (offline)**.
- The run summary: "**Website:** N pages, M MB" (Code check adds "— builds fine with this change").
- Warnings that do not stop the build, in the same log: `[links] …` (a link in the data was repaired
  or hidden), `[icon] missing icon: …`, `[sitemap] missing page(s): …`, `[search-index] …`,
  `[content] could not read data/site/…`, `[booth] N problem(s) — left out of the booth display: …` (a row of
  `content/booth/booth.csv`, a Drive booth file or a live item the booth display could not use).
- `/status/` shows the **content sources**, not code problems.

---

## 15. Check your change on the live site

1. Open the page in **both** languages, for example
   <https://neta65.github.io/aagrapevine/events/> and <https://neta65.github.io/aagrapevine/es/events/>.
   Reload once (or use a private window) so the browser does not show its older copy.
2. Open <https://neta65.github.io/aagrapevine/build.json>. It looks like this (values change with
   every build):
   ```json
   {"v":1,"built":"2026-10-02T23:40:50.636Z","day":"2026-10-02","tz":"America/Chicago","quotes":{"gv":"2026-10-02","lv":"2026-10-02"},"data":"2026-10-02T23:40:30Z","full":"2026-10-02T22:31:32Z","run":"37078627589","version":"ab2671a92b","commit":"c62f8ea"}
   ```
   `commit` is the first 7 characters of the commit that was built: it should match yours (or a
   later one). `version` changes only when code changed.
3. The footer's "Last updated" is the build time, shown in the visitor's own time zone.
4. Check a phone width, dark mode and larger text ("Aa" panel). Shared pieces (menus, footer, hero)
   show on every page, so look at two or three other pages too.
5. Changed the menus or added a page? Try the site search (`/search/?q=faq`).

---

## 16. Going further: filters, data files and tests

### 16.1 Add your own filter (a "view model")

When a template needs data prepared (sorted, merged, translated), write a filter instead of long
template logic. Create a file in `eleventy/filters/`; it is loaded by itself:

```js
// eleventy/filters/faq.js — the FAQ page's filters (loaded by eleventy.config.js, like every file here)
export default function (eleventyConfig) {
  // {{ faq.items | faqItems(lang) }} → [{ q, a }] in the page language, empty questions left out
  eleventyConfig.addFilter("faqItems", (items, lang) =>
    (Array.isArray(items) ? items : [])
      .map((it) => ({ q: (lang === "es" && it.q_es) || it.q || "", a: (lang === "es" && it.a_es) || it.a || "" }))
      .filter((it) => it.q));
}
```

The second argument holds `translateKey`, `pickLang`, `fmtDate`, `toDate` and `esMeridiem` if you
need them (`export default function (eleventyConfig, { translateKey }) { … }`).

### 16.2 Add a global data file

A file in `src/_data/` becomes a variable in every template. For example, questions kept in a new
settings file `config/faq.yml`:

```js
// src/_data/faq.js — `faq` in every template, from config/faq.yml (empty when the file is missing)
import fs from "node:fs";
import * as yaml from "js-yaml";

export default function () {
  if (!fs.existsSync("config/faq.yml")) return { items: [] };
  const cfg = yaml.load(fs.readFileSync("config/faq.yml", "utf8")) || {};
  return { items: Array.isArray(cfg.items) ? cfg.items : [] };
}
```

```yaml
# config/faq.yml
items:
  - q: "When does the committee meet?"
    q_es: "¿Cuándo se reúne el comité?"
    a: "Once a month on Zoom. Everyone is welcome."
    a_es: "Una vez al mes por Zoom. Todos son bienvenidos."
```

In the template: `{% for it in faq.items | faqItems(lang) %}<details><summary>{{ it.q }}</summary><p>{{ it.a }}</p></details>{% endfor %}`.
Keep only the default export in a data file: with another (named) export, Eleventy hands the
templates the module instead of calling the function (the comment at the top of
`src/_data/meeting.js` says so). Paths like `config/faq.yml` are relative to the repository folder,
where the build runs.

**New synced content** (a new `data/site/<name>.json` written by the sync) also needs its name added
to the `FILES` list in `src/_data/db.js`; then it is `db.<name>` everywhere, with its links cleaned.
The sync side is in [Automatic sources](automatic-sources.md) and `docs/DATA_SCHEMA.md`.

### 16.3 Tests

Set up Python once (Windows PowerShell, in the repository folder):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Then run all the tests:

```powershell
python -m unittest discover -s tests
```

Some tests run the site's JavaScript with Node; without Node or without `npm ci` they are
**skipped**, not failed. Code check runs them all on GitHub (only the few that need the translation
models are skipped there). To run just the ones for your change:

| You changed | Run (`python -m unittest …`) |
|---|---|
| Strings in `src/_i18n` | `tests.test_i18n_keys` (+ `tests.test_accessibility` for `comfort.*` or `access.*`); some tests check exact words, so run them all once |
| Header, footer, menus | `tests.test_header_footer tests.test_bulletin tests.test_pwa_install tests.test_expenses_page` |
| A card on the right of a hero | `tests.test_hero_aside` |
| The service worker, the manifest, icons, the save list | `tests.test_pwa tests.test_pwa_worker tests.test_pwa_install` |
| Events, the calendar feed, meeting times | `tests.test_events_feeds tests.test_recurring_events tests.test_build_times` |
| Home page filters | `tests.test_home` |
| The digest page (it must match the monthly e-mail) | `tests.test_digest_parity tests.test_send_digest` |
| Things that hide themselves when their time is over | `tests.test_app_expire tests.test_client_dates` |
| Portfolio tiles | `tests.test_portfolio` |
| Tracker | `tests.test_expenses_core tests.test_expenses_app tests.test_expenses_page` |
| Presentations | `tests.test_presentations tests.test_presentations_core tests.test_presentations_build` |
| The booth display | `tests.test_booth_csv tests.test_booth_build tests.test_booth_core tests.test_booth_page tests.test_booth_media tests.test_booth_names tests.test_booth_sync tests.test_pwa_worker` |

Each test file starts with a short description of what it checks. Read it when a test fails: it
usually names the rule you broke.

---

## 17. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| The GitHub build failed with `Missing i18n key: faq.title` | A template uses a key that no `src/_i18n/*.json` file has | Add the key with `en` and `es`. Check on your computer with `$env:I18N_STRICT = "1"; npx @11ty/eleventy`. |
| The build failed with `Missing i18n key: undefined` | A dropdown entry in `nav.js` has no `descKey` | Add `descKey` and its string (section 6.2) |
| The build failed with `[carry] config/carry.yml: …` (or `[orientation]`, `[history]`, `[expenses]`, `[presentations]`) | A problem in that settings file (a missing `en` / `es` text, an unknown id, a date it cannot read …); on GitHub it stops the build | The message names the problem. Fix the file ([Settings](settings.md), [Presentations](presentations.md)); check on your computer with `$env:I18N_STRICT = "1"; npx @11ty/eleventy` |
| **Code check** is red after you only changed some words | A test checks those exact words (for example "Online on Zoom", the menu names "Bulletin" and "QR Post") | The failing test names the words it expected: change them in the test too, in the same commit (section 12.1) |
| A page shows a raw key such as `nav.faq` (on your computer) | The same missing key; locally the build does not stop | Add the key |
| Links go to `/aagrapevine/aagrapevine/…` | `\| url` used inside an HTML attribute | Remove `\| url` (section 9.1, rule 2) |
| A link works on your computer but is "not found" on the live site | The address is in a `data-*` attribute, an inline `style`, JSON or a script, which the build does not rewrite | Use `\| siteUrl(site)`, or `GV.url()` in a script (rule 3) |
| A link on a Spanish page opens the English page | The template wrote the path without `\| lurl(lang)` | Add `\| lurl(lang)` |
| A PDF or picture link is "not found" on Spanish pages only | `\| lurl(lang)` added `/es/` to a file address | Leave files without `lurl` |
| A new utility class does nothing | The class is built from pieces, or written only in `src/_data`, `config/` or content, which Tailwind does not read | Write the whole class name in a template, or use the area CSS file |
| A style change does not show on your computer | Saving only a `.css` file does not start a rebuild | Save any template, or stop and start the server |
| A style change does not show on the live site | The browser kept the old copy | Reload; after a code change the CSS address gets a new `?v=` by itself |
| Something looks wrong in dark mode | A fixed colour (`#hex`, `text-white`) where a token belongs | Use `var(--c-…)` or a token class (section 10.2) |
| The new page is not in the menu, or the menu does not underline it | No entry in `nav.js`, or its `page` is not the template's `pageKey` | Add or fix the entry (section 6.2) |
| The new page is not found by the site search | It is not in `nav.js` | Add it to `nav.js`, or to the site pages in `searchIndex` (`eleventy/filters/library.js`) |
| The build log says `[icon] missing icon: …` | A misspelled icon name | Use a name from lucide.dev, or add an SVG to `src/_includes/icons/` |
| `tests.test_i18n_keys` fails with "a key in two files" | The same key in two JSON files | Keep one |
| `tests.test_hero_aside` fails | A hero card without the `{% call(slot) … %}` form or without `opts.side`, or a video card (`ui.heroAsideVideo`) on a page that does not load lite-youtube | Follow the rule in section 6.4; a video card needs `/assets/vendor/lite-yt-embed.js` in `pageScripts` and `/assets/vendor/lite-yt-embed.css` in `pageStyles` |
| A new `site.<name>` setting is always empty | A new top-level section of `config/site.yml` is not passed by `src/_data/site.js` | Add it there (recipe 12.6) |
| A page you edited shows old content after the push | The run is still going, or the page comes from the daily data | Wait for the Update & Deploy run; content like articles updates in the daily full run |
| The local site has no content | `data/site/*.json` is missing or old | `git pull` |
| `npm ci` fails or `npx` is not found | Node is missing or older than 20 | Install Node 22 LTS, open a new PowerShell window |
| Git Bash builds links that point into Git's own program folder (`…/Program Files/Git/aagrapevine/`) | Git Bash rewrote `PATH_PREFIX` | Add `MSYS_NO_PATHCONV=1` (section 3) |
| The browser on your computer shows pages from an older build | The service worker on `localhost` kept them | DevTools → Application → Storage → Clear site data |
| A row or a Drive file is missing from the booth display | It has a mistake, or says a word the booth never shows: the build left it out | The build log's `[booth]` lines and the player's Settings → Slides name it ([Booth display](booth.md)) |

---

## 18. Good practice and AA principles

- **Anonymity.** Never put full names or faces in templates, pictures (the share picture, app
  screenshots), alt texts, examples or test files. Writers' names show exactly as the magazines
  printed them (first name and initial). Everything in the Drive panel folder is public too.
- **Attraction, not promotion.** No ads, trackers or analytics. Outside media load only when
  the visitor asks: videos through lite-youtube (only a thumbnail until Play), Instagram posts only
  after "Show post here". Keep the words informative and welcoming, never pushy.
- **The repository is public.** No passwords, secrets or private e-mail addresses in code or settings.
  Use the committee's address (grapevine@neta65.org, `site.contact_email` in `config/site.yml`) or an
  official `@aagrapevine.org` address. The Drive **root** folder is never linked (it can hold private
  files): pages link the current panel folder only.
- **Both languages, always.** Every new string gets `en` **and** `es`. Test every change on `/x/` and
  `/es/x/`. On Spanish pages La Viña usually comes first.
- **Safety.** Keep `autoescape` on. Never use `| safe` on text that comes from outside (titles,
  captions); use it only on our own strings and on `md` output. Links from data go through `| extUrl`.
  JSON inside a `<script>` goes through `scriptJson` (in a template: `| jsonScript | safe`).
- **Accessibility.** Buttons at least 44 px on phones, a label for every icon-only button, colour
  never the only signal. Check larger text, high contrast and dark mode in the "Aa" panel.
- **Visitors' privacy.** What a visitor types (Tracker, checklists, settings) stays in their own
  browser. Do not add code that sends it anywhere.
- **Small steps.** Change one thing, check it on your computer, push, and watch the run. A red ✗ is
  easy to fix when the change was small.

---

## 19. See also

- [How-to index](README.md): the big picture and "I want to… go here"
- [Settings](settings.md): `config/site.yml` and the other settings files
- [Translations](translations.md): `src/_i18n`, `overrides.yml`, `glossary.yml`, strict mode
- [Flyers and events](flyers-and-events.md): how events reach `/events/`, and adding a field to every event card
- [Bulletin](bulletin.md): bulletin posts on `/bulletin/` and the home page
- [Presentations](presentations.md): the web presentations on `/orientation/`
- [Booth display](booth.md): the booth display on `/about/`
- [Automatic sources](automatic-sources.md): where `data/site/*.json` comes from
- [Email and alerts](email-and-alerts.md): the monthly digest e-mail (the twin of `/digest/`)
- [Automation and troubleshooting](automation-and-troubleshooting.md): the workflows, runs and schedules
- [Drive panel folder](drive-panel-folder.md), [File types](file-types.md), [Photos, slides and reports](photos-slides-reports.md)
- Code: [eleventy.config.js](../eleventy.config.js), [src/_data/nav.js](../src/_data/nav.js),
  [src/_data/site.js](../src/_data/site.js), [src/_data/db.js](../src/_data/db.js),
  [src/_includes/layouts/base.njk](../src/_includes/layouts/base.njk),
  [src/_includes/macros/ui.njk](../src/_includes/macros/ui.njk),
  [src/assets/css/main.css](../src/assets/css/main.css), [src/pages/sw.11ty.js](../src/pages/sw.11ty.js),
  [src/pages/sitemap.11ty.js](../src/pages/sitemap.11ty.js)
- Background: [docs/OPERATIONS.md](../docs/OPERATIONS.md) ("Running locally") and the
  repository [README](../README.md)
