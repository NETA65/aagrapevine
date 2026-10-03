/* The booth display — the About page's #booth section (/about/, /es/about/): a show that plays by itself, all day,
   on a TV, laptop or tablet at the committee's Grapevine / La Viña table at assemblies and conventions. Quizzes with
   the answer shown after a while, true or false, facts, quotes, our history, fill in the blank, word scrambles,
   polls, "Let's talk" prompts, messages, QR codes, videos (the Drive booth folder's files and YouTube), sounds,
   photos and posters, and the site's live lists (events, a countdown to the next assembly, themes, prices, the Book
   of the Month, meetings) — in English, Spanish, both, or one then the other. Visitors can tap it to play. Opened
   once with internet, it keeps playing offline. The show is /about/booth.json (src/_data/booth.js); what may show
   now, what comes next, in which language and for how long is booth-core.js (window.GVB, tested on its own); this
   file is the screen. Plain JavaScript, no dependencies (loaded with `defer` after app.js and booth-core.js); the
   page works without it (the section then says the display needs JavaScript).

   Hooks on the page (src/_includes/macros/booth.njk; the dialog shell #gvb-tpl, the icons #gvb-icons and the words
   #gvb-config are printed at the end of the page):
     button[data-gvb-start]       starts the show: a full-screen dialog (a click = the gesture that lets the browser
                                  go full screen and play sound)
     button[data-gvb-settings]    the same dialog, opened on its Settings
     button[data-gvb-preview]     "Preview here": the show plays inside the preview card, without sound
     [data-gvb-pv-frame]          the 16:9 preview card: a still welcome slide; while it is on screen (and motion and
                                  data are welcome) a few real slides cycle in it, small and silent
     [data-gvb-q="event|event_es|lang|preset"]  the quick controls (they change the same settings as the dialog)
     [data-gvb-chip="items|content|offline"]    the status chips: slides in the show, the content's date, the
                                  offline copy
     the address ?booth=start     opens the show at once (muted until a tap where the browser asks for one: "Tap for
                                  full screen & sound"); &bs=<settings> applies a shared setup (Settings → Share)
   The screen (one engine per screen: the dialog, "Preview here", the cycling card): a header (the event's name and
   its second line, the clock, the language), the stage (ONE slide in the DOM, plus the one leaving while they
   cross), a footer (progress, "Tap to play", the site's QR code and address). Every slide is drawn by the renderer
   of its render type, inside try/catch: a slide that fails is skipped. A slide shows each text in its language
   (lang="en" / lang="es"); in Both, the first language first, the other under it after a rule — the screen's own
   words too ("Right!", "Show the answer", a poll's note), and a scramble's tiles: each language's from its own word.
   A live list (events, meetings, themes) and the prices fill a screen in one language: in Both their languages take
   turns on the slide instead (the first, then half-way through its time the other). A slide that would not fit at
   75 % of its type in two languages shows in one, the other leading its next showing: nothing is cut off. Sizes
   are in container units (areas/booth.css), so the same slide fills a TV and the small card.
   Visitors (Kiosk → "Visitors can tap"): a tap or a key brings up a bar (Back · Pause · Next · Quiz me · English /
   Español / Both · Take it home) in the show's language; quiz and true-or-false choices and poll options answer
   when tapped (the answer at once, ✓ / ✗, the explanation; a vote is counted on this device only — the focus a key
   left on a choice stays there); fill in the blank and scrambles get "Show the answer"; a video gets Sound (when
   the sound is allowed: a toggle, pressed while it plays with its sound) and Skip. A tap on a YouTube video lands in
   YouTube's player: the booth hears it as its window losing the focus to that frame, so the bar comes up as for any
   tap and the keys come back to the show, and a pause from inside the player plays on (YouTube's own links in its
   player stay as YouTube shows them: its API policies forbid disabling them). After the idle time without a touch
   the bar goes, a visitor's language choice is undone and the show goes on by itself. "Quiz me": a round of
   questions in the bar's language that wait for the visitor's answer (no timer; the idle time ends a round left
   half-way), a score, a friendly last card — no names, no rankings.
   Operator: S settings · Space pause · ← → back and next · F full screen · M sound · L language (English → Spanish
   → Both → Alternate) · Q quiz round · Esc closes a panel, then asks before leaving; on a touch screen, press and
   hold the event's name (top left) for 3 seconds for Settings, whose foot has "Leave the show". With a PIN
   (Settings → Kiosk) Settings and leaving ask for it first — kept on the device as typed: it only stops visitors.
   The PIN or "Leave?" box left open closes by itself after the idle time, Settings left alone after 2 minutes (or 3
   idle times): a visitor's hold never leaves the show dimmed all day.
   Robust for a whole day: timers live on the engine and stop with it; one 250 ms ticker moves the progress bar, the
   timer ring and the slide's clock (paused = it stands still, and holds a video still starting); a watchdog moves on
   when a slide outlives its time by 20 s; media elements and iframes are stopped and emptied when their slide goes;
   YouTube that does not start within 12 s is skipped (and left out for 10 minutes) — the wait for a start is not
   taken from a clip's time, so a short clip is checked too; a video or sound that stops for lack of data for 12 s is
   skipped; a failed load of YouTube's script leaves nothing behind; a picture or file that fails is skipped. Online /
   offline: navigator.onLine and a probe (build.json, every 60 s and after an online item fails; its unused answer is
   cancelled — an unread body keeps its loader alive); offline, the items that need internet leave the show quietly.
   New content (booth.json's `version`, checked every refreshMinutes) swaps in at the next slide. The screen stays on
   (Wake Lock) where the browser can.
   Offline: on start (and after new content), with internet and Kiosk → "Save for offline", the service worker is
   asked to keep both About pages, the show and its files (BOOTH_SAVE through a MessageChannel; BOOTH_PROGRESS /
   BOOTH_DONE come back), with progress on screen and in Settings → Offline (BOOTH_STATUS, BOOTH_CLEAR);
   navigator.storage.persist() is asked once. On a device that had the site before, the new worker may still wait
   behind the old one: for the operator's saves it takes over (SKIP_WAITING). A save asked while one runs (new
   content) runs when it ends; "Save now" goes on by itself; "Remove the offline copy" cancels a pending retry. A
   browser with no service worker says it can't keep a copy (on the screen too); the About page opened offline
   checks the saved copy.
   Accessibility: a modal dialog (the page behind is inert, focus stays inside — in "Take it home", and in Settings
   where they cover the show — and goes back to the opener), every control labelled, a polite live region (what a
   visitor's action did; the slides are not read out while the show plays by itself), reduced motion and Screen →
   "Calm" stop every animation (the progress bar still moves in steps), the high-contrast setting is followed.
   Storage (every access in try/catch; without storage it still plays and says so once): localStorage "gv-booth-v1"
   (this device's own settings — only what was changed here, so the site's defaults still apply to the rest),
   "gv-booth-polls-v1" (the poll votes counted here) and "gv-booth-state-v1" (the scheduler's memory of what it
   showed, when the offline copy was saved). Nothing is ever sent anywhere; a poll never asks for a name. */
(function () {
  "use strict";
  var G = window.GVB;
  if (!G || !document.querySelector || !document.getElementById("gvb-config")) return;

  /* ================================================================== 1. setup */
  var CFG = (function () {
    var node = document.getElementById("gvb-config");
    try { return JSON.parse(node.textContent || "{}") || {}; } catch (e) { return {}; }
  })();
  var LANG = CFG.lang === "es" ? "es" : "en";
  var STRINGS = CFG.t || {};
  var SCREEN = CFG.screen || {};
  var BASE = String(CFG.base || (window.SITE && window.SITE.base) || "/").replace(/\/?$/, "/");
  var JSON_URL = CFG.json || BASE + "about/booth.json";
  var BUILD_URL = CFG.build || BASE + "build.json";
  var PAGES = Array.isArray(CFG.pages) && CFG.pages.length ? CFG.pages : [BASE + "about/", BASE + "es/about/"];
  var SETTINGS_KEY = "gv-booth-v1", POLLS_KEY = "gv-booth-polls-v1", STATE_KEY = "gv-booth-state-v1";
  // the presets (assembly, spanish, english, quiet, quizparty) and the language modes (en, es, both, alternate — the
  // L key's order) are the core's
  var PRESETS = G.PRESETS.slice();
  var LANG_MODES = G.MODES.slice();
  // the dialog (one at a time): its root, its engine, what opened it
  var P = { root: null, E: null, opener: null, startUrl: "", inerted: [], drawer: false, tab: "event", modal: null, wake: null, pinResolve: null };
  var TICK_MS = 250;
  var WATCHDOG_SLACK = 20000;     // a slide that outlives its time by this much is moved on
  var YT_START_MS = 12000;        // YouTube that hasn't started by then is skipped …
  var YT_DOWN_MS = 600000;        // … and left out for 10 minutes
  var STALL_MS = 12000;           // a video or a sound that stops for lack of data this long is skipped
  var FAIL_MS = 600000;           // a file that failed is left out for 10 minutes (then tried again)
  var PROBE_MS = 60000;

  /** A control's words in the page language (src/_i18n/booth.json via the macro); {name} filled in. */
  function T(key, vars) {
    var s = STRINGS[key];
    if (typeof s !== "string") s = key;
    return fmt(s, vars || {});
  }
  function TN(key, n, vars) { return T(n === 1 ? key + "_one" : key, Object.assign({ n: n }, vars || {})); }
  /** A word on the screen, in a content language ("en" | "es"): the slide's, not the page's. */
  function S(l, key, vars) {
    var map = SCREEN[l === "es" ? "es" : "en"] || {};
    var s = map[key];
    if (typeof s !== "string") s = (SCREEN.en && SCREEN.en[key]) || key;
    return fmt(s, vars || {});
  }
  function SN(l, key, n, vars) { return S(l, n === 1 ? key + "_one" : key, Object.assign({ n: n }, vars || {})); }
  function reducedMotion() {
    try { return window.GV && window.GV.reducedMotion ? window.GV.reducedMotion() : window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }
  function now() { return Date.now(); }
  function perf() { return window.performance && performance.now ? performance.now() : Date.now(); }
  function clone(o) { try { return JSON.parse(JSON.stringify(o === undefined ? null : o)); } catch (e) { return null; } }
  function isObj(o) { return !!o && typeof o === "object" && !Array.isArray(o); }
  /** b merged into a (plain objects deeply; arrays and values replaced) — a new object. */
  function deepMerge(a, b) {
    var out = isObj(a) ? clone(a) : {};
    if (!isObj(b)) return out;
    Object.keys(b).forEach(function (k) {
      if (k === "__proto__" || k === "constructor" || k === "prototype") return;
      out[k] = isObj(b[k]) && isObj(out[k]) ? deepMerge(out[k], b[k]) : clone(b[k]);
    });
    return out;
  }
  function getPath(o, path) {
    return String(path).split(".").reduce(function (x, k) { return x && typeof x === "object" ? x[k] : undefined; }, o);
  }
  function setPath(o, path, v) {
    var parts = String(path).split("."), x = o;
    for (var i = 0; i < parts.length - 1; i++) {
      if (!isObj(x[parts[i]])) x[parts[i]] = {};
      x = x[parts[i]];
    }
    x[parts[parts.length - 1]] = v;
    return o;
  }

  /* ------------------------------------------------------------------ the core, through one door
     Every call into booth-core.js (window.GVB — the API its header describes, tested on its own) goes through
     call(): the core never throws on odd data, but should a call fail all the same, the plain answer given here takes
     its place and the show keeps playing. */
  function call(name, args, fallback) {
    try { return G[name].apply(G, args); } catch (e) { return fallback; }
  }
  function fmt(s, vars) {
    var text = String(s == null ? "" : s);
    var out = call("fmt", [text, vars || {}], null);
    return typeof out === "string" ? out : text;
  }
  /** The event's name in a content language (the other language's when this one is blank), "" while none is set
   *  or while Settings → Event says not to show it. */
  function eventName(l) {
    var ev = SETTINGS.event || {};
    if (ev.show === false) return "";
    return String(l === "es" ? (ev.es || ev.en || "") : (ev.en || ev.es || "")).trim();
  }
  /** {event} {committee} {site} {site_es} in a content language: the event's name ("this event" while none is set —
   *  a row may say "Welcome to {event}!"), the committee's name, the site's address and its Spanish home. */
  function fillVars(l) {
    var site = siteInfo();
    return {
      event: eventName(l) || S(l, "booth.screen.this_event"),
      committee: l === "es" ? site.committee_es || site.committee_en || "" : site.committee_en || "",
      site: site.host || "", site_es: site.url_es || "",
    };
  }
  function fill(text, l) {
    if (text == null || text === "") return "";
    return String(call("fill", [String(text), fillVars(l)], String(text)));
  }
  function rng(seed) { return call("rng", [seed], Math.random); }
  /** Settings made safe (unknown keys out, numbers clamped; never throws) — what a missing key takes: `base`. */
  function normSettings(raw, base) {
    var s = call("normSettings", [raw, base], null);
    return isObj(s) ? s : clone(G.DEFAULTS);
  }
  /** An item's words in one language: { title, text, choices, answer, explain, credit, rows }, every field there. */
  function textOf(item, l) { return call("text", [item, l], null) || {}; }
  function itemHasLang(item, l) {
    var t = item && item[l];
    return isObj(t) && !!(t.text || t.title || (t.rows && t.rows.length) || (t.choices && t.choices.length));
  }
  function poolOf(json, settings, ctx) { return call("pool", [json, settings, ctx], []); }
  /** Why an item may not show now: off | channel | pub | collection | tag | date | over | lang | offline | muted |
   *  media, or "" (it may). */
  function whyOf(item, settings, ctx) { return call("why", [item, settings, ctx], null) || ""; }
  function nextOf(state, pool, settings, ctx) { return call("next", [state, pool, settings, ctx], null) || { item: null, state: state }; }
  function langOf(item, settings, state) { return call("lang", [item, settings, state], settings.first === "es" ? "es" : "en"); }
  function durationOf(item, settings, l) { return call("duration", [item, settings, l], 12); }
  /** Seconds until the answer shows (quiz, truefalse, fill, scramble); 0 for the other types. */
  function revealOf(item, settings, l) { return call("revealAt", [item, settings, l], null) || 0; }
  function scrambleOf(word, seed) { return call("scramble", [word, seed], word); }
  function quizRoundOf(pool, l, n, r) { return call("quizRound", [pool, l, n, r], []); }
  function tallyOf(polls, id, choice) { return call("tally", [polls, id, choice], polls); }
  /** The votes for a poll as { counts: [n …], pcts: [whole % …], total } — from the core's [{ count, pct }] (its
   *  pcts add up to 100). */
  function pollResultsOf(polls, item, nChoices) {
    var r = call("pollResults", [polls, item], []);
    var counts = [], pcts = [];
    for (var i = 0; i < nChoices; i++) {
      var x = isObj(r[i]) ? r[i] : {};
      counts.push(Number(x.count) || 0);
      pcts.push(Number(x.pct) || 0);
    }
    return { counts: counts, pcts: pcts, total: counts.reduce(function (a, b) { return a + b; }, 0) };
  }
  function abs(u) { try { return new URL(u, location.href).href; } catch (e) { return ""; } }
  function sameOrigin(u) { try { return new URL(u, location.href).origin === location.origin; } catch (e) { return false; } }
  /** What the service worker keeps for offline use: the core's list (paths on this site) — its first two are both
   *  About pages (BOOTH_SAVE `pages`), the rest the show and the files its items use (`files`) — as addresses. */
  function saveListOf(json, settings) {
    var list = call("saveList", [json, settings, BASE], null) || PAGES.concat([JSON_URL]);
    var seen = {};
    var keep = function (part) {
      return part.map(abs).filter(function (u) { if (!u || !sameOrigin(u) || seen[u]) return false; seen[u] = 1; return true; });
    };
    return { pages: keep(list.slice(0, 2)), files: keep(list.slice(2)) };
  }
  function presetOf(name) { return call("preset", [name], null); }
  function channelIds() { return G.CHANNELS.map(function (c) { return c.id; }); }
  /* The core's own slides (auto:welcome, auto:about — their words also name them in Settings → Slides and for
     screen readers) say what this screen shows: src/_i18n/booth.json is the one place for those words, so they go
     into GVB.WORDS before the core makes anything (booth.screen.welcome, welcome_line, about_line, about_note). */
  (function () {
    var map = { welcome: "booth.screen.welcome", welcome_text: "booth.screen.welcome_line", shared_by: "booth.screen.about_line", not_official: "booth.screen.about_note" };
    ["en", "es"].forEach(function (l) {
      var words = G.WORDS && G.WORDS[l], screen = SCREEN[l];
      if (!isObj(words) || !isObj(screen)) return;
      Object.keys(map).forEach(function (k) { if (typeof screen[map[k]] === "string" && screen[map[k]]) words[k] = screen[map[k]]; });
    });
  })();

  /* ------------------------------------------------------------------ storage */
  var storageOk = true, warnedNoStorage = false;
  var STORED = {};            // this device's own choices (only what was changed here)
  var SETTINGS = normSettings({}, null);
  var POLLS = {};
  var MEMO = { sched: null, saved: null, persistAsked: false };
  function readJSON(key) {
    try {
      var v = localStorage.getItem(key);
      storageOk = true;
      return v ? JSON.parse(v) : null;
    } catch (e) {
      storageOk = false;
      return null;
    }
  }
  function writeJSON(key, value) {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(value));
      storageOk = true;
    } catch (e) {
      storageOk = false;
    }
    // the first change that cannot be kept says so (a private window, site data turned off)
    if (!storageOk && !warnedNoStorage && P.root) { warnedNoStorage = true; toast(T("booth.no_storage")); }
    var line = P.root ? P.root.querySelector("[data-gvb-nostore]") : null;
    if (line) line.hidden = storageOk;
    return storageOk;
  }
  /** The settings: the core's defaults, then the site's (booth.json `defaults`; the Spanish page leads in Spanish)
   *  — the BASE every device starts from — then this device's own choices, kept against it and made safe by the
   *  core (it never throws on garbage, it clamps every number). */
  var BASE_SETTINGS = null;
  function baseSettings() {
    var defs = (DATA && isObj(DATA.defaults)) ? DATA.defaults : {};
    BASE_SETTINGS = call("withDefaults", [defs, LANG], null) || clone(G.DEFAULTS);
    return BASE_SETTINGS;
  }
  function computeSettings() { SETTINGS = normSettings(STORED, baseSettings()); return SETTINGS; }
  function loadSettings() {
    var raw = readJSON(SETTINGS_KEY);
    STORED = isObj(raw) ? raw : {};
    return computeSettings();
  }
  /** Kept as a diff: only what differs from the site's starting settings (GVB.diff against booth.json's defaults),
   *  so a value this device never changed — or changed back — keeps following the site. (Before the show's file is
   *  in, the site's defaults are not known yet: what was changed is kept as it is, and made a diff later.) */
  function saveSettings() {
    if (DATA) {
      var d = call("diff", [SETTINGS, BASE_SETTINGS || baseSettings()], null);
      if (isObj(d)) STORED = d;
    }
    writeJSON(SETTINGS_KEY, Object.keys(STORED).length ? STORED : null);
  }
  /** One setting changed here (path like "event.en" or "channels.quiz"): kept, normalized, applied at once. */
  function setSetting(path, value, quiet) {
    setPath(STORED, path, value);
    computeSettings();
    // a value the core would not take (out of range …) is stored as the core reads it
    var got = getPath(SETTINGS, path);
    if (got !== undefined && JSON.stringify(got) !== JSON.stringify(value) && !isObj(got)) setPath(STORED, path, got);
    saveSettings();
    if (!quiet) settingsChanged(path);
  }
  function loadPolls() { var p = readJSON(POLLS_KEY); POLLS = isObj(p) ? p : {}; return POLLS; }
  function savePolls() { writeJSON(POLLS_KEY, Object.keys(POLLS).length ? POLLS : null); }
  function loadMemo() {
    var m = readJSON(STATE_KEY);
    MEMO = { sched: m && m.sched !== undefined ? m.sched : null, saved: m && isObj(m.saved) ? m.saved : null, persistAsked: !!(m && m.persistAsked) };
    return MEMO;
  }
  var memoTimer = 0, memoAt = 0;
  /** The scheduler's memory, written at most every 30 s (a whole day of slides is not a write per slide). */
  function saveMemo(soon) {
    clearTimeout(memoTimer);
    var write = function () { memoTimer = 0; memoAt = now(); writeJSON(STATE_KEY, MEMO); };
    if (!soon || now() - memoAt > 30000) write();
    else memoTimer = setTimeout(write, 30000);
  }

  /* ------------------------------------------------------------------ the show (booth.json), fetched on demand */
  var DATA = null, PENDING = null, LOADING = null;
  /** The site's addresses and names: booth.json's `site`, else the page's (#gvb-config). */
  function siteInfo() {
    var d = (DATA && isObj(DATA.site)) ? DATA.site : {};
    var c = CFG.site || {};
    return {
      url: d.url || c.url || abs(BASE), url_es: d.url_es || c.url_es || abs(BASE + "es/"),
      host: d.host || c.host || location.host + BASE.replace(/\/$/, ""),
      committee_en: d.committee_en || c.committee_en || "", committee_es: d.committee_es || c.committee_es || d.committee_en || c.committee_en || "",
    };
  }
  function siteUrl(l) { var s = siteInfo(); return l === "es" ? s.url_es : s.url; }
  function okShow(j) { return isObj(j) && j.app === "gv-booth" && Array.isArray(j.items); }
  /** The show's file (no-cache: the service worker answers network first, its copy when offline). */
  function loadData() {
    if (DATA) return Promise.resolve(DATA);
    if (LOADING) return LOADING;
    LOADING = fetch(JSON_URL, { cache: "no-cache", credentials: "same-origin" }).then(function (r) {
      if (!r.ok) { dropBody(r); throw new Error("HTTP " + r.status); }
      return r.json();
    }).then(function (j) {
      if (!okShow(j)) throw new Error("not the show");
      DATA = j;
      LOADING = null;
      computeSettings();
      onData();
      return j;
    }, function (e) {
      LOADING = null;
      throw e;
    });
    return LOADING;
  }
  /** New content (another `version`) is fetched every refreshMinutes while the show plays, and swapped in at the
   *  next slide (the settings stay; ids that are gone are simply not there any more). */
  var updateTimer = 0;
  function scheduleUpdates() {
    clearInterval(updateTimer);
    var min = Math.max(5, Number(SETTINGS.refreshMinutes) || 30);
    updateTimer = setInterval(checkUpdate, min * 60000);
  }
  function checkUpdate() {
    if (!NET.online || !DATA) return;
    fetch(JSON_URL, { cache: "no-cache", credentials: "same-origin" }).then(function (r) {
      if (r.ok) return r.json();
      dropBody(r);
      return null;
    }).then(function (j) {
      if (okShow(j) && j.version && j.version !== DATA.version) PENDING = j;
    }, function () { probe(); });
  }
  /** At a slide boundary: the new content in. */
  function swapPending() {
    if (!PENDING) return false;
    DATA = PENDING;
    PENDING = null;
    computeSettings();
    onData();
    live(T("booth.updated"));
    if (P.drawer) renderPanel(P.tab);
    saveOffline("update");
    return true;
  }

  /* ------------------------------------------------------------------ online / offline */
  var NET = { online: navigator.onLine !== false, n: 0, timer: 0, busy: false };
  /** An answer whose body is not used is cancelled: Chromium keeps a fetch's loader (~30 KB) alive until its body is
   *  read, so a probe left unread every minute would add ~15 MB a day to a booth that never reloads. */
  function dropBody(r) {
    try { var c = r && r.body && r.body.cancel(); if (c && c.catch) c.catch(function () { /* gone */ }); } catch (e) { /* no stream */ }
  }
  /** Is the site reachable? navigator.onLine first (false is trusted), then a small request that no cache answers. */
  function probe() {
    if (navigator.onLine === false) { setOnline(false); return; }
    if (NET.busy) return;
    NET.busy = true;
    var ctrl = window.AbortController ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, 4000);
    NET.n += 1;
    fetch(BUILD_URL + (BUILD_URL.indexOf("?") < 0 ? "?" : "&") + "booth=" + NET.n + "-" + now(), { cache: "no-store", credentials: "same-origin", signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) { setOnline(!!r.ok); dropBody(r); }, function () { setOnline(false); })
      .then(function () { clearTimeout(t); NET.busy = false; });
  }
  function setOnline(on) {
    var was = NET.online;
    NET.online = !!on;
    if (was === NET.online) return;
    if (NET.online && OFF.retry) saveOffline("online");
    if (P.drawer && (P.tab === "offline" || P.tab === "items" || P.tab === "show")) renderPanel(P.tab);
    renderChips();
  }
  function startProbes() {
    if (NET.timer) return;
    probe();
    NET.timer = setInterval(probe, PROBE_MS);
  }
  function stopProbes() { clearInterval(NET.timer); NET.timer = 0; }
  window.addEventListener("online", probe);
  window.addEventListener("offline", function () {
    setOnline(false);
    // a page opened online with Data saver on, now offline: the saved copy says whether the show is ready
    if (sectionSeen && !DATA && !LOADING) pageData().then(function () { offlineStatus(); }, function () { /* the chip says so */ });
  });

  // YouTube that did not start (or the API that did not load) is left out for 10 minutes; a file that failed too
  var YT = { promise: null, downUntil: 0 };
  var FAILED = {};
  function ytOk() { return now() > YT.downUntil; }
  function failedRecently(id) { return FAILED[id] && now() - FAILED[id] < FAIL_MS; }

  /* ================================================================== 2. DOM helpers */
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }
  function attrs(e, map) {
    Object.keys(map).forEach(function (k) {
      var v = map[k];
      if (v === null || v === undefined || v === false) e.removeAttribute(k);
      else e.setAttribute(k, v === true ? "" : String(v));
    });
    return e;
  }
  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); return node; }
  var uid = 0;
  function newId(prefix) { uid += 1; return (prefix || "gvb") + "-" + uid; }
  /** An icon from the macro's #gvb-icons (lucide, as the site's {% icon %} draws them). */
  function icon(name) {
    var tpl = document.getElementById("gvb-icons");
    var src = tpl && tpl.content ? tpl.content.querySelector('[data-gvb-icon="' + name + '"] svg') : null;
    if (src) return src.cloneNode(true);
    return attrs(el("span", "gvb-ic"), { "aria-hidden": "true" });
  }
  function button(cls, label, opts) {
    var b = el("button", cls);
    b.type = "button";
    opts = opts || {};
    if (opts.icon) b.appendChild(icon(opts.icon));
    if (label !== undefined && label !== null && label !== "") b.appendChild(el("span", opts.hideLabel ? "sr-only" : "", label));
    if (opts.aria) b.setAttribute("aria-label", opts.aria);
    if (opts.title) b.title = opts.title;
    if (opts.lang) b.setAttribute("lang", opts.lang);
    return b;
  }
  /** A QR code from the show's file (the build's SVG of squares) as a picture: an <img> never runs anything inside
   *  it. null when the show has no code for that address. */
  function qrImg(url, alt, cls) {
    var map = (DATA && DATA.qr) || {};
    var svg = url ? map[url] || map[abs(url)] || map[String(url).replace(/\/$/, "")] || map[String(url).replace(/\/?$/, "/")] : "";
    if (!svg || typeof svg !== "string" || svg.indexOf("<svg") < 0) return null;
    var img = el("img", cls || "");
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    img.alt = alt || "";
    img.decoding = "async";
    return img;
  }
  function hostOf(u) { try { var x = new URL(u); return (x.host + x.pathname).replace(/^www\./, "").replace(/\/$/, ""); } catch (e) { return String(u || ""); } }
  /** The address of an item's QR code in a content language: its Spanish page on a Spanish slide (qr_es — a CSV
   *  qr_url written {site}…, a live list's page under /es/), else its qr ("" when it has none). The core's qrOf;
   *  in Both the slide's first language decides (R.lead). */
  function qrFor(item, l) { return call("qrOf", [item, l, SETTINGS], (item && item.qr) || "") || ""; }
  /** A slide's own small code (a message, a live list, prices, the Book of the Month), or null. */
  function slideQr(R) {
    var u = qrFor(R.item, R.lead);
    return u ? qrImg(u, "QR: " + hostOf(u), "gvb-qrsmall") : null;
  }
  function setLang(node, l) { if (l) node.setAttribute("lang", l); return node; }

  /* ------------------------------------------------------------------ text → elements (never HTML) */
  /** Markdown-light into `parent`: **bold**, line breaks, "- " bullets. */
  function richInto(parent, text) {
    var lines = String(text || "").replace(/\r\n?/g, "\n").split("\n");
    var ul = null, firstLine = true;
    lines.forEach(function (line) {
      var m = /^\s*[-•*]\s+(.*)$/.exec(line);
      if (m) {
        if (!ul) { ul = el("ul"); parent.appendChild(ul); }
        boldInto(ul.appendChild(el("li")), m[1]);
        return;
      }
      ul = null;
      if (!line.trim()) { if (!firstLine) parent.appendChild(el("br")); return; }
      if (!firstLine && parent.lastChild && parent.lastChild.nodeName !== "UL" && parent.lastChild.nodeName !== "BR") parent.appendChild(el("br"));
      boldInto(parent, line);
      firstLine = false;
    });
    return parent;
  }
  function boldInto(parent, s) {
    String(s).split(/(\*\*[^*]+\*\*)/).forEach(function (part) {
      if (!part) return;
      var b = /^\*\*([^*]+)\*\*$/.exec(part);
      if (b) parent.appendChild(el("strong", "", b[1]));
      else parent.appendChild(document.createTextNode(part));
    });
    return parent;
  }
  function plain(s) { return String(s || "").replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\s+/g, " ").trim(); }
  /** At most n characters, cut at a word with "…". */
  function short(s, n) {
    s = String(s || "");
    if (s.length <= n) return s;
    var cut = s.slice(0, n - 1);
    var sp = cut.lastIndexOf(" ");
    return (sp > n * 0.6 ? cut.slice(0, sp) : cut).replace(/[\s,.;:—–-]+$/, "") + "…";
  }
  function locale(l) { return l === "es" ? "es-US" : "en-US"; }
  /** "October 2" for a day ("2026-10-02" is a day, never shifted by time zones). */
  function fmtDay(v, l, withYear) {
    if (!v) return "";
    var d = /^\d{4}-\d{2}-\d{2}$/.test(String(v)) ? new Date(String(v) + "T12:00:00Z") : new Date(v);
    if (isNaN(d)) return String(v);
    try {
      return d.toLocaleDateString(locale(l), { month: "long", day: "numeric", year: withYear ? "numeric" : undefined, timeZone: /^\d{4}-\d{2}-\d{2}$/.test(String(v)) ? "UTC" : "America/Chicago" });
    } catch (e) { return d.toISOString().slice(0, 10); }
  }
  function fmtStamp(ms, l) {
    try { return new Date(ms).toLocaleString(locale(l), { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); } catch (e) { return new Date(ms).toISOString(); }
  }
  function fileSize(b) {
    if (window.GV && typeof window.GV.fileSize === "function") return window.GV.fileSize(b) || "0 B";
    b = Number(b) || 0;
    var u = ["B", "KB", "MB", "GB"], i = 0;
    while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
    return b.toFixed(i ? 1 : 0) + " " + u[i];
  }

  /* ================================================================== 3. the slides
     One renderer per render type. A renderer gets R — { item, type, langs (["en"], ["es"] or both, the first
     language first), lead, E (the engine), interactive (taps answer), round (the quiz round, or null), t(l) (the
     item's words in a language, {event} … filled in) } — and returns { node, media, reveal, answer, vote, tick,
     seconds } (all but node optional): `media` plays and says when it ends, `reveal()` shows the answer, `answer(i)`
     is a visitor's tap on a choice, `tick(elapsed, total)` moves what shows the time, `seconds` overrides the
     duration. null = nothing to show (the next slide comes instead). */
  var RENDER = {};
  function words(item, l) {
    var t = textOf(item, l) || {};
    var f = function (v) { return typeof v === "string" ? fill(v, l) : ""; };
    return {
      title: f(t.title), text: f(t.text), answer: f(t.answer), explain: f(t.explain), credit: f(t.credit),
      choices: Array.isArray(t.choices) ? t.choices.map(f) : [],
      rows: Array.isArray(t.rows) ? t.rows.filter(isObj) : [],
    };
  }
  /** The slide's root: its render type, its magazine's colour, its first language, a label for screen readers. */
  function slideRoot(R, extra) {
    var root = el("section", "gvb-slide gvb-t-" + R.type + (extra ? " " + extra : ""));
    attrs(root, { "data-pub": pubOf(R.item), "data-item": R.item.id, lang: R.lead });
    return root;
  }
  function pubOf(item) { var p = item && item.pub; return p === "gv" || p === "lv" ? p : "both"; }
  function box(R, center, wide) {
    return el("div", "gvb-s" + (center ? " gvb-s--center" : "") + (wide ? " gvb-s--wide" : ""));
  }
  /** Marks a part for the entrance animation (in order: --i). */
  function enter(node, i) { node.classList.add("gvb-in"); node.style.setProperty("--i", String(i || 0)); return node; }
  /** The eyebrow: the slide's kind in its language(s), with the magazine's name for a Grapevine or La Viña slide. */
  function eyebrow(R, key, ico) {
    var row = el("p", "gvb-eyebrow");
    if (ico) row.appendChild(icon(ico));
    if (key) {
      row.appendChild(setLang(el("span", "", S(R.lead, key)), R.lead));
      if (R.langs.length > 1) {
        var alt = S(R.langs[1], key);
        if (alt !== S(R.lead, key)) {
          row.appendChild(attrs(el("span", "gvb-eyebrow-alt", "·"), { "aria-hidden": "true" }));
          row.appendChild(setLang(el("span", "gvb-eyebrow-alt", alt), R.langs[1]));
        }
      }
    }
    var p = pubOf(R.item);
    if (p !== "both") row.appendChild(el("span", "gvb-pubtag", S(R.lead, "booth.screen." + p)));
    return row;
  }
  /** Each language's block: the first into `parent`, the other into a quieter block under a rule (Both). */
  function perLang(R, parent, draw) {
    R.langs.forEach(function (l, i) {
      var blk = parent;
      if (i > 0) {
        blk = setLang(el("div", "gvb-alt"), l);
        blk.appendChild(attrs(el("span", "gvb-langtag", l.toUpperCase()), { "aria-hidden": "true" }));
        enter(blk, 3);
      }
      draw(blk, l, i);
      if (i > 0 && blk.children.length > 1) parent.appendChild(blk);
    });
  }
  function para(cls, text, l) { var p = setLang(el("p", cls), l); richInto(p, text); return p; }
  function long(s, n) { return String(s || "").length > n; }
  /** A few of the screen's own words in the slide's language(s), into `node`: the first language's, then (Both)
   *  " · " and the other's, quieter — `wordsIn(l)` gives them in a language ("Right!", "Show the answer"). */
  function inLangs(node, R, wordsIn) {
    clear(node);
    var first = wordsIn(R.lead);
    node.appendChild(setLang(el("span", "", first), R.lead));
    var l2 = R.langs[1];
    var second = l2 ? wordsIn(l2) : "";
    if (second && second !== first) {
      node.appendChild(attrs(el("span", "gvb-also", " · "), { "aria-hidden": "true" }));
      node.appendChild(setLang(el("span", "gvb-also", second), l2));
    }
    return node;
  }

  /* ---------- statements: fact, quote, history, prompt, message, qr, welcome, about ---------- */
  RENDER.fact = function (R) {
    var root = slideRoot(R), s = box(R);
    s.appendChild(enter(eyebrow(R, "booth.screen.fact", "lightbulb"), 0));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (!t.text && !t.title) return;
      if (t.title) blk.appendChild(enter(setLang(el("p", "gvb-h gvb-h--m", t.title), l), i ? 3 : 1));
      if (t.text) blk.appendChild(enter(para("gvb-txt gvb-txt--big" + (long(t.text, 170) ? " is-long" : ""), t.text, l), i ? 3 : 2));
      if (t.credit && (i === R.langs.length - 1 || t.credit !== R.t(R.langs[R.langs.length - 1]).credit)) blk.appendChild(setLang(el("p", "gvb-credit", t.credit), l));
    });
    root.appendChild(s);
    return { node: root };
  };
  RENDER.quote = function (R) {
    var root = slideRoot(R), s = box(R);
    var q = el("div", "gvb-quote");
    q.appendChild(attrs(el("span", "gvb-quote-mark", "“"), { "aria-hidden": "true" }));
    perLang(R, q, function (blk, l, i) {
      var t = R.t(l);
      if (!t.text) return;
      var p = enter(para("gvb-txt gvb-txt--big" + (long(t.text, 200) ? " is-long" : ""), t.text, l), i ? 3 : 1);
      if (i === 0) {
        var bq = el("blockquote");
        bq.appendChild(p);
        blk.appendChild(bq);
      } else blk.appendChild(p);
      if (t.credit) blk.appendChild(enter(setLang(el("p", "gvb-credit", "— " + t.credit), l), i ? 3 : 2));
    });
    // a heading of its own (the Daily Quote: "Grapevine Daily Quote · Oct 2") in the eyebrow's place
    var head = eyebrow(R, "", "quote");
    var qt = R.t(R.lead).title;
    if (qt) head.insertBefore(setLang(el("span", "", qt), R.lead), head.children[1] || null);
    s.appendChild(enter(head, 0));
    s.appendChild(q);
    root.appendChild(s);
    return { node: root };
  };
  RENDER.history = function (R) {
    var root = slideRoot(R), s = box(R);
    s.appendChild(enter(eyebrow(R, "booth.screen.history", "history"), 0));
    var lead = R.t(R.lead);
    if (lead.title) s.appendChild(enter(setLang(el("p", "gvb-year", lead.title), R.lead), 1));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (i > 0 && t.title && t.title !== lead.title) blk.appendChild(setLang(el("p", "gvb-h gvb-h--m", t.title), l));
      if (t.text) blk.appendChild(enter(para(i ? "gvb-txt" : "gvb-txt gvb-txt--big" + (long(t.text, 170) ? " is-long" : ""), t.text, l), i ? 3 : 2));
      if (t.credit && i === R.langs.length - 1) blk.appendChild(setLang(el("p", "gvb-credit", t.credit), l));
    });
    root.appendChild(s);
    return { node: root };
  };
  RENDER.prompt = function (R) {
    var root = slideRoot(R), s = box(R, true);
    s.appendChild(enter(eyebrow(R, "booth.screen.prompt", "message-circle-question"), 0));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (!t.text) return;
      blk.appendChild(enter(para(i ? "gvb-q" : "gvb-h" + (long(t.text, 110) ? " gvb-h--m" : ""), t.text, l), i ? 3 : 1));
    });
    var ask = el("p", "gvb-txt gvb-txt--muted");
    ask.appendChild(setLang(el("span", "", S(R.lead, "booth.screen.prompt_line")), R.lead));
    if (R.langs.length > 1) {
      ask.appendChild(document.createTextNode(" · "));
      ask.appendChild(setLang(el("span", "", S(R.langs[1], "booth.screen.prompt_line")), R.langs[1]));
    }
    s.appendChild(enter(ask, 4));
    root.appendChild(s);
    return { node: root };
  };
  RENDER.message = function (R) {
    var root = slideRoot(R), s = box(R);
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (t.title) blk.appendChild(enter(setLang(el("p", i ? "gvb-h gvb-h--m" : "gvb-h", t.title), l), i ? 3 : 0));
      if (t.text) blk.appendChild(enter(para("gvb-txt" + (i ? "" : long(t.text, 260) ? "" : " gvb-txt--big"), t.text, l), i ? 3 : 1));
    });
    var qr = slideQr(R);
    if (qr) {
      var wrap = el("div", "gvb-withqr");
      wrap.appendChild(s);
      wrap.appendChild(enter(qr, 2));
      root.appendChild(wrap);
    } else root.appendChild(s);
    return { node: root };
  };
  RENDER.qr = function (R) {
    var url = qrFor(R.item, R.lead) || R.item.url;
    var lead = R.t(R.lead);
    var img = qrImg(url, "QR: " + (lead.title || hostOf(url)), "gvb-qrbig");
    if (!img) return null;
    var root = slideRoot(R), b = el("div", "gvb-qrbox");
    b.appendChild(enter(img, 1));
    var w = el("div", "gvb-qrwords");
    w.appendChild(enter(eyebrow(R, "booth.screen.qr", "qr-code"), 0));
    perLang(R, w, function (blk, l, i) {
      var t = R.t(l);
      if (t.title) blk.appendChild(enter(setLang(el("p", i ? "gvb-h gvb-h--m" : "gvb-h", t.title), l), i ? 3 : 1));
      if (t.text) blk.appendChild(enter(para("gvb-txt", t.text, l), i ? 3 : 2));
    });
    w.appendChild(enter(el("p", "gvb-qrurl", hostOf(url)), 4));
    b.appendChild(w);
    root.appendChild(b);
    return { node: root };
  };
  /** "Welcome!" big, the event's name on its own line under it (no sentence joins them: "Welcome to {event}!" reads
   *  wrong with many names — "¡Bienvenidos a Asamblea…!" lacks its "la"), then "Grapevine and La Viña — ask us
   *  anything"; in Both the other language's under a rule (its name only when it differs). */
  RENDER.welcome = function (R) {
    var root = slideRoot(R), s = box(R, true);
    var mark = el("p", "gvb-welcome-mark");
    mark.appendChild(icon("grapes"));
    s.appendChild(enter(attrs(mark, { "aria-hidden": "true" }), 0));
    var leadName = eventName(R.lead);
    perLang(R, s, function (blk, l, i) {
      var ev = eventName(l);
      blk.appendChild(enter(setLang(el("p", i ? "gvb-h gvb-h--m" : "gvb-h gvb-h--xl", S(l, "booth.screen.welcome_plain")), l), i ? 3 : 1));
      if (ev && (i === 0 || ev !== leadName)) blk.appendChild(enter(setLang(el("p", i ? "gvb-txt" : "gvb-h gvb-h--m", ev), l), i ? 3 : 1.5));
      blk.appendChild(enter(setLang(el("p", "gvb-txt" + (i ? "" : " gvb-txt--big"), S(l, "booth.screen.welcome_line")), l), i ? 3 : 2));
    });
    root.appendChild(s);
    return { node: root };
  };
  /** Who shares the display, with the site's code — and, right under the heading, that it is not an official
   *  AA Grapevine, Inc. or A.A.W.S. display, in each language shown (one line: never the part a long slide loses at
   *  its bottom). */
  RENDER.about = function (R) {
    var root = slideRoot(R, "gvb-t-about"), s = box(R, true);
    var site = siteInfo();
    var url = siteUrl(R.lead);
    var img = qrImg(url, "QR: " + site.host, "gvb-qrbig");
    if (img) s.appendChild(enter(img, 0));
    perLang(R, s, function (blk, l, i) {
      var committee = l === "es" ? site.committee_es : site.committee_en;
      blk.appendChild(enter(setLang(el("p", i ? "gvb-txt" : "gvb-h gvb-h--m", S(l, "booth.screen.about_line", { committee: committee })), l), i ? 3 : 1));
      if (i === 0) {
        blk.appendChild(enter(inLangs(el("p", "gvb-about-note"), R, function (x) { return S(x, "booth.screen.about_note"); }), 1.5));
        blk.appendChild(enter(el("p", "gvb-qrurl", site.host), 2));
      }
    });
    root.appendChild(s);
    return { node: root };
  };

  /* ---------- play: quiz, true or false ---------- */
  /** The SVG timer ring (until the answer shows) with the seconds left in it. */
  function timerRing() {
    var wrap = attrs(el("div", "gvb-ring"), { "aria-hidden": "true" });
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    var track = document.createElementNS(ns, "circle"), bar = document.createElementNS(ns, "circle");
    [track, bar].forEach(function (c) { c.setAttribute("cx", "50"); c.setAttribute("cy", "50"); c.setAttribute("r", "40"); svg.appendChild(c); });
    track.setAttribute("class", "gvb-ring-track");
    bar.setAttribute("class", "gvb-ring-bar");
    wrap.appendChild(svg);
    var n = el("span", "gvb-ring-n", "");
    wrap.appendChild(n);
    var last = -1;
    return {
      node: wrap,
      set: function (frac, secondsLeft) {
        bar.style.strokeDashoffset = String(251.33 * Math.max(0, Math.min(1, frac)));
        var s = Math.max(0, Math.ceil(secondsLeft));
        if (s !== last) { last = s; n.textContent = String(s); }
      },
    };
  }
  function choiceMark(right) { var m = icon(right ? "circle-check" : "circle-x"); m.setAttribute("class", "gvb-ic gvb-choice-mark"); return m; }
  RENDER.quiz = function (R) {
    var tf = R.type === "truefalse";
    var lead = R.t(R.lead);
    var alt = R.langs.length > 1 ? R.t(R.langs[1]) : null;
    var labels = tf ? [S(R.lead, "booth.screen.true"), S(R.lead, "booth.screen.false")] : lead.choices;
    var altLabels = alt ? (tf ? [S(R.langs[1], "booth.screen.true"), S(R.langs[1], "booth.screen.false")] : alt.choices) : null;
    if (!lead.text || !labels.length) return null;
    var correct = tf ? (R.item.correct === true || R.item.correct === "true" ? 0 : 1) : Number(R.item.correct);
    if (!(correct >= 0 && correct < labels.length)) return null;
    var root = slideRoot(R), s = box(R, false, true);
    var top = el("div", "gvb-toprow");
    top.appendChild(eyebrow(R, tf ? "booth.screen.truefalse" : "booth.screen.quiz", tf ? "check" : "circle-help"));
    var ring = timerRing();
    top.appendChild(ring.node);
    s.appendChild(enter(top, 0));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (t.text) blk.appendChild(enter(para(i ? "gvb-txt" : "gvb-q" + (long(t.text, 120) ? " is-long" : ""), t.text, l), i ? 2 : 1));
    });
    // (in Both the question's second language sits under the first, before the choices)
    var grid = el("div", "gvb-choices" + (tf ? " is-tf" : labels.length >= 4 || labels.length === 2 ? " is-grid" : ""));
    var btns = labels.map(function (label, i) {
      var b = el("button", "gvb-choice");
      b.type = "button";
      b.setAttribute("data-i", String(i));
      if (!R.interactive) { b.disabled = true; b.tabIndex = -1; }
      if (!tf) b.appendChild(attrs(el("span", "gvb-choice-k", String.fromCharCode(65 + i)), { "aria-hidden": "true" }));
      var w = el("span", "gvb-choice-w");
      w.appendChild(setLang(el("span", "gvb-choice-t", label), R.lead));
      if (altLabels && altLabels[i] && altLabels[i] !== label) w.appendChild(setLang(el("span", "gvb-choice-alt", altLabels[i]), R.langs[1]));
      b.appendChild(w);
      b.appendChild(choiceMark(i === correct));
      if (!tf) b.insertBefore(el("span", "sr-only", String.fromCharCode(65 + i) + ". "), b.firstChild);
      // (the right one known to the layout, unseen: fitSlide measures the answer's layout — this one kept, the others
      // gone — before it shows)
      if (i === correct) b.classList.add("is-answer");
      grid.appendChild(enter(b, 2 + i * 0.5));
      return b;
    });
    s.appendChild(grid);
    var ex = explainBox(R);
    s.appendChild(ex.node);
    if (lead.credit) s.appendChild(setLang(el("p", "gvb-credit", lead.credit), R.lead));
    root.appendChild(s);
    var picked = -1;
    return {
      node: root, ring: ring,
      reveal: function () {
        btns.forEach(function (b, i) {
          b.classList.toggle("is-right", i === correct);
          if (i === correct) b.appendChild(setLang(el("span", "sr-only", " (" + S(R.lead, "booth.screen.right_answer") + ")"), R.lead));
          // answered: no more taps (the engine takes one answer), but the button keeps the focus a visitor's key left
          // on it, and Tab still reaches "(the right answer)" and "(your answer)"
          if (!b.disabled) b.setAttribute("aria-disabled", "true");
        });
        ex.show();
      },
      // a visitor's tap: ✓ or ✗ on their choice, "Right!" or "Not quite — here's the answer." over the explanation
      answer: function (i) {
        if (picked >= 0 || !(i >= 0 && i < btns.length)) return null;
        picked = i;
        btns[i].classList.add("is-picked");
        btns[i].appendChild(setLang(el("span", "sr-only", " (" + S(R.lead, "booth.screen.your_answer") + ")"), R.lead));
        var right = i === correct;
        ex.say(right);
        return right;
      },
    };
  };
  RENDER.truefalse = RENDER.quiz;
  /** The answer's box: "Answer" (or a visitor's "Right!" / "Not quite …", in each language shown) and the
   *  explanation in each language. Out of the layout until the answer shows (no empty room under the question);
   *  fitSlide sizes the slide for the taller of the question and the answer, so nothing jumps when it comes. */
  function explainBox(R, answerText) {
    var ex = el("div", "gvb-explain is-waiting");
    var h = el("p", "gvb-explain-h");
    var ico = icon("check");
    h.appendChild(ico);
    var label = inLangs(el("span"), R, function (l) { return S(l, "booth.screen.answer"); });
    h.appendChild(label);
    ex.appendChild(h);
    var any = false;
    R.langs.forEach(function (l, i) {
      var t = R.t(l);
      var line = answerText && answerText[l] ? answerText[l] : "";
      var text = [line, t.explain].filter(Boolean).join(" — ");
      if (!text) return;
      any = true;
      ex.appendChild(para(i ? "gvb-alt-line" : "gvb-txt", text, l));
    });
    if (!any) ex.classList.add("is-empty");
    var said = null;
    return {
      node: ex,
      show: function () {
        if (!any && said === null) return;
        ex.classList.remove("is-waiting");
        ex.classList.add("gvb-reveal-in");
      },
      say: function (right) {
        said = !!right;
        inLangs(label, R, function (l) { return S(l, right ? "booth.screen.right" : "booth.screen.wrong"); });
        ex.classList.toggle("is-wrong", !right);
        var mark = icon(right ? "check" : "circle-x");
        h.replaceChild(mark, h.firstChild);
        ex.classList.remove("is-empty");
      },
    };
  }

  /* ---------- puzzles: fill in the blank, scramble ---------- */
  var BLANK = /_{3,}/;
  /** The sentence with its blank (a box that the answer writes itself into at the reveal). */
  function blankSentence(cls, text, l) {
    var p = setLang(el("p", cls), l);
    var parts = String(text).split(BLANK);
    boldInto(p, parts[0] || "");
    var blank = el("span", "gvb-blank");
    p.appendChild(blank);
    if (parts.length > 1) boldInto(p, parts.slice(1).join(" "));
    return { node: p, blank: blank };
  }
  function writeInto(blank, word) {
    clear(blank);
    String(word).split("").forEach(function (ch, i) {
      var sp = el("span", "", ch === " " ? " " : ch);
      sp.style.setProperty("--i", String(i));
      blank.appendChild(sp);
    });
  }
  /** "Show the answer" for a visitor (fill in the blank, scramble), in the slide's language(s). */
  function showAnswerBtn(R, s) {
    if (!R.interactive) return null;
    var b = el("button", "gvb-showans");
    b.type = "button";
    b.appendChild(icon("eye"));
    b.appendChild(inLangs(el("span"), R, function (l) { return S(l, "booth.screen.show_answer"); }));
    b.setAttribute("data-gvb-reveal", "");
    s.appendChild(enter(b, 5));
    return b;
  }
  RENDER.fill = function (R) {
    var lead = R.t(R.lead);
    if (!lead.text || !BLANK.test(lead.text) || !lead.answer) return null;
    var root = slideRoot(R), s = box(R, false, true);
    var top = el("div", "gvb-toprow");
    top.appendChild(eyebrow(R, "booth.screen.fill", "pen-line"));
    var ring = timerRing();
    top.appendChild(ring.node);
    s.appendChild(enter(top, 0));
    var blanks = [];
    R.langs.forEach(function (l, i) {
      var t = R.t(l);
      if (!t.text || !BLANK.test(t.text)) return;
      var bs = blankSentence(i ? "gvb-txt" : "gvb-q" + (long(t.text, 110) ? " is-long" : ""), t.text, l);
      blanks.push({ blank: bs.blank, answer: t.answer || lead.answer });
      if (i === 0) s.appendChild(enter(bs.node, 1));
      else {
        var blk = setLang(el("div", "gvb-alt"), l);
        blk.appendChild(attrs(el("span", "gvb-langtag", l.toUpperCase()), { "aria-hidden": "true" }));
        blk.appendChild(bs.node);
        s.appendChild(enter(blk, 3));
      }
    });
    var btn = showAnswerBtn(R, s);
    var ex = explainBox(R);
    s.appendChild(ex.node);
    root.appendChild(s);
    return {
      node: root, ring: ring,
      reveal: function () {
        blanks.forEach(function (b) { writeInto(b.blank, b.answer); });
        if (btn) btn.hidden = true;
        ex.show();
      },
    };
  };
  /** One row of letter tiles for a word in a language: each word of it scrambled on its own, its letters in a
   *  shuffled order (the same order each time it shows), and the letters as one line for screen readers (in that
   *  language). → { node, order (the tiles in their right order), sr, word } */
  function tileRow(word, seed, l, alt) {
    var tiles = attrs(el("div", "gvb-tiles" + (word.length > 10 ? " is-many" : "") + (alt ? " gvb-tiles--alt" : "")), { "aria-hidden": "true" });
    var order = [];        // the tiles in their correct order
    var shown = [];        // the tiles as first laid out
    word.split(/(\s+)/).forEach(function (part, wi) {
      if (!part) return;
      if (/^\s+$/.test(part)) { var gap = el("span", "gvb-tile gvb-tile--gap"); order.push(gap); shown.push(gap); return; }
      var right = part.split("").map(function (ch) { return el("span", "gvb-tile", ch.toUpperCase()); });
      order = order.concat(right);
      var mixed = scrambleOf(part, seed + wi);
      var pool = right.slice();
      mixed.split("").forEach(function (ch) {
        var at = -1;
        for (var j = 0; j < pool.length; j++) if (pool[j].textContent === ch.toUpperCase()) { at = j; break; }
        if (at < 0) at = 0;
        shown.push(pool.splice(at, 1)[0]);
      });
    });
    shown.forEach(function (t) { tiles.appendChild(t); });
    var sr = setLang(el("p", "sr-only", shown.map(function (t) { return t.textContent; }).join(" ")), l);
    return { node: tiles, order: order, sr: sr, word: word };
  }
  /** The same word whatever its case, its accents' form and its spaces ("PODCAST" / "Podcast"): one row of tiles
   *  serves both languages then. */
  function sameWord(a, b) {
    var f = function (s) { s = String(s || ""); if (s.normalize) s = s.normalize("NFC"); return s.toUpperCase().replace(/\s+/g, ""); };
    return f(a) === f(b);
  }
  /** A scramble: the clue in each language and the letter tiles; in Both, a language whose word differs (Preamble /
   *  Preámbulo, Sponsor / Padrino) gets its own, smaller row under its own clue — each row is made of its own word's
   *  letters, and each puts itself in order at the reveal. */
  RENDER.scramble = function (R) {
    var lead = R.t(R.lead);
    var word = String(lead.answer || "").trim();
    if (!word || word.replace(/\s/g, "").length < 2) return null;
    var root = slideRoot(R), s = box(R, true, true);
    var top = el("div", "gvb-toprow");
    top.appendChild(eyebrow(R, "booth.screen.scramble", "puzzle"));
    var ring = timerRing();
    top.appendChild(ring.node);
    s.appendChild(enter(top, 0));
    var seed = 0;
    for (var k = 0; k < R.item.id.length; k++) seed = (seed * 31 + R.item.id.charCodeAt(k)) >>> 0;
    var altL = R.langs[1];
    var altWord = altL ? String(R.t(altL).answer || "").trim() : "";
    var split = !!altL && altWord.replace(/\s/g, "").length >= 2 && !sameWord(altWord, word);
    var leadRow = tileRow(word, seed, R.lead, false);
    var rows = [leadRow];
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (t.text) blk.appendChild(enter(para(i ? "gvb-txt" : "gvb-q", t.text, l), i ? 3 : 1));
      if (!split) return;
      var row = i ? tileRow(altWord, seed + 7919, l, true) : leadRow;
      if (i) rows.push(row);
      blk.appendChild(enter(row.node, i ? 3 : 2));
      blk.appendChild(row.sr);
    });
    // one word for both languages (or one language): its tiles under the clues
    if (!split) {
      s.appendChild(enter(leadRow.node, 2));
      s.appendChild(leadRow.sr);
    }
    var btn = showAnswerBtn(R, s);
    var answers = {};
    R.langs.forEach(function (l) { var a = R.t(l).answer; if (a) answers[l] = a; });
    var ex = explainBox(R, R.langs.length > 1 ? answers : null);
    s.appendChild(ex.node);
    root.appendChild(s);
    return {
      node: root, ring: ring,
      reveal: function () {
        // each row's tiles slide into their places (FLIP); without motion they simply are there
        rows.forEach(function (row) {
          var before = row.order.map(function (t) { return t.getBoundingClientRect(); });
          row.order.forEach(function (t) { row.node.appendChild(t); });
          row.sr.textContent = row.word;
          if (!calm() && row.order[0] && row.order[0].animate) {
            row.order.forEach(function (t, i) {
              var a = before[i], b = t.getBoundingClientRect();
              var dx = a.left - b.left, dy = a.top - b.top;
              if (dx || dy) t.animate([{ transform: "translate(" + dx + "px," + dy + "px)" }, { transform: "none" }], { duration: 700, easing: "cubic-bezier(.2,.8,.2,1)", delay: i * 40 });
            });
          }
        });
        if (btn) btn.hidden = true;
        ex.show();
      },
    };
  };

  /* ---------- poll: tap to vote, the votes counted on this device as bars ---------- */
  RENDER.poll = function (R) {
    var lead = R.t(R.lead);
    var alt = R.langs.length > 1 ? R.t(R.langs[1]) : null;
    var labels = lead.choices;
    if (!lead.text || labels.length < 2) return null;
    var root = slideRoot(R), s = box(R, false, true);
    s.appendChild(enter(eyebrow(R, "booth.screen.poll", "vote"), 0));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (t.text) blk.appendChild(enter(para(i ? "gvb-txt" : "gvb-q" + (long(t.text, 110) ? " is-long" : ""), t.text, l), i ? 2 : 1));
    });
    var list = el("div", "gvb-poll");
    var rows = labels.map(function (label, i) {
      var b = el("button", "gvb-pollrow");
      b.type = "button";
      b.setAttribute("data-i", String(i));
      if (!R.interactive) { b.disabled = true; b.tabIndex = -1; }
      var bar = attrs(el("span", "gvb-pollbar"), { "aria-hidden": "true" });
      b.appendChild(bar);
      var w = el("span", "gvb-choice-w");
      w.appendChild(setLang(el("span", "gvb-choice-t", label), R.lead));
      if (alt && alt.choices[i] && alt.choices[i] !== label) w.appendChild(setLang(el("span", "gvb-choice-alt", alt.choices[i]), R.langs[1]));
      b.appendChild(w);
      var pct = el("span", "gvb-pollpct", "");
      b.appendChild(pct);
      list.appendChild(enter(b, 2 + i * 0.5));
      return { b: b, bar: bar, pct: pct };
    });
    s.appendChild(list);
    var note = setLang(el("p", "gvb-pollnote"), R.lead);
    s.appendChild(enter(note, 4));
    // a poll's own word after it ("Ask us how each one works"), in each language shown (Both: the second quieter,
    // under the first one's words)
    R.langs.forEach(function (l, i) {
      var t = R.t(l);
      if (!t.explain || (i > 0 && t.explain === lead.explain)) return;
      var ex = setLang(el("p", "gvb-facts" + (i && lead.explain ? " gvb-facts--alt" : "")), l);
      var exs = el("span");
      if (!i || !lead.explain) exs.appendChild(icon("lightbulb"));
      exs.appendChild(document.createTextNode(t.explain));
      ex.appendChild(exs);
      s.appendChild(enter(ex, i ? 5.5 : 5));
    });
    root.appendChild(s);
    var voted = -1;
    var draw = function () {
      var res = pollResultsOf(POLLS, R.item, labels.length);
      rows.forEach(function (r, i) {
        var p = res.total ? res.pcts[i] || 0 : 0;
        r.bar.style.setProperty("--p", p + "%");
        r.pct.textContent = res.total ? p + "%" : "";
      });
      // "Tap an answer to vote", "Thanks for voting! · 3 votes at this table" — in each language shown
      var say = function (l) {
        return voted >= 0 ? S(l, "booth.screen.voted") + " · " + SN(l, "booth.screen.votes", res.total)
          : res.total ? SN(l, "booth.screen.votes", res.total) : R.interactive ? S(l, "booth.screen.votes_none") : "";
      };
      if (say(R.lead)) inLangs(note, R, say); else clear(note);
    };
    draw();
    return {
      node: root,
      vote: function (i) {
        if (voted >= 0 || !(i >= 0 && i < labels.length)) return false;
        voted = i;
        POLLS = tallyOf(POLLS, R.item.id, i);
        savePolls();
        // voted: no more votes (vote() takes one), but the row keeps the focus a visitor's key left on it
        rows.forEach(function (r, j) { if (!r.b.disabled) r.b.setAttribute("aria-disabled", "true"); if (j === i) r.b.classList.add("is-mine"); });
        draw();
        return true;
      },
    };
  };

  /* ---------- pictures: photo (cover, a slow zoom), poster (contain over a blurred copy), a web picture ---------- */
  var ZOOM_FROM = ["50% 50%", "30% 35%", "70% 35%", "35% 70%", "65% 65%"];
  /** The caption over a picture or a video: its title (and the other language's, in Both), its credit line. */
  function caption(R) {
    var lead = R.t(R.lead);
    var text = lead.title || lead.text;
    if (!text) return null;
    var c = setLang(el("p", "gvb-caption"), R.lead);
    c.appendChild(el("span", "", plain(text)));
    if (R.langs.length > 1) {
      var t2 = R.t(R.langs[1]);
      var other = t2.title || t2.text;
      if (other && other !== text) c.appendChild(setLang(el("span", "gvb-caption-alt", plain(other)), R.langs[1]));
    }
    if (lead.credit) c.appendChild(el("span", "gvb-credit", lead.credit));
    return enter(c, 2);
  }
  /** A picture's "media": nothing to play, but a file that fails (or never loads) moves the show on. */
  function imageMedia(R, img) {
    var M = { started: true, failed: false, live: false };
    img.addEventListener("error", function () { M.failed = true; if (M.live) R.E.mediaFailed(R.item, "image"); });
    img.addEventListener("load", function () { img.classList.add("is-loaded"); });
    M.start = function () {
      M.live = true;
      if (M.failed || (img.complete && img.naturalWidth === 0 && img.getAttribute("src"))) R.E.mediaFailed(R.item, "image");
    };
    // (a picture stays as it is while its slide fades out; it goes with the slide)
    M.stop = function () { M.live = false; };
    return M;
  }
  function picture(R, fit) {
    var m = R.item.media;
    if (!m || !m.src) return null;
    var root = slideRoot(R, "gvb-slide--media");
    var wrap = el("div", "gvb-media");
    var lead = R.t(R.lead);
    var img = el("img", "gvb-img " + (fit === "cover" ? "gvb-img--cover" : "gvb-img--contain"));
    img.alt = plain(lead.title || lead.text || "");
    img.decoding = "async";
    if (fit === "cover") {
      var seed = R.item.id.length + (R.E.count || 0);
      img.style.setProperty("--zo", ZOOM_FROM[seed % ZOOM_FROM.length]);
    } else {
      // the blurred copy behind a picture shown whole (no words of its own for screen readers)
      var back = attrs(el("img", "gvb-backimg"), { alt: "", "aria-hidden": "true" });
      back.decoding = "async";
      back.src = m.src;
      wrap.appendChild(back);
    }
    img.src = m.src;
    wrap.appendChild(img);
    root.appendChild(wrap);
    var cap = caption(R);
    if (cap) root.appendChild(cap);
    return { node: root, media: imageMedia(R, img) };
  }
  RENDER.photo = function (R) { return picture(R, "cover"); };
  RENDER.poster = function (R) { return picture(R, "contain"); };
  RENDER.image = function (R) { return picture(R, R.item.media && R.item.media.fit === "cover" ? "cover" : "contain"); };

  /* ---------- video and sound ---------- */
  /** May this slide play sound? The setting, a browser that lets it (someone tapped), and the file's own (muted). */
  function soundOn(R, m) {
    return R.E.mode === "full" && !!SETTINGS.sound && SOUND.unlocked && !(m && m.muted);
  }
  var SOUND = { unlocked: false, blocked: false };
  /** The media started playing: its slide's time counts from now (E.show gave it the 12 s of the start check on
   *  top), so the wait for YouTube or a slow file is not taken from the clip — and a clip shorter than that check
   *  still lets the check run while its slide is on screen. */
  function mediaStarted(R) {
    var c = R.E.cur;
    if (c && c.item === R.item && c.mediaMs) { c.total = elapsed(c) + c.mediaMs; c.mediaMs = 0; }
  }
  /** A file's player (a <video> on the slide, or an Audio): it says when it ends, or fails, to the engine. Not
   *  playing 12 s after it was asked, or stopped for lack of data for 12 s once it played (the venue's Wi-Fi
   *  dropped) → the next slide. A paused show holds it: the checks wait, and Pause pressed while it starts (the
   *  browser's AbortError) is not a failure — Play starts it again. */
  function fileMedia(R, elm, m, isAudio) {
    var M = { started: false, dead: false, timer: 0, stall: 0, onMute: null };
    var fail = function () { if (!M.dead) R.E.mediaFailed(R.item, "file"); };
    var end = function () { if (!M.dead) R.E.mediaEnded(R.item); };
    // (its Sound button follows: mediaButtons)
    var muteNews = function () { if (M.onMute) { try { M.onMute(); } catch (e) { /* its button is gone */ } } };
    var arm = function () {
      clearTimeout(M.timer);
      M.timer = setTimeout(function () {
        if (M.dead || M.started) return;
        if (R.E.paused) { arm(); return; }
        fail();
      }, YT_START_MS);
    };
    // play() refused: the browser wants a tap before sound — a video plays without it (and says "Tap for … sound");
    // a sound with no sound is nothing (the next slide)
    var refused = function (err) {
      if (M.dead || R.E.paused || (err && err.name === "AbortError")) return;
      if (!isAudio && !elm.muted) {
        SOUND.blocked = true;
        elm.muted = true;
        muteNews();
        showTapChip();
        var p2 = null;
        try { p2 = elm.play(); } catch (e) { fail(); return; }
        if (p2 && p2.catch) p2.catch(function (e2) { if (!M.dead && !R.E.paused && !(e2 && e2.name === "AbortError")) fail(); });
      } else if (isAudio) { SOUND.blocked = true; showTapChip(); fail(); }
      else fail();
    };
    elm.preload = "auto";
    elm.addEventListener("loadedmetadata", function () {
      if (m.start && elm.currentTime < m.start - 0.5) { try { elm.currentTime = m.start; } catch (e) { /* not seekable yet */ } }
    });
    elm.addEventListener("playing", function () {
      if (!M.started) mediaStarted(R);
      M.started = true;
      clearTimeout(M.timer);
      clearTimeout(M.stall);
    });
    elm.addEventListener("waiting", function () {
      if (!M.started || M.dead) return;
      clearTimeout(M.stall);
      M.stall = setTimeout(function () { if (!M.dead && !R.E.paused && elm.readyState < 3) fail(); }, STALL_MS);
    });
    elm.addEventListener("ended", end);
    elm.addEventListener("timeupdate", function () { if (m.end && elm.currentTime >= m.end) end(); });
    elm.addEventListener("error", fail);
    M.start = function () {
      elm.muted = !soundOn(R, m);
      muteNews();
      try { elm.volume = Math.max(0, Math.min(1, Number(SETTINGS.volume) || 0.8)); } catch (e) { /* iOS: the device's volume */ }
      elm.src = m.src + (!isAudio && (m.start || m.end) ? "#t=" + (m.start || 0) + (m.end ? "," + m.end : "") : "");
      var p = null;
      try { p = elm.play(); } catch (e) { fail(); return; }
      if (p && p.catch) p.catch(refused);
      arm();
    };
    M.pause = function () { clearTimeout(M.stall); try { elm.pause(); } catch (e) { /* gone */ } };
    M.resume = function () { try { var p = elm.play(); if (p && p.catch) p.catch(refused); } catch (e) { /* gone */ } };
    M.stop = function () {
      M.dead = true;
      clearTimeout(M.timer);
      clearTimeout(M.stall);
      try { elm.pause(); elm.removeAttribute("src"); elm.load(); } catch (e) { /* gone */ }
    };
    M.setMuted = function (mu) { elm.muted = !!mu; muteNews(); };
    M.muted = function () { return !!elm.muted; };
    M.progress = function () {
      var s = m.start || 0, d = m.end || elm.duration;
      if (!isFinite(d) || d <= s) return null;
      return Math.max(0, Math.min(1, (elm.currentTime - s) / (d - s)));
    };
    return M;
  }
  /** The YouTube IFrame Player API (loaded once, on the first YouTube slide; never offline). A load that fails, or
   *  does not answer within 12 s, leaves nothing behind: its <script> goes, the page's onYouTubeIframeAPIReady is
   *  put back as it was, and only this attempt's promise is let go (a newer attempt's stays) — a venue that blocks
   *  YouTube all day does not pile up scripts. A slow load that arrives after all still defines YT.Player, and the
   *  next call uses it. */
  function loadYT() {
    if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
    if (YT.promise) return YT.promise;
    var s = document.createElement("script");
    var prev = window.onYouTubeIframeAPIReady;
    var done = false, timer = 0, settle = null;
    var mine = new Promise(function (resolve, reject) {
      settle = function (ok) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (ok) { resolve(window.YT); return; }
        s.onerror = null;
        if (s.parentNode) s.parentNode.removeChild(s);
        if (window.onYouTubeIframeAPIReady === ready) window.onYouTubeIframeAPIReady = prev;
        if (YT.promise === mine) YT.promise = null;
        reject(new Error("youtube"));
      };
    });
    var ready = function () {
      if (typeof prev === "function") { try { prev(); } catch (e) { /* theirs */ } }
      settle(true);
    };
    YT.promise = mine;
    window.onYouTubeIframeAPIReady = ready;
    s.src = "https://www.youtube.com/iframe_api";
    s.async = true;
    s.onerror = function () { settle(false); };
    document.head.appendChild(s);
    timer = setTimeout(function () { settle(false); }, YT_START_MS);
    return mine;
  }
  /** A YouTube video (privacy-enhanced youtube-nocookie.com): autoplay, muted unless the sound is on, captions as
   *  set, only its part (start / end); it ends → the next slide; an error, or no start within 12 s → skipped (and
   *  YouTube left out for 10 minutes); stopped for lack of data 12 s once it played (the connection dropped) →
   *  skipped, the probe asked at once. A paused show holds it — also one paused while the player still loaded
   *  (autoplay alone would start it). A visitor's tap on the video lands in YouTube's player (the booth hears it as
   *  its window's blur: onWinBlur) and pauses it there: a pause the booth did not ask for plays on (at its end: the
   *  next slide), so YouTube's own pause never holds the screen. Its links stay as YouTube shows them (YouTube's API
   *  policies forbid disabling them). */
  function ytMedia(R, frame, m, title) {
    var M = { started: false, dead: false, player: null, timer: 0, stall: 0, muted: true, extPauses: 0, onMute: null };
    var fail = function (down) {
      if (M.dead) return;
      if (down) { YT.downUntil = now() + YT_DOWN_MS; live(T("booth.yt_down")); }
      R.E.mediaFailed(R.item, "youtube");
    };
    var muteNews = function () { if (M.onMute) { try { M.onMute(); } catch (e) { /* its button is gone */ } } };
    var arm = function () {
      clearTimeout(M.timer);
      M.timer = setTimeout(function () {
        if (M.dead || M.started) return;
        if (R.E.paused) { arm(); return; }
        fail(true);
      }, YT_START_MS);
    };
    M.start = function () {
      M.muted = !soundOn(R, m);
      muteNews();
      arm();
      loadYT().then(function (api) {
        if (M.dead) return;
        var div = el("div");
        div.id = newId("gvb-yt");
        frame.appendChild(div);
        var vars = { autoplay: 1, mute: M.muted ? 1 : 0, controls: 0, playsinline: 1, rel: 0, iv_load_policy: 3, fs: 0, disablekb: 1,
          cc_load_policy: SETTINGS.captions === false ? 0 : 1, cc_lang_pref: R.lead, hl: R.lead, origin: location.origin };
        if (m.start) vars.start = Math.floor(m.start);
        if (m.end) vars.end = Math.ceil(m.end);
        M.player = new api.Player(div.id, {
          host: "https://www.youtube-nocookie.com", videoId: m.id, width: "100%", height: "100%", playerVars: vars,
          events: {
            onReady: function (e) {
              if (M.dead) return;
              try {
                var f = e.target.getIframe();
                if (f) { f.setAttribute("tabindex", "-1"); f.setAttribute("title", title || "YouTube"); }
                if (M.muted) e.target.mute(); else { e.target.unMute(); e.target.setVolume(Math.round((Number(SETTINGS.volume) || 0.8) * 100)); }
                // (a show paused meanwhile stays paused: Play starts it)
                if (R.E.paused) e.target.pauseVideo(); else e.target.playVideo();
              } catch (err) { fail(false); }
            },
            onStateChange: function (e) {
              if (M.dead) return;
              var st = e.data;
              if (st !== 3) clearTimeout(M.stall);
              if (st === 1) {
                if (!M.started) mediaStarted(R);
                M.started = true;
                clearTimeout(M.timer);
                // (autoplay racing a Pause pressed just now)
                if (R.E.paused) { try { e.target.pauseVideo(); } catch (x) { /* gone */ } }
              } else if (st === 0) R.E.mediaEnded(R.item);
              else if (st === 3) {
                if (M.started && !R.E.paused) {
                  probe();
                  clearTimeout(M.stall);
                  M.stall = setTimeout(function () { if (!M.dead && !R.E.paused) fail(false); }, STALL_MS);
                }
              } else if (st === 2 && !R.E.paused && R.E.cur && R.E.cur.media === M) {
                // paused inside the player (a visitor's tap), not by the booth: at its end → the next slide; else it
                // plays on (Pause is the bar's)
                try {
                  if (m.end && e.target.getCurrentTime() >= m.end - 1) { R.E.mediaEnded(R.item); return; }
                  M.extPauses += 1;
                  if (M.extPauses > 3) { R.E.next(); return; }
                  e.target.playVideo();
                } catch (err) { R.E.next(); }
              }
            },
            onError: function () { fail(false); },
          },
        });
      }, function () { fail(true); });
    };
    M.pause = function () { clearTimeout(M.stall); try { if (M.player && M.player.pauseVideo) M.player.pauseVideo(); } catch (e) { /* gone */ } };
    M.resume = function () { try { if (M.player && M.player.playVideo) M.player.playVideo(); } catch (e) { /* gone */ } };
    M.stop = function () {
      M.dead = true;
      clearTimeout(M.timer);
      clearTimeout(M.stall);
      try { if (M.player && M.player.destroy) M.player.destroy(); } catch (e) { /* gone */ }
      M.player = null;
      clear(frame);
    };
    M.setMuted = function (mu) {
      M.muted = !!mu;
      try { if (M.player) { if (mu) M.player.mute(); else { M.player.unMute(); M.player.setVolume(Math.round((Number(SETTINGS.volume) || 0.8) * 100)); } } } catch (e) { /* not ready */ }
      muteNews();
    };
    M.isMuted = function () { return M.muted; };
    M.progress = function () {
      try {
        if (!M.player || !M.player.getCurrentTime) return null;
        var s = m.start || 0, d = m.end || M.player.getDuration();
        if (!d || d <= s) return null;
        var t = M.player.getCurrentTime();
        if (m.end && t >= m.end) R.E.mediaEnded(R.item);
        return Math.max(0, Math.min(1, (t - s) / (d - s)));
      } catch (e) { return null; }
    };
    return M;
  }
  /** Sound / Skip on a video, for a visitor (Sound only when the booth's sound is allowed). Sound is a toggle with
   *  one name: pressed while the video plays with its sound, its icon showing which (a speaker with waves, or
   *  crossed out). The media itself keeps it true (M.onMute): a browser that held the sound back, the first tap
   *  that lets it play, the M key. */
  function mediaButtons(R, root, getMedia) {
    if (!R.interactive || R.E.mode !== "full") return;
    var bar = el("div", "gvb-mediabar");
    if (SETTINGS.sound && !(R.item.media && R.item.media.muted)) {
      var snd = el("button", "gvb-mediabtn");
      snd.type = "button";
      var mutedOf = function (M) { return M.isMuted ? M.isMuted() : M.muted ? M.muted() : true; };
      var draw = function (on) {
        setBtn(snd, S(R.lead, "booth.screen.sound"), on ? "volume-2" : "volume-x", R.lead);
        snd.setAttribute("aria-pressed", on ? "true" : "false");
      };
      draw(soundOn(R, R.item.media));
      var M0 = getMedia();
      if (M0) M0.onMute = function () { draw(!mutedOf(M0)); };
      snd.addEventListener("click", function () {
        var M = getMedia();
        if (!M) return;
        SOUND.unlocked = true;
        M.setMuted(!mutedOf(M));
      });
      bar.appendChild(snd);
    }
    var skip = button("gvb-mediabtn", S(R.lead, "booth.screen.skip"), { icon: "skip-forward", lang: R.lead });
    skip.addEventListener("click", function () { R.E.next({ user: true }); });
    bar.appendChild(skip);
    root.appendChild(bar);
  }
  RENDER.video = function (R) {
    var m = R.item.media;
    if (!m) return null;
    var lead = R.t(R.lead);
    var title = plain(lead.title || lead.text || "");
    var root, M = null;
    if (m.kind === "youtube") {
      if (!m.id || !ytOk()) return null;
      root = slideRoot(R, "gvb-slide--media");
      var frame = el("div", "gvb-yt");
      // the video's own picture while the player loads (YouTube's, from the show's file)
      if (m.poster && /^https:\/\//.test(m.poster)) frame.style.backgroundImage = "url(\"" + m.poster.replace(/["\\]/g, "") + "\")";
      if (m.short) {
        // a Short: upright, in a phone's frame, its title beside it
        var sh = el("div", "gvb-shorts");
        var phone = el("div", "gvb-phone");
        phone.appendChild(frame);
        sh.appendChild(enter(phone, 0));
        var s = box(R);
        s.appendChild(enter(eyebrow(R, "booth.screen.video", "circle-play"), 1));
        perLang(R, s, function (blk, l, i) {
          var t = R.t(l);
          if (t.title) blk.appendChild(enter(setLang(el("p", i ? "gvb-h gvb-h--m" : "gvb-h", t.title), l), i ? 3 : 2));
          if (t.text) blk.appendChild(enter(para("gvb-txt", t.text, l), i ? 3 : 2));
          if (t.credit && i === 0) blk.appendChild(setLang(el("p", "gvb-credit", t.credit), l));
        });
        sh.appendChild(s);
        root.appendChild(sh);
      } else {
        root.appendChild(frame);
        var cap = caption(R);
        if (cap) root.appendChild(cap);
      }
      M = ytMedia(R, frame, m, title);
    } else {
      if (!m.src) return null;
      root = slideRoot(R, "gvb-slide--media");
      var wrap = el("div", "gvb-media");
      var v = el("video", "gvb-video");
      attrs(v, { playsinline: "", "webkit-playsinline": "", "aria-label": title || null, disablepictureinpicture: "" });
      v.playsInline = true;
      if (m.poster) v.poster = m.poster;
      wrap.appendChild(v);
      root.appendChild(wrap);
      var cap2 = caption(R);
      if (cap2) root.appendChild(cap2);
      M = fileMedia(R, v, m, false);
    }
    mediaButtons(R, root, function () { return M; });
    return { node: root, media: M };
  };
  RENDER.audio = function (R) {
    var m = R.item.media;
    if (!m || !m.src || !soundOn(R, m)) return null;
    var root = slideRoot(R), b = el("div", "gvb-audio");
    var art;
    if (m.poster) {
      art = attrs(el("img", "gvb-audio-art"), { alt: "" });
      art.src = m.poster;
      art.addEventListener("error", function () { art.style.visibility = "hidden"; });
    } else {
      art = attrs(el("div", "gvb-audio-art gvb-audio-art--icon"), { "aria-hidden": "true" });
      art.appendChild(icon("headphones"));
    }
    b.appendChild(enter(art, 0));
    var s = box(R);
    s.appendChild(enter(eyebrow(R, "booth.screen.audio", "headphones"), 1));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (t.title) blk.appendChild(enter(setLang(el("p", i ? "gvb-h gvb-h--m" : "gvb-h", t.title), l), i ? 3 : 2));
      if (t.text) blk.appendChild(enter(para("gvb-txt gvb-txt--muted", t.text, l), i ? 3 : 2));
      if (t.credit && i === 0) blk.appendChild(setLang(el("p", "gvb-credit", t.credit), l));
    });
    var bars = attrs(el("div", "gvb-bars"), { "aria-hidden": "true" });
    for (var i = 0; i < 24; i++) { var sp = el("span"); sp.style.setProperty("--i", String(i * 7 % 24)); bars.appendChild(sp); }
    s.appendChild(enter(bars, 3));
    b.appendChild(s);
    root.appendChild(b);
    var audio = new Audio();
    return { node: root, media: fileMedia(R, audio, m, true) };
  };

  /* ---------- the live lists: events, meetings, themes, prices, the book of the month, the countdown ----------
     A list (events, meetings, themes) and the prices fill a screen in one language, so in Both their languages take
     turns on the slide: the first language's part, then — half-way through its time, which Both makes 1.7 times as
     long, as it does a text slide's — the other's in the same place (E.onTick calls half()). Both still shows both
     every time it shows; the eyebrow and the header keep both languages all the while. The countdown has room:
     both languages at once. */
  function liveRowsOf(R, l) {
    var t = R.t(l || R.lead);
    var at = now();
    return t.rows.filter(function (r) { return !(Number(r.ends_ts) && Number(r.ends_ts) < at); });
  }
  /** One row in a language: when (big, in the slide's colour) · title, place and note · a flyer's picture (only
   *  online, or when it is a copy on the site itself). */
  function rowEl(r, R, ico, l) {
    l = l || R.lead;
    var row = el("div", "gvb-row" + (r.when ? "" : " no-when"));
    if (r.pub === "gv" || r.pub === "lv") row.setAttribute("data-pub", r.pub);
    if (r.when) row.appendChild(el("p", "gvb-row-when", fill(r.when, l)));
    var main = el("div", "gvb-row-main");
    main.appendChild(el("p", "gvb-row-title", fill(r.title || "", l)));
    if (r.place || r.note) {
      var sub = el("p", "gvb-row-sub");
      if (r.place) { var pl = el("span"); pl.appendChild(icon(ico || "map-pin")); pl.appendChild(document.createTextNode(fill(r.place, l))); sub.appendChild(pl); }
      if (r.note) sub.appendChild(el("span", "", fill(r.note, l)));
      main.appendChild(sub);
    }
    row.appendChild(main);
    if (r.thumb && (NET.online || sameOrigin(r.thumb))) {
      var th = attrs(el("img", "gvb-row-thumb"), { alt: "" });
      th.decoding = "async";
      th.addEventListener("error", function () { th.remove(); });
      th.src = r.thumb;
      row.appendChild(th);
    }
    return row;
  }
  /** A box with the slide's own small code beside it (when the item has one: in the slide's language — R.lead). */
  function withQr(R, s, i) {
    var qr = slideQr(R);
    if (!qr) return s;
    var wrap = el("div", "gvb-withqr");
    wrap.appendChild(s);
    wrap.appendChild(enter(qr, i));
    return wrap;
  }
  /** A slide made of one language's part at a time: part(l, RL) draws language l's (its box and its code; RL is R
   *  with l first, so its eyebrow leads with l), or null when l has nothing to show. Both → the first language's
   *  part, and the other's hidden until half-way (half()). */
  function langParts(R, part) {
    var first = part(R.lead, R);
    if (!first) return null;
    var root = slideRoot(R);
    root.appendChild(setLang(first, R.lead));
    var l2 = R.langs[1];
    var second = l2 ? part(l2, Object.assign({}, R, { lead: l2, langs: [l2, R.lead] })) : null;
    if (!second) return { node: root };
    second.hidden = true;
    root.appendChild(setLang(second, l2));
    return {
      node: root,
      seconds: Math.round(durationOf(R.item, R.E.eff(), R.lead) * 1.7),
      half: function () {
        first.hidden = true;
        second.hidden = false;
        fitSlide(root);
      },
    };
  }
  function listSlide(R, key, ico, rowIco, max) {
    return langParts(R, function (l, RL) {
      var rows = liveRowsOf(RL, l).slice(0, max || 4);
      if (!rows.length) return null;
      var t = RL.t(l);
      var s = box(RL, false, true);
      s.appendChild(enter(eyebrow(RL, key, ico), 0));
      if (t.title) s.appendChild(enter(setLang(el("p", "gvb-h gvb-h--m", t.title), l), 1));
      var list = el("div", "gvb-rows");
      rows.forEach(function (r, i) { list.appendChild(enter(rowEl(r, RL, rowIco, l), 1.5 + i * 0.6)); });
      s.appendChild(list);
      if (t.text) s.appendChild(enter(para("gvb-txt gvb-txt--muted", t.text, l), 4));
      return withQr(RL, s, 3);
    });
  }
  RENDER.events = function (R) { return listSlide(R, "booth.screen.events", "calendar-days", "map-pin", 4); };
  RENDER.meetings = function (R) { return listSlide(R, "booth.screen.meetings", "users", "map-pin", 4); };
  RENDER.themes = function (R) { return listSlide(R, "booth.screen.themes", "pen-line", "tag", 5); };
  RENDER.prices = function (R) {
    return langParts(R, function (l, RL) {
      var rows = liveRowsOf(RL, l);
      if (!rows.length) return null;
      var t = RL.t(l);
      var s = box(RL, false, true);
      s.appendChild(enter(eyebrow(RL, "booth.screen.prices", "book-open"), 0));
      if (t.title) s.appendChild(enter(setLang(el("p", "gvb-h gvb-h--m", t.title), l), 1));
      var table = el("table", "gvb-table");
      var tb = el("tbody");
      // a row as the show writes it: what (title: "Grapevine · Print · 1 year") · the price (`when`: "$36.00") and
      // under it a change already announced (`note`: "From Jan 1, 2027: $39.00")
      rows.slice(0, 6).forEach(function (r) {
        var tr = el("tr");
        var a = el("td", "", fill(r.title || "", l));
        var b = el("td", "", fill(r.when || "", l));
        if (r.note) b.appendChild(el("span", "gvb-table-note", fill(r.note, l)));
        if (r.place) a.appendChild(el("span", "gvb-table-note", fill(r.place, l)));
        tr.appendChild(a);
        tr.appendChild(b);
        tb.appendChild(tr);
      });
      table.appendChild(tb);
      s.appendChild(enter(table, 2));
      if (t.text) s.appendChild(enter(para("gvb-txt gvb-txt--muted", t.text, l), 3));
      // "As of" the show's day — unless its own words already say it ("Prices as of October 2, 2026 …")
      var asOf = DATA && DATA.as_of && !t.text ? S(l, "booth.screen.as_of", { date: fmtDay(DATA.as_of, l, true) }) : "";
      if (t.credit || asOf) s.appendChild(enter(el("p", "gvb-credit", [t.credit, asOf].filter(Boolean).join(" · ")), 4));
      return withQr(RL, s, 3);
    });
  };
  RENDER.book = function (R) {
    var lead = R.t(R.lead);
    if (!lead.title) return null;
    var root = slideRoot(R), s = box(R);
    // the title the book is sold under (the same in both languages) is in its own language — its store's
    // (eleventy/filters/shop.js STORE_LANG: Grapevine's English, La Viña's Spanish) —, also on a slide in the other
    // language, where the line under it says so ("En inglés · Traducción del título: …")
    var sold = R.t("en").title === R.t("es").title;
    var titleLang = !sold ? null : R.item.pub === "gv" ? "en" : R.item.pub === "lv" ? "es" : null;
    s.appendChild(enter(eyebrow(R, "booth.screen.book", "book-open"), 0));
    perLang(R, s, function (blk, l, i) {
      var t = R.t(l);
      if (t.title && (i === 0 || t.title !== lead.title)) blk.appendChild(enter(setLang(el("p", i ? "gvb-h gvb-h--m" : "gvb-h", t.title), titleLang || l), i ? 3 : 1));
      if (t.text) blk.appendChild(enter(para(i ? "gvb-txt gvb-txt--muted" : "gvb-txt", t.text, l), i ? 3 : 2));
    });
    var facts = liveRowsOf(R);
    // the price line as the show writes it ("$11.99 instead of $14.99, until October 14"), else its rows
    if (lead.explain) {
      var px = setLang(el("p", "gvb-facts"), R.lead);
      var pxs = el("span");
      pxs.appendChild(icon("tag"));
      pxs.appendChild(el("strong", "", lead.explain));
      px.appendChild(pxs);
      s.appendChild(enter(px, 3));
    }
    if (facts.length) {
      var f = el("p", "gvb-facts");
      facts.slice(0, 4).forEach(function (r) {
        var sp = el("span");
        sp.appendChild(icon("tag"));
        if (r.title) sp.appendChild(document.createTextNode(fill(r.title, R.lead) + (r.note ? " " : "")));
        if (r.note) sp.appendChild(el("strong", "", fill(r.note, R.lead)));
        if (r.when) sp.appendChild(document.createTextNode(" · " + fill(r.when, R.lead)));
        f.appendChild(sp);
      });
      s.appendChild(enter(f, 3));
    }
    if (lead.credit) s.appendChild(setLang(el("p", "gvb-credit", lead.credit), R.lead));
    var qr = slideQr(R);
    if (qr) {
      var wrap = el("div", "gvb-withqr");
      wrap.appendChild(s);
      wrap.appendChild(enter(qr, 3));
      root.appendChild(wrap);
    } else root.appendChild(s);
    return { node: root };
  };
  /** The moment a countdown counts to: the assembly's start as the show gives it (its row's starts_ts), else the
   *  moment the item is over (until_ts: the same start). 0 when neither is known. */
  function countdownAt(item, rows) {
    var r0 = rows[0] || {};
    var v = Number(r0.starts_ts) > 0 ? Number(r0.starts_ts) : Number(item.until_ts);
    return v > 0 ? v : 0;
  }
  /** A fact's words in the slide's first language, then (Both, when the other's differ) " · " and the other's,
   *  quieter — into `span`. */
  function factWords(span, first, other, l2) {
    span.appendChild(document.createTextNode(first));
    if (other && other !== first) {
      span.appendChild(attrs(el("span", "gvb-also", " · "), { "aria-hidden": "true" }));
      span.appendChild(setLang(el("span", "gvb-also", other), l2));
    }
    return span;
  }
  /** The countdown to the next assembly: its heading and name (in Both the other language's under a rule, when it
   *  says something else), the days and hours (each word in the languages shown), then when, where and the row's
   *  note — "Details to be confirmed" for a tentative assembly (its date may still change: research.md Open
   *  question 4), "Online on Zoom" for a hybrid one — as the events slide and /events/ give them. */
  RENDER.countdown = function (R) {
    var lead = R.t(R.lead);
    var rows = lead.rows;
    var at = countdownAt(R.item, rows);
    var left = at - now();
    if (!at || left < -12 * 3600e3) return null;
    var l2 = R.langs[1] || "";
    var alt = l2 ? R.t(l2) : null;
    var altRows = alt ? alt.rows : [];
    var root = slideRoot(R), s = box(R, true);
    s.appendChild(enter(eyebrow(R, "booth.screen.countdown", "calendar-days"), 0));
    // the show's words: a heading ("Next assembly") and the event's name; or the name alone
    var name = lead.text || (rows[0] && rows[0].title) || "";
    if (lead.title && name && lead.title !== name) s.appendChild(enter(setLang(el("p", "gvb-h gvb-h--m", lead.title), R.lead), 1));
    if (name || lead.title) s.appendChild(enter(setLang(el("p", "gvb-h", plain(name || lead.title)), R.lead), 1));
    if (alt) {
      var headOf = function (t, rs) {
        var nm = t.text || (rs[0] && rs[0].title) || "";
        return [t.title && nm && t.title !== nm ? t.title : "", plain(nm || t.title)].filter(Boolean).join(" · ");
      };
      var altHead = headOf(alt, altRows);
      if (altHead && altHead !== headOf(lead, rows)) {
        var blk = setLang(el("div", "gvb-alt"), l2);
        blk.appendChild(attrs(el("span", "gvb-langtag", l2.toUpperCase()), { "aria-hidden": "true" }));
        blk.appendChild(setLang(el("p", "gvb-h gvb-h--m", altHead), l2));
        s.appendChild(enter(blk, 1.5));
      }
    }
    var cells = el("div", "gvb-count");
    var cell = function (n, one, many) {
      var c = el("div", "gvb-count-cell");
      c.appendChild(el("span", "gvb-count-n", String(n)));
      var key = n === 1 ? one : many;
      c.appendChild(setLang(el("span", "gvb-count-l", S(R.lead, key)), R.lead));
      if (l2 && S(l2, key) !== S(R.lead, key)) c.appendChild(setLang(el("span", "gvb-count-l gvb-count-l--alt", S(l2, key)), l2));
      return c;
    };
    if (left <= 0) cells.appendChild(inLangs(el("p", "gvb-h gvb-h--xl"), R, function (l) { return S(l, "booth.screen.today"); }));
    else {
      var days = Math.floor(left / 864e5), hours = Math.floor(left % 864e5 / 36e5), mins = Math.floor(left % 36e5 / 6e4);
      if (days >= 1) { cells.appendChild(cell(days, "booth.screen.day", "booth.screen.days")); cells.appendChild(cell(hours, "booth.screen.hour", "booth.screen.hours")); }
      else { cells.appendChild(cell(hours, "booth.screen.hour", "booth.screen.hours")); cells.appendChild(cell(mins, "booth.screen.minute", "booth.screen.minutes")); }
    }
    s.appendChild(enter(cells, 2));
    var r0 = rows[0], a0 = altRows[0] || {};
    if (r0 && (r0.when || r0.place || r0.note)) {
      var sub = el("p", "gvb-facts");
      var fact = function (ico, v, v2) {
        if (!v) return;
        var sp = el("span");
        sp.appendChild(icon(ico));
        sub.appendChild(factWords(sp, fill(v, R.lead), v2 ? fill(v2, l2) : "", l2));
      };
      fact("clock", r0.when, a0.when);
      fact("map-pin", r0.place, a0.place);
      fact("info", r0.note, a0.note);
      s.appendChild(enter(sub, 3));
    }
    root.appendChild(s);
    return { node: root };
  };

  /* ---------- the quiz round's last card ---------- */
  RENDER.score = function (R) {
    var sc = R.score || { n: 0, total: 0 };
    var root = slideRoot(R), s = box(R, true);
    var mark = el("p", "gvb-welcome-mark");
    mark.appendChild(icon(sc.n === sc.total && sc.total ? "party-popper" : "sparkles"));
    s.appendChild(enter(attrs(mark, { "aria-hidden": "true" }), 0));
    s.appendChild(enter(setLang(el("p", "gvb-score", S(R.lead, "booth.screen.score", { n: sc.n, total: sc.total })), R.lead), 1));
    var line = sc.total && sc.n === sc.total ? "booth.screen.score_all" : sc.n * 2 >= sc.total ? "booth.screen.score_good" : "booth.screen.score_some";
    s.appendChild(enter(setLang(el("p", "gvb-h gvb-h--m", S(R.lead, line)), R.lead), 2));
    s.appendChild(enter(setLang(el("p", "gvb-txt gvb-txt--big", S(R.lead, "booth.screen.score_line")), R.lead), 3));
    var acts = el("div", "gvb-actions");
    var again = button("gvb-bigbtn", S(R.lead, "booth.screen.play_again"), { icon: "rotate-ccw", lang: R.lead });
    again.setAttribute("data-gvb-quiz", "again");
    var back = button("gvb-bigbtn gvb-bigbtn--ghost", S(R.lead, "booth.screen.back_to_show"), { icon: "monitor-play", lang: R.lead });
    back.setAttribute("data-gvb-quiz", "end");
    acts.appendChild(again);
    acts.appendChild(back);
    s.appendChild(enter(acts, 4));
    root.appendChild(s);
    return { node: root, seconds: 20 };
  };

  /* ================================================================== 4. the engine (one per screen)
     "full" = the dialog (visitors, keys, sound), "inline" = "Preview here" in the card (taps answer, no sound),
     "card" = the cycling preview (small, silent, no video or sound, slides of 7 s at most). */
  function calm() { return reducedMotion() || SETTINGS.motion === "calm"; }
  /** The player's own slides that apply now (the core's: welcome while an event name is set, about always). */
  function autoItemsOf(settings) { return call("autoItems", [DATA, settings], []); }
  /** The about slide (who shares the display, the site's QR): what shows when nothing else can. */
  function fallbackItem() {
    var about = autoItemsOf(SETTINGS).filter(function (it) { return it.id === "auto:about"; })[0];
    return about || { id: "auto:about", type: "about", pub: "both", langs: ["en", "es"], en: null, es: null, media: null, online: false, qr: null, url: null };
  }
  /** Every item of the show and the player's own two: the Slides list. */
  function allItems(settings) { return DATA ? DATA.items.concat(autoItemsOf(settings)) : []; }
  /** The moment a pool is made for (the core's ctx): now, the Central day, online or not, the page's language, and
   *  what the screen knows — YouTube not answering lately, the items whose file failed (both: "media"). */
  function baseCtx() {
    var failed = {};
    Object.keys(FAILED).forEach(function (id) { if (failedRecently(id)) failed[id] = true; });
    var o = { now: now(), online: NET.online, page: LANG, failed: failed };
    if (!ytOk()) o.youtube = false;
    return call("ctx", [o], o);
  }
  /** The slide's languages: one, or both with the first language first (a missing one is left out). */
  function langsFor(item, mode, settings) {
    if (mode === "both") {
      var first = settings.first === "es" ? "es" : "en", other = first === "es" ? "en" : "es";
      var ls = [first, other].filter(function (l) { return itemHasLang(item, l); });
      return ls.length ? ls : [first, other];
    }
    return [mode === "es" ? "es" : "en"];
  }
  function elapsed(c) { return (c.pausedAt !== null ? c.pausedAt : perf()) - c.t0 - c.pausedTotal; }
  /** A show's starting state: the stored one (its memory of what showed, so a reload does not repeat it) opening
   *  with the `first` items again, or a new one. */
  function freshState(stored) {
    var st = isObj(stored) ? call("normState", [stored], null) : null;
    if (isObj(st)) st.firstQueue = null;
    return isObj(st) ? st : call("newState", [now()], {});
  }
  /** After the settings changed what may show: the next slides open with the `first` items again. */
  function reopen(E) {
    if (E && isObj(E.sched)) E.sched = Object.assign({}, E.sched, { firstQueue: null });
  }
  /** A picture or video shown whole (a poster, a video, YouTube) keeps clear of its caption: how far the caption
   *  reaches up from the slide's bottom (+ a small gap) → --cap-room, which areas/booth.css keeps free under it. */
  function captionRoom(node) {
    var cap = node.querySelector(".gvb-caption");
    if (!cap || !node.querySelector(".gvb-img--contain, .gvb-video, .gvb-yt")) return;
    // (layout boxes, not the entrance animation's moving ones: the caption sits in the slide's own box)
    var room = cap.offsetParent === node ? Math.ceil(node.clientHeight - cap.offsetTop + 10) : 0;
    node.style.setProperty("--cap-room", room > 10 ? room + "px" : "0px");
  }
  /** The slide's box on screen: its first part that is not hidden (a list in Both has a part per language). */
  function shownPart(node) {
    for (var k = node.firstElementChild; k; k = k.nextElementSibling) if (!k.hidden) return k;
    return null;
  }
  /** A Short on an upright screen: its words take at most about 40 % of the height, the phone the rest. One
   *  proportional step of --fit (the words are sized in --f, the phone in --u), worked out from the words' height
   *  at the --fit they have now — so it gives the same answer when it runs again (a resize, the fonts in). On a
   *  wide screen, --fit 1. */
  function fitShort(node) {
    var sh = node.querySelector(".gvb-shorts");
    var txt = sh && sh.querySelector(".gvb-shorts > .gvb-s");
    if (!txt) return;
    var f0 = parseFloat(node.style.getPropertyValue("--fit")) || 1, fit = 1;
    if (node.clientWidth < node.clientHeight && txt.offsetHeight > 0) {
      fit = Math.max(0.6, Math.min(1, Math.floor(0.4 * sh.clientHeight * f0 / txt.offsetHeight * 20) / 20));
    }
    node.style.setProperty("--fit", String(fit));
  }
  /** A long slide shrinks its type until it fits its box: down to `floor` (60 % unless asked — E.show asks 75 % of
   *  a slide in two languages, and shows it in one language when even that is too tall), then, as a last resort,
   *  without its small print (.is-tight: the credit lines, a poll's note — never the question, the right answer or
   *  the explanation). The big QR code shrinks with the type (--fit). An answer slide is fitted to the taller of its
   *  question and its answer (measured with the explanation in and the wrong choices gone: .is-measure-answer), so
   *  nothing jumps when the answer shows. It measures the layout itself: the entrance animation's lift is left out
   *  (.is-fitting), and so are reduced motion's tiny transitions (areas/booth.css), which would hold the old size
   *  until the next frame. → true when it fits. */
  function fitSlide(node, floor) {
    if (!node || !node.isConnected) return true;
    if (node.classList.contains("gvb-slide--media")) { captionRoom(node); fitShort(node); return true; }
    var content = shownPart(node);
    if (!content) return true;
    node.classList.remove("is-tight");
    var cs = getComputedStyle(node);
    var availH = node.clientHeight - (parseFloat(cs.paddingTop) || 0) - (parseFloat(cs.paddingBottom) || 0);
    var availW = node.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
    if (availH <= 0 || availW <= 0) return true;
    floor = floor || 0.6;
    var answerToo = !node.classList.contains("is-revealed") && !!node.querySelector(".gvb-explain.is-waiting");
    var over1 = function () { return content.scrollHeight > availH + 1 || content.scrollWidth > availW + 1; };
    var over = function () {
      if (over1()) return true;
      if (!answerToo) return false;
      node.classList.add("is-measure-answer");
      var o = over1();
      node.classList.remove("is-measure-answer");
      return o;
    };
    node.classList.add("is-fitting");
    var fit = 1;
    node.style.setProperty("--fit", "1");
    for (var i = 0; i < 9 && over() && fit > floor; i++) {
      fit = Math.max(floor, Math.round((fit - 0.05) * 100) / 100);
      node.style.setProperty("--fit", String(fit));
    }
    var fits = !over();
    if (!fits && floor <= 0.6) {
      node.classList.add("is-tight");
      fits = !over();
    }
    node.classList.remove("is-fitting");
    return fits;
  }
  /** After an answer showed (or a vote): the focus a visitor's key left on the slide stays there — on the same
   *  control while it can take it, else on the explanation, the right choice or the slide — never lost to the page
   *  behind the dialog. */
  function keepFocus(c) {
    var a = document.activeElement;
    if (a && a !== document.body && c.node.contains(a) && !a.disabled && !a.closest("[hidden]") && a.offsetParent !== null) return;
    var to = c.node.querySelector(".gvb-explain:not(.is-waiting):not(.is-empty)") || c.node.querySelector(".gvb-choice.is-right") || c.node;
    if (to.tagName !== "BUTTON" && !to.hasAttribute("tabindex")) to.setAttribute("tabindex", "-1");
    try { to.focus({ preventScroll: true }); } catch (e) { /* gone */ }
  }

  function makeEngine(host, mode) {
    var E = {
      mode: mode, host: host, screen: null, stage: null, cur: null, paused: false, history: [], fails: 0, count: 0, sched: null,
      langOverride: null, quiz: null, visitor: false, alive: false, timers: {}, leaving: [], qrKey: "", barKey: "",
    };
    E.interactive = mode !== "card";
    buildScreen(E);

    /** The settings this screen plays with: a visitor's language; no sound in the previews or before a tap. */
    E.eff = function () {
      var patch = null;
      if (E.langOverride) patch = { lang: E.langOverride };
      if (E.mode !== "full" || !SOUND.unlocked) patch = Object.assign(patch || {}, { sound: false });
      return patch ? Object.assign({}, SETTINGS, patch) : SETTINGS;
    };
    E.ctx = function () { return baseCtx(); };
    /** What may show now: the core's pool (its ctx knows what the screen knows — offline, YouTube not answering, the
     *  files that failed lately), less what this screen does not play (the card: no video or sound; "Preview here":
     *  no sound). */
    E.pool = function () {
      if (!DATA) return [];
      return poolOf(DATA, E.eff(), E.ctx()).filter(function (it) {
        if (!RENDER[it.type]) return false;
        if (E.mode === "card" && (it.type === "video" || it.type === "audio")) return false;
        if (E.mode !== "full" && it.type === "audio") return false;
        return true;
      });
    };
    /** The bar's (and the clock's, the corner code's) language: a visitor's choice, else the show's one language,
     *  else the first language. */
    E.barLang = function () {
      var m = E.langOverride || SETTINGS.lang;
      if (m === "en" || m === "es") return m;
      return SETTINGS.first === "es" ? "es" : "en";
    };

    E.start = function () {
      if (E.alive) return;
      E.alive = true;
      E.sched = freshState(E.mode === "full" ? MEMO.sched : null);
      E.applyLook();
      E.timers.tick = setInterval(function () { try { E.onTick(); } catch (e) { /* the watchdog moves on */ } }, TICK_MS);
      E.timers.watch = setInterval(function () { try { E.onWatch(); } catch (e) { /* next round */ } }, 5000);
      E.timers.clock = setInterval(function () { E.renderClock(); }, 10000);
      // the header's and the footer's heights (the slide sits between them), and a slide fitted again when the
      // screen changes size (full screen, Settings beside it, a tablet turned)
      E.measure();
      if (window.ResizeObserver) {
        var raf = 0;
        E.ro = new ResizeObserver(function () {
          if (raf) return;
          raf = requestAnimationFrame(function () { raf = 0; E.measure(); if (E.cur) fitSlide(E.cur.node); });
        });
        E.ro.observe(E.screen);
        E.ro.observe(E.head);
        E.ro.observe(E.foot);
      }
      E.renderClock();
      clear(E.stage);                        // ("Getting the show ready…")
      E.next();
    };
    E.stop = function () {
      E.alive = false;
      Object.keys(E.timers).forEach(function (k) { clearInterval(E.timers[k]); clearTimeout(E.timers[k]); });
      E.timers = {};
      if (E.ro) { E.ro.disconnect(); E.ro = null; }
      if (E.cur) stopSlide(E.cur);
      E.cur = null;
      E.leaving.forEach(function (n) { n.remove(); });
      E.leaving = [];
      if (E.screen) E.screen.remove();
    };

    /** The next slide: the core picks it (or the next question of a quiz round); new content swaps in first. */
    E.next = function (o) {
      o = o || {};
      if (!E.alive) return;
      if (E.quiz) { quizStep(E); return; }
      if (E.mode === "full") swapPending();
      var pool = E.pool();
      var res = nextOf(E.sched, pool, E.eff(), E.ctx());
      E.sched = res.state;
      if (E.mode === "full") { MEMO.sched = E.sched; saveMemo(true); }
      E.show(res.item || fallbackItem(), { user: o.user, record: true });
    };
    /** Back: the slide before (the screen keeps the last 30). */
    E.back = function () {
      if (E.quiz || !E.history.length) return;
      var item = E.history.pop();
      E.show(item, { user: true, record: false });
    };
    /** One slide on the stage (the one before leaves); an item that cannot be drawn is skipped. A slide in two
     *  languages that does not fit at 75 % of its type (a long quiz on a small screen, Large text, the TV's safe
     *  margin) shows in one language instead, the other leading its next showing (E.solo) — nothing is cut off and
     *  nothing shrinks out of reading from 3 m. */
    E.show = function (item, o) {
      o = o || {};
      if (!E.alive || !item) return;
      var eff = E.eff();
      var lmode = E.quiz && !o.score ? E.quiz.lang : langOf(item, eff, E.sched);
      var langs = E.quiz && !o.score ? [E.quiz.lang] : langsFor(item, lmode, eff);
      var cache = {};
      var wordsOf = function (l) { return cache[l] || (cache[l] = words(item, l)); };
      var makeR = function (ls) {
        return {
          item: item, type: item.type, langs: ls, lead: ls[0], E: E, score: o.score || null, round: E.quiz,
          interactive: E.interactive && (E.mode !== "full" || SETTINGS.visitor !== false || !!E.quiz), t: wordsOf,
        };
      };
      var draw = function (R1) { try { return RENDER[item.type] ? RENDER[item.type](R1) : null; } catch (err) { return null; } };
      var R = makeR(langs);
      var built = draw(R);
      if (!built || !built.node) {
        E.fails += 1;
        if (item.id && item.id !== "auto:about") FAILED[item.id] = now();
        clearTimeout(E.timers.skip);
        // the slide on screen waits for the next one (the ticker does not ask again meanwhile)
        if (E.cur) E.cur.total = Math.max(E.cur.total, elapsed(E.cur) + 2000);
        if (E.fails > 6 && item.id !== "auto:about") { E.fails = 0; E.show(fallbackItem(), o); return; }
        // (even the "about" slide failed: try again in a while, never in a tight loop)
        E.timers.skip = setTimeout(function () { E.next(); }, item.id === "auto:about" ? 5000 : 40);
        return;
      }
      E.fails = 0;
      var old = E.cur;
      if (old) {
        stopSlide(old);
        if (o.record && !E.quiz && old.item && old.item.type !== "score") {
          E.history.push(old.item);
          if (E.history.length > 30) E.history.shift();
        }
        var gone = old.node;
        gone.classList.remove("is-in");
        gone.classList.add("is-out");
        attrs(gone, { "aria-hidden": "true" });
        gone.inert = true;
        E.leaving.push(gone);
        setTimeout(function () { gone.remove(); E.leaving = E.leaving.filter(function (n) { return n !== gone; }); }, calm() ? 0 : 650);
      }
      // never more than the slide leaving and the one coming
      while (E.leaving.length > 1) E.leaving.shift().remove();
      // a slide is a named group ("slide" in its language, its title or first words as the name)
      var prep = function (n, R1) {
        var tw = R1.t(R1.lead);
        var name = plain(tw.title || tw.text || "") || (SCREEN.en && SCREEN.en["booth.screen." + item.type] ? S(R1.lead, "booth.screen." + item.type) : "");
        if (name) attrs(n, { role: "group", "aria-roledescription": S(R1.lead, "booth.screen.slide"), "aria-label": short(name, 90) });
        if (!calm()) n.classList.add("is-in");
      };
      var node = built.node;
      prep(node, R);
      E.stage.appendChild(node);
      // (a list in Both shows one language at a time: it never needs the two languages' floor; nor does a slide shown
      // while Settings narrow the show — "Show now" — which fits itself again when they close)
      var two = R.langs.length > 1 && !built.half && !(E.mode === "full" && P.drawer);
      if (!fitSlide(node, two ? 0.75 : 0.6) && two) {
        var solo = E.solo || (E.solo = {});
        var last = langs.indexOf(solo[item.id]) >= 0 ? solo[item.id] : "";
        // its languages take turns from one showing to the next (Back and a redraw keep the one it had)
        var one = o.record === false && last ? last : last === langs[0] ? langs[1] : langs[0];
        solo[item.id] = one;
        var R1 = makeR([one]);
        var b1 = draw(R1);
        if (b1 && b1.node) {
          prep(b1.node, R1);
          E.stage.replaceChild(b1.node, node);
          node = b1.node;
          built = b1;
          R = R1;
          langs = [one];
          lmode = one;
          fitSlide(node);
        }
      }
      var total = built.seconds || durationOf(item, eff, lmode);
      var rv = built.reveal ? revealOf(item, eff, lmode) : 0;
      if (E.mode === "card") { total = Math.min(total, 7); rv = rv ? Math.min(rv, 4) : 0; }
      // a round's question waits for the visitor: no answer timer (a tap on a choice, "Show the answer" or the bar's
      // Next shows the answer; the idle time ends a round left half-way)
      if (E.quiz && !o.score) { total = 3600; rv = 0; }
      // a video or a sound: the 12 s its start may take come on top (its own time counts from when it plays)
      var waitMs = (item.type === "video" || item.type === "audio") && built.media && built.media.start ? YT_START_MS : 0;
      node.style.setProperty("--zd", Math.round(total + 2) + "s");
      E.cur = {
        item: item, R: R, built: built, node: node, langs: langs, lmode: lmode, total: total * 1000 + waitMs, mediaMs: waitMs ? total * 1000 : 0,
        revealAt: rv * 1000, revealed: false, answered: false, halved: false, done: false, t0: perf(), pausedTotal: 0,
        pausedAt: E.paused ? perf() : null, media: built.media || null, pending: false,
      };
      E.count += 1;
      E.renderChrome();
      E.setProgress(0);
      // (a round's question: no ring — it waits)
      if (built.ring) { if (rv) built.ring.set(0, rv); else built.ring.node.hidden = true; }
      if (E.cur.media && E.cur.media.start) {
        if (E.paused) E.cur.pending = true;
        else {
          try { E.cur.media.start(); } catch (err) { E.mediaFailed(item, "start"); return; }
        }
      }
      if (o.user) sayItem(E, E.cur);
    };
    E.rerender = function () {
      var c = E.cur;
      if (!c || E.quiz) return;
      // a video or a sound goes on as it is (a new language is for the next slide)
      if (c.item.type === "video" || c.item.type === "audio") { E.renderChrome(); return; }
      var inPool = E.pool().some(function (it) { return it.id === c.item.id; }) || /^auto:/.test(c.item.id);
      if (inPool) E.show(c.item, { record: false });
      else E.next();
    };

    /* ---------- time ---------- */
    E.onTick = function () {
      var c = E.cur;
      if (!c || E.paused || !E.alive) return;
      var t = elapsed(c);
      if (c.revealAt && !c.revealed) {
        if (t >= c.revealAt) E.reveal();
        else if (c.built.ring) c.built.ring.set(t / c.revealAt, (c.revealAt - t) / 1000);
      }
      var frac = null;
      if (c.media && c.media.progress) frac = c.media.progress();
      if (frac === null || frac === undefined) frac = Math.min(1, t / c.total);
      E.setProgress(frac);
      // a list in Both: the other language's part half-way through
      if (c.built.half && !c.halved && t >= c.total / 2) { c.halved = true; try { c.built.half(); } catch (e) { /* the first part stays */ } }
      if (t >= c.total) E.next();
    };
    E.onWatch = function () {
      if (!E.alive || E.paused) return;
      if (!E.cur || !E.cur.node.isConnected) { E.next(); return; }
      if (elapsed(E.cur) > E.cur.total + WATCHDOG_SLACK) E.next();
    };
    E.measure = function () {
      var h = E.head.offsetHeight, f = E.foot.offsetHeight;
      if (h) E.screen.style.setProperty("--head-h", h + "px");
      if (f) E.screen.style.setProperty("--foot-h", f + "px");
      if (E.bar && E.bar.offsetHeight) E.screen.style.setProperty("--bar-h", E.bar.offsetHeight + "px");
    };
    E.setProgress = function (f) {
      if (E.progressBar) E.progressBar.style.transform = "scaleX(" + Math.max(0, Math.min(1, f)).toFixed(4) + ")";
    };
    /** More time for this slide (a visitor is reading it): at least `ms` from now. */
    E.extend = function (ms) {
      var c = E.cur;
      if (c) c.total = Math.max(c.total, elapsed(c) + ms);
    };
    E.pause = function () {
      if (E.paused) return;
      E.paused = true;
      var c = E.cur;
      if (c) {
        c.pausedAt = perf();
        if (c.media && c.media.pause) c.media.pause();
      }
      E.screen.classList.add("is-paused");
      E.renderChrome();
    };
    E.resume = function () {
      if (!E.paused) return;
      E.paused = false;
      var c = E.cur;
      E.screen.classList.remove("is-paused");
      if (c) {
        if (c.pausedAt !== null) { c.pausedTotal += perf() - c.pausedAt; c.pausedAt = null; }
        // its video or sound ended (or failed) while the show was paused: the next slide, now
        if (c.done) { E.renderChrome(); E.next(); return; }
        if (c.pending) { c.pending = false; try { c.media.start(); } catch (e) { E.mediaFailed(c.item, "start"); } }
        else if (c.media && c.media.resume) c.media.resume();
      }
      E.renderChrome();
    };
    E.togglePause = function () {
      if (E.paused) E.resume(); else E.pause();
      // (what happened, said as a state: "Paused" — the button itself reads Play then)
      live(S(E.barLang(), E.paused ? "booth.screen.paused" : "booth.screen.play"));
    };

    /* ---------- answers ---------- */
    E.reveal = function () {
      var c = E.cur;
      if (!c || c.revealed || !c.built.reveal) return;
      c.revealed = true;
      // (a visitor's key on the slide — a choice, "Show the answer", the bar's Next: the focus stays in the dialog)
      var hadFocus = c.node.contains(document.activeElement);
      c.node.classList.add("is-revealed");
      try { c.built.reveal(); } catch (e) { /* the slide goes on as it is */ }
      fitSlide(c.node);
      if (E.quiz) {
        if (!c.answered && (c.item.type === "quiz" || c.item.type === "truefalse")) { c.answered = true; E.quiz.results.push(false); }
        quizAfterReveal(E, c, hadFocus);
        renderRound(E);
        fitSlide(c.node);
      } else {
        // the time for the answer: what the slide had after its reveal (at least 8 s), counted from now
        var after = Math.max(8000, c.total - (c.revealAt || 0));
        if (E.mode === "card") after = Math.min(after, 4000);
        c.total = elapsed(c) + after;
        if (hadFocus) keepFocus(c);
      }
    };
    E.answer = function (i) {
      var c = E.cur;
      if (!c || c.answered || c.revealed || !c.built.answer) return;
      var right = c.built.answer(i);
      if (right === null || right === undefined) return;
      c.answered = true;
      if (E.quiz) { E.quiz.results.push(!!right); if (right) E.quiz.score += 1; }
      E.reveal();
      if (right && E.mode !== "card" && !calm()) confetti(E);
      live(S(c.R.lead, right ? "booth.screen.right" : "booth.screen.wrong"));
    };
    E.vote = function (i) {
      var c = E.cur;
      if (!c || !c.built.vote) return;
      if (c.built.vote(i)) {
        E.extend(7000);
        live(S(c.R.lead, "booth.screen.voted"));
      }
    };

    /* ---------- media ---------- */
    // (one that ends — or fails — while the show is paused waits for Play: its slide is marked done, E.resume)
    E.mediaEnded = function (item) {
      if (!E.cur || E.cur.item !== item || !E.alive) return;
      if (E.paused) { E.cur.done = true; return; }
      E.next();
    };
    E.mediaFailed = function (item, kind) {
      if (!E.cur || E.cur.item !== item || !E.alive) return;
      if (item.id) FAILED[item.id] = now();
      if (item.online || kind === "youtube") probe();
      if (E.paused) { E.cur.done = true; return; }
      E.next();
    };

    /* ---------- a visitor's language, the look ---------- */
    E.setLang = function (l) {
      if (E.langOverride === l) return;
      E.langOverride = l;
      E.renderBar();
      E.rerender();
    };
    E.applyLook = function () {
      var sc = E.screen;
      attrs(sc, {
        "data-gvb-theme": SETTINGS.theme === "daylight" ? "daylight" : "dark",
        "data-gvb-text": SETTINGS.textSize === "large" ? "large" : "normal",
        "data-gvb-motion": SETTINGS.motion === "calm" ? "calm" : "full",
        "data-gvb-overscan": E.mode === "full" && SETTINGS.overscan ? "1" : null,
      });
      if (E.clockEl) E.clockEl.hidden = SETTINGS.clock === false;
      if (E.progressWrap) E.progressWrap.hidden = SETTINGS.progress === false;
      E.qrKey = "";
      E.renderChrome();
    };
    E.renderClock = function () {
      if (!E.clockEl || E.clockEl.hidden) return;
      var l = E.barLang();
      try { E.clockEl.textContent = new Date().toLocaleTimeString(locale(l), { hour: "numeric", minute: "2-digit" }); } catch (e) { E.clockEl.textContent = ""; }
      setLang(E.clockEl, l);
    };
    /** Everything around the slide: the header, the colours, the language chip, the hint, the corner code, the bar. */
    E.renderChrome = function () {
      var c = E.cur;
      var lead = c ? c.langs[0] : E.barLang();
      var langs = c ? c.langs : [lead];
      E.screen.setAttribute("data-pub", c ? pubOf(c.item) : "both");
      E.screen.classList.toggle("is-media", !!(c && c.node.classList.contains("gvb-slide--media")));
      E.bg.setAttribute("data-pub", c ? pubOf(c.item) : "both");
      // the event's name in the slide's language (and the other one, in Both); else "Grapevine · La Viña"
      var ev = SETTINGS.event || {};
      var nameIn = function (l) { return l === "es" ? (ev.es || ev.en || "") : (ev.en || ev.es || ""); };
      var show = ev.show !== false;
      var name = show ? nameIn(lead) : "";
      E.evName.textContent = name || S(lead, "booth.screen.both");
      setLang(E.evName, lead);
      var alt = show && langs[1] ? nameIn(langs[1]) : "";
      E.evAlt.textContent = alt && alt !== name ? alt : "";
      E.evAlt.hidden = !E.evAlt.textContent;
      if (langs[1]) setLang(E.evAlt, langs[1]);
      var site = siteInfo();
      var sub = show ? String(ev.sub || "") : "";
      if (!name && !sub) sub = lead === "es" ? site.committee_es : site.committee_en;
      E.evSub.textContent = sub;
      E.evSub.hidden = !sub;
      // the language chip
      var m = E.langOverride || SETTINGS.lang || "both";
      var f = SETTINGS.first === "es" ? ["ES", "EN"] : ["EN", "ES"];
      var chip = m === "en" ? "EN" : m === "es" ? "ES" : m === "both" ? f.join(" · ") : f.join(" ⇄ ");
      if (E.langChipText.textContent !== chip) E.langChipText.textContent = chip;
      E.langChip.setAttribute("aria-label", S(E.barLang(), "booth.screen.lang") + ": " + chip);
      if (E.pauseChip) {
        E.pauseChip.hidden = !E.paused;
        E.pauseChipText.textContent = S(E.barLang(), "booth.screen.paused");
        setLang(E.pauseChip, E.barLang());
      }
      // "Tap to play" in the slide's language(s), while visitors may play and the bar is down
      if (E.hint) {
        var hint = E.mode === "full" && SETTINGS.visitor !== false && !E.quiz;
        E.hint.hidden = !hint;
        if (hint) {
          clear(E.hintText);
          E.hintText.appendChild(setLang(el("span", "", S(lead, "booth.screen.tap_play")), lead));
          if (langs[1]) {
            E.hintText.appendChild(document.createTextNode(" · "));
            E.hintText.appendChild(setLang(el("span", "gvb-hint-alt", S(langs[1], "booth.screen.tap_play")), langs[1]));
          }
        }
      }
      // the site's code in the corner (in the bar's language)
      var ql = E.barLang();
      var key = ql + "|" + (SETTINGS.qrCorner === false ? 0 : 1) + "|" + (DATA ? DATA.version || 1 : 0);
      if (E.qrc && key !== E.qrKey) {
        E.qrKey = key;
        clear(E.qrc);
        var img = SETTINGS.qrCorner === false ? null : qrImg(siteUrl(ql), "QR: " + site.host, "gvb-qrc-img");
        if (img) {
          E.qrc.appendChild(img);
          // "neta65.github.io" over "/aagrapevine": the address breaks where it reads well
          var hostP = el("p", "gvb-qrc-host");
          var cut = site.host.indexOf("/");
          if (cut > 0) { hostP.appendChild(el("span", "", site.host.slice(0, cut))); hostP.appendChild(el("span", "", site.host.slice(cut))); }
          else hostP.textContent = site.host;
          E.qrc.appendChild(hostP);
        }
        E.qrc.hidden = !img;
      }
      E.renderBar();
      if (E.round) renderRound(E);
      E.renderClock();
    };
    E.renderBar = function () { if (E.mode === "full") renderBar(E); };
    return E;
  }
  function stopSlide(c) {
    if (c.media && c.media.stop) { try { c.media.stop(); } catch (e) { /* gone */ } }
    c.media = null;
  }
  /** What a visitor's Back / Next brought up, said once (the show playing by itself is not read out). */
  function sayItem(E, c) {
    if (E.mode !== "full") return;
    var t = c.R.t(c.R.lead);
    var text = plain(t.title || t.text || "");
    if (text) live(short(text, 160));
  }

  /* ------------------------------------------------------------------ the screen's parts */
  function buildScreen(E) {
    var sc = el("div", "gvb-screen" + (E.mode === "full" ? "" : " gvb-screen--pv"));
    E.screen = sc;
    E.bg = attrs(el("div", "gvb-bg"), { "aria-hidden": "true" });
    sc.appendChild(E.bg);
    var head = el("div", "gvb-head");
    E.head = head;
    var ev = el("div", "gvb-event");
    if (E.mode === "full") ev.setAttribute("data-gvb-hold", "");
    E.evName = el("p", "gvb-event-name");
    E.evAlt = el("p", "gvb-event-alt");
    E.evSub = el("p", "gvb-event-sub");
    ev.appendChild(E.evName);
    ev.appendChild(E.evAlt);
    ev.appendChild(E.evSub);
    ev.appendChild(attrs(el("span", "gvb-holdbar"), { "aria-hidden": "true" }));
    head.appendChild(ev);
    var meta = el("div", "gvb-meta");
    if (E.mode === "full") {
      E.saveChip = el("span", "gvb-langchip gvb-statuschip");
      E.saveChip.hidden = true;
      meta.appendChild(E.saveChip);
      E.pauseChip = el("span", "gvb-pausechip");
      E.pauseChip.appendChild(icon("pause"));
      E.pauseChipText = el("span");
      E.pauseChip.appendChild(E.pauseChipText);
      E.pauseChip.hidden = true;
      meta.appendChild(E.pauseChip);
    }
    E.clockEl = el("p", "gvb-clock");
    meta.appendChild(E.clockEl);
    E.langChip = el("p", "gvb-langchip");
    E.langChip.appendChild(icon("languages"));
    E.langChipText = el("span");
    E.langChip.appendChild(E.langChipText);
    meta.appendChild(E.langChip);
    head.appendChild(meta);
    sc.appendChild(head);
    E.stage = el("div", "gvb-stage");
    sc.appendChild(E.stage);
    var foot = el("div", "gvb-foot");
    E.foot = foot;
    if (E.mode === "full") {
      E.hint = el("p", "gvb-hint");
      E.hint.appendChild(icon("hand"));
      E.hintText = el("span");
      E.hint.appendChild(E.hintText);
      foot.appendChild(E.hint);
    }
    E.qrc = el("div", "gvb-qrc");
    foot.appendChild(E.qrc);
    E.progressWrap = attrs(el("span", "gvb-progress"), { "aria-hidden": "true" });
    E.progressBar = el("span");
    E.progressWrap.appendChild(E.progressBar);
    foot.appendChild(E.progressWrap);
    sc.appendChild(foot);
    if (E.mode === "full") {
      sc.appendChild(buildBar(E));
      E.round = el("div", "gvb-round");
      E.round.hidden = true;
      sc.appendChild(E.round);
    }
    E.host.appendChild(sc);
  }
  function setStatusChip(E, text) {
    if (!E || !E.saveChip) return;
    E.saveChip.textContent = text || "";
    E.saveChip.hidden = !text;
  }
  function showLoading(E, failed, retry) {
    clear(E.stage);
    var slide = el("section", "gvb-slide is-shown");
    var s = el("div", "gvb-s gvb-s--center");
    s.appendChild(el("p", failed ? "gvb-txt" : "gvb-txt gvb-txt--muted", T(failed ? "booth.load_failed" : "booth.loading")));
    if (failed && retry) {
      var b = button("gvb-bigbtn", T("booth.retry"), { icon: "rotate-ccw" });
      b.addEventListener("click", retry);
      s.appendChild(b);
    }
    slide.appendChild(s);
    E.stage.appendChild(slide);
    E.renderChrome();
    return slide;
  }

  /* ------------------------------------------------------------------ confetti (a right answer) */
  function confetti(E) {
    var box = attrs(el("div", "gvb-confetti"), { "aria-hidden": "true" });
    var colors = ["#ffd79a", "#8cc4f4", "#f9ad75", "#cfa8f0", "#7bd88f", "#ffffff"];
    for (var i = 0; i < 42; i++) {
      var s = el("span");
      s.style.left = (Math.random() * 100).toFixed(1) + "%";
      s.style.setProperty("--c", colors[i % colors.length]);
      s.style.setProperty("--x", ((Math.random() - 0.5) * 30).toFixed(1) + "cqw");
      s.style.setProperty("--r", Math.round(360 + Math.random() * 720) + "deg");
      s.style.setProperty("--d", (1.8 + Math.random() * 1.4).toFixed(2) + "s");
      s.style.setProperty("--w", (Math.random() * 0.4).toFixed(2) + "s");
      box.appendChild(s);
    }
    E.screen.appendChild(box);
    setTimeout(function () { box.remove(); }, 4000);
  }

  /* ================================================================== 5. visitors: the bar, "Take it home", the quiz
     round. The bar's words follow the show's language (a visitor's choice, else the show's one language, else the
     first language), not the page's. */
  function buildBar(E) {
    // a group of plain buttons, each its own Tab stop — not a toolbar: ← → stay the show's keys (an operator's, a
    // presenter remote's), also while a bar button keeps the focus after a tap
    var bar = attrs(el("div", "gvb-bar"), { role: "group" });
    E.vb = {};
    var add = function (parent, name, cls) {
      var b = el("button", "gvb-vb" + (cls ? " " + cls : ""));
      b.type = "button";
      b.setAttribute("data-gvb-v", name);
      parent.appendChild(b);
      E.vb[name] = b;
      return b;
    };
    add(bar, "back");
    add(bar, "pause");
    add(bar, "next");
    bar.appendChild(attrs(el("span", "gvb-vsep"), { "aria-hidden": "true" }));
    add(bar, "quiz", "gvb-vb--accent");
    var grp = attrs(el("div", "gvb-vgroup"), { role: "group" });
    E.vb.group = grp;
    ["en", "es", "both"].forEach(function (l) { add(grp, "lang-" + l).setAttribute("aria-pressed", "false"); });
    bar.appendChild(grp);
    add(bar, "take");
    E.bar = bar;
    return bar;
  }
  function setBtn(b, text, ico, l) {
    clear(b);
    if (ico) b.appendChild(icon(ico));
    var sp = el("span", "", text);
    if (l) sp.setAttribute("lang", l);
    b.appendChild(sp);
    return b;
  }
  function renderBar(E) {
    if (!E.bar) return;
    var l = E.barLang();
    var key = [l, E.paused ? 1 : 0, E.langOverride || "", SETTINGS.lang, SETTINGS.first, E.history.length ? 1 : 0, E.quiz ? 1 : 0].join("|");
    if (key === E.barKey) return;
    E.barKey = key;
    // (the button keeping the focus is redrawn in place: its words change, the focus stays on it)
    setLang(E.bar, l);
    E.bar.setAttribute("aria-label", S(l, "booth.screen.controls"));
    setBtn(E.vb.back, S(l, "booth.screen.back"), "chevron-left");
    E.vb.back.disabled = !E.history.length || !!E.quiz;
    // (its words say what a tap does — Pause, or Play while paused —, so no pressed state that would read "Play,
    // pressed" while the show stands still)
    setBtn(E.vb.pause, S(l, E.paused ? "booth.screen.play" : "booth.screen.pause"), E.paused ? "play" : "pause");
    setBtn(E.vb.next, S(l, "booth.screen.next"), "chevron-right");
    setBtn(E.vb.quiz, S(l, "booth.screen.quiz_me"), "party-popper");
    E.vb.group.setAttribute("aria-label", S(l, "booth.screen.lang"));
    setBtn(E.vb["lang-en"], S("en", "booth.screen.lang_en"), "", "en");
    setBtn(E.vb["lang-es"], S("es", "booth.screen.lang_es"), "", "es");
    setBtn(E.vb["lang-both"], S(l, "booth.screen.lang_both"), "languages");
    var m = E.langOverride || SETTINGS.lang;
    ["en", "es", "both"].forEach(function (x) { E.vb["lang-" + x].setAttribute("aria-pressed", m === x ? "true" : "false"); });
    setBtn(E.vb.take, S(l, "booth.screen.take_home"), "qr-code");
  }
  function barAction(E, name) {
    if (name === "back") E.back();
    else if (name === "pause") E.togglePause();
    else if (name === "next") { if (E.quiz && E.cur && E.cur.item.type !== "score" && !E.cur.revealed) E.reveal(); else E.next({ user: true }); }
    else if (name === "quiz") startQuiz(E);
    else if (name === "take") openTake(E);
    else if (/^lang-/.test(name)) {
      var l = name.slice(5);
      E.setLang(l);
      var said = l === "en" ? S("en", "booth.screen.lang_en") : l === "es" ? S("es", "booth.screen.lang_es") : S(E.barLang(), "booth.screen.lang_both");
      live(S(l === "both" ? E.barLang() : l, "booth.screen.lang") + ": " + said);
    }
  }
  /** Any tap or key from a visitor: the bar comes up (while visitors may play), the idle countdown starts again. */
  function visitorTouch(E) {
    if (!E || E.mode !== "full" || !E.alive) return;
    if (SETTINGS.visitor === false && !E.quiz) return;
    if (!E.visitor) {
      E.visitor = true;
      E.screen.classList.add("is-visitor");
      E.renderChrome();
      E.measure();
      if (E.cur) fitSlide(E.cur.node);          // (the slide keeps clear of the bar)
    }
    clearTimeout(E.timers.idle);
    E.timers.idle = setTimeout(function () { visitorIdle(E); }, Math.max(10, Number(SETTINGS.idleSeconds) || 40) * 1000);
  }
  /** Nobody touched it for a while: the bar goes, a visitor's language is undone, the show goes on by itself. While
   *  the PIN or "Leave?" box is up it waits (that box closes by itself: armPrompt). Settings left alone close after
   *  the longer of 2 minutes and 3 idle times — what an operator does in them counts (P.drawerUsed) — so a drawer a
   *  visitor opened (a 3-second hold, the S key) never covers the show all day. */
  function visitorIdle(E) {
    if (!E.alive) return;
    if (P.modal) { E.timers.idle = setTimeout(function () { visitorIdle(E); }, 10000); return; }
    if (P.drawer) {
      var left = Math.max(120, 3 * (Number(SETTINGS.idleSeconds) || 40)) * 1000 - (now() - (P.drawerUsed || 0));
      if (left > 0) { E.timers.idle = setTimeout(function () { visitorIdle(E); }, Math.min(10000, left + 50)); return; }
      closeDrawer();
    }
    var hadFocus = E.screen.contains(document.activeElement);
    E.visitor = false;
    E.screen.classList.remove("is-visitor");
    closeTake(E, false);
    var wasQuiz = !!E.quiz, hadLang = !!E.langOverride;
    E.langOverride = null;
    if (E.paused) E.resume();
    // a round left half-way ends (its question waits for nobody now): the show's next slide, in its own language
    if (wasQuiz) endQuiz(E);
    else if (hadLang) { E.renderBar(); E.rerender(); }
    E.renderChrome();
    if (E.cur) fitSlide(E.cur.node);
    if (hadFocus && P.root) P.root.focus({ preventScroll: true });
  }

  /* ---------- "Take it home": the site's code and the slide's own, big ---------- */
  function openTake(E) {
    closeTake(E, false);
    var l = E.barLang();
    var site = siteInfo();
    var panel = attrs(el("div", "gvb-take"), { role: "dialog", "aria-modal": "true", lang: l });
    var b = el("div", "gvb-take-box");
    var h = el("p", "gvb-take-h", S(l, "booth.screen.take_home"));
    h.id = newId("gvb-take-h");
    panel.setAttribute("aria-labelledby", h.id);
    b.appendChild(h);
    b.appendChild(el("p", "gvb-take-text", S(l, "booth.screen.take_home_text")));
    var codes = el("div", "gvb-take-codes");
    var code = function (url, label) {
      var img = qrImg(url, "QR: " + hostOf(url));
      if (!img) return;
      var f = el("figure", "gvb-take-code");
      f.appendChild(img);
      var cap = el("figcaption", "", label);
      cap.appendChild(el("span", "gvb-take-url", hostOf(url)));
      f.appendChild(cap);
      codes.appendChild(f);
    };
    code(siteUrl(l), S(l, "booth.screen.take_site"));
    var it = E.cur && E.cur.item;
    var own = it && (qrFor(it, l) || it.url);
    if (own && own !== siteUrl(l) && own !== site.url && own !== site.url_es) code(own, S(l, "booth.screen.take_slide"));
    b.appendChild(codes);
    var x = button("gvb-take-close", "", { icon: "x", aria: S(l, "booth.screen.close") });
    x.setAttribute("data-gvb-take-close", "");
    b.appendChild(x);
    panel.appendChild(b);
    E.take = { panel: panel, from: document.activeElement, inerted: [] };
    E.screen.appendChild(panel);
    // the rest of the screen out of reach while it is open (a modal panel for screen readers and Tab alike)
    Array.prototype.forEach.call(E.screen.children, function (n) { if (n !== panel && !n.inert) { n.inert = true; E.take.inerted.push(n); } });
    E.extend(30000);
    x.focus({ preventScroll: true });
  }
  function closeTake(E, focusBack) {
    if (!E || !E.take) return;
    var from = E.take.from;
    E.take.inerted.forEach(function (n) { n.inert = false; });
    E.take.panel.remove();
    E.take = null;
    if (focusBack) {
      if (from && from.isConnected && from.focus) from.focus({ preventScroll: true });
      else if (P.root) P.root.focus({ preventScroll: true });
    }
  }

  /* ---------- "Quiz me": a round of questions in one language, a score, a friendly last card ---------- */
  function startQuiz(E) {
    if (!E.alive || !DATA) return;
    var l = E.barLang();
    var n = Math.max(1, Math.min(10, Number(SETTINGS.quizLength) || 5));
    var items = quizRoundOf(E.pool(), l, n, rng((now() % 2147483647) >>> 0));
    if (!items.length) { flash(E, S(l, "booth.screen.no_quiz"), l); return; }
    closeTake(E, false);
    E.quiz = { items: items, i: 0, score: 0, lang: l, results: [], done: false };
    if (E.paused) E.resume();
    // the idle countdown runs during a round too (also on a booth where taps don't open the bar): nobody playing → the show
    visitorTouch(E);
    renderRound(E);
    E.renderChrome();
    E.show(items[0], { record: false, user: true });
  }
  function quizStep(E) {
    var Q = E.quiz;
    if (Q.done) { endQuiz(E); return; }
    Q.i += 1;
    if (Q.i < Q.items.length) {
      renderRound(E);
      E.show(Q.items[Q.i], { record: false, user: true });
      return;
    }
    Q.done = true;
    renderRound(E);
    E.show({ id: "auto:score", type: "score", pub: "both", langs: [Q.lang] }, { record: false, user: true, score: { n: Q.score, total: Q.items.length } });
  }
  function endQuiz(E, quiet) {
    E.quiz = null;
    renderRound(E);
    E.renderChrome();
    if (!quiet) E.next();
  }
  /** After a question's answer: "Next question" (or "See my score"); a fill-in asks "Did you know it?" first. */
  function quizAfterReveal(E, c, hadFocus) {
    var s = c.node.querySelector(".gvb-s");
    if (!s || s.querySelector("[data-gvb-quiz]")) return;
    var l = E.quiz.lang;
    var acts = el("div", "gvb-actions gvb-reveal-in");
    if (c.item.type !== "quiz" && c.item.type !== "truefalse" && !c.answered) {
      acts.appendChild(setLang(el("p", "gvb-txt", S(l, "booth.screen.did_you")), l));
      var yes = button("gvb-bigbtn", S(l, "booth.screen.got_it"), { icon: "check", lang: l });
      yes.setAttribute("data-gvb-quiz", "knew");
      var no = button("gvb-bigbtn gvb-bigbtn--ghost", S(l, "booth.screen.missed_it"), { lang: l });
      no.setAttribute("data-gvb-quiz", "missed");
      acts.appendChild(yes);
      acts.appendChild(no);
    } else {
      var last = E.quiz.i >= E.quiz.items.length - 1;
      var nx = button("gvb-bigbtn", S(l, last ? "booth.screen.see_score" : "booth.screen.next_question"), { icon: "chevron-right", lang: l });
      nx.setAttribute("data-gvb-quiz", "next");
      acts.appendChild(nx);
    }
    s.appendChild(acts);
    var first = acts.querySelector("button");
    if (first && (hadFocus || E.screen.contains(document.activeElement))) first.focus({ preventScroll: true });
  }
  function quizAction(E, act) {
    var c = E.cur;
    if (act === "again") { E.quiz = null; startQuiz(E); return; }
    if (act === "end") { endQuiz(E); return; }
    if (!E.quiz || !c) return;
    if (act === "knew" || act === "missed") {
      if (!c.answered) { c.answered = true; E.quiz.results.push(act === "knew"); if (act === "knew") E.quiz.score += 1; }
      if (act === "knew" && !calm()) confetti(E);
      E.next();
      return;
    }
    if (act === "next") E.next();
  }
  function renderRound(E) {
    if (!E.round) return;
    var Q = E.quiz;
    E.round.hidden = !Q || Q.done;
    if (!Q || Q.done) return;
    clear(E.round);
    setLang(E.round, Q.lang);
    E.round.appendChild(el("span", "", S(Q.lang, "booth.screen.question_n", { n: Q.i + 1, total: Q.items.length })));
    var dots = attrs(el("span", "gvb-round-dots"), { "aria-hidden": "true" });
    Q.items.forEach(function (it, i) {
      var d = el("span");
      if (i < Q.results.length) d.className = Q.results[i] ? "is-right" : "is-done";
      dots.appendChild(d);
    });
    E.round.appendChild(dots);
  }
  /** A short message on the screen (no quiz questions in this language …). */
  function flash(E, text, l) {
    var p = setLang(el("p", "gvb-tapchip"), l);
    p.style.animation = "none";
    p.appendChild(icon("info"));
    p.appendChild(el("span", "", text));
    E.screen.appendChild(p);
    live(text);
    setTimeout(function () { p.remove(); }, 4500);
  }

  /* ---------- "Tap for full screen & sound" (opened by its address; or a browser that held the sound back) ---------- */
  function showTapChip() {
    var E = P.E;
    if (!E || E.tapChip || (SOUND.unlocked && !SOUND.blocked && fsEl())) return;
    var l = E.barLang();
    var b = button("gvb-tapchip", S(l, "booth.screen.tap_full"), { icon: "hand", lang: l });
    b.setAttribute("data-gvb-tapchip", "");
    E.tapChip = b;
    E.screen.appendChild(b);
  }
  /** The first tap: sound may play now, full screen (if the settings say so), the current video unmuted. */
  function unlockFromTap(gesture) {
    SOUND.unlocked = true;
    SOUND.blocked = false;
    var E = P.E;
    if (E && E.tapChip) { E.tapChip.remove(); E.tapChip = null; }
    if (gesture && SETTINGS.autoFullscreen !== false && !fsEl()) goFull();
    if (E && E.cur && E.cur.media && E.cur.media.setMuted && SETTINGS.sound && !(E.cur.item.media && E.cur.item.media.muted)) E.cur.media.setMuted(false);
  }

  /* ================================================================== 6. the player (a modal dialog) */
  function q(sel) { return P.root ? P.root.querySelector(sel) : null; }
  function qa(sel) { return P.root ? Array.prototype.slice.call(P.root.querySelectorAll(sel)) : []; }
  /** Opens the show. opts: gesture (a click started it: full screen and sound may follow), auto (?booth=start),
   *  tab (open on Settings at this tab), opener (the focus goes back there). */
  function openPlayer(opts) {
    opts = opts || {};
    if (P.root) { if (opts.tab) openSettings(opts.tab); return; }
    var tpl = document.getElementById("gvb-tpl");
    if (!tpl || !tpl.content || !tpl.content.firstElementChild) return;
    stopPreviews();
    loadSettings();
    loadPolls();
    loadMemo();
    P.opener = opts.opener || (document.activeElement && document.activeElement !== document.body ? document.activeElement : null);
    P.startUrl = location.pathname + cleanSearch(location.search) + location.hash;
    P.root = tpl.content.firstElementChild.cloneNode(true);
    document.body.appendChild(P.root);
    P.inerted = Array.prototype.filter.call(document.body.children, function (n) {
      return n !== P.root && !/^(SCRIPT|TEMPLATE|STYLE|LINK)$/.test(n.tagName) && !n.hasAttribute("inert") && !n.classList.contains("gvb-toast--page");
    });
    P.inerted.forEach(function (n) { n.setAttribute("inert", ""); });
    document.documentElement.classList.add("gvb-open");
    SOUND.unlocked = !!opts.gesture || !!(navigator.userActivation && navigator.userActivation.hasBeenActive);
    // full screen needs the click itself: asked for now, before anything waits (not for "Settings" from the page)
    if (opts.gesture && !opts.noFull && SETTINGS.autoFullscreen !== false) goFull();
    P.E = makeEngine(q("[data-gvb-host]"), "full");
    var nostore = q("[data-gvb-nostore]");
    if (nostore) nostore.hidden = storageOk;
    bindDialog();
    P.root.focus({ preventScroll: true });
    if (!storageOk && !warnedNoStorage) { warnedNoStorage = true; toast(T("booth.no_storage")); }
    if (opts.applied) toast(T(opts.applied));
    showLoading(P.E);
    var root = P.root;
    // the slide on screen fitted again once the web fonts are in (Fraunces is wider than its stand-in)
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { if (P.root === root && P.E && P.E.cur) fitSlide(P.E.cur.node); });
    var go = function () {
      loadData().then(function () {
        if (P.root !== root) return;
        P.E.start();
        if (opts.tab) openSettings(opts.tab, true);
        saveOffline("start");
        renderChips();
      }, function () {
        if (P.root !== root) return;
        showLoading(P.E, true, function () { showLoading(P.E); go(); });
      });
    };
    go();
    requestWake();
    startProbes();
    scheduleUpdates();
    if (opts.auto && !opts.gesture) showTapChip();
  }
  function closePlayer() {
    if (!P.root) return;
    try { if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document); } catch (e) { /* fine */ }
    unbindDialog();
    if (P.E) {
      if (P.E.sched !== null) { MEMO.sched = P.E.sched; saveMemo(); }
      P.E.stop();
    }
    P.E = null;
    releaseWake();
    stopProbes();
    clearInterval(updateTimer);
    clearTimeout(TOAST.timer);
    clearTimeout(P.promptTimer);
    // a retry of an offline save belongs to the show and goes with it (the next Start saves again)
    clearTimeout(OFF.retryTimer);
    OFF.retryTimer = 0;
    OFF.retry = false;
    P.root.remove();
    P.root = null;
    P.inerted.forEach(function (n) { n.removeAttribute("inert"); });
    P.inerted = [];
    P.drawer = false;
    P.modal = null;
    document.documentElement.classList.remove("gvb-open");
    try { history.replaceState(history.state, "", P.startUrl || location.pathname); } catch (e) { /* fine */ }
    renderQuick();
    renderChips();
    resumeCard();
    var back = P.opener && P.opener.isConnected && P.opener.focus ? P.opener : document.querySelector("[data-gvb-start]");
    P.opener = null;
    if (back && back.focus) back.focus({ preventScroll: true });
  }
  /** The address without ?booth / &bs (what the page was before the show opened). */
  function cleanSearch(search) {
    try {
      var p = new URLSearchParams(search);
      p.delete("booth");
      p.delete("bs");
      var s = p.toString();
      return s ? "?" + s : "";
    } catch (e) { return ""; }
  }

  /* ---------- full screen, the screen kept on ---------- */
  function fsEl() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
  function fullOk() { return !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen); }
  function goFull() {
    if (!P.root || fsEl() || !fullOk()) return;
    try {
      var r = (P.root.requestFullscreen || P.root.webkitRequestFullscreen).call(P.root);
      if (r && r.catch) r.catch(function () { /* not allowed now: "Tap for full screen" stays */ });
    } catch (e) { /* not allowed here */ }
  }
  function toggleFull() {
    if (!P.root) return;
    try {
      if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else goFull();
    } catch (e) { /* not allowed */ }
  }
  function syncFull() {
    if (P.drawer && P.tab === "screen") renderPanel("screen");
  }
  function requestWake() {
    if (!P.root || SETTINGS.wakeLock === false) return;
    if (!("wakeLock" in navigator) || !navigator.wakeLock || !navigator.wakeLock.request) { P.wakeState = "none"; return; }
    if (P.wake) return;
    navigator.wakeLock.request("screen").then(function (lock) {
      if (!P.root) { try { lock.release(); } catch (e) { /* gone */ } return; }
      P.wake = lock;
      P.wakeState = "on";
      lock.addEventListener("release", function () { P.wake = null; if (P.wakeState === "on") P.wakeState = "off"; });
      if (P.drawer && P.tab === "kiosk") renderPanel("kiosk");
    }, function () { P.wakeState = "off"; });
  }
  function releaseWake() {
    try { if (P.wake) P.wake.release(); } catch (e) { /* gone */ }
    P.wake = null;
    P.wakeState = "";
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState !== "visible") return;
    if (P.root) { requestWake(); probe(); }
  });

  /* ---------- events of the dialog ---------- */
  function bindDialog() {
    P.root.addEventListener("click", onDialogClick);
    P.root.addEventListener("pointerdown", onDialogPointer, true);
    P.root.addEventListener("pointerup", cancelHold);
    P.root.addEventListener("pointercancel", cancelHold);
    P.root.addEventListener("pointerleave", cancelHold);
    document.addEventListener("keydown", onKey);
    document.addEventListener("fullscreenchange", syncFull);
    document.addEventListener("webkitfullscreenchange", syncFull);
    var tabs = q("[data-gvb-tabs]");
    if (tabs) tabs.addEventListener("keydown", onTabKey);
    var form = q("[data-gvb-pin-form]");
    if (form) form.addEventListener("submit", onPinSubmit);
    window.addEventListener("blur", onWinBlur);
    if (WIDE) { if (WIDE.addEventListener) WIDE.addEventListener("change", syncInert); else if (WIDE.addListener) WIDE.addListener(syncInert); }
    // what an operator does in Settings, or in the PIN / "Leave?" box, keeps it open (visitorIdle, armPrompt)
    var dr = q("[data-gvb-drawer]");
    if (dr) ["pointerdown", "keydown", "input", "focusin"].forEach(function (ev) { dr.addEventListener(ev, drawerTouched); });
    [q("[data-gvb-pin]"), q("[data-gvb-leave]")].forEach(function (m) {
      if (m) ["pointerdown", "keydown", "input"].forEach(function (ev) { m.addEventListener(ev, armPrompt); });
    });
  }
  function unbindDialog() {
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("fullscreenchange", syncFull);
    document.removeEventListener("webkitfullscreenchange", syncFull);
    window.removeEventListener("blur", onWinBlur);
    if (WIDE) { if (WIDE.removeEventListener) WIDE.removeEventListener("change", syncInert); else if (WIDE.removeListener) WIDE.removeListener(syncInert); }
    cancelHold();
  }
  function drawerTouched() { P.drawerUsed = now(); }
  /** A tap on a YouTube video lands in its frame — YouTube's page: the booth never gets the click, and the frame
   *  keeps the keyboard. The booth hears it as its window losing the focus to that frame: the bar comes up as for
   *  any tap, and the focus comes back to the dialog, so S, Esc, Space and the arrows are the show's again. (YouTube's
   *  own links in its player stay as YouTube shows them: its API policies forbid disabling them; a pause they cause
   *  plays on — ytMedia.) */
  function onWinBlur() {
    setTimeout(function () {
      var E = P.E, a = document.activeElement;
      if (!E || !P.root || !a || a.tagName !== "IFRAME" || !E.stage || !E.stage.contains(a)) return;
      visitorTouch(E);
      P.root.focus({ preventScroll: true });
    }, 0);
  }
  function onDialogPointer(e) {
    // a tap anywhere in the dialog (Settings too) is the gesture that lets the browser play sound from now on
    SOUND.unlocked = true;
    var E = P.E;
    if (!E) return;
    var t = e.target;
    if (!t.closest || !E.screen.contains(t)) return;
    // press and hold the event's name (top left) 3 s: Settings
    var hold = t.closest("[data-gvb-hold]");
    if (hold && !P.drawer && !P.modal) startHold(hold);
  }
  function onDialogClick(e) {
    var t = e.target;
    if (!t.closest) return;
    var a = t.closest("[data-gvb-act]");
    if (a && !a.disabled) { act(a.getAttribute("data-gvb-act")); return; }
    var tab = t.closest("[data-gvb-tab]");
    if (tab) { selectTab(tab.getAttribute("data-gvb-tab"), true); return; }
    var E = P.E;
    if (!E || !E.screen.contains(t)) return;
    if (HOLD.done) { HOLD.done = false; return; }          // (the click after a 3-second hold)
    if (t.closest("[data-gvb-tapchip]")) { unlockFromTap(true); visitorTouch(E); return; }
    if (E.tapChip) unlockFromTap(true);
    if (t.closest("[data-gvb-take-close]")) { closeTake(E, true); return; }
    if (E.take && !t.closest(".gvb-take-box")) { closeTake(E, true); return; }
    var v = t.closest("[data-gvb-v]");
    if (v) { visitorTouch(E); if (!v.disabled) barAction(E, v.getAttribute("data-gvb-v")); return; }
    var ch = t.closest(".gvb-choice");
    if (ch) { visitorTouch(E); if (!ch.disabled && (SETTINGS.visitor !== false || E.quiz)) E.answer(Number(ch.getAttribute("data-i"))); return; }
    var pr = t.closest(".gvb-pollrow");
    if (pr) { visitorTouch(E); if (!pr.disabled && SETTINGS.visitor !== false) E.vote(Number(pr.getAttribute("data-i"))); return; }
    var rv = t.closest("[data-gvb-reveal]");
    if (rv) { visitorTouch(E); E.reveal(); return; }
    var qz = t.closest("[data-gvb-quiz]");
    if (qz) { visitorTouch(E); quizAction(E, qz.getAttribute("data-gvb-quiz")); return; }
    visitorTouch(E);
  }
  function act(name) {
    var E = P.E;
    if (name === "settings") { if (P.drawer) closeDrawer(); else openSettings(); }
    else if (name === "pin-cancel") closePin(false);
    else if (name === "leave-yes") { closeModal(); closePlayer(); }
    // Settings' foot: "Leave the show" (a touch screen's way out — Esc's on a keyboard); Settings asked for the PIN
    // already, so only "Leave the booth display?"
    else if (name === "leave") openModal(q("[data-gvb-leave]"));
    else if (name === "leave-no") closeModal();
    else if (name === "full") toggleFull();
    else if (E && name === "next") E.next({ user: true });
  }
  var HOLD = { timer: 0, node: null, hint: null, done: false };
  function startHold(node) {
    cancelHold();
    HOLD.node = node;
    node.classList.add("is-holding");
    node.addEventListener("pointerleave", cancelHold, { once: true });
    HOLD.hint = el("span", "gvb-holdhint", T("booth.hold"));
    node.appendChild(HOLD.hint);
    HOLD.timer = setTimeout(function () {
      cancelHold();
      HOLD.done = true;
      setTimeout(function () { HOLD.done = false; }, 800);
      openSettings();
    }, 3000);
  }
  function cancelHold() {
    clearTimeout(HOLD.timer);
    HOLD.timer = 0;
    if (HOLD.node) HOLD.node.classList.remove("is-holding");
    if (HOLD.hint) HOLD.hint.remove();
    HOLD.node = null;
    HOLD.hint = null;
  }
  /** Tab stays in the box on top: the PIN or "Leave?" box, else "Take it home", else the dialog (where Settings
   *  cover the show, the show is inert: syncInert). */
  function trapTab(e) {
    var scope = P.modal || (P.E && P.E.take && P.E.take.panel) || P.root;
    var f = Array.prototype.slice.call(scope.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]')).filter(function (x) {
      return x.offsetParent !== null && !x.closest("[hidden]") && !x.closest("[inert]") && x.getAttribute("tabindex") !== "-1" && getComputedStyle(x).visibility !== "hidden";
    });
    if (!f.length) { e.preventDefault(); return; }
    var first = f[0], last = f[f.length - 1];
    var a = document.activeElement;
    if (!a || a === P.root || a === scope || !scope.contains(a)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); return; }
    if (f.indexOf(a) < 0) {
      // the focus on something Tab does not stop at (the explanation an answer left it on): on in the page's order,
      // and around at either end
      var before = f.filter(function (x) { return x.compareDocumentPosition(a) & 4; }).length;
      if (e.shiftKey && !before) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && before === f.length) { e.preventDefault(); first.focus(); }
      return;
    }
    if (e.shiftKey && a === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && a === last) { e.preventDefault(); first.focus(); }
  }
  function escape() {
    var E = P.E;
    if (P.modal) { if (P.modal === q("[data-gvb-pin]")) closePin(false); else closeModal(); return; }
    if (E && E.take) { closeTake(E, true); return; }
    if (P.drawer) { closeDrawer(); return; }
    if (E && E.quiz) { endQuiz(E); return; }
    askLeave();
  }
  function onKey(e) {
    if (!P.root || e.altKey || e.ctrlKey || e.metaKey) return;
    var k = e.key, t = e.target;
    if (t && t !== document.body && t !== document.documentElement && !P.root.contains(t)) return;
    var E = P.E;
    if (k === "Escape") { e.preventDefault(); escape(); return; }
    // (the bar first: Tab then reaches its buttons)
    if (k === "Tab") { if (!P.drawer && !P.modal) visitorTouch(E); trapTab(e); return; }
    if (P.modal) return;
    if (!t.closest) return;
    if (t.closest("input, textarea, select, [contenteditable], [data-gvb-drawer], .gvb-toast")) return;
    if ((k === " " || k === "Enter") && t.closest("a, button, summary")) { visitorTouch(E); return; }
    if (!E || !E.alive) return;
    var low = k.length === 1 ? k.toLowerCase() : k;
    if (E.tapChip) unlockFromTap(false);
    if (low === "s") { e.preventDefault(); openSettings(); }
    else if (k === " ") { e.preventDefault(); visitorTouch(E); E.togglePause(); }
    else if (k === "ArrowRight") { e.preventDefault(); visitorTouch(E); barAction(E, "next"); }
    else if (k === "ArrowLeft") { e.preventDefault(); visitorTouch(E); E.back(); }
    else if (low === "f") { e.preventDefault(); toggleFull(); }
    else if (low === "m") {
      e.preventDefault();
      SOUND.unlocked = true;
      setSetting("sound", !SETTINGS.sound);
      live(T(SETTINGS.sound ? "booth.sound_on" : "booth.sound_off"));
    } else if (low === "l") {
      e.preventDefault();
      var at = LANG_MODES.indexOf(SETTINGS.lang);
      var nx = LANG_MODES[(at + 1) % LANG_MODES.length];
      E.langOverride = null;
      setSetting("lang", nx);
      live(T("booth.lang_set", { lang: T("booth.lang." + nx) }));
    } else if (low === "q") { e.preventDefault(); visitorTouch(E); startQuiz(E); }
    else visitorTouch(E);
  }

  /* ---------- the PIN, "Leave?" ---------- */
  function openModal(node, focusEl) {
    if (!node) return;
    closeModal();
    P.modal = node;
    node.hidden = false;
    syncInert();
    var f = focusEl || node.querySelector("button, input");
    if (f) f.focus({ preventScroll: true });
    armPrompt();
  }
  function closeModal() {
    if (!P.modal) return;
    clearTimeout(P.promptTimer);
    P.modal.hidden = true;
    P.modal = null;
    syncInert();
    var back = P.drawer ? q('[data-gvb-tab][aria-selected="true"]') : null;
    (back || P.root).focus({ preventScroll: true });
  }
  /** What is inert behind what: everything but the box while the PIN or "Leave?" box is up; the show while Settings
   *  cover it (a window narrower than 64rem — wider, areas/booth.css lays the drawer beside the show, which stays
   *  reachable). Worked out again whenever one opens or closes, and when the window crosses that width (a tablet
   *  turned). */
  var WIDE = (function () { try { return window.matchMedia("(min-width: 64rem)"); } catch (e) { return null; } })();
  function syncInert() {
    var host = q("[data-gvb-host]"), dr = q("[data-gvb-drawer]");
    if (host) host.inert = !!P.modal || (P.drawer && !(WIDE && WIDE.matches));
    if (dr) dr.inert = !!P.modal;
  }
  /** The PIN or "Leave?" box closes by itself after the idle time without a touch in it (opened by a visitor's
   *  3-second hold, an S or Esc on the laptop …): the show is never left dimmed behind it all day. The idle that
   *  follows hides the bar, undoes a visitor's language and ends a round left half-way. A key or a tap in the box
   *  starts its time again. */
  function armPrompt() {
    clearTimeout(P.promptTimer);
    if (!P.modal) return;
    P.promptTimer = setTimeout(function () {
      if (!P.root || !P.modal) return;
      if (P.modal === q("[data-gvb-pin]")) closePin(false); else closeModal();
      if (P.E && P.E.alive) visitorIdle(P.E);
    }, Math.max(10, Number(SETTINGS.idleSeconds) || 40) * 1000);
  }
  /** The PIN before Settings or leaving (none set: straight on). → Promise<boolean> */
  function askPin(why) {
    var pin = String(SETTINGS.pin || "");
    if (!/^\d{4}$/.test(pin)) return Promise.resolve(true);
    return new Promise(function (resolve) {
      var box = q("[data-gvb-pin]");
      if (!box) { resolve(true); return; }
      var input = q("[data-gvb-pin-input]");
      input.value = "";
      q("[data-gvb-pin-err]").textContent = "";
      q("[data-gvb-pin-why]").textContent = T(why === "leave" ? "booth.pin_for_leave" : "booth.pin_for_settings");
      P.pinResolve = resolve;
      openModal(box, input);
    });
  }
  function onPinSubmit(e) {
    e.preventDefault();
    var input = q("[data-gvb-pin-input]");
    if (String(input.value) === String(SETTINGS.pin || "")) { closePin(true); return; }
    q("[data-gvb-pin-err]").textContent = T("booth.pin_wrong");
    input.select();
  }
  function closePin(ok) {
    var r = P.pinResolve;
    P.pinResolve = null;
    closeModal();
    if (r) r(!!ok);
  }
  function askLeave() {
    askPin("leave").then(function (ok) {
      if (!ok || !P.root) return;
      if (/^\d{4}$/.test(String(SETTINGS.pin || ""))) closePlayer();     // the PIN was the asking
      else openModal(q("[data-gvb-leave]"));
    });
  }
  function openSettings(tab, noPin) {
    var go = function (ok) { if (ok && P.root) openDrawer(tab || P.tab || "event"); };
    if (noPin) go(true); else askPin("settings").then(go);
  }

  /* ---------- the live region, the toast ---------- */
  function live(text) {
    var r = P.root ? q("[data-gvb-live]") : null;
    if (!r) { if (window.GV && window.GV.announce) window.GV.announce(text); return; }
    r.textContent = "";
    setTimeout(function () { if (r.isConnected) r.textContent = text; }, 60);
  }
  var TOAST = { timer: 0, action: null };
  function pageToast() {
    var t = document.getElementById("gvb-page-toast");
    if (!t) {
      t = attrs(el("div", "gvb-toast gvb-toast--page is-idle"), { role: "status", "aria-live": "polite", id: "gvb-page-toast" });
      document.body.appendChild(t);
    }
    return t;
  }
  /** A short message at the bottom (in the dialog while it is open), with an optional action (Undo) for 10 s. */
  function toast(text, action) {
    var t = P.root ? q("[data-gvb-toast]") : pageToast();
    if (!t) return null;
    clearTimeout(TOAST.timer);
    clear(t);
    var msg = el("span", "", text);
    msg.id = newId("gvb-tt");
    t.appendChild(msg);
    var b = null;
    if (action) {
      b = button("gvb-toast-btn", action.label);
      b.setAttribute("aria-describedby", msg.id);
      b.addEventListener("click", function () {
        hideToast(t);
        action.run();
        if (action.after) action.after();
      });
      t.appendChild(b);
    }
    t.classList.remove("is-idle");
    TOAST.timer = setTimeout(function () { hideToast(t); }, action ? 10000 : 5000);
    return b;
  }
  function hideToast(t) {
    clearTimeout(TOAST.timer);
    var had = t.contains(document.activeElement);
    clear(t);
    t.classList.add("is-idle");
    if (had && P.root) P.root.focus({ preventScroll: true });
  }

  /* ================================================================== 7. Settings (a drawer beside the screen)
     Event · Show · Slides · Timing & sound · Screen · Kiosk · Offline · Share & reset. Every change applies at once
     and is kept on this device (only what was changed here); the show keeps playing beside it. */
  var TABS = ["event", "show", "items", "timing", "screen", "kiosk", "offline", "share"];
  function openDrawer(tab) {
    if (!P.root) return;
    var d = q("[data-gvb-drawer]");
    if (!d) return;
    if (P.E) closeTake(P.E, false);
    d.hidden = false;
    P.drawer = true;
    P.drawerUsed = now();
    P.root.classList.add("has-drawer");
    syncInert();
    // the idle countdown runs while it is open (S or a hold start none): left alone, it closes (visitorIdle)
    if (P.E && P.E.alive) { clearTimeout(P.E.timers.idle); P.E.timers.idle = setTimeout(function () { visitorIdle(P.E); }, 10000); }
    selectTab(TABS.indexOf(tab) >= 0 ? tab : "event", true);
    if (P.tab === "offline" || P.tab === "items") offlineStatus();
  }
  function closeDrawer() {
    var d = q("[data-gvb-drawer]");
    if (d) d.hidden = true;
    P.drawer = false;
    P.root.classList.remove("has-drawer");
    syncInert();
    if (P.contentChanged) { P.contentChanged = false; reopen(P.E); }
    P.root.focus({ preventScroll: true });
  }
  function selectTab(name, focusTab) {
    P.tab = name;
    qa("[data-gvb-tab]").forEach(function (t) {
      var on = t.getAttribute("data-gvb-tab") === name;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
    });
    qa("[data-gvb-panel]").forEach(function (p) { p.hidden = p.getAttribute("data-gvb-panel") !== name; });
    renderPanel(name);
    if (name === "offline") offlineStatus();
    if (focusTab) {
      var t = q('[data-gvb-tab="' + name + '"]');
      if (t) t.focus({ preventScroll: true });
    }
  }
  function onTabKey(e) {
    var t = e.target.closest && e.target.closest("[data-gvb-tab]");
    if (!t) return;
    var tabs = qa("[data-gvb-tab]");
    var at = tabs.indexOf(t), to = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") to = (at + 1) % tabs.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") to = (at - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") to = 0;
    else if (e.key === "End") to = tabs.length - 1;
    if (to < 0) return;
    e.preventDefault();
    selectTab(tabs[to].getAttribute("data-gvb-tab"), true);
  }
  /** Draws a panel again, the focus back on the same control (its data-gvb-key) and the list where it was. */
  function renderPanel(name) {
    if (!P.root || !P.drawer) return;
    var p = q('[data-gvb-panel="' + name + '"]');
    if (!p || p.hidden) return;
    var a = document.activeElement;
    var key = a && p.contains(a) ? a.getAttribute("data-gvb-key") : null;
    var caret = key && a.selectionStart !== undefined ? [a.selectionStart, a.selectionEnd] : null;
    var scroll = p.scrollTop;
    clear(p);
    try { PANELS[name](p); } catch (e) { p.appendChild(el("p", "gvb-pp", T("booth.load_failed"))); }
    p.scrollTop = scroll;
    if (key) {
      var again = p.querySelector('[data-gvb-key="' + key + '"]');
      if (again && !again.disabled) {
        again.focus({ preventScroll: true });
        if (caret && again.setSelectionRange) { try { again.setSelectionRange(caret[0], caret[1]); } catch (e) { /* not a text field */ } }
      } else p.focus({ preventScroll: true });
    }
  }
  /** After a setting changed (here, on the page's quick controls or by a key): what shows it, at once. */
  var CONTENT_KEYS = { lang: 1, first: 1, pubs: 1, channels: 1, collections: 1, items: 1, tags: 1, order: 1, event: 1, boost: 1 };
  function settingsChanged(path) {
    var top = String(path || "").split(".")[0];
    var E = P.E;
    // what may show changed: when Settings closes, the show opens with its first slides again (the core's rule)
    if (CONTENT_KEYS[top]) P.contentChanged = true;
    [E, INLINE, CARD].forEach(function (x) { if (x && x.alive) x.applyLook(); });
    if (E && E.alive) {
      if (top === "lang" || top === "first") { E.langOverride = null; E.barKey = ""; E.rerender(); }
      else if (top === "event" && E.cur && E.cur.item.type === "welcome") E.rerender();
      else if (top === "sound" || top === "volume") {
        var c = E.cur;
        if (c && c.media && c.media.setMuted) c.media.setMuted(!(SETTINGS.sound && SOUND.unlocked && !(c.item.media && c.item.media.muted)));
      } else if (top === "visitor" && SETTINGS.visitor === false) visitorIdle(E);
      else if (top === "refreshMinutes") scheduleUpdates();
      else if (top === "wakeLock") { if (SETTINGS.wakeLock === false) releaseWake(); else requestWake(); }
    }
    if (P.drawer && top !== "event" && top !== "pin") renderPanel(P.tab);
    renderQuick();
    renderChips();
  }

  /* ---------- the panels' controls ---------- */
  function sect(p, heading) {
    var s = el("section", "gvb-sect");
    if (heading) s.appendChild(el("h4", "gvb-sect-h", heading));
    p.appendChild(s);
    return s;
  }
  function textField(parent, label, value, onInput, o) {
    o = o || {};
    var f = el("div", "gvb-field");
    var id = newId("gvb-f");
    f.appendChild(attrs(el("label", "gvb-label", label), { for: id }));
    var input = el("input", "gvb-input" + (o.cls ? " " + o.cls : ""));
    attrs(input, { id: id, type: o.type || "text", maxlength: o.max || 120, autocomplete: "off", spellcheck: "false", placeholder: o.ph || null,
      lang: o.lang || null, "data-gvb-key": o.key || null, inputmode: o.inputmode || null, readonly: o.readonly ? "" : null });
    input.value = value == null ? "" : String(value);
    if (onInput) input.addEventListener(o.change ? "change" : "input", function () { onInput(input.value, input); });
    f.appendChild(input);
    if (o.hint) {
      var h = el("p", "gvb-pp gvb-pp--muted", o.hint);
      h.id = id + "-h";
      input.setAttribute("aria-describedby", h.id);
      f.appendChild(h);
    }
    parent.appendChild(f);
    return input;
  }
  function numField(parent, label, path, min, max, step) {
    return textField(parent, label, getPath(SETTINGS, path), function (v, input) {
      var n = Number(String(v).replace(",", "."));
      if (!isFinite(n)) { input.value = getPath(SETTINGS, path); return; }
      setSetting(path, Math.max(min, Math.min(max, n)));
    }, { type: "number", cls: "gvb-input--num", key: "n:" + path, change: true, inputmode: step && step < 1 ? "decimal" : "numeric", max: 6 });
  }
  /** Radio buttons for one setting: options [{ value, label, desc }]. */
  function radios(parent, legend, path, options, o) {
    o = o || {};
    var fs = el("fieldset", o.segs ? "gvb-radios gvb-segs" : "gvb-radios");
    if (legend) fs.appendChild(el("legend", "", legend));
    var name = newId("gvb-r");
    var cur = getPath(SETTINGS, path);
    options.forEach(function (opt) {
      var lab = el("label", "gvb-radio");
      var input = attrs(el("input"), { type: "radio", name: name, value: opt.value, "data-gvb-key": "r:" + path + ":" + opt.value });
      input.checked = String(cur) === String(opt.value);
      input.addEventListener("change", function () { if (input.checked) setSetting(path, opt.value); });
      lab.appendChild(input);
      var w = el("span", "gvb-opt-words");
      w.appendChild(setLang(el("span", "gvb-opt-t", opt.label), opt.lang || null));
      if (opt.desc) w.appendChild(el("span", "gvb-opt-d", opt.desc));
      lab.appendChild(w);
      fs.appendChild(lab);
    });
    parent.appendChild(fs);
    return fs;
  }
  /** A checkbox for a true / false setting (`off`: the setting is true when the box is clear). */
  function checkbox(parent, label, path, o) {
    o = o || {};
    var lab = el("label", "gvb-check");
    var input = attrs(el("input"), { type: "checkbox", "data-gvb-key": "c:" + path });
    var v = getPath(SETTINGS, path);
    input.checked = o.defaultOn ? v !== false : !!v;
    input.addEventListener("change", function () { setSetting(path, input.checked); });
    lab.appendChild(input);
    var w = el("span", "gvb-opt-words");
    w.appendChild(setLang(el("span", "gvb-opt-t", label), o.lang || null));
    if (o.desc) w.appendChild(el("span", "gvb-opt-d", o.desc));
    lab.appendChild(w);
    if (o.count !== undefined) lab.appendChild(el("span", "gvb-opt-n", o.count));
    if (o.net) w.firstChild.appendChild(el("span", "gvb-opt-net", T("booth.sh_net")));
    parent.appendChild(lab);
    return input;
  }
  function pill(parent, label, onClick, o) {
    o = o || {};
    var b = button("gvb-pill" + (o.cls ? " " + o.cls : ""), label, { icon: o.icon });
    if (o.key) b.setAttribute("data-gvb-key", o.key);
    if (o.disabled) b.disabled = true;
    b.addEventListener("click", onClick);
    parent.appendChild(b);
    return b;
  }
  function copyText(text, b) {
    if (window.GV && typeof window.GV.copy === "function") { window.GV.copy(text, b); return; }
    var done = function () { toast(T("booth.copied")); };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, function () { /* no clipboard */ });
  }
  function itemTitle(item) {
    var l = LANG === "es" ? ["es", "en"] : ["en", "es"];
    for (var i = 0; i < l.length; i++) {
      var t = textOf(item, l[i]);
      if (t && (t.title || t.text)) return { text: plain(fill(t.title || t.text, l[i])), lang: l[i] };
    }
    if (item.id === "auto:welcome") return { text: T("booth.type.welcome"), lang: LANG };
    if (item.id === "auto:about") return { text: T("booth.type.about"), lang: LANG };
    return { text: T("booth.it_untitled"), lang: LANG };
  }
  /** A reason in words (booth.why.<key>): the core's (off, channel, pub, collection, tag, date, over — said "ended" —,
   *  lang, offline, muted, media) or the screen's own "youtube" (not answering lately); anything else "unknown". */
  function whyText(key) {
    if (key === "over") return T("booth.why.ended");
    return T(key === "youtube" || G.REASONS.indexOf(key) >= 0 ? "booth.why." + key : "booth.why.unknown");
  }
  function chKey(id) { return "booth.ch." + String(id).replace(/-/g, "_"); }
  /** A topic's name in the page's language (booth.tag.<tag>, dashes as underscores: src/_i18n/booth.json has the two
   *  words of every tag the CSV and the live items use — tests/test_booth_page.py checks it); a tag without words
   *  yet: as written, dashes as spaces. */
  function tagLabel(tg) {
    var s = STRINGS["booth.tag." + String(tg).replace(/-/g, "_")];
    return typeof s === "string" && s ? s : String(tg).replace(/-/g, " ");
  }

  var PANELS = {};
  /* ---------- Event ---------- */
  PANELS.event = function (p) {
    var ev = SETTINGS.event || {};
    var s1 = sect(p, T("booth.ev_names_h"));
    var later = function (path) {
      var t = 0;
      return function (v) { clearTimeout(t); t = setTimeout(function () { setSetting(path, v.trim()); }, 250); };
    };
    textField(s1, T("booth.f_event"), ev.en, later("event.en"), { ph: T("booth.f_event_ph"), key: "ev-en", max: 80 });
    textField(s1, T("booth.f_event_es"), ev.es, later("event.es"), { ph: T("booth.f_event_es_ph"), key: "ev-es", lang: "es", max: 80 });
    textField(s1, T("booth.f_sub"), ev.sub, later("event.sub"), { ph: T("booth.f_sub_ph"), key: "ev-sub", max: 100 });
    checkbox(s1, T("booth.f_show_event"), "event.show", { defaultOn: true });
    var s2 = sect(p, T("booth.pick_h"));
    var picks = (DATA && Array.isArray(DATA.events_pick)) ? DATA.events_pick.filter(isObj) : [];
    if (!picks.length) s2.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.pick_empty")));
    else {
      var f = el("div", "gvb-field");
      var id = newId("gvb-f");
      f.appendChild(attrs(el("label", "gvb-label", T("booth.pick_label")), { for: id }));
      var sel = attrs(el("select", "gvb-input"), { id: id, "data-gvb-key": "pick" });
      sel.appendChild(attrs(el("option", "", T("booth.pick_choose")), { value: "" }));
      picks.forEach(function (ev2, i) {
        var title = (LANG === "es" ? ev2.title_es || ev2.title_en : ev2.title_en || ev2.title_es) || "";
        var date = LANG === "es" ? ev2.date_label_es || ev2.date_label_en : ev2.date_label_en || ev2.date_label_es;
        sel.appendChild(attrs(el("option", "", [title, date].filter(Boolean).join(" — ")), { value: String(i) }));
      });
      sel.addEventListener("change", function () {
        var e2 = picks[Number(sel.value)];
        if (!e2) return;
        var dl = SETTINGS.first === "es" ? e2.date_label_es || e2.date_label_en : e2.date_label_en || e2.date_label_es;
        // the place's first part ("Primary Purpose Group – Arlington", not the street address): one line on screen
        var place = String(e2.place || "").split(",")[0].trim();
        setPath(STORED, "event.en", String(e2.title_en || e2.title_es || ""));
        setPath(STORED, "event.es", e2.title_es && e2.title_es !== e2.title_en ? String(e2.title_es) : "");
        setPath(STORED, "event.sub", [dl, place].filter(Boolean).join(" · "));
        setPath(STORED, "event.show", true);
        computeSettings();
        saveSettings();
        settingsChanged("event");
        renderPanel("event");
        toast(T("booth.pick_done", { title: e2.title_en || e2.title_es || "" }));
      });
      f.appendChild(sel);
      s2.appendChild(f);
    }
    var s3 = sect(p, T("booth.presets_h"));
    s3.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.presets_intro")));
    var list = el("div", "gvb-presets");
    PRESETS.forEach(function (name) {
      var b = el("button", "gvb-preset");
      b.type = "button";
      b.setAttribute("data-gvb-key", "preset:" + name);
      b.appendChild(el("span", "gvb-opt-t", T("booth.preset." + name)));
      b.appendChild(el("span", "gvb-opt-d", T("booth.preset." + name + "_d")));
      b.addEventListener("click", function () { applyPreset(name); });
      list.appendChild(b);
    });
    s3.appendChild(list);
  };
  function applyPreset(name) {
    var patch = presetOf(name);
    if (!patch) return;
    STORED = deepMerge(STORED, patch);
    computeSettings();
    saveSettings();
    settingsChanged("lang");
    toast(T("booth.preset_done", { name: T("booth.preset." + name) }));
  }

  /* ---------- Show ---------- */
  PANELS.show = function (p) {
    // nothing of the show can play with these switches: only the "about" slide would come (never a blank screen)
    if (DATA && P.E && !P.E.pool().some(function (it) { return !/^auto:/.test(it.id); })) {
      p.appendChild(attrs(el("p", "gvb-pp gvb-pp--warn", T("booth.empty")), { role: "status" }));
    }
    var s1 = sect(p);
    radios(s1, T("booth.sh_lang_h"), "lang", LANG_MODES.map(function (m) {
      return { value: m, label: T("booth.lang." + m), desc: T("booth.lang_d." + m), lang: m === "en" || m === "es" ? m : null };
    }));
    var s2 = sect(p);
    radios(s2, T("booth.sh_first_h"), "first", [{ value: "en", label: T("booth.lang.en"), lang: "en" }, { value: "es", label: T("booth.lang.es"), lang: "es" }], { segs: true });
    var s3 = sect(p);
    var fs = el("fieldset", "gvb-checks");
    fs.appendChild(el("legend", "", T("booth.sh_pubs_h")));
    checkbox(fs, "Grapevine", "pubs.gv", { defaultOn: true, lang: "en" });
    checkbox(fs, "La Viña", "pubs.lv", { defaultOn: true, lang: "es" });
    s3.appendChild(fs);
    // the channels that have slides (with how many), and the player's own two
    var s4 = sect(p);
    var counts = {}, net = {};
    ((DATA && DATA.channels) || []).forEach(function (c) { if (isObj(c) && c.id) counts[c.id] = Number(c.count) || 0; });
    ((DATA && DATA.items) || []).forEach(function (it) { if (it.online && it.channel) net[it.channel] = true; });
    var fs2 = el("fieldset", "gvb-checks");
    fs2.appendChild(el("legend", "", T("booth.sh_channels_h")));
    channelIds().forEach(function (id) {
      var auto = id === "welcome" || id === "about";
      if (!auto && !counts[id]) return;
      checkbox(fs2, T(chKey(id)), "channels." + id, { defaultOn: true, count: auto ? "" : TN("booth.n_slides", counts[id]), net: !!net[id] });
    });
    s4.appendChild(fs2);
    s4.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.sh_sound_note")));
    var cols = ((DATA && DATA.collections) || []).filter(function (c) { return isObj(c) && c.id; });
    if (cols.length) {
      var s5 = sect(p);
      var fs3 = el("fieldset", "gvb-checks");
      fs3.appendChild(el("legend", "", T("booth.sh_collections_h")));
      // (the files right in the booth folder: "main", named in the page's language)
      cols.forEach(function (c) {
        var label = c.id === "main" ? T("booth.sh_collection_main") : c.label || c.id;
        checkbox(fs3, label, "collections." + c.id, { defaultOn: true, count: TN("booth.n_slides", Number(c.count) || 0) });
      });
      s5.appendChild(fs3);
    }
    var tags = {};
    ((DATA && DATA.items) || []).forEach(function (it) { (it.tags || []).forEach(function (tg) { if (tg) tags[tg] = (tags[tg] || 0) + 1; }); });
    var tagList = Object.keys(tags).sort(function (a, b) { return tags[b] - tags[a] || tagLabel(a).localeCompare(tagLabel(b), LANG); });
    if (tagList.length) {
      var s6 = sect(p);
      var fs4 = el("fieldset", "gvb-checks");
      fs4.appendChild(el("legend", "", T("booth.sh_tags_h")));
      tagList.forEach(function (tg) { checkbox(fs4, tagLabel(tg), "tags." + tg, { defaultOn: true, count: TN("booth.n_slides", tags[tg]) }); });
      s6.appendChild(fs4);
    }
    var s7 = sect(p);
    radios(s7, T("booth.sh_order_h"), "order", [{ value: "shuffle", label: T("booth.order.shuffle") }, { value: "inorder", label: T("booth.order.inorder") }]);
  };

  /* ---------- Slides: every item, on / off, why it can't show now, "Show now" ---------- */
  var ITEMS_VIEW = { q: "", f: "all" };
  PANELS.items = function (p) {
    var E = P.E;
    var tools = el("div", "gvb-itools");
    var search = textField(tools, T("booth.it_search"), ITEMS_VIEW.q, function (v) { ITEMS_VIEW.q = v; drawRows(); }, { type: "search", key: "it-q", max: 60 });
    search.closest(".gvb-field").style.marginTop = "0";
    var ff = el("div", "gvb-field");
    var fid = newId("gvb-f");
    ff.style.marginTop = "0";
    ff.appendChild(attrs(el("label", "gvb-label", T("booth.it_filter")), { for: fid }));
    var sel = attrs(el("select", "gvb-input"), { id: fid, "data-gvb-key": "it-f" });
    ["all", "on", "off", "out"].forEach(function (f) { sel.appendChild(attrs(el("option", "", T("booth.it_f." + f)), { value: f })); });
    sel.value = ITEMS_VIEW.f;
    sel.addEventListener("change", function () { ITEMS_VIEW.f = sel.value; drawRows(); });
    ff.appendChild(sel);
    tools.appendChild(ff);
    p.appendChild(tools);
    var count = attrs(el("p", "gvb-icount"), { role: "status", "aria-live": "polite" });
    p.appendChild(count);
    var list = el("div", "gvb-irows");
    p.appendChild(list);
    var s = E ? E.eff() : SETTINGS;
    var ctx = E ? E.ctx() : baseCtx();
    var all = allItems(s);
    var inPool = {};
    (E ? E.pool() : []).forEach(function (it) { inPool[it.id] = 1; });
    function drawRows() {
      clear(list);
      var qv = ITEMS_VIEW.q.trim().toLowerCase();
      var shown = 0, matched = 0;
      all.forEach(function (it) {
        var off = SETTINGS.items && SETTINGS.items[it.id] === false;
        var can = !!inPool[it.id];
        var f = ITEMS_VIEW.f;
        if (f === "on" && !can) return;
        if (f === "off" && !off) return;
        if (f === "out" && (off || can)) return;
        var tt = itemTitle(it);
        if (qv) {
          var hay = [tt.text, it.id, it.type, JSON.stringify(it.en || ""), JSON.stringify(it.es || "")].join(" ").toLowerCase();
          if (hay.indexOf(qv) < 0) return;
        }
        matched += 1;
        if (shown >= 150) return;
        shown += 1;
        var row = el("div", "gvb-irow" + (off ? " is-off" : ""));
        var main = el("div", "gvb-irow-main");
        main.appendChild(setLang(el("span", "gvb-irow-t", short(tt.text, 120)), tt.lang !== LANG ? tt.lang : null));
        var meta = el("span", "gvb-irow-meta");
        var pub = pubOf(it);
        meta.appendChild(el("span", "gvb-badge gvb-badge--" + pub, T("booth.type." + (RENDER[it.type] ? it.type : "message"))));
        if (it.online) meta.appendChild(el("span", "gvb-badge", T("booth.sh_net")));
        if (!can && !off) {
          // (a YouTube video is "media" for the core while YouTube is not answering: said as such)
          var w = whyOf(it, s, ctx);
          if (w === "media" && it.media && it.media.kind === "youtube" && !ytOk()) w = "youtube";
          meta.appendChild(el("span", "gvb-irow-why", whyText(w)));
        }
        main.appendChild(meta);
        row.appendChild(main);
        var acts = el("div", "gvb-irow-acts");
        if (E && !off) {
          var now1 = button("gvb-pill gvb-pill--sm", T("booth.it_show_now"), { icon: "eye" });
          now1.setAttribute("data-gvb-key", "now:" + it.id);
          now1.setAttribute("aria-label", T("booth.it_show_now") + ": " + short(tt.text, 80));
          now1.addEventListener("click", function () {
            if (E.quiz) endQuiz(E, true);
            E.show(it, { record: true, user: true });
            toast(T("booth.it_shown_now", { title: short(tt.text, 60) }));
          });
          acts.appendChild(now1);
        }
        var sw = el("button", "gvb-switch");
        sw.type = "button";
        attrs(sw, { role: "switch", "aria-checked": off ? "false" : "true", "data-gvb-key": "sw:" + it.id });
        sw.appendChild(el("span", "sr-only", T("booth.it_switch", { title: short(tt.text, 80) })));
        sw.appendChild(attrs(el("span", "gvb-switch-track"), { "aria-hidden": "true" }));
        sw.addEventListener("click", function () {
          // (the slides switched off now — this device's, else the site's — with this one changed)
          var items = Object.assign({}, SETTINGS.items || {});
          if (off) delete items[it.id]; else items[it.id] = false;
          STORED.items = items;
          computeSettings();
          saveSettings();
          settingsChanged("items");
        });
        acts.appendChild(sw);
        row.appendChild(acts);
        list.appendChild(row);
      });
      if (!matched) list.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.it_none")));
      count.textContent = T("booth.it_count", { n: matched, total: all.length }) + (matched > shown ? " · " + T("booth.it_more", { n: shown }) : "");
    }
    drawRows();
    var probs = ((DATA && DATA.problems) || []).filter(isObj);
    if (probs.length) {
      var box2 = el("div", "gvb-problems");
      box2.appendChild(el("p", "gvb-sect-h", T("booth.it_problems_h")));
      var ul = el("ul");
      probs.slice(0, 40).forEach(function (pr) {
        var li = el("li");
        if (pr.where) li.appendChild(el("strong", "", pr.where + ": "));
        li.appendChild(document.createTextNode(pr[LANG] || pr.en || pr.es || pr.problem || ""));
        ul.appendChild(li);
      });
      box2.appendChild(ul);
      p.appendChild(box2);
    }
  };

  /* ---------- Timing & sound ---------- */
  PANELS.timing = function (p) {
    var s1 = sect(p);
    radios(s1, T("booth.ti_pace_h"), "pace", ["calm", "normal", "lively"].map(function (v) { return { value: v, label: T("booth.pace." + v) }; }), { segs: true });
    var s2 = sect(p);
    numField(s2, T("booth.ti_reveal"), "reveal", 4, 60);
    numField(s2, T("booth.ti_photo"), "photoSeconds", 3, 120);
    numField(s2, T("booth.ti_media"), "mediaMax", 10, 900);
    numField(s2, T("booth.ti_webmedia"), "webMediaMax", 10, 900);
    // (a whole number: booth-core keeps clipEvery in steps of 1)
    numField(s2, T("booth.ti_clip"), "clipEvery", 3, 30);
    var s3 = sect(p, T("booth.ti_sound_h"));
    checkbox(s3, T("booth.ti_sound"), "sound");
    s3.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.ti_sound_note")));
    var f = el("div", "gvb-field");
    var id = newId("gvb-f");
    f.appendChild(attrs(el("label", "gvb-label", T("booth.ti_volume")), { for: id }));
    var range = attrs(el("input", "gvb-meter"), { id: id, type: "range", min: "0", max: "1", step: "0.1", "data-gvb-key": "volume" });
    range.value = String(SETTINGS.volume === undefined ? 0.8 : SETTINGS.volume);
    range.addEventListener("change", function () { setSetting("volume", Number(range.value)); });
    f.appendChild(range);
    s3.appendChild(f);
    checkbox(s3, T("booth.ti_captions"), "captions", { defaultOn: true });
  };

  /* ---------- Screen ---------- */
  PANELS.screen = function (p) {
    var s1 = sect(p);
    radios(s1, T("booth.sc_theme_h"), "theme", [{ value: "dark", label: T("booth.theme.dark") }, { value: "daylight", label: T("booth.theme.daylight") }]);
    var s2 = sect(p);
    radios(s2, T("booth.sc_text_h"), "textSize", [{ value: "normal", label: T("booth.text.normal") }, { value: "large", label: T("booth.text.large") }], { segs: true });
    var s3 = sect(p);
    radios(s3, T("booth.sc_motion_h"), "motion", [{ value: "full", label: T("booth.motion.full") }, { value: "calm", label: T("booth.motion.calm") }]);
    var s4 = sect(p, T("booth.sc_parts_h"));
    checkbox(s4, T("booth.sc_clock"), "clock", { defaultOn: true });
    checkbox(s4, T("booth.sc_qr"), "qrCorner", { defaultOn: true });
    checkbox(s4, T("booth.sc_progress"), "progress", { defaultOn: true });
    checkbox(s4, T("booth.sc_overscan"), "overscan");
    if (fullOk()) {
      var tools = el("div", "gvb-tools");
      pill(tools, fsEl() ? T("booth.full_exit") : T("booth.full"), function () { toggleFull(); }, { icon: fsEl() ? "minimize" : "maximize", key: "full" });
      s4.appendChild(tools);
    }
  };

  /* ---------- Kiosk ---------- */
  PANELS.kiosk = function (p) {
    var s1 = sect(p, T("booth.ki_pin_h"));
    var pinInput = textField(s1, T("booth.ki_pin"), SETTINGS.pin || "", null, { type: "password", inputmode: "numeric", max: 4, key: "pin", cls: "gvb-input--pin", hint: T("booth.ki_pin_note") });
    var tools = el("div", "gvb-tools");
    pill(tools, T("booth.ki_pin_set"), function () {
      var v = String(pinInput.value || "").trim();
      if (!/^\d{4}$/.test(v)) { toast(T("booth.ki_pin_bad")); pinInput.focus(); return; }
      setSetting("pin", v);
      toast(T("booth.ki_pin_saved"));
    }, { cls: "gvb-pill--primary", icon: "lock", key: "pin-set" });
    if (SETTINGS.pin) pill(tools, T("booth.ki_pin_clear"), function () { setSetting("pin", ""); toast(T("booth.ki_pin_removed")); renderPanel("kiosk"); }, { key: "pin-clear" });
    s1.appendChild(tools);
    var s2 = sect(p, T("booth.ki_visitors_h"));
    checkbox(s2, T("booth.ki_visitor"), "visitor", { defaultOn: true });
    numField(s2, T("booth.ki_idle"), "idleSeconds", 10, 600);
    numField(s2, T("booth.ki_quiz"), "quizLength", 3, 10);
    var s3 = sect(p, T("booth.ki_device_h"));
    checkbox(s3, T("booth.ki_wake"), "wakeLock", { defaultOn: true });
    var ws = P.wakeState;
    var wline = SETTINGS.wakeLock === false ? "booth.ki_wake_off" : ws === "on" ? "booth.ki_wake_on" : ws === "none" ? "booth.ki_wake_no" : "booth.ki_wake_off";
    s3.appendChild(el("p", "gvb-pp " + (ws === "on" && SETTINGS.wakeLock !== false ? "gvb-pp--ok" : "gvb-pp--warn"), T(wline)));
    checkbox(s3, T("booth.ki_autofull"), "autoFullscreen", { defaultOn: true });
    if (!fullOk() || /iPhone|iPad|iPod/.test(navigator.userAgent || "")) s3.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.ki_iphone")));
    numField(s3, T("booth.ki_refresh"), "refreshMinutes", 5, 1440);
    checkbox(s3, T("booth.ki_autosave"), "autoSave", { defaultOn: true });
    var s4 = sect(p, T("booth.ki_link_h"));
    s4.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.ki_link_text")));
    startLinkBox(s4, T("booth.ki_link_label"), "kiosk-link");
  };
  /** The address that opens this page and starts the show, with this setup in it: the part of the settings that
   *  differs from the site's (GVB.diff), encoded (GVB.encode: at most 2048 characters — a setup too big for a link,
   *  many slides switched off one by one, gives null: the link then starts the show with the site's settings, and
   *  the panel says so). The PIN never travels. → { url, whole } */
  function startLink() {
    var s = clone(SETTINGS) || {};
    s.pin = "";
    var code = call("encode", [call("diff", [s, BASE_SETTINGS || baseSettings()], {})], null);
    var page = location.origin + BASE + (LANG === "es" ? "es/" : "") + "about/";
    return { url: page + "?booth=start" + (code ? "&bs=" + encodeURIComponent(code) : ""), whole: !!code };
  }
  /** The start link's box, and a line under it when this setup is too big to travel in it. */
  function startLinkBox(parent, label, key) {
    var link = startLink();
    linkBox(parent, label, link.url, key);
    if (!link.whole) parent.appendChild(el("p", "gvb-pp gvb-pp--warn", T("booth.link_too_big")));
  }
  function linkBox(parent, label, url, key) {
    var f = el("div", "gvb-field");
    var id = newId("gvb-f");
    f.appendChild(attrs(el("label", "gvb-label", label), { for: id }));
    var row = el("div", "gvb-linkbox");
    var input = attrs(el("input", "gvb-input"), { id: id, type: "text", readonly: "", "data-gvb-key": key });
    input.value = url;
    input.addEventListener("focus", function () { input.select(); });
    row.appendChild(input);
    var b = button("gvb-pill gvb-pill--sm", T("booth.copy"), { icon: "copy" });
    b.setAttribute("data-gvb-key", key + "-copy");
    b.addEventListener("click", function () { copyText(url, b); });
    row.appendChild(b);
    f.appendChild(row);
    parent.appendChild(f);
  }

  /* ---------- Offline ---------- */
  PANELS.offline = function (p) {
    var s1 = sect(p, T("booth.of_state_h"));
    var line = attrs(el("p", "gvb-pp"), { role: "status" });
    line.textContent = offlineLine();
    if (OFF.ready && OFF.state !== "saving") line.classList.add("gvb-pp--ok");
    if (/^(failed|nosw|full|gaveup|reload)$/.test(OFF.state)) line.classList.add("gvb-pp--warn");
    s1.appendChild(line);
    if (OFF.state === "saving" && OFF.total) {
      var bar = attrs(el("progress", "gvb-meter"), { max: String(OFF.total), value: String(OFF.done || 0) });
      s1.appendChild(bar);
    }
    var tools = el("div", "gvb-tools");
    pill(tools, T("booth.of_save"), function () { saveOffline("button"); }, { icon: "download", key: "of-save", cls: "gvb-pill--primary", disabled: !canSW || !NET.online || OFF.state === "saving" });
    pill(tools, T("booth.of_clear"), function () {
      if (!window.confirm(T("booth.of_clear_confirm"))) return;
      clearOffline();
    }, { icon: "trash-2", key: "of-clear", cls: "gvb-pill--danger", disabled: !canSW || OFF.state === "saving" });
    s1.appendChild(tools);
    if (canSW && !NET.online) s1.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.of_need_net")));
    var s2 = sect(p, T("booth.of_net_h"));
    s2.appendChild(el("p", "gvb-pp " + (NET.online ? "gvb-pp--ok" : "gvb-pp--warn"), T(NET.online ? "booth.of_online" : "booth.of_offline")));
    var s3 = sect(p);
    var est = el("p", "gvb-pp gvb-pp--muted");
    var per = el("p", "gvb-pp gvb-pp--muted");
    s3.appendChild(est);
    s3.appendChild(per);
    try {
      if (navigator.storage && navigator.storage.estimate) navigator.storage.estimate().then(function (e) {
        if (e && e.quota) est.textContent = T("booth.of_storage", { used: fileSize(e.usage || 0), quota: fileSize(e.quota) });
      }, function () { /* unknown */ });
      if (navigator.storage && navigator.storage.persisted) navigator.storage.persisted().then(function (yes) {
        per.textContent = T(yes ? "booth.of_persist_yes" : "booth.of_persist_no");
      }, function () { /* unknown */ });
    } catch (e) { /* not in this browser */ }
  };

  /* ---------- Share & reset ---------- */
  PANELS.share = function (p) {
    var s1 = sect(p, T("booth.sr_share_h"));
    s1.appendChild(el("p", "gvb-pp gvb-pp--muted", T("booth.sr_share_text")));
    startLinkBox(s1, T("booth.sr_link_label"), "share-link");
    var s2 = sect(p, T("booth.sr_reset_h"));
    var tools = el("div", "gvb-tools");
    pill(tools, T("booth.sr_reset_settings"), function () { resetWith("booth.sr_reset_settings_confirm", "booth.sr_reset_done", { settings: true }); }, { icon: "rotate-ccw", key: "rs-settings" });
    pill(tools, T("booth.sr_reset_polls"), function () { resetWith("booth.sr_reset_polls_confirm", "booth.sr_polls_done", { polls: true }); }, { icon: "vote", key: "rs-polls" });
    pill(tools, T("booth.sr_reset_all"), function () { resetWith("booth.sr_reset_all_confirm", "booth.sr_all_done", { settings: true, polls: true, memo: true }); }, { icon: "trash-2", key: "rs-all", cls: "gvb-pill--danger" });
    s2.appendChild(tools);
    p.appendChild(el("p", "gvb-privacy", T("booth.sr_privacy")));
  };
  /** A reset: asked first, then done, with Undo for 10 s. */
  function resetWith(confirmKey, doneKey, what) {
    if (!window.confirm(T(confirmKey))) return;
    var before = { stored: clone(STORED), polls: clone(POLLS), memo: clone(MEMO) };
    if (what.settings) { STORED = {}; computeSettings(); saveSettings(); }
    if (what.polls) { POLLS = {}; savePolls(); }
    if (what.memo) {
      MEMO.sched = null;
      saveMemo();
      if (P.E) P.E.sched = freshState(null);
    }
    settingsChanged("lang");
    var b = toast(T(doneKey), {
      label: T("booth.undo"),
      run: function () {
        STORED = before.stored || {};
        POLLS = before.polls || {};
        if (what.memo && before.memo) { MEMO.sched = before.memo.sched; if (P.E) P.E.sched = before.memo.sched || P.E.sched; saveMemo(); }
        computeSettings();
        saveSettings();
        savePolls();
        settingsChanged("lang");
        toast(T("booth.undone"));
      },
    });
    if (b) b.focus({ preventScroll: true });
  }

  /* ================================================================== 8. offline: the service worker keeps a copy
     (src/_includes/pwa/sw-core.js: BOOTH_SAVE → BOOTH_PROGRESS … BOOTH_DONE, BOOTH_STATUS, BOOTH_CLEAR → BOOTH_CLEARED,
     answered through the MessageChannel's port, as pwa.js's SAVE is). The worker asked is the one that knows these
     messages (boothWorker: on a device that had the site before this version, the new worker may still be waiting
     behind the old one). OFF.state: idle | saving | done | failed | full | gaveup (no answer) | nosw (no worker can
     keep a copy) | reload (the new worker waits and the old one knows no booth messages: a reload finishes it). */
  var canSW = !!(navigator.serviceWorker && window.isSecureContext && window.caches && window.MessageChannel);
  var OFF = { state: canSW ? "idle" : "nosw", done: 0, total: 0, failed: 0, have: 0, all: 0, bytes: 0, ready: false, checked: false, retry: false,
    retryTimer: 0, chipTimer: 0, again: false, manual: false };
  /** → a Promise kept `ms` after the page's load event (pwa.js registers the worker on load). */
  function whenLoaded(ms) {
    return new Promise(function (resolve) {
      var go = function () { setTimeout(resolve, ms); };
      if (document.readyState === "complete") go(); else window.addEventListener("load", go, { once: true });
    });
  }
  /** The worker that knows the booth's messages. A device that had the site before this version keeps its OLD worker
   *  in charge — it never answers BOOTH_* and can't serve the booth's copy offline — with the new one WAITING until
   *  every tab of the site closes (sw-core.js). This page is already the new version's, so for the operator's own
   *  saves and removals (takeOver) the new worker takes over now: SKIP_WAITING, its activate claims this page, and
   *  pwa.js reloads only after its own "Reload". A visitor's page asking how much is saved (BOOTH_STATUS) never swaps
   *  the worker behind their back: the waiting one answers that. → Promise<the worker to post to, or null> */
  function boothWorker(reg, takeOver) {
    var sw = navigator.serviceWorker;
    if (!reg.waiting) return Promise.resolve(reg.active || sw.controller);
    if (!takeOver) return Promise.resolve(reg.waiting);
    var w = reg.waiting;
    return new Promise(function (resolve) {
      var done = false, t = 0;
      var finish = function () {
        if (done) return;
        done = true;
        clearTimeout(t);
        sw.removeEventListener("controllerchange", finish);
        // taken over: the new active one; not (yet): still the waiting one, which answers too
        resolve(reg.waiting || reg.active || sw.controller);
      };
      t = setTimeout(finish, 10000);
      sw.addEventListener("controllerchange", finish);
      try { w.postMessage({ type: "SKIP_WAITING" }); } catch (e) { finish(); }
    });
  }
  /** A message to the worker; `onMsg(reply)` → true when that reply is the last. Given up after `waitMs` without
   *  news (each reply starts the wait again: on a weak signal the files come slowly but come) — the first answer after
   *  `firstMs` when given (a worker that knows the message answers at once). With nothing registered at all (site
   *  data blocked, a policy: `ready` would never come), given up a few seconds after the page's load. */
  function swCall(msg, onMsg, waitMs, takeOver, firstMs) {
    return new Promise(function (resolve, reject) {
      if (!canSW) { reject(new Error("no worker")); return; }
      var over = false, timer = 0;
      var stop = function (fn, v) { if (over) return; over = true; clearTimeout(timer); fn(v); };
      var wait = function (ms) { clearTimeout(timer); timer = setTimeout(function () { stop(reject, new Error("no answer")); }, ms || waitMs || 45000); };
      wait();
      whenLoaded(3000).then(noWorker).then(function (none) { if (none) stop(reject, new Error("no worker")); });
      navigator.serviceWorker.ready.then(function (reg) {
        if (over) return null;
        return boothWorker(reg, takeOver).then(function (w) {
          if (over) return;
          if (!w) { stop(reject, new Error("no worker")); return; }
          var ch = new MessageChannel();
          ch.port1.onmessage = function (ev) {
            if (over) return;
            var d = ev.data || {};
            wait();
            if (onMsg(d)) stop(resolve, d);
          };
          try { w.postMessage(msg, [ch.port2]); wait(firstMs); } catch (e) { stop(reject, e); }
        });
      }).then(null, function (e) { stop(reject, e); });
    });
  }
  function askPersist() {
    if (MEMO.persistAsked || !navigator.storage || !navigator.storage.persist) return;
    MEMO.persistAsked = true;
    saveMemo();
    try { navigator.storage.persist().then(function () { if (P.drawer && P.tab === "offline") renderPanel("offline"); }, function () { /* the browser decides */ }); } catch (e) { /* not here */ }
  }
  /** Both About pages, the show and the files its items use, kept by the worker (and what is no longer used,
   *  dropped: prune). On start, after new content, and from Settings → Offline → "Save now" — only for the open show
   *  (a retry left from it goes with it). A save asked while one runs (new content swapped in, the connection back)
   *  runs when that one ends: it took the old list. */
  function saveOffline(reason) {
    if (!DATA || !P.root) return;
    if (!canSW) { OFF.state = "nosw"; renderOfflineUI(reason === "start"); return; }
    // "Save for offline when the show starts" decides only the saves on start and after new content; a save asked
    // for with "Save now" goes on by itself (its next 4-minute round, the retry after failures or after the worker
    // went quiet, the connection back), as the panel's "they will be tried again" promises
    if (reason === "button") OFF.manual = true;
    else if (SETTINGS.autoSave === false && !(OFF.manual && (reason === "more" || reason === "retry" || reason === "online"))) return;
    if (!NET.online) { OFF.retry = true; renderOfflineUI(); return; }
    if (OFF.state === "saving") { OFF.again = true; return; }
    OFF.again = false;
    OFF.state = "saving";
    OFF.done = 0;
    OFF.total = 0;
    OFF.retry = false;
    clearTimeout(OFF.retryTimer);
    askPersist();
    var list = saveListOf(DATA, SETTINGS);
    renderOfflineUI();
    swCall({ type: "BOOTH_SAVE", pages: list.pages, files: list.files, prune: true }, function (d) {
      if (d.type === "BOOTH_PROGRESS") {
        OFF.done = Number(d.done) || 0;
        OFF.total = Number(d.total) || 0;
        renderOfflineUI();
        return false;
      }
      return d.type === "BOOTH_DONE";
    }, 45000, true, 15000).then(function (d) {
      // a removal (BOOTH_CLEAR, maybe from another tab) stopped this save: nothing to say — the removal says it
      if (d.stopped) { OFF.again = false; OFF.manual = false; OFF.state = "idle"; renderOfflineUI(); return; }
      var failed = Array.isArray(d.failed) ? d.failed.length : Number(d.failed) || 0;
      OFF.failed = failed;
      OFF.state = d.full ? "full" : failed ? "failed" : "done";
      OFF.have = Number(d.saved) || 0;
      OFF.all = Number(d.total) || OFF.have;
      OFF.bytes = Number(d.bytes) || 0;
      // (new content came during this save: not ready until its files are in too)
      OFF.ready = !failed && OFF.have > 0 && !OFF.again;
      OFF.checked = true;
      MEMO.saved = { at: now(), files: OFF.have, total: OFF.all, bytes: OFF.bytes };
      saveMemo();
      if ((d.more || OFF.again) && !d.full) {
        // the worker's time for one task ran out (a browser stops it after a few minutes), or new content came
        // meanwhile: asked again (with the list as it is now), it goes on — what it kept is skipped
        OFF.state = "idle";
        OFF.retryTimer = setTimeout(function () { saveOffline("more"); }, 1500);
      } else if (failed && !d.full) { OFF.retry = true; OFF.retryTimer = setTimeout(function () { saveOffline("retry"); }, 10 * 60000); }
      else OFF.manual = false;
      renderOfflineUI(true);
    }, function () {
      OFF.state = "gaveup";
      OFF.retry = true;
      // no worker at all (registration blocked: a private window, a policy) — not a save that stopped; the site's new
      // worker still WAITING behind an old one that knows no booth messages: a reload finishes the update; a save that
      // went quiet (the browser stopped the worker half-way) is asked again in 2 minutes: what it kept is skipped
      Promise.all([noWorker(), waitingWorker()]).then(function (r) {
        if (r[0]) { OFF.state = "nosw"; OFF.manual = false; OFF.retry = false; }
        else if (r[1]) { OFF.state = "reload"; OFF.retry = false; }
        else { clearTimeout(OFF.retryTimer); OFF.retryTimer = setTimeout(function () { saveOffline("retry"); }, 2 * 60000); }
        renderOfflineUI(true);
      });
    });
  }
  /** → Promise<true> when this page has no service worker (and so cannot keep a copy). */
  function noWorker() {
    try {
      return navigator.serviceWorker.getRegistration(BASE).then(function (r) { return !r; }, function () { return true; });
    } catch (e) { return Promise.resolve(true); }
  }
  /** → Promise<the site's new worker still waiting (installed, not in charge), or null>. */
  function waitingWorker() {
    try {
      return navigator.serviceWorker.getRegistration(BASE).then(function (r) { return (r && r.waiting) || null; }, function () { return null; });
    } catch (e) { return Promise.resolve(null); }
  }
  /** What the worker holds of the show now (for the chips and Settings → Offline). No worker registered at all:
   *  the page's chip says the browser can't keep a copy (not "Not saved for offline yet"). */
  function offlineStatus() {
    if (!canSW) { OFF.state = "nosw"; renderOfflineUI(); return; }
    if (!DATA || OFF.state === "saving") return;
    var list = saveListOf(DATA, SETTINGS);
    // (the files only: the two pages are kept with the saved pages, not in the booth's copy)
    swCall({ type: "BOOTH_STATUS", files: list.files }, function (d) { return d.type === "BOOTH_STATUS"; }, 8000).then(function (d) {
      OFF.have = Number(d.have) || 0;
      OFF.all = Number(d.total) || 0;
      OFF.bytes = Number(d.bytes) || 0;
      OFF.ready = OFF.all > 0 && OFF.have >= OFF.all;
      OFF.checked = true;
      renderOfflineUI();
    }, function () {
      noWorker().then(function (none) {
        if (none && OFF.state !== "saving") OFF.state = "nosw";
        OFF.checked = true;
        renderOfflineUI();
      });
    });
  }
  function clearOffline() {
    // a removal asked for is not undone by a retry of the save before it (10 minutes later, or when the connection
    // comes back): the retry goes now, before BOOTH_CLEAR is even sent
    OFF.retry = false;
    OFF.manual = false;
    OFF.again = false;
    clearTimeout(OFF.retryTimer);
    OFF.retryTimer = 0;
    swCall({ type: "BOOTH_CLEAR" }, function (d) { return d.type === "BOOTH_CLEARED"; }, 15000, true).then(function () {
      OFF.state = "idle";
      OFF.have = 0;
      OFF.bytes = 0;
      OFF.ready = false;
      OFF.checked = true;
      MEMO.saved = null;
      saveMemo();
      renderOfflineUI();
      toast(T("booth.of_cleared"));
    }, function () { renderOfflineUI(); });
  }
  function offlineLine() {
    var saved = MEMO.saved;
    if (OFF.state === "nosw") return T("booth.of_no_sw");
    if (OFF.state === "reload") return T("booth.of_reload");
    if (OFF.state === "saving") return OFF.total ? T("booth.of_saving", { done: OFF.done, total: OFF.total }) : T("booth.of_saving_start");
    if (OFF.state === "full") return T("booth.of_full");
    if (OFF.state === "failed") return T("booth.of_failed", { n: OFF.failed });
    if (OFF.state === "gaveup") return T("booth.of_gave_up");
    if (OFF.ready) {
      var files = OFF.have || (saved && saved.files) || 0, size = fileSize(OFF.bytes || (saved && saved.bytes) || 0);
      return saved && saved.at ? T("booth.of_ready", { files: files, size: size, date: fmtStamp(saved.at, LANG) }) : T("booth.of_ready_nodate", { files: files, size: size });
    }
    if (OFF.have > 0) return T("booth.of_partial", { have: OFF.have, total: OFF.all, size: fileSize(OFF.bytes) });
    if (OFF.checked) return T("booth.of_none");
    return T("booth.of_checking");
  }
  /** The chip on the screen while saving (then "Ready offline ✓" for a few seconds; a save that ended badly — and a
   *  browser that can't keep a copy at all — for 12 s), Settings → Offline, the page's chip. */
  function renderOfflineUI(finished) {
    var E = P.E;
    if (E && E.alive) {
      clearTimeout(OFF.chipTimer);
      if (OFF.state === "saving") setStatusChip(E, OFF.total ? T("booth.of_saving", { done: OFF.done, total: OFF.total }) : T("booth.of_saving_start"));
      else if (finished && OFF.state === "done") { setStatusChip(E, T("booth.of_done")); OFF.chipTimer = setTimeout(function () { setStatusChip(E, ""); }, 8000); }
      else if (finished && /^(failed|gaveup|full|nosw|reload)$/.test(OFF.state)) { setStatusChip(E, offlineLine()); OFF.chipTimer = setTimeout(function () { setStatusChip(E, ""); }, 12000); }
      else setStatusChip(E, "");
    }
    if (P.drawer && P.tab === "offline") renderPanel("offline");
    renderChips();
  }

  /* ================================================================== 9. the About page: the quick controls, the
     preview card, "Preview here", the status chips, Start, and ?booth=start */
  var CARD = null, INLINE = null, cardVisible = false, sectionSeen = false;
  function saverOn() { return document.documentElement.getAttribute("data-saver") === "on" || navigator.onLine === false && !DATA; }
  function frame() { return document.querySelector("[data-gvb-pv-frame]"); }
  function still(show) {
    var f = frame();
    var s = f ? f.querySelector("[data-gvb-still]") : null;
    if (s) s.hidden = !show;
  }
  /** The quick controls show the settings as they are (also after the dialog changed them). */
  function renderQuick() {
    var map = { event: (SETTINGS.event || {}).en || "", event_es: (SETTINGS.event || {}).es || "", lang: SETTINGS.lang || "both" };
    Array.prototype.forEach.call(document.querySelectorAll("[data-gvb-q]"), function (x) {
      var k = x.getAttribute("data-gvb-q");
      if (k === "preset") return;
      if (document.activeElement === x && x.tagName === "INPUT") return;
      if (map[k] !== undefined && x.value !== map[k]) x.value = map[k];
    });
  }
  /** How many slides can show on this device now (no engine: the page's chip). */
  function pageCount() {
    if (!DATA) return 0;
    return poolOf(DATA, Object.assign({}, SETTINGS, { sound: false }), baseCtx()).filter(function (it) { return !!RENDER[it.type]; }).length;
  }
  function chip(name, text, tone) {
    var c = document.querySelector('[data-gvb-chip="' + name + '"]');
    if (!c) return;
    c.hidden = !text;
    c.classList.toggle("is-ok", tone === "ok");
    c.classList.toggle("is-warn", tone === "warn");
    var sp = c.querySelector("span");
    if (sp && sp.textContent !== text) sp.textContent = text || "";
  }
  function renderChips() {
    if (!document.querySelector("[data-gvb-chip]")) return;
    if (DATA) {
      chip("items", TN("booth.st_items", pageCount()));
      chip("content", DATA.as_of || DATA.built ? T("booth.st_content", { date: fmtDay(DATA.as_of || DATA.built, LANG, true) }) : "");
    } else chip("items", LOADING ? T("booth.st_loading") : LOAD_FAILED ? T("booth.load_failed") : T("booth.st_waiting"), LOAD_FAILED ? "warn" : "");
    var off = "";
    var tone = "";
    if (OFF.state === "nosw") { off = T("booth.st_no_sw"); tone = "warn"; }
    else if (OFF.state === "reload") { off = T("booth.of_reload"); tone = "warn"; }
    else if (OFF.state === "saving") off = OFF.total ? T("booth.of_saving", { done: OFF.done, total: OFF.total }) : T("booth.of_saving_start");
    else if (OFF.ready) { off = T("booth.st_ready"); tone = "ok"; }
    else if (OFF.have > 0) off = T("booth.st_partial", { have: OFF.have, total: OFF.all });
    else if (OFF.checked) off = T("booth.st_not_saved");
    if (!NET.online) { off = T("booth.st_offline") + (OFF.ready ? " · " + T("booth.st_ready") : ""); tone = OFF.ready ? "ok" : "warn"; }
    chip("offline", off, tone);
  }
  var LOAD_FAILED = false;
  /** The show's file for the page (the chips, the previews), once the section is near — never with Data saver on
   *  while online; offline it reads the worker's saved copy (no data used), so the chips can say it is ready. */
  function pageData() {
    if (DATA) return Promise.resolve(DATA);
    var p = loadData();
    renderChips();
    return p.then(function (d) { LOAD_FAILED = false; renderChips(); return d; }, function (e) { LOAD_FAILED = true; renderChips(); throw e; });
  }
  function onData() {
    renderQuick();
    renderChips();
    if (!OFF.checked && OFF.state !== "nosw") offlineStatus();
  }

  /* ---------- the preview card: real slides, small and silent, only while it is on screen ---------- */
  function startCard() {
    if (CARD || INLINE || P.root || !cardVisible || reducedMotion() || saverOn()) return;
    var f = frame();
    if (!f) return;
    pageData().then(function () {
      if (CARD || INLINE || P.root || !cardVisible) return;
      still(false);
      CARD = makeEngine(f, "card");
      attrs(CARD.screen, { "aria-hidden": "true" });
      CARD.screen.inert = true;
      CARD.start();
    }, function () { /* the still slide stays */ });
  }
  function resumeCard() {
    if (CARD) { if (cardVisible) CARD.resume(); return; }
    startCard();
  }
  function stopCard() {
    if (!CARD) return;
    CARD.stop();
    CARD = null;
    if (!INLINE) still(true);
  }
  function stopPreviews() {
    stopInline(true);
    stopCard();
  }

  /* ---------- "Preview here": the show in the card, playable, without sound ---------- */
  function startInline(btn) {
    if (INLINE || P.root) return;
    pageData().then(function () {
      if (INLINE || P.root) return;
      stopCard();
      var f = frame();
      if (!f) return;
      still(false);
      f.classList.add("is-live");
      attrs(f, { role: "region", "aria-label": T("booth.preview_label") });
      INLINE = makeEngine(f, "inline");
      INLINE.screen.addEventListener("click", function (e) {
        var t = e.target;
        if (!t.closest || !INLINE) return;
        var ch = t.closest(".gvb-choice");
        if (ch && !ch.disabled) { INLINE.answer(Number(ch.getAttribute("data-i"))); return; }
        var pr = t.closest(".gvb-pollrow");
        if (pr && !pr.disabled) { INLINE.vote(Number(pr.getAttribute("data-i"))); return; }
        if (t.closest("[data-gvb-reveal]")) INLINE.reveal();
      });
      INLINE.start();
      var ctl = document.querySelector("[data-gvb-pv-ctl]");
      if (ctl) ctl.hidden = false;
      inlinePauseLabel();
      Array.prototype.forEach.call(document.querySelectorAll("[data-gvb-preview]"), function (b) { b.setAttribute("aria-pressed", "true"); });
      live(T("booth.preview_on"));
    }, function () { toast(T("booth.load_failed")); });
  }
  function stopInline(quiet) {
    if (!INLINE) return;
    INLINE.stop();
    INLINE = null;
    var f = frame();
    if (f) {
      f.classList.remove("is-live");
      attrs(f, { role: "img", "aria-label": T("booth.preview_label") });
    }
    still(true);
    var ctl = document.querySelector("[data-gvb-pv-ctl]");
    if (ctl) {
      var hadFocus = ctl.contains(document.activeElement);
      ctl.hidden = true;
      if (hadFocus) { var pb = document.querySelector("[data-gvb-preview]"); if (pb) pb.focus({ preventScroll: true }); }
    }
    Array.prototype.forEach.call(document.querySelectorAll("[data-gvb-preview]"), function (b) { b.setAttribute("aria-pressed", "false"); });
    if (!quiet) resumeCard();
  }
  /** The preview's Pause button: its words and its icon say what a tap does ("Pause the preview" / "Play the
   *  preview") — no pressed state, which would read "Play the preview, pressed" while it stands still. */
  function inlinePauseLabel() {
    var b = document.querySelector('[data-gvb-pv-act="pause"]');
    if (!b || !INLINE) return;
    var sp = b.querySelector("span");
    if (sp) sp.textContent = T(INLINE.paused ? "booth.preview_play" : "booth.preview_pause");
    var old = b.querySelector("svg"), ico = icon(INLINE.paused ? "play" : "pause");
    if (old) { ico.setAttribute("class", old.getAttribute("class") || "size-4"); b.replaceChild(ico, old); }
  }

  /* ---------- the page's hooks ---------- */
  function bindPage() {
    var debounced = {};
    Array.prototype.forEach.call(document.querySelectorAll("[data-gvb-q]"), function (x) {
      var k = x.getAttribute("data-gvb-q");
      if (k === "event" || k === "event_es") {
        x.addEventListener("input", function () {
          clearTimeout(debounced[k]);
          debounced[k] = setTimeout(function () { setSetting(k === "event" ? "event.en" : "event.es", x.value.trim()); }, 300);
        });
      } else if (k === "lang") x.addEventListener("change", function () { setSetting("lang", x.value); });
      else if (k === "preset") x.addEventListener("change", function () {
        if (!x.value) return;
        applyPreset(x.value);
        x.value = "";
      });
    });
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest || (P.root && P.root.contains(t))) return;
      var b = t.closest("[data-gvb-start], [data-gvb-settings], [data-gvb-preview], [data-gvb-pv-act]");
      if (!b) return;
      e.preventDefault();
      if (b.hasAttribute("data-gvb-start")) openPlayer({ gesture: true, opener: b });
      else if (b.hasAttribute("data-gvb-settings")) openPlayer({ gesture: true, noFull: true, tab: "event", opener: b });
      else if (b.hasAttribute("data-gvb-preview")) { if (INLINE) stopInline(); else startInline(b); }
      else {
        var a = b.getAttribute("data-gvb-pv-act");
        if (!INLINE) return;
        if (a === "pause") { if (INLINE.paused) INLINE.resume(); else INLINE.pause(); inlinePauseLabel(); }
        else if (a === "next") INLINE.next({ user: true });
        else if (a === "stop") stopInline();
      }
    });
    // the card plays only while it is on screen; the show's file comes when the section is near
    var f = frame();
    if (f && window.IntersectionObserver) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          cardVisible = en.isIntersecting;
          if (cardVisible) resumeCard(); else if (CARD) CARD.pause();
        });
      }, { threshold: 0.25 }).observe(f);
      var sec = document.querySelector("[data-gvb-section]") || f;
      var io = new IntersectionObserver(function (entries) {
        if (!entries.some(function (en) { return en.isIntersecting; }) || sectionSeen) return;
        sectionSeen = true;
        io.disconnect();
        // offline, the show comes from the worker's saved copy (no data used): the chips can say whether it is ready
        if (!saverOn() || navigator.onLine === false) pageData().then(function () { offlineStatus(); }, function () { /* the chip says so */ });
        else if (!canSW) renderOfflineUI();
      }, { rootMargin: "300px 0px" });
      io.observe(sec);
    }
    // the page's live region for its own toasts (a preset from the quick controls), there before it speaks
    if (document.querySelector("[data-gvb-section]")) pageToast();
  }
  function startPage() {
    loadSettings();
    loadPolls();
    loadMemo();
    renderQuick();
    renderChips();
    bindPage();
    var sp = null;
    try { sp = new URLSearchParams(location.search); } catch (e) { sp = null; }
    if (sp && sp.get("booth") === "start" && document.getElementById("gvb-tpl")) {
      var bs = sp.get("bs"), applied = "";
      if (bs) {
        var dec = call("decode", [bs], null);
        if (isObj(dec)) {
          var pin = STORED.pin;
          STORED = deepMerge({}, dec);
          if (pin && !STORED.pin) STORED.pin = pin;
          computeSettings();
          saveSettings();
          renderQuick();
          applied = "booth.link_applied";
        } else applied = "booth.link_bad";
      }
      openPlayer({ auto: true, applied: applied });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startPage);
  else startPage();
})();
