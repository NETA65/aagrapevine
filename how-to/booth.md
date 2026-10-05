# The booth display: the show at our table

> Part of the [how-to guide](README.md). This page is the whole story of the **booth display**: a show that plays by
> itself on a TV, laptop or tablet at the committee's Grapevine / La Viña table. It covers using it at an event,
> changing it on the spot, every setting, what the show is made of, the Drive booth folder's naming convention, the
> CSV with the quizzes and facts, offline use, troubleshooting, and where to change the code. The About page's
> "How to use it at a booth" box links here.

**Contents**

1. [What it is](#1-what-it-is)
2. [Quick start at an event](#2-quick-start-at-an-event) —
   [the night before](#21-the-night-before-with-internet) ·
   [at the table](#22-at-the-table) ·
   [lock the device to the show](#23-lock-the-device-to-the-show) ·
   [when the event is over](#24-when-the-event-is-over)
3. [Change it at a moment's notice](#3-change-it-at-a-moments-notice) —
   [quick controls and presets](#31-from-the-about-page-quick-controls-and-presets) ·
   [keys](#32-while-it-plays-the-keys) ·
   [the 3-second hold](#33-on-a-touch-screen-the-3-second-hold) ·
   [the PIN](#34-the-pin) ·
   [the start link](#35-one-link-for-every-device-the-start-link)
4. [Every setting, tab by tab](#4-every-setting-tab-by-tab) —
   [Event](#41-event) · [Show](#42-show) · [Slides](#43-slides) · [Timing & sound](#44-timing--sound) ·
   [Screen](#45-screen) · [Kiosk](#46-kiosk) · [Offline](#47-offline) · [Share & reset](#48-share--reset) ·
   [presets](#49-the-five-presets) ·
   [what the device keeps](#410-what-the-device-keeps-and-what-is-never-sent) ·
   [the site's starting settings](#411-the-sites-starting-settings-configsiteyml)
5. [What the show contains](#5-what-the-show-contains) —
   [three sources](#51-three-sources) · [the channels](#52-the-channels) ·
   [the live channels](#53-the-live-channels) · [welcome and about](#54-the-welcome-and-about-slides) ·
   [languages](#55-languages-on-the-screen) · [how the next slide is chosen](#56-how-the-next-slide-is-chosen) ·
   [how long a slide stays](#57-how-long-a-slide-stays)
6. [Visitor mode](#6-visitor-mode) —
   [what visitors can do](#61-what-visitors-can-do) · [Quiz me](#62-quiz-me) ·
   [when nobody touches it](#63-when-nobody-touches-it) · [privacy](#64-privacy)
7. [Photos, videos, sound and notes from Drive](#7-photos-videos-sound-and-notes-from-drive) —
   [quick start](#71-quick-start-put-a-photo-on-the-booth) ·
   [the folder and its collections](#72-the-booth-folder-and-its-collections) ·
   [the naming convention](#73-the-naming-convention) · [every option](#74-every-option) ·
   [examples](#75-examples) · [file types](#76-file-types) ·
   [never shown, and problems](#77-what-is-never-shown-and-the-problem-list) ·
   [offline copies](#78-the-offline-copies-of-drive-files) ·
   [check that a file arrived](#79-check-that-a-file-arrived) · [AA rules](#710-aa-rules-for-the-folder)
8. [Editing the CSV](#8-editing-the-csv) —
   [on GitHub](#81-edit-it-on-github) ·
   [in Excel or Sheets](#82-edit-it-in-excel-google-sheets-or-libreoffice) ·
   [every column](#83-every-column) · [every type, with a real row](#84-every-type-with-a-real-row) ·
   [languages](#85-languages) · [links and QR codes](#86-links-and-qr-codes) ·
   [placeholders](#87-placeholders) · [off, weights, dates](#88-switching-a-row-off-weights-and-dates) ·
   [refused words](#89-words-the-booth-never-shows) · [mistakes](#810-how-mistakes-are-reported) ·
   [AA rules](#811-aa-rules-for-the-content) · [check before an event](#812-check-before-an-event)
9. [Offline and updates](#9-offline-and-updates)
10. [Troubleshooting](#10-troubleshooting)
11. [Going further: change the code](#11-going-further-change-the-code) —
    [how the pieces fit](#111-how-the-pieces-fit) · [code map](#112-code-map) ·
    [a new CSV column](#113-recipe-a-new-csv-column) · [a new slide type](#114-recipe-a-new-slide-type) ·
    [a new live channel](#115-recipe-a-new-live-channel) ·
    [the scheduler's rules](#116-recipe-change-the-schedulers-rules) ·
    [colours and words](#117-recipe-change-the-colours-or-the-words) · [tests](#118-tests-to-run)
12. [See also](#12-see-also)

---

## 1. What it is

The booth display is a section of the About page that turns any screen with a web browser into a show for the
committee's table at assemblies, conventions and workshops. Press **Start the booth** and it fills the screen and
plays by itself, all day: quizzes whose answer shows after a few seconds, true or false, facts and history, quotes,
fill in the blank, word scrambles, polls, "Let's talk" questions, messages and QR codes, official videos, the
committee's own photos and posters, and the site's live news (the next events and a countdown to the next
assembly, the daily quotes, story themes and deadlines, prices, the Books of the Month, meetings anyone can join,
the newest bulletin posts) — in English, Spanish, both, or one then the other. Visitors can tap it to answer a
question, vote, play a short quiz or scan a QR code to take the site home.

Opened once with internet, it saves itself on the device and keeps playing with no connection. Everything about it
can be changed at the table in a few seconds — the event's name, the language, what to include or leave out — and
those changes stay on that device only. What it shows comes from three places: **one CSV file** in the repository
(`content/booth/booth.csv`, the committee's quizzes, facts, quotes and video links), the **booth folder** of the
Drive panel folder (photos, videos, sound files, short notes) and the site's own data (the live channels).

**Where it is** (full addresses start with `https://neta65.github.io/aagrapevine`):

| What | English | Spanish |
|---|---|---|
| The section on the About page (in its "On this page" bar: **Booth display** / **Pantalla para la mesa**) | `/about/#booth` | `/es/about/#booth` |
| Open the page and start the show at once | `/about/?booth=start` | `/es/about/?booth=start` |
| The same with a setup in it (the link from Settings → Share & reset or Kiosk) | `/about/?booth=start&bs=…` | `/es/about/?booth=start&bs=…` |
| The show itself: one file for both languages, rebuilt with every deploy | `/about/booth.json` | — |
| The saved copies of the Drive folder's photos, videos and sounds | `/about/booth/media/<file>` | — |

The About page itself is linked as **About us** (Spanish: **Quiénes somos**) at the bottom of every page and in
the phone menu's "More".

**What the section looks like.** Under the heading "A booth display for our table" (eyebrow: "For our table at
assemblies and events") there is a 16:9 preview card that cycles a few real slides, small and silent, while it is
on screen; a **Set it up** card with the quick controls (Event name, Name in Spanish (optional), Language on the
screen, Preset) and three buttons — **Start the booth**, **Settings**, **Preview here** —; three status chips; and a
closed box **How to use it at a booth** with seven steps, the AA rules in one line and the link to this page. On
`/es/about/` the same words are in Spanish ("Prepárala", "Iniciar la pantalla", "Ajustes", "Ver aquí").

**Today** (October 3, 2026) the show holds 293 slides: the CSV's 246 rows that are switched on, 47 live items and
no Drive file yet (the booth folder is still empty). The first chip says **284 slides in the show**: with the
starting settings the 10 sound slides (4 podcast rows of the CSV, 6 live podcast episodes) wait for the sound to be
turned on, and the player adds its own "about" slide.

**Who can do what**

| You want to | Who can | Where |
|---|---|---|
| Run it at a table, change its settings, set a PIN | anyone with the device in hand (the changes stay on that device) | the About page, the player's Settings ([section 4](#4-every-setting-tab-by-tab)) |
| Add photos, posters, videos, sound files, short notes | anyone with Editor access to the Drive panel folder | the panel folder's `booth` folder ([section 7](#7-photos-videos-sound-and-notes-from-drive)) |
| Add or change quizzes, facts, quotes, polls, messages, QR codes, video links | anyone with write access to the GitHub repository (the MKP715 login is enough) | `content/booth/booth.csv` ([section 8](#8-editing-the-csv)) |
| Change every device's starting settings, or the size of the offline copy | write access to the repository | `config/site.yml` → `booth:` ([4.11](#411-the-sites-starting-settings-configsiteyml)) |
| Change how it works | write access, and a PC to test on | the code ([section 11](#11-going-further-change-the-code)) |

---

## 2. Quick start at an event

### 2.1 The night before, with internet

Do this on the very device (and in the very browser) that will run the show: each browser keeps its own offline
copy and its own settings. On an iPad that will use a Home Screen icon, do it from the icon
([2.3](#23-lock-the-device-to-the-show)).

1. Plug the device in and connect it to the internet.
2. Open `https://neta65.github.io/aagrapevine/about/#booth` (or `/es/about/#booth` for Spanish menus and Spanish
   first). The chips under the buttons say, for example, **284 slides in the show**, **Content as of October 3,
   2026** and **Not saved for offline yet**.
3. In **Set it up**, type the **Event name** — `NETA 65 Spring Assembly` — and, if it differs, the **Name in
   Spanish (optional)** — `Asamblea de Primavera de NETA 65`. A blank Spanish name means Spanish slides use the
   English one. Choose the **Language on the screen** (**Both** for an assembly) or a **Preset** ("Assembly — both
   languages", "Spanish-speaking event" …). Another way: **Settings** → **Event** → **Pick from the upcoming
   events**, which fills both names and the second line from the site's calendar.
4. Press **Start the booth**. The show fills the screen; with an event name set it opens with the welcome slide
   ("Welcome!", the event's name, "Grapevine and La Viña — ask us anything"). At the top right a chip shows
   **Saving for offline 2 of 3** and then **Ready offline ✓** for a few seconds (it counts the two About pages, the
   show and every saved Drive file).
5. To be sure: press **S** (or hold the event's name for 3 seconds), tab **Offline**. The line reads **Ready
   offline: 1 files · 519.3 KB · saved Oct 3, 8:33 AM** today. It counts the show file and the saved Drive copies
   (the two About pages are kept with the site's saved pages) — one file today, because the booth folder is empty;
   with Drive photos and videos it reads like *Ready offline: 14 files · 86.2 MB · saved …*.
6. Optional: tab **Kiosk** → **Address that starts the show** → **Copy**, and bookmark that address on this device.
   It opens the About page and starts the show at once, with this setup ([3.5](#35-one-link-for-every-device-the-start-link)).
7. Leave with **Esc** → **Leave the booth display?** → **Leave** (on a touch screen: Settings → **Leave the show**
   at the bottom). The page's third chip now says **Ready offline**.
8. Optional test: turn the Wi-Fi off, reload the About page and press Start. It plays from the saved copy; the chip
   says **You're offline · Ready offline**. Videos from YouTube and the podcast are left out quietly offline: they
   always need internet ([9.2](#92-what-plays-offline-and-what-needs-internet)).

How long it takes: with today's show, a few seconds. With a booth folder full of videos the first save can take
minutes (up to 400 MB); the show plays meanwhile, and the save goes on by itself until every file is in. Files added
to the Drive folder after this save are not on the device until it saves again with internet — so add them at least
one site update before the night before ([7.8](#78-the-offline-copies-of-drive-files)).

### 2.2 At the table

1. **Power.** Plug the device in. A TV: connect the laptop by HDMI and set the laptop to stay on with its lid
   closed if you close it.
2. **Never sleep.** Set the device's own screen timeout to "Never" ([2.3](#23-lock-the-device-to-the-show)). The
   booth also asks the browser to keep the screen on: Settings → **Kiosk** → **Keep the screen on** (on by
   default) says **The screen stays on while the show plays.** when the browser agrees.
3. **Open and start.** Open the About page (the bookmark works offline) and press **Start the booth**, or open your
   start link. A start link opens the show without a tap, so the browser keeps it out of full screen and silent
   until someone taps: the chip **Tap for full screen & sound** says so. Tap once.
4. **Full screen.** **Start the booth** asks for full screen by itself (Settings → Kiosk → **Full screen when the
   show starts**). **F** switches it on and off; Settings → **Screen** has a **Full screen** button (in a browser
   that has full screen: not on an iPhone or iPad, [2.3](#23-lock-the-device-to-the-show)).
5. **PIN.** Press **S** → **Kiosk** → type 4 digits under **4-digit PIN to open the settings or leave** → **Set the
   PIN** → toast **PIN set.** From now on Settings and leaving ask for it; visitors can still play
   ([3.4](#34-the-pin)).
6. **Sound.** The show starts silent. To play the videos' sound, the sound files and the podcast: Settings →
   **Timing & sound** → **Play sound**, or press **M** (screen readers hear "Sound on"). A browser plays sound only
   after someone has tapped or clicked the page once.
7. **Look.** In a bright hall: Settings → **Screen** → **Daylight — for bright rooms**. Readers far away: **Text
   size** → **Large**. A TV that cuts the edges: **Safe margin for TVs that cut the edges (5%)**.
8. **Try it.** Tap the screen: the visitors' bar comes up (Back · Pause · Next · Quiz me · English · Español · Both
   · Take it home). Leave it alone for 40 seconds: the bar goes and the show goes on by itself.
9. **Lock it** to the browser and turn notifications off ([2.3](#23-lock-the-device-to-the-show)).

### 2.3 Lock the device to the show

The PIN stops visitors from changing the booth's settings or leaving the show with its own controls. It cannot stop
the device itself: a swipe from a screen edge, a notification, or a tap on YouTube's own title or logo in a playing
video (YouTube's rules keep those links clickable, and the booth cannot switch them off) can take the screen away
from the show. Each kind of device has a way to stay in the browser. Try it once at home before an event.

| Device | Keep it in the show | Keep the screen on | No interruptions |
|---|---|---|---|
| **Windows laptop (Edge or Chrome)** | Simplest: **Start the booth** (full screen) with a PIN. A stray tap that opens YouTube in a new tab: close that tab (Ctrl+W) and press **F** to fill the screen again. Locked down: **Edge kiosk mode**, a desktop shortcut whose target is `"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --kiosk "https://neta65.github.io/aagrapevine/about/?booth=start" --edge-kiosk-type=fullscreen --no-first-run` (one window, no address bar or tabs; **Alt+F4** closes it). Microsoft documents kiosk sessions as private (InPrivate): settings and the offline copy last only while that window is open, so start it while online, and put your setup in the address (the start link of [3.5](#35-one-link-for-every-device-the-start-link)). Test it at home — start it, cut the internet, let it run an hour — before you count on it offline | Settings → System → Power (& battery) → the screen and sleep times → "Never" when plugged in; for a closed lid on a TV, Control Panel → Power Options → "Choose what closing the lid does" → "Do nothing" | Settings → System → Notifications → **Do not disturb** on; pause Windows Update for the day |
| **iPad (Safari)** | **Guided Access**: Settings → Accessibility → Guided Access → On, set a passcode; open the booth, triple-click the top (or Home) button → **Start**. Triple-click and the passcode end it. For a page without Safari's bars: Share → **Add to Home Screen**, and run the show from that icon — the icon opens the site's home page, so go to About us → Booth display. The icon keeps its **own** settings and offline copy, apart from Safari: do the night-before steps from the icon | Settings → Display & Brightness → **Auto-Lock** → Never (Guided Access has its own "Display Auto-Lock" setting too) | Control Center → Focus → **Do Not Disturb** |
| **Android (Chrome)** | **App pinning** (also called screen pinning): Settings → Security (on some phones Security & privacy → More security settings) → App pinning → On; open the booth, open the recent-apps view, tap the app's icon on its card → **Pin**. To unpin: hold Back and Overview (or swipe up and hold, with gesture navigation). Chrome's menu → **Add to Home screen** / **Install app** gives a window without the address bar | Settings → Display → **Screen timeout** → the longest; or Developer options → **Stay awake** (while charging) | Quick settings → **Do not disturb** |
| **A smart TV's own browser** | not recommended: many TV browsers cannot keep an offline copy or play the videos. Use a laptop or a tablet with HDMI | — | — |

On an iPhone or iPad, or any browser without a full-screen function, Settings → Kiosk shows the tip **iPhone and
iPad: Share → Add to Home Screen, then open the site from there to fill the screen.** The installable app and its
steps are on the site's "Saved pages & app" page (`/offline/`).

A wireless presenter remote works as Back and Next when it sends the ← and → keys (many send Page Up and Page Down,
which the booth does not use).

### 2.4 When the event is over

1. **Esc** → the PIN, when one is set → the show closes and the About page comes back. With a PIN, the right PIN
   leaves at once; without one, the box **Leave the booth display?** asks first (**Leave** / **Keep playing**). On a
   touch screen: the 3-second hold (the PIN, when one is set, opens Settings) → **Leave the show** at the bottom of
   Settings → **Leave the booth display?** → **Leave**.
2. The offline copy stays on the device for the next event; opening the About page with internet there and
   starting the show brings it up to date.
   To free the room: Settings → **Offline** → **Remove the offline copy** ([9.5](#95-remove-the-offline-copy)).
3. Poll votes stay too ("3 votes at this table"). For a fresh count at the next event: Settings → **Share &
   reset** → **Reset the poll votes**.
4. To hand the device to someone else with the site's own settings: Settings → Share & reset → **Reset the
   settings** (this also removes the PIN).

---

## 3. Change it at a moment's notice

Every change applies at once — the slide on screen is redrawn in the new language straight away — and stays on that
device: the next time the show starts there, it starts the same way. Other devices are not touched (use the start
link of [3.5](#35-one-link-for-every-device-the-start-link) to copy a setup).

### 3.1 From the About page: quick controls and presets

The **Set it up** card changes the same settings as the player's Settings, without starting the show:

| Control | What it sets | Example → result |
|---|---|---|
| **Event name** (at most 80 characters) | the name at the top of the screen and on the welcome slide | `NETA 65 Spring Assembly` → top left of every slide; the welcome slide every 12 slides |
| **Name in Spanish (optional)** | the name on Spanish slides | `Asamblea de Primavera de NETA 65` → shown on Spanish slides; in Both, under the English one |
| **Language on the screen** | English · Español · Both · Alternate ([5.5](#55-languages-on-the-screen)) | **Español** → Spanish slides only, and pictures without words |
| **Preset** | one of the five presets ([4.9](#49-the-five-presets)); the box goes back to "Choose one…" | "Quiet room" → toast **Preset applied: Quiet room**; no sound, calm pace, no animations |

The three buttons: **Start the booth** (the show, full screen); **Settings** (the show opens with Settings beside it,
on the Event tab, without full screen — and without asking for the PIN: the PIN only guards the show itself);
**Preview here** (the show plays inside the preview card, small and silent; its own buttons **Pause the preview**,
**Next slide**, **Stop the preview**).

The three chips under them:

| Chip | Says | Means |
|---|---|---|
| slides | **284 slides in the show** (**1 slide in the show** for one) | how many slides can show on this device now, with its settings, the date and the connection — the sound slides are never counted here, even with the sound on (the page plays no sound: they play only in the show itself) |
| content | **Content as of October 3, 2026** | the day the show file was built (the live items are as fresh as that) |
| offline | **Ready offline** · **Saved for offline: 9 of 14 files** · **Not saved for offline yet** · **This browser can't keep an offline copy** · **You're offline** (· **Ready offline**) · **Reload the page to finish updating the site, then start the booth again.** · while a save runs, **Saving for offline 23 of 86** | the device's offline copy ([section 9](#9-offline-and-updates)) |

Before the show file is loaded the first chip says **The show loads when you start it**; while it loads,
**Loading the show…**; when it cannot be loaded, **The show couldn't be loaded. Check the connection and try again.**

### 3.2 While it plays: the keys

On a laptop or with a keyboard. The keys do nothing while you type in a field or work in the Settings panel; Esc
always works.

| Key | Does | Notes |
|---|---|---|
| **S** | opens Settings | asks for the PIN first when one is set |
| **Space** | pause / play | the chip **Paused** shows at the top. With "Visitors can tap the screen to play" on (the default), a pause ends by itself after the idle time (40 s) like a visitor's |
| **→** | next slide | during a Quiz me round: shows the answer first, then the next question |
| **←** | the slide before | the screen keeps the last 30 |
| **F** | full screen on / off | |
| **M** | sound on / off | saved as the setting (Timing & sound → Play sound); says "Sound on" / "Sound off" to screen readers |
| **L** | the next language mode: English → Español → Both → Alternate → English … | saved as the setting; the language chip at the top right changes: `EN` · `ES` · `EN · ES` (Both) · `EN ⇄ ES` (Alternate) — Spanish first: `ES · EN`, `ES ⇄ EN` |
| **Q** | starts a Quiz me round ([6.2](#62-quiz-me)) | |
| **Esc** | closes what is open, one thing at a time: the PIN or "Leave?" box, "Take it home", Settings, a Quiz me round; with nothing open, asks before leaving | with a PIN, the PIN is the question |

Any other key from a visitor brings up the visitors' bar.

### 3.3 On a touch screen: the 3-second hold

There is no Settings button on the screen, so visitors cannot find it. To open Settings: **press and hold the
event's name** (top left; "Grapevine · La Viña" when no name is set) **for 3 seconds**. While you hold, the words
**Keep holding to open the settings** show. With a PIN, the PIN box comes first. **Leave the show** is at the bottom
of Settings, under every tab.

Settings left alone close by themselves after 2 minutes (or three idle times, if that is longer), and the PIN box
after the idle time — so a curious visitor's hold never leaves the show dimmed behind a panel all day.

### 3.4 The PIN

Settings → **Kiosk** → **PIN**:

1. Type 4 digits in **4-digit PIN to open the settings or leave**, then **Set the PIN** → **PIN set.** Anything
   but 4 digits → **A PIN is 4 digits.**
2. From now on, **S**, the 3-second hold and **Esc** show **Enter the PIN** with the line **The PIN opens the
   settings.** or **The PIN lets you leave the show.** A wrong PIN: **That's not the PIN. Try again.**
3. **Remove the PIN** (same place) → **PIN removed.**

What the PIN is and is not:

- It only keeps visitors from changing things. It is kept on the device **as typed**, not hidden (the panel says
  so: "It only keeps visitors from changing things; it is kept on this device as typed."). Do not reuse a PIN that
  matters elsewhere.
- Visitors can still do everything a visitor does ([section 6](#6-visitor-mode)).
- It never travels in a start link, and a start link opened on a device keeps that device's PIN.
- **Reset the settings** removes it.
- The About page's own controls do not ask for it — the **Settings** button there opens Settings directly. That is
  the way back in when the PIN is forgotten: leave the show by closing the browser tab or window, open the About
  page, press **Settings** → **Kiosk** → **Remove the PIN** ([section 10](#10-troubleshooting)).

### 3.5 One link for every device: the start link

Settings → **Share & reset** → **Link to this setup** (and the same address in Settings → **Kiosk** → **Address
that starts the show**), with a **Copy** button. Open it on another device — or bookmark it on this one — and the
About page opens and starts the show at once, with this setup.

How the address is made:

```text
https://neta65.github.io/aagrapevine/about/?booth=start&bs=eyJ2IjoxLCJzIjp7ImV2ZW50Ijp7ImVuIjoiTkVUQSA2NSBTcHJpbmcgQXNzZW1ibHkiLCJlcyI6IkFzYW1ibGVhIGRlIFByaW1hdmVyYSBkZSBORVRBIDY1In0sImxhbmciOiJlcyIsImZpcnN0IjoiZXMifX0
```

- `?booth=start` opens the show at once. Alone (`/about/?booth=start`) it starts with the device's own settings.
- `&bs=…` carries the setup: only what differs from the site's starting settings, coded so it fits in an address.
  The example above holds the event names "NETA 65 Spring Assembly" / "Asamblea de Primavera de NETA 65", the
  language Español and Spanish first (the "Spanish-speaking event" preset). A device with nothing changed gives
  `&bs=eyJ2IjoxLCJzIjp7fX0` — "no changes".
- The link is the page language's: made on `/es/about/`, it opens `/es/about/` (Spanish menus, Spanish first in
  Both).
- **Opening it replaces that device's settings** with the link's (only its PIN stays) and says **The settings from
  the link were applied.** It does so each time the link is opened: a bookmarked link always brings the device back
  to exactly that setup, whatever was changed at the table since.
- A link that was cut or mistyped changes nothing: **The settings in the link couldn't be read; this device's
  settings stay.**
- The PIN never travels in it.
- A setup too big for an address (many single slides switched off one by one; the code may be at most 2,048
  characters) gives the warning **This setup is too big to fit in a link (many slides switched off one by one), so
  the link starts the show with the site's settings. Set up the other device by hand.** — the link then has no
  `bs=`.
- Opened without a tap (a bookmark, a kiosk shortcut), the browser keeps the show silent and out of full screen
  until someone taps: **Tap for full screen & sound** (Spanish: **Toca para pantalla completa y sonido**).

---

## 4. Every setting, tab by tab

Open Settings with **S**, the 3-second hold or the About page's **Settings** button. The panel ("Booth settings":
"Changes apply at once and stay on this device.") sits beside the show on a wide screen and over it on a narrow
one; the show keeps playing. Its eight tabs, with the Spanish page's names:

| Tab | Spanish page | Holds |
|---|---|---|
| **Event** | Evento | the event's names, the second line, pick from the calendar, presets |
| **Show** | Contenido | language, which language first, magazines, what to show, Drive folders, topics, order |
| **Slides** | Diapositivas | every slide: search, on / off, why it can't show now, Show now; the problem list |
| **Timing & sound** | Tiempo y sonido | pace, seconds, video and sound limits, how often a video, sound, volume, captions |
| **Screen** | Pantalla | look, text size, motion, clock, corner QR code, progress bar, TV margin, full screen |
| **Kiosk** | Quiosco | PIN, visitors, idle time, Quiz me length, screen on, full screen, updates, offline saving, the start address |
| **Offline** | Sin conexión | the offline copy, Save now, Remove, connection, storage |
| **Share & reset** | Compartir y restablecer | the setup's link, the three resets |

Numbers take effect when you leave the field or press Enter, and are kept inside their range (type 500 where 120 is
the most, and 120 is kept).

### 4.1 Event

| Setting | Default | What it does |
|---|---|---|
| **Event name** | blank | big at the top left of every slide and on the welcome slide; `{event}` in the CSV's texts ([8.7](#87-placeholders)) |
| **Name in Spanish (optional)** | blank | the same on Spanish slides; blank = the English name |
| **Second line (date · place)** | blank | a smaller line under the name, for example `March 14 · Tyler, Texas` (up to 100 characters) |
| **Show the event name at the top** | on | off: the top shows "Grapevine · La Viña" and the committee's name, the welcome slide stops, and `{event}` reads "this event" |
| **Pick from the upcoming events** → **Upcoming event** | — | the next 12 events of `/events/` a booth could be at (not committee meetings, not online-only ones). Choosing one fills both names and the second line, and turns "Show the event name" on: toast **Filled in from the calendar: …** |
| **Presets** | — | five buttons, one tap each ([4.9](#49-the-five-presets)) |

Example of "Pick from the upcoming events": choosing **GV/LV booth at CityWide Dallas — Saturday, October 10, 2026**
gives the name "GV/LV booth at CityWide Dallas", the Spanish name "Mesa de GV/LV en CityWide Dallas" (only when it
differs) and the second line "Saturday, October 10, 2026 · Lover's Lane United Methodist Church" (the date in the
first language; the place up to its first comma). The list today (12 events): the Grapevine Writing Workshop in
Arlington, La Viña's workshops in Mansfield, Duncanville, Tyler and Longview, the monthly CityWide Dallas booth
(October to March) and the North Texas Zone gathering of January 29–31, 2027.

Without an event name the top of the screen shows **Grapevine · La Viña** (Spanish first: **La Viña · Grapevine**)
with the committee's name under it, and there is no welcome slide.

### 4.2 Show

| Setting | Default | What it does |
|---|---|---|
| **Language on the screen** | Both | English ("Slides in English, and pictures without words") · Español · Both ("Each slide in both languages, one under the other") · Alternate ("One slide in English, the next in Spanish") — [5.5](#55-languages-on-the-screen) |
| **Which language goes first** | English (on `/es/about/`: Español) | the language on top in Both, and the first one in Alternate; also the language of the visitors' bar, the clock and the corner QR code in those modes |
| **Magazines** → Grapevine, La Viña | both on | a magazine off leaves out its slides (`pub` = gv or lv); slides for both stay while either is on |
| **What to show** | all on | one switch per channel, with how many slides it has and a **needs internet** mark — only the channels that have slides today, plus **Welcome slide** and **About this display** ([5.2](#52-the-channels)). Under the list: "Sounds and the podcast play only while the sound is on (Timing & sound)." |
| **Folders in the committee's Drive** | all on | one switch per collection of the Drive booth folder, with its count; **The booth folder itself** for the files right in it. Listed only when the folder has files ([7.2](#72-the-booth-folder-and-its-collections)) |
| **Topics** | all on | one switch per tag of the CSV and the live items, in the page's language, most used first, with counts — today from **History** (71 slides), **Service** (64) and **Writing for the magazines** (58) down to **Zoom** (1). A topic off hides every slide that has it |
| **Order** | Shuffle | **Shuffle — a new mix all day** · **In order — as numbered in the folder and the list** ([5.6](#56-how-the-next-slide-is-chosen)) |

When the switches leave nothing to show, the top of this tab says **Nothing can show with these settings. Turn more
on in Settings → Show.** — the screen then shows the about slide (and the welcome slide), never a blank screen.

### 4.3 Slides

Every slide of the show and the player's own (the about slide, and the welcome slide while an event name is set),
one row each:

- **Search the slides** — any word of a slide, its id or its type (`staples`, `quiz-gvhist`, `video`).
- **Show** — **All** · **Can show now** · **Turned off** · **On, but not now**.
- The count, for example **294 of 294 · Showing the first 150: search to narrow the list.**
- Each row: the slide's title or first words; a badge with its type ("Quiz", "Video", "Photo" …) and **needs
  internet** when it does; and, when it is on but cannot show now, why:

| Reason shown | Means |
|---|---|
| Its group is off (Show) | its channel is switched off in Show → What to show |
| Its magazine is off | Show → Magazines |
| Its Drive folder is off | Show → Folders in the committee's Drive |
| Its topic is hidden | one of its tags is off in Show → Topics |
| Not on today's date | outside its from / until days (Central time) |
| Already over | a live item whose time has passed (an event list whose last event ended, a daily quote two days old) |
| Not in this language | it has no words in the language mode chosen (an English-only quote in Español) |
| Needs internet | YouTube, a web video, sound or picture, the podcast, or a Drive picture without a saved copy — while offline |
| Plays only with the sound on | a sound file or podcast episode while the sound is off |
| Its file isn't available | its picture or video failed lately (tried again after 10 minutes) |
| YouTube isn't answering | YouTube did not start a video lately: its videos wait 10 minutes |

- **Show now** puts that slide on the screen at once (toast **Showing “…”**) — handy to check a new photo or row.
- The switch at the end of each row turns that slide off on **this device** (filter: Turned off). It stays off there
  until switched back on, also after the CSV changes — the device remembers it by its id.
- At the bottom, when there are any: **Files and rows the show couldn't use** — up to 40 lines naming the CSV row,
  Drive file, live item or setting that was left out, and why, in the page's language
  ([8.10](#810-how-mistakes-are-reported)). Today it has two, two official Shorts left out of the live videos:
  *YouTube: ¡Descárgala ahora! ¡Luego suscríbete!: left out of the booth: it says “Descárgala ahora”* and
  *YouTube: Download Now! Then Subscribe!: left out of the booth: it says “Download Now”*.

### 4.4 Timing & sound

| Setting | Default | Range | What it does |
|---|---|---|---|
| **Pace** | Normal | Calm · Normal · Lively | multiplies every slide's time: Calm × 1.35, Lively × 0.75 (not a video's or sound's own length) |
| **Seconds before an answer shows** | 12 | 4–60 | for quiz, true or false, fill in the blank, scramble (× pace); a row's own `reveal` wins |
| **Seconds for each photo** | 8 | 3–120 | a photo (and a web picture without a caption); a file's own `(Ns)` wins |
| **Longest a video or sound from the folder plays (seconds)** | 180 | 10–900 | a Drive video or sound file plays to its end or to this, whichever comes first |
| **Longest a web video or sound plays (seconds)** | 90 | 10–900 | the same for YouTube, the CSV's web files and the podcast: a 5-minute video plays its first 90 seconds |
| **A video or sound at most every … slides** | 8 | 3–30 | at most one clip (any video or sound) in that many slides ([5.6](#56-how-the-next-slide-is-chosen)) |
| **Play sound** | off | — | videos play muted and sound slides wait while it is off. "A browser may keep the sound off until someone taps the screen once." |
| **Volume** | 0.8 | 0–1 | the booth's own volume (an iPad uses the device's) |
| **Captions on YouTube videos** | on | — | YouTube's captions, in the slide's language when the video has them |

### 4.5 Screen

| Setting | Default | What it does |
|---|---|---|
| **Look** | Dark stage — best on TVs | or **Daylight — for bright rooms** (light paper, dark text) |
| **Text size** | Normal | **Large**: 15% bigger type |
| **Motion** | Animations on | **Calm — no animations**: no entrance animation, slow zoom, tile shuffle or confetti (also when the device asks for reduced motion) |
| **Clock** | on | the time at the top right, in the screen's language |
| **The site's QR code in the corner** | on | the site's code and address at the bottom right (English or Spanish home, by the screen's language) |
| **Progress bar** | on | the thin bar at the bottom that fills as a slide's time runs |
| **Safe margin for TVs that cut the edges (5%)** | off | moves the words and controls further in from every edge (by 4% of the screen, on top of the usual margin); pictures and the backdrop still fill the screen. In the show itself, not in the About page's previews |
| **Full screen** / **Exit full screen** | — | the button, like the F key (only in a browser that has full screen) |

### 4.6 Kiosk

| Setting | Default | What it does |
|---|---|---|
| **PIN** | none | [3.4](#34-the-pin) |
| **Visitors can tap the screen to play** | on | off: taps do nothing (no bar, quizzes answer themselves), the "Tap to play" hint goes; the hold and the keys still work for you |
| **Seconds without a touch before the show goes on by itself** | 40 (10–600) | after this, the visitors' bar goes, a visitor's language choice is undone, a pause ends, a Quiz me round left half-way ends ([6.3](#63-when-nobody-touches-it)) |
| **Questions in “Quiz me”** | 5 (3–10) | the length of a Quiz me round |
| **Keep the screen on** | on | asks the browser to keep the screen awake while the show plays. The line under it: **The screen stays on while the show plays.** · **This browser can't keep the screen on by itself: plug the device in and set its screen timeout to "Never".** · **The screen may turn off by itself.** (off, or the browser refused — low battery, power saver) |
| **Full screen when the show starts** | on | Start the booth fills the screen |
| **Look for new content every (minutes)** | 30 (5–1440) | how often a running show checks the site for a new show file ([9.4](#94-new-content-while-it-plays)) |
| **Save for offline when the show starts** | on | off: no saving on start or after new content (Offline → Save now still saves) |
| **Start automatically** → **Address that starts the show** | — | the start link with this setup, and **Copy** ([3.5](#35-one-link-for-every-device-the-start-link)) |

### 4.7 Offline

- **Offline copy** — one line: **Ready offline: 14 files · 86.2 MB · saved Oct 3, 6:05 AM** ·
  **Saved for offline: 9 of 14 files (40.1 MB)** · **Saving for offline 23 of 86** (with a progress bar) ·
  **Nothing saved for offline yet.** · **Some files couldn't be saved (3) — they will be tried again.** ·
  **This device ran out of room: some files couldn't be saved for offline.** · **Saving stopped without an
  answer. It will be tried again.** · **This browser can't keep an offline copy.** · **Reload the page to finish
  updating the site, then start the booth again.** ([section 9](#9-offline-and-updates)). The file count is the
  show file plus the saved Drive copies; the two About pages are kept with the site's saved pages. (A save that
  ends while this tab is open counts the two pages too — *Ready offline: 3 files …* today — until the tab is opened
  again.)
- **Save now** (needs internet: "Connect to the internet to save.") and **Remove the offline copy** (asks first).
- **Connection** — **Online**, or **Offline — the show plays from the saved copy**.
- Storage — "This site uses 4.6 MB of the 10.0 GB this browser allows." and **Persistent storage: yes — the
  browser won't clear it on its own.** or **Persistent storage: no — the browser may clear it when space runs low.**

### 4.8 Share & reset

- **Share this setup** — "This link opens the booth display with these settings on another device." **Link to
  this setup** + **Copy** ([3.5](#35-one-link-for-every-device-the-start-link)).
- **Reset** — three buttons, each asks first and offers **Undo** for 10 seconds:

| Button | Asks | Does | Then |
|---|---|---|---|
| **Reset the settings** | "Put every booth setting on this device back to how it started?" | every setting back to the site's starting settings — PIN, event name and switched-off slides included | **Settings reset.** |
| **Reset the poll votes** | "Clear the poll votes counted on this device?" | the votes back to zero | **Poll votes cleared.** |
| **Reset everything** | "Reset the settings, the poll votes and the show's memory of what it has shown?" | all three | **Everything reset.** |

**Undo** brings it all back (**Undone.**). The offline copy is not touched by any reset.

At the bottom: "Everything stays on this device: nothing is sent anywhere, and the polls never ask for names."

### 4.9 The five presets

A preset changes only what it names and keeps the rest of the device's settings — it is not a reset.

| Preset (Spanish page) | Its line | Sets |
|---|---|---|
| **Assembly — both languages** (Asamblea — en los dos idiomas) | Every slide in English and Spanish | language Both (the first language stays as it was) |
| **Spanish-speaking event** (Evento de habla hispana) | Spanish only, Spanish first | language Español, Spanish first |
| **English-speaking event** (Evento de habla inglesa) | English only | language English, English first |
| **Quiet room** (Sala tranquila) | No sound, a calm pace, no animations | sound off, pace Calm, motion Calm |
| **Quiz party** (Fiesta de preguntas) | More quizzes and puzzles, fewer videos, a lively pace | quizzes and puzzles twice as often, pace Lively, a video or sound at most every 10 slides |

Presets add up: "Quiet room" then "Quiz party" gives the lively pace with no sound and no animations. After
"Spanish-speaking event", "Assembly" gives Both **with Spanish first** — set Show → Which language goes first →
English (or tap "English-speaking event" first) for English on top.

### 4.10 What the device keeps, and what is never sent

| Kept in the browser | What | Removed by |
|---|---|---|
| `gv-booth-v1` (the browser's local storage) | this device's settings — only what differs from the site's starting settings, so the rest keeps following the site | Reset the settings |
| `gv-booth-polls-v1` | the poll votes counted on this device | Reset the poll votes |
| `gv-booth-state-v1` | the show's memory: the slides shown lately (so a reload does not repeat them), when the offline copy was saved | Reset everything (the slides' memory); Offline → Remove the offline copy (the date of the save) |
| the cache `gvlv-booth-v1` | the offline copy: the show file and its photos, videos, sounds and pictures | Offline → Remove the offline copy |
| the site's saved pages | both About pages, so they open offline | the site's "Saved pages & app" page (`/offline/`) |

Nothing of it is sent anywhere: no names, no votes, no settings, no visit counts. What the browser does fetch while
the show plays, online: the show file from the site (every 30 minutes), a tiny file every minute to tell whether the
connection is up, YouTube's player when a YouTube video plays (its script from `youtube.com`, the video from the
privacy-enhanced `youtube-nocookie.com`, its still picture from `i.ytimg.com`), the podcast's sound from its official
host, and the pictures that have no copy saved with the site from Google (`lh3.googleusercontent.com`).

A private window, or a browser with site data turned off, keeps nothing: the show still plays, and says once
**This browser isn't keeping the settings (a private window?). They last until you close this page.**

### 4.11 The site's starting settings (config/site.yml)

Every device starts from the defaults above, with the site's own on top — the `booth:` section of
[config/site.yml](../config/site.yml) (also in [Settings §3.14](settings.md#314-booth--the-booth-display)):

```yaml
booth:
  max_file_mb: 95
  max_total_mb: 400
  defaults:
    event_name: ""        # e.g. "NETA 65 Spring Assembly" (shown big at the top)
    event_name_es: ""     # e.g. "Asamblea de Primavera de NETA 65" (blank = the English one)
    language: "both"      # en | es | both | alternate
    sound: false          # start with the sound on? (true / false)
```

| Key | What it does | Example |
|---|---|---|
| `max_file_mb` | the biggest video or sound file saved for offline; a bigger one is left out of the show ([7.8](#78-the-offline-copies-of-drive-files)) | `95` |
| `max_total_mb` | the most of the booth folder saved for offline (never more than 800, whatever it says) | `400` |
| `defaults: event_name` / `event_name_es` | the event's name on every device that has not typed its own (at most 80 characters) | `event_name: "NETA 65 Spring Assembly"` → every booth shows it, and the welcome slide, until a device types another |
| `defaults: language` | `en`, `es`, `both` or `alternate` | `language: "es"` → every device that never chose a language plays in Spanish |
| `defaults: sound` | `true` starts with the sound on | `sound: true` |

Only these four starting settings live in the file; everything else is set per device. A device keeps only what was
changed on it, so a value it never touched — or changed back — follows the file. On the Spanish page Spanish goes
first in Both. Saving the file starts a site update (a quick run, live in a few minutes); a running booth picks the
new defaults up within half an hour, at its next slide. A value the build cannot read keeps the default and is named
in the build's log and in Settings → Slides, for example *config/site.yml booth.defaults.language: "spanish" is not
en, es, both or alternate: both is used*.

---

## 5. What the show contains

### 5.1 Three sources

| Source | Who edits it | What it gives | When it changes on the screen |
|---|---|---|---|
| `content/booth/booth.csv` in the repository | the committee, on GitHub ([section 8](#8-editing-the-csv)) | quizzes, true or false, facts, history, quotes, fill in the blank, scrambles, polls, "Let's talk", messages, QR codes, official YouTube videos and podcast episodes, web pictures — 246 rows switched on today | a few minutes after the commit (the site rebuilds), then within half an hour on a running booth |
| The Drive panel folder's `booth` folder | anyone with Editor access ([section 7](#7-photos-videos-sound-and-notes-from-drive)) | photos, posters (pictures and documents shown whole), videos, sound files, short notes — none today | at the next site update that reads Drive (the morning refresh, the nightly full update, the midday and evening refreshes, the quick run after any change saved in the repository, or one started by hand) |
| The site's own data | nobody: it updates itself | the live channels ([5.3](#53-the-live-channels)) — 47 items today | with every site update; rows that are over leave the screen by themselves, also offline |

Every site update writes all three into one file, `/about/booth.json` (293 items today, about 520 KB), which the
player reads. The build checks every row, file and live item against the booth's rules; whatever breaks one is left
out and named in Settings → Slides ([8.10](#810-how-mistakes-are-reported)) — the rest plays.

### 5.2 The channels

The switches of Settings → Show → **What to show**. Each slide belongs to exactly one.

| Switch · on the Spanish page | From | Slide types | Today | Needs internet |
|---|---|---|---|---|
| Quizzes and true or false · Preguntas y verdadero o falso | CSV | quiz, truefalse | 80 | no |
| Fill in the blank and word scrambles · Completar la frase y ordenar letras | CSV | fill, scramble | 25 | no |
| Facts and history · Datos e historia | CSV | fact, history | 51 | no |
| Quotes · Citas | CSV | quote | 15 | no |
| Quick polls · Encuestas rápidas | CSV | poll | 14 | no |
| Conversation starters · Temas para conversar | CSV | prompt | 13 | no |
| Messages · Mensajes | CSV | message | 11 | no |
| QR codes · Códigos QR | CSV | qr | 10 | no |
| Web videos (YouTube) · Videos de la web (YouTube) | CSV | video | 23 | **yes** |
| Web audio · Audio de la web | CSV | audio | 4 | **yes**, and the sound on |
| Web pictures · Imágenes de la web | CSV | image | 0 | **yes** |
| Photos (Drive) · Fotos (Drive) | Drive | photo | 0 | no, once saved for offline |
| Posters (Drive) · Carteles (Drive) | Drive | poster | 0 | no, once saved for offline |
| Videos (Drive) · Videos (Drive) | Drive | video | 0 | no: they play only from the saved copy |
| Sounds (Drive) · Sonidos (Drive) | Drive | audio | 0 | no; the sound on |
| Notes (Drive text files) · Notas (textos del Drive) | Drive | message | 0 | no |
| Upcoming events · Próximos eventos | site | events, countdown | 2 | no (a flyer's small picture shows only online) |
| Daily quotes · Citas diarias | site | quote | 2 | no |
| Official videos · Videos oficiales | site | video | 30 | **yes** |
| Podcast · Podcast | site | audio | 6 | **yes**, and the sound on |
| Upcoming themes · Próximos temas | site | themes | 1 | no |
| Subscription prices · Precios de suscripción | site | prices | 1 | no |
| Book of the Month · Libro del mes | site | book | 2 | no |
| Meetings · Reuniones | site | meetings | 1 | no |
| Bulletin posts · Avisos del boletín | site | message | 2 | no |
| Welcome slide · Diapositiva de bienvenida | the player | welcome | — | no |
| About this display · Acerca de esta pantalla | the player | about | — | no |

A channel with no slides is not listed in Settings. A Drive picture whose copy could not be saved shows from
Google's copy, so it needs internet; a Drive video or sound file without a saved copy is left out altogether.

### 5.3 The live channels

Made by the site at each update from its own data — the same words and numbers its pages show — in both languages.
Each slide's QR code leads to the page that has more, the Spanish page on Spanish slides.

| Channel | The slide shows | Stays until | QR code |
|---|---|---|---|
| **Upcoming events** | **Coming up**: the next four events of `/events/` (a monthly series once), each with its date and time, title, place and a note — "Online on Zoom" for an online or hybrid one (its place stays beside it), "Details to be confirmed" for a tentative one. Today: the Grapevine Writing Workshop in Arlington (hybrid), the La Viña Writing Workshop in Mansfield, the CityWide Dallas booth, the La Viña Recording Workshop in Duncanville | each row until its event ends; the slide until the last one does | `/events/` |
| **Upcoming events** — countdown | **Coming up next**: "Next assembly" · the next NETA 65 assembly, the days and hours left (hours and minutes on its last day), its dates and place. Today: NETA 65 Spring Assembly 2027, Fri, Mar 19 – Sun, Mar 21, 2027 | the assembly's start | its card on `/events/` |
| **Daily quotes** | Grapevine's Daily Quote (English) and La Viña's Cita Diaria (Spanish), word for word as the Home page shows them, with their attribution, under the headings "Grapevine Daily Quote · Oct 2" and "Cita Diaria de La Viña · 2 de octubre" | two days after its date | the official page |
| **Official videos** | the two videos the About page features (`config/site.yml` → `site:` → `about_videos`) first, then the newest 30 Shorts and videos of 8 minutes or less of the official AA Grapevine & La Viña channel, each in its own language, credited "AA Grapevine & La Viña on YouTube" — never a recording of a weekly open meeting or a live stream, never one a CSV row already plays (today both featured videos are CSV rows, so all 30 are the newest ones), never one whose title says a refused word | the next update's list | — |
| **Podcast** | the six newest episodes of AA Grapevine's podcast (English), with a headphones picture (never the show's logo) — never one a CSV row already plays | the next update's list | — |
| **Upcoming themes** | **Write for the magazines**: "Upcoming themes & deadlines", the next three themes of each magazine — "Due October 17, 2026 · Recaídas (Relapses) · La Viña · May–June 2027" | each row until its deadline; the slide until the last | `/contribute/` |
| **Subscription prices** | **Subscriptions**: the 1-year print and digital plans of both magazines — "Grapevine · Print · 1 year $36.00", with an announced change beside it ("From Jan 1, 2027: $39.00") and "Prices as of October 2, 2026, from the official stores" | the announced change's day (a new update brings the new prices) | `/shop/#subscriptions` |
| **Book of the Month** | Grapevine's Book of the Month and La Viña's Libro del mes: the title it is sold under, a short description, "$11.99 instead of $14.99, until October 14" — never a cover. A book in the other language says so ("En inglés · Traducción del título: …") | the offer's last day | the official store page |
| **Meetings** | **Meetings you can join**: the committee's monthly meeting (Zoom), Grapevine's and La Viña's weekly open meetings, La Viña's monthly virtual workshop — a meeting in the other language marked "(in Spanish)" / "(en inglés)" | always (a dated row until it is over) | `/meetings/` |
| **Bulletin posts** | the bulletin's two newest posts (pinned first, none past its last day): the headline and its first paragraph (at most 280 characters) | the post's "until" day | the post on `/bulletin/` |

The lists (events, meetings, themes) and the prices fill the screen in one language at a time: in Both, the first
language's part shows first and the other's takes its place half-way through (the slide gets 1.7 times its time).
The countdown has room for both at once.

Where each kind of data comes from, and how to change it at the source, is in
[Automatic sources](automatic-sources.md) (videos, podcasts, daily quotes, themes, prices, weekly open meetings),
[Flyers and events](flyers-and-events.md) (events) and [Bulletin](bulletin.md) (posts).

### 5.4 The welcome and about slides

The player makes two slides of its own:

- **Welcome** — only while an event name is set (and "Show the event name at the top" is on). The grape mark,
  **Welcome!** in big type, the event's name, and **Grapevine and La Viña — ask us anything**; on Spanish slides
  **¡Bienvenidos!**, the Spanish name and **La Viña y Grapevine — pregúntanos lo que quieras**. It opens the show
  and comes back every 12 slides. 10 seconds.
- **About** — always: the site's QR code, **Shared by the NETA 65 Grapevine & La Viña Committee**, **Not an
  official AA Grapevine, Inc. or A.A.W.S. display**, and the site's address `neta65.github.io/aagrapevine`
  (Spanish: "Compartido por el Comité de Grapevine y La Viña de NETA 65" / "Esta no es una pantalla oficial de AA
  Grapevine, Inc. ni de A.A.W.S."). Every 30 slides, 12 seconds; and the slide that shows whenever nothing else
  can. Keep it on: it is the line that tells visitors the display is ours, not AA Grapevine's.

Both can be switched off in Show → What to show (Welcome slide, About this display).

### 5.5 Languages on the screen

| Mode | Shows | A slide in both languages | A one-language slide | A picture without words |
|---|---|---|---|---|
| **English** | the slides that have English words | in English | only if it is English | yes |
| **Español** | the slides that have Spanish words | in Spanish | only if it is Spanish | yes |
| **Both** (default) | everything | the first language on top, the other under a thin line, a little quieter | in its own language | yes |
| **Alternate** | everything | in English, then the next slide in Spanish, starting with the first language | in its own language (it counts as that language's turn) | yes |

What that means today:

- English mode: 264 slides; Español: 258; Both and Alternate: 284 (with the starting settings, online).
- The 14 English-only quotes (seven Traditions, the Declaration of Unity, three passages of The A.A. Service Manual,
  a 1960 Advisory Action and two AAWS service pieces — texts with no official Spanish wording the committee could
  quote),
  Grapevine's Daily Quote, the English podcast and Grapevine's English videos never show in Español. La Viña's Cita
  Diaria and its Spanish videos never show in English.
- A video's caption is in the slide's language even when its sound is in the other one: the CSV's video rows say
  "In Spanish:" / "En inglés:" for that.
- In Both, a slide that would not fit at 75% of its type in two languages shows in **one** language, and the
  other one leads the next time it comes — nothing is cut off, nothing shrinks out of reading range.
- The screen's own words (eyebrows such as "Did you know? · ¿Sabías que…?", "True" / "False", "Show the answer",
  the poll's note) follow the slide's languages, not the page's.

Visitors can choose English, Español or Both for themselves from the bar ([6.1](#61-what-visitors-can-do)); the
choice lasts until they walk away.

### 5.6 How the next slide is chosen

**Shuffle** (the default) picks each slide at random among the ones that keep these rules, the most important
first. A rule that no slide can keep at that moment gives way; the others still hold.

1. **No repeats too soon.** A slide does not come back until 40% of the show (at least 4 slides) has played since
   — with today's 284 slides, 114 others in between.
2. **Videos and sounds are spaced.** At most one video or sound (YouTube, a web or Drive file, a podcast episode)
   in every 8 slides (Timing & sound → "A video or sound at most every … slides"). A clip plays for a minute or
   more where a slide stays for seconds; without this rule the official videos would take most of the screen time.
3. **Variety.** Never the same kind of slide twice in a row (two photos in a row at most).
4. **Not too much play.** At most one of every 3 slides is a quiz, true or false, fill in the blank, scramble or
   poll.
5. **Something to look at.** A picture or a clip at least every 4 slides, when one can come (a clip only when rule
   2 allows it). When there are few pictures, they are spread evenly instead of all coming early.
6. **Lists are spaced.** At most one events, meetings or themes list in 6 slides.
7. **Welcome and about.** The welcome slide every 12 slides (when an event name is set), the about slide every 30
   — a slide later when a picture or clip is due at that moment.

Among the slides that pass, a slide's **weight** (the CSV's `weight`, a Drive file's `(x2)` or `(rare)`) and the
"Quiz party" preset's ×2 for quizzes and puzzles make it more or less likely. With rule 1 in place, a weight counts
only among the slides that are allowed at that moment.

Files marked `(first)` in the Drive folder open the show, in their order, right after the welcome slide — at every
start, and again when Settings close after a change to what may show.

A real start (today's show, starting settings, online, with an event name; each start on a device draws its own
mix, so yours will differ):

```text
1 welcome · 2 scramble · 3 message · 4 fact · 5 true or false · 6 history · 7 message · 8 official video ·
9 quiz · 10 fact · 11 prices · 12 true or false · 13 welcome · 14 message · 15 quiz · 16 official video ·
17 quote · 18 events · 19 scramble · 20 Book of the Month · …
```

The same show offline has no videos (they need internet): the clips' turns go to quotes, messages and the other
slides. Over 400 slides online, 50 were videos — one in 8, never closer.

**In order** plays the slides in a fixed order, looping: first the Drive files that have an order number (01, 02 …),
then the CSV rows from top to bottom, then the other Drive files, then the live items — the welcome and about slides
still come every 12 and 30. None of the shuffle rules apply. Today's CSV is sorted by type, so In order plays its 55
quizzes one after the other: it is meant for a hand-ordered show (a numbered Drive folder, a CSV you arranged). Use
Shuffle otherwise.

### 5.7 How long a slide stays

| Slide | Time (Normal pace) |
|---|---|
| quiz, true or false, fill, scramble | the question until the answer shows (12 s), then 7 s + the answer and explanation's reading time; at least 8 s after the answer |
| fact, history, quote, message, note, Book of the Month | reading time: 6 s + 1 s per 12 characters, at least 8 s and at most 30 s (× 1.7 in Both, still 30 s at most) |
| poll, "Let's talk", QR code | 14 s |
| photo | 8 s (Timing & sound → Seconds for each photo) |
| poster | 12 s |
| web picture | 8 s, longer with a caption to read |
| events, meetings, themes, prices | 15 s (× 1.7 in Both: each language for half) |
| countdown, welcome | 10 s |
| about | 12 s |
| video, sound | from its start to its end, at most 180 s for a Drive file and 90 s for YouTube, a web file or the podcast; the next slide comes when it ends |

Then: × 1.35 at Calm pace, × 0.75 at Lively (not videos and sounds); a CSV row's `seconds` or a Drive file's `(15s)`
replaces the computed time (× pace); every slide but a video or sound stays between 5 and 180 seconds.

Real examples (today's rows):

| Slide | English | Both | Calm, English |
|---|---|---|---|
| `quiz-gvhist-founders` ("In 1944, how many AA members started the Grapevine?") | 29.1 s, the answer at 12 s | 38.8 s | 39.3 s, the answer at 16.2 s |
| `fact-gvhist-mail-call` ("Our meeting in print") | 28.8 s | 30 s | 38.9 s |
| `history-gvhist-1944-first-issue` ("June 1944") | 20.8 s | 30 s | 28 s |
| `poll-service-your-connection` | 14 s | 14 s | 18.9 s |
| `video-gv-victor-e-is-back` (a 44-second Short) | 44 s (it ends) | 44 s | 44 s |
| `video-gv-twelfth-step-tools` (5:16 long) | its first 90 s | 90 s | 90 s |
| a Drive file `GV EN Welcome to our table (first) (15s).png` | 15 s | 15 s | 20.3 s |

A visitor who taps an answer gets at least 8 more seconds to read it; a vote keeps the poll on screen at least 7
seconds more; "Take it home" keeps the slide at least 30 seconds. A slide that has not moved on 20 seconds after its
time is moved on anyway, and a video or sound that does not start within 12 seconds, or stops for lack of data for
12 seconds, is skipped.

---

## 6. Visitor mode

### 6.1 What visitors can do

Any tap on the screen (or any key) brings up the **visitors' bar** at the bottom, in the screen's language — the
visitor's choice, else the show's one language, else the first language:

| Button (Spanish) | Does |
|---|---|
| **Back** (Atrás) | the slide before |
| **Pause** / **Play** (Pausa / Seguir) | stops the show on this slide / goes on |
| **Next** (Siguiente) | the next slide |
| **Quiz me** (Ponme a prueba) | a short quiz round ([6.2](#62-quiz-me)) |
| **English** · **Español** · **Both** (Ambos) | the screen's language, for this visitor |
| **Take it home** (Llévatelo) | a panel "Scan a code with your phone's camera." with the site's code (**Our website**) and, when the slide has a QR code of its own, **About this slide** |

On the slides themselves:

- **Quiz and true or false**: a visitor taps a choice (A, B, C … or True / False). The answer shows at once — the
  right choice lit with ✓, theirs with ✗ when it is wrong — with **Right!** or **Not quite — here's the answer.**
  over the explanation, and a burst of confetti for a right answer (not in Calm motion).
- **Fill in the blank and scramble**: a **Show the answer** button. The word writes itself into the blank; the
  letter tiles slide into place.
- **Poll**: tapping an option is a vote. The bars show the percentages, and the note reads **Thanks for voting! ·
  3 votes at this table** (before any vote: **Tap an answer to vote**). One vote per showing of the poll.
- **Video**: **Sound** (only when the booth's sound is on and the file is not marked `(muted)`; it shows whether the
  video plays with its sound) and **Skip**.
- **"Tap to play"** (Toca para jugar) at the bottom of the screen invites the taps while the bar is down.

A tap on a playing YouTube video goes to YouTube's player, not the booth: the booth notices, brings up its bar and
takes the keys back; a pause made inside YouTube's player plays on. YouTube's own title and logo links stay
clickable (YouTube's rules); a kiosk mode keeps such a tap from leaving the show
([2.3](#23-lock-the-device-to-the-show)).

With **Visitors can tap the screen to play** off (Settings → Kiosk), taps do nothing: no bar, and quizzes answer
themselves on their timer.

### 6.2 Quiz me

**Quiz me** (or the **Q** key) starts a round of 5 questions (Settings → Kiosk → Questions in “Quiz me”, 3 to 10)
picked from the quizzes, true or false and fill in the blank that can show now, in the bar's language, none twice:

1. The top of the screen shows **Question 1 of 5** and a dot per question.
2. A question waits for the visitor — no timer. A quiz or true or false answers with a tap; a fill in the blank has
   **Show the answer**, then **Did you know it?** → **I knew it** / **Not this time**.
3. **Next question**, and after the last one **See my score**.
4. The last card: **4 of 5!** and **Every one right — wonderful!**, **Nicely done!** (half or more) or **Thanks for
   playing!**, then **Ask us about Grapevine and La Viña**, with **Play again** and **Back to the show**. It stays
   20 seconds.

No names, no rankings, nothing kept. In a language with no playable question: **No quiz questions in this language
right now.** A round left half-way ends after the idle time.

### 6.3 When nobody touches it

After **40 seconds** without a touch (Settings → Kiosk → Seconds without a touch …): the bar goes down, a visitor's
language choice is undone, a pause ends, a Quiz me round left half-way ends, "Take it home" closes, and the show
goes on by itself. A PIN or "Leave?" box opened by a visitor closes after the same time, and Settings left alone
after 2 minutes.

### 6.4 Privacy

- Polls count votes on this device only ("… votes at this table"); they never ask for a name, and the votes never
  leave the device. **Reset the poll votes** clears them.
- Quiz me keeps no score, no name, no ranking.
- Nothing a visitor does is sent anywhere ([4.10](#410-what-the-device-keeps-and-what-is-never-sent)).
- The slides themselves follow AA's anonymity rules: no faces or full names in the photos, first name and last
  initial at most in the texts ([7.10](#710-aa-rules-for-the-folder), [8.11](#811-aa-rules-for-the-content)).

---

## 7. Photos, videos, sound and notes from Drive

The Drive rules every folder shares — sharing ("Anyone with the link"), panel folders, what is never published,
replacing and deleting files, the API key — are in [The Drive panel folder](drive-panel-folder.md) (its booth part
is [§3.6](drive-panel-folder.md#36-the-booth-folder-new)); what each file type becomes in every folder is in
[File types](file-types.md#418-the-booth-folder). This section is the booth folder in full.

### 7.1 Quick start: put a photo on the booth

1. Google Drive → **A65_GV** → **2027-2028_Panel77_GVLV** → **booth**. The folder exists and is empty today; any of
   the booth folder words works ([7.2](#72-the-booth-folder-and-its-collections)).
2. Name the file: magazine, language, a short title, options in brackets —
   `GV EN Our literature table (15s).jpg`.
3. Upload it.
4. Wait for the next site update that reads Drive — the morning refresh (about 4:30 AM Central with the morning
   alarm), the nightly full update, or the midday or evening refresh — or start one: GitHub → **Actions** →
   **Website update** → **Run workflow** → tick **skip_crawl** → **Run workflow** (a few minutes, plus the time to
   download new videos).
5. That run lists the file (`data/site/booth.json`), saves a copy of it with the website (Google's 1920-pixel
   picture of a photo; a video or sound file whole) and publishes the show with it.
6. A booth that is playing online picks it up within half an hour, at its next slide, and saves it for offline; any
   other booth gets it the next time its About page is opened (or reloaded) with internet — a page left open keeps
   the show it loaded.
7. Check (reload the About page first if it was already open): Settings → **Slides** → search `literature` →
   **Show now**. The photo fills the screen with a slow zoom,
   blue (Grapevine), the caption "Our literature table" at the bottom, for 15 seconds; it plays in the English,
   Both and Alternate modes, not in Español.

### 7.2 The booth folder and its collections

**The folder.** The first folder below the panel folder whose name holds one of these words, as a whole word
(capitals and accents do not matter): `booth`, `booths`, `mesa`, `mesas`, `kiosk`, `kiosko`, `kiosco`, `display`,
`displays`, `pantalla`, `pantallas`, `stand`, `stands`, `exhibit`, `exhibits`, `exhibición`, `exhibiciones`. When a
name holds the words of two kinds of folder, the one written first wins:

| Folder below the panel folder | Is |
|---|---|
| `booth`, `Booth`, `Mesa`, `Booth display`, `Kiosk 2027`, `Pantalla` | the booth folder |
| `Booth photos`, `Display boards`, `Literature display photos`, `Exhibit hall photos`, `Mesa de literatura`, `Mesa de GV y LV`, `Stand-up` | the booth folder — the booth word comes first |
| `Booth flyers` | the booth folder: these flyers do **not** become events (put flyers in `flyers`) |
| `Photos of the booth`, `Pictures of the booth`, `Fotos de la mesa` | a photo folder (an album on `/photos/`): the photo word comes first |
| `photos/Booth at CityWide` | an album: only the first folder counts, and it is `photos` |
| `Workshop displays`, `Flyers for the booth`, `Notas de la mesa` | workshops, flyers, notes |

A booth file goes to the booth display **only**: never to the Portfolio, `/photos/`, the bulletin, the events,
What's New, the search or the digest. Only `/status/` counts it, with the other Drive files. Everything in the
folder is public, like the rest of A65_GV.

**Collections.** Each sub-folder is a **collection** that a booth can switch off in Settings → Show → **Folders in
the committee's Drive** (all on to start with), with how many slides it has:

| File | Collection (its id) |
|---|---|
| `booth/Welcome.png` | "The booth folder itself" (`main`) |
| `Booth photos/Welcome.png` | `main` — that folder **is** the booth folder |
| `booth/Spring Assembly 2027/GV EN Book display.jpg` | "Spring Assembly 2027" (`spring-assembly-2027`) |
| `booth/Spring Assembly 2027/extra/Welcome.png` | "Spring Assembly 2027" — a deeper folder belongs to its top collection |
| `booth/Spring_Assembly_2027/Welcome.png` | "Spring Assembly 2027" (underscores read as spaces) |
| `Mesa/Asamblea de Primavera/Bienvenidos.png` | "Asamblea de Primavera" (`asamblea-de-primavera`) |
| `booth/Exhibición Área 65/Welcome.png` | "Exhibición Área 65" (`exhibicion-area-65`) |
| `booth/Main/Welcome.png` | "Main" (`main-folder`: it keeps an id of its own) |

A device remembers a collection switched off by its id, so renaming a sub-folder brings it back on. Two panels'
booth folders play together, and sub-folders with the same name form one collection. An idea: one sub-folder per
event (`booth/Spring Assembly 2027/`, `booth/CityWide/`) plus the general files right in `booth/`; at each event,
switch off the other events' folders.

### 7.3 The naming convention

```text
[order] [magazine] [language] Title [(option) (option) …].ext          every part is optional but the title
```

| Part | Write | It means |
|---|---|---|
| **order** | a number of 1 to 3 digits and a separator at the very start: `01 `, `02-`, `3_`, `01.`, `01)`, `1 - ` | its place in the "In order" mode ([5.6](#56-how-the-next-slide-is-chosen)); never shown. A year or a date at the start is not an order (`2027 Spring Assembly`, `10-26-2026 Taller`), nor a number that counts something (`12 Steps poster`, `3 ways to carry the message`, `10 años de La Viña`): write `01 12 Steps poster.png` to give that one an order |
| **magazine** | at the start, any capitals: `GV` (Grapevine), `LV` (La Viña), or both: `GVLV`, `GV-LV`, `GV+LV`, `GV&LV`, `GV/LV`, `GV LV`, `GV_LV`, `LV-GV`; `AA` (both) only right before a language code (`AA EN Welcome.png`). Or in brackets anywhere: `(LV)`, `[GV]`, `(AA)`, `(Grapevine)`, `(La Viña)`, `(AA Grapevine)`, `(Grapevine y La Viña)` | the slide's colour (Grapevine blue, La Viña amber, both grape) and the Magazines switch of Settings → Show. No magazine = both |
| **language** | at the start in CAPITALS: `EN`, `ES`, `BI`, or `EN-ES` (also `EN/ES`, `ES-EN` …); right after the magazine also the words `English`, `Inglés`, `Spanish`, `Español`, `Bilingual`, `Bilingüe`. Or in brackets anywhere, any capitals: `(es)`, `[English]`, `(en español)`, `(in English)`, `(Bilingüe)`, `(EN ES)`, `(en inglés y español)` | which language modes play it: `EN` in English, Both and Alternate (not Español), `ES` the other way round, `BI` in all. No language = every mode — right for photos, music and pictures without words. A note with no language code plays in the language(s) its paragraphs are written in |
| **title** | the rest of the name | the caption (a note's heading). Tidied like other Drive names: underscores become spaces, `GV_LV` becomes "GV/LV", "Copy of", "Copia de" and a copy's " (1)" are dropped. A date stays in the caption here. A camera's name (`IMG_2045`, `PXL_…`, `WhatsApp Image …`, `Screenshot …`, a bare number) gives no caption. Never machine-translated: the same words show in both languages |
| **options** | in `( )` or `[ ]`, one per pair, any order, English or Spanish, any capitals | [7.4](#74-every-option). Anything else in brackets stays in the caption: `(parte 2)`, `(from the Chair)`, `(until further notice)` |

Leading words count only **before** the title starts: `Esto ES La Viña.jpg` keeps its "ES", `En la mesa de
Tyler.jpg` its "En", and `AA Preamble.png` its "AA" (a leading AA is the magazine code only right before a
language code; both magazines is the default anyway).

### 7.4 Every option

| Option | Means |
|---|---|
| `(poster)` `(cartel)` `(afiche)` | show the whole picture, never cropped, over a blurred copy of itself — the default for .png .gif .webp .svg .bmp and for documents (a PDF's or a slide deck's first page) |
| `(photo)` `(foto)` | fill the screen with a slow zoom (the picture's edges may be cut) — the default for .jpg .jpeg .jfif .heic .heif .tif .tiff. (Written on a video it is kept in the data, but the player always shows a video whole) |
| `(15s)` `(15 s)` `(15 sec)` `(15 seconds)` `(15 seg)` `(15 segundos)` `(2 min)` `(2 minutos)` | seconds on screen of a photo, poster or note, kept between 3 and 120; ignored for a video or sound file, which plays its own length |
| `(0:15-1:30)` `(0:15–1:30)` `(0:15 a 1:30)` `(0:15 to 1:30)` `(15-90)` `(0:15-)` `(1:02:03-1:05:00)` | play only that part of a video or sound file; no end = to its end; an end before the start is dropped (to its end). Plain seconds (`15-90`) count only on a video or sound file |
| `(muted)` `(mute)` `(silent)` `(sin sonido)` `(silencio)` | never play this file's sound (the visitors' Sound button does not show) |
| `(x2)` … `(x5)` `(2x)` `(×3)` | shown 2 to 5 times as often (a bigger number counts as 5) — among many slides; with few pictures each one already comes back as often as the no-repeat rule allows |
| `(rare)` `(sometimes)` `(poco)` `(a veces)` | shown half as often |
| `(first)` `(primero)` `(primera)` | shown first when the show starts, right after the welcome slide (and again after the settings change); several, in the folder's order |
| `(from 2027-03-01)` `(desde …)` `(starting …)` `(a partir de …)` | only from that day (Central time) |
| `(until 2027-03-15)` `(hasta …)` `(till …)` `(through …)` `(expires …)` `(vence …)` | only until that day, both days included. The booth stops showing it after that day by itself (offline too); at the next update the file leaves the show's file and is not saved any more |
| `(no caption)` `(no text)` `(no title)` `(sin texto)` `(sin título)` | no caption; a note without its heading |
| `(off)` `(apagado)` `(draft)` `(borrador)` — or a name that starts with `_` or `~` | kept in Drive, never shown (and never listed as a problem) |

**Dates in options** can be written any way the site reads dates in file names, with a year from 2000 to 2099
([The Drive panel folder §3.8](drive-panel-folder.md#38-dates-in-file-names)): `2027-03-01`, `March 1, 2027`,
`03/15/2027`, `15 March 2027`, `el 15 de marzo de 2027`, `2027.03.15`; a month alone means its first day for
"from" and its last day for "until" (`(until March 2027)` → March 31). A date without its year (`(until March
15)`) stays in the caption. A future "from" day is fine: the file is saved for offline at once and starts showing on
its day, offline too.

Several options may share one pair — `(first, 15s)`, `(GV EN)`, `(first x2)`, `(GV; ES; muted)` — but a pair that
holds anything else stays whole in the caption: `Welcome (first, see notes).png` is not shown first. Keep to one
option per pair and there is nothing to remember.

### 7.5 Examples

Every example below is one of the naming tests (`tests/test_booth_names.py`), with the result the real code gives.
"Every language" means the file plays in every language mode.

**The design's examples**

| File in `booth/` | The booth shows |
|---|---|
| `GV EN Welcome to our table (first) (15s).png` | poster · Grapevine · English · "Welcome to our table" · shown first · 15 seconds |
| `LV ES Testimonio - Mi primer número (0:05-1:45).mp4` | video · La Viña · Spanish · "Testimonio - Mi primer número" · plays 0:05 to 1:45 |
| `GVLV Our booth at CityWide Dallas.jpg` | photo filling the screen · both magazines · every language · "Our booth at CityWide Dallas" |
| `IMG_2045.JPG` | photo · both · every language · no caption |
| `02 GV Our book table (x3).png` | poster · Grapevine · every language · "Our book table" · number 2 in "In order" · 3 times as often |
| `LV ES Taller de escritura en Tyler (hasta 2026-10-26).jpg` | photo · La Viña · Spanish · "Taller de escritura en Tyler" · until October 26, 2026 |
| `_draft poster.png` · `Draft poster (off).png` | never shown |
| `Spring Assembly 2027/GV EN Book display.jpg` | photo · Grapevine · English · "Book display" · collection "Spring Assembly 2027" |
| `GVLV BI Bienvenidos - Welcome.mp4` | video · both · English and Spanish · "Bienvenidos - Welcome" |
| `GV EN Welcome message.txt` | note · Grapevine · English · heading "Welcome message", the file's text under it |
| `Grapevine and La Viña - ways to carry the message.pdf` | poster of the document's first page · both · every language |
| `Esto ES La Viña.jpg` | photo · every language · "Esto ES La Viña" |
| `[LV][ES] Cita (10s) (muted).mp4` | video · La Viña · Spanish · "Cita" · never its sound ("10s" ignored for a video) |
| `GV EN Podcast teaser (0:30-).mp3` | sound · Grapevine · English · "Podcast teaser" · from 0:30 to its end (only while the sound is on) |

**Spanish options, capitals, accents**

| File | Result |
|---|---|
| `LV ES Bienvenidos (primero) (20 segundos).png` | first · 20 seconds · "Bienvenidos" |
| `LV ES Bienvenidas (primera) (20 seg).png` | first · 20 seconds |
| `GV EN Book display (foto).png` | photo: a .png filling the screen |
| `LV Folleto (cartel).jpg` · `LV Folleto (afiche).jpg` | poster: a .jpg shown whole |
| `LV ES Cita (sin sonido) (0:10-0:40).mp4` | never its sound · plays 0:10 to 0:40 |
| `GV Clip (silencio).webm` | never its sound |
| `LV ES Taller (desde 2027-03-01) (hasta 2027-03-15).jpg` | from March 1 to March 15, 2027 |
| `LV ES Recuerdo (a veces).jpg` · `LV ES Recuerdo (poco).jpg` | half as often |
| `LV ES Mesa (sin título).jpg` · `LV ES Mesa (sin texto).jpg` · `LV ES Taller (sin titulo).jpg` | no caption (the accent is not needed) |
| `LV Cartel nuevo (borrador).png` · `LV Cartel nuevo (apagado).png` | never shown |
| `LV ES Mesa (SIN TEXTO) (Primera) (X2).jpg` | no caption · first · twice as often |
| `LV ES Taller (Desde 1 de marzo de 2027).jpg` | from March 1, 2027 · "Taller" |
| `GV EN Clip (mute).mp4` · `GV EN Clip (silent).mp4` | never its sound |
| `GV EN Table (rare).jpg` · `GV EN Table (sometimes).jpg` | half as often |
| `GV EN Table (no text).jpg` · `GV EN Table (no caption).jpg` | no caption |
| `GV EN Table (draft).jpg` | never shown |

**Dates**

| File | Result |
|---|---|
| `GV Booth (from March 1, 2027).jpg` | from 2027-03-01 · "Booth" |
| `GV Booth (until 03/15/2027).jpg` · `GV Booth (until 15 March 2027).jpg` · `GV Booth (hasta el 15 de marzo de 2027).jpg` · `GV Booth (until 2027.03.15).jpg` | until 2027-03-15 |
| `GV Booth (from: 2027-03-01).jpg` | from 2027-03-01 |
| `GV Booth (from March 2027).jpg` | from 2027-03-01 |
| `GV Booth (until March 2027).jpg` | until 2027-03-31 (the whole month) |
| `LV Mesa (hasta febrero de 2028).jpg` | until 2028-02-29 (a leap year) |
| `GV EN Message (from the Chair).txt` | no date: the caption is "Message (from the Chair)" |
| `GV EN Notice (until further notice).txt` | the caption is "Notice (until further notice)" |
| `LV ES Aviso (hasta el 1 de febrero).txt` | no year, no date: "Aviso (hasta el 1 de febrero)" |
| `GV Booth (from 2027-03-15) (until 2027-03-01).jpg` | a **problem**: "its days never meet — the (from …) day is after the (until …) day" |
| `2027-03-14 Spring Assembly.jpg` | caption "2027-03-14 Spring Assembly" — the date stays, it is not an order or a "from" day |
| `GV EN Spring Assembly March 14, 2027.jpg` | caption "Spring Assembly March 14, 2027" |

**Brackets and several options**

| File | Result |
|---|---|
| `[GV] [EN] Welcome [first] [x2].png` | Grapevine · English · first · twice as often · "Welcome" |
| `Welcome [LV] [poster].jpg` | La Viña · poster · "Welcome" |
| `Welcome (first, 15s).png` | first · 15 seconds |
| `Welcome (GV EN).png` | Grapevine · English |
| `Welcome (first x2).png` | first · twice as often |
| `Welcome (GV; ES; muted).mp4` | Grapevine · Spanish · never its sound |
| `Welcome (first, see notes).png` | **not** first: the caption is "Welcome (first, see notes)" |
| `Taller (parte 2).jpg` | caption "Taller (parte 2)" |
| `Taller (English version).jpg` | caption "Taller (English version)", every language |
| `Welcome (Off Broadway).png` | shown (not "off"): caption "Welcome (Off Broadway)" |
| `Taller (La Viña).jpg` | La Viña · "Taller" |
| `Story (Grapevine).jpg` · `Story (AA Grapevine).jpg` | Grapevine |
| `Story (Grapevine y La Viña).jpg` | both magazines |
| `Cita (en español).mp4` · `Cita (Español).mp4` · `Cita [es].mp4` | Spanish · "Cita" |
| `Quote (in English).mp4` · `Quote (English).mp4` | English |
| `Saludo (Bilingüe).mp4` · `Saludo (EN-ES).mp4` · `Saludo (en inglés y español).mp4` · `Saludo (EN ES).mp4` | English and Spanish |

**Time on screen, weight, the part of a clip**

| File | Result |
|---|---|
| `GV Poster (1s).png` | 3 seconds (the least) |
| `GV Poster (500s).png` · `GV Poster (2 min).png` | 120 seconds (the most) |
| `GV Poster (10 sec).png` · `GV Poster (10 seconds).png` | 10 seconds |
| `GV EN Note (45s).txt` | a note shown 45 seconds |
| `GV Song (30s).mp3` | "30s" ignored: a sound plays its own length · "Song" |
| `GV Poster (x9).png` | 5 times as often (the most) |
| `GV Poster (x1).png` · `GV Poster.png` | as often as any other |
| `GV Poster (3x).png` · `GV Poster (×2).png` | 3 times · twice as often |
| `GV Clip (15-90).mp4` · `GV Clip (0:15–1:30).mp4` · `GV Clip (0:15 a 1:30).mp4` · `GV Clip (0:15 to 1:30).mp4` | plays 0:15 to 1:30 |
| `GV Clip (1:02:03-1:05:00).mp4` | plays 1:02:03 to 1:05:00 |
| `GV Clip (1:30-0:15).mp4` | the end is before the start: from 1:30 to its end |
| `GV Clip (0:00-0:45).m4v` | plays 0:00 to 0:45 |
| `Big Book pages (15-90).jpg` | on a picture, plain numbers stay in the caption: "Big Book pages (15-90)" |
| `GV Poster (0:15-1:30).png` | on a picture, clock times are taken out and ignored: "Poster" |

**Order numbers**

| File | Result |
|---|---|
| `01 Welcome.png` · `01-Welcome.png` · `01_Welcome.png` · `01. Welcome.png` · `01) Welcome.png` · `1 - Welcome.png` · `001 Welcome.png` | order 1 · "Welcome" |
| `3_GV_EN_Welcome.png` | order 3 · Grapevine · English · "Welcome" |
| `02-GV EN Welcome.png` | order 2 · Grapevine · English |
| `(first) 02 GV EN Welcome.png` | order 2 · first · Grapevine · "Welcome" |
| `2027 Spring Assembly.jpg` · `10-26-2026 Taller en Tyler.jpg` · `5 de octubre Taller en Tyler.jpg` · `1 May 2027 Workshop.jpg` · `0042 Booth.jpg` | no order (a year, a date, four digits): the whole name is the caption |
| `12 Steps poster.png` · `12 Tradiciones.png` · `3 ways to carry the message.png` · `1 Step at a time.png` · `10 años de La Viña.png` | no order: the number counts something |
| `01 Steps poster.png` | order 1 · "Steps poster" (a leading zero makes it an order) |

**Magazine and language codes**

| File | Result |
|---|---|
| `GVLV EN Welcome.png` · `GV-LV EN …` · `GV+LV EN …` · `GV&LV EN …` · `GV/LV EN …` · `GV LV EN …` · `GV_LV EN …` · `LV-GV EN …` · `AA EN Welcome.png` | both magazines · English · "Welcome" |
| `gv Welcome.png` | Grapevine (magazine codes: any capitals) |
| `Lv ES Taller.png` | La Viña · Spanish |
| `EN GV Welcome.png` | Grapevine · English (either order) |
| `GV EN-ES Welcome.mp4` · `GV BI Welcome.mp4` | English and Spanish |
| `GV English Welcome.png` | English · "Welcome" (the word right after the magazine) |
| `LV Español Bienvenidos.png` | Spanish · "Bienvenidos" |
| `ES Bienvenidos.png` | Spanish · both magazines |
| `AA EN Preamble poster.png` | both · English · "Preamble poster" |
| `AA Preamble (poster).png` | both · every language · caption "AA Preamble" |
| `AA and Grapevine.png` · `Aa ver la mesa.png` · `AA in Prison.jpg` · `AA en Tyler.jpg` · `AA en español.png` · `AA Grapevine Story.jpg` · `AA GV Welcome.png` · `AA ENGLISH TABLE.png` · `AA.png` | AA starts the title: every language, the whole name is the caption |
| `EN AA Welcome.png` · `GV AA Welcome.png` · `01 AA Preamble.png` | English / Grapevine / order 1, and the caption starts with "AA" |
| `02 AA ES Taller.png` · `AA_EN_Welcome.png` · `AA-ES Taller.png` · `AA BI Saludo.mp4` · `AA EN-ES Saludo.mp4` · `[AA][EN] Preamble.png` · `Preamble (AA).png` | AA as the code: both magazines, and the language that follows it |
| `Esto ES La Viña.jpg` · `En la mesa de Tyler.jpg` · `Es hora de servir.jpg` · `LV es hora de servir.jpg` · `LV En la mesa.jpg` · `English literature table.jpg` · `Spanish Assembly booth.jpg` · `Bienvenidos a la mesa EN Tyler.jpg` | words that only look like codes: no language, the caption is kept whole (after LV in the two LV ones) |
| `Grapevine table.jpg` · `GVR training.jpg` · `Lvl 2 display.jpg` | both magazines: a magazine's name inside a title is a word, and "GVR" is not "GV" |

**Captions, copies and odd names**

| File | Result |
|---|---|
| `PXL_20261017_183316123.jpg` · `WhatsApp Image 2026-10-17 at 6.33.16 PM.jpeg` · `Screenshot 2026-10-01 at 10.15.32 AM.png` · `DSC_0042.JPG` · `20261017_183316.jpg` · `0042.jpg` · `IMG_2045 (1).JPG` · `VID_20261017_183316.mp4` · `Captura de pantalla 2026-10-01.png` · `01.png` · `IMG-20261017-WA0003.jpg` | camera names: no caption |
| `GV EN IMG_1234.jpg` | Grapevine · English · no caption |
| `GV EN Book display IMG_1234.jpg` | caption "Book display IMG 1234" |
| `Copy of GV EN Welcome.png` · `Copia de LV ES Taller.jpg` | "Welcome" (Grapevine, English) · "Taller" (La Viña, Spanish) |
| `GV EN Welcome (1).png` · `Welcome - Copy.png` | "Welcome" |
| `GV EN Welcome (first) (2).png` · `GV EN Welcome (2) (first).png` | "Welcome" · first |
| `Step (2) poster.png` | "Step (2) poster" (a number inside the title stays) |
| `  GV   EN   Welcome   to  our   table   ( first )  (15 s) .png` | Grapevine · English · "Welcome to our table" · first · 15 seconds |
| `GV_EN_Welcome_to_our_table_(first).png` | the same, first |
| `02__GV__EN__Welcome.png` | order 2 · Grapevine · English · "Welcome" |
| `Our GV_LV table.jpg` | "Our GV/LV table" |
| `Welcome%20to%20our%20table.png` | "Welcome to our table" |
| `_README naming.txt` · `~notes for the chair.txt` · `GV EN Welcome (off) (first).png` | never shown |

**Options that do not apply are ignored**: `GV EN Note (muted) (0:15-1:30).txt` (a note has no sound or part) →
"Note"; `GV Poster (muted).png` → "Poster".

### 7.6 File types

Drive's own file type decides; when Drive gives none, the name's ending does.

| The booth shows it as | Files | Channel |
|---|---|---|
| **photo** — fills the screen, slow zoom | .jpg .jpeg .jfif .heic .heif .tif .tiff (an iPhone's HEIC through Google's converted copy) | Photos (Drive) |
| **poster** — the whole picture over a blurred copy | .png .gif .webp .svg .bmp; the first page of a PDF, a PowerPoint (.ppt .pptx .pps .ppsx), Keynote, .odp, Google Slides or Google Drawing | Posters (Drive) |
| **video** — plays from the copy saved with the site | .mp4 (best: H.264 video, AAC sound), .m4v, .webm, .mov (plays everywhere only with H.264) | Videos (Drive) |
| **sound** — plays only while the sound is on, with a headphones picture and moving bars | .mp3 .m4a .aac .wav .ogg .oga .opus | Sounds (Drive) |
| **note** — the name is the heading, the file's text the message | .txt, .md (.markdown), Google Docs, .docx | Notes (Drive text files) |
| **a problem** — never shown, listed with the reason | anything else ([7.7](#77-what-is-never-shown-and-the-problem-list)) | — |

**Notes.** The text is downloaded like a bulletin post's body and kept Markdown-light: paragraphs and line breaks,
**bold** (`**words**`), and "- " lists (a "* ", "+ " or "•" list becomes "- "); a heading becomes a bold line, a link
its words; pictures, tables and code are dropped. At most 1,200 characters are kept (cut at a word with "…"); a few
short lines read best — a long note is shown in smaller type. Its time on screen is its reading time, or its own
`(Ns)`. The run downloads at most 40 texts in all, bulletin posts first; an unchanged file keeps its text without a
new download.

**Sizes.** A video or sound file is saved for offline up to 95 MB, and the folder up to about 400 MB in all
([7.8](#78-the-offline-copies-of-drive-files)). Photos are saved as Google's 1920-pixel copies (usually well under 1
MB each), whatever their original size. A minute of phone video at 1080p is roughly 60 to 130 MB: trim it, or save it
at 720p, to stay under 95 MB. iPhones record video in HEVC by default, which not every browser plays: before filming
for the booth, set Settings → Camera → Formats → **Most Compatible**, or convert the file to .mp4 (H.264).

### 7.7 What is never shown, and the problem list

**Never shown, silently** (on purpose):

- a file switched off — `(off)`, `(apagado)`, `(draft)`, `(borrador)`, or a name starting with `_` or `~`;
- a file past its `(until …)` day — it leaves `data/site/booth.json` at the next update;
- a file the site never publishes at all, in any folder: a name with `PRIVATE`, `PRIVADO`, `(Responses)`,
  `(Respuestas)` or `wrong size`; spreadsheets, CSV and TSV files, Apps Script, Google Sites
  ([The Drive panel folder §3.10](drive-panel-folder.md#310-what-is-never-published)). `booth questions.csv` in the
  booth folder is never read — the booth's quizzes live in the repository's CSV.

**Problems** — files that can never be shown, each named with its reason (and, for a video or sound type, what to
do):

| Problem (English and Spanish words) | Example |
|---|---|
| not a type the booth can show / no es un tipo de archivo que la pantalla de la mesa pueda mostrar | `notes.zip`, a Google Form, `Old notes.doc`, `Page.html`, `Icon.ico`, a shortcut Drive would not follow |
| a video type browsers do not play — save it as .mp4 (H.264 video, AAC sound) | `intro.avi`, `Old clip.mkv`, a .wmv, .flv, .3gp, .mpg, .mts |
| a sound type browsers do not play — save it as .mp3 or .m4a | `Song.wma`, a .flac, .aif, .amr, .mid |
| no text to show — the file is empty, or its text could not be read yet | an empty `.txt`; a note whose download failed with no earlier text (a later run tries again) |
| its days never meet — the (from …) day is after the (until …) day | `Welcome (from 2027-03-15) (until 2027-03-01).png` |

They are listed in four places:

1. The **Website update** run's summary (the sync job), under **Booth folder files the booth display can't
   show** ("… the rest of the booth still updated — fix the file in the Drive booth folder"), one line per file:
   `booth/intro.avi — a video type browsers do not play — save it as .mp4 (H.264 video, AAC sound)`; the first 10
   also as yellow warnings titled **Booth folder file to fix**.
2. The Drive source's note in the same summary's "Content sources" table: *booth folder: 1 file(s) the booth display
   cannot show — intro.avi (data/site/booth.json → problems says why)* (at most four names).
3. `data/site/booth.json` → `problems`, in English and Spanish.
4. The player's Settings → **Slides** → **Files and rows the show couldn't use**: *Drive: booth/intro.avi: a video
   type browsers do not play — save it as .mp4 (H.264 video, AAC sound)*.

**Left out by the build** (not in the run summary's list): a file whose caption — or a note whose heading or text —
says a word the booth never shows ([8.9](#89-words-the-booth-never-shows)): `GV EN Donate to Grapevine.png` →
*Drive: booth/GV EN Donate to Grapevine.png: left out of the booth: it says “Donate”*, in Settings → Slides and in
the build's log (step *Build the website*, the `[booth]` lines). Rename it, or add `(no caption)` to show a picture
without its title (a hidden caption is not checked). A video or sound file the run could not save is also left out
there: *not downloaded in this build, so it is left out (videos and sound files play only from the copy saved with
the site): too big to save for offline (120.4 MB; one video or sound file may have 95 MB — config/site.yml
booth.max_file_mb)*.

### 7.8 The offline copies of Drive files

The booth plays offline, so every site update also saves a copy of the booth folder's pictures, videos and sound
files **with the website** (at `/about/booth/media/`, never in Git). The Website update run's **Build & publish
website** job does it, just before it builds the site (`scripts/build/booth-media.mjs`):

1. It brings back the files the last runs saved (GitHub keeps them in its Actions cache between runs), deletes the
   ones no longer in the folder, and downloads only what is new or changed — a photo or poster as Google's
   1920-pixel picture of it, a video or sound file whole.
2. Each saved file gets a name made from the Drive file's id, its last change and its size, then a few words of its
   title (`<stamp>-<words>.<ext>`, for example `3f9a1c07b2-our-literature-table.jpg`): a new version of the file in
   Drive gets a new name and is downloaded again — by the site and by every booth that saved the show —, an
   unchanged one never is.
3. The show's file points each slide at its saved copy; a device that saves the show for offline then keeps those
   files too ([9.1](#91-how-the-offline-copy-is-made)).

**Limits** (`config/site.yml` → `booth:`):

| Limit | Default | Beyond it |
|---|---|---|
| one video or sound file: `max_file_mb` | 95 MB | not saved → **left out of the show** (a stream from Drive is not something a booth can count on) |
| the whole folder: `max_total_mb` | 400 MB (never more than 800, whatever it says: GitHub Pages takes sites up to 1 GB) | the files marked `(first)`, then the folder's order (order numbers, then names), are kept first; past the limit a picture shows only while the booth is online (from Google's copy) and a video or sound file is left out |
| time for downloads per run | 15 minutes | what is left waits for the next run |
| tries per file | 3 (a picture 60 s each, a video 8 minutes) | tried again by the next run |

Without the optional `GOOGLE_API_KEY` (today) Drive does not give the sizes: a video of unknown size may take the
room really left in the folder, and its download stops at the limit
([The Drive panel folder §3.15](drive-panel-folder.md#315-the-optional-google_api_key)).

**The run's lines.** In the Website update run's summary (the build job):

```text
Booth display (copies for offline): 12 file(s) saved for offline, 85.3 MB (limits: 95 MB for one video or sound
file, 400 MB in all) — 3 downloaded (40.1 MB), 9 kept from the last run, 1 removed; 48 s.
- Not saved: GV EN Long talk.mp4 — too big to save for offline (120.4 MB; one video or sound file may have 95 MB —
  config/site.yml booth.max_file_mb)
```

and a yellow warning **Booth display: a file was not saved for offline** for each file not saved (the first 10).
Today, with the folder empty, the line reads "0 file(s) saved for offline, 0 B …". The other reasons a file is not
saved: "not saved for offline: the booth folder's saved files would pass 400 MB (config/site.yml
booth.max_total_mb; …)", "Google Drive answered with a web page instead of the file (too many downloads of it today,
or Drive could not check it for viruses); the next run tries again", "the download was incomplete …", "the download
failed …", "not downloaded: this run's time for downloads ran out (the next run tries again)". The step never stops
the site from being published.

The *Code check* saves no copies: its test build shows Drive pictures from Google's copy and leaves videos out.

### 7.9 Check that a file arrived

| Where | What you see |
|---|---|
| The player: Settings → **Slides** → search a word of the caption | its row ("Photo", "Poster", "Video" …), **Show now** to see it; a reason when it cannot show now (**Its Drive folder is off**, **Not in this language** …) |
| Settings → **Show** | the channel (Photos (Drive) …) and the collection with their counts |
| Settings → Slides → **Files and rows the show couldn't use** | the file, if it has a problem or was left out |
| `/about/booth.json` in a browser (search the page for the caption) | an item `"id": "drive:<file id>"` with `"source": "drive"`; its `media.src` is `/aagrapevine/about/booth/media/…` when a copy was saved (`"local": true`), or `https://lh3.googleusercontent.com/…` when it was not (pictures only: online only) |
| `data/site/booth.json` in the repository | the file as the sync read it: name, kind, magazine, languages, title, options, collection |
| The Website update run's summary | "Booth display (copies for offline): …" and the "Not saved" lines; "Booth folder files the booth display can't show" |
| `/status/` | the Drive row counts every Drive file, booth files included |

Nothing there? Check in this order: the file is inside the panel folder's booth folder (not a "Photos of the booth"
folder); a run that reads Drive has finished since you uploaded it; its name has no `(off)`, `_`, `~`, `PRIVATE`; its
`(until …)` day has not passed and its `(from …)` day has come; its language code matches the language mode; its
magazine and its collection are switched on. More in [section 10](#10-troubleshooting).

### 7.10 AA rules for the folder

The folder is public, and the booth shows its files to anyone walking by. The rules (AA's anonymity and copyright
guidance: the pamphlet *Anonymity — Our Spiritual Foundation* (P-47), AA Grapevine's copyright and reprint policy,
The A.A. Service Manual):

- **Photos of tables, displays and empty rooms only** — no faces, no full names of AA members, no screenshots of a
  Zoom gallery. A full-face photo of a member breaks anonymity even without a name.
- **No recordings of members' talks or shares** — no video or sound file of a member speaking as an AA member
  (face or voice): AA asks that talks be given in person rather than as recordings (a 1980 Conference resolution,
  quoted in P-47). Grapevine's Audio Project and La Viña's "Graba tu historia" are the magazines' own process, and
  their stories reach the booth only as links (a CSV `audio` or `video` row).
- **No Grapevine or La Viña logos, magazine covers, artwork or cartoons** (Victor E. included — his official videos
  are already in the CSV as YouTube rows), and **none of their audio or video files**: official videos and podcast
  episodes go into the CSV as links, which play from the official channel and host. Holding up the printed issue at
  the table is fine; a photo of its cover on the screen is not.
- **Only material the committee made, or has permission to use.** The postcards, flyers and posters Grapevine and
  La Viña offer reps (aagrapevine.org/gvr-resources, aalavina.org/recursos) are made to be printed for the table:
  print them rather than putting their pictures in this public folder (they carry the magazines' logos and artwork;
  when in doubt, ask Grapevine at gvrc@aagrapevine.org).
- **AAWS pamphlet covers** (not Grapevine's or La Viña's) may be shown, with © and "The above graphic is used with
  permission of A.A. World Services, Inc." — put that line in the picture itself; without it, leave the cover out.
- **Attraction, not promotion**: no sales or urgency words in captions or notes — the build leaves such a file out
  ([8.9](#89-words-the-booth-never-shows)).
- Notes follow the CSV's rules ([8.11](#811-aa-rules-for-the-content)).

---

## 8. Editing the CSV

[`content/booth/booth.csv`](../content/booth/booth.csv) is the committee's own part of the show: one row per slide.
Today it has 247 rows (55 quizzes, 25 true or false, 12 fill in the blank, 13 scrambles, 35 facts, 16 moments of
history, 15 quotes, 14 polls, 13 talking points, 11 messages, 10 QR codes, 24 official videos, 4 podcast episodes),
all fact-checked; one video is switched off until someone has watched it ([8.12](#812-check-before-an-event)). Its
short guide, [content/booth/README.md](../content/booth/README.md), says the same as this section in fewer words.

### 8.1 Edit it on GitHub

1. Open `https://github.com/NETA65/aagrapevine/blob/main/content/booth/booth.csv` (signed in with a login that has
   write access — MKP715 is enough). GitHub shows the file as a table, with a search box.
2. Press the **pencil** ("Edit this file"). Each line is one row; the first line is the header.
3. Change a cell, or add a row: copy a similar row to a new line, give it a new `id`, change its words.
4. **Commit changes…** → a short message ("booth: a quiz about the 1949 masthead") → **Commit directly to the main
   branch** → **Commit changes**.
5. Two runs start by themselves: **Code check (tests and test build)** (it checks every row; a green ✓ or a red
   ✗ in a few minutes) and **Website update** (a quick run: the site is updated about 2 minutes after it starts,
   GitHub Pages may take a few minutes more to show it).
6. A booth that is playing online picks the change up within half an hour, at its next slide; any other booth gets
   it the next time its About page is opened (or reloaded) with internet. To see it at once: open (or reload) the
   About page → **Settings** → **Slides** → search the new row → **Show now**.

A cell that holds a comma or a line break is written in double quotes (`"Yes, of course"`), and a double quote
inside it twice (`"He said ""hi"""`) — GitHub's editor shows the raw text, so type them yourself there.

### 8.2 Edit it in Excel, Google Sheets or LibreOffice

The CSV must stay **UTF-8**, or every ñ, é and ¿ is spoiled — the check then says *booth.csv: the file is not
saved as UTF-8: letters like ñ and é may be wrong (Excel: Save As → CSV UTF-8)*.

| Program | Open | Before you type | Save |
|---|---|---|---|
| **Excel** | download the file from GitHub (the "Download raw file" button), open it | select the `from`, `until`, `start` and `end` columns → Format Cells → **Text**, so Excel does not turn `2027-03-01` into `3/1/2027` or `1:30` into a time | File → Save As → **CSV UTF-8 (Comma delimited) (\*.csv)** — not plain "CSV" |
| **Google Sheets** | File → Import → Upload, untick "Convert text to numbers, dates, and formulas" | the same columns → Format → Number → **Plain text** | File → Download → **Comma-separated values (.csv)** |
| **LibreOffice Calc** | open it with Character set **Unicode (UTF-8)**, separated by comma | the same columns as Text | Save As → Text CSV → **Keep current format**, character set UTF-8, field delimiter `,`, string delimiter `"` |

Then put it back: GitHub → `content/booth` → **Add file** → **Upload files** → drop `booth.csv` (the same name
replaces the old one) → **Commit changes**. Keep the header as the first row, and add nothing under the table (no
totals, no notes in other cells).

### 8.3 Every column

Columns may be in any order and any capitals; a column the booth does not know is ignored (add your own, for
example `reviewer`). A column named twice: the first one is used, and the check names it.

| Column | For | Write | Example |
|---|---|---|---|
| `id` | every row, **needed** | a unique name: a–z, 0–9, single dashes, at most 48 characters. Keep it once chosen: a booth remembers the rows switched off on it by their id. A row whose id starts with `#` is skipped (a draft, a note) | `quiz-gvhist-founders` |
| `on` | every row | `yes` (also blank, `y`, `true`, `1`, `sí`) or `no` (also `n`, `false`, `0`) — a quick switch; a row that is off is still checked | `no` |
| `type` | every row, **needed** | quiz, truefalse, fact, quote, history, fill, scramble, poll, prompt, message, qr, video, audio, image ([8.4](#84-every-type-with-a-real-row)); capitals, spaces, dashes and slashes do not count (`True-False` is truefalse) | `quiz` |
| `pub` | every row | `gv`, `lv` or `both` (blank = both; also `Grapevine`, `La Viña`, `ambos`, `GVLV`, `GV/LV`, `aa`): the slide's colour and the Magazines switch | `lv` |
| `tags` | every row | topic words separated by spaces, `;` or `,` — letters, digits, dashes, at most 32 characters each. A booth can hide a topic. A **new** tag needs its two names in `src/_i18n/booth.json` ([11.3](#113-recipe-a-new-csv-column)) | `history;founders` |
| `weight` | every row | 0.5 to 5 (blank = 1): how likely the row is to come up, beside the others ([5.6](#56-how-the-next-slide-is-chosen)) | `2` |
| `from`, `until` | every row | days written `YYYY-MM-DD`, a year 2000–2099, Central time, both days included | `2027-03-01` |
| `seconds` | every row | 4 to 180: the time on screen instead of the computed one ([5.7](#57-how-long-a-slide-stays)) | `20` |
| `reveal` | quiz, truefalse, fill, scramble | 4 to 60: seconds before the answer shows (blank = the booth's setting, 12) | `10` |
| `title_en`, `title_es` | history (**needed**: the WHEN), message, qr, video, audio, image, fact | a heading, at most 80 characters | `June 1944` |
| `text_en`, `text_es` | every type (on video, audio and image: the caption) | the question, statement, fact, quote, message or talking point: at most 300 characters (a quiz, true or false or fill question: 180). Line breaks (in a quoted cell), `**bold**` and "- " lists show. `{event}`, `{committee}`, `{site}` are filled in ([8.7](#87-placeholders)) | `In 1944, how many AA members started the Grapevine?` |
| `choices_en`, `choices_es` | quiz, poll | 2 to 6 choices separated by `\|`, at most 70 characters each, no two the same; the same number and order in both languages | `Two\|Twelve\|Six\|Sixty` |
| `correct` | quiz, truefalse | quiz: the right choice's number (1–6) or letter (A–F); truefalse: `true` or `false` (also yes/no, t/f, verdadero/falso, cierto, sí) | `3` |
| `answer_en`, `answer_es` | fill, scramble | fill: the missing word(s), at most 60 characters; scramble: the word to unscramble, letters and spaces only, 3 to 16 letters | `digest` |
| `explain_en`, `explain_es` | quiz, truefalse, fill, scramble (shown with the answer), poll (a line under the votes) | one or two sentences, at most 240 characters | `Six members in the New York area …` |
| `credit_en`, `credit_es` | quote (**needed**), fact, history, quiz, truefalse, video, audio, image | the credit line or source note in small type, at most 200 characters (a quote gets "— " in front of it on the screen) | `Source: aagrapevine.org` |
| `media_url` | video, audio, image (**needed**) | a YouTube link, or an https `.mp4` / `.webm` video, `.mp3` / `.m4a` / `.ogg` sound, `.jpg` / `.png` / `.webp` picture, on an allowed site ([8.6](#86-links-and-qr-codes)) | `https://www.youtube.com/shorts/_mjB6hXYHn4` |
| `start`, `end` | video, audio | seconds (`90`) or m:ss (`1:30`, also h:mm:ss): play only that part. `?t=1m30s` in a YouTube link is a start too | `8:00` |
| `qr_url` | qr (**needed**), any other row | a link shown as a QR code — on a message beside its text, on a qr row big, on any row in the visitors' "Take it home" panel ("About this slide"). `{site}` or `{site_es}` at the start for a page of this site. A page, never a document file ([8.6](#86-links-and-qr-codes)) | `{site}meetings/` |
| `source_url` | quiz, truefalse, fact, history, fill (**needed**); any row | where the fact can be checked (an https link) — never shown | `https://www.aagrapevine.org/history-aa-grapevine` |
| `notes` | every row | for the committee only — never shown, never checked | `Checked 2026-10-02 on the history page.` |

### 8.4 Every type, with a real row

Each block is a real row of today's file: the cells it fills (empty ones left out), then what a visitor sees with
the starting settings (Both, English first, Normal pace).

#### quiz

Needs, in each language it is shown in: `text` and `choices`; and `correct`. Takes `explain`, `credit`, `reveal`.

| Column | Value |
|---|---|
| `id` | `quiz-gvhist-founders` |
| `type` · `pub` · `tags` | `quiz` · `gv` · `history;founders` |
| `text_en` | In 1944, how many AA members started the Grapevine? |
| `choices_en` | Two\|Twelve\|Six\|Sixty |
| `correct` | `3` |
| `explain_en` | Six members in the New York area, four women and two men, published the first issue in June 1944 with Bill W.'s blessing. |
| `credit_en` | Source: aagrapevine.org |
| `text_es` | En 1944, ¿cuántos miembros de AA fundaron el Grapevine? |
| `choices_es` | Dos\|Doce\|Seis\|Sesenta |
| `explain_es` | Seis miembros del área de Nueva York, cuatro mujeres y dos hombres, publicaron el primer número en junio de 1944 con la bendición de Bill W. |
| `credit_es` | Fuente: aagrapevine.org |
| `source_url` | https://www.aagrapevine.org/history-aa-grapevine |

On the screen: blue (Grapevine). The eyebrow "Quiz · Pregunta · Grapevine", a timer ring counting 12 seconds, the
question big and the Spanish one under it, four buttons A Two (Dos) · B Twelve (Doce) · C Six (Seis) · D Sixty
(Sesenta). At 12 seconds C lights up with ✓ and the box "Answer · Respuesta" shows both explanations; the credit line
is under it. 38.8 seconds in all (29.1 in English only). A visitor's tap answers at once ([6.1](#61-what-visitors-can-do)).

#### truefalse

Needs `text`; and `correct` (`true` / `false`). Takes `explain`, `credit`, `reveal`.

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` | `truefalse-gvhist-older-than-conference` · `truefalse` · `gv` · `history;conference` |
| `text_en` | The Grapevine is older than AA's General Service Conference. |
| `correct` | `true` |
| `explain_en` | True! The first issue came out in June 1944. Later issues reported the birth of AA's general service structure, and the Conference's Advisory Actions begin in 1951. |
| `credit_en` · `credit_es` | Source: aagrapevine.org · Fuente: aagrapevine.org |
| `text_es` | El Grapevine es más antiguo que la Conferencia de Servicios Generales de AA. |
| `explain_es` | ¡Verdadero! El primer número salió en junio de 1944. Números posteriores informaron del nacimiento de la estructura de servicios generales de AA, y las Acciones Recomendables de la Conferencia comienzan en 1951. |
| `source_url` | https://www.aagrapevine.org/history-aa-grapevine |

On the screen: "True or false? · ¿Verdadero o falso?", the statement, two big buttons **True** (Verdadero) and
**False** (Falso), the ring; at 12 seconds True lights up and the explanations show. 48.9 seconds in Both.

#### fill

Needs `text` with `___` (three underscores, once) where the answer goes, and `answer`. Takes `explain`, `reveal`.
The line in the file:

```csv
fill-gvhist-founders,yes,fill,gv,history;founders,,,,,,,The Grapevine was started in 1944 by six AA members: four women and ___ men.,,,two,"With Bill W.'s blessing, they sent the first issue to every AA group, about 300 at the time.",Source: aagrapevine.org,,"En 1944, seis miembros de AA fundaron el Grapevine: cuatro mujeres y ___ hombres.",,dos,"Con la bendición de Bill W., enviaron el primer número a todos los grupos de AA, unos 300 en ese entonces.",Fuente: aagrapevine.org,,,,,https://www.aagrapevine.org/history-aa-grapevine,
```

On the screen: "Fill in the blank · Completa la frase", the sentence with an empty box, the ring; at 12 seconds
"two" writes itself into the box (and "dos" into the Spanish one), then the explanation. Visitors get a **Show the
answer** button.

#### scramble

Needs `text` (the clue) and `answer` (3–16 letters, letters and spaces only). Takes `explain`, `reveal`.

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` | `scramble-gvhist-preamble` · `scramble` · `gv` · `history;preamble` |
| `text_en` | Unscramble it! A Grapevine editor wrote it, and it first appeared in the June 1947 issue. |
| `answer_en` | Preamble |
| `explain_en` | The AA Preamble says what AA is and what it is not. Its wording was updated after the 2021 General Service Conference (“men and women” became “people”). |
| `credit_en` | Source: P-52 (aa.org) |
| `text_es` | ¡Ordena las letras! Lo escribió un editor del Grapevine, y apareció por primera vez en el número de junio de 1947. |
| `answer_es` | Preámbulo |
| `explain_es` | El Preámbulo de AA dice qué es AA y qué no es. Su texto en inglés se actualizó tras la Conferencia de Servicios Generales de 2021 («men and women» pasó a ser «people»). |
| `source_url` | https://www.aa.org/aa-grapevine-and-la-vina-our-meetings-print |

On the screen: "Unscramble the word · Ordena las letras", the clue, the letters of PREAMBLE as shuffled tiles (the
same shuffle every time it shows) and, because the Spanish word differs, a smaller row of PREÁMBULO's tiles under
the Spanish clue; at the reveal each row slides into order. When both languages have the same word (`PODCAST`), one
row serves both.

#### fact

Needs `text`. Takes `title` (a heading), `credit`.

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` · `weight` | `fact-gvhist-mail-call` · `fact` · `gv` · `history;identity` · `2` |
| `title_en` / `title_es` | Our meeting in print / Nuestra reunión impresa |
| `text_en` | In the 1940s, AA members serving overseas wrote to a full page called “Mail Call for All AAs in the Armed Forces.” They named the Grapevine their “meeting in print,” and today Grapevine and La Viña carry the phrase on their covers. |
| `text_es` | En los años 40, miembros de AA que servían en el extranjero escribían a una página entera llamada «Mail Call for All AAs in the Armed Forces». Llamaron al Grapevine su «reunión impresa», y hoy La Viña y Grapevine llevan la frase en sus portadas. |
| `credit_en` / `credit_es` | Source: aagrapevine.org / Fuente: aagrapevine.org |
| `source_url` | https://www.aagrapevine.org/history-aa-grapevine |

On the screen: "Did you know? · ¿Sabías que…? · Grapevine", the heading, the text big, the credit; the Spanish
heading and text under a thin line. Weight 2: twice as likely as most rows. 30 seconds in Both.

#### history

Needs `title` (the WHEN: a year, a month and year) and `text`. Takes `credit`, `qr_url`.

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` · `weight` | `history-gvhist-1944-first-issue` · `history` · `gv` · `history;founders` · `2` |
| `title_en` / `title_es` | June 1944 / Junio de 1944 |
| `text_en` | Six AA members in the New York area, four women and two men, publish the first Grapevine with Bill W.'s blessing, just nine years after AA began. |
| `text_es` | Seis miembros de AA del área de Nueva York, cuatro mujeres y dos hombres, publican el primer Grapevine con la bendición de Bill W., apenas nueve años después del comienzo de AA. |
| `credit_en` / `credit_es` | Source: aagrapevine.org / Fuente: aagrapevine.org |
| `qr_url` | https://www.aagrapevine.org/history-aa-grapevine |
| `source_url` | https://www.aagrapevine.org/history-aa-grapevine |

On the screen: "From our history · De nuestra historia", **June 1944** very big, the text, the Spanish text under it.
The `qr_url` is not drawn on a history slide: it is the "About this slide" code of "Take it home".

#### quote

Needs `text` and `credit`, word for word ([8.11](#811-aa-rules-for-the-content)).

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` | `quote-service-tradition-1` · `quote` · `both` · `service;traditions` |
| `text_en` | Our common welfare should come first; personal recovery depends upon A.A. unity. |
| `credit_en` | Tradition One (short form). Reprinted from AA Grapevine and La Viña: Our Meetings in Print (P-52), p. 17, with permission of Alcoholics Anonymous World Services, Inc. |
| `source_url` | https://www.aa.org/aa-grapevine-and-la-vina-our-meetings-print |

On the screen: grape (both magazines), a big quotation mark, the quote in large type and "— Tradition One (short
form). Reprinted from …" under it. English only (no official Spanish text was available to quote), so it never shows
in Español; in Both and Alternate it shows in English.

#### poll

Needs `text` and `choices` (2–6). Takes `explain` (a line under the votes). The line in the file:

```csv
poll-service-group-rep,yes,poll,both,service;gvr;rlv,,,,,,,Does your home group have a GVR or RLV right now?,Yes!|Not right now|I'm not sure,,,"Each group decides for itself (Tradition Four). If yours is curious, ask us how it works.",,,¿Tu grupo base tiene RLV o GVR en este momento?,¡Sí!|Por ahora no|No lo sé,,"Cada grupo decide por sí mismo (Cuarta Tradición). Si al tuyo le interesa, pregúntanos cómo funciona.",,,,,,,"Poll: no names, no group names, no ranking; the explanation keeps it pressure-free (Tradition Four; GVR Workbook 2026 p. 52)."
```

On the screen: "Quick poll · Encuesta rápida", the question, three rows **Yes! (¡Sí!)** · **Not right now (Por
ahora no)** · **I'm not sure (No lo sé)** with bars and percentages of this device's votes, the note **Tap an answer
to vote** or **2 votes at this table**, and the explanation with a light bulb. 14 seconds; a vote keeps it on screen
at least 7 seconds more.

#### prompt

Needs `text`.

```csv
prompt-write-funny,yes,prompt,gv,writing;humor,,,,,,,What's the funniest thing that's happened to you in sobriety? Could it become a joke for Grapevine's At Wit's End page?,,,,,,,¿Qué es lo más gracioso que te ha pasado en tu vida sobria? ¿Podría convertirse en un chiste para la página At Wit's End de Grapevine?,,,,,,,,,,At Wit's End = Grapevine's jokes page (GV guidelines; research.md C3). Keep it clean: nothing about drinking.
```

On the screen: "Let's talk · Conversemos", the question big, and **Tell us at the table · Cuéntanos en la mesa** under
it. 14 seconds. (The `notes` cell is for the committee only.)

#### message

Needs `text`. Takes `title` (the heading), `qr_url` (shown beside the text).

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` | `message-fun-event-committee` · `message` · `both` · `message;committee` |
| `title_en` / `title_es` | Thanks for stopping by / Gracias por visitarnos |
| `text_en` | The {committee} meets on Zoom every month, and every AA member is welcome. Ask us for the details. |
| `text_es` | El {committee} se reúne por Zoom cada mes y todos los miembros de AA son bienvenidos. Pídenos los detalles. |
| `qr_url` | {site}meetings/ |
| `source_url` | https://neta65.org/trusted-servants/grapevine-la-vina/ |

On the screen: the heading, the text — "The NETA 65 Grapevine & La Viña Committee meets on Zoom every month …" / "El
Comité de Grapevine y La Viña de NETA 65 se reúne por Zoom cada mes …" — and the QR code of `/meetings/` beside it
(`/es/meetings/` when Spanish leads).

#### qr

Needs `qr_url`, and `title` or `text`.

```csv
qr-fun-site,yes,qr,both,qr;online,,,,,,"Our table, in your pocket","Our committee’s site: this month’s issues, events, story deadlines, the GVR/RLV corner and more, in English and Spanish.",,,,,,"Nuestra mesa, en tu bolsillo","El sitio de nuestro comité: los números del mes, eventos, fechas para enviar historias, el rincón del GVR/RLV y más, en español e inglés.",,,,,,,,{site},,"The site home ({site}). English pages offer Spanish-first browsers a '¿Prefieres español?' banner (src/_includes/partials/lang-banner.njk), so one QR serves both languages."
```

On the screen: a big QR code, "Scan to take it home · Escanea para llevártelo", the heading and text, and the
address printed under the code (`neta65.github.io/aagrapevine`). `{site}` gives the English home on English-led
slides and `…/es/` on Spanish ones. 14 seconds.

#### video

Needs `media_url` (YouTube, or an https .mp4 / .webm on an allowed site), and `title` or `text` (the caption).
Takes `credit`, `start`, `end`. Needs internet.

```csv
video-gv-victor-e-is-back,yes,video,gv,video;official;humor,,,,,,Victor E. is back,Victor E. returns with a quick tour of the ways Grapevine helps alcoholics in their recovery.,,,,,AA Grapevine & La Viña on YouTube,Victor E. ha vuelto,En inglés: Victor E. regresa con un recorrido rápido por las formas en que Grapevine ayuda a los alcohólicos en su recuperación.,,,,AA Grapevine & La Viña en YouTube,https://www.youtube.com/shorts/_mjB6hXYHn4,,,,https://www.youtube.com/watch?v=_mjB6hXYHn4,"Short, 0:44 (2025-11-18); also the /watch/ hero video. title translated (es). La Viña's own Spanish version is video-lv-victor-e-ha-vuelto."
```

On the screen: a YouTube **Short** shows upright in a phone-shaped frame with "Watch · Mira", its title, text and
credit beside it; a normal video fills the screen with its caption at the bottom. Muted unless the sound is on,
captions on, YouTube's privacy-enhanced player. It plays its 44 seconds and the next slide comes. A longer one stops
at 90 seconds (Timing & sound), or at its `end`: `video-lv-historia-e-impacto` (8:09 long) has `end` = `8:00`, so even
a booth that allows 900 seconds never plays its last 9. A `watch?v=` link the official channel lists as a Short is
shown as a Short too.

#### audio

Needs `media_url` (an https .mp3 / .m4a / .ogg on an allowed site — the podcast's host), and `title` or `text`.
Plays only while the sound is on; needs internet.

| Column | Value |
|---|---|
| `id` · `type` · `pub` · `tags` | `audio-digital-podcast-hope` · `audio` · `gv` · `podcast;audio;corrections` |
| `title_en` / `title_es` | Podcast: The Day Hope Arrived / Podcast: El día que llegó la esperanza |
| `text_en` | A member shares his experience in prison, and how a Grapevine he picked up by chance, and later the Big Book, opened the door to AA. |
| `text_es` | Episodio en inglés: un miembro habla de su experiencia en prisión y de cómo un ejemplar de Grapevine que tomó por casualidad, y luego el Libro Grande, le abrieron la puerta a AA. |
| `credit_en` / `credit_es` | Grapevine Podcast (official) / Podcast de Grapevine (oficial) |
| `media_url` | https://episodes.captivate.fm/episode/3566b338-b747-455b-aa0b-7e353fdb922c.mp3 |
| `start` | `0` |
| `qr_url` | {site}listen/ |
| `source_url` | https://www.aagrapevine.org/podcasts |

On the screen: a headphones picture, "Listen · Escucha", the title and text, moving bars; the first 90 seconds of the
episode play. With the sound off the row waits (Settings → Slides: **Plays only with the sound on**).

#### image

Needs `media_url` (an https .jpg / .png / .webp on an allowed site) and `title` or `text`. Needs internet. None in the
file today — pictures of our own tables go into the Drive booth folder, where they are saved for offline. A row would
look like this (a made-up address):

| Column | Value |
|---|---|
| `id` · `type` · `pub` | `image-literature-table-2027` · `image` · `both` |
| `title_en` / `title_es` | Our literature table / Nuestra mesa de literatura |
| `media_url` | https://www.neta65.org/wp-content/uploads/2027/03/literature-table.jpg |

On the screen: the picture shown whole over a blurred copy, the caption at the bottom; 8 seconds (Seconds for each
photo), longer when the row has a `text` to read.

### 8.5 Languages

- A row is shown in **English** when it has any of its English words (`title_en`, `text_en`, `choices_en`,
  `answer_en`, `explain_en`, `credit_en`), in **Spanish** when it has any Spanish words. Write both, or only one.
- Once a row has anything in a language, it needs **everything its type needs** in that language: a quiz with
  `text_es` but no `choices_es` is a mistake (*choices_es is empty, but other Spanish cells are filled (text_es):
  fill it in, or empty them*).
- A row with no words at all is a mistake — except a video, audio or image row, which then plays in every language.
- `choices` need the same number, in the same order, in both languages (the Spanish C is the English C).
- An English-only row never shows in the Español mode, a Spanish-only one never in English. In Both and Alternate a
  one-language row shows in its own language ([5.5](#55-languages-on-the-screen)).
- House style for Spanish: Latin-American Spanish with "tú"; AA's own words (grupo base, padrino / madrina, Paso
  Doce, RLV, GVR, puesto de servicio, la Comunidad); **La Viña first** in a Spanish text that names both magazines
  ("La Viña y Grapevine").
- A video whose sound is in the other language says so in its caption: "In Spanish: …", "En inglés: …".

### 8.6 Links and QR codes

**Allowed sites** for `media_url` and `qr_url` (AA's non-affiliation: links only to AA, Grapevine, La Viña, NETA 65
and this site):

| Site | Addresses |
|---|---|
| YouTube | `youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`, `youtube-nocookie.com`, `www.youtube-nocookie.com` |
| AA Grapevine | `aagrapevine.org`, `www.aagrapevine.org` |
| La Viña | `aalavina.org`, `www.aalavina.org` |
| A.A. World Services | `aa.org`, `www.aa.org` |
| NETA 65 | `neta65.org`, `www.neta65.org` |
| This site | `neta65.github.io` (the site's own address) |
| The podcast's host | `episodes.captivate.fm`, `podcasts.captivate.fm`, `player.captivate.fm` (not any other `*.captivate.fm`) |

Every link must start with `https://`. Refused: `http://…`, `mailto:…`, another site (*qr_url: www.facebook.com is
not one of the allowed sites (YouTube, aagrapevine.org, aalavina.org, aa.org, neta65.org, the podcast's
captivate.fm, this website)*), and tricks such as `https://www.aa.org@other.site/`. The Code check also makes sure a
YouTube row plays a video of the official AA Grapevine & La Viña channel and a podcast row an episode the site
lists (`data/site/videos.json`, `data/site/episodes.json`) — a video the channel published today is in that list
after the next daily run.

**YouTube links** the booth reads: `https://www.youtube.com/watch?v=<id>`, `https://youtu.be/<id>`,
`https://www.youtube.com/shorts/<id>` (shown as a Short), `https://www.youtube.com/embed/<id>`,
`https://www.youtube-nocookie.com/embed/<id>`, `https://m.youtube.com/watch?v=<id>`; `?t=90`, `?t=1m30s` or
`?start=90` start it there (the `start` column wins).

**`qr_url` and the site's own pages.** Write `{site}` (or `{site_es}`) at the start for a page of this site:

| `qr_url` | English-led slide | Spanish-led slide |
|---|---|---|
| `{site}contribute/` | `https://neta65.github.io/aagrapevine/contribute/` | `https://neta65.github.io/aagrapevine/es/contribute/` |
| `{site}` | the English home | `…/aagrapevine/es/` |
| `{site_es}meetings/` | `…/es/meetings/` | `…/es/meetings/` (the Spanish page on every slide) |
| `{site}shop/#carry` | `…/shop/#carry` | `…/es/shop/#carry` |
| `https://www.aalavina.org/comparte` | the same code on every slide | the same |
| `https://www.aa.org/{site}` | refused: `{site}` only at the start | |

**Never a document file.** The address is printed under the code, and a visitor never reads "PDF": a `qr_url`
whose path names a .pdf file is refused (*qr_url: a link to a document file (its address shows under the code): link
to the page that offers the document*). Link the page that offers the document instead.

Where a row's QR code shows: on a **qr** row (big), on a **message** (beside the text), and for every row in the
visitors' **Take it home** panel as "About this slide".

### 8.7 Placeholders

Three words in braces are filled in by the player, in each text cell (`title`, `text`, `choices`, `answer`,
`explain`, `credit`):

| Placeholder | Becomes | Example cell → on the screen |
|---|---|---|
| `{event}` | the event's name in the slide's language (the Spanish name on Spanish slides, else the English one); "this event" / "este evento" while none is set or "Show the event name at the top" is off | `Welcome to {event}!` → "Welcome to NETA 65 Spring Assembly!" — with no name, "Welcome to this event!" |
| `{committee}` | "NETA 65 Grapevine & La Viña Committee" / "Comité de Grapevine y La Viña de NETA 65" | `The {committee} meets on Zoom every month` → "The NETA 65 Grapevine & La Viña Committee meets on Zoom every month" |
| `{site}` | the site's address, `neta65.github.io/aagrapevine` | `Everything is at {site}` → "Everything is at neta65.github.io/aagrapevine" |

Any other word in braces is a mistake (*text_en: {Event} is not a placeholder the booth knows ({event}, {committee},
{site})* — capitals count). `{site_es}` works only at the start of a `qr_url`. Spanish tip: event names rarely take
an article well ("¡Bienvenidos a Asamblea de Primavera…!" lacks its "la"), so put `{event}` where the name stands
alone — `{event}: pregúntanos sobre La Viña` — or leave the greeting to the welcome slide.

### 8.8 Switching a row off, weights and dates

| You want | Do | Result |
|---|---|---|
| a row off for everyone, kept in the file | `on` = `no` | still checked, not in the show (and not listed in Settings → Slides) |
| a draft that is not checked yet | start its `id` with `#` (`#quiz-new-idea`) | skipped entirely |
| a row off on one device only | Settings → Slides → its switch | that device only, remembered by the id |
| a row shown more often | `weight` = `2` (up to `5`) | twice as likely as a weight-1 row whenever both may come |
| a row shown less often | `weight` = `0.5` | half as likely |
| a row for a time | `from` = `2027-03-01`, `until` = `2027-03-21` | shown from March 1 to March 21, 2027 (Central days, both included); outside them Settings → Slides says **Not on today's date** |
| a row only on assembly weekend | `from` and `until` = the assembly's days | it appears by itself on the Friday, also on a booth that saved the show weeks before |
| more time on screen | `seconds` = `25` | 25 seconds (× pace) instead of the computed time |
| a longer wait before the answer | `reveal` = `20` | the answer at 20 seconds |

"today only" is refused in a text that has no `{event}` in it: the same rows play on many days. "Today only at
{event}" is fine.

Keep a mix of true and false answers and spread the right quiz choices over A–D (today: 10 true, 15 false; right
answers in place 1 ×11, 2 ×16, 3 ×14, 4 ×14), so guessing does not pay.

### 8.9 Words the booth never shows

These words are refused in every shown cell of the CSV (titles, texts, choices, answers, explanations, credit lines —
never `notes` or the links), in the Drive folder's captions and notes, and in every live item (an official video's
title, a bulletin post, an event's name). A CSV row that says one is a mistake; a Drive file or live item is left out
(a list loses only that row) and named in Settings → Slides.

| Refused | Why — and what to write instead | Example line |
|---|---|---|
| "PDF", "PDFs" | visitors never read it: say "document" | *text_en: “PDF” is not used on the booth — say “document” instead* |
| donate, donation, donativo … (any word with "donat") | Grapevine and La Viña take no donations: say "Carry the Message gift" | *text_es: “donativo” is not used on the booth — Grapevine and La Viña take no donations (say “Carry the Message gift”)* |
| "contribution(s) to (the) (AA) Grapevine / La Viña", "contribuir / contribución a La Viña" | AA Grapevine, Inc. does not accept contributions | *text_en: “contribution to Grapevine” is not used on the booth — AA Grapevine, Inc. does not accept contributions* |
| "buy now", "hurry", "limited time", "act now", "last chance", "don't miss", "subscribe now / today", "download now / today" (also "download it now"), "sale!", "before prices go up / rise / change", a shouted "Subscribe!" — and in Spanish "compra ya / ahora", "apúrate", "date prisa", "tiempo limitado", "última oportunidad", "suscríbete ya / hoy / ahora", "¡Suscríbete!", "descárgala ahora", "antes de que suban los precios" | no sales or urgency words: attraction, not promotion | *text_en: “Buy now” is not used on the booth — no sales or urgency words: attraction, not promotion* |
| "reach millions", "llegan a millones", "183 Challenge", "Reto 183" | claims no source was found for: leave them out | *text_es: “Reto 183” is not used on the booth — an unverified claim (no source found): leave it out* |
| "Conference-approved" / "aprobada por la Conferencia", in a cell that names Grapevine or La Viña | the Conference **recognizes** Grapevine as the international journal of AA: say "recognized by the Conference as the international journal of AA" | *text_en: “Conference-approved” is not used on the booth — say “recognized by the Conference as the international journal of AA”* |
| "today only", "solo hoy", "únicamente hoy" — in a cell without `{event}` | the booth shows the same rows on many days | *text_en: “Today only” is not used on the booth — “today only” needs {event} (the booth shows the same rows on many days)* |

Informative wording stays: "Download the app today", "ask us how to subscribe", "Where can you download the La Viña
app today?", the Service Manual's own "Conference-approval process". Today's two official Shorts "Download Now! Then
Subscribe!" and "¡Descárgala ahora! ¡Luego suscríbete!" are left out of the live videos for this reason.

### 8.10 How mistakes are reported

A row with any mistake is **left out** of the show; every other row still plays, and the site still updates. Each
mistake is one line, naming the row by its number as a spreadsheet shows it (the header is row 1; on GitHub that is
the line number, as long as no cell above it holds a line break) and its id:

```text
booth.csv row 14 (quiz-12): correct "4": there are only 3 choices
```

You see it in four places:

1. **Code check** (GitHub → **Actions** → **Code check (tests and test build)**): a red ✗ a few minutes after
   the commit. Open the run → **Python tests (offline)** → **Run the tests**: the failing test
   (`test_no_problem_at_all` in `tests/test_booth_csv.py`) prints every line. GitHub e-mails the person who
   pushed, when that person has its failure e-mails switched on
   ([Automation and troubleshooting §8.3](automation-and-troubleshooting.md#83-who-gets-githubs-run-failed-e-mails)).
2. **The build** (the Website update run → **Build & publish website** → **Build the website**): a warning
   `[booth] 1 problem(s) — left out of the booth display:` followed by the lines (CSV rows, Drive files, settings;
   live items are listed only in the player).
3. **The player**: Settings → **Slides** → **Files and rows the show couldn't use**, in the page's language.
4. **On a PC**: `python tests/test_booth_csv.py content/booth/booth.csv` prints the same lines —
   `content\booth\booth.csv: 246 row(s) shown, 0 problem(s)` today ([11.8](#118-tests-to-run)).

More lines, as the check writes them (each also has a Spanish twin for the Spanish page):

| Mistake | Line |
|---|---|
| a comma in a text without quotes | *booth.csv row 3 (fact-comma): the row has 5 cells but the header has 4: a comma inside a text needs the whole cell in double quotes* |
| a quote never closed | *booth.csv row 5: a cell starts with a double quote (") that is never closed: everything after it was read as that one cell* |
| an id with capitals or spaces | *id "Fact-Caps": use only a–z, 0–9 and dashes (no spaces or capitals), at most 48 characters* |
| an id used twice | *id "fact-ok" is already used in row 2* |
| a typo in on / type / pub | *on "maybe": write yes or no* · *type "trivia" is not one of: quiz, truefalse, …* · *pub "AA Grapevine": write gv, lv or both* |
| a date Excel changed | *from "3/1/2027": a date written YYYY-MM-DD, year 2000–2099 (Excel may have changed it: format the column as Text)* |
| dates the wrong way round | *until (2027-04-01) is before from (2027-05-01)* |
| out of range | *weight "0.25": a number from 0.5 to 5* · *seconds "200": a whole number from 4 to 180* · *reveal "2": a whole number from 4 to 60* |
| a column the type does not take | *reveal is only for quiz, truefalse, fill and scramble rows* · *choices_en is only for quiz and poll rows* · *media_url is only for video, audio and image rows* |
| too long | *title_en is 81 characters long: at most 80* · *text_en is 181 characters long: at most 180* (a quiz question) |
| choices | *choices_en: give 2 to 6 choices separated by \|* · *choices_en: two choices are the same ("yes")* · *choices_en has 3 choices and choices_es has 2: both languages need the same number, in the same order* |
| the right answer | *correct is empty: the number (1–6) or letter (A–F) of the right choice* · *correct "E": there are only 3 choices* · *correct "maybe": write true or false* |
| fill and scramble | *text_en: put ___ (three underscores) where the answer goes* · *answer_en "AA2026": letters and spaces only, 3 to 16 letters* |
| a missing source | *source_url is empty: where can this be checked? (an https:// link)* |
| links | *media_url "http://www.youtube.com/watch?v=…": not an https:// link* · *media_url "https://episodes.captivate.fm/episode/x.mp3": a YouTube video or an https .mp4 / .webm file* (an .mp3 on a video row) · *start "1:75": seconds (90) or m:ss (1:30)* · *end (1:30) is not after start (2:00)* |
| the file | *booth.csv: the file is not saved as UTF-8 …* · *booth.csv header: the header (first row) has no type column* · *booth.csv header: column text_en is in the header twice: the first one is used* |

### 8.11 AA rules for the content

The check refuses what it can see ([8.9](#89-words-the-booth-never-shows)); the rest is up to whoever writes the
row. The rules come from AA's own guidance (the Traditions, *Anonymity — Our Spiritual Foundation* (P-47), The A.A.
Service Manual, AA Grapevine's copyright and reprint policy, the 1960 Advisory Action on an "informative attitude"):

- **Only Grapevine and La Viña** — their history, how they work, writing for them, GVR / RLV service, the apps,
  podcast and YouTube, Carry the Message, prices as information, our committee's meetings and events — and AA texts
  about them. No outside issues, nothing that endorses an outside business.
- **Facts only from official sources** (aa.org, aagrapevine.org, aalavina.org, AA literature), with the link in
  `source_url` and a short source note in `credit` where it helps ("Source: aagrapevine.org").
- **Quotes from A.A. World Services texts word for word**, with their exact credit line — "Reprinted from (the
  publication, its page), with permission of Alcoholics Anonymous World Services, Inc." Present the Steps and
  Traditions exactly as published; never shorten or "update" them, never present a paraphrase as the text. The AA
  Preamble is AA Grapevine, Inc.'s, not AAWS's: word for word in its 2021 wording ("…a fellowship of people…"), with
  its own credit line, "Copyright © by AA Grapevine, Inc.; reprinted with permission." The Responsibility Statement
  may be shown word for word too, from one source, with a source note (no copyright line exists for it:
  [8.12](#812-check-before-an-event)). Spanish only from an official Spanish text — otherwise leave the row
  English-only, as today's 14 quotes are.
- **Grapevine and La Viña material is paraphrased, never quoted**: stories, the Statement of Purpose, the editorial
  policy, the workbooks, Daily Quotes (AA Grapevine grants no "brief excerpt" permission). The one exception is the
  site's own: the live **Daily quotes** channel shows the day's quote exactly as the Home page does, with its
  attribution and a link to the official page — never add a Daily Quote to the CSV, and switch that channel off in
  Settings → Show to leave it out.
- **No covers, logos, artwork or cartoons** of Grapevine or La Viña, and none of their audio or video files: link the
  official video or episode instead (a `video` or `audio` row plays it from its official home).
- **Attraction, not promotion**: information and invitations — "you might", "ask us", "consider" — never pressure,
  guilt, quotas or rankings; prices only as information (the live prices slide dates them). Grapevine takes no
  contributions: groups support it by buying and using the magazines.
- **Accurate terms**: "the international journal of Alcoholics Anonymous", "recognized by the Conference" (never
  "Conference-approved"), "Carry the Message gift" (never "donation"), "AA Grapevine, Inc." for the publisher.
- **Anonymity**: first name and last initial at most; polls and quizzes never ask for names.
- **Verified only**: never the numbers or dates no source supports ("millions", the "183 Challenge").

### 8.12 Check before an event

A few rows rest on facts that can change, or that need a person's look. Before an event (or once a season):

1. **La Viña's weekly open meeting** (Thursdays from November 5, 2026, 11 a.m. Central) is known only from La Viña's
   flyer. Rows `quiz-lv-open-meeting-day` and `fact-lv-weekly-open-meeting` say "according to La Viña's flyer".
   Check aalavina.org; if the day or time changed, fix those rows — and the Meetings slide's source,
   `lavina_weekly_open` in `config/site.yml` ([Automatic sources §3.11](automatic-sources.md#311-weekly-open-meetings)).
2. **The record-your-story phone lines.** Grapevine's Audio Project line was reported down in May 2026, so no row
   shows its number: `message-write-record-gv`'s QR code leads to the official page instead. La Viña's "Graba tu
   historia" number does show, in `quiz-write-lv-record` and `qr-write-graba-lv`: call it; if it does not answer,
   set those rows to `on` = `no` (or switch them off on the booth, Settings → Slides).
3. **La Viña's story e-mail address** in `fact-write-record-at-home` and `message-write-send-lv` is the
   committee's choice of October 2026 (the site's `links.lv_email_editorial`); La
   Viña's recording page names a different address for audio files. If La Viña's pages change it, change the rows.
4. **`video-lv-aplicaciones`** is off (`on` = `no`): its 2023 description gives Grapevine's digital price, and La
   Viña's is different. Watch it once; if the video does not show that price as La Viña's, set `on` = `yes`.
5. **Facts checked on official pages** (not in the committee's research brief): `truefalse-service-1978-table`,
   `fact-service-1954-reporter`, `quiz-gvhist-wits-end`, `truefalse-gvhist-slogans`,
   `truefalse-gvhist-big-book-stories`, `fact-gvhist-serenity-prayer`, `fact-gvhist-responsibility`,
   `fact-gvhist-early-pages`, `fact-gvhist-humor`, `fact-gvhist-masthead`, `quiz-lv-first-name`,
   `truefalse-lv-only-translations`, `quiz-lv-first-subscribers`, `truefalse-lv-local-newsletters`. Each row's
   `source_url` names its page (and most rows' `notes` say what it says); look again when that page changes.
6. **The Responsibility Statement** (`quote-service-responsibility`) follows aagrapevine.org/about-us word for word
   ("the hand of AA"); its Spanish is the official 2025 wording. Keep both exactly as they are.
7. **Page numbers of The A.A. Service Manual** (2024–2026 edition: pp. 81 and 83–85) in the credit lines: check them
   when the 2026–2028 edition comes out.
8. **Audio and subscriptions**: `fill-digital-three-formats` says audio stories come with digital subscriptions and
   to "check the store" — which plan includes what may change.
9. **Dates that age**: "In 2026 it turned 30" (La Viña: `quiz-lv-first-issue`, `truefalse-lv-anniversary-july`,
   `fact-lv-thirty-years`) and "from Nov. 5, 2026" stay true as written, but read oddly years later: reword them
   when they do.
10. **Official videos**: the newest 30 come and go by themselves. Before an event, a quick look at Settings → Slides
    (search "video") shows what will play; switch one off on the booth if it does not suit the room.

---

## 9. Offline and updates

### 9.1 How the offline copy is made

1. **When.** Each time the show starts with internet, and each time new content arrives while it plays — as long
   as Settings → Kiosk → **Save for offline when the show starts** is on (the default). **Save now** (Settings →
   Offline) saves on demand, whatever that setting says.
2. **What.** Both About pages (kept with the site's saved pages, so the page itself opens offline), the show file
   `/about/booth.json`, and every file of this site that the show's slides use: the saved copies of the Drive folder's
   photos, videos and sounds, and the small pictures the site keeps. It keeps them **whatever the switches say** — a
   channel, a magazine, a collection, a topic or a language switched off — so a switch turned back on at the table,
   offline, still finds its files. YouTube, the CSV's web files and the podcast are on other sites and are never
   kept.
3. **Progress.** A chip at the top right of the screen: **Saving for offline…**, **Saving for offline 23 of 86**,
   then **Ready offline ✓** for 8 seconds. A save that ends badly shows its line for 12 seconds
   ([4.7](#47-offline)). The page's chip and Settings → Offline say the same.
4. **How.** The site's service worker (the part of the browser that serves the site offline) does the saving, into
   its own store, `gvlv-booth-v1`. A browser lets it work about 5 minutes at a time, so a big save runs in rounds of
   4 minutes and goes on by itself; a file already kept is skipped.
5. **Tidy.** Files the show no longer names (a photo taken out of the Drive folder, an older version of a video)
   leave the copy at the next save — never before the new show file itself is saved.
6. **Retries.** Started without internet: saved as soon as the connection comes back. Some files failed: **Some
   files couldn't be saved (3) — they will be tried again.**, 10 minutes later. No answer: **Saving stopped without
   an answer. It will be tried again.**, 2 minutes later. Out of room: **This device ran out of room: some files
   couldn't be saved for offline.** — no retry.
7. **An old site version.** On a device that had the site before the booth existed, the new service worker may wait
   behind the old one. The booth asks it to take over for its own save; when that cannot happen yet, it says
   **Reload the page to finish updating the site, then start the booth again.**
8. **No service worker** — a private window, a locked-down browser, a very old one: **This browser can't keep an
   offline copy.** The show still plays while online.
9. The first save asks the browser, once, to keep the site's storage for good ("persistent storage").

### 9.2 What plays offline, and what needs internet

| Plays offline, once saved | Needs internet (left out quietly while offline) |
|---|---|
| every CSV row except video, audio and image rows | the CSV's video, audio and image rows (YouTube, web files, the podcast) |
| Drive photos and posters that have a saved copy; Drive videos and sound files (they play only from the saved copy); Drive notes | Drive pictures without a saved copy (past the folder's limit): shown from Google's copy |
| the live events (and the countdown), daily quotes, story themes, prices, Books of the Month, meetings, bulletin posts — as of the last save | the official videos and the podcast |
| every QR code (the show file carries them as pictures), the welcome and about slides | a flyer's small picture on an events row, when it comes from Google |

The booth tells offline from online by the browser's own signal and a tiny request to the site every minute. Offline,
the slides that need internet leave the show (Settings → Slides: **Needs internet**; Settings → Offline:
**Offline — the show plays from the saved copy**); back online, they return. Rows of the live lists still end on
time offline: an event leaves its list when it ends, a daily quote two days after its date.

The About page opened offline (from a bookmark, or the address typed) comes from the saved copy, and its chip says
**You're offline · Ready offline** when the copy is complete.

### 9.3 Storage on the device

- The copy holds the show file (about 520 KB), the two pages, and the saved Drive files — up to the folder's 400 MB.
  Settings → Offline shows how much the site uses ("This site uses 4.6 MB of the 10.0 GB this browser allows.").
- **Persistent storage: yes** means the browser will not clear it on its own. With **no**, it may be cleared when
  the device runs low on space. Browsers decide by themselves; installing the site as an app (Edge: **…** → Apps →
  **Install this site as an app**; Android Chrome: **Add to Home screen**) often tips them to yes.
- Safari (iPhone, iPad) may delete a site's saved data after about a week without a visit; a Home Screen icon is
  spared that. Do the night-before save within a few days of the event, or use the icon.
- Do not "clear browsing data" or "clear site data" on the booth device: that removes the offline copy, the
  settings, the PIN and the votes.

### 9.4 New content while it plays

- **The site.** Every site update rebuilds the show file: the morning refresh (about 4:30 AM Central), the nightly
  full update, the midday and evening refreshes, and a quick run after every saved change (the CSV,
  `config/site.yml`) or one started by hand. The live items are as fresh as that update ("Content as of …").
- **A running booth.** Every 30 minutes (Settings → Kiosk → **Look for new content every (minutes)**, 5 to 1440)
  it asks the site for the show file. When the file is new — any slide or the site's starting settings changed — it
  swaps in at the next slide, quietly (screen readers hear "New content arrived; it shows from the next slide."). The
  device's settings stay; a slide that is gone simply stops coming. Then the new files are saved for offline.
- **A page that opens.** The About page reads the newest show from the site when it is opened (or reloaded) online
  (or its saved copy after 6 seconds without an answer). It then keeps that show for as long as it stays open:
  leaving the show and starting it again plays the same show file, so reload the page to get a newer one at once —
  or let the show run, and the check above brings it within half an hour.
- **Offline**, it keeps the last saved show until it is online again.

### 9.5 Remove the offline copy

Settings → **Offline** → **Remove the offline copy** → "Remove the booth's offline copy from this device? The show
will need internet until it is saved again." → **The offline copy was removed.** A retry or a save waiting for its
turn is cancelled too. The About pages stay among the site's saved pages (remove them on the site's "Saved pages &
app" page, `/offline/`). The browser's own "clear site data" removes everything at once — settings, PIN and votes
included.

---

## 10. Troubleshooting

First look in Settings → **Slides**: the filter **On, but not now** says why each slide is waiting, and **Files and
rows the show couldn't use** lists what the build left out. Then the Website update run's summary on GitHub
([7.7](#77-what-is-never-shown-and-the-problem-list), [8.10](#810-how-mistakes-are-reported)).

| Symptom | Likely cause | Fix |
|---|---|---|
| A YouTube slide stays black, or YouTube videos never play | YouTube is blocked or slow on the venue's network (church and hotel Wi-Fi often filter it), a content blocker or strict tracking prevention blocks YouTube's player, or the device is offline. The frame shows the video's picture while the player loads; a video that has not started after 12 seconds is skipped, and every YouTube video then waits 10 minutes (Settings → Slides: **YouTube isn't answering**) | Test the venue's network the day before (open a YouTube video there). Allow `youtube.com` and `youtube-nocookie.com` in the blocker, or set tracking prevention to Balanced. For that event, switch off **Web videos (YouTube)** and **Official videos** in Settings → Show — the rest plays — or use a phone's hotspot |
| A visitor's tap opened YouTube, or left the show | YouTube's own title and logo links stay clickable (YouTube's rules) | Lock the device to the browser: a kiosk mode, Guided Access, app pinning ([2.3](#23-lock-the-device-to-the-show)) |
| "Not saved for offline yet" stays, or nothing is saved | the show was never started with internet on this browser; **Save for offline when the show starts** is off; a private window or a locked-down browser (**This browser can't keep an offline copy**); the site's new version waits behind an old one (**Reload the page to finish updating the site, then start the booth again.**) | Start the show once with internet (or Settings → Offline → **Save now**); turn the setting on; use a normal window; reload the page and start again |
| It played offline last week, but now asks for internet | the browser cleared its storage (**Persistent storage: no**, low space, Safari's week without a visit), or someone cleared site data | Save again with internet before each event; install the site as an app; keep free space ([9.3](#93-storage-on-the-device)) |
| "Some files couldn't be saved (3)" | a weak signal, or a file removed from the site meanwhile | Leave it online: it tries again in 10 minutes (or press **Save now**) |
| "This device ran out of room" | the device is full | Free space on the device, or make the booth folder smaller (fewer or shorter videos, or a lower `max_total_mb` in `config/site.yml`): the copy keeps every file the show names, whatever is switched off |
| A Drive file never shows | it is not in the booth folder (a "Photos of the booth" folder is a photo album); no run has read Drive since you uploaded it; its name has `(off)`, `_`, `~` or `PRIVATE`; its `(until …)` day passed or its `(from …)` day has not come; its language code does not match the language mode; its magazine or collection is off on this device; it is a type the booth cannot show; its caption says a refused word; a video too big to save (over 95 MB) | Settings → Slides (search its caption; **Files and rows the show couldn't use**); `data/site/booth.json`; the run summary's booth lines ([7.9](#79-check-that-a-file-arrived)). Rename, convert to .mp4 / .mp3, trim the video, or start a run by hand |
| A Drive photo shows online but not offline | it has no saved copy (the folder passed 400 MB), or the device saved the show before the photo was added | Make room in the folder, or raise `max_total_mb`; after the next site update, open (or reload) the About page with internet and start the show once |
| A Drive video never plays | it was not saved (too big, over the folder's limit, a failed download — the run summary's "Not saved" lines), or its format does not play in this browser (an iPhone's HEVC .mov) | Keep videos under 95 MB (720p, trimmed); save as .mp4 with H.264 video and AAC sound (on an iPhone: Settings → Camera → Formats → **Most Compatible**) |
| A CSV row never shows | a mistake in the row (the Code check is red; Settings → Slides → "Files and rows the show couldn't use"); `on` = `no`; its `id` starts with `#`; outside its `from` / `until` days; its channel, magazine or topic is off; it was switched off on this device (Slides → **Turned off**); a video, audio or image row while offline; an audio row while the sound is off | Fix the row ([8.10](#810-how-mistakes-are-reported)); check Settings → Slides → **On, but not now** for the reason |
| A new row is not on the booth yet | the site has not rebuilt yet, or the booth checks every 30 minutes, or it is offline; the About page keeps the show it loaded until it is reloaded | Wait a few minutes after the commit; leave the show, reload the About page and start it again; check the Website update run |
| Spanish slides missing | the language mode is English; the row has no Spanish words (the 14 English-only quotes, Grapevine's Daily Quote, the English podcast, Grapevine's English videos); a visitor chose English (undone after the idle time) | Settings → Show → **Language on the screen** → Español, Both or Alternate; add `_es` cells to the row |
| Each slide shows in only one language in Both | the slide is too long for two languages at a readable size: it shows one language and the other leads the next time | Shorter texts; or **Text size** Normal; or the Safe margin off |
| No sound | the sound is off (the default): Settings → Timing & sound → **Play sound**, or **M**; the browser waits for a first tap (**Tap for full screen & sound**); the file is marked `(muted)`; the volume or the device is muted; "Preview here" never plays sound | Turn the sound on and tap the screen once; check the device's volume; take `(muted)` out of the name |
| Sound files and the podcast never show | they play only while the sound is on (Settings → Slides: **Plays only with the sound on**); the podcast needs internet | Turn the sound on |
| The screen goes dark or locks | the browser could not keep it on (Kiosk: **This browser can't keep the screen on by itself …**, or **The screen may turn off by itself.**), battery saver, the device's own timeout | Plug in; set the device's screen timeout to Never ([2.3](#23-lock-the-device-to-the-show)); leave **Keep the screen on** on |
| The PIN is forgotten | — | Close the browser tab or window (the PIN only guards the show itself), open the About page, press **Settings** (no PIN is asked there) → **Kiosk** → **Remove the PIN**. Last resort: clear the site's data for `neta65.github.io` in the browser's settings — that also removes the offline copy, the settings and the votes |
| Settings open by themselves, or the PIN box shows | a visitor held the event's name for 3 seconds or pressed S | Nothing to do: they close by themselves (the PIN box after the idle time, Settings after 2 minutes) |
| "Nothing can show with these settings" | the switches leave no slide: language + magazine + channels + collections + topics, or Spanish only offline with few Spanish slides | Turn more on in Settings → Show; **Reset the settings** |
| The same slides keep coming back | a small show (filters, offline, one language): the no-repeat window is 40% of the show | Turn more channels or topics on |
| "The show couldn't be loaded. Check the connection and try again." | the first opening needs internet, or the saved copy was removed | Connect, press **Try again** |
| The preview card on the About page stands still | the device asks for reduced motion, the site's Data saver is on, or the card is off screen | Use **Preview here**, or Start the booth |
| The edges of the picture are cut on the TV | the TV's overscan | Settings → Screen → **Safe margin for TVs that cut the edges (5%)** (or the TV's "Just scan" / "Screen fit" picture size) |
| Text too small from across the room | — | Settings → Screen → **Text size** → Large; Daylight in a bright room |
| The clock shows the wrong time | the device's clock or time zone | Fix the device's date and time |
| The link applied somebody else's setup | a start link replaces the device's settings each time it is opened | Make a new link from this device's Settings → Share & reset, or Reset the settings |
| Settings don't stay after closing the browser | a private window, or site data blocked (**This browser isn't keeping the settings (a private window?) …**) | Use a normal window, and allow site data for the site |
| The Code check is red after a CSV edit | a mistake in the CSV; a new topic tag without its two names; a YouTube video the official channel's list does not know yet | Read the lines ([8.10](#810-how-mistakes-are-reported)); add the tag's words ([11.3](#113-recipe-a-new-csv-column)); wait for the next daily run for a brand-new video |

---

## 11. Going further: change the code

You never need this section to run the booth or to add content. It is for changing how the booth works.

### 11.1 How the pieces fit

```text
Drive: panel folder/booth/…  ── the sync (scripts/sync/drive.py reads every name with booth_names.py) ──▶ data/raw/drive.json
                                  └─ scripts/sync/build_data.py build_booth ──▶ data/site/booth.json  (the Drive files, in git)

Website update, job "Build & publish website":
  scripts/build/booth-media.mjs ── downloads the copies ──▶ .cache/booth-media/files + manifest.json  (Actions cache, never git)
  Eleventy:
    src/_data/booth.js  (loadBooth: content/booth/booth.csv checked, data/site/booth.json + the manifest,
                         config/site.yml booth:)  ──▶ the `booth` global
    src/pages/booth-json.11ty.js (boothShow: + the live items from data/site/*.json) ──▶ /about/booth.json
    eleventy.config.js copies .cache/booth-media/files ──▶ /about/booth/media/
    src/pages/about.njk + src/_includes/macros/booth.njk ──▶ the #booth section and the player's shell

In the browser (the About page):
  booth-core.js (window.GVB: settings, pool, next slide, language, time)  +  booth.js (the screen, Settings, visitors)
  sw-core.js (the service worker): keeps the offline copy (gvlv-booth-v1), answers the videos' byte ranges offline
```

### 11.2 Code map

| File | What it does | Look for |
|---|---|---|
| [content/booth/booth.csv](../content/booth/booth.csv) | the committee's rows | — |
| [content/booth/README.md](../content/booth/README.md) | the CSV's short guide | — |
| [config/site.yml](../config/site.yml) → `booth:` | the offline limits, every device's starting settings | `max_file_mb`, `max_total_mb`, `defaults` |
| [scripts/sync/booth_names.py](../scripts/sync/booth_names.py) | reads a booth file's name: kind, magazine, languages, title, options; a note's text; the problems | `parse_booth_name`, `media_type`, `_WORD_OPTIONS`, `_leading`, `message_text`, `PROBLEMS`, `collection_id` |
| [scripts/sync/drive.py](../scripts/sync/drive.py) | the `booth` folder words; each booth file's `extra.booth`; the notes' texts (shared download budget); the run summary's note | `CATEGORY_SYNONYMS["booth"]`, `build_item`, `fill_booth_texts`, `text_langs` |
| [scripts/sync/build_data.py](../scripts/sync/build_data.py) | `data/site/booth.json`: the files to show in order, the collections, the problems; keeps booth files out of every other page | `build_booth`, `booth_item`, `booth_stamp`, `Ctx.items`, `Ctx.booth_items` |
| [scripts/build/booth-media.mjs](../scripts/build/booth-media.mjs) | downloads the copies for offline (the build job's step), writes the manifest, the run summary's line and warnings | `main`, `fetchOnce`, `report` |
| [scripts/build/booth-media-core.mjs](../scripts/build/booth-media-core.mjs) | its rules: limits, the plan, file names, picture sizes, reasons | `DEFAULTS`, `CEILING_MB`, `plan`, `reasonText`, `parseBoothConfig` |
| [.github/workflows/update.yml](../.github/workflows/update.yml) | the four media steps (restore, download, key, save) and the run summary's booth list | "booth" in the build-deploy job; "Booth folder files the booth display can't show" |
| [eleventy/filters/booth.js](../eleventy/filters/booth.js) | everything the show is made of at build time: the CSV reader and checker, the Drive items, the live items, the refused words, the allowed sites, the whole `/about/booth.json` | `COLUMNS`, `TYPES`, `CSV_CHANNEL`, `NEEDS`, `MAX`, `ALLOWED_HOSTS`, `REFUSED` / `refusedIn`, `checkCsv`, `driveItems`, `boothDefaults`, `liveItems` (and `liveEvents` … `liveBulletin`), `BOOTH_WORDS`, `eventsPick`, `boothShow` |
| [src/_data/booth.js](../src/_data/booth.js) | the `booth` global and the build log's `[booth]` lines; `BOOTH_CSV`, `BOOTH_DRIVE`, `BOOTH_MANIFEST` point it at other files for a preview | `loadBooth` |
| [src/pages/booth-json.11ty.js](../src/pages/booth-json.11ty.js) | writes `/about/booth.json` | — |
| [src/assets/js/booth-core.js](../src/assets/js/booth-core.js) | the logic, no screen: settings and their limits, channels, types, the pool and why a slide may not show, the scheduler, languages, durations, presets, the start link's code, Quiz me, polls, the offline list. Its header describes all of it | `DEF`, `NUMS`, `CHANNELS`, `TYPES`, `EVERY`, `WINDOW_MIN`, `WINDOW_SHARE`, `reason`, `pool`, `shuffle`, `pick`, `duration`, `preset`, `encode` / `decode`, `saveList`, `WORDS` |
| [src/assets/js/booth.js](../src/assets/js/booth.js) | the screen: one renderer per slide type, the engine (time, reveal, media, watchdog), the visitors' bar, Quiz me, keys, the hold, the PIN, Settings' eight panels, the offline saving, the About page's quick controls, chips and previews, `?booth=start` | `RENDER.<type>`, `makeEngine`, `onKey`, `askPin`, `PANELS.<tab>`, `saveOffline`, `startLink`, `startPage` |
| [src/assets/css/areas/booth.css](../src/assets/css/areas/booth.css) | the look (class names start with `gvb-`) | `.gvb-screen` colour tokens, `[data-pub]`, `[data-gvb-theme="daylight"]` |
| [src/_includes/macros/booth.njk](../src/_includes/macros/booth.njk) | the About page's section, the player's dialog shell, its icons, and `#gvb-config` (the words the script may use: the `pageKeys` and `screenKeys` lists) | `section`, `player`, `pageKeys`, `screenKeys` |
| [src/pages/about.njk](../src/pages/about.njk) | places the section after "Our committee", its "On this page" entry, the two scripts | `boothUi.section`, `pageScripts` |
| [src/_i18n/booth.json](../src/_i18n/booth.json) | every word of the section, Settings and the screen, in English and Spanish | `booth.*`, `booth.screen.*`, `booth.ch.*`, `booth.tag.*` |
| [src/_includes/pwa/sw-core.js](../src/_includes/pwa/sw-core.js) | the offline copy: `gvlv-booth-v1`, the saves, the status, the removal, videos' byte ranges, the show file network first | `boothMedia`, `boothJson`, `boothSave`, `BOOTH_BUDGET`, the `BOOTH_*` messages |
| [src/pages/sw.11ty.js](../src/pages/sw.11ty.js) | the booth's two addresses for the worker | `CONFIG.booth` |
| [eleventy.config.js](../eleventy.config.js) | publishes the saved copies at `/about/booth/media/`; rebuilds when `content/booth/` changes | "booth-media", `addWatchTarget` |
| `tests/test_booth_*.py`, `tests/fixtures/booth_csv/` | the tests ([11.8](#118-tests-to-run)) | — |

### 11.3 Recipe: a new CSV column

Example: a `first` column (`yes` / `no`) so that a CSV row can open the show, as a Drive file's `(first)` does. The
player already opens the show with every item marked `first` — only the CSV cannot say it yet.

1. **The build's checker** — `eleventy/filters/booth.js`:
   - add `"first"` to `COLUMNS`;
   - in `checkCsv`, next to the `on` cell, read it the same way —
     `const firstRaw = oneLine(get("first"))`, `true` for `ON_YES`, `false` for blank or `ON_NO`, else
     `err(\`first "${firstRaw}": write yes or no\`, \`first "${firstRaw}": escribe yes o no\`)`;
   - in the `items.push({ … })` at the end, `first: firstValue` instead of `first: false`.
2. **Its Python twin** — `tests/test_booth_csv.py`: the same in `COLUMNS` and in `check_csv` (the same English line).
   The *Twin* test fails until both give the same lines and items.
3. **A fixture**: a row with `first` = `yes` and one with `first` = `maybe` in a file of `tests/fixtures/booth_csv/`,
   and the expected ids and lines in `EXPECTED` (`tests/test_booth_csv.py`).
4. **The guides**: the column's line in `content/booth/README.md` and in this page ([8.3](#83-every-column)).
5. **Run** `python -m unittest tests.test_booth_csv tests.test_booth_build -v`, and build the site.

A column that only the committee reads (`reviewer`, `checked_on`) needs none of this: unknown columns are ignored.

A **new topic tag** is not a new column but needs two words: add `"booth.tag.<tag>": { "en": "…", "es": "…" }` to
`src/_i18n/booth.json` (dashes as underscores: `self-support` → `booth.tag.self_support`) and `"tag.<tag>"` to the
`pageKeys` list in `src/_includes/macros/booth.njk`; `tests/test_booth_page.py` names any tag that lacks them.

### 11.4 Recipe: a new slide type

Example: a `tip` row — "Tip" as its eyebrow, a short text, switched with "Facts and history".

1. `eleventy/filters/booth.js`: add `"tip"` to `TYPES`, `tip: "facts"` to `CSV_CHANNEL`, `tip: ["text"]` to `NEEDS`
   (and to `SOURCE_TYPES` if it needs a `source_url`). The same in `tests/test_booth_csv.py`.
2. `src/assets/js/booth-core.js`: add `tip: { group: "learn", channel: "facts", interactive: false }` to `TYPES`, and
   `"tip"` to the `types` of the `facts` channel in `CHANNELS`. `duration` gives it the reading time by itself
   (a different time: one more line in `duration`).
3. `src/assets/js/booth.js`: a renderer — copy `RENDER.fact` as `RENDER.tip` and give its `eyebrow` the key
   `"booth.screen.tip"` and an icon of the `#gvb-icons` list (add the icon's name to that list in the macro if it is
   new). A slide type with no renderer is never shown.
4. Words: `booth.screen.tip` (on the screen) and `booth.type.tip` (its badge in Settings → Slides) in
   `src/_i18n/booth.json`, both languages; `"tip"` in `screenKeys` and `"type.tip"` in `pageKeys`
   (`src/_includes/macros/booth.njk`).
5. Look: a `.gvb-t-tip` rule in `src/assets/css/areas/booth.css` only if it should look different.
6. Tests: the type lists pinned in `tests/test_booth_core.py` (the set of render types) and the CSV fixtures; then
   `test_booth_core`, `test_booth_csv`, `test_booth_page`, `test_booth_build`. Document it in
   `content/booth/README.md` and here ([8.4](#84-every-type-with-a-real-row)).

### 11.5 Recipe: a new live channel

Example: **Record your story** — the current numbers of Grapevine's Audio Project and La Viña's "Graba tu historia",
read every day from their official pages into `data/site/audio_project.json` (`db.audio_project.gv` / `.lv`: `phone`,
`minutes_max`, `page_url` …), so the booth never shows an old number.

1. `eleventy/filters/booth.js`:
   - a function in the style of `liveMeetings`, returning `liveItem({ … })` items — for example a `message` per
     magazine:

     ```js
     function liveRecord(c) {
       const ap = isMap(c.db.audio_project) ? c.db.audio_project : {};
       const out = [];
       for (const pub of ["gv", "lv"]) {
         const x = isMap(ap[pub]) ? ap[pub] : null;
         if (!x || !x.phone) continue;
         const lang = pub === "lv" ? "es" : "en";
         out.push(liveItem({
           id: `live:record:${pub}`, type: "message", channel: "live-record", pub, langs: [lang],
           [lang]: { title: BOOTH_WORDS.record[lang], text: `${x.phone} · ${x.minutes_max} min` },
           qr: c.qrOk(str(x.page_url)), url: c.qrOk(str(x.page_url)), tags: ["recording"],
         }));
       }
       return out;
     }
     ```

   - its words in `BOOTH_WORDS` (`record: { en: "Record your story by phone", es: "Graba tu historia por teléfono" }`);
   - `["record", () => liveRecord(c)]` in the `parts` list of `liveItems`, and `record` in `PARTS` and `LIVE_WHERE`
     (the problem lines' words);
   - `"live-record"` in `CHANNELS` (its place is its place in Settings → Show).
   Every live item is checked for the refused words by itself (`screenLive`).
2. `src/assets/js/booth-core.js`: `{ id: "live-record", group: "live", types: ["message"] }` in `CHANNELS`
   (`needsNet: true` only for a channel that streams from the web). Its default switch is on by itself.
3. Words: `booth.ch.live_record` in `src/_i18n/booth.json` and `"ch.live_record"` in `pageKeys`.
4. Tests: `CHANNEL_IDS` in `tests/test_booth_core.py` and `CHANNELS` in `tests/test_booth_build.py`, plus a test in
   `test_booth_build.py`'s *Show* class with made-up `audio_project` data.

### 11.6 Recipe: change the scheduler's rules

Everything is in `src/assets/js/booth-core.js`, whose header explains each rule:

| To change | Edit | Example |
|---|---|---|
| how often the welcome and about slides come | `EVERY.welcome` (12), `EVERY.about` (30) | `welcome: 20` |
| how often a picture or clip is due | `EVERY.media` (4) | `media: 3` |
| how many play slides | `EVERY.play` (3: at most 1 in 3) | `play: 2` |
| how often a live list | `EVERY.list` (6) | `list: 10` |
| the no-repeat window | `WINDOW_MIN` (4), `WINDOW_SHARE` (0.4) | `WINDOW_SHARE = 0.5` |
| the default spacing of videos and sounds | `DEF.clipEvery` (8) and its range in `NUMS.clipEvery` (3–30); the Quiz party preset's 10 in `preset` | `clipEvery: 10` |
| a rule's importance, or a new rule | the `rules` list in `shuffle()` — earlier is more important; a rule that no slide can keep gives way alone | |
| the default times | `NUMS` and `DEF` (reveal 12, photo 8, video 180 / 90 s), the numbers in `duration()` and `readTime()` | |

Then update the numbers the tests pin (`tests/test_booth_core.py`: `DEFAULTS`, the *Scheduler* class — welcome every
12, about every 30 …) and run `python -m unittest tests.test_booth_core -v`. Every device picks the new rules up the
next time it opens (or reloads) the About page with internet after the deploy; a device's own settings (clipEvery,
reveal …) stay as it set them.

### 11.7 Recipe: change the colours or the words

- **Colours** — `src/assets/css/areas/booth.css`: the dark stage's tokens on `.gvb-screen` (`--bg`, `--ink`,
  `--muted` …), each magazine's accent on `.gvb-screen[data-pub="gv"]`, `[data-pub="lv"]` and `[data-pub="both"]`
  (`--acc` the text accent, `--acc-bg` the filled colour, `--glow` and `--glow-2` the backdrop), and the Daylight
  look on `.gvb-screen[data-gvb-theme="daylight"]`. Keep text at a contrast of 4.5:1 or more against its background
  (the Daylight block's comment says so). Example: a deeper Grapevine blue → `--acc-bg: #084f8c;` in the gv block.
  The site's general colour tokens are in [Pages and code §12.2](pages-and-code.md#122-change-a-colour).
- **Words** — `src/_i18n/booth.json`, both languages ([Translations §3.2](translations.md#32-buttons-menus-and-headings-src_i18njson)).
  A new key the script uses must also be listed in `pageKeys` (Settings and page words) or `screenKeys` (words on the
  slides) in `src/_includes/macros/booth.njk`; `tests/test_booth_page.py` checks that every key exists in both
  languages and reaches the script. The welcome and about slides' words (`booth.screen.welcome`,
  `welcome_line`, `about_line`, `about_note`) are also written in `WORDS` at the top of `booth-core.js` (for the
  tests): change both. Never "PDF" in a visitor's words; La Viña first in a Spanish text that names both magazines.

### 11.8 Tests to run

On a PC set up as in [Automation and troubleshooting §11](automation-and-troubleshooting.md#11-run-the-sync-the-build-and-the-tests-on-a-pc):

```powershell
python tests/test_booth_csv.py content/booth/booth.csv        # the CSV alone: "246 row(s) shown, 0 problem(s)"
python -m unittest tests.test_booth_csv tests.test_booth_build tests.test_booth_core tests.test_booth_page tests.test_booth_media tests.test_booth_names tests.test_booth_sync tests.test_pwa_worker -v
python -m unittest discover -s tests                          # everything, as the Code check runs it
```

The booth's 254 tests took about 36 seconds on the owner's PC on October 3, 2026 (Node.js and `npm ci` are needed for
most of them; without them they skip themselves).

| Test file | Checks |
|---|---|
| `tests/test_booth_csv.py` | the real CSV has no problem; its YouTube and podcast rows are official; the reader; every fixture line by line; the build's JavaScript checker gives the same lines (the *Twin*) |
| `tests/test_booth_names.py` | every naming example of [7.5](#75-examples), file types, problems, a note's text |
| `tests/test_booth_sync.py` | the booth folder through the sync: category words, `data/site/booth.json`, booth files kept out of every other page, the run summary's list |
| `tests/test_booth_media.py` | the offline copies: limits, plan, names, picture sizes, the downloader end to end against a local server, the workflow's steps |
| `tests/test_booth_build.py` | `/about/booth.json` from fixtures: every key, the Drive items with and without copies, every live channel, the refused words, a real build of the file |
| `tests/test_booth_core.py` | the logic: settings, the start link's code, the pool and its reasons, languages, the scheduler over thousands of slides, timing, Quiz me, polls, the offline list |
| `tests/test_booth_page.py` | the About page: every word in both languages and reaching the script, the wiring, a built page |
| `tests/test_pwa_worker.py` | the service worker, the booth's copy and byte ranges included |

To look at it, build and serve the site on the PC (`npm start`, then `http://localhost:8080/about/#booth`; editing
`content/booth/booth.csv` rebuilds the show). `$env:BOOTH_CSV = "$HOME\Documents\draft.csv"` builds the show from another
CSV (remove it afterwards: `Remove-Item Env:BOOTH_CSV`). For phone-size screenshots and JavaScript errors, Playwright
with Edge ([Automation and troubleshooting §11.5](automation-and-troubleshooting.md#115-look-at-pages-in-a-real-browser-playwright-with-edge)).

---

## 12. See also

- [content/booth/README.md](../content/booth/README.md) — the CSV's short guide, beside the file.
- [The Drive panel folder](drive-panel-folder.md) — sharing, panel folders, never-published names, replacing files;
  the booth folder in [§3.6](drive-panel-folder.md#36-the-booth-folder-new).
- [File types](file-types.md) — every file type in every folder; the booth folder in
  [§4.18](file-types.md#418-the-booth-folder).
- [Settings](settings.md) — `config/site.yml`, the `booth:` section in
  [§3.14](settings.md#314-booth--the-booth-display).
- [Automatic sources](automatic-sources.md) — where the live channels' data comes from (videos, podcasts, daily
  quotes, themes, prices, Books of the Month, weekly open meetings).
- [Flyers and events](flyers-and-events.md) and [Bulletin](bulletin.md) — the events and posts the live channels
  show.
- [Automation and troubleshooting](automation-and-troubleshooting.md) — the runs, their summaries, the booth's media
  steps ([§4.2](automation-and-troubleshooting.md#42-website-update-and-its-three-modes)), running things on a PC.
- [Pages and code](pages-and-code.md) — the site's pages, styles and the service worker.
- [Translations](translations.md) — the words in `src/_i18n/`.
- [Presentations](presentations.md) — the four web slide decks, another kind of show.
