# Grapevine / La Viña — NETA 65 Committee website

[![Website update](https://github.com/NETA65/aagrapevine/actions/workflows/update.yml/badge.svg)](https://github.com/NETA65/aagrapevine/actions/workflows/update.yml)

**Website:** <https://neta65.github.io/aagrapevine/> · **En español:** <https://neta65.github.io/aagrapevine/es/>

The website of the **Northeast Texas Area 65 (NETA 65) Grapevine & La Viña Committee**.
It **updates itself every morning** and is **fully bilingual (English + Spanish)**. Nobody has
to hand-edit pages, retype flyers or translate anything any more.

> **Setting it up for the first time?** Use the [first-run checklist](#11-first-run-checklist)
> (details in [docs/SETUP-GITHUB.md](docs/SETUP-GITHUB.md), about 15 minutes).

> **How-to guides:** [how-to/README.md](how-to/README.md) explains, step by step and with examples, every file the
> committee can place (Drive files, events, bulletin posts, the booth display, settings, translations) and how it
> becomes the website.

## Resumen en español

Sitio web del **Comité de Grapevine y La Viña del Área 65 del Noreste de Texas**.
**Se actualiza solo todos los días**, en **inglés y español**. La **cita del día** de Grapevine y La Viña y
las fechas del nuevo día quedan en el sitio **antes de las 5:30 a. m.** (hora del Centro) con la **alarma de
la mañana** (sección [10 d](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)).

- Trae automáticamente los **artículos nuevos** de Grapevine y La Viña, **los documentos oficiales** (PDF) de
  aagrapevine.org y aalavina.org — **cada uno una sola vez**, con sus ediciones en inglés, español y francés
  en la misma tarjeta —, los episodios de **los dos podcasts** (el de AA Grapevine y la **Reunión Abierta
  Semanal de Grapevine**), los **videos de YouTube** y las **publicaciones de Instagram**, y lo
  **traduce todo** (inglés ⇄ español) con software libre.
- **Lo único que usted hace:** subir archivos a las carpetas del comité en **Google Drive**
  (dentro de la carpeta del Panel 77). Al día siguiente aparecen en el sitio: informes, notas, presentaciones y
  talleres en el **Portafolio** (`/es/portfolio/`; la antigua dirección `/es/documents/` lleva allí).
  - Un **volante** con la fecha al inicio del nombre se convierte en **evento** — con hora y lugar si
    los escribe: `2027-03-14 Asamblea de primavera 9am @ Tyler TX.pdf`
  - Un **Google Doc** en `boletín` (o `bulletin`) se convierte en un aviso del **Boletín**; `(fijado)` lo
    deja arriba, `(desde 2027-02-01)` lo publica ese día (con la actualización de esa mañana) y
    `(hasta 2027-02-01)` lo oculta después de esa fecha.
  - Cada **subcarpeta** de `fotos` es un **álbum**. Por favor, solo fotos donde **no se reconozca la
    cara** de ningún miembro de AA.
- **Tienda** (`/es/shop/`): el **libro del mes** de Grapevine y La Viña y los **precios de suscripción** por
  región, leídos cada día de las tiendas oficiales (toda compra se hace allí), y los **artículos especiales**
  (tarjetas de ocasión, agenda de bolsillo, calendario de pared y, en temporada, las tarjetas para las
  fiestas), leídos cada semana. Cuando AA Grapevine anuncia **nuevos precios**, un bloque en `config/site.yml`
  (`price_changes:`) los avisa desde el día del anuncio y los pone solos en su día (sección
  [When Grapevine announces new prices](#when-grapevine-announces-new-prices)). **Kit del mes**
  (`/es/monthly/`): todo lo de este mes — la reunión del comité, los eventos, las fechas límite para
  historias, las revistas del mes y el libro del mes —, un cartel para cada mes (descargar en PNG, compartir,
  imprimir), las 10 maneras de poner una edición a trabajar y cada mes también como mensaje para WhatsApp o
  correo. El **Resumen mensual** (`/es/digest/`) reúne todo lo nuevo del mes pasado (el correo mensual,
  sección [10 c](#c-monthly-e-mail-digest-keep-every-district-informed), es la misma edición). La **reunión
  abierta semanal de La Viña** (jueves, en español) está en `/es/meetings/#weekly-open`. La página
  **Reuniones** (`/es/meetings/`) también reúne las **reuniones de Grapevine** de los grupos de AA de nuestra
  Área y de las áreas cercanas (de las 8 listas de reuniones que usa la página del Grupo Rowlett). El
  **informe de GV/LV** para la reunión del distrito está en `/es/monthly/#report` (la antigua página
  *Distritos* ya no existe; su dirección lleva allí).
- **RLV / GVR 101** (`/es/orientation/`): seis lecciones breves para los nuevos RLV y GVR (el Panel 77 empieza
  en enero de 2027), cada una con preguntas de repaso; también como **diapositivas** para una reunión del
  distrito ("Presentar diapositivas") y como **hoja para imprimir** (una por lección). El texto está en
  `config/orientation.yml` (inglés y español en el mismo archivo).
- **Pantalla para la mesa** (`/es/about/#booth`): una presentación que se reproduce sola en un televisor, una
  computadora portátil o una tableta en nuestra mesa en asambleas y eventos, en español, en inglés o en ambos;
  abierta una vez con internet, sigue funcionando sin conexión. Guía (en inglés): [how-to/booth.md](how-to/booth.md).
- **Instalar como app:** la página **Páginas guardadas y app** (`/es/offline/`; al pie de cada página y en el
  menú del celular, en *Más*) tiene, después de las páginas guardadas, los pasos para cada teléfono y
  navegador, y abre los del teléfono de quien la visita («Tu dispositivo»). En Chrome y Samsung Internet
  (Android) basta un toque en **Instalar** (no «Crear acceso directo»); en iPhone, Safari → **Menú de
  página** (iOS 27) o **Más** (iOS 26) → **Compartir** → **Agregar a Inicio**, con **Abrir como app web**
  activado. Para pasarla a un grupo, envíen el enlace `https://neta65.github.io/aagrapevine/es/offline/#steps`
  (el botón **Enviar esta página** manda ese mismo enlace, y los enlaces a la antigua página de instalación
  llevan allí). En los celulares, un aviso discreto la ofrece a partir de la tercera página visitada (la
  segunda si el navegador permite instalarla con un toque); «Ahora no» = 30 días, y nunca aparece dentro de
  otras apps, sin conexión ni en la app ya instalada.
- **Escritores publicados** (`/es/published/`): las historias recientes de escritores del Área 65 y de Texas y,
  debajo, el **archivo de escritores de Texas** (`/es/published/#archive`): cada historia de un escritor de Texas
  en los archivos en línea de Grapevine (desde 1944) y La Viña (desde 1996). Se arma con dos exportaciones en CSV
  de esos archivos en línea, guardadas en la carpeta `content/archive` del repositorio (se usa la más reciente de
  cada revista, según la fecha de su nombre: `aagrapevine_archive_2026-11-05.csv`), y las historias de cada nueva
  edición se suman solas. Guía (en inglés): [how-to/writers-archive.md](how-to/writers-archive.md).
- **Usar sin conexión:** menú **Aa** (arriba en cada página) → **Sin conexión y app** → **Guardar páginas
  clave** (Inicio, Reuniones, el kit del mes, Comparte tu historia, Tienda, Escritores publicados con el archivo
  de Texas, Accesibilidad y RLV / GVR 101),
  que luego se abren sin señal; las páginas que se abren también se guardan (las últimas 80). El **Ahorro de
  datos** apaga las imágenes, las vistas previas de video y el arte animado. Detalles:
  [Install the app, offline use and Data saver](#install-the-app-offline-use-and-data-saver).
- **Lectura y pantalla:** el mismo menú **Aa** agranda el texto (hasta 150%), da más espacio entre líneas y
  letras, pone alto contraste, detiene las animaciones y lee la página en voz alta; se guarda solo en ese
  dispositivo. La página **Accesibilidad** (`/es/accessibility/`, enlace al pie de cada página) explica
  esos ajustes, los subtítulos de los videos, los videos en lengua de señas (ASL), el audio y **cómo unirse
  por teléfono** a nuestras reuniones de Zoom (números y código para teléfono: `config/site.yml` →
  `phone_access`).
- **Ajustes** (reunión del comité, Zoom, correo, eventos de cada mes como la mesa en CityWide Dallas o el
  taller mensual de La Viña por Zoom — `host: "lv"`: un evento de La Viña, no nuestro): archivo `config/site.yml`.
  **Corregir una traducción:** `data/translations/overrides.yml`.
- **Eventos sin volante** (talleres, asambleas): un archivo en `content/events`. Si todavía faltan
  detalles, `tentative: true` muestra "Detalles por confirmar"; el lugar en español va en `location_es`.
- **¿Funciona todo?** Página **/es/status/** del sitio (junto a *Cita del día*: a qué hora llegaron las
  citas de hoy), o la pestaña **Actions** en GitHub.
  **Actualizar ya:** GitHub → **Actions** → **Website update** → **Run workflow**. **Poner ya la cita de
  hoy:** **Actions** → **Morning check (new day by 5:30 AM)** → **Run workflow** (solo hace lo que falta:
  desde las 2 a. m., hora del Centro, si la revista ya publicó la cita, la trae; si no, lo dice; si otra
  actualización está en curso, primero la espera). Un cambio guardado en GitHub se publica en unos 5 minutos:
  antes se pasan las pruebas del código, y si fallan, el sitio sigue con la versión anterior.

Las instrucciones detalladas están abajo (en inglés); puede usar el traductor de su navegador.

---

## The short version

| Every day the site automatically… | You only… |
|---|---|
| puts the new day and the Grapevine and La Viña **daily quote** up by **5:30 AM Central** (with the [morning alarm](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)) | *(once)* set up the morning alarm — about 15 minutes |
| picks up new **Grapevine** and **La Viña** magazine stories | **upload files** to the committee's Google Drive folders (flyers, reports, notes, slides, photos) |
| searches **aagrapevine.org** and **aalavina.org** for every **PDF** (flyers, catalogs, GVR/RLV kits, order forms…) | *(optional)* change a setting in **`config/site.yml`** |
| adds new episodes of **both podcasts**, new **YouTube** videos and **Instagram** posts | |
| turns dated **flyers** into **events** and Drive docs into **bulletin posts** | *(rarely)* fix a translation in **`data/translations/overrides.yml`** |
| **translates everything** English ⇄ Spanish (free, open-source, no account needed) | |
| rebuilds and publishes the website — and keeps the last good version if a source is down | |

Everything runs for free on GitHub (GitHub Actions + GitHub Pages) using open-source software.
No paid services, no passwords or API keys required.

---

## Contents

1. [What updates automatically](#1-what-updates-automatically)
2. [Your part: uploading to Google Drive](#2-your-part-uploading-to-google-drive)
3. [Changing settings (`config/site.yml`)](#3-changing-settings-configsiteyml)
4. [The monthly GV/LV report](#4-the-monthly-gvlv-report)
5. [Fixing a translation](#5-fixing-a-translation)
6. [Bulletin posts and events without Drive (optional)](#6-bulletin-posts-and-events-without-drive-optional)
7. [Running the update right now](#7-running-the-update-right-now)
8. [Is everything working?](#8-is-everything-working)
9. [Instagram: how the site reads it (please read)](#9-instagram-how-the-site-reads-it-please-read)
10. [Optional upgrades](#10-optional-upgrades) (Google API key · Instagram token · monthly e-mail · the morning alarm)
11. [First-run checklist](#11-first-run-checklist) (and what to expect on day 1)
12. [Using your own address (custom domain)](#12-using-your-own-address-custom-domain)
13. [Replacing the old site](#13-replacing-the-old-site)
14. [Housekeeping](#14-housekeeping)
15. [Troubleshooting](#15-troubleshooting)
16. [How it works](#16-how-it-works)
17. [Credits and licenses](#17-credits-and-licenses)

---

## 1. What updates automatically

**With the [morning alarm](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended) set up, by 5:30 AM
Central every day** the new day's dates and both **daily quotes** are on the site (unless a magazine
publishes its quote later than that): at 4:30 AM the alarm starts the **Morning check**, which runs a short
**morning refresh** of the **Website update** job (the daily quote, Google Drive, the bulletin and the
podcasts — on the 1st also the new magazine issues, on the 1st and the 15th the Book of the Month; about
3 minutes) and checks the live site. If a magazine has not published its quote yet, it asks again every
10 minutes until 7 AM (after that, each Morning check asks once). Without the alarm, GitHub's own hourly
backstop starts the Morning check whenever GitHub gets to it — often hours late.

The **full update** (every source, the PDF search) runs every night on GitHub's own schedule, and two short
runs, the **midday refresh** and the **evening refresh**, bring the day's Drive files, bulletin posts, podcasts
and archive files during the day. GitHub starts timed runs 4 to 6 hours late (sometimes 8), so all three are
scheduled about 4 hours early — 2:17 AM, 7:07 AM and 3:07 PM Central in summer (CDT; an hour earlier in winter,
CST: 1:17 AM, 6:07 AM, 2:07 PM) — and usually start around 6 to 8 AM, 11 AM to 1 PM and 7 to 9 PM (summer times).
The nightly one is set so that it is not running at 4:30 AM, when the morning alarm starts the morning refresh: on
time it is done long before, and with GitHub's usual delay (4 hours or more) it starts after the morning refresh is live.
Only the nightly one is a full update: any other schedule is a quick refresh. A full update usually takes 10 to 15
minutes (at the very most a little over 2 hours, when the PDF search and the translations use all their time). On
the 1st of the month, and after a day GitHub skipped, the Morning check also starts the full update — even when
today's quotes were already on the site. The site also updates about 3 minutes after someone saves a change to the
settings or content (a page may take up to about 10 more minutes to show it everywhere). A change to the **code**
takes about 5: that run **tests the code first** and publishes only when the tests pass, so a change that breaks
something never goes live (the site keeps the version before). A slip in the content or the settings does not stop
the site from updating: the update leaves out what it cannot read, and the *Code check* goes red on that save. (Only
what the build itself refuses stops it, as before: a settings file that cannot be read at all, or a mistake in one
of the files it checks — a presentation deck, `config/orientation.yml`, `carry.yml`, `history.yml`, `expenses.yml`.) When the change is to a source only the full update reads (an Instagram post listed by hand, a
YouTube channel, La Viña's weekly open meeting, the meeting lists …), that save's run reads that source too.
In the **Actions** tab each run's title says what it is: "Nightly full update (GitHub schedule)", "Midday
refresh (GitHub schedule)", "Evening refresh (GitHub schedule)", "Morning refresh: new day and daily quote",
"Full update (started by hand)" … (a run started by a saved change carries the change's message).

| Source | What the site gets | Where it shows |
|---|---|---|
| **AA Grapevine** magazine (aagrapevine.org) | Each new issue's stories: title, author's first name + initial, the publisher's public teaser, link to read it | **Read** |
| **La Viña** magazine (aalavina.org) | Same, for each bimonthly issue | **Read** |
| **The magazines' online archives** (two CSV exports the owner keeps in `content/archive/`, plus every story the site has captured) | Every story by a writer from Texas since 1944 (Grapevine) and 1996 (La Viña): title, the publisher's subtitle, theme, byline as printed, link — Area 65 first (the counties in `spotlight.neta65_counties`). Read again by every run; a new export shows a few minutes after it is pushed ([how-to/writers-archive.md](how-to/writers-archive.md)) | **Published writers** (`/published/#archive`, a line on Home) |
| **Both websites, searched page by page** | Every **official** PDF — only files on aagrapevine.org, aalavina.org, aa.org or aaws.widen.net (`library.official_hosts`) — flyers, catalogs, GVR / RLV kits, order forms, newsletters…, **each once** (`scripts/sync/pdf_curate.py`: copies of one file merged, older versions of one document dropped, English / Spanish / French editions on one card with language links), with page count and a preview picture | **Library** (catalogs and order forms also on **Shop**) |
| **AA Grapevine's Podcast** | Every episode, playable on the site | **Listen** |
| **Grapevine Weekly Open AA Meeting** (podcast) | Every recorded meeting, playable on the site | **Listen** |
| **YouTube** (@AAGrapevine — Grapevine *and* La Viña videos) | Every video, playable on the site | **Watch** |
| **Instagram** (@alcoholicsanonymous_gv, @alcoholicosanonimos_lv) | Newest posts — see [section 9](#9-instagram-how-the-site-reads-it-please-read) | **Instagram** |
| **Committee Google Drive** | Reports, notes, slides, workshops, forms, photo albums; dated flyers → events; docs in *bulletin* → bulletin posts | **Portfolio · Photos · Events · Bulletin** |
| **Editorial calendar** (Grapevine), **yearly themes** (La Viña: the "Temas de LV" document on aalavina.org/recursos) and suggested topics (La Viña) | Upcoming themes and story deadlines of both magazines | **Contribute** (also the monthly toolkit, the district report, Home and the workshop presentations) |
| **Grapevine Weekly Open meeting** (web page) | Current day, time and Zoom details | **Meetings** |
| **La Viña's weekly open meeting** (from the settings, `lavina_weekly_open:` — an official La Viña flyer) | Thursdays in Spanish, first date, Zoom details | **Meetings** (one line on Home · Listen · Watch · monthly posters) |
| **Official stores** (aagrapevine.org / aalavina.org store pages) | **Book of the Month** (title, cover, percent, sale price, dates) and **subscription prices** per region (U.S. · Canada · International; print / digital / complete); once a week the **specialty items** — greeting cards, pocket planner, wall calendar and, in season, the holiday cards (picture, price, pack size, volume price, a short description) | **Shop** (a short teaser on Home, the monthly posters and the monthly toolkit) |
| **Daily quote** (the home pages of aagrapevine.org and aalavina.org) | Grapevine's *Daily Quote* and La Viña's *Cita Diaria*: the quote as published (never translated), who said it, the book it comes from, the official e-mail sign-up | **Home** |
| **Record your story by phone** (aagrapevine.org/audio-portal, aalavina.org/graba-tu-historia) | Grapevine's *Audio Project* and La Viña's *Graba tu historia*: the phone number, the keys to press, the length, the e-mail address for recordings, Grapevine's story playlists | **Share your story** (`/contribute/#record`; one link on Listen · Watch) |
| **Committee meeting** (from the settings) | Next dates, countdown, "add to calendar" | **Meetings · Events** |
| **Local meeting lists** (the 8 intergroup / central office lists the Rowlett Group's meeting page uses — in or at our Area: Dallas Intergroup, Fort Worth Central Office, Tyler Central Service Office, the Spanish-speaking Dallas office, District 71 Abilene; nearby: Arkansas Central Office, OKC Intergroup, Northwest Texas Area 66) | Every meeting with the Grapevine ("GR") type: day, time, place, directions, link to the office's page. A meeting in two lists is shown once; our Area first (by county), nearby areas after | **Meetings** (one line on Home; each meeting is in the site search) |
| **Monthly events** (from the settings: our booth at CityWide Dallas, La Viña's monthly workshop on Zoom) | The next dates, "add to calendar", the flyer from our Drive; a date La Viña's own calendar lists too is shown once | **Events · Home · calendar feed · monthly toolkit** (and, once it has taken place, the monthly digest) |
| **Other calendars** (optional, e.g. the NETA 65 workshop calendar on neta65.org) | Their events, each shown **once** even when it is also in `content/events` (yours wins). *neta65.org currently blocks robots — see [the NETA 65 workshop calendar](#the-neta-65-workshop-calendar)* | **Events** |
| **Translation** | Every title, teaser and bulletin post in both languages | Everywhere |

The site also offers, automatically: a **What's New** page (the newest items from every source),
an **RSS feed**, a **calendar file** your phone can subscribe to, **QR posters** for districts (with the committee meeting on them),
a **search** page, and a **status** page that shows the health of every source (and when each morning's
daily quotes came in). **Shop** is the one
page for subscribing and buying (every purchase links to the official Grapevine / La Viña stores;
the old `/subscribe/` address redirects there, #anchors included).

What the newer pages do:

- **Book of the Month** (`/shop/#botm`): both magazines' books of the month with cover, percent off, sale and
  regular price, the offer's dates and a live "N days left" count; the heading and buttons switch to
  "Offer ended" by themselves on the last day, even before the next update. The home page shows a small teaser.
- **Subscriptions & prices** (`/shop/#subscriptions`): a switch for magazine × region (U.S., Canada,
  International) with every term's price as the stores list it, volume prices, gift subscriptions (Carry the
  Message), home-group order forms and catalogs. Links like `/shop/?pub=lv#subscriptions` open La Viña's prices.
  When AA Grapevine announces new prices, a calm notice above the prices (`#price-changes`) says what changes
  and when, and from that day the new 1-year prices show by themselves — see
  [When Grapevine announces new prices](#when-grapevine-announces-new-prices).
- **Calendars, planners & cards** (`/shop/#specialty`): one card per item — greeting cards, the pocket
  planner, the wall calendar and, while the stores sell them (from about September), the **holiday cards**
  (a pack of 12) — from the page language's store, with the other store's edition linked under it; the
  hero's right-hand card lists them too. Four cards sit in one row on a computer screen (two rows of two
  below about 1250px — 1440px with relaxed spacing, larger with larger text — and on tablets, one column on
  phones). The holiday cards are seasonal (a "Seasonal" mark on their picture): when the stores
  take them down after the holidays, the card stays about two more weeks and then leaves by itself (the other
  three take the row); it comes back with the next season, with no change to make. The addresses read are in
  `config/site.yml` → `sources.grapevine.specialty` / `sources.lavina.specialty`; to stop showing one store's
  item, name its kind in `specialty_skip` next to them (for example `specialty_skip: [holiday]`).
- **Monthly toolkit** (`/monthly/`) — everything current for this month: the "10 ways to put an issue to
  work" guide (`config/carry.yml`), and a page for this month and each of the next 12 — the issue themes, tips,
  story deadlines, dates (committee meeting, the CityWide booth, workshops), the Book of the Month and a
  **poster** in its own seasonal design to download as a PNG for WhatsApp / Instagram (1080 × 1350), share, or
  print on one letter page. Each month's page also has the month **as a message** — the same toolkit as text
  with its links, in one language or both, with *Copy for WhatsApp* / *Copy for e-mail* — and how many
  stories each magazine issue has on the site, with a link to them. **This month's** page also shows what is
  live now: a date is marked "Over" as soon as it ends, even between updates, and the next update moves it
  under "Earlier in …"; once the month's committee meeting is over, the next one; a newer issue that is
  already out; and "Keep up all month" (the daily quote, What's New, the bulletin, Instagram, subscriptions).
  Each month's Dates card also offers **"Add <Month>'s dates to my calendar"**: one calendar file
  (`/monthly/2026-10/neta65-grapevine-2026-10-en.ics`, Spanish `…/es/monthly/2026-10/…-es.ics`) with the month's
  committee meeting, events and story deadlines. `/monthly/` shows each month as a small poster (the full poster,
  with dates and QR code, is on the month's own page); its "This month" card drops a date once it is over and
  shows the next committee meeting. A page left open after the month ends says so and links the new month. Its QR
  code opens that month's page; the **12 previous months'** addresses forward to `/monthly/` (since October 2026,
  so a poster on a corkboard keeps working for a year). Shared on WhatsApp, Facebook or in a text message, a
  month's page shows the top of its poster as the link's picture (since October 2026; made by every update — the
  committee's card on a day it could not be made). Facebook also keeps a page's preview for a few days: to refresh a
  month already shared, paste its address into Facebook's **Sharing Debugger** and press **Scrape Again**. On the
  Spanish poster the note "Títulos traducidos automáticamente del inglés — originales en cursiva" sits beside the
  italic originals it explains, once. The same page holds the **GV/LV report** for district
  meetings (`/monthly/#report`, see section 4); the old `/districts/` address forwards there.
- **Monthly digest** (`/digest/`) — everything from last month on one page (the *September 2026 digest* all
  through October): bulletin posts, the events that took place, the committee's files and photo albums added
  that month, the magazines' new stories, writers from Area 65 & Texas, podcasts, videos, the magazines'
  Instagram posts (how many each account shared, the newest ones and a link to the site's Instagram page) and
  documents — with one link to this month's toolkit, and *Copy for WhatsApp* / *Copy for e-mail* in one
  language or both. The monthly e-mail ([section 10 c](#c-monthly-e-mail-digest-keep-every-district-informed))
  is the same edition.
- **GVR / RLV 101** (`/orientation/`): the orientation for new GVRs and RLVs — six short lessons (5–8 minutes
  each: goal, key points, "try this at your group", a live example from the site's own data, official links and
  a 3-question self-check with instant feedback; "lessons done on this device" is kept in the browser only),
  one page per lesson (`/orientation/<id>/`). The hub has **Present as slides** (a full-screen 16:9 slide show
  for a projector: arrow keys / Space / Home / End, F for full screen, Esc to exit, swipe on touch;
  `/orientation/?slides#slide-12` resumes, `#lesson-role` starts a lesson), a **printable handout** (printing
  the hub gives one Letter sheet per lesson) and a 45-minute plan for district trainers. The lessons live in
  `config/orientation.yml` (both languages, checked by the build and by `tests/test_orientation.py`); the GVR
  corner and the Monthly toolkit link to it.
- **Meetings** (`/meetings/`, renamed from *Committee meeting*; the old `/meeting/` address forwards there,
  `#weekly-open` included): the committee meeting (`#committee-meeting`), the **Grapevine meetings** of local
  groups (`#grapevine-meetings`: our Area first, then each nearby area — filters for place, day, in person /
  online and "include nearby areas"; each card links to the meeting's page on the office's site, which has the
  joining details and any changes), and the weekly open meetings (`#weekly-open`: each has **Add to calendar**, a
  weekly repeating entry for Google Calendar or as a calendar file for Apple and Outlook).
- **Districts** page: removed. Its one piece of its own, the GV/LV report, lives at `/monthly/#report`
  (found in the site search by "district" / "report", "distrito" / "informe"); `/districts/` forwards there.
- **La Viña's weekly open meeting**: `/meetings/#weekly-open` shows both public weekly meetings (Grapevine on
  Wednesdays in English, La Viña on Thursdays in Spanish) with day, time and Zoom details — the one place
  with those details; other pages link there.
- **Published writers** (`/published/`): the stories of the last 60 or 90 days by writers from Area 65, the rest of
  Texas or anywhere, and below them **"Texas writers through the years"** (`#archive`): every story by a Texas
  writer in the magazines' online archives, grouped by decade, Area 65 first (the rest of Texas loads when a visitor
  chooses *All of Texas*), with the page's one search box and filters, decade chips, the Area 65 hometowns with the
  most stories, and shareable addresses such as `/published/?scope=texas&dec=1990s#archive`. Its Area 65 stories
  show without JavaScript and offline. The data: the two archive exports in `content/archive/` and every Texas
  story the site captures — guide: [how-to/writers-archive.md](how-to/writers-archive.md).
- **Booth display** (`/about/#booth`): a show for the committee's table at assemblies and events. **Start the
  booth** on a TV, laptop or tablet and it plays by itself — quizzes, facts, polls, official videos, the
  committee's photos and the site's news of the day — in English, Spanish or both, and keeps playing offline once
  opened with internet. Its rows are `content/booth/booth.csv`; its photos and videos go in the Drive panel folder's
  `booth` folder. Full guide: [how-to/booth.md](how-to/booth.md).

**Menus** (`src/_data/nav.js`): What's New · Read · Listen · Watch · Library · Shop ·
**Get Involved** (monthly toolkit & GV/LV report, GVR / RLV 101, share your story, published writers, GVR / RLV
corner) · **Committee** (Meetings — committee meeting, Grapevine meetings & weekly open meetings —, events,
Portfolio — the committee's reports, notes, slides and workshop files, `/portfolio/` —, photos, bulletin).
The Portfolio was called *Committee documents* (`/documents/`); that address forwards to `/portfolio/`, `#anchors` included.
The Bulletin was called *Announcements* (`/announcements/`); that address forwards to `/bulletin/` the same way.
Instagram and QR Post (`/share/`) are in the footer's *Stay updated* column, after the two magazine sites;
accessibility, Saved pages & app (`/offline/`: the pages saved on the device and the steps to install the
site), search and status in its bottom bar; the phone menu lists them all under *More*. The install steps
used to be a page of their own; old links to it forward to `/offline/#steps` (a guide's own `#anchor`,
like `#android`, is kept).
Each piece of information has one home page; other pages only link to it.

**Wording on the site** (both languages): visitors read "document(s)" / "documento(s)", never "PDF", and
"we keep it updated regularly" / "lo mantenemos actualizado con regularidad" — the pages do not describe how
the sites are searched (no "crawl", "checked every day on …"). Code, file names, data keys and these docs keep
the technical words.

**Respecting AA Grapevine, Inc.:** the site shows titles and the publishers' own public teasers and
links back to the official pages. It never copies magazine articles. **Respecting anonymity:** it
only shows what the official sources publish (first names and last initials).

---

## 2. Your part: uploading to Google Drive

The committee's shared folder is **A65_GV** (the one in `config/site.yml` → `drive.root_folder_id`).
It must be shared as **"Anyone with the link — Viewer"**. Inside it, each panel has its own folder:

```
A65_GV/
└── 2027-2028_Panel77_GVLV/          ← a panel folder (any name containing "Panel 77")
    ├── reports/        (or informes)
    ├── notes/          (or notas, minutes, actas)
    ├── slides/         (or presentaciones)
    ├── flyers/         (or volantes)         → dated flyers become EVENTS
    ├── workshops/      (or talleres)
    ├── forms/          (or formularios)
    ├── bulletin/       (or boletín; announcements, anuncios) → Google Docs become BULLETIN posts
    └── photos/         (or fotos)
        ├── Spring Assembly 2027/             → each sub-folder is an ALBUM
        └── Writing Workshop/
```

Upload files into the right folder (reports, notes, slides, workshops and forms show on the **Portfolio**
page, `/portfolio/`). **They appear on the site the next morning**
(or a few minutes after you [run the update](#7-running-the-update-right-now)).
Folder names can be English or Spanish, any capitalization. Any other folder name also works —
it shows on the Portfolio page (`/portfolio/`) under its own name. Folders *outside* a Panel folder are ignored.

### Naming files (optional, but it makes the site smarter)

**Flyers → events.** Put the flyer in *flyers* and start its name with the date. Add a time and a
place if you like — the place goes after an `@`:

| File name | Result |
|---|---|
| `2027-03-14 Spring Assembly GV booth.pdf` | Event on Mar 14, 2027 (all day), flyer attached |
| `2027-03-14 Spring Assembly booth 9am @ Tyler Civic Center.pdf` | Mar 14, 2027 at 9:00 AM, at "Tyler Civic Center" |
| `2027-05-02 Writing workshop 10-12pm @ Ross Ave Group.pdf` | 10:00 AM – 12:00 PM |
| `2027-12-31 New Year's Eve Dance 8pm-1am @ Rowlett Alano Club.pdf` | Dec 31, 8:00 PM – 1:00 AM (an end after midnight is the next morning) |
| `2027-05-02 Workshop noon-2pm.pdf` | 12:00 – 2:00 PM ("noon", "mediodía" and "midnight" work where they are a time: "12 noon", "noon-2pm", "11am-noon") |
| `2026-11-05 Reunión abierta 12 p. m. (hora del Este) por Zoom.png` | 12:00 PM Eastern = 11:00 AM Central (a time zone right after the time — ET, EST, Eastern Time, (Eastern), (hora del Este) — is used; without one the time is Central) |

A picture saved under the phone's own name (`IMG_20261017_183316.jpg`, `WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg`,
a screenshot) is not an event: that date is when the picture was taken. Rename it to start with the event's
date. The same flyer uploaded twice (a PDF and a picture of it) shows once, as the PDF.

**The Bulletin.** Put a Google Doc (or a .txt / .docx file) in *bulletin*. It becomes a post on the
Bulletin page (`/bulletin/`, under *Committee*); the file name is the headline and the document's text is the body:

| File name | Result |
|---|---|
| `2027-01-10 Welcome new GVRs` | Headline "Welcome new GVRs", dated Jan 10, 2027 |
| `2027-01-10 Welcome new GVRs (pinned)` — or `(fijado)` | Stays at the top |
| `Spring Assembly sign-ups (from 2027-02-01)` — or `(desde 2027-02-01)` | Stays off the site until Feb 1, 2027, and appears with that morning's update (by 5:30 AM with the morning alarm) |
| `Summer schedule (until 2027-08-31)` — or `(hasta 2027-08-31)` | Disappears by itself after Aug 31 |

The dates need their year: `(until Feb 1)` / `(hasta el 1 de febrero)` is not understood, stays in the headline
and the post does not come down by itself. Words that are not a date, such as `(until further notice)` or
`(hasta 20 personas)`, stay in the headline as written.

A scheduled post is kept off the site, not hidden: the Drive folder is shared with anyone who has its link,
so the document can be opened there before its day.

**Headings help a long post.** Each post has the page's width to itself, one under the other. On a computer
screen a post shows its text beside a small panel with its *Copy link* and *Share* buttons (and *Open the
document* when there is one). When the text has two or more headings — lines that start with `# ` (or `## `)
in a .md or .txt file, or typed that way in the Google Doc — the panel also lists them as **In this post**
and marks the one being read; each heading has a link of its own (`/bulletin/#<post>--<heading>`) that can be
shared. On a phone the post reads as before, with the buttons under it.

**Documents.** A date at the start of any file name sets its date: `2027-03-14 Area report.pdf`.
Dates can also be written `03-14-2027`, `March 14, 2027` or `14 de marzo de 2027`.

**Photos.** Create a sub-folder inside *photos* for each album (e.g. `Fall Assembly 2027`).
**Please protect anonymity:** only upload pictures where **no AA member's face can be recognized**
(booths, literature tables, venues, banners) — or where everyone pictured agreed to share.

### Good to know

- **A new panel** (e.g. Panel 79): create `2029-2030_Panel79_GVLV` with the same sub-folders. The site picks it up
  automatically. Panels older than `drive.min_panel` in the settings are ignored.
- **Never published on the site:** spreadsheets (form responses can contain personal information) and anything
  whose name contains `PRIVATE`, `PRIVADO`, `(Responses)` or `(Respuestas)`. **But the Drive folders are shared
  "Anyone with the link"** (the Portfolio page links to them): a file inside them can still be opened there.
  Keep private drafts and personal information out of the A65_GV folders altogether.
- **Deleting or moving** a file in Drive removes it from the site on the next update.
- Empty folders are fine — the site shows a friendly "nothing here yet" message.

---

## 3. Changing settings (`config/site.yml`)

All settings live in **one file**: [`config/site.yml`](config/site.yml). To edit it:

1. Open the file on GitHub and click the **pencil icon** (✎ "Edit this file").
2. Change the value after the colon. **Keep the spaces at the start of each line exactly as they are**
   (YAML uses indentation), and keep quotes around text that has them.
3. Click **Commit changes…** → **Commit changes**.
4. The site rebuilds automatically in **about 3 minutes** (watch it in the **Actions** tab; a page may take up
   to about 10 more minutes to show the change everywhere). The *Code check* tests your change meanwhile, in about
   10 minutes: a red ✗ there means a slip to fix (the site was published without the part it could not use).

Common changes:

| To change… | Edit… |
|---|---|
| Committee meeting day/time | `meeting:` → `week_of_month`, `weekday`, `start`, `end` (24-hour, Central time; "7:00 PM", "7pm" or 19 are read the same way) |
| Skip a meeting (holiday) | `meeting:` → `skip_dates: ["2027-12-15"]` (must be a meeting day — that month's 3rd Wednesday; any other date is ignored and the run summary says which date to use) |
| Something we do every month (a booth, a workshop) | `recurring_events:` — see [below](#add-a-recurring-event) |
| Something La Viña or Grapevine holds every month (La Viña's workshop on Zoom) | `recurring_events:` with `host: "lv"`, `online_url`, `meeting_id`, `flyer_match` — see [below](#something-la-viña-or-grapevine-holds-every-month-host-online-only-its-flyer) |
| Skip one month of it | `recurring_events:` → that event's `skip_dates: ["2026-12-12"]` |
| Zoom link, meeting ID, passcode | `meeting:` → `zoom_url`, `meeting_id`, `passcode` |
| Who may come (the first line of *Who can come* on Meetings, and the end of the calendar text); where it is held | `meeting:` → `note` and `note_es` (write both); `platform` (the pages say "Join on Zoom": left out, Zoom) |
| Joining our Zoom meetings by phone (dial-in numbers, the committee's phone passcode) | `phone_access:` — see [below](#joining-our-meetings-by-phone) |
| Contact e-mail | `site:` → `contact_email` and `meeting:` → `chair_email` |
| Which Drive panels are shown | `drive:` → `min_panel` |
| The offices whose Grapevine meetings are listed (our Area and nearby) | `meetings:` → `feeds` (each with `region_label`; `enabled: false` hides the list) |
| How long the daily PDF search runs | `sources:` → `crawler:` → `minutes_per_run` (default 40; **`0` pauses the PDF search** — everything else keeps updating) |
| Instagram: official method only | `sources:` → `instagram:` → `anonymous: false` (see [section 9](#9-instagram-how-the-site-reads-it-please-read)) |
| Another website's calendar on the Events page | `sources:` → `ics_feeds:` (instructions in the comments there) |
| Monthly digest: stories per magazine issue / items per section | `digest:` → `highlights`, `per_section` |
| New prices AA Grapevine announced (subscriptions, books) | `price_changes:` — see [below](#when-grapevine-announces-new-prices) |
| The site's public address | `site:` → `url` (see [custom domain](#12-using-your-own-address-custom-domain)) |

If a change breaks the file (for example a missing space), the update shows a **red ✗** in the
Actions tab and **the website stays as it was**. Open the file's **History**, compare with the
previous version, and fix or undo the change.

### Add a recurring event

For something the committee does **every month** — like our Grapevine / La Viña booth at
**CityWide Dallas** (2nd Saturday, 5–8 PM) — add a block under `recurring_events:` in
`config/site.yml`. This is the one already there:

```yaml
recurring_events:
  - key: "citywide-dallas"          # short name: letters, numbers, dashes. Don't change it later.
    title: "GV/LV booth at CityWide Dallas"
    title_es: "Mesa de GV/LV en CityWide Dallas"
    summary: "Stop by our Grapevine and La Viña literature table at CityWide Dallas, …"
    summary_es: "Visita nuestra mesa de literatura de Grapevine y La Viña en CityWide Dallas, …"
    week_of_month: 2                # 1–5, or -1 for "the last one"
    weekday: "saturday"             # English or Spanish ("sábado")
    start: "17:00"                  # 24-hour clock, Central time
    end: "20:00"
    location: "Lover's Lane United Methodist Church, 9200 Inwood Road, Dallas, TX 75220"
    url: "https://citywidedallasaa.org"   # the "Event details" link (optional)
    months_ahead: 6                 # how many upcoming dates to list (Events page, calendar feed)
    skip_dates: []                  # a month without it: ["2026-12-12"] (must be that month's 2nd Saturday)
```

`months_ahead` only sets how many dates the **Events** page and the calendar feed list; the monthly posters
(`/monthly/`, 13 months) work out the later dates from the same rule, so there is no need to raise it.

To add another one, copy the whole block (from `- key:` down), paste it under the last one and
change the values. Every date then shows on the **Events** page (with an "Every month" badge) and in the
**monthly toolkit** (the month's page, poster and message); the next date of each series of ours always
keeps a place in the home page's **Upcoming events** row (the other places go to the soonest workshops and
other events, so a busy month never pushes the booth off the home page; a series La Viña or Grapevine
holds takes its turn instead — see `host` below); once a date
has taken place it is in that month's **monthly digest**; all of them are in the **calendar feed** — in
both languages, with daylight-saving time handled. Write the Spanish
yourself (`title_es`, `summary_es`); if you leave it out, the site translates the English
automatically and marks it "auto-translated". A monthly event never shows as "New" and does not,
on its own, make the monthly e-mail go out. If a block has a mistake (for example
`weekday: "funday"`), only that event is left out: the site still updates, and the run summary in
the **Actions** tab shows a yellow **Settings problem** saying what to fix. The same happens for a
`skip_dates` date that is not one of the event's days (for example the Sunday, or the 1st Saturday):
that month still shows, and the note gives the date to use instead.

#### Something La Viña or Grapevine holds every month (`host:`, online only, its flyer)

The second block under `recurring_events:` is **La Viña's monthly workshop on Zoom** (in Spanish, open to
everyone). It is La Viña's event, not ours, so it says so — and, being online only, it has a Zoom link
instead of a place:

```yaml
  - key: "lv-monthly-workshop"
    title: "La Viña Monthly Virtual Workshop (in Spanish)"
    title_es: "Taller Mensual y Virtual de La Viña"
    summary: "In Spanish, open to all: …"      # short (about 100 characters): the card shows 3 lines
    summary_es: "En español y abierto a todos: …"
    host: "lv"                      # who holds it: "neta" (us — the default), "lv" (La Viña) or "gv" (Grapevine)
    week_of_month: 4                # La Viña's calendar lists it on the 4th Thursday (-1: the last one)
    weekday: "thursday"
    start: "14:00"                  # 3 PM Eastern = 2 PM Central
    end: "15:00"                    # no end time is published: one hour
    online_url: "https://us06web.zoom.us/j/81595931777"   # no location: online only
    meeting_id: "815 9593 1777"     # shown on the card and in the calendars (optional)
    contact: "lveditorial@aagrapevine.org"   # who to write to: a line on the card and in the calendars (optional)
    flyer_match: "taller (informativo )?mensual( y virtual)? de la vi[nñ]a"   # its flyer on our Drive (optional)
    months_ahead: 6
    skip_dates: ["2026-11-26", "2026-12-24", "2027-11-25", "2027-12-23"]   # Thanksgiving, Christmas week
```

- **`host`** — `"lv"` or `"gv"` puts the event with the **Grapevine / La Viña calendars** on the Events page
  (the *GV & LV calendars* filter) and gives it that magazine's colour everywhere — the Events page, the home
  page, the monthly toolkit and its posters, the search; search engines see La Viña (or Grapevine) as the
  organizer. Such a series keeps no reserved place in the home page's **Upcoming events** row: its next date
  takes its turn by date with the one-off events, so it never pushes off one of our workshops that comes
  sooner. Leave it out for our own events, like the CityWide booth.
- **`online_url` without `location`** — an online-only event: the card says *Online on Zoom* with a
  **Join online** button and no map; the calendar files get the Zoom link as the place; the home page,
  the monthly toolkit, the digest and the district report say *Online* / *En línea*.
- **`meeting_id`** — for people who type the meeting ID into the Zoom app: a line on the card and in the
  calendar entry. If it is not the meeting the `online_url` opens, the run summary says so.
- **`flyer_match`** — finds the flyer on the committee's Drive by a pattern (a *regular expression*,
  capitals ignored, with or without accents), not by its exact name, so **renaming the file does not
  lose it**: the newest file whose name matches is shown on every date ("View flyer", its picture on the
  card, attached in the calendar files). A flyer whose name starts with a date (`2027-01-28 Taller
  Mensual y Virtual de La Viña.png`) is that date's own; one with just a month (`Enero 2027 …`) is that
  month's. Nothing matches: no flyer, and nothing to fix. A pattern the site cannot read is listed in the
  run summary (the event still shows).
- **`contact`** — the e-mail address to write to about it: a line of its own on the card (a link that opens
  the visitor's e-mail program) and in the calendar entry. Put it here, not in the summary — the card shows
  only three lines of the summary, so an address at its end can be cut off on a phone or with larger text.
  Something that is not an e-mail address is left out, and the run summary says so.
- **`summary`** — keep it short (about 100 characters): the card shows three lines of it.

**La Viña lists the same dates on its own calendar** (aalavina.org, which the site also reads): a date
listed there **and** here shows **once** — ours, with its time, Zoom ID and flyer (they are recognized by
the Zoom meeting, so the titles do not have to match). If La Viña's calendar lists the workshop on
**another day** of a month, both stay on the Events page and the run summary on the **Actions** tab shows
a **Settings problem** naming the date to add to `skip_dates` — add it and the rule's date goes away; La
Viña's own listing of the new day stays. (A month whose own date La Viña lists too is not moved: another
session in the same room that month is simply shown, with no Settings problem.) That is why November and
December are skipped above: La Viña has held it on the Thursday before Thanksgiving and before Christmas,
and its calendar lists those dates itself (about three weeks ahead). **Thanksgiving is always the 4th
Thursday of November**, so add each year's date to `skip_dates` ahead of time (and December's, if La Viña
moves it again): the run summary only warns once La Viña's calendar lists the moved date, and the
`/monthly/` posters work out the months a year ahead from the rule. In a skipped month, La Viña's own
listing **is** that month's date: the Events page shows it with the workshop's title, Zoom ID and flyer
(and "Time not listed", as La Viña gives none), and the workshop's card names it in its "Then …" dates.
To show such a date with its time, add a
[`content/events`](content/events/README.md#an-event-la-viña-or-grapevine-holds-host) file with
`host: lv` and the same `online_url` — or upload its flyer with the date at the start of its name.

**4th or last Thursday?** The flyer says "el último jueves de cada mes", but in the months with five
Thursdays La Viña's own calendar has listed the 4th (five times out of six since 2024), so the site
follows its calendar: `week_of_month: 4`. Should La Viña really hold it on the last Thursday, change it
to `-1` — and change the December `skip_dates` too (the last Thursday of December 2026 is New Year's Eve,
Dec 31).

### La Viña's weekly open meeting

`lavina_weekly_open:` in `config/site.yml` holds La Viña's weekly open meeting (from its official flyer —
there is no web page to read yet): Spanish and English title and summary, `day`, `time` + `timezone` (the
meeting's own time zone; the site also shows Central time), `starts` (the first meeting, which must be on
that `day`), `zoom_id` and `passcode`. When La Viña publishes a page for it, put the address in `url`.
Set `enabled: false` (or delete the block) to take it off the site.

### Joining our meetings by phone

The Accessibility page (`/accessibility/#phone`) tells people how to join the committee meeting and the
weekly open meetings **by phone** — no internet or app needed — with tap-to-call buttons. The meeting IDs
come from `meeting:` and the weekly open meetings; `phone_access:` in `config/site.yml` holds the rest:

- `numbers`: Zoom's U.S. dial-in numbers (the ones printed in every Zoom invitation under "Dial by your
  location"). The first one is used for the tap-to-call buttons.
- `committee:` → `phone_passcode`: **fill this in.** Our Zoom passcode (`neta65`) has letters, so Zoom
  gives phone callers a different passcode made of numbers only. Find it in the host's Zoom invitation
  (the digits after `*` in the "One tap mobile" line, or "Passcode:" under "Dial by your location") and
  paste it between the quotes. Until then the page says "Ask the chair for the phone passcode".
- `weekly_open:` → `phone_passcode`: leave it empty — that passcode (`238047`) is numbers only, and callers
  type the same one.

Joining by phone only works while the host's Zoom settings allow it (Zoom: "Allow participants to join
by telephone").

**The passcodes are public, on purpose.** The committee meeting's and the weekly open meetings' meeting IDs and
passcodes are printed on `/meetings/`, in the calendar files, on the QR poster and in the presentations, for
anyone to read. That is normal for open AA meetings, which anyone may attend. It means each meeting's host should
keep Zoom's own protection on: the **waiting room**, or the host controls (admit people, remove a participant,
lock the meeting once it has started). Changing the passcode protects nothing: the site shows the new one at its
next update.

### When Grapevine announces new prices

Every price on the site is read from the official stores, so the site follows a price change by itself once
the stores show it. What a block under `price_changes:` in `config/site.yml` adds is everything before that:

- **From the day AA Grapevine announced it** (`announced`): a calm notice right above the subscription prices
  on `/shop/` — "Prices change on January 1, 2027", each 1-year subscription with today's price and the new
  one, the books ("$2.00 more each"), AA Grapevine's reason in one sentence and a link to its notice (the
  letter on our Drive, found by `doc_match`). Each of those plans also says "From Jan 1, 2027: $39.00", and
  each Book of the Month card has a line about the books. The monthly toolkit (its message and "Keep up all
  month"), the GV/LV report for the district meeting and the monthly e-mail pass it on.
- **From the day it takes effect** (`effective`): the new 1-year prices show **by themselves** — even while a
  store's own page still shows the old price, and even in a page built (or saved on a phone) the day before:
  it switches at midnight Central. As soon as a store shows anything else after that day, the store's price
  wins. "New prices since …" shows until `notice_until`. A Book of the Month price read before the day — or
  read after it while the store still shows the book's old price — is not shown (no "you save" on an old
  price); the store's own prices show again once it shows the new price, or a new book starts on the 15th.

Only what the announcement names changes: the 2- and 3-year, monthly and Complete plans keep the stores'
prices. The block for January 1, 2027 (AA Grapevine's letter of October 1, 2026) is the one to copy:

```yaml
price_changes:
  - key: "2027-01"                 # short name: letters, numbers and dashes
    effective: "2027-01-01"        # the day the new prices start (Central time)
    announced: "2026-10-01"        # the notice shows from this day
    notice_until: "2027-01-31"     # the last day of the "New prices since …" notice
    source: "AA Grapevine's letter to Intergroups and Central Offices, October 1, 2026"
    source_es: "Carta de AA Grapevine a las oficinas intergrupales y centrales, 1 de octubre de 2026"
    doc_match: "pricing update.*2027|actualizaci[oó]n de precios.*2027"   # finds the letter on Drive
    yearly:                        # the new 1-YEAR prices, U.S. dollars (gv = Grapevine, lv = La Viña)
      gv: { print: 39.00, digital: 34.00 }
      lv: { print: 19.50, digital: 17.00 }
    books_more: 2.00               # every Grapevine and La Viña book costs this much more
```

Also: put the letter in the Panel's Drive `notes` folder with **the letter's date first** in its name
(`2026-10-01 Grapevine & La Viña Pricing Update - Effective January 1, 2027.pdf` — otherwise the Portfolio
dates it by the date in its title), and, if you like, write a bulletin post for the day it was announced and
one for the day it takes effect (`content/bulletin/2026-10-01-prices-change-january-1-2027.md` and
`2027-01-01-new-prices-in-effect.md` are examples: one opening sentence with every new price — the home page
shows the first lines —, AA Grapevine's reason, what it means for the groups — never "buy now before prices go
up"). A mistake in the block shows as a **Settings problem** in the
Actions run summary; the rest of the site still updates. Once the stores show the new prices the block may be
deleted. Details: [docs/OPERATIONS.md](docs/OPERATIONS.md#when-grapevine-announces-new-prices).

---

## 4. The monthly GV/LV report

Nothing to edit: **Monthly toolkit → Your GV/LV report** (`/monthly/#report`) is the report a GVR / RLV
gives at the district meeting, in English or Spanish, filled in with the current month's data on every update
(`eleventy/filters/report.js`): the header with blanks for the district and name, the committee meeting, this
month's issues and "put it to work" tips, story deadlines (and the record-by-phone lines), Book of the Month
and subscriptions, events of the next 45 days, published writers from our Area, Grapevine meetings (with a
county picker), the weekly open meetings, new service documents and sign-up links, the Area's asks and the
member's own notes. Each GVR / RLV can switch sections on and off, reorder and edit them, add their own, and
copy the result (plain text for WhatsApp, or formatted for e-mail / Word), send it by WhatsApp or e-mail,
download it (Word .docx or .txt) or print it (`src/assets/js/report.js`). When a new month starts, the editor
offers **"Start from last month's draft?"** (for an older draft it names the month: "Start from your August 2026
draft?"): it brings back the GVR's own sections, their order, the sections left
out, changed titles, the counties picked and the *Action items* and *My notes* texts (the sections built from the
site's data start fresh). The Book of the Month offer shows only while it runs, and the shop section's text changes
by itself at midnight Central when an offer starts or ends or a price change is announced, takes effect or ends. WhatsApp is one tap at any
length: a short report opens in WhatsApp already written; a full one goes through the phone's share sheet,
or (on a computer) is copied while WhatsApp opens, ready to paste into a chat. Their changes stay in their own
browser only, per month and language; nothing is sent anywhere. Without JavaScript the page shows the whole
report as text. (The old *Districts* page and its
`content/districts.yml` list were retired; its news feed, calendar, digest and poster links live on
`/events/`, `/digest/`, `/share/` and in the footer.)

---

## 5. Fixing a translation

Machine translation is good but not perfect. Two ways to correct it:

**A. Fix one specific title or phrase** — [`data/translations/overrides.yml`](data/translations/overrides.yml).
Add one line per fix at the bottom of the file (no `#` in front): the exact original text, then the
translation you want:

```yaml
"Carry the Message Project": { es: "Proyecto Lleva el Mensaje" }
"Casados, sobrios y felices": { en: "Married, Sober and Happy" }
```

**B. Fix a word everywhere** — [`data/translations/glossary.yml`](data/translations/glossary.yml).
Add names that must never be translated under `keep:` (for example a group's name) and AA terms
that always need the same translation under `terms:`. Instructions are at the top of that file.

Saving either file rebuilds the site in about 3 minutes. If a file has a typo, the **Website update** run
summary lists it under *Settings problems*: the translations already made stay, and new titles wait in their
original language until the file is fixed.

---

## 6. Bulletin posts and events without Drive (optional)

Drive is the easy way. If you prefer GitHub, you can also add a small text file:

- **Bulletin post:** a Markdown file in [`content/bulletin/`](content/bulletin/README.md), e.g. `2027-01-10-welcome-gvrs.md`.
  It needs no header (the first `# heading` is the title, a date at the start of the file name is the date),
  pictures and PDFs saved next to it can be linked by name, and [`_example.md`](content/bulletin/_example.md)
  shows every option. To post it on a later day, add `publish: 2027-02-01` to the header: it stays off the
  site until that morning's update (the file itself is public in the repository as soon as it is saved).
- **Event without a flyer:** a Markdown file in [`content/events/`](content/events/README.md).

Each folder's README shows a copy-and-paste example. English or Spanish — it is translated automatically.
To write the other language yourself, add `title_es` and `summary_es` to a file written in English
(or `title_en` and `summary_en` to one written in Spanish): the other page then shows your words as
written, not an automatic translation. A bulletin post's `summary_es` is its whole Spanish text; written as
`summary_es: |` with the text indented on the lines below, it keeps its paragraphs and lists.
Committee meetings are **not** added by hand; they come from the settings — and so do events that
happen every month ([`recurring_events:`](#add-a-recurring-event)).

**Events over several days** (the Area assemblies): write only dates, `start: 2027-03-19` and
`end: 2027-03-21` (the last day). The site shows the range ("Fri, Mar 19 – Sun, Mar 21, 2027") and
keeps the event listed until its last day is over.

**Always write the whole date, with its year.** A `start:` or `end:` without a year (`January 10`), without a day
(`March 2027`, `marzo de 2027`) or a time alone (`19:00`) is not guessed any more: the event is left out (its last
good version stays) and the run summary lists it under **Event files to fix**, with a line to copy, for example
`start: 2027-01-10`. A time written with a UTC offset that is not Central time's on that day still shows, and is
listed too. The Code check tests every file in `content/events` the same way (`tests/test_content_events.py`), so
a mistake shows as a red ✗ on the Code check of your save. *Website update* still publishes the rest of the site
(it leaves the tests of the committee's own files to the Code check): fix the file soon.

**Details not final yet** (a date is set, the venue is not): add `tentative: true` (or `yes` / `sí`)
and, for the place, `location: "Venue to be announced"` with `location_es: "Lugar por anunciarse"`.
The event shows a **"Details to be confirmed"** badge everywhere and calendar apps mark it tentative.

### When an assembly's details are final

1. Open its file in [`content/events/`](content/events/) (for example
   `2027-06-25-neta65-summer-assembly.md`) and click the **pencil icon**.
2. Put the real venue and address in `location:` and **delete the `location_es:` line** (an address
   needs no translation).
3. Correct `start:` / `end:` if the dates changed, and update the description and `summary_es:`
   (the host districts, the format …). Add `url:` with the event's page on neta65.org if there is one.
4. **Delete the `tentative: true` line.**
5. **Commit changes.** A few minutes later the Events page, the home page and the monthly toolkit show it
   as confirmed, with the new place; subscribed calendars follow the next time they refresh.

(A date change only needs the file renamed if you want the name to match; the site reads the date
from `start:`.)

### The NETA 65 workshop calendar

`config/site.yml` → `sources:` → `ics_feeds:` lists the NETA 65 workshop calendar
(`https://neta65.org/events/category/workshop/list/?ical=1`). When the site can read it, its workshops
appear on the Events page by themselves, with the NETA 65 events. A workshop that is also in
`content/events` is shown **once**: your file wins (with your own Spanish) and the calendar only fills
in what the file leaves out, such as the flyer. The two are matched when they start the same day and
link the same neta65.org event page (`url:`), or have a similar title at about the same time — so a
workshop or a booth *at* an assembly stays its own event. When the calendar says something your file
does not (another date or time for the same event page, or the venue of an event your file still calls
"Venue to be announced"), the run summary on the **Actions** tab shows a **Check:** line naming the
file, so you can update it.

**Right now neta65.org blocks it.** The Area website is behind Cloudflare's "Just a moment…" bot
check, which turns away every robot, including ours (the site does not try to get around it). The
**Status** page says so under *Other calendars we read*. Until it is unblocked, a workshop or an
assembly shows on the Events page **only after someone on the committee adds it to `content/events`**
by hand — check <https://neta65.org/events/category/workshop/> now and then. The robot asks at most
once a day, and a blocked calendar never opens the *"A content source has stopped updating"* issue.

**To get it unblocked,** send this to the Area webmaster:

> Our committee website reads the public workshop calendar
> `https://neta65.org/events/category/workshop/list/?ical=1` once a day, but Cloudflare's bot check
> answers "403 Just a moment…". Could you add a Cloudflare WAF custom rule (Security → WAF →
> Custom rules) with the action **Skip** for requests whose URI query string contains `ical=1`, or
> whose User-Agent starts with `NETA65-GrapevineCommitteeBot`? ("Allow verified bots" alone is not
> enough: our small robot is not on Cloudflare's list.)

After that, nothing needs changing here: the next daily update reads it, and the Status page shows
*Working*.

---

## 7. Running the update right now

1. Open the repository on GitHub → **Actions** tab.
2. Click **Website update** in the left list.
3. Click **Run workflow** (right side) and choose:
   - **crawl_minutes** — how long to search aagrapevine.org / aalavina.org for PDFs.
     Leave it **empty** to use the daily setting (normally 40 minutes). Use up to `300` only for a
     big catch-up (see the [first-run checklist](#11-first-run-checklist)) — and start it in the morning
     or early afternoon, never in the evening: it runs up to 6 hours, and the next morning's refresh
     would have to wait behind it.
   - **skip_crawl** — tick it for a **quick refresh** (a few minutes): only **Google Drive**,
     the **bulletin**, the **podcasts**, the **daily quote** and the **writers archive files** are updated. Videos,
     magazine stories, Instagram and PDFs wait for the next nightly full update.
   - **morning** — the **morning refresh** the Morning check starts every morning: the new day's dates,
     the daily quote, Google Drive, the bulletin and the podcasts (on the 1st also the new magazine issues,
     on the 1st and the 15th the Book of the Month), published in about 3 minutes. Ticked, it wins over
     the two fields above.
4. Click the green **Run workflow** button. A full run usually takes 10 to 15 minutes (the PDF search waits 5
   seconds between pages, as the sites ask, but it has little left to do), at the very most a little over 2 hours
   when the PDF search and the translations use all their time; a quick refresh about 3 minutes; a 300-minute
   catch-up about 6 hours. When the code changed since the tests last passed, the run also tests it before it
   publishes (a few more minutes).
   You can close the page — it runs on GitHub's computers. The run's title in the list says which kind it is:
   "Full update (started by hand)", "Full update without the document search (started by hand)" (`0` minutes),
   "Quick refresh (started by hand)" or "Morning refresh: new day and daily quote".

Saving any settings or content file starts a quick update automatically — no need to do this by hand.

**Put today's quote up now:** **Actions → Morning check (new day by 5:30 AM) → Run workflow**. It only does
what is missing: when the site does not have today's update yet, it starts the morning refresh; when only a
magazine's quote is missing, it asks that magazine (from 2 AM Central, when the magazines usually publish it,
every 10 minutes until 7 AM, once after that) and brings the quote as soon as it is out; otherwise it ends
in a few seconds. When another update is already running (on the 1st, the full daily update), it waits for
that one first — it reads the quote too — and then brings only what is still missing. Tick **check_only**
to only see what is on the site and what it would do.

**Stopping a run:** open it and click **Cancel workflow**. Everything it fetched so far is still
saved (nothing has to be fetched again), but the website is only republished by the next run.

---

## 8. Is everything working?

- **The site's Status page** — <https://neta65.github.io/aagrapevine/status/> shows, for every source,
  when it last updated, how many items it has and any problem (a source **On hold** suddenly found far fewer
  items: they stay on the site until the next update confirms they are really gone; under a source, *Notes from
  the last update* holds its small hiccups, for the site maintainer), plus a small **Document library** panel
  (how many documents have a preview, last update). How far the PDF search has got (pages known ·
  crawled) is in each run's summary on the **Actions** tab (the **PDF crawl** line) and in
  `data/site/status.json` → `crawl` — the public page does not describe the crawl.
- **The Actions tab** on GitHub — each run shows a green ✓ or a red ✗. Click a run to see two summary
  tables (every step of the update, and every source). A yellow ⚠ warning means one source had a
  bad day; the site still published (with that source's previous items). Below the tables,
  **Notes** lists small hiccups of sources that still updated (only worth a look if the same note
  repeats for a week), and **New podcast feeds found** appears when the Grapevine or La Viña site
  links a podcast the website does not show yet. Nothing is added by itself: to show it, add a
  `- key:` / `name:` / `feed:` entry like the two already under `podcasts:` in `config/site.yml`
  (or send the address to whoever helps with the website).
- **The Morning check** (**Actions → Morning check (new day by 5:30 AM)**): each morning's run says when
  today's update went live — "✅ Today's update is on the site since **4:34 AM CDT** — goal 5:30 AM" (a
  check that found it already there says when the latest build is from) — with the day of each quote and
  the Website update run it started. A red ✗ means today's update did **not** reach the site (GitHub
  e-mails whoever started the check — for the alarm, the owner of its key); green with a yellow note means
  only a magazine's quote was late at the source (the note says when the magazine was last asked; the site
  shows the last quote, labelled "Yesterday", until the new one comes in). Runs that had nothing to do —
  today's update was already there, or it was too early to ask a magazine — are deleted after a day. On
  the **Status** page, the *Daily quote* row says when today's quotes came in (or which one has not yet),
  against the goal, and *Technical details* at the bottom shows the last 7 mornings.
- **In the Website update run summary** you also find **Bulletin files to fix** / **Event files to fix**
  (a file in `content/bulletin` or `content/events` that could not be read — the rest of the site still
  updated), **Scheduled bulletin posts** (posts waiting for their `publish:` / "(from …)" day), the
  **Daily quote** line (the day of each quote now on the site), the **Writers archive** lines (the archive files
  in use; "New archive file used: …" after a new export; **CSV file to fix** when one could not be used),
  **Reminders** (dated settings that run out soon: the monthly tips, a panel, next year's skip dates, the next
  assemblies, an old price-change block — each with the file to edit) and, for a source that no run has even
  tried for 3 days, **NOT CHECKED** ("not checked for N days").
- **The badge** at the top of this page is green when the last update succeeded.
- **"Code check (tests and test build)" runs:** when a settings, content or code file is saved, a
  **Code check** run also appears next to **Website update** (about 10 minutes). It builds a test copy of
  the site, opens it in a real browser and runs every automatic test; nothing is published. A red ✗ there
  means that change broke something: fix it, or undo it from the file's **History** (or send the run to whoever
  helps with the website). The live site keeps working either way. A change to the **code** that fails the tests
  is not published: **Website update** runs them before it publishes (its run is red, *"Tests failed — not
  published"*; the site keeps the version before). A slip in a settings or content file is published without the
  part that could not be read (the run summary names it), and only the Code check goes red.
- **E-mail when a run fails:** GitHub → your picture → Settings → Notifications → *Actions* →
  "Only notify for failed workflows". **Good to know:** e-mails about the *timed* runs go to the
  person who last switched each workflow on (or last changed its schedule). To make sure they come to
  **you**: **Actions** → **Website update** → **⋯** (top right) → **Disable workflow**, then **Enable
  workflow** — and the same for **Morning check (new day by 5:30 AM)** (its hourly backstop),
  **Monthly e-mail digest** (if it is used) and **Weekly link check**. Do it again whenever someone
  else changes a workflow's schedule (its `cron:` line). The runs the morning alarm starts e-mail the
  owner of its key.
- **An issue when a source stops updating:** if the same source (for example Google Drive) has not
  updated for **7 days**, the site opens one issue titled **"A content source has stopped
  updating"** in this repository's **Issues** tab, explaining what to check. GitHub e-mails it to
  everyone who *watches* the repository (**Watch** button at the top → **All Activity**, or
  **Custom → Issues**). The issue closes by itself once the source works again. The optional
  **other calendars** (`ics_feeds:`) never open this issue: the Status page explains them under
  *Other calendars we read*, and the run summary lists them as information only.
- **An issue when the update itself keeps failing:** GitHub's failure e-mail for a timed run goes only to whoever
  last switched the workflow on, and the Morning check's runs e-mail nobody, so when two of them fail in a row the
  site opens **"The website update keeps failing"**,
  naming the failing part and what to do. It closes by itself after the next run that works.

It is normal for **one** source to fail now and then (Instagram in particular sometimes refuses
robots). Nothing is lost: the previous items stay on the site and the next run tries again.
Only worry if the same source fails for more than a week — that is when the issue above appears.
See [Troubleshooting](#15-troubleshooting).

---

## 9. Instagram: how the site reads it (please read)

**By default** the site looks at the two official accounts' **public embed pages** — the small
"widget" Instagram offers to websites — a few requests a day, and shows each post's picture, date
and the start of its caption, linking back to Instagram.

**Please know:** Instagram's terms of use **discourage automated collection** of its pages, even
public ones and even at this tiny volume. The committee can choose how strict to be:

| Choice | How | Result |
|---|---|---|
| **Default** — public embed pages | Nothing to do (`anonymous: true`) | Works most days; Instagram sometimes refuses for a day |
| **Official and compliant** — Instagram's own API | Add the free **Instagram token** ([section 10 b](#b-instagram-token-the-official-way)) | Most reliable, and the method Instagram's terms allow |
| **Official only, no token** — manual list | In `config/site.yml` set `sources:` → `instagram:` → `anonymous: false`, then list posts by hand in [`content/instagram.yml`](content/instagram.yml) | No automated visits to Instagram at all |

With `anonymous: false` and no token, only the posts you list in `content/instagram.yml` appear
(paste each post's link; add a `caption:` line, because the site will not visit Instagram to fetch
the caption or picture). Instructions are at the top of that file.

**A post taken down leaves the site too** (since October 2026, for anonymity). Each nightly update looks up again
a few posts that are no longer in an account's list (`sources.instagram.recheck_per_run`, 5): a post Instagram no
longer shows (deleted, archived or made private) is removed, with its picture, after two such answers at least
12 hours apart. A day when Instagram turns the site away decides nothing. Posts you listed by hand are never
removed this way.

---

## 10. Optional upgrades

None of these are needed. a) to c) are each a **GitHub secret** — a private value only the workflows can
read. To add one: repository **Settings** → **Secrets and variables** → **Actions** →
**New repository secret** → enter the **Name** exactly as shown and the **Secret** → **Add secret**.
d), the morning alarm, is set up outside GitHub (its key never goes into the repository) — and it is the
one we recommend.

### a) Google API key: exact dates for Drive files

Without it, Drive file dates come from the file name or the day the site first saw the file.

1. Go to <https://console.cloud.google.com/> (sign in with the committee Google account).
2. Top bar → project list → **New project** → name it `grapevine-site` → **Create**.
3. Menu → **APIs & Services** → **Library** → search **Google Drive API** → **Enable**.
4. **APIs & Services** → **Credentials** → **Create credentials** → **API key**. Copy it.
5. Click the new key → **API restrictions** → **Restrict key** → tick **Google Drive API** → **Save**.
6. In GitHub add the secret **`GOOGLE_API_KEY`** with that key. Done — the next run uses it.

The key is free for this amount of use and only reads folders that are already public.

### b) Instagram token: the official way

Instagram's *Business Discovery* API lets one Instagram **professional** account read the public
posts of other professional accounts (AA Grapevine's accounts are professional accounts). It is free
and takes about 30 minutes once. Someone comfortable with Facebook/Meta settings should do it:

1. The committee's own Instagram account → **Settings → Account type and tools → Switch to
   professional → Business** (free), linked to a **Facebook Page** the committee manages.
2. At <https://developers.facebook.com/> → **My Apps → Create app** → type **Business** → add the
   product **Instagram** (Instagram API with Facebook Login).
3. Get a token that never expires: **business.facebook.com → Settings → Users → System users** →
   add one (Admin) → **Assign assets**: the Facebook Page and the app → **Generate new token** with the
   permissions `instagram_basic`, `pages_show_list`, `pages_read_engagement`, `business_management`,
   expiry **Never**.
4. Find the committee's **Instagram business account ID** (a long number): open
   `https://graph.facebook.com/v21.0/me/accounts?fields=name,instagram_business_account{id,username}&access_token=TOKEN`
   (put your token in place of `TOKEN`) and copy `instagram_business_account` → `id` (not the Page id).
5. Add the GitHub secrets **`IG_ACCESS_TOKEN`** (the token) and **`IG_BUSINESS_ID`** (the id).

The next run uses the API automatically. Full technical notes are at the top of
`scripts/sync/instagram.py`. If the token ever stops working, the Status page shows an Instagram
error; generate a new token and replace the secret.

### Meeting-list keys (Dallas, Fort Worth) — usually nothing to do

The Meetings page lists the Grapevine meetings of the intergroups' public meeting lists
(`meetings:` in `config/site.yml`). Dallas Intergroup and the Fort Worth Central Office answer
their full list only with a key. The key is already stored in the settings (`feed_obf`), hidden the
same way the Rowlett Group's meetings page hides it (written backwards and base64-encoded — this
only keeps it from casual reading, it is not encryption). Each run tries the keys in this order:

1. the optional GitHub secret **`TSML_KEY_AADALLAS`** / **`TSML_KEY_FORTWORTHAA`** (the key alone, or the whole
   list address with `&key=…`);
2. that office's `feed_obf` in `config/site.yml`;
3. the Rowlett Group's `meetings.html` (`meetings.key_source.url`, the constant named in `key_const`).

A key the office refuses (HTTP 401 / 403) is skipped and the next one is tried; a warning on the run (and
in `data/raw/meetings.json` → `stats.warnings`) names the refused source, so a stale secret or `feed_obf`
can be updated. A key is only ever sent to its own office's site (a redirect to another site is not
followed), and no key is written anywhere in plain text. If an office gives out a new key, either add it
as the secret, or run
`python -m scripts.sync.meetings --obfuscate "<the full list address with the new key>"` and paste the
printed value into that office's `feed_obf`. Without any working key, the office's public meeting page is
read instead, so the meetings keep showing. If a list cannot be read — or comes back empty, or its page
changed format — that office's previous meetings stay on the site until it works again.

### c) Monthly e-mail digest: keep every district informed

Early each month the site can e-mail a clean **English + Spanish** recap of **last month** — the same
edition GVRs copy from the **Monthly digest** page (`/digest/`, which shows the *September 2026 digest* all
through October):

- the bulletin's posts, the events that took place (the committee meeting included), and the committee's
  files and new photo albums added that month (a report named after an earlier meeting too, with its own date);
- the Grapevine and La Viña issues whose stories came out online that month: theme, number of stories, a few
  highlights (free to read first) and a link to all of them;
- stories by writers from Area 65 and the rest of Texas;
- podcast episodes (a YouTube upload of the same episode is shown once, with an "also on YouTube" link),
  other videos, the magazines' **Instagram** posts (how many each account shared, the newest ones and a link
  to the site's Instagram page) and new documents;
- and **one link**, "Coming up in October", to this month's page of the **Monthly toolkit**
  (`/monthly/2026-10/` in October) — the home of everything current: the committee meeting (with a link to
  its Zoom details on Meetings), the events still to come, the weekly open meetings, story deadlines and
  La Viña's topics, this month's issues and tips, the Book of the Month and subscriptions.

It goes out **once**, on the **1st from 7 AM Central**, as soon as the site's first full update of the month
has run (the Morning check starts it early on the 1st), so the month's last items are in it — usually on the
1st. If that update is late, it tries again later that day and on the 2nd; from **noon on the 3rd** it goes
out with the data there is. (GitHub starts these scheduled runs late, sometimes by hours — that is normal.)

Send it to one **Google Group** that includes all DCMs / GVRs / RLVs, and the districts get it
without anyone lifting a finger.

**With a Gmail account** (for example the committee's):

1. Turn on **2-Step Verification** for that Google account.
2. Go to <https://myaccount.google.com/apppasswords>, create an app password named
   `grapevine digest`, and copy the 16-letter password.
3. Add these GitHub secrets:

| Secret | Value |
|---|---|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` *(optional — 587 is the default; use 465 if your provider says "SSL")*. The password is only ever sent over an encrypted connection: on 587 the mail server must offer STARTTLS (Gmail does), otherwise the run stops without sending it |
| `SMTP_USERNAME` | the full Gmail address |
| `SMTP_PASSWORD` | the 16-letter **app password** (not the normal password) |
| `DIGEST_TO` | where to send it — ideally one Google Group address; several addresses can be separated by commas (they are sent as **Bcc**, so nobody sees the others) |
| `DIGEST_FROM` | *(optional)* the "From" address, if different from `SMTP_USERNAME` |
| `DIGEST_REPLY_TO` | *(optional)* where replies go (default: `contact_email` in the settings) |

4. **Preview first:** Actions → **Monthly e-mail digest** → **Run workflow** (leave *Preview only* ticked) →
   open the finished run → **Artifacts** → download **digest-preview** → open `digest.html`. The *month* box
   is the month the digest **covers**: empty = last month; `2026-09` = the September digest (the one sent on
   October 1). Write it exactly like that: a month typed any other way — `2026-9`, `Oct` — stops the run,
   and nothing is sent.
5. To send one right away, run it again with *Preview only* **unticked**. A manual send goes at once (with the
   data there is — it does not wait for the update) and counts as that month's e-mail, so the scheduled tries
   then skip it. Like a scheduled try, it sends nothing when nothing was new that month. A month that already went
   out is **not sent twice**: the run only shows *"Already sent"*. To send it again on purpose, tick **force** as
   well (the run is titled "SEND AGAIN (forced, started by hand)").
6. If a run ever fails with **"It MAY have been sent"**, the connection broke while the e-mail was being
   handed over. The month is marked as done, so the later tries do not send it again: check the Google Group (or
   a district's inbox), and only if it did not arrive send it with **Run workflow** (*Preview only* unticked,
   **force** ticked). If a run was cut off while sending, every later try shows a yellow *"Digest send not
   confirmed"* and sends nothing by itself: check the same way. Other failures (wrong password, server not
   reachable, e-mail refused) send nothing; the next try sends it.

How many stories each magazine issue shows and how many items each list shows before "and N more" are
set in `config/site.yml` → `digest:` (`highlights`, `per_section`). If nothing was new last month, no
e-mail is sent. To stop the digest, delete the `SMTP_PASSWORD` secret.

### d) The morning alarm: today's quote on the site by 5:30 AM (recommended)

**Why:** GitHub starts the site's own timed runs when it has room. Since late August 2026 that is often
4 to 8 hours late, so without help the new day's quote may reach the site only in the afternoon. The
morning alarm is a free outside alarm clock that presses the site's **Morning check** button at
**4:30 AM Central** every day. The Morning check puts the new day and both daily quotes on the site within
minutes, and does nothing when they are already there. Setting it up takes about 15 minutes, once. Sign in
to GitHub as **the owner of the repository**.

**Part 1 — a key for the site's workflows only (GitHub)**

1. Click your picture (top right) → **Settings** → at the bottom of the left menu **Developer settings** →
   **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Fill in:
   - **Token name:** `Morning alarm`
   - **Description:** `cron-job.org starts the Morning check of the GV/LV website at 4:30 AM Central`
   - **Resource owner:** **NETA65** (the account that owns the repository).
   - **Expiration:** *Custom* → one year from today. **Write that date in your calendar**, with a reminder a
     week before: on that date the alarm stops until the key is renewed ([Housekeeping](#14-housekeeping)).
   - **Repository access:** *Only select repositories* → **aagrapevine**.
   - **Permissions → Repository permissions → Actions → Read and write**. Nothing else (GitHub adds
     *Metadata: Read-only* by itself).
3. **Generate token** → copy it (it starts with `github_pat_`). GitHub shows it only once, so keep the page
   open until Part 2 is done. **Never** paste it into a file of the repository, an issue or an e-mail.

**Part 2 — the alarm clock (cron-job.org: free and open source)**

1. Go to <https://cron-job.org> → **Sign up** with the committee's e-mail address → confirm it → sign in.
2. **Cronjobs** → **Create cronjob**:
   - **Title:** `GV/LV website — Morning check`
   - **URL:** `https://api.github.com/repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches`
   - **Execution schedule:** every day at **4:30**.
   - **Notifications:** tick "execution fails" and "succeeds after previously failing".
3. The **Advanced** tab:
   - **Time zone:** `America/Chicago` (it follows daylight saving by itself)
   - **Request method:** `POST`
   - **Headers** (Key → Value):
     - `Accept` → `application/vnd.github+json`
     - `Authorization` → `Bearer ` and the key (one space after *Bearer*)
     - `X-GitHub-Api-Version` → `2022-11-28`
     - `Content-Type` → `application/json`
   - **Request body:** `{"ref":"main"}`
4. **Create**, open the job → **Test run**. The answer must be **204** ("OK, started"). On GitHub,
   **Actions → Morning check (new day by 5:30 AM)** now shows a new run (it may simply say the site
   is already up to date).
5. Close the page that shows the key.

**See that it works:** the next mornings, **Actions → Morning check (new day by 5:30 AM)** → the day's run says
"on the site since 4:34 AM CDT — goal 5:30 AM", and the **Status** page says when today's quotes came in.

**If cron-job.org e-mails a failure**, open the job's **History**:

| Answer | Meaning | What to do |
|---|---|---|
| **401** | The key expired or was deleted | Make a new key (Part 1) and replace the *Authorization* value |
| **403** | The key's *Actions* permission is not *Read and write* | Edit the key (**Settings → Developer settings → Personal access tokens → Fine-grained tokens → Morning alarm**): **Permissions → Actions → Read and write** |
| **404** | The repository or the workflow file was renamed (or the key cannot see the repository) | Fix the URL; check the key's *Repository access* |
| **422** | The body is not exactly `{"ref":"main"}`, or the Morning check is switched off | Correct the request body; or **Actions → Morning check (new day by 5:30 AM) → Enable workflow** |

Meanwhile the site still updates, only later in the day.

**Stop the alarm:** disable the job at cron-job.org, then delete the key under **Developer settings**.
The key can do what this repository's **Actions** tab can: start, re-run, cancel and delete its workflow
runs (and their logs), clear its caches, switch its workflows on or off and change a few Actions settings.
It cannot change the site's files or secrets — but it could, for example, send the monthly e-mail to every
district again, or start hours-long searches of the magazines' websites. **If it ever leaks** (it was
pasted somewhere others can see), delete it at once, look in **Actions** for a workflow that was switched
off (**Enable workflow**), and make a new key (Part 1). Any scheduler that can send the same request works
too — for example a Google Apps Script timer in the committee's Google account, or a scheduled task on a
computer that is on at 4:30 AM.

---

## 11. First-run checklist

Done for the current site (the owner's once-only steps after the move are in
[The move to the NETA65 account](#the-move-to-the-neta65-account-september-30-2026)). For a new copy
(or after moving the repository) — click-by-click details are in
**[docs/SETUP-GITHUB.md](docs/SETUP-GITHUB.md)**:

- [ ] **Settings → Pages → Build and deployment → Source: GitHub Actions**
- [ ] **Settings → Actions → General → Actions permissions: Allow all actions** (leave *Workflow
  permissions* at its default — the workflows ask for exactly what they need)
- [ ] Check `site:` → `url:` and `repository:`, the address at the end of `sources:` → `crawler:` →
  `user_agent`, and the meeting details in `config/site.yml`
- [ ] **Actions → Website update → Run workflow** once, with **crawl_minutes** left empty (the
  daily setting, 40 minutes).
  - Use **`300`** only if the big first PDF search has *not* been saved in the repository yet:
    after the first run, open the run's summary on the **Actions** tab — if its **PDF crawl** line shows
    only a small part of the known pages crawled, you may run it once more with `300`. (The committee's first PDF search was run
    ahead of time and saved, so normally `40` is right. Without it, the daily 40-minute search still
    reaches every page within about 10 days.)
- [ ] When the run shows a green ✓, open the website and its **Status** page.
- [ ] *(Recommended)* Turn on failure e-mails, and make sure they come to you (see
  [section 8](#8-is-everything-working)).
- [ ] *(Recommended)* Set up the [morning alarm](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)
  and press its **Test run** once (the answer must be 204).

### What to expect on day 1

- **Magazine stories, both podcasts, videos and Instagram** appear on the first run.
- **The PDF Library** shows what the first PDF search found and keeps growing and re-checking daily.
- **Committee sections** (Portfolio, Photos, flyer events, the Bulletin) show a friendly
  **"nothing here yet"** message: the Panel 77 folders in Drive are still empty. They fill in the
  morning after the first uploads. The **committee meeting** dates show right away (from the settings).
- **Translations:** the first run translates hundreds of titles (up to 40 minutes a day); anything not
  done yet shows in its original language and is finished on the next runs.
- **Monthly e-mail** stays off until its secrets are added; the **link check** first runs on Sunday.

---

## 12. Using your own address (custom domain)

For example **grapevine.neta65.org** instead of neta65.github.io/aagrapevine:

1. **DNS** (whoever manages neta65.org — the Area webmaster): add a **CNAME** record
   `grapevine` → `neta65.github.io` (the GitHub account that owns this repository).
2. **GitHub:** repository **Settings → Pages → Custom domain** → type `grapevine.neta65.org` →
   **Save**. Wait for the green "DNS check successful" (minutes to a few hours), then tick
   **Enforce HTTPS**.
3. **Settings file:** change `site:` → `url:` in `config/site.yml` to `https://grapevine.neta65.org`.
4. Run **Website update** once. Links, feeds and share buttons now use the new address.

No `CNAME` file is needed: sites published by GitHub Actions take the domain from the Pages
setting, and the workflow reads the address from there by itself. Links and QR codes that show
neta65.github.io/aagrapevine keep working: GitHub forwards them to the custom domain.

---

## 13. Replacing the old site

The committee's old site at **https://neta65.github.io/Grapevine/** (repository `NETA65/Grapevine`)
was edited by hand. None of its content (old flyers, announcements, events, photo lists) is carried
over — only the logo and the grapevine artwork live on in the new design. That repository is private
now, so the old address shows GitHub's "404". If old links, bookmarks or printed flyers still point
there, pick **one** of these (signed in to GitHub as **NETA65**):

**Option A — keep the new address and forward visitors from the old one (recommended)**

1. Open github.com/NETA65/Grapevine. Delete the old files (or leave them — only `index.html` and
   `404.html` matter).
2. **Add file → Upload files:** upload [`docs/redirect-old-site/index.html`](docs/redirect-old-site/index.html)
   as `index.html`, and a second copy renamed **`404.html`** (so old deep links forward too). Commit.
3. **Settings → General → Danger Zone → Change visibility → Public** (GitHub Pages is free only for
   public repositories).
4. **Settings → Pages → Build and deployment → Source: Deploy from a branch** → `main` / `(root)` → **Save**.

A few minutes later, visitors of the old page land on the matching new page — for example
`…/Grapevine/#events` opens the new **Events** page, in Spanish if they had chosen Spanish on the old
site. If the new site's address ever changes, open the uploaded files with the pencil icon and change
`NEW_SITE` at the very top — plus the same address in the three places marked *NO-JAVASCRIPT FALLBACK*.

**Option B — the new site takes over the old address**

Only if the old address matters more than the current one: every link, bookmark and QR code that
shows neta65.github.io/aagrapevine then stops working (GitHub does not forward a Pages address after a
rename), and people who installed the app install it again.

1. github.com/NETA65/Grapevine: **Settings → General** → rename it to `Grapevine-old` (or delete it
   once you're sure).
2. This repository: **Settings → General** → rename `aagrapevine` to `Grapevine`.
3. In `config/site.yml` set `url: "https://neta65.github.io/Grapevine"` and
   `repository: "https://github.com/NETA65/Grapevine"`, and update the address in
   `sources: → crawler: → user_agent`.
4. The [morning alarm](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended): change the
   job's URL to `…/repos/NETA65/Grapevine/…`, and check the key's *Repository access* includes it.
5. Run **Website update**. The workflow detects the new address and folder name by itself.

### The move to the NETA65 account (September 30, 2026)

The repository was re-created in the committee's account as **NETA65/aagrapevine** (a new repository,
not a GitHub transfer), and the site moved from `mkp715.github.io/AAGrapevine` to
**<https://neta65.github.io/aagrapevine/>**. The old address is **not** forwarded: a link, bookmark or
printed QR code from before the move must be replaced with the new address, and someone who installed
the app before the move removes it and installs it again from the new site
([Install the app](#install-the-app-offline-use-and-data-saver)). What the site kept in a browser
belongs to the old address and does not come across either: on the new site, Tracker entries and
receipt photos, district report drafts, GVR / RLV 101 progress, listening positions and saved offline
pages start empty, and the **Aa** settings and the theme are back at their defaults. A GVR who backed
up the Tracker restores that file on the new Tracker (*Have a spreadsheet or a backup? → Import it*);
otherwise the entries are typed in again. The site's own QR codes, share buttons, feeds and calendar
file use the new address by themselves.

Settings never come along with the files. Done once, signed in to GitHub as **NETA65**:

- [ ] **Failure e-mails:** **Actions → Website update → ⋯ → Disable workflow**, then **Enable
  workflow**, and the same for **Morning check (new day by 5:30 AM)**, **Monthly e-mail digest** and
  **Weekly link check**, so the e-mails about their timed runs come to NETA65
  ([section 8](#8-is-everything-working)). Do it after the last push that changed a schedule (the
  schedules moved 4 hours earlier on September 30, 2026, pushed from another account). Set **Watch** to
  **All Activity** (or *Custom* with *Issues*) so the automatic issues reach you too.
- [ ] **The morning alarm** ([10 d](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)):
  a new key (*Resource owner* **NETA65**, *Repository access* **aagrapevine**) and, at cron-job.org,
  the URL `https://api.github.com/repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches`
  with the new key → **Test run** (204). A job still set to the old `…/repos/MKP715/AAGrapevine/…`
  address gets 404.
- [ ] **Secrets**, only for the optional upgrades you use: the new repository starts with none
  ([docs/SETUP-GITHUB.md → Where to add secrets](docs/SETUP-GITHUB.md#where-to-add-secrets)).

For a later move, follow
[docs/SETUP-GITHUB.md → If you move or copy the repository later](docs/SETUP-GITHUB.md#if-you-move-or-copy-the-repository-later).

---

## 14. Housekeeping

- **Keep the repository public.** GitHub Actions is free and unlimited for public repositories.
  A private repository gets 2,000 free minutes a month, which the daily update would use up.
- **The 60-day rule.** GitHub pauses scheduled workflows in a public repository after 60 days
  without activity. The daily data commit counts as activity, so this should never happen. If it
  ever does: **Actions → Website update → Enable workflow**, and the same for
  **Morning check (new day by 5:30 AM)**, **Monthly e-mail digest** and **Weekly link check** (a
  switched-off Morning check also turns the morning alarm away: 422).
- **Dependabot pull requests.** Once a month GitHub may open a pull request titled
  `chore(actions)…` (the workflows' building blocks) or `chore(deps)…` (the site tools, and since October 2026 a
  new **major** version of a Python package: every run already installs the newest minor and patch releases,
  `requirements.txt` caps each package below its next major version, and `yt-dlp` has no cap; also each newer
  `playwright`, pinned in `scripts/ops/requirements-browser.txt` for the browser checks and the posters' share
  pictures). About 10 minutes later the **Code check** has built the website with the update, opened it in a real
  browser and run the tests: **merge only if the pull request shows a green ✓**. If it shows a red ✗, leave it open (or close it) — the live site is not
  affected. After merging, glance at the next **Website update** run; if it is red, open the merged
  pull request and click **Revert**.
- **Who gets the failure e-mails.** E-mails about the timed runs — Website update, the hourly backstop of
  Morning check (new day by 5:30 AM), Monthly e-mail digest, Weekly link check — go to the person who
  last switched each workflow on (or last changed its schedule). When a new chair takes over, after
  moving the repository, or after someone else changed a schedule, the person who should receive them
  opens **Actions → Website update → ⋯ → Disable workflow**, then **Enable workflow**, and does the same
  for **Morning check (new day by 5:30 AM)**, **Monthly e-mail digest** and **Weekly link check** (and
  turns on the e-mails, see [section 8](#8-is-everything-working)). The runs the morning alarm starts
  e-mail the owner of its key.
- **Repository size** grows slowly (data files and small preview pictures). That is expected; see
  [docs/OPERATIONS.md](docs/OPERATIONS.md#repository-size) if it ever passes about 1 GB.
- **Daily data commits** by `github-actions[bot]` ("chore(data): daily content sync …" — a full update, nightly or
  started by hand —, "… morning refresh with the daily quotes of Oct 6 …" (or "… with the Grapevine quote of
  Oct 6 and the La Viña quote of Oct 5 …", or just "… morning refresh …" when no quote is new), "… midday
  refresh …", "… evening refresh …",
  "… quick refresh …", "… content sync after settings/content change …"; with "+ writers archive" before the date
  when that run took a new archive file in) are normal.
- **Renew the morning alarm's key once a year**, about a week before the date in your calendar (on that
  date it stops working): **Settings → Developer settings → Personal access tokens → Fine-grained tokens
  → Morning alarm → Regenerate token** → **Expiration:** *Custom* → one year from today → **Regenerate
  token**, then paste the new key after `Bearer ` in the cron-job.org job's *Authorization* header, press
  **Test run** (204) and write the new date in your calendar. The key must be made by the repository's
  **owner** (a key only reaches its owner's repositories): when the chair changes, the owner keeps — or
  remakes — it; if the repository moves ([section 13](#13-replacing-the-old-site)), make a new key with the
  new owner as *Resource owner* and change the job's URL
  ([10 d](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended)).
- **Many Morning check runs** in the Actions tab are normal: GitHub's own schedule starts it every hour
  from the afternoon through the night as a backstop (it begins 4 hours early because GitHub runs late). A run that had nothing to do (today's update was already there, or it was
  too early to ask a magazine) takes a few seconds and is deleted the next day; the others stay, so you can
  see what each morning did.

---

## 15. Troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| The site did not change today | The run failed, is still running, or the schedule was paused | **Actions** tab: open the latest **Website update** run. If the workflow shows "disabled", click **Enable workflow**. Then **Run workflow**. |
| Today's quote is not on the site at 5:30 AM | The morning alarm is not set up or failed; the magazine had not published it yet; or the morning refresh failed | **Actions → Morning check (new day by 5:30 AM)**: the day's run says which (a yellow "late at the source" note says when the magazine was last asked — the site shows yesterday's quote, labelled "Yesterday", until an update brings the new one). No run at 4:30 AM: check the alarm (cron-job.org's e-mail or the job's *History*). To bring it now: **Morning check (new day by 5:30 AM) → Run workflow** — from 2 AM Central it asks the magazine and brings the quote if it is out. If an update is already running — on the 1st, the full daily update — it waits for that run first (it reads the quote too) and then brings whatever it did not. |
| cron-job.org e-mails that the alarm failed (401, 403, 404 or 422) | The key expired or was deleted (401), its *Actions* permission is not *Read and write* (403), the address changed (404), or the request body is wrong (422) | See [10 d](#d-the-morning-alarm-todays-quote-on-the-site-by-530-am-recommended) → *If cron-job.org e-mails a failure*. Until it is fixed the site still updates, later in the day. |
| Many **Morning check** runs in the Actions tab | Normal: GitHub's schedule starts it every hour from the afternoon through the night | Nothing to do: the runs that found nothing to do are deleted after a day. |
| A bulletin post with `publish:` / "(from …)" is not on the site | Its day has not come yet (Central time), or its date could not be read | The **Website update** run summary lists it under *Scheduled bulletin posts*, or under *Bulletin files to fix* with the reason. |
| One phone or computer shows an old page, or a page looks unstyled after an update | A copy the browser kept (the site works offline) | Reload the page; if the small "Updated" notice shows, choose **Reload**. Still wrong: close every tab of the site and open it again. Last resort on that device: browser settings → site data for the site → clear (its saved pages go too). |
| Red ✗ right after editing a settings file | A typo in the YAML (usually indentation or a missing quote) | Open the failed run → the red step shows the line. Fix the file, or undo your change from the file's **History**. The live site is unaffected. |
| Red ✗ with *"Tests failed — not published"* | A change to the code broke the automatic tests, so it was not published (the live site keeps the version before) | The run summary's *Tests before publishing* lists the failing tests, and which of them read the committee's own files. Fix the change or undo it; the next run publishes. [how-to/automation-and-troubleshooting.md §14.10](how-to/automation-and-troubleshooting.md#1410-tests-failed--not-published) |
| An issue "The website update keeps failing" appeared | Two timed (or Morning check) runs in a row failed | Open the issue: it names the failing part and links the run. It closes itself after the next run that works. |
| Status page: a source says **On hold** | It suddenly found far fewer items (or a Drive folder looked empty), so the missing ones stay until the next update confirms it | Nothing to do: the next update removes them if they are really gone. A big removal of your own (many Drive files at once) leaves the site one update later. |
| A Drive file does not appear | Wrong folder, folder not public, name contains `PRIVATE`, it is a spreadsheet, or the update hasn't run yet | Check the file is inside the current Panel folder and the root folder is shared "Anyone with the link". Wait for the next run or run it manually. |
| A flyer did not become an event | No date at the start of the name, it is not in *flyers*, or the name is the phone's own (IMG_…, WhatsApp Image …, Screenshot …) | Rename it like `2027-03-14 Title 9am @ Place.pdf`. |
| A bulletin post did not appear | Not in the *bulletin* folder, or its `(until …)` date passed | Move/rename it; it must be a Google Doc, .txt, .md or .docx. |
| A translation is wrong | Machine translation | Add a fix to `data/translations/overrides.yml` ([section 5](#5-fixing-a-translation)). |
| Instagram stopped updating | Instagram is refusing robots for a while (or `anonymous: false` without a token) | The last posts stay and it usually recovers. For a permanent fix add the [Instagram token](#b-instagram-token-the-official-way). |
| The PDF library looks small | Usually nothing is wrong: the PDF search has checked every page of both sites (about 3,450 pages) and found about 130 PDFs; the Library shows the official ones, each once (about 90 entries: copies, older versions and language editions are merged) | Open the last **Website update** run's summary → the **PDF crawl** line (or `data/site/status.json` → `crawl`). If (nearly) every known page is crawled, the library is complete and there is nothing to do. Only if few are (for example after the crawl's saved progress was deleted) run **Website update** once with `crawl_minutes = 300`. The run log's `pdf_curate` lines say which documents were merged and why. |
| Site shows "404 — There isn't a GitHub Pages site here" | Pages not switched to GitHub Actions | **Settings → Pages → Source: GitHub Actions**, then run **Website update**. |
| Run fails at "Read GitHub Pages settings" | Same as above | Same as above. |
| Run fails at "Commit refreshed data" with *permission denied* / *403* / *protected branch* | A rule on `main` stops the bot from saving its data | If `main` has branch protection or a ruleset, add **GitHub Actions** to its bypass list (**Settings → Rules** or **Settings → Branches**). The workflow already asks for write access itself; *Workflow permissions* does not need changing. |
| Status page: a calendar under *Other calendars we read* says "Blocked by the site's bot protection" | That website (neta65.org) turns robots away with Cloudflare | Until it is fixed, a workshop or assembly shows on the Events page only after someone adds it to `content/events` by hand ([how](#6-bulletin-posts-and-events-without-drive-optional)). To fix it, ask the site's webmaster to let calendar requests through ([what to send](#the-neta-65-workshop-calendar)). |
| The holiday cards are not on the Shop page | Out of season: the stores sell them from about September through the holidays | Nothing to do — they come back with the weekly read once a store sells them again. If a store has them now but the page does not: look at `/status/` (a holiday page the store changed, or one that is down while the store's listing still shows the cards, is reported there under "Book of the Month, prices & specialty items"), then check `config/site.yml` → `sources.<grapevine/lavina>`: the `specialty` addresses (the "specialty-items" / "articulos-especiales" listings find the cards even at a new address) and that `specialty_skip` does not name `holiday`. The specialty items are read once a week, so a fix shows within 7 days (sooner: `python -m scripts.sync.shop --refresh-specialty`, then **Website update**). |
| An issue "A content source has stopped updating" appeared | One source has not updated for 7 days (the site keeps its older items) | Open the issue: it names the source, the error and what to check (for Google Drive: is the folder still shared "Anyone with the link"?). It closes itself when the source works again. |
| Yellow ⚠ "Translation models missing" or "Translation is not working" | The free translation models could not be downloaded (their website was down or moved) | New titles stay in their original language; nothing else is affected. If it lasts more than a few days, send the run's log to whoever helps with the website. |
| Run fails at "Publish to GitHub Pages" with *environment protection* | The `github-pages` environment only allows certain branches | **Settings → Environments → github-pages** → allow the `main` branch. |
| The monthly e-mail did not arrive | Secrets missing, wrong app password, nothing new last month, or it is still waiting for the month's first full update (it goes out on the 1st from 7 AM Central once the site has updated — at the latest from noon on the 3rd) | Open the latest **Monthly e-mail digest** run: its summary says exactly which ("waiting for the data" means a later try sends it; "Digest send not confirmed" means a send was cut off: check the group). Gmail needs an **app password**. To send it now, run it with *Preview only* unticked (and **force** ticked if the month was marked as sent). |
| Someone installed the site, but it opens in the browser (a small Chrome badge on its icon, or it opens in Safari) | It was added as a shortcut or a bookmark, not as the app | Send them `/offline/#steps`: on Android, remove the icon and choose **Install** (not "Create shortcut"); on iPhone, remove it and add it again with **Open as Web App** on. |
| An issue "Broken links found by the weekly check" appeared | A link in the settings or in a `content/` file moved | Open the issue; fix the address in `config/site.yml` or the `content/` file. It closes itself when fixed. |
| A new archive file in `content/archive` is not on `/published/#archive` | Its name is not understood or carries an older date, it is not a `.csv` file (an `.xlsx` export, for example), or it was not used (a missing column, far fewer rows than the file before) | The **Website update** run summary's *Writers archive* lines say which (**CSV file to fix**); the older rows stay on the site meanwhile. A file with a missing column, or one that cannot be read, also turns the **Code check** red; *Website update* still publishes (it leaves the tests of the committee's own files to the Code check). See [how-to/writers-archive.md](how-to/writers-archive.md). |
| Red ✗ on **Code check** only, after saving a settings or content file | A slip in that file (a date without its year, a bad booth row, a setting no code reads …) | The Code check's log names the file and what to change; the site was published without the part it could not read. Fix the file soon. |

Still stuck? Open the failed run, click the red step, copy the last 20 lines, and send them to
whoever helps with the website (or open an **Issue** in this repository).

---

## 16. How it works

```
 every morning (GitHub Actions)                                     GitHub Pages
 ─────────────────────────────                                      ────────────
  aagrapevine.org ─┐
  aalavina.org  ───┤  Python sync scripts    data/raw/*.json     Eleventy +      website
  2 podcast feeds ─┤  (scripts/sync/*.py) ──► + translation   ──► Tailwind    ──► in English
  YouTube ─────────┤  polite: robots.txt,     (offline, open      (src/)          and Spanish
  Instagram ───────┤  5-second crawl delay    source models)
  Google Drive ────┘                          data/site/*.json
                                              committed to this repository (history = backup)
```

Technical details, how to run it on your own computer, and how to add a new source:
**[docs/OPERATIONS.md](docs/OPERATIONS.md)**.

**Page design (for developers).** Every page is built from the same shared pieces, so the site
reads as one: the hero (`ui.pageHero`, with the grapevine art), section headers (`ui.sectionHead`
in eyebrow form), the in-page nav of long pages (`ui.pageNav`), "Updated … ago" (`ui.freshness`),
closing link cards (`ui.nextSteps`), the collapsed "For committee members" help (`ui.memberHelp`),
the page-level "nothing yet" card (`ui.pageEmpty`) and the in-list "no results" box
(`ui.emptyState`) — all in `src/_includes/macros/ui.njk`, each documented at the top of that file.
The matching CSS utilities (cards, buttons, chip rows, `sticky-aside`, `meta-row`, `tap-link`,
`step-num` …) and the rules for what may stick to the screen are documented at the top of
`src/assets/css/main.css`. Two rules to keep: nothing may cover content (sticky columns end above
the language banner and never grow taller than the window), and the one gap before the footer is
the footer's own margin.

### Reading & display settings and the Accessibility page

The **Aa** button at the top of every page (in the Menu on phones) opens **Reading & display**: text size
(100 / 115 / 130 / 150%), spacing (relaxed = the WCAG 1.4.12 text spacing), contrast (high, in light and
dark mode), motion (follow the device / reduce: the vineyard art stops) and **Read aloud** (the device's
own voice reads the page, paragraph by paragraph, in the page's language), then Data saver and the
"Offline & app" part (above). The choices are saved on that device only (`localStorage "gvlv-prefs"`) and
applied before the page is drawn; nothing is sent anywhere. **Reset to defaults** clears them.

**Light or dark:** the moon / sun button in the header (from 640px wide), or the **Dark mode** switch, the
first line of the Menu on phones and tablets — one setting, saved on that device (`localStorage
"gvlv-theme"`) and applied before the page is drawn; until someone chooses, the site follows the device's
own light / dark setting.

The **Accessibility** page (`/accessibility/`, in the footer) explains the settings and gathers the other
ways in: YouTube captions, AA Grapevine's American Sign Language playlist and AA's own ASL videos, audio
(podcasts, the weekly open meetings, recording a story by phone), printing and large print, joining our
meetings by phone ([above](#joining-our-meetings-by-phone)), and how to report a barrier.

**For maintainers**

| File | What it does |
|---|---|
| `src/_includes/partials/comfort-panel.njk` | the panel (included by `header.njk`; the Aa buttons are in the header and the drawer) |
| `src/_includes/partials/header.njk` | light / dark: the header's moon / sun button and the menu's "Dark mode" switch (`role="switch"`; its look: `main.css` `.site-switch`), both `app.js` `siteHeader` `theme` / `toggleTheme()` |
| `src/_includes/layouts/base.njk` | the first `<head>` script: saved choices → `<html data-text data-spacing data-contrast data-motion data-saver>` |
| `src/assets/js/app.js` | `GV.prefs` (read / save / apply; event `gvlv:prefs`), `GV.reducedMotion()`, `GV.tts` (read aloud), the panel |
| `src/assets/css/main.css` → "READING & DISPLAY SETTINGS" | what the settings do site-wide (text scale, spacing, high-contrast colours, reduced motion, larger-text layout rules) |
| `src/assets/css/areas/access.css` | the panel's look, the read-aloud highlight, the header and nav at larger text, per-page adjustments, the Accessibility page |
| `src/pages/accessibility.njk`, `src/_i18n/access.json`, `eleventy/filters/access.js` | the page; `links:` in `config/site.yml` holds its official ASL and accessibility links |

### Install the app, offline use and Data saver

For weak signals — church basements, country roads, the long drive to the assembly — the site can be
installed like an app, works without a connection, and can save data. Everything happens on the
visitor's own device; nothing is sent anywhere.

**What to tell your group**

- **Install it.** Send the group the install steps on the **Saved pages & app** page:
  <https://neta65.github.io/aagrapevine/offline/#steps> (Spanish: `/es/offline/#steps`; its **Send this
  page** button shares that link, and old links to the install page land there too). The page is at the
  bottom of every page and under *More* in the phone menu (*Saved pages & app*), and the **Aa** menu leads
  to the steps (**Offline & app** → **Install as an app**). It opens the steps for the phone and browser it
  is opened on, marked "Your device":
  - Chrome and Samsung Internet on Android phones and tablets (and Chrome or Edge on a computer): one tap
    on **Install**. Choose **Install**, not "Create shortcut": a shortcut opens in Chrome.
  - Safari on iPhone and iPad: the menu next to the address bar — **Page Menu** on iOS 27, **More** on
    iOS 26 — then **Share** (on older iPhones, and on iPads, the **Share** button itself) → **Add to Home
    Screen**, with **Open as Web App** left on.
  - Chrome, Edge or Firefox on iPhone or iPad (iOS 16.4 and later): **Share** (Chrome: the button at the
    right of the address bar; Edge and Firefox: in the browser's menu) → **Add to Home Screen** → **Add**.
  - Firefox, Edge and others on Android: the browser's menu → **Add app to Home screen** (Firefox: under
    **More**) or **Add to phone** (Edge). The full app, with its own place in the list of apps, needs Chrome
    or Samsung Internet.
  - Safari on a Mac: **File → Add to Dock**.
  - A link opened inside Facebook, Instagram, Messenger, TikTok, LinkedIn and similar apps can't be
    installed. The page says so and shows how to open it in the phone's browser, with **Copy the link**.
    WhatsApp opens a link either in the phone's browser (install right away) or in its own window; in its
    own window the page says "You're reading this inside WhatsApp" and shows the same steps.

  The app is called **GV/LV 65**. It opens in its own window, in the language it was installed from, and
  has shortcuts to Meetings, Monthly toolkit and GVR / RLV 101 (touch and hold the icon on Android). Once
  it is installed, the Aa menu says "The app is on this device" (where the browser can tell); inside the
  app the install links go away and *Saved pages & app* says "You're using the app" (the guides stay
  closed until someone opens one).
- **The install notice.** On phones and tablets, a small notice at the bottom of the page says "Install this
  site as an app", with **Install** (where the browser offers one-tap install) or **Show me how**, and
  **Not now**. It appears after a visitor's 3rd page view (the 2nd with one-tap install), once they have
  spent 20 seconds on a page and tapped or scrolled. It never shows inside other apps, in the installed
  app, offline, on `/offline/`, while typing, or together with the language banner, the podcast player, read
  aloud, the Aa menu or the phone menu. How long it stays away:
  - **Not now** (or Escape): 30 days; after two "Not now"s it never comes back.
  - Reading the steps — **Show me how**, the Aa menu's **Install as an app**, or the steps on `/offline/`
    reached (a look at the saved pages above them doesn't count): 30 days.
  - Each time it shows and the visitor does neither: 7 days; after four showings it never comes back.
  - Installed from that browser, or opened as the app in the last 90 days: not shown. If the app is later
    removed and the browser offers one-tap install again, that is forgotten and the notice may return.

  On a short screen (a phone held sideways) it shows just its title and its two buttons. It is remembered
  on that device only (`localStorage "gvlv-app"`).
- **Use it offline.** Every page opened on the device is kept (the last 80). **Save key pages for
  offline** (same menu) keeps Home, Meetings, this month's Monthly toolkit, Share your story, Shop,
  Published writers (with the whole Texas writers archive), Accessibility and GVR / RLV 101, in the visitor's
  language, with their styles and scripts — a good
  idea before a trip. On a weak signal the save keeps going as long as pages keep arriving; only 45
  seconds without a page saved counts as a failure ("Try again with a better signal"). Saved from `/offline/`
  itself, its "Saved on this device" list shows the pages as soon as the save is done (no reload). The page open
  during the very first visit is kept too, with its own styles and
  scripts. "Save key pages" also asks the browser to **keep** them (persistent storage): the result line then says
  "This browser will keep them until you remove them." or "This browser may still remove them when the device is
  short of space." followed, since October 2026, by what helps on that device: on an iPhone, an iPad or Safari on
  a Mac "On this device an installed app keeps its own copy: install the site as an app, then open it and save the
  pages there to keep them."; on other phones and computers "Installing the site as an app and saving them again
  from the app helps keep them."; inside the installed app, and in a browser that cannot install the site (Firefox
  on a computer, the browser inside Facebook or Instagram), nothing more. Saved pages not opened for a week are
  fetched again in the background when the site is opened with a connection (one at a time, at most every 6 hours;
  a page that is gone keeps its saved copy) — but never while Data saver is on (the visitor's choice in the Aa
  menu, or *Automatic* with the browser's data saver or a 2G connection: then saved pages are refreshed only when
  opened online or saved again), and never beside "Save key pages" or the booth display's save (a save stops a
  running round, and a page the save removed, such as last month's toolkit, is not put back). A month's toolkit page
  saved for offline keeps its own calendar file too, so its **Add … to my calendar** button works offline (the big
  `/events.ics` feeds are never kept). A page opened online but not saved keeps its own area stylesheet (the
  monthly toolkit's, the booth's, the Tracker's …) offline after a code update too: the new service worker carries
  the old version's stylesheets over (nothing is downloaded for it). Offline, kept pages open normally under a small "You're offline" notice; any other
  page shows the Saved pages & app page (`/offline/`, also "See saved pages" in the menu) in its place,
  saying "You're offline — this page isn't saved on this device yet" above the list of saved pages, and
  reloads itself when the connection is back. That stand-in keeps up with the daily content (the **Join
  by phone** numbers, the footer): pages opened with a connection refresh it once a day, and opening Saved
  pages & app refreshes it at once. An address typed without its last slash (`…/aagrapevine/es`) opens
  the same saved page. When the connection is so slow that a page
  takes more than 4 seconds, the kept copy opens instead, with "Slow connection — this is the copy saved …
  Try again". Audio, video and the official sites always need a connection.
- **Data saver** (Aa menu: Off / On / Automatic — automatic follows the browser's own data saver and a
  2G connection; while offline its effects are always on): the hero art stays still, pictures are not downloaded
  (grey tiles), YouTube previews become **Load video (uses data)** buttons, podcast episodes show their
  download size (e.g. "70.1 MB") before you press play, and nothing is fetched ahead of time — not even the
  weekly background refresh of saved pages (since October 2026).
  **Show images** (in the small notice, or the Aa menu) brings the pictures back on that page.

**How updates arrive.** With a connection, pages always come from the site (checked with the site on
every visit), so a new deploy shows on the next page view. Styles and scripts carry a version in their
address (`main.css?v=…`: a fingerprint of the site's code, `src/_data/build.js`), so a new page never
runs with old styles. When the code changes, browsers install the new service worker in the background:
open tabs and the installed app show **Updated — A new version of the site is ready · Reload**
(Reload in one of them applies it, at once even on a weak signal: the open tabs' pages are refreshed afterwards,
in the background; in the other tabs, Reload then simply reloads the page);
otherwise it takes over the next time the site is opened after all its tabs were closed. The daily
content update does not change the code fingerprint, so it never triggers that prompt or a new
download of the styles and scripts. The offline stand-in (Saved pages & app), which carries that content,
is refreshed by the service worker itself instead: at most once a day as pages are opened, and whenever
that page is opened.

**For maintainers**

| File | What it does |
|---|---|
| `src/pages/manifest.11ty.js` | `/manifest.webmanifest` and `/es/manifest.webmanifest`: name, icons, colours, shortcuts (Meetings, Monthly toolkit, GVR / RLV 101); both the same app (id and scope = the site's base path; the Spanish one opens on `/es/`), each naming both as `related_applications`, so Chrome on Android can tell a tab the app is installed |
| `src/pages/sw.11ty.js` + `src/_includes/pwa/sw-core.js` | `/sw.js`: the cache rules are in the header comment of `sw-core.js`; the pages "Save key pages" keeps are the `save` list in `sw.11ty.js` (Accessibility and GVR 101 join it automatically once those pages exist) |
| `src/assets/js/pwa.js`, `src/assets/css/areas/pwa.css` | registration and updates, the "Offline & app" part of the Aa menu (with its install row), the notices (the install notice too), the live parts of `/offline/` (its hero, the saved pages, the install steps), and everything Data saver does |
| `src/assets/js/install-core.js` | which phone and browser this is (from its user agent — Android tablets asking for desktop sites included), which guide and which Safari step fit it, the name of the app a page is open inside, and the install notice's rules (`RULES`: page views, 20 s, quiet days, limits). Pure functions, tested with real user agents by `tests/test_pwa_install.py` |
| `src/pages/offline.njk` | *Saved pages & app* (`/offline/`, `/es/offline/`): what is saved on this device, how the site works without a connection, and the install steps (`#steps`): the seven guides — `iphone`, `iphone-other`, `android`, `samsung`, `android-other`, `in-app`, `computer` (their ids are the `#links` the site uses) —, why install it, good to know. The worker also shows it for a page that is not saved when there is no connection (it then says "You're offline" and offers **Try again**). A page like the others: in the sitemap, the search and search engines. The data-attribute contract with pwa.js is in its header comment; the official help links are `app_help_iphone(_es)` and `app_help_android(_es)` in `config/site.yml`. `src/pages/app-redirect.njk` keeps the old install page's address (and its `#guide` links) working |
| `scripts/dev/make_app_icons.py` | draws `src/assets/img/app-icon-*.png` and `apple-touch-icon-180.png` (`python -m scripts.dev.make_app_icons`) |

**Keeping the install steps current.** Phones move their menus: Safari 26 put Share behind **More**,
Safari 27 behind **Page Menu**, and Chrome 150 renamed its menu item **Install and create shortcut**.
Every September (a new iOS) and after big Chrome releases:
- compare the words in `src/_i18n/pwa.json` (`pwa.app.*`, English and Spanish) with Apple's and Google's
  help pages (linked in the steps on `/offline/`);
- update the pinned words in `tests/test_pwa_install.py` together with them;
- add any new in-app browser's user-agent token to `install-core.js` (and a test user agent).

After such a change, check on real phones: Android Chrome (the notice's **Install** puts the app in the
app drawer), a Samsung phone, an iPhone on the current iOS, and a `/offline/#steps` link tapped in a WhatsApp group
(on both, whether it opens in the browser or in WhatsApp's own window).

The worker only handles GET requests to this site: it never stores anything from other sites (YouTube,
podcast audio, aagrapevine.org, aalavina.org, Google Drive) and never touches forms. Caches: the app
shell and styles/scripts are replaced with each code version; kept and saved pages, images (≤ 200) and
the JSON indexes survive updates. Service workers need `https://` or `http://localhost` (so they work in
`npm start`); with a custom domain (`PATH_PREFIX=/`) the scope follows automatically. To test a clean
first visit in Chrome: DevTools → Application → Storage → **Clear site data**.

### The Tracker (service expenses)

The **Tracker** (Committee menu, <https://neta65.github.io/aagrapevine/tracker/>) is a GVR's, RLV's or
committee chair's own record of what their service costs and gives: miles, purchases, gift
subscriptions, literature given away and reimbursements. It lives only in that browser — nothing is
uploaded — so it asks for a backup now and then (**Back up now**: one `.zip` file with the receipt photos).
This describes Tracker 1.2.0 (October 2026).

**What to tell your GVRs**

- **Every entry can say what service it was for** — a *service activity*: Assemblies & Area committee
  meetings, District meetings, Information tables & conventions, Workshops & events, Grapevine / La Viña
  committee meetings, Groups & group visits, Other service. They are the sections of the service report,
  and each GVR renames, hides, reorders or adds them in **Settings → Service activities**.
- **Miles:** the one-way miles, **Round trip**, and **How many trips** for the same trip made on several
  days (3 days at a convention's table is one entry: 58.7 mi × 2 × 3 = 352.2 mi), a **Last day**, and
  **Your role** there (Attended, Table support, Tech setup, Zoom setup, Projector & screen… or their own
  words). An event reached riding with someone is **I didn't drive (I rode with someone)**: the event and
  the role stay on record, with no miles and nothing to ask back.
- **Purchases** keep their store's number (**Order or confirmation no.**, under *More details*; a hotel's
  **Confirmation no.** sits with its name and city), and a subscription bought several at once says
  **How many** (10 gift subscriptions for a jail: one entry).
- **Giveaways → Subscriptions:** every subscription given (or bought for someone, the group, oneself),
  where each stands today — *Ending soon* (within Settings → Reminders' days), *Ended*, *Active*,
  *Renewed* (a later one for the same person and magazine; a gift with no name, the next one with no
  name that starts once it ends — what **Record the renewal** writes, on time or late), *No end date* —
  how many were gifted in the period (Grapevine · La Viña; 10 bought at once count 10), **Record the
  renewal**, and **End dates for my calendar (.ics)**: a file for the phone's calendar with a reminder at
  9 AM that many days before each end (the next morning for one ending sooner; never one already past).
  Downloading it again after a renewal moves that subscription's event to the new end date instead of
  adding a second one.
- **Giveaways → Literature** follows the period at the top: given away, bought, received and on hand at
  its end (Grapevine · La Viña), each item's count (*At the start* + bought + received − given = on hand)
  and what went out at each event.
- **Requests → Service expense report:** what the service cost for a year, a panel or any dates, set out
  as a GVR's own expense report: the money by category, the miles by service activity (with the trips),
  the mileage total and the **total cost of service**; every entry if wanted (dates, hotel and
  confirmation, route, role, trips, one-way and total miles); literature given away and subscriptions
  bought, counted; who covers it (self-supported, asked back, received, still owed). The periods offered include
  the **service panels**, worked out by themselves (Area 65's two-year terms start on January 1 of an odd year:
  Panel 75 is 2025–2026, Panel 77 2027–2028), so nothing needs adding every two years. *Prepared for* and a
  note at the top ("This is a record, not a request for payment") are kept with the settings. People's
  names and the notes appear only when ticked. **Print or save as a document**, or **Download CSV** for a
  treasurer's spreadsheet. On screen, a table that has no room for all its columns (a phone, a tablet,
  larger text) puts its dates, routes and roles under the words, the amount always in sight; paper gets
  every column.
- **Who owes you** (Summary) and **Owed to you** count everything **up to the end** of the period shown: a
  hotel asked back in December and repaid in January shows "Even" in January's views ("Where things stand at the
  end of the period: …"), and still "Owes you" in December's — also once the request is marked **Paid**, as its
  paid date is in January (a request marked paid with no paid date counts as settled).
- **Backups** (Settings → Data → Export): **Full backup (.zip)** — `service-expenses-backup-YYYY-MM-DD.zip`
  (Spanish `gastos-de-servicio-respaldo-YYYY-MM-DD.zip`) holds `backup.json` and one picture file per receipt photo,
  so any unzip program opens it; **Back up without photos (.json)** —
  `service-expenses-backup-no-photos-YYYY-MM-DD.json`, small enough to e-mail (the photos stay on this device);
  and **Export CSV (all)**. Before saving it shows the size ("Full backup: about X, n receipt photos. Without
  photos: about Y."); above about 18 MB it says the full backup is too big to send by e-mail (most e-mail allows
  about 25 MB), and **Back up now** asks: Cancel, Without photos, or Save the full backup. Since October 2026 a full
  backup reads each receipt photo first: a photo this browser can no longer read (its stored file is gone) is left
  out and the rest is still backed up, and the message names it — "Downloaded … — without 1 receipt photo this
  browser couldn't read: Big Book · Sep 27." (at most 3 names). Settings → Data → Export then lists those entries
  under the buttons ("Not in the last full backup — this browser couldn't read these receipt photos. If you still
  have the receipt, open the entry and choose its photo again:") until the next full backup. A backup that fails all
  the same gives its own reason (too big for one `.zip`, for example) or says "The full backup couldn't be made. Back
  up without photos instead (Settings → Data): it keeps every entry and setting." *Last backup* is stamped even
  when photos were left out. ("The photos stay on this device" holds for the entries the browser stored: while it
  is not storing entries — storage full or blocked — a photo added meanwhile is in the full backup only.)
- **Restore** (Settings → Data → Import): a `.zip` backup, any `.json` backup of any size (the old 80 MB limit is
  gone; older backups with the photos inside still restore), or a backup that was unpacked: choose its
  `backup.json` together with its photos (zipped again with Windows' or a Mac's own "compress" works too). The
  preview counts any photo that is missing, and the photos come back one by one ("Restoring the receipt photos: n
  of total…"). Restoring a backup without photos keeps this device's photos; an entry whose photo is not on this
  device (it stayed on the one the backup came from) says **Photo not on this device** — in the list (a crossed-out
  picture instead of the paper clip) and in its form, which says how to add the photo again. Photos that could not
  be restored (a damaged `.zip` entry, storage that refuses) are said once when the photos are done: in the message
  ("Receipt photos that couldn't be restored: N.", read out by screen readers), or to screen readers alone while an
  **Undo** is on screen. A backup whose list names no photos (such as the repaired download of unreadable data,
  below) finds each entry's photo by its file name, `<entry id>.jpg` (or `.png`, `.webp`, `.gif`), chosen with it or
  zipped with it.
- **Import a spreadsheet:** a CSV (also Excel's "Unicode text", which is UTF-16), or an Excel workbook (`.xlsx`:
  its first sheet; Chrome or Edge 103+, Firefox 113+, Safari 16.4+). An old `.xls` gets a message to save it as
  `.xlsx` or CSV.
- **Safer:** fixing a typo in an imported entry keeps the details its form does not show (nights, quantity, item,
  attendees …). Leaving the page asks "Leave site?" with unsaved changes in the form — and, since October 2026, also
  while the browser is not keeping the entries (storage full or blocked, data saved by a newer version of the page,
  unreadable data with no room to set it aside), until a save works again or a backup has everything: a full
  backup always counts, a backup without photos only when no receipt photo exists in this tab alone, a CSV export
  never. (A phone that closes a background tab by itself asks nothing.) If the browser's stored Tracker data ever
  cannot be read, it is set aside unchanged and a notice offers **Download it** and **Remove it** (nothing new is
  saved over it): **Download it** gives a `.zip` of that data as it was plus the receipt photos it names (`<entry
  id>.jpg`), or the `.json` alone when it names none — repaired, it restores with those photos; **Remove it** says
  how many photos go too ("…and its receipt photos (2 receipt photos)? … the download has its photos too"), and
  after it the notice does not come back; **Erase everything** leaves that set-aside data and its photos in place.
- **Two tabs:** an entry with a receipt photo, open in the edit form in one tab and deleted in another, is saved
  again as itself — same id, its creation date, the details its form does not show and its photo, even after the
  other tab's undo time ran out and deleted the photo (the open form keeps a copy). Meanwhile the form says "This
  entry was deleted in another tab. Saving it adds it again." and counts as unsaved; the other tab's **Undo** stays
  on screen.

**For maintainers**

| File | What it does |
|---|---|
| `src/pages/tracker.njk` | the page: hero, the five views (Entries · Summary · Giveaways · Requests · Settings), the add / edit dialog, the privacy promises |
| `src/assets/js/expenses-core.js` | `window.GVX`, no DOM: the data model, the money math, summaries, subscriptions and the calendar file, the service report, CSV and backups. Its header comment is the **contract**: CSV columns are never renamed or reordered, a new one goes at the end (1.1.0 added `activity, activity_label, role, trips, no_miles, ref`), and files written before still import as they did |
| `src/assets/js/expenses-files.js` | `window.GVF` (Tracker 1.2.0), no DOM: the `.zip` backups (writing, and reading with a CRC check), `.xlsx` sheets, large `.json` backups read in slices |
| `src/assets/js/expenses.js` | the Alpine app `xpApp`: storage (localStorage + IndexedDB photos; the keys `gv-expenses:v1`, `…:undo` for photos a pending undo still needs, `…:unreadable-YYYY-MM-DD` for a stored copy that could not be read; the entry open in the edit form also protects its photo — an in-memory copy, stored again on save when missing, and spared by `dropPhotos` / `cleanPhotos`), the views, the form, print and downloads |
| `config/expenses.yml` | the defaults every visitor starts from (categories, who pays, payment methods, service activities, mileage rates, reminder days; `panels` only overrides or adds to the panels the Tracker works out itself). A built-in id is permanent: see its header |
| `src/_i18n/expenses.json`, `src/assets/css/areas/expenses.css` | the words (English and Spanish) and the look, print included |
| `tests/test_expenses_core.py`, `test_expenses_app.py`, `test_expenses_files.py`, `test_expenses_page.py` | the logic (a GVR's 2026 report rebuilt number for number — modeled on a real one, its names, references and distances invented: a public repository holds no one's booking numbers or home; `tests/fixtures/expenses/`: files written before 1.1.0 must import identically), the screen in Node.js, the page and its strings |

---

## 17. Credits and licenses

This project's **code** is free software under the **GNU GPL v3** (see [LICENSE](LICENSE)). The license does not
cover the content the site shows or keeps a copy of (stories' titles and teasers, quotes, covers and pictures,
documents, flyers, photos, event details): that belongs to its owners, as the [NOTICE](NOTICE) file says. It is
built entirely from open-source tools — thank you to their authors:

**Website**

| Tool | Used for | License |
|---|---|---|
| [Eleventy](https://www.11ty.dev/) | Builds the pages | MIT |
| [Tailwind CSS](https://tailwindcss.com/) | Design system / styles | MIT |
| [Alpine.js](https://alpinejs.dev/) | Small interactive parts (menus, filters, countdown) | MIT |
| [MiniSearch](https://lucaong.github.io/minisearch/) | Site search | MIT |
| [GLightbox](https://biati-digital.github.io/glightbox/) | Photo albums | MIT |
| [lite-youtube-embed](https://github.com/paulirish/lite-youtube-embed) | Fast, privacy-friendly video players | Apache-2.0 |
| [Lucide](https://lucide.dev/) | Icons | ISC |
| [Inter](https://rsms.me/inter/) and [Fraunces](https://github.com/undercasetype/Fraunces) via [Fontsource](https://fontsource.org/) | Fonts (self-hosted) | SIL OFL 1.1 |
| [markdown-it](https://github.com/markdown-it/markdown-it), [js-yaml](https://github.com/nodeca/js-yaml), [node-qrcode](https://github.com/soldair/node-qrcode) | Text formatting, settings, QR codes | MIT |

**Daily content sync**

| Tool | Used for | License |
|---|---|---|
| [Requests](https://requests.readthedocs.io/) | Fetching pages | Apache-2.0 |
| [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) | Reading web pages | MIT / BSD-3 |
| [Protego](https://github.com/scrapy/protego) | Obeying robots.txt and crawl delays | BSD-3 |
| [feedparser](https://github.com/kurtmckee/feedparser) | Podcast and YouTube feeds | BSD-2 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Complete YouTube video lists (no API key) | Unlicense |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) (PDFium) | PDF page counts and preview pictures | Apache-2.0 / BSD-3 |
| [Pillow](https://python-pillow.org/) | Small WebP thumbnails | MIT-CMU |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) + [SentencePiece](https://github.com/google/sentencepiece) | Offline English ⇄ Spanish translation | MIT / Apache-2.0 |
| [Argos Translate](https://github.com/argosopentech/argos-translate) models (trained on [OPUS](https://opus.nlpl.eu/) data) | The translation models | CC-BY 4.0 (models) |
| [python-dateutil](https://github.com/dateutil/dateutil), [PyYAML](https://pyyaml.org/), [icalendar](https://github.com/collective/icalendar) | Dates, settings, calendars | Apache-2.0/BSD, MIT, BSD-2 |

**Automation:** [GitHub Actions](https://docs.github.com/actions) (`actions/checkout`, `setup-python`,
`setup-node`, `cache`, `configure-pages`, `upload-pages-artifact`, `deploy-pages`, `upload-artifact`,
`download-artifact` — MIT), [lychee](https://github.com/lycheeverse/lychee) link checker (MIT / Apache-2.0; its
action pinned to a commit), Dependabot.

*AA Grapevine®, La Viña® and their content are the property of AA Grapevine, Inc. This committee
website links to the official sources and is not affiliated with or endorsed by AA Grapevine, Inc.
or Alcoholics Anonymous World Services, Inc.*
