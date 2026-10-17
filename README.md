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
  [When Grapevine announces new prices](#when-grapevine-announces-new-prices)). En **Suscribe a tu grupo base**,
  la tarjeta **Lo que costaría** (`/es/shop/#group-cost`) calcula lo que costaría una suscripción del grupo
  (revista, formato, duración y número de ejemplares, con los precios por cantidad) e imprime una **hoja
  informativa** de una página para la conciencia de grupo (en inglés, en español o bilingüe). Para quien quiere
  **ayudar económicamente**, la tarjeta *¿Quieres ayudar económicamente?* (en *Quiénes somos* y en la página «no
  encontrada», donde está también en inglés) dice que el comité no recibe dinero; esa tarjeta y *Lleva el Mensaje*
  (`/es/shop/#carry`) enlazan los dos programas oficiales: Lleva el Mensaje de La Viña y Carry the Message de
  Grapevine (`links:` → `lleva_el_mensaje`, `carry_the_message`). **Kit del mes**
  (`/es/monthly/`): todo lo de este mes — la reunión del comité, los eventos, las fechas límite para
  historias, las revistas del mes y el libro del mes —, un cartel para cada mes (descargar en PNG, compartir,
  imprimir), las 10 maneras de poner una edición a trabajar y cada mes también como mensaje para WhatsApp o
  correo. El **Resumen mensual** (`/es/digest/`) reúne todo lo nuevo del mes pasado (el correo mensual,
  sección [10 c](#c-monthly-e-mail-digest-keep-every-district-informed), es la misma edición). La **reunión
  abierta semanal de La Viña** (jueves, en español) está en `/es/meetings/#weekly-open`. La página
  **Reuniones** (`/es/meetings/`) también reúne las **reuniones de Grapevine** de los grupos de AA de nuestra
  Área y de las áreas cercanas (de las 8 listas de reuniones que usa la página del Grupo Rowlett). Arriba, la
  tarjeta *¿Eres nuevo en AA?* lleva a los sitios de AA para encontrar cualquier reunión de AA (aa.org, la app
  Meeting Guide y las oficinas de AA de nuestra Área, primero Alcohólicos Anónimos Dallas); la página «no
  encontrada» (404) muestra una versión breve, e Inicio, una línea. El **informe de GV/LV** para la reunión
  del distrito está en `/es/monthly/#report` (la antigua página *Distritos* ya no existe; su dirección lleva
  allí). Con **Para: Área**, el mismo lugar arma el **informe del coordinador para el Área** (una asamblea o
  una reunión del comité de área) para las fechas que se elijan: una parte en inglés y otra en español, en un
  solo documento, con el nombre de archivo para la carpeta `reports` del Drive (sección
  [4](#for-area--the-chairs-report-to-the-area)). El informe y los anteriores quedan solo en ese navegador: en una
  ventana privada duran hasta cerrarla, y en una pestaña de Safari, o en cualquier navegador de iPhone o iPad,
  pueden borrarse tras 7 días de uso sin tocar nada del sitio (la página lo avisa). Por eso conviene descargar el
  archivo de Word de cada informe al pasarlo a *Informes anteriores* y subirlo enseguida a la carpeta `reports`.
- **Fechas límite en tu calendario:** `https://neta65.github.io/aagrapevine/es/deadlines.ics` (en inglés,
  `/deadlines.ics`) tiene cada fecha límite abierta para historias de Grapevine y La Viña, con un aviso a las
  9 a. m. del día anterior; quien se suscribe una vez recibe los cambios solo (los pasos están en
  `/es/contribute/#deadlines-calendar`; cada fecha límite tiene además **Agregar a mi calendario**). Cada
  archivo «Agregar al calendario» del sitio trae ahora **un aviso**: 1 hora antes, o a las 9 a. m. del día
  anterior para lo que dura todo el día (Google Calendar no usa esos avisos). Detalles: [Calendar
  files](#calendar-files-story-deadlines-and-reminders).
- **Escuchar y Ver:** en `/es/listen/`, la tarjeta **Historias habladas de La Viña** va primero: las listas de
  videos en español de La Viña, que se abren en **Ver** ya filtradas. Cada episodio tiene su propio enlace para
  compartir (`/es/listen/?ep=…`), y cada video de **Ver** y cada historia de **Leer** y de **Escritores
  publicados** tiene un botón **Compartir** (envía el enlace oficial, nunca el texto ni el autor). El
  botón de velocidad tiene 0.75×, e **Inicio** recuerda dónde quedó cada episodio, igual que *Escuchar*.
  Detalles: [Listen and Watch](#listen-and-watch).
- **Novedades** (`/es/whats-new/`): a quien vuelve, la página le dice «Desde tu última visita (fecha): N
  novedades» y marca esas entradas con **Nuevo para ti** (se recuerda solo en ese dispositivo; no se envía
  nada).
- **Rincón del RLV / GVR** (`/es/gvr/`): la sección **Pásalo** (`#pass-it-on`) tiene un anuncio para cuando el
  grupo busca representante, un mensaje de bienvenida para el nuevo y consejos para entregar el puesto, con
  una media hoja y una hoja de entrega para imprimir y correos listos para avisar a la oficina (direcciones:
  `links:` → `gvr_office_email` y `rlv_office_email`). **¿Sabías que…?**, una pregunta al día de la pantalla
  de la mesa, aparece allí y en **Quiénes somos**; en el Rincón comparte una fila con los dos videos de Quiénes
  somos sobre las revistas (`about_videos`), y *RLV / GVR 101* y el *Registro* van lado a lado. Detalles: [The
  GVR / RLV corner](#the-gvr--rlv-corner-pass-it-on-and-the-question-of-the-day).
- **RLV / GVR 101** (`/es/orientation/`): seis lecciones breves para los nuevos RLV y GVR (el Panel 77 empieza
  en enero de 2027), cada una con preguntas de repaso; también como **diapositivas** para una reunión del
  distrito ("Presentar diapositivas") y como **hoja para imprimir** (una por lección). El texto está en
  `config/orientation.yml` (inglés y español en el mismo archivo). En sus **Presentaciones**, la reunión mensual
  del comité tiene en **Personalizar → Agenda y acta** el correo con la agenda, un recordatorio (en inglés y en
  español), el borrador del acta y **Empezar el mes siguiente**, hechos con los datos del coordinador; todo
  queda en su dispositivo y el sitio no envía nada (sección [The committee meeting's
  paperwork](#the-committee-meetings-paperwork-agenda--minutes)).
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
- **Grabadora de historias** (`/es/contribute/#record`, en **Comparte tu historia**): cada miembro graba su historia
  para Grapevine o La Viña con el micrófono del teléfono o de la computadora, escucha sus tomas, recorta el
  principio o el final y la envía en **MP3** (para el correo) o en **WAV** (para el formulario de la revista), con
  el mensaje para la revista ya escrito; también convierte una grabación ya hecha (por ejemplo, una nota de voz del
  iPhone, `.m4a`). Sigue las indicaciones de cada revista: la duración, qué decir al empezar y, para La Viña, la
  frase de permiso (los mismos datos que los pasos por teléfono). La lista **¿Sobre qué vas a hablar?**
  (opcional) ofrece los temas de las próximas ediciones y los temas sugeridos de cada revista (en la tarjeta de La
  Viña, cada tema sugerido tiene **Graba sobre este tema**; los de Grapevine son solo ideas); el tema va en el correo y, si se elige antes de
  descargar la toma, en el nombre del archivo (si se elige después de recargar la página, conviene descargar la
  toma otra vez).
  Al pie, **¿Tienes problemas? Revisa este dispositivo** arma un informe de lo que puede hacer ese teléfono o
  computadora (nunca nombres, temas ni sonido) para copiarlo o enviarlo al comité. **No se sube nada al
  sitio:** las tomas quedan solo en ese navegador, en ese dispositivo, hasta que la persona las borre (el sitio
  nunca las borra solo). Cada toma se guarda mientras se graba; si una no se pudo guardar, la página lo dice, lo
  vuelve a intentar y pregunta antes de salir por un enlace, también en iPhone. En una ventana privada duran
  hasta cerrarla; en una pestaña de Safari, Safari puede borrarlas tras 7 días de uso sin tocar nada del sitio, y la app de la pantalla de inicio
  guarda las suyas aparte: conviene guardar una copia de la toma elegida (en Archivos, o enviarla). En una
  computadora compartida, hay que borrarlas al terminar. Detalles: [The story
  recorder](#the-story-recorder-share-your-story).
- **Usar sin conexión:** menú **Aa** (arriba en cada página) → **Sin conexión y app** → **Guardar páginas
  clave** (Inicio, Reuniones, el kit del mes, Comparte tu historia, Tienda, Escritores publicados con el archivo
  de Texas, Accesibilidad y RLV / GVR 101),
  que luego se abren sin señal; las páginas que se abren también se guardan (las últimas 80). La grabadora de
  *Comparte tu historia* también graba sin señal (siempre en WAV; en MP3 si ya se usó una vez con conexión desde el
  último cambio del código del sitio). El **Ahorro de
  datos** apaga las imágenes, las vistas previas de video y el arte animado. Detalles:
  [Install the app, offline use and Data saver](#install-the-app-offline-use-and-data-saver).
- **Lectura y pantalla:** el mismo menú **Aa** agranda el texto (hasta 150%), da más espacio entre líneas y
  letras, pone alto contraste, detiene las animaciones, lee la página en voz alta (desde la parte que está en
  pantalla, con **velocidad de lectura** y **párrafo anterior / siguiente**) y activa los **subtítulos en los
  videos** del sitio; se guarda solo en ese dispositivo. La página **Accesibilidad** (`/es/accessibility/`,
  enlace al pie de cada página) explica esos ajustes, los subtítulos de los videos (con el botón **Activar
  subtítulos en todos los videos**), los videos en lengua de señas (ASL), el audio y **cómo unirse
  por teléfono** a nuestras reuniones de Zoom (números y código para teléfono: `config/site.yml` →
  `phone_access`).
- **Ajustes** (reunión del comité, Zoom, correo, eventos de cada mes como la mesa en CityWide Dallas o el
  taller mensual de La Viña por Zoom — `host: "lv"`: un evento de La Viña, no nuestro): archivo `config/site.yml`.
  **Corregir una traducción:** `data/translations/overrides.yml`.
- **Eventos sin volante** (talleres, asambleas): un archivo en `content/events`. Si todavía faltan
  detalles, `tentative: true` muestra "Detalles por confirmar"; el lugar en español va en `location_es`.
- **Buscadores** (Google, Bing): el sitio ya les da a cada página su título y una descripción breve, el **mapa del
  sitio** (`sitemap.xml`) con la fecha en que cambió el contenido de cada página, datos estructurados (quién es el
  comité, qué es cada página, los eventos con lugar y dirección) y, después de cada publicación, la lista de páginas
  que cambiaron (IndexNow: Bing y otros; Google no lo usa). **Pasos únicos del dueño:** enviar `sitemap.xml` en
  Google Search Console, importar el sitio en Bing Webmaster Tools y, como **NETA65**, crear el repositorio
  `NETA65/neta65.github.io` con `docs/user-site/robots.txt` (sección
  [12b](#12b-search-engines-google-bing), en inglés).
- **¿Funciona todo?** Página **/es/status/** del sitio (junto a *Cita del día*: a qué hora llegaron las
  citas de hoy), o la pestaña **Actions** en GitHub.
  **Actualizar ya:** GitHub → **Actions** → **Website update** → **Run workflow**. **Poner ya la cita de
  hoy:** **Actions** → **Morning check (new day by 5:30 AM)** → **Run workflow** (solo hace lo que falta:
  desde las 2 a. m., hora del Centro, si la revista ya publicó la cita, la trae; si no, lo dice; si otra
  actualización está en curso, primero la espera). Un cambio guardado en GitHub se publica en unos 5 minutos:
  antes se pasan las pruebas del código, y si fallan, el sitio sigue con la versión anterior.

Las instrucciones detalladas están abajo (en inglés); puede usar el traductor de su navegador. Las funciones
nuevas de octubre de 2026 tienen textos y datos que conviene leer una vez y confirmar: lista [Owner OK
needed](#owner-ok-needed-the-october-2026-features).

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
    - [Owner OK needed: the October 2026 features](#owner-ok-needed-the-october-2026-features) (wording and
      facts to read once and confirm)
2. [Your part: uploading to Google Drive](#2-your-part-uploading-to-google-drive)
3. [Changing settings (`config/site.yml`)](#3-changing-settings-configsiteyml)
4. [The monthly GV/LV report](#4-the-monthly-gvlv-report) (for the district meeting · for the Area)
5. [Fixing a translation](#5-fixing-a-translation)
6. [Bulletin posts and events without Drive (optional)](#6-bulletin-posts-and-events-without-drive-optional)
7. [Running the update right now](#7-running-the-update-right-now)
8. [Is everything working?](#8-is-everything-working)
9. [Instagram: how the site reads it (please read)](#9-instagram-how-the-site-reads-it-please-read)
10. [Optional upgrades](#10-optional-upgrades) (Google API key · Instagram token · monthly e-mail · the morning alarm)
11. [First-run checklist](#11-first-run-checklist) (and what to expect on day 1)
12. [Using your own address (custom domain)](#12-using-your-own-address-custom-domain)
    - [12b. Search engines (Google, Bing)](#12b-search-engines-google-bing) (what the site tells them · the
      owner's once-only steps: the sitemap, Bing, the root robots.txt)
13. [Replacing the old site](#13-replacing-the-old-site)
14. [Housekeeping](#14-housekeeping)
15. [Troubleshooting](#15-troubleshooting)
16. [How it works](#16-how-it-works) (reading & display · install, offline & Data saver · the Tracker · the story
    recorder · Listen & Watch · What's New · calendar files · New to AA? · the GVR / RLV corner · the committee
    meeting's paperwork)
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
| **YouTube** (@AAGrapevine — Grapevine *and* La Viña videos) | Every video, playable on the site | **Watch** (La Viña's Spanish playlists also show on **Listen** as *Spoken stories from La Viña* / *Historias habladas de La Viña* — [Listen and Watch](#listen-and-watch)) |
| **Instagram** (@alcoholicsanonymous_gv, @alcoholicosanonimos_lv) | Newest posts — see [section 9](#9-instagram-how-the-site-reads-it-please-read) | **Instagram** |
| **Committee Google Drive** | Reports, notes, slides, workshops, forms, photo albums; dated flyers → events; docs in *bulletin* → bulletin posts | **Portfolio · Photos · Events · Bulletin** |
| **Editorial calendar** (Grapevine), **yearly themes** (La Viña: the "Temas de LV" document on aalavina.org/recursos) and suggested topics (both: La Viña's *temas sugeridos*; the departments and "always in need of" topics Grapevine's /contribute page names) | Upcoming themes and story deadlines of both magazines, and the topics they take any time | **Contribute** (also the monthly toolkit, the district report, Home and the workshop presentations; the story recorder's topic list; the [story deadlines calendar](#calendar-files-story-deadlines-and-reminders), `/deadlines.ics`) |
| **Grapevine Weekly Open meeting** (web page) | Current day, time and Zoom details | **Meetings** |
| **La Viña's weekly open meeting** (from the settings, `lavina_weekly_open:` — an official La Viña flyer) | Thursdays in Spanish, first date, Zoom details | **Meetings** (one line on Home · Listen · Watch · monthly posters) |
| **Official stores** (aagrapevine.org / aalavina.org store pages) | **Book of the Month** (title, cover, percent, sale price, dates) and **subscription prices** per region (U.S. · Canada · International; print / digital / complete); once a week the **specialty items** — greeting cards, pocket planner, wall calendar and, in season, the holiday cards (picture, price, pack size, volume price, a short description) | **Shop** (a short teaser on Home, the monthly posters and the monthly toolkit) |
| **Daily quote** (the home pages of aagrapevine.org and aalavina.org) | Grapevine's *Daily Quote* and La Viña's *Cita Diaria*: the quote as published (never translated), who said it, the book it comes from, the official e-mail sign-up — under them the publishers' permission credits ("Reprinted with permission of A.A. World Services, Inc." · "Copyright © The AA Grapevine, Inc. Reprinted with permission. All rights reserved.") | **Home** |
| **Record your story by phone** (aagrapevine.org/audio-portal, aalavina.org/graba-tu-historia) | Grapevine's *Audio Project* and La Viña's *Graba tu historia*: the phone number, the keys to press, the length, the e-mail address for recordings, Grapevine's story playlists | **Share your story** (`/contribute/#record`: the steps by phone, and above them the [story recorder](#the-story-recorder-share-your-story), with the same lengths, addresses and La Viña's permission sentence as the steps; one link on Listen · Watch) |
| **Committee meeting** (from the settings) | Next dates, countdown, "add to calendar" | **Meetings · Events** |
| **Local meeting lists** (the 8 intergroup / central office lists the Rowlett Group's meeting page uses — in or at our Area: Dallas Intergroup, Fort Worth Central Office, Tyler Central Service Office, the Spanish-speaking Dallas office, District 71 Abilene; nearby: Arkansas Central Office, OKC Intergroup, Northwest Texas Area 66) | Every meeting with the Grapevine ("GR") type: day, time, place, directions, link to the office's page. A meeting in two lists is shown once; our Area first (by county), nearby areas after | **Meetings** (one line on Home; each meeting is in the site search) |
| **Monthly events** (from the settings: our booth at CityWide Dallas, La Viña's monthly workshop on Zoom) | The next dates, "add to calendar", the flyer from our Drive; a date La Viña's own calendar lists too is shown once | **Events · Home · calendar feed · monthly toolkit** (and, once it has taken place, the monthly digest) |
| **Other calendars** (optional, e.g. the NETA 65 workshop calendar on neta65.org) | Their events, each shown **once** even when it is also in `content/events` (yours wins). *neta65.org currently blocks robots — see [the NETA 65 workshop calendar](#the-neta-65-workshop-calendar)* | **Events** |
| **Translation** | Every title, teaser and bulletin post in both languages | Everywhere |

The site also offers, automatically: a **What's New** page (the newest items from every source; a visitor who
comes back sees *New since your last visit (date): N updates* above the timeline, with a *New for you* label on
those entries, plus *Mark all as read* and *Forget my last visit* — remembered on that device only, nothing is
sent anywhere: [What's New](#whats-new-new-since-your-last-visit)),
an **RSS feed**, **calendar files** your phone can subscribe to (the events, `/events.ics`, and the story
deadlines, `/deadlines.ics`: [Calendar files](#calendar-files-story-deadlines-and-reminders)), **QR posters**
for districts (with the committee meeting on them),
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
- **What it would cost** (`/shop/#group-cost`, in *Subscribe your home group*): for a GVR or RLV who wants to
  propose a group subscription at the business meeting. Pick the magazine, the format (Print, Digital,
  Complete — only those the magazine sells), the term and the number of copies (1 to 999): the card shows the
  total for the term, about how much that is a month, and the price per copy — the volume price when the store
  lists one for that many copies ("$35.50 a copy (volume price for 2–19 copies)"). While AA Grapevine's notice of a
  price change is up, it also says what the plan will cost from that day, or that the notice names no new price
  for this plan; on that day it switches by itself (midnight Central). **See this plan on aagrapevine.org /
  aalavina.org** opens the plan in the official store, and **Print an information sheet** (English, Español or
  Bilingual) prints one page for the group conscience: the plan, copies, price per copy, total, how the group
  orders, "The group decides through its group conscience, and pays with its own Seventh Tradition
  contributions", and blank lines for the group's decision and the date ("Save as PDF" in the print window makes
  a file to send). Each "Group & volume pricing" box links to it (**What it would cost your group**). Every number
  comes from the daily store read and `price_changes:` (U.S. prices only); nothing is typed into the page and
  nothing is saved or sent. Nothing for the owner to do.
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
- **Carry the Message** (`/shop/#carry`, and since October 2026 a card on About and the 404 page): for anyone who
  wants to help financially. The card, *Want to help financially?*, says plainly that our committee collects no
  money, and how the official program works (as its own pages say): a Carry the Message gift certificate, bought in
  the official store, which AA Grapevine or La Viña turns into a subscription for an alcoholic in need — a purchase,
  not a donation, with the buyer's name not linked to it. Every place shows **both** programs — Grapevine's *Carry the
  Message* (in English) and La Viña's *Lleva el Mensaje* (in Spanish), the page language's first, the other one
  marked "En español" / "In English" — from `links:` → `carry_the_message` and `lleva_el_mensaje`. On About it
  closes *Our committee* (`#ctm`); on the 404 page it is a row of its own under the nine popular pages, which stay
  three even rows of three (where only two fit, the ninth takes the whole row). Like the rest of the 404 page it is
  bilingual — GitHub Pages shows that one page for every missing address, Spanish ones too — so the card's words
  are there in the other language as well, under a line (beside them on the widest screens), and on a broken
  `/es/…` address La Viña's button comes first. Nothing for the owner to do.
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
  committee meeting, events and story deadlines, each with one reminder
  ([Calendar files](#calendar-files-story-deadlines-and-reminders)).
  `/monthly/` shows each month as a small poster (the full poster,
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
  corner and the Monthly toolkit link to it. Its **Presentations** are the committee's four web slide decks
  ([how-to/presentations.md](how-to/presentations.md)); the monthly committee meeting's deck also makes the
  chair's paperwork — the agenda e-mail, a reminder, the draft minutes and **Start next month** (Customize →
  **Agenda & minutes**: [The committee meeting's paperwork](#the-committee-meetings-paperwork-agenda--minutes)).
- **Meetings** (`/meetings/`, renamed from *Committee meeting*; the old `/meeting/` address forwards there,
  `#weekly-open` included): a *New to AA?* card at the top (`#new-to-aa`) with AA's own places to find **any** AA
  meeting (aa.org's *Find AA near you*, *Is AA for you?*, the *Meeting Guide app*, and the AA offices in our
  Area, the Spanish-speaking office first on `/es/`) — the 404 page shows a short version in both languages,
  and Home has one line to it ([New to AA?](#new-to-aa-meetings-the-404-page-home)) —, the committee meeting
  (`#committee-meeting`), the **Grapevine meetings** of local
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
  `booth` folder. Full guide: [how-to/booth.md](how-to/booth.md). Its question rows also give the website's
  **question of the day**, *Did you know?* / *¿Sabías que…?*, on About (under the history timeline) and on the
  GVR / RLV corner ([below](#the-gvr--rlv-corner-pass-it-on-and-the-question-of-the-day)).
- **Share your story** (`/contribute/`): the magazines' upcoming themes and story deadlines and their suggested topics
  (Grapevine's departments, "In every issue", and what it is "Always needed": Steps 4–12, every Tradition; La Viña's
  *temas sugeridos*) — side by side, the two cards show as many deadlines and topics as make them end together at
  each width (`eleventy/filters/read.js` `deadlineLayout`) —, how to send a story,
  and the [story recorder](#the-story-recorder-share-your-story) (with its optional topic list, *What will you talk
  about?*, and *Having trouble? Check this device*). Each deadline has **Add to my calendar**, and under the
  deadline cards **Get the deadlines in your calendar** (`#deadlines-calendar`) sets up the deadlines calendar
  ([Calendar files](#calendar-files-story-deadlines-and-reminders)). In *What you can send* → **Photos & art**, a
  folded note, **Your meeting place in “If Walls Could Talk”**, says how to send a photo of the group's meeting
  place for Grapevine's section of that name (no people or faces, no names on boards or anniversary lists; the
  group's name and city), with Grapevine's guidelines and share page and La Viña's share page (the existing
  `links:` `gv_guidelines`, `gv_share_story`, `lv_share_story`). Words and links only: the site never sees the photo.
- **GVR / RLV corner** (`/gvr/`): **Pass it on** (`#pass-it-on`) — words to find, welcome and hand over a rep,
  two printouts and ready-made e-mails to the offices — and the question of the day, beside the About page's two
  videos about the magazines; *GVR / RLV 101* and the *Tracker* side by side under *What does a GVR or RLV do?*
  ([The GVR / RLV corner](#the-gvr--rlv-corner-pass-it-on-and-the-question-of-the-day)).
- **Listen** and **Watch**: La Viña's spoken stories on Listen (first on `/es/listen/`), Watch's filters kept in
  its address, a link and a **Share** button for one episode, video or story, a 0.75× speed, and Home and Listen
  sharing the place in an episode ([Listen and Watch](#listen-and-watch)).

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

### Owner OK needed: the October 2026 features

The features added in mid-October 2026 (described above and in [section 16](#16-how-it-works)) use words written
by hand in both languages (not machine-translated), and a few facts could not be confirmed from here. Please read
these once — in English and in Spanish — and tell whoever helps with the website what should change. Nothing
breaks while you decide.

- **Listen — La Viña's spoken stories:** is "la revista en español de AA Grapevine" how you want La Viña
  described? Keep the general "La Viña" playlist in the card (it also holds a few promotional and service videos),
  or leave it out? Are "From your link" / "De tu enlace" and the share line "— Grapevine, October 2026" right?
- **The story recorder's topic list:** look at Grapevine's Audio Project page (aagrapevine.org/audio-portal) once:
  can a recording be tied to an issue's theme? (Today Grapevine's themes are shown "only as ideas".) Should La
  Viña's dated issue themes stay in the list, or only its suggested topics?
- **Grapevine's suggested topics (Share your story › Upcoming themes & deadlines):** read the eight tiles in
  Grapevine's card, in English and Spanish — the six departments its /contribute page names (Emotional Sobriety,
  Sponsorship, Newcomers, Youth Enjoying Sobriety, Old-Timers, Home Group: "In every issue" / "En cada edición") and
  "Steps 4–12" and "Every Tradition" ("Always needed" / "Siempre se necesitan"). Their Spanish is hand-written in
  `data/translations/overrides.yml` (Sobriedad emocional, Apadrinamiento, Recién llegados, Jóvenes que disfrutan de la
  sobriedad, Veteranos, Grupo base, Pasos 4 a 12, Cada una de las Tradiciones): is "Veteranos" right for Old-Timers
  here, and should "Emotional Sobriety" show as a department while it is also June 2027's theme (today: both, the
  tile marked "In every issue")?
- **"If Walls Could Talk":** confirm the advice ("no names on boards or anniversary lists", "no street address
  needed"), that photos go to Grapevine's share page (aagrapevine.org/share) and La Viña's "Comparte" page, and
  that La Viña also welcomes photos of meeting places.
- **The recorder's device report:** is grapevine@neta65.org (`contact_email`) the right address, and is it fine
  that the report holds the browser's own description (on Android it can name the phone model)? A Spanish
  speaker's glance at the new recorder words, please.
- **Story deadlines calendar and reminders:** read the card "Get the deadlines in your calendar" / "Las fechas
  límite en tu calendario" and the reminder line under each *Add to calendar*. Is **9 AM the day before** the
  right time for a deadline? (Another time is a maintainer's job, not a setting: `icsAlarm` in
  `eleventy/central-time.js` gives every all-day event the same reminder, assemblies included, so a deadline-only
  time needs a new argument from its callers — `committee.js` `buildIcs` and `app.js` `GV.icsText`; the words
  "9 AM the day before" are in `read.dlcal.text`, `read.dlcal.desc` and `committee.cal.reminder_day`, English and
  Spanish; and `tests/test_r12_u3_calendar.py` expects `TRIGGER:-PT15H` — *Website update*'s tests stop the
  publish until it is changed too — as does the Code check's browser check
  `tests/browser/test_r12_u3_calendar_browser.py`.) Keep `/events.ics` without reminders? On a phone set to
  Spanish, check that iPhone's switch is called "Eliminar alertas".
- **Aa panel:** the words for *Video captions* and *Reading speed* (Slower / Normal / Faster = 0.8 / 1 / 1.2 ×
  the voice's own speed; if "Slower" is not slow enough, 0.7 means changing `RATES` in `src/assets/js/app.js` and
  the tests that expect 0.8: `tests/test_r12_u4_aa.py` checks that line word for word — *Website update*'s tests
  stop the publish until it is changed too — and the Code check's browser check
  `tests/browser/test_r12_u4_aa_browser.py` checks the rate), and how the Accessibility page's settings cards look
  now.
- **Pass it on (GVR / RLV corner):** La Viña's address for rep-list changes — the draft is
  `preguntas@aagrapevine.org`; if La Viña names its own, put it in `config/site.yml` → `links:` →
  `rlv_office_email`. Read the announcement, the welcome message and the two *Tell the office* e-mails (do the
  offices want other details?), and say if the handover sheet needs a field added or dropped. The question of the
  day now links a booth row's `source_url` when it is on an AA site or this site (two rows today link pages of
  this site) — OK?
- **New to AA?:** all the card's words; "¿Eres nuevo en AA?" (masculine — "¿Llegas por primera vez a AA?" is an
  option); "tú" (the site's voice) where aa.org says "usted"; whether District 71 AA (a district site) stays in
  the office list; whether the card stays first on Meetings (on a phone the committee meeting now starts about
  one screen lower); and whether About's "Find an AA meeting" should link aa.org's *Find AA* page.
- **What it would cost (Shop):** the sheet's Tradition line; that a group can order a multi-copy subscription
  online **and** with the order form; "The store will list the new volume prices"; that AA Grapevine's letter
  names no new price for the 2- and 3-year, Complete and 1-month plans; the Spanish labels ("Lo que costaría",
  "Duración", "Hoja informativa"); U.S. prices only.
- **What's New:** the words ("New since your last visit", "New for you", "Mark all as read", "Forget my last
  visit"), the 30-minute "visit" rule, and the green label.
- **Agenda & minutes (committee meeting deck):** the reminder's Spanish paragraph ("La reunión es en inglés" —
  offer interpretation?); what **Start next month** clears and keeps; the agenda's and the minutes' wording
  (opening, closing, "DRAFT, for the committee's approval…"); the Spanish names of the controls. The texts are in
  `config/presentations/committee-meeting.yml` under `paperwork:`.
- **Report to the Area:** the title and the blanks' words, the names of the Area meetings ("Assembly", "Area
  committee meeting" — or "Area Chairs' Meeting"?), the file name (`… Grapevine La Vina Area … Report`), whether
  the printed report should carry the Zoom ID and passcode, and which events count as "ours".
- **On a real phone** (with the [story recorder's real-device test](#the-story-recorder-share-your-story)):
  start an episode on Home, stop it, and open Listen ("Continue listening"); start Read aloud half-way down a page
  and try Next / Previous and Slower; turn Video captions on and play a video on Watch; add a deadline to Google
  Calendar, Apple Calendar and Outlook and see which ones keep the reminder; Copy and **Open in my e-mail** from
  *Agenda & minutes* with the e-mail app you use, and print the draft minutes and the Shop's information sheet
  (Bilingual).

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
| Contact e-mail (also where the story recorder's *Email it to the committee* device report is addressed) | `site:` → `contact_email` and `meeting:` → `chair_email` |
| The offices' addresses for *Tell the office* (GVR / RLV corner → Pass it on, and its handover sheet) | `links:` → `gvr_office_email`, `rlv_office_email` (any e-mail address; La Viña's is a draft — see [the GVR / RLV corner](#the-gvr--rlv-corner-pass-it-on-and-the-question-of-the-day)) |
| The *New to AA?* card's aa.org links (Meetings, the 404 page) | `links:` → `aa_find`, `aa_is_aa_for_you`, `aa_meeting_guide` (each with its `_es` twin for `/es/`); its AA offices are the `meetings:` → `feeds` with `in_area: true` |
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
  organizer of a date held at a place. An online-only series, like La Viña's Zoom workshop, is not given to
  search engines at all ([Search engines](#12b-search-engines-google-bing)). Such a series keeps no reserved
  place in the home page's **Upcoming events** row: its next date
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

### For: Area — the chair's report to the Area

The report builder starts with a switch, **For: District meeting | Area** (Spanish: **Para: Reunión de distrito |
Área**). *District meeting* is the GVR / RLV report above, unchanged. **Area** builds the chair's report to an
Area assembly or an Area committee meeting:

- **Area meeting:** *Assembly* or *Area committee meeting*. It fills in the title ("NETA 65 Grapevine / La Viña
  Committee — report to the Area 65 Assembly").
- **From / To (the day of the meeting):** the dates the report covers. The page suggests them: from the day after
  the last Area assembly it knows of (within about 6½ months), else from 3 months back, up to today. Until you
  pick the *To* yourself, it moves to today each time you come back (a line under the dates says so).
- **Your name** (first name and last initial) goes into "Prepared by", with the chair's title from
  `config/site.yml` (`meeting:` → `chair_title` / `chair_title_es`).

The report is **one document: the English part, then the Spanish part**. The language switch, labelled **Part to
edit**, picks the part you are editing; copy, WhatsApp, e-mail, print and the Word file always give both parts (in
print and in Word the Spanish part starts on a new page). Its sections can be switched off, moved and edited, and
you can add your own, as in the district report:

1. **Title and your name**, with the period ("Period: September 21, 2026 – November 20, 2026").
2. **Recent activities:** the committee's own events of the period (workshops, dated Drive flyers, the monthly
   CityWide booth on one line with its dates), each with blanks to fill in — "about [N] attended", "[N] stories
   written", "[N] stories recorded", "about [N] visitors" — and the committee meetings held ("… — about [N]
   members each time"). Counts only: never a list of who came.
3. **Next activities:** our events after the period, until the next Area assembly (the assembly itself is
   listed), and the committee meetings until then.
4. **Area 65 writers published:** stories by Area 65 members in the issues of the period, as the magazines
   printed the names. An issue counts in the period its first day is in, so two reports never list the same story.
5. **An invitation to the districts** to ask for a workshop or a literature table, with the committee's e-mail.
6. **Next committee meeting:** the first one after the period, with the Zoom meeting ID and passcode (the same
   ones `/meetings/` shows).
7. **Other news and requests:** empty, and left out until you write in it.

**One working report, and the earlier ones.** Everything stays on the chair's device; nothing is sent anywhere.
The page keeps **one working report**, both parts. Changing *From* or *To* changes only the dates: the sections
you edited keep your words, and the others show the site's text for the new dates. Nothing is moved, copied or
dropped when the dates change.

- **Next report: from … to today.** Once a *To* you picked is before today (the meeting is over), this button
  appears under the dates. It asks first. Then it files the working report under **Earlier reports** and starts
  the next one: from the day after the last *To*, up to today, with the site's text. The new report offers
  **Start from your … report?** only when the filed report has something of yours to carry over: your own
  sections, their order, the sections you left out, titles you changed, or the *invitation* or *Other news* text.
  Those are what it brings back, in both parts; the counts and the other sections' words never carry over. (A
  report where you only changed sections made from the site's data, such as the counts in *Recent activities*,
  gets no offer.) The offer goes once you edit that part.
- **Earlier reports** (folded under the dates) keeps the last 12, newest first. Each one can be downloaded as a
  Word file or printed as it was filed: its dates, your words, the site's text of the day it was filed, your name
  and the Area meeting. It can't be edited: to change one, download it and edit the Word file. **Delete** removes
  one (it asks first). When 12 are kept, *Next report* says which one it will remove, so you can download it
  first.
- **Start this part over** (under the sections; the district report calls it *Reset all to latest data*) asks
  first, then clears your changes to the part you are editing only. The other part and the dates stay as they
  are.

If the browser can't save (site data blocked for the site, a full device), the page says so and your words stay
on screen: copy or download the report before you leave. Nothing is filed under *Earlier reports* then. A
**private window** (Incognito, InPrivate) is different: it saves, files under *Earlier reports* and shows no
warning, but it keeps the report and its earlier ones only until the window is closed. Download the Word file
before you close it.

**Keep a copy of each filed report outside the browser.** The device keeps the report only while the browser keeps
the site's data. Clearing the site's data removes it. **Safari** may remove it after 7 days of using Safari
without tapping or clicking anything on this site. That applies to a Safari tab on an iPhone, an iPad or a Mac, and
to every other browser on an iPhone or iPad, and there the page says so, under *Earlier reports* and in the note at
the bottom of *Your details*: "Safari may remove this report and your earlier ones after 7 days of using Safari
without tapping anything on this site, so download the Word file of each report when you file it." ("This browser
may remove …" in another browser on an iPhone or iPad; "… without clicking …" on a Mac.) The site added to the Home
Screen counts its own days of use, so it is exempt from that rule and has no such line, but it keeps its own
reports, apart from Safari's: a report made in one doesn't show in the other. Once something is saved or filed,
the page also asks the browser to keep the site's data (`navigator.storage.persist()`, as the Tracker and the story
recorder do). Firefox may ask you to allow it; Chrome and Edge decide on their own; the page works the same either
way. So each time you press *Next report*, download that report's Word file and put it in the committee's Drive
`reports` folder: that copy is the one that lasts.

**The file name for Drive.** Word, text and "Save as PDF" use a dated name like the committee's other reports,
`2026-11-20 Grapevine La Vina Area Assembly Report.docx` (or "… Area Committee Meeting Report"; the date is the
period's *To* day), and the page says so ("For the committee's Drive (the “reports” folder), the file is named
…"). Upload each finished report to the panel's `reports` folder as soon as it is filed. It is the copy that
lasts (see above), and it shows on `/portfolio/`.

**How far back.** The page offers dates from about 13 months back to 13 months ahead ("Pick dates between … and
…" otherwise). Committee meetings come from the meeting rule (skipped dates left out) and the writers from the
archive, so they are complete for any of those periods. Our events come from what the site keeps: the newest 12 past
one-off events and the last 90 days of the monthly booth. When the *From* day is before that, the page says "The
site keeps only our recent past events: check for any before {date} and add them by hand." For the usual 3 months
between two Area meetings this note does not show. The Area report needs JavaScript. Nothing to set up: it uses
`meeting:` in `config/site.yml` and the site's own data.

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
  assemblies, an old price-change block — each with the file to edit), the **Sitemap dates** line (how many
  pages got a new date because their content changed) and, after publishing, the **IndexNow** line (those pages
  sent to Bing and the other IndexNow engines — both explained in [Search engines](#12b-search-engines-google-bing))
  and, for a source that no run has even tried for 3 days, **NOT CHECKED** ("not checked for N days").
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
- [ ] *(Recommended)* [Search engines](#12b-search-engines-google-bing), once: submit the sitemap in Google Search
  Console (A), import the site into Bing Webmaster Tools (B) and, signed in as **NETA65**, create the
  `neta65.github.io` repository with `docs/user-site/robots.txt` (C).

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

**Search engines after the move** ([12b](#12b-search-engines-google-bing)): with an address of its own, the site's
own `robots.txt` (`src/robots.njk`) is the one search engines read, and the weekly link check stops reading
neta65.github.io/robots.txt. In the `neta65.github.io` repository (12b, step C), change the address in
`index.html` (or delete that file) and in the `Sitemap:` line of `robots.txt` to the new one — and the same in
`docs/user-site/` here (a test compares them with `site.url`). Add the new address as a new property in Google
Search Console and Bing Webmaster Tools and submit its sitemap there (12b, steps A and B). The custom domain goes
in **this** repository's settings only — never in the `neta65.github.io` repository's, which would move every
NETA65 site.

---

## 12b. Search engines (Google, Bing)

Search engines can already find the site: nothing keeps them out, and every page tells them what it is. This
section says what the site does by itself, the owner's once-only steps that make sure Google and Bing know every
page (A to C, about 30 minutes in all), one optional choice (D), and what not to expect.

### What the site already tells search engines

Nothing to do here: every update writes all of it, in both languages.

- **A title and a short description for every page** — the words a search result shows under the link. The
  descriptions are plain facts of at most 160 characters (what Google and Bing show whole), never promotional
  words: attraction, not promotion. Every page also names its own address and its twin in the other language,
  so a Spanish search finds the Spanish page.
- **The sitemap** — <https://neta65.github.io/aagrapevine/sitemap.xml>, the list of the 88 pages meant to be
  found (both languages). Each one carries the **date its content last changed**, not the day of the update: the
  site is rebuilt several times a day, and a date that always moves teaches search engines to ignore it. Each
  Website update compares what every page says with what it said in the last publish (GitHub keeps that list for
  the next run), and only a page whose words, links or pictures changed gets a new date. Its run summary says how
  many: *Sitemap dates: 3 of 88 page(s) got this build's date*. The first publish after this was added dated
  every page once. Should the last publish's list ever be unreadable, that run gives no page a date rather than a
  wrong one (*no page got a date this time*), and the next run compares again. A yellow warning *"N of 88 pages
  changed although the code did not"* that comes back on ordinary days means a text on some page changes by
  itself with the calendar (a countdown, "today") and needs a mark in the code — tell whoever helps with the
  website ([how-to/pages-and-code.md → 6.6](how-to/pages-and-code.md#66-what-search-engines-read)).
- **Structured data** (schema.org): a small block on every page that tells machines who runs the site (the
  committee, part of NETA 65, with its page on neta65.org — never a person's name), what kind of page it is,
  where it sits on the site (Home → GVR / RLV 101 → a session) and, on *Share your story* (`/contribute/`), the
  questions and answers the page shows. On `/events/`, every upcoming **event held at a place**, with its address
  (best written `Venue, street, city, TX ZIP` in a `content/events` file —
  [how-to/flyers-and-events.md](how-to/flyers-and-events.md)); a place with no city, state or ZIP code (a
  venue's name alone) is not enough. Online-only events (the committee meeting, La Viña's Zoom workshop) are not
  given to search engines: Google lists only events people can go to. Their cards, calendar files and share pages
  are the same as before. How to join online (a meeting ID, a passcode, a Zoom link) stays on the page for people
  but out of this machine-readable copy: it would only help those who look for meetings to disrupt.
- **Share previews** — the picture, title and description WhatsApp, Facebook, X, iMessage … show when someone
  shares a page.
- **The site's search in the browser** — a browser can add the site's search as one of its search engines
  ("Add search engine"), in English or in Spanish.
- **Pages kept out of search results** — the *Update status* page (`/status/`: the build's own figures), the
  "page not found" page, the event share pages and the old addresses that forward to new ones.
- **IndexNow, after each publish** — Website update tells Bing, Yandex and the other IndexNow search engines
  exactly which pages changed (only those — every page only the very first time; at most 2,000 a publish), so
  they look at them again soon. The summary of the run's publish part says *IndexNow: 3 changed page(s) sent … —
  HTTP 200: received* (*could not be sent* when IndexNow did not answer). **Google does not use
  IndexNow**: it reads the sitemap and its dates. The key is `config/site.yml` → `search_engines:` →
  `indexnow_key`; it is public on purpose (the site publishes it so the engines can check the list comes from
  this site), and `""` turns IndexNow off. A **403** answer on the very first send is normal; the other answers
  are explained in
  [how-to/automation-and-troubleshooting.md → 14](how-to/automation-and-troubleshooting.md#14-troubleshooting).
- **A check in every Code check** — every page in the sitemap must have a title, a description and its own
  address, and no two pages of one language the same title (an `[seo]` build warning otherwise: for whoever
  changes the code).

To see what Google reads on a page, paste its address into Google's Rich Results Test,
<https://search.google.com/test/rich-results> (for `/events/`: the events held at a place, each with its address).

### The owner's once-only steps

**A. Google Search Console: submit the sitemap (5 minutes)** — with the committee's Google account that verified
the site:

1. Open <https://search.google.com/search-console> and choose the property
   **https://neta65.github.io/aagrapevine/** in the list at the top left. If it says the property is not verified,
   press **Verify** with the *HTML file* method: the site already publishes Google's file
   (`googlef96fc15466439295.html`, from `src/pages/google-site-verification.11ty.js` — never delete or change it).
2. Left menu → **Indexing → Sitemaps**. Under *Add a new sitemap*, type `sitemap.xml` after the address that is
   already there → **Submit**.
3. A few minutes to a day later its row says **Success**, with about 88 pages found. Over the next weeks the
   **Pages** report shows which pages Google took into its index.

**B. Bing Webmaster Tools: import the site from Google (5 minutes)** — Bing's results also reach DuckDuckGo and
Microsoft Copilot:

1. Open <https://www.bing.com/webmasters> and sign in (with a Microsoft account, or the Google account of step A).
2. Choose **Import your sites from GSC** (Google Search Console) → **Import** → sign in with the Google account
   of step A → **Allow**.
3. Tick **https://neta65.github.io/aagrapevine/** → **Import**. Bing trusts Google's check and brings the sitemap
   along.
4. Left menu → **Sitemaps**: `https://neta65.github.io/aagrapevine/sitemap.xml` should be listed. If it is not:
   **Submit sitemap**, paste that address → **Submit**.

Only if the import refuses the site: choose **Add your site manually** instead, type
`https://neta65.github.io/aagrapevine/` → **Add** → method **HTML Meta Tag**. Bing shows a line like
`<meta name="msvalidate.01" content="1A2B3C…" />`: copy only the code between the quotes after `content=`. On
GitHub open `config/site.yml` → pencil icon → paste it between the quotes of `bing_verification: ""` (under
`search_engines:`) → **Commit changes**. About 5 minutes later the home page carries the code (check the
**Actions** tab: the **Website update** run is green); back in Bing press **Verify**, then do step 4. Leave the
code there while Bing Webmaster Tools is used. Yandex Webmaster works the same way with `yandex_verification`
(only if the committee wants it).

**C. The root robots.txt (15 minutes, signed in to GitHub as NETA65 — recommended)**

`robots.txt` is the file that tells search engines' robots what they may visit. They read it **only at the very
top of an address**. This site lives in a folder of `neta65.github.io`, so the file they read is
**<https://neta65.github.io/robots.txt>** — never the site's own `/aagrapevine/robots.txt`. Until step C is done
that address answers "not found", which search engines take as "everything is open": the site is visited anyway,
but nothing there tells them where the sitemap is. Only a repository named **neta65.github.io** in the NETA65
account can publish that file, and only NETA65 can create it. Its files are ready in this repository, in
[`docs/user-site/`](docs/user-site/).

1. github.com → **+** (top right) → **New repository**. *Owner:* **NETA65**. *Repository name:*
   **`neta65.github.io`** (exactly that, all lowercase). **Public** (GitHub Pages is free only for public
   repositories). Leave *Add a README file* off, no .gitignore, no license → **Create repository**.
2. On the new, empty repository click the link **creating a new file**. Name: `robots.txt`. Content: open
   [`docs/user-site/robots.txt`](docs/user-site/robots.txt) here → **Raw** → select all → copy → paste. **Commit
   changes…** → *Commit directly to the main branch* → **Commit changes**.
3. **Add file → Create new file**: name `.nojekyll` (it starts with a dot), leave it **empty** → commit. It tells
   GitHub to publish the files exactly as they are.
4. *(Optional.)* **Add file → Create new file**: `index.html`, content from
   [`docs/user-site/index.html`](docs/user-site/index.html) (**Raw** → copy → paste) → commit. The bare address
   https://neta65.github.io/ then opens this site instead of GitHub's "Site not found". Skip it if that address
   should stay empty: robots.txt works either way.
5. **Settings → Pages**: under *Build and deployment*, *Source* **Deploy from a branch**, branch **main**, folder
   **/ (root)** → **Save** (usually already set for a repository with this name).
6. 1–10 minutes later open <https://neta65.github.io/robots.txt>: it shows the text. Check that
   <https://neta65.github.io/aagrapevine/>, <https://neta65.github.io/GV_Booth/> and
   <https://neta65.github.io/Archives_Booth/> still open.

The **Weekly link check** (Sundays, or **Actions → Weekly link check → Run workflow**) reads that file every week.
Its run summary has a part *The root robots.txt*: **Not set up yet** before step C (not a problem), then **OK:
Googlebot and Bingbot may crawl … and it names the sitemap.** If the file ever keeps Google or Bing out, loses its
`Sitemap:` line, redirects or does not answer, the check opens (or updates) the issue **"Broken links found by the
weekly check"** with what to fix; copying `docs/user-site/robots.txt` over it again puts it right (then redo step
D if the committee chose it). Should the check itself fail to run, the issue says so too (*The check itself could
not run*), rather than closing as if all were well.

**Rules for the neta65.github.io repository.** It sits above every NETA65 site (/aagrapevine/, /GV_Booth/,
/Archives_Booth/ …), so a slip there touches all of them:

- **Never set a Custom domain** in its *Settings → Pages*, and never add a `CNAME` file: GitHub would move every
  NETA65 site to that domain. (A custom domain for this site alone is set in this repository —
  [section 12](#12-using-your-own-address-custom-domain).)
- **Never create folders named after the NETA65 repositories** (`aagrapevine`, `GV_Booth`, `Archives_Booth`,
  `aatapestry`, `RowlettAA`): GitHub does not say which of the two would win.
- **Never add a `Disallow: /` line** (or other `Disallow` lines) to its robots.txt: it would hide every NETA65 site
  from every search engine, and search engines need the sites' styles, scripts and data files to read the pages.
- **No service worker** (`sw.js`) at its top: it would take over every NETA65 site in visitors' browsers.
- Keep it **public**, and keep its robots.txt the same as `docs/user-site/robots.txt` here (change both together),
  apart from the optional block of step D.

Optional, once it exists: in Search Console add a second property, **URL prefix** `https://neta65.github.io/`,
verified with the HTML file Search Console offers (upload it to the `neta65.github.io` repository: **Add file →
Upload files**). Only a property without a folder shows Google's *robots.txt report*.

**D. Optional: keep AI-training crawlers out (the owner's choice)**

The bottom of that robots.txt has a block that is **off** as delivered. Turned on, it asks the robots that collect
pages to **train AI models** — GPTBot (OpenAI), ClaudeBot (Anthropic), Google-Extended (Google's Gemini), CCBot
(Common Crawl) and Applebot-Extended (Apple) — to stay away. Google and Bing search, and the robots behind AI
search answers that link to the site (ChatGPT search, Claude, Perplexity), stay allowed, so the site still shows in
search results and in those answers. The Grapevine and La Viña magazines' own websites keep GPTBot out the same
way. It covers **every** NETA65 site under neta65.github.io (the booth and the archives too).

To turn it on: in the **neta65.github.io** repository open `robots.txt` → pencil icon → delete the `# ` at the
start of the six lines from `# User-agent: GPTBot` to `# Disallow: /` (nothing else) → **Commit changes**. Leave
`docs/user-site/robots.txt` here as it is, with the block off (the Code check tests the delivered file that way);
the weekly link check then lists the crawlers under *AI-model training crawlers kept out (the owner's choice)*, so
the choice is on record. To turn it off again, put the `# ` back.

### What not to expect, and what not to do

- **Google and Bing decide what they show, and when.** A submitted sitemap is a hint, not a promise: new pages
  can take days or weeks, not every page is taken, and Google sometimes writes its own description.
- **No site name above the results.** Google shows a site's name only for a whole address, not for a site in a
  folder like neta65.github.io/aagrapevine/ — it shows the address instead. With a custom domain (section 12) it
  could.
- **No question-and-answer or step-by-step boxes.** Google retired its FAQ and HowTo results (and the search box
  under a site's link). The questions on `/contribute/` still help search engines and AI tools read the page.
- **No event listing for online-only events** (Google's own rule), nor for an event whose place has no city,
  state or ZIP code (a venue's name alone: Google wants the address).
- **Nothing to add "for SEO":** no keywords tag (Google ignores it), no sitemap "pings" (Google and Bing retired
  them), no analytics or trackers, no promotional wording and no member's name anywhere (the AA principles,
  [how-to/pages-and-code.md](how-to/pages-and-code.md)).

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
| A member's recording on *Share your story* is gone, or a take says **Not saved on this device yet** | Recorded in a private tab that was then closed (on an iPhone, also one left in the background long enough for iOS to clear it: the take then says "The browser removed this take from this device …" if the page had no copy of it); recorded in Safari and looked for in the Home Screen app (or the other way round), or in Facebook's or Instagram's own browser; Safari removed it after 7 days of using Safari without tapping anything on the site; or the device is out of room (the box under *Your takes* says so). Until mid-October 2026 a link from an iPhone's Private tab also lost it | Open the page where the take was made. Right after a good take, **Download the MP3** (iPhone: **Save to Files**) or send it: a copy outside the browser is the only one the browser can't remove. With **Not saved on this device yet**, stay on the page, delete takes you don't need or free up space, then **Try again**. Ask the member to open **Having trouble? Check this device** (at the bottom of the recorder) and send you the report (**Copy the report** or **Email it to the committee**). Details: [The story recorder](#the-story-recorder-share-your-story). |
| *New since your last visit* never shows on What's New | A first visit on that device, a private tab, site data blocked or cleared (Safari may clear it after 7 days of using Safari without tapping anything on the site), or nothing new since the last visit | Nothing to fix: it is remembered per device and per browser. On an iPhone the Home Screen app and Safari each keep their own. |
| A video starts without captions although **Video captions** is On (Aa panel) | YouTube decides in the end: some phones' players ignore the request, and a video may have no captions in the page's language | Use the video's own **CC** button (the steps are on the Accessibility page). |
| A reminder from an **Add to calendar** file or the deadlines calendar never rings | Google Calendar ignores the reminders inside calendar files; on an iPhone, "Remove Alerts" was left on when subscribing | Google: in its settings, open the calendar and add a notification (for all-day events, for the deadlines). iPhone: subscribe again with **Remove Alerts** off. |
| An issue "Broken links found by the weekly check" appeared | A link in the settings or in a `content/` file moved, or the root robots.txt has a problem (the next row) | Open the issue; fix the address in `config/site.yml` or the `content/` file. It closes itself when fixed. |
| That issue has a part *The root robots.txt* saying "Fix it in **the NETA65/neta65.github.io repository**" | Someone changed robots.txt there (a `Disallow` line, a lost `Sitemap:` line) or set a custom domain on that repository | Signed in as **NETA65**: copy [`docs/user-site/robots.txt`](docs/user-site/robots.txt) over robots.txt in that repository (and turn the optional AI block of 12b, step D, on again if the committee chose it); remove a custom domain there (*Settings → Pages*). The issue closes itself after the next clean week ([12b](#12b-search-engines-google-bing)). |
| The weekly link check's summary says *The root robots.txt … Not set up yet* | The NETA65/neta65.github.io repository does not exist yet | Nothing is broken: search engines may visit everything. To announce the sitemap there, do [12b, step C](#12b-search-engines-google-bing). |
| That issue's part *The root robots.txt* says "The check itself could not run" | The weekly check of that file crashed or could not install its tools (nothing is known about the file this week) | Usually nothing: the next week's check tries again. If it repeats, send the run (its step *Check the root robots.txt (politely)*) to whoever helps with the website. |
| A yellow ⚠ *Sitemap dates*: "N of 88 pages changed although the code did not" | Usually a settings or wording change that touched many pages (fine); if it comes back on ordinary days, a text on some page that changes by itself every day is not marked yet | If it repeats, send the run to whoever helps with the website ([how-to/automation-and-troubleshooting.md §14](how-to/automation-and-troubleshooting.md#14-troubleshooting)). The site is published either way. |
| A yellow ⚠ *IndexNow* (HTTP 403, 429 …) after publishing | Bing and the other IndexNow engines did not take the list this time (403 is normal on the very first send) | Nothing, unless it repeats on every run: the site is published, and the next publish sends its own list ([how-to/automation-and-troubleshooting.md §14](how-to/automation-and-troubleshooting.md#14-troubleshooting)). |
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
dark mode), motion (follow the device / reduce: the vineyard art stops), **Read aloud** (the device's
own voice reads the page, paragraph by paragraph, in the page's language), **Video captions**, then Data saver
and the "Offline & app" part (above). The choices are saved on that device only (`localStorage "gvlv-prefs"`) and
applied before the page is drawn; nothing is sent anywhere. **Reset to defaults** clears them.

- **Read aloud** starts from the part of the page on the screen: at the top of the page it starts at the
  beginning; scrolled down, at the first paragraph on the screen (in the page's main column, not a side column that
  stays in view), and the page does not jump. **Reading speed: Slower / Normal / Faster** (Normal at first) is heard
  at once; how much it changes depends on the device and its voice (some voices always read at one speed — the
  panel says so). **Previous paragraph** / **Next paragraph** are buttons with those words in the panel; the small
  read-aloud bar at the bottom of the screen (shown while the page is read or paused and the panel is closed) has
  them too, on every screen size as icon buttons whose names screen readers say (and a mouse shows as a tooltip).
  It still stops when you leave the page.
- **Video captions: Off / On** (Off at first). On, every YouTube video on the site — Home, About, the GVR / RLV
  corner, Watch, Listen — starts with captions, in the page's language when the video has them. YouTube does not always follow the
  request (some phones' players don't) and its automatic captions can get words wrong; the video's own CC button
  still works. The booth display keeps its own captions switch.

**Light or dark:** the moon / sun button in the header (from 640px wide), or the **Dark mode** switch, the
first line of the Menu on phones and tablets — one setting, saved on that device (`localStorage
"gvlv-theme"`) and applied before the page is drawn; until someone chooses, the site follows the device's
own light / dark setting.

The **Accessibility** page (`/accessibility/`, in the footer) explains the settings and gathers the other
ways in: YouTube captions (with a one-tap **Turn on captions for all videos** button — the same choice as the
panel's Video captions), AA Grapevine's American Sign Language playlist and AA's own ASL videos, audio
(podcasts, the weekly open meetings, recording a story by phone), printing and large print, joining our
meetings by phone ([above](#joining-our-meetings-by-phone)), and how to report a barrier.

**For maintainers**

| File | What it does |
|---|---|
| `src/_includes/partials/comfort-panel.njk` | the panel (included by `header.njk`; the Aa buttons are in the header and the drawer) |
| `src/_includes/partials/header.njk` | light / dark: the header's moon / sun button and the menu's "Dark mode" switch (`role="switch"`; its look: `main.css` `.site-switch`), both `app.js` `siteHeader` `theme` / `toggleTheme()` |
| `src/_includes/layouts/base.njk` | the first `<head>` script: saved choices → `<html data-text data-spacing data-contrast data-motion data-saver>` |
| `src/assets/js/app.js` | `GV.prefs` (read / save / apply; event `gvlv:prefs`; `gvlv-prefs` also holds `rate` — `"slower"` / `"normal"` / `"faster"`, 0.8 / 1 / 1.2 × the voice's own speed (`RATES`) — and `captions` — `"off"` / `"on"` —, which change nothing on the page and so are not applied in `base.njk`), `GV.reducedMotion()`, `GV.tts` (read aloud: `.prev()`, `.next()`, `status.next`; where it starts, `onScreen()` / `pinned()`; a list marked `data-tts-read` has its chips read, as the AA offices on *New to AA?*), `GV.ytCaptions()` (the captions part of a YouTube address while On; a lite-youtube preview gets it just before it plays, and `media.js` adds it to the Watch dialog), the panel |
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
  `/events.ics` feeds and the story deadlines calendar, `/deadlines.ics`, are never kept).
  A page opened online but not saved keeps its own area stylesheet (the
  monthly toolkit's, the booth's, the Tracker's …) offline after a code update too: the new service worker carries
  the old version's stylesheets over (nothing is downloaded for it). Offline, kept pages open normally under a small "You're offline" notice; any other
  page shows the Saved pages & app page (`/offline/`, also "See saved pages" in the menu) in its place,
  saying "You're offline — this page isn't saved on this device yet" above the list of saved pages, and
  reloads itself when the connection is back. That stand-in keeps up with the daily content (the **Join
  by phone** numbers, the footer): pages opened with a connection refresh it once a day, and opening Saved
  pages & app refreshes it at once. An address typed without its last slash (`…/aagrapevine/es`) opens
  the same saved page. When the connection is so slow that a page
  takes more than 4 seconds, the kept copy opens instead, with "Slow connection — this is the copy saved …
  Try again". Audio, video and the official sites always need a connection — except the [story
  recorder](#the-story-recorder-share-your-story) on Share your story, which records without one: a take is always
  ready as a WAV, and as an MP3 too once its MP3 encoder has been loaded with a connection (it is fetched the first
  time the microphone is turned on, and the worker keeps it like a script: so again after each code update). Until
  then the MP3 is made when the connection is back, or the next time the page opens with one.
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
shell and styles/scripts (the story recorder's `.wasm` MP3 encoder too) are replaced with each code version;
kept and saved pages, images (≤ 200) and the JSON indexes survive updates. Service workers need `https://`
or `http://localhost` (so they work in `npm start`); with a custom domain (`PATH_PREFIX=/`) the scope follows
automatically. To test a clean first visit in Chrome: DevTools → Application → Storage → **Clear site data**.

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
  paid date is in January (a request marked paid with no paid date counts as settled). Its **Not requested** /
  **Submitted** columns go by the request's date the same way: asked for in January, it is "Not requested" in
  December's view, paid or not.
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

### The story recorder (Share your story)

The **story recorder** (Share your story, <https://neta65.github.io/aagrapevine/contribute/#record>; Spanish
`/es/contribute/#record`) lets a member record a story for Grapevine's Audio Project or La Viña's *Graba tu
historia* with the microphone of a phone or a computer, listen to it, and send it as a file the magazines accept
(both take WAV and MP3). It is the card at the top of *Record your story*, above the two story-line cards; each
card's "Or record it yourself" box links to it (**Or record it here, in your browser**: it scrolls up with that
magazine chosen). Like the Tracker it lives only in that browser — nothing is uploaded to this website. This
describes recorder 1.0.0 (October 2026) with the takes' storage as rebuilt in mid-October 2026 (database schema 2:
on phones, an iPhone above all, takes used to vanish after a link to another page), and the topic list and the
device check added after it.

**What to tell your GVRs and RLVs**

- **Choose the magazine first** (Grapevine · in English, La Viña · in Spanish; the page's language picks the first
  one). It sets the length to aim for, the checklist, what to say first, the address, the file names and the
  language of the e-mail. **What to say first** follows each magazine's instructions: for Grapevine, your full name
  and phone number, where you are, that you give AA Grapevine permission to use your story (the sentence is our
  suggestion: on the phone line it is a key), then "My name is …, and I'm an alcoholic."; for La Viña, begin as in a
  meeting, then your full name and phone number, then La Viña's permission sentence word for word (shown on the
  page). **Before you record** adds the magazines' tips: one topic, as you would share it in a meeting, your own
  story only (never a recording of a speaker at a meeting or event), no last names of others, a quiet room, a short
  test take first, and send it once (by e-mail or on the magazine's site, not both).
- **What will you talk about? (optional)**, right under the magazine choice. For **La Viña** it lists, in La
  Viña's own Spanish words, the themes of its coming issues with the days left ("2 days left" / "quedan 2 días",
  counted on the member's device), then **La Viña's suggested topics (any time)** exactly as La Viña writes them
  (on the English page a chosen topic's English meaning shows under the list, marked "Auto-translated" when a
  machine made it). For **Grapevine** it lists the themes of its coming issues under **Ideas: themes of
  Grapevine's coming issues**, then its departments and what it always needs under **Ideas: Grapevine's suggested
  topics** (a theme of a coming issue that is also a department — "Emotional Sobriety" — once, with its deadline) —
  "listed only as ideas to get you started". **Another topic: write your own** opens
  a box for the member's own words. The topic goes into the e-mail's Topic line and subject and into the file's
  name (`la-vina-historia-2026-10-15-recaidas-toma-2.mp3`): "It goes into your email and the file's name. Each
  magazine chooses which stories it publishes." — nothing promises publication. A topic gets into the file's name
  only if it is chosen before that take is first downloaded or shared: from then on, **while the page stays open**,
  the file keeps its name (a topic chosen later still goes into the e-mail). The page keeps that name in its memory
  only, like the topic: after a reload, or on coming back later (the take itself is still on the device), it no
  longer knows which name the saved file has, so the name it shows follows the topic chosen then. A member who picks
  a topic after a reload should download (or share) the take again before sending it, so the file attached is the
  one the e-mail names. The topic is never stored: **Clear these details** (*Borrar estos datos*) and **Delete all
  recordings from this device** clear it, and switching the magazine clears a topic from the other magazine's list
  (a topic the member wrote stays).
- **"Record a story on this topic" / "Graba sobre este tema".** On Share your story, in La Viña's card under
  *Upcoming themes & deadlines*, each of La Viña's suggested topics has this small link: it scrolls up to the
  recorder with La Viña and that topic already chosen (the address does not change, which keeps an iPhone Home
  Screen app's microphone permission). There is no such link on Grapevine's themes or topics (only ideas: its
  topic tiles say instead why they are there — **In every issue** for a department, **Always needed** for Steps 4–12
  and every Tradition) or on the dated deadline rows (those rows have **Add to my calendar**; the dated La Viña themes
  can still be picked in the list).
- **Recording.** **Test the microphone** shows the level in words ("Good level", "A bit quiet: move closer", "Too
  loud: move back a little"); **Start recording** counts 3, 2, 1; then **Pause** / **Resume**, **Stop and save** or
  **Discard**. The bar under the timer shows the magazine's length (Grapevine 6–8 minutes, La Viña up to 7, read
  every day from the official pages) and warns 30 seconds before the limit; a screen reader hears when the minimum
  is reached, one minute is left and the limit is reached. Every take stops at 10 minutes. A device with more than
  one microphone offers a choice; **Reduce background noise** (off at first) is for a noisy place only. Keep the
  page open with the screen on (the recorder keeps it awake where the browser can): a call, a locked screen or
  another app pauses the take, and **Resume** goes on.
- **Takes** (at most 8 on a device; then "delete one you don't need"): each one can be played, renamed, marked
  **My pick** or deleted. **Trim or adjust** (cut the start or the end; **Even out the volume** for a quiet take)
  makes a new take and keeps the original. A take that is too short or too long for its magazine, too
  quiet, too loud or missing some sound says so.
- **Send or save.** **MP3** is the one for e-mail (8 minutes ≈ 7.7 MB); **WAV** is full quality and much larger
  (over about 18 MB the page says it is too big for most e-mail) — fine for the magazines' upload forms (one file,
  up to 100 MB: **Upload on Grapevine's website** / **on La Viña's website**). Save it first (**Download the MP3**;
  in the app on iPhone or iPad, **Save to Files**), then send it: **Share or email…** (Mail, Gmail … with the file,
  where the phone can share files), or the e-mail the page writes — the address, a subject and a message in the
  magazine's language, built from details the member may add (topic, name, phone, e-mail, mailing address, where
  they are, **Show my name as**: first name and last initial, initials only, or anonymous) — with **Open my
  email**, Gmail or Outlook.com, then attach the file the page names (`grapevine-story-2026-10-13-take-2.mp3`,
  `la-vina-historia-2026-10-13-toma-2.wav`). Those details only go into that e-mail: the site neither keeps nor
  sends them. Grapevine's address is the Audio Project's (`webcoord@aagrapevine.org`, read from the official page);
  La Viña's is `links.lv_email_editorial` in `config/site.yml` (`manuscritoslv@aagrapevine.org`), else the one on
  its page — the same rule as the cards' "Or record it yourself".
- **Already recorded it?** **Add a recording** turns a file from the phone or computer — an iPhone Voice Memos
  `.m4a`, an MP3, a WAV … (at most 80 MB and 20 minutes) — into a take: trim it and send it as MP3 or WAV.
- **Kept on the device until the member deletes them.** The site never deletes a take on its own (until
  mid-October 2026 takes older than 30 days were removed; the only thing cleared now is what a cut-off take left
  with no sound or under one second of it). A take is written to the device while it is being
  recorded — when it starts, then every 3 seconds and whenever the page is hidden — so a closed page, a dropped call
  or a crashed browser loses at most the last few seconds: the take comes back marked "Recovered".
  **Stop and save** writes the rest and the MP3; only then is the take "saved". The sound is stored as plain bytes,
  never as a browser "Blob" (an iPhone's Private tab refuses every Blob, and sometimes a normal tab does too: that
  is how takes vanished before). If a save fails anyway, the take stays in the page with all its sound and says
  **Not saved on this device yet**; a box under *Your takes* says so too, with **Try again**, and the page keeps
  trying by itself (3, 6, 12 and 20 seconds later, then every 20 seconds, whenever the page is shown again, and
  when another take is saved or deleted). Until it is saved, a tap on a link to another page asks first — "A take
  isn't saved on this device, so leaving this page loses it. Download or send it first. Leave anyway?" (while a
  take is being recorded or saved: "A take is being recorded or saved …") — also on an iPhone, where the browser
  itself never asks. On a computer or Android phone the browser's own "Leave site?" also covers closing the tab, a
  reload and Back; an iPhone can't be asked about those, so keep the page open until the badge is gone. Links that
  open a new tab, download a file, or start an e-mail, a call or a calendar file ask nothing.
- **Short of room.** Before a take (and after a recording is added) the page warns when the device may not have
  room for a long one ("about … free": delete takes you don't need, or free up space, first); nothing is stopped.
  A save that fails because the device is full says "This device is out of room for recordings …": delete takes
  you don't need (or free up space), then **Try again** — deleting a take saves the waiting one at once, and each
  take shows its size meanwhile. A take whose sound can't be read back is shown as such (with **Try again**;
  **Delete** works), never deleted, and never hides the others.
- **How long the browser keeps them.** The *Your recordings stay on this device* box says it for that browser:
  "Your browser has agreed to keep them until you delete them." (the page asks the browser for that —
  `navigator.storage.persist()` — at the first **Stop and save**, **Add a recording** or **Apply**; the browser
  decides), else that they are kept until deleted but the browser may still remove them if the device runs short of
  space (and a private or Incognito window only until it is closed); in a tab on an iPhone or iPad, that Safari (or
  "this browser": Chrome, Firefox, Edge, DuckDuckGo… there) may remove them after 7 days of using it without
  tapping anything on this site, so keep a copy of the take you want (save it to Files, or send it) — Safari on a
  Mac says the same with "download it". The app on the Home Screen is exempt from that 7-day rule, but on iPhone
  and iPad it keeps its recordings apart from Safari: a take made in one doesn't show in the other (the box says
  so). The box says "a closed page or a dropped call doesn't lose them" only where that holds. In Safari's private
  tabs and windows a box says the takes are kept **at most** until it is closed — on an iPhone, Safari may lose them
  sooner if the member switches to another app — so save or send the one they want as soon as it is good. Inside
  Facebook, Instagram and other apps, the card says recordings made there may not be kept and won't be in Safari or
  Chrome (and the box adds no promise of its own). A browser that won't let the page keep anything (website data
  blocked) says so: takes are then **Only in this page**.
- **When the browser loses them anyway.** An iPhone keeps a private tab's recordings (in any browser) in a part of
  the browser iOS may end while the page is in the background. There the page keeps its own copy of every take and,
  when it finds the device's copy gone (on coming back to the page), saves it again — until it is, the box under
  *Your takes* says a take isn't saved yet and leaving asks first. A take being recorded or saved at that moment is
  written again from its start, so it is never "saved" with its beginning missing. A take the page had no copy of
  (it could not tell the tab was private) says "The browser removed this take from this device, and this page has
  no copy of it": delete it from the list. A **Try again** that fails again says so ("still isn't saved … it will be
  tried again", or "still can't be read").
- **Keep my recordings on this device** off (it asks first when takes are saved; the switch works once the takes
  are listed, and not while recording): nothing is kept — takes last only while the page is open, and leaving
  asks first. Switched off, it removes only the takes this page lists; **Delete all recordings from this device**
  spares a take another tab is recording.
- **Privacy.** The recording has the member's name and phone number: send it only to the magazine (or someone they
  trust, like a sponsor; **Share just the file** sends it with no message), and never post it. **Delete all
  recordings from this device** also clears the e-mail details — on a shared computer, do it when you are done. The
  Gmail and Outlook.com buttons open with a short message only (a web address stays in the browser's history), and
  the whole message is copied to paste.
  *For maintainers — who else could read them:* the takes are in IndexedDB on the origin
  `https://neta65.github.io`, which every GitHub Pages project of the NETA65 account shares. Keep those other
  projects free of third-party scripts (a custom domain for this site would end the sharing: §12).
- **When it can't record:** inside Facebook, Instagram and other apps (the microphone may be refused: the card
  says so, with **Copy the link** and how to open the page in Safari or Chrome), without `https://`, when the
  microphone was refused (the card shows the steps for that browser), and without JavaScript (a note points to "Or
  record it yourself": the phone's own voice recorder, then e-mail the file). It works offline on a saved Share
  your story page (always WAV; MP3 once its encoder has been loaded with a connection — see *Use it offline*
  above).
- **Having trouble? Check this device** (a folded panel at the very bottom of the recorder; Spanish **¿Tienes
  problemas? Revisa este dispositivo**). Opened, it makes a short report, in the page's language, of what this
  phone or computer and its browser can do for the recorder: the date, the page's language and the site's version,
  the browser and system, whether it is a tab, the installed app or an app's built-in browser, online, secure page,
  microphone access and permission, whether recording and the MP3 maker work here, whether saving on the device
  works (it writes a few bytes into a small database of its own, `gvlv-rec-check`, reads them back and deletes it —
  the recordings are not touched), the *Keep my recordings* switch, whether the browser promised to keep them, signs
  of a private window, free and used space, how many recordings are on the device (and how many are not saved yet
  or can't be read), the last storage error, and the browser's own description of itself (its "user agent"). It
  **never** holds a recording's name, topic, length, file name or sound, anything typed in the e-mail details, or a
  microphone's name, and it **never asks for the microphone** (the permission is only read). **Copy the report**,
  **Email it to the committee** (the member's own e-mail app opens, addressed to `site.contact_email`, with the
  report and a "What happened (optional):" line — nothing goes until the member sends it; a report too long for the
  e-mail link is copied to paste) and **Check again**.

**Real-device test (owner, once the mid-October 2026 storage change is live)**

The automatic checks run in Chromium on a computer; the takes went missing on phones, an iPhone above all. Do this
on each of: **(a)** iPhone, Safari, a normal tab · **(b)** iPhone, Safari, a **Private** tab · **(c)** the site's
app on the iPhone's Home Screen · **(d)** Android, Chrome. A take of 20 seconds is enough; say anything.

1. Open <https://neta65.github.io/aagrapevine/contribute/#record>, **Start recording**, then **Stop and save**.
   Within a second or two the take is listed with no "Saving on this device…" or "Not saved on this device yet".
2. Tap a link to another page of the site (the footer's **Events**), then a link back to *Share your story* (not
   Back). The take is listed and plays.
3. Again with **Back** instead of the link back, and once with the header's **ES**: `/es/contribute/` lists the
   same take.
4. Lock the phone right after **Stop and save** on a second take; unlock, tap a link and come back: both are there.
5. While recording, tap the footer's **Events**: the page asks "A take is being recorded or saved. If you leave
   this page now, it may be lost. Leave anyway?". **Cancel** stays on the page; then **Stop and save**, and the take
   is listed.
6. Read the *Your recordings stay on this device* box. (a): Safari's 7-day line ("Safari may remove them after 7
   days of using Safari without tapping anything on this site …"), and "Safari and the app on your
   Home Screen keep separate recordings". (b): "In a private tab or window, your takes are kept at most until you
   close it", and above the takes the box "This looks like a private tab …". (c): the takes recorded in Safari are **not**
   listed (expected), and the line says "Your browser has agreed to keep them …" or "… may still remove them if the
   device runs short of space". (d): one of those two.
7. Close the tab (swipe the app away; on Android close Chrome's tab) and open the page again: the takes are there
   — except in (b), where closing the private tab ends them (expected: the box said so).
8. **Delete all recordings from this device**.

After each of (a)–(d), open **Having trouble? Check this device** at the bottom of the recorder and tap **Copy
the report** (or **Email it to the committee**), and paste it back to the maintainer with what you saw. The report
already holds the browser, the system, the signs of a private window, the storage results and the number of takes;
add only what the box or the take's badge said, whether a take marked "Recovered" came back, and (iPhone) whether
Lockdown Mode or Safari's "Block All Cookies" is on.

**For maintainers**

| File | What it does |
|---|---|
| `src/assets/js/recorder-core.js` | `window.GVRec`, no DOM, no storage, no devices: the numbers (`LIMITS`: 8 takes, the stop at 10:00, the sound written every 3 seconds in rows of at most 1 MiB, tries again every 20 seconds, 10 s / 30 s before a storage open / transaction counts as failed, MP3 CBR 128 kbps mono at 44.1 kHz, the 18 MB e-mail warning, 80 MB / 20 minutes for an added file …; no time limit on the device), 16-bit PCM and the 44-byte WAV header (WAV: 16-bit mono at the device's own rate), the meter, the waveform, the magazine's length rule (`rule`, `zone`, `verdict`, `crossed`), file names (`fileName(take, ext, topic)`: a chosen topic, shortened, goes before the take's name), the topic list's days left (`daysLeft()`, counted from the device's own today), the device check's `REPORT` (the only facts a report may hold, in order) and `report(facts, words)` (one line each), the e-mail message and its mailto / Gmail / Outlook.com links, which browsers can record, and for storage `SCHEMA` (2), the sound rows' keys (`soundKey`, `soundRange`), what a storage error means (`storeError`: try again, ask to delete takes, reload, or keep the takes in the page) and which clicks leave the page (`leaves`). A plain ES2019 script (an older iPhone's Safari runs it); its header comment explains the sound, the rules, a take's record and the files |
| `src/assets/js/recorder.js` | the Alpine component `storyRecorder` and the sound: the microphone (`getUserMedia`; the browser's voice processing off unless **Reduce background noise**) → an AudioWorklet made from a Blob URL (a ScriptProcessor where there is none) → 16-bit PCM, with the MP3 made as the take goes; storage in IndexedDB `gvlv-recorder` version 2 — `takes` (the records; a take being recorded or saved is a `draft`) and `sound` (its PCM and MP3 as ArrayBuffers of at most 1 MiB, never Blobs: Safari's private store refuses them, WebKit bug 156347) — with a time-out on every open and transaction, retries instead of giving up, a Web Lock per take being made or not yet saved (another tab never takes it for a crashed one), the version-1 stores `pcm` / `mp3` / `parts` read once, moved into `sound` and emptied; the lasting storage box (`storeNote()`: none / reload / full / unsaved / private) and each take's badge; `navigator.storage.persist()` / `persisted()` / `estimate()`; a private tab (`getDirectory()` refused, asked in Safari and every iPhone / iPad browser — only Safari is told "private") or a database the page saw come back empty (`E.lost`) keeps each saved take's sound in the page too (`ephemeral`) and saves it again if the browser loses the device's copy (`checkLost`; a saved take it holds no sound of is shown as lost), and a write such a loss cut short starts again from its first row (`E.gen`); `localStorage "gvlv-rec-keep"` (the switch); trims, added files, Share / Download / e-mail; the topic list (`topicPick` / `pickTopic` / `topicText`; `go(pub, topic)` for the cards' links, whose `data-rec-topic` carries La Viña's suggested topic; the topic is page memory only, and a take's file keeps the name it had when it was first downloaded or shared while the page stays open — `namedAs`, page memory too: after a reload the take is downloaded again once a topic is chosen); the device check (`diagnose()` gathers the facts, `storageCheck()` writes, reads back and deletes its own database `gvlv-rec-check`, `micState()` reads the permission and never asks for the microphone). Leaving: a capture click listener (`askLeave`, `window.confirm`: it works on an iPhone) asks before a link takes the tab to another page while `atRisk()`; the browser's "Leave site?" (beforeunload) covers closing the tab, a reload and Back where the browser asks; `html.cm-rec-hold` while a take is at risk. Its header comment (WHERE TAKES LIVE) explains the storage. No MediaRecorder (it gives WebM or MP4, which the magazines don't take), and it never changes the address's `#` (iOS home-screen apps then forget the microphone permission): the cards' links and the page nav's `#record` chip scroll instead |
| `src/_includes/partials/story-recorder.njk` | the card `#recorder` (included by `src/pages/contribute.njk` at the top of `#record`; that page's `pageScripts` lists `recorder-core.js` and `recorder.js`, its cards carry the `data-rec-go` links) and the `#rec-config` JSON: each magazine's length and address from the data, the e-mail templates in the magazine's language, `topics` (the topic list), `diag: {to, ver}` (the device report's address, `site.contact_email`, and the code's version — `data-lastmod="skip:diag"`, so a deploy does not date the page again), and the words the script writes or announces (`recSay` under `"s"`: a new one must be listed there; the report's words `recReport` under `"d"`) |
| `eleventy/filters/read.js` → `recorderTopics()` (filter `readRecTopics`) | the topic list, from the same `readEditorial` data as the deadline cards: each magazine's coming themes first (at most 8), then its suggested topics (at most 30; Grapevine's too, since October 2026), a theme listed twice once; items `{i, t, l, g, m, d, dated}` — no count of days, so the built page says the same every day |
| `src/assets/css/areas/community.css` → the `cm-rec-*` rules at the end | the look; `cm-rec-on` on `<html>` while recording, which `pwa.js` `busy()` also reads (the install notice stays away) |
| `src/assets/js/pwa.js` → `recHeld()` | while `<html>` has `cm-rec-on` or `cm-rec-hold`, the **Updated — Reload** notice of a new version waits (its Reload would end the take, and an iPhone never asks before a reload), and so does the line a screen reader hears with it; it shows, and is said once, when both are gone |
| `src/_i18n/community.json` → `community.recorder.*` | the words, English and Spanish (the section and the cards are `community.rec.*`) |
| `eleventy.config.js` (vendor copies), `package.json` | `wasm-media-encoders` (MIT; LAME 3.100 inside, LGPL) copied to `/assets/vendor/wasm-media-encoder.min.js` and `/assets/vendor/lame-mp3.wasm`; the page fetches them the first time the microphone is turned on |
| `src/_includes/pwa/sw-core.js` | `.wasm` is in the static route (stale-while-revalidate, like the scripts), so the MP3 encoder works offline once it has been fetched (per code version) |
| `db.audio_project`, `config/site.yml` → `links:` | the lengths (`minutes_min` / `minutes_max`), Grapevine's address (`gv.email`), La Viña's permission sentence (`lv.permission_text`); La Viña's address `lv_email_editorial`, the upload forms `gv_share_story` / `lv_share_story` |
| `tests/test_recorder_core.py`, `test_recorder_page.py`, `test_recorder_store.py`, `test_r12_u2_contribute.py` (the topic list, days left, file names, the device report); the browser checks `StoryRecorder`, `RecorderKeepsTakes`, `RecorderHoldsUpdate`, `RecorderTopicAndCheck`, `WallsLinks` | the logic in Node.js; the page, its script and its strings; the storage, page load after page load, over a pretend IndexedDB that fails the way phones fail (`tests/fakeidb.js`: Blobs refused, a write failing once or for good, a full device, an unreadable take, an open that never answers, a version-1 database, two tabs, a link click while a take isn't saved); in a real browser (`tests/browser`, Chromium's fake microphone), a take recorded in English and Spanish, its MP3 and WAV, the address, a reload, "Delete all"; a take still there after a link away and back and in Spanish, also where the browser refuses Blobs; a full device that asks before a link and saves once there is room; the update notice held while a take is being recorded |

### Listen and Watch

Nothing to set up: everything here builds itself from the podcast and YouTube syncs.

**What to tell your group**

- **La Viña's spoken stories** (Listen, `#la-vina-audio`): a card, **Spoken stories from La Viña** / **Historias
  habladas de La Viña**, lists La Viña's own Spanish playlists on the AA Grapevine YouTube channel (*Un día a la
  vez*, *Amor y servicio*, *Mujeres en AA*, *Tocaron Fondo* …), each with how many videos it holds and how long they
  last. On the **Spanish** Listen page it comes first, right after the player (the podcast episodes are in English;
  the note under the episodes links up to it); on the English page it comes last. A playlist opens **Watch** with
  only that playlist (`/es/watch/?pl=<playlist id>#videos`), and **See all of La Viña's videos** opens Watch with
  La Viña's videos only (`/es/watch/?lang=es#videos`); a video plays (from YouTube's privacy-enhanced player) only
  when it is tapped. Two more lines lead to La Viña's open meeting (Meetings) and to the story recorder. The
  playlists keep La Viña's own Spanish titles on both pages, and the card says "videos", never "podcast". A Spanish
  playlist is listed once it has at least 3 videos that are not Shorts (the apps' how-to Shorts and the "Weekly
  Open" and "Podcast" playlists, which have their own chips on Watch, stay out); its count and length include its
  Shorts, as Watch counts them. When YouTube's "not a bot" check leaves the lengths unknown, the card shows the
  counts only.
- **Addresses that open a filtered list**, to copy and send: Listen `?show=…` / `?season=…` (as before) and
  `?ep=<episode id>` (one episode, below); Watch `?lang=es` or `?lang=en`, `?type=short`, `weekly` or `podcast`, and
  `?pl=<YouTube playlist id>`. Choosing a filter on Watch updates the address; values the page doesn't know are
  dropped.
- **Share one episode, video or story.** Every episode has its own address,
  `https://neta65.github.io/aagrapevine/listen/?ep=pod:gv:c8fe55f36619`: it loads that episode into the player
  **without playing it**, scrolls to its row and marks it **From your link**. An episode older than the newest 24
  waits for the full list ("Opening the episode from your link…"); if the visitor starts something else meanwhile,
  it is offered instead ("From your link: … · Go to episode"), and if the list can't load (offline, weak signal) the
  page says "The episode from your link didn't open: the full list of episodes couldn't load." with **Try again**.
  A shared link never changes the visitor's own "Continue listening": nothing is saved until they play, skip or
  seek. The **Share** buttons: each episode row on Listen and the latest-episode player (the site's `?ep=` link);
  each video card on Watch (the official YouTube link); each story on Read (current issues and the archive) and on
  Published writers (the official magazine link, with the title as the magazine published it and "— Grapevine,
  October 2026" / "— La Viña, septiembre–octubre de 2026" — never the story's text or the writer's name). Where the
  browser has its own share sheet — phones, and some computers too (Safari on a Mac, Chrome or Edge on Windows) —
  they open it, with the title at the start of the message too (some apps, such as Messages on an iPhone and
  WhatsApp, drop the share sheet's separate title, and the link's preview names only the page: "Hot Topic:
  Sponsorship" and the link, not just "Listen"); elsewhere the title, the share line (when there is one) and the
  link are copied as text, and the button says "Copied!". In Search and on What's New an episode now opens in the
  site's own player, with the podcast host's page as a second, smaller link (**Episode page**). Search engines still
  see `/listen/` as one page.
- **Easier listening.** The speed button goes 1× → 1.25× → 1.5× → 2× → **0.75×** → 1× (remembered on the device).
  **Home's** episode player uses the same saved places as Listen, on the same device: an episode started on Home goes
  on from the same point on Listen and the other way round, finished ones say **Played**, and an episode left
  part-way (more than 30 seconds in, in the last 60 days) shows **Continue listening: *(the episode's title)* — 23 min left** with
  **Resume** (on `/es/`: *Sigue escuchando: … — quedan 23 min*, **Continuar**). Nothing leaves the device
  (`localStorage "gv:audio:pos"` and `"gv:audio:last"`, as before).

**For maintainers**

| File | What it does |
|---|---|
| `eleventy/filters/media.js` | `mediaSpanishStories` (the La Viña card's playlists: `SPOKEN_MIN` = 3), the playlists' `id`, Watch's `plIds` |
| `src/pages/listen.njk` | the card (macro `lvCard`, `#la-vina-audio`: first on `/es/`, last on `/listen/`) |
| `src/assets/js/media.js` | the player (`RATES`), `?ep=` (`openLinked`, the `held` flag: nothing saved until the visitor plays, skips or seeks), Watch's `readUrl` / `syncUrl` (`?type=`, `?pl=`, `?lang=`), the share links |
| `src/assets/js/home.js` | Home's player on Listen's saved places (`gv:audio:pos`, `gv:audio:last`), "Continue listening" |
| `eleventy/filters/library.js`, `src/assets/js/search.js` | the search index: an episode's `u` is `/listen/?ep=<id>`, its host page the optional `u2` |
| `tests/test_r12_u1_listen.py`, `tests/browser/test_r12_u1_listen_browser.py` | the card, the addresses, the shared episode, the share texts, Home's places |

### What's New: new since your last visit

A visitor who comes back to **What's New** after a while sees one line above the timeline — "New since your last
visit (Oct 13): 18 updates" / "Desde tu última visita (13 oct): 18 novedades" — and a small green **New for you**
label on each entry that arrived since. **Mark all as read** removes the line and the labels (the next visit counts
from this one); **Forget my last visit** deletes what the device remembered. Nothing shows on a first visit, in a
private window, when the browser blocks site data, or when nothing new has arrived. The date is in Central time
("earlier today" for the same day; the year for another year). The count covers every entry on the page, whatever
the type filter shows (a magazine issue counts its stories, as the day headings do). A **visit** is What's New pages
opened less than 30 minutes apart, in English or Spanish, so a reload, Back or the other language keeps the labels.
"New" means new to this device: a video dated two weeks back but found today is new to someone who last came a
week ago; a bulletin post scheduled for a later day counts from that day. Nothing is sent anywhere. Nothing to set.

For maintainers: the browser keeps one entry, `localStorage "gv-wn-seen"` = `{ upto, last, base }` — `upto` the
newest entry's first-seen second shown on this device, `last` when What's New was last open (also saved when the
page is left or put in the background), `base` the visit before, `{ upto, at }`, or `null`; 30 minutes or more
starts a new visit. The line is filled in by a small script right after it in `src/pages/whats-new.njk`, before the
feed is drawn, so nothing moves. Each entry carries `data-seen` (`eleventy/filters/community.js` `wnSeenOf`: its
`first_seen`, not its news date); the buttons and the visit's time
are `src/assets/js/community.js` (`sinceDone`, `watchVisit`). Tests: `tests/test_r12_u8_whatsnew.py`, browser check
`WhatsNewSince` (`tests/browser/test_r12_u8_whatsnew_browser.py`).

### Calendar files: story deadlines and reminders

**The story deadlines calendar.** Every open story deadline of AA Grapevine and La Viña, in one calendar a member
subscribes to once: `https://neta65.github.io/aagrapevine/deadlines.ics` (Spanish:
`https://neta65.github.io/aagrapevine/es/deadlines.ics`). Each deadline is an all-day entry on its day ("Story
deadline: “Emotional Sobriety” — Grapevine"), with its issue and a link to Share your story, and one reminder at
9 AM the day before. It updates itself after every site update: when a magazine adds, moves or drops a theme, the
subscribers' calendars follow. The magazines' suggested topics have no date, so they are not in it. Where people find
it:

- **Share your story** (`/contribute/#deadlines-calendar`): under the deadline cards, **Get the deadlines in your
  calendar** — the same three set-up rows as the Events page's *Subscribe to the calendar* card (Google Calendar,
  iPhone / iPad / Mac, Outlook), **Copy calendar address**, and the other language's address. Its notes: "Google
  Calendar ignores the reminders inside calendar files: in its settings, open this calendar and add a notification
  for all-day events." and "To keep the reminders, turn off “Remove Alerts” when you subscribe." The card shows
  while at least one deadline is open.
- Beside each deadline on Share your story: **Add to my calendar** (Google Calendar, Outlook.com, "Apple / Outlook
  (.ics file)") adds that one deadline; it has the same ID as in the subscribed calendar and the month files, so
  adding it twice never makes a copy.
- **Home** ("Write for the magazines": **Story deadlines in my calendar**) and **What's New** ("Stay in the loop":
  **Story deadlines calendar (.ics)**, with a copy button).

**One reminder in every "Add to calendar" file.** Each calendar file a member downloads or adds now carries one
reminder: **1 hour before** a timed or online event (the committee meeting, a workshop, a weekly open meeting),
**9 AM the day before** an all-day event or a story deadline (the member's own time). The reminder's text is the
event's title only; the Zoom link, meeting ID and passcode stay in the description. Files with it: "Add to
calendar → Apple / Outlook (.ics file)" on Events, Meetings and Home; the weekly open meetings' files
(`/meetings/weekly-open-gv.ics`, `-lv.ics`); each month's file (`/monthly/YYYY-MM/…ics`); the deadlines calendar and
each deadline's file. **Not** in the subscribed events calendar (`/events.ics`), on purpose: a subscriber would
get about ninety alarms. The Tracker's "End dates for my calendar" keeps its own reminder. Every "Add to calendar"
menu says so in one line: "The .ics file comes with a reminder 1 hour before. Google Calendar skips it and uses
your own notification settings." (or "… at 9 AM the day before …"). Nothing to set.

For maintainers: the deadlines are `eleventy/filters/monthly.js` (`storyDeadlines`, `deadlineEntry`,
`openDeadlines`, `deadlinesIcs`; the menus' entries `mpDeadlineCals`), the file `src/pages/deadlines-ics.11ty.js`
(not a page: out of the sitemap and the search; the service worker never keeps it), the card `committee.js`
`{% cmSubscribe lang, site, "deadlines" %}`, the menu `contribute.njk` `dlCalMenu` + `src/assets/js/read.js`. A
deadline's UID is `deadline-<theme id>[-es]@neta65-gvlv` in both the month files and the calendar. The one
reminder is `eleventy/central-time.js` `icsAlarm` / `alarmText` (the browser runs the same code as
`window.GVTime`), used by `committee.js` `buildIcs` (`alarms: true`), `weeklyIcs` and `app.js` `GV.icsText`;
`alarmText` keeps a passcode or meeting-ID value out of the reminder even if a title holds one. A file with nothing
in it (no deadline open) still holds the time zone, so it stays a valid calendar.

### New to AA? (Meetings, the 404 page, Home)

People sometimes reach the site looking for help — from a search or a QR poster, often on a phone, often in
Spanish. The **New to AA? / ¿Eres nuevo en AA?** card points them to **any** AA meeting, through AA only:

- **Meetings, at the top** (`/meetings/#new-to-aa`, before the committee meeting): a short welcome ("If you want to
  stop drinking, or just want to know more, AA welcomes you. …"), a line saying the page lists only Grapevine and
  La Viña meetings and our committee's monthly meeting, then **On aa.org** — *Find AA near you*, *Is AA for you?*
  (AA's twelve questions) and the *Meeting Guide app* (aa.org's Spanish pages on `/es/`) — and **AA offices in our
  Area**: one button per office (Dallas Intergroup, Fort Worth AA Central Office, AA Central Service Office Tyler,
  Alcohólicos Anónimos Dallas, District 71 AA), then the Area 65 site. On `/es/`, Alcohólicos Anónimos Dallas comes
  first; an office whose site is in the other language has a small "ES" or "EN" tag. Read aloud reads the offices
  by name.
- **The "page not found" page** (`/404.html`, `/es/404.html`): a short version in both languages (the page's own
  first), with the three aa.org links and **AA offices in our Area →** to the full card. GitHub Pages answers every
  missing address with the root `/404.html`, a broken Spanish link (`/aagrapevine/es/…`) too: there the Spanish
  card comes first (a tiny script in the page, before it shows; without JavaScript the English one stays first).
- **Home:** one line near the end, before the "For GVRs, RLVs & districts" band — "New to AA? AA's own sites list
  the AA meetings near you, in English and in Spanish. First steps →".

No phone numbers (nothing to keep current), no outside services and no clinical wording. The site search finds
the Meetings page for *help*, *new to AA*, *newcomer*, *Meeting Guide*, *intergroup* (*ayuda*, *nuevo en AA*,
*recién llegado*, *intergrupo* on `/es/`). **Settings** (optional to touch): `links:` → `aa_find`,
`aa_is_aa_for_you`, `aa_meeting_guide` and their `_es` twins (deleting one hides that link, and the Code check goes
red); the offices are the `meetings:` → `feeds` entries with `in_area: true` and a `site:` (in the file's order, the
`lang: es` ones first on `/es/`; never the `feed` address); the Area's site is `site:` → `area_website`. Details:
how-to/settings.md [§3.11 `links:`](how-to/settings.md#311-links--official-links-used-across-the-site) (the three
aa.org links) and [§3.9 `meetings:`](how-to/settings.md#39-meetings--grapevine-meetings-near-us) (the offices). For
maintainers: `src/_includes/macros/ui.njk` (`newcomerCard`, `newcomerLine`), `eleventy/filters/newcomer.js`
(`ncOffices`), `src/_i18n/common.json` (`newcomer.*`), `tests/test_r12_u6_newcomers.py`.

### The GVR / RLV corner: Pass it on and the question of the day

**Pass it on: from one rep to the next** (`/gvr/#pass-it-on`, and a **Pass it on** / **Pásalo** chip in the page's
"On this page" row) sits after *Ideas for your home group*. Three numbered cards, one for each moment of a rep's
term:

1. **Our group needs a GVR or RLV** — a one-minute announcement for the group's business meeting (or to send to
   members): what the service position is, that any member willing to help can serve, that the group conscience
   decides how the rep is chosen and for how long, an invitation to speak up after the meeting, and the corner's
   address. **Copy**, **Share** (on devices with a share sheet) and **Print a half-sheet**: one Letter page with the
   announcement twice, to cut along the dashed line, each half with a QR code to the corner.
2. **Welcome a new rep** — a message to paste into an e-mail or a text when the new GVR or RLV says yes: both
   registration links (La Viña's first on `/es/`), the **next committee meeting's date and time** (it moves on by
   itself after each meeting), GVR / RLV 101, the corner's first steps and the committee's e-mail. **Copy**,
   **Share**.
3. **Handing over your service position** — four short tips for the rep rotating out, **Print the handover
   sheet**, a link to the Tracker's subscriptions (when the group's subscription ends), and **Tell the office**: two
   buttons that open a ready-made e-mail in the visitor's own mail app, one to the Grapevine office and one to La
   Viña, asking to update their list of reps, with blank lines for the group's name, city and state, service
   number and district (the Area line comes filled in from `site.area` / `area_es`: "Northeast Texas Area 65").
   Nothing is sent from the site.

The **handover sheet** is one Letter page to fill in by hand: the group, the magazines and copies, when the
subscription ends and how it is renewed, where the copies and table supplies are kept, the order forms, the district
meeting, our committee meeting (from the settings), where the new rep registers, a "Tell them" checklist and lines
for notes, with a QR code to the corner. No names anywhere (no name fields, no names in the messages); the words
invite and never press — each group chooses its own rep. The browser's own Print still prints the page as before;
the two sheets print only from their buttons. **Settings:** `config/site.yml` → `links:` → `gvr_office_email`
(`gvrc@aagrapevine.org`) and `rlv_office_email` — **a draft:** `preguntas@aagrapevine.org` is AA Grapevine's
Spanish help address, not one La Viña names for RLV changes; put La Viña's own address there if it names one (any
valid e-mail address works; the Code check alone checks these two, so a change never stops the site from
publishing). It also uses `meeting:` and `links:` → `gvr_register`, `rlv_register`.

**Did you know? / ¿Sabías que…?** — one question a day from the booth display (the quiz, true-or-false and fill-in
rows of `content/booth/booth.csv` that are on, inside their `from` / `until` dates and complete in the page's
language; rows that mention `{event}`, rows that speak as the table — "this table", "Like this one!", "Ask us", "esta
mesa", "¡Como esta!", "Pregúntanos", in either language — and rows whose `web` column says `no` stay at the booth). It
is on **About** (under the history timeline) and at the end of *Ideas for your home group* on the corner ("something
to share in your group's announcements"), where it shares one row with **Short videos to share at your group**:
the About page's two videos about the magazines (`config/site.yml` → `site:` → `about_videos`; the page language's
magazine first), compact — the player (only the preview picture until it is played, nothing with Data saver), the
magazine, the language, the length and the title (on the other-language page our translated title under it) — with a
link to their full cards on About. Side by side from about 1180px (1360px at the first larger text size), the
question in the middle of its card until it is answered; one under the other on smaller screens and at larger text;
without the question card (no JavaScript) the videos take the whole row, and a single video (an entry with no title
is skipped) takes the whole card under the heading "A short video …". Neither is printed. The visitor taps
an answer (or "Show the answer"); the card says whether it was right, shows the row's explanation and its source
line, the row's `credit_*` — a link to `source_url` only when that is an https:// address on an AA site (aa.org,
aagrapevine.org, aalavina.org, neta65.org) or this site (a row with no credit then shows the link as "Source" /
"Fuente"), plain text otherwise. **Another question** brings up to three
more of that day's. No scores, no streaks, nothing saved, never called a quiz; on `/es/` La Viña's questions come
first. The questions change at midnight Central even without a new build and in a page saved for offline use: each
build puts only the next 7 days' questions (4 a day) into the page. Needs JavaScript; not printed. Guide to the rows:
[content/booth/README.md](content/booth/README.md#the-question-of-the-day-on-the-website).

For maintainers: `src/pages/gvr.njk` (`#pass-it-on` and the two printouts), `src/assets/js/read.js` (`gvrPass`,
`dailyQuestion`), `src/_includes/macros/question.njk`, `src/_includes/macros/media.njk` (`magVideo`: the videos'
card, About's and the corner's compact one; `src/assets/css/areas/read.css` `.read-dyk-row`, `.read-vid-c`),
`eleventy/filters/booth.js` (`dailyQuestions`, `DAILY_DAYS`, `DAILY_PER`, `boothOnly`, `BOOTH_VOICE`, `csvColumn`,
`SOURCE_HOSTS`, `csvSources`), the words `src/_i18n/read.json` (`read.gvr.pass_*`, `read.gvr.hs_*`, `read.gvr.vid_*`)
and `booth.json` (`booth.dyk.*`); browser checks `PassItOn`
(`tests/browser/test_r12_u5_gvr.py`) and `StartCards`, `VideosBesideQuestion` (`tests/browser/test_r13_u2_gvr.py`).

### The committee meeting's paperwork (Agenda & minutes)

The monthly committee meeting's slides (GVR / RLV 101 → Presentations → the committee meeting; the player is
`/orientation/?present=committee-meeting`) have a tab in **Customize**: **Agenda & minutes** (Spanish: **Agenda y
acta**). Only that deck has it (a deck has it when its file has a `paperwork:` block). It makes the chair's monthly
paperwork from what is typed in **Customize → Your details** and from the site's own facts (the meeting's date and
time, Zoom ID and passcode, the phone number):

1. **Agenda e-mail** — for the *next* meeting: date and time, Zoom and phone details, the agenda's times (from
   the version of the agenda slide chosen), last month's minutes, old and new business, the order of the district
   reports, the Zoom / no-photos reminder and a signature.
2. **Reminder** — a short note for an e-mail or a group chat: the date, time and Zoom and phone details in English,
   then a paragraph in Spanish with the date, time, Zoom meeting ID and passcode (no phone line) that also says
   the meeting is in English ("La reunión es en inglés"); then the link to the meeting's details and the
   signature.
3. **Draft minutes** — for the *last meeting held*: an outline with the chair and minutes-taker **by service
   position**, "Attended: about ___ members", every part of the meeting with what was typed, the action items and
   the next meeting. Service positions and counts only: no names, phone numbers or e-mail addresses, and no
   attendance list. Make it right after the meeting.

Each text has **Copy**, **Copy the subject** and **Open in my e-mail** (the chair's own e-mail app opens with no
address: every address goes in BCC). A long text is copied first and the e-mail opens with "(Paste the text here:
it's on your clipboard.)"; if the browser won't let the page copy, no e-mail opens and the page says to copy the
text by hand. The minutes also have **Print** (named with the meeting's date; the print window can save a
document). A line whose details are all blank is left out; a blank left empty beside a filled one shows in
[brackets].

4. **Start next month** — after the meeting, once the minutes are drafted. The chair ticks what to carry (the
   night's action items come ticked; old business still open comes unticked; up to 4, the deck's old-business
   lines): they become next month's **old business**; the details that were for that meeting only are cleared;
   the presenter, the order of districts, the treasurer's budget and reimbursement process and the phone passcode
   are kept (the panel lists them); the minutes' month moves on, the week-before checklist (Customize → Prepare) is
   unticked, and the agenda and reminder move on to the next meeting. It asks first, and **Undo “Start next
   month”** stays until the next meeting begins.

Everything stays on the chair's device; nothing is sent from the site and no e-mail address is stored. The texts
are in English like the slides; the buttons are in the page's language. **To change the wording**, edit
`config/presentations/committee-meeting.yml` under `paperwork:` (what "Start next month" clears is its `clear:`
list), then run the checker: `.venv\Scripts\python.exe tests\test_presentations.py
config\presentations\committee-meeting.yml`. What the texts may hold (`{fill:…}`, `{live:…}`, `{paper:…}`) is
explained in the comment just above `paperwork:` in that file; the decks in general:
[how-to/presentations.md](how-to/presentations.md). If the meeting rule or a skipped date changes in
`config/site.yml` → `meeting:`, the paperwork follows by itself. For maintainers: `eleventy/filters/presentations.js`
(the deck JSON's `paperwork`), `src/assets/js/presentations-core.js` (`paperText`, `paperMeetings`,
`nextMonthPlan` / `startNextMonth` / `undoNextMonth`; the stored state's per-deck `prev`, what the Undo puts back,
never in a saved "my version" file), `src/assets/js/presentations.js`, `tests/test_r12_u9_meeting.py`.

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
| [wasm-media-encoders](https://github.com/arseneyr/wasm-media-encoders) | MP3 files from the story recorder (Share your story): LAME compiled to WebAssembly | MIT |
| [LAME](https://lame.sourceforge.io) | The MP3 encoder inside it (LAME 3.100) | LGPL-2.0 or later |
| [Lucide](https://lucide.dev/) | Icons | ISC |
| [Inter](https://rsms.me/inter/) and [Fraunces](https://github.com/undercasetype/Fraunces) via [Fontsource](https://fontsource.org/) | Fonts (self-hosted) | SIL OFL 1.1 |
| [markdown-it](https://github.com/markdown-it/markdown-it), [js-yaml](https://github.com/nodeca/js-yaml), [node-qrcode](https://github.com/soldair/node-qrcode) | Text formatting, settings, QR codes | MIT |

**Daily content sync**

| Tool | Used for | License |
|---|---|---|
| [Requests](https://requests.readthedocs.io/) | Fetching pages | Apache-2.0 |
| [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) | Reading web pages | MIT / BSD-3 |
| [Protego](https://github.com/scrapy/protego) | Obeying robots.txt and crawl delays; checking the root robots.txt (weekly link check) | BSD-3 |
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
