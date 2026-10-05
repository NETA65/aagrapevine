/* The booth display's logic (About page → "Booth display": the randomized show that plays by itself at the committee's
   Grapevine / La Viña table at assemblies and conventions). The screen itself — the full-screen dialog, the slides,
   the visitor bar, Settings, the service worker messages — is src/assets/js/booth.js; the show's content is
   /about/booth.json (src/_data/booth.js + src/pages/booth-json.11ty.js: the committee's CSV content/booth/booth.csv,
   the Drive booth folder's photos and videos, and live items made from the site's data).
   Pure functions, no DOM, no fetch, no storage: this file only knows about the show's items, the player's settings
   and the order the slides come in. Tested in Node by tests/test_booth_core.py (the file runs in a vm context, as
   presentations-core.js does). A plain script (no imports; no optional chaining or ?? — old Safari on a booth's
   tablet must run it): it defines window.GVB (globalThis.GVB in Node).

   THE SHOW — /about/booth.json: { app: "gv-booth", schema: 1, version, built, as_of, site: { url, url_es, base, host,
   committee_en, committee_es }, defaults, collections, channels, events_pick, items, qr, problems }. An ITEM:
     { id ("quiz-first-issue" | "drive:<fileId>" | "live:<kind>:<key>" | "auto:<name>"), source (csv|drive|live|auto),
       type (the render type below), channel (the settings switch below), pub (gv|lv|both), langs (["en","es"]; [] =
       a picture or sound without words: shown in every language), en / es ({ title, text, choices, answer, explain,
       credit, rows } or null), correct (quiz: the 0-based index of the right choice; truefalse: true/false), seconds,
       reveal, weight, from, until (YYYY-MM-DD, Central time, inclusive), tags, collection, first, order,
       media (null | { kind: youtube|video|audio|image, src, id, short, local, poster, start, end, muted, fit, w, h,
       bytes }), online (true = needs a connection), qr (the address its QR code opens), qr_es (the code's address
       on its Spanish slides — a page of the site under /es/ — or null: the same code in both languages; qrOf()
       picks one), url, until_ts (epoch ms: the item is over after it) }.
   A live list's `rows` (per language): [{ title, when, place, note, ends_ts, pub, thumb }] — a row is dropped once
   its ends_ts has passed, and the list with it when no row is left.

   RENDER TYPES (GVB.TYPES: { group, channel?, interactive }) — "play": quiz, truefalse, fill, scramble, poll ·
   "learn": fact, history, quote, prompt · "info": message, qr, and the player's own welcome and about slides ·
   "media": video, audio, image, photo, poster · "live": events, countdown, themes, prices, book, meetings.
   `channel` is given when the type belongs to one channel only (a quote is a CSV quote or the Daily Quote; a video
   is a CSV video, a Drive video or an official channel's video — item.channel always says which).
   The auto items are made here (autoItems), never in the JSON: auto:welcome (type "welcome": when an event name is
   set — "Welcome! · {event}" / "¡Bienvenidos! · {event}") and auto:about (type "about": who shares the display and
   that it is not an official AA Grapevine, Inc. or A.A.W.S. display, with the site's QR).

   CHANNELS (GVB.CHANNELS: [{ id, group, types, needsNet? }]) — the include / exclude switches of Settings → Show:
   quiz (quiz + truefalse), puzzles (fill + scramble), facts (fact + history), quotes (CSV quotes), polls, prompts,
   messages (CSV), qr, web-video / web-audio / web-image (CSV links: need internet), photos, posters, videos and
   sounds (the Drive booth folder), notes (Drive text files), the live-* channels (events, quote, video, podcast,
   themes, prices, book, meetings, bulletin), welcome and about. All on by default. A sound (audio) never plays while
   the booth's sound is off, whatever its channel says.

   THE SETTINGS — localStorage["gv-booth-v1"] (booth.js reads and writes it; never sent anywhere). GVB.DEFAULTS:
     event: { en: "", es: "", sub: "", show: true }       the event name (es blank → the English one); sub = one line
     lang: "both" (en | es | both | alternate)   first: "en" (which language leads in "both"; the /es/ page: "es")
     pubs: { gv: true, lv: true }   channels: { <channel>: true … }   collections: { <id>: true … } (unknown = on)
     items: { <id>: false } (only the excluded ones)   tags: { <tag>: false } (only the hidden ones)
     boost: { <channel>: 2 } (shown that many times as often; "Quiz party")   order: "shuffle" | "inorder"
     pace: "normal" (calm | normal | lively)   reveal: 12   photoSeconds: 8   mediaMax: 180   webMediaMax: 90
     clipEvery: 8 (3–30: a video or a sound at most once in that many slides — THE ORDER, rule 2)
     sound: false   volume: 0.8   captions: true   idleSeconds: 40   visitor: true   quizLength: 5
     theme: "dark" (dark | daylight)   textSize: "normal" (normal | large)   motion: "full" (full | calm)
     clock: true   qrCorner: true   progress: true   overscan: false
     pin: "" (4 digits; it only stops visitors — it is kept as typed, not secret)   wakeLock: true
     autoFullscreen: true   refreshMinutes: 30   autoSave: true
   The site's starting values (config/site.yml booth.defaults → booth.json "defaults") go on top of these:
   withDefaults(json.defaults) is the BASE every device starts from; what a device changes is kept against it.
   normSettings(raw, base) makes any stored value safe to use: unknown keys dropped, wrong types replaced by the
   base's value, every number clamped — it never throws, whatever is in storage. diff(settings, base) is the part
   that differs (what "Share this setup" sends); encode / decode turn that part into the address's `&bs=…` and
   back: base64url JSON, at most 2048 characters, strict (anything wrong → null, nothing of it applied).
   Presets (preset(name)): assembly (both languages) · spanish (Spanish, Spanish first) · english · quiet (no sound,
   calm pace, calm motion) · quizparty (quizzes and puzzles twice as often, lively pace, a video or a sound at most
   once in 10 slides).

   THE POOL — pool(json, settings, ctx): the items that may show now. ctx = GVB.ctx({ now, online, page }) →
   { now, today (YYYY-MM-DD in Central time), online, page }. why(item, settings, ctx) says why one may not (null
   when it may), for Settings → Items — checked in this order:
     off (switched off by id) · channel (its channel is off) · pub (Grapevine / La Viña filter) · collection (its
     Drive collection is off) · tag (one of its tags is hidden) · date (outside from / until) · over (until_ts has
     passed, or every row of its list is over) · lang (no text in the language shown: "en" needs English or a
     picture without words, "es" Spanish, both / alternate either) · offline (needs internet, and there is none) ·
     muted (a sound while the sound is off) · media (its picture / video / sound is not available).
   Two optional ctx fields come from the screen: youtube: false (YouTube did not start lately: its videos wait) and
   failed: { <id>: true } (items whose media failed) — both give "media".

   THE ORDER — next(state, pool, settings, ctx) → { item, state }: pure (the state passed in is never changed; the
   new one comes back). newState(seed) starts a show: { seed, n, recent: [ids, newest last], firstQueue, lastType,
   sinceWelcome, sinceAbout, sinceMedia, sinceClip, sincePlay, sinceList, langTurn } — each "since" counts the
   slides shown since the last one of its kind (or since the start). Every pick draws from a mulberry32 generator
   seeded with (seed, n): the same seed and pool give the same show, which is what the tests check.
     · The items marked `first` open the show (auto:welcome before them, when an event name is set), in order,
       whatever the rules below say (two videos marked first play one after the other); a clip among them is still
       the last clip for rule 2. Set state.firstQueue = null (or start a newState) after the settings change to
       open with them again.
     · auto:welcome comes back every 12 slides, auto:about every 30 (when they are in the pool) — a slide later
       when a media slide is due then and one can be shown (a media item outside the no-repeat window; a clip only
       when rule 2 lets it), so the media rule below always holds; a media slide that cannot come yet never holds
       them back.
     · "In order": the CSV / Drive order (the order number first, then the place in the show), looping — the
       committee's own order: none of the rules below changes it.
     · "Shuffle" (the default): a weighted draw (weight × the channel's boost) among the items that keep these
       rules, the most important first — a rule that no item can keep along with the more important ones gives
       way, and the less important ones still apply:
         1. not repeated until max(4, 40% of the pool) others have shown (the no-repeat window)
         2. a CLIP — a video or a sound: YouTube, a web video or sound, a Drive video or sound file, a podcast
            episode (isClip) — at most once in settings.clipEvery slides (default 8). A clip plays for a minute or
            two where a slide shows for seconds: online, where the official channels' videos filled every media
            slide, they were about 30 % of the slides and most of the screen time
         3. never the same render type twice in a row (photo after photo up to 2)
         4. at most 1 of every 3 slides from the "play" group (quiz, truefalse, fill, scramble, poll)
         5. a "media" item (a picture — photo, poster, image — or a clip) at least every 4 slides, when one can be
            shown: one outside the window, and a clip only when rule 2 lets it — a media slide that is due never
            forces a clip; with nothing but clips it waits for the next one's turn. The pictures keep this pace.
            With too few media items for it (room × 4 ≤ window + 1, the room being what the window holds of them:
            each picture once, and the clips once each but at most (window + 1) / clipEvery of them — mediaRoom),
            one every (window + 1) / room slides instead, rounded down (mediaEvery)
         6. a live list (events, meetings, themes) at most once in 6 slides
         7. with that few media items, none between their turns (mediaScarce): they spread evenly over the window
            instead of all coming at once and then none for half an hour (an offline booth, a small Drive folder)
       With few media items each one already shows as often as rule 1 allows (once per window), so a Drive file's
       (x2)…(x5) / (rare) counts when there are more of them (online, or a bigger folder).
     · An empty pool → the about slide (taking turns with the welcome slide when an event name is set): never a
       blank screen. That fallback about item has qr null (the pool cannot say the site's address): the screen
       shows the site's own QR then.

   LANGUAGES — lang(item, settings, state) → "en" | "es" | "both" for one slide: an item with one language always
   shows in that one; mode both → "both" (the screen puts settings.first first); alternate → en, es, en … starting
   with settings.first (next() moves state.langTurn: a one-language slide counts as its language's turn).
   text(item, lang) → { title, text, choices, answer, explain, credit, rows } with every field there ("" / []);
   a language the item has no words for borrows the other one's (a picture's caption); "both" → { en, es }.
   fill(text, vars) puts in {event} {committee} {site} {site_es} (an empty value takes its space with it).
   qrOf(item, lang, settings) → the address of the slide's QR code: qr_es on a Spanish slide (when the item has
   one), else qr; in "both" the first language's (settings.first).

   TIME — duration(item, settings, lang) → seconds on screen (× pace: calm 1.35, normal 1, lively 0.75; 5–180):
   text slides 6 s + 1 s per 12 characters (both languages × 1.7), 8–30 s; quiz / truefalse / fill / scramble:
   revealAt + 7 s + the answer's reading time; poll, prompt, qr 14 s; photo settings.photoSeconds; poster 12 s;
   live lists 15 s; countdown 10 s; an item's own `seconds` wins (× pace). Video and sound: the part between start
   and end, at most mediaMax (a file of the booth) or webMediaMax (from the web) — the screen moves on when it ends.
   revealAt(item, settings, lang) → seconds until the answer shows (quiz, truefalse, fill, scramble), else null.

   THE REST — scramble(word, seed): the letters shuffled (spaces stay), never the word itself (3+ letters) ·
   quizRound(pool, lang, n, rng): "Quiz me" — up to n quiz / truefalse / fill items in that language, none twice ·
   tally(polls, id, choice) / pollResults(polls, item): this device's poll votes (localStorage
   "gv-booth-polls-v1": { <id>: [counts] }) → a new object / [{ count, pct }] (the pcts add up to 100) ·
   saveList(json, settings, base): what to keep for offline — the two About pages first (BOOTH_SAVE `pages`), then
   booth.json and every same-origin file the items use (BOOTH_SAVE `files`): local media, posters, list thumbs.
   It ignores every switch of the settings (an item, a channel, a magazine, a collection, a tag off; the language,
   the sound) and of the moment (the date, an item that is over, offline): a booth flips them at the table, maybe
   offline, and one switched back on must find its files still there. The build caps the booth folder (booth.max_total_mb), every
   switch is on by default (the first save holds every file anyway), and the save's prune then drops only what
   booth.json no longer names — the service worker's rule · fmt(s, vars): "{n} of {total}". */
(function (root) {
  "use strict";

  var VERSION = "1.0.0";
  var SCHEMA = 1;
  var APP = "gv-booth";
  var STORAGE_KEY = "gv-booth-v1";
  var POLLS_KEY = "gv-booth-polls-v1";
  var STATE_KEY = "gv-booth-state-v1";
  var TZ = "America/Chicago";
  var LANGS = ["en", "es"];
  var MODES = ["en", "es", "both", "alternate"];
  var PACE = { calm: 1.35, normal: 1, lively: 0.75 };
  var REASONS = ["off", "channel", "pub", "collection", "tag", "date", "over", "lang", "offline", "muted", "media"];
  var PRESETS = ["assembly", "spanish", "english", "quiet", "quizparty"];
  // the live lists: at most one of them in 6 slides
  var LISTS = ["events", "meetings", "themes"];
  // the render types that need a picture, a video or a sound
  var MEDIA_TYPES = ["video", "audio", "image", "photo", "poster"];
  var MEDIA_KINDS = ["youtube", "video", "audio", "image"];
  // the "clips" among them — a video or a sound, from YouTube, the web, the Drive folder or the podcast: at most one
  // in settings.clipEvery slides (the others are the pictures: photo, poster, image)
  var CLIP_TYPES = ["video", "audio"];
  // the types that have an answer to reveal ("Quiz me" takes the first three)
  var ANSWER_TYPES = ["quiz", "truefalse", "fill", "scramble"];
  var QUIZ_TYPES = ["quiz", "truefalse", "fill"];
  // the scheduler's numbers (SPEC §3.3)
  var EVERY = { welcome: 12, about: 30, media: 4, play: 3, list: 6 };
  var WINDOW_MIN = 4, WINDOW_SHARE = 0.4;
  var RECENT_MAX = 400;
  var SHARE_MAX = 2048;

  /* The include / exclude switches (SPEC §3.2), in Settings → Show's order. needsNet: every item of the channel
     comes from the web (a YouTube video, a web picture, the podcast). */
  var CHANNELS = [
    { id: "quiz", group: "play", types: ["quiz", "truefalse"] },
    { id: "puzzles", group: "play", types: ["fill", "scramble"] },
    { id: "facts", group: "learn", types: ["fact", "history"] },
    { id: "quotes", group: "learn", types: ["quote"] },
    { id: "polls", group: "play", types: ["poll"] },
    { id: "prompts", group: "learn", types: ["prompt"] },
    { id: "messages", group: "info", types: ["message"] },
    { id: "qr", group: "info", types: ["qr"] },
    { id: "web-video", group: "media", types: ["video"], needsNet: true },
    { id: "web-audio", group: "media", types: ["audio"], needsNet: true },
    { id: "web-image", group: "media", types: ["image"], needsNet: true },
    { id: "photos", group: "media", types: ["photo"] },
    { id: "posters", group: "media", types: ["poster"] },
    { id: "videos", group: "media", types: ["video"] },
    { id: "sounds", group: "media", types: ["audio"] },
    { id: "notes", group: "info", types: ["message"] },
    { id: "live-events", group: "live", types: ["events", "countdown"] },
    { id: "live-quote", group: "live", types: ["quote"] },
    { id: "live-video", group: "live", types: ["video"], needsNet: true },
    { id: "live-podcast", group: "live", types: ["audio"], needsNet: true },
    { id: "live-themes", group: "live", types: ["themes"] },
    { id: "live-prices", group: "live", types: ["prices"] },
    { id: "live-book", group: "live", types: ["book"] },
    { id: "live-meetings", group: "live", types: ["meetings"] },
    { id: "live-bulletin", group: "live", types: ["message"] },
    { id: "welcome", group: "info", types: ["welcome"] },
    { id: "about", group: "info", types: ["about"] },
  ];
  var CHANNEL_IDS = CHANNELS.map(function (c) { return c.id; });

  /* The render types (SPEC §3.1) and the player's two own slides. interactive: a visitor can answer or vote. */
  var TYPES = {
    quiz: { group: "play", channel: "quiz", interactive: true },
    truefalse: { group: "play", channel: "quiz", interactive: true },
    fill: { group: "play", channel: "puzzles", interactive: true },
    scramble: { group: "play", channel: "puzzles", interactive: true },
    poll: { group: "play", channel: "polls", interactive: true },
    fact: { group: "learn", channel: "facts", interactive: false },
    history: { group: "learn", channel: "facts", interactive: false },
    quote: { group: "learn", interactive: false },
    prompt: { group: "learn", channel: "prompts", interactive: false },
    message: { group: "info", interactive: false },
    qr: { group: "info", channel: "qr", interactive: false },
    welcome: { group: "info", channel: "welcome", interactive: false },
    about: { group: "info", channel: "about", interactive: false },
    video: { group: "media", interactive: false },
    audio: { group: "media", interactive: false },
    image: { group: "media", channel: "web-image", interactive: false },
    photo: { group: "media", channel: "photos", interactive: false },
    poster: { group: "media", channel: "posters", interactive: false },
    events: { group: "live", channel: "live-events", interactive: false },
    countdown: { group: "live", channel: "live-events", interactive: false },
    themes: { group: "live", channel: "live-themes", interactive: false },
    prices: { group: "live", channel: "live-prices", interactive: false },
    book: { group: "live", channel: "live-book", interactive: false },
    meetings: { group: "live", channel: "live-meetings", interactive: false },
  };

  /* The words of the player's own slides, in both languages (a slide shows the content's languages, not the
     page's). The committee's name and the site's address come from booth.json's `site` when it has them. On the
     About page booth.js first puts the site's own words in GVB.WORDS (this very object: src/_i18n/booth.json
     booth.screen.welcome, welcome_line, about_line, about_note), so that file is the one place to change them; these
     are the same words, for Node and the tests. */
  var WORDS = {
    en: {
      // (no sentence joins the event's name: "¡Bienvenidos a Asamblea de Primavera…!" would lack its "la")
      welcome: "Welcome! · {event}",
      welcome_text: "Grapevine and La Viña — ask us anything",
      shared_by: "Shared by the {committee}",
      not_official: "Not an official AA Grapevine, Inc. or A.A.W.S. display",
      committee: "NETA 65 Grapevine & La Viña Committee",
    },
    es: {
      welcome: "¡Bienvenidos! · {event}",
      // La Viña first on a Spanish text that names both (SPEC §4)
      welcome_text: "La Viña y Grapevine — pregúntanos lo que quieras",
      shared_by: "Compartido por el {committee}",
      not_official: "Esta no es una pantalla oficial de AA Grapevine, Inc. ni de A.A.W.S.",
      committee: "Comité de Grapevine y La Viña de NETA 65",
    },
  };

  /* ------------------------------------------------------------------ small helpers */
  function isMap(v) { return !!v && typeof v === "object" && !Array.isArray(v); }
  function isStr(v) { return typeof v === "string"; }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function has(o, k) { return isMap(o) && Object.prototype.hasOwnProperty.call(o, k); }
  function copy(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
  function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
  function clamp(n, lo, hi) { return n < lo ? lo : n > hi ? hi : n; }
  function round(n, step) { return Math.round(Math.round(n / step) * step * 100) / 100; }
  function tenth(n) { return Math.round(n * 10) / 10; }
  function str(v) { return isStr(v) ? v : isNum(v) ? String(v) : ""; }
  function list(v) { return Array.isArray(v) ? v : []; }
  function fmt(s, vars) {
    return String(s).replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m; });
  }
  /** A number from a number or a numeric string ("12", " 0.5 "); NaN for anything else. */
  function num(v) {
    if (isNum(v)) return v;
    if (isStr(v) && /^\s*-?\d+(?:\.\d+)?\s*$/.test(v)) return parseFloat(v);
    return NaN;
  }
  /** A switch's value: true / false (also "true" / "false", 1 / 0); `dflt` for anything else. */
  function bool(v, dflt) {
    if (v === true || v === 1 || v === "true" || v === "1") return true;
    if (v === false || v === 0 || v === "false" || v === "0") return false;
    return dflt;
  }
  /** Text typed in Settings, kept as typed (no trimming while someone types) — control characters out, cut at max. */
  function line(v, max) {
    return String(v).replace(/[\u0000-\u001f\u007f]+/g, " ").slice(0, max);
  }
  /** A seed from a number or a word (FNV-1a). */
  function seedOf(v) {
    if (isNum(v)) return Math.floor(Math.abs(v)) >>> 0;
    if (isStr(v) && v) {
      var h = 2166136261;
      for (var i = 0; i < v.length; i++) h = Math.imul(h ^ v.charCodeAt(i), 16777619);
      return h >>> 0;
    }
    return 0;
  }
  function typeOf(item) { return isMap(item) && isStr(item.type) && has(TYPES, item.type) ? TYPES[item.type] : null; }
  function groupOf(item) { var t = typeOf(item); return t ? t.group : ""; }
  function isMedia(item) { return groupOf(item) === "media"; }
  function isClip(item) { return isMap(item) && CLIP_TYPES.indexOf(item.type) >= 0; }
  function isPlay(item) { return groupOf(item) === "play"; }
  function isList(item) { return isMap(item) && LISTS.indexOf(item.type) >= 0; }
  function isAuto(item) { return isMap(item) && (item.id === "auto:welcome" || item.id === "auto:about"); }
  function langsOf(item) {
    return list(item && item.langs).filter(function (l) { return LANGS.indexOf(l) >= 0; });
  }

  /* ------------------------------------------------------------------ the settings */
  var ITEM_ID = /^[A-Za-z0-9][A-Za-z0-9:._-]{0,159}$/;
  var COLLECTION_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;
  var TAG = /^[^\s<>"'`{}|;,_][^\s<>"'`{}|;,]{0,39}$/;
  var PIN = /^(?:\d{4})?$/;
  var CAP = { items: 3000, collections: 200, tags: 200 };
  var NAME_MAX = 80, SUB_MAX = 120;
  // every number of the settings: [lowest, highest, step]
  var NUMS = {
    reveal: [4, 60, 1], photoSeconds: [3, 120, 1], mediaMax: [10, 900, 1], webMediaMax: [10, 900, 1],
    clipEvery: [3, 30, 1], volume: [0, 1, 0.01], idleSeconds: [10, 600, 1], quizLength: [3, 10, 1],
    refreshMinutes: [5, 1440, 1],
  };
  var ENUMS = {
    lang: MODES, first: LANGS, order: ["shuffle", "inorder"], pace: ["calm", "normal", "lively"],
    theme: ["dark", "daylight"], textSize: ["normal", "large"], motion: ["full", "calm"],
  };
  var BOOLS = ["sound", "captions", "visitor", "clock", "qrCorner", "progress", "overscan", "wakeLock", "autoFullscreen", "autoSave"];
  // a channel's boost: [lowest, highest, step]
  var BOOST = [0.25, 5, 0.05];

  var DEF = {
    event: { en: "", es: "", sub: "", show: true },
    lang: "both", first: "en",
    pubs: { gv: true, lv: true },
    channels: (function () { var c = {}; CHANNEL_IDS.forEach(function (id) { c[id] = true; }); return c; })(),
    collections: {}, items: {}, tags: {}, boost: {},
    order: "shuffle",
    pace: "normal", reveal: 12, photoSeconds: 8, mediaMax: 180, webMediaMax: 90, clipEvery: 8,
    sound: false, volume: 0.8, captions: true,
    idleSeconds: 40, visitor: true, quizLength: 5,
    theme: "dark", textSize: "normal", motion: "full",
    clock: true, qrCorner: true, progress: true, overscan: false,
    pin: "", wakeLock: true, autoFullscreen: true, refreshMinutes: 30, autoSave: true,
  };
  var KEYS = Object.keys(DEF);

  /** A stored value made safe against `b` (a clean base): each key of its kind, else the base's. */
  function clean(raw, b) {
    var r = isMap(raw) ? raw : {};
    var s = {};
    var ev = isMap(r.event) ? r.event : {};
    s.event = {
      en: isStr(ev.en) ? line(ev.en, NAME_MAX) : b.event.en,
      es: isStr(ev.es) ? line(ev.es, NAME_MAX) : b.event.es,
      sub: isStr(ev.sub) ? line(ev.sub, SUB_MAX) : b.event.sub,
      show: bool(ev.show, b.event.show),
    };
    Object.keys(ENUMS).forEach(function (k) { s[k] = ENUMS[k].indexOf(r[k]) >= 0 ? r[k] : b[k]; });
    Object.keys(NUMS).forEach(function (k) {
      var n = num(r[k]), lim = NUMS[k];
      s[k] = isFinite(n) ? clamp(round(n, lim[2]), lim[0], lim[1]) : b[k];
    });
    BOOLS.forEach(function (k) { s[k] = bool(r[k], b[k]); });
    s.pin = isStr(r.pin) && PIN.test(r.pin) ? r.pin : b.pin;
    var p = isMap(r.pubs) ? r.pubs : {};
    s.pubs = { gv: bool(p.gv, b.pubs.gv), lv: bool(p.lv, b.pubs.lv) };
    var c = isMap(r.channels) ? r.channels : {};
    s.channels = {};
    CHANNEL_IDS.forEach(function (id) { s.channels[id] = bool(c[id], bool(b.channels[id], true)); });
    // collections: merged into the base's, key by key (a collection the settings never named is on)
    s.collections = copy(b.collections);
    if (isMap(r.collections)) {
      Object.keys(r.collections).forEach(function (id) {
        var v = bool(r.collections[id], undefined);
        if (COLLECTION_ID.test(id) && v !== undefined && (has(s.collections, id) || Object.keys(s.collections).length < CAP.collections)) s.collections[id] = v;
      });
    }
    // boost: merged too, one number per channel
    s.boost = copy(b.boost);
    if (isMap(r.boost)) {
      Object.keys(r.boost).forEach(function (id) {
        var n = num(r.boost[id]);
        if (CHANNEL_IDS.indexOf(id) >= 0 && isFinite(n)) s.boost[id] = clamp(round(n, BOOST[2]), BOOST[0], BOOST[1]);
      });
    }
    // items / tags: only what is turned off; a stored map replaces the base's as a whole
    s.items = offMap(r.items, b.items, ITEM_ID, CAP.items, false);
    s.tags = offMap(r.tags, b.tags, TAG, CAP.tags, true);
    var out = {};
    KEYS.forEach(function (k) { out[k] = s[k]; });         // DEFAULTS' order, nothing else
    return out;
  }
  function offMap(raw, dflt, re, cap, lower) {
    if (!isMap(raw)) return copy(dflt);
    var out = {}, n = 0;
    Object.keys(raw).forEach(function (k) {
      var key = lower ? k.toLowerCase() : k;
      if (n < cap && re.test(key) && bool(raw[k], undefined) === false && !has(out, key)) { out[key] = false; n++; }
    });
    return out;
  }
  /**
   * Any value (a stored one, a decoded link, a form's) → complete, safe settings: the keys of DEFAULTS only, each
   * of its kind (else the base's), numbers clamped to their range. `base`: what a missing key takes — the site's
   * starting settings (withDefaults(json.defaults)); DEFAULTS without it. Never throws.
   */
  function normSettings(raw, base) {
    var b = DEF;
    if (isMap(base) && base !== DEF) {
      try { b = clean(base, DEF); } catch (e) { b = DEF; }   // a broken base: DEFAULTS stand in for it
    }
    try {
      return clean(raw, b);
    } catch (e) {
      return copy(b);
    }
  }
  /** The site's starting settings: DEFAULTS with booth.json's `defaults` on top — written as settings keys
   *  ({ event: { en, es }, lang, sound }) or with config/site.yml's own names (event_name, event_name_es, language,
   *  sound). page "es" (the /es/ About page): Spanish leads in "both" unless the site says otherwise. */
  function withDefaults(jsonDefaults, page) {
    var raw = {};
    try {
      var j = isMap(jsonDefaults) ? jsonDefaults : {};
      Object.keys(j).forEach(function (k) { if (has(DEF, k)) raw[k] = j[k]; });
      var ev = isMap(raw.event) ? copy(raw.event) : {};
      if (isStr(j.event_name) && !isStr(ev.en)) ev.en = j.event_name;
      if (isStr(j.event_name_es) && !isStr(ev.es)) ev.es = j.event_name_es;
      raw.event = ev;
      if (!has(raw, "lang") && isStr(j.language)) raw.lang = j.language.trim().toLowerCase();
    } catch (e) { raw = {}; }
    if (page === "es" && !has(raw, "first")) raw.first = "es";
    return normSettings(raw, DEF);
  }
  // the maps whose keys are merged one by one, and what a key missing from them stands for
  var MERGED = { event: null, pubs: true, channels: true, collections: true, boost: 1 };
  /** Only what differs from `base` (DEFAULTS without it): a merged map gives only its differing keys (a key
   *  missing from either side counts as its default: on, boost 1); items and tags are given whole. */
  function diff(settings, base) {
    var b = normSettings(base, DEF), s = normSettings(settings, b);
    var out = {};
    KEYS.forEach(function (k) {
      if (has(MERGED, k)) {
        var d = {}, dflt = MERGED[k];
        var keys = Object.keys(b[k]);
        Object.keys(s[k]).forEach(function (x) { if (keys.indexOf(x) < 0) keys.push(x); });
        keys.forEach(function (x) {
          var a = has(s[k], x) ? s[k][x] : dflt, c = has(b[k], x) ? b[k][x] : dflt;
          if (a !== c) d[x] = a;
        });
        if (Object.keys(d).length) out[k] = d;
      } else if (!same(s[k], b[k])) out[k] = copy(s[k]);
    });
    return out;
  }

  /* ------------------------------------------------------------------ "Share this setup" (&bs=…) */
  // base64url (RFC 4648 §5, no padding) and UTF-8 by hand: a vm context and old browsers have no btoa / TextEncoder
  var B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  function utf8(s) {
    var out = [];
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c >= 0xd800 && c <= 0xdbff && i + 1 < s.length) {
        var d = s.charCodeAt(i + 1);
        if (d >= 0xdc00 && d <= 0xdfff) { c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00); i++; }
      }
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
      else if (c < 0x10000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
      else out.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 63), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    }
    return out;
  }
  /** Bytes → text, strictly: an overlong form, a surrogate, a cut sequence → null. */
  function fromUtf8(bytes) {
    var out = "", i = 0;
    while (i < bytes.length) {
      var b = bytes[i], c, need;
      if (b < 0x80) { c = b; need = 0; }
      else if (b >= 0xc2 && b <= 0xdf) { c = b & 31; need = 1; }
      else if (b >= 0xe0 && b <= 0xef) { c = b & 15; need = 2; }
      else if (b >= 0xf0 && b <= 0xf4) { c = b & 7; need = 3; }
      else return null;
      for (var k = 1; k <= need; k++) {
        var x = bytes[i + k];
        if (x === undefined || (x & 0xc0) !== 0x80) return null;
        c = (c << 6) | (x & 63);
      }
      if ((need === 2 && c < 0x800) || (need === 3 && (c < 0x10000 || c > 0x10ffff)) || (c >= 0xd800 && c <= 0xdfff)) return null;
      out += c < 0x10000 ? String.fromCharCode(c) : String.fromCharCode(0xd800 + ((c - 0x10000) >> 10), 0xdc00 + ((c - 0x10000) & 1023));
      i += need + 1;
    }
    return out;
  }
  function toB64(bytes) {
    var out = "", i = 0, n;
    for (; i + 2 < bytes.length; i += 3) {
      n = (bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2];
      out += B64.charAt((n >> 18) & 63) + B64.charAt((n >> 12) & 63) + B64.charAt((n >> 6) & 63) + B64.charAt(n & 63);
    }
    if (bytes.length - i === 1) {
      n = bytes[i] << 16;
      out += B64.charAt((n >> 18) & 63) + B64.charAt((n >> 12) & 63);
    } else if (bytes.length - i === 2) {
      n = (bytes[i] << 16) | (bytes[i + 1] << 8);
      out += B64.charAt((n >> 18) & 63) + B64.charAt((n >> 12) & 63) + B64.charAt((n >> 6) & 63);
    }
    return out;
  }
  /** base64url → bytes; null on a foreign character, an impossible length or stray bits (not the canonical form). */
  function fromB64(s) {
    if (s.length % 4 === 1) return null;
    var bytes = [], buf = 0, bits = 0;
    for (var i = 0; i < s.length; i++) {
      var v = B64.indexOf(s.charAt(i));
      if (v < 0) return null;
      buf = (buf << 6) | v;
      bits += 6;
      if (bits >= 8) {
        bits -= 8;
        bytes.push((buf >> bits) & 255);
        buf &= (1 << bits) - 1;
      }
    }
    return buf === 0 ? bytes : null;
  }
  /** A partial settings value exactly as normSettings would keep it — known keys, right kinds, numbers already in
   *  range — or null. What a share link may carry. */
  function strictPart(p) {
    if (!isMap(p)) return null;
    var keys = Object.keys(p), i;
    for (i = 0; i < keys.length; i++) if (!has(DEF, keys[i])) return null;
    var n = normSettings(p, DEF);
    for (i = 0; i < keys.length; i++) {
      var k = keys[i], v = p[k];
      if (has(MERGED, k)) {
        if (!isMap(v)) return null;
        var sub = Object.keys(v);
        for (var j = 0; j < sub.length; j++) if (!has(n[k], sub[j]) || n[k][sub[j]] !== v[sub[j]]) return null;
      } else if (!same(n[k], v)) return null;
    }
    return copy(p);
  }
  /** A partial settings value (diff()) → the text of the address's `&bs=`: base64url of {"v":1,"s":{…}}. null
   *  when the value is not one normSettings keeps as it is, or when the text would pass 2048 characters. */
  function encode(partial) {
    try {
      var p = strictPart(partial);
      if (!p) return null;
      var out = toB64(utf8(JSON.stringify({ v: SCHEMA, s: p })));
      return out.length <= SHARE_MAX ? out : null;
    } catch (e) {
      return null;
    }
  }
  /** The text of `&bs=` → the partial settings it carries, or null on anything wrong (length, characters, UTF-8,
   *  JSON, schema, an unknown key, a value of the wrong kind or out of range): nothing of a broken link is used. */
  function decode(s) {
    try {
      if (!isStr(s) || !s.length || s.length > SHARE_MAX || !/^[A-Za-z0-9_-]+$/.test(s)) return null;
      var bytes = fromB64(s);
      var text = bytes && fromUtf8(bytes);
      if (!isStr(text)) return null;
      var o = JSON.parse(text);
      if (!isMap(o) || o.v !== SCHEMA || !isMap(o.s) || Object.keys(o).length !== 2) return null;
      return strictPart(o.s);
    } catch (e) {
      return null;
    }
  }
  /** A preset's settings (a part: put it on top of the settings, then normSettings). null for an unknown name. */
  function preset(name) {
    switch (name) {
      case "assembly": return { lang: "both" };
      case "spanish": return { lang: "es", first: "es" };
      case "english": return { lang: "en", first: "en" };
      case "quiet": return { sound: false, pace: "calm", motion: "calm" };
      case "quizparty": return { boost: { quiz: 2, puzzles: 2 }, pace: "lively", clipEvery: 10 };
      default: return null;
    }
  }

  /* ------------------------------------------------------------------ chance, the day, the moment */
  /** mulberry32: a small seeded generator → a function giving numbers in [0, 1). The same seed, the same numbers. */
  function rng(seed) {
    var a = seedOf(seed);
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  /** Central time's offset from UTC in minutes at that instant, by the U.S. rule (since 2007): daylight time from
   *  the second Sunday of March, 2 AM, to the first Sunday of November, 2 AM. For a browser without time zones. */
  function centralOffset(t) {
    var y = new Date(t).getUTCFullYear();
    var mar = 1 + ((7 - new Date(Date.UTC(y, 2, 1)).getUTCDay()) % 7) + 7;
    var nov = 1 + ((7 - new Date(Date.UTC(y, 10, 1)).getUTCDay()) % 7);
    return t >= Date.UTC(y, 2, mar, 8) && t < Date.UTC(y, 10, nov, 7) ? -300 : -360;
  }
  /** "YYYY-MM-DD" of an instant in Central time (the committee's day: from / until are Central days). */
  function dayCentral(ms) {
    var t = isNum(ms) ? ms : Date.now();
    try {
      var p = new Intl.DateTimeFormat("en-US", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(t));
      var get = function (k) { for (var i = 0; i < p.length; i++) if (p[i].type === k) return p[i].value; return ""; };
      var s = get("year") + "-" + get("month") + "-" + get("day");
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    } catch (e) { /* a browser without time zones: the rule below */ }
    return new Date(t + centralOffset(t) * 60000).toISOString().slice(0, 10);
  }
  /** The moment a pool is made for: { now, today, online, page } (+ youtube: false, failed: { id: true } when the
   *  screen gives them). */
  function ctx(o) {
    var c = isMap(o) ? o : {};
    // a number, or a Date (also one from another frame: no instanceof)
    var t = c.now && typeof c.now.getTime === "function" ? c.now.getTime() : c.now;
    var now = isNum(t) ? t : Date.now();
    var out = { now: now, today: dayCentral(now), online: c.online !== false, page: c.page === "es" ? "es" : "en" };
    if (c.youtube === false) out.youtube = false;
    if (isMap(c.failed)) out.failed = c.failed;
    return out;
  }
  // a ctx() made earlier is used as it is; anything else goes through ctx() (online unless it says false)
  function ctxOf(c) { return isMap(c) && isNum(c.now) && isStr(c.today) && typeof c.online === "boolean" ? c : ctx(c); }

  /* ------------------------------------------------------------------ the player's own slides */
  function blank() { return { title: "", text: "", choices: [], answer: "", explain: "", credit: "", rows: [] }; }
  function words(fields) {
    var t = blank();
    Object.keys(fields).forEach(function (k) { t[k] = fields[k]; });
    return t;
  }
  function autoItem(name, en, es, qr, qrEs) {
    return {
      id: "auto:" + name, source: "auto", type: name, channel: name, pub: "both", langs: ["en", "es"], en: en, es: es,
      correct: null, seconds: null, reveal: null, weight: 1, from: null, until: null, tags: [], collection: "auto",
      first: false, order: null, media: null, online: false, qr: qr, qr_es: qr && qrEs && qrEs !== qr ? qrEs : null,
      url: qr, until_ts: null,
    };
  }
  /** auto:welcome — only while an event name is set (and shown): "Welcome! · {event}" in both languages (the
   *  Spanish name blank → the English one, and the other way round). */
  function welcomeItem(s) {
    var en = s.event.en.trim(), es = s.event.es.trim();
    if (s.event.show === false || (!en && !es)) return null;
    return autoItem("welcome",
      words({ title: fmt(WORDS.en.welcome, { event: en || es }), text: WORDS.en.welcome_text }),
      words({ title: fmt(WORDS.es.welcome, { event: es || en }), text: WORDS.es.welcome_text }), null);
  }
  /** auto:about — who shares the display, the site's address and QR, and that it is not an official display.
   *  Without booth.json's `site` (the fallback of an empty pool before anything loaded): the committee's name from
   *  here, no address (qr null — the screen shows the site's own QR). */
  function aboutItem(json) {
    var site = isMap(json) && isMap(json.site) ? json.site : {};
    var url = isStr(site.url) && /^https:\/\//.test(site.url) ? site.url : null;
    var urlEs = isStr(site.url_es) && /^https:\/\//.test(site.url_es) ? site.url_es : null;
    var host = str(site.host);
    return autoItem("about",
      words({ title: fmt(WORDS.en.shared_by, { committee: str(site.committee_en) || WORDS.en.committee }), text: WORDS.en.not_official, credit: host }),
      words({ title: fmt(WORDS.es.shared_by, { committee: str(site.committee_es) || WORDS.es.committee }), text: WORDS.es.not_official, credit: host }),
      url, urlEs);
  }
  /** The auto items that apply: auto:welcome while an event name is set, auto:about always. (Their channels and
   *  the other switches are why()'s business.) */
  function autoItems(json, settings) {
    var s = normSettings(settings);
    var w = welcomeItem(s);
    return w ? [w, aboutItem(json)] : [aboutItem(json)];
  }

  /* ------------------------------------------------------------------ the pool */
  var YMD = /^\d{4}-\d{2}-\d{2}$/;
  function channelOf(item) {
    if (isStr(item.channel) && CHANNEL_IDS.indexOf(item.channel) >= 0) return item.channel;
    var t = typeOf(item);
    return t && t.channel ? t.channel : "";
  }
  function pubOn(pub, pubs) {
    if (pub === "gv") return pubs.gv;
    if (pub === "lv") return pubs.lv;
    return pubs.gv || pubs.lv;
  }
  function langOk(item, mode) {
    var langs = langsOf(item);
    if (!langs.length) return true;                       // a picture or a sound without words
    if (mode === "en" || mode === "es") return langs.indexOf(mode) >= 0;
    return true;
  }
  function rowLive(r, now) { return isMap(r) && !(isNum(r.ends_ts) && now > r.ends_ts); }
  // (every language of an item has `rows`, mostly empty: a list is an item with rows in it)
  function hasRows(item) {
    return LANGS.some(function (l) { return isMap(item[l]) && list(item[l].rows).length > 0; });
  }
  /** A list whose rows are all over (or a live list with no rows at all). */
  function rowsOver(item, now) {
    if (!hasRows(item)) return isList(item);
    return !LANGS.some(function (l) {
      return isMap(item[l]) && list(item[l].rows).some(function (r) { return rowLive(r, now); });
    });
  }
  /** The item with the rows that are over taken out (a copy; the item itself when nothing changes). */
  function trimRows(item, now) {
    if (!hasRows(item)) return item;
    var drop = LANGS.some(function (l) {
      return isMap(item[l]) && list(item[l].rows).some(function (r) { return !rowLive(r, now); });
    });
    if (!drop) return item;
    var out = {};
    Object.keys(item).forEach(function (k) { out[k] = item[k]; });
    LANGS.forEach(function (l) {
      if (!isMap(item[l])) return;
      var t = {};
      Object.keys(item[l]).forEach(function (k) { t[k] = item[l][k]; });
      t.rows = list(item[l].rows).filter(function (r) { return rowLive(r, now); });
      out[l] = t;
    });
    return out;
  }
  function mediaOk(item, c) {
    if (c.failed && c.failed[item.id] === true) return false;
    if (MEDIA_TYPES.indexOf(item.type) < 0) return true;
    var m = item.media;
    if (!isMap(m) || MEDIA_KINDS.indexOf(m.kind) < 0) return false;
    if (m.kind === "youtube") return c.youtube !== false && isStr(m.id) && !!m.id;
    return isStr(m.src) && !!m.src;
  }
  var NONE = {};
  /** The reason an item may not show (null: it may). `ignore`: the checks saveList leaves out (SAVE_IGNORE). */
  function reason(item, s, c, ignore) {
    if (!isMap(item) || !isStr(item.id) || !typeOf(item)) return "media";
    if (!ignore.off && s.items[item.id] === false) return "off";
    var ch = channelOf(item);
    if (!ignore.channel && ch && s.channels[ch] === false) return "channel";
    if (!ignore.pub && !pubOn(item.pub, s.pubs)) return "pub";
    if (!ignore.collection && isStr(item.collection) && s.collections[item.collection] === false) return "collection";
    if (!ignore.tag) {
      var tags = list(item.tags);
      for (var i = 0; i < tags.length; i++) if (isStr(tags[i]) && s.tags[tags[i].toLowerCase()] === false) return "tag";
    }
    if (!ignore.date && ((isStr(item.from) && YMD.test(item.from) && item.from > c.today) ||
      (isStr(item.until) && YMD.test(item.until) && item.until < c.today))) return "date";
    if (!ignore.over && ((isNum(item.until_ts) && c.now > item.until_ts) || rowsOver(item, c.now))) return "over";
    if (!ignore.lang && !langOk(item, s.lang)) return "lang";
    if (!ignore.offline && item.online === true && !c.online) return "offline";
    if (!ignore.muted && item.type === "audio" && !s.sound) return "muted";
    if (!mediaOk(item, c)) return "media";
    return null;
  }
  /** Why an item may not show now: null, or off | channel | pub | collection | tag | date | over | lang | offline |
   *  muted | media (Settings → Items says it in words). */
  function why(item, settings, c) {
    return reason(item, normSettings(settings), ctxOf(c), NONE);
  }
  /** The items that may show now: json.items and the auto items that apply, each with its lists' past rows taken
   *  out, the others left out (why()). An item id is taken once. */
  function pool(json, settings, c) {
    var s = normSettings(settings), cx = ctxOf(c);
    var items = list(isMap(json) ? json.items : null).concat(autoItems(json, s));
    var out = [], seen = {};
    items.forEach(function (it) {
      if (!isMap(it) || !isStr(it.id) || has(seen, it.id)) return;
      seen[it.id] = 1;
      if (reason(it, s, cx, NONE) === null) out.push(trimRows(it, cx.now));
    });
    return out;
  }

  /* ------------------------------------------------------------------ the order of the slides */
  var COUNTERS = ["sinceWelcome", "sinceAbout", "sinceMedia", "sinceClip", "sincePlay", "sinceList", "langTurn"];
  /** A new show. seed: a number or a word (without one: from the clock — the tests always give one). */
  function newState(seed) {
    var sd = seed === undefined || seed === null ? ((Date.now() ^ Math.floor(Math.random() * 4294967296)) >>> 0) : seedOf(seed);
    return { seed: sd, n: 0, recent: [], firstQueue: null, lastType: null, sinceWelcome: 0, sinceAbout: 0, sinceMedia: 0, sinceClip: 0, sincePlay: 0, sinceList: 0, langTurn: 0 };
  }
  function count(v) { return isNum(v) && v >= 0 ? Math.floor(Math.min(v, 1e9)) : 0; }
  /** A state (also one stored in gv-booth-state-v1) as a fresh, safe copy. */
  function normState(raw) {
    var r = isMap(raw) ? raw : {};
    var st = newState(isNum(r.seed) ? r.seed : 1);
    st.n = count(r.n);
    st.recent = list(r.recent).filter(function (x) { return isStr(x) && x.length <= 200; }).slice(-RECENT_MAX);
    st.firstQueue = Array.isArray(r.firstQueue) ? r.firstQueue.filter(isStr) : null;
    st.lastType = isStr(r.lastType) && has(TYPES, r.lastType) ? r.lastType : null;
    COUNTERS.forEach(function (k) { st[k] = count(r[k]); });
    return st;
  }
  /** The items in the CSV / Drive order: those with an order number first (by the number), then the pool's order. */
  function ordered(items) {
    return items.map(function (it, i) { return { it: it, i: i, o: isNum(it.order) ? it.order : Infinity }; })
      .sort(function (a, b) { return (a.o - b.o) || (a.i - b.i); })
      .map(function (x) { return x.it; });
  }
  function weightOf(it, s) {
    var w = num(it.weight);
    if (!isFinite(w) || w <= 0) w = 1;
    var b = s.boost[channelOf(it)];
    return isNum(b) ? w * b : w;
  }
  function draw(cands, s, r) {
    var ws = cands.map(function (it) { return weightOf(it, s); });
    var total = ws.reduce(function (a, b) { return a + b; }, 0);
    var x = r() * total;
    for (var i = 0; i < cands.length; i++) {
      x -= ws[i];
      if (x < 0) return cands[i];
    }
    return cands[cands.length - 1];
  }
  // "since" counts the slides since the last one of its kind — or since the start when there was none yet
  function noneYet(st, k) { return st[k] >= st.n; }
  function due(st, k, every) { return st[k] >= every - 1; }
  /** The no-repeat window (rule 1) of a pool of n items: max(4, 40% of the pool), always less than the pool. */
  function windowOf(n) { return Math.min(Math.max(WINDOW_MIN, Math.ceil(WINDOW_SHARE * n)), n - 1); }
  /** The ids the no-repeat window holds now ({ id: 1 }): the last windowOf(pool) slides shown. */
  function recentOf(st, rest) {
    var size = windowOf(rest.length), out = {};
    st.recent.slice(size > 0 ? -size : st.recent.length).forEach(function (id) { out[id] = 1; });
    return out;
  }
  /** A clip (a video or a sound) may come now (rule 2): clipEvery slides after the last one — or none came yet. */
  function clipOk(st, s) { return due(st, "sinceClip", s.clipEvery) || noneYet(st, "sinceClip"); }
  /** The media slides one turn of the no-repeat window (window + 1 slides) has room for — each picture once, the
   *  clips once each but all of them together at most (window + 1) / clipEvery times (rule 2) — × clipEvery, so
   *  it stays a whole number (no rounding in the sums below). */
  function mediaRoom(rest, s) {
    var turn = windowOf(rest.length) + 1, pictures = 0, clips = 0;
    rest.forEach(function (it) { if (isClip(it)) clips++; else if (isMedia(it)) pictures++; });
    return pictures * s.clipEvery + Math.min(clips * s.clipEvery, turn);
  }
  /** How often a media slide is due: every EVERY.media slides — or, with too little room for that (each media item
   *  may come back only after the window, the clips only once in clipEvery slides), every (window + 1) / room
   *  slides, rounded down (each picture still shows once per window), so they spread over the window instead of
   *  all coming at once and then none for half an hour. Only clips (online, no pictures): one every clipEvery
   *  slides. Infinity when there are none. */
  function mediaEvery(rest, s) {
    var m = mediaRoom(rest, s);
    return m ? Math.max(EVERY.media, Math.floor((windowOf(rest.length) + 1) * s.clipEvery / m)) : Infinity;
  }
  /** Too little room for a media slide every EVERY.media slides (room × 4 ≤ window + 1): they come only on their
   *  turn (rule 7) — a media item drawn between turns would use them up early and leave a hole after. */
  function mediaScarce(rest, s) {
    var m = mediaRoom(rest, s);
    return m > 0 && m * EVERY.media <= (windowOf(rest.length) + 1) * s.clipEvery;
  }
  /** A media slide is due AND one can be drawn now (a media item outside the no-repeat window — a clip only when
   *  rule 2 lets it): only then does the media rule apply and do the welcome / about slides wait a slide for it.
   *  (A due media slide that cannot come must not hold them back: with few pictures they would wait until one left
   *  the window — 2 to 7 times less often than every 12 / 30 slides, and the about slide is the one that says the
   *  display is not official. Nor may it force a clip before its turn.) */
  function mediaReady(st, rest, s) {
    if (!due(st, "sinceMedia", mediaEvery(rest, s))) return false;
    var recent = recentOf(st, rest), clips = clipOk(st, s);
    return rest.some(function (it) { return isMedia(it) && (clips || !isClip(it)) && !has(recent, it.id); });
  }
  /** "In order": the item after the last ordered one shown, looping (from the start when none was). */
  function inOrder(st, rest) {
    var seq = ordered(rest), at = {};
    seq.forEach(function (it, i) { at[it.id] = i; });
    for (var i = st.recent.length - 1; i >= 0; i--) {
      if (has(at, st.recent[i])) return seq[(at[st.recent[i]] + 1) % seq.length];
    }
    return seq[0];
  }
  /** "Shuffle": a weighted draw among the items that keep the rules. Each rule, in the list's order (their
   *  importance), narrows the candidates unless none would be left: only then does that one rule give way, and the
   *  less important ones still apply (a rule that cannot be kept never takes the others with it). */
  function shuffle(st, rest, byId, s, r) {
    var recent = recentOf(st, rest);
    var photos = 0;
    for (var i = st.recent.length - 1; i >= 0 && byId[st.recent[i]] && byId[st.recent[i]].type === "photo"; i--) photos++;
    if (st.lastType !== "photo") photos = 0;
    var playOk = due(st, "sincePlay", EVERY.play) || noneYet(st, "sincePlay");
    var listOk = due(st, "sinceList", EVERY.list) || noneYet(st, "sinceList");
    var clipsOk = clipOk(st, s);
    var needMedia = mediaReady(st, rest, s);
    // few media items: only on their turn, so they stay spread over the window
    var mediaOk = needMedia || !mediaScarce(rest, s);
    // (the clip rule before the media rule: a media slide that is due narrows the draw to pictures while a clip
    // may not come yet, and waits when there are none — it never forces a clip)
    var rules = [
      function (it) { return !has(recent, it.id); },                                        // no repeat too soon
      function (it) { return clipsOk || !isClip(it); },                                      // ≤ 1 clip in clipEvery
      function (it) { return it.type !== st.lastType || (it.type === "photo" && photos < 2); },  // types vary
      function (it) { return playOk || !isPlay(it); },                                       // ≤ 1 play in 3
      function (it) { return !needMedia || isMedia(it); },                                   // media when due
      function (it) { return listOk || !isList(it); },                                       // ≤ 1 list in 6
      function (it) { return mediaOk || !isMedia(it); },                                     // few media: their turn
    ];
    // (`rest` is never empty here: pick() returns before)
    var cands = rest;
    rules.forEach(function (rule) {
      var kept = cands.filter(rule);
      if (kept.length) cands = kept;
    });
    return draw(cands, s, r);
  }
  function pick(st, items, byId, s, r) {
    if (!items.length) {
      // never a blank screen: the welcome slide (event set) and the about slide take turns
      var w0 = welcomeItem(s);
      return w0 && st.sinceWelcome >= st.sinceAbout ? w0 : aboutItem(null);
    }
    if (st.firstQueue === null) {
      st.firstQueue = has(byId, "auto:welcome") ? ["auto:welcome"] : [];
      ordered(items.filter(function (it) { return it.first === true && !isAuto(it); })).forEach(function (it) { st.firstQueue.push(it.id); });
    }
    while (st.firstQueue.length) {
      var id = st.firstQueue.shift();
      if (has(byId, id)) return byId[id];
    }
    var w = byId["auto:welcome"], a = byId["auto:about"];
    var rest = items.filter(function (it) { return !isAuto(it); });
    // the welcome / about slides when their turn has come — after a media slide that is due and can be shown now
    // (one that cannot come yet never holds them back)
    if (!(s.order === "shuffle" && mediaReady(st, rest, s))) {
      if (w && due(st, "sinceWelcome", EVERY.welcome)) return w;
      if (a && due(st, "sinceAbout", EVERY.about)) return a;
    }
    if (!rest.length) return w && a ? (st.sinceWelcome >= st.sinceAbout ? w : a) : (w || a);
    return s.order === "inorder" ? inOrder(st, rest) : shuffle(st, rest, byId, s, r);
  }
  function turnLang(t, first) { return t % 2 === 1 || t === 0 ? first : first === "en" ? "es" : "en"; }
  /** The state after `item` has been picked. */
  function after(st, item, s) {
    st.n += 1;
    st.recent.push(item.id);
    if (st.recent.length > RECENT_MAX) st.recent = st.recent.slice(-RECENT_MAX);
    st.lastType = item.type;
    st.sinceWelcome = item.id === "auto:welcome" ? 0 : st.sinceWelcome + 1;
    st.sinceAbout = item.id === "auto:about" ? 0 : st.sinceAbout + 1;
    st.sinceMedia = isMedia(item) ? 0 : st.sinceMedia + 1;
    st.sinceClip = isClip(item) ? 0 : st.sinceClip + 1;
    st.sincePlay = isPlay(item) ? 0 : st.sincePlay + 1;
    st.sinceList = isList(item) ? 0 : st.sinceList + 1;
    if (s.lang === "alternate") {
      // this slide's turn; a one-language slide takes its own language's turn, so the next one is the other
      var langs = langsOf(item), t = st.langTurn + 1;
      if (langs.length === 1 && turnLang(t, s.first) !== langs[0]) t += 1;
      st.langTurn = t;
    }
    return st;
  }
  /**
   * The next slide → { item, state }: the item from `items` (the pool) and the new state. Pure: `state` is not
   * changed. Each pick draws from mulberry32 seeded with the state's seed and slide number, so the same seed and
   * pool give the same show.
   */
  function next(state, items, settings, c) {
    var s = normSettings(settings);
    var st = normState(state);
    var good = list(items).filter(function (it) { return isMap(it) && isStr(it.id) && !!typeOf(it); });
    var byId = {}, uniq = [];
    good.forEach(function (it) { if (!has(byId, it.id)) { byId[it.id] = it; uniq.push(it); } });
    var r = rng((st.seed + Math.imul(st.n + 1, 0x9e3779b1)) >>> 0);
    var item = pick(st, uniq, byId, s, r);
    return { item: item, state: after(st, item, s) };
  }

  /* ------------------------------------------------------------------ languages and words */
  /** "en" | "es" | "both" for this slide: one language → that one; en / es → that one; both → "both";
   *  alternate → state.langTurn's language (settings.first on odd turns). */
  function lang(item, settings, state) {
    var s = normSettings(settings);
    var langs = langsOf(item);
    if (langs.length === 1) return langs[0];
    if (s.lang === "en" || s.lang === "es") return s.lang;
    if (s.lang === "both") return "both";
    return turnLang(isMap(state) ? count(state.langTurn) : 0, s.first);
  }
  function wordsOf(src) {
    var t = blank();
    if (!isMap(src)) return t;
    ["title", "text", "answer", "explain", "credit"].forEach(function (k) { t[k] = str(src[k]); });
    t.choices = list(src.choices).map(str);
    t.rows = list(src.rows).filter(isMap);
    return t;
  }
  /** The item's words in a language, every field there ("" / []). One language the item has no words for borrows
   *  the other's (a picture's caption); "both" → { en, es }, each its own (a missing one is all empty). */
  function text(item, l) {
    var it = isMap(item) ? item : {};
    if (l === "both") return { en: wordsOf(it.en), es: wordsOf(it.es) };
    var k = l === "es" ? "es" : "en", other = k === "en" ? "es" : "en";
    return wordsOf(isMap(it[k]) ? it[k] : it[other]);
  }
  /** {event} {committee} {site} {site_es} put in (an empty one takes the space before it away). */
  function fill(t, vars) {
    var v = isMap(vars) ? vars : {};
    return str(t).replace(/( ?)\{(event|committee|site|site_es)\}/g, function (m, sp, k) {
      var val = str(v[k]);
      return val ? sp + val : "";
    });
  }
  /** The address of a slide's QR code (SPEC update 1): on a Spanish slide the item's qr_es when it has one (a page
   *  of the site under /es/: a CSV qr_url written {site}…, a live list's page), else its qr; lang "both" → the first
   *  language's (settings.first). "" when the item has no code. */
  function qrOf(item, l, settings) {
    if (!isMap(item)) return "";
    var lg = l === "both" ? normSettings(settings).first : l;
    var es = lg === "es" && isStr(item.qr_es) ? item.qr_es : "";
    return es || (isStr(item.qr) ? item.qr : "");
  }

  /* ------------------------------------------------------------------ time on screen */
  /** The characters of those fields in a language ("both": the longer language's). */
  function shown(item, l, fields) {
    function n(lg) {
      var t = text(item, lg);
      return fields.reduce(function (a, f) { return a + (Array.isArray(t[f]) ? t[f].join(" ").length : t[f].length); }, 0);
    }
    return l === "both" ? Math.max(n("en"), n("es")) : n(l);
  }
  /** Reading time: 6 s + 1 s per 12 characters, × 1.7 for both languages, 8–30 s. */
  function readTime(chars, both) { return clamp((6 + chars / 12) * (both ? 1.7 : 1), 8, 30); }
  /** A video's or a sound's time: the part between start and end, at most mediaMax (a file of the booth) or
   *  webMediaMax (from the web). The screen moves on when it ends. */
  function mediaSeconds(item, s) {
    var m = isMap(item.media) ? item.media : {};
    var cap = m.local === true && m.kind !== "youtube" ? s.mediaMax : s.webMediaMax;
    var start = num(m.start), end = num(m.end);
    if (!isFinite(start) || start < 0) start = 0;
    if (isFinite(end) && end > start) cap = Math.min(cap, end - start);
    return tenth(Math.max(5, cap));
  }
  /** Seconds until the answer shows (quiz, truefalse, fill, scramble): the item's `reveal`, else settings.reveal,
   *  × pace. null for the other types (a poll shows its results live). */
  function revealAt(item, settings, l) {
    if (!isMap(item) || ANSWER_TYPES.indexOf(item.type) < 0) return null;
    var s = normSettings(settings);
    var v = num(item.reveal);
    return tenth((isFinite(v) && v > 0 ? clamp(v, 4, 60) : s.reveal) * PACE[s.pace]);
  }
  /** Seconds on screen for a slide in that language (SPEC §3.4). */
  function duration(item, settings, l) {
    var s = normSettings(settings);
    if (!isMap(item)) return 8;
    var both = l === "both", lg = both ? "both" : l === "es" ? "es" : "en";
    var pace = PACE[s.pace], type = item.type;
    if (type === "video" || type === "audio") return mediaSeconds(item, s);
    var own = num(item.seconds);
    own = isFinite(own) && own > 0 ? clamp(own, 3, 180) : null;
    var t;
    if (ANSWER_TYPES.indexOf(type) >= 0) {
      // the question until the reveal, then the answer and its explanation: 7 s + their reading time
      var at = revealAt(item, s, lg);
      var answer = 7 + shown(item, lg, ["answer", "explain"]) / 12 * (both ? 1.7 : 1);
      t = own !== null ? Math.max(own * pace, at + 4) : at + answer * pace;
      return tenth(clamp(t, 5, 180));
    }
    if (own !== null) t = own;
    else if (type === "poll" || type === "prompt" || type === "qr") t = 14;
    else if (type === "photo") t = s.photoSeconds;
    else if (type === "poster") t = 12;
    // a web picture: the photo time, longer when it has a caption to read
    else if (type === "image") t = shown(item, lg, ["text"]) ? Math.max(s.photoSeconds, readTime(shown(item, lg, ["title", "text", "credit"]), both)) : s.photoSeconds;
    else if (LISTS.indexOf(type) >= 0 || type === "prices") t = 15;
    else if (type === "countdown" || type === "welcome") t = 10;
    else if (type === "about") t = 12;
    else t = readTime(shown(item, lg, ["title", "text", "credit"]), both);
    return tenth(clamp(t * pace, 5, 180));
  }

  /* ------------------------------------------------------------------ puzzles, "Quiz me", polls */
  /** A word's letters shuffled (spaces stay where they are), never the word itself when that can be (3+ letters
   *  that are not all the same): the same seed, the same shuffle. */
  function scramble(word, seed) {
    var w = str(word);
    if (w.normalize) w = w.normalize("NFC");
    var chars = w.split(""), slots = [], letters = [];
    chars.forEach(function (ch, i) { if (!/\s/.test(ch)) { slots.push(i); letters.push(ch); } });
    if (letters.length < 2) return w;
    var key = letters.join("").toLowerCase();
    var r = rng(seed === undefined || seed === null ? w : seed);
    var out = letters;
    for (var tries = 0; tries < 30; tries++) {
      out = letters.slice();
      for (var i = out.length - 1; i > 0; i--) {
        var j = Math.floor(r() * (i + 1)), tmp = out[i];
        out[i] = out[j];
        out[j] = tmp;
      }
      if (out.join("").toLowerCase() !== key) break;
    }
    // still the word (a word of very few different letters): turned by a place or more
    for (var k = 1; k < letters.length && out.join("").toLowerCase() === key; k++) out = letters.slice(k).concat(letters.slice(0, k));
    var res = chars.slice();
    slots.forEach(function (pos, x) { res[pos] = out[x]; });
    return res.join("");
  }
  /** Can a visitor play this item in that language ("both": either)? A quiz needs its choices and the right one,
   *  a true / false its answer, a fill its missing words. */
  function playable(it, l) {
    if (!isMap(it) || QUIZ_TYPES.indexOf(it.type) < 0) return false;
    var langs = langsOf(it);
    var ls = (l === "en" || l === "es" ? [l] : LANGS).filter(function (x) { return langs.indexOf(x) >= 0; });
    if (!ls.length) return false;
    var t = text(it, ls[0]);
    if (!t.text) return false;
    if (it.type === "quiz") return isNum(it.correct) && it.correct >= 0 && it.correct < t.choices.length && t.choices.length >= 2;
    if (it.type === "truefalse") return typeof it.correct === "boolean";
    return !!t.answer;
  }
  /** "Quiz me": up to n (default 5, at most 20) quiz / truefalse / fill items a visitor can play in that
   *  language, none twice, in a random order. rng: a function from GVB.rng (or a seed). */
  function quizRound(items, l, n, r) {
    var rand = typeof r === "function" ? r : rng(isNum(r) || isStr(r) ? r : Math.floor(Math.random() * 4294967296));
    var k = clamp(Math.floor(num(n)) || 5, 1, 20);
    var seen = {}, cands = [];
    list(items).forEach(function (it) {
      if (playable(it, l) && !has(seen, it.id)) { seen[it.id] = 1; cands.push(it); }
    });
    for (var i = cands.length - 1; i > 0; i--) {
      var j = Math.floor(rand() * (i + 1)), tmp = cands[i];
      cands[i] = cands[j];
      cands[j] = tmp;
    }
    return cands.slice(0, k);
  }
  var POLL_IDS = 500, POLL_MAX = 1000000, CHOICES = 6;
  /** This device's poll votes made safe: { <id>: [counts] }. */
  function normPolls(p) {
    var out = {};
    if (!isMap(p)) return out;
    Object.keys(p).slice(0, POLL_IDS).forEach(function (k) {
      if (!ITEM_ID.test(k) || !Array.isArray(p[k])) return;
      out[k] = p[k].slice(0, CHOICES).map(function (c) { return isNum(c) && c >= 0 ? Math.min(Math.floor(c), POLL_MAX) : 0; });
    });
    return out;
  }
  /** One vote (choice: 0-based) → a new votes object; the old one is not changed. A wrong id or choice → the
   *  votes as they were. */
  function tally(polls, id, choice) {
    var out = normPolls(polls);
    var c = num(choice);
    if (!isStr(id) || !ITEM_ID.test(id) || !isFinite(c) || c < 0 || c >= CHOICES || Math.floor(c) !== c) return out;
    var row = out[id] || [];
    while (row.length <= c) row.push(0);
    row[c] = Math.min(row[c] + 1, POLL_MAX);
    out[id] = row;
    return out;
  }
  /** A poll's results: [{ count, pct }] for each of its choices; the pcts are whole numbers adding up to 100
   *  (largest remainder) once there is a vote, all 0 before. */
  function pollResults(polls, item) {
    if (!isMap(item)) return [];
    var k = Math.min(CHOICES, Math.max(text(item, "en").choices.length, text(item, "es").choices.length));
    var row = normPolls(polls)[item.id] || [];
    var counts = [];
    for (var i = 0; i < k; i++) counts.push(row[i] || 0);
    var total = counts.reduce(function (a, b) { return a + b; }, 0);
    if (!total) return counts.map(function () { return { count: 0, pct: 0 }; });
    var exact = counts.map(function (c) { return c * 100 / total; });
    var pct = exact.map(Math.floor);
    var left = 100 - pct.reduce(function (a, b) { return a + b; }, 0);
    exact.map(function (x, j) { return { j: j, rest: x - pct[j] }; })
      .sort(function (a, b) { return (b.rest - a.rest) || (a.j - b.j); })
      .slice(0, left)
      .forEach(function (x) { pct[x.j] += 1; });
    return counts.map(function (c, j) { return { count: c, pct: pct[j] }; });
  }

  /* ------------------------------------------------------------------ offline */
  // every switch a booth flips at the table, maybe offline (an item, a channel, a magazine, a collection, a tag; the
  // language, the sound) and the moment (the date, over, offline): their items' files are kept anyway, so a switch
  // turned back on offline still finds them — the build caps the folder (booth.max_total_mb), every switch is on by
  // default (the first save holds every file anyway), and the save's prune drops only what booth.json no longer
  // names (the service worker's rule). Only an item that cannot be shown at all (its type, its media) is left out.
  var SAVE_IGNORE = { off: 1, channel: 1, pub: 1, collection: 1, tag: 1, date: 1, over: 1, lang: 1, offline: 1, muted: 1 };
  function local(u, origin) {
    if (!isStr(u) || !u) return "";
    if (u.charAt(0) === "/" && u.charAt(1) !== "/" && u.charAt(1) !== "\\") return u;
    if (origin && u.indexOf(origin + "/") === 0) return u.slice(origin.length);
    return "";
  }
  /** What to keep for offline (paths on this site): the two About pages first (BOOTH_SAVE `pages`), then
   *  booth.json and every same-origin file of every item booth.json lists, whatever the switches say — media,
   *  posters, list thumbs (BOOTH_SAVE `files`). Each once. The settings do not change it (SAVE_IGNORE); the
   *  argument stays for the callers. */
  function saveList(json, settings, base) {
    var s = normSettings(settings);
    var site = isMap(json) && isMap(json.site) ? json.site : {};
    var b = isStr(base) && base ? base : str(site.base) || "/";
    if (b.charAt(0) !== "/") b = "/" + b;
    if (b.charAt(b.length - 1) !== "/") b += "/";
    var origin = (/^(https?:\/\/[^\/]+)/.exec(str(site.url)) || [])[1] || "";
    var out = [b + "about/", b + "es/about/", b + "about/booth.json"];
    function add(u) {
      var p = local(u, origin);
      if (p && out.indexOf(p) < 0) out.push(p);
    }
    var c = { now: 0, today: "", online: true, page: "en" };
    list(isMap(json) ? json.items : null).forEach(function (it) {
      if (!isMap(it) || reason(it, s, c, SAVE_IGNORE) !== null) return;
      if (isMap(it.media)) { add(it.media.src); add(it.media.poster); }
      LANGS.forEach(function (l) {
        if (isMap(it[l])) list(it[l].rows).forEach(function (r) { if (isMap(r)) add(r.thumb); });
      });
    });
    return out;
  }

  /* ------------------------------------------------------------------ the module */
  root.GVB = {
    VERSION: VERSION, SCHEMA: SCHEMA, APP: APP, STORAGE_KEY: STORAGE_KEY, POLLS_KEY: POLLS_KEY, STATE_KEY: STATE_KEY,
    TZ: TZ, LANGS: LANGS, MODES: MODES, PACE: PACE, REASONS: REASONS, PRESETS: PRESETS, LISTS: LISTS, EVERY: EVERY,
    WORDS: WORDS, DEFAULTS: copy(DEF), CHANNELS: copy(CHANNELS), TYPES: copy(TYPES),
    // the settings
    withDefaults: withDefaults, normSettings: normSettings, diff: diff, encode: encode, decode: decode, preset: preset,
    // chance, the day, the moment
    rng: rng, dayCentral: dayCentral, ctx: ctx,
    // the pool and the order
    autoItems: autoItems, why: why, pool: pool, newState: newState, normState: normState, next: next,
    // languages, words, time
    lang: lang, text: text, fill: fill, qrOf: qrOf, duration: duration, revealAt: revealAt,
    // puzzles, "Quiz me", polls, offline, text
    scramble: scramble, quizRound: quizRound, tally: tally, pollResults: pollResults, normPolls: normPolls,
    saveList: saveList, fmt: fmt,
  };
})(typeof window !== "undefined" ? window : globalThis);
